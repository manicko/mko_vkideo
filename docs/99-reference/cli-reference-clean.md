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
| `--max-retries` | `-r` | int | `3` | Maximum retry attempts for failed downloads; valid range 1-10 (env: `VKDOWNLOADER_MAX_RETRIES`) |
| `--quality` | | str | `best` | Video quality: `best`, `worst`, `unknown`, or any height in pixels the video offers (e.g. `720`, `1080`, `1072`) |
| `--output` | `-o` | Path | `.` | Output directory for downloaded video |
| `--method` | `-m` | str | `auto` | Download method: `yt-dlp` or `auto`. The ffmpeg download method was removed; ffmpeg is still required to merge downloaded segments. |
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
| `1` | Download failure ? the command ran and failed: invalid URL, download error, or missing streams. |
| `2` | Usage error ? rejected before the command body ran: unknown option/command, `--method ffmpeg` rejection, an invalid `--cookie-source` / `--method` value, a `--quality` token that is neither `best` / `worst` / `unknown` nor a positive height, or the missing `URL` argument. Nothing was attempted and no file was created. |
| `3` | Configuration error ? the operator's setup is wrong: an out-of-range `--max-retries` (bounds 1-10, enforced by the `Settings` model), or a preamble failure (a malformed `.env`, a setting the model rejects, or a log directory that cannot be created). |
| `130` | Interrupted by user (Ctrl+C). |
| `4`-`129`, `131`+ | Unallocated ? reserved for future use. |

`2` is a terminal outcome in its own right, deliberately separate from `1`: on `2` nothing was attempted, so a script must not treat it as a failed download. Every value printed in the parser's own error message (for example the accepted `--quality` values, quoted under [Quality Options](#quality-options)) is accepted when pasted back into the command line.

**Examples:**

```bash
# Download a video with best quality
vkdownloader download "https://vkvideo.ru/video-12345_67890"

# Download with specific quality and method
vkdownloader download "https://vkvideo.ru/video-12345_67890" --quality 720 --method yt-dlp

# Download the exact height the video offers, including a non-standard one
vkdownloader download "https://vkvideo.ru/video-12345_67890" --quality 1072

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
| `--max-retries` | `-r` | int | `3` | Maximum retry attempts for failed segment downloads; valid range 1-10 (env: `VKDOWNLOADER_MAX_RETRIES`) |
| `--quality` | | str | `best` | Video quality for all downloads: `best`, `worst`, `unknown`, or any height in pixels the video offers (e.g. `720`, `1080`, `1072`) |
| `--output` | `-o` | Path | `.` | Output directory for downloaded videos |
| `--method` | `-m` | str | `auto` | Download method: `yt-dlp` or `auto`. The ffmpeg download method was removed; ffmpeg is still required to merge downloaded segments. |
| `--cookie-source` | `-c` | str | `none` | Cookie strategy: `none` or `browser` |
| `--ssl-verify/--no-ssl-verify` | | bool | `true` | Verify SSL certificates for CDN connections. **Warning:** `--no-ssl-verify` disables certificate verification and should only be used for debugging or in isolated environments. |

**Environment Variables:**

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VKDOWNLOADER_MAX_RETRIES` | int | `3` | Maximum retry attempts for failed segment downloads (1-10) |

**Behavior:**

1. Reads video URLs from the provided file (one URL per line)
2. Skips empty lines and lines starting with `#`
3. Validates each remaining URL against the VK video URL pattern; non-matching entries are skipped with a warning and counted as invalid
4. Downloads each video concurrently as `asyncio` tasks governed by a shared semaphore (up to 4 parallel downloads)
5. Uses a per-video semaphore for video-level concurrency; segment fan-out is bounded by a separate semaphore owned by the segment layer
6. Shows a live multi-line progress display during download, one line per active download, when the output stream is a terminal
7. Prints summary of successful and failed downloads, including the number of invalid URLs skipped and any items skipped as duplicate URLs

**Progress Display:**

The display is a `rich` live multi-line view on stderr, refreshed 10 times per second, with one line per currently active download:

```
    video_2                        ━━━━╸━━╸━━━━━━━━   12%  1.8MB/s  0:00:31
    video_0: Morning in the city   ━━━━━━━━━━╸━━━━━━━━  45%  2.4MB/s  0:00:18
[✓] video_0: Morning in the city done ━━━━━━━━━━━━━━━━ 100%  2.2MB/s  0:00:00
[✗] video_1: Night walk failed    ━━╸╸╸╸╸╸╸╸╸╸╸╸╸━   8%     ?  -:--:--
```

Each line is labelled `video_{N}` during extraction and `video_{N}: {sanitized_title}` once the title is known, with columns for the status marker, label, bar, percentage, transfer speed and ETA. A finished download becomes a status line that stays on screen and scrolls up with the display: the marker is `[✓]` for `done`, `[✗]` for `failed`, and `[⊘]` for `skipped` (a duplicate URL detected within the batch — reachable) or `cancelled`, with the outcome word appended to the label. The terminal returns to normal output when the batch ends.

yt-dlp's own native progress echo is suppressed while the display is active, so it cannot interleave with the bars.

When the output stream is not a terminal (piped, redirected, or CI) the display is never started and no escape codes are written. Progress falls back to structlog INFO events `download_progress` (at most one per second per video) and `download_finished`, and yt-dlp's progress echo stays on stderr.

**Exit codes:**

| Code | Condition |
|------|-----------|
| `0` | Success ? all downloads completed. |
| `1` | Download failure ? the command ran and failed: no URLs found in the file, unreadable URL file, or an error occurred during the batch. |
| `2` | Usage error ? rejected before the command body ran: unknown option/command, `--method ffmpeg` rejection, an invalid `--cookie-source` / `--method` value, a `--quality` token that is neither `best` / `worst` / `unknown` nor a positive height, the missing `URLS_FILE` argument, or a `URLS_FILE` path that does not exist (the argument is declared with `exists=True`). Nothing was attempted and no file was created. |
| `3` | Configuration error ? the operator's setup is wrong: an out-of-range `--max-retries` (bounds 1-10, enforced by the `Settings` model), or a preamble failure (a malformed `.env`, a setting the model rejects, or a log directory that cannot be created). |
| `130` | Interrupted by user (Ctrl+C). |
| `4`-`129`, `131`+ | Unallocated ? reserved for future use. |

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
| `auto` | Downloads via yt-dlp, falls back to segment download on failure (default) |

The `ffmpeg` download method was removed. yt-dlp is the only download transport; `ffmpeg` is still required to merge downloaded segments.

---

## Cookie Source Options

Available cookie source values for `--cookie-source` option:

| Value | Description |
|-------|-------------|
| `none` | No browser launch, fastest for public videos (default) |
| `browser` | Launch browser to extract real cookies for authenticated content |

---

## Quality Options

Available quality values for `--quality` option. VK does not publish a fixed
resolution ladder ? one reported video offers `106p`, `178p`, `268p`, `358p`,
`536p`, `804p`, `1072p`, `1610p` ? so the option is not a closed list. A keyword
or any height the video actually offers is accepted:

| Value | Description |
|-------|-------------|
| `best` | Highest available resolution (default) |
| `worst` | Lowest available resolution |
| `unknown` | Stream with unavailable height (browser HLS capture) |
| `720` or `720p` | 720p resolution, when the video offers it |
| `1080` or `1080p` | 1080p resolution, when the video offers it |
| `1072` or `1072p` | 1072p resolution, a non-standard height, when the video offers it |

A height is a positive integer in pixels with an optional trailing `p`. The
token is case-insensitive and surrounding whitespace is ignored, so `720`,
`720P` and ` 720 ` are the same request.

The option's `--help` text is:

```
Video quality: best, worst, unknown, or any height in pixels the video offers (e.g. 720, 1080, 1072)
```

**Selection semantics:**

- `best` and `worst` rank the streams of the video by height. A stream whose height is unavailable is treated as absent.
- A specific height is an **exact match** on the stream's quality label. There is no silent fallback to a lower quality. When the video does not offer the requested height, `download` fails with exit code `1` and prints the requested value verbatim, followed by the ladder the video does offer:

```
Requested quality '1000' is not available for this video.
Available qualities: 106p, 178p, 268p, 358p, 536p, 804p, 1072p, 1610p
```

  In `batch`, the same condition marks that URL as failed with the `quality_not_available` status in the summary, and the command exits `1`.

**Rejected tokens:** anything that is neither a keyword nor a positive height ? a keyword other than `best`, `worst` or `unknown`, `0`, a negative number, `abc`, `720x` ? is a usage error with exit code `2`, raised during argument parsing, so nothing is downloaded:

```
Invalid value for '--quality': Use 'best', 'worst', 'unknown', or a height in pixels the video offers (e.g. 720, 1080, 1072).
```

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
