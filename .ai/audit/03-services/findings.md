---
name: audit-findings
description: Service Layer Audit Findings
agent: auditor
status: complete
validated: no
---

# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** no  

---

## Findings

### SRV-001: Dead code - `_parse_m3u8_playlist` method never called

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | LOW |
| **Type** | DEAD-CODE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** The `_parse_m3u8_playlist` method is defined in `VKVideoExtractor` class (lines 218-281) but is never called anywhere in the codebase. It was planned for parsing m3u8 playlists to extract quality variants, but the current implementation uses yt-dlp for stream extraction which already provides parsed quality information.

**Evidence:**
- Definition exists: `src\vkdownloader\services\extractor.py:218`
- No other code references this method (grep search returns only the definition)
- The method imports `HttpClient` internally and duplicates logic that yt-dlp already handles

**Recommendation:** Either remove the unused method or integrate it if m3u8 playlist parsing is needed for future use cases. Effort: trivial (removal) or medium (integration).

---

### SRV-002: Dead code - `AdaptiveThrottle` class exported but never used

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | LOW |
| **Type** | DEAD-CODE |
| **Affected Modules** | src/vkdownloader/infrastructure/adaptive_throttle.py |
| **Classification** | advisory |

**Description:** The `AdaptiveThrottle` class is defined and exported from `infrastructure/__init__.py` but is never imported or used anywhere in the service layer or application code.

**Evidence:**
- Definition: `src\vkdownloader\infrastructure\adaptive_throttle.py:11`
- Export list: `src\vkdownloader\infrastructure\__init__.py:9`
- No usages found outside the module definition

**Recommendation:** Investigate if this rate limiter was intended for future use or remove if unnecessary. Effort: trivial (removal) or medium (integration).

---

### SRV-003: Cookie type incompatibility in `_format_cookies_for_ffmpeg`

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/extractor.py:186 |
| **Classification** | mandatory |

**Description:** The `_format_cookies_for_ffmpeg` method signature accepts `list[dict]` but receives `list[Cookie]` from Playwright's `page.context.cookies()` API. This type mismatch could cause runtime errors if the Cookie type structure differs from dict expectations.

**Evidence:**
- mypy error 1: `src\vkdownloader\services\extractor.py:168: error: Argument 1 to "_format_cookies_for_ffmpeg" has incompatible type "list[Cookie]"; expected "list[dict[Any, Any]]"  [arg-type]`
- mypy error 2: `src\vkdownloader\services\extractor.py:186: error: Missing type arguments for generic type "dict"  [type-arg]`
- Method definition at line 186 declares `list[dict]` but receives Playwright Cookie objects

**Recommendation:** Change signature to `def _format_cookies_for_ffmpeg(self, cookies: list[Any])` to accept Playwright's Cookie type, and remove unused `domain` variable. Effort: trivial.

---

### SRV-004: Unused import `typing.Any` in extractor.py

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/extractor.py:5 |
| **Classification** | advisory |

**Description:** The `typing.Any` import is unused in extractor.py. While not causing runtime errors, this indicates dead code or incomplete refactoring.

**Evidence:**
- ruff error: `F401 [*] 'typing.Any' imported but unused` at line 5
- The import was likely intended for the `_format_cookies_for_ffmpeg` method but proper typing wasn't applied

**Recommendation:** Remove the unused import. Effort: trivial.

---

### SRV-005: Unused variable `domain` in `_format_cookies_for_ffmpeg`

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/extractor.py:192 |
| **Classification** | advisory |

**Description:** Variable `domain` is extracted from cookies but never used, indicating incomplete implementation or dead code.

**Evidence:**
- ruff error: `F841 Local variable 'domain' is assigned to but never used` at line 192
- Code: `domain = cookie.get("domain", "")` followed by no usage of the variable

**Recommendation:** Either use the domain for cookie formatting or remove the unused assignment. Effort: trivial.

---

### SRV-006: Missing type annotation for `extractor` parameter in `download_hls_with_resume`

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/downloader.py:71 |
| **Classification** | advisory |

**Description:** The `download_hls_with_resume` function accepts an `extractor` parameter without type annotation, violating the project's strict type checking requirements.

**Evidence:**
- mypy error: `Function is missing a type annotation for one or more parameters` at line 71
- Signature: `async def download_hls_with_resume(m3u8_url: str, output_file: Path, quality: str = "best", cookies: str | None = None, settings: Settings | None = None, extractor=None) -> Path | None:`
- Parameter `extractor=None` at line 77 has no type annotation

**Recommendation:** Add proper type annotation: `extractor: VKVideoExtractor | None = None`. Effort: trivial.

---

### SRV-007: Missing type arguments for generic `dict` in downloader functions

| Field | Value |
|-------|-------|
| **ID** | SRV-007 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/downloader.py:151,192 |
| **Classification** | advisory |

**Description:** Two functions use bare `dict` type instead of parameterized generic `dict[K, V]`, violating strict mypy configuration.

**Evidence:**
- mypy error: `Missing type arguments for generic type "dict"` at lines 148 and 192
- `_fetch_playlist_with_retry` parameter `headers: dict` at line 151
- `_download_segment` parameter `headers: dict` at line 192

**Recommendation:** Add type arguments: `dict[str, str]` for headers parameters. Effort: trivial.

---

### SRV-008: Returning `Any` from `_load_downloaded_count` function

| Field | Value |
|-------|-------|
| **ID** | SRV-008 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/downloader.py:301 |
| **Classification** | advisory |

**Description:** The `_load_downloaded_count` function returns `Any` from `json.load()` without explicit type conversion, which can cause type safety issues.

**Evidence:**
- mypy error: `Returning Any from function declared to return "int"` at line 301
- Code: `return data.get("downloaded_count", 0)` where `data` comes from `json.load()`

**Recommendation:** Add explicit cast or handle type safely: `return int(data.get("downloaded_count", 0))`. Effort: trivial.

---

### SRV-009: `create_stealth_context` return type mismatch

| Field | Value |
|-------|-------|
| **ID** | SRV-009 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/infrastructure/browser.py:13 |
| **Classification** | mandatory |

**Description:** The `create_stealth_context` function is missing `async` but calls `launch_persistent_context` which is async in Playwright, causing a critical type error.

**Evidence:**
- mypy error: `Incompatible return value type (got "Coroutine[Any, Any, BrowserContext]", expected "BrowserContext")  [return-value]` at line 29
- Function is defined as `def create_stealth_context(...)` but calls `playwright.chromium.launch_persistent_context()` which returns a coroutine

**Recommendation:** Either add `async` keyword to function definition or call with `await`. Given tests expect async behavior, add `async/await`. Effort: trivial.

---

### SRV-010: Missing newlines at end of service files

| Field | Value |
|-------|-------|
| **ID** | SRV-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/extractor.py, src/vkdownloader/services/quality.py |
| **Classification** | advisory |

**Evidence:**
- ruff errors for `W292 [*] No newline at end of file` in all three service files

**Recommendation:** Add trailing newlines to maintain consistent file formatting. Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 6 |

## Mandatory Fixes

- SRV-003: Cookie type incompatibility in `_format_cookies_for_ffmpeg`
- SRV-009: `create_stealth_context` return type mismatch (critical coroutine issue)

## Advisory Recommendations

- SRV-001: Dead code - `_parse_m3u8_playlist` method never called
- SRV-002: Dead code - `AdaptiveThrottle` class exported but never used
- SRV-004: Unused import `typing.Any` in extractor.py
- SRV-005: Unused variable `domain` in `_format_cookies_for_ffmpeg`
- SRV-006: Missing type annotation for `extractor` parameter in `download_hls_with_resume`
- SRV-007: Missing type arguments for generic `dict` in downloader functions
- SRV-008: Returning `Any` from `_load_downloaded_count` function
- SRV-010: Missing newlines at end of service files

## Doc Updates Needed

The audit phase template referenced TelegramService, PostProcessor, ImageCache, TelegramPoster, GSheetsReader, and Task model - these services do not exist in the current codebase. The actual service layer contains: HLSDownloader, VKVideoExtractor, QualitySelector, BrowserManager, HttpClient, NetworkMonitor, and AdaptiveThrottle. The template should be updated to reflect the actual project architecture (VK Video Downloader).