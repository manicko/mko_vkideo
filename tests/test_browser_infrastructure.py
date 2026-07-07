"""Tests for browser infrastructure: BrowserManager and NetworkMonitor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.infrastructure.browser import BrowserManager, create_stealth_context
from vkdownloader.infrastructure.network_monitor import NetworkMonitor


class TestBrowserManager:
    """Tests for BrowserManager class."""

    def test_browser_manager_init_with_settings(self, test_settings: Settings) -> None:
        """Test BrowserManager initializes correctly with provided settings."""
        manager = BrowserManager(settings=test_settings)

        assert manager.settings == test_settings
        assert manager.playwright is None
        assert manager.browser is None

    def test_browser_manager_init_without_settings(self) -> None:
        """Test BrowserManager initializes with default settings when not provided."""
        manager = BrowserManager()

        assert manager.settings is not None
        assert isinstance(manager.settings, Settings)

    @pytest.mark.asyncio
    async def test_browser_manager_context_entry(self, test_settings: Settings) -> None:
        """Test BrowserManager context manager enters correctly."""
        manager = BrowserManager(settings=test_settings)

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_playwright:
            mock_instance = AsyncMock()
            mock_playwright.return_value.start = AsyncMock(return_value=mock_instance)
            mock_instance.chromium.launch = AsyncMock(return_value=AsyncMock())

            result = await manager.__aenter__()
            assert result is manager
            assert manager.playwright is mock_instance

    @pytest.mark.asyncio
    async def test_browser_manager_context_exit(self, test_settings: Settings) -> None:
        """Test BrowserManager context manager exits and cleans up correctly."""
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        manager.browser = mock_browser
        manager.playwright = mock_playwright

        await manager.__aexit__(None, None, None)

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()


class TestStealthContext:
    """Tests for create_stealth_context function."""

    def test_stealth_context_creation(self, test_settings: Settings) -> None:
        """Test stealth context is created with correct parameters."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_playwright.chromium.launch_persistent_context.return_value = mock_browser

        create_stealth_context(mock_playwright, test_settings)

        mock_playwright.chromium.launch_persistent_context.assert_called_once()
        call_kwargs = mock_playwright.chromium.launch_persistent_context.call_args[1]
        assert call_kwargs["headless"] is False
        assert call_kwargs["viewport"] == {"width": 1920, "height": 1080}
        assert call_kwargs["user_agent"] == test_settings.user_agent
        assert call_kwargs["locale"] == test_settings.locale
        assert call_kwargs["timezone_id"] == test_settings.timezone

    def test_stealth_context_with_user_data_dir(self, test_settings: Settings) -> None:
        """Test stealth context with optional user data directory."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_playwright.chromium.launch_persistent_context.return_value = mock_browser

        user_data_dir = "/tmp/user_data"
        create_stealth_context(mock_playwright, test_settings, user_data_dir)

        call_kwargs = mock_playwright.chromium.launch_persistent_context.call_args[1]
        # user_data_dir is passed as keyword argument
        assert call_kwargs["user_data_dir"] == user_data_dir

    def test_stealth_context_automation_flags(self, test_settings: Settings) -> None:
        """Test stealth context includes automation-controlled disable flag."""
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_playwright.chromium.launch_persistent_context.return_value = mock_browser

        create_stealth_context(mock_playwright, test_settings)

        call_kwargs = mock_playwright.chromium.launch_persistent_context.call_args[1]
        assert "--disable-blink-features=AutomationControlled" in call_kwargs["args"]


class TestNetworkMonitor:
    """Tests for NetworkMonitor class."""

    def test_network_monitor_init(self) -> None:
        """Test NetworkMonitor initializes with empty URL list."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        assert monitor.page == mock_page
        assert monitor.m3u8_urls == []

    def test_network_monitor_m3u8_pattern(self) -> None:
        """Test M3U8_PATTERN correctly matches m3u8 URLs."""
        pattern = NetworkMonitor.M3U8_PATTERN

        assert pattern.match("https://example.com/video.m3u8")
        assert pattern.match("https://example.com/video.m3u8?token=abc")
        assert pattern.match("http://cdn.example.com/stream.m3u8")
        assert not pattern.match("https://example.com/video.mp4")

    @pytest.mark.asyncio
    async def test_network_monitor_m3u8_capture(self) -> None:
        """Test NetworkMonitor captures m3u8 URLs from responses."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://cdn.example.com/video.m3u8"

        await monitor._intercept_response(mock_response)

        assert "https://cdn.example.com/video.m3u8" in monitor.m3u8_urls

    @pytest.mark.asyncio
    async def test_network_monitor_json_url_extraction(self) -> None:
        """Test NetworkMonitor extracts m3u8 URLs from JSON responses."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/video"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(
            return_value={"url": "https://cdn.example.com/stream.m3u8", "data": "value"}
        )

        await monitor._intercept_response(mock_response)

        assert "https://cdn.example.com/stream.m3u8" in monitor.m3u8_urls

    def test_extract_urls_from_json_dict(self) -> None:
        """Test _extract_urls_from_json extracts URLs from dict data."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        data = {"stream": "https://example.com/video.m3u8", "other": "value"}
        monitor._extract_urls_from_json(data)

        assert "https://example.com/video.m3u8" in monitor.m3u8_urls

    def test_extract_urls_from_json_nested(self) -> None:
        """Test _extract_urls_from_json extracts URLs from nested structures."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        data = {
            "video": {
                "quality": [{"url": "https://example.com/720p.m3u8"}]
            }
        }
        monitor._extract_urls_from_json(data)

        assert "https://example.com/720p.m3u8" in monitor.m3u8_urls
