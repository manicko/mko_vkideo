---
name: audit-findings-02-config
description: Configuration & Pydantic Models Phase Findings
agent: auditor
executor: auditor
status: complete
validated: no
---

# Phase 02 Audit Findings — Configuration & Pydantic Models

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** no

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

### CFG-002: StreamFormat.DASH enum value defined but never used

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src\vkdownloader\models\enums.py, src\vkdownloader\models\video.py |
| **Classification** | mandatory |

**Description:** The `StreamFormat.DASH` enum value is defined but never used anywhere in the codebase. The extractor service at line 166 only checks for `.m3u8` (HLS) and falls back to `MP4`, never handling DASH format. This creates an inconsistency between the model definition and actual usage.

**Evidence:**
- `src\vkdownloader\models\enums.py` lines 20-25: `StreamFormat` enum defines HLS, DASH, and MP4 values
- `src\vkdownloader\services\extractor.py` line 166: `format=StreamFormat.HLS if ".m3u8" in format_url else StreamFormat.MP4` - DASH never used
- Grep search for `StreamFormat.DASH` returns no matches in source code

**Recommendation:** Either remove `StreamFormat.DASH` from the enum if DASH streams are not supported, or add DASH detection logic in the extractor service to handle `.mpd` URLs properly. If removing, also remove it from `models/__init__.py` exports.

**Effort:** trivial

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
- Mypy output: `"Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"` and `"has no attribute "cancel"``

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

### CFG-006: HLSDownloadRequest uses Any type instead of forward reference

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src\vkdownloader\models\dtos.py |
| **Classification** | advisory |

**Description:** The `HLSDownloadRequest` model uses `Any` type for `settings` and `extractor` fields instead of proper forward references. While there's a comment explaining this is intentional to avoid circular imports, modern Pydantic supports forward references via string annotations that work with type checkers.

**Evidence:**
- `src\vkdownloader\models\dtos.py` line 36-37: `settings: Any | None = None` and `extractor: Any | None = None`
- Comment at lines 33-35: "Runtime types: Settings | None and VKVideoExtractor | None - Using Any to avoid circular import issues"

**Recommendation:** Use Pydantic's `ForwardRef` or string annotations (`"Settings"`, `"VKVideoExtractor"`) with `model_config = ConfigDict(arbitrary_types_allowed=True)` already present. This maintains type safety without circular import issues while still working with modern type checkers.

**Effort:** small

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
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

- CFG-003: Test file crash blocks all test execution
- CFG-004: Type errors in batch download will cause runtime AttributeError
- CFG-007: Global shutdown event causes event loop binding failures in tests

## Advisory Recommendations

- CFG-001: log_level should be validated against known log levels
- CFG-002: Unused StreamFormat.DASH enum creates inconsistency
- CFG-005: Remove unused type ignore comments  
- CFG-006: Use forward references instead of Any for HLSDownloadRequest

---

## Runtime Evidence Summary

1. **Test suite failure**: `uv run pytest` exits with SyntaxError in `test_hls_downloader_patch.py` before any tests run
2. **Type checker output**: Mypy reports 4 errors across 2 files (downloader.py and cli.py)
3. **Invalid log level acceptance**: `Settings(log_level='INVALID_LOG_LEVEL')` succeeds silently
4. **Event loop binding failures**: 8 tests fail with `RuntimeError: is bound to a different event loop` due to global shutdown event