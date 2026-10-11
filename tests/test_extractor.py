"""Tests for VKVideoExtractor service."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright.async_api import Cookie
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from vkdownloader.config import Settings
from vkdownloader.exceptions import ExtractionError, InvalidVideoUrlError, VideoNotFoundError
from vkdownloader.models.enums import CookieSource, QualityLabel, StreamFormat
from vkdownloader.models.video import Stream
from vkdownloader.services.cookies import _cookies_to_netscape
from vkdownloader.services.downloader_throttle import _shutdown_event_ctx
from vkdownloader.services.extractor import VKVideoExtractor, _build_streams, is_valid_video_url


def test_parse_video_id_valid() -> None:
    """Test parse_video_id extracts IDs from valid VK video URL."""
    extractor = VKVideoExtractor()
    url = "https://vkvideo.ru/video-12345_67890"

    owner_id, video_id = extractor.parse_video_id(url)
    assert owner_id == "12345"
    assert video_id == "67890"


def test_parse_video_id_various_urls() -> None:
    """Test parse_video_id handles various valid URL formats."""
    extractor = VKVideoExtractor()

    # Standard URL format
    owner_id, video_id = extractor.parse_video_id("https://vkvideo.ru/video-1_2")
    assert owner_id == "1"
    assert video_id == "2"

    # URL with path prefix
    owner_id, video_id = extractor.parse_video_id("https://vk.com/video-123_456")
    assert owner_id == "123"
    assert video_id == "456"


def test_parse_video_id_invalid() -> None:
    """Test parse_video_id raises InvalidVideoUrlError for invalid URL."""
    extractor = VKVideoExtractor()
    invalid_url = "https://example.com/invalid"

    with pytest.raises(InvalidVideoUrlError, match="Invalid VK video URL"):
        extractor.parse_video_id(invalid_url)


def test_parse_video_id_empty_string() -> None:
    """Test parse_video_id raises InvalidVideoUrlError for empty string."""
    extractor = VKVideoExtractor()

    with pytest.raises(InvalidVideoUrlError, match="Invalid VK video URL"):
        extractor.parse_video_id("")


# ---------------------------------------------------------------------------
# B12 acceptance table — data-driven accept / reject oracle
# ---------------------------------------------------------------------------

_ACCEPT_URLS = [
    "https://vkvideo.ru/video-12345_67890",  # canonical, no trailing slash
    "https://vkvideo.ru/video-12345_67890/",  # canonical, trailing slash
    "https://vkvideo.ru/video-12345_67890?some=param",  # canonical, query string
    "https://vk.com/video-12345_67890",  # alternate host
    "https://vkvideo.ru/video-12345_67890?t=123",  # canonical, query params
]

_REJECT_URLS = [
    "video_123_456",  # wrong separator: _ instead of -
    "videos-123_456",  # plural "videos" not "video"
    "video-1O3_456",  # letter O instead of zero
    "",  # empty string
    "not a url",  # no pattern at all
    "https://example.com/some/video-12345_67890/extra",  # pattern embedded in longer path
]


@pytest.mark.parametrize("url", _ACCEPT_URLS)
def test_video_url_acceptance_table(url: str) -> None:
    """B12: is_valid_video_url accepts the canonical VK forms.

    Criterion 8 — the canonical form (``sample_video_url``) and its
    trailing-slash / query variants stay accepted. criterion 2 — the bare
    pattern with no scheme or origin is rejected — is exercised by the
    rejection table below.
    """
    assert is_valid_video_url(url) is True


@pytest.mark.parametrize("url", _REJECT_URLS)
def test_video_url_rejection_table(url: str) -> None:
    """B12: is_valid_video_url rejects near-miss and foreign-origin forms.

    criterion 1 — a foreign origin whose path embeds the pattern, and one
    whose query value embeds it, are rejected (the last case in the table
    has the pattern as a non-final path component).  criterion 2 — the
    bare pattern with no scheme or origin is rejected (``video_123_456``,
    ``videos-123_456``, ``video-1O3_456``, the empty string, ``not a url``).
    """
    assert is_valid_video_url(url) is False


@pytest.mark.parametrize("url", _ACCEPT_URLS)
def test_video_url_acceptance_table_parse(url: str) -> None:
    """B12: accepted URLs also parse to the expected owner/video pair."""
    extractor = VKVideoExtractor()
    owner_id, video_id = extractor.parse_video_id(url)
    assert owner_id == "12345"
    assert video_id == "67890"


@pytest.mark.parametrize("url", _REJECT_URLS)
def test_video_url_rejection_table_parse(url: str) -> None:
    """B12: rejected URLs raise InvalidVideoUrlError from parse_video_id."""
    extractor = VKVideoExtractor()
    with pytest.raises(InvalidVideoUrlError, match="Invalid VK video URL"):
        extractor.parse_video_id(url)


class TestExtractionErrors:
    """Tests for extraction exception raising behavior."""

    @pytest.mark.asyncio
    async def test_extract_streams_no_streams_raises_video_not_found(self) -> None:
        """Test extract_streams raises VideoNotFoundError when no streams are found."""
        extractor = VKVideoExtractor()

        with patch.object(extractor, "_extract_with_ytdlp", return_value=([], None)):
            with pytest.raises(VideoNotFoundError, match="No streams found"):
                await extractor.extract_streams("https://vkvideo.ru/video-12345_67890")

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_no_streams_raises_video_not_found(self) -> None:
        """Test extract_streams_with_cookies raises VideoNotFoundError when no streams found."""
        # Use BROWSER cookie_source to test browser extraction path
        settings = Settings(cookie_source=CookieSource.BROWSER)
        extractor = VKVideoExtractor(settings=settings)

        with patch.object(extractor, "_extract_with_browser", return_value=([], None, None)):
            with pytest.raises(VideoNotFoundError, match="No streams found"):
                await extractor.extract_streams_with_cookies("https://vkvideo.ru/video-12345_67890")

    @pytest.mark.asyncio
    async def test_extract_with_ytdlp_no_info_raises_extraction_error(self) -> None:
        """Test _extract_with_ytdlp raises ExtractionError when no video info extracted."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"

        # Mock the internal sync function to simulate no info returned
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = mock_ydl_class.return_value.__enter__.return_value
            mock_ydl.extract_info.return_value = None

            with pytest.raises(ExtractionError, match="No video info extracted"):
                await extractor._extract_with_ytdlp(url, "12345_67890")

    @pytest.mark.asyncio
    async def test_extract_with_ytdlp_ssl_verify_default_true(self) -> None:
        """Test _extract_with_ytdlp passes nocheckcertificate=False when ssl_verify is True (default)."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = mock_ydl_class.return_value.__enter__.return_value
            mock_ydl.extract_info.return_value = {"title": "Test", "formats": []}

            await extractor._extract_with_ytdlp(url, "12345_67890")

            ydl_opts = mock_ydl_class.call_args[0][0]
            assert ydl_opts["nocheckcertificate"] is False

    @pytest.mark.asyncio
    async def test_extract_with_ytdlp_no_ssl_verify_sets_nocheckcertificate(self) -> None:
        """Test _extract_with_ytdlp passes nocheckcertificate=True when ssl_verify is False."""
        settings = Settings(ssl_verify=False)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = mock_ydl_class.return_value.__enter__.return_value
            mock_ydl.extract_info.return_value = {"title": "Test", "formats": []}

            await extractor._extract_with_ytdlp(url, "12345_67890")

            ydl_opts = mock_ydl_class.call_args[0][0]
            assert ydl_opts["nocheckcertificate"] is True

    @pytest.mark.asyncio
    async def test_extract_with_ytdlp_propagates_settings_to_ydl_opts(self) -> None:
        """Settings fields are propagated to yt-dlp ydl_opts."""
        settings = Settings(max_retries=5, download_timeout=600, throttled_rate=50000)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = mock_ydl_class.return_value.__enter__.return_value
            mock_ydl.extract_info.return_value = {"title": "Test", "formats": []}

            await extractor._extract_with_ytdlp(url, "12345_67890")

            ydl_opts = mock_ydl_class.call_args[0][0]
            assert ydl_opts["socket_timeout"] == 600
            assert ydl_opts["retries"] == 5
            assert ydl_opts["fragment_retries"] == 5
            assert ydl_opts["throttled_rate"] == 50000

    @pytest.mark.asyncio
    async def test_extract_with_ytdlp_timeout_raises_extraction_error(self) -> None:
        """asyncio.wait_for timeout raises ExtractionError."""
        settings = Settings(download_timeout=30)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        # Mock asyncio.wait_for to raise TimeoutError, simulating a hang
        # in the yt-dlp extraction thread.
        async def fake_wait_for(coro: object, timeout: float | None) -> tuple[list[Any], None]:
            raise TimeoutError("simulated timeout")

        with patch("asyncio.wait_for", side_effect=fake_wait_for):
            with patch("asyncio.get_running_loop"):
                with pytest.raises(ExtractionError, match="timed out"):
                    await extractor._extract_with_ytdlp(url, "12345_67890")

    def test_format_cookies_for_ffmpeg(self) -> None:
        """Test _format_cookies_for_ffmpeg correctly formats cookies for ffmpeg header."""
        extractor = VKVideoExtractor()

        # Test with single cookie
        cookies = [{"name": "session_id", "value": "abc123"}]
        result = extractor._format_cookies_for_ffmpeg(cookies)
        assert result == "session_id=abc123"

        # Test with multiple cookies
        cookies = [
            {"name": "session_id", "value": "abc123"},
            {"name": "user_token", "value": "xyz789"},
        ]
        result = extractor._format_cookies_for_ffmpeg(cookies)
        assert "session_id=abc123" in result
        assert "user_token=xyz789" in result
        assert "; " in result

        # Test with empty cookies list
        result = extractor._format_cookies_for_ffmpeg([])
        assert result == ""

        # Test with cookies with empty name/value (includes them as-is)
        cookies = [{"name": "", "value": "val"}, {"name": "name", "value": ""}]
        result = extractor._format_cookies_for_ffmpeg(cookies)
        assert "=val; name=" == result

        # Test CRLF sanitization - prevents header injection
        cookies = [{"name": "session\nmalicious", "value": "abc\r123"}]
        result = extractor._format_cookies_for_ffmpeg(cookies)
        assert "\n" not in result
        assert "\r" not in result
        assert "sessionmalicious" in result
        assert "abc123" in result

        # Test CRLF in both name and value
        cookies = [{"name": "bad\r\nname", "value": "val\nue\r\n"}]
        result = extractor._format_cookies_for_ffmpeg(cookies)
        assert "\r" not in result
        assert "\n" not in result
        assert "badname" in result
        assert "value" in result

    def test_format_cookies_for_ffmpeg_all_cookies_included(self) -> None:
        """Test that _format_cookies_for_ffmpeg includes all cookies without truncation."""
        extractor = VKVideoExtractor()

        # Create 50 cookies to verify no limit
        cookies = [{"name": f"c{i}", "value": f"v{i}"} for i in range(50)]
        result = extractor._format_cookies_for_ffmpeg(cookies)

        # All cookies should be present (no 20-cookie truncation)
        assert result.count("=") == 50  # 50 cookies
        assert "c49=v49" in result  # Last cookie should be present

    def test_format_cookies_for_ffmpeg_keeps_cookies_from_every_domain(self) -> None:
        """SEC-010 / B8: this test PINS CURRENT BEHAVIOUR, which is the point of it.

        A cookie set spanning several domains is formatted into one flat header
        with no per-domain filtering, because no consumer has been able to state
        that the media host needs a cookie set for a domain other than its own (§9 Q3, Alt A).
        The harvest is bounded instead: BrowserManager.create_stealth_page uses
        new_context(...) with no storage_state / launch_persistent_context /
        user_data_dir, so the store holds only what this run's page visit set.

        If a future change filters by domain this test is SUPPOSED to fail. Do
        not "fix" it by narrowing the fixture or relaxing the assertion: the
        failure is the signal that a decision changed, and it must be made
        deliberately. Two consumers already scope by domain on their own
        (services/cookies.py::_cookies_to_netscape preserves each cookie's own
        domain for the yt-dlp --cookies file), so narrowing the flat header
        would change only the aiohttp segment path — and it could not be
        validated without a live run.

        See VKVideoExtractor._format_cookies_for_ffmpeg, the seam this pins.
        """
        extractor = VKVideoExtractor()
        cookies: list[Cookie] = [
            {"name": "session_id", "value": "abc123", "domain": ".vkvideo.ru"},
            {"name": "remixdsid", "value": "xyz789", "domain": ".vkvideo.ru"},
            {"name": "tracker", "value": "track-me", "domain": ".userapi.com"},
            {"name": "sid", "value": "cross-site", "domain": ".example.com"},
        ]

        result = extractor._format_cookies_for_ffmpeg(cookies)

        # Every cookie survives, regardless of domain: no filter exists here.
        assert result == ("session_id=abc123; remixdsid=xyz789; tracker=track-me; sid=cross-site")
        # The domain never reaches the header at all - which is why the filter,
        # if one is ever added, belongs in this function and nowhere upstream.
        assert "vkvideo" not in result
        assert "userapi" not in result
        assert "example" not in result

    def test_cookies_to_netscape_preserves_domain(self) -> None:
        """Test that _cookies_to_netscape preserves cookie domains from Cookie objects."""
        cookies = [
            {"name": "session", "value": "abc", "domain": ".vk.com"},
            {"name": "token", "value": "xyz", "domain": ".userapi.com"},
            {"name": "user", "value": "123", "domain": "vkvideo.ru"},
        ]
        result = _cookies_to_netscape(cookies)

        # Verify each cookie has its correct domain preserved
        assert ".vk.com" in result
        assert ".userapi.com" in result
        assert "vkvideo.ru" in result
        # The hardcoded ".vkvideo.ru" should NOT be used for all cookies
        lines = result.split("\n")
        cookie_lines = [line for line in lines if "\t" in line and not line.startswith("#")]
        assert len(cookie_lines) == 3

    def test_cookies_to_netscape_backward_compatible(self) -> None:
        """Test that _cookies_to_netscape still works with string input (backward compat)."""
        cookies = "vk=abc123; session=xyz789"
        result = _cookies_to_netscape(cookies)

        # Should use hardcoded domain for backward compatibility
        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tvk\tabc123" in result
        assert ".vkvideo.ru\tTRUE\t/\tFALSE\t0\tsession\txyz789" in result

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_success(self) -> None:
        """Test extract_streams_with_cookies returns streams and formatted cookies."""
        # Use BROWSER cookie_source to test browser extraction path
        settings = Settings(cookie_source=CookieSource.BROWSER)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        raw_cookies = [
            {"name": "session_id", "value": "abc123", "domain": ".vkvideo.ru"},
            {"name": "user_token", "value": "xyz789", "domain": ".vkvideo.ru"},
        ]
        with patch.object(
            extractor,
            "_extract_with_browser",
            return_value=([mock_stream], "session_id=abc123; user_token=xyz789", raw_cookies),
        ):
            streams, cookies, raw = await extractor.extract_streams_with_cookies(url)

            assert len(streams) == 1
            assert streams[0].format == StreamFormat.HLS
            assert "session_id=abc123" in cookies
            assert "user_token=xyz789" in cookies
            assert raw is not None
            assert len(raw) == 2

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_none_skips_browser(self) -> None:
        """Test extract_streams_with_cookies skips browser when cookie_source=NONE."""
        # Default cookie_source is NONE
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        with patch.object(
            extractor,
            "_extract_with_ytdlp",
            return_value=([mock_stream], None),
        ):
            streams, cookies, raw = await extractor.extract_streams_with_cookies(url)

            assert len(streams) == 1
            assert cookies is None
            assert raw is None  # No cookies when cookie_source=NONE

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_force_browser(self) -> None:
        """Test extract_streams_with_cookies forces browser launch with force_browser=True."""
        settings = Settings(cookie_source=CookieSource.NONE)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        raw_cookies = [{"name": "forced", "value": "cookies", "domain": ".vkvideo.ru"}]
        with patch.object(
            extractor,
            "_extract_with_browser",
            return_value=([mock_stream], "forced_cookies", raw_cookies),
        ):
            streams, cookies, raw = await extractor.extract_streams_with_cookies(
                url, force_browser=True
            )

            assert len(streams) == 1
            assert cookies == "forced_cookies"  # Cookies returned when forced
            assert raw is not None

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_invalid_url(self) -> None:
        """Test extract_streams raises InvalidVideoUrlError for invalid URL format."""
        extractor = VKVideoExtractor()
        invalid_url = "https://example.com/invalid"

        with pytest.raises(InvalidVideoUrlError, match="Invalid VK video URL"):
            await extractor.extract_streams(invalid_url)

        with pytest.raises(InvalidVideoUrlError, match="Invalid VK video URL"):
            await extractor.extract_streams_with_cookies(invalid_url)

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_none_mode(self) -> None:
        """Test that browser is not launched when cookie_source=NONE."""
        settings = Settings(cookie_source=CookieSource.NONE)
        extractor = VKVideoExtractor(settings=settings)

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        with patch.object(
            extractor, "_extract_with_ytdlp", return_value=([mock_stream], None)
        ) as mock_extract:
            streams, cookies, raw = await extractor.extract_streams_with_cookies(
                "https://vkvideo.ru/video-1_2"
            )

            mock_extract.assert_called_once()
            assert cookies is None

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_browser_mode(self) -> None:
        """Test that browser is launched when cookie_source=BROWSER."""
        settings = Settings(cookie_source=CookieSource.BROWSER)
        extractor = VKVideoExtractor(settings=settings)

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        raw_cookies = [{"name": "test", "value": "cookie", "domain": ".vkvideo.ru"}]
        with patch.object(
            extractor, "_extract_with_browser", return_value=([mock_stream], "cookies", raw_cookies)
        ) as mock_browser:
            streams, cookies, raw = await extractor.extract_streams_with_cookies(
                "https://vkvideo.ru/video-1_2"
            )

            mock_browser.assert_called_once()
            assert cookies == "cookies"

    @pytest.mark.asyncio
    async def test_extract_streams_title_populated(self) -> None:
        """Test extract_streams returns VideoWithStreams with populated title."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"
        mock_stream = Stream(
            url="https://example.com/video.m3u8", format=StreamFormat.HLS, quality="720"
        )

        with patch.object(
            extractor,
            "_extract_with_ytdlp",
            return_value=([mock_stream], "Test Video Title"),
        ):
            result = await extractor.extract_streams(url)

            assert result.title == "Test Video Title"
            assert result.id == "12345_67890"
            assert len(result.streams) == 1

    @pytest.mark.asyncio
    async def test_extract_streams_title_fallback_to_fulltitle(self) -> None:
        """Test extract_streams uses fulltitle when title is not available."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"
        mock_stream = Stream(
            url="https://example.com/video.m3u8", format=StreamFormat.HLS, quality="720"
        )

        with patch.object(
            extractor,
            "_extract_with_ytdlp",
            return_value=([mock_stream], "Full Video Title"),
        ):
            result = await extractor.extract_streams(url)

            assert result.title == "Full Video Title"

    @pytest.mark.asyncio
    async def test_extract_streams_title_none_when_unavailable(self) -> None:
        """Test extract_streams handles None title gracefully."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"
        mock_stream = Stream(
            url="https://example.com/video.m3u8", format=StreamFormat.HLS, quality="720"
        )

        with patch.object(
            extractor,
            "_extract_with_ytdlp",
            return_value=([mock_stream], None),
        ):
            result = await extractor.extract_streams(url)

            assert result.title is None
            assert result.id == "12345_67890"

    @pytest.mark.asyncio
    async def test_extract_with_browser_goto_failure_raises_extraction_error(self) -> None:
        """Test _extract_with_browser wraps Playwright navigation failure in ExtractionError."""
        settings = Settings(cookie_source=CookieSource.BROWSER)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        mock_page = MagicMock()
        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))

        mock_browser = AsyncMock()
        mock_browser.create_stealth_page = AsyncMock(return_value=mock_page)

        mock_browser_manager = MagicMock()
        mock_browser_manager.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_browser_manager.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "vkdownloader.services.extractor.BrowserManager",
            return_value=mock_browser_manager,
        ):
            with pytest.raises(ExtractionError, match="Failed to navigate to video page"):
                await extractor._extract_with_browser(url, "12345_67890")


class TestBuildStreams:
    """Unit tests for the _build_streams format-selection oracle (D-12)."""

    def test_build_streams_excludes_audio_only_formats(self) -> None:
        """D-12: audio-only formats (vcodec 'none') are excluded; video-bearing keep input order."""
        formats = [
            {"vcodec": "none", "url": "https://example.com/audio.mp4", "height": 0},
            {
                "vcodec": "h264",
                "url": "https://example.com/720.mp4",
                "height": 720,
                "width": 1280,
                "tbr": 2500,
            },
            {
                "vcodec": "h264",
                "url": "https://example.com/1080.mp4",
                "height": 1080,
                "width": 1920,
                "tbr": 5000,
            },
        ]

        streams = _build_streams(formats)

        assert len(streams) == 2
        assert streams[0].height == 720
        assert streams[1].height == 1080

    def test_build_streams_detects_hls_format(self) -> None:
        """D-12: a URL containing .m3u8 maps to StreamFormat.HLS."""
        formats = [
            {"vcodec": "h264", "url": "https://example.com/stream.m3u8", "height": 720},
        ]

        streams = _build_streams(formats)

        assert len(streams) == 1
        assert streams[0].format == StreamFormat.HLS

    def test_build_streams_detects_mp4_format(self) -> None:
        """D-12: a plain progressive URL maps to StreamFormat.MP4."""
        formats = [
            {"vcodec": "h264", "url": "https://example.com/video.mp4", "height": 720},
        ]

        streams = _build_streams(formats)

        assert len(streams) == 1
        assert streams[0].format == StreamFormat.MP4

    def test_build_streams_quality_with_height(self) -> None:
        """D-12: a present height yields quality '720p' and height 720."""
        formats = [
            {"vcodec": "h264", "url": "https://example.com/720.mp4", "height": 720},
        ]

        streams = _build_streams(formats)

        assert streams[0].quality == "720p"
        assert streams[0].height == 720

    def test_build_streams_quality_unknown_without_height(self) -> None:
        """D-12: an absent height yields quality 'unknown' and height None."""
        formats = [
            {"vcodec": "h264", "url": "https://example.com/idx.mp4"},
        ]

        streams = _build_streams(formats)

        assert streams[0].quality == "unknown"
        assert streams[0].height is None

    def test_build_streams_resolution_both_dimensions(self) -> None:
        """D-12: present width and height yield resolution '1920x1080'."""
        formats = [
            {
                "vcodec": "h264",
                "url": "https://example.com/1080.mp4",
                "width": 1920,
                "height": 1080,
            },
        ]

        streams = _build_streams(formats)

        assert streams[0].resolution == "1920x1080"

    def test_build_streams_resolution_partial_dimensions(self) -> None:
        """D-12: width-only or height-only dimensions yield resolution None."""
        width_only = [
            {"vcodec": "h264", "url": "https://example.com/w.mp4", "width": 1280},
        ]
        height_only = [
            {"vcodec": "h264", "url": "https://example.com/h.mp4", "height": 720},
        ]

        assert _build_streams(width_only)[0].resolution is None
        assert _build_streams(height_only)[0].resolution is None

    def test_build_streams_bitrate_present(self) -> None:
        """D-12: a present tbr yields bitrate 2500."""
        formats = [
            {
                "vcodec": "h264",
                "url": "https://example.com/720.mp4",
                "height": 720,
                "tbr": 2500,
            },
        ]

        streams = _build_streams(formats)

        assert streams[0].bitrate == 2500

    def test_build_streams_bitrate_absent_or_zero(self) -> None:
        """D-12: absent or zero tbr yields bitrate None."""
        absent = [
            {"vcodec": "h264", "url": "https://example.com/a.mp4", "height": 720},
        ]
        zero = [
            {
                "vcodec": "h264",
                "url": "https://example.com/b.mp4",
                "height": 720,
                "tbr": 0,
            },
        ]

        assert _build_streams(absent)[0].bitrate is None
        assert _build_streams(zero)[0].bitrate is None

    def test_build_streams_excludes_falsy_url(self) -> None:
        """D-12: a format with a falsy/empty URL is excluded."""
        formats = [
            {"vcodec": "h264", "url": "", "height": 720},
            {"vcodec": "h264", "url": None, "height": 1080},
            {"vcodec": "h264", "url": "https://example.com/ok.mp4", "height": 480},
        ]

        streams = _build_streams(formats)

        assert len(streams) == 1
        assert streams[0].url == "https://example.com/ok.mp4"

    def test_build_streams_empty_list_yields_empty(self) -> None:
        """D-12: an empty format list yields no streams."""
        assert _build_streams([]) == []

    @pytest.mark.asyncio
    async def test_build_streams_none_formats_yields_empty(self) -> None:
        """D-12: None formats in extract_info yields an empty stream list via the production path."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"
        info = {"title": "Test Video", "formats": None}

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = mock_ydl_class.return_value.__enter__.return_value
            mock_ydl.extract_info.return_value = info

            streams, title = await extractor._extract_with_ytdlp(url, "12345_67890")

        assert title == "Test Video"
        assert streams == []

    @pytest.mark.asyncio
    async def test_build_streams_reached_via_extract_with_ytdlp(self) -> None:
        """D-12: _extract_with_ytdlp reaches _build_streams through patched YoutubeDL.extract_info."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"
        info = {
            "title": "Test Video",
            "formats": [
                {"vcodec": "none", "url": "https://example.com/audio.mp4"},
                {
                    "vcodec": "h264",
                    "url": "https://example.com/stream.m3u8",
                    "height": 720,
                    "width": 1280,
                    "tbr": 2500,
                },
                {
                    "vcodec": "h264",
                    "url": "https://example.com/prog.mp4",
                    "height": 1080,
                    "width": 1920,
                    "tbr": 5000,
                },
            ],
        }

        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = mock_ydl_class.return_value.__enter__.return_value
            mock_ydl.extract_info.return_value = info

            streams, title = await extractor._extract_with_ytdlp(url, "12345_67890")

        assert title == "Test Video"
        assert len(streams) == 2
        assert streams[0].format == StreamFormat.HLS
        assert streams[0].quality == "720p"
        assert streams[0].height == 720
        assert streams[0].bitrate == 2500
        assert streams[0].resolution == "1280x720"
        assert streams[1].format == StreamFormat.MP4
        assert streams[1].quality == "1080p"
        assert streams[1].height == 1080
        assert streams[1].bitrate == 5000
        assert streams[1].resolution == "1920x1080"

    def test_build_streams_classifies_mp4_when_m3u8_in_query(self) -> None:
        """NET-017: a progressive URL whose query carries .m3u8 is MP4, not HLS."""
        formats = [
            {
                "vcodec": "h264",
                "url": "https://c/v.mp4?src=https://x/a.m3u8&t=1",
                "height": 720,
            },
        ]

        streams = _build_streams(formats)

        assert len(streams) == 1
        assert streams[0].format == StreamFormat.MP4

    def test_build_streams_classifies_mp4_when_m3u8_is_directory_name(self) -> None:
        """NET-017: a .m3u8 directory in the path does not make a progressive URL HLS."""
        formats = [
            {
                "vcodec": "h264",
                "url": "https://c/v.m3u8/720/v.mp4",
                "height": 720,
            },
        ]

        streams = _build_streams(formats)

        assert len(streams) == 1
        assert streams[0].format == StreamFormat.MP4

    def test_build_streams_classifies_hls_by_path_suffix_only(self) -> None:
        """NET-017: a true .m3u8 path suffix is HLS even when .mp4 appears in the query."""
        formats = [
            {
                "vcodec": "h264",
                "url": "https://c/s.m3u8?x=1.mp4",
                "height": 720,
            },
        ]

        streams = _build_streams(formats)

        assert len(streams) == 1
        assert streams[0].format == StreamFormat.HLS

    def test_build_streams_excludes_record_without_vcodec(self) -> None:
        """NET-017: a record that omits vcodec is indeterminate and not offered."""
        formats = [
            {"url": "https://example.com/video.mp4", "height": 720, "width": 1280},
        ]

        streams = _build_streams(formats)

        assert streams == []


def _browser_settings() -> Settings:
    """Build Settings for the browser-extraction oracle with both interaction waits at 0.

    ``browser_pre_interaction_wait`` and ``browser_post_interaction_wait`` are declared
    with ``ge=1``, so a zero wait cannot be passed to the constructor. They are zeroed
    on the built instance instead, which keeps the two awaited ``asyncio.sleep`` calls
    inside ``_extract_with_browser`` instant and the outcome independent of wall-clock
    timing. Every value that matters is still supplied explicitly, so the ``.env`` file
    resolved from the working directory cannot influence the result.
    """
    settings = Settings(
        cookie_source=CookieSource.BROWSER,
        browser_pre_interaction_wait=1,
        browser_post_interaction_wait=1,
    )
    settings.browser_pre_interaction_wait = 0
    settings.browser_post_interaction_wait = 0
    return settings


def _mock_browser_page(cookies: list[Cookie]) -> MagicMock:
    """Build a mock Playwright page that navigates successfully and returns ``cookies``."""
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    page.context.cookies = AsyncMock(return_value=cookies)
    return page


def _mock_browser_manager(page: MagicMock) -> MagicMock:
    """Build a mock ``BrowserManager`` context manager whose ``__aenter__`` yields ``page``."""
    browser = MagicMock()
    browser.create_stealth_page = AsyncMock(return_value=page)
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(return_value=browser)
    manager.__aexit__ = AsyncMock(return_value=None)
    return manager


def _mock_network_monitor(m3u8_urls: list[str]) -> MagicMock:
    """Build a mock ``NetworkMonitor`` reporting exactly ``m3u8_urls``."""
    monitor = MagicMock()
    monitor.m3u8_urls = m3u8_urls
    monitor.select.return_value = list(m3u8_urls)
    return monitor


class TestExtractWithBrowser:
    """Outcome oracles for the browser extraction body of _extract_with_browser (D-12)."""

    @pytest.mark.asyncio
    async def test_browser_extraction_captures_cookies(self) -> None:
        """D-12: browser cookies reach the caller both raw and as the ffmpeg cookie header."""
        extractor = VKVideoExtractor(settings=_browser_settings())
        url = "https://vkvideo.ru/video-12345_67890"
        cookies: list[Cookie] = [
            {"name": "session_id", "value": "abc123", "domain": ".vkvideo.ru"},
            {"name": "remixdsid", "value": "xyz789", "domain": ".vkvideo.ru"},
        ]
        page = _mock_browser_page(cookies)

        with (
            patch(
                "vkdownloader.services.extractor.BrowserManager",
                return_value=_mock_browser_manager(page),
            ),
            patch(
                "vkdownloader.services.extractor.NetworkMonitor",
                return_value=_mock_network_monitor([]),
            ),
            patch.object(extractor, "_simulate_video_interaction", new_callable=AsyncMock),
        ):
            _, cookies_str, raw_cookies = await extractor._extract_with_browser(url, "12345_67890")

        assert raw_cookies == cookies
        assert cookies_str is not None
        assert "session_id=abc123" in cookies_str
        assert "remixdsid=xyz789" in cookies_str
        assert cookies_str.count("=") == 2

    @pytest.mark.asyncio
    async def test_browser_extraction_survives_cookie_capture_failure(self) -> None:
        """D-12: a failing cookie capture is contained; the m3u8 stream is still returned."""
        extractor = VKVideoExtractor(settings=_browser_settings())
        url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://cdn.example.com/video.m3u8"
        page = _mock_browser_page([])
        page.context.cookies.side_effect = RuntimeError("browser context closed")

        with (
            patch(
                "vkdownloader.services.extractor.BrowserManager",
                return_value=_mock_browser_manager(page),
            ),
            patch(
                "vkdownloader.services.extractor.NetworkMonitor",
                return_value=_mock_network_monitor([m3u8_url]),
            ),
            patch.object(extractor, "_simulate_video_interaction", new_callable=AsyncMock),
        ):
            streams, cookies_str, raw_cookies = await extractor._extract_with_browser(
                url, "12345_67890"
            )

        assert raw_cookies is None
        assert cookies_str is None
        assert [stream.url for stream in streams] == [m3u8_url]

    @pytest.mark.asyncio
    async def test_browser_extraction_uses_first_m3u8_url(self) -> None:
        """D-12: only the first captured m3u8 URL becomes an HLS stream with no height."""
        extractor = VKVideoExtractor(settings=_browser_settings())
        url = "https://vkvideo.ru/video-12345_67890"
        first_url = "https://cdn.example.com/first.m3u8"
        second_url = "https://cdn.example.com/second.m3u8"
        page = _mock_browser_page([])

        with (
            patch(
                "vkdownloader.services.extractor.BrowserManager",
                return_value=_mock_browser_manager(page),
            ),
            patch(
                "vkdownloader.services.extractor.NetworkMonitor",
                return_value=_mock_network_monitor([first_url, second_url]),
            ),
            patch.object(extractor, "_simulate_video_interaction", new_callable=AsyncMock),
        ):
            streams, _, _ = await extractor._extract_with_browser(url, "12345_67890")

        assert len(streams) == 1
        assert streams[0].url == first_url
        assert second_url not in [stream.url for stream in streams]
        assert streams[0].format is StreamFormat.HLS
        assert streams[0].height is None
        # Removed-stamp oracle (B7): browser stream quality is stamped
        # QualityLabel.UNKNOWN.value, not the old literal "best".
        assert streams[0].quality == QualityLabel.UNKNOWN.value

    @pytest.mark.asyncio
    async def test_browser_extraction_respects_shutdown_event(self) -> None:
        """D-12: a set shutdown event cancels extraction before any cookie is read."""
        extractor = VKVideoExtractor(settings=_browser_settings())
        url = "https://vkvideo.ru/video-12345_67890"
        page = _mock_browser_page([])

        # The shutdown Event is loop-bound, so a fresh one is injected and the previous
        # ContextVar state is restored on the way out: a set Event never leaks to others.
        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()

            with (
                patch(
                    "vkdownloader.services.extractor.BrowserManager",
                    return_value=_mock_browser_manager(page),
                ),
                patch(
                    "vkdownloader.services.extractor.NetworkMonitor",
                    return_value=_mock_network_monitor(["https://cdn.example.com/video.m3u8"]),
                ),
                patch.object(extractor, "_simulate_video_interaction", new_callable=AsyncMock),
            ):
                with pytest.raises(asyncio.CancelledError):
                    await extractor._extract_with_browser(url, "12345_67890")

            page.context.cookies.assert_not_awaited()
        finally:
            _shutdown_event_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_browser_extraction_without_m3u8_urls_returns_no_streams(self) -> None:
        """D-12: no captured m3u8 URL yields an empty stream list, which the caller rejects."""
        extractor = VKVideoExtractor(settings=_browser_settings())
        url = "https://vkvideo.ru/video-12345_67890"
        cookies: list[Cookie] = [
            {"name": "session_id", "value": "abc123", "domain": ".vkvideo.ru"},
        ]
        page = _mock_browser_page(cookies)

        with (
            patch(
                "vkdownloader.services.extractor.BrowserManager",
                return_value=_mock_browser_manager(page),
            ),
            patch(
                "vkdownloader.services.extractor.NetworkMonitor",
                return_value=_mock_network_monitor([]),
            ),
            patch.object(extractor, "_simulate_video_interaction", new_callable=AsyncMock),
        ):
            streams, cookies_str, raw_cookies = await extractor._extract_with_browser(
                url, "12345_67890"
            )

        assert streams == []
        assert raw_cookies == cookies
        assert cookies_str == "session_id=abc123"
