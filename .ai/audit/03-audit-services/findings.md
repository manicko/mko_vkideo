# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** auditor (Senior architecture auditor)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/03-audit-services.md
**Status:** complete
**Validated:** no
**Problems-only:** yes (passing checks are omitted per phase output mode)
**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).
Service surface audited: `src/vkdownloader/services/` (`cookies`, `concurrency`, `downloader`, `downloader_throttle`, `extractor`, `ffmpeg_utils`, `quality`, `segment_downloader`, `signal_handlers`), the supporting models (`models/`), infrastructure (`infrastructure/`), and utils consumed by services (`utils/security`, `utils/url_sanitizer`, `utils/correlation`).

## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 — Import | `uv run python -c "import vkdownloader.services.{downloader,extractor,ffmpeg_utils,quality,segment_downloader,cookies,signal_handlers,downloader_throttle,concurrency}; import vkdownloader.models.{dtos,enums,video}; import vkdownloader.infrastructure.{browser,network_monitor}; import vkdownloader.utils.{security,url_sanitizer,correlation}"` | PASS | All service modules import cleanly; no import-time errors / circular-import crashes. |
| R2 — Lint | `uv run ruff check src/vkdownloader/ tests/` | FAIL | 1 error in app scope: `tests/test_correlation.py:28` F841 unused `full` (pre-existing; tracked as CLI-003 in phase 01). The repo-wide `ruff check` also fails on stray `.temp/*.py` and `.ai/builders/back/*.py` tooling files (no `[tool.ruff] exclude`) — tracked as CLI-003. |
| R2 — Format | `uv run ruff format --check src/vkdownloader/ tests/` | FAIL | 4 files would reformat: `services/downloader.py` (production service), `tests/test_cli.py`, `tests/test_hls_downloader.py`, `tests/test_security.py` — pre-existing, tracked as CLI-005 in phase 01. `cli.py` itself is clean. |
| R2 — Types | `uv run mypy src/vkdownloader` | FAIL | 1 error: `utils/correlation.py:55` unused `type: ignore` (pre-existing; tracked as CLI-004 in phase 01). Service modules themselves are type-clean; the only failure is the `utils/correlation` dependency imported by the service layer. |
| R3 — Tests | `uv run pytest` | PASS | 325 passed (incl. `test_hls_downloader.py`, `test_downloader_throttle.py`, `test_segment_downloader.py`, `test_extractor.py`, `test_quality_selector.py`). |
| R4 — Dead code | grep each service symbol's definition vs. callers in `src/` and `tests/` | See SRV-002 | `_write_netscape_cookie_file` (`services/cookies.py:58`) is defined + exported in `__all__` but has zero callers in `src/` or `tests/`; the live cookie-file path is `_create_temp_cookie_file` in `services/downloader.py`. All other service-layer functions have production callers (verified via import-chain trace). |

> Note: R2/R2 lint/format/type failures are pre-existing and already recorded under phase-01 findings CLI-003/CLI-004/CLI-005. They are restated here only because they sit in modules the service layer depends on (`utils/correlation`) or are the service under audit (`services/downloader.py`). No *new* service-layer lint/type defects were introduced.

---

## Findings

### SRV-001: `services/downloader.py` is a 1,218-line god-module mixing orchestration, subprocess I/O, parsing, temp-file handling, and a cross-module re-export facade

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE, SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `downloader.py` (1,218 lines — see discovery note below) does not have a single responsibility. In one module it owns: (a) the `HLSDownloader` class (ffmpeg orchestration, lines 381-539); (b) `perform_download` — the download-method dispatcher (`match` on `DownloadMethod`, lines 966-1139); (c) `download_video` — the extract→select→resolve→download pipeline (lines 1142-1218); (d) `download_with_ytdlp_with_resume_fallback` + `_attempt_segment_resume` + `_download_with_ytdlp` + `_resolve_cookies` — the yt-dlp subprocess + token-refresh flow (lines 542-963); (e) parsing/building helpers (`_parse_ytdlp_progress`, `_echo_ytdlp_line`, `_build_ytdlp_cli_command`, `_parse_quality_to_enum`); (f) temp-file helpers (`_create_temp_cookie_file`, `_temp_headers_file`, `_semaphore_context`); and (g) a 23-entry backward-compatibility re-export `__all__` facade (lines 327-378) that publicly re-exports private symbols from five sibling modules.

This violates project rule #4 (single responsibility), #15 (small focused modules), and #5 (avoid overengineering via composition), and directly contradicts the architecture doc `docs/01-tools/vkdownloader-overview.md:294` which lists `downloader.py` at "~487 lines". The module has grown ~2.5x that documented size into a god-module that a single change to (e.g.) the yt-dlp retry flow can destabilize the ffmpeg and orchestration paths together.

**Evidence:**
- Line counts: `downloader.py` = 1,218 lines (`services/extractor.py` = 284, `ffmpeg_utils.py` = 360, `segment_downloader.py` = 901). `downloader.py` is the largest module and exceeds `extractor.py`+`ffmpeg_utils.py`+`segment_downloader.py` combined in responsibility scope despite being a sibling, not a wrapper.
- `downloader.py:327-378` — `__all__` re-export facade listing `_cookies_to_netscape`, `_retry_429_with_backoff`, `_cleanup_segments`, `_download_segment`, `_download_segment_parallel`, `_download_segment_sequential`, `_fetch_playlist_with_retry`, `_parse_m3u8_segments`, `_merge_segments_batched`, `_build_ffmpeg_concat_command`, `_build_ytdlp_cli_command`, `_await_first_and_cancel_others`, `setup_signal_handlers`, `read_progress`, `cancel_subprocess`, `check_ffmpeg_available`, `FfmpegProgress`, `ProgressParser` — i.e. it publicly aliases internals from `cookies.py`, `downloader_throttle.py`, `segment_downloader.py`, `ffmpeg_utils.py`, `signal_handlers.py`.
- `docs/01-tools/vkdownloader-overview.md:294-296` claims `downloader.py` is "(~487 lines) - Orchestration, ffmpeg integration" — stale by ~2.5x.
- `downloader.py:1156-1159` docstring already calls `download_video` "Shared orchestration for single-download and batch-download CLI handlers", confirming the intended thin-orchestration role is now buried inside an overstuffed module rather than isolated behind a stable service boundary.

**Recommendation (advisory):** Split `downloader.py` into intent-named, single-responsibility units: (1) a `VideoDownloadOrchestrator` (extract→select→resolve→dispatch, i.e. today's `download_video`); (2) a `YtDlpDownloader` (yt-dlp subprocess + cookie-file temp lifecycle + progress echo); (3) an `FFmpegDownloader` (`HLSDownloader` already isolates this); (4) a `DownloadResumeOrchestrator` (the yt-dlp→segment-fallback retry loop). Demote the `_`-prefixed re-exports from `__all__`: either make the aliased symbols stable public names in their owning modules, or stop re-exporting private internals so sibling refactors don't break the facade. Effort: large; priority: recommended.

### SRV-002: Dead code — `_write_netscape_cookie_file` defined and exported but never called

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/cookies.py:58-74` (definition); `__all__` at `cookies.py:77` |
| **Classification** | advisory |

**Description:** `cookies.py` defines `_write_netscape_cookie_file(path, cookies_input)` (lines 58-74) and exports it from `__all__` (line 77), but it has **zero callers** anywhere in `src/` or `tests/`. The live cookie-file creation path is `_create_temp_cookie_file` in `services/downloader.py:71`, which calls `_cookies_to_netscape` (`cookies.py:13`) directly and manages its own file with `tempfile.mkstemp` + `0o600`. The two functions implement the same Netscape-format write with the same `0o600` intent but to different locations, so they are a divergent, confusing duplicate.

Per the audit dead-code policy this is a "investigate purpose, not delete" finding: the function exists, is documented (docstring), and is exported, so it may be intended future-proofing for a `CookieSource.FILE` path — but it is unused today and its docstring (lines 59-66) documents `0o600`-via-`os.open` semantics that do not match the actually-used `tempfile.mkstemp` path, so the documentation describes behavior that is not exercised.

**Evidence:**
- `services/cookies.py:58` `def _write_netscape_cookie_file(path: Path, cookies_input: str | list[Cookie]) -> None:`
- `services/cookies.py:77` `__all__ = ["_cookies_to_netscape", "_write_netscape_cookie_file"]`
- grep across `src/` + `tests/` for `_write_netscape_cookie_file` → matches only the definition (cookies.py:58) and the `__all__` export (cookies.py:77); no call sites.
- Live path: `services/downloader.py:71` `_create_temp_cookie_file` → `content = _cookies_to_netscape(cookies)` (`downloader.py:86`) → `tempfile.mkstemp(..., )` + `os.write`. (Note: the security phase separately flags that `_cookies_to_netscape` does not strip CRLF — ownership of the security angle is retained there; this finding is purely the dead-code/ownership issue.)

**Recommendation (advisory):** Either (a) remove `_write_netscape_cookie_file` and its `__all__` entry and consolidate cookie-file writes into `_create_temp_cookie_file` (single, owned path), or (b) if it is retained as future-proofing for an eventual `CookieSource.FILE` loader, wire it to a real caller or gate it behind a documented module-level flag so it cannot silently diverge from the live path. Effort: small; priority: recommended.

### SRV-003: `_ffmpeg_progress_adapter` always reports 100% progress for the ffmpeg download path

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE (correctness) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:1079-1083` (`perform_download`, FFMPEG branch) |
| **Classification** | advisory |

**Description:** In `perform_download`'s `DownloadMethod.FFMPEG` branch, the progress callback is wrapped by a nested adapter:

```python
def _ffmpeg_progress_adapter(fp: FfmpegProgress) -> None:
    downloaded = fp.total_size if fp.total_size is not None else 0
    progress_callback(video_id, downloaded, downloaded)   # total == downloaded
```

The callback contract is `(video_id, downloaded, total)`. Here `total` is set equal to `downloaded`, which is `fp.total_size`. ffmpeg's `-progress` `total_size` key is the **cumulative output bytes written so far** (not a known final total) — verified against ffmpeg's `-progress` documentation and the ffmpeg-devel mailing list, which state there is no total-size field and that percentage must be derived from `out_time`/`out_time_ms` over the input duration. Because `total` is bound to the same running counter as `downloaded`, the rendered progress `video_N: {total_size}/{total_size}` is always 100%, regardless of actual download progress. In batch mode (`cli.py` feeds a real `progress_callback` for `FFMPEG`/`auto` with `--method ffmpeg`), every ffmpeg download appears complete immediately, which can prompt a user to abort an in-progress transfer.

This path is also **untested**: `test_hls_downloader.py` exercises `HLSDownloader.download_with_ffmpeg` with a callback that receives `FfmpegProgress` directly (test line 113), but no test reaches `perform_download`'s FFMPEG branch with a `progress_callback`, so the adapter's `downloaded == total` mapping is never asserted.

**Evidence:**
- `src/vkdownloader/services/downloader.py:1075-1083` — the adapter sets `downloaded = fp.total_size ...; progress_callback(video_id, downloaded, downloaded)`.
- ffmpeg semantics: `total_size` is "size so far in bytes" (cumulative), not final total; ffmpeg emits no total-bytes field for the `-progress` stream (ffmpeg.org `-progress url`; ffmpeg-devel 2016-07: "total_size = size so far in bytes"; "Progress as in % done is not provided").
- `read_progress` (`ffmpeg_utils.py:94-125`) only populates `FfmpegProgress.total_size` from the `total_size=` key — there is no expected-total field available to pass as the third argument.
- No test in `tests/test_hls_downloader.py` invokes `perform_download(..., method=DownloadMethod.FFMPEG, progress_callback=...)` (searched: `perform_download` FFMPEG tests at lines 1360, 1418, 2462 all omit `progress_callback`).

**Recommendation (advisory):** For the ffmpeg batch path, do not fabricate a 100% total. Either (a) omit progress reporting for ffmpeg downloads (report `downloaded=total_size, total=0` so the UI shows "unknown total / N bytes" rather than "100%"), or (b) derive a real percentage from `out_time_ms` against the m3u8/playlist duration if/where it is known. At minimum, add a test asserting the adapter's total semantics. Effort: small-medium; priority: recommended.

### SRV-004: `api-reference.md` documents a stale `_download_segment` signature and false retry/cleanup behavior claims

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE, SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/api-reference.md:455-487`; `src/vkdownloader/services/segment_downloader.py:342-353`; `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** The API reference deviates from the implemented `services/` layer in three concrete ways:

1. **Stale `_download_segment` signature.** `api-reference.md:461-469` documents `_download_segment` with 6 parameters: `(session, segment_url, output_path, headers, max_concurrent_downloads=1, segment_index=0)`. The actual signature (`segment_downloader.py:342-353`) has 10 parameters and adds `backoff_coordinator=None, video_url=None, max_retries=3, download_timeout=300`. A reader following the doc would miss the retry/coordination knobs.

2. **False claim: parallel mode has no retry/backoff.** `api-reference.md:486-487` states "When `max_concurrent_downloads>1`: Uses direct download without retry backoff". This is wrong. The parallel path (`_run_parallel_download_with_backoff`, `segment_downloader.py:197`) implements full AWS Full Jitter backoff: it calls `_parse_retry_after` (line 233), `_compute_backoff_delay` (line 234), `_wait_with_shutdown` (line 236), `_notify_backoff_for_retryable_status` (line 230), and `_should_continue_on_retry` (line 232). The parallel path is in fact at least as resilient as the sequential path.

3. **False claim: `download_hls_with_resume` cleans up partial downloads on failure.** `api-reference.md:451` lists "Cleans up partial downloads on failure" as a feature, directly contradicting `api-reference.md:447` ("Resumes from last downloaded segment on interruption") and the code. The implementation **preserves** segments on failure for resume (`download_hls_with_resume` `finally:` block calls `_log_preserve_segments` at `segment_downloader.py:889`; cleanup only runs on success via `_cleanup_segments` at line 603). The doc therefore misrepresents both features.

**Evidence:**
- `src/vkdownloader/services/segment_downloader.py:342-353` actual `_download_segment` signature vs `docs/01-tools/api-reference.md:461-469`.
- `src/vkdownloader/services/segment_downloader.py:197-237` (`_run_parallel_download_with_backoff`) calls `_parse_retry_after`, `_compute_backoff_delay`, `_wait_with_shutdown`, `_notify_backoff_for_retryable_status`, `_should_continue_on_retry` — full backoff present in parallel mode.
- `src/vkdownloader/services/segment_downloader.py:885-901` — `download_hls_with_resume` `finally: if not success: _log_preserve_segments(segments_dir)` preserves partials; `segment_downloader.py:603` `_cleanup_segments` only on the success path.
- `docs/01-tools/api-reference.md:447` (resume on interruption) vs `:451` (clean up on failure) — internally contradictory.

**Recommendation (DOC-UPDATE):** Sync `api-reference.md`: (1) update `_download_segment` params table to include `backoff_coordinator`, `video_url`, `max_retries`, `download_timeout`; (2) correct the parallel-mode behavior to "uses AWS Full Jitter backoff with shared `URLBackoffCoordinator`" (same as sequential, plus coordinator pauses); (3) reword "Cleans up partial downloads on failure" to "Preserves partial segments on failure for segment-level resume; cleans up only on successful merge". Effort: trivial; priority: recommended.

### SRV-005: Docs reference a non-existent `DownloaderThrottle` class, a non-function `download_with_ffmpeg`, and mis-attribute quality selection

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE, SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/vkdownloader-overview.md:27,34,36,177`; `docs/01-tools/api-reference.md:177-196,433-442`; `src/vkdownloader/services/downloader.py:393` (`HLSDownloader.download_with_ffmpeg`), `src/vkdownloader/services/downloader.py:966`/`download_video:1202`; `src/vkdownloader/models/dtos.py` |
| **Classification** | advisory |

**Description:** Three documented-but-wrong service references:

1. **Non-existent `DownloaderThrottle` class.** `vkdownloader-overview.md:27` lists `DownloaderThrottle` as a service in `services/downloader_throttle.py`. No such class exists; the module defines `URLBackoffCoordinator` and `ProgressManager` (verified: `grep "class DownloaderThrottle|DownloaderThrottle" src/` → no matches). `api-reference.md:724` correctly documents `URLBackoffCoordinator`, so the overview name is stale.

2. **`download_with_ffmpeg` documented as a module function.** `vkdownloader-overview.md:36` and `api-reference.md:177-196` present `download_with_ffmpeg(...)` as a standalone function with a `quality` parameter. The actual symbol is the instance method `HLSDownloader.download_with_ffmpeg` (`downloader.py:393`), whose `quality` arg (line 398) is only used for logging, not for ffmpeg stream selection.

3. **`perform_download` mis-described as doing quality selection.** `vkdownloader-overview.md:34` says `perform_download()` does "quality selection + download method routing". Quality selection (`QualitySelector.select`, `downloader.py:1202`) actually happens in `download_video` (`downloader.py:1195-1202`); `perform_download` (`downloader.py:966-1139`) only routes on `DownloadMethod` and consumes a pre-selected `quality` string.

4. **`HLSDownloadRequest` doc example passes non-field kwargs.** `api-reference.md:433-442` constructs `HLSDownloadRequest(video_url=..., ..., settings=settings, extractor=extractor)`. `HLSDownloadRequest` (`models/dtos.py:11-24`) has only `video_url, m3u8_url, output_file, quality, cookies, progress_callback` — no `settings`/`extractor` fields. Because `HLSDownloadRequest` is a plain `BaseModel` (default `extra="ignore"`), those kwargs are silently dropped, so the example produces a request without settings; the real call signature is `download_hls_with_resume(request, settings=..., extractor=..., ...)` (`segment_downloader.py:821-826`).

**Evidence:**
- `grep -n "DownloaderThrottle" src/vkdownloader` → no `class DownloaderThrottle` (only `URLBackoffCoordinator`/`ProgressManager` in `downloader_throttle.py:44,76`).
- `downloader.py:393` `async def download_with_ffmpeg(self, ...)`.
- `downloader.py:1195` `selector = QualitySelector(); 1202: stream = selector.select(...)` inside `download_video`, not `perform_download`.
- `models/dtos.py:11-24` — `HLSDownloadRequest` fields; `segment_downloader.py:821-826` — `download_hls_with_resume(request, settings=None, extractor=None, ...)`.
- `docs/01-tools/vkdownloader-overview.md:27`, `:34`, `:36`; `docs/01-tools/api-reference.md:177-196`, `:433-442`.

**Recommendation (DOC-UPDATE):** Fix `vkdownloader-overview.md:27` (replace `DownloaderThrottle` with `URLBackoffCoordinator`/`ProgressManager` and point to the correct table already in `api-reference.md:724`); fix `vkdownloader-overview.md:34`/`api-reference.md:177-196` to show `HLSDownloader.download_with_ffmpeg` as a method (drop the misleading standalone `quality` param emphasis); correct `vkdownloader-overview.md:34` to attribute quality selection to `download_video`; rewrite `api-reference.md:433-442` to show `settings`/`extractor` as `download_hls_with_resume` kwargs, not `HLSDownloadRequest` fields. Effort: trivial; priority: recommended.

---

### SRV-006: Application-level retry loop in `download_with_ytdlp_with_resume_fallback` uses no backoff; `backoff_coordinator` is accepted but ignored for the yt-dlp attempts

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
    result = await _download_with_ytdlp(...)      # downloader.py:586  -- no sleep, no backoff
    if result:
        ...
        return result
    retry_count += 1                              # downloader.py:595  -- immediate re-attempt
    ...
    return await _attempt_segment_resume(..., backoff_coordinator,  # downloader.py:619 -- forwarded, but only here
        ...
    )
```

Between yt-dlp attempts there is **no `asyncio.sleep`, no jitter, no coordinator pause, no `_notify_backoff_for_retryable_status`**. The function therefore retries a failed yt-dlp download up to `MAX_RESUME_RETRIES` (=3) times in a tight loop, hammering the VK origin on failure — the opposite of the "rate limiting" the parameter advertises. yt-dlp's own `-R`/`--retry` flags (docstring `downloader.py:760-763`) handle transport-level retries, but the *application-level* yt-dlp→segment fallback retries have no backoff of their own.

This is an inconsistency, not a total absence: the segment fallback path delegates to `download_hls_with_resume` with the `backoff_coordinator` (line 727), and `segment_downloader._run_parallel_download_with_backoff` implements full AWS Full Jitter backoff (`_parse_retry_after`, `_compute_backoff_delay`, `_wait_with_shutdown`, `_notify_backoff_for_retryable_status`, `_should_continue_on_retry`; `segment_downloader.py:197-237`). So the two download backbones apply *different* retry policies: segments get jittered backoff; yt-dlp gets none. A reader (and maintainer) reasonably expects the documented "shared `URLBackoffCoordinator for rate limiting`" to govern both paths.

**Evidence:**
- `downloader.py:57` `MAX_RESUME_RETRIES = 3`.
- `downloader.py:585` `while retry_count <= MAX_RESUME_RETRIES:` — loop body calls `_download_with_ytdlp` (586) then `retry_count += 1` (595); no `await asyncio.sleep` anywhere between 586 and 619.
- `downloader.py:552, 572` — `backoff_coordinator` parameter + docstring "shared URLBackoffCoordinator for rate limiting".
- grep `backoff_coordinator` / `_notify_backoff_for_retry` / `compute_backoff` / `_wait_with_shutdown` within `downloader.py:542-632` → only the pass-through at line 619 (to `_attempt_segment_resume`).
- Contrast: `segment_downloader.py:197-237` `_run_parallel_download_with_backoff` uses `_parse_retry_after` (233), `_compute_backoff_delay` (234), `_wait_with_shutdown` (236), `_notify_backoff_for_retryable_status` (230), `_should_continue_on_retry` (232).
- `tests/test_hls_downloader.py` lines 812, 1360, 1418, 2462 — no test injects a real `URLBackoffCoordinator` and asserts a pause occurred during `download_with_ytdlp_with_resume_fallback` retries.

**Recommendation (advisory):** Either (a) make the documented behavior real by inserting a jittered backoff between yt-dlp retry attempts (e.g. `await _coord_wait(backoff_coordinator, retry_count)` capped at `MAX_RESUME_RETRIES`), or (b) keep the tight loop but drop `backoff_coordinator` from `download_with_ytdlp_with_resume_fallback` and state in the docstring that it is forwarded only to the segment-fallback path — removing the misleading "shared rate limiting" claim. Add a test asserting a backoff/pause occurs on yt-dlp retry using a fake coordinator. Effort: small-medium; priority: recommended.

---

## Summary

| ID | Title | Severity | Type | Affected | Effort | Status |
|----|-------|----------|------|----------|--------|--------|
| SRV-001 | `services/downloader.py` is a 1,218-line god-module mixing orchestration, subprocess I/O, parsing, temp-file handling, and a cross-module re-export facade | MEDIUM | BEST-PRACTICE, SPEC-DEVIATION | `src/vkdownloader/services/downloader.py` | large | open |
| SRV-002 | Dead code — `_write_netscape_cookie_file` defined and exported but never called | LOW | BEST-PRACTICE | `src/vkdownloader/services/cookies.py:58-74` | small | open |
| SRV-003 | `_ffmpeg_progress_adapter` always reports 100% progress for the ffmpeg download path | MEDIUM | BEST-PRACTICE (correctness) | `src/vkdownloader/services/downloader.py:1079-1083` | small-medium | open |
| SRV-004 | `api-reference.md` documents a stale `_download_segment` signature and false retry/cleanup behavior claims | LOW | DOC-UPDATE, SPEC-DEVIATION | `docs/01-tools/api-reference.md:455-487`; `services/segment_downloader.py:342-353` | trivial | open |
| SRV-005 | Docs reference a non-existent `DownloaderThrottle` class, a non-function `download_with_ffmpeg`, and mis-attribute quality selection | LOW | DOC-UPDATE, SPEC-DEVIATION | `docs/01-tools/vkdownloader-overview.md`; `api-reference.md:177-196,433-442`; `downloader.py:393,966,1202`; `models/dtos.py` | trivial | open |
| SRV-006 | Application-level retry loop in `download_with_ytdlp_with_resume_fallback` uses no backoff; `backoff_coordinator` accepted but ignored for yt-dlp attempts | MEDIUM | BEST-PRACTICE, SPEC-DEVIATION | `src/vkdownloader/services/downloader.py:542-632` | small-medium | open |

## Cross-reference

- Pre-existing lint/test-format state is tracked in Phase 01 (`CLI-001` ruff, `CLI-002` mypy, `CLI-003` pytest formatting, `CLI-004` unused `type:ignore`, `CLI-005` dead `module=['vkdownloader.cli']` mypy section) — not re-filed here per the constraint.
