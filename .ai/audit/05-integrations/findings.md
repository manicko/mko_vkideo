---
name: 05-integrations-audit
description: External Integrations Audit Findings - Playwright, ffmpeg, yt-dlp, HTTP client
agent: auditor
status: complete
validated: no
---

# Phase 05 Audit Findings — External Integrations

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### INT-001: create_stealth_context returns coroutine but declared as sync function

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src\vkdownloader\infrastructure\browser.py` |
| **Classification** | mandatory |

**Description:** The `create_stealth_context` function at line 13 is declared to return `BrowserContext` synchronously, but `launch_persistent_context` is an async coroutine. This mismatch will cause a runtime error when the function is called - the returned coroutine object will not be an actual BrowserContext, and attempting to use it as such will fail.

**Evidence:** 
- Line 13: `def create_stealth_context(...)` - declared as synchronous function
- Line 29: `return playwright.chromium.launch_persistent_context(...)` - calls async method without await
- mypy error: `"src\vkdownloader\infrastructure\browser.py:29: error: Incompatible return value type (got "Coroutine[Any, Any, BrowserContext]", expected "BrowserContext")"`

**Recommendation:** Add `async` to the function definition and `await` to the return statement. The function should be `async def create_stealth_context(...)` and return `await playwright.chromium.launch_persistent_context(...)`. Effort: small.

---

### INT-002: Cookie type mismatch between Playwright API and _format_cookies_for_ffmpeg

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src\vkdownloader\services\extractor.py` |
| **Classification** | mandatory |

**Description:** The `_format_cookies_for_ffmpeg` method at line 186 expects `list[dict[Any, Any]]` but `page.context.cookies()` at line 167 returns `list[Cookie]` - Playwright's typed Cookie objects. This type mismatch will cause runtime attribute errors since Cookie objects have a different interface than dicts.

**Evidence:**
- Line 167: `cookies = await page.context.cookies()` returns `list[Cookie]` from Playwright
- Line 168: `cookies_str = self._format_cookies_for_ffmpeg(cookies)` - calls with wrong type
- Line 186-195: Method expects dict-like access but Cookie objects may have different attribute access patterns
- mypy error: `"src\vkdownloader\services\extractor.py:168: error: Argument 1 to "_format_cookies_for_ffmpeg" has incompatible type "list[Cookie]"; expected "list[dict[Any, Any]]"`

**Recommendation:** Update the type annotation to use the correct Playwright Cookie type, or import and use `playwright.async_api.Cookie` for proper typing. Effort: small.

---

### INT-003: Missing type annotations in download_hls_with_resume

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The `download_hls_with_resume` function at line 71 is missing type annotation for the `headers` local variable (line 106). Under strict mypy mode, this causes type checking failures and reduces code maintainability.

**Evidence:** mypy errors:
- Line 71: `"Function is missing a type annotation for one or more parameters"`
- Line 148: `"Function is missing a type annotation for one or more parameters"`
- Line 151: `"Missing type arguments for generic type "dict"`

**Recommendation:** Add explicit type annotations: `headers: dict[str, str] = {...}`. Effort: small.

---

### INT-004: Returning Any from _load_downloaded_count declared to return int

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | mandatory |

**Description:** The `_load_downloaded_count` function at line 296 uses `json.load()` which returns `Any`, and returns its value without type validation. If the JSON structure is malformed or contains invalid data, this could return a non-integer value, causing type errors downstream when used for arithmetic operations.

**Evidence:**
- Line 300-301: `data = json.load(f); return data.get("downloaded_count", 0)` - no type check
- mypy error: `"src\vkdownloader\services\downloader.py:301: error: Returning Any from function declared to return "int"`

**Recommendation:** Add explicit type cast or validation: `return int(data.get("downloaded_count", 0))`. Effort: trivial.

---

### INT-005: Unused variable `domain` in _format_cookies_for_ffmpeg

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\extractor.py` |
| **Classification** | advisory |

**Description:** Variable `domain` at line 192 is extracted from cookie but never used. This suggests incomplete cookie domain filtering logic or dead code that should be removed.

**Evidence:** Line 190-194 shows `domain` is assigned but never referenced in the following code. ruff error: `"F841 Local variable domain is assigned to but never used"`.

**Recommendation:** Remove the unused variable assignment to clean up the code and prevent confusion. Effort: trivial.

---

### INT-006: Unused import `Any` in extractor.py

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\extractor.py` |
| **Classification** | advisory |

**Description:** `from typing import Any` at line 5 is imported but never used in the module.

**Evidence:** ruff error: `"F401 typing.Any imported but unused"`.

**Recommendation:** Remove the unused import. Effort: trivial.

---

### INT-007: Duplicate test class TestHLSDownloaderDownload

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests\test_hls_downloader.py` |
| **Classification** | advisory |

**Description:** The test class `TestHLSDownloaderDownload` is defined twice: at lines 97 and 166. This causes test discovery issues and duplicate test execution.

**Evidence:** ruff error: `"F811 Redefinition of unused TestHLSDownloaderDownload from line 97"`. The same class name appears twice with overlapping test methods.

**Recommendation:** Remove the duplicate class definition (lines 166-224) since it duplicates tests already defined in lines 97-164. Effort: small.

---

### INT-008: Missing type arguments for generic dict types

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The functions `_fetch_playlist_with_retry` and `_download_segment` use untyped `dict` instead of parameterized `dict[K, V]` types, causing mypy type checking failures under strict mode.

**Evidence:** mypy errors:
- Line 151: `"Missing type arguments for generic type "dict""`
- Line 192: `"Missing type arguments for generic type "dict""`

**Recommendation:** Add type arguments to dict types: `dict[str, str]` for headers. Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 3 |

## Mandatory Fixes

- INT-001: `create_stealth_context` async return type mismatch
- INT-002: Cookie type mismatch between Playwright API and handler
- INT-004: Returning Any from _load_downloaded_count

## Advisory Recommendations

- INT-003: Missing type annotations in download_hls_with_resume
- INT-005: Unused variable `domain` in _format_cookies_for_ffmpeg
- INT-006: Unused import `Any` in extractor.py
- INT-007: Duplicate test class definition
- INT-008: Missing type arguments for generic dict types

---

## Runtime Verification Results

- **Import Verification:** PASSED - All integration modules import successfully
- **Linter (ruff check):** FAILED - 11 errors found (import order, unused vars, duplicate class)
- **Type Checker (mypy):** FAILED - 8 errors found (async return type mismatch, missing type annotations, type arg errors)
- **Test Suite:** PASSED - 53 tests passed

## Integration Architecture Summary

The project integrates with:
1. **Playwright** (`src\vkdownloader\infrastructure\browser.py`) - Browser automation with stealth configuration
2. **ffmpeg** (`src\vkdownloader\services\downloader.py`) - HLS to MP4 conversion via subprocess
3. **yt-dlp** (`src\vkdownloader\services\extractor.py`) - Video stream extraction
4. **aiohttp** (`src\vkdownloader\infrastructure\http_client.py`) - HTTP requests with retry logic

No Google Sheets or Telegram API integrations exist in this codebase (they were referenced in the generic phase template but are not applicable to this VK video downloader project).