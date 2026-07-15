"""Tests for security utilities - path validation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vkdownloader.exceptions import DownloadError
from vkdownloader.utils.security import validate_output_path


class TestValidateOutputPath:
    """Tests for validate_output_path security function."""

    def test_valid_path_returns_resolved_path(self, tmp_path: Path) -> None:
        """Test that a valid path returns resolved Path."""
        path = tmp_path / "output" / "video.mp4"
        result = validate_output_path(path)

        assert result == path.resolve()
        assert ".." not in str(result)

    def test_path_traversal_rejected(self, tmp_path: Path) -> None:
        """Test that path traversal with '..' raises DownloadError."""
        path = tmp_path / ".." / "etc" / "passwd"

        with pytest.raises(DownloadError, match="Path traversal detected"):
            validate_output_path(path)

    def test_path_traversal_in_middle_rejected(self, tmp_path: Path) -> None:
        """Test that path traversal in middle of path raises DownloadError."""
        path = tmp_path / "output" / ".." / ".." / "etc"

        with pytest.raises(DownloadError, match="Path traversal detected"):
            validate_output_path(path)

    def test_path_traversal_at_start_rejected(self) -> None:
        """Test that path traversal at start raises DownloadError."""
        path = Path("../outside_repo")

        with pytest.raises(DownloadError, match="Path traversal detected"):
            validate_output_path(path)

    def test_valid_path_creates_no_warning(self, tmp_path: Path) -> None:
        """Test that valid path outside repo does not warn."""
        path = tmp_path / "output" / "video.mp4"

        with patch("vkdownloader.utils.security.logger") as mock_logger:
            result = validate_output_path(path)

            # Should not warn for paths outside repo
            mock_logger.warning.assert_not_called()
            assert result == path.resolve()

    def test_path_inside_repo_warns(self, tmp_path: Path) -> None:
        """Test that path inside repository root triggers warning."""
        test_path = tmp_path / "output" / "video.mp4"

        with patch("vkdownloader.utils.security.logger") as mock_logger:
            # Mock relative_to to succeed (meaning path is inside repo)
            resolved_mock = MagicMock()
            resolved_mock.relative_to.return_value = tmp_path  # Succeeds for paths inside repo

            with patch.object(
                Path,
                "resolve",
                return_value=resolved_mock,
            ):
                validate_output_path(test_path, warning=True)

                # Warning should be logged for path inside repo
                mock_logger.warning.assert_called_once()
                call_kwargs = mock_logger.warning.call_args[1]
                assert "path" in call_kwargs
                assert "repo_root" in call_kwargs


class TestValidateOutputPathEdgeCases:
    """Edge case tests for path validation."""

    def test_empty_path_rejected(self) -> None:
        """Test that empty path is handled safely."""
        path = Path(".")

        # Current directory should not raise, but let's verify it works
        with patch("vkdownloader.utils.security.logger"):
            result = validate_output_path(path)
            assert result == Path.cwd()

    def test_absolute_path_valid(self, tmp_path: Path) -> None:
        """Test that absolute paths are accepted."""
        path = tmp_path / "absolute" / "path.mp4"

        with patch("vkdownloader.utils.security.logger"):
            result = validate_output_path(path)
            assert result == path.resolve()

    def test_relative_path_valid(self, tmp_path: Path) -> None:
        """Test that relative paths without '..' are accepted."""
        path = Path("relative") / "path" / "video.mp4"

        with patch("vkdownloader.utils.security.logger"):
            result = validate_output_path(path)
            # Should resolve relative to current directory
            assert ".." not in str(result)
