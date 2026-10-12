"""Tests for exception hierarchy status labels and structured attributes."""

from vkdownloader.exceptions import (
    DownloadError,
    ExtractionError,
    InvalidVideoUrlError,
    QualityNotAvailableError,
    QualityParseError,
    VideoNotFoundError,
    VKDownloadError,
)
from vkdownloader.models.enums import ErrorCode


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

    def test_no_streams_error_code(self) -> None:
        """Test ErrorCode has NO_STREAMS member."""
        assert ErrorCode.NO_STREAMS.value == "no_streams"

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
        """Test base exception status_label returns error_code value."""
        exc = VKDownloadError("test")
        assert exc.status_label() == ErrorCode.UNEXPECTED_ERROR.value

    def test_status_label_video_not_found(self) -> None:
        """Test VideoNotFoundError status_label."""
        exc = VideoNotFoundError("test")
        assert exc.status_label() == ErrorCode.VIDEO_NOT_FOUND.value

    def test_status_label_quality_not_available_with_available(self) -> None:
        """Test QualityNotAvailableError status_label when qualities exist."""
        exc = QualityNotAvailableError("1080", ["720"])
        assert exc.status_label() == ErrorCode.QUALITY_NOT_AVAILABLE.value

    def test_status_label_quality_not_available_no_streams(self) -> None:
        """Test QualityNotAvailableError status_label when no streams."""
        exc = QualityNotAvailableError("1080", [])
        assert exc.status_label() == ErrorCode.NO_STREAMS.value

    def test_status_label_quality_parse_error(self) -> None:
        """Test QualityParseError status_label."""
        exc = QualityParseError("bad")
        assert exc.status_label() == ErrorCode.QUALITY_PARSE_ERROR.value

    def test_status_label_extraction_error(self) -> None:
        """Test ExtractionError status_label."""
        exc = ExtractionError("test")
        assert exc.status_label() == ErrorCode.EXTRACTION_ERROR.value

    def test_status_label_download_error(self) -> None:
        """Test DownloadError status_label."""
        exc = DownloadError("test")
        assert exc.status_label() == ErrorCode.DOWNLOAD_ERROR.value

    def test_status_label_invalid_video_url(self) -> None:
        """Test InvalidVideoUrlError status_label."""
        exc = InvalidVideoUrlError("https://example.com")
        assert exc.status_label() == ErrorCode.INVALID_URL.value

    # --- invariant: every status_label() returns an ErrorCode member value ---

    def test_status_label_invariant_all_classes(self) -> None:
        """Every exception class's status_label() returns its error_code.value.

        Closes QLT-010's oracle gap: no test previously asserted that
        status_label() always equals error_code.value. QualityNotAvailableError
        is the sole documented exception — it overrides status_label() to
        return ErrorCode.NO_STREAMS.value when available is empty and
        ErrorCode.QUALITY_NOT_AVAILABLE.value otherwise.
        """
        # Classes that derive status_label from error_code.value (no override).
        direct_derivation_classes: list[type[VKDownloadError]] = [
            VKDownloadError,
            VideoNotFoundError,
            InvalidVideoUrlError,
            QualityParseError,
            ExtractionError,
            DownloadError,
        ]
        for exc_cls in direct_derivation_classes:
            exc: VKDownloadError
            if exc_cls is InvalidVideoUrlError:
                exc = exc_cls("https://example.com/invalid")
            elif exc_cls is QualityParseError:
                exc = exc_cls("bad")
            else:
                exc = exc_cls("test")
            assert exc.status_label() == exc.error_code.value, (
                f"{exc_cls.__name__}.status_label() should return error_code.value"
            )

        # ExtractionError allows a custom error_code at construction; the
        # override must be reflected by status_label() too.
        custom_exc = ExtractionError("msg", error_code=ErrorCode.STEALTH_ASSET_MISSING)
        assert custom_exc.status_label() == ErrorCode.STEALTH_ASSET_MISSING.value

        # QualityNotAvailableError: documented override with two branches.
        # Branch 1: available is non-empty -> QUALITY_NOT_AVAILABLE.value.
        exc_with_available = QualityNotAvailableError("1080", ["720"])
        assert exc_with_available.status_label() == ErrorCode.QUALITY_NOT_AVAILABLE.value
        # Branch 2: available is empty -> NO_STREAMS.value.
        exc_no_streams = QualityNotAvailableError("1080", [])
        assert exc_no_streams.status_label() == ErrorCode.NO_STREAMS.value

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
