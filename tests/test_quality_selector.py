"""Tests for QualitySelector service."""

import pytest

from vkdownloader.exceptions import QualityNotAvailableError
from vkdownloader.models.enums import QualityEnum, StreamFormat
from vkdownloader.models.video import Stream
from vkdownloader.services.quality import QualitySelector


def test_select_best_quality() -> None:
    """Test quality selector chooses best stream."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/240p.m3u8", format=StreamFormat.HLS, quality="240", height=270
        ),
        Stream(
            url="https://example.com/1080p.m3u8",
            format=StreamFormat.HLS,
            quality="1080",
            height=1080,
        ),
    ]

    result = selector.select(streams, QualityEnum.BEST)
    assert result.quality == "1080"


def test_select_worst_quality() -> None:
    """Test quality selector chooses worst stream."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/240p.m3u8", format=StreamFormat.HLS, quality="240", height=270
        ),
        Stream(
            url="https://example.com/1080p.m3u8",
            format=StreamFormat.HLS,
            quality="1080",
            height=1080,
        ),
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540
        ),
    ]

    result = selector.select(streams, QualityEnum.WORST)
    assert result.quality == "240"


def test_quality_not_available_raises() -> None:
    """Test quality selector raises QualityNotAvailableError when requested quality not found."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540
        ),
        Stream(
            url="https://example.com/1080p.m3u8",
            format=StreamFormat.HLS,
            quality="1080",
            height=1080,
        ),
    ]

    # Request 480p which doesn't exist - should raise QualityNotAvailableError
    with pytest.raises(QualityNotAvailableError) as exc_info:
        selector.select(streams, QualityEnum.Q480)

    # Verify structured fields
    error = exc_info.value
    assert error.requested == "480"
    assert error.available == ["720", "1080"]
    # Verify message format
    assert "Quality '480' not available" in str(error)


def test_select_specific_quality() -> None:
    """Test quality selector chooses specific quality when available."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540
        ),
        Stream(
            url="https://example.com/480p.m3u8", format=StreamFormat.HLS, quality="480", height=360
        ),
    ]

    result = selector.select(streams, QualityEnum.Q480)
    assert result.quality == "480"


def test_select_empty_streams_raises() -> None:
    """Test quality selector raises QualityNotAvailableError for empty streams."""
    selector = QualitySelector()

    with pytest.raises(
        QualityNotAvailableError, match="Cannot select quality from empty streams list"
    ):
        selector.select([], QualityEnum.BEST)


def test_select_empty_streams_error_status_label() -> None:
    """Test that empty-streams QualityNotAvailableError maps to no_streams status."""
    selector = QualitySelector()

    with pytest.raises(QualityNotAvailableError) as exc_info:
        selector.select([], QualityEnum.BEST)

    assert exc_info.value.status_label() == "no_streams"
    assert exc_info.value.error_code is not None  # Error code is set


def test_list_available_qualities() -> None:
    """Test list_available_qualities returns sorted unique qualities."""
    selector = QualitySelector()
    streams = [
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720"),
        Stream(url="https://example.com/1080p.m3u8", format=StreamFormat.HLS, quality="1080"),
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720"
        ),  # duplicate
    ]

    qualities = selector.list_available_qualities(streams)
    assert qualities == ["1080", "720"]


def test_find_quality_match_returns_matching_stream() -> None:
    """Test _find_quality_match finds stream by quality string."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540
        ),
        Stream(
            url="https://example.com/480p.m3u8", format=StreamFormat.HLS, quality="480", height=360
        ),
    ]

    result = selector._find_quality_match(streams, "480")
    assert result is not None
    assert result.quality == "480"


def test_find_quality_match_returns_none_for_no_match() -> None:
    """Test _find_quality_match returns None when quality not found."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540
        ),
        Stream(
            url="https://example.com/480p.m3u8", format=StreamFormat.HLS, quality="480", height=360
        ),
    ]

    result = selector._find_quality_match(streams, "1080")
    assert result is None


def test_find_quality_match_handles_p_suffix() -> None:
    """Test _find_quality_match matches quality with or without p suffix."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720p", height=540
        ),
        Stream(
            url="https://example.com/480p.m3u8", format=StreamFormat.HLS, quality="480p", height=360
        ),
    ]

    # Match with "720" against stream quality "720p"
    result = selector._find_quality_match(streams, "720")
    assert result is not None
    assert result.quality == "720p"


def test_get_fallback_stream_returns_best_quality() -> None:
    """Test _get_fallback_stream returns stream with highest resolution."""
    selector = QualitySelector()
    streams = [
        Stream(
            url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720", height=540
        ),
        Stream(
            url="https://example.com/1080p.m3u8",
            format=StreamFormat.HLS,
            quality="1080",
            height=1080,
        ),
        Stream(
            url="https://example.com/240p.m3u8", format=StreamFormat.HLS, quality="240", height=270
        ),
    ]

    result = selector._get_fallback_stream(streams)
    assert result.quality == "1080"
    assert result.height == 1080


def test_get_fallback_stream_handles_none_height() -> None:
    """Test _get_fallback_stream handles streams with None height."""
    selector = QualitySelector()
    streams = [
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720"),
        Stream(
            url="https://example.com/1080p.m3u8",
            format=StreamFormat.HLS,
            quality="1080",
            height=1080,
        ),
    ]

    result = selector._get_fallback_stream(streams)
    assert result.quality == "1080"
    assert result.height == 1080
