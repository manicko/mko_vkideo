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

Extracts video stream URLs from VK video URLs using yt-dlp (primary) or browser automation.

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

Extract available streams from video URL using yt-dlp (handles VK protections).

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| url | str | VK video URL to extract streams from. |

**Returns:** `VideoWithStreams` containing available quality variants.

**Raises:** `ValueError` if URL does not contain valid video identifier.
`VideoNotFoundError` if no streams are found.
`ExtractionError` if extraction fails.

**Example:**
```python
video = await extractor.extract_streams("https://vkvideo.ru/video-123_456")
for stream in video.streams:
    print(f"{stream.quality}: {stream.url}")
```

#### `extract_streams_with_cookies(url: str) -> tuple[list[Stream], str | None]`

Extract streams using browser automation to capture cookies for ffmpeg authentication.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| url | str | VK video URL to extract streams from. |

**Returns:** Tuple of (streams list, cookies string) for ffmpeg headers.

**Raises:** `ValueError` if URL does not contain valid video identifier.
`VideoNotFoundError` if no streams are found.

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

## Download Functions

### perform_download

Location: `vkdownloader.services.downloader`

Main download orchestration function that handles quality selection and download method routing.

```python
from vkdownloader.services.downloader import perform_download
from vkdownloader.models.enums import DownloadMethod
from pathlib import Path

result = await perform_download(
    url="https://vkvideo.ru/video-123_456",
    quality="720",
    output_file=Path("output.mp4"),
    method=DownloadMethod.AUTO,
)
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `url` | str | VK video URL to download. |
| `quality` | str | Quality string (e.g., "720", "1080"). |
| `output_file` | Path | Output file path. |
| `method` | DownloadMethod | Download method (YTDLP, FFMPEG, or AUTO). |
| `extractor` | VKVideoExtractor \| None | Optional extractor instance. |
| `settings` | Settings \| None | Optional settings instance. |

**Returns:** Path to downloaded file on success, None on failure.

**Raises:** `VideoNotFoundError` if no streams found.

---

### download_hls_with_resume

Location: `vkdownloader.services.downloader`

Download HLS stream with segment-level resume and automatic token refresh on 403/410 responses.

```python
from vkdownloader.services.downloader import download_hls_with_resume
from vkdownloader.models.dtos import HLSDownloadRequest

request = HLSDownloadRequest(
    video_url="https://vkvideo.ru/video-123_456",
    m3u8_url="https://cdn.example.com/playlist.m3u8",
    output_file=Path("output.mp4"),
    quality="720",
    cookies="session=abc123",
    settings=settings,
    extractor=extractor,
)
result = await download_hls_with_resume(request)
```

**Features:**
- Downloads segments individually with progress tracking
- Resumes from last downloaded segment on interruption
- Refreshes expired m3u8 tokens via browser automation
- Cleans up partial downloads on failure

---

### download_with_ytdlp_with_resume_fallback

Location: `vkdownloader.services.downloader`

Download using yt-dlp with automatic segment-based resume fallback on failure.

**Flow:**
1. Try yt-dlp download
2. On failure with partial file: get fresh token via browser + switch to segment download
3. Segment download resumes from last checkpoint

---

## Models

### HLSDownloadRequest

Location: `vkdownloader.models.dtos`

Request model for HLS download with segment-level resume support.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `video_url` | str | Original VK video URL for token refresh. |
| `m3u8_url` | str | HLS playlist URL. |
| `output_file` | Path | Output file path. |
| `quality` | str | Quality string (default: "best"). |
| `cookies` | str \| None | Cookies string for CDN authentication. |
| `settings` | Settings \| None | Application settings. |
| `extractor` | VKVideoExtractor \| None | Extractor for token refresh. |

---

### DownloadRequest

Location: `vkdownloader.models.dtos`

Request model for video download initiation.

**Attributes:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | HttpUrl | Required | Video URL. |
| `quality` | QualityEnum | BEST | Quality preference. |
| `output_path` | str | "." | Output directory path. |
| `filename` | str \| None | None | Optional custom filename. |

---

### DownloadResult

Location: `vkdownloader.models.dtos`

Result model for completed video download.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `video_id` | str | Video identifier. |
| `output_file` | str | Path to downloaded file. |
| `file_size` | int | File size in bytes. |
| `duration` | int | Video duration in seconds. |
| `streams_used` | list[Stream] | List of streams used. |
| `success` | bool | Whether download succeeded. |
| `error_message` | str \| None | Error message if failed. |

---

### StreamWithCookies

Location: `vkdownloader.models.video`

Stream model with associated cookies for CDN authentication.

**Attributes (inherits from Stream):**
| Name | Type | Description |
|------|------|-------------|
| `cookies` | str \| None | Cookies string for ffmpeg headers. |

---

### DownloadProgress

Location: `vkdownloader.models.video`

Tracks download progress for a video.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `video_id` | str | Video identifier. |
| `downloaded_bytes` | int | Bytes downloaded. |
| `total_bytes` | int \| None | Total bytes (if known). |
| `segments_downloaded` | int | Number of segments downloaded. |
| `segments_total` | int | Total segments. |
| `status` | DownloadStatus | Current download status. |
| `error` | str \| None | Error message if any. |

---

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

### DownloadMethod

Location: `vkdownloader.models.enums`

Download method selection for video downloads. Controls how videos are downloaded from VK.

| Value | Description |
|-------|-------------|
| `YTDLP` | "yt-dlp" — Uses yt-dlp for download with automatic segment-based resume on failure |
| `FFMPEG` | "ffmpeg" — Direct ffmpeg download with browser-captured cookies |
| `AUTO` | "auto" — Tries yt-dlp first, falls back to segment download on failure (default) |

**Example:**
```python
from vkdownloader.models.enums import DownloadMethod
from vkdownloader.services.downloader import perform_download

result = await perform_download(
    url="https://vkvideo.ru/video-123_456",
    quality="720",
    output_file=Path("output.mp4"),
    method=DownloadMethod.FFMPEG,
)
```

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

## Security Utilities

### validate_output_path

Location: `vkdownloader.utils.security`

Validates output path to prevent path traversal attacks and warns if path is inside repository root.

```python
from pathlib import Path
from vkdownloader.utils.security import validate_output_path

validated_path = validate_output_path(Path("./output/video.mp4"))
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `path` | Path | Required | Output path to validate. |
| `warning` | bool | True | Whether to log warning for repo-root paths. |

**Raises:** `DownloadError` if path contains traversal attempts ("..").

---

## Exceptions

### VKDownloadError

Location: `vkdownloader.exceptions`

Base exception for all VK Video Downloader errors.

---

### VideoNotFoundError

Location: `vkdownloader.exceptions`

Raised when a requested video cannot be found or no streams are extracted.

**Raised by:**
- `VKVideoExtractor.extract_streams()` — When no streams found for video URL
- `VKVideoExtractor.extract_streams_with_cookies()` — When no streams found

---

### QualityNotAvailableError

Location: `vkdownloader.exceptions`

Raised when the requested quality is not available for a video.

**Raised by:**
- `QualitySelector.select()` — When specific quality not found in streams

---

### ExtractionError

Location: `vkdownloader.exceptions`

Raised when video data extraction fails unexpectedly.

**Raised by:**
- `VKVideoExtractor._extract_with_ytdlp()` — When extraction returns no data

---

### DownloadError

Location: `vkdownloader.exceptions`

Raised when video download fails.

**Raised by:**
- `validate_output_path()` — When path traversal is detected

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
| download_timeout | 300 | Download timeout in seconds |
| ssl_verify | True | Verify SSL certificates for CDN connections |
| download_method | AUTO | Download method: yt-dlp, ffmpeg, or auto |


