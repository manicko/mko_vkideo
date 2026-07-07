"""HTTP client wrapper with aiohttp for VK Video Downloader."""

import asyncio
from collections.abc import Callable
from pathlib import Path

import aiohttp
from structlog import get_logger

from ..config import Settings
from ..exceptions import DownloadError

logger = get_logger(__name__)


class HttpClient:
    """Async context manager for HTTP requests with browser-like headers and retry logic."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize HttpClient with optional settings.

        Args:
            settings: Application settings. Uses global settings if not provided.
        """
        self.settings = settings if settings is not None else Settings()
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get the session, raising an error if not initialized."""
        if self._session is None:
            raise RuntimeError("HttpClient session not initialized. Use as async context manager.")
        return self._session

    async def __aenter__(self) -> "HttpClient":
        """Start aiohttp ClientSession with browser-like headers and timeout."""
        logger.info("starting_http_client")

        timeout = aiohttp.ClientTimeout(total=self.settings.download_timeout)
        headers = {
            "User-Agent": self.settings.user_agent,
            "Referer": "https://vkvideo.ru/",
            "Accept-Language": self.settings.accept_language,
        }

        self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Close aiohttp ClientSession."""
        logger.info("closing_http_client")

        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get(self, url: str) -> str:
        """
        Perform GET request with retry logic.

        Args:
            url: Target URL for the request.

        Returns:
            Response text content.

        Raises:
            DownloadError: If all retry attempts fail.
        """
        last_error: Exception | None = None

        for attempt in range(self.settings.max_retries):
            try:
                response = await self.session.get(url)
                response.raise_for_status()
                result: str = await response.text()
                return result
            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(
                    "http_request_failed",
                    url=url,
                    attempt=attempt + 1,
                    max_retries=self.settings.max_retries,
                    error=str(e),
                )
                if attempt < self.settings.max_retries - 1:
                    await asyncio.sleep(1)

        raise DownloadError(f"Failed to fetch {url} after {self.settings.max_retries} attempts") from last_error

    async def download_file(
        self,
        url: str,
        output_path: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """
        Download file from URL with progress tracking.

        Args:
            url: Source URL to download from.
            output_path: Local path to save downloaded file.
            progress_callback: Optional callback for progress updates (bytes_downloaded, total_bytes).

        Raises:
            DownloadError: If download fails.
        """
        buffer_size = 8192
        bytes_downloaded = 0
        total_bytes = 0

        try:
            async with self.session.get(url) as response:
                response.raise_for_status()

                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    total_bytes = int(content_length)

                output_path.parent.mkdir(parents=True, exist_ok=True)

                with output_path.open("wb") as f:
                    async for chunk in response.content.iter_chunked(buffer_size):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        if progress_callback is not None:
                            progress_callback(bytes_downloaded, total_bytes)

                logger.info("download_completed", url=url, path=str(output_path))

        except aiohttp.ClientError as e:
            logger.error("download_failed", url=url, path=str(output_path), error=str(e))
            if output_path.exists():
                output_path.unlink()
            raise DownloadError(f"Failed to download {url}") from e
