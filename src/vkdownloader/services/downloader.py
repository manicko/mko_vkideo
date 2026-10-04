"""HLS downloader service with orchestration.

This module focuses on orchestration. yt-dlp-specific logic (subprocess
management, cookie-file lifecycle, retry-with-resume fallback) has been
extracted to :mod:`vkdownloader.services.ytdlp_downloader`.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

from structlog import get_logger

from ..config import Settings
from ..exceptions import QualityNotAvailableError
from ..models.enums import CookieSource, DownloadMethod
from ..models.quality import QualitySpec
from ..models.video import Stream, VideoWithStreams
from ..services.extractor import VKVideoExtractor
from ..utils.security import _resolve_output_file, sanitize_title
from ..utils.url_sanitizer import _strip_auth_params
from .concurrency import SemaphoreLike
from .cookies import _cookies_to_netscape  # noqa: F401 — backward-compat re-export
from .downloader_throttle import (
    _retry_429_with_backoff,  # noqa: F401 — backward-compat re-export
)
from .ffmpeg_utils import (
    _MERGE_HINT,
    _build_ffmpeg_concat_command,
    _merge_segments_batched,
    cancel_subprocess,
    check_ffmpeg_available,
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
    _is_ytdlp_progress_line,  # noqa: F401 — backward-compat re-export
    _parse_ytdlp_progress,  # noqa: F401 — backward-compat re-export
    _resolve_cookies,
    download_with_ytdlp_with_resume_fallback,
)

if TYPE_CHECKING:
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
#       perform_download, download_video, _semaphore_context
#   * ytdlp_downloader.py:
#       download_with_ytdlp_with_resume_fallback, _build_ytdlp_cli_command,
#       _echo_ytdlp_line, _parse_ytdlp_progress,
#       _resolve_cookies, _create_temp_cookie_file, _await_first_and_cancel_others
#   * ffmpeg_utils.py:
#       cancel_subprocess, _build_ffmpeg_concat_command,
#       _merge_segments_batched, check_ffmpeg_available
__all__ = [
    "cancel_subprocess",
    "check_ffmpeg_available",
    "download_hls_with_resume",
    "download_with_ytdlp_with_resume_fallback",
    "download_video",
    "perform_download",
    "_await_first_and_cancel_others",
    "_build_ffmpeg_concat_command",
    "_build_ytdlp_cli_command",
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
        quality: Quality token (``best``, ``worst``, ``unknown``, or a height in
            pixels the video offers, e.g. ``1072``).
        output_file: Output file path.
        method: Download method (yt-dlp or auto).
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
            dropped). Only governs yt-dlp output.

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
    # binary before a long download fails at the merge step. The probe's answer
    # is used here — not discarded — to emit one actionable warning when the
    # muxer is absent (D6, TRN-008).
    if not check_ffmpeg_available():
        logger.warning(
            "ffmpeg_missing_for_merge",
            hint=_MERGE_HINT,
        )

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
            case DownloadMethod.AUTO:
                # Auto mode downloads via yt-dlp's native HLS downloader with segment-level resume
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
    quality: QualitySpec,
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
        quality: Parsed quality request (a keyword or an exact height).
        output: Output directory for downloaded video.
        method: Download method (yt-dlp or auto).
        settings: Application settings with environment-loaded values.
        log_available_qualities: If True, log available stream qualities.
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
        semaphore: Optional per-video semaphore for concurrency control. This is a
            single permit acquired once for the entire video download (D-01).
        progress_callback: Optional callback for per-URL segment progress.
        output_index: Index for fallback filename (0 for single, index for batch).
        echo: When False, suppresses yt-dlp's native console echo (progress
            lines are emitted at DEBUG level instead; non-progress lines are
            dropped). Only governs yt-dlp output.
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
        str(quality),  # DF-001: pass the original request, not the degraded str(stream.quality)
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
