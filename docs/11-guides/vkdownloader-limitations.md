---
id: vkdownloader-limitations-and-workarounds
domain: guides
tags:
  - limitations
  - workarounds
  - vk
  - hls
related:
  - vkdownloader-overview
  - vkdownloader-api-reference
---

# VK Video Downloader Limitations and Workarounds

## Purpose

Document key findings from development: what works, what doesn't, and workarounds for VK's anti-bot protection.

## Main Concepts

### Key Findings

1. **Videos accessible without login** - VK video pages can be opened and video metadata extracted without authentication
2. **Strong bot protection** - VK implements multiple layers: headless detection, time-limited tokens, CDN request authentication
3. **Speed limitations** - yt-dlp has artificial throttling (~100KB/s); segment download provides full speed with resume support

## Protection Mechanisms

### 1. Headless Browser Detection

**Finding:** VK implements multi-layer bot detection:
- `navigator.webdriver` flag (masked by stealth.min.js when `stealth_enabled` is true)
- WebGL fingerprinting (partially masked)
- Canvas rendering (masked via getContext override)
- Missing Chrome plugins/extensions
- Unusual screen/window dimensions (masked)

**Technical limitation:** Complete browser emulation requires:
- Consistent GPU/driver fingerprint
- Realistic mouse movement patterns
- Proper audio/video device enumeration
- Real Chrome extension signatures

**Workaround:** Use non-headless browser (`headless=False`). Trade-off: user must wait for browser window.

### 2. Time-Limited m3u8 Tokens

**Finding:** m3u8 URLs contain expiring tokens (typically valid 1-2 hours).

**Example URL structure:**
```
https://vkvdXXX.okcdn.ru/?expires=1783915662438&sig=XXXXX&urls=...
```

**Consequence:** Tokens expire during long downloads, causing incomplete files.

**Workaround:** Extract m3u8 URL immediately before download, ensure quick download, and use segment download with resume support for long-running downloads.

### 3. CDN Request Authentication

**Finding:** CDN segments require cookies from the browser session.

**Workaround:** Extract cookies from active browser session and pass to yt-dlp. Cookies are written to a temporary Netscape cookie file (requested at `0o600`, which is owner-only on POSIX; on Windows `os.chmod` only toggles the read-only attribute, so the owner-only guarantee is not offered there) and supplied to yt-dlp via its configuration file.

## Download Methods Comparison

| Method | Speed | Reliability | Notes |
|--------|-------|-------------|-------|
| yt-dlp direct | ~100KB/s | High | Handles token refresh automatically |
| Segment download | Variable | High | Has retry backoff and anti-detection delay |

### Segment Download Throttling

When `max_concurrent_downloads=1` (sequential mode), the downloader applies:

- **Anti-detection delay**: 1.5s + random(0, 0.5s) between segment requests
- **Retry backoff**: AWS Full Jitter on 429/5xx errors (1s base for 429, 0.05s for 5xx)
- **Delay placement**: After semaphore release to avoid blocking concurrency mechanism

### Segment Merge Disk Space

The segment path merges in two stages, and each stage writes its output while its input is still on disk: the batch temp files are produced from the segments, then the final file is produced from those batch temp files, which are deleted only after the final write succeeds. Peak disk usage is therefore a **multiple** of the finished video, not a copy of it. Measured by sampling the working directory's total size throughout a real merge and recording the peak, amplification was **2.96×** — budget about **three times the video's size** in free space on the output volume.

That factor is a measured approximation, not a hard guarantee. It depends on segment count, segment size and filesystem behaviour, and a different video can land either side of it.

**Early failure:** before the first merge subprocess is spawned, the downloader measures the segments actually on disk and compares the requirement — the segment bytes twice, because the final artefact is written while the segments are still there, plus a 64 MiB safety margin — against the volume's free space. When the volume is short, the merge stops before anything is written and reports the bytes required, the bytes available, and what to do about it: free disk space, write to a different output volume, or select a lower quality. The downloaded segments are preserved, so the download can be resumed once there is room.

Two limits of that check, stated plainly:

- If the free-space figure cannot be read at all — an unusual or unreadable mount — the check logs it and lets the merge proceed. An unreadable volume is not evidence of a full one, and a failed probe must not block a download that would have succeeded.
- A volume can still fill *after* the probe, because another process may consume the space and the probe cannot predict that. The merge is also the one download step that cannot be resumed, since its input segments are still needed. When this happens ffmpeg fails on its own write and the merge returns a failure with no partial output.

## What Works

1. **Browser automation (non-headless)** - Captures m3u8 URLs and cookies
2. **yt-dlp download** - Downloads with segment-level resume on token expiration
3. **Automatic fallback** - Segment retry when yt-dlp fails

## What Doesn't Work

1. **`ffmpeg -ssl_verification`** - Invalid option, causes immediate failure. Correct flag is `-tls_verify 0`.
2. **Headless browser** - May be detected and blocked by VK
3. **Long-running downloads** - Token expiration leads to incomplete downloads (segment download with resume support mitigates this)
4. **Cookie-only approach without browser** - Cookies expire/invalidate without active session
5. **yt-dlp cancellation in batch mode** - yt-dlp runs in an executor thread that cannot be terminated by `asyncio.CancelledError`; the thread persists as a zombie until process exit. This is a CPython `concurrent.futures` limitation: `Future.cancel()` returns `False` for running futures. No workaround within the current architecture. `VKDOWNLOADER_DOWNLOAD_TIMEOUT` bounds how long the event loop waits for that thread, not the wait for the thread itself: on expiry only the asyncio future is cancelled, and the abandoned thread is joined later at interpreter shutdown under the interpreter's own thread-join rule. |

## Recommended Usage

For public videos (fastest download, no authentication needed):
```bash
vkdownloader download --cookie-source none "VIDEO_URL"
```
- No browser launch, fastest execution
- Uses yt-dlp with segment-level resume

For authenticated content:
```bash
vkdownloader download --cookie-source browser "VIDEO_URL"
```
- Browser opens (user must wait for page load)
- m3u8 URL captured with fresh token
- yt-dlp downloads with captured cookies
- Falls back to segment download if needed

For most reliable download (~100KB/s):
```bash
vkdownloader download --method yt-dlp --cookie-source browser --quality 720 "VIDEO_URL"
```
- Accepts a keyword (`--quality best`, `worst`, `unknown`) or any height in pixels the video actually offers (`--quality 720`, `--quality 1072`, ...). There is no fixed resolution set, because VK publishes non-standard ladders
- A specific height is an exact match on the stream's quality label; there is no silent fallback to a lower quality, so a height the video does not offer is reported with the ladder it does offer
- Cookies are captured fresh from the browser. The browser-captured stream is only re-selected for `--quality best`; for any other request the stream selected before the browser launch is reused, because the browser capture labels its streams `unknown` (no height)
- Falls back to segment download if yt-dlp fails