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