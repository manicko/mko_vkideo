---
name: audit-findings
description: Structured findings template for audit phase output
agent: auditor
alwaysApply: false
---

# Phase 07 Audit Findings — Test Quality

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/07-audit-tests.md
**Status:** complete
**Validated:** no

---

## Findings

### TST-001: Resume/fallback decision tree in `download_with_ytdlp_with_resume_fallback` is entirely untested

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`download_with_ytdlp_with_resume_fallback`, `_attempt_segment_resume`) |
| **Classification** | advisory |

**Description:** The most complex and bug-prone code path — the yt-dlp failure → token refresh → segment-resume fallback — has no direct test. `download_with_ytdlp_with_resume_fallback` (downloader.py:358-437) contains the partial-file detection (`validated_output.exists()` / `st_size == 0`, lines 413-415), the `MAX_RESUME_RETRIES` retry loop, and the call to `_attempt_segment_resume` (440-528) which forces browser extraction and switches to `download_hls_with_resume`. Every test that touches this path (test_cli.py, test_hls_downloader.py `TestDownloadMethodLogging`) either mocks `perform_download` outright or mocks `download_with_ytdlp_with_resume_fallback` (test_hls_downloader.py:973). The actual branch logic is never executed.

**Evidence:**
- `tests/test_cli.py:33` patches `perform_download` as `mock_download` → CLI never reaches the fallback.
- `tests/test_hls_downloader.py:973,1120` patch `download_with_ytdlp_with_resume_fallback` as a Mock; assertions only check `result == output_file` and that `logger.info` was captured.
- grep for `download_with_ytdlp_with_resume_fallback` / `_attempt_segment_resume` / `MAX_RESUME_RETRIES` in `tests/` returns only mock patches — no behavioral test.
- Source logic that is unverified: downloader.py:414-415 (returns `None` when no partial file), 418-433 (segment resume branch), 505-506 (`output_file.unlink()` before segment download).

**Recommendation:** Add a behavioral test for `download_with_ytdlp_with_resume_fallback` that exercises at least: (a) yt-dlp success returns file with zero retries; (b) yt-dlp failure with a non-empty partial file triggers `_attempt_segment_resume`; (c) yt-dlp failure with zero-byte/empty partial file returns `None` immediately. This is the path most likely to silently corrupt downloads in production.

---

### TST-002: `perform_download` orchestration (method dispatch + FFMPEG→segment fallback) lacks behavioral tests

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download`, lines 658-777) |
| **Classification** | advisory |

**Description:** `perform_download` is the central entry point used by the CLI/commands layer for both download methods. The `DownloadMethod.AUTO`, `DownloadMethod.FFMPEG`, and the FFMPEG-failure→`download_hls_with_resume` fallback (downloader.py:736-758) are never exercised end-to-end. The only `perform_download` tests in `test_hls_downloader.py::TestDownloadMethodLogging` mock `extract_streams`/`download_with_ytdlp_with_resume_fallback`/`download_with_ffmpeg` and only assert log emission (`starting_download` with `method=...`). They cannot catch regressions in method dispatch, cookie resolution, or the fallback switch.

**Evidence:**
- `tests/test_hls_downloader.py:948-1132` — `TestDownloadMethodLogging`: all three `perform_download` tests stub the real download functions and assert only `len(starting_logs) >= 1` with `kwargs.get("method")`. No assertion on returned path correctness, no branch coverage of `match method` cases.
- `perform_download` `FFMPEG` case fallback to segment download (downloader.py:742-757) is never covered by any test that lets `download_with_ffmpeg` return `None`.

**Recommendation:** Add tests that drive `perform_download` with a real (mocked-at-boundary) extractor and let the download functions return realistic values, asserting the dispatched method and fallback behavior (`FFMPEG` returning `None` → segment path is invoked).

---

### TST-003: `test_structured_logging_on_retry` does not verify the logging it claims to test

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_downloader_throttle.py:379-422` |
| **Classification** | advisory |

**Description:** The test name and intent is to verify structured logging on retry, but it mocks `_strip_auth_params` and then asserts only `result == b"segment content"` — a value already guaranteed by the local `get_side_effect` mock. The only comment about logging, `# Verify structured logging was verified in separate test` (line 422), concedes that no logging assertion is performed here. The test therefore cannot fail whether or not the structured logging exists, giving a false sense of coverage for an audit-related (security/logging) behavior.

**Evidence:**
- `tests/test_downloader_throttle.py:379-422`: no `mock_logger.warning`/`mock_logger.info` spy is set up and no `assert_called` on any logger. The sole assertion is `assert result == b"segment content"`.

**Recommendation:** Either add a real logger assertion (spy on `vkdownloader.services.downloader_throttle.logger` and check the `attempt`/`status`/`segment_index`/`url` structured fields as the sibling `test_structured_logging_on_non_retryable` does), or rename the test to reflect that it only checks the return value and remove the misleading comment.

---

### TST-004: `test_delay_capped_at_30_seconds` asserts nothing about the cap it claims to verify

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_downloader_throttle.py:337-378` |
| **Classification** | advisory |

**Description:** This test is titled "Test delay is capped at 30 seconds maximum" but contains no assertion about the 30-second cap. It only asserts the result equals the downloaded content and a comment explains the delay math (lines 376-377). The actual cap is verified elsewhere (`TestComputeBackoffDelay.test_delay_caps_at_30_seconds`), so this test is redundant and misleading — it passes regardless of whether the cap logic is correct.

**Evidence:**
- `tests/test_downloader_throttle.py:337-378`: body has only `assert result == b"segment content"` plus explanatory comments; no check on delay/cap behavior.

**Recommendation:** Remove this redundant test or convert it into a genuine assertion of the retry-timing behavior (e.g., spy on the sleep/wait delay and confirm it stays within bounds after N retries).

---

### TST-005: Misleadingly named `test_empty_path_rejected` actually accepts the path

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_security.py:81-88` (`test_empty_path_rejected`) |
| **Classification** | advisory |

**Description:** The test name says "rejected" but the body asserts the path is accepted: `result == Path.cwd()` with no `pytest.raises`. This contradicts the security intent implied by the name and can mislead a maintainer into thinking `Path(".")` is blocked. The behavior itself (accepting `.`) may be intentional, but the name creates a false sense of safety.

**Evidence:**
- `tests/test_security.py:81-88`: `def test_empty_path_rejected(self) -> None:` followed by `result = validate_output_path(path); assert result == Path.cwd()` (no raise). Confirmed against `src/vkdownloader/utils/security.py:23-62` where `Path(".")` resolves to cwd and has no `".."`, so it is accepted.

**Recommendation:** Rename to `test_empty_path_accepted_resolves_to_cwd` (or similar) to reflect actual behavior, or add an explicit comment clarifying that `.` is a permitted current-directory target.

---

### TST-006: Coverage gap — `_sanitize_title` (Windows filename safety) has no tests

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/utils/security.py:12-20` (`_sanitize_title`); exported in `src/vkdownloader/utils/__init__.py:3,6` |
| **Classification** | advisory |

**Description:** `_sanitize_title` sanitizes video titles for filesystem safety by replacing Windows/Unix-invalid characters (`/ \ : * ? " < > |`), stripping whitespace, and capping to 100 chars. This is exported as part of the public `utils` API and is a correctness concern on Windows (the project's target OS). It has zero tests. A regression here (e.g., failing to strip a colon or truncating incorrectly) would silently produce invalid/overlong filenames.

**Evidence:**
- `src/vkdownloader/utils/security.py:12-20` defines the function; `src/vkdownloader/utils/__init__.py:3,6` exports it.
- grep for `_sanitize_title` across `tests/` returns no matches.

**Recommendation:** Add unit tests for `_sanitize_title` covering: invalid-char replacement, whitespace strip, and the 100-char cap. These are pure, fast, deterministic functions and cheap to cover.

---

### TST-007: Coverage gap — `_fetch_playlist_with_retry` token-refresh logic never executed

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py:433-467` (`_fetch_playlist_with_retry`) |
| **Classification** | advisory |

**Description:** `_fetch_playlist_with_retry` implements the m3u8 fetch with token refresh on HTTP 403/410 (retrying with a fresh URL from `_handle_token_refresh`) and returns `None` on unrecoverable errors. In every test it is mocked (`tests/test_hls_downloader.py` lines 239, 271, 510, 554, 608, 763, 828, 910, 1003). The real retry loop, the 403/410-refresh branch, and the final-`None` fallback are never verified, so a break in token refresh would not be caught by the suite.

**Evidence:**
- All 9 references in `tests/` are `patch("vkdownloader.services.segment_downloader._fetch_playlist_with_retry", return_value=...)`. No test calls the real function with a mocked `aiohttp` session.

**Recommendation:** Add at least one behavioral test using a mocked `aiohttp.ClientSession` that covers: (a) 200 returns playlist text; (b) 403 then refreshed-200 returns text; (c) persistent 403/410 with no extractor returns `None`.

---

### TST-008: Coverage gap — `setup_signal_handlers` and `_resolve_cookies` untested

| Field | Value |
|-------|-------|
| **ID** | TST-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/signal_handlers.py` (`setup_signal_handlers`); `src/vkdownloader/services/downloader.py:609-655` (`_resolve_cookies`) |
| **Classification** | advisory |

**Description:** `setup_signal_handlers` (graceful SIGINT/SIGTERM shutdown, including the Windows `signal.signal` fallback — directly relevant on the project's Windows target) has no test. `_resolve_cookies` (cookie-source branching, quality selection from browser streams, `QualityNotAvailableError` propagation) also has no direct test. Both are non-trivial control-flow paths that currently rely on indirect CLI coverage only.

**Evidence:**
- grep for `setup_signal_handlers` / `_resolve_cookies` in `tests/` returns no behavioral tests (only CLI mocks of `perform_download`).
- `signal_handlers.py` is a standalone module with a documented Windows-specific branch (lines 45-53) that is never exercised.

**Recommendation:** Add a test for `_resolve_cookies` (NONE vs BROWSER sources, `QualityNotAvailableError` raise) and a guarded test for `setup_signal_handlers` that confirms idempotent registration and that it sets the shutdown event on signal. Mark the signal test to skip on platforms/builds where signal handlers cannot be installed.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 3 |

## Mandatory Fixes

None. No failing tests, no production bugs surfaced directly by the suite, and no security/data-loss defect was identified in the tests themselves.

## Advisory Recommendations

- TST-001 (HIGH): Add behavioral tests for the yt-dlp→segment resume fallback.
- TST-002 (MEDIUM): Add behavioral tests for `perform_download` dispatch and FFMPEG→segment fallback.
- TST-003 (MEDIUM): Make `test_structured_logging_on_retry` actually assert logging.
- TST-004 (LOW): Remove or fix the no-op `test_delay_capped_at_30_seconds`.
- TST-005 (LOW): Rename `test_empty_path_rejected` to reflect accepted behavior.
- TST-006 (MEDIUM): Add tests for `_sanitize_title` (Windows filename safety).
- TST-007 (MEDIUM): Add behavioral tests for `_fetch_playlist_with_retry` token refresh.
- TST-008 (LOW): Add tests for `setup_signal_handlers` (Windows fallback) and `_resolve_cookies`.

## Doc Updates Needed

None.
