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

**Recommendation:** Reset progress metadata at the start of a fresh download_hls_with_resume invocation (or make resume explicitly opt-in), and base the merge decision on on-disk segment count (segments_dir.glob("*.ts")) rather than accumulated counter.

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

**Recommendation:** When resuming, filter the segment list to files not already present in segments_dir (and whose size is non-zero). Write the completion check against the on-disk count.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | DF-001, DF-002 |
| Reclassified | 0 | |
| Merged | 0 | |
| Rejected | 0 | |

### Rejected Findings

No findings rejected.

### Merged Findings

No findings merged. The issues are related but describe distinct aspects:
- DF-001 focuses on the merge-trigger bug
- DF-002 focuses on the redundant-download bug

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
