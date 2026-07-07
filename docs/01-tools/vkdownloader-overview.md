---
id: vkdownloader-overview
domain: tools
tags:
  - overview
  - architecture
related:
  - vkdownloader-installation
  - vkdownloader-api-reference
---
# VK Downloader Overview

## Purpose

VK Video Downloader is an async Python module for downloading videos from vkvideo.ru with intelligent quality selection. It combines browser automation for stream extraction with ffmpeg for direct HLS-to-MP4 conversion.

## Main Concepts

### Core Services

| Service | Module | Responsibility |
|---------|--------|----------------|
| VKVideoExtractor | `services/extractor.py` | Extracts stream URLs from VK video pages using Playwright browser automation |
| QualitySelector | `services/quality.py` | Selects appropriate stream based on quality preference |
| HLSDownloader | `services/downloader.py` | Downloads HLS streams to MP4 using ffmpeg |

### Infrastructure

| Component | Module | Responsibility |
|-----------|--------|----------------|
| HttpClient | `infrastructure/http_client.py` | Async HTTP requests with retry logic and browser-like headers |
| BrowserManager | `infrastructure/browser.py` | Playwright browser lifecycle management |
| NetworkMonitor | `infrastructure/network_monitor.py` | Captures m3u8 URLs from browser network traffic |
| AdaptiveThrottle | `infrastructure/adaptive_throttle.py` | Rate limiting and request throttling |

### Models

| Model | Module | Description |
|-------|--------|-------------|
| `Video` | `models/video.py` | Basic video metadata |
| `Stream` | `models/video.py` | Video stream with URL and quality info |
| `VideoWithStreams` | `models/video.py` | Video model with available streams |
| `QualityEnum` | `models/enums.py` | Quality options (240, 360, 480, 720, 1080, best, worst) |
| `StreamFormat` | `models/enums.py` | Stream format types (HLS, DASH, MP4) |
| `DownloadStatus` | `models/enums.py` | Download state tracking |

## Architecture Flow

```
User Request
    │
    ▼
┌─────────────────┐
│  VKVideoExtractor│
│  (BrowserAutomation)│
└────────┬────────┘
         │ Extract m3u8 URLs
         ▼
┌─────────────────┐
│  NetworkMonitor  │
│  (Captures URLs)  │
└────────┬────────┘
         │ Parse playlist
         ▼
┌─────────────────┐
│  QualitySelector │
│  (Select stream)  │
└────────┬────────┘
         │ Selected stream
         ▼
┌─────────────────┐
│   HLSDownloader  │
│(ffmpeg → MP4)    │
└─────────────────┘
```

## Configuration

The `Settings` class in `config.py` provides:

- **VK API settings**: API URL and version
- **Browser settings**: User agent, locale, timezone for stealth
- **Download settings**: Timeout, concurrent downloads, output directory
- **Logging settings**: Log level and optional file output

## CLI Interface

The CLI (`cli.py`) provides two commands:

- `download`: Download single video with quality selection
- `batch`: Download multiple videos from a URL file

Both commands use the core services and support the same quality options.