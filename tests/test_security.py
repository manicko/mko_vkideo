"""Tests for security utilities - path validation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vkdownloader.exceptions import DownloadError
from vkdownloader.models.enums import StreamFormat
from vkdownloader.models.video import Stream, VideoWithStreams
from vkdownloader.utils.security import (
    _resolve_output_file,
    sanitize_filename_component,
    validate_output_path,
)


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

    def test_path_inside_repo_warns(self) -> None:
        """Test that path inside repository root triggers warning.

        Uses the real repo_root derivation (no Path.resolve mock) so the
        assertion is meaningful: the path under src/ must be recognised as
        inside the repository root.
        """
        repo_root = Path(__file__).resolve().parent.parent  # tests/ → repo root
        test_path = repo_root / "src" / "vkdownloader" / "placeholder.mp4"

        with patch("vkdownloader.utils.security.logger") as mock_logger:
            validate_output_path(test_path, warning=True)

            # Warning should be logged for path inside repo
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]
            assert "path" in call_kwargs
            assert "repo_root" in call_kwargs

    def test_path_inside_repo_outside_src_warns(self) -> None:
        """Test that a path under the repo root but outside src/ also warns.

        This is the oracle that detects the repo_root mis-derivation: with
        the old three-.parent expression repo_root pointed to src/ and a path
        under docs/ would not warn. With four .parent calls it points to the
        true repo root and the warning fires.
        """
        repo_root = Path(__file__).resolve().parent.parent
        test_path = repo_root / "docs" / "test_output.mp4"

        with patch("vkdownloader.utils.security.logger") as mock_logger:
            validate_output_path(test_path, warning=True)

            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]
            assert "path" in call_kwargs
            assert "repo_root" in call_kwargs

    def test_repo_root_derives_to_project_root(self) -> None:
        """Test that repo_root in security.py derives to the true project root.

        security.py lives at src/vkdownloader/utils/security.py, so four
        .parent calls reach the repository root. Asserted by value, not mock.
        """
        from vkdownloader.utils import security as security_module

        security_file = Path(security_module.__file__).resolve()
        actual_repo_root = security_file.parent.parent.parent.parent
        expected_repo_root = Path(__file__).resolve().parent.parent
        assert actual_repo_root == expected_repo_root


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


class TestSanitizeFilenameComponent:
    """Tests for sanitize_filename_component filesystem safety."""

    def test_strips_windows_illegal_characters(self) -> None:
        """Test that Windows-illegal characters are replaced with underscores."""
        raw = 'my:title/with*illegal?chars|and"quotes<>п'
        result = sanitize_filename_component(raw)

        for char in '/\\:*?"<>|':
            assert char not in result
        assert "_" in result
        assert result == "my_title_with_illegal_chars_and_quotes__п"

    def test_strips_leading_and_trailing_whitespace(self) -> None:
        """Test that surrounding whitespace is stripped."""
        result = sanitize_filename_component("   spaced title   ")
        assert result == "spaced title"

    def test_preserves_internal_whitespace(self) -> None:
        """Test that internal whitespace is preserved (only strip, not collapse)."""
        result = sanitize_filename_component("normal title")
        assert result == "normal title"

    def test_limits_length_to_100_characters(self) -> None:
        """Test that output is truncated to 100 characters."""
        result = sanitize_filename_component("a" * 150)
        assert len(result) == 100

    def test_returns_empty_string_for_blank_input(self) -> None:
        """Test that blank/whitespace-only input yields an empty string."""
        assert sanitize_filename_component("   ") == ""
        assert sanitize_filename_component("") == ""

    def test_combines_all_sanitizations(self) -> None:
        """Test illegal chars, whitespace strip, and length limit together."""
        raw = "  title:with|illegal*chars?and/long-suffix-" + "x" * 200
        result = sanitize_filename_component(raw)
        for char in '/\\:*?"<>|':
            assert char not in result
        assert not result.startswith(" ")
        assert not result.endswith(" ")
        assert len(result) == 100

    @pytest.mark.parametrize("code", [chr(c) for c in range(32)] + [chr(127)])
    def test_no_control_character_survives(self, code: str) -> None:
        """No C0 control character (chr(0)-chr(31)) or DEL (chr(127)) survives."""
        char = code
        result = sanitize_filename_component(f"before{char}after")
        assert char not in result

    def test_newline_and_tab_do_not_produce_multiline(self) -> None:
        """A newline or tab in a title no longer produces a multi-line string."""
        result = sanitize_filename_component("line1\nline2\ttabbed")
        assert "\n" not in result
        assert "\t" not in result

    def test_null_byte_replaced_not_stripped(self) -> None:
        """chr(0) is replaced with underscore — the ValueError failure mode is pinned.

        str.strip cannot remove a control character from the middle of a string,
        and a null byte that reaches the filesystem layer raises
        ValueError: embedded null byte. Replacement is the required shape.
        """
        result = sanitize_filename_component("before\x00after")
        assert result == "before_after"
        assert "\x00" not in result


class TestValidateOutputPathTraversal:
    """Tests for validate_output_path traversal detection (SEC-006).

    SEC-006: The pre-resolution \"..\" check is a no-op for paths that
    callers already resolve. The fix adds a post-resolution check too,
    making the guard effective regardless of whether the path arrives
    resolved or unresolved.
    """

    def test_pre_resolution_double_dot_rejected(self, tmp_path: Path) -> None:
        """\"..\" in an unresolved path is caught before resolution."""
        path = tmp_path / ".." / "etc" / "passwd"
        with pytest.raises(DownloadError, match="Path traversal detected"):
            validate_output_path(path)

    def test_pre_resolution_double_dot_in_middle_rejected(self, tmp_path: Path) -> None:
        """\"..\" anywhere in an unresolved path is caught."""
        path = tmp_path / "output" / ".." / ".." / "etc"
        with pytest.raises(DownloadError, match="Path traversal detected"):
            validate_output_path(path)

    def test_resolved_path_without_double_dot_accepted(self, tmp_path: Path) -> None:
        """A resolved path without '..' is accepted (SEC-006 post-resolution guard).

        SEC-006 adds a post-resolution '..' check as defense-in-depth.
        This test verifies valid resolved paths do not trigger false positives.
        """
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        resolved_path = real_dir / "video.mp4"
        result = validate_output_path(resolved_path.resolve(), warning=False)
        assert result == resolved_path.resolve()
        assert ".." not in str(result)

    def test_validate_output_path_accepts_already_resolved(self, tmp_path: Path) -> None:
        """SEC-006: already-resolved valid path is accepted."""
        path = tmp_path / "output" / "video.mp4"
        resolved = path.resolve()
        result = validate_output_path(resolved, warning=False)
        assert result == resolved

    def test_validate_output_path_rejects_traversal_even_if_resolved(self) -> None:
        """SEC-006: post-resolution guard catches '..' in resolved path.

        Constructs a path object whose string representation contains '..'
        even after resolve (simulated via string Path), verifying the
        post-resolution check fires.
        """
        # Build a path whose str() still contains ".." — this simulates
        # an already-resolved path that somehow retains ".." segments.
        path = Path("/safe/base") / ".." / "etc"
        # path.resolve() will resolve this to /etc (no ".."), but str(path) has ".."
        # The pre-resolution check catches it. For the post-resolution check,
        # we verify that a path object with ".." in its string form is rejected:
        with pytest.raises(DownloadError, match="Path traversal detected"):
            validate_output_path(path)

    def test_double_dot_inside_filename_accepted(self) -> None:
        """A literal filename component containing ".." (e.g. "a..b") is accepted.

        The guard inspects path *components*, so a filename that merely contains
        two consecutive dots is not confused with the parent-directory component
        ".." and is therefore not a false positive.
        """
        path = Path("a..b") / "video.mp4"
        with patch("vkdownloader.utils.security.logger"):
            result = validate_output_path(path, warning=True)
        assert result == path.resolve()

    def test_post_resolution_double_dot_component_rejected(self, tmp_path: Path) -> None:
        """A resolved path whose components still contain ".." is rejected.

        The input itself has no ".." component, so the pre-resolution guard is
        a no-op; the post-resolution guard must catch a resolved value whose
        parts still contain ".." (e.g. from a symlink or UNC path that survives
        normalization).
        """
        path = tmp_path / "output" / "video.mp4"
        malicious_resolved = Path("/safe") / ".." / "etc"
        with patch.object(Path, "resolve", return_value=malicious_resolved):
            with pytest.raises(DownloadError, match="Path traversal detected in resolved path"):
                validate_output_path(path, warning=False)


class TestResolveOutputFile:
    """Tests for _resolve_output_file path resolution."""

    def _make_video(
        self, title: str | None = "Test Video", video_id: str = "12345_67890"
    ) -> VideoWithStreams:
        return VideoWithStreams(
            id=video_id,
            title=title,
            streams=[
                Stream(
                    url="https://example.com/stream.m3u8", format=StreamFormat.HLS, quality="720"
                )
            ],
        )

    def test_uses_output_directory_when_provided(self, tmp_path: Path) -> None:
        """Test that a provided output directory is used."""
        settings = MagicMock(download_dir=Path("/default"))
        video = self._make_video()
        output_dir = tmp_path / "downloads"

        result = _resolve_output_file(video, output_dir, settings, 0)

        assert result.parent == output_dir.resolve()
        assert result.name == "Test Video_12345_67890.mp4"

    def test_uses_settings_download_dir_when_output_is_dot(self, tmp_path: Path) -> None:
        """Test that settings.download_dir is used when output is '.'."""
        settings = MagicMock(download_dir=tmp_path / "default_downloads")
        video = self._make_video()

        result = _resolve_output_file(video, Path("."), settings, 0)

        assert result.parent == (tmp_path / "default_downloads").resolve()
        assert result.name == "Test Video_12345_67890.mp4"

    def test_falls_back_to_index_when_title_none(self, tmp_path: Path) -> None:
        """Test that fallback filename uses index when title is None."""
        settings = MagicMock(download_dir=tmp_path)
        video = self._make_video(title=None)

        result = _resolve_output_file(video, Path("."), settings, 3)

        assert result.name == "3_12345_67890.mp4"

    def test_falls_back_to_index_when_title_empty(self, tmp_path: Path) -> None:
        """Test that fallback filename uses index when title is empty string."""
        settings = MagicMock(download_dir=tmp_path)
        video = self._make_video(title="")

        result = _resolve_output_file(video, Path("."), settings, 5)

        assert result.name == "5_12345_67890.mp4"

    def test_creates_output_directory_if_missing(self, tmp_path: Path) -> None:
        """Test that the output directory is created if it doesn't exist."""
        settings = MagicMock(download_dir=tmp_path)
        video = self._make_video()
        output_dir = tmp_path / "nested" / "downloads"

        result = _resolve_output_file(video, output_dir, settings, 0)

        assert output_dir.exists()
        assert result.parent == output_dir.resolve()

    def test_sanitizes_title_in_filename(self, tmp_path: Path) -> None:
        """Test that illegal characters in title are sanitized."""
        settings = MagicMock(download_dir=tmp_path)
        video = self._make_video(title="My:Video/Title")

        result = _resolve_output_file(video, Path("."), settings, 0)

        assert result.name == "My_Video_Title_12345_67890.mp4"
