"""Tests for HLSDownloader service with ffmpeg integration."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.models.dtos import HLSDownloadRequest
from vkdownloader.services.downloader import (
    HLSDownloader,
    _cleanup_segments,
    _load_downloaded_count,
    _parse_m3u8_segments,
    _save_downloaded_count,
    download_hls_with_resume,
)


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
        headers_arg = cmd[cmd.index("-headers") + 1]
        assert "User-Agent" in headers_arg
        assert "-i" in cmd
        assert m3u8_url in cmd


class TestDownloadHlsWithResume:
    """Tests for download_hls_with_resume segment-level resume functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_on_playlist_fetch_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test segments are cleaned up when playlist fetch fails."""
        output_path = tmp_path / "video.mp4"
        segments_dir = tmp_path / ".video_segments"
        metadata_file = tmp_path / ".video_progress.json"

        # Pre-create segments dir to simulate partial state
        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_bytes(b"fake segment data")
        metadata_file.write_text('{"downloaded_count": 1}')

        with patch(
            "vkdownloader.services.downloader._fetch_playlist_with_retry",
            return_value=None,
        ):
            result = await download_hls_with_resume(
                HLSDownloadRequest(
                    video_url="https://vkvideo.ru/video-12345_67890",
                    m3u8_url="https://example.com/video.m3u8",
                    output_file=output_path,
                    settings=test_settings,
                )
            )

        assert result is None
        assert not segments_dir.exists(), "Segments directory should be cleaned up"
        assert not metadata_file.exists(), "Metadata file should be cleaned up"

    @pytest.mark.asyncio
    async def test_cleanup_on_segment_download_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test segments are cleaned up when segment download fails."""
        output_path = tmp_path / "video.mp4"
        segments_dir = tmp_path / ".video_segments"
        metadata_file = tmp_path / ".video_progress.json"

        # Pre-create segments dir to simulate partial state
        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00000.ts").write_bytes(b"fake segment data")
        metadata_file.write_text('{"downloaded_count": 1}')

        with patch(
            "vkdownloader.services.downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts",
        ):
            with patch(
                "vkdownloader.services.downloader._download_segment",
                return_value=False,
            ):
                result = await download_hls_with_resume(
                    HLSDownloadRequest(
                        video_url="https://vkvideo.ru/video-12345_67890",
                        m3u8_url="https://example.com/video.m3u8",
                        output_file=output_path,
                        settings=test_settings,
                    )
                )

        assert result is None
        assert not segments_dir.exists(), "Segments directory should be cleaned up on failure"


class TestParseM3u8Segments:
    """Tests for _parse_m3u8_segments helper function."""

    def test_parse_simple_playlist(self) -> None:
        """Test parsing simple m3u8 playlist."""
        content = "#EXTM3U\nsegment1.ts\nsegment2.ts\nsegment3.ts"
        result = _parse_m3u8_segments(content)

        assert result == ["segment1.ts", "segment2.ts", "segment3.ts"]

    def test_parse_playlist_with_metadata(self) -> None:
        """Test parsing playlist with metadata lines."""
        content = "#EXTM3U\n#EXT-X-VERSION:3\nsegment1.ts\n#EXT-X-ENDLIST\nsegment2.ts"
        result = _parse_m3u8_segments(content)

        assert result == ["segment1.ts", "segment2.ts"]

    def test_parse_empty_playlist(self) -> None:
        """Test parsing empty playlist."""
        content = "#EXTM3U\n#EXT-X-VERSION:3"
        result = _parse_m3u8_segments(content)

        assert result == []


class TestLoadSaveDownloadedCount:
    """Tests for progress metadata functions."""

    def test_load_downloaded_count_no_file(self, tmp_path: Path) -> None:
        """Test loading count when metadata file doesn't exist."""
        metadata_file = tmp_path / ".progress.json"

        result = _load_downloaded_count(metadata_file)

        assert result == 0

    def test_save_and_load_downloaded_count(self, tmp_path: Path) -> None:
        """Test saving and loading downloaded count."""
        metadata_file = tmp_path / ".progress.json"

        _save_downloaded_count(metadata_file, 5)
        result = _load_downloaded_count(metadata_file)

        assert result == 5

    def test_load_downloaded_count_invalid_json(self, tmp_path: Path) -> None:
        """Test loading count with invalid JSON returns 0."""
        metadata_file = tmp_path / ".progress.json"
        metadata_file.write_text("invalid json")

        result = _load_downloaded_count(metadata_file)

        assert result == 0


class TestCleanupSegments:
    """Tests for _cleanup_segments helper function."""

    def test_cleanup_removes_segment_files(self, tmp_path: Path) -> None:
        """Test that cleanup removes segment files."""
        segments_dir = tmp_path / ".segments"
        metadata_file = tmp_path / ".progress.json"

        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_text("segment data")
        (segments_dir / "00002.ts").write_text("segment data")
        metadata_file.write_text('{"downloaded_count": 2}')

        _cleanup_segments(segments_dir, metadata_file)

        assert not segments_dir.exists()
        assert not metadata_file.exists()

    def test_cleanup_handles_missing_metadata(self, tmp_path: Path) -> None:
        """Test cleanup handles missing metadata file gracefully."""
        segments_dir = tmp_path / ".segments"
        metadata_file = tmp_path / ".progress.json"

        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_text("segment data")

        _cleanup_segments(segments_dir, metadata_file)

        assert not segments_dir.exists()
        assert not metadata_file.exists()

    def test_cleanup_handles_non_empty_directory(self, tmp_path: Path) -> None:
        """Test cleanup removes all files in segments directory."""
        segments_dir = tmp_path / ".segments"
        metadata_file = tmp_path / ".progress.json"

        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_text("segment data")
        (segments_dir / "batch.txt").write_text("batch file")

        _cleanup_segments(segments_dir, metadata_file)

        assert not segments_dir.exists()
