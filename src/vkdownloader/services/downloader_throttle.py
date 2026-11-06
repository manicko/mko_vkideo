"""Throttle utilities for VK Video Downloader."""

from __future__ import annotations

import asyncio
import contextvars
import random  # noqa: F401 — test-compat: patches target downloader_throttle.random.uniform
import time
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from structlog import get_logger

from ..config import Settings
from ..utils.formatting import format_bytes
from ..utils.url_sanitizer import (
    _strip_auth_params as _strip_auth_params,  # noqa: F401 — re-exported for retry_policies module-level access
)

if TYPE_CHECKING:
    import aiohttp

logger = get_logger(__name__)

# Single source of truth for the download-timeout default. Mirrors
# Settings.download_timeout's declared default at import time; every consumer
# default in segment_downloader.py and ffmpeg_utils.py is sourced from this
# constant rather than re-hardcoding 300, so the two converge on the schema
# in one place.
DEFAULT_DOWNLOAD_TIMEOUT: int = Settings.model_fields["download_timeout"].default


def build_client_timeout(download_timeout: int) -> aiohttp.ClientTimeout:
    """Compose a ``ClientTimeout`` from the ``download_timeout`` setting.

    Replaces the three byte-identical compositions that were duplicated across
    ``downloader_throttle.py``, ``segment_downloader.py`` (x2). The floor (30s)
    on ``connect`` is preserved; ``sock_connect`` is removed (it is redundant
    with ``connect``); ``sock_read`` is set to the full ``download_timeout`` so
    the per-read ceiling grows with the operator's budget.
    """
    import aiohttp

    return aiohttp.ClientTimeout(
        total=download_timeout,
        connect=min(30, download_timeout // 4),
        sock_read=download_timeout,
    )


# Default pause duration (seconds) applied to a shared origin backoff across all
# segment and manifest retries when a retryable transport failure is observed.
_DEFAULT_BACKOFF_PAUSE_SECONDS: float = 10.0

# HTTP status code indicating a transport-layer failure from the upstream server.
_TRANSPORT_FAILURE_STATUS: int = 500


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
        self._state: dict[int, tuple[int, int, str]] = {}
        self._lock = asyncio.Lock()

    async def update(
        self, url_index: int, downloaded: int, total: int, unit: str = "bytes"
    ) -> None:
        """Update progress for a URL in thread-safe manner."""
        async with self._lock:
            self._state[url_index] = (int(downloaded), int(total), str(unit))

    def update_sync(self, url_index: int, downloaded: int, total: int, unit: str = "bytes") -> None:
        """Update progress for a URL from sync callbacks."""
        self._state[url_index] = (int(downloaded), int(total), str(unit))

    async def get_formatted_progress(self, url_count: int) -> str:
        """Get formatted progress string for all URLs."""
        async with self._lock:
            progress_lines = []
            for i in range(url_count):
                downloaded, total, unit = self._state.get(i, (0, 0, "bytes"))
                if unit == "segments":
                    if total and total > 0:
                        progress_lines.append(f"video_{i}: {downloaded}/{total} segments")
                    else:
                        progress_lines.append(f"video_{i}: {downloaded} segments")
                else:
                    if total and total > 0:
                        progress_lines.append(
                            f"video_{i}: {format_bytes(downloaded)}/{format_bytes(total)}"
                        )
                    else:
                        progress_lines.append(f"video_{i}: {format_bytes(downloaded)}")
            return ", ".join(progress_lines)

    async def clear(self) -> None:
        """Clear progress state for new batch."""
        async with self._lock:
            self._state.clear()


_HTTP_DATE_FORMATS = (
    "%a, %d %b %Y %H:%M:%S GMT",  # IMF-fixdate (RFC 7231)
    "%A, %d-%b-%y %H:%M:%S GMT",  # RFC 850
    "%a %b %d %H:%M:%S %Y",  # asctime (RFC 7231)
)
