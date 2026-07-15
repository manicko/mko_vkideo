"""Throttle utilities for VK Video Downloader with retry logic for rate limiting."""

import asyncio
import contextvars
import random
import time
from datetime import datetime

import aiohttp
from structlog import get_logger

from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)

# Status codes that should trigger retry
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

# ContextVar for shutdown event - provides loop-safe event per asyncio context
_shutdown_event_ctx: contextvars.ContextVar[asyncio.Event] = contextvars.ContextVar(
    "shutdown_event"
)


def get_shutdown_event() -> asyncio.Event:
    """Get the shutdown event for the current asyncio context.

    Creates a new Event if one doesn't exist in the current context.
    This ensures each event loop gets its own Event, avoiding the
    'bound to a different event loop' error.
    """
    try:
        return _shutdown_event_ctx.get()
    except LookupError:
        event = asyncio.Event()
        _shutdown_event_ctx.set(event)
        return event


class URLBackoffCoordinator:
    """Manages shared backoff state per URL for coordinated rate limiting.

    When a 429 response occurs on any segment of a URL, all segments
    of that URL pause to avoid cascading rate limit violations.
    """

    def __init__(self) -> None:
        self._backoff_state: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def pause(self, video_url: str, duration_seconds: float) -> None:
        """Set backoff duration for URL."""
        async with self._lock:
            self._backoff_state[video_url] = time.time() + duration_seconds

    async def wait_if_paused(self, video_url: str) -> bool:
        """Block until backoff expires for URL. Returns True if was paused."""
        async with self._lock:
            timestamp = self._backoff_state.get(video_url, 0)
        if time.time() >= timestamp:
            return False

        delay = timestamp - time.time()
        try:
            shutdown_event = get_shutdown_event()
            await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
            return True  # Shutdown triggered
        except TimeoutError:
            return True  # Backoff completed normally


class ProgressManager:
    """Thread-safe progress state manager for concurrent batch downloads.

    Encapsulates progress state and asyncio.Lock for safe concurrent access
    across multiple download tasks.

    Thread-safety notes:
        - The `_state` dict is accessed via async methods (update, clear, get_formatted_progress)
          with lock protection for thread-safe access across async tasks.
        - For sync callbacks (e.g., progress callbacks from segment downloads), use
          `update_sync()` which relies on single-event-loop execution semantics.
        - The async lock protects the read path in get_formatted_progress, ensuring consistent
          reads while callbacks may write concurrently.
    """

    def __init__(self) -> None:
        self._state: dict[int, tuple[int, int]] = {}
        self._lock = asyncio.Lock()

    async def update(self, url_index: int, downloaded: int, total: int) -> None:
        """Update progress for a URL in thread-safe manner.

        Args:
            url_index: Index of the URL in the batch for tracking.
            downloaded: Number of bytes downloaded so far.
            total: Total bytes to download.
        """
        async with self._lock:
            self._state[url_index] = (downloaded, total)

    def update_sync(self, url_index: int, downloaded: int, total: int) -> None:
        """Update progress for a URL from sync callbacks in the same event loop.

        This method is for use with sync callbacks that run within the asyncio event loop.
        It performs direct assignment without lock protection, relying on the guarantee that
        these callbacks execute sequentially in the single-threaded event loop.

        Args:
            url_index: Index of the URL in the batch for tracking.
            downloaded: Number of bytes downloaded so far.
            total: Total bytes to download.

        Note:
            Do not call this method from true multi-threaded contexts; use `update()` instead.
        """
        self._state[url_index] = (downloaded, total)

    async def get_formatted_progress(self, url_count: int) -> str:
        """Get formatted progress string for all URLs.

        Args:
            url_count: Total number of URLs in the batch.

        Returns:
            Formatted string like "video_0: 25/100, video_1: 45/150".
        """
        async with self._lock:
            progress_lines = [
                f"video_{i}: {self._state.get(i, (0, 0))[0]}/{self._state.get(i, (0, 0))[1]}"
                for i in range(url_count)
            ]
            return ", ".join(progress_lines)

    async def clear(self) -> None:
        """Clear progress state for new batch."""
        async with self._lock:
            self._state.clear()

    async def get_progress(self, url_index: int) -> tuple[int, int]:
        """Get progress tuple for a specific URL index.

        Args:
            url_index: Index of the URL to get progress for.

        Returns:
            Tuple of (downloaded, total), defaults to (0, 0) if not set.
        """
        async with self._lock:
            return self._state.get(url_index, (0, 0))


async def _retry_429_with_backoff(
    session: aiohttp.ClientSession,
    segment_url: str,
    headers: dict[str, str],
    segment_index: int,
    max_retries: int = 3,
) -> bytes | None:
    """Download segment with AWS Full Jitter exponential backoff for 429/5xx errors.

    Uses full jitter exponential backoff with Retry-After header priority.
    Reads response content inside retry loop to avoid lifecycle issues with context manager.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        headers: Request headers to use.
        segment_index: Index of the segment being downloaded (for logging).
        max_retries: Maximum number of retry attempts (default 3).

    Returns:
        Bytes content on success, None on permanent failure.
    """
    sanitized_url = _strip_auth_params(segment_url)
    shutdown_event = get_shutdown_event()

    for attempt in range(max_retries):
        # Check for shutdown signal before each attempt
        if shutdown_event.is_set():
            logger.info("download_cancelled", segment_index=segment_index, url=sanitized_url)
            return None

        try:
            async with session.get(segment_url, headers=headers) as response:
                if response.status == 200:
                    return await response.read()

                if response.status not in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        "segment_download_failed_non_retryable",
                        status=response.status,
                        segment_index=segment_index,
                        url=sanitized_url,
                    )
                    return None

                # Parse Retry-After header
                retry_after_seconds = _parse_retry_after(response)

                # Determine base delay based on status code
                if response.status == 429:
                    base_delay = 1.0
                else:
                    # 5xx errors use shorter base delay per AWS SDK guidance
                    base_delay = 0.05

                # Calculate delay with full jitter: random(0, base_delay * 2^attempt)
                delay = random.uniform(0, min(base_delay * (2**attempt), 30.0))

                # Prefer Retry-After header over calculated delay
                if retry_after_seconds is not None:
                    delay = max(delay, retry_after_seconds)

                logger.warning(
                    "segment_retry_429",
                    attempt=attempt + 1,
                    status=response.status,
                    retry_after=retry_after_seconds,
                    segment_index=segment_index,
                    url=sanitized_url,
                )

                # Use asyncio.wait_for to allow interruption during sleep
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
                    # If wait completes (shutdown was triggered), return None
                    logger.info(
                        "download_cancelled", segment_index=segment_index, url=sanitized_url
                    )
                    return None
                except TimeoutError:
                    # Normal timeout - continue with retry
                    pass

        except asyncio.CancelledError:
            logger.info(
                "segment_download_cancelled", segment_index=segment_index, url=sanitized_url
            )
            raise
        except Exception as e:
            logger.error(
                "segment_download_error",
                error=str(e),
                segment_index=segment_index,
                url=sanitized_url,
            )
            return None

    return None


def _parse_retry_after(response: aiohttp.ClientResponse) -> float | None:
    """Parse Retry-After header from response.

    Handles both integer seconds and HTTP date formats.

    Args:
        response: aiohttp ClientResponse with headers.

    Returns:
        Seconds to wait, or None if header not present or invalid.
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None

    # Try parsing as integer seconds
    try:
        return float(retry_after)
    except ValueError:
        pass

    # Try parsing as HTTP date
    try:
        retry_date = datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S GMT")
        now = datetime.utcnow()
        delta = (retry_date - now).total_seconds()
        if delta > 0:
            return delta
    except (ValueError, TypeError):
        pass

    return None
