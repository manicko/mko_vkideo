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
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
ACCEPT_LANGUAGE=ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7
TIMEZONE=Europe/Moscow
LOCALE=ru-RU
MAX_RETRIES=3
DOWNLOAD_TIMEOUT=300
SSL_VERIFY=true

# Download settings
DOWNLOAD_DIR=~/Downloads/vkdownloader
MAX_CONCURRENT_DOWNLOADS=4
DOWNLOAD_METHOD=auto

# Logging
LOG_LEVEL=INFO
LOG_FILE=
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