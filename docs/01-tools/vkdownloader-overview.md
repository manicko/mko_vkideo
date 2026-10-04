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
| YtDlpDownloader | `services/ytdlp_downloader.py` | yt-dlp subprocess management, cookie-file lifecycle, retry-with-fallback |
| URLBackoffCoordinator | `services/downloader_throttle.py` | Coordinates backoff across batch URLs for 429/5xx errors (AWS Full Jitter) |
| RichProgressReporter | `services/progress_display.py` | Multi-line rich progress display for concurrent batch downloads |
| ProgressManager | `services/downloader_throttle.py` | Progress state manager retained for backward compatibility; no longer used by the batch path |
| SegmentDownloader | `services/segment_downloader.py` | Segment-level download orchestration with resume support |

### Download Functions

| Function | Module | Responsibility |
|----------|--------|----------------|
| `perform_download()` | `services/downloader.py` | Main entry: download method routing (yt-dlp, auto); takes the quality as a plain token string, and the stream is pre-selected by the caller |
| `download_video()` | `services/downloader.py` | Extract-select-download pipeline: extraction, quality selection from a `QualitySpec`, perform_download dispatch |
| `download_hls_with_resume()` | `services/segment_downloader.py` | Segment-level download with token refresh and anti-detection throttling |
| `download_with_ytdlp_with_resume_fallback()` | `services/ytdlp_downloader.py` | yt-dlp download with segment fallback on failure (SRV-006: includes inter-retry backoff) |

### Infrastructure

| Component | Module | Responsibility |
|-----------|--------|----------------|
| BrowserManager | `infrastructure/browser.py` | Playwright browser lifecycle management (user agent, locale, timezone; stealth is opt-in via `stealth_enabled`) |
| NetworkMonitor | `infrastructure/network_monitor.py` | Captures m3u8 URLs from browser network traffic |
| **_retry_429_with_backoff** | `services/downloader_throttle.py` | AWS Full Jitter backoff for rate-limited segment downloads |

### Models

| Model | Module | Description |
|-------|--------|-------------|
| `Video` | `models/video.py` | Basic video metadata |
| `Stream` | `models/video.py` | Video stream with URL and quality info |
| `VideoWithStreams` | `models/video.py` | Video model with available streams |
| `HLSDownloadRequest` | `models/dtos.py` | Request model for segment-level resume download |
| `QualitySpec` | `models/quality.py` | Validated quality request (a keyword or one exact stream label), parsed from the `--quality` token |

### Enums

| Enum | Module | Description |
|------|--------|-------------|
| `QualityKind` | `models/enums.py` | How a quality request is resolved against the streams (`best`, `worst`, `exact`) |
| `QualityLabel` | `models/enums.py` | Fixed stream quality labels the extractor stamps on a stream (`unknown`) |
| `StreamFormat` | `models/enums.py` | Stream format types (HLS, MP4) |
| `DownloadMethod` | `models/enums.py` | Download method selection (yt-dlp, auto) |
| `CookieSource` | `models/enums.py` | Cookie acquisition strategy (`none`, `browser`; `file` was removed as unimplemented) |
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
|----------|--------|----------------|
| `validate_output_path()` | `utils/security.py` | Prevents path traversal attacks |
| `sanitize_title()` | `utils/security.py` | Sanitizes titles for filesystem safety |
| `_strip_auth_params()` | `utils/url_sanitizer.py` | Strips tokens from URLs in logs |
| `sanitize_url_for_log()` | `utils/url_sanitizer.py` | Public alias for `_strip_auth_params` (used by CLI entry layer) |

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
           └── AUTO ──► download_with_ytdlp_with_resume_fallback()
                          (fallback to segment download on failure)
```

## Configuration

The `Settings` class in `config.py` provides:

- **Browser settings**: User agent, locale, timezone for browser context identity; `headless` mode toggle for server/CI/Docker
- **Download settings**: Timeout, concurrent downloads, output directory, download method
- **Security settings**: SSL verification (enabled by default)
- **Logging settings**: Log level and optional file output

## CLI Interface

The CLI (`cli.py`) provides two commands:

- `download`: Download single video with quality and method selection
- `batch`: Download multiple videos from a URL file

Both commands support:

- `--quality`: Quality selection — `best`, `worst`, `unknown`, or any height in pixels the video offers (e.g. `720`, `1080`, `1072`). Any other token is a usage error (exit code 2) raised while the command line is parsed. See the [Quality Selection Guide](quality-selection.md).
- `--method`: Download method (yt-dlp, auto)
- `--output/-o`: Output directory (defaults to `Settings.download_dir` when not provided)

## Download Methods

| Method | Speed | Reliability | Notes |
|--------|-------|-------------|-------|
| `yt-dlp` | ~100KB/s | High | Handles token refresh automatically, fallback to segments |
| `auto` | Variable | High | Tries yt-dlp first, falls back to segment download on failure |

## Security Features

- Path traversal prevention via `validate_output_path()`
- Authentication token stripping from logged URLs
- SSL verification enabled by default
- Opt-in browser stealth configuration (`stealth_enabled`, off by default)
- Title sanitization for filesystem safety via `sanitize_title()`
- **Secret-safe cookie passing**: VK session cookies are written to a temporary Netscape cookie file (requested at `0o600`, owner-only on POSIX only, with the same Windows caveat as above) and passed to the yt-dlp subprocess as `--cookies <path>` in argv. Only the file **path** appears in process listings (`ps`, `/proc/<pid>/cmdline`, `htop`, `docker inspect`); the **contents** (signed CDN URLs and session tokens) do not. The path exposure is moot for this single-user desktop deployment (D1), but is tracked by phase 06's `SEC-006`. The temporary file is removed automatically after the download completes.
- **Subprocess process boundary**: every subprocess spawn (yt-dlp and ffmpeg merge stages) starts a new process session/group (`start_new_session=True` on POSIX, `CREATE_NEW_PROCESS_GROUP` on Windows). On POSIX this lets the termination ladder signal descendants via `os.killpg`; on Windows the group is console-signal routing only and descendants the child started for itself can survive — see the [limitations guide](vkdownloader-limitations.md#subprocess-process-boundary-trn-003) for the Windows residual and how to clean up manually.

## Rate Limiting & Throttling

### AWS Full Jitter Backoff

The `URLBackoffCoordinator` in `downloader_throttle.py` implements rate limiting for VK's anti-bot protection:

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

## Batch Download Architecture

### Shared Concurrency Control

All URLs in a batch share a single `asyncio.Semaphore` that gates **video-level** concurrency. The semaphore's `max_concurrent_downloads` limit (from Settings) controls the total number of concurrent video downloads across all URLs in the batch. Each video's segment fan-out is bounded by a separate semaphore owned by the segment layer, sized by the same setting. This design enables **work stealing**: when one video finishes downloading, its acquired permit is immediately released and available for remaining URLs.

A third level is bounded by the same setting on the HLS segment path: each segment download builds its own aiohttp `TCPConnector`, sized to `max_concurrent_downloads` for both the total and the per-origin ceiling, so the transport never clips what the operator asked for. The two ceilings carry the same value deliberately — a per-origin ceiling equal to the total can never be the binding term — so the per-origin one is **intentionally non-binding** and is not a second, separately tunable limit.

That connector is per download, so there is **no process-wide pool and no process-wide bound**. On the segment path a concurrent video can hold up to `max_concurrent_downloads` connections, so the batch aggregate is this setting squared: 16 concurrent connections at the default `4`, and 256 at the ceiling `16` — with nothing capping it. On the yt-dlp path the same value is passed to yt-dlp as `-N`, which runs in a **separate child process** with its own sockets and never touches this connector: the same squaring, different sockets. Under `--method auto` the method is resolved per video, so one batch can hold both kinds at once.

```
Batch Download Flow
    │
    ▼
┌─────────────────┐
│  Shared Semaphore │
│  (max_concurrent)│
│  one permit per   │
│  video            │
└────────┬────────┘
          │
          ▼
┌──────────────────────────────────┐
│  All URLs start immediately       │
│  (up to max_concurrent total)   │
└──────────────────────────────────┘
          │
          ├──► video_1 ──► performs download ──► [seg1][seg2][seg3]... (uses own local semaphore)
          ├──► video_2 ──► performs download ──► [seg1][seg2][seg3]... (uses own local semaphore)
          └──► video_3 ──► performs download ──► [seg1][seg2][seg3]... (uses own local semaphore)
          
As videos complete, permits return to the pool and are immediately reallocated
to remaining URLs. Each video's segment fan-out never re-acquires from the batch semaphore.
```

### Batch Progress Display

The `RichProgressReporter` in `services/progress_display.py` renders one live progress line per currently active download. The display is a `rich` live multi-line view written to **stderr** and refreshed 10 times per second, so concurrent downloads no longer overwrite each other's output.

Each line is labelled `video_{N}` while the video is still being extracted and `video_{N}: {sanitized_title}` once the title is known, and shows a status marker, the download bar, a percentage, the transfer speed and an ETA:

```
$ vkdownloader batch urls.txt

    video_2                        ━━━━╸━━╸━━━━━━━━   12%  1.8MB/s  0:00:31
    video_0: Morning in the city   ━━━━━━━━━━╸━━━━━━━━  45%  2.4MB/s  0:00:18
    video_1: Night walk            ━━╸╸╸╸╸╸╸╸╸╸╸╸╸━   8%     ?  -:--:--
[✓] video_2: Sunset timelapse done ━━━━━━━━━━━━━━━━━━━ 100%  3.0MB/s  0:00:00

2026-09-28T13:06:16.130710Z [warning  ] segment_retry_429              attempt=1 segment_index=17 status=429
    video_0: Morning in the city   ━━━━━━━━━━━╸━━━━━━━━  48%  2.1MB/s  0:00:17
[✓] video_0: Morning in the city done ━━━━━━━━━━━━━━━━━ 100%  2.2MB/s  0:00:00
[✗] video_1: Night walk failed    ━━╸╸╸╸╸╸╸╸╸╸╸╸╸━   8%     ?  -:--:--
```

Where:
- `video_{N}`: sequential index of the video in the batch; the sanitized title is appended once known (truncated at 60 characters)
- Column order: status marker, label, bar, percentage, transfer speed, ETA
- A finished download becomes a status line that stays on screen and scrolls up with the display: the marker is `[✓]` for `done`, `[✗]` for `failed`, and `[⊘]` for `skipped` or `cancelled`, with the outcome word appended to the label
- When the batch ends, the terminal is restored to normal output

All download methods report an unknown total, so their bar pulses indeterminately and shows no percentage. Segment-count progress and yt-dlp byte progress both render a determinate bar with a percentage. The percentage column does not label its unit, and under `--method auto` the download method is resolved per video, so one batch screen can show byte percentages and segment percentages side by side — a known, accepted limitation.

yt-dlp's own native progress echo is suppressed while the display is active, so its lines cannot interleave with the bars. The same data still reaches the display through the progress callback, and the parsed byte counts are logged at DEBUG level as `ytdlp_progress_suppressed`. structlog INFO, WARNING and ERROR lines render above the live display, which resumes below them. The log record format is unchanged — structlog's `ConsoleRenderer` is still the renderer — but while the display is open the re-pointed console stream is rich's `FileProxy`, which passes each line to `Console.print` and word-wraps it at the terminal width, so a log line longer than the terminal spans several rows. Log files are not affected: `VKDOWNLOADER_LOG_FILE` is written by a `logging.FileHandler` that is never re-pointed, so file output is byte-identical throughout.

**Non-terminal output:** when stderr is not a TTY (piped, redirected, or CI) the live display is never started, so no escape codes reach the output. Progress falls back to structlog INFO events — `download_progress`, throttled to at most one per second per video, and `download_finished` — each carrying `video_index`, `video_label`, `downloaded`, `total` and, for the finished event, `status`. yt-dlp's echo stays on stderr in that case, as before.

Each URL's `_download_single()` task (in `services/batch_downloader.py`) drives the shared reporter: `start_task()` opens the line, `update()` advances it from the download callbacks, `set_title()` relabels it once the title is extracted, and `finish_task()` renders the terminal status.

### Work Stealing Behavior

URLs start immediately without waiting for previous downloads to complete. The shared semaphore ensures total concurrency never exceeds `max_concurrent_downloads` — one permit per video (acquired once per video in ``perform_download``; the segment layer does not re-acquire from it, per D-01):

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
├── downloader.py          (~350 lines)  - Orchestration (perform_download, download_video)
├── ytdlp_downloader.py    (~722 lines)  - yt-dlp subprocess management, cookie-file lifecycle, retry-with-fallback
├── segment_downloader.py  (~901 lines) - Segment download, playlist fetching, merging
├── ffmpeg_utils.py        (~360 lines) - FFmpeg commands, process management
└── downloader_throttle.py - Rate limiting, progress management, backoff coordination
```

The `downloader.py` module was split (SRV-001) into a focused orchestration layer and `ytdlp_downloader.py` (~722 lines). The `__all__` re-export facade in `downloader.py` preserves all public symbol paths for backward compatibility with 30+ test import sites.

All modules export their public APIs through `downloader.py` for backward compatibility.
