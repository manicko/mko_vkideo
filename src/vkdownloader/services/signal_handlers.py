"""Signal handlers for graceful shutdown on SIGINT/SIGTERM."""

from __future__ import annotations

import asyncio
import signal

from structlog import get_logger

from .downloader_throttle import get_shutdown_event

logger = get_logger(__name__)

# Track if signal handlers already setup to prevent duplicate registration
_signal_handlers_setup = False


__all__ = ["setup_signal_handlers"]


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown on SIGINT/SIGTERM."""
    global _signal_handlers_setup
    if _signal_handlers_setup:
        return

    shutdown_event = get_shutdown_event()

    def _handle_signal() -> None:
        """Signal handler to trigger graceful shutdown."""
        if not shutdown_event.is_set():
            logger.info("shutdown_signal_received")
            shutdown_event.set()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _handle_signal)
                _signal_handlers_setup = True
            except NotImplementedError:
                # Windows doesn't support loop.add_signal_handler in some Python versions
                # Use signal.signal as fallback
                signal.signal(sig, lambda s, f: _handle_signal())
                _signal_handlers_setup = True
    else:
        # Fallback for non-async context
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda s, f: _handle_signal())
            _signal_handlers_setup = True
