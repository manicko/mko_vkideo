"""Pytest configuration and fixtures for VK Video Downloader tests."""

import pytest

from vkdownloader.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings instance with safe defaults."""
    return Settings(
        download_dir=Settings.model_fields["download_dir"].default,
        max_concurrent_downloads=2,
        max_retries=1,
    )


@pytest.fixture
def sample_video_url() -> str:
    """Provide a sample VK video URL for testing."""
    return "https://vkvideo.ru/video-12345_67890"


@pytest.fixture
def mock_m3u8_content() -> str:
    """Provide mock m3u8 playlist content for testing."""
    return """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=4684000,RESOLUTION=1920x804
https://example.com/1080p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2384000,RESOLUTION=1280x540
https://example.com/720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1184000,RESOLUTION=854x360
https://example.com/360p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=684000,RESOLUTION=640x270
https://example.com/240p.m3u8
"""


@pytest.fixture
def mock_m3u8_single_stream() -> str:
    """Provide mock m3u8 content with single stream."""
    return """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=4684000,RESOLUTION=1920x804
https://example.com/1080p.m3u8
"""


@pytest.fixture
def mock_invalid_url() -> str:
    """Provide an invalid URL that won't match the video ID pattern."""
    return "https://example.com/invalid"
