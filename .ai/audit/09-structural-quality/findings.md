---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 09 Audit Findings — Structural Code Quality

**Executor:** audit-executor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### STR-001: `read_progress` function has CRITICAL cyclomatic complexity (rank D)

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | CRITICAL |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `read_progress` async generator function at line 66 has cyclomatic complexity of 21 (rank D), significantly exceeding the recommended threshold of 10. This is caused by a long if/elif chain with 9 branches for parsing different ffmpeg progress keys. The function is 46 lines with multiple conditional branches inside a while loop, making it hard to test and maintain.

**Evidence:** `radon cc src/ -s` output: `F 66:0 read_progress - D (21)`. The function contains a `while True` loop with an if/elif chain of 9 branches (lines 91-111), each with conditional assignments.

**Recommendation:** Extract the key-value parsing logic into a separate helper method or use a dispatch table (dictionary mapping). Replace the if/elif chain with a lookup table: `{key: handler}` where each handler is a small function that processes the value. This reduces complexity to near 1 and improves testability. Effort: small.

---

### STR-002: `download_hls_with_resume` function exceeds length and nesting limits

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `download_hls_with_resume` function at line 296 is 125 lines long (exceeds 50 line limit) with nesting depth of 6 levels (exceeds 3 level limit) and cyclomatic complexity of 13 (rank C). The function defines nested async helper function `download_segment_concurrent` inside the main function, creating deeply nested control flow.

**Evidence:** `radon cc src/ -s` shows CC=13 (rank C). Function spans lines 296-422. Nesting path: `try -> async with ClientSession -> async def download_segment_concurrent -> async with semaphore -> if -> if` reaches 6 levels. Contains ~4 return points.

**Recommendation:** Extract the nested `download_segment_concurrent` function to module level. Split the segment download orchestration from the merge logic. Consider separating: (1) segment downloading, (2) progress tracking, (3) batch merging into distinct functions. Effort: medium.

---

### STR-003: `download_with_ytdlp_with_resume_fallback` has HIGH complexity and nesting

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `download_with_ytdlp_with_resume_fallback` function at line 805 has cyclomatic complexity of 12 (rank C), is 94 lines long, and has nesting depth of 6 levels. It combines retry logic, token refresh, and fallback switching in a single function with multiple return points.

**Evidence:** `radon cc src/ -s` shows CC=12 (rank C). Function spans lines 805-898. Nesting path: `while -> if result -> if validated_output.exists -> if retry_count <= MAX_RESUME_RETRIES -> try -> if extractor is None -> if browser_streams` reaches 6 levels. Contains ~5 return points.

**Recommendation:** Extract the retry loop into a separate function. Pull the segment resume logic (`_attempt_segment_resume`) into its own function. Use early returns to flatten the nesting. Effort: medium.

---

### STR-004: `perform_download` exceeds function length and has multiple return points

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `perform_download` function at line 976 is 87 lines long (exceeds 50 line limit) with cyclomatic complexity of 12 (rank C) and ~4 return points. Each match case branch has its own nested cookie handling logic, creating code duplication and cognitive overhead.

**Evidence:** `radon cc src/ -s` shows CC=12 (rank C). Function spans lines 976-1063. The YTDLP and FFMPEG case branches both duplicate the `if settings.cookie_source == CookieSource.BROWSER` check with identical nested logic.

**Recommendation:** Extract cookie acquisition logic into a helper method `_get_cookies_for_url(url)`. Reduce function length by extracting the method dispatch into smaller functions. Consider using a strategy pattern with separate handlers per DownloadMethod. Effort: small.

---

### STR-005: `downloader.py` is a god module exceeding 300 lines

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `downloader.py` source file is 1063 lines long, far exceeding the 300 line threshold for a "god module". This file contains multiple concerns: HLS downloading, ffmpeg progress parsing, segment merging, yt-dlp integration, and signal handling.

**Evidence:** `radon raw src/` shows LOC: 1063 for this file. Contains 4 high-complexity functions and implements 3+ distinct features in one file.

**Recommendation:** Split into separate modules: (1) `ffmpeg_progress.py` for progress parsing, (2) `segment_merger.py` for segment merging logic, (3) `ytdlp_downloader.py` for yt-dlp integration, (4) `signal_handlers.py` for shutdown handling. Effort: large (but should be done incrementally).

---

### STR-006: Average cyclomatic complexity exceeds threshold

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/ |
| **Classification** | advisory |

**Description:** The average cyclomatic complexity across the project is 14.5 (rank C), exceeding the recommended threshold of ≤5. This indicates systemic complexity issues across the codebase, not just isolated functions.

**Evidence:** `radon cc src/ -a -nc` output: `Average complexity: C (14.5)`. Four functions have rank C or worse contributing to this high average.

**Recommendation:** Prioritize refactoring the highest complexity functions first (read_progress with CC=21, download_hls_with_resume with CC=13). Establish CI linting with `radon cc` to prevent complexity creep. Effort: ongoing.

---

### STR-007: BOM character in `__init__.py` causes parsing error

| Field | Value |
|-------|-------|
| **ID** | STR-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/__init__.py |
| **Classification** | advisory |

**Description:** The `src/vkdownloader/__init__.py` file contains a BOM (U+FEFF) character at line 1, causing `radon` to fail with an error. This is a hidden character that can cause issues with tooling.

**Evidence:** `radon cc src/ -a -nc` output: `ERROR: invalid non-printable character U+FEFF (<unknown>, line 1)`. File inspection confirms BOM presence.

**Recommendation:** Remove the BOM character from `__init__.py`. Ensure files are saved with UTF-8 without BOM encoding. Effort: trivial.

---

### STR-008: `_parse_retry_after` uses nested try/except for pattern matching

| Field | Value |
|-------|-------|
| **ID** | STR-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader_throttle.py |
| **Classification** | advisory |

**Description:** The `_parse_retry_after` function uses nested try/except blocks (lines 141-144 and 147-156) to handle two different parsing formats. While the complexity is acceptable at rank A (5), the nested exception handling could be flattened.

**Evidence:** Lines 141-144 (try/except for float parsing) and 147-156 (try/except for datetime parsing) are sequential, not nested. However, the function returns `None` in multiple places and has a cognitive load from dual parsing strategies.

**Recommendation:** Extract each parsing strategy into separate helper functions or use early returns with guard clauses to reduce mental overhead. Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

None - all findings are advisory quality improvements.

## Advisory Recommendations

- STR-001: Refactor `read_progress` to use dispatch table instead of if/elif chain
- STR-002: Extract `download_segment_concurrent` and split segment download logic
- STR-003: Extract retry loop and segment resume logic from fallback function
- STR-004: Extract cookie acquisition logic; reduce method duplication
- STR-005: Split `downloader.py` into smaller, focused modules
- STR-006: Target high-CC functions for incremental refactoring
- STR-007: Remove BOM character from `__init__.py` for tooling compatibility
- STR-008: Consider flattening `_parse_retry_after` exception handling

## Doc Updates Needed

None

---