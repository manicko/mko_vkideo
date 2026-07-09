---
name: 05-integrations
description: Phase 05 Audit Findings — External Integrations (Validated)
agent: validator
alwaysApply: false
---

# Phase 05 Audit Findings — External Integrations (Validated)

**Executor:** validator  
**Source:** `.ai/audit/05-integrations/findings.md`  
**Base:** Phase 05 Audit  
**Status:** complete  
**Validated:** yes

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

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates CFG-005 (Phase 02), SRV-009 (Phase 03), and SEC-003 (Phase 04). The same async return type issue is documented across all phases. The function is exported in `__init__.py` and has dedicated tests, but is never used by `BrowserManager` (which uses `self.browser.new_context()` instead). The tests pass because they mock with `MagicMock` which doesn't enforce async behavior. This represents a single root cause: the function should be removed as unused code or properly converted to async.

**Merged Into:** See CFG-005 (Phase 02) for consolidated analysis.

---

### INT-002: Cookie type mismatch between Playwright API and _format_cookies_for_ffmpeg

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src\vkdownloader\services\extractor.py` |
| **Classification** | mandatory |

**Description:** The `_format_cookies_for_ffmpeg` method at line 186 expects `list[dict]` but `page.context.cookies()` at line 167 returns `list[Cookie]` - Playwright's typed Cookie objects. This type mismatch will cause mypy type checking failures.

**Evidence:**
- Line 167: `cookies = await page.context.cookies()` returns `list[Cookie]` from Playwright
- Line 168: `cookies_str = self._format_cookies_for_ffmpeg(cookies)` - calls with wrong type
- Line 186: `def _format_cookies_for_ffmpeg(self, cookies: list[dict]) -> str:` - accepts `list[dict]` but receives `list[Cookie]`
- mypy error: `"src\vkdownloader\services\extractor.py:168: error: Argument 1 to "_format_cookies_for_ffmpeg" has incompatible type "list[Cookie]"; expected "list[dict[Any, Any]]"`

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** Per verification, Playwright's `Cookie` is a TypedDict subclass that inherits from `dict`, so the `.get()` method works at runtime. However, mypy correctly identifies this as a type safety violation. This is covered in CFG-004 (Phase 02) which consolidates all type annotation issues.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

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
- Line 71: `"Function is missing a type annotation for one or more parameters"` (extractor parameter)
- Line 148: `"Function is missing a type annotation for one or more parameters"` (_fetch_playlist_with_retry)
- Line 151: `"Missing type arguments for generic type "dict"` (headers parameter)

**Recommendation:** Add explicit type annotations: `headers: dict[str, str] = {...}`. Effort: small.

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates CFG-004 (Phase 02), SRV-006 (Phase 03), and CLI-005 (Phase 01). All cover the same type annotation issues across downloader.py.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

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
- mypy error: `"src\vkdownloader\services\downloader.py:301: error: Returning Any from function declared to return "int"``

**Recommendation:** Add explicit type cast or validation: `return int(data.get("downloaded_count", 0))`. Effort: trivial.

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates CFG-004 (Phase 02), SRV-008 (Phase 03), and CLI-005 (Phase 01). All cover the same type safety issue in downloader.py.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

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

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates CFG-004 (Phase 02), SRV-005 (Phase 03), and CLI-006 (Phase 01). All cover the same code quality issue in extractor.py.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

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

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates CFG-004 (Phase 02), SRV-004 (Phase 03), and CLI-006 (Phase 01). All cover the same code quality issue.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

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

**Evidence:** ruff error: `"F811 Redefinition of unused TestHLSDownloaderDownload from line 97"`. The second class (lines 166-224) duplicates the first (lines 97-164) with identical test methods.

**Recommendation:** Remove the duplicate class definition (lines 166-224) since it duplicates tests already defined in lines 97-164. Effort: small.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** This finding is unique to Phase 05 and represents a real code quality issue that hasn't been addressed. The duplicate class definition causes ruff F811 errors and duplicate test discovery. Lines 166-224 are a duplicate of lines 97-164 with no additional test coverage.

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

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates CFG-004 (Phase 02), SRV-007 (Phase 03), and CLI-005 (Phase 01). All cover the same type annotation issue.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 1 | INT-007 |
| Merged | 7 | INT-001 → CFG-005, INT-002 → CFG-004, INT-003 → CFG-004, INT-004 → CFG-004, INT-005 → CFG-004, INT-006 → CFG-004, INT-008 → CFG-004 |
| Rejected | 0 | — |
| Reclassified | 0 | — |

---

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| INT-001 | CFG-005 (Phase 02) | Duplicate create_stealth_context async return type issue (also covered in SRV-009, SEC-003) |
| INT-002 | CFG-004 (Phase 02) | Duplicate cookie type mismatch issue (SRV-003, CLI-005) |
| INT-003 | CFG-004 (Phase 02) | Duplicate missing type annotation for extractor parameter (SRV-006, CLI-005) |
| INT-004 | CFG-004 (Phase 02) | Duplicate Any return type issue (SRV-008, CLI-005) |
| INT-005 | CFG-004 (Phase 02) | Duplicate unused variable issue (SRV-005, CLI-006) |
| INT-006 | CFG-004 (Phase 02) | Duplicate unused import issue (SRV-004, CLI-006) |
| INT-008 | CFG-004 (Phase 02) | Duplicate missing type arguments for generic dict (SRV-007, CLI-005) |

---

### Cross-Phase Conflicts

None detected. All duplicate findings (INT-001 through INT-006, INT-008) are consistent with validated findings in earlier phases:
- INT-001 = CFG-005 (Phase 02), SRV-009 (Phase 03), SEC-003 (Phase 04)
- INT-002 = CFG-004 (Phase 02), SRV-003 (Phase 03)
- INT-003 = CFG-004 (Phase 02), SRV-006 (Phase 03), CLI-005 (Phase 01)
- INT-004 = CFG-004 (Phase 02), SRV-008 (Phase 03), CLI-005 (Phase 01)
- INT-005 = CFG-004 (Phase 02), SRV-005 (Phase 03), CLI-006 (Phase 01)
- INT-006 = CFG-004 (Phase 02), SRV-004 (Phase 03), CLI-006 (Phase 01)
- INT-008 = CFG-004 (Phase 02), SRV-007 (Phase 03), CLI-005 (Phase 01)

---

## Warnings

- **Type Safety Risk:** All type annotation issues (INT-001, INT-002, INT-003, INT-004, INT-008) violate project rule #9 (Type Safety Everywhere) and are consolidated under CFG-004 (Phase 02).
- **Test Quality Risk:** The duplicate test class (INT-007) creates confusion during test maintenance and may cause inconsistent test runs.
- **Cross-cutting Concern:** The `create_stealth_context` function issues span multiple audit phases but represent a single root cause: an unused function with incorrect async signature that should be removed.

---

## Required Fixes (from Validated Findings)

- INT-007: Remove duplicate `TestHLSDownloaderDownload` class definition (lines 166-224 in test_hls_downloader.py)
- All other type annotation issues are consolidated under CFG-004 and CFG-005 in Phase 02. See those validated findings for complete details.
