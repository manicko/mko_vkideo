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

All settings support environment variables via Pydantic Settings. Create a `.env` file to customize defaults.

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `user_agent` | `VKDOWNLOADER_USER_AGENT` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` | User agent string for browser requests |
| `accept_language` | `VKDOWNLOADER_ACCEPT_LANGUAGE` | ru-RU,... | Accept-Language header for browser |
| `timezone` | `VKDOWNLOADER_TIMEZONE` | Europe/Moscow | Timezone for stealth configuration |
| `locale` | `VKDOWNLOADER_LOCALE` | ru-RU | Locale for browser stealth |
| `max_retries` | `VKDOWNLOADER_MAX_RETRIES` | 3 | Maximum retry attempts for failed segment downloads during batch processing (1-10) |
| `download_timeout` | `VKDOWNLOADER_DOWNLOAD_TIMEOUT` | 300 | Download timeout in seconds (30-3600) |
| `ssl_verify` | `VKDOWNLOADER_SSL_VERIFY` | true | Verify SSL certificates |
| `download_dir` | `VKDOWNLOADER_DOWNLOAD_DIR` | ~/Downloads/vkdownloader | Output directory |
| `max_concurrent_downloads` | `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS` | 4 | Segment-level concurrency limit shared across all batch URLs (1-16); 1 enables anti-detection delay |
| `throttled_rate` | `VKDOWNLOADER_THROTTLED_RATE` | 100000 | Minimum download rate in bytes/sec before throttling triggers re-extract |
| `http_chunk_size` | `VKDOWNLOADER_HTTP_CHUNK_SIZE` | 10485760 | HTTP chunk size in bytes for segment downloads |
| `cookie_source` | `VKDOWNLOADER_COOKIE_SOURCE` | none | Cookie acquisition strategy: none, browser (file is not implemented) |
| `log_level` | `VKDOWNLOADER_LOG_LEVEL` | INFO | Logging level |
| `log_file` | `VKDOWNLOADER_LOG_FILE` | None | Optional log file path |

## Cookie Source Settings

### cookie_source

Controls how cookies are acquired for authenticated video downloads:

- **`none`** (default) — No browser launch, fastest downloads for public videos only
- **`browser`** — Launch browser to extract real cookies for authenticated content
- **`file`** — Not implemented; selecting it raises `NotImplementedError`. Use `none` or `browser` instead.

**Download Method Behavior:**
| Method | cookie_source=NONE | cookie_source=BROWSER |
|--------|-------------------|-------------------|
| `yt-dlp` | Uses yt-dlp, no cookies passed | Uses yt-dlp with browser cookies |
| `ffmpeg` | Direct download without cookies | Captures cookies for ffmpeg headers |
| `auto` | No browser involvement | No browser involvement |

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

Controls retry behavior for failed segment downloads during batch processing.

- **CLI Flag:** `--max-retries` / `-r`
- **Environment Variable:** `VKDOWNLOADER_MAX_RETRIES`
- **Default:** `3` (range: 1-10)
- **Description:** Maximum retry attempts for failed segment downloads. When a segment download fails (e.g., due to 403/410 errors), the system will automatically retry up to this number of attempts before marking the download as failed.

**Example:**
```env
VKDOWNLOADER_MAX_RETRIES=5
```

### max_concurrent_downloads

Controls segment-level concurrency shared across all batch URLs.

- **CLI Flag:** Not available (use environment variable)
- **Environment Variable:** `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS`
- **Default:** `4` (range: 1-16)
- **Description:** The semaphore limit that controls how many concurrent segment downloads can run across all URLs in a batch. Setting this to `1` enables anti-detection delay between segments. This is a shared limit across the entire batch, not per-URL.

**Example for batch downloads:**
```env
VKDOWNLOADER_MAX_RETRIES=5
VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS=8
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

