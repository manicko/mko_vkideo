"""Correlation ID utilities for structlog request tracing.

Provides a thin wrapper around :mod:`structlog.contextvars` so that every
log entry emitted within a logical operation (e.g. a single download)
carries a ``correlation_id`` field. This makes it possible to filter and
group log output for a specific request across the extract -> select ->
download pipeline, including in concurrent batch mode.
"""

import uuid

import structlog.contextvars


def generate_correlation_id() -> str:
    """Generate a short 8-character hex correlation ID.

    Returns:
        An 8-character lowercase hexadecimal string derived from
        ``uuid.uuid4().hex``.
    """
    return uuid.uuid4().hex[:8]


def bind_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID to the current structlog context.

    All subsequent structlog log calls within the same async context will
    include the ``correlation_id`` field in their output.

    Args:
        correlation_id: The correlation ID to bind (typically from
            :func:`generate_correlation_id`).
    """
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_correlation_id() -> None:
    """Unbind the correlation ID from the structlog context.

    Removes only the ``correlation_id`` key, preserving any other context
    variables that may have been bound alongside it. Should be called in a
    ``finally`` block to prevent correlation-ID leakage between operations.
    """
    structlog.contextvars.unbind_contextvars("correlation_id")


def get_correlation_id() -> str | None:
    """Get the current correlation ID from the structlog context.

    Returns:
        The bound correlation ID, or ``None`` if no correlation ID has been
        bound in the current context.
    """
    context_vars = structlog.contextvars.get_contextvars()
    return context_vars.get("correlation_id")
