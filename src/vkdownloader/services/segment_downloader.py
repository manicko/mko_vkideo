"""HLS segment downloader with segment-level resume support."""

from __future__ import annotations

import asyncio
import json
import random
import ssl
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import aiohttp
from structlog import get_logger

from ..config import Settings
from ..models.enums import CookieSource
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params
from .downloader_throttle import RETRYABLE_STATUS_CODES, _retry_429_with_backoff, get_shutdown_event
from .ffmpeg_utils import _merge_segments_batched

if TYPE_CHECKING:
    from ..models.dtos import HLSDownloadRequest
    from ..services.extractor import VKVideoExtractor
    from .downloader_throttle import URLBackoffCoordinator

logger = get_logger(__name__)


def _parse_m3u8_segments(content: str) -> list[str]:
    """Parse m3u8 playlist and extract segment URLs."""
    segments = []
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            segments.append(line)
    return segments


async def _download_segment(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    max_concurrent_downloads: int = 1,
    segment_index: int = 0,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_url: str | None = None,
    max_retries: int = 3,
) -> bool:
    """Download a single HLS segment.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        output_path: Path to save the downloaded segment.
        headers: Request headers to use.
        max_concurrent_downloads: Maximum concurrent downloads. When 1, uses retry with backoff.
        segment_index: Index of the segment being downloaded (for logging).
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_url: Original video URL for coordinator keying (required if coordinator provided).
        max_retries: Maximum retry attempts for parallel mode on 429/5xx responses.

    Returns:
        True on success, False on failure.
    """
    if max_concurrent_downloads == 1:
        content = await _retry_429_with_backoff(
            session, segment_url, headers, segment_index, max_retries=max_retries
        )
        if content is not None:
            with open(output_path, "wb") as f:
                f.write(content)
            return True
        return False

    # Existing logic for parallel mode with shared backoff support
    shutdown_event = get_shutdown_event()

    for attempt in range(max_retries):
        # Check for shutdown signal
        if shutdown_event.is_set():
            return False

        # Check for shared backoff before download attempt
        if backoff_coordinator and video_url:
            was_paused = await backoff_coordinator.wait_if_paused(video_url)
            if was_paused and shutdown_event.is_set():
                return False

        try:
            async with session.get(segment_url, headers=headers) as response:
                if response.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await response.read())
                    return True
                logger.warning("segment_download_failed", status=response.status)
                # Notify coordinator of rate limit for shared backoff
                if backoff_coordinator and video_url and response.status in RETRYABLE_STATUS_CODES:
                    await backoff_coordinator.pause(video_url, 10.0)
                # Retry loop continues on retryable status codes
                if response.status not in RETRYABLE_STATUS_CODES:
                    return False
                # Continue to next retry attempt after backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0)  # Brief pause before retry
        except aiohttp.ClientError as e:
            logger.error("segment_download_error", error=str(e))
            if attempt == max_retries - 1:
                return False

    return False


def _load_downloaded_count(metadata_file: Path) -> int:
    """Load downloaded segment count from metadata."""
    if metadata_file.exists():
        try:
            with open(metadata_file, encoding="utf-8") as f:
                data: dict[str, int] = json.load(f)
                return data.get("downloaded_count", 0)
        except (json.JSONDecodeError, OSError):
            return 0
    return 0


def _save_downloaded_count(metadata_file: Path, count: int) -> None:
    """Save downloaded segment count to metadata."""
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump({"downloaded_count": count}, f)


def _cleanup_segments(segments_dir: Path, metadata_file: Path) -> None:
    """Clean up downloaded segments."""
    for f in segments_dir.glob("*"):
        f.unlink()
    try:
        segments_dir.rmdir()
    except OSError:
        pass
    metadata_file.unlink(missing_ok=True)


async def _fetch_playlist_with_retry(
    session: aiohttp.ClientSession,
    video_url: str,
    m3u8_url: str,
    headers: dict[str, str],
    extractor: VKVideoExtractor | None,
    settings: Settings,
    max_retries: int = 3,
) -> str | None:
    """Fetch m3u8 playlist with token refresh on 403/410."""
    current_url = m3u8_url

    for attempt in range(max_retries):
        try:
            async with session.get(current_url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                if response.status in (403, 410) and extractor:
                    logger.info("token_expired_fetching_new", attempt=attempt + 1)
                    # Check if cookie_source allows browser use for token refresh
                    if settings.cookie_source == CookieSource.BROWSER:
                        # Can refresh token via browser (recovery scenario)
                        streams, new_cookies = await extractor.extract_streams_with_cookies(
                            video_url, force_browser=True
                        )
                        if streams:
                            current_url = str(streams[0].url)
                            headers["Cookie"] = new_cookies or ""
                            continue
                    else:
                        # Cannot refresh without browser, log warning and return None
                        logger.warning(
                            "token_refresh_failed_cookie_source",
                            cookie_source=str(settings.cookie_source),
                            reason="Cannot refresh token without browser access",
                        )
                        return None
        except (aiohttp.ClientError, asyncio.CancelledError) as e:
            logger.warning("playlist_fetch_failed", error=str(e))

    return None


def _create_connector(settings: Settings, video_url: str) -> aiohttp.TCPConnector:
    """Create aiohttp connector with SSL settings.

    Args:
        settings: Application settings for SSL verification.
        video_url: Video URL for logging.

    Returns:
        Configured TCPConnector.
    """
    if settings.ssl_verify:
        return aiohttp.TCPConnector(limit=10)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))
    return aiohttp.TCPConnector(ssl=ssl_context, limit=10)


async def _process_downloaded_segments(
    tasks: list[asyncio.Task[bool]],
    metadata_file: Path,
    segments: list[str],
    segments_dir: Path,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
    video_url: str,
) -> Path | None:
    """Process downloaded segments and merge if complete.

    Args:
        tasks: List of download tasks to await.
        metadata_file: Path to progress metadata file.
        segments: List of all segment URLs.
        segments_dir: Directory containing downloaded segments.
        output_file: Final output file path.
        progress_callback: Optional callback for progress updates.
        video_url: Video URL for progress callback video_id extraction.

    Returns:
        Path to merged file on success, None otherwise.
    """
    if not tasks:
        return None

    try:
        # Wait for all tasks to complete, but allow shutdown interruption
        download_results = await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        # Cancel any still-running tasks on interruption
        for task in tasks:
            if not task.done():
                task.cancel()
        # Wait for cancellation to propagate
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("download_cancelled", reason="shutdown_requested")
        return None

    downloaded_count = _load_downloaded_count(metadata_file) + sum(
        1 for r in download_results if r
    )
    _save_downloaded_count(metadata_file, downloaded_count)

    # Call progress callback for per-URL segment updates
    if progress_callback:
        video_id = (
            video_url.split("_")[-1]
            if "_" in video_url
            else video_url
        )
        progress_callback(video_id, downloaded_count, len(segments))

    # All downloaded - merge in batches
    if downloaded_count == len(segments):
        logger.info("merging_segments", count=len(segments))
        result = await _merge_segments_batched(segments_dir, output_file, len(segments))
        if result:
            _cleanup_segments(segments_dir, metadata_file)
        return result

    return None


async def _download_segment_concurrent(
    session: aiohttp.ClientSession,
    idx: int,
    segment_url: str,
    segments_dir: Path,
    semaphore: asyncio.Semaphore,
    m3u8_url: str,
    headers: dict[str, str],
    max_concurrent_downloads: int,
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str,
    max_retries: int,
    is_shared_semaphore: bool,
) -> bool:
    """Download a segment with semaphore rate limiting.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        idx: Index of the segment being downloaded.
        segment_url: URL of the segment to download.
        segments_dir: Directory to save downloaded segments.
        semaphore: Semaphore for rate limiting.
        m3u8_url: Base m3u8 URL for resolving relative segment URLs.
        headers: Request headers to use.
        max_concurrent_downloads: Maximum concurrent downloads.
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_url: Original video URL for coordinator keying.
        max_retries: Maximum retry attempts for parallel mode on 429/5xx responses.
        is_shared_semaphore: Whether the semaphore is shared (skips anti-detection delay).

    Returns:
        True on success, False on failure.
    """
    shutdown_event = get_shutdown_event()

    # Check for shutdown before starting - raise to interrupt gather
    if shutdown_event.is_set():
        raise asyncio.CancelledError("Download cancelled by user")

    async with semaphore:
        # Check for shutdown after acquiring semaphore
        if shutdown_event.is_set():
            raise asyncio.CancelledError("Download cancelled by user")

        full_url = urljoin(m3u8_url, segment_url) if not segment_url.startswith("http") else segment_url

        segment_path = segments_dir / f"{idx:05d}.ts"
        if segment_path.exists() and segment_path.stat().st_size > 0:
            result = True
        else:
            result = await _download_segment(
                session,
                full_url,
                segment_path,
                headers,
                max_concurrent_downloads=max_concurrent_downloads,
                segment_index=idx,
                backoff_coordinator=backoff_coordinator,
                video_url=video_url,
                max_retries=max_retries,
            )

        if result and not is_shared_semaphore and max_concurrent_downloads == 1:
            if shutdown_event.is_set():
                raise asyncio.CancelledError("Download cancelled by user")

            # Anti-detection delay after semaphore release
            delay = 1.5 + random.uniform(0, 0.5)
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
                raise asyncio.CancelledError("Download cancelled by user")
            except TimeoutError:
                pass  # Normal completion

        return result


def _create_segment_download_tasks(
    session: aiohttp.ClientSession,
    segments: list[str],
    segments_dir: Path,
    semaphore: asyncio.Semaphore,
    m3u8_url: str,
    headers: dict[str, str],
    max_concurrent_downloads: int,
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str,
    max_retries: int,
    is_shared_semaphore: bool,
) -> list[asyncio.Task[bool]]:
    """Create tasks for downloading missing segments.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segments: List of segment URLs to download.
        segments_dir: Directory to save downloaded segments.
        semaphore: Semaphore for rate limiting.
        m3u8_url: Base m3u8 URL for resolving relative segment URLs.
        headers: Request headers to use.
        max_concurrent_downloads: Maximum concurrent downloads.
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_url: Original video URL for coordinator keying.
        max_retries: Maximum retry attempts for parallel mode on 429/5xx responses.
        is_shared_semaphore: Whether the semaphore is shared (skips anti-detection delay).

    Returns:
        List of download tasks.
    """
    return [
        asyncio.create_task(_download_segment_concurrent(
            session,
            i,
            seg,
            segments_dir,
            semaphore,
            m3u8_url,
            headers,
            max_concurrent_downloads,
            backoff_coordinator,
            video_url,
            max_retries,
            is_shared_semaphore,
        ))
        for i, seg in enumerate(segments)
        if not (segments_dir / f"{i:05d}.ts").exists()
        or (segments_dir / f"{i:05d}.ts").stat().st_size == 0
    ]


async def _run_download_session(
    m3u8_url: str,
    headers: dict[str, str],
    settings: Settings,
    segments_dir: Path,
    metadata_file: Path,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
    video_url: str,
    extractor: VKVideoExtractor | None,
    backoff_coordinator: URLBackoffCoordinator | None,
    semaphore: asyncio.Semaphore | None,
) -> Path | None:
    """Run the download session with aiohttp client.

    Args:
        m3u8_url: HLS playlist URL.
        headers: Request headers to use.
        settings: Application settings.
        segments_dir: Directory for downloaded segments.
        metadata_file: Path to progress metadata file.
        output_file: Final output file path.
        progress_callback: Optional callback for progress updates.
        video_url: Video URL for progress callback and coordinator keying.
        extractor: Optional extractor for token refresh.
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        semaphore: Optional shared semaphore for work-stealing concurrency.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    connector = _create_connector(settings, video_url)

    async with aiohttp.ClientSession(connector=connector) as session:
        playlist_content = await _fetch_playlist_with_retry(
            session, video_url, m3u8_url, headers, extractor, settings,
            max_retries=settings.max_retries
        )
        if not playlist_content:
            return None

        segments = _parse_m3u8_segments(playlist_content)
        downloaded_count = _load_downloaded_count(metadata_file)
        logger.info("found_segments", count=len(segments), resume_from=downloaded_count)

        semaphore_to_use = semaphore if semaphore is not None else asyncio.Semaphore(settings.max_concurrent_downloads)
        is_shared = semaphore is not None

        tasks = _create_segment_download_tasks(
            session,
            segments,
            segments_dir,
            semaphore_to_use,
            m3u8_url,
            headers,
            settings.max_concurrent_downloads,
            backoff_coordinator,
            video_url,
            settings.max_retries,
            is_shared,
        )

        return await _process_downloaded_segments(
            tasks,
            metadata_file,
            segments,
            segments_dir,
            output_file,
            progress_callback,
            video_url,
        )


async def download_hls_with_resume(
    request: HLSDownloadRequest,
    semaphore: asyncio.Semaphore | None = None,
) -> Path | None:
    """
    Download HLS stream with segment-level resume and token refresh.

    Downloads original HLS segments individually, tracks progress, and can resume
    after interruption by re-downloading missing segments. Uses batched merging
    to handle large number of segments.

    Args:
        request: HLSDownloadRequest containing all download parameters.
        semaphore: Optional shared semaphore for work-stealing concurrency in batch downloads.
            When None, creates a local semaphore based on settings.max_concurrent_downloads.

    Returns:
        Path to downloaded MP4 file on success, None on failure.
    """
    logger.info(
        "starting_segment_download",
        url=_strip_auth_params(request.video_url),
        output=str(request.output_file),
        quality=request.quality,
    )

    settings = request.settings if request.settings is not None else Settings()
    output_file = validate_output_path(request.output_file)

    segments_dir = output_file.parent / f".{output_file.stem}_segments"
    metadata_file = output_file.parent / f".{output_file.stem}_progress.json"
    segments_dir.mkdir(parents=True, exist_ok=True)

    headers: dict[str, str] = {
        "User-Agent": settings.user_agent,
        "Referer": "https://vkvideo.ru/",
    }
    if request.cookies:
        headers["Cookie"] = request.cookies

    try:
        return await _run_download_session(
            request.m3u8_url,
            headers,
            settings,
            segments_dir,
            metadata_file,
            output_file,
            request.progress_callback,
            request.video_url,
            request.extractor,
            request.backoff_coordinator,
            semaphore,
        )
    except Exception:
        _log_preserve_segments(segments_dir)
        raise


def _log_preserve_segments(segments_dir: Path) -> None:
    """Log preserved segments for resume on exception.

    Args:
        segments_dir: Directory containing downloaded segments.
    """
    if segments_dir.exists():
        segment_count = len(list(segments_dir.glob("*.ts")))
        if segment_count > 0:
            logger.info("preserving_segments_for_resume", count=segment_count)
