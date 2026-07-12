---
name: 01-cli-validated-findings
description: Validated findings for CLI Entry Point & Command Layer
agent: validator
validated: yes
---

# Phase 01 Validated Findings - CLI Entry Point & Command Layer

**Source:** `.ai/audit/01-cli/findings.md`  
**Validated:** yes  
**Validation Date:** 2026-07-11

---

## Cross-Finding Analysis

### Duplicate Findings Across Phases

| Original ID | Duplicate IDs | Target for Merge |
|-------------|---------------|----------------|
| CLI-001 | CFG-004, SRV-005, QLT-011 | Keep CLI-001 |
| CLI-003 | CFG-005, QLT-006 | Keep CLI-003 |
| CLI-002 | QLT-010 | Keep CLI-002 |

### Cross-Phase Conflicts

No conflicts detected. All phases consistently report the same issues.

---

## Findings

### CLI-001: Type Safety Violation in Batch Download Task Cancellation

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by mypy output. The `tasks` list contains coroutines (line 210: `tasks = [_limited_download(url) for url in urls]`), not Task objects. In the CancelledError handler (lines 222-224), the code attempts to call `.done()` and `.cancel()` on coroutines, which will cause `AttributeError` at runtime when cancellation is attempted.
> - **See also:** CFG-004, SRV-005, QLT-011 (duplicates)

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | mandatory |

Description: In the batch download function the code attempts to call .done() and .cancel() methods on coroutine objects instead of Task objects. The tasks list contains coroutines created by calling the code, but asyncio.as_completed() wraps these in Tasks. When CancelledError is caught, the code incorrectly iterates over the original coroutines rather than the Task objects.

Evidence:
- File: src/vkdownloader/cli.py, lines 210-227
- mypy output: `src\vkdownloader\cli.py:223: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"` and `line 224: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "cancel"`

Recommendation: Wrap coroutines in tasks before the loop: `tasks = [asyncio.create_task(_limited_download(url)) for url in urls]`. Effort: small. Priority: recommended.

---

### CLI-002: Missing Trailing Newline in CLI Module

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by ruff W292 check. The file ends at line 258 with `app()` and no trailing newline.
> - **See also:** QLT-010 (duplicate)

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py |

Description: The CLI module file ends without a trailing newline.

Evidence:
- ruff output: W292 No newline at end of file

Recommendation: Add trailing newline. Effort: trivial.

---

### CLI-003: Unused Type Ignore Comments

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by mypy `unused-ignore` output. Lines 796 and 801 in downloader.py have `# type: ignore` comments that mypy reports as unused - the underlying type issues have been resolved.
> - **See also:** CFG-005, QLT-006 (duplicates)

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |

Description: Two type ignore comments on lines 796 and 801 are unused.

Evidence:
- mypy output: `Unused "type: ignore" comment at lines 796 and 801`

Recommendation: Remove unused comments. Effort: trivial.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | CLI-001, CLI-002, CLI-003 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

None. All findings in this phase are valid.

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| CFG-004 | CLI-001 (Phase 01) | Same mypy error in same code location |
| SRV-005 | CLI-001 (Phase 01) | Same mypy error in same code location |
| QLT-011 | CLI-001 (Phase 01) | Same mypy error in same code location |
| CFG-005 | CLI-003 (Phase 01) | Same unused type ignore comment location |
| QLT-006 | CLI-003 (Phase 01) | Same unused type ignore comment location |
| QLT-010 | CLI-002 (Phase 01) | Same missing newline issue |

### Reclassified Findings

None.

## Rollout Analysis

**No rollout safety issues detected within this phase.** The findings are isolated linting/type issues that do not affect architectural dependencies.

## Warnings

- **CFG-003** (Phase 02) / **SRV-001** (Phase 03) / **QLT-007** (Phase 08): Syntax error in `tests/test_hls_downloader_patch.py` blocks all test collection - affects test execution across all phases
- **QLT-001** (Phase 08): `print()` statements in CLI batch download (lines 215, 229, 231) violates project convention - uses print() instead of logger  
- **CFG-007** (Phase 02) / **SRV-002** (Phase 03): Global `_shutdown_event` causes event loop binding failures in tests - cross-phase architectural risk

## Required Fixes

- CLI-001: Type Safety Violation in Batch Download Task Cancellation (HIGH severity) - Critical bug that causes AttributeError on cancellation
- CLI-003: Unused Type Ignore Comments (LOW severity) - Clean up noise in code

## Advisory Recommendations

- CLI-002: Missing Trailing Newline in CLI Module (LOW severity) - Trivial cleanup