# Phase 05 Audit Findings - External Integrations (Validated)

**Executor:** auditor -> validator
**Template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** yes

---

## Findings

### INT-001: BrowserManager leaks the Playwright subprocess when launch fails in __aenter__

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/infrastructure/browser.py |
| **Classification** | mandatory (resource lifecycle) |

**Description:** BrowserManager.__aenter__ (browser.py:28-39) assigns self.playwright and then calls self.browser = await playwright_instance.chromium.launch(...). If chromium.launch() raises, __aexit__ is never called and the orphaned Playwright subprocess is leaked.

> **Validation Note:** Action: validated. Code vulnerable to resource leaks on launch failure.

**Recommendation:** In browser.py:__aenter__, wrap the launch call in try/except and call await playwright_instance.stop() on failure before re-raising. Assign to local variable first, then assign to self after successful launch.

### INT-002: Playwright browser is not stopped on interruption mid-extraction

> **Validation Note:** Action: validated. Signal handler only sets event, no cancellation mechanism.

**Recommendation:** In extractor.py:_extract_with_browser (lines 195-232), add shutdown event check after browser_pre_interaction_wait and browser_post_interaction_wait sleeps (lines 208, 210). Call raise asyncio.CancelledError() when shutdown is detected. The BrowserManager context manager will then cleanly close the browser.

### INT-003: Spec deviation - auto + cookie_source=BROWSER launches the browser

> **Validation Note:** Action: validated. Documentation states No browser involvement but code launches browser.

**Recommendation:** In downloader.py:perform_download (lines 759-774), change the AUTO case to skip _resolve_cookies when settings.cookie_source == CookieSource.NONE. This aligns with documented behavior that auto mode with cookie_source=none should not involve the browser.

### INT-004: CookieSource.FILE is documented as not implemented

> **Validation Note:** Action: validated. Correctly classified per dead-code policy.

**Recommendation:** Add a field_validator in config.py (after line 114) that rejects CookieSource.FILE values at configuration time. This resolves INT-004 together with CFG-001/SEC-002 by failing fast during Settings initialization.

**Note:** This finding is resolved together with CFG-001/SEC-002 via a config.py field_validator.

### INT-005: Parallel segment download has hardcoded retry sleep

> **Validation Note:** Action: validated. Uses asyncio.sleep(1.0) instead of proper backoff.

**Recommendation:** In segment_downloader.py:_run_parallel_download_with_backoff (lines 139-169), replace the hardcoded await asyncio.sleep(1.0) at line 165 with exponential backoff using _compute_backoff_delay from downloader_throttle.py.

### INT-006: _fetch_single_playlist swallows asyncio.CancelledError

> **Validation Note:** Action: validated. CancelledError should propagate.

**Recommendation:** In segment_downloader.py:_fetch_single_playlist (lines 398-412), remove asyncio.CancelledError from the caught exception tuple at line 410. Let CancelledError propagate naturally.

### INT-007: NetworkMonitor intercepts all video JSON responses

> **Validation Note:** Action: validated. Broad matching with no size guard.

**Recommendation:** In network_monitor.py:_intercept_response (lines 51-85), add a size guard before reading JSON body: check that content-length is under 1MB before calling response.json().

### INT-008: download_timeout semantics unclear

> **Validation Note:** Action: validated. Single timeout field used inconsistently.

**Recommendation:** In config.py (line 41-46), add a clear docstring to download_timeout field: description=HTTP client timeout in seconds for individual segment requests and playlist fetches.

### INT-009: cancel_ffmpeg_process result ignored

> **Validation Note:** Action: validated. Return value discarded, potential stderr truncation.

**Recommendation:** In downloader.py:HLSDownloader.download_with_ffmpeg (lines 314-315 and 324-325), capture the return value of cancel_ffmpeg_process and log if the process did not terminate cleanly.

### INT-010: Segment merge leaves partial files on failure

> **Validation Note:** Action: validated. FileNotFoundError raised, temp files not cleaned.

**Recommendation:** In ffmpeg_utils.py:_merge_segments_batched (lines 236-271), wrap the merge loop in try/finally to clean up partial temp files on any failure.

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
