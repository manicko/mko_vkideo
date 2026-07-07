"""Adaptive rate limiting for VK Video Downloader."""

import asyncio
import random

from structlog import get_logger

logger = get_logger(__name__)


class AdaptiveThrottle:
    """Rate limiter with dynamic delay adjustment based on response patterns."""

    def __init__(self, base_rpm: int = 20, max_rpm: int = 60) -> None:
        """
        Initialize adaptive throttle with request rate parameters.

        Args:
            base_rpm: Base requests per minute for delay calculation.
            max_rpm: Maximum requests per minute allowed.
        """
        self.base_rpm = base_rpm
        self.max_rpm = max_rpm
        self.current_delay: float = self._calculate_base_delay()

    def _calculate_base_delay(self) -> float:
        """Calculate base delay from RPM settings."""
        return 60.0 / self.base_rpm

    async def wait(self) -> None:
        """Apply rate limiting delay with random jitter before requests."""
        delay = self.current_delay + random.uniform(0, 1)
        logger.debug("throttle_wait", delay=delay)
        await asyncio.sleep(delay)

    def on_rate_limited(self) -> None:
        """
        Increase delay after rate limiting response.

        Implements exponential backoff capped at maximum delay.
        """
        old_delay = self.current_delay
        self.current_delay = min(self.current_delay * 1.5, 10.0)
        logger.warning(
            "rate_limited_backoff",
            old_delay=old_delay,
            new_delay=self.current_delay,
        )

    def on_success(self) -> None:
        """
        Recover delay after successful request.

        Gradually reduces delay toward base minimum.
        """
        old_delay = self.current_delay
        self.current_delay = max(self.current_delay * 0.95, 1.0)
        logger.debug(
            "throttle_recovery",
            old_delay=old_delay,
            new_delay=self.current_delay,
        )

    def get_current_delay(self) -> float:
        """Return current delay value for monitoring purposes."""
        return self.current_delay
