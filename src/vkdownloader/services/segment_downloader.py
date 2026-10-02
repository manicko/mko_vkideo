"""HLS segment downloader with segment-level resume support."""

from __future__ import annotations

import asyncio
import hashlib
import os
import random
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.parse import urljoin

import aiohttp
from structlog import get_logger

from ..config import Settings
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params
from .concurrency import SemaphoreLike
from .downloader_throttle import (
    _TRANSPORT_FAILURE_STATUS,
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
    total_segments: int = 1


@dataclass
class PlaylistFetchResult:
    """Result of a successful playlist fetch.

    Attributes:
        playlist_text: The raw m3u8 playlist content.
        base_url: The actual base URL the playlist was served from, which may
            differ from the requested URL after a token-refresh redirect.
    """

    playlist_text: str
    base_url: str


@dataclass
class DownloadPolicy:
    """Download policy configuration for segment downloads.

    Bundles HTTP session, rate-limiting, and retry settings.
    """

    session: aiohttp.ClientSession
    semaphore: asyncio.Semaphore
    headers: dict[str, str]
    max_concurrent_downloads: int
    backoff_coordinator: URLBackoffCoordinator | None
    video_url: str
    max_retries: int
    download_timeout: int = 300
    is_bounded_batch: bool = False
    m3u8_url: str = ""
    segments_dir: Path = Path()
    # DF-003: Added to enable per-segment progress reporting from
    # _download_segment_concurrent instead of only at merge time.
    progress_callback: Callable[[str, int, int], None] | None = None


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
    *,
    backoff_coordinator: URLBackoffCoordinator | None = None,
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
        backoff_coordinator: Optional shared URLBackoffCoordinator for pausing
            retryable transport failures on the origin before each attempt.

    Returns:
        True on success, False on failure.
    """
    shutdown_event = get_shutdown_event()

    if shutdown_event.is_set():
        return False
    if backoff_coordinator is not None:
        await backoff_coordinator.wait_if_paused(segment_url)

    content = await _retry_429_with_backoff(
        session,
        segment_url,
        headers,
        segment_index,
        max_retries=max_retries,
        download_timeout=download_timeout,
    )
    if content is not None and len(content) > 0:
        # DF-010: Write to temp file then os.replace for atomicity
        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        try:
            with open(temp_path, "wb") as f:
                f.write(content)
            os.replace(temp_path, output_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        return True
    return False


def _is_retryable_status(status_code: int) -> bool:
    """Check if status code is retryable (408, 425, 429, or 5xx transport failure)."""
    return status_code in RETRYABLE_STATUS_CODES


async def _notify_backoff_for_retryable_status(
    status_code: int,
    backoff_coordinator: URLBackoffCoordinator | None,
    resource_url: str | None,
) -> None:
    """Notify backoff coordinator for retryable HTTP status codes.

    The coordinator normalizes *resource_url* internally via ``_resource_key``,
    so callers may pass the raw URL.
    """
    if backoff_coordinator and resource_url and _is_retryable_status(status_code):
        await backoff_coordinator.pause(resource_url, backoff_coordinator.pause_seconds)


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
            # DF-010: Write to temp file then os.replace for atomicity
            temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
            try:
                with open(temp_path, "wb") as f:
                    f.write(content)
                os.replace(temp_path, output_path)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
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
    resource_url: str | None,
    shutdown_event: asyncio.Event,
) -> bool:
    """Check backoff state before download attempt. Returns True if should abort."""
    if backoff_coordinator and resource_url:
        was_paused = await backoff_coordinator.wait_if_paused(resource_url)
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
            backoff_coordinator=backoff_coordinator,
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
    # DF-006: Removed the `cookie_source != BROWSER` guard. The
    # `force_browser=True` parameter already bypasses the CookieSource
    # check inside extract_streams_with_cookies, matching the pattern in
    # _attempt_segment_resume (downloader.py). Token refresh was
    # impossible with the default CookieSource.NONE configuration.
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
    except (aiohttp.ClientError, TimeoutError) as e:
        logger.warning("playlist_fetch_failed", error=str(e))
        return None


async def _handle_token_refresh(
    video_url: str,
    extractor: VKVideoExtractor,
    settings: Settings,
    headers: dict[str, str],
) -> tuple[str, str] | None:
    """Handle token refresh on 403/410 error.

    Returns (new_url, new_cookies) tuple on success, None on failure.
    Does not mutate the caller's headers dict; the caller is responsible
    for applying new_cookies.
    """
    return await _refresh_token_and_retry(video_url, extractor, settings)


async def _fetch_playlist_with_retry(
    session: aiohttp.ClientSession,
    video_url: str,
    m3u8_url: str,
    headers: dict[str, str],
    extractor: VKVideoExtractor | None,
    settings: Settings,
    max_retries: int = 3,
    *,
    backoff_coordinator: URLBackoffCoordinator | None = None,
) -> PlaylistFetchResult | None:
    """Fetch m3u8 playlist with token refresh on 403/410 and retry on transport failures.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        video_url: Original video URL for token refresh.
        m3u8_url: Initial playlist URL to fetch.
        headers: Request headers (mutated on token refresh).
        extractor: Optional VKVideoExtractor for token refresh.
        settings: Application settings.
        max_retries: Maximum retry attempts.
        backoff_coordinator: Optional shared backoff coordinator for pausing
            retryable transport failures on the origin.

    Returns:
        PlaylistFetchResult with playlist text and base URL on success,
        None on failure.
    """
    current_url = m3u8_url
    client_timeout = aiohttp.ClientTimeout(
        total=settings.download_timeout,
        connect=min(30, settings.download_timeout // 4),
        sock_connect=30,
        sock_read=60,
    )
    shutdown_event = get_shutdown_event()

    for attempt in range(max_retries):
        if shutdown_event.is_set():
            return None

        if backoff_coordinator is not None:
            await backoff_coordinator.wait_if_paused(current_url)

        result = await _fetch_single_playlist(session, current_url, headers, client_timeout)

        if result is None:
            logger.warning(
                "playlist_retry_transport_error",
                url=_strip_auth_params(current_url),
                attempt=attempt + 1,
                max_retries=max_retries,
            )
            if attempt == max_retries - 1:
                return None
            if backoff_coordinator is not None:
                await backoff_coordinator.pause(current_url, backoff_coordinator.pause_seconds)
            # D1: compute the exponential-backoff delay and honour shutdown
            # before looping. Manifest retry has no Retry-After, so pass None.
            delay = _compute_backoff_delay(_TRANSPORT_FAILURE_STATUS, attempt, None)
            shutdown_triggered = await _wait_with_shutdown(
                delay, shutdown_event, attempt, _strip_auth_params(current_url)
            )
            if shutdown_triggered:
                return None
            continue

        playlist_text, status = result

        if status == 200:
            return PlaylistFetchResult(playlist_text=playlist_text, base_url=current_url)

        if _is_retryable_status(status):
            logger.warning(
                "playlist_retry_status",
                url=_strip_auth_params(current_url),
                status=status,
                attempt=attempt + 1,
                max_retries=max_retries,
            )
            if attempt == max_retries - 1:
                return None
            if backoff_coordinator is not None:
                await backoff_coordinator.pause(current_url, backoff_coordinator.pause_seconds)
            # D1: compute the exponential-backoff delay and honour shutdown
            # before looping. Manifest retry has no Retry-After, so pass None.
            delay = _compute_backoff_delay(status, attempt, None)
            shutdown_triggered = await _wait_with_shutdown(
                delay, shutdown_event, attempt, _strip_auth_params(current_url)
            )
            if shutdown_triggered:
                return None
            continue

        if status in (403, 410) and extractor is not None:
            logger.info(
                "token_expired_fetching_new",
                url=_strip_auth_params(current_url),
                status=status,
                attempt=attempt + 1,
            )
            refresh_result = await _handle_token_refresh(video_url, extractor, settings, headers)
            if refresh_result is not None:
                current_url, new_cookies = refresh_result
                headers["Cookie"] = new_cookies
                continue
            logger.warning(
                "playlist_fetch_failed_non_retryable",
                url=_strip_auth_params(current_url),
                status=status,
                reason="token_refresh_failed",
            )
            return None

        logger.warning(
            "playlist_fetch_failed_non_retryable",
            url=_strip_auth_params(current_url),
            status=status,
            reason="non_retryable",
        )
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


_REASON_SHUTDOWN: Final = "shutdown_requested"
_REASON_CANCELLED: Final = "cancelled"


class _SegmentFanoutOutcome(StrEnum):
    """Why the segment fan-out produced its result (CON-006, CON-008, phase04/VAL-402).

    COMPLETED: the factory produced at least one task and every task settled.
    NOTHING_TO_DO: no segment was missing, so the merge must still be attempted
    from what is already on disk. Cancellation is not a member — it is raised.
    """

    COMPLETED = "completed"
    NOTHING_TO_DO = "nothing_to_do"


@dataclass(frozen=True)
class _SegmentFanoutResult:
    """``_await_and_cancel``' return value: the outcome plus the results it produced.

    ``results`` is a list, not a tuple, so it reaches ``_tally_and_merge``
    unchanged. It is empty exactly when the outcome is NOTHING_TO_DO; the
    outcome is still carried explicitly, because a consumer must not be left
    inferring the distinction from a falsy length.
    """

    outcome: _SegmentFanoutOutcome
    results: list[tuple[int, bool]]


async def _await_and_cancel(
    tasks: list[asyncio.Task[tuple[int, bool]]],
) -> _SegmentFanoutResult:
    """Await segment download tasks, settling every sibling before returning or raising.

    Args:
        tasks: Download tasks to await. Each returns (segment_index, success).

    Returns:
        ``_SegmentFanoutResult`` with outcome COMPLETED and one (index, success) tuple per
        task, or outcome NOTHING_TO_DO with an empty results list when no
        segment was missing.

    Raises:
        asyncio.CancelledError if the enclosing task is cancelled, after every
        sibling is settled. Any other exception from a task is re-raised,
        also after every sibling is settled.
    """
    # CON-006: "nothing to do" is an outcome, not None -- the consumer must reach
    # the merge in the resume case instead of being told the download failed.
    if not tasks:
        return _SegmentFanoutResult(_SegmentFanoutOutcome.NOTHING_TO_DO, [])

    try:
        results = await asyncio.gather(*tasks)
    except BaseException as exc:
        # CON-007: a raising part must not orphan its siblings. CON-008: a
        # cancellation is re-raised, never turned into a return value.
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if isinstance(exc, asyncio.CancelledError):
            logger.info(
                "download_cancelled",
                reason=_REASON_SHUTDOWN if get_shutdown_event().is_set() else _REASON_CANCELLED,
            )
        raise

    return _SegmentFanoutResult(_SegmentFanoutOutcome.COMPLETED, results)


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

    # Detect failed segments explicitly from download results.
    # download_results is empty on the resume path (CON-006): no segment failed
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
    fanout = await _await_and_cancel(tasks)
    # CON-006: NOTHING_TO_DO (all segments already on disk) is not a failure --
    # fall through to _tally_and_merge, which checks the on-disk count and
    # merges if complete, rather than short-circuiting as a "download failed".
    return await _tally_and_merge(
        fanout.results,
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

        # DF-003: Report per-segment progress so users see incremental
        # progress during segment downloads, not just once at merge time.
        if policy.progress_callback is not None:
            video_id = (
                policy.video_url.split("_")[-1] if "_" in policy.video_url else policy.video_url
            )
            # Count segments downloaded so far (including existing) + result
            downloaded = len(list(task.segments_dir.glob("*.ts")))
            policy.progress_callback(video_id, downloaded, task.total_segments)

        if result and not policy.is_bounded_batch and policy.max_concurrent_downloads == 1:
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
                        total_segments=len(segments),
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
    video_semaphore: SemaphoreLike | None,
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
        video_semaphore: The batch video permit the caller already holds. This is
            used only to detect batch context (for the ``is_bounded_batch`` flag);
            the segment fan-out is bounded by a semaphore this layer owns.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    connector = _create_connector(settings, video_url)

    async with aiohttp.ClientSession(connector=connector) as session:
        playlist_result = await _fetch_playlist_with_retry(
            session,
            video_url,
            m3u8_url,
            headers,
            extractor,
            settings,
            max_retries=settings.max_retries,
            backoff_coordinator=backoff_coordinator,
        )
        if playlist_result is None or not playlist_result.playlist_text:
            return None

        segments = _parse_m3u8_segments(playlist_result.playlist_text)
        logger.info("found_segments", count=len(segments))

        _clear_stale_segments(segments_dir, segments)

        # D-01: The batch semaphore gates *videos* (one permit per video, acquired
        # once in perform_download). asyncio.Semaphore is not reentrant: reusing the
        # caller's batch permit here for per-segment acquisition would deadlock once
        # all video permits are held, because every inner acquisition would wait on a
        # permit the same task already holds. The segment fan-out is therefore
        # bounded by a semaphore this layer owns, sized by the same
        # max_concurrent_downloads setting.
        semaphore_to_use: asyncio.Semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        is_bounded_batch = video_semaphore is not None

        policy = DownloadPolicy(
            session=session,
            semaphore=semaphore_to_use,
            headers=headers,
            max_concurrent_downloads=settings.max_concurrent_downloads,
            backoff_coordinator=backoff_coordinator,
            video_url=video_url,
            max_retries=settings.max_retries,
            download_timeout=settings.download_timeout,
            is_bounded_batch=is_bounded_batch,
            m3u8_url=playlist_result.base_url,
            segments_dir=segments_dir,
            progress_callback=progress_callback,  # DF-003: enable per-segment progress
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
    video_semaphore: SemaphoreLike | None = None,
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
        video_semaphore: The batch video permit the caller already holds (one
            permit per video, acquired once in ``perform_download``). This is the
            batch-level semaphore, **not** the segment-level one: the segment
            fan-out is deliberately NOT gated by it, and is bounded instead by a
            semaphore this layer owns. Passing the batch permit here would
            deadlock (see D-01): ``asyncio.Semaphore`` is not reentrant, so a
            second acquisition from the same object per segment could never be
            satisfied once all video permits are held. When ``None`` (single-download
            mode), the segment layer still creates its own local semaphore sized
            by ``settings.max_concurrent_downloads``.

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
            video_semaphore,
        )
        if result is not None:
            success = True
            return result
        return None
    finally:
        if not success:
            _log_preserve_segments(segments_dir)


def _log_preserve_segments(segments_dir: Path) -> None:
    """Log preserved segments for resume on exception.

    Args:
        segments_dir: Directory containing downloaded segments.
    """
    if not segments_dir.exists():
        return

    # D-13: reported on every non-success exit, count 0 included. The old
    # `count > 0` gate emitted nothing in exactly the case that mattered --
    # a total loss -- so the operator saw silence instead of "nothing was
    # kept". The count below is deliberately labelled: it is every `*.ts` in
    # the working directory, and a failed merge leaves `batch_*.ts` temps
    # there, which a `*.ts` glob cannot distinguish from segments. Excluding
    # them is phase 07's ART-004; until then the count is stated as a
    # working-directory count and the action is to clear the directory.
    working_count = len(list(segments_dir.glob("*.ts")))
    logger.info(
        "preserving_segments_for_resume",
        working_dir=str(segments_dir),
        working_dir_ts_count=working_count,
        count_note=(
            "every *.ts file in the working directory, including any batch_*.ts "
            "merge temp a failed merge left behind; this is not a count of "
            "resumable segments"
        ),
        next_action="clear the working directory before re-running the download",
    )
