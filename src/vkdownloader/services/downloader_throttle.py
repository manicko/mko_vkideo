"""Throttle utilities for VK Video Downloader with retry logic for rate limiting."""

import asyncio
import contextvars
import random
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

import aiohttp
from structlog import get_logger

from ..config import Settings
from ..utils.formatting import format_bytes
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)

# Single source of truth: the download timeout default is owned by Settings.download_timeout.
_DEFAULT_DOWNLOAD_TIMEOUT: int = Settings.model_fields["download_timeout"].default

# Default pause duration (seconds) applied to a shared origin backoff across all
# segment and manifest retries when a retryable transport failure is observed.
_DEFAULT_BACKOFF_PAUSE_SECONDS: float = 10.0

# HTTP status code indicating a transport-layer failure from the upstream server.
_TRANSPORT_FAILURE_STATUS: int = 500

# Status codes that should trigger retry.
# INT-008: widened to include 408 (Request Timeout) and 425 (Too Early) alongside
# the existing 429 and 5xx transport failures.
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def _resource_key(url: str) -> str:
    """Return a normalized origin key for *url*.

    The key is the scheme-stripped, userinfo-stripped, lowercased netloc
    (``host:port``) so that any path or query variation on the same origin
    maps to the same backoff slot.
    """
    parsed = urlsplit(url)
    netloc = parsed.hostname or ""
    if parsed.port is not None:
        netloc = f"{parsed.hostname}:{parsed.port}"
    return netloc.lower()


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

    def __init__(self, pause_seconds: float = _DEFAULT_BACKOFF_PAUSE_SECONDS) -> None:
        self.pause_seconds: float = pause_seconds
        self._backoff_state: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def pause(self, resource_url: str, duration_seconds: float) -> None:
        """Set backoff duration for URL.

        Normalizes *resource_url* via ``_resource_key`` so that any path or
        query variation on the same origin maps to the same backoff slot.
        """
        key = _resource_key(resource_url)
        async with self._lock:
            self._backoff_state[key] = time.time() + duration_seconds

    async def wait_if_paused(self, resource_url: str) -> bool:
        """Block until backoff expires for URL. Returns True if was paused.

        Normalizes *resource_url* via ``_resource_key`` internally so callers
        may pass the raw URL.
        """
        key = _resource_key(resource_url)
        async with self._lock:
            timestamp = self._backoff_state.get(key, 0)
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

    Deprecation note (spec T9 / risk R5): this class has no production callers
    now that ``RichProgressReporter`` owns the batch-download progress display.
    It is retained only for backward compatibility with external importers that
    import ``ProgressManager`` directly from this module, and
    ``tests/test_downloader_throttle.py`` still exercises it. Once that
    deprecation window closes, it can be removed without replacement.

    Thread-safety notes:
        - The `_state` dict is accessed via async methods (update, clear, get_formatted_progress)
          with lock protection for thread-safe access across async tasks.
        - Sync callbacks (the ``progress_callback(...)`` invocations in this
          codebase) are delivered on the asyncio event loop thread, so
          ``update_sync()`` performs a direct dict assignment without lock
          protection.
        - The async lock protects the read path in get_formatted_progress,
          ensuring consistent reads while other async tasks may update between
          awaits.
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
        """Update progress for a URL from sync callbacks on the event loop thread.

        This is a synchronous progress-callback update that performs a direct
        dict assignment without lock protection. That is safe here because
        progress callbacks in this codebase are delivered on the asyncio event
        loop thread, not via ``loop.run_in_executor``.

        Args:
            url_index: Index of the URL in the batch for tracking.
            downloaded: Number of bytes downloaded so far.
            total: Total bytes to download.

        Note:
            If progress is ever updated from a thread pool or executor thread,
            use the async ``update()`` method instead, which acquires the
            asyncio lock.
        """
        self._state[url_index] = (downloaded, total)

    async def get_formatted_progress(self, url_count: int) -> str:
        """Get formatted progress string for all URLs.

        Args:
            url_count: Total number of URLs in the batch.

        Returns:
            Formatted string like "video_0: 25B/100B, video_1: 45/100".
            Units are detected heuristically: values exceeding 1024 are
            treated as byte counts and formatted with SI prefixes (B/KB/MB/etc.);
            smaller totals are treated as segment counts and displayed
            numerically. When total is 0 (unknown), only downloaded bytes are shown.
        """
        async with self._lock:
            progress_lines = []
            for i in range(url_count):
                downloaded, total = self._state.get(i, (0, 0))
                if total <= 0:
                    # Unknown total: byte-based progress (yt-dlp/ffmpeg streams in)
                    progress_lines.append(f"video_{i}: {format_bytes(downloaded)}")
                elif total > 1024:
                    # Byte-based progress (yt-dlp/ffmpeg)
                    progress_lines.append(
                        f"video_{i}: {format_bytes(downloaded)}/{format_bytes(total)}"
                    )
                else:
                    # Segment-count-based progress
                    progress_lines.append(f"video_{i}: {downloaded}/{total} segments")
            return ", ".join(progress_lines)

    async def clear(self) -> None:
        """Clear progress state for new batch."""
        async with self._lock:
            self._state.clear()


async def _retry_429_with_backoff(
    session: aiohttp.ClientSession,
    segment_url: str,
    headers: dict[str, str],
    segment_index: int,
    max_retries: int = 3,
    download_timeout: int = _DEFAULT_DOWNLOAD_TIMEOUT,
) -> bytes | None:
    """Download segment with AWS Full Jitter exponential backoff for 429/5xx errors.

    Uses full jitter exponential backoff, treating the Retry-After header as a floor on the computed delay.
    Reads response content inside retry loop to avoid lifecycle issues with context manager.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        headers: Request headers to use.
        segment_index: Index of the segment being downloaded (for logging).
        max_retries: Maximum number of retry attempts (default 3).
        download_timeout: Total timeout for HTTP request in seconds.

    Returns:
        Bytes content on success, None on permanent failure.
    """
    sanitized_url = _strip_auth_params(segment_url)
    shutdown_event = get_shutdown_event()
    client_timeout = aiohttp.ClientTimeout(
        total=download_timeout,
        connect=min(30, download_timeout // 4),
        sock_connect=30,
        sock_read=60,
    )

    for attempt in range(max_retries):
        if shutdown_event.is_set():
            logger.info("download_cancelled", segment_index=segment_index, url=sanitized_url)
            return None

        try:
            async with session.get(
                segment_url, headers=headers, timeout=client_timeout
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    if len(content) == 0:
                        logger.warning(
                            "empty_segment_content", segment_index=segment_index, url=sanitized_url
                        )
                        return None
                    return content

                if response.status not in RETRYABLE_STATUS_CODES:
                    logger.warning(
                        "segment_download_failed_non_retryable",
                        status=response.status,
                        segment_index=segment_index,
                        url=sanitized_url,
                    )
                    return None

                retry_after_seconds = _parse_retry_after(response)
                delay = _compute_backoff_delay(response.status, attempt, retry_after_seconds)

                logger.warning(
                    "segment_retry_429",
                    attempt=attempt + 1,
                    status=response.status,
                    retry_after=retry_after_seconds,
                    segment_index=segment_index,
                    url=sanitized_url,
                )

                if attempt == max_retries - 1:
                    break

                if await _wait_with_shutdown(delay, shutdown_event, segment_index, sanitized_url):
                    return None

        except asyncio.CancelledError:
            logger.info(
                "segment_download_cancelled", segment_index=segment_index, url=sanitized_url
            )
            raise
        # INT-006: Narrow exception handling to network-level errors only.
        # Previously caught broad ``Exception``, which swallowed programming
        # errors (TypeError, AttributeError, etc.) and treated them as
        # transient download failures. ``aiohttp.ClientError`` does not cover
        # all asyncio-level errors (e.g. ``TimeoutError`` in some aiohttp
        # versions), so both are listed explicitly.
        except (aiohttp.ClientError, TimeoutError) as e:
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
        retry_date = datetime.strptime(retry_after, "%a, %d %b %Y %H:%M:%S GMT").replace(tzinfo=UTC)
        now = datetime.now(UTC)
        delta = (retry_date - now).total_seconds()
        if delta > 0:
            return delta
    except (ValueError, TypeError):
        pass

    return None


def _compute_backoff_delay(
    status_code: int,
    attempt: int,
    retry_after_seconds: float | None,
) -> float:
    """Compute backoff delay using AWS Full Jitter exponential backoff.

    Calculates delay with full jitter: random(0, base_delay * 2^attempt).
    Retry-After header, if present, is a floor on the computed delay.

    Args:
        status_code: HTTP status code.
        attempt: Current retry attempt number (0-indexed).
        retry_after_seconds: Seconds from Retry-After header, if any.

    Returns:
        Seconds to wait before retry.
    """
    # Determine base delay based on status code
    if status_code == 429:
        base_delay = 1.0
    else:
        # 5xx errors use shorter base delay per AWS SDK guidance
        base_delay = 0.05

    # Calculate delay with full jitter: random(0, base_delay * 2^attempt)
    delay = random.uniform(0, min(base_delay * (2**attempt), 30.0))

    # Retry-After header is a floor on the calculated delay
    if retry_after_seconds is not None:
        delay = max(delay, retry_after_seconds)

    return delay


async def _wait_with_shutdown(
    delay: float,
    shutdown_event: asyncio.Event | None,
    segment_index: int,
    url: str,
) -> bool:
    """Wait for specified delay while monitoring shutdown signal.

    Uses asyncio.wait_for to allow interruption during sleep.

    Args:
        delay: Seconds to wait.
        shutdown_event: Event that signals shutdown, if set returns True immediately.
        segment_index: Segment index for logging.
        url: Sanitized URL for logging.

    Returns:
        True if shutdown was triggered, False if delay completed normally.
    """
    if shutdown_event is None:
        await asyncio.sleep(delay)
        return False

    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
        # If wait completes (shutdown was triggered), return True
        logger.info("download_cancelled", segment_index=segment_index, url=url)
        return True
    except TimeoutError:
        # Normal timeout - continue with retry
        return False
