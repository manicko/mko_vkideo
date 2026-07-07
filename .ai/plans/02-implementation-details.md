# VK Video Downloader Module - Implementation Details (Part 2)

## 8. Data Models & API Contracts

### 8.1 Core Domain Models

```python
# src/vkdownloader/models/video.py
from pydantic import BaseModel, HttpUrl
from enum import StrEnum
from typing import Optional

class QualityEnum(StrEnum):
    BEST = "best"
    WORST = "worst"
    Q240 = "240"
    Q360 = "360"
    Q480 = "480"
    Q720 = "720"
    Q1080 = "1080"

class StreamFormat(StrEnum):
    HLS = "hls"
    DASH = "dash"
    MP4 = "mp4"

class Video(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[HttpUrl] = None
    upload_date: Optional[str] = None
    views: Optional[int] = None

class Stream(BaseModel):
    url: HttpUrl
    format: StreamFormat
    quality: str
    resolution: Optional[str] = None
    bitrate: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None

class VideoWithStreams(Video):
    streams: list[Stream]

class DownloadProgress(BaseModel):
    video_id: str
    downloaded_bytes: int
    total_bytes: Optional[int] = None
    segments_downloaded: int
    segments_total: int
    status: str
    error: Optional[str] = None
```

### 8.2 Input/Output DTOs

```python
# src/vkdownloader/models/dtos.py
from pydantic import BaseModel, HttpUrl

class DownloadRequest(BaseModel):
    url: HttpUrl
    quality: QualityEnum = QualityEnum.BEST
    output_path: str = "."
    filename: Optional[str] = None

class DownloadResult(BaseModel):
    video_id: str
    output_file: str
    file_size: int
    duration: int
    streams_used: list[Stream]
    success: bool
    error_message: Optional[str] = None
```

## 9. Interface Definitions

### 9.1 Abstract Interfaces

```python
# src/vkdownloader/domain/interfaces/extractor.py
from abc import ABC, abstractmethod
from ..models.video import VideoWithStreams, Stream

class VideoExtractor(ABC):
    @abstractmethod
    async def extract_streams(self, url: str) -> VideoWithStreams:
        """Extract available streams from video URL"""
        pass

# src/vkdownloader/domain/interfaces/downloader.py
class StreamDownloader(ABC):
    @abstractmethod
    async def download_stream(
        self, 
        stream: Stream, 
        output_path: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> str:
        """Download stream to output path, returns file path"""
        pass
```

## 10. Implementation Tasks Breakdown

### 10.1 Phase 1 Tasks (Foundational)

#### Task 1.1.1: Poetry Setup
```bash
# Commands to execute
poetry init --no-interaction
poetry add pydantic aiohttp playwright ffmpeg-python typer structlog
poetry add --group dev pytest pytest-asyncio mypy ruff
```

#### Task 1.1.2: Configuration Module
```python
# src/vkdownloader/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
    accept_language: str = "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    request_delay_min: float = 2.0
    request_delay_max: float = 5.0
    max_retries: int = 3
    concurrency: int = 8
    download_timeout: int = 300
    output_dir: Path = Path("./downloads")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

#### Task 1.1.3: Enums Module
```python
# src/vkdownloader/models/enums.py
from enum import StrEnum

class QualityEnum(StrEnum):
    BEST = "best"
    WORST = "worst"
    Q240 = "240"
    Q360 = "360"
    Q480 = "480"
    Q720 = "720"
    Q1080 = "1080"

class DownloadStatus(StrEnum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    DOWNLOADING = "downloading"
    MUXING = "muxing"
    COMPLETED = "completed"
    FAILED = "failed"
```

### 10.2 Phase 2 Tasks (Extraction)

#### Task 2.1.1: Browser Manager
```python
# src/vkdownloader/infrastructure/browser.py
import asyncio
from playwright.async_api import async_playwright, Page

class BrowserManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.playwright = None
        self.browser = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False,  # Can be configured
            args=["--disable-blink-features=AutomationControlled"]
        )
        return self

    async def __aexit__(self, *args):
        await self.browser.close()
        await self.playwright.stop()

    async def create_stealth_page(self) -> Page:
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=self.settings.user_agent,
        )
        page = await context.new_page()
        # Apply stealth scripts
        await page.add_init_script(path="stealth.min.js")
        return page
```

#### Task 2.1.2: Network Interceptor
```python
# src/vkdownloader/infrastructure/network_interceptor.py
import re
from typing import Optional
from playwright.async_api import Page

class NetworkInterceptor:
    M3U8_PATTERN = re.compile(r"https?://.*\.m3u8.*")

    def __init__(self, page: Page):
        self.page = page
        self.m3u8_urls: list[str] = []
        self._setup_listeners()

    def _setup_listeners(self):
        self.page.on("response", self._on_response)

    async def _on_response(self, response):
        url = response.url
        if self.M3U8_PATTERN.match(url):
            self.m3u8_urls.append(url)
        # Also check for XHR responses containing stream URLs
        if "video" in url and response.headers.get("content-type", "").startswith("application/json"):
            try:
                data = await response.json()
                self._extract_from_json(data)
            except:
                pass

    def _extract_from_json(self, data: dict):
        # Extract m3u8 URLs from JSON responses
        def recursive_search(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    if isinstance(value, str) and self.M3U8_PATTERN.match(value):
                        self.m3u8_urls.append(value)
                    elif isinstance(value, (dict, list)):
                        recursive_search(value)
            elif isinstance(obj, list):
                for item in obj:
                    recursive_search(item)
        recursive_search(data)
```

#### Task 2.2.1: VK Video Parser
```python
# src/vkdownloader/services/extractor.py
import re
from urllib.parse import urlparse
from ..models.video import VideoWithStreams, Stream, Video, StreamFormat

class VKVideoExtractor:
    VIDEO_ID_PATTERN = re.compile(r"video-(\d+)_(\d+)")

    def parse_video_id(self, url: str) -> tuple[str, str]:
        """Extract owner_id and video_id from URL"""
        match = self.VIDEO_ID_PATTERN.search(url)
        if not match:
            raise ValueError(f"Invalid VK video URL: {url}")
        return match.group(1), match.group(2)

    async def extract_streams(self, url: str) -> VideoWithStreams:
        owner_id, video_id = self.parse_video_id(url)
        video_id_full = f"{owner_id}_{video_id}"

        # Use browser to get streams
        async with BrowserManager() as browser:
            page = await browser.create_stealth_page()
            interceptor = NetworkInterceptor(page)
            
            await page.goto(url, wait_until="networkidle")
            await self._simulate_video_interaction(page)
            await asyncio.sleep(3)  # Wait for API calls

            streams = []
            for m3u8_url in interceptor.m3u8_urls:
                stream = await self._parse_m3u8_playlist(m3u8_url)
                streams.extend(stream)

            return VideoWithStreams(
                id=video_id_full,
                streams=streams
            )

    async def _simulate_video_interaction(self, page):
        # Click play button or simulate mouse movement
        await page.mouse.move(150, 200)
        await page.mouse.move(200, 250)
        await asyncio.sleep(1)
        # Try clicking video player
        try:
            await page.click(".VideoPlayer")
        except:
            pass

    async def _parse_m3u8_playlist(self, url: str) -> list[Stream]:
        # Download and parse m3u8
        # Extract variants with quality info
        pass
```

### 10.3 Phase 3 Tasks (Download)

#### Task 3.1.1: HLS Downloader
```python
# src/vkdownloader/services/downloader.py
import aiohttp
import asyncio
from pathlib import Path
from ..models.video import Stream, DownloadProgress, DownloadStatus

class HLSDownloader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": self.settings.user_agent,
                "Referer": "https://vkvideo.ru/",
            }
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def download_stream(
        self,
        stream: Stream,
        output_path: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        segments = await self._get_playlist_segments(stream.url)
        
        temp_dir = Path(output_path) / "temp_segments"
        temp_dir.mkdir(exist_ok=True)

        # Download segments concurrently
        for i, segment_url in enumerate(segments):
            await self._download_segment(segment_url, temp_dir / f"{i}.ts")
            if progress_callback:
                progress_callback(DownloadProgress(
                    video_id=stream.quality,
                    segments_downloaded=i + 1,
                    segments_total=len(segments)
                ))

        # Combine and mux with ffmpeg
        output_file = await self._mux_segments(temp_dir, output_path)
        return output_file

    async def _get_playlist_segments(self, url: str) -> list[str]:
        """Fetch and parse m3u8 to get segment URLs"""
        async with self.session.get(url) as resp:
            content = await resp.text()
        # Parse m3u8 and extract .ts URLs
        pass

    async def _download_segment(self, url: str, output: Path):
        """Download single segment with retry"""
        for attempt in range(self.settings.max_retries):
            try:
                async with self.session.get(url) as resp:
                    output.write_bytes(await resp.read())
                return
            except Exception:
                if attempt == self.settings.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
```

### 10.4 Phase 4 Tasks (CLI)

#### Task 4.1.1: CLI Interface
```python
# src/vkdownloader/cli.py
import typer
from pathlib import Path
from .services.extractor import VKVideoExtractor
from .services.downloader import HLSDownloader
from .services.quality import QualitySelector
from .models.enums import QualityEnum

app = typer.Typer()

@app.command()
def download(
    url: str = typer.Argument(..., help="VK Video URL"),
    quality: QualityEnum = typer.Option(QualityEnum.BEST, help="Video quality"),
    output: Path = typer.Option(".", help="Output directory")
):
    """Download video from vkvideo.ru"""
    async def _download():
        async with VKVideoExtractor() as extractor:
            video = await extractor.extract_streams(url)
        
        selector = QualitySelector()
        stream = selector.select(video.streams, quality)

        async with HLSDownloader() as downloader:
            output_file = await downloader.download_stream(stream, str(output))
        
        print(f"Downloaded: {output_file}")

    asyncio.run(_download())

if __name__ == "__main__":
    app()
```

---

*To be continued in Part 3: Testing strategy, error handling, and deployment.*