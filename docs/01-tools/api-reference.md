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
  - vkdownloader-limitations
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

Extract streams using browser automation to capture cookies for CDN authentication.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| url | str | Required | VK video URL to extract streams from. |
| force_browser | bool | False | Force browser launch even when cookie_source=NONE (for token refresh scenarios). |

**Returns:** Tuple of (streams list, cookies string) for CDN headers.

**Behavior:**
- When `cookie_source=NONE` and `force_browser=False`: Returns streams without cookies via yt-dlp
- When `cookie_source=BROWSER`: Launches browser, captures cookies from active session
- When `force_browser=True`: Forces browser launch regardless of cookie_source setting

**Raises:** `ValueError` if URL does not contain valid video identifier.
`VideoNotFoundError` if no streams are found.

---

### QualitySelector

Location: `vkdownloader.services.quality`

Selects appropriate stream from available streams based on quality preference.

```python
from vkdownloader.models.quality import QualitySpec
from vkdownloader.services.quality import QualitySelector

selector = QualitySelector()
```

#### `select(streams: list[Stream], quality: QualitySpec) -> Stream`

Select a stream based on quality preference.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| streams | list[Stream] | List of available streams to choose from. |
| quality | QualitySpec | Parsed quality request (a keyword or an exact height). |

**Returns:** Selected `Stream` object.

**Raises:** `QualityNotAvailableError` if the streams list is empty, or if an exact request matches no stream. The error carries the requested token and the available labels.

**Selection by `quality.kind`:**
| Kind | Behavior |
|------|----------|
| `QualityKind.BEST` | Stream with the highest usable `height` (a `height <= 0` placeholder is treated as absent) |
| `QualityKind.WORST` | Stream with the lowest usable `height` (same placeholder rule) |
| `QualityKind.EXACT` | The stream whose `quality` label matches the request exactly; there is no fallback to a lower quality |

**Example:**
```python
from vkdownloader.models.quality import QualitySpec

stream = selector.select(video.streams, QualitySpec.parse("1072"))
```

#### `list_available_qualities(streams: list[Stream]) -> list[str]`

Get sorted list of available quality options from streams.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| streams | list[Stream] | List of available streams. |

**Returns:** Sorted list of unique quality strings in descending order by resolution. A label with no numeric height (the `unknown` label) sorts last.

**Example:**
```python
qualities = selector.list_available_qualities(video.streams)
# Returns: ["1610p", "1072p", "804p", "536p"]
```

---

---

### DownloaderThrottle

Location: `vkdownloader.services.downloader_throttle`

> **Renamed:** This class was renamed to `URLBackoffCoordinator`. See the `URLBackoffCoordinator` section below for current API.

**Deprecated name:** `DownloaderThrottle` (no longer exists in this module)

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

### RichProgressReporter

Location: `vkdownloader.services.progress_display`

Multi-line `rich` progress display for concurrent batch downloads. Renders one self-overwriting progress line per active download on stderr; when the output stream is not a terminal it disables itself and emits throttled structlog INFO events instead, so piped and CI output contains no escape codes.

```python
from vkdownloader.models.enums import ProgressStatus
from vkdownloader.services.progress_display import RichProgressReporter

reporter = RichProgressReporter()
reporter.start()
try:
    reporter.start_task(0)
    reporter.set_title(0, "Morning in the city")
    reporter.update(0, 45, 100)
    reporter.finish_task(0, ProgressStatus.SUCCESS)
finally:
    reporter.stop()
```

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `console` | rich.console.Console \| None | None | Console to render on. Built lazily as `Console(stderr=True)` in `start()` when omitted. |
| `enabled` | bool \| None | None | Force the display on or off. When None, the display is enabled only if the console is a terminal. |
| `refresh_per_second` | float | 10.0 | Live display refresh rate in Hz. Internal escape hatch only: it is not exposed through `Settings` or any CLI option, and changing it requires wiring it through configuration. |

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `is_enabled` | bool (property) | Whether the rich live display is active for this reporter. |

**Methods:**
| Method | Description |
|--------|-------------|
| `start()` | Open the live display. Idempotent; a no-op when disabled. |
| `stop()` | Close the live display and restore captured state. Safe without `start()` and idempotent. |
| `start_task(index, title=None)` | Register a new progress line for `index`. |
| `set_title(index, title)` | Rewrite the description of an existing line, e.g. from `video_0` to `video_0: {title}`. |
| `update(index, downloaded, total)` | Advance the line. `total <= 0` means unknown size and keeps the bar indeterminate. |
| `finish_task(index, status)` | Mark `index` terminal and render its status marker. |

**Behavior:**
- Labels are `video_{index}`, or `video_{index}: {title}` once a title is known (truncated at 60 characters)
- Columns are status marker, label, bar, percentage, transfer speed and ETA
- The percentage column is fed the raw `(downloaded, total)` pair from the download callback and does not label its unit, because the sources disagree: yt-dlp reports byte counts (`total=0` when the size is unknown) and the HLS segment path reports segment counts. Under `--method auto` the method is resolved per video, so one batch screen can show byte percentages and segment percentages side by side. This is a known, accepted limitation: rich's `DownloadColumn` would render segment counts as byte counts, which is more misleading than an unlabelled percentage
- A finished task keeps its label and gains an outcome word, prefixed by a status marker taken from `ProgressStatus`: `SUCCESS` `[✓] done`, `FAILED` `[✗] failed`, `SKIPPED` `[⊘] skipped`, `CANCELLED` `[⊘] cancelled`
- A successful task with a known total is completed to 100%; other terminal statuses leave the bar where it stopped
- Root `StreamHandler` log streams are re-pointed onto the live display while it is open and restored on `stop()`, so log lines print above the display and it resumes below them. The log record format itself is unchanged — structlog's `ConsoleRenderer` is still the renderer — but the re-pointed console stream is rich's `FileProxy`, which splits writes on newlines and passes them to `Console.print`; that word-wraps at the terminal width, so a log line longer than the terminal is rendered across several rows while the display is open. Log files are unaffected: `setup_logging` attaches a `logging.FileHandler` for `VKDOWNLOADER_LOG_FILE` and the re-pointing skips `FileHandler` instances, so file output stays byte-identical
- When disabled, `update()` emits a `download_progress` INFO event throttled to at most one per second per index, and `finish_task()` emits a single `download_finished` INFO event

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
| `quality` | str | Required | Quality token as a plain string: `best`, `worst`, `unknown`, or any offered height (e.g. "720", "1072"). A numeric token becomes the yt-dlp format selector `best[height<=N]`. Not a `QualitySpec`. |
| `output_file` | Path | Required | Output file path. |
| `method` | DownloadMethod | Required | Download method (YTDLP or AUTO). |
| `extractor` | VKVideoExtractor \| None | None | Optional extractor instance. |
| `settings` | Settings \| None | None | Optional settings instance. |
| `backoff_coordinator` | URLBackoffCoordinator \| None | None | URLBackoffCoordinator for shared rate limiting across batch URLs. |
| `video_semaphore` | asyncio.Semaphore \| None | None | Per-video semaphore for concurrency control. One permit per video, acquired once in `perform_download` (D-01). |
| `progress_callback` | Callable[[str, int, int], None] \| None | None | Callback reporting `(video_id, downloaded, total)`: byte counts on the yt-dlp path (`total` is `0` when the size is unknown) and segment counts on the HLS segment path. Drives the batch progress display. |
| `video_data` | VideoWithStreams \| None | None | Optional pre-extracted video data with streams. When provided, skips extraction. |
| `selected_stream` | Stream \| None | None | Optional pre-selected stream. When provided, used instead of streams[0]. |
| `echo` | bool | True | Keyword-only. When False, suppresses yt-dlp's native console echo; parsed byte counts are logged at DEBUG level as `ytdlp_progress_suppressed` and still reach `progress_callback`. Governs the yt-dlp path only. |

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
    progress_callback=None,
)
result = await download_hls_with_resume(
    request,
    settings=settings,
    extractor=extractor,
)
```

**Features:**
- Downloads segments individually with progress tracking
- Resumes from last downloaded segment on interruption
- Playlist signature validation: stores SHA-256 hash of segment URLs in `.signature` file; stale segments from a previous playlist are automatically cleared on resume
- Refreshes expired m3u8 tokens via browser automation (when cookie_source=BROWSER)
- Applies anti-detection delay in sequential mode (max_concurrent_downloads=1)
- Preserves partial segments on failure for segment-level resume; cleans up only on successful merge
- Checks the output volume's free space before the merge starts: the batched merge writes its output while its input is still on disk, so it needs the segment bytes twice plus a safety margin. A volume that is short fails before any merge subprocess runs, with a message naming the bytes required and the bytes available; the segments are preserved for resume. See [Segment Merge Disk Space](../11-guides/vkdownloader-limitations.md#segment-merge-disk-space) for the measured amplification factor and the limits of the check

**Raises:** `DownloadError` if the output volume does not have the free space the merge requires.

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
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_url: str | None = None,
    max_retries: int = 3,
    download_timeout: int = 300,
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
| max_concurrent_downloads | int | 1 | Maximum concurrent downloads; when 1, uses sequential retry with backoff. |
| segment_index | int | 0 | Index of the segment being downloaded (for logging). |
| backoff_coordinator | URLBackoffCoordinator \| None | None | URLBackoffCoordinator for shared rate limiting across batch URLs. |
| video_url | str \| None | None | Original video URL for coordinator keying (required if coordinator provided). |
| max_retries | int | 3 | Maximum retry attempts for rate-limited (429/5xx) responses. |
| download_timeout | int | 300 | Total timeout for HTTP request in seconds. |

**Returns:** True on success, False on failure.

**Behavior:**
- When `max_concurrent_downloads=1`: Uses `_retry_429_with_backoff` for rate-limited downloads
- When `max_concurrent_downloads>1`: Uses `_run_parallel_download_with_backoff` which implements full AWS Full Jitter backoff via the shared `URLBackoffCoordinator` (same backoff as sequential mode, plus coordinator pause for batched rate limit coordination)

---

### download_with_ytdlp_with_resume_fallback

Location: `vkdownloader.services.ytdlp_downloader`

Download using yt-dlp with automatic segment-based resume fallback on failure.

**Flow:**
1. Try yt-dlp download
2. On failure with partial file: get fresh token via browser (forced) + switch to segment download
3. Segment download resumes from existing segment files on disk

**Note:** Token refresh during resume always forces browser launch, regardless of `cookie_source` setting.

**Backoff (SRV-006):** Between yt-dlp retry attempts, a jittered backoff delay is computed via `_compute_backoff_delay` and applied via `_wait_with_shutdown`. If a `backoff_coordinator` (URLBackoffCoordinator) is provided, its `wait_if_paused` method is also consulted before each retry.

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
| `progress_callback` | Callable[[str, int, int], None] \| None | Callback reporting `(video_id, downloaded, total)`: byte counts on the yt-dlp path (`total` is `0` when the size is unknown) and segment counts on the HLS segment path. Drives the batch progress display. |

> **Note:** Service objects (`settings`, `extractor`, `backoff_coordinator`, `video_semaphore`) are passed as function arguments to `download_hls_with_resume`, not as model attributes.

---

### Stream

Location: `vkdownloader.models.video`

Represents a video stream with URL and quality information.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| url | str | Stream URL |
| format | StreamFormat | Stream format (HLS, MP4) |
| quality | str | Quality label written by the extractor: `{height}p` (e.g. "1072p"), or `unknown` when the height is unavailable |
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

### QualitySpec

Location: `vkdownloader.models.quality`

A validated quality request: a selection keyword (`best` / `worst`) or the exact quality label of a single stream. VK height ladders are non-standard, so a request cannot be modelled as a closed enum of resolutions. Frozen Pydantic v2 model, re-exported from `vkdownloader.models`.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| kind | QualityKind | How the request is resolved against the available streams. |
| label | str \| None | Quality label matched exactly; set only for `QualityKind.EXACT` (e.g. `"1072p"`). |

**Methods:**
| Method | Description |
|--------|-------------|
| `QualitySpec.parse(raw: str) -> QualitySpec` | Classmethod. Parses a user-supplied token. Accepted: `best`, `worst`, `unknown`, or any positive height in pixels with an optional trailing `p` (`720`, `720p`, `1072`). Case-insensitive, surrounding whitespace ignored, empty value falls back to `best`. Raises `QualityParseError` otherwise. |
| `matches(stream_label: str) -> bool` | True for an exact request whose label equals `stream_label` (the numeric form without the `p` suffix is accepted too). A `best` / `worst` request never matches a single label. |
| `__str__() -> str` | The canonical token: `"1072"` for an exact height, otherwise the keyword. This is the string handed to the yt-dlp format selector as `best[height<=1072]`. |

**Example:**
```python
from vkdownloader.exceptions import QualityParseError
from vkdownloader.models.quality import QualitySpec

spec = QualitySpec.parse("1072p")
spec.kind    # QualityKind.EXACT
spec.label   # "1072p"
str(spec)    # "1072"
spec.matches("1072p")   # True
spec.matches("1610p")   # False

try:
    QualitySpec.parse("720x")
except QualityParseError as exc:
    print(exc.quality)  # "720x"
```

**Note:** the model validator rejects a structurally invalid state: `QualityKind.EXACT` without a non-empty label, and a `best` or `worst` request carrying a label.

---

## Enums

### QualityKind

Location: `vkdownloader.models.enums`

How a quality request is resolved against the streams of a video. Replaces the former closed `QualityEnum` of fixed resolutions, which could not express the non-standard height ladders VK publishes.

| Value | Description |
|-------|-------------|
| `BEST` | "best" — the stream with the highest usable height |
| `WORST` | "worst" — the stream with the lowest usable height |
| `EXACT` | "exact" — one stream, matched on its quality label |

---

### QualityLabel

Location: `vkdownloader.models.enums`

Fixed stream quality labels written onto `Stream` records by the extractor. These are labels, not user selection modes.

| Value | Description |
|-------|-------------|
| `UNKNOWN` | "unknown" — the label on a stream whose height cannot be determined (browser HLS capture); the label `--quality unknown` matches |

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
| `AUTO` | "auto" — Tries yt-dlp first, falls back to segment download on failure (default) |

**Example:**
```python
from vkdownloader.models.enums import DownloadMethod
from vkdownloader.services.downloader import perform_download

result = await perform_download(
    url="https://vkvideo.ru/video-123_456",
    quality="720",
    output_file=Path("output.mp4"),
    method=DownloadMethod.AUTO,
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

---

## Infrastructure

### BrowserManager

Location: `vkdownloader.infrastructure.browser`

Async context manager for Playwright browser automation. Anti-detection measures are applied only when `stealth_enabled` is true.

**Methods:**
| Method | Description |
|--------|-------------|
| `create_stealth_page() -> Page` | Create a new page with the configured browser context identity; injects stealth.min.js when `stealth_enabled` is true |

---

### NetworkMonitor

Location: `vkdownloader.infrastructure.network_monitor`

Monitors network traffic to capture m3u8 URLs from responses. The captured
address set is constrained to HLS-only (path suffix ``.m3u8``) via ``select()``;
if every captured address would be rejected, the filter is suspended and the
unconstrained set is returned with a single warning logged.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| m3u8_urls | list[str] | List of captured m3u8 URLs |

**Methods:**
| Method | Description |
|--------|-------------|
| `select() -> list[str]` | Return HLS-only addresses (NET-008 filter) with safety suspension. Never raises. Media playlists ranked first. |
| `_classify_hls(address: str) -> bool` | Local duplicate of `extractor._classify_format` (NET-008). Returns True when the URL path suffix is `.m3u8`. |
| `_classify_playlist(body: bytes \| None)` | Three-valued media-over-master rank from a playlist body (media/master/unclassified). Rank only, never a filter. |

---

### ProgressManager

Location: `vkdownloader.services.downloader_throttle`

Thread-safe progress state manager for concurrent batch downloads. Encapsulates progress state and asyncio.Lock for safe concurrent access across multiple download tasks.

> **Note:** This class is retained for backward compatibility. The batch progress display is no longer driven by `ProgressManager`; it is handled by `RichProgressReporter` in `services/progress_display.py`, and nothing in the batch path instantiates this class.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| `_state` | dict[int, tuple[int, int]] | Progress state keyed by URL index |
| `_lock` | asyncio.Lock | Lock for thread-safe state access |

**Methods:**
| Method | Description |
|--------|-------------|
| `update(url_index, downloaded, total)` | Async progress state update under the lock |
| `update_sync(url_index, downloaded, total)` | Synchronous progress-callback update delivered on the event loop thread; direct dict assignment without lock protection |
| `get_formatted_progress(url_count)` | Returns formatted string for all URLs |
| `clear()` | Clear progress state for new batch |

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

### sanitize_title

Location: `vkdownloader.utils.security`

Sanitizes video titles for filesystem safety by removing invalid characters.

```python
def sanitize_title(title: str) -> str:
    ...
```

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

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| requested | str | The requested quality token, verbatim (e.g. "1072"). |
| available | list[str] | The quality labels the video does offer. |

**Raised by:**
- `QualitySelector.select()` — When an exact request matches no stream, and when the streams list is empty

---

### QualityParseError

Location: `vkdownloader.exceptions`

Raised when a quality token is neither a keyword nor a positive height.

**Attributes:**
| Name | Type | Description |
|------|------|-------------|
| quality | str | The token that failed to parse. |

**Raised by:**
- `QualitySpec.parse()` — When the token is not `best`, `worst`, `unknown`, or a positive height in pixels

**Note:** through the CLI this is caught by the `--quality` argument callback, which turns it into a usage error with exit code `2` before the command body runs.

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

**Settings attributes are documented in the [Configuration Guide](../11-guides/configuration.md), the single source of truth for all settings, environment-variable mappings, defaults, and valid ranges.**


