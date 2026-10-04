"""yt-dlp subprocess download with cookie-file lifecycle and resume fallback."""

from __future__ import annotations

import asyncio
import atexit
import os
import re
import shutil
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.async_api import Cookie
from structlog import get_logger

from ..config import Settings
from ..exceptions import (
    DownloadError,
    ExtractionError,
    QualityNotAvailableError,
    QualityParseError,
)
from ..models.dtos import HLSDownloadRequest
from ..models.enums import CookieSource, QualityKind
from ..models.quality import QualitySpec
from ..services.cookies import _cookies_to_netscape
from ..services.downloader_throttle import (
    _compute_backoff_delay,
    _wait_with_shutdown,
    get_shutdown_event,
)
from ..services.extractor import VKVideoExtractor
from ..services.ffmpeg_utils import (
    _SPAWN_BOUNDARY_KWARGS,
    cancel_subprocess,
    iter_process_lines,
)
from ..services.quality import QualitySelector
from ..services.segment_downloader import download_hls_with_resume
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params, sanitize_text_for_log

if TYPE_CHECKING:
    from ..services.concurrency import SemaphoreLike
    from .downloader_throttle import URLBackoffCoordinator

logger = get_logger(__name__)

# Cookie artefact lifecycle constants (SEC-001, SEC-002, VAL-602).
# These strings are frozen by B2: the prefix ``vk_cookies_`` is what the
# sweep is keyed on, and the suffix ``.cookies.txt`` is what ``.gitignore``
# matches. Renaming either breaks coverage silently.
_COOKIE_ARTIFACT_PREFIX = "vk_cookies_"
_COOKIE_ARTIFACT_SUFFIX = ".cookies.txt"
_ARTEFACT_DIR_SUFFIX = "_dir"
_OWNER_PID_FILENAME = "owner.pid"

# Tracks every artefact directory this process created, so the atexit
# handler can purge them on orderly exit.
_COOKIE_ARTIFACT_DIRS: set[Path] = set()
_cookie_lifecycle_started: bool = False
_COOKIE_LIFECYCLE_LOCK = threading.Lock()


def _is_pid_alive(pid: int) -> bool:
    """Report whether a process with ``pid`` is currently alive.

    On POSIX, uses ``os.kill(pid, 0)`` — signal 0 tests process existence
    without delivering a signal. On Windows, ``os.kill`` is **prohibited**
    because CPython maps non-console signal values to ``TerminateProcess``
    (confirmed: signal 0 is not in the console-control set), so a ctypes
    probe via ``OpenProcess`` + ``GetExitCodeProcess`` is used instead
    (D-1). ``STILL_ACTIVE`` (259) means the process has not exited yet.
    """
    if os.name == "nt":
        import ctypes

        # GetExitCodeProcess requires PROCESS_QUERY_INFORMATION (0x0400), not
        # SYNCHRONIZE — SYNCHRONIZE only permits WaitForSingleObject. Using the
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


def _read_owner_pid(cookie_dir: Path) -> int | None:
    """Read the owning PID recorded in ``owner.pid`` within ``cookie_dir``."""
    owner_file = cookie_dir / _OWNER_PID_FILENAME
    try:
        return int(owner_file.read_text().strip())
    except (OSError, ValueError):
        return None


def _purge_cookie_artifact_dir(cookie_dir: Path) -> None:
    """Forcefully remove a stale cookie artefact directory and its contents.

    Used by the sweep (prior-run residue) and the atexit handler. Errors
    are swallowed so a leftover directory never blocks the current run.
    """
    shutil.rmtree(cookie_dir, ignore_errors=True)


def _remove_cookie_artifact_dir(cookie_dir: Path) -> None:
    """Remove a cookie artefact directory when it is empty.

    Called from the ``finally`` block after the cookie file has been
    unlinked. Successful removal emits no record. If the file could not be
    deleted (the ``OSError`` arm already logged ``cookie_file_cleanup_failed``),
    ``rmdir`` will fail because the directory is not empty — that failure
    is also logged as ``cookie_file_cleanup_failed`` so the cleanup attempt
    is visible, then the directory is left for the atexit sweep to reclaim.
    """
    try:
        cookie_dir.rmdir()
    except OSError as exc:
        logger.warning(
            "cookie_file_cleanup_failed",
            path=str(cookie_dir),
            error=str(exc),
        )


def _sweep_stale_cookie_dirs() -> None:
    """Remove cookie artefact directories whose owner PID is no longer live.

    Scans the system temp directory for directories whose names start with
    the product prefix (``vk_cookies_dir``). A directory is removed only
    when its recorded owner PID — read from ``owner.pid`` — is not a live
    process. Directories owned by a live process (including the current one)
    are left untouched. This is the liveness-gated sweep that makes residue
    reclaimable by the *next* run rather than only by the operator (SEC-002),
    and is PID-based rather than age-based to avoid the concurrency hazard
    VAL-002 rules out (VAL-602).
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
            if owner_pid is None or not _is_pid_alive(owner_pid):
                stale.append(entry)
    except OSError:
        return
    for cookie_dir in stale:
        _purge_cookie_artifact_dir(cookie_dir)
        with _COOKIE_LIFECYCLE_LOCK:
            _COOKIE_ARTIFACT_DIRS.discard(cookie_dir)


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


async def _await_first_and_cancel_others(
    *tasks: asyncio.Task[Any],
) -> tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]:
    """Launch tasks concurrently, await first completion, cancel remaining.

    Args:
        *tasks: Tasks to await concurrently.

    Returns:
        Tuple of (done_tasks, pending_tasks) after cancellation.

    A task in ``done`` that raised — e.g. the reader dying mid-drain — has its
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
    # re-raised — re-raising would turn a drain into a crash (TRN-006 sink half).
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
    child's stdout — i.e. the child has gone silent. While the reader is still
    yielding lines the clock is never started, so a child that keeps producing
    output is never killed, no matter how long it runs. A bare
    ``asyncio.wait_for(process.wait(), ...)`` without this ladder would leave
    the child unreaped on timeout.

    Args:
        process: The yt-dlp subprocess whose re-wait is being bounded.
        timeout: Maximum seconds of inactivity (silence) to wait for the
            child to exit before terminating it. Mandatory — has no default
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
    except (TimeoutError, asyncio.CancelledError):
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
    r"(?P<pct>\d+(?:\.\d+)?)%\s+of\s+~?\s*"
    r"(?P<size>\d+(?:\.\d+)?)"
    r"(?P<size_unit>[KMG]?i?B)"
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
        count) are still progress updates — see :func:`_is_ytdlp_progress_line`
        — they simply carry no ratio to report.
    """
    match = _YTDLP_PROGRESS_RE.search(line)
    if match is None:
        return None
    pct = float(match.group("pct"))
    size = float(match.group("size"))
    size_unit = match.group("size_unit")
    multiplier = _SIZE_UNITS.get(size_unit, 1)
    total = int(size * multiplier)
    downloaded = int(total * pct / 100)
    return downloaded, total


def _echo_ytdlp_line(line: str, *, echo: bool = True) -> None:
    """Echo a yt-dlp output line to the console.

    Progress lines (e.g. ``[download]  40.3% of 649.37MiB ...``) are
    rewritten in-place using carriage returns to restore the
    pre-migration behavior where yt-dlp used ``\\r`` for live progress
    updates.  Non-progress lines use newlines as-is.

    When ``echo`` is ``False`` (batch mode), nothing is written to stderr
    at all — progress data is emitted at DEBUG level instead and
    non-progress lines are dropped silently, so yt-dlp output never
    interleaves with the rich progress display.
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
        return
    if _is_ytdlp_progress_line(line):
        text = line.rstrip("\n\r")
        width = shutil.get_terminal_size((80, 24)).columns
        sys.stderr.write("\r" + text.ljust(width)[:width] + "\r")
        sys.stderr.flush()
    else:
        sys.stderr.write(line)
        sys.stderr.flush()


def _build_ytdlp_cli_command(
    output_file: Path,
    quality_str: str,
    user_agent: str,
    settings: Settings,
    cookies: str | None,
    raw_cookies: list[Cookie] | None,
) -> tuple[list[str], Path | None]:
    """Build a yt-dlp CLI command list and optional temp cookie file path.

    The command is executed via ``asyncio.create_subprocess_exec`` so the
    yt-dlp process can be properly terminated on cancellation or shutdown.

    Args:
        output_file: Path to save the downloaded video.
        quality_str: Quality token: ``best``, ``worst``, ``unknown``, or a height in
            pixels the video offers (e.g. ``"1072"``). A numeric token becomes the
            yt-dlp format selector ``best[height<=1072]``.
        user_agent: User agent string for HTTP requests.
        settings: Application settings.
        cookies: Optional raw cookie string (Netscape format) for backward compat.
        raw_cookies: Optional list of Playwright Cookie objects for Netscape format.

    Returns:
        Tuple of (command list, cookie_file Path or None).
    """
    # Build format selector: use height filter for numeric quality, bare "best" otherwise
    format_selector = (
        f"best[height<={quality_str}]" if quality_str and quality_str.isdigit() else "best"
    )

    cmd: list[str] = [
        sys.executable,
        "-u",  # Unbuffered stderr — critical for real-time progress passthrough with PIPE
        "-m",
        "yt_dlp",
        "--encoding",
        "utf-8",
        "-o",
        str(output_file),
        "-f",
        format_selector,
        "--newline",
        "--hls-prefer-native",
        "--no-warnings",
        "--socket-timeout",
        str(settings.download_timeout),
        "-R",
        str(settings.max_retries),
        "--fragment-retries",
        str(settings.max_retries),
        "-N",
        str(settings.max_concurrent_downloads),
        "--throttled-rate",
        str(settings.throttled_rate),
        "--user-agent",
        user_agent,
        "--referer",
        "https://vkvideo.ru/",
    ]

    # --http-chunk-size forces range-request-based downloading of HLS segments.
    # When enabled (> 0), it can cause silent data corruption on CDNs that do not
    # properly support HTTP Range headers, producing files with corrupted segments
    # ("broken chunks in the middle"). Disabled by default (0) for reliability.
    # Only include when explicitly enabled by the user.
    if settings.http_chunk_size > 0:
        cmd.extend(["--http-chunk-size", str(settings.http_chunk_size)])

    if not settings.ssl_verify:
        cmd.append("--no-check-certificates")

    # Add cookies file if cookies are provided
    cookie_file: Path | None = None
    if raw_cookies:
        cookie_file = _create_temp_cookie_file(raw_cookies)
        cmd.extend(["--cookies", str(cookie_file)])
    elif cookies:
        cookie_file = _create_temp_cookie_file(cookies)
        cmd.extend(["--cookies", str(cookie_file)])

    return cmd, cookie_file


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
    echo: bool = True,
) -> Path | None:
    """Download using yt-dlp with automatic segment-based fallback on failure.

    Flow:
    1. Try yt-dlp download
    2. On failure with partial file: get fresh token via browser + switch to segment download
    3. Falls back to a fresh segment-based download via HLS; the partial yt-dlp file is discarded

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
            Only governs yt-dlp output — has no effect on the ffmpeg or segment paths.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    if settings is None:
        settings = Settings()

    shutdown_event = get_shutdown_event()
    retry_count = 0

    while retry_count <= settings.max_retries:
        result = await _download_with_ytdlp(
            video_url,
            output_file,
            quality,
            settings,
            cookies,
            raw_cookies,
            progress_callback,
            echo=echo,
        )

        if result:
            if retry_count > 0:
                logger.info("download_completed_after_retries", retries=retry_count)
            return result

        retry_count += 1

        if shutdown_event.is_set():
            logger.info(
                "yt_dlp_download_cancelled",
                url=_strip_auth_params(video_url),
            )
            return None

        # Backoff between yt-dlp retry attempts (SRV-006):
        # Without this, the retry loop hammers the VK origin on failure.
        # Use _compute_backoff_delay with a 500 base status (yt-dlp failures
        # don't carry an HTTP status at this level); _wait_with_shutdown
        # respects the shared URLBackoffCoordinator's pause state if one is
        # provided, and allows interruption via the shutdown event.
        backoff_delay = _compute_backoff_delay(500, retry_count, None)
        if backoff_coordinator is not None:
            await backoff_coordinator.wait_if_paused(video_url)
        shutdown_triggered = await _wait_with_shutdown(
            backoff_delay,
            shutdown_event,
            retry_count,
            _strip_auth_params(video_url),
        )
        if shutdown_triggered:
            logger.info(
                "yt_dlp_download_cancelled_during_backoff", url=_strip_auth_params(video_url)
            )
            return None

        # Check for partial file - switch to segment download with fresh token
        validated_output = validate_output_path(output_file, warning=False)
        if not validated_output.exists() or validated_output.stat().st_size == 0:
            return None

        # Attempt segment resume with fresh token
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
            )
        ) is not None:
            return segment_result

    # All retries exhausted without success
    logger.error(
        "max_retries_exceeded",
        url=_strip_auth_params(video_url),
        retries=settings.max_retries,
    )
    # DF-008: Clean up partial output file left by yt-dlp on failure
    try:
        validated_output.unlink(missing_ok=True)
    except OSError:
        logger.warning("failed_to_cleanup_partial_file", path=str(validated_output))
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
    video_semaphore: SemaphoreLike | None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> Path | None:
    """Attempt segment-based download with fresh token on yt-dlp failure.

    Called when yt-dlp fails and partial file exists. Forces browser extraction
    to get fresh token, then falls back to a fresh segment-based download via HLS.
    The partial yt-dlp file is discarded; segment download starts from the beginning.

    Args:
        video_url: Original VK video URL.
        m3u8_url: HLS playlist URL (may be stale).
        output_file: Output file path (partial file is discarded, segment download starts fresh).
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
    logger.warning(
        "download_interrupted_switching_to_segments",
        url=_strip_auth_params(video_url),
        path=str(output_file),
        size=output_file.stat().st_size,
        retry=retry_count,
    )
    logger.info("attempting_segment_resume", retry=retry_count)

    try:
        if extractor is None:
            extractor = VKVideoExtractor(settings=settings, backoff_coordinator=backoff_coordinator)
        # Force browser for token refresh during resume (recovery scenario)
        browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(
            video_url, force_browser=True
        )
        if browser_streams:
            try:
                quality_spec = QualitySpec.parse(quality)
                # Browser streams are labelled QualityLabel.UNKNOWN.value
                # ("unknown") and height=None by _extract_with_browser.
                # Only run quality selection for BEST; for exact requests, reuse the
                # pre-selected m3u8_url from the caller (yt-dlp already selected the stream).
                if quality_spec.kind is QualityKind.BEST:
                    selector = QualitySelector()
                    selected_stream = selector.select(browser_streams, quality_spec)
                    m3u8_url = str(selected_stream.url)
                    logger.info(
                        "fresh_token_obtained_for_resume",
                        quality=quality,
                        selected_quality=selected_stream.quality,
                    )
                else:
                    logger.info(
                        "browser_streams_selected_with_preselected_url_for_resume",
                        quality=quality,
                        m3u8_url=_strip_auth_params(m3u8_url),
                    )
            except QualityNotAvailableError:
                logger.error(
                    "requested_quality_not_available_in_browser_streams",
                    url=_strip_auth_params(video_url),
                    quality=quality,
                    available=[s.quality for s in browser_streams],
                )
                raise
            # Remove partial file to start clean segment download
            output_file.unlink()
            # Continue to segment download
            return await download_hls_with_resume(
                HLSDownloadRequest(
                    video_url=video_url,
                    m3u8_url=m3u8_url,
                    output_file=output_file,
                    quality=quality,
                    cookies=cookies,
                    progress_callback=progress_callback,
                ),
                settings=settings,
                extractor=extractor,
                backoff_coordinator=backoff_coordinator,
                video_semaphore=video_semaphore,
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


# TRN-011: The child transcript buffer exists only to build the
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


async def _download_with_ytdlp(
    video_url: str,
    output_file: Path,
    quality: str,
    settings: Settings,
    cookies: str | None = None,
    raw_cookies: list[Cookie] | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    *,
    echo: bool = True,
) -> Path | None:
    """Download video using yt-dlp via subprocess.

    Uses ``asyncio.create_subprocess_exec`` instead of ``run_in_executor``
    so the yt-dlp process can be properly terminated (SIGTERM -> SIGKILL)
    on cancellation or shutdown. yt-dlp has its own ``--socket-timeout``,
    ``-R`` (retries), ``--fragment-retries``, and ``-N`` (concurrent
    fragments) for network robustness — no application-level download
    timeout is imposed, avoiding premature kill of legitimate long downloads.
    A download that keeps producing output is never killed, no matter how
    long it runs. Only the **inactivity** of the stream — the one-shot reap
    applied after the reader has consumed every line and the child has gone
    silent — is bounded by ``download_stall_timeout``: on expiry the child is
    terminated through the cancellation ladder (``cancel_subprocess``) and
    the resulting ``TimeoutError`` is re-raised. This is not a whole-operation
    budget (see ``download_timeout`` for the per-request and per-subprocess
    bounds that are), and it does not apply to the merge subprocesses, which
    ``download_timeout`` already bounds.

    Args:
        video_url: VK video URL to download.
        output_file: Path to save the downloaded video.
        quality: Quality token (``best``, ``worst``, ``unknown``, or a height in
            pixels the video offers, e.g. ``1072``).
        settings: Application settings.
        cookies: Optional cookies string for backward compatibility.
        raw_cookies: Optional raw Cookie objects for Netscape format.
        progress_callback: Optional callback for per-URL progress updates.
        echo: When False, suppresses yt-dlp's native console echo (progress lines
            are emitted at DEBUG level instead; non-progress lines are dropped).
            Only governs yt-dlp output — has no effect on the ffmpeg or segment paths.

    Returns:
        Path to the output file on success, None on failure.
    """
    logger.info(
        "starting_ytdlp_download",
        url=_strip_auth_params(video_url),
        output=str(output_file),
        quality=quality,
    )

    quality_str = quality.replace("p", "") if quality else "720"
    user_agent = settings.user_agent
    video_id = video_url.split("_")[-1] if "_" in video_url else video_url
    shutdown_event = get_shutdown_event()

    if not settings.ssl_verify:
        logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))

    cmd, cookie_file = _build_ytdlp_cli_command(
        output_file,
        quality_str,
        user_agent,
        settings,
        cookies,
        raw_cookies,
    )
    # yt-dlp takes the URL as its final positional argument
    cmd.append(video_url)

    # yt-dlp writes progress and most output to stdout by default (confirmed
    # empirically). Using stdout=PIPE + stderr=STDOUT merges all output into a
    # single stream, avoiding dual-pipe deadlock complexity while preserving
    # error messages for structured logging on failure.
    process: asyncio.subprocess.Process | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            **_SPAWN_BOUNDARY_KWARGS,  # type: ignore[arg-type]
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
            try:
                async for line in iter_process_lines(
                    process.stdout, shutdown_event, on_shutdown=_on_shutdown
                ):
                    decoded = line.decode(errors="replace")
                    _echo_ytdlp_line(decoded, echo=echo)
                    _retain_transcript_line(output_chunks, line)
                    progress = _parse_ytdlp_progress(decoded)
                    if progress is not None and progress_callback is not None:
                        downloaded, total = progress
                        progress_callback(video_id, downloaded, total)
            except DownloadError as exc:
                # The reader met a line longer than its limit. It drained the
                # pipe first, so this task completing is what lets the child be
                # reaped below — record which download lost its transcript, then
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
            try:
                async for line in iter_process_lines(
                    process.stdout, shutdown_event, on_shutdown=_on_shutdown
                ):
                    decoded = line.decode(errors="replace")
                    _echo_ytdlp_line(decoded, echo=echo)
                    _retain_transcript_line(output_chunks, line)
            except DownloadError as exc:
                # The reader met a line longer than its limit. It drained the
                # pipe first, so this task completing is what lets the child be
                # reaped below — record which download lost its transcript, then
                # end normally and let the returncode decide the verdict.
                logger.error(
                    "ytdlp_reader_line_overrun",
                    url=_strip_auth_params(video_url),
                    pid=process.pid,
                    error=str(exc),
                )

        if progress_callback:
            process_task = asyncio.create_task(process.wait())
            monitor_task = asyncio.create_task(_monitor_progress())
            await _await_first_and_cancel_others(process_task, monitor_task)
        else:
            process_task = asyncio.create_task(process.wait())
            drain_task = asyncio.create_task(_drain_output())
            await _await_first_and_cancel_others(process_task, drain_task)

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
                return None

        output_data = bytes(output_chunks) if output_chunks else b""

        if shutdown_event.is_set():
            logger.info("yt_dlp_download_cancelled", url=_strip_auth_params(video_url))
            return None

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
            )
            return None

        logger.info("ytdlp_download_completed", output=str(output_file))
        return output_file

    except FileNotFoundError as exc:
        # yt-dlp binary / Python interpreter not found on PATH
        logger.error(
            "ytdlp_not_found",
            url=_strip_auth_params(video_url),
            path=exc.filename,
            exc_info=True,
        )
        return None
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
        if cookie_file is not None and cookie_file.exists():
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
            _remove_cookie_artifact_dir(cookie_file.parent)


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
    if settings.cookie_source == CookieSource.BROWSER:
        browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(url)
        if browser_streams:
            quality_spec = QualitySpec.parse(quality)
            # Browser streams are labelled QualityLabel.UNKNOWN.value
            # ("unknown") and height=None by _extract_with_browser.
            # Only run quality selection for BEST; for exact requests, reuse the
            # pre-selected m3u8_url from the caller (yt-dlp already selected the stream).
            if quality_spec.kind is QualityKind.BEST:
                selector = QualitySelector()
                selected_stream = selector.select(browser_streams, quality_spec)
                m3u8_url = str(selected_stream.url)
                logger.info(
                    "browser_streams_selected",
                    quality=quality,
                    selected_quality=selected_stream.quality,
                )
            else:
                logger.info(
                    "browser_streams_selected_with_preselected_url",
                    quality=quality,
                    m3u8_url=_strip_auth_params(m3u8_url),
                )
        else:
            cookies = None
            raw_cookies = None
        return m3u8_url, cookies, raw_cookies
    return m3u8_url, None, None
