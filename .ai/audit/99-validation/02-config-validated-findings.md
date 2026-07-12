---
name: 02-config-validated-findings
description: Validated findings for Configuration & Pydantic Models Phase
agent: validator
status: complete
validated: yes
---

# Phase 02 Validated Findings — Configuration & Pydantic Models

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** yes

---

## Findings

### CFG-001: log_level field accepts invalid values without validation

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src\vkdownloader\config.py |
| **Classification** | advisory |

**Description:** The `log_level` field in the `Settings` model accepts any string value without validation. This can lead to runtime errors when `logging.getLevelName(settings.log_level)` is called with an invalid log level like "INVALID_LOG_LEVEL" - it silently returns the string as-is instead of raising an error, causing unexpected behavior in the logging configuration.

**Evidence:**
- `src\vkdownloader\config.py` line 91-94: `log_level: str = Field(default="INFO", description="Logging level")` - no validator
- `src\vkdownloader\config.py` line 122: `logging.getLevelName(settings.log_level)` - relies on string being a valid log level
- Runtime test: `Settings(log_level='INVALID_LOG_LEVEL')` succeeds without error, and `logging.getLevelName('INVALID_LOG_LEVEL')` returns `'INVALID_LOG_LEVEL'` instead of raising

**Recommendation:** Add a `@field_validator` for `log_level` that validates against standard log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL). Use `Literal` type or enum for stricter typing. This prevents runtime misconfigurations and provides clearer error messages.

**Effort:** small

---

### CFG-002: ~~StreamFormat.DASH enum value defined but never used~~ [REJECTED]

> **Rejection reason:** Documentation in `docs/01-tools/api-reference.md` (line 646-701) and `docs/00-overview/vkdownloader-overview.md` (line 65) explicitly references DASH as a valid stream format. This indicates the enum value is part of the documented API specification, not dead code. The finding incorrectly labels this as "dead code" when it represents a planned feature that is documented but not yet implemented. Per validation rules for "dead code" findings, when spec or documentation references the component, it should be rejected as SPEC-DEVIATION (missing integration) rather than dead code.

---

### CFG-003: Test file test_hls_downloader_patch.py has syntax error

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests\test_hls_downloader_patch.py |
| **Classification** | mandatory |

**Description:** The test file `test_hls_downloader_patch.py` contains a standalone function with `nonlocal gather_called` but no enclosing function scope, causing a SyntaxError that prevents the entire test suite from running.

**Evidence:**
- `tests\test_hls_downloader_patch.py` lines 1-5: Function uses `nonlocal` without enclosing scope
- Runtime error: `SyntaxError: no binding for nonlocal 'gather_called' found` when running `uv run pytest`
- Error output: `ERROR collecting tests/test_hls_downloader_patch.py - SyntaxError: no binding for nonlocal 'gather_called' found`

**Recommendation:** Either fix the test file by wrapping the function in a proper test class/function with the `gather_called` variable in scope, or delete the file if it's an orphaned/incomplete patch test.

**Effort:** trivial

---

### CFG-004: Mypy type errors in batch download coroutine handling

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src\vkdownloader\cli.py |
| **Classification** | mandatory |

**Description:** The batch download code attempts to check `.done()` and `.cancel()` on coroutine objects instead of Task objects. Coroutines created via list comprehension (`tasks = [_limited_download(url) for url in urls]`) are not Tasks, they are coroutines that haven't been scheduled. The `asyncio.as_completed()` function expects Tasks, not coroutines.

**Evidence:**
- `src\vkdownloader\cli.py` line 210: `tasks = [_limited_download(url) for url in urls]` - creates coroutines, not Tasks
- `src\vkdownloader\cli.py` lines 222-224: `for task in tasks: if not task.done(): task.cancel()` - coroutines don't have these methods
- Mypy output confirms: `"Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"` and `"has no attribute "cancel"``

**Recommendation:** Wrap coroutines in `asyncio.create_task()` before adding to the tasks list, or change the iteration logic to properly handle the coroutine/Task distinction. The fix requires converting coroutines to Tasks before they can be cancelled.

**Effort:** small

---

### CFG-005: Unused type ignore comments in downloader.py

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src\vkdownloader\services\downloader.py |
| **Classification** | advisory |

**Description:** Two `# type: ignore` comments at lines 796 and 801 are no longer needed - mypy reports them as unused, indicating the underlying type issues have been resolved or the comments were incorrectly placed.

**Evidence:**
- `src\vkdownloader\services\downloader.py` line 796: `signal.signal(sig, lambda s, f: _handle_signal())  # type: ignore`
- `src\vkdownloader\services\downloader.py` line 801: `signal.signal(sig, lambda s, f: _handle_signal())  # type: ignore`
- Mypy output: `error: Unused "type: ignore" comment` for both locations

**Recommendation:** Remove the unused `# type: ignore` comments to clean up the code and prevent confusion about actual type issues.

**Effort:** trivial

---

### CFG-006: ~~HLSDownloadRequest uses Any type instead of forward reference~~ [REJECTED]

> **Rejection reason:** The `Any` type usage is intentional and correct for this use case. Pydantic models with `arbitrary_types_allowed=True` can accept `Any` for runtime-injected dependencies that are not validated. Using forward references (`"Settings"`, `"VKVideoExtractor"`) would not work for runtime type checking since these objects are passed in at runtime, not parsed from input data. The current implementation trades static type safety for runtime flexibility, which is appropriate for this DTO pattern. Forward references would add complexity without providing runtime validation benefits, and the circular import issue is real (Settings imports from config, which would need to import this DTO). This recommendation introduces unnecessary abstraction for a working solution.

---

### CFG-007: Global shutdown event causes event loop binding issues in tests

| Field | Value |
|-------|-------|
| **ID** | CFG-007 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src\vkdownloader\services\downloader_throttle.py |
| **Classification** | mandatory |

**Description:** The `_shutdown_event` in `downloader_throttle.py` is a module-level global `asyncio.Event` that persists across test runs with different event loops. When tests run in isolation or in different orders, the Event created in one event loop is accessed from another, causing `RuntimeError: is bound to a different event loop`.

**Evidence:**
- `src\vkdownloader\services\downloader_throttle.py` lines 17-18: `_shutdown_event: asyncio.Event | None = None` - global event
- `src\vkdownloader\services\downloader_throttle.py` lines 21-26: `get_shutdown_event()` creates event on first access
- Test failures show: `RuntimeError: <asyncio.locks.Event object at 0x0000024450BFBCB0 [unset]> is bound to a different event loop`
- 8 test failures in `test_downloader_throttle.py` related to this issue

**Recommendation:** Either reset the global `_shutdown_event` in a test fixture cleanup, or restructure the code to accept the shutdown event as a parameter for better testability. For production code, consider using `asyncio.Event()` created fresh per context rather than caching globally.

**Effort:** small

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- CFG-003: Test file crash blocks all test execution
- CFG-004: Type errors in batch download will cause runtime AttributeError
- CFG-007: Global shutdown event causes event loop binding failures in tests

## Advisory Recommendations

- CFG-001: log_level should be validated against known log levels
- CFG-005: Remove unused type ignore comments

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | CFG-001, CFG-003, CFG-004, CFG-005, CFG-007 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 2 | CFG-002 (documented spec), CFG-006 (intentional design) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| CFG-002 | StreamFormat.DASH enum value defined but never used | Documentation in api-reference.md and vkdownloader-overview.md explicitly references DASH as a valid stream format, indicating planned feature not dead code |
| CFG-006 | HLSDownloadRequest uses Any type instead of forward reference | Intentional design; forward references wouldn't provide runtime validation benefits for runtime-injected dependencies; Any is appropriate with arbitrary_types_allowed=True |

### Merged Findings

No merged findings.

### Reclassified Findings

No reclassified findings.

---

## Runtime Evidence Summary

1. **Test suite failure**: `uv run pytest` exits with SyntaxError in `test_hls_downloader_patch.py` before any tests run
2. **Type checker output**: Mypy reports 4 errors across 2 files (downloader.py and cli.py)
3. **Invalid log level acceptance**: `Settings(log_level='INVALID_LOG_LEVEL')` succeeds silently
4. **Event loop binding failures**: 8 tests fail with `RuntimeError: is bound to a different event loop` due to global shutdown event