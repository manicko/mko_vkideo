---
name: 07-tests-validated
description: Test Quality Audit Findings - Validated
agent: validator
validated: yes
---

# Phase 07 Audit Findings — Test Quality (Validated)

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes

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
- File `tests/test_hls_downloader_patch.py` contains orphaned code at lines 1-5:
  ```python
  async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
      nonlocal gather_called  # SyntaxError: no binding for nonlocal
      ...
  ```
- `Any` is imported but no binding exists for `gather_called`
- Test output: `SyntaxError: no binding for nonlocal 'gather_called' found`
- Collection error: `ERROR collecting tests/test_hls_downloader_patch.py`

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed active issue blocking all test collection. File is incomplete/fragmented code.

### TST-002: Global Shutdown Event Causes Event Loop Isolation Failures

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader_throttle.py, src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |

**Description:** The `_shutdown_event` global variable in `downloader_throttle.py` (line 18) is created once and reused across all tests. When pytest runs tests with different event loops (asyncio mode), the event object created in one test's event loop is accessed in another test's event loop, causing `RuntimeError: <asyncio.locks.Event object> is bound to a different event loop`. This breaks 10 tests that involve retry logic or sequential download mode.

**Evidence:**
- Source: `src/vkdownloader/services/downloader_throttle.py` lines 17-26:
  ```python
  _shutdown_event: asyncio.Event | None = None
  
  def get_shutdown_event() -> asyncio.Event:
      global _shutdown_event
      if _shutdown_event is None:
          _shutdown_event = asyncio.Event()  # Created in first test's loop
      return _shutdown_event
  ```
- Test failures show: `RuntimeError: '<asyncio.locks.Event object at 0x...> is bound to a different event loop'`
- **Verified failed tests (10 total):**
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_429_retry_with_exponential_backoff`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_retry_after_header_overrides_delay`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_max_retries_exceeded_returns_none`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_500_status_code_triggers_retry`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_502_status_code_triggers_retry`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_503_status_code_triggers_retry`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_504_status_code_triggers_retry`
  - `test_downloader_throttle.py::TestRetry429WithBackoff::test_structured_logging_on_retry`
  - `test_hls_downloader.py::TestSequentialDownloadMode::test_sequential_mode_applies_delay_after_semaphore`
  - `test_hls_downloader.py::TestSequentialDownloadMode::test_sequential_mode_triggers_backoff_on_429`

> **Validation Note:**
> - **Action:** Reclassified
> - **Detail:** Changed from `RUNTIME-ERROR` to `SPEC-DEVIATION` - the code pattern violates async best practices for testability. The implementation should be changed to create events per-async-context rather than caching globally.
> - **See also:** SRV-002 (Phase 03) reports the same issue

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
      # Full integration test would require mocking Path.resolve() which is complex
      pass  # No actual test implementation
  ```

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed - the test exists but is a no-op. The implementation in `security.py` (lines 42-47) shows the warning path exists and is functional, but the test does not verify it.

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

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed - the CLI implementation only has `download` and `batch` commands. The audit template references commands that don't exist in the codebase, indicating either a documentation mismatch or an incomplete feature. No SPEC.md or configuration references the non-existent commands.

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

> **Validation Note:**
> - **Action:** Rejected
> - **Reason:** The mock setup is actually correct - the tests properly mock `__aenter__` and `__aexit__` on `AsyncMock` objects (see lines 25-28, 64-70, etc. in test_downloader_throttle.py). The test failures are caused by TST-002 (global shutdown event event-loop binding issue), not by mock setup problems. The same mock pattern works in `test_successful_response_on_first_attempt` which passes. The error `is bound to a different event loop` confirms this is the underlying cause.

---

## Cross-Phase Conflicts & Merge Candidates

### Merge Candidates

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| TST-001 | SRV-001 (Phase 03) | Identical finding - syntax error in `test_hls_downloader_patch.py`. SRV-001 provides more detail but both describe the same root cause. |
| TST-002 | SRV-002 (Phase 03) | Identical finding - global shutdown event causing event loop binding errors. Both findings describe the same architectural issue. |

### Cross-Phase Conflicts

None detected. All test-related findings across phases are consistent with the evidence.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | TST-003, TST-004 |
| Reclassified | 1 | TST-002: RUNTIME-ERROR → SPEC-DEVIATION |
| Merged | 2 | TST-001 → SRV-001, TST-002 → SRV-002 |
| Rejected | 1 | TST-005 (mock issue is misdiagnosed; root cause is TST-002) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| TST-005 | Mock Setup Issues in Retry Tests Cause False Negatives | Misdiagnosed root cause. The mock setup is correct; test failures are caused by the global shutdown event binding to wrong event loop (TST-002). Same mock pattern works in passing tests. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| TST-001 | SRV-001 (Phase 03) | Identical finding - orphaned test file with syntax error blocking test collection |
| TST-002 | SRV-002 (Phase 03) | Identical finding - global asyncio.Event causing event loop isolation failures in tests |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| TST-002 | RUNTIME-ERROR | SPEC-DEVIATION | The code pattern violates async testability best practices. Global caching of asyncio primitives that are tied to event loops is an architectural anti-pattern that should be fixed in the implementation. |

---

## Rollout Safety Assessment

### Dependency Chain

- TST-001 (syntax error) must be fixed before any test execution
- TST-002 (event loop binding) affects 10 tests - fixing this unlocks retry and sequential mode tests
- TST-003 (no-op test) can be fixed independently

### Unsafe Rollout Ordering

The current test failures make it impossible to validate other fixes. Fixing in this order:
1. Remove/fix `test_hls_downloader_patch.py` (TST-001) - unblocks test collection
2. Refactor `get_shutdown_event()` (TST-002) - enables retry tests to run

### Fragile Insertion Points

The global `_shutdown_event` pattern is used at `downloader_throttle.py:21-26` and called from `downloader_throttle.py:52` and `downloader.py:380`. Any fix must maintain backward compatibility with production code while enabling test isolation.

---

## Warnings

- **Architectural Risk:** The global `_shutdown_event` pattern violates async isolation principles. In production, this could cause issues if the module is imported but never used in the main event loop, or in future test scenarios.
- **Rollout Risk:** The `AdaptiveThrottle` class (SRV-004, Phase 03) is exported but unused - potential dead code that could confuse developers.
- **Documentation Inconsistency:** The audit template references `init`, `config`, and `version` CLI commands that do not exist in the implementation.