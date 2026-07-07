# VK Video Downloader Module - Development Plan (Part 1)

## Overview

This document outlines the development plan for a Python module to download videos from `vkvideo.ru` with quality selection support. The module must bypass anti-scraping protections while appearing as a legitimate browser.

## 1. Research Summary: VK Video Protection Mechanisms

### 1.1 Current Protection Methods (2026)

Based on analysis of VK Video and similar platforms:

1. **Dynamic m3u8 URLs**: Video URLs are not embedded in HTML but loaded via XHR requests after page load
2. **Token-based authentication**: m3u8 URLs require temporary tokens valid for short periods (typically 1-2 hours)
3. **Referer checks**: CDN validates that requests come from vkvideo.ru domain
4. **User-Agent validation**: Block requests with non-browser User-Agent strings
5. **Rate limiting and IP throttling**: Multiple rapid requests trigger temporary bans
6. **Geo-restrictions**: Some content may be region-locked
7. **CSRF tokens**: Required for API requests to prevent automated access
8. **Browser fingerprinting**: Detection of headless browser automation

### 1.2 Video Quality Structure

VK Video typically provides multiple quality options:
- 1080p (highest)
- 720p (high)
- 480p (medium)
- 360p (low)
- 240p (lowest)
- HLS variants (adaptive streaming with .m3u8 playlists)

Quality selection works by choosing appropriate stream URL from master playlist or directly from API response.

### 1.3 Key Technical Observations

From yt-dlp research:
- Video ID format: `video{OwnerID}_{VideoID}` (e.g., `video225794656_456242637`)
- API endpoints may be available at:
  - `https://vkvideo.ru/video{OwnerID}_{VideoID}`
  - `https://vk.com/video{OwnerID}_{VideoID}`
- m3u8 playlists use HLS protocol with segmented .ts files
- Some videos use adaptive streaming (DASH) via separate manifests

## 2. Architecture & Stack Selection

### 2.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Browser Automation | Playwright (async) | Best for JavaScript-heavy sites, reliable, supports stealth |
| HTTP Client | aiohttp | Async-native, performant, good for segment downloading |
| Data Models | Pydantic v2 | Type safety, validation, JSON serialization |
| Configuration | StrEnum + pydantic-settings | Type-safe enum-based configuration |
| Video Processing | ffmpeg-python | Direct ffmpeg integration for HLS download |
| Logging | structlog | Structured logging for debugging |

### 2.2 Clean Architecture Layers

```
vkdownloader/
├── domain/           # Business logic (models, interfaces)
│   ├── models/       # Pydantic models for Video, Stream, Quality
│   └── interfaces/   # Abstract interfaces for downloaders, parsers
├── application/      # Use cases and services
│   ├── services/     # VideoExtractor, StreamDownloader, QualitySelector
│   └── dtos/         # Data transfer objects
├── infrastructure/   # External implementations
│   ├── http/         # HTTP clients, cookie management
│   ├── browser/      # Playwright context, stealth configuration
│   └── storage/      # File system operations
└── main.py           # CLI entry point
```

### 2.3 Module Structure

```
src/
├── vkdownloader/
│   ├── __init__.py
│   ├── config.py             # StrEnum-based configuration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── video.py          # Video, Stream, Quality models
│   │   └── enums.py          # QualityEnum, StatusEnum
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extractor.py      # Video URL extraction logic
│   │   ├── downloader.py     # HLS/m3u8 downloader
│   │   └── quality.py        # Quality selection service
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── browser.py        # Playwright stealth setup
│   │   └── http_client.py    # aiohttp session wrapper
│   └── cli.py                # Typer-based CLI interface
```

## 3. Anti-Detection Strategy

### 3.1 Browser Headers to Mimic

```python
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://vkvideo.ru/",
    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}
```

### 3.2 Stealth Techniques

1. **Playwright stealth plugin**: Use `playwright-stealth` or manual stealth scripts
2. **Real browser profile**: Load existing Chrome profile with cookies
3. **Random delays**: Randomize request timing (2-5 seconds between requests)
4. **Viewport consistency**: Match typical desktop resolution (1920x1080)
5. **Disable automation flags**: Remove `webdriver`, `automation` indicators
6. **Mouse movement simulation**: Random mouse movements before video interaction
7. **Natural scrolling**: Simulate human-like page scrolling

### 3.3 Cookie & Session Management

- Preserve cookies between requests
- Handle session expiration gracefully
- Use realistic session duration (simulate user watching video)

## 4. Phase 1: Foundational Components (Estimated: 2-3 days)

### 4.1 Task 1.1: Project Setup
- Initialize Python project with poetry
- Configure pydantic-settings for configuration
- Create StrEnum for quality options and statuses
- Setup logging with structlog

### 4.2 Task 1.2: Models Layer
- Create `Video` model (Pydantic)
  - Fields: `id`, `title`, `description`, `duration`, `thumbnail`
- Create `Stream` model
  - Fields: `url`, `quality`, `format`, `resolution`, `bitrate`
- Create `QualityEnum` (240p, 360p, 480p, 720p, 1080p, best, worst)
- Create `DownloadStatus` enum (pending, downloading, completed, failed)

### 4.3 Task 1.3: HTTP Client Infrastructure
- Create async aiohttp client wrapper
- Implement header management (browser-like headers)
- Implement retry logic with exponential backoff
- Add request/response logging

### 4.4 Task 1.4: Browser Infrastructure
- Configure Playwright with stealth settings
- Create context manager for browser lifecycle
- Implement video player interaction simulation
- Add network request interception for m3u8 discovery

## 5. Phase 2: Video Extraction (Estimated: 3-4 days)

### 5.1 Task 2.1: Page Parsing Logic
- Navigate to video page
- Wait for VideoPlayer container to load
- Extract initial page HTML (if needed)
- Monitor network for m3u8/XHR requests

### 5.2 Task 2.2: API Endpoint Discovery
- Analyze XHR requests during video load
- Identify JSON endpoints for video metadata
- Extract video/stream URLs from API responses
- Handle different response formats

### 5.3 Task 2.3: Stream URL Extraction
- Parse master m3u8 playlists
- Extract available quality variants
- Validate stream URL accessibility
- Handle token refresh if needed

### 5.4 Task 2.4: Quality Selection Service
- Implement quality selection logic
- Map quality strings to resolution/bitrate
- Select best available quality if requested
- Validate selected stream matches request

## 6. Phase 3: Download Implementation (Estimated: 2-3 days)

### 6.1 Task 3.1: HLS Downloader Core
- Parse m3u8 playlists (using m3u8 library or custom parser)
- Download segments concurrently (aiohttp)
- Implement retry for failed segments
- Track download progress

### 6.2 Task 3.2: ffmpeg Integration
- Combine downloaded segments
- Use ffmpeg for final MP4 muxing
- Handle codec information from manifest
- Support for different container formats

### 6.3 Task 3.3: Resume & Recovery
- Track downloaded segments state
- Resume partial downloads
- Validate file integrity
- Clean temporary files on failure

## 7. Phase 4: CLI & Integration (Estimated: 1-2 days)

### 7.1 Task 4.1: CLI Interface
- Use Typer for argument parsing
- Support URL input, quality selection
- Add progress bar (tqdm)
- Implement output path configuration

### 7.2 Task 4.2: Error Handling
- Graceful error messages
- Retry logic with max attempts
- Log file generation
- Handle edge cases (private videos, deleted videos)

### 7.3 Task 4.3: Testing
- Unit tests for parsers
- Integration tests with mock responses
- Test quality selection
- Test download/resumption flow

---

*To be continued in Part 2: Detailed implementation steps, API contracts, and test strategies.*