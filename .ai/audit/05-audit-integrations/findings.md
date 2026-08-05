# Phase 05 Audit Findings — External Integrations

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification

| Step | Command | Result |
|------|---------|--------|
| R1 Import | `.venv\Scripts\python -c "import vkdownloader.infrastructure.browser, ...cli, config"` | OK — all 10 integration modules import cleanly; no missing optional deps. stealth.min.js present at `src/vkdownloader/stealth.min.js`. |
| R2 Lint | `ruff check src/vkdownloader/` | Pass — "All checks passed!". |
| R2 Format | `ruff format --check src/vkdownloader/` | Pass — "23 files already formatted". |
| R2 Types | `mypy src/vkdownloader/` | Pass — "no issues found in 23 source files" (note: unused `tests.*` override section, see prior phase CLI-008). |
| R3 Tests | `pytest tests/` | Pass — 248 passed in 9.54s. |

**Docker runtime verification:** Docker is not installed in this environment (`docker` not on PATH). No `Dockerfile` or `docker-compose.yml` exists in the repository, and `docs/11-guides/docker.md` (referenced by audit command files) does not exist. ffmpeg is also not installed, so the ffmpeg subprocess path could not be exercised at runtime. All findings are based on static code analysis, FFmpeg official documentation verification, and the passing (mocked) test suite.

### Integration Inventory (discovered)

| Integration | Library/Binary | Entry Point | Lifecycle Owner |
|-------------|----------------|-------------|-----------------|
| Headless browser | `playwright.async_api` | `BrowserManager` (`infrastructure/browser.py`) | `async with BrowserManager(...)` in `extractor._extract_with_browser` |
| Stream extraction | `yt_dlp` (sync, in executor) | `VKVideoExtractor._extract_with_ytdlp` / `downloader._download_with_ytdlp` | `with yt_dlp.YoutubeDL(...)` (context-managed) |
| HLS→MP4 download | `ffmpeg` subprocess | `HLSDownloader.download_with_ffmpeg` | `try/finally` + `cancel_ffmpeg_process` |
| Segment merge | `ffmpeg` subprocess | `ffmpeg_utils._merge_segments_batched` → `_merge_batch_segments` / `_perform_final_merge` | **No lifecycle protection** (see INT-001) |
| Segment HTTP | `aiohttp` | `segment_downloader._run_download_session` | `async with aiohttp.ClientSession(...)` |
| Cookie serialisation | `services.cookies` | `_write_netscape_cookie_file` / `_cookies_to_netscape` | caller-managed cleanup |

---

## Findings

### INT-001: ffmpeg segment-merge subprocesses have no timeout and no cancellation cleanup

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` (`_merge_batch_segments`, `_perform_final_merge`) |
| **Classification** | mandatory |

**Description:** The ffmpeg binary is spawned in two segment-merge helpers via `asyncio.create_subprocess_exec` + `await process.communicate()` with **no `try/finally`** to terminate the process, **no timeout**, and **no call to `cancel_ffmpeg_process`**. When the coroutine is cancelled (e.g. Ctrl+C / `shutdown_event`) or ffmpeg hangs, the subprocess is orphaned. This contrasts sharply with `download_with_ffmpeg` (`downloader.py:333-410`) which wraps its subprocess in `try/finally` and calls `cancel_ffmpeg_process`. The merge path is reached via `download_hls_with_resume` → `_tally_and_merge` → `_merge_segments_batched` → `_merge_batch_segments`/`_perform_final_merge`, so an interruption during the merge of a long video leaves a live ffmpeg process consuming CPU/disk indefinitely.

**Evidence:**
- `ffmpeg_utils.py:205-211` (`_merge_batch_segments`): `process = await asyncio.create_subprocess_exec(...)` then `stdout, stderr = await process.communicate()` — no try/finally, no timeout, no process termination.
- `ffmpeg_utils.py:245-251` (`_perform_final_merge`): same pattern, no cleanup.
- Static check confirms: `_merge_batch_segments` has `try_finally=False, timeout=False, cancel=False`; `_perform_final_merge` identical. (`_merge_segments_batched` has try/finally for *temp-file* cleanup only — line 278-305 — but does not kill the ffmpeg process it spawns inside the helpers.)
- In contrast `download_with_ffmpeg` (downloader.py:339-410) has `try_finally=True, cancel_ffmpeg=True` with a proper `finally: if process.returncode is None: await cancel_ffmpeg_process(process)`.
- Runtime verification: ffmpeg not installed in this environment, so the hang could not be reproduced live; the defect is proven by code analysis.

**Recommendation:** Wrap the subprocess in `_merge_batch_segments` and `_perform_final_merge` with `try/finally` that calls `cancel_ffmpeg_process(process)` (or `process.kill()`), and enforce `settings.download_timeout` via `asyncio.wait_for(process.communicate(), timeout=...)`. Effort: small. Priority: mandatory.

---

### INT-002: yt-dlp download task has no asyncio-level timeout — hangs can block forever

| Field | Value |
|--------|-------|
| **ID** | INT-002 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`) |
| **Classification** | mandatory |

**Description:** The yt-dlp download runs via `loop.run_in_executor(None, _download)` and the result is awaited at `downloader.py:651` with `await download_task` — there is **no `asyncio.wait_for`** wrapper and **no asyncio-level timeout**. yt-dlp options set `"socket_timeout": settings.download_timeout` (300s) and `"retries": settings.max_retries`, but `socket_timeout` only governs individual socket-read/write operations inside yt-dlp; it does not bound the overall operation. If yt-dlp hangs at a point outside socket I/O — DNS resolution in C extensions, process spawning (`yt_dlp._utils._execute`), SSL handshake stalls, or a deadlock in Python's GIL while the thread holds it — the asyncio task blocks indefinitely with no way to interrupt it. The `shutdown_event` is checked in the progress hook (`downloader.py:201`) and before download starts (`downloader.py:624`), but yt-dlp's C-level blocking calls are immune to `asyncio.CancelledError` once the executor thread is running.

**Evidence:**
- `downloader.py:646-652`:
  ```python
  download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))
  try:
      result = await download_task   # <-- no asyncio.wait_for(timeout=...)
      return Path(result)
  ```
- `downloader.py:180`: `"socket_timeout": settings.download_timeout` — yt-dlp's per-socket timeout, not an overall operation timeout.
- Contrast with `download_with_ffmpeg` (`downloader.py:339`) which uses `try/finally` + `cancel_ffmpeg_process` and concurrent task monitoring with `_await_first_and_cancel_others`.
- Runtime verification: Python's `concurrent.futures.Future.cancel()` returns `False` if the future is already running (CPython docs), so even a cancellation request at line 658 cannot stop the executing thread.

**Recommendation:** Wrap the yt-dlp await in `asyncio.wait_for(download_task, timeout=settings.download_timeout)` so that a total operation-level timeout fires even if yt-dlp's internal socket timeout fails. On `asyncio.TimeoutError`, force cleanup of the executor thread's resources. Effort: small. Priority: mandatory.

---

### INT-003: yt-dlp executor thread cannot be cancelled — zombie threads accumulate in batch mode

| Field | Value |
|--------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`, lines 646–662) |
| **Classification** | mandatory |

**Description:** When a yt-dlp download is cancelled (`asyncio.CancelledError`), the code calls `download_task.cancel()` at `downloader.py:658`. However, `download_task` wraps `loop.run_in_executor(None, _download)`, and Python's `Future.cancel()` is a **no-op on a future that is already running** — it cannot terminate the OS-level thread executing yt-dlp's synchronous Python/C code. The code comment at lines 655–656 explicitly acknowledges this: *"the thread will continue, it will be cleaned up when the process exits or on subsequent runs"*. In batch download mode, each URL launches its own yt-dlp thread via `asyncio.create_task(_download_single(...))` at `cli.py:281-299`. If the user presses Ctrl+C, all in-flight yt-dlp threads survive as zombie threads — still consuming memory, holding open sockets, and continuing to write partial files. Repeated cancellations in long batch runs can exhaust thread pool capacity (default `ThreadPoolExecutor` caps at `min(32, cpu_count+4)`, `downloader.py:648`).

**Evidence:**
- `downloader.py:648`: `download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))` — spawns an OS thread in the default executor.
- `downloader.py:653-659`:
  ```python
  except asyncio.CancelledError:
      logger.info("yt_dlp_download_cancelled")
      # Cancel the executor task (though the thread will continue, it will be
      # cleaned up when the process exits or on subsequent runs)
      if not download_task.done():
          download_task.cancel()
      raise
  ```
- `cli.py:281-299`: In batch mode, all URL tasks are created without semaphore gating (`asyncio.create_task` per URL); yt-dlp primary path receives no semaphore (see INT-006).
- CPython `concurrent.futures` docs: `Future.cancel()` returns `False` if the future is currently executing or completed.

**Recommendation:** Either (a) run yt-dlp as an explicit `asyncio.create_subprocess_exec` (like `download_with_ffmpeg` does) so the process can be killed, or (b) move the `shutdown_event` check into a periodic `asyncio.sleep` loop that breaks the `_download` closure into cancellable chunks. At minimum, document the zombie-thread limitation as a known constraint. Effort: medium. Priority: mandatory.

---
### INT-004: Browser extraction timeout is hardcoded and not integrated with shutdown signal

| Field | Value |
|--------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` (`BrowserManager`), `src/vkdownloader/services/extractor.py` (`_extract_with_browser`) |
| **Classification** | advisory |

**Description:** Playwright browser operations in `_extract_with_browser` use hardcoded timeouts and `asyncio.sleep` calls that do not check the `shutdown_event` during the wait. The `shutdown_event` is only checked **after** all initial delays complete (`extractor.py:224-227`), meaning a Ctrl+C during `page.goto` (60s) or during the pre/post-interaction sleeps (5s + 8s = 13s) is not responded to until the full sequence finishes. Furthermore, `page.goto` timeout is hardcoded at 60000ms (`extractor.py:215`) rather than using `settings.download_timeout` (default 300s), and `chromium.launch()` (`browser.py:35-38`) has no explicit timeout. `page.click(".VideoPlayer")` (`extractor.py:280`) also relies on Playwright's 30s default with no configuration path. This deviates from the documented `download_timeout` config field (`config.py:51-56`), which states it is the "HTTP client timeout in seconds for individual segment requests and playlist fetches" — implying browser operations should also respect it.

**Evidence:**
- `extractor.py:215`: `await page.goto(url, wait_until="domcontentloaded", timeout=60000)` — hardcoded 60s, no `settings.download_timeout`.
- `extractor.py:220`: `await asyncio.sleep(self.settings.browser_pre_interaction_wait)` — 5s, not interrupted by shutdown.
- `extractor.py:222`: `await asyncio.sleep(self.settings.browser_post_interaction_wait)` — 8s, not interrupted by shutdown.
- `extractor.py:224-227`: shutdown_event checked only **after** the two sleeps; if shutdown is signaled during sleep, up to 13s of dead time before response.
- `browser.py:35-38`: `playwright_instance.chromium.launch(headless=..., args=[...])` — no `timeout=` parameter; relies on Playwright default (30s) which is undocumented and unconfigurable.
- `extractor.py:280`: `await page.click(".VideoPlayer")` — no explicit timeout; if selector never appears, blocks for Playwright default (30s).
- Config field `config.py:51-56`: `download_timeout: int = Field(default=300, ge=30, le=3600, ...)` described as "HTTP client timeout in seconds for individual segment requests and playlist fetches" — not applied to browser navigation.

**Recommendation:** [BEST-PRACTICE] Pass `settings.download_timeout` to `page.goto(timeout=...)` and `chromium.launch(timeout=...)`, and replace `asyncio.sleep` with `asyncio.wait_for(shutdown_event.wait(), timeout=...)` so shutdown is responsive. Effort: small. Priority: recommended.

---
### INT-005: ffmpeg download path silently ignores `ssl_verify` setting

| Field | Value |
|--------|-------|
| **ID** | INT-005 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download` FFMPEG branch, `HLSDownloader.download_with_ffmpeg`) |
| **Classification** | mandatory |

**Description:** When `DownloadMethod.FFMPEG` is used, `settings.ssl_verify=False` is **not enforced** on the ffmpeg subprocess. The code logs a warning (`downloader.py:800-806`) stating "The --no-ssl-verify flag is not applied to the direct ffmpeg download path", but the warning is purely informational — no `-ssl_verify 0` flag is passed to the ffmpeg command. This means a user running `vkdownloader download --ssl-verify --method ffmpeg ...` (or with `VKDOWNLOADER_SSL_VERIFY=false`) gets SSL verification enforced regardless of their setting, which is inconsistent with the yt-dlp path (where `nocheckcertificate` is correctly set at `downloader.py:171`). For users with corporate MITM proxies or custom CA environments, the ffmpeg path fails silently where yt-dlp succeeds, with no functional bypass available.

**Evidence:**
- `downloader.py:798-828` (FFMPEG case):
  ```python
  case DownloadMethod.FFMPEG:
      if not settings.ssl_verify:
          logger.warning("ssl_verify_ignored_for_ffmpeg", ...)
      ...
  ```
  Warning logged but no SSL flag added to ffmpeg command.
- `downloader.py:318-331`: ffmpeg command list contains no `-ssl_verify` or equivalent flag.
- Contrast: `downloader.py:171` — `"nocheckcertificate": not settings.ssl_verify` correctly propagated to yt-dlp.
- `config.py:69-72`: `ssl_verify` field documented as "Verify SSL certificates for **CDN connections**" — implies all download paths, not just yt-dlp.
- ffmpeg official docs: the `-ssl_verify` flag controls certificate verification for HTTPS protocol (`ffmpeg -ssl_verify 0`).

**Recommendation:** [SPEC-DEVIATION] Add `"-ssl_verify", "0"` to the ffmpeg command in `download_with_ffmpeg` when `not self.settings.ssl_verify`. Effort: trivial. Priority: mandatory.

---

### INT-006: yt-dlp primary download path bypasses shared concurrency semaphore in batch mode

| Field | Value |
|--------|-------|
| **ID** | INT-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`download_with_ytdlp_with_resume_fallback`, `_download_with_ytdlp`, `perform_download`) |
| **Classification** | mandatory |

**Description:** In batch downloads, `perform_download` receives a `semaphore` parameter (from `cli.py:272`) intended to cap concurrency at `settings.max_concurrent_downloads` (default 4). This semaphore is correctly passed to the segment-download fallback path (`download_hls_with_resume` → `_download_segment_concurrent` → `async with policy.semaphore`), but it is **never acquired** for the yt-dlp primary download. `_download_with_ytdlp` (downloader.py:586-662) runs inside `loop.run_in_executor(None, _download)` with no semaphore acquire. In batch mode, all N URLs start their yt-dlp threads simultaneously (cli.py:281-299), each yt-dlp process internally spawning up to `concurrent_fragments` (settings.max_concurrent_downloads) worker threads (downloader.py:173). With 10 URLs and max_concurrent_downloads=4, this creates 40+ concurrent threads plus yt-dlp's internal network I/O — overwhelming system resources, potentially triggering CDN rate limits, and making the `--max-concurrent-downloads` setting meaningless for the yt-dlp path.

**Evidence:**
- `cli.py:272`: `shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)` — created at batch level.
- `downloader.py:785-797`: `download_with_ytdlp_with_resume_fallback(...)` called with `semaphore=semaphore` — but this parameter is only used for the segment fallback.
- `downloader.py:413-426` (`download_with_ytdlp_with_resume_fallback`): `semaphore` parameter accepted but **only forwarded to `_attempt_segment_resume` → `download_hls_with_resume`** (line 483); `_download_with_ytdlp` at line 456 does **not** receive or use it.
- `downloader.py:456`: `result = await _download_with_ytdlp(video_url, output_file, quality, settings, cookies, raw_cookies, progress_callback)` — no semaphore.
- `downloader.py:648`: `_download` runs inside `loop.run_in_executor(None, _download)` — no semaphore acquire before thread creation.
- `downloader.py:173`: `"concurrent_fragments": settings.max_concurrent_downloads` — yt-dlp's own internal concurrency compounds the issue.

**Recommendation:** [BEST-PRACTICE] Acquire the semaphore at the `perform_download` entry point (before `match method:`), so all download methods (yt-dlp, ffmpeg, segment) are bounded by the same concurrency limit. Effort: small. Priority: mandatory.

---

### INT-007: aiohttp segment download uses coarse `total` timeout with no separate connect timeout

| Field | Value |
|--------|-------|
| **ID** | INT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (`_run_parallel_download_with_backoff`), `src/vkdownloader/services/downloader_throttle.py` (`_retry_429_with_backoff`) |
| **Classification** | advisory |

**Description:** Both HTTP download paths construct `aiohttp.ClientTimeout(total=download_timeout)` with only the `total` parameter set. No separate `connect` or `sock_connect` timeout is specified. The `total` timeout encompasses connection establishment, DNS resolution, TLS handshake, and data transfer — all as a single budget. If DNS or connection establishment is slow (e.g., a stalled CDN edge, a throttled resolver), the entire 300s budget is consumed before any data transfer begins, leaving no effective time for the actual segment download. Additionally, a stalled connection establishment triggers the retry loop, wasting retry attempts on connectivity issues rather than transient HTTP errors.

**Evidence:**
- `segment_downloader.py:158`: `client_timeout = aiohttp.ClientTimeout(total=download_timeout)` in `_run_parallel_download_with_backoff`.
- `downloader_throttle.py:171`: `client_timeout = aiohttp.ClientTimeout(total=download_timeout)` in `_retry_429_with_backoff`.
- `config.py:51-56`: `download_timeout` default 300s, range 30-3600 — too coarse for connection-level failures.
- aiohttp docs: `ClientTimeout` supports `connect`, `sock_connect`, `sock_read` for granular control.

**Recommendation:** [BEST-PRACTICE] Split the timeout into `aiohttp.ClientTimeout(total=download_timeout, connect=min(30, download_timeout//4), sock_connect=30, sock_read=60)` so connection failures fail fast and don't consume the retry budget. Effort: trivial. Priority: recommended.

---

### INT-008: Parallel segment-download backoff sleeps without shutdown awareness

| Field | Value |
|--------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (`_run_parallel_download_with_backoff`, lines 143–174) |
| **Classification** | advisory |

**Description:** The parallel segment download path (`_run_parallel_download_with_backoff` at `segment_downloader.py:169-172`) uses a bare `await asyncio.sleep(delay)` for backoff between retries. Unlike the sequential path (`_retry_429_with_backoff` in `downloader_throttle.py:206`, which calls `_wait_with_shutdown(...)`), the parallel path's sleep is **not interruptible by the shutdown_event**. If a user presses Ctrl+C during a backoff sleep, the segment download task continues sleeping for the full delay duration (up to ~30s with jitter) before the `shutdown_event.is_set()` check at `_download_segment_parallel` line 277 is reached on the next loop iteration. This delays shutdown response in batch downloads with many active segment-download tasks.

**Evidence:**
- `segment_downloader.py:169-172`:
  ```python
  delay = _compute_backoff_delay(response.status, attempt, None)
  await asyncio.sleep(delay)  # <-- not interruptible by shutdown_event
  return None
  ```
- Contrast: `downloader_throttle.py:206-207` (sequential path):
  ```python
  if await _wait_with_shutdown(delay, shutdown_event, segment_index, sanitized_url):
      return None
  ```
- `segment_downloader.py:277-283`: `_download_segment_parallel` checks `shutdown_event.is_set()` at the top of the retry loop — only checked **between** attempts, not during the sleep.

**Recommendation:** [BEST-PRACTICE] Replace `await asyncio.sleep(delay)` at `segment_downloader.py:171` with `await _wait_with_shutdown(delay, shutdown_event, ...)` (the same helper used by the sequential path). Requires importing `_wait_with_shutdown` and `get_shutdown_event` into `segment_downloader.py`. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

- **[INT-001]** Wrap ffmpeg subprocess in `_merge_batch_segments` (`ffmpeg_utils.py:205-211`) and `_perform_final_merge` (`ffmpeg_utils.py:245-251`) with `try/finally` that calls `cancel_ffmpeg_process(process)`, and enforce `settings.download_timeout` via `asyncio.wait_for(process.communicate(), timeout=...)`. Prevents orphaned ffmpeg processes on cancellation/hang during segment merge. Effort: small.
- **[INT-002]** Wrap `await download_task` in `_download_with_ytdlp` (`downloader.py:651`) with `asyncio.wait_for(download_task, timeout=settings.download_timeout)` so a total-operation-level timeout fires even if yt-dlp's internal socket timeout fails to catch a hang. Effort: small.
- **[INT-003]** Address the inability to cancel the yt-dlp executor thread (`downloader.py:648,658`). Either restructure yt-dlp to run as `asyncio.create_subprocess_exec` (killable like ffmpeg), or break `_download` into shutdown-aware `asyncio.wait_for` chunks. At minimum, document the zombie-thread limitation. Effort: medium.
- **[INT-005]** Add `-ssl_verify 0` to the ffmpeg command in `download_with_ffmpeg` (`downloader.py:318-331`) when `not self.settings.ssl_verify`. Ensures `--no-ssl-verify` / `VKDOWNLOADER_SSL_VERIFY=false` applies to the ffmpeg download path, matching yt-dlp behavior. Effort: trivial.
- **[INT-006]** Acquire the shared `semaphore` at `perform_download` entry (`downloader.py:716`) before the `match method:` dispatch, so all download methods (yt-dlp, ffmpeg, segment) are bounded by `settings.max_concurrent_downloads`. Prevents thread pool exhaustion and CDN rate-limit cascades in batch mode. Effort: small.

## Advisory Recommendations

- **[INT-004]** Pass `settings.download_timeout` to `page.goto(timeout=...)` (`extractor.py:215`) and `chromium.launch(timeout=...)` (`browser.py:35`), and replace `asyncio.sleep` with `asyncio.wait_for(shutdown_event.wait(), timeout=...)` so shutdown is responsive during browser automation. Effort: small.
- **[INT-007]** Split the coarse aiohttp `total` timeout into granular `connect`, `sock_connect`, `sock_read` components (`segment_downloader.py:158`, `downloader_throttle.py:171`) so connection failures fail fast and don't consume the retry budget. Effort: trivial.
- **[INT-008]** Replace `await asyncio.sleep(delay)` in `_run_parallel_download_with_backoff` (`segment_downloader.py:171`) with `await _wait_with_shutdown(delay, shutdown_event, ...)` to make retry backoff interruptible by shutdown signals, consistent with the sequential path. Effort: trivial.

## Doc Updates Needed

- **[DOC-UPDATE]** Update `docs/11-guides/vkdownloader-limitations.md` to document that the ffmpeg `--method` download path does **not** currently honor `--no-ssl-verify` (INT-005), and that yt-dlp's thread-based execution cannot be truly cancelled on Ctrl+C (INT-003). The limitations guide currently implies all methods support the same feature surface. Effort: trivial.

---
