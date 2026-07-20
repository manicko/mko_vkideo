"""Tests for VKVideoExtractor service."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from vkdownloader.config import Settings
from vkdownloader.exceptions import ExtractionError, VideoNotFoundError
from vkdownloader.models.enums import CookieSource, StreamFormat
from vkdownloader.models.video import Stream
from vkdownloader.services.cookies import _cookies_to_netscape
from vkdownloader.services.extractor import VKVideoExtractor


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
    """Test parse_video_id raises ValueError for invalid URL."""
    extractor = VKVideoExtractor()
    invalid_url = "https://example.com/invalid"

    with pytest.raises(ValueError, match="Invalid VK video URL"):
        extractor.parse_video_id(invalid_url)


def test_parse_video_id_empty_string() -> None:
    """Test parse_video_id raises ValueError for empty string."""
    extractor = VKVideoExtractor()

    with pytest.raises(ValueError, match="Invalid VK video URL"):
        extractor.parse_video_id("")


class TestExtractionErrors:
    """Tests for extraction exception raising behavior."""

    @pytest.mark.asyncio
    async def test_extract_streams_no_streams_raises_video_not_found(self) -> None:
        """Test extract_streams raises VideoNotFoundError when no streams are found."""
        extractor = VKVideoExtractor()

        with patch.object(
            extractor, "_extract_with_ytdlp", return_value=([], None)
        ):
            with pytest.raises(VideoNotFoundError, match="No streams found"):
                await extractor.extract_streams("https://vkvideo.ru/video-12345_67890")

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_no_streams_raises_video_not_found(self) -> None:
        """Test extract_streams_with_cookies raises VideoNotFoundError when no streams found."""
        # Use BROWSER cookie_source to test browser extraction path
        settings = Settings(cookie_source=CookieSource.BROWSER)
        extractor = VKVideoExtractor(settings=settings)

        with patch.object(
            extractor, "_extract_with_browser", return_value=([], None, None)
        ):
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
    async def test_format_cookies_for_ffmpeg(self) -> None:
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

    @pytest.mark.asyncio
    async def test_format_cookies_for_ffmpeg_all_cookies_included(self) -> None:
        """Test that _format_cookies_for_ffmpeg includes all cookies without truncation."""
        extractor = VKVideoExtractor()

        # Create 50 cookies to verify no limit
        cookies = [{"name": f"c{i}", "value": f"v{i}"} for i in range(50)]
        result = extractor._format_cookies_for_ffmpeg(cookies)

        # All cookies should be present (no 20-cookie truncation)
        assert result.count("=") == 50  # 50 cookies
        assert "c49=v49" in result  # Last cookie should be present

    @pytest.mark.asyncio
    async def test_cookies_to_netscape_preserves_domain(self) -> None:
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

    @pytest.mark.asyncio
    async def test_cookies_to_netscape_backward_compatible(self) -> None:
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
            streams, cookies, raw = await extractor.extract_streams_with_cookies(url, force_browser=True)

            assert len(streams) == 1
            assert cookies == "forced_cookies"  # Cookies returned when forced
            assert raw is not None

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_file_mode_raises_validation_error(self) -> None:
        """Test that Settings rejects CookieSource.FILE at construction (not implemented)."""
        # Creating Settings with FILE cookie_source raises ValidationError
        with pytest.raises(ValidationError) as exc_info:
            Settings(cookie_source=CookieSource.FILE)
        assert "CookieSource.FILE is not implemented" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_invalid_url(self) -> None:
        """Test extract_streams raises ValueError for invalid URL format."""
        extractor = VKVideoExtractor()
        invalid_url = "https://example.com/invalid"

        with pytest.raises(ValueError, match="Invalid VK video URL"):
            await extractor.extract_streams(invalid_url)

        with pytest.raises(ValueError, match="Invalid VK video URL"):
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
            streams, cookies, raw = await extractor.extract_streams_with_cookies("https://vkvideo.ru/video-1_2")

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
            streams, cookies, raw = await extractor.extract_streams_with_cookies("https://vkvideo.ru/video-1_2")

            mock_browser.assert_called_once()
            assert cookies == "cookies"

    @pytest.mark.asyncio
    async def test_extract_streams_title_populated(self) -> None:
        """Test extract_streams returns VideoWithStreams with populated title."""
        extractor = VKVideoExtractor()
        url = "https://vkvideo.ru/video-12345_67890"
        mock_stream = Stream(url="https://example.com/video.m3u8", format=StreamFormat.HLS, quality="720")

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
        mock_stream = Stream(url="https://example.com/video.m3u8", format=StreamFormat.HLS, quality="720")

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
        mock_stream = Stream(url="https://example.com/video.m3u8", format=StreamFormat.HLS, quality="720")

        with patch.object(
            extractor,
            "_extract_with_ytdlp",
            return_value=([mock_stream], None),
        ):
            result = await extractor.extract_streams(url)

            assert result.title is None
            assert result.id == "12345_67890"
