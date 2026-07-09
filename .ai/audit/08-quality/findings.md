---
name: 08-quality-audit-findings
description: Code Quality, Security & Maintainability findings
agent: auditor
alwaysApply: false
---

# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** no  

---

## Findings

### QLT-001: Forbidden `print()` statements in production code

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | main.py |
| **Classification** | mandatory |

**Description:** The `main.py` file uses `print()` statements for output instead of the required `logger` pattern. This violates project rule #12 which states "No `print()` Statements - Use proper logging: `logger = logging.getLogger(__name__)`". While the code uses `structlog.get_logger(__name__)`, it still outputs user-facing messages via `print()` which bypasses structured logging and makes output harder to configure and control.

**Evidence:**
- main.py:49: `print(f"Available streams: {len(streams)}")`
- main.py:52: `print(f"Qualities: {', '.join(available[:8])}")`
- main.py:137: `print(f"Download interrupted. Switching to segment-based resume ({retry_count}/{MAX_RESUME_RETRIES})...")`
- main.py:155: `print(f"Failed to download after {MAX_RESUME_RETRIES} attempts. Stopping.", file=sys.stderr)`
- main.py:206-209: Multiple print calls for usage/help output
- main.py:217-218: Print calls for validation errors
- main.py:226-227: Print calls for validation errors
- main.py:233: `print(f"Downloaded: {result}")`
- main.py:235: `print("Download failed", file=sys.stderr)`

**Recommendation:** Replace all `print()` calls with `logger.info()` or `logger.error()` calls. For CLI usage/help output, use `typer.echo()` (already imported in cli.py but unused in main.py) or `logger.info()`. This ensures consistent output handling and enables structured logging.

---

### QLT-002: Unused import `typing.Any`

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** The `typing.Any` import at line 5 is unused in the extractor module. Ruff reports this as F401.

**Evidence:**
- ruff output: `F401 [*] 'typing.Any' imported but unused` at src\vkdownloader\services\extractor.py:5:20

**Recommendation:** Remove the unused import `from typing import Any` to clean up the code and avoid confusion.

---

### QLT-003: Unused variable `domain` in cookie formatting

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** Variable `domain` is assigned but never used in the `_format_cookies_for_ffmpeg` method. While the comment indicates cookies may be needed for CDN authentication, the domain value is not utilized.

**Evidence:**
- ruff output: `F841 Local variable 'domain' is assigned to but never used` at src\vkdownloader\services\extractor.py:192:13
- Code: `domain = cookie.get("domain", "")` followed by only using `name` and `value`

**Recommendation:** Remove the unused `domain` variable assignment, or if domain information is intended to be included in the cookie header, add it to the `cookie_parts.append()` call.

---

### QLT-004: Missing type annotation for generic `dict` in type hints

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/extractor.py |
| **Classification** | mandatory |

**Description:** Type hints use `dict` without type arguments, which violates mypy strict mode requirements. This is reported by mypy as `type-arg` error.

**Evidence:**
- mypy output: `src\vkdownloader\services\downloader.py:151: error: Missing type arguments for generic type "dict"`
- mypy output: `src\vkdownloader\services\downloader.py:192: error: Missing type arguments for generic type "dict"`
- mypy output: `src\vkdownloader\services\extractor.py:186: error: Missing type arguments for generic type "dict"`

**Recommendation:** Add type arguments to generic `dict` types, e.g., change `dict` to `dict[str, Any]` or `dict[str, str]` as appropriate. Use `from typing import Any` where needed.

---

### QLT-005: Missing type annotation on function parameter

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |

**Description:** The `download_hls_with_resume` function (line 71) and `_fetch_playlist_with_retry` function (line 148) have parameters without type annotations. The `extractor` parameter at line 77 uses `extractor=None` without a type hint. The `headers` parameter at line 151 lacks type arguments.

**Evidence:**
- mypy output: `src\vkdownloader\services\downloader.py:71: error: Function is missing a type annotation for one or more parameters`
- mypy output: `src\vkdownloader\services\downloader.py:148: error: Function is missing a type annotation for one or more parameters`
- Code at line 77: `extractor=None,` without type hint

**Recommendation:** Add proper type annotations to the `extractor` and `headers` parameters. For `extractor`, use `extractor: VKVideoExtractor | None = None`. For `headers`, use `headers: dict[str, str]`.

---

### QLT-006: Return type annotation returning `Any` where specific type required

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |

**Description:** The `_load_downloaded_count` function returns `Any` from `json.load()` when it should return `int`. This triggers the mypy `no-any-return` check.

**Evidence:**
- mypy output: `src\vkdownloader\services\downloader.py:301: error: Returning Any from function declared to return "int"`
- Code at line 300: `data = json.load(f)` returns `Any`, then `.get()` returns `Any`

**Recommendation:** Add explicit type cast or use `isinstance` check: `return int(data.get("downloaded_count", 0))` or `return data.get("downloaded_count", 0)` with proper type assertion.

---

### QLT-006b: Missing `await` on async function in `create_stealth_context`

| Field | Value |
|-------|-------|
| **ID** | QLT-006b |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/infrastructure/browser.py |
| **Classification** | mandatory |

**Description:** The `create_stealth_context` function (line 13-29) is declared as synchronous but calls `playwright.chromium.launch_persistent_context()` which is an async method. The mypy error indicates the function returns `Coroutine[Any, Any, BrowserContext]` but is typed to return `BrowserContext`. This is a correctness issue - the function needs to be `async` with `await`. The function is exported and tested, but the tests pass because MagicMock doesn't enforce async correctness.

**Evidence:**
- mypy output: `src\vkdownloader\infrastructure\browser.py:29: error: Incompatible return value type (got "Coroutine[Any, Any, BrowserContext]", expected "BrowserContext") [return-value]`
- Code at line 29: `return playwright.chromium.launch_persistent_context(...)` without `await`
- Function is exported in `__init__.py` and used in tests

**Recommendation:** Either make the function `async def create_stealth_context` with `return await playwright.chromium.launch_persistent_context(...)`, or note that this function is dead code (not used in production code) and remove it along with its exports.

---

### QLT-007: Redefinition of test class `TestHLSDownloaderDownload`

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_hls_downloader.py |
| **Classification** | advisory |

**Description:** The test class `TestHLSDownloaderDownload` is defined twice in the same file (lines 97 and 166). This is reported by ruff as F811 (redefinition of unused class).

**Evidence:**
- ruff output: `F811 Redefinition of unused 'TestHLSDownloaderDownload' from line 97`
- test_hls_downloader.py has duplicate class definitions

**Recommendation:** Remove the duplicate class definition at line 166 or consolidate the test methods into a single class.

---

### QLT-008: Missing newlines at end of files

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | main.py, src/vkdownloader/services/downloader.py, src/vkdownloader/services/extractor.py, src/vkdownloader/services/quality.py, tests/integration/__init__.py |
| **Classification** | advisory |

**Description:** Multiple files are missing trailing newlines, which is a code quality issue detected by ruff format checking.

**Evidence:**
- ruff format --check shows 21 files would be reformatted
- ruff check reports W292 on 5 files

**Recommendation:** Add trailing newlines to all affected files to comply with proper file formatting conventions.

---

### QLT-009: Hardcoded User-Agent string duplicated in main.py

| Field | Value |
|-------|-------|
| **ID** | QLT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | main.py |
| **Classification** | advisory |

**Description:** The User-Agent string is hardcoded in `main.py` (line 182) instead of using the `Settings` configuration. This duplicates the value already defined in the Settings class's `user_agent` field.

**Evidence:**
- main.py:182-183: `"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"`

**Recommendation:** Use `settings.user_agent` instead of hardcoding the User-Agent string, ensuring consistency with the Settings configuration.

---

### QLT-010: Unused exception classes in exception hierarchy

| Field | Value |
|-------|-------|
| **ID** | QLT-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/exceptions.py |
| **Classification** | advisory |

**Description:** Exception classes `VideoNotFoundError`, `QualityNotAvailableError`, and `ExtractionError` are defined in the exception hierarchy but never raised or caught in the codebase. Only `DownloadError` is used (imported in http_client.py).

**Evidence:**
- Grep shows only `DownloadError` is imported/used
- Other 3 exception classes have no references in source code outside their definition

**Recommendation:** Either remove unused exception classes or investigate whether they should be used in the appropriate places (e.g., `VideoNotFoundError` when video not found, `ExtractionError` when extraction fails).

---

### QLT-011: Unused `StreamWithCookies` model

| Field | Value |
|-------|-------|
| **ID** | QLT-011 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/models/video.py |
| **Classification** | advisory |

**Description:** The `StreamWithCookies` class is defined in video.py but never used anywhere in the codebase. It extends `Stream` with a cookies field but there are no imports or usages.

**Evidence:**
- Grep shows `StreamWithCookies` is only defined, never imported or used
- Not exported in `__init__.py` and not used in any service

**Recommendation:** Either remove the unused class or export and use it where cookies are associated with streams.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 7 |

## Mandatory Fixes

- QLT-001: Replace `print()` statements with `logger` calls in main.py
- QLT-004: Add type arguments to generic `dict` type hints
- QLT-005: Add missing type annotations to function parameters
- QLT-006: Fix return type annotation to avoid returning `Any`
- QLT-006b: Add `await` to async call in `create_stealth_context` or remove unused function

## Advisory Recommendations

- QLT-002: Remove unused `typing.Any` import
- QLT-003: Remove unused `domain` variable in cookie formatting
- QLT-007: Remove duplicate test class definition
- QLT-008: Add trailing newlines to files
- QLT-009: Use `settings.user_agent` instead of hardcoded string
- QLT-010: Investigate or remove unused exception classes
- QLT-011: Investigate or remove unused `StreamWithCookies` model