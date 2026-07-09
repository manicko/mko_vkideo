# HLS Download Throttling Bypass Research

## 1. Current Architecture Analysis

### Download Pipeline Overview

```
video_url → VKVideoExtractor.extract_streams() → m3u8_url → perform_download() → HLSDownloader
```

### Current yt-dlp Configuration (downloader.py:504-519)

```python
ydl_opts = {
    "outtmpl": str(output_file),
    "quiet": False,
    "no_warnings": True,
    "format": f"best[height<={quality_str}]",
    "nocheckcertificate": True,
    "hls_prefer_native": True,         # Uses native HLS downloader
    "http_headers": {...},
    "socket_timeout": 180,
    "retries": 10,
    "fragment_retries": 10,
    "throttledratelimit": 0,           # DISABLED - causes slow downloads!
}
```

### Segment-based Resume Implementation (downloader.py:138-150)

```python
# Sequential download - MAJOR BOTTLENECK
for i in range(downloaded_count, len(segments)):
    segment_url = segments[i]
    # ...
    success = await _download_segment(session, segment_url, segment_path, headers)
    downloaded_count += 1
```

### Key Issues Identified

| Issue | Location | Impact |
|-------|----------|--------|
| **No concurrent fragments** | `_download_with_ytdlp()` | yt-dlp downloads HLS segments sequentially, causing throughput throttling on CDN |
| **Sequential segment download** | `download_hls_with_resume()` loop | Same issue - no parallelization in fallback path |
| **AdaptiveThrottle unused** | `adaptive_throttle.py` exists but not integrated | Rate limiting mechanism available but not applied |
| **throttledratelimit=0** | Explicitly disables throttling detection | No recovery from CDN throttling |

---

## 2. Modern Throttling Bypass Practices (2024-2025)

### 2.1 Concurrent Fragment Downloads

**Source: yt-dlp Changelog 2021.03.15, yt-dlp Issue #10525, #11121**

The `--concurrent-fragments` (`-N`) option enables parallel HLS segment downloading:

- **Default**: 1 (sequential)
- **Recommended for VK**: 4-8 concurrent connections
- **Effect**: Bypasses per-connection rate limiting on CDNs

### 2.2 Throttling Detection and Recovery

**Source: yt-dlp Issue #10443 (Russian throttling), yt-dlp documentation**

```python
"throttledratelimit": 100000  # 100KB/s threshold - if speed drops below, re-extract
```

When download speed drops below threshold, yt-dlp re-extracts video for fresh URL.

### 2.3 Chunk Size Optimization

**Source: yt-dlp README 2024**

```python
"http_chunk_size": 10485760  # 10MB chunks to bypass web server throttling
```

Larger chunks reduce connection overhead and throttling impact.

---

## 3. Priority Recommendations for VK Video

### HIGH Priority (Immediate Implementation)

1. **Enable concurrent-fragments for yt-dlp**
   - Add `concurrent_fragments` parameter to Settings
   - Apply in `_download_with_ytdlp()`: `"concurrent_fragments": 4`
   - **Expected improvement**: 3-5x download speed

2. **Enable throttled-rate detection**
   - Remove `"throttledratelimit": 0` line or set to `100000` (100KB/s)
   - **Expected improvement**: Automatic recovery from throttling

3. **Parallelize segment-based download**
   - Modify `download_hls_with_resume()` to use semaphore with concurrent downloads
   - Use `asyncio.Semaphore(settings.max_concurrent_downloads)` (currently 4)
   - **Expected improvement**: 3-4x speed in fallback mode

---

## 4. Recommended Implementation

### Settings Changes (config.py)

```python
concurrent_fragments: int = Field(
    default=4,
    ge=1,
    le=16,
    description="Concurrent HLS fragment downloads for yt-dlp",
)
throttled_rate: int = Field(
    default=100000,  # 100KB/s
    ge=50000,
    le=1000000,
    description="Minimum download rate before throttling detection triggers re-extract",
)
```

### yt-dlp Options Update (downloader.py)

```python
# In _download_with_ytdlp():
ydl_opts = {
    ...
    "concurrent_fragments": settings.concurrent_fragments,  # ADD
    "throttledratelimit": settings.throttled_rate,         # CHANGE from 0
    "http_chunk_size": 10485760,                         # ADD
}
```

---

## 6. Detailed Implementation Plan

### 6.1 Settings Configuration (config.py)

Add new fields to `Settings` class after line 62 (after `max_concurrent_downloads`):

```python
concurrent_fragments: int = Field(
    default=4,
    ge=1,
    le=16,
    description="Concurrent HLS fragment downloads for yt-dlp (reduces throttling)",
)
throttled_rate: int = Field(
    default=100000,
    ge=50000,
    le=1000000,
    description="Minimum download rate in bytes/sec before throttling triggers re-extract",
)
http_chunk_size: int = Field(
    default=10485760,  # 10MB
    ge=1048576,
    le=104857600,
    description="HTTP chunk size in bytes for segment downloads",
)
```

### 6.2 yt-dlp Options Update (downloader.py)

Replace `ydl_opts` in `_download_with_ytdlp()` (lines 504-519):

```python
# BEFORE:
ydl_opts = {
    "outtmpl": str(output_file),
    "quiet": False,
    "no_warnings": True,
    "format": f"best[height<={quality_str}]",
    "nocheckcertificate": True,
    "hls_prefer_native": True,
    "http_headers": {
        "User-Agent": user_agent,
        "Referer": "https://vkvideo.ru/",
    },
    "socket_timeout": 180,
    "retries": 10,
    "fragment_retries": 10,
    "throttledratelimit": 0,  # REMOVE THIS LINE
}

# AFTER:
ydl_opts = {
    "outtmpl": str(output_file),
    "quiet": False,
    "no_warnings": True,
    "format": f"best[height<={quality_str}]",
    "nocheckcertificate": True,
    "hls_prefer_native": True,
    "concurrent_fragments": settings.concurrent_fragments,
    "throttledratelimit": settings.throttled_rate,
    "http_chunk_size": settings.http_chunk_size,
    "http_headers": {
        "User-Agent": user_agent,
        "Referer": "https://vkvideo.ru/",
    },
    "socket_timeout": 180,
    "retries": 10,
    "fragment_retries": 10,
}
```

### 6.3 Segment-based Download Parallelization (downloader.py)

Replace the sequential loop (lines 137-150) with concurrent downloads:

```python
# Add import at top
import asyncio

# Replace loop section with:
semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)

async def download_segment_concurrent(idx: int, segment_url: str) -> bool:
    """Download segment with semaphore rate limiting."""
    async with semaphore:
        full_url = segment_url
        if not segment_url.startswith("http"):
            full_url = urljoin(request.m3u8_url, segment_url)
        segment_path = segments_dir / f"{idx:05d}.ts"
        if not segment_path.exists():
            return await _download_segment(session, full_url, segment_path, headers)
        return True

# Download all missing segments concurrently
tasks = [
    download_segment_concurrent(i, seg)
    for i, seg in enumerate(segments)
    if not (segments_dir / f"{i:05d}.ts").exists()
]
results = await asyncio.gather(*tasks)
if not all(results):
    return None
downloaded_count = len(segments)
```

---

## 7. Testing Strategy

### 7.1 Automated Tests (to be added)

1. **Test concurrent_fragments parameter**
```python
def test_concurrent_fragments_default(test_settings):
    assert test_settings.concurrent_fragments == 4

def test_concurrent_fragments_custom(self, test_settings):
    settings = Settings(concurrent_fragments=8)
    assert settings.concurrent_fragments == 8
```

2. **Test throttled_rate parameter**
```python
def test_throttled_rate_default(test_settings):
    assert test_settings.throttled_rate == 100000

def test_throttled_rate_triggers_reextract(self, tmp_path):
    # Mock segment downloads that are slow, verify re-extract triggered
```

3. **Test parallel segment download**
```python
@pytest.mark.asyncio
async def test_parallel_segments_faster_than_sequential(self, tmp_path):
    # Compare time for sequential vs concurrent downloads
```

### 7.2 Manual Testing

1. Download test video with current code (baseline speed)
2. Apply changes and re-download same video
3. Compare download times and speeds

Test video: `https://vkvideo.ru/video-113218548_456242260`

---

## 8. Browser-Like Behavior (Human Impersonation)

### 8.1 Current Browser Integration

The project already has browser automation via Playwright (`VKVideoExtractor._extract_with_browser()`), which captures:
- **Cookies** - via `page.context.cookies()` → formatted for ffmpeg headers
- **m3u8 URLs** - via `NetworkMonitor` intercepting network responses

However, **yt-dlp extraction (`extract_streams`) does NOT use browser cookies**. It uses yt-dlp standalone.

### 8.2 Making yt-dlp More Browser-Like

#### Option A: Pass Cookies to yt-dlp (Recommended)

```python
# In downloader.py or extractor.py
def _build_ydl_cookies_header(cookies_str: str | None) -> str:
    """Convert cookies string to Netscape format for yt-dlp."""
    if not cookies_str:
        return ""
    
    lines = [
        "# Netscape HTTP Cookie File",
        "# This file is generated by vkdownloader",
        "",
    ]
    for cookie in cookies_str.split("; "):
        if "=" in cookie:
            name, value = cookie.split("=", 1)
            lines.append(f".vkvideo.ru\tTRUE\t/\tFALSE\t0\t{name}\t{value}")
    return "\n".join(lines)

# In download flow:
browser_streams, cookies = await extractor.extract_streams_with_cookies(url)
if cookies:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(_build_ydl_cookies_header(cookies))
    ydl_opts["cookiefile"] = str(cookie_file)
```

#### Option B: Use curl-impersonate (Advanced)

yt-dlp supports `--impersonate` for realistic browser headers:

```python
ydl_opts = {
    "impersonate": "chrome:windows-10",  # or "safari:macos"
    # Requires curl-cffi package
}
```

Available targets (via `--list-impersonate-targets`):
- Chrome-110/107/104/101/100 on Windows-10
- Safari-15.5 on macOS
- Edge variants

**Risk**: May reduce stability, requires curl-cffi dependency.

#### Option C: Combined Approach

1. Use browser for extraction → capture fresh authenticated m3u8 URL + cookies
2. Pass cookies to yt-dlp via `cookiefile`
3. Enable concurrent fragments for speed
4. Add realistic delays between fragments (using `sleep_interval`)

### 8.3 Implementation for Human-Like yt-dlp

```python
# In downloader.py - modify _download_with_ytdlp to accept cookies

async def _download_with_ytdlp(
    video_url: str, 
    output_file: Path, 
    quality: str, 
    settings: Settings,
    cookies: str | None = None,  # ADD parameter
) -> Path | None:
    ...
    def _download() -> str:
        ydl_opts = {
            ...
            "concurrent_fragments": settings.concurrent_fragments,
            "throttledratelimit": settings.throttled_rate,
            "http_chunk_size": settings.http_chunk_size,
        }
        
        # ADD: Pass cookies to yt-dlp
        if cookies:
            # Create cookies.txt in Netscape format
            cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
            cookie_file.write_text(_cookies_to_netscape(cookies))
            ydl_opts["cookiefile"] = str(cookie_file)
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        ...
```

```python
# Helper function to convert cookies string to Netscape format

def _cookies_to_netscape(cookies_str: str) -> str:
    """Convert cookies string to Netscape HTTP Cookie File format."""
    lines = [
        "# Netscape HTTP Cookie File",
        "# Generated by vkdownloader",
        "",
    ]
    for cookie in cookies_str.split("; "):
        if "=" in cookie:
            name, value = cookie.split("=", 1)
            # Match VK's CDN domain patterns
            domain = ".vkvideo.ru"
            lines.append(f"{domain}\tTRUE\t/\tFALSE\t0\t{name}\t{value}")
    return "\n".join(lines)
```

```python
# In perform_download() - modify for YTDLP case

match method:
    case DownloadMethod.YTDLP:
        # First get cookies via browser for authenticated requests
        browser_streams, cookies = await extractor.extract_streams_with_cookies(url)
        if browser_streams:
            m3u8_url = str(browser_streams[0].url)
        
        return await download_with_ytdlp_with_resume_fallback(
            url, m3u8_url, output_file, quality, extractor, settings,
            cookies=cookies  # Pass cookies
        )
```

### 8.4 Additional yt-dlp Impersonation Options

```python
ydl_opts = {
    # Primary options for browser-like behavior
    "concurrent_fragments": 4,
    "throttledratelimit": 100000,
    "http_chunk_size": 10485760,
    
    # Sleep between downloads (mimics human behavior)
    "sleep_interval": 1,      # Minimum seconds between requests
    "max_sleep_interval": 3,  # Maximum random variation
    
    # Extractor impersonation (requires curl-cffi)
    "impersonate": "chrome",  # or "safari", "edge"
    
    # Generic extractor args for impersonation
    "extractor_args": {
        "generic": {
            "impersonate": "chrome",
        },
    },
}
```

**Available impersonate targets** (via `yt-dlp --list-impersonate-targets`):
- Chrome-110/107/104/101/100 (Windows-10)
- Safari-15.5 (macOS)
- Edge-101/99 (Windows-10)

**Note**: curl-cffi package required for impersonate feature. May affect stability.

---

## 10. Priority Implementation Order

### Option 1: Minimal Changes (Fastest Deployment)
1. Add `concurrent_fragments` and `throttled_rate` to Settings
2. Apply to yt-dlp options in `_download_with_ytdlp()`
3. **Expected: 3-5x speed improvement**

### Option 2: Browser-Cookies Integration (Best Anti-Throttling)
1. All of Option 1
2. Add cookie file generation from browser extraction
3. Pass `cookiefile` to yt-dlp options
4. **Expected: Better authentication, avoids token rejection**

### Option 3: Full Parallelization (Maximum Performance)
1. All of Option 2
2. Parallelize segment download in `download_hls_with_resume()`
3. Integrate `AdaptiveThrottle` for rate limiting
4. **Expected: Maximum speed, automatic throttling recovery**

---

## 11. References

1. **yt-dlp Changelog 2021.03.15** - Parallel fragment downloads with `-N`
2. **yt-dlp Issue #10525** - HLS rate limiting behavior with concurrent fragments
3. **yt-dlp Issue #11121** - YouTube throttling on less popular content
4. **yt-dlp Issue #10443** - Russian ISP DPI throttling workarounds
5. **VK Video HLS Architecture** (GogoAI News, 2025) - Token expiration, authentication layers