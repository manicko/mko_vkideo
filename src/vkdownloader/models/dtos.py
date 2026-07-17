"""Data Transfer Objects for VK Video Downloader."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel


class HLSDownloadRequest(BaseModel):
    """Request model for HLS download with segment-level resume.

    Contains only pure data fields - no service dependencies.
    Service objects (settings, extractor, backoff_coordinator) are passed
    as function arguments to download_hls_with_resume.
    """

    video_url: str
    m3u8_url: str
    output_file: Path
    quality: str = "best"
    cookies: str | None = None
    progress_callback: Callable[[str, int, int], None] | None = None
