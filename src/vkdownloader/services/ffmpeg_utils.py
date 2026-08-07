"""FFmpeg utilities for command building, process management, and progress parsing."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path

from structlog import get_logger

logger = get_logger(__name__)

# Module-level cache: PATH lookup happens only once per process lifetime
_ffmpeg_available: bool | None = None


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
) -> AsyncIterator[FfmpegProgress]:
    """Read ffmpeg progress output in real-time.

    Args:
        stderr: StreamReader from ffmpeg process stderr.
        stderr_collector: Optional list to collect raw stderr lines for error handling.

    Yields:
        FfmpegProgress objects as they are parsed.
    """
    progress = FfmpegProgress()
    while True:
        line = await stderr.readline()
        if not line:
            break
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


async def cancel_ffmpeg_process(
    process: asyncio.subprocess.Process,
    *,
    timeout: float = 5.0,
) -> bool:
    """Cancel and terminate an ffmpeg process gracefully.

    Args:
        process: The ffmpeg process to cancel.
        timeout: Seconds to wait for graceful termination before force kill.

    Returns:
        True if process was cancelled, False if process was already gone.
    """
    logger.info("cancelling_ffmpeg_process", pid=process.pid)
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


async def _await_ffmpeg_with_timeout(
    process: asyncio.subprocess.Process,
    timeout: float,
) -> tuple[bytes | None, bytes | None]:
    """Await ffmpeg process communication with timeout and graceful cancellation.

    Wraps ``process.communicate()`` in ``asyncio.wait_for`` and ensures the
    process is terminated via ``cancel_ffmpeg_process`` on cancellation or
    timeout, preventing orphaned ffmpeg subprocesses.

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

    # Remove individual segment files after batch merge
    for segment_path in batch_files:
        segment_path.unlink()
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


async def _merge_segments_batched(
    segments_dir: Path, output_file: Path, count: int, download_timeout: float = 300.0
) -> Path | None:
    """Merge segments in batches to avoid command line limits.

    Args:
        segments_dir: Directory containing segment files.
        output_file: Final output file path.
        count: Total number of segments to merge.
        download_timeout: Maximum seconds for each ffmpeg subprocess to complete.

    Returns:
        Path to output file on success, None on failure.
    """
    batch_size = 100
    temp_files: list[Path] = []

    try:
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

        # Final merge of all batches
        if temp_files:
            if await _perform_final_merge(temp_files, output_file, download_timeout):
                return output_file

        return None
    finally:
        # Remove any partial batch temp files created by this merge on failure.
        # On success these were already unlinked by _perform_final_merge.
        for tf in temp_files:
            tf.unlink(missing_ok=True)
