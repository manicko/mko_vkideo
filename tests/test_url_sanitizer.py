"""Tests for URL sanitization utilities."""

from vkdownloader.utils.url_sanitizer import _strip_auth_params, sanitize_text_for_log


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


class TestSanitizeTextForLog:
    """Tests for sanitize_text_for_log function (SEC-002 subprocess output redaction)."""

    def test_redacts_url_in_text(self) -> None:
        """Test that URLs in text are redacted to scheme://host only."""
        text = "Error: cannot fetch https://cdn.example.com/seg.m3u8?token=abc123&sig=def456"
        result = sanitize_text_for_log(text)

        assert "abc123" not in result
        assert "def456" not in result
        assert "cdn.example.com" in result
        assert "https://cdn.example.com" in result

    def test_redacts_multiple_urls_in_text(self) -> None:
        """Test that multiple URLs in text are all redacted."""
        text = "From https://a.example.com/x?tok=aaa to https://b.example.com/y?tok=bbb"
        result = sanitize_text_for_log(text)

        assert "aaa" not in result
        assert "bbb" not in result
        assert "a.example.com" in result
        assert "b.example.com" in result

    def test_preserves_text_without_urls(self) -> None:
        """Test that text without URLs is unchanged."""
        text = "Simple error message with no URLs here"
        result = sanitize_text_for_log(text)

        assert result == text

    def test_redacts_url_in_yt_dlp_output(self) -> None:
        """Test URL redaction in typical yt-dlp error output format."""
        text = (
            "[download] https://vkvideo.ru/video-123_456 "
            "[warning] error: failed to fetch https://cdn.vkhost.com/stream.m3u8?sig=xyz"
        )
        result = sanitize_text_for_log(text)

        assert "sig=xyz" not in result
        assert "stream.m3u8?sig=xyz" not in result
        assert "vkvideo.ru" in result  # Host preserved for debugging
        assert "cdn.vkhost.com" in result  # Host preserved for debugging
