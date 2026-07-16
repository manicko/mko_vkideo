---
id: vkdownloader-overview
domain: tools
tags:
  - overview
  - architecture
related:
  - vkdownloader-installation
  - vkdownloader-api-reference
  - configuration-guide
---
# VK Downloader Overview

## Purpose

VK Video Downloader is an async Python module for downloading videos from vkvideo.ru with intelligent quality selection. It combines yt-dlp for stream extraction with ffmpeg for direct HLS-to-MP4 conversion, featuring segment-level resume on token expiration.

## Main Concepts

### Core Services

| Service | Module | Responsibility |
|---------|--------|----------------|
| VKVideoExtractor | `services/extractor.py` | Extracts stream URLs from VK video URLs using yt-dlp or browser automation |
| QualitySelector | `services/quality.py` | Selects appropriate stream based on quality preference |
| HLSDownloader | `services/downloader.py` | Downloads HLS streams via ffmpeg integration |
| DownloaderThrottle | `services/downloader_throttle.py` | Rate limiting with AWS Full Jitter exponential backoff for 429/5xx errors |
| SegmentDownloader | `services/segment_downloader.py` | Segment-level download orchestration with resume support |

### Download Functions

| Function | Module | Responsibility |
|----------|--------|----------------|
| `perform_download()` | `services/downloader.py` | Main orchestration: quality selection + download method routing |
| `download_hls_with_resume()` | `services/segment_downloader.py` | Segment-level download with token refresh and anti-detection throttling |
| `download_with_ffmpeg()` | `services/downloader.py` | Direct ffmpeg download with real-time progress tracking |
| `download_with_ytdlp_with_resume_fallback()` | `services/downloader.py` | yt-dlp download with segment fallback on failure |

### Infrastructure

| Component | Module | Responsibility |
|-----------|--------|----------------|
| BrowserManager | `infrastructure/browser.py` | Playwright browser lifecycle management with stealth configuration (user agent, locale, timezone) |
| NetworkMonitor | `infrastructure/network_monitor.py` | Captures m3u8 URLs from browser network traffic |
| **_retry_429_with_backoff** | `services/downloader_throttle.py` | AWS Full Jitter backoff for rate-limited segment downloads |

### Models

| Model | Module | Description |
|-------|--------|-------------|
| `Video` | `models/video.py` | Basic video metadata |
| `Stream` | `models/video.py` | Video stream with URL and quality info |
| `VideoWithStreams` | `models/video.py` | Video model with available streams |
| `HLSDownloadRequest` | `models/dtos.py` | Request model for segment-level resume download |

### Enums

| Enum | Module | Description |
|------|--------|-------------|
| `QualityEnum` | `models/enums.py` | Quality options (240, 360, 480, 720, 1080, 1440, 2160, best, worst) |
| `StreamFormat` | `models/enums.py` | Stream format types (HLS, DASH, MP4) |
| `DownloadStatus` | `models/enums.py` | Download state tracking (pending, downloading, completed, failed) |
| `DownloadMethod` | `models/enums.py` | Download method selection (yt-dlp, ffmpeg, auto) |
| `CookieSource` | `models/enums.py` | Cookie acquisition strategy (`none`, `browser`; `file` is not implemented and raises `NotImplementedError`) |
| `LogLevel` | `models/enums.py` | Logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Exceptions

| Exception | Module | Description |
|-----------|--------|-------------|
| `VKDownloadError` | `exceptions.py` | Base exception for all errors |
| `VideoNotFoundError` | `exceptions.py` | Video or streams not found |
| `QualityNotAvailableError` | `exceptions.py` | Requested quality not available |
| `ExtractionError` | `exceptions.py` | Stream extraction failure |
| `DownloadError` | `exceptions.py` | Download or path validation failure |

### Security Utilities

| Function | Module | Responsibility |
|----------|--------|---------------|
| `validate_output_path()` | `utils/security.py` | Prevents path traversal attacks |
| `_sanitize_title()` | `utils/security.py` | Sanitizes titles for filesystem safety |
| `_strip_auth_params()` | `utils/url_sanitizer.py` | Strips tokens from URLs in logs |

## Architecture Flow

```
User Request
    │
    ▼
┌─────────────────┐
│  VKVideoExtractor │
│  (Extract streams)│
└────────┬────────┘
         │ Available streams
         ▼
┌─────────────────┐
│  QualitySelector │
│  (Select stream)  │
└────────┬────────┘
         │ Selected stream
         ▼
┌─────────────────┐
│  DownloadMethod  │
│  Routing (AUTO)   │
└────────┬────────┘
         │
         ├── YTDLP ──► download_with_ytdlp_with_resume_fallback()
         │              (fallback to segment on partial failure)
         │
         └── FFMPEG ──► download_with_ffmpeg() + extract_streams_with_cookies()
                        (with segment fallback on failure)
```

## Configuration

The `Settings` class in `config.py` provides:

- **Browser settings**: User agent, locale, timezone for stealth
- **Download settings**: Timeout, concurrent downloads, output directory, download method
- **Security settings**: SSL verification (enabled by default)
- **Logging settings**: Log level and optional file output

## CLI Interface

The CLI (`cli.py`) provides two commands:

- `download`: Download single video with quality and method selection
- `batch`: Download multiple videos from a URL file

Both commands support:

- `--quality`: Quality selection (240, 360, 480, 720, 1080, 1440, 2160, best, worst)
- `--method`: Download method (yt-dlp, ffmpeg, auto)
- `--output/-o`: Output directory (defaults to `Settings.download_dir` when not provided)

## Download Methods

| Method | Speed | Reliability | Notes |
|--------|-------|-------------|-------|
| `yt-dlp` | ~100KB/s | High | Handles token refresh automatically, fallback to segments |
| `ffmpeg` | ~1MB/s | Medium-High | Uses fresh browser cookies, faster but needs token refresh |
| `auto` | Variable | High | Tries yt-dlp first, falls back to segment download on failure |

## Security Features

- Path traversal prevention via `validate_output_path()`
- Authentication token stripping from logged URLs
- SSL verification enabled by default
- Secure-by-default browser stealth configuration
- Title sanitization for filesystem safety via `_sanitize_title()`

## Rate Limiting & Throttling

### AWS Full Jitter Backoff

The `DownloaderThrottle` module implements rate limiting for VK's anti-bot protection:

- **Exponential backoff**: Uses AWS Full Jitter algorithm (random(0, base_delay * 2^attempt))
- **Base delay**: 1 second for 429 responses, 0.05 seconds for 5xx errors
- **Retry-After support**: Honors server's Retry-After header when present
- **Max delay cap**: 30 seconds maximum delay
- **Retry codes**: 429 (Too Many Requests), 500, 502, 503, 504

### Anti-Detection Delay

In sequential download mode (`max_concurrent_downloads=1`), an additional anti-detection delay is applied:

- **Delay**: 1.5 seconds base + 0-0.5s random jitter between segment requests
- **Placement**: After semaphore release to avoid blocking the semaphore
- **Purpose**: Reduces detection risk by mimicking human-like request patterns

## Real-time Progress Tracking

### FFmpeg Progress Integration

The `download_with_ffmpeg()` function supports real-time progress updates:

- **`-progress pipe:2`**: FFmpeg outputs progress to stderr in KEY=VALUE format
- **`-nostats`**: Suppresses stdout noise, keeps output clean
- **`FfmpegProgress` dataclass**: Captures frame, fps, speed, total_size, out_time_us, out_time_ms, out_time, progress

### Progress Callback

```python
async def download_with_ffmpeg(
    m3u8_url: str,
    output_file: Path,
    quality: str = "best",
    cookies: str | None = None,
    progress_callback: Callable[[FfmpegProgress], None] | None = None,
) -> Path | None:
    ...
```

The `progress_callback` parameter is optional for backward compatibility. When provided, it receives `FfmpegProgress` objects during download for live progress bars and ETA calculation.

### ProgressParser

The `ProgressParser` class handles ffmpeg's KEY=VALUE output:

- `parse_line(line)` - Static method returning tuple of (key, value) or None
- Ignores lines without `=` separator
- Handles `N/A` values gracefully

### DownloadProgress Model Enhancement

The `DownloadProgress` model includes:

- `speed` - Bytes per second download rate
- `eta_seconds` - Estimated time to completion
- `percent` - Percentage completion (when duration known)

## Batch Download Architecture

### Shared Concurrency Control

All URLs in a batch share a single `asyncio.Semaphore` for segment downloads. The semaphore `max_concurrent_downloads` limit (from Settings) controls the total number of concurrent segment downloads across all URLs in the batch. This design enables **work stealing**: when one URL finishes downloading, its acquired semaphore permits are immediately released and available for remaining URLs.

```
Batch Download Flow
    │
    ▼
┌─────────────────┐
│  Shared Semaphore │
│  (max_concurrent)│
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────┐
│  All URLs start immediately       │
│  (up to max_concurrent total)   │
└──────────────────────────────────┘
         │
         ├──► video_1 ──► [seg1][seg2][seg3]... (uses shared permits)
         ├──► video_2 ──► [seg1][seg2][seg3]... (uses shared permits)
         └──► video_3 ──► [seg1][seg2][seg3]... (uses shared permits)
         
As segments complete on shorter videos, permits return to pool
and are immediately reallocated to remaining URLs.
```

### Per-URL Progress Tracking

Progress displays in a per-URL segment format showing download status for each video:

```
Progress Format:
video_1: 25/100, video_2: 45/150, video_3: 78/80

Where:
- video_N: Sequential index of the video in the batch
- X/Y: Downloaded segments / Total segments for that video
```

The progress updates in-place using `\r` overwrite for a clean single-line display. Each URL's `_download_single()` task updates progress via a shared `_progress_state` dictionary using `_create_progress_callback()`.

### Work Stealing Behavior

URLs start immediately without waiting for previous downloads to complete. The shared semaphore ensures total concurrency never exceeds `max_concurrent_downloads`:

- When video_1 completes (freed its permits), video_2 and video_3 can claim them
- Available concurrency is automatically reallocated to remaining downloads
- No manual coordination needed - semaphore naturally balances work allocation
- All URLs make progress simultaneously rather than sequentially

### Shared Backoff Coordination

When any segment receives a 429 (Too Many Requests) or 5xx response, the `URLBackoffCoordinator` coordinates backoff:

- `pause(video_url, duration)` sets backoff for the specific video URL
- All segments of that URL call `wait_if_paused()` before downloading
- Segments wait together during backoff to avoid cascading rate limits
- Other URLs continue downloading using available semaphore permits
- Backoff duration: 10 seconds default, with server `Retry-After` header honored

This prevents a single rate-limited video from causing all downloads to stall, while still respecting VK's rate limiting across the batch.

## Shutdown Handling

The `get_shutdown_event()` function provides an asyncio-aware shutdown mechanism:

- Uses `ContextVar` to avoid "bound to different event loop" errors
- Checked during segment downloads to enable graceful cancellation
- Integrated with signal handlers via `setup_signal_handlers()`
- Supports SIGINT/SIGTERM for clean interruption of ongoing downloads

## Module Architecture

The downloader module has been refactored into focused components per project rule #5:

```
services/
├── downloader.py        (~487 lines)  - Orchestration, ffmpeg integration
├── segment_downloader.py (~336 lines) - Segment download, playlist fetching, merging
└── ffmpeg_utils.py      (~269 lines)  - FFmpeg commands, progress parsing, process management
```

All modules export their public APIs through `downloader.py` for backward compatibility.
