"""Domain enums for VK Video Downloader."""

from enum import StrEnum


class QualityEnum(StrEnum):
    """Video quality options for stream selection."""

    Q240 = "240"
    Q360 = "360"
    Q480 = "480"
    Q720 = "720"
    Q1080 = "1080"
    Q1440 = "1440"
    Q2160 = "2160"
    BEST = "best"
    WORST = "worst"


class StreamFormat(StrEnum):
    """Stream format types."""

    HLS = "hls"
    MP4 = "mp4"


class LogLevel(StrEnum):
    """Standard logging level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DownloadMethod(StrEnum):
    """Download method options."""

    YTDLP = "yt-dlp"
    FFMPEG = "ffmpeg"
    AUTO = "auto"


class CookieSource(StrEnum):
    """Cookie acquisition strategy for video downloads."""

    NONE = "none"
    BROWSER = "browser"
    FILE = "file"


class ErrorCode(StrEnum):
    """Machine-readable error codes for structured logging and filtering.

    Each domain exception carries one of these codes so that log
    aggregators and users can filter and group by specific failure
    modes in structured (JSON) logs.
    """

    VIDEO_NOT_FOUND = "video_not_found"
    INVALID_URL = "invalid_url"
    QUALITY_NOT_AVAILABLE = "quality_not_available"
    QUALITY_PARSE_ERROR = "quality_parse_error"
    EXTRACTION_ERROR = "extraction_error"
    DOWNLOAD_ERROR = "download_error"
    PATH_TRAVERSAL = "path_traversal"
    UNEXPECTED_ERROR = "unexpected_error"
