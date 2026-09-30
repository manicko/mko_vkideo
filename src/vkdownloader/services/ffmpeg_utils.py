"""FFmpeg utilities for command building, process management, and progress parsing."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from structlog import get_logger

from ..exceptions import DownloadError
from ..utils.formatting import format_bytes

logger = get_logger(__name__)

# Module-level cache: PATH lookup happens only once per process lifetime
_ffmpeg_available: bool | None = None

# Free space kept in reserve on top of the size arithmetic below. It covers
# what the byte figures cannot see: the batch temp file that coexists with the
# segments it was written from, filesystem block-allocation slack, and whatever
# another process writes between the probe and the first output byte. 64 MiB is
# negligible against a video download and large enough to absorb all three.
_MERGE_SPACE_MARGIN_BYTES = 64 * 1024 * 1024


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
    - the stream is exhausted (``readline`` returns an empty bytes object).

    Args:
        stream: A subprocess ``StreamReader`` to read lines from.
        shutdown_event: asyncio Event that signals cancellation.
        on_shutdown: Optional async callback invoked when shutdown is
            detected, e.g. to cancel the underlying subprocess.

    Yields:
        Raw ``bytes`` lines from the stream (including trailing newline).
    """
    while True:
        if shutdown_event.is_set():
            if on_shutdown is not None:
                await on_shutdown()
            break
        line = await stream.readline()
        if not line:
            break
        yield line


def check_ffmpeg_available() -> bool:
    """Check whether the ``ffmpeg`` binary is present on the system PATH.

    Results are cached within the process so the (cheap) ``shutil.which``
    lookup runs at most once. When ``ffmpeg`` is not found a warning is
    emitted on the first detection, so users learn about the missing
    dependency *before* a long download finishes and the merge step fails
    with an opaque ``FileNotFoundError``.

    Returns:
        ``True`` if ``ffmpeg`` was found on ``PATH``, ``False`` otherwise.
    """
    global _ffmpeg_available
    if _ffmpeg_available is None:
        _ffmpeg_available = shutil.which("ffmpeg") is not None
        if not _ffmpeg_available:
            logger.warning(
                "ffmpeg_not_found",
                hint=(
                    "ffmpeg binary not found on PATH; downloads using ffmpeg "
                    "or segment merge will fail"
                ),
            )
    return _ffmpeg_available


@dataclass
class FfmpegProgress:
    """Progress state from ffmpeg -progress pipe output."""

    frame: int | None = None
    fps: float | None = None
    speed: float | None = None
    total_size: int | None = None
    out_time_us: int | None = None
    out_time_ms: int | None = None
    out_time: str | None = None
    progress: str | None = None


# Type alias for progress key handler
_ProgressHandler = Callable[[str, FfmpegProgress], None]


# Lookup table for progress key handlers
_PROGRESS_KEY_HANDLERS: dict[str, _ProgressHandler] = {
    "frame": lambda v, p: setattr(p, "frame", int(v) if v != "N/A" else None),
    "fps": lambda v, p: setattr(p, "fps", float(v) if v != "N/A" else None),
    "speed": lambda v, p: setattr(p, "speed", float(v.rstrip("x")) if v != "N/A" else None),
    "total_size": lambda v, p: setattr(p, "total_size", int(v) if v != "N/A" else None),
    "out_time_us": lambda v, p: setattr(p, "out_time_us", int(v) if v != "N/A" else None),
    "out_time_ms": lambda v, p: setattr(p, "out_time_ms", int(v) if v != "N/A" else None),
    "out_time": lambda v, p: setattr(p, "out_time", v if v != "N/A" else None),
}


class ProgressParser:
    """Parser for ffmpeg KEY=VALUE progress output."""

    @staticmethod
    def parse_line(line: str) -> tuple[str, str] | None:
        """Parse a single progress line in KEY=VALUE format.

        Args:
            line: Raw line from ffmpeg stderr.

        Returns:
            Tuple of (key, value) if valid format, None otherwise.
        """
        if "=" in line:
            key, value = line.strip().split("=", 1)
            return key, value
        return None


async def read_progress(
    stderr: asyncio.StreamReader,
    stderr_collector: list[bytes] | None = None,
    *,
    shutdown_event: asyncio.Event | None = None,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> AsyncIterator[FfmpegProgress]:
    """Read ffmpeg progress output in real-time.

    Args:
        stderr: StreamReader from ffmpeg process stderr.
        stderr_collector: Optional list to collect raw stderr lines for error handling.
        shutdown_event: Optional asyncio Event; if set, the loop breaks early.
        on_shutdown: Optional async callback invoked when shutdown is detected.

    Yields:
        FfmpegProgress objects as they are parsed.
    """
    progress = FfmpegProgress()
    async for line in iter_process_lines(
        stderr, shutdown_event or asyncio.Event(), on_shutdown=on_shutdown
    ):
        if stderr_collector is not None:
            stderr_collector.append(line)
        parsed = ProgressParser.parse_line(line.decode())
        if parsed:
            key, value = parsed
            handler = _PROGRESS_KEY_HANDLERS.get(key)
            if handler is not None:
                handler(value, progress)
            elif key == "progress":
                progress.progress = value
                yield progress
                if value == "end":
                    break
                progress = FfmpegProgress()  # Reset for next block


async def cancel_subprocess(
    process: asyncio.subprocess.Process,
    *,
    timeout: float = 5.0,
) -> bool:
    """Cancel and terminate a subprocess gracefully (SIGTERM → SIGKILL).

    Works with any ``asyncio.subprocess.Process``, including both ffmpeg and
    yt-dlp subprocesses.

    Args:
        process: The asyncio subprocess to cancel.
        timeout: Seconds to wait for graceful termination before force kill.

    Returns:
        True if process was cancelled, False if process was already gone.
    """
    logger.info("cancelling_subprocess", pid=process.pid)
    try:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
            return True
        except TimeoutError:
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
    batch_files: list[Path], temp_dir: Path, download_timeout: float = 300.0
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

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await _await_ffmpeg_with_timeout(process, download_timeout)
    except TimeoutError:
        logger.error("batch_merge_timeout", timeout=download_timeout)
        return None

    if process.returncode != 0:
        error = stderr.decode() if stderr else "Unknown error"
        logger.error("batch_merge_failed", error=error[:200])
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
    temp_files: list[Path], output_file: Path, download_timeout: float = 300.0
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

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await _await_ffmpeg_with_timeout(process, download_timeout)
    except TimeoutError:
        logger.error("final_merge_timeout", timeout=download_timeout)
        return False

    if process.returncode == 0:
        logger.info("merge_completed", output=str(output_file))
        final_list_path.unlink()
        for tf in temp_files:
            tf.unlink()
        return True

    logger.error("final_merge_failed", error=stderr.decode()[:200] if stderr else "Unknown")
    return False


def _required_merge_bytes(segment_paths: Iterable[Path]) -> int:
    """Compute the free space the batched merge needs for ``segment_paths``.

    Both merge stages write their output while their input is still on disk —
    the final artefact is produced from the batch temp files before those are
    unlinked — so the volume must hold the segments *and* a full copy of them
    at the same time. The requirement is therefore twice the measured segment
    bytes, plus a fixed safety margin.

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
    return segment_bytes * 2 + _MERGE_SPACE_MARGIN_BYTES


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
    segments_dir: Path, output_file: Path, count: int, download_timeout: float = 300.0
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
            path wraps this call in ``except (ExtractionError, OSError)``
            (ytdlp_downloader.py), which would swallow a FileNotFoundError
            here, relabel it "failed_to_refresh_token" and return None, losing
            the message.
    """
    batch_size = 100
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
        # ART-004; this block edits no `*.ts` glob. The compensating control
        # is `_log_preserve_segments`, which now reports the working
        # directory's `*.ts` count and the clear-the-directory action instead
        # of implying the directory is resumable as it stands. The merge peak
        # also moves from 2x to 3x the segment bytes; the sizing belongs to
        # phase 07's ART-012.
        for segment_path in merged_inputs:
            segment_path.unlink(missing_ok=True)

        return output_file

    return None
