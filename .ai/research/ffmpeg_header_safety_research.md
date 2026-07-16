# FFmpeg Header Safety Research

**Task ID:** research_ffmpeg_header_safety  
**Source Reference:** SEC-001 (Security Finding)  
**Date:** 2026-07-16

## Executive Summary

**Recommendation: GO** - The `@file` syntax approach is viable and should be implemented. The temp file lifecycle pattern is straightforward and mirrors existing cookie file cleanup patterns already in the codebase.

## Problem Analysis

### Current Vulnerability (SEC-001)

The `_build_ffmpeg_cmd` method in `src/vkdownloader/services/downloader.py` passes cookies as a command-line argument:

```python
def _build_ffmpeg_cmd(
    self, m3u8_url: str, output_file: Path, cookies: str | None = None
) -> list[str]:
    cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""
    headers = f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n{cookie_part}"

    cmd = [
        "ffmpeg",
        "-y",
        "-progress", "pipe:2",
        "-nostats",
        "-headers", headers,  # VULNERABILITY: cookies visible in process listing
        "-i", m3u8_url,
        "-c", "copy",
        str(output_file),
    ]
    return cmd
```

**Exposure Vector:** When `asyncio.create_subprocess_exec(*cmd)` is called, the cookies string is visible via:
- `ps aux` (Linux/macOS)
- `/proc/<pid>/cmdline` (Linux)
- `htop`, `docker top`, `docker inspect` (containerized environments)

## FFmpeg @file Syntax Solution

### How It Works

FFmpeg supports reading option arguments from a file using the `@` prefix:

```bash
# Current (vulnerable):
ffmpeg -headers "User-Agent: xyz\r\nCookie: remixsid=secret\r\n" -i url.m3u8 ...

# Secure (with @file):
ffmpeg -headers @headers.txt -i url.m3u8 ...
```

When using `@filename`, ffmpeg reads the option value from the file, keeping secrets out of process arguments.

### Requirements

1. The file must exist before calling ffmpeg
2. The file content is the literal header string (not the argument itself)
3. File path becomes the only argument (no secrets in arguments)

### Example Implementation Pattern

```python
import tempfile
from pathlib import Path
from contextlib import contextmanager

@contextmanager
def _temp_headers_file(headers: str) -> Path:
    """Create temporary file with headers for secure ffmpeg invocation."""
    fd, path = tempfile.mkstemp(suffix=".headers", prefix="vk_ffmpeg_")
    try:
        os.write(fd, headers.encode())
        os.close(fd)
        yield Path(path)
    finally:
        Path(path).unlink(missing_ok=True)

# Usage in download_with_ffmpeg:
headers = f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\nCookie: {cookies}\r\n"
with _temp_headers_file(headers) as headers_file:
    cmd = [
        "ffmpeg",
        "-y",
        "-progress", "pipe:2",
        "-nostats",
        "-headers", f"@{headers_file}",  # Safe: only filename in args
        "-i", m3u8_url,
        "-c", "copy",
        str(output_file),
    ]
    process = await asyncio.create_subprocess_exec(*cmd, ...)
```

## Temp File Lifecycle Strategy

### Pattern 1: Context Manager (Recommended)

**Pros:**
- Guaranteed cleanup even on exceptions
- Clear ownership semantics
- Minimal code changes

**Cons:**
- Headers file must exist during process execution
- Process reads file before completion

### Pattern 2: async contextlib with Explicit Cleanup

For async compatibility, use `contextlib.asynccontextmanager`:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def _temp_headers_file(headers: str) -> Path:
    """Async context manager for temp headers file."""
    fd, path = tempfile.mkstemp(suffix=".headers", prefix="vk_ffmpeg_")
    try:
        os.write(fd, headers.encode())
        os.close(fd)
        yield Path(path)
    finally:
        Path(path).unlink(missing_ok=True)
```

### Cleanup Considerations

1. **File creation:** Use `tempfile.mkstemp()` for secure temp file creation
2. **Permissions:** Default umask applies; file should have appropriate permissions (600 recommended)
3. **Location:** System temp directory, cleaned on reboot
4. **Race conditions:** File created just before use, deleted immediately after

### Existing Pattern Reference

The codebase already implements cookie file cleanup in `_download_with_ytdlp`:

```python
# Lines 462-481 in downloader.py
cookie_file: Path | None = None
if cookies:
    cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
    cookie_file.write_text(_cookies_to_netscape(cookies))
    ydl_opts["cookiefile"] = str(cookie_file)

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
finally:
    if cookie_file is not None and cookie_file.exists():
        cookie_file.unlink()
```

This pattern proves the codebase handles temp file cleanup correctly.

## Impact Assessment

### Files Affected

| File | Method | Change Type |
|------|--------|-------------|
| `src/vkdownloader/services/downloader.py` | `_build_ffmpeg_cmd` | Refactor to support file-based headers |
| `src/vkdownloader/services/downloader.py` | `download_with_ffmpeg` | Add temp file lifecycle management |

### Behavior Changes

1. **No API changes:** Method signatures remain identical
2. **No output changes:** Commands produce identical ffmpeg behavior
3. **Security improvement:** Secrets no longer visible in process listings

### Edge Cases

1. **Empty headers:** If no cookies, skip file creation (current behavior preserved)
2. **Long headers:** Same limit as current (~20 cookies, 8KB HTTP header limit)
3. **Concurrent downloads:** Unique temp files prevent collisions
4. **Process interrupted:** File cleanup in `finally` block

## Go/No-Go Recommendation

**GO** - Implementation is recommended with the following approach:

1. Add `_temp_headers_file` context manager to `downloader.py`
2. Modify `_build_ffmpeg_cmd` to accept optional temp file path or return headers separately
3. Update `download_with_ffmpeg` to wrap subprocess execution in context manager
4. Add test for `@filename` syntax in command building

## Test Considerations

The test suite will need updates:

```python
def test_ffmpeg_command_uses_file_syntax_for_cookies(self, test_settings: Settings) -> None:
    """Test ffmpeg command uses @file syntax when cookies provided."""
    downloader = HLSDownloader(settings=test_settings)
    output_path = Path("/tmp/output.mp4")
    cookies = "vk=abc123; session=xyz"

    cmd = downloader._build_ffmpeg_cmd(m3u8_url, output_path, cookies)

    # Should use @file syntax instead of inline headers
    headers_index = cmd.index("-headers")
    headers_value = cmd[headers_index + 1]
    assert headers_value.startswith("@"), "Should use @file syntax for cookies"
```

## References

- FFmpeg documentation: `-headers` option accepts file input with `@` prefix
- Similar pattern: yt-dlp's `cookiefile` option (already successfully implemented)
- Security best practice: Never pass secrets via CLI arguments