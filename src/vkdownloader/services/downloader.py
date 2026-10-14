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
from ..utils.security import _resolve_output_file, sanitize_filename_component
from ..utils.url_sanitizer import _strip_auth_params
from .concurrency import SemaphoreLike
from .ffmpeg_utils import (
    _MERGE_HINT,
    check_ffmpeg_available,
)
from .quality import QualitySelector
from .ytdlp_downloader import (
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
        echo: When False, suppresses yt-dlp's native console echo; progress
            lines are emitted at DEBUG level as ``ytdlp_progress_suppressed``
            and non-progress lines are emitted at DEBUG level as
            ``ytdlp_output_suppressed`` (redacted) via
            :func:`~vkdownloader.services.ytdlp_downloader._echo_ytdlp_line`, so
            no child output is silently lost. Only governs yt-dlp output.

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
    video_data: VideoWithStreams | None = None,
    selected_stream: Stream | None = None,
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
        echo: When False, suppresses yt-dlp's native console echo; progress
            lines are emitted at DEBUG level as ``ytdlp_progress_suppressed``
            and non-progress lines are emitted at DEBUG level as
            ``ytdlp_output_suppressed`` (redacted) via
            :func:`~vkdownloader.services.ytdlp_downloader._echo_ytdlp_line`, so
            no child output is silently lost. Only governs yt-dlp output.
        title_callback: Optional callback invoked with the sanitized video
            title immediately after stream extraction succeeds. Used by the
            batch progress reporter for per-file labeling. If the video has no
            title (None), the callback is not invoked.
        video_data: Optional pre-extracted video data with streams. When
            provided together with ``selected_stream``, skips the
            ``extract_streams`` call and uses ``video_data`` directly.
        selected_stream: Optional pre-selected stream. When provided together
            with ``video_data``, used as the m3u8 source for ``perform_download``
            instead of the stream produced by ``QualitySelector.select``.

    Returns:
        Path to the downloaded file on success, None on failure.

    Raises:
        QualityNotAvailableError: If no streams found or requested quality unavailable.
        VideoNotFoundError: If the video cannot be found or is unavailable.
    """
    extractor = VKVideoExtractor(settings=settings, backoff_coordinator=backoff_coordinator)

    # When pre-extracted data is provided (B10, Decision A), skip the network
    # extraction and use the buffered video_data directly, mirroring
    # perform_download's guard at line ~195.
    if video_data is not None and selected_stream is not None:
        video = video_data
    else:
        video = await extractor.extract_streams(url)

    if title_callback is not None and video.title:
        title_callback(sanitize_filename_component(video.title))

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

    # When pre-extracted data is provided, forward the pre-selected stream
    # to perform_download (which will skip its own extraction via the
    # video_data / selected_stream guard).
    if video_data is not None and selected_stream is not None:
        stream = selected_stream

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
