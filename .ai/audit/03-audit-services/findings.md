# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/03-audit-services.md
**Status:** complete
**Validated:** no

> problems-only mode: only real problems are documented. Dimensions with no findings are omitted.

---

## Runtime Verification

- **R1 (Import):** `uv run python -c "import ..."` for all 8 service modules + 3 model modules → `IMPORTS OK`. No import errors.
- **R2 (Lint/Type):** `uv run ruff check src/vkdownloader/services src/vkdownloader/models` → All checks passed. `uv run mypy ...` → Success, no issues found (13 files).
- **R3 (Tests):** `uv run pytest tests -q` → 217 passed.
- **R4 (Dead code):** Static scan of `src/vkdownloader` identified two never-referenced symbols (see SRV-001, SRV-002). All other service helpers are referenced.

---

## Findings

### SRV-001: `SegmentRetryResult` enum is dead code

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/enums.py` |
| **Classification** | advisory |

**Description:** `SegmentRetryResult` (enums.py:53-58) is a `StrEnum` defining `SUCCESS`, `PERMANENT_FAILURE`, `RETRY_EXHAUSTED`. It is neither imported nor referenced anywhere in `src/` or `tests/`. The segment downloader reports failure as a bare `None` (see `download_hls_with_resume` / `_run_download_session`), so this differentiated failure taxonomy is unused.

**Evidence:**
```
src/vkdownloader/models/enums.py:53
class SegmentRetryResult(StrEnum):
    SUCCESS = "success"
    PERMANENT_FAILURE = "permanent_failure"
    RETRY_EXHAUSTED = "retry_exhausted"
```
Grep for `SegmentRetryResult` across `src/` returns only the definition (0 usages).

**Recommendation:** Investigate intent (the docstring says "for differentiated failure modes"). Either wire it into `_run_download_session`/`download_hls_with_resume` return path so callers can distinguish permanent vs retry-exhausted failures, or remove it. Per dead-code policy, do not delete blindly — confirm whether it is planned future-proofing before removal. Effort: trivial. Priority: recommended.

---

### SRV-002: `ProgressManager.get_progress` is never called

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `ProgressManager.get_progress(self, url_index)` (downloader_throttle.py:143-153) is a public async method that duplicates the read done by `get_formatted_progress` but for a single index. It is never referenced anywhere. Only `update_sync`, `get_formatted_progress`, and `clear` are used (by `cli.py`).

**Evidence:**
```
downloader_throttle.py:143
async def get_progress(self, url_index: int) -> tuple[int, int]:
    async with self._lock:
        return self._state.get(url_index, (0, 0))
```
Grep for `get_progress` across `src/` returns only the definition.

**Recommendation:** Remove the method to reduce surface area, or replace the internal read in `_create_progress_callback`/batch summary if single-index reads are genuinely needed. Effort: trivial. Priority: recommended.

---

### SRV-003: Segment resume double-counts progress and can never complete a resumed run

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `download_hls_with_resume` advertises segment-level resume ("can resume after interruption by re-downloading missing segments"). However, the resume path has two compounding defects that make a resumed run fail to produce output:

1. `_run_download_session` (segment_downloader.py:726-751) loads `downloaded_count = _load_downloaded_count(metadata_file)` (line 727) but never uses it to skip already-downloaded segments. It creates tasks for **all** segments from index 0 (line 751, `_create_segment_download_tasks`), overwriting existing `.ts` files.
2. `_tally_and_merge` (segment_downloader.py:540) computes `downloaded_count = _load_downloaded_count(metadata_file) + sum(1 for r in download_results if r)`. Because every segment is re-downloaded and succeeds, the persisted count is **added to itself**: resumed count = old_count + total_segments. The completion check `if downloaded_count == len(segments)` (line 549) then compares e.g. `150 == 100`, which is always false, so the merge branch is never taken and the function returns `None`.

**Consequence:** After an interrupted run (the intended resume scenario), re-invoking the download re-downloads all segments successfully but never merges them — the user gets no output file and the run is reported as failed, defeating the core resume feature. The `downloaded_count` persisted in `.<stem>_progress.json` also grows unbounded across invocations.

**Evidence:**
```python
# segment_downloader.py:540 (_tally_and_merge)
downloaded_count = _load_downloaded_count(metadata_file) + sum(1 for r in download_results if r)
_save_downloaded_count(metadata_file, downloaded_count)
...
# segment_downloader.py:549
if downloaded_count == len(segments):
    result = await _merge_segments_batched(...)
```
```python
# segment_downloader.py:726-751 (_run_download_session) — no skip of already-downloaded segments
segments = _parse_m3u8_segments(playlist_content)
downloaded_count = _load_downloaded_count(metadata_file)   # loaded but unused for skipping
...
tasks = _create_segment_download_tasks(segments, policy)    # ALL segments, index 0..N
```

**Recommendation:** Make resume real: (a) skip segments whose file already exists (or track per-segment completion in metadata instead of a single counter), and (b) replace the additive counter with the true count of existing+newly-downloaded segments, and only persist the final count when `downloaded_count == len(segments)`. The `downloaded_count` value logged as `resume_from` should drive the skip set. Effort: medium. Priority: mandatory (correctness / data-loss-of-progress).

---

### SRV-004: Dead conditional guard in `_attempt_segment_resume`

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** In `download_with_ytdlp_with_resume_fallback`, the `while retry_count <= MAX_RESUME_RETRIES:` loop (downloader.py:400) guarantees `retry_count <= MAX_RESUME_RETRIES` on every iteration. Inside `_attempt_segment_resume`, the line `if retry_count <= MAX_RESUME_RETRIES:` (downloader.py:418) is therefore always true and the branch is unconditional. This is dead/confusing control flow that implies a guard that does not exist.

**Evidence:**
```python
# downloader.py:418 (inside _attempt_segment_resume, called only from the retry loop)
if retry_count <= MAX_RESUME_RETRIES:
    if (
        segment_result := await _attempt_segment_resume(...)
    ) is not None:
        return segment_result
```

**Recommendation:** Remove the redundant `if retry_count <= MAX_RESUME_RETRIES:` wrapper; the body is already gated by the caller loop. Effort: trivial. Priority: recommended.

---

### SRV-005: BROWSER cookie-source rejects all specific qualities (only `best` works)

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/quality.py` |
| **Classification** | mandatory |

**Description:** When `cookie_source == BROWSER`, `perform_download` calls `_resolve_cookies` (downloader.py:631), which re-extracts streams via `extractor.extract_streams_with_cookies(..., force_browser=True)` and re-selects with `QualitySelector.select(browser_streams, quality_enum)`. But the browser path (`extractor._extract_with_browser`, extractor.py:222-230) captures a **single** m3u8 URL and assigns it `quality="best"` with `height=None`. Any requested non-`best` quality (`Q720`, `Q1080`, etc.) therefore fails `_find_quality_match` and raises `QualityNotAvailableError`, even though the originally selected yt-dlp stream (`selected_stream`) was a valid numeric quality.

**Consequence:** A user invoking `vkdownloader download <url> --cookie-source browser --quality 720` (or `--method ffmpeg --quality 720` with BROWSER source) gets a hard `QualityNotAvailableError` ("requested 720p, available: best") for every numeric quality. The `--method ffmpeg` and `--method auto` doc examples (quality-selection.md:96-99) implicitly assume numeric qualities work with the browser/cookie path; they do not. Only `--quality best` succeeds.

**Evidence:**
```python
# extractor.py:222-230 — browser path yields exactly one stream, quality="best", height=None
if monitor.m3u8_urls:
    stream = Stream(
        url=monitor.m3u8_urls[0],
        format=StreamFormat.HLS,
        quality="best",
        width=None,
        height=None,
    )
    streams.append(stream)
```
```python
# downloader.py:634-650 (_resolve_cookies) — re-selects on browser streams only
quality_enum = _parse_quality_to_enum(quality)
selector = QualitySelector()
selected_stream = selector.select(browser_streams, quality_enum)  # raises for Q720/Q1080/...
```
```python
# quality.py:73-81 — no match -> QualityNotAvailableError
match = self._find_quality_match(streams, quality_str)
if match:
    result = match
else:
    available_qualities = [s.quality for s in streams]   # -> ["best"]
    raise QualityNotAvailableError(str(quality), available_qualities)
```

**Recommendation:** Decide the intended contract and align code + docs. Options: (a) when `selected_stream` is already provided and only cookies are needed, do not re-run quality selection on the single browser stream — reuse `selected_stream.url` and just fetch cookies; or (b) if browser re-extraction is required, document that BROWSER cookie-source only supports `--quality best`. Given the doc examples show numeric qualities with ffmpeg, option (a) preserves the documented behavior. Effort: small. Priority: mandatory.

---

### SRV-006: `_get_fallback_stream` / `WORST` selection is arbitrary when stream heights are `None`

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/quality.py` |
| **Classification** | advisory |

**Description:** `QualitySelector._get_fallback_stream` (quality.py:35-45) uses `max(streams, key=lambda s: s.height or 0)`, and `WORST` (quality.py:70) uses `min(streams, key=lambda s: s.height or float("inf"))`. Streams from the browser path have `height=None`, which collapses to `0`/`inf`. With multiple `None`-height streams, `max`/`min` return an arbitrary (first/last) element rather than a meaningful "best/worst". For the yt-dlp path heights are populated, so this only bites the browser-derived streams, but it is a latent correctness gap that interacts with SRV-005.

**Evidence:**
```python
# quality.py:45
return max(streams, key=lambda s: s.height or 0)
# quality.py:70
result = min(streams, key=lambda s: s.height or float("inf"))
```

**Recommendation:** When heights are unavailable, fall back to a documented, deterministic secondary key (e.g. bitrate, then URL order) or explicitly raise a clear error. Keep selection deterministic rather than relying on `max`/`min` tie-breaking. Effort: trivial. Priority: recommended.

---

### SRV-007: Segment resume discards the partial yt-dlp file instead of resuming it

| Field | Value |
|-------|-------|
| **ID** | SRV-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `download_with_ytdlp_with_resume_fallback` (downloader.py:358) advertises "segment-based resume on failure", and `_attempt_segment_resume` (downloader.py:440) is invoked when yt-dlp leaves a partial MP4 (`validated_output.stat().st_size > 0`, line 414). However, `_attempt_segment_resume` immediately calls `output_file.unlink()` (downloader.py:506) to "start clean segment download", discarding the partial file entirely. The switch to `download_hls_with_resume` then re-downloads the full set of HLS segments from scratch. So on a yt-dlp interruption, **zero bytes of the partial file are reused** — the "resume" is a full restart via a different mechanism, not a true resume.

**Consequence:** The feature name and the docstrings ("Resume from last checkpoint", "resumes from last checkpoint") overstate the behavior. Users with a large partially-downloaded file pay the full re-download cost. (This also feeds SRV-003: because the partial file is removed and a fresh `download_hls_with_resume` runs, the resume double-count bug from SRV-003 can still trigger on a *subsequent* interruption of the segment phase.)

**Evidence:**
```python
# downloader.py:505-506
# Remove partial file to start clean segment download
output_file.unlink()
# Continue to segment download
return await download_hls_with_resume(...)
```

**Recommendation:** Either rename/clarify the behavior as "fallback restart via segment download" (and fix the docstrings), or — if a real resume is desired — reuse the existing partial file. Given HLS segment resume is the only mechanism that supports resume, the cleanest fix is to make `download_hls_with_resume` itself correct (SRV-003) and document that yt-dlp failures fall back to a fresh segment download. Effort: trivial (docs) / small (behavior). Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 4 |

## Mandatory Fixes

- **SRV-003** (HIGH): Segment resume double-counts progress and can never complete a resumed run — fix skipping + counter semantics.
- **SRV-005** (MEDIUM): BROWSER cookie-source rejects all specific (numeric) qualities; align with documented ffmpeg/numeric usage or update docs.

## Advisory Recommendations

- **SRV-001** (LOW): `SegmentRetryResult` enum is dead code — wire in or remove.
- **SRV-002** (LOW): `ProgressManager.get_progress` is never called — remove or use.
- **SRV-004** (LOW): Dead `if retry_count <= MAX_RESUME_RETRIES:` guard in `_attempt_segment_resume`.
- **SRV-006** (LOW): `BEST`/`WORST` selection is arbitrary for `height=None` streams.
- **SRV-007** (LOW): Segment "resume" discards the partial yt-dlp file (full restart); clarify docs/behavior.

## Doc Updates Needed

- **SRV-005** (SPEC-DEVIATION): quality-selection.md (lines 45-50, 96-99) implies numeric qualities work with ffmpeg/browser cookie path; clarify that BROWSER cookie-source only yields a `best`-quality stream, or fix code so numeric qualities reuse the pre-selected stream URL.
- **SRV-007**: Docstrings in `download.py` ("resumes from last checkpoint", segment_downloader docstring "re-downloading missing segments") overstate resume; align with actual fallback-restart behavior.
