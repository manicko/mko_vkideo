"""Custom exception hierarchy for VK Video Downloader."""


class VKDownloadError(Exception):
    """Base exception for all VK Video Downloader errors."""

    pass


class VideoNotFoundError(VKDownloadError):
    """Raised when a requested video cannot be found."""

    pass


class QualityNotAvailableError(VKDownloadError):
    """Raised when requested quality is not available for a video.

    Attributes:
        requested: The quality string that was requested (e.g., "1440p").
        available: List of available quality strings (e.g., ["1080p", "720p"]).
    """

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


class ExtractionError(VKDownloadError):
    """Raised when video data extraction fails."""

    pass


class DownloadError(VKDownloadError):
    """Raised when video download fails."""

    pass
