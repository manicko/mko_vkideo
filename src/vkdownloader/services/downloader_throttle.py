"""Throttle utilities for VK Video Downloader with retry logic for rate limiting."""

import asyncio
import random
from datetime import datetime

import aiohttp
from structlog import get_logger

from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)

# Status codes that should trigger retry
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


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

    for attempt in range(max_retries):
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
                delay = random.uniform(0, min(base_delay * (2 ** attempt), 30.0))

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

                await asyncio.sleep(delay)

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
        retry_date = datetime.strptime(
            retry_after, "%a, %d %b %Y %H:%M:%S GMT"
        )
        now = datetime.utcnow()
        delta = (retry_date - now).total_seconds()
        if delta > 0:
            return delta
    except (ValueError, TypeError):
        pass

    return None
