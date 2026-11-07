"""yt-dlp subprocess download with cookie-file lifecycle and resume fallback."""

from __future__ import annotations

import asyncio
import atexit
import itertools
import json
import math
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import IO, TYPE_CHECKING, cast

from playwright.async_api import Cookie
from pydantic import SecretStr
from structlog import get_logger

from ..config import Settings
from ..exceptions import (
    DownloadError,
    ExtractionError,
    QualityMismatchError,
    QualityNotAvailableError,
    QualityParseError,
)
from ..models.dtos import HLSDownloadRequest
from ..models.enums import CookieSource, DownloadState, ErrorCategory, QualityKind
from ..models.quality import QualitySpec
from ..services.cookies import _cookies_to_netscape
from ..services.downloader_throttle import get_shutdown_event
from ..services.extractor import VKVideoExtractor, _extract_video_id
from ..services.ffmpeg_utils import (
    _SPAWN_BOUNDARY_KWARGS,
    cancel_subprocess,
    iter_process_lines,
)
from ..services.quality import QualitySelector
from ..services.quality_refresh import refresh_stream
from ..services.retry_policies import (
    _compute_backoff_delay,
    _wait_with_shutdown,
)
from ..services.segment_downloader import download_hls_with_resume
from ..services.workspace import DownloadWorkspace
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params, sanitize_text_for_log

if TYPE_CHECKING:
    from ..services.concurrency import SemaphoreLike
    from ..services.state_machine import DownloadStateMachine
    from .downloader_throttle import URLBackoffCoordinator

logger = get_logger(__name__)

_YTDLP_LAUNCH_COUNTER = itertools.count(1)

_YTDLP_FILE_ACCESS_RETRIES = 3
_YTDLP_FILE_ACCESS_RETRY_SLEEP = 0.5

# Cookie artefact lifecycle constants (SEC-001, SEC-002, VAL-602, SEC-006).
# These literals are frozen by B2: ``vk_cookies_`` is what the sweep is keyed
# on, and ``.cookies.txt`` is what the redaction rule in
# utils/url_sanitizer._COOKIE_FILE_ARTEFACT_REGEX keys on. The earlier claim
# that a separate "cleanup tooling" keys on the suffix was an over-claim - only
# the redaction rule does - and is corrected here. Renaming either breaks
# coverage silently.
#
# These literals are DUPLICATED in utils/url_sanitizer.py, where the matching
# rules live, because utils/ must not import services/ (layer rule; it would
# invert the import order and create a cycle). The two copies are kept in
# lock-step by the test suite only.
#
# Redaction-rule design law (see the rules in utils/url_sanitizer.py):
#  - Left boundary: a rule's left boundary must be a predicate its own
#    replacement can never satisfy. ***REDACTED*** ends in '*', a non-word
#    character, so a \b guard would manufacture a boundary on the second pass
#    (measured 3 fixed-point violations in 400 000). '*' is inside the
#    excluded set, so the chosen lookbehind is unsatisfiable by the marker
#    (0 violations).
#  - The parent is CONSUMED by the optional greedy lead, not asserted by
#    lookbehind: a variable-length lookbehind is illegal in the re module,
#    and consuming the parent is what strips the username-bearing temp root
#    (C:\Users\<name>\AppData\Local\Temp, CWE-532).
#  - No re.IGNORECASE: every matched string is built from a frozen lowercase
#    literal, and IGNORECASE widens [a-z] with U+0130/U+0131/U+017F/U+212A for
#    zero measured coverage gain.
#  - The tail is [a-z0-9_]+, not {8}: tempfile._RandomNameSequence.characters
#    is a CPython internal whose length is not contractual.
# Note: neither string is matched by ``.gitignore`` - its only cookie rule is
# ``*_cookies.txt``, which needs an underscore where the product emits a dot.
# The artefacts live under the OS temp root, outside the working tree, so no
# ignore rule is required for them to stay out of ``git status``.
_COOKIE_ARTIFACT_PREFIX = "vk_cookies_"
_COOKIE_ARTIFACT_SUFFIX = ".cookies.txt"
_ARTEFACT_DIR_SUFFIX = "_dir"
_OWNER_PID_FILENAME = "owner.pid"

# Grace window applied ONLY to a PID-less directory (owner.pid absent or
# unreadable): such a directory is reclaimed once it is provably older than
# this duration, and retained otherwise. It is never a deletion criterion for
# a directory carrying a readable record (VAL-602). Derived from the measured
# creation window (median 0.236 ms / p95 0.546 ms / max 1.482 ms on an idle
# machine) plus loaded-machine headroom; see the _sweep_stale_cookie_dirs
# docstring and commit body. Not a frozen artefact string; not a key for R3.
_COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS: float = 30.0

# Tracks every artefact directory this process created, so the atexit
# handler can purge them on orderly exit.
_COOKIE_ARTIFACT_DIRS: set[Path] = set()
_cookie_lifecycle_started: bool = False
_COOKIE_LIFECYCLE_LOCK = threading.Lock()


def _is_pid_alive(pid: int) -> bool:
    """Report whether a process with ``pid`` is currently alive.

    On POSIX, uses ``os.kill(pid, 0)`` - signal 0 tests process existence
    without delivering a signal. ``os.kill`` is **prohibited** on the Windows
    branch, but not because it would terminate the target: on Windows
    ``os.kill(pid, sig)`` dispatches the two console-control values first -
    ``signal.CTRL_C_EVENT`` (0) and ``signal.CTRL_BREAK_EVENT`` (1) go to
    ``GenerateConsoleCtrlEvent``, and only any other value reaches
    ``TerminateProcess``. Because ``CTRL_C_EVENT == 0``, ``os.kill(pid, 0)``
    takes the **console-control** branch, which makes it wrong as a probe twice
    over: against a target that is not attached to a console the call fails with
    ``OSError`` and says nothing about liveness - exactly the batch and service
    case ``SEC-002`` targets - and against a console-attached target it delivers a
    real CTRL_C event to that process's console group, which reaches the
    operator's own foreground program. A ``ctypes`` probe via ``OpenProcess`` +
    ``GetExitCodeProcess`` is used instead (D-1); ``STILL_ACTIVE`` (259) means
    the process has not exited yet.
    """
    if os.name == "nt":
        import ctypes

        # GetExitCodeProcess requires PROCESS_QUERY_INFORMATION (0x0400), not
        # SYNCHRONIZE - SYNCHRONIZE only permits WaitForSingleObject. Using the
        # wrong right makes GetExitCodeProcess fail with access denied, so
        # _is_pid_alive incorrectly returns False for the current process (D-1).
        PROCESS_QUERY_INFORMATION = 0x0400
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
        if handle == 0:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == 259  # STILL_ACTIVE
            return False
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _is_pid_probe_conclusive(pid: int) -> bool:
    """Report whether ``_is_pid_alive``'s ``False`` for ``pid`` proves death.

    Answers one question only: was a negative liveness result a *positive
    demonstration of death* (the PID is absent), or an *inconclusive* denial
    that could hide a live owner (e.g. a privilege boundary)? It never re-implements
    ``_is_pid_alive``: that function is the sole liveness oracle and is left
    untouched.

    On POSIX the answer is always ``True``: ``_is_pid_alive`` already maps
    ``PermissionError`` to alive, so its ``False`` can only come from
    ``ProcessLookupError`` - a definitive "no such process".

    On Windows a ``False`` can also come from ``OpenProcess`` failing with
    ``ERROR_ACCESS_DENIED`` (5): an elevated, SYSTEM, or other-account owner
    like live PID 4 opens with access denied and is misreported dead. This
    function re-issues ``OpenProcess(PROCESS_QUERY_INFORMATION)`` and treats
    **only** ``ERROR_INVALID_PARAMETER`` (87) - "no process object for this PID"
    - as conclusive; ``ERROR_ACCESS_DENIED`` (5) and any other failure are
    inconclusive and the directory is retained.

    Trap honoured: the DLL is loaded with
    ``ctypes.WinDLL("kernel32", use_last_error=True)`` and consulted via
    ``ctypes.get_last_error()``. ``ctypes.windll.kernel32`` does not arm the
    last-error slot and can report a stale code, which would make a denied
    owner look conclusively dead - re-opening the very hazard this closes.
    When the handle is non-zero (a process object exists) the handle is closed
    and the result is inconclusive, for a handle that opens proves nothing
    about liveness once ``_is_pid_alive`` has already answered ``False``.
    """
    if os.name != "nt":
        return True
    import ctypes

    # PROCESS_QUERY_INFORMATION (0x0400) is the right to query exit status;
    # it is the same right _is_pid_alive uses, so this is not an ACL reader
    # and adds no dependency.
    process_query_information = 0x0400
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(process_query_information, False, pid)
    if handle == 0:
        last_error = ctypes.get_last_error()
        # ERROR_INVALID_PARAMETER (87): the PID is not allocated - death proven.
        # Any other code, notably ERROR_ACCESS_DENIED (5), is inconclusive.
        return last_error == 87
    kernel32.CloseHandle(handle)
    return False


def _read_owner_pid(cookie_dir: Path) -> int | None:
    """Read the owning PID recorded in ``owner.pid`` within ``cookie_dir``.

    Returns ``None`` to mean "no readable record" - the file is absent, empty,
    unparseable, or is not a regular file - never "the owner is dead". What the
    sweep may conclude from ``None`` is :func:`_sweep_stale_cookie_dirs`'
    business; this function is a pure parser and its return value and except
    clause are left unchanged.
    """
    owner_file = cookie_dir / _OWNER_PID_FILENAME
    try:
        return int(owner_file.read_text().strip())
    except OSError, ValueError:
        return None


def _purge_cookie_artifact_dir(cookie_dir: Path) -> None:
    """Forcefully remove a stale cookie artefact directory and its contents.

    Used by the sweep (prior-run residue) and the atexit handler. Errors
    are swallowed so a leftover directory never blocks the current run.
    """
    shutil.rmtree(cookie_dir, ignore_errors=True)


def _remove_cookie_artifact_dir(cookie_dir: Path) -> None:
    """Remove a cookie artefact directory and its ``owner.pid`` record.

    The directory holds exactly two things: the credential file, which the
    caller has already unlinked, and ``owner.pid``, written by
    ``_create_cookie_artifact_dir``. ``Path.rmdir`` succeeds only on an EMPTY
    directory, so ``owner.pid`` is unlinked first and the directory is then
    removed. No glob, no recursion: the credential file is never touched here.

    ``FileNotFoundError`` is success, not failure - a concurrent sweep (or an
    earlier teardown) already removed the directory - so its arm precedes the
    ``OSError`` arm, which it subclasses. An ``OSError`` from the ``owner.pid``
    unlink means ``rmdir`` provably cannot succeed while that file exists, so it
    is not attempted; one ``cookie_file_cleanup_failed`` record is emitted and
    the directory is left tracked for the ``atexit`` handler.

    A record is emitted only on genuine survival. Successful removal is silent.
    """
    removed = False
    failure: OSError | None = None
    try:
        (cookie_dir / _OWNER_PID_FILENAME).unlink(missing_ok=True)
        cookie_dir.rmdir()
        removed = True
    except FileNotFoundError:  # must precede except OSError: it subclasses it
        removed = True
    except OSError as exc:
        failure = exc
    with _COOKIE_LIFECYCLE_LOCK:
        if removed:
            _COOKIE_ARTIFACT_DIRS.discard(cookie_dir)
    if failure is not None:
        logger.warning(
            "cookie_file_cleanup_failed",
            path=str(cookie_dir),
            error=str(failure),
        )


def _cookie_artifact_dir_age_seconds(cookie_dir: Path) -> float | None:
    """Age in seconds of a cookie artefact directory, or ``None`` if unknown.

    Reads ``st_birthtime`` where the platform exposes it and falls back to
    ``st_ctime`` (which on Windows *is* the creation time; on POSIX it is the
    inode-change time, equal to creation time for a freshly made directory).
    Returns ``None`` when the age cannot be established - ``stat`` raises, or
    neither attribute exists - so the caller degrades to *retain*. Uses
    ``time.time()``, never ``time.monotonic()``: the value is compared against a
    filesystem timestamp written by another process, so only the wall clock is
    comparable. ``max(0.0, ...)`` absorbs a clock that steps backwards.
    """
    try:
        info = cookie_dir.stat()
    except OSError:
        return None
    created = getattr(info, "st_birthtime", None)
    if created is None:
        created = getattr(info, "st_ctime", None)
    if created is None:
        return None
    return max(0.0, time.time() - float(created))


def _sweep_stale_cookie_dirs() -> None:
    """Remove cookie artefact directories whose owner is positively dead.

    Scans the system temp directory for directories whose names start with
    ``_COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX`` - composed, this is
    ``vk_cookies_`` + ``_dir`` = ``vk_cookies__dir`` (the doubled underscore is
    the join, not a separate literal). Classification is **default-deny**:
    a directory is destroyed only on a positive demonstration that it is no
    longer in use. Per matching directory:

    1. ``owner.pid`` is readable and parses to an int PID. The sweep calls
       ``_is_pid_alive`` exactly once: a live PID is retained; a not-live PID
       is reclaimed only when ``_is_pid_probe_conclusive`` reports the
       ``False`` as a positive demonstration of death (e.g.
       ``ERROR_INVALID_PARAMETER`` on Windows); an inconclusive probe
       (``ERROR_ACCESS_DENIED``, a PID this user cannot probe) is retained.
    2. ``owner.pid`` is absent or unreadable - ``_read_owner_pid`` returns
       ``None``. Such a directory is reclaimed only when its age is known and
       is at least ``_COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS``; an age that
       cannot be established is retained. The grace is a **skip condition on
       this branch only** and never appears in the criterion for a directory
       carrying a readable record, so the deletion criterion stays age-free
       (VAL-602).

    The "cannot determine the owner" states are therefore not read as "stale"
    by default: a missing record (the mid-creation window left by
    ``_create_cookie_artifact_dir``, which calls ``mkdtemp`` before writing
    ``owner.pid``), an empty ``owner.pid``, an unparseable record,
    ``owner.pid`` being a directory, a crash between ``open`` and ``write``,
    and a record denied to this user. The PID-less class *is* reclaimed by the
    sweep itself once provably older than the grace - and because ``R1``'s
    teardown window (``_remove_cookie_artifact_dir`` unlinking ``owner.pid``
    then ``rmdir``) is byte-identical on disk to a PID-less directory, that
    window is closed by the same grace.

    What the sweep cannot reclaim is **not** destroyed: an owner PID this user
    cannot probe (inconclusive) is retained for the owning run's own ``atexit``
    handler or the operator; ``R1``'s teardown window before it ages out is
    likewise left for a later sweep. ``R1``'s locked-file residue -
    ``shutil.rmtree`` with ``ignore_errors=True`` may silently fail on a
    credential file held open by an indexer or scanner - sits in this class; it
    is retried on later sweeps and otherwise needs the operator. PID reuse is
    pre-existing and deliberately untouched: a recycled PID makes a dead owner
    look live, so residue is retained, never destroyed.

    This is the liveness-gated sweep that makes residue reclaimable by the
    *next* run rather than only by the operator (SEC-002), and is PID-based
    rather than age-based in its deletion criterion to avoid the concurrency
    hazard VAL-602 rules out (VAL-602).
    """
    temp_dir = Path(tempfile.gettempdir())
    dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
    stale: list[Path] = []
    try:
        for entry in temp_dir.iterdir():
            if not entry.is_dir():
                continue
            if not entry.name.startswith(dir_prefix):
                continue
            owner_pid = _read_owner_pid(entry)
            if owner_pid is None:
                age = _cookie_artifact_dir_age_seconds(entry)
                if age is not None and age >= _COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS:
                    stale.append(entry)
            elif not _is_pid_alive(owner_pid) and _is_pid_probe_conclusive(owner_pid):
                stale.append(entry)
    except OSError:
        return
    for cookie_dir in stale:
        _purge_cookie_artifact_dir(cookie_dir)
        with _COOKIE_LIFECYCLE_LOCK:
            _COOKIE_ARTIFACT_DIRS.discard(cookie_dir)


def clean_legacy_cookie_files(temp_dir: Path | None = None) -> int:
    """Remove legacy bare cookie files from the shared temp root (R3 / SEC-002 residue).

    Earlier versions wrote the borrowed session cookie straight into the system
    temp folder as ``vk_cookies_<tail>.cookies.txt`` and never reclaimed it.
    The per-run fix (R1) only recognises the private ``vk_cookies__dir*`` folders
    it created, so those legacy bare files are invisible to the automatic sweep
    and accumulate indefinitely.

    This function reclaims them **only when the operator explicitly asks** (§9 Q1,
    Option D): it scans ``temp_dir`` (the system temp root by default) for files
    matching the legacy cookie-file shape and unlinks each one. It is **not**
    automatic and runs only when invoked by the ``clean-cookies`` CLI command.

    **Liveness.** A bare legacy file carries no ``owner.pid`` record, so the
    product cannot distinguish "abandoned" from "in use right now". Option D
    places that decision with the operator: the operator invokes the command
    knowing no concurrent instance is using those files. The function therefore
    performs no PID probe - it would be a false safety that could silently
    preserve residue while implying protection.

    **Scope.** Only bare *files* matching ``vk_cookies_<tail>.cookies.txt`` are
    considered. The ``vk_cookies__dir*`` directories owned by a live run are never
    touched here - they have their own lifecycle and the sweep in
    :func:`_sweep_stale_cookie_dirs` reclaims their dead-PID residue.

    Args:
        temp_dir: Directory to scan. Defaults to ``tempfile.gettempdir()``.

    Returns:
        The number of files removed.
    """
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir())

    removed = 0
    try:
        for entry in temp_dir.iterdir():
            if not entry.is_file():
                continue
            if not entry.name.startswith(_COOKIE_ARTIFACT_PREFIX):
                continue
            if not entry.name.endswith(_COOKIE_ARTIFACT_SUFFIX):
                continue
            # Skip directory-shaped artefacts: those are ``vk_cookies__dir*``
            # and belong to the automatic sweep, not this explicit command.
            if entry.name.startswith(_COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX):
                continue
            try:
                entry.unlink()
                removed += 1
                logger.info("legacy_cookie_file_removed", path=str(entry))
            except OSError as exc:
                logger.warning(
                    "legacy_cookie_file_cleanup_failed",
                    path=str(entry),
                    error=str(exc),
                )
    except OSError:
        return removed
    return removed


def _create_cookie_artifact_dir() -> Path:
    """Create a private per-run directory for cookie artefacts.

    The directory is created within the system temp directory and records
    the current process's PID in ``owner.pid`` so the sweep can identify
    orphans after a hard kill. The directory is tracked in
    ``_COOKIE_ARTIFACT_DIRS`` for atexit cleanup.
    """
    _ensure_cookie_lifecycle_started()
    dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
    cookie_dir = Path(tempfile.mkdtemp(prefix=dir_prefix))
    owner_file = cookie_dir / _OWNER_PID_FILENAME
    # VAL-602 race window: between mkdtemp returning and write_text completing
    # the directory is observable with NO owner.pid (the widest sub-state is a
    # zero-length owner.pid, since open(mode='w') creates the file before any
    # byte lands). A concurrent sweep must not destroy it; _sweep_stale_cookie_dirs
    # covers this PID-less window with the _COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS
    # grace. Behaviour is unchanged: mkdtemp, the write, the lock and the set.add
    # all stay as-is, and mkdtemp's 0o700 POSIX semantics are untouched.
    owner_file.write_text(str(os.getpid()))
    with _COOKIE_LIFECYCLE_LOCK:
        _COOKIE_ARTIFACT_DIRS.add(cookie_dir)
    return cookie_dir


def _ensure_cookie_lifecycle_started() -> None:
    """Register the atexit sweep handler (idempotent).

    On the first call, sweeps stale directories from prior runs and
    registers ``_cleanup_cookie_artifact_dirs`` with ``atexit``. Subsequent
    calls are no-ops, so repeat artefact creation registers only one hook.
    """
    global _cookie_lifecycle_started
    with _COOKIE_LIFECYCLE_LOCK:
        if _cookie_lifecycle_started:
            return
        _cookie_lifecycle_started = True
    _sweep_stale_cookie_dirs()
    atexit.register(_cleanup_cookie_artifact_dirs)


def _cleanup_cookie_artifact_dirs() -> None:
    """atexit handler: purge every cookie artefact directory this process created."""
    with _COOKIE_LIFECYCLE_LOCK:
        tracked = list(_COOKIE_ARTIFACT_DIRS)
    for cookie_dir in tracked:
        _purge_cookie_artifact_dir(cookie_dir)
    with _COOKIE_LIFECYCLE_LOCK:
        _COOKIE_ARTIFACT_DIRS.clear()


def _create_temp_cookie_file(cookies: str | list[Cookie]) -> Path:
    """Create a temporary Netscape cookie file in a per-run private directory.

    The file is written inside a private subdirectory of the system temp
    directory (created by :func:`_create_cookie_artifact_dir`) with mode 0o600
    on POSIX. The private directory records the owning process's PID so the
    sweep can reclaim it on the next run if this process is hard-killed
    (SEC-002).

    Args:
        cookies: Either a raw cookie string (Netscape format) or a list of
            Playwright Cookie objects.

    Returns:
        Path to the temporary cookie file (mode 0o600, applied on POSIX; see
        D-11). The caller is responsible for cleanup of both the file and
        its containing directory.
    """
    content = _cookies_to_netscape(cookies)
    cookie_dir = _create_cookie_artifact_dir()
    fd, path = tempfile.mkstemp(
        suffix=_COOKIE_ARTIFACT_SUFFIX,
        prefix=_COOKIE_ARTIFACT_PREFIX,
        dir=str(cookie_dir),
    )
    # QLT-004: Always close the fd in `finally` BEFORE unlinking the file.
    # On Windows, an open fd locks the file and unlink will silently fail.
    # Suppressing close errors prevents masking the original write error.
    write_error: OSError | None = None
    try:
        os.write(fd, content.encode())
    except OSError as exc:
        write_error = exc
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    if write_error is not None:
        Path(path).unlink(missing_ok=True)
        _remove_cookie_artifact_dir(cookie_dir)
        raise write_error
    # DF-007: Confine the artefact by location, not just by mode.
    # _create_cookie_artifact_dir created a private directory (mkdtemp uses
    # 0o700 on POSIX), so only the owning user can reach the file inside.
    # This os.chmod(0o600) is kept as defence-in-depth for the file's POSIX
    # permission bits; on Windows os.chmod toggles only the read-only
    # attribute, so the owner-only guarantee is not offered there (D-11) and
    # the mode is requested for its POSIX effect only.
    os.chmod(path, 0o600)
    return Path(path)


def _create_temp_batch_file(url: str) -> Path:
    """Create a private temp file holding a signed playlist URL for yt-dlp.

    yt-dlp reads the URL via ``--batch-file <path>`` instead of receiving it
    on argv, so the signed URL (with its query token) never enters the child
    process command line. The file is created inside a private per-run
    artefact directory (reusing the cookie artefact lifecycle) with mode 0o600
    on POSIX. The caller is responsible for unlinking the file and its
    containing directory.

    Args:
        url: Signed playlist URL to write (one URL per line, as yt-dlp expects).

    Returns:
        Path to the temporary batch file.
    """
    _ensure_cookie_lifecycle_started()
    url_dir = _create_cookie_artifact_dir()
    fd, path = tempfile.mkstemp(
        suffix=".txt",
        prefix=_COOKIE_ARTIFACT_PREFIX,
        dir=str(url_dir),
    )
    write_error: OSError | None = None
    try:
        os.write(fd, (url + "\n").encode("utf-8"))
    except OSError as exc:
        write_error = exc
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    if write_error is not None:
        Path(path).unlink(missing_ok=True)
        _remove_cookie_artifact_dir(url_dir)
        raise write_error
    os.chmod(path, 0o600)
    return Path(path)


# Backwards/alternative names kept for compatibility with callers/tests.
_create_temp_url_file = _create_temp_batch_file
_create_private_temp_file = _create_temp_batch_file


async def _await_first_and_cancel_others(
    *tasks: asyncio.Task[object],
) -> tuple[set[asyncio.Task[object]], set[asyncio.Task[object]]]:
    """Launch tasks concurrently, await first completion, cancel remaining.

    Args:
        *tasks: Tasks to await concurrently.

    Returns:
        Tuple of (done_tasks, pending_tasks) after cancellation.

    A task in ``done`` that raised - e.g. the reader dying mid-drain - has its
    exception retrieved and reported via the ``subprocess_reader_failed`` event
    so the failure is visible instead of swallowed.  The exception is never
    re-raised: that would turn a cooperative drain into a crash.  A
    cancelled-and-settled pending task stays in ``pending`` and produces no
    record, preserving plan 08's settle-before-return contract.
    """
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED,
    )
    # Cancel pending tasks
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    # Report any failed task's exception so a reader death is visible. Only
    # the ``done`` set is inspected: cancelled-and-settled tasks remain in
    # ``pending`` and produce no record. The exception is retrieved, not
    # re-raised - re-raising would turn a drain into a crash (TRN-006 sink half).
    for task in done:
        if task.cancelled():
            continue
        exc = task.exception()
        if exc is not None:
            logger.error("subprocess_reader_failed", error=str(exc))
    return done, pending


async def _await_ytdlp_reap_with_timeout(
    process: asyncio.subprocess.Process,
    timeout: float,
) -> int:
    """Bound the one-shot re-wait after the yt-dlp reader has drained the stream.

    Wraps ``process.wait()`` in ``asyncio.wait_for`` and ensures the child is
    terminated via ``cancel_subprocess`` on timeout or cancellation, preventing
    an unreaped orphan. The shape mirrors ``_await_ffmpeg_with_timeout``.

    The bound is an **inactivity** bound: it is only armed once the reader task
    (``_monitor_progress`` or ``_drain_output``) has finished consuming the
    child's stdout - i.e. the child has gone silent. While the reader is still
    yielding lines the clock is never started, so a child that keeps producing
    output is never killed, no matter how long it runs. A bare
    ``asyncio.wait_for(process.wait(), ...)`` without this ladder would leave
    the child unreaped on timeout.

    Args:
        process: The yt-dlp subprocess whose re-wait is being bounded.
        timeout: Maximum seconds of inactivity (silence) to wait for the
            child to exit before terminating it. Mandatory - has no default
            so the bound cannot be forgotten.

    Returns:
        The child's exit code, or ``None``-equivalent if already set.

    Raises:
        TimeoutError: If the child does not exit within ``timeout`` seconds
            of the reader finishing. The child is terminated before
            re-raise.
        asyncio.CancelledError: If the caller is cancelled. The child is
            terminated before re-raise.
    """
    try:
        returncode = await asyncio.wait_for(process.wait(), timeout=timeout)
        return returncode
    except TimeoutError, asyncio.CancelledError:
        await cancel_subprocess(process)
        raise


# yt-dlp progress lines (see yt_dlp/downloader/common.py, msg_template).
#
# yt-dlp picks one of five templates depending on what it knows about the
# download; a fragment (HLS) download only knows an *estimated* total, so the
# size is prefixed with "~" and the estimate grows as fragments are discovered:
#   [download]  40.3% of 649.37MiB at 983.45KiB/s ETA 06:43
#   [download]   0.8% of ~   1.18GiB at 1.42MiB/s ETA 16:38 (frag 5/566)
#   [download]  12.34MiB at 1.00MiB/s (00:12)
#   [download]   0.0% at Unknown B/s ETA Unknown
# Each may carry a trailing " (frag i/n)" or " (frag i)".
#
# Every progress line begins with a number right after "[download]" (a percent,
# "N/A", or a byte count); every one-shot message begins with a word
# ("Destination:", "Downloading", "has already been downloaded", ...). That
# distinction is what keeps a progress update on one rewritten line instead of
# appending a new one per update.
_YTDLP_PROGRESS_LINE_RE = re.compile(r"^\[download\]\s+(?:N/A|\d+(?:\.\d+)?)(?:%|[KMGT]?i?B)")

# Percent-and-size progress lines, the subset whose byte counts can be derived.
# The optional "~" marks an estimated total (fragment downloads); without it in
# the pattern the estimated form is not recognised as progress at all and every
# update is appended as a new line.
#
# yt-dlp produces several ETA formats depending on the calculated value:
#   - MM:SS        e.g. "06:43"         (eta < 1 hour)
#   - HH:MM:SS     e.g. "01:01:00"      (1h <= eta <= 99h)
#   - --:--:--     (eta > 99h or unknown, e.g. very large file / slow speed)
#   - "Unknown"    (speed is 0, eta not yet calculated)
#
# Speed can also be "Unknown B/s" right after start.  The regex uses
# permissive patterns for speed/eta because _parse_ytdlp_progress() only
# reads pct, size, and size_unit -- speed/eta groups exist for clarity only.
_YTDLP_PROGRESS_RE = re.compile(
    r"\[download\]\s+"
    r"(?P<pct>\d+(?:\.\d+)?)%\s+of\s+"
    r"(?P<estimate>~)?\s*"
    r"(?P<size>\d+(?:\.\d+)?)"
    r"(?P<size_unit>[KMGT]?i?B)"
    r"\s+at\s+"
    r"(?P<speed>.+?)"
    r"\s+ETA\s+"
    r"(?P<eta>\S+)"
)

# Size unit multipliers to bytes
_SIZE_UNITS: dict[str, int] = {
    "B": 1,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
}


def _is_ytdlp_progress_line(line: str) -> bool:
    """Report whether a yt-dlp line is a live progress update.

    Covers every template yt-dlp can emit for a download (known total,
    estimated total with the ``~`` marker, byte count without a total, and the
    percent-only fallback), optionally followed by a ``(frag i/n)`` suffix.
    One-shot ``[download]`` messages (Destination, Downloading, Resuming, ...)
    are not progress and keep their own line.

    Args:
        line: A decoded stderr line from the yt-dlp subprocess.

    Returns:
        True if the line is a progress update.
    """
    return _YTDLP_PROGRESS_LINE_RE.match(line) is not None


@dataclass
class ProgressState:
    """Normalized progress state for a single yt-dlp download attempt.

    Separates measured (downloaded) bytes, fragment-based progress, and the
    (possibly estimated) total size so callers can avoid misleading percentage
    or ETA jumps caused by fluctuating byte estimates.
    """

    downloaded: int = 0
    total: int = 0
    fragment_index: int = 0
    fragment_count: int = 0
    is_estimate: bool = False
    eta_seconds: float | None = None


def _parse_ytdlp_eta(text: str) -> float | None:
    """Parse a yt-dlp ETA token defensively.

    Accepts ``MM:SS`` and ``HH:MM:SS``. Returns ``None`` for dashes,
    ``Unknown``, empty, unparseable or negative values.
    """
    if text is None:
        return None
    token = str(text).strip()
    if not token:
        return None
    if token.lower() in {"unknown", "n/a"}:
        return None
    if token in {"--:--:--", "--:--", "-"}:
        return None
    if token.startswith("-"):
        return None
    if ":" in token:
        parts = token.split(":")
        try:
            values = [int(p) for p in parts]
        except ValueError:
            return None
        if len(values) == 2:
            hours = 0
            minutes, seconds = values
        elif len(values) == 3:
            hours, minutes, seconds = values
        else:
            return None
        if any(v < 0 for v in values):
            return None
        # Reject obviously malformed minute/second fields.
        if seconds > 59 or minutes > 59:
            return None
        total = hours * 3600 + minutes * 60 + seconds
        if total < 0:
            return None
        return float(total)
    try:
        value = float(token)
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _parse_ytdlp_progress_state(line: str) -> ProgressState | None:
    """Parse a yt-dlp progress line into a :class:`ProgressState`.

    Extends :func:`_parse_ytdlp_progress` with fragment information parsed from
    a trailing ``(frag i/n)`` or ``(frag i)`` suffix and an ``is_estimate``
    flag derived from the ``~`` marker on the total size.

    Args:
        line: A decoded stderr line from the yt-dlp subprocess.

    Returns:
        A :class:`ProgressState` if the line carries a percent and a size,
        otherwise ``None``.
    """
    match = _YTDLP_PROGRESS_RE.search(line)
    if match is not None:
        try:
            pct = float(match.group("pct"))
        except ValueError:
            return None
        if pct < 0 or pct > 100:
            return None
        size = float(match.group("size"))
        size_unit = match.group("size_unit")
        multiplier = _SIZE_UNITS.get(size_unit, 1)
        raw_total = size * multiplier
        if not math.isfinite(raw_total) or raw_total < 0:
            raw_total = float(sys.maxsize)
        total = min(int(raw_total), sys.maxsize)
        try:
            downloaded = int(total * pct / 100.0)
        except OverflowError, ValueError:
            downloaded = total
        if downloaded > total:
            downloaded = total
            is_estimate = True
        else:
            is_estimate = match.group("estimate") is not None
        # TiB/TB totals (or >= 1 TiB) are estimates.
        if size_unit in ("TiB", "TB") or total >= (1 << 40):
            is_estimate = True
        if match.group("estimate") is not None:
            is_estimate = True
        eta_seconds = _parse_ytdlp_eta(match.group("eta"))
        frag_match = re.search(r"\(frag\s+(\d+)(?:/(\d+))?\)", line)
        fragment_index = int(frag_match.group(1)) if frag_match else 0
        fragment_count = (
            int(frag_match.group(2)) if frag_match and frag_match.group(2) is not None else 0
        )
        return ProgressState(
            downloaded=downloaded,
            total=total,
            fragment_index=fragment_index,
            fragment_count=fragment_count,
            is_estimate=is_estimate,
            eta_seconds=eta_seconds,
        )

    # Byte-count progress lines carry a measured byte count but no total.
    byte_match = re.search(
        r"\[download\]\s+(?P<size>\d+(?:\.\d+)?)(?P<size_unit>[KMGT]?i?B)\s+at\b", line
    )
    if byte_match is not None:
        size = float(byte_match.group("size"))
        size_unit = byte_match.group("size_unit")
        multiplier = _SIZE_UNITS.get(size_unit, 1)
        raw = size * multiplier
        if not math.isfinite(raw) or raw < 0:
            raw = 0.0
        downloaded = min(int(raw), sys.maxsize)
        frag_match = re.search(r"\(frag\s+(\d+)(?:/(\d+))?\)", line)
        fragment_index = int(frag_match.group(1)) if frag_match else 0
        fragment_count = (
            int(frag_match.group(2)) if frag_match and frag_match.group(2) is not None else 0
        )
        return ProgressState(
            downloaded=downloaded,
            total=0,
            fragment_index=fragment_index,
            fragment_count=fragment_count,
            is_estimate=False,
        )

    # Percent-only fallback lines carry no size at all.
    pct_match = re.search(r"\[download\]\s+(?P<pct>N/A|\d+(?:\.\d+)?)%\s+at\b", line)
    if pct_match is not None:
        pct_token = pct_match.group("pct")
        if pct_token != "N/A":
            try:
                pct_val = float(pct_token)
            except ValueError:
                return None
            if pct_val < 0 or pct_val > 100:
                return None
        frag_match = re.search(r"\(frag\s+(\d+)(?:/(\d+))?\)", line)
        fragment_index = int(frag_match.group(1)) if frag_match else 0
        fragment_count = (
            int(frag_match.group(2)) if frag_match and frag_match.group(2) is not None else 0
        )
        # Try to parse ETA if present.
        eta_match = re.search(r"ETA\s+(?P<eta>\S+)", line)
        eta_seconds = _parse_ytdlp_eta(eta_match.group("eta")) if eta_match else None
        return ProgressState(
            downloaded=0,
            total=0,
            fragment_index=fragment_index,
            fragment_count=fragment_count,
            is_estimate=False,
            eta_seconds=eta_seconds,
        )

    return None


def _parse_ytdlp_progress(line: str) -> tuple[int, int] | None:
    """Parse a yt-dlp progress line into (downloaded_bytes, total_bytes).

    yt-dlp with ``--newline`` writes lines like::

        [download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43
        [download]   0.8% of ~   1.18GiB at 1.42MiB/s ETA 16:38 (frag 5/566)

    Args:
        line: A decoded stderr line from the yt-dlp subprocess.

    Returns:
        Tuple of (downloaded_bytes, total_bytes) if the line carries a percent
        and a size, otherwise ``None``. Templates without a total (a bare byte
        count) are still progress updates - see :func:`_is_ytdlp_progress_line`
        - they simply carry no ratio to report.
    """
    state = _parse_ytdlp_progress_state(line)
    if state is None or state.total <= 0:
        return None
    return state.downloaded, state.total


def _echo_ytdlp_line(line: str, *, echo: bool = True) -> None:
    """Echo a yt-dlp output line to the console.

    What reaches stderr is the TRANSFORMED line: ``https?://`` URLs are reduced
    to ``scheme://host/***REDACTED***`` and the product's own ``vk_cookies_``
    artefact file and directory names collapse to ``***REDACTED***``, applied
    once at the write by
    :func:`~vkdownloader.utils.url_sanitizer.sanitize_text_for_log`.

    Classification and byte accounting use the RAW line:
    :func:`_is_ytdlp_progress_line` and :func:`_parse_ytdlp_progress` both read
    untransformed text, so the ``\\r`` rewrite and the reported
    ``downloaded`` / ``total`` figures are unaffected by the transform.

    When ``echo=False`` nothing is written to stderr. Progress lines
    (parseable by :func:`_parse_ytdlp_progress`) emit a compact
    ``ytdlp_progress_suppressed`` debug record with their byte accounting.
    Non-progress lines emit a single ``ytdlp_output_suppressed`` debug record
    carrying the REDACTED text (``\\n``/``\\r`` stripped), so no child output
    is silently lost without a log trace. The redaction processor in the
    structlog chain (``redact_log_event``) provides defence-in-depth on top
    of :func:`sanitize_text_for_log`.

    The transcript buffer still receives the RAW line
    (:func:`_retain_transcript_line` / ``output_chunks``): redaction here must
    not substitute U+FFFD for undecodable child bytes, and
    ``download_failed`` applies the transform at its own call site.

    Progress lines (e.g. ``[download]  40.3% of 649.37MiB ...``) are rewritten
    in place using carriage returns to restore the pre-migration behavior where
    yt-dlp used ``\\r`` for live progress updates.  Non-progress lines use
    newlines as-is.
    """
    if not echo:
        progress = _parse_ytdlp_progress(line)
        if progress is not None:
            downloaded, total = progress
            logger.debug(
                "ytdlp_progress_suppressed",
                downloaded=downloaded,
                total=total,
            )
        else:
            logger.debug(
                "ytdlp_output_suppressed",
                line=sanitize_text_for_log(line.rstrip("\n\r")),
            )
        return
    if _is_ytdlp_progress_line(line):
        text = sanitize_text_for_log(line.rstrip("\n\r"))
        width = shutil.get_terminal_size((80, 24)).columns
        sys.stderr.write("\r" + text.ljust(width)[:width] + "\r")
        sys.stderr.flush()
    else:
        sys.stderr.write(sanitize_text_for_log(line))
        sys.stderr.flush()


def _resolve_format_selector(quality_str: str) -> str:
    """Resolve a yt-dlp format selector string from a quality token.

    Every stream URL extracted from VK/OK CDN is a single-quality media
    playlist (or direct media file) carrying no height metadata, so a
    height filter such as ``best[height<=N]`` never matches and yt-dlp fails
    with "Requested format is not available". The quality is already selected
    upstream by :class:`~vkdownloader.services.quality.QualitySelector` via the
    stream URL, so here yt-dlp only needs to download the best (sole) format
    of that URL. The keyword ``worst`` selects ``worst``; everything else
    (including ``best``, ``unknown`` and any height) selects ``best``.

    This replaces the inline ternary that silently mapped ``worst`` -> ``best``
    (NET-003) and the earlier ``best[height<=N]`` filter that could not match
    a heightless media playlist.
    """
    if quality_str == "worst":
        return "worst"
    return "best"


def _build_ytdlp_cli_command(
    output_file: Path,
    quality_str: str,
    user_agent: str,
    settings: Settings,
    cookies: str | None,
    raw_cookies: list[Cookie] | None,
    *,
    workspace: DownloadWorkspace | None = None,
) -> tuple[list[str], Path | None]:
    """Build a yt-dlp CLI command list and optional temp cookie file path.

    When ``workspace`` is provided, yt-dlp routes its home/temp paths through
    ``-P`` and uses a relative output template so fragments land inside the
    workspace instead of the output root.
    """
    # Build format selector: use height filter for numeric quality, bare "best" otherwise
    format_selector = _resolve_format_selector(quality_str)

    output_template: str
    if workspace is not None:
        output_template = workspace.final_path.name.replace("%", "%%")
    else:
        output_template = str(output_file)

    cmd: list[str] = [
        sys.executable,
        "-u",  # Unbuffered stderr - critical for real-time progress passthrough with PIPE
        "-m",
        "yt_dlp",
        "--encoding",
        "utf-8",
        "-o",
        output_template,
        "-f",
        format_selector,
        "--newline",
        "--hls-prefer-native",
        "--no-warnings",
        "--ignore-config",
        "--socket-timeout",
        str(settings.download_timeout),
        "-R",
        "1",
        "--fragment-retries",
        "1",
        "--file-access-retries",
        str(_YTDLP_FILE_ACCESS_RETRIES),
        "--retry-sleep",
        f"file_access:{_YTDLP_FILE_ACCESS_RETRY_SLEEP}",
        "-N",
        str(settings.max_concurrent_segments),
        "--user-agent",
        user_agent,
        "--referer",
        "https://vkvideo.ru/",
    ]

    if workspace is not None:
        cmd.extend(["-P", f"home:{workspace.staging_dir}"])
        cmd.extend(["-P", f"temp:{workspace.ytdlp_dir}"])

    # --http-chunk-size forces range-request-based downloading of HLS segments.
    # When enabled (> 0), it can cause silent data corruption on CDNs that do not
    # properly support HTTP Range headers, producing files with corrupted segments
    # ("broken chunks in the middle"). Disabled by default (0) for reliability.
    # Only include when explicitly enabled by the user.
    if settings.http_chunk_size > 0:
        cmd.extend(["--http-chunk-size", str(settings.http_chunk_size)])

    if not settings.ssl_verify:
        cmd.append("--no-check-certificates")

    # SEC-004: Pass cookies via stdin using yt-dlp's `--cookies -` syntax so the
    # cookie file path never enters the child process argv (/proc/<pid>/cmdline).
    # The caller opens cookie_file and passes the FD as stdin to the subprocess.
    cookie_file: Path | None = None
    if raw_cookies:
        cookie_file = _create_temp_cookie_file(raw_cookies)
        cmd.extend(["--cookies", "-"])
    elif cookies:
        cookie_file = _create_temp_cookie_file(cookies)
        cmd.extend(["--cookies", "-"])

    return cmd, cookie_file


class YtdlpArtifactCompatibility(StrEnum):
    """Compatibility classification for yt-dlp resume artifacts."""

    COMPATIBLE_RESUME = "compatible_resume"
    RECOVERY_CANDIDATE = "recovery_candidate"
    AMBIGUOUS = "ambiguous"
    NONE = "none"


@dataclass(frozen=True)
class YtdlpArtifacts:
    """Track the real yt-dlp temp paths for one job."""

    directory: Path
    final_name: str

    @property
    def temp_path(self) -> Path:
        return self.directory / (self.final_name + ".part")

    @property
    def ytdl_path(self) -> Path:
        return self.directory / (self.final_name + ".ytdl")

    def fragment_paths(self) -> list[Path]:
        try:
            return sorted(
                p
                for p in self.directory.iterdir()
                if p.name.startswith(self.final_name + ".part-Frag")
            )
        except OSError:
            return []

    def has_artifacts(self) -> bool:
        try:
            if self.temp_path.exists() and self.temp_path.stat().st_size > 0:
                return True
        except OSError:
            pass
        if self.fragment_paths():
            return True
        try:
            if self.ytdl_path.exists():
                return True
        except OSError:
            pass
        return False


@dataclass(frozen=True)
class YtdlpLaunchResult:
    """Typed outcome of a single yt-dlp launch."""

    path: Path | None = None
    phase: str = "failed"
    returncode: int | None = None
    last_error_code: str | None = None
    http_status: int | None = None
    error_category: ErrorCategory = ErrorCategory.UNKNOWN
    candidate_path: Path | None = None
    file_conflict: bool = False
    cancelled: bool = False


def _ytdlp_artifacts_for(
    output_file: Path, workspace: DownloadWorkspace | None = None
) -> YtdlpArtifacts:
    if workspace is not None:
        return YtdlpArtifacts(directory=workspace.ytdlp_dir, final_name=workspace.final_path.name)
    return YtdlpArtifacts(directory=output_file.parent, final_name=output_file.name)


def _acquire_job_lock(job_lock: object | None) -> object | None:
    return job_lock


def _capture_ytdlp_artifact_snapshot(artifacts: YtdlpArtifacts, job_lock: object | None = None) -> dict[str, int] | None:
    """Capture relative artifact name -> size snapshot.

    Returns ``None`` on ``OSError``. Captured under ``job_lock`` when provided.
    """

    def _capture() -> dict[str, int] | None:
        try:
            snapshot: dict[str, int] = {}
            candidates = [artifacts.temp_path, artifacts.ytdl_path] + list(artifacts.fragment_paths())
            for path in candidates:
                try:
                    if path.exists():
                        snapshot[path.name] = int(path.stat().st_size)
                except OSError:
                    raise
            return snapshot
        except OSError:
            return None

    if job_lock is None:
        return _capture()
    if hasattr(job_lock, "__enter__") and hasattr(job_lock, "__exit__"):
        with job_lock:
            return _capture()
    acquire = getattr(job_lock, "acquire", None)
    release = getattr(job_lock, "release", None)
    if callable(acquire) and callable(release):
        acquire()
        try:
            return _capture()
        finally:
            release()
    return _capture()


# Public-ish aliases for tests/importers.
capture_artifact_snapshot = _capture_ytdlp_artifact_snapshot
capture_ytdlp_artifact_snapshot = _capture_ytdlp_artifact_snapshot
_ytdlp_artifact_snapshot = _capture_ytdlp_artifact_snapshot
_artifact_snapshot = _capture_ytdlp_artifact_snapshot


def parse_ytdl_file(path: object, *, max_bytes: int = 65536) -> dict[str, object] | None:
    """Safely parse a yt-dlp ``.ytdl`` resume hint file.

    Returns a small normalized dict containing only ``index`` and optional
    ``fragment_count``. Returns ``None`` on any validation failure. The file
    is never modified.
    """
    try:
        p = Path(str(path))
        if p.is_symlink():
            return None
        if not p.is_file():
            return None
        try:
            size = p.stat().st_size
        except OSError:
            return None
        if size > max_bytes:
            return None
        raw = p.read_bytes()
    except OSError:
        return None
    if len(raw) > max_bytes:
        return None
    try:
        text = raw.decode("utf-8")
        data = json.loads(text)
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    downloader = data.get("downloader")
    if not isinstance(downloader, dict):
        return None
    current = downloader.get("current_fragment")
    if not isinstance(current, dict):
        return None
    index = current.get("index")
    if isinstance(index, bool) or not isinstance(index, int):
        return None
    if index < 0:
        return None
    result: dict[str, object] = {"index": index}

    fragment_count: object = None
    has_fc = False
    if "fragment_count" in current:
        fragment_count = current.get("fragment_count")
        has_fc = True
    elif "fragment_count" in downloader:
        fragment_count = downloader.get("fragment_count")
        has_fc = True
    if has_fc:
        if fragment_count is None:
            # Treat missing as absent; but if key present with None reject.
            return None
        if isinstance(fragment_count, bool) or not isinstance(fragment_count, int):
            return None
        if fragment_count < index:
            return None
        result["fragment_count"] = fragment_count
    return result


def _has_repeated_ytdlp_blocks(path: object, *, block_size: int = 65536) -> bool:
    """Return True when the initial block appears again later in *path*."""
    try:
        p = Path(str(path))
        if p.is_symlink() or not p.is_file():
            return False
        with open(p, "rb") as handle:
            first = handle.read(block_size)
            if not first:
                return False
            rest = handle.read()
        return first in rest
    except OSError:
        return False


def _owned_ytdlp_guard_failure(output_file: Path, workspace: object) -> bool:
    """Return True if ownership guards fail."""
    try:
        from .workspace import (
            is_owned_ytdlp_artifact_path,
            resolve_owned_job_root,
            resolve_owned_ytdlp_dir,
        )
    except Exception:  # noqa: BLE001
        return True
    if workspace is None:
        return True
    try:
        root = resolve_owned_job_root(workspace)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return True
    if root is None:
        return True
    try:
        ytdlp_dir = resolve_owned_ytdlp_dir(workspace)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        return True
    if ytdlp_dir is None:
        return True
    artifacts = _ytdlp_artifacts_for(output_file, cast("DownloadWorkspace", workspace))
    try:
        if artifacts.final_name != cast("DownloadWorkspace", workspace).final_path.name:
            return True
    except Exception:  # noqa: BLE001
        return True
    candidates = []
    try:
        candidates = [artifacts.temp_path, artifacts.ytdl_path] + list(artifacts.fragment_paths())
    except Exception:  # noqa: BLE001
        return True
    for cand in candidates:
        try:
            if cand.exists():
                if not is_owned_ytdlp_artifact_path(cand, artifacts, cast("DownloadWorkspace", workspace)):
                    return True
        except OSError:
            return True
    return False


def classify_ytdlp_artifacts(
    output_file: Path,
    workspace: object = None,
    *,
    state_machine: object = None,
    stream_variant_id: object = None,
    playlist_fingerprint: object = None,
    init_map_sha256: object = None,
    job_lock: object = None,
) -> YtdlpArtifactCompatibility:
    """Classify yt-dlp artifacts for resume compatibility."""
    artifacts = _ytdlp_artifacts_for(output_file, cast("DownloadWorkspace", workspace))

    # No artifacts at all -> NONE.
    try:
        has = artifacts.has_artifacts()
    except Exception:  # noqa: BLE001
        has = False
    if not has:
        return YtdlpArtifactCompatibility.NONE

    # Legacy / no workspace: conservative (unowned) -> AMBIGUOUS.
    if workspace is None:
        return YtdlpArtifactCompatibility.AMBIGUOUS

    # Ownership guards first.
    if _owned_ytdlp_guard_failure(output_file, workspace):
        return YtdlpArtifactCompatibility.AMBIGUOUS

    # Resolve expected identity.
    expected_variant = stream_variant_id
    expected_fingerprint = playlist_fingerprint
    expected_init = init_map_sha256
    if expected_variant is None and state_machine is not None:
        try:
            sm_state = getattr(state_machine, "job_state", None)
            expected_variant = getattr(sm_state, "artifact_stream_variant_id", None)
            if not expected_variant:
                expected_variant = getattr(sm_state, "stream_variant_id", None)
        except Exception:  # noqa: BLE001
            expected_variant = None
    if expected_fingerprint is None and state_machine is not None:
        try:
            sm_state = getattr(state_machine, "job_state", None)
            expected_fingerprint = getattr(sm_state, "artifact_playlist_fingerprint", None)
        except Exception: # noqa: BLE001
            expected_fingerprint = None
    if expected_init is None and state_machine is not None:
        try:
            sm_state = getattr(state_machine, "job_state", None)
            expected_init = getattr(sm_state, "artifact_init_map_sha256", None)
        except Exception:  # noqa: BLE001
            expected_init = None

    if not isinstance(expected_variant, str) or not expected_variant.strip():
        return YtdlpArtifactCompatibility.AMBIGUOUS
    if not isinstance(expected_fingerprint, str) or not expected_fingerprint.strip():
        return YtdlpArtifactCompatibility.AMBIGUOUS

    # Compare to persisted identity fields when present.
    if state_machine is not None:
        try:
            sm_state = getattr(state_machine, "job_state", None)
            persisted_variant = getattr(sm_state, "artifact_stream_variant_id", None)
            if persisted_variant is None:
                persisted_variant = getattr(sm_state, "stream_variant_id", None)
            persisted_fp = getattr(sm_state, "artifact_playlist_fingerprint", None)
            persisted_init = getattr(sm_state, "artifact_init_map_sha256", None)
        except Exception:  # noqa: BLE001
            persisted_variant = None
            persisted_fp = None
            persisted_init = None
        if persisted_variant is not None and persisted_variant != expected_variant:
            return YtdlpArtifactCompatibility.AMBIGUOUS
        if persisted_fp is not None and persisted_fp != expected_fingerprint:
            return YtdlpArtifactCompatibility.AMBIGUOUS
        if (
            persisted_init is not None
            and expected_init is not None
            and persisted_init != expected_init
        ):
            return YtdlpArtifactCompatibility.AMBIGUOUS

    # Inspect .ytdl if present.
    ytdl_path = artifacts.ytdl_path
    ytdl_present = False
    ytdl_index = 0
    try:
        if ytdl_path.exists():
            ytdl_present = True
    except OSError:
        return YtdlpArtifactCompatibility.AMBIGUOUS
    if ytdl_present:
        parsed = parse_ytdl_file(ytdl_path)
        if parsed is None:
            return YtdlpArtifactCompatibility.AMBIGUOUS
        ytdl_index = int(cast("int", parsed.get("index", 0)))
        fc = parsed.get("fragment_count")
        if isinstance(fc, int) and fc < ytdl_index:
            return YtdlpArtifactCompatibility.AMBIGUOUS

    # Repeated TS blocks -> AMBIGUOUS.
    temp_path = artifacts.temp_path
    part_non_empty = False
    try:
        if temp_path.exists() and temp_path.is_file():
            try:
                if temp_path.stat().st_size > 0:
                    part_non_empty = True
            except OSError:
                return YtdlpArtifactCompatibility.AMBIGUOUS
            if _has_repeated_ytdlp_blocks(temp_path):
                return YtdlpArtifactCompatibility.AMBIGUOUS
    except OSError:
        return YtdlpArtifactCompatibility.AMBIGUOUS

    try:
        if temp_path.exists() and temp_path.is_file() and temp_path.stat().st_size == 0 and ytdl_present and ytdl_index > 0:
            return YtdlpArtifactCompatibility.AMBIGUOUS
    except OSError:
        return YtdlpArtifactCompatibility.AMBIGUOUS

    # fragments count as artifacts
    try:
        if artifacts.fragment_paths():
            part_non_empty = True
    except Exception:  # noqa: BLE001
        pass

    if ytdl_present:
        if part_non_empty:
            return YtdlpArtifactCompatibility.COMPATIBLE_RESUME
        return YtdlpArtifactCompatibility.RECOVERY_CANDIDATE
    if part_non_empty:
        return YtdlpArtifactCompatibility.RECOVERY_CANDIDATE
    return YtdlpArtifactCompatibility.NONE


_classify_ytdlp_artifacts = classify_ytdlp_artifacts


def _has_recoverable_ytdlp_artifacts(
    output_file: Path, workspace: DownloadWorkspace | None = None, **kwargs: object
) -> bool:
    """Report whether yt-dlp artifacts are recoverable (compatible_resume)."""
    state_machine = kwargs.pop("state_machine", None)
    stream_variant_id = kwargs.pop("stream_variant_id", None)
    playlist_fingerprint = kwargs.pop("playlist_fingerprint", None)
    init_map_sha256 = kwargs.pop("init_map_sha256", None)
    job_lock = kwargs.pop("job_lock", None)
    segments_fallback = False
    for key in (
        "allow_segments",
        "segments_fallback",
        "check_segments",
        "include_segments",
        "segments_dir_check",
    ):
        if kwargs.pop(key, False):
            segments_fallback = True

    # Legacy (no workspace) layout preserves the previous existence-based behavior.
    if workspace is None:
        art = _ytdlp_artifacts_for(output_file, None)
        if art.has_artifacts():
            return True
        if segments_fallback:
            segments_dir = Path(output_file).parent / f".{Path(output_file).stem}_segments"
            try:
                if segments_dir.exists() and any(segments_dir.iterdir()):
                    return True
            except OSError:
                pass
        return False

    compat = classify_ytdlp_artifacts(
        output_file,
        workspace,
        state_machine=state_machine,
        stream_variant_id=stream_variant_id,
        playlist_fingerprint=playlist_fingerprint,
        init_map_sha256=init_map_sha256,
        job_lock=job_lock,
    )
    if compat == YtdlpArtifactCompatibility.COMPATIBLE_RESUME:
        return True
    if segments_fallback:
        segments_dir = workspace.segments_dir
        try:
            if segments_dir.exists() and any(segments_dir.iterdir()):
                return True
        except OSError:
            pass
    return False


async def download_with_ytdlp_with_resume_fallback(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    extractor: VKVideoExtractor | None,
    settings: Settings | None = None,
    cookies: str | None = None,
    raw_cookies: list[Cookie] | None = None,
    *,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    progress_snapshot_callback: Callable[[str, object], None] | None = None,
    echo: bool = True,
    diagnostic_sink: object | None = None,
    attempt_id: int | None = None,
    workspace: DownloadWorkspace | None = None,
    stream_variant_id: str | None = None,
    stream_binding: object | None = None,
    state_machine: DownloadStateMachine | None = None,
    job_lock: object | None = None,
) -> Path | None:
    """
    Flow:
    1. Try yt-dlp download
    2. On failure with partial file: get fresh token via browser + switch to segment download
     3. Falls back to a fresh segment-based download via HLS; the partial yt-dlp
     artifacts are preserved for resume.

    Args:
        video_url: Original VK video URL.
        m3u8_url: HLS playlist URL (may be stale).
        output_file: Output file path.
        quality: Quality token (``best``, ``worst``, ``unknown``, or a height in
            pixels the video offers, e.g. ``1072``).
        extractor: VKVideoExtractor for token refresh.
        settings: Application settings.
        cookies: Optional cookies string for ffmpeg headers.
        raw_cookies: Optional raw Cookie objects for Netscape format (preserves domain).
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
            Used both for inter-retry backoff between yt-dlp attempts and for
            coordinating backoff during segment-resume fallback.
        video_semaphore: The batch video permit the caller already holds (one permit per
            video, acquired once in ``perform_download``). This is the batch-level
            semaphore, **not** the segment-level one: the segment fan-out is deliberately
            NOT gated by it and is bounded by a semaphore the segment layer owns. Re-
            acquiring from this non-reentrant semaphore per segment would deadlock (D-01).
            When ``None`` (single-download mode), no video-level permit is in effect.
        progress_callback: Optional callback for per-URL segment progress (video_id, downloaded, total).
        echo: When False, suppresses yt-dlp's native console echo (progress lines
            are emitted at DEBUG level instead; non-progress lines are dropped).
            Only governs yt-dlp output - has no effect on the ffmpeg or segment paths.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    if settings is None:
        settings = Settings()

    shutdown_event = get_shutdown_event()
    retry_count = 0

    if state_machine is None:
        try:
            from .state_machine import DownloadStateMachine

            job_id = None
            if workspace is not None:
                job_id = getattr(workspace, "job_id", None)
                try:
                    from .workspace import acquire_job_lock

                    with acquire_job_lock(workspace, timeout=10.0):
                        from .state_migration import migrate_legacy_state

                        migrate_legacy_state(workspace)
                except Exception:  # noqa: BLE001
                    pass
            if job_id is None:
                from .workspace import stable_job_id

                job_id = stable_job_id(
                    _extract_video_id(video_url) if video_url else output_file.stem,
                    str(quality),
                    (workspace.final_path.name if workspace is not None else output_file.name),
                )
            state_machine = DownloadStateMachine.create(
                job_id=job_id,
                quality_requested=quality,
                workspace=workspace,
            )
        except Exception:  # noqa: BLE001
            state_machine = None

    # Advance state machine to the download phase.
    if state_machine is not None:
        for _target in (DownloadState.RESOLVE_STREAM, DownloadState.DOWNLOAD):
            try:
                if state_machine.can_transition(_target):
                    state_machine.transition(_target)
            except Exception:  # noqa: BLE001
                pass

    # Advance state machine to the download phase.
    if state_machine is not None:
        for _target in (DownloadState.RESOLVE_STREAM, DownloadState.DOWNLOAD):
            try:
                if state_machine.can_transition(_target):
                    state_machine.transition(_target)
            except Exception:  # noqa: BLE001
                pass

    # Resume reconciliation before backend starts.
    if workspace is not None:
        try:
            from .state_machine import CommitRecoveryDirective, DownloadStateMachine

            if state_machine is None:
                try:
                    state_machine = DownloadStateMachine.load(workspace, job_id=workspace.job_id)
                except Exception:  # noqa: BLE001
                    state_machine = None
            expected_height = None
            try:
                expected_height = int(str(quality).rstrip("p"))
            except TypeError, ValueError:
                expected_height = None
            from .state_migration import reconcile_commit_state

            directive, usable = await reconcile_commit_state(
                workspace, state_machine, expected_height=expected_height
            )
            if directive == CommitRecoveryDirective.ALREADY_COMMITTED and usable is not None:
                return usable
            if directive == CommitRecoveryDirective.PUBLISH_STAGING and usable is not None:
                try:
                    from .ffmpeg_utils import check_ffprobe_available
                    from .media_validation import validate_media_file
                    from .workspace import (
                        acquire_publish_lock,
                        cleanup_owned_job_artifacts,
                        publish_verified_file,
                    )

                    if not check_ffprobe_available():
                        logger.error("ffprobe_missing", path=str(usable))
                        return None
                    await validate_media_file(usable, expected_height=expected_height)
                    final_lock = acquire_publish_lock(workspace.final_path, 10.0)

                    _safe_transition(state_machine, DownloadState.ATOMIC_NO_CLOBBER_PUBLICATION)
                    publish_verified_file(usable, workspace.final_path, final_lock=final_lock)
                    await validate_media_file(workspace.final_path, expected_height=expected_height)
                    if not (
                        workspace.final_path.exists()
                        and workspace.final_path.is_file()
                        and workspace.final_path.stat().st_size > 0
                    ):
                        return None
                    _safe_transition(state_machine, DownloadState.FINAL_COMMITTED)
                    _safe_transition(state_machine, DownloadState.CLEANUP_OWNED_TEMP_ARTIFACTS)
                    cleanup_owned_job_artifacts(workspace)
                    return workspace.final_path
                except asyncio.CancelledError, KeyboardInterrupt:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning("publish_staging_failed", error=str(exc))
                    return None
        except asyncio.CancelledError, KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.debug("reconcile_failed", error=str(exc))

    while retry_count <= settings.max_retries:
        result = await _download_with_ytdlp_result(
            video_url,
            m3u8_url,
            output_file,
            quality,
            settings,
            cookies,
            raw_cookies,
            progress_callback,
            progress_snapshot_callback=progress_snapshot_callback,
            echo=echo,
            diagnostic_sink=diagnostic_sink,
            attempt_id=attempt_id,
            workspace=workspace,
            state_machine=state_machine,
        )

        if result is not None and result.path is not None:
            if retry_count > 0:
                logger.info("download_completed_after_retries", retries=retry_count)
            return result.path

        if result is not None and result.cancelled:
            if state_machine is not None:
                try:
                    state_machine.record_cancellation()
                except Exception:  # noqa: BLE001
                    pass
            return None

        # Terminal local outcomes: file lock or staging candidate failure.
        if result is not None and (
            result.file_conflict
            or result.error_category == ErrorCategory.FILE_LOCKED
            or result.phase in {"file_locked", "local_block", "missing_output"}
        ):
            if state_machine is not None:
                try:
                    reason_code = (
                        "file_lock_conflict"
                        if result.file_conflict or result.error_category == ErrorCategory.FILE_LOCKED or result.phase == "file_locked"
                        else "staging_candidate_failed"
                    )
                    _ec = result.error_category
                    # Persist without a state transition that may be illegal.
                    state_machine.job_state.reason_code = reason_code
                    state_machine.job_state.error_category = _ec
                    state_machine.job_state.updated_at = __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
                    state_machine.persist()
                except Exception:  # noqa: BLE001
                    pass
            return None

        retry_count += 1

        if shutdown_event.is_set():
            if state_machine is not None:
                state_machine.record_cancellation()
            logger.info(
                "yt_dlp_download_cancelled",
                url=_strip_auth_params(video_url),
            )
            return None

        # Backoff between yt-dlp retry attempts:
        # Without this, the retry loop hammers the VK origin on failure.
        # Use _compute_backoff_delay with a 500 base status (yt-dlp failures
        # don't carry an HTTP status at this level); _wait_with_shutdown
        # respects the shared URLBackoffCoordinator's pause state if one is
        # provided, and allows interruption via the shutdown event.
        backoff_delay = _compute_backoff_delay(500, retry_count, None)
        if state_machine is not None:
            allowed = state_machine.record_retry("yt-dlp", "ytdlp_retry", backoff_delay)
            if not allowed:
                try:
                    state_machine.transition(
                        DownloadState.FAILED_RETRY_BUDGET,
                        reason_code="retry_budget_exhausted",
                        error_category=ErrorCategory.UNKNOWN,
                    )
                except Exception:  # noqa: BLE001
                    pass
                return None
        if backoff_coordinator is not None:
            await backoff_coordinator.wait_if_paused(video_url)
        shutdown_triggered = await _wait_with_shutdown(
            backoff_delay,
            shutdown_event,
            retry_count,
            _strip_auth_params(video_url),
        )
        if shutdown_triggered:
            if state_machine is not None:
                state_machine.record_cancellation()
            logger.info(
                "yt_dlp_download_cancelled_during_backoff", url=_strip_auth_params(video_url)
            )
            return None

        # Check for partial file - switch to segment download with fresh token.
        # yt-dlp writes to <output>.part until the download completes, so we
        # probe for recoverable artifacts, not just the .part file (Block B).
        validated_output = validate_output_path(output_file)
        if workspace is None:
            if not _has_recoverable_ytdlp_artifacts(validated_output, None, allow_segments=True, segments_fallback=True):
                return None
        else:
            expected_variant = stream_variant_id
            expected_fingerprint = None
            expected_init = None
            if state_machine is not None:
                try:
                    if expected_variant is None:
                        expected_variant = state_machine.job_state.stream_variant_id
                    expected_fingerprint = state_machine.job_state.artifact_playlist_fingerprint
                    expected_init = state_machine.job_state.artifact_init_map_sha256
                except Exception:  # noqa: BLE001
                    pass
            compat = classify_ytdlp_artifacts(
                validated_output,
                workspace,
                state_machine=state_machine,
                stream_variant_id=expected_variant,
                playlist_fingerprint=expected_fingerprint,
                init_map_sha256=expected_init,
                job_lock=job_lock,
            )
            try:
                if state_machine is not None:
                    state_machine.job_state.artifact_classification = compat.value
                    if not state_machine.job_state.artifact_generation:
                        state_machine.job_state.artifact_generation = "gen-0"
                    if expected_variant and not state_machine.job_state.artifact_stream_variant_id:
                        state_machine.job_state.artifact_stream_variant_id = expected_variant
                    if expected_fingerprint and not state_machine.job_state.artifact_playlist_fingerprint:
                        state_machine.job_state.artifact_playlist_fingerprint = expected_fingerprint
                    if expected_init and not state_machine.job_state.artifact_init_map_sha256:
                        state_machine.job_state.artifact_init_map_sha256 = expected_init
                    state_machine.persist()
            except Exception:  # noqa: BLE001
                pass

            if compat == YtdlpArtifactCompatibility.AMBIGUOUS:
                try:
                    from .checkpoint import quarantine_generation

                    old_gen = "gen-0"
                    if state_machine is not None:
                        old_gen = state_machine.job_state.artifact_generation or old_gen
                    num = 0
                    if isinstance(old_gen, str) and old_gen.startswith("gen-"):
                        try:
                            num = int(old_gen.split("-", 1)[1])
                        except (TypeError, ValueError):
                            num = 0
                    new_gen = f"gen-{num + 1}"
                    quarantine_generation(workspace.ytdlp_dir, old_gen)
                    workspace.ytdlp_dir.mkdir(parents=True, exist_ok=True)
                    if state_machine is not None:
                        state_machine.job_state.artifact_generation = new_gen
                        state_machine.job_state.reason_code = "ytdlp_artifacts_quarantined"
                        state_machine.persist()
                except Exception:  # noqa: BLE001
                    if state_machine is not None:
                        try:
                            state_machine.job_state.reason_code = "artifact_isolation_failed"
                            state_machine.job_state.error_category = ErrorCategory.INTEGRITY_FAILURE
                            state_machine.persist()
                        except Exception:  # noqa: BLE001
                            pass
                    return None
                return None

            if compat != YtdlpArtifactCompatibility.COMPATIBLE_RESUME:
                # Preserve recovery candidates / none; do not append to unproven .part.
                return None

        # Attempt segment resume with fresh token
        if state_machine is not None:
            try:
                if state_machine.can_transition(DownloadState.REFRESH_STREAM):
                    state_machine.transition(
                        DownloadState.REFRESH_STREAM, reason_code="segment_resume"
                    )
            except Exception:  # noqa: BLE001
                pass
        if (
            segment_result := await _attempt_segment_resume(
                video_url,
                m3u8_url,
                validated_output,
                quality,
                retry_count,
                extractor,
                settings,
                backoff_coordinator,
                video_semaphore,
                progress_callback,
                progress_snapshot_callback=progress_snapshot_callback,
                workspace=workspace,
                stream_variant_id=stream_variant_id,
                stream_binding=stream_binding,
                state_machine=state_machine,
            )
        ) is not None:
            return segment_result

    # All retries exhausted without success
    logger.error(
        "max_retries_exceeded",
        url=_strip_auth_params(video_url),
        retries=settings.max_retries,
    )
    # Block B: preserve partials (.part, fragments, .ytdl) for resume.
    logger.info("preserving_ytdlp_partials", path=str(validated_output))
    return None


async def _attempt_segment_resume(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    retry_count: int,
    extractor: VKVideoExtractor | None,
    settings: Settings,
    backoff_coordinator: URLBackoffCoordinator | None,
    video_semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    progress_snapshot_callback: Callable[[str, object], None] | None = None,
    workspace: DownloadWorkspace | None = None,
    stream_variant_id: str | None = None,
    stream_binding: object | None = None,
    state_machine: DownloadStateMachine | None = None,
    job_lock: object | None = None,
) -> Path | None:
    """Attempt segment-based download with fresh token on yt-dlp failure.

    Called when yt-dlp fails and partial file exists. Forces browser extraction
    to get fresh token, then falls back to a fresh segment-based download via HLS.
    Partial yt-dlp artifacts (.part, fragments, .ytdl) are PRESERVED; the segment
    backend runs in its own workspace and leaves the original artifact untouched.

    Args:
        video_url: Original VK video URL.
        m3u8_url: HLS playlist URL (may be stale).
        output_file: Output file path (partial file is preserved, segment download starts fresh).
        quality: Quality token (``best``, ``worst``, ``unknown``, or a height in
            pixels the video offers, e.g. ``1072``).
        retry_count: Current retry attempt number.
        extractor: VKVideoExtractor for token refresh.
        settings: Application settings.
        backoff_coordinator: Optional shared URLBackoffCoordinator.
        video_semaphore: The batch video permit the caller already holds (one permit per
            video, acquired once in ``perform_download``). The segment fan-out is NOT
            gated by it; the segment layer owns its own semaphore (D-01).
        progress_callback: Optional callback for per-URL segment progress.

    Returns:
        Path to downloaded file on success, None on failure.

    Raises:
        QualityNotAvailableError: If the requested height is absent from the
            refreshed browser streams.
        QualityParseError: If ``quality`` is neither a keyword nor a positive
            height; logged and re-raised so the caller reports it verbatim.
    """
    if state_machine is None:
        try:
            from .state_machine import DownloadStateMachine

            job_id = None
            if workspace is not None:
                job_id = getattr(workspace, "job_id", None)
                try:
                    from .workspace import acquire_job_lock

                    with acquire_job_lock(workspace, timeout=10.0):
                        from .state_migration import migrate_legacy_state

                        migrate_legacy_state(workspace)
                except Exception:  # noqa: BLE001
                    pass
            if job_id is None:
                from .workspace import stable_job_id

                job_id = stable_job_id(
                    _extract_video_id(video_url) if video_url else output_file.stem,
                    str(quality),
                    output_file.name,
                )
            state_machine = DownloadStateMachine.create(
                job_id=job_id,
                quality_requested=quality,
                workspace=workspace,
            )
        except Exception:  # noqa: BLE001
            state_machine = None

    temp_file = _ytdlp_artifacts_for(output_file).temp_path
    try:
        partial_size = temp_file.stat().st_size if temp_file.exists() else 0
    except OSError:
        partial_size = 0
    logger.warning(
        "download_interrupted_switching_to_segments",
        url=_strip_auth_params(video_url),
        path=str(output_file),
        size=partial_size,
        retry=retry_count,
    )
    logger.info("attempting_segment_resume", retry=retry_count)

    try:
        if extractor is None:
            extractor = VKVideoExtractor(settings=settings, backoff_coordinator=backoff_coordinator)
        try:
            from ..models.enums import CookieSource

            if getattr(extractor, "settings", None) is not None:
                extractor.settings.cookie_source = CookieSource.BROWSER
        except Exception:  # noqa: BLE001
            pass
        try:
            binding = await refresh_stream(video_url, quality, None, extractor)
        except QualityMismatchError as exc:
            logger.error(
                "requested_quality_mismatch_in_browser_streams",
                url=_strip_auth_params(video_url),
                quality=quality,
                available=["best"] + (getattr(exc, "available", []) or []),
            )
            raise
        except QualityNotAvailableError as exc:
            logger.error(
                "requested_quality_not_available_in_browser_streams",
                url=_strip_auth_params(video_url),
                quality=quality,
                available=["best"] + (getattr(exc, "available", []) or []),
            )
            raise
        m3u8_url = binding.media_playlist_url
        if state_machine is not None:
            try:
                requested = str(quality).strip()
                quality_match = True
                if requested.isdecimal():
                    quality_match = getattr(binding, "actual_height", None) == int(requested)
                variant_match = True
                prev_variant = getattr(stream_binding, "variant_id", None)
                if prev_variant is not None:
                    variant_match = getattr(binding, "variant_id", None) == prev_variant
                if not (quality_match and variant_match):
                    try:
                        state_machine.transition(
                            DownloadState.PRESERVE_AND_STOP,
                            reason_code="refresh_mismatch",
                            error_category=ErrorCategory.INTEGRITY_FAILURE,
                        )
                    except Exception:  # noqa: BLE001
                        pass
                    return None
                state_machine.record_refresh_completed(
                    quality_match=quality_match, variant_match=variant_match
                )
            except Exception:  # noqa: BLE001
                pass
        cookies = binding.cookies if isinstance(binding.cookies, str) else None
        stream_variant_id = binding.variant_id
        logger.info(
            "fresh_token_obtained_for_resume",
            quality=quality,
            selected_quality=quality,
        )
        # Preserve the yt-dlp partial; do NOT unlink it. The segment backend
        # runs in its own workspace and leaves the original artifact untouched.
        # Continue to segment download
        return await download_hls_with_resume(
            HLSDownloadRequest(
                video_url=video_url,
                m3u8_url=m3u8_url,
                output_file=output_file,
                quality=quality,
                cookies=SecretStr(cookies) if isinstance(cookies, str) and cookies else None,
                progress_callback=progress_callback,
                stream_variant_id=stream_variant_id,
                stream_binding=binding,
            ),
            settings=settings,
            extractor=extractor,
            backoff_coordinator=backoff_coordinator,
            video_semaphore=video_semaphore,
            workspace=workspace,
            stream_variant_id=stream_variant_id,
            stream_binding=binding,
            state_machine=state_machine,
            progress_snapshot_callback=progress_snapshot_callback,
        )
    except ExtractionError as e:
        # TRN-008 / B13 arm (d): narrowed from (ExtractionError, OSError).
        # A FileNotFoundError from the merge is an OSError, but arm (b) now
        # catches it at the merge level and produces a record there; it must
        # NOT be swallowed here and relabeled as a token problem. Only a
        # genuine ExtractionError (token refresh failure) reaches this arm.
        logger.warning(
            "failed_to_refresh_token",
            url=_strip_auth_params(video_url),
            error=str(e),
        )
    except QualityParseError as e:
        # QualitySpec.parse() rejects a token that is neither a keyword nor a
        # height. Surfaced (not swallowed) so the caller reports it verbatim.
        logger.error(
            "invalid_quality_for_browser_streams",
            url=_strip_auth_params(video_url),
            error=str(e),
        )
        raise

    return None


def _derive_last_error_code(sanitized_tail: str) -> str | None:
    """Derive a machine-readable error code from a sanitized child tail.

    Prefers an explicit HTTP status reported by yt-dlp (e.g.
    ``HTTP Error 403: Forbidden``); falls back to a bare 4xx/5xx status
    token. Returns ``None`` when no code can be determined.
    """
    for pattern in (
        r"HTTP Error\s+(\d{3})",
        r"HTTP\s+(\d{3})",
        r"(?:status|status code|http status)[:\s=]+(\d{3})",
    ):
        match = re.search(pattern, sanitized_tail, re.IGNORECASE)
        if match is not None:
            return match.group(1)
    match = re.search(r"ERROR:\s*(\d{3})\b", sanitized_tail)
    if match is not None:
        return match.group(1)
    return None


# ``download_failed`` record, so only a bounded *tail* of the child's output
# is retained. The tail is the informative part of a failure; the head is not.
# Sized against the reader's per-line limit (``asyncio.streams._DEFAULT_LIMIT``
# = 64 KiB) so a full line always fits, and against the merge-error truncation
# precedent in ffmpeg_utils.py (``error[:200]``). It is deliberately not a
# Setting: TRN-013 was rejected upstream for adding configuration knobs to
# this class of buffer. In batch mode a chatty child would otherwise multiply
# this bound across ``max_concurrent_downloads`` (up to 16).
_MAX_CHILD_OUTPUT_BYTES = 64 * 1024


def _retain_transcript_line(output: bytearray, line: bytes) -> None:
    """Append ``line`` to the bounded transcript, keeping only the tail.

    Every byte is appended first; only the oldest bytes are trimmed from the
    front once the running total exceeds ``_MAX_CHILD_OUTPUT_BYTES``. No line
    is silently skipped. Retaining the tail ensures the ``download_failed``
    record carries the end of the child's output -- the reason it failed --
    not its beginning (TRN-011).
    """
    output.extend(line)
    if len(output) > _MAX_CHILD_OUTPUT_BYTES:
        del output[: len(output) - _MAX_CHILD_OUTPUT_BYTES]


def _ytdlp_candidate_path(output_file: Path, workspace: DownloadWorkspace | None = None) -> Path | None:
    """Return a non-empty staging candidate path when available."""
    if workspace is not None:
        candidate = workspace.staging_dir / workspace.final_path.name
    else:
        candidate = Path(output_file)
    try:
        if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    except OSError:
        pass
    # Fall back to yt-dlp .part artifact when present.
    try:
        art = _ytdlp_artifacts_for(output_file, workspace)
        if art.temp_path.exists() and art.temp_path.is_file() and art.temp_path.stat().st_size > 0:
            return art.temp_path
    except OSError:
        pass
    return None


async def _download_with_ytdlp_result(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    settings: Settings,
    cookies: str | None = None,
    raw_cookies: list[Cookie] | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    progress_snapshot_callback: Callable[[str, object], None] | None = None,
    *,
    echo: bool = True,
    diagnostic_sink: object | None = None,
    attempt_id: int | None = None,
    workspace: DownloadWorkspace | None = None,
    state_machine: DownloadStateMachine | None = None,
    job_lock: object | None = None,
) -> YtdlpLaunchResult:
    """Download video using yt-dlp via subprocess.

    Uses ``asyncio.create_subprocess_exec`` instead of ``run_in_executor``
    so the yt-dlp process can be properly terminated (SIGTERM -> SIGKILL)
    on cancellation or shutdown. yt-dlp has its own ``--socket-timeout``,
    ``-R`` (retries), ``--fragment-retries``, and ``-N`` (concurrent
    fragments) for network robustness - no application-level download
    timeout is imposed, avoiding premature kill of legitimate long downloads.
    A download that keeps producing output is never killed, no matter how
    long it runs. Only the **inactivity** of the stream - the one-shot reap
    applied after the reader has consumed every line and the child has gone
    silent - is bounded by ``download_stall_timeout``: on expiry the child is
    terminated through the cancellation ladder (``cancel_subprocess``) and
    the resulting ``TimeoutError`` is re-raised. This is not a whole-operation
    budget (see ``download_timeout`` for the per-request and per-subprocess
    bounds that are), and it does not apply to the merge subprocesses, which
    ``download_timeout`` already bounds.

    Args:
        video_url: VK video URL to download.
        m3u8_url: HLS manifest URL passed as yt-dlp's target argument.
        output_file: Path to save the downloaded video.
        quality: Quality token (``best``, ``worst``, ``unknown``, or a height in
            pixels the video offers, e.g. ``1072``).
        settings: Application settings.
        cookies: Optional cookies string for backward compatibility.
        raw_cookies: Optional raw Cookie objects for Netscape format.
        progress_callback: Optional callback for per-URL progress updates.
        echo: When False, suppresses yt-dlp's native console echo (progress lines
            are emitted at DEBUG level instead; non-progress lines are dropped).
            Only governs yt-dlp output - has no effect on the ffmpeg or segment paths.

    Returns:
        Path to the output file on success, None on failure.
    """
    try:
        from ..utils.correlation import (
            bind_correlation_id,
            clear_correlation_id,
            generate_correlation_id,
            get_correlation_id,
        )

        _correlation_id = get_correlation_id() or generate_correlation_id()
        bind_correlation_id(_correlation_id)
    except Exception:  # noqa: BLE001
        _correlation_id = None

    logger.info(
        "starting_ytdlp_download",
        url=_strip_auth_params(m3u8_url),
        output=str(output_file),
        quality=quality,
        attempt_id=attempt_id,
        correlation_id=_correlation_id,
    )

    quality_str = quality.replace("p", "") if quality else "720"
    user_agent = settings.user_agent
    video_id = _extract_video_id(video_url)
    shutdown_event = get_shutdown_event()
    started_at = time.monotonic()

    if not settings.ssl_verify:
        logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))

    cmd, cookie_file = _build_ytdlp_cli_command(
        output_file,
        quality_str,
        user_agent,
        settings,
        cookies,
        raw_cookies,
        workspace=workspace,
    )
    logger.info(
        "ytdlp_format_selected",
        url=_strip_auth_params(m3u8_url),
        format_selector=_resolve_format_selector(quality_str),
        quality=quality_str,
    )
    # SEC-002: the signed playlist URL is written to a private temp file and
    # passed via --batch-file so it never appears in the child's argv. Cookies
    # keep using stdin (--cookies -), avoiding any stdin conflict.
    batch_file: Path | None = None

    # yt-dlp writes progress and most output to stdout by default (confirmed
    # empirically). Using stdout=PIPE + stderr=STDOUT merges all output into a
    # single stream, avoiding dual-pipe deadlock complexity while preserving
    # error messages for structured logging on failure.
    # SEC-004: Pass cookies via stdin (yt-dlp's `--cookies -`) instead of
    # `--cookies <path>`, so the cookie file path never appears in argv.
    cookie_stdin: IO[str] | None = None
    process: asyncio.subprocess.Process | None = None
    try:
        batch_file = _create_temp_batch_file(m3u8_url)
        cmd.extend(["--batch-file", str(batch_file)])

        spawn_kwargs: dict[str, object] = {
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.STDOUT,
            **_SPAWN_BOUNDARY_KWARGS,
        }
        if cookie_file is not None:
            cookie_stdin = open(cookie_file)
            spawn_kwargs["stdin"] = cookie_stdin
        _artifacts = _ytdlp_artifacts_for(output_file, workspace)
        _snapshot_before = _capture_ytdlp_artifact_snapshot(_artifacts, job_lock)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            **spawn_kwargs,  # type: ignore[arg-type]
        )

        _launch_number = next(_YTDLP_LAUNCH_COUNTER)
        try:
            _phase = getattr(state_machine, "state", None)
            _phase = str(_phase) if _phase is not None else "downloading"
        except Exception:  # noqa: BLE001
            _phase = "downloading"
        _next_action = "read_stdout"
        _effective_settings = {
            "N": int(getattr(settings, "max_concurrent_segments", 0)),
            "throttled_rate": int(getattr(settings, "throttled_rate", 0)),
            "ignore_config": "--ignore-config" in cmd,
        }
        logger.info(
            "child_started",
            pid=process.pid,
            launch_number=_launch_number,
            attempt_number=attempt_id if attempt_id is not None else 0,
            attempt_id=attempt_id,
            phase=_phase,
            next_action=_next_action,
            artifact_snapshot=_snapshot_before,
            settings=_effective_settings,
            correlation_id=_correlation_id,
        )

        output_chunks: bytearray = bytearray()

        async def _on_shutdown() -> None:
            if not await cancel_subprocess(process) and process.returncode is None:
                logger.warning(
                    "yt_dlp_cancel_not_clean",
                    pid=process.pid,
                    url=_strip_auth_params(video_url),
                )

        async def _monitor_progress() -> None:
            """Read stdout, parse yt-dlp progress, invoke callback."""
            assert process.stdout is not None
            progress_state: ProgressState | None = None
            try:
                async for line in iter_process_lines(
                    process.stdout, shutdown_event, on_shutdown=_on_shutdown
                ):
                    decoded = line.decode(errors="replace")
                    _echo_ytdlp_line(decoded, echo=echo)
                    _retain_transcript_line(output_chunks, line)
                    if diagnostic_sink is not None:
                        try:
                            getattr(diagnostic_sink, "write_line", lambda *a, **k: None)(
                                decoded, is_progress=_is_ytdlp_progress_line(decoded)
                            )
                        except Exception:
                            pass
                    progress_state = _parse_ytdlp_progress_state(decoded)
                    if progress_state is not None:
                        low_speed_tracker.observe(progress_state.downloaded)
                    if progress_state is not None and progress_callback is not None:
                        if progress_state.fragment_count > 0:
                            progress_callback(
                                video_id,
                                progress_state.fragment_index,
                                progress_state.fragment_count,
                            )
                        elif progress_state.total > 0:
                            progress_callback(
                                video_id, progress_state.downloaded, progress_state.total
                            )
                        else:
                            progress_callback(video_id, progress_state.downloaded, 0)
                    if progress_state is not None and progress_snapshot_callback is not None:
                        try:
                            from .progress import JobPhase, ProgressSnapshot

                            sm = state_machine
                            job_id = sm.job_state.job_id if sm is not None else video_id
                            verified_segments = (
                                sm.job_state.verified_segments if sm is not None else 0
                            )
                            expected_segments = (
                                sm.job_state.expected_segments
                                if sm is not None
                                else (progress_state.fragment_count or None)
                            )
                            verified_bytes = sm.job_state.verified_bytes if sm is not None else 0
                            network_bytes = (
                                sm.job_state.network_bytes_this_session
                                if sm is not None
                                else progress_state.downloaded
                            )
                            attempt = (
                                sm.job_state.attempt_id if sm is not None else (attempt_id or 0)
                            )
                            snapshot = ProgressSnapshot(
                                job_id=str(job_id),
                                phase=JobPhase.DOWNLOADING,
                                verified_segments=int(verified_segments or 0),
                                expected_segments=expected_segments,
                                verified_bytes_on_disk=int(verified_bytes or 0),
                                network_bytes_this_session=int(network_bytes or 0),
                                transfer_rate_bytes_per_sec=0.0,
                                eta_seconds=progress_state.eta_seconds,
                                is_estimate=progress_state.is_estimate,
                                attempt_id=int(attempt or 0),
                                child_fragment_index=progress_state.fragment_index,
                                child_fragment_count=progress_state.fragment_count,
                                measured_at=time.monotonic(),
                            )
                            progress_snapshot_callback(video_id, snapshot)
                        except Exception:  # noqa: BLE001
                            pass
            except DownloadError as exc:
                # The reader met a line longer than its limit. It drained the
                # pipe first, so this task completing is what lets the child be
                # reaped below - record which download lost its transcript, then
                # end normally and let the returncode decide the verdict.
                logger.error(
                    "ytdlp_reader_line_overrun",
                    url=_strip_auth_params(video_url),
                    pid=process.pid,
                    error=str(exc),
                )

        async def _drain_output() -> None:
            """Drain stdout to prevent buffer deadlock when no callback."""
            assert process.stdout is not None
            progress_state: ProgressState | None = None
            try:
                async for line in iter_process_lines(
                    process.stdout, shutdown_event, on_shutdown=_on_shutdown
                ):
                    decoded = line.decode(errors="replace")
                    _echo_ytdlp_line(decoded, echo=echo)
                    _retain_transcript_line(output_chunks, line)
                    if diagnostic_sink is not None:
                        try:
                            getattr(diagnostic_sink, "write_line", lambda *a, **k: None)(
                                decoded, is_progress=_is_ytdlp_progress_line(decoded)
                            )
                        except Exception:
                            pass
                    progress_state = _parse_ytdlp_progress_state(decoded)
                    if progress_state is not None:
                        low_speed_tracker.observe(progress_state.downloaded)
                    if progress_state is not None and progress_callback is not None:
                        if progress_state.fragment_count > 0:
                            progress_callback(
                                video_id,
                                progress_state.fragment_index,
                                progress_state.fragment_count,
                            )
                        elif progress_state.total > 0:
                            progress_callback(
                                video_id, progress_state.downloaded, progress_state.total
                            )
                        else:
                            progress_callback(video_id, progress_state.downloaded, 0)
                    if progress_state is not None and progress_snapshot_callback is not None:
                        try:
                            from .progress import JobPhase, ProgressSnapshot

                            sm = state_machine
                            job_id = sm.job_state.job_id if sm is not None else video_id
                            verified_segments = (
                                sm.job_state.verified_segments if sm is not None else 0
                            )
                            expected_segments = (
                                sm.job_state.expected_segments
                                if sm is not None
                                else (progress_state.fragment_count or None)
                            )
                            verified_bytes = sm.job_state.verified_bytes if sm is not None else 0
                            network_bytes = (
                                sm.job_state.network_bytes_this_session
                                if sm is not None
                                else progress_state.downloaded
                            )
                            attempt = (
                                sm.job_state.attempt_id if sm is not None else (attempt_id or 0)
                            )
                            snapshot = ProgressSnapshot(
                                job_id=str(job_id),
                                phase=JobPhase.DOWNLOADING,
                                verified_segments=int(verified_segments or 0),
                                expected_segments=expected_segments,
                                verified_bytes_on_disk=int(verified_bytes or 0),
                                network_bytes_this_session=int(network_bytes or 0),
                                transfer_rate_bytes_per_sec=0.0,
                                eta_seconds=progress_state.eta_seconds,
                                is_estimate=progress_state.is_estimate,
                                attempt_id=int(attempt or 0),
                                child_fragment_index=progress_state.fragment_index,
                                child_fragment_count=progress_state.fragment_count,
                                measured_at=time.monotonic(),
                            )
                            progress_snapshot_callback(video_id, snapshot)
                        except Exception:  # noqa: BLE001
                            pass
            except DownloadError as exc:
                # The reader met a line longer than its limit. It drained the
                # pipe first, so this task completing is what lets the child be
                # reaped below - record which download lost its transcript, then
                # end normally and let the returncode decide the verdict.
                logger.error(
                    "ytdlp_reader_line_overrun",
                    url=_strip_auth_params(video_url),
                    pid=process.pid,
                    error=str(exc),
                )

        low_speed_tracker = LowSpeedWarningTracker(settings.throttled_rate)

        if progress_callback:
            process_task = asyncio.create_task(process.wait())
            monitor_task = asyncio.create_task(_monitor_progress())
            await _await_first_and_cancel_others(process_task, monitor_task)
        else:
            process_task = asyncio.create_task(process.wait())
            drain_task = asyncio.create_task(_drain_output())
            await _await_first_and_cancel_others(process_task, drain_task)

        # Bounded final drain: capture any tail still buffered after the primary
        # reader completed/cancelled, append to output_chunks and transcript sink.
        if getattr(process, "stdout", None) is not None:
            try:
                _tail = await bounded_drain(
                    process.stdout, timeout=2.0, max_bytes=262144, chunk_size=65536
                )
            except Exception:  # noqa: BLE001
                _tail = b""
            if _tail:
                output_chunks.extend(_tail)
                if len(output_chunks) > _MAX_CHILD_OUTPUT_BYTES:
                    del output_chunks[: len(output_chunks) - _MAX_CHILD_OUTPUT_BYTES]
                if diagnostic_sink is not None:
                    try:
                        getattr(diagnostic_sink, "write_line", lambda *a, **k: None)(
                            _tail.decode(errors="replace")
                        )
                    except Exception:  # noqa: BLE001
                        pass

        # Reap the child exactly once before reading ``returncode``. In normal
        # operation the process has already exited and ``wait()`` returns
        # immediately; bound this one-shot re-wait with ``download_stall_timeout``
        # so a child that stopped producing output but has not yet exited (e.g. the
        # reader drained the pipe yet the child lingers) cannot stall shutdown or
        # retry indefinitely. On expiry the child is destroyed via the
        # cancellation path and the ``TimeoutError`` is re-raised; the call site
        # below translates it to a normal ``None`` result.
        if process.returncode is None:
            try:
                await _await_ytdlp_reap_with_timeout(process, settings.download_stall_timeout)
            except TimeoutError:
                logger.error(
                    "yt_dlp_download_stall_timeout",
                    stall_timeout=settings.download_stall_timeout,
                )
                return YtdlpLaunchResult(
                    path=None,
                    phase="failed",
                    returncode=getattr(process, "returncode", None),
                    last_error_code=None,
                    http_status=None,
                    error_category=ErrorCategory.UNKNOWN,
                    candidate_path=_ytdlp_candidate_path(output_file, workspace),
                    file_conflict=False,
                    cancelled=False,
                )

        elapsed_seconds = time.monotonic() - started_at
        output_data = bytes(output_chunks) if output_chunks else b""

        sanitized_tail = (
            sanitize_text_for_log(output_data.decode(errors="replace")) if output_data else ""
        )
        last_error_code = _derive_last_error_code(sanitized_tail)

        _snapshot_after = _capture_ytdlp_artifact_snapshot(_artifacts, job_lock)

        logger.info(
            "child_exit",
            pid=process.pid,
            launch_number=_launch_number,
            attempt_id=attempt_id,
            returncode=process.returncode,
            elapsed_seconds=elapsed_seconds,
            last_error_code=last_error_code,
            phase="exited",
            next_action="finalize",
            artifact_snapshot=_snapshot_after,
        )

        if shutdown_event.is_set():
            logger.info("yt_dlp_download_cancelled", url=_strip_auth_params(video_url))
            return YtdlpLaunchResult(
                path=None,
                phase="cancelled",
                returncode=getattr(process, "returncode", None),
                last_error_code=last_error_code,
                http_status=None,
                error_category=ErrorCategory.CANCELLED,
                candidate_path=_ytdlp_candidate_path(output_file, workspace),
                file_conflict=False,
                cancelled=True,
            )

        if process.returncode != 0:
            # SEC-002: sanitize subprocess output to redact any signed
            # CDN URLs that yt-dlp may echo in error messages before
            # persisting to log files.
            error_msg = output_data.decode() if output_data else "Unknown yt-dlp error"
            error_msg = sanitize_text_for_log(error_msg)
            logger.error(
                "download_failed",
                url=_strip_auth_params(video_url),
                returncode=process.returncode,
                error=error_msg,
                attempt_id=attempt_id,
            )
            _error_category = ErrorCategory.UNKNOWN
            _file_conflict = False
            try:
                if state_machine is not None:
                    _error_category = state_machine.classify_error(error_msg)
                else:
                    _msg = str(error_msg).lower()
                    if "sharing violation" in _msg or "being used by another process" in _msg or "resource busy" in _msg or "winerror 32" in _msg:
                        _error_category = ErrorCategory.FILE_LOCKED
            except Exception:  # noqa: BLE001
                _error_category = ErrorCategory.UNKNOWN
            if _error_category == ErrorCategory.FILE_LOCKED:
                _file_conflict = True
            return YtdlpLaunchResult(
                path=None,
                phase="file_locked" if _file_conflict else "failed",
                returncode=process.returncode,
                last_error_code=last_error_code,
                http_status=None,
                error_category=_error_category,
                candidate_path=_ytdlp_candidate_path(output_file, workspace),
                file_conflict=_file_conflict,
                cancelled=False,
            )

        logger.info("ytdlp_download_completed", output=str(output_file))
        if workspace is not None:
            staged = workspace.staging_dir / workspace.final_path.name
            if not staged.exists() or not staged.is_file() or staged.stat().st_size <= 0:
                return YtdlpLaunchResult(
                    path=None,
                    phase="missing_output",
                    returncode=process.returncode,
                    last_error_code=last_error_code,
                    http_status=None,
                    error_category=ErrorCategory.INVALID_OUTPUT_PATH,
                    candidate_path=_ytdlp_candidate_path(output_file, workspace),
                    file_conflict=False,
                    cancelled=False,
                )
            try:
                from .ffmpeg_utils import check_ffprobe_available
                from .media_validation import MediaValidationError, validate_media_file
                from .workspace import (
                    acquire_publish_lock,
                    cleanup_owned_job_artifacts,
                    publish_verified_file,
                )

                expected_height = None
                try:
                    expected_height = int(str(quality).rstrip("p"))
                except TypeError, ValueError:
                    expected_height = None

                if not check_ffprobe_available():
                    logger.error("ffprobe_missing", path=str(staged))
                    return YtdlpLaunchResult(
                        path=None,
                        phase="local_block",
                        returncode=process.returncode,
                        last_error_code=last_error_code,
                        http_status=None,
                        error_category=ErrorCategory.INTEGRITY_FAILURE,
                        candidate_path=_ytdlp_candidate_path(output_file, workspace),
                        file_conflict=False,
                        cancelled=False,
                    )
                try:
                    await validate_media_file(staged, expected_height=expected_height)
                except (MediaValidationError, OSError, TimeoutError) as exc:
                    logger.warning("media_validation_failed", error=str(exc))
                    return YtdlpLaunchResult(
                        path=None,
                        phase="local_block",
                        returncode=process.returncode,
                        last_error_code=last_error_code,
                        http_status=None,
                        error_category=ErrorCategory.INTEGRITY_FAILURE,
                        candidate_path=_ytdlp_candidate_path(output_file, workspace),
                        file_conflict=False,
                        cancelled=False,
                    )

                if state_machine is not None:
                    ensure_download_phase(state_machine)

                    _safe_transition(state_machine, DownloadState.ALL_SEGMENTS_VERIFIED)
                    _safe_transition(state_machine, DownloadState.MERGING_IN_STAGING)
                    _safe_transition(state_machine, DownloadState.CANDIDATE_READY)
                    _safe_transition(state_machine, DownloadState.VALIDATING)
                    _safe_transition(state_machine, DownloadState.VALIDATED)

                final_lock = acquire_publish_lock(workspace.final_path, 10.0)
                if state_machine is not None:
                    _safe_transition(state_machine, DownloadState.ATOMIC_NO_CLOBBER_PUBLICATION)
                try:
                    publish_verified_file(staged, workspace.final_path, final_lock=final_lock)
                except (FileExistsError, OSError, FileNotFoundError, TimeoutError) as exc:
                    logger.warning("publish_failed", error=str(exc))
                    return YtdlpLaunchResult(
                        path=None,
                        phase="local_block",
                        returncode=process.returncode,
                        last_error_code=last_error_code,
                        http_status=None,
                        error_category=ErrorCategory.INVALID_OUTPUT_PATH,
                        candidate_path=_ytdlp_candidate_path(output_file, workspace),
                        file_conflict=False,
                        cancelled=False,
                    )

                if job_lock is not None:
                    try:
                        job_lock.release()  # type: ignore[attr-defined]
                    except Exception:  # noqa: BLE001
                        pass
                try:
                    await validate_media_file(workspace.final_path, expected_height=expected_height)
                except (MediaValidationError, OSError, TimeoutError) as exc:
                    logger.warning("media_validation_failed", error=str(exc))
                    return YtdlpLaunchResult(
                        path=None,
                        phase="local_block",
                        returncode=process.returncode,
                        last_error_code=last_error_code,
                        http_status=None,
                        error_category=ErrorCategory.INTEGRITY_FAILURE,
                        candidate_path=_ytdlp_candidate_path(output_file, workspace),
                        file_conflict=False,
                        cancelled=False,
                    )
                if not (
                    workspace.final_path.exists()
                    and workspace.final_path.is_file()
                    and workspace.final_path.stat().st_size > 0
                ):
                    return YtdlpLaunchResult(
                        path=None,
                        phase="missing_output",
                        returncode=process.returncode,
                        last_error_code=last_error_code,
                        http_status=None,
                        error_category=ErrorCategory.INVALID_OUTPUT_PATH,
                        candidate_path=_ytdlp_candidate_path(output_file, workspace),
                        file_conflict=False,
                        cancelled=False,
                    )
                if state_machine is not None:
                    _safe_transition(state_machine, DownloadState.FINAL_COMMITTED)
                    _safe_transition(state_machine, DownloadState.CLEANUP_OWNED_TEMP_ARTIFACTS)
                cleanup_owned_job_artifacts(workspace)
            except asyncio.CancelledError, KeyboardInterrupt:
                raise
            except (
                MediaValidationError,
                FileNotFoundError,
                FileExistsError,
                OSError,
                TimeoutError,
            ) as exc:
                logger.warning("commit_failed", error=str(exc))
                return YtdlpLaunchResult(
                    path=None,
                    phase="local_block",
                    returncode=process.returncode,
                    last_error_code=last_error_code,
                    http_status=None,
                    error_category=ErrorCategory.INTEGRITY_FAILURE,
                    candidate_path=_ytdlp_candidate_path(output_file, workspace),
                    file_conflict=False,
                    cancelled=False,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("commit_unexpected", error=str(exc))
                return YtdlpLaunchResult(
                    path=None,
                    phase="local_block",
                    returncode=process.returncode,
                    last_error_code=last_error_code,
                    http_status=None,
                    error_category=ErrorCategory.INTEGRITY_FAILURE,
                    candidate_path=_ytdlp_candidate_path(output_file, workspace),
                    file_conflict=False,
                    cancelled=False,
                )
            return YtdlpLaunchResult(
                path=workspace.final_path,
                phase="completed",
                returncode=process.returncode,
                last_error_code=last_error_code,
                http_status=None,
                error_category=ErrorCategory.UNKNOWN,
                candidate_path=workspace.final_path,
                file_conflict=False,
                cancelled=False,
            )
        if output_file.exists():
            logger.info("download_final_size", size=output_file.stat().st_size)
        return YtdlpLaunchResult(
            path=output_file,
            phase="completed",
            returncode=process.returncode,
            last_error_code=last_error_code,
            http_status=None,
            error_category=ErrorCategory.UNKNOWN,
            candidate_path=None,
            file_conflict=False,
            cancelled=False,
        )

    except FileNotFoundError as exc:
        # yt-dlp binary / Python interpreter not found on PATH
        logger.error(
            "ytdlp_not_found",
            url=_strip_auth_params(video_url),
            path=exc.filename,
            exc_info=True,
        )
        return YtdlpLaunchResult(
            path=None,
            phase="failed",
            returncode=None,
            last_error_code=last_error_code if "last_error_code" in locals() else None,
            http_status=None,
            error_category=ErrorCategory.UNKNOWN,
            candidate_path=_ytdlp_candidate_path(output_file, workspace),
            file_conflict=False,
            cancelled=False,
        )
    except asyncio.CancelledError:
        logger.info("yt_dlp_download_cancelled", url=_strip_auth_params(video_url))
        if process is not None and process.returncode is None:
            if not await cancel_subprocess(process) and process.returncode is None:
                logger.warning(
                    "yt_dlp_cancel_not_clean",
                    pid=process.pid,
                    url=_strip_auth_params(video_url),
                )
        raise
    finally:
        try:
            from ..utils.correlation import clear_correlation_id

            clear_correlation_id()
        except Exception:  # noqa: BLE001
            pass
        if cookie_stdin is not None:
            cookie_stdin.close()
        if cookie_file is not None:
            # The inner exists() guard is kept: folding it in would make
            # unlink(missing_ok=True) "succeed" on an absent file and emit
            # cookie_file_cleaned_up for a file that never existed.
            if cookie_file.exists():
                try:
                    cookie_file.unlink(missing_ok=True)
                except OSError as exc:
                    # A failed destroy must never replace the download's own outcome.
                    # ``missing_ok=True`` already covers ``FileNotFoundError``; any
                    # other ``OSError`` (e.g. ``PermissionError`` from an indexer or
                    # scanner holding the file) is recorded here so the method's
                    # return value / propagated exception survives.
                    logger.warning(
                        "cookie_file_cleanup_failed",
                        path=str(cookie_file),
                        error=str(exc),
                    )
                else:
                    logger.debug("cookie_file_cleaned_up", path=str(cookie_file))
            # LOAD-BEARING ORDER: the credential file is unlinked above, so the
            # directory is empty apart from owner.pid and the removal below can
            # succeed. Run this whenever a cookie file was created, even if it
            # has already vanished or its unlink failed - otherwise the directory
            # leaks.
            _remove_cookie_artifact_dir(cookie_file.parent)
        if batch_file is not None:
            if batch_file.exists():
                try:
                    batch_file.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning(
                        "batch_file_cleanup_failed",
                        path=str(batch_file),
                        error=str(exc),
                    )
                else:
                    logger.debug("batch_file_cleaned_up", path=str(batch_file))
            _remove_cookie_artifact_dir(batch_file.parent)


async def _download_with_ytdlp(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    settings: Settings,
    cookies: str | None = None,
    raw_cookies: list[Cookie] | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    progress_snapshot_callback: Callable[[str, object], None] | None = None,
    *,
    echo: bool = True,
    diagnostic_sink: object | None = None,
    attempt_id: int | None = None,
    workspace: DownloadWorkspace | None = None,
    state_machine: DownloadStateMachine | None = None,
    job_lock: object | None = None,
) -> Path | None:
    """Compatibility shim returning Path | None."""
    result = await _download_with_ytdlp_result(
        video_url,
        m3u8_url,
        output_file,
        quality,
        settings,
        cookies,
        raw_cookies,
        progress_callback,
        progress_snapshot_callback=progress_snapshot_callback,
        echo=echo,
        diagnostic_sink=diagnostic_sink,
        attempt_id=attempt_id,
        workspace=workspace,
        state_machine=state_machine,
        job_lock=job_lock,
    )
    if result is not None and result.phase == "completed":
        return result.path
    return None


async def bounded_drain(
    stream: object,
    *,
    timeout: float = 2.0,
    max_bytes: int = 262144,
    chunk_size: int = 65536,
) -> bytes:
    """Bounded final drain of a subprocess stream.

    Reads up to ``max_bytes`` from ``stream`` within ``timeout`` seconds using
    a monotonic deadline. Stops at EOF, timeout, or byte cap. Logs
    ``child_drain_truncated`` with the captured byte count when the cap is hit.
    """
    result = bytearray()
    deadline = time.monotonic() + float(timeout)
    truncated = False
    read = getattr(stream, "read", None)
    if read is None:
        return bytes(result)
    while len(result) < max_bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            chunk = await asyncio.wait_for(read(chunk_size), timeout=remaining)
        except Exception:  # noqa: BLE001
            # Treat timeout and read errors as end-of-drain.
            break
        if not chunk:
            break
        data = bytes(chunk)
        if len(result) + len(data) > max_bytes:
            allowed = max_bytes - len(result)
            if allowed > 0:
                result.extend(data[:allowed])
            truncated = True
            break
        result.extend(data)
    if truncated or len(result) >= max_bytes:
        try:
            logger.info("child_drain_truncated", captured_bytes=len(result))
        except Exception:  # noqa: BLE001
            pass
    return bytes(result)


# Backwards-compatible alias used by tests/importers.
bounded_drain_stream = bounded_drain



async def _resolve_cookies(
    extractor: VKVideoExtractor,
    settings: Settings,
    url: str,
    m3u8_url: str,
    quality: str,
) -> tuple[str, str | None, list[Cookie] | None]:
    """Resolve cookies and update m3u8_url based on cookie_source setting.

    Args:
        extractor: VKVideoExtractor instance for stream extraction.
        settings: Application settings.
        url: Video URL to extract streams from.
        m3u8_url: Current m3u8 URL (may be updated if browser streams used).
        quality: Quality token (``best``, ``worst``, ``unknown``, or a height in
            pixels the video offers, e.g. ``1072``), parsed here to decide
            whether the browser-captured stream may be re-selected.

    Returns:
        Tuple of (updated m3u8_url, cookies string, raw cookies for Netscape format).

    Raises:
        QualityNotAvailableError: If requested quality is BEST but not available in browser streams.
        QualityParseError: If ``quality`` is neither a keyword nor a positive height.
    """
    if settings.cookie_source != CookieSource.BROWSER:
        return m3u8_url, None, None

    quality_spec = QualitySpec.parse(quality)
    if quality_spec.kind is QualityKind.BEST:
        browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(url)
        if browser_streams:
            selector = QualitySelector()
            selected_stream = selector.select(browser_streams, quality_spec)
            m3u8_url = str(selected_stream.url)
            logger.info(
                "browser_streams_selected",
                quality=quality,
                selected_quality=selected_stream.quality,
            )
        else:
            cookies = None
            raw_cookies = None
        return m3u8_url, cookies, raw_cookies

    # Exact quality: obtain cookies from browser extraction only; retain the
    # caller's preselected m3u8_url and do not require height verification.
    browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(url)
    if not browser_streams:
        cookies = None
        raw_cookies = None
    return m3u8_url, cookies, raw_cookies


def _safe_transition(state_machine: object, target: object) -> None:
    import asyncio

    if state_machine is None:
        return
    try:
        from structlog import get_logger

        _logger = get_logger(__name__)
    except Exception:  # noqa: BLE001
        _logger = None
    try:
        if hasattr(state_machine, "can_transition") and cast(
            "DownloadStateMachine", state_machine
        ).can_transition(cast("DownloadState", target)):
            cast("DownloadStateMachine", state_machine).transition(cast("DownloadState", target))
        else:
            if _logger is not None:
                _logger.debug(
                    "transition_skipped",
                    current=getattr(state_machine, "state", None),
                    target=str(target),
                )
    except asyncio.CancelledError, KeyboardInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001
        if _logger is not None:
            _logger.debug(
                "transition_skipped",
                current=getattr(state_machine, "state", None),
                target=str(target),
                error=str(exc),
            )


def ensure_download_phase(state_machine: object) -> None:
    if state_machine is None:
        return
    import asyncio

    try:
        from ..models.enums import DownloadState

        for target in (
            DownloadState.RESOLVE_STREAM,
            DownloadState.VALIDATE_VARIANT,
            DownloadState.DOWNLOAD,
        ):
            if hasattr(state_machine, "can_transition") and cast(
                "DownloadStateMachine", state_machine
            ).can_transition(target):
                cast("DownloadStateMachine", state_machine).transition(target)
    except asyncio.CancelledError, KeyboardInterrupt:
        raise
    except Exception:  # noqa: BLE001
        pass



class LowSpeedWarningTracker:
    """Sustained low-speed diagnostic warning tracker."""

    def __init__(
        self,
        threshold_bytes_per_sec: int,
        *,
        sample_count: int = 3,
        min_window_seconds: float = 3.0,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.threshold_bytes_per_sec = int(threshold_bytes_per_sec)
        self.sample_count = int(sample_count)
        self.min_window_seconds = float(min_window_seconds)
        self.cooldown_seconds = float(cooldown_seconds)
        self._samples: deque[tuple[float, int]] = deque(maxlen=self.sample_count)
        self._warned_episode = False
        self._last_warning_at: float | None = None

    def observe(self, downloaded: int, *, now: float | None = None) -> bool:
        if self.threshold_bytes_per_sec <= 0:
            return False

        if now is None:
            current_now = time.monotonic()
        else:
            current_now = now
        now_value = float(current_now)
        downloaded = int(downloaded)

        self._samples.append((now_value, downloaded))

        if len(self._samples) < self.sample_count:
            return False

        first_ts, first_bytes = self._samples[0]
        last_ts, last_bytes = self._samples[-1]
        span = last_ts - first_ts
        if span < self.min_window_seconds:
            return False

        if span <= 0:
            rate = 0.0
        else:
            rate = (last_bytes - first_bytes) / span

        if rate <= 0:
            self._warned_episode = False
            self._last_warning_at = None
            return False

        if rate >= self.threshold_bytes_per_sec:
            self._warned_episode = False
            self._last_warning_at = None
            return False

        should_warn = (
            not self._warned_episode
            or self._last_warning_at is None
            or (now_value - self._last_warning_at) >= self.cooldown_seconds
        )
        if should_warn:
            logger.warning(
                "ytdlp_low_speed",
                rate_bytes_per_sec=float(rate),
                threshold_bytes_per_sec=self.threshold_bytes_per_sec,
                sample_count=self.sample_count,
                window_seconds=float(span),
                downloaded=downloaded,
            )
            self._warned_episode = True
            self._last_warning_at = now_value
            return True
        return False
