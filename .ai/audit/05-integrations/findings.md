# Phase 05 Audit Findings — External Integrations

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** no

> Scope: browser automation (Playwright), network capture, aiohttp segment/playlist fetch,
> ffmpeg subprocess integration, yt-dlp subprocess integration, cookie handling, signal-driven
> shutdown. Runtime verification (imports, ruff, mypy, 217 pytest) all passed; findings below are
> from code/config analysis of the integration boundary, not test failures.

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

**Description:** `BrowserManager.__aenter__` (browser.py:28-39) assigns `self.playwright` and then calls `self.browser = await playwright_instance.chromium.launch(...)`. In Python, an `async with` block only invokes `__aexit__` if `__aenter__` returned normally. If `chromium.launch()` raises (missing browser binary, sandbox/permission error on Windows, headless detection crash), `__aexit__` is never called, so `await self.playwright.stop()` is skipped and the orphaned Playwright driver/node subprocess is leaked until process exit.

**Evidence:**
```python
# browser.py:32-39  (__aenter__)
playwright_instance = await async_playwright().start()
self.playwright = playwright_instance
self.browser = await playwright_instance.chromium.launch(   # raises here -> __aexit__ NOT called
    headless=self.settings.headless,
    args=["--disable-blink-features=AutomationControlled"],
)
```
Consequence: a failed browser start hangs the calling task's resource cleanup and leaves a zombie `node`/`playwright` process; combined with `_extract_with_browser` (extractor.py:203) this surfaces as an opaque traceback from Playwright rather than a clear "browser unavailable" message.

**Recommendation:** Wrap the launch in `try/except` inside `__aenter__` and call `playwright.stop()` before re-raising, or move cleanup into a `finally`-like guard so the driver is always stopped on partial init. Effort: small. Priority: recommended.

---

### INT-002: Playwright browser is not stopped on `KeyboardInterrupt` mid-extraction

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `BrowserManager.__aexit__` (browser.py:41-53) runs cleanup, but it is only reached if the `async with` block is exited normally or via an exception that unwinds to the `async with`. A `KeyboardInterrupt` raised inside `await page.goto(...)` / `_simulate_video_interaction` propagates: if caught and swallowed before the `async with` scope exits (e.g. in CLI `except KeyboardInterrupt` at cli.py:393 which calls `typer.Exit`), the `async with BrowserManager` context may already have unwound — but in the non-CLI `extract_streams_with_cookies` path the interrupt can leave the browser open. More importantly, the doc/lint rule requires teardown "on user interruption (Ctrl+C)"; the current design relies solely on `async with` semantics plus a global signal handler that only *sets an event* — it never closes the live browser. If a SIGINT lands during `page.goto`, Playwright's own internal asyncio loops can hold the browser open until forced kill.

**Evidence:** `signal_handlers.py:29-33` only sets `shutdown_event.set()`; nothing cancels the in-flight `BrowserManager` context. `extractor.py:207` `await page.goto(url, ..., timeout=60000)` is a long blocking-ish await that ignores `shutdown_event`.

**Recommendation:** In the browser extraction path, periodically observe `shutdown_event` and abort `goto`/interaction early (e.g. wrap with `asyncio.wait_for` against a shutdown-aware future), or explicitly `await browser.close()` in the signal handler path. Effort: medium. Priority: recommended.

---

### INT-003: Spec deviation — `auto` + `cookie_source=BROWSER` still launches the browser (docs say "No browser involvement")

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/11-guides/configuration.md`, `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `configuration.md:71` states the behavior matrix: for method `auto`, both `cookie_source=NONE` and `cookie_source=BROWSER` are "No browser involvement". The code contradicts this: `perform_download` AUTO branch (downloader.py:759-764) calls `_resolve_cookies(extractor, settings, url, m3u8_url, quality)`, and `_resolve_cookies` (downloader.py:631-654) launches the browser whenever `settings.cookie_source == CookieSource.BROWSER`. So `auto --cookie-source browser` DOES launch the browser, unlike the documented "No browser involvement".

**Evidence:**
```python
# downloader.py:759-764 (AUTO branch)
case DownloadMethod.AUTO:
    m3u8_url, cookies, raw_cookies = await _resolve_cookies(
        extractor, settings, url, m3u8_url, quality
    )
# downloader.py:631
if settings.cookie_source == CookieSource.BROWSER:
    browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(url)
```
Doc table (configuration.md:67-71):
```
| `auto` | No browser involvement | No browser involvement |
```

**Recommendation:** The code behavior (browser launch for BROWSER source) is the more sensible one; update `configuration.md` line 71 to "Launches browser" for the BROWSER column. Effort: trivial. Priority: recommended.

---

### INT-004: CookieSource.FILE is documented as "not implemented" but the only reference tells users to "use --cookie-source browser or none" inside a raised error

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `docs/01-tools/vkdownloader-overview.md`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** `extract_streams_with_cookies` raises `NotImplementedError` for `CookieSource.FILE` (extractor.py:123-126). The config field `cookie_source` is a StrEnum with `FILE` as a valid value (config.py:87, docs list `none, browser, file`), so a user can set it via env and will get a runtime crash rather than a friendly validation error at startup. The error message is the only guidance. This is consistent across docs (they say "file is not implemented"), so it is primarily a doc/UX note: the enum should ideally exclude `FILE` or validate it at Settings construction.

**Evidence:** `extractor.py:124-126` `raise NotImplementedError("CookieSource.FILE is not implemented. Use --cookie-source browser or none instead.")`

**Recommendation:** Either drop `FILE` from `CookieSource` (it is dead/undocumented-as-working) or add a `field_validator` in `Settings` that rejects `FILE` with a clear message at startup instead of mid-extraction. Effort: trivial. Priority: recommended. (Per dead-code policy, the FILE branch is documented-as-unimplemented, so investigate before removing.)

---

### INT-005: Parallel segment download path has no backoff/retry beyond a hardcoded 1.0s sleep; divergent from sequential path

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** There are two parallel code paths for segment download with inconsistent retry semantics. The sequential path (`_download_segment_sequential`) delegates to `_retry_429_with_backoff`, which implements AWS Full Jitter, Retry-After parsing, and shutdown-aware waiting. The parallel path (`_run_parallel_download_with_backoff`) only sleeps a **hardcoded `await asyncio.sleep(1.0)`** (segment_downloader.py:165) on retryable status and never applies jitter or honors Retry-After. For the default `max_concurrent_downloads=4` (non-sequential), every retryable 429/5xx therefore waits exactly 1.0s with no jitter — increasing the chance of synchronized re-hits (thundering herd) against VK's CDN, the exact scenario the throttle module is designed to avoid.

**Evidence:**
```python
# segment_downloader.py:164-166 (parallel path)
if _should_continue_on_retry(response.status, attempt, max_retries):
    await asyncio.sleep(1.0)   # no jitter, no Retry-After, no shutdown-aware wait
    return None
```
Contrast with `downloader_throttle.py:271-303` (`_compute_backoff_delay`) and `:306-336` (`_wait_with_shutdown`) used by the sequential path.

**Recommendation:** Route the parallel path through the same `_compute_backoff_delay` / `_wait_with_shutdown` helper (or a shared helper) so retry timing, jitter, Retry-After, and shutdown monitoring are identical across both paths. Effort: small. Priority: recommended.

---

### INT-006: `_fetch_single_playlist` swallows `asyncio.CancelledError`, defeating graceful shutdown

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_fetch_single_playlist` (segment_downloader.py:410) catches `asyncio.CancelledError` alongside `aiohttp.ClientError` and returns `None`, treating cancellation as a generic "fetch failed". Callers (`_fetch_playlist_with_retry`) then loop and retry the playlist fetch up to `max_retries` times even though the task was cancelled. This prevents a Ctrl+C during playlist resolution from actually stopping the download; the system keeps re-fetching instead of unwinding. `asyncio.CancelledError` must propagate so the shutdown event / task cancellation works.

**Evidence:**
```python
# segment_downloader.py:410-412
except (aiohttp.ClientError, asyncio.CancelledError) as e:   # Cancel swallowed
    logger.warning("playlist_fetch_failed", error=str(e))
    return None
```

**Recommendation:** Remove `asyncio.CancelledError` from this `except` (catch only `aiohttp.ClientError`) and let cancellation propagate. The surrounding retry loop should also check `shutdown_event.is_set()` before each iteration. Effort: trivial. Priority: recommended.

---

### INT-007: NetworkMonitor intercepts every JSON response containing "video" and reads the full body

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | advisory |

**Description:** `_intercept_response` (network_monitor.py:51-84) registers a response handler on the page. For *every* response whose URL contains "video" AND whose content-type starts with `application/json`, it `await response.json()` and recursively walks the entire structure for `.m3u8` strings. This is broad: (a) it reads full response bodies for unrelated JSON endpoints (comments, profile, recommendations) just because the URL contains the substring "video"; (b) `response.json()` buffers the full body and may race with the page consuming it; (c) the recursive walker has no depth cap or size guard, so a large JSON payload blocks the single Playwright response thread. This couples the monitor to arbitrary VK endpoints and can slow or distort the very extraction it supports.

**Evidence:**
```python
# network_monitor.py:67-72
if "video" in url and response.headers.get("content-type", "").startswith("application/json"):
    data = await response.json()
    self._extract_urls_from_json(data)   # unbounded recursion over whole payload
```

**Recommendation:** Narrow the match (e.g. only inspect JSON whose URL pattern matches known VK stream/player API hosts), cap payload size before `response.json()`, and bound recursion depth. Effort: small. Priority: recommended.

---

### INT-008: `_download_segment_parallel` ignores `download_timeout` for the connect phase via a shared `ClientTimeout(total=...)` that also bounds total time, not idle

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** In `_run_parallel_download_with_backoff` (segment_downloader.py:154) `aiohttp.ClientTimeout(total=download_timeout)` is used, where `download_timeout` defaults to 300s (config.py:41). `total` is a hard cap on the entire request lifetime including reading the body. For a large TS segment this is reasonable, but the sequential path (`_retry_429_with_backoff`, downloader_throttle.py:182) uses the same `total` timeout, while yt-dlp uses `socket_timeout` separately (downloader.py:175). The config field `download_timeout` is documented as "Download timeout in seconds" with no distinction between connect/idle/total, so the same value governs both a single segment request and (for yt-dlp) the socket — inconsistent semantics across the three integrations.

**Evidence:** config.py:41-46 `download_timeout` single field; segment_downloader.py:154 `ClientTimeout(total=download_timeout)`; downloader.py:175 `"socket_timeout": settings.download_timeout`.

**Recommendation:** Either split into connect/idle/total timeouts in `Settings` or document precisely that `download_timeout` is a per-request total cap applied uniformly. Effort: small. Priority: recommended.

---

### INT-009: `cancel_ffmpeg_process` result is ignored; progress monitor can cancel before reading final stderr

| Field | Value |
|-------|-------|
| **ID** | INT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** In `download_with_ffmpeg`, both `_monitor_progress` and `_drain_stderr` call `await cancel_ffmpeg_process(process)` and then `break` (downloader.py:313-315, 323-325). `cancel_ffmpeg_process` returns `True`/`False` (ffmpeg_utils.py:100-125) but the return is discarded, so a failed terminate (e.g. process already gone) is not logged. More importantly, after `process.wait()` completes first, `_await_first_and_cancel_others` cancels the still-reading monitor/drain task, which may discard the final stderr chunk that explains a non-zero exit. The exit-code branch (downloader.py:347) then reports `stderr_data` that may be truncated.

**Evidence:**
```python
# downloader.py:332-335
if progress_callback:
    process_task = asyncio.create_task(process.wait())
    monitor_task = asyncio.create_task(_monitor_progress())
    await _await_first_and_cancel_others(process_task, monitor_task)  # cancels monitor on completion
```

**Recommendation:** Capture/await the draining task to completion before reading stderr on normal exit (use `FIRST_COMPLETED` only to trigger cancellation, then `gather` the other), and log the `cancel_ffmpeg_process` return value. Effort: small. Priority: recommended.

---

### INT-010: Segment merge leaves partial `.ts` files and a temp dir on certain failure paths

| Field | Value |
|-------|-------|
| **ID** | INT-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_merge_segments_batched` (ffmpeg_utils.py:236-271) deletes individual segment files only *inside* `_merge_batch_segments` on success. If a batch merge fails (`_merge_batch_segments` returns `None` at ffmpeg_utils.py:188), the already-merged `batch_*.ts` temp files and any remaining segment `.ts` files are left on disk, and `download_hls_with_resume` returns `None` without cleanup because `_tally_and_merge` only calls `_cleanup_segments` when `downloaded_count == len(segments)` (segment_downloader.py:549-554). The orphaned batch files accumulate in `<output>._<name>_segments/`. Also `_merge_segments_batched` itself raises `FileNotFoundError` (ffmpeg_utils.py:258) on a missing segment, which aborts the whole merge leaving earlier batches merged but undeleted.

**Evidence:** ffmpeg_utils.py:185-188 (fails -> `return None`, leaves batch temp), segment_downloader.py:549-554 (cleanup only on full success).

**Recommendation:** Add a `finally`/best-effort cleanup of `temp_dir` batch files whenever a merge aborts, and make `_merge_segments_batched` not raise (return `None`) so partial batch temp files are cleaned uniformly. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 6 |
| LOW | 4 |

## Mandatory Fixes

- INT-001 (resource lifecycle): BrowserManager leaks Playwright subprocess on launch failure.

## Advisory Recommendations

- INT-002: Browser teardown on Ctrl+C.
- INT-003: Fix `auto`+`BROWSER` doc deviation.
- INT-004: Reject/remove `CookieSource.FILE` at startup.
- INT-005: Unify retry/backoff between sequential and parallel segment paths.
- INT-006: Stop swallowing `asyncio.CancelledError` in playlist fetch.
- INT-007: Narrow NetworkMonitor JSON interception.
- INT-008: Clarify `download_timeout` semantics across integrations.
- INT-009: Preserve final ffmpeg stderr / log cancel result.
- INT-010: Clean up temp batch files on merge failure.

## Doc Updates Needed

- INT-003 (configuration.md:71 auto/BROWSER matrix)
- INT-004 (CookieSource.FILE wording, already consistent but enum should be validated)
