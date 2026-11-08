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


@pytest.mark.asyncio
async def test_validate_complete_ts_rejects_wrong_container(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return _ffprobe_payload(format_name="mov,mp4,m4a,3gp,3g2,mj2")

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path, name="video.ts")
    with pytest.raises(MediaValidationError) as exc:
        await mv.validate_complete_ts(f)
    assert exc.value.reason == "container_mismatch"


@pytest.mark.asyncio
async def test_check_dts_continuity_accepts_monotonic(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return {
            "streams": [],
            "format": {"duration": "10.0", "format_name": "mpegts"},
            "packets": [
                {"pkt_dts_time": "0.0"},
                {"pkt_dts_time": "5.0"},
                {"pkt_dts_time": "10.0"},
            ],
        }

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path, name="video.ts")
    await mv.check_dts_continuity(f, expected_duration=10.0)


@pytest.mark.asyncio
async def test_check_dts_continuity_rejects_backward_jump(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return {
            "streams": [],
            "format": {"duration": "10.0", "format_name": "mpegts"},
            "packets": [
                {"pkt_dts_time": "0.0"},
                {"pkt_dts_time": "5.0"},
                {"pkt_dts_time": "3.0"},
            ],
        }

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path, name="video.ts")
    with pytest.raises(MediaValidationError) as exc:
        await mv.check_dts_continuity(f)
    assert exc.value.reason == "dts_backward_jump_exceeded"


@pytest.mark.asyncio
async def test_check_dts_continuity_rejects_final_timestamp(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return {
            "streams": [],
            "format": {"duration": "10.0", "format_name": "mpegts"},
            "packets": [
                {"pkt_dts_time": "0.0"},
                {"pkt_dts_time": "5.0"},
                {"pkt_dts_time": "9.0"},
            ],
        }

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)
    f = _make_file(tmp_path, name="video.ts")
    with pytest.raises(MediaValidationError) as exc:
        await mv.check_dts_continuity(f, expected_duration=100.0)
    assert exc.value.reason == "final_timestamp_out_of_tolerance"


@pytest.mark.asyncio
async def test_remux_ts_to_mp4_invokes_ffmpeg_with_c_copy(monkeypatch, tmp_path):
    import asyncio
    import shutil
    from pathlib import Path
    from types import SimpleNamespace

    monkeypatch.setattr(mv, "check_ffprobe_available", lambda: True)

    async def fake_validate(path, **kwargs):
        return SimpleNamespace(video_height=720, duration_seconds=10.0)

    monkeypatch.setattr(mv, "validate_media_file", fake_validate)

    async def fake_ffprobe(path, *, timeout_seconds=60.0):
        return {
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1280, "height": 720},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"duration": "10.0", "format_name": "mpegts"},
        }

    monkeypatch.setattr(mv, "run_ffprobe_json", fake_ffprobe)

    monkeypatch.setattr(shutil, "which", lambda name: "ffmpeg" if name == "ffmpeg" else None)

    captured = {}

    class FakeProc:
        returncode = 0

        async def communicate(self):
            Path(captured["cmd"][-1]).write_bytes(b"x")
            return b"", b""

    async def fake_exec(*args, **kwargs):
        captured["cmd"] = list(args)
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)

    ts = _make_file(tmp_path, name="video.ts")
    mp4 = tmp_path / "video.mp4"
    result = await mv.remux_ts_to_mp4(ts, mp4)
    assert result == mp4
    cmd = captured["cmd"]
    assert "-c" in cmd
    idx = cmd.index("-c")
    assert cmd[idx + 1] == "copy"
    assert "-bsf:a" in cmd
    bsf_idx = cmd.index("-bsf:a")
    assert cmd[bsf_idx + 1] == "aac_adtstoasc"
