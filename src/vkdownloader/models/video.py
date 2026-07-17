"""Core domain models for VK Video Downloader."""

from pydantic import BaseModel

from .enums import StreamFormat


class Video(BaseModel):
    """Represents a VK video with metadata."""

    id: str
    title: str | None = None


class Stream(BaseModel):
    """Represents a video stream with URL and quality information."""

    url: str
    format: StreamFormat
    quality: str
    resolution: str | None = None
    bitrate: int | None = None
    width: int | None = None
    height: int | None = None


class VideoWithStreams(Video):
    """Video model extended with available streams."""

    streams: list[Stream]
