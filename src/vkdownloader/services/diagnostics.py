"""Diagnostics re-export for service-layer imports."""

from vkdownloader.utils.diagnostics import (
    STRUCTURED_DIAGNOSTIC_EVENTS,
    STRUCTURED_DIAGNOSTIC_FIELDS,
    ChildTranscriptSink,
    DiagnosticContext,
    bind_diagnostic_context,
    open_diagnostic_sink,
)

__all__ = [
    "STRUCTURED_DIAGNOSTIC_EVENTS",
    "STRUCTURED_DIAGNOSTIC_FIELDS",
    "ChildTranscriptSink",
    "DiagnosticContext",
    "bind_diagnostic_context",
    "open_diagnostic_sink",
]
