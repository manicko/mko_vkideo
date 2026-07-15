"""Data Transfer Objects for VK Video Downloader."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class HLSDownloadRequest(BaseModel):
    """Request model for HLS download with segment-level resume."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    video_url: str
    m3u8_url: str
    output_file: Path
    quality: str = "best"
    cookies: str | None = None
    # Runtime types: Settings | None and VKVideoExtractor | None
    settings: Settings | None = None  # type: ignore[name-defined]  # noqa: F821
    extractor: VKVideoExtractor | None = None  # type: ignore[name-defined]  # noqa: F821
    # Runtime type: URLBackoffCoordinator | None for shared rate limiting across URLs
    backoff_coordinator: URLBackoffCoordinator | None = None  # type: ignore[name-defined]  # noqa: F821
    # Progress callback receives (video_id, downloaded, total) for per-URL progress tracking.
    progress_callback: Callable[[str, int, int], None] | None = None
    # Shared semaphore for work-stealing concurrency across batch downloads
    semaphore: asyncio.Semaphore | None = None


# Lazy model rebuild - called only when actually needed (when non-None values are passed)
# This avoids circular import issues at module load time
def _ensure_model_rebuilt() -> None:
    """Ensure HLSDownloadRequest model is rebuilt with forward references resolved."""
    # Bind types to module namespace for forward references
    import vkdownloader.models.dtos as dtos_module
    from vkdownloader.config import Settings
    from vkdownloader.services.downloader_throttle import URLBackoffCoordinator
    from vkdownloader.services.extractor import VKVideoExtractor

    dtos_module.Settings = Settings  # type: ignore[attr-defined]
    dtos_module.VKVideoExtractor = VKVideoExtractor  # type: ignore[attr-defined]
    dtos_module.URLBackoffCoordinator = URLBackoffCoordinator  # type: ignore[attr-defined]
    HLSDownloadRequest.model_rebuild()


# Patch the model's __init__ to trigger rebuild on first use with non-None values
_original_init = HLSDownloadRequest.__init__


def _lazy_init(self: HLSDownloadRequest, **data: object) -> None:
    """Lazy init that rebuilds model on first use with actual types."""
    if not hasattr(HLSDownloadRequest, "_model_rebuilt"):
        _ensure_model_rebuilt()
        HLSDownloadRequest._model_rebuilt = True  # type: ignore[attr-defined]
    _original_init(self, **data)  # type: ignore[arg-type]


HLSDownloadRequest.__init__ = _lazy_init  # type: ignore[method-assign]
