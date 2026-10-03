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

    def test_filesystem_paths_are_not_redacted(self) -> None:
        """Filesystem paths pass through unchanged; only URLs are redacted.

        ``_URL_REGEX`` matches only ``https?://`` URLs, so a bare
        filesystem path (e.g. a yt-dlp ``--cookies`` argument) can never
        match and is returned byte-identical. This pins the capability
        boundary so the redaction claim cannot silently drift back.
        """
        cookie_path = "/tmp/vkdownloader_cookies_8u3x.txt"
        signed_url = "https://cdn.example.com/seg.m3u8?token=abc123&sig=def456"
        text = f"cookies: {cookie_path} - fetch: {signed_url}"
        result = sanitize_text_for_log(text)

        # Signed CDN URL is redacted to scheme + host only.
        assert "https://cdn.example.com" in result
        assert "abc123" not in result
        assert "def456" not in result
        # Filesystem path is untouched -- no path-matching clause exists.
        assert cookie_path in result

    def test_transform_before_truncate_proves_sanitize_order(self) -> None:
        """SEC-002: prove sanitize-then-truncate ordering (ffmpeg_utils pattern).

        ``ffmpeg_utils`` calls ``sanitize_text_for_log(error)[:200]``. When a
        signed URL starts past the 200-char boundary, truncating first would
        silently drop it (no host in the log); sanitizing first shrinks it to
        ``scheme://host/***REDACTED***/`` so the host survives truncation.

        The ``len(result) == 200`` assertion pins the order: the wrong order
        (``sanitize_text_for_log(error[:200])``) would produce a string
        *longer* than 200 chars after the short redaction expands the URL.
        """
        filler = "x" * 170
        signed_url = "https://cdn.example.com/seg.m3u8?token=SECRET123&sig=ABC"
        error = f"{filler}{signed_url}"

        result = sanitize_text_for_log(error)[:200]

        assert "cdn.example.com" in result
        assert "SECRET123" not in result
        assert "ABC" not in result
        assert len(result) == 200

    def test_redacts_signed_cdn_url_in_merge_failure_text(self) -> None:
        """Merge-failure stderr with a signed CDN URL must be fully redacted."""
        text = (
            "ffmpeg version 6.0 Copyright (c) 2023\n"
            "Error opening https://cdn.vkhost.com/segments/00000.ts"
            "?token=s3cr3t&sig=deadbeef as\n"
            "Input #0"
        )
        result = sanitize_text_for_log(text)

        assert "s3cr3t" not in result
        assert "deadbeef" not in result
        assert "cdn.vkhost.com" in result
        assert "https://cdn.vkhost.com" in result

    def test_preserves_plaintext_merge_failure_text(self) -> None:
        """Plaintext error messages without URLs pass through byte-identical."""
        text = "Error: invalid data found when processing input stream"
        result = sanitize_text_for_log(text)

        assert result == text
