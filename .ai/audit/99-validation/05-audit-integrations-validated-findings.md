# Phase 05 Audit Findings — External Integrations (VALIDATED)

**Phase:** 05-audit-integrations (External Integrations)
**Source (audited):** `.ai/audit/05-audit-integrations/findings.md`
**Template:** `.ai/audit/templates/audit-findings.md`
**Executor:** auditor
**Validator:** validator (evidence-driven, conservative)
**Scope:** `src/vkdownloader/services/ffmpeg_utils.py`, `services/downloader.py`, `infrastructure/browser.py`, `services/extractor.py`, `services/segment_downloader.py`, `services/downloader_throttle.py`, `config.py`, `cli.py`, `docs/11-guides/vkdownloader-limitations.md`
**Status:** complete
**Validated:** yes

> Validator note: this file is a verified, self-contained copy of the source findings with inline validation
> decisions applied. It is self-contained — the reader need not consult the original. Validation was performed
> against the working tree at `C:\py_exp\mko_vkideo` on 2026-08-05 (Python 3.12.1, pydantic 2.13.4,
> structlog 26.1.0). `ruff check src/vkdownloader` → All checks passed; `pytest tests/` → 248 passed
> (9.87s). No source code was modified.

---

## Validation Methodology

1. **Source** — read `ffmpeg_utils.py` (305 lines), `downloader.py` (853 lines), `infrastructure/browser.py` (90 lines), `extractor.py` (283 lines), `segment_downloader.py` (843 lines), `downloader_throttle.py` (325 lines), `config.py` (229 lines), `cli.py` (608 lines), `models/enums.py`, `models/video.py`, `services/cookies.py`, `services/signal_handlers.py`.
2. **Static enumeration** — grep every `asyncio.create_subprocess_exec` site, every `asyncio.sleep` site, every `aiohttp.ClientTimeout` site, every `run_in_executor` site, and every semaphore acquire site to confirm the findings scope claims.
3. **Runtime evidence** — `ruff check src/vkdownloader` (pass), `pytest tests/` (248 passed). The auditor R1-R3 checks are confirmed green. ffmpeg/docker binaries are not installed in this environment, so findings are based on static code analysis (substantially corroborated by the passing mocked test suite).
4. **Cross-phase** — compared against Phase 01 (CLI), Phase 02 (Config), Phase 03 (Services), Phase 04 (Security) findings for overlapping root causes and conflicting evidence.
5. **External docs** — verified ffmpeg `tls_verify` flag via FFmpeg official documentation (`ffmpeg-protocols.7`, `libavformat/tls.h`) and FFmpeg source. Verified aiohttp `ClientTimeout` granular options via aiohttp API docs.
6. **Tests** — inspected `tests/test_ffmpeg_utils.py`, `tests/test_hls_downloader.py`, `tests/test_downloader_throttle.py` for coverage of the cited functions.

### Decision legend

- **[VALIDATED]** Root cause verified against current code; recommendation stands unchanged.
- **[RECLASSIFIED]** Valid issue, but `Type` adjusted per the validator taxonomy (`SPEC-DEVIATION` / `BEST-PRACTICE` / `DOC-UPDATE`).
- **[REJECTED]** Not present, stale, duplicate, low-ROI, architecture-breaking, operationally unsafe.
- **[VALIDATED → CORRECTION]** Valid root cause, but the finding supporting evidence or recommendation contains an inaccuracy that is corrected.

### Validator taxonomy note

`RUNTIME-ERROR` (used by the auditor for INT-001, INT-002, INT-003) is the auditor severity tag and falls
outside the validator classification set. Consistent with Phase 03 SRV-001 prior reclassification
(`RUNTIME-ERROR` → `SPEC-DEVIATION`), these three findings are reclassified to `SPEC-DEVIATION` because the
code violates the project own established patterns (subprocess lifecycle protection, bounded operations,
graceful shutdown). Code must change; documentation is already correct.

---

## Runtime Verification Summary

Re-confirmed against the current tree. Retained only findings-relevant items (problems_only=TRUE).

| Step | Check | Result |
|------|-------|--------|
| R1 Import | 10 integration modules import cleanly; stealth.min.js present | OK (confirms audit R1) |
| R2 Lint | `ruff check src/vkdownloader/` | All checks passed! |
| R2 Format | `ruff format --check src/vkdownloader/` | 23 files already formatted |
| R2 Types | `mypy src/vkdownloader/` | no issues found in 23 source files |
| R3 Tests | `pytest tests/` | 248 passed (9.87s) |
| R4 (validator) | enumerate `→` `asyncio.create_subprocess_exec` sites | 3: `downloader.py:333` (protected); `ffmpeg_utils.py:205` (unprotected); `ffmpeg_utils.py:245` (unprotected) |
| R4 (validator) | enumerate `run_in_executor` sites | 2: `extractor.py:197`; `downloader.py:648` |
| R4 (validator) | enumerate `ClientTimeout(total=)` sites | 3: `downloader_throttle.py:171`, `segment_downloader.py:158`, `segment_downloader.py:444` |
| R4 (validator) | enumerate bare `asyncio.sleep` in segment_downloader | 1: `segment_downloader.py:171` |

---

## Findings

### INT-001: ffmpeg segment-merge subprocesses have no timeout and no cancellation cleanup  [VALIDATED — RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | `RUNTIME-ERROR` → **SPEC-DEVIATION** *(reclassified — see Validation Note)* |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` (`_merge_batch_segments`, `_perform_final_merge`) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified (RUNTIME-ERROR → SPEC-DEVIATION)
> - **Detail:** `RUNTIME-ERROR` is outside the validator taxonomy. The implementation violates the project own subprocess lifecycle pattern: `download_with_ffmpeg` (`downloader.py:339-410`) wraps its ffmpeg subprocess in `try/finally` with `cancel_ffmpeg_process`; `_merge_batch_segments` (`ffmpeg_utils.py:205-223`) and `_perform_final_merge` (`ffmpeg_utils.py:245-261`) do not. Code must change; docs are correct.
> - **Evidence verified:** (1) `ffmpeg_utils.py:205-211` — `create_subprocess_exec` + `process.communicate()` with no `try/finally`, no `asyncio.wait_for` timeout, no `cancel_ffmpeg_process` call. (2) `ffmpeg_utils.py:245-251` — identical pattern. (3) `_merge_segments_batched` (`ffmpeg_utils.py:278-305`) has `try/finally` but only for temp-file cleanup (lines 301-305), NOT for the ffmpeg process. (4) `download_with_ffmpeg` (`downloader.py:339-410`) has the correct pattern: `try/finally` with `if process.returncode is None: await cancel_ffmpeg_process(process)` at lines 405-410. (5) `cancel_ffmpeg_process` is defined at `ffmpeg_utils.py:128-153` and already imported into `downloader.py:32`.
> - **Test coverage:** `tests/test_ffmpeg_utils.py` (TestMergeBatchSegments, TestPerformFinalMerge, TestMergeSegmentsBatched) mock `asyncio.create_subprocess_exec` and `process.communicate` but have zero tests for cancellation, timeout, or orphaned-process scenarios.
> - **Architectural fit:** mirroring `download_with_ffmpeg` `try/finally` + `cancel_ffmpeg_process` pattern is architecturally consistent — no new abstraction. Reuses the existing `cancel_ffmpeg_process` helper.
> - **See also:** INT-002 (same no-timeout theme in a different module); `cancel_ffmpeg_process` definition at `ffmpeg_utils.py:128-153`.
> - **Rollout safety:** independent; backward-compatible (adds protection on exceptional paths only).

**Description:** The ffmpeg binary is spawned in two segment-merge helpers via `asyncio.create_subprocess_exec` + `await process.communicate()` with no `try/finally` to terminate the process, no timeout, and no call to `cancel_ffmpeg_process`. When the coroutine is cancelled (e.g. Ctrl+C / `shutdown_event`) or ffmpeg hangs, the subprocess is orphaned. This contrasts with `download_with_ffmpeg` (`downloader.py:333-410`) which wraps its subprocess in `try/finally` and calls `cancel_ffmpeg_process`. The merge path is reached via `download_hls_with_resume` → `_tally_and_merge` → `_merge_segments_batched` → `_merge_batch_segments`/`_perform_final_merge`, so an interruption during the merge of a long video leaves a live ffmpeg process consuming CPU/disk indefinitely.

**Evidence:**
- `ffmpeg_utils.py:205-211` (`_merge_batch_segments`): `process = await asyncio.create_subprocess_exec(...)` then `stdout, stderr = await process.communicate()` — no try/finally, no timeout, no process termination.
- `ffmpeg_utils.py:245-251` (`_perform_final_merge`): same pattern, no cleanup.
- `_merge_segments_batched` (`ffmpeg_utils.py:278-305`): has `try/finally` for temp-file cleanup only (lines 301-305) — does not kill the ffmpeg process spawned inside the helpers it calls.
- In contrast, `download_with_ffmpeg` (`downloader.py:339-410`) has `try/finally` with `if process.returncode is None: await cancel_ffmpeg_process(process)` at lines 405-410.
- `cancel_ffmpeg_process` defined at `ffmpeg_utils.py:128-153`, already imported into `downloader.py:32`.
- Runtime: ffmpeg not installed in this environment; the defect is proven by code analysis.

**Recommendation (confirmed with refinement):** Wrap each subprocess invocation in `_merge_batch_segments` and `_perform_final_merge` with `try/finally` that calls `cancel_ffmpeg_process(process)`, and enforce `settings.download_timeout` via `asyncio.wait_for(process.communicate(), timeout=settings.download_timeout)`. The `settings` object is currently not available inside these functions — they take `(batch_files, temp_dir)` and `(temp_files, output_file)` respectively. The timeout parameter must be threaded through `_merge_segments_batched` (the entry point from `segment_downloader.py:556`) down to the two helpers. Effort: small (requires threading one additional parameter). Priority: mandatory.

### INT-002: yt-dlp download task has no asyncio-level timeout — hangs can block forever  [VALIDATED — RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | HIGH |
| **Type** | `RUNTIME-ERROR` → **SPEC-DEVIATION** *(reclassified — see Validation Note)* |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified (RUNTIME-ERROR → SPEC-DEVIATION)
> - **Detail:** `RUNTIME-ERROR` is outside the validator taxonomy. The code uses `settings.download_timeout` everywhere via the settings model (`config.py:51-56`), including yt-dlp `socket_timeout` (`downloader.py:180`), but the overall asyncio await has no timeout bound. Code must change; docs are correct.
> - **Evidence verified:** (1) `downloader.py:648` — `download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))`. (2) `downloader.py:651` — `result = await download_task` — no `asyncio.wait_for` wrapper. (3) `downloader.py:180` — `"socket_timeout": settings.download_timeout` — yt-dlp per-socket timeout, not an overall operation timeout. (4) Python `concurrent.futures.Future.cancel()` returns `False` if the future is already running — even cancellation at line 658 cannot stop the executing thread.
> - **Architectural fit:** `asyncio.wait_for(download_task, timeout=settings.download_timeout)` is consistent with the project use of `asyncio.wait_for(..., timeout=...)` elsewhere (e.g. `cancel_ffmpeg_process` at `ffmpeg_utils.py:146` and `_wait_with_shutdown` at `downloader_throttle.py:319`).
> - **See also:** INT-003 (same root cause — `run_in_executor` for yt-dlp; INT-003 addresses cancellation, INT-002 addresses timeout).
> - **Rollout safety:** independent; backward-compatible (adds timeout on the await only).

**Description:** The yt-dlp download runs via `loop.run_in_executor(None, _download)` and the result is awaited at `downloader.py:651` with `await download_task` — no `asyncio.wait_for` wrapper and no asyncio-level timeout. yt-dlp options set `"socket_timeout": settings.download_timeout` (line 180) and `"retries": settings.max_retries` (line 181), but `socket_timeout` only governs individual socket read/write operations inside yt-dlp; it does not bound the overall operation. If yt-dlp hangs at a point outside socket I/O → DNS resolution in C extensions, process spawning, SSL handshake stalls, or a deadlock — the asyncio task blocks indefinitely with no way to interrupt it. The `shutdown_event` is checked in the progress hook (line 201) and before download starts (line 624), but yt-dlp C-level blocking calls are immune to `asyncio.CancelledError` once the executor thread is running.

**Evidence:**
- `downloader.py:646-652`:
  ```python
  download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))
  try:
      result = await download_task   # <-- no asyncio.wait_for(timeout=...)
      return Path(result)
  ```
- `downloader.py:180`: `"socket_timeout": settings.download_timeout` — yt-dlp per-socket timeout, not an overall operation timeout.
- Contrast with `download_with_ffmpeg` (`downloader.py:339`) which uses `try/finally` + `cancel_ffmpeg_process` and concurrent task monitoring with `_await_first_and_cancel_others`.
- Python `concurrent.futures.Future.cancel()` returns `False` if the future is already running.

**Recommendation (confirmed):** Wrap the yt-dlp await in `asyncio.wait_for(download_task, timeout=settings.download_timeout)` so that a total operation-level timeout fires even if yt-dlp internal `socket_timeout` fails to catch a hang. On `asyncio.TimeoutError`, log and return `None` (the retry loop in `download_with_ytdlp_with_resume_fallback` at lines 455-465 will handle the fallback). Note: per INT-003, the underlying executor thread cannot be killed — the timeout prevents indefinite blocking but the thread may still complete in the background. Effort: small. Priority: mandatory.

### INT-003: yt-dlp executor thread cannot be cancelled — zombie threads accumulate in batch mode  [VALIDATED — RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | `RUNTIME-ERROR` → **SPEC-DEVIATION** *(reclassified — see Validation Note)* |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`, lines 646–662) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified (RUNTIME-ERROR → SPEC-DEVIATION)
> - **Detail:** `RUNTIME-ERROR` is outside the validator taxonomy. The implementation uses `loop.run_in_executor` for yt-dlp (`downloader.py:648`), which cannot be interrupted by `asyncio.CancelledError` — a known CPython limitation. The code comment at downloader.py:655-656 explicitly acknowledges this (the thread will continue, it will be cleaned up when the process exits or on subsequent runs). This deviates from the project graceful-shutdown pattern (`shutdown_event` + `cancel_ffmpeg_process` for ffmpeg subprocesses). Code must change; docs are correct.
> - **Evidence verified:** (1) `downloader.py:648` — `_download` runs inside `loop.run_in_executor`. (2) `downloader.py:653-659` — `except asyncio.CancelledError` block calls `download_task.cancel()`, which is a no-op on a running future. (3) `cli.py:281-299` — batch mode creates `asyncio.create_task` per URL without semaphore gating for the yt-dlp path (see INT-006). (4) Default `ThreadPoolExecutor` caps at `min(32, cpu_count+4)` — repeated cancellations in batch mode can exhaust capacity.
> - **Test coverage:** `tests/test_hls_downloader.py:1028-1057` tests `_download_with_ytdlp` logging but does NOT test cancellation behavior. Zero tests cover the `except asyncio.CancelledError` block at lines 653-659.
> - **Architectural fit:** the recommendation (use `create_subprocess_exec` like ffmpeg, or break `_download` into shutdown-aware chunks) is consistent with the existing ffmpeg subprocess pattern (`downloader.py:333`). The documentation-only fallback is zero-risk and should be done regardless.
> - **See also:** INT-002 (same root cause — `run_in_executor`; INT-002 adds a timeout, INT-003 enables true cancellation). INT-006 (zombie threads in batch mode exacerbated by no semaphore gating on yt-dlp path).
> - **Rollout safety:** the documentation-only option is zero-risk; the subprocess restructure is the higher-effort path and should be sequenced after INT-001 (which establishes the subprocess pattern).

**Description:** When a yt-dlp download is cancelled (`asyncio.CancelledError`), the code calls `download_task.cancel()` at `downloader.py:658`. However, `download_task` wraps `loop.run_in_executor(None, _download)`, and Python `Future.cancel()` is a no-op on a future that is already running — it cannot terminate the OS-level thread executing yt-dlp synchronous Python/C code. The code comment at lines 655-659 explicitly acknowledges this. In batch download mode, each URL launches its own yt-dlp thread via `asyncio.create_task(_download_single(...))` at `cli.py:281-299`. If the user presses Ctrl+C, all in-flight yt-dlp threads survive as zombie threads — still consuming memory, holding open sockets, and continuing to write partial files.

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
- `cli.py:281-299`: In batch mode, all URL tasks are created without semaphore gating (`asyncio.create_task` per URL); the yt-dlp primary path receives no semaphore (see INT-006).
- CPython `concurrent.futures` docs: `Future.cancel()` returns `False` if the future is currently executing or completed.

**Recommendation (confirmed with priority):** Restructure `_download_with_ytdlp` (downloader.py:587-663) to run yt-dlp as an explicit `asyncio.create_subprocess_exec` — the **single recommended approach** — mirroring the existing `download_with_ffmpeg` pattern (downloader.py:334-411) which uses `try/finally` + `cancel_ffmpeg_process` for graceful process termination. This is consistent with the project's established subprocess lifecycle standard (also applied in INT-001's fix for `_merge_batch_segments` and `_perform_final_merge`). The subprocess restructure enables true cancellation via `process.terminate()` (unlike `run_in_executor` whose `Future.cancel()` is a no-op on running futures). Document the zombie-thread limitation as a known constraint in `docs/11-guides/vkdownloader-limitations.md` as part of this change. This should be sequenced after INT-001 (which establishes the `try/finally` + `cancel_ffmpeg_process` pattern) to reuse the same lifecycle guard. Effort: medium. Priority: mandatory.

### INT-004: Browser extraction timeout is hardcoded and not integrated with shutdown signal  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Validation Status** | VALIDATED (finding recommendation label `[BEST-PRACTICE]` at p.139 contradicts its own Type field `SPEC-DEVIATION`; Type field governs) |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` (`BrowserManager`), `src/vkdownloader/services/extractor.py` (`_extract_with_browser`) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (no reclassification)
> - **Detail:** Verified against current source. (1) `extractor.py:215` — `page.goto(url, ..., timeout=60000)` hardcoded; not `settings.download_timeout`. (2) `extractor.py:220` — `asyncio.sleep(self.settings.browser_pre_interaction_wait)` not interruptible by `shutdown_event`. (3) `extractor.py:222` — `asyncio.sleep(self.settings.browser_post_interaction_wait)` not interruptible. (4) `extractor.py:224-227` — `shutdown_event` checked after the two sleeps; up to 13s dead time on Ctrl+C. (5) `browser.py:35-38` — `chromium.launch(...)` has no `timeout=` parameter. (6) `extractor.py:280` — `page.click(".VideoPlayer")` has no explicit timeout (relies on Playwright 30s default). (7) `config.py:51-56` — `download_timeout` description says "HTTP client timeout in seconds for individual segment requests and playlist fetches" — does not explicitly mention browser operations, but the spirit of the setting (bounded, configurable operations) is violated by the hardcoded 60000ms.
> - **Evidence correction (minor):** The finding describes `page.click(".VideoPlayer")` as relying on "Playwright 30s default with no configuration path." This is accurate — there is no explicit `timeout=` argument. However, `page.click` at `extractor.py:278-283` IS wrapped in `try/except PlaywrightTimeoutError` (line 282) with a debug log, so a timeout does not crash — it degrades gracefully. The finding core claim (no explicit timeout configured, relying on undocumented defaults) is correct.
> - **Classification note:** The finding recommendation header at line 139 says "[BEST-PRACTICE]" but the Type field says `SPEC-DEVIATION` and the description says "This deviates from the documented `download_timeout` config field." The correct classification is `SPEC-DEVIATION` (implementation deviates from the configurable-settings pattern established by the project). The Type field governs.
> - **See also:** Phase 03 SRV-001 (browser-cookie acquisition path, different root cause); Phase 04 SEC-001 (cookie file handling in the same flow).
> - **Rollout safety:** backward-compatible (replaces magic numbers with settings values; adds shutdown-interruptible sleeps).

**Description:** Playwright browser operations in `_extract_with_browser` use hardcoded timeouts and `asyncio.sleep` calls that do not check the `shutdown_event` during the wait. The `shutdown_event` is only checked **after** all initial delays complete (`extractor.py:224-227`), meaning a Ctrl+C during `page.goto` (60s) or during the pre/post-interaction sleeps (5s + 8s = 13s) is not responded to until the full sequence finishes. Furthermore, `page.goto` timeout is hardcoded at 60000ms (`extractor.py:215`) rather than using `settings.download_timeout` (default 300s), and `chromium.launch()` (`browser.py:35-38`) has no explicit timeout. `page.click(".VideoPlayer")` (`extractor.py:280`) also has no explicit timeout.

**Evidence:**
- `extractor.py:215`: `await page.goto(url, wait_until="domcontentloaded", timeout=60000)` — hardcoded 60s.
- `extractor.py:220`: `await asyncio.sleep(self.settings.browser_pre_interaction_wait)` — 5s, not interrupted by shutdown.
- `extractor.py:222`: `await asyncio.sleep(self.settings.browser_post_interaction_wait)` — 8s, not interrupted by shutdown.
- `extractor.py:224-227`: shutdown_event checked only after the two sleeps.
- `browser.py:35-38`: `playwright_instance.chromium.launch(headless=..., args=[...])` — no `timeout=` parameter.
- `extractor.py:280`: `await page.click(".VideoPlayer")` — no explicit timeout (wrapped in `try/except PlaywrightTimeoutError`, line 282).
- `config.py:51-56`: `download_timeout` field described as "HTTP client timeout in seconds for individual segment requests and playlist fetches."

**Recommendation (confirmed):** Pass `settings.download_timeout` to `page.goto(timeout=...)` and `chromium.launch(timeout=...)`, and replace `asyncio.sleep` with `asyncio.wait_for(shutdown_event.wait(), timeout=...)` so shutdown is responsive. **Correction:** fix the contradictory recommendation label in the source finding — the Type is `SPEC-DEVIATION`, not `BEST-PRACTICE`. Effort: small. Priority: recommended.

### INT-005: ffmpeg download path silently ignores `ssl_verify` setting  [VALIDATED — CORRECTION]

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Validation Status** | VALIDATED with CORRECTION (ffmpeg flag name in recommendation is wrong; correct flag is `tls_verify`, not `ssl_verify`) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download` FFMPEG branch, `HLSDownloader.download_with_ffmpeg`) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** validated (core deviation confirmed) — recommendation flag corrected
> - **Detail:** The core finding is correct: the FFMPEG download path at `downloader.py:798-806` logs a warning when `settings.ssl_verify=False` but does not pass any SSL flag to the ffmpeg command. The ffmpeg command at `downloader.py:318-331` contains no SSL verification option. The yt-dlp path at `downloader.py:171` correctly sets `"nocheckcertificate": not settings.ssl_verify`. The `ssl_verify` config field at `config.py:69-72` is documented as "Verify SSL certificates for CDN connections."
> - **Correction — ffmpeg flag name:** the finding evidence at line 166 claims "ffmpeg official docs: the `-ssl_verify` flag controls certificate verification for HTTPS protocol (`ffmpeg -ssl_verify 0`)." This is **incorrect**. Per FFmpeg official documentation (`ffmpeg-protocols.7`) and source code (`libavformat/tls.h`), the correct option name is **`tls_verify`** (with older alias **`verify`**). There is **no** `ssl_verify` option in FFmpeg — using `-ssl_verify 0` would produce an "Unrecognized option" error and abort the download. The project own limitations doc (`docs/11-guides/vkdownloader-limitations.md:92`) corroborates this: it lists `ffmpeg -ssl_verification` as "Invalid option, causes immediate failure."
> - **Corrected recommendation:** Add `"-tls_verify", "0"` to the ffmpeg command in `download_with_ffmpeg` (`downloader.py:318-331`) when `not self.settings.ssl_verify`. The `self.settings` is available in `download_with_ffmpeg` (set in `__init__` at line 279). Alternatively, use URL query parameter `?tls_verify=0` appended to the m3u8 URL.
> - **Architectural fit:** consistent with the yt-dlp path `nocheckcertificate: not settings.ssl_verify` pattern. Forwarded to ffmpeg as a protocol option — no new abstraction.
> - **Test coverage:** `tests/test_hls_downloader.py:2048-2101` (TestSslVerifyFfmpegWarning) verifies the warning is logged but does NOT verify that any SSL flag is passed to the ffmpeg command — confirming the gap is untested at the command-construction level.
> - **See also:** SEC-001 (Phase 04) — both touch the ffmpeg download path; SEC-001 is about cookie-file location, INT-005 is about SSL flag; distinct root causes.
> - **Rollout safety:** backward-compatible (the flag only affects `ssl_verify=False` case; `ssl_verify=True` is the ffmpeg default and unchanged).

**Description:** When `DownloadMethod.FFMPEG` is used, `settings.ssl_verify=False` is not enforced on the ffmpeg subprocess. The code logs a warning (`downloader.py:799-806`) stating "The --no-ssl-verify flag is not applied to the direct ffmpeg download path", but the warning is purely informational — no SSL flag is passed to the ffmpeg command. This means a user with `ssl_verify=False` gets SSL verification enforced regardless of their setting on the ffmpeg path, inconsistent with the yt-dlp path (where `nocheckcertificate` is correctly set at `downloader.py:171`). For users with corporate MITM proxies or custom CA environments, the ffmpeg path fails silently where yt-dlp succeeds, with no functional bypass available.

**Evidence:**
- `downloader.py:798-806` (FFMPEG case):
  ```python
  case DownloadMethod.FFMPEG:
      if not settings.ssl_verify:
          logger.warning(
              "ssl_verify_ignored_for_ffmpeg",
              ...
              hint="The --no-ssl-verify flag is not applied to the direct ffmpeg "
              "download path; use --method yt-dlp or --method auto for SSL "
              "verification control on the CDN connection.",
          )
  ...
  ```
  Warning logged but no SSL flag added to ffmpeg command.
- `downloader.py:318-331`: ffmpeg command list contains no SSL-related flag.
- Contrast: `downloader.py:171` — `"nocheckcertificate": not settings.ssl_verify` correctly propagated to yt-dlp.
- `config.py:69-72`: `ssl_verify` field documented as "Verify SSL certificates for CDN connections."
- FFmpeg official docs (`ffmpeg-protocols.7`) and source (`libavformat/tls.h`) confirm the option is `tls_verify` (alias `verify`), `1|0`, default enabled. **No `ssl_verify` option exists** in FFmpeg.
- `docs/11-guides/vkdownloader-limitations.md:92`: documents `ffmpeg -ssl_verification` as "Invalid option, causes immediate failure" — corroborating that SSL-related ffmpeg flags are error-prone.

**Recommendation (corrected):** Add `"-tls_verify", "0"` to the ffmpeg command in `download_with_ffmpeg` (`downloader.py:318-331`) when `not self.settings.ssl_verify`. This is the correct FFmpeg flag for disabling peer certificate verification on HTTPS connections. *(The original finding recommended `-ssl_verify 0`, which is not a valid FFmpeg option — corrected to `-tls_verify 0` based on FFmpeg official documentation and source code.)* Effort: trivial. Priority: mandatory.

### INT-006: yt-dlp primary download path bypasses shared concurrency semaphore in batch mode  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download`, `download_with_ytdlp_with_resume_fallback`, `_download_with_ytdlp`) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** validated (no reclassification)
> - **Detail:** Verified against current source. (1) `cli.py:272` — `shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)` created at batch level. (2) `downloader.py:780-850` — `perform_download` dispatches on `method` and passes `semaphore=semaphore` to `download_with_ytdlp_with_resume_fallback` (line 795/848) but never acquires it with `async with semaphore:` before the dispatch. (3) `download_with_ytdlp_with_resume_fallback` (`downloader.py:413-491`) accepts `semaphore` (line 424) but only forwards it to `_attempt_segment_resume` (line 483); never to `_download_with_ytdlp` (line 456, no semaphore argument). (4) `_download_with_ytdlp` runs inside `loop.run_in_executor(None, _download)` (line 648) with no semaphore acquire. (5) The FFMPEG primary path (`downloader.py:811`) also receives no semaphore — `download_with_ffmpeg` at line 281 does not accept a semaphore parameter.
> - **Evidence correction (minor):** The finding evidence at line 190 cites `downloader.py:413-426` for `download_with_ytdlp_with_resume_fallback` semaphore parameter — verified that the parameter IS present (line 424: `semaphore: asyncio.Semaphore | None = None`) but is only forwarded to `_attempt_segment_resume` (line 483), not `_download_with_ytdlp` (line 456).
> - **Test coverage:** `tests/test_hls_downloader.py:2048` (TestSslVerifyFfmpegWarning) is **mislabeled** — its docstring says "Tests for INT-006: ssl_verify warning when using ffmpeg method" but INT-006 is about semaphore bypass and INT-005 is about ssl_verify warning. The test body actually validates INT-005 behavior (warning logged for FFMPEG + `ssl_verify=False`). No test exists for INT-006 (semaphore acquisition in `perform_download`). This is a test-naming issue, noted under INT-009.
> - **Architectural fit:** acquiring the semaphore at `perform_download` entry (before `match method:`) is the minimal change that bounds all download methods uniformly. Consistent with the segment download path which acquires it at `segment_downloader.py:616`. The `semaphore is None` guard is an established pattern (segment_downloader.py:737-742).
> - **See also:** INT-003 (zombie threads in batch mode exacerbated by no semaphore gating on yt-dlp path).
> - **Rollout safety:** changes concurrency behavior — should be tested carefully in batch mode. Backward-compatible in semantics (same `max_concurrent_downloads` limit, now actually enforced for yt-dlp path).

**Description:** In batch downloads, `perform_download` receives a `semaphore` parameter (from `cli.py:272`) intended to cap concurrency at `settings.max_concurrent_downloads` (default 4). This semaphore is correctly passed to the segment-download fallback path (`download_hls_with_resume` → `_download_segment_concurrent` → `async with policy.semaphore`, segment_downloader.py:616), but it is **never acquired** for the yt-dlp primary download. `_download_with_ytdlp` (downloader.py:586-662) runs inside `loop.run_in_executor(None, _download)` with no semaphore acquire. In batch mode, all N URLs start their yt-dlp threads simultaneously (cli.py:281-299), each yt-dlp process internally spawning up to `concurrent_fragments` (downloader.py:173) worker threads. With 10 URLs and `max_concurrent_downloads=4`, this creates 40+ concurrent threads plus yt-dlp internal network I/O — overwhelming system resources, potentially triggering CDN rate limits, and making the `--max-concurrent-downloads` setting meaningless for the yt-dlp path.

**Evidence:**
- `cli.py:272`: `shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)` — created at batch level.
- `downloader.py:780-850`: `perform_download` passes `semaphore=semaphore` to `download_with_ytdlp_with_resume_fallback` (line 795, 848) but never acquires it with `async with semaphore:` before the `match method:` dispatch.
- `downloader.py:413-426`: `download_with_ytdlp_with_resume_fallback` accepts `semaphore` (line 424) but only forwards it to `_attempt_segment_resume` (line 483); `_download_with_ytdlp` at line 456 does not receive or use it.
- `downloader.py:456`: `result = await _download_with_ytdlp(...)` — no semaphore.
- `downloader.py:648`: `_download` runs inside `loop.run_in_executor(None, _download)` — no semaphore acquire before thread creation.
- `downloader.py:173`: `"concurrent_fragments": settings.max_concurrent_downloads` — yt-dlp internal concurrency compounds the issue.
- `downloader.py:811`: `download_with_ffmpeg` (FFMPEG path) does not accept a semaphore parameter at all.

**Recommendation (confirmed):** Acquire the shared `semaphore` at the `perform_download` entry point (before `match method:` at line 780), so all download methods (yt-dlp, ffmpeg, segment) are bounded by the same concurrency limit. Guard for `semaphore is None` (single-download mode) following the established pattern at `segment_downloader.py:737-742`. Effort: small. Priority: mandatory.

### INT-007: aiohttp segment download uses coarse `total` timeout with no separate connect timeout  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED (additional scope site noted: `segment_downloader.py:444`) |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (`_run_parallel_download_with_backoff`), `src/vkdownloader/services/downloader_throttle.py` (`_retry_429_with_backoff`) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (no reclassification)
> - **Detail:** Verified against current source. (1) `segment_downloader.py:158` — `aiohttp.ClientTimeout(total=download_timeout)` — only `total` set. (2) `downloader_throttle.py:171` — same pattern. (3) **Additional site (not cited by finding):** `segment_downloader.py:444` — `_fetch_playlist_with_retry` also constructs `aiohttp.ClientTimeout(total=settings.download_timeout)` with only `total`. This is the same coarse-timeout pattern applied to playlist fetching, which the finding description implicitly covers ("playlist fetches"). (4) `config.py:51-56` — `download_timeout` default 300s, range 30-3600. (5) aiohttp `ClientTimeout` supports `connect`, `sock_connect`, `sock_read` for granular control (aiohttp API docs).
> - **Architectural fit:** Splitting the timeout budget is backward-compatible — aiohttp accepts `ClientTimeout(total=..., connect=..., sock_connect=..., sock_read=...)` and when granular values are omitted they default to the `total` budget. No new abstraction.
> - **See also:** INT-008 (same file, `_run_parallel_download_with_backoff` function); Phase 03 SRV-002 (Retry-After in parallel path — same `_run_parallel_download_with_backoff` function).
> - **Rollout safety:** independent; backward-compatible (granular timeouts only tighten failure semantics for slow connections, which is the intent).

**Description:** Both HTTP download paths construct `aiohttp.ClientTimeout(total=download_timeout)` with only the `total` parameter set. No separate `connect` or `sock_connect` timeout is specified. The `total` timeout encompasses connection establishment, DNS resolution, TLS handshake, and data transfer — all as a single budget. If DNS or connection establishment is slow (e.g. a stalled CDN edge, a throttled resolver), the entire 300s budget is consumed before any data transfer begins, leaving no effective time for the actual segment download. Additionally, a stalled connection establishment triggers the retry loop, wasting retry attempts on connectivity issues rather than transient HTTP errors.

**Evidence:**
- `segment_downloader.py:158`: `client_timeout = aiohttp.ClientTimeout(total=download_timeout)` in `_run_parallel_download_with_backoff`.
- `downloader_throttle.py:171`: `client_timeout = aiohttp.ClientTimeout(total=download_timeout)` in `_retry_429_with_backoff`.
- **Additional (not cited):** `segment_downloader.py:444`: `client_timeout = aiohttp.ClientTimeout(total=settings.download_timeout)` in `_fetch_playlist_with_retry`.
- `config.py:51-56`: `download_timeout` default 300s, range 30-3600.
- aiohttp docs: `ClientTimeout` supports `connect`, `sock_connect`, `sock_read` for granular control.

**Recommendation (confirmed with scope expansion):** Split the timeout into `aiohttp.ClientTimeout(total=download_timeout, connect=min(30, download_timeout//4), sock_connect=30, sock_read=60)` at all three sites (`segment_downloader.py:158`, `downloader_throttle.py:171`, `segment_downloader.py:444`) so connection failures fail fast and do not consume the retry budget. Effort: trivial. Priority: recommended.

---

### INT-008: Parallel segment-download backoff sleeps without shutdown awareness  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED (minor evidence correction: `get_shutdown_event` already imported) |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (`_run_parallel_download_with_backoff`, lines 143–174) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (no reclassification)
> - **Detail:** Verified against current source. (1) `segment_downloader.py:169-172` — bare `await asyncio.sleep(delay)` with no `shutdown_event` check. (2) `downloader_throttle.py:206` — sequential path uses `await _wait_with_shutdown(delay, shutdown_event, ...)` — confirmed. (3) `segment_downloader.py:277-283` — `_download_segment_parallel` checks `shutdown_event.is_set()` at the top of the retry loop — only between attempts, not during the sleep.
> - **Evidence correction:** the finding states "Requires importing `_wait_with_shutdown` and `get_shutdown_event` into `segment_downloader.py`." This is **partially inaccurate** — `get_shutdown_event` is **already imported** at `segment_downloader.py:25` (import block at lines 21-26: `RETRYABLE_STATUS_CODES`, `_compute_backoff_delay`, `_retry_429_with_backoff`, `get_shutdown_event` — `_wait_with_shutdown` is absent). Only `_wait_with_shutdown` needs to be added. `_run_parallel_download_with_backoff` already receives `shutdown_event` via `_download_segment_parallel` (line 277), so it is in scope.
> - **Architectural fit:** reusing the existing `_wait_with_shutdown` helper from `downloader_throttle.py` is consistent with the sequential path pattern. No new abstraction.
> - **See also:** INT-007 (same file, `_run_parallel_download_with_backoff` function); Phase 03 SRV-002 (Retry-After in parallel path — same function).
> - **Rollout safety:** independent; backward-compatible (replaces bare sleep with shutdown-aware wait; behavior identical when shutdown is not signaled).

**Description:** The parallel segment download path (`_run_parallel_download_with_backoff` at `segment_downloader.py:169-172`) uses a bare `await asyncio.sleep(delay)` for backoff between retries. Unlike the sequential path (`_retry_429_with_backoff` in `downloader_throttle.py:206`, which calls `_wait_with_shutdown(...)`), the parallel path sleep is **not interruptible by the shutdown_event**. If a user presses Ctrl+C during a backoff sleep, the segment download task continues sleeping for the full delay duration (up to ~30s with jitter) before the `shutdown_event.is_set()` check at `_download_segment_parallel` line 277 is reached on the next loop iteration. This delays shutdown response in batch downloads with many active segment-download tasks.

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
- `_wait_with_shutdown` is defined at `downloader_throttle.py:295` but is **not imported** into `segment_downloader.py` (imports at lines 21-26: `RETRYABLE_STATUS_CODES`, `_compute_backoff_delay`, `_retry_429_with_backoff`, `get_shutdown_event` — `_wait_with_shutdown` absent). `get_shutdown_event` **is already imported** (line 25).

**Recommendation (confirmed with correction):** Replace `await asyncio.sleep(delay)` at `segment_downloader.py:171` with `await _wait_with_shutdown(delay, shutdown_event, ...)`. Add `_wait_with_shutdown` to the import from `.downloader_throttle` (line 21-26). `get_shutdown_event` is already imported (line 25) — no change needed there. Effort: trivial. Priority: recommended.

### INT-009 (NEW): Mislabeled test references INT-006 but tests INT-005 behavior  [DETECTED DURING VALIDATION]

| Field | Value |
|-------|-------|
| **ID** | INT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | ADDED (detected during validation of INT-006) |
| **Affected Modules** | `tests/test_hls_downloader.py` (line 2049) |
| **Classification** | advisory |

> **Origin Note:**
> - **Action:** detected during validation of INT-006
> - **Detail:** `tests/test_hls_downloader.py:2049` has docstring "Tests for INT-006: ssl_verify warning when using ffmpeg method" but INT-006 is about semaphore bypass, and INT-005 is about ssl_verify warning. The test body (lines 2052-2101) actually validates INT-005 behavior (warning logged for FFMPEG + `ssl_verify=False`).
> - **See also:** INT-006 (semaphore bypass, the finding the test is mislabeled as covering); INT-005 (ssl_verify warning, the actual behavior under test).

**Description:** The test class at `test_hls_downloader.py:2048` (`TestSslVerifyFfmpegWarning`) has a docstring referencing INT-006 ("semaphore bypass") but its body tests INT-005 ssl_verify warning behavior. This mislabeling means INT-006 has zero test coverage, and the test for INT-005 lacks a correctly-scoped label.

**Evidence:**
- `test_hls_downloader.py:2049`: docstring "Tests for INT-006: ssl_verify warning when using ffmpeg method."
- The test body (lines 2052-2101) calls `perform_download` with `DownloadMethod.FFMPEG` and `Settings(ssl_verify=False)`, then asserts `ssl_verify_ignored_for_ffmpeg` warning was logged — this is INT-005 behavior, not INT-006.

**Recommendation:** Fix the docstring at `test_hls_downloader.py:2049` — change "INT-006" to "INT-005". Effort: trivial. Priority: recommended.

---

## Cross-Finding Analysis

**Scope:** Phase 05 findings cross-referenced against Phase 01 (CLI), Phase 02 (Config), Phase 03 (Services), and Phase 04 (Security) findings for overlapping root causes, conflicting evidence, and dependency chains.

### Same root cause (merge candidates)

- **INT-002 and INT-003** share the root cause of using `loop.run_in_executor(None, _download)` for yt-dlp (`downloader.py:648`). INT-002 addresses the missing asyncio-level timeout on the await; INT-003 addresses the inability to cancel the executor thread. The long-term fix for INT-003 (restructure yt-dlp as `create_subprocess_exec` like ffmpeg) would inherently enable INT-002 time-based timeout via process-level `asyncio.wait_for`. **Kept separate** — different severities (HIGH vs MEDIUM), different immediate remediation scopes (timeout wrapper vs subprocess restructure), and INT-002 one-line timeout fix is a valid interim mitigation. Merge would conflate two distinct operational hazards (indefinite hang vs zombie threads).
- **INT-007 and Phase 03 SRV-002** both touch `_run_parallel_download_with_backoff` (`segment_downloader.py:143-174`). INT-007 covers the coarse `ClientTimeout` at line 158; SRV-002 covers the ignored `Retry-After` header at line 170. **Not merged** — distinct issues (timeout granularity vs header respect) with distinct fixes, though they share the same function.
- **INT-008 and INT-007** both touch `_run_parallel_download_with_backoff` in `segment_downloader.py`. INT-008 covers the bare `asyncio.sleep` at line 171; INT-007 covers the `ClientTimeout` at line 158. **Not merged** — same function, distinct concerns, independent fixes.
- **INT-005 and Phase 04 SEC-001** both touch the ffmpeg download path. INT-005 is about SSL flag omission; SEC-001 is about cookie-file location on disk. **Not merged** — distinct root causes.

### Conflicting evidence (cross-phase)

**None.** No other phase asserts that the ffmpeg merge subprocesses have lifecycle protection, that yt-dlp `run_in_executor` is cancellable, that browser timeouts use `settings.download_timeout`, that the ffmpeg path honors `ssl_verify`, that the yt-dlp path is semaphore-gated, that aiohttp uses granular timeouts, or that backoff sleeps are shutdown-interruptible. All Phase 05 findings describe gaps that are silent in other phases. No other phase claims the ffmpeg path honors `ssl_verify` (Phase 04 SEC-001 actually documents the ffmpeg path cookie handling separately).

### Dependency chains

- **INT-003 (preferred fix) depends on INT-001:** If INT-003 is implemented via the `create_subprocess_exec` restructure (recommended option), it would create a new subprocess spawn site that needs the same `try/finally` + `cancel_ffmpeg_process` protection that INT-001 establishes for the merge helpers. Sequencing INT-001 first establishes the pattern; INT-003 then follows it. This is an ordering preference, not a hard dependency. No circular dependency.
- **INT-002 is independent** of INT-003 — adding `asyncio.wait_for` (INT-002) does not require the subprocess restructure; it is a one-line timeout wrapper.
- **INT-001 depends on threading** `settings.download_timeout` through `_merge_segments_batched` (caller at `segment_downloader.py:556`) down to `_merge_batch_segments` and `_perform_final_merge`. No dependency on other findings.
- **INT-006 independent** — acquiring the semaphore at `perform_download` entry doesn't depend on any other finding.
- **INT-005 independent** — adding the `tls_verify` flag to the ffmpeg command doesn't depend on any other finding.
- No finding fix depends on another in a circular or hidden manner.

---

## Rollout Analysis

**Independence / ordering:**

- **INT-001 (HIGH, mandatory):** Wrap ffmpeg subprocesses in `_merge_batch_segments` and `_perform_final_merge` with `try/finally` → `cancel_ffmpeg_process` + `asyncio.wait_for(timeout=...)`. Requires threading `settings.download_timeout` through `_merge_segments_batched`. First priority — prevents orphaned ffmpeg processes. Backward-compatible (adds protection on exceptional paths only).
- **INT-005 (HIGH, mandatory):** Add `-tls_verify 0` to ffmpeg command when `not self.settings.ssl_verify`. Trivial, backward-compatible. Can be done in parallel with INT-001 (same file, sibling method, different concern).
- **INT-002 (HIGH, mandatory):** Wrap `await download_task` with `asyncio.wait_for(..., timeout=settings.download_timeout)`. Small, backward-compatible. Independent of INT-001/005.
- **INT-003 (MEDIUM, mandatory):** Restructure yt-dlp to `create_subprocess_exec` (preferred) or add shutdown-aware chunking. Higher-effort; should follow INT-001 (establishes subprocess pattern). The documentation-only fallback is zero-risk and should be done regardless.
- **INT-006 (MEDIUM, mandatory):** Acquire semaphore at `perform_download` entry before `match method:`. Small but changes concurrency behavior — test carefully in batch mode. Independent of INT-001/002/003/005.
- **INT-004 (MEDIUM, advisory):** Replace hardcoded browser timeouts with `settings.download_timeout` and `asyncio.sleep` with shutdown-aware waits. Independent, backward-compatible.
- **INT-007 (LOW, advisory):** Split `ClientTimeout` into granular components at three sites. Backward-compatible.
- **INT-008 (LOW, advisory):** Replace bare `asyncio.sleep` with `_wait_with_shutdown` in `_run_parallel_download_with_backoff`. Backward-compatible.
- **INT-009 (LOW, advisory):** Fix mislabeled test docstring. Trivial.

**Circular / hidden dependencies:** None.

**Backward compatibility:**
- INT-001: Adds cleanup on exceptional paths only; success/failure return values unchanged.
- INT-005: Flag only affects `ssl_verify=False` case; `ssl_verify=True` is ffmpeg default and unchanged.
- INT-002: Adds timeout that fires only when yt-dlp hangs — normally returns within the timeout.
- INT-003: Depends on chosen approach (subprocess restructure vs documentation).
- INT-006: Same `max_concurrent_downloads` limit, now actually enforced for yt-dlp path — expected behavior, not a breaking change.
- INT-004/007/008: Behavioral changes only on edge cases (slow connections, shutdown during sleep).
- INT-009: Docstring only.

**Recommended sequencing:** INT-001 → INT-005 → INT-002 → INT-003 (subprocess restructure, follows INT-001 pattern) → INT-006 → INT-004 → INT-007 → INT-008 → INT-009 (can run in parallel with any phase).

---
## Execution Validation

All change targets confirmed to still exist in the current source tree:

| Finding | Target | Line(s) | Exists? | Stale? |
|---------|--------|---------|---------|--------|
| INT-001 | `_merge_batch_segments` subprocess spawn | ffmpeg_utils.py:205-211 | yes | no |
| INT-001 | `_perform_final_merge` subprocess spawn | ffmpeg_utils.py:245-251 | yes | no |
| INT-001 | `cancel_ffmpeg_process` (secure pattern) | ffmpeg_utils.py:128-153 | yes | no |
| INT-001 | `download_with_ffmpeg` try/finally pattern | downloader.py:339-410 | yes | no |
| INT-002 | `await download_task` without timeout | downloader.py:650-651 | yes | no |
| INT-002 | `socket_timeout` in ydl_opts | downloader.py:180 | yes | no |
| INT-002 | `run_in_executor` for yt-dlp | downloader.py:648 | yes | no |
| INT-003 | executor-thread cancellation no-op | downloader.py:648,653-659 | yes | no |
| INT-003 | batch mode task creation | cli.py:281-299 | yes | no |
| INT-004 | `page.goto` hardcoded timeout | extractor.py:215 | yes | no |
| INT-004 | `asyncio.sleep` not shutdown-aware | extractor.py:220, 222 | yes | no |
| INT-004 | `shutdown_event` checked after sleeps | extractor.py:224-227 | yes | no |
| INT-004 | `chromium.launch` no timeout | browser.py:35-38 | yes | no |
| INT-004 | `page.click` no explicit timeout | extractor.py:280 | yes | no |
| INT-005 | FFMPEG case warning-only | downloader.py:798-806 | yes | no |
| INT-005 | ffmpeg command with no SSL flag | downloader.py:318-331 | yes | no |
| INT-005 | yt-dlp `nocheckcertificate` (contrast) | downloader.py:171 | yes | no |
| INT-005 | `ssl_verify` config field | config.py:69-72 | yes | no |
| INT-006 | `shared_semaphore` created | cli.py:272 | yes | no |
| INT-006 | `perform_download` never acquires semaphore | downloader.py:780-850 | yes | no |
| INT-006 | `download_with_ytdlp_with_resume_fallback` accepts but doesn't use semaphore for yt-dlp | downloader.py:413-491 | yes | no |
| INT-006 | `_download_with_ytdlp` no semaphore | downloader.py:456, 586-662 | yes | no |
| INT-007 | coarse `ClientTimeout(total=)` in parallel path | segment_downloader.py:158 | yes | no |
| INT-007 | coarse `ClientTimeout(total=)` in sequential path | downloader_throttle.py:171 | yes | no |
| INT-007 | coarse `ClientTimeout(total=)` in playlist fetch | segment_downloader.py:444 | yes | no |
| INT-008 | bare `asyncio.sleep` in parallel backoff | segment_downloader.py:171 | yes | no |
| INT-008 | `_wait_with_shutdown` in sequential path | downloader_throttle.py:206 | yes | no |
| INT-008 | `_wait_with_shutdown` NOT imported in segment_downloader | segment_downloader.py:21-26 | yes | no |
| INT-009 | mislabeled test docstring | test_hls_downloader.py:2049 | yes | no |

**Applicability and readiness:** All targets are present in the current source tree and the codebase is in the described state (ruff pass, 248 tests pass). Every finding cited line contents match the current source. No finding is rejected on staleness or applicability grounds. INT-005 recommendation flag name corrected from `-ssl_verify` to `-tls_verify` based on FFmpeg official documentation and source code.

---

## Warnings

- **INT-005 — incorrect ffmpeg flag in recommendation (corrected):** The finding recommendation to use `-ssl_verify 0` would cause an FFmpeg error ("Unrecognized option"). The correct flag is `-tls_verify 0`. The project own limitations doc (`docs/11-guides/vkdownloader-limitations.md:92`) already documents that `ffmpeg -ssl_verification` is an invalid option. If INT-005 is implemented as written (with `-ssl_verify`), it would introduce a new bug — a regression worse than the documented-warning status quo. The validated report corrects this to `-tls_verify 0`.
- **INT-003 — subprocess restructure complexity:** The preferred fix (run yt-dlp as `create_subprocess_exec`) is a non-trivial restructure with medium effort. It changes the download execution model from thread-based to process-based. If implemented, it must reuse the INT-001-established `try/finally` + `cancel_ffmpeg_process` pattern. The documentation-only fallback is safe but leaves the zombie-thread issue unresolved.
- **INT-006 — concurrency behavior change:** Acquiring the semaphore at `perform_download` entry changes the concurrency characteristics of the yt-dlp path. In single-download mode (`cli.py:443-452`), `perform_download` is called without a semaphore (`semaphore=None`), so the change must guard for `None` (the existing pattern at `segment_downloader.py:737-742` already handles this). No regression risk in single-download mode; batch mode gains correct concurrency limiting.
- **INT-007 — additional scope not cited:** `_fetch_playlist_with_retry` at `segment_downloader.py:444` uses the same coarse `ClientTimeout(total=settings.download_timeout)`. The finding cites only lines 158 and 171. The validated recommendation covers all three sites.
- **INT-008 — partial evidence claim:** The finding states "Requires importing `_wait_with_shutdown` and `get_shutdown_event` into `segment_downloader.py`." `get_shutdown_event` is already imported (line 25). Only `_wait_with_shutdown` needs adding. This doesn't change the fix — only the import statement is simplified.
- **Documentation — limitations doc inconsistency:** `docs/11-guides/vkdownloader-limitations.md:92` lists `ffmpeg -ssl_verification` as invalid, while INT-005 originally recommended `-ssl_verify` (also invalid). The correct flag is `-tls_verify`. If INT-005 is implemented with the corrected `-tls_verify` flag, the limitations doc "What Doesn't Work" entry for SSL verification should be updated to reflect that it now works.
- **Test coverage gaps:** INT-001 (no cancellation/timeout tests for merge helpers), INT-002 (no timeout tests for `_download_with_ytdlp`), INT-006 (no semaphore-acquisition tests for `perform_download`). Regression tests should accompany each fix.
- **Test mislabeling:** `tests/test_hls_downloader.py:2049` docstring references INT-006 but the test body validates INT-005. This creates a false impression that INT-006 has test coverage.

---

## Required Fixes (mandatory)

1. **INT-001** (HIGH, mandatory): In `src/vkdownloader/services/ffmpeg_utils.py`, wrap the subprocess in `_merge_batch_segments` (lines 205-223) and `_perform_final_merge` (lines 245-261) with `try/finally` that calls `cancel_ffmpeg_process(process)`, and enforce `settings.download_timeout` via `asyncio.wait_for(process.communicate(), timeout=settings.download_timeout)`. Thread `settings.download_timeout` through `_merge_segments_batched` (caller at `segment_downloader.py:556`) to the two helpers. `cancel_ffmpeg_process` is already defined at `ffmpeg_utils.py:128` and imported in `downloader.py:32`.

2. **INT-002** (HIGH, mandatory): In `src/vkdownloader/services/downloader.py`, wrap `await download_task` at line 651 with `asyncio.wait_for(download_task, timeout=settings.download_timeout)`. On `asyncio.TimeoutError`, log and return `None` (the retry loop in `download_with_ytdlp_with_resume_fallback` at lines 455-465 will handle the fallback).

3. **INT-003** (MEDIUM, mandatory): In `src/vkdownloader/services/downloader.py`, restructure `_download_with_ytdlp` (lines 587-663) to run yt-dlp as an explicit `asyncio.create_subprocess_exec` mirroring the `download_with_ffmpeg` pattern (downloader.py:334-411), reusing `cancel_ffmpeg_process` for graceful termination. This is the recommended approach (not an alternative) — it enables true process-level cancellation via `process.terminate()`. The `shutdown_event` check + `asyncio.wait_for` sleep pattern (segment_downloader.py:646-649, `_check_backoff_before_attempt`) should be integrated into the new subprocess wait loop. Also document the zombie-thread limitation in `docs/11-guides/vkdownloader-limitations.md`. Sequence after INT-001 (establishes the `try/finally` + `cancel_ffmpeg_process` pattern). Effort: medium.

4. **INT-005** (HIGH, mandatory): In `src/vkdownloader/services/downloader.py`, add `"-tls_verify", "0"` (corrected from `-ssl_verify` — see Warnings) to the ffmpeg command in `download_with_ffmpeg` (lines 318-331) when `not self.settings.ssl_verify`. `self.settings` is available in `download_with_ffmpeg` (set in `__init__`, line 279).

5. **INT-006** (MEDIUM, mandatory): In `src/vkdownloader/services/downloader.py`, acquire the shared `semaphore` at `perform_download` entry (line 716, before `match method:` at line 780) with `async with semaphore:` (guard for `semaphore is None`, matching the pattern at `segment_downloader.py:737-742`).

---

## Advisory Recommendations

1. **INT-004** (MEDIUM, small): In `src/vkdownloader/services/extractor.py`, pass `settings.download_timeout` to `page.goto(timeout=...)` (line 215), set `chromium.launch(timeout=...)` in `browser.py:35`, and replace `asyncio.sleep` at lines 220 and 222 with `asyncio.wait_for(shutdown_event.wait(), timeout=...)`. Fix the contradictory recommendation label in the source finding (Type is `SPEC-DEVIATION`, not `BEST-PRACTICE`).

2. **INT-007** (LOW, trivial): In `src/vkdownloader/services/segment_downloader.py:158` and `downloader_throttle.py:171` (and the additional site at `segment_downloader.py:444`), split `aiohttp.ClientTimeout(total=download_timeout)` into `ClientTimeout(total=download_timeout, connect=min(30, download_timeout//4), sock_connect=30, sock_read=60)`.

3. **INT-008** (LOW, trivial): In `src/vkdownloader/services/segment_downloader.py`, add `_wait_with_shutdown` to the import from `.downloader_throttle` (line 21-26) and replace `await asyncio.sleep(delay)` at line 171 with `await _wait_with_shutdown(delay, shutdown_event, ...)`. `get_shutdown_event` is already imported (line 25).

4. **INT-009** (LOW, trivial): Fix the docstring at `tests/test_hls_downloader.py:2049` — change "Tests for INT-006" to "Tests for INT-005".

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | INT-004, INT-006, INT-007, INT-008 |
| Validated + scope/evidence correction | 1 | INT-005 (flag name corrected: `-ssl_verify` to `-tls_verify`; additional recommendation note for `download_with_ffmpeg` method-level fix) |
| Reclassified | 3 | INT-001 (RUNTIME-ERROR to SPEC-DEVIATION), INT-002 (RUNTIME-ERROR to SPEC-DEVIATION), INT-003 (RUNTIME-ERROR to SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 0 | — |
| Added (new, detected during validation) | 1 | INT-009 (mislabeled test docstring) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| _(none)_ | — | All 8 source findings verified against current code; none stale/duplicated/low-ROI/unsafe. INT-005 recommendation flag name corrected but the underlying deviation is real and retained. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| _(none)_ | — | INT-002 and INT-003 share the `run_in_executor` root cause but target distinct operational hazards (indefinite hang vs zombie threads) with distinct severities and remediations. INT-001/005 and INT-007/008 share function-level locality but distinct concerns. All kept separate for independent remediation. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| INT-001 | RUNTIME-ERROR | SPEC-DEVIATION | `RUNTIME-ERROR` is outside the validator taxonomy. Reproduced via source inspection: `_merge_batch_segments` and `_perform_final_merge` spawn ffmpeg subprocesses without `try/finally` or `cancel_ffmpeg_process`, while `download_with_ffmpeg` has the correct pattern. The implementation deviates from the project own subprocess lifecycle standard. Code must change; docs are correct. |
| INT-002 | RUNTIME-ERROR | SPEC-DEVIATION | `RUNTIME-ERROR` is outside the validator taxonomy. `_download_with_ytdlp` awaits an `run_in_executor` future with no `asyncio.wait_for` timeout, despite `settings.download_timeout` being available. The implementation deviates from the project bounded-operation design. Code must change; docs are correct. |
| INT-003 | RUNTIME-ERROR | SPEC-DEVIATION | `RUNTIME-ERROR` is outside the validator taxonomy. `_download_with_ytdlp` runs yt-dlp in an executor thread that cannot be cancelled by `asyncio.CancelledError`; the code comment at lines 655-656 acknowledges this. The implementation deviates from the project graceful-shutdown pattern. Code must change; docs are correct. |
| INT-004 | SPEC-DEVIATION | SPEC-DEVIATION (no change) | Type already aligns. The finding recommendation header "[BEST-PRACTICE]" at p.139 is a typo — contradicts the Type field. Type field governs: SPEC-DEVIATION (hardcoded timeouts deviate from configurable-settings pattern). |
| INT-005 | SPEC-DEVIATION | SPEC-DEVIATION (no change) | Type already aligns. Recommendation corrected: ffmpeg flag is `-tls_verify`, not `-ssl_verify` (per FFmpeg official docs and source). |
| INT-006 | BEST-PRACTICE | BEST-PRACTICE (no change) | Type already aligns. Test-mislabeling discrepancy noted (INT-009). |
| INT-007 | BEST-PRACTICE | BEST-PRACTICE (no change) | Type already aligns. Additional scope site noted (`segment_downloader.py:444`). |
| INT-008 | BEST-PRACTICE | BEST-PRACTICE (no change) | Type already aligns. Import-scope correction: `get_shutdown_event` already imported (line 25); only `_wait_with_shutdown` needs adding. |
