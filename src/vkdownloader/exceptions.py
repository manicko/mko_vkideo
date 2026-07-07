"""Custom exception hierarchy for VK Video Downloader."""


class VKDownloadError(Exception):
    """Base exception for all VK Video Downloader errors."""

    pass


class VideoNotFoundError(VKDownloadError):
    """Raised when a requested video cannot be found."""

    pass


class QualityNotAvailableError(VKDownloadError):
    """Raised when requested quality is not available for a video."""

    pass


class ExtractionError(VKDownloadError):
    """Raised when video data extraction fails."""

    pass


class DownloadError(VKDownloadError):
    """Raised when video download fails."""

    pass
