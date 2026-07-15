# Phase 06 Audit Findings — End-to-End Data Flow (Validated)

**Executor:** validator  
**Source:** /.ai/audit/06-audit-data-flow/findings.md  
**Status:** complete

> **Scope note (mandatory context):** The assigned phase template (`06-audit-data-flow.md`) describes a Google-Sheets→Telegram pipeline. The actual project (`mko_vkideo`) is a VK video downloader. See DF-009 for the template mismatch.

---

## Findings

### DF-001: BROWSER cookie mode silently drops the user-selected quality

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** When `--cookie-source browser` is used, `perform_download()` re-extracts the stream via the browser and overwrites the chosen m3u8 URL with `browser_streams[0].url`. The browser extraction path (`VKVideoExtractor._extract_with_browser`) builds **only one** Stream with `quality="best"` (extractor.py:226-234), so `browser_streams[0]` is always the "best" quality playlist. The previously quality-selected `selected_stream` is discarded for the FFMPEG method and for the yt-dlp→segment resume path, so the downloaded file contains a different quality than requested while the output filename is still built from the requested quality.

**Evidence:**
- `downloader.py:524-526` (YTDLP+BROWSER): `m3u8_url = str(browser_streams[0].url)` replaces the selected URL
- `downloader.py:536-538` (FFMPEG+BROWSER): same URL overwrite pattern
- `extractor.py:226-234`: single Stream appended with `quality="best"`, so `streams[0]` is always "best" regardless of the user's `--quality`
- For pure YTDLP method: the override uses yt-dlp's format filter (line 369: `"format": f"best[height<={quality_str}]"`), which works correctly, but FFMPEG path and yt-dlp→segment resume fallback lose quality selection

**Recommendation:** Do not discard the selected stream when fetching browser cookies. Capture only the cookies/header from `_extract_with_browser` (or re-select from the returned streams by quality) and keep the URL of the originally selected `selected_stream`.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified in code. Lines 524-526, 536-538 show m3u8_url overwrite. Lines 226-234 show only one "best" stream created in browser extraction. This is a real bug affecting FFMPEG and resume fallback paths.

---

### DF-002: `--method auto` ignores `--cookie-source browser`

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** The AUTO branch calls `download_with_ytdlp_with_resume_fallback(...)` without passing the `cookies` argument, unlike the explicit YTDLP and FFMPEG branches which first call `extract_streams_with_cookies()` when `cookie_source == BROWSER`. As a result, with `--cookie-source browser --method auto` the primary yt-dlp download runs without the cookies.

**Evidence:** `downloader.py:561-565` (AUTO case) omits `cookies=`; contrast with `downloader.py:530-532` and `downloader.py:543` which pass `cookies=cookies` after browser extraction.

**Recommendation:** Make cookie acquisition uniform across all three method branches.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified. The AUTO case at lines 561-565 does not pass cookies, while YTDLP (lines 530-532) and FFMPEG (line 543) do. This is a real inconsistency.

---

### DF-003: Segment "resume" is defeated by unconditional cleanup of partial progress

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `download_hls_with_resume()` advertises segment-level resume, but its `finally` block deletes the entire `segments_dir` and `metadata_file` whenever the function exits without success. Because every failed run erases on-disk progress, there is never any partial state to resume on the next invocation. Additionally, `downloaded_count` is recomputed as `_load_downloaded_count(metadata_file) + sum(results)` and `_save_downloaded_count` runs only *after* all tasks complete; a crash before that point loses everything.

**Evidence:**
- `segment_downloader.py:324`: only returns result when `downloaded_count == len(segments)`; otherwise returns `None`
- `segment_downloader.py:332-336`: `finally: if segments_dir.exists(): _cleanup_segments(...)` unconditionally removes segments + metadata on every non-success exit
- `segment_downloader.py:309-312`: `_save_downloaded_count` only called after `asyncio.gather` completes

**Recommendation:** Only clean up segments on successful completion. On failure, preserve already-downloaded segments and correct progress count.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified. Lines 332-336 show unconditional cleanup in finally block. Line 309 shows `downloaded_count` is saved only after all segments complete. This defeats resume functionality.

---

### DF-004: Partial/corrupt segment files are treated as complete on resume

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | mandatory |

**Description:** A previously downloaded segment is reused if `segment_path.exists()` is true, with no check that the file is complete or non-empty. If a prior run crashed mid-write, a truncated `.ts` remains on disk and is silently reused. Additionally, `_merge_segments_batched()` silently skips any batch where a segment file is missing, yielding a truncated output without error.

**Evidence:**
- `segment_downloader.py:261` (line 260 in actual file): `if not segment_path.exists()` check, but no validation of file integrity when file exists (line 272: `else: result = True`)
- `ffmpeg_utils.py:254-256`: `if not all(f.exists() for f in batch_files): continue` — missing segments cause the batch to be dropped silently

**Recommendation:** Validate each segment's integrity (non-zero size, or checksum verification). In the merge step, fail loudly instead of silently skipping.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified. Line 272 shows `result = True` when file exists without integrity check. Lines 254-256 in ffmpeg_utils.py show silent `continue` on missing batch files. Real bug causing corrupt output.

---

### DF-005: `Stream.url` typed as `HttpUrl` can mangle signed CDN URLs

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/video.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `Stream.url` is declared as Pydantic `HttpUrl`. Pydantic v2 `HttpUrl` performs percent-encoding normalization and host/query canonicalization on construction. VK m3u8 and segment URLs carry signed query tokens; normalization can alter these tokens and cause 403/410 responses.

**Evidence:** `models/video.py:23` (`url: HttpUrl`); `extractor.py:174` and `extractor.py:228` construct `Stream(url=HttpUrl(...))`; `downloader.py:508` and `segment_downloader.py:231-259` consume `str(stream.url)`.

**Recommendation:** Store stream URLs as `str` to avoid silent canonicalization of signed URLs.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified. `HttpUrl` is used at models/video.py:23 and extractor.py:174, 228. While Pydantic HttpUrl may normalize URLs, this is an advisory improvement with moderate risk for signed URLs. Valid concern but lower operational value than critical bugs.

---

### DF-006: `--cookie-source file` is a non-functional placeholder

| Field | Value |
|-------|-------|
| **ID** | DF-006 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** The `CookieSource.FILE` enum value is accepted by the CLI and config, but `extract_streams_with_cookies()` only contains a "Future: Load cookies from file" comment and returns `(streams, None)` — no cookies are ever loaded or used.

**Evidence:** `extractor.py:124-131`: the FILE branch has the placeholder comment and returns `streams, None`; no file-reading implementation exists anywhere in the codebase.

**Recommendation:** Raise `NotImplementedError` in `extractor.py:extract_streams_with_cookies()` when `cookie_source == CookieSource.FILE`. Add the following check after line 123: `if self.settings.cookie_source == CookieSource.FILE: raise NotImplementedError("Cookie file loading is not implemented. Use --cookie-source browser for authenticated downloads or --cookie-source none to skip authentication.")` This fails fast with a clear message instead of silently ignoring user intent.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified. Lines 124-131 show the placeholder implementation. CookieSource.FILE is defined in enums.py (line 60) and exposed in config.py (line 79), but extractor.py ignores it. Users get misleading behavior.

---

### DF-007: Stale `docs/STRUCT.md` and orphaned infrastructure modules

| Field | Value |
|-------|-------|
| **ID** | DF-007 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/STRUCT.md`, `src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/infrastructure/adaptive_throttle.py` |
| **Classification** | advisory |

**Description:** `docs/STRUCT.md` does not list `services/ffmpeg_utils.py` or `services/segment_downloader.py`, both of which exist and are central. Conversely, `infrastructure/http_client.py` (`HttpClient`) and `infrastructure/adaptive_throttle.py` (`AdaptiveThrottle`) are exported from `infrastructure/__init__.py` and listed in the docs but are never referenced by any service.

**Evidence:**
- `docs/STRUCT.md` lines 37-43 list only `downloader.py`, `downloader_throttle.py`, `extractor.py`, `quality.py` — missing `ffmpeg_utils.py` and `segment_downloader.py`
- `infrastructure/__init__.py` exports both `HttpClient` and `AdaptiveThrottle`
- Grep for `HttpClient` and `AdaptiveThrottle` outside their defining modules returns only the `__init__.py` exports — verified orphaned

**Recommendation:** Update `STRUCT.md` to reflect the real module tree. Investigate whether `HttpClient`/`AdaptiveThrottle` are intended to be wired in.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified. STRUCT.md is outdated (missing ffmpeg_utils.py, segment_downloader.py). HttpClient and AdaptiveThrottle are exported but unused. This is correctly classified as DOC-UPDATE.

---

### DF-008: Deprecated `asyncio.get_event_loop()` in running coroutine

| Field | Value |
|-------|-------|
| **ID** | DF-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `_extract_with_ytdlp` calls `asyncio.get_event_loop()` inside a coroutine. The deprecated API can emit `DeprecationWarning` and would not return the running loop reliably in some configurations.

**Evidence:** `extractor.py:194`: `loop = asyncio.get_event_loop()`.

**Recommendation:** Replace with `asyncio.get_running_loop()` for correctness.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified at line 194. However, this is already fixed at line 400 in downloader.py (`loop = asyncio.get_running_loop()`), showing the correct pattern exists in the codebase. Valid best-practice improvement.

---

### DF-009: Audit phase template does not match the project under audit

| Field | Value |
|-------|-------|
| **ID** | DF-009 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.kilo/commands/audit/phases/06-audit-data-flow.md` |
| **Classification** | advisory |

**Description:** The phase template describes a Google-Sheets→Telegram pipeline that does not exist in mko_vkideo. The real pipeline is a VK video downloader.

**Evidence:** `06-audit-data-flow.md` describes `GSheetsReader`, `TelegramPoster`, etc.; repository contains only `vkdownloader` (CLI + extractor + downloader services).

**Recommendation:** Rewrite the phase to describe the real pipeline.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified. The phase template is for a different project. Correctly classified as DOC-UPDATE.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 9 | All findings verified |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

None. All findings were verified and validated.

### Merged Findings

None. No findings share the same root cause.

### Reclassified Findings

None. All classifications were appropriate.

---

## Rollout Safety Analysis

### Dependency Chain Observations

1. **DF-001 and DF-002 are coupled** — Both involve cookie handling in `perform_download()`. Fixing either requires understanding the shared cookie acquisition logic.

2. **DF-003 and DF-004 interact** — The cleanup issue (DF-003) and corruption issue (DF-004) both affect the same `download_hls_with_resume` function and segment lifecycle.

### Sequencing Concerns

1. **High severity fixes (DF-001, DF-003) should be addressed first** — These cause data integrity loss and user-facing correctness issues.

2. **DF-006 is blocking for FFMPEG/BROWSER users** — Without cookie loading, authenticated downloads via browser are partially supported.

3. **DF-005 is lower risk** — URL normalization may not cause issues in practice; validate with real VK URLs before prioritizing.

---

## Warnings

- **Orphaned code risk:** `HttpClient` and `AdaptiveThrottle` exist but are unused. Consider removing to reduce maintenance surface, or integrating to centralize HTTP/retries.
- **Template drift:** The audit phase template being mismatched indicates potential for future audit phases to target wrong components. Address DF-009 to prevent recurring issues.