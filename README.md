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

VK Video Downloader provides a programmatic and CLI interface for downloading videos from VK Video (vkvideo.ru). It uses browser automation to extract HLS streams and ffmpeg for direct download-to-MP4 conversion.

## Features

- Extract video streams from VK video URLs
- Quality selection (240p, 360p, 480p, 720p, 1080p, best, worst)
- Batch download support via CLI
- Stealth browser automation to bypass bot detection
- Adaptive throttling for respectful downloading

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

### Download to Specific Directory

```bash
vkdownloader download "https://vkvideo.ru/video-123_456" -o ./videos
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
from vkdownloader.services.extractor import VKVideoExtractor
from vkdownloader.services.quality import QualitySelector
from vkdownloader.services.downloader import HLSDownloader
from vkdownloader.models.enums import QualityEnum

async def download_video():
    # Extract available streams
    extractor = VKVideoExtractor()
    video = await extractor.extract_streams("https://vkvideo.ru/video-123_456")
    
    # Select quality
    selector = QualitySelector()
    stream = selector.select(video.streams, QualityEnum.Q720)
    
    # Download
    downloader = HLSDownloader()
    output_path = await downloader.download_with_ffmpeg(
        str(stream.url),
        Path("output.mp4"),
        quality="720"
    )

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