"""Tests for CLI commands using typer.testing.CliRunner."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from vkdownloader.cli import app
from vkdownloader.exceptions import QualityNotAvailableError, VideoNotFoundError

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
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download") as mock_download,
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

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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

        with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
            with patch("vkdownloader.cli.Settings") as mock_settings_cls:
                mock_settings_cls.return_value = MagicMock(log_file=None)
                result = runner.invoke(
                    app,
                    ["download", invalid_url],
                    catch_exceptions=False,
                )

        assert result.exit_code == 1
        assert "Invalid URL format" in result.output or "Invalid VK video URL" in result.output

    def test_download_keyboard_interrupt(
        self, tmp_path: Path, sample_video_url: str, mock_m3u8_content: str
    ) -> None:
        """Check that KeyboardInterrupt is handled with proper exit code."""
        with (
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                side_effect=KeyboardInterrupt()
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.list_available_qualities.return_value = ["1080", "720"]
            mock_selector.select.return_value = MagicMock(quality="1080")
            mock_selector_cls.return_value = mock_selector

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(side_effect=mock_extract_side_effect)
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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

    def test_batch_all_success_exits_zero(self, tmp_path: Path) -> None:
        """Check that batch exits with code 0 when all downloads succeed."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("https://vkvideo.ru/video-1_1\n")

        with (
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download") as mock_download,
        ):
            mock_extractor = MagicMock()
            mock_extractor.extract_streams = AsyncMock(
                return_value=MagicMock(id="video1", streams=[])
            )
            mock_extractor_cls.return_value = mock_extractor

            mock_selector = MagicMock()
            mock_selector.select.return_value = MagicMock(quality="720")
            mock_selector_cls.return_value = mock_selector

            mock_download.return_value = tmp_path / "video1.mp4"

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download"),
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

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download") as mock_download,
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

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download") as mock_download,
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

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download") as mock_download,
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

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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
            patch("vkdownloader.cli.VKVideoExtractor") as mock_extractor_cls,
            patch("vkdownloader.cli.QualitySelector") as mock_selector_cls,
            patch("vkdownloader.cli.perform_download") as mock_download,
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

            with patch("vkdownloader.cli.validate_output_path", return_value=tmp_path):
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
