---
name: 05-audit-integrations-validated
description: Validated findings for Phase 05 — External Integrations
agent: validator
alwaysApply: false
---

# Phase 05 Audit Findings — External Integrations (Validated)

**Executor:** validator  
**Source:** /.ai/audit/05-audit-integrations/findings.md  
**Status:** validated  
**Validation Date:** 2026-07-20

---

## Runtime Verification Summary (Confirmed)

- **R1 — Import Verification:** PASS. All modules import cleanly.
- **R2 — Linter / Type Checker:**
  - `uv run ruff check src/vkdownloader` → exit 0, "All checks passed!".
  - `uv run ruff format --check src/vkdownloader` → **exit 1**, 2 files would be reformatted (`models/enums.py`, `services/signal_handlers.py`). Verified: both files have formatting issues.
  - `uv run mypy src/vkdownloader` → exit 0, "Success: no issues found in 23 source files".
- **R3 — Test Suite:** `uv run pytest tests -q` → **233 passed**.

---

## Findings

### INT-001: Browser interaction catches builtin `TimeoutError`, not Playwright's — click failure aborts extraction

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** `_simulate_video_interaction` wraps `await page.click(".VideoPlayer")` in `try/except TimeoutError` to make the click optional. However, the module imports only `from playwright.async_api import Cookie, Page` — so `TimeoutError` here resolves to the **builtin** `TimeoutError`. Playwright raises `playwright._impl._errors.TimeoutError`, which is NOT a subclass of the builtin. When the `.VideoPlayer` selector is not present (a normal case), `page.click` waits the default ~30s and then raises an **uncaught** Playwright `TimeoutError`.

**Evidence:**
- `extractor.py:271-275` — `except TimeoutError:` guards only the builtin.
- `extractor.py:6-7` — imports `Cookie, Page` only; no Playwright `TimeoutError` imported.
- Runtime verification: Playwright's TimeoutError MRO does not include `builtins.TimeoutError`; `issubclass(playwright.async_api.TimeoutError, builtins.TimeoutError) == False`.
- No test exercises this path (grep for `VideoPlayer`/`simulate_video_interaction` in `tests/` → no matches).

**Recommendation:** Import Playwright's error explicitly and catch it, optionally also with a short per-click timeout.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified the exception hierarchy; Playwright's TimeoutError is a separate class hierarchy. The finding is technically correct and represents a real bug. The code will crash on missing selector instead of handling gracefully.

---

### INT-002: `BrowserManager.__aexit__` leaks the Playwright driver if `browser.close()` raises

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | mandatory |

**Description:** Teardown runs `await self.browser.close()` and then `await self.playwright.stop()` sequentially with no `try/finally`. If `browser.close()` raises, `playwright.stop()` is never reached, leaking the Playwright driver node subprocess.

**Evidence:**
- `browser.py:56-59` — `__aexit__` calls `browser.close()` then `playwright.stop()` with no exception isolation.

**Recommendation:** Guarantee `playwright.stop()` runs regardless of `browser.close()` outcome.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified the code structure. The `__aexit__` method does not use try/finally to protect against `browser.close()` raising. This is a valid resource leak risk in batch scenarios.

---

### INT-003: Browser extraction errors are not wrapped; they escape uncaught on the resume path

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** `extract_streams` documents that it raises `ValueError`, `VideoNotFoundError`, or `ExtractionError`. The browser path `_extract_with_browser` calls `page.goto(url, ..., timeout=60000)` without wrapping failures. A `goto` timeout or Chromium launch failure propagates as a raw Playwright `TimeoutError`/`Error`. The token-refresh resume path `_attempt_segment_resume` only catches `(ExtractionError, OSError)` and `ValueError`, so these raw browser errors escape that handler.

**Evidence:**
- `extractor.py:211` — `await page.goto(...)` not wrapped in `ExtractionError`.
- `browser.py:38-41` — launch failure logged then re-raised as the raw exception.
- `downloader.py:554-558` — resume handler catches only `(ExtractionError, OSError)` / `ValueError`; Playwright errors not covered.

**Recommendation:** Wrap browser navigation and launch failures in `ExtractionError` so callers can handle a single documented error type.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified the exception flow. The documented contract in `extract_streams` docstring lists specific exception types, but browser operations can raise Playwright exceptions that are not caught. Also verified no integration of Playwright errors in the except clauses at `downloader.py:554-558`.

---

### INT-004: Graceful shutdown does not stop an in-progress yt-dlp download

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** yt-dlp runs synchronously inside a thread-pool executor. The wrapper `_download` checks `shutdown_event.is_set()` only **once, before** calling `ydl.download(...)`. Once the download starts, there is no hook to interrupt it.

**Evidence:**
- `downloader.py:598-614` — `_download` checks `shutdown_event` only at entry.
- `downloader.py:197-205` — `_progress_hook` reports progress but never inspects `shutdown_event`.
- `downloader.py:629-632` — comment confirms "the thread will continue".

**Recommendation:** Make the yt-dlp `progress_hook` raise when `shutdown_event.is_set()`.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified the code. The `_download` function checks the shutdown event only at the start (lines 600-601). The `_progress_hook` function (lines 197-205) does not check for interruption. The comment at lines 631-632 confirms the thread continues. This is a valid improvement opportunity.

---

### INT-005: ffmpeg subprocess can be orphaned when the download coroutine is cancelled

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `HLSDownloader.download_with_ffmpeg` spawns ffmpeg via `asyncio.create_subprocess_exec` and awaits `_await_first_and_cancel_others(...)`. Cleanup relies solely on `shutdown_event` being set. There is no `try/finally` guaranteeing the process is terminated.

**Evidence:**
- `downloader.py:328-332` — ffmpeg spawned; no surrounding `try/finally` to terminate it.
- `downloader.py:362-377` — termination only happens via `shutdown_event` branches.
- `downloader.py:80-102` — `_await_first_and_cancel_others` cancels pending tasks on normal completion but is itself cancellable.
- `cli.py:279-289` — batch cancels sibling tasks on the first `CancelledError`.

**Recommendation:** Wrap the ffmpeg lifecycle in `try/finally` and call `cancel_ffmpeg_process` in the finally.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified the code structure. In `download_with_ffmpeg`, there is no try/finally wrapping the subprocess lifecycle. The `shutdown_event.is_set()` check at line 374 only handles the shutdown case, not a plain `CancelledError`. This is a valid resource leak risk.

---

### INT-006: `ssl_verify=False` is silently ignored by the direct ffmpeg download path

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** The `--no-ssl-verify` setting is honored by the yt-dlp path (`nocheckcertificate`) and the aiohttp segment path (insecure `SSLContext`), but the direct ffmpeg path builds a command with no TLS-verification control. When a user selects `--method ffmpeg --no-ssl-verify`, the setting is silently dropped.

**Evidence:**
- `downloader.py:312-326` — ffmpeg command construction; no branch on `settings.ssl_verify`.
- `downloader.py:169` — yt-dlp `nocheckcertificate` is set.
- `segment_downloader.py:487-494` — `_create_connector` creates insecure context when `ssl_verify=False`.
- `docs/11-guides/vkdownloader-limitations.md:92` — confirms ffmpeg SSL option is invalid.

**Recommendation:** Emit an explicit warning when `ssl_verify=False` is combined with `--method ffmpeg`.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified all three code paths. The docs already document that ffmpeg's `-ssl_verification` option is invalid, but the code does not warn the user when they use the flag with the ffmpeg method. This is a genuine SPEC-DEVIATION: documented behavior (ssl_verify flag) does not match actual behavior for this code path.

---

### INT-007: Missing `ffmpeg` binary surfaces as an opaque error, and only after a full segment download

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** ffmpeg is invoked via `create_subprocess_exec("ffmpeg", ...)` with no pre-flight availability check. In the AUTO/segment path, segments are downloaded first and ffmpeg is only invoked at merge time.

**Evidence:**
- `downloader.py:313-332` — `"ffmpeg"` spawned directly, no existence check.
- `ffmpeg_utils.py:175-186` and `215-231` — batch/final merge spawn ffmpeg without checks.

**Recommendation:** Probe ffmpeg availability once at startup with `shutil.which("ffmpeg")`.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified the code. No pre-flight check exists. The `create_subprocess_exec` calls would raise `FileNotFoundError` if ffmpeg is absent. The merge operations in `ffmpeg_utils.py` would fail after segments are downloaded. This is a valid improvement for user experience.

---

### INT-008: NetworkMonitor bypasses its oversized-JSON guard when `Content-Length` is absent

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | advisory |

**Description:** `_intercept_response` guards against reading huge JSON bodies by checking the `content-length` header against a ~1MB threshold before calling `await response.json()`. When the header is missing (chunked/streamed responses), the guard is skipped entirely.

**Evidence:**
- `network_monitor.py:70-86` — the size guard only runs `if content_length is not None`; the `else` (missing header) falls straight through to `await response.json()`.

**Recommendation:** Enforce a byte cap even when `Content-Length` is absent.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified the code. When `content_length` is `None`, the code proceeds directly to `await response.json()` (line 85). The `else` branch from the `if content_length is not None` check (line 72) has no guard. This is a valid security/memory concern for untrusted responses.

---

### INT-009: `ruff format --check` fails on integration-teardown module (and enums)

| Field | Value |
|-------|-------|
| **ID** | INT-009 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/signal_handlers.py`, `src/vkdownloader/models/enums.py` |
| **Classification** | advisory |

**Description:** Runtime Verification step R2 recorded a non-zero exit from `uv run ruff format --check src/vkdownloader` (exit 1): two files would be reformatted. This indicates the file was edited without running the formatter.

**Evidence:**
- `uv run ruff format --check src/vkdownloader` → Confirms "Would reformat" for both files.
- Both files pass `ruff check` and `mypy`.

**Recommendation:** Run `uv run ruff format src/vkdownloader` to normalize the two files.

> **Validation Note:**  
> - **Action:** validated  
> - **Detail:** Verified: `signal_handlers.py` has a trailing blank line at end of file; `enums.py` has formatting issues. Both files are checked in without proper formatting. No CI format gate exists in `.github/workflows/` (only doc-lint.yml), but the finding correctly identifies a deviation from project formatting standards.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 9 | All findings INT-001 through INT-009 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

None. All findings were verified and retained.

### Merged Findings

None. No duplicate or overlapping findings detected.

### Reclassified Findings

None. All findings maintained their original classification:
- INT-001, INT-003, INT-006, INT-009 remained as their original types (RUNTIME-ERROR or SPEC-DEVIATION)
- INT-002, INT-004, INT-005, INT-007, INT-008 remained as BEST-PRACTICE (valid improvement opportunities)

---

## Rollout Analysis

### Dependency Chains

- **INT-001** and **INT-003** share the same root cause (Playwright exception handling). Fixing both requires importing and using Playwright's `TimeoutError` and `Error` types consistently. INT-003 is blocked until INT-001 is addressed, as the exception type integration needs to be consistent.
- **INT-002** is independent of other findings.
- **INT-004** and **INT-005** are independent but related to shutdown/event handling patterns.
- **INT-009** (formatting) should be applied first as it has no runtime risk and establishes clean baseline.

### Safe Sequencing

1. **INT-009** (formatting) — No risk, can be done first.
2. **INT-001** and **INT-003** — Related; should be fixed together to establish consistent exception handling.
3. **INT-002** — Can be done independently.
4. **INT-004**, **INT-005**, **INT-007** — Independent cleanup improvements.
5. **INT-006** — Documentation/warning addition; low risk.
6. **INT-008** — Security hardening; moderate risk due to potential impact on interception behavior.

---

## Warnings

| Category | Finding | Details |
|----------|---------|---------|
| Resource Leak | INT-002, INT-005 | `playwright.stop()` and ffmpeg processes can be orphaned in batch scenarios |
| UX/Crash Risk | INT-001, INT-003 | Uncaught Playwright exceptions abort downloads with opaque tracebacks |
| Memory Safety | INT-008 | Unbounded JSON parsing on chunked responses |
| Startup Reliability | INT-007 | ffmpeg availability not verified before download begins |
| Silent Misconfiguration | INT-006 | `--no-ssl-verify` flag ignored silently with `--method ffmpeg` |

---

## Required Fixes

- **INT-001 (HIGH)** — Browser click guards the wrong `TimeoutError`; Playwright click timeouts escape uncaught and abort extraction.
- **INT-002 (MEDIUM)** — `BrowserManager.__aexit__` leaks the Playwright driver if `browser.close()` raises.
- **INT-003 (MEDIUM)** — Browser navigation/launch errors are not wrapped as `ExtractionError` and escape the resume-path handler.

---

## Advisory Recommendations

- **INT-004 (MEDIUM)** — Graceful shutdown does not stop an in-progress yt-dlp download.
- **INT-005 (MEDIUM)** — ffmpeg subprocess can be orphaned on coroutine cancellation without `shutdown_event`.
- **INT-006 (LOW)** — `ssl_verify=False` silently ignored by the direct ffmpeg path; emit warning.
- **INT-007 (LOW)** — Missing ffmpeg binary yields opaque error after full segment download.
- **INT-008 (LOW)** — NetworkMonitor oversized-JSON guard bypassed for chunked responses.
- **INT-009 (LOW)** — Run `ruff format` on `signal_handlers.py` and `enums.py`.