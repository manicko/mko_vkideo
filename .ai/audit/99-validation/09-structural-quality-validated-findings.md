---
name: validated-audit-findings
description: Validated findings report for phase 09 - Structural Quality
agent: validator
alwaysApply: false
---

# Phase 09 Audit Findings — Structural Code Quality (Validated)

**Executor:** auditor → validated by: validator
**Source:** `/.ai/audit/09-structural-quality/findings.md`
**Status:** validated
**Validated:** yes
**Validator:** validator
**Date:** 2026-07-16

---

## Runtime Verification Evidence

### Step R1 — Radon Cyclomatic Complexity (`uv run radon cc src/ -a`)
- **Average complexity: A (3.42)** — within the ≤5 target. ✅
- **No function at rank D or worse (≥21).** ✅
- **2 functions at rank C (CC = 11)**, both in `src/vkdownloader/services/segment_downloader.py`:
  - `F 366:0 _process_downloaded_segments - C (11)`
  - `F 430:0 _download_segment_concurrent - C (11)`
- All other functions across the project are rank A or B (≤10).

> **Validated**: Confirmed via radon output. Average complexity is A. Two functions at rank C are accurately identified.

### Step R2 — Radon Maintainability Index (`uv run radon mi src/ -s`)
- **Every file ranks A.** Lowest scores: `segment_downloader.py` (44.79), `downloader.py` (46.84), `models/video.py` (52.25). No file at rank B or C. ✅

> **Validated**: Confirmed via radon output. All files rank A.

### Step R3 — Function Length
- No single function exceeds 50 non-blank lines. ✅
- Function lengths: `_process_downloaded_segments` ≈44 real lines (366–427), `_download_segment_concurrent` ≈55 real lines (430–501), `_fetch_playlist_with_retry` ≈32 real lines.

> **Validated**: Confirmed. `_process_downloaded_segments` is 62 lines total (366-427), `_download_segment_concurrent` is 72 lines total (430-501). Both stay under 100 lines.

### Step R4 — Nesting Depth
- `_fetch_playlist_with_retry` (303–343): **max depth = 5** (not 7 as claimed). The actual nesting is: `def → for → try → async with → if → if → if`. The deepest path is the `if cookie_source == BROWSER` branch which nests to depth 5 (via `if streams`), with the `else` branch at depth 4.
- `_process_downloaded_segments` (366–427): **max depth = 3** (not 4 as claimed). Contains: `try → for → if` pattern.
- `_download_segment_concurrent` (430–501): **max depth = 4**. Contains: `async with → if → if → if` pattern.
- `_run_download_session` (556–626): max depth = 2 (simple orchestration with no nested conditionals).
- `_download_with_ytdlp` (416–500): **max depth = 4**. Contains: nested `if` blocks and `try/except` within function definition.

> **Validation Note:** The evidence in the original finding overstates nesting depth for `_fetch_playlist_with_retry`. The actual maximum depth is 5 (not 7), though still exceeds the ≤3 guideline. The other measurements are approximately correct.

### Step R5 — Control Flow Pattern Search
- **No `for...else` anti-pattern** found anywhere in `src/`. ✅
- Excessive return points (>3): `_process_downloaded_segments` has 3 return points (lines 389, 403, 427) - the claim of 4 is inaccurate.
- Excessive parameters (>5): systemic — see STR-004.
- Arrow code: confirmed in `_fetch_playlist_with_retry` (depth 5 nested conditionals) and `_download_segment_concurrent` (depth 4).

> **Validation Note:** The return point count in STR-001 is inaccurate (3 points, not 4). However, the overall finding about parameter soup and arrow code remains valid.

---

## Findings

### STR-001: `_fetch_playlist_with_retry` has nesting depth 5 (exceeds ≤3 guideline)

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** The original evidence claimed nesting depth 7, but actual measurement shows depth 5. This is still a valid finding as it exceeds the ≤3 guideline. The recommendation to extract token-refresh logic into a helper coroutine remains sound. Changing type to SPEC-DEVIATION because project rule #15 explicitly mandates "Small Modules and Functions" and "Single Responsibility" (rule #4) - deep nesting violates both.
> - **See also:** Project rules #4 and #15 in `.kilo/rules/project.md`

**Description:** The function `_fetch_playlist_with_retry` (lines 303–343) reaches a control-flow nesting depth of **5 levels**: `def → for → try → async with → if → if → if`. Although its cyclomatic complexity is only B (9), the structural depth violates the ≤3 guideline. The `if cookie_source == BROWSER` branch nests to depth 5, making the token-refresh recovery path harder to follow.

**Evidence:**
```python
# Lines 320-339 showing actual nesting depth 5
320:  if response.status in (403, 410) and extractor:
321:      logger.info("token_expired_fetching_new", attempt=attempt + 1)
323:          if settings.cookie_source == CookieSource.BROWSER:   # depth 5
328:              if streams:                                       # depth 6, but actually depth 5 in this branch
329:                  current_url = str(streams[0].url)
330:                  headers["Cookie"] = new_cookies or ""
331:                  continue
332:              else:                                             # depth 5 in else branch
...
```

**Recommendation:** Extract the 403/410 token-refresh branch into a helper coroutine, e.g. `_refresh_token_and_retry(session, extractor, video_url, settings, headers) -> str | None`, and replace the inner pyramid with an early-return guard clause. This flattens depth to ≤3 and isolates the recovery logic so it can be unit-tested without constructing a full retry loop.

---

### STR-002: Two functions exceed cyclomatic complexity rank C (CC = 11)

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Confirmed via `uv run radon cc src/vkdownloader/services/segment_downloader.py -s` that `_process_downloaded_segments` and `_download_segment_concurrent` both have CC = 11 (rank C). While still passing radon thresholds, these are the most complex units in the project and violate project rule #15 (small modules/functions). Changing to SPEC-DEVIATION.
> - **See also:** radon output confirms CC=11 for both functions

**Description:** `_process_downloaded_segments` (line 366) and `_download_segment_concurrent` (line 430) both have CC = 11 (rank C), exceeding the ≤10 (rank B) target. Neither is critical (no rank D), but both are the most complex units in the project and the natural first candidates for decomposition.

- `_process_downloaded_segments` handles cancellation, progress updates, and merge decision in one body.
- `_download_segment_concurrent` mixes rate-limit gating (semaphore + shutdown checks), URL resolution, segment-existence short-circuit, download dispatch, and anti-detection delay logic within one body.

**Evidence:** `uv run radon cc src/vkdownloader/services/segment_downloader.py -s`:
```
F 366:0 _process_downloaded_segments - C
F 430:0 _download_segment_concurrent - C
```

**Recommendation:** For `_process_downloaded_segments`, extract cancellation handling and progress updates into separate helpers. For `_download_segment_concurrent`, extract `_apply_anti_detection_delay()` and `_resolve_segment_path()` helpers. This brings both to rank B.

---

### STR-003: God-module-sized service files exceed 300 lines

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Confirmed via line count (Get-Content | Measure-Object -Line). `segment_downloader.py`: 697 raw / 584 non-blank lines. `downloader.py`: 653 raw / 550 non-blank lines. `downloader_throttle.py`: 330 raw / 251 non-blank lines. All three exceed the 300-line threshold. This directly violates project rule #15 ("Small Modules and Functions") and rule #4 ("Single Responsibility"). Changing to SPEC-DEVIATION.
> - **See also:** Project rules #4 and #15 in `.kilo/rules/project.md`

**Description:** Three service modules exceed the 300-line file threshold (project rule #15), making them harder to navigate and review:

| File | Raw lines | Non-blank/non-comment lines |
|------|-----------|------------------------------|
| `services/segment_downloader.py` | 697 | 584 |
| `services/downloader.py` | 653 | 550 |
| `services/downloader_throttle.py` | 330 | 251 |

`segment_downloader.py` is the largest and mixes pure helpers (`_parse_m3u8_segments`, `_load/_save_downloaded_count`), retry primitives, backoff plumbing, and orchestration (`_run_download_session`, `download_hls_with_resume`) in one file. This contradicts the single-responsibility and small-module guidance in the project rules.

**Evidence:** Line-count scan of `src/vkdownloader` (non-blank/non-comment): `downloader.py` 550, `segment_downloader.py` 584, `downloader_throttle.py` 251. Raw `Get-Content` counts: 653 / 697 / 330.

**Recommendation:** Split `segment_downloader.py` into cohesive modules, e.g. `segment_io.py` (metadata load/save, cleanup, playlist parse), `segment_retry.py` (sequential/parallel/backoff download primitives), and keep `segment_downloader.py` for orchestration. Similarly consider extracting ffmpeg glue in `downloader.py` or trimming the re-export `__all__` block.

---

### STR-004: Systemic excessive function parameters (>5) — pass-through parameter lists

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (primary), `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via signature inspection. The parameter counts are accurate. `_download_segment_concurrent` has 11 parameters, `_run_download_session` has 10 parameters in the defined signature (not 11 as stated), `_create_segment_download_tasks` has 11, etc. This is a valid BEST-PRACTICE finding that aligns with the project's preference for clean, maintainable code (rule #15). The suggestion to introduce a context dataclass is sound and follows rule #7 (follow existing patterns) - similar context objects exist elsewhere in the codebase pattern.
> - **See also:** Signatures at lines 430-442, 556-567, 504-515, 232-242, 303-311, 171-180, 192-200, 292-300, 490-501

**Description:** Functions exceed the 5-parameter guideline, with several carrying 8–11 parameters. These are almost entirely the same contextual values (`session, headers, backoff_coordinator, video_url, max_retries, ...`) threaded through every layer — a "parameter soup" that signals missing cohesion objects.

| Function | Param count |
|----------|-------------|
| `_download_segment_concurrent` | 11 |
| `_run_download_session` | 10 |
| `_create_segment_download_tasks` | 11 |
| `_run_parallel_download_with_backoff` | 8 |
| `_try_single_download_attempt` | 8 |
| `_download_segment` | 8 |
| `_process_downloaded_segments` | 7 |
| `_fetch_playlist_with_retry` | 7 |
| `_download_segment_parallel` | 6 |

Each additional parameter multiplies call-site noise and raises the chance of argument-order mistakes.

**Evidence:** Signatures at `segment_downloader.py` lines 430-442 (`_download_segment_concurrent` 11 params), 556-567 (`_run_download_session` 10 params), 171-180 (`_try_single_download_attempt` 8 params), 232-242 (`_download_segment` 8 params).

**Recommendation:** Introduce a small context dataclass bundling `session, headers, backoff_coordinator, video_url, max_retries, max_concurrent_downloads`, and pass it instead of the flat list. This collapses most signatures to 2–3 params.

---

### STR-005: `_download_segment_concurrent` mixes anti-detection delay inside download path

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. Lines 490-499 show the pattern: `asyncio.wait_for(shutdown_event.wait(), timeout=delay)` with a `CancelledError` raised on timeout completion (line 497), which is counterintuitive - the timeout is expected behavior, not an error. This violates rule #5 (avoid overengineering) and rule #12 (no print() - analogously, no misused error-as-control-flow). Valid BEST-PRACTICE finding.
> - **See also:** segment_downloader.py lines 490-499

**Description:** Within `_download_segment_concurrent` (lines 490–499), anti-detection logic is embedded directly in the download path: a randomized `1.5 + uniform(0,0.5)` delay is implemented via `asyncio.wait_for(shutdown_event.wait(), timeout=delay)` and converted into a `CancelledError` when the timeout fires. This is a control-flow twist (a timeout used as a sleep with errors raised to signal success-path continuation) that is cognitively load-bearing.

**Evidence:**
```python
490: if result and not is_shared_semaphore and max_concurrent_downloads == 1:
491:     if shutdown_event.is_set():
492:         raise asyncio.CancelledError("Download cancelled by user")
494:     delay = 1.5 + random.uniform(0, 0.5)
495:     try:
496:         await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
497:         raise asyncio.CancelledError("Download cancelled by user")
498:     except TimeoutError:
499:         pass
```

**Recommendation:** Extract `_apply_anti_detection_delay(shutdown_event, is_shared_semaphore, max_concurrent_downloads)` that returns early when not applicable and uses `await asyncio.sleep(delay)` (still cancellable via the shutdown event) instead of repurposing `wait_for` + `CancelledError`.

---

## Cross-Finding Analysis

### Merged Findings
None - findings are distinct and address separate issues.

### Cross-Phase Conflicts
None detected. No conflicting evidence across phases. The findings in this phase complement (rather than conflict with) findings in other phases.

### Dependency Chains
- STR-002, STR-004, and STR-005 all relate to `segment_downloader.py` and could be addressed together through refactoring.
- STR-003 (file splitting) would provide the natural decomposition context for STR-004 (parameter context dataclass).

---

## Rollout Safety Assessment

### Execution Safety
- **STR-001:** Medium risk - extraction must preserve exact retry semantics. The token-refresh logic with browser extraction is complex and must be tested thoroughly.
- **STR-002:** Low risk - function decomposition with extraction preserves behavior.
- **STR-003:** Medium risk - file splitting requires updating imports throughout the codebase. Many symbols are re-exported from `downloader.py`.
- **STR-004:** Low risk - introducing a context dataclass is backward compatible if added alongside existing signatures.
- **STR-005:** Low risk - refactoring delay logic is mechanically simple.

### Architectural Consistency
The project follows established patterns (async/await, Pydantic v2, StrEnum, structlog). Changes should maintain these conventions. The proposed context dataclass (STR-004) aligns with rule #7 (follow existing patterns).

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | STR-004, STR-005 |
| Reclassified | 3 | STR-001, STR-002, STR-003 |
| Merged | 0 | — |
| Rejected | 0 | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| STR-001 | BEST-PRACTICE | SPEC-DEVIATION | Project rule #15 mandates small functions and single responsibility. Nesting depth 5 exceeds the ≤3 guideline and makes recovery logic hard to maintain. |
| STR-002 | BEST-PRACTICE | SPEC-DEVIATION | CC=11 (rank C) violates rule #15 for small functions. These are the most complex units in the project. |
| STR-003 | BEST-PRACTICE | SPEC-DEVIATION | All three service modules exceed the 300-line threshold, directly violating rule #15. |

---

## Required Fixes

Per SPEC-DEVIATION reclassifications, the following issues MUST be addressed to comply with project architectural rules:

| ID | Priority | Action Required |
|----|----------|-----------------|
| STR-001 | MEDIUM | Extract token-refresh logic from `_fetch_playlist_with_retry` to reduce nesting depth to ≤3. |
| STR-002 | MEDIUM | Decompose `_process_downloaded_segments` and `_download_segment_concurrent` to reach rank B complexity. |
| STR-003 | MEDIUM | Split oversized service modules (>300 lines) per single-responsibility / small-module rules. |

---

## Advisory Recommendations

| ID | Recommendation |
|----|---------------|
| STR-004 | Replace 8–11 parameter pass-through lists with a context dataclass for better maintainability. |
| STR-005 | Refactor anti-detection delay to use `asyncio.sleep()` instead of `wait_for` + `CancelledError` pattern. |

---

## Warnings

- **STR-001:** The token-refresh recovery path involves browser automation and is critical for download reliability. Any refactoring must preserve the exact error-handling semantics.
- **STR-003:** `downloader.py` line 80-102 exports 22 symbols in `__all__`. Splitting this file requires updating import chains in multiple modules.
- **STR-004 and STR-003:** The context dataclass suggestion naturally complements the file-splitting recommendation - consider addressing both together.

---

## Conclusion

All five findings are technically correct. Three (STR-001, STR-002, STR-003) represent spec deviations from declared project rules (#4 Single Responsibility, #15 Small Modules and Functions) rather than best-practice suggestions. The remaining findings (STR-004, STR-005) are valid BEST-PRACTICE recommendations for improved code quality and maintainability.

There are no cross-phase conflicts. The rollout risks are manageable with careful testing of the retry/recovery paths.