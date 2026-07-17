# Phase 06 Audit Findings — End-to-End Data Flow (Validated)

**Source:** `.ai/audit/06-data-flow/findings.md`  
**Validator:** validator  
**Date:** 2026-07-17

---

## Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 1 | DF-005 |
| Reclassified | 1 | DF-004 (RUNTIME-ERROR → SPEC-DEVIATION) |
| Rejected | 1 | DF-006 |
| Cross-Phase Conflicts | 3 | DF-001, DF-002, DF-003 referenced but exist in other phases |

---

## Findings

### DF-004: Corrupt/partial segment file is treated as complete on resume

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | MEDIUM |
| **Type** | ~~RUNTIME-ERROR~~ SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (`_download_segment_concurrent`, `_create_segment_download_tasks`) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type RUNTIME-ERROR reclassified to SPEC-DEVIATION. The implementation violates the expected invariant that resume logic should validate segment integrity. The code trusts `size > 0` as proof of successful download, but this is a correctness issue — the spec for resume should include validation, and the implementation omits it.
> - **See also:** —

**Description:** The segment-level resume logic treats any existing `.ts` file with `size > 0` as successfully downloaded and skips re-downloading it (`segment_downloader.py:563`). A segment that was partially written when the process crashed (or was truncated by an interrupted write) leaves a non-empty `.ts` on disk. On the next run, `_create_segment_download_tasks` excludes it from the work list (`:645-646`), and `_download_segment_concurrent` returns `True` for it (`:563-564`). The merge then concatenates the corrupt segment into the final MP4, producing a broken/glitchy file — often with no error if ffmpeg still completes. This silently corrupts output while reporting success.

**Evidence:**
- `segment_downloader.py:563-564`: `if segment_path.exists() and segment_path.stat().st_size > 0: result = True`
- `segment_downloader.py:645-646`: tasks only created for segments that do not exist OR have `st_size == 0`, so a partial non-empty file is never re-fetched.
- `_process_downloaded_segments:504-511`: merge proceeds when `downloaded_count == len(segments)`; a corrupt segment counts toward completion.

**Recommendation:** Validate segment integrity before accepting a cached `.ts` (e.g. compare expected size from the playlist `#EXTINF`/byte-range, or re-fetch if a known-good size is available), or at minimum verify ffmpeg merge return code and treat merge failure as a retryable error rather than returning the corrupt output. At a minimum, do not treat `size > 0` as "complete" for resume.

---

### DF-005: AUTO download method does not apply cookie resolution

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download` AUTO branch) |
| **Classification** | advisory |

**Description:** Both `YTDLP` (`:704-720`) and `FFMPEG` (`:721-743`) branches call `_resolve_cookies()` to apply `cookie_source`-based authentication before download. The `AUTO` branch (`:744-756`) calls `download_with_ytdlp_with_resume_fallback` directly without `_resolve_cookies`. With `cookie_source=BROWSER`, the first yt-dlp attempt therefore runs without cookies; only the failure-triggered segment resume forces a browser refresh. This is an inconsistency that wastes the first attempt and diverges from the other methods' behavior.

**Evidence:**
- `downloader.py:744-756`: AUTO branch lacks the `_resolve_cookies` call present in the YTDLP/FFMPEG branches (`downloader.py:705-707`, `:722-724`).

**Recommendation:** Call `_resolve_cookies` in the AUTO branch as well so cookie auth is applied on the first attempt, matching YTDLP/FFMPEG and reducing avoidable failures. Effort: trivial.

---

### DF-006: ~~Batch summary masks unexpected exceptions as "cancelled"~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | DF-006 |
| **Severity** | LOW |
| **Affected Modules** | `src/vkdownloader/cli.py` (`_run_batch_with_progress`, `_download_single`) |
| **Classification** | ~~advisory~~ |

> **Rejection reason:** The finding is inaccurate. Investigation confirms:
> - `cli.py:153-156`: `_download_single` does **re-raise** unexpected exceptions with `raise`, as the finding states.
> - `cli.py:229-233`: `asyncio.gather(*tasks, return_exceptions=True)` is used, and the fallback `r if isinstance(r, tuple) else (urls[i], "", "cancelled")` processes results.
> - However, the `for coro in asyncio.as_completed(tasks)` loop at lines 214-226 **already catches `CancelledError`** and re-raises it, which propagates to `batch_download`'s try block that catches `(KeyboardInterrupt, asyncio.CancelledError)` at line 461-463.
> - The real issue is that `_download_single` re-raises exceptions (line 156), and these propagate through the `as_completed` loop uncaught, causing the raw traceback. This was correctly identified as CLI-002 in Phase 01 (HIGH severity), not a separate data-flow issue.
> - Additionally, the fallback logic for non-tuple results is a defensive coding pattern. Since `_download_single` returns a tuple on all successful paths and re-raises on exceptions, exceptions reaching the gather result would be exception objects (not tuples). Labeling them as "cancelled" may be semantically inaccurate, but the actual problem — uncaught exceptions crashing the batch — is already captured in CLI-002.
> - This finding duplicates CLI-002 with less accurate root-cause analysis. The primary issue (unexpected exceptions escape and crash the batch) is already addressed in Phase 01.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 1 | DF-005 |
| Reclassified | 1 | DF-004 (RUNTIME-ERROR → SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 1 | DF-006 (duplicate of CLI-002) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| DF-006 | Batch summary masks unexpected exceptions as "cancelled" | Duplicate of CLI-002 (Phase 01). The core issue — unexpected exceptions escaping and crashing the batch — is already captured. The fallback labeling is a secondary concern. |

### Merged Findings

None.

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| DF-004 | RUNTIME-ERROR | SPEC-DEVIATION | The implementation violates the expected invariant that resume logic should validate segment integrity. This is a correctness/spec-deviation issue, not just a runtime error. |

---

## Cross-Phase Conflicts Detected

The Phase 06 findings summary references DF-001, DF-002, and DF-003 as mandatory fixes, but these findings are **not present in the Phase 06 findings file**. Cross-phase analysis identifies:

| Phase 06 Reference | Actual Location | Status |
|-------------------|-----------------|--------|
| DF-001 (download_timeout) | INT-003 (Phase 05) | **Already validated** in Phase 05. `downloader.py:528` hardcodes `"socket_timeout": 180` while `settings.download_timeout` is available. |
| DF-002 (filename collision) | Not found in any phase | **Potential missing finding** or incorrectly referenced. The `_sanitize_title` function could produce identical outputs for different titles (e.g., titles differing only by trailing whitespace become identical). No previous phase addresses this. |
| DF-003 (CookieSource.FILE) | SRV-003 (Phase 03) / INT-008 cross-reference | **Already validated** in Phase 03. `extractor.py:123-126` raises `NotImplementedError`, while `api-reference.md:99` incorrectly states "Placeholder returns streams without cookies". |

---

## Rollout Safety Notes

| ID | Risk | Mitigation |
|----|------|------------|
| DF-004 | HIGH | Segment integrity check must handle missing size metadata gracefully (e.g., when m3u8 does not provide byte ranges). Consider adding size validation only when available, or using CRC/hash comparison as fallback. |
| DF-005 | LOW | Adding `_resolve_cookies` call to AUTO branch is low-risk; the function already handles `CookieSource.BROWSER` and `CookieSource.NONE` correctly. |

---

## Dependency Chain

- DF-005 (cookie resolution) is independent — can be addressed in any order relative to other issues.
- DF-004 (segment integrity) involves the same `_process_downloaded_segments` path that INT-006 (Phase 05) targets for observability; these can be addressed together or independently.