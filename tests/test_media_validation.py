"""Tests for independent media validation via ffprobe."""

from __future__ import annotations

from pathlib import Path

import pytest

from vkdownloader.services import media_validation as mv
from vkdownloader.services.media_validation import (
    MediaValidationError,
    validate_media_file,
)


def _make_file(tmp_path: Path, name: str = "video.mp4", content: bytes = b"x") -> Path:
    p = tmp_path / name
    p.write_bytes(content)
    return p


def _ffprobe_payload(
    *,
    height: int = 720,
    duration: float = 10.0,
    format_name: str = "mov,mp4,m4a,3gp,3g2,mj2",
    streams: list[dict] | None = None,
) -> dict:
    if streams is None:
        streams = [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1280,
                "height": height,
            },
            {"index": 1, "codec_type": "audio", "codec_name": "aac"},
        ]
    return {"streams": streams, "format": {"duration": str(duration), "format_name": format_name}}


@pytest.mark.asyncio
async def test_ffprobe_missing_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: False)
    f = _make_file(tmp_path)
    with pytest.raises(MediaValidationError) as exc:
        await validate_media_file(f)
    assert exc.value.reason == "ffprobe_missing"


@pytest.mark.asyncio
async def test_media_validation_rejects_empty_staged(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)
    f = _make_file(tmp_path, content=b"")
    # ensure empty file exists
    f.write_bytes(b"")
    with pytest.raises(MediaValidationError) as exc:
        await validate_media_file(f)
    assert exc.value.reason == "media_file_empty"


@pytest.mark.asyncio
async def test_media_validation_rejects_wrong_height(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return _ffprobe_payload(height=720)

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path)
    with pytest.raises(MediaValidationError) as exc:
        await validate_media_file(f, expected_height=1080)
    assert exc.value.reason == "height_mismatch"


@pytest.mark.asyncio
async def test_media_validation_rejects_missing_video_stream(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return _ffprobe_payload(streams=[{"index": 0, "codec_type": "audio", "codec_name": "aac"}])

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path)
    with pytest.raises(MediaValidationError) as exc:
        await validate_media_file(f)
    assert exc.value.reason == "missing_video_stream"


@pytest.mark.asyncio
async def test_media_validation_rejects_bad_container(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return _ffprobe_payload(format_name="matroska")

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path)
    with pytest.raises(MediaValidationError) as exc:
        await validate_media_file(f)
    assert exc.value.reason == "container_mismatch"


@pytest.mark.asyncio
async def test_media_validation_duration_tolerance(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return _ffprobe_payload(duration=10.0)

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path)
    # within tolerance (2s)
    info = await validate_media_file(f, expected_duration=11.0)
    assert info.duration_seconds == 10.0
    # outside tolerance
    with pytest.raises(MediaValidationError) as exc:
        await validate_media_file(f, expected_duration=100.0)
    assert exc.value.reason == "duration_mismatch"
