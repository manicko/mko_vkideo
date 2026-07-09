"""Tests for VKVideoExtractor service."""

from unittest.mock import patch

import pytest

from vkdownloader.exceptions import ExtractionError, VideoNotFoundError
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
        extractor = VKVideoExtractor()

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
