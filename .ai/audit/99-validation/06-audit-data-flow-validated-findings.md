# Phase 06 Audit Findings — Validated Report

**Phase:** 06-audit-data-flow (End-to-End Data Flow)
**Source (audited):** .ai/audit/06-audit-data-flow/findings.md
**Validator:** validator (evidence-driven, conservative)
**Scope:** src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/downloader_throttle.py, src/vkdownloader/services/ffmpeg_utils.py, src/vkdownloader/cli.py
**Status:** validated
**Validated:** yes
**Validated on:** 2026-08-05 (Python 3.12, pydantic 2.13.4)

> This report validates each Phase 06 finding against the current source tree and runtime behavior.
> It is self-contained; the original findings file need not be consulted. No source code was modified.

---

## Runtime Verification Summary

Re-confirmed the auditor's R1-R4 checks against the current tree:

| Step | Command | Result |
|------|---------|--------|
| R1 Import | uv run python -c "import vkdownloader.cli, vkdownloader.config, vkdownloader.services.downloader, vkdownloader.services.segment_downloader, vkdownloader.services.downloader_throttle, vkdownloader.services.ffmpeg_utils, vkdownloader.services.quality, vkdownloader.services.cookies, vkdownloader.services.signal_handlers, vkdownloader.infrastructure.browser, vkdownloader.infrastructure.network_monitor, vkdownloader.utils.security, vkdownloader.utils.url_sanitizer" | ALL IMPORTS OK |
| R2 Lint | uv run ruff check src/vkdownloader | Pass — All checks passed! |
| R2 Types | uv run mypy src/vkdownloader | Pass — Success: no issues found in 23 source files |
| R3 Tests | uv run pytest tests/ -q | Pass — 248 passed in 9.93s |
| R4 Empty-segment trace | Runtime simulation: 200 response with empty body in segment download path | Confirmed: 0-byte file written, returns True; reaches merge unhandled |

> **Note (R1 command):** The source R1 command used bare module names (config, services.downloader)
> alongside kdownloader.cli — an inconsistent import prefix. Re-verified with consistent
> kdownloader.-prefixed imports (above); all import cleanly. The conclusion (pipeline imports OK) is
> unaffected.

---

## Validation Evidence Log

Each finding was verified against current source and re-run at runtime:

| Check | Method | Finding(s) |
|-------|--------|------------|
| _run_parallel_download_with_backoff — 200 response, no size check | segment_downloader.py:160-163 direct read | DF-001 |
| _retry_429_with_backoff — returns raw "" on 200 | downloader_throttle.py:182-183 direct read | DF-001 |
| _download_segment_sequential — "" is not None → writes 0 bytes, returns True | downloader_throttle.py:112-114 direct read | DF-001 |
| _tally_and_merge — glob count only, no size check | segment_downloader.py:541 direct read | DF-001 |
| _tally_and_merge — ll(download_results) passes for 0-byte | segment_downloader.py:548 direct read | DF-001 |
| _merge_segments_batched — existence check only | fmpeg_utils.py:285 direct read | DF-001 |
| Runtime empty-body simulation | code-path trace confirmed | DF-001 |
| Resume filename is index-only | segment_downloader.py:626 direct read | DF-002 |
| Resume skip checks existence + size only | segment_downloader.py:672 direct read | DF-002 |
| No playlist signature stored on resume | segment_downloader.py:734 + full module scan | DF-002 |
| download_hls_with_resume re-export from downloader.py | runtime import | DF-002 |
| ailed_indices from enumerate(download_results) (task-list position) | segment_downloader.py:549 direct read | DF-003 |
| Tasks created only for missing segments | segment_downloader.py:669-687 direct read | DF-003 |
| shared_semaphore from config, no peak counter | cli.py:268-335 direct read | DF-004 |
| DownloadContext has no peak-tracking field | cli.py:69-77 direct read | DF-004 |
| Config value displayed as "Peak concurrency" | cli.py:362, cli.py:593 direct read | DF-004 |
| Display refreshed only after wait coro completes | cli.py:305-320 direct read | DF-005 |
| Callbacks update state but no real-time refresh | cli.py:95-96 direct read | DF-005 |
| Docs acknowledge index-only resume? | grep across docs/**/*.md | DOC-UPDATE |

---

## Findings

### DF-001: Empty (0-byte) segment from HTTP 200 with empty body treated as a successful download

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION *(reclassified from RUNTIME-ERROR — see note)* |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/downloader_throttle.py, src/vkdownloader/services/ffmpeg_utils.py |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** RUNTIME-ERROR is outside the validator taxonomy (SPEC-DEVIATION / BEST-PRACTICE / DOC-UPDATE). The implementation silently produces corrupt output (0-byte segments merged into the final video), violating the functional requirement of correct downloads. Code must change. Per the validator SPEC-DEVIATION rule, this aligns with Phase 03 SRV-001 (RUNTIME-ERROR → SPEC-DEVIATION reclassification precedent).
> - **See also:** Phase 05 INT-001 (ffmpeg merge subprocess lifecycle — distinct concern: process timeout vs. content validation); Phase 05 INT-007 (coarse aiohttp timeout — same HTTP call sites but distinct concern).

**Description:** When the VK CDN returns an HTTP 200 response with an empty body (plausible during token expiry or CDN edge errors), the segment-download functions write a 0-byte .ts file and return True (success). The tally stage validates segment integrity by filename count (glob("*.ts")) and file existence, never by file size, so 0-byte segments pass every check and flow into the ffmpeg concat merge. ffmpeg then either errors on the empty segment (causing the entire video download to fail with a misleading error) or silently includes a blank segment in the output. The root cause is invisible to the user. On the sequential path, the same gap exists: esponse.read() returning "" is written as 0 bytes and marked success because "" is not None.

**Evidence (verified):**

- segment_downloader.py:160-163 — parallel path, no size check after write:
  `python
  if response.status == 200:
      with open(output_path, "wb") as f:
          f.write(await response.read())
      return True
  `
- downloader_throttle.py:182-183 — sequential path returns raw content including "":
  `python
  if response.status == 200:
      return await response.read()
  `
- downloader_throttle.py:112-116 — sequential wrapper treats "" as success ("" is not None):
  `python
  if content is not None:
      with open(output_path, "wb") as f:
          f.write(content)
      return True
  `
- segment_downloader.py:541 — integrity check is filename-count only:
  `python
  downloaded_count = len(list(segments_dir.glob("*.ts")))
  `
- segment_downloader.py:548-549 — ll(download_results) is True because the 0-byte segment returned True:
  `python
  if download_results and not all(download_results):
      failed_indices = [i for i, r in enumerate(download_results) if not r]
  `
- segment_downloader.py:554 — downloaded_count == len(segments) passes because the 0-byte .ts file exists on disk.
- fmpeg_utils.py:285 — merge only checks existence, not size:
  `python
  if not all(f.exists() for f in batch_files):
  `
- Runtime verified: simulated a 200+empty-body response — download returns True, the 0-byte file passes _tally_and_merge checks, and ffmpeg fails at the merge step with a generic error.

**Recommendation:** After writing content on a 200 response, validate that the downloaded content is non-empty (len(content) > 0 / output_path.stat().st_size > 0). If empty, treat as a retryable failure (return None) so the retry loop re-attempts the segment. Effort: small. Priority: mandatory.

**Validation decision: VALIDATED (reclassified RUNTIME-ERROR to SPEC-DEVIATION).** Confirmed against current source: _run_parallel_download_with_backoff (line 160) writes and returns True with no size check; _retry_429_with_backoff (line 182) returns "" for a 200+empty-body; _download_segment_sequential (line 112) writes "" and returns True ("" is not None). _tally_and_merge counts .ts files by glob (line 541), passes the ll(download_results) check (line 548), and passes the count check (line 554). _merge_segments_batched checks only .exists() (line 285). Runtime simulation confirmed the 0-byte segment reaches the merge stage unhandled.

---

### DF-002: Resume logic reuses stale segments by filename index with no content or URL validation

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION *(reclassified from RUNTIME-ERROR — see note)* |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** RUNTIME-ERROR is outside the validator taxonomy. The implementation silently corrupts
>   output (stale + fresh segments merged) or produces false failures (leftover stale files abort merges),
>   violating the functional correctness requirement of correct resume behavior. Code must change.
> - **Line-number note:** The finding cites segment_downloader.py:534 for the claim that
>   _parse_m3u8_segments is called with no signature stored. The actual call site is at **line 734**
>   (segments = _parse_m3u8_segments(playlist_content)); line 534 is in the _tally_and_merge docstring.
>   The _parse_m3u8_segments function definition is at lines 70-78. A full-module scan confirms NO
>   playlist signature, URL hash, or content digest is stored anywhere in the resume path — the substance
>   of the finding is correct; only the cited line number is imprecise.
> - **See also:** DF-003 (downstream consequence: ailed_indices reports wrong indices because tasks
>   skip existing segments); Phase 05 INT-008 (parallel backoff sleep not interruptible — touches the same
>   _run_parallel_download_with_backoff function but a distinct concern).

**Description:** When resuming a segment download after an interruption, _create_segment_download_tasks skips existing segments based solely on filename index and non-zero file size (segment_downloader.py:672). The segment filename is purely index-based ("{i:05d}.ts", line 626) with no URL hash, playlist signature, or content fingerprint recorded. Two failure modes result: (1) Silent corruption — if a new playlist (e.g., after token refresh returns a fresh m3u8 from a different CDN edge) has the same segment count but different content at the same indices, existing on-disk segments are NOT re-downloaded, and the merge combines stale + fresh segments into a corrupt output reported as "success". (2) False failure — if the new playlist has a different segment count, leftover .ts files from the previous run cause downloaded_count != len(segments) (line 554), aborting the merge entirely even though all current playlist segments are present.

**Evidence (verified):**

- segment_downloader.py:626 — segment filename is index-only, no URL/content binding:
  `python
  segment_path = task.segments_dir / f"{task.idx:05d}.ts"
  `
- segment_downloader.py:672 — resume skip checks existence + size only, no URL/content match:
  `python
  if segment_path.exists() and segment_path.stat().st_size > 0:
      logger.debug("skipping_existing_segment", idx=i)
      continue
  `
- segment_downloader.py:734 — _parse_m3u8_segments parses the current playlist but no signature is stored for comparison on resume (full-module scan confirms no signature/URL-hash/content-digest field exists in SegmentTask, DownloadPolicy, or any resume data structure).
- segment_downloader.py:541 — downloaded_count counts ALL .ts files including stale ones from a previous playlist.
- segment_downloader.py:554 — count-mismatch abort when stale files are present at non-overlapping indices:
  `python
  if downloaded_count == len(segments):
  `

**Recommendation:** Bind on-disk segments to the current playlist by including a URL/content digest in the filename (e.g., "{i:05d}_{md5(url)[:8]}.ts"), or store a playlist signature (hash of segment URLs) in the segments directory and clear stale files whose indices or signatures do not match at session start. At minimum, delete .ts files whose indices are >= len(segments) before creating download tasks. Effort: medium. Priority: mandatory.

**Validation decision: VALIDATED (reclassified RUNTIME-ERROR to SPEC-DEVIATION).** Confirmed against current source: filenames are index-only (line 626); resume skip is existence + size only (line 672); _parse_m3u8_segments (line 70-78, called at line 734) stores no signature; download_hls_with_resume re-export confirmed from downloader.py:44. No URL hash, playlist signature, or content fingerprint exists in SegmentTask (lines 35-44), DownloadPolicy (lines 47-64), or anywhere in the resume path. Both failure modes (silent corruption and false-failure abort) are real. Line reference corrected from 534 to 734.

---

### DF-003: failed_indices in _tally_and_merge reports wrong segment indices

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION *(reclassified from RUNTIME-ERROR — see note)* |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** RUNTIME-ERROR is outside the validator taxonomy. The implementation produces incorrect
>   diagnostic output (reports wrong segment indices, directing operators to the wrong segment). This
>   violates the correctness requirement of accurate diagnostics. Code must change.
> - **Line-number note:** The finding cites segment_downloader.py:670-686 for the task-creation loop;
>   the actual span is 669-687. Minor offset. Substance correct.
> - **See also:** DF-002 (the resume-skip logic at line 672 is the cause of the index mismatch —
>   download_results only contains results for non-skipped segments).

**Description:** _tally_and_merge computes ailed_indices from enumerate(download_results) (line 549), but download_results corresponds only to the tasks created by _create_segment_download_tasks — which excludes segments that already existed on disk (skipped at line 672). So the index i in ailed_indices is a position into the missing-segments task list, NOT the actual segment index in the playlist.

Example: playlist has segments [0,1,2,3,4]. Segments 0 and 2 already exist from a prior run. Segment 1 fails. Tasks are created for [1, 3, 4]. download_results = [False, True, True]. ailed_indices = [0] (position of the False entry in the task list), but the actual failed segment is index 1.

**Evidence (verified):**

- segment_downloader.py:549:
  `python
  failed_indices = [i for i, r in enumerate(download_results) if not r]
  `
- segment_downloader.py:669-687: tasks are created only for missing segments (existing ones skipped at line 672 via the continue statement).

**Impact:** The diagnostic log reports incorrect segment indices, directing developers/operators to the wrong segment when troubleshooting download failures.

**Recommendation:** Track the actual segment index alongside each download result (e.g., download_results as list[tuple[int, bool]] or preserve SegmentTask.idx), and compute ailed_indices from the real segment indices. Effort: trivial. Priority: recommended.

**Validation decision: VALIDATED (reclassified RUNTIME-ERROR to SPEC-DEVIATION).** Confirmed against current source: line 549 computes ailed_indices from enumerate(download_results); lines 669-687 create tasks only for missing segments (line 672 continue skips existing). The index arithmetic is confirmed incorrect — download_results does not contain entries for skipped segments, so positional enumeration does not map to playlist indices.

---

### DF-004: Batch summary reports configured max_concurrent_downloads as Peak concurrency without measuring actual peak

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (no change)
> - **Detail:** All claims confirmed. shared_semaphore is created from settings.max_concurrent_downloads
>   (line 272) with no peak-tracking counter; DownloadContext (lines 69-77) has no concurrency-tracking
>   field; settings.max_concurrent_downloads is passed directly to _print_batch_summary (line 593) and
>   displayed verbatim as "Peak concurrency" (line 362). When batch URLs < max_concurrent_downloads, the
>   reported peak exceeds the actual peak.
> - **Test gap note:** 	est_cli.py:202 (	est_batch_statistics_summary) only asserts the string
>   "Peak concurrency:" appears — it does NOT verify the value is a measured peak vs. the config value.

**Description:** _run_batch_with_progress creates a shared_semaphore from settings.max_concurrent_downloads (line 272) to cap concurrency, but no counter tracks the actual peak number of concurrent downloads. The atch_download command passes settings.max_concurrent_downloads directly to _print_batch_summary as the "peak" value (line 593), and _print_batch_summary displays it verbatim as "Peak concurrency" (line 362). The DownloadContext dataclass (lines 69-77) has no field for tracking observed concurrency.

When the number of batch URLs is less than max_concurrent_downloads, the reported "Peak concurrency" is higher than what actually occurred (e.g., "Peak concurrency: 4" for a 2-URL batch where the actual peak was 2).

**Evidence (verified):**

- cli.py:272 — semaphore created from config, no peak counter:
  `python
  shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
  `
- cli.py:69-77 — DownloadContext has no peak-tracking field.
- cli.py:362 — config value displayed as peak:
  `python
  typer.echo(f"  Peak concurrency: {max_concurrent}")
  `
- cli.py:593 — config value passed as "peak":
  `python
  _print_batch_summary(results, settings.max_concurrent_downloads, skipped_count)
  `

**Recommendation:** Track actual concurrent in-flight downloads by incrementing/decrementing a counter when _download_single starts/completes (or when the semaphore is acquired/released) and report the measured peak. Effort: small. Priority: recommended.

**Validation decision: VALIDATED (no change).** Confirmed against current source: line 272 creates the semaphore from config with no peak counter; lines 69-77 confirm DownloadContext has no concurrency-tracking field; line 362 displays max_concurrent verbatim; line 593 passes settings.max_concurrent_downloads directly. The spec-deviation classification is correct — the code labels a config value as "peak" which it is not.

---

### DF-005: Batch progress display only refreshes on download completion, not in real time

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (no change)
> - **Detail:** Confirmed: 	yper.echo (line 320) runs only after wait coro (line 307) completes. The
>   callbacks at line 96 (_progress_manager.update_sync) update state but the display is never refreshed
>   between completions. A full cli.py grep for syncio.create_task returns zero matches — no background
>   polling task exists. BEST-PRACTICE classification is correct — this is an improvement opportunity,
>   not a correctness violation.

**Description:** The batch progress display refreshes only after each wait coro completes in the
s_completed loop (cli.py:307-320). The 	yper.echo at line 320 runs only after a full video download
finishes. During a long-running download, progress callbacks do update _progress_manager (line 96), but
the display is never refreshed. The user sees stale progress (frozen on the last completed download) for
the entire duration of in-progress downloads, with no indication of ongoing activity.

**Evidence (verified):**

- cli.py:305-320 — display only updated post-completion:
  `python
  for coro in asyncio.as_completed(tasks):
      try:
          await coro
      except asyncio.CancelledError:
          ...
      except Exception:
          logger.exception("unexpected_error_in_batch_progress")
      # Update progress display with \r overwrite
      typer.echo(f"\r{await _format_progress(total)}", nl=False)  # only after await coro
  `
- cli.py:95-96 — callbacks update _progress_manager.update_sync(url_index, ...) but display isn't refreshed between completions.

**Recommendation:** Run a background syncio.create_task that polls _progress_manager.get_formatted_progress(total) at a 1-second interval and refreshes the display independently of download completions; cancel the polling task after all downloads finish. Effort: small. Priority: recommended.

**Validation decision: VALIDATED (no change).** Confirmed against current source: the s_completed loop (line 305-320) only calls 	yper.echo after wait coro returns; no background polling task exists (any syncio.create_task grep in cli.py returns zero matches). The progress state is updated by callbacks (line 96) but the display is static during in-progress downloads. BEST-PRACTICE classification is correct — this is an improvement opportunity, not a correctness violation.

---

### DOC-UPDATE: Document resume/index-only segment identification limitation

| Field | Value |
|-------|-------|
| **ID** | DOC-UPDATE |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | docs/01-tools/api-reference.md, docs/01-tools/vkdownloader-overview.md |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (no change)
> - **Detail:** docs/01-tools/api-reference.md:447 states "Resumes from last downloaded segment on
>   interruption" but does NOT document the index-only identification limitation (no content/URL validation).
>   A full docs/ scan for terms index.only, index only, stale, content validation, content
>   fingerprint, playlist signature, or known limitation returns NO matches. The limitation
>   described in DF-002 is undocumented. Once DF-002 is fixed, this doc update becomes moot; until then,
>   documenting the known limitation improves transparency.

**Description:** The documentation does not disclose that segment-level resume identifies segments by
filename index only (no content or URL validation), so playlist changes between runs may cause stale
segment reuse or false-failure aborts.

**Evidence (verified):**

- pi-reference.md:447: "Resumes from last downloaded segment on interruption" — a general statement
  with no mention of the index-only limitation.
- pi-reference.md:450: "Cleans up partial downloads on failure" — no mention of stale-file behavior.
- Full docs/ scan: no documentation of the index-only resume limitation, stale-segment risk, or
  content-validation gap.

**Recommendation:** Document the resume behavior as a known limitation until DF-002 is resolved: segments
are identified by index only (no content validation), so playlist changes between runs may cause stale
segment reuse. Effort: trivial.

**Validation decision: VALIDATED.** The documentation gap is confirmed. pi-reference.md:447 makes a
general "resume" claim without disclosing the index-only limitation. No doc in the tree mentions the
stale-segment risk, index-only identification, or content-validation gap.

---

## Cross-Finding Analysis

**Scope:** Phase 06 findings cross-referenced against all other phases (Phase 01 CLI, Phase 02 Config,
Phase 03 Services, Phase 04 Security, Phase 05 Integrations) for overlapping root causes, conflicting
evidence, and dependency chains.

### Same root cause (merge candidates)

- **DF-001 + DF-002:** Both stem from a missing content-validation invariant in the segment-download
  pipeline. DF-001 lacks post-download size validation (0-byte segments pass as success); DF-002 lacks
  resume-time content binding (stale segments reused by index only). They share the theme "no content-level
  validation" but have **distinct fix sites and mechanisms** (download-path size check vs. resume-path
  content binding). **Not merged** — keeping them separate preserves actionable granularity. Fixing
  DF-001 (size check on write) partially mitigates the DF-002 silent-corruption case (a stale segment
  from a different playlist would have non-zero size, so it would still be skipped), confirming the
  findings are complementary, not redundant.

- **DF-001 + Phase 05 INT-001:** Both converge on the ffmpeg merge stage (_merge_segments_batched).
  DF-001 is about 0-byte segments reaching merge unhandled; INT-001 is about the ffmpeg subprocess itself
  having no timeout/cancellation cleanup. Distinct root causes (content validation vs. process lifecycle).
  **Not merged.**

- **DF-002 + DF-003:** DF-003's incorrect ailed_indices is a **direct consequence** of DF-002's
  resume-skip design (tasks created only for non-existing segments). The index mismatch arises because
  download_results excludes skipped segments. Root causes differ (content binding vs. index tracking),
  but DF-003 cannot be fully resolved without addressing the resume-skip logic in DF-002. **Not merged**
  but DF-003 is downstream of DF-002.

- **SRV-002 (Phase 03) + DF-001:** Both touch _run_parallel_download_with_backoff in
  segment_downloader.py. SRV-002 fixes the Retry-After header being passed as None (line 170);
  DF-001 adds a content-size check after write (lines 160-163). Same function, distinct concerns.
  **Not merged.**

### Conflicting evidence (cross-phase)

None. No other phase asserts that 0-byte segments are handled, that resume validates content, that
ailed_indices is correct, that peak concurrency is measured, or that progress refreshes in real time.
All findings are mutually consistent with the green runtime state (248 tests pass, ruff/mypy clean).

### Dependency chains

- **DF-005 ↔ CLI-005 (Phase 01):** Both target _run_batch_with_progress (cli.py:247-335). CLI-005
  recommends replacing the s_completed + gather double-collection with a single gather +
  progress_callback. DF-005 recommends adding a background polling task for real-time display.
  **Soft dependency: implement CLI-005 before DF-005** to avoid double-rewriting _run_batch_with_progress.

- **DF-003 downstream of DF-002:** Fixing DF-002's resume-skip to track real segment indices (per
  DF-003's recommendation: list[tuple[int, bool]] or SegmentTask.idx) would also resolve DF-003 as
  a side effect. **Ordering preference: DF-002 before DF-003.**

- **DF-001 → DOC-UPDATE:** The DOC-UPDATE recommends documenting the index-only limitation "until
  DF-002 is resolved." If DF-001 and DF-002 are fixed together, the doc note becomes obsolete; document
  now, revisit after fixes.

---

## Rollout Analysis

**Independence / ordering:**

| Finding | Risk | Dependencies | Recommended order |
|---------|------|--------------|-------------------|
| DF-001 (SPEC-DEVIATION, mandatory) | Low — adds size check, returns None for empty to trigger retry | Independent | 1st |
| DF-002 (SPEC-DEVIATION, mandatory) | Medium — changes segment filename scheme / resume clearing | Independent | 1st (parallel with DF-001) |
| DF-003 (SPEC-DEVIATION, advisory) | Low — changes ailed_indices data shape | Downstream of DF-002's skip logic | After DF-002 |
| DF-004 (SPEC-DEVIATION, advisory) | Low — adds peak counter, changes summary label semantics | Independent | 2nd |
| DF-005 (BEST-PRACTICE, advisory) | Low — adds background polling task | Soft: CLI-005 (Phase 01) precedes | After CLI-005 |

**Circular / hidden dependencies:** None. DF-001 and DF-002 touch overlapping code
(_run_parallel_download_with_backoff / _tally_and_merge) but at distinct lines (write logic
vs. filename/resumption logic). No circular dependency.

**Backward compatibility:**

- **DF-001:** Adding a len(content) > 0 check changes behavior — 0-byte segments that were previously
  "succeeded" will now trigger retries (or fail after retries exhausted). This is a correctness fix —
  the prior "success" on a 0-byte segment was itself a bug (corrupt output). No previously-correct
  invocation changes behavior. Existing tests (	est_download_segment_sequential_success at
  	est_hls_downloader.py:1411) mock non-empty content and are unaffected.
- **DF-002:** Changing the segment filename scheme (e.g., adding a URL hash) is a **breaking change for
  existing partial downloads** — on-disk .ts files with the old naming scheme would be treated as stale
  and re-downloaded. Mitigation: clear stale .ts files whose indices exceed the current playlist
  length at session start (the finding's "at minimum" recommendation), or store a playlist signature
  in the segments dir. The download_hls_with_resume tests mock _merge_segments_batched and use fresh
  	mp_path dirs, so they are unaffected.
- **DF-003:** Changing download_results to carry real indices may change the ailed_indices log
  format. Tests don't assert on ailed_indices content (grep confirms no test references it), so no
  breakage.
- **DF-004:** Adding a peak counter is additive. The "Peak concurrency" label would now show a measured
  value instead of the config value. Tests (	est_cli.py:202) only assert the label string appears, not
  the value — no breakage.
- **DF-005:** Adding a background polling task is additive. No tests assert on real-time progress output
  format.

**Rollout sequencing recommendation:**

1. **DF-001** (mandatory, small) — add size validation on 200 responses in both download paths.
2. **DF-002** (mandatory, medium) — bind segments to playlist content/URL on resume.
3. **DF-003** (advisory, trivial) — fix ailed_indices to use real segment indices (naturally
   addressed by DF-002's data-structure changes).
4. **DF-004** (advisory, small) — add peak-concurrency measurement and counter.
5. **DF-005** (advisory, small) — add background polling task for real-time progress (implement after
   CLI-005 from Phase 01 to avoid rewriting _run_batch_with_progress twice).

---

## Execution Validation

All change targets were confirmed to **still exist** in the current source:

| Finding | Target | Line(s) | Exists? | Stale? |
|---------|--------|---------|---------|--------|
| DF-001 | _run_parallel_download_with_backoff 200-response block | segment_downloader.py:160-163 | yes | no |
| DF-001 | _retry_429_with_backoff 200-response return | downloader_throttle.py:182-183 | yes | no |
| DF-001 | _download_segment_sequential content-not-None check | downloader_throttle.py:112-114 | yes | no |
| DF-001 | _tally_and_merge glob count | segment_downloader.py:541 | yes | no |
| DF-001 | _tally_and_merge all(download_results) check | segment_downloader.py:548 | yes | no |
| DF-001 | _merge_segments_batched existence check | ffmpeg_utils.py:285 | yes | no |
| DF-002 | index-only segment filename | segment_downloader.py:626 | yes | no |
| DF-002 | resume skip (existence + size only) | segment_downloader.py:672 | yes | no |
| DF-002 | _parse_m3u8_segments call (no signature stored) | segment_downloader.py:734 (corrected from 534) | yes | no |
| DF-002 | downloaded_count glob | segment_downloader.py:541 | yes | no |
| DF-002 | count-mismatch abort | segment_downloader.py:554 | yes | no |
| DF-003 | failed_indices enumerate | segment_downloader.py:549 | yes | no |
| DF-003 | tasks created only for missing segments | segment_downloader.py:669-687 | yes | no |
| DF-004 | shared_semaphore from config | cli.py:272 | yes | no |
| DF-004 | DownloadContext (no peak field) | cli.py:69-77 | yes | no |
| DF-004 | Peak concurrency display | cli.py:362 | yes | no |
| DF-004 | config passed as peak | cli.py:593 | yes | no |
| DF-005 | as_completed display refresh | cli.py:305-320 | yes | no |
| DF-005 | callback state update | cli.py:95-96 | yes | no |
| DOC-UPDATE | "Resumes from last downloaded segment" | api-reference.md:447 | yes | no |

**Applicability and readiness:** All targets are present in the current source tree. The codebase is in
the audited green state (248 tests pass, ruff/mypy clean, all imports OK). No finding is rejected on
applicability or staleness grounds. Recommendations are operationally safe and aligned with existing
codebase patterns. This report validates safety, consistency, and applicability only — no source code
was modified.

---

## Warnings

- **DF-002 rollout — breaking existing partial downloads:** Changing the segment filename scheme (e.g.,
  appending a URL/content digest) means on-disk .ts files from previous runs with the old naming are
  not recognized. The recommended migration: clear stale .ts files whose indices exceed the current
  playlist length at session start (the finding's "at minimum" recommendation), or store a playlist
  signature in the segments dir. Without migration, users lose resume capability for in-flight downloads.
- **DF-001 — retry amplification risk:** Treating 0-byte segments as retryable failures (returning None
  to trigger the retry loop) is correct, but if the CDN persistently returns empty 200s for a given URL,
  the segment will exhaust all max_retries and fail. This is the desired behavior (fail loudly rather
  than silently corrupt), but the failure message should clearly indicate "empty content" vs. generic
  HTTP errors for operability.
- **DF-003 — downstream of DF-002:** The ailed_indices bug is a direct consequence of the resume-skip
  logic. Fixing DF-002 to carry real segment indices (e.g., list[tuple[int, bool]]) should be done
  before or alongside DF-003 to avoid implementing the fix twice.
- **DF-005 — interaction with CLI-005 (Phase 01):** DF-005's background polling task and CLI-005's
  s_completed→gather simplification both modify _run_batch_with_progress (cli.py:247-335).
  Implementing them in the wrong order causes redundant rework. Implement CLI-005 first.
- **Line-number discrepancies:** DF-002 cites segment_downloader.py:534 (actual: 734, function at 70-78);
  DF-003 cites segment_downloader.py:670-686 (actual: 669-687). Substance correct in both; only line
  pointers are imprecise.
- **R1 command inconsistency:** The source R1 command uses bare module names (config,
  services.downloader) alongside kdownloader.cli. Re-verified with consistent kdownloader.
  prefixes; all import cleanly. Conclusion unaffected.
- **No direct test coverage** for _run_parallel_download_with_backoff, _tally_and_merge,
  _create_segment_download_tasks, _print_batch_summary, or _run_batch_with_progress (grep in
  	ests/ returns 0 matches for each). The download_hls_with_resume tests mock
  _merge_segments_batched and _download_segment, so the 0-byte-segment and resume flows are
  untested end-to-end.

---

## Required Fixes (mandatory)

1. **DF-001** *(mandatory)*: After writing content on a 200 response, validate non-empty size in both
   download paths:
   - segment_downloader.py:160-163 (_run_parallel_download_with_backoff): check len(content) > 0
     or output_path.stat().st_size > 0 after write; return None (retryable) if empty.
   - downloader_throttle.py:182-183 (_retry_429_with_backoff): check len(content) > 0; return None
     if empty.
   - downloader_throttle.py:112-114 (_download_segment_sequential): the "" is not None check
     must also verify len(content) > 0.
2. **DF-002** *(mandatory)*: Bind on-disk segments to the current playlist:
   - Include a URL/content digest in the segment filename (e.g., "{i:05d}_{md5(url)[:8]}.ts"), or
   - Store a playlist signature (hash of segment URLs) in the segments directory and clear stale files
     whose indices or signatures do not match at session start.
   - At minimum: delete .ts files whose indices are >= len(segments) before creating download tasks.

---

## Advisory Recommendations

1. **DF-003** *(trivial)*: Track the actual segment index alongside each download result (e.g.,
   download_results as list[tuple[int, bool]] or preserve SegmentTask.idx), and compute
   ailed_indices from real segment indices instead of enumerate(download_results) positions.
2. **DF-004** *(small)*: Track actual concurrent in-flight downloads by incrementing/decrementing a counter
   when _download_single starts/completes (or when the semaphore is acquired/released), store it on
   DownloadContext, and report the measured peak instead of echoing settings.max_concurrent_downloads.
3. **DF-005** *(small)*: Add a background syncio.create_task that polls
   _progress_manager.get_formatted_progress(total) at 1-second intervals and refreshes the display
   independently of download completions; cancel the polling task after all downloads finish. Implement
   after CLI-005 (Phase 01) to avoid rewriting _run_batch_with_progress twice.
4. **DOC-UPDATE** *(trivial)*: Document the resume behavior as a known limitation until DF-002 is resolved:
   segments are identified by index only (no content validation), so playlist changes between runs may
   cause stale segment reuse. Add to pi-reference.md alongside the existing "Resumes from last
   downloaded segment" statement.
5. **Test coverage** *(recommended)*: Add tests for: 0-byte segment on 200 (DF-001), resume with a
   changed playlist (DF-002), ailed_indices correctness with skipped segments (DF-003), and measured
   peak concurrency < config value (DF-004).

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | DF-004 (SPEC-DEVIATION), DF-005 (BEST-PRACTICE) |
| Reclassified | 3 | DF-001 (RUNTIME-ERROR → SPEC-DEVIATION), DF-002 (RUNTIME-ERROR → SPEC-DEVIATION), DF-003 (RUNTIME-ERROR → SPEC-DEVIATION); DOC-UPDATE validated as-is |
| Merged | 0 | — |
| Rejected | 0 | — |
| New (from validation) | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| _(none)_ | — | All 5 source findings + 1 DOC-UPDATE were verified against current code and runtime. None stale, duplicated, speculative, or low-ROI. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| _(none)_ | — | DF-001 and DF-002 share the theme "missing content validation" but have distinct fix sites (download-path size check vs. resume-path content binding). DF-002 and DF-003 share a root-cause region (resume-skip logic) but distinct concerns (corruption vs. index reporting). Retained separately. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| DF-001 | RUNTIME-ERROR | SPEC-DEVIATION | RUNTIME-ERROR is outside the validator taxonomy. Confirmed at runtime/source: 0-byte segments pass all checks as "success," silently corrupting output. Code must change per project rules (correct downloads are a functional requirement). Precedent: Phase 03 SRV-001 (same reclassification). |
| DF-002 | RUNTIME-ERROR | SPEC-DEVIATION | Same taxonomy reason. Silent corruption + false-failure abort on resume is a correctness violation. Code must change. |
| DF-003 | RUNTIME-ERROR | SPEC-DEVIATION | Same taxonomy reason. Incorrect diagnostic output (wrong segment indices) is a correctness violation in reporting. Code must change. |
