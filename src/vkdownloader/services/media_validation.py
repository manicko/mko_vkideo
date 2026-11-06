"""Independent media validation via ffprobe."""

from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..models.enums import ErrorCode
from .ffmpeg_utils import _ffprobe_binary, check_ffprobe_available


class MediaValidationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.error_code = ErrorCode.MEDIA_VALIDATION_FAILED


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    size_bytes: int
    duration_seconds: float | None
    format_name: str
    video_codec: str | None
    video_width: int | None
    video_height: int | None
    has_audio: bool
    stream_count: int


async def run_ffprobe_json(path: Path, *, timeout_seconds: float = 60.0) -> dict[str, object]:
    if not check_ffprobe_available():
        raise MediaValidationError("ffprobe_missing")
    binary = _ffprobe_binary()
    if binary is None:
        raise MediaValidationError("ffprobe_missing")
    target = Path(path)
    if not target.exists() or not target.is_file() or target.stat().st_size <= 0:
        raise MediaValidationError("media_file_missing_or_empty")
    cmd = [
        binary,
        "-v",
        "error",
        "-hide_banner",
        "-show_entries",
        "stream=index,codec_type,codec_name,width,height",
        "-show_entries",
        "format=duration,size,format_name",
        "-of",
        "json",
        str(target),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise MediaValidationError(f"ffprobe_spawn_failed: {exc}") from exc
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        raise MediaValidationError("ffprobe_timeout") from exc
    if proc.returncode != 0:
        raise MediaValidationError(f"ffprobe_failed: {stderr.decode(errors='replace').strip()}")
    try:
        data = json.loads(stdout.decode(errors="replace"))
    except (json.JSONDecodeError, ValueError) as exc:
        raise MediaValidationError("ffprobe_json_parse_failed") from exc
    if not isinstance(data, dict):
        raise MediaValidationError("ffprobe_json_invalid")
    return data


async def validate_media_file(
    path: Path,
    *,
    expected_height: int | None = None,
    expected_duration: float | None = None,
    duration_tolerance_seconds: float = 2.0,
    expected_container: str = "mp4",
    require_video: bool = True,
    require_audio: bool = False,
    timeout_seconds: float = 60.0,
    deep_decode: bool = False,
) -> MediaInfo:
    target = Path(path)
    if not target.exists() or not target.is_file():
        raise MediaValidationError("media_file_missing")
    size = target.stat().st_size
    if size <= 0:
        raise MediaValidationError("media_file_empty")

    data = await run_ffprobe_json(target, timeout_seconds=timeout_seconds)
    streams_raw = data.get("streams")
    streams = streams_raw if isinstance(streams_raw, list) else []
    fmt_raw = data.get("format")
    fmt = fmt_raw if isinstance(fmt_raw, dict) else {}
    format_name = str(fmt.get("format_name") or "")
    duration_raw = fmt.get("duration")
    try:
        duration = float(duration_raw) if duration_raw is not None else None
    except TypeError, ValueError:
        duration = None

    video_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    video = video_streams[0] if video_streams else None
    video_codec = video.get("codec_name") if isinstance(video, dict) else None
    video_width = video.get("width") if isinstance(video, dict) else None
    video_height = video.get("height") if isinstance(video, dict) else None

    if require_video and not video_streams:
        raise MediaValidationError("missing_video_stream")
    if require_audio and not audio_streams:
        raise MediaValidationError("missing_audio_stream")

    if (
        expected_height is not None
        and isinstance(expected_height, int)
        and video_height is not None
    ):
        if video_height != expected_height:
            raise MediaValidationError("height_mismatch")

    if expected_duration is not None and duration is not None:
        tol = max(duration_tolerance_seconds, 0.01 * float(expected_duration))
        if abs(duration - float(expected_duration)) > tol:
            raise MediaValidationError("duration_mismatch")

    if expected_container:
        container_token = str(expected_container).lower()
        if container_token == "mp4":
            if not any(tok in format_name.lower() for tok in ("mp4", "mov", "m4v", "isma")):
                raise MediaValidationError("container_mismatch")
        else:
            if container_token not in format_name.lower():
                raise MediaValidationError("container_mismatch")

    if deep_decode:
        await _deep_decode(target, timeout_seconds)

    return MediaInfo(
        path=target,
        size_bytes=size,
        duration_seconds=duration,
        format_name=format_name,
        video_codec=video_codec,
        video_width=int(video_width) if video_width is not None else None,
        video_height=int(video_height) if video_height is not None else None,
        has_audio=bool(audio_streams),
        stream_count=len(streams),
    )


async def _deep_decode(path: Path, timeout_seconds: float) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        for cand in ("C:/ffmpeg/ffmpeg.exe", "C:\\ffmpeg\\ffmpeg.exe"):
            if Path(cand).is_file():
                ffmpeg = cand
                break
    if ffmpeg is None:
        raise MediaValidationError("ffmpeg_missing")
    proc = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(path),
        "-f",
        "null",
        "-",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        raise MediaValidationError("ffmpeg_decode_timeout") from exc
    if proc.returncode != 0:
        raise MediaValidationError(
            f"ffmpeg_decode_failed: {stderr.decode(errors='replace').strip()}"
        )


__all__ = ["MediaInfo", "MediaValidationError", "run_ffprobe_json", "validate_media_file"]
