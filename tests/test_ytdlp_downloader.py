"""RED tests for Block G yt-dlp outer loop scenarios."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from vkdownloader.config import Settings


def _import_ytdlp():
    try:
        from vkdownloader.services.ytdlp_downloader import _build_ytdlp_cli_command
    except ImportError as exc:
        pytest.fail(f"yt-dlp helpers not available: {exc}")
    return _build_ytdlp_cli_command


def _import_state_machine():
    try:
        from vkdownloader.models.enums import DownloadState, ErrorCategory
        from vkdownloader.services.state_machine import DownloadStateMachine
    except ImportError as exc:
        pytest.fail(f"Block G state machine not available: {exc}")
    return DownloadState, ErrorCategory, DownloadStateMachine


def test_ytdlp_internal_retries_are_one(test_settings: Settings) -> None:
    from vkdownloader.config import Settings

    custom = Settings(max_retries=3)
    _build_ytdlp_cli_command = _import_ytdlp()
    cmd, _ = _build_ytdlp_cli_command(
        output_file=Path("/tmp/test.mp4"),
        quality_str="720",
        user_agent=custom.user_agent,
        settings=custom,
        cookies=None,
        raw_cookies=None,
    )
    assert "-R" in cmd
    assert cmd[cmd.index("-R") + 1] == "1"
    assert "--fragment-retries" in cmd
    assert cmd[cmd.index("--fragment-retries") + 1] == "1"


def test_block_g_state_machine_importable() -> None:
    DownloadState, ErrorCategory, DownloadStateMachine = _import_state_machine()
    assert DownloadState is not None
    assert ErrorCategory is not None
    assert DownloadStateMachine is not None


@pytest.mark.asyncio
async def test_ytdlp_argv_lacks_signed_url_with_cookies(
    test_settings: Settings, tmp_path: Path
) -> None:
    from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

    output_file = tmp_path / "video.mp4"
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.pid = 12345
    mock_process.stdout = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)

    captured: dict[str, object] = {"cmd": [], "kwargs": {}}

    async def mock_create_subprocess_exec(*cmd: object, **kwargs: object) -> object:
        captured["cmd"] = [str(c) for c in cmd]
        captured["kwargs"] = kwargs
        return mock_process

    signed_url = "https://example.com/playlist.m3u8?token=SECRET123"
    with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
        with patch("vkdownloader.services.ytdlp_downloader.logger"):
            await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                signed_url,
                output_file,
                "720",
                test_settings,
                cookies="vk=abc123",
            )

    flat_cmd = " ".join(captured["cmd"])  # type: ignore[arg-type]
    assert signed_url not in flat_cmd
    assert "SECRET123" not in flat_cmd
    assert "--batch-file" in captured["cmd"]
    assert captured["kwargs"].get("stdin") is not None


@pytest.mark.asyncio
async def test_ytdlp_argv_lacks_signed_url_without_cookies(
    test_settings: Settings, tmp_path: Path
) -> None:
    from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

    output_file = tmp_path / "video.mp4"
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.pid = 12345
    mock_process.stdout = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)

    captured: dict[str, object] = {"cmd": [], "kwargs": {}}

    async def mock_create_subprocess_exec(*cmd: object, **kwargs: object) -> object:
        captured["cmd"] = [str(c) for c in cmd]
        captured["kwargs"] = kwargs
        return mock_process

    signed_url = "https://example.com/playlist.m3u8?token=SECRET456"
    with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
        with patch("vkdownloader.services.ytdlp_downloader.logger"):
            await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                signed_url,
                output_file,
                "720",
                test_settings,
            )

    flat_cmd = " ".join(captured["cmd"])  # type: ignore[arg-type]
    assert signed_url not in flat_cmd
    assert "SECRET456" not in flat_cmd
    assert "--batch-file" in captured["cmd"]
    assert captured["kwargs"].get("stdin") is None


@pytest.mark.asyncio
async def test_bounded_drain_cap_and_truncation() -> None:
    from vkdownloader.services.ytdlp_downloader import bounded_drain

    class FakeStream:
        def __init__(self):
            self.data = b"a" * 1000

        async def read(self, n):
            if not self.data:
                return b""
            chunk = self.data[:n]
            self.data = self.data[n:]
            return chunk

    stream = FakeStream()
    result = await bounded_drain(stream, timeout=5.0, max_bytes=100, chunk_size=60)
    assert len(result) == 100


@pytest.mark.asyncio
async def test_bounded_drain_eof() -> None:
    from vkdownloader.services.ytdlp_downloader import bounded_drain

    class FakeStream:
        async def read(self, n):
            return b""

    result = await bounded_drain(FakeStream(), timeout=5.0, max_bytes=100, chunk_size=60)
    assert result == b""


@pytest.mark.asyncio
async def test_child_started_emitted_right_after_spawn(test_settings, tmp_path) -> None:
    from unittest.mock import AsyncMock, patch

    from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

    output_file = tmp_path / "video.mp4"
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.pid = 999
    mock_process.stdout = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)

    async def mock_create_subprocess_exec(*cmd, **kwargs):
        return mock_process

    events = []

    class FakeLogger:
        def info(self, event, **kw):
            events.append((event, kw))

        def warning(self, *a, **k):
            pass

        def error(self, *a, **k):
            pass

        def debug(self, *a, **k):
            pass

    with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
        with patch("vkdownloader.services.ytdlp_downloader.logger", FakeLogger()):
            await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                "https://example.com/playlist.m3u8",
                output_file,
                "720",
                test_settings,
            )

    names = [e[0] for e in events]
    assert "child_started" in names
    cs = next(e[1] for e in events if e[0] == "child_started")
    assert cs.get("pid") == 999
    ce = next(e[1] for e in events if e[0] == "child_exit")
    assert ce.get("pid") == 999


@pytest.mark.asyncio
async def test_correlation_id_bound(test_settings, tmp_path) -> None:
    from unittest.mock import AsyncMock, patch

    from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp
    from vkdownloader.utils import correlation

    output_file = tmp_path / "video.mp4"
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.pid = 1
    mock_process.stdout = AsyncMock()
    mock_process.stdout.readline = AsyncMock(return_value=b"")
    mock_process.wait = AsyncMock(return_value=0)

    async def mock_create_subprocess_exec(*cmd, **kwargs):
        return mock_process

    with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
        with patch("vkdownloader.services.ytdlp_downloader.logger"):
            await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                "https://example.com/playlist.m3u8",
                output_file,
                "720",
                test_settings,
            )
    assert hasattr(correlation, "generate_correlation_id")
