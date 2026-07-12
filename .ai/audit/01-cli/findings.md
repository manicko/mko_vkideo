---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 01 Audit Findings - CLI Entry Point & Command Layer

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### CLI-001: Type Safety Violation in Batch Download Task Cancellation

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | mandatory |

Description: In the batch download function the code attempts to call .done() and .cancel() methods on coroutine objects instead of Task objects. The tasks list contains coroutines created by calling the code, but asyncio.as_completed() wraps these in Tasks. When CancelledError is caught, the code incorrectly iterates over the original coroutines rather than the Task objects.

Evidence:
- File: src/vkdownloader/cli.py, lines 210-227
- mypy output: lines 223 and 224: Coroutine attribute errors

Recommendation: Wrap coroutines in tasks before the loop: tasks = [asyncio.create_task(_limited_download(url)) for url in urls]. Effort: small. Priority: recommended.

---

### CLI-002: Missing Trailing Newline in CLI Module

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

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |

Description: Two type ignore comments on lines 796 and 801 are unused.

Evidence:
- mypy output: Unused type: ignore comment at lines 796 and 801

Recommendation: Remove unused comments. Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 0 |
| LOW | 2 |

## Mandatory Fixes

- CLI-001: Type Safety Violation in Batch Download Task Cancellation (HIGH severity)

## Advisory Recommendations

- CLI-002: Missing Trailing Newline in CLI Module (LOW severity)
- CLI-003: Unused Type Ignore Comments (LOW severity)
