# Phase 06 Audit Validation — End-to-End Data Flow

**Source:** .ai/audit/06-data-flow/findings.md
**Validator:** validator
**Date:** 2026-07-20

---

## Findings

### DF-001: Resume metadata is never reset; accumulated count can exceed total and permanently skip the merge

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR / SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/downloader.py |

**Description:** download_hls_with_resume() (segment_downloader.py:764) is documented as "segment-level download can resume after interruption by re-downloading missing segments" (docs/01-tools/vkdownloader-overview.md:16, :251). In reality it never resets the progress metadata or the segments directory at start, and the merge-completion check uses an accumulated count rather than the count of segments present on disk.

**Evidence:**
- segment_downloader.py:796-802 — no reset of segments_dir / metadata_file before download
- segment_downloader.py:540-556 — downloaded_count = _load_downloaded_count(...) + sum(...), merge only when == len(segments)
- downloader.py:400-437 — download_with_ytdlp_with_resume_fallback loops up to MAX_RESUME_RETRIES calling _attempt_segment_resume

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms the bug. Line 796-802 creates the directories with exist_ok=True but never deletes existing .ts files or resets metadata. Line 540 accumulates counts across runs, causing merge to never trigger when re-invoked. This is a SPEC-DEVIATION: the documented resume behavior does not match the implementation.
> - **See also:** DF-002, SRV-003 (Phase 03 - duplicate issue)

**Recommendation:** In `segment_downloader.py`, modify `_create_segment_download_tasks` (line 652) to filter out segments whose `.ts` file already exists with non-zero size (check `segments_dir / f"{i:05d}.ts"` before creating task); then modify `_tally_and_merge` (line 540) to compute `downloaded_count = len(list(segments_dir.glob("*.ts")))` (on-disk count only, not additive) and persist to metadata only when `downloaded_count == len(segments)`. This fixes both the redundant-download bug and the incomplete-merge bug with minimal changes. See SRV-003 (Phase 03) for the authoritative validated recommendation — this fix resolves both DF-001 and DF-002.

**Investigation (2026-07-20):** Code analysis confirms the additive counter in `_tally_and_merge` (line 540) causes double-counting: if 50 segments downloaded then `_load_downloaded_count` returns 50, and a resumed run adds another 50, yielding `downloaded_count = 100` which never equals `len(segments) = 50`. Simultaneously, `_create_segment_download_tasks` (lines 665-677) creates tasks for all segments without checking for existing files. The fix is to skip existing segments and use only the on-disk count for merge decisions.

**Note:** This finding is a duplicate of SRV-003 (Phase 03). The single fix under SRV-003 resolves both DF-001 and DF-002.

---

### DF-002: "Segment-level resume" re-downloads all segments instead of only missing ones

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |

**Description:** Documentation states the segment downloader "resumes after interruption by re-downloading missing segments" (docs/01-tools/vkdownloader-overview.md:251). The implementation creates download tasks for every segment on each call. _create_segment_download_tasks (lines 652-677) iterates over the full segments list and writes each to segment_path with open("wb"), overwriting any previously downloaded file.

**Evidence:**
- segment_downloader.py:651-677 — tasks created for all segments, no skip of already-present files
- segment_downloader.py:540 — downloaded_count read from metadata but not used to filter the task list

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms _create_segment_download_tasks creates ALL segment tasks without checking for existing files. The downloaded_count metadata value is used only for display/logging, not for skipping existing segments. This is a SPEC-DEVIATION: documented behavior contradicts implementation.
> - **See also:** DF-001

**Recommendation:** When resuming, filter the segment list to files not already present in segments_dir (and whose size is non-zero). Write the completion check against the on-disk count. **Note:** This finding is a duplicate of SRV-003 (Phase 03). The single fix under SRV-003 resolves both DF-001 and DF-002.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 0 | DF-001/DF-002 re-validated then consolidated |
| Reclassified | 0 | |
| Merged | 2 | DF-001, DF-002 consolidated into SRV-003 |
| Rejected | 0 | |

### Rejected Findings

No findings rejected.

### Merged Findings

DF-001 and DF-002 are duplicates of SRV-003 (Phase 03). Per the Cross-Phase Analysis, fix efforts should consolidate under SRV-003. The actionable recommendation from SRV-003 resolves both findings:
- Skip segments whose file already exists (lines 665-677 in `_create_segment_download_tasks`)
- Use on-disk segment count instead of additive counter (line 540 in `_tally_and_merge`)

### Reclassified Findings

No findings reclassified.

---

## Rollout Analysis

Findings are operationally isolated to segment_downloader.py. No rollout safety issues detected. Changes involve:
- Adding logic to check for existing segment files before download
- Resetting metadata at appropriate entry points
- Both are backward-compatible (existing behavior works, fixes improve correctness)

---

## Cross-Phase Analysis

### DF-001/DF-002 Duplicate with Phase 03

**Critical Conflict:** DF-001 and DF-002 are nearly identical to SRV-003 from Phase 03 ("Segment resume double-counts progress and can never complete a resumed run"). The Phase 03 finding provides equivalent analysis and was validated separately.

**Recommendation:** Consolidate fix efforts under SRV-003 (Phase 03) which has higher visibility and includes the related SRV-007 finding.
