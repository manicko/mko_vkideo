"""HLS downloader service with ffmpeg integration and orchestration."""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yt_dlp
from playwright.async_api import Cookie
from structlog import get_logger

from ..config import Settings
from ..exceptions import ExtractionError, QualityNotAvailableError, QualityParseError
from ..models.dtos import HLSDownloadRequest
from ..models.enums import CookieSource, DownloadMethod, QualityEnum
from ..models.video import Stream, VideoWithStreams
from ..services.extractor import VKVideoExtractor
from ..utils.security import _resolve_output_file, validate_output_path
from ..utils.url_sanitizer import _strip_auth_params
from .concurrency import SemaphoreLike
from .cookies import _cookies_to_netscape
from .downloader_throttle import _retry_429_with_backoff, get_shutdown_event
from .ffmpeg_utils import (
    FfmpegProgress,
    ProgressParser,
    _build_ffmpeg_concat_command,
    _merge_segments_batched,
    cancel_ffmpeg_process,
    check_ffmpeg_available,
    read_progress,
)
from .quality import QualitySelector
from .segment_downloader import (
    _cleanup_segments,
    _download_segment,
    _download_segment_parallel,
    _download_segment_sequential,
    _fetch_playlist_with_retry,
    _parse_m3u8_segments,
    download_hls_with_resume,
)
from .signal_handlers import setup_signal_handlers

if TYPE_CHECKING:
    from .downloader_throttle import URLBackoffCoordinator

logger = get_logger(__name__)

# Maximum retry attempts for getting new token on resume failure
MAX_RESUME_RETRIES = 3


def _semaphore_context(semaphore: SemaphoreLike | None) -> Any:
    """Return an async context manager for semaphore acquisition.

    When ``semaphore`` is None (single-download mode), returns a no-op context
    manager so callers can always use ``async with _semaphore_context(semaphore):``.
    """
    if semaphore is not None:
        return semaphore
    return nullcontext()


def _create_temp_cookie_file(cookies: str | list[Cookie]) -> Path:
    """Create a temporary Netscape cookie file in the system temp directory.

    Unlike writing to the download output directory (which may be cloud-synced),
    the system temp directory is private and not synced, reducing the risk of
    live session-cookie leakage on abnormal termination.

    Args:
        cookies: Either a raw cookie string (Netscape format) or a list of
            Playwright Cookie objects.

    Returns:
        Path to the temporary cookie file (created with 0o600 permissions
        via tempfile.mkstemp). The caller is responsible for cleanup.
    """
    content = _cookies_to_netscape(cookies)
    fd, path = tempfile.mkstemp(suffix=".cookies.txt", prefix="vk_cookies_")
    try:
        os.write(fd, content.encode())
        os.close(fd)
    except Exception:
        os.close(fd)
        Path(path).unlink(missing_ok=True)
        raise
    return Path(path)


@asynccontextmanager
async def _temp_headers_file(headers: str) -> AsyncIterator[Path]:
    """Async context manager for temporary headers file for ffmpeg @file syntax.

    Creates a temporary file with headers content, ensuring proper cleanup
    after use. This prevents cookies from appearing in process argument lists.

    Args:
        headers: Header string to write to temporary file.

    Yields:
        Path to the temporary file.
    """
    fd, path = tempfile.mkstemp(suffix=".headers", prefix="vk_ffmpeg_")
    try:
        os.write(fd, headers.encode())
        os.close(fd)
        yield Path(path)
    finally:
        Path(path).unlink(missing_ok=True)


async def _await_first_and_cancel_others(
    *tasks: asyncio.Task[Any],
) -> tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]:
    """Launch tasks concurrently, await first completion, cancel remaining.

    Args:
        *tasks: Tasks to await concurrently.

    Returns:
        Tuple of (done_tasks, pending_tasks) after cancellation.
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
    return done, pending


def _parse_quality_to_enum(quality: str) -> QualityEnum:
    """
    Parse quality string to QualityEnum for stream selection.

    Args:
        quality: Quality string (e.g., "720", "1080", "best", "worst", "720p").

    Returns:
        QualityEnum value matching the string.

    Raises:
        QualityParseError: If quality string cannot be parsed to QualityEnum.
    """
    try:
        return QualityEnum(quality)
    except ValueError:
        normalized = quality.rstrip("p") if quality else "best"
        try:
            return QualityEnum(normalized)
        except ValueError:
            raise QualityParseError(quality) from None


def _build_ytdlp_options(
    output_file: Path,
    quality_str: str,
    user_agent: str,
    settings: Settings,
    cookies: str | None,
    raw_cookies: list[Cookie] | None,
    video_id: str,
    progress_callback: Callable[[str, int, int], None] | None = None,
    shutdown_event: asyncio.Event | None = None,
) -> tuple[dict[str, Any], Path | None]:
    """
    Build yt-dlp options dictionary for video download.

    Args:
        output_file: Path to save downloaded video.
        quality_str: Quality string without p suffix (e.g., 720).
        user_agent: User agent string for requests.
        settings: Application settings.
        cookies: Optional cookies string for backward compatibility.
        raw_cookies: Optional raw Cookie objects for Netscape format.
        video_id: Video ID for progress callback.
        progress_callback: Optional callback for download progress.
        shutdown_event: Optional asyncio.Event checked by the progress hook
            to abort in-progress downloads during graceful shutdown.

    Returns:
        Tuple of (ydl_opts dict, cookie_file Path or None).
    """
    # Build format selector: use height filter for numeric quality, bare best otherwise
    format_selector = (
        f"best[height<={quality_str}]" if quality_str and quality_str.isdigit() else "best"
    )

    # yt-dlp boundary: its options mapping accepts heterogeneous values (str, int,
    # bool, nested dicts, callables) and is not statically typed upstream, so `Any`
    # is the pragmatic value type at this integration edge.
    ydl_opts: dict[str, Any] = {
        "outtmpl": str(output_file),
        "quiet": False,
        "no_warnings": True,
        "format": format_selector,
        "nocheckcertificate": not settings.ssl_verify,
        "hls_prefer_native": True,
        "concurrent_fragments": settings.max_concurrent_downloads,
        "throttledratelimit": settings.throttled_rate,
        "http_chunk_size": settings.http_chunk_size,
        "http_headers": {
            "User-Agent": user_agent,
            "Referer": "https://vkvideo.ru/",
        },
        "socket_timeout": settings.download_timeout,
        "retries": settings.max_retries,
        "fragment_retries": settings.max_retries,
    }

    # Add cookies file generation if cookies provided
    cookie_file: Path | None = None
    if raw_cookies:
        cookie_file = _create_temp_cookie_file(raw_cookies)
        ydl_opts["cookiefile"] = str(cookie_file)
    elif cookies:
        cookie_file = _create_temp_cookie_file(cookies)
        ydl_opts["cookiefile"] = str(cookie_file)

    # Add progress hook with shutdown signal awareness
    if shutdown_event is not None or progress_callback is not None:

        def _progress_hook(d: dict[str, Any]) -> None:
            # Abort in-progress download promptly when shutdown is requested
            if shutdown_event is not None and shutdown_event.is_set():
                raise RuntimeError("Download cancelled")
            if progress_callback is None:
                return
            if d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes_estimate", 0) or d.get("total_bytes", 0)
                progress_callback(video_id, downloaded, total or 1)
            elif d.get("status") == "finished":
                progress_callback(video_id, 1, 1)

        ydl_opts["progress_hooks"] = [_progress_hook]

    return ydl_opts, cookie_file


# Backward-compatibility re-export facade.
#
# This module intentionally re-exports symbols that were historically importable
# from ``vkdownloader.services.downloader``. Downstream code (and tests) still
# import from here, so the names below are kept as a stable public surface even
# though most implementations now live in focused sibling modules.
#
# Symbol ownership (where each name is actually defined):
#   * Owned by this module (downloader.py):
#       HLSDownloader, perform_download,
#       download_with_ytdlp_with_resume_fallback,
#       _build_ytdlp_options, _await_first_and_cancel_others
#   * ffmpeg_utils.py:
#       FfmpegProgress, ProgressParser, read_progress,
#       cancel_ffmpeg_process, _build_ffmpeg_concat_command,
#       _merge_segments_batched
#   * segment_downloader.py:
#       download_hls_with_resume, _cleanup_segments, _download_segment,
#       _download_segment_parallel, _download_segment_sequential,
#       _fetch_playlist_with_retry, _parse_m3u8_segments
#   * downloader_throttle.py:
#       _retry_429_with_backoff
#   * cookies.py:
#       _cookies_to_netscape
#   * signal_handlers.py:
#       setup_signal_handlers
__all__ = [
    "FfmpegProgress",
    "HLSDownloader",
    "ProgressParser",
    "cancel_ffmpeg_process",
    "check_ffmpeg_available",
    "download_hls_with_resume",
    "download_with_ytdlp_with_resume_fallback",
    "download_video",
    "perform_download",
    "read_progress",
    "_await_first_and_cancel_others",
    "_build_ffmpeg_concat_command",
    "_build_ytdlp_options",
    "_cleanup_segments",
    "_cookies_to_netscape",
    "_download_segment",
    "_download_segment_parallel",
    "_download_segment_sequential",
    "_fetch_playlist_with_retry",
    "_merge_segments_batched",
    "_parse_m3u8_segments",
    "_retry_429_with_backoff",
    "setup_signal_handlers",
]


class HLSDownloader:
    """Downloads HLS streams to MP4 using ffmpeg."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize HLSDownloader with optional settings.

        Args:
            settings: Application settings. Uses global settings if not provided.
        """
        self.settings = settings if settings is not None else Settings()

    async def download_with_ffmpeg(
        self,
        m3u8_url: str,
        output_file: Path,
        quality: str = "best",
        cookies: str | None = None,
        progress_callback: Callable[[FfmpegProgress], None] | None = None,
    ) -> Path | None:
        """Download HLS stream to MP4 using ffmpeg.

        Args:
            m3u8_url: HLS playlist URL.
            output_file: Output file path.
            quality: Quality string (e.g., "720", "1080").
            cookies: Optional cookies string for authenticated downloads.
            progress_callback: Optional callback for real-time progress updates.

        Returns:
            Path to output file on success, None on failure.
        """
        logger.info(
            "starting_ffmpeg_download",
            url=_strip_auth_params(m3u8_url),
            output=str(output_file),
            quality=quality,
            has_cookies=bool(cookies),
        )

        # Build headers content
        cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""
        headers_content = (
            f"User-Agent: {self.settings.user_agent}\r\n"
            f"Referer: https://vkvideo.ru/\r\n"
            f"{cookie_part}"
        )

        async with _temp_headers_file(headers_content) as headers_file:
            cmd: list[str] = [
                "ffmpeg",
                "-y",
                "-progress",
                "pipe:2",
                "-nostats",
                "-headers",
                f"@{headers_file}",  # Safe: only filename in args
            ]
            if not self.settings.ssl_verify:
                cmd.extend(["-tls_verify", "0"])
            cmd.extend(["-i", m3u8_url, "-c", "copy", str(output_file)])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stderr_chunks: list[bytes] = []

                shutdown_event = get_shutdown_event()

                async def _monitor_progress() -> None:
                    """Read progress and call callback, while collecting stderr for error handling."""
                    assert process.stderr is not None
                    async for progress in read_progress(
                        process.stderr, stderr_collector=stderr_chunks
                    ):
                        if shutdown_event.is_set():
                            if not await cancel_ffmpeg_process(process):
                                logger.warning("ffmpeg_cancel_not_clean", pid=process.pid)
                            break
                        if progress_callback:
                            progress_callback(progress)

                async def _drain_stderr() -> None:
                    """Drain stderr to prevent buffer deadlock when no callback is provided."""
                    assert process.stderr is not None
                    while True:
                        if shutdown_event.is_set():
                            if not await cancel_ffmpeg_process(process):
                                logger.warning("ffmpeg_cancel_not_clean", pid=process.pid)
                            break
                        line = await process.stderr.readline()
                        if not line:
                            break
                        stderr_chunks.append(line)

                # Run process wait and stderr reading concurrently.
                # _await_first_and_cancel_others may cancel process.wait() if the
                # reader task finishes first (e.g. read_progress breaks on
                # "progress=end" before ffmpeg exits). We reap the process
                # afterwards to ensure returncode is set before the success check.
                if progress_callback:
                    process_task = asyncio.create_task(process.wait())
                    monitor_task = asyncio.create_task(_monitor_progress())
                    await _await_first_and_cancel_others(process_task, monitor_task)
                else:
                    process_task = asyncio.create_task(process.wait())
                    drain_task = asyncio.create_task(_drain_stderr())
                    await _await_first_and_cancel_others(process_task, drain_task)

                # Ensure the process is fully reaped before reading returncode.
                # If wait() was cancelled, returncode may still be None.
                if process.returncode is None:
                    await process.wait()

                stderr_data = b"".join(stderr_chunks) if stderr_chunks else b""

                if shutdown_event.is_set():
                    if not await cancel_ffmpeg_process(process):
                        logger.warning("ffmpeg_cancel_not_clean", pid=process.pid)
                    return None

                if process.returncode != 0:
                    error_msg = stderr_data.decode() if stderr_data else "Unknown ffmpeg error"
                    logger.error(
                        "ffmpeg_download_failed", returncode=process.returncode, error=error_msg
                    )
                    return None

                logger.info("ffmpeg_download_completed", output=str(output_file))
                return output_file
            finally:
                # Guarantee ffmpeg is terminated even on CancelledError or
                # unhandled exception, preventing orphaned processes.
                if process.returncode is None:
                    if not await cancel_ffmpeg_process(process):
                        logger.warning("ffmpeg_cancel_not_clean", pid=process.pid)


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
    semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
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
        quality: Quality string.
        extractor: VKVideoExtractor for token refresh.
        settings: Application settings.
        cookies: Optional cookies string for ffmpeg headers.
        raw_cookies: Optional raw Cookie objects for Netscape format (preserves domain).
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
        semaphore: Optional shared semaphore for work-stealing concurrency in batch downloads.
        progress_callback: Optional callback for per-URL segment progress (video_id, downloaded, total).

    Returns:
        Path to downloaded file on success, None on failure.
    """
    if settings is None:
        settings = Settings()

    retry_count = 0

    while retry_count <= MAX_RESUME_RETRIES:
        result = await _download_with_ytdlp(
            video_url, output_file, quality, settings, cookies, raw_cookies, progress_callback
        )

        if result:
            if retry_count > 0:
                logger.info("download_completed_after_retries", retries=retry_count)
            return result

        retry_count += 1

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
                semaphore,
                progress_callback,
            )
        ) is not None:
            return segment_result

    # All retries exhausted without success
    logger.error("max_retries_exceeded")
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
    semaphore: SemaphoreLike | None,
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
        quality: Quality string.
        retry_count: Current retry attempt number.
        extractor: VKVideoExtractor for token refresh.
        settings: Application settings.
        backoff_coordinator: Optional shared URLBackoffCoordinator.
        semaphore: Optional shared semaphore for concurrency control.
        progress_callback: Optional callback for per-URL segment progress.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    logger.warning(
        "download_interrupted_switching_to_segments",
        path=str(output_file),
        size=output_file.stat().st_size,
        retry=retry_count,
    )
    logger.info("attempting_segment_resume", retry=retry_count)

    try:
        if extractor is None:
            extractor = VKVideoExtractor(settings=settings)
        # Force browser for token refresh during resume (recovery scenario)
        browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(
            video_url, force_browser=True
        )
        if browser_streams:
            try:
                quality_enum = _parse_quality_to_enum(quality)
                selector = QualitySelector()
                selected_stream = selector.select(browser_streams, quality_enum)
                m3u8_url = str(selected_stream.url)
                logger.info(
                    "fresh_token_obtained_for_resume",
                    quality=quality,
                    selected_quality=selected_stream.quality,
                )
            except QualityNotAvailableError:
                logger.error(
                    "requested_quality_not_available_in_browser_streams",
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
                semaphore=semaphore,
            )
    except (ExtractionError, OSError) as e:
        logger.warning("failed_to_refresh_token", error=str(e))
    except ValueError as e:
        logger.error("invalid_quality_for_browser_streams", error=str(e))
        raise

    return None


async def _download_with_ytdlp(
    video_url: str,
    output_file: Path,
    quality: str,
    settings: Settings,
    cookies: str | None = None,
    raw_cookies: list[Cookie] | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> Path | None:
    """Download using yt-dlp."""
    logger.info(
        "starting_ytdlp_download",
        url=_strip_auth_params(video_url),
        output=str(output_file),
        quality=quality,
    )
    quality_str = quality.replace("p", "") if quality else "720"
    user_agent = settings.user_agent
    shutdown_event = get_shutdown_event()

    # Extract video_id for progress callback (matches segment downloader pattern)
    video_id = video_url.split("_")[-1] if "_" in video_url else video_url

    # Build yt-dlp options using extracted helper (must happen before _download closure captures it)
    ydl_opts, cookie_file = _build_ytdlp_options(
        output_file,
        quality_str,
        user_agent,
        settings,
        cookies,
        raw_cookies,
        video_id,
        progress_callback,
        shutdown_event=shutdown_event,
    )

    def _download() -> str:
        # Check shutdown before starting download
        if shutdown_event.is_set():
            raise RuntimeError("Download cancelled")

        if not settings.ssl_verify:
            logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            return str(output_file)
        except Exception as e:
            if "cancelled" in str(e).lower() or shutdown_event.is_set():
                raise RuntimeError("Download cancelled") from e
            raise
        finally:
            # Clean up cookie file after download completes (success or failure)
            if cookie_file is not None and cookie_file.exists():
                cookie_file.unlink()
                logger.debug("cookie_file_cleaned_up", path=str(cookie_file))

    loop = asyncio.get_running_loop()

    # Create task for the executor to allow cancellation
    download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))

    try:
        result = await download_task
        return Path(result)
    except asyncio.CancelledError:
        logger.info("yt_dlp_download_cancelled")
        # Cancel the executor task (though the thread will continue, it will be
        # cleaned up when the process exits or on subsequent runs)
        if not download_task.done():
            download_task.cancel()
        raise
    except (RuntimeError, OSError) as e:
        logger.error("download_failed", error=str(e))
        return None


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
        quality: Quality string for stream selection.

    Returns:
        Tuple of (updated m3u8_url, cookies string, raw cookies for Netscape format).

    Raises:
        QualityNotAvailableError: If requested quality is BEST but not available in browser streams.
    """
    if settings.cookie_source == CookieSource.BROWSER:
        browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(url)
        if browser_streams:
            quality_enum = _parse_quality_to_enum(quality)
            # Browser streams always have quality="best" with height=None.
            # Only run quality selection for BEST; for numeric qualities, reuse the
            # pre-selected m3u8_url from the caller (yt-dlp already selected the stream).
            if quality_enum == QualityEnum.BEST:
                selector = QualitySelector()
                selected_stream = selector.select(browser_streams, quality_enum)
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


async def perform_download(
    url: str,
    quality: str,
    output_file: Path,
    method: DownloadMethod,
    extractor: VKVideoExtractor | None = None,
    settings: Settings | None = None,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    video_data: VideoWithStreams | None = None,
    selected_stream: Stream | None = None,
) -> Path | None:
    """Perform video download using the specified method.

    Args:
        url: VK Video URL to download.
        quality: Quality string (e.g., "720", "1080").
        output_file: Output file path.
        method: Download method (yt-dlp, ffmpeg, or auto).
        extractor: Optional VKVideoExtractor for token refresh.
        settings: Application settings.
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
        semaphore: Optional shared semaphore for work-stealing concurrency in batch downloads.
        progress_callback: Optional callback for per-URL segment progress (video_id, downloaded, total).
        video_data: Optional pre-extracted video data with streams. When provided, skips extraction.
        selected_stream: Optional pre-selected stream. When provided, used instead of streams[0].

    Returns:
        Path to downloaded file on success, None on failure.
    """
    logger.info(
        "starting_download",
        method=str(method),
        url=_strip_auth_params(url),
        quality=quality,
        output=str(output_file),
    )

    if settings is None:
        settings = Settings()

    # Probe ffmpeg availability once at startup so users learn about a missing
    # binary before a long download fails at the merge step.
    check_ffmpeg_available()

    if extractor is None:
        extractor = VKVideoExtractor(settings=settings)

    # Use pre-extracted data when provided, otherwise extract streams
    if video_data is not None and selected_stream is not None:
        streams = video_data.streams
        m3u8_url = str(selected_stream.url)
    else:
        # Get m3u8 URL via yt-dlp (most reliable for extraction)
        video_data = await extractor.extract_streams(url)
        streams = video_data.streams

        if not streams:
            logger.error("no_streams_found", url=_strip_auth_params(url))
            return None

        m3u8_url = str(streams[0].url)

    # Acquire the shared semaphore (if provided) to bound concurrency across
    # all download methods. When None (single-download mode), no limiting.
    semaphore_context = _semaphore_context(semaphore)

    async with semaphore_context:
        match method:
            case DownloadMethod.YTDLP:
                m3u8_url, cookies, raw_cookies = await _resolve_cookies(
                    extractor, settings, url, m3u8_url, quality
                )
                return await download_with_ytdlp_with_resume_fallback(
                    url,
                    m3u8_url,
                    output_file,
                    quality,
                    extractor,
                    settings,
                    cookies=cookies,
                    raw_cookies=raw_cookies,
                    backoff_coordinator=backoff_coordinator,
                    semaphore=semaphore,
                    progress_callback=progress_callback,
                )
            case DownloadMethod.FFMPEG:
                if not settings.ssl_verify:
                    logger.warning(
                        "ssl_verify_ignored_for_ffmpeg",
                        url=_strip_auth_params(url),
                        hint="The --no-ssl-verify flag is not applied to the direct ffmpeg "
                        "download path; use --method yt-dlp or --method auto for SSL "
                        "verification control on the CDN connection.",
                    )
                m3u8_url, cookies, raw_cookies = await _resolve_cookies(
                    extractor, settings, url, m3u8_url, quality
                )
                downloader = HLSDownloader(settings=settings)

                ffmpeg_progress_callback: Callable[[FfmpegProgress], None] | None = None
                if progress_callback is not None:
                    video_id = url.split("_")[-1] if "_" in url else url

                    def _ffmpeg_progress_adapter(fp: FfmpegProgress) -> None:
                        downloaded = fp.total_size if fp.total_size is not None else 0
                        progress_callback(video_id, downloaded, downloaded)

                    ffmpeg_progress_callback = _ffmpeg_progress_adapter

                result = await downloader.download_with_ffmpeg(
                    m3u8_url,
                    output_file,
                    quality,
                    cookies,
                    progress_callback=ffmpeg_progress_callback,
                )
                if result is None:
                    logger.info("ffmpeg_failed_fallback_to_segment_download")
                    result = await download_hls_with_resume(
                        HLSDownloadRequest(
                            video_url=url,
                            m3u8_url=m3u8_url,
                            output_file=output_file,
                            quality=quality,
                            cookies=cookies,
                            progress_callback=progress_callback,
                        ),
                        settings=settings,
                        extractor=extractor,
                        backoff_coordinator=backoff_coordinator,
                        semaphore=semaphore,
                    )
                return result
            case DownloadMethod.AUTO:
                # Auto: try yt-dlp first (more reliable), segment download for resume
                if settings.cookie_source == CookieSource.NONE:
                    # Skip browser cookie resolution when explicitly disabled
                    m3u8_url, cookies, raw_cookies = m3u8_url, None, None
                else:
                    m3u8_url, cookies, raw_cookies = await _resolve_cookies(
                        extractor, settings, url, m3u8_url, quality
                    )
                return await download_with_ytdlp_with_resume_fallback(
                    url,
                    m3u8_url,
                    output_file,
                    quality,
                    extractor,
                    settings,
                    cookies=cookies,
                    raw_cookies=raw_cookies,
                    backoff_coordinator=backoff_coordinator,
                    semaphore=semaphore,
                    progress_callback=progress_callback,
                )
            case _:
                logger.error("unknown_download_method", method=str(method))
                return None


async def download_video(
    url: str,
    quality: QualityEnum,
    output: Path,
    method: DownloadMethod,
    settings: Settings,
    *,
    max_retries_override: int | None = None,
    log_available_qualities: bool = False,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    output_index: int = 0,
) -> Path | None:
    """Extract streams, select quality, resolve output, and download a video.

    Shared orchestration for single-download and batch-download CLI handlers.
    Encapsulates the extract -> guard-empty -> select -> resolve -> download
    pipeline so that both entry-point paths delegate to a single implementation.

    Args:
        url: Video URL to download.
        quality: Video quality selection.
        output: Output directory for downloaded video.
        method: Download method (yt-dlp, ffmpeg, or auto).
        settings: Application settings with environment-loaded values.
        max_retries_override: Optional max_retries override from CLI.
        log_available_qualities: If True, log available stream qualities.
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
        semaphore: Optional shared semaphore for concurrency control.
        progress_callback: Optional callback for per-URL segment progress.
        output_index: Index for fallback filename (0 for single, index for batch).

    Returns:
        Path to the downloaded file on success, None on failure.

    Raises:
        QualityNotAvailableError: If no streams found or requested quality unavailable.
        VideoNotFoundError: If the video cannot be found or is unavailable.
    """
    if max_retries_override is not None:
        settings = settings.model_copy(update={"max_retries": max_retries_override})

    extractor = VKVideoExtractor(settings=settings)
    video = await extractor.extract_streams(url)

    if not video.streams:
        raise QualityNotAvailableError(
            str(quality),
            [],
            "No streams found for this video; the video may be private or unavailable",
        )

    selector = QualitySelector()

    if log_available_qualities:
        available = selector.list_available_qualities(video.streams)
        logger.info("available_streams", count=len(video.streams))
        logger.info("available_qualities", qualities=available[:8])

    stream = selector.select(video.streams, quality)

    output_file = _resolve_output_file(video, output, settings, output_index)

    return await perform_download(
        url,
        str(stream.quality),
        output_file,
        method,
        extractor,
        settings,
        backoff_coordinator=backoff_coordinator,
        semaphore=semaphore,
        progress_callback=progress_callback,
        video_data=video,
        selected_stream=stream,
    )
