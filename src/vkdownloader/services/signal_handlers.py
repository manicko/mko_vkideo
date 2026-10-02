"""Signal handlers for graceful shutdown on SIGINT/SIGTERM."""

from __future__ import annotations

import asyncio
import signal

from structlog import get_logger

from .downloader_throttle import get_shutdown_event

logger = get_logger(__name__)

# Three distinct facts, kept apart on purpose:
#   _registered_signals  - signals installed for; the single gate and iteration set
#   _previous_handlers  - what was installed BEFORE this module displaced it (may differ
#                          per signal: SIGINT is the runtime's Runner._on_sigint partial,
#                          SIGTERM is SIG_DFL)
#   _installed_handlers - the callable installed here; the identity guard reads it
_registered_signals: set[signal.Signals] = set()
_previous_handlers: dict[signal.Signals, signal._HANDLER | None] = {}
_installed_handlers: dict[signal.Signals, signal._HANDLER] = {}

# Single source for the two signals this module displaces and restores: SIGINT's
# displaced handler is asyncio.runners.Runner._on_sigint (NOT SIG_DFL), while SIGTERM's
# is SIG_DFL, so the two values differ and neither may be assumed to be signal.SIG_DFL.
_HANDLED_SIGNALS: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM)


__all__ = ["setup_signal_handlers", "cleanup_signal_handlers"]


def _capture_previous_handler(sig: signal.Signals) -> None:
    """Record the process-level handler this module is about to displace.

    Captured once per signal: a second setup with no intervening cleanup must keep the
    ORIGINAL pre-install value, or the cleanup that follows would restore this module's
    own handler and the displacement would survive it. signal.getsignal returns None for
    a signal never set from Python, and there is then nothing to put back, so it is
    not stored.
    """
    if sig in _previous_handlers:
        return
    previous = signal.getsignal(sig)
    if previous is not None:
        _previous_handlers[sig] = previous


def _restore_previous_handler(sig: signal.Signals) -> None:
    """Put back the handler captured at install time, once.

    Skipped when nothing was captured, and skipped when the installed handler is no longer
    the one installed here -- a third party owns the disposition then, and clobbering it
    would be worse than leaving it. Never signal.SIG_DFL for SIGINT: the displaced handler
    is asyncio.runners.Runner._on_sigint, and resetting to the default would turn Ctrl-C
    from "cancel the main task" into "terminate the process".
    """
    previous = _previous_handlers.get(sig)
    if previous is None:
        return
    if signal.getsignal(sig) is not _installed_handlers.get(sig):
        return
    try:
        signal.signal(sig, previous)
    except (OSError, ValueError, RuntimeError):
        # Ignore errors if the signal is not restorable from this thread or context
        pass


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown on SIGINT/SIGTERM.

    The handler installed for each signal BEFORE this module displaced it is captured per
    signal and retained, because the two pre-install values differ -- SIGINT is the
    runtime's ``Runner._on_sigint`` partial and SIGTERM is ``SIG_DFL`` -- and neither may
    be assumed to be ``signal.SIG_DFL``. ``cleanup_signal_handlers`` restores exactly
    those captured values, which is what lets ``asyncio.run`` perform its own SIGINT
    restore on exit.
    """
    shutdown_event = get_shutdown_event()

    def _handle_signal() -> None:
        """Signal handler to trigger graceful shutdown."""
        if not shutdown_event.is_set():
            logger.info("shutdown_signal_received")
            shutdown_event.set()

    def _process_signal(_sig: int, _frame: object) -> None:
        _handle_signal()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        for sig in _HANDLED_SIGNALS:
            try:
                loop.add_signal_handler(sig, _handle_signal)
                _registered_signals.add(sig)
            except NotImplementedError:
                # Windows ProactorEventLoop.add_signal_handler is unavailable; fall back
                # to the process-level signal.signal, capturing what this module displaces.
                _capture_previous_handler(sig)
                signal.signal(sig, _process_signal)
                _installed_handlers[sig] = _process_signal
                _registered_signals.add(sig)
    else:
        # Fallback for a non-async context: install process-level handlers directly.
        for sig in _HANDLED_SIGNALS:
            _capture_previous_handler(sig)
            signal.signal(sig, _process_signal)
            _installed_handlers[sig] = _process_signal
            _registered_signals.add(sig)


def cleanup_signal_handlers() -> None:
    """Restore each signal's captured pre-install handler and clear state.

    The handler captured for each signal at setup time is put back, per signal, because
    the two captured values differ -- SIGINT's is the runtime's ``Runner._on_sigint``
    partial and SIGTERM's is ``SIG_DFL`` -- and neither may be assumed to be
    ``signal.SIG_DFL``. A signal already replaced by a third party is left alone, and
    the three module stores are cleared together so the next cycle re-captures instead
    of re-using a stale value.
    """
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

    # Hoisted out of the loop/non-loop split so both paths share one restore. On a loop
    # that supports remove_signal_handler this is a no-op (nothing was captured there),
    # and where the loop-level restore is unavailable the identity guard puts the
    # process-level handler back -- never signal.SIG_DFL, which is wrong for SIGINT.
    for sig in list(_registered_signals):
        _restore_previous_handler(sig)

    # Cleared as one group: a store that outlives a cycle makes the next one re-use a
    # stale value instead of re-capturing.
    _registered_signals.clear()
    _previous_handlers.clear()
    _installed_handlers.clear()
