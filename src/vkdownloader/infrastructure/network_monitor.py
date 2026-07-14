"""Network monitoring infrastructure for VK Video Downloader."""

import re
from typing import Any

from playwright.async_api import Page
from structlog import get_logger

from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


class NetworkMonitor:
    """Monitors network traffic to capture m3u8 URLs from responses."""

    M3U8_PATTERN = re.compile(r"(?:https?://)?[^\s\"'<>]+\.m3u8(?:\?[^\s\"'<>]*)?")

    def __init__(self, page: Page) -> None:
        """
        Initialize NetworkMonitor with a Playwright page.

        Args:
            page: Playwright Page instance to monitor network traffic for.
        """
        self.page = page
        self.m3u8_urls: list[str] = []
        self._setup_interceptors()

    def _setup_interceptors(self) -> None:
        """Set up response interceptors for m3u8 detection."""
        logger.debug("setting_up_network_interceptors")
        self.page.on("response", self._intercept_response)

    def _normalize_url(self, url: str) -> str:
        """Convert relative m3u8 URL to absolute URL."""
        url = url.strip()
        if url.startswith("http://") or url.startswith("https://"):
            return url
        # Handle relative URLs from VK CDN
        if url.startswith("/"):
            return f"https://{url[1:]}" if not url.startswith("//") else f"https:{url}"
        if url.startswith("//"):
            return f"https:{url}"
        return f"https://{url}"

    async def _intercept_response(self, response: Any) -> None:
        """
        Intercept network responses and capture m3u8 URLs.

        Args:
            response: Playwright Response object.
        """
        url = response.url
        # Check both absolute and relative m3u8 URLs
        if ".m3u8" in url.lower() or self.M3U8_PATTERN.search(url):
            normalized = self._normalize_url(url)
            if normalized not in self.m3u8_urls:
                self.m3u8_urls.append(normalized)
            logger.debug("m3u8_url_captured", url=_strip_auth_params(normalized))

        # Also check for XHR responses containing stream URLs
        if "video" in url and response.headers.get("content-type", "").startswith(
            "application/json"
        ):
            try:
                data = await response.json()
                self._extract_urls_from_json(data)
            except Exception:
                pass

    def _extract_urls_from_json(self, data: Any) -> None:
        """
        Recursively extract m3u8 URLs from JSON data.

        Args:
            data: JSON data to search for m3u8 URLs.
        """
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str) and ".m3u8" in value.lower():
                    normalized = self._normalize_url(value)
                    if normalized not in self.m3u8_urls:
                        self.m3u8_urls.append(normalized)
                        logger.debug("m3u8_url_found_in_json", url=_strip_auth_params(normalized))
                elif isinstance(value, (dict, list)):
                    self._extract_urls_from_json(value)
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item)
