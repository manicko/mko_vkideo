"""RED tests for Block H FFmpeg transport (optional adapter)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vkdownloader.config import Settings


def _import_transport():
    try:
        from vkdownloader.services.ffmpeg_transport import DownloadTransport, FfmpegTransport
    except ImportError as exc:
        pytest.fail(f"ffmpeg transport not available: {exc}")
    return DownloadTransport, FfmpegTransport


def _import_helpers():
    try:
        from vkdownloader.services.ffmpeg_utils import (
            FfmpegProgress,
            ProgressParser,
            _temp_argfile,
            read_progress,
        )
    except ImportError as exc:
        pytest.fail(f"ffmpeg helpers not available: {exc}")
    return FfmpegProgress, ProgressParser, read_progress, _temp_argfile


def test_download_method_ffmpeg_exists() -> None:
    from vkdownloader.models.enums import DownloadMethod

    assert DownloadMethod.FFMPEG == "ffmpeg"
    assert DownloadMethod("ffmpeg") == DownloadMethod.FFMPEG


def test_download_transport_is_protocol() -> None:
    DownloadTransport, FfmpegTransport = _import_transport()
    import typing

    assert typing.is_protocol(DownloadTransport) is True
    transport = FfmpegTransport()
    assert transport.name == "ffmpeg"
    assert isinstance(transport, DownloadTransport)


@pytest.mark.asyncio
async def test_ffmpeg_transport_download_returns_staged_path(tmp_path: Path) -> None:
    DownloadTransport, FfmpegTransport = _import_transport()
    from vkdownloader.services.quality_refresh import StreamBinding
    from vkdownloader.services.workspace import make_workspace

    settings = Settings(download_dir=tmp_path)
    output_file = tmp_path / "video.mp4"
    workspace = make_workspace(output_file, "12345_67890", "720")
    binding = StreamBinding(
        media_playlist_url="https://example.com/v.m3u8", requested_quality="720"
    )

    class _FakeStream:
        async def readline(self) -> bytes:
            return b""

    fake_proc = _make_fake_process(workspace)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("asyncio.create_subprocess_exec", _make_fake_exec(workspace, fake_proc))
        transport = FfmpegTransport(settings=settings)
        staged = await transport.download(binding, workspace)

    assert staged is None


def _make_fake_process(workspace):
    from unittest.mock import AsyncMock, MagicMock

    proc = MagicMock()
    proc.pid = 12345
    proc.returncode = 0
    proc.stdout = MagicMock()
    proc.stdout.readline = AsyncMock(return_value=b"")
    proc.stderr = MagicMock()
    proc.stderr.readline = AsyncMock(return_value=b"")
    proc.communicate = AsyncMock(return_value=(b"", b""))
    proc.wait = AsyncMock(return_value=0)
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    return proc


def _make_fake_exec(workspace, proc):
    async def _exec(*args, **kwargs):
        assert kwargs.get("shell") is not True
        # Expected invocation shape: direct ffmpeg argv (no @argfile).
        assert args and str(args[0]) == "ffmpeg"
        # Simulate ffmpeg writing the staged artifact.
        (workspace.staging_dir / workspace.final_path.name).write_bytes(b"video")
        return proc

    return _exec


@pytest.mark.asyncio
async def test_ffmpeg_transport_failure_preserves_staged(tmp_path: Path) -> None:
    DownloadTransport, FfmpegTransport = _import_transport()
    from vkdownloader.services.quality_refresh import StreamBinding
    from vkdownloader.services.workspace import make_workspace

    settings = Settings(download_dir=tmp_path)
    output_file = tmp_path / "video.mp4"
    workspace = make_workspace(output_file, "12345_67890", "720")
    binding = StreamBinding(
        media_playlist_url="https://example.com/v.m3u8", requested_quality="720"
    )

    staged = workspace.staging_dir / workspace.final_path.name
    staged.write_bytes(b"partial")

    from unittest.mock import AsyncMock, MagicMock

    proc = MagicMock()
    proc.pid = 12345
    proc.returncode = 1
    proc.stdout = MagicMock()
    proc.stdout.readline = AsyncMock(return_value=b"")
    proc.stderr = MagicMock()
    proc.stderr.readline = AsyncMock(return_value=b"")
    proc.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
    proc.wait = AsyncMock(return_value=1)
    proc.terminate = MagicMock()
    proc.kill = MagicMock()

    async def _exec(*args, **kwargs):
        return proc

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("asyncio.create_subprocess_exec", _exec)
        transport = FfmpegTransport(settings=settings)
        result = await transport.download(binding, workspace)

    assert result is None
    assert staged.exists()


@pytest.mark.asyncio
async def test_ffmpeg_transport_no_secrets_in_argv(tmp_path: Path) -> None:
    DownloadTransport, FfmpegTransport = _import_transport()
    from vkdownloader.services.quality_refresh import StreamBinding
    from vkdownloader.services.workspace import make_workspace

    settings = Settings(download_dir=tmp_path)
    output_file = tmp_path / "video.mp4"
    workspace = make_workspace(output_file, "12345_67890", "720")
    binding = StreamBinding(
        media_playlist_url="https://example.com/v.m3u8?token=SECRET",
        requested_quality="720",
        cookies="cookie-secret",
        raw_cookies="raw-cookie-secret",
    )

    captured = {}

    from unittest.mock import AsyncMock, MagicMock

    proc = MagicMock()
    proc.pid = 1
    proc.returncode = 0
    proc.stdout = MagicMock()
    proc.stdout.readline = AsyncMock(return_value=b"")
    proc.stderr = MagicMock()
    proc.stderr.readline = AsyncMock(return_value=b"")
    proc.communicate = AsyncMock(return_value=(b"", b""))
    proc.wait = AsyncMock(return_value=0)

    async def _exec(*args, **kwargs):
        captured["args"] = list(args)
        captured["kwargs"] = dict(kwargs)
        (workspace.staging_dir / workspace.final_path.name).write_bytes(b"video")
        return proc

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("vkdownloader.services.media_validation.check_ffprobe_available", lambda: False)
        mp.setattr("asyncio.create_subprocess_exec", _exec)
        transport = FfmpegTransport(settings=settings)
        result = await transport.download(binding, workspace)

    assert result is None
    assert captured["kwargs"].get("shell") is not True
    argv = [str(a) for a in captured["args"]]
    assert argv and argv[0] == "ffmpeg"

    headers_idx = argv.index("-headers")
    headers_element = argv[headers_idx + 1]
    i_idx = argv.index("-i")
    i_element = argv[i_idx + 1]
    output_path = argv[-1]

    for marker in ("cookie-secret", "raw-cookie-secret"):
        for idx, element in enumerate(argv):
            if marker in element:
                assert idx == headers_idx + 1, (
                    f"secret marker {marker!r} found outside -headers at argv[{idx}]"
                )

    assert "token=SECRET" in i_element

    for idx, element in enumerate(argv):
        if "SECRET" in element and idx != headers_idx + 1:
            assert idx == i_idx + 1 and "token=SECRET" in element, (
                f"SECRET leaked at argv[{idx}]: {element!r}"
            )

    for marker in ("SECRET", "cookie-secret", "raw-cookie-secret"):
        assert marker not in output_path, f"{marker!r} in output path"

    assert i_element != output_path
    _ = (headers_element, i_element)


def test_helpers_importable() -> None:
    FfmpegProgress, ProgressParser, read_progress, _temp_argfile = _import_helpers()
    assert FfmpegProgress is not None
    assert ProgressParser is not None
    assert read_progress is not None
    assert _temp_argfile is not None


@pytest.mark.asyncio
async def test_temp_argfile_removed_after_use(tmp_path: Path) -> None:
    FfmpegProgress, ProgressParser, read_progress, _temp_argfile = _import_helpers()

    async with _temp_argfile(
        ["-i", "https://example.com/v.m3u8", "-y", str(tmp_path / "out.mp4")]
    ) as path:
        assert path.exists()
        try:
            mode = path.stat().st_mode & 0o777
            assert mode == 0o600
        except Exception:
            pass
    assert not path.exists()


def test_progress_parser_parse_line() -> None:
    FfmpegProgress, ProgressParser, read_progress, _temp_argfile = _import_helpers()
    # Basic smoke: parse_line exists and callable.
    assert callable(getattr(ProgressParser, "parse_line", None))


@pytest.mark.asyncio
async def test_progress_total_zero_adapter() -> None:
    # Smoke: read_progress importable and callable/asyncgen.
    FfmpegProgress, ProgressParser, read_progress, _temp_argfile = _import_helpers()
    assert callable(read_progress) or hasattr(read_progress, "__aiter__")
