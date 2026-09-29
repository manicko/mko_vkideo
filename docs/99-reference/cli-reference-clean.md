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

**Package:** `vkdownloader` ? VK Video Downloader for vkvideo.ru

The CLI is built with [Typer](https://typer.tiangolo.com/). The `batch` command shows a live multi-line progress display during concurrent downloads; the single `download` command shows no live progress during execution.

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

### 1. `download` ? Download a single video

Download a video from vkvideo.ru with quality and method selection support.

**Source:** `vkdownloader/cli.py` ? `download()`

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
| `--cookie-source` | `-c` | str | `none` | Cookie strategy: `none` or `browser` |
| `--ssl-verify/--no-ssl-verify` | | bool | `true` | Verify SSL certificates for CDN connections. **Warning:** `--no-ssl-verify` disables certificate verification and should only be used for debugging or in isolated environments. |

**Behavior:**

1. Extracts available streams from the provided VK video URL
2. Selects the requested quality (or best available by default)
3. Validates and creates the output directory
4. Downloads using the selected method (default: auto)
5. Outputs the downloaded file path on success

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Success ? video downloaded successfully. |
| `1` | Failure ? the command ran and failed: invalid URL, configuration error, download error, or missing streams. |
| `2` | Usage error ? the command line was rejected by the argument parser before anything ran: unknown option, invalid `--quality` / `--method` / `--cookie-source` value, or the missing `URL` argument. Nothing was downloaded and no file was created. |
| `130` | Interrupted by user (Ctrl+C). |

`2` is a terminal outcome in its own right, deliberately separate from `1`: on `2` nothing was attempted, so a script must not treat it as a failed download. Every value printed in the parser's own error message (for example the accepted `--quality` values) is accepted when pasted back into the command line.

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

### 2. `batch` ? Download multiple videos

Download multiple videos from a file containing URLs.

**Source:** `vkdownloader/cli.py` ? `batch_download()`

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
| `--max-retries` | `-r` | int | `3` | Maximum retry attempts for failed segment downloads (env: `VKDOWNLOADER_MAX_RETRIES`) |
| `--quality` | | str | `best` | Video quality selection for all downloads |
| `--output` | `-o` | Path | `.` | Output directory for downloaded videos |
| `--method` | `-m` | str | `auto` | Download method: `yt-dlp`, `ffmpeg`, or `auto` |
| `--cookie-source` | `-c` | str | `none` | Cookie strategy: `none` or `browser` |
| `--ssl-verify/--no-ssl-verify` | | bool | `true` | Verify SSL certificates for CDN connections. **Warning:** `--no-ssl-verify` disables certificate verification and should only be used for debugging or in isolated environments. |

**Environment Variables:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VKDOWNLOADER_MAX_RETRIES` | int | `3` | Maximum retry attempts for failed segment downloads (1-10) |

**Behavior:**

1. Reads video URLs from the provided file (one URL per line)
2. Skips empty lines and lines starting with `#`
3. Downloads each video concurrently as `asyncio` tasks governed by a shared semaphore (up to 4 parallel downloads)
4. Uses a per-video semaphore for video-level concurrency; segment fan-out is bounded by a separate semaphore owned by the segment layer
5. Shows a live multi-line progress display during download, one line per active download, when the output stream is a terminal
6. Prints summary of successful and failed downloads

**Progress Display:**

The display is a `rich` live multi-line view on stderr, refreshed 10 times per second, with one line per currently active download:

```
    video_2                        ━━━━╸━━╸━━━━━━━━   12%  1.8MB/s  0:00:31
    video_0: Morning in the city   ━━━━━━━━━━╸━━━━━━━━  45%  2.4MB/s  0:00:18
[✓] video_0: Morning in the city done ━━━━━━━━━━━━━━━━ 100%  2.2MB/s  0:00:00
[✗] video_1: Night walk failed    ━━╸╸╸╸╸╸╸╸╸╸╸╸╸━   8%     ?  -:--:--
```

Each line is labelled `video_{N}` during extraction and `video_{N}: {sanitized_title}` once the title is known, with columns for the status marker, label, bar, percentage, transfer speed and ETA. A finished download becomes a status line that stays on screen and scrolls up with the display: the marker is `[✓]` for `done`, `[✗]` for `failed`, and `[⊘]` for `skipped` or `cancelled`, with the outcome word appended to the label. The terminal returns to normal output when the batch ends.

yt-dlp's own native progress echo is suppressed while the display is active, so it cannot interleave with the bars.

When the output stream is not a terminal (piped, redirected, or CI) the display is never started and no escape codes are written. Progress falls back to structlog INFO events `download_progress` (at most one per second per video) and `download_finished`, and yt-dlp's progress echo stays on stderr.

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Success ? all downloads completed. |
| `1` | Failure ? the command ran and failed: no URLs found in the file, unreadable URL file, or an error occurred during the batch. |
| `2` | Usage error ? the command line was rejected by the argument parser before anything ran: unknown option, invalid `--quality` / `--method` / `--cookie-source` value, the missing `URLS_FILE` argument, or a `URLS_FILE` path that does not exist (the argument is declared with `exists=True`). Nothing was downloaded and no file was created. |
| `130` | Interrupted by user (Ctrl+C). |

`2` is a terminal outcome in its own right, deliberately separate from `1`: on `2` nothing was attempted, so a script must not treat it as a failed batch. It is also the outcome of invoking `vkdownloader` with no command, an unknown command, or an unknown option.

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

## Cookie Source Options

Available cookie source values for `--cookie-source` option:

| Value | Description |
|-------|-------------|
| `none` | No browser launch, fastest for public videos (default) |
| `browser` | Launch browser to extract real cookies for authenticated content |

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

- [Configuration Guide](../11-guides/configuration.md) ? detailed configuration options.
- [Quality Selection Guide](../01-tools/quality-selection.md) ? quality options and selection.
- [VK Downloader Overview](../01-tools/vkdownloader-overview.md) ? architecture overview.
