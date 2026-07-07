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

## How Quality Selection Works

### Stream Extraction

When extracting streams from a VK video URL, the `VKVideoExtractor` parses the HLS playlist to identify available quality variants:

1. Navigates to the video page with stealth browser
2. Intercepts network responses to capture m3u8 URLs
3. Parses the HLS playlist for `#EXT-X-STREAM-INF` entries
4. Extracts bandwidth and resolution for each stream variant

### Selection Algorithm

The `QualitySelector` uses the following logic:

1. **BEST**: Returns the stream with the highest `height` value
2. **WORST**: Returns the stream with the lowest `height` value
3. **Specific resolution** (e.g., `720`): Finds exact match first, falls back to BEST if not found

### Stream Matching

Streams are matched by comparing the `quality` field extracted from the HLS playlist:

- Quality string format: `{height}p` (e.g., "720p")
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

### Complete Download Flow

```python
import asyncio
from pathlib import Path
from vkdownloader.services.extractor import VKVideoExtractor
from vkdownloader.services.quality import QualitySelector
from vkdownloader.services.downloader import HLSDownloader
from vkdownloader.models.enums import QualityEnum

async def download_quality_example():
    # Step 1: Extract streams
    extractor = VKVideoExtractor()
    video = await extractor.extract_streams("https://vkvideo.ru/video-123_456")
    
    # Step 2: See available qualities
    selector = QualitySelector()
    qualities = selector.list_available_qualities(video.streams)
    print(f"Available qualities: {qualities}")
    
    # Step 3: Select quality
    stream = selector.select(video.streams, QualityEnum.Q720)
    
    # Step 4: Download
    downloader = HLSDownloader()
    result = await downloader.download_with_ffmpeg(
        str(stream.url),
        Path(f"{video.id}_{stream.quality}.mp4"),
        quality=str(stream.quality)
    )
    
    return result

asyncio.run(download_quality_example())
```

## Quality Fallback Behavior

If a specific quality is requested but not available:

1. The selector attempts to find an exact match
2. If no match is found, it falls back to the best available quality
3. A debug log entry is created: `"quality_not_found_fallback_to_best"`

This ensures downloads never fail due to unavailable quality options.