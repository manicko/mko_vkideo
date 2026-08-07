"""Custom exception hierarchy for VK Video Downloader.

Every domain exception carries a machine-readable :class:`ErrorCode` and a
polymorphic ``status_label()`` so that structured JSON logs and batch
results can be filtered deterministically. The legacy
``_map_exception_to_status()`` helper and ``_EXCEPTION_STATUS_HANDLERS``
dict are retained for backward compatibility; new call sites should
prefer ``status_label()`` directly.
"""

from collections.abc import Callable

from vkdownloader.models.enums import ErrorCode


class VKDownloadError(Exception):
    """Base exception for all VK Video Downloader errors.

    Attributes:
        error_code: Stable machine-readable code for log filtering.
            Subclasses set this to their specific ``ErrorCode``; the base
            defaults to :attr:`ErrorCode.UNEXPECTED_ERROR`.
    """

    error_code: ErrorCode = ErrorCode.UNEXPECTED_ERROR

    def __init__(self, message: str | None = None) -> None:
        """Initialize with an optional message.

        When ``message`` is ``None``, defaults to the class name
        (e.g., ``"VideoNotFoundError"``). Subclasses with custom
        ``__init__`` signatures pass a string to ``super().__init__``
        and remain compatible because a string is truthy and accepted
        as ``message``.

        Args:
            message: Optional human-readable message. Defaults to the
                class name when not provided.
        """
        if message is not None:
            super().__init__(message)
        else:
            super().__init__(self.__class__.__name__)

    def status_label(self) -> str:
        """Return a short, machine-readable status label for batch results.

        Format: ``"error: <error_code_value>"`` (e.g.,
        ``"error: unexpected_error"``). Subclasses override to return
        codes like ``"no_streams"``, ``"video_not_found"``, etc.
        """
        return f"error: {self.error_code.value}"

    def user_message(self) -> str:
        """Return a human-readable message for end users."""
        return str(self)

    def log_context(self) -> dict[str, object]:
        """Return a dict of structured fields for structlog.

        Includes the machine-readable ``error_code`` and the exception
        ``message`` string.
        """
        return {
            "error_code": self.error_code.value,
            "message": str(self),
        }


class VideoNotFoundError(VKDownloadError):
    """Raised when a requested video cannot be found."""

    error_code = ErrorCode.VIDEO_NOT_FOUND

    def status_label(self) -> str:
        """Return status label for video-not-found errors."""
        return "video_not_found"


class InvalidVideoUrlError(VKDownloadError):
    """Raised when a URL does not match the VK video URL pattern.

    Attributes:
        url: The original URL that failed validation.
    """

    error_code = ErrorCode.INVALID_URL
    url: str

    def __init__(self, url: str) -> None:
        """Initialize with the offending URL.

        Args:
            url: The URL that did not match the VK video URL pattern.
        """
        self.url = url
        # Imported lazily to avoid a circular import: vkdownloader.utils
        # package __init__ imports security.py, which imports DownloadError
        # from this module at module load time.
        from vkdownloader.utils.url_sanitizer import _strip_auth_params

        super().__init__(f"Invalid VK video URL: {_strip_auth_params(url)}")

    def status_label(self) -> str:
        """Return status label for invalid-URL errors."""
        return "invalid_url"


class QualityNotAvailableError(VKDownloadError):
    """Raised when requested quality is not available for a video.

    Attributes:
        requested: The quality string that was requested (e.g., "1440p").
        available: List of available quality strings (e.g., ["1080p", "720p"]).
    """

    error_code = ErrorCode.QUALITY_NOT_AVAILABLE
    requested: str
    available: list[str]

    def __init__(
        self,
        requested: str,
        available: list[str],
        message: str | None = None,
    ) -> None:
        """Initialize the exception with requested and available qualities.

        Args:
            requested: The quality string that was requested.
            available: List of available quality strings.
            message: Optional custom message. If None, uses default format.
        """
        self.requested = requested
        self.available = available
        if message is not None:
            super().__init__(message)
        else:
            super().__init__(f"Quality '{requested}' not available. Available: {available}")

    def status_label(self) -> str:
        """Return status label based on whether streams are available.

        Returns ``"no_streams"`` when the available list is empty,
        otherwise ``"quality_not_available"``.
        """
        if not self.available:
            return "no_streams"
        return "quality_not_available"


class QualityParseError(VKDownloadError):
    """Raised when a quality string cannot be parsed to QualityEnum.

    Attributes:
        quality: The quality string that failed to parse.
    """

    error_code = ErrorCode.QUALITY_PARSE_ERROR
    quality: str

    def __init__(self, quality: str) -> None:
        """Initialize with the unparseable quality string.

        Args:
            quality: The quality string that failed to parse.
        """
        self.quality = quality
        super().__init__(f"Invalid quality value: {quality}")

    def status_label(self) -> str:
        """Return status label for parse errors."""
        return "invalid_quality"


class ExtractionError(VKDownloadError):
    """Raised when video data extraction fails."""

    error_code = ErrorCode.EXTRACTION_ERROR

    def status_label(self) -> str:
        """Return status label for extraction errors."""
        return "extraction_error"


class DownloadError(VKDownloadError):
    """Raised when video download fails."""

    error_code = ErrorCode.DOWNLOAD_ERROR

    def status_label(self) -> str:
        """Return status label for download errors."""
        return "download_error"


def _map_exception_to_status(exc: Exception) -> str:
    """Map exception to status label for batch results.

    Args:
        exc: The exception to map.

    Returns:
        Status label string (e.g., ``"no_streams: <message>"``,
        ``"video_not_found: <message>"``, ``"download_error: <message>"``).
    """
    for exc_type, handler in _EXCEPTION_STATUS_HANDLERS.items():
        if isinstance(exc, exc_type):
            return handler(exc)
    return f"unexpected_error: {type(exc).__name__}"


def _quality_not_available_status(exc: QualityNotAvailableError) -> str:
    if not exc.available and exc.requested:
        return f"no_streams: {exc}"
    return (
        f"quality_not_available: requested {exc.requested}p, available: {', '.join(exc.available)}"
    )


_EXCEPTION_STATUS_HANDLERS: dict[type[Exception], Callable[..., str]] = {
    ExtractionError: lambda e: f"extraction_error: {e}",
    DownloadError: lambda e: f"download_error: {e}",
    InvalidVideoUrlError: lambda e: f"invalid_url: {e}",
    QualityNotAvailableError: _quality_not_available_status,
    QualityParseError: lambda e: f"invalid_quality: {e.quality}",
    VideoNotFoundError: lambda e: f"video_not_found: {e}",
    VKDownloadError: lambda e: f"download_error: {e}",
}
