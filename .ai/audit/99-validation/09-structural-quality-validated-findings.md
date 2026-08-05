# Phase 09 Audit Findings — Structural Code Quality

**Executor:** audit-executor (auditor)
**Validator:** kilo/poolside/laguna-s-2.1:free (validator agent)
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes

---

## Methodology (Runtime Verification)

Runtime verification was executed against the project source tree (`src/`) and, where relevant, `tests/`. No Docker services exist in this repository (a `uv`-managed Python CLI tool with a `src/` layout; no `docker-compose*.y*`/`Dockerfile`), so the "Start services" step is N/A.

- **R1 — Cyclomatic Complexity:** `rradon cc src -s -a` → 131 blocks, average **A (3.78 ≤ 5 ✓)**; 7 functions rank C (CC 11–14); no function reached rank D/E/F (≥21).
- **R2 — Maintainability Index:** `rradon mi src -s` → all 19 files rank **A** (scores 42.17–100; A = score > 19). No rank B/C files.
- **R3 — Function length:** AST walk (non-blank/non-comment lines). 3 functions >100 lines; 11 functions in the 50–100 line band.
- **R4 — Nesting depth:** AST walk of `if/for/while/try/with`. 5 functions at depth 5; 3 at depth 4.
- **R5 — Control-flow patterns:** `for…else` — none. Functions with >3 returns — 9. Functions with >5 parameters (excl. `self`, M=method) — 18.

---

## Findings

### STR-001: God-module source files exceed the 300-line file threshold

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py, src/vkdownloader/services/downloader.py, src/vkdownloader/services/segment_downloader.py |
| **Classification** | advisory |

**Description:** Three production modules exceed 300 SLOC (blanks/comments excluded), bundling multiple responsibilities into single files. This expands blast radius, makes targeted review slow, and discourages clean separation of concerns.

**Evidence (rradon raw):**
| File | SLOC | LOC | LLOC |
|------|------|-----|------|
| cli.py | 403 | 608 | 258 |
| downloader.py | 560 | 853 | 296 |
| segment_downloader.py | 540 | 843 | 306 |

**Recommendation:** Split each god module by responsibility (e.g. `downloader.py` → ytdlp/ffmpeg/hls sub-modules behind a thin dispatcher; extract batch-progress CLI plumbing from `cli.py`; partition `segment_downloader.py` into playlist/segment/orchestration concerns). Effort: medium. Priority: recommended.

---

### STR-002: Three functions exceed 100 code lines

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** Functions this large resist isolated unit testing, hide multiple responsibilities, and frequently co-occur with high complexity and parameter counts (see STR-004/005/007).

**Evidence (AST, non-blank/non-comment lines):**
| Function | Location | Code lines | CC | Params | Nesting |
|----------|----------|-----------|----|--------|---------|
| perform_download | downloader.py:716 | 123 | C(12) | 11 | 2 |
| download | cli.py:385 | 107 | B(9) | 6 | 2 |
| HLSDownloader.download_with_ffmpeg | downloader.py:281 | 105 | C(11) | 5 | 5 |

**Recommendation:** Extract cohesive sub-behaviours into single-purpose helpers (dispatch each `match` branch of `perform_download` to a strategy function; hoist the nested `_monitor_progress`/`_drain_stderr` helpers to module-level, which also resolves STR-005; extract header/cookie assembly). Effort: medium. Priority: recommended.

---

### STR-003: Eleven functions in the 50–100 code-line range

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/{downloader,downloader_throttle,segment_downloader,network_monitor}.py, src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** Eleven functions exceed the 50-line single-responsibility guideline, indicating multi-step orchestration that is hard to follow top-to-bottom.

**Evidence (AST code-line counts):** `_build_ytdlp_options` downloader.py:129 (71); `_intercept_response` network_monitor.py:53 (59); `_attempt_segment_resume` downloader.py:494 (82); `_run_batch_with_progress` cli.py:247 (70); `_retry_429_with_backoff` downloader_throttle.py:145 (68); `_run_download_session` segment_downloader.py:690 (70); `download_with_ytdlp_with_resume_fallback` downloader.py:413 (66); `batch_download` cli.py:512 (82); `_download_single` cli.py:166 (65); `_download_with_ytdlp` downloader.py:586 (61); `download_hls_with_resume` segment_downloader.py:770 (55).

**Recommendation:** Apply Extract Method + early-return guard clauses to flatten exit paths and isolate testable units. Effort: medium. Priority: recommended.

---

### STR-004: Seven functions at cyclomatic complexity rank C (CC 11–14)

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py, infrastructure/network_monitor.py, services/downloader.py, services/ffmpeg_utils.py |
| **Classification** | advisory |

**Description:** Project average CC is healthy (A, 3.78), but seven functions exceed the CC ≤ 10 guideline (rank C). These demand N-branch test matrices and are prime locations for edge-case bugs.

**Evidence (rradon cc -s):** `perform_download` downloader.py:716 C(12); `_intercept_response` network_monitor.py:53 C(13); `_download_single` cli.py:166 C(14); `_print_batch_summary` cli.py:338 C(11); `_run_batch_with_progress` cli.py:247 C(11); `download_with_ffmpeg` downloader.py:281 C(11); `_merge_segments_batched` ffmpeg_utils.py:264 C(11). No function reached rank D/E/F (≥21).

**Recommendation:** Reduce branch count via guard clauses (flatten the nested `if/elif/raise` in `_intercept_response`), replace type-dispatch chains with strategy objects, and extract `try` bodies into named helpers. Effort: medium. Priority: recommended.

---

### STR-005: Five functions nest control flow to depth 5 (pyramid-of-doom)

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py, services/downloader.py, services/extractor.py, services/ffmpeg_utils.py |
| **Classification** | advisory |

**Description:** Depth-5 nesting (>4) is the "arrow code" anti-pattern: the happy path is buried under nested conditionals, harming readability and making exit/continue points hard to trace.

**Evidence (AST nesting depth):**
- `_run_batch_with_progress` cli.py:247 — nest=5 (try→for→try→for→if)
- `download_with_ffmpeg` downloader.py:281 — nest=5 (deep nesting inside the nested `_monitor_progress`/`_drain_stderr` helpers defined within it)
- `_extract_with_ytdlp` extractor.py:143 — nest=5 (contains the nested helper `_sync_extract` below)
- `_sync_extract` extractor.py:152 — nest=5 (with→try→for→if→if); defined inside `_extract_with_ytdlp`
- `read_progress` ffmpeg_utils.py:94 — nest=5 (while→if parsed→if handler→elif→if value=="end")

**Recommendation:** Flatten with guard clauses/early returns and promote the nested helpers (`_monitor_progress`, `_drain_stderr`, `_sync_extract`) to module-level private functions — this also lowers the enclosing functions' nesting. Effort: small/medium. Priority: recommended.

---

### STR-006: Three functions at nesting depth 4

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/infrastructure/network_monitor.py, services/downloader_throttle.py |
| **Classification** | advisory |

**Description:** Exceeds the ≤3 nesting guideline.

**Evidence (AST):** `_intercept_response` network_monitor.py:53 nest=4; `_extract_urls_from_json` network_monitor.py:123 nest=4; `_retry_429_with_backoff` downloader_throttle.py:145 nest=4 (for→try→async-with→if).

**Recommendation:** Extract the innermost conditional blocks into small predicate/helper functions and use early returns to reduce indentation. Effort: small. Priority: recommended.

---

### STR-007: Parameter bloat — functions exceed 5 parameters (excl. self)

> **Validation Note:**
> - **Action:** corrected
> - **Detail:** Core claim is valid — parameter bloat is widespread in the download-orchestration layer. However, the auditor's count of 18 is inaccurate. Re-analysis with keyword-only arguments included (AST: posonlyargs + args + kwonlyargs + vararg + kwarg, self/cls excluded for methods) yields **20** functions exceeding 5 params, not 18. Two functions were omitted from the auditor's list: _tally_and_merge (segment_downloader.py:517, 6 params) and _process_downloaded_segments (segment_downloader.py:564, 6 params). Additionally, 8 of the 18 listed entries were misclassified as methods (M) when they are module-level free functions — subtracting 1 for a non-existent self — making their reported param counts 1 lower than actual. All 20 functions still exceed the 5-parameter threshold, so the recommendation stands.
> - **See also:** STR-001 (god-module files are the locus of this bloat); CLI-002 (Phase 01 addresses cli.py separation of concerns)

| Field | Value |
|-------|-------|
| **ID** | STR-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py, segment_downloader.py, downloader_throttle.py, cli.py |
| **Classification** | advisory |

**Description:** High parameter counts signal that functions do too much and are painful to construct in tests. The download-orchestration layer is the most affected cluster.

**Evidence (AST, real param count; `self` excluded for methods, M=method):** `perform_download` 11 (downloader.py:716); `download_with_ytdlp_with_resume_fallback` 11 (downloader.py:413); `_attempt_segment_resume` 10 (downloader.py:494); `_build_ytdlp_options` 9 (downloader.py:129); `_run_download_session` 9 (segment_downloader.py:690, M); `_download_segment` 9 (segment_downloader.py:306, M); `_run_parallel_download_with_backoff` 8 (segment_downloader.py:143, M); `_do_parallel_download_attempt` 8 (segment_downloader.py:190, M); `_try_single_download_attempt` 8 (segment_downloader.py:219, M); `_download_segment_parallel` 7 (segment_downloader.py:252, M); `_download_with_ytdlp` 7 (downloader.py:586); `_download_single` 7 (cli.py:166); `batch_download` 7 (cli.py:512); `_download_segment_sequential` 6 (segment_downloader.py:81, M); `_fetch_playlist_with_retry` 6 (segment_downloader.py:433, M); `_run_batch_with_progress` 6 (cli.py:247); `download` 6 (cli.py:385); `_retry_429_with_backoff` 6 (downloader_throttle.py:145).

**Recommendation:** Group related parameters into a configuration dataclass/Pydantic model (e.g. a `DownloadOptions` DTO) and pass that instead; this cuts call-site noise and improves test ergonomics. Effort: medium. Priority: recommended.

---

### STR-008: Nine functions have more than 3 return points

| Field | Value |
|-------|-------|
| **ID** | STR-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py, services/downloader.py, services/downloader_throttle.py, services/segment_downloader.py, infrastructure/network_monitor.py |
| **Classification** | advisory |

**Description:** Multiple returns make control-flow reasoning and branch coverage harder; several are type-dispatch chains better expressed as lookup tables. (No `for…else` usage was found — that specific anti-pattern is absent.)

**Evidence (AST return count):** `_retry_429_with_backoff` downloader_throttle.py:145 — 6 returns; `_map_exception_to_status` cli.py:145 — 5 returns (if/elif exception→status dispatch, CC=6); `perform_download` downloader.py:716 — 5 returns (match-case); `_download_segment_parallel` segment_downloader.py:252 — 5; `_download_single` cli.py:166 — 4; `download_with_ytdlp_with_resume_fallback` downloader.py:413 — 4 (11 params); `_parse_retry_after` downloader_throttle.py:226 — 4; `_fetch_playlist_with_retry` segment_downloader.py:433 — 4; `_normalize_url` network_monitor.py:41 — 4.

**Recommendation:** Replace the `_map_exception_to_status` if/elif chain with a dispatch dict keyed by exception class; collapse multiple early returns in leaf functions (`_parse_retry_after`, `_normalize_url`) into a single result variable where it improves clarity. Effort: small. Priority: recommended.

---

### STR-009: God-module test suites exceed the 300-line file threshold

| Field | Value |
|-------|-------|
| **ID** | STR-009 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_hls_downloader.py, tests/test_downloader_throttle.py, tests/test_cli.py, tests/test_ffmpeg_utils.py |
| **Classification** | advisory |

**Description:** Four test suites far exceed the 300-line guideline, making them slow to navigate, hard to extend, and expensive to load in isolation. Test maintainability degrades in lock-step with production complexity (cf. STR-001).

**Evidence (rradon raw):** `test_hls_downloader.py` SLOC=1535 (LOC=2101); `test_downloader_throttle.py` SLOC=487 (LOC=683); `test_cli.py` SLOC=472 (LOC=622); `test_ffmpeg_utils.py` SLOC=319 (LOC=505). Also: `tests/test_extractor.py:128 TestExtractionErrors.test_format_cookies_for_ffmpeg` CC=15 (rank C).

**Recommendation:** Partition test suites by behaviour/fixture (e.g. retry vs throttling vs error-path cases) and parametrize the CC=15 test. Effort: medium. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 6 |
| LOW | 1 |

## Mandatory Fixes

(None — all findings are advisory structural-quality issues; no security, data-loss, or correctness defects were found in this dimension.)

## Advisory Recommendations

- STR-001: split the three god-module source files (cli.py, downloader.py, segment_downloader.py) by responsibility.
- STR-002 / STR-003: extract methods and apply guard clauses to bring functions under 50 lines.
- STR-004 / STR-005 / STR-006: reduce cyclomatic complexity and nesting via guard clauses, strategy objects, and module-level helpers.
- STR-007: consolidate oversized parameter lists behind a DTO/dataclass.
- STR-008: replace dispatch-style return chains with lookup tables.
- STR-009: split the oversized test suites.

## Doc Updates Needed

(None — no doc/spec deviation identified in this phase.)

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 8 | STR-001, STR-002, STR-003, STR-004, STR-005, STR-006, STR-008, STR-009 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Corrected (evidence) | 1 | STR-007 (count 18→20; 8 miscategorized entries) |
| Rejected | 0 | — |

### Rejected Findings

(none)

### Merged Findings

(none)

### Corrected Findings

| ID | Original Count | Corrected Count | Rationale |
|----|---------------|-----------------|-----------|
| STR-007 | 18 functions | 20 functions | 2 omitted (_tally_and_merge, _process_downloaded_segments); 8 entries miscategorized as methods |

---

## Cross-Finding Analysis

**Same root cause / symptom cluster:**
- STR-001 (god-module source files) is the **root cause**. STR-002, STR-003, STR-004, STR-005, STR-006, STR-007, and STR-008 are **symptoms** — they flag oversized functions, high CC, deep nesting, and parameter bloat that all live within the three god-module files (cli.py, downloader.py, segment_downloader.py). Splitting files (STR-001) naturally resolves most downstream findings by isolating responsibilities.

**Conceptual overlap with other phases (not merged — different dimensions):**
- STR-001 / STR-002 (cli.py size) ↔ CLI-002 (Phase 01: _download() nested inside download()) — same file, different concern (line count vs. nested-function anti-pattern).
- STR-002 (perform_download) ↔ QLT-002 (Phase 08: FFMPEG progress_callback mismatch) — QLT-002 targets the FFMPEG branch of perform_download for a type-compatibility fix; STR-002 targets function length. Distinct root causes.
- STR-002 / STR-007 (perform_download, _run_batch_with_progress) ↔ INT-006 (Phase 05: semaphore acquisition) — INT-006 is a concurrency bug fix; STR findings are code-quality metrics. No conflict.

**Cross-phase conflicts:** None detected. No phase makes a claim that contradicts another phase's verified evidence.

---

## Rollout Analysis

| Finding | Type | Rollout Risk | Dependencies |
|---------|------|-------------|--------------|
| STR-001 | BEST-PRACTICE | Low — pure refactor, no behavior change | Resolving STR-001 naturally addresses STR-002/003/004/005/007/008 |
| STR-002 | BEST-PRACTICE | Low — extract methods, no API change | STR-001 (file split) or standalone |
| STR-003 | BEST-PRACTICE | Low — extract methods + guard clauses | STR-001 (file split) or standalone |
| STR-004 | BEST-PRACTICE | Low — flatten branches, no API change | STR-001/002 (refactor together) |
| STR-005 | BEST-PRACTICE | Low — promote nested helpers, no behavior change | STR-001 (file split) or standalone |
| STR-006 | BEST-PRACTICE | Low — extract predicates, no API change | STR-001 (file split) or standalone |
| STR-007 | BEST-PRACTICE | Medium — introducing a DTO changes call signatures across perform_download, download_with_ytdlp_with_resume_fallback, and CLI callers | STR-001 (group functions before DTO refactor) |
| STR-008 | BEST-PRACTICE | Low — dispatch dict / result variable, no API change | STR-001 (file split) or standalone |
| STR-009 | BEST-PRACTICE | Low — test suite partitioning, no production change | STR-001 (parallel effort) |

**Circular dependencies:** None.
**Hidden dependencies:** STR-007 (DTO introduction) changes internal call signatures within downloader.py and segment_downloader.py. Care must be taken that internal callers are updated in the same rollout to avoid TypeError from mismatched signatures. This is internal (not a public API), so blast radius is limited to the vkdownloader package.
**Unsafe rollout ordering:** Splitting god-module files (STR-001) before introducing a DTO (STR-007) reduces the diff size and review burden per commit. STR-008 (dispatch-dict for _map_exception_to_status) is independent and can be done first.

---

## Execution Validation

**Applicability:** All 9 findings remain applicable. The codebase state matches the auditor's evidence (verified via 
radon cc, 
radon raw, 
radon mi, and AST analysis on 2026-08-05). No finding has been partially or fully implemented since audit execution.

**Execution readiness:**
- STR-001/002/003/004/005/006/008/009 — ready to execute. Pure refactors with no external API impact. Existing tests (248 passing) provide regression coverage.
- STR-007 — ready to execute but with medium effort. Introducing a DownloadOptions DTO changes internal signatures; update all internal call sites in the same PR.

---

## Warnings

- **STR-007 evidence discrepancy:** The auditor reported 18 functions with >5 params; actual count is 20 (2 omitted + 8 miscategorized as methods vs. free functions). The finding's direction is correct but the specific count and 8 param values are off by ±1. Type remains BEST-PRACTICE.
- **STR-002 line-count discrepancy:** download (cli.py:385) reported as 107 code lines; actual is 106. The 1-line difference does not change the finding (still >100). Likely a different blank/comment exclusion heuristic.
- **STR-003 line-count discrepancy:** batch_download (cli.py:512) reported as 82 code lines; actual is 81. Does not change the finding (still in 50–100 band).
- **STR-005 methodology note:** The auditor's nesting-depth measurement for _extract_with_ytdlp (extractor.py:143) and download_with_ffmpeg (downloader.py:281) includes nesting depth *within nested helper functions* defined inside the parent. A stricter interpretation (measuring only the parent's own control flow, excluding nested function bodies) would yield lower depths. However, the code **is** deeply nested in practice (nested helpers inside deeply nested control flow), so the finding's practical value holds. The recommendation to promote nested helpers to module-level is valid regardless.
- **No mandatory fixes:** All findings are advisory BEST-PRACTICE. No SPEC-DEVIATION or security/correctness findings in this phase.

---

## Required Fixes

(none — no mandatory or spec-deviation findings in this phase)

---

## Advisory Recommendations

- **STR-001:** Split cli.py, downloader.py, and segment_downloader.py by responsibility. This is the highest-leverage action — it naturally reduces function length (STR-002/003), complexity (STR-004), nesting (STR-005/006), and parameter count (STR-007) in one pass.
- **STR-007 (corrected):** Group related parameters into a DownloadOptions DTO/Pydantic model. Apply after the file split from STR-001 to minimize the diff.
- **STR-008:** Replace _map_exception_to_status if/elif chain (cli.py:145) with a dispatch dict; collapse early returns in _parse_retry_after and _normalize_url into single result variables.
- **STR-009:** Partition test_hls_downloader.py (1535 SLOC), test_downloader_throttle.py (487 SLOC), test_cli.py (472 SLOC), and test_ffmpeg_utils.py (319 SLOC) by behaviour/fixture.
