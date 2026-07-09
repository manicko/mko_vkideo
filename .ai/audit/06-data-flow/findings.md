---
name: audit-findings
description: Structured findings for data flow audit
agent: auditor
alwaysApply: false
---

# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

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

**Recommendation:** Store the result of `parse_video_id(url)` in a variable and use it twice. Effort: trivial. The code should be:
```python
owner_id, video_id = extractor.parse_video_id(url)
video_id_full = f"{owner_id}_{video_id}"
```

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

**Evidence:** `main.py:23` function signature has `output_dir: Path = Path(".")` but Settings has `download_dir: Path` field at line 73-76 in config.py. The settings object `Settings()` is created at line 38 but `download_dir` is never referenced.

**Recommendation:** Use `settings.download_dir` as the default output directory. Effort: trivial. This would make the configuration consistent and respect user settings.

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

**Recommendation:** The function should be declared as `async def create_stealth_context(...)` to properly await the coroutine. Effort: trivial.

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

**Recommendation:** Add cleanup in the error path to remove partial segment files when download fails. Consider using try/finally to ensure cleanup. Effort: small.

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

**Recommendation:** Create Settings once at the start of the command and use `AdaptiveThrottle` for rate limiting between requests. Effort: small.

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

**Recommendation:** The `download_hls_with_resume` function needs to accept the original video URL as a parameter and pass it to `_fetch_playlist_with_retry`, which then passes it to the extractor. The current function signature only accepts `m3u8_url` which is insufficient for token refresh. Effort: small.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 2 |
| MEDIUM | 4 |
| LOW | 3 |

## Mandatory Fixes

- DF-012: m3u8 URL passed to extractor expecting video URL (will cause crash on token refresh)

## Advisory Recommendations

- DF-001: Remove redundant video_id parsing in main.py
- DF-002: Use settings.download_dir as default output directory
- DF-003: Remove unused typing.Any import
- DF-004: Remove unused domain variable or use it
- DF-005: Add trailing newlines to files
- DF-006: Remove duplicate test class definition
- DF-007: Add missing type annotations in downloader.py
- DF-008: Fix create_stealth_context to be async
- DF-009: Replace print() with structured logging
- DF-010: Add cleanup for partial segment downloads on failure
- DF-011: Use configured settings and throttle in batch download

---

## Template Field Reference

### Mandatory Fields Per Finding

| Field | Type | Values/Format |
|-------|------|---------------|
| `id` | string | Unique identifier within phase (e.g., `BE-001`) |
| `title` | string | Human-readable one-line summary |
| `type` | enum | `SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, `RUNTIME-ERROR` |
| `severity` | enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `description` | string | Detailed problem description with context |
| `evidence` | string | File paths, line references, code snippets |
| `affected_modules` | list | Affected module paths |
| `recommendation` | string | Concrete fix direction: what to change and why |
| `classification` | enum | `mandatory` or `advisory` |