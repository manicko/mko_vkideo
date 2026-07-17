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
