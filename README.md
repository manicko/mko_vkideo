---
id: vkdownloader-readme
domain: tools
tags:
  - vkdownloader
  - download
  - hls
related:
  - vkdownloader-installation
  - vkdownloader-api-reference
---

# VK Video Downloader

Async Python module to download videos from vkvideo.ru with quality selection support.

## Purpose

VK Video Downloader provides a programmatic and CLI interface for downloading videos from VK Video (vkvideo.ru). It uses yt-dlp for stream extraction and ffmpeg for direct download-to-MP4 conversion, with segment-level resume support for handling token expiration.

## Features

- Extract video streams from VK video URLs using yt-dlp or browser automation
- Quality selection (240p, 360p, 480p, 720p, 1080p, best, worst)
- Download method selection (yt-dlp, ffmpeg, auto)
- Segment-level resume on token expiration
- Batch download support via CLI
- Path traversal prevention for security
- SSL verification enabled by default

## Installation

See [Installation Guide](docs/01-tools/installation.md) for detailed setup instructions.

```bash
pip install -e .
```

## CLI Usage

### Download Single Video

```bash
vkdownloader download "https://vkvideo.ru/video-123_456"
```

### Download with Specific Quality

```bash
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 720
```

### Download with Specific Method

```bash
# Use ffmpeg for faster download (~1MB/s)
vkdownloader download "https://vkvideo.ru/video-123_456" --method ffmpeg

# Use yt-dlp for higher reliability (~100KB/s)
vkdownloader download "https://vkvideo.ru/video-123_456" --method yt-dlp
```

### Download to Specific Directory

```bash
vkdownloader download "https://vkvideo.ru/video-123_456" -o ./videos
```


```bash
vkdownloader download "https://vkvideo.ru/video-225794656_456243903" --quality 1440 --method yt-dlp --output ".\Shows" --no-ssl-verify

```



### Batch Download

Create a file with video URLs (one per line):

```bash
vkdownloader batch ./urls.txt --quality best
```


## Programmatic Usage

```python
import asyncio
from pathlib import Path
from vkdownloader.services.downloader import perform_download
from vkdownloader.models.enums import DownloadMethod


async def download_video():
    # Simple download with method selection
    result = await perform_download(
        url="https://vkvideo.ru/video-123_456",
        quality="720",
        output_file=Path("output.mp4"),
        method=DownloadMethod.AUTO,
    )
    return result


asyncio.run(download_video())
```

## Requirements

- Python 3.10+
- ffmpeg (in system PATH)
- Playwright browsers (auto-installed)

## Architecture

See [VK Downloader Overview](docs/01-tools/vkdownloader-overview.md) for architecture details.

## API Reference

See [API Reference](docs/01-tools/api-reference.md) for complete API documentation.

## Quality Selection

See [Quality Selection Guide](docs/01-tools/quality-selection.md) for quality selection options.

## Error Handling & Logging

### Exception Hierarchy

All domain errors inherit from `VKDownloadError` and carry a machine-readable `ErrorCode` (StrEnum), a `status_label()` for batch results, and a `log_context()` dict for structured logging.

| Exception | Error Code | Status Label | Description |
|-----------|-----------|-------------|-------------|
| `VKDownloadError` | `UNEXPECTED_ERROR` | `error: unexpected_error` | Base exception; also the catch-all for unexpected failures. |
| `InvalidVideoUrlError` | `INVALID_URL` | `invalid_url` | URL does not match VK video pattern. |
| `VideoNotFoundError` | `VIDEO_NOT_FOUND` | `video_not_found` | Video not found or no streams returned. |
| `QualityNotAvailableError` | `QUALITY_NOT_AVAILABLE` | `quality_not_available` / `no_streams` | Requested quality not in available streams. |
| `QualityParseError` | `QUALITY_PARSE_ERROR` | `invalid_quality` | Quality string cannot be parsed. |
| `ExtractionError` | `EXTRACTION_ERROR` | `extraction_error` | Stream extraction failed (yt-dlp or browser). |
| `DownloadError` | `DOWNLOAD_ERROR` | `download_error` | Download or path-safety failure. |
| `DownloadError(ErrorCode.PATH_TRAVERSAL)` | `PATH_TRAVERSAL` | `download_error` | Output path contains path traversal. |

The legacy `_map_exception_to_status()` helper and `_EXCEPTION_STATUS_HANDLERS` dict are retained for backward compatibility. New code paths use `status_label()` directly on exception instances.

### Logging

Logging uses `structlog` with a structured processor chain. When `--log-file` is set, logs are emitted as JSON; otherwise they use a human-readable console format.

**Processor chain:**

1. `merge_contextvars` — merges structlog context variables (correlation IDs)
2. `add_log_level` — adds log level to every entry
3. `TimeStamper(fmt="iso", utc=True)` — UTC ISO-8601 timestamp
4. `format_exc_info` — structured traceback frames when `exc_info=True`
5. `UnicodeDecoder()` — safe decoding of non-ASCII log content
6. JSON or Console renderer

**Correlation IDs:** Each download operation (single or batch) is assigned an 8-character hex correlation ID via `generate_correlation_id()`. The ID is bound to the structlog context and automatically included in every log entry within that operation. Use `--log-file` to get JSON output with correlation IDs for log aggregation.

**URL redaction:** All log entries that include URLs pass them through `_strip_auth_params()` which replaces path and query parameters with `***REDACTED***`, preventing signed CDN tokens from leaking into logs.