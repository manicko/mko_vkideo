"""Signal handlers for graceful shutdown on SIGINT/SIGTERM."""

from __future__ import annotations

import asyncio
import signal

from structlog import get_logger

from .downloader_throttle import get_shutdown_event

logger = get_logger(__name__)

# Track registered signals for loop-scoped cleanup
_registered_signals: set[signal.Signals] = set()


__all__ = ["setup_signal_handlers", "cleanup_signal_handlers"]


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown on SIGINT/SIGTERM.

    Registers handlers on the current running event loop. Handlers are loop-scoped
    and must be cleaned up via cleanup_signal_handlers() after the async context exits.
    """
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
                _registered_signals.add(sig)
            except NotImplementedError:
                # Windows doesn't support loop.add_signal_handler in some Python versions
                # Use signal.signal as fallback
                signal.signal(sig, lambda s, f: _handle_signal())
                _registered_signals.add(sig)
    else:
        # Fallback for non-async context
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda s, f: _handle_signal())
            _registered_signals.add(sig)


def cleanup_signal_handlers() -> None:
    """Remove signal handlers and reset registration state.

    Must be called after the async context exits to allow re-registration
    on subsequent event loops in the same process.
    """
    global _registered_signals

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        for sig in list(_registered_signals):
            try:
                loop.remove_signal_handler(sig)
            except (NotImplementedError, KeyError, RuntimeError):
                # Ignore errors if handler wasn't registered or loop closed
                pass
    else:
        # Fallback: reset signal handlers to default in non-async context
        for sig in list(_registered_signals):
            try:
                signal.signal(sig, signal.SIG_DFL)
            except (OSError, ValueError, RuntimeError):
                # Ignore errors if signal not registered
                pass

    _registered_signals.clear()
