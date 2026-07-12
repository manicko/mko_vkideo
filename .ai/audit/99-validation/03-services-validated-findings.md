---
name: 03-services-validated
description: Service Layer & Business Logic Audit - Validated Findings
executor: validator
status: complete
validated: yes
source: .ai/audit/03-services/findings.md
---

# Phase 03 Audit Findings — Service Layer & Business Logic (Validated)

**Executor:** validator  
**Source:** .ai/audit/03-services/findings.md  
**Status:** complete  
**Validated:** yes

---

## Cross-Finding Analysis

### Duplicate Findings Across Phases

| Original ID | Duplicate IDs | Target for Merge |
|-------------|---------------|----------------|
| SRV-001 | CFG-003, QLT-007 | Keep SRV-001 (Phase 03) |
| SRV-002 | CFG-007 | Keep SRV-002 (Phase 03) |
| SRV-005 | CFG-004, CLI-001, QLT-011 | Keep SRV-005 (Phase 03) |

### Cross-Phase Conflicts

No conflicts detected. All phases consistently report the same issues.

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
tests/test_hls_downloader_patch.py:1-2:
async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
        nonlocal gather_called
```
Error: `SyntaxError: no binding for nonlocal 'gather_called' found` (verified via `python -m py_compile`)

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by Python syntax check. The file is orphaned and incomplete - `nonlocal` requires an enclosing function scope and `Any` requires import from `typing`.
> - **See also:** CFG-003 (Phase 02), QLT-007 (Phase 08) - duplicate findings

**Status:** ✅ VALIDATED

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

**Evidence:** Test failures in `test_hls_downloader.py`:
```
RuntimeError: '<asyncio.locks.Event object at 0x000001C35BBC28D0 [unset]> is bound to a different event loop'
```
Confirmed in `tests/test_hls_downloader.py::TestSequentialDownloadMode::test_sequential_mode_applies_delay_after_semaphore` and `test_sequential_mode_triggers_backoff_on_429`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by runtime test execution. The global event pattern is fundamentally incompatible with asyncio.STRICT mode where each test gets a fresh event loop.
> - **See also:** CFG-007 (Phase 02) - duplicate finding

**Status:** ✅ VALIDATED

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

**Evidence:** `ruff check` confirms:
```
F841 Local variable `results` is assigned to but never used
   --> src\vkdownloader\services\downloader.py:395:21
```

**Recommendation:** Either use the results to check for failures, or remove the assignment if the return value is intentionally discarded.

**Status:** ✅ VALIDATED

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

**Evidence:** Grep search for `AdaptiveThrottle(` with usage outside its definition and `__init__.py` export returns no matches in source code.

> **Validation Note:**
> - **Action:** REJECTED
> - **Detail:** The AdaptiveThrottle class IS referenced in project architecture documentation (`.ai/structure/back/py_anchors.yaml` and `.ai/structure/back/py_map.yaml`). Per validation rules for "dead code" findings: if spec, models, or config reference the component, reject the "dead code" label and reclassify as `SPEC-DEVIATION` (missing integration, not dead code).
> - **See also:** `.ai/structure/back/py_anchors.yaml` lines 332, 339, 347, 355

**Status:** ❌ REJECTED - Component referenced in architecture documentation, not dead code. Missing integration represents architectural incompleteness.

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

**Evidence:** `mypy` confirms the exact errors:
```
src\vkdownloader\cli.py:223: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"  [attr-defined]
src\vkdownloader\cli.py:224: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "cancel"  [attr-defined]
```

**Recommendation:** The `tasks` list holds coroutine objects, not Task objects. Either wrap coroutines in tasks using `asyncio.create_task()` before `as_completed`, or restructure to track Task objects separately for proper cancellation.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by mypy type checking. The coroutines created on line 210 cannot have `.done()` or `.cancel()` called on them - this will raise `AttributeError` at runtime during cancellation handling.
> - **See also:** CFG-004 (Phase 02), CLI-001 (Phase 01), QLT-011 (Phase 08) - duplicate findings

**Status:** ✅ VALIDATED

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
- `I001`: Import blocks unsorted in `.ai/builders/back/py_map.py` (generated artifact, not source) - EXCLUDED
- `UP041`: Use builtin `TimeoutError` instead of `asyncio.TimeoutError` (3 occurrences in `downloader.py`, 1 in `downloader_throttle.py`) - VALIDATED as source issues
- `W292`: Missing newlines at end of files (`cli.py` line 258) - VALIDATED as source issue
- `F841`: Unused variables (`results` in downloader.py, `mock_download` in test_cli.py, `result` in test_hls_downloader.py) - VALIDATED as source issues
- `F821`: Undefined name `Any` and unused `gather_called` in `test_hls_downloader_patch.py` - ALREADY COVERED by SRV-001

> **Validation Note:**
> - **Action:** PARTIALLY REJECTED
> - **Detail:** The `.ai/builders/back/py_map.py` issue is from a generated artifact in `.ai/` directory, not source code. The UP041 and W292 issues in source files are valid but represent minor deprecations. Issues in `test_hls_downloader_patch.py` are covered by SRV-001.
> - **See also:** SRV-001 covers `test_hls_downloader_patch.py` issues; UP041 issues overlap with downloader.py logic changes

**Status:** ⚠️ PARTIALLY VALIDATED - Source issues are real but low severity; artifact file excluded

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | SRV-001, SRV-002, SRV-003, SRV-005 |
| Reclassified | 0 | — |
| Merged | 3 | SRV-001 → SRV-001 (keep), SRV-002 → SRV-002 (keep), SRV-005 → SRV-005 (keep) |
| Rejected | 1 | SRV-004 |
| Partially Validated | 1 | SRV-006 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| SRV-004 | AdaptiveThrottle class is dead code | Component referenced in `.ai/structure/back/py_anchors.yaml` and `.ai/structure/back/py_map.yaml` - represents missing integration, not dead code |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| CFG-003 | SRV-001 (Phase 03) | Same syntax error in same file (`test_hls_downloader_patch.py`) |
| CFG-007 | SRV-002 (Phase 03) | Same event loop binding runtime error in same module |
| CFG-004 | SRV-005 (Phase 03) | Same mypy type error in same location (`cli.py:223-224`) |
| CLI-001 | SRV-005 (Phase 03) | Same coroutine/Task handling error in same location |
| QLT-011 | SRV-005 (Phase 03) | Same mypy type error in same location |

### Reclassified Findings

No reclassification needed.

---

## Rollout Analysis

**No rollout safety issues detected within this phase.** The findings are isolated linting/type issues that do not affect architectural dependencies.

---

## Warnings

- **Architectural Risk:** SRV-002 (global shutdown event) affects testability and may cause issues in concurrent/parallel execution scenarios
- **Documentation Inconsistency:** SRV-004 highlights that `AdaptiveThrottle` is documented in architecture files but not integrated into runtime code
- **SRV-001 blocks test collection** - affects test execution across all phases (CFG-003, QLT-007)

---

## Required Fixes

- SRV-001: Fix or remove broken test file blocking test collection (HIGH severity)
- SRV-002: Fix global shutdown event event-loop binding issue (MEDIUM severity)
- SRV-005: Fix mypy type errors in CLI cancellation logic (MEDIUM severity)

---

## Advisory Recommendations

- SRV-003: Remove unused `results` variable or use its value (LOW severity)
- SRV-006: Run ruff auto-fixes for deprecated exception aliases and trailing newlines (LOW severity)