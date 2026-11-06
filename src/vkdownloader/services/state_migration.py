"""Central, idempotent migration from legacy state.json to split v2 owners.

This module classifies legacy ``state.json`` bytes, preserves corrupt or
ambiguous payloads under a dated recovery root, and performs a crash-recoverable
migration into ``job_state.v2.json`` (job state owner) and
``segment_checkpoint.v2.json`` (HLS checkpoint owner). Legacy ``state.json`` is
never deleted or modified by this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError
from structlog import get_logger

from .checkpoint import CHECKPOINT_SCHEMA_VERSION, JobCheckpoint, write_checkpoint_atomic
from .state_machine import DownloadJobState

logger = get_logger(__name__)


class LegacyStateClassification(StrEnum):
    ABSENT = "absent"
    JOB_STATE = "job_state"
    CHECKPOINT = "checkpoint"
    AMBIGUOUS = "ambiguous"
    CORRUPT = "corrupt"


class MigrationResult(StrEnum):
    NOT_NEEDED = "not_needed"
    ALREADY_MIGRATED = "already_migrated"
    MIGRATED_JOB_STATE = "migrated_job_state"
    MIGRATED_CHECKPOINT = "migrated_checkpoint"
    MIGRATED_BOTH = "migrated_both"
    PRESERVED = "preserved"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    FAILED = "failed"


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def try_parse_job_state(raw: bytes | str | bytearray | None) -> DownloadJobState | None:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        text = bytes(raw).decode("utf-8", errors="replace")
    else:
        text = str(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError, ValueError, TypeError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return DownloadJobState.model_validate(data)
    except ValidationError, ValueError, TypeError:
        return None


def try_parse_checkpoint(raw: bytes | str | bytearray | None) -> JobCheckpoint | None:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        text = bytes(raw).decode("utf-8", errors="replace")
    else:
        text = str(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError, ValueError, TypeError:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        return None
    try:
        checkpoint = JobCheckpoint.model_validate(data)
    except ValidationError, ValueError, TypeError:
        return None
    if checkpoint.schema_version != CHECKPOINT_SCHEMA_VERSION:
        return None
    return checkpoint


def classify_legacy_state(raw: bytes | str | bytearray | None) -> LegacyStateClassification:
    if raw is None:
        return LegacyStateClassification.ABSENT
    # Empty bytes => absent-ish but treat as corrupt? Keep absent for no file handled by caller.
    if isinstance(raw, (bytes, bytearray)) and len(raw) == 0:
        return LegacyStateClassification.ABSENT
    job_state = try_parse_job_state(raw)
    checkpoint = try_parse_checkpoint(raw)
    if job_state is not None and checkpoint is not None:
        return LegacyStateClassification.AMBIGUOUS
    if job_state is not None:
        return LegacyStateClassification.JOB_STATE
    if checkpoint is not None:
        return LegacyStateClassification.CHECKPOINT
    # Exists but not parseable.
    text = (
        raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    )
    try:
        data = json.loads(text)
    except json.JSONDecodeError, ValueError, TypeError:
        return LegacyStateClassification.CORRUPT
    if not isinstance(data, dict):
        return LegacyStateClassification.CORRUPT
    return LegacyStateClassification.AMBIGUOUS


def preserve_bytes(source: Path | str, recovery_dir: Path | str) -> Path | None:
    """Copy *source* bytes into *recovery_dir*, verifying size and hash."""
    source = Path(source)
    recovery_dir = Path(recovery_dir)
    if not source.exists() or not source.is_file():
        return None
    recovery_dir.mkdir(parents=True, exist_ok=True)
    src_size = source.stat().st_size
    src_hash = _file_hash(source)

    # Idempotent: reuse an existing identical copy.
    for candidate in recovery_dir.iterdir():
        if not candidate.is_file():
            continue
        try:
            if candidate.stat().st_size == src_size and _file_hash(candidate) == src_hash:
                return candidate
        except OSError:
            continue

    dest = recovery_dir / source.name
    if dest.exists():
        counter = 1
        while True:
            candidate = recovery_dir / f"{source.name}.{counter}"
            if not candidate.exists():
                dest = candidate
                break
            counter += 1
    shutil.copy2(source, dest)
    if dest.stat().st_size != src_size or _file_hash(dest) != src_hash:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError("preserve_bytes verification failed")
    return dest


def _timestamp_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    base = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = root / base
    counter = 1
    while candidate.exists():
        candidate = root / f"{base}.{counter}"
        counter += 1
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _valid_job_state(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        raw = path.read_bytes()
        return try_parse_job_state(raw) is not None
    except OSError:
        return False


def _valid_checkpoint(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        raw = path.read_bytes()
        return try_parse_checkpoint(raw) is not None
    except OSError:
        return False


def _atomic_write(path: Path, payload: object) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, DownloadJobState):
        write_checkpoint_atomic(path, payload)
    elif isinstance(payload, JobCheckpoint):
        write_checkpoint_atomic(path, payload)
    else:
        # try coerce
        js = try_parse_job_state(
            json.dumps(payload).encode()
            if not isinstance(payload, (str, bytes, bytearray))
            else payload
        )
        if js is not None:
            write_checkpoint_atomic(path, js)
        else:
            cp = try_parse_checkpoint(
                json.dumps(payload).encode()
                if not isinstance(payload, (str, bytes, bytearray))
                else payload
            )
            if cp is not None:
                write_checkpoint_atomic(path, cp)
            else:
                # fallback raw atomic
                tmp = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
                data = (
                    payload if isinstance(payload, (str, bytes, bytearray)) else json.dumps(payload)
                )
                with open(tmp, "w", encoding="utf-8") as handle:
                    handle.write(
                        data if isinstance(data, str) else data.decode("utf-8", errors="replace")
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp, path)


if TYPE_CHECKING:
    from .workspace import DownloadWorkspace


def migrate_legacy_state(
    workspace: DownloadWorkspace,
    *,
    confirm_ambiguous: bool = False,
    recovery_root: object | None = None,
) -> MigrationResult:
    log = logger
    try:
        job_state_path = Path(workspace.job_state_path)
        checkpoint_path = Path(workspace.segment_checkpoint_path)
        legacy_path = Path(workspace.state_path)
        job_id = (
            getattr(workspace, "job_id", None)
            or getattr(workspace, "root", Path()).name
            or "unknown"
        )

        if recovery_root is None:
            tmp = Path(workspace.root).parent.parent  # tmp
            recovery_root = tmp / "recovery" / str(job_id)
        recovery_root = Path(str(recovery_root))

        legacy_exists = legacy_path.exists()
        raw = legacy_path.read_bytes() if legacy_exists else None

        classification = (
            classify_legacy_state(raw) if legacy_exists else LegacyStateClassification.ABSENT
        )
        if not legacy_exists:
            classification = LegacyStateClassification.ABSENT

        v2_job_valid = _valid_job_state(job_state_path)
        v2_ckpt_valid = _valid_checkpoint(checkpoint_path)

        # Already fully migrated for the classified owner.
        if classification == LegacyStateClassification.ABSENT:
            if v2_job_valid and v2_ckpt_valid:
                return MigrationResult.ALREADY_MIGRATED
            return MigrationResult.NOT_NEEDED

        if classification in (
            LegacyStateClassification.AMBIGUOUS,
            LegacyStateClassification.CORRUPT,
        ):
            if legacy_exists:
                dated = _timestamp_dir(recovery_root)
                preserve_bytes(legacy_path, dated)
                # classification marker
                try:
                    (dated / "classification.txt").write_text(
                        classification.value, encoding="utf-8"
                    )
                except OSError:
                    pass
            if not confirm_ambiguous:
                return MigrationResult.REQUIRES_CONFIRMATION
            return MigrationResult.PRESERVED

        # Classified as job_state or checkpoint.
        already = False
        if classification == LegacyStateClassification.JOB_STATE and v2_job_valid:
            already = True
        if (
            classification == LegacyStateClassification.CHECKPOINT
            and v2_ckpt_valid
            and v2_job_valid
        ):
            already = True
        if already and v2_job_valid:
            # idempotent: do not rewrite
            return MigrationResult.ALREADY_MIGRATED

        js = (
            try_parse_job_state(raw)
            if classification == LegacyStateClassification.JOB_STATE
            else None
        )
        cp = (
            try_parse_checkpoint(raw)
            if classification == LegacyStateClassification.CHECKPOINT
            else None
        )

        try:
            if classification == LegacyStateClassification.JOB_STATE:
                if js is not None:
                    js.job_id = str(job_id)
                if not v2_job_valid:
                    _atomic_write(
                        job_state_path,
                        js if js is not None else DownloadJobState(job_id=str(job_id)),
                    )
                # Do not create checkpoint from job state; leave for reconcile.
                return MigrationResult.MIGRATED_JOB_STATE
            else:  # CHECKPOINT
                if cp is not None:
                    if not v2_ckpt_valid:
                        _atomic_write(checkpoint_path, cp)
                else:
                    if not v2_ckpt_valid:
                        _atomic_write(
                            checkpoint_path,
                            JobCheckpoint(
                                schema_version=CHECKPOINT_SCHEMA_VERSION,
                                video_id=getattr(workspace, "job_id", str(job_id)),
                                quality_requested="unknown",
                                stream_variant_id="unknown",
                                playlist_fingerprint="unknown",
                            ),
                        )
                if not v2_job_valid:
                    default_js = DownloadJobState(job_id=str(job_id))
                    _atomic_write(job_state_path, default_js)
                return MigrationResult.MIGRATED_CHECKPOINT
        except Exception as exc:  # noqa: BLE001
            log.warning("migration_failed", error=str(exc))
            # Preserve offending legacy bytes on failure.
            if legacy_exists:
                dated = _timestamp_dir(recovery_root)
                try:
                    preserve_bytes(legacy_path, dated)
                except Exception:  # noqa: BLE001
                    pass
            return MigrationResult.FAILED
    except Exception as exc:  # noqa: BLE001
        logger.warning("migration_failed_outer", error=str(exc))
        return MigrationResult.FAILED


__all__ = [
    "LegacyStateClassification",
    "MigrationResult",
    "classify_legacy_state",
    "migrate_legacy_state",
    "preserve_bytes",
    "try_parse_checkpoint",
    "try_parse_job_state",
]
