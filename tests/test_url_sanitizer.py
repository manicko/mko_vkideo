"""Tests for URL sanitization utilities."""

from vkdownloader.utils.url_sanitizer import _strip_auth_params


class TestStripAuthParams:
    """Tests for _strip_auth_params function."""

    def test_strips_url_with_query_params(self) -> None:
        """Test URL with query parameters is fully redacted."""
        url = "https://example.com/video.m3u8?token=abc123"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"
        assert "token" not in result
        assert "abc123" not in result

    def test_strips_url_with_multiple_query_params(self) -> None:
        """Test URL with multiple query parameters is fully redacted."""
        url = "https://example.com/video.m3u8?token=abc123&expire=3600&quality=720"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"
        assert "token" not in result
        assert "expire" not in result
        assert "quality" not in result
        assert "abc123" not in result

    def test_handles_url_without_query_params(self) -> None:
        """Test URL without query parameters still gets redacted."""
        url = "https://example.com/video.m3u8"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"

    def test_handles_empty_url(self) -> None:
        """Test empty URL returns redacted marker."""
        url = ""
        result = _strip_auth_params(url)

        assert result == "***REDACTED***"

    def test_strips_signed_cdn_url_with_path_token(self) -> None:
        """Test signed CDN URL with token in path is fully redacted."""
        url = "https://cdn.example.com/signature123/segment_0.ts?quality=720"
        result = _strip_auth_params(url)

        assert result == "https://cdn.example.com/***REDACTED***"
        assert "signature123" not in result
        assert "quality" not in result

    def test_strips_unknown_auth_params(self) -> None:
        """Test unknown auth parameters are redacted (allowlist strategy)."""
        url = "https://example.com/video.m3u8?siv=signed_value&extra=extra_value"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"
        assert "siv" not in result
        assert "signed_value" not in result

    def test_preserves_scheme_and_host(self) -> None:
        """Test that scheme and host are preserved."""
        url = "https://example.com/video.m3u8?token=secret"
        result = _strip_auth_params(url)

        assert "https://" in result
        assert "example.com" in result

    def test_handles_invalid_url(self) -> None:
        """Test that invalid URLs return redacted marker."""
        url = "not a valid url with ?query=params"
        result = _strip_auth_params(url)

        assert result == "***REDACTED***"