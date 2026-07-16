# Phase 06 Validation Report — End-to-End Data Flow

**Executor:** validator  
**Source Findings:** .ai/audit/06-data-flow/findings.md  
**Status:** complete

---

## Findings

### DF-001: Per-URL progress callback accepted by default download path but never invoked

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** The batch download flow creates a per-URL `progress_callback` and threads it through `perform_download` → `download_with_ytdlp_with_resume_fallback` → `_download_with_ytdlp`. However, `_download_with_ytdlp` (downloader.py:416-500) never calls `progress_callback` — it does not even accept the parameter in its signature. The callback is only passed to the segment-resume path (`download_hls_with_resume`, via `_attempt_segment_resume`) which executes only on yt-dlp *failure* with a partial file. On the default `DownloadMethod.AUTO` path (downloader.py:644-650), yt-dlp downloads complete inside `_download_with_ytdlp` and the callback is silently dropped.

ProgressManager stores `0/0` for successfully downloaded URLs in the batch, giving users a false "no progress" signal.

**Evidence:**
- Callback creation at cli.py:26-45 (`_create_progress_callback`), invoked per-URL at cli.py:176
- `_download_with_ytdlp` signature (downloader.py:416-422): no `progress_callback` parameter
- `download_with_ytdlp_with_resume_fallback` calls `_download_with_ytdlp` at downloader.py:297 without callback
- Segment path only fired on failure: `_attempt_segment_resume` at downloader.py:313-317 → `download_hls_with_resume` at downloader.py:393-405

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed: `_download_with_ytdlp` does not accept or invoke `progress_callback`. The callback is threaded through `download_with_ytdlp_with_resume_fallback` to the segment fallback but dead-dropped on the primary yt-dlp success path. This is a genuine implementation defect causing silent data loss in progress reporting.
> - **See also:** DF-005 (related callback contract issue)

---

### DF-002: Settings() re-instantiated across the lifecycle with subset field construction

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description:** `Settings` (a Pydantic `BaseSettings`) is re-instantiated in multiple places. Several call sites construct it with only a subset of fields, fragmenting config propagation. The CLI-side subset construction at cli.py:93-95 (`Settings(cookie_source=cookie_source, max_retries=actual_max_retries, ssl_verify=ssl_verify)`) and cli.py:292 (`Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)`) silently drop `user_agent`, `download_dir`, `throttled_rate`, `http_chunk_size`, `max_concurrent_downloads`, `timezone`, `locale` to their defaults, ignoring environment-set values.

**Evidence:**
- Subset construction cli.py:93-95 drops environment-configured fields
- Single-field reads cli.py:92, cli.py:169, cli.py:431 each instantiate `Settings()` independently
- Fallback instantiations in downloader.py:115, 292, 591; segment_downloader.py:655; extractor.py:33; browser.py:23

> **Validation Note:**
> - **Action:** Reclassified from BEST-PRACTICE to SPEC-DEVIATION
> - **Detail:** This is not a best-practice cleanup opportunity — it is an actual spec deviation causing config values to be silently ignored. The code violates the principle that environment-configured settings should propagate end-to-end.
> - **See also:** —

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
- Batch (`_download_single`): `{safe_title}_{video.id}.mp4` or `{index}_{video.id}.mp4`
- Single (`download`): `{safe_title}_{video.id}.mp4` or `{video.id}_{stream.quality}.mp4`

The single-command fallback embeds `stream.quality` (cli.py:321), which can be `"best"` (when `QualityEnum.BEST` selects a stream) or `"unknown"` (when yt-dlp extracts a stream without height). This produces non-deterministic filenames like `{id}_best.mp4` / `{id}_unknown.mp4`.

Additionally, when `stream.quality` is `"best"`, this combines with DF-004 to create `best[height<=best]` format selector errors during download.

**Evidence:**
- Batch scheme: cli.py:113-117
- Single scheme: cli.py:317-321 (`{video.id}_{stream.quality}.mp4` fallback)
- `QualityEnum.BEST` flows through: quality.py:66-68 returns stream with `.quality` = actual stream's quality value (e.g., "1080" or "best" from browser extraction)
- Browser extraction sets quality="best": extractor.py:226

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed: Different naming schemes between batch and single commands. The single command fallback includes `stream.quality` which can be non-numeric ("best", "unknown"), creating inconsistent and potentially confusing filenames. This is a spec deviation from expected consistent behavior.
> - **See also:** DF-004 (both involve "best" quality handling)

---

### DF-004: yt-dlp format selector `best[height<=best]` breaks for literal "best" quality (HLSDownloadRequest default)

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/models/dtos.py` |
| **Classification** | mandatory |

**Description:** `_download_with_ytdlp` builds the yt-dlp format selector as `f"best[height<={quality_str}]"` (downloader.py:446), where `quality_str = quality.replace("p", "") if quality else "720"` (downloader.py:430). When `quality` is the literal string `"best"` (the default value in `HLSDownloadRequest.quality` at dtos.py:20), `quality_str` becomes `"best"`, producing the invalid selector `best[height<=best]`. yt-dlp rejects this as a malformed format string because `height<=best` is not a valid numeric comparison.

This breaks downloads on the default path when:
1. `QualityEnum.BEST` is selected (CLI default)
2. The selected stream has `quality="best"` (browser extraction case at extractor.py:226)

**Evidence:**
- Selector construction: downloader.py:446 (`"format": f"best[height<={quality_str}]"`)
- `quality_str` derivation: downloader.py:430 (`quality.replace("p", "") if quality else "720"`)
- Default quality `"best"`: dtos.py:20
- Browser extraction sets quality="best": extractor.py:226

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed: yt-dlp format selector syntax requires numeric bound for `height<=N` filter. The literal "best" produces an invalid selector. This is a correctness bug on the default code path.
> - **See also:** DF-003 (both involve quality="best" handling)

---

### DF-005: Progress callback's `video_id` argument is computed and discarded; keying is positional `url_index`

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** The progress callback contract is documented as `(video_id, downloaded, total)` (dtos.py:27-28, downloader.py:286, 352, 575). The callback created in `_create_progress_callback` (cli.py:42-43) ignores the first argument and keys solely by `url_index`:
```python
def callback(video_id: str, downloaded: int, total: int) -> None:
    _progress_manager.update_sync(url_index, downloaded, total)  # video_id unused
```

Meanwhile, `_process_downloaded_segments` (segment_downloader.py:411-417) computes a `video_id` from the URL and passes it as the first positional argument. This is misleading: the API advertises `video_id` keying but actually uses positional indexing.

**Evidence:**
- Callback signature ignores `video_id`: cli.py:42-43
- `url_index` is the real key (closure variable): cli.py:43; `_progress_manager.update_sync(url_index, ...)`
- `video_id` computed and passed in segment path: segment_downloader.py:411-417

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Confirmed: The `video_id` parameter in the callback signature is never used. The progress bookkeeping is keyed by `url_index`. This is an API mislabel — the documented contract does not match implementation.
> - **See also:** DF-001 (progress callback never invoked context)

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 0 | — |
| Reclassified | 1 | DF-002 (BEST-PRACTICE → SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

None

### Merged Findings

None

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| DF-002 | BEST-PRACTICE | SPEC-DEVIATION | Configuration values are silently dropped on the CLI subset path — this causes actual incorrect behavior (env-configured values ignored), not just code style issues |

---

## Rollout Analysis

### Dependency Chains

- **DF-001** (progress callback) and **DF-005** (callback contract) can be fixed together since both involve the progress callback mechanism. DF-005's simplification (removing unused `video_id` parameter) should be done first to clarify the contract before adding invocation in DF-001.

- **DF-003** (filename scheme) and **DF-004** (format selector) both involve handling of `"best"` quality values. Fixing DF-004 first (normalize quality before selector) may reduce the impact of DF-003's filename inconsistency, but both should be addressed for complete consistency.

### Sequencing Concerns

1. DF-004 should be fixed first (format selector correctness) — this is on the default path and causes outright failures
2. DF-001 second (progress callback invocation) — user-visible data integrity defect
3. DF-003 third (filename unification) — user experience consistency
4. DF-005 fourth (callback contract simplification) — can be done last after progress callback is functional

### Rollout Safety

- DF-004: Low risk. Adding a guard for non-numeric quality values preserves backward compatibility for numeric values while fixing the broken "best" case.

- DF-001: Medium risk. Adding yt-dlp progress hooks changes the timing of callback invocations. Must verify segment progress updates still work correctly after the fix.

- DF-003: Low risk. Only affects filename generation; does not change download logic. Existing files retain their names.

- DF-005: Low risk. Simplifying the callback signature to `(downloaded, total)` requires updating call sites but does not change core logic.

---

## Execution Validation

All findings target real, existing code issues. No rejected findings. No assumptions invalidated.

---

## Warnings

- **Architectural Risk:** The current design threads `progress_callback` through multiple function signatures but only uses it in one execution path (segment fallback). Consider whether the callback should be unified or if progress reporting should be handled differently for yt-dlp vs segment downloads.

- **Documentation inconsistency:** The docs (vkdownloader-overview.md) mention progress tracking but do not specify the exact callback contract. The documented behavior does not match the implementation (video_id vs url_index keying).

---

## Required Fixes

1. **DF-004** — yt-dlp format selector produces invalid `best[height<=best]` on default quality path. Add guard: if quality is non-numeric, use bare `best` selector without height filter.

2. **DF-001** — Progress callback is never invoked on successful yt-dlp downloads. Add progress hooks to `_download_with_ytdlp` to call the callback during download, or invoke at minimum start/end.

---

## Advisory Recommendations

1. **DF-002** — Construct `Settings` once per invocation in CLI `download()` / `batch_download()` and pass the single instance down through all layers, merging CLI overrides with environment-loaded values.

2. **DF-003** — Unify output-filename scheme across both commands. Adopt `index` fallback (not quality) for single downloads, and never embed the free-form `Stream.quality` label in filenames.

3. **DF-005** — Align the documented callback contract with actual implementation. Either remove the unused `video_id` parameter or implement video_id-based keying consistently.