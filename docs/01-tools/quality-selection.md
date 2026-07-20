---
id: vkdownloader-quality-selection
domain: tools
tags:
  - quality
  - streaming
  - selection
related:
  - vkdownloader-api-reference
  - vkdownloader-overview
---
# Quality Selection Guide

## Purpose

This guide explains how to select video quality when downloading from VK Video using the VK Video Downloader.

## Quality Options

VK Video Downloader supports the following quality options:

| Option | Value | Description |
|--------|-------|-------------|
| Best | `best` | Selects the highest available resolution |
| Worst | `worst` | Selects the lowest available resolution |
| 240p | `240` | 240p resolution (if available) |
| 360p | `360` | 360p resolution (if available) |
| 480p | `480` | 480p resolution (if available) |
| 720p | `720` | 720p resolution (if available) |
| 1080p | `1080` | 1080p resolution (if available) |
| 1440p | `1440` | 1440p resolution (if available) |
| 2160p | `2160` | 2160p resolution (if available) |

## How Quality Selection Works

### Stream Extraction

When extracting streams from a VK video URL, the `VKVideoExtractor` uses yt-dlp as the primary extraction method (handles VK protections):

1. Uses yt-dlp to extract available formats
2. Filters formats to include only video streams (skips audio-only)
3. Extracts height, width, and bitrate for each stream variant
4. Creates Stream objects with quality strings in `{height}p` format

For ffmpeg download method, `extract_streams_with_cookies()` additionally:

1. Opens video page in stealth browser
2. Captures cookies for CDN authentication
3. Simulates video interaction to trigger stream loading
4. Captures m3u8 URLs from network traffic

### Selection Algorithm

The `QualitySelector` uses the following logic:

1. **BEST**: Returns the stream with the highest `height` value
2. **WORST**: Returns the stream with the lowest `height` value
3. **Specific resolution** (e.g., `720`): Finds exact match first, raises `QualityNotAvailableError` if not found

### Stream Matching

Streams are matched by comparing the `quality` field:

- Quality string format: `{height}p` (e.g., "720p")
- Also supports numeric format (e.g., "720" matches "720p")
- Streams without height are assigned "unknown" quality

## CLI Usage

### Download Best Quality (Default)

```bash
vkdownloader download "https://vkvideo.ru/video-123_456"
```

### Download Specific Quality

```bash
# 720p
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 720

# 1080p
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 1080

# Best available
vkdownloader download "https://vkvideo.ru/video-123_456" --quality best

# Worst available (smallest file)
vkdownloader download "https://vkvideo.ru/video-123_456" --quality worst
```

### Download with Specific Method

```bash
# Use ffmpeg for faster download (~1MB/s)
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 720 --method ffmpeg

# Use ffmpeg with browser cookies for authenticated content
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 720 --method ffmpeg --cookie-source browser

# Use yt-dlp for higher reliability (~100KB/s)
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 720 --method yt-dlp
```

### Batch Download with Quality

```bash
# All videos in batch at 720p
vkdownloader batch ./urls.txt --quality 720
```

## Programmatic Usage

### Using QualitySelector

```python
from vkdownloader.services.quality import QualitySelector
from vkdownloader.models.enums import QualityEnum

selector = QualitySelector()

# Get available qualities
available = selector.list_available_qualities(video.streams)
print(available)  # ['1080p', '720p', '480p', ...]

# Select best quality
stream = selector.select(video.streams, QualityEnum.BEST)

# Select specific resolution
stream = selector.select(video.streams, QualityEnum.Q720)

# Select worst quality
stream = selector.select(video.streams, QualityEnum.WORST)
```

### Complete Download Flow with Method Selection

```python
import asyncio
from pathlib import Path
from vkdownloader.services.downloader import perform_download
from vkdownloader.models.enums import DownloadMethod

async def download_quality_example():
    result = await perform_download(
        url="https://vkvideo.ru/video-123_456",
        quality="720",
        output_file=Path("video_720.mp4"),
        method=DownloadMethod.AUTO,  # or DownloadMethod.FFMPEG
    )
    return result

asyncio.run(download_quality_example())
```

## Quality Fallback Behavior

If a specific quality is requested but not available:

1. The selector attempts to find an exact match
2. If no match is found, `QualityNotAvailableError` is raised with available options listed
3. Error message includes: `"Requested quality 'X' not available. Available: [...]`

This ensures users are informed when their quality preference cannot be met.