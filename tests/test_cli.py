"""Tests for CLI commands using typer.testing.CliRunner."""

import asyncio
import locale
import re
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from vkdownloader import cli
from vkdownloader.cli import app
from vkdownloader.exceptions import (
    QualityNotAvailableError,
    QualityParseError,
    VideoNotFoundError,
)
from vkdownloader.models.enums import CookieSource, ProgressStatus, QualityEnum
from vkdownloader.services import batch_downloader
from vkdownloader.services.downloader import download_video as _real_download_video
from vkdownloader.services.progress_display import RichProgressReporter

runner = CliRunner()

_REFERENCE_DOCS = Path(__file__).resolve().parent.parent / "docs" / "99-reference"
_REFERENCE_DOC_NAMES = ("cli-reference.md", "cli-reference-clean.md")
_COMMAND_HEADING = re.compile(r"^### \d+\. `([a-z]+)`")
_EXIT_CODE_ROW = re.compile(r"^\|\s*`(\d+)`\s*\|")


def _documented_exit_codes(doc_path: Path) -> dict[str, set[int]]:
    """Extract the exit codes each command documents, keyed by command name."""
    codes: dict[str, set[int]] = {}
    command: str | None = None
    in_exit_table = False
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        heading = _COMMAND_HEADING.match(line)
        if heading is not None:
            command = heading.group(1)
            in_exit_table = False
            continue
        if line.strip() == "**Exit codes:**":
            in_exit_table = True
            continue
        if not in_exit_table:
            continue
        row = _EXIT_CODE_ROW.match(line)
        if row is not None:
            assert command is not None, f"exit-code row outside a command section: {line}"
            codes.setdefault(command, set()).add(int(row.group(1)))
        elif line.strip() and not line.startswith("|"):
            in_exit_table = False
    return codes


def _is_undecodable(payload: bytes, encoding: str) -> bool:
    """Report whether ``payload`` cannot be decoded with ``encoding``."""
    try:
        payload.decode(encoding)
    except UnicodeDecodeError:
        return True
    return False


def _undecodable_byte() -> int:
    """Return a byte that is invalid as UTF-8 and in the platform's default encoding.

    ``Path.read_text()`` decodes with the platform's preferred encoding, which is
    not UTF-8 on a default Windows install, so a payload built for UTF-8 alone
    would be readable there. The byte is therefore required to be undecodable in
    both, so the caller cannot silently stop exercising the failure it needs.
    """
    platform_encoding = locale.getpreferredencoding(False)
    for candidate in range(0x80, 0x100):
        if _is_undecodable(bytes([candidate]), "utf-8") and _is_undecodable(
            bytes([candidate]), platform_encoding
        ):
            return candidate
    raise AssertionError(f"no byte is undecodable as utf-8 and as {platform_encoding}")


class TestDownloadCommand:
    """Tests for the download CLI command."""

    def test_download_success(
        self, tmp_path: Path, sample_video_url: str, mock_m3u8_content: str
    ) -> None:
        """Verify successful invocation of download command."""
        mock_streams = [
            MagicMock(
                url="https://example.com/1080p.m3u8",
                quality="1080",
                height=1080,
                width=1920,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams)
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080", "720"]
            mock_selector.select.return_value = MagicMock(quality="1080")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "test_video_1080.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        download_dir=tmp_path,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["download", sample_video_url],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        assert "Downloaded:" in result.output

    def test_download_invalid_url(self, tmp_path: Path) -> None:
        """Check error handling for bad URLs."""
        invalid_url = "https://example.com/invalid"

        with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
            with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                mock_settings_cls.return_value = MagicMock(log_file=None)
                result = runner.invoke(
                    app,
                    ["download", invalid_url],
                    catch_exceptions=False,
                )

        assert result.exit_code == 1
        assert "Invalid URL format" in result.output
        assert "Traceback" not in result.output

    def test_download_keyboard_interrupt(
        self, tmp_path: Path, sample_video_url: str, mock_m3u8_content: str
    ) -> None:
        """Check that KeyboardInterrupt is handled with proper exit code."""
        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(side_effect=KeyboardInterrupt())
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080", "720"]
            mock_selector.select.return_value = MagicMock(quality="1080")
            mock_selector_cls.return_value = mock_selector

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(log_file=None)
                    result = runner.invoke(
                        app,
                        ["download", sample_video_url],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 130
        assert "cancelled" in result.output.lower()


class TestBatchCommand:
    """Tests for the batch CLI command."""

    def test_batch_empty_file(self, tmp_path: Path) -> None:
        """Check handling of empty batch input file."""
        empty_file = tmp_path / "empty_urls.txt"
        empty_file.write_text("")

        result = runner.invoke(
            app,
            ["batch", str(empty_file)],
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "No URLs found" in result.output

    def test_batch_file_with_comments_only(self, tmp_path: Path) -> None:
        """Check handling of batch file with only comments."""
        comment_file = tmp_path / "comments_only.txt"
        comment_file.write_text("# Comment 1\n# Comment 2\n")

        result = runner.invoke(
            app,
            ["batch", str(comment_file)],
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "No URLs found" in result.output

    def test_batch_file_with_whitespace_only(self, tmp_path: Path) -> None:
        """Check handling of batch file with only whitespace."""
        whitespace_file = tmp_path / "whitespace.txt"
        whitespace_file.write_text("   \n\n\t\n")

        result = runner.invoke(
            app,
            ["batch", str(whitespace_file)],
            catch_exceptions=False,
        )

        assert result.exit_code == 1
        assert "No URLs found" in result.output

    def test_batch_statistics_summary(self, tmp_path: Path) -> None:
        """Check that batch download summary includes failed URLs with error reasons."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\nhttps://vkvideo.ru/video-2_2\n")

        call_count = [0]

        def mock_extract_side_effect(*args: object) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(id="video1", streams=[])
            raise VideoNotFoundError("Video not found")

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(side_effect=mock_extract_side_effect)
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["720"]
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 1
        assert "Download Summary:" in result.output
        assert "Total connections:" in result.output
        assert "Peak concurrent videos:" in result.output
        assert "Successful:" in result.output
        assert "Failed:" in result.output
        # TST-002: Assert error reasons appear in Failed URLs section
        assert "Failed URLs:" in result.output
        assert "video_not_found" in result.output
        assert "video-2_2" in result.output

    def test_batch_all_success_exits_zero(self, tmp_path: Path) -> None:
        """Check that batch exits with code 0 when all downloads succeed."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="video1", streams=[MagicMock(quality="720")])
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        assert "Download Summary:" in result.output
        assert "Successful:" in result.output

    def test_batch_skip_invalid_urls(self, tmp_path: Path) -> None:
        """Check that invalid URLs are skipped with a warning before download starts."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "https://example.com/invalid\n"
            "https://vkvideo.ru/video-1_1\n"
            "https://vkvideo.ru/video-2_2\n"
        )

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="video1", streams=[MagicMock(quality="720")])
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        assert "Skipped 1 invalid URL" in result.output
        assert "Skipped (invalid URLs): 1" in result.output
        assert "Total connections: 2" in result.output

    def test_batch_start_finish_task_per_url(self, tmp_path: Path) -> None:
        """AC1/R1: each active download gets start_task and finish_task calls."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\nhttps://vkvideo.ru/video-2_2\n")

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter"
            ) as mock_reporter_cls,
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="video1", title="Test Title", streams=[MagicMock(quality="720")]
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        reporter = mock_reporter_cls.return_value
        assert reporter.start_task.call_count == 2
        reporter.start_task.assert_any_call(0)
        reporter.start_task.assert_any_call(1)
        assert reporter.finish_task.call_count == 2
        reporter.finish_task.assert_any_call(0, ProgressStatus.SUCCESS)
        reporter.finish_task.assert_any_call(1, ProgressStatus.SUCCESS)

    def test_batch_non_tty_reporter_logs_progress(self, tmp_path: Path) -> None:
        """AC1/R7: real reporter in non-TTY mode logs progress callbacks via structlog."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        async def drive_progress(*args: object, **kwargs: object) -> Path:
            cb = kwargs.get("progress_callback")
            if cb is not None and callable(cb):
                cb("video_1", 50, 100)
            return tmp_path / "video1.mp4"

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch(
                "vkdownloader.services.downloader.perform_download",
                side_effect=drive_progress,
            ),
            patch("vkdownloader.services.progress_display.logger") as mock_logger,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="video1", title="Test Title", streams=[MagicMock(quality="720")]
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        mock_logger.info.assert_any_call(
            "download_progress",
            video_index=0,
            video_label="video_0: Test Title",
            downloaded=50,
            total=100,
        )
        mock_logger.info.assert_any_call(
            "download_finished",
            video_index=0,
            video_label="video_0: Test Title",
            status="success",
            downloaded=50,
            total=100,
        )

    def test_batch_status_lines_success_and_failed(self, tmp_path: Path) -> None:
        """AC3/R3: success and failure produce correct finish_task statuses."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\nhttps://vkvideo.ru/video-2_2\n")

        async def mixed_outcome(*args: object, **kwargs: object) -> Path:
            url = str(args[0])
            if "video-1_1" in url:
                return tmp_path / "video1.mp4"
            raise VideoNotFoundError("Not found")

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter"
            ) as mock_reporter_cls,
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch(
                "vkdownloader.services.downloader.perform_download",
                side_effect=mixed_outcome,
            ),
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="video1", title="Test Title", streams=[MagicMock(quality="720")]
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 1
        reporter = mock_reporter_cls.return_value
        reporter.finish_task.assert_any_call(0, ProgressStatus.SUCCESS)
        reporter.finish_task.assert_any_call(1, ProgressStatus.FAILED)

    def test_batch_cancelled_produces_cancelled_status(self, tmp_path: Path) -> None:
        """Cancellation: finish_task called with CANCELLED status."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        async def raise_cancelled(*args: object, **kwargs: object) -> Path:
            raise asyncio.CancelledError()

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter"
            ) as mock_reporter_cls,
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch(
                "vkdownloader.services.downloader.perform_download",
                side_effect=raise_cancelled,
            ),
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="video1", title="Test Title", streams=[MagicMock(quality="720")]
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        reporter = mock_reporter_cls.return_value
        reporter.finish_task.assert_any_call(0, ProgressStatus.CANCELLED)
        assert result.exit_code == 130

    def test_batch_echo_suppressed_when_reporter_enabled(self, tmp_path: Path) -> None:
        """R5/AC2: echo=False when reporter.is_enabled is True."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter"
            ) as mock_reporter_cls,
            patch("vkdownloader.services.batch_downloader.download_video") as mock_dv,
        ):
            mock_reporter = mock_reporter_cls.return_value
            mock_reporter.is_enabled = True
            mock_dv.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        mock_dv.assert_called_once()
        assert mock_dv.call_args.kwargs["echo"] is False

    def test_batch_echo_not_suppressed_when_reporter_disabled(self, tmp_path: Path) -> None:
        """R5/AC2: echo=True when reporter.is_enabled is False."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter"
            ) as mock_reporter_cls,
            patch("vkdownloader.services.batch_downloader.download_video") as mock_dv,
        ):
            mock_reporter = mock_reporter_cls.return_value
            mock_reporter.is_enabled = False
            mock_dv.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        mock_dv.assert_called_once()
        assert mock_dv.call_args.kwargs["echo"] is True

    def test_batch_title_callback_reaches_reporter(self, tmp_path: Path) -> None:
        """R8: title_callback received by download_video reaches reporter.set_title."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter"
            ) as mock_reporter_cls,
            patch("vkdownloader.services.batch_downloader.download_video") as mock_dv,
        ):
            mock_reporter = mock_reporter_cls.return_value
            mock_dv.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        mock_dv.assert_called_once()
        title_cb = mock_dv.call_args.kwargs.get("title_callback")
        assert title_cb is not None
        assert callable(title_cb)
        title_cb("My Sanitized Title")
        mock_reporter.set_title.assert_called_once_with(0, "My Sanitized Title")

    def test_batch_old_progress_polling_removed(self, tmp_path: Path) -> None:
        """R5/T7: _poll_progress_display, _format_progress, and _progress_manager are gone."""
        assert not hasattr(batch_downloader, "_poll_progress_display")
        assert not hasattr(batch_downloader, "_format_progress")
        assert not hasattr(batch_downloader, "_create_progress_callback")
        assert not hasattr(batch_downloader, "_progress_manager")
        assert not hasattr(batch_downloader, "ProgressManager")

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with (
            patch("vkdownloader.services.batch_downloader.RichProgressReporter"),
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="video1", title="Test Title", streams=[MagicMock(quality="720")]
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        assert "\r" not in result.output

    def test_batch_no_escape_codes_under_cli_runner(self, tmp_path: Path) -> None:
        """AC5: CliRunner output has no escape codes or carriage returns."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\nhttps://vkvideo.ru/video-2_2\n")

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="video1", title="Test Title", streams=[MagicMock(quality="720")]
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        assert "\x1b" not in result.output
        assert "\r" not in result.output

    def test_batch_reporter_started_and_stopped(self, tmp_path: Path) -> None:
        """R7: reporter.start() and reporter.stop() both called."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter"
            ) as mock_reporter_cls,
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="video1", title="Test Title", streams=[MagicMock(quality="720")]
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        reporter = mock_reporter_cls.return_value
        reporter.start.assert_called_once()
        reporter.stop.assert_called_once()

    def test_batch_real_reporter_renders_concurrent_progress(self, tmp_path: Path) -> None:
        """AC1/R1/R5: a real enabled reporter renders per-video progress through the batch path.

        Every batch test today either mocks ``RichProgressReporter`` (so nothing
        renders) or runs under ``CliRunner`` (non-TTY, so ``is_enabled`` is False
        and only the structlog fallback runs). This substitutes a real, enabled
        reporter wired to an in-memory console and drives the real callbacks,
        proving the enabled render path end-to-end.
        """
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\nhttps://vkvideo.ru/video-2_2\n")

        buffer = StringIO()
        real_reporter = RichProgressReporter(
            console=Console(file=buffer, width=120, no_color=True),
            enabled=True,
        )

        async def drive_progress(url: str, *args: object, **kwargs: object) -> Path:
            progress_cb = kwargs.get("progress_callback")
            if progress_cb is not None and callable(progress_cb):
                progress_cb("video_segment", 50, 100)
            return tmp_path / "download.mp4"

        mock_extractor = MagicMock()
        mock_extractor.extract_streams = AsyncMock(
            side_effect=[
                MagicMock(id="v1", title="Alpha Title", streams=[MagicMock(quality="720")]),
                MagicMock(id="v2", title="Beta Title", streams=[MagicMock(quality="720")]),
            ]
        )

        with (
            patch(
                "vkdownloader.services.batch_downloader.RichProgressReporter",
                return_value=real_reporter,
            ),
            patch(
                "vkdownloader.services.batch_downloader.download_video",
                wraps=_real_download_video,
            ) as mock_dv,
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch(
                "vkdownloader.services.downloader.perform_download",
                side_effect=drive_progress,
            ),
        ):
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        max_retries=3,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["batch", str(urls_file)],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0
        output = buffer.getvalue()
        # AC1: each active download shows a dedicated progress line.
        assert "video_0" in output
        assert "video_1" in output
        # R1/R2: titles driven through title_callback (invoked by download_video
        # after extraction) render in the display.
        assert "Alpha Title" in output
        assert "Beta Title" in output
        # R5: the success outcome renders the "done" marker.
        assert "done" in output
        # R9/AC8: a percentage column is rendered for known-total progress.
        assert "%" in output
        # R5/AC2: echo suppression is derived from the enabled reporter, so the
        # real download_video (observed via its wraps spy) is invoked with
        # echo=False; download_video forwards echo unchanged to perform_download.
        assert mock_dv.call_count == 2
        for call in mock_dv.call_args_list:
            assert call.kwargs["echo"] is False


class TestQualityOptionValidation:
    """Tests for quality enum validation in CLI."""

    def test_quality_not_available_error(self, tmp_path: Path, sample_video_url: str) -> None:
        """Check that requesting unavailable quality shows helpful error message."""
        mock_streams = [
            MagicMock(
                url="https://example.com/1080p.m3u8",
                quality="1080",
                height=1080,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download"),
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams)
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080", "720"]
            mock_selector.select.side_effect = QualityNotAvailableError(
                "1440", ["1080", "720", "480", "360", "240", "144"]
            )
            mock_selector_cls.return_value = mock_selector

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(log_file=None)
                    result = runner.invoke(
                        app,
                        ["download", sample_video_url, "--quality", "1440"],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 1
        assert "Requested quality '1440p' is not available" in result.output
        assert "Available qualities:" in result.output

    def test_invalid_quality_option(self, tmp_path: Path) -> None:
        """Check quality enum validation rejects invalid values."""
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890", "--quality", "invalid_quality"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0

    def test_valid_quality_option_accepted(self, tmp_path: Path, sample_video_url: str) -> None:
        """Check that valid quality options are accepted."""
        mock_streams = [
            MagicMock(
                url="https://example.com/720p.m3u8",
                quality="720",
                height=720,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams)
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["720", "480"]
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "test_video_720.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(log_file=None)
                    result = runner.invoke(
                        app,
                        ["download", sample_video_url, "--quality", "720"],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0


class TestMethodOptionValidation:
    """Tests for method enum validation in CLI."""

    def test_invalid_method_option(self, tmp_path: Path) -> None:
        """Check method enum validation rejects invalid values."""
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890", "--method", "invalid_method"],
            catch_exceptions=False,
        )

        assert result.exit_code != 0

    def test_valid_method_option_accepted(self, tmp_path: Path, sample_video_url: str) -> None:
        """Check that valid method options are accepted."""
        mock_streams = [
            MagicMock(
                url="https://example.com/720p.m3u8",
                quality="720",
                height=720,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams)
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["720"]
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "test_video_720.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(log_file=None)
                    result = runner.invoke(
                        app,
                        ["download", sample_video_url, "--method", "yt-dlp"],
                        catch_exceptions=False,
                    )

        assert result.exit_code == 0


class TestSslVerifyOption:
    """Tests for SSL verify option in CLI."""

    def test_ssl_verify_default_true(self, tmp_path: Path, sample_video_url: str) -> None:
        """Check that ssl_verify defaults to True and is passed to Settings."""
        mock_streams = [
            MagicMock(
                url="https://example.com/720p.m3u8",
                quality="720",
                height=720,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams)
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["720"]
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "test_video_720.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        download_dir=tmp_path,
                        ssl_verify=True,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["download", sample_video_url],
                        catch_exceptions=False,
                    )

                    # Verify Settings was called with ssl_verify=True (default)
                    mock_settings_cls.assert_called_once()
                    call_kwargs = mock_settings_cls.call_args[1]
                    assert call_kwargs.get("ssl_verify", True) is True

        assert result.exit_code == 0

    def test_no_ssl_verify_flag(self, tmp_path: Path, sample_video_url: str) -> None:
        """Check that --no-ssl-verify flag sets ssl_verify to False."""
        mock_streams = [
            MagicMock(
                url="https://example.com/720p.m3u8",
                quality="720",
                height=720,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams)
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["720"]
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "test_video_720.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(
                        max_concurrent_downloads=4,
                        download_dir=tmp_path,
                        ssl_verify=False,
                        log_file=None,
                    )

                    result = runner.invoke(
                        app,
                        ["download", sample_video_url, "--no-ssl-verify"],
                        catch_exceptions=False,
                    )

                    # Verify Settings was called with ssl_verify=False
                    mock_settings_cls.assert_called_once()
                    call_kwargs = mock_settings_cls.call_args[1]
                    assert call_kwargs.get("ssl_verify") is False

        assert result.exit_code == 0


class TestConfigurationErrors:
    """Tests for graceful handling of Settings validation errors."""

    def test_download_file_cookie_source_rejected_at_parsing(self) -> None:
        """Verify --cookie-source file is rejected at Typer parsing (not deferred to Settings)."""
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890", "--cookie-source", "file"],
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "file" in result.output.lower()
        assert "Traceback" not in result.output

    def test_batch_file_cookie_source_rejected_at_parsing(self, tmp_path: Path) -> None:
        """Verify --cookie-source file is rejected at Typer parsing for batch command."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n")

        result = runner.invoke(
            app,
            ["batch", str(urls_file), "--cookie-source", "file"],
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "file" in result.output.lower()
        assert "Traceback" not in result.output

    def test_batch_unreadable_url_file_error(self, tmp_path: Path) -> None:
        """Verify unreadable URL file produces clean error, not raw traceback."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n")

        with patch.object(Path, "read_text", side_effect=PermissionError("Permission denied")):
            result = runner.invoke(
                app,
                ["batch", str(urls_file)],
            )

            assert result.exit_code == 1
            assert "Failed to read URL file" in result.output
            assert "Traceback" not in result.output

    def test_download_invalid_env_var_shows_concise_error(self, tmp_path: Path) -> None:
        """Verify invalid VKDOWNLOADER_* env var produces concise error with field info."""
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890"],
            env={"VKDOWNLOADER_MAX_RETRIES": "notanint"},
        )

        assert result.exit_code == 1
        assert "Configuration error" in result.output
        assert "max_retries" in result.output
        assert "Traceback" not in result.output


class TestCliHelp:
    """Tests for CLI help output."""

    def test_download_help(self) -> None:
        """Verify download command help is available."""
        result = runner.invoke(app, ["download", "--help"])

        assert result.exit_code == 0
        assert "VK Video URL" in result.output or "url" in result.output.lower()

    def test_batch_help(self) -> None:
        """Verify batch command help is available."""
        result = runner.invoke(app, ["batch", "--help"])

        assert result.exit_code == 0
        assert "file" in result.output.lower() or "urls" in result.output.lower()

    def test_main_help(self) -> None:
        """Verify main CLI help is available."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "download" in result.output or "vkdownloader" in result.output.lower()


class TestBatchErrorHandler:
    """D-03: the batch error handler must survive failures raised before URL parsing."""

    def test_batch_non_utf8_url_file_reports_designed_error(self, tmp_path: Path) -> None:
        """A URL file that is not valid UTF-8 must print the designed message and exit 1.

        ``urls_file.read_text()`` raises ``UnicodeDecodeError``, which subclasses
        ``ValueError`` rather than ``OSError``, so it reaches the generic handler
        rather than the OSError arm. The handler reports ``len(valid_urls)``, so
        this also pins that the read path is covered by the handler at all.
        """
        urls_file = tmp_path / "urls.txt"
        urls_file.write_bytes(
            b"https://vkvideo.ru/video-12345_67890\n" + bytes([_undecodable_byte()]) + b"\n"
        )

        result = runner.invoke(app, ["batch", str(urls_file)], catch_exceptions=False)

        assert result.exit_code == 1
        assert "An error occurred during batch download" in result.output
        assert "UnboundLocalError" not in result.output

    def test_batch_non_utf8_env_file_reports_designed_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ``.env`` that is not valid UTF-8 must print the designed message and exit 1.

        ``Settings`` and ``warn_unknown_env_vars()`` both read ``.env`` from the
        working directory before the URL file is touched, so a malformed ``.env``
        raises above the binding the handler reports. Before the fix the handler
        itself raised ``UnboundLocalError``: the designed message never printed,
        the intended exit code never happened, and the process died with a raw
        traceback. ``catch_exceptions=False`` makes that failure mode observable —
        the exception propagates out of ``runner.invoke`` and errors the test.
        """
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")
        (tmp_path / ".env").write_bytes(
            b"VKDOWNLOADER_LOG_LEVEL=" + bytes([_undecodable_byte()]) + b"\n"
        )
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["batch", str(urls_file)], catch_exceptions=False)

        assert result.exit_code == 1
        assert "An error occurred during batch download" in result.output
        assert "UnboundLocalError" not in result.output

    def test_batch_failure_before_url_file_read_reports_designed_error(
        self, tmp_path: Path
    ) -> None:
        """A failure raised above the URL file read must not break the error handler.

        ``warn_unknown_env_vars()`` runs before the URL file is read, so raising
        from it reproduces the D-03 ``UnboundLocalError`` on the same path without
        depending on file encodings.
        """
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        with patch(
            "vkdownloader.cli.warn_unknown_env_vars",
            side_effect=RuntimeError("environment scan failed"),
        ):
            result = runner.invoke(app, ["batch", str(urls_file)], catch_exceptions=False)

        assert result.exit_code == 1
        assert "An error occurred during batch download" in result.output
        assert "UnboundLocalError" not in result.output


class TestQualityRecoveryHint:
    """D-05 part 1: the recovery hint must name only values the parser accepts."""

    def test_quality_recovery_hint_names_only_accepted_values(
        self, tmp_path: Path, sample_video_url: str
    ) -> None:
        """Every value printed in "Use one of:" must be a valid ``QualityEnum`` value.

        The ``except QualityParseError`` arm is unreachable through a normal CLI
        invocation: ``--quality`` is typed ``QualityEnum``, so Click rejects an
        unknown value at parse time and the command body never runs. The test
        therefore forces the producer — ``_parse_quality_to_enum``, the only
        function that raises ``QualityParseError`` — by patching it to raise, and
        asserts on the message the CLI actually prints.
        """
        stream = MagicMock(url="https://example.com/preselected.m3u8", quality="best", height=None)
        video = MagicMock(id="12345_67890", title=None, streams=[stream])

        with (
            patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
                new_callable=AsyncMock,
                return_value=video,
            ),
            patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                new_callable=AsyncMock,
                return_value=([stream], None, None),
            ),
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch(
                "vkdownloader.services.ytdlp_downloader._parse_quality_to_enum",
                side_effect=QualityParseError("720p"),
            ) as mock_parse_quality,
            patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path),
        ):
            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["best"]
            mock_selector.select.return_value = stream
            mock_selector_cls.return_value = mock_selector

            result = runner.invoke(
                app,
                ["download", sample_video_url, "--cookie-source", "browser"],
                catch_exceptions=False,
            )

        assert mock_parse_quality.call_count > 0, "the producer was never reached"
        assert result.exit_code == 1
        assert "Invalid quality value: 720p" in result.output

        hint = result.output.split("Use one of: ", 1)[1].splitlines()[0].rstrip(".")
        printed = {name.strip() for name in hint.split(",") if name.strip()}
        accepted = {member.value for member in QualityEnum}

        assert printed, "the recovery hint listed no values"
        for name in sorted(printed):
            assert name in accepted, f"recovery hint names '{name}', which the parser rejects"
        assert printed == accepted, "the recovery hint does not list every accepted quality"


class TestExitCodeContract:
    """D-05 part 2: the documented exit codes must match the values actually emitted."""

    def test_every_observable_exit_code_is_documented(
        self, tmp_path: Path, sample_video_url: str
    ) -> None:
        """Every exit code the process can emit must be documented for both commands.

        The four values are observed by invoking the CLI, not assumed:

        * ``0``   — ``download`` with the download service mocked to succeed.
        * ``1``   — ``download`` with a URL that is not a VK video URL, which the
          command maps to its own "Invalid URL format" handler.
        * ``2``   — ``download --quality 720p``: a value the argument parser
          rejects, so the command body never runs. The same value is produced by
          a missing argument, an unknown command and an unknown option.
        * ``130`` — ``download`` interrupted with ``KeyboardInterrupt`` from the
          extraction layer, which the command maps to its cancellation handler.
        """
        observed = self._observe_exit_codes(tmp_path, sample_video_url)

        assert set(observed) == {0, 1, 2, 130}, observed

        for doc_name in _REFERENCE_DOC_NAMES:
            documented = _documented_exit_codes(_REFERENCE_DOCS / doc_name)
            assert documented.get("download") == {0, 1, 2, 130}, doc_name
            assert documented.get("batch") == {0, 1, 2, 130}, doc_name

    @staticmethod
    def _observe_exit_codes(tmp_path: Path, sample_video_url: str) -> dict[int, str]:
        """Invoke the CLI once per observable exit code and record how it arose."""
        observed: dict[int, str] = {}

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(
                    id="12345_67890",
                    streams=[MagicMock(url="https://example.com/1080.m3u8", quality="1080")],
                )
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080"]
            mock_selector.select.return_value = MagicMock(quality="1080")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video_1080.mp4"

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(log_file=None)
                    result = runner.invoke(
                        app,
                        ["download", sample_video_url],
                        catch_exceptions=False,
                    )
        observed.setdefault(result.exit_code, "download succeeded with a mocked download")

        result = runner.invoke(
            app,
            ["download", "https://example.com/invalid"],
            catch_exceptions=False,
        )
        observed.setdefault(result.exit_code, "download rejected a non-VK URL")

        result = runner.invoke(
            app,
            ["download", sample_video_url, "--quality", "720p"],
            catch_exceptions=False,
        )
        observed.setdefault(result.exit_code, "parser rejected the --quality value '720p'")

        with patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls:
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(side_effect=KeyboardInterrupt())
            mock_extractor_cls.return_value = mock_extractor

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(log_file=None)
                    result = runner.invoke(
                        app,
                        ["download", sample_video_url],
                        catch_exceptions=False,
                    )
        observed.setdefault(result.exit_code, "download interrupted by KeyboardInterrupt")

        return observed


class TestEntryPointSourcePrecedence:
    """A1-A4: the .env file and CLI options both reach the Settings that runs.

    These tests deliberately do **not** patch ``vkdownloader.cli.Settings`` — the
    real model is constructed so the ``.env`` file and ``VKDOWNLOADER_*`` variables
    are exercised end to end.  Deep consumers are patched instead of the service
    boundary so the identity assertion (A4) observes the real chain rather than a
    stub's copy.
    """

    # The .env written by A1/A2 — also used as a positive control via
    # VKDOWNLOADER_THROTTLED_RATE, which this block does not touch.
    _ENV_CONTENT = (
        "VKDOWNLOADER_COOKIE_SOURCE=browser\n"
        "VKDOWNLOADER_SSL_VERIFY=false\n"
        "VKDOWNLOADER_MAX_RETRIES=5\n"
        "VKDOWNLOADER_THROTTLED_RATE=200000\n"
    )

    @staticmethod
    def _write_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Write the shared .env into tmp_path and chdir into it."""
        (tmp_path / ".env").write_text(
            TestEntryPointSourcePrecedence._ENV_CONTENT,
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

    # ---- A1: .env reaches all three fields + positive control -------------

    def test_a1_env_reaches_fields_download(
        self,
        tmp_path: Path,
        sample_video_url: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A1 (download): .env values reach cookie_source, ssl_verify, max_retries."""
        self._write_env(tmp_path, monkeypatch)
        mock_streams = [
            MagicMock(
                url="https://example.com/1080.m3u8",
                quality="1080",
                height=1080,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
            patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path),
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams),
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080"]
            mock_selector.select.return_value = MagicMock(quality="1080")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video.mp4"

            result = runner.invoke(
                app,
                ["download", sample_video_url],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        settings_arg = mock_download.call_args.args[5]
        assert settings_arg.cookie_source == CookieSource.BROWSER
        assert settings_arg.ssl_verify is False
        assert settings_arg.max_retries == 5
        # Positive control — a field this block does not touch, proving the
        # .env file actually reached the model.
        assert settings_arg.throttled_rate == 200000

    def test_a1_env_reaches_fields_batch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A1 (batch): .env values reach cookie_source, ssl_verify, max_retries."""
        self._write_env(tmp_path, monkeypatch)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        with (
            patch("vkdownloader.services.batch_downloader.RichProgressReporter"),
            patch(
                "vkdownloader.services.batch_downloader.download_video",
            ) as mock_dv,
            patch("vkdownloader.services.batch_downloader.setup_signal_handlers"),
            patch("vkdownloader.services.batch_downloader.cleanup_signal_handlers"),
            patch(
                "vkdownloader.utils.security.validate_output_path",
                return_value=tmp_path,
            ),
        ):
            mock_dv.return_value = tmp_path / "video.mp4"

            result = runner.invoke(
                app,
                ["batch", str(urls_file)],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        settings_arg = mock_dv.call_args.args[4]
        assert settings_arg.cookie_source == CookieSource.BROWSER
        assert settings_arg.ssl_verify is False
        assert settings_arg.max_retries == 5
        # Positive control.
        assert settings_arg.throttled_rate == 200000

    # ---- A2: options beat the .env ---------------------------------------

    def test_a2_options_override_env_download(
        self,
        tmp_path: Path,
        sample_video_url: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A2 (download): CLI options win over .env values."""
        self._write_env(tmp_path, monkeypatch)
        mock_streams = [
            MagicMock(
                url="https://example.com/1080.m3u8",
                quality="1080",
                height=1080,
            ),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
            patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path),
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams),
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080"]
            mock_selector.select.return_value = MagicMock(quality="1080")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video.mp4"

            result = runner.invoke(
                app,
                [
                    "download",
                    sample_video_url,
                    "--cookie-source",
                    "none",
                    "--ssl-verify",
                    "--max-retries",
                    "7",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        settings_arg = mock_download.call_args.args[5]
        # Options beat .env: .env says browser / false / 5
        assert settings_arg.cookie_source == CookieSource.NONE
        assert settings_arg.ssl_verify is True
        assert settings_arg.max_retries == 7
        # Positive control — still resolves from .env.
        assert settings_arg.throttled_rate == 200000

    def test_a2_options_override_env_batch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A2 (batch): CLI options win over .env values."""
        self._write_env(tmp_path, monkeypatch)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        with (
            patch("vkdownloader.services.batch_downloader.RichProgressReporter"),
            patch(
                "vkdownloader.services.batch_downloader.download_video",
            ) as mock_dv,
            patch("vkdownloader.services.batch_downloader.setup_signal_handlers"),
            patch("vkdownloader.services.batch_downloader.cleanup_signal_handlers"),
            patch(
                "vkdownloader.utils.security.validate_output_path",
                return_value=tmp_path,
            ),
        ):
            mock_dv.return_value = tmp_path / "video.mp4"

            result = runner.invoke(
                app,
                [
                    "batch",
                    str(urls_file),
                    "--cookie-source",
                    "none",
                    "--ssl-verify",
                    "--max-retries",
                    "7",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        settings_arg = mock_dv.call_args.args[4]
        assert settings_arg.cookie_source == CookieSource.NONE
        assert settings_arg.ssl_verify is True
        assert settings_arg.max_retries == 7
        assert settings_arg.throttled_rate == 200000

    # ---- A3: bound enforced before the service ---------------------------

    def test_a3_max_retries_bound_enforced_download(
        self,
        tmp_path: Path,
        sample_video_url: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A3 (download): --max-retries 0 and 11 are rejected before the service runs."""
        monkeypatch.chdir(tmp_path)

        for invalid_value in [0, 11]:
            with patch(
                "vkdownloader.services.downloader.perform_download",
            ) as mock_download:
                result = runner.invoke(
                    app,
                    ["download", sample_video_url, "--max-retries", str(invalid_value)],
                )

            assert result.exit_code == 1, f"max_retries={invalid_value} should fail"
            assert "max_retries" in result.output
            assert "Traceback" not in result.output
            assert mock_download.call_count == 0

    def test_a3_max_retries_bound_enforced_batch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A3 (batch): --max-retries 0 and 11 are rejected before the service runs."""
        monkeypatch.chdir(tmp_path)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        for invalid_value in [0, 11]:
            with patch(
                "vkdownloader.services.batch_downloader.download_video",
            ) as mock_dv:
                result = runner.invoke(
                    app,
                    ["batch", str(urls_file), "--max-retries", str(invalid_value)],
                )

            assert result.exit_code == 1, f"max_retries={invalid_value} should fail"
            assert "max_retries" in result.output
            assert "Traceback" not in result.output
            assert mock_dv.call_count == 0

    # ---- A4: object identity across the preamble -------------------------

    def test_a4_settings_object_identity_download(
        self,
        tmp_path: Path,
        sample_video_url: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A4 (download): setup_logging and perform_download share one Settings object."""
        monkeypatch.chdir(tmp_path)
        mock_streams = [
            MagicMock(
                url="https://example.com/1080.m3u8",
                quality="1080",
                height=1080,
            ),
        ]

        with (
            patch("vkdownloader.cli.setup_logging") as mock_setup,
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.services.downloader.perform_download") as mock_download,
            patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path),
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=mock_streams),
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080"]
            mock_selector.select.return_value = MagicMock(quality="1080")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video.mp4"

            result = runner.invoke(
                app,
                ["download", sample_video_url, "--max-retries", "5"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        setup_settings = mock_setup.call_args[0][0]
        download_settings = mock_download.call_args.args[5]
        assert setup_settings is download_settings

    def test_a4_settings_object_identity_batch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A4 (batch): setup_logging and download_video share one Settings object."""
        monkeypatch.chdir(tmp_path)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        with (
            patch("vkdownloader.cli.setup_logging") as mock_setup,
            patch("vkdownloader.services.batch_downloader.RichProgressReporter"),
            patch(
                "vkdownloader.services.batch_downloader.download_video",
            ) as mock_dv,
            patch("vkdownloader.services.batch_downloader.setup_signal_handlers"),
            patch("vkdownloader.services.batch_downloader.cleanup_signal_handlers"),
            patch(
                "vkdownloader.utils.security.validate_output_path",
                return_value=tmp_path,
            ),
        ):
            mock_dv.return_value = tmp_path / "video.mp4"

            result = runner.invoke(
                app,
                ["batch", str(urls_file), "--max-retries", "5"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        setup_settings = mock_setup.call_args[0][0]
        download_settings = mock_dv.call_args.args[4]
        assert setup_settings is download_settings


class TestCommandPreamble:
    """VAL-105: tests for the shared _run_command_preamble helper."""

    def test_preamble_performs_all_four_steps(self, tmp_path: Path) -> None:
        """The preamble runs the env scan, builds Settings from .env, configures
        logging with that same object, and reports the resolved env file.

        The helper is called directly with a .env in tmp_path.  The four leaf
        collaborators are patched so the test asserts the wiring (component
        interaction) rather than implementation details.
        """
        (tmp_path / ".env").write_text("VKDOWNLOADER_MAX_RETRIES=5\n", encoding="utf-8")

        with (
            patch("vkdownloader.cli.warn_unknown_env_vars") as mock_warn,
            patch("vkdownloader.cli.setup_logging") as mock_setup,
            patch("vkdownloader.cli._log_env_file_path") as mock_log_env,
        ):
            settings = cli._run_command_preamble(
                cookie_source=None, ssl_verify=None, max_retries=None
            )

        mock_warn.assert_called_once()
        mock_log_env.assert_called_once()
        mock_setup.assert_called_once()
        assert mock_setup.call_args[0][0] is settings
        assert settings.max_retries == 5


class TestPreambleCalledOncePerCommand:
    """VAL-105: both commands delegate to _run_command_preamble exactly once."""

    def test_download_invokes_preamble_once(self, tmp_path: Path, sample_video_url: str) -> None:
        """download calls _run_command_preamble exactly once."""
        with (
            patch("vkdownloader.cli._run_command_preamble") as mock_preamble,
            patch("vkdownloader.cli.download_video", new_callable=AsyncMock) as mock_download,
        ):
            mock_preamble.return_value = MagicMock(log_file=None)
            mock_download.return_value = tmp_path / "video.mp4"

            result = runner.invoke(
                app,
                ["download", sample_video_url],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert mock_preamble.call_count == 1

    def test_batch_invokes_preamble_once(self, tmp_path: Path) -> None:
        """batch calls _run_command_preamble exactly once."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        with (
            patch("vkdownloader.cli._run_command_preamble") as mock_preamble,
            patch("vkdownloader.cli.run_batch", new_callable=AsyncMock) as mock_run_batch,
        ):
            mock_preamble.return_value = MagicMock(log_file=None)
            mock_run_batch.return_value = 0

            result = runner.invoke(
                app,
                ["batch", str(urls_file)],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert mock_preamble.call_count == 1
