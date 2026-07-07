"""Tests for QualitySelector service."""

import pytest

from vkdownloader.models.enums import QualityEnum, StreamFormat
from vkdownloader.models.video import Stream
from vkdownloader.services.quality import QualitySelector


def test_select_best_quality() -> None:
    """Test quality selector chooses best stream."""
    selector = QualitySelector()
    streams = [
        Stream(url="https://example.com/240p.m3u8", format=StreamFormat.HLS, quality="240", height=270),
        Stream(url="https://example.com/1080p.m3u8", format=StreamFormat.HLS, quality="1080", height=1080),
    ]

    result = selector.select(streams, QualityEnum.BEST)
    assert result.quality == "1080"


def test_select_worst_quality() -> None:
    """Test quality selector chooses worst stream."""
    selector = QualitySelector()
    streams = [
        Stream(url="https://example.com/240p.m3u8", format=StreamFormat.HLS, quality="240", height=270),
        Stream(url="https://example.com/1080p.m3u8", format=StreamFormat.HLS, quality="1080", height=1080),
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540),
    ]

    result = selector.select(streams, QualityEnum.WORST)
    assert result.quality == "240"


def test_fallback_to_best() -> None:
    """Test quality selector falls back to best when requested quality not found."""
    selector = QualitySelector()
    streams = [
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540),
        Stream(url="https://example.com/1080p.m3u8", format=StreamFormat.HLS, quality="1080", height=1080),
    ]

    # Request 480p which doesn't exist - should fall back to 1080p
    result = selector.select(streams, QualityEnum.Q480)
    assert result.quality == "1080"


def test_select_specific_quality() -> None:
    """Test quality selector chooses specific quality when available."""
    selector = QualitySelector()
    streams = [
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540),
        Stream(url="https://example.com/480p.m3u8", format=StreamFormat.HLS, quality="480", height=360),
    ]

    result = selector.select(streams, QualityEnum.Q480)
    assert result.quality == "480"


def test_select_empty_streams_raises() -> None:
    """Test quality selector raises ValueError for empty streams."""
    selector = QualitySelector()

    with pytest.raises(ValueError, match="Cannot select from empty streams list"):
        selector.select([], QualityEnum.BEST)


def test_list_available_qualities() -> None:
    """Test list_available_qualities returns sorted unique qualities."""
    selector = QualitySelector()
    streams = [
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720"),
        Stream(url="https://example.com/1080p.m3u8", format=StreamFormat.HLS, quality="1080"),
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720"),  # duplicate
    ]

    qualities = selector.list_available_qualities(streams)
    assert qualities == ["1080", "720"]
