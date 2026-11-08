"""Independent media validation via ffprobe."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
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
        "-show_entries",
        "packet=pkt_dts_time",
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


async def check_dts_continuity(
    path: Path,
    *,
    allowed_backward_jumps: int = 0,
    expected_duration: float | None = None,
    duration_tolerance_seconds: float = 2.0,
    timeout_seconds: float = 60.0,
) -> None:
    """Check DTS continuity of the video stream."""
    target = Path(path)
    if not target.exists() or not target.is_file() or target.stat().st_size <= 0:
        raise MediaValidationError("media_file_missing_or_empty")
    data = await run_ffprobe_json(target, timeout_seconds=timeout_seconds)
    if not isinstance(data, dict):
        raise MediaValidationError("ffprobe_json_invalid")
    packets_raw = data.get("packets")
    packets = packets_raw if isinstance(packets_raw, list) else []
    dts_values: list[float] = []
    for pkt in packets:
        if not isinstance(pkt, dict):
            continue
        value = pkt.get("pkt_dts_time")
        if value is None:
            value = pkt.get("dts_time")
        if value is None:
            value = pkt.get("dts")
        try:
            dts_values.append(float(value))  # type: ignore[arg-type]
        except TypeError, ValueError:
            continue
    if len(dts_values) < 2:
        raise MediaValidationError("insufficient_packets")
    backward_jumps = 0
    for i in range(1, len(dts_values)):
        if dts_values[i - 1] - dts_values[i] > 0.1:
            backward_jumps += 1
    if backward_jumps > int(allowed_backward_jumps):
        raise MediaValidationError("dts_backward_jump_exceeded")
    if expected_duration is not None:
        tol = max(duration_tolerance_seconds, 0.01 * float(expected_duration))
        if abs(dts_values[-1] - float(expected_duration)) > tol:
            raise MediaValidationError("final_timestamp_out_of_tolerance")


async def validate_complete_ts(
    path: Path,
    *,
    expected_height: int | None = None,
    expected_duration: float | None = None,
    allowed_backward_jumps: int = 0,
    duration_tolerance_seconds: float = 2.0,
    deep_decode: bool = False,
    timeout_seconds: float = 60.0,
) -> MediaInfo:
    info = await validate_media_file(
        path,
        expected_container="mpegts",
        expected_height=expected_height,
        expected_duration=expected_duration,
        duration_tolerance_seconds=duration_tolerance_seconds,
        deep_decode=deep_decode,
        timeout_seconds=timeout_seconds,
    )
    await check_dts_continuity(
        path,
        allowed_backward_jumps=allowed_backward_jumps,
        expected_duration=expected_duration,
        duration_tolerance_seconds=duration_tolerance_seconds,
        timeout_seconds=timeout_seconds,
    )
    return info


async def remux_ts_to_mp4(
    ts_path: Path,
    mp4_path: Path,
    *,
    timeout_seconds: float = 300.0,
) -> Path:
    import shutil as _shutil

    ts = Path(ts_path)
    mp4 = Path(mp4_path)
    mp4.parent.mkdir(parents=True, exist_ok=True)

    # Sweep stale remux temp files.
    try:
        for stale in mp4.parent.glob(".remux-*.tmp"):
            # best-effort
            try:
                stale.unlink(missing_ok=True)
            except OSError:
                pass
        for stale in mp4.parent.glob(f".{mp4.name}.remux-*.tmp"):
            try:
                stale.unlink(missing_ok=True)
            except OSError:
                pass
    except OSError:
        pass

    if not check_ffprobe_available():
        raise MediaValidationError("ffprobe_missing")
    # ffmpeg availability
    ffmpeg = _shutil.which("ffmpeg")
    if ffmpeg is None:
        for cand in ("C:/ffmpeg/ffmpeg.exe", "C:\\ffmpeg\\ffmpeg.exe"):
            if Path(cand).is_file():
                ffmpeg = cand
                break
    if ffmpeg is None:
        raise MediaValidationError("ffmpeg_missing")

    # Probe TS info and audio codec.
    ts_info = await validate_media_file(ts, expected_container="mpegts")
    height = ts_info.video_height
    duration = ts_info.duration_seconds

    data = await run_ffprobe_json(ts, timeout_seconds=60.0)
    audio_codec = None
    streams_raw = data.get("streams")
    streams = streams_raw if isinstance(streams_raw, list) else []
    audio_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    if audio_streams and isinstance(audio_streams[0], dict):
        audio_codec = audio_streams[0].get("codec_name")

    temp = mp4.parent / f".{mp4.name}.remux-{os.getpid()}-{uuid.uuid4().hex}.tmp"

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(ts),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-dn",
        "-sn",
        "-c",
        "copy",
    ]
    if audio_codec == "aac":
        cmd += ["-bsf:a", "aac_adtstoasc"]
    cmd += ["-movflags", "+faststart", str(temp)]

    from .ffmpeg_utils import _SPAWN_BOUNDARY_KWARGS

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **_SPAWN_BOUNDARY_KWARGS,  # type: ignore[arg-type]
        )
    except OSError as exc:
        raise MediaValidationError(f"ffmpeg_spawn_failed: {exc}") from exc
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise MediaValidationError("remux_timeout") from exc
    if proc.returncode != 0:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise MediaValidationError("remux_failed")
    # Validate temp.
    try:
        await validate_media_file(
            temp,
            expected_container="mp4",
            expected_height=height,
            expected_duration=duration,
            deep_decode=False,
            timeout_seconds=60.0,
        )
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    # Atomic replace.
    os.replace(temp, mp4)
    try:
        fd = os.open(str(mp4.parent), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass
    return mp4


__all__ = [
    "MediaInfo",
    "MediaValidationError",
    "run_ffprobe_json",
    "validate_media_file",
    "check_dts_continuity",
    "validate_complete_ts",
    "remux_ts_to_mp4",
]
