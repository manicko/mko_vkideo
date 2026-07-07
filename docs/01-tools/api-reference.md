---
id: vkdownloader-api-reference
domain: tools
tags:
  - api
  - reference
  - documentation
related:
  - vkdownloader-overview
  - vkdownloader-installation
---
# API Reference

## Purpose

Complete API documentation for all public classes and methods in VK Video Downloader.

## Services

### VKVideoExtractor

Location: `vkdownloader.services.extractor`

Extracts video stream URLs from VK video pages using browser automation.

```python
from vkdownloader.services.extractor import VKVideoExtractor
from vkdownloader.config import Settings

extractor = VKVideoExtractor(settings)
```

#### `__init__(settings: Settings | None = None)`

Initialize VKVideoExtractor with optional settings.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| settings | Settings \| None | None | Application settings. Uses global settings if not provided. |

#### `parse_video_id(url: str) -> tuple[str, str]`

Extract owner_id and video_id from VK video URL.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| url | str | VK video URL containing video identifier. |

**Returns:** Tuple of (owner_id, video_id).

**Raises:** `ValueError` if URL does not contain valid video identifier.

**Example:**
```python
owner_id, video_id = extractor.parse_video_id("https://vkvideo.ru/video-123_456")
# Returns: ("123", "456")
```

#### `extract_streams(url: str) -> VideoWithStreams`

Extract available streams from video URL by navigating page and capturing m3u8 URLs.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| url | str | VK video URL to extract streams from. |

**Returns:** `VideoWithStreams` containing available quality variants.

**Raises:** `ValueError` if URL does not contain valid video identifier.

**Example:**
```python
video = await extractor.extract_streams("https://vkvideo.ru/video-123_456")
for stream in video.streams:
    print(f"{stream.quality}: {stream.url}")
```

---

### QualitySelector

Location: `vkdownloader.services.quality`

Selects appropriate stream from available streams based on quality preference.

```python
from vkdownloader.services.quality import QualitySelector
from vkdownloader.models.enums import QualityEnum

selector = QualitySelector()
```

#### `select(streams: list[Stream], quality: QualityEnum) -> Stream`

Select a stream based on quality preference.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| streams | list[Stream] | List of available streams to choose from. |
| quality | QualityEnum | Quality preference (best, worst, or specific resolution). |

**Returns:** Selected `Stream` object.

**Raises:** `ValueError` if streams list is empty.

**Quality Options:**
| Value | Description |
|-------|-------------|
| `QualityEnum.BEST` | Highest available resolution |
| `QualityEnum.WORST` | Lowest available resolution |
| `QualityEnum.Q240` | 240p resolution or nearest available |
| `QualityEnum.Q360` | 360p resolution or nearest available |
| `QualityEnum.Q480` | 480p resolution or nearest available |
| `QualityEnum.Q720` | 720p resolution or nearest available |
| `QualityEnum.Q1080` | 1080p resolution or nearest available |

**Example:**
```python
stream = selector.select(video.streams, QualityEnum.Q720)
```

#### `list_available_qualities(streams: list[Stream]) -> list[str]`

Get sorted list of available quality options from streams.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| streams | list[Stream] | List of available streams. |

**Returns:** Sorted list of unique quality strings in descending order by resolution.

**Example:**
```python
qualities = selector.list_available_qualities(video.streams)
# Returns: ["1080p", "720p", "480p", "360p", "240p"]
```

---

### HLSDownloader

Location: `vkdownloader.services.downloader`

Downloads HLS streams to MP4 using ffmpeg's native HLS support.

```python
from vkdownloader.services.downloader import HLSDownloader
from pathlib import Path

downloader = HLSDownloader()
```

#### `__init__(settings: Settings | None = None)`

Initialize HLSDownloader with optional settings.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| settings | Settings \| None | None | Application settings. Uses global settings if not provided. |

#### `download_with_ffmpeg(m3u8_url: str, output_file: Path, quality: str = "best") -> Path | None`

Download HLS stream to MP4 using ffmpeg.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| m3u8_url | str | Required | URL of the HLS m3u8 playlist to download. |
| output_file | Path | Required | Path where the output MP4 file will be saved. |
| quality | str | "best" | Quality identifier for logging purposes. |

**Returns:** Path to downloaded MP4 file on success, None on failure.

**Example:**
```python
result = await downloader.download_with_ffmpeg(
    "https://example.com/playlist.m3u8",
    Path("output.mp4"),
    quality="720"
)
```

---

## Models

### Stream

Location: `vkdownloader.models.video`

Represents a video stream with URL and quality information.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| url | HttpUrl | Stream URL |
| format | StreamFormat | Stream format (HLS, DASH, MP4) |
| quality | str | Quality string (e.g., "720p", "best") |
| resolution | str \| None | Resolution string |
| bitrate | int \| None | Bitrate in kbps |
| width | int \| None | Video width in pixels |
| height | int \| None | Video height in pixels |

---

### VideoWithStreams

Location: `vkdownloader.models.video`

Video model extended with available streams.

**Inherits from:** `Video`

**Additional Attributes:**
| Name | Type | Description |
|------|------|-------------|
| streams | list[Stream] | List of available stream variants |

---

## Enums

### QualityEnum

Location: `vkdownloader.models.enums`

Video quality options for stream selection.

| Value | Description |
|-------|-------------|
| `Q240` | "240" |
| `Q360` | "360" |
| `Q480` | "480" |
| `Q720` | "720" |
| `Q1080` | "1080" |
| `BEST` | "best" |
| `WORST` | "worst" |

---

### StreamFormat

Location: `vkdownloader.models.enums`

Stream format types.

| Value | Description |
|-------|-------------|
| `HLS` | "hls" |
| `DASH` | "dash" |
| `MP4` | "mp4" |

---

### DownloadStatus

Location: `vkdownloader.models.enums`

Download status states.

| Value | Description |
|-------|-------------|
| `PENDING` | "pending" |
| `DOWNLOADING` | "downloading" |
| `COMPLETED` | "completed" |
| `FAILED` | "failed" |

---

## Infrastructure

### HttpClient

Location: `vkdownloader.infrastructure.http_client`

Async context manager for HTTP requests with browser-like headers and retry logic.

**Methods:**
| Method | Description |
|--------|-------------|
| `get(url: str) -> str` | Perform GET request with retry logic |
| `download_file(url: str, output_path: Path, progress_callback: Callable?) -> None` | Download file with progress tracking |

---

### BrowserManager

Location: `vkdownloader.infrastructure.browser`

Async context manager for Playwright browser automation with stealth configuration.

**Methods:**
| Method | Description |
|--------|-------------|
| `create_stealth_page() -> Page` | Create a new page with stealth configuration |

---

### NetworkMonitor

Location: `vkdownloader.infrastructure.network_monitor`

Monitors network traffic to capture m3u8 URLs from responses.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| m3u8_urls | list[str] | List of captured m3u8 URLs |

---

## Settings

Location: `vkdownloader.config`

Application settings with defaults and environment variable support.

**Key Attributes:**
| Name | Default | Description |
|------|---------|-------------|
| user_agent | Chrome 120 UA | User agent string for requests |
| download_dir | ~/Downloads/vkdownloader | Directory for downloaded videos |
| max_concurrent_downloads | 4 | Maximum concurrent downloads |
| timeout_seconds | 30 | Request timeout in seconds |
| request_delay_min | 2.0 | Minimum request delay |
| request_delay_max | 5.0 | Maximum request delay |