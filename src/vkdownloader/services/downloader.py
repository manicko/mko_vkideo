"""HLS downloader service with ffmpeg integration and orchestration.

This module focuses on orchestration and the ffmpeg download path.
yt-dlp-specific logic (subprocess management, cookie-file lifecycle,
retry-with-resume fallback) has been extracted to
:mod:`vkdownloader.services.ytdlp_downloader`.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

from structlog import get_logger

from ..config import Settings
from ..exceptions import QualityNotAvailableError
from ..models.dtos import HLSDownloadRequest
from ..models.enums import CookieSource, DownloadMethod, QualityEnum
from ..models.video import Stream, VideoWithStreams
from ..services.extractor import VKVideoExtractor
from ..utils.security import _resolve_output_file, sanitize_title
from ..utils.url_sanitizer import _strip_auth_params, sanitize_text_for_log
from .concurrency import SemaphoreLike
from .cookies import _cookies_to_netscape  # noqa: F401 — backward-compat re-export
from .downloader_throttle import (
    _retry_429_with_backoff,  # noqa: F401 — backward-compat re-export
    get_shutdown_event,
)
from .ffmpeg_utils import (
    FfmpegProgress,
    ProgressParser,
    _build_ffmpeg_concat_command,
    _merge_segments_batched,
    cancel_subprocess,
    check_ffmpeg_available,
    iter_process_lines,
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
from .ytdlp_downloader import (
    _attempt_segment_resume,  # noqa: F401 — backward-compat re-export
    _await_first_and_cancel_others,
    _build_ytdlp_cli_command,  # noqa: F401 — backward-compat re-export
    _create_temp_cookie_file,  # noqa: F401 — backward-compat re-export
    _download_with_ytdlp,  # noqa: F401 — backward-compat re-export
    _echo_ytdlp_line,  # noqa: F401 — backward-compat re-export
    _parse_quality_to_enum,  # noqa: F401 — backward-compat re-export
    _parse_ytdlp_progress,  # noqa: F401 — backward-compat re-export
    _resolve_cookies,
    download_with_ytdlp_with_resume_fallback,
)

if TYPE_CHECKING:
    from playwright.async_api import Cookie

    from .downloader_throttle import URLBackoffCoordinator

logger = get_logger(__name__)


def _semaphore_context(
    semaphore: SemaphoreLike | None,
) -> SemaphoreLike | AbstractAsyncContextManager[object]:
    """Return an async context manager for semaphore acquisition.

    When ``semaphore`` is None (single-download mode), returns a no-op context
    manager so callers can always use ``async with _semaphore_context(semaphore):``.
    """
    if semaphore is not None:
        return semaphore
    return nullcontext()


@asynccontextmanager
async def _temp_argfile(args: list[str]) -> AsyncIterator[Path]:
    """Async context manager for temporary ffmpeg argument file.

    Writes all ffmpeg arguments to a temp file (mode 0o600, applied on POSIX;
    see D-11) and yields the path. The caller invokes ``ffmpeg @<argfile>`` so
    that sensitive values (e.g. signed m3u8 URLs with CDN tokens) never appear
    in the process command-line arguments — they are only visible inside
    the temp file, which is removed after use.

    Each argument is written on its own line. Arguments containing
    whitespace are shell-quoted via :func:`shlex.quote` so that ffmpeg's
    ``@file`` parser handles them correctly.

    Args:
        args: List of ffmpeg arguments (options and values, in order).

    Yields:
        Path to the temporary argument file.
    """
    fd, path = tempfile.mkstemp(suffix=".args", prefix="vk_ffmpeg_")
    try:
        os.close(fd)  # Close fd first; chmod needs a path on Windows
        # SEC-001/SEC-003: request owner-only access before the arguments, which
        # carry signed CDN tokens, are written to disk. 0o600 sets POSIX
        # permission bits; on Windows os.chmod toggles only the read-only
        # attribute, so the owner-only guarantee is not offered there (D-11) and
        # the mode is requested for its POSIX effect only.
        os.chmod(path, 0o600)
        content = _format_argfile(args)
        Path(path).write_text(content)
        yield Path(path)
    finally:
        Path(path).unlink(missing_ok=True)


def _format_argfile(args: list[str]) -> str:
    """Format a list of arguments into ffmpeg @file syntax content.

    Each argument is written on its own line. Arguments containing
    whitespace or special characters are wrapped in single quotes
    (matching ffmpeg's ``@file`` quoting rules).

    Args:
        args: List of ffmpeg arguments in order.

    Returns:
        String content suitable for writing to an argument file.
    """
    quoted = [shlex.quote(arg) for arg in args]
    return "\n".join(quoted) + "\n"


# Backward-compatibility re-export facade.
#
# This module intentionally re-exports symbols that were historically
# importable from ``vkdownloader.services.downloader``. Downstream code
# (and tests) still imports from here, so the names below are kept as a
# stable public surface even though most implementations now live in
# focused sibling modules.
#
# Symbol ownership (where each name is actually defined):
#   * Owned by this module (downloader.py):
#       HLSDownloader, perform_download, download_video, _semaphore_context,
#       _temp_argfile, _format_argfile
#   * ytdlp_downloader.py:
#       download_with_ytdlp_with_resume_fallback, _build_ytdlp_cli_command,
#       _download_with_ytdlp, _echo_ytdlp_line, _parse_ytdlp_progress,
#       _parse_quality_to_enum, _resolve_cookies, _create_temp_cookie_file,
#       _await_first_and_cancel_others, _attempt_segment_resume
#   * ffmpeg_utils.py:
#       FfmpegProgress, ProgressParser, read_progress,
#       cancel_subprocess, _build_ffmpeg_concat_command,
#       _merge_segments_batched, check_ffmpeg_available
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
    "cancel_subprocess",
    "check_ffmpeg_available",
    "download_hls_with_resume",
    "download_with_ytdlp_with_resume_fallback",
    "download_video",
    "perform_download",
    "read_progress",
    "_await_first_and_cancel_others",
    "_build_ffmpeg_concat_command",
    "_build_ytdlp_cli_command",
    "_cleanup_segments",
    "_cookies_to_netscape",
    "_download_segment",
    "_download_segment_parallel",
    "_download_segment_sequential",
    "_fetch_playlist_with_retry",
    "_format_argfile",
    "_merge_segments_batched",
    "_parse_m3u8_segments",
    "_retry_429_with_backoff",
    "_temp_argfile",
    "_format_argfile",
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
        raw_cookies: list[Cookie] | None = None,
        progress_callback: Callable[[FfmpegProgress], None] | None = None,
    ) -> Path | None:
        """Download HLS stream to MP4 using ffmpeg.

        Cookies (if provided) are passed via the ffmpeg ``cookies`` protocol
        option using a temporary Netscape cookie file created by
        :func:`_create_temp_cookie_file` (SEC-003/INT-001). This replaces the
        non-functional ``-headers @file`` approach where ffmpeg's ``@file``
        is a response-file reader, not a per-option value loader.

        User-Agent and Referer are passed as a plain string via ``-headers``
        (inside the argfile, so not visible in process listings).

        Args:
            m3u8_url: HLS playlist URL.
            output_file: Output file path.
            quality: Quality string (e.g., "720", "1080").
            cookies: Optional cookies string for authenticated downloads.
            raw_cookies: Optional list of Playwright Cookie objects.
            progress_callback: Optional callback for real-time progress updates.

        Returns:
            Path to output file on success, None on failure.
        """
        logger.info(
            "starting_ffmpeg_download",
            url=_strip_auth_params(m3u8_url),
            output=str(output_file),
            quality=quality,
            has_cookies=bool(cookies) or bool(raw_cookies),
        )

        # INT-001: Pass cookies via the ffmpeg `cookies` protocol option
        # using the Netscape cookie file (created with 0o600 permissions).
        # This replaces the broken `-headers @file` approach. The cookie file
        # path is appended to the m3u8 URL as a query parameter; since the URL
        # is now inside the argfile (SEC-001), the cookie file path is also
        # protected from the process listing.
        cookie_file: Path | None = None
        if raw_cookies:
            cookie_file = _create_temp_cookie_file(raw_cookies)
        elif cookies:
            cookie_file = _create_temp_cookie_file(cookies)

        try:
            # Append cookies_file to the m3u8 URL if we have a cookie file
            ffmpeg_url = m3u8_url
            if cookie_file:
                separator = "&" if "?" in m3u8_url else "?"
                ffmpeg_url = f"{m3u8_url}{separator}cookies=file:{cookie_file}"

            # Build headers as a plain string (NOT @file syntax — INT-001 fix).
            # This goes inside the argfile so it is not visible in process args.
            headers_content = (
                f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n"
            )

            # Build all ffmpeg arguments. The m3u8 URL (containing signed CDN
            # tokens and the cookies_file path) is written into the argfile,
            # NOT passed as a command-line argument, so it never appears in
            # /proc/<pid>/cmdline or `ps` output. (SEC-001)
            ffmpeg_args: list[str] = [
                "-y",
                "-progress",
                "pipe:2",
                "-nostats",
                "-headers",
                headers_content,
                "-i",
                ffmpeg_url,
                "-c",
                "copy",
                str(output_file),
            ]
            if not self.settings.ssl_verify:
                ffmpeg_args.insert(5, "-tls_verify")
                ffmpeg_args.insert(6, "0")

            async with _temp_argfile(ffmpeg_args) as argfile:
                cmd: list[str] = ["ffmpeg", f"@{argfile}"]

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

                    async def _on_shutdown() -> None:
                        if not await cancel_subprocess(process):
                            logger.warning(
                                "ffmpeg_cancel_not_clean",
                                pid=process.pid,
                                url=_strip_auth_params(m3u8_url),
                            )

                    async for progress in read_progress(
                        process.stderr,
                        stderr_collector=stderr_chunks,
                        shutdown_event=shutdown_event,
                        on_shutdown=_on_shutdown,
                    ):
                        if progress_callback is not None:
                            progress_callback(progress)

                async def _drain_stderr() -> None:
                    """Drain stderr to prevent buffer deadlock when no callback is provided."""
                    assert process.stderr is not None

                    async def _on_shutdown() -> None:
                        if not await cancel_subprocess(process):
                            logger.warning(
                                "ffmpeg_cancel_not_clean",
                                pid=process.pid,
                                url=_strip_auth_params(m3u8_url),
                            )

                    async for line in iter_process_lines(
                        process.stderr, shutdown_event, on_shutdown=_on_shutdown
                    ):
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
                    if not await cancel_subprocess(process):
                        logger.warning(
                            "ffmpeg_cancel_not_clean",
                            pid=process.pid,
                            url=_strip_auth_params(m3u8_url),
                        )
                    return None

                if process.returncode != 0:
                    # SEC-002: sanitize subprocess output to redact any signed
                    # CDN URLs or cookie file paths that ffmpeg may echo in
                    # error messages before persisting to log files.
                    error_msg = stderr_data.decode() if stderr_data else "Unknown ffmpeg error"
                    error_msg = sanitize_text_for_log(error_msg)
                    logger.error(
                        "ffmpeg_download_failed",
                        url=_strip_auth_params(m3u8_url),
                        returncode=process.returncode,
                        error=error_msg,
                    )
                    return None

                logger.info("ffmpeg_download_completed", output=str(output_file))
                return output_file
            finally:
                # Guarantee ffmpeg is terminated even on CancelledError or
                # unhandled exception, preventing orphaned processes.
                if process.returncode is None:
                    if not await cancel_subprocess(process):
                        logger.warning(
                            "ffmpeg_cancel_not_clean",
                            pid=process.pid,
                            url=_strip_auth_params(m3u8_url),
                        )
        finally:
            # Clean up the temporary cookie file (created with 0o600).
            if cookie_file:
                cookie_file.unlink(missing_ok=True)


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
    *,
    echo: bool = True,
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
        semaphore: Optional per-video semaphore for concurrency control. This is a
        single permit acquired once for the entire download (see D-01: the
        segment layer does not re-acquire from it).
        progress_callback: Optional callback for per-URL segment progress (video_id, downloaded, total).
        video_data: Optional pre-extracted video data with streams. When provided, skips extraction.
        selected_stream: Optional pre-selected stream. When provided, used instead of streams[0].
        echo: When False, suppresses yt-dlp's native console echo (progress
            lines are emitted at DEBUG level instead; non-progress lines are
            dropped). Only governs yt-dlp output — has no effect on the ffmpeg
            or segment paths.

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
        extractor = VKVideoExtractor(settings=settings, backoff_coordinator=backoff_coordinator)

    # Use pre-extracted data when provided, otherwise extract streams
    if video_data is not None and selected_stream is not None:
        streams = video_data.streams
        m3u8_url = str(selected_stream.url)
    else:
        # Get m3u8 URL via yt-dlp (most reliable for extraction)
        video_data = await extractor.extract_streams(url)
        streams = video_data.streams

        if not streams:
            logger.error(
                "no_streams_found",
                url=_strip_auth_params(url),
                error_code="no_streams",
            )
            raise QualityNotAvailableError(
                str(quality),
                [],
                "No streams found after extraction; the video may be private or unavailable",
            )

        m3u8_url = str(streams[0].url)

    # Acquire the per-video semaphore (if provided) to bound concurrency across
    # all download methods. This is one permit per video, acquired exactly once
    # here; the segment layer does not re-acquire from it (see D-01).
    # When None (single-download mode), no limiting.
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
                    video_semaphore=semaphore,
                    progress_callback=progress_callback,
                    echo=echo,
                )
            case DownloadMethod.FFMPEG:
                m3u8_url, cookies, raw_cookies = await _resolve_cookies(
                    extractor, settings, url, m3u8_url, quality
                )
                downloader = HLSDownloader(settings=settings)

                ffmpeg_progress_callback: Callable[[FfmpegProgress], None] | None = None
                if progress_callback is not None:
                    video_id = url.split("_")[-1] if "_" in url else url

                    def _ffmpeg_progress_adapter(fp: FfmpegProgress) -> None:
                        # ffmpeg's total_size from -progress is cumulative bytes
                        # written so far, NOT the final file size. Reporting it
                        # as "total" would falsely show 100% progress.
                        # Pass 0 to signal "unknown total" to the caller.
                        downloaded = fp.total_size if fp.total_size is not None else 0
                        progress_callback(video_id, downloaded, 0)

                    ffmpeg_progress_callback = _ffmpeg_progress_adapter

                result = await downloader.download_with_ffmpeg(
                    m3u8_url,
                    output_file,
                    quality,
                    cookies,
                    raw_cookies,
                    progress_callback=ffmpeg_progress_callback,
                )
                if result is None:
                    if get_shutdown_event().is_set():
                        return None
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
                        video_semaphore=semaphore,
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
                    video_semaphore=semaphore,
                    progress_callback=progress_callback,
                    echo=echo,
                )
            case _:
                logger.error(
                    "unknown_download_method",
                    url=_strip_auth_params(url),
                    method=str(method),
                )
                return None


async def download_video(
    url: str,
    quality: QualityEnum,
    output: Path,
    method: DownloadMethod,
    settings: Settings,
    *,
    log_available_qualities: bool = False,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    output_index: int = 0,
    echo: bool = True,
    title_callback: Callable[[str], None] | None = None,
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
        log_available_qualities: If True, log available stream qualities.
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
        semaphore: Optional per-video semaphore for concurrency control. This is a
            single permit acquired once for the entire video download (D-01).
        progress_callback: Optional callback for per-URL segment progress.
        output_index: Index for fallback filename (0 for single, index for batch).
        echo: When False, suppresses yt-dlp's native console echo (progress
            lines are emitted at DEBUG level instead; non-progress lines are
            dropped). Only governs yt-dlp output — has no effect on the ffmpeg
            or segment paths.
        title_callback: Optional callback invoked with the sanitized video
            title immediately after stream extraction succeeds. Used by the
            batch progress reporter for per-file labeling. If the video has no
            title (None), the callback is not invoked.

    Returns:
        Path to the downloaded file on success, None on failure.

    Raises:
        QualityNotAvailableError: If no streams found or requested quality unavailable.
        VideoNotFoundError: If the video cannot be found or is unavailable.
    """
    extractor = VKVideoExtractor(settings=settings, backoff_coordinator=backoff_coordinator)
    video = await extractor.extract_streams(url)

    if title_callback is not None and video.title:
        title_callback(sanitize_title(video.title))

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
        str(quality),  # DF-001: pass original QualityEnum, not degraded str(stream.quality)
        output_file,
        method,
        extractor,
        settings,
        backoff_coordinator=backoff_coordinator,
        semaphore=semaphore,
        progress_callback=progress_callback,
        video_data=video,
        selected_stream=stream,
        echo=echo,
    )
