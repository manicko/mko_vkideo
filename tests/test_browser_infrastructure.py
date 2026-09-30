"""Tests for browser infrastructure: BrowserManager and NetworkMonitor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import ExtractionError
from vkdownloader.infrastructure.browser import BrowserManager
from vkdownloader.infrastructure.network_monitor import JsonValue, NetworkMonitor
from vkdownloader.models.enums import PlaylistType


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

    @pytest.mark.asyncio
    async def test_browser_manager_context_exit_stops_playwright_on_browser_close_error(
        self, test_settings: Settings
    ) -> None:
        """Test playwright.stop() is called even when browser.close() raises."""
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock(side_effect=RuntimeError("close failed"))
        mock_playwright = AsyncMock()
        manager.browser = mock_browser
        manager.playwright = mock_playwright

        # __aexit__ guarantees playwright.stop() runs via try/finally,
        # but does not suppress the browser.close() exception
        with pytest.raises(RuntimeError, match="close failed"):
            await manager.__aexit__(None, None, None)

        mock_browser.close.assert_called_once()
        # playwright.stop() must still run despite browser.close() raising
        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_manager_launch_failure_raises_extraction_error(
        self, test_settings: Settings
    ) -> None:
        """Test that browser launch failure is wrapped in ExtractionError."""
        manager = BrowserManager(settings=test_settings)

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_playwright:
            mock_instance = AsyncMock()
            mock_playwright.return_value.start = AsyncMock(return_value=mock_instance)
            mock_instance.chromium.launch = AsyncMock(side_effect=RuntimeError("launch failed"))
            mock_instance.stop = AsyncMock()

            with pytest.raises(ExtractionError, match="Failed to launch browser"):
                await manager.__aenter__()

            # playwright.stop() should be called during cleanup
            mock_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_manager_context_exit_handles_close_timeout(
        self, test_settings: Settings
    ) -> None:
        """INT-004: browser.close() timeout is caught and logged, playwright.stop() still runs."""
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()

        # Make browser.close() hang by sleeping longer than the timeout
        async def hanging_close() -> None:
            await asyncio.sleep(100)

        mock_browser.close = hanging_close
        mock_playwright = AsyncMock()
        manager.browser = mock_browser
        manager.playwright = mock_playwright

        await manager.__aexit__(None, None, None)

        # playwright.stop() must still run despite browser.close() timing out
        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_manager_context_exit_handles_playwright_stop_timeout(
        self, test_settings: Settings
    ) -> None:
        """INT-004: playwright.stop() timeout is caught and logged."""
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()
        manager.browser = mock_browser
        mock_playwright = AsyncMock()

        async def hanging_stop() -> None:
            await asyncio.sleep(100)

        mock_playwright.stop = hanging_stop

        # Should not raise; timeout is caught and logged as warning
        await manager.__aexit__(None, None, None)
        mock_browser.close.assert_called_once()


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
        mock_response.body = AsyncMock(
            return_value=b'{"url": "https://cdn.example.com/stream.m3u8", "data": "value"}'
        )

        await monitor._intercept_response(mock_response)

        assert "https://cdn.example.com/stream.m3u8" in monitor.m3u8_urls

    def test_extract_urls_from_json_dict(self) -> None:
        """Test _extract_urls_from_json extracts URLs from dict data."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        data: JsonValue = {"stream": "https://example.com/video.m3u8", "other": "value"}
        monitor._extract_urls_from_json(data)

        assert "https://example.com/video.m3u8" in monitor.m3u8_urls

    def test_extract_urls_from_json_nested(self) -> None:
        """Test _extract_urls_from_json extracts URLs from nested structures."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        data: JsonValue = {"video": {"quality": [{"url": "https://example.com/720p.m3u8"}]}}
        monitor._extract_urls_from_json(data)

        assert "https://example.com/720p.m3u8" in monitor.m3u8_urls

    @pytest.mark.asyncio
    async def test_network_monitor_json_decode_error_graceful(self) -> None:
        """Test NetworkMonitor handles JSONDecodeError gracefully without crashing."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/video"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.body = AsyncMock(return_value=b"invalid json data")

        # Should not raise - exception handled gracefully
        await monitor._intercept_response(mock_response)
        # No URL should be extracted (invalid JSON)
        assert len(monitor.m3u8_urls) == 0

    @pytest.mark.asyncio
    async def test_network_monitor_error_graceful(self) -> None:
        """Test NetworkMonitor handles other errors gracefully without crashing."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/video"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.body = AsyncMock(side_effect=RuntimeError("network error"))

        # Should not raise - exception handled gracefully
        await monitor._intercept_response(mock_response)
        # No URL should be extracted (error)
        assert len(monitor.m3u8_urls) == 0

    @pytest.mark.asyncio
    async def test_network_monitor_skips_oversized_body_without_content_length(self) -> None:
        """Test NetworkMonitor skips JSON parsing when body exceeds cap and Content-Length is absent."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/video"
        mock_response.headers = {"content-type": "application/json"}
        # No content-length header; body exceeds the 1 MB cap
        mock_response.body = AsyncMock(return_value=b"x" * 1_000_000)

        await monitor._intercept_response(mock_response)

        # No URL should be extracted (body too large)
        assert len(monitor.m3u8_urls) == 0

    @pytest.mark.parametrize(
        ("address_form", "expected"),
        [
            pytest.param(
                "https://cdn.example/a/stream.m3u8",
                "https://cdn.example/a/stream.m3u8",
                id="absolute-https",
            ),
            pytest.param(
                "http://cdn.example/a/stream.m3u8",
                None,
                id="absolute-http",
            ),
            pytest.param(
                "http://cdn.example/a/stream.m3u8?sig=X",
                None,
                id="absolute-http-with-query",
            ),
            pytest.param(
                "//cdn.example/a/stream.m3u8",
                "https://cdn.example/a/stream.m3u8",
                id="scheme-relative",
            ),
            pytest.param(
                "/a/stream.m3u8",
                None,
                id="root-relative",
            ),
            pytest.param(
                "cdn.example/a/stream.m3u8",
                "https://cdn.example/a/stream.m3u8",
                id="bare-host",
            ),
            pytest.param(
                "a/stream.m3u8",
                None,
                id="bare-relative",
            ),
            pytest.param(
                "stream.m3u8",
                None,
                id="bare-filename",
            ),
            pytest.param(
                "  https://cdn.example/a/stream.m3u8  ",
                "https://cdn.example/a/stream.m3u8",
                id="whitespace-padded",
            ),
        ],
    )
    def test_normalize_url_address_forms(self, address_form: str, expected: str | None) -> None:
        """NET-016: the nine address forms produce the expected classification.

        Five forms are dropped (return None exactly); four are kept or
        promoted to https.  Scheme-relative is evaluated before root-relative
        so the former is promoted, not swallowed and dropped.
        """
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        result = monitor._normalize_url(address_form)

        if expected is None:
            assert result is None
        else:
            assert result == expected

    def test_extract_urls_from_json_drops_unresolvable_value(self) -> None:
        """NET-016: a JSON value of 720/stream.m3u8 is not appended to the discovered set."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        data: JsonValue = {"hls": "720/stream.m3u8"}
        monitor._extract_urls_from_json(data)

        assert monitor.m3u8_urls == []

    def test_extract_urls_from_json_keeps_resolvable_value_in_mixed_payload(self) -> None:
        """NET-016: a resolvable https value in a mixed payload is the only address kept."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        data: JsonValue = {
            "drop_me": "720/stream.m3u8",
            "keep_me": "https://cdn.example.com/stream.m3u8",
        }
        monitor._extract_urls_from_json(data)

        assert monitor.m3u8_urls == ["https://cdn.example.com/stream.m3u8"]

    @pytest.mark.asyncio
    async def test_intercept_response_drops_plaintext_m3u8_address(self) -> None:
        """NET-016: an http:// response URL yields no captured address.

        Green counterpart: test_network_monitor_m3u8_capture asserts an
        https:// address is still captured, so the m3u8 branch is narrowed,
        not broken.
        """
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "http://cdn.example.com/stream.m3u8"

        await monitor._intercept_response(mock_response)

        assert monitor.m3u8_urls == []

    # --- B7: HLS filter, safety suspension, and select() ---

    def test_select_empty_returns_empty_list(self) -> None:
        """select() returns an empty list when no addresses were captured."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        result = monitor.select()

        assert result == []

    def test_select_filters_to_hls_only(self) -> None:
        """NET-008: select() keeps only addresses whose path suffix is .m3u8.

        An address with .m3u8 appearing only in a directory name (not as the
        path suffix) is rejected by the HLS filter.
        """
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.example.com/stream.m3u8",
            "https://cdn.example.com/data.m3u8/playlist",
        ]

        result = monitor.select()

        assert result == ["https://cdn.example.com/stream.m3u8"]

    def test_select_suspends_filter_when_all_non_hls(self) -> None:
        """NET-008: safety suspension returns the unconstrained set when the
        HLS filter would reject every captured address."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn1.example.com/data.m3u8/playlist",
            "https://cdn2.example.com/m3u8dir/index",
        ]

        result = monitor.select()

        # Filter suspended: unconstrained set is returned
        assert result == monitor.m3u8_urls
        assert monitor._hls_filter_suspended_logged is True

    def test_select_suspension_logs_once(self) -> None:
        """NET-008: the suspension warning is emitted at most once."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.example.com/data.m3u8/playlist",
        ]

        monitor.select()
        assert monitor._hls_filter_suspended_logged is True

        # Reset and confirm no double-log
        monitor._hls_filter_suspended_logged = False
        monitor.select()
        assert monitor._hls_filter_suspended_logged is True

    def test_select_never_raises_on_empty(self) -> None:
        """B7 exception totality: select() on empty captures returns [] without raising."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        result = monitor.select()

        assert result == []

    def test_select_never_raises_with_mixed_validity(self) -> None:
        """B7 exception totality: select() does not raise on any address set."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.example.com/stream.m3u8",
            "://malformed",
        ]

        result = monitor.select()

        # The valid HLS URL is retained; malformed is rejected by _classify_hls.
        assert "https://cdn.example.com/stream.m3u8" in result

    def test_classify_hls_matches_path_suffix_only(self) -> None:
        """NET-008: _classify_hls agrees with extractor._classify_format logic."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)

        assert monitor._classify_hls("https://cdn.example.com/stream.m3u8") is True
        assert monitor._classify_hls("https://cdn.example.com/master.m3u8?token=abc") is True
        assert monitor._classify_hls("https://cdn.example.com/data.m3u8/playlist") is False

    @pytest.mark.asyncio
    async def test_intercept_response_captures_mixed_hosts(self) -> None:
        """NET-008: the real monitor captures m3u8 URLs from multiple hosts."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response_1 = MagicMock()
        mock_response_1.url = "https://cdn1.example.com/stream.m3u8"

        mock_response_2 = MagicMock()
        mock_response_2.url = "https://cdn2.example.com/master.m3u8?token=abc"

        await monitor._intercept_response(mock_response_1)
        await monitor._intercept_response(mock_response_2)

        assert "https://cdn1.example.com/stream.m3u8" in monitor.m3u8_urls
        assert "https://cdn2.example.com/master.m3u8?token=abc" in monitor.m3u8_urls

    @pytest.mark.asyncio
    async def test_intercept_response_classifies_master_playlist(self) -> None:
        """B7: a body containing #EXT-X-STREAM-INF is classified as MASTER."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://cdn.example.com/master.m3u8"
        mock_response.body = AsyncMock(return_value=b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1234\n")

        await monitor._intercept_response(mock_response)

        assert "https://cdn.example.com/master.m3u8" in monitor.m3u8_urls
        assert monitor._playlist_types["https://cdn.example.com/master.m3u8"] == PlaylistType.MASTER

    @pytest.mark.asyncio
    async def test_intercept_response_classifies_media_playlist(self) -> None:
        """B7: a body containing #EXT-X-PLAYLIST-TYPE is classified as MEDIA."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://cdn.example.com/media.m3u8"
        mock_response.body = AsyncMock(
            return_value=b"#EXTM3U\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-TARGETDURATION:10\n"
        )

        await monitor._intercept_response(mock_response)

        assert monitor._playlist_types["https://cdn.example.com/media.m3u8"] == PlaylistType.MEDIA

    @pytest.mark.asyncio
    async def test_intercept_response_classifies_unclassified_playlist(self) -> None:
        """B7: a body with neither master nor media tags is UNCLASSIFIED."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://cdn.example.com/unknown.m3u8"
        mock_response.body = AsyncMock(return_value=b"#EXTM3U\n#EXT-X-TARGETDURATION:10\n")

        await monitor._intercept_response(mock_response)

        assert (
            monitor._playlist_types["https://cdn.example.com/unknown.m3u8"]
            == PlaylistType.UNCLASSIFIED
        )

    def test_select_sorts_master_first(self) -> None:
        """B7: select() ranks master playlists ahead of unclassified and media."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.example.com/media.m3u8",
            "https://cdn.example.com/master.m3u8",
            "https://cdn.example.com/plain.m3u8",
        ]
        monitor._playlist_types = {
            "https://cdn.example.com/media.m3u8": PlaylistType.MEDIA,
            "https://cdn.example.com/master.m3u8": PlaylistType.MASTER,
            "https://cdn.example.com/plain.m3u8": PlaylistType.UNCLASSIFIED,
        }

        result = monitor.select()

        assert result[0] == "https://cdn.example.com/master.m3u8"
        assert result[-1] == "https://cdn.example.com/media.m3u8"

    def test_select_returns_all_when_no_suspension_and_all_hls(self) -> None:
        """select() with all HLS addresses returns them all, ranked."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn1.example.com/a.m3u8",
            "https://cdn2.example.com/b.m3u8",
        ]

        result = monitor.select()

        assert result == ["https://cdn1.example.com/a.m3u8", "https://cdn2.example.com/b.m3u8"]
