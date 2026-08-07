"""HLS segment downloader with segment-level resume support."""

from __future__ import annotations

import asyncio
import hashlib
import random
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import aiohttp
from structlog import get_logger

from ..config import Settings
from ..models.enums import CookieSource
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params
from .concurrency import SemaphoreLike
from .downloader_throttle import (
    RETRYABLE_STATUS_CODES,
    _compute_backoff_delay,
    _parse_retry_after,
    _retry_429_with_backoff,
    _wait_with_shutdown,
    get_shutdown_event,
)
from .ffmpeg_utils import _merge_segments_batched

if TYPE_CHECKING:
    from ..models.dtos import HLSDownloadRequest
    from ..services.extractor import VKVideoExtractor
    from .downloader_throttle import URLBackoffCoordinator


@dataclass
class SegmentTask:
    """Identity and location for a single segment download task.

    Contains the segment's position, URL, and where to save it.
    """

    idx: int
    segment_url: str
    segments_dir: Path


@dataclass
class DownloadPolicy:
    """Download policy configuration for segment downloads.

    Bundles HTTP session, rate-limiting, and retry settings.
    """

    session: aiohttp.ClientSession
    semaphore: SemaphoreLike | asyncio.Semaphore
    headers: dict[str, str]
    max_concurrent_downloads: int
    backoff_coordinator: URLBackoffCoordinator | None
    video_url: str
    max_retries: int
    download_timeout: int = 300
    is_shared_semaphore: bool = False
    m3u8_url: str = ""
    segments_dir: Path = Path()


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


_PLAYLIST_SIGNATURE_FILE = ".signature"


def _compute_playlist_signature(segments: list[str]) -> str:
    """Compute a SHA-256 signature of the segment URL list.

    Used to detect playlist changes between download sessions so stale
    segments from a previous playlist are not silently reused.

    Args:
        segments: List of segment URLs from the current playlist.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    joined = "\n".join(segments)
    return hashlib.sha256(joined.encode()).hexdigest()


def _clear_stale_segments(segments_dir: Path, segments: list[str]) -> None:
    """Remove stale segment files that belong to a previous playlist.

    If the playlist signature does not match the one on disk, all ``*.ts``
    files in ``segments_dir`` are stale and must be removed before
    downloading the current playlist's segments.

    Args:
        segments_dir: Directory containing downloaded segments.
        segments: List of segment URLs from the current playlist.
    """
    if not segments_dir.exists():
        return

    signature = _compute_playlist_signature(segments)
    signature_file = segments_dir / _PLAYLIST_SIGNATURE_FILE

    if signature_file.exists():
        stored = signature_file.read_text(encoding="utf-8").strip()
        if stored == signature:
            return

    stale_count = len(list(segments_dir.glob("*.ts")))
    if stale_count:
        logger.info("clearing_stale_segments", count=stale_count)
    for stale_file in segments_dir.glob("*.ts"):
        stale_file.unlink(missing_ok=True)

    signature_file.write_text(signature, encoding="utf-8")


async def _download_segment_sequential(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    segment_index: int = 0,
    max_retries: int = 3,
    download_timeout: int = 300,
) -> bool:
    """Download a single HLS segment with sequential retry logic.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        output_path: Path to save the downloaded segment.
        headers: Request headers to use.
        segment_index: Index of the segment being downloaded (for logging).
        max_retries: Maximum retry attempts for 429/5xx responses.
        download_timeout: Total timeout for HTTP request in seconds.

    Returns:
        True on success, False on failure.
    """
    content = await _retry_429_with_backoff(
        session,
        segment_url,
        headers,
        segment_index,
        max_retries=max_retries,
        download_timeout=download_timeout,
    )
    if content is not None and len(content) > 0:
        with open(output_path, "wb") as f:
            f.write(content)
        return True
    return False


def _is_retryable_status(status_code: int) -> bool:
    """Check if HTTP status code is retryable (429, 500, 502, 503, 504)."""
    return status_code in RETRYABLE_STATUS_CODES


async def _notify_backoff_for_retryable_status(
    status_code: int,
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
) -> None:
    """Notify backoff coordinator for retryable HTTP status codes."""
    if backoff_coordinator and video_url and _is_retryable_status(status_code):
        await backoff_coordinator.pause(video_url, 10.0)


def _should_continue_on_retry(
    status_code: int,
    attempt: int,
    max_retries: int,
) -> bool:
    """Check if we should continue retrying for given status code."""
    return _is_retryable_status(status_code) and attempt < max_retries - 1


async def _run_parallel_download_with_backoff(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
    attempt: int,
    max_retries: int,
    download_timeout: int = 300,
) -> bool | None:
    """Run a single download attempt in parallel mode.

    Returns True on success, None for retryable status codes, False for fatal errors.
    """
    connect_timeout = min(30, download_timeout // 4)
    client_timeout = aiohttp.ClientTimeout(
        total=download_timeout,
        connect=connect_timeout,
        sock_connect=30,
        sock_read=60,
    )
    async with session.get(segment_url, headers=headers, timeout=client_timeout) as response:
        if response.status == 200:
            content = await response.read()
            if len(content) == 0:
                logger.warning("empty_segment_content", segment_url=_strip_auth_params(segment_url))
                return None
            with open(output_path, "wb") as f:
                f.write(content)
            return True

        logger.warning("segment_download_failed", status=response.status)
        await _notify_backoff_for_retryable_status(response.status, backoff_coordinator, video_url)

        if _should_continue_on_retry(response.status, attempt, max_retries):
            retry_after_seconds = _parse_retry_after(response)
            delay = _compute_backoff_delay(response.status, attempt, retry_after_seconds)
            shutdown_event = get_shutdown_event()
            await _wait_with_shutdown(delay, shutdown_event, attempt, video_url or "unknown")
            return None

        return False


async def _check_backoff_before_attempt(
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
    shutdown_event: asyncio.Event,
) -> bool:
    """Check backoff state before download attempt. Returns True if should abort."""
    if backoff_coordinator and video_url:
        was_paused = await backoff_coordinator.wait_if_paused(video_url)
        if was_paused and shutdown_event.is_set():
            return True
    return False


async def _try_single_download_attempt(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
    attempt: int,
    max_retries: int,
    download_timeout: int = 300,
) -> bool | None:
    """Try a single download attempt, return True on success. Handles exceptions.

    Returns True on success, None for retryable failures (including network
    errors), False for fatal HTTP status codes (non-retryable).
    """
    try:
        return await _run_parallel_download_with_backoff(
            session,
            segment_url,
            output_path,
            headers,
            backoff_coordinator,
            video_url,
            attempt,
            max_retries,
            download_timeout=download_timeout,
        )
    except aiohttp.ClientError as e:
        logger.error("segment_download_error", error=str(e))
        return None


async def _download_segment_parallel(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    max_retries: int = 3,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_url: str | None = None,
    download_timeout: int = 300,
) -> bool:
    """Download a single HLS segment with parallel retry logic and shared backoff.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        output_path: Path to save the downloaded segment.
        headers: Request headers to use.
        max_retries: Maximum retry attempts for 429/5xx responses.
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_url: Original video URL for coordinator keying (required if coordinator provided).
        download_timeout: Total timeout for HTTP request in seconds.

    Returns:
        True on success, False on failure.
    """
    shutdown_event = get_shutdown_event()

    for attempt in range(max_retries):
        if shutdown_event.is_set():
            return False
        if await _check_backoff_before_attempt(backoff_coordinator, video_url, shutdown_event):
            return False

        result = await _try_single_download_attempt(
            session,
            segment_url,
            output_path,
            headers,
            backoff_coordinator,
            video_url,
            attempt,
            max_retries,
            download_timeout=download_timeout,
        )
        if result is True:
            return True
        if result is False:
            # Fatal error (non-retryable HTTP status) — fail fast, no retry
            return False
        # result is None: retryable, continue loop

    return False


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
    download_timeout: int = 300,
) -> bool:
    """Download a single HLS segment.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        output_path: Path to save the downloaded segment.
        headers: Request headers to use.
        max_concurrent_downloads: Maximum concurrent downloads. When 1, uses sequential retry.
        segment_index: Index of the segment being downloaded (for logging).
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_url: Original video URL for coordinator keying (required if coordinator provided).
        max_retries: Maximum retry attempts for parallel mode on 429/5xx responses.
        download_timeout: Total timeout for HTTP request in seconds.

    Returns:
        True on success, False on failure.
    """
    if max_concurrent_downloads == 1:
        return await _download_segment_sequential(
            session,
            segment_url,
            output_path,
            headers,
            segment_index=segment_index,
            max_retries=max_retries,
            download_timeout=download_timeout,
        )

    return await _download_segment_parallel(
        session,
        segment_url,
        output_path,
        headers,
        max_retries=max_retries,
        backoff_coordinator=backoff_coordinator,
        video_url=video_url,
        download_timeout=download_timeout,
    )


def _cleanup_segments(segments_dir: Path) -> None:
    """Clean up downloaded segments.

    Args:
        segments_dir: Directory containing downloaded segments.
    """
    for f in segments_dir.glob("*"):
        f.unlink()
    try:
        segments_dir.rmdir()
    except OSError:
        pass


async def _refresh_token_and_retry(
    video_url: str,
    extractor: VKVideoExtractor,
    settings: Settings,
) -> tuple[str, str] | None:
    """Refresh token via browser extraction on 403/410 error.

    Returns tuple of (new_url, cookies) on success, None if refresh failed.
    """
    if settings.cookie_source != CookieSource.BROWSER:
        logger.warning(
            "token_refresh_failed_cookie_source",
            cookie_source=str(settings.cookie_source),
            reason="Cannot refresh token without browser access",
        )
        return None

    streams, new_cookies, _raw_cookies = await extractor.extract_streams_with_cookies(
        video_url, force_browser=True
    )
    if not streams:
        return None

    return str(streams[0].url), new_cookies or ""


async def _fetch_single_playlist(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str],
    timeout: aiohttp.ClientTimeout,
) -> tuple[str, int] | None:
    """Fetch a single playlist, returning (playlist_text, status_code) or None on error."""
    try:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status == 200:
                return await response.text(), response.status
            return "", response.status
    except aiohttp.ClientError as e:
        logger.warning("playlist_fetch_failed", error=str(e))
        return None


async def _handle_token_refresh(
    video_url: str,
    extractor: VKVideoExtractor,
    settings: Settings,
    headers: dict[str, str],
) -> str | None:
    """Handle token refresh and update headers.

    Returns new URL on success, None on failure.
    """
    refresh_result = await _refresh_token_and_retry(video_url, extractor, settings)
    if refresh_result:
        current_url, new_cookies = refresh_result
        headers["Cookie"] = new_cookies
        return current_url
    return None


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
    client_timeout = aiohttp.ClientTimeout(
        total=settings.download_timeout,
        connect=min(30, settings.download_timeout // 4),
        sock_connect=30,
        sock_read=60,
    )

    for _ in range(max_retries):
        result = await _fetch_single_playlist(session, current_url, headers, client_timeout)
        if result is None:
            continue

        playlist_text, status = result
        if status == 200:
            return playlist_text

        # Check if we should attempt token refresh
        if status not in (403, 410) or not extractor:
            return None

        logger.info("token_expired_fetching_new")
        new_url = await _handle_token_refresh(video_url, extractor, settings, headers)
        if new_url is not None:
            current_url = new_url
            continue

        return None

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


async def _await_and_cancel(
    tasks: list[asyncio.Task[tuple[int, bool]]],
) -> list[tuple[int, bool]] | None:
    """Await segment download tasks with cancellation handling.

    Args:
        tasks: List of download tasks to await. Each task returns (segment_index, success).

    Returns:
        List of (segment_index, success) tuples on success, None if cancelled.
    """
    if not tasks:
        return None

    try:
        return await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        # Cancel any still-running tasks on interruption
        for task in tasks:
            if not task.done():
                task.cancel()
        # Wait for cancellation to propagate
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("download_cancelled", reason="shutdown_requested")
        return None


async def _tally_and_merge(
    download_results: list[tuple[int, bool]],
    segments: list[str],
    segments_dir: Path,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
    video_url: str,
    download_timeout: int,
) -> Path | None:
    """Tally download results and merge if all segments downloaded.

    Uses ``download_results`` to detect per-segment failures explicitly,
    falling back to filesystem count for progress reporting.

    Args:
        download_results: List of (segment_index, success) tuples from completed tasks.
        segments: List of all segment URLs.
        segments_dir: Directory containing downloaded segments.
        output_file: Final output file path.
        progress_callback: Optional callback for progress updates.
        video_url: Video URL for progress callback video_id extraction.
        download_timeout: Maximum seconds for ffmpeg subprocess merge operations.

    Returns:
        Path to merged file on success, None otherwise.
    """
    downloaded_count = len(list(segments_dir.glob("*.ts")))

    if progress_callback:
        video_id = video_url.split("_")[-1] if "_" in video_url else video_url
        progress_callback(video_id, downloaded_count, len(segments))

    # Detect failed segments explicitly from download results
    if download_results and not all(r for _, r in download_results):
        failed_indices = [idx for idx, r in download_results if not r]
        logger.warning("segment_download_failed", failed_indices=failed_indices)
        return None

    # All segments present on disk — merge
    if downloaded_count == len(segments):
        logger.info("merging_segments", count=len(segments))
        result = await _merge_segments_batched(
            segments_dir, output_file, len(segments), float(download_timeout)
        )
        if result:
            _cleanup_segments(segments_dir)
        return result

    return None


async def _process_downloaded_segments(
    tasks: list[asyncio.Task[tuple[int, bool]]],
    segments: list[str],
    segments_dir: Path,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
    video_url: str,
    download_timeout: int,
) -> Path | None:
    """Process downloaded segments and merge if complete.

    Args:
        tasks: List of download tasks to await. Each returns (segment_index, success).
        segments: List of all segment URLs.
        segments_dir: Directory containing downloaded segments.
        output_file: Final output file path.
        progress_callback: Optional callback for progress updates.
        video_url: Video URL for progress callback video_id extraction.
        download_timeout: Maximum seconds for ffmpeg subprocess merge operations.

    Returns:
        Path to merged file on success, None otherwise.
    """
    download_results = await _await_and_cancel(tasks)
    if download_results is None:
        return None
    return await _tally_and_merge(
        download_results,
        segments,
        segments_dir,
        output_file,
        progress_callback,
        video_url,
        download_timeout,
    )


async def _download_segment_concurrent(
    task: SegmentTask,
    policy: DownloadPolicy,
) -> tuple[int, bool]:
    """Download a segment with semaphore rate limiting.

    Args:
        task: SegmentTask containing segment identity and location.
        policy: DownloadPolicy containing HTTP session, rate-limiting, and retry settings.

    Returns:
        Tuple of (segment_index, success) where success is True on download success.
    """
    shutdown_event = get_shutdown_event()

    if shutdown_event.is_set():
        raise asyncio.CancelledError("Download cancelled by user")

    async with policy.semaphore:
        if shutdown_event.is_set():
            raise asyncio.CancelledError("Download cancelled by user")

        full_url = (
            urljoin(policy.m3u8_url, task.segment_url)
            if not task.segment_url.startswith("http")
            else task.segment_url
        )

        segment_path = task.segments_dir / f"{task.idx:05d}.ts"
        result = await _download_segment(
            policy.session,
            full_url,
            segment_path,
            policy.headers,
            max_concurrent_downloads=policy.max_concurrent_downloads,
            segment_index=task.idx,
            backoff_coordinator=policy.backoff_coordinator,
            video_url=policy.video_url,
            max_retries=policy.max_retries,
            download_timeout=policy.download_timeout,
        )

        if result and not policy.is_shared_semaphore and policy.max_concurrent_downloads == 1:
            if shutdown_event.is_set():
                raise asyncio.CancelledError("Download cancelled by user")

            delay = 1.5 + random.uniform(0, 0.5)
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
                raise asyncio.CancelledError("Download cancelled by user")
            except TimeoutError:
                pass

        return task.idx, result


def _create_segment_download_tasks(
    segments: list[str],
    policy: DownloadPolicy,
) -> list[asyncio.Task[tuple[int, bool]]]:
    """Create tasks for downloading missing segments.

    Skips segments whose .ts file already exists with non-zero size.

    Args:
        segments: List of segment URLs to download.
        policy: DownloadPolicy containing HTTP session, rate-limiting, and retry settings.

    Returns:
        List of download tasks for missing segments only.
    """
    tasks = []
    for i, seg in enumerate(segments):
        segment_path = policy.segments_dir / f"{i:05d}.ts"
        if segment_path.exists() and segment_path.stat().st_size > 0:
            logger.debug("skipping_existing_segment", idx=i)
            continue
        tasks.append(
            asyncio.create_task(
                _download_segment_concurrent(
                    SegmentTask(
                        idx=i,
                        segment_url=seg,
                        segments_dir=policy.segments_dir,
                    ),
                    policy,
                )
            )
        )
    return tasks


async def _run_download_session(
    m3u8_url: str,
    headers: dict[str, str],
    settings: Settings,
    segments_dir: Path,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
    video_url: str,
    extractor: VKVideoExtractor | None,
    backoff_coordinator: URLBackoffCoordinator | None,
    semaphore: SemaphoreLike | None,
) -> Path | None:
    """Run the download session with aiohttp client.

    Args:
        m3u8_url: HLS playlist URL.
        headers: Request headers to use.
        settings: Application settings.
        segments_dir: Directory for downloaded segments.
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
            session,
            video_url,
            m3u8_url,
            headers,
            extractor,
            settings,
            max_retries=settings.max_retries,
        )
        if not playlist_content:
            return None

        segments = _parse_m3u8_segments(playlist_content)
        logger.info("found_segments", count=len(segments))

        _clear_stale_segments(segments_dir, segments)

        semaphore_to_use = (
            semaphore
            if semaphore is not None
            else asyncio.Semaphore(settings.max_concurrent_downloads)
        )
        is_shared = semaphore is not None

        policy = DownloadPolicy(
            session=session,
            semaphore=semaphore_to_use,
            headers=headers,
            max_concurrent_downloads=settings.max_concurrent_downloads,
            backoff_coordinator=backoff_coordinator,
            video_url=video_url,
            max_retries=settings.max_retries,
            download_timeout=settings.download_timeout,
            is_shared_semaphore=is_shared,
            m3u8_url=m3u8_url,
            segments_dir=segments_dir,
        )

        tasks = _create_segment_download_tasks(segments, policy)

        return await _process_downloaded_segments(
            tasks,
            segments,
            segments_dir,
            output_file,
            progress_callback,
            video_url,
            settings.download_timeout,
        )


async def download_hls_with_resume(
    request: HLSDownloadRequest,
    settings: Settings | None = None,
    extractor: VKVideoExtractor | None = None,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    semaphore: SemaphoreLike | None = None,
) -> Path | None:
    """
    Download HLS stream with segment-level resume and token refresh.

    Downloads original HLS segments individually, tracks progress, and can resume
    after interruption by re-downloading missing segments. Uses batched merging
    to handle large number of segments.

    Args:
        request: HLSDownloadRequest containing download parameters.
        settings: Application settings. Uses default if not provided.
        extractor: Optional VKVideoExtractor for token refresh.
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
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

    if settings is None:
        settings = Settings()
    output_file = validate_output_path(request.output_file)

    segments_dir = output_file.parent / f".{output_file.stem}_segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    headers: dict[str, str] = {
        "User-Agent": settings.user_agent,
        "Referer": "https://vkvideo.ru/",
    }
    if request.cookies:
        headers["Cookie"] = request.cookies

    success = False
    try:
        result = await _run_download_session(
            request.m3u8_url,
            headers,
            settings,
            segments_dir,
            output_file,
            request.progress_callback,
            request.video_url,
            extractor,
            backoff_coordinator,
            semaphore,
        )
        if result is not None:
            success = True
            return result
        return None
    except Exception:
        raise
    finally:
        if not success:
            _log_preserve_segments(segments_dir)


def _log_preserve_segments(segments_dir: Path) -> None:
    """Log preserved segments for resume on exception.

    Args:
        segments_dir: Directory containing downloaded segments.
    """
    if segments_dir.exists():
        segment_count = len(list(segments_dir.glob("*.ts")))
        if segment_count > 0:
            logger.info("preserving_segments_for_resume", count=segment_count)
