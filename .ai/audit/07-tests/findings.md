---
name: audit-findings-tests
description: Test Quality Audit Findings
agent: auditor
status: complete
validated: no
---

# Phase 07 Audit Findings — Test Quality

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### TST-001: Syntax Error in Test File Blocks Test Collection

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | CRITICAL |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/test_hls_downloader_patch.py |
| **Classification** | mandatory |

**Description:** The test file `test_hls_downloader_patch.py` contains a syntax error that prevents the entire test suite from being collected. The file has 5 lines with a `nonlocal` statement outside of any function scope, causing `SyntaxError: no binding for 'nonlocal' found`. This prevents any tests from running.

**Evidence:**
- File `tests/test_hls_downloader_patch.py` line 1-5 contains orphaned code:
  ```python
  async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
      nonlocal gather_called  # SyntaxError: no binding for nonlocal
      ...
  ```
- Test output: `SyntaxError: no binding for nonlocal 'gather_called' found`
- Collection error: `ERROR collecting tests/test_hls_downloader_patch.py`

**Recommendation:** Remove or fix `tests/test_hls_downloader_patch.py`. The file appears to be incomplete/fragmented code that was accidentally committed. If it was meant to be a patch file, it should either be removed or properly completed with the enclosing function scope.

---

### TST-002: Global Shutdown Event Causes Event Loop Isolation Failures

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/downloader_throttle.py, src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |

**Description:** The `_shutdown_event` global variable in `downloader_throttle.py` (line 18) is created once and reused across all tests. When pytest runs tests with different event loops (asyncio mode), the event object created in one test's event loop is accessed in another test's event loop, causing `RuntimeError: <asyncio.locks.Event object> is bound to a different event loop`. This breaks 9 tests that involve retry logic or sequential download mode.

**Evidence:**
- Source: `src/vkdownloader/services/downloader_throttle.py` line 17-26:
  ```python
  _shutdown_event: asyncio.Event | None = None
  
  def get_shutdown_event() -> asyncio.Event:
      global _shutdown_event
      if _shutdown_event is None:
          _shutdown_event = asyncio.Event()  # Created in first test's loop
      return _shutdown_event
  ```
- Test failures show: `RuntimeError: '<asyncio.locks.Event object at 0x...> is bound to a different event loop'`
- Affected tests:
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_429_retry_with_exponential_backoff`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_retry_after_header_overrides_delay`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_max_retries_exceeded_returns_none`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_500_status_code_triggers_retry` (and 502, 503, 504 variants)
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_structured_logging_on_retry`
  - `test_hls_downloader.py::TestSequentialDownloadMode::test_sequential_mode_applies_delay_after_semaphore`
  - `test_hls_downloader.py::TestSequentialDownloadMode::test_sequential_mode_triggers_backoff_on_429`

**Recommendation:** Refactor the global shutdown event to be created per-call rather than cached, or provide a way to reset it between tests. For async code in tests, the event should be created in the context of the running event loop, not cached globally. Consider using `asyncio.Event()` directly in functions that need it, or adding a test fixture to reset/clear the event between tests.

---

### TST-003: No-Op Test with Pass Statement and Incomplete Implementation

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_security.py |
| **Classification** | advisory |

**Description:** The test `test_path_inside_repo_warns` in `TestValidateOutputPath` class (lines 55-64) contains only a `pass` statement and does not actually test the warning behavior. The docstring indicates the test should verify that a path inside the repository root triggers a warning, but the implementation is incomplete.

**Evidence:**
- File: `tests/test_security.py` lines 55-64:
  ```python
  def test_path_inside_repo_warns(self, tmp_path: Path) -> None:
      """Test that path inside repository root triggers warning."""
      # Note: This test validates that the warning path exists in the code
      # ...
      pass  # No actual test implementation
  ```

**Recommendation:** Either implement the actual test logic with proper mocking to verify the warning is triggered, or remove the test if the warning behavior is not critical to test. The current `pass` statement provides no test value and creates confusion about what is being tested.

---

### TST-004: Missing Tests for Init/Config CLI Commands and Error Paths

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/cli.py, src/vkdownloader/exceptions.py |
| **Classification** | advisory |

**Description:** The audit phase template specifies that CLI commands (init, run, config, version) must have error path tests. However:
1. No `init`, `config`, or `version` CLI commands exist in `cli.py` - only `download` and `batch_download` commands are implemented
2. Error handling tests are missing for critical CLI error paths including: missing output directory creation failures, file permission errors, concurrent download failures

**Evidence:**
- `cli.py` lines 25-218 show only two commands: `download` and `batch`
- The audit template (line 96-104) specifies tests needed for: init, config, version commands, error paths
- Exception tests only cover basic instantiation in `test_models.py` and specific error raising in `test_extractor.py`, `test_quality_selector.py`, `test_security.py`

**Recommendation:** Add tests for missing error paths in CLI commands:
1. Test that download command handles permission denied for output directory
2. Test that batch command handles file read errors
3. Test edge cases for validate_output_path with permission issues
4. Consider if init/config/version commands should be added or documentation updated

---

### TST-005: Mock Setup Issues in Retry Tests Cause False Negatives

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/test_downloader_throttle.py |
| **Classification** | advisory |

**Description:** Multiple retry tests in `TestRetry429WithBackoff` fail due to incorrect mock setup for the async context manager pattern. The tests mock `session.get` but the code in `_retry_429_with_backoff` uses `async with session.get(...) as response`, requiring proper `__aenter__` and `__aexit__` mock setup that is not correctly implemented.

**Evidence:**
- Test `test_429_retry_with_exponential_backoff` expects `sleep_calls` to have 1 element but gets 0
- Test `test_retry_after_header_overrides_delay` expects result `b"segment content"` but gets `None`
- The mock setup uses `MagicMock` for context manager but async context manager requires `AsyncMock` with proper `__aenter__`/`__aexit__`

**Recommendation:** Fix mock setup in retry tests to properly mock async context managers:
```python
mock_context = AsyncMock()
mock_context.__aenter__ = AsyncMock(return_value=mock_response)
mock_context.__aexit__ = AsyncMock(return_value=None)
mock_session.get = MagicMock(return_value=mock_context)
```

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 0 |

## Mandatory Fixes

- TST-001: Fix syntax error in `tests/test_hls_downloader_patch.py` (blocking all tests)
- TST-002: Fix global shutdown event to work with pytest's asyncio event loop isolation

## Advisory Recommendations

- TST-003: Implement or remove `test_path_inside_repo_warns` no-op test
- TST-004: Add missing error path tests for CLI commands
- TST-005: Fix async context manager mock setup in retry tests

---