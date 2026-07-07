"""VK Video Extractor service for extracting stream URLs from video pages."""

import asyncio
import re

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

    VIDEO_ID_PATTERN = re.compile(r"video-(\d+)_(\d+)")

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
        Extract available streams from video URL by navigating page and capturing m3u8 URLs.

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

        async with BrowserManager(self.settings) as browser:
            page = await browser.create_stealth_page()
            monitor = NetworkMonitor(page)

            await page.goto(url, wait_until="networkidle")
            await self._simulate_video_interaction(page)
            await asyncio.sleep(3)  # Wait for API calls to complete

            streams = []
            for m3u8_url in monitor.m3u8_urls:
                parsed_streams = await self._parse_m3u8_playlist(m3u8_url)
                streams.extend(parsed_streams)
                logger.debug("parsed_m3u8_playlist", url=m3u8_url, streams_count=len(parsed_streams))

            logger.info("extraction_complete", video_id=video_id_full, streams_count=len(streams))

            return VideoWithStreams(
                id=video_id_full,
                streams=streams,
            )

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

        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                # Parse the stream info line
                bandwidth_match = re.search(r"BANDWIDTH=(\d+)", line)
                resolution_match = re.search(r"RESOLUTION=(\d+x\d+)", line)

                # Get the URL from next line
                if i + 1 < len(lines):
                    stream_url = lines[i + 1]
                    if stream_url and not stream_url.startswith("#"):
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

        return streams
