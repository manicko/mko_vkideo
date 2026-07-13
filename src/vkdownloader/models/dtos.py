"""Data Transfer Objects for VK Video Downloader."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, HttpUrl

from .enums import QualityEnum
from .video import Stream


class DownloadRequest(BaseModel):
    """Request model for video download initiation."""

    url: HttpUrl
    quality: QualityEnum = QualityEnum.BEST
    output_path: str = "."
    filename: str | None = None


class HLSDownloadRequest(BaseModel):
    """Request model for HLS download with segment-level resume."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    video_url: str
    m3u8_url: str
    output_file: Path
    quality: str = "best"
    cookies: str | None = None
    # Runtime types: Settings | None and VKVideoExtractor | None
    # Using Any to avoid circular import issues at module load time
    # Type checkers understand these as the correct types via forward references
    settings: Any | None = None
    extractor: Any | None = None
    # Runtime type: URLBackoffCoordinator | None for shared rate limiting across URLs
    # Using Any to avoid circular import issues at module load time
    backoff_coordinator: Any | None = None
    # Progress callback receives (video_id, downloaded, total) for per-URL progress tracking.
    # Fire-and-forget mechanism - non-blocking, called from download tasks.
    progress_callback: Callable[[str, int, int], None] | None = None
    # Shared semaphore for work-stealing concurrency across batch downloads
    semaphore: asyncio.Semaphore | None = None


class DownloadResult(BaseModel):
    """Result model for completed video download."""

    video_id: str
    output_file: str
    file_size: int
    duration: int
    streams_used: list[Stream]
    success: bool
    error_message: str | None = None
