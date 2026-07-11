# Research Report: Hidden Consumers of extract_streams_with_cookies

## Summary

Analysis of all code paths that call `extract_streams_with_cookies` to identify hidden consumers
that may break when the method becomes conditional on `settings.cookie_source`.

## Direct Callers of `extract_streams_with_cookies`

### 1. `perform_download()` - downloader.py:840 (YTDLP branch)
- **Location**: `src/vkdownloader/services/downloader.py`, lines 838-846
- **Code**: `browser_streams, cookies = await extractor.extract_streams_with_cookies(url)`
- **Context**: Called unconditionally for YTDLP download method
- **Impact**: HIGH - Browser always launched when using YTDLP method

### 2. `perform_download()` - downloader.py:849 (FFMPEG branch)
- **Location**: `src/vkdownloader/services/downloader.py`, lines 847-869
- **Code**: `browser_streams, cookies = await extractor.extract_streams_with_cookies(url)`
- **Context**: Called unconditionally for FFMPEG download method
- **Impact**: HIGH - Browser always launched when using FFMPEG method

### 3. `download_with_ytdlp_with_resume_fallback()` - downloader.py:712 (token refresh)
- **Location**: `src/vkdownloader/services/downloader.py`, lines 710-714
- **Code**: `browser_streams, cookies = await extractor.extract_streams_with_cookies(video_url)`
- **Context**: Called when yt-dlp download fails and partial file exists (retry loop)
- **Impact**: HIGH - This is critical for resume functionality with token refresh

### 4. `_fetch_playlist_with_retry()` - downloader.py:364 (token refresh)
- **Location**: `src/vkdownloader/services/downloader.py`, lines 362-368
- **Code**: `streams, new_cookies = await extractor.extract_streams_with_cookies(video_url)`
- **Context**: Called when m3u8 playlist fetch returns 403/410
- **Impact**: CRITICAL - Token refresh for segment downloads

## Indirect Callers (via `_fetch_playlist_with_retry`)

### `download_hls_with_resume()` - downloader.py:281
- **Location**: `src/vkdownloader/services/downloader.py`, line 281
- **Function signature**: `_fetch_playlist_with_retry(session, request.m3u8_url, request.video_url, headers, request.extractor, settings)`
- **Context**: Downloads HLS segments with resume support
- **Token refresh scenario**: When CDN returns 403/410, `_fetch_playlist_with_retry` calls `extract_streams_with_cookies` to get fresh token
- **Impact**: CRITICAL - Without token refresh, segment downloads fail permanently on auth expiry

## Call Graph

```
perform_download (line 744)
├── DownloadMethod.YTDLP (line 840)
│   └── extractor.extract_streams_with_cookies() [ALWAYS]
│       └── download_with_ytdlp_with_resume_fallback (line 843)
│           └── extract_streams_with_cookies() [on retry for resume] (line 712)
│               └── download_hls_with_resume (line 721)
│                   └── _fetch_playlist_with_retry (line 281)
│                       └── extract_streams_with_cookies() [on 403/410] (line 364)
│
├── DownloadMethod.FFMPEG (line 849)
│   └── extractor.extract_streams_with_cookies() [ALWAYS]
│       └── download_with_ffmpeg (line 853)
│           └── download_hls_with_resume (line 858)
│               └── _fetch_playlist_with_retry (line 281)
│                   └── extract_streams_with_cookies() [on 403/410] (line 364)
│
└── DownloadMethod.AUTO (line 872)
    └── download_with_ytdlp_with_resume_fallback (line 872)
        └── extract_streams_with_cookies() [on retry for resume] (line 712)
            └── download_hls_with_resume (line 721)
                └── _fetch_playlist_with_retry (line 281)
                    └── extract_streams_with_cookies() [on 403/410] (line 364)
```

## Impact Assessment for `cookie_source=NONE`

### Current Problem
When `cookie_source=NONE` is set:
- `extract_streams_with_cookies` currently ALWAYS launches the browser
- The method name implies it should use cookies, but no conditional check exists
- This defeats the purpose of the `cookie_source` setting

### Risk Analysis

| Caller | Risk Level | Issue |
|--------|------------|-------|
| `perform_download` YTDLP | MEDIUM | Public videos don't need browser; unnecessary overhead |
| `perform_download` FFMPEG | MEDIUM | Same as above |
| `download_with_ytdlp_with_resume_fallback` line 712 | CRITICAL | Token refresh without cookies will fail for private/content-restricted videos |
| `_fetch_playlist_with_retry` line 364 | CRITICAL | Segment downloads will permanently fail when 403/410 occurs |

### Token Refresh Scenarios

1. **Resume after interruption** (`download_with_ytdlp_with_resume_fallback`, line 712):
   - When yt-dlp fails mid-download with partial file
   - Browser extracts fresh m3u8 URL with valid token
   - Without cookies capability, resume will fail

2. **Segment download auth expiry** (`_fetch_playlist_with_retry`, line 364):
   - During long segment downloads, CDN token may expire
   - Returns 403/410, triggers retry with fresh token
   - Without cookies, segment downloads cannot recover

## Go/No-Go Recommendation

### Status: **GO with modifications**

### Recommendation Details

1. **`extract_streams_with_cookies` should implement conditional browser launch**:
   - Check `self.settings.cookie_source` at method entry
   - If `cookie_source == CookieSource.NONE`: skip browser, return empty cookies
   - If `cookie_source == CookieSource.BROWSER`: launch browser (current behavior)
   - If `cookie_source == CookieSource.FILE`: use file-based cookies (not yet implemented)

2. **Token refresh requires special handling**:
   - `_fetch_playlist_with_retry` and `download_with_ytdlp_with_resume_fallback` need the browser
   - These should either:
     - Pass a flag to force browser launch regardless of setting
     - OR use a separate internal method that always launches browser for recovery

3. **Implementation approach**:
   - Add `_extract_streams_internal(force_browser: bool = False)` parameter
   - Token refresh paths pass `force_browser=True`
   - Direct callers respect `cookie_source` setting

### Confidence Level: HIGH (90%)

The analysis is comprehensive based on code review of all production and test files.

## Test Expectations

Current tests mock `extract_streams_with_cookies` and do not verify conditional behavior:
- `tests/test_extractor.py` lines 69-77, 123-141: Test extraction success/failure
- `tests/test_hls_downloader.py` lines 910-912, 1045-1047: Mock return value, no cookie_source check

Tests will need updates to verify:
- `extract_streams_with_cookies` skips browser when `cookie_source=NONE`
- `extract_streams_with_cookies` launches browser when `cookie_source=BROWSER`
- Token refresh paths still work regardless of `cookie_source`

## Files Requiring Changes

1. **src/vkdownloader/services/extractor.py**: Add conditional check in `extract_streams_with_cookies`
2. **src/vkdownloader/services/downloader.py**: Update token refresh calls to handle `cookie_source=NONE`
3. **tests/test_extractor.py**: Add tests for conditional browser behavior
4. **tests/test_hls_downloader.py**: Update mocks to include settings in HLSDownloadRequest