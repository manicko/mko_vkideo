# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/06-audit-data-flow.md
**Status:** complete
**Validated:** no

---

## Runtime Verification

- **R1 — Import full pipeline:** OK. `vkdownloader.cli`, `config`, `services.downloader`, `services.extractor`, `services.quality`, `services.segment_downloader`, `services.downloader_throttle` all import cleanly.
- **R2 — Linter / Type Checker:** `uv run ruff check src/vkdownloader` → exit 0 (all checks passed). `uv run mypy src/vkdownloader` → exit 0 (no issues in 23 source files).
- **R3 — Test Suite:** `uv run pytest -q` → 217 passed.

No runtime failures. All findings below are derived from static tracing of the data-flow path, not from test/lint failures.

## Findings

### DF-001: Resume metadata is never reset; accumulated count can exceed total and permanently skip the merge

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR / SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** `download_hls_with_resume()` (segment_downloader.py:764) is documented as "segment-level download … can resume after interruption by re-downloading missing segments" (docs/01-tools/vkdownloader-overview.md:16, :251). In reality it never resets the progress metadata or the segments directory at start, and the merge-completion check uses an *accumulated* count rather than the count of segments present on disk.

`download_hls_with_resume` creates `segments_dir` and `metadata_file` with `exist_ok=True` (lines 800-802) but does **not** delete a pre-existing `.{stem}_progress.json` or stale `.{stem}_segments/*.ts`. On any re-entry for the same `output_file` (e.g. a second retry inside `download_with_ytdlp_with_resume_fallback`'s loop, or a re-run after a previous failed/partial download), `_tally_and_merge` (line 540) computes:

```python
downloaded_count = _load_downloaded_count(metadata_file) + sum(1 for r in download_results if r)
```

If the prior run already stored a partial count `P` (e.g. 50 of 100), and the new run successfully re-downloads all 100 segments, `downloaded_count = 50 + 100 = 150`. The merge is gated by `if downloaded_count == len(segments)` (line 549). Since `150 != 100`, the merge branch is **skipped**, `_cleanup_segments` is never called, and the function returns `None` — **even though every segment is present on disk and the download silently fails to produce an output file.**

**Evidence:**
- segment_downloader.py:796-802 — no reset of `segments_dir` / `metadata_file` before download.
- segment_downloader.py:540-556 — `downloaded_count = _load_downloaded_count(...) + sum(...)`, merge only when `== len(segments)`.
- downloader.py:400-437 — `download_with_ytdlp_with_resume_fallback` loops up to `MAX_RESUME_RETRIES` (3) calling `_attempt_segment_resume` → `download_hls_with_resume` repeatedly on the same `output_file`, so stale metadata from a prior segment attempt is reused.

**Recommendation:** Reset progress metadata at the start of a fresh `download_hls_with_resume` invocation (or make resume explicitly opt-in), and base the merge decision on the number of segment files actually present on disk (`segments_dir.glob("*.ts")`) rather than an accumulated counter. This prevents a successful-but-count-inflated run from silently producing no output.

---

### DF-002: "Segment-level resume" re-downloads all segments instead of only missing ones

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** Documentation states the segment downloader "resume[s] after interruption by re-downloading missing segments" (docs/01-tools/vkdownloader-overview.md:251). The implementation, however, always creates a download task for **every** segment on each call. `_create_segment_download_tasks` (lines 652-677) iterates over the full `segments` list and writes each to `segment_path = task.segments_dir / f"{task.idx:05d}.ts"` with `open("wb")` (via `_download_segment_sequential`/`_download_segment_parallel`), **overwriting** any previously downloaded file. The saved `downloaded_count` is used only for progress display and the (broken, see DF-001) merge gate; it is never used to skip already-downloaded segments.

Consequence: a resume after interruption re-fetches all N segments (wasting bandwidth and time, and re-triggering rate limits), contradicting the documented resume behavior. Combined with DF-001, the re-download also corrupts the completion counter.

**Evidence:**
- segment_downloader.py:651-677 — tasks created for all `segments`, no skip of already-present files.
- segment_downloader.py:540 — `downloaded_count` read from metadata but not used to filter the task list.

**Recommendation:** When resuming, filter the segment list to files not already present in `segments_dir` (and whose size is non-zero), and write the completion check against the on-disk count. This realizes the documented resume contract and avoids redundant re-downloads.

---
