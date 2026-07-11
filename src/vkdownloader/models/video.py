"""Core domain models for VK Video Downloader."""


from pydantic import BaseModel, HttpUrl

from .enums import DownloadStatus, StreamFormat


class Video(BaseModel):
    """Represents a VK video with metadata."""

    id: str
    title: str | None = None
    description: str | None = None
    duration: int | None = None
    thumbnail: HttpUrl | None = None
    upload_date: str | None = None
    views: int | None = None


class Stream(BaseModel):
    """Represents a video stream with URL and quality information."""

    url: HttpUrl
    format: StreamFormat
    quality: str
    resolution: str | None = None
    bitrate: int | None = None
    width: int | None = None
    height: int | None = None


class VideoWithStreams(Video):
    """Video model extended with available streams."""

    streams: list[Stream]


class DownloadProgress(BaseModel):
    """Tracks download progress for a video."""

    video_id: str
    downloaded_bytes: int
    total_bytes: int | None = None
    segments_downloaded: int
    segments_total: int
    speed: float | None = None  # bytes/sec
    eta_seconds: int | None = None
    percent: float | None = None
    status: DownloadStatus
    error: str | None = None


class StreamWithCookies(Stream):
    """Stream with associated cookies for authentication."""

    cookies: str | None = None
