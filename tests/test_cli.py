"""Tests for CLI commands using typer.testing.CliRunner."""

import asyncio
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from rich.console import Console
from typer.testing import CliRunner

from vkdownloader.cli import app
from vkdownloader.exceptions import QualityNotAvailableError, VideoNotFoundError
from vkdownloader.models.enums import ProgressStatus
from vkdownloader.services import batch_downloader
from vkdownloader.services.downloader import download_video as _real_download_video
from vkdownloader.services.progress_display import RichProgressReporter

runner = CliRunner()


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
        assert "Peak concurrency:" in result.output
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
