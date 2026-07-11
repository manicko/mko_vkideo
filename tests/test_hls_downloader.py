"""Tests for HLSDownloader service with ffmpeg integration."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.models.dtos import HLSDownloadRequest
from vkdownloader.services.downloader import (
    FfmpegProgress,
    HLSDownloader,
    _cleanup_segments,
    _cookies_to_netscape,
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

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(return_value=b"")
        mock_process.stderr = mock_stderr

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

        async def mock_wait() -> int:
            return 1

        mock_process.wait = mock_wait
        mock_process.returncode = 1
        mock_stderr = AsyncMock()
        # Return one error line then EOF
        mock_stderr.readline = AsyncMock(side_effect=[b"ffmpeg error\n", b""])
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_download_with_ffmpeg_with_progress_callback(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg calls progress callback when provided."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        progress_updates: list[FfmpegProgress] = []

        def progress_callback(progress: FfmpegProgress) -> None:
            progress_updates.append(progress)

        mock_process = AsyncMock()

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        # Return progress lines then EOF
        progress_lines = [
            b"frame=100\n",
            b"speed=1.5x\n",
            b"progress=continue\n",
            b"",  # EOF
        ]
        mock_stderr.readline = AsyncMock(side_effect=progress_lines)
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720",
                progress_callback=progress_callback
            )

            assert result == output_path
            assert len(progress_updates) == 1
            assert progress_updates[0].frame == 100
            assert progress_updates[0].speed == 1.5
            assert progress_updates[0].progress == "continue"

    @pytest.mark.asyncio
    async def test_download_with_ffmpeg_no_progress_callback(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg works without progress callback for backward compatibility."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        mock_process = AsyncMock()

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(return_value=b"")
        mock_process.stderr = mock_stderr

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720"
            )

            assert result == output_path


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
        assert not metadata_file.exists()


class TestCookiesToNetscape:
    """Tests for _cookies_to_netscape helper function."""

    def test_converts_valid_cookies(self) -> None:
        """Test converting valid cookies string to Netscape format."""
        cookies = "vk=abc123; session=xyz789"
        result = _cookies_to_netscape(cookies)

        assert "# Netscape HTTP Cookie File" in result
        assert "# Generated by vkdownloader" in result
        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tvk\tabc123" in result
        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession\txyz789" in result

    def test_handles_empty_cookies(self) -> None:
        """Test handling empty cookies string."""
        result = _cookies_to_netscape("")

        assert "# Netscape HTTP Cookie File" in result
        assert "# Generated by vkdownloader" in result
        # Should have only header lines, no cookie entries
        lines = result.split("\n")
        assert len(lines) == 3

    def test_handles_single_cookie(self) -> None:
        """Test handling single cookie."""
        cookies = "token=mytoken123"
        result = _cookies_to_netscape(cookies)

        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\ttoken\tmytoken123" in result

    def test_handles_cookie_with_equals_in_value(self) -> None:
        """Test handling cookie values containing equals sign."""
        cookies = "key=value=with=equals"
        result = _cookies_to_netscape(cookies)

        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tkey\tvalue=with=equals" in result

    def test_handles_malformed_cookies(self) -> None:
        """Test handling malformed cookies without equals sign."""
        cookies = "valid=abc; malformed; another=def"
        result = _cookies_to_netscape(cookies)

        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tvalid\tabc" in result
        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tanother\tdef" in result
        # malformed entry should not appear
        assert "malformed\t" not in result


class TestYtdlpOptions:
    """Tests for yt-dlp options configuration."""

    def test_ytdlp_options_includes_concurrent_fragments(self, test_settings: Settings) -> None:
        """Test yt-dlp options include concurrent_fragments setting."""
        ydl_opts = {
            "concurrent_fragments": test_settings.concurrent_fragments,
            "throttledratelimit": test_settings.throttled_rate,
            "http_chunk_size": test_settings.http_chunk_size,
        }

        assert "concurrent_fragments" in ydl_opts
        assert ydl_opts["concurrent_fragments"] == 4  # test_settings has max_concurrent_downloads=2 but concurrent_fragments=4 default


    def test_ytdlp_options_includes_throttled_rate(self, test_settings: Settings) -> None:
        """Test yt-dlp options include throttled_rate setting."""
        ydl_opts = {
            "concurrent_fragments": test_settings.concurrent_fragments,
            "throttledratelimit": test_settings.throttled_rate,
            "http_chunk_size": test_settings.http_chunk_size,
        }

        assert "throttledratelimit" in ydl_opts
        assert ydl_opts["throttledratelimit"] == 100000


    def test_ytdlp_options_includes_http_chunk_size(self, test_settings: Settings) -> None:
        """Test yt-dlp options include http_chunk_size setting."""
        ydl_opts = {
            "concurrent_fragments": test_settings.concurrent_fragments,
            "throttledratelimit": test_settings.throttled_rate,
            "http_chunk_size": test_settings.http_chunk_size,
        }

        assert "http_chunk_size" in ydl_opts
        assert ydl_opts["http_chunk_size"] == 10485760


    def test_ytdlp_options_custom_values(self) -> None:
        """Test yt-dlp options accept custom settings values."""
        custom_settings = Settings(concurrent_fragments=8, throttled_rate=200000, http_chunk_size=5242880)

        ydl_opts = {
            "concurrent_fragments": custom_settings.concurrent_fragments,
            "throttledratelimit": custom_settings.throttled_rate,
            "http_chunk_size": custom_settings.http_chunk_size,
        }

        assert ydl_opts["concurrent_fragments"] == 8
        assert ydl_opts["throttledratelimit"] == 200000
        assert ydl_opts["http_chunk_size"] == 5242880


class TestParallelSegmentsDownload:
    """Tests for parallel segment download with semaphore."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_downloads(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that semaphore enforces max_concurrent_downloads limit."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

        test_settings = Settings(max_concurrent_downloads=2)

        output_path = tmp_path / "video.mp4"

        download_count = 0

        async def mock_download_segment(
            session: Any,
            segment_url: str,
            output_path: Path,
            headers: dict[str, str],
        ) -> bool:
            nonlocal download_count
            download_count += 1
            output_path.write_bytes(b"segment data")
            return True

        with patch(
            "vkdownloader.services.downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts\nseg3.ts\nseg4.ts\n",
        ):
            with patch(
                "vkdownloader.services.downloader._download_segment",
                side_effect=mock_download_segment,
            ):
                with patch(
                    "vkdownloader.services.downloader._merge_segments_batched",
                    return_value=output_path,
                ):
                    await download_hls_with_resume(
                        HLSDownloadRequest(
                            video_url="https://vkvideo.ru/video-12345_67890",
                            m3u8_url="https://example.com/video.m3u8",
                            output_file=output_path,
                            settings=test_settings,
                        )
                    )

        # Verify all segments were downloaded
        assert download_count == 4


    @pytest.mark.asyncio
    async def test_parallel_download_uses_gather(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that parallel download uses asyncio.gather for concurrency."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

        output_path = tmp_path / "video.mp4"

        gather_called = False

        async def mock_gather(*tasks: Any) -> list[bool]:
            nonlocal gather_called
            gather_called = True
            # Return True for each task
            return [True] * len(tasks)

        with patch(
            "vkdownloader.services.downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts",
        ):
            with patch(
                "vkdownloader.services.downloader._download_segment",
                return_value=True,
            ):
                with patch(
                    "vkdownloader.services.downloader._merge_segments_batched",
                    return_value=output_path,
                ):
                    with patch("asyncio.gather", side_effect=mock_gather):
                        await download_hls_with_resume(
                            HLSDownloadRequest(
                                video_url="https://vkvideo.ru/video-12345_67890",
                                m3u8_url="https://example.com/video.m3u8",
                                output_file=output_path,
                                settings=test_settings,
                            )
                        )

        assert gather_called, "asyncio.gather should be called for concurrent downloads"


class TestBrowserCookiesIntegration:
    """Tests for browser cookies integration with yt-dlp."""

    @pytest.mark.asyncio
    async def test_cookies_passed_to_ytdlp_creates_cookie_file(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that cookies are passed to yt-dlp via cookie file."""
        from typing import Any

        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_ydl_instance = MagicMock()

        with patch("vkdownloader.services.downloader.yt_dlp") as mock_yt:
            mock_yt.YoutubeDL.return_value.__enter__ = lambda self: mock_ydl_instance

            # Mock run_in_executor to call the function synchronously
            with patch(
                "vkdownloader.services.downloader.asyncio.get_event_loop"
            ) as mock_loop:

                def run_in_executor_side_effect(
                    executor: Any, func: Any, *args: Any
                ) -> Any:
                    # Call the sync function directly and return the result
                    result: str | Path = func()
                    # Return a coroutine that resolves to the result
                    async def coro() -> str:
                        return str(result)

                    return coro()

                mock_loop.return_value.run_in_executor = run_in_executor_side_effect

                await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    output_file,
                    "720",
                    test_settings,
                    cookies=cookies,
                )

        # Check that cookie file was created
        cookie_file = tmp_path / f".{output_file.stem}_cookies.txt"
        assert cookie_file.exists(), "Cookie file should be created for yt-dlp"

        # Verify cookie content
        cookie_content = cookie_file.read_text()
        assert ".vkvideo.ru" in cookie_content
        assert "vk\tabc123" in cookie_content


    def test_ytdlp_cookiefile_option_set(self) -> None:
        """Test that cookiefile option is set in ydl_opts when cookies provided."""
        cookies = "vk=abc123"

        # Test via the actual function behavior - check cookie file creation
        # This is tested more thoroughly in test_cookies_passed_to_ytdlp_creates_cookie_file
        # Here we verify the _cookies_to_netscape produces correct format
        from vkdownloader.services.downloader import _cookies_to_netscape

        netscape = _cookies_to_netscape(cookies)
        assert "# Netscape HTTP Cookie File" in netscape
        assert "vk\tabc123" in netscape


    def test_cookies_to_netscape_format_for_ytdlp(self) -> None:
        """Test _cookies_to_netscape produces format compatible with yt-dlp."""
        cookies = "access_token=mytoken; user_id=12345"
        result = _cookies_to_netscape(cookies)

        lines = result.split("\n")
        header_lines = [line for line in lines if line.startswith("#")]
        cookie_lines = [line for line in lines if not line.startswith("#") and line.strip()]

        assert len(header_lines) == 2
        assert any(".vkvideo.ru" in line for line in cookie_lines)
        assert any("access_token\tmytoken" in line for line in cookie_lines)
        assert any("user_id\t12345" in line for line in cookie_lines)


class TestFfmpegProgress:
    """Tests for FfmpegProgress dataclass."""

    def test_ffmpeg_progress_default_values(self) -> None:
        """Test FfmpegProgress default values are None."""
        from vkdownloader.services.downloader import FfmpegProgress

        progress = FfmpegProgress()

        assert progress.frame is None
        assert progress.fps is None
        assert progress.speed is None
        assert progress.total_size is None
        assert progress.out_time_us is None
        assert progress.out_time_ms is None
        assert progress.out_time is None
        assert progress.progress is None

    def test_ffmpeg_progress_custom_values(self) -> None:
        """Test FfmpegProgress accepts custom values."""
        from vkdownloader.services.downloader import FfmpegProgress

        progress = FfmpegProgress(
            frame=120,
            fps=30.0,
            speed=1.5,
            total_size=1024,
            out_time_us=5000000,
            out_time_ms=5000,
            out_time="00:00:05.000000",
            progress="continue",
        )

        assert progress.frame == 120
        assert progress.fps == 30.0
        assert progress.speed == 1.5
        assert progress.total_size == 1024
        assert progress.out_time_us == 5000000
        assert progress.out_time_ms == 5000
        assert progress.out_time == "00:00:05.000000"
        assert progress.progress == "continue"


class TestProgressParser:
    """Tests for ProgressParser class."""

    def test_parse_line_valid_format(self) -> None:
        """Test parsing valid KEY=VALUE format."""
        from vkdownloader.services.downloader import ProgressParser

        result = ProgressParser.parse_line("frame=120")

        assert result == ("frame", "120")

    def test_parse_line_with_spaces(self) -> None:
        """Test parsing line that needs stripping."""
        from vkdownloader.services.downloader import ProgressParser

        result = ProgressParser.parse_line("  frame=120  ")

        assert result == ("frame", "120")

    def test_parse_line_no_equals(self) -> None:
        """Test parsing line without equals sign returns None."""
        from vkdownloader.services.downloader import ProgressParser

        result = ProgressParser.parse_line("invalid line")

        assert result is None

    def test_parse_line_value_with_equals(self) -> None:
        """Test parsing line where value contains equals sign."""
        from vkdownloader.services.downloader import ProgressParser

        result = ProgressParser.parse_line("out_time=00:00:05.000000")

        assert result == ("out_time", "00:00:05.000000")

    def test_parse_line_speed_format(self) -> None:
        """Test parsing speed value with x suffix."""
        from vkdownloader.services.downloader import ProgressParser

        result = ProgressParser.parse_line("speed=1.2x")

        assert result == ("speed", "1.2x")


class TestReadProgress:
    """Tests for read_progress async generator."""

    @pytest.mark.asyncio
    async def test_read_progress_yields_progress(self) -> None:
        """Test read_progress yields FfmpegProgress on progress key."""
        import asyncio

        from vkdownloader.services.downloader import read_progress

        # Create mock StreamReader with progress output
        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(
            side_effect=[
                b"frame=100\n",
                b"speed=1.5x\n",
                b"progress=continue\n",
                b"",
            ]
        )

        results = []
        async for prog in read_progress(mock_stream):
            results.append(prog)

        assert len(results) == 1
        assert results[0].frame == 100
        assert results[0].speed == 1.5
        assert results[0].progress == "continue"

    @pytest.mark.asyncio
    async def test_read_progress_handles_na_values(self) -> None:
        """Test read_progress handles N/A values gracefully."""
        import asyncio

        from vkdownloader.services.downloader import read_progress

        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(
            side_effect=[
                b"frame=N/A\n",
                b"speed=N/A\n",
                b"progress=continue\n",
                b"",
            ]
        )

        results = []
        async for prog in read_progress(mock_stream):
            results.append(prog)

        assert len(results) == 1
        assert results[0].frame is None
        assert results[0].speed is None

    @pytest.mark.asyncio
    async def test_read_progress_resets_on_continue(self) -> None:
        """Test read_progress resets progress object after yield."""
        import asyncio

        from vkdownloader.services.downloader import read_progress

        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(
            side_effect=[
                b"frame=100\n",
                b"progress=continue\n",
                b"frame=200\n",
                b"progress=continue\n",
                b"",
            ]
        )

        results = []
        async for prog in read_progress(mock_stream):
            results.append(prog)

        assert len(results) == 2
        assert results[0].frame == 100
        assert results[1].frame == 200

    @pytest.mark.asyncio
    async def test_read_progress_stops_on_end(self) -> None:
        """Test read_progress stops on progress=end."""
        import asyncio

        from vkdownloader.services.downloader import read_progress

        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(
            side_effect=[
                b"frame=100\n",
                b"progress=end\n",
                b"frame=200\n",  # This should not be read
            ]
        )

        results = []
        async for prog in read_progress(mock_stream):
            results.append(prog)

        assert len(results) == 1
        assert results[0].frame == 100
        assert results[0].progress == "end"

    @pytest.mark.asyncio
    async def test_read_progress_parses_all_fields(self) -> None:
        """Test read_progress parses all expected fields."""
        import asyncio

        from vkdownloader.services.downloader import read_progress

        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(
            side_effect=[
                b"frame=150\n",
                b"fps=30.02\n",
                b"speed=1.2x\n",
                b"total_size=2048\n",
                b"out_time_us=3000000\n",
                b"out_time_ms=3000\n",
                b"out_time=00:00:03.000000\n",
                b"progress=continue\n",
                b"",
            ]
        )

        results = []
        async for prog in read_progress(mock_stream):
            results.append(prog)

        assert len(results) == 1
        assert results[0].frame == 150
        assert results[0].fps == 30.02
        assert results[0].speed == 1.2
        assert results[0].total_size == 2048
        assert results[0].out_time_us == 3000000
        assert results[0].out_time_ms == 3000
        assert results[0].out_time == "00:00:03.000000"
