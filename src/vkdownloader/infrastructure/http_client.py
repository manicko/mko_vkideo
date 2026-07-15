"""HTTP client wrapper with aiohttp for VK Video Downloader."""

import asyncio
import ssl
from collections.abc import Callable
from io import BufferedWriter
from pathlib import Path

import aiohttp
from structlog import get_logger

from ..config import Settings
from ..exceptions import DownloadError
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


class HttpClient:
    """Async context manager for HTTP requests with browser-like headers and retry logic."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize HttpClient with optional settings.

        Args:
            settings: Application settings. Constructs a new Settings() from environment when not provided.
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

        # Create SSL context based on settings
        if self.settings.ssl_verify:
            connector = aiohttp.TCPConnector()
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            logger.warning(
                "ssl_verification_disabled",
                message="SSL certificate verification is disabled - connections may be insecure",
            )

        self._session = aiohttp.ClientSession(headers=headers, timeout=timeout, connector=connector)
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
                    url=_strip_auth_params(url),
                    attempt=attempt + 1,
                    max_retries=self.settings.max_retries,
                    error=str(e),
                )
                if attempt < self.settings.max_retries - 1:
                    await asyncio.sleep(1)

        raise DownloadError(
            f"Failed to fetch {url} after {self.settings.max_retries} attempts"
        ) from last_error

    @staticmethod
    def _write_chunk_to_file(chunk: bytes, file_handle: BufferedWriter) -> int:
        """
        Write a chunk to file and return bytes written.

        Args:
            chunk: Bytes data to write.
            file_handle: Open file handle for writing.

        Returns:
            Number of bytes written.
        """
        file_handle.write(chunk)
        return len(chunk)

    @staticmethod
    def _update_progress(
        downloaded: int, total: int, callback: Callable[[int, int], None] | None
    ) -> None:
        """
        Update progress via callback if provided.

        Args:
            downloaded: Bytes downloaded so far.
            total: Total bytes to download.
            callback: Optional progress callback function.
        """
        if callback is not None:
            callback(downloaded, total)

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
                        bytes_downloaded += self._write_chunk_to_file(chunk, f)
                        self._update_progress(bytes_downloaded, total_bytes, progress_callback)

                logger.info(
                    "download_completed", url=_strip_auth_params(url), path=str(output_path)
                )

        except aiohttp.ClientError as e:
            logger.error(
                "download_failed", url=_strip_auth_params(url), path=str(output_path), error=str(e)
            )
            if output_path.exists():
                output_path.unlink()
            raise DownloadError(f"Failed to download {url}") from e
