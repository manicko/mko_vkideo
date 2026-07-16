# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/06-audit-data-flow.md
**Status:** complete
**Validated:** no

---

## Findings

### DF-001: Per-URL progress callback accepted by default download path but never invoked

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** The batch download flow creates a per-URL `progress_callback` (cli.py:26-45, created per URL at cli.py:176) and threads it all the way down through `perform_download` → `download_with_ytdlp_with_resume_fallback` → `_download_with_ytdlp`. However, `_download_with_ytdlp` (downloader.py:416-500) never calls `progress_callback`. It only passes the callback onward to the segment-resume path (`download_hls_with_resume`, via `_attempt_segment_resume` at downloader.py:393-405) which is only reached on yt-dlp *failure* with a partial file. On the default `DownloadMethod.AUTO` path (downloader.py:644-650) — the most common and usually successful path — the yt-dlp download completes inside `_download_with_ytdlp` and the callback is silently dropped.

The result: for every URL that downloads successfully via yt-dlp (the normal case), no segment-level progress is ever reported. `ProgressManager` stores `0/0` for that URL for the entire download. The live batch progress display (cli.py:190-204, `_format_progress`) therefore shows `0/0` (or only reflects the segment-resume fallback) for the overwhelming majority of units, permanently understating actual progress and giving the user a false "no progress" signal for hours-long downloads. This is a user-visible data-integrity defect in the progress reporting channel.

**Evidence:**
- Callback creation + per-URL wiring: cli.py:26-45 (`_create_progress_callback`), cli.py:176 (callbacks list), cli.py:178-186 (`_download_single(..., callbacks[i])`).
- Callback threaded into download: cli.py:128 (`progress_callback=progress_callback`) → downloader.py:619, 649 (`progress_callback=progress_callback`).
- Default AUTO path: downloader.py:644-650 calls `download_with_ytdlp_with_resume_fallback(...)` with `progress_callback`.
- Failure-only invocation: downloader.py:297 (`result = await _download_with_ytdlp(...)` — note `_download_with_ytdlp` signature at downloader.py:416-422 does NOT accept `progress_callback`), and the callback is only forwarded to the segment path at downloader.py:313-317 / 393-405.
- `_download_with_ytdlp` body (downloader.py:416-500): the `progress_callback` parameter is absent from the signature and there is no `progress_callback(...)` call anywhere in the function. Only `logger.info("starting_ytdlp_download", ...)` (downloader.py:424-429) and `logger.info("yt_dlp_download_cancelled")` (downloader.py:492) exist.
- Live display reads from shared state that never updates: cli.py:190 / 204 (`typer.echo(f"\r{await _format_progress(total)}")`).

**Recommendation:** Make yt-dlp progress observable on the primary path. Options, in order of simplicity:
- (a) Wrap the yt-dlp download in a download hook (`ydl_opts["progress_hooks"]`) inside `_download_with_ytdlp` and translate yt-dlp's `downloaded_bytes`/`total_bytes` into the `(video_id, downloaded, total)` callback signature, passing `progress_callback` into `_download_with_ytdlp` and `_attempt_segment_resume` already receives it. This keeps the existing callback contract intact.
- (b) If byte-level granularity from yt-dlp is unreliable, at minimum invoke the callback once at start (`0, total`) and once at completion (`total, total`) so the live display reflects reality.
- Either fix must preserve the correct `url_index` keying already established by `_create_progress_callback`. Verify the fix by batch-downloading ≥2 URLs and confirming the on-screen progress leaves `0/0` before completion.

---

### DF-002: Settings() re-instantiated across the lifecycle with subset field construction

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description:** `Settings` (a Pydantic `BaseSettings`) is re-instantiated in many independent places across the unit-of-work lifecycle, each time reading environment variables / `.env` from scratch. Critically, several call sites construct it with only a *subset* of fields, fragmenting config propagation:
- cli.py:92 — `Settings().max_retries` (separate instantiation just to read one field).
- cli.py:93-95 — `_download_single` builds `Settings(cookie_source=cookie_source, max_retries=actual_max_retries, ssl_verify=ssl_verify)` — a *subset* that silently resets every other setting (`user_agent`, `download_dir`, `throttled_rate`, `http_chunk_size`, `max_concurrent_downloads`, `timezone`, `locale`, etc.) to defaults because they are not passed through.
- cli.py:169 — `Settings().max_concurrent_downloads` (another standalone read).
- cli.py:292 — `download()` builds `Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)` (also subset).
- downloader.py:115 (`HLSDownloader.__init__`), downloader.py:292 (`download_with_ytdlp_with_resume_fallback`), downloader.py:591 (`perform_download`) — fall back to `Settings()` when none is passed.
- segment_downloader.py:655, extractor.py:33, infrastructure/browser.py:23 — same `Settings()` fallback pattern.

The CLI-side subset construction is the real risk: a user who sets `VKDOWNLOADER_USER_AGENT` or `VKDOWNLOADER_DOWNLOAD_DIR` in the environment will see those values ignored during batch/single download, because the per-unit `Settings(...)` only forwards `cookie_source`, `max_retries`, `ssl_verify`. Configuration is therefore not propagated uniformly end-to-end — it depends on which code path re-reads the env. This violates the "trace each config section from source to its final consumer, no silent drops" requirement of the data-flow audit.

**Evidence:**
- Subset construction dropping fields: cli.py:93-95 (`Settings(cookie_source=cookie_source, max_retries=actual_max_retries, ssl_verify=ssl_verify)`); cli.py:292 (`Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)`).
- Redundant single-field reads: cli.py:92 (`Settings().max_retries`), cli.py:169 (`Settings().max_concurrent_downloads`), cli.py:431 (`Settings().max_concurrent_downloads`).
- Multiple fallback instantiations: downloader.py:115, 292, 591; segment_downloader.py:655; extractor.py:33; infrastructure/browser.py:23.
- `Settings` definition with no propagation mechanism: config.py:15-102 (fields like `user_agent`, `download_dir`, `throttled_rate`, `http_chunk_size`, `max_concurrent_downloads`, `timezone`, `locale` are defined but only honored when `Settings()` is constructed with all of env loaded — which the subset constructors bypass).

**Recommendation:** Construct `Settings` exactly once per invocation and pass the single instance down through `perform_download` → `download_with_ytdlp_with_resume_fallback` → `_download_with_ytdlp` → `HLSDownloader` → `VKVideoExtractor` → `browser`. For the CLI, build one `Settings` object at the top of `download()` / `batch_download()` that merges CLI overrides with the full environment-loaded instance (e.g. `Settings(**{**Settings().model_dump(), "cookie_source": cookie_source, ...})` or use Pydantic `model_construct`/merge) rather than constructing a narrow subset that resets other fields. This removes 8+ redundant env reads, guarantees uniform propagation, and makes config traceability auditable in one place. Effort: small. Priority: recommended.

---

### DF-003: Inconsistent output-filename schemes between single and batch; single-command fallback embeds non-deterministic `stream.quality`

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** The two code paths that build output filenames use different schemes:
- Batch (`_download_single`): cli.py:113-117 → `{safe_title}_{video.id}.mp4` when a title exists, else `{index}_{video.id}.mp4`. The scheme is `title-or-index` + `video.id`.
- Single (`download`): cli.py:317-321 → `{safe_title}_{video.id}.mp4` when a title exists, else `{video.id}_{stream.quality}.mp4`. The fallback scheme is `video.id` + `stream.quality`.

Because the single-command fallback embeds `stream.quality` (cli.py:321), and `Stream.quality` can be the literal `"best"` (the `QualityEnum.BEST` label, see quality.py:66-68 returning the best stream whose `quality` may be labeled `"best"`/`"unknown"`) or `"unknown"`, the resulting filename is non-deterministic and can collide or produce confusing names like `{id}_best.mp4` / `{id}_unknown.mp4`. The batch path, by contrast, never embeds `stream.quality` in its fallback. This is both a cross-path inconsistency (two different naming contracts for the "no title" case) and a determinism break (filenames vary with the upstream quality label that the system does not control). A documented naming scheme is part of the user-visible data-flow output contract.

**Evidence:**
- Batch scheme: cli.py:113-117 (`safe_title_{video.id}.mp4` or `{index}_{video.id}.mp4`).
- Single scheme: cli.py:317-321 (`safe_title_{video.id}.mp4` or `{video.id}_{stream.quality}.mp4`).
- `stream.quality` can be `"best"`/`"unknown"`: quality.py:47-85 (`QualitySelector.select` returns `result` whose `.quality` is the raw stream label; for `QualityEnum.BEST` it returns `_get_fallback_stream` result at quality.py:67). `QualityEnum.BEST` itself is the CLI default (cli.py:256, 376). Stream model labels are not guaranteed numeric.
- `Stream.quality` type: models/video.py (Stream model) — quality is a free-form string per the audit scope; values such as `"best"`/`"unknown"` are observed in tests (test_hls_downloader.py uses `quality="720"` but the model permits arbitrary strings).

**Recommendation:** Unify the output-filename scheme across both commands. Adopt the batch scheme (`{safe_title}_{video.id}.mp4`, fallback `{index}_{video.id}.mp4`) for the single command as well, and never embed `stream.quality` in the filename — use a normalized numeric resolution only if a resolution suffix is desired (derive from `stream.height`, not the free-form label). Document the single canonical naming scheme in `docs/` and reference it from both commands. This removes cross-path inconsistency and the non-deterministic `best`/`unknown` filenames. Effort: small. Priority: recommended.

---

### DF-004: yt-dlp format selector `best[height<=best]` breaks for literal "best" quality (HLSDownloadRequest default)

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/models/dtos.py` |
| **Classification** | mandatory |

**Description:** `_download_with_ytdlp` builds the yt-dlp format selector as `f"best[height<={quality_str}]"` (downloader.py:446), where `quality_str = quality.replace("p", "") if quality else "720"` (downloader.py:430). When `quality` is the literal string `"best"` — which is the *default* value of `HLSDownloadRequest.quality` (dtos.py:20) and is also what the CLI passes when `QualityEnum.BEST` is selected and `stream.quality` resolves to `"best"` — `quality_str` becomes `"best"`, producing the invalid selector `best[height<=best]`. yt-dlp rejects this as a malformed format string (`height<=best` is not a valid numeric comparison), so the download fails outright on the primary path whenever the resolved quality label is the literal `"best"`.

This is a correctness bug on the default code path: a freshly defaulted `HLSDownloadRequest` (quality="best") combined with a best-selected stream yields a broken selector. The failure is then handed to the segment-resume fallback, which only works if a partial file exists — otherwise the unit returns `None` (downloader.py:308-309) and the download fails entirely.

**Evidence:**
- Selector construction: downloader.py:446 (`"format": f"best[height<={quality_str}]"`).
- `quality_str` derivation: downloader.py:430 (`quality.replace("p", "") if quality else "720"`).
- Default quality `"best"`: dtos.py:20 (`quality: str = "best"` on `HLSDownloadRequest`).
- CLI default `QualityEnum.BEST` flows to `perform_download` as `str(stream.quality)` (cli.py:121, 325); when the selected stream's quality label is `"best"`, the literal is passed unchanged.
- yt-dlp semantics: a numeric `height<=N` filter requires a numeric bound; `height<=best` is not parseable (verified against yt-dlp format-selector grammar — height filters expect integers).

**Recommendation:** Normalize the quality value *before* building the selector. When the resolved quality is `"best"` (or any non-numeric label), use yt-dlp's bare `best` format with no `height<=` filter (or `best/bestvideo+bestaudio`); only apply `best[height<={n}]` when `quality_str` parses as an integer. A small guard (`if quality_str.isdigit(): selector = f"best[height<={quality_str}]" else: selector = "best"`) at downloader.py:430-446 closes the gap. Add a unit test passing `quality="best"` through `_download_with_ytdlp`'s option build to lock the behavior. Effort: trivial. Priority: recommended (mandatory classification due to correctness on the default path).

---

### DF-005: Progress callback's `video_id` argument is computed and discarded; keying is positional `url_index`

| Field | Value |
|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** The progress callback contract is documented as `(video_id, downloaded, total)` (dtos.py:27-28, downloader.py:286, 352, 575). But the callback actually created in `_create_progress_callback` (cli.py:26-45) ignores the first argument entirely:
```python
def callback(video_id: str, downloaded: int, total: int) -> None:
    _progress_manager.update_sync(url_index, downloaded, total)
```
`video_id` is declared but never used; the true key is the `url_index` captured at closure creation (cli.py:43). Any producer that computes a `video_id` to pass into this callback (the segment path passes `HLSDownloadRequest.video_url` or similar as the first positional) is doing wasted work, and the API is misleading: it advertises a `video_id` key that has no effect on state. This is a minor data-flow mislabel — the progress bookkeeping is keyed positionally, not by the advertised identifier, so two URLs that happen to share a `video_id` would still be tracked separately (good) but the documented `video_id` dimension is dead.

**Evidence:**
- Callback signature ignores `video_id`: cli.py:42-43 (`def callback(video_id: str, downloaded: int, total: int)` → `_progress_manager.update_sync(url_index, downloaded, total)`).
- `url_index` is the real key (closure var): cli.py:43; `_progress_manager.update_sync(url_index, ...)`; read via `_format_progress(url_count)` keyed by index (cli.py:48-57, 190-204).
- Advertised contract: dtos.py:27-28 (`progress_callback: Callable[[str, int, int], None]` — "(video_id, downloaded, total)"); downloader.py:286, 352, 575.

**Recommendation:** Either (a) drop the unused `video_id` parameter from the callback signature and the documented contract (simplify to `Callable[[int, int], None]` / plain `(downloaded, total)`), or (b) actually key progress by `video_id` if cross-call correlation is desired. Option (a) is preferred for a small project — it removes the dead parameter and the misleading docstring, reducing reader confusion during future maintenance. Update the call sites in downloader.py that pass a first positional to match. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 1 |

## Mandatory Fixes

- **DF-001** (HIGH, RUNTIME-ERROR) — Per-URL `progress_callback` is accepted by the default AUTO/yt-dlp download path but never invoked in `_download_with_ytdlp`; only the segment-resume fallback fires it. Live batch progress is permanently `0/0` on the most common path. Must fix.
- **DF-004** (MEDIUM, RUNTIME-ERROR) — yt-dlp format selector `best[height<=best]` is malformed when `quality` is the literal `"best"` (the `HLSDownloadRequest` default), breaking the default download path. Must fix.

## Advisory Recommendations

- **DF-002** (MEDIUM, BEST-PRACTICE) — `Settings()` is re-instantiated with subset field construction across the lifecycle (cli.py:92-95, 169, 292; downloader.py:115/292/591; segment_downloader.py:655; extractor.py:33; browser.py:23), fragmenting config propagation and silently dropping env-set fields on the CLI subset path. Construct once and pass down.
- **DF-003** (MEDIUM, SPEC-DEVIATION) — Single vs batch output-filename schemes are inconsistent; the single-command fallback embeds `stream.quality` (can be `"best"`/`"unknown"`), producing non-deterministic filenames. Unify the naming scheme and never embed the free-form quality label.
- **DF-005** (LOW, BEST-PRACTICE) — The progress callback's `video_id` argument is computed and discarded; keying is positional `url_index`. Remove the dead parameter and align the documented contract.

## Doc Updates Needed

- **DF-003** — Document a single canonical output-filename scheme in `docs/` and reference it from both `download` and `batch_download`; note that filenames must not depend on the free-form `Stream.quality` label.
- **DF-005** — Update the progress-callback contract docstring (dtos.py:27-28, downloader.py:286/352/575) to reflect the real `(url_index, downloaded, total)` keying, or rename the parameter to match actual use.
