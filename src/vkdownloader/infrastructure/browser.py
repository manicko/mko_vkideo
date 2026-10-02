"""Browser infrastructure for VK Video Downloader."""

import asyncio
from pathlib import Path

from playwright.async_api import Browser, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError
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

        Both releases run unconditionally whenever the handle exists: ``browser.close()``
        is wrapped in ``asyncio.wait_for`` with ``_BROWSER_CLOSE_TIMEOUT`` so a stop
        SHORTENS the close instead of skipping it, and ``playwright.stop()`` runs in the
        ``finally`` so it is guaranteed even when ``browser.close()`` raises or times out.

        A release failure of the typed set — ``(PlaywrightError, TimeoutError)`` — is
        logged and suppressed so it can never replace the exception the ``async with``
        body was unwinding. Any other exception from the release path propagates,
        because it is a defect in this code.
        """
        logger.info("closing_browser")
        # CON-004 + CON-005, enforced by phase04/VAL-401:
        # The guard previously skipped browser.close() on the stop path — exactly the
        # path _extract_with_browser takes when it raises CancelledError — so an
        # interrupted extraction released exactly one of two resources. And each release
        # arm caught only TimeoutError, so a non-timeout driver failure escaped __aexit__
        # and replaced the exception already in flight. Both arms now catch
        # (PlaywrightError, TimeoutError) and log+suppress, so a release failure can never
        # displace the failure that caused the exit. INT-006 in downloader_throttle.py
        # is the in-repo precedent for the typed set: a bare `except Exception` would
        # destroy the only signal that this module's teardown is broken. CancelledError,
        # KeyboardInterrupt and SystemExit are never suppressed. The finally guaranteeing
        # playwright.stop() is preserved exactly; handles are not cleared on the way out.
        primary_error = exc_type.__name__ if exc_type is not None else None
        try:
            if self.browser:
                try:
                    await asyncio.wait_for(self.browser.close(), timeout=_BROWSER_CLOSE_TIMEOUT)
                except (PlaywrightError, TimeoutError) as exc:
                    logger.warning(
                        "browser_close_failed",
                        error=str(exc),
                        error_type=type(exc).__name__,
                        timeout=_BROWSER_CLOSE_TIMEOUT,
                        primary_error=primary_error,
                        pid=getattr(self.browser, "pid", None),
                        exc_info=True,
                    )
        finally:
            if self.playwright:
                try:
                    await asyncio.wait_for(self.playwright.stop(), timeout=_BROWSER_CLOSE_TIMEOUT)
                except (PlaywrightError, TimeoutError) as exc:
                    logger.warning(
                        "playwright_stop_failed",
                        error=str(exc),
                        error_type=type(exc).__name__,
                        timeout=_BROWSER_CLOSE_TIMEOUT,
                        primary_error=primary_error,
                        exc_info=True,
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
