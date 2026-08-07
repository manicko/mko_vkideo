"""Network monitoring infrastructure for VK Video Downloader."""

import json
import re

from playwright.async_api import Page, Response
from structlog import get_logger

from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


# Type alias for JSON values (recursive structure)
type JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None


class NetworkMonitor:
    """Monitors network traffic to capture m3u8 URLs from responses."""

    M3U8_PATTERN = re.compile(r"(?:https?://)?[^\s\"'<>]+\.m3u8(?:\?[^\s\"'<>]*)?")
    # Maximum response body size (in bytes) to parse for m3u8 URLs
    MAX_JSON_BODY_BYTES: int = 1_000_000

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

    async def _intercept_response(self, response: Response) -> None:
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
            # Guard: skip oversized JSON bodies to avoid memory issues
            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    size_bytes = int(content_length)
                    if size_bytes >= self.MAX_JSON_BODY_BYTES:
                        logger.debug(
                            "skipping_oversized_json_response",
                            url=_strip_auth_params(url),
                            size=size_bytes,
                        )
                        return
                except ValueError:
                    pass  # Invalid content-length header, fall through to body check

            # Enforce a byte cap even when Content-Length is absent
            # (chunked/streamed responses may omit the header).
            try:
                body = await response.body()
            except Exception as e:
                logger.warning(
                    "response_body_error",
                    url=_strip_auth_params(url),
                    error=str(e.__class__.__name__),
                )
                return

            if len(body) >= self.MAX_JSON_BODY_BYTES:
                logger.debug(
                    "skipping_oversized_json_response",
                    url=_strip_auth_params(url),
                    size=len(body),
                )
                return

            try:
                data = json.loads(body)
                self._extract_urls_from_json(data)
            except json.JSONDecodeError:
                logger.warning(
                    "json_parse_error",
                    url=_strip_auth_params(url),
                    reason="invalid_json_in_response",
                )
            except Exception as e:
                logger.warning(
                    "response_json_error",
                    url=_strip_auth_params(url),
                    error=str(e.__class__.__name__),
                )

    def _extract_urls_from_json(self, data: JsonValue) -> None:
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
