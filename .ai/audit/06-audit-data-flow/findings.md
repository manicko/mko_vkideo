# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/06-audit-data-flow.md
**Status:** complete
**Validated:** no

> **Scope note (mandatory context):** The assigned phase template (`06-audit-data-flow.md`)
> describes a Google-Sheets→Telegram pipeline (`GSheetsReader`, `TelegramPoster`,
> `TelegramService`, `ImageCache`, `PostProcessor`, `chats.*` config, etc.). None of these
> components exist in this repository. The actual project (`mko_vkideo`) is a **VK video
> downloader** whose real pipeline is:
> `CLI → Settings → VKVideoExtractor.extract_streams() → VideoWithStreams → QualitySelector.select()
> → perform_download() → {yt-dlp | ffmpeg | segment download} → ffmpeg merge → cleanup`.
> The audit below traces the **actual** pipeline. See DF-009 for the template mismatch.

---

## Findings

### DF-001: BROWSER cookie mode silently drops the user-selected quality

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** When `--cookie-source browser` is used, `perform_download()` re-extracts the
stream via the browser and overwrites the chosen m3u8 URL with `browser_streams[0].url`. The
browser extraction path (`VKVideoExtractor._extract_with_browser`) builds **only one** Stream
with `quality="best"` (extractor.py:226-234), so `browser_streams[0]` is always the "best"
quality playlist. The previously quality-selected `selected_stream` is discarded for the FFMPEG
method and for the yt-dlp→segment resume path, so the downloaded file contains a different
quality than requested while the output filename is still built from the requested quality
(e.g. `MyVideo_720p.mp4` actually holds the "best" rendition).

**Evidence:**
- `downloader.py:523-529` (YTDLP+BROWSER) and `downloader.py:534-541` (FFMPEG+BROWSER):
  `m3u8_url = str(browser_streams[0].url)` replaces the selected URL.
- `downloader.py:304-323` (resume path inside `download_with_ytdlp_with_resume_fallback`):
  `m3u8_url = str(browser_streams[0].url)` used for `download_hls_with_resume` (segments
  consume the URL directly at `segment_downloader.py:231-259`).
- `extractor.py:226-234`: single Stream appended with `quality="best"`, so `streams[0]` is
  always "best" regardless of the user's `--quality`.
- Note: for the pure YTDLP method the override is a no-op (yt-dlp re-extracts from `video_url`
  and honors quality via the `best[height<=N]` format filter), but quality is still lost on the
  FFMPEG path and on any yt-dlp→segment resume fallback.

**Recommendation:** Do not discard the selected stream when fetching browser cookies. Capture
only the cookies/header from `_extract_with_browser` (or re-select from the returned streams by
quality) and keep the URL of the originally selected `selected_stream`. If the browser returns a
single "best" playlist, map it back through `QualitySelector` instead of overwriting by index.

---

### DF-002: `--method auto` ignores `--cookie-source browser`

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** The AUTO branch calls `download_with_ytdlp_with_resume_fallback(...)` without
passing the `cookies` argument, unlike the explicit YTDLP and FFMPEG branches which first call
`extract_streams_with_cookies()` when `cookie_source == BROWSER`. As a result, with
`--cookie-source browser --method auto` the primary yt-dlp download runs without the cookies
that the same configuration attaches in the other two methods — inconsistent behavior for an
identical configuration.

**Evidence:** `downloader.py:561-565` (AUTO case) omits `cookies=`; contrast with
`downloader.py:530-532` and `downloader.py:543` which pass `cookies=cookies` after a browser
extraction.

**Recommendation:** Make cookie acquisition uniform across all three method branches (e.g. a
shared helper that returns `(m3u8_url, cookies)` given `cookie_source`), so AUTO behaves the
same as YTDLP/FFMPEG for authenticated downloads.

---

### DF-003: Segment "resume" is defeated by unconditional cleanup of partial progress

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `download_hls_with_resume()` advertises segment-level resume, but its `finally`
block deletes the entire `segments_dir` and `metadata_file` whenever the function exits without
success (any transient segment failure, partial download, or crash mid-run). Because every failed
run erases on-disk progress, there is never any partial state to resume on the next invocation,
so the feature cannot persist across runs. Worse, `downloaded_count` is recomputed as
`_load_downloaded_count(metadata_file) + sum(results)` and `_save_downloaded_count` runs only
*after* all tasks complete; a crash before that point loses everything, and a run where some
segments failed returns `None` while the `finally` block then discards the good segments too.
This wastes large re-downloads and contradicts the function's documented purpose.

**Evidence:**
- `segment_downloader.py:309-331`: merge only happens when `downloaded_count == len(segments)`;
  otherwise the function returns `None`.
- `segment_downloader.py:332-336`: `finally: if segments_dir.exists(): _cleanup_segments(...)`
  unconditionally removes segments + metadata on every non-success exit.
- `segment_downloader.py:312`: `_save_downloaded_count` is only called after `asyncio.gather`
  completes, so a crash mid-run leaves `metadata_file` stale/empty while `.ts` files remain —
  and the next run's `finally` deletes them anyway.

**Recommendation:** Only clean up segments on *successful* completion. On failure, preserve
already-downloaded segments and a correct progress count so a subsequent run can skip them.
Recompute `downloaded_count` from the actual set of existing `.ts` files (not just the in-memory
metadata) before deciding whether a merge is possible.

---

### DF-004: Partial/corrupt segment files are treated as complete on resume

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | mandatory |

**Description:** A previously downloaded segment is reused if `segment_path.exists()` is true,
with no check that the file is complete or non-empty. If a prior run crashed mid-write, a
truncated `.ts` remains on disk and is silently reused, producing a corrupt (but "complete")
merged video with no error raised. Additionally, `_merge_segments_batched()` silently skips any
batch where a segment file is missing (`if not all(f.exists() ...): continue`), yielding a
truncated output without surfacing the failure.

**Evidence:**
- `segment_downloader.py:261-273`: `if not segment_path.exists(): ... else: result = True` —
  existence alone marks success.
- `ffmpeg_utils.py:254-256`: `if not all(f.exists() for f in batch_files): continue` — missing
  segments cause the batch (and thus that portion of the video) to be dropped silently.

**Recommendation:** Validate each segment's integrity (e.g. non-zero size, or keep a verified
count in the progress metadata and remove/re-fetch any segment not confirmed written). In the
merge step, fail loudly instead of silently skipping a missing batch.

---

### DF-005: `Stream.url` typed as `HttpUrl` can mangle signed CDN URLs

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/video.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `Stream.url` is declared as Pydantic `HttpUrl`. Pydantic v2 `HttpUrl` performs
percent-encoding normalization and host/query canonicalization on construction. VK m3u8 and
segment URLs carry signed query tokens (hashes, expiries, signatures); normalization can alter
these tokens and cause 403/410 responses from the CDN. The downstream code feeds the `str()`
form of these URLs into ffmpeg and aiohttp, so any silent mutation propagates into the actual
download request.

**Evidence:** `models/video.py:22-23` (`url: HttpUrl`); `extractor.py:173-184` and
`extractor.py:227-233` construct `Stream(url=HttpUrl(...))`; `downloader.py:508` /
`segment_downloader.py:231-259` consume `str(stream.url)` / the raw m3u8 URL.

**Recommendation:** Store stream URLs as `str` (or use `AnyUrl` only with explicit raw handling)
to avoid silent canonicalization of signed URLs, and keep the parsed URL type only where
validation is genuinely needed.

---

### DF-006: `--cookie-source file` is a non-functional placeholder

| Field | Value |
|-------|-------|
| **ID** | DF-006 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** The `CookieSource.FILE` enum value is accepted by the CLI and config, but
`extract_streams_with_cookies()` only contains a "Future: Load cookies from file" comment and
returns `(streams, None)` — no cookies are ever loaded or used. A user passing
`--cookie-source file` believes cookies are applied when in fact the download proceeds without
them, leading to silent auth failures / 403s on protected videos.

**Evidence:** `extractor.py:124-131`: the FILE branch has the placeholder comment and returns
`streams, None`; no file-reading implementation exists anywhere in the codebase.

**Recommendation:** Either implement cookie-file loading (Netscape/JSON) or explicitly disable
the `FILE` option and fail fast with a clear message until it is supported, so users are not
misled.

---

### DF-007: Stale `docs/STRUCT.md` and orphaned infrastructure modules

| Field | Value |
|-------|-------|
| **ID** | DF-007 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/STRUCT.md`, `src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/infrastructure/adaptive_throttle.py` |
| **Classification** | advisory |

**Description:** `docs/STRUCT.md` does not list `services/ffmpeg_utils.py` or
`services/segment_downloader.py`, both of which exist and are central to the real download flow.
Conversely, `infrastructure/http_client.py` (`HttpClient`) and `infrastructure/adaptive_throttle.py`
(`AdaptiveThrottle`) are exported from `infrastructure/__init__.py` and listed in the docs but are
never referenced by any service (verified via grep: matches only in their own definitions and the
`__init__`). They are orphaned relative to the actual data flow.

**Evidence:** `docs/STRUCT.md:37-43` omits the two service files; grep for `HttpClient` /
`AdaptiveThrottle` returns only the defining module and `infrastructure/__init__.py` (no service
consumers). The real HTTP work is done by `segment_downloader.py` (aiohttp) and `downloader.py`
(yt-dlp/ffmpeg).

**Recommendation:** Update `STRUCT.md` to reflect the real module tree. Investigate whether
`HttpClient`/`AdaptiveThrottle` are intended to be wired in; if not, remove them (or the docs
claim) to reduce maintenance surface. Per the dead-code policy, confirm intent before deletion.

---

### DF-008: Deprecated `asyncio.get_event_loop()` in running coroutine

| Field | Value |
|-------|-------|
| **ID** | DF-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `_extract_with_ytdlp` calls `asyncio.get_event_loop()` inside a coroutine. The
deprecated API can emit `DeprecationWarning` and, in some event-loop configurations, would not
return the running loop reliably. The correct call inside a coroutine is
`asyncio.get_running_loop()`.

**Evidence:** `extractor.py:194`: `loop = asyncio.get_event_loop()`.

**Recommendation:** Replace with `asyncio.get_running_loop()` for correctness and to avoid the
deprecation path.

---

### DF-009: Audit phase template does not match the project under audit

| Field | Value |
|-------|-------|
| **ID** | DF-009 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.kilo/commands/audit/phases/06-audit-data-flow.md` |
| **Classification** | advisory |

**Description:** The phase template's Discovery/Config/Multi-Chat/Error-Propagation sections
reference Google Sheets and Telegram components (`GSheetsReader`, `TelegramPoster`,
`TelegramService`, `PostProcessor`, `ImageCache`, `chats.*`, `range_names`, `topic_id`, etc.)
that do not exist in `mko_vkideo`. The actual pipeline is a VK video downloader with no
multi-chat / message-posting stage. Executing the template verbatim would yield false
"missing component" findings and miss the real data-flow concerns. The auditor adapted by
tracing the real pipeline; future runs should target the correct components.

**Evidence:** `06-audit-data-flow.md` lines 26, 69-99 describe a GSheet→Telegram flow; the
repository contains only `vkdownloader` (CLI + extractor + downloader services).

**Recommendation:** Rewrite the phase to describe the real pipeline (CLI → Settings →
VKVideoExtractor → QualitySelector → perform_download → segment/ffmpeg → merge → cleanup) and the
relevant config fields (`cookie_source`, `ssl_verify`, `max_concurrent_downloads`,
`throttled_rate`, `max_retries`, etc.), or mark this phase as not applicable to this project.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 4 |
| LOW | 3 |

## Mandatory Fixes

- DF-001 — BROWSER cookie mode drops selected quality (HIGH, correctness/data integrity)
- DF-002 — AUTO method ignores `cookie_source=browser` (MEDIUM, consistency)
- DF-003 — Segment resume defeated by unconditional cleanup of partial progress (HIGH, data loss)
- DF-004 — Partial/corrupt segment treated as complete on resume (MEDIUM, data integrity)
- DF-006 — `--cookie-source file` is a non-functional placeholder (MEDIUM, misleading behavior)

## Advisory Recommendations

- DF-005 — Avoid `HttpUrl` for signed CDN stream URLs (MEDIUM)
- DF-007 — Update stale `STRUCT.md` and investigate orphaned `HttpClient`/`AdaptiveThrottle` (LOW)
- DF-008 — Replace deprecated `asyncio.get_event_loop()` (LOW)
- DF-009 — Correct the audit phase template to match the real pipeline (LOW)

## Doc Updates Needed

- DF-007 — `docs/STRUCT.md` must list `services/ffmpeg_utils.py` and `services/segment_downloader.py`
  and reconcile the documented (but unused) `HttpClient`/`AdaptiveThrottle`.
- DF-009 — Phase `06-audit-data-flow.md` must target the real VK-downloader pipeline.

