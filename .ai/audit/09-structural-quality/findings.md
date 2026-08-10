# Phase 09 Audit Findings — Structural Code Quality

**Executor:** auditor (Senior architecture auditor)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/09-structural-quality.md
**Status:** complete
**Validated:** no
**Problems-only:** yes (passing checks and clean dimensions are omitted per phase output mode)

**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).
Source: `src/vkdownloader/`. Tests: `tests/`.

This phase targets structural shape: cyclomatic complexity, nesting depth, function/file
length, and control-flow patterns. Phases 01-08 findings are not re-filed; only the
structural-quality evidence collected in this phase is recorded below.

---

## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 — Cyclomatic Complexity | `uv run radon cc src/vkdownloader -a -nc` | 10 functions rank C (CC >= 11); average C (12.9); 0 functions rank D+ | `_download_with_ytdlp` CC17; `_download_single` CC16; `perform_download` CC15; `_intercept_response` CC13; `batch_download` CC12; `download_with_ffmpeg` CC12; `_run_batch_with_progress` CC11; `_print_batch_summary` CC11; `download` CC11; `_merge_segments_batched` CC11 |
| R2 — Maintainability Index | `uv run radon mi src/vkdownloader -s` | All 21 source files rank A (radon scale: A if MI>19, B if 9<MI<=19, C if MI<=9); no file ranks B/C | Lowest scores: `downloader.py` 37.13, `segment_downloader.py` 39.09, `cli.py` 44.00 — all still grade A; the low scores corroborate the god-module findings (STR-002) rather than forming a separate MI finding |
| R3 — Function length | AST SLOC scan (blanks + comments excluded) | 16 functions exceed 50 SLOC; 4 exceed 100 SLOC | `perform_download` 152, `_download_with_ytdlp` 142, `download_with_ffmpeg` 122, `download` 104; twelve more in the 55-99 range |
| R4 — Nesting depth | AST scan (if/for/while/try/with blocks) | 8 functions nest deeper than 3; 2 reach depth 5; 6 reach depth 4 | `_retry_429_with_backoff` (5), `_sync_extract` (5); six functions at depth 4 |
| R5 — Control flow patterns | AST scan | 0 `for...else` (clean); 10 functions have >3 return statements; 19 internal functions >5 parameters | `_retry_429_with_backoff` 7 returns; `perform_download` / `download_with_ytdlp_with_resume_fallback` / `download_video` 11 params |

All measurements taken on 2026-08-09 against the live working tree.

---

## Findings

### STR-001: Project cyclomatic complexity exceeds the rank-A budget (average C, 10 rank-C functions)

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (5 functions); `src/vkdownloader/services/downloader.py` (3 functions); `src/vkdownloader/infrastructure/network_monitor.py` (1); `src/vkdownloader/services/ffmpeg_utils.py` (1) |
| **Classification** | advisory |

**Description:** The project has no enforced complexity gate. `radon cc -a` reports an average
complexity of **C (12.9)** — 2.6x the <= 5 target — driven by 10 functions at rank C (CC >= 11).
Three of those cross the HIGH threshold of CC > 15: `_download_with_ytdlp` (CC 17),
`_download_single` (CC 16), and `perform_download` (CC 15). No function reaches rank D (CC >= 21).

The worst offenders are orchestration/dispatch functions that each combine several
responsibilities: `perform_download` (downloader.py:966) dispatches three download strategies via
`match/case` while also resolving cookies and managing a shared semaphore; `_download_with_ytdlp`
(downloader.py:747) mixes subprocess management, progress parsing, output draining and error
logging; `_download_single` (cli.py:181) carries a 6-branch `except` ladder that maps each
exception type to a status tuple.

**Evidence:** `radon cc src/vkdownloader -s`:
```
cli.py:181 _download_single - C (16)
cli.py:543 batch_download - C (12)
cli.py:267 _run_batch_with_progress - C (11)
cli.py:372 _print_batch_summary - C (11)
cli.py:419 download - C (11)
network_monitor.py:53 _intercept_response - C (13)
downloader.py:747 _download_with_ytdlp - C (17)
downloader.py:966 perform_download - C (15)
downloader.py:393 download_with_ffmpeg - C (12)
ffmpeg_utils.py:316 _merge_segments_batched - C (11)
Average complexity: C (12.9)
```

**Recommendation:** Apply Extract Method to peel responsibilities out of each rank-C function
(cookie resolution, progress parsing, strategy dispatch). Replace the `_download_single`
per-type `except` ladder with a single `except VKDownloadError` plus the existing
`exceptions._map_exception_to_status` lookup table. Introduce a CI complexity gate
(`xenon --max-absolute A` or `radon` + threshold in CI) so CC cannot drift without blocking merge.
Effort: medium; priority: recommended.

---

### STR-002: Two service modules are god-modules that exceed the 300-line file cap

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`; `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `downloader.py` is 1218 LOC / **798 SLOC** (3x the 300-line file budget) and
hosts 12 top-level functions including the three highest-CC functions in the project (STR-001).
At 901 LOC / **571 SLOC**, `segment_downloader.py` is the second god-module: 24 functions spanning
playlist fetching, retry/backoff, parallel HTTP I/O, concurrency coordination and segment merging
with no internal boundaries — `_tally_and_merge` is CC 10, `_download_segment_concurrent` CC 9,
`_download_segment_parallel` CC 9. These two files are the root cause of STR-001 and STR-005.

**Evidence:** `radon raw src/vkdownloader` (SLOC excludes blank lines and comments, matching the
phase definition):
```
downloader.py        LOC: 1218  LLOC: 414  SLOC: 798
segment_downloader.py LOC: 901  LLOC: 340  SLOC: 571
```
`radon cc -s` confirms CC 17/15/12 (downloader.py) and CC 10/9/7/9/6 (segment_downloader.py).

**Recommendation:** Split `downloader.py` by download strategy (`ytdlp.py`, `ffmpeg.py`,
`orchestrator.py`) and split `segment_downloader.py` into `playlist.py`,
`segment_concurrency.py` and `segment_merger.py`. Each resulting module should stay well under
300 SLOC and own one responsibility. Effort: large; priority: recommended (architectural).

---

### STR-003: Nesting depth 5 in `_retry_429_with_backoff` and `_sync_extract`

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py:149`; `src/vkdownloader/services/extractor.py:147` |
| **Classification** | advisory |

**Description:** Two functions nest control flow to depth **5** (the project ceiling is 3).

- `downloader_throttle._retry_429_with_backoff` (downloader_throttle.py:149): the chain
  `for attempt` -> `try` -> `async with session.get(...)` -> `if response.status == 200` ->
  `if len(content) == 0` reaches depth 5 and produces **7 return** statements (STR-007).
- `extractor._sync_extract` (extractor.py:147, a closure inside `_extract_with_ytdlp`):
  `with yt_dlp.YoutubeDL(...)` -> `try` -> `for f in formats` ->
  `if f.get("vcodec") != "none"` -> `if format_url:` reaches depth 5; the `Stream(...)`
  construction block is purely a map and is the deepest, least-related part of the function.

Deep nesting of `for/try/with/if` is exactly the arrow-code / pyramid-of-doom smell the phase
targets; it is hard to test in isolation and obscures the retry/loop boundaries.

**Evidence:** AST nesting-depth scan over `src/vkdownloader` (counting if/for/while/try/with):
```
downloader_throttle.py:149 _retry_429_with_backoff  -> nesting depth 5
extractor.py:147 _sync_extract                   -> nesting depth 5
```

**Recommendation:** Flatten with Guard Clauses and single-exit structure. For
`_retry_429_with_backoff`, return early on `shutdown_event` / non-retryable status and use a
`continue` instead of multiple `return None`. For `_sync_extract`, extract the per-format `Stream`
mapping into a helper so the loop body stays at depth <= 2. Effort: small for `_sync_extract`,
medium for the retry loop; priority: recommended.

---

### STR-004: Six functions nest control flow to depth 4

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py:267` (`_run_batch_with_progress`); `src/vkdownloader/infrastructure/network_monitor.py:53` (`_intercept_response`); `src/vkdownloader/infrastructure/network_monitor.py:123` (`_extract_urls_from_json`); `src/vkdownloader/services/downloader.py:635` (`_attempt_segment_resume`); `src/vkdownloader/services/downloader.py:393` (`download_with_ffmpeg`); `src/vkdownloader/services/ffmpeg_utils.py:94` (`read_progress`) |
| **Classification** | advisory |

**Description:** Six functions breach the depth-3 ceiling at depth 4. Several are the same
dispatch/error sites flagged in STR-001 (rank-C CC is correlated with deep nesting).
`read_progress` (ffmpeg_utils.py:94) reaches depth 4 via `while` -> `if parsed:` -> `elif progress`
-> `if value == "end"`; `_extract_urls_from_json` via `if dict:` -> `for value` -> `if str...m3u8:`
-> `if not in list`.

**Evidence:** AST nesting-depth scan:
```
cli.py:267            _run_batch_with_progress     depth 4
network_monitor.py:53 _intercept_response         depth 4
network_monitor.py:123 _extract_urls_from_json    depth 4
downloader.py:635     _attempt_segment_resume     depth 4
downloader.py:393     download_with_ffmpeg        depth 4
ffmpeg_utils.py:94    read_progress               depth 4
```

**Recommendation:** Push the deepest condition out with a Guard Clause (e.g. early-exit in the
JSON walker) and Extract Method the deeply nested block. The shutdown/cancel handling that recurs
across the depth-4 download functions is a consolidation candidate (see STR-008). Effort: small
per function; priority: recommended.

---

### STR-005: Sixteen functions exceed the 50-line length guideline (four exceed 100)

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (7); `src/vkdownloader/cli.py` (4); `src/vkdownloader/services/segment_downloader.py` (2); `src/vkdownloader/services/downloader_throttle.py` (1); `src/vkdownloader/infrastructure/network_monitor.py` (1); `src/vkdownloader/services/extractor.py` (1) |
| **Classification** | advisory |

**Description:** Sixteen functions exceed 50 SLOC (the phase guideline), 4 of them exceed 100
SLOC — the HIGH band. The four >100-SLOC functions are exactly the worst offenders in STR-001:

| Function | File | SLOC | CC |
|----------|------|------|----|
| `perform_download` | downloader.py:966 | 152 | 15 |
| `_download_with_ytdlp` | downloader.py:747 | 142 | 17 |
| `download_with_ffmpeg` | downloader.py:393 | 122 | 12 |
| `download` | cli.py:419 | 104 | 11 |

The remaining twelve (55-99 SLOC): `_run_batch_with_progress` (86), `_retry_429_with_backoff` (79),
`download_with_ytdlp_with_resume_fallback` (77), `_run_download_session` (72), `_download_single`
(71), `download_video` (66), `_attempt_segment_resume` (99), `batch_download` (91),
`_build_ytdlp_cli_command` (65), `download_hls_with_resume` (62), `_intercept_response` (59),
`_extract_with_ytdlp` (55).

Note: `cli.py` `download` / `batch_download` are Typer command handlers; a substantial fraction of
their SLOC is `typer.Option(...)` declarations rather than logic, so CC (11/12) is the stronger
signal for those two than raw length.

**Evidence:** AST SLOC scan (non-blank, non-comment lines per function body):
```
perform_download                          152
_download_with_ytdlp                      142
download_with_ffmpeg                      122
download                                  104
_attempt_segment_resume                   99
batch_download                            91
_run_batch_with_progress                  86
_retry_429_with_backoff                   79
download_with_ytdlp_with_resume_fallback  77
_run_download_session                     72
_download_single                          71
download_video                            66
_build_ytdlp_cli_command                  65
download_hls_with_resume                  62
_intercept_response                       59
_extract_with_ytdlp                       55
```

**Recommendation:** Extract Method each function into cohesive sub-operations (validation, setup,
dispatch, teardown). The >100-SLOC functions live in the god-modules of STR-002 and are best
addressed by that split. Effort: large; priority: recommended.

---

### STR-006: Nineteen internal functions take more than five parameters (recurring orchestration quintet)

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`; `src/vkdownloader/services/segment_downloader.py`; `src/vkdownloader/services/downloader_throttle.py`; `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** Nineteen internal functions exceed the 5-parameter guideline (the two Typer
command handlers `cli.download` / `cli.batch_download` are excluded: their parameters are
`typer.Option`/`typer.Argument` declarations, not call-site arguments). The dominant pattern is a
recurring quintet threaded through every download helper: `extractor`, `settings`,
`backoff_coordinator`, `semaphore`, `progress_callback` — the same five are passed (often
positionally or as keyword args) across `perform_download` -> `download_with_ytdlp_with_resume_fallback`
-> `_download_with_ytdlp` -> `download_hls_with_resume` -> `_run_download_session` ->
`_run_parallel_download_with_backoff`. Leaders:

| Function | File:Line | Params |
|----------|-----------|--------|
| `perform_download` | downloader.py:966 | 11 |
| `download_with_ytdlp_with_resume_fallback` | downloader.py:542 | 11 |
| `download_video` | downloader.py:1142 | 11 |
| `_attempt_segment_resume` | downloader.py:635 | 10 |
| `_run_download_session` | segment_downloader.py:738 | 10 |
| `_download_segment` | segment_downloader.py:342 | 10 |
| `_run_parallel_download_with_backoff` | segment_downloader.py:197 | 9 |
| `_try_single_download_attempt` | segment_downloader.py:255 | 9 |
| `_download_segment_parallel` | segment_downloader.py:288 | 8 |

(the remaining ten sit at 6-7 params, e.g. `_download_single` 7, `_download_with_ytdlp` 7,
`_tally_and_merge` 7, `_retry_429_with_backoff` 6, `download_with_ffmpeg` 6).

More than five parameters signals a function doing too much and creates fragile call sites
(the codebase already relies heavily on keyword args to keep these calls readable).

**Evidence:** AST parameter scan over `src/vkdownloader` (19 functions; Typer command handlers
excluded).

**Recommendation:** Bundle the repeated cross-cutting dependencies into the existing
`DownloadContext` (`cli.py:120`) or a dedicated `DownloadDependencies` dataclass, and pass it
plus the URL/quality-specific arguments. This collapses the 8-11-param signatures to 2-3.
Effort: medium; priority: recommended.

---

### STR-007: Ten functions use more than three return statements

| Field | Value |
|-------|-------|
| **ID** | STR-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py:149`; `src/vkdownloader/cli.py:181`; `src/vkdownloader/services/downloader.py:966,542,747`; `src/vkdownloader/services/segment_downloader.py:288,197,469`; `src/vkdownloader/services/downloader_throttle.py:241`; `src/vkdownloader/infrastructure/network_monitor.py:41` |
| **Classification** | advisory |

**Description:** Ten functions exceed the 3-return guideline:

| Function | File:Line | Returns |
|----------|-----------|---------|
| `_retry_429_with_backoff` | downloader_throttle.py:149 | 7 |
| `_download_single` | cli.py:181 | 6 |
| `perform_download` | downloader.py:966 | 5 |
| `download_with_ytdlp_with_resume_fallback` | downloader.py:542 | 5 |
| `_download_segment_parallel` | segment_downloader.py:288 | 5 |
| `_download_with_ytdlp` | downloader.py:747 | 4 |
| `_run_parallel_download_with_backoff` | segment_downloader.py:197 | 4 |
| `_fetch_playlist_with_retry` | segment_downloader.py:469 | 4 |
| `_parse_retry_after` | downloader_throttle.py:241 | 4 |
| `_normalize_url` | network_monitor.py:41 | 4 |

`_retry_429_with_backoff` is the worst: depth-5 nesting (STR-003) *and* 7 returns, each returning
`None` or `content` at different exit points, making the success/failure contract hard to follow.

**Evidence:** AST return-statement scan; cross-referenced with the nesting analysis (STR-003).

**Recommendation:** Collapse to a Single-Exit structure: assign to a `result` variable, use early
`continue`/`break` for retry-loop exits, and return once at the end. This lowers cognitive load
without changing behavior. Effort: small; priority: recommended.

---

### STR-008: Duplicated readline-and-cancel stream loops across download strategies

| Field | Value |
|-------|-------|
| **ID** | STR-008 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`:817-857; `download_with_ffmpeg`:454-486) |
| **Classification** | advisory |

**Description:** The two download strategies each define a near-identical pair of nested closures
that read an asyncio `StreamReader` line-by-line, echo the line, append to a chunk list, and
cancel the subprocess on shutdown:

- `_download_with_ytdlp`: `_monitor_progress` (downloader.py:817) and `_drain_output` (840) —
  same readline loop, same `shutdown_event` check, same `cancel_subprocess` + warning call.
- `download_with_ffmpeg`: `_monitor_progress` (downloader.py:454) and `_drain_stderr` (471) —
  same shape on `process.stderr`.

The two pairs differ only in whether a per-line parser/callback is invoked and whether stdout or
stderr is read. Keeping the cancellation/shutdown logic in four copies is a correctness hazard: a
fix to one shutdown path is unlikely to be mirrored to the other three.

**Evidence:** `src/vkdownloader/services/downloader.py`:
```python
# downloader.py:817-857 (inside _download_with_ytdlp)
async def _monitor_progress() -> None:
    ...
    while True:
        if shutdown_event.is_set():
            if not await cancel_subprocess(process):
                logger.warning("yt_dlp_cancel_not_clean", ...)
            break
        line = await process.stdout.readline()
        if not line:
            break
        decoded = line.decode(errors="replace")
        _echo_ytdlp_line(decoded)
        output_chunks.append(line)
        progress = _parse_ytdlp_progress(decoded)
        ...
async def _drain_output() -> None:
    ...  # same loop, no callback, on process.stdout
```
(and the structurally identical `_monitor_progress`/`_drain_stderr` pair on `process.stderr` at
downloader.py:454-486).

**Recommendation:** Extract a single
`read_stream_with_shutdown(reader, on_line, on_shutdown_canceled)` async helper that performs the
readline + shutdown-check + cancel + on_line callback, and have both strategies pass their
differing `on_line` (parse progress vs. no-op). Effort: medium; priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 (STR-001, STR-002, STR-003) |
| MEDIUM | 4 (STR-004, STR-005, STR-006, STR-008) |
| LOW | 1 (STR-007) |
| **Total** | **8** |

## Mandatory Fixes

_No findings are classified as mandatory._ This pass targets structural quality (complexity,
nesting, length, control flow); no security, data-loss, or correctness defects were introduced or
exposed during measurement. All eight findings are advisory.

## Advisory Recommendations

- **STR-001 (HIGH):** Reduce cyclomatic complexity on the 10 rank-C functions via Extract Method
  and a lookup table for exception mapping; add a CI complexity gate. [Cyclomatic Complexity]
- **STR-002 (HIGH):** Split the `downloader.py` (798 SLOC) and `segment_downloader.py` (571 SLOC)
  god-modules by responsibility so each file stays under 300 SLOC. [File Length / Function Length]
- **STR-003 (HIGH):** Flatten depth-5 nesting in `_retry_429_with_backoff` and `_sync_extract` with
  guard clauses and by extracting the `Stream` mapping helper. [Nesting Depth]
- **STR-004 (MEDIUM):** Reduce six depth-4 functions to depth <= 3 via guard clauses / extraction.
  [Nesting Depth]
- **STR-005 (MEDIUM):** Break the 16 functions over 50 SLOC into cohesive sub-operations; the four
  >100-SLOC ones ride on the STR-002 module split. [Function Length]
- **STR-006 (MEDIUM):** Collapse the recurring `extractor/settings/backoff_coordinator/`
  `semaphore/progress_callback` quintet into a `DownloadDependencies` object (or reuse the existing
  `DownloadContext`). [Control Flow Patterns -- parameters]
- **STR-008 (MEDIUM):** De-duplicate the four monitor/drain readline closures into a single
  `read_stream_with_shutdown` helper. [Cognitive Load]
- **STR-007 (LOW):** Consolidate the 10 multi-return functions to single-exit where it aids
  readability (`_retry_429_with_backoff` is the priority). [Control Flow Patterns -- returns]

## Doc Updates Needed

_None. The structural-quality findings above are code-shape issues in `src/`; no authoring, API, or
configuration documentation deviates from the implementation in a way this phase covers. (Prior-phase
doc gaps remain tracked under their original finding IDs.)
