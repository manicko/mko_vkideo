---
name: 03-audit-services-validated-findings
phase: 03-services
description: Validated service layer & business logic audit findings
---

# Phase 03 Audit Findings — Service Layer & Business Logic (Validated)

**Executor:** auditor → validator  
**Source:** `.ai/audit/03-audit-services/findings.md`  
**Validated:** yes  
**Status:** complete

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 Import | `uv run python -c "import vkdownloader.services.*"` | OK — all 8 service modules import cleanly (`IMPORT_OK`). |
| R2 Lint | `uv run ruff check src/vkdownloader/services` | Pass ("All checks passed!"). |
| R2 Format | `uv run ruff format --check src/vkdownloader/services` | FAIL — `signal_handlers.py` would be reformatted (see SRV-007). |
| R2 Types | `uv run mypy src/vkdownloader/services` | Pass ("no issues found in 9 source files"). |
| R3 Tests | `uv run pytest tests` | Pass — 233 passed in ~13.5s. |
| R4 Dead code | AST + reference scan | Vestigial metadata + unused param found (SRV-004, SRV-005). |

---

## Findings

### SRV-001: Parallel segment download retries non-retryable HTTP errors without backoff

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** In the parallel download path (used whenever `max_concurrent_downloads > 1`, the default is 4), non-retryable HTTP statuses (e.g. 401/403/404) are retried up to `max_retries` times with **no delay** between attempts. This violates the "non-retryable errors fail fast" invariant and is inconsistent with the sequential path, which returns immediately on a non-retryable status. It also produces a rapid burst of failing requests against the CDN.

**Evidence:**
- `_run_parallel_download_with_backoff` (segment_downloader.py:144-175) returns `True` on 200, `None` only when `_should_continue_on_retry` is true (retryable + not last attempt, and only then does it `await asyncio.sleep(delay)`), and `False` otherwise (including all non-retryable statuses) — with no sleep.
- `_do_parallel_download_attempt` (segment_downloader.py:191-217) collapses the result with `return result is True`, so `None` (retryable) and `False` (fatal) become indistinguishable.
- `_download_segment_parallel` (segment_downloader.py:276-295) loops `for attempt in range(max_retries)` and simply continues on any non-`True` result, so a 403/404 is re-requested `max_retries` times back-to-back.
- Contrast the sequential path `_retry_429_with_backoff` (downloader_throttle.py:185-192), which returns `None` immediately for `response.status not in RETRYABLE_STATUS_CODES`.

**Recommendation:** Propagate a tri-state (success / retryable / fatal) from `_run_parallel_download_with_backoff` up through `_download_segment_parallel` so fatal statuses break the loop immediately (mirroring the sequential path). This restores fail-fast behavior and removes redundant CDN load. Effort: small. Priority: recommended.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified in segment_downloader.py lines 276-295 — the loop continues on any non-`True` result without distinguishing fatal from retryable errors. Code inspection confirms the race condition described.

---

### SRV-002: Browser interaction catches builtin TimeoutError, not Playwright's TimeoutError

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** `_simulate_video_interaction` wraps `page.click(".VideoPlayer")` in `try/except TimeoutError` intending to gracefully ignore a click that never resolves. However Playwright raises `playwright.async_api.TimeoutError`, which is **not** a subclass of the builtin `TimeoutError`. The `except` clause therefore never matches, so a click timeout propagates out of `_simulate_video_interaction` → `_extract_with_browser`, aborting browser-based extraction (and any forced token-refresh resume) instead of degrading gracefully.

**Evidence:**
- extractor.py:7 imports only `from playwright.async_api import Cookie, Page` — `TimeoutError` in the handler refers to the builtin.
- extractor.py:271-275:
  ```python
  try:
      await page.click(".VideoPlayer")
      logger.debug("clicked_video_player")
  except TimeoutError:
      logger.debug("video_player_click_failed", exc_info=True)
  ```
- Runtime check confirms the mismatch:
  `uv run python -c "import playwright.async_api as p; print(issubclass(p.TimeoutError, TimeoutError))"` → `is_subclass False`; MRO is `playwright._impl._errors.TimeoutError -> Error -> Exception`.

**Recommendation:** Import and catch Playwright's error, e.g. `from playwright.async_api import TimeoutError as PlaywrightTimeoutError` and `except PlaywrightTimeoutError:`. This makes the intended graceful fallback actually work. Effort: trivial. Priority: recommended.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified runtime check confirms `playwright.async_api.TimeoutError` is not a subclass of builtin `TimeoutError`. The except clause at line 274 will not catch Playwright timeouts, causing extraction to fail instead of gracefully degrading.

---

### SRV-003: ffmpeg success is judged by `process.returncode` after cancelling `process.wait()`

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** `HLSDownloader.download_with_ffmpeg` runs `process.wait()` concurrently with a stderr monitor/drain task via `_await_first_and_cancel_others`, which awaits `FIRST_COMPLETED` and cancels the loser. When the monitor/drain task finishes first (e.g. the progress reader breaks on `progress=end` before ffmpeg has fully exited), the `process.wait()` task is cancelled, so the process may not be reaped and `process.returncode` can still be `None`. The subsequent `if process.returncode != 0` check then treats `None != 0` as a failure and returns `None` for a download that actually succeeded.

**Evidence:**
- downloader.py:362-370 launches `process_task = create_task(process.wait())` alongside `monitor_task`/`drain_task` and calls `_await_first_and_cancel_others(...)`.
- `_await_first_and_cancel_others` (downloader.py:80-102) uses `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)` and cancels all pending tasks — including `process.wait()` if the reader task wins the race.
- `read_progress` (ffmpeg_utils.py:90-95) `break`s as soon as it reads `progress=end`, which ffmpeg emits *before* it finishes finalizing/exiting.
- downloader.py:379-384 then checks `if process.returncode != 0: ... return None` with no guard for `returncode is None`.
- Mitigating factor: the production `perform_download` FFMPEG branch (downloader.py:775) calls `download_with_ffmpeg` with **no** `progress_callback`, so it takes the `_drain_stderr` branch which reads until stderr EOF (process exit); this narrows but does not close the race, and the documented public API path with a `progress_callback` remains exposed.

**Recommendation:** After the concurrent wait, ensure the process is actually reaped before reading `returncode` (e.g. `await process.wait()` unconditionally after the reader completes, or treat `returncode is None` as "still running / await it"), rather than inferring failure from an unset return code. Effort: small. Priority: recommended.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified in downloader.py lines 362-379 and ffmpeg_utils.py lines 90-94. The race condition exists: `read_progress` breaks on `progress=end` before process exit, and `returncode is None` is treated as failure without handling the concurrent cancellation scenario.

---

### SRV-004: Segment-progress metadata file is vestigial and does not drive resume

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** The `_progress.json` metadata (`_load_downloaded_count` / `_save_downloaded_count`) is documented as a resume "checkpoint" but has no effect on resume behavior. Actual resume is driven entirely by on-disk `.ts` file existence checks. The metadata is written only on full completion, immediately before it is deleted, and is read only to populate a log field — so it never survives an interruption to be used on the next run.

**Evidence:**
- `_save_downloaded_count` is called once (segment_downloader.py:555) inside `_tally_and_merge`, only when `downloaded_count == len(segments)`; the very next successful step, `_cleanup_segments` (segment_downloader.py:558 → :376), deletes the file via `metadata_file.unlink(missing_ok=True)`.
- `_load_downloaded_count` result (segment_downloader.py:740) is consumed only by the log line `logger.info("found_segments", ..., resume_from=downloaded_count)` (line 741); it is not passed to `_create_segment_download_tasks`.
- Real resume logic is `_create_segment_download_tasks` (segment_downloader.py:672-690), which skips segments whose `{i:05d}.ts` already exists with non-zero size — independent of the metadata count.
- Docs (`docs/01-tools/api-reference.md:499`) state "Segment download resumes from last checkpoint", implying a checkpoint file that is not actually used.

**Recommendation:** Investigate intent before removing: either wire the metadata into resume decisions (persist on partial failure and use it to skip work) or remove the metadata mechanism and update the docs to describe file-existence-based resume. Effort: small. Priority: recommended.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified in segment_downloader.py: the metadata file is written at line 555 just before `_cleanup_segments` deletes it at line 558. Resume (line 675) checks `.ts` file existence, ignoring the metadata count. However, docs/01-tools/api-reference.md:521-524 still list `settings`, `extractor`, `backoff_coordinator`, `semaphore` as HLSDownloadRequest attributes, but the actual model (dtos.py:19-24) does not have these. This finding overlaps with SRV-006 — both involve documentation inaccuracies.

---

### SRV-005: `_tally_and_merge` ignores per-segment download results; success inferred from filesystem

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_tally_and_merge` receives the list of per-segment success booleans (`download_results`) but never inspects it. Completion is decided purely by counting `.ts` files on disk (`len(list(segments_dir.glob("*.ts")))`). The returned booleans from `_download_segment_*` are therefore dead information, and correctness relies entirely on the invariant that a failed download never leaves a non-empty `.ts` file. This is fragile and makes the explicit result-tracking code misleading.

**Evidence:**
- `download_results` is passed into `_tally_and_merge` (segment_downloader.py:524-525, 591) and documented (line 536) but is not referenced anywhere in the function body (segment_downloader.py:547-561).
- Success is computed as `downloaded_count = len(list(segments_dir.glob("*.ts")))` and compared to `len(segments)` (lines 547, 553).

**Recommendation:** Either use `download_results` to detect failed segments explicitly (and fail fast / report which segments failed) or drop the unused parameter and its docstring to remove dead code. Effort: trivial. Priority: recommended.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified in segment_downloader.py:547-553 — `download_results` parameter is received but never used. Success is computed solely from filesystem scan.

---

### SRV-006: Data-model docs deviate from actual models

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/models/video.py`, `src/vkdownloader/models/dtos.py`, `docs/01-tools/api-reference.md` |
| **Classification** | advisory |

**Description:** The API reference describes the data models inaccurately, which matters for the Data Model Integrity dimension because downstream consumers rely on these contracts. Three concrete mismatches exist between docs and code.

**Evidence:**
- `Stream.url`: docs say type `HttpUrl` (api-reference.md:538) but the model declares `url: str` (video.py:18). The service layer still wraps it in `str(...)` (e.g. downloader.py:740, 750), a leftover from when it was a URL type.
- `Stream.format`: docs list "(HLS, DASH, MP4)" (api-reference.md:539) but `StreamFormat` defines only `HLS` and `MP4` (enums.py:20-24); there is no `DASH`.
- `HLSDownloadRequest`: docs list attributes `settings`, `extractor`, `backoff_coordinator`, `semaphore` (api-reference.md:521-525) that do not exist on the model; `dtos.py:19-24` defines only `video_url, m3u8_url, output_file, quality, cookies, progress_callback` (those service objects are intentionally passed as function args, per the model docstring).

**Recommendation:** Update `docs/01-tools/api-reference.md` to match the real models: `Stream.url: str`, remove `DASH` from the format list, and correct the `HLSDownloadRequest` attribute table. Optionally, if URL validation is desired, promote `Stream.url` to a validated type in code instead. Effort: trivial. Priority: recommended.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Verified all three mismatches: Stream.url (video.py:18 is `str`), StreamFormat (enums.py:20-24 has no DASH), HLSDownloadRequest (dtos.py:19-24 has `video_url, m3u8_url, output_file, quality, cookies, progress_callback`). Also verified docs/01-tools/api-reference.md:538-544 and 521-524 still contain the incorrect information.

---

### SRV-007: `ruff format --check` fails on a service module

| Field | Value |
|-------|-------|
| **ID** | SRV-007 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/signal_handlers.py` |
| **Classification** | advisory |

**Description:** The project's formatting gate (`uv run ruff format --check`) fails on `signal_handlers.py` due to a trailing blank line at end of file, so the service directory is not fully format-clean.

**Evidence:**
- `uv run ruff format --check src/vkdownloader/services` → "Would reformat: src\vkdownloader\services\signal_handlers.py; 1 file would be reformatted".
- signal_handlers.py ends at line 86 with actual code content, followed by a trailing blank line at line 87.

**Recommendation:** Run `uv run ruff format src/vkdownloader/services/signal_handlers.py` to remove the trailing newline. Effort: trivial. Priority: recommended.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed: signal_handlers.py ends at line 87 with a trailing blank line (file has 87 lines total but content ends at line 86). Running `ruff format --check` reports "1 file would be reformatted".

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 7 | SRV-001, SRV-002, SRV-003, SRV-004, SRV-005, SRV-006, SRV-007 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Cross-Phase Analysis

No cross-phase conflicts detected. All findings are internally consistent with verified code evidence.

### Rollout Safety Assessment

| Concern | Status |
|---------|--------|
| Circular dependencies | None detected in service layer |
| Hidden dependencies | None detected |
| Unsafe execution sequences | Not applicable (validation only) |

### Architectural Impact Assessment

| Finding ID | Impact | Risk Level |
|------------|--------|------------|
| SRV-001 | Medium — retries non-retryable errors violates fail-fast invariant; may cause unnecessary CDN load | MEDIUM |
| SRV-002 | Medium — exception mismatch breaks graceful degradation in browser extraction path | MEDIUM |
| SRV-003 | Medium — race condition in ffmpeg returncode handling can report false failures | MEDIUM |
| SRV-004 | Low — dead code / documentation inconsistency; no runtime risk | LOW |
| SRV-005 | Low — unused parameter creates misleading dead code path | LOW |
| SRV-006 | Low — documentation inaccuracy; no code change needed | LOW |
| SRV-007 | Low — formatting issue; no runtime impact | LOW |

### Required Actions Summary

| Priority | Findings | Action |
|----------|----------|--------|
| Mandatory | SRV-001, SRV-002, SRV-003 | Code fixes required before production use |
| Advisory | SRV-004, SRV-005, SRV-006, SRV-007 | Documentation and cleanup improvements |