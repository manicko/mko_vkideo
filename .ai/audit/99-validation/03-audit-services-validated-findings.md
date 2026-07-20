# Phase 03 Audit Findings — Service Layer & Business Logic (Validated)

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/03-audit-services.md
**Status:** complete
**Validated:** validator
**Validated Date:** 2026-07-20

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

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms `SegmentRetryResult` is defined in `enums.py` but has zero runtime references in `src/` or `tests/`. No imports exist. This is unused code that should be removed or integrated.
> - **See also:** None

**Recommendation:** Remove the enum. Effort: trivial. Priority: recommended.

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
```python
downloader_throttle.py:143
async def get_progress(self, url_index: int) -> tuple[int, int]:
    async with self._lock:
        return self._state.get(url_index, (0, 0))
```
Grep for `get_progress` across `src/` returns only the definition.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms `get_progress` is defined but has zero runtime references. The only tests for this method are absent. The method adds surface area without utility.
> - **See also:** None

**Recommendation:** Remove the method to reduce surface area. Effort: trivial. Priority: recommended.

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

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms both defects. Line 727 loads `downloaded_count` but it is never passed to any function that would skip already-downloaded segments. Line 540 adds the old count to the new result count, making completion impossible on resume. This is a critical bug that prevents resume functionality from working.
> - **See also:** None

**Recommendation:** Fix the resume logic: (a) skip segments whose file already exists, and (b) replace the additive counter with only the count of newly-downloaded segments, only persisting when `downloaded_count == len(segments)`. Effort: medium. Priority: mandatory.

---

### SRV-004: Dead conditional guard in `_attempt_segment_resume`

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** In `download_with_ytdlp_with_resume_fallback` (downloader.py:358), the `while retry_count <= MAX_RESUME_RETRIES:` loop (downloader.py:400) guarantees `retry_count <= MAX_RESUME_RETRIES` on every iteration. Inside the loop body, the line `if retry_count <= MAX_RESUME_RETRIES:` (downloader.py:418) is therefore always true and the branch is unconditional. This is dead/confusing control flow that implies a guard that does not exist.

**Evidence:**
```python
# downloader.py:400 (while loop) and 418 (redundant guard inside same function)
while retry_count <= MAX_RESUME_RETRIES:
    ...
    if retry_count <= MAX_RESUME_RETRIES:  # <-- redundant inside the while loop
        if (
            segment_result := await _attempt_segment_resume(...)
        ) is not None:
            return segment_result
```

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms the guard at line 418 is redundant. The `while retry_count <= MAX_RESUME_RETRIES` loop at line 400 ensures the condition is always satisfied when the inner `if` is reached. The guard adds no protection and misleads the reader. Additionally, the original finding incorrectly stated the guard is inside `_attempt_segment_resume`; it is actually in the same function (`download_with_ytdlp_with_resume_fallback`) at line 418.
> - **See also:** None

**Recommendation:** Remove the redundant guard. The body is already gated by the caller loop. Effort: trivial. Priority: recommended.

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
# downloader.py:631-637 (_resolve_cookies) — re-selects on browser streams and raises for numeric quality
if settings.cookie_source == CookieSource.BROWSER:
    browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(url)
    if browser_streams:
        ...
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

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms the bug. The browser extraction path always produces a single stream with `quality="best"` and `height=None`. When `_resolve_cookies` calls `QualitySelector.select()` with a numeric quality enum, `_find_quality_match` fails and raises `QualityNotAvailableError`. The `download` and `ffmpeg` paths in `perform_download` both call `_resolve_cookies` when `cookie_source == BROWSER`, making this a real user-facing defect. The documentation in `quality-selection.md` (lines 96-99) shows examples with numeric qualities and `--method ffmpeg` without warning about this limitation.
> - **See also:** SRV-006 (related: BEST/WORST selection with None heights)

**Recommendation:** When `cookie_source == BROWSER`, if a stream was already selected, reuse its URL instead of re-selecting. Do not run quality selection on the browser-stream list unless quality == BEST. Effort: small. Priority: mandatory.

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

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms the implementation. When `height=None`, the default values produce arbitrary selection. However, the test at `test_quality_selector.py:142-152` (`test_get_fallback_stream_handles_none_height`) shows the current behavior: it falls back to streams with actual heights when available. The issue only manifests when ALL streams have `height=None`, which occurs with browser-extraction. While technically correct, this is latent for the browser path. Given SRV-005 should be fixed to avoid quality re-selection on browser streams, this becomes a secondary concern.
> - **See also:** SRV-005

**Recommendation:** When fixing SRV-005, this issue becomes moot for browser streams. For robustness, consider documenting that BEST/WORST with None-height streams returns an arbitrary element. Effort: trivial. Priority: recommended.

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

**Consequence:** The feature name and the docstrings ("resumes from last checkpoint", segment_downloader docstring "re-downloading missing segments") overstate the behavior. Users with a large partially-downloaded file pay the full re-download cost. (This also feeds SRV-003: because the partial file is removed and a fresh `download_hls_with_resume` runs, the resume double-count bug from SRV-003 can still trigger on a *subsequent* interruption of the segment phase.)

**Evidence:**
```python
# downloader.py:505-506
# Remove partial file to start clean segment download
output_file.unlink()
# Continue to segment download
return await download_hls_with_resume(...)
```

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms `output_file.unlink()` at line 506 removes the partial file before calling `download_hls_with_resume`. The docstring at downloader.py:373-377 promises "segment-based resume on failure" and "resumes from last checkpoint", but the implementation is a fallback restart via segment download. This is a documentation-behavior mismatch.
> - **See also:** SRV-003

**Recommendation:** Update docstrings to clarify this is a fallback restart, not true resume. Change "resumes from last checkpoint" to "falls back to a fresh segment-based download via HLS". Note that the partial yt-dlp file is discarded, not resumed. This documentation-only fix is sufficient since SRV-003 must be fixed for actual resume behavior, and implementing true partial-file resume would add complexity with low ROI. Effort: trivial. Priority: recommended.

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
- **SRV-005** (MEDIUM): BROWSER cookie-source rejects all specific (numeric) qualities; fix the code to reuse the already-selected stream URL instead of re-selection, then update docs/01-tools/quality-selection.md and docs/11-guides/vkdownloader-limitations.md to remove contradictory numeric-quality-with-browser examples.

## Advisory Recommendations

- **SRV-001** (LOW): `SegmentRetryResult` enum is dead code — remove it.
- **SRV-002** (LOW): `ProgressManager.get_progress` is never called — remove it.
- **SRV-004** (LOW): Dead `if retry_count <= MAX_RESUME_RETRIES:` guard in `download_with_ytdlp_with_resume_fallback` (inside the while loop).
- **SRV-006** (LOW): `BEST`/`WORST` selection is arbitrary for `height=None` streams.
- **SRV-007** (LOW): Segment "resume" discards the partial yt-dlp file (full restart); clarify docs/behavior.

## Doc Updates Needed

- **SRV-005**: quality-selection.md (lines 96-99) implies numeric qualities work with ffmpeg/browser cookie path; update it to reflect that BROWSER cookie-source only yields a `best`-quality stream after the SRV-005 code fix reuses the pre-selected stream URL (and remove the contradictory numeric-quality-with-browser examples).
- **SRV-007**: Clarify docstrings in `downloader.py` ("resumes from last checkpoint") to reflect actual fallback-restart behavior.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 7 | SRV-001, SRV-002, SRV-003, SRV-004, SRV-005, SRV-006, SRV-007 |
| Reclassified | 0 | - |
| Merged | 0 | - |
| Rejected | 0 | - |

### Rejected Findings

None

### Merged Findings

None

### Reclassified Findings

None

---

## Cross-Phase Analysis

### SRV-003 Interaction with SRV-007

SRV-003 (segment resume counter bug) and SRV-007 (partial file discarded) are related but distinct. SRV-007 discards the yt-dlp partial file, then SRV-003 prevents the segment-download phase from completing even on a fresh start. Both must be fixed for reliable resume behavior.

### SRV-005 Documentation-Crossference

SRV-005 directly contradicts the documentation in `docs/01-tools/quality-selection.md` lines 96-99 which shows `--quality 720 --method ffmpeg` without warning that this fails with `--cookie-source browser`. Additionally, `docs/11-guides/vkdownloader-limitations.md` lines 115-118 recommends `--method ffmpeg --cookie-source browser` which would trigger this bug. This is a SPEC-DEVIATION resolved by the SRV-005 code fix (reuse the already-selected stream URL) plus a doc update to remove the contradictory examples.

### CFG-001 Cross-Reference

CFG-001 from Phase 02 identifies that `CookieSource.FILE` silently no-ops in the primary download flow. This shares root cause with SRV-005: both relate to `cookie_source` handling. However, CFG-001 covers FILE mode specifically, while SRV-005 covers BROWSER mode quality selection. They are distinct issues requiring separate fixes.


