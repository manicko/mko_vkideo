---
name: 09-structural-quality-validated
description: Validated Phase 09 audit findings for structural code quality
agent: validator
validated: yes
---

# Phase 09 Audit Findings — Structural Code Quality (Validated)

**Executor:** auditor
**Validator:** validator
**Status:** complete
**Validated:** yes

---

## Runtime Verification Evidence

### R1 — Radon Cyclomatic Complexity (`uv run radon cc src/ -s -a`)

Functions at rank **C or worse (CC ≥ 11)** (VERIFIED):

| Function | Location | CC | Rank |
|----------|----------|----|------|
| `read_progress` | `services/ffmpeg_utils.py:51` | 21 | **D** |
| `download_hls_with_resume` | `services/segment_downloader.py:172` | 19 | C |
| `batch_download` | `cli.py:179` | 14 | C |
| `perform_download` | `services/downloader.py:460` | 14 | C |
| `download_with_ytdlp_with_resume_fallback` | `services/downloader.py:243` | 12 | C |
| `_download_segment` | `services/segment_downloader.py:42` | 12 | C |

Average complexity across project: **A (3.43)** — passes the ≤5 target.

### R2 — Radon Maintainability Index (`uv run radon mi src/ -s`)

All files scored rank **A**. No MI-rank B/C files. (VERIFIED — issues are localized to specific functions, not whole-file rot.)

### R3/R4 — Function length & nesting depth (VERIFIED)

| Function | SLOC (body) | Nesting depth | CC | Verified |
|----------|-------------|---------------|----|----------|
| `download_hls_with_resume` | ~164 lines | 7 | 19 | ✓ |
| `batch_download` | ~187 lines | 7 | 14 | ✓ |
| `download_with_ytdlp_with_resume_fallback` | ~93 lines | 7 | 12 | ✓ |
| `perform_download` | ~108 lines | 5 | 14 | ✓ |
| `_retry_429_with_backoff` | ~76 lines | 6 | 10 | ✓ |
| `read_progress` | ~46 lines | 4 | 21 | ✓ |
| `_download_segment` | ~55 lines | 4 | 12 | ✓ |

### R5 — Control flow patterns (VERIFIED)

- `for...else`: none found.
- Excessive parameters: `perform_download` declares **11 parameters** (signature at lines 460-472).
- File size: `services/downloader.py` SLOC = **409** (verified via `radon raw`).

---

## Findings

### STR-01: `read_progress` has cyclomatic complexity 21 (rank D) and an 11-branch if/elif chain

| Field | Value |
|-------|-------|
| **ID** | STR-01 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** `read_progress` (lines 51–97) is the only function in the project at Radon rank **D** (CC=21), which violates the "no CC rank D or worse (≥21)" threshold. Its complexity comes entirely from a flat 11-branch `if/elif` chain (lines 76–96) that maps each ffmpeg progress key to a field assignment. This is a lookup anti-pattern: every new ffmpeg key linearly increases CC and makes the function harder to test in isolation.

**Evidence:** Verified via `radon cc`: function at line 51 has CC=21, rank D. Source inspection confirms 11-branch if/elif chain mapping ffmpeg keys (frame, fps, speed, total_size, out_time_us, out_time_ms, out_time, progress) to field assignments, plus special handling for yield/break.

**Recommendation:** Replace the `if/elif` chain with a key→setter lookup table. This drops CC from 21 to ~3 and isolates each parser for unit testing. Effort: small. Priority: recommended.

---

### STR-02: `download_hls_with_resume` — 165-line function with nesting depth 7

| Field | Value |
|-------|-------|
| **ID** | STR-02 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `download_hls_with_resume` (lines 172–336, CC=19) is ~164 lines of executable code, well beyond the 50-line limit, with measured nesting depth **7** (the `if not task.done(): task.cancel()` block at lines 302–304 sits 7 levels deep). It mixes connector setup, playlist fetch, an inline `download_segment_concurrent` closure (~40 lines), `asyncio.gather` orchestration, cancellation handling, progress callbacks, and merge logic — multiple responsibilities in one function.

**Evidence:** Verified via `radon raw` and source inspection. The inner closure `download_segment_concurrent` (lines 248–288) is defined inside the session context. The cancellation handling at lines 300–308 is nested: `try` → `except CancelledError` → `for task in tasks` → `if not task.done()` → `task.cancel()` (depth 5 from inside the closure, depth 7 from outer function).

**Recommendation:** Extract connector construction, segment-worker closure, gather+cancellation handling, and merge step into separate helpers. Each helper ≤50 lines and nesting ≤3. Effort: medium. Priority: recommended.

---

### STR-03: `download_with_ytdlp_with_resume_fallback` — nesting depth 7 inside retry loop

| Field | Value |
|-------|-------|
| **ID** | STR-03 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `download_with_ytdlp_with_resume_fallback` (lines 243–336, CC=12) reaches nesting depth **7**: the `if segment_result: return segment_result` (line 324) sits inside `if browser_streams` (307) → `try` (300) → `if retry_count <= MAX_RESUME_RETRIES` (297) → `if validated_output.exists()` (288) → `while retry_count <= MAX_RESUME_RETRIES` (276). The token-refresh + segment-resume block is a deeply nested "pyramid of doom" embedded in the retry loop.

**Evidence:** Verified via source inspection. The nesting chain at lines 276-325 is: `while` → `if validated_output.exists()` → `if retry_count <= MAX_RESUME_RETRIES` → `try` → `if browser_streams` → `await download_hls_with_resume()` → `if segment_result` (depth 7).

**Recommendation:** Extract the resume block into a `_attempt_segment_resume(...)` helper and call it as a flat expression. Effort: medium. Priority: recommended.

---

### STR-04: `batch_download` — 188-line CLI entrypoint with closure nesting depth 7

| Field | Value |
|-------|-------|
| **ID** | STR-04 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `batch_download` (lines 179–366, CC=14) is ~187 lines. Two large closures (`_download_single` 237–290, `_run_batch_with_progress` 292–336) are defined inline, and `_run_batch_with_progress` reaches nesting depth **7** in its cancellation handling. The outer function additionally mixes logging setup, file reading, batch orchestration, result aggregation, and summary printing — multiple responsibilities.

**Evidence:** Verified via `radon cc` (CC=14) and source inspection. The cancellation handling at lines 317–327 is nested: `for coro in asyncio.as_completed(tasks)` → `try` → `except CancelledError` → `for task in tasks` → `if not task.done()` → `task.cancel()` (depth 7 from inside the closure).

**Recommendation:** Hoist `_download_single` and `_run_batch_with_progress` to module-level helpers. Extract result aggregation + summary printing into `_print_batch_summary(results)`. Effort: medium. Priority: recommended.

---

### STR-05: `perform_download` — nesting depth 5 and duplicated cookie-resolution logic

| Field | Value |
|-------|-------|
| **ID** | STR-05 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `perform_download` (lines 460–567, CC=14) reaches nesting depth **5** inside the `match` cases. It also duplicates the exact same cookie-resolution block in both `DownloadMethod.YTDLP` and `DownloadMethod.FFMPEG` cases (lines 523–529 vs 535–541), violating single-responsibility.

**Evidence:** Verified via source inspection. Lines 523–529 (YTDLP case) and lines 535–541 (FFMPEG case) contain identical logic: `if settings.cookie_source == CookieSource.BROWSER:` → `await extractor.extract_streams_with_cookies(url)` → `if browser_streams:` → `m3u8_url = str(browser_streams[0].url)` → `else:` → `browser_streams = None; cookies = None`.

**Recommendation:** Extract `_resolve_cookies(extractor, settings, url) -> tuple[str, str | None]` returning `(m3u8_url, cookies)` and call it once per branch. Effort: small. Priority: recommended.

---

### STR-06: `_download_segment` — CC 12 with nesting depth 4 mixing sequential and parallel paths

| Field | Value |
|-------|-------|
| **ID** | STR-06 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_download_segment` (lines 42–97, CC=12) has nesting depth **4** (`with open(...) as f: f.write(...)` at 70–71 and 87–88 sits inside `if` → `if content`/`if status==200` → `try`/`async with`). It also folds two distinct download strategies (sequential retry-with-backoff path and parallel/coordinator path) into one function guarded by `if max_concurrent_downloads == 1`.

**Evidence:** Verified via `radon cc` (CC=12) and source inspection. Lines 67–73 handle sequential mode with `_retry_429_with_backoff`. Lines 76–97 handle parallel mode with backoff_coordinator integration. Both paths share the same function scope.

**Recommendation:** Split into `_download_segment_sequential(...)` and `_download_segment_parallel(...)` helpers. Each helper then has CC ≤5 and nesting ≤3. Effort: small. Priority: recommended.

---

### STR-07: `_retry_429_with_backoff` — nesting depth 6 with double-nested try/except

| Field | Value |
|-------|-------|
| **ID** | STR-07 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `_retry_429_with_backoff` (lines 142–239) has nesting depth **6**: the `except TimeoutError: pass` (line 221–223) is inside `for attempt` (167) → `try` (173) → `async with session.get` (174) → `try` (214) → `asyncio.wait_for` (215). The retry-delay calculation and shutdown-wait block are embedded several levels deep.

**Evidence:** Verified via `radon cc` (CC=10) and source inspection. The inner try/except block at lines 214–223 handles shutdown interruption during backoff delay, nested 6 levels deep.

**Recommendation:** Extract `_compute_backoff_delay(response, attempt) -> float` and `_wait_with_shutdown(delay, shutdown_event) -> bool` as standalone helpers. Effort: small. Priority: recommended.

---

### STR-08: `services/downloader.py` is a god module (409 SLOC, >300 limit)

| Field | Value |
|-------|-------|
| **ID** | STR-08 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `services/downloader.py` is **409 SLOC** (Radon raw), exceeding the 300-line file limit. It co-locates unrelated responsibilities: Netscape cookie conversion (`_cookies_to_netscape`), the `HLSDownloader` class, three module-level async download orchestrators (`download_with_ytdlp_with_resume_fallback`, `_download_with_ytdlp`, `perform_download`), and signal handling (`setup_signal_handlers`).

**Evidence:** Verified via `radon raw`: LOC 568, SLOC 409. The module contains disconnected functionality: cookie formatting (lines 75–90), class `HLSDownloader` (lines 92–241), function `download_with_ytdlp_with_resume_fallback` (lines 243–336), function `_download_with_ytdlp` (lines 339–417), function `setup_signal_handlers` (lines 424–457), and function `perform_download` (lines 460–567).

**Recommendation:** Split into `services/cookies.py`, `services/signal_handlers.py`, and keep `HLSDownloader` in `hls_downloader.py`. Effort: medium. Priority: recommended.

---

### STR-09: `perform_download` declares 11 parameters (exceeds 5-parameter limit)

| Field | Value |
|-------|-------|
| **ID** | STR-09 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `perform_download` (signature lines 460–472) takes **11 parameters**: `url, quality, output_file, method, extractor, settings, backoff_coordinator, semaphore, progress_callback, video_data, selected_stream`. This exceeds the ≤5 parameter guideline. Note the project already defines request dataclasses (`DownloadRequest`, `HLSDownloadRequest` in `models/dtos.py`) yet `perform_download` still uses a flat primitive signature, creating an inconsistency.

**Evidence:** Verified via source inspection at lines 460–472. The `HLSDownloadRequest` dataclass exists and is used by `download_hls_with_resume`, confirming the pattern is established in this codebase.

**Recommendation:** Extend `DownloadRequest` dataclass to bundle all 11 parameters and change `perform_download(request: DownloadRequest)`. Effort: small. Priority: recommended.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 9 | STR-01, STR-02, STR-03, STR-04, STR-05, STR-06, STR-07, STR-08, STR-09 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

None. All findings are verified and correctly classified.

### Merged Findings

None. No overlapping root causes detected between findings.

### Reclassified Findings

None. All findings are correctly classified as BEST-PRACTICE improvements.

### Rollout Safety Analysis

The findings in this phase are all advisory BEST-PRACTICE recommendations focused on code quality improvements. They have no rollout safety concerns:

- All changes are structural refactors (no behavior changes)
- No circular dependencies introduced
- Changes are modular and can be applied independently
- No migration or backward compatibility concerns

### Advisory Recommendations

1. **STR-01** — `read_progress`: Replace 11-branch if/elif with key→setter lookup table (CC 21→~3). High ROI: simplifies testing and reduces complexity in core ffmpeg integration.

2. **STR-02** — `download_hls_with_resume`: Extract closures/helpers; cut 165 lines & depth-7 nesting. High ROI: improves testability of segment download orchestration.

3. **STR-03** — `download_with_ytdlp_with_resume_fallback`: Extract resume block; cut depth-7 nesting. High ROI: clarifies retry logic and reduces cognitive load.

4. **STR-04** — `batch_download`: Hoist closures to module level; extract summary printing. High ROI: follows existing pattern of `HLSDownloadRequest` usage.

5. **STR-05** — `perform_download`: Extract duplicated cookie-resolution; cut depth-5 nesting. High ROI: eliminates clear duplication and aligns with DRY principles.

6. **STR-06** — `_download_segment`: Split sequential/parallel paths. High ROI: separates concerns and improves testability.

7. **STR-07** — `_retry_429_with_backoff`: Extract backoff/shutdown-wait helpers; cut depth-6 nesting. Medium ROI: clarifies retry logic without changing behavior.

8. **STR-08** — `services/downloader.py`: Split god module (409 SLOC) into focused files. High ROI: improves code organization and follows single-responsibility principle.

9. **STR-09** — `perform_download`: Replace 11-param signature with `DownloadRequest` dataclass. High ROI: aligns with existing `HLSDownloadRequest` pattern and reduces call-site complexity.