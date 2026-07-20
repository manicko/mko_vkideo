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
  - vkdownloader-quality-selection
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

#### `extract_streams_with_cookies(url: str, force_browser: bool = False) -> tuple[list[Stream], str | None]`

Extract streams using browser automation to capture cookies for ffmpeg authentication.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| url | str | Required | VK video URL to extract streams from. |
| force_browser | bool | False | Force browser launch even when cookie_source=NONE (for token refresh scenarios). |

**Returns:** Tuple of (streams list, cookies string) for ffmpeg headers.

**Behavior:**
- When `cookie_source=NONE` and `force_browser=False`: Returns streams without cookies via yt-dlp
- When `cookie_source=BROWSER`: Launches browser, captures cookies from active session
- When `cookie_source=FILE`: Raises `NotImplementedError` (not implemented)
- When `force_browser=True`: Forces browser launch regardless of cookie_source setting

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

#### `download_with_ffmpeg(m3u8_url: str, output_file: Path, quality: str = "best", cookies: str | None = None, progress_callback: Callable[[FfmpegProgress], None] | None = None) -> Path | None`

Download HLS stream to MP4 using ffmpeg.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| m3u8_url | str | Required | URL of the HLS m3u8 playlist to download. |
| output_file | Path | Required | Path where the output MP4 file will be saved. |
| quality | str | "best" | Quality identifier for logging purposes. |
| cookies | str \| None | None | Cookies string for authenticated downloads. |
| progress_callback | Callable[[FfmpegProgress], None] \| None | None | Optional callback for real-time progress updates. |

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

### DownloaderThrottle

Location: `vkdownloader.services.downloader_throttle`

Rate limiting utilities with AWS Full Jitter exponential backoff for handling VK's anti-bot protection.

**Constants:**
| Name | Value | Description |
|------|-------|-------------|
| `RETRYABLE_STATUS_CODES` | {429, 500, 502, 503, 504} | HTTP status codes that trigger retry with backoff |

#### `_retry_429_with_backoff(session: aiohttp.ClientSession, segment_url: str, headers: dict[str, str], segment_index: int, max_retries: int = 3) -> bytes | None`

Download segment with AWS Full Jitter backoff for 429/5xx errors.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| session | aiohttp.ClientSession | Required | aiohttp session for HTTP requests. |
| segment_url | str | Required | URL of the segment to download. |
| headers | dict[str, str] | Required | Request headers to use. |
| segment_index | int | Required | Index of the segment being downloaded (for logging). |
| max_retries | int | 3 | Maximum number of retry attempts. |

**Returns:** Bytes content on success, None on permanent failure.

**Behavior:**
- Uses exponential backoff: random(0, base_delay * 2^attempt)
- Base delay: 1s for 429, 0.05s for 5xx errors
- Honors Retry-After header when present
- Max delay capped at 30 seconds
- Retries on: 429, 500, 502, 503, 504

---

### FfmpegProgress

Location: `vkdownloader.services.ffmpeg_utils`

Progress state from ffmpeg -progress pipe output.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| frame | int \| None | Frame count |
| fps | float \| None | Frames per second |
| speed | float \| None | Speed multiplier (e.g., 1.5 = 1.5x) |
| total_size | int \| None | Total bytes |
| out_time_us | int \| None | Output time in microseconds |
| out_time_ms | int \| None | Output time in milliseconds |
| out_time | str \| None | Output time as string |
| progress | str \| None | Progress state ("continue" or "end") |

---

### ProgressParser

Location: `vkdownloader.services.ffmpeg_utils`

Parser for ffmpeg KEY=VALUE progress output.

#### `parse_line(line: str) -> tuple[str, str] | None`

Parse a single progress line in KEY=VALUE format.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| line | str | Raw line from ffmpeg stderr. |

**Returns:** Tuple of (key, value) if valid format, None otherwise.

---

### read_progress

Location: `vkdownloader.services.ffmpeg_utils`

Async generator reading ffmpeg progress output in real-time.

```python
async def read_progress(
    stderr: asyncio.StreamReader,
    duration_ms: int | None = None,
    stderr_collector: list[bytes] | None = None,
) -> AsyncIterator[FfmpegProgress]:
    ...
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| stderr | asyncio.StreamReader | Required | StreamReader from ffmpeg process stderr. |
| duration_ms | int \| None | None | Optional video duration in milliseconds for percentage calculation. |
| stderr_collector | list[bytes] \| None | None | Optional list to collect raw stderr lines for error handling. |

**Yields:** FfmpegProgress objects as they are parsed from stdout.

---

### _parse_retry_after

Location: `vkdownloader.services.downloader_throttle`

Parse Retry-After header from HTTP response for delay calculation.

```python
def _parse_retry_after(response: aiohttp.ClientResponse) -> float | None:
    ...
```

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| response | aiohttp.ClientResponse | Response with Retry-After header. |

**Returns:** Seconds to wait, or None if header not present or invalid.

**Behavior:**
- Handles integer seconds format (e.g., "120")
- Handles HTTP date format (e.g., "Fri, 31 Dec 1999 23:59:59 GMT")
- Returns None for missing or unparseable headers

---

### _fetch_playlist_with_retry

Location: `vkdownloader.services.segment_downloader`

Fetch m3u8 playlist with automatic token refresh on 403/410 responses.

```python
async def _fetch_playlist_with_retry(
    session: aiohttp.ClientSession,
    video_url: str,
    m3u8_url: str,
    headers: dict[str, str],
    extractor: VKVideoExtractor | None,
    settings: Settings,
    max_retries: int = 3,
) -> str | None:
    ...
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| session | aiohttp.ClientSession | Required | aiohttp session for HTTP requests. |
| video_url | str | Required | Original VK video URL for token refresh. |
| m3u8_url | str | Required | HLS playlist URL to fetch. |
| headers | dict[str, str] | Required | Request headers to use. |
| extractor | VKVideoExtractor \| None | Required | Extractor for token refresh. |
| settings | Settings | Required | Application settings. |
| max_retries | int | 3 | Maximum retry attempts. |

**Returns:** Playlist content on success, None on failure.

**Behavior:**
- On 200 response: Returns playlist content
- On 403/410 with cookie_source=BROWSER: Refreshes token via browser
- On 403/410 with cookie_source=NONE: Logs warning, returns None (cannot refresh)

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
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `url` | str | Required | VK video URL to download. |
| `quality` | str | Required | Quality string (e.g., "720", "1080"). |
| `output_file` | Path | Required | Output file path. |
| `method` | DownloadMethod | Required | Download method (YTDLP, FFMPEG, or AUTO). |
| `extractor` | VKVideoExtractor \| None | None | Optional extractor instance. |
| `settings` | Settings \| None | None | Optional settings instance. |
| `backoff_coordinator` | URLBackoffCoordinator \| None | None | URLBackoffCoordinator for shared rate limiting across batch URLs. |
| `semaphore` | asyncio.Semaphore \| None | None | Shared semaphore for work-stealing concurrency in batch downloads. |
| `progress_callback` | Callable[[str, int, int], None] \| None | None | Callback for per-URL segment progress (video_id, downloaded, total). |
| `video_data` | VideoWithStreams \| None | None | Optional pre-extracted video data with streams. When provided, skips extraction. |
| `selected_stream` | Stream \| None | None | Optional pre-selected stream. When provided, used instead of streams[0]. |

**Returns:** Path to downloaded file on success, None on failure.

**Raises:** `VideoNotFoundError` if no streams found.

---

### download_hls_with_resume

Location: `vkdownloader.services.segment_downloader`

Download HLS stream with segment-level resume and automatic token refresh on 403/410 responses.

```python
from vkdownloader.services.segment_downloader import download_hls_with_resume
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
- Refreshes expired m3u8 tokens via browser automation (when cookie_source=BROWSER)
- Applies anti-detection delay in sequential mode (max_concurrent_downloads=1)
- Cleans up partial downloads on failure

---

### _download_segment

Location: `vkdownloader.services.segment_downloader`

Download a single HLS segment with optional retry backoff for sequential mode.

```python
async def _download_segment(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    max_concurrent_downloads: int = 1,
    segment_index: int = 0,
) -> bool:
    ...
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| session | aiohttp.ClientSession | Required | aiohttp session for HTTP requests. |
| segment_url | str | Required | URL of the segment to download. |
| output_path | Path | Required | Path to save the downloaded segment. |
| headers | dict[str, str] | Required | Request headers to use. |
| max_concurrent_downloads | int | 1 | Maximum concurrent downloads; when 1, uses retry with backoff. |
| segment_index | int | 0 | Index of the segment being downloaded (for logging). |

**Returns:** True on success, False on failure.

**Behavior:**
- When `max_concurrent_downloads=1`: Uses `_retry_429_with_backoff` for rate-limited downloads
- When `max_concurrent_downloads>1`: Uses direct download without retry backoff

---

### download_with_ytdlp_with_resume_fallback

Location: `vkdownloader.services.downloader`

Download using yt-dlp with automatic segment-based resume fallback on failure.

**Flow:**
1. Try yt-dlp download
2. On failure with partial file: get fresh token via browser (forced) + switch to segment download
3. Segment download resumes from last checkpoint

**Note:** Token refresh during resume always forces browser launch, regardless of `cookie_source` setting.

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
| `backoff_coordinator` | URLBackoffCoordinator \| None | For shared rate limiting across URLs. |
| `progress_callback` | Callable[[str, int, int], None] \| None | Callback for per-URL segment progress (video_id, downloaded, total). |
| `semaphore` | asyncio.Semaphore \| None | Shared semaphore for work-stealing concurrency. |

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
| `Q1440` | "1440" |
| `Q2160` | "2160" |
| `BEST` | "best" |
| `WORST` | "worst" |

---

### StreamFormat

Location: `vkdownloader.models.enums`

Stream format types.

| Value | Description |
|-------|-------------|
| `HLS` | "hls" |
| `MP4` | "mp4" |

### LogLevel

Location: `vkdownloader.models.enums`

Standard logging level options for configuring application logging output.

| Value | Description |
|-------|-------------|
| `DEBUG` | "DEBUG" — Detailed debugging information |
| `INFO` | "INFO" — Confirmation of normal operation (default) |
| `WARNING` | "WARNING" — Indication something unexpected happened |
| `ERROR` | "ERROR" — Error event occurred, application continues |
| `CRITICAL` | "CRITICAL" — Serious error, application may not continue |

**Usage:**
```python
from vkdownloader.config import Settings
from vkdownloader.models.enums import LogLevel

settings = Settings(log_level=LogLevel.DEBUG)
```

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

### CookieSource

Location: `vkdownloader.models.enums`

Cookie acquisition strategy for video downloads. Controls whether browser is launched for cookie extraction.

| Value | Description |
|-------|-------------|
| `NONE` | "none" — No browser launch, fastest for public videos only (default) |
| `BROWSER` | "browser" — Launch browser to extract real cookies for authenticated content |
| `FILE` | "file" — **Rejected with ValueError**. Not implemented; use `none` or `browser` instead |

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

### ProgressManager

Location: `vkdownloader.services.downloader_throttle`

Thread-safe progress state manager for concurrent batch downloads. Encapsulates progress state and asyncio.Lock for safe concurrent access across multiple download tasks.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `_state` | dict[int, tuple[int, int]] | Progress state keyed by URL index |
| `_lock` | asyncio.Lock | Lock for thread-safe state access |

**Methods:**
| Method | Description |
|--------|-------------|
| `update(url_index, downloaded, total)` | Thread-safe progress state update |
| `get_formatted_progress(url_count)` | Returns formatted string for all URLs |
| `clear()` | Clear progress state for new batch |
| `get_progress(url_index)` | Get progress tuple for specific URL |

---

### URLBackoffCoordinator

Location: `vkdownloader.services.downloader_throttle`

Manages shared backoff state per URL for coordinated rate limiting during batch downloads. When a 429 response occurs on any segment of a URL, all segments pause to avoid cascading rate limit violations.

**Methods:**
| Method | Description |
|--------|-------------|
| `pause(video_url, duration_seconds)` | Set backoff duration for URL |
| `wait_if_paused(video_url)` | Block until backoff expires, returns True if was paused |

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

### _sanitize_title

Location: `vkdownloader.utils.security`

Sanitizes video titles for filesystem safety by removing invalid characters.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| title | str | Video title to sanitize. |

**Returns:** Sanitized title string.

**Behavior:** Replaces characters invalid on Windows/Unix filesystems (`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`) with underscores, strips whitespace, and limits length to 100 characters.

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

Application settings with defaults and environment variable support. Uses Pydantic BaseSettings for validation.

**Key Attributes:**
| Name | Default | Description |
|------|---------|-------------|
| `headless` | `False` | Run Playwright browser in headless mode (no visible GUI); enables server, CI, and Docker usage |
| `user_agent` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` | User agent string for requests |
| `timezone` | `Europe/Moscow` | Timezone for stealth configuration |
| `locale` | `ru-RU` | Locale for browser stealth |
| `max_retries` | `3` | Maximum retry attempts (1-10) |
| `download_timeout` | `300` | Download timeout in seconds (30-3600) |
| `ssl_verify` | `True` | Verify SSL certificates for CDN connections |
| `download_dir` | `~/Downloads/vkdownloader` | Directory for downloaded videos |
| `max_concurrent_downloads` | `4` | Maximum concurrent downloads (1-16) |
| `throttled_rate` | `100000` | Minimum bytes/sec before throttling triggers re-extract |
| `http_chunk_size` | `10485760` | HTTP chunk size for segment downloads |
| `cookie_source` | `NONE` | Cookie acquisition strategy: none, browser (file is not implemented) |
| `log_level` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `log_file` | `None` | Optional log file path for file output |


