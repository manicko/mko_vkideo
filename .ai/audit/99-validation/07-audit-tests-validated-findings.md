---
name: audit-findings-validated
description: Validated findings report for test quality audit phase
agent: validator
alwaysApply: false
---

# Phase 07 Audit Findings — Test Quality (Validated)

**Executor:** validator  
**Source:** `.ai/audit/07-audit-tests/findings.md`  
**Validation Date:** 2026-07-20

---

## Findings

### TST-001: ~~Resume/fallback decision tree in `download_with_ytdlp_with_resume_fallback` is entirely untested~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Rejection reason:** The finding's evidence is **partially incorrect**. The `_attempt_segment_resume` function is imported into `downloader.py` but is NOT re-exported in `__all__` (lines 207-231). The function is a private implementation detail called internally. While `download_with_ytdlp_with_resume_fallback` itself is only mocked at one location (test_hls_downloader.py:973), the actual download retry logic is covered through `_download_segment_sequential` tests (lines 1366-1462) which call `_retry_429_with_backoff` directly. The partial file detection logic (lines 413-415) is a valid coverage gap, but the severity is overstated since the test suite already covers the component functions.

### TST-002: `perform_download` orchestration (method dispatch + FFMPEG→segment fallback) lacks behavioral tests

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated (unchanged)
> - **Detail:** Confirmed the `perform_download` tests in `TestDownloadMethodLogging` (lines 948-1132) only mock the download functions and assert log message content without verifying branch logic. The FFMPEG fallback to segment download (lines 742-757) is not covered by tests that let `download_with_ffmpeg` return `None`.
> - **See also:** TST-001 (related to the same code path)

### TST-003: `test_structured_logging_on_retry` does not verify the logging it claims to test

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated (unchanged)
> - **Detail:** Confirmed. The test name promises structured logging verification but contains no `mock_logger.warning`/`mock_logger.info` spy setup. The sole assertion `assert result == b"segment content"` cannot fail regardless of whether structured logging exists (valid side effect mock returns the value regardless). The sibling `test_structured_logging_on_non_retryable` properly verifies logging assertions (lines 425-457).

### TST-004: `test_delay_capped_at_30_seconds` asserts nothing about the cap it claims to verify

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated (unchanged)
> - **Detail:** Confirmed. This test (lines 337-378) only asserts `result == b"segment content"` with no check on delay/cap behavior. The actual cap IS verified in `TestComputeBackoffDelay.test_delay_caps_at_30_seconds` (lines 564-573). The test is redundant and misleading.

### TST-005: Misleadingly named `test_empty_path_rejected` actually accepts the path

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated (unchanged)
> - **Detail:** Confirmed. The test at test_security.py:81-88 is named `test_empty_path_rejected` but asserts `result == Path.cwd()` without `pytest.raises`. The code in `validate_output_path` (security.py:23-62) correctly resolves `Path(".")` to cwd without raising. The test name is misleading but the behavior is intentional (accepts "." as current directory).

### TST-006: Coverage gap — `_sanitize_title` (Windows filename safety) has no tests

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated (unchanged)
> - **Detail:** Confirmed. The `_sanitize_title` function (security.py:12-20) is exported in `utils/__init__.py` but grep for `_sanitize_title` in `tests/` returns no matches. This is a pure function with deterministic behavior that is cheap to test and important for Windows filename safety.

### TST-007: Coverage gap — `_fetch_playlist_with_retry` token-refresh logic never executed

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated (unchanged)
> - **Detail:** Confirmed. All 9 references to `_fetch_playlist_with_retry` in tests are mock patches returning static values. The function (segment_downloader.py:433-467) implements token refresh on HTTP 403/410 with retry loop, which is never verified. This is a valid coverage gap for production error handling.

### TST-008: Coverage gap — `setup_signal_handlers` and `_resolve_cookies` untested

| Field | Value |
|-------|-------|
| **ID** | TST-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated (unchanged)
> - **Detail:** Confirmed. `setup_signal_handlers` (signal_handlers.py) has Windows-specific signal handler fallback logic (lines 44-53) that is never exercised. `_resolve_cookies` (downloader.py:609-655) has cookie-source branching and `QualityNotAvailableError` propagation with no direct tests. These rely on indirect CLI coverage only.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 7 | TST-002, TST-003, TST-004, TST-005, TST-006, TST-007, TST-008 |
| Rejected | 1 | TST-001 |
| Merged | 0 | — |
| Reclassified | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| TST-001 | Resume/fallback decision tree in `download_with_ytdlp_with_resume_fallback` is entirely untested | Evidence partially incorrect: `_attempt_segment_resume` is private and not exported; the component functions it calls ARE tested through other test classes; the gap exists but is less severe than claimed |

### Merged Findings

None.

### Reclassified Findings

None.

---

## Rollout Analysis

No rollout risks identified. These are test coverage gaps only - no production code modifications required.

---

## Execution Validation

All findings relate to test suite gaps, not production code defects. The existing tests pass and provide reasonable coverage of core functionality. Adding the recommended tests would improve maintainability but is not urgent.