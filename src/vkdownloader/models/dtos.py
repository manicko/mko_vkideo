"""Data Transfer Objects for VK Video Downloader."""


from pydantic import BaseModel, HttpUrl

from .enums import QualityEnum
from .video import Stream


class DownloadRequest(BaseModel):
    """Request model for video download initiation."""

    url: HttpUrl
    quality: QualityEnum = QualityEnum.BEST
    output_path: str = "."
    filename: str | None = None


class DownloadResult(BaseModel):
    """Result model for completed video download."""

    video_id: str
    output_file: str
    file_size: int
    duration: int
    streams_used: list[Stream]
    success: bool
    error_message: str | None = None
