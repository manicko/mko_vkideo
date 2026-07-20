---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 09 Audit Findings — Structural Code Quality

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/09-structural-quality.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Evidence

**Step R1 — Cyclomatic Complexity (`uv run radon cc src/vkdownloader -a -s`):**
- Total blocks analyzed: 125.
- Project average complexity: **A (3.44)** — within the ≤5 threshold.
- Functions with rank **C (≥11) or worse**: exactly **1** — `cli.py:_download_single` at **CC 17**.
- **No** function with rank D/E/F (≥21).

**Step R2 — Maintainability Index (`uv run radon mi src/vkdownloader -s`):**
- All 23 files rank **A** (no B/C files).
- Lowest MI scores (still rank A, but approaching B threshold ~20): `segment_downloader.py` **42.21**, `downloader.py` **45.42**, `cli.py` **53.20**, `ffmpeg_utils.py` **58.03**, `extractor.py` **61.60**. These low-A scores correlate with the large-file and high-CC findings below.

**Step R3 — Function Length (AST measurement, body lines excluding blank/comment deltas):**
- Files exceeding the 300-LOC guideline: `segment_downloader.py` (LOC 839 / SLOC 544), `downloader.py` (LOC 777 / SLOC 532), `cli.py` (LOC 489 / SLOC 323).
- Functions exceeding 50 body lines: `_download_single` (93), `download` (116), `perform_download` (120), `download_with_ytdlp_with_resume_fallback` (80), `download_with_ffmpeg` (109), `_attempt_segment_resume` (89), `_run_batch_with_progress` (80), `batch_download` (69).

**Step R4 — Nesting Depth (AST measurement of compound-statement depth):**
- `ffmpeg_utils.py:read_progress` — **nesting 5** (arrow code).
- `cli.py:_run_batch_with_progress` — **nesting 4**.
- `downloader_throttle.py:_retry_429_with_backoff` — **nesting 4**.
- `network_monitor.py:_extract_urls_from_json` — **nesting 4**.

**Step R5 — Control Flow Patterns:**
- **No `for...else`** usage anywhere in the source tree (grep confirmed — all `else:` blocks are paired with `if`, not `for`).
- Functions with **>5 parameters** (parameter overpass): `perform_download` (11), `download_with_ytdlp_with_resume_fallback` (11), `_run_download_session` (11), `_attempt_segment_resume` (10), `_download_segment` (10), `_build_ytdlp_options` (8), `_download_segment_parallel` (8), `_run_parallel_download_with_backoff` (9), `_do_parallel_download_attempt` (9), `_try_single_download_attempt` (9), `_download_with_ytdlp` (7), `_download_single` (7), `download` (6), `_run_batch_with_progress` (6), `download_with_ffmpeg` (6), `batch_download` (7).

---

## Findings

### STR-001: Arrow-code in `read_progress` — nesting depth 5

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** The `read_progress` async generator (lines 64-97) nests control flow 5 levels deep: `while True` (L80) → `if parsed` (L87) → `if handler is not None` / `elif key == "progress"` (L90-92) → `if value == "end"` (L95). This is the classic "pyramid of doom" — the happy-path logic is pushed to the far right and the exit condition (`value == "end"`) is buried at the deepest level, making the flow hard to follow and easy to break when the progress protocol changes.

**Evidence:**
```
src/vkdownloader/services/ffmpeg_utils.py:64  async def read_progress(...)
src/vkdownloader/services/ffmpeg_utils.py:80      while True:                       # depth 1
src/vkdownloader/services/ffmpeg_utils.py:87          if parsed:                   # depth 2
src/vkdownloader/services/ffmpeg_utils.py:90              if handler is not None:   # depth 3
src/vkdownloader/services/ffmpeg_utils.py:92              elif key == "progress":  # depth 3
src/vkdownloader/services/ffmpeg_utils.py:95                  if value == "end":    # depth 4
   (AST measurement: effective max nesting = 5)
```
`radon cc` confirms rank B (8); AST compound-statement depth = 5 (exceeds the ≤3 guideline, and exceeds 4 → HIGH per severity guide).

**Recommendation:** Flatten with guard clauses / early `continue`. Example shape:
```python
async def read_progress(stderr, duration_ms=None, stderr_collector=None):
    progress = FfmpegProgress()
    while True:
        line = await stderr.readline()
        if not line:
            break
        if stderr_collector is not None:
            stderr_collector.append(line)
        parsed = ProgressParser.parse_line(line.decode())
        if not parsed:
            continue
        key, value = parsed
        handler = _PROGRESS_KEY_HANDLERS.get(key)
        if handler is not None:
            handler(value, progress)
            continue
        if key != "progress":
            continue
        progress.progress = value
        yield progress
        if value == "end":
            break
        progress = FfmpegProgress()
```
This drops the deepest nesting to 1 and keeps the function linear top-to-bottom. Effort: trivial. Priority: recommended.

---

### STR-002: Deep nesting (depth 4) in `_run_batch_with_progress`

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `_run_batch_with_progress` (L172-251, 80 lines) nests to depth 4 at the cancellation handling block: `for coro in asyncio.as_completed(tasks)` (L229) → `except asyncio.CancelledError` (L232) → `for task in tasks` (L234) → `if not task.done()` (L235). The nested loops/branches inside a broad `except` make the cancellation path hard to reason about and test in isolation.

**Evidence:**
```
src/vkdownloader/cli.py:172  async def _run_batch_with_progress(...)
src/vkdownloader/cli.py:229      for coro in asyncio.as_completed(tasks):   # depth 1
src/vkdownloader/cli.py:232          except asyncio.CancelledError:        # depth 2
src/vkdownloader/cli.py:234              for task in tasks:                 # depth 3
src/vkdownloader/cli.py:235                  if not task.done():            # depth 4
```
AST measurement: nesting = 4; radon CC = B (10).

**Recommendation:** Extract the cancellation-cleanup block (L232-239) into a helper, e.g. `_cancel_remaining(tasks)`, that performs the inner loop. The main loop body then becomes a single `try/except` calling the helper. This lowers the function to nesting ≤2 and isolates the cancellation concern for unit testing. Effort: small. Priority: recommended.

---

### STR-003: Deep nesting (depth 4) in `_retry_429_with_backoff`

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `_retry_429_with_backoff` (L156-234, 79 lines, radon CC B=8, 6 params) contains retry/backoff logic nested 4 levels deep (outer retry `for` → `if` status branch → nested `try`/`for` over headers → conditional publish). Backoff and status-classification concerns are interleaved, raising cognitive load and making the retry policy hard to verify independently.

**Evidence:** `radon cc src/vkdownloader/services/downloader_throttle.py` → `_retry_429_with_backoff - B (8)`; AST measurement nesting = 4. Full body at `src/vkdownloader/services/downloader_throttle.py:156-234`.

**Recommendation:** Extract (a) the per-attempt HTTP fetch + status classification into a small helper, and (b) the backoff-delay decision into the existing `_compute_backoff_delay` helper (already present at L271). The retry loop should read as: classify status → decide delay → wait → repeat. Reduces nesting to ≤2 and reuses the existing delay helper. Effort: small. Priority: recommended.

---

### STR-004: Deep nesting (depth 4) in `_extract_urls_from_json`

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | advisory |

**Description:** `_extract_urls_from_json` (L86-104, radon CC B=9) reaches nesting depth 4 while walking nested dict/list structures (`for value in data.values()` → `if isinstance(list)` → `for item in data` → `if isinstance(dict)`). Recursive/recursive-shaped traversal logic is interleaved with URL-extraction, making the function do two things (traverse + extract).

**Evidence:** `radon cc .../network_monitor.py` → `_extract_urls_from_json - B (9)`; AST measurement nesting = 4; body at `src/vkdownloader/infrastructure/network_monitor.py:86-104`.

**Recommendation:** Extract the generic recursive "walk all dict/list nodes" traversal into a generator (`_walk_json(node)`), and have `_extract_urls_from_json` consume yielded dict/list nodes to apply the `m3u8`/`.mp4` filter. This separates traversal from extraction, drops nesting to ≤2, and makes the traversal reusable. Effort: small. Priority: recommended.

---

### STR-005: `_download_single` — high complexity (CC 17), 93 lines, multiple responsibilities

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `_download_single` (L77-169) is the only function in the project with radon rank **C (CC 17)**, and is 93 lines with 7 parameters. It performs at least five distinct responsibilities: (1) context unpacking, (2) settings merge, (3) stream extraction + quality selection, (4) output-path resolution / validation / filename generation, and (5) orchestration call + result mapping, plus a 6-branch `except` chain mapping domain errors to status strings. The single-responsibility guideline is violated, and the long exception chain is the primary CC contributor.

**Evidence:**
```
radon cc src/vkdownloader/cli.py
    F 77:0 _download_single - C (17)
AST: lines=93, params=7, nesting=2
src/vkdownloader/cli.py:106-145  try body (extraction/selection/resolve/call)
src/vkdownloader/cli.py:150-169  6-branch except chain (Cancelled/ValueError/QualityNotAvailable/VideoNotFound/VKDownloadError/Exception)
```

**Recommendation:** Split into focused helpers: (a) `_resolve_output_file(video, output, settings, index)` to encapsulate L117-131 (path resolution, validation, sanitized filename); (b) a small `_map_error_to_status(url, exc)` lookup/dispatch for the `except` chain instead of sequential `except` blocks. `_download_single` then becomes a thin orchestrator: unpack context → extract → select → resolve path → `perform_download` → map result. Target CC ≤10 and length ≤50. Effort: medium. Priority: recommended.

---

### STR-006: Parameter overpass in orchestrator functions (up to 11 params)

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** Several orchestration functions exceed the ≤5-parameter guideline by a wide margin, signalling "function does too much" / missing parameter object:
- `perform_download` — **11** params (`downloader.py:658`)
- `download_with_ytdlp_with_resume_fallback` — **11** params (`downloader.py:358`)
- `_run_download_session` — **11** params (`segment_downloader.py:680`)
- `_attempt_segment_resume` — **10** params (`downloader.py:440`)
- `_download_segment` — **10** params (`segment_downloader.py:291`)
- `_build_ytdlp_options` — **8** (`downloader.py:130`), `_download_segment_parallel` — **8** (`segment_downloader.py:242`)
- Plus several 7-9 param helpers.

Long positional/keyword parameter lists are error-prone (easy to swap args), hard to call, and hard to test (every test must supply all 11). `DownloadPolicy` (`segment_downloader.py:44`) and `DownloadContext`/`HLSDownloadRequest` already demonstrate the right pattern — a dataclass bundling related params — but it is applied inconsistently.

**Evidence:** AST parameter counts + `radon cc` output listing the above functions; e.g. `downloader.py:658 perform_download` CC B(10) with 11 params; `segment_downloader.py:680 _run_download_session` CC A(3) with 11 params.

**Recommendation:** Introduce focused parameter objects (dataclasses) for the repeated `(url, quality, output_file, method, settings, extractor, backoff_coordinator, semaphore, progress_callback, video_data, selected_stream)` cluster. `perform_download` and `download_with_ytdlp_with_resume_fallback` can accept a `DownloadOptions`/`RequestContext` object. This collapses 11 params to ~3-4, reduces call-site verbosity (already very repetitive — see `downloader.py:720-735` vs `737-757` vs `761-774`), and makes adding fields (e.g. a new retry policy) non-breaking. Effort: medium. Priority: recommended.

---

### STR-007: Duplicated output-path / filename resolution in `cli.py`

| Field | Value |
|-------|-------|
| **ID** | STR-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** The output-path resolution + sanitized-filename generation logic appears twice, nearly identically, in `_download_single` (L117-131) and the inner `_download()` of `download` (L350-365). Divergent filenames are even produced: `_download_single` uses `{safe_title}_{video.id}.mp4` while `download` falls back to `{video.id}_{stream.quality}.mp4`. This duplication risks the two code paths drifting (they already differ in the fallback case), and the divergence is a latent behavioral inconsistency between single and batch modes.

**Evidence:**
```
src/vkdownloader/cli.py:117-131   _download_single: output_path resolve + validate + mkdir + filename
src/vkdownloader/cli.py:350-365   download::_download: same block, different fallback filename
```

**Recommendation:** Extract a single `_resolve_output_file(video, output, settings, index, stream)` helper (ties into STR-005) and call it from both code paths. This removes duplication and, by sharing one implementation, forces a decision on the fallback filename convention (eliminating the current single-vs-batch inconsistency). Effort: small. Priority: recommended.

---

### STR-008: `downloader.py` `__all__` re-export hub (god-module facade)

| Field | Value |
|-------|-------|
| **ID** | STR-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `downloader.py` (777 LOC / SLOC 532) acts as both an implementation module and a re-export facade. Its `__all__` (L208-232) re-exports ~24 names, many of which are **imported from other modules** (`_cookies_to_netscape` from `cookies.py`, `download_hls_with_resume` / `_download_segment*` / `_fetch_playlist_with_retry` from `segment_downloader.py`, `read_progress` / `_merge_segments_batched` / `cancel_ffmpeg_process` from `ffmpeg_utils.py`, `_retry_429_with_backoff` from `downloader_throttle.py`, `setup_signal_handlers` from `signal_handlers.py`). This makes `downloader.py` a central import hub: consumers importing from it couple to the wrong module, and the module mixes its own orchestration logic (`perform_download`, `download_with_ytdlp_with_resume_fallback`) with pass-through re-exports. This is a structural smell contributing to its low MI (45.42).

**Evidence:**
```
src/vkdownloader/services/downloader.py:207-232  __all__ = [ ... ] re-exporting cross-module symbols
src/vkdownloader/services/downloader.py:25-47    corresponding imports from cookies/segment_downloader/ffmpeg_utils/downloader_throttle/signal_handlers
```

**Recommendation:** Remove the cross-module re-exports from `downloader.py.__all__` and have callers (e.g. `cli.py`, `extractor.py`) import directly from the owning module. Keep `__all__` limited to symbols actually defined in `downloader.py`. This shrinks the module's responsibility surface, removes the facade indirection, and improves MI. Per the Dead-Code Policy, verify each re-exported name is still consumed before removal (do not delete blindly). Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 3 |

## Mandatory Fixes

None. All findings are advisory (structural quality / maintainability). No security, data-loss, or correctness defects were identified in this phase.

## Advisory Recommendations

- **STR-001** (HIGH): Flatten `read_progress` arrow code via guard clauses (nesting 5 → 1).
- **STR-002** (MEDIUM): Extract cancellation-cleanup helper from `_run_batch_with_progress`.
- **STR-003** (MEDIUM): Decompose `_retry_429_with_backoff` retry/backoff interleave.
- **STR-004** (MEDIUM): Separate JSON traversal from URL extraction in `network_monitor._extract_urls_from_json`.
- **STR-005** (MEDIUM): Decompose `_download_single` (CC 17) into path-resolution + error-mapping helpers.
- **STR-006** (MEDIUM): Introduce parameter objects for 10-11-param orchestrators (`perform_download`, `_run_download_session`, etc.).
- **STR-007** (LOW): De-duplicate output-path/filename logic in `cli.py`; unify single-vs-batch fallback filename.
- **STR-008** (LOW): Drop cross-module `__all__` re-exports from `downloader.py`.

## Doc Updates Needed

None required. Findings are forward-looking code-structure improvements, not documentation divergences. (No spec deviation found; all code matches the documented module layout in `docs/STRUCT.md`.)
