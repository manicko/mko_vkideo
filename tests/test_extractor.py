"""Tests for VKVideoExtractor service."""

import pytest

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
