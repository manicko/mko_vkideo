"""HLS segment downloader with segment-level resume support."""

from __future__ import annotations

import asyncio
import json
import random
import ssl
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

    if request.settings is None:
        settings = Settings()
    else:
        settings = request.settings

    # Validate output path to prevent path traversal
    output_file = validate_output_path(request.output_file)

    segments_dir = output_file.parent / f".{output_file.stem}_segments"
    metadata_file = output_file.parent / f".{output_file.stem}_progress.json"

    segments_dir.mkdir(parents=True, exist_ok=True)
    shutdown_event = get_shutdown_event()

    try:
        downloaded_count = _load_downloaded_count(metadata_file)
        headers: dict[str, str] = {
            "User-Agent": settings.user_agent,
            "Referer": "https://vkvideo.ru/",
        }
        if request.cookies:
            headers["Cookie"] = request.cookies

        if settings.ssl_verify:
            connector = aiohttp.TCPConnector(limit=10)
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context, limit=10)
            logger.warning("ssl_verification_disabled", url=_strip_auth_params(request.video_url))

        async with aiohttp.ClientSession(connector=connector) as session:
            playlist_content = await _fetch_playlist_with_retry(
                session, request.video_url, request.m3u8_url, headers, request.extractor, settings,
                max_retries=settings.max_retries
            )
            if not playlist_content:
                return None

            segments = _parse_m3u8_segments(playlist_content)
            logger.info("found_segments", count=len(segments), resume_from=downloaded_count)

            # Download missing segments concurrently
            # Use shared semaphore if provided, otherwise create local one based on settings
            semaphore_to_use = (
                semaphore
                if semaphore is not None
                else asyncio.Semaphore(settings.max_concurrent_downloads)
            )

            async def download_segment_concurrent(idx: int, segment_url: str) -> bool:
                """Download segment with semaphore rate limiting."""
                # Check for shutdown before starting - raise CancelledError to interrupt gather
                if shutdown_event.is_set():
                    raise asyncio.CancelledError("Download cancelled by user")
                async with semaphore_to_use:
                    # Check for shutdown after acquiring semaphore
                    if shutdown_event.is_set():
                        raise asyncio.CancelledError("Download cancelled by user")
                    full_url = segment_url
                    if not segment_url.startswith("http"):
                        full_url = urljoin(request.m3u8_url, segment_url)
                    segment_path = segments_dir / f"{idx:05d}.ts"
                    if not segment_path.exists() or segment_path.stat().st_size == 0:
                        result = await _download_segment(
                            session,
                            full_url,
                            segment_path,
                            headers,
                            max_concurrent_downloads=settings.max_concurrent_downloads,
                            segment_index=idx,
                            backoff_coordinator=request.backoff_coordinator,
                            video_url=request.video_url,
                            max_retries=settings.max_retries,
                        )
                    else:
                        result = True
                    # Anti-detection delay AFTER semaphore release (outside context block)
                    # Delay only applies in sequential mode (max_concurrent_downloads == 1)
                    # Skip when shared semaphore is provided (work-stealing context)
                    if result and semaphore is None and settings.max_concurrent_downloads == 1:
                        # Check for shutdown in delay loop - raise to interrupt gather
                        if shutdown_event.is_set():
                            raise asyncio.CancelledError("Download cancelled by user")
                        delay = 1.5 + random.uniform(0, 0.5)
                        try:
                            # Allow interruption during delay
                            await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
                            raise asyncio.CancelledError("Download cancelled by user")
                        except TimeoutError:
                            pass  # Normal completion
                    return result

            # Download all missing segments concurrently
            tasks = [
                asyncio.create_task(download_segment_concurrent(i, seg))
                for i, seg in enumerate(segments)
                if not (segments_dir / f"{i:05d}.ts").exists()
                or (segments_dir / f"{i:05d}.ts").stat().st_size == 0
            ]

            if tasks:
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
                if request.progress_callback:
                    video_id = (
                        request.video_url.split("_")[-1]
                        if "_" in request.video_url
                        else request.video_url
                    )
                    request.progress_callback(video_id, downloaded_count, len(segments))

            # All downloaded - merge in batches
            if downloaded_count == len(segments):
                logger.info("merging_segments", count=len(segments))
                result = await _merge_segments_batched(segments_dir, output_file, len(segments))
                if result:
                    _cleanup_segments(segments_dir, metadata_file)
                return result

            return None
    except Exception:
        # On any exception, preserve segments for resume (don't cleanup)
        if segments_dir.exists():
            segment_count = len(list(segments_dir.glob("*.ts")))
            if segment_count > 0:
                logger.info("preserving_segments_for_resume", count=segment_count)
        raise
