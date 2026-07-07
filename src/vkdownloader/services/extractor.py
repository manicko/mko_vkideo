"""VK Video Extractor service for extracting stream URLs from video pages."""

import asyncio
import re
from typing import Any

import yt_dlp
from playwright.async_api import Page
from pydantic import HttpUrl
from structlog import get_logger

from ..config import Settings
from ..infrastructure.browser import BrowserManager
from ..infrastructure.http_client import HttpClient
from ..infrastructure.network_monitor import NetworkMonitor
from ..models.enums import StreamFormat
from ..models.video import Stream, VideoWithStreams

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
            raise ValueError(f"Invalid VK video URL: {url}")
        owner_id, video_id = match.group(1), match.group(2)
        logger.debug("parsed_video_id", owner_id=owner_id, video_id=video_id, url=url)
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
        """
        owner_id, video_id = self.parse_video_id(url)
        video_id_full = f"{owner_id}_{video_id}"

        logger.info("extracting_streams", video_id=video_id_full, url=url)

        streams = await self._extract_with_ytdlp(url, video_id_full)

        logger.info("extraction_complete", video_id=video_id_full, streams_count=len(streams))

        return VideoWithStreams(
            id=video_id_full,
            streams=streams,
        )

    async def extract_streams_with_cookies(self, url: str) -> tuple[list[Stream], str | None]:
        """
        Extract streams using browser automation to capture cookies for ffmpeg.

        Args:
            url: VK video URL to extract streams from.

        Returns:
            Tuple of (streams list, cookies string for ffmpeg headers).
        """
        owner_id, video_id = self.parse_video_id(url)
        video_id_full = f"{owner_id}_{video_id}"

        logger.info("extracting_streams_with_cookies", video_id=video_id_full, url=url)

        streams, cookies = await self._extract_with_browser(url, video_id_full)

        logger.info("extraction_complete", video_id=video_id_full, streams_count=len(streams))
        return streams, cookies

    async def _extract_with_ytdlp(self, url: str, video_id: str) -> list[Stream]:
        """Extract streams using yt-dlp (handles VK protections)."""
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        def _sync_extract() -> list[Stream]:
            """Synchronous extraction in thread."""
            found_streams: list[Stream] = []
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        return found_streams

                    formats = info.get("formats", [])
                    for f in formats:
                        # Only include formats with video (skip audio-only)
                        if f.get("vcodec") != "none":
                            height = f.get("height")
                            width = f.get("width")
                            format_url = f.get("url")
                            if format_url:
                                stream = Stream(
                                    url=HttpUrl(format_url),
                                    format=StreamFormat.HLS if ".m3u8" in format_url else StreamFormat.MP4,
                                    quality=f"{height}p" if height else "unknown",
                                    width=width,
                                    height=height,
                                    bitrate=int(f.get("tbr")) if f.get("tbr") else None,
                                    resolution=f"{width}x{height}" if width and height else None,
                                )
                                found_streams.append(stream)
                except Exception as e:
                    logger.warning("ytdlp_extraction_error", error=str(e))

            return found_streams

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        streams = await loop.run_in_executor(None, _sync_extract)

        logger.debug("ytdlp_extraction_complete", count=len(streams))
        return streams

    async def _extract_with_browser(self, url: str, video_id_full: str) -> tuple[list[Stream], str | None]:
        """Extract streams using Playwright browser automation with cookies capture."""
        streams: list[Stream] = []
        cookies_str: str | None = None

        async with BrowserManager(self.settings) as browser:
            page = await browser.create_stealth_page()
            monitor = NetworkMonitor(page)

            # Navigate to video page
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for page to load, then simulate interaction
            await asyncio.sleep(5)
            
            # Simulate human-like interaction
            await self._simulate_video_interaction(page)
            
            # Wait for m3u8 URLs to be captured (network requests for video)
            await asyncio.sleep(8)

            # Capture cookies from browser session for ffmpeg
            try:
                cookies = await page.context.cookies()
                cookies_str = self._format_cookies_for_ffmpeg(cookies)
            except Exception as e:
                logger.debug("failed_to_capture_cookies", error=str(e))

            logger.debug("captured_m3u8_urls", urls=monitor.m3u8_urls)

            # Use master m3u8 URL directly with ffmpeg (skip parsing for simplicity)
            if monitor.m3u8_urls:
                stream = Stream(
                    url=HttpUrl(monitor.m3u8_urls[0]),
                    format=StreamFormat.HLS,
                    quality="best",
                    width=None,
                    height=None,
                )
                streams.append(stream)

        return streams, cookies_str

    def _format_cookies_for_ffmpeg(self, cookies: list[dict]) -> str:
        """Format cookies list for ffmpeg HTTP cookie header."""
        cookie_parts = []
        for cookie in cookies:
            name = cookie.get("name", "")
            value = cookie.get("value", "")
            domain = cookie.get("domain", "")
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
        except Exception:
            pass

    async def _parse_m3u8_playlist(self, url: str) -> list[Stream]:
        """
        Download and parse m3u8 playlist to extract quality variants.

        Args:
            url: URL of m3u8 playlist to parse.

        Returns:
            List of Stream objects with extracted quality information.
        """
        logger.debug("parsing_m3u8_playlist", url=url)

        async with HttpClient(self.settings) as http_client:
            content = await http_client.get(url)

        streams = []
        lines = content.split("\n")

        from urllib.parse import urljoin

        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                # Parse the stream info line
                bandwidth_match = re.search(r"BANDWIDTH=(\d+)", line)
                resolution_match = re.search(r"RESOLUTION=(\d+x\d+)", line)

                # Get the URL from next line
                if i + 1 < len(lines):
                    stream_url = lines[i + 1]
                    if stream_url and not stream_url.startswith("#"):
                        # Resolve relative URLs
                        if not stream_url.startswith("http"):
                            stream_url = urljoin(url, stream_url)

                        # Parse resolution
                        width = None
                        height = None
                        if resolution_match:
                            resolution = resolution_match.group(1)
                            width, height = map(int, resolution.split("x"))

                        stream = Stream(
                            url=HttpUrl(stream_url),
                            format=StreamFormat.HLS,
                            quality=f"{height}p" if height else "unknown",
                            bitrate=int(bandwidth_match.group(1)) if bandwidth_match else None,
                            width=width,
                            height=height,
                        )
                        streams.append(stream)

        # Handle single stream (not a playlist)
        if not streams:
            if url.endswith(".m3u8"):
                stream = Stream(
                    url=HttpUrl(url),
                    format=StreamFormat.HLS,
                    quality="unknown",
                    width=None,
                    height=None,
                )
                streams.append(stream)

        return streams