# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** validated
**Validated by:** validator
**Date:** 2026-07-14
**Note:** Finalized by orchestrator after validator hit step limit. SRV-007 rejected (see below).

---

> NOTE: The phase template (`.kilo/commands/audit/phases/03-audit-services.md`) describes a
> Telegram/Google-Sheets service layer (`TelegramService`, `PostProcessor`, `ImageCache`,
> `GSheetsReader`, `Task` model). That layer does NOT exist in this repository. The actual
> `mko_vkideo` service layer under `src/vkdownloader/services/` is:
> `downloader.py`, `downloader_throttle.py`, `extractor.py`, `ffmpeg_utils.py`,
> `quality.py`, `segment_downloader.py`. This audit covers the **actual** services.

## Runtime Verification (preconditions)

- **R1 Import:** `uv run python -c "import vkdownloader.services.*"` → `IMPORT OK`.
- **R2 Lint/Types:** `ruff check src/vkdownloader/services` → `All checks passed!`;
  `mypy src/vkdownloader/services` → `Success: no issues found in 7 source files`.
- **R3 Tests:** `pytest` (full suite) → **201 passed**, 4 `ResourceWarning`s
  (`coroutine 'Event.wait' was never awaited` in `test_downloader_throttle.py`).
- **R4 Dead code:** `URLBackoffCoordinator.is_paused`, `DownloadRequest`, `DownloadResult`,
  `DownloadProgress`, `StreamWithCookies` are defined/exported but never instantiated in
  production code (see SRV-008, SRV-009).

---

## Findings

### SRV-001: Batch progress callback and shared backoff coordinator are dropped for yt-dlp / auto methods

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** `perform_download()` accepts `backoff_coordinator`, `semaphore`, and
`progress_callback` and documents them as enabling "shared rate limiting across URLs" and
"per-URL progress tracking" for batch downloads. However, the `DownloadMethod.YTDLP` and
`DownloadMethod.AUTO` branches (the DEFAULT method is `AUTO`) call
`download_with_ytdlp_with_resume_fallback(...)` without passing any of these three values. The
called function's signature (`downloader.py:243`) also does not accept them, so the internal
segment fallback (`downloader.py:313`) likewise omits them.

**Evidence:**
`downloader.py:530` (YTDLP) and `downloader.py:563` (AUTO) call
`download_with_ytdlp_with_resume_fallback(url, m3u8_url, output_file, quality, extractor, settings, cookies=cookies)`
with no `backoff_coordinator` / `semaphore` / `progress_callback`. The FFMPEG branch
(`downloader.py:555-557`) *does* pass them, proving the omission is inconsistent, not intentional.
In `cli.py` batch mode (`_run_batch_with_progress`), `progress_callback` feeds `_format_progress`
and `backoff_coordinator` is created for shared rate limiting — both are inert for the default
method.

**Recommendation:** Thread `backoff_coordinator`, `semaphore`, and `progress_callback` through
`download_with_ytdlp_with_resume_fallback` (and its internal segment call) exactly as the FFMPEG
branch does, so batch progress display and shared rate limiting work for all methods. Effort: small.
Priority: recommended.

---

### SRV-002: User-selected quality is silently overridden when `cookie_source=BROWSER`

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** When `cookie_source == CookieSource.BROWSER`, both the YTDLP and FFMPEG branches
in `perform_download()` re-extract via `extractor.extract_streams_with_cookies(url)` and then
overwrite `m3u8_url = str(browser_streams[0].url)`. The browser path (`extractor.py:227-234`)
always produces a single `Stream` with hardcoded `quality="best"`. The user's already-selected
stream (e.g. 720p chosen by `QualitySelector`) is discarded and the download proceeds at the
browser's best quality. `QualitySelector` is never re-run on the browser streams, so a request for
a specific resolution under BROWSER mode is silently ignored.

**Evidence:**
`downloader.py:523-527` and `downloader.py:535-539`: `m3u8_url = str(browser_streams[0].url)`.
`extractor.py:226-234`: browser stream is built with `quality="best"` only. `cli.py:117` selects a
concrete quality before calling `perform_download`, but it is overridden above.

**Recommendation:** In BROWSER mode, run `QualitySelector.select(browser_streams, quality)` (or map
the user's chosen `selected_stream` onto the browser-derived streams) before picking the URL, so the
requested resolution is honored; otherwise fail loudly if the requested quality is unavailable.
Effort: small. Priority: recommended.

---

### SRV-003: Parallel segment downloads (default config) never retry 429/5xx — rate-limit handling is inert by default

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory |

**Description:** The entire retry/backoff machinery in `downloader_throttle.py`
(`_retry_429_with_backoff`, `RETRYABLE_STATUS_CODES`, jitter) is only exercised in the
`max_concurrent_downloads == 1` branch of `_download_segment`. In the parallel branch
(`max_concurrent_downloads > 1`, which is the **default**: `Settings.max_concurrent_downloads = 4`),
a non-200 response is logged, the coordinator is told to `pause` *other* segments, and the segment
returns `False` with **no retry**. Because the merge gate requires
`downloaded_count == len(segments)`, a single transient 429/5xx in the default parallel path
permanently fails the whole download. Current best practice (confirmed via websearch: httpx-retries,
tenacity, aiohttp scraping guides) is that transient 429/5xx retries with backoff+jitter must apply
*regardless of concurrency*. Here the headline "adaptive throttling / rate-limit" feature is
inoperative for the default configuration.

**Evidence:**
`segment_downloader.py:67-73`: retry/backoff only when `max_concurrent_downloads == 1`.
`segment_downloader.py:84-94`: parallel branch returns `False` on any non-200, calling
`backoff_coordinator.pause(...)` but never retrying. `config.py:57-62`: default
`max_concurrent_downloads = 4`. `downloader.py:546` FFMPEG path (and internal yt-dlp fallback at
`downloader.py:313`) feed `settings` whose default is parallel.

**Recommendation:** In `segment_downloader.py:84-94`, replace the non-200 response handling that returns `False` immediately with a retry loop that uses the same `_retry_429_with_backoff` pattern already implemented for sequential mode. Wrap the `session.get()` call in a `for attempt in range(max_retries):` loop, apply backoff+jitter on 429/5xx responses, and only return `False` after exhausting retries. This ensures transient rate-limit errors are handled consistently regardless of `max_concurrent_downloads` setting. Effort: medium. Priority: recommended.

---

### SRV-004: `Settings.max_retries` and the `--max-retries` CLI flag have no effect on actual retries

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** `Settings.max_retries` (default 3, range 1–10) and the `batch --max-retries`
option that sets it are never consulted by the code that actually retries. Segment retry loops
hardcode `max_retries: int = 3` in both `_retry_429_with_backoff` (`downloader_throttle.py:147`)
and `_fetch_playlist_with_retry` (`segment_downloader.py:136`). yt-dlp retry counts are hardcoded
(`retries: 10`, `fragment_retries: 10` in `downloader.py:380-381`). A user passing
`--max-retries 8` gets no change in behavior.

**Evidence:**
`segment_downloader.py:136` `_fetch_playlist_with_retry(..., max_retries: int = 3)` and
`downloader_throttle.py:147` `_retry_429_with_backoff(..., max_retries: int = 3)` — both use a
literal default, not `settings.max_retries`. `cli.py:212-217` exposes `--max-retries` →
`Settings(max_retries=actual_max_retries)` (`cli.py:246-249`), but the value is never read by the
download paths.

**Recommendation:** Pass `settings.max_retries` into `_retry_429_with_backoff` and
`_fetch_playlist_with_retry`, and use a `settings`-derived value for yt-dlp `retries`. Effort: small.
Priority: recommended.

---

### SRV-005: `HLSDownloadRequest` DTO carries live service objects and relies on a fragile monkeypatched `__init__`

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/dtos.py` |
| **Classification** | advisory |

**Description:** `HLSDownloadRequest` (a Pydantic model) holds non-data runtime objects: an
`extractor` service (`VKVideoExtractor`), `settings`, a `URLBackoffCoordinator`, an
`asyncio.Semaphore`, and a `progress_callback`. This mixes a data container with live services and
state, breaking serializability and making the model impossible to construct/inspect in isolation
(mocking/unit tests). To work around the resulting forward-reference/circular-import problem, the
module monkeypatches `HLSDownloadRequest.__init__` (`dtos.py:74-85`) to lazily call
`model_rebuild()` on first use and mutates the module namespace. Domain-model guidance (websearch:
service-layer / DDD references) is that request/response models stay serializable data; services and
runtime state are injected at the call site, not embedded in the DTO.

**Evidence:**
`dtos.py:34-42`: fields typed `Settings | None`, `VKVideoExtractor | None`,
`URLBackoffCoordinator | None`, `asyncio.Semaphore | None`, `Callable`. `dtos.py:59-85`:
`_ensure_model_rebuilt` + `HLSDownloadRequest.__init__ = _lazy_init` monkeypatch with `# noqa: F821`
forward refs.

**Recommendation:** Keep `HLSDownloadRequest` as pure serializable data (URLs, quality, cookies,
paths). Pass `extractor`, `settings`, `backoff_coordinator`, `semaphore`, and `progress_callback`
as explicit arguments through the call chain (as already done for `perform_download`), removing the
monkeypatched `__init__`/`model_rebuild` hack. Effort: medium. Priority: recommended.

---

### SRV-006: yt-dlp cookie temp file is created but never cleaned up (orphaned temp file)

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** In `_download_with_ytdlp`, a cookie file
`output_file.parent / f".{output_file.stem}_cookies.txt"` is written and passed to yt-dlp, but it
is never deleted on success or failure. Repeated downloads leave accumulating hidden dotfiles next
to outputs.

**Evidence:**
`downloader.py:386-388` writes `cookie_file.write_text(_cookies_to_netscape(cookies))` and sets
`ydl_opts["cookiefile"]`; no `finally`/cleanup removes it.

**Recommendation:** Remove the cookie file in a `try/finally` after the yt-dlp download completes
(success or failure). Effort: trivial. Priority: recommended.

---

### SRV-007: Unreachable `max_retries_exceeded` branch in `download_with_ytdlp_with_resume_fallback`  **[REJECTED BY VALIDATOR]**

| Field | Value |
|-------|-------|
| **ID** | SRV-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Validator rejection:** FALSE FINDING. The retry loop is `while retry_count <= MAX_RESUME_RETRIES:`
with `MAX_RESUME_RETRIES = 3`. After a failed attempt `retry_count` is incremented, then the guard
`if retry_count <= MAX_RESUME_RETRIES:` is evaluated. On the 4th failed attempt `retry_count` becomes
`4`, so `4 <= 3` is false and the `else: logger.error("max_retries_exceeded")` branch IS reached
before the loop exits. The exhaustion path is reachable and the finding's core claim (unreachable
`else`) is incorrect. Rejected; no code change warranted.

---

### SRV-008: `URLBackoffCoordinator.is_paused()` is defined but never called (dead code)

| Field | Value |
|-------|-------|
| **ID** | SRV-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `URLBackoffCoordinator.is_paused(self, video_url)` is a public method that is never
invoked anywhere in the codebase (only its definition exists). Per the dead-code policy, this should
be investigated: either it is leftover from an earlier design (coordinated backoff that was replaced
by `wait_if_paused`) or it is intended API that is missing a caller.

**Evidence:**
`downloader_throttle.py:51-55` (definition only). grep across `src/` shows no call sites.

**Recommendation:** Remove `is_paused` method from `URLBackoffCoordinator` in `downloader_throttle.py:51-55`. The method is never called (verified via grep), `wait_if_paused` already provides the blocking behavior needed for rate-limit coordination, and `pause()` sets the backoff duration. Dead code that serves no purpose should be deleted to maintain code clarity. Effort: trivial. Priority: recommended.

---

### SRV-009: Declared DTOs/models are never instantiated — `perform_download` returns `Path | None`, not `DownloadResult`

| Field | Value |
|-------|-------|
| **ID** | SRV-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/dtos.py`, `src/vkdownloader/models/video.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `DownloadRequest`, `DownloadResult`, `DownloadProgress`, and `StreamWithCookies`
are defined and exported (`models/__init__.py`) but never instantiated in production code. The
service entry point `perform_download` returns `Path | None` rather than the declared
`DownloadResult`, and the CLI consumes the raw `Path`. This indicates an intended-but-unwired data
model: the documented result/status types exist but the code never produces them, so download
outcomes (file size, duration, streams used, success/error) are discarded instead of being captured
in a structured result.

**Evidence:**
grep shows `DownloadResult`/`DownloadRequest`/`DownloadProgress`/`StreamWithCookies` only at their
definitions/exports; `downloader.py:460-568` `perform_download` returns `Path | None`.

**Recommendation:** Remove `DownloadRequest`, `DownloadResult`, `DownloadProgress`, and `StreamWithCookies` from `models/dtos.py` and `models/video.py`. These models are never instantiated in production code (`perform_download` returns `Path | None`), and the project follows "Production Code is King" with preference for simple, focused return types. The `HLSDownloadRequest` type is the only DTO actively used; the unused models only create false expectations about structured results. Effort: small. Priority: recommended.

---

### SRV-010: `CookieSource.FILE` is a non-functional placeholder with no warning

| Field | Value |
|-------|-------|
| **ID** | SRV-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** In `extract_streams_with_cookies`, the `CookieSource.FILE` branch contains only a
comment `# Future: Load cookies from file` and then behaves identically to `CookieSource.NONE` —
it returns yt-dlp streams with `cookies=None`. A user selecting `--cookie-source file` (a value
exposed in the CLI and `Settings`) gets no cookie authentication and no indication that the feature
is unimplemented.

**Evidence:**
`extractor.py:124-131`: FILE branch returns `streams, None` after the "Future" comment.

**Recommendation:** Raise `NotImplementedError` with a clear message when `CookieSource.FILE` is selected in `extractor.py:124`. Replace the placeholder branch with: `raise NotImplementedError("CookieSource.FILE is not implemented. Use --cookie-source BROWSER or NONE instead.")`. This provides immediate, actionable feedback to users instead of silently failing to provide authentication. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 5 |

## Mandatory Fixes

- SRV-001 (YTDLP/AUTO drop progress_callback & backoff_coordinator)
- SRV-002 (quality overridden under BROWSER)
- SRV-003 (parallel mode never retries 429/5xx — default config)
- SRV-004 (`--max-retries` / `Settings.max_retries` ignored)

## Advisory Recommendations

- SRV-005 (DTO carries service objects + fragile init)
- SRV-006 (orphaned cookie temp file)
- SRV-008 (unused `is_paused`)  _(SRV-007 rejected by validator)_
- SRV-009 (unused DTOs; `DownloadResult` never produced)
- SRV-010 (`CookieSource.FILE` placeholder)

## Doc Updates Needed

- The phase template (`03-audit-services.md`) references a non-existent Telegram/Google-Sheets
  service layer; it should be updated to describe the real `vkdownloader` services (see note at top).
- `cli.py` help/README should document that `CookieSource.FILE` is unimplemented (SRV-010) and that
  quality selection is ignored under `CookieSource.BROWSER` (SRV-002).

---


