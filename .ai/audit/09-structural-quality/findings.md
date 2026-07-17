# Phase 09 Audit Findings — Structural Code Quality

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### STR-001: `HLSDownloader.download_with_ffmpeg` exceeds max nesting depth (5) and length (135 lines)

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (lines 168–303) |
| **Classification** | advisory |

**Description:** `download_with_ffmpeg` is the single most structurally problematic function in the codebase. It is 135 lines long (limit 50) and reaches a **maximum nesting depth of 5**, far above the 3-level guideline. The depth is driven by `async with` → `try` → `if progress_callback:` → `for task in pending:` → `try/except CancelledError`. Cyclomatic complexity is rank **C (≥11)** per radon. The function also contains two near-identical branches (`if progress_callback:` / `else:`) that duplicate the same `asyncio.wait([...])` + "cancel pending tasks" loop verbatim (lines 250–283), violating DRY and inflating both CC and length.

**Evidence:**
```
radon cc src/vkdownloader/services/downloader.py:
    M 168:4 HLSDownloader.download_with_ffmpeg - C
radon mi: services/downloader.py - A (44.34)  # low MI score is the 2nd-lowest in project

AST scan (this audit):
    services/downloader.py:168 download_with_ffmpeg | lines=135 | max_nesting=5 | params=6

Duplicated cancel-pending block:
  L250-266 (progress_callback branch) and L268-284 (else branch):
      done, pending = await asyncio.wait([...], return_when=asyncio.FIRST_COMPLETED)
      for task in pending:
          task.cancel()
          try:
              await task
          except asyncio.CancelledError:
              pass
```

**Recommendation:** Extract the shared "launch two coroutines, await FIRST_COMPLETED, cancel the loser" pattern into a single helper (e.g. `_await_first_and_cancel_others(process_task, reader_task)`), removing the duplicated branch. This collapses both branches into one, cuts nesting by a level, and drops CC. The two inner closures `_monitor_progress` / `_drain_stderr` are already extracted — keep them but call the shared await helper from both paths. Effort: small. Priority: recommended (HIGH maintenance cost today: hard to test the ffmpeg-cancellation path in isolation, and any fix to cancellation must be applied in two places).

---

### STR-002: `cli.py` is a god module (398 lines) and duplicates single-download logic

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (398 lines total) |
| **Classification** | advisory |

**Description:** `cli.py` is 398 lines, exceeding the 300-line file-size guideline. More importantly, the `_download()` nested closure inside the `download` Typer command (lines ~330–385) **re-implements the entire single-video download flow that already exists in `_download_single()`** (cli.py:64–161): extract streams → select quality → resolve output path → `validate_output_path` → `_sanitize_title` → build filename → `perform_download`. This is structural duplication that will drift: a change to output-path/filename logic must be made in two places.

**Evidence:**
```
Line counts: cli.py = 398 lines (radon/Measure-Object)
_download_single (cli.py:64)  : 93 lines, 10 params, CC=C
Nested _download() closure     : ~55 lines, duplicates the same 8-step flow
```

**Recommendation:** Have the single `download` command reuse `_download_single()` (or extract the shared 8-step flow into a private `_resolve_and_download(...)` helper called by both), rather than re-declaring the logic as an inline closure. This removes ~50 lines of duplication and keeps filename/path resolution in one place. Effort: small. Priority: recommended.

---

### STR-003: `_download_single` has excessive parameters (10) and length (93 lines)

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 64–156) |
| **Classification** | advisory |

**Description:** `_download_single` takes **10 parameters** (url, index, quality, output, method, settings, max_retries_override, shared_semaphore, backoff_coordinator, progress_callback) — double the 5-parameter limit. Several are batch-only concerns (index, shared_semaphore, backoff_coordinator). The function is 93 lines with CC rank C (≥11). High parameter count signals the function is doing batch orchestration + single download in one place.

**Evidence:**
```
radon cc:   F 64:0 _download_single - C
AST scan:   cli.py:64 _download_single | lines=93 | max_nesting=2 | params=10
```

**Recommendation:** Introduce a small dataclass (e.g. `DownloadContext`) bundling the batch-scoped fields (semaphore, backoff_coordinator, progress_callback, max_retries_override). This reduces the signature to ~6 params and makes the single-download path clearer. The broad `except Exception: raise` + 5 typed `except` branches are acceptable (clear error mapping) but contribute to CC — consider a `_classify_download_error(exc)` helper returning the status tuple. Effort: small. Priority: recommended.

---

### STR-004: `_download_segment_concurrent` has excessive parameters (13)

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (lines 514–590) |
| **Classification** | advisory |

**Description:** `_download_segment_concurrent` takes **13 parameters** (over 2.5× the 5-param limit) and is 77 lines (CC rank C). The parameter list bundles unrelated concerns: HTTP plumbing (session, segment_url, headers, m3u8_url, download_timeout), rate-limiting (semaphore, backoff_coordinator, is_shared_semaphore, max_concurrent_downloads), and identity (idx, segments_dir, video_url, max_retries). This makes call sites (e.g. `_create_segment_download_tasks`, lines 593–647) verbose and error-prone — that caller itself takes 12 params.

**Evidence:**
```
radon cc:   F 514:0 _download_segment_concurrent - C
AST scan:   segment_downloader.py:514 _download_segment_concurrent | lines=77 | max_nesting=3 | params=13
            segment_downloader.py:593 _create_segment_download_tasks | lines=55 | max_nesting=0 | params=12
```

**Recommendation:** Group the 13 params into two or three cohesive objects — e.g. a `SegmentTask` (idx, segment_url, segments_dir, m3u8_url) and a `DownloadPolicy` (max_concurrent_downloads, max_retries, download_timeout, backoff_coordinator, is_shared_semaphore). The `session`/`headers`/`semaphore` are shared session state and can be captured on the class or passed once. This also shrinks `_create_segment_download_tasks` (12 params) in lockstep. Effort: medium. Priority: recommended.

---

### STR-005: Project average cyclomatic complexity is 11.5 (target ≤ 5)

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | whole `src/vkdownloader/` (4 functions at CC rank C) |
| **Classification** | advisory |

**Description:** Radon reports an **average cyclomatic complexity of C (11.5)** across the 4 analyzed functions, well above the ≤5 target and above the ≤10 threshold. Four functions are individually at rank C (≥11): `_download_single`, `download_with_ffmpeg`, `_process_downloaded_segments`, `_download_segment_concurrent`. No function reaches rank D (≥21), so there is no CRITICAL bug-prone code, but the aggregate complexity indicates the download/segments path is branch-heavy (many `if shutdown_event.is_set()` guards, broad except chains, parallel/sequential mode switches).

**Evidence:**
```
radon cc src/vkdownloader -a -nc:
    F 64:0  _download_single - C
    M 168:4 HLSDownloader.download_with_ffmpeg - C
    F 456:0 _process_downloaded_segments - C
    F 514:0 _download_segment_concurrent - C
    4 blocks analyzed. Average complexity: C (11.5)
```

**Recommendation:** Treat the average as a trend metric, not a gate. The highest-leverage reductions are STR-001 (extract duplicated ffmpeg await/cancel logic), STR-003/STR-004 (parameter bundling reduces CC by collapsing mode switches), and replacing repeated inline `if shutdown_event.is_set(): raise CancelledError(...)` guards with a single `_raise_if_shutdown(event)` helper used across segment_downloader. Effort: medium (spread across the above). Priority: recommended.

---

### STR-006: `_download_with_ytdlp` exceeds 50-line limit (114 lines); `_process_downloaded_segments` (56) just over

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (lines 478–591); `src/vkdownloader/services/segment_downloader.py` (lines 456–511) |
| **Classification** | advisory |

**Description:** Two additional functions exceed the 50-line guideline (though their CC is below rank C, so they are not in the radon C-list): `_download_with_ytdlp` is 114 lines (7 params, nesting 3) — it nests a large synchronous `_download()` closure containing the full yt-dlp option dict + progress-hook + download call; `_process_downloaded_segments` is 56 lines (7 params). Neither is bug-prone, but both read as "do several things" blocks.

**Evidence:**
```
AST scan:
    services/downloader.py:478 _download_with_ytdlp | lines=114 | max_nesting=3 | params=7
    services/segment_downloader.py:456 _process_downloaded_segments | lines=56 | max_nesting=3 | params=7
```

**Recommendation:** Extract the yt-dlp `ydl_opts` dict construction into a `_build_ytdlp_options(output_file, settings, quality_str, cookies, progress_callback)` helper to shrink `_download_with_ytdlp` below 50 lines and isolate the option-building responsibility. For `_process_downloaded_segments`, split the "await + cancellation" handling from the "tally + merge" step. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 1 |

## Mandatory Fixes

None. All findings are structural-quality improvements (advisory). No security, data-loss, or correctness defects were identified in this phase.

## Advisory Recommendations

- **STR-001** (HIGH): Refactor `download_with_ffmpeg` — remove duplicated cancel-pending branch, reduce nesting from 5 to ≤3.
- **STR-002** (MEDIUM): Split `cli.py` god module; eliminate duplicate single-download flow in the `download` command closure.
- **STR-003** (MEDIUM): Bundle `_download_single` batch params into a context object (10 → ~6 params).
- **STR-004** (MEDIUM): Bundle `_download_segment_concurrent` params into `SegmentTask`/`DownloadPolicy` (13 → ~3 objects); also fixes the 12-param caller.
- **STR-005** (MEDIUM): Track average CC (11.5) as a trend; address via STR-001/003/004 + a shared `_raise_if_shutdown` helper.
- **STR-006** (LOW): Extract yt-dlp option builder; split `_process_downloaded_segments`.

## Doc Updates Needed

None. No documentation claims were found that contradict the observed structure (no AGENTS.md present; no function-length/complexity policy documented in `docs/`). If a coding-standards doc is added later, it should capture the 50-line / 5-param / depth-3 / CC≤10 targets enforced by this audit.

---

### Runtime Verification Evidence

```
# R1 — Cyclomatic complexity (radon cc src/vkdownloader -a -nc)
4 blocks analyzed. Average complexity: C (11.5)
  cli.py:64 _download_single - C
  services/downloader.py:168 HLSDownloader.download_with_ffmpeg - C
  services/segment_downloader.py:456 _process_downloaded_segments - C
  services/segment_downloader.py:514 _download_segment_concurrent - C

# R2 — Maintainability index (radon mi src/vkdownloader -s)
All 22 source files rank A. Lowest scores:
  services/segment_downloader.py - A (42.74)
  services/downloader.py        - A (44.34)
  cli.py                        - A (56.25)

# R3 — Function length (>50 lines): _download_single(93), download_with_ffmpeg(135),
#      _process_downloaded_segments(56), _download_segment_concurrent(77),
#      _download_with_ytdlp(114), download_with_ytdlp_with_resume_fallback(80)
#      File >300 lines: cli.py (398)

# R4 — Nesting depth: download_with_ffmpeg=5 (max); others 2-3

# R5 — Control flow: NO for...else found (AST scan). No function exceeds 3 return points
#      in the flagged set. Excessive params: _download_single(10),
#      download_with_ytdlp_with_resume_fallback(11), _download_segment_concurrent(13),
#      _create_segment_download_tasks(12).
```
