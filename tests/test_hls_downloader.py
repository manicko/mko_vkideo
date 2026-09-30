"""Tests for HLSDownloader service with ffmpeg integration."""

import asyncio
import os
from os import PathLike
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import QualityNotAvailableError
from vkdownloader.models.dtos import HLSDownloadRequest
from vkdownloader.models.enums import CookieSource, QualityEnum, StreamFormat
from vkdownloader.models.video import Stream
from vkdownloader.services.cookies import _cookies_to_netscape, _sanitize_cookie_value
from vkdownloader.services.downloader import (
    FfmpegProgress,
    HLSDownloader,
    _build_ytdlp_cli_command,
    _cleanup_segments,
    _create_temp_cookie_file,
    _format_argfile,
    _parse_m3u8_segments,
    _parse_quality_to_enum,
    _parse_ytdlp_progress,
    _resolve_cookies,
    _temp_argfile,
    download_hls_with_resume,
)
from vkdownloader.services.downloader_throttle import get_shutdown_event
from vkdownloader.services.ffmpeg_utils import (
    _merge_segments_batched,
    check_ffmpeg_available,
    iter_process_lines,
)
from vkdownloader.services.quality import QualitySelector
from vkdownloader.services.segment_downloader import (
    PlaylistFetchResult,
    _download_segment,
    _download_segment_parallel,
    _download_segment_sequential,
    _is_retryable_status,
)
from vkdownloader.services.signal_handlers import setup_signal_handlers


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
    async def test_error_handling_ffmpeg_failure_sanitizes_url_in_error(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test ffmpeg failure error_msg is URL-sanitized (SEC-002)."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        mock_process = AsyncMock()

        async def mock_wait() -> int:
            return 1

        mock_process.wait = mock_wait
        mock_process.returncode = 1
        mock_stderr = AsyncMock()
        # ffmpeg echoes the m3u8 URL with CDN tokens in error output
        error_text = (
            b"Error opening 'https://cdn.example.com/stream.m3u8?sig=secret_token': Invalid data"
        )
        mock_stderr.readline = AsyncMock(side_effect=[error_text, b""])
        mock_process.stderr = mock_stderr

        with (
            patch("asyncio.create_subprocess_exec", return_value=mock_process),
            patch("vkdownloader.services.downloader.logger") as mock_logger,
        ):
            result = await downloader.download_with_ffmpeg(
                "https://example.com/video.m3u8", output_path, "720"
            )

            assert result is None
            # The error log call should have sanitized URLs in the error field
            error_calls = [
                call
                for call in mock_logger.error.call_args_list
                if call.args[0] == "ffmpeg_download_failed"
            ]
            assert len(error_calls) == 1
            error_value = error_calls[0].kwargs.get("error", "")
            assert "sig=secret_token" not in error_value, "Token should not appear in logged error"
            assert "cdn.example.com" in error_value, "Host should be preserved for debugging"

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
                "https://example.com/video.m3u8",
                output_path,
                "720",
                progress_callback=progress_callback,
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
    async def test_download_with_ffmpeg_uses_argfile_syntax(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test download_with_ffmpeg uses ffmpeg @argfile to hide m3u8 URL and cookies."""
        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"
        cookies = "vk=secret123; session=xyz789"
        m3u8_url = "https://example.com/video.m3u8?token=abc123"

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
                m3u8_url,
                output_path,
                "720",
                cookies=cookies,
            )

        assert result == output_path
        # Verify ffmpeg is invoked with @argfile syntax
        assert len(captured_args) == 2  # ["ffmpeg", "@/path/to/argfile.args"]
        assert captured_args[0] == "ffmpeg"
        assert captured_args[1].startswith("@")
        argfile_path = Path(captured_args[1][1:])  # Strip the @ prefix
        # The argfile should have been cleaned up by now
        assert not argfile_path.exists(), "Argfile should be cleaned up after download"

        # Verify cookies and m3u8 URL tokens do NOT appear in command-line args
        all_args_str = " ".join(captured_args)
        assert "secret123" not in all_args_str, (
            "Cookie value should not appear in process arguments"
        )
        assert "xyz789" not in all_args_str, "Session value should not appear in process arguments"
        assert "abc123" not in all_args_str, "CDN token should not appear in process arguments"


class TestDownloadHlsWithResume:
    """Tests for download_hls_with_resume segment-level resume functionality."""

    @pytest.mark.asyncio
    async def test_preserves_segments_on_playlist_fetch_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test segments are preserved when playlist fetch fails for resume."""
        output_path = tmp_path / "video.mp4"
        segments_dir = tmp_path / ".video_segments"

        # Pre-create segments dir to simulate partial state
        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_bytes(b"fake segment data")

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\nseg3.ts\nseg4.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
        ):
            result = await download_hls_with_resume(
                HLSDownloadRequest(
                    video_url="https://vkvideo.ru/video-12345_67890",
                    m3u8_url="https://example.com/video.m3u8",
                    output_file=output_path,
                ),
                settings=test_settings,
            )

        assert result is None
        # Segments directory should be preserved for resume
        assert segments_dir.exists(), "Segments directory should be preserved for resume"

    @pytest.mark.asyncio
    async def test_preserves_segments_on_segment_download_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test segments are preserved when segment download fails for resume."""
        output_path = tmp_path / "video.mp4"
        segments_dir = tmp_path / ".video_segments"

        # Pre-create segments dir to simulate partial state
        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00000.ts").write_bytes(b"fake segment data")

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts",
                base_url="https://example.com/playlist.m3u8",
            ),
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
                    ),
                    settings=test_settings,
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


class TestCleanupSegments:
    """Tests for _cleanup_segments helper function."""

    def test_cleanup_removes_segment_files(self, tmp_path: Path) -> None:
        """Test that cleanup removes segment files."""
        segments_dir = tmp_path / ".segments"

        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_text("segment data")
        (segments_dir / "00002.ts").write_text("segment data")

        _cleanup_segments(segments_dir)

        assert not segments_dir.exists()

    def test_cleanup_handles_non_empty_directory(self, tmp_path: Path) -> None:
        """Test cleanup removes all files in segments directory."""
        segments_dir = tmp_path / ".segments"

        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_text("segment data")
        (segments_dir / "batch.txt").write_text("batch file")

        _cleanup_segments(segments_dir)

        assert not segments_dir.exists()


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

    def test_strips_crlf_from_cookie_values(self) -> None:
        """Test that CRLF characters are stripped from cookie values (SEC-007).

        CRLF injection could create extra cookie lines in the Netscape file.
        After stripping, injected content stays on the same line as the
        cookie value and does not form a separate cookie entry.
        """
        cookies = "vk=abc\r\nSet-Cookie: evil=hack; session=xyz"
        result = _cookies_to_netscape(cookies)

        # Count non-empty, non-comment lines — should be exactly 2 (vk + session)
        lines = result.split("\n")
        cookie_lines = [line for line in lines if line.strip() and not line.startswith("#")]
        assert len(cookie_lines) == 2, (
            f"Expected 2 cookie lines, got {len(cookie_lines)}: {cookie_lines}"
        )
        # No extra newline should create a separate Set-Cookie line
        for line in cookie_lines:
            assert not line.startswith("Set-Cookie"), (
                "CRLF injection created a separate cookie line"
            )

    def test_strips_crlf_from_cookie_objects(self) -> None:
        """Test CRLF stripping for Playwright Cookie objects (SEC-007)."""
        cookies = [
            {"name": "vk", "value": "abc\r\nSet-Cookie: evil=hack", "domain": ".vkvideo.ru"},
            {"name": "session", "value": "xyz", "domain": ".vkvideo.ru"},
        ]
        result = _cookies_to_netscape(cookies)

        # Should have exactly 2 cookie lines, no injected line
        lines = result.split("\n")
        cookie_lines = [line for line in lines if line.strip() and not line.startswith("#")]
        assert len(cookie_lines) == 2
        for line in cookie_lines:
            assert not line.startswith("Set-Cookie"), (
                "CRLF injection created a separate cookie line"
            )
        # The value with stripped CRLF should contain the injected text as part of the value
        assert "Set-Cookie" in cookie_lines[0]  # It's in the value, not on its own line
        assert "abcSet-Cookie: evil=hack" in cookie_lines[0]  # CRLF removed, text preserved


class TestCreateTempCookieFile:
    """Direct unit tests for _create_temp_cookie_file (TST-004)."""

    def test_writes_netscape_format_content(self) -> None:
        """Test that the file contains valid Netscape HTTP Cookie File format."""
        cookies = "vk=abc123; session=xyz789"
        result = _create_temp_cookie_file(cookies)

        try:
            content = result.read_text()
            assert "# Netscape HTTP Cookie File" in content
            assert "# Generated by vkdownloader" in content
            assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tvk\tabc123" in content
            assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession\txyz789" in content
        finally:
            result.unlink(missing_ok=True)

    def test_file_created_in_system_temp_dir(self) -> None:
        """Test that the cookie file is created in the system temp directory,
        not in the download output directory."""
        import tempfile as _tempfile

        temp_dir = _tempfile.gettempdir()
        cookies = "vk=test"
        result = _create_temp_cookie_file(cookies)

        try:
            assert str(result).startswith(temp_dir)
            # Ensure file is NOT in a typical download output directory
            assert result.parent == Path(temp_dir)
        finally:
            result.unlink(missing_ok=True)

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Owner-only confinement is not offered on Windows: os.chmod there toggles "
        "only the read-only attribute, so the measured mode is 0o666 rather than the "
        "requested 0o600 (D-11).",
    )
    def test_file_permissions_are_0600(self) -> None:
        """Test that the temp cookie file is created with 0o600 permissions (DF-007)."""
        cookies = "vk=sensitive_session_token"
        result = _create_temp_cookie_file(cookies)

        try:
            stat_info = os.stat(result)
            # DF-007: permissions should be 0o600 (owner read/write only)
            actual_mode = stat_info.st_mode & 0o777
            assert actual_mode == 0o600, f"Expected 0o600 permissions, got 0o{actual_mode:o}"
        finally:
            result.unlink(missing_ok=True)

    def test_cleanup_on_write_error(self) -> None:
        """Test that temp file is cleaned up when os.write fails."""
        import tempfile as _tempfile

        cookies = "vk=abc"
        original_mkstemp = _tempfile.mkstemp

        # Track temp files created so we can assert cleanup
        created_paths: list[Path] = []

        def tracking_mkstemp(
            suffix: str | None = "",
            prefix: str | None = "",
            dir: str | PathLike[str] | None = None,
            text: bool = False,
        ) -> tuple[int, str]:
            fd, path = original_mkstemp(suffix=suffix, prefix=prefix, dir=dir, text=text)
            created_paths.append(Path(path))
            return fd, path

        with (
            patch("vkdownloader.services.ytdlp_downloader.tempfile.mkstemp", tracking_mkstemp),
            patch(
                "vkdownloader.services.ytdlp_downloader.os.write",
                side_effect=OSError("simulated write failure"),
            ),
        ):
            with pytest.raises(OSError):
                _create_temp_cookie_file(cookies)

        # Verify the temp file was cleaned up on write failure
        assert len(created_paths) == 1
        assert not created_paths[0].exists(), (
            f"Temp file {created_paths[0]} should have been cleaned up on write failure"
        )

    def test_file_has_vc_prefix(self) -> None:
        """Test that the temp file name contains the vk_cookies prefix."""
        cookies = "vk=test"
        result = _create_temp_cookie_file(cookies)

        try:
            assert result.name.startswith("vk_cookies_")
            assert ".cookies.txt" in result.name
        finally:
            result.unlink(missing_ok=True)

    def test_handles_empty_cookies(self) -> None:
        """Test that empty cookies produces a valid file with header only."""
        result = _create_temp_cookie_file("")

        try:
            content = result.read_text()
            assert "# Netscape HTTP Cookie File" in content
            assert "# Generated by vkdownloader" in content
            # Should have only header lines, no cookie entries
            lines = content.split("\n")
            cookie_lines = [line for line in lines if line.strip() and not line.startswith("#")]
            assert len(cookie_lines) == 0
        finally:
            result.unlink(missing_ok=True)


class TestSanitizeCookieValue:
    """Tests for _sanitize_cookie_value CRLF injection prevention (SEC-007)."""

    def test_strips_crlf(self) -> None:
        """Test that \\r\\n is stripped from values."""
        assert _sanitize_cookie_value("abc\r\ndef") == "abcdef"

    def test_strips_cr_only(self) -> None:
        """Test that \\r alone is stripped."""
        assert _sanitize_cookie_value("abc\rdef") == "abcdef"

    def test_strips_lf_only(self) -> None:
        """Test that \\n alone is stripped."""
        assert _sanitize_cookie_value("abc\ndef") == "abcdef"

    def test_preserves_clean_value(self) -> None:
        """Test that values without CRLF are unchanged."""
        assert _sanitize_cookie_value("normal_value_123") == "normal_value_123"

    def test_handles_empty_string(self) -> None:
        """Test that empty string is handled."""
        assert _sanitize_cookie_value("") == ""


class TestTempArgfile:
    """Tests for _temp_argfile and _format_argfile (SEC-001)."""

    def test_format_argfile_simple_args(self) -> None:
        """Test _format_argfile produces correct content for simple args."""
        args = ["-y", "-progress", "pipe:2", "-nostats"]
        result = _format_argfile(args)

        assert result == "-y\n-progress\npipe:2\n-nostats\n"

    def test_format_argfile_quotes_args_with_spaces(self) -> None:
        """Test _format_argfile quotes arguments containing spaces."""
        args = ["-y", "arg with spaces", "-c"]
        result = _format_argfile(args)

        lines = result.strip().split("\n")
        assert lines[1].startswith("'")  # shlex single-quotes args with spaces
        assert " " in lines[1]

    def test_format_argfile_preserves_urls(self) -> None:
        """Test _format_argfile preserves URL content (quoted if needed)."""
        args = ["-i", "https://cdn.example.com/stream.m3u8?sig=abc123"]
        result = _format_argfile(args)

        # The URL appears in the argfile content (not in cmdline)
        assert "https://cdn.example.com/stream.m3u8?sig=abc123" in result

    @pytest.mark.asyncio
    async def test_temp_argfile_creates_and_cleans_up(self) -> None:
        """Test _temp_argfile creates file and cleans up."""
        args = ["-y", "-i", "https://example.com/video.m3u8"]
        async with _temp_argfile(args) as argfile:
            assert argfile.exists()
            content = argfile.read_text()
            assert "https://example.com/video.m3u8" in content

        # File should be cleaned up after context exit
        assert not argfile.exists()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        os.name == "nt",
        reason="Owner-only confinement is not offered on Windows: os.chmod there toggles "
        "only the read-only attribute, so the measured mode is 0o666 rather than the "
        "requested 0o600 (D-11).",
    )
    async def test_temp_argfile_permissions_are_0600(self) -> None:
        """Test _temp_argfile creates the argument file with 0o600 permissions (SEC-001)."""
        args = ["-y", "-i", "https://example.com/video.m3u8"]
        async with _temp_argfile(args) as argfile:
            mode = os.stat(argfile).st_mode & 0o777
            assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"


class TestFfmpegCookiePassing:
    """Tests for INT-001: ffmpeg cookie passing via `cookies` protocol option."""

    @pytest.mark.asyncio
    async def test_download_with_ffmpeg_uses_cookies_protocol_option(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """INT-001: cookies passed via `cookies=file:` in URL, not -headers @file."""
        from vkdownloader.services.downloader import HLSDownloader

        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"
        cookies = "vk=secret123; session=xyz789"
        m3u8_url = "https://example.com/video.m3u8?token=abc123"

        mock_process = AsyncMock()

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(return_value=b"")
        mock_process.stderr = mock_stderr

        captured_args: list[str] = []
        captured_argfile_content: list[str] = []

        async def mock_create_subprocess_exec(*args: str, **kwargs: Any) -> AsyncMock:
            captured_args.extend(args)
            # Read argfile content immediately before it's cleaned up
            argfile_path = args[1][1:]  # Strip @ prefix
            captured_argfile_content.append(Path(argfile_path).read_text())
            return mock_process

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            result = await downloader.download_with_ffmpeg(
                m3u8_url,
                output_path,
                "720",
                cookies=cookies,
            )

        assert result == output_path
        # Command should be: ffmpeg @argfile
        assert captured_args[0] == "ffmpeg"
        argfile_content = captured_argfile_content[0]

        # The URL in the argfile should contain cookies=file:... (INT-001 fix)
        assert "cookies=file:" in argfile_content, (
            "m3u8 URL should include cookies=file: protocol option"
        )
        # The headers should be a plain string (not @file)
        assert "-headers" in argfile_content
        lines = argfile_content.split("\n")
        headers_idx = lines.index("-headers")
        headers_value = lines[headers_idx + 1]
        assert not headers_value.startswith("@"), (
            "Headers should be a plain string, not @file reference (INT-001 fix)"
        )
        # Cookie value should NOT appear in headers (it's in the cookie file)
        assert "secret123" not in headers_value

    @pytest.mark.asyncio
    async def test_download_with_ffmpeg_no_cookies_no_cookies_param(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """INT-001: when no cookies provided, cookies=file: is not added to URL."""
        from vkdownloader.services.downloader import HLSDownloader

        downloader = HLSDownloader(settings=test_settings)
        output_path = tmp_path / "video.mp4"
        m3u8_url = "https://example.com/video.m3u8?token=abc123"

        mock_process = AsyncMock()

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        mock_stderr.readline = AsyncMock(return_value=b"")
        mock_process.stderr = mock_stderr

        captured_args: list[str] = []
        captured_argfile_content: list[str] = []

        async def mock_create_subprocess_exec(*args: str, **kwargs: Any) -> AsyncMock:
            captured_args.extend(args)
            argfile_path = args[1][1:]
            captured_argfile_content.append(Path(argfile_path).read_text())
            return mock_process

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            result = await downloader.download_with_ffmpeg(
                m3u8_url,
                output_path,
                "720",
                cookies=None,
            )

        assert result == output_path
        argfile_content = captured_argfile_content[0]
        assert "cookies=file:" not in argfile_content


class TestYtdlpCliCommand:
    """Tests for yt-dlp CLI command builder."""

    def test_cli_command_includes_throttled_rate(self, test_settings: Settings) -> None:
        """Test CLI command includes --throttled-rate from settings."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--throttled-rate" in cmd
        idx = cmd.index("--throttled-rate")
        assert cmd[idx + 1] == str(test_settings.throttled_rate)

    def test_cli_command_excludes_http_chunk_size_by_default(self, test_settings: Settings) -> None:
        """Test CLI command does NOT include --http-chunk-size by default.

        The --http-chunk-size flag forces range-request-based downloading of HLS
        segments, which can cause silent data corruption on CDNs that do not
        properly support HTTP Range headers. Disabled by default (http_chunk_size=0).
        """
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--http-chunk-size" not in cmd

    def test_cli_command_includes_http_chunk_size_when_enabled(self) -> None:
        """Test CLI command includes --http-chunk-size when explicitly set > 0."""
        custom_settings = Settings(http_chunk_size=10485760)
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=custom_settings.user_agent,
            settings=custom_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--http-chunk-size" in cmd
        idx = cmd.index("--http-chunk-size")
        assert cmd[idx + 1] == "10485760"

    def test_cli_command_custom_values(self) -> None:
        """Test CLI command accepts custom settings values."""
        custom_settings = Settings(
            max_concurrent_downloads=8, throttled_rate=200000, http_chunk_size=5242880
        )

        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=custom_settings.user_agent,
            settings=custom_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "-N" in cmd
        idx = cmd.index("-N")
        assert cmd[idx + 1] == "8"

        idx = cmd.index("--throttled-rate")
        assert cmd[idx + 1] == "200000"

        idx = cmd.index("--http-chunk-size")
        assert cmd[idx + 1] == "5242880"

    def test_cli_command_no_certificates_when_ssl_verify_false(
        self, test_settings: Settings
    ) -> None:
        """Test --no-check-certificates is added when ssl_verify is False."""
        settings = test_settings.model_copy(update={"ssl_verify": False})
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=settings.user_agent,
            settings=settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--no-check-certificates" in cmd

    def test_cli_command_no_certificates_absent_when_ssl_verify_true(
        self, test_settings: Settings
    ) -> None:
        """Test --no-check-certificates is absent when ssl_verify is True (default)."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--no-check-certificates" not in cmd

    def test_cli_command_includes_user_agent_and_referer(self, test_settings: Settings) -> None:
        """Test CLI command includes --user-agent and --referer."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent="TestAgent/1.0",
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--user-agent" in cmd
        idx = cmd.index("--user-agent")
        assert cmd[idx + 1] == "TestAgent/1.0"

        assert "--referer" in cmd
        idx = cmd.index("--referer")
        assert cmd[idx + 1] == "https://vkvideo.ru/"

    def test_cli_command_includes_newline_flag(self, test_settings: Settings) -> None:
        """Test CLI command includes --newline for parseable progress output."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--newline" in cmd

    def test_cli_command_includes_output_and_format(self, test_settings: Settings) -> None:
        """Test CLI command includes -o output_file and -f format selector."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "-o" in cmd
        idx = cmd.index("-o")
        assert cmd[idx + 1] == str(Path("/tmp/test.mp4"))

        assert "-f" in cmd
        idx = cmd.index("-f")
        assert "best[height<=720]" in cmd[idx + 1]

    def test_cli_command_format_best_when_quality_not_digit(self, test_settings: Settings) -> None:
        """Test format selector is 'best' when quality is non-numeric."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="best",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "-f" in cmd
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "best"

    def test_cli_command_uses_python_module(self, test_settings: Settings) -> None:
        """Test CLI command uses sys.executable -m yt_dlp for environment consistency."""
        import sys

        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert cmd[0] == sys.executable
        assert cmd[1] == "-u"
        assert cmd[2] == "-m"
        assert cmd[3] == "yt_dlp"

    def test_cli_command_includes_hls_prefer_native(self, test_settings: Settings) -> None:
        """Test CLI command includes --hls-prefer-native for native HLS with cookie support."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--hls-prefer-native" in cmd

    def test_cli_command_does_not_include_no_part(self, test_settings: Settings) -> None:
        """Test CLI command does not include --no-part (lets yt-dlp use .part files)."""
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "--no-part" not in cmd

    def test_cli_command_creates_cookie_file_for_cookies(self, test_settings: Settings) -> None:
        """Test CLI command creates cookie file and adds --cookies flag when raw_cookies provided."""
        from playwright.async_api import Cookie

        raw_cookies = [
            Cookie(
                name="vk",
                value="abc123",
                domain="vkvideo.ru",
                path="/",
            )
        ]
        cmd, cookie_file = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=raw_cookies,
        )

        assert cookie_file is not None
        assert cookie_file.exists()
        assert "--cookies" in cmd
        idx = cmd.index("--cookies")
        assert cmd[idx + 1] == str(cookie_file)

    def test_cli_command_creates_cookie_file_for_string_cookies(
        self, test_settings: Settings
    ) -> None:
        """Test CLI command creates cookie file for string cookies."""
        cmd, cookie_file = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="720",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies="vk=abc123",
            raw_cookies=None,
        )

        assert cookie_file is not None
        assert cookie_file.exists()
        assert "--cookies" in cmd


class TestYtdlpProgressParsing:
    """Tests for _parse_ytdlp_progress."""

    def test_parse_progress_mib(self) -> None:
        """Test parsing progress line with MiB total."""
        line = "[download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        # 649.37 * 1024 * 1024 bytes
        assert total == int(649.37 * 1024 * 1024)
        # downloaded = total * 40.3 / 100
        assert downloaded == int(total * 40.3 / 100)

    def test_parse_progress_kib(self) -> None:
        """Test parsing progress line with KiB total."""
        line = "[download]   10.0% of 500.00KiB at 100.00KiB/s ETA 00:04"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert total == 500 * 1024
        assert downloaded == 50 * 1024

    def test_parse_progress_gib(self) -> None:
        """Test parsing progress line with GiB total."""
        line = "[download]   50.0% of 1.50GiB at 1.00MiB/s ETA 00:08"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert total == int(1.50 * 1024**3)
        assert downloaded == total // 2

    def test_parse_progress_gb(self) -> None:
        """Test parsing progress line with GB (SI) total."""
        line = "[download]   25.0% of 2.00GB at 5.00MB/s ETA 00:60"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert total == 2_000_000_000
        assert downloaded == 500_000_000

    def test_parse_progress_100_percent(self) -> None:
        """Test parsing progress line at 100%."""
        line = "[download]  100.0% of 100.00MiB at 2.00MiB/s ETA 00:00"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert downloaded == total

    def test_parse_non_progress_line_returns_none(self) -> None:
        """Test non-progress lines return None."""
        assert _parse_ytdlp_progress("[download] Destination: /tmp/video.mp4") is None
        assert _parse_ytdlp_progress("ERROR: Unable to download") is None
        assert _parse_ytdlp_progress("") is None

    def test_parse_100_percent_with_mb_unit(self) -> None:
        """Test parsing 100% with MB unit."""
        line = "[download]  100.0% of 100.00MB at 2.00MB/s ETA 00:00"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert total == 100_000_000
        assert downloaded == total

    def test_parse_progress_eta_dash_format(self) -> None:
        """Test parsing progress with dash ETA (eta exceeds 99 hours)."""
        line = "[download]   0.0% of    4.93GiB at   10.37KiB/s ETA --:--:--"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert total == int(4.93 * 1024**3)
        assert downloaded == 0

    def test_parse_progress_eta_unknown_speed(self) -> None:
        """Test parsing progress with Unknown speed and ETA (just started)."""
        line = "[download]   0.0% of    4.93GiB at  Unknown B/s ETA Unknown"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert total == int(4.93 * 1024**3)
        assert downloaded == 0

    def test_parse_progress_hh_mm_ss_eta(self) -> None:
        """Test parsing progress with HH:MM:SS ETA format."""
        line = "[download]   30.0% of 1.50GiB at 1.00MiB/s ETA 01:01:00"
        result = _parse_ytdlp_progress(line)
        assert result is not None
        downloaded, total = result
        assert total == int(1.50 * 1024**3)
        assert downloaded == int(total * 30.0 / 100)


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
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\nseg3.ts\nseg4.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
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
                        ),
                        settings=test_settings,
                    )

        # Verify all segments were downloaded
        assert download_count == 4

    @pytest.mark.asyncio
    async def test_parallel_download_uses_gather(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that parallel download downloads all segments via gather."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

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
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts",
                base_url="https://example.com/playlist.m3u8",
            ),
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
                        ),
                        settings=test_settings,
                    )

        # Verify all segments were downloaded (gather is invoked internally)
        assert download_count == 2

    @pytest.mark.asyncio
    async def test_shared_semaphore_parameter(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """D-01: caller's video permit is passed in but not consumed by segment download."""
        import asyncio

        from vkdownloader.services.downloader import download_hls_with_resume

        test_settings = Settings(max_concurrent_downloads=4)

        output_path = tmp_path / "video.mp4"

        # Create a video semaphore with different limit
        video_semaphore = asyncio.Semaphore(2)

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

        # Hold all permits to prove the segment layer does not acquire from the
        # caller's video semaphore (D-01: non-reentrant semaphore would deadlock).
        await video_semaphore.acquire()
        await video_semaphore.acquire()
        initial_value = video_semaphore._value

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=mock_download_segment,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
                    return_value=output_path,
                ):
                    # Call with video semaphore parameter
                    result = await asyncio.wait_for(
                        download_hls_with_resume(
                            HLSDownloadRequest(
                                video_url="https://vkvideo.ru/video-12345_67890",
                                m3u8_url="https://example.com/video.m3u8",
                                output_file=output_path,
                            ),
                            settings=test_settings,
                            video_semaphore=video_semaphore,
                        ),
                        timeout=10,
                    )

        # Segment layer must complete without acquiring from the caller's semaphore
        assert result == output_path
        assert download_count == 2
        assert video_semaphore._value == initial_value


class TestBrowserCookiesIntegration:
    """Tests for browser cookies integration with yt-dlp."""

    @pytest.mark.asyncio
    async def test_cookies_passed_to_ytdlp_creates_cookie_file(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that cookies are passed to yt-dlp via cookie file and cleaned up."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        # Track the command that was passed to create_subprocess_exec
        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
            await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                output_file,
                "720",
                test_settings,
                cookies=cookies,
            )

        # Verify --cookies flag was in the command
        assert "--cookies" in captured_cmd
        cookies_idx = captured_cmd.index("--cookies")
        cookie_file_path = Path(captured_cmd[cookies_idx + 1])
        # Cookie file should have been cleaned up after download completes
        assert not cookie_file_path.exists(), "Cookie file should be cleaned up after download"

        # Verify the cookie format is correct
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
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
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
                    with patch(
                        "vkdownloader.services.segment_downloader.get_shutdown_event",
                        return_value=mock_shutdown_event,
                    ):
                        with patch("asyncio.wait_for", side_effect=mock_wait_for):
                            await download_hls_with_resume(
                                HLSDownloadRequest(
                                    video_url="https://vkvideo.ru/video-12345_67890",
                                    m3u8_url="https://example.com/video.m3u8",
                                    output_file=output_path,
                                ),
                                settings=test_settings,
                            )

        # Verify delay was called for each segment in sequential mode (max_concurrent_downloads=1)
        assert len(wait_for_calls) == 2, "Should have wait_for call for each segment"
        # Each delay should be approximately 1.5-2.0 seconds (1.5 + 0-0.5 jitter)
        for delay in wait_for_calls:
            assert 1.4 <= delay <= 2.1, f"Delay should be ~1.5s + jitter, got {delay}"

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
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
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
                with patch(
                    "vkdownloader.services.segment_downloader.get_shutdown_event",
                    return_value=mock_shutdown_event,
                ):
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
                                ),
                                settings=test_settings,
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
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\nseg3.ts\nseg4.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
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
                    with patch(
                        "vkdownloader.services.segment_downloader.get_shutdown_event",
                        return_value=mock_shutdown_event,
                    ):
                        with patch("asyncio.wait_for", side_effect=mock_wait_for):
                            await download_hls_with_resume(
                                HLSDownloadRequest(
                                    video_url="https://vkvideo.ru/video-12345_67890",
                                    m3u8_url="https://example.com/video.m3u8",
                                    output_file=output_path,
                                ),
                                settings=test_settings,
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
            return_value=MagicMock(
                streams=[MagicMock(url="https://example.com/video.m3u8", quality="720")]
            ),
        ):
            with patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=(
                    [MagicMock(url="https://example.com/video.m3u8", quality="720")],
                    "cookies",
                ),
            ):
                with patch(
                    "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                    return_value=output_file,
                ):
                    with patch(
                        "vkdownloader.services.downloader.logger.info", side_effect=capture_log
                    ):
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
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
            ) as mock_download:
                # Create a side effect that writes segment files (needed for on-disk count)
                def download_side_effect(
                    session: Any,
                    segment_url: str,
                    output_path: Path,
                    headers: dict[str, str],
                    **kwargs: Any,
                ) -> bool:
                    output_path.write_bytes(b"segment data")
                    return True

                mock_download.side_effect = download_side_effect
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
                    with patch(
                        "vkdownloader.services.segment_downloader.get_shutdown_event",
                        return_value=mock_shutdown_event,
                    ):
                        with patch(
                            "vkdownloader.services.segment_downloader.logger.info",
                            side_effect=capture_log,
                        ):
                            result = await download_hls_with_resume(
                                HLSDownloadRequest(
                                    video_url="https://vkvideo.ru/video-12345_67890",
                                    m3u8_url="https://example.com/video.m3u8",
                                    output_file=output_file,
                                ),
                                settings=test_settings,
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

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch(
                "vkdownloader.services.ytdlp_downloader.logger.info", side_effect=capture_log
            ):
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
            return_value=MagicMock(
                streams=[MagicMock(url="https://example.com/video.m3u8", quality="720")]
            ),
        ):
            with patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=(
                    [MagicMock(url="https://example.com/video.m3u8", quality="720")],
                    "cookies",
                ),
            ):
                with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                    with patch(
                        "vkdownloader.services.downloader.logger.info", side_effect=capture_log
                    ):
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

    @pytest.mark.asyncio
    async def test_perform_download_ffmpeg_progress_adapter_sends_unknown_total(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that the ffmpeg progress adapter passes total=0 (not 100%) for ffmpeg downloads (SRV-003)."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.services.downloader import perform_download

        output_file = tmp_path / "video_720p.mp4"

        # Capture what progress_callback receives: (video_id, downloaded, total)
        progress_calls: list[tuple[str, int, int]] = []

        def progress_callback(video_id: str, downloaded: int, total: int) -> None:
            progress_calls.append((video_id, downloaded, total))

        mock_process = AsyncMock()

        async def mock_wait() -> int:
            return 0

        mock_process.wait = mock_wait
        mock_process.returncode = 0
        mock_stderr = AsyncMock()
        # FFmpeg emits total_size as cumulative bytes (not final total).
        # The adapter should report total=0 to avoid false 100%.
        progress_lines = [
            b"out_time_ms=5000\n",
            b"total_size=1024\n",
            b"progress=continue\n",
            b"out_time_ms=10000\n",
            b"total_size=2048\n",
            b"progress=continue\n",
            b"",  # EOF
        ]
        mock_stderr.readline = AsyncMock(side_effect=progress_lines)
        mock_process.stderr = mock_stderr

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=MagicMock(
                streams=[MagicMock(url="https://example.com/video.m3u8", quality="720")]
            ),
        ):
            with patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=(
                    [MagicMock(url="https://example.com/video.m3u8", quality="720")],
                    "cookies",
                ),
            ):
                with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                    result = await perform_download(
                        "https://vkvideo.ru/video-12345_67890",
                        "720",
                        output_file,
                        DownloadMethod.FFMPEG,
                        settings=test_settings,
                        progress_callback=progress_callback,
                    )

        assert result == output_file
        assert len(progress_calls) >= 1, "Progress callback should have been called"

        # SRV-003: total must be 0 (unknown), not equal to downloaded (which would show 100%)
        for _video_id, downloaded, total in progress_calls:
            assert total == 0, (
                f"Expected total=0 (unknown total), got total={total} (would show 100%)"
            )
            assert downloaded > 0, f"Expected downloaded > 0, got {downloaded}"

    @pytest.mark.asyncio
    async def test_perform_download_ffmpeg_falls_back_to_segment_download(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test perform_download falls back to segment download when ffmpeg returns None."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.services.downloader import perform_download

        output_file = tmp_path / "video_720p.mp4"

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=MagicMock(
                streams=[MagicMock(url="https://example.com/video.m3u8", quality="720")]
            ),
        ):
            with patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=(
                    [MagicMock(url="https://example.com/video.m3u8", quality="720")],
                    "cookies",
                ),
            ):
                # ffmpeg branch returns None -> should trigger segment-download fallback
                with patch(
                    "vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg",
                    return_value=None,
                ) as mock_ffmpeg:
                    with patch(
                        "vkdownloader.services.downloader.download_hls_with_resume",
                        return_value=output_file,
                    ) as mock_segment_fallback:
                        result = await perform_download(
                            "https://vkvideo.ru/video-12345_67890",
                            "720",
                            output_file,
                            DownloadMethod.FFMPEG,
                            settings=test_settings,
                        )

        # ffmpeg branch was attempted first
        mock_ffmpeg.assert_awaited_once()
        # segment-download fallback ran and produced the result
        mock_segment_fallback.assert_awaited_once()
        request = mock_segment_fallback.call_args[0][0]
        assert isinstance(request, HLSDownloadRequest)
        assert request.output_file == output_file
        assert result == output_file


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


class TestIterProcessLines:
    """Tests for the shared iter_process_lines utility (STR-008)."""

    @pytest.mark.asyncio
    async def test_yields_lines_until_eof(self) -> None:
        """Test that iter_process_lines yields all lines until empty (EOF)."""
        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(side_effect=[b"line1\n", b"line2\n", b""])
        shutdown_event = asyncio.Event()

        result = [line async for line in iter_process_lines(mock_stream, shutdown_event)]
        assert result == [b"line1\n", b"line2\n"]

    @pytest.mark.asyncio
    async def test_breaks_on_shutdown(self) -> None:
        """Test that iteration stops when shutdown_event is set."""
        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(side_effect=[b"line1\n", b"line2\n", b""])
        shutdown_event = asyncio.Event()

        # With shutdown already set, should break immediately without reading
        shutdown_event.set()

        result = [line async for line in iter_process_lines(mock_stream, shutdown_event)]
        assert result == []

    @pytest.mark.asyncio
    async def test_invokes_on_shutdown_callback(self) -> None:
        """Test that on_shutdown callback is invoked when shutdown is detected."""
        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        shutdown_event = asyncio.Event()
        callback_called = []

        async def on_shutdown() -> None:
            callback_called.append(True)

        shutdown_event.set()
        result = [
            line
            async for line in iter_process_lines(
                mock_stream, shutdown_event, on_shutdown=on_shutdown
            )
        ]

        assert result == []
        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_no_callback_when_shutdown_not_set(self) -> None:
        """Test that on_shutdown is not called when shutdown is never set."""
        mock_stream = AsyncMock(spec=asyncio.StreamReader)
        mock_stream.readline = AsyncMock(side_effect=[b"line1\n", b""])
        shutdown_event = asyncio.Event()
        callback_called = []

        async def on_shutdown() -> None:
            callback_called.append(True)

        result = [
            line
            async for line in iter_process_lines(
                mock_stream, shutdown_event, on_shutdown=on_shutdown
            )
        ]

        assert result == [b"line1\n"]
        assert callback_called == []


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
    async def test_download_segment_sequential_success(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
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
    async def test_download_segment_sequential_retries_on_429(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test _download_segment_sequential retries on 429 response."""
        segment_url = "https://example.com/segment.ts"
        output_path = tmp_path / "00000.ts"
        headers = {"User-Agent": "test-agent"}

        call_count = 0

        def make_mock_response(status_code: int) -> AsyncMock:
            response = AsyncMock()
            response.status = status_code
            response.read = AsyncMock(
                return_value=b"segment after retry" if status_code == 200 else b""
            )
            response.__aenter__ = AsyncMock(return_value=response)
            response.__aexit__ = AsyncMock(return_value=None)
            response.headers = MagicMock()
            response.headers.get = MagicMock(return_value=None)
            return response

        def mock_get(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return make_mock_response(429)
            return make_mock_response(200)

        mock_session = MagicMock()
        mock_session.get = mock_get

        with patch(
            "vkdownloader.services.downloader_throttle._wait_with_shutdown", return_value=False
        ):
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
    async def test_download_segment_sequential_fails_non_retryable(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
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
    async def test_download_segment_parallel_success(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
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
    async def test_download_segment_parallel_retries_on_503(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
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

        def mock_get(*args: object, **kwargs: object) -> MagicMock:
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
    async def test_download_segment_parallel_fails_fast_on_non_retryable(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test _download_segment_parallel fails immediately on non-retryable 403."""
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

        result = await _download_segment_parallel(
            mock_session,
            segment_url,
            output_path,
            headers,
            max_retries=3,
        )

        # Should return False immediately (fail-fast), not retry 3 times
        assert result is False
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_download_segment_main_sequential_dispatch(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
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

        with patch(
            "vkdownloader.services.downloader_throttle._wait_with_shutdown", return_value=False
        ):
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
    async def test_download_segment_main_parallel_dispatch(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
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


class TestManifestBaseAddressFeedsSegments:
    """Tests that PlaylistFetchResult.base_url flows through to segment download."""

    @pytest.mark.asyncio
    async def test_manifest_base_url_used_for_segment_resolution(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """PlaylistFetchResult.base_url feeds DownloadPolicy.m3u8_url for segment URL resolution."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

        playlist = "#EXTM3U\nseg1.ts\nseg2.ts"
        base_url = "https://cdn.example.com/hls/playlist.m3u8"
        captured_urls: list[str] = []

        async def mock_download_segment(
            session: Any,
            segment_url: str,
            output_path: Path,
            headers: dict[str, str],
            **kwargs: Any,
        ) -> bool:
            captured_urls.append(segment_url)
            output_path.write_bytes(b"segment data")
            return True

        output_path = tmp_path / "video.mp4"

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value=PlaylistFetchResult(
                playlist_text=playlist,
                base_url=base_url,
            ),
        ):
            with patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=mock_download_segment,
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._merge_segments_batched",
                    return_value=output_path,
                ):
                    result = await download_hls_with_resume(
                        HLSDownloadRequest(
                            video_url="https://vkvideo.ru/video-12345_67890",
                            m3u8_url="https://example.com/initial.m3u8",
                            output_file=output_path,
                        ),
                        settings=test_settings,
                    )

        assert result is not None
        assert len(captured_urls) == 2
        # Segments resolved relative to base_url, not the initial m3u8_url.
        assert captured_urls[0] == "https://cdn.example.com/hls/seg1.ts"
        assert captured_urls[1] == "https://cdn.example.com/hls/seg2.ts"


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

        async def mock_communicate() -> tuple[bytes, bytes]:
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

        async def mock_communicate() -> tuple[bytes, bytes]:
            return b"", b""

        mock_process.communicate = mock_communicate

        def track_batch(*cmd: str, **kwargs: object) -> MagicMock:
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


class TestSetupSignalHandlers:
    """Tests for setup_signal_handlers Windows fallback branch."""

    @pytest.mark.asyncio
    async def test_windows_fallback_registers_signal_handlers(self) -> None:
        """Test that platforms without loop.add_signal_handler support fall
        back to signal.signal for SIGINT and SIGTERM."""
        import signal as signal_module

        from vkdownloader.services import signal_handlers

        class _FakeLoop:
            def add_signal_handler(self, sig: object, handler: object) -> None:
                raise NotImplementedError("signal only works in main thread")

            def remove_signal_handler(self, sig: object) -> None:
                raise NotImplementedError("signal only works in main thread")

        with patch.object(asyncio, "get_running_loop", return_value=_FakeLoop()):
            with patch.object(signal_module, "signal") as mock_signal:
                setup_signal_handlers()

                # SIGINT and SIGTERM must be registered via the signal.signal fallback
                assert mock_signal.call_count == 2
                registered = {call.args[0] for call in mock_signal.call_args_list}
                assert signal_module.SIGINT in registered
                assert signal_module.SIGTERM in registered
            # Reset module state so other tests are unaffected
            signal_handlers.cleanup_signal_handlers()

    @pytest.mark.asyncio
    async def test_registered_handler_triggers_shutdown(self) -> None:
        """Test that the fallback signal handler sets the shutdown event."""
        import signal as signal_module

        from vkdownloader.services import signal_handlers

        captured: dict[int, Any] = {}

        class _FakeLoop:
            def add_signal_handler(self, sig: object, handler: object) -> None:
                raise NotImplementedError("signal only works in main thread")

            def remove_signal_handler(self, sig: object) -> None:
                raise NotImplementedError("signal only works in main thread")

        def _record_signal(sig: int, handler: object) -> None:
            captured[sig] = handler

        with patch.object(asyncio, "get_running_loop", return_value=_FakeLoop()):
            with patch.object(signal_module, "signal", side_effect=_record_signal):
                setup_signal_handlers()

            shutdown_event = get_shutdown_event()
            shutdown_event.clear()
            handler = captured[signal_module.SIGINT]
            handler(signal_module.SIGINT, None)
            assert shutdown_event.is_set()

            # Restore clean state
            shutdown_event.clear()
            signal_handlers.cleanup_signal_handlers()


class TestResolveCookies:
    """Tests for _resolve_cookies cookie-source branching."""

    @pytest.mark.asyncio
    async def test_non_browser_source_skips_extraction(self, test_settings: Settings) -> None:
        """Test that non-browser cookie source returns m3u8_url without cookies."""
        test_settings.cookie_source = CookieSource.NONE
        extractor = MagicMock()
        extractor.extract_streams_with_cookies = AsyncMock(return_value=([], None, None))
        m3u8_url = "https://example.com/video.m3u8"

        result = await _resolve_cookies(
            extractor, test_settings, "https://vkvideo.ru/video-1_2", m3u8_url, "best"
        )

        assert result == (m3u8_url, None, None)
        extractor.extract_streams_with_cookies.assert_not_called()

    @pytest.mark.asyncio
    async def test_browser_source_best_quality_selects_stream(
        self, test_settings: Settings
    ) -> None:
        """Test browser source with BEST quality selects a stream and returns cookies."""
        test_settings.cookie_source = CookieSource.BROWSER
        stream = Stream(
            url="https://example.com/best.m3u8",
            format=StreamFormat.HLS,
            quality="best",
            height=1080,
        )
        raw_cookies = [MagicMock()]
        extractor = MagicMock()
        extractor.extract_streams_with_cookies = AsyncMock(
            return_value=([stream], "vk=abc", raw_cookies)
        )
        m3u8_url = "https://example.com/preselected.m3u8"

        result = await _resolve_cookies(
            extractor, test_settings, "https://vkvideo.ru/video-1_2", m3u8_url, "best"
        )

        assert result[0] == "https://example.com/best.m3u8"
        assert result[1] == "vk=abc"
        assert result[2] == raw_cookies
        extractor.extract_streams_with_cookies.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_browser_source_numeric_quality_keeps_preselected_url(
        self, test_settings: Settings
    ) -> None:
        """Test numeric quality reuses caller's preselected m3u8_url (no select)."""
        test_settings.cookie_source = CookieSource.BROWSER
        stream = Stream(
            url="https://example.com/best.m3u8",
            format=StreamFormat.HLS,
            quality="best",
            height=1080,
        )
        extractor = MagicMock()
        extractor.extract_streams_with_cookies = AsyncMock(
            return_value=([stream], "vk=abc", [MagicMock()])
        )
        m3u8_url = "https://example.com/preselected.m3u8"

        with patch.object(QualitySelector, "select") as mock_select:
            result = await _resolve_cookies(
                extractor, test_settings, "https://vkvideo.ru/video-1_2", m3u8_url, "720"
            )

        # Preselected URL is reused; quality selection must not run for numeric quality.
        assert result[0] == m3u8_url
        assert result[1] == "vk=abc"
        mock_select.assert_not_called()

    @pytest.mark.asyncio
    async def test_browser_source_no_streams_returns_none_cookies(
        self, test_settings: Settings
    ) -> None:
        """Test browser source with no streams returns m3u8_url and None cookies."""
        test_settings.cookie_source = CookieSource.BROWSER
        extractor = MagicMock()
        extractor.extract_streams_with_cookies = AsyncMock(return_value=([], None, None))
        m3u8_url = "https://example.com/preselected.m3u8"

        result = await _resolve_cookies(
            extractor, test_settings, "https://vkvideo.ru/video-1_2", m3u8_url, "best"
        )

        assert result == (m3u8_url, None, None)
        extractor.extract_streams_with_cookies.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_quality_not_available_propagates(self, test_settings: Settings) -> None:
        """Test QualityNotAvailableError from selection propagates out of _resolve_cookies."""
        test_settings.cookie_source = CookieSource.BROWSER
        stream = Stream(
            url="https://example.com/best.m3u8",
            format=StreamFormat.HLS,
            quality="best",
            height=1080,
        )
        extractor = MagicMock()
        extractor.extract_streams_with_cookies = AsyncMock(
            return_value=([stream], "vk=abc", [MagicMock()])
        )

        class _FailingSelector:
            def select(self, streams: list[Stream], quality: QualityEnum) -> Stream:
                raise QualityNotAvailableError("best", ["720p"])

        with patch("vkdownloader.services.ytdlp_downloader.QualitySelector", _FailingSelector):
            with pytest.raises(QualityNotAvailableError):
                await _resolve_cookies(
                    extractor,
                    test_settings,
                    "https://vkvideo.ru/video-1_2",
                    "https://example.com/preselected.m3u8",
                    "best",
                )


class TestYtDlpSubprocessShutdown:
    """Tests for INT-004: yt-dlp subprocess responds to shutdown signal."""

    @pytest.mark.asyncio
    async def test_ytdlp_cancelled_on_shutdown_returns_none(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that _download_with_ytdlp returns None when shutdown_event is set."""
        from vkdownloader.services.downloader import _download_with_ytdlp
        from vkdownloader.services.downloader_throttle import get_shutdown_event

        # Set shutdown signal before download starts
        shutdown_event = get_shutdown_event()
        shutdown_event.set()

        output_file = tmp_path / "video.mp4"
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_stdout_line: list[bytes] = []

        # TST-006: Use named function instead of fragile
        # `(_ for _ in ()).throw(asyncio.CancelledError())` lambda hack
        async def mock_readline() -> bytes:
            if not mock_stdout_line:
                raise asyncio.CancelledError()
            return mock_stdout_line.pop(0)

        mock_process.stdout.readline = mock_readline
        mock_process.wait = AsyncMock(return_value=0)

        # Patch cancel_subprocess to track it's called
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch(
                "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_cancel:
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    output_file,
                    "720",
                    test_settings,
                )

        assert result is None
        # cancel_subprocess should have been called for shutdown
        mock_cancel.assert_awaited()
        shutdown_event.clear()

    @pytest.mark.asyncio
    async def test_ytdlp_subprocess_terminated_on_cancelled_error(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that CancelledError triggers process termination and re-raises."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        # Simulate the outer task being cancelled while waiting for process
        mock_process.wait = AsyncMock(side_effect=asyncio.CancelledError())

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch(
                "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_cancel:
                with pytest.raises(asyncio.CancelledError):
                    await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        output_file,
                        "720",
                        test_settings,
                    )

        mock_cancel.assert_awaited()

    @pytest.mark.asyncio
    async def test_ytdlp_returncode_nonzero_returns_none(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that non-zero returncode returns None with error logging."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[b"ERROR: video not found\n", b""])
        mock_process.wait = AsyncMock(return_value=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                output_file,
                "720",
                test_settings,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_ytdlp_stdout_progress_written_to_console(
        self, test_settings: Settings, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that yt-dlp stdout progress lines are echoed to the console."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        progress_line = b"[download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43\n"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[progress_line, b""])
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                output_file,
                "720",
                test_settings,
            )

        assert result == output_file
        captured = capsys.readouterr()
        assert "[download]" in captured.err
        assert "40.3%" in captured.err
        assert "649.37MiB" in captured.err
        assert "983.45KiB/s" in captured.err
        assert "06:43" in captured.err

    @pytest.mark.asyncio
    async def test_ytdlp_echo_false_suppresses_stderr_while_callback_fires(
        self, test_settings: Settings, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that echo=False suppresses yt-dlp console output while progress_callback still fires."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        progress_line = b"[download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43\n"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[progress_line, b""])
        mock_process.wait = AsyncMock(return_value=0)

        progress_calls: list[tuple[str, int, int]] = []

        def progress_callback(video_id: str, downloaded: int, total: int) -> None:
            progress_calls.append((video_id, downloaded, total))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger"):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    output_file,
                    "720",
                    test_settings,
                    progress_callback=progress_callback,
                    echo=False,
                )

        assert result == output_file
        captured = capsys.readouterr()
        assert "[download]" not in captured.err
        assert "40.3%" not in captured.err
        assert "649.37MiB" not in captured.err
        assert "983.45KiB/s" not in captured.err
        assert "06:43" not in captured.err
        assert len(progress_calls) == 1
        video_id, downloaded, total = progress_calls[0]
        assert video_id == "67890"
        expected_total = int(649.37 * 1024 * 1024)
        assert total == expected_total
        assert downloaded == int(expected_total * 40.3 / 100)

    @pytest.mark.asyncio
    async def test_ytdlp_echo_false_no_callback_stderr_empty(
        self, test_settings: Settings, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that echo=False suppresses all yt-dlp stderr output when no progress callback."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        progress_line = b"[download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43\n"
        other_line = b"ERROR: something went wrong\n"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[progress_line, other_line, b""])
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger"):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    output_file,
                    "720",
                    test_settings,
                    echo=False,
                )

        assert result == output_file
        captured = capsys.readouterr()
        assert captured.err == ""

    @pytest.mark.asyncio
    async def test_ytdlp_echo_false_progress_emits_debug_log(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that echo=False on a progress line emits a single ytdlp_progress_suppressed debug event."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        progress_line = b"[download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43\n"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[progress_line, b""])
        mock_process.wait = AsyncMock(return_value=0)

        debug_events: list[tuple[str, dict[str, Any]]] = []

        def capture_debug(event: str, **kwargs: Any) -> None:
            debug_events.append((event, kwargs))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch(
                "vkdownloader.services.ytdlp_downloader.logger.debug",
                side_effect=capture_debug,
            ):
                with patch("vkdownloader.services.ytdlp_downloader.logger.info"):
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        output_file,
                        "720",
                        test_settings,
                        echo=False,
                    )

        assert result == output_file
        suppressed = [
            (event, kwargs)
            for event, kwargs in debug_events
            if event == "ytdlp_progress_suppressed"
        ]
        assert len(suppressed) == 1, (
            f"Expected exactly 1 ytdlp_progress_suppressed debug call, got {len(suppressed)}"
        )
        _, kwargs = suppressed[0]
        expected_total = int(649.37 * 1024 * 1024)
        assert kwargs["total"] == expected_total
        assert kwargs["downloaded"] == int(expected_total * 40.3 / 100)

    @pytest.mark.asyncio
    async def test_ytdlp_echo_false_non_progress_line_no_output_no_log(
        self, test_settings: Settings, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that echo=False on a non-progress line writes nothing and emits no debug log."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        non_progress_line = b"[download] Destination: /tmp/video.mp4\n"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[non_progress_line, b""])
        mock_process.wait = AsyncMock(return_value=0)

        debug_events: list[tuple[str, dict[str, Any]]] = []

        def capture_debug(event: str, **kwargs: Any) -> None:
            debug_events.append((event, kwargs))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch(
                "vkdownloader.services.ytdlp_downloader.logger.debug",
                side_effect=capture_debug,
            ):
                with patch("vkdownloader.services.ytdlp_downloader.logger.info"):
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        output_file,
                        "720",
                        test_settings,
                        echo=False,
                    )

        assert result == output_file
        captured = capsys.readouterr()
        assert captured.err == ""
        assert len(debug_events) == 0, (
            "No debug log events should be emitted for non-progress lines"
        )


class TestAttemptSegmentResumeQuality:
    """Tests for _attempt_segment_resume quality handling with browser streams."""

    @pytest.mark.asyncio
    async def test_attempt_segment_resume_numeric_quality_does_not_raise(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test _attempt_segment_resume handles numeric quality without QualityNotAvailableError.

        Browser streams only have quality="best", so numeric qualities must reuse
        the pre-selected m3u8_url (mirroring the _resolve_cookies BEST-only guard).
        """
        from vkdownloader.services.downloader import _attempt_segment_resume

        output_file = tmp_path / "video.mp4"
        output_file.write_bytes(b"partial data")

        stream = Stream(
            url="https://example.com/fresh.m3u8",
            format=StreamFormat.HLS,
            quality="best",
            height=1080,
        )

        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = AsyncMock(return_value=([stream], None, None))

        with patch(
            "vkdownloader.services.ytdlp_downloader.download_hls_with_resume",
            new_callable=AsyncMock,
            return_value=output_file,
        ):
            result = await _attempt_segment_resume(
                "https://vkvideo.ru/video-12345_67890",
                "https://example.com/stale.m3u8",
                output_file,
                "1080",
                retry_count=1,
                extractor=mock_extractor,
                settings=test_settings,
                backoff_coordinator=None,
                video_semaphore=None,
            )

        assert result == output_file
        mock_extractor.extract_streams_with_cookies.assert_awaited_once_with(
            "https://vkvideo.ru/video-12345_67890", force_browser=True
        )


class TestFfmpegAvailabilityCheck:
    """Tests for INT-007: ffmpeg availability probing."""

    def test_check_ffmpeg_available_returns_bool(self) -> None:
        """Test check_ffmpeg_available returns a boolean."""
        result = check_ffmpeg_available()
        assert isinstance(result, bool)

    def test_check_ffmpeg_available_caches_result(self) -> None:
        """Test check_ffmpeg_available caches the result across calls."""
        import vkdownloader.services.ffmpeg_utils as fu

        original = fu._ffmpeg_available
        try:
            # First call should set the cache
            check_ffmpeg_available()
            assert fu._ffmpeg_available is not None

            # Subsequent calls should return the cached value
            cached = check_ffmpeg_available()
            assert cached == fu._ffmpeg_available
        finally:
            fu._ffmpeg_available = original


class TestSslVerifyFfmpegWarning:
    """Tests for INT-005: ssl_verify warning removed for ffmpeg method.

    The stale ``ssl_verify_ignored_for_ffmpeg`` warning was misleading —
    ffmpeg DOES apply ``-tls_verify 0`` when ``settings.ssl_verify=False``.
    The warning is removed; this test verifies it is no longer logged.
    """

    @pytest.mark.asyncio
    async def test_perform_download_ffmpeg_no_stale_ssl_warning(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test perform_download does NOT log ssl_verify_ignored_for_ffmpeg for ffmpeg method."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.services.downloader import perform_download

        log_messages: list[dict[str, Any]] = []

        def capture_log(msg: str, **kwargs: Any) -> None:
            log_messages.append({"message": msg, "kwargs": kwargs})

        output_file = tmp_path / "video_720p.mp4"
        ssl_settings = Settings(ssl_verify=False)

        mock_stream = MagicMock()
        mock_stream.url = "https://example.com/video.m3u8"
        mock_stream.quality = "720"

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=MagicMock(streams=[mock_stream]),
        ):
            with patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=([mock_stream], "cookies", None),
            ):
                with patch(
                    "vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg",
                    return_value=output_file,
                ):
                    with patch(
                        "vkdownloader.services.downloader.check_ffmpeg_available",
                    ):
                        with patch(
                            "vkdownloader.services.downloader.logger.warning",
                            side_effect=capture_log,
                        ):
                            result = await perform_download(
                                "https://vkvideo.ru/video-12345_67890",
                                "720",
                                output_file,
                                DownloadMethod.FFMPEG,
                                settings=ssl_settings,
                            )

        assert result == output_file
        # Verify ssl_verify warning was NOT logged (INT-005 fix)
        ssl_warnings = [m for m in log_messages if "ssl_verify_ignored_for_ffmpeg" in m["message"]]
        assert len(ssl_warnings) == 0, "Stale ssl_verify warning should not be logged"


class TestParseQualityToEnum:
    """Tests for _parse_quality_to_enum quality string parsing."""

    def test_parse_numeric_quality(self) -> None:
        """Test parsing numeric quality strings without p suffix."""
        assert _parse_quality_to_enum("720") == QualityEnum("720")
        assert _parse_quality_to_enum("1080") == QualityEnum("1080")

    def test_parse_quality_with_p_suffix(self) -> None:
        """Test parsing quality strings with p suffix are stripped."""
        assert _parse_quality_to_enum("720p") == QualityEnum("720")
        assert _parse_quality_to_enum("480p") == QualityEnum("480")

    def test_parse_named_qualities(self) -> None:
        """Test parsing named quality strings."""
        assert _parse_quality_to_enum("best") == QualityEnum.BEST
        assert _parse_quality_to_enum("worst") == QualityEnum.WORST

    def test_parse_unknown_quality_raises(self) -> None:
        """Test that unparseable quality strings raise QualityParseError."""
        from vkdownloader.exceptions import QualityParseError

        with pytest.raises(QualityParseError):
            _parse_quality_to_enum("invalid_quality")

    def test_parse_empty_quality_defaults_to_best(self) -> None:
        """Test that empty quality string defaults to BEST."""
        assert _parse_quality_to_enum("") == QualityEnum.BEST


class TestYtDlpRetryBackoff:
    """Tests for SRV-006: backoff between yt-dlp retry attempts."""

    @pytest.mark.asyncio
    async def test_backoff_between_ytdlp_retries(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that a backoff delay occurs between yt-dlp retry attempts."""
        from vkdownloader.services.downloader import download_with_ytdlp_with_resume_fallback

        output_file = tmp_path / "video.mp4"
        # Create a partial file so the retry loop doesn't exit early
        output_file.write_text("partial")

        mock_coord = AsyncMock()
        mock_coord.wait_if_paused = AsyncMock(return_value=False)

        call_count = {"n": 0}

        async def mock_download_ytdlp(*args: Any, **kwargs: Any) -> Path | None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                return None  # First attempt fails
            return output_file  # Second attempt succeeds

        with patch(
            "vkdownloader.services.ytdlp_downloader._download_with_ytdlp",
            side_effect=mock_download_ytdlp,
        ):
            with patch(
                "vkdownloader.services.ytdlp_downloader._attempt_segment_resume",
                return_value=None,  # Segment resume fails, so loop retries yt-dlp
            ):
                with patch(
                    "vkdownloader.services.ytdlp_downloader._compute_backoff_delay",
                    return_value=0.01,  # Short delay for tests
                ) as mock_compute:
                    with patch(
                        "vkdownloader.services.ytdlp_downloader._wait_with_shutdown",
                        AsyncMock(return_value=False),
                    ) as mock_wait:
                        result = await download_with_ytdlp_with_resume_fallback(
                            "https://vkvideo.ru/video-12345_67890",
                            "https://cdn.example.com/video.m3u8",
                            output_file,
                            "720",
                            None,
                            test_settings,
                            backoff_coordinator=mock_coord,
                        )

        assert result == output_file
        assert call_count["n"] == 2, "Should have retried yt-dlp after first failure"
        # Backoff should have been computed and waited between attempts
        mock_compute.assert_called()
        mock_wait.assert_called()

    @pytest.mark.asyncio
    async def test_backoff_coordinator_consulted_on_retry(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that backoff_coordinator.wait_if_paused is called between retries."""
        from vkdownloader.services.downloader import download_with_ytdlp_with_resume_fallback

        output_file = tmp_path / "video.mp4"
        output_file.write_text("partial")

        mock_coord = AsyncMock()
        mock_coord.wait_if_paused = AsyncMock(return_value=False)

        call_count = {"n": 0}

        async def mock_download_ytdlp(*args: Any, **kwargs: Any) -> Path | None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                return None
            return output_file

        with patch(
            "vkdownloader.services.ytdlp_downloader._download_with_ytdlp",
            side_effect=mock_download_ytdlp,
        ):
            with patch(
                "vkdownloader.services.ytdlp_downloader._attempt_segment_resume",
                return_value=None,
            ):
                with patch(
                    "vkdownloader.services.ytdlp_downloader._compute_backoff_delay",
                    return_value=0.01,
                ):
                    with patch(
                        "vkdownloader.services.ytdlp_downloader._wait_with_shutdown",
                        AsyncMock(return_value=False),
                    ):
                        await download_with_ytdlp_with_resume_fallback(
                            "https://vkvideo.ru/video-12345_67890",
                            "https://cdn.example.com/video.m3u8",
                            output_file,
                            "720",
                            None,
                            test_settings,
                            backoff_coordinator=mock_coord,
                        )

        # Coordinator should have been consulted during the backoff
        mock_coord.wait_if_paused.assert_called()


class TestDownloadVideoTitleCallback:
    """Tests for download_video title_callback propagation (R8/Q6/A5)."""

    @pytest.mark.asyncio
    async def test_title_callback_receives_sanitized_title(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that title_callback receives a sanitized title with special chars replaced."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.models.video import Stream, VideoWithStreams
        from vkdownloader.services.downloader import download_video

        captured: list[str] = []

        def title_callback(title: str) -> None:
            captured.append(title)

        video = VideoWithStreams(
            id="video-12345_67890",
            title="My:Crazy/Title",
            streams=[
                Stream(
                    url="https://example.com/v.m3u8",
                    format=StreamFormat.HLS,
                    quality="720",
                )
            ],
        )

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=video,
        ):
            with patch(
                "vkdownloader.services.downloader.perform_download",
                return_value=tmp_path / "video.mp4",
            ):
                result = await download_video(
                    "https://vkvideo.ru/video-12345_67890",
                    QualityEnum.Q720,
                    tmp_path,
                    DownloadMethod.YTDLP,
                    test_settings,
                    title_callback=title_callback,
                )

        assert result == tmp_path / "video.mp4"
        assert len(captured) == 1
        assert captured[0] == "My_Crazy_Title"

    @pytest.mark.asyncio
    async def test_title_callback_not_called_when_title_none(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that title_callback is not invoked when video title is None."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.models.video import Stream, VideoWithStreams
        from vkdownloader.services.downloader import download_video

        captured: list[str] = []

        def title_callback(title: str) -> None:
            captured.append(title)

        video = VideoWithStreams(
            id="video-12345_67890",
            title=None,
            streams=[
                Stream(
                    url="https://example.com/v.m3u8",
                    format=StreamFormat.HLS,
                    quality="720",
                )
            ],
        )

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=video,
        ):
            with patch(
                "vkdownloader.services.downloader.perform_download",
                return_value=tmp_path / "video.mp4",
            ):
                result = await download_video(
                    "https://vkvideo.ru/video-12345_67890",
                    QualityEnum.Q720,
                    tmp_path,
                    DownloadMethod.YTDLP,
                    test_settings,
                    title_callback=title_callback,
                )

        assert result == tmp_path / "video.mp4"
        assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_title_callback_optional_when_not_supplied(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that download_video works without title_callback and defaults echo=True."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.models.video import Stream, VideoWithStreams
        from vkdownloader.services.downloader import download_video

        video = VideoWithStreams(
            id="video-12345_67890",
            title="Some:Title",
            streams=[
                Stream(
                    url="https://example.com/v.m3u8",
                    format=StreamFormat.HLS,
                    quality="720",
                )
            ],
        )

        with patch(
            "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
            return_value=video,
        ):
            with patch(
                "vkdownloader.services.downloader.perform_download",
                return_value=tmp_path / "video.mp4",
            ) as mock_perform:
                result = await download_video(
                    "https://vkvideo.ru/video-12345_67890",
                    QualityEnum.Q720,
                    tmp_path,
                    DownloadMethod.YTDLP,
                    test_settings,
                )

        assert result == tmp_path / "video.mp4"
        assert mock_perform.call_count == 1
        # Default echo=True should be forwarded to perform_download
        assert mock_perform.call_args.kwargs["echo"] is True
