---
name: 09-structural-quality
description: Structural Code Quality Audit Findings
agent: auditor
status: complete
validated: no
---

# Phase 09 Audit Findings — Structural Code Quality

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** no

---

## Findings

### STR-001: Function with Excessive Cyclomatic Complexity (Rank D - CRITICAL)

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | CRITICAL |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The `read_progress` function at line 69 has cyclomatic complexity of 21 (Rank D), far exceeding the recommended threshold of 10. This function contains a while loop with nested if-elif chains for parsing ffmpeg progress output, creating an arrow-code pattern that is hard to understand and test. The nesting depth of 11 levels indicates deeply nested conditionals that contribute to the high complexity.

**Evidence:**
```
src\vkdownloader\services\downloader.py
    F 69:0 read_progress - D (21)
```
Function spans lines 69-114 with deep nesting chain: while → if → if → if → elif → elif → elif → elif → elif → elif → elif → if

**Recommendation:** Extract the parsing logic into a lookup table or dispatch pattern. Replace the if-elif chain for each key (frame, fps, speed, total_size, out_time_us, out_time_ms, out_time, progress) with a dictionary mapping keys to attribute setters. This would reduce nesting depth from 11 to 2 and improve testability. Effort: medium.

---

### STR-002: Function with Excessively Deep Nesting Depth (HIGH)

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The `download_hls_with_resume` function (lines 312-461, 150 lines) has nesting depth of 7 and contains 5 return statements. This function orchestrates segment downloading with multiple layers of control flow: try/with/async for/try/if/for/if/try/try. The function also defines a nested inner function `download_segment_concurrent` which adds to cognitive complexity.

**Evidence:**
```
src\vkdownloader\services\downloader.py
    F 312:0 download_hls_with_resume - C (19)
```
Nesting structure includes: try → async with → if → for → async def → async with → if → try → async with → if → for → try → except

**Recommendation:** Extract the inner `download_segment_concurrent` function to module level. Split the large function into smaller focused functions: `_create_segment_tasks()`, `_process_segment_results()`, `_handle_segment_download()`. Use early returns to flatten conditionals. Effort: large.

---

### STR-003: Function with Excessive Parameters (HIGH)

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The `perform_download` function has 9 parameters, exceeding the recommended limit of 5. This indicates the function is doing too much and has too many responsibilities. Multiple parameters are related (backoff_coordinator, semaphore, progress_callback) and could be consolidated.

**Evidence:**
```
src\vkdownloader\services\downloader.py
    F 1034:0 perform_download - C (12), params=9
```
Function signature at lines 1034-1043 spans 10 parameters including optional backoff_coordinator, semaphore, and progress_callback.

**Recommendation:** Create a `DownloadContext` or `DownloadOptions` dataclass to group the optional parameters (backoff_coordinator, semaphore, progress_callback) together. This reduces parameter count to 4 required + 1 grouped. Effort: small.

---

### STR-004: Function with Excessive Parameters and High Complexity (HIGH)

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The `_download_segment` function (lines 518-575, 58 lines) has 8 parameters and 6 return statements with nesting depth of 4. The function has two distinct code paths (sequential with retry vs parallel mode) that share minimal logic, indicating it should be split into separate functions.

**Evidence:**
```
src\vkdownloader\services\downloader.py
    F 518:0 _download_segment - C (12), params=8, returns=6, depth=4
```

**Recommendation:** Split into `_download_segment_sequential()` and `_download_segment_parallel()` functions. Each would have 4-5 parameters and handle their specific logic without shared branches. Effort: medium.

---

### STR-005: Function with Excessive Parameters in Retry Logic (MEDIUM)

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader_throttle.py`, `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** Multiple functions have excessive parameters related to retry/backoff logic: `_fetch_playlist_with_retry` (7 params), `_retry_429_with_backoff` (6 returns, depth=5), and `_parse_retry_after` (4 returns). These functions are tightly coupled with retry concerns.

**Evidence:**
```
src\vkdownloader\services\downloader.py
    F 464:0 _fetch_playlist_with_retry - B (9), params=7, depth=6
src\vkdownloader\services\downloader_throttle.py
    F 142:0 _retry_429_with_backoff - B (10), returns=6, depth=5
    F 238:0 _parse_retry_after - A (4), returns=4
```

**Recommendation:** Consider consolidating retry-related parameters into a configuration object. The `_parse_retry_after` function's multiple return statements could be simplified with guard clauses. Effort: small.

---

### STR-006: CLI Functions with Excessive Parameters (MEDIUM)

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\cli.py` |
| **Classification** | advisory |

**Description:** CLI functions have excessive parameters: `download` has 6 params and `batch_download` has 7 params. While CLI commands often have many options, the `batch_download` function also has nesting depth of 5 due to nested async functions and complex control flow.

**Evidence:**
```
src\vkdownloader\cli.py
    F 182:0 batch_download - C (14), params=7, depth=5
    F 77:0 download - B (8), params=6
```

**Recommendation:** The parameter count is a CLI design constraint (Typer options), but the nesting depth in `batch_download` could be reduced by extracting `_download_single` logic to module level and simplifying `_run_batch_with_progress`. Effort: small.

---

### STR-007: File Exceeds Recommended Line Count (MEDIUM)

| Field | Value |
|-------|-------|
| **ID** | STR-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The `downloader.py` file has 956 lines, far exceeding the recommended 300-line limit for source files. This is a "god module" that contains HLS downloading, ffmpeg process management, segment merging, signal handling, and download orchestration logic.

**Evidence:**
```
Lines in src\vkdownloader\services\downloader.py: 956
```

**Recommendation:** Split into focused modules: `hls_downloader.py` (segment download logic), `ffmpeg_processor.py` (progress parsing, merging), `download_orchestrator.py` (perform_download, download_with_ytdlp_with_resume_fallback). Effort: large.

---

### STR-008: Multiple Return Statements in Control Flow (LOW)

| Field | Value |
|-------|-------|
| **ID** | STR-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader_throttle.py` |
| **Classification** | advisory |

**Description:** The `_parse_retry_after` function has 4 return statements in a simple parsing function. While not critical, this pattern could be simplified with guard clauses for early exits.

**Evidence:**
```
src\vkdownloader\services\downloader_throttle.py (lines 238-271)
return None (line 251), return float (line 255), return delta (line 267), return None (line 271)
```

**Recommendation:** Apply guard clause pattern: return early on missing header, return early on successful integer parse, return early on successful date parse. This clarifies the single responsibility. Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 3 |
| MEDIUM | 2 |
| LOW | 1 |

## Advisory Recommendations

- **STR-001:** Refactor `read_progress` with lookup table dispatch to reduce complexity
- **STR-002:** Split `download_hls_with_resume` into smaller focused functions
- **STR-003:** Consolidate optional download parameters into a dataclass
- **STR-004:** Split `_download_segment` into sequential/parallel variants
- **STR-005:** Simplify retry function parameter lists and control flow
- **STR-006:** Reduce CLI function nesting through extraction
- **STR-007:** Split the 956-line downloader.py into focused modules
- **STR-008:** Apply guard clause pattern in `_parse_retry_after`

---

## Radon Analysis Summary

**Average Complexity:** A (3.46) — exceeds target of ≤5

**Functions with Rank C (complexity 11-20):**
- `read_progress` — Rank D, complexity 21 (CRITICAL)
- `download_hls_with_resume` — Rank C, complexity 19 (HIGH)
- `_download_segment` — Rank C, complexity 12 (MEDIUM)
- `download_with_ytdlp_with_resume_fallback` — Rank C, complexity 12 (MEDIUM)
- `perform_download` — Rank C, complexity 12 (MEDIUM)

**Functions with Rank B (complexity 6-10):**
- `_retry_429_with_backoff` — Rank B, complexity 10
- `_fetch_playlist_with_retry` — Rank B, complexity 9
- `download` (cli.py) — Rank B, complexity 8
- `batch_download` (cli.py) — Rank C, complexity 14 (MEDIUM)

**Maintainability Index:** All files rank A, but `downloader.py` scored 22.56 (lowest), indicating maintainability concerns due to file size and complexity.