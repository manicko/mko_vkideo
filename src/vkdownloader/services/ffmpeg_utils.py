"""FFmpeg utilities for command building, process management, and progress parsing."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import signal
import subprocess
import sys
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from pathlib import Path
from typing import Final

from structlog import get_logger

from ..exceptions import DownloadError
from ..utils.formatting import format_bytes
from ..utils.url_sanitizer import (
    sanitize_text_for_log,  # SEC-002: redact signed CDN URLs from merge-failure stderr before logging
)
from .downloader_throttle import DEFAULT_DOWNLOAD_TIMEOUT

# Per-stage timeout for ffmpeg merge subprocesses. Separate from download_timeout
# so lowering the HTTP budget (NET-007) does not shorten each merge stage and
# trigger the NET-001 data-loss path. Each subprocess gets this budget once;
# the caller passes it through _merge_segments_batched rather than repeating it.
_MERGE_STAGE_TIMEOUT: float = float(DEFAULT_DOWNLOAD_TIMEOUT)

logger = get_logger(__name__)

# TRN-003: Process boundary at every asyncio subprocess spawn site.
# On POSIX, start_new_session=True calls setsid() in the child before exec,
# making it a session leader whose process group ID equals its PID. os.killpg
# can then signal descendants. On Windows, CREATE_NEW_PROCESS_GROUP (0x200)
# only disables Ctrl+C routing for the group — it does NOT make the tree
# killable by pid. See docs/11-guides/vkdownloader-limitations.md.
#
# creationflags raises ValueError on POSIX (it is Windows-only), and
# subprocess.CREATE_NEW_PROCESS_GROUP does not exist on POSIX (AttributeError),
# so the selection is a module-level platform guard, not per call.
_IS_WINDOWS: Final[bool] = sys.platform == "win32"

# The minimum platform-appropriate boundary keyword, applied at every spawn site
# via ** _SPAWN_BOUNDARY_KWARGS. Typed dict[str, int | bool] — not Any — and a
# platform dispatch, not an enumerated business constant (rule 10).
_SPAWN_BOUNDARY_KWARGS: Final[dict[str, int | bool]] = (
    {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    if _IS_WINDOWS
    else {"start_new_session": True}
)

# Module-level cache: PATH lookup happens only once per process lifetime
_ffmpeg_available: bool | None = None

# Hint text naming the missing dependency and the consequence, reused by every
# arm that reports a missing muxer so the install step is named once and
# consistently (D6, TRN-008).
_MERGE_HINT: Final[str] = "ffmpeg binary not found on PATH; segment merge will fail after download"

# Free space kept in reserve on top of the size arithmetic below. It covers
# what the byte figures cannot see: the batch temp file that coexists with the
# segments it was written from, filesystem block-allocation slack, and whatever
# another process writes between the probe and the first output byte. 64 MiB is
# negligible against a video download and large enough to absorb all three.
_MERGE_SPACE_MARGIN_BYTES = 64 * 1024 * 1024

# The peak of the additive merge holds three live copies of the segment bytes
# simultaneously: the original segments, the accumulated batch temp files, and
# the growing final artefact. The multiplier therefore reflects that three-way
# overlap, not a two-way one (ART-012, P12-B8).
_MERGE_MULTIPLIER: Final[int] = 3

# Number of segments merged per ffmpeg subprocess batch. Shared with
# ``_required_merge_bytes`` so the sizing arithmetic and the merge staging
# cannot drift apart (P12-B8).
_MERGE_BATCH_SIZE: Final[int] = 100


async def iter_process_lines(
    stream: asyncio.StreamReader,
    shutdown_event: asyncio.Event,
    *,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> AsyncIterator[bytes]:
    """Yield lines from a subprocess stream, respecting a shutdown event.

    This consolidates the repeated ``readline`` loop pattern used across
    yt-dlp stdout draining, ffmpeg stderr draining, and progress monitoring
    into a single utility (STR-008).

    The loop terminates when:
    - ``shutdown_event`` is set (an optional ``on_shutdown`` callback can
      cancel the subprocess so ``readline`` unblocks), or
    - the stream is exhausted (``readline`` returns an empty bytes object), or
    - a line arrives that the reader cannot hold in one piece — see Raises.

    A generator-scoped watcher task awaits ``shutdown_event.wait()`` so that
    a stop landing *while* ``readline()`` is blocked is observed without
    waiting for the child to produce more output. The watcher invokes the
    shared ``fire()`` helper — the single place ``on_shutdown`` is called —
    so the callback fires at most once whether the stop arrives mid-read or
    between lines. The same guard runs between the discard reads taken after
    an over-long line, so a stop that lands mid-drain is honoured too.

    Args:
        stream: A subprocess ``StreamReader`` to read lines from.
        shutdown_event: asyncio Event that signals cancellation.
        on_shutdown: Optional async callback invoked when shutdown is
            detected, e.g. to cancel the underlying subprocess.

    Yields:
        Raw ``bytes`` lines from the stream (including trailing newline).
        Never a fragment: a line is either yielded whole or dropped whole.

    Raises:
        DownloadError: A child output line is longer than the stream reader's
            limit, so ``readline()`` cannot return it. The remainder of the
            stream is consumed first — without buffering it and without
            spinning — so the pipe reaches EOF and the caller can still reap
            the child; child output after that line is then discarded.
    """
    fired = False

    async def fire() -> None:
        """The ONLY place on_shutdown is invoked, so it cannot fire twice."""
        nonlocal fired
        if on_shutdown is None or fired:
            return
        fired = True
        await on_shutdown()

    async def _watch_shutdown() -> None:
        """Unblocks a read that is already in flight."""
        await shutdown_event.wait()
        await fire()

    async def _discard_after_overlong_line() -> int:
        """Consume the rest of a stream whose current line the reader cannot hold.

        ``StreamReader.readline`` raises once a line does not fit the reader's
        limit, and asyncio has already dropped that line's bytes by the time it
        does. What is left is whatever the child writes next, and nothing reads
        it. On this platform the exit waiter completes only once the returncode
        is set *and* every pipe has reached EOF, so an undrained pipe makes
        ``process.wait()`` unable to return even after ``kill()``. This consumes
        that remainder and returns how many bytes were discarded.

        Nothing is accumulated: each read is capped and dropped, so a child that
        never emits a newline cannot grow the reader's buffer. Every iteration
        consumes at least the bytes it just read, so the loop cannot spin. It
        ends at EOF — the only thing ``process.wait()`` is waiting for — or at a
        stop, where ``fire()`` turns the stop into the kill that closes the pipe.
        """
        # Bytes consumed per step. Any positive size works; this matches the
        # reader's own default limit so one step cannot exceed the window the
        # transport keeps buffered.
        chunk_bytes = 65536
        discarded = 0
        while True:
            if shutdown_event.is_set():
                await fire()
                return discarded
            chunk = await stream.read(chunk_bytes)
            if not chunk:
                return discarded
            discarded += len(chunk)

    watch_task = asyncio.create_task(_watch_shutdown())
    try:
        while True:
            if shutdown_event.is_set():
                await fire()
                break
            try:
                line = await stream.readline()
            except ValueError as exc:
                # A line the reader cannot hold in one piece; asyncio has already
                # dropped it. Drain what follows so the pipe can reach EOF, then
                # surface it as a product error. The try wraps ONLY this read: a
                # ValueError thrown in at the yield below belongs to the consumer.
                discarded = await _discard_after_overlong_line()
                logger.error(
                    "subprocess_line_overrun",
                    discarded_bytes=discarded,
                    error=str(exc),
                )
                raise DownloadError(
                    f"A child output line exceeded the stream reader's limit and "
                    f"could not be read; {format_bytes(discarded)} ({discarded} "
                    f"bytes) of further child output were discarded so the pipe "
                    f"could reach EOF. Child output after that line was not "
                    f"captured. Reader said: {exc}"
                ) from exc
            if not line:
                break
            yield line
    finally:
        if not watch_task.done():
            watch_task.cancel()
            try:
                await watch_task
            except asyncio.CancelledError:
                pass


def check_ffmpeg_available() -> bool:
    """Check whether the ``ffmpeg`` binary is present on the system PATH.

    Results are cached within the process so the (cheap) ``shutil.which``
    lookup runs at most once (write-once cache — no invalidation hook).
    The probe itself is silent: the single warning that names the install
    step is emitted by the call site (``perform_download``) when this
    returns ``False``, so the answer is **used**, not discarded (D6, TRN-008).

    Returns:
        ``True`` if ``ffmpeg`` was found on ``PATH``, ``False`` otherwise.
    """
    global _ffmpeg_available
    if _ffmpeg_available is None:
        _ffmpeg_available = shutil.which("ffmpeg") is not None
    return _ffmpeg_available


async def cancel_subprocess(
    process: asyncio.subprocess.Process,
    *,
    timeout: float = 5.0,
) -> bool:
    """Cancel and terminate a subprocess gracefully (SIGTERM → SIGKILL).

    Works with any ``asyncio.subprocess.Process``, including both ffmpeg and
    yt-dlp subprocesses.

    On POSIX, when the child was spawned with ``start_new_session=True`` (the
    boundary keyword applied at every spawn site), the child is a session
    leader whose process group ID equals its PID. A supplementary
    ``os.killpg`` signal reaches any descendant the child started, closing
    TRN-003's orphan case on Unix. On Windows, the boundary keyword is
    ``CREATE_NEW_PROCESS_GROUP``, which only routes console Ctrl+C — the
    group is **not** killable by pid, and descendants the child started for
    itself survive. See ``docs/11-guides/vkdownloader-limitations.md``.

    Args:
        process: The asyncio subprocess to cancel.
        timeout: Seconds to wait for graceful termination before force kill.

    Returns:
        ``True`` if the direct child was terminated (by the ladder),
        ``False`` if the process was already gone — the clean outcome.
        Callers must not treat ``False`` as a failure to stop the child;
        a second ``returncode is None`` check is the correct discriminator
        for a genuinely not-clean termination.

        Note: ``True`` means the **direct child** was terminated, not that
        the whole tree was reaped. On POSIX, descendants that share the
        child's process group also receive the signal, but they are not
        children of this process and are never awaited.
    """
    logger.info("cancelling_subprocess", pid=process.pid)
    try:
        # TRN-003: On POSIX, signal the whole process group, not just the
        # child pid. The child was spawned with start_new_session=True, so
        # its pgid == pid (setsid guarantees this). os.getpgid is unnecessary
        # and does not protect against PID recycling. Guarded by
        # returncode is None to mirror asyncio's gh-127049 fix: signalling
        # an already-reaped PID can hit an unrelated recycled process group.
        if not _IS_WINDOWS and process.returncode is None:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(process.pid, signal.SIGTERM)  # type: ignore[attr-defined]
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
            return True
        except TimeoutError:
            # Force-kill the whole group on POSIX, then the pid-only alias.
            if not _IS_WINDOWS and process.returncode is None:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
            process.kill()
            await process.wait()
            return True
    except ProcessLookupError:
        return False


# Backward-compatible alias — this function was originally named
# cancel_ffmpeg_process when it only managed ffmpeg processes. It was
# generalized for yt-dlp subprocesses as well; the old name is kept so
# existing imports from downstream code and tests continue to work.
cancel_ffmpeg_process = cancel_subprocess


async def _await_ffmpeg_with_timeout(
    process: asyncio.subprocess.Process,
    timeout: float,
) -> tuple[bytes | None, bytes | None]:
    """Await ffmpeg process communication with timeout and graceful cancellation.

    Wraps ``process.communicate()`` in ``asyncio.wait_for`` and ensures the
    process is terminated via ``cancel_subprocess`` on cancellation or
    timeout, preventing orphaned subprocesses.

    Args:
        process: The ffmpeg subprocess to await.
        timeout: Maximum seconds to wait for the process to complete.

    Returns:
        Tuple of (stdout, stderr) on success.

    Raises:
        asyncio.TimeoutError: If the process does not complete within ``timeout``.
    """
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return stdout, stderr
    except (TimeoutError, asyncio.CancelledError):
        await cancel_ffmpeg_process(process)
        raise


def _build_ffmpeg_concat_command(file_list_path: Path, output_file: Path) -> list[str]:
    """Build ffmpeg concat command for merging files.

    Args:
        file_list_path: Path to the file list text file.
        output_file: Path to the output file.

    Returns:
        Command list for ffmpeg.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(file_list_path),
        "-c",
        "copy",
        str(output_file),
    ]

    return cmd


async def _merge_batch_segments(
    batch_files: list[Path], temp_dir: Path, download_timeout: float = _MERGE_STAGE_TIMEOUT
) -> Path | None:
    """Merge a batch of segments into a single temp file.

    This stage is additive: it does not remove its input segments. They are
    deleted on the whole-merge success tail in ``_merge_segments_batched``
    (D-13), so a failure in a later stage cannot destroy already-merged data.

    Args:
        batch_files: List of segment file paths to merge.
        temp_dir: Directory for temp files.
        download_timeout: Maximum seconds for the ffmpeg subprocess to complete.

    Returns:
        Path to merged batch file on success, None on failure.
    """
    # Derive batch_start from first file's index (e.g., "00000.ts" -> 0)
    batch_start = int(batch_files[0].stem)
    batch_output = temp_dir / f"batch_{batch_start:05d}.ts"
    file_list_path = temp_dir / f"batch_list_{batch_start}.txt"

    # Write file list for concat demuxer
    with open(file_list_path, "w", encoding="utf-8") as f:
        for segment_path in batch_files:
            f.write(f"file '{segment_path.as_posix()}'\n")

    cmd = _build_ffmpeg_concat_command(file_list_path, batch_output)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **_SPAWN_BOUNDARY_KWARGS,  # type: ignore[arg-type]
        )
        stdout, stderr = await _await_ffmpeg_with_timeout(process, download_timeout)
    except TimeoutError:
        logger.error("batch_merge_timeout", timeout=download_timeout)
        return None
    except OSError as exc:
        # TRN-008 / B13 arm (b): a missing ffmpeg binary surfaces here as
        # FileNotFoundError (an OSError subclass) from create_subprocess_exec.
        # Catch it so the merge produces a product record instead of an
        # escaping exception that the resume layer would mislabel.
        logger.error(
            "merge_spawn_failed",
            error=str(exc),
            hint=_MERGE_HINT,
        )
        return None

    if process.returncode != 0:
        error = stderr.decode() if stderr else "Unknown error"
        logger.error("batch_merge_failed", error=sanitize_text_for_log(error)[:200])
        return None

    # D-13: this stage is additive. Its input segments are removed only after
    # the whole merge has succeeded, by _merge_segments_batched's success
    # tail, and not here: a per-batch deletion destroyed the only copy of
    # every already-merged byte whenever a later stage failed (NET-001, phase
    # 03 -- 0 of 250 originals survived a failed final stage).
    # The concat list is a different matter. It is rebuilt from the surviving
    # inputs on every attempt, so keeping it would be pure residue, while the
    # segment files are the residue that is worth keeping.
    file_list_path.unlink()

    return batch_output


async def _perform_final_merge(
    temp_files: list[Path], output_file: Path, download_timeout: float = _MERGE_STAGE_TIMEOUT
) -> bool:
    """Merge all batch temp files into final output.

    Args:
        temp_files: List of batch temp file paths to merge.
        output_file: Final output file path.
        download_timeout: Maximum seconds for the ffmpeg subprocess to complete.

    Returns:
        True on success, False on failure.
    """
    final_list_path = temp_files[0].parent / "final_list.txt"

    # Write file list for concat demuxer
    with open(final_list_path, "w", encoding="utf-8") as f:
        for temp_file in temp_files:
            f.write(f"file '{temp_file.as_posix()}'\n")

    cmd = _build_ffmpeg_concat_command(final_list_path, output_file)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **_SPAWN_BOUNDARY_KWARGS,  # type: ignore[arg-type]
        )
        stdout, stderr = await _await_ffmpeg_with_timeout(process, download_timeout)
    except TimeoutError:
        logger.error("final_merge_timeout", timeout=download_timeout)
        return False
    except OSError as exc:
        # TRN-008 / B13 arm (b): a missing ffmpeg binary surfaces here as
        # FileNotFoundError (an OSError subclass) from create_subprocess_exec.
        # Catch it so the merge produces a product record instead of an
        # escaping exception that the resume layer would mislabel.
        logger.error(
            "merge_spawn_failed",
            error=str(exc),
            hint=_MERGE_HINT,
        )
        return False

    if process.returncode == 0:
        logger.info("merge_completed", output=str(output_file))
        final_list_path.unlink()
        for tf in temp_files:
            tf.unlink()
        return True

    logger.error(
        "final_merge_failed",
        error=sanitize_text_for_log(stderr.decode())[:200] if stderr else "Unknown",
    )
    return False


def _required_merge_bytes(segment_paths: Iterable[Path]) -> int:
    """Compute the free space the batched merge needs for ``segment_paths``.

    The peak of the additive merge is the segments plus the accumulated batch
    temps plus the growing final output, all alive at the same instant before
    the success tail unlinks the originals. The volume must therefore hold
    three copies of the segment bytes at once: the originals, the batch temp
    files, and the final artefact. The requirement is therefore three times
    the measured segment bytes, plus a fixed safety margin.

    A segment that has already disappeared contributes nothing: its absence is
    a different precondition, reported with a precise message by the merge's
    own existence check rather than by a byte count.

    Args:
        segment_paths: The segment files the merge is about to read.

    Returns:
        Free space, in bytes, the merge requires. Never negative.
    """
    segment_bytes = 0
    for segment_path in segment_paths:
        try:
            segment_bytes += segment_path.stat().st_size
        except OSError:
            # An unstattable segment is counted as zero. Whether it blocks the
            # merge is decided by the existence check that runs next, which
            # names the file; a size probe must not pre-empt that verdict.
            continue
    return segment_bytes * _MERGE_MULTIPLIER + _MERGE_SPACE_MARGIN_BYTES


def _check_merge_space(segment_paths: Iterable[Path], segments_dir: Path) -> None:
    """Fail before the merge starts when the volume cannot hold its own output.

    The merge is the one download step that cannot be resumed — its input
    segments are still needed — so running out of space halfway through turns a
    large download into a failed one with no partial result, and the failure
    surfaces as a raw filesystem error at an unknown point. Probing first turns
    that into a single actionable message at a known point, before any ffmpeg
    subprocess exists to have written anything.

    Args:
        segment_paths: The segment files the merge is about to read.
        segments_dir: Directory holding the segments; the volume probed is the
            one the merge writes into.

    Raises:
        DownloadError: If the volume holds less free space than the merge needs.
    """
    try:
        free_bytes = shutil.disk_usage(segments_dir).free
    except OSError as exc:
        # An unreadable or unusual mount is not evidence of a full one, and a
        # failed probe must not block downloads that would otherwise succeed.
        # Log it and proceed; ffmpeg reports the failure if it is real.
        logger.warning("merge_space_probe_failed", error=str(exc))
        return

    required_bytes = _required_merge_bytes(segment_paths)
    if free_bytes >= required_bytes:
        return

    hint = (
        "Free disk space, write the download to another output volume, or select a "
        "lower quality so the video is smaller."
    )
    # structlog carries the structured fields for log aggregation; the
    # exception carries the same facts for the user, because not every caller
    # logs a caught exception (batch_downloader._download_single returns the
    # status label alone). Emitting both means the message survives whichever
    # layer handles the failure.
    logger.error(
        "merge_insufficient_disk_space",
        required_bytes=required_bytes,
        available_bytes=free_bytes,
        hint=hint,
    )
    raise DownloadError(
        f"Not enough free space to merge the video: {format_bytes(required_bytes)} "
        f"required ({required_bytes} bytes) but only {format_bytes(free_bytes)} "
        f"available ({free_bytes} bytes). {hint}"
    )


async def _merge_segments_batched(
    segments_dir: Path,
    output_file: Path,
    count: int,
    download_timeout: float = _MERGE_STAGE_TIMEOUT,
) -> Path | None:
    """Merge segments in batches to avoid command line limits.

    Probes the output volume's free space before the first ffmpeg subprocess is
    spawned, and fails with an actionable message when the volume cannot hold
    both the segments and the artefact they become.

    Args:
        segments_dir: Directory containing segment files.
        output_file: Final output file path.
        count: Total number of segments to merge.
        download_timeout: Maximum seconds for each ffmpeg subprocess to complete.

    Returns:
        Path to output file on success, None on failure.

    Raises:
        FileNotFoundError: If segment files are missing.
        DownloadError: If the volume lacks the free space the merge requires.
            A precondition failure like the missing-segment one above, not a
            merge failure — which is why it raises rather than returning None.
            It is deliberately not an ``OSError`` subclass: the yt-dlp resume
            path wraps this call in ``except ExtractionError``
            (ytdlp_downloader.py). A missing muxer raises ``FileNotFoundError``
            — an ``OSError`` but **not** an ``ExtractionError`` subclass — so the
            resume handler does not swallow it; the merge sinks catch it at
            their own ``except OSError`` arm instead. A ``DownloadError``
            likewise survives: it is neither class, so the resume path cannot
            relabel it "failed_to_refresh_token" and return None, losing the
            message.
    """
    batch_size = _MERGE_BATCH_SIZE
    temp_files: list[Path] = []
    merged_inputs: list[Path] = []

    _check_merge_space(
        (segments_dir / f"{i:05d}.ts" for i in range(count)),
        segments_dir,
    )

    # Process in batches
    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        batch_files = [segments_dir / f"{i:05d}.ts" for i in range(batch_start, batch_end)]

        # Check all files exist - raise error if missing instead of silent continue
        if not all(f.exists() for f in batch_files):
            missing = [f.name for f in batch_files if not f.exists()]
            raise FileNotFoundError(f"Missing segment files for merge: {missing}")

        result = await _merge_batch_segments(batch_files, segments_dir, download_timeout)
        if result is None:
            return None

        temp_files.append(result)
        merged_inputs.extend(batch_files)

    # Final merge of all batches
    if temp_files and await _perform_final_merge(temp_files, output_file, download_timeout):
        # D-13: the input segments are deleted here, and only here, because
        # this is the first point at which the whole merge is known to have
        # succeeded. The shape this replaces deleted each batch's inputs the
        # moment that batch merged and swept every accumulated batch temp on
        # any non-success exit, so a failure in a later stage destroyed both
        # copies of every already-merged byte: 250 segments with a failed
        # final stage left 0 originals, and a failed second batch left 150 of
        # 250 with the first batch's temp deleted by the same sweep.
        #
        # `missing_ok=True` because `returncode == 0` from the final stage
        # attests only to the batch temps -- the originals are not in
        # `final_list.txt` -- so a bare unlink() would assert a precondition
        # no code path established. The bare unlink() on the temps and on the
        # final list stays: there the exit code does attest.
        #
        # Deferred (same tag): a graceful stage failure now leaves the temps
        # beside a complete segment set, so the `*.ts` counts in
        # segment_downloader.py also count `batch_*.ts` and a resumed run will
        # not re-trigger the merge. Excluding the merge temps is phase 07's
        # ART-004; discharged by P12-B6 in segment_downloader._tally_and_merge. The compensating control
        # is `_log_preserve_segments`, which now reports the working
        # directory's `*.ts` count and the clear-the-directory action instead
        # of implying the directory is resumable as it stands. The merge peak
        # sizing (3x the segment bytes via _MERGE_MULTIPLIER) is discharged
        # by P12-B8 — both _required_merge_bytes and this comment now carry
        # the corrected multiplier.
        for segment_path in merged_inputs:
            segment_path.unlink(missing_ok=True)

        return output_file

    return None
