"""VK Video Extractor service for extracting stream URLs from video pages."""

import asyncio
import re

import yt_dlp
from playwright.async_api import Cookie, Page
from structlog import get_logger

from ..config import Settings
from ..exceptions import ExtractionError, VideoNotFoundError
from ..infrastructure.browser import BrowserManager
from ..infrastructure.network_monitor import NetworkMonitor
from ..models.enums import CookieSource, StreamFormat
from ..models.video import Stream, VideoWithStreams
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


class VKVideoExtractor:
    """Extracts video stream information from VK video URLs using browser automation."""

    VIDEO_ID_PATTERN = re.compile(r"video-(-?\d+)_(\d+)")

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize VKVideoExtractor with optional settings.

        Args:
            settings: Application settings. Uses global settings if not provided.
        """
        self.settings = settings if settings is not None else Settings()

    def parse_video_id(self, url: str) -> tuple[str, str]:
        """
        Extract owner_id and video_id from VK video URL.

        Args:
            url: VK video URL containing video identifier.

        Returns:
            Tuple of (owner_id, video_id) extracted from URL.

        Raises:
            ValueError: If URL does not contain valid video identifier.
        """
        match = self.VIDEO_ID_PATTERN.search(url)
        if not match:
            raise ValueError(f"Invalid VK video URL: {_strip_auth_params(url)}")
        owner_id, video_id = match.group(1), match.group(2)
        logger.debug(
            "parsed_video_id", owner_id=owner_id, video_id=video_id, url=_strip_auth_params(url)
        )
        return owner_id, video_id

    async def extract_streams(self, url: str) -> VideoWithStreams:
        """
        Extract available streams from video URL using yt-dlp.

        Uses yt-dlp as primary method (handles VK protections).

        Args:
            url: VK video URL to extract streams from.

        Returns:
            VideoWithStreams containing available quality variants.

        Raises:
            ValueError: If URL does not contain valid video identifier.
            VideoNotFoundError: If no streams are found for the video.
            ExtractionError: If extraction fails.
        """
        owner_id, video_id = self.parse_video_id(url)
        video_id_full = f"{owner_id}_{video_id}"

        logger.info("extracting_streams", video_id=video_id_full, url=_strip_auth_params(url))

        streams, title = await self._extract_with_ytdlp(url, video_id_full)

        if not streams:
            raise VideoNotFoundError(f"No streams found for video: {_strip_auth_params(url)}")

        logger.info("extraction_complete", video_id=video_id_full, streams_count=len(streams))

        return VideoWithStreams(
            id=video_id_full,
            streams=streams,
            title=title,
        )

    async def extract_streams_with_cookies(
        self, url: str, force_browser: bool = False
    ) -> tuple[list[Stream], str | None]:
        """
        Extract streams using browser automation to capture cookies for ffmpeg.

        Args:
            url: VK video URL to extract streams from.
            force_browser: Force browser launch even when cookie_source=NONE (for token refresh).

        Returns:
            Tuple of (streams list, cookies string for ffmpeg headers).

        Raises:
            ValueError: If URL does not contain valid video identifier.
            VideoNotFoundError: If no streams are found for the video.
        """
        owner_id, video_id = self.parse_video_id(url)
        video_id_full = f"{owner_id}_{video_id}"

        logger.info("extracting_streams_with_cookies", video_id=video_id_full)

        # Check cookie source setting first (unless forced)
        if not force_browser and self.settings.cookie_source == CookieSource.NONE:
            # Skip browser, use yt-dlp only - no cookies
            streams, _ = await self._extract_with_ytdlp(url, video_id_full)
            if not streams:
                raise VideoNotFoundError(f"No streams found for video: {_strip_auth_params(url)}")
            logger.info("extraction_complete", video_id=video_id_full, streams_count=len(streams))
            return streams, None

        if self.settings.cookie_source == CookieSource.FILE:
            raise NotImplementedError(
                "CookieSource.FILE is not implemented. "
                "Use --cookie-source browser or none instead."
            )

        # Existing browser launch logic for BROWSER mode or forced
        streams, cookies = await self._extract_with_browser(url, video_id_full)

        if not streams:
            raise VideoNotFoundError(f"No streams found for video: {_strip_auth_params(url)}")

        logger.info("extraction_complete", video_id=video_id_full, streams_count=len(streams))
        return streams, cookies

    async def _extract_with_ytdlp(self, url: str, video_id: str) -> tuple[list[Stream], str | None]:
        """Extract streams and title using yt-dlp (handles VK protections)."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        def _sync_extract() -> tuple[list[Stream], str | None]:
            """Synchronous extraction in thread."""
            found_streams: list[Stream] = []
            title: str | None = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        raise ExtractionError(
                            f"No video info extracted for video: {_strip_auth_params(url)}"
                        )

                    # Extract title from video metadata
                    title = info.get("title") or info.get("fulltitle")

                    formats = info.get("formats", [])
                    for f in formats:
                        # Only include formats with video (skip audio-only)
                        if f.get("vcodec") != "none":
                            height = f.get("height")
                            width = f.get("width")
                            format_url = f.get("url")
                            if format_url:
                                stream = Stream(
                                    url=format_url,
                                    format=StreamFormat.HLS
                                    if ".m3u8" in format_url
                                    else StreamFormat.MP4,
                                    quality=f"{height}p" if height else "unknown",
                                    width=width,
                                    height=height,
                                    bitrate=int(f.get("tbr")) if f.get("tbr") else None,
                                    resolution=f"{width}x{height}" if width and height else None,
                                )
                                found_streams.append(stream)
                except ExtractionError:
                    raise
                except Exception as e:
                    logger.warning("ytdlp_extraction_error", error=str(e))
                    raise ExtractionError(f"Failed to extract video data: {e}") from e

            return found_streams, title

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        streams, title = await loop.run_in_executor(None, _sync_extract)

        logger.debug("ytdlp_extraction_complete", count=len(streams))
        return streams, title

    async def _extract_with_browser(
        self, url: str, video_id_full: str
    ) -> tuple[list[Stream], str | None]:
        """Extract streams using Playwright browser automation with cookies capture."""
        streams: list[Stream] = []
        cookies_str: str | None = None

        async with BrowserManager(self.settings) as browser:
            page = await browser.create_stealth_page()
            monitor = NetworkMonitor(page)

            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
            await self._simulate_video_interaction(page)
            await asyncio.sleep(8)

            try:
                cookies = await page.context.cookies()
                cookies_str = self._format_cookies_for_ffmpeg(cookies)
            except Exception as e:
                logger.debug("failed_to_capture_cookies", error=str(e))

            logger.debug(
                "captured_m3u8_urls", urls=[_strip_auth_params(u) for u in monitor.m3u8_urls]
            )

            if monitor.m3u8_urls:
                stream = Stream(
                    url=monitor.m3u8_urls[0],
                    format=StreamFormat.HLS,
                    quality="best",
                    width=None,
                    height=None,
                )
                streams.append(stream)

        return streams, cookies_str

    def _format_cookies_for_ffmpeg(self, cookies: list[Cookie]) -> str:
        """Format cookies list for ffmpeg HTTP cookie header.

        Strips CRLF characters from cookie names and values to prevent header injection.
        """
        cookie_parts = []
        for cookie in cookies:
            name = cookie.get("name", "").replace("\r", "").replace("\n", "")
            value = cookie.get("value", "").replace("\r", "").replace("\n", "")
            # Include all cookies - they may be needed for CDN authentication
            cookie_parts.append(f"{name}={value}")
        return "; ".join(cookie_parts[:20])  # Limit to avoid header size issues

    async def _simulate_video_interaction(self, page: Page) -> None:
        """
        Simulate user interaction with video player to trigger stream loading.

        Args:
            page: Playwright Page instance with loaded video page.
        """
        logger.debug("simulating_video_interaction")

        # Simulate mouse movement to appear more human-like
        await page.mouse.move(150, 200)
        await page.mouse.move(200, 250)
        await asyncio.sleep(0.5)

        # Try clicking video player to trigger playback
        try:
            await page.click(".VideoPlayer")
            logger.debug("clicked_video_player")
        except TimeoutError:
            logger.debug("video_player_click_failed", exc_info=True)
