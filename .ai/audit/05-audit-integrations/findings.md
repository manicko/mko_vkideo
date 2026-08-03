---
name: audit-findings
description: Structured findings for Phase 05 — External Integrations
agent: auditor
alwaysApply: false
---

# Phase 05 Audit Findings — External Integrations

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

- **R1 — Import Verification:** PASS. All integration modules and the CLI entry point
  import cleanly (`vkdownloader.cli`, `services.downloader`, `services.extractor`,
  `infrastructure.browser`, `infrastructure.network_monitor`, `services.segment_downloader`,
  `services.ffmpeg_utils`, `services.cookies`, `services.downloader_throttle`) → `IMPORTS_OK`.
- **R2 — Linter / Type Checker:**
  - `uv run ruff check src/vkdownloader` → exit 0, "All checks passed!".
  - `uv run ruff format --check src/vkdownloader` → **exit 1**, 2 files would be reformatted
    (`models/enums.py`, `services/signal_handlers.py`). See INT-009.
  - `uv run mypy src/vkdownloader` → exit 0, "Success: no issues found in 23 source files".
- **R3 — Test Suite:** `uv run pytest tests -q` → **233 passed** in ~15s.

External integrations discovered: Playwright (Chromium browser automation + network
interception), yt-dlp (stream extraction + download), ffmpeg (HLS→MP4 mux + segment
concat, via `create_subprocess_exec`), aiohttp (HLS segment/playlist HTTP), VK CDN
(signed m3u8 URLs), and browser-captured cookies/session credentials.

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

**Description:** `_simulate_video_interaction` wraps `await page.click(".VideoPlayer")`
in `try/except TimeoutError` to make the click optional. However, the module imports
only `from playwright.async_api import Cookie, Page` — so `TimeoutError` here resolves
to the **builtin** `TimeoutError`. Playwright raises `playwright._impl._errors.TimeoutError`,
which is NOT a subclass of the builtin (`issubclass(...) == False`). When the
`.VideoPlayer` selector is not present (a normal case: VK markup changes, slow load,
or different player), `page.click` waits the default ~30s and then raises an **uncaught**
Playwright `TimeoutError`. That propagates out of `_simulate_video_interaction` →
`_extract_with_browser` → aborting the entire browser extraction, instead of being
logged and skipped as the code intends.

**Evidence:**
- `extractor.py:256-275` — `except TimeoutError:` guards only the builtin.
- `extractor.py:6-7` — imports `Cookie, Page` only; no Playwright `TimeoutError` imported.
- Runtime check: `playwright.async_api.TimeoutError` MRO = `['TimeoutError','Error','Exception','BaseException','object']`; `issubclass(p.TimeoutError, builtins.TimeoutError) == False`.
- No test exercises this path (grep for `VideoPlayer`/`simulate_video_interaction` in `tests/` → no matches), so the defect is invisible to the suite.

**Recommendation:** Import Playwright's error explicitly
(`from playwright.async_api import TimeoutError as PlaywrightTimeoutError`) and catch it
(optionally also `Error`) so the click stays best-effort. Consider a short per-click
timeout (e.g. `page.click(..., timeout=...)`) so a missing selector does not stall
extraction for the full default timeout. Add a regression test that raises the
Playwright timeout from a mocked `page.click`.

---

### INT-002: `BrowserManager.__aexit__` leaks the Playwright driver if `browser.close()` raises

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | mandatory |

**Description:** Teardown runs `await self.browser.close()` and then
`await self.playwright.stop()` sequentially with no `try/finally`. If `browser.close()`
raises (common when Chromium already crashed, was killed, or the connection dropped),
`playwright.stop()` is never reached, leaking the Playwright driver node subprocess and
its pipes for the lifetime of the process. In batch mode this can accumulate multiple
orphaned driver processes.

**Evidence:**
- `browser.py:47-59` — `__aexit__` calls `browser.close()` then `playwright.stop()` with
  no exception isolation between them.

**Recommendation:** Guarantee `playwright.stop()` runs regardless of `browser.close()`
outcome, e.g. wrap `browser.close()` in `try/finally` (or suppress-and-log its error)
so the driver is always stopped on every exit path.

---

### INT-003: Browser extraction errors are not wrapped; they escape uncaught on the resume path

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** `extract_streams` documents that it raises `ValueError`,
`VideoNotFoundError`, or `ExtractionError`. The browser path `_extract_with_browser`
calls `page.goto(url, ..., timeout=60000)` and browser launch (`BrowserManager.__aenter__`)
without wrapping their failures. A `goto` timeout or a Chromium launch failure therefore
propagates as a raw Playwright `TimeoutError`/`Error`. The token-refresh resume path
`_attempt_segment_resume` only catches `(ExtractionError, OSError)` and `ValueError`, so
these raw browser errors escape that handler and abort the whole download unit (and, in
batch, are re-raised through `_download_single`'s generic handler). The boundary check
"startup failure is reported clearly, app does not crash with an opaque traceback" is not met.

**Evidence:**
- `extractor.py:211` — `await page.goto(...)` not wrapped in `ExtractionError`.
- `browser.py:38-41` — launch failure logged then re-raised as the raw exception.
- `downloader.py:554-558` — resume handler catches only `(ExtractionError, OSError)` / `ValueError`;
  Playwright `TimeoutError`/`Error` are not covered.

**Recommendation:** Wrap browser navigation and launch failures in `ExtractionError`
(preserving `__cause__`) so callers can handle a single documented error type, and/or
broaden the resume-path `except` to include the Playwright error base class. Ensure the
user sees a clear "could not reach VK / browser failed" message rather than a traceback.

---

### INT-004: Graceful shutdown does not stop an in-progress yt-dlp download

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** yt-dlp (the default `AUTO` method) runs synchronously inside a thread-pool
executor. The wrapper `_download` checks `shutdown_event.is_set()` only **once, before**
calling `ydl.download(...)`; the yt-dlp `progress_hooks` callback built in
`_build_ytdlp_options` does not check the shutdown event either. Once the download starts,
there is no hook to interrupt it. On Ctrl+C / SIGTERM the signal handler sets
`shutdown_event` and `asyncio.run` cancels the awaiting coroutine (the executor future is
cancelled), but the underlying thread keeps running yt-dlp to completion — network transfer
and disk writes continue after the CLI reports "cancelled". The code comment at
`downloader.py:631-632` acknowledges "the thread will continue", confirming the gap.

**Evidence:**
- `downloader.py:598-614` — `_download` checks `shutdown_event` only at entry; `ydl.download()`
  has no interruption path.
- `downloader.py:197-205` — `_progress_hook` reports progress but never inspects `shutdown_event`.
- `downloader.py:629-635` — on `CancelledError` only the future is cancelled; comment notes the
  thread continues until process exit.

**Recommendation:** Make the yt-dlp `progress_hook` raise (e.g. a `DownloadCancelled`) when
`shutdown_event.is_set()`, so yt-dlp aborts promptly on Ctrl+C. This is the standard yt-dlp
cancellation idiom and turns graceful shutdown into an actual stop rather than a detach.

---

### INT-005: ffmpeg subprocess can be orphaned when the download coroutine is cancelled

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `HLSDownloader.download_with_ffmpeg` spawns ffmpeg via
`asyncio.create_subprocess_exec` and then awaits `_await_first_and_cancel_others(...)`.
Cleanup of the ffmpeg child relies solely on `shutdown_event` being set (checked inside the
monitor/drain loops). There is no `try/finally` guaranteeing the process is terminated. If
the coroutine is cancelled **without** the shutdown event being set — e.g. the batch runner
cancels sibling tasks in `_run_batch_with_progress` / `_download_single` after another task
raises — the `CancelledError` unwinds through `asyncio.wait`, but the created `process.wait()`
and monitor/drain tasks are not cancelled and the ffmpeg child keeps running, orphaned.

**Evidence:**
- `downloader.py:328-332` — ffmpeg spawned; no surrounding `try/finally` to terminate it.
- `downloader.py:362-377` — termination only happens via the `shutdown_event` branches; a plain
  `CancelledError` leaves `cancel_ffmpeg_process` uncalled.
- `downloader.py:80-102` — `_await_first_and_cancel_others` cancels *pending* tasks on normal
  completion but is itself cancellable, leaving the subprocess untouched.
- `cli.py:279-289` — batch cancels sibling tasks on the first `CancelledError`, the trigger path.

**Recommendation:** Wrap the ffmpeg lifecycle in `try/finally` and call
`cancel_ffmpeg_process(process)` in the `finally` (and on `CancelledError`) so the child is
always terminated on every exit path, not only when `shutdown_event` is set.

---

### INT-006: `ssl_verify=False` is silently ignored by the direct ffmpeg download path

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** The `--no-ssl-verify` / `settings.ssl_verify=False` setting is honored by the
yt-dlp path (`nocheckcertificate`) and the aiohttp segment path (insecure `SSLContext`), but
the direct ffmpeg path `download_with_ffmpeg` builds an ffmpeg command that contains no
TLS-verification control at all. When a user selects `--method ffmpeg --no-ssl-verify`, the
setting is silently dropped and ffmpeg still verifies TLS — with no warning that the flag is
ineffective. The project's own docs (`docs/11-guides/vkdownloader-limitations.md:92`) note
that ffmpeg's `-ssl_verification` option is invalid, so the field genuinely cannot be applied,
but the code neither warns nor documents this at the call site.

**Evidence:**
- `downloader.py:312-326` — ffmpeg command construction; no branch on `settings.ssl_verify`.
- Contrast: `downloader.py:169` (yt-dlp `nocheckcertificate`) and
  `segment_downloader.py:487-494` (`_create_connector` insecure context) both consume the flag.
- `docs/11-guides/vkdownloader-limitations.md:92` — confirms ffmpeg SSL option is invalid.

**Recommendation:** Emit an explicit warning when `ssl_verify=False` is combined with
`--method ffmpeg` (the flag has no effect for that path), and document the limitation next to
the `ssl_verify` setting so the config-to-integration contract is honest.

---

### INT-007: Missing `ffmpeg` binary surfaces as an opaque error, and only after a full segment download

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** ffmpeg is a required external binary (per
`docs/01-tools/installation.md`) but is invoked via `create_subprocess_exec("ffmpeg", ...)`
with no pre-flight availability check. If ffmpeg is absent from PATH, the call raises a raw
`FileNotFoundError`. In the direct ffmpeg path this propagates uncaught to the CLI's generic
handler ("An error occurred during download"). Worse, in the `AUTO`/segment path the segments
are downloaded first and ffmpeg is only invoked at merge time (`_merge_segments_batched` →
`_merge_batch_segments`), so a user with no ffmpeg wastes the entire download before hitting an
opaque failure at the final merge.

**Evidence:**
- `downloader.py:313-332` — `"ffmpeg"` spawned directly, no existence check, `FileNotFoundError`
  not handled.
- `ffmpeg_utils.py:175-186` and `215-231` — batch/final merge spawn `ffmpeg` the same way; the
  merge is the last step of the segment pipeline.

**Recommendation:** Probe ffmpeg availability once at startup (e.g. `shutil.which("ffmpeg")`)
and fail fast with a clear, actionable message pointing at the install docs, before any
network work begins.

---

### INT-008: NetworkMonitor bypasses its oversized-JSON guard when `Content-Length` is absent

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | advisory |

**Description:** `_intercept_response` guards against reading huge JSON bodies by checking the
`content-length` header against a ~1MB threshold before calling `await response.json()`. When
the header is missing (chunked / streamed responses, which are common), the guard is skipped
entirely and the full body is read and parsed into memory. A large streamed JSON response from
an intercepted `video`-matching URL could therefore consume unbounded memory during extraction.

**Evidence:**
- `network_monitor.py:67-86` — the size guard only runs `if content_length is not None`; the
  `else` (missing header) falls straight through to `await response.json()` with no cap.

**Recommendation:** Enforce a byte cap even when `Content-Length` is absent — e.g. read the body
with a bounded reader or check the length of the fetched text before parsing — so interception
cannot be forced to buffer arbitrarily large responses.

---

### INT-009: `ruff format --check` fails on integration-teardown module (and enums)

| Field | Value |
|-------|-------|
| **ID** | INT-009 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/signal_handlers.py`, `src/vkdownloader/models/enums.py` |
| **Classification** | advisory |

**Description:** Runtime Verification step R2 recorded a non-zero exit from
`uv run ruff format --check src/vkdownloader` (exit 1): two files would be reformatted.
One of them, `services/signal_handlers.py`, is directly part of the integration teardown path
(graceful-shutdown signal registration/cleanup). Formatting drift on a checked-in module means
CI format gates would fail and indicates the file was edited without running the formatter.

**Evidence:**
- `uv run ruff format --check src/vkdownloader` → "Would reformat: src\\vkdownloader\\models\\enums.py"
  and "Would reformat: src\\vkdownloader\\services\\signal_handlers.py"; "2 files would be reformatted".
- (`ruff check` and `mypy` both pass; this is a formatting-only deviation.)

**Recommendation:** Run `uv run ruff format src/vkdownloader` to normalize the two files and
keep the format gate green.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 4 |

## Mandatory Fixes

- **INT-001 (HIGH)** — Browser click guards the wrong `TimeoutError`; Playwright click timeouts
  escape uncaught and abort extraction.
- **INT-002 (MEDIUM)** — `BrowserManager.__aexit__` leaks the Playwright driver if
  `browser.close()` raises.
- **INT-003 (MEDIUM)** — Browser navigation/launch errors are not wrapped as `ExtractionError`
  and escape the resume-path handler.

## Advisory Recommendations

- **INT-004 (MEDIUM)** — Graceful shutdown does not stop an in-progress yt-dlp download.
- **INT-005 (MEDIUM)** — ffmpeg subprocess can be orphaned on coroutine cancellation without
  `shutdown_event`.
- **INT-006 (LOW)** — `ssl_verify=False` silently ignored by the direct ffmpeg path.
- **INT-007 (LOW)** — Missing ffmpeg binary yields an opaque error, only after a full segment
  download in AUTO mode.
- **INT-008 (LOW)** — NetworkMonitor oversized-JSON guard bypassed when `Content-Length` is absent.
- **INT-009 (LOW)** — `ruff format --check` fails on `signal_handlers.py` and `enums.py`.

## Doc Updates Needed

- **INT-006** — Document (next to the `ssl_verify` setting / CLI `--no-ssl-verify`) that the flag
  has no effect for `--method ffmpeg`, aligning with `docs/11-guides/vkdownloader-limitations.md`.
