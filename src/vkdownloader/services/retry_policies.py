"""HTTP retry policies with backoff scheduling for rate-limited downloads.

This module centralizes the retry logic for HTTP segment downloads that
fail with retryable status codes (408, 425, 429, and 5xx transport errors).
It provides AWS Full Jitter exponential backoff, Retry-After header parsing,
and shutdown-aware waiting.
"""

import asyncio
import random
from datetime import UTC, datetime

import aiohttp

from . import downloader_throttle
from .downloader_throttle import (
    _HTTP_DATE_FORMATS,
    DEFAULT_DOWNLOAD_TIMEOUT,
    build_client_timeout,
    logger,
)

# Status codes that should trigger retry.
# Widened to include 408 (Request Timeout) and 425 (Too Early) alongside
# the existing 429 and 5xx transport failures.
RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


async def _retry_429_with_backoff(
    session: aiohttp.ClientSession,
    segment_url: str,
    headers: dict[str, str],
    segment_index: int,
    max_retries: int = 3,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
) -> bytes | None:
    """Download segment with AWS Full Jitter backoff for 429/5xx errors.

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
    sanitized_url = downloader_throttle._strip_auth_params(segment_url)
    shutdown_event = downloader_throttle.get_shutdown_event()
    client_timeout = build_client_timeout(download_timeout)

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
        # Narrow exception handling to network-level errors only.
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
            # Transport-level failure (connection reset, timeout, DNS, etc.):
            # treat as transient and retry with backoff instead of giving
            # up immediately (NET-010 sequential).
            delay = _compute_backoff_delay(503, attempt, None)
            if attempt == max_retries - 1:
                break
            if await _wait_with_shutdown(delay, shutdown_event, segment_index, sanitized_url):
                return None
            continue

    return None


def _parse_retry_after(response: aiohttp.ClientResponse) -> float | None:
    """Parse Retry-After header from response.

    Handles integer seconds and three HTTP-date forms (IMF-fixdate, RFC 850,
    asctime) per RFC 7231 §7.1.3. Non-positive parsed values are rejected.
    Lower-case variants (e.g. ``gmt``) are accepted via upper-casing.

    Args:
        response: aiohttp ClientResponse with headers.

    Returns:
        Seconds to wait (always positive), or None if header absent,
        invalid, or in the past.
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None

    # Try parsing as integer seconds
    try:
        seconds = float(retry_after.strip())
        if seconds <= 0:
            return None
        return seconds
    except ValueError, TypeError:
        pass

    # Try parsing as HTTP date (IMF-fixdate, RFC 850, asctime)
    normalized = retry_after.strip().upper()
    for date_format in _HTTP_DATE_FORMATS:
        try:
            retry_date = datetime.strptime(normalized, date_format).replace(tzinfo=UTC)
            now = datetime.now(UTC)
            delta = (retry_date - now).total_seconds()
            if delta > 0:
                return delta
            return None  # Past date — ignored per spec (criterion 6)
        except ValueError, TypeError:
            continue

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

    # Calculate delay with full jitter: random(0, min(base_delay * 2^attempt, 30.0))
    # The 30s ceiling bounds the jitter RANGE passed to random.uniform —
    # test_delay_caps_at_30_seconds asserts this and must stay green unchanged.
    delay = random.uniform(0, min(base_delay * (2**attempt), 30.0))

    # Retry-After header is a floor on the calculated delay. The 30s ceiling
    # is applied AFTER this max, so Retry-After is a clamped floor (NET-018):
    # values above the ceiling are clamped, not passed through uncapped.
    if retry_after_seconds is not None:
        delay = max(delay, retry_after_seconds)

    delay = min(delay, 30.0)

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
