# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification

| Step | Command | Result |
|------|---------|--------|
| R1 Import | uv run python -c "import vkdownloader.cli, config, services.downloader, services.segment_downloader, services.downloader_throttle, services.ffmpeg_utils, services.quality, services.cookies, services.signal_handlers, infrastructure.browser, infrastructure.network_monitor, utils.security, utils.url_sanitizer" (full pipeline) | ALL IMPORTS OK |
| R2 Lint | uv run ruff check src/vkdownloader | Pass — All checks passed! |
| R2 Types | uv run mypy src/vkdownloader | Pass — no issues found in 23 source files |
| R3 Tests | uv run pytest tests/ -q | Pass — 248 passed |
| R4 Empty-segment trace | Runtime simulation: 200 response with empty body (b"") in segment download path | Confirmed: 0-byte file written, returns True (success); reaches merge stage unhandled |
---

## Findings

### DF-001: Empty (0-byte) segment from HTTP 200 with empty body treated as a successful download

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py (_run_parallel_download_with_backoff), src/vkdownloader/services/downloader_throttle.py (_retry_429_with_backoff, _download_segment_sequential), src/vkdownloader/services/ffmpeg_utils.py (_merge_segments_batched) |
| **Classification** | mandatory |

**Description:** When the VK CDN returns an HTTP 200 response with an empty body (plausible during token expiry or CDN edge errors), the segment-download functions write a 0-byte .ts file and return True (success). The tally stage validates segment integrity by filename count (glob("*.ts")) and file existence, never by file size, so 0-byte segments pass every check and flow into the ffmpeg concat merge. ffmpeg then either errors on the empty segment (causing the entire video download to fail with a misleading error) or silently includes a blank segment in the output. The root cause is invisible to the user. On the sequential path, the same gap exists: response.read() returning b"" is written as 0 bytes and marked success because b"" is not None.

**Evidence:**
- segment_downloader.py:160-163 — parallel path, no size check after write:
  ```python
  if response.status == 200:
      with open(output_path, "wb") as f:
          f.write(await response.read())
      return True
  ```
- downloader_throttle.py:182-183 — sequential path returns raw content including b"":
  ```python
  if response.status == 200:
      return await response.read()
  ```
- downloader_throttle.py:112-114 — sequential wrapper treats b"" as success (b"" is not None):
  ```python
  if content is not None:
      with open(output_path, "wb") as f:
          f.write(content)
      return True
  ```
- segment_downloader.py:541 — integrity check is filename-count only:
  ```python
  downloaded_count = len(list(segments_dir.glob("*.ts")))
  ```
- segment_downloader.py:548 — all(download_results) is True because the 0-byte segment returned True.
- segment_downloader.py:554 — downloaded_count == len(segments) passes because the 0-byte .ts file exists on disk.
- ffmpeg_utils.py:285 — merge only checks existence, not size:
  ```python
  if not all(f.exists() for f in batch_files):
  ```
- Runtime verified: simulated a 200+empty-body response — download returns True, the 0-byte file passes _tally_and_merge checks, and ffmpeg fails at the merge step with a generic error.

**Recommendation:** After writing content on a 200 response, validate that the downloaded content is non-empty (len(content) > 0 / output_path.stat().st_size > 0). If empty, treat as a retryable failure (return None) so the retry loop re-attempts the segment. Effort: small. Priority: mandatory.

---
### DF-002: Resume logic reuses stale segments by filename index with no content or URL validation

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py (_create_segment_download_tasks, _tally_and_merge) |
| **Classification** | mandatory |

**Description:** When resuming a segment download after an interruption, _create_segment_download_tasks skips existing segments based solely on filename index and non-zero file size (segment_downloader.py:672). The segment filename is purely index-based (f"{i:05d}.ts", line 626) with no URL hash, playlist signature, or content fingerprint recorded. Two failure modes result: (1) Silent corruption — if a new playlist (e.g., after token refresh returns a fresh m3u8 from a different CDN edge) has the same segment count but different content at the same indices, existing on-disk segments are NOT re-downloaded, and the merge combines stale + fresh segments into a corrupt output reported as "success". (2) False failure — if the new playlist has a different segment count, leftover .ts files from the previous run cause downloaded_count != len(segments) (line 554), aborting the merge entirely even though all current playlist segments are present.

**Evidence:**
- segment_downloader.py:626 — segment filename is index-only, no URL/content binding:
  ```python
  segment_path = task.segments_dir / f"{task.idx:05d}.ts"
  ```
- segment_downloader.py:672 — resume skip checks existence + size only, no URL/content match:
  ```python
  if segment_path.exists() and segment_path.stat().st_size > 0:
      logger.debug("skipping_existing_segment", idx=i)
      continue
  ```
- segment_downloader.py:534 — _parse_m3u8_segments parses the current playlist but no signature is stored for comparison on resume.
- segment_downloader.py:541 — downloaded_count counts ALL .ts files including stale ones from a previous playlist.
- segment_downloader.py:554 — count-mismatch abort when stale files are present at non-overlapping indices:
  ```python
  if downloaded_count == len(segments):
  ```

**Recommendation:** Bind on-disk segments to the current playlist by including a URL/content digest in the filename (e.g., f"{i:05d}_{md5(url)[:8]}.ts"), or store a playlist signature (hash of segment URLs) in the segments directory and clear stale files whose indices or signatures do not match at session start. At minimum, delete .ts files whose indices are >= len(segments) before creating download tasks. Effort: medium. Priority: mandatory.

---
### DF-003: failed_indices in _tally_and_merge reports wrong segment indices

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py (_tally_and_merge, _create_segment_download_tasks) |
| **Classification** | advisory |

**Description:** _tally_and_merge computes failed_indices from enumerate(download_results) (line 549), but download_results corresponds only to the tasks created by _create_segment_download_tasks — which excludes segments that already existed on disk (skipped at line 672). So the index i in failed_indices is a position into the missing-segments task list, NOT the actual segment index in the playlist.

Example: playlist has segments [0,1,2,3,4]. Segments 0 and 2 already exist from a prior run. Segment 1 fails. Tasks are created for [1, 3, 4]. download_results = [False, True, True]. failed_indices = [0] (position of the False entry in the task list), but the actual failed segment is index 1.

**Evidence:**
- segment_downloader.py:549:
  ```python
  failed_indices = [i for i, r in enumerate(download_results) if not r]
  ```
- segment_downloader.py:670-686: tasks are created only for missing segments (existing ones skipped at line 672 via the continue statement).

**Impact:** The diagnostic log reports incorrect segment indices, directing developers/operators to the wrong segment when troubleshooting download failures.

**Recommendation:** Track the actual segment index alongside each download result (e.g., download_results as list[tuple[int, bool]] or preserve SegmentTask.idx), and compute failed_indices from the real segment indices. Effort: trivial. Priority: recommended.

---

### DF-004: Batch summary reports configured max_concurrent_downloads as Peak concurrency without measuring actual peak

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py (_run_batch_with_progress, _print_batch_summary) |
| **Classification** | advisory |

**Description:** _run_batch_with_progress creates a shared_semaphore from settings.max_concurrent_downloads (line 272) to cap concurrency, but no counter tracks the actual peak number of concurrent downloads. The batch_download command passes settings.max_concurrent_downloads directly to _print_batch_summary as the "peak" value (line 593), and _print_batch_summary displays it verbatim as "Peak concurrency" (line 362). The DownloadContext dataclass (lines 69-77) has no field for tracking observed concurrency.

When the number of batch URLs is less than max_concurrent_downloads, the reported "Peak concurrency" is higher than what actually occurred (e.g., "Peak concurrency: 4" for a 2-URL batch where the actual peak was 2).

**Evidence:**
- cli.py:272 — semaphore created from config, no peak counter:
  ```python
  shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
  ```
- cli.py:69-77 — DownloadContext has no peak-tracking field.
- cli.py:362 — config value displayed as peak:
  ```python
  typer.echo(f"  Peak concurrency: {max_concurrent}")
  ```
- cli.py:593 — config value passed as "peak":
  ```python
  _print_batch_summary(results, settings.max_concurrent_downloads, skipped_count)
  ```

**Recommendation:** Track actual concurrent in-flight downloads by incrementing/decrementing a counter when _download_single starts/completes (or when the semaphore is acquired/released) and report the measured peak. Effort: small. Priority: recommended.

---

### DF-005: Batch progress display only refreshes on download completion, not in real time

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py (_run_batch_with_progress) |
| **Classification** | advisory |

**Description:** The batch progress display refreshes only after each await coro completes in the as_completed loop (cli.py:307-320). The typer.echo at line 320 runs only after a full video download finishes. During a long-running download, progress callbacks do update _progress_manager (line 96), but the display is never refreshed. The user sees stale progress (frozen on the last completed download) for the entire duration of in-progress downloads, with no indication of ongoing activity.

**Evidence:**
- cli.py:305-320 — display only updated post-completion:
  ```python
  for coro in asyncio.as_completed(tasks):
      try:
          await coro
      except asyncio.CancelledError:
          ...
      except Exception:
          logger.exception("unexpected_error_in_batch_progress")
      typer.echo(f"\r{await _format_progress(total)}", nl=False)  # only after await coro
  ```
- cli.py:95-96 — callbacks update _progress_manager.update_sync(url_index, ...) but display isn't refreshed between completions.

**Recommendation:** Run a background asyncio.create_task that polls _progress_manager.get_formatted_progress(total) at a 1-second interval and refreshes the display independently of download completions; cancel the polling task after all downloads finish. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 3 |

## Mandatory Fixes

- **[DF-001]** Add a content-size check after segment download: validate `len(content) > 0` (or `st_size > 0`) on HTTP 200 responses in both `_run_parallel_download_with_backoff` (segment_downloader.py:160-163) and `_retry_429_with_backoff` / `_download_segment_sequential` (downloader_throttle.py:182-183, 112-114). Treat empty content as a retryable failure so the segment is re-attempted instead of being merged as 0 bytes.
- **[DF-002]** Bind on-disk segments to the current playlist in the resume logic: either include a URL/content digest in the segment filename, or store a playlist signature in the segments directory and clear stale files at session start. At minimum, delete .ts files whose indices exceed the current playlist length.

## Advisory Recommendations

- **[DF-003]** Fix failed_indices computation in _tally_and_merge to report actual segment indices (not task-list positions) for accurate diagnostics.
- **[DF-004]** Measure and report actual peak concurrency in the batch summary instead of echoing the configured max_concurrent_downloads value.
- **[DF-005]** Add a background polling task to refresh the progress display in real time during long-running batch downloads.

## Doc Updates Needed

- **[DOC-UPDATE]** Document the resume behavior: segments are identified by index only (no content validation), so playlist changes between runs may cause stale segment reuse. Consider documenting this as a known limitation until DF-002 is resolved. Effort: trivial.
