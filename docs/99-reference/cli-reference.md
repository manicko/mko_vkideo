---
id: cli-reference
domain: reference
tags:
  - cli
  - commands
  - usage
related:
  - configuration-guide
  - ast-editor
---

# CLI Command Reference

**Package:** `vkdownloader` — VK Video Downloader for vkvideo.ru

The CLI is built with [Typer](https://typer.tiangolo.com/) and uses progress bars for download feedback.

---

## Global Invocation

```bash
vkdownloader [OPTIONS] COMMAND [ARGS]...
```

The `vkdownloader` command is registered as a console script in `pyproject.toml`:

```toml
[project.scripts]
vkdownloader = "vkdownloader.cli:cli"
```

| Flag | Description |
|------|-------------|
| `--help` | Show the help message listing all commands and global options. |
| `--install-completion` | Install shell completion for the current shell. |
| `--show-completion` | Show shell completion source code. |

---

## Commands

### 1. `download` — Download a single video

Download a video from vkvideo.ru with quality and method selection support.

**Source:** `vkdownloader/cli.py` → `download()`

```bash
vkdownloader download [OPTIONS] URL
```

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `URL` | string | VK Video URL to download (format: `https://vkvideo.ru/video-{owner_id}_{video_id}`) |

**Options:**

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--quality` | | str | `best` | Video quality selection: `240`, `360`, `480`, `720`, `1080`, `1440`, `2160`, `best`, `worst` |
| `--output` | `-o` | Path | `.` | Output directory for downloaded video |
| `--method` | `-m` | str | `auto` | Download method: `yt-dlp`, `ffmpeg`, or `auto` |

**Behavior:**

1. Extracts available streams from the provided VK video URL
2. Selects the requested quality (or best available by default)
3. Validates and creates the output directory
4. Downloads the video using FFmpeg
5. Outputs the downloaded file path on success

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Success — video downloaded successfully. |
| `1` | Failure — invalid URL, download error, or missing streams. |
| `130` | Interrupted by user (Ctrl+C). |

**Examples:**

```bash
# Download a video with best quality
vkdownloader download "https://vkvideo.ru/video-12345_67890"

# Download with specific quality and method
vkdownloader download "https://vkvideo.ru/video-12345_67890" --quality 720 --method ffmpeg

# Download to specific directory
vkdownloader download "https://vkvideo.ru/video-12345_67890" -o "./videos"
```

---

### 2. `batch` — Download multiple videos

Download multiple videos from a file containing URLs.

**Source:** `vkdownloader/cli.py` → `batch_download()`

```bash
vkdownloader batch [OPTIONS] URLS_FILE
```

**Arguments:**

| Name | Type | Description |
|------|------|-------------|
| `URLS_FILE` | Path | Path to file containing video URLs (one per line) |

**Options:**

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--quality` | | str | `best` | Video quality selection for all downloads |
| `--output` | `-o` | Path | `.` | Output directory for downloaded videos |
| `--method` | `-m` | str | `auto` | Download method: `yt-dlp`, `ffmpeg`, or `auto` |

**Behavior:**

1. Reads video URLs from the provided file (one URL per line)
2. Skips empty lines and lines starting with `#`
3. Downloads each video concurrently (up to 4 parallel downloads)
4. Shows a progress bar during download
5. Prints summary of successful and failed downloads

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Success — all downloads completed. |
| `1` | Failure — no URLs found in file or error occurred. |
| `130` | Interrupted by user (Ctrl+C). |

**Examples:**

```bash
# Download videos from a file
vkdownloader batch urls.txt

# Download with specific quality to output directory
vkdownloader batch urls.txt --quality 1080 -o "./downloads"

# Example urls.txt content:
# https://vkvideo.ru/video-12345_67890
# https://vkvideo.ru/video-23456_78901
# # This is a comment and will be ignored
```

---

## Download Method Options

Available method values for `--method` option:

| Value | Description |
|-------|-------------|
| `yt-dlp` | Uses yt-dlp for download with automatic segment-based resume on failure |
| `ffmpeg` | Direct ffmpeg download with browser-captured cookies |
| `auto` | Tries yt-dlp first, falls back to segment download on failure (default) |

---

## Quality Options

Available quality values for `--quality` option:

| Value | Description |
|-------|-------------|
| `240` | 240p resolution |
| `360` | 360p resolution |
| `480` | 480p resolution |
| `720` | 720p (HD) resolution |
| `1080` | 1080p (Full HD) resolution |
| `1440` | 1440p (2K) resolution |
| `2160` | 2160p (4K) resolution |
| `best` | Best available quality (default) |
| `worst` | Worst available quality |

---

## Shell Completion

Typer provides built-in shell completion:

```bash
# Install completion for the current shell
vkdownloader --install-completion

# Show the completion script (for manual installation)
vkdownloader --show-completion
```

Supports: Bash, Zsh, Fish, and PowerShell.

---

## See Also

- [Configuration Guide](../11-guides/configuration.md) — detailed configuration options.
- [Quality Selection Guide](../01-tools/quality-selection.md) — quality options and selection.
- [VK Downloader Overview](../01-tools/vkdownloader-overview.md) — architecture overview.