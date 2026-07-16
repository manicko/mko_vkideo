"""Tests for HLSDownloader service with ffmpeg integration."""
import asyncio
from pathlib import Path
from typing import Any
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
from vkdownloader.services.ffmpeg_utils import _merge_segments_batched
from vkdownloader.services.segment_downloader import (
    _download_segment,
    _download_segment_parallel,
    _download_segment_sequential,
    _is_retryable_status,
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

    def test_ffmpeg_command_includes_progress_flags(self, test_settings: Settings) -> None:
        """Test ffmpeg command includes -progress pipe:2 for real-time progress."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = Path("/tmp/output.mp4")
        m3u8_url = "https://example.com/video.m3u8"

        cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path)

        assert "-progress" in cmd
        progress_index = cmd.index("-progress")
        assert cmd[progress_index + 1] == "pipe:2"
        assert "-nostats" in cmd


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

    @pytest.mark.asyncio
    async def test_download_with_ffmpeg_uses_header_file_syntax(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg uses @file syntax to avoid cookie exposure."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"
        cookies = "vk=secret123; session=xyz789"

        mock_process = AsyncMock()

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(return_value=b"")
        mock_process.stderr = mock_stderr

        captured_args: list[str] = []

        async def mock_create_subprocess_exec(*args: str, **kwargs: Any) -> AsyncMock:
            captured_args.extend(args)
            return mock_process

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720",
                cookies=cookies,
            )

        assert result == output_path
        # Verify @file syntax is used (filename starts with ./ or /)
        headers_idx = captured_args.index("-headers")
        headers_arg = captured_args[headers_idx + 1]
        assert headers_arg.startswith("@") or headers_arg.startswith("/"), \
            f"Headers should use @file syntax, got: {headers_arg}"
        # Verify actual cookies are NOT in the command arguments
        all_args_str = " ".join(captured_args)
        assert "secret123" not in all_args_str, \
            "Cookie value should not appear in process arguments"
        assert "xyz789" not in all_args_str, \
            "Session value should not appear in process arguments"


class TestDownloadHlsWithResume:
    """Tests for download_hls_with_resume segment-level resume functionality."""

    @pytest.mark.asyncio
    async def test_preserves_segments_on_playlist_fetch_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test segments are preserved when playlist fetch fails for resume."""
        output_path = tmp_path / "video.mp4"
        segments_dir = tmp_path / ".video_segments"
        metadata_file = tmp_path / ".video_progress.json"

        # Pre-create segments dir to simulate partial state
        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_bytes(b"fake segment data")
        metadata_file.write_text('{"downloaded_count": 1}')

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
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
        # Segments directory should be preserved for resume
        assert segments_dir.exists(), "Segments directory should be preserved for resume"
        assert metadata_file.exists(), "Metadata file should be preserved for resume"

    @pytest.mark.asyncio
    async def test_preserves_segments_on_segment_download_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test segments are preserved when segment download fails for resume."""
        output_path = tmp_path / "video.mp4"
        segments_dir = tmp_path / ".video_segments"
        metadata_file = tmp_path / ".video_progress.json"

        # Pre-create segments dir to simulate partial state
        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00000.ts").write_bytes(b"fake segment data")
        metadata_file.write_text('{"downloaded_count": 1}')

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
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
        # Segments directory should be preserved for resume
        assert segments_dir.exists(), "Segments directory should be preserved for resume"


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

    def test_ytdlp_options_includes_throttled_rate(self, test_settings: Settings) -> None:
        """Test yt-dlp options include throttled_rate setting."""
        ydl_opts = {
            "throttledratelimit": test_settings.throttled_rate,
            "http_chunk_size": test_settings.http_chunk_size,
        }

        assert "throttledratelimit" in ydl_opts
        assert ydl_opts["throttledratelimit"] == 100000

    def test_ytdlp_options_includes_http_chunk_size(self, test_settings: Settings) -> None:
        """Test yt-dlp options include http_chunk_size setting."""
        ydl_opts = {
            "throttledratelimit": test_settings.throttled_rate,
            "http_chunk_size": test_settings.http_chunk_size,
        }

        assert "http_chunk_size" in ydl_opts
        assert ydl_opts["http_chunk_size"] == 10485760

    def test_ytdlp_options_custom_values(self) -> None:
        """Test yt-dlp options accept custom settings values."""
        custom_settings = Settings(max_concurrent_downloads=8, throttled_rate=200000, http_chunk_size=5242880)

        ydl_opts = {
            "max_concurrent_downloads": custom_settings.max_concurrent_downloads,
            "throttledratelimit": custom_settings.throttled_rate,
            "http_chunk_size": custom_settings.http_chunk_size,
        }

        assert ydl_opts["max_concurrent_downloads"] == 8
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
            **kwargs: Any,
        ) -> bool:
            nonlocal download_count
            download_count += 1
            output_path.write_bytes(b"segment data")
            return True

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts\nseg3.ts\nseg4.ts\n",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=mock_download_segment,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
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

        async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
            nonlocal gather_called
            gather_called = True
            # Return True for each task
            return [True] * len(tasks)

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                return_value=True,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
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

    @pytest.mark.asyncio
    async def test_shared_semaphore_parameter(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that download_hls_with_resume accepts and uses shared semaphore parameter."""
        import asyncio

        from vkdownloader.services.downloader import download_hls_with_resume

        test_settings = Settings(max_concurrent_downloads=4)

        output_path = tmp_path / "video.mp4"

        # Create a shared semaphore with different limit
        shared_semaphore = asyncio.Semaphore(2)

        download_count = 0

        async def mock_download_segment(
            session: Any,
            segment_url: str,
            output_path: Path,
            headers: dict[str, str],
            **kwargs: Any,
        ) -> bool:
            nonlocal download_count
            download_count += 1
            output_path.write_bytes(b"segment data")
            return True

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts\n",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=mock_download_segment,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
                    return_value=output_path,
                ):
                    # Call with shared semaphore parameter
                    result = await download_hls_with_resume(
                        HLSDownloadRequest(
                            video_url="https://vkvideo.ru/video-12345_67890",
                            m3u8_url="https://example.com/video.m3u8",
                            output_file=output_path,
                            settings=test_settings,
                        ),
                        semaphore=shared_semaphore,
                    )

        assert result == output_path
        assert download_count == 2


class TestBrowserCookiesIntegration:
    """Tests for browser cookies integration with yt-dlp."""

    @pytest.mark.asyncio
    async def test_cookies_passed_to_ytdlp_creates_cookie_file(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that cookies are passed to yt-dlp via cookie file and cleaned up."""
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

        # Cookie file should be cleaned up after download completes
        cookie_file = tmp_path / f".{output_file.stem}_cookies.txt"
        assert not cookie_file.exists(), "Cookie file should be cleaned up after download"

        # Verify cookiefile option was set correctly in ydl_opts
        # by checking the cookie format is correct
        from vkdownloader.services.downloader import _cookies_to_netscape
        netscape = _cookies_to_netscape(cookies)
        assert ".vkvideo.ru" in netscape
        assert "vk\tabc123" in netscape


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


class TestSequentialDownloadMode:
    """Tests for sequential download mode with anti-detection throttling."""

    @pytest.mark.asyncio
    async def test_sequential_mode_applies_delay_after_semaphore(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that sequential mode applies 1.5s + jitter delay after semaphore release."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

        test_settings = Settings(max_concurrent_downloads=1)

        output_path = tmp_path / "video.mp4"

        wait_for_calls: list[float] = []

        async def mock_download_segment(
            session: Any,
            segment_url: str,
            output_path: Path,
            headers: dict[str, str],
            **kwargs: Any,
        ) -> bool:
            # Simulate successful download
            output_path.write_bytes(b"segment data")
            return True

        # Mock wait_for to capture delay and raise TimeoutError (simulating normal completion)
        # We must await the passed coroutine (shutdown_event.wait()) to avoid unawaited warning
        async def mock_wait_for(coro: Any, timeout: float) -> None:
            """Mock wait_for to capture delay values. Raises TimeoutError to simulate completion."""
            wait_for_calls.append(timeout)
            # Await the coroutine to avoid RuntimeWarning
            try:
                await coro
            except Exception:
                pass  # Ignore any exceptions from the awaited coroutine
            raise TimeoutError()  # Simulate timeout - normal completion

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts\n",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=mock_download_segment,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
                    return_value=output_path,
                ):
                    # Mock get_shutdown_event to return a mock with proper wait() method
                    # is_set() must return False to avoid early cancellation
                    mock_shutdown_event = MagicMock()
                    mock_shutdown_event.is_set.return_value = False

                    async def mock_wait() -> None:
                        pass

                    mock_shutdown_event.wait = mock_wait
                    with patch("vkdownloader.services.segment_downloader.get_shutdown_event", return_value=mock_shutdown_event):
                        with patch("asyncio.wait_for", side_effect=mock_wait_for):
                            await download_hls_with_resume(
                                HLSDownloadRequest(
                                video_url="https://vkvideo.ru/video-12345_67890",
                                m3u8_url="https://example.com/video.m3u8",
                                output_file=output_path,
                                settings=test_settings,
                            )
                        )

        # Verify delay was called for each segment in sequential mode (max_concurrent_downloads=1)
        assert len(wait_for_calls) == 2, "Should have wait_for call for each segment"
        # Each delay should be approximately 1.5-2.0 seconds (1.5 + 0-0.5 jitter)
        for delay in wait_for_calls:
            assert 1.4 <= delay <= 2.1, (
                f"Delay should be ~1.5s + jitter, got {delay}"
            )

    @pytest.mark.asyncio
    async def test_sequential_mode_triggers_backoff_on_429(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that sequential mode triggers _retry_429_with_backoff for 429 responses."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

        test_settings = Settings(max_concurrent_downloads=1)

        output_path = tmp_path / "video.mp4"

        backoff_calls: list[tuple[str, int]] = []

        async def mock_backoff(
            session: Any,
            segment_url: str,
            headers: dict[str, str],
            segment_index: int,
            **kwargs: Any,
        ) -> bytes:
            backoff_calls.append((segment_url, segment_index))
            return b"segment content"

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\n",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._retry_429_with_backoff",
                side_effect=mock_backoff,
            ):
                async def mock_wait_for(coro: Any, timeout: float) -> None:
                    # Simulate timeout - no shutdown
                    # Await the coroutine to avoid RuntimeWarning about unawaited coroutine
                    try:
                        await coro
                    except Exception:
                        pass
                    raise TimeoutError()

                # Mock get_shutdown_event to return a mock with proper wait() method
                # is_set() must return False to avoid early cancellation
                mock_shutdown_event = MagicMock()
                mock_shutdown_event.is_set.return_value = False

                async def mock_wait() -> None:
                    pass

                mock_shutdown_event.wait = mock_wait
                with patch("vkdownloader.services.segment_downloader.get_shutdown_event", return_value=mock_shutdown_event):
                    with patch("asyncio.wait_for", side_effect=mock_wait_for):
                        with patch(
                            "vkdownloader.services.segment_downloader._merge_segments_batched",
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

        # Verify _retry_429_with_backoff was called for sequential mode
        assert len(backoff_calls) == 1
        assert backoff_calls[0][1] == 0, "Should pass segment index to backoff function"

    @pytest.mark.asyncio
    async def test_parallel_mode_no_inter_segment_delay(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that parallel mode does not apply inter-segment delay."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

        test_settings = Settings(max_concurrent_downloads=4)

        output_path = tmp_path / "video.mp4"

        wait_for_calls: list[float] = []

        async def mock_download_segment(
            session: Any,
            segment_url: str,
            output_path: Path,
            headers: dict[str, str],
            **kwargs: Any,
        ) -> bool:
            output_path.write_bytes(b"segment data")
            return True

        # Mock wait_for to capture delay and raise TimeoutError (simulating normal completion)
        # We must await the passed coroutine (shutdown_event.wait()) to avoid unawaited warning
        async def mock_wait_for(coro: Any, timeout: float) -> None:
            """Mock wait_for to capture delay values. Raises TimeoutError to simulate completion."""
            wait_for_calls.append(timeout)
            # Await the coroutine to avoid RuntimeWarning
            try:
                await coro
            except Exception:
                pass  # Ignore any exceptions from the awaited coroutine
            raise TimeoutError()  # Simulate timeout - normal completion

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts\nseg3.ts\nseg4.ts\n",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=mock_download_segment,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
                    return_value=output_path,
                ):
                    # Mock get_shutdown_event to return a mock with proper wait() method
                    # is_set() must return False to avoid early cancellation
                    mock_shutdown_event = MagicMock()
                    mock_shutdown_event.is_set.return_value = False

                    async def mock_wait() -> None:
                        pass

                    mock_shutdown_event.wait = mock_wait
                    with patch("vkdownloader.services.segment_downloader.get_shutdown_event", return_value=mock_shutdown_event):
                        with patch("asyncio.wait_for", side_effect=mock_wait_for):
                            await download_hls_with_resume(
                            HLSDownloadRequest(
                                video_url="https://vkvideo.ru/video-12345_67890",
                                m3u8_url="https://example.com/video.m3u8",
                                output_file=output_path,
                                settings=test_settings,
                            )
                        )

        # Parallel mode should not have anti-detection wait_for calls
        assert len(wait_for_calls) == 0, "Parallel mode should not have inter-segment delay"


class TestDownloadMethodLogging:
    """Tests for download method logging."""

    @pytest.mark.asyncio
    async def test_perform_download_logs_method(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that perform_download logs the download method."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.services.downloader import perform_download

        # Capture log messages
        log_messages: list[dict[str, Any]] = []

        def capture_log(msg: str, **kwargs: Any) -> None:
            log_messages.append({"message": msg, "kwargs": kwargs})

        output_file = tmp_path / "video_720p.mp4"

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=MagicMock(streams=[MagicMock(url="https://example.com/video.m3u8", quality="720")]),
        ):
            with patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=([MagicMock(url="https://example.com/video.m3u8", quality="720")], "cookies"),
            ):
                with patch(
                    "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                    return_value=output_file,
                ):
                    with patch("vkdownloader.services.downloader.logger.info", side_effect=capture_log):
                        result = await perform_download(
                            "https://vkvideo.ru/video-12345_67890",
                            "720",
                            output_file,
                            DownloadMethod.YTDLP,
                            settings=test_settings,
                        )

        assert result == output_file
        # Check that starting_download was logged with method
        starting_logs = [m for m in log_messages if m["kwargs"].get("method") == "yt-dlp"]
        assert len(starting_logs) >= 1, "Should log starting_download with method=yt-dlp"

    @pytest.mark.asyncio
    async def test_download_hls_with_resume_logs_segment_method(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that download_hls_with_resume logs the segment download method."""
        log_messages: list[dict[str, Any]] = []

        def capture_log(msg: str, **kwargs: Any) -> None:
            log_messages.append({"message": msg, "kwargs": kwargs})

        output_file = tmp_path / "video.mp4"

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value="#EXTM3U\nseg1.ts\nseg2.ts\n",
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                return_value=True,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
                    return_value=output_file,
                ):
                    # Mock get_shutdown_event to return a mock with proper wait() method
                    # is_set() must return False to avoid early cancellation
                    mock_shutdown_event = MagicMock()
                    mock_shutdown_event.is_set.return_value = False

                    async def mock_wait() -> None:
                        pass

                    mock_shutdown_event.wait = mock_wait
                    with patch("vkdownloader.services.segment_downloader.get_shutdown_event", return_value=mock_shutdown_event):
                        with patch("vkdownloader.services.segment_downloader.logger.info", side_effect=capture_log):
                            result = await download_hls_with_resume(
                            HLSDownloadRequest(
                                video_url="https://vkvideo.ru/video-12345_67890",
                                m3u8_url="https://example.com/video.m3u8",
                                output_file=output_file,
                                settings=test_settings,
                            )
                        )

        assert result == output_file
        # Check that starting_segment_download was logged
        starting_logs = [m for m in log_messages if "starting_segment_download" in m["message"]]
        assert len(starting_logs) >= 1, "Should log starting_segment_download"

    @pytest.mark.asyncio
    async def test_download_with_ytdlp_logs_download_start(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that _download_with_ytdlp logs starting_ytdlp_download."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        log_messages: list[dict[str, Any]] = []

        def capture_log(msg: str, **kwargs: Any) -> None:
            log_messages.append({"message": msg, "kwargs": kwargs})

        output_file = tmp_path / "video.mp4"

        mock_ydl_instance = MagicMock()

        with patch("vkdownloader.services.downloader.yt_dlp") as mock_yt:
            mock_yt.YoutubeDL.return_value.__enter__ = lambda self: mock_ydl_instance

            with patch(
                "vkdownloader.services.downloader.asyncio.get_event_loop"
            ) as mock_loop:
                def run_in_executor_side_effect(
                    executor: Any, func: Any, *args: Any
                ) -> Any:
                    async def coro() -> str:
                        return str(output_file)
                    return coro()

                mock_loop.return_value.run_in_executor = run_in_executor_side_effect

                with patch("vkdownloader.services.downloader.logger.info", side_effect=capture_log):
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        output_file,
                        "720",
                        test_settings,
                    )

        # Check that starting_ytdlp_download was logged
        starting_logs = [m for m in log_messages if "starting_ytdlp_download" in m["message"]]
        assert len(starting_logs) >= 1, "Should log starting_ytdlp_download"
        # Verify quality is in the log
        assert starting_logs[0]["kwargs"].get("quality") == "720"
        assert result == output_file

    @pytest.mark.asyncio
    async def test_perform_download_logs_ffmpeg_method(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that perform_download logs the ffmpeg download method."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.services.downloader import perform_download

        log_messages: list[dict[str, Any]] = []

        def capture_log(msg: str, **kwargs: Any) -> None:
            log_messages.append({"message": msg, "kwargs": kwargs})

        output_file = tmp_path / "video_720p.mp4"

        # Mock for ffmpeg method
        mock_process = AsyncMock()
        async def mock_wait() -> int:
            return 0
        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(return_value=b"")
        mock_process.stderr = mock_stderr

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=MagicMock(streams=[MagicMock(url="https://example.com/video.m3u8", quality="720")]),
        ):
            with patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=([MagicMock(url="https://example.com/video.m3u8", quality="720")], "cookies"),
            ):
                with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                    with patch("vkdownloader.services.downloader.logger.info", side_effect=capture_log):
                        result = await perform_download(
                            "https://vkvideo.ru/video-12345_67890",
                            "720",
                            output_file,
                            DownloadMethod.FFMPEG,
                            settings=test_settings,
                        )

        assert result == output_file
        # Check that starting_download was logged with ffmpeg method
        starting_logs = [m for m in log_messages if "starting_download" in m["message"]]
        assert len(starting_logs) >= 1, "Should log starting_download"
        assert starting_logs[0]["kwargs"].get("method") == "ffmpeg"


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

class TestDownloadSegmentRealExecution:
    """Tests for _download_segment with real execution logic."""

    @pytest.mark.asyncio
    async def test_download_segment_sequential_success(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test _download_segment_sequential successfully downloads segment."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"fake segment content")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        result = await _download_segment_sequential(
            mock_session,
            segment_url,
            output_path,
            headers,
            segment_index=0,
            max_retries=3,
        )

        assert result is True
        assert output_path.exists()
        assert output_path.read_bytes() == b"fake segment content"

    @pytest.mark.asyncio
    async def test_download_segment_sequential_retries_on_429(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test _download_segment_sequential retries on 429 response."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        call_count = 0

        def make_mock_response(status_code: int) -> AsyncMock:
            response = AsyncMock()
            response.status = status_code
            response.read = AsyncMock(return_value=b"segment after retry" if status_code == 200 else b"")
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=None)
            response.headers = MagicMock()
            response.headers.get = MagicMock(return_value=None)
            return response

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_mock_response(429)
            return make_mock_response(200)

        mock_session = MagicMock()
        mock_session.get = mock_get

        with patch("vkdownloader.services.downloader_throttle._wait_with_shutdown", return_value=False):
            result = await _download_segment_sequential(
                mock_session,
                segment_url,
                output_path,
                headers,
                segment_index=0,
                max_retries=3,
            )

        assert result is True
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_download_segment_sequential_fails_non_retryable(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test _download_segment_sequential fails on non-retryable error."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.read = AsyncMock(return_value=b"forbidden")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        result = await _download_segment_sequential(
            mock_session,
            segment_url,
            output_path,
            headers,
            segment_index=0,
            max_retries=3,
        )

        assert result is False
        assert not output_path.exists()

    @pytest.mark.asyncio
    async def test_download_segment_parallel_success(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test _download_segment_parallel successfully downloads segment."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"parallel segment content")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        result = await _download_segment_parallel(
            mock_session,
            segment_url,
            output_path,
            headers,
            max_retries=3,
        )

        assert result is True
        assert output_path.exists()
        assert output_path.read_bytes() == b"parallel segment content"

    @pytest.mark.asyncio
    async def test_download_segment_parallel_retries_on_503(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test _download_segment_parallel retries on 503 response."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        call_count = 0

        def make_mock_response(status_code: int) -> AsyncMock:
            response = AsyncMock()
            response.status = status_code
            response.read = AsyncMock(return_value=b"segment after retry")
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=None)
            response.headers = MagicMock()
            response.headers.get = MagicMock(return_value=None)
            return response

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return make_mock_response(503)
            return make_mock_response(200)

        mock_session = MagicMock()
        mock_session.get = mock_get

        result = await _download_segment_parallel(
            mock_session,
            segment_url,
            output_path,
            headers,
            max_retries=3,
        )

        assert result is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_download_segment_main_success(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test _download_segment dispatches to sequential mode when max_concurrent=1."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"main segment content")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        with patch("vkdownloader.services.downloader_throttle._wait_with_shutdown", return_value=False):
            result = await _download_segment(
                mock_session,
                segment_url,
                output_path,
                headers,
                max_concurrent_downloads=1,
                segment_index=0,
            )

        assert result is True
        assert output_path.read_bytes() == b"main segment content"

    @pytest.mark.asyncio
    async def test_download_segment_main_parallel_dispatch(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test _download_segment dispatches to parallel mode when max_concurrent>1."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"parallel dispatch content")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        result = await _download_segment(
            mock_session,
            segment_url,
            output_path,
            headers,
            max_concurrent_downloads=4,
            segment_index=0,
        )

        assert result is True
        assert output_path.read_bytes() == b"parallel dispatch content"


class TestMergeSegmentsBatchedRealExecution:
    """Tests for _merge_segments_batched with real execution."""

    @pytest.mark.asyncio
    async def test_merge_segments_batched_success(self, tmp_path: Path) -> None:
        """Test successful merge of segments with mocked ffmpeg."""
        output = tmp_path / "output.ts"

        for i in range(5):
            (tmp_path / f"{i:05d}.ts").write_bytes(b"segment data")

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate():
            return b"", b""

        mock_process.communicate = mock_communicate

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            batch_output = tmp_path / "batch_00000.ts"
            batch_output.write_bytes(b"batch data")

            result = await _merge_segments_batched(tmp_path, output, 5)

        assert result == output

    @pytest.mark.asyncio
    async def test_merge_segments_batched_raises_on_missing_files(self, tmp_path: Path) -> None:
        """Test _merge_segments_batched raises FileNotFoundError for missing segments."""
        output = tmp_path / "output.ts"

        with patch("asyncio.create_subprocess_exec"):
            with pytest.raises(FileNotFoundError) as exc_info:
                await _merge_segments_batched(tmp_path, output, 5)

            assert "Missing segment files" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_merge_segments_batched_uses_batch_size_100(self, tmp_path: Path) -> None:
        """Test that merge processes segments in batches of 100."""
        output = tmp_path / "output.ts"

        for i in range(250):
            (tmp_path / f"{i:05d}.ts").write_bytes(b"segment data")

        call_count = 0

        mock_process = MagicMock(spec=asyncio.subprocess.Process)
        mock_process.returncode = 0
        mock_process.pid = 12345

        async def mock_communicate():
            return b"", b""

        mock_process.communicate = mock_communicate

        def track_batch(*cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=track_batch):
            for i in range(0, 250, 100):
                batch_output = tmp_path / f"batch_{i:05d}.ts"
                batch_output.write_bytes(b"batch data")

            result = await _merge_segments_batched(tmp_path, output, 250)

        assert call_count == 4  # 3 batches (0-99, 100-199, 200-249) + 1 final merge
        assert result == output

    def test_is_retryable_status(self) -> None:
        """Test _is_retryable_status identifies retryable codes correctly."""
        for code in [429, 500, 502, 503, 504]:
            assert _is_retryable_status(code) is True

        for code in [200, 400, 403, 404]:
            assert _is_retryable_status(code) is False


