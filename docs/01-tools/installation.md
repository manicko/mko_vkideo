---
id: vkdownloader-installation
domain: tools
tags:
  - installation
  - setup
  - requirements
related:
  - vkdownloader-overview
  - vkdownloader-api-reference
---
# Installation Guide

## Purpose

This guide covers installation and setup of VK Video Downloader for development and usage.

## Prerequisites

- Python 3.10 or higher
- ffmpeg installed and available in system PATH
- Windows, macOS, or Linux operating system

## System Requirements

### ffmpeg

ffmpeg is required for HLS stream to MP4 conversion:

**Windows:**
```powershell
choco install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

## Installation Steps

### 1. Clone Repository

```bash
git clone <repository-url>
cd mko_vkideo
```

### 2. Install Dependencies

Using pip:
```bash
pip install -e .
```

Using uv (recommended):
```bash
uv sync
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

## Development Setup

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

Or with uv:
```bash
uv sync --extra dev
```

### Run Tests

```bash
pytest tests/
```

### Run Linting

```bash
ruff check src/
```

## Configuration

Create a `.env` file for custom settings:

```env
# Browser Automation settings
VKDOWNLOADER_HEADLESS=false
VKDOWNLOADER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
VKDOWNLOADER_TIMEZONE=Europe/Moscow
VKDOWNLOADER_LOCALE=ru-RU
VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT=5
VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT=8
VKDOWNLOADER_MAX_RETRIES=3
VKDOWNLOADER_DOWNLOAD_TIMEOUT=300
VKDOWNLOADER_SSL_VERIFY=true

# Download settings
VKDOWNLOADER_DOWNLOAD_DIR=~/Downloads/vkdownloader
VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS=4
VKDOWNLOADER_THROTTLED_RATE=10000
VKDOWNLOADER_HTTP_CHUNK_SIZE=10485760

# Cookie Source
VKDOWNLOADER_COOKIE_SOURCE=none

# Logging
VKDOWNLOADER_LOG_LEVEL=INFO
VKDOWNLOADER_LOG_FILE=~/vkdownloader.log
```

### ffprobe (Optional)

ffprobe (bundled with ffmpeg) is used for video duration extraction when available:

- Enables ETA (estimated time remaining) in progress display
- Missing ffprobe is handled gracefully with warning log
- Falls back to m3u8 playlist parsing for approximate duration

## Verification

After installation, verify the setup:

```python
from vkdownloader import __version__
print(f"VK Video Downloader version: {__version__}")
```

```bash
vkdownloader --help
```