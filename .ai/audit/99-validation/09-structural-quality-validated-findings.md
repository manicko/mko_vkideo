# Phase 09 Audit Findings — Structural Code Quality (Validated)

**Executor:** auditor  
**Validator:** validator  
**Source:** `.ai/audit/09-structural-quality/findings.md`  
**Status:** complete  
**Validated:** yes

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 | `uv run radon cc src/vkdownloader/ -a -nc` | Confirmed: 4 functions at CC rank C (average 11.5) |
| R2 | `uv run ruff check src/vkdownloader/ && uv run mypy src/vkdownloader/` | All checks passed; no lint/type issues |
| R3 | `uv run pytest tests/ -q` | 223 passed in 10.75s — tests pass but do not cover structural modifications |

---

## Findings

### STR-001: `HLSDownloader.download_with_ffmpeg` exceeds max nesting depth (6) and length (135 lines)

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (lines 168-302) |
| **Classification** | advisory |

**Description:** `download_with_ffmpeg` is 135 lines long with maximum nesting depth of **6** (exceeds 3-level guideline). Two branches at lines 260-270 and 274-284 contain near-identical `asyncio.wait([...])` + "cancel pending tasks" loops.

**Evidence:**
- AST scan: `downloader.py:168 download_with_ffmpeg | lines=135 | nesting=6 | params=6` (note: original finding claimed depth 5, actual depth is 6)
- Duplicated block: Lines 260-270 (progress_callback branch) and 274-284 (else branch) both contain identical task cancellation logic.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Evidence verified. The function is 135 lines (over 50-line guideline), has nesting depth 6 (exceeds 3), and contains duplicated cancellation logic. The recommendation to extract the shared pattern into `_await_first_and_cancel_others()` is sound and would collapse nesting by ~1 level.

**Recommendation:** Extract the shared "launch two coroutines, await FIRST_COMPLETED, cancel the loser" pattern into a single helper. Effort: small.

---

### STR-002: ~~`cli.py` is a god module (398 lines) and duplicates single-download logic~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (468 lines total) |
| **Classification** | advisory |

> **Rejection reason:** The duplication claim is **overstated**. Code inspection reveals:
> - The nested `_download()` in the `download` command (lines 315-358) is **~44 lines**, not ~55 as claimed.
> - `_download_single` (lines 64-156) is **93 lines** but includes batch-oriented error handling (returns status tuples, catches `VideoNotFoundError`, etc.) that the command-specific `_download()` does not need.
> - The "8-step flow" (extract streams → select quality → resolve output path → validate → sanitize title → build filename → perform download) is indeed present in both, but this is **shared business logic**, not duplication that will drift. The core difference is that `_download_single` handles batch-aggregation semantics (tuple returns, exception classification) while `_download()` handles CLI-output semantics.
> - cli.py is 468 lines (exceeds 300), but splitting it would require artificial boundaries. The file follows the single-`app` module pattern common in Typer CLI applications.
> This finding falls under "low-value complexity" — the refactoring cost outweighs the maintenance benefit because the logic paths diverge in meaning and the functions have distinct return contracts.

---

### STR-003: ~~`_download_single` has excessive parameters (10) and length (93 lines)~~ [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 64–156) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. Function has 10 parameters (exceeds 5-param guideline) and is 93 lines with CC rank C. Several are batch-only concerns (`index`, `shared_semaphore`, `backoff_coordinator`, `progress_callback`) that could be bundled.

**Description:** `_download_single` takes 10 parameters — double the 5-parameter limit. Several are batch-only concerns (index, shared_semaphore, backoff_coordinator, progress_callback). The function is 93 lines with CC rank C (≥11).

**Evidence:**
- AST scan: `cli.py:64 _download_single | lines=93 | nesting=2 | params=10`
- radon cc: `_download_single - C` (complexity 13)

**Recommendation:** Introduce a `DownloadContext` dataclass bundling batch-scoped fields. Effort: small. Priority: recommended.

---

### STR-004: ~~`_download_segment_concurrent` has excessive parameters (13)~~ [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (lines 514–590) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. Function has 13 parameters (over 2.5× the 5-param limit) and `_create_segment_download_tasks` (lines 593-647) has 12 parameters, creating verbose call sites. The parameter list bundles HTTP plumbing, rate-limiting, and identity concerns.

**Description:** `_download_segment_concurrent` takes 13 parameters and is 77 lines (CC rank C). The caller `_create_segment_download_tasks` has 12 parameters.

**Evidence:**
- AST scan: `segment_downloader.py:514 _download_segment_concurrent | lines=77 | nesting=4 | params=13`
- AST scan: `segment_downloader.py:593 _create_segment_download_tasks | lines=55 | params=12`

**Recommendation:** Group params into cohesive objects (`SegmentTask`, `DownloadPolicy`). Effort: medium. Priority: recommended.

---

### STR-005: ~~Project average cyclomatic complexity is 11.5 (target ≤5)~~ [MERGED]

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | whole `src/vkdownloader/` (4 functions at CC rank C) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** merged
> - **Detail:** This is an aggregate metric derived from STR-001, STR-003, STR-004, and `_process_downloaded_segments`. The individual functions are already flagged; no separate action item needed.
> - **See also:** STR-001, STR-003, STR-004

**Recommendation:** Address via the individual function refactorings. The `_raise_if_shutdown` helper suggestion would be a cross-cutting improvement.

---

### STR-006: ~~`_download_with_ytdlp` exceeds 50-line limit (114 lines); `_process_downloaded_segments` (56) just over~~ [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (lines 478–591); `src/vkdownloader/services/segment_downloader.py` (lines 456–511) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. `_download_with_ytdlp` is 114 lines (7 params, nesting 3). `_process_downloaded_segments` is 56 lines (7 params, nesting 4). Both exceed the 50-line guideline.

**Description:** `_download_with_ytdlp` nests a large synchronous `_download()` closure containing the full yt-dlp option dict. `_process_downloaded_segments` combines "await + cancellation" handling with "tally + merge" step.

**Evidence:**
- AST: `_download_with_ytdlp | lines=114 | nesting=3 | params=7`
- AST: `_process_downloaded_segments | lines=56 | nesting=3 | params=7`

**Recommendation:** Extract yt-dlp opts dict builder; split `_process_downloaded_segments`. Effort: small. Priority: recommended.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | STR-001, STR-003, STR-004, STR-006 |
| Reclassified | 0 | — |
| Merged | 1 | STR-005 → aggregate of STR-001/003/004 |
| Rejected | 1 | STR-002 (overstated duplication claim) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| STR-002 | `cli.py` is a god module and duplicates single-download logic | Overstated duplication: `_download()` in command and `_download_single` serve different contracts (CLI output vs batch aggregation). The shared logic is business flow, not drift-prone duplication. Splitting would introduce artificial complexity. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| STR-005 | Consolidated into STR-001/STR-003/STR-004 | Aggregate complexity metric derived from already-flagged functions; no separate action needed. |

### Reclassified Findings

None.

---

## Cross-Phase Conflicts

None detected. The structural findings are internally consistent and do not contradict other phases.

---

## Rollout Safety Notes

| ID | Risk | Mitigation |
|----|------|------------|
| STR-001 | MEDIUM | Extracting helper from `download_with_ffmpeg` affects progress callback path; ensure tests cover both branches. |
| STR-003 | MEDIUM | Parameter bundling via dataclass should maintain backward-compatible call sites during transition. |
| STR-004 | MEDIUM | Parameter grouping affects `_create_segment_download_tasks` and `_download_segment_concurrent` call chain; refactor both together. |

---

## Dependency Chain

- STR-001 and STR-006 both affect `downloader.py` and can be addressed in the same PR.
- STR-003 and STR-004 can be addressed independently but both reduce parameter counts.
- STR-001's helper extraction could be shared with other async cancellation patterns (matches `_process_downloaded_segments` pattern in STR-006).