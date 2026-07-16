---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 09 Audit Findings — Structural Code Quality

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/09-structural-quality.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Evidence

### Step R1 — Radon Cyclomatic Complexity (`uv run radon cc src/ -a`)
- **Average complexity: A (3.42)** — within the ≤5 target. ✅
- **No function at rank D or worse (≥21).** ✅
- **2 functions at rank C (CC = 11)**, both in `src/vkdownloader/services/segment_downloader.py`:
  - `F 366:0 _process_downloaded_segments - C (11)`
  - `F 430:0 _download_segment_concurrent - C (11)`
- All other functions across the project are rank A or B (≤10).

### Step R2 — Radon Maintainability Index (`uv run radon mi src/ -s`)
- **Every file ranks A.** Lowest scores: `segment_downloader.py` (44.79), `downloader.py` (46.84), `models/video.py` (52.25). No file at rank B or C. ✅

### Step R3 — Function Length
- No single function exceeds 50 non-blank lines. ✅
- Function lengths: `_process_downloaded_segments` ≈44 real lines (366–427), `_download_segment_concurrent` ≈55 real lines (430–501), `_fetch_playlist_with_retry` ≈32 real lines.

### Step R4 — Nesting Depth (measured via indentation scan, 4-space units)
- `_fetch_playlist_with_retry` (303–343): **max depth = 7** (`def` → `for` → `try` → `async with` → `if` → `if` → `if` → `if`).
- `_process_downloaded_segments` (366–427): **max depth = 4**.
- `_download_segment_concurrent` (430–501): **max depth = 4**.
- `_run_download_session` (556–626): max depth = 3.
- `_download_with_ytdlp` (416–500): max depth = 4.
- Threshold violated (>3): `_fetch_playlist_with_retry` (7), `_process_downloaded_segments` (4), `_download_segment_concurrent` (4), `_download_with_ytdlp` (4).

### Step R5 — Control Flow Pattern Search
- **No `for...else` anti-pattern** found anywhere in `src/`. ✅
- Excessive return points (>3): only `_process_downloaded_segments` (4 returns) — borderline.
- Excessive parameters (>5): systemic — see STR-004.
- Arrow code: confirmed in `_fetch_playlist_with_retry` and `_download_segment_concurrent`.

---

## Findings

### STR-001: `_fetch_playlist_with_retry` has nesting depth 7 (pyramid of doom)

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** The function `_fetch_playlist_with_retry` (lines 303–343) reaches a control-flow nesting depth of **7 levels**: `def → for → try → async with → if → if → if → if`. Although its cyclomatic complexity is only B (10), the structural depth violates the ≤3 guideline by more than double. The deepest branch (lines 323–331) is a classic arrow pattern: `if cookie_source == BROWSER → if streams → continue`, with an `else` at the same depth (332–339). This makes the token-refresh recovery path hard to follow and easy to break when edited.

**Evidence:**
```
320:  if response.status in (403, 410) and extractor:
321:      logger.info("token_expired_fetching_new", attempt=attempt + 1)
323:          if settings.cookie_source == CookieSource.BROWSER:   # depth 5
328:              if streams:                                       # depth 6
329:                  current_url = str(streams[0].url)             # depth 7
330:                  headers["Cookie"] = new_cookies or ""
331:                  continue
332:          else:                                                # depth 5
...
```

**Recommendation:** Extract the 403/410 token-refresh branch into a helper coroutine, e.g. `_refresh_token_and_retry(session, extractor, video_url, settings, headers) -> str | None`, and replace the inner pyramid with an early-`return` guard clause. This flattens depth to ≤3 and isolates the recovery logic so it can be unit-tested without constructing a full retry loop. Effort: small. Priority: recommended.

---

### STR-002: Two functions exceed cyclomatic complexity rank C (CC = 11)

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_process_downloaded_segments` (line 366) and `_download_segment_concurrent` (line 430) both have CC = 11 (rank C), exceeding the ≤10 (rank B) target. Neither is critical (no rank D), but both are the most complex units in the project and the natural first candidates for decomposition.

- `_process_downloaded_segments` mixes three responsibilities: awaiting/cancelling tasks, updating progress metadata, and deciding whether to merge. It has 4 return points.
- `_download_segment_concurrent` mixes rate-limit gating (semaphore + shutdown checks), URL resolution, segment-existence short-circuit, download dispatch, and anti-detection delay logic within one body.

**Evidence:** `uv run radon cc src/vkdownloader/services/segment_downloader.py -s`:
```
F 366:0 _process_downloaded_segments - C
F 430:0 _download_segment_concurrent - C
```

**Recommendation:** For `_process_downloaded_segments`, split into `_await_download_tasks(tasks)` (cancellation handling) + `_update_progress(...)` + the merge decision (already near top-level). For `_download_segment_concurrent`, extract `_maybe_apply_anti_detection_delay(shutdown_event, max_concurrent_downloads, is_shared_semaphore)` and `_resolve_segment_path(...)`. This brings both to rank B. Effort: small–medium. Priority: recommended.

---

### STR-003: God-module-sized service files exceed 300 lines

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** Three service modules exceed the 300-line file threshold (project rule #15: "Small Modules and Functions"), making them harder to navigate and review:

| File | Raw lines | Non-blank/non-comment lines |
|------|-----------|------------------------------|
| `services/segment_downloader.py` | 697 | 584 |
| `services/downloader.py` | 653 | 550 |
| `services/downloader_throttle.py` | 330 | 251 |

`segment_downloader.py` is the largest and mixes pure helpers (`_parse_m3u8_segments`, `_load/_save_downloaded_count`), retry primitives, backoff plumbing, and orchestration (`_run_download_session`, `download_hls_with_resume`) in one file. This contradicts the single-responsibility and small-module guidance in the project rules.

**Evidence:** Line-count scan of `src/vkdownloader` (non-blank/non-comment): `downloader.py` 550, `segment_downloader.py` 584, `downloader_throttle.py` 251. Raw `Get-Content` counts: 653 / 697 / 330.

**Recommendation:** Split `segment_downloader.py` into cohesive modules, e.g. `segment_io.py` (metadata load/save, cleanup, playlist parse), `segment_retry.py` (sequential/parallel/backoff download primitives), and keep `segment_downloader.py` for orchestration (`_run_download_session`, `download_hls_with_resume`). Similarly consider extracting the ffmpeg-orchestration glue in `downloader.py` or trimming its re-export `__all__` block (lines 80–102) which documents 22 symbols. Effort: medium. Priority: recommended.

---

### STR-004: Systemic excessive function parameters (>5) — pass-through parameter lists

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (primary), `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** Nine functions exceed the 5-parameter guideline, with several carrying 8–12 parameters. These are almost entirely the same contextual values (`session, headers, backoff_coordinator, video_url, max_retries, ...`) threaded through every layer — a "parameter soup" that signals missing cohesion objects.

| Function | Param count |
|----------|-------------|
| `_download_segment_concurrent` | 12 |
| `_run_download_session` | 11 |
| `_create_segment_download_tasks` | 11 |
| `_run_parallel_download_with_backoff` | 8 |
| `_try_single_download_attempt` | 8 |
| `_download_segment` | 8 |
| `_process_downloaded_segments` | 7 |
| `_fetch_playlist_with_retry` | 7 |
| `_download_segment_parallel` | 6 |

Each additional parameter multiplies call-site noise, raises the chance of argument-order mistakes at call sites (e.g. lines 535–553, 665–682), and makes the functions hard to reuse or test in isolation (a unit test must supply all 11–12 args).

**Evidence:** Signatures at `segment_downloader.py` lines 430–442 (`_download_segment_concurrent` 12 params), 504–515 (`_create_segment_download_tasks` 11 params), 556–567 (`_run_download_session` 11 params), 232–242 (`_download_segment` 8 params).

**Recommendation:** Introduce a small context dataclass (e.g. `SegmentDownloadContext` / `DownloadSession`) bundling `session, headers, backoff_coordinator, video_url, max_retries, max_concurrent_downloads`, and pass it instead of the flat list. This collapses most signatures to 2–3 params, eliminates order-dependence, and is a natural follow-on to the STR-003 split. Effort: medium. Priority: recommended.

---

### STR-005: `_download_segment_concurrent` mixes anti-detection delay inside download path

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** Within `_download_segment_concurrent` (lines 490–499), anti-detection logic is embedded directly in the download path: a randomized `1.5 + uniform(0,0.5)` delay is implemented via `asyncio.wait_for(shutdown_event.wait(), timeout=delay)` and converted into a `CancelledError` when the timeout fires. This is a control-flow twist (a timeout used as a sleep, errors raised to signal success-path continuation) that is cognitively load-bearing and not obvious to a reader. It also contributes to the function's depth-4 nesting and CC=11.

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

**Recommendation:** Extract `_apply_anti_detection_delay(shutdown_event, is_shared_semaphore, max_concurrent_downloads)` that returns early when not applicable and uses `await asyncio.sleep(delay)` (still cancellable via the shutdown event) instead of repurposing `wait_for` + `CancelledError`. This removes the misleading error-as-control-flow pattern and reduces cognitive load. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 4 |
| LOW | 1 |

## Mandatory Fixes

None. All findings are advisory (structural quality / maintainability). No security, data-loss, or correctness defects were identified in this phase.

## Advisory Recommendations

- **STR-001** — Flatten `_fetch_playlist_with_retry` arrow code (depth 7) via guard-clause extraction.
- **STR-002** — Decompose the two rank-C functions (`_process_downloaded_segments`, `_download_segment_concurrent`) to reach rank B.
- **STR-003** — Split the three oversized service modules (>300 lines) per single-responsibility / small-module rules.
- **STR-004** — Replace 8–12 parameter pass-through lists with a context dataclass.
- **STR-005** — Extract anti-detection delay and stop using `CancelledError` as success-path control flow.

## Doc Updates Needed

None required. The project rules already state the 300-line / single-responsibility / small-function guidance that these findings reinforce; no documentation divergence was found.
