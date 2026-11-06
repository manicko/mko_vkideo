"""Observable, budgeted download state machine (Block G).

This module owns the single source of truth for a download job's state,
its combined retry budget, stream-refresh cap, error classification and
atomic persistence to ``workspace.state_path``. It never deletes artifacts.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict
from structlog import get_logger

from ..models.enums import DownloadState, ErrorCategory
from .checkpoint import write_state_atomic

if TYPE_CHECKING:
    from .workspace import DownloadWorkspace


class _Logger(Protocol):
    def debug(self, *args: object, **kwargs: object) -> None: ...
    def info(self, *args: object, **kwargs: object) -> None: ...
    def warning(self, *args: object, **kwargs: object) -> None: ...
    def error(self, *args: object, **kwargs: object) -> None: ...


logger = get_logger(__name__)

YTDLP_INTERNAL_RETRIES = 1
REFRESH_CAP = 2
COMBINED_RETRY_BUDGET = 6

_TERMINAL_STATES: frozenset[DownloadState] = frozenset(
    {
        DownloadState.DONE,
        DownloadState.PRESERVE_AND_STOP,
        DownloadState.CANCELLED,
        DownloadState.DISK_FULL,
        DownloadState.FAILED_RETRY_BUDGET,
        DownloadState.INTEGRITY_FAILED,
        DownloadState.FAILED,
    }
)

# Explicit allow-list of valid transitions. Terminal states have no outgoing
# edges. Every non-terminal state may also move to any terminal state so that
# cancellation / disk-full / budget exhaustion can be recorded from anywhere.
_AUTO_TERMINALS: frozenset[DownloadState] = frozenset(
    {
        DownloadState.PRESERVE_AND_STOP,
        DownloadState.CANCELLED,
        DownloadState.DISK_FULL,
        DownloadState.FAILED_RETRY_BUDGET,
        DownloadState.INTEGRITY_FAILED,
        DownloadState.FAILED,
    }
)
_BASE_TRANSITIONS: dict[DownloadState, set[DownloadState]] = {
    DownloadState.CREATED: {DownloadState.RESOLVE_STREAM},
    DownloadState.RESOLVE_STREAM: {
        DownloadState.VALIDATE_VARIANT,
        DownloadState.REFRESH_STREAM,
        DownloadState.RETRY,
    },
    DownloadState.VALIDATE_VARIANT: {DownloadState.DOWNLOAD, DownloadState.REFRESH_STREAM},
    DownloadState.DOWNLOAD: {
        DownloadState.VERIFY_MEDIA,
        DownloadState.RETRY_SAME_SEGMENT,
        DownloadState.REFRESH_STREAM,
        DownloadState.RATE_LIMIT_WAIT,
        DownloadState.RETRY,
    },
    DownloadState.RETRY_SAME_SEGMENT: {
        DownloadState.DOWNLOAD,
        DownloadState.REFRESH_STREAM,
        DownloadState.RATE_LIMIT_WAIT,
        DownloadState.RETRY,
    },
    DownloadState.REFRESH_STREAM: {DownloadState.VALIDATE_VARIANT, DownloadState.DOWNLOAD},
    DownloadState.RATE_LIMIT_WAIT: {DownloadState.DOWNLOAD, DownloadState.RETRY},
    DownloadState.RETRY: {DownloadState.RESOLVE_STREAM, DownloadState.DOWNLOAD},
    DownloadState.VERIFY_MEDIA: {DownloadState.COMMIT, DownloadState.INTEGRITY_FAILED},
    DownloadState.COMMIT: {DownloadState.DONE},
}


def _build_transitions() -> dict[DownloadState, set[DownloadState]]:
    result: dict[DownloadState, set[DownloadState]] = {}
    for state in DownloadState:
        edges = set(_BASE_TRANSITIONS.get(state, ()))
        if state not in _TERMINAL_STATES:
            edges |= _AUTO_TERMINALS
        result[state] = edges
    for terminal in _TERMINAL_STATES:
        result[terminal] = set()
    return result


class DownloadJobState(BaseModel):
    """Pydantic v2 model mirroring the checkpoint atomic-write convention."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    job_id: str
    state: DownloadState = DownloadState.CREATED
    error_category: ErrorCategory | None = None
    attempt_id: int = 0
    backend: str | None = None
    stream_variant_id: str | None = None
    quality_requested: str | None = None
    verified_segments: int = 0
    expected_segments: int | None = None
    verified_bytes: int = 0
    network_bytes_this_session: int = 0
    fragment_done: int | None = None
    fragment_total: int | None = None
    refresh_count: int = 0
    refresh_cap: int = REFRESH_CAP
    ytdlp_internal_retries: int = YTDLP_INTERNAL_RETRIES
    combined_retry_budget: int = COMBINED_RETRY_BUDGET
    retries_used: int = 0
    reason_code: str | None = None
    last_error_code: str | None = None
    retry_in_seconds: float | None = None
    http_status: int | None = None
    host: str | None = None
    path: str | None = None
    resume_bytes: int | None = None
    elapsed_seconds: float | None = None
    disk_full: bool = False
    cancelled: bool = False
    slow_throughput_observed: bool = False
    playlist_reverified: bool = False
    preserve_artifacts: bool = True
    created_at: str | None = None
    updated_at: str | None = None

    # Internal observation window (not persisted as a hard contract but harmless).
    _slow_samples: list[tuple[float, float]] = []

    def model_post_init(self, __context: object) -> None:  # noqa: D401
        if self.created_at is None:
            self.created_at = datetime.now(UTC).isoformat()
        if self.updated_at is None:
            self.updated_at = self.created_at


class DownloadStateMachine:
    """Owns transitions, budget, refresh cap, classification and persistence."""

    _TRANSITIONS: dict[DownloadState, set[DownloadState]] = _build_transitions()

    def __init__(
        self,
        job_state: DownloadJobState | dict[str, object],
        workspace: DownloadWorkspace | None = None,
        logger: _Logger | None = None,
    ) -> None:
        if isinstance(job_state, dict):
            job_state = DownloadJobState.model_validate(job_state)
        self.job_state: DownloadJobState = job_state
        self.workspace = workspace
        from structlog import get_logger as _get

        self.logger = logger if logger is not None else _get(__name__)
        self._slow_samples: list[tuple[float, float]] = []

    # ------------------------------------------------------------------ #
    # Construction
    # ------------------------------------------------------------------ #
    @classmethod
    def create(
        cls,
        *,
        job_id: str,
        quality_requested: str | None = None,
        workspace: DownloadWorkspace | None = None,
        attempt_id: int = 0,
        backend: str | None = None,
        stream_variant_id: str | None = None,
        **kwargs: object,
    ) -> DownloadStateMachine:
        job_state = DownloadJobState(
            job_id=job_id,
            quality_requested=quality_requested,
            attempt_id=attempt_id,
            backend=backend,
            stream_variant_id=stream_variant_id,
            **{k: v for k, v in kwargs.items() if k in DownloadJobState.model_fields},  # type: ignore[arg-type]
        )
        sm = cls(job_state, workspace=workspace)
        if workspace is not None:
            try:
                sm.persist()
            except Exception:  # noqa: BLE001
                pass
        return sm

    @classmethod
    def load(cls, workspace: DownloadWorkspace | None) -> DownloadStateMachine:
        if workspace is None:
            return cls(DownloadJobState(job_id="unknown"), workspace=None)
        path = Path(workspace.state_path)
        job_id = getattr(getattr(workspace, "root", None), "name", None) or "unknown"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                job_state = DownloadJobState.model_validate(data)
                return cls(job_state, workspace=workspace)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "corrupt_state_file",
                    path=str(path),
                    error=str(exc),
                )
                corrupt = path.with_name(path.name + ".corrupt")
                counter = 1
                while corrupt.exists():
                    corrupt = path.with_name(f"{path.name}.corrupt.{counter}")
                    counter += 1
                try:
                    path.rename(corrupt)
                except OSError:  # noqa: BLE001
                    pass
                job_state = DownloadJobState(job_id=job_id)
                sm = cls(job_state, workspace=workspace)
                try:
                    sm.persist()
                except Exception:  # noqa: BLE001
                    pass
                return sm
        job_state = DownloadJobState(job_id=job_id)
        return cls(job_state, workspace=workspace)

    # ------------------------------------------------------------------ #
    # State access
    # ------------------------------------------------------------------ #
    @property
    def state(self) -> DownloadState:
        return self.job_state.state

    def can_transition(self, new_state: DownloadState) -> bool:
        try:
            new_state = DownloadState(str(new_state))
        except Exception:  # noqa: BLE001
            return False
        current = self.job_state.state
        return new_state in self._TRANSITIONS.get(current, set())

    def transition(
        self,
        new_state: object,
        *,
        reason_code: str | None = None,
        error_category: ErrorCategory | str | None = None,
        persist: bool = True,
    ) -> None:
        new_state = DownloadState(str(new_state))
        if not self.can_transition(new_state):
            raise ValueError(f"invalid transition {self.job_state.state} -> {new_state}")
        self.job_state.state = new_state
        if reason_code is not None:
            self.job_state.reason_code = reason_code
        if error_category is not None:
            self.job_state.error_category = (
                ErrorCategory(error_category)
                if not isinstance(error_category, ErrorCategory)
                else error_category
            )
        self.job_state.updated_at = datetime.now(UTC).isoformat()
        if persist and self.workspace is not None:
            self.persist()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def persist(self) -> None:
        if self.workspace is None:
            return
        write_state_atomic(self.workspace.state_path, self.job_state)

    # ------------------------------------------------------------------ #
    # Classification
    # ------------------------------------------------------------------ #
    def classify_error(self, error: object, *, http_status: int | None = None) -> ErrorCategory:
        # Cancelled
        if isinstance(error, (asyncio.CancelledError,)):
            self.job_state.cancelled = True
            return ErrorCategory.CANCELLED
        # Timeout
        if isinstance(error, TimeoutError):
            return ErrorCategory.CONNECTION_TIMEOUT
        # Connection reset
        if isinstance(error, ConnectionResetError):
            return ErrorCategory.CONNECTION_RESET

        # http status from error if not provided
        if http_status is None:
            for attr in ("status", "status_code", "http_status"):
                val = getattr(error, attr, None)
                if isinstance(val, int):
                    http_status = val
                    break

        if http_status is not None:
            if http_status in (401, 403, 410):
                return ErrorCategory.AUTH_EXPIRED
            if http_status == 429:
                return ErrorCategory.RATE_LIMITED
            if http_status == 404:
                self.job_state.playlist_reverified = True
                return ErrorCategory.NOT_FOUND
            if 500 <= http_status < 600:
                return ErrorCategory.SERVER_ERROR
            if http_status == 408:
                return ErrorCategory.CONNECTION_TIMEOUT

        # OSError handling
        import errno as _errno

        if isinstance(error, OSError):
            code = getattr(error, "errno", None)
            msg = str(error).lower()
            if code == _errno.ENOSPC or "no space left" in msg or "enospc" in msg:
                self.job_state.disk_full = True
                return ErrorCategory.DISK_FULL
            if code in (_errno.EACCES, _errno.EPERM) or "permission denied" in msg:
                return ErrorCategory.PERMISSION_ERROR
            if "invalid output path" in msg or "invalid path" in msg:
                return ErrorCategory.INVALID_OUTPUT_PATH

        msg = str(error).lower() if error is not None else ""
        if "no space left" in msg:
            self.job_state.disk_full = True
            return ErrorCategory.DISK_FULL
        if "permission denied" in msg:
            return ErrorCategory.PERMISSION_ERROR
        if "cancelled" in msg:
            self.job_state.cancelled = True
            return ErrorCategory.CANCELLED
        if "playlist" in msg and "incompatible" in msg:
            return ErrorCategory.INCOMPATIBLE_PLAYLIST
        if "codec" in msg and "incompatible" in msg:
            return ErrorCategory.INCOMPATIBLE_CODEC
        if "integrity" in msg:
            return ErrorCategory.INTEGRITY_FAILURE
        if "slow" in msg:
            return ErrorCategory.SLOW_THROUGHPUT
        if "timeout" in msg:
            return ErrorCategory.CONNECTION_TIMEOUT
        if "connection reset" in msg or "reset by peer" in msg:
            return ErrorCategory.CONNECTION_RESET
        return ErrorCategory.UNKNOWN

    # ------------------------------------------------------------------ #
    # Retry budget
    # ------------------------------------------------------------------ #
    def is_budget_exhausted(self) -> bool:
        return self.job_state.retries_used >= self.job_state.combined_retry_budget

    def record_retry(
        self,
        scope: str,
        reason_code: str,
        delay_seconds: float,
        *,
        http_status: int | None = None,
    ) -> bool:
        if self.is_budget_exhausted():
            try:
                if self.can_transition(DownloadState.FAILED_RETRY_BUDGET):
                    self.transition(
                        DownloadState.FAILED_RETRY_BUDGET,
                        reason_code="retry_budget_exhausted",
                        error_category=ErrorCategory.UNKNOWN,
                        persist=True,
                    )
                else:
                    self.persist()
            except Exception:  # noqa: BLE001
                pass
            return False
        self.job_state.retries_used += 1
        self.job_state.reason_code = reason_code
        self.job_state.retry_in_seconds = delay_seconds
        if http_status is not None:
            self.job_state.http_status = http_status
        try:
            self.logger.info(
                "retry_scheduled",
                job_id=self.job_state.job_id,
                attempt_id=self.job_state.attempt_id,
                scope=scope,
                reason_code=reason_code,
                delay_seconds=delay_seconds,
                retry_in_seconds=delay_seconds,
            )
        except Exception:  # noqa: BLE001
            pass
        if self.workspace is not None:
            self.persist()
        return True

    # ------------------------------------------------------------------ #
    # Refresh
    # ------------------------------------------------------------------ #
    def request_refresh(self, reason_code: str) -> bool:
        if self.job_state.refresh_count >= self.job_state.refresh_cap:
            if self.workspace is not None:
                self.persist()
            return False
        self.job_state.refresh_count += 1
        self.job_state.reason_code = reason_code
        try:
            self.logger.info(
                "refresh_requested",
                job_id=self.job_state.job_id,
                attempt_id=self.job_state.attempt_id,
                reason_code=reason_code,
            )
        except Exception:  # noqa: BLE001
            pass
        if self.workspace is not None:
            self.persist()
        return True

    def record_refresh_completed(self, *, quality_match: bool, variant_match: bool) -> None:
        try:
            self.logger.info(
                "refresh_completed",
                job_id=self.job_state.job_id,
                attempt_id=self.job_state.attempt_id,
                quality_match=quality_match,
                variant_match=variant_match,
            )
        except Exception:  # noqa: BLE001
            pass
        if self.workspace is not None:
            self.persist()

    # ------------------------------------------------------------------ #
    # Cancellation / disk full
    # ------------------------------------------------------------------ #
    def record_cancellation(self) -> None:
        self.job_state.cancelled = True
        if self.can_transition(DownloadState.CANCELLED):
            try:
                self.transition(
                    DownloadState.CANCELLED,
                    reason_code="cancelled",
                    error_category=ErrorCategory.CANCELLED,
                    persist=True,
                )
            except Exception:  # noqa: BLE001
                if self.workspace is not None:
                    self.persist()
        else:
            if self.workspace is not None:
                self.persist()

    def record_disk_full(self) -> None:
        self.job_state.disk_full = True
        if self.can_transition(DownloadState.DISK_FULL):
            try:
                self.transition(
                    DownloadState.DISK_FULL,
                    reason_code="disk_full",
                    error_category=ErrorCategory.DISK_FULL,
                    persist=True,
                )
            except Exception:  # noqa: BLE001
                if self.workspace is not None:
                    self.persist()
        else:
            if self.workspace is not None:
                self.persist()

    # ------------------------------------------------------------------ #
    # Throughput observation
    # ------------------------------------------------------------------ #
    def observe_throughput(self, rate_bytes_per_sec: float, *, now: float | None = None) -> bool:
        if now is None:
            import time as _t

            now = _t.monotonic()
        self._slow_samples.append((float(now), float(rate_bytes_per_sec)))
        # prune older than 10s window
        cutoff = float(now) - 10.0
        self._slow_samples = [s for s in self._slow_samples if s[0] >= cutoff]
        threshold = 1024.0
        slow = [s for s in self._slow_samples if s[1] < threshold]
        if len(self._slow_samples) < 2:
            return False
        if len(slow) != len(self._slow_samples):
            return False
        span = self._slow_samples[-1][0] - self._slow_samples[0][0]
        if span < 5.0:
            return False
        self.job_state.slow_throughput_observed = True
        if self.workspace is not None:
            self.persist()
        return True

    # ------------------------------------------------------------------ #
    # 404 re-verification
    # ------------------------------------------------------------------ #
    def reverify_playlist_on_404(self) -> None:
        self.job_state.playlist_reverified = True
        if self.workspace is not None:
            self.persist()

    # ------------------------------------------------------------------ #
    # Counters helpers (Block I)
    # ------------------------------------------------------------------ #
    def increment_verified_segment(self, bytes_count: int = 0) -> None:
        self.job_state.verified_segments += 1
        self.job_state.verified_bytes += int(bytes_count)
        if self.workspace is not None:
            self.persist()

    def set_network_bytes(self, value: int) -> None:
        self.job_state.network_bytes_this_session = int(value)
        if self.workspace is not None:
            self.persist()

    def set_fragment_progress(self, done: int | None, total: int | None) -> None:
        self.job_state.fragment_done = done
        self.job_state.fragment_total = total
        if self.workspace is not None:
            self.persist()

    def increment_attempt_id(self) -> int:
        self.job_state.attempt_id += 1
        return self.job_state.attempt_id
