"""Browser infrastructure for VK Video Downloader."""

import asyncio
from pathlib import Path

from playwright.async_api import Browser, Page, Playwright, async_playwright
from structlog import get_logger

from ..config import Settings
from ..exceptions import ExtractionError

logger = get_logger(__name__)

# Timeout for browser/playwright cleanup (INT-004).
# Prevents indefinite hang during teardown.
_BROWSER_CLOSE_TIMEOUT = 10.0


class BrowserManager:
    """Async context manager for Playwright browser automation with stealth configuration."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize BrowserManager with optional settings.

        Args:
            settings: Application settings. Constructs a new Settings() from environment when not provided.
        """
        self.settings = settings if settings is not None else Settings()
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self._stealth_path = Path(__file__).parent.parent / "stealth.min.js"

    async def __aenter__(self) -> "BrowserManager":
        """Start Playwright and launch browser with stealth configuration."""
        logger.info("starting_browser")

        playwright_instance = await async_playwright().start()
        try:
            browser = await playwright_instance.chromium.launch(
                headless=self.settings.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            logger.error("browser_launch_failed", exc_info=True)
            await playwright_instance.stop()
            raise ExtractionError("Failed to launch browser for video extraction") from None

        self.playwright = playwright_instance
        self.browser = browser
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Close browser and stop Playwright with timeout safeguards (INT-004).

        Wraps ``browser.close()`` and ``playwright.stop()`` in
        ``asyncio.wait_for`` with a ~10s timeout and checks the shared
        ``shutdown_event`` before each step. The ``finally`` guarantee
        that ``playwright.stop()`` runs even if ``browser.close()`` raises
        or times out is preserved.
        """
        logger.info("closing_browser")
        # Lazy import to avoid circular dependency:
        # browser.py -> services.__init__ -> downloader -> extractor -> browser
        from ..services.downloader_throttle import get_shutdown_event

        shutdown_event = get_shutdown_event()

        try:
            if self.browser and not shutdown_event.is_set():
                try:
                    await asyncio.wait_for(self.browser.close(), timeout=_BROWSER_CLOSE_TIMEOUT)
                except TimeoutError:
                    logger.warning(
                        "browser_close_timeout",
                        pid=getattr(self.browser, "pid", None),
                        timeout=_BROWSER_CLOSE_TIMEOUT,
                    )
        finally:
            if self.playwright:
                try:
                    await asyncio.wait_for(self.playwright.stop(), timeout=_BROWSER_CLOSE_TIMEOUT)
                except TimeoutError:
                    logger.warning(
                        "playwright_stop_timeout",
                        timeout=_BROWSER_CLOSE_TIMEOUT,
                    )

    async def create_stealth_page(self) -> Page:
        """
        Create a new page with stealth configuration.

        Returns:
            Page: Configured browser page with user-agent and stealth scripts.
        """
        logger.debug("creating_stealth_page")

        context = await self.browser.new_context(  # type: ignore[union-attr]
            viewport={"width": 1920, "height": 1080},
            user_agent=self.settings.user_agent,
            locale=self.settings.locale,
            timezone_id=self.settings.timezone,
        )

        page = await context.new_page()

        if self._stealth_path.exists():
            await page.add_init_script(path=str(self._stealth_path))
            logger.debug("stealth_script_applied")

        return page
