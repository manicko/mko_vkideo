"""Pytest configuration and fixtures for VK Video Downloader tests."""

import os
from pathlib import Path

import pytest

from vkdownloader.config import Settings

ENV_VAR_PREFIX = "VKDOWNLOADER_"


@pytest.fixture(autouse=True)
def isolate_settings_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Pin the settings environment source to nothing for the whole suite (D-10).

    ``Settings.model_config`` declares ``env_file=".env"`` as a *relative* path, so
    pydantic-settings resolves it against the current working directory on every
    construction, and the ``VKDOWNLOADER_`` variables are read straight from
    ``os.environ``. Both halves are ambient: without this fixture a developer's
    own ``.env`` in the directory the suite was launched from and any exported
    ``VKDOWNLOADER_*`` variable decide test outcomes, so the suite's result
    depends on the shell it is launched from. Measured by D-10: one documented
    variable, ``VKDOWNLOADER_COOKIE_SOURCE=browser``, flipped
    ``test_cookie_source_default`` from pass to fail.

    Two halves are neutralised, both for the duration of a single test:

    * the **file half** — the working directory is moved to ``tmp_path``, a fresh
      empty directory unique to this test, so no ``.env`` is reachable;
    * the **variable half** — every ``VKDOWNLOADER_*`` entry in ``os.environ`` is
      deleted for the duration of the test.

    ``monkeypatch`` restores both the working directory and the environment
    afterwards, and ``tmp_path`` is removed by pytest's own teardown, so nothing
    leaks between tests and nothing needs manual cleanup. This is test-side
    isolation only: no production code carries a branch for the suite.
    """
    for key in list(os.environ):
        if key.startswith(ENV_VAR_PREFIX):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


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
