"""Shared concurrency primitives for VK Video Downloader."""

from __future__ import annotations

from typing import Any, Protocol


class SemaphoreLike(Protocol):
    """Protocol for objects usable as an async context manager semaphore.

    Matches ``asyncio.Semaphore`` and wrapper classes that implement
    ``__aenter__``/``__aexit__``.
    """

    async def __aenter__(self) -> Any: ...
    async def __aexit__(self, *args: object) -> None: ...
