"""Tests for VKVideoExtractor service."""

from unittest.mock import MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import ExtractionError, VideoNotFoundError
from vkdownloader.models.enums import CookieSource, StreamFormat
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
            extractor, "_extract_with_ytdlp", return_value=[]
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
            extractor, "_extract_with_browser", return_value=([], None)
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

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_success(self) -> None:
        """Test extract_streams_with_cookies returns streams and formatted cookies."""
        # Use BROWSER cookie_source to test browser extraction path
        settings = Settings(cookie_source=CookieSource.BROWSER)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        with patch.object(
            extractor,
            "_extract_with_browser",
            return_value=([mock_stream], "session_id=abc123; user_token=xyz789"),
        ):
            streams, cookies = await extractor.extract_streams_with_cookies(url)

            assert len(streams) == 1
            assert streams[0].format == StreamFormat.HLS
            assert "session_id=abc123" in cookies
            assert "user_token=xyz789" in cookies

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
            return_value=[mock_stream],
        ):
            streams, cookies = await extractor.extract_streams_with_cookies(url)

            assert len(streams) == 1
            assert cookies is None  # No cookies when cookie_source=NONE

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_force_browser(self) -> None:
        """Test extract_streams_with_cookies forces browser launch with force_browser=True."""
        settings = Settings(cookie_source=CookieSource.NONE)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        with patch.object(
            extractor,
            "_extract_with_browser",
            return_value=([mock_stream], "forced_cookies"),
        ):
            streams, cookies = await extractor.extract_streams_with_cookies(url, force_browser=True)

            assert len(streams) == 1
            assert cookies == "forced_cookies"  # Cookies returned when forced

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_file_mode(self) -> None:
        """Test extract_streams_with_cookies returns streams without cookies for FILE mode."""
        settings = Settings(cookie_source=CookieSource.FILE)
        extractor = VKVideoExtractor(settings=settings)
        url = "https://vkvideo.ru/video-12345_67890"

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        with patch.object(
            extractor,
            "_extract_with_ytdlp",
            return_value=[mock_stream],
        ):
            streams, cookies = await extractor.extract_streams_with_cookies(url)

            assert len(streams) == 1
            assert cookies is None  # No cookies for FILE mode (placeholder)

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
            extractor, "_extract_with_ytdlp", return_value=[mock_stream]
        ) as mock_extract:
            streams, cookies = await extractor.extract_streams_with_cookies("https://vkvideo.ru/video-1_2")

            mock_extract.assert_called_once()
            assert cookies is None

    @pytest.mark.asyncio
    async def test_extract_streams_with_cookies_browser_mode(self) -> None:
        """Test that browser is launched when cookie_source=BROWSER."""
        settings = Settings(cookie_source=CookieSource.BROWSER)
        extractor = VKVideoExtractor(settings=settings)

        mock_stream = MagicMock()
        mock_stream.format = StreamFormat.HLS

        with patch.object(
            extractor, "_extract_with_browser", return_value=([mock_stream], "cookies")
        ) as mock_browser:
            streams, cookies = await extractor.extract_streams_with_cookies("https://vkvideo.ru/video-1_2")

            mock_browser.assert_called_once()
            assert cookies == "cookies"
