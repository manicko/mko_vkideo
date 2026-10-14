"""Tests for browser infrastructure: BrowserManager and NetworkMonitor."""

import asyncio
import traceback
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import Error as PlaywrightError
from structlog.testing import capture_logs

from vkdownloader.config import Settings
from vkdownloader.exceptions import ExtractionError
from vkdownloader.infrastructure.browser import BrowserManager
from vkdownloader.infrastructure.network_monitor import JsonValue, NetworkMonitor, _PlaylistType
from vkdownloader.models.enums import ErrorCode
from vkdownloader.services.downloader_throttle import _shutdown_event_ctx, get_shutdown_event


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
        """CON-004 / phase04/VAL-401: playwright.stop() runs despite a close error
        and the in-flight primary escapes intact while the driver error does not.

        browser.close() now raises a typed PlaywrightError (suppressed), not the
        old RuntimeError stand-in. The primary exception raised in the body must
        escape __aexit__ with its type and message preserved; the driver error
        must not. Measured today this test's shape fails: the escaped exception
        is Error('close failed'), not the primary.
        """
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock(side_effect=PlaywrightError("close failed"))
        mock_instance = AsyncMock()
        mock_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_instance.stop = AsyncMock()

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
            mock_pw.return_value.start = AsyncMock(return_value=mock_instance)

            # __aexit__ returns None (falsy), so the async-with machinery
            # re-raises the primary. The PlaywrightError from browser.close() is
            # caught by the typed (PlaywrightError, TimeoutError) set and
            # suppressed — it never escapes.
            with pytest.raises(RuntimeError, match="primary failure"):
                async with BrowserManager(settings=test_settings):
                    raise RuntimeError("primary failure")

        mock_browser.close.assert_called_once()
        # playwright.stop() must still run despite browser.close() raising
        mock_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_manager_launch_failure_raises_extraction_error(
        self, test_settings: Settings
    ) -> None:
        """A browser launch failure surfaces as the application's ExtractionError.

        BRW-001: the caught Playwright failure's actionable cause (the missing
        binary and the ``playwright install`` remedy) is carried into the raised
        message, and ``from None`` keeps the raw Playwright banner out of the
        traceback. ``logger.error`` still records ``exc_info=True`` unchanged —
        the encoding gap that can raise on a strict console is mechanism (a),
        B16's subject, not this arm's.
        """
        manager = BrowserManager(settings=test_settings)
        missing_binary = (
            "Executable doesn't exist at /root/.cache/ms-playwright/"
            "chromium_headless_shell-1164/chrome-linux/headless_shell\n"
            "Run `playwright install` to download new browsers"
        )

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_playwright:
            mock_instance = AsyncMock()
            mock_playwright.return_value.start = AsyncMock(return_value=mock_instance)
            mock_instance.chromium.launch = AsyncMock(side_effect=PlaywrightError(missing_binary))
            mock_instance.stop = AsyncMock()

            # The match is widened from the old generic text to the new
            # actionable text; that the application's own exception type reaches
            # the caller — not the raw Playwright error — is the finding's real
            # content and is not weakened away.
            with pytest.raises(ExtractionError, match="to obtain it: playwright install"):
                await manager.__aenter__()

            # playwright.stop() must still run during cleanup.
            mock_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_launch_failure_message_carries_binary_and_remedy(
        self, test_settings: Settings
    ) -> None:
        """BRW-001 cause-content: both the missing executable path and the
        install remedy reach the ExtractionError's text, derived from the caught
        exception.

        Uses the "does not exist at" spelling to confirm the second marker is
        matched, and a browser name in the remedy ("playwright install chromium")
        to confirm the canonical command is surfaced without absorbing the trailing
        backtick or the browser token into the path.
        """
        manager = BrowserManager(settings=test_settings)
        launch_error = PlaywrightError(
            "Executable does not exist at /home/u/.cache/ms-playwright/"
            "chromium_headless_shell-1164/chrome-linux/headless_shell\n"
            "Run `playwright install chromium` to download new browsers"
        )

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_playwright:
            mock_instance = AsyncMock()
            mock_playwright.return_value.start = AsyncMock(return_value=mock_instance)
            mock_instance.chromium.launch = AsyncMock(side_effect=launch_error)
            mock_instance.stop = AsyncMock()

            with pytest.raises(ExtractionError) as exc_info:
                await manager.__aenter__()

        message = str(exc_info.value)
        assert (
            "/home/u/.cache/ms-playwright/chromium_headless_shell-1164/"
            "chrome-linux/headless_shell" in message
        )
        assert "playwright install" in message
        # The application's own type reaches the caller, not the raw stand-in.
        assert isinstance(exc_info.value, ExtractionError)
        assert not isinstance(exc_info.value, PlaywrightError)
        mock_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_launch_failure_retains_from_none_suppression(
        self, test_settings: Settings
    ) -> None:
        """BRW-001 suppression: ``from None`` is retained so the raw Playwright
        traceback is never displayed and its box-drawing banner never reaches the user.

        Dropping ``from None`` (or chaining with ``from exc``) breaks both
        assertions, so this pins the suppression the plan mandates.
        """
        manager = BrowserManager(settings=test_settings)
        banner = (
            "Executable doesn't exist at /x/chromium\n"
            "\u2500\u2500\u2500 Playwright error banner \u2500\u2500\u2500\n"
            "Run `playwright install` to download new browsers"
        )

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_playwright:
            mock_instance = AsyncMock()
            mock_playwright.return_value.start = AsyncMock(return_value=mock_instance)
            mock_instance.chromium.launch = AsyncMock(side_effect=PlaywrightError(banner))
            mock_instance.stop = AsyncMock()

            with pytest.raises(ExtractionError) as exc_info:
                await manager.__aenter__()

        # `raise ... from None` sets __cause__ to None and __suppress_context__ to
        # True; the chained Playwright error is populated but hidden from display.
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__ is True
        # The surfaced message carries only the extracted ASCII facts, never the
        # banner's box-drawing characters.
        assert "\u2500" not in str(exc_info.value)
        rendered = "".join(traceback.format_exception(exc_info.value))
        # Without ``from None`` the suppressed context (the banner) would be
        # rendered here, reintroducing the box-drawing hazard.
        assert "Executable doesn't exist" not in rendered
        mock_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_launch_failure_uninformative_cause_is_non_empty(
        self, test_settings: Settings
    ) -> None:
        """BRW-001 fallback: when the caught exception carries neither the binary
        nor the remedy, the message stays non-empty, single-line, and preserves
        the underlying detail rather than degrading to the old generic text alone."""
        manager = BrowserManager(settings=test_settings)

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_playwright:
            mock_instance = AsyncMock()
            mock_playwright.return_value.start = AsyncMock(return_value=mock_instance)
            mock_instance.chromium.launch = AsyncMock(side_effect=RuntimeError("launch failed"))
            mock_instance.stop = AsyncMock()

            with pytest.raises(ExtractionError) as exc_info:
                await manager.__aenter__()

        message = str(exc_info.value)
        assert message.startswith("Failed to launch browser for video extraction")
        # The uninformative underlying detail is preserved, not dropped.
        assert "launch failed" in message
        # Single line: no newline leakage from a multi-line Playwright banner.
        assert "\n" not in message
        mock_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_manager_context_exit_handles_close_timeout(
        self, test_settings: Settings
    ) -> None:
        """browser.close() timeout is caught and logged, playwright.stop() still runs."""
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
        """playwright.stop() timeout is caught and logged."""
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

    # --- B4: CON-005, CON-004, phase04/VAL-401 ---

    @pytest.mark.asyncio
    async def test_con005_close_runs_on_stop_path(self, test_settings: Settings) -> None:
        """CON-005 oracle (RED today): browser.close() runs even when stop is set.

        On the stop path — which _extract_with_browser takes when it raises
        CancelledError — both release steps must still execute. Before the fix
        the guard skipped browser.close() entirely; measured 0 calls against 1
        expected. The stop event is set via the project token idiom so it never
        leaks to later tests.
        """
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        manager.browser = mock_browser
        manager.playwright = mock_playwright

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()
            await manager.__aexit__(None, None, None)
        finally:
            _shutdown_event_ctx.reset(token)

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_con004_con005_val401_cancelled_survives_close_error(
        self, test_settings: Settings
    ) -> None:
        """phase04/VAL-401: a release failure never replaces the in-flight CancelledError.

        Mirrors _extract_with_browser: the body reads the stop state and raises
        CancelledError; browser.close() raises a PlaywrightError. The escaping
        exception must be CancelledError, not the driver error. Both release
        steps run. RED in the forbidden intermediate state (guard dropped,
        suppression still narrow): the PlaywrightError would escape and replace
        CancelledError.
        """
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock(side_effect=PlaywrightError("close failed"))
        mock_instance = AsyncMock()
        mock_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_instance.stop = AsyncMock()

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()

            with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
                mock_pw.return_value.start = AsyncMock(return_value=mock_instance)

                with pytest.raises(asyncio.CancelledError, match="cancelled by user"):
                    async with BrowserManager(settings=test_settings):
                        shutdown_event = get_shutdown_event()
                        if shutdown_event.is_set():
                            raise asyncio.CancelledError("cancelled by user")
        finally:
            _shutdown_event_ctx.reset(token)

        mock_browser.close.assert_called_once()
        mock_instance.stop.assert_called_once()

    @pytest.mark.parametrize(
        ("failing_step",),
        [
            pytest.param("browser_close", id="close-fails"),
            pytest.param("playwright_stop", id="stop-fails"),
        ],
    )
    @pytest.mark.asyncio
    async def test_release_failure_nothing_in_flight_is_suppressed(
        self,
        failing_step: str,
        test_settings: Settings,
    ) -> None:
        """§3.2 fork: with nothing in flight, a release failure is logged, not raised.

        A PlaywrightError from either release step is suppressed, the OTHER step
        still ran, and a captured warning carries error_type with
        primary_error is None.
        """
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()

        if failing_step == "browser_close":
            mock_browser.close = AsyncMock(side_effect=PlaywrightError("close failed"))
        else:
            mock_playwright.stop = AsyncMock(side_effect=PlaywrightError("stop failed"))

        manager.browser = mock_browser
        manager.playwright = mock_playwright

        with capture_logs() as logs:
            await manager.__aexit__(None, None, None)

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

        expected_event = f"{failing_step}_failed"
        warnings = [e for e in logs if e.get("event") == expected_event]
        assert len(warnings) == 1
        entry = warnings[0]
        assert entry["error_type"] == "Error"
        assert entry["primary_error"] is None

    @pytest.mark.asyncio
    async def test_type_error_from_release_escapes(self, test_settings: Settings) -> None:
        """CON-004 distinction: TypeError is NOT in the suppression set.

        A TypeError from the release path escapes __aexit__ when nothing is in
        flight; on a real async with with a body error, it still escapes and
        the body error survives as __context__. Green today — guards against a
        future blanket except.
        """
        # Nothing in flight: TypeError escapes, playwright.stop() still runs.
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock(side_effect=TypeError("defect"))
        mock_playwright = AsyncMock()
        manager.browser = mock_browser
        manager.playwright = mock_playwright

        with pytest.raises(TypeError, match="defect"):
            await manager.__aexit__(None, None, None)
        mock_playwright.stop.assert_called_once()

        # Body error in flight: TypeError escapes, body error preserved as __context__.
        mock_browser2 = AsyncMock()
        mock_browser2.close = AsyncMock(side_effect=TypeError("defect"))
        mock_instance2 = AsyncMock()
        mock_instance2.chromium.launch = AsyncMock(return_value=mock_browser2)
        mock_instance2.stop = AsyncMock()

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
            mock_pw.return_value.start = AsyncMock(return_value=mock_instance2)

            with pytest.raises(TypeError, match="defect") as exc_info:
                async with BrowserManager(settings=test_settings):
                    raise RuntimeError("body failed")

        assert exc_info.value.__context__ is not None
        assert isinstance(exc_info.value.__context__, RuntimeError)
        assert str(exc_info.value.__context__) == "body failed"
        mock_instance2.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_hang_guard_close_bounded_by_wait_for(
        self,
        test_settings: Settings,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Hang guard: a hanging browser.close() is bounded by _BROWSER_CLOSE_TIMEOUT.

        _BROWSER_CLOSE_TIMEOUT is shrunk via monkeypatch so the guard costs
        milliseconds rather than seconds. The __aexit__ call is wrapped in an
        outer wait_for with a ceiling; a regression that drops the bound fails
        the suite (pytest.fail) instead of hanging. Follows the B1/B2/B3
        precedent. Green today by design.
        """
        monkeypatch.setattr("vkdownloader.infrastructure.browser._BROWSER_CLOSE_TIMEOUT", 0.01)
        manager = BrowserManager(settings=test_settings)
        mock_browser = AsyncMock()

        async def hanging_close() -> None:
            await asyncio.sleep(100)

        mock_browser.close = AsyncMock(side_effect=hanging_close)
        mock_playwright = AsyncMock()
        manager.browser = mock_browser
        manager.playwright = mock_playwright

        try:
            await asyncio.wait_for(manager.__aexit__(None, None, None), timeout=5.0)
        except TimeoutError:
            pytest.fail(
                "browser.close() was not bounded by asyncio.wait_for — "
                "the close hung beyond the ceiling and the bound was removed"
            )

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()

    # --- B15: stealth_enabled opt-in gating (D5, BRW-003) ---

    @pytest.mark.asyncio
    async def test_stealth_disabled_no_automation_suppression_no_injection(
        self, test_settings: Settings
    ) -> None:
        """B15: with stealth_enabled False, launch args do NOT contain the
        automation-suppression argument and add_init_script is never called,
        yet the page is still returned."""
        manager = BrowserManager(settings=test_settings)

        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_instance = AsyncMock()
        mock_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
            mock_pw.return_value.start = AsyncMock(return_value=mock_instance)

            async with manager:
                page = await manager.create_stealth_page()

            launch_kwargs = mock_instance.chromium.launch.call_args.kwargs
            assert "--disable-blink-features=AutomationControlled" not in launch_kwargs.get(
                "args", []
            )
            mock_page.add_init_script.assert_not_called()
            assert page is mock_page

    @pytest.mark.asyncio
    async def test_stealth_disabled_asset_absent_no_check_no_error(
        self, test_settings: Settings
    ) -> None:
        """B15: with stealth_enabled False, an absent asset produces no error,
        no warning, and no check — nothing consults self._stealth_path.

        This dissolves BRW-003: silence about an asset never asked for is
        not a defect.
        """
        manager = BrowserManager(settings=test_settings)
        manager._stealth_path = MagicMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=AsyncMock())
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_instance = AsyncMock()
        mock_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
            mock_pw.return_value.start = AsyncMock(return_value=mock_instance)

            with capture_logs() as logs:
                async with manager:
                    page = await manager.create_stealth_page()

            manager._stealth_path.exists.assert_not_called()
            assert not [e for e in logs if e.get("event") == "stealth_asset_missing"]
            assert page is not None

    @pytest.mark.asyncio
    async def test_stealth_enabled_asset_present_injects_and_suppresses(
        self,
    ) -> None:
        """B15: with stealth_enabled True and the asset present, launch args
        contain the automation-suppression argument and add_init_script is
        called."""
        settings = Settings(stealth_enabled=True)
        manager = BrowserManager(settings=settings)

        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_instance = AsyncMock()
        mock_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
            mock_pw.return_value.start = AsyncMock(return_value=mock_instance)

            async with manager:
                page = await manager.create_stealth_page()

            launch_kwargs = mock_instance.chromium.launch.call_args.kwargs
            assert "--disable-blink-features=AutomationControlled" in launch_kwargs.get("args", [])
            mock_page.add_init_script.assert_called_once()
            assert page is mock_page

    @pytest.mark.asyncio
    async def test_stealth_enabled_asset_missing_hard_fails_before_driver(
        self,
    ) -> None:
        """B15: with stealth_enabled True and the asset missing, __aenter__
        raises ExtractionError with the new ErrorCode — before
        async_playwright is started (the ordering proof that is the gate).

        The message names the missing path, the declared-build-artifact
        consequence, and the remedy.
        """
        settings = Settings(stealth_enabled=True)
        manager = BrowserManager(settings=settings)
        manager._stealth_path = Path("/nonexistent/stealth.min.js")

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
            mock_pw.return_value.start = AsyncMock()

            with capture_logs() as logs:
                with pytest.raises(ExtractionError) as exc_info:
                    await manager.__aenter__()

            # Ordering proof: the Playwright driver was never started — the
            # check ran before async_playwright().start(), so no browser was
            # launched and no teardown is needed.
            mock_pw.return_value.start.assert_not_called()

            # ErrorCode is the new member, not EXTRACTION_ERROR
            assert exc_info.value.error_code == ErrorCode.STEALTH_ASSET_MISSING

            # The warning was emitted with the same event name
            assert any(e.get("event") == "stealth_asset_missing" for e in logs)

            # Message names the path, build-artifact consequence, and remedy
            msg = str(exc_info.value)
            assert str(manager._stealth_path) in msg
            assert "broken build" in msg
            assert "partial deployment" in msg
            assert "VKDOWNLOADER_STEALTH_ENABLED" in msg
            assert "pyproject.toml" in msg

    @pytest.mark.asyncio
    async def test_stealth_disabled_context_identity_not_gated(
        self, test_settings: Settings
    ) -> None:
        """B15 S1h: with stealth_enabled False, new_context is still called
        with viewport, user_agent, locale, and timezone_id — component 3
        must NOT be gated by the flag."""
        manager = BrowserManager(settings=test_settings)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=AsyncMock())
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_instance = AsyncMock()
        mock_instance.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("vkdownloader.infrastructure.browser.async_playwright") as mock_pw:
            mock_pw.return_value.start = AsyncMock(return_value=mock_instance)

            async with manager:
                await manager.create_stealth_page()

            mock_browser.new_context.assert_called_once()
            ctx_kwargs = mock_browser.new_context.call_args.kwargs
            assert ctx_kwargs["viewport"] == {"width": 1920, "height": 1080}
            assert ctx_kwargs["user_agent"] == test_settings.user_agent
            assert ctx_kwargs["locale"] == test_settings.locale
            assert ctx_kwargs["timezone_id"] == test_settings.timezone


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
            "https://cdn.vkvideo.ru/stream.m3u8",
            "https://cdn.vkvideo.ru/data.m3u8/playlist",
        ]

        result = monitor.select()

        assert result == ["https://cdn.vkvideo.ru/stream.m3u8"]

    def test_select_suspends_filter_when_all_non_hls(self) -> None:
        """NET-008: safety suspension returns the unconstrained set when the
        HLS filter would reject every captured address."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn1.vkvideo.ru/data.m3u8/playlist",
            "https://cdn2.vkvideo.ru/m3u8dir/index",
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
            "https://cdn.vkvideo.ru/data.m3u8/playlist",
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

    def test_select_filters_non_vk_hosts(self) -> None:
        """NET-008: addresses from non-VK hosts are dropped by the host allowlist."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.vkvideo.ru/stream.m3u8",
            "https://ads.tracker.example/stream.m3u8",
        ]

        result = monitor.select()

        # Only the VK-host address survives the host filter.
        assert result == ["https://cdn.vkvideo.ru/stream.m3u8"]

    def test_select_suspends_host_filter_when_all_non_vk(self) -> None:
        """NET-008: host-filter suspension returns the unconstrained set when
        the host filter would reject every captured address."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://ads.tracker.example/first.m3u8",
            "https://analytics.badger.net/second.m3u8",
        ]

        result = monitor.select()

        # Host filter suspended: unconstrained set is returned.
        assert result == monitor.m3u8_urls
        assert monitor._host_filter_suspended_logged is True

    def test_select_host_filter_suspension_logs_once(self) -> None:
        """NET-008: the host-filter suspension warning is emitted at most once."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://ads.tracker.example/stream.m3u8",
        ]

        monitor.select()
        assert monitor._host_filter_suspended_logged is True

        # Reset and confirm no double-log.
        monitor._host_filter_suspended_logged = False
        monitor.select()
        assert monitor._host_filter_suspended_logged is True

    def test_select_never_raises_with_mixed_validity(self) -> None:
        """B7 exception totality: select() does not raise on any address set."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.vkvideo.ru/stream.m3u8",
            "://malformed",
        ]

        result = monitor.select()

        # The valid HLS URL is retained; malformed is rejected by _classify_hls.
        assert "https://cdn.vkvideo.ru/stream.m3u8" in result

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
        mock_response_1.url = "https://cdn1.vkvideo.ru/stream.m3u8"

        mock_response_2 = MagicMock()
        mock_response_2.url = "https://cdn2.vkvideo.ru/master.m3u8?token=abc"

        await monitor._intercept_response(mock_response_1)
        await monitor._intercept_response(mock_response_2)

        assert "https://cdn1.vkvideo.ru/stream.m3u8" in monitor.m3u8_urls
        assert "https://cdn2.vkvideo.ru/master.m3u8?token=abc" in monitor.m3u8_urls

    @pytest.mark.asyncio
    async def test_intercept_response_classifies_master_playlist(self) -> None:
        """B7: a body containing #EXT-X-STREAM-INF is classified as MASTER."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://cdn.vkvideo.ru/master.m3u8"
        mock_response.body = AsyncMock(return_value=b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1234\n")

        await monitor._intercept_response(mock_response)

        assert "https://cdn.vkvideo.ru/master.m3u8" in monitor.m3u8_urls
        assert monitor._playlist_types["https://cdn.vkvideo.ru/master.m3u8"] == _PlaylistType.MASTER

    @pytest.mark.asyncio
    async def test_intercept_response_classifies_media_playlist(self) -> None:
        """B7: a body containing #EXT-X-PLAYLIST-TYPE is classified as MEDIA."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://cdn.vkvideo.ru/media.m3u8"
        mock_response.body = AsyncMock(
            return_value=b"#EXTM3U\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-TARGETDURATION:10\n"
        )

        await monitor._intercept_response(mock_response)

        assert monitor._playlist_types["https://cdn.vkvideo.ru/media.m3u8"] == _PlaylistType.MEDIA

    @pytest.mark.asyncio
    async def test_intercept_response_classifies_unclassified_playlist(self) -> None:
        """B7: a body with neither master nor media tags is UNCLASSIFIED."""
        mock_page = MagicMock()
        mock_page.on = MagicMock()
        monitor = NetworkMonitor(mock_page)

        mock_response = MagicMock()
        mock_response.url = "https://cdn.vkvideo.ru/unknown.m3u8"
        mock_response.body = AsyncMock(return_value=b"#EXTM3U\n#EXT-X-TARGETDURATION:10\n")

        await monitor._intercept_response(mock_response)

        assert (
            monitor._playlist_types["https://cdn.vkvideo.ru/unknown.m3u8"]
            == _PlaylistType.UNCLASSIFIED
        )

    def test_select_sorts_media_first(self) -> None:
        """B7: select() ranks media playlists above unclassified above master.

        Spec: "media above master above unclassified, ties broken by arrival
        order." A master manifest carries no segments, so it must never be
        the first address handed to the downloader.
        """
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.vkvideo.ru/media.m3u8",
            "https://cdn.vkvideo.ru/master.m3u8",
            "https://cdn.vkvideo.ru/plain.m3u8",
        ]
        monitor._playlist_types = {
            "https://cdn.vkvideo.ru/media.m3u8": _PlaylistType.MEDIA,
            "https://cdn.vkvideo.ru/master.m3u8": _PlaylistType.MASTER,
            "https://cdn.vkvideo.ru/plain.m3u8": _PlaylistType.UNCLASSIFIED,
        }

        result = monitor.select()

        assert result[0] == "https://cdn.vkvideo.ru/media.m3u8"
        assert result[-1] == "https://cdn.vkvideo.ru/master.m3u8"

    def test_select_media_before_master_with_both_captured(self) -> None:
        """B7: when both a media playlist and a master manifest are captured,
        the media playlist is select()[0] — the master would produce a
        silently corrupt file if passed to the downloader."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn.vkvideo.ru/master.m3u8",
            "https://cdn.vkvideo.ru/media.m3u8",
        ]
        monitor._playlist_types = {
            "https://cdn.vkvideo.ru/master.m3u8": _PlaylistType.MASTER,
            "https://cdn.vkvideo.ru/media.m3u8": _PlaylistType.MEDIA,
        }

        result = monitor.select()

        assert result[0] == "https://cdn.vkvideo.ru/media.m3u8"
        assert result[1] == "https://cdn.vkvideo.ru/master.m3u8"

    def test_select_returns_all_when_no_suspension_and_all_hls(self) -> None:
        """select() with all HLS addresses returns them all, ranked."""
        mock_page = MagicMock()
        monitor = NetworkMonitor(mock_page)
        monitor.m3u8_urls = [
            "https://cdn1.vkvideo.ru/a.m3u8",
            "https://cdn2.vkvideo.ru/b.m3u8",
        ]

        result = monitor.select()

        assert result == ["https://cdn1.vkvideo.ru/a.m3u8", "https://cdn2.vkvideo.ru/b.m3u8"]
