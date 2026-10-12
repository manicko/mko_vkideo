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

- Python 3.14 or higher
- ffmpeg — required for the segment download path (HLS segment download and MP4 merge); not needed for single-stream yt-dlp downloads
- Windows, macOS, or Linux operating system

**Python 3.12 and 3.13 are no longer supported.** This package declares `requires-python = ">=3.14"`, so attempting to install it on 3.12 or 3.13 will fail with a resolution error. This is a deliberate narrowing, not a documentation oversight.

## System Requirements

### ffmpeg

ffmpeg is **required for the segment download path** (HLS segment download and MP4 merge to MP4). It is **not required for every download** — single-stream yt-dlp downloads work without it; only segment-based downloads will fail at merge time if it is absent.

Install it as follows for your platform:

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

The verification tooling (`ruff`, `mypy`, `pytest`, `pytest-asyncio`) is declared in the
`dev` dependency group. `uv sync` installs that group by default, so no extra flag is needed:

```bash
uv sync
```

### Run Tests

```bash
uv run pytest tests/
```

### Run Linting

```bash
uv run ruff check src/
```

### Run Formatting Check

```bash
uv run ruff format --check src/
```

### Run Type Check

```bash
uv run mypy src/
```

## Configuration

Create a `.env` file for custom settings. It is read from the directory the command is run from; see the [configuration guide](../11-guides/configuration.md) for the full rule:

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
VKDOWNLOADER_THROTTLED_RATE=100000
VKDOWNLOADER_HTTP_CHUNK_SIZE=0

# Cookie Source
VKDOWNLOADER_COOKIE_SOURCE=none

# Logging
VKDOWNLOADER_LOG_LEVEL=INFO
VKDOWNLOADER_LOG_FILE=~/vkdownloader.log
```

## Verification

After installation, verify the setup:

```python
from vkdownloader import __version__
print(f"VK Video Downloader version: {__version__}")
```

```bash
vkdownloader --help
```