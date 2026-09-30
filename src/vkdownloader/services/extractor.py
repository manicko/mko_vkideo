"""VK Video Extractor service for extracting stream URLs from video pages."""

import asyncio
import re
from pathlib import PurePosixPath
from typing import Any, cast
from urllib.parse import urlsplit

import yt_dlp
from playwright.async_api import Cookie, Page
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from structlog import get_logger

from ..config import Settings
from ..exceptions import ExtractionError, InvalidVideoUrlError, VideoNotFoundError
from ..infrastructure.browser import BrowserManager
from ..infrastructure.network_monitor import NetworkMonitor
from ..models.enums import CookieSource, QualityEnum, StreamFormat
from ..models.video import Stream, VideoWithStreams
from ..services.downloader_throttle import URLBackoffCoordinator, get_shutdown_event
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)

# VK video URL pattern for validation and parsing
VIDEO_ID_PATTERN = re.compile(r"video-(-?\d+)_(\d+)")


def is_valid_video_url(url: str) -> bool:
    """Check if a URL matches the VK video URL pattern.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL contains a valid VK video identifier, False otherwise.
    """
    return bool(VIDEO_ID_PATTERN.search(url))


def _classify_format(url: str) -> StreamFormat:
    """Classify a stream URL as HLS or MP4 by its parsed path suffix (NET-017).

    Only a ``.m3u8`` path suffix maps to HLS; every other suffix — including a
    suffixless path — maps to MP4. A ``.m3u8`` appearing only in the query
    string, a fragment, or a directory name does not count. ``urlsplit`` raising
    ``ValueError`` falls back to MP4 so the parse is total and the caller never
    has to handle an exception.
    """
    try:
        path = urlsplit(url).path
    except ValueError:
        return StreamFormat.MP4
    suffix = PurePosixPath(path).suffix.lower()
    return StreamFormat.HLS if suffix == ".m3u8" else StreamFormat.MP4


def _declares_video_codec(f: dict[str, Any]) -> bool:
    """Return True when a format dict declares a usable video codec (NET-017).

    A record is video-bearing only when the ``vcodec`` key is present, its value
    is a non-empty string, and it is not the audio-only literal ``"none"``
    (case-insensitive). A record that omits the key is indeterminate — neither
    video-bearing nor explicitly audio-only — and is therefore not offered.

    Height or width are never read as a proxy here: they are the placeholder
    field this same block redefines, and a heightless video record would be
    wrongly dropped (see ``test_build_streams_quality_unknown_without_height``).
    """
    codec = f.get("vcodec")
    if not isinstance(codec, str) or codec == "":
        return False
    return codec.lower() != "none"


def _build_streams(formats: list[dict[str, Any]]) -> list[Stream]:
    """Convert raw yt-dlp format dicts into the stream list, in input order.

    Filtering decisions (NET-017):
    - Offer only a record that explicitly declares a video codec (see
      ``_declares_video_codec``); a record with no ``vcodec`` key is dropped.
    - Skip formats with a falsy ``url``.
    - Classify format by the parsed path suffix via ``_classify_format``
      (``.m3u8`` -> HLS, everything else -> MP4), not by a substring test.
    """
    found_streams: list[Stream] = []
    for f in formats:
        # NET-017: exclude records that do not declare a video codec (absent,
        # empty, or the audio-only literal).
        if not _declares_video_codec(f):
            continue
        height = cast(int | None, f.get("height"))
        width = cast(int | None, f.get("width"))
        format_url = f.get("url")
        # Skip formats without a usable URL.
        if not format_url:
            continue
        tbr = f.get("tbr")
        # NET-017: height <= 0 is treated as absent so a placeholder zero cannot
        # be mistaken for a real resolution. Stream.height keeps the raw value.
        quality = f"{height}p" if height is not None and height > 0 else "unknown"
        stream = Stream(
            url=format_url,
            format=_classify_format(format_url),
            quality=quality,
            width=width,
            height=height,
            bitrate=int(tbr) if tbr else None,
            resolution=f"{width}x{height}" if width and height else None,
        )
        found_streams.append(stream)
    return found_streams


class VKVideoExtractor:
    """Extracts video stream information from VK video URLs using browser automation."""

    VIDEO_ID_PATTERN = VIDEO_ID_PATTERN

    def __init__(
        self,
        settings: Settings | None = None,
        backoff_coordinator: URLBackoffCoordinator | None = None,
    ) -> None:
        """
        Initialize VKVideoExtractor with optional settings.

        Args:
            settings: Application settings. Uses global settings if not provided.
            backoff_coordinator: Optional shared URLBackoffCoordinator for
                pausing retryable transport failures on the origin before
                yt-dlp extraction calls.
        """
        self.settings = settings if settings is not None else Settings()
        self.backoff_coordinator = backoff_coordinator

    def parse_video_id(self, url: str) -> tuple[str, str]:
        """
        Extract owner_id and video_id from VK video URL.

        Args:
            url: VK video URL containing video identifier.

        Returns:
            Tuple of (owner_id, video_id) extracted from URL.

        Raises:
            InvalidVideoUrlError: If URL does not contain a valid video identifier.
        """
        match = self.VIDEO_ID_PATTERN.search(url)
        if not match:
            raise InvalidVideoUrlError(url)
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
            InvalidVideoUrlError: If URL does not contain a valid video identifier.
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
    ) -> tuple[list[Stream], str | None, list[Cookie] | None]:
        """
        Extract streams using browser automation to capture cookies for ffmpeg.

        Args:
            url: VK video URL to extract streams from.
            force_browser: Force browser launch even when cookie_source=NONE (for token refresh).

        Returns:
            Tuple of (streams list, cookies string for ffmpeg headers, raw cookies for Netscape).

        Raises:
            InvalidVideoUrlError: If URL does not contain a valid video identifier.
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
            return streams, None, None

        # Existing browser launch logic for BROWSER mode or forced
        streams, cookies, raw_cookies = await self._extract_with_browser(url, video_id_full)

        if not streams:
            raise VideoNotFoundError(f"No streams found for video: {_strip_auth_params(url)}")

        logger.info("extraction_complete", video_id=video_id_full, streams_count=len(streams))
        return streams, cookies, raw_cookies

    async def _extract_with_ytdlp(self, url: str, video_id: str) -> tuple[list[Stream], str | None]:
        """Extract streams and title using yt-dlp (handles VK protections).

        Propagates relevant :class:`Settings` fields (``socket_timeout``,
        ``retries``, ``fragment_retries``, ``throttled_rate``) into the
        yt-dlp options dict and wraps the blocking extraction in
        ``asyncio.wait_for`` with ``settings.download_timeout`` so the
        event loop is not blocked indefinitely (INT-003).
        """
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "nocheckcertificate": not self.settings.ssl_verify,
            # INT-003: propagate Settings to yt-dlp library-mode so it
            # respects the same timeout/retry/throttle config as the
            # subprocess CLI path (downloader.py _build_ytdlp_cli_command).
            "socket_timeout": self.settings.download_timeout,
            "retries": self.settings.max_retries,
            "fragment_retries": self.settings.max_retries,
            "throttled_rate": self.settings.throttled_rate,
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

                    found_streams = _build_streams(info.get("formats", []) or [])
                except ExtractionError:
                    raise
                except Exception as e:
                    logger.warning(
                        "ytdlp_extraction_error",
                        error=str(e),
                        url=_strip_auth_params(url),
                    )
                    raise ExtractionError(
                        f"Extraction failed for {_strip_auth_params(url)}: {e}"
                    ) from e

            return found_streams, title

        # Run in thread pool to avoid blocking, with a timeout (INT-003)
        # so a hung yt-dlp extraction cannot block the event loop
        # indefinitely.
        if self.backoff_coordinator is not None:
            await self.backoff_coordinator.wait_if_paused(url)
        loop = asyncio.get_running_loop()
        try:
            streams, title = await asyncio.wait_for(
                loop.run_in_executor(None, _sync_extract),
                timeout=self.settings.download_timeout,
            )
        except TimeoutError:
            logger.error(
                "ytdlp_extraction_timeout",
                url=_strip_auth_params(url),
                timeout=self.settings.download_timeout,
            )
            raise ExtractionError(
                f"yt-dlp extraction timed out after {self.settings.download_timeout}s "
                f"for {_strip_auth_params(url)}"
            ) from None

        logger.debug("ytdlp_extraction_complete", count=len(streams))
        return streams, title

    async def _extract_with_browser(
        self, url: str, video_id_full: str
    ) -> tuple[list[Stream], str | None, list[Cookie] | None]:
        """Extract streams using Playwright browser automation with cookies capture."""
        streams: list[Stream] = []
        cookies_str: str | None = None
        raw_cookies: list[Cookie] | None = None

        async with BrowserManager(self.settings) as browser:
            page = await browser.create_stealth_page()
            monitor = NetworkMonitor(page)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except (PlaywrightError, PlaywrightTimeoutError) as e:
                raise ExtractionError(
                    f"Failed to navigate to video page: {_strip_auth_params(url)}"
                ) from e
            await asyncio.sleep(self.settings.browser_pre_interaction_wait)
            await self._simulate_video_interaction(page)
            await asyncio.sleep(self.settings.browser_post_interaction_wait)

            shutdown_event = get_shutdown_event()
            if shutdown_event.is_set():
                logger.info("browser_extraction_cancelled")
                raise asyncio.CancelledError("Browser extraction cancelled by user")

            try:
                raw_cookies = await page.context.cookies()
                cookies_str = self._format_cookies_for_ffmpeg(raw_cookies)
            except Exception as e:
                logger.debug("failed_to_capture_cookies", error=str(e))

            logger.debug(
                "captured_m3u8_urls", urls=[_strip_auth_params(u) for u in monitor.m3u8_urls]
            )

            addresses = monitor.select()
            if addresses:
                stream = Stream(
                    url=addresses[0],
                    format=StreamFormat.HLS,
                    quality=QualityEnum.UNKNOWN.value,
                    width=None,
                    height=None,
                )
                streams.append(stream)
                # B7: single combined INFO record carrying the chosen address's
                # host and the chosen quality label together (criterion 3).
                logger.info(
                    "browser_stream_selected",
                    host=urlsplit(addresses[0]).netloc or "unknown",
                    quality=QualityEnum.UNKNOWN.value,
                )
                # B7: single combined record carrying the chosen address's host
                # and the chosen quality label together (criterion 3).
                logger.info(
                    "browser_stream_selected",
                    host=urlsplit(addresses[0]).netloc or "unknown",
                    quality=QualityEnum.UNKNOWN.value,
                )

        return streams, cookies_str, raw_cookies

    def _format_cookies_for_ffmpeg(self, cookies: list[Cookie]) -> str:
        """Format cookies list for ffmpeg HTTP cookie header.

        Strips CRLF characters from cookie names and values to prevent header injection.
        Includes all cookies to ensure proper CDN authentication.
        """
        cookie_parts = []
        for cookie in cookies:
            name = cookie.get("name", "").replace("\r", "").replace("\n", "")
            value = cookie.get("value", "").replace("\r", "").replace("\n", "")
            cookie_parts.append(f"{name}={value}")
        return "; ".join(cookie_parts)

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
        except PlaywrightTimeoutError:
            logger.debug("video_player_click_failed", exc_info=True, phase="video_interaction")
