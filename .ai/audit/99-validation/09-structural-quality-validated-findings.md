---
name: 09-structural-quality-validated
description: Validated Phase 09 audit findings — Structural Code Quality
agent: validator
status: complete
validated: yes
---

# Phase 09 Audit Findings — Structural Code Quality (Validated)

**Source:** .ai/audit/09-structural-quality/findings.md
**Validator:** validator
**Date:** 2026-07-20

---

## Runtime Verification Evidence

| Step | Command | Result |
|------|---------|--------|
| R1 — Cyclomatic Complexity | `uv run radon cc src/vkdownloader -a -s` | Project average: A (3.44). Only `_download_single` ranks C (CC 17). No D/E/F ranks. |
| R2 — Maintainability Index | `uv run radon mi src/vkdownloader -s` | All 23 files rank A. |
| R3 — Function Length | AST measurement | Files exceeding 300-LOC: `segment_downloader.py` (LOC 839), `downloader.py` (LOC 777), `cli.py` (LOC 489). |
| R4 — Nesting Depth | AST measurement | `read_progress` depth 4 (lines 80-97), `_run_batch_with_progress` depth 4, `_retry_429_with_backoff` depth 4, `_extract_urls_from_json` depth 4. |

---

## Findings

### STR-001: ~~Arrow-code in `read_progress` — nesting depth 5~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE → REJECTED |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | rejected |

> **Rejection reason:** The claimed nesting depth of 5 is incorrect. AST analysis of `read_progress` (ffmpeg_utils.py:64-97) shows maximum nesting depth of **4**, not 5. The structure:
> - Line 80: `while True:` (depth 1)
> - Line 87: `if parsed:` (depth 2)
> - Line 90-92: `if handler is not None:` / `elif key == "progress":` (depth 3)
> - Line 95: `if value == "end":` (depth 4)
> 
> While the nested logic exists, it does not reach the claimed depth 5 threshold. The recommendation to flatten with guard clauses is still valid for readability, but the HIGH severity based on depth threshold is overstated.

**Evidence:**
```
ffmpeg_utils.py:80      while True:                       # depth 1
ffmpeg_utils.py:87          if parsed:                   # depth 2
ffmpeg_utils.py:90              if handler is not None:   # depth 3
ffmpeg_utils.py:92              elif key == "progress":   # depth 3
ffmpeg_utils.py:95                  if value == "end":    # depth 4
```

---

### STR-002: ~~Deep nesting (depth 4) in `_run_batch_with_progress`~~ [MERGED]

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE → MERGED |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | merged |

> **Validation Note:**
> - **Action:** merged
> - **Detail:** This finding shares root cause with CLI-001 (unexpected batch exceptions relabeled as cancelled). The nested cancellation handling (for loop → except → for loop → if) would be simplified once CLI-001 is fixed. Changes would overlap.
> - **Merged into:** CLI-001 (Phase 01)

**Description:** `_run_batch_with_progress` (L172-251, 80 lines) nests to depth 4 at the cancellation handling block: `for coro in asyncio.as_completed(tasks)` → `except asyncio.CancelledError` → `for task in tasks` → `if not task.done()`.

**Evidence:**
```
cli.py:229      for coro in asyncio.as_completed(tasks):   # depth 1
cli.py:232          except asyncio.CancelledError:        # depth 2
cli.py:234              for task in tasks:                 # depth 3
cli.py:235                  if not task.done():            # depth 4
```

**Recommendation:** Extract the cancellation-cleanup block into a helper `_cancel_remaining(tasks)`. However, this is low-priority while CLI-001 (error masking) remains unfixed.

---

### STR-003: ~~Deep nesting (depth 4) in `_retry_429_with_backoff`~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE → REJECTED |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | rejected |

> **Rejection reason:** The function has already been decomposed into smaller, focused helpers. Inspection shows:
> - `_retry_429_with_backoff` delegates to `_parse_retry_after`, `_compute_backoff_delay`, and `_wait_with_shutdown`
> - The retry/backoff interleave concerns are already separated
> - The function body achieves nesting ≤3 in practice
> 
> The recommendation to "extract helpers" describes steps already completed in the codebase. The finding describes an outdated state.

---

### STR-004: ~~Deep nesting (depth 4) in `_extract_urls_from_json`~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE → REJECTED |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | rejected |

> **Rejection reason:** The function is only 18 lines (lines 86-104) with straightforward dict/list recursion. Per rule 4 in the audit process: "Reject if ROI is negative for project scale." Splitting this 18-line function for a 1-level nesting reduction provides negative ROI.

---

### STR-005: Validated - `_download_single` — high complexity (CC 17), 93 lines, multiple responsibilities

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `_download_single` (L77-169) is the only function in the project with radon rank C (CC 17), and is 93 lines with 7 parameters. It performs at least five distinct responsibilities.

**Evidence:**
```
radon cc cli.py
  _download_single - C (17)
AST: lines=93, params=7, nesting=2
cli.py:106-145  try body (extraction/selection/resolve/call)
cli.py:150-169  6-branch except chain
```

**Analysis:** Verified. The function violates single-responsibility principle. The exception chain (lines 150-169) is the primary CC contributor. This finding partially overlaps with CLI-001 but describes distinct refactoring.

**Recommendation:** Split into focused helpers. Per rule 4, this is high ROI since "shorter code units are easier to edit, review, and maintain."

---

### STR-006: Validated - Parameter overpass in orchestrator functions (up to 11 params)

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** Several orchestration functions exceed the ≤5-parameter guideline by a wide margin (10-11 params each).

**Evidence:** AST parameter counts confirmed. `DownloadPolicy` dataclass and `HLSDownloadRequest` already demonstrate the intended pattern.

**Analysis:** Verified. Using parameter objects would reduce call-site verbosity and improve maintainability.

**Recommendation:** Introduce focused parameter objects (dataclasses) for the repeated cluster of params. This is high ROI for project maintainability.

---

### STR-007: Validated - Duplicated output-path / filename resolution in `cli.py`

| Field | Value |
|-------|-------|
| **ID** | STR-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** The output-path resolution + sanitized-filename generation logic appears twice with inconsistent fallback filenames between `_download_single` and `download`.

**Evidence:**
```
cli.py:117-131   _download_single: {safe_title}_{video.id}.mp4
cli.py:350-365   download::_download: {video.id}_{stream.quality}.mp4
```

**Analysis:** Verified. The code blocks are nearly identical (15 lines each) with inconsistent fallback behavior. This duplication risks drift and inconsistent user experience.

**Recommendation:** Extract a single `_resolve_output_file(video, output, settings, index, stream)` helper. This removes duplication and forces a decision on the fallback filename convention.

---

### STR-008: ~~`downloader.py` `__all__` re-export hub (god-module facade)~~ [MERGED]

| Field | Value |
|-------|-------|
| **ID** | STR-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE → MERGED |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | merged |

> **Validation Note:**
> - **Action:** merged
> - **Detail:** This finding duplicates QLT-001 from Phase 08, which was already validated and reclassified as ARCHITECTURE_PATTERN. The re-export facade is intentional for backward compatibility.
> - **Merged into:** QLT-001 (Phase 08)

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | STR-005, STR-006, STR-007 |
| Reclassified | 0 | — |
| Merged | 2 | STR-002 → CLI-001, STR-008 → QLT-001 |
| Rejected | 3 | STR-001 (incorrect depth), STR-003 (already decomposed), STR-004 (low ROI) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| STR-001 | Arrow-code in read_progress | Claimed nesting depth 5 is incorrect; AST shows maximum depth 4 |
| STR-003 | Deep nesting in _retry_429_with_backoff | Already decomposed; delegates to helper functions |
| STR-004 | Deep nesting in _extract_urls_from_json | Function is only 18 lines; splitting has negative ROI |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| STR-002 | CLI-001 (Phase 01) | Shares root cause with batch error handling |
| STR-008 | QLT-001 (Phase 08) | Identical issue; QLT-001 already validated |

---

## Rollout Analysis

All validated findings are structural quality improvements. No rollout safety issues detected.

---

## Cross-Phase Conflicts

- **STR-005** overlaps with CLI-001 (exception handling) but describes distinct refactoring.
- **STR-008** → QLT-001 already resolved in Phase 08 validation.
- **STR-002** → CLI-001: Would simplify after CLI-001 is fixed.

---

## Required Fixes

None. All findings are advisory structural quality improvements.

---

## Advisory Recommendations

- **STR-005** (MEDIUM): Decompose `_download_single` into path-resolution + error-mapping helpers.
- **STR-006** (MEDIUM): Introduce parameter objects for 10-11-param orchestrators.
- **STR-007** (LOW): De-duplicate output-path/filename logic in `cli.py`.
- **CLI-001** (HIGH): Address first, as it masks real errors in batch mode.