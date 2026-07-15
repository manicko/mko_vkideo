---
name: 09-structural-quality-findings
description: Phase 09 audit findings for structural code quality (complexity, length, nesting, control flow)
agent: auditor
status: complete
validated: no
---

# Phase 09 Audit Findings — Structural Code Quality

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/09-structural-quality.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Evidence

### R1 — Radon Cyclomatic Complexity (`uv run radon cc src/ -s -a`)

Functions at rank **C or worse (CC ≥ 11)**:

| Function | Location | CC | Rank |
|----------|----------|----|------|
| `read_progress` | `services/ffmpeg_utils.py:51` | 21 | **D** |
| `download_hls_with_resume` | `services/segment_downloader.py:172` | 19 | C |
| `batch_download` | `cli.py:179` | 14 | C |
| `perform_download` | `services/downloader.py:460` | 14 | C |
| `download_with_ytdlp_with_resume_fallback` | `services/downloader.py:243` | 12 | C |
| `_download_segment` | `services/segment_downloader.py:42` | 12 | C |

Average complexity across project: **A (3.43)** — passes the ≤5 target (omit).

### R2 — Radon Maintainability Index (`uv run radon mi src/ -s`)

All files scored rank **A**. No MI-rank B/C files. (Validates that issues are localized to specific functions, not whole-file rot.)

### R3/R4 — Function length & nesting depth

Measured manually from source (nesting depth = deepest `if/for/while/try/with` indentation; length excludes docstring/blank lines where noted).

| Function | SLOC (body) | Nesting depth | CC |
|----------|-------------|---------------|----|
| `download_hls_with_resume` | ~165 | **7** | 19 |
| `batch_download` | ~188 (outer) | **7** (inner closure) | 14 |
| `download_with_ytdlp_with_resume_fallback` | ~66 | **7** | 12 |
| `perform_download` | ~77 | **5** | 14 |
| `_retry_429_with_backoff` | ~76 | **6** | 10 |
| `read_progress` | ~47 | **4** | 21 |
| `_download_segment` | ~41 | **4** | 12 |

### R5 — Control flow patterns

- `for...else`: none found.
- Excessive parameters: `perform_download` declares **11** parameters (>5 limit).
- File size: `services/downloader.py` SLOC = **409** (>300 limit — god module).

---

## Findings

### STR-01: `read_progress` has cyclomatic complexity 21 (rank D) and a 11-branch if/elif chain

| Field | Value |
|-------|-------|
| **ID** | STR-01 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** `read_progress` (lines 51–97) is the only function in the project at Radon rank **D** (CC=21), which violates the phase's "no CC rank D or worse (≥21)" threshold. Its complexity comes almost entirely from a flat 11-branch `if/elif` chain (lines 76–96) that maps each ffmpeg progress key (`frame`, `fps`, `speed`, `total_size`, `out_time_us`, `out_time_ms`, `out_time`, `progress`, …) to a field assignment. This is an arrow/lookup anti-pattern: every new ffmpeg key linearly increases CC and makes the function harder to test in isolation.

**Evidence:**
```
src/vkdownloader/services/ffmpeg_utils.py:73-96
    parsed = ProgressParser.parse_line(line.decode())
    if parsed:
        key, value = parsed
        if key == "frame":
            progress.frame = int(value) if value != "N/A" else None
        elif key == "fps":
            progress.fps = float(value) if value != "N/A" else None
        elif key == "speed":
            progress.speed = float(value.rstrip("x")) if value != "N/A" else None
        elif key == "total_size":   ...   # (11 branches total)
        ...
        elif key == "progress":
            progress.progress = value
            yield progress
            if value == "end":   # nesting depth 4
                break
```

**Recommendation:** Replace the `if/elif` chain with a key→setter lookup table, e.g. a module-level dict `PROGRESS_FIELDS: dict[str, Callable[[str], object]]` mapping each ffmpeg key to a parse function (`{"frame": lambda v: int(v) if v != "N/A" else None, ...}`). The loop body becomes `setattr(progress, key, PROGRESS_FIELDS[key](value))` plus special handling for the `progress`/`end` yield. This drops CC from 21 to ~3 and isolates each parser for unit testing. Effort: small. Priority: recommended.

---

### STR-02: `download_hls_with_resume` — 165-line function with nesting depth 7

| Field | Value |
|-------|-------|
| **ID** | STR-02 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `download_hls_with_resume` (lines 172–336) is ~165 lines of executable code, well beyond the 50-line limit, with measured nesting depth **7** (the `if not task.done(): task.cancel()` block at lines 302–304 sits 7 levels deep). It mixes connector setup, playlist fetch, an inline `download_segment_concurrent` closure (~40 lines, itself nesting 7), `asyncio.gather` orchestration, cancellation handling, progress callbacks, and merge logic — at least four responsibilities in one function. This is the most severe structural smell in the codebase and is effectively untestable in isolation.

**Evidence:**
```
src/vkdownloader/services/segment_downloader.py:296-308
    if tasks:
        try:
            results = await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            for task in tasks:          # depth 5
                if not task.done():     # depth 6
                    task.cancel()        # depth 7
```
Plus the inner closure at 248–288 reaches depth 7 under the `semaphore_to_use` context manager.

**Recommendation:** Extract (a) connector construction, (b) the segment-worker closure into a standalone `async def _download_one_segment(...)` helper, (c) the `gather` + cancellation handling into a `_run_segment_tasks(...)` helper, and (d) the merge step. Reduce nesting with guard clauses (`if not playlist_content: return None` already exists; apply the same to tasks/merge paths). Target each helper ≤50 lines and nesting ≤3. Effort: medium. Priority: recommended.

---

### STR-03: `download_with_ytdlp_with_resume_fallback` — nesting depth 7 inside retry loop

| Field | Value |
|-------|-------|
| **ID** | STR-03 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `download_with_ytdlp_with_resume_fallback` (lines 243–336, CC=12) reaches nesting depth **7**: the `if segment_result: return segment_result` (line 324) sits inside `if browser_streams` (307) → `try` (300) → `if retry_count <= MAX_RESUME_RETRIES` (297) → `if validated_output.exists()...` (288) → `while retry_count <= MAX_RESUME_RETRIES` (276). The token-refresh + segment-resume block is a deeply nested "pyramid of doom" embedded in the retry loop, making the resume path hard to follow and reason about.

**Evidence:**
```
src/vkdownloader/services/downloader.py:276-325
    while retry_count <= MAX_RESUME_RETRIES:        # depth 1
        ...
        if validated_output.exists() and ...:        # depth 2
            if retry_count <= MAX_RESUME_RETRIES:    # depth 3
                try:                                 # depth 4
                    ...
                    if browser_streams:              # depth 5
                        m3u8_url = str(browser_streams[0].url)
                        segment_result = await download_hls_with_resume(   # depth 6
                            HLSDownloadRequest(...)  # depth 7
                        )
                        if segment_result:          # depth 7
                            return segment_result
```

**Recommendation:** Extract the resume block into a `_attempt_segment_resume(video_url, m3u8_url, output_file, quality, extractor, settings) -> Path | None` helper and call it as a flat `result = await _attempt_segment_resume(...); if result: return result`. Push the `retry_count <= MAX_RESUME_RETRIES` guard to an early `return None` (guard clause) so the success/partial-file logic is not doubly nested. Effort: medium. Priority: recommended.

---

### STR-04: `batch_download` — 188-line CLI entrypoint with closure nesting depth 7

| Field | Value |
|-------|-------|
| **ID** | STR-04 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `batch_download` (lines 179–366, CC=14) is ~188 lines. Two large closures (`_download_single` 237–290, `_run_batch_with_progress` 292–336) are defined inline, and `_run_batch_with_progress` reaches nesting depth **7** in its cancellation handling (`if not task.done(): task.cancel()` at 322–324, 5 levels inside the closure which is already 2 levels inside the outer `try`). The outer function additionally mixes logging setup, file reading, batch orchestration, result aggregation, and summary printing — multiple responsibilities.

**Evidence:**
```
src/vkdownloader/cli.py:317-327
    for coro in asyncio.as_completed(tasks):          # depth 2 (inside closure)
        try:                                          # depth 3
            await coro
        except asyncio.CancelledError:                # depth 4
            for task in tasks:                        # depth 5
                if not task.done():                   # depth 6
                    task.cancel()                     # depth 7
```

**Recommendation:** Hoist `_download_single` and `_run_batch_with_progress` to module-level helpers (they already only close over a few parameters that can be passed explicitly). Extract result aggregation + summary printing (lines 342–361) into `_print_batch_summary(results)`. After extraction the outer `batch_download` becomes a thin coordinator. Effort: medium. Priority: recommended.

---

### STR-05: `perform_download` — nesting depth 5 and duplicated cookie-resolution logic

| Field | Value |
|-------|-------|
| **ID** | STR-05 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `perform_download` (lines 460–567, CC=14) reaches nesting depth **5** inside the `match` cases (e.g. `if browser_streams:` at 525/537 is depth 4, and the `HLSDownloadRequest(...)` call at 547 is depth 5). It also duplicates the exact same cookie-resolution block in both `DownloadMethod.YTDLP` and `DownloadMethod.FFMPEG` cases (lines 523–529 vs 535–541), violating single-responsibility and increasing the chance of divergence.

**Evidence:**
```
src/vkdownloader/services/downloader.py:523-529  (YTDLP case)
    if settings.cookie_source == CookieSource.BROWSER:
        browser_streams, cookies = await extractor.extract_streams_with_cookies(url)
        if browser_streams:
            m3u8_url = str(browser_streams[0].url)
    else:
        browser_streams = None
        cookies = None
# ...identical block repeated at 535-541 (FFMPEG case)
```

**Recommendation:** Extract `_resolve_cookies(extractor, settings, url) -> tuple[str, str | None]` returning `(m3u8_url, cookies)` and call it once per branch. This collapses the duplication and trims nesting. (Pairs with STR-09's request-object refactor.) Effort: small. Priority: recommended.

---

### STR-06: `_download_segment` — CC 12 with nesting depth 4 mixing sequential and parallel paths

| Field | Value |
|-------|-------|
| **ID** | STR-06 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_download_segment` (lines 42–97, CC=12) has nesting depth **4** (`with open(...) as f: f.write(...)` at 70–71 and 87–88 sits inside `if`→`if content`/`if status==200`→`try`/`async with`). It also folds two distinct download strategies (sequential retry-with-backoff path at 67–73 and parallel/coordinator path at 76–97) into one function guarded by `if max_concurrent_downloads == 1`, which inflates CC and obscures both flows.

**Evidence:** `src/vkdownloader/services/segment_downloader.py:67-97` — two code paths under one function with the sequential branch's `with open` at depth 3–4 and the parallel branch's `with open` at depth 4.

**Recommendation:** Split into `_download_segment_sequential(...)` and `_download_segment_parallel(...)` helpers selected by a guard at the call site (in `download_segment_concurrent`). Each helper then has CC ≤5 and nesting ≤3. Effort: small. Priority: recommended.

---

### STR-07: `_retry_429_with_backoff` — nesting depth 6 with double-nested try/except

| Field | Value |
|-------|-------|
| **ID** | STR-07 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `_retry_429_with_backoff` (lines 142–239) sits exactly at the CC threshold (CC=10, rank B) but reaches nesting depth **6**: the `except TimeoutError: pass` (line 221–223) is inside `try` (214) → `async with session.get` (174) → `try` (173) → `for attempt` (167). The retry-delay calculation (191–202) and the shutdown-wait block (213–223) are embedded several levels deep, making the backoff logic hard to verify.

**Evidence:**
```
src/vkdownloader/services/downloader_throttle.py:173-223
    try:                                     # depth 2
        async with session.get(...) as response:   # depth 3
            if response.status == 200:     # depth 4
                return await response.read()
            ...
            try:                            # depth 4
                await asyncio.wait_for(shutdown_event.wait(), timeout=delay)  # depth 5
                return None
            except TimeoutError:           # depth 5
                pass                        # depth 6
```

**Recommendation:** Extract `_compute_backoff_delay(response, attempt) -> float` and `_wait_with_shutdown(delay, shutdown_event) -> bool` (returns True if cancelled) as standalone helpers called from the loop body. This removes the inner `try/except` nesting and clarifies the retry decision. Effort: small. Priority: recommended.

---

### STR-08: `services/downloader.py` is a god module (409 SLOC, >300 limit)

| Field | Value |
|-------|-------|
| **ID** | STR-08 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `services/downloader.py` is **409 SLOC** (Radon raw, excluding blanks/comments) and 568 total LOC, exceeding the 300-line file limit. It co-locates unrelated responsibilities: Netscape cookie conversion (`_cookies_to_netscape`), the `HLSDownloader` class, three module-level async download orchestrators (`download_with_ytdlp_with_resume_fallback`, `_download_with_ytdlp`, `perform_download`), and signal handling (`setup_signal_handlers`). This concentrates the highest-complexity functions (STR-03, STR-05) in one file and makes the module expensive to load and review.

**Evidence:** `uv run radon raw src/vkdownloader/services/downloader.py` → LOC 568, SLOC 409. Combined with STR-03/STR-05 which both live in this file.

**Recommendation:** Split into `services/cookies.py` (cookie conversion), `services/signal_handlers.py` (`setup_signal_handlers`), and keep `HLSDownloader` in `hls_downloader.py`; `perform_download` and friends remain the download orchestration module. Each resulting file drops well under 300 SLOC. Effort: medium. Priority: recommended.

---

### STR-09: `perform_download` declares 11 parameters (exceeds 5-parameter limit)

| Field | Value |
|-------|-------|
| **ID** | STR-09 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `perform_download` (signature lines 460–472) takes **11** parameters: `url, quality, output_file, method, extractor, settings, backoff_coordinator, semaphore, progress_callback, video_data, selected_stream`. This exceeds the ≤5 parameter guideline and signals the function should accept a single request object. Note the project already defines request dataclasses (`DownloadRequest`, `HLSDownloadRequest` in `models/dtos.py`) yet `perform_download` still uses a flat primitive signature, creating an inconsistency with sibling functions like `download_hls_with_resume` (which takes a single `HLSDownloadRequest`).

**Evidence:** `src/vkdownloader/services/downloader.py:460-472` — 11-parameter `async def perform_download(...)`.

**Recommendation:** Introduce/extend a `DownloadRequest` dataclass bundling `url, quality, output_file, method, extractor, settings, backoff_coordinator, semaphore, progress_callback, video_data, selected_stream`, and change `perform_download(request: DownloadRequest)`. `batch_download` (STR-04) already constructs most of these values and can build the dataclass directly. This also reduces call-site noise at cli.py:269-281. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 5 |
| MEDIUM | 4 |
| LOW | 0 |

## Mandatory Fixes

None (all findings are advisory code-quality/refactoring improvements; no security, data-loss, or correctness defects identified in this phase).

## Advisory Recommendations

- STR-01 — `read_progress`: replace 11-branch if/elif with key→setter lookup table (CC 21→~3).
- STR-02 — `download_hls_with_resume`: extract closures/helpers; cut 165 lines & depth-7 nesting.
- STR-03 — `download_with_ytdlp_with_resume_fallback`: extract resume block; cut depth-7 nesting.
- STR-04 — `batch_download`: hoist closures to module level; extract summary printing.
- STR-05 — `perform_download`: extract duplicated cookie-resolution; cut depth-5 nesting.
- STR-06 — `_download_segment`: split sequential/parallel paths.
- STR-07 — `_retry_429_with_backoff`: extract backoff/shutdown-wait helpers; cut depth-6 nesting.
- STR-08 — `services/downloader.py`: split god module (409 SLOC) into focused files.
- STR-09 — `perform_download`: replace 11-param signature with a `DownloadRequest` dataclass.

## Doc Updates Needed

None.
