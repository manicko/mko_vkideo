---
name: 03-services
description: Service Layer & Business Logic Audit
executor: auditor
status: complete
validated: no
template: .ai/audit/templates/audit-findings.md
---

# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### SRV-001: Test file has syntax error preventing test collection

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `tests/test_hls_downloader_patch.py` |
| **Classification** | mandatory |

**Description:** The file `tests/test_hls_downloader_patch.py` contains invalid Python syntax. It uses `nonlocal gather_called` without a parent function scope and references `Any` without importing it, causing a `SyntaxError` that prevents the entire test suite from being collected.

**Evidence:**
```
tests/test_hls_downloader_patch.py:1:
async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
        nonlocal gather_called
        gather_called = True
        return [True] * len(tasks)
```
Error: `SyntaxError: no binding for nonlocal 'gather_called' found`

**Recommendation:** Either remove this orphaned file or fix it to be a valid module. If it was intended as a patch helper, it should be properly integrated with the test file or removed entirely.

---

### SRV-002: Global shutdown event bound to wrong event loop in tests

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py:22-26`, `src/vkdownloader/services/downloader.py:222-224` |
| **Classification** | mandatory |

**Description:** The global `_shutdown_event` in `downloader_throttle.py` and its usage in `downloader.py` cause `RuntimeError: '...Event object... is bound to a different event loop'` when tests run with `asyncio.STRICT` mode. Each test runs in its own event loop, but the global event persists across tests and becomes bound to the wrong loop.

**Evidence:** Test failures in `test_downloader_throttle.py` and `test_hls_downloader.py` show:
```
RuntimeError: '<asyncio.locks.Event object at 0x... [unset]> is bound to a different event loop'
```
This occurs at:
- `tests/test_downloader_throttle.py:106` - during `asyncio.wait_for(shutdown_event.wait(), timeout=delay)`
- `tests/test_hls_downloader.py:380` - during the same pattern in `download_segment_concurrent`

**Recommendation:** Either reset the shutdown event in test setup/teardown, or make the event loop-aware by creating a fresh event per async context. The current implementation prevents the retry logic from being tested properly.

---

### SRV-003: Unused variable in download_hls_with_resume function

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:395` |
| **Classification** | advisory |

**Description:** The variable `results` is assigned on line 395 but never used after the `asyncio.gather()` call, triggering `F841` linter warning. While not a functional bug, it indicates incomplete code.

**Evidence:**
```python
# downloader.py:395
results = await asyncio.gather(*tasks)
```
The value is discarded immediately - no further use of `results` in the function.

**Recommendation:** Either use the results to check for failures, or remove the assignment if the return value is intentionally discarded.

---

### SRV-004: AdaptiveThrottle class is dead code

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/infrastructure/adaptive_throttle.py` |
| **Classification** | advisory |

**Description:** The `AdaptiveThrottle` class is defined and exported from `infrastructure/__init__.py` but is never imported or used anywhere else in the codebase. It exists only as an exported symbol.

**Evidence:** Grep search for `AdaptiveThrottle(` with usage outside its definition and `__init__.py` export returns no matches.

**Recommendation:** Investigate whether this class was intended for future use or if it should be removed. If kept for future use, document its intended purpose; if not, remove it to reduce maintenance burden.

---

### SRV-005: mypy errors in CLI batch download implementation

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py:217-227` |
| **Classification** | mandatory |

**Description:** Mypy reports errors that coroutines from `asyncio.as_completed` have no `done` or `cancel` attribute. The code incorrectly treats coroutines as Task objects when handling cancellation.

**Evidence:**
```
src\vkdownloader\cli.py:223: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"  [attr-defined]
src\vkdownloader\cli.py:224: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "cancel"  [attr-defined]
```

Code in question:
```python
for coro in asyncio.as_completed(tasks):
    try:
        await coro
    except asyncio.CancelledError:
        for task in tasks:
            if not task.done():
                task.cancel()
```

**Recommendation:** The `tasks` list holds coroutine objects, not Task objects. Either wrap coroutines in tasks using `asyncio.create_task()` before `as_completed`, or restructure to track Task objects separately for proper cancellation.

---

### SRV-006: Ruff linter reports multiple issues

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | Multiple (see evidence) |
| **Classification** | advisory |

**Description:** Ruff check reports several automatically-fixable issues including unresolved imports, deprecated `asyncio.TimeoutError` usage, and unused variables.

**Evidence:**
- `I001`: Import blocks unsorted in `.ai/builders/back/py_map.py` and `tests/test_hls_downloader_patch.py`
- `UP041`: Use builtin `TimeoutError` instead of `asyncio.TimeoutError` (3 occurrences in `downloader.py`, 1 in `downloader_throttle.py`)
- `W292`: Missing newlines at end of files (`cli.py` line 258, `test_hls_downloader_patch.py`)
- `F841`: Unused variables (`results`, `mock_download`, `result` in test contexts)

**Recommendation:** Run `uv run ruff check --fix` and `uv run ruff format` to resolve these issues.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 3 |

## Mandatory Fixes

- SRV-001: Fix or remove broken test file blocking test collection
- SRV-002: Fix global shutdown event event-loop binding issue
- SRV-005: Fix mypy type errors in CLI cancellation logic

## Advisory Recommendations

- SRV-003: Remove unused `results` variable or use its value
- SRV-004: Investigate and document or remove dead code `AdaptiveThrottle`
- SRV-006: Run ruff auto-fixes for import sorting and deprecated exception aliases
