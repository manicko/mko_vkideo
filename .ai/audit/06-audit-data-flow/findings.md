---
name: 06-audit-data-flow-findings
description: End-to-end data-flow audit findings for mko_vkideo
agent: auditor
alwaysApply: false
---

# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

**Runtime verification (all passed):**
- Import full pipeline: OK
- `uv run ruff check src/vkdownloader`: All checks passed (exit 0)
- `uv run mypy src/vkdownloader`: Success, no issues in 23 source files (exit 0)
- `uv run pytest`: 233 passed (exit 0)

---

## Findings

### DF-001: ProgressManager.update_sync is called from threads but is unsynchronized

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description:** In batch mode, `ProgressManager.update_sync()` writes to the shared module-level `_progress_manager._state` dict from multiple concurrent contexts. The yt-dlp progress hook is registered in `_build_ytdlp_options` (`downloader.py:197-205`) and invoked from inside `_download()`, which runs on a worker thread via `loop.run_in_executor(None, _download)` (`downloader.py:621-628`). The segment path (`_tally_and_merge`, `segment_downloader.py:548-550`) writes the same dict from the event loop. `update_sync` performs direct assignment with **no lock** (`downloader_throttle.py:106-121`). The class and `cli.py` docstrings explicitly claim this is safe because "callbacks execute sequentially in the single-threaded asyncio event loop" (`cli.py:62-67`, `downloader_throttle.py:82-89, 106-120`) — this invariant is **false** for yt-dlp hooks, which fire on the executor thread. The `asyncio.Lock` in `get_formatted_progress` only serializes coroutines, not threads, so read paths can observe torn/partial writes while a thread mutates the dict.

**Evidence:**
- `cli.py:69-72` — `_create_progress_callback` → `_progress_manager.update_sync(url_index, downloaded, total)` invoked from the yt-dlp hook chain.
- `downloader.py:621-628` — `_download` (which calls `ydl.download`) runs via `run_in_executor` → progress hooks execute on a worker thread.
- `downloader_throttle.py:106-121` — `update_sync` does `self._state[url_index] = (downloaded, total)` with no synchronization; docstring contradicts the real call site.
- Tests only exercise the async `update()` (e.g. `test_downloader_throttle.py:634`), never the threaded `update_sync` path, so the race is untested.

**Recommendation:** Either (a) make `update_sync` thread-safe (e.g., use a `threading.Lock` or a `dict` specialized for concurrency), or (b) marshal the yt-dlp progress events onto the event loop (e.g., via `loop.call_soon_threadsafe`) so the documented single-threaded invariant becomes true. Also correct the inaccurate docstrings. Why it matters: under `max_concurrent_downloads > 1`, concurrent batch runs can show inconsistent/garbage progress and, during dict resize, risk a `RuntimeError: dictionary changed size during iteration` — a latent crash with no functional benefit from the current design.

---

### DF-002: Segment-based resume only supports BEST quality; numeric qualities abort on yt-dlp failure

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/quality.py` |
| **Classification** | mandatory |

**Description:** The documented "automatic segment-based fallback on failure" (`downloader.py:404-468`) cannot recover a download when the user requested a **specific numeric quality** (e.g. 720p). On a yt-dlp partial failure, `_attempt_segment_resume` force-launches the browser to obtain a fresh token and re-selects the stream (`downloader.py:516-524`). However, browser-captured streams are hardcoded to `quality="best"` with `height=None` (`extractor.py:232-239`). The code then runs `_parse_quality_to_enum(quality)` (e.g. `"720p"` → `QualityEnum.Q720`) and `selector.select(browser_streams, QualityEnum.Q720)`. `QualitySelector.select` finds no numeric match (the only browser stream is `"best"`) and raises `QualityNotAvailableError` (`quality.py:82-91`). `_attempt_segment_resume` only catches `(ExtractionError, OSError)` and `ValueError` (`downloader.py:554-558`); `QualityNotAvailableError` (subclass of `VKDownloadError`, not `ValueError`) is **not** caught and propagates, aborting the whole download. So a numeric-quality download that partially failed via yt-dlp is reported as a hard quality error rather than being resumed — the exact recovery scenario the feature advertises.

**Evidence:**
- `downloader.py:471-560` — `_attempt_segment_resume` raises/propagates when browser stream selection fails for non-BEST quality.
- `extractor.py:232-239` — browser stream `quality="best"`, `height=None`.
- `quality.py:82-91` — numeric match fails → `QualityNotAvailableError`.
- `downloader.py:554-558` — handler list omits `QualityNotAvailableError` (and `VKDownloadError`).

**Recommendation:** When the requested quality is numeric and the browser stream only exposes `"best"`, fall back to downloading the available `"best"` stream during resume (preserving the original intent of retrying the download) and/or catch `QualityNotAvailableError` in `_attempt_segment_resume` to degrade gracefully. Why it matters: this silently breaks resume robustness for the most common user case (a specific resolution), turning a recoverable transient failure into a failed download.

---

### DF-003: Settings validation errors are misreported as URL-format errors

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** The `download()` command constructs `Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)` (`cli.py:392`), then wraps the whole body in `except ValueError:` that prints `"Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}"` and exits 1 (`cli.py:445-450`). But `Settings` can also raise `ValueError` during construction — specifically the `cookie_source` validator rejects `CookieSource.FILE` (`config.py:124-136`). Because Typer accepts `file` as a valid `CookieSource` enum member, `--cookie-source file` reaches `Settings()` and raises `ValueError`, which is then mislabeled as an invalid URL. A user who passed a perfectly valid URL gets a confusing "Invalid URL format" message. The sibling `batch_download` command (`cli.py:527`) constructs the same `Settings` but has **no** `ValueError` handler, so the identical input produces an unhandled traceback. The two commands handle the same failure differently.

**Evidence:**
- `cli.py:392` + `cli.py:445-450` — `except ValueError` conflates config validation with `parse_video_id` `ValueError`.
- `config.py:124-136` — validator raises `ValueError` for `CookieSource.FILE`.
- `cli.py:527` — `batch_download` builds `Settings` with no equivalent handler (inconsistent).

**Recommendation:** Separate config-validation failures from URL-parse failures. Catch the `Settings` construction error explicitly (or let Typer/pydantic validation surface a clear message) before any URL work, and reserve the "Invalid URL format" message for `ValueError` originating from `parse_video_id`. Why it matters: misleading diagnostics waste user time and the inconsistent handling (silent traceback in `batch`) undermines the "config error stops before side-effects" expectation.

---

### DF-004: Unreachable empty-streams guard masks real control flow

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `_download_single` (`cli.py:177-182`) and `download()` (`cli.py:406-411`) both contain `if not video.streams: raise QualityNotAvailableError(...)`. This guard is unreachable: `VKVideoExtractor.extract_streams` already raises `VideoNotFoundError` when no streams are found (`extractor.py:85-86`) before returning, so `video.streams` can never be empty after a successful `extract_streams` call. The guards' comments (`cli.py:176`, `cli.py:405`) claim they "provide an accurate error message," which they never do. The code implies a fallback path that does not exist, which can mislead maintainers about how empty-stream errors are actually surfaced.

**Evidence:**
- `extractor.py:83-94` — `extract_streams` raises `VideoNotFoundError` when `streams` is empty; only then returns `VideoWithStreams`.
- `cli.py:177-182` and `cli.py:406-411` — post-extraction empty-stream checks can never be True.

**Recommendation:** Investigate intent: either remove the dead guards (and rely on `extract_streams` raising) or change `extract_streams` to return rather than raise on empty and let the guards own the error. Document whichever choice is made. Why it matters: dead defensive code hides the true error-propagation path and invites incorrect "fixes" later.

---

### DF-005: Stale merge temp files can inflate progress and defeat resume cleanup

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_merge_segments_batched` writes intermediate merge files named `batch_{NNNNN}.ts` directly into the same `segments_dir` as the real segments (`ffmpeg_utils.py:165`). The resume bookkeeping then globs `segments_dir.glob("*.ts")` in two places: `_run_download_session` computes `existing_segment_count` (`segment_downloader.py:818`) to decide whether to clear stale metadata, and `_tally_and_merge` counts `len(segments_dir.glob("*.ts"))` for progress (`segment_downloader.py:547`). A `batch_*.ts` file left over from an interrupted/partial merge (the `finally` in `_merge_segments_batched` only unlinks *temp_files* it created, `ffmpeg_utils.py:271-275`) matches the `*.ts` glob and is counted as a downloaded segment, overstating progress and preventing the fresh-start metadata clear. This is an edge case (requires a prior failed merge) but is a genuine data-integrity gap in naming/cleanup.

**Evidence:**
- `ffmpeg_utils.py:165` — `batch_output = temp_dir / f"batch_{batch_start:05d}.ts"` inside `segments_dir`.
- `segment_downloader.py:818` and `segment_downloader.py:547` — `*.ts` glob collides with `batch_*.ts`.
- `ffmpeg_utils.py:271-275` — `finally` only removes `temp_files` it appended, not arbitrary leftovers.

**Recommendation:** Store intermediate merge files in a dedicated subdirectory (e.g. `segments_dir / "_merge"`) or name them so they do not match the segment glob (e.g. prefix with a non-digit/dot). Why it matters: keeps resume bookkeeping and progress counts accurate; avoids a confusing over-count after an interrupted merge.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

- **DF-001** — Synchronize `ProgressManager.update_sync` (remove false event-loop-serialization assumption in threaded yt-dlp path).
- **DF-002** — Make segment resume recover numeric-quality downloads (catch `QualityNotAvailableError` / fall back to best in `_attempt_segment_resume`).
- **DF-003** — Stop conflating `Settings` validation `ValueError` with URL-format errors; align `download` and `batch` handling.

## Advisory Recommendations

- **DF-004** — Remove or re-home the unreachable empty-streams guards; document the real error path.
- **DF-005** — Isolate merge temp files from the segment glob to keep resume/progress bookkeeping correct.

## Doc Updates Needed

- No explicit documentation-only updates identified; the code-level fixes above (DF-001 docstrings, DF-002 behavior) should be reflected in any docs describing progress reporting and the yt-dlp→segment resume fallback.

