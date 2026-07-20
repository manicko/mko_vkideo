# Phase 05 Audit Findings - External Integrations (Validated)

**Executor:** auditor -> validator
**Template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** yes

---

## Findings

### INT-001: BrowserManager leaks the Playwright subprocess when launch fails in `__aenter__`

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | mandatory (resource lifecycle) |

**Description:** `BrowserManager.__aenter__` (browser.py:28-39) assigns `self.playwright` and then calls `self.browser = await playwright_instance.chromium.launch(...)`. If `chromium.launch()` raises, `__aexit__` is never called and the orphaned Playwright subprocess is leaked.

> **Validation Note:** Action: validated. Code vulnerable to resource leaks on launch failure.

### INT-002: Playwright browser is not stopped on interruption mid-extraction

> **Validation Note:** Action: validated. Signal handler only sets event, no cancellation mechanism.

### INT-003: Spec deviation - auto + cookie_source=BROWSER launches the browser

> **Validation Note:** Action: validated. Documentation states No browser involvement but code launches browser.

### INT-004: CookieSource.FILE is documented as not implemented

> **Validation Note:** Action: validated. Correctly classified per dead-code policy.

### INT-005: Parallel segment download has hardcoded retry sleep

> **Validation Note:** Action: validated. Uses asyncio.sleep(1.0) instead of proper backoff.

### INT-006: `_fetch_single_playlist` swallows asyncio.CancelledError

> **Validation Note:** Action: validated. CancelledError should propagate.

### INT-007: NetworkMonitor intercepts all video JSON responses

> **Validation Note:** Action: validated. Broad matching with no size guard.

### INT-008: download_timeout semantics unclear

> **Validation Note:** Action: validated. Single timeout field used inconsistently.

### INT-009: cancel_ffmpeg_process result ignored

> **Validation Note:** Action: validated. Return value discarded, potential stderr truncation.

### INT-010: Segment merge leaves partial files on failure

> **Validation Note:** Action: validated. FileNotFoundError raised, temp files not cleaned.

---

## Validation Summary

| Action | Count |
|--------|-------|
| Validated | 10 |
| Rejected | 0 |
| Merged | 0 |
| Reclassified | 0 |

## Rollout Analysis

INT-001 before INT-002. INT-002 and INT-006 relate to shutdown. INT-005 and INT-008 involve backoff. INT-009 and INT-010 affect temp cleanup.

## Execution Validation

All findings verified. Codebase passes ruff and mypy. Tests pass.