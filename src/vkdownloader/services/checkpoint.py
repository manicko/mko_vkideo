"""Durable per-segment checkpoint helpers for HLS downloads."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from structlog import get_logger

logger = get_logger(__name__)

CHECKPOINT_SCHEMA_VERSION = 1


class SegmentRecord(BaseModel):
    """Content identity for a single persisted segment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=0)
    relative_file: str
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_seconds: float | None = None
    byte_range: str | None = None
    discontinuity_sequence: int = 0
    media_sequence: int | None = None
    init_map_sha256: str | None = None
    key_method: str | None = None
    key_id: str | None = None
    generation_id: str


class JobCheckpoint(BaseModel):
    """Versioned checkpoint for one download job."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = CHECKPOINT_SCHEMA_VERSION
    video_id: str
    quality_requested: str
    stream_variant_id: str
    playlist_fingerprint: str
    generation_id: str = "gen-0"
    media_sequence: int | None = None
    discontinuity_sequence: int = 0
    init_map_identity: str | None = None
    codecs: str | None = None
    resolution: str | None = None
    is_live: bool = False
    endlist: bool = False
    segments: dict[str, SegmentRecord] = Field(default_factory=dict)
    updated_at: str | None = None

    @model_validator(mode="after")
    def _unique_sequences(self) -> JobCheckpoint:
        sequences = [record.sequence for record in self.segments.values()]
        if len(set(sequences)) != len(sequences):
            raise ValueError("duplicate segment sequence in checkpoint")
        return self


def streaming_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    """Hash a file in fixed-size chunks without loading it fully."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def confine_relative_path(relative: str | Path, segments_dir: str | Path) -> Path:
    """Resolve *relative* inside *segments_dir* and reject traversal/escape."""
    text = str(relative)
    if "\x00" in text or "\\" in text:
        raise ValueError("unsafe relative path")
    candidate = Path(text)
    if candidate.is_absolute() or candidate.drive:
        raise ValueError("absolute or drive-qualified relative path")
    if any(part in ("", ".", "..") for part in candidate.parts):
        # allow "."? reject ".." only; "." harmless but normalize
        if any(part == ".." for part in candidate.parts):
            raise ValueError("path traversal in relative path")
    # reject any ".." component explicitly
    if ".." in candidate.parts:
        raise ValueError("path traversal in relative path")

    base = Path(segments_dir).resolve(strict=False)
    target = (base / candidate).resolve(strict=False)
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError("relative path escapes segments directory") from exc
    if target == base:
        raise ValueError("empty relative path")
    return target


validate_relative_file = confine_relative_path


def _coerce_checkpoint(payload: Any) -> JobCheckpoint | None:
    if isinstance(payload, JobCheckpoint):
        return payload
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict):
        return None
    return JobCheckpoint.model_validate(payload)


def read_checkpoint(
    path: str | Path,
    segments_dir: str | Path | None = None,
    *,
    schema_version: int = CHECKPOINT_SCHEMA_VERSION,
) -> JobCheckpoint | None:
    """Load and validate a checkpoint, returning None on any failure."""
    path = Path(path)
    base_dir = Path(segments_dir) if segments_dir is not None else path.parent
    try:
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if data.get("schema_version") != schema_version:
            return None
        checkpoint = JobCheckpoint.model_validate(data)
        if checkpoint.schema_version != schema_version:
            return None
        for record in checkpoint.segments.values():
            confine_relative_path(record.relative_file, base_dir)
        return checkpoint
    except OSError, ValueError, ValidationError, json.JSONDecodeError, TypeError:
        logger.warning("checkpoint_load_failed", path=str(path))
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("checkpoint_load_failed", path=str(path), error=str(exc))
        return None


load_checkpoint = read_checkpoint


def write_state_atomic(path: str | Path, payload: Any) -> None:
    """Atomically write *payload* as JSON to *path*."""
    write_checkpoint_atomic(path, payload)


def write_checkpoint_atomic(path: str | Path, payload: Any) -> None:
    """Atomically write *payload* as JSON to *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(payload, JobCheckpoint):
        data = payload.model_dump(mode="json")
    elif hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")
    elif hasattr(payload, "dict"):
        data = payload.dict()
    else:
        data = payload

    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, sort_keys=True, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    # Best-effort parent directory fsync (limited on Windows).
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError, AttributeError, ValueError:
        pass


def verify_segment_record(record: SegmentRecord, segments_dir: str | Path) -> bool:
    """Verify a segment record against the file on disk."""
    try:
        if not isinstance(record, SegmentRecord):
            # allow dict-like? attempt coercion
            record = SegmentRecord.model_validate(record)
        relative = str(record.relative_file)
        if relative.endswith(".tmp"):
            return False
        if record.size <= 0:
            return False
        target = confine_relative_path(relative, segments_dir)
        if not target.is_file():
            return False
        if target.stat().st_size != record.size:
            return False
        actual = streaming_sha256(target)
        return actual == record.sha256
    except Exception:  # noqa: BLE001
        return False


def verify_checkpoint(
    checkpoint: JobCheckpoint,
    *args: Any,
    stream_variant_id: str | None = None,
    playlist_fingerprint: str | None = None,
    init_map_identity: str | None = None,
    media_sequence: int | None = None,
    discontinuity_sequence: int | None = None,
    generation_id: str | None = None,
    video_id: str | None = None,
    quality_requested: str | None = None,
    **kwargs: Any,
) -> bool:
    """Return True if checkpoint matches the supplied identity fields."""
    try:
        if not isinstance(checkpoint, JobCheckpoint):
            checkpoint = JobCheckpoint.model_validate(checkpoint)

        # positional convenience: variant, fingerprint
        if args:
            if isinstance(args[0], str) and stream_variant_id is None:
                stream_variant_id = args[0]
            if len(args) > 1 and isinstance(args[1], str) and playlist_fingerprint is None:
                playlist_fingerprint = args[1]
            if len(args) > 2 and isinstance(args[2], str) and init_map_identity is None:
                init_map_identity = args[2]

        # kwargs aliases
        if stream_variant_id is None:
            stream_variant_id = kwargs.get("variant_id") or kwargs.get("stream_variant_id")
        if playlist_fingerprint is None:
            playlist_fingerprint = kwargs.get("fingerprint") or kwargs.get("playlist_fingerprint")
        if init_map_identity is None:
            init_map_identity = kwargs.get("init_map_identity")

        if checkpoint.schema_version != CHECKPOINT_SCHEMA_VERSION:
            return False
        if stream_variant_id is not None and checkpoint.stream_variant_id != stream_variant_id:
            return False
        if (
            playlist_fingerprint is not None
            and checkpoint.playlist_fingerprint != playlist_fingerprint
        ):
            return False
        if init_map_identity is not None and checkpoint.init_map_identity != init_map_identity:
            return False
        if media_sequence is not None and checkpoint.media_sequence != media_sequence:
            return False
        if (
            discontinuity_sequence is not None
            and checkpoint.discontinuity_sequence != discontinuity_sequence
        ):
            return False
        if generation_id is not None and checkpoint.generation_id != generation_id:
            return False
        if video_id is not None and checkpoint.video_id != video_id:
            return False
        if quality_requested is not None and checkpoint.quality_requested != quality_requested:
            return False
        return True
    except Exception:  # noqa: BLE001
        return False


def _sanitize_generation_id(generation_id: Any) -> str:
    """Return a single safe path component for *generation_id*.

    Rejects separators, ``.``, ``..``, empty values, and NUL bytes, falling
    back to ``"gen"`` when the value is unsafe.
    """
    text = str(generation_id or "gen")
    if not text or "\x00" in text:
        return "gen"
    if text in (".", ".."):
        return "gen"
    if "/" in text or "\\" in text:
        return "gen"
    try:
        import os as _os

        if _os.sep in text or (_os.altsep and _os.altsep in text):
            return "gen"
    except Exception:  # noqa: BLE001
        pass
    from pathlib import Path as _Path

    if _Path(text).parts != (text,):
        return "gen"
    return text


def quarantine_generation(
    segments_dir: str | Path,
    generation_id: str | None = None,
    checkpoint: JobCheckpoint | None = None,
    *args: Any,
    **kwargs: Any,
) -> Path:
    """Rename *segments_dir* to a quarantine sibling and recreate it.

    The quarantine target directory is created only when there is something to
    move; an absent ``segments_dir`` does not leave an empty generation
    directory behind.
    """
    segments_dir = Path(segments_dir)
    if generation_id is None and checkpoint is not None:
        generation_id = getattr(checkpoint, "generation_id", None)
    if generation_id is None and args:
        if isinstance(args[0], str):
            generation_id = args[0]
        elif isinstance(args[0], JobCheckpoint):
            generation_id = getattr(args[0], "generation_id", None)
    if generation_id is None:
        generation_id = kwargs.get("generation_id")

    gen = _sanitize_generation_id(generation_id)

    parent = segments_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    quarantine_root = parent / "generations"

    target = quarantine_root / gen
    if segments_dir.exists():
        quarantine_root.mkdir(parents=True, exist_ok=True)
        if target.exists():
            index = 1
            while (quarantine_root / f"{gen}-{index}").exists():
                index += 1
            target = quarantine_root / f"{gen}-{index}"
        segments_dir.rename(target)

    segments_dir.mkdir(parents=True, exist_ok=True)
    return target


def upsert_segment_record(
    *args: Any,
    state_path: str | Path | None = None,
    segments_dir: str | Path | None = None,
    write: bool = False,
    checkpoint: JobCheckpoint | None = None,
    record: SegmentRecord | None = None,
    key: str | int | None = None,
    **kwargs: Any,
) -> JobCheckpoint:
    """Insert or replace a segment record in a checkpoint."""
    # Resolve positional arguments flexibly.
    positional_checkpoint: JobCheckpoint | None = None
    positional_record: SegmentRecord | None = None
    positional_key: str | int | None = None
    positional_state_path: str | Path | None = None

    for arg in args:
        if isinstance(arg, JobCheckpoint):
            positional_checkpoint = arg
        elif isinstance(arg, SegmentRecord):
            positional_record = arg
        elif isinstance(arg, Path):
            positional_state_path = arg
        elif isinstance(arg, str):
            if arg.endswith(".json") or arg.endswith(".tmp") or "/" in arg or "\\" in arg:
                positional_state_path = arg
            else:
                positional_key = arg
        elif isinstance(arg, int):
            positional_key = arg

    if checkpoint is None:
        checkpoint = positional_checkpoint
    if record is None:
        record = positional_record
    if key is None:
        key = positional_key
    if state_path is None:
        state_path = positional_state_path

    if checkpoint is None and "checkpoint" in kwargs:
        checkpoint = kwargs.pop("checkpoint")
    if record is None and "record" in kwargs:
        record = kwargs.pop("record")
    if key is None and "index" in kwargs:
        key = kwargs.pop("index")
    if state_path is None and "path" in kwargs:
        state_path = kwargs.pop("path")

    if checkpoint is None:
        raise ValueError("checkpoint is required")
    if record is None:
        raise ValueError("record is required")
    if not isinstance(record, SegmentRecord):
        record = SegmentRecord.model_validate(record)
    if key is None:
        key = record.sequence

    if segments_dir is not None:
        confine_relative_path(record.relative_file, segments_dir)

    checkpoint.segments[str(key)] = record
    checkpoint.updated_at = datetime.now(UTC).isoformat()

    if write and state_path is not None:
        write_checkpoint_atomic(state_path, checkpoint)
    return checkpoint
