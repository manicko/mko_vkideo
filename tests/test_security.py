"""Tests for security utilities - path validation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vkdownloader.exceptions import DownloadError
from vkdownloader.utils.security import _sanitize_title, validate_output_path


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

    def test_empty_path_resolves_to_cwd(self) -> None:
        """Test that '.' (empty/current path) is accepted and resolves to cwd."""
        path = Path(".")

        # "." is a valid path with no traversal, so it is accepted and resolves to cwd
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


class TestSanitizeTitle:
    """Tests for _sanitize_title filesystem safety."""

    def test_strips_windows_illegal_characters(self) -> None:
        """Test that Windows-illegal characters are replaced with underscores."""
        raw = 'my:title/with*illegal?chars|and"quotes<>п'
        result = _sanitize_title(raw)

        for char in '/\\:*?"<>|':
            assert char not in result
        assert "_" in result
        assert result == "my_title_with_illegal_chars_and_quotes__п"

    def test_strips_leading_and_trailing_whitespace(self) -> None:
        """Test that surrounding whitespace is stripped."""
        result = _sanitize_title("   spaced title   ")
        assert result == "spaced title"

    def test_preserves_internal_whitespace(self) -> None:
        """Test that internal whitespace is preserved (only strip, not collapse)."""
        result = _sanitize_title("normal title")
        assert result == "normal title"

    def test_limits_length_to_100_characters(self) -> None:
        """Test that output is truncated to 100 characters."""
        result = _sanitize_title("a" * 150)
        assert len(result) == 100

    def test_returns_empty_string_for_blank_input(self) -> None:
        """Test that blank/whitespace-only input yields an empty string."""
        assert _sanitize_title("   ") == ""
        assert _sanitize_title("") == ""

    def test_combines_all_sanitizations(self) -> None:
        """Test illegal chars, whitespace strip, and length limit together."""
        raw = "  title:with|illegal*chars?and/long-suffix-" + "x" * 200
        result = _sanitize_title(raw)
        for char in '/\\:*?"<>|':
            assert char not in result
        assert not result.startswith(" ")
        assert not result.endswith(" ")
        assert len(result) == 100

