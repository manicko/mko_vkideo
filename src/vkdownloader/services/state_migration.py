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
from typing import TYPE_CHECKING, cast

from pydantic import ValidationError
from structlog import get_logger

from .checkpoint import CHECKPOINT_SCHEMA_VERSION, JobCheckpoint, write_checkpoint_atomic
from .state_machine import CommitRecoveryDirective, DownloadJobState, DownloadStateMachine

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


def _safe_transition_state(sm: object, target: object) -> None:
    if sm is None:
        return
    import asyncio

    try:
        if hasattr(sm, "can_transition") and sm.can_transition(target):
            from typing import cast

            cast("DownloadStateMachine", sm).transition(target)
        else:
            try:
                from structlog import get_logger

                get_logger(__name__).debug(
                    "transition_skipped", current=getattr(sm, "state", None), target=str(target)
                )
            except Exception:  # noqa: BLE001
                pass
    except asyncio.CancelledError, KeyboardInterrupt:
        raise
    except Exception:  # noqa: BLE001
        pass


def ensure_download_phase_state(sm: object) -> None:
    if sm is None:
        return
    import asyncio

    try:
        from ..models.enums import DownloadState

        for target in (
            DownloadState.RESOLVE_STREAM,
            DownloadState.VALIDATE_VARIANT,
            DownloadState.DOWNLOAD,
        ):
            if hasattr(sm, "can_transition") and sm.can_transition(target):
                cast(DownloadStateMachine, sm).transition(target)
    except asyncio.CancelledError, KeyboardInterrupt:
        raise
    except Exception:  # noqa: BLE001
        pass


def _identity_matches(
    state_machine: object,
    expected_generation: object,
    expected_variant: object,
    expected_fingerprint: object,
    expected_init: object,
) -> bool:
    """Return True only when provided persisted identity fields match."""
    if state_machine is None:
        return False
    try:
        sm_state = getattr(state_machine, "job_state", None)
    except Exception:  # noqa: BLE001
        return False
    if sm_state is None:
        return False
    try:
        persisted_generation = getattr(sm_state, "artifact_generation", None)
        persisted_variant = getattr(sm_state, "artifact_stream_variant_id", None)
        if persisted_variant is None:
            persisted_variant = getattr(sm_state, "stream_variant_id", None)
        persisted_fp = getattr(sm_state, "artifact_playlist_fingerprint", None)
        persisted_init = getattr(sm_state, "artifact_init_map_sha256", None)
    except Exception:  # noqa: BLE001
        return False

    provided = False
    pairs = (
        (expected_generation, persisted_generation),
        (expected_variant, persisted_variant),
        (expected_fingerprint, persisted_fp),
        (expected_init, persisted_init),
    )
    for expected, persisted in pairs:
        if expected is None:
            continue
        provided = True
        if persisted is None or expected != persisted:
            return False
    return provided


async def reconcile_commit_state(
    workspace: DownloadWorkspace,
    state_machine: DownloadStateMachine | None = None,
    *,
    expected_height: int | None = None,
) -> tuple[CommitRecoveryDirective, Path | None]:
    """Classify on-disk commit state for *workspace*; never delete bytes."""
    import asyncio
    from pathlib import Path

    from .ffmpeg_utils import check_ffprobe_available

    final_path = Path(workspace.final_path)
    staging_dir = Path(workspace.staging_dir)
    segments_dir = Path(workspace.segments_dir)
    staging_path = staging_dir / final_path.name

    sm = state_machine

    # 1. Already committed final.
    if final_path.exists() and final_path.is_file() and final_path.stat().st_size > 0:
        ffprobe_ok = False
        try:
            ffprobe_ok = check_ffprobe_available()
        except Exception:  # noqa: BLE001
            ffprobe_ok = False
        if not ffprobe_ok:
            try:
                from structlog import get_logger

                get_logger(__name__).error("ffprobe_missing", path=str(final_path))
            except Exception:  # noqa: BLE001
                pass
        else:
            try:
                from .media_validation import validate_media_file

                expected_duration = None
                if sm is not None:
                    try:
                        expected_duration = getattr(sm.job_state, "artifact_expected_duration_seconds", None)
                    except Exception:  # noqa: BLE001
                        expected_duration = None
                await validate_media_file(
                    final_path, expected_height=expected_height, expected_duration=expected_duration
                )
                # Identity verification: only treat as committed when identity is proven.
                identity_ok = False
                if sm is not None:
                    try:
                        js = sm.job_state
                        identity_ok = _identity_matches(
                            sm,
                            getattr(js, "artifact_generation", None),
                            getattr(js, "artifact_stream_variant_id", None)
                            or getattr(js, "stream_variant_id", None),
                            getattr(js, "artifact_playlist_fingerprint", None),
                            getattr(js, "artifact_init_map_sha256", None),
                        )
                    except Exception:  # noqa: BLE001
                        identity_ok = False
                if not identity_ok:
                    if sm is not None:
                        try:
                            sm.job_state.reason_code = "destination_conflict"
                            sm.persist()
                        except Exception:  # noqa: BLE001
                            pass
                    return CommitRecoveryDirective.DESTINATION_CONFLICT, None
                # Advance state to FINAL_COMMITTED when possible.
                ensure_download_phase_state(sm)
                from ..models.enums import DownloadState

                for target in (
                    DownloadState.ALL_SEGMENTS_VERIFIED,
                    DownloadState.MERGING_IN_STAGING,
                    DownloadState.CANDIDATE_READY,
                    DownloadState.VALIDATING,
                    DownloadState.VALIDATED,
                    DownloadState.ATOMIC_NO_CLOBBER_PUBLICATION,
                    DownloadState.FINAL_COMMITTED,
                ):
                    _safe_transition_state(sm, target)
                if sm is not None and hasattr(sm, "persist"):
                    try:
                        sm.persist()
                    except Exception:  # noqa: BLE001
                        pass
                return CommitRecoveryDirective.ALREADY_COMMITTED, final_path
            except asyncio.CancelledError, KeyboardInterrupt:
                raise
            except Exception:  # noqa: BLE001
                pass

    # 2. Validated staging candidate.
    if staging_path.exists() and staging_path.is_file() and staging_path.stat().st_size > 0:
        ffprobe_ok = False
        try:
            ffprobe_ok = check_ffprobe_available()
        except Exception:  # noqa: BLE001
            ffprobe_ok = False
        if not ffprobe_ok:
            try:
                from structlog import get_logger

                get_logger(__name__).error("ffprobe_missing", path=str(staging_path))
            except Exception:  # noqa: BLE001
                pass
        else:
            try:
                from .media_validation import validate_media_file

                expected_duration = None
                if sm is not None:
                    try:
                        expected_duration = getattr(sm.job_state, "artifact_expected_duration_seconds", None)
                    except Exception:  # noqa: BLE001
                        expected_duration = None
                await validate_media_file(
                    staging_path, expected_height=expected_height, expected_duration=expected_duration
                )
                # Identity verification.
                identity_ok = False
                if sm is not None:
                    try:
                        js = sm.job_state
                        identity_ok = _identity_matches(
                            sm,
                            getattr(js, "artifact_generation", None),
                            getattr(js, "artifact_stream_variant_id", None)
                            or getattr(js, "stream_variant_id", None),
                            getattr(js, "artifact_playlist_fingerprint", None),
                            getattr(js, "artifact_init_map_sha256", None),
                        )
                    except Exception:  # noqa: BLE001
                        identity_ok = False
                if not identity_ok:
                    if sm is not None:
                        try:
                            sm.job_state.reason_code = "destination_conflict"
                            sm.persist()
                        except Exception:  # noqa: BLE001
                            pass
                    return CommitRecoveryDirective.DESTINATION_CONFLICT, None
                ensure_download_phase_state(sm)
                from ..models.enums import DownloadState

                for target in (
                    DownloadState.ALL_SEGMENTS_VERIFIED,
                    DownloadState.MERGING_IN_STAGING,
                    DownloadState.CANDIDATE_READY,
                    DownloadState.VALIDATING,
                    DownloadState.VALIDATED,
                ):
                    _safe_transition_state(sm, target)
                if sm is not None and hasattr(sm, "persist"):
                    try:
                        sm.persist()
                    except Exception:  # noqa: BLE001
                        pass
                return CommitRecoveryDirective.PUBLISH_STAGING, staging_path
            except asyncio.CancelledError, KeyboardInterrupt:
                raise
            except Exception:  # noqa: BLE001
                pass

    # 3. Preserved segments.
    if segments_dir.exists():
        try:
            if any(segments_dir.glob("*.ts")):
                ensure_download_phase_state(sm)
                from ..models.enums import DownloadState

                # Walk at least to DOWNLOAD if legal.
                _safe_transition_state(sm, DownloadState.DOWNLOAD)
                if sm is not None and hasattr(sm, "persist"):
                    try:
                        sm.persist()
                    except Exception:  # noqa: BLE001
                        pass
                return CommitRecoveryDirective.RESUME_SEGMENTS, None
        except asyncio.CancelledError, KeyboardInterrupt:
            raise
        except Exception:  # noqa: BLE001
            pass

    # 4. Fresh.
    if sm is not None and hasattr(sm, "persist"):
        try:
            sm.persist()
        except Exception:  # noqa: BLE001
            pass
    return CommitRecoveryDirective.FRESH, None


__all__ = [
    "LegacyStateClassification",
    "MigrationResult",
    "CommitRecoveryDirective",
    "classify_legacy_state",
    "migrate_legacy_state",
    "preserve_bytes",
    "try_parse_checkpoint",
    "try_parse_job_state",
    "reconcile_commit_state",
    "_identity_matches",
]
