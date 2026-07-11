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
| `user_agent` | `USER_AGENT` | `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` | User agent string for browser requests |
| `accept_language` | `ACCEPT_LANGUAGE` | ru-RU,... | Accept-Language header for browser |
| `timezone` | `TIMEZONE` | Europe/Moscow | Timezone for stealth configuration |
| `locale` | `LOCALE` | ru-RU | Locale for browser stealth |
| `max_retries` | `MAX_RETRIES` | 3 | Maximum retry attempts (1-10) |
| `download_timeout` | `DOWNLOAD_TIMEOUT` | 300 | Download timeout in seconds (30-3600) |
| `ssl_verify` | `SSL_VERIFY` | true | Verify SSL certificates |
| `download_dir` | `DOWNLOAD_DIR` | ~/Downloads/vkdownloader | Output directory |
| `max_concurrent_downloads` | `MAX_CONCURRENT_DOWNLOADS` | 4 | Concurrent downloads (1-16); 1 enables anti-detection delay |
| `concurrent_fragments` | `CONCURRENT_FRAGMENTS` | 4 | Concurrent HLS fragments for yt-dlp (reduces throttling) |
| `throttled_rate` | `THROTTLED_RATE` | 100000 | Minimum download rate in bytes/sec before throttling triggers re-extract |
| `http_chunk_size` | `HTTP_CHUNK_SIZE` | 10485760 | HTTP chunk size in bytes for segment downloads |
| `download_method` | `DOWNLOAD_METHOD` | auto | Download method: yt-dlp, ffmpeg, auto |
| `log_level` | `LOG_LEVEL` | INFO | Logging level |
| `log_file` | `LOG_FILE` | None | Optional log file path |

## Example .env File

```env
# Browser settings
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
DOWNLOAD_TIMEOUT=300
SSL_VERIFY=true

# Download settings
DOWNLOAD_DIR=~/Downloads/vkdownloader
MAX_CONCURRENT_DOWNLOADS=4
DOWNLOAD_METHOD=auto

# Logging
LOG_LEVEL=INFO
```

## Security Settings

### ssl_verify

Controls SSL certificate verification for CDN connections.

- **Default: `true`** — Secure by default
- **Setting to `false`** — Logs a security warning; use only for edge cases

### download_dir

Output directory for downloaded videos. Paths are validated to prevent path traversal attacks.