"""Tests for download service, ytdlp/segment download paths, and utilities."""

import asyncio
import logging
import os
import sys
from os import PathLike
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import structlog
from aiohttp import web
from aiohttp.test_utils import TestServer
from pydantic import SecretStr

from vkdownloader.config import Settings, setup_logging
from vkdownloader.exceptions import (
    DownloadError,
    ExtractionError,
    QualityNotAvailableError,
)
from vkdownloader.models.dtos import HLSDownloadRequest
from vkdownloader.models.enums import CookieSource, LogLevel, QualityKind, StreamFormat
from vkdownloader.models.quality import QualitySpec
from vkdownloader.models.video import Stream
from vkdownloader.services.cookies import _cookies_to_netscape, _sanitize_cookie_value
from vkdownloader.services.downloader import (
    _build_ytdlp_cli_command,
    _cleanup_segments,
    _create_temp_cookie_file,
    _echo_ytdlp_line,
    _is_ytdlp_progress_line,
    _parse_m3u8_segments,
    _parse_ytdlp_progress,
    _resolve_cookies,
    download_hls_with_resume,
)
from vkdownloader.services.downloader_throttle import get_shutdown_event
from vkdownloader.services.ffmpeg_utils import (
    _SPAWN_BOUNDARY_KWARGS,
    _merge_segments_batched,
    cancel_subprocess,
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

    @pytest.mark.asyncio
    async def test_resume_with_all_segments_present_merges_without_download(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """CON-006: when all segments already exist on disk, no download tasks
        are created, yet _tally_and_merge still runs the merge from the on-disk
        count.

        Pre-fix code returned None for an empty task list, skipping the merge
        entirely.
        """
        output_path = tmp_path / "video.mp4"
        segments_dir = output_path.parent / ".video_segments"

        # Pre-create both segment files so _iter_pending_segment_tasks
        # produces zero tasks в†’ _await_and_cancel returns NOTHING_TO_DO.
        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00000.ts").write_bytes(b"segment 0 data")
        (segments_dir / "00001.ts").write_bytes(b"segment 1 data")

        with patch(
            "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
            return_value=PlaylistFetchResult(
                playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\n",
                base_url="https://example.com/playlist.m3u8",
            ),
        ):
            with patch(
                "vkdownloader.services.segment_downloader._clear_stale_segments",
            ):
                with patch(
                    "vkdownloader.services.segment_downloader._download_segment",
                    new_callable=AsyncMock,
                ) as mock_download:
                    with patch(
                        "vkdownloader.services.segment_downloader._merge_segments_batched",
                        return_value=output_path,
                    ) as mock_merge:
                        result = await asyncio.wait_for(
                            download_hls_with_resume(
                                HLSDownloadRequest(
                                    video_url="https://vkvideo.ru/video-12345_67890",
                                    m3u8_url="https://example.com/video.m3u8",
                                    output_file=output_path,
                                ),
                                settings=test_settings,
                            ),
                            timeout=5.0,
                        )

        assert result == output_path
        mock_download.assert_not_called()
        mock_merge.assert_called_once()


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

    def test_cleanup_skips_non_regular_entries(self, tmp_path: Path) -> None:
        """Non-regular entries (subdirectories) are left untouched by _cleanup_segments.

        The ``is_file()`` guard skips anything that is not a regular file,
        so a stray subdirectory inside the segments dir survives the unlink sweep.
        Because the directory is not empty after the sweep, ``rmdir()`` fails
        silently and the segments dir itself is preserved.
        """
        segments_dir = tmp_path / ".segments"

        segments_dir.mkdir(parents=True, exist_ok=True)
        (segments_dir / "00001.ts").write_text("segment data")
        subdir = segments_dir / "subdir"
        subdir.mkdir()

        _cleanup_segments(segments_dir)

        # Regular file was cleaned up.
        assert not (segments_dir / "00001.ts").exists()
        # Non-regular entry (subdirectory) was skipped, not removed.
        assert subdir.exists(), "subdirectory should be skipped by is_file() guard"
        # Segments dir still exists because it contains the subdir (rmdir fails).
        assert segments_dir.exists(), (
            "segments dir with surviving subdir should not be removed by rmdir"
        )


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

    def test_file_created_in_private_cookie_subdir(self) -> None:
        """The cookie file must be created in a private subdirectory of the
        system temp dir, not directly in the shared temp root.

        This is the Windows-executable oracle for SEC-001's confinement:
        the artefact's parent is a directory this process created, not the
        shared temp root. The original assertion ``result.parent == temp_dir``
        is intentionally reversed to ``result.parent != temp_dir``.
        """
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _COOKIE_ARTIFACT_DIRS,
            _remove_cookie_artifact_dir,
        )

        temp_dir = Path(_tempfile.gettempdir())
        cookies = "vk=test"
        result = _create_temp_cookie_file(cookies)

        try:
            # The cookie file must NOT sit directly in the shared system temp root.
            assert result.parent != temp_dir, (
                "cookie file must not sit directly in the shared system temp root"
            )
            # The cookie file's parent must be a strict descendant of the temp dir.
            assert temp_dir in result.parent.parents, (
                "cookie file directory must be a strict descendant of the system temp dir"
            )
            # The containing directory must be one this process created.
            assert result.parent in _COOKIE_ARTIFACT_DIRS
            result.unlink(missing_ok=True)
            _remove_cookie_artifact_dir(result.parent)
            assert not result.parent.exists(), (
                "cookie artefact directory must be removed after teardown"
            )
        finally:
            result.unlink(missing_ok=True)

    def test_file_permissions_are_0600(self) -> None:
        """Test that the temp cookie file has 0o600 permissions (DF-007).

        POSIX: ``_create_temp_cookie_file`` calls ``os.chmod(path, 0o600)`` and
        ``st_mode & 0o777 == 0o600`` is asserted.

        Windows: ``tempfile.mkstemp`` is wrapped so the file is pre-marked
        read-only (0o444) after the descriptor opens, then the read-only
        attribute is asserted clear after ``os.chmod(path, 0o600)`` runs.
        Owner-only confinement is not guaranteed on Windows (D-11): the
        assertion targets the cleared attribute, not POSIX permission bits.

        R1/R2 confinement properties are already covered by the following
        tests, not duplicated here: ``test_file_created_in_private_cookie_subdir``,
        ``test_remove_cookie_artifact_dir_removes_created_dir``,
        ``test_full_round_trip_removes_parent_dir``, the nine
        ``TestCookieArtefactLifecycle`` tests, and
        ``TestCookieArtefactCreationRaceAcrossProcesses``.
        """
        from vkdownloader.services.ytdlp_downloader import _remove_cookie_artifact_dir

        cookies = "vk=sensitive_session_token"

        if os.name != "nt":
            result = _create_temp_cookie_file(cookies)
            try:
                stat_info = os.stat(result)
                # DF-007: permissions should be 0o600 (owner read/write only)
                actual_mode = stat_info.st_mode & 0o777
                assert actual_mode == 0o600, f"Expected 0o600 permissions, got 0o{actual_mode:o}"
            finally:
                result.unlink(missing_ok=True)
        else:
            # Alt B: pre-mark the file read-only after mkstemp opens the fd.
            import tempfile as _tempfile

            _original_mkstemp = _tempfile.mkstemp

            def _ro_mkstemp(*args: Any, **kwargs: Any) -> tuple[int, str]:
                fd, path = _original_mkstemp(*args, **kwargs)
                os.chmod(path, 0o444)
                return fd, path

            with patch("vkdownloader.services.ytdlp_downloader.tempfile.mkstemp", _ro_mkstemp):
                result = _create_temp_cookie_file(cookies)

            try:
                assert getattr(os.stat(result), "st_file_attributes", 0) & 0x1 == 0, (
                    "read-only attribute should be cleared after chmod(0o600)"
                )
            finally:
                os.chmod(result, 0o600)
                _remove_cookie_artifact_dir(result.parent)

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
            max_concurrent_segments=8, throttled_rate=200000, http_chunk_size=5242880
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

    def test_cli_command_format_best_for_best_quality(self, test_settings: Settings) -> None:
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

    def test_cli_command_format_worst_for_worst_quality(self, test_settings: Settings) -> None:
        """Test format selector is 'worst' when quality is the keyword 'worst'."""
        from vkdownloader.services.ytdlp_downloader import _resolve_format_selector

        assert _resolve_format_selector("worst") == "worst"

        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str="worst",
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        assert "-f" in cmd
        idx = cmd.index("-f")
        assert cmd[idx + 1] == "worst"

    def test_cli_command_format_selector_for_non_standard_height(
        self, test_settings: Settings
    ) -> None:
        """A height outside any fixed ladder reaches yt-dlp as a height filter.

        The user's reported case: a video offering 106p вЂ¦ 1610p, requested at
        1072p. The token produced by ``QualitySpec`` must become
        ``best[height<=1072]``, not a rejected value.
        """
        cmd, _ = _build_ytdlp_cli_command(
            output_file=Path("/tmp/test.mp4"),
            quality_str=str(QualitySpec.parse("1072p")),
            user_agent=test_settings.user_agent,
            settings=test_settings,
            cookies=None,
            raw_cookies=None,
        )

        idx = cmd.index("-f")
        assert cmd[idx + 1] == "best[height<=1072]"

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

    def test_parse_progress_estimated_total(self) -> None:
        """The "~" estimate form of a fragment download is progress, not a new line.

        A fragment (HLS) download has no exact total, so yt-dlp prefixes the
        running estimate with "~". This is the line shape reported for
        ``--quality 1072`` on video-225794656_456243579 (566 fragments).
        """
        line = "[download]   0.8% of ~   1.18GiB at    1.42MiB/s ETA 16:38 (frag 5/566)"

        result = _parse_ytdlp_progress(line)

        assert result is not None
        downloaded, total = result
        assert total == int(1.18 * 1024**3)
        assert downloaded == int(total * 0.8 / 100)


class TestYtdlpProgressLineDetection:
    """Tests for the live-progress line detection behind the in-place rewrite.

    A line that is not recognised as progress is written with a newline, so a
    missed template turns the one rewriting progress line into an endless list.
    """

    @pytest.mark.parametrize(
        "line",
        [
            # total known
            "[download]  40.3% of 649.37MiB at 983.45KiB/s ETA 06:43",
            "[download]  100.0% of 100.00MiB at 2.00MiB/s ETA 00:00",
            # estimated total (fragment download), with and without fragment index
            "[download]   0.8% of ~   1.18GiB at    1.42MiB/s ETA 16:38 (frag 5/566)",
            "[download]   0.0% of ~  340.05MiB at    756.65B/s ETA Unknown (frag 0/566)",
            "[download]   0.8% of ~   1.18GiB at    1.42MiB/s ETA 16:38 (frag 5)",
            # no total at all: byte count instead of percent
            "[download]  12.34MiB at 1.00MiB/s",
            "[download]  12.34MiB at 1.00MiB/s (00:12)",
            "[download]   0.00B at Unknown B/s (00:00)",
            # percent-only fallback
            "[download]   0.0% at Unknown B/s ETA Unknown",
            "[download]  N/A% at Unknown B/s ETA Unknown",
        ],
    )
    def test_progress_templates_are_detected(self, line: str) -> None:
        """Every template yt-dlp can emit must rewrite the same console line."""
        assert _is_ytdlp_progress_line(line) is True

    @pytest.mark.parametrize(
        "line",
        [
            "[download] Destination: /tmp/video.mp4",
            "[download] Downloading 1 format(s): hls-5108",
            "[download] video.mp4 has already been downloaded",
            "[download] Resuming download at byte 1000",
            "[download] Got error: unable to resume",
            "[download] Unable to resume",
            "[hlsnative] Downloading m3u8 manifest",
            "[hlsnative] Total fragments: 566",
            "ERROR: [vk] Unable to download JSON metadata",
        ],
    )
    def test_one_shot_messages_are_not_progress(self, line: str) -> None:
        """One-shot messages keep their own line instead of being overwritten."""
        assert _is_ytdlp_progress_line(line) is False


class TestEchoYtdlpLine:
    """Tests for the console rendering of a yt-dlp line.

    A non-progress line with nothing to redact is passed through unchanged,
    while a non-progress line carrying a signed CDN URL is redacted on the
    terminal. These two cases are siblings, not replacements: pass-through is
    content-dependent, not unconditional.
    """

    def test_progress_line_is_rewritten_in_place(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A progress update must not append a newline (it would scroll)."""
        line = "[download]   0.8% of ~   1.18GiB at    1.42MiB/s ETA 16:38 (frag 5/566)\n"

        _echo_ytdlp_line(line)

        captured = capsys.readouterr()
        assert captured.err.startswith("\r")
        assert captured.err.endswith("\r")
        assert "\n" not in captured.err
        assert "frag 5/566" in captured.err

    def test_one_shot_line_keeps_its_newline(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Non-progress output is passed through unchanged."""
        line = "[download] Destination: /tmp/video.mp4\n"

        _echo_ytdlp_line(line)

        captured = capsys.readouterr()
        assert captured.err == line

    def test_non_progress_signed_cdn_url_is_redacted_on_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A non-progress line carrying a signed CDN URL is redacted on stderr.

        The signed query values (``sig=``, ``token=``) and their payloads never
        reach the terminal; only ``scheme://host/***REDACTED***`` survives. The
        surrounding yt-dlp prose and the trailing newline are preserved. This is
        the core SEC-005 evidence: nothing in tests/ previously passed a URL to
        ``_echo_ytdlp_line``. Sibling of ``test_one_shot_line_keeps_its_newline``,
        not a replacement for its benign pass-through.
        """
        line = (
            "[video] abc123: Downloading webpage: "
            "https://vk-cdn.net/video/seg1.ts?sig=A1b2C3d4e5f6&token=zzzZZZ\n"
        )

        _echo_ytdlp_line(line)

        captured = capsys.readouterr()
        assert "https://vk-cdn.net/***REDACTED***" in captured.err
        assert "sig=" not in captured.err
        assert "token=" not in captured.err
        assert "A1b2C3d4e5f6" not in captured.err
        assert "zzzZZZ" not in captured.err
        assert "Downloading webpage:" in captured.err
        assert captured.err.endswith("\n")

    def test_non_progress_cookie_artefact_path_is_redacted_on_stderr(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A real cookie artefact path in a non-progress line is redacted on stderr.

        Builds a genuine artefact via ``_create_temp_cookie_file`` (so the
        ``vk_cookies_`` shape is real, not synthetic) and proves B4's widened
        artefact rule reaches the terminal: ``***REDACTED***`` appears with none
        of ``vk_cookies_``, ``AppData`` or ``Users`` present. Cleaned up in a
        ``finally`` so no residue escapes.
        """
        from vkdownloader.services.ytdlp_downloader import _remove_cookie_artifact_dir

        cookie_file = _create_temp_cookie_file("vk=test")
        cookie_dir = cookie_file.parent
        try:
            line = f"[download] Destination: {cookie_file}\n"

            _echo_ytdlp_line(line)

            captured = capsys.readouterr()
            assert "***REDACTED***" in captured.err
            assert "vk_cookies_" not in captured.err
            assert "AppData" not in captured.err
            assert "Users" not in captured.err
            assert captured.err.endswith("\n")
        finally:
            _remove_cookie_artifact_dir(cookie_dir)

    def test_progress_branch_text_is_transformed_before_padding(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The progress write branch redacts ``text`` before width padding/truncation.

        A line classified as progress (``_is_ytdlp_progress_line``) that also
        carries a signed CDN URL in its speed field still takes the ``\\r``
        rewrite and writes the redacted URL. Fixture constraint: the transformed
        text is kept under 80 columns so ``ljust``/truncation at
        ``shutil.get_terminal_size((80, 24)).columns`` cannot make the assertion
        environment-dependent.
        """
        line = "[download]  40.3% of 649.37MiB at https://vk-cdn.net/v?sig=X ETA 06:43\n"

        _echo_ytdlp_line(line)

        captured = capsys.readouterr()
        assert captured.err.startswith("\r")
        assert captured.err.endswith("\r")
        assert "\n" not in captured.err
        assert "https://vk-cdn.net/***REDACTED***" in captured.err
        assert "sig=" not in captured.err

    def test_echo_false_url_line_writes_nothing_and_logs_nothing(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``echo=False`` on a URL-bearing line writes nothing and logs nothing.

        The observable half of gate-before-transform: the ``if not echo`` gate is
        evaluated before any transform, so a URL-bearing non-progress line
        leaves stderr empty and emits no progress-suppressed debug record. Done
        at ``_echo_ytdlp_line`` directly with ``capsys`` and a patched logger;
        the existing subprocess-level ``echo=False`` test is not duplicated here.
        """
        line = (
            "[video] abc123: Downloading webpage: "
            "https://vk-cdn.net/video/seg1.ts?sig=A1b2C3d4e5f6&token=zzzZZZ\n"
        )

        with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
            _echo_ytdlp_line(line, echo=False)

        captured = capsys.readouterr()
        assert captured.err == ""
        assert mock_logger.debug.call_count == 0
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0

    def test_progress_templates_are_transform_identically(self) -> None:
        """D-6 evidence: all seven real yt-dlp progress templates are fixed points.

        For each template: ``sanitize_text_for_log(t) == t`` (the URL rule keeps
        ``scheme://host/`` and the artefact rules key on ``vk_cookies_…``, which
        the ``[download] <pct>% of <size>`` region never contains); and
        classification (``_is_ytdlp_progress_line``) and parse
        (``_parse_ytdlp_progress``) results are identical before and after. The
        second half pins *classification*, which the existing ``downloaded`` /
        ``total`` assertions provably do not cover — they would stay green through
        a transform that changed which arm a line takes. Identity holds because
        ``_YTDLP_PROGRESS_LINE_RE`` is anchored at ``^[download]`` and none of
        B4's three rules can match that region.
        """
        from vkdownloader.utils.url_sanitizer import sanitize_text_for_log

        templates = [
            "[download]  40.3% of 649.37MiB at 983.45KiB/s ETA 06:43",
            "[download]   0.8% of ~   1.18GiB at    1.42MiB/s ETA 16:38 (frag 5/566)",
            "[download]  12.34MiB at 1.00MiB/s (00:12)",
            "[download]   0.0% at Unknown B/s ETA Unknown",
            "[download]  40.3% of 649.37MiB at 983.45KiB/s ETA 06:43 (frag 1/10)",
            "[download]  100% of 344.38MiB at 5.00MiB/s ETA 00:00",
            "[download]   0.8% of ~   1.18GiB at    1.42MiB/s ETA 16:38 (frag 5)",
        ]
        for template in templates:
            transformed = sanitize_text_for_log(template)
            assert transformed == template, (
                f"template must be a fixed point of the transform: {template!r}"
            )
            assert _is_ytdlp_progress_line(template) == _is_ytdlp_progress_line(transformed)
            assert _parse_ytdlp_progress(template) == _parse_ytdlp_progress(transformed)

    def test_shorter_progress_line_clears_the_previous_one(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The line is padded to the terminal width, so no tail is left behind."""
        _echo_ytdlp_line("[download]  40.3% of 649.37MiB at 983.45KiB/s ETA 06:43\n")
        _echo_ytdlp_line(
            "[download]   0.8% of ~   1.18GiB at    1.42MiB/s ETA 16:38 (frag 5/566)\n"
        )

        captured = capsys.readouterr()
        updates = captured.err.split("\r")
        assert all(
            update == "" or update.endswith(" ") or "(frag 5/566)" in update for update in updates
        )


class TestBoundedYtDlpTranscript:
    """Tests for TRN-011: the child transcript retains only a bounded tail.

    The ``_download_with_ytdlp`` transcript buffer exists solely to build the
    ``download_failed`` record, so only a tail of the child's output is
    retained. These cases pin that behaviour through the observable
    failure-message length rather than any private attribute.
    """

    @staticmethod
    def _recording_logger(
        errors: list[tuple[str, dict[str, Any]]],
    ) -> MagicMock:
        """Return a MagicMock logger whose ``error`` calls are recorded."""
        logger_mock = MagicMock()

        def capture_error(event: str, **kwargs: Any) -> None:
            errors.append((event, kwargs))

        logger_mock.error.side_effect = capture_error
        return logger_mock

    @pytest.mark.asyncio
    async def test_failing_child_output_capped_to_bound(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A chatty failing child yields a failure message no larger than the bound."""
        from vkdownloader.services.ytdlp_downloader import (
            _MAX_CHILD_OUTPUT_BYTES,
            _download_with_ytdlp,
        )

        output_file = tmp_path / "video_output.mp4"
        # 200 lines of 4 KiB ≈ 800 KiB, far over the 64 KiB bound.
        overlong_line = b"x" * 4090 + b"\n"
        readline_lines = [overlong_line] * 200

        error_records: list[tuple[str, dict[str, Any]]] = []
        mock_logger = self._recording_logger(error_records)

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=readline_lines + [b""])
        mock_process.wait = AsyncMock(return_value=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger", mock_logger):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                )

        assert result is None
        failed = [r for r in error_records if r[0] == "download_failed"]
        assert len(failed) == 1
        error_msg = failed[0][1]["error"]
        assert len(error_msg) <= _MAX_CHILD_OUTPUT_BYTES

    @pytest.mark.asyncio
    async def test_bounded_transcript_success_returns_output(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A chatty child that succeeds still returns the output file normally."""
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video_output.mp4"
        overlong_line = b"x" * 4090 + b"\n"
        readline_lines = [overlong_line] * 200

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=readline_lines + [b""])
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger"):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                )

        assert result == output_file

    @pytest.mark.asyncio
    async def test_bounded_transcript_retains_tail_not_head(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """The retained transcript is the tail (end), not the head (beginning)."""
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video_output.mp4"
        # 1000 labelled lines of ~1 KiB ≈ 1 MiB, far over the 64 KiB bound.
        readline_lines: list[bytes] = []
        for i in range(1, 1001):
            prefix = f"LINE_{i:04d}:".encode()
            readline_lines.append(prefix + b"." * (1024 - len(prefix) - 1) + b"\n")

        error_records: list[tuple[str, dict[str, Any]]] = []
        mock_logger = self._recording_logger(error_records)

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=readline_lines + [b""])
        mock_process.wait = AsyncMock(return_value=1)

        def on_progress(video_id: str, downloaded: int, total: int) -> None:
            pass

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger", mock_logger):
                # A callback routes through _monitor_progress so both append
                # sites are covered by the bounding.
                await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                    progress_callback=on_progress,
                )

        failed = [r for r in error_records if r[0] == "download_failed"]
        assert len(failed) == 1
        error_msg = failed[0][1]["error"]
        assert "LINE_1000" in error_msg
        assert "LINE_0001" not in error_msg

    @pytest.mark.asyncio
    async def test_short_transcript_unaffected_by_bound(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A transcript shorter than the bound is retained in full."""
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video_output.mp4"
        readline_lines = [
            b"first line\n",
            b"second line\n",
            b"third line and final\n",
        ]

        error_records: list[tuple[str, dict[str, Any]]] = []
        mock_logger = self._recording_logger(error_records)

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=readline_lines + [b""])
        mock_process.wait = AsyncMock(return_value=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger", mock_logger):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                )

        assert result is None
        failed = [r for r in error_records if r[0] == "download_failed"]
        assert len(failed) == 1
        error_msg = failed[0][1]["error"]
        assert "first line" in error_msg
        assert "second line" in error_msg
        assert "third line and final" in error_msg

    @pytest.mark.asyncio
    async def test_echo_false_chatty_child_no_stderr_and_bounded(
        self,
        test_settings: Settings,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """echo=False writes nothing to stderr; the tail remains bounded."""
        from vkdownloader.services.ytdlp_downloader import (
            _MAX_CHILD_OUTPUT_BYTES,
            _download_with_ytdlp,
        )

        output_file = tmp_path / "video_output.mp4"
        overlong_line = b"x" * 4090 + b"\n"
        readline_lines = [overlong_line] * 200

        error_records: list[tuple[str, dict[str, Any]]] = []
        mock_logger = self._recording_logger(error_records)

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=readline_lines + [b""])
        mock_process.wait = AsyncMock(return_value=1)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger", mock_logger):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                    echo=False,
                )

        assert result is None
        captured = capsys.readouterr()
        assert captured.err == ""
        failed = [r for r in error_records if r[0] == "download_failed"]
        assert len(failed) == 1
        error_msg = failed[0][1]["error"]
        assert len(error_msg) <= _MAX_CHILD_OUTPUT_BYTES


class TestParallelSegmentsDownload:
    """Tests for parallel segment download with semaphore."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_downloads(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Test that semaphore enforces max_concurrent_segments limit."""
        from typing import Any

        from vkdownloader.services.downloader import download_hls_with_resume

        test_settings = Settings(max_concurrent_segments=2)

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

        test_settings = Settings(max_concurrent_segments=4)

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
                "https://example.com/playlist.m3u8",
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

        test_settings = Settings(max_concurrent_segments=1)

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

        # Verify delay was called for each segment in sequential mode (max_concurrent_segments=1)
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

        test_settings = Settings(max_concurrent_segments=1)

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

        test_settings = Settings(max_concurrent_segments=4)

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
                    "https://example.com/playlist.m3u8",
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
    async def test_child_receives_selected_address(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Verify yt-dlp's final positional argument is the m3u8_url, not the video_url."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: Any, **kwargs: Any) -> Any:
            captured_cmd.extend(str(c) for c in cmd)
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

        assert captured_cmd[-1] == "https://example.com/playlist.m3u8"


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

    @pytest.mark.asyncio
    async def test_stop_while_read_blocked_invokes_on_shutdown(self) -> None:
        """A stop landing while readline() is blocked must invoke on_shutdown.

        None of the four original tests can observe this case: they either
        pre-set the event or exhaust a finite side_effect list. This drives a
        real asyncio.StreamReader fed one line and then left silent, so the
        next readline() blocks. The stop is set from a task, the watcher fires
        on_shutdown, and the generator terminates.
        """
        stream = asyncio.StreamReader()
        stream.feed_data(b"line one\n")  # one line, then silence → next read blocks
        shutdown_event = asyncio.Event()

        async def _stop_soon() -> None:
            await asyncio.sleep(0)
            shutdown_event.set()

        stopper = asyncio.create_task(_stop_soon())
        callback_calls: list[str] = []

        async def on_shutdown() -> None:
            callback_calls.append("fired")
            stream.feed_eof()  # stand-in for cancel_subprocess closing the pipe

        async def _drain() -> list[bytes]:
            return [
                line
                async for line in iter_process_lines(
                    stream, shutdown_event, on_shutdown=on_shutdown
                )
            ]

        try:
            lines = await asyncio.wait_for(_drain(), timeout=5.0)
        except TimeoutError:
            pytest.fail(
                "iter_process_lines did not terminate within 5.0s of a stop "
                "that landed while readline() was blocked; "
                f"on_shutdown invoked: {bool(callback_calls)}"
            )
        await stopper

        assert lines == [b"line one\n"]
        assert callback_calls == ["fired"]
        # No watcher task should outlive the generator.
        leftover = [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task() and t is not stopper
        ]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_on_shutdown_fires_exactly_once_after_blocked_read(self) -> None:
        """A naive fix double-fires on the discriminator sequence.

        The stop lands while a read is blocked; on_shutdown then feeds more
        data; the generator continues and the next iteration's between-lines
        guard also calls fire(). The shared fired flag must suppress the second
        call, so the callback is invoked exactly once.
        """
        stream = asyncio.StreamReader()
        stream.feed_data(b"line one\n")
        shutdown_event = asyncio.Event()

        async def _stop_soon() -> None:
            await asyncio.sleep(0)
            shutdown_event.set()

        stopper = asyncio.create_task(_stop_soon())
        callback_calls: list[str] = []

        async def on_shutdown() -> None:
            callback_calls.append("fired")
            # Simulate the child still having buffered output after the kill.
            stream.feed_data(b"line two\n")
            stream.feed_eof()

        async def _drain() -> list[bytes]:
            return [
                line
                async for line in iter_process_lines(
                    stream, shutdown_event, on_shutdown=on_shutdown
                )
            ]

        try:
            lines = await asyncio.wait_for(_drain(), timeout=5.0)
        except TimeoutError:
            pytest.fail(
                "iter_process_lines did not terminate within 5.0s of a stop "
                "that landed while readline() was blocked; "
                f"on_shutdown invoked: {bool(callback_calls)}"
            )
        await stopper

        assert lines == [b"line one\n", b"line two\n"]
        assert callback_calls == ["fired"]
        leftover = [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task() and t is not stopper
        ]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_eof_terminates_without_invoking_on_shutdown(self) -> None:
        """EOF ends the drain without calling on_shutdown, and leaves no tasks.

        Uses a real StreamReader (not AsyncMock) to verify the between-lines
        path and the watcher cleanup on normal exhaustion.
        """
        stream = asyncio.StreamReader()
        stream.feed_data(b"line1\nline2\n")
        stream.feed_eof()
        shutdown_event = asyncio.Event()
        callback_calls: list[str] = []

        async def on_shutdown() -> None:
            callback_calls.append("fired")

        lines = [
            line
            async for line in iter_process_lines(stream, shutdown_event, on_shutdown=on_shutdown)
        ]

        assert lines == [b"line1\n", b"line2\n"]
        assert callback_calls == []
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_consumer_break_leaves_no_pending_tasks(self) -> None:
        """A consumer that breaks mid-stream must not leave the watcher pending."""
        stream = asyncio.StreamReader()
        stream.feed_data(b"line1\nline2\n")
        shutdown_event = asyncio.Event()
        callback_calls: list[str] = []

        async def on_shutdown() -> None:
            callback_calls.append("fired")

        gen = iter_process_lines(stream, shutdown_event, on_shutdown=on_shutdown)
        consumed: list[bytes] = []
        async for line in gen:
            consumed.append(line)
            break  # consumer stops mid-stream
        await gen.aclose()  # finalize the generator so the finally runs

        assert consumed == [b"line1\n"]
        assert callback_calls == []
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_aclose_leaves_no_pending_tasks(self) -> None:
        """Explicitly closing the generator must cancel and await the watcher."""
        stream = asyncio.StreamReader()
        stream.feed_data(b"line one\n")
        shutdown_event = asyncio.Event()
        callback_calls: list[str] = []

        async def on_shutdown() -> None:
            callback_calls.append("fired")

        gen = iter_process_lines(stream, shutdown_event, on_shutdown=on_shutdown)
        first = await gen.__anext__()
        assert first == b"line one\n"
        await gen.aclose()

        assert callback_calls == []
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_consumer_cancellation_cleans_up_watcher(self) -> None:
        """Cancelling the consumer must not fire on_shutdown or leave tasks.

        The callers own that path via their CancelledError arms; the watcher
        in this generator must be cancelled and awaited away.
        """
        stream = asyncio.StreamReader()
        stream.feed_data(b"line one\n")
        shutdown_event = asyncio.Event()
        callback_calls: list[str] = []

        async def on_shutdown() -> None:
            callback_calls.append("fired")

        gen = iter_process_lines(stream, shutdown_event, on_shutdown=on_shutdown)
        consumed: list[bytes] = []

        async def _consume() -> None:
            async for line in gen:
                consumed.append(line)

        consumer = asyncio.create_task(_consume())
        # Let the consumer receive the first line and block on the next readline.
        await asyncio.sleep(0.01)
        consumer.cancel()
        try:
            await consumer
        except asyncio.CancelledError:
            pass

        assert callback_calls == []
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_overlong_line_raises_after_draining_pipe(self) -> None:
        """T1: an over-long line drains the pipe then surfaces DownloadError.

        The reader's default limit is 65536 bytes, so a 70000-byte line (with
        its newline) cannot be returned by ``readline()`` and raises. The
        generator must first drain the bytes that follow it so the pipe can
        reach EOF, then surface the overrun as a ``DownloadError`` carrying the
        original ``ValueError`` as its cause. No fragment is ever yielded.
        """
        stream = asyncio.StreamReader()
        stream.feed_data(b"head\n")
        stream.feed_data(b"x" * 70000 + b"\n")
        stream.feed_data(b"y" * 200000 + b"\n")
        stream.feed_eof()
        shutdown_event = asyncio.Event()
        calls: list[str] = []

        async def on_shutdown() -> None:
            calls.append("fired")

        yielded: list[bytes] = []
        with patch("vkdownloader.services.ffmpeg_utils.logger") as mock_logger:
            with pytest.raises(DownloadError) as excinfo:
                async for line in iter_process_lines(
                    stream, shutdown_event, on_shutdown=on_shutdown
                ):
                    yielded.append(line)

        assert yielded == [b"head\n"]
        assert excinfo.value.__cause__ is not None
        assert "Separator is found" in str(excinfo.value.__cause__)
        # at_eof only becomes True once the 200001-byte tail has been drained.
        assert stream.at_eof() is True
        assert calls == []
        overrun_records = [
            c
            for c in mock_logger.error.call_args_list
            if c.args and c.args[0] == "subprocess_line_overrun"
        ]
        assert len(overrun_records) == 1, (
            f"Expected exactly 1 subprocess_line_overrun record, got {len(overrun_records)}"
        )
        assert overrun_records[0].kwargs["discarded_bytes"] == 200001
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_stop_during_overlong_drain_fires_on_shutdown_once(self) -> None:
        """T2: a stop landing while the drain is blocked fires on_shutdown once.

        Only the over-long line is fed and no EOF is offered, so the drain
        blocks on ``stream.read``. The stop is set from a task; the watcher
        fires ``on_shutdown`` (which feeds EOF as the stand-in for killing the
        child), the drain unblocks, and the generator ends with a
        ``DownloadError``. ``fire()`` stays at-most-once: both the watcher and
        the drain's own guard observe the stop, but only one invocation gets
        through.
        """
        stream = asyncio.StreamReader()
        stream.feed_data(b"x" * 70000 + b"\n")
        # No feed_eof: the drain must block until the stop offers EOF.
        shutdown_event = asyncio.Event()

        async def _stop_soon() -> None:
            await asyncio.sleep(0)
            shutdown_event.set()

        stopper = asyncio.create_task(_stop_soon())
        calls: list[str] = []

        async def on_shutdown() -> None:
            calls.append("fired")
            stream.feed_eof()  # stand-in for cancel_subprocess closing the pipe

        async def _drive() -> None:
            async for _ in iter_process_lines(stream, shutdown_event, on_shutdown=on_shutdown):
                pass

        try:
            await asyncio.wait_for(_drive(), timeout=5.0)
            pytest.fail(
                "iter_process_lines raised no DownloadError when a stop landed "
                "during the over-long drain"
            )
        except DownloadError:
            pass
        except TimeoutError:
            pytest.fail("iter_process_lines drain ignored the stop and blocked until timeout")
        await stopper

        assert calls == ["fired"]
        leftover = [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task() and t is not stopper
        ]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_overlong_line_leaves_no_pending_watcher(self) -> None:
        """T3: the over-long path leaves no pending watcher task.

        The ``async for`` runs inside a task so the generator's ``finally``
        executes as part of the task's own unwinding rather than deferring to
        a GC-driven finalizer pass. The task's exception is retrieved by the
        ``pytest.raises`` await — an unretrieved exception would grow the suite
        warning count.
        """
        stream = asyncio.StreamReader()
        stream.feed_data(b"head\n")
        stream.feed_data(b"x" * 70000 + b"\n")
        stream.feed_data(b"y" * 200000 + b"\n")
        stream.feed_eof()
        shutdown_event = asyncio.Event()

        async def _consume() -> list[bytes]:
            yielded: list[bytes] = []
            async for line in iter_process_lines(stream, shutdown_event):
                yielded.append(line)
            return yielded

        consumer = asyncio.create_task(_consume())
        with pytest.raises(DownloadError):
            await consumer

        assert consumer.done()
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert leftover == []

    @pytest.mark.asyncio
    async def test_overlong_line_does_not_wedge_process_wait(self) -> None:
        """T4: draining the pipe lets ``process.wait()`` return (TRN-004).

        The only test in this suite that spawns a real child. The child writes
        a 70001-byte line (above the reader limit) followed by 200001 more
        bytes so the unconsumed remainder exceeds the transport's 131072-byte
        window; a short tail would not wedge the wait and so would not gate
        the fix. After the drain the pipe reaches EOF, so ``wait()`` returns the
        child's already-known exit code instead of hanging.
        """
        child = (
            "import sys; out = sys.stdout.buffer; "
            "out.write(b'x' * 70000 + b'\\n'); out.flush(); "
            "out.write(b'y' * 200000 + b'\\n'); out.flush()"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            "-c",
            child,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        shutdown_event = asyncio.Event()
        try:
            with pytest.raises(DownloadError):
                async for _ in iter_process_lines(process.stdout, shutdown_event):
                    pass
            returncode = await asyncio.wait_for(process.wait(), timeout=10.0)
            assert returncode == 0
        finally:
            if process.returncode is None:
                process.kill()
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except TimeoutError:
                    pass


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
                max_concurrent_segments=1,
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
            max_concurrent_segments=4,
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

    @pytest.mark.asyncio
    async def test_cleanup_restores_each_signals_previous_handler(self) -> None:
        """Assert each signal's OWN pre-install handler comes back, per signal.

        Before the fix the displaced handler was not restored on the branch that actually
        runs, so asyncio.run's own SIGINT restore was skipped and the displacement
        compounded across cycles. Exercises the real signal.signal path with no patching.
        """
        import signal as signal_module

        from vkdownloader.services import signal_handlers

        pre_int = signal_module.getsignal(signal_module.SIGINT)
        pre_term = signal_module.getsignal(signal_module.SIGTERM)
        try:
            signal_handlers.setup_signal_handlers()
            assert signal_module.getsignal(signal_module.SIGINT) is not pre_int
            assert signal_module.getsignal(signal_module.SIGTERM) is not pre_term
            signal_handlers.cleanup_signal_handlers()
            assert signal_module.getsignal(signal_module.SIGINT) is pre_int
            assert signal_module.getsignal(signal_module.SIGTERM) is pre_term
        finally:
            # Unconditional: a half-finished fix must not leave pytest-asyncio's own restore
            # suppressed for the rest of the session.
            signal_module.signal(signal_module.SIGINT, pre_int)
            signal_module.signal(signal_module.SIGTERM, pre_term)

    @pytest.mark.asyncio
    async def test_second_setup_keeps_the_first_captured_handler(self) -> None:
        """A second setup must not overwrite the captured previous handler.

        Capture-once oracle: the first setup's captured pre-install value is retained
        through a second setup, so one cleanup restores the ORIGINAL handler and a
        further cycle re-captures the same original -- proving the stores were cleared
        rather than left holding a stale (this module's own) value.
        """
        import signal as signal_module

        from vkdownloader.services import signal_handlers

        pre_int = signal_module.getsignal(signal_module.SIGINT)
        pre_term = signal_module.getsignal(signal_module.SIGTERM)
        try:
            signal_handlers.setup_signal_handlers()
            installed_1 = signal_module.getsignal(signal_module.SIGINT)
            signal_handlers.setup_signal_handlers()
            installed_2 = signal_module.getsignal(signal_module.SIGINT)
            assert installed_2 is not installed_1
            signal_handlers.cleanup_signal_handlers()
            assert signal_module.getsignal(signal_module.SIGINT) is pre_int
            assert signal_module.getsignal(signal_module.SIGTERM) is pre_term
            signal_handlers.setup_signal_handlers()
            signal_handlers.cleanup_signal_handlers()
            assert signal_module.getsignal(signal_module.SIGINT) is pre_int
            assert signal_module.getsignal(signal_module.SIGTERM) is pre_term
        finally:
            signal_module.signal(signal_module.SIGINT, pre_int)
            signal_module.signal(signal_module.SIGTERM, pre_term)

    def test_handler_is_not_displaced_across_consecutive_event_loops(self) -> None:
        """SIGINT must not be left displaced across three consecutive asyncio.run cycles.

        Drives asyncio.run itself (not a shared pytest-asyncio Runner) three times, which
        is the only shape in which three distinct Runner._on_sigint partials are
        observable: inside a pytest-asyncio async test the cycles share one Runner and
        therefore one pre-install object. Uses the project token idiom for the shutdown
        event so get_shutdown_event() returns a test-owned Event instead of a leaked
        loop-bound one.
        """
        import asyncio as asyncio_module
        import signal as signal_module

        from vkdownloader.services import signal_handlers
        from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

        pre_int = signal_module.getsignal(signal_module.SIGINT)
        pre_term = signal_module.getsignal(signal_module.SIGTERM)
        token = _shutdown_event_ctx.set(asyncio_module.Event())
        captured_pre_ints: list[object] = []
        try:

            async def _cycle() -> None:
                cycle_pre_int = signal_module.getsignal(signal_module.SIGINT)
                cycle_pre_term = signal_module.getsignal(signal_module.SIGTERM)
                captured_pre_ints.append(cycle_pre_int)
                signal_handlers.setup_signal_handlers()
                signal_handlers.cleanup_signal_handlers()
                # Per cycle: the pre-install disposition is restored after cleanup.
                assert signal_module.getsignal(signal_module.SIGINT) is cycle_pre_int
                assert signal_module.getsignal(signal_module.SIGTERM) is cycle_pre_term

            for _ in range(3):
                asyncio_module.run(_cycle())
                # After asyncio.run returns, the runtime has restored default_int_handler
                # because the displaced Runner._on_sigint partial was put back rather than
                # left in place.
                assert (
                    signal_module.getsignal(signal_module.SIGINT)
                    is signal_module.default_int_handler
                )

            # Three fresh Runner._on_sigint partials were captured, all distinct.
            assert captured_pre_ints[0] is not captured_pre_ints[1]
            assert captured_pre_ints[1] is not captured_pre_ints[2]
            assert captured_pre_ints[0] is not captured_pre_ints[2]
        finally:
            _shutdown_event_ctx.reset(token)
            signal_module.signal(signal_module.SIGINT, pre_int)
            signal_module.signal(signal_module.SIGTERM, pre_term)

    @pytest.mark.asyncio
    async def test_repeated_interrupt_forwards_to_displaced_handler(self) -> None:
        """B5: a second interrupt escalates by re-invoking the displaced handler.

        First fire: requests stop — one ``shutdown_signal_received`` record,
        shutdown event set.
        Second fire: escalates — the stand-in installed **before** setup (the
        displaced object) runs, so its call list becomes ``[SIGINT]``.
        Third fire: one-shot guard already set — no-op, call list unchanged.

        Exercises the real ``signal.signal`` fallback (loop.add_signal_handler is
        unavailable on this platform) with a recording stand-in substituted for
        the runtime's own ``Runner._on_sigint``, so the escalation forwards to a
        safe stand-in rather than cancelling the test task.
        """
        import signal as signal_module

        from vkdownloader.services import signal_handlers
        from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

        pre_int = signal_module.getsignal(signal_module.SIGINT)
        pre_term = signal_module.getsignal(signal_module.SIGTERM)

        # Token idiom: supply a test-owned Event so the handler writes to one
        # we control instead of a leaked loop-bound one.
        token = _shutdown_event_ctx.set(asyncio.Event())

        displaced_calls: list[int] = []

        def _displaced(signum: int, _frame: object) -> None:
            """Recording stand-in that captures the forwarded signal number."""
            displaced_calls.append(signum)

        try:
            signal_module.signal(signal_module.SIGINT, _displaced)
            signal_handlers.setup_signal_handlers()

            installed = signal_module.getsignal(signal_module.SIGINT)
            if installed is _displaced:
                pytest.fail("setup_signal_handlers did not displace the stand-in handler")

            with patch.object(signal_handlers, "logger") as mock_logger:
                # Fire 1: requests a stop, one shutdown_signal_received record.
                installed(signal_module.SIGINT, None)
                assert get_shutdown_event().is_set()
                assert mock_logger.info.call_count == 1
                assert mock_logger.info.call_args_list[0].args[0] == "shutdown_signal_received"

                # Fire 2: escalates — the displaced object ran.
                installed(signal_module.SIGINT, None)
                assert mock_logger.warning.call_count == 1
                warning_call = mock_logger.warning.call_args_list[0]
                assert warning_call.args[0] == "shutdown_signal_escalated"
                assert warning_call.kwargs["reason"] == "displaced_handler"
                assert displaced_calls == [signal_module.SIGINT]

                # Fire 3: one-shot guard, no-op — stand-in call list unchanged.
                installed(signal_module.SIGINT, None)
                assert mock_logger.warning.call_count == 1
                assert displaced_calls == [signal_module.SIGINT]
        finally:
            signal_handlers.cleanup_signal_handlers()
            _shutdown_event_ctx.reset(token)
            signal_module.signal(signal_module.SIGINT, pre_int)
            signal_module.signal(signal_module.SIGTERM, pre_term)

    @pytest.mark.asyncio
    async def test_repeated_interrupt_raises_keyboard_interrupt_when_no_handler_captured(
        self,
    ) -> None:
        """B5: when the loop owns the disposition, escalation raises
        ``KeyboardInterrupt`` directly.

        On a platform where ``loop.add_signal_handler`` succeeds, no previous
        handler is captured (the loop path does not go through
        ``_capture_previous_handler``), so ``_escalate_interrupt`` finds nothing
        callable and raises ``KeyboardInterrupt`` with ``reason="keyboard_interrupt"``.
        """
        import signal as signal_module

        from vkdownloader.services import signal_handlers
        from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

        token = _shutdown_event_ctx.set(asyncio.Event())

        registered: dict[int, Any] = {}

        class _SucceedingLoop:
            def add_signal_handler(self, sig: int, callback: object) -> None:
                registered[sig] = callback

            def remove_signal_handler(self, sig: int) -> None:
                registered.pop(sig, None)

        try:
            with patch.object(asyncio, "get_running_loop", return_value=_SucceedingLoop()):
                with patch.object(signal_module, "signal") as mock_signal:
                    signal_handlers.setup_signal_handlers()

                    # signal.signal must NOT be called when the loop path succeeds.
                    assert mock_signal.call_count == 0

            # The loop-path callback takes no arguments.
            callback = registered[signal_module.SIGINT]

            with patch.object(signal_handlers, "logger") as mock_logger:
                # Fire 1: requests a stop, one record.
                callback()
                assert get_shutdown_event().is_set()
                assert mock_logger.info.call_count == 1
                assert mock_logger.info.call_args_list[0].args[0] == "shutdown_signal_received"

                # Fire 2: escalation raises KeyboardInterrupt (no callable captured).
                with pytest.raises(KeyboardInterrupt):
                    callback()
                assert mock_logger.warning.call_count == 1
                warning_call = mock_logger.warning.call_args_list[0]
                assert warning_call.args[0] == "shutdown_signal_escalated"
                assert warning_call.kwargs["reason"] == "keyboard_interrupt"

                # Fire 3: one-shot guard, no-op.
                callback()
                assert mock_logger.warning.call_count == 1
        finally:
            signal_handlers.cleanup_signal_handlers()
            get_shutdown_event().clear()
            _shutdown_event_ctx.reset(token)


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
            def select(self, streams: list[Stream], quality: QualitySpec) -> Stream:
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
                    "https://example.com/playlist.m3u8",
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
                        "https://example.com/playlist.m3u8",
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
                "https://example.com/playlist.m3u8",
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
                "https://example.com/playlist.m3u8",
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
                    "https://example.com/playlist.m3u8",
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
                    "https://example.com/playlist.m3u8",
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
                        "https://example.com/playlist.m3u8",
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
                        "https://example.com/playlist.m3u8",
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

    @pytest.mark.asyncio
    async def test_reader_line_overrun_recorded_when_no_progress_callback(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """T5: an over-long line is logged as ``ytdlp_reader_line_overrun``.

        With no progress callback the no-callback drain path (``_drain_output``)
        runs. The reader raises ``DownloadError`` after draining the pipe, the
        drain catches it and logs exactly one overrun record, and the task ends
        normally — so ``_await_first_and_cancel_others`` must NOT emit the
        ``subprocess_reader_failed`` record that a dead reader would normally
        produce. The pipe really was drained: ``stdout.read`` was awaited.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        progress_line = b"[download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43\n"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                progress_line,
                ValueError("Separator is found, but chunk is longer than limit"),
            ]
        )
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                )

        assert result == output_file
        overrun_records = [
            c
            for c in mock_logger.error.call_args_list
            if c.args and c.args[0] == "ytdlp_reader_line_overrun"
        ]
        assert len(overrun_records) == 1, (
            f"Expected exactly 1 ytdlp_reader_line_overrun record, got {len(overrun_records)}"
        )
        assert overrun_records[0].kwargs["pid"] == 12345
        assert overrun_records[0].kwargs["url"] == "https://vkvideo.ru/***REDACTED***"
        failed_records = [
            c
            for c in mock_logger.error.call_args_list
            if c.args and c.args[0] == "subprocess_reader_failed"
        ]
        assert len(failed_records) == 0, (
            f"Expected 0 subprocess_reader_failed records, got {len(failed_records)}"
        )
        mock_process.stdout.read.assert_awaited()

    @pytest.mark.asyncio
    async def test_reader_line_overrun_recorded_with_progress_callback(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """T6: an over-long line is logged with a callback in flight.

        The progress-callback path (``_monitor_progress``) runs. The good
        progress line is parsed and the callback fires exactly once for it; the
        over-long line then stops the transcript with a ``DownloadError`` that
        is logged as ``ytdlp_reader_line_overrun`` — no fabricated line follows,
        and no ``subprocess_reader_failed`` record is emitted.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        progress_line = b"[download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43\n"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(
            side_effect=[
                progress_line,
                ValueError("Separator is found, but chunk is longer than limit"),
            ]
        )
        mock_process.stdout.read = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        progress_calls: list[tuple[str, int, int]] = []

        def progress_callback(video_id: str, downloaded: int, total: int) -> None:
            progress_calls.append((video_id, downloaded, total))

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                    progress_callback=progress_callback,
                    echo=False,
                )

        assert result == output_file
        overrun_records = [
            c
            for c in mock_logger.error.call_args_list
            if c.args and c.args[0] == "ytdlp_reader_line_overrun"
        ]
        assert len(overrun_records) == 1, (
            f"Expected exactly 1 ytdlp_reader_line_overrun record, got {len(overrun_records)}"
        )
        assert overrun_records[0].kwargs["pid"] == 12345
        assert overrun_records[0].kwargs["url"] == "https://vkvideo.ru/***REDACTED***"
        failed_records = [
            c
            for c in mock_logger.error.call_args_list
            if c.args and c.args[0] == "subprocess_reader_failed"
        ]
        assert len(failed_records) == 0, (
            f"Expected 0 subprocess_reader_failed records, got {len(failed_records)}"
        )
        mock_process.stdout.read.assert_awaited()
        assert len(progress_calls) == 1, (
            f"Expected progress_callback to fire exactly once, got {len(progress_calls)}"
        )

    @pytest.mark.asyncio
    async def test_cookie_cleanup_failure_does_not_replace_success_outcome(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A destroy that raises OSError leaves the file behind; success returns output_file.

        TRN-002 (outcome half): the cookie-file unlink raising ``OSError``
        must not propagate out of the ``finally`` and replace the method's
        return value.  Drive the failure by patching ``Path.unlink`` — no
        real OS handle is held.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        def raising_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
            raise PermissionError("simulated indexer lock")

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            with patch.object(Path, "unlink", new=raising_unlink):
                with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        "https://example.com/playlist.m3u8",
                        output_file,
                        "720",
                        test_settings,
                        cookies=cookies,
                    )

        assert result == output_file
        cookies_idx = captured_cmd.index("--cookies")
        cookie_file_path = Path(captured_cmd[cookies_idx + 1])
        assert cookie_file_path.exists(), "Cookie file should remain when unlink raises OSError"
        mock_logger.warning.assert_any_call(
            "cookie_file_cleanup_failed",
            path=str(cookie_file_path),
            error="simulated indexer lock",
        )
        # The success debug record must NOT fire when cleanup failed.
        cleanup_debug_calls = [
            c
            for c in mock_logger.debug.call_args_list
            if c.args and c.args[0] == "cookie_file_cleaned_up"
        ]
        assert len(cleanup_debug_calls) == 0, (
            "cookie_file_cleaned_up debug must not be logged when cleanup failed"
        )

    @pytest.mark.asyncio
    async def test_cookie_cleanup_failure_does_not_replace_failure_outcome(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A destroy that raises OSError leaves the file behind; non-zero returncode returns None.

        TRN-002 (outcome half): the cookie-file unlink raising ``OSError``
        must not propagate out of the ``finally`` and replace the ``None``
        that a non-zero yt-dlp returncode already produced.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[b"ERROR: video not found\n", b""])
        mock_process.wait = AsyncMock(return_value=1)

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        def raising_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
            raise PermissionError("simulated indexer lock")

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            with patch.object(Path, "unlink", new=raising_unlink):
                with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        "https://example.com/playlist.m3u8",
                        output_file,
                        "720",
                        test_settings,
                        cookies=cookies,
                    )

        assert result is None
        cookies_idx = captured_cmd.index("--cookies")
        cookie_file_path = Path(captured_cmd[cookies_idx + 1])
        assert cookie_file_path.exists(), "Cookie file should remain when unlink raises OSError"
        mock_logger.warning.assert_any_call(
            "cookie_file_cleanup_failed",
            path=str(cookie_file_path),
            error="simulated indexer lock",
        )

    @pytest.mark.asyncio
    async def test_cookie_cleanup_failure_does_not_replace_shutdown_outcome(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A destroy that raises OSError leaves the file behind; shutdown returns None.

        TRN-002 (outcome half): the cookie-file unlink raising ``OSError``
        must not propagate out of the ``finally`` and replace the ``None``
        that the shutdown path already produced.  Uses the project token
        idiom for the shutdown event so it does not leak across tests.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp
        from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            get_shutdown_event().set()

            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.pid = 12345
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock(return_value=0)

            captured_cmd: list[str] = []

            async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
                captured_cmd.extend(cmd)
                return mock_process

            def raising_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
                raise PermissionError("simulated indexer lock")

            with patch(
                "asyncio.create_subprocess_exec",
                side_effect=mock_create_subprocess_exec,
            ):
                with patch.object(Path, "unlink", new=raising_unlink):
                    with patch(
                        "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                        new_callable=AsyncMock,
                        return_value=True,
                    ):
                        with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                            result = await _download_with_ytdlp(
                                "https://vkvideo.ru/video-12345_67890",
                                "https://example.com/playlist.m3u8",
                                output_file,
                                "720",
                                test_settings,
                                cookies=cookies,
                            )

            assert result is None
            cookies_idx = captured_cmd.index("--cookies")
            cookie_file_path = Path(captured_cmd[cookies_idx + 1])
            assert cookie_file_path.exists(), "Cookie file should remain when unlink raises OSError"
            mock_logger.warning.assert_any_call(
                "cookie_file_cleanup_failed",
                path=str(cookie_file_path),
                error="simulated indexer lock",
            )
        finally:
            _shutdown_event_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_cookie_file_removed_and_logged_on_success(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """The negative case: cleanup succeeds, file is removed, debug record is written.

        Guards against the fix passing by deleting the cleanup entirely: the
        file IS removed on success and ``cookie_file_cleaned_up`` IS logged.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        debug_events: list[tuple[str, dict[str, Any]]] = []

        def capture_debug(event: str, **kwargs: Any) -> None:
            debug_events.append((event, kwargs))

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            with patch(
                "vkdownloader.services.ytdlp_downloader.logger.debug",
                side_effect=capture_debug,
            ):
                with patch("vkdownloader.services.ytdlp_downloader.logger.info"):
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        "https://example.com/playlist.m3u8",
                        output_file,
                        "720",
                        test_settings,
                        cookies=cookies,
                    )

        assert result == output_file
        cookies_idx = captured_cmd.index("--cookies")
        cookie_file_path = Path(captured_cmd[cookies_idx + 1])
        assert not cookie_file_path.exists(), "Cookie file should be removed when cleanup succeeds"
        cleanup_events = [
            (event, kwargs) for event, kwargs in debug_events if event == "cookie_file_cleaned_up"
        ]
        assert len(cleanup_events) == 1, (
            f"Expected exactly 1 cookie_file_cleaned_up debug call, got {len(cleanup_events)}"
        )
        _, kwargs = cleanup_events[0]
        assert kwargs["path"] == str(cookie_file_path)

    @pytest.mark.asyncio
    async def test_cookie_cleanup_failure_child_reaped_before_unlink(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """On the failed-destroy path, the child is reaped before the finally runs.

        TRN-002 (orphan half, mooted by D2): the residue that survives is
        only the outcome-masking half.  This assertion makes the residue
        honest by checking the observable effect — ``process.wait()`` was
        called — rather than a private attribute.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        ordering: list[str] = []

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")

        async def recording_wait() -> int:
            ordering.append("process_wait")
            return 0

        mock_process.wait = AsyncMock(side_effect=recording_wait)

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        def recording_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
            ordering.append("cookie_unlink")
            raise PermissionError("simulated indexer lock")

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            with patch.object(Path, "unlink", new=recording_unlink):
                with patch("vkdownloader.services.ytdlp_downloader.logger"):
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        "https://example.com/playlist.m3u8",
                        output_file,
                        "720",
                        test_settings,
                        cookies=cookies,
                    )

        assert result == output_file
        assert "process_wait" in ordering, "process.wait() must be called before the finally runs"
        assert "cookie_unlink" in ordering, "cookie file unlink must be attempted in the finally"
        assert ordering.index("process_wait") < ordering.index("cookie_unlink"), (
            "process.wait() must be called before cookie file unlink"
        )

    @pytest.mark.asyncio
    async def test_no_cancel_not_clean_when_already_reaped_on_second_cancel(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """TRN-012 composition case: _on_shutdown cancels the child first,
        then the CancelledError arm re-enters cancel_subprocess on the same
        handle.

        cancel_subprocess returns True on the first call (ladder succeeded),
        then False on the second (the child was already reaped by the first
        call's terminate).  The second call's side-effect sets returncode,
        so the new ``and process.returncode is None`` guard suppresses the
        yt_dlp_cancel_not_clean record the old code would have emitted.

        Asserts on log records, not on return values.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp
        from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

        output_file = tmp_path / "video.mp4"

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            get_shutdown_event().set()

            mock_process = AsyncMock()
            mock_process.returncode = None
            mock_process.pid = 12345
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock(side_effect=asyncio.CancelledError())

            cancel_call_count = 0

            def mock_cancel_side_effect(proc: Any) -> bool:
                nonlocal cancel_call_count
                cancel_call_count += 1
                if cancel_call_count == 1:
                    # First call from _on_shutdown: ladder terminated the child.
                    return True
                # Second call from CancelledError arm: child already reaped.
                proc.returncode = 1
                return False

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch(
                    "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                    new_callable=AsyncMock,
                    side_effect=mock_cancel_side_effect,
                ) as mock_cancel_mock:
                    with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                        with pytest.raises(asyncio.CancelledError):
                            await _download_with_ytdlp(
                                "https://vkvideo.ru/video-12345_67890",
                                "https://example.com/playlist.m3u8",
                                output_file,
                                "720",
                                test_settings,
                            )

            assert mock_cancel_mock.await_count == 2
            not_clean_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if c.args and c.args[0] == "yt_dlp_cancel_not_clean"
            ]
            assert len(not_clean_calls) == 0, (
                f"Expected 0 yt_dlp_cancel_not_clean records, got {len(not_clean_calls)}"
            )
        finally:
            _shutdown_event_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_no_cancel_not_clean_when_process_already_reaped(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """TRN-012: cancel_subprocess returns False with returncode already set —
        the reachable "already gone ⇒ clean" state — emits no warning.

        cancel_subprocess returns False only via the ProcessLookupError arm,
        which fires when the handle is already gone — a state in which returncode
        is already set. The ``and process.returncode is None`` guard suppresses
        the yt_dlp_cancel_not_clean record in that reachable case. This test must
        fail if anyone reverts to the pre-B5
        ``if not await cancel_subprocess(process):`` warning.
        """
        from vkdownloader.services.downloader import _download_with_ytdlp
        from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

        output_file = tmp_path / "video.mp4"

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            get_shutdown_event().set()

            mock_process = AsyncMock()
            mock_process.returncode = 1  # already gone — reachable state
            mock_process.pid = 12345
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b"")
            mock_process.wait = AsyncMock(return_value=1)

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with patch(
                    "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                    new_callable=AsyncMock,
                    return_value=False,
                ) as mock_cancel:
                    with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                        await _download_with_ytdlp(
                            "https://vkvideo.ru/video-12345_67890",
                            "https://example.com/playlist.m3u8",
                            output_file,
                            "720",
                            test_settings,
                        )

            mock_cancel.assert_awaited()
            not_clean_calls = [
                c
                for c in mock_logger.warning.call_args_list
                if c.args and c.args[0] == "yt_dlp_cancel_not_clean"
            ]
            assert len(not_clean_calls) == 0, (
                f"Expected 0 yt_dlp_cancel_not_clean records (process already reaped), "
                f"got {len(not_clean_calls)}"
            )
        finally:
            _shutdown_event_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_reader_task_failure_emits_record(self) -> None:
        """TRN-006 sink half: a reader task that raises produces exactly one
        ``subprocess_reader_failed`` record instead of being swallowed.

        Asserts on the observable log record, not on the helper's return tuple.
        """
        from vkdownloader.services.ytdlp_downloader import _await_first_and_cancel_others

        async def failing_reader() -> None:
            raise RuntimeError("reader died")

        async def blocker() -> None:
            await asyncio.sleep(3600)

        failed = asyncio.create_task(failing_reader())
        blocked = asyncio.create_task(blocker())
        try:
            with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                await _await_first_and_cancel_others(failed, blocked)

            records = [
                c
                for c in mock_logger.error.call_args_list
                if c.args and c.args[0] == "subprocess_reader_failed"
            ]
            assert len(records) == 1, (
                f"Expected exactly 1 subprocess_reader_failed record, got {len(records)}"
            )
            assert "reader died" in records[0].kwargs["error"]
        finally:
            for task in (failed, blocked):
                if not task.done():
                    task.cancel()

    @pytest.mark.asyncio
    async def test_normal_completion_emits_no_record(self) -> None:
        """TRN-006 discrimination case: a task that completes normally produces
        NO ``subprocess_reader_failed`` record.

        Without this the fix is satisfiable by logging every finished task,
        which would be noise rather than visibility.
        """
        from vkdownloader.services.ytdlp_downloader import _await_first_and_cancel_others

        async def normal_reader() -> None:
            return None

        async def blocker() -> None:
            await asyncio.sleep(3600)

        normal = asyncio.create_task(normal_reader())
        blocked = asyncio.create_task(blocker())
        try:
            with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                await _await_first_and_cancel_others(normal, blocked)

            records = [
                c
                for c in mock_logger.error.call_args_list
                if c.args and c.args[0] == "subprocess_reader_failed"
            ]
            assert len(records) == 0, (
                f"Expected 0 subprocess_reader_failed records, got {len(records)}"
            )
        finally:
            for task in (normal, blocked):
                if not task.done():
                    task.cancel()

    @pytest.mark.asyncio
    async def test_cancelled_pending_task_emits_no_record(self) -> None:
        """TRN-006 cancellation case: a pending task that is cancelled and
        settles does NOT produce a ``subprocess_reader_failed`` record.

        One task raises (proving the done-failure path logs once); the other
        is pending and cancelled by the helper, so it must not add a second
        record even though it would have raised had it run.  This is plan
        08's settle-before-return contract, which this block must not break.
        """
        from vkdownloader.services.ytdlp_downloader import _await_first_and_cancel_others

        async def failing_reader() -> None:
            raise RuntimeError("done failure")

        async def slow_failing_reader() -> None:
            await asyncio.sleep(3600)
            raise RuntimeError("pending failure")

        failed = asyncio.create_task(failing_reader())
        blocked = asyncio.create_task(slow_failing_reader())
        try:
            with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                await _await_first_and_cancel_others(failed, blocked)

            records = [
                c
                for c in mock_logger.error.call_args_list
                if c.args and c.args[0] == "subprocess_reader_failed"
            ]
            assert len(records) == 1, (
                f"Expected exactly 1 subprocess_reader_failed record (from the failed "
                f"done task), got {len(records)} — the cancelled pending task "
                f"must not produce one"
            )
            assert records[0].kwargs["error"] == "done failure"
            assert blocked.cancelled()
        finally:
            for task in (failed, blocked):
                if not task.done():
                    task.cancel()

    @pytest.mark.asyncio
    async def test_download_success_removes_dir_and_emits_no_cleanup_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """On the success path the directory is removed and no cleanup failure is recorded.

        Covers AC-1 and AC-2: the per-run directory is absent after a successful
        download, and ``cookie_file_cleanup_failed`` is never emitted on the
        success path (the log-noise regression from 36b801e) (T3).
        """
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
            with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                    cookies=cookies,
                )

        assert result == output_file
        cookies_idx = captured_cmd.index("--cookies")
        cookie_file_path = Path(captured_cmd[cookies_idx + 1])
        assert not cookie_file_path.exists(), "cookie file should be removed on success"
        assert not cookie_file_path.parent.exists(), (
            "cookie artefact directory must be removed on success"
        )
        cleanup_failure_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "cookie_file_cleanup_failed"
        ]
        assert len(cleanup_failure_calls) == 0, (
            f"no cookie_file_cleanup_failed should be emitted on success, "
            f"got {len(cleanup_failure_calls)}"
        )

    @pytest.mark.asyncio
    async def test_locked_cookie_file_records_one_failure_and_keeps_both(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A locked credential file emits one directory-arm failure record and
        leaves both the file and directory behind, with the outcome unchanged (T4).

        Two records are correct in production — one from the file arm (path =
        the file) and one from the directory arm (path = the directory).
        This test's "one failure" refers to the directory arm; it holds only
        because this test patches Path.unlink wholesale, so owner.pid's unlink
        raises too and rule 4 short-circuits. Do not generalise to a real lock.
        """
        from vkdownloader.services.ytdlp_downloader import (
            _COOKIE_ARTIFACT_DIRS,
            _COOKIE_LIFECYCLE_LOCK,
            _download_with_ytdlp,
        )

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        def raising_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
            raise PermissionError("simulated indexer lock")

        import shutil

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=mock_create_subprocess_exec,
        ):
            with patch.object(Path, "unlink", new=raising_unlink):
                with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
                    result = await _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        "https://example.com/playlist.m3u8",
                        output_file,
                        "720",
                        test_settings,
                        cookies=cookies,
                    )

        # Outcome is unchanged (success).
        assert result == output_file
        cookies_idx = captured_cmd.index("--cookies")
        cookie_file_path = Path(captured_cmd[cookies_idx + 1])
        # The credential file survives (unlink raised).
        assert cookie_file_path.exists(), "credential file must survive a locked unlink"
        # The directory survives (rmdir cannot succeed while the file is present).
        assert cookie_file_path.parent.exists(), "directory must survive a locked unlink"

        # Exactly one cookie_file_cleanup_failed record for the directory arm.
        dir_failures = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args
            and c.args[0] == "cookie_file_cleanup_failed"
            and c.kwargs.get("path") == str(cookie_file_path.parent)
        ]
        assert len(dir_failures) == 1, (
            f"expected exactly 1 directory-arm cookie_file_cleanup_failed record, "
            f"got {len(dir_failures)}"
        )

        # The directory stays tracked on failure.
        with _COOKIE_LIFECYCLE_LOCK:
            assert cookie_file_path.parent in _COOKIE_ARTIFACT_DIRS, (
                "directory must remain tracked when unlink fails"
            )
        # Safety cleanup.
        cookie_file_path.unlink(missing_ok=True)
        shutil.rmtree(cookie_file_path.parent, ignore_errors=True)
        with _COOKIE_LIFECYCLE_LOCK:
            _COOKIE_ARTIFACT_DIRS.discard(cookie_file_path.parent)

    @pytest.mark.asyncio
    async def test_cancel_path_removes_dir(self, test_settings: Settings, tmp_path: Path) -> None:
        """On CancelledError the per-run directory is still removed (T5).

        The finally runs during unwinding and _remove_cookie_artifact_dir is
        reached despite the CancelledError arm re-raising.
        """
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(side_effect=asyncio.CancelledError())

        captured_cmd: list[str] = []

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
            with patch(
                "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                new_callable=AsyncMock,
                return_value=True,
            ):
                with patch("vkdownloader.services.ytdlp_downloader.logger"):
                    with pytest.raises(asyncio.CancelledError):
                        await _download_with_ytdlp(
                            "https://vkvideo.ru/video-12345_67890",
                            "https://example.com/playlist.m3u8",
                            output_file,
                            "720",
                            test_settings,
                            cookies=cookies,
                        )

        cookies_idx = captured_cmd.index("--cookies")
        cookie_file_path = Path(captured_cmd[cookies_idx + 1])
        assert not cookie_file_path.parent.exists(), (
            "cookie artefact directory must be removed even on cancellation"
        )

    @pytest.mark.asyncio
    async def test_teardown_runs_when_cookie_file_already_absent(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """The directory teardown runs whenever cookie_file is not None, even
        when the credential file has already vanished (T6 / R1-A2).
        """
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"
        cookies = "vk=abc123; session=xyz789"

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")
        mock_process.wait = AsyncMock(return_value=0)

        captured_cmd: list[str] = []
        cookie_file_path: Path | None = None

        async def mock_create_subprocess_exec(*cmd: str, **kwargs: Any) -> AsyncMock:
            captured_cmd.extend(cmd)
            # Simulate yt-dlp consuming the cookie file so it vanishes before
            # the finally block runs.
            nonlocal cookie_file_path
            if "--cookies" in cmd:
                cookies_idx = cmd.index("--cookies")
                cookie_file_path = Path(cmd[cookies_idx + 1])
                cookie_file_path.unlink(missing_ok=True)
            return mock_process

        with patch("asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec):
            with patch("vkdownloader.services.ytdlp_downloader.logger"):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    test_settings,
                    cookies=cookies,
                )

        assert result == output_file
        assert cookie_file_path is not None
        assert not cookie_file_path.exists(), "cookie file should have been consumed"
        assert not cookie_file_path.parent.exists(), (
            "cookie artefact directory must be removed even when the file vanished before teardown"
        )


class TestProcessBoundaryDescendant:
    """Tests for TRN-003: process boundary at subprocess spawn sites.

    A stand-in child spawns a grandchild process, then ``cancel_subprocess``
    is run on the child. On POSIX the group signal (``killpg``) reaches the
    grandchild; on Windows ``CREATE_NEW_PROCESS_GROUP`` routes console signals
    only, so the grandchild survives — the documented residual.
    """

    # Stand-in child: spawns a grandchild (a sleeping python), prints the
    # grandchild PID to stdout, then idles until the termination ladder kills it.
    _CHILD_SCRIPT = (
        "import subprocess, sys, time\n"
        "gc = subprocess.Popen(\n"
        "    [sys.executable, '-c', 'import time; time.sleep(60)'],\n"
        "    stdout=subprocess.DEVNULL,\n"
        "    stderr=subprocess.DEVNULL,\n"
        ")\n"
        "print(f'GPID:{gc.pid}')\n"
        "sys.stdout.flush()\n"
        "time.sleep(30)\n"
    )

    @staticmethod
    def _is_alive(pid: int) -> bool:
        """Cross-platform liveness check via ``os.kill(pid, 0)``."""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but we lack permission to signal it.
            return True
        except OSError:
            return False

    async def _spawn_child_with_grandchild(
        self,
        tmp_path: Path,
    ) -> tuple[asyncio.subprocess.Process, int]:
        """Spawn a child that spawns a grandchild; return (process, gc_pid).

        Asserts the grandchild is alive before returning — a test that
        passes because the child never spawned is not a test.
        """
        child_script = tmp_path / "child_standin.py"
        child_script.write_text(self._CHILD_SCRIPT)

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            str(child_script),
            **_SPAWN_BOUNDARY_KWARGS,  # type: ignore[arg-type]
            stdout=asyncio.subprocess.PIPE,
        )
        assert process.stdout is not None
        line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
        assert line.startswith(b"GPID:"), f"unexpected child output: {line!r}"
        grandchild_pid = int(line.split(b":")[1].strip())
        assert self._is_alive(grandchild_pid), "grandchild never started"
        return process, grandchild_pid

    async def _cleanup(
        self,
        process: asyncio.subprocess.Process | None,
        grandchild_pid: int | None,
    ) -> None:
        if process is not None and process.returncode is None:
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except TimeoutError:
                pass
        if grandchild_pid is not None and self._is_alive(grandchild_pid):
            try:
                # 9 is SIGKILL on POSIX; on Windows os.kill(pid, 9) maps to
                # TerminateProcess (signal.SIGKILL is absent at runtime there).
                os.kill(grandchild_pid, 9)
            except (ProcessLookupError, PermissionError, OSError):
                pass

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="POSIX-only: killpg reaches descendants",
    )
    async def test_descendant_killed_on_posix(self, tmp_path: Path) -> None:
        """On POSIX, cancel_subprocess kills the grandchild via killpg."""
        process, grandchild_pid = await self._spawn_child_with_grandchild(tmp_path)
        try:
            result = await cancel_subprocess(process)
            assert result is True
            assert process.returncode is not None
            # Give the signal time to propagate to the grandchild.
            await asyncio.sleep(1.0)
            assert not self._is_alive(grandchild_pid), "grandchild survived on POSIX"
        finally:
            await self._cleanup(process, grandchild_pid)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="Windows-only: CREATE_NEW_PROCESS_GROUP does not kill descendants",
    )
    async def test_descendant_survives_on_windows(self, tmp_path: Path) -> None:
        """On Windows, the grandchild survives cancel_subprocess (TRN-003 residual)."""
        process, grandchild_pid = await self._spawn_child_with_grandchild(tmp_path)
        try:
            result = await cancel_subprocess(process)
            assert result is True
            assert process.returncode is not None
            # CREATE_NEW_PROCESS_GROUP routes console signals only; the
            # grandchild survives. This is the documented Windows residual.
            await asyncio.sleep(1.0)
            assert self._is_alive(grandchild_pid), (
                "grandchild died on Windows — residual not honored"
            )
        finally:
            await self._cleanup(process, grandchild_pid)


class TestYtDlpStallTimeout:
    """Tests for the inactivity-bounded yt-dlp child reap (TRN-007).

    ``_download_with_ytdlp`` reaps the child exactly once before reading
    ``returncode``. When the reader has finished draining the stream and the
    child has not yet exited, that one-shot reap is bounded by
    ``download_stall_timeout`` — an INACTIVITY bound, not a whole-operation
    budget. On expiry the child is terminated through the cancellation ladder
    (``cancel_subprocess``) and the ``TimeoutError`` is re-raised. A child
    that keeps producing output is never killed.
    """

    @staticmethod
    def _fast_settings(stall: float = 1.0) -> Settings:
        """Settings with a short stall timeout (bypassing the ge=30 floor).

        ``Settings`` has no ``validate_assignment``, so direct field mutation
        is the established pattern in this suite (mirrors the drain trio's
        use of ``test_settings``).
        """
        s = Settings(
            download_dir=Settings.model_fields["download_dir"].default,
            max_concurrent_downloads=2,
            max_retries=1,
        )
        s.download_stall_timeout = stall
        return s

    @pytest.mark.asyncio
    async def test_stall_terminates_and_reaps_silent_child(self, tmp_path: Path) -> None:
        """STALL CASE: a child that emits then goes silent is killed within the
        bound AND the child is reaped (cancel_subprocess is awaited)."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        stall_timeout = 1.0
        settings = self._fast_settings(stall=stall_timeout)
        output_file = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        # Child emits one line then goes silent (EOF).
        mock_process.stdout.readline = AsyncMock(side_effect=[b"some output\n", b""])

        async def blocking_wait() -> int:
            await asyncio.sleep(3600)
            return 0

        mock_process.wait = blocking_wait

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch(
                "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_cancel:
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    settings,
                )

        # The call returns within the bound, not after 3600 s.
        assert result is None
        # Both halves: the termination ladder ran.
        mock_cancel.assert_awaited()

    @pytest.mark.asyncio
    async def test_liveness_continuous_output_never_killed(self, tmp_path: Path) -> None:
        """LIVENESS CASE: a child that keeps emitting output does NOT trip the
        bound, proving this is an inactivity limit (not a total-time budget)
        and that NET-007 is preserved, not reinstated."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        stall_timeout = 1.0
        settings = self._fast_settings(stall=stall_timeout)
        output_file = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()

        # Reader emits 4 lines at 0.3 s intervals (1.2 s total), then EOF.
        # The child is still active well past the 1 s stall budget — proving
        # the clock only starts after EOF.
        lines_remaining = [b"line1\n", b"line2\n", b"line3\n", b"line4\n"]

        async def emitting_readline() -> bytes:
            await asyncio.sleep(0.3)
            if lines_remaining:
                return lines_remaining.pop(0)
            return b""

        mock_process.stdout.readline = emitting_readline

        # Child exits 0.5 s after the reader finishes (within the 1 s stall).
        exit_event = asyncio.Event()

        async def schedule_exit() -> None:
            await asyncio.sleep(2.0)
            exit_event.set()

        exit_task = asyncio.create_task(schedule_exit())
        try:

            async def waiting_wait() -> int:
                await exit_event.wait()
                mock_process.returncode = 0
                return 0

            mock_process.wait = waiting_wait

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await _download_with_ytdlp(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/playlist.m3u8",
                    output_file,
                    "720",
                    settings,
                )
        finally:
            exit_task.cancel()

        # Child kept producing, was never killed — returned normally.
        assert result == output_file

    @pytest.mark.asyncio
    async def test_cancellation_during_reap_propagates_and_reaps(self, tmp_path: Path) -> None:
        """CANCELLATION ARM: cancelling the holder still propagates
        ``CancelledError`` and the termination ladder still runs."""
        from vkdownloader.services.downloader import _download_with_ytdlp

        settings = self._fast_settings(stall=10.0)
        output_file = tmp_path / "video.mp4"

        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b"")

        async def blocking_wait() -> int:
            await asyncio.sleep(3600)
            return 0

        mock_process.wait = blocking_wait

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            with patch(
                "vkdownloader.services.ytdlp_downloader.cancel_subprocess",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_cancel:
                task = asyncio.create_task(
                    _download_with_ytdlp(
                        "https://vkvideo.ru/video-12345_67890",
                        "https://example.com/playlist.m3u8",
                        output_file,
                        "720",
                        settings,
                    )
                )
                # Let the re-wait arm be armed, then cancel before the 10 s
                # stall expiry.
                await asyncio.sleep(0.2)
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task

        mock_cancel.assert_awaited()

    @pytest.mark.asyncio
    async def test_setting_default_and_bounds(self, tmp_path: Path) -> None:
        """SETTING: the default constructs against ``Settings``; the documented
        ``.env.example`` value constructs against ``Settings``; ``ge=30`` and
        ``le=3600`` reject out-of-range values."""
        from pydantic import ValidationError

        # Default constructs.
        default_settings = Settings(
            download_dir=Settings.model_fields["download_dir"].default,
            max_concurrent_downloads=2,
            max_retries=1,
        )
        assert default_settings.download_stall_timeout == 300.0
        assert isinstance(default_settings.download_stall_timeout, float)

        # The .env.example value constructs.
        env_example_path = Path(__file__).resolve().parent.parent / ".env.example"
        env_text = env_example_path.read_text(encoding="utf-8")
        # Extract the commented value next to VKDOWNLOADER_DOWNLOAD_STALL_TIMEOUT.
        stall_line = [
            line for line in env_text.splitlines() if "VKDOWNLOADER_DOWNLOAD_STALL_TIMEOUT" in line
        ][0]
        # "# VKDOWNLOADER_DOWNLOAD_STALL_TIMEOUT=300.0" -> "300.0"
        env_value = float(stall_line.split("=")[1])
        env_settings = Settings(
            download_dir=Settings.model_fields["download_dir"].default,
            max_concurrent_downloads=2,
            max_retries=1,
            download_stall_timeout=env_value,
        )
        assert env_settings.download_stall_timeout == env_value

        # ge=30 rejects below the floor.
        with pytest.raises(ValidationError):
            Settings(
                download_dir=Settings.model_fields["download_dir"].default,
                max_concurrent_downloads=2,
                max_retries=1,
                download_stall_timeout=29.9,
            )

        # le=3600 rejects above the ceiling.
        with pytest.raises(ValidationError):
            Settings(
                download_dir=Settings.model_fields["download_dir"].default,
                max_concurrent_downloads=2,
                max_retries=1,
                download_stall_timeout=3600.1,
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


class TestB13AvailabilityProbe:
    """Tests for TRN-008 / B13: cache behaviour and probe answer usage.

    The write-once cache is left untouched (no invalidation path added,
    per the Planner's choice recorded in the commit body). A second absence
    is not silent: the cached value is returned so that the call site
    (``perform_download``) can still react to it on every invocation.
    """

    def test_check_ffmpeg_available_write_once_when_false(self) -> None:
        """Write-once cache: when ffmpeg is absent, False is cached and a
        second call returns the cached value without re-probing."""
        import vkdownloader.services.ffmpeg_utils as fu

        original = fu._ffmpeg_available
        try:
            fu._ffmpeg_available = None

            # First call discovers the absence and caches False
            with patch("shutil.which", return_value=None):
                result = check_ffmpeg_available()
            assert result is False
            assert fu._ffmpeg_available is False

            # Second call returns cached False — write-once, no re-probe
            with patch("shutil.which", return_value="/usr/bin/ffmpeg") as mock_which:
                result2 = check_ffmpeg_available()
            assert result2 is False  # cached, not silent
            mock_which.assert_not_called()
        finally:
            fu._ffmpeg_available = original

    @pytest.mark.asyncio
    async def test_perform_download_emits_one_warning_when_ffmpeg_missing(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """The probe's answer is used: with check_ffmpeg_available forced to
        False, perform_download emits exactly ONE warning, does NOT raise, and
        does NOT change the exit code (D6)."""
        from vkdownloader.models.enums import DownloadMethod
        from vkdownloader.services.downloader import perform_download

        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=False,
            ),
            patch("vkdownloader.services.downloader.logger.warning") as mock_warning,
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=output_file,
            ),
        ):
            result = await perform_download(
                "https://vkvideo.ru/video-12345_67890",
                "720",
                output_file,
                DownloadMethod.YTDLP,
                settings=test_settings,
                video_data=MagicMock(
                    streams=[MagicMock(url="https://example.com/v.m3u8")],
                ),
                selected_stream=Stream(
                    url="https://example.com/v.m3u8",
                    format=StreamFormat.HLS,
                    quality="best",
                    height=720,
                ),
            )

        # Exactly one warning for the missing muxer
        ffmpeg_warnings = [
            c for c in mock_warning.call_args_list if c[0][0] == "ffmpeg_missing_for_merge"
        ]
        assert len(ffmpeg_warnings) == 1
        assert ffmpeg_warnings[0].kwargs.get("hint") is not None

        # Download proceeded normally — no raise, no early return
        assert result == output_file


class TestB13MergeMissingMuxer:
    """TRN-008 / B13 arm (b): the merge path with no muxer produces one
    actionable record instead of an escaping exception."""

    @pytest.mark.asyncio
    async def test_merge_batch_catches_missing_ffmpeg(self, tmp_path: Path) -> None:
        """_merge_batch_segments returns None and logs merge_spawn_failed when
        ffmpeg is missing, instead of letting FileNotFoundError escape."""
        from vkdownloader.services.ffmpeg_utils import _merge_batch_segments

        segment1 = tmp_path / "00000.ts"
        segment1.write_bytes(b"segment data")

        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError(2, "No such file", "ffmpeg"),
            ),
            patch("vkdownloader.services.ffmpeg_utils.logger.error") as mock_error,
        ):
            result = await _merge_batch_segments([segment1], tmp_path, 300)

        assert result is None
        mock_error.assert_called_once()
        assert mock_error.call_args[0][0] == "merge_spawn_failed"
        assert "ffmpeg" in mock_error.call_args[1]["hint"]

    @pytest.mark.asyncio
    async def test_final_merge_catches_missing_ffmpeg(self, tmp_path: Path) -> None:
        """_perform_final_merge returns False and logs merge_spawn_failed when
        the ffmpeg binary is not on PATH."""
        from vkdownloader.services.ffmpeg_utils import _perform_final_merge

        temp_file = tmp_path / "batch_00000.ts"
        temp_file.write_bytes(b"batch data")
        output = tmp_path / "merged.mp4"

        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError(2, "No such file", "ffmpeg"),
            ),
            patch("vkdownloader.services.ffmpeg_utils.logger.error") as mock_error,
        ):
            result = await _perform_final_merge([temp_file], output, 300)

        assert result is False
        mock_error.assert_called_once()
        assert mock_error.call_args[0][0] == "merge_spawn_failed"
        assert "ffmpeg" in mock_error.call_args[1]["hint"]


class TestB13ResumeErrorHandling:
    """TRN-008 / B13 arm (d): _attempt_segment_resume must not mislabel a
    missing muxer as a token refresh failure."""

    @pytest.mark.asyncio
    async def test_file_not_found_not_logged_as_refresh_token(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A FileNotFoundError escaping from the merge is NOT caught as
        failed_to_refresh_token — it propagates instead."""
        from vkdownloader.services.ytdlp_downloader import _attempt_segment_resume

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

        with (
            patch(
                "vkdownloader.services.ytdlp_downloader.download_hls_with_resume",
                new_callable=AsyncMock,
                side_effect=FileNotFoundError(2, "No such file", "ffmpeg"),
            ),
            patch("vkdownloader.services.ytdlp_downloader.logger.warning") as mock_warning,
        ):
            with pytest.raises(FileNotFoundError):
                await _attempt_segment_resume(
                    "https://vkvideo.ru/video-12345_67890",
                    "https://example.com/stale.m3u8",
                    output_file,
                    "best",
                    retry_count=1,
                    extractor=mock_extractor,
                    settings=test_settings,
                    backoff_coordinator=None,
                    video_semaphore=None,
                )

        # No failed_to_refresh_token warning emitted
        for call in mock_warning.call_args_list:
            assert call[0][0] != "failed_to_refresh_token"

    @pytest.mark.asyncio
    async def test_extraction_error_still_logged_as_refresh_token(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """A genuine ExtractionError IS still caught and logged as
        failed_to_refresh_token."""
        from vkdownloader.services.ytdlp_downloader import _attempt_segment_resume

        output_file = tmp_path / "video.mp4"
        output_file.write_bytes(b"partial data")

        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = AsyncMock(
            side_effect=ExtractionError("Token refresh failed")
        )

        with patch("vkdownloader.services.ytdlp_downloader.logger.warning") as mock_warning:
            result = await _attempt_segment_resume(
                "https://vkvideo.ru/video-12345_67890",
                "https://example.com/stale.m3u8",
                output_file,
                "best",
                retry_count=1,
                extractor=mock_extractor,
                settings=test_settings,
                backoff_coordinator=None,
                video_semaphore=None,
            )

        assert result is None
        # ExtractionError IS still caught and logged as failed_to_refresh_token
        refresh_calls = [
            c for c in mock_warning.call_args_list if c[0][0] == "failed_to_refresh_token"
        ]
        assert len(refresh_calls) == 1
        assert refresh_calls[0].kwargs["error"] == "Token refresh failed"


class TestB13DownloadMissingBinary:
    """TRN-008 / B13 arm (c): the FileNotFoundError arm's record names the
    missing binary."""

    @pytest.mark.asyncio
    async def test_ytdlp_not_found_names_binary(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """When asyncio.create_subprocess_exec raises FileNotFoundError, the
        ytdlp_not_found record includes the missing binary path."""
        from vkdownloader.services.ytdlp_downloader import _download_with_ytdlp

        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError(2, "No such file", "yt-dlp"),
            ),
            patch("vkdownloader.services.ytdlp_downloader.logger.error") as mock_error,
        ):
            result = await _download_with_ytdlp(
                "https://vkvideo.ru/video-12345_67890",
                "https://example.com/playlist.m3u8",
                output_file,
                "720",
                test_settings,
            )

        assert result is None
        mock_error.assert_called_once()
        assert mock_error.call_args[0][0] == "ytdlp_not_found"
        assert mock_error.call_args[1]["path"] == "yt-dlp"


class TestQualitySpecParsing:
    """Tests for the QualitySpec parsing that replaces _parse_quality_to_enum.

    The old helper could only return members of the fixed 240/360/720/1080
    ladder, so heights such as 1072p were unexpressible. ``QualitySpec.parse``
    accepts every positive height the video offers.
    """

    def test_parse_numeric_quality(self) -> None:
        """Test parsing numeric quality strings without p suffix."""
        assert QualitySpec.parse("720").label == "720p"
        assert QualitySpec.parse("1080").label == "1080p"

    def test_parse_quality_with_p_suffix(self) -> None:
        """Test parsing quality strings with p suffix are stripped."""
        assert QualitySpec.parse("720p").label == "720p"
        assert QualitySpec.parse("480p").label == "480p"

    def test_parse_non_standard_height(self) -> None:
        """A height outside the old fixed ladder is accepted."""
        spec = QualitySpec.parse("1072")

        assert spec.kind is QualityKind.EXACT
        assert spec.label == "1072p"
        assert str(spec) == "1072"

    def test_parse_named_qualities(self) -> None:
        """Test parsing named quality strings."""
        assert QualitySpec.parse("best").kind is QualityKind.BEST
        assert QualitySpec.parse("worst").kind is QualityKind.WORST

    def test_parse_unknown_quality_raises(self) -> None:
        """Test that unparseable quality strings raise QualityParseError."""
        from vkdownloader.exceptions import QualityParseError

        with pytest.raises(QualityParseError):
            QualitySpec.parse("invalid_quality")

    def test_parse_empty_quality_defaults_to_best(self) -> None:
        """Test that empty quality string defaults to BEST."""
        assert QualitySpec.parse("").kind is QualityKind.BEST


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
                    QualitySpec.parse("720"),
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
                    QualitySpec.parse("720"),
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
                    QualitySpec.parse("720"),
                    tmp_path,
                    DownloadMethod.YTDLP,
                    test_settings,
                )

        assert result == tmp_path / "video.mp4"
        assert mock_perform.call_count == 1
        # Default echo=True should be forwarded to perform_download
        assert mock_perform.call_args.kwargs["echo"] is True


class TestCookieArtefactLifecycle:
    """Tests for the cookie artefact lifecycle (SEC-001, SEC-002, VAL-602).

    Covers directory confinement, owner-PID liveness probing, stale-dir sweep,
    and atexit hook registration.
    """

    def test_create_cookie_artifact_dir_creates_private_subdir_in_temp(
        self,
    ) -> None:
        """_create_cookie_artifact_dir creates a private subdir within the system temp.

        The directory is a direct child of the system temp root (mkdtemp's parent)
        and is tracked in ``_COOKIE_ARTIFACT_DIRS`` so the atexit handler can purge it.
        """
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _COOKIE_ARTIFACT_DIRS,
            _COOKIE_LIFECYCLE_LOCK,
            _create_cookie_artifact_dir,
            _remove_cookie_artifact_dir,
        )

        temp_dir = Path(_tempfile.gettempdir())
        cookie_dir = _create_cookie_artifact_dir()

        try:
            assert cookie_dir.parent == temp_dir, (
                "cookie artefact directory must be a direct child of the system temp root"
            )
            with _COOKIE_LIFECYCLE_LOCK:
                assert cookie_dir in _COOKIE_ARTIFACT_DIRS, (
                    "cookie artefact directory must be tracked for atexit cleanup"
                )
            # With Alt A, _remove_cookie_artifact_dir now succeeds: assert the
            # directory is gone rather than discarding a tracked-but-present
            # residue that the old finally masked.
            _remove_cookie_artifact_dir(cookie_dir)
            assert not cookie_dir.exists(), (
                "cookie artefact directory must be removed after teardown"
            )
        finally:
            _remove_cookie_artifact_dir(cookie_dir)

    def test_create_cookie_artifact_dir_writes_owner_pid(self) -> None:
        """_create_cookie_artifact_dir records the current process PID in owner.pid.

        The recorded PID is what the sweep uses to identify live-owned directories
        and reclaim residues from hard-killed prior runs (SEC-002).
        """
        from vkdownloader.services.ytdlp_downloader import (
            _OWNER_PID_FILENAME,
            _create_cookie_artifact_dir,
            _remove_cookie_artifact_dir,
        )

        cookie_dir = _create_cookie_artifact_dir()

        try:
            owner_file = cookie_dir / _OWNER_PID_FILENAME
            assert owner_file.exists(), "owner.pid must exist in the artefact directory"
            assert int(owner_file.read_text().strip()) == os.getpid()
            # With Alt A, removal now succeeds: assert the directory is gone
            # rather than discarding a tracked-but-present residue.
            _remove_cookie_artifact_dir(cookie_dir)
            assert not cookie_dir.exists(), (
                "cookie artefact directory must be removed after teardown"
            )
        finally:
            _remove_cookie_artifact_dir(cookie_dir)

    def test_remove_cookie_artifact_dir_removes_created_dir(self) -> None:
        """_remove_cookie_artifact_dir removes a directory created by _create_cookie_artifact_dir.

        This is a REMOVED assertion, not a tracked one: it asserts the directory
        is gone from the filesystem after teardown (R1-A1).
        """
        from vkdownloader.services.ytdlp_downloader import (
            _create_cookie_artifact_dir,
            _remove_cookie_artifact_dir,
        )

        cookie_dir = _create_cookie_artifact_dir()
        assert cookie_dir.exists()

        _remove_cookie_artifact_dir(cookie_dir)
        assert not cookie_dir.exists(), (
            "cookie artefact directory must be removed by _remove_cookie_artifact_dir"
        )

    def test_full_round_trip_removes_parent_dir(self) -> None:
        """The full round trip through _create_temp_cookie_file removes the parent directory.

        The cookie file is unlinked first (caller responsibility), then
        _remove_cookie_artifact_dir unlinks owner.pid and rmdir's the parent (T2).
        """
        from vkdownloader.services.ytdlp_downloader import _remove_cookie_artifact_dir

        cookie_file = _create_temp_cookie_file("vk=test")
        assert cookie_file.exists()
        cookie_dir = cookie_file.parent
        assert cookie_dir.exists()

        cookie_file.unlink(missing_ok=True)
        _remove_cookie_artifact_dir(cookie_dir)
        assert not cookie_dir.exists(), (
            "cookie artefact directory must be removed after the full round trip"
        )

    def test_is_pid_alive_current_process(self) -> None:
        """_is_pid_alive returns True for the current process PID."""
        from vkdownloader.services.ytdlp_downloader import _is_pid_alive

        assert _is_pid_alive(os.getpid()) is True

    def test_is_pid_alive_dead_pid(self) -> None:
        """_is_pid_alive returns False for a PID that cannot exist."""
        from vkdownloader.services.ytdlp_downloader import _is_pid_alive

        # 999999 is well beyond any real PID on common platforms.
        assert _is_pid_alive(999999) is False

    def test_sweep_stale_cookie_dirs_removes_dead_owner(self) -> None:
        """_sweep_stale_cookie_dirs removes directories whose owner PID is dead.

        A directory with ``owner.pid`` pointing at a non-existent PID is residue
        from a hard-killed prior run and must be purged by the liveness-gated
        sweep (VAL-602 / SEC-002).
        """
        import shutil
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _ARTEFACT_DIR_SUFFIX,
            _COOKIE_ARTIFACT_PREFIX,
            _OWNER_PID_FILENAME,
            _sweep_stale_cookie_dirs,
        )

        dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
        stale_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))

        try:
            (stale_dir / _OWNER_PID_FILENAME).write_text("999999")
            _sweep_stale_cookie_dirs()
            assert not stale_dir.exists(), "stale dir with dead owner PID should be swept"
        finally:
            if stale_dir.exists():
                shutil.rmtree(stale_dir, ignore_errors=True)

    def test_sweep_stale_cookie_dirs_preserves_live_owner(self) -> None:
        """_sweep_stale_cookie_dirs preserves directories owned by a live PID.

        The current process is live, so a directory whose ``owner.pid`` records
        it must survive the sweep — proving the guard is PID-based, not blanket
        time-based (VAL-602).
        """
        import shutil
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _ARTEFACT_DIR_SUFFIX,
            _COOKIE_ARTIFACT_PREFIX,
            _OWNER_PID_FILENAME,
            _sweep_stale_cookie_dirs,
        )

        dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
        live_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))

        try:
            (live_dir / _OWNER_PID_FILENAME).write_text(str(os.getpid()))
            _sweep_stale_cookie_dirs()
            assert live_dir.exists(), "live-owned directory must be preserved by the sweep"
        finally:
            if live_dir.exists():
                shutil.rmtree(live_dir, ignore_errors=True)

    def test_ensure_cookie_lifecycle_started_registers_atexit_once(self) -> None:
        """_ensure_cookie_lifecycle_started registers the atexit handler exactly once.

        Resets the module-level ``_cookie_lifecycle_started`` flag so the
        registration branch is observable, then restores it for isolation.
        """
        import vkdownloader.services.ytdlp_downloader as mod
        from vkdownloader.services.ytdlp_downloader import _ensure_cookie_lifecycle_started

        original = mod._cookie_lifecycle_started
        try:
            mod._cookie_lifecycle_started = False
            with patch("vkdownloader.services.ytdlp_downloader.atexit.register") as mock_register:
                _ensure_cookie_lifecycle_started()
                _ensure_cookie_lifecycle_started()
            assert mock_register.call_count == 1, (
                "atexit.register must be called exactly once across repeated invocations"
            )
        finally:
            mod._cookie_lifecycle_started = original

    def test_read_owner_pid_missing_file_returns_none(self, tmp_path: Path) -> None:
        """_read_owner_pid returns None when owner.pid does not exist.

        A missing ``owner.pid`` is a statement about this pure parser: it means
        "no readable record", never "the owner is dead". What the sweep may
        conclude from ``None`` is ``_sweep_stale_cookie_dirs``' business, and
        the default-deny rule there declines to destroy on ``None`` -- "cannot
        determine the owner" is not a positive demonstration of death (VAL-602).
        """
        from vkdownloader.services.ytdlp_downloader import _read_owner_pid

        assert _read_owner_pid(tmp_path) is None

    def test_owner_pid_unlink_failure_skips_rmdir_and_records(self) -> None:
        """A credential file left in the directory makes rmdir fail: one
        ``cookie_file_cleanup_failed`` record with ``path=str(cookie_dir)``,
        the directory survives, and it stays tracked.

        Companion: a call on an already-gone directory emits NO record —
        pinning the ``FileNotFoundError``-before-``OSError`` arm ordering (T7).
        """
        import shutil

        from vkdownloader.services.ytdlp_downloader import (
            _COOKIE_ARTIFACT_DIRS,
            _COOKIE_LIFECYCLE_LOCK,
            _create_cookie_artifact_dir,
            _remove_cookie_artifact_dir,
        )

        # Part A: credential file occupies the directory so rmdir cannot
        # succeed even after owner.pid is unlinked.
        cookie_dir = _create_cookie_artifact_dir()
        credential = cookie_dir / "credential.txt"
        credential.write_text("locked")

        with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:
            _remove_cookie_artifact_dir(cookie_dir)

        failure_records = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and c.args[0] == "cookie_file_cleanup_failed"
        ]
        assert len(failure_records) == 1, (
            f"expected exactly 1 cookie_file_cleanup_failed record for the "
            f"directory arm, got {len(failure_records)}"
        )
        assert failure_records[0].kwargs["path"] == str(cookie_dir)

        assert cookie_dir.exists(), "directory must survive a rmdir failure"
        assert credential.exists(), "credential file must survive"
        with _COOKIE_LIFECYCLE_LOCK:
            assert cookie_dir in _COOKIE_ARTIFACT_DIRS, "directory must remain tracked on failure"

        # Part B: companion — an already-removed directory emits NO record.
        # This pins the FileNotFoundError-before-OSError ordering: if the arms
        # were reversed, FileNotFoundError (a subclass of OSError) would fall
        # into the failure arm and emit a spurious warning.
        shutil.rmtree(cookie_dir, ignore_errors=True)
        assert not cookie_dir.exists()

        with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger2:
            _remove_cookie_artifact_dir(cookie_dir)

        any_warning = mock_logger2.warning.called
        assert not any_warning, "no warning should be emitted for an already-removed directory"

    def test_artifact_dir_set_does_not_grow_across_cycles(self) -> None:
        """_COOKIE_ARTIFACT_DIRS does not grow after N create/teardown cycles (T8).

        Each cycle creates a directory, tracks it, then removes it and prunes
        the set. After N >= 3 cycles the set size must equal the pre-cycle size.
        """
        from vkdownloader.services.ytdlp_downloader import (
            _COOKIE_ARTIFACT_DIRS,
            _COOKIE_LIFECYCLE_LOCK,
            _create_cookie_artifact_dir,
            _remove_cookie_artifact_dir,
        )

        with _COOKIE_LIFECYCLE_LOCK:
            size_before = len(_COOKIE_ARTIFACT_DIRS)

        for _ in range(3):
            cookie_dir = _create_cookie_artifact_dir()
            assert cookie_dir.exists()
            with _COOKIE_LIFECYCLE_LOCK:
                assert cookie_dir in _COOKIE_ARTIFACT_DIRS
            _remove_cookie_artifact_dir(cookie_dir)
            assert not cookie_dir.exists()

        with _COOKIE_LIFECYCLE_LOCK:
            size_after = len(_COOKIE_ARTIFACT_DIRS)
        assert size_after == size_before, (
            f"_COOKIE_ARTIFACT_DIRS grew from {size_before} to {size_after} "
            f"across 3 create/teardown cycles"
        )

    # --- R2: VAL-602 creation-race closure (default-deny sweep) ---

    def test_created_cookie_dir_matches_the_sweep_filter(self) -> None:
        """R2-A3 guard: a freshly created artefact dir matches the sweep's filter.

        Nothing asserted this before, so an edit that broke the prefix would turn
        the sweep into a silent no-op. _create_cookie_artifact_dir's result must
        be matched by startswith(_COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX).
        Written FIRST, before any rule is exercised, so it goes green immediately.
        """
        from vkdownloader.services.ytdlp_downloader import (
            _ARTEFACT_DIR_SUFFIX,
            _COOKIE_ARTIFACT_PREFIX,
            _create_cookie_artifact_dir,
            _remove_cookie_artifact_dir,
        )

        dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
        cookie_dir = _create_cookie_artifact_dir()
        try:
            assert cookie_dir.name.startswith(dir_prefix), (
                "the sweep's startswith filter must match a freshly created "
                "cookie artefact directory"
            )
        finally:
            _remove_cookie_artifact_dir(cookie_dir)

    def test_pidless_new_dir_survives_sweep(self) -> None:
        """AC-1 / R2-A1: a fresh PID-less directory survives the sweep.

        Built with tempfile.mkdtemp(prefix=_COOKIE_ARTIFACT_PREFIX +
        _ARTEFACT_DIR_SUFFIX) and no owner.pid -- the exact on-disk shape
        observable between mkdtemp returning and write_text completing. It is
        fresh (well under the grace), so it is retained.
        """
        import shutil
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _ARTEFACT_DIR_SUFFIX,
            _COOKIE_ARTIFACT_PREFIX,
            _sweep_stale_cookie_dirs,
        )

        dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
        pidless_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            assert not (pidless_dir / "owner.pid").exists()
            _sweep_stale_cookie_dirs()
            assert pidless_dir.exists(), (
                "a fresh PID-less directory must survive the sweep (VAL-602 race)"
            )
        finally:
            if pidless_dir.exists():
                shutil.rmtree(pidless_dir, ignore_errors=True)

    def test_pidless_dir_aged_past_grace_is_swept(self) -> None:
        """AC-1: a PID-less directory provably older than the grace is reclaimed.

        Deterministic ageing goes through the clock seam
        (_cookie_artifact_dir_age_seconds), NOT os.utime: the platform split
        matters. On Windows, os.utime moves only st_mtime and leaves st_birthtime
        (and therefore st_ctime, equal to it) untouched, so a birth-time rule
        cannot be aged from a test on Windows at all. On POSIX, os.stat_result
        exposes no st_birthtime (the helper falls back to st_ctime) and os.utime
        DOES move st_ctime because POSIX st_ctime is inode-change time. The clock
        seam is the only portable deterministic route on both.
        """
        import shutil
        import tempfile as _tempfile
        from unittest.mock import patch

        import vkdownloader.services.ytdlp_downloader as yd

        dir_prefix = yd._COOKIE_ARTIFACT_PREFIX + yd._ARTEFACT_DIR_SUFFIX
        pidless_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            assert not (pidless_dir / yd._OWNER_PID_FILENAME).exists()
            aged = yd._COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS + 1.0
            with patch.object(yd, "_cookie_artifact_dir_age_seconds", return_value=aged):
                yd._sweep_stale_cookie_dirs()
            assert not pidless_dir.exists(), (
                "a PID-less directory provably older than the grace must be swept"
            )
        finally:
            if pidless_dir.exists():
                shutil.rmtree(pidless_dir, ignore_errors=True)

    def test_pidless_dir_with_unknown_age_survives_sweep(self) -> None:
        """AC-1: a PID-less directory whose age cannot be established is retained.

        Default-deny's third state: an unestablishable age degrades to retain,
        which is what keeps the rule safe on a filesystem with unusable
        timestamps.
        """
        import shutil
        import tempfile as _tempfile
        from unittest.mock import patch

        import vkdownloader.services.ytdlp_downloader as yd

        dir_prefix = yd._COOKIE_ARTIFACT_PREFIX + yd._ARTEFACT_DIR_SUFFIX
        pidless_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            assert not (pidless_dir / yd._OWNER_PID_FILENAME).exists()
            with patch.object(yd, "_cookie_artifact_dir_age_seconds", return_value=None):
                yd._sweep_stale_cookie_dirs()
            assert pidless_dir.exists(), "a PID-less directory with an unknown age must be retained"
        finally:
            if pidless_dir.exists():
                shutil.rmtree(pidless_dir, ignore_errors=True)

    def test_zero_length_owner_pid_survives_sweep(self) -> None:
        """R2-A1 widest sub-window: open(mode='w') creates owner.pid before any byte lands.

        A zero-length owner.pid makes _read_owner_pid return None
        (int("".strip()) raises ValueError), so the directory enters the
        PID-less branch and -- being fresh -- is retained by the grace. This is
        the on-disk shape most exposed to the creation race.
        """
        import shutil
        import tempfile as _tempfile

        import vkdownloader.services.ytdlp_downloader as yd

        dir_prefix = yd._COOKIE_ARTIFACT_PREFIX + yd._ARTEFACT_DIR_SUFFIX
        cookie_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            (cookie_dir / yd._OWNER_PID_FILENAME).write_text("")
            assert yd._read_owner_pid(cookie_dir) is None
            yd._sweep_stale_cookie_dirs()
            assert cookie_dir.exists(), (
                "a zero-length owner.pid leaves the directory PID-less and fresh, "
                "so it must be retained"
            )
        finally:
            if cookie_dir.exists():
                shutil.rmtree(cookie_dir, ignore_errors=True)

    def test_unparseable_owner_pid_survives_sweep(self) -> None:
        """R2-A2 state 3: an unparseable owner.pid is retained.

        owner.pid containing a NUL suffix ("14920\\x00") is not a valid int --
        int() rejects the trailing NUL -- so _read_owner_pid returns None and
        the fresh directory is retained by the grace.
        """
        import shutil
        import tempfile as _tempfile

        import vkdownloader.services.ytdlp_downloader as yd

        dir_prefix = yd._COOKIE_ARTIFACT_PREFIX + yd._ARTEFACT_DIR_SUFFIX
        cookie_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            (cookie_dir / yd._OWNER_PID_FILENAME).write_text("14920\x00")
            assert yd._read_owner_pid(cookie_dir) is None
            yd._sweep_stale_cookie_dirs()
            assert cookie_dir.exists(), (
                "an unparseable owner.pid leaves the directory PID-less and fresh, "
                "so it must be retained"
            )
        finally:
            if cookie_dir.exists():
                shutil.rmtree(cookie_dir, ignore_errors=True)

    def test_owner_pid_is_a_directory_survives_sweep(self) -> None:
        """R2-A2 state 4: owner.pid that is itself a directory is retained.

        _read_owner_pid's read_text() raises IsADirectoryError (an OSError), so
        it returns None and the directory is not reclaimed. Keeps the A-3 path
        reachable (R1-A3).
        """
        import shutil
        import tempfile as _tempfile

        import vkdownloader.services.ytdlp_downloader as yd

        dir_prefix = yd._COOKIE_ARTIFACT_PREFIX + yd._ARTEFACT_DIR_SUFFIX
        cookie_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            (cookie_dir / yd._OWNER_PID_FILENAME).mkdir()
            assert yd._read_owner_pid(cookie_dir) is None
            yd._sweep_stale_cookie_dirs()
            assert cookie_dir.exists(), (
                "owner.pid being a directory is unreadable and must be retained"
            )
        finally:
            if cookie_dir.exists():
                shutil.rmtree(cookie_dir, ignore_errors=True)

    def test_torn_digit_prefix_owner_pid_behaviour_is_explicit(self) -> None:
        """R2-A1 wrong-int channel: a torn digit prefix yields 14, not None.

        owner.pid containing "14" (a torn prefix of "14920") makes _read_owner_pid
        return the int 14, not None -- int() accepts the ASCII-digit prefix and
        stops at the file end. The sweep then treats 14 as a PID; since 14 is not
        the current process, the probe reports not-alive, and reclamation depends
        on conclusiveness. This pins that explicit outcome (rather than leaving it
        incidental) and documents that this channel yields a plausible-but-wrong
        PID -- a recycled/real low PID is retained, a provably absent one is swept.
        """
        import shutil
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _ARTEFACT_DIR_SUFFIX,
            _COOKIE_ARTIFACT_PREFIX,
            _OWNER_PID_FILENAME,
            _is_pid_alive,
            _is_pid_probe_conclusive,
            _read_owner_pid,
            _sweep_stale_cookie_dirs,
        )

        dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
        cookie_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            (cookie_dir / _OWNER_PID_FILENAME).write_text("14")
            pid = _read_owner_pid(cookie_dir)
            assert pid == 14, "_read_owner_pid must return the torn int 14, not None"
            assert pid is not None
            assert pid != os.getpid()
            # The sweep reclaims a not-live PID only when the probe is conclusive;
            # assert the directory's fate tracks that rule exactly -- deterministic
            # and platform-independent (we do not assume whether 14 is a live
            # system PID on a given machine).
            reclaim = (not _is_pid_alive(pid)) and _is_pid_probe_conclusive(pid)
            _sweep_stale_cookie_dirs()
            assert cookie_dir.exists() != reclaim, (
                "sweep treatment of a torn PID must match the conclusive-death rule"
            )
        finally:
            if cookie_dir.exists():
                shutil.rmtree(cookie_dir, ignore_errors=True)

    def test_cookie_artifact_dir_age_seconds_reports_a_fresh_directory_as_fresh(
        self,
    ) -> None:
        """T11 (smoke, un-patched): a just-created matching directory has a small, non-None age.

        No monkeypatching, so the clock seam cannot hide a broken helper: the real
        _cookie_artifact_dir_age_seconds must read a real timestamp and return a
        non-negative float below the grace.
        """
        import shutil
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _ARTEFACT_DIR_SUFFIX,
            _COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS,
            _COOKIE_ARTIFACT_PREFIX,
            _cookie_artifact_dir_age_seconds,
        )

        dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX
        fresh_dir = Path(_tempfile.mkdtemp(prefix=dir_prefix))
        try:
            age = _cookie_artifact_dir_age_seconds(fresh_dir)
            assert age is not None
            assert age >= 0.0
            assert age < _COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS
        finally:
            shutil.rmtree(fresh_dir, ignore_errors=True)

    def test_cookie_artifact_dir_age_seconds_returns_none_when_unstattable(
        self,
    ) -> None:
        """T12: a path that cannot be stat'd yields None, not an exception."""
        import tempfile as _tempfile

        from vkdownloader.services.ytdlp_downloader import (
            _cookie_artifact_dir_age_seconds,
        )

        ghost = Path(_tempfile.gettempdir()) / "vk_test_ghost_that_does_not_exist"
        assert not ghost.exists()
        assert _cookie_artifact_dir_age_seconds(ghost) is None

    def test_is_pid_probe_conclusive_windows_semantics(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3: _is_pid_probe_conclusive has a direct, platform-independent test.

        The function is a Windows-only leaf (POSIX short-circuits to True), so
        the test drives it with a fake kernel32 and asserts the full decision
        table:

        - use_last_error=True arms the last-error slot (required so get_last_error
          is reliable; ctypes.windll.kernel32 does NOT arm it).
        - ERROR_INVALID_PARAMETER (87) => True  (PID provably absent).
        - ERROR_ACCESS_DENIED (5)      => False (privilege boundary, inconclusive).
        - any other code                => False (defensive default).
        - non-zero handle              => False, and CloseHandle is called with
                                          that handle so no leak.

        No real DLL is loaded; ctypes is stubbed so the test runs on every
        platform. Mutating _is_pid_probe_conclusive to always-True would fail
        this test.
        """
        import ctypes as real_ctypes

        import vkdownloader.services.ytdlp_downloader as yd

        # Force the Windows branch so the ctypes leaf is exercised on every
        # platform; the test never loads a real DLL.
        monkeypatch.setattr(os, "name", "nt")

        ERROR_INVALID_PARAMETER = 87
        ERROR_ACCESS_DENIED = 5
        ERROR_MOD_NOT_FOUND = 126  # arbitrary "other" code

        captured: dict[str, object] = {}

        class _FakeKernel32:
            def __init__(self) -> None:
                self.open_result: int = 0
                self.last_error: int = 0
                self.close_handle_called_with: int | None = None
                self.close_handle_call_count: int = 0

            def OpenProcess(self, _desired: int, _inherit: int, _pid: int) -> int:
                return self.open_result

            def CloseHandle(self, handle: int) -> bool:
                self.close_handle_called_with = handle
                self.close_handle_call_count += 1
                return True

        fake = _FakeKernel32()

        def _fake_win_dll(name: str, **kwargs: object) -> _FakeKernel32:
            captured["name"] = name
            captured["kwargs"] = kwargs
            return fake

        def _fake_get_last_error() -> int:
            return fake.last_error

        monkeypatch.setattr(real_ctypes, "WinDLL", _fake_win_dll)
        monkeypatch.setattr(real_ctypes, "get_last_error", _fake_get_last_error)

        # --- ERROR_INVALID_PARAMETER (87) => True (conclusive death) ---
        fake.open_result = 0
        fake.last_error = ERROR_INVALID_PARAMETER
        assert yd._is_pid_probe_conclusive(999) is True
        assert captured["name"] == "kernel32"
        assert captured["kwargs"].get("use_last_error") is True  # type: ignore[attr-defined]

        # --- ERROR_ACCESS_DENIED (5) => False (inconclusive) ---
        fake.open_result = 0
        fake.last_error = ERROR_ACCESS_DENIED
        assert yd._is_pid_probe_conclusive(999) is False

        # --- any other code => False (defensive default) ---
        fake.open_result = 0
        fake.last_error = ERROR_MOD_NOT_FOUND
        assert yd._is_pid_probe_conclusive(999) is False

        # --- non-zero handle => False, CloseHandle called with that handle ---
        fake.open_result = 0x1234
        assert yd._is_pid_probe_conclusive(999) is False
        assert fake.close_handle_called_with == 0x1234
        assert fake.close_handle_call_count == 1


class TestCookieArtefactCreationRaceAcrossProcesses:
    """Two-process proof of the VAL-602 creation-race closure.

    The child parks its single ``owner.pid`` write between ``mkdtemp`` and the
    real ``write_text`` using a two-marker-file barrier, so the parent can run the
    full sweep against a PID-less directory with no timing dependency. Against
    pre-fix source the sweep purges it and the discriminating assertion fails;
    with the default-deny grace it is retained. The child is a ``-c`` script on
    ``sys.executable`` and never touches ``msvcrt``/``fcntl``, so the test runs on
    Windows.
    """

    def test_pidless_dir_survives_concurrent_creation_sweep(self, tmp_path: Path) -> None:
        """A directory observed mid-creation (no owner.pid) survives the sweep."""
        import shutil
        import subprocess
        import time

        import vkdownloader.services.ytdlp_downloader as yd
        from vkdownloader.services.ytdlp_downloader import _sweep_stale_cookie_dirs

        # Both sync markers live in pytest's tmp_path, which is OUTSIDE the
        # system temp root the sweep scans, so they can never widen the sweep's
        # match set and are auto-cleaned by pytest. They carry non-matching names.
        created_marker = tmp_path / "created.marker"
        release_marker = tmp_path / "release.marker"

        original_started = yd._cookie_lifecycle_started
        cookie_dir: Path | None = None
        child: subprocess.Popen[bytes] | None = None
        try:
            child_code = (
                "import atexit, os, pathlib, sys, time\n"
                "import vkdownloader.services.ytdlp_downloader as yd\n"
                "created, release = sys.argv[1], sys.argv[2]\n"
                "real_write_text = pathlib.Path.write_text\n"
                "def patched_write_text(self, data, *a, **k):\n"
                "    if self.name == yd._OWNER_PID_FILENAME:\n"
                "        pathlib.Path(created).write_text(str(self.parent))\n"
                "        deadline = time.time() + 60.0\n"
                "        while not pathlib.Path(release).exists():\n"
                "            if time.time() >= deadline:\n"
                "                break\n"
                "            time.sleep(0.05)\n"
                "        return real_write_text(self, data, *a, **k)\n"
                "    return real_write_text(self, data, *a, **k)\n"
                "pathlib.Path.write_text = patched_write_text\n"
                "cookie_dir = yd._create_cookie_artifact_dir()\n"
                "atexit.unregister(yd._cleanup_cookie_artifact_dirs)\n"
                "print(str(os.getpid()), flush=True)\n"
                "print(str(cookie_dir), flush=True)\n"
            )
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    child_code,
                    str(created_marker),
                    str(release_marker),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for the child to signal "directory created, owner.pid not yet written".
            deadline = time.time() + 30.0
            while not created_marker.exists() and time.time() < deadline:
                if child.poll() is not None:
                    break
                time.sleep(0.05)
            assert created_marker.exists(), "child did not signal directory creation within 30s"
            cookie_dir = Path(created_marker.read_text().strip())

            assert cookie_dir.exists(), "child's cookie directory must exist"
            assert not (cookie_dir / yd._OWNER_PID_FILENAME).exists(), (
                "owner.pid must NOT exist while the child is parked (pre-write state)"
            )

            # The sweep must not destroy a PID-less directory mid-creation.
            # Pre-fix this purges it and the next assertion fails; post-fix the
            # grace retains it. No timing dependency: the child is parked for the
            # whole sweep.
            _sweep_stale_cookie_dirs()
            assert cookie_dir.exists(), (
                "mid-creation (PID-less) directory must survive the sweep (VAL-602 race closure)"
            )

            # Release the child so it completes the write_text and exits.
            release_marker.write_text("release")
            stdout, stderr = child.communicate(timeout=30.0)
            assert child.returncode == 0, (
                f"child exited {child.returncode}: {stderr.decode(errors='replace')}"
            )
            # owner.pid now holds the child's own PID -- confirming the write_text
            # past the barrier completed. Compare against the PID the child reports
            # on its own stdout (os.getpid()), not child.pid: the venv python.exe
            # spawns a launcher whose PID differs from the interpreter running code.
            out_lines = stdout.decode().strip().splitlines()
            assert len(out_lines) >= 2, f"unexpected child output: {stdout!r}"
            child_pid_reported = int(out_lines[0])
            owner_pid_text = (cookie_dir / yd._OWNER_PID_FILENAME).read_text().strip()
            assert int(owner_pid_text) == child_pid_reported, (
                "owner.pid must record the child process PID after release"
            )
            assert Path(out_lines[1]) == cookie_dir, (
                "child must report the same directory the marker named"
            )
        finally:
            # Safety: always release a parked child so it can finish or fail fast,
            # then let it exit before resorting to a kill (avoids orphaned grandchild).
            release_marker.write_text("release")
            if child is not None:
                try:
                    child.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    child.kill()
                    try:
                        child.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        pass
            created_marker.unlink(missing_ok=True)
            if cookie_dir is not None and cookie_dir.name.startswith(
                yd._COOKIE_ARTIFACT_PREFIX + yd._ARTEFACT_DIR_SUFFIX
            ):
                shutil.rmtree(cookie_dir, ignore_errors=True)
            yd._cookie_lifecycle_started = original_started


# ---------------------------------------------------------------------------


class TestB7SessionCarrierProtection:
    """SEC-008 (B7): session carrier must not leak through repr or logs."""

    CANARY = "b7_probesession_cookie_value_1234567890"

    def test_cookies_absent_from_repr_str_and_json_dump(self) -> None:
        """The canary session string must not appear in any model rendering.

        This test FAILS if SecretStr is replaced by Field(repr=False) alone:
        repr=False hides the field from repr/str, but model_dump_json()
        would then emit the raw secret in clear text. SecretStr's masked
        str() (**********) is the only mechanism that covers every rendering.
        """
        request = HLSDownloadRequest(
            video_url="https://vkvideo.ru/video-12345_67890",
            m3u8_url="https://example.com/video.m3u8",
            output_file=Path("out.mp4"),
            cookies=SecretStr(self.CANARY),
        )
        assert self.CANARY not in repr(request)
        assert self.CANARY not in str(request)
        assert self.CANARY not in request.model_dump_json()

    def test_session_value_not_leaked_through_configured_log_chain(self, tmp_path: Path) -> None:
        """The session value must not surface through a rendered log record.

        Driven through config.setup_logging (which wires redact_log_event as
        B6's processor) then structlog.get_logger, this test emits the cookies
        field as an event value. The B6 processor (redact_log_event) applies
        sanitize_text_for_log only to str-typed values — a flat session string
        carries no http(s):// URL and no vk_cookies_* artefact shape, so B6 is
        the IDENTITY on it and passes it through unchanged. Protection MUST
        therefore come from SecretStr: structlog's JSONRenderer falls back to
        str(), SecretStr.__str__ returns '**********', and the canary never
        reaches the log. A plain-str cookies field (Field(repr=False) alone)
        would fail this test.
        """
        log_file = tmp_path / "audit.log"
        log_settings = Settings(
            log_file=log_file,
            log_level=LogLevel.DEBUG,
            max_concurrent_downloads=2,
            max_retries=1,
        )

        # --- Save global state so we can restore it (setup_logging mutates) ---
        original_structlog_config = structlog.get_config()
        root_logger = logging.getLogger()
        original_root_handlers = root_logger.handlers[:]
        original_root_level = root_logger.level

        try:
            setup_logging(log_settings)

            request = HLSDownloadRequest(
                video_url="https://vkvideo.ru/video-12345_67890",
                m3u8_url="https://example.com/video.m3u8",
                output_file=Path("out.mp4"),
                cookies=SecretStr(self.CANARY),
            )

            # Emit the SecretStr itself (not .get_secret_value()) — this is
            # the realistic logging pattern where an operator logs the field.
            logger = structlog.get_logger()
            logger.debug("b7_probe", cookies=request.cookies)

            log_content = log_file.read_text()
            assert self.CANARY not in log_content, (
                f"canary leaked through log chain; got:\n{log_content}"
            )
        finally:
            root_logger.handlers = original_root_handlers
            root_logger.setLevel(original_root_level)
            structlog.configure(**original_structlog_config)

    @pytest.mark.asyncio
    async def test_secret_str_cookie_unwraps_to_wire_header_through_live_server(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Retrievability: SecretStr unwraps to a real Cookie header on the wire.

        Starts a live local aiohttp server, drives download_hls_with_resume
        with cookies=SecretStr(CANARY), and asserts the server received the
        canary byte-for-byte as the Cookie header. This makes the fix
        unsatisfiable by destruction: a change that blanks the field at
        construction (cookies=None) would pass the repr/canary tests but
        fail here because the server would receive no Cookie header at all.
        """
        captured_cookies: list[str] = []

        async def handle_playlist(req: web.Request) -> web.Response:
            captured_cookies.append(req.headers.get("Cookie", ""))
            # seg0.ts is resolved against the playlist URL by _download_segment_concurrent
            playlist = "#EXTM3U\nseg0.ts\n"
            return web.Response(text=playlist, content_type="application/vnd.apple.mpegurl")

        async def handle_segment(req: web.Request) -> web.Response:
            return web.Response(body=b"fake-segment-data")

        app = web.Application()
        app.router.add_get("/playlist.m3u8", handle_playlist)
        app.router.add_get("/{segment}", handle_segment)

        # --- Mock the context-var-based shutdown event ---
        # Both segment_downloader (6 call sites) and downloader_throttle
        # (_retry_429_with_backoff) call get_shutdown_event, so patch both.
        mock_shutdown = MagicMock()
        mock_shutdown.is_set.return_value = False
        mock_shutdown.wait = AsyncMock()

        with (
            patch(
                "vkdownloader.services.segment_downloader.get_shutdown_event",
                return_value=mock_shutdown,
            ),
            patch(
                "vkdownloader.services.downloader_throttle.get_shutdown_event",
                return_value=mock_shutdown,
            ),
            patch(
                "vkdownloader.services.segment_downloader._merge_segments_batched",
                AsyncMock(return_value=tmp_path / "video.mp4"),
            ),
        ):
            async with TestServer(app) as server:
                playlist_url = f"http://{server.host}:{server.port}/playlist.m3u8"

                await download_hls_with_resume(
                    HLSDownloadRequest(
                        video_url="https://vkvideo.ru/video-12345_67890",
                        m3u8_url=playlist_url,
                        output_file=tmp_path / "video.mp4",
                        cookies=SecretStr(self.CANARY),
                    ),
                    settings=test_settings,
                )

        # At least the playlist request must have carried the Cookie header.
        assert captured_cookies, (
            "server received no requests — cannot verify Cookie header on the wire"
        )
        assert self.CANARY in captured_cookies[0], (
            f"wire Cookie header must carry the unwrapped canary value; "
            f"got Cookie={captured_cookies[0]!r}"
        )
