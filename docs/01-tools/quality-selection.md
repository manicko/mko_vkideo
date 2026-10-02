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

VK Video Downloader accepts a keyword or any height the video actually offers. VK does not publish a fixed resolution ladder: one reported video offers `106p`, `178p`, `268p`, `358p`, `536p`, `804p`, `1072p`, `1610p`, so a closed list of known resolutions would make most real requests impossible to express.

| Option | Value | Description |
|--------|-------|-------------|
| Best | `best` | Selects the highest available resolution (default) |
| Worst | `worst` | Selects the lowest available resolution |
| Unknown | `unknown` | Selects a stream whose height is unavailable (browser HLS capture) |
| Height in pixels | `720`, `1080`, `1072`, any other offered height | Selects the stream whose quality label is exactly that height, when the video offers it |

A height is a positive integer in pixels with an optional trailing `p`, so `720` and `720p` are the same request. The token is case-insensitive and surrounding whitespace is ignored, so `720P` and ` 720 ` are accepted too. An empty value falls back to `best`, matching the CLI default.

Anything else is rejected: a keyword other than `best`, `worst` or `unknown`, `0`, a negative number, `abc`, `720x`. Through the CLI the rejection is a usage error with exit code `2`, raised while the command line is parsed, so nothing is downloaded:

```
Invalid value for '--quality': Use 'best', 'worst', 'unknown', or a height in pixels the video offers (e.g. 720, 1080, 1072).
```

Every value that message names is accepted when pasted back into the command line.

## How Quality Selection Works

### Stream Extraction

When extracting streams from a VK video URL, the `VKVideoExtractor` uses yt-dlp as the primary extraction method (handles VK protections):

1. Uses yt-dlp to extract available formats
2. Filters formats to include only video-bearing streams — a record that does not
   declare a non-`none` video codec (``vcodec``) is dropped
3. Extracts height, width, and bitrate for each stream variant
4. Creates Stream objects with quality strings in `{height}p` format

For ffmpeg download method, `extract_streams_with_cookies()` additionally:

1. Opens video page in stealth browser
2. Captures cookies for CDN authentication
3. Simulates video interaction to trigger stream loading
4. Captures m3u8 URLs from network traffic

### Selection Algorithm

A user-supplied token is parsed once by `QualitySpec.parse` into a request with a `QualityKind` — how it is resolved against the streams of the video. The `QualitySelector` then takes one of three paths:

1. **BEST** (`QualityKind.BEST`): Returns the stream with the highest usable `height` (a `height <= 0` placeholder is treated as absent)
2. **WORST** (`QualityKind.WORST`): Returns the stream with the lowest usable `height` (a `height <= 0` placeholder is treated as absent, and the two arms never select the same record from a `{0, None}` set)
3. **EXACT** (`QualityKind.EXACT`): Finds the stream whose quality label matches the request exactly — whatever height it carries, including a non-standard one such as `1072p` — and raises `QualityNotAvailableError` if no such stream exists

There is no silent fallback to a lower quality on the exact path. A request for a height the video does not offer is reported, not downgraded.

### Stream Matching

Streams are matched by comparing the `quality` field:

- Quality string format: `{height}p` (e.g., "1072p")
- A request also matches the numeric form (e.g., `1072` matches "1072p"), and a request written as `1072p` matches either spelling
- Streams without a positive `height` (`None`, `0`, or negative) are assigned the `unknown` quality label, which `--quality unknown` selects
- A `best` or `worst` request never matches a single label; it ranks the streams instead

## CLI Usage

### Download Best Quality (Default)

```bash
vkdownloader download "https://vkvideo.ru/video-123_456"
```

### Download Specific Quality

Any height the video offers is valid, including non-standard ones. Both spellings below request the same 1072p stream:

```bash
# 720p, when the video offers it
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 720

# 1080p, when the video offers it
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 1080

# A non-standard height, with or without the trailing p
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 1072
vkdownloader download "https://vkvideo.ru/video-123_456" --quality 1072p

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

`QualitySelector.select` takes a `QualitySpec`, not an enum member. Build one with `QualitySpec.parse` from the same token the CLI accepts.

```python
from vkdownloader.models.quality import QualitySpec
from vkdownloader.services.quality import QualitySelector

selector = QualitySelector()

# Get available qualities
available = selector.list_available_qualities(video.streams)
print(available)  # ['1610p', '1072p', '804p', ...]

# Select best quality
stream = selector.select(video.streams, QualitySpec.parse("best"))

# Select a specific height the video offers, including a non-standard one
stream = selector.select(video.streams, QualitySpec.parse("1072"))

# Select worst quality
stream = selector.select(video.streams, QualitySpec.parse("worst"))
```

`QualitySpec.parse` raises `QualityParseError` for a token that is neither a keyword nor a positive height. The parsed request carries `kind` (`QualityKind.BEST`, `QualityKind.WORST` or `QualityKind.EXACT`) and, for an exact request, the `label` it matches (`"1072p"`). `str(spec)` renders the token the CLI accepts — `"1072"` — which is also the value handed to the yt-dlp format selector as `best[height<=1072]`.

### Complete Download Flow with Method Selection

`perform_download` takes the plain token string, not a `QualitySpec`; `download_video` is the entry point that takes a `QualitySpec` and performs the selection itself.

```python
import asyncio
from pathlib import Path
from vkdownloader.services.downloader import perform_download
from vkdownloader.models.enums import DownloadMethod

async def download_quality_example():
    result = await perform_download(
        url="https://vkvideo.ru/video-123_456",
        quality="720",  # "best", "worst", "unknown" or any offered height
        output_file=Path("video_720.mp4"),
        method=DownloadMethod.AUTO,  # or DownloadMethod.FFMPEG
    )
    return result

asyncio.run(download_quality_example())
```

## Quality Fallback Behavior

If a specific quality is requested but not available:

1. The selector looks for an exact match on the quality label
2. If no match is found, `QualityNotAvailableError` is raised, carrying the requested token and the available labels
3. The exception message reads `"Quality '1072' not available. Available: ['1610p', '1072p', ...]"`, and the `download` command renders the requested value verbatim followed by the ladder the video does offer:

```
Requested quality '1000' is not available for this video.
Available qualities: 106p, 178p, 268p, 358p, 536p, 804p, 1072p, 1610p
```

   In `batch`, the same condition reports that URL as failed with the `quality_not_available` status label in the summary, and the command exits `1`.

This ensures users are informed when their quality preference cannot be met, rather than silently receiving a different one.