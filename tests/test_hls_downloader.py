"""Tests for HLSDownloader service with ffmpeg integration."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.services.downloader import HLSDownloader


class TestHLSDownloader:
    """Tests for HLSDownloader class."""

    def test_hls_downloader_init_with_settings(self, test_settings: Settings) -> None:
        """Test HLSDownloader initializes correctly with provided settings."""
        downloader = HLSDownloader(settings=test_settings)

        assert downloader.settings == test_settings

    def test_hls_downloader_init_without_settings(self) -> None:
        """Test HLSDownloader initializes with default settings when not provided."""
        downloader = HLSDownloader()

        assert downloader.settings is not None
        assert isinstance(downloader.settings, Settings)


class TestFFmpegCommand:
    """Tests for ffmpeg command building."""

    def test_ffmpeg_command_build(self, test_settings: Settings) -> None:
        """Test ffmpeg command is built with correct arguments."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("/tmp/output.mp4")
        m3u8_url = "https://example.com/video.m3u8"

        cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path)

        assert "ffmpeg" in cmd
        assert "-y" in cmd
        assert "-headers" in cmd
        assert "-i" in cmd
        assert "-c" in cmd
        assert "copy" in cmd
        assert str(output_path) in cmd
        assert m3u8_url in cmd

    def test_ffmpeg_command_includes_user_agent(self, test_settings: Settings) -> None:
        """Test ffmpeg command includes user-agent header."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("/tmp/output.mp4")
        m3u8_url = "https://example.com/video.m3u8"

        cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path)

        headers_index = cmd.index("-headers")
        headers_value = cmd[headers_index + 1]
        assert "User-Agent" in headers_value
        assert test_settings.user_agent in headers_value
        assert "Referer" in headers_value

    def test_ffmpeg_command_includes_cookies(self, test_settings: Settings) -> None:
        """Test ffmpeg command includes cookies when provided."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("/tmp/output.mp4")
        m3u8_url = "https://example.com/video.m3u8"
        cookies = "vk=abc123; session=xyz"

        cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path, cookies)

        headers_index = cmd.index("-headers")
        headers_value = cmd[headers_index + 1]
        assert "Cookie" in headers_value
        assert cookies in headers_value

    def test_ffmpeg_command_includes_m3u8_url(self, test_settings: Settings) -> None:
        """Test ffmpeg command includes the m3u8 URL."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("/tmp/output.mp4")
        m3u8_url = "https://example.com/video.m3u8"

        cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path)

        assert m3u8_url in cmd

    def test_ffmpeg_command_output_path(self, test_settings: Settings) -> None:
        """Test ffmpeg command uses correct output path."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("output/720p.mp4")

        cmd = downloader._build_ffmpeg_cmd("https://example.com/video.m3u8", output_path)

        assert str(output_path) in cmd


class TestHLSDownloaderDownload:
    """Tests for HLSDownloader download functionality."""

    @pytest.mark.asyncio
    async def test_download_with_ffmpeg_success(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg returns path on success."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720"
            )

            assert result == output_path

    @pytest.mark.asyncio
    async def test_error_handling_ffmpeg_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg returns None on ffmpeg failure."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_ffmpeg_command_contains_expected_elements(
        self, test_settings: Settings
    ) -> None:
        """Test that ffmpeg command is built with all expected elements."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("/tmp/video.mp4")
        m3u8_url = "https://example.com/video.m3u8"

        cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path)

        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd
        assert "-headers" in cmd
        assert "User-Agent" in cmd[cmd.index("-headers") + 1]
        assert "-i" in cmd
        assert m3u8_url in cmd

    def test_ffmpeg_command_output_path(self, test_settings: Settings) -> None:
        """Test ffmpeg command uses correct output path."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("output/720p.mp4")

        cmd = downloader._build_ffmpeg_cmd("https://example.com/video.m3u8", output_path)

        assert str(output_path) in cmd


class TestHLSDownloaderDownload:
    """Tests for HLSDownloader download functionality."""

    @pytest.mark.asyncio
    async def test_download_with_ffmpeg_success(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg returns path on success."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720"
            )

            assert result == output_path

    @pytest.mark.asyncio
    async def test_error_handling_ffmpeg_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg returns None on ffmpeg failure."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"ffmpeg error"))
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_ffmpeg_command_contains_expected_elements(
        self, test_settings: Settings
    ) -> None:
        """Test that ffmpeg command is built with all expected elements."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("/tmp/video.mp4")
        m3u8_url = "https://example.com/video.m3u8"

        cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path)

        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd
        assert "-headers" in cmd
        headers_arg = cmd[cmd.index("-headers") + 1]
        assert "User-Agent" in headers_arg
        assert "-i" in cmd
        assert m3u8_url in cmd
