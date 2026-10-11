"""Browser infrastructure for VK Video Downloader."""

import asyncio
from pathlib import Path

from playwright.async_api import Browser, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError
from structlog import get_logger

from ..config import Settings
from ..exceptions import ExtractionError
from ..models.enums import ErrorCode

logger = get_logger(__name__)

# Timeout for browser/playwright cleanup.
# Prevents indefinite hang during teardown.
_BROWSER_CLOSE_TIMEOUT = 10.0


class BrowserManager:
    """Async context manager for Playwright browser automation.

    Anti-detection measures — the
    ``--disable-blink-features=AutomationControlled`` launch argument and the
    ``stealth.min.js`` init-script injection — are applied only when
    :attr:`Settings.stealth_enabled` is true. The browser context's viewport,
    user agent, locale and timezone are applied unconditionally as ordinary
    context identity.
    """

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

    async def __aenter__(self) -> BrowserManager:
        """Start Playwright and launch the browser.

        When ``stealth_enabled`` is true, the ``stealth.min.js`` asset must be
        present — its absence is a hard error raised here, before the Playwright
        driver starts, so no browser is launched and no cleanup is needed. When
        stealth is disabled the asset is not consulted at all.
        """
        logger.info("starting_browser")

        if self.settings.stealth_enabled and not self._stealth_path.exists():
            msg = (
                f"stealth.min.js asset not found at {self._stealth_path}; "
                "stealth.min.js is a declared build artifact in pyproject.toml, "
                "so a missing file indicates a broken build or partial "
                "deployment rather than a bad install; "
                "VKDOWNLOADER_STEALTH_ENABLED is true but the asset is "
                "missing, so extraction cannot proceed"
            )
            logger.warning("stealth_asset_missing", hint=msg)
            error = ExtractionError(msg, error_code=ErrorCode.STEALTH_ASSET_MISSING)
            raise error

        playwright_instance = await async_playwright().start()
        try:
            launch_args: list[str] = (
                ["--disable-blink-features=AutomationControlled"]
                if self.settings.stealth_enabled
                else []
            )
            browser = await playwright_instance.chromium.launch(
                headless=self.settings.headless,
                args=launch_args,
            )
        except Exception as exc:
            # BRW-001: carry the actionable cause (the missing binary and the
            # ``playwright install`` remedy) into the raised message so the
            # caller learns how to repair the failure. ``from None`` is kept on
            # purpose: it hides the raw Playwright traceback, whose banner
            # carries box-drawing characters and a multi-line layout that a
            # strict console sink can fail to encode (that encoding gap is
            # mechanism (a), B16's subject, not this arm's). ``exc_info=True``
            # is preserved unchanged.
            logger.error("browser_launch_failed", exc_info=True)
            await playwright_instance.stop()
            raise ExtractionError(_describe_launch_failure(exc)) from None

        self.playwright = playwright_instance
        self.browser = browser
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Close browser and stop Playwright with timeout safeguards.

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
        # displace the failure that caused the exit. The pattern in downloader_throttle.py
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
        """Create a new page with the configured browser context identity.

        The page carries the ``stealth.min.js`` init script **iff**
        ``stealth_enabled`` is true; when disabled no anti-detection measures
        are applied.

        Returns:
            Page: Configured browser page with the user-agent, locale,
            timezone and viewport set, and the stealth script injected when
            enabled.
        """
        logger.debug("creating_stealth_page")

        context = await self.browser.new_context(  # type: ignore[union-attr]
            viewport={"width": 1920, "height": 1080},
            user_agent=self.settings.user_agent,
            locale=self.settings.locale,
            timezone_id=self.settings.timezone,
        )

        page = await context.new_page()

        if self.settings.stealth_enabled and self._stealth_path.exists():
            await page.add_init_script(path=str(self._stealth_path))
            logger.debug("stealth_script_applied")

        return page


# BRW-001 — private helpers that carry a browser launch failure's actionable
# cause into the raised ``ExtractionError`` message. Kept module-private and
# dependency-free so the remedy stays local to the anchor that owns it.


def _describe_launch_failure(exc: Exception) -> str:
    """Build a single-line, actionable message from a browser launch failure.

    Extracts the missing executable path and the ``playwright install`` remedy
    from the caught exception so the user can act without the multi-line
    Playwright banner that ``from None`` hides in ``__aenter__``. When neither
    element is present, falls back to an ASCII-only shadow of the underlying
    message so the surfaced text is never empty and never carries characters
    a strict console sink could not encode.
    """
    text = str(exc)
    executable = _extract_executable_path(text)
    remedy = _extract_install_remedy(text)
    parts = ["Failed to launch browser for video extraction"]
    if executable:
        parts.append(f"browser binary not found: {executable}")
    if remedy:
        parts.append(f"to obtain it: {remedy}")
    if not executable and not remedy:
        parts.append(_underlying_error_text(exc))
    return "; ".join(parts)


def _extract_executable_path(text: str) -> str:
    """Return the missing binary path from a Playwright launch error, else ``""``.

    Matches the Playwright launcher's "Executable doesn't exist at <path>"
    wording (and its "does not exist" variant), taking the path up to the end
    of that line so an install hint on a later line is never absorbed.
    """
    lowered = text.lower()
    for marker in (
        "executable doesn't exist at ",
        "executable does not exist at ",
    ):
        idx = lowered.find(marker)
        if idx != -1:
            start = idx + len(marker)
            newline = text.find("\n", start)
            end = newline if newline != -1 else len(text)
            return text[start:end].strip()
    return ""


def _extract_install_remedy(text: str) -> str:
    """Return the ``playwright install`` remedy from a launch error, else ``""``.

    The user-facing fix is the canonical ``playwright install`` command; detecting
    that phrase is sufficient to surface the actionable step, regardless of any
    ``npx`` / ``python -m`` prefix or a trailing browser name.
    """
    if "playwright install" in text.lower():
        return "playwright install"
    return ""


def _underlying_error_text(exc: Exception) -> str:
    """Single-line, ASCII-only shadow of an uninformative launch error."""
    raw = str(exc).strip()
    if not raw:
        return "see the 'browser_launch_failed' log record for details"
    first_line = raw.splitlines()[0]
    ascii_only = "".join(ch for ch in first_line if ord(ch) < 128).strip()
    if not ascii_only:
        return "see the 'browser_launch_failed' log record for details"
    return f"underlying error: {ascii_only}"
