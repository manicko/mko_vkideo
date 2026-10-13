---
id: configuration-guide
domain: guides
tags:
  - config
  - settings
related:
  - vkdownloader-installation
  - vkdownloader-overview
---
# Configuration Guide

## Purpose

This guide documents all configuration options available in VK Video Downloader and their environment variable mappings.

## Settings Reference

All settings support environment variables via Pydantic Settings. Create a `.env` file to customize defaults. The file is read from the process's current working directory, so keep `.env` in the directory you invoke `vkdownloader` from — a `.env` in the project root is read only when the command is also run from the project root.

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `headless` | `VKDOWNLOADER_HEADLESS` | false | Run Playwright browser in headless mode (no visible GUI); required for server, CI, and Docker usage |
| `user_agent` | `VKDOWNLOADER_USER_AGENT` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` | User agent string for browser requests |
| `timezone` | `VKDOWNLOADER_TIMEZONE` | Europe/Moscow | Timezone for browser context |
| `locale` | `VKDOWNLOADER_LOCALE` | ru-RU | Locale for browser context |
| `stealth_enabled` | `VKDOWNLOADER_STEALTH_ENABLED` | false | Gates the browser anti-detection posture: when true, `--disable-blink-features=AutomationControlled` is passed to the chromium launch and `stealth.min.js` is injected as an init script. The `stealth.min.js` asset is a declared build artifact, so when this is true a missing asset is a hard error before the browser starts. Does NOT gate the browser context's viewport, user agent, locale or timezone (these are applied unconditionally as ordinary context identity). Off by default. |
| `browser_pre_interaction_wait` | `VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT` | 5 | Seconds to wait before video interaction in browser extraction (1-30) |
| `browser_post_interaction_wait` | `VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT` | 8 | Seconds to wait after video interaction in browser extraction (1-30) |
| `max_retries` | `VKDOWNLOADER_MAX_RETRIES` | 3 | Maximum retry attempts for failed segment and network requests (1-10) |
| `download_timeout` | `VKDOWNLOADER_DOWNLOAD_TIMEOUT` | 300 | Download timeout in seconds (30-3600). Does **not** bound the ffmpeg merge subprocesses — each merge stage has its own separate per-stage budget (see `_MERGE_STAGE_TIMEOUT` in `ffmpeg_utils`). On retryable HTTP failures (408, 425, 429, 5xx), the exponential backoff delay is capped at **30 seconds per request** — each request may wait up to that ceiling independently, so a batch of N concurrent videos may have multiple bounded waits in flight simultaneously |
| `download_stall_timeout` | `VKDOWNLOADER_DOWNLOAD_STALL_TIMEOUT` | 300.0 | Inactivity bound in seconds on the one-shot re-wait that follows the yt-dlp reader consuming the download stream — `process.wait()` after EOF on the child's stdout (30-3600); a child that keeps producing output is never killed, only one that has gone silent but not yet exited, and it is then terminated through the existing cancellation ladder (`cancel_subprocess`) with the resulting `TimeoutError` re-raised. This is **not** a whole-operation budget, so a download that keeps producing output runs for as long as it needs. It does not apply to the ffmpeg merge subprocesses, which use a separate per-stage budget (`_MERGE_STAGE_TIMEOUT`) |
| `backoff_pause_seconds` | `VKDOWNLOADER_BACKOFF_PAUSE_SECONDS` | 10 | Seconds a retryable transport failure pauses the origin before retrying, shared across all segment and manifest retries for that origin (1-120) |
| `ssl_verify` | `VKDOWNLOADER_SSL_VERIFY` | true | Verify SSL certificates |
| `download_dir` | `VKDOWNLOADER_DOWNLOAD_DIR` | ~/Downloads/vkdownloader | Output directory |
| `max_concurrent_downloads` | `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS` | 4 | Maximum number of videos downloading concurrently in a batch (1-16); the batch semaphore gates one permit per video, each video's segment fan-out is bounded by `max_concurrent_segments`, and each segment download's aiohttp connection pool is sized to this value for both the total and per-origin ceiling — 1 disables batch parallelism |
| `max_concurrent_segments` | `VKDOWNLOADER_MAX_CONCURRENT_SEGMENTS` | 4 | Maximum number of segments to download concurrently per video (1-16); governs the segment fan-out semaphore and yt-dlp's `-N` (fragment concurrency) flag. The batch-level video gate remains governed by `max_concurrent_downloads`. Setting this to 1 enables sequential segment download with an anti-detection delay |
| `throttled_rate` | `VKDOWNLOADER_THROTTLED_RATE` | 100000 | Minimum download rate in bytes/sec (50000-1000000). If yt-dlp's download rate falls below this threshold, yt-dlp aborts the download; the application then retries with a fresh token re-extract. Default is 100000 (100KB/s). |
| `http_chunk_size` | `VKDOWNLOADER_HTTP_CHUNK_SIZE` | 0 | HTTP chunk size in bytes (0-104857600) for yt-dlp range-request downloads. 0 disables the flag for reliable HLS segment downloads; non-zero values are for advanced users only |
| `cookie_source` | `VKDOWNLOADER_COOKIE_SOURCE` | none | Cookie acquisition strategy: none or browser |
| `log_level` | `VKDOWNLOADER_LOG_LEVEL` | INFO | Logging level |
| `log_file` | `VKDOWNLOADER_LOG_FILE` | None | Optional log file path |

## Headless Mode

### headless

Controls whether the Playwright browser runs with a visible window or headless:

- **`false`** (default) — Browser launches with a visible GUI window. Required for VK video pages that apply headless detection (see [Limitations](vkdownloader-limitations.md)).
- **`true`** — Browser runs headless (no GUI). Required for server, CI, and Docker environments without a display.

**Environment Variable:** `VKDOWNLOADER_HEADLESS`

```env
# For server / CI / Docker (no display)
VKDOWNLOADER_HEADLESS=true
```

> Note: VK applies multi-layer headless detection. Headless mode may be blocked for some videos; use non-headless (`false`) on a desktop when browser-based extraction fails.

## Cookie Source Settings

### cookie_source

Controls how cookies are acquired for authenticated video downloads:

- **`none`** (default) — No browser launch, fastest downloads for public videos only
- **`browser`** — Launch browser to extract real cookies for authenticated content

**Download Method Behavior:**
| Method | cookie_source=NONE | cookie_source=BROWSER |
|--------|-------------------|-------------------|
| `yt-dlp` | Uses yt-dlp, no cookies passed | Uses yt-dlp with browser cookies |
| `auto` | No browser involvement | Browser is launched for cookie resolution |

**Recovery Scenarios:**
When token refresh is needed (segment download on 403/410), the system forces browser launch regardless of `cookie_source` setting to recover from expired tokens.

**Example .env configuration:**
```env
# For public videos (no authentication needed)
VKDOWNLOADER_COOKIE_SOURCE=none

# For private/authenticated videos
VKDOWNLOADER_COOKIE_SOURCE=browser
```

## Example .env File

```env
# Browser settings
VKDOWNLOADER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
VKDOWNLOADER_DOWNLOAD_TIMEOUT=300
VKDOWNLOADER_SSL_VERIFY=true

# Download settings
VKDOWNLOADER_DOWNLOAD_DIR=~/Downloads/vkdownloader
VKDOWNLOADER_COOKIE_SOURCE=none

# Logging
VKDOWNLOADER_LOG_LEVEL=INFO
```

## Batch Download Configuration

### max_retries

Controls retry behavior for failed segment and network requests during both single and batch downloads.

- **CLI Flag:** `--max-retries` / `-r` (batch command only)
- **Environment Variable:** `VKDOWNLOADER_MAX_RETRIES`
- **Default:** `3` (range: 1-10)
- **Description:** Maximum retry attempts for failed segment and network requests (mapped to both yt-dlp `retries`/`fragment_retries` and the segment downloader policy). When a download fails (e.g., due to 403/404 errors), the system will automatically retry up to this number of attempts before marking the download as failed.

> **Note:** The `--max-retries` CLI flag is only available on the `batch` command. For single downloads, configure retries via the `VKDOWNLOADER_MAX_RETRIES` environment variable.

**Example:**
```env
VKDOWNLOADER_MAX_RETRIES=5
```

### max_concurrent_downloads

Controls the number of videos downloading concurrently in a batch.

- **CLI Flag:** Not available (use environment variable)
- **Environment Variable:** `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS`
- **Default:** `4` (range: 1-16)
- **Description:** The semaphore limit that controls how many concurrent video downloads can run across all URLs in a batch. The batch semaphore gates one permit per video (acquired once per video download) and is shared across the entire batch. Each segment download's aiohttp connection pool is sized to this value for both the total and the per-origin ceiling, so the transport never clips this setting. The segment fan-out within each video is governed separately by `max_concurrent_segments`.

  Each connection pool belongs to its own download, so there is **no process-wide pool and no process-wide bound**: the batch aggregate is `min(max_concurrent_segments, max_concurrent_downloads) × max_concurrent_downloads`. At the default (4, 4) this is 16 concurrent segment downloads; at the ceiling (16, 16) it is 256. On the yt-dlp path, `max_concurrent_segments` is passed to yt-dlp as `-N`, which runs in a separate child process with its own sockets and never touches the aiohttp connector. Setting this to `1` disables batch parallelism.

**Example for batch downloads:**
```env
VKDOWNLOADER_MAX_RETRIES=5
VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS=8
```

### max_concurrent_segments

Controls the number of segments downloaded concurrently within a single video.

- **CLI Flag:** Not available (use environment variable)
- **Environment Variable:** `VKDOWNLOADER_MAX_CONCURRENT_SEGMENTS`
- **Default:** `4` (range: 1-16)
- **Description:** Governs the per-item segment fan-out: the segment semaphore that bounds concurrent segment downloads within a video, and yt-dlp's `-N` (fragment concurrency) flag. The batch-level video gate remains governed by `max_concurrent_downloads`. The effective aggregate ceiling across all videos is `min(max_concurrent_segments, max_concurrent_downloads) × max_concurrent_downloads`. Setting this to `1` enables sequential segment download with an anti-detection delay.

**Example:**
```env
VKDOWNLOADER_MAX_CONCURRENT_SEGMENTS=8
```

## Security Settings

### ssl_verify

Controls SSL certificate verification for CDN connections.

- **Default: `true`** — Secure by default
- **Setting to `false`** — Logs a security warning; use only for edge cases

### log_level

Controls the verbosity of application logging output.

- **Default: `INFO`** — Standard operational logging
- **`DEBUG`** — Detailed debugging information including HTTP requests
- **`WARNING`** — Warnings and errors only
- **`ERROR`** — Errors only
- **`CRITICAL`** — Critical errors only

**Example:**
```env
VKDOWNLOADER_LOG_LEVEL=DEBUG
```

### log_file

Optional path to a file for structured JSON log output. When set, logs are written to this file instead of console.

**Example:**
```env
VKDOWNLOADER_LOG_FILE=/var/log/vkdownloader.log
```

### download_dir

Output directory for downloaded videos. Paths are validated to prevent path traversal attacks.

## Environment Variable Caveats

| Source | Typos behavior | Detection |
|--------|---------------|-----------|
| `.env` file | Unknown `VKDOWNLOADER_*` keys are **rejected** at construction with a `ValidationError` (due to `extra='forbid'`) | `warn_unknown_env_vars()` scans the `.env` file *before* construction and the entry point renders each unknown variable as a line on **stderr** (not a log record) |
| OS environment (`os.environ`) | Unknown `VKDOWNLOADER_*` keys are **silently ignored** (the default value is used) | `warn_unknown_env_vars()` detects and renders each unknown variable on **stderr** (not a log record) |

The CLI calls `warn_unknown_env_vars()` before each `Settings()` construction, so typos in either the `.env` file or OS environment are rendered on **stderr** — once per command, before logging is configured, one line per unknown variable — each line naming that variable and the set of valid variables. This is not a log record: it is emitted through `typer.echo(..., err=True)` and does not reach the configured log artifact. A `.env` file typo still causes a hard failure (ValidationError), so fix the typo and try again.

