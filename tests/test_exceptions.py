"""Tests for exception mapping utility."""

from vkdownloader.exceptions import (
    QualityNotAvailableError,
    VideoNotFoundError,
    VKDownloadError,
    _map_exception_to_status,
)


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
