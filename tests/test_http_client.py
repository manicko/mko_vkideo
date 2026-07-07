"""Tests for HttpClient with retry logic and timeout handling."""

from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import DownloadError
from vkdownloader.infrastructure.http_client import HttpClient


class TestHttpClient:
    """Tests for HttpClient class."""

    def test_http_client_init_with_settings(self, test_settings: Settings) -> None:
        """Test HttpClient initializes correctly with provided settings."""
        client = HttpClient(settings=test_settings)

        assert client.settings == test_settings
        assert client._session is None

    def test_http_client_init_without_settings(self) -> None:
        """Test HttpClient initializes with default settings when not provided."""
        client = HttpClient()

        assert client.settings is not None
        assert isinstance(client.settings, Settings)

    @pytest.mark.asyncio
    async def test_http_client_context_entry(self, test_settings: Settings) -> None:
        """Test HttpClient context manager starts session correctly."""
        client = HttpClient(settings=test_settings)

        with patch("vkdownloader.infrastructure.http_client.aiohttp.ClientSession") as mock_session:
            mock_session.return_value = MagicMock()
            result = await client.__aenter__()

            assert result is client
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_http_client_context_exit(self, test_settings: Settings) -> None:
        """Test HttpClient context manager closes session correctly."""
        client = HttpClient(settings=test_settings)
        mock_session = AsyncMock()
        client._session = mock_session

        await client.__aexit__(None, None, None)

        mock_session.close.assert_called_once()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_http_client_headers(self, test_settings: Settings) -> None:
        """Test HttpClient sets correct headers on session."""
        client = HttpClient(settings=test_settings)

        with patch("vkdownloader.infrastructure.http_client.aiohttp.ClientSession") as mock_session:
            mock_session.return_value = MagicMock()
            await client.__aenter__()

            call_kwargs = mock_session.call_args[1]
            headers = call_kwargs["headers"]

            assert "User-Agent" in headers
            assert headers["User-Agent"] == test_settings.user_agent
            assert "Referer" in headers
            assert headers["Referer"] == "https://vkvideo.ru/"
            assert "Accept-Language" in headers
            assert headers["Accept-Language"] == test_settings.accept_language


class TestHttpClientRetryLogic:
    """Tests for HttpClient retry logic."""

    @pytest.mark.asyncio
    async def test_retry_logic_success_on_first_attempt(self, test_settings: Settings) -> None:
        """Test HttpClient returns result on first successful attempt."""
        client = HttpClient(settings=test_settings)

        # Create response mock - session.get returns response directly (not async context manager in get())
        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="success content")
        mock_response.raise_for_status = MagicMock()

        # Use AsyncMock for session.get to make it awaitable
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        client._session = mock_session

        result = await client.get("https://example.com/test")

        assert result == "success content"

    @pytest.mark.asyncio
    async def test_retry_logic_raises_on_all_failures(self, test_settings: Settings) -> None:
        """Test HttpClient raises DownloadError after all retries fail."""
        client = HttpClient(settings=test_settings)
        client.settings.max_retries = 2

        mock_response = AsyncMock()
        mock_response.text = AsyncMock(return_value="")
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientError("Failed"))

        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        client._session = mock_session

        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(DownloadError, match="Failed to fetch"):
                await client.get("https://example.com/test")


class TestHttpClientTimeout:
    """Tests for HttpClient timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_handling(self, test_settings: Settings) -> None:
        """Test HttpClient applies timeout to session."""
        client = HttpClient(settings=test_settings)

        with patch("vkdownloader.infrastructure.http_client.aiohttp.ClientSession") as mock_session:
            mock_session.return_value = MagicMock()
            await client.__aenter__()

            call_kwargs = mock_session.call_args[1]
            timeout = call_kwargs["timeout"]

            assert timeout.total == test_settings.download_timeout


class TestHttpClientDownloadFile:
    """Tests for HttpClient file download functionality."""

    @pytest.mark.asyncio
    async def test_download_file_creates_parent_dirs(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test download_file creates parent directories if needed."""
        client = HttpClient(settings=test_settings)
        output_path = tmp_path / "subdir" / "video.mp4"

        mock_chunk = b"test data"

        async def async_iter() -> AsyncIterator[bytes]:
            yield mock_chunk

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"Content-Length": "8"}
        mock_response.content.iter_chunked = MagicMock(return_value=async_iter())

        mock_context_response = AsyncMock()
        mock_context_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_context_response)
        client._session = mock_session

        await client.download_file("https://example.com/video.mp4", output_path)

        assert output_path.parent.exists()

    @pytest.mark.asyncio
    async def test_download_file_progress_callback(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test download_file invokes progress callback."""
        client = HttpClient(settings=test_settings)
        output_path = tmp_path / "video.mp4"
        progress_values: list[tuple[int, int]] = []

        def progress_callback(downloaded: int, total: int) -> None:
            progress_values.append((downloaded, total))

        mock_chunk = b"test"

        async def async_iter() -> AsyncIterator[bytes]:
            yield mock_chunk

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {"Content-Length": "4"}
        mock_response.content.iter_chunked = MagicMock(return_value=async_iter())

        mock_context_response = AsyncMock()
        mock_context_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_context_response)
        client._session = mock_session

        await client.download_file("https://example.com/video.mp4", output_path, progress_callback)

        assert len(progress_values) > 0

    @pytest.mark.asyncio
    async def test_download_file_cleans_up_on_error(self, test_settings: Settings, tmp_path: Path) -> None:
        """Test download_file removes partial file on error."""
        client = HttpClient(settings=test_settings)
        output_path = tmp_path / "video.mp4"

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientError("Connection failed"))
        mock_response.headers = {}
        mock_response.content = MagicMock()

        mock_context_response = AsyncMock()
        mock_context_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_context_response)
        client._session = mock_session

        with pytest.raises(DownloadError):
            await client.download_file("https://example.com/video.mp4", output_path)

        assert not output_path.exists()
