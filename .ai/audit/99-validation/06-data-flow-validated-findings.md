---
name: 06-data-flow
description: Phase 06 Audit Findings — End-to-End Data Flow (Validated)
agent: validator
alwaysApply: false
---

# Phase 06 Audit Findings — End-to-End Data Flow (Validated)

**Executor:** validator  
**Source:** `.ai/audit/06-data-flow/findings.md`  
**Base:** Phase 06 Audit  
**Status:** complete  
**Validated:** yes

---

## Findings

### DF-001: Redundant video_id parsing in main entry point

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | main.py |
| **Classification** | advisory |

**Description:** In `main.py` line 41, `extractor.parse_video_id(url)` is called twice consecutively - once to extract the video_id and once again immediately after. This is inefficient and creates unnecessary overhead.

**Evidence:** `main.py:41`: `video_id = extractor.parse_video_id(url)[0] + "_" + extractor.parse_video_id(url)[1]`

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. The function `parse_video_id` is called twice with the same URL, which is inefficient. Both calls execute the same regex search and validation logic. The recommendation is technically sound and effort is trivial.

**Recommendation:** Store the result of `parse_video_id(url)` in a variable and use it twice. Effort: trivial.

---

### DF-002: Config settings not propagated from Settings to download_video

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | main.py |
| **Classification** | advisory |

**Description:** The `download_video` function in `main.py` ignores several Settings parameters that are defined but not used. Specifically, `download_dir` defaults to Path(".") in the function signature (line 23) instead of using `settings.download_dir`, and `max_concurrent_downloads` from settings is not used in the async flow control.

**Evidence:** `main.py:23` function signature has `output_dir: Path = Path(".")` but Settings has `download_dir: Path` field at lines 73-76 in config.py. The settings object `Settings()` is created at line 38 but `download_dir` is never referenced.

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. `Settings.download_dir` exists (default: `~/Downloads/vkdownloader`) but `download_video` uses `Path(".")` as default instead. This is a SPEC-DEVIATION because the code should use the configured settings value.

**Recommendation:** Use `settings.download_dir` as the default output directory. Effort: trivial.

---

### DF-003: Unused import in extractor module

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** The `typing.Any` import at line 5 is unused in the extractor module.

**Evidence:** `src/vkdownloader/services/extractor.py:5` - `from typing import Any` - mypy and ruff both report this as unused.

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. The import `from typing import Any` at line 5 is unused. ruff F401 and mypy would report this. Recommendation is technically sound.

**Recommendation:** Remove the unused import. Effort: trivial.

---

### DF-004: Unused variable in cookie formatting

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** In `_format_cookies_for_ffmpeg` method, the `domain` variable is extracted from cookies but never used.

**Evidence:** `src/vkdownloader/services/extractor.py:192` - `domain = cookie.get("domain", "")` is assigned but never referenced.

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. The `domain` variable at line 192 is extracted but never used. The comment on line 193 indicates "Include all cookies - they may be needed for CDN authentication", suggesting the domain variable may be leftover from incomplete filter logic.

**Recommendation:** Remove the unused variable assignment or use it to filter/include cookies based on domain. Effort: trivial.

---

### DF-005: Missing file newline at end of files

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | main.py, src/vkdownloader/services/downloader.py, src/vkdownloader/services/extractor.py, src/vkdownloader/services/quality.py, tests/integration/__init__.py |
| **Classification** | advisory |

**Description:** Multiple files are missing trailing newlines, which causes ruff format check failures.

**Evidence:** ruff check reports W292 errors:
- main.py:240
- downloader.py:319
- extractor.py:281
- quality.py:77
- tests/integration/__init__.py:1

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. ruff check confirms W292 errors at all listed file locations. These are trivial fixes that improve code quality.

**Recommendation:** Add trailing newline to each affected file. Effort: trivial.

---

### DF-006: Duplicate test class definition

| Field | Value |
|-------|-------|
| **ID** | DF-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_hls_downloader.py |
| **Classification** | advisory |

**Description:** `TestHLSDownloaderDownload` class is defined twice at lines 97 and 166, causing ruff F811 error.

**Evidence:** ruff check reports `tests/test_hls_downloader.py:166:7: F811 Redefinition of unused "TestHLSDownloaderDownload" from line 97`

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. The class `TestHLSDownloaderDownload` appears at lines 97 and 166. Lines 166-224 are a duplicate of lines 97-164 with identical test methods (`test_download_with_ffmpeg_success`, `test_error_handling_ffmpeg_failure`, `test_ffmpeg_command_contains_expected_elements`, `test_ffmpeg_command_output_path`). This causes test discovery issues and duplicate test execution.
> - **Cross-reference:** This same finding was validated as INT-007 in Phase 05, confirming consistency across audit phases.

**Recommendation:** Remove the duplicate class definition (lines 166-224). Effort: trivial.

---

### DF-007: Missing type annotations in downloader functions

| Field | Value |
|-------|-------|
| **ID** | DF-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Several functions in downloader.py lack proper type annotations for parameters, violating the project's type safety requirements.

**Evidence:** mypy reports:
- Line 71: Function `download_hls_with_resume` missing type annotation for parameters `extractor` and `settings`
- Line 148: Function `_fetch_playlist_with_retry` missing type annotation for `headers` parameter
- Line 151, 192: Missing type arguments for generic type "dict"

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. mypy confirms:
>   - Line 77: `extractor=None` lacks type annotation (should be `VKVideoExtractor | None`)
>   - Line 151: `headers: dict` should be `headers: dict[str, str]`
>   - Line 192: `headers: dict` should be `headers: dict[str, str]`
> This violates project rule #9 (Type Safety Everywhere).

**Recommendation:** Add proper type annotations to all function parameters. Effort: small.

---

### DF-008: Incorrect return type annotation in browser.py

| Field | Value |
|-------|-------|
| **ID** | DF-008 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/infrastructure/browser.py |
| **Classification** | advisory |

**Description:** The `create_stealth_context` function at line 13 is declared as a synchronous function but returns a `BrowserContext` which is actually a coroutine, causing mypy error.

**Evidence:** mypy reports `src\vkdownloader\infrastructure\browser.py:29: error: Incompatible return value type (got "Coroutine[Any, Any, BrowserContext]", expected "BrowserContext") [return-value]`

**Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-001 (Phase 05), CFG-005 (Phase 02), SRV-009 (Phase 03), and SEC-003 (Phase 04). The function is exported in `__init__.py` and has dedicated tests in `test_browser_infrastructure.py`, but is never used by `BrowserManager` (which uses `self.browser.new_context()` instead). Per cross-phase analysis, this is a consolidated issue.

**Merged Into:** See CFG-005 (Phase 02) for consolidated analysis.

---

### DF-009: Print statements used instead of structured logging

| Field | Value |
|-------|-------|
| **ID** | DF-009 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | main.py |
| **Classification** | advisory |

**Description:** Multiple `print()` statements are used in main.py (lines 49, 52, 137, 155, 206, 217, 226, 233, 235) instead of structured logging as required by project rules.

**Evidence:** Project rules require `logger = logging.getLogger(__name__)` and prohibit print() statements. The code uses `print(f"Available streams: {len(streams)}")` and similar statements throughout.

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. `main.py` contains multiple `print()` statements:
>   - Line 49: `print(f"Available streams: {len(streams)}")`
>   - Line 52: `print(f"Qualities: {', '.join(available[:8])}")`
>   - Line 137: `print(f"Download interrupted. Switching to segment-based resume ({retry_count}/{MAX_RESUME_RETRIES})...")`
>   - Line 155: `print(f"Failed to download after {MAX_RESUME_RETRIES} attempts. Stopping.", file=sys.stderr)`
>   - Lines 206, 217, 226, 233, 235 in `main()` function
>   This violates project rule #12 (No `print()` Statements). A `logger` instance already exists at line 14 using `get_logger(__name__)`.

**Recommendation:** Replace all `print()` calls with structured logging using the existing `logger` instance. Effort: small.

---

### DF-010: Segment download cleanup does not handle partial completion

| Field | Value |
|-------|-------|
| **ID** | DF-010 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** In `download_hls_with_resume` function, when segment download fails mid-way (line 132 returns None), the partially downloaded segments are not cleaned up. This leaves orphaned segment files and progress metadata on the filesystem.

**Evidence:** `src/vkdownloader/services/downloader.py:123-135` - When `_download_segment` returns False, the function returns None without calling `_cleanup_segments`. Partial segment files remain on disk.

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. In `download_hls_with_resume` (lines 71-145), when `_download_segment` returns False at line 132, the function returns None immediately without cleanup. Partial segment files in `{output_file.stem}_segments/` and progress metadata `{output_file.stem}_progress.json` will remain on disk. This creates orphaned files that may confuse users and consume disk space.

**Recommendation:** Wrap `download_hls_with_resume` in try/finally to ensure cleanup on partial completion:
```python
async def download_hls_with_resume(...):
    try:
        # existing download logic
        result = await _fetch_playlist_with_retry(...)
        # segment download and merge
        return output_file
    finally:
        # Only preserve progress file if intentional resume planned
        # Clean up partial segments if download failed
        if not download_completed and segments_dir.exists():
            _cleanup_segments(segments_dir, output_file.stem)
```
Add early cleanup in error paths (lines 132, 143). This prevents orphaned `.ts` files and progress metadata on failure. Effort: small. Priority: mandatory.

---

### DF-011: Settings concurrency parameters unused in batch download

| Field | Value |
|-------|-------|
| **ID** | DF-011 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** In `batch_download` command, the semaphore is initialized with `Settings().max_concurrent_downloads` (line 138) but creates a new Settings instance instead of using the configured settings, and ignores `request_delay_min/max` for rate limiting.

**Evidence:** `src/vkdownloader/cli.py:138` - `semaphore = asyncio.Semaphore(Settings().max_concurrent_downloads)` creates a fresh Settings instance rather than using the application's configured settings. The throttle classes (`AdaptiveThrottle`) exist but are never used in the batch flow.

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified. Line 138 creates a new `Settings()` instance inside `_run_batch_with_progress()` instead of reusing one. The `request_delay_min` and `request_delay_max` settings exist in config.py (lines 43-52) but are never referenced in cli.py. This represents missed opportunity for proper rate limiting.

**Recommendation:** Create `Settings()` once at the start of `batch_download` command and pass it to `_run_batch_with_progress()`. Instantiate `AdaptiveThrottle` with `base_rpm=settings.max_concurrent_downloads` and call `throttle.wait()` before each download request with `on_success()` / `on_rate_limited()` callbacks. However, per CFG-005 resolution, `AdaptiveThrottle` is dead code and should be removed. For immediate fix, create Settings once and reuse it:
```python
@app.command()
def batch(...):
    settings = Settings()  # Create once
    ...
    semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)  # Reuse
```
Effort: small. Priority: advisory.

---

### DF-012: m3u8 URL passed to extractor instead of video URL during token refresh

| Field | Value |
|-------|-------|
| **ID** | DF-012 |
| **Severity** | CRITICAL |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |

**Description:** In `_fetch_playlist_with_retry` at line 166, when a 403/410 response is received during segment download, the code calls `extractor.extract_streams_with_cookies(m3u8_url)` passing an m3u8 playlist URL instead of the original VK video page URL. The `extract_streams_with_cookies` method expects a VK video page URL (validated by `parse_video_id` which matches pattern `video-(-?\d+)_(\d+)`), not a direct m3u8 URL.

**Evidence:** `src/vkdownloader/services/downloader.py:166` calls `extractor.extract_streams_with_cookies(m3u8_url)` where `m3u8_url` is a URL like `https://example.com/video.m3u8`, but `extract_streams_with_cookies` at `extractor.py:95` calls `parse_video_id(url)` which requires the URL to match `video-(-?\d+)_(\d+)` pattern. This will raise `ValueError: Invalid VK video URL` when token refresh is triggered during download resume.

**Validation Note:**
> - **Action:** Validated
> - **Detail:** The evidence is verified and represents a critical architectural defect. At `downloader.py:166`:
>   ```python
>   streams, new_cookies = await extractor.extract_streams_with_cookies(m3u8_url)
>   ```
>   This passes `m3u8_url` (e.g., `https://vkvd3259-103865-prod_vkvideo_ru/video.m3u8?token=...`) to `extract_streams_with_cookies`, which at line 95 calls `parse_video_id(url)` with `VIDEO_ID_PATTERN = re.compile(r"video-(-?\d+)_(\d+)")`. An m3u8 URL does not contain this pattern, so a `ValueError` will be raised.
>   
>   However, the original `video_url` IS available in some call paths:
>   - `download_with_ytdlp_with_resume_fallback` receives `video_url` (line 90) and passes it to `extractor.extract_streams_with_cookies(video_url)` at line 141 - this is CORRECT
>   - But `download_hls_with_resume` only receives `m3u8_url` and does NOT have access to the original `video_url`
>   
>   This is a genuine architectural gap that requires passing the original video URL through the call chain.

**Recommendation:** The `download_hls_with_resume` function needs to accept the original video URL as a parameter and pass it to `_fetch_playlist_with_retry`, which then passes it to the extractor. The current function signature only accepts `m3u8_url` which is insufficient for token refresh. Effort: small.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 11 | DF-001, DF-002, DF-003, DF-004, DF-005, DF-006, DF-007, DF-009, DF-010, DF-011, DF-012 |
| Merged | 1 | DF-008 → CFG-005 (Phase 02) |
| Rejected | 0 | — |
| Reclassified | 0 | — |

---

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| DF-008 | CFG-005 (Phase 02) | Duplicate create_stealth_context async return type issue (also covered in INT-001, SRV-009, SEC-003) |

---

### Cross-Phase Conflicts

None detected. All findings are consistent with validated findings in Phase 05 (INT-001-INT-008) and earlier phases. The `create_stealth_context` function issues span multiple audit phases but represent a single root cause that has been consolidated.

---

## Warnings

- **Type Safety Risk:** DF-007 and DF-008 violations of project rule #9 (Type Safety Everywhere) should be fixed.
- **Resource Leak Risk:** DF-010 (segment cleanup on failure) can leave orphaned files on disk.
- **Runtime Error Risk:** DF-012 (incorrect URL passed for token refresh) will cause crashes during resume operations when 403/410 responses are received.
- **Print Statement Risk:** DF-009 violates project rule #12 and reduces observability in production.

---

## Required Fixes (from Validated Findings)

- **DF-012 (CRITICAL):** m3u8 URL passed to extractor expecting video URL - will cause crash on token refresh. Must be fixed.
- **DF-010 (HIGH):** Add cleanup for partial segment downloads on failure to prevent orphaned files.
- **DF-011 (MEDIUM):** Use configured settings and throttle in batch download; create Settings once instead of per-call.

---

## Advisory Recommendations (Validated)

- **DF-001:** Remove redundant video_id parsing in main.py
- **DF-002:** Use settings.download_dir as default output directory
- **DF-003:** Remove unused typing.Any import
- **DF-004:** Remove unused domain variable or use it for filtering
- **DF-005:** Add trailing newlines to files
- **DF-006:** Remove duplicate TestHLSDownloaderDownload class definition
- **DF-007:** Add missing type annotations in downloader.py
- **DF-009:** Replace print() with structured logging