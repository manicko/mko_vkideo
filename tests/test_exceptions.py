"""Tests for exception mapping utility."""

from vkdownloader.exceptions import (
    DownloadError,
    ExtractionError,
    InvalidVideoUrlError,
    QualityNotAvailableError,
    QualityParseError,
    VideoNotFoundError,
    VKDownloadError,
    _map_exception_to_status,
)
from vkdownloader.models.enums import ErrorCode


class TestMapExceptionToStatus:
    """Tests for _map_exception_to_status exception-to-label mapping."""

    def test_quality_not_available_no_streams(self) -> None:
        """Test QualityNotAvailableError with empty available is mapped as no_streams."""
        exc = QualityNotAvailableError("1080", [])
        result = _map_exception_to_status(exc)
        assert result.startswith("no_streams:")

    def test_quality_not_available_missing_quality(self) -> None:
        """Test QualityNotAvailableError with available qualities is mapped correctly."""
        exc = QualityNotAvailableError("1440", ["1080", "720"])
        result = _map_exception_to_status(exc)
        assert result.startswith("quality_not_available:")
        assert "1440" in result
        assert "1080" in result
        assert "720" in result

    def test_video_not_found(self) -> None:
        """Test VideoNotFoundError is mapped to video_not_found."""
        exc = VideoNotFoundError("Video ID 12345 not found")
        result = _map_exception_to_status(exc)
        assert result.startswith("video_not_found:")
        assert "not found" in result

    def test_download_error(self) -> None:
        """Test VKDownloadError (non-quality, non-not-found) is mapped to download_error."""
        exc = VKDownloadError("Segment download failed")
        result = _map_exception_to_status(exc)
        assert result.startswith("download_error:")
        assert "Segment download failed" in result

    def test_unexpected_exception(self) -> None:
        """Test generic Exception is mapped to unexpected_error with type name."""
        exc = RuntimeError("Something went wrong")
        result = _map_exception_to_status(exc)
        assert result == "unexpected_error: RuntimeError"

    def test_unexpected_exception_with_traceback(self) -> None:
        """Test that unexpected exceptions include the type name in the status."""
        exc = ValueError("Bad value")
        result = _map_exception_to_status(exc)
        assert result == "unexpected_error: ValueError"

    def test_quality_not_available_with_requested_and_available(self) -> None:
        """Test QualityNotAvailableError with both requested and available qualities."""
        exc = QualityNotAvailableError("2160", ["1080"])
        result = _map_exception_to_status(exc)
        assert "quality_not_available" in result
        assert "2160" in result

    def test_quality_not_available_empty_available_no_requested(self) -> None:
        """Test QualityNotAvailableError where available is empty and requested is empty."""
        exc = QualityNotAvailableError("", [])
        result = _map_exception_to_status(exc)
        assert result.startswith("quality_not_available:")

    def test_video_not_found_with_special_characters(self) -> None:
        """Test VideoNotFoundError with special characters in message."""
        exc = VideoNotFoundError("URL: https://vkvideo.ru/video-1_1")
        result = _map_exception_to_status(exc)
        assert "video_not_found" in result


class TestStructuredAttributes:
    """Tests for structured attributes on the exception hierarchy."""

    def test_base_error_code(self) -> None:
        """Test VKDownloadError has UNEXPECTED_ERROR error_code."""
        exc = VKDownloadError("something broke")
        assert exc.error_code == ErrorCode.UNEXPECTED_ERROR

    def test_video_not_found_error_code(self) -> None:
        """Test VideoNotFoundError has VIDEO_NOT_FOUND error_code."""
        exc = VideoNotFoundError("video 123 not found")
        assert exc.error_code == ErrorCode.VIDEO_NOT_FOUND

    def test_quality_not_available_error_code(self) -> None:
        """Test QualityNotAvailableError has QUALITY_NOT_AVAILABLE error_code."""
        exc = QualityNotAvailableError("1080", ["720"])
        assert exc.error_code == ErrorCode.QUALITY_NOT_AVAILABLE

    def test_quality_parse_error_code(self) -> None:
        """Test QualityParseError has QUALITY_PARSE_ERROR error_code."""
        exc = QualityParseError("bad")
        assert exc.error_code == ErrorCode.QUALITY_PARSE_ERROR

    def test_extraction_error_code(self) -> None:
        """Test ExtractionError has EXTRACTION_ERROR error_code."""
        exc = ExtractionError("extraction failed")
        assert exc.error_code == ErrorCode.EXTRACTION_ERROR

    def test_download_error_code(self) -> None:
        """Test DownloadError has DOWNLOAD_ERROR error_code."""
        exc = DownloadError("download failed")
        assert exc.error_code == ErrorCode.DOWNLOAD_ERROR

    def test_invalid_video_url_error_code(self) -> None:
        """Test InvalidVideoUrlError has INVALID_URL error_code."""
        exc = InvalidVideoUrlError("https://example.com/invalid")
        assert exc.error_code == ErrorCode.INVALID_URL

    # --- status_label() tests ---

    def test_status_label_base(self) -> None:
        """Test base exception status_label returns error: code."""
        exc = VKDownloadError("test")
        assert exc.status_label() == "error: unexpected_error"

    def test_status_label_video_not_found(self) -> None:
        """Test VideoNotFoundError status_label."""
        exc = VideoNotFoundError("test")
        assert exc.status_label() == "video_not_found"

    def test_status_label_quality_not_available_with_available(self) -> None:
        """Test QualityNotAvailableError status_label when qualities exist."""
        exc = QualityNotAvailableError("1080", ["720"])
        assert exc.status_label() == "quality_not_available"

    def test_status_label_quality_not_available_no_streams(self) -> None:
        """Test QualityNotAvailableError status_label when no streams."""
        exc = QualityNotAvailableError("1080", [])
        assert exc.status_label() == "no_streams"

    def test_status_label_quality_parse_error(self) -> None:
        """Test QualityParseError status_label."""
        exc = QualityParseError("bad")
        assert exc.status_label() == "invalid_quality"

    def test_status_label_extraction_error(self) -> None:
        """Test ExtractionError status_label."""
        exc = ExtractionError("test")
        assert exc.status_label() == "extraction_error"

    def test_status_label_download_error(self) -> None:
        """Test DownloadError status_label."""
        exc = DownloadError("test")
        assert exc.status_label() == "download_error"

    def test_status_label_invalid_video_url(self) -> None:
        """Test InvalidVideoUrlError status_label."""
        exc = InvalidVideoUrlError("https://example.com")
        assert exc.status_label() == "invalid_url"

    # --- user_message() tests ---

    def test_user_message_returns_str(self) -> None:
        """Test user_message() returns the string representation."""
        exc = VideoNotFoundError("video not found")
        assert exc.user_message() == str(exc)

    # --- log_context() tests ---

    def test_log_context_returns_dict(self) -> None:
        """Test log_context returns dict with error_code and message."""
        exc = QualityParseError("bad")
        ctx = exc.log_context()
        assert "error_code" in ctx
        assert "message" in ctx
        assert ctx["error_code"] == ErrorCode.QUALITY_PARSE_ERROR.value
        assert "Invalid quality value: bad" in str(ctx["message"])

    # --- InvalidVideoUrlError tests ---

    def test_invalid_video_url_is_vkdownload_error(self) -> None:
        """Test InvalidVideoUrlError is subclass of VKDownloadError."""
        exc = InvalidVideoUrlError("https://example.com/invalid")
        assert isinstance(exc, VKDownloadError)

    def test_invalid_video_url_message_contains_sanitized_url(self) -> None:
        """Test InvalidVideoUrlError message includes sanitized URL."""
        exc = InvalidVideoUrlError("https://example.com/invalid")
        msg = str(exc)
        assert "Invalid VK video URL" in msg
        # URL should be sanitized (no full URL in message)
        assert "https://example.com/invalid" not in msg

    def test_invalid_video_url_url_attr(self) -> None:
        """Test InvalidVideoUrlError stores the original url."""
        url = "https://vkvideo.ru/video-12345_67890"
        exc = InvalidVideoUrlError(url)
        assert exc.url == url


class TestExtractionErrorStatusMapping:
    """Tests for ExtractionError status mapping via _map_exception_to_status."""

    def test_extraction_error_mapped(self) -> None:
        """Test ExtractionError is mapped to extraction_error status."""
        exc = ExtractionError("extraction failed")
        result = _map_exception_to_status(exc)
        assert result.startswith("extraction_error:")
        assert "extraction failed" in result

    def test_extraction_error_status_label(self) -> None:
        """Test ExtractionError.status_label() returns extraction_error."""
        exc = ExtractionError("test")
        assert exc.status_label() == "extraction_error"

    def test_download_error_mapped(self) -> None:
        """Test DownloadError is mapped to download_error status."""
        exc = DownloadError("download failed")
        result = _map_exception_to_status(exc)
        assert result.startswith("download_error:")
        assert "download failed" in result

    def test_download_error_status_label(self) -> None:
        """Test DownloadError.status_label() returns download_error."""
        exc = DownloadError("test")
        assert exc.status_label() == "download_error"
