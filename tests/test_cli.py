"""Tests for CLI commands using typer.testing.CliRunner."""

import asyncio
import locale
import logging
import re
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rich.console import Console
from typer.testing import CliRunner, Result

from vkdownloader import cli
from vkdownloader.cli import app
from vkdownloader.exceptions import (
    QualityNotAvailableError,
    VideoNotFoundError,
)
from vkdownloader.models.enums import TERMINAL_STATUSES, CookieSource, ProgressStatus
from vkdownloader.models.quality import QualitySpec
from vkdownloader.services import batch_downloader
from vkdownloader.services.downloader import download_video as _real_download_video
from vkdownloader.services.progress_display import RichProgressReporter

runner = CliRunner()

_REFERENCE_DOCS = Path(__file__).resolve().parent.parent / "docs" / "99-reference"
_REFERENCE_DOC_NAMES = ("cli-reference.md", "cli-reference-clean.md")
_COMMAND_HEADING = re.compile(r"^### \d+\. `([a-z]+)`")
_EXIT_CODE_ROW = re.compile(r"^\|\s*`(\d+)`\s*\|")
_EXIT_TABLE_DATA_ROW = re.compile(r"^\|\s*`")
_MAX_RETRIES_OPTION_ROW = re.compile(r"^\|\s*`--max-retries`\s*\|")
_BATCH_SUMMARY_STEP = re.compile(r"^\s*\d+\.\s+Prints summary of successful and failed downloads")


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


def _documented_exit_code_row_count(doc_path: Path) -> dict[str, int]:
    """Count the exit-code table data rows per command (including the unallocated row).

    Unlike :func:`_documented_exit_codes`, which only extracts single-numeric-code
    rows, this counts every data row in the exit-code table — ``_EXIT_TABLE_DATA_ROW``
    matches any row starting with ``| ` ``, catching the ``4-129, 131+`` unallocated
    line that ``_EXIT_CODE_ROW`` skips because it has no single code.
    """
    counts: dict[str, int] = {}
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
        if _EXIT_TABLE_DATA_ROW.match(line):
            assert command is not None, f"exit-code row outside a command section: {line}"
            counts[command] = counts.get(command, 0) + 1
        elif line.strip() and not line.startswith("|"):
            in_exit_table = False
    return counts


def _documented_max_retries_descriptions(doc_path: Path) -> dict[str, str]:
    """Extract the ``--max-retries`` option-table description per command.

    Returns a mapping of command name to the Description column of the
    ``--max-retries`` row in that command's Options table. A command whose
    option table omits the row is absent from the mapping, so the caller can
    detect a row missing from a single table.
    """
    descriptions: dict[str, str] = {}
    command: str | None = None
    in_options_table = False
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        heading = _COMMAND_HEADING.match(line)
        if heading is not None:
            command = heading.group(1)
            in_options_table = False
            continue
        if line.strip() == "**Options:**":
            in_options_table = True
            continue
        if not in_options_table:
            continue
        if _MAX_RETRIES_OPTION_ROW.match(line):
            assert command is not None, "option-table row outside a command section"
            descriptions[command] = line.split("|")[-2].strip()
        elif line.strip() and not line.startswith("|"):
            in_options_table = False
    return descriptions


def _documented_batch_summary_step(doc_path: Path) -> str:
    """Return the batch command's summary step line from a reference doc.

    Scans the batch command's ``**Behavior:**`` section (scoped via the
    ``### N. command`` heading so the single download command's behavior is
    ignored) and asserts the summary step appears exactly once. A missing or
    duplicated step is the divergence B8's doc edit is meant to keep dead;
    asserting uniqueness here turns it into a checked contract.
    """
    command: str | None = None
    in_batch = False
    matches: list[str] = []
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        heading = _COMMAND_HEADING.match(line)
        if heading is not None:
            command = heading.group(1)
            in_batch = False
            continue
        if command == "batch" and line.strip() == "**Behavior:**":
            in_batch = True
            continue
        if line.strip() == "**Progress Display:**":
            in_batch = False
            continue
        if in_batch and _BATCH_SUMMARY_STEP.match(line):
            matches.append(line.strip())
    assert len(matches) == 1, f"batch summary step not exactly once in {doc_path.name}: {matches!r}"
    return matches[0]


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
        assert "Total videos:" in result.output
        assert "Peak concurrent videos:" in result.output
        assert "Successful:" in result.output
        assert "Failed:" in result.output
        # TST-002: Assert error reasons appear in Failed URLs section
        assert "Failed URLs:" in result.output
        assert "video_not_found" in result.output
        assert "video-2_2" in result.output

    def test_batch_non_standard_height_reaches_the_service_layer(self, tmp_path: Path) -> None:
        """`batch --quality 1072` parses into the same request `download` builds.

        batch is a separate command with its own option declaration, so the
        open-ended quality contract has to hold on both paths.
        """
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with patch(
            "vkdownloader.cli.run_batch", new_callable=AsyncMock, return_value=0
        ) as mock_run_batch:
            result = runner.invoke(
                app,
                ["batch", str(urls_file), "--quality", "1072"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        requested = mock_run_batch.call_args.args[1]
        assert isinstance(requested, QualitySpec)
        assert requested.label == "1072p"
        assert str(requested) == "1072"

    def test_batch_invalid_quality_is_a_usage_error(self, tmp_path: Path) -> None:
        """`batch --quality nope` is rejected before the command body runs."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with patch("vkdownloader.cli.run_batch", new_callable=AsyncMock) as mock_run_batch:
            result = runner.invoke(
                app,
                ["batch", str(urls_file), "--quality", "nope"],
                catch_exceptions=False,
            )

        assert result.exit_code == 2
        mock_run_batch.assert_not_called()

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
        assert "Total videos: 2" in result.output

    def test_batch_summary_total_line_names_videos_and_counts_each_video(
        self, tmp_path: Path
    ) -> None:
        """B8 oracle: the summary's total line reports a video count, not a connection count.

        The label must name the unit it reports -- a video count -- and the value
        must equal the number of videos in the batch. A regression that moves the
        count under a connection-flavoured word, or lets the value drift from the
        video count, fails this test rather than only pinning a literal string.
        """
        url_count = 3
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "".join(f"https://vkvideo.ru/video-{i}_{i}\n" for i in range(1, url_count + 1))
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
        # The label must name the unit it reports: a video count.
        assert "Total videos:" in result.output
        total_line = next(
            line for line in result.output.splitlines() if line.strip().startswith("Total ")
        )
        # Regression guard: a connection-flavoured label fails this assertion.
        assert "video" in total_line.lower(), total_line
        assert "connection" not in total_line.lower(), total_line
        # The value must equal the number of videos in the batch.
        assert int(total_line.split(":")[-1].strip()) == url_count, total_line

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
    """Tests for --quality validation in CLI."""

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
        # The requested value is rendered verbatim: it is already a bare height,
        # so appending "p" would be wrong (and used to print "bestp" for keywords).
        assert "Requested quality '1440' is not available" in result.output
        assert "'1440p'" not in result.output
        assert "Available qualities:" in result.output

    def test_invalid_quality_option(self, tmp_path: Path) -> None:
        """Check quality validation rejects invalid values as a usage error."""
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890", "--quality", "invalid_quality"],
            catch_exceptions=False,
        )

        assert result.exit_code == 2

    def test_non_standard_height_is_accepted(self, tmp_path: Path, sample_video_url: str) -> None:
        """A height outside any fixed ladder (1072) reaches the service layer.

        VK ladders are non-standard (106p … 1072p … 1610p); before the open-ended
        quality model the argument parser rejected such a value outright.
        """
        with patch(
            "vkdownloader.cli.download_video",
            new_callable=AsyncMock,
            return_value=tmp_path / "video_1072.mp4",
        ) as mock_download_video:
            result = runner.invoke(
                app,
                ["download", sample_video_url, "--quality", "1072"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        requested = mock_download_video.call_args.args[1]
        assert isinstance(requested, QualitySpec)
        assert requested.label == "1072p"
        assert str(requested) == "1072"

    def test_non_standard_height_missing_from_video_is_reported(self, tmp_path: Path) -> None:
        """An unavailable height is reported with the ladder the video offers."""
        streams = [
            MagicMock(url="https://example.com/1072p.m3u8", quality="1072p", height=1072),
            MagicMock(url="https://example.com/804p.m3u8", quality="804p", height=804),
        ]

        with (
            patch("vkdownloader.services.downloader.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.services.downloader.perform_download"),
            patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path),
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="12345_67890", streams=streams)
            )
            mock_extractor_cls.return_value = mock_extractor

            result = runner.invoke(
                app,
                ["download", "https://vkvideo.ru/video-12345_67890", "--quality", "1000"],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert "Requested quality '1000' is not available" in result.output
        assert "1072p" in result.output

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


class TestMethodFfmpegRemoved:
    """Tests that --method ffmpeg is no longer accepted after the download transport was removed."""

    def test_download_method_ffmpeg_rejected(self, tmp_path: Path) -> None:
        """Check that --method ffmpeg is rejected with a usage error."""
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890", "--method", "ffmpeg"],
            catch_exceptions=False,
        )

        assert result.exit_code == 2

    def test_batch_method_ffmpeg_rejected(self, tmp_path: Path) -> None:
        """Check that --method ffmpeg is rejected for batch command."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n")

        result = runner.invoke(
            app,
            ["batch", str(urls_file), "--method", "ffmpeg"],
            catch_exceptions=False,
        )

        assert result.exit_code == 2

    def test_method_help_text_excludes_ffmpeg(self) -> None:
        """Verify ffmpeg is not listed in the --method help text."""
        result = runner.invoke(app, ["download", "--help"])

        assert result.exit_code == 0
        assert "ffmpeg" not in result.output.lower()

    def test_method_option_still_present_in_download_help(self) -> None:
        """``--method`` still appears in ``download --help`` with both valid values.

        Distinguishes “value rejected by the parser” from “flag removed
        outright”: if ``--method`` were deleted entirely the option would not
        appear in ``--help`` (exit code would be 2, not 0).  The two valid
        values are asserted individually so the test pins the list, not just
        the flag’s existence.
        """
        result = runner.invoke(app, ["download", "--help"])

        assert result.exit_code == 0
        assert "--method" in result.output
        assert "yt-dlp" in result.output
        assert "auto" in result.output

    def test_method_option_still_present_in_batch_help(self) -> None:
        """``--method`` still appears in ``batch --help`` with both valid values.

        Mirrors the download counterpart so the two commands’ identical
        ``--method`` help text is pinned in *both*, as required.
        """
        result = runner.invoke(app, ["batch", "--help"])

        assert result.exit_code == 0
        assert "--method" in result.output
        assert "yt-dlp" in result.output
        assert "auto" in result.output

    def test_download_ffmpeg_rejection_carries_migration_note(self) -> None:
        """The ``--method ffmpeg`` rejection carries a migration note, not a bare error.

        Unlike ``test_download_method_ffmpeg_rejected`` — which asserts only
        ``exit_code == 2`` and would pass even if the flag were deleted
        outright — this asserts the substantive substring ``was removed``.
        That substring distinguishes a deliberate removal explanation from a
        bare invalid-choice error and pins the note’s presence against its
        absence.  The substring is not the bare token ``ffmpeg`` (whose
        absence from ``--help`` is already pinned by
        ``test_method_help_text_excludes_ffmpeg``).
        """
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890", "--method", "ffmpeg"],
            catch_exceptions=False,
        )

        assert result.exit_code == 2
        assert "was removed" in result.output.lower()

    def test_batch_ffmpeg_rejection_carries_migration_note(self, tmp_path: Path) -> None:
        """The ``--method ffmpeg`` rejection for batch carries a migration note.

        Same honest witness as the download counterpart: asserts the
        substantive substring ``was removed`` appears in the rejection
        output, distinguishing a deliberate removal explanation from a bare
        invalid-choice error.
        """
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n")

        result = runner.invoke(
            app,
            ["batch", str(urls_file), "--method", "ffmpeg"],
            catch_exceptions=False,
        )

        assert result.exit_code == 2
        assert "was removed" in result.output.lower()


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

        assert result.exit_code == 3
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

    def test_batch_os_error_after_read_not_misreported_as_url_file_error(
        self, tmp_path: Path
    ) -> None:
        """A post-read OSError must not be misreported as a URL file read failure.

        After the URL file is read successfully, an OSError from the batch
        run itself falls through to the generic catch-all — it does not
        produce the "Failed to read URL file" message.
        """
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        with (
            patch("vkdownloader.cli._run_command_preamble") as mock_preamble,
            patch("vkdownloader.cli.run_batch", new_callable=AsyncMock) as mock_run_batch,
        ):
            mock_preamble.return_value = MagicMock(log_file=None)
            mock_run_batch.side_effect = OSError("No space left on device")

            result = runner.invoke(
                app,
                ["batch", str(urls_file)],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert "Failed to read URL file" not in result.output
        assert "An error occurred during batch download" in result.output


class TestQualityRecoveryHint:
    """D-05 part 1: the recovery hint must name only values the parser accepts."""

    _QUOTED_TOKEN_RE = re.compile(r"'([^']+)'")
    _EXAMPLE_RE = re.compile(r"e\.g\.\s*([^)]+)\)")

    def _named_tokens(self, message: str) -> list[str]:
        """Extract every value the rejection message names as acceptable.

        Both spellings are collected: quoted keywords ('best', 'worst',
        'unknown') and the example heights in the trailing "(e.g. …)" clause.
        The option name that Click prints in the prefix is not a value, so the
        search starts after the colon that follows it.
        """
        _, separator, body = message.partition("Invalid value for '--quality':")
        assert separator, "the rejection message carries no recognizable prefix"
        tokens = set(self._QUOTED_TOKEN_RE.findall(body))
        for group in self._EXAMPLE_RE.findall(body):
            tokens.update(part.strip() for part in group.split(","))
        return sorted(token for token in tokens if token and not token.startswith("-"))

    def test_quality_recovery_hint_names_only_accepted_values(
        self, tmp_path: Path, sample_video_url: str
    ) -> None:
        """Every value the rejection message prints must be accepted when pasted back.

        The hint is emitted by the ``--quality`` callback, which runs during
        argument parsing, so it is observable by invoking the CLI with a rejected
        token and reading the parser's own message.
        """
        rejected = runner.invoke(
            app,
            ["download", sample_video_url, "--quality", "bogus"],
            catch_exceptions=False,
        )

        assert rejected.exit_code == 2
        assert "Invalid value for '--quality'" in rejected.output

        tokens = self._named_tokens(rejected.output)
        assert tokens, "the recovery hint named no values"

        for token in tokens:
            with patch(
                "vkdownloader.cli.download_video",
                new_callable=AsyncMock,
                return_value=tmp_path / "video.mp4",
            ):
                result = runner.invoke(
                    app,
                    ["download", sample_video_url, "--quality", token],
                    catch_exceptions=False,
                )

            assert "Invalid value for '--quality'" not in result.output, (
                f"recovery hint names '{token}', which the parser rejects"
            )
            assert result.exit_code == 0
            assert QualitySpec.parse(token)


class TestExitCodeContract:
    """D-05 part 2: the documented exit codes must match the values actually emitted."""

    def test_every_observable_exit_code_is_documented(
        self, tmp_path: Path, sample_video_url: str
    ) -> None:
        """Every exit code the process can emit must be documented for both commands.

        The five values are observed by invoking the CLI, not assumed:

        * ``0``   — ``download`` with the download service mocked to succeed.
        * ``1``   — ``download`` with a URL that is not a VK video URL, which the
          command maps to its own "Invalid URL format" handler.
        * ``2``   — ``download --quality not-a-quality``: a value the argument
          parser rejects, so the command body never runs. The same value is
          produced by a missing argument, an unknown command and an unknown
          option. (``720p`` no longer belongs here: it is a valid height.)
        * ``3``   — ``download --max-retries 0``: an out-of-range value the
          ``Settings`` model rejects, so the command body never runs and the
          preamble's ``ValidationError`` handler exits 3 (configuration error).
        * ``130`` — ``download`` interrupted with ``KeyboardInterrupt`` from the
          extraction layer, which the command maps to its cancellation handler.
        """
        observed = self._observe_exit_codes(tmp_path, sample_video_url)

        assert set(observed) == {0, 1, 2, 3, 130}, observed

        for doc_name in _REFERENCE_DOC_NAMES:
            documented = _documented_exit_codes(_REFERENCE_DOCS / doc_name)
            assert documented.get("download") == {0, 1, 2, 3, 130}, doc_name
            assert documented.get("batch") == {0, 1, 2, 3, 130}, doc_name

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
            ["download", sample_video_url, "--quality", "not-a-quality"],
            catch_exceptions=False,
        )
        observed.setdefault(result.exit_code, "parser rejected the --quality value 'not-a-quality'")

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

        # Observe code 3 outside the Settings mock: the real model rejects the
        # out-of-range value and raises ValidationError, which download maps to 3.
        result = runner.invoke(
            app,
            ["download", sample_video_url, "--max-retries", "0"],
            catch_exceptions=False,
        )
        observed.setdefault(
            result.exit_code,
            "download with out-of-range --max-retries exits 3 (configuration error)",
        )

        return observed

    def test_repeated_interrupt_escalates_to_exit_130(self, tmp_path: Path) -> None:
        """B5: a second Ctrl-C escalates to a cancellation that exits 130.

        Without the escalator, a second interrupt is a silent no-op: the batch
        completes, prints its summary, and exits 1.  With it, the displaced
        ``Runner._on_sigint`` cancels the main task, ``_print_batch_summary`` is
        never reached, and ``cli.py``'s cancellation arm raises ``Exit(130)``.

        Patches **only** ``vkdownloader.services.batch_downloader.download_video``
        so the real CLI preamble, signal handler installation, and ``asyncio.run``
        Runner lifecycle all run end-to-end.
        """
        import signal as signal_module

        from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n")

        # Token idiom: supply a fresh, unset Event so the handler inside
        # asyncio.run copies the ContextVar and writes to one we control.
        token = _shutdown_event_ctx.set(asyncio.Event())

        def _fire_sigint() -> None:
            """Resolve and fire the SIGINT dispatch installed by setup_signal_handlers."""
            loop = asyncio.get_running_loop()
            loop_handlers = getattr(loop, "_signal_handlers", {})
            if signal_module.SIGINT in loop_handlers:
                # Loop path: callback takes no arguments.
                loop_handlers[signal_module.SIGINT]()
                return
            handler = signal_module.getsignal(signal_module.SIGINT)
            if (
                handler is signal_module.SIG_DFL
                or handler is signal_module.SIG_IGN
                or not callable(handler)
            ):
                pytest.fail(
                    "could not resolve SIGINT dispatch: neither the loop handler "
                    "table nor signal.getsignal returns a callable handler"
                )
            handler(signal_module.SIGINT, None)

        async def _stalls(url: str, *args: object, **kwargs: object) -> Path | None:
            # First fire: request a stop.
            _fire_sigint()
            try:
                await asyncio.wait_for(asyncio.sleep(0), timeout=5.0)
            except TimeoutError:
                pytest.fail("first SIGINT did not yield control within 5.0s")

            # Second fire: the escalation — forwards to Runner._on_sigint which
            # cancels main_task; if the escalation is a no-op, we fall through.
            _fire_sigint()
            try:
                await asyncio.wait_for(asyncio.sleep(1.0), timeout=1.5)
            except TimeoutError:
                pytest.fail("second SIGINT did not escalate within 1.5s")
            raise TimeoutError("the second interrupt did not escalate")

        try:
            with patch(
                "vkdownloader.services.batch_downloader.download_video",
                side_effect=_stalls,
            ):
                result = runner.invoke(
                    app,
                    ["batch", str(urls_file)],
                    catch_exceptions=False,
                )
        finally:
            _shutdown_event_ctx.reset(token)

        assert result.exit_code == 130, result.output
        assert "Download Summary:" not in result.output

    def test_exit_code_table_has_six_rows_including_130(self) -> None:
        """Both reference docs must carry exactly six exit-code rows per command.

        The six-row contract (DEC-X) is: 0, 1, 2, 3, 130, and the unallocated
        ``4-129, 131+`` row.  Membership is checked separately by
        ``test_every_observable_exit_code_is_documented``; this oracle checks the
        *shape* — the row count — so a future edit that drops the unallocated
        row or merges two rows cannot pass silently.
        """
        for doc_name in _REFERENCE_DOC_NAMES:
            doc_path = _REFERENCE_DOCS / doc_name
            row_counts = _documented_exit_code_row_count(doc_path)
            documented = _documented_exit_codes(doc_path)
            for command in ("download", "batch"):
                assert row_counts.get(command, 0) == 6, (
                    f"{doc_name}: {command} exit-code table has "
                    f"{row_counts.get(command, 0)} rows, expected 6"
                )
                assert 130 in documented.get(command, set()), (
                    f"{doc_name}: {command} exit-code table is missing 130"
                )

    def test_exit_code_3_distinct_from_1(
        self,
        tmp_path: Path,
        sample_video_url: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Exit 3 (configuration error) is distinct from exit 1 (download failure).

        A download that runs and fails — ``perform_download`` returns ``None`` —
        exits 1.  An out-of-range ``--max-retries`` that the ``Settings`` model
        rejects exits 3.  Without this test, a future change that collapses 3
        back into 1 would pass the membership oracle alone.
        """
        monkeypatch.chdir(tmp_path)

        # Case 1: a legitimate download failure exits 1.
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

            mock_download.return_value = None  # download runs but fails

            with patch("vkdownloader.utils.security.validate_output_path", return_value=tmp_path):
                with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                    mock_settings_cls.return_value = MagicMock(log_file=None)
                    result_fail = runner.invoke(
                        app,
                        ["download", sample_video_url],
                        catch_exceptions=False,
                    )

        assert result_fail.exit_code == 1, "a download failure must exit 1, not 3"

        # Case 2: a settings rejection exits 3 (configuration error).
        result_config = runner.invoke(
            app,
            ["download", sample_video_url, "--max-retries", "0"],
            catch_exceptions=False,
        )
        assert result_config.exit_code == 3, (
            "an out-of-range --max-retries must exit 3 (configuration error), not 1"
        )


class TestMaxRetriesOptionDocumentation:
    """B5 (doc half of OUT-005): the ``--max-retries`` option-table row must exist
    for every command and state the range that ``Settings.max_retries`` enforces.

    The option deliberately carries no ``min``/``max`` (prohibited by R3b), so the
    reference row is the only place the bound is stated. This oracle derives floor
    and ceiling from the model field's metadata, never from a literal, so the prose
    can only drift as far as the test is rewritten.
    """

    @staticmethod
    def _documented_retry_range() -> str:
        """Build the expected ``floor-ceiling`` string from the model field.

        Mirrors ``TestConditionalOverridesConstruction`` in ``test_config.py``:
        floor/ceiling are read from the ``Ge``/``Le`` metadata on
        ``Settings.model_fields["max_retries"]`` so the test cannot drift from
        the field that enforces the bound.
        """
        from annotated_types import Ge, Le

        from vkdownloader.config import Settings

        field = Settings.model_fields["max_retries"]
        floor = next(m.ge for m in field.metadata if isinstance(m, Ge))
        ceiling = next(m.le for m in field.metadata if isinstance(m, Le))
        return f"{floor}-{ceiling}"

    def test_max_retries_row_exists_and_states_model_range(self) -> None:
        documented_range = self._documented_retry_range()

        for doc_name in _REFERENCE_DOC_NAMES:
            descriptions = _documented_max_retries_descriptions(_REFERENCE_DOCS / doc_name)

            # Per command: a row absent from either table must fail this test.
            assert set(descriptions) == {"download", "batch"}, (
                f"{doc_name}: --max-retries row missing from at least one command "
                f"(present for: {set(descriptions)})"
            )

            for command, description in descriptions.items():
                assert documented_range in description, (
                    f"{doc_name}: `{command}` --max-retries row does not state the "
                    f"model range {documented_range!r}: {description!r}"
                )


class TestBatchSummaryDocumentation:
    """B8 oracle: both reference docs describe the batch summary step with
    identical wording and both mention the skipped-invalid-URL count.

    B8 reconciled a divergence where ``cli-reference.md`` numbered the step 7 and
    mentioned the skipped count while ``cli-reference-clean.md`` numbered it 6 and
    omitted the clause; this oracle keeps that reconciliation a checked contract
    rather than a one-off prose edit.
    """

    def test_batch_summary_step_is_consistent_and_mentions_skipped_urls(self) -> None:
        steps = {
            doc_name: _documented_batch_summary_step(_REFERENCE_DOCS / doc_name)
            for doc_name in _REFERENCE_DOC_NAMES
        }

        # Reconciled wording: the step text must be identical across both files,
        # so the item number and the clause cannot drift apart again.
        assert steps["cli-reference.md"] == steps["cli-reference-clean.md"], steps

        # Both must mention the skipped-invalid-URL count, because that is what
        # _print_batch_summary prints ("Skipped (invalid URLs): {skipped_count}").
        for doc_name, step in steps.items():
            assert "invalid URL" in step, (doc_name, step)

    def test_docs_marker_line_states_skipped_reachable(self) -> None:
        """B9: the marker line in both docs states [⊘] for skipped is reachable.

        Before B9, the docs advertised a skipped marker that no code path could
        produce. After the fix, SKIPPED is reachable via the dedup path, and the
        docs state that explicitly. Both files must say the same thing.
        """
        for doc_name in _REFERENCE_DOC_NAMES:
            content = (_REFERENCE_DOCS / doc_name).read_text(encoding="utf-8")
            assert "skipped" in content.lower(), doc_name
            assert "reachable" in content.lower(), (
                f"{doc_name}: marker line must state reachability"
            )
            # IN_PROGRESS is non-terminal: it emits no glyph, so it must
            # not appear in the docs.
            assert "in_progress" not in content.lower(), doc_name

    def test_docs_marker_set_matches_terminal_statuses(self) -> None:
        """B9: the glyphs documented in both reference files match the terminal
        ProgressStatus members the code can emit.

        Fails if a glyph is documented but not emitted, if an emitted glyph is
        missing from the docs, or if IN_PROGRESS (a non-terminal status) leaks
        into the documented terminal glyph set.
        """
        # IN_PROGRESS is the non-terminal producer state: it is present in
        # the enum but excluded from TERMINAL_STATUSES.
        assert hasattr(ProgressStatus, "IN_PROGRESS")
        assert ProgressStatus.IN_PROGRESS not in TERMINAL_STATUSES

        # Glyphs are derived from the terminal ProgressStatus members, mirroring
        # _StatusColumn.render. SKIPPED and CANCELLED share ⊘. Every terminal
        # status must carry a glyph — a new terminal status without a documented
        # glyph fails the coverage assertion below rather than silent drift.
        terminal_glyphs: dict[ProgressStatus, str] = {
            ProgressStatus.SUCCESS: "✓",
            ProgressStatus.FAILED: "✗",
            ProgressStatus.SKIPPED: "⊘",
            ProgressStatus.CANCELLED: "⊘",
        }
        assert set(terminal_glyphs) == set(TERMINAL_STATUSES)
        emittable_glyphs = set(terminal_glyphs.values())

        for doc_name in _REFERENCE_DOC_NAMES:
            content = (_REFERENCE_DOCS / doc_name).read_text(encoding="utf-8")
            for glyph in emittable_glyphs:
                assert glyph in content, (
                    f"{doc_name}: documented marker {glyph!r} is not emitted by code"
                )


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

            assert result.exit_code == 3, f"max_retries={invalid_value} should fail"
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

            assert result.exit_code == 3, f"max_retries={invalid_value} should fail"
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


class TestPreSinkDiagnostic:
    """Pre-sink diagnostics: env-var warnings, download_dir coercion, and the
    environment-file resolution report.

    Verifies that the bootstrap warning for unknown VKDOWNLOADER_* variables
    is rendered to stderr exactly once per command (not doubled by structured
    logging); that empty-string download_dir coercion no longer emits a debug
    record; and that the resolved environment file is reported at INFO (CFG-008),
    with distinct event names for the found and not-found branches.
    """

    _UNKNOWN_VAR = "VKDOWNLOADER_UNKNOWN_FOO"

    def test_unknown_variable_rendered_once_on_stderr(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unrecognised VKDOWNLOADER_* var is echoed to stderr exactly once per command."""
        monkeypatch.setenv(self._UNKNOWN_VAR, "bogus")

        # --- download command ---
        result = runner.invoke(
            app,
            ["download", "https://example.com/invalid"],
            catch_exceptions=False,
        )

        assert result.stderr.count(self._UNKNOWN_VAR) == 1
        assert "unknown_env_var_ignored" not in result.stdout
        assert "unknown_env_var_ignored" not in result.stderr

        # --- batch command ---
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("", encoding="utf-8")

        result = runner.invoke(
            app,
            ["batch", str(urls_file)],
            catch_exceptions=False,
        )

        assert result.stderr.count(self._UNKNOWN_VAR) == 1
        assert "unknown_env_var_ignored" not in result.stdout
        assert "unknown_env_var_ignored" not in result.stderr

    def test_no_unknown_variable_warning_when_none_present(self, tmp_path: Path) -> None:
        """Without any unknown vars, the warning text is absent from stderr."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("", encoding="utf-8")

        result = runner.invoke(
            app,
            ["batch", str(urls_file)],
            catch_exceptions=False,
        )

        assert "Ignored unknown environment variable" not in result.stderr

    def test_download_dir_debug_record_is_not_emitted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty-string download_dir is silently coerced; no debug record is emitted."""
        log_path = tmp_path / "test.log"
        monkeypatch.setenv("VKDOWNLOADER_DOWNLOAD_DIR", "")
        monkeypatch.setenv("VKDOWNLOADER_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("VKDOWNLOADER_LOG_FILE", str(log_path))

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("", encoding="utf-8")

        result = runner.invoke(
            app,
            ["batch", str(urls_file)],
            catch_exceptions=False,
        )

        assert "download_dir_empty_string_using_default" not in result.stdout
        log_contents = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        assert "download_dir_empty_string_using_default" not in log_contents

    # ---- CFG-008: the env-file resolution report is emitted at INFO --------

    @staticmethod
    def _make_env_file(path: Path) -> Path:
        """Write a minimal legal .env and return its resolved absolute path."""
        path.write_text("VKDOWNLOADER_MAX_RETRIES=5\n", encoding="utf-8")
        return path.resolve()

    def test_env_file_resolved_info_at_default_level(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A .env present in the working directory is reported at INFO.

        Before CFG-008 the found-branch record was at DEBUG and invisible at
        the default INFO level.  One INFO record naming the resolved path is
        emitted per invocation.
        """
        self._make_env_file(tmp_path / ".env")
        monkeypatch.chdir(tmp_path)

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("", encoding="utf-8")

        with caplog.at_level(logging.INFO):
            result = runner.invoke(app, ["batch", str(urls_file)], catch_exceptions=False)

        assert result.exit_code == 1
        resolved = [r for r in caplog.records if "env_file_resolved" in r.getMessage()]
        assert len(resolved) == 1
        # Assert on the structured record, not the rendered string: the
        # rendered form is renderer-dependent (JSONRenderer escapes
        # backslashes), but the level is not.  The path content itself is
        # verified by test_log_env_file_path_calls_info_not_debug.
        assert resolved[0].levelno == logging.INFO
        # The not-found branch must NOT fire when a file is present.
        assert not any(
            "env_file_not_found_using_environment_or_defaults" in r.getMessage()
            for r in caplog.records
        )

    def test_env_file_not_found_info_at_default_level(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No .env in the working directory is reported at INFO.

        The not-found branch carries a distinct event name so the two runs
        are distinguishable at the default level.
        """
        monkeypatch.chdir(tmp_path)
        assert not (tmp_path / ".env").exists()

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("", encoding="utf-8")

        with caplog.at_level(logging.INFO):
            result = runner.invoke(app, ["batch", str(urls_file)], catch_exceptions=False)

        assert result.exit_code == 1
        not_found = [
            r
            for r in caplog.records
            if "env_file_not_found_using_environment_or_defaults" in r.getMessage()
        ]
        assert len(not_found) == 1
        # The found branch must NOT fire when no file is present.
        assert not any("env_file_resolved" in r.getMessage() for r in caplog.records)

    def test_env_file_report_still_visible_at_debug_level(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """The resolution report is still emitted as INFO when the log level is DEBUG.

        At DEBUG verbosity the report must not be downgraded — it stays at
        INFO so it is visible at the default level.  Captures at DEBUG
        threshold so any DEBUG-level regression would surface, and asserts
        the record's level is INFO and that it is the only environment-file
        record emitted.
        """
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VKDOWNLOADER_LOG_LEVEL", "DEBUG")

        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("", encoding="utf-8")

        with caplog.at_level(logging.DEBUG):
            result = runner.invoke(app, ["batch", str(urls_file)], catch_exceptions=False)

        assert result.exit_code == 1
        env_file_records = [r for r in caplog.records if "env_file" in r.getMessage()]
        assert len(env_file_records) == 1
        assert env_file_records[0].levelno == logging.INFO

    def test_log_env_file_path_calls_info_not_debug(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Direct: _log_env_file_path uses logger.info, never logger.debug.

        Guards against a regression to DEBUG that would hide the report at the
        default log level.
        """
        monkeypatch.chdir(tmp_path)
        resolved_path = self._make_env_file(tmp_path / ".env")

        with patch("vkdownloader.cli.logger") as mock_logger:
            cli._log_env_file_path()

        mock_logger.info.assert_called_once()
        mock_logger.info.assert_called_once_with("env_file_resolved", path=str(resolved_path))
        mock_logger.debug.assert_not_called()


class TestPreambleFailureRendering:
    """ENT-002, ENT-003: preamble/bootstrap failure is rendered via a shared path.

    Both commands must reach ``_render_preamble_failure`` and emit the same
    single-line message on stderr — never a traceback, never an absolute
    source path, and never the Settings object.
    """

    @staticmethod
    def _force_logging_failure(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Point VKDOWNLOADER_LOG_FILE inside a regular file so mkdir fails."""
        blocker = tmp_path / "blocker"
        blocker.write_text("")
        monkeypatch.setenv("VKDOWNLOADER_LOG_FILE", str(blocker / "app.log"))

    @staticmethod
    def _project_root() -> str:
        """Return the repository root path to detect leaked source paths."""
        return str(Path(__file__).resolve().parent.parent)

    def _assert_clean_preamble_failure_output(self, result: Result) -> None:
        """Assert exit 3, single-line stderr message, no traceback/path/settings."""
        assert result.exit_code == 3
        stderr = result.stderr
        assert "Logging configuration failed" in stderr
        # Single line — only the trailing newline from typer.echo.
        assert stderr.count("\n") == 1
        combined = result.output
        assert "Traceback" not in result.stdout
        assert "Traceback" not in combined
        assert self._project_root() not in combined
        assert "Settings(" not in combined

    def test_download_preamble_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """download: setup_logging OSError renders the shared stderr message."""
        self._force_logging_failure(tmp_path, monkeypatch)
        result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890"],
            catch_exceptions=False,
        )
        self._assert_clean_preamble_failure_output(result)

    def test_batch_preamble_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """batch: setup_logging OSError renders the shared stderr message."""
        self._force_logging_failure(tmp_path, monkeypatch)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")
        result = runner.invoke(
            app,
            ["batch", str(urls_file)],
            catch_exceptions=False,
        )
        self._assert_clean_preamble_failure_output(result)
        # A logging-setup failure must not be misreported as a URL-file error.
        assert "Failed to read URL file" not in result.output

    def test_download_and_batch_preamble_failure_render_same_message(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Both commands emit the identical preamble-failure message on stderr."""
        self._force_logging_failure(tmp_path, monkeypatch)
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-12345_67890\n", encoding="utf-8")

        download_result = runner.invoke(
            app,
            ["download", "https://vkvideo.ru/video-12345_67890"],
            catch_exceptions=False,
        )
        batch_result = runner.invoke(
            app,
            ["batch", str(urls_file)],
            catch_exceptions=False,
        )
        assert download_result.exit_code == 3
        assert batch_result.exit_code == 3
        assert download_result.stderr == batch_result.stderr
