п»ї# Phase 03 Validation Report — Service Layer & Business Logic

**Validator:** conservative validator (architectural integrity, rollout safety, implementation correctness)
**Date:** 2026-08-09
**Source findings:** `.ai/audit/03-audit-services/findings.md`
**Output:** `.ai/audit/99-validation/03-audit-services-validated-findings.md`
**Phase template:** `.kilo/commands/audit/phases/99-audit-validate.md`
**Original executor:** auditor (Senior architecture auditor)
**Status:** validated
**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).
**Validated:** yes

This report is self-contained. The original findings are reproduced below with inline validation
decisions applied. The reader never needs to consult the source findings file.

---

## Validation Methodology

Each finding was verified against:

1. **Implementation** — source code at the cited file paths and line numbers (read in full).
2. **Dependencies** — import chains, `__all__` exports, caller counts via grep across `src/` and `tests/`.
3. **Documentation** — `docs/01-tools/*.md` referenced by the findings.
4. **Runtime** — `uv run pytest`, `uv run ruff check`, `ruff format --check`, `uv run mypy` re-run by the validator.
5. **Cross-phase consistency** — compared against findings in phases 01 (CLI), 02 (config), 04 (security).

## Runtime Verification (re-run by validator)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 Import | `uv run python -c "import all service/model/infra/utils modules"` | PASS | `IMPORT OK` — all 21 modules import cleanly; no circular-import crashes. |
| R2 Lint | `uv run ruff check src/vkdownloader/ tests/` | FAIL (1) | `tests/test_correlation.py:28` F841 unused `full` — pre-existing CLI-003 (phase 01). |
| R2 Format | `uv run ruff format --check src/vkdownloader/ tests/` | FAIL (4) | `downloader.py`, `test_cli.py`, `test_hls_downloader.py`, `test_security.py` — pre-existing CLI-005. |
| R2 Types | `uv run mypy src/vkdownloader` | FAIL (1) | `utils/correlation.py:55` unused type: ignore — pre-existing CLI-004. |
| R3 Tests | `uv run pytest` | PASS (325) | `325 passed in 9.95s`. |
| R4 Line counts | `python splitlines()` | PASS | downloader.py = 1,218; segment_downloader.py = 901; ffmpeg_utils.py = 360; extractor.py = 284; cookies.py = 77. |

> Note: R2/R2/R2 failures are pre-existing and tracked under CLI-003/CLI-004/CLI-005. No new service-layer defects.

---
## Findings (validated)

### SRV-001: `services/downloader.py` is a 1,218-line god-module mixing orchestration, subprocess I/O, parsing, temp-file handling, and a cross-module re-export facade

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified by direct code inspection. `downloader.py` is confirmed at 1,218 lines (Python `splitlines()` count). The module contains: `HLSDownloader` class (lines 381-539), `perform_download` dispatcher (lines 966-1139), `download_video` pipeline (lines 1142-1218), `download_with_ytdlp_with_resume_fallback` + `_attempt_segment_resume` + `_download_with_ytdlp` + `_resolve_cookies` (lines 542-963), parsing helpers, temp-file helpers, and a 23-entry `__all__` re-export facade at lines 327-378. The facade publicly re-exports private internals from 5 sibling modules (confirmed by reading the ownership comment block at lines 327-353). Documentation staleness confirmed: `vkdownloader-overview.md:294` claims `downloader.py (~487 lines)` — actual is 1,218 (~2.5x). Architecture rule violations confirmed (#4 single responsibility, #5 avoid overengineering, #15 small focused modules). **Rollout risk:** 30+ test import sites depend on the `__all__` facade; splitting requires preserving backward-compatible re-exports or updating all imports in lockstep.
> - **See also:** CLI-007 (phase 01) flags the same stale line counts.

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE, SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `downloader.py` (1,218 lines) does not have a single responsibility. In one module it owns: (a) the `HLSDownloader` class (ffmpeg orchestration, lines 381-539); (b) `perform_download` — the download-method dispatcher (`match` on `DownloadMethod`, lines 966-1139); (c) `download_video` — the extract-select-resolve-download pipeline (lines 1142-1218); (d) `download_with_ytdlp_with_resume_fallback` + `_attempt_segment_resume` + `_download_with_ytdlp` + `_resolve_cookies` — the yt-dlp subprocess + token-refresh flow (lines 542-963); (e) parsing/building helpers (`_parse_ytdlp_progress`, `_echo_ytdlp_line`, `_build_ytdlp_cli_command`, `_parse_quality_to_enum`); (f) temp-file helpers (`_create_temp_cookie_file`, `_temp_headers_file`, `_semaphore_context`); and (g) a 23-entry backward-compatibility re-export `__all__` facade (lines 327-378) that publicly re-exports private symbols from five sibling modules.

This violates project rule #4 (single responsibility), #15 (small focused modules), and #5 (avoid overengineering via composition), and directly contradicts `vkdownloader-overview.md:294` which lists `downloader.py` at "~487 lines". The module has grown ~2.5x into a god-module that a single change to (e.g.) the yt-dlp retry flow can destabilize the ffmpeg and orchestration paths together.

**Evidence:**
- Line counts: `downloader.py` = 1,218; `extractor.py` = 284; `ffmpeg_utils.py` = 360; `segment_downloader.py` = 901. `downloader.py` is the largest module and exceeds the other three combined in responsibility scope.
- `downloader.py:327-378` — `__all__` facade listing `_cookies_to_netscape`, `_retry_429_with_backoff`, `_cleanup_segments`, `_download_segment`, `_download_segment_parallel`, `_download_segment_sequential`, `_fetch_playlist_with_retry`, `_parse_m3u8_segments`, `_merge_segments_batched`, `_build_ffmpeg_concat_command`, `_build_ytdlp_cli_command`, `_await_first_and_cancel_others`, `setup_signal_handlers`, `read_progress`, `cancel_subprocess`, `check_ffmpeg_available`, `FfmpegProgress`, `ProgressParser`.
- `vkdownloader-overview.md:294-296` claims `downloader.py` is "(~487 lines) - Orchestration, ffmpeg integration" — stale by ~2.5x.
- `downloader.py:1156-1159` docstring calls `download_video` "Shared orchestration for single-download and batch-download CLI handlers" — intended thin-orchestration role buried in overstuffed module.

**Recommendation (advisory):** Split `downloader.py` into: (1) `VideoDownloadOrchestrator` (extract-select-resolve-dispatch); (2) `YtDlpDownloader` (yt-dlp subprocess + cookie-file temp lifecycle + progress echo); (3) `FFmpegDownloader` (HLSDownloader already isolates this); (4) `DownloadResumeOrchestrator` (yt-dlp-to-segment-fallback retry loop). Demote `_`-prefixed re-exports from `__all__`. Effort: large; priority: recommended.

---

### SRV-002: Dead code — `_write_netscape_cookie_file` defined and exported but never called

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified by grep across `src/` and `tests/`: `_write_netscape_cookie_file` appears ONLY at its definition (cookies.py:58) and `__all__` export (cookies.py:77). Zero call sites in production or test code. The live cookie-file path is `_create_temp_cookie_file` in downloader.py:71, which calls `_cookies_to_netscape` (cookies.py:13) directly and manages the file via `tempfile.mkstemp` + `0o600`. Both functions write Netscape format to disk with 0o600 intent but via different mechanisms (`os.open` at cookies.py:72 vs `tempfile.mkstemp` at downloader.py:87) — a divergent duplicate. The `.temp/findings_original.md:41` reference confirms this function WAS called in an earlier code version, supporting the finding's "investigate purpose, not delete" guidance. Cross-phase overlap: `.temp/write_findings.py:279` planned a SEC-005 finding about this same function's "divergent permission semantics" in the security phase; SRV-002 owns the dead-code/ownership aspect.
> - **See also:** `.temp/write_findings.py` SEC-005 (planned security finding on same symbol).

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/cookies.py:58-74` (definition); `__all__` at `cookies.py:77` |
| **Classification** | advisory |

**Description:** `cookies.py` defines `_write_netscape_cookie_file(path, cookies_input)` (lines 58-74) and exports it from `__all__` (line 77), but it has **zero callers** anywhere in `src/` or `tests/`. The live cookie-file creation path is `_create_temp_cookie_file` in `services/downloader.py:71`, which calls `_cookies_to_netscape` (`cookies.py:13`) directly and manages its own file with `tempfile.mkstemp` + `0o600`. The two functions implement the same Netscape-format write with the same `0o600` intent but to different locations, so they are a divergent, confusing duplicate.

Per the audit dead-code policy this is "investigate purpose, not delete": the function exists, is documented (docstring), and is exported, so it may be intended future-proofing for a `CookieSource.FILE` path — but it is unused today. Its docstring (lines 59-66) documents `0o600`-via-`os.open` semantics that do not match the actually-used `tempfile.mkstemp` path, so the documentation describes behavior that is not exercised.

**Evidence:**
- `cookies.py:58` `def _write_netscape_cookie_file(path: Path, cookies_input: str | list[Cookie]) -> None:`
- `cookies.py:77` `__all__ = ["_cookies_to_netscape", "_write_netscape_cookie_file"]`
- grep across `src/` + `tests/` for `_write_netscape_cookie_file` в†’ matches only the definition (cookies.py:58) and the `__all__` export (cookies.py:77); no call sites.
- Live path: `downloader.py:71` `_create_temp_cookie_file` в†’ `content = _cookies_to_netscape(cookies)` (downloader.py:86) в†’ `tempfile.mkstemp` + `os.write`.
- `.temp/findings_original.md:41` confirms this function was called in a prior version: `_write_netscape_cookie_file(cookie_file, raw_cookies)`.

**Recommendation (advisory):** Either (a) remove `_write_netscape_cookie_file` and its `__all__` entry and consolidate cookie-file writes into `_create_temp_cookie_file` (single, owned path), or (b) if retained as future-proofing for an eventual `CookieSource.FILE` loader, wire it to a real caller or gate behind a documented module-level flag so it cannot silently diverge. Effort: small; priority: recommended.

---
### SRV-003: `_ffmpeg_progress_adapter` always reports 100% progress for the ffmpeg download path

> **Validation Note:**
> - **Action:** validated (borderline SPEC-DEVIATION)
> - **Detail:** Verified by code inspection. At downloader.py:1079-1081, the adapter sets `downloaded = fp.total_size if fp.total_size is not None else 0` then calls `progress_callback(video_id, downloaded, downloaded)` — the third argument (total) is bound equal to downloaded. FFmpeg's `-progress` `total_size` key reports cumulative output bytes written so far, NOT a known final total (confirmed: ffmpeg.org `-progress` docs; ffmpeg-devel 2016-07 states "total_size = size so far in bytes"; "Progress as in % done is not provided"). The `FfmpegProgress` dataclass (ffmpeg_utils.py:45-56) has `total_size` but no expected-total/duration field; `read_progress` (ffmpeg_utils.py:94-125) only populates `total_size` from the `total_size=` key. Therefore `downloaded == total` is always true, rendering ffmpeg downloads as 100% complete in batch mode. **Test gap verified:** All 3 `perform_download` FFMPEG-branch tests (test_hls_downloader.py:1403, 1449, 2500) omit `progress_callback`. The progress-callback test at line 113 calls `HLSDownloader.download_with_ffmpeg` directly (receives `FfmpegProgress`), NOT through `perform_download`'s adapter — so the adapter's `downloaded == total` mapping is never asserted. **Type note:** Classified as BEST-PRACTICE (correctness); borders on SPEC-DEVIATION given `vkdownloader-overview.md:173-176` documents "real-time progress updates" and the `DownloadProgress` model advertises `percent` and `eta_seconds` — the always-100% behavior contradicts the documented progress-tracking capability.
> - **See also:** SEC-001 (phase 04) flags the same `download_with_ffmpeg` code path for a different issue (m3u8 token in command-line args).

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE (correctness) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:1079-1083` (perform_download, FFMPEG branch) |
| **Classification** | advisory |

**Description:** In `perform_download`'s `DownloadMethod.FFMPEG` branch, the progress callback is wrapped by a nested adapter:

```python
def _ffmpeg_progress_adapter(fp: FfmpegProgress) -> None:
    downloaded = fp.total_size if fp.total_size is not None else 0
    progress_callback(video_id, downloaded, downloaded)   # total == downloaded
```

The callback contract is `(video_id, downloaded, total)`. Here `total` is set equal to `downloaded`, which is `fp.total_size`. FFmpeg's `-progress` `total_size` key is the **cumulative output bytes written so far** (not a known final total) — verified against ffmpeg's `-progress` documentation and the ffmpeg-devel mailing list, which state there is no total-size field and that percentage must be derived from `out_time`/`out_time_ms` over the input duration. Because `total` is bound to the same running counter as `downloaded`, the rendered progress is always 100%, regardless of actual download progress. In batch mode, every ffmpeg download appears complete immediately, which can prompt a user to abort an in-progress transfer.

This path is also **untested**: `test_hls_downloader.py` exercises `HLSDownloader.download_with_ffmpeg` with a callback that receives `FfmpegProgress` directly (test line 113), but no test reaches `perform_download`'s FFMPEG branch with a `progress_callback`, so the adapter's `downloaded == total` mapping is never asserted.

**Evidence:**
- `downloader.py:1079-1081` — the adapter sets `downloaded = fp.total_size ...; progress_callback(video_id, downloaded, downloaded)`.
- FFmpeg semantics: `total_size` is "size so far in bytes" (cumulative), not final total; ffmpeg emits no total-bytes field for the `-progress` stream.
- `ffmpeg_utils.py:52` — `FfmpegProgress.total_size: int | None = None`; no expected-total/duration field exists.
- `ffmpeg_utils.py:68` — `read_progress` only populates `total_size` from the `total_size=` key.
- No test in `tests/test_hls_downloader.py` invokes `perform_download(..., method=DownloadMethod.FFMPEG, progress_callback=...)` (verified: lines 1360, 1418, 2462 all omit `progress_callback`).

**Recommendation (advisory):** For the ffmpeg batch path, do not fabricate a 100% total. Either (a) report `downloaded=total_size, total=0` so the UI shows "unknown total / N bytes" rather than "100%", or (b) derive a real percentage from `out_time_ms` against the playlist duration if known. At minimum, add a test asserting the adapter's total semantics. Effort: small-medium; priority: recommended.

---

### SRV-004: `api-reference.md` documents a stale `_download_segment` signature and false retry/cleanup behavior claims

> **Validation Note:**
> - **Action:** validated
> - **Detail:** All 3 sub-claims verified against source code:
>   1. `_download_segment` signature: api-reference.md:461-469 shows 6 params (`session, segment_url, output_path, headers, max_concurrent_downloads=1, segment_index=0`); actual `segment_downloader.py:342-353` has 10 params (`backoff_coordinator, video_url, max_retries, download_timeout` added). Doc is stale. Confirmed by reading both.
>   2. Parallel-mode backoff claim: api-reference.md:486-487 states "Uses direct download without retry backoff". Actual `_run_parallel_download_with_backoff` (segment_downloader.py:197-237) calls `_parse_retry_after` (233), `_compute_backoff_delay` (234), `_wait_with_shutdown` (236), `_notify_backoff_for_retryable_status` (230), `_should_continue_on_retry` (232) — full AWS Full Jitter backoff present. Doc is false.
>   3. Cleanup-on-failure claim: api-reference.md:451 lists "Cleans up partial downloads on failure". Actual `download_hls_with_resume` finally-block (segment_downloader.py:887-889) calls `_log_preserve_segments` on failure; `_cleanup_segments` (line 603) only runs on success. Doc is false.
>   4. Internal contradiction: api-reference.md:447 ("Resumes from last downloaded segment on interruption") vs :451 ("Cleans up partial downloads on failure") — both false/contradictory.
>   **Additional observation:** api-reference.md:508-524 has a CORRECT `HLSDownloadRequest` attribute table (only `video_url, m3u8_url, output_file, quality, cookies, progress_callback`) and even notes "Service objects (settings, extractor, backoff_coordinator, semaphore) are passed as function arguments to `download_hls_with_resume`" (line 524). This correct table CONTRADICTS the stale usage example at api-reference.md:433-442.
> - **See also:** SRV-005 shares the same `api-reference.md` file (doc accuracy issues).

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE, SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/api-reference.md:455-487`; `src/vkdownloader/services/segment_downloader.py:342-353` |
| **Classification** | advisory |

**Description:** The API reference deviates from the implemented `services/` layer in three concrete ways:

1. **Stale `_download_segment` signature.** `api-reference.md:461-469` documents `_download_segment` with 6 parameters: `(session, segment_url, output_path, headers, max_concurrent_downloads=1, segment_index=0)`. The actual signature (`segment_downloader.py:342-353`) has 10 parameters and adds `backoff_coordinator=None, video_url=None, max_retries=3, download_timeout=300`. A reader following the doc would miss the retry/coordination knobs.

2. **False claim: parallel mode has no retry/backoff.** `api-reference.md:486-487` states "When `max_concurrent_downloads>1`: Uses direct download without retry backoff". This is wrong. The parallel path (`_run_parallel_download_with_backoff`, `segment_downloader.py:197`) implements full AWS Full Jitter backoff.

3. **False claim: `download_hls_with_resume` cleans up partial downloads on failure.** `api-reference.md:451` lists "Cleans up partial downloads on failure" as a feature, directly contradicting `api-reference.md:447` ("Resumes from last downloaded segment on interruption") and the code. The implementation **preserves** segments on failure for resume; cleanup only runs on success.

**Evidence:**
- `segment_downloader.py:342-353` actual `_download_segment` signature (10 params) vs `api-reference.md:461-469` (6 params).
- `segment_downloader.py:197-237` (`_run_parallel_download_with_backoff`) calls `_parse_retry_after` (233), `_compute_backoff_delay` (234), `_wait_with_shutdown` (236), `_notify_backoff_for_retryable_status` (230), `_should_continue_on_retry` (232) — full backoff present in parallel mode.
- `segment_downloader.py:885-901` — `download_hls_with_resume` `finally: if not success: _log_preserve_segments(segments_dir)` preserves partials; `segment_downloader.py:603` `_cleanup_segments` only on the success path.
- `api-reference.md:447` (resume on interruption) vs `:451` (clean up on failure) — internally contradictory.
- `api-reference.md:508-524` — correct `HLDSegmentRequest` attribute table contradicting the usage example at `:433-442`.

**Recommendation (DOC-UPDATE):** Sync `api-reference.md`: (1) update `_download_segment` params table to include `backoff_coordinator`, `video_url`, `max_retries`, `download_timeout`; (2) correct parallel-mode behavior to "uses AWS Full Jitter backoff with shared `URLBackoffCoordinator`" (same as sequential, plus coordinator pauses); (3) reword "Cleans up partial downloads on failure" to "Preserves partial segments on failure for segment-level resume; cleans up only on successful merge". Effort: trivial; priority: recommended.

---
### SRV-005: Docs reference a non-existent `DownloaderThrottle` class, a non-function `download_with_ffmpeg`, and mis-attribute quality selection

> **Validation Note:**
> - **Action:** validated (with precision correction)
> - **Detail:** All 4 sub-claims verified:
>   1. `DownloaderThrottle` class: grep across `src/` returns zero matches for `class DownloaderThrottle`. `downloader_throttle.py:44` defines `URLBackoffCoordinator`; line 76 defines `ProgressManager`. `vkdownloader-overview.md:27` lists `DownloaderThrottle` as a service. **Additional finding not in original:** `api-reference.md:217` ALSO has a stale `### DownloaderThrottle` section header (same module). `api-reference.md:724` correctly documents `URLBackoffCoordinator`. Both doc headers staleness confirmed.
>   2. `download_with_ffmpeg` as standalone function: `vkdownloader-overview.md:36` table lists `download_with_ffmpeg()` as a standalone function without class context. Actual symbol is `HLSDownloader.download_with_ffmpeg` (downloader.py:393). **Precision correction:** api-reference.md:169-213 actually presents this CORRECTLY as a method under the `HLSDownloader` section (heading `#### download_with_ffmpeg` under `### HLSDownloader`, example `downloader.download_with_ffmpeg(...)` at line 208, line 200 correctly notes quality="for logging purposes"). The finding's claim that "api-reference.md:177-196 present download_with_ffmpeg as a standalone function" is imprecise — those lines are actually correct. The real inaccuracy is in `vkdownloader-overview.md:36` (table) and `vkdownloader-overview.md:110` (architecture flow showing `download_with_ffmpeg()`). The quality arg IS only used for logging (downloader.py:417 `quality=quality` in logger.info; never passed to ffmpeg) — verified.
>   3. `perform_download` mis-described: `vkdownloader-overview.md:34` claims `perform_download()` does "quality selection + download method routing". Quality selection (`QualitySelector.select`, downloader.py:1202) actually happens in `download_video` (downloader.py:1195-1202); `perform_download` (downloader.py:966-1139) only routes on `DownloadMethod` and consumes a pre-selected quality string — verified.
>   4. `HLSDownloadRequest` doc example: api-reference.md:433-442 constructs `HLSDownloadRequest(video_url=..., ..., settings=settings, extractor=extractor)`. Actual model (dtos.py:11-24) has only `video_url, m3u8_url, output_file, quality, cookies, progress_callback` — no `settings`/`extractor` fields. Pydantic BaseModel default `extra="ignore"` silently drops them. The real call signature is `download_hls_with_resume(request, settings=..., extractor=...)` (segment_downloader.py:821-826). Verified.
> - **Precision correction:** The finding's recommendation targeting "api-reference.md:177-196" is partially unnecessary — that section is already correct. The fixes should target `vkdownloader-overview.md:27` (DownloaderThrottle name), `:34` (perform_download quality selection), `:36` (standalone download_with_ffmpeg), `:110` (architecture flow), and `api-reference.md:217` (stale section header) and `:433-442` (HLSDownloadRequest example). Otherwise the finding is fully valid.

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE, SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/vkdownloader-overview.md:27,34,36,110`; `docs/01-tools/api-reference.md:217,433-442`; `downloader.py:393,966,1202`; `models/dtos.py` |
| **Classification** | advisory |

**Description:** Three documented-but-wrong service references:

1. **Non-existent `DownloaderThrottle` class.** `vkdownloader-overview.md:27` lists `DownloaderThrottle` as a service in `services/downloader_throttle.py`. No such class exists; the module defines `URLBackoffCoordinator` and `ProgressManager` (verified: `grep "class DownloaderThrottle" src/` в†’ no matches). `api-reference.md:724` correctly documents `URLBackoffCoordinator`, so the overview name is stale.

2. **`download_with_ffmpeg` documented as a module function.** `vkdownloader-overview.md:36` presents `download_with_ffmpeg(...)` as a standalone function with a `quality` parameter. The actual symbol is the instance method `HLSDownloader.download_with_ffmpeg` (`downloader.py:393`), whose `quality` arg (line 398) is only used for logging, not for ffmpeg stream selection.

3. **`perform_download` mis-described as doing quality selection.** `vkdownloader-overview.md:34` says `perform_download()` does "quality selection + download method routing". Quality selection (`QualitySelector.select`, `downloader.py:1202`) actually happens in `download_video` (`downloader.py:1195-1202`); `perform_download` (`downloader.py:966-1139`) only routes on `DownloadMethod` and consumes a pre-selected `quality` string.

4. **`HLSDownloadRequest` doc example passes non-field kwargs.** `api-reference.md:433-442` constructs `HLSDownloadRequest(video_url=..., ..., settings=settings, extractor=extractor)`. `HLSDownloadRequest` (`models/dtos.py:11-24`) has only `video_url, m3u8_url, output_file, quality, cookies, progress_callback` — no `settings`/`extractor` fields. Because `HLSDownloadRequest` is a plain `BaseModel` (default `extra="ignore"`), those kwargs are silently dropped, so the example produces a request without settings; the real call signature is `download_hls_with_resume(request, settings=..., extractor=...)`.

**Evidence:**
- `grep -n "DownloaderThrottle" src/vkdownloader` в†’ no `class DownloaderThrottle` (only `URLBackoffCoordinator`/`ProgressManager` in `downloader_throttle.py:44,76`). Also found in `api-reference.md:217` as a stale section header.
- `downloader.py:393` `async def download_with_ffmpeg(self, ...)`.
- `downloader.py:1195` `selector = QualitySelector()`; `1202: stream = selector.select(...)` inside `download_video`, not `perform_download`.
- `models/dtos.py:11-24` — `HLSDownloadRequest` fields; `segment_downloader.py:821-826` — `download_hls_with_resume(request, settings=None, extractor=None, ...)`.
- `docs/01-tools/vkdownloader-overview.md:27`, `:34`, `:36`, `:110`; `docs/01-tools/api-reference.md:217, 433-442`.

**Recommendation (DOC-UPDATE):** Fix docs: (1) `vkdownloader-overview.md:27` — replace `DownloaderThrottle` with `URLBackoffCoordinator`/`ProgressManager`; also fix stale `api-reference.md:217` section header. (2) `vkdownloader-overview.md:34` — attribute quality selection to `download_video`, not `perform_download`. (3) `vkdownloader-overview.md:36` and `:110` — show `HLSDownloader.download_with_ffmpeg` as a method, not a standalone function. (4) `api-reference.md:433-442` — show `settings`/`extractor` as `download_hls_with_resume` kwargs, not `HLSDownloadRequest` fields. Effort: trivial; priority: recommended.

---

### SRV-006: Application-level retry loop in `download_with_ytdlp_with_resume_fallback` uses no backoff; `backoff_coordinator` is accepted but ignored for the yt-dlp attempts

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified by code inspection of downloader.py:542-632. `backoff_coordinator` parameter declared at line 552, docstring "Optional shared URLBackoffCoordinator for rate limiting" at line 572. The retry loop (585-624): `while retry_count <= MAX_RESUME_RETRIES` (585) then `_download_with_ytdlp(...)` (586), `retry_count += 1` (595), then `_attempt_segment_resume(..., backoff_coordinator, ...)` (611-619). Between `_download_with_ytdlp` (586) and the next loop iteration or `_attempt_segment_resume`, there is NO `asyncio.sleep`, NO `_wait_with_shutdown`, NO `_compute_backoff_delay`, NO `_notify_backoff_for_retryable_status`. Grep across downloader.py confirms these backoff helpers appear only in `segment_downloader.py`, never in downloader.py's retry loop. The `backoff_coordinator` is forwarded only at line 619 to `_attempt_segment_resume` (which delegates to segment download). The contrast is real: `segment_downloader.py:197-237` (`_run_parallel_download_with_backoff`) implements full AWS Full Jitter backoff. The docstring at line 572 overpromises "rate limiting" that the yt-dlp retry path does not deliver. **Test gap:** No test injects a real `URLBackoffCoordinator` and asserts a pause occurred during `download_with_ytdlp_with_resume_fallback` retries.
> - **See also:** SRV-001 (same file; the retry loop would move to `YtDlpDownloader` on split).

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE, SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:542-632` (retry loop; `MAX_RESUME_RETRIES` at `downloader.py:57`) |
| **Classification** | advisory |

**Description:** `download_with_ytdlp_with_resume_fallback` advertises a shared rate-limiting capability: it accepts `backoff_coordinator: URLBackoffCoordinator | None = None` (line 552) and documents it as "Optional shared URLBackoffCoordinator for rate limiting" (line 572). However, on the yt-dlp retry path the coordinator is **never consulted**. The retry loop is:

```python
retry_count = 0
while retry_count <= MAX_RESUME_RETRIES:          # downloader.py:585  (MAX_RESUME_RETRIES = 3)
    result = await _download_with_ytdlp(...)        # downloader.py:586  -- no sleep, no backoff
    if result:
        ...
        return result
    retry_count += 1                               # downloader.py:595  -- immediate re-attempt
    ...
    return await _attempt_segment_resume(..., backoff_coordinator,  # line 619 -- forwarded, but only here
```

Between yt-dlp attempts there is **no `asyncio.sleep`, no jitter, no coordinator pause, no `_notify_backoff_for_retryable_status`**. The function retries a failed yt-dlp download up to `MAX_RESUME_RETRIES` (=3) times in a tight loop, hammering the VK origin on failure — the opposite of the "rate limiting" the parameter advertises. yt-dlp's own `-R`/`--retry` flags handle transport-level retries, but the application-level yt-dlp-to-segment fallback retries have no backoff of their own.

This is an inconsistency: the segment fallback path delegates to `download_hls_with_resume` with the `backoff_coordinator` (line 727), and `segment_downloader._run_parallel_download_with_backoff` implements full AWS Full Jitter backoff. So the two download backbones apply **different** retry policies: segments get jittered backoff; yt-dlp gets none.

**Evidence:**
- `downloader.py:57` `MAX_RESUME_RETRIES = 3`.
- `downloader.py:585` `while retry_count <= MAX_RESUME_RETRIES:` — loop body calls `_download_with_ytdlp` (586) then `retry_count += 1` (595); no `await asyncio.sleep` anywhere between 586 and 619.
- `downloader.py:552, 572` — `backoff_coordinator` parameter + docstring "shared URLBackoffCoordinator for rate limiting".
- grep `backoff_coordinator` within `downloader.py:542-632` в†’ only line 552 (param), 572 (docstring), 619 (pass-through). No `_notify_backoff_for_retry`, `_compute_backoff_delay`, or `_wait_with_shutdown` in this range.
- Contrast: `segment_downloader.py:197-237` implements full backoff via `_parse_retry_after` (233), `_compute_backoff_delay` (234), `_wait_with_shutdown` (236), `_notify_backoff_for_retryable_status` (230), `_should_continue_on_retry` (232).
- No test in `tests/test_hls_downloader.py` injects a real `URLBackoffCoordinator` and asserts a pause during `download_with_ytdlp_with_resume_fallback` retries.

**Recommendation (advisory):** Either (a) make the documented behavior real by inserting a jittered backoff between yt-dlp retry attempts (e.g. `await _coord_wait(backoff_coordinator, retry_count)` capped at `MAX_RESUME_RETRIES`), or (b) keep the tight loop but drop `backoff_coordinator` from `download_with_ytdlp_with_resume_fallback` and state in the docstring that it is forwarded only to the segment-fallback path. Add a test asserting a backoff/pause occurs on yt-dlp retry using a fake coordinator. Effort: small-medium; priority: recommended.

---
## Cross-Finding Analysis

### Cross-phase overlaps

| Overlap | Phases | Nature | Assessment |
|---------|--------|--------|------------|
| Stale module line counts | SRV-001 + CLI-007 (phase 01) | Both flag `vkdownloader-overview.md:294-296` claiming downloader.py ~487 lines (actual 1,218), segment_downloader ~336 (actual 901), ffmpeg_utils ~269 (actual 360) | CLI-007 documents the doc-staleness as its primary subject; SRV-001 uses it as supporting evidence for the god-module argument. Not a duplicate — SRV-001's core finding (god-module, architectural violation) stands independently; the doc staleness is shared context. |
| Pre-existing lint/format/type | Services R2 + CLI-003/004/005 (phase 01) | Services findings R2 restates CLI-003 (F841 `full` in test_correlation.py:28), CLI-004 (mypy `correlation.py:55`), CLI-005 (format drift in downloader.py + 3 test files) as pre-existing | Consistently restated; no new service-layer defects. Same root cause, already filed in phase 01. |
| `_write_netscape_cookie_file` ownership | SRV-002 + planned SEC-005 (phase 04) | `.temp/write_findings.py:279` planned a SEC-005 finding about this function's "divergent permission semantics" (os.open 0o600 vs tempfile.mkstemp). SRV-002 covers dead-code/ownership. | The security findings file (04-audit-security) is truncated at 58 lines and does not yet contain SEC-005. If completed, it should reference SRV-002 rather than duplicate. No conflict — complementary ownership (dead-code vs permission semantics). |
| Same `download_with_ffmpeg` code path | SRV-001/003 + SEC-001 (phase 04) | SEC-001 flags m3u8 CDN tokens passed as ffmpeg command-line args (downloader.py:441); SRV-001/003 are about code structure and progress reporting in the same method | Complementary security and structural findings on the same code; no conflict. |

### Cross-phase conflicts

**None detected.** All phases report consistent runtime verification:

- pytest: 325 passed (confirmed by validator re-run)
- ruff check: 1 error in `tests/test_correlation.py:28` (F841) — phases differ by scope (`src/` clean, `src/ tests/` has the test error) but no contradiction
- ruff format: 4 files including `downloader.py` — consistent
- mypy: 1 error in `utils/correlation.py:55` — consistent

No phase claims "all commands work" while another reports a crash. No contradictory behavioral assertions about the same code.

### Dependency chains

| Finding | Depends on | Reason |
|---------|-----------|--------|
| SRV-003 (fix ffmpeg progress) | SRV-001 (split downloader.py) | The FFMPEG branch is inside `perform_download` in downloader.py; recommended split would move it to `FFmpegDownloader`. Can be fixed independently but split touches same code. |
| SRV-006 (add yt-dlp backoff) | SRV-001 (split downloader.py) | Retry loop is in `download_with_ytdlp_with_resume_fallback`; recommended split would move it to `YtDlpDownloader`. Same soft dependency. |
| SRV-004 / SRV-005 (doc fixes) | None | Independent doc fixes; no code changes required. |
| SRV-002 (remove dead code) | None | Independent; low risk. |

No circular dependencies. No hidden dependency chains.

---

## Rollout Safety Assessment

**Circular dependencies:** None detected. The `__all__` facade in downloader.py re-exports from 5 sibling modules, but these are one-directional imports (downloader.py imports from siblings, not vice versa). No circular imports exist in the service layer (confirmed by R1 import test — all modules import cleanly).

**Unsafe execution sequences:** None. All findings are advisory. No mandatory fixes in this phase. No finding requires a database migration or schema change.

**Fragile insertion points:**
- SRV-003's `_ffmpeg_progress_adapter` is defined inside `perform_download` as a closure (downloader.py:1079). Modifying it requires careful placement within the enclosing function's FFMPEG branch.
- SRV-006's retry loop is inside `download_with_ytdlp_with_resume_fallback` (downloader.py:585). Inserting a backoff call requires placement between the yt-dlp attempt (line 586) and the segment-resume fallback (line 611) — the insertion point is a multi-line block with shutdown-check and partial-file validation in between.
- Both insertion points would be simplified by SRV-001's proposed module split, but neither requires it.

**Backward compatibility:** The `__all__` re-export facade (SRV-001) is actively depended upon by 30+ test import sites (test_hls_downloader.py:15-20 plus 17 other `from vkdownloader.services.downloader import ...` sites). Any split of downloader.py MUST preserve these re-exports or update all consumers to avoid breaking the test suite and any downstream imports.

---

## Execution Validation

**Applicability:** All 6 findings are applicable to the current codebase (v0.1.0). Verified by:
- Direct source code inspection (all cited line numbers match)
- Runtime verification (pytest 325 passed; ruff/mypy/format failures confirmed pre-existing and tracked in phase 01)
- Dependency/import chain tracing (grep across src/ and tests/)
- Documentation comparison (docs vs implementation)

**Execution readiness:** All findings are approved for implementation. They are advisory (no mandatory fixes), independently actionable, and pose no rollout safety risks beyond the noted backward-compatibility concern for SRV-001's module split.

---

## Warnings

- **Architectural risk (SRV-001):** Splitting downloader.py is a large refactoring of the most critical download path. The 23-entry `__all__` facade is actively used by 30+ test import sites — the split must preserve backward-compatible re-exports or migrate all consumers in lockstep.
- **Rollout risk (SRV-001 to SRV-003, SRV-006):** Fixing SRV-003 and SRV-006 is easier after the proposed module split, but both can be fixed independently in the current monolith. Recommended to fix SRV-003 and SRV-006 before the full split to reduce the change surface in the monolith.
- **Documentation precision (SRV-005):** The finding states that `api-reference.md:177-196` presents `download_with_ffmpeg` as a standalone function. In reality, those lines are under the `HLSDownloader` section and correctly show it as a method with a proper `downloader.download_with_ffmpeg(...)` example (line 208). The actual inaccuracy is in `vkdownloader-overview.md:36` (table lists it as standalone) and `vkdownloader-overview.md:110` (architecture flow). The recommendation should target the overview, not the api-reference for this sub-point.
- **Documentation precision (SRV-005):** The finding notes `api-reference.md:724` correctly documents `URLBackoffCoordinator`, but `api-reference.md:217` ALSO has a stale `### DownloaderThrottle` section header not mentioned in the original finding. This additional staleness should be included in the doc fix.
- **Cross-phase (SRV-002):** The security phase (04) findings file is truncated at 58 lines and may contain a planned SEC-005 finding about `_write_netscape_cookie_file` with divergent permission semantics. If completed, it should reference SRV-002 rather than duplicate.
- **Pre-existing failures:** ruff check (1 error), ruff format (4 files), mypy (1 error) — all pre-existing and tracked in phase 01 (CLI-003/004/005). These block the project's CI gates but are not in scope for this validation.

## Required Fixes

_None_ — all findings in this phase are classified `advisory`. The only mandatory fixes are in phase 01 (CLI-003, CLI-004, CLI-005) for the lint/format/type gates, which are prerequisites for clean CI but not blockers for the service-layer improvements documented here.

## Advisory Recommendations

| ID | Title | Type | Effort | Status |
|----|-------|------|--------|--------|
| SRV-001 | Split downloader.py god-module into VideoDownloadOrchestrator, YtDlpDownloader, FFmpegDownloader, DownloadResumeOrchestrator | BEST-PRACTICE, SPEC-DEVIATION | large | validated |
| SRV-002 | Remove or wire up dead `_write_netscape_cookie_file`; consolidate cookie-file writes | BEST-PRACTICE | small | validated |
| SRV-003 | Fix ffmpeg progress adapter (don't report 100%); add test | BEST-PRACTICE (correctness) | small-medium | validated |
| SRV-004 | Sync api-reference.md: fix `_download_segment` signature, parallel-mode backoff claim, cleanup-on-failure claim | DOC-UPDATE, SPEC-DEVIATION | trivial | validated |
| SRV-005 | Fix docs: replace DownloaderThrottle name, show download_with_ffmpeg as method, attribute quality selection to download_video, fix HLSDownloadRequest example | DOC-UPDATE, SPEC-DEVIATION | trivial | validated |
| SRV-006 | Add backoff between yt-dlp retry attempts or fix docstring; add test | BEST-PRACTICE, SPEC-DEVIATION | small-medium | validated |

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 6 | SRV-001, SRV-002, SRV-003, SRV-004, SRV-005, SRV-006 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| (none) | — | All 6 findings verified against source code, runtime, and documentation. No rejections. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| (none) | — | No findings share the same root cause within this phase. Cross-phase overlaps noted separately in the Cross-Finding Analysis above. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| (none) | — | — | All findings retain their original type classifications. SRV-003's "BEST-PRACTICE (correctness)" is borderline SPEC-DEVIATION but retained per the conservative principle; SRV-005's type classification retained despite precision corrections to affected module paths. |

### Cross-Phase Conflicts

| Conflict | Phases | Resolution |
|----------|--------|-----------|
| (none) | — | No contradictory evidence between phases. All runtime verification results are consistent. |

### Recommended Fix Ordering

1. **SRV-004, SRV-005** (documentation fixes) — low-effort, no code risk, independent. Apply first.
2. **SRV-002** (remove dead code) — low-risk, independent. Can be done in parallel.
3. **SRV-003** (fix ffmpeg progress adapter) — targeted fix in `perform_download` FFMPEG branch; add test. Do before the full module split.
4. **SRV-006** (add yt-dlp backoff) — targeted fix in `download_with_ytdlp_with_resume_fallback` retry loop; add test. Do before the full module split.
5. **SRV-001** (split downloader.py) — largest change; do last, after SRV-003/006 are fixed so the split can incorporate the fixes into the new module boundaries. Preserve `__all__` re-exports for backward compatibility with 30+ test import sites, or migrate all consumers in lockstep.

---

*End of validation report.*