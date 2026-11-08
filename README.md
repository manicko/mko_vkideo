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
- Quality selection by keyword (`best`, `worst`, `unknown`) or by any height in pixels the video offers
- Download method selection (yt-dlp, auto, or optional direct ffmpeg)
- Segment-level resume on token expiration, with a durable per-job checkpoint
- Per-job temporary workspace under `output/tmp` (no in-progress files at the output root)
- Redacted per-job diagnostics logs under `output/tmp/logs`
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

`--quality` accepts `best`, `worst`, `unknown`, or any height in pixels the video offers. A height is an exact match, so pick one the video actually publishes.

```bash
# Highest available resolution (the default)
vkdownloader download "https://vkvideo.ru/video-123_456" --quality best

# A specific height the video offers, with or without the trailing p
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 720
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 1072p
```

A height the video does not offer is reported rather than downgraded, and the error lists the qualities it does offer. Any token that is neither a keyword nor a positive height (`abc`, `720x`, `0`) is rejected as a usage error with exit code 2, before any download is attempted.

### Download with Specific Method

```bash
# Use yt-dlp for higher reliability (~100KB/s)
vkdownloader download "https://vkvideo.ru/video-123_456" --method yt-dlp
```

### Download to Specific Directory

```bash
vkdownloader download "https://vkvideo.ru/video-123_456" -o ./videos
```


```bash
# A real-world run: pick the method, the output directory, and the quality.
# A keyword such as best needs no knowledge of the video's ladder; replace it
# with a height only when you know the video offers that exact height.
vkdownloader download "https://vkvideo.ru/video-225794656_456243903" --quality best --method yt-dlp --output ".\Shows" --no-ssl-verify

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
        # The quality token, as a plain string: "best", "worst", "unknown",
        # or any height in pixels the video offers. The stream itself is
        # pre-selected by the caller; use download_video() for the full
        # extract -> select -> download pipeline.
        quality="best",
        output_file=Path("output.mp4"),
        method=DownloadMethod.AUTO,
    )
    return result


asyncio.run(download_video())
```

## Requirements

- Python 3.14+
- ffmpeg — required for the segment download path (HLS segment download and MP4 merge); not needed for single-stream yt-dlp downloads
- Playwright browsers (manual install — see Installation Guide)

## Architecture

See [VK Downloader Overview](docs/01-tools/vkdownloader-overview.md) for architecture details.

## API Reference

See [API Reference](docs/01-tools/api-reference.md) for complete API documentation.

## Quality Selection

See [Quality Selection Guide](docs/01-tools/quality-selection.md) for quality selection options.

## Temporary Workspace and Resume

New downloads use a per-job workspace under `output/tmp` automatically. The familiar command still works; the first new run creates it for you:

```text
output/
└── tmp/
    ├── jobs/
    │   └── <job-id>/
    │       ├── job_state.v2.json           # durable job state
    │       ├── segment_checkpoint.v2.json  # HLS segment checkpoint
    │       ├── state.json                 # legacy read-only migration input
    │       ├── ytdlp/                     # yt-dlp fragments and partials
    │       ├── segments/                  # downloaded HLS segments
    │       ├── staging/                   # completed, not-yet-published media
    │       └── diagnostics/               # non-secret metadata
    ├── locks/
    │   └── <job-id>.lock                  # exclusive job lock (external)
    └── logs/
        └── <job-id>.jsonl                 # redacted per-job diagnostic log
```

- In-progress files are never written at the output root; only the validated final MP4 is published there.
- Failed or cancelled jobs keep their usable temp data for resume. Successful jobs remove only their owned intermediates, while logs are retained with rotation.
- Resume uses the checkpoint (`state.json`) and verifies each segment by size and SHA-256, so a token-only URL change reuses valid segments instead of restarting at byte zero. If media identity is ambiguous, the old generation is quarantined rather than mixed.
- Exact `--quality 1440` is preserved across refresh, retry, and backend selection, or fails with an explicit error and the available ladder; there is no silent downgrade.

### Throttled-rate semantics

- `VKDOWNLOADER_THROTTLED_RATE` defaults to `0`, which disables yt-dlp throttled re-extraction. Positive values are a diagnostic low-speed threshold only: they never trigger a download abort, refresh, or backend switch.
- The managed argv uses `--ignore-config`, so the invocation is reproducible and global yt-dlp configuration is not auto-applied.

### Staging recovery

A terminal `file_locked` outcome preserves the staging candidate. Recovery is local: close the holder, retry the job, or change the output location. After the lock clears there are zero HTTP requests, and partial artifacts are preserved for resume.

### Windows lock-owner pointer

On Windows, a `SHARING VIOLATION` holder can be correlated with `child_started.pid` / `launch_number` using the Process Monitor subsection in [Troubleshooting Guide](docs/11-guides/troubleshooting.md).

See [Troubleshooting Guide](docs/11-guides/troubleshooting.md) for log location, diagnostics bundle, manual cleanup, and migration/rollback notes.

### Exception Hierarchy

All domain errors inherit from `VKDownloadError` and carry a machine-readable `ErrorCode` (StrEnum), a `status_label()` for batch results, and a `log_context()` dict for structured logging.

| Exception | Error Code | Status Label | Description |
|-----------|-----------|-------------|-------------|
| `VKDownloadError` | `UNEXPECTED_ERROR` | `error: unexpected_error` | Base exception; also the catch-all for unexpected failures. |
| `InvalidVideoUrlError` | `INVALID_URL` | `invalid_url` | URL does not match VK video pattern. |
| `VideoNotFoundError` | `VIDEO_NOT_FOUND` | `video_not_found` | Video not found or no streams returned. |
| `QualityNotAvailableError` | `QUALITY_NOT_AVAILABLE` | `quality_not_available` / `no_streams` | Requested quality not in available streams. |
| `QualityParseError` | `QUALITY_PARSE_ERROR` | `quality_parse_error` | Quality string cannot be parsed. |
| `ExtractionError` | `EXTRACTION_ERROR` | `extraction_error` | Stream extraction failed (yt-dlp or browser). |
| `DownloadError` | `DOWNLOAD_ERROR` | `download_error` | Download or path-safety failure. |
| `DownloadError(ErrorCode.PATH_TRAVERSAL)` | `PATH_TRAVERSAL` | `download_error` | Output path contains path traversal. |

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

### Per-job logs and diagnostics bundle

The per-job diagnostic log is created automatically under `output/tmp/logs/<job-id>.jsonl` when diagnostics are enabled. To view its location:

```bash
# Linux/macOS
ls output/tmp/logs

# Windows PowerShell
Get-ChildItem -LiteralPath "output\tmp\logs"
```

A redacted diagnostics bundle should contain filenames and sizes plus the JSONL logs. Do not include cookies or signed URLs:

```bash
# Dry-run inventory (filenames and sizes only)
find output/tmp/jobs -type f -printf '%p %s bytes\n' | sort

# Windows PowerShell
Get-ChildItem -LiteralPath "output\tmp\jobs" -Recurse -File | Select-Object FullName, Length
```