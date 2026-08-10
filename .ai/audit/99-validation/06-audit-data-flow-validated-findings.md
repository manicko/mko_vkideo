# Phase 06 Audit Findings - End-to-End Data Flow (VALIDATED)

**Executor:** audit-executor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes (validator agent - 2026-08-09)

---

## Validator Scope

Validated by the validator agent against vkdownloader v0.1.0 source tree (src/vkdownloader/).
Each finding was cross-checked against the actual implementation in downloader.py (1,218 lines), segment_downloader.py (901 lines), extractor.py (284 lines), cookies.py (77 lines), ffmpeg_utils.py (360 lines), downloader_throttle.py (340 lines), quality.py (116 lines), cli.py (653 lines), models/enums.py (68 lines), models/dtos.py (24 lines), models/video.py (30 lines), utils/correlation.py (55 lines), config.py (252 lines), docs/11-guides/configuration.md, docs/01-tools/vkdownloader-overview.md.

All evidence in the findings was verified against the current codebase. Line-number anchors match the files as they exist today.

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| R1 - Import | python import | PASS |
| R2 - Lint | uv run ruff check src/ | PASS |
| R2 - Format | uv run ruff format --check src/ | FAIL (services/downloader.py - pre-existing, tracked CLI-005 Phase 01) |
| R2 - Types | uv run mypy | FAIL (pre-existing utils/correlation.py:55 unused type:ignore - tracked CLI-004 Phase 01) |
| R3 - Tests | uv run pytest | PASS (325 passed) |

---

## Cross-Phase Analysis

### Duplicates / Merge Candidates

| Finding | Related Phase Finding | Action |
|---------|-----------------------|--------|
| DF-005 | SRV-003 (Phase 03) | MERGE - identical root cause: _ffmpeg_progress_adapter at downloader.py:1079-1083 always reports downloaded == total. SRV-003 classifies as BEST-PRACTICE; DF-005 classifies as SPEC-DEVIATION. Reclassified SPEC-DEVIATION. SRV-003 retained for reference. |
| DF-012 | (self-contained) | MERGE INTO DF-001 - DF-012 is explicit downstream consequence. Fixing DF-001 automatically resolves DF-012. |
| DF-007 | SRV-002 (Phase 03) | RELATED MERGE - SRV-002 found _write_netscape_cookie_file (cookies.py:58-74) with correct 0o600 but dead code; DF-007 found live path _create_temp_cookie_file (downloader.py:87) at 0644. Same security concern, converging fix. |
| DF-011 | CFG-004 (Phase 02) | COMPLEMENTARY OVERLAP - CFG-004 (DOC-UPDATE) recommends clarifying docs; DF-011 (SPEC-DEVIATION) recommends adding flag. Not conflicting. |
| Phase 06 doc note (CookieSource.FILE) | CFG-003 (Phase 02) | DUPLICATE - CFG-003 already covers this exact doc inconsistency. |

### Cross-Phase Conflicts

None detected. All phases agree on:
- Test suite: 325 passed (consistent Phases 01-06)
- ruff check src/: PASS (Phases 02, 04, 06)
- ruff format --check: FAIL on services/downloader.py (consistent Phases 01-06)
- mypy: FAIL on utils/correlation.py:55 (consistent Phases 01-06)

No phase asserts all commands work while another asserts a command crashes.

### Dependency Chains

- DF-001 -> DF-012 -> DF-006: Critical failure cascade validated. Fixing DF-001 resolves DF-012. DF-006 is independent fix in same cascade.
- DF-007 <-> INT-001 (Phase 05): INT-001 recommends ffmpeg cookies file option, routing through _create_temp_cookie_file. Apply joint fix.
- DF-005 <-> DF-009: Both address progress reporting. DF-005 (ffmpeg 100%) is subset of DF-009 (units inconsistent).

---

## Findings

### DF-001: Quality enum degrades from QualityEnum.BEST to stream quality string (e.g. 1080p) [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (mandatory)**

**Verification:**

`download_video()` (downloader.py:1206-1218) selects a stream via `QualitySelector.select(video.streams, quality)` where `quality` is the original `QualityEnum` (e.g., `QualityEnum.BEST`). The selected `Stream` carries `stream.quality` as a `str` set by the extractor at `extractor.py:175`: `quality=f"{height}p" if height else "unknown"` -- e.g., `"1080p"`.

At line 1208, `download_video` passes `str(stream.quality)` -- i.e., `"1080p"` -- as the `quality` parameter to `perform_download()` (downloader.py:966). This is a type-preserving no-op (`Stream.quality` is already `str` per `models/video.py:20`), but the value has been degraded from the semantic `"best"` to the resolution-specific `"1080p"`.

In `_resolve_cookies()` (downloader.py:940-944):
```python
quality_enum = _parse_quality_to_enum(quality)  # _parse_quality_to_enum("1080p") -> QualityEnum.Q1080
if quality_enum == QualityEnum.BEST:             # Q1080 == BEST -> always False
```

`_parse_quality_to_enum("1080p")` (downloader.py:145-165) first tries `QualityEnum("1080p")` -> `ValueError` (no member has value `"1080p"`), then strips `"p"` -> `QualityEnum("1080")` -> `QualityEnum.Q1080`. The `== QualityEnum.BEST` comparisons at `downloader.py:944` (`_resolve_cookies`) and `downloader.py:690` (`_attempt_segment_resume`) always evaluate to `False` when the user originally requested `BEST`.

Consequence verified: The `if quality_enum == QualityEnum.BEST` branch (which selects the fresh `m3u8_url` from browser-extracted streams at `downloader.py:693` / `downloader.py:947`) is unreachable when the original request was `QualityEnum.BEST`. The `else` branch retains the stale `m3u8_url`.

All evidence line numbers verified against current source: `downloader.py:1208` OK, `downloader.py:944` OK, `downloader.py:690` OK, `extractor.py:175` OK, `enums.py:16` OK.

**Recommendation stands:** Pass `str(quality)` (the original `QualityEnum` from the `download_video` parameter at line 1144) instead of `str(stream.quality)` at line 1208.

**Rollout risk:** Medium. Minimal-risk fix: single-line change (`str(stream.quality)` -> `str(quality)`). Preserves `str` type contract throughout; no signature changes needed. Full `str` -> `QualityEnum` type change across 5 functions + 1 DTO is cleaner but more invasive.


### DF-002: Single download command has no correlation ID [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory)**

**Verification:**

The `download` command (`cli.py:418-445`) defines an inner `_download()` coroutine at `cli.py:455-477` that calls `download_video()` directly at `cli.py:459` **without** calling `bind_correlation_id()` or `generate_correlation_id()`. No correlation ID is bound in this code path.

The `batch` command routes through `_download_single()` (`cli.py:181-264`), which calls `generate_correlation_id()` + `bind_correlation_id()` at `cli.py:219-220` before invoking `download_video()`, and calls `clear_correlation_id()` in its `finally` block at `cli.py:264`.

`download_video()` itself (`downloader.py:1142-1218`) contains **no** correlation-ID binding -- no call to `bind_correlation_id`, `generate_correlation_id`, or `clear_correlation_id` anywhere in `downloader.py`. Confirmed by grep across the entire `src/vkdownloader/` tree: `correlation` is imported only in `cli.py` and `utils/correlation.py`.

All log calls in the single-download path (extract -> select -> download) will lack a `correlation_id` field in their structured output, since structlog's `merge_contextvars` (`config.py:240`) merges contextvars and the single-download path never binds one.

All evidence verified: `cli.py:219-220` (batch binds) OK, `cli.py:459` (single calls directly, no binding) OK, `downloader.py:1142` (download_video has no binding) OK.

**Recommendation stands:** Move `bind_correlation_id`/`clear_correlation_id` into `download_video()` (try/finally) so both paths are covered. Trivial, low-risk change.


### DF-003: Segment download progress callback fires only once, at merge time [APPROVED]

> **Validator Decision:** **VALIDATED -- BEST-PRACTICE (advisory)**

**Verification:**

`_download_segment_concurrent()` (`segment_downloader.py:646-699`) downloads a single segment and returns `(task.idx, result)` but **never invokes `progress_callback`**. The callback is only called once, in `_tally_and_merge()` at `segment_downloader.py:586-588`:

```python
if progress_callback:
    progress_callback(video_id, downloaded_count, len(segments))
```

This fires after `asyncio.gather(*tasks)` completes at `_await_and_cancel()` (`segment_downloader.py:632`), i.e., after *all* segments finish downloading.

By contrast:
- yt-dlp path: `progress_callback(video_id, downloaded, total)` fires per-progress-line at `downloader.py:838`
- ffmpeg path: `progress_callback` fires per-ffmpeg-progress-block via `_ffmpeg_progress_adapter` at `downloader.py:1081`

During batch runs, `_poll_progress_display` (`cli.py:166-178`) polls every 1.0s, but for segment-download URLs the progress state stays at `0/total` until merge time, giving the user no visibility into in-flight segment downloads.

All evidence verified: `segment_downloader.py:584-588` (_tally_and_merge, single callback) OK, `segment_downloader.py:646-699` (_download_segment_concurrent, no callback) OK, `cli.py:166-178` (_poll_progress_display) OK.

**Recommendation stands:** Call `progress_callback` per-segment completion in `_download_segment_concurrent`. The `Callable[[str, int, int], None]` protocol already exists and is passed via `DownloadPolicy` / `DownloadContext`. The `progress_callback` is available in `_run_download_session` via `request.progress_callback` which flows into `DownloadPolicy` -- but `_download_segment_concurrent` only receives `policy` and `task`, and `policy` does **not** include `progress_callback`. A new field would need to be added to `DownloadPolicy` or the callback invoked at the `_download_segment` level. Moderate effort, moderate risk.


### DF-004: MAX_RESUME_RETRIES hardcoded; --max-retries does not control application-level fallback [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory)**

**Verification:**

`MAX_RESUME_RETRIES = 3` is a module-level constant at `downloader.py:57`. The retry loop at `downloader.py:585` uses it directly:

```python
while retry_count <= MAX_RESUME_RETRIES:
```

The `--max-retries` CLI flag (`cli.py:576-581`) flows through `download_video` at `cli.py:1182-1183`:

```python
if max_retries_override is not None:
    settings = settings.model_copy(update={"max_retries": max_retries_override})
```

This updates `settings.max_retries`, but the retry loop at `downloader.py:585` uses `MAX_RESUME_RETRIES` (the hardcoded constant), **not** `settings.max_retries`. The `settings.max_retries` value only reaches the yt-dlp subprocess via `-R` and `--fragment-retries` flags at `downloader.py:296-299`.

Documentation at `configuration.md:112` states max_retries "applies to single downloads as well as batch downloads" with "automatically retry up to this number of attempts" -- this is only true for the yt-dlp subprocess flags, not the application-level fallback loop.

**Related finding:** SRV-006 (Phase 03) notes the same retry loop at `downloader.py:585-595` lacks any backoff/sleep between attempts. DF-004 (hardcoded count) and SRV-006 (no backoff) are complementary -- both target the same loop but address different aspects.

All evidence verified: `downloader.py:57` (MAX_RESUME_RETRIES = 3) OK, `downloader.py:585` (while loop uses constant) OK, `downloader.py:296-299` (yt-dlp flags use settings.max_retries) OK, `cli.py:576-581` (batch --max-retries) OK, `downloader.py:1182-1183` (model_copy update) OK.

**Recommendation stands:** Replace `MAX_RESUME_RETRIES` with `settings.max_retries` at `downloader.py:585`. Trivial, low-risk change. Consider also addressing SRV-006's missing backoff simultaneously.


### DF-005: FFMPEG progress adapter always reports 100% completion [APPROVED -- MERGED WITH SRV-003]

> **Validation Note:**
> - **Action:** merged
> - **Detail:** Identical root cause to SRV-003 (Phase 03, BEST-PRACTICE). Both findings target `_ffmpeg_progress_adapter` at `downloader.py:1079-1083`: `downloaded = fp.total_size; progress_callback(video_id, downloaded, downloaded)` -- `total` is always equal to `downloaded`, reporting 100% unconditionally. ffmpeg's `-progress` `total_size` key is cumulative bytes written so far, not a final total; ffmpeg emits no total-bytes field. Reclassified from BEST-PRACTICE (SRV-003's original classification) to SPEC-DEVIATION because the code deviates from the documented real-time progress behavior (vkdownloader-overview.md:177-196).
> - **See also:** SRV-003 (Phase 03), DF-009

**Verification:**

`perform_download`'s `DownloadMethod.FFMPEG` branch (`downloader.py:1075-1083`):

```python
def _ffmpeg_progress_adapter(fp: FfmpegProgress) -> None:
    downloaded = fp.total_size if fp.total_size is not None else 0
    progress_callback(video_id, downloaded, downloaded)  # total == downloaded
```

`FfmpegProgress` (`ffmpeg_utils.py:45-56`) has fields: `frame, fps, speed, total_size, out_time_us, out_time_ms, out_time, progress`. There is **no** `downloaded_bytes` field. `total_size` is populated from ffmpeg's `total_size=` key, which represents "size so far in bytes" (cumulative), not the final file size. Since `total = downloaded = fp.total_size`, the callback always reports 100%.

All evidence verified: `downloader.py:1080-1081` OK, `ffmpeg_utils.py:46-56` (FfmpegProgress, out_time_us present, no downloaded_bytes) OK.

**Recommendation stands:** Report `downloaded=fp.total_size, total=0` (unknown total) for ffmpeg path, or derive percentage from `out_time_us`/`out_time_ms` against input duration if available.


### DF-006: Token refresh during segment download blocked by cookie_source check [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory)**

**Verification:**

`_refresh_token_and_retry()` (`segment_downloader.py:408-431`):

```python
if settings.cookie_source != CookieSource.BROWSER:    # line 417
    logger.warning("token_refresh_failed_cookie_source", ...)
    return None                                        # line 423

streams, new_cookies, _raw_cookies = await extractor.extract_streams_with_cookies(
    video_url, force_browser=True                       # line 426 -- UNREACHABLE when cookie_source != BROWSER
)
```

The guard at `segment_downloader.py:417-423` returns `None` before `extract_streams_with_cookies` (which accepts `force_browser=True`) is ever called. Since `cookie_source` defaults to `CookieSource.NONE` (`config.py:97-100`), this means **token refresh is impossible for the default configuration** during segment playlist fetch retry on 403/410.

This is inconsistent with `_attempt_segment_resume()` (`downloader.py:677-683`), which calls `extractor.extract_streams_with_cookies(video_url, force_browser=True)` **without** the cookie_source guard, at line 681-683. The `force_browser=True` parameter is designed to bypass the `cookie_source == NONE` check inside `extract_streams_with_cookies` (`extractor.py:121`: `if not force_browser and self.settings.cookie_source == CookieSource.NONE:`).

This is step 8 in the critical failure cascade (DF-001 -> DF-012 -> DF-006). Fixing DF-001 resolves the cascade entry, but DF-006 remains an independent gap: even with fresh m3u8_url (post-DF-001 fix), a 403/410 during segment playlist fetch cannot trigger token refresh when `cookie_source != BROWSER`.

All evidence verified: `segment_downloader.py:417-423` (cookie_source guard) OK, `downloader.py:681-683` (force_browser=True without guard) OK, `extractor.py:121` (bypassed check) OK.

**Recommendation stands:** Remove the `if settings.cookie_source != CookieSource.BROWSER: return None` guard in `_refresh_token_and_retry` so `force_browser=True` is reached, matching the pattern in `_attempt_segment_resume`. Small, low-risk change.


### DF-007: Temp cookie file created with world-readable permissions (0644) on Unix [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (mandatory)**
> **Related:** SRV-002 (Phase 03) -- `_write_netscape_cookie_file` (cookies.py:58-74) correctly uses `os.open(..., 0o600)` but is dead code (zero callers). DF-007 targets the *live* path `_create_temp_cookie_file` (downloader.py:87) which uses `tempfile.mkstemp` at default 0644.

**Verification:**

`_create_temp_cookie_file()` (`downloader.py:87`):

```python
fd, path = tempfile.mkstemp(suffix=".cookies.txt", prefix="vk_cookies_")
```

`tempfile.mkstemp()` on Unix with default umask `022` creates files at mode `0644` (owner-writable, group/other world-readable). The file contains live VK session cookies (Netscape format from `_cookies_to_netscape` at `cookies.py:13`). The Python docs for `tempfile.mkstemp` do not guarantee `0o600` -- the file permissions are subject to the process umask, which is typically `022` on Unix, yielding `0644`.

Cleanup is in the `finally` block of `_download_with_ytdlp` at `downloader.py:909-912`:

```python
finally:
    if cookie_file is not None and cookie_file.exists():
        cookie_file.unlink(missing_ok=True)
```

If the process crashes, is killed (SIGKILL), or terminates abnormally before reaching this `finally`, the cookie file persists on disk at `0644` permissions.

By contrast, `_write_netscape_cookie_file()` (`cookies.py:72`) correctly uses `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` -- but it is dead code (confirmed by SRV-002 in Phase 03: zero callers in `src/` or `tests/`). The audit in Phase 03 found the secure function exists but is unused; this phase (06) found the live function is insecure. Same root cause, converging fix.

All evidence verified: `downloader.py:87` (tempfile.mkstemp) OK, `cookies.py:72` (os.open at 0o600) OK, `downloader.py:909-912` (finally cleanup only) OK.

**Recommendation stands:** In `_create_temp_cookie_file`, add `os.chmod(path, 0o600)` immediately after `os.write`/`os.close` at `downloader.py:89-90`, or replace `tempfile.mkstemp` with `os.open` at `0o600`. Trivial, low-risk. Consider consolidating with dead `_write_netscape_cookie_file` (SRV-002).


### DF-008: Partial yt-dlp output file not cleaned up on failure [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory)**

**Verification:**

In `download_with_ytdlp_with_resume_fallback()` (`downloader.py:585-632`), the retry loop calls `_download_with_ytdlp` (line 586) which writes to `output_file` via yt-dlp's `-o` flag (`downloader.py:288`). When yt-dlp fails, `_attempt_segment_resume()` is called (line 611).

`_attempt_segment_resume` (`downloader.py:677-744`) calls `output_file.unlink()` at line 714 -- but this is **inside** the `if browser_streams:` block (line 684). If browser extraction returns empty streams, raises `ExtractionError`, or raises `OSError`, execution falls through to the `except` handlers at lines 730-741, and the partial file is **never unlinked**.

When all retries are exhausted (line 626-628, `while retry_count <= MAX_RESUME_RETRIES` exits), the function returns `None` at line 632 with no cleanup of the partial `output_file` from the last `_download_with_ytdlp` attempt.

The `finally` block in `_download_with_ytdlp` (`downloader.py:909-912`) only cleans up the cookie file, not the output file.

All evidence verified: `downloader.py:585-632` (retry loop, no output cleanup) OK, `downloader.py:684-714` (unlink only inside `if browser_streams:`) OK.

**Recommendation stands:** Add a `finally` block in `download_with_ytdlp_with_resume_fallback` to clean up `output_file` when returning `None`. Consider downloading to a `.part` temp file and renaming on success. Small, low-risk change.


### DF-009: Progress units are inconsistent across download methods [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory)**

**Verification:**

The `progress_callback` protocol is `Callable[[str, int, int], None]` (`downloader.py:554`, `segment_downloader.py:563`, `dtos.py:24`). Different methods pass different units:

| Method | Location | Units |
|--------|----------|-------|
| yt-dlp | `downloader.py:838` | bytes (`downloaded, total` from `_parse_ytdlp_progress`) |
| segment | `segment_downloader.py:588` | segment counts (`downloaded_count, len(segments)`) |
| ffmpeg | `downloader.py:1081` | bytes, but `downloaded == total` (always 100% -- see DF-005) |

`ProgressManager.get_formatted_progress()` (`downloader_throttle.py:127-141`) displays:

```python
f"video_{i}: {self._state.get(i, (0, 0))[0]}/{self._state.get(i, (0, 0))[1]}"
```

No unit label. For batch downloads with mixed methods (e.g., one URL via yt-dlp reporting bytes, another via segments reporting counts), the display shows inconsistent units with no disambiguation.

Documentation at `vkdownloader-overview.md:248-254` claims: `video_1: 25/100, video_2: 45/150, video_3: 78/80` with `X/Y: Downloaded segments / Total segments for that video` -- this is only true for segment downloads; yt-dlp reports bytes.

All evidence verified: `downloader_throttle.py:137-139` OK, `downloader.py:838` OK, `segment_downloader.py:588` OK, `downloader.py:1081` OK, `vkdownloader-overview.md:248-254` OK.

**Recommendation stands:** Add a unit parameter to the callback protocol, or normalize all progress to bytes. Minimum viable: add unit labels in `get_formatted_progress`. Medium effort -- callback protocol change has coordination cost across all call sites.


### DF-010: Segment files written non-atomically; partial writes corrupt resume state [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory)**

**Verification:**

Both segment download paths write directly to the final `.ts` path:

- `_download_segment_sequential()` (`segment_downloader.py:167-168`):
  ```python
  with open(output_path, "wb") as f:
      f.write(content)
  ```
- `_run_parallel_download_with_backoff()` (`segment_downloader.py:225-226`):
  ```python
  with open(output_path, "wb") as f:
      f.write(content)
  ```

No temp-file + atomic-rename pattern is used. No `fsync` or flush-before-rename.

Resume logic at `_create_segment_download_tasks()` (`segment_downloader.py:718-720`):

```python
segment_path = policy.segments_dir / f"{i:05d}.ts"
if segment_path.exists() and segment_path.stat().st_size > 0:
    logger.debug("skipping_existing_segment", idx=i)
    continue
```

If the process crashes mid-`f.write(content)`, the file is truncated but has non-zero size. On the next attempt, `st_size > 0` is `True`, so the segment is **skipped** -- treated as complete. A truncated segment is merged into the final output, producing corrupted video.

No Content-Length or byte-count verification exists anywhere in the segment download path.

All evidence verified: `segment_downloader.py:167-168` OK, `segment_downloader.py:225-226` OK, `segment_downloader.py:720` (resume check) OK.

**Recommendation stands:** Write to `{idx:05d}.ts.tmp`, verify written bytes against content length, then `os.replace(tmp, final)` for atomicity. Small, low-risk change.


### DF-011: Single download command lacks --max-retries override [APPROVED -- COMPLEMENTARY TO CFG-004]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory)**
> **Related:** CFG-004 (Phase 02) -- doc-update recommending clarification that `--max-retries` is batch-only. DF-011 recommends the implementation fix (add the flag). Complementary, not conflicting.

**Verification:**

The `download` command (`cli.py:418-445`) defines options: `url, quality, output, method, cookie_source, ssl_verify` -- **no** `--max-retries`.

The `batch` command (`cli.py:542-581`) defines `--max-retries / -r` at `cli.py:576-581`.

Users cannot override `max_retries` for single downloads via CLI -- only via `VKDOWNLOADER_MAX_RETRIES` env var (which, per DF-004, still only affects yt-dlp subprocess flags, not the app-level retry loop).

This confirms CFG-004 (Phase 02), which documents the same gap as a doc-update. CFG-004 recommends clarifying docs; DF-011 recommends adding the flag. Both are valid and complementary.

All evidence verified: `cli.py:418-444` (download command, no --max-retries) OK, `cli.py:576-581` (batch --max-retries) OK.

**Recommendation stands:** Add `--max-retries / -r` to the `download` command, mirroring the batch command. Trivial, low-risk change. Note: does not resolve CFG-004's doc-update recommendation -- that should be applied separately.


### DF-012: _attempt_segment_resume uses stale m3u8_url when BEST quality requested [APPROVED -- MERGED INTO DF-001]

> **Validation Note:**
> - **Action:** merged
> - **Detail:** DF-012 is an explicit downstream consequence of DF-001. The stale `m3u8_url` retention at `downloader.py:699-704` (else branch) is a direct symptom of the `quality_enum == QualityEnum.BEST` check failing at `downloader.py:690` because the quality string was degraded to `"1080p"` at `downloader.py:1208`. Fixing DF-001 (passing the original `QualityEnum` value `"best"` through the pipeline) causes `_parse_quality_to_enum("best")` to return `QualityEnum.BEST`, making the `if` branch at line 690 reachable and the fresh browser `m3u8_url` selected.
> - **See also:** DF-001

**Verification:**

In `_attempt_segment_resume()` (`downloader.py:677-744`):

```python
if browser_streams:                                    # line 684
    try:
        quality_enum = _parse_quality_to_enum(quality) # line 686 -- quality is "1080p" (degraded by DF-001)
        if quality_enum == QualityEnum.BEST:           # line 690 -- False (it is Q1080)
            selector = QualitySelector()
            selected_stream = selector.select(browser_streams, quality_enum)
            m3u8_url = str(selected_stream.url)         # fresh browser URL -- NEVER REACHED
            logger.info("fresh_token_obtained_for_resume", ...)
        else:                                           # line 699 -- always taken when original was BEST
            logger.info("browser_streams_selected_with_preselected_url_for_resume", ...)
            # stale m3u8_url retained (not updated to fresh browser URL)
```

The fresh browser-extracted `m3u8_url` is only selected when `quality_enum == QualityEnum.BEST` (line 690). Since DF-001 causes `quality` to be `"1080p"` (-> `Q1080`) instead of `"best"` (-> `BEST`), this branch is always skipped, and the stale `m3u8_url` from the initial yt-dlp extraction is passed to `HLSDownloadRequest` at line 719.

All evidence verified: `downloader.py:684-704` (quality check fails, stale m3u8_url retained) OK, `downloader.py:716-724` (HLSDownloadRequest uses stale m3u8_url) OK.

**Recommendation absorbed into DF-001.** No separate fix required. This is the step 5-6 in the critical failure cascade (DF-001 -> DF-012 -> DF-006).


---

## Summary (Updated by Validation)

| Severity | Original Count | After Validation | Notes |
|----------|---------------|------------------|-------|
| CRITICAL | 1 | 1 | DF-001 (unchanged) |
| HIGH | 4 | 3 | Original had 4 (DF-003, DF-006, DF-007, DF-012); DF-012 merged into DF-001 |
| MEDIUM | 6 | 7 | Original had 6 (DF-002, DF-004, DF-005, DF-008, DF-009, DF-010); DF-011 reclassified from LOW |
| LOW | 1 | 0 | DF-011 reclassified to MEDIUM (was LOW) -- CLI parity gap confirmed by CFG-004 Phase 02 |
| **Total** | **12** | **11** (10 validated + 1 merged-into-DF-001) | Original summary in findings.md said 10 (counted DF-012 as neither HIGH nor MEDIUM); actual count is 12. After validation: 11 effective findings (DF-012 absorbed into DF-001). |

Note: The original findings summary table (findings.md:239-245) undercounted -- it listed HIGH: 3 and Total: 10, but 12 findings exist (DF-012 was uncounted). The actual original counts are CRITICAL 1, HIGH 4, MEDIUM 6, LOW 1, Total 12. Validation corrects DF-011 from LOW to MEDIUM (confirmed by CFG-004 in Phase 02) and merges DF-012 into DF-001, yielding 11 effective findings.

### Mandatory Fixes

1. **DF-001 (CRITICAL, approved)** -- Fix quality enum degradation at `downloader.py:1208`. Change `str(stream.quality)` to `str(quality)` so the original `QualityEnum` value (e.g., `"best"`) flows through the pipeline. This also resolves DF-012.
2. **DF-007 (HIGH, approved)** -- Use secure file permissions (0o600) for temp cookie file at `downloader.py:87`. Add `os.chmod(path, 0o600)` or replace `tempfile.mkstemp` with `os.open` at `0o600`.

### Advisory Recommendations

1. **DF-002** -- Centralize correlation ID binding in `download_video()`.
2. **DF-003** -- Add per-segment progress callback during download.
3. **DF-004** -- Use `settings.max_retries` instead of hardcoded `MAX_RESUME_RETRIES`.
4. **DF-005** (merged with SRV-003) -- Fix FFMPEG progress adapter to report actual progress, not 100% always.
5. **DF-006** -- Remove `cookie_source != BROWSER` guard in `_refresh_token_and_retry`.
6. **DF-008** -- Clean up partial output file on download failure in `finally` block.
7. **DF-009** -- Normalize progress units or add unit labels to `ProgressManager` display.
8. **DF-010** -- Use atomic writes (temp file + rename) for segment files.
9. **DF-011** -- Add `--max-retries` to single download command for CLI parity.
10. **DF-012** -- Resolved by fixing DF-001. No separate action.
11. **Consolidation (DF-007 + SRV-002)** -- Remove dead `_write_netscape_cookie_file` and consolidate cookie-file writes through the now-secured `_create_temp_cookie_file`.
12. **Doc note (Phase 06 line 269 CookieSource.FILE)** -- DUPLICATE of CFG-003 (Phase 02). No additional doc work needed.

## Rollout Analysis

### Risks, Dependencies, and Sequencing

**Mandatory fixes (high risk):**

- **DF-001 (CRITICAL):** The quality string flows through `perform_download` (line 968), `_resolve_cookies` (line 920), `download_with_ytdlp_with_resume_fallback` (line 546), `_attempt_segment_resume` (line 639), and `HLSDownloadRequest` (dtos.py:22). All accept `quality: str` and call `_parse_quality_to_enum`. The minimal-risk fix (pass `str(quality)` instead of `str(stream.quality)` at line 1208) requires changing one line and needs no signature changes. The full type-safe fix (change `str` to `QualityEnum` across 5 functions + 1 DTO) is more invasive. **Recommended: minimal one-line fix.**
  - **Dependency:** Must be applied before DF-012 can be tested (DF-012 is downstream).
  - **Risk:** Low for the minimal fix; Medium for the full type change (could break tests that assert on `quality: str`).

- **DF-007 (HIGH):** `os.chmod(path, 0o600)` after `os.write`/`os.close` in `_create_temp_cookie_file`. The `os` module is already imported at `downloader.py:6`.
  - **Cross-dependency:** INT-001 (Phase 05) recommends routing ffmpeg cookies through `_create_temp_cookie_file` (via ffmpeg's `cookies` option). DF-007's fix must be applied alongside to avoid creating a new insecure cookie file for the ffmpeg path.
  - **Risk:** Very low -- only tightens permissions; file path semantics unchanged.

**Advisory fixes (low risk):**

- **DF-006:** Removing the `cookie_source != BROWSER` guard at `segment_downloader.py:417` makes `_refresh_token_and_retry` consistent with `_attempt_segment_resume` (downloader.py:681). Risk: low -- `force_browser=True` is already the established pattern; the guard is redundant.
- **DF-008:** Adding `finally` cleanup in `download_with_ytdlp_with_resume_fallback`. Risk: low -- only deletes partial files on failure paths.
- **DF-010:** Atomic segment writes (temp + `os.replace`). Risk: low -- `os.replace` is atomic on the same filesystem.
- **DF-002/DF-003/DF-004/DF-005/DF-009/DF-011:** All independent, low-risk changes.

**No circular dependencies** detected. All findings have linear or independent dependency chains.

## Execution Validation

All targets verified to still exist in the current codebase. No stale anchors.

| Finding | Target Location | Verified Exists | Notes |
|---------|----------------|-----------------|-------|
| DF-001 | downloader.py:1208 | Yes | `str(stream.quality)` in `download_video`. `quality` param is `QualityEnum` at line 1144. |
| DF-002 | cli.py:459 | Yes | `download` command calls `download_video` directly. `_download_single` at cli.py:219 binds correlation. |
| DF-003 | segment_downloader.py:646-699 | Yes | `_download_segment_concurrent` never calls `progress_callback`. |
| DF-004 | downloader.py:57,585 | Yes | `MAX_RESUME_RETRIES = 3` constant; loop uses it, not `settings.max_retries`. |
| DF-005 | downloader.py:1079-1083 | Yes | `_ffmpeg_progress_adapter` sets `total = downloaded = fp.total_size`. |
| DF-006 | segment_downloader.py:417-423 | Yes | `cookie_source != BROWSER` guard returns None before `force_browser=True` call. |
| DF-007 | downloader.py:87 | Yes | `tempfile.mkstemp` at default permissions. `cookies.py:72` has correct 0o600 but dead. |
| DF-008 | downloader.py:585-632, 714 | Yes | `output_file.unlink()` only inside `if browser_streams:` block. |
| DF-009 | downloader_throttle.py:137-139 | Yes | `get_formatted_progress` has no unit label. |
| DF-010 | segment_downloader.py:167-168, 225-226, 720 | Yes | Direct writes to final path; resume checks `st_size > 0` only. |
| DF-011 | cli.py:418-445 vs 576-581 | Yes | `download` command lacks `--max-retries`; `batch` has it. |

All findings remain applicable. No assumptions invalidated. No dependencies drifted. Architecture integrity intact.

## Warnings

1. **Architectural risk (DF-001):** The full type-safe fix (changing `quality: str` to `QualityEnum` across 5 functions + `HLSDownloadRequest` DTO) increases the change surface area and may break existing tests that pass `quality: str`. The minimal one-line fix (`str(quality)` at line 1208) is recommended instead.

2. **Rollout risk (DF-005 + DF-009):** Both address progress reporting. DF-005 (ffmpeg always 100%) is a subset of DF-009 (units inconsistent). The `Callable[[str, int, int], None]` protocol change proposed in DF-009 would require coordinated changes across all callers (downloader.py, segment_downloader.py, dtos.py, cli.py). Recommend addressing DF-005 first (minimal adapter fix), then DF-009 (protocol change).

3. **Dependency risk (DF-007 + INT-001):** INT-001 (Phase 05, CRITICAL) recommends replacing ffmpeg `@file` headers with ffmpeg's `cookies` file option. That fix routes cookies through `_create_temp_cookie_file` -- the exact function DF-007 flags. DF-007 and INT-001 should be implemented together to avoid creating a new cookie file with insecure permissions for the ffmpeg path.

4. **Documentation inconsistency (Phase 06 doc notes):** Two of the three "Doc Updates Needed" notes duplicate findings from earlier phases:
   - `vkdownloader-overview.md:63` (CookieSource.FILE) = duplicate of CFG-003 (Phase 02)
   - `configuration.md:112` (max_retries scope) = overlaps with CFG-004 (Phase 02) and DF-004
   Only `vkdownloader-overview.md:248-254` (progress format docs) is unique -- covered by DF-009.

5. **Pre-existing lint/format/type failures** (tracked Phase 01): `ruff format --check` fails on `services/downloader.py` (the module most DF findings target) and `mypy` fails on `utils/correlation.py:55`. These gates should be unblocked (CLI-004, CLI-005) before or alongside implementation changes.

6. **Dead code overlap (DF-007 + SRV-002):** `_write_netscape_cookie_file` (cookies.py:58-74) is the correct secure implementation (0o600) but is dead code. The fix for DF-007 should consolidate into this existing function rather than duplicating `os.open` logic.

## Required Fixes

1. **DF-001 (CRITICAL, mandatory):** At `downloader.py:1208`, change `str(stream.quality)` to `str(quality)` so the original `QualityEnum` value (e.g., `"best"`) is passed through the pipeline. The `quality` parameter is already the original `QualityEnum` at `download_video` line 1144. This restores the `== QualityEnum.BEST` branch at `downloader.py:690` and `downloader.py:944`, and automatically resolves DF-012.

2. **DF-007 (HIGH, mandatory):** In `_create_temp_cookie_file` (`downloader.py:87-95`), add `os.chmod(path, 0o600)` immediately after `os.write(fd, content.encode())` / `os.close(fd)` at lines 89-90. Alternatively, replace `tempfile.mkstemp` with `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` to match the dead `_write_netscape_cookie_file` pattern at `cookies.py:72`. The `os` module is already imported at `downloader.py:6`.

## Advisory Recommendations

1. **DF-002 (trivial):** Move `bind_correlation_id`/`clear_correlation_id` into `download_video()` try/finally (downloader.py:1142). Both single and batch paths covered.

2. **DF-003 (medium):** Invoke `progress_callback` per-segment in `_download_segment_concurrent` (segment_downloader.py:646-699). May require adding `progress_callback` to `DownloadPolicy` or invoking at `_download_segment` level.

3. **DF-004 (trivial):** Replace `MAX_RESUME_RETRIES` constant with `settings.max_retries` at `downloader.py:585`. Consider also addressing SRV-006 (Phase 03) backoff gap in the same loop.

4. **DF-005 (small-medium, merged with SRV-003):** In `_ffmpeg_progress_adapter` (`downloader.py:1079-1081`), report `downloaded=fp.total_size, total=0` (unknown total) instead of `total=downloaded`. Or derive percentage from `out_time_us`/`out_time_ms`.

5. **DF-006 (small):** Remove the `if settings.cookie_source != CookieSource.BROWSER: return None` guard in `_refresh_token_and_retry` (`segment_downloader.py:417-423`) so `force_browser=True` is reached, matching `_attempt_segment_resume` (downloader.py:681).

6. **DF-008 (small):** Add `finally` cleanup in `download_with_ytdlp_with_resume_fallback` (`downloader.py:585-632`) for partial `output_file`. Consider `.part` temp file pattern.

7. **DF-009 (medium):** Normalize progress units to bytes or add unit labels in `ProgressManager.get_formatted_progress` (`downloader_throttle.py:127-141`). Callback protocol change has coordination cost.

8. **DF-010 (small):** Write segments to `{idx:05d}.ts.tmp` and `os.replace` to final path after verifying byte count. Apply to both `_download_segment_sequential` (line 167) and `_run_parallel_download_with_backoff` (line 225).

9. **DF-011 (trivial):** Add `--max-retries / -r` option to `download` command (`cli.py:418-445`), mirroring batch at `cli.py:576-581`. Does not resolve CFG-004's doc-update recommendation.

10. **Consolidation (DF-007 + SRV-002):** Remove dead `_write_netscape_cookie_file` from `cookies.py:58-74` and its `__all__` entry; consolidate all cookie-file writes through the now-secured `_create_temp_cookie_file`.

11. **Cross-phase doc sync:** Remove duplicate doc note for `vkdownloader-overview.md:63` (covered by CFG-003). Apply DF-009's progress-format doc correction at `vkdownloader-overview.md:248-254`.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (approved, unchanged) | 10 | DF-001, DF-002, DF-003, DF-004, DF-006, DF-007, DF-008, DF-009, DF-010, DF-011 |
| Reclassified | 0 | DF-005 was already SPEC-DEVIATION; merged with SRV-003 (Phase 03) which was BEST-PRACTICE. Final type: SPEC-DEVIATION. |
| Merged | 2 | DF-012 -> DF-001 (downstream consequence); DF-005 -> SRV-003 (same root cause, different phase) |
| Rejected | 0 | -- |
| Cross-phase duplicates detected | 2 | Phase 06 doc note CookieSource.FILE = duplicate of CFG-003; DF-005 = duplicate of SRV-003 |
| Cross-phase conflicts detected | 0 | -- |

### Rejected Findings

_None._ All 12 findings are technically correct and applicable. None are stale, speculative, or unsupported.

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| DF-012 | DF-001 | DF-012 is a downstream symptom of quality-enum degradation (DF-001). The `== QualityEnum.BEST` check at `downloader.py:690` fails because quality is `"1080p"` (degraded at line 1208). Fixing DF-001 resolves DF-012 automatically. |
| DF-005 | SRV-003 (Phase 03) | Identical root cause: `_ffmpeg_progress_adapter` at `downloader.py:1079-1083` sets `total = downloaded = fp.total_size`. DF-005 (SPEC-DEVIATION) absorbs SRV-003 (BEST-PRACTICE); final type: SPEC-DEVIATION. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| DF-011 | SPEC-DEVIATION (LOW) | SPEC-DEVIATION (MEDIUM) | Severity corrected: CLI parity gap (single vs batch `--max-retries`) is confirmed by CFG-004 (Phase 02) as the same issue across phases. MEDIUM reflects the consistency/UX impact. |
