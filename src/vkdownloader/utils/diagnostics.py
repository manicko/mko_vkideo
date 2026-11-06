"""Diagnostic helpers for Block C."""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vkdownloader.config import Settings
from vkdownloader.utils.url_sanitizer import sanitize_for_log, sanitize_text_for_log

STRUCTURED_DIAGNOSTIC_EVENTS = (
    "job_started",
    "workspace_opened",
    "backend_started",
    "backend_stopped",
    "child_exit",
    "segment_request_failed",
    "retry_scheduled",
    "refresh_requested",
    "refresh_completed",
    "backend_switch_blocked",
    "resume_checkpoint_loaded",
    "progress_estimate_unreliable",
    "job_failed_preserved",
    "media_verified",
    "job_committed",
)

STRUCTURED_DIAGNOSTIC_FIELDS = (
    "job_id",
    "attempt_id",
    "correlation_id",
    "backend",
    "stream_variant_id",
    "quality_requested",
    "fragment_done",
    "fragment_total",
    "resume_bytes",
    "elapsed_seconds",
    "reason_code",
    "retry_in_seconds",
    "http_status",
    "host",
    "path",
)


@dataclass
class DiagnosticContext:
    job_id: str | None = None
    attempt_id: int = 0
    correlation_id: str | None = None
    backend: str | None = None
    stream_variant_id: str | None = None
    quality_requested: str | None = None
    fragment_done: int | None = None
    fragment_total: int | None = None
    resume_bytes: int | None = None
    elapsed_seconds: float | None = None
    reason_code: str | None = None
    retry_in_seconds: float | None = None
    http_status: int | None = None
    host: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _PrivateRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler that keeps rotated/new files owner-only on POSIX."""

    def _open(self):
        stream = super()._open()
        try:
            os.chmod(self.baseFilename, 0o600)
        except OSError:
            pass
        return stream


class ChildTranscriptSink:
    def __init__(
        self,
        path: str | Path,
        max_line_bytes: int = 4096,
        progress_rate_limit_seconds: float = 0.25,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        *,
        progress_min_interval_seconds: float | None = None,
    ) -> None:
        if progress_min_interval_seconds is not None:
            progress_rate_limit_seconds = progress_min_interval_seconds
        self.path = Path(path)
        self.max_line_bytes = max_line_bytes
        self.progress_rate_limit_seconds = progress_rate_limit_seconds
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._last_progress_time = 0.0
        self._disabled = False
        self._handler: logging.handlers.RotatingFileHandler | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handler = _PrivateRotatingFileHandler(
                self.path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._handler = handler
            try:
                self.path.chmod(0o600)
            except OSError:
                pass
        except OSError:
            self._disabled = True
            self._handler = None

    def write_line(self, line: object, *, is_progress: bool = False) -> None:
        if self._disabled or self._handler is None:
            return
        now = time.monotonic()
        if is_progress:
            if now - self._last_progress_time < self.progress_rate_limit_seconds:
                return
            self._last_progress_time = now
        try:
            sanitized = sanitize_text_for_log(str(line).rstrip("\r\n"))

            sanitized = re.sub(
                r"(?i)((?:authorization|proxy-authorization|cookie|set-cookie|x-api-key|x-auth-token|api-key):)\s*.*",
                r"\1 ***REDACTED***",
                sanitized,
            )
            data = sanitized.encode("utf-8")
            if len(data) > self.max_line_bytes:
                data = data[: self.max_line_bytes]
                sanitized = data.decode("utf-8", errors="ignore") + "...[truncated]"
            record = {
                "event": "child_output",
                "line": sanitized,
                "is_progress": is_progress,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            msg = json.dumps(record, ensure_ascii=False)
            log_record = logging.LogRecord(
                name="child_transcript",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=msg,
                args=(),
                exc_info=None,
            )
            self._handler.emit(log_record)
        except OSError, ValueError:
            self._disabled = True
            try:
                if self._handler is not None:
                    self._handler.close()
            except Exception:
                pass
            self._handler = None

    def close(self) -> None:
        if self._handler is not None:
            try:
                self._handler.close()
            except Exception:
                pass
            self._handler = None


def open_diagnostic_sink(path: object, settings: Settings) -> ChildTranscriptSink | None:
    if path is None:
        return None
    if not getattr(settings, "diagnostics_enabled", True):
        return None
    try:
        max_bytes = getattr(settings, "log_max_bytes", 10 * 1024 * 1024)
        backup_count = getattr(settings, "log_backup_count", 5)
        return ChildTranscriptSink(
            path,
            max_bytes=max_bytes,
            backup_count=backup_count,
        )
    except Exception:
        try:
            from structlog import get_logger

            get_logger(__name__).warning("child_transcript_sink_disabled", path=str(path))
        except Exception:
            pass
        return None


def bind_diagnostic_context(**kwargs: object) -> dict[str, object]:
    sanitized = {key: sanitize_for_log(value) for key, value in kwargs.items()}
    try:
        import structlog.contextvars

        structlog.contextvars.bind_contextvars(**sanitized)
    except Exception:
        pass
    return sanitized
