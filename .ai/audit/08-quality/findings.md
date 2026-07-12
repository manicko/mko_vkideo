---
name: audit-findings
description: Structured findings template for audit phase output
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

### QLT-001: `print()` statements used in production code (CLI)

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** The `batch_download` function in cli.py uses `print()` statements for progress output (lines 215, 229, 231), which violates the project convention that all output must use `logger`. This prevents proper log aggregation and structured logging. Using print() makes output inconsistent with other parts of the application that use structlog.

**Evidence:** ruff check output; lines 215, 229, 231 in src\vkdownloader\cli.py:
```
215|     print(f"Downloading videos: 0/{total} completed", end="\r", flush=True)
229|     print(f"Downloading videos: {done_count}/{total} completed", end="\r", flush=True)
231|     print()  # New line after progress
```

**Recommendation:** Replace `print()` statements with `typer.echo()` for user-facing output (already used elsewhere in the file) or `logger.info()` for operational logging. Using typer.echo() maintains consistency with other CLI output in the same file.

---

### QLT-002: Unused variable `results` in downloader.py

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Variable `results` is assigned at line 395 but never read. The results from `asyncio.gather()` are collected but unused, indicating either dead code or incomplete implementation. While the code functions correctly, this wasted assignment adds cognitive overhead and may indicate missing error handling.

**Evidence:** ruff check output:
```
F841 Local variable `results` is assigned to but never used
--> src\vkdownloader\services\downloader.py:395:21
```

**Recommendation:** Either remove the assignment if results are not needed, or use the results to verify all downloads succeeded before marking completion.

---

### QLT-003: Bare `except:` not used but general `Exception` catches in downloader code

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** While no bare `except:` clauses were found, several functions catch broad `Exception` types (e.g., line 219, 518, 637, 888). The most notable is in `_download_with_ytdlp` at line 948 which catches `Exception` without specific handling. This reduces debuggability by masking specific error types. However, the code does log errors appropriately.

**Evidence:** src\vkdownloader\services\downloader.py:948 - `except Exception as e:` in `_download_with_ytdlp`

**Recommendation:** Consider catching more specific exception types where possible (e.g., `yt_dlp.DownloadError`, `OSError`) to enable more targeted error handling. Current broad catches are still acceptable given proper logging is in place.

---

### QLT-004: Functions exceed 50-line guideline without clear justification

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py, src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Three functions exceed the ~50-line guideline: `batch_download` (53 statements), `download_with_ffmpeg` (70 statements), and `download_hls_with_resume` (67 statements). These are complex functions handling download orchestration, progress tracking, and error recovery. While the complexity is justified by their responsibilities, they could benefit from extraction of subtasks for improved readability.

**Evidence:** ruff check output (PLR0915):
```
src\vkdownloader\cli.py:122 - batch_download has 53 > 50 statements
src\vkdownloader\services\downloader.py:166 - download_with_ffmpeg has 70 > 50 statements
src\vkdownloader\services\downloader.py:296 - download_hls_with_resume has 67 > 50 statements
```

**Recommendation:** Consider refactoring complex functions by extracting nested async functions into module-level helpers. For `download_with_ffmpeg`, extract `_monitor_progress` and `_drain_stderr` setup. For `download_hls_with_resume`, extract the segment download logic into a separate helper. Priority: medium - these are maintainable but could be cleaner.

---

### QLT-005: `Any` type used in network_monitor.py for Playwright types

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/infrastructure/network_monitor.py |
| **Classification** | advisory |

**Description:** The `network_monitor.py` module uses `Any` type for `response` and `data` parameters in `_intercept_response` and `_extract_urls_from_json`. This is intentional because Playwright's `Response` type and JSON data types are dynamic. While `Any` is generally discouraged, this is a pragmatic choice for library interop where types cannot be precisely specified.

**Evidence:** src\vkdownloader\infrastructure\network_monitor.py:47 and 70:
```python
async def _intercept_response(self, response: Any) -> None:
def _extract_urls_from_json(self, data: Any) -> None:
```

**Recommendation:** This is acceptable as-is. Consider adding `# type: ignore[assignment]` comments or using `object` if stricter typing is desired, but for Playwright integration the pragmatic use of `Any` is reasonable.

---

### QLT-006: Unused `type: ignore` comments in downloader.py signal handler setup

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Lines 796 and 801 have `type: ignore` comments that mypy reports as unused. This suggests either the type issue was resolved or the suppressions are no longer needed.

**Evidence:** mypy output:
```
src\vkdownloader\services\downloader.py:796: error: Unused "type: ignore" comment
src\vkdownloader\services\downloader.py:801: error: Unused "type: ignore" comment
```

**Recommendation:** Remove the unused `type: ignore` comments as they add noise without purpose.

---

### QLT-007: Syntax error in test file blocks test collection

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | CRITICAL |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/test_hls_downloader_patch.py |
| **Classification** | mandatory |

**Description:** The test file `test_hls_downloader_patch.py` contains a syntax error using `nonlocal` outside of a containing scope. This prevents pytest from even collecting the test module, causing complete test suite failure.

**Evidence:** pytest error output:
```
tests\test_hls_downloader_patch.py:2: nonlocal gather_called
SyntaxError: no binding for nonlocal 'gather_called' found
```

**Recommendation:** Fix the syntax error by either: (1) removing this incomplete test file if not used, (2) completing the implementation with proper variable scoping, or (3) moving `gather_called` to an enclosing function scope.

---

### QLT-008: Unused variable `mock_download` in test_cli.py

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_cli.py |
| **Classification** | advisory |

**Description:** In test_cli.py line 174, `mock_download` is patched but never used in the test, suggesting incomplete test setup or dead test mock.

**Evidence:** ruff check output:
```
F841 Local variable `mock_download` is assigned to but never used
--> tests\test_cli.py:174:59
```

**Recommendation:** Remove the unused mock or use it in the test assertions.

---

### QLT-009: Unused variable `result` in test_hls_downloader.py

| Field | Value |
|-------|-------|
| **ID** | QLT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_hls_downloader.py |
| **Classification** | advisory |

**Description:** In test_hls_downloader.py line 1002, `result` is assigned from `_download_with_ytdlp` but never used, suggesting incomplete test or missing assertion.

**Evidence:** ruff check output:
```
F841 Local variable `result` is assigned to but never used
--> tests\test_hls_downloader.py:1002:21
```

**Recommendation:** Use the result in assertions or remove the assignment.

---

### QLT-010: Missing newline at end of cli.py

| Field | Value |
|-------|-------|
| **ID** | QLT-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** The cli.py file lacks a trailing newline at line 258, which violates POSIX text file conventions and may cause issues with some tools.

**Evidence:** ruff check output:
```
W292 No newline at end of file
--> src\vkdownloader\cli.py:258:10
```

**Recommendation:** Add a trailing newline to the file.

---

### QLT-011: Mypy error: accessing `.done()` on coroutine instead of task

| Field | Value |
|-------|-------|
| **ID** | QLT-011 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | mandatory |

**Description:** mypy reports that `task.done()` and `task.cancel()` are being called on a Coroutine object rather than an asyncio.Task. Looking at line 222-224, `tasks` is a list of coroutines created with list comprehension, not tasks. The code then calls `.done()` on coroutines which would fail at runtime. However, examining the actual code, `tasks[i]` after `asyncio.as_completed()` returns the original coroutines, and the actual flow uses `asyncio.as_completed` correctly - the mypy error indicates a real type safety issue.

**Evidence:** mypy output:
```
src\vkdownloader\cli.py:223: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"
src\vkdownloader\cli.py:224: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no new attribute "cancel"
```

**Recommendation:** The code at lines 222-224 iterates over `tasks` (which are coroutines) and calls `.done()` on them incorrectly. Looking at the actual code flow, `asyncio.as_completed(tasks)` yields completed tasks, but the code then iterates over the original `tasks` list in the `CancelledError` handler. This is a bug: `tasks[i]` returns a coroutine, not a task. Fix by storing the actual task objects returned by `asyncio.as_completed` or restructuring the cancellation logic.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 2 |
| MEDIUM | 1 |
| LOW | 7 |

## Mandatory Fixes

- QLT-007: Fix syntax error in test_hls_downloader_patch.py that blocks test collection
- QLT-011: Fix mypy error - code attempts to call `.done()` and `.cancel()` on Coroutine objects instead of Tasks

## Advisory Recommendations

- QLT-001: Replace `print()` statements with `logger` or `typer.echo()` in cli.py
- QLT-002: Remove or use the unused `results` variable in downloader.py
- QLT-003: Consider more specific exception types where practical
- QLT-004: Refactor large functions for maintainability
- QLT-005: Keep `Any` for Playwright interop (acceptable as-is)
- QLT-006: Remove unused `type: ignore` comments in downloader.py
- QLT-008: Remove unused `mock_download` in test_cli.py
- QLT-009: Use or remove unused `result` variable in test_hls_downloader.py
- QLT-010: Add trailing newline to cli.py