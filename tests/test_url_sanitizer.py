"""Tests for URL sanitization utilities."""

from vkdownloader.utils.url_sanitizer import _strip_auth_params


class TestStripAuthParams:
    """Tests for _strip_auth_params function."""

    def test_strip_single_token_param(self) -> None:
        """Test stripping a single token parameter from URL."""
        url = "https://example.com/video.m3u8?token=abc123"
        result = _strip_auth_params(url)

        assert "token" not in result
        assert result == "https://example.com/video.m3u8"

    def test_strip_multiple_auth_params(self) -> None:
        """Test stripping multiple auth parameters from URL."""
        url = "https://example.com/video.m3u8?token=abc123&expire=3600&quality=720"
        result = _strip_auth_params(url)

        assert "token" not in result
        assert "expire" not in result
        assert "quality=720" in result
        assert result == "https://example.com/video.m3u8?quality=720"

    def test_preserve_non_auth_params(self) -> None:
        """Test that non-auth parameters are preserved."""
        url = "https://example.com/video.m3u8?quality=720&format=mp4"
        result = _strip_auth_params(url)

        assert "quality=720" in result
        assert "format=mp4" in result
        assert result == "https://example.com/video.m3u8?quality=720&format=mp4"

    def test_no_query_params(self) -> None:
        """Test URL without query parameters returns unchanged."""
        url = "https://example.com/video.m3u8"
        result = _strip_auth_params(url)

        assert result == url

    def test_empty_url(self) -> None:
        """Test empty URL returns empty string."""
        url = ""
        result = _strip_auth_params(url)

        assert result == url

    def test_strip_access_token(self) -> None:
        """Test stripping access_token parameter."""
        url = "https://example.com/video.m3u8?access_token=xyz789&other=value"
        result = _strip_auth_params(url)

        assert "access_token" not in result
        assert "other=value" in result

    def test_strip_signature_params(self) -> None:
        """Test stripping signature-related parameters."""
        url = "https://example.com/video.m3u8?signature=sig123&sig=sig456&data=test"
        result = _strip_auth_params(url)

        assert "signature" not in result
        assert "sig" not in result
        assert "data=test" in result

    def test_strip_expire_params(self) -> None:
        """Test stripping expire-related parameters."""
        url = "https://example.com/video.m3u8?expires=123456&expires_in=3600"
        result = _strip_auth_params(url)

        assert "expires" not in result
        assert "expires_in" not in result

    def test_case_insensitive_param_matching(self) -> None:
        """Test that parameter matching is case-insensitive."""
        url = "https://example.com/video.m3u8?TOKEN=abc123&Expires=7200"
        result = _strip_auth_params(url)

        assert "TOKEN" not in result
        assert "Expires" not in result
        assert result == "https://example.com/video.m3u8"

    def test_invalid_url_returns_unchanged(self) -> None:
        """Test that invalid URLs return unchanged on exception."""
        url = "not a valid url with ?query=params"
        # The function should handle this gracefully
        result = _strip_auth_params(url)

        # Function returns original URL on parsing exception
        assert result == url
