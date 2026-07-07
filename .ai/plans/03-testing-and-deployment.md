# VK Video Downloader Module - Testing & Deployment (Part 3)

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tests/test_extractor.py
import pytest
from unittest.mock import AsyncMock, patch
from vkdownloader.services.extractor import VKVideoExtractor

class TestVKVideoExtractor:
    def test_parse_video_id_valid(self):
        extractor = VKVideoExtractor()
        owner_id, video_id = extractor.parse_video_id(
            "https://vkvideo.ru/video-225794656_456242637"
        )
        assert owner_id == "225794656"
        assert video_id == "456242637"

    def test_parse_video_id_invalid(self):
        extractor = VKVideoExtractor()
        with pytest.raises(ValueError):
            extractor.parse_video_id("https://example.com/video")

    @pytest.mark.asyncio
    async def test_extract_streams_mock(self):
        extractor = VKVideoExtractor()
        with patch("vkdownloader.services.extractor.BrowserManager") as mock_browser:
            mock_page = AsyncMock()
            mock_browser.return_value.create_stealth_page.return_value = mock_page
            # ... mock network responses
            pass
```

### 11.2 Integration Tests

```python
# tests/test_integration.py
import pytest
import json
from pathlib import Path

MOCK_M3U8_CONTENT = """
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=4684000,RESOLUTION=1920x804
https://example.com/1080p/playlist.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=790000,RESOLUTION=640x268
https://example.com/480p/playlist.m3u8
"""

@pytest.mark.asyncio
async def test_m3u8_parsing():
    from vkdownloader.services.downloader import HLSDownloader
    
    downloader = HLSDownloader()
    segments = await downloader._parse_m3u8("#test content")
    assert len(segments) > 0
```

### 11.3 Test Fixtures

```python
# tests/conftest.py
import pytest
from vkdownloader.config import Settings

@pytest.fixture
def test_settings():
    return Settings(
        user_agent="Mozilla/5.0 Test Browser",
        request_delay_min=0.1,
        request_delay_max=0.2,
        max_retries=2,
    )

@pytest.fixture
def sample_video_url():
    return "https://vkvideo.ru/video-225794656_456242637"
```

## 12. Error Handling & Resilience

### 12.1 Exception Hierarchy

```python
# src/vkdownloader/exceptions.py
class VKDownloadError(Exception):
    """Base exception for VK video downloader"""
    pass

class VideoNotFoundError(VKDownloadError):
    """Video was deleted or is private"""
    pass

class QualityNotAvailableError(VKDownloadError):
    """Requested quality not available"""
    pass

class ExtractionError(VKDownloadError):
    """Failed to extract stream URLs"""
    pass

class DownloadError(VKDownloadError):
    """Failed to download stream"""
    pass
```

### 12.2 Retry Logic

```python
# src/vkdownloader/utils/retry.py
import asyncio
import functools

@functools.lru_cache
def get_retry_decorator(max_retries: int = 3, base_delay: float = 2.0):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
        return wrapper
    return decorator
```

## 13. Security Considerations

### 13.1 Rate Limiting

```python
# src/vkdownloader/infrastructure/rate_limiter.py
import asyncio
import time
from collections import deque

class RateLimiter:
    def __init__(self, min_delay: float, max_delay: float):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.request_times: deque = deque()

    async def wait(self):
        now = time.time()
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
        self.request_times.append(now + delay)
```

### 13.2 User Agent Rotation

```python
# src/vkdownloader/utils/user_agents.py
from typing import List
import random

USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)
```

## 14. Deployment & Configuration

### 14.1 Dockerfile

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && poetry install

COPY . .

CMD ["python", "-m", "vkdownloader.cli"]
```

### 14.2 GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install poetry && poetry install
      - run: poetry run pytest --cov=vkdownloader
      - run: poetry run mypy vkdownloader
```

## 15. Usage Examples

### 15.1 Basic CLI Usage

```bash
# Install
pip install vkdownloader

# Download with best quality
vkdownloader download https://vkvideo.ru/video-225794656_456242637

# Download specific quality
vkdownloader download https://vkvideo.ru/video-225794656_456242637 --quality 720

# Specify output directory
vkdownloader download https://vkvideo.ru/video-225794656_456242637 --output ./videos
```

### 15.2 Programmatic Usage

```python
# main.py
import asyncio
from vkdownloader.services.extractor import VKVideoExtractor
from vkdownloader.services.downloader import HLSDownloader
from vkdownloader.services.quality import QualitySelector
from vkdownloader.models.enums import QualityEnum

async def download_video(url: str, quality: str = "best"):
    async with VKVideoExtractor() as extractor:
        video = await extractor.extract_streams(url)
    
    selector = QualitySelector()
    stream = selector.select(video.streams, QualityEnum(quality))
    
    async with HLSDownloader() as downloader:
        output = await downloader.download_stream(stream, "./downloads")
    
    return output

if __name__ == "__main__":
    result = asyncio.run(download_video(
        "https://vkvideo.ru/video-225794656_456242637", 
        "720"
    ))
    print(f"Saved to: {result}")
```

### 15.3 Batch Download

```python
# batch_download.py
import asyncio
from pathlib import Path
from vkdownloader.services.extractor import VKVideoExtractor

async def batch_download(urls: list[str], quality: str, output_dir: str):
    results = []
    for url in urls:
        try:
            output = await download_video(url, quality)
            results.append((url, output, "success"))
        except Exception as e:
            results.append((url, None, str(e)))
    return results
```

## 16. Dependencies

### 16.1 pyproject.toml

```toml
[tool.poetry]
name = "vkdownloader"
version = "0.1.0"
description = "VK Video downloader with quality selection"

[tool.poetry.dependencies]
python = "^3.11"
pydantic = "^2.0"
pydantic-settings = "^2.0"
aiohttp = "^3.9"
playwright = "^1.40"
ffmpeg-python = "^0.2"
typer = "^0.9"
structlog = "^24.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
mypy = "^1.8"
ruff = "^0.2"
```

### 16.2 Runtime Requirements

- Python 3.11+
- ffmpeg installed (for HLS segment muxing)
- Chrome/Chromium (for Playwright)

## 17. Troubleshooting Guide

| Issue | Solution |
|-------|----------|
| 403 Forbidden | Rotate User-Agent, add Referer header, use stealth mode |
| No m3u8 URLs found | Increase wait time, check if video is geo-blocked |
| Empty segments | Check token expiration, video may require login |
| Slow downloads | Reduce concurrency, increase delay between requests |
| ffmpeg not found | Install ffmpeg from https://ffmpeg.org |

---

*To be continued in Part 4: Advanced features, rate limiting, and production deployment.*