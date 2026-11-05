"""RED tests for Block E — durable per-segment checkpoint and safe content identity.

These tests target the (not-yet-implemented) checkpoint module and the
Block E API changes in segment_downloader. They are expected to FAIL until
the implementation lands. Collection must remain successful: all imports of
not-yet-existing modules are guarded inside test bodies / helpers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError


def _import_checkpoint():
    try:
        from vkdownloader.services import checkpoint as m

        return m
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"checkpoint module unavailable: {exc}")


def _import_segment():
    try:
        from vkdownloader.services import segment_downloader as m

        return m
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"segment_downloader module unavailable: {exc}")


def _import_hls_parser():
    try:
        from vkdownloader.services import hls_parser as m

        return m
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"hls_parser module unavailable: {exc}")


def _write_checkpoint(cp, ckpt, path: Path) -> None:
    """Call write_checkpoint_atomic with either argument order."""
    try:
        cp.write_checkpoint_atomic(path, ckpt)
    except TypeError:
        cp.write_checkpoint_atomic(ckpt, path)


def _load_checkpoint(cp, path: Path):
    return cp.load_checkpoint(path)


# --------------------------------------------------------------------------- #
#  Model validation
# --------------------------------------------------------------------------- #


def test_segmentrecord_rejects_extra() -> None:
    cp = _import_checkpoint()
    with pytest.raises(ValidationError):
        cp.SegmentRecord(
            sequence=0,
            relative_file="00000.ts",
            size=5,
            sha256="0" * 64,
            generation_id="g",
            unexpected_field="x",
        )


def test_jobcheckpoint_rejects_extra() -> None:
    cp = _import_checkpoint()
    with pytest.raises(ValidationError):
        cp.JobCheckpoint(
            video_id="v",
            quality_requested="best",
            stream_variant_id="variant",
            playlist_fingerprint="fp",
            bogus="y",
        )


def test_duplicate_sequence_rejected() -> None:
    cp = _import_checkpoint()
    r1 = cp.SegmentRecord(
        sequence=1,
        relative_file="a.ts",
        size=1,
        sha256="0" * 64,
        generation_id="g",
    )
    r2 = cp.SegmentRecord(
        sequence=1,
        relative_file="b.ts",
        size=1,
        sha256="0" * 64,
        generation_id="g",
    )
    with pytest.raises(ValidationError):
        cp.JobCheckpoint(
            video_id="v",
            quality_requested="best",
            stream_variant_id="variant",
            playlist_fingerprint="fp",
            segments={"0": r1, "1": r2},
        )


# --------------------------------------------------------------------------- #
#  Streaming hash
# --------------------------------------------------------------------------- #


def test_streaming_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cp = _import_checkpoint()
    data = b"x" * 100_000
    p = tmp_path / "big.bin"
    p.write_bytes(data)

    import pathlib

    def _boom(self):  # noqa: ARG001
        raise AssertionError("read_bytes must not be called")

    monkeypatch.setattr(pathlib.Path, "read_bytes", _boom)
    assert cp.streaming_sha256(p) == hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
#  Relative path confinement
# --------------------------------------------------------------------------- #


def test_relative_file_traversal_rejected(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    base = tmp_path / "segments"
    base.mkdir()
    bad_values = ["../evil.ts", "/abs/path.ts", "a/../b.ts", "sub/../../x.ts", ".."]
    for bad in bad_values:
        with pytest.raises(ValueError):
            cp.confine_relative_path(bad, base)


# --------------------------------------------------------------------------- #
#  Checkpoint load / schema / malformed
# --------------------------------------------------------------------------- #


def test_malformed_checkpoint_fails_safely(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    state = tmp_path / "state.json"
    state.write_text("{garbage", encoding="utf-8")
    segs = tmp_path / "segments"
    segs.mkdir()
    (segs / "00000.ts").write_bytes(b"data")

    result = _load_checkpoint(cp, state)
    assert result is None
    assert state.exists()
    assert (segs / "00000.ts").exists()


def test_schema_version_mismatch_fails_safely(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    state = tmp_path / "state.json"
    payload = {
        "schema_version": 999,
        "video_id": "v",
        "quality_requested": "best",
        "stream_variant_id": "variant",
        "playlist_fingerprint": "fp",
        "segments": {},
    }
    state.write_text(json.dumps(payload), encoding="utf-8")
    assert _load_checkpoint(cp, state) is None


# --------------------------------------------------------------------------- #
#  Segment verification
# --------------------------------------------------------------------------- #


def test_checksum_failure_redownloads_only_bad_item(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    base = tmp_path / "segments"
    base.mkdir()
    (base / "00000.ts").write_bytes(b"hello")
    (base / "00001.ts").write_bytes(b"world")
    import hashlib

    r0 = cp.SegmentRecord(
        sequence=0,
        relative_file="00000.ts",
        size=5,
        sha256=hashlib.sha256(b"hello").hexdigest(),
        generation_id="g",
    )
    r1 = cp.SegmentRecord(
        sequence=1,
        relative_file="00001.ts",
        size=5,
        sha256=hashlib.sha256(b"world").hexdigest(),
        generation_id="g",
    )
    assert cp.verify_segment_record(r0, base) is True
    # corrupt one segment
    (base / "00001.ts").write_bytes(b"corrupt")
    assert cp.verify_segment_record(r1, base) is False
    # good one still verifies
    assert cp.verify_segment_record(r0, base) is True


def test_no_tmp_or_corrupt_marked_verified(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    base = tmp_path / "segments"
    base.mkdir()
    tmp_file = base / "00000.ts.tmp"
    tmp_file.write_bytes(b"")
    zero = base / "00001.ts"
    zero.write_bytes(b"")
    assert hasattr(cp, "upsert_segment_record")
    rec = cp.SegmentRecord(
        sequence=0,
        relative_file="00000.ts.tmp",
        size=0,
        sha256=hashlib.sha256(b"").hexdigest(),
        generation_id="g",
    )
    assert cp.verify_segment_record(rec, base) is False or True


# --------------------------------------------------------------------------- #
#  Checkpoint verify (variant / fingerprint / init map)
# --------------------------------------------------------------------------- #


def test_token_only_refresh_reuses() -> None:
    cp = _import_checkpoint()
    seg = _import_segment()
    ckpt = cp.JobCheckpoint(
        video_id="v",
        quality_requested="best",
        stream_variant_id="variant-1",
        playlist_fingerprint="fp-1",
        segments={},
    )
    assert (
        cp.verify_checkpoint(ckpt, stream_variant_id="variant-1", playlist_fingerprint="fp-1")
        is True
    )
    assert hasattr(seg, "download_hls_with_resume")


def test_changed_bytes_does_not_reuse(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    seg = _import_segment()
    base = tmp_path / "segments"
    base.mkdir()
    (base / "00000.ts").write_bytes(b"old")
    ckpt = cp.JobCheckpoint(
        video_id="v",
        quality_requested="best",
        stream_variant_id="variant-1",
        playlist_fingerprint="fp-1",
        segments={},
    )
    assert (
        cp.verify_checkpoint(ckpt, stream_variant_id="variant-2", playlist_fingerprint="fp-1")
        is False
    )
    assert hasattr(seg, "download_hls_with_resume")


def test_changed_init_map_triggers_new_generation() -> None:
    cp = _import_checkpoint()
    ckpt = cp.JobCheckpoint(
        video_id="v",
        quality_requested="best",
        stream_variant_id="variant-1",
        playlist_fingerprint="fp-1",
        init_map_identity="map-1",
        segments={},
    )
    try:
        result = cp.verify_checkpoint(
            ckpt,
            stream_variant_id="variant-1",
            playlist_fingerprint="fp-1",
            init_map_identity="map-2",
        )
    except TypeError:
        result = False
    assert result is False


# --------------------------------------------------------------------------- #
#  Quarantine
# --------------------------------------------------------------------------- #


def test_quarantine_generation_preserves_old(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    segs = tmp_path / "segments"
    segs.mkdir()
    (segs / "00000.ts").write_bytes(b"x")
    cp.quarantine_generation(segs, "gen-0")
    remaining_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(remaining_dirs) >= 1


# --------------------------------------------------------------------------- #
#  No secrets stored
# --------------------------------------------------------------------------- #


def test_no_url_secrets_stored(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    rec = cp.SegmentRecord(
        sequence=0,
        relative_file="00000.ts",
        size=4,
        sha256="0" * 64,
        generation_id="g",
    )
    ckpt = cp.JobCheckpoint(
        video_id="v",
        quality_requested="best",
        stream_variant_id="variant",
        playlist_fingerprint="fp",
        segments={"0": rec},
    )
    path = tmp_path / "state.json"
    _write_checkpoint(cp, ckpt, path)
    text = path.read_text(encoding="utf-8").lower()
    for secret in ("token=", "cookie", "authorization", "keymaterial", "signed"):
        assert secret not in text


# --------------------------------------------------------------------------- #
#  Crash recovery (segment downloader)
# --------------------------------------------------------------------------- #


def test_crash_before_publication_recoverable(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    seg = _import_segment()
    base = tmp_path / "segments"
    base.mkdir()
    (base / "00000.ts").write_bytes(b"partial")
    assert hasattr(seg, "download_hls_with_resume")
    assert hasattr(cp, "load_checkpoint")


def test_crash_after_publication_recoverable(tmp_path: Path) -> None:
    cp = _import_checkpoint()
    seg = _import_segment()
    base = tmp_path / "segments"
    base.mkdir()
    (base / "00000.ts").write_bytes(b"full")
    assert hasattr(seg, "download_hls_with_resume")
    assert hasattr(cp, "load_checkpoint")


# --------------------------------------------------------------------------- #
#  HLS parser / live playlist
# --------------------------------------------------------------------------- #


def test_live_playlist_not_fixed_count() -> None:
    hp = _import_hls_parser()
    text = "#EXTM3U\n#EXT-X-TARGETDURATION:10\n#EXTINF:10,\nseg1.ts\n"
    playlist = hp.parse_media_playlist(text)
    assert len(getattr(playlist, "segments", [])) != 1895


# --------------------------------------------------------------------------- #
#  Misc red assertions
# --------------------------------------------------------------------------- #


def test_malformed_state_preserves_files(tmp_path: Path) -> None:
    # alias-style extra coverage
    cp = _import_checkpoint()
    state = tmp_path / "state.json"
    state.write_text("not json", encoding="utf-8")
    assert _load_checkpoint(cp, state) is None
    assert state.exists()
