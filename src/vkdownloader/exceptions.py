"""Custom exception hierarchy for VK Video Downloader.

Every domain exception carries a machine-readable :class:`ErrorCode` and a
polymorphic ``status_label()`` so that structured JSON logs and batch
results can be filtered deterministically. ``status_label()`` returns the
``value`` of the exception's :attr:`ErrorCode` member; the sole override is
on :class:`QualityNotAvailableError`, which returns
``ErrorCode.NO_STREAMS`` when no streams are available and
``ErrorCode.QUALITY_NOT_AVAILABLE`` otherwise.
"""

from vkdownloader.models.enums import ErrorCode
from vkdownloader.utils.url_sanitizer import _strip_auth_params


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

        Returns the ``value`` of this exception's :attr:`ErrorCode`
        member (e.g., ``"unexpected_error"`` for the base class). The sole
        override is on :class:`QualityNotAvailableError`, which returns
        ``ErrorCode.NO_STREAMS.value`` (``"no_streams"``) when no streams
        are available and ``ErrorCode.QUALITY_NOT_AVAILABLE.value``
        (``"quality_not_available"``) otherwise.
        """
        return self.error_code.value

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
        super().__init__(f"Invalid VK video URL: {_strip_auth_params(url)}")


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

        Returns ``ErrorCode.NO_STREAMS.value`` (``"no_streams"``) when
        the available list is empty, otherwise
        ``ErrorCode.QUALITY_NOT_AVAILABLE.value``
        (``"quality_not_available"``).
        """
        if not self.available:
            return ErrorCode.NO_STREAMS.value
        return ErrorCode.QUALITY_NOT_AVAILABLE.value


class QualityParseError(VKDownloadError):
    """Raised when a quality string cannot be parsed to QualitySpec.

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


class ExtractionError(VKDownloadError):
    """Raised when video data extraction fails.

    Carries an ``error_code`` that may differ from the class-level
    ``EXTRACTION_ERROR`` to distinguish sub-causes (for example, a missing
    stealth asset) while remaining an ``ExtractionError`` so that callers
    need no new handler.
    """

    error_code = ErrorCode.EXTRACTION_ERROR

    def __init__(
        self,
        message: str | None = None,
        error_code: ErrorCode | None = None,
    ) -> None:
        """Initialize with an optional message and optional error code.

        Args:
            message: Optional human-readable message. Defaults to the
                class name when not provided.
            error_code: Optional machine-readable code. When provided, it
                overrides the class-level ``EXTRACTION_ERROR`` to distinguish
                sub-causes (e.g. a missing stealth asset).
        """
        super().__init__(message)
        if error_code is not None:
            self.error_code = error_code


class DownloadError(VKDownloadError):
    """Raised when video download fails."""

    error_code = ErrorCode.DOWNLOAD_ERROR
