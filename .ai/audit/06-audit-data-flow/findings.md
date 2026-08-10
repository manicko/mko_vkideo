# Phase 06 Audit Findings - End-to-End Data Flow

**Executor:** audit-executor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes

## Verification Results

| Check | Command | Result |
|-------|---------|--------|
| R1 - Import | python import | PASS |
| R2 - Lint | uv run ruff check src/ | PASS |
| R2 - Format | uv run ruff format --check src/ | FAIL (services/downloader.py) |
| R2 - Types | uv run mypy | FAIL (pre-existing correlation.py) |
| R3 - Tests | uv run pytest | PASS (325 passed) |

## Findings

### DF-001: Quality enum degrades from QualityEnum.BEST to stream quality string (e.g. "1080p")

| Severity | CRITICAL |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/downloader.py |
| Classification | mandatory |

**Description:**

download_video() selects the best stream via QualitySelector.select(video.streams, quality) where quality is the user QualityEnum (e.g. QualityEnum.BEST). The selected Stream carries stream.quality = "1080p" (set by extractor at extractor.py:175 as f"{height}p"). download_video passes str(stream.quality) - i.e. "1080p" - as the quality parameter to perform_download().

Inside perform_download(), _resolve_cookies() and _attempt_segment_resume() call _parse_quality_to_enum(quality) and compare to QualityEnum.BEST. Since quality is "1080p", _parse_quality_to_enum("1080p") returns QualityEnum.Q1080, and the == QualityEnum.BEST check always fails.

Consequence: browser stream selection (updating m3u8_url from fresh browser extraction) is dead code in production. The stale m3u8_url from yt-dlp extraction is reused for both cookie extraction and segment download resume.

**Evidence:**
- downloader.py:1208: str(stream.quality) passed as quality to perform_download
- downloader.py:944: if quality_enum == QualityEnum.BEST -- always False
- downloader.py:690: same check in _attempt_segment_resume
- extractor.py:175: quality=f"{height}p" if height else "unknown"
- enums.py:16: BEST = "best"

**Recommendation:** Pass original QualityEnum through pipeline instead of str(stream.quality). Fix download_video line 1208 to pass the original quality enum value. Effort: small. Priority: mandatory.

### DF-002: Single download command has no correlation ID

| Severity | MEDIUM |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/cli.py |
| Classification | advisory |

**Description:**

The batch path routes every URL through _download_single() (cli.py:217-220), which binds a per-operation correlation_id. The single download command calls download_video() directly (cli.py:459) without binding a correlation ID. All log entries from single-download lack correlation_id, making tracing across extract -> select -> download impossible.

**Evidence:**
- cli.py:217-220: batch binds correlation ID before download_video
- cli.py:455-466: single download calls download_video with no correlation binding
- downloader.py:1142: download_video does not bind correlation ID internally

**Recommendation:** Move correlation ID binding into download_video() itself (try/finally), so both single and batch paths are covered. Effort: trivial. Priority: recommended.

### DF-003: Segment download progress callback fires only once, at merge time

| Severity | HIGH |
| Type | BEST-PRACTICE |
| Affected Modules | src/vkdownloader/services/segment_downloader.py |
| Classification | advisory |

**Description:**

The segment download path fires the progress callback only once in _tally_and_merge (line 586-588), after all segment tasks complete. There is no per-segment progress during the actual download. For batch downloads, _poll_progress_display polls every 1.0s, but segment progress remains at 0/total until merge time. yt-dlp and ffmpeg paths fire progress per-iteration; only segment downloads have this gap.

**Evidence:**
- segment_downloader.py:584-588: _tally_and_merge - single callback at end
- segment_downloader.py:646-699: _download_segment_concurrent - never calls progress_callback
- cli.py:176: _poll_progress_display polls every 1.0s

**Recommendation:** Call progress_callback per-segment in _download_segment_concurrent, or use asyncio.as_completed in _await_and_cancel to fire on each segment completion. Effort: medium. Priority: recommended.

### DF-004: MAX_RESUME_RETRIES hardcoded; --max-retries does not control application-level fallback

| Severity | MEDIUM |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/downloader.py |
| Classification | advisory |

**Description:**

download_with_ytdlp_with_resume_fallback() uses hardcoded MAX_RESUME_RETRIES = 3 (downloader.py:57) as the retry loop bound (line 585). The --max-retries CLI flag overrides settings.max_retries via model_copy (line 1183), but this only affects yt-dlp subprocess -R/--fragment-retries and segment download internal retries -- NOT the application-level fallback retry count. Docs (configuration.md:112) claim max_retries applies to "single downloads as well as batch downloads" with "automatically retry up to this number of attempts," but the fallback path is hardcoded.

**Evidence:**
- downloader.py:57: MAX_RESUME_RETRIES = 3
- downloader.py:585: while retry_count <= MAX_RESUME_RETRIES
- downloader.py:296-299: --max-retries affects only yt-dlp subprocess flags

**Recommendation:** Replace MAX_RESUME_RETRIES with settings.max_retries, or add a dedicated setting. Effort: trivial. Priority: recommended.

### DF-005: FFMPEG progress adapter always reports 100% completion

| Severity | MEDIUM |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/downloader.py |
| Classification | advisory |

**Description:**

The FFMPEG progress adapter (downloader.py:1079-1083) sets downloaded = fp.total_size, making downloaded == total on every callback -- always reports 100%. ffmpeg's -progress output provides out_time_us (time), not byte progress. No conversion is implemented.

**Evidence:**
- downloader.py:1080-1081: downloaded = fp.total_size; progress_callback(video_id, downloaded, downloaded)
- ffmpeg_utils.py:46-56: FfmpegProgress has out_time_us but no downloaded_bytes field

**Recommendation:** Either convert out_time_us to byte progress (requires total duration), accept time-based progress and adapt ProgressManager, or document that ffmpeg path does not support byte-level progress. Effort: medium. Priority: recommended.

### DF-006: Token refresh during segment download blocked by cookie_source check

| Severity | HIGH |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/segment_downloader.py |
| Classification | advisory |

**Description:**

_refresh_token_and_retry() (segment_downloader.py:417-423) guards with if settings.cookie_source != CookieSource.BROWSER: return None. Since cookie_source == NONE is the default, token refresh is impossible during segment playlist fetch retry (403/410). This is inconsistent with _attempt_segment_resume() (downloader.py:681), which uses force_browser=True to bypass the check. So yt-dlp-failure recovery can force browser extraction, but the segment download internal retry cannot.

**Evidence:**
- segment_downloader.py:417-423: if settings.cookie_source != CookieSource.BROWSER: return None
- downloader.py:681-683: _attempt_segment_resume calls extract_streams_with_cookies(video_url, force_browser=True)

**Recommendation:** Remove the cookie_source != BROWSER guard in _refresh_token_and_retry, or make it use force_browser=True consistently. Effort: small. Priority: recommended.

### DF-007: Temp cookie file created with world-readable permissions (0644) on Unix

| Severity | HIGH |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/downloader.py, src/vkdownloader/services/cookies.py |
| Classification | mandatory |

**Description:**

_create_temp_cookie_file() (downloader.py:87) uses tempfile.mkstemp() which creates files at mode 0644 on Unix (default umask 022). Meanwhile, cookies.py has _write_netscape_cookie_file() (line 72) which correctly uses os.open() with 0o600 -- but this function is NOT used by the yt-dlp download path. The temp cookie file contains live VK session cookies. If the process crashes before the finally cleanup (downloader.py:909), cookies remain world-readable on disk.

**Evidence:**
- downloader.py:87: tempfile.mkstemp(suffix=".cookies.txt", prefix="vk_cookies_")
- cookies.py:72: os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
- downloader.py:909-912: cleanup only in finally block

**Recommendation:** Replace tempfile.mkstemp() with os.open() at 0o600, or call os.chmod(cookie_file, 0o600) immediately after creation. Effort: trivial. Priority: mandatory.

### DF-008: Partial yt-dlp output file not cleaned up on failure

| Severity | MEDIUM |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/downloader.py |
| Classification | advisory |

**Description:**

yt-dlp writes directly to output_file via -o flag (downloader.py:288). When yt-dlp fails, _attempt_segment_resume() deletes the partial file at line 714, but only if browser_streams is truthy and no exception is raised. If browser extraction fails (empty streams), or if QualityParseError/QualityNotAvailableError is raised, the partial file persists. When all retries are exhausted (line 632), the partial file from the last attempt is also left on disk. The CLI reports "Download failed" but the partial file remains.

**Evidence:**
- downloader.py:585-632: retry loop with no cleanup in exhaustion path
- downloader.py:684-714: output_file.unlink() only inside if browser_streams: block

**Recommendation:** Add a finally block in download_with_ytdlp_with_resume_fallback to clean up the partial file when returning None. Consider downloading to a .part temp file and renaming on success. Effort: small. Priority: recommended.

### DF-009: Progress units are inconsistent across download methods

| Severity | MEDIUM |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/downloader.py, src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/downloader_throttle.py |
| Classification | advisory |

**Description:**

The progress_callback protocol is Callable[[str, int, int], None] (video_id, downloaded, total), but each method reports different units: yt-dlp reports bytes, segment reports segment counts, ffmpeg reports total_size for both (always 100%). ProgressManager.get_formatted_progress() (downloader_throttle.py:137-139) displays video_{i}: {downloaded}/{total} with no unit context. For batches with mixed methods, units are inconsistent. Docs (vkdownloader-overview.md:248-254) claim progress shows "Downloaded segments / Total segments" -- only true for segment downloads.

**Evidence:**
- downloader_throttle.py:137-139: format string with no unit
- downloader.py:838: progress_callback(video_id, downloaded, total) -- bytes
- segment_downloader.py:588: progress_callback(video_id, downloaded_count, len(segments)) -- segment counts

**Recommendation:** Add a unit parameter to the callback protocol, or normalize all progress to bytes. At minimum, include unit label in the display. Effort: medium. Priority: recommended.

### DF-010: Segment files written non-atomically; partial writes corrupt resume state

| Severity | MEDIUM |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/segment_downloader.py |
| Classification | advisory |

**Description:**

Both _download_segment_sequential() (line 167-168) and _run_parallel_download_with_backoff() (line 225-226) write directly to the final .ts path. If the process crashes during f.write(), the file is truncated but has non-zero size. On the next attempt, _create_segment_download_tasks() (line 720) checks only st_size > 0 and skips the segment -- a corrupted segment is treated as complete. The merge step then produces a corrupted output file.

**Evidence:**
- segment_downloader.py:167-168: with open(output_path, "wb") as f: f.write(content)
- segment_downloader.py:720: if segment_path.exists() and segment_path.stat().st_size > 0: continue
- No Content-Length verification anywhere in the download path

**Recommendation:** Write to a temp file (e.g. {idx:05d}.ts.tmp) and atomically rename after successful write. Optionally verify segment size against Content-Length. Effort: small. Priority: recommended.

### DF-011: Single download command lacks --max-retries override

| Severity | LOW |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/cli.py |
| Classification | advisory |

**Description:**

The batch command exposes --max-retries / -r (cli.py:576-581). The download command has no such option. Users cannot override max_retries for single downloads without environment variables. Docs (configuration.md:105-112) imply max_retries applies to single downloads.

**Evidence:**
- cli.py:418-444: download command -- no --max-retries option
- cli.py:576-581: batch command -- has --max-retries

**Recommendation:** Add --max-retries / -r to the download command for CLI parity. Effort: trivial. Priority: recommended.

### DF-012: _attempt_segment_resume uses stale m3u8_url when BEST quality requested

| Severity | HIGH |
| Type | SPEC-DEVIATION |
| Affected Modules | src/vkdownloader/services/downloader.py |
| Classification | advisory |

**Description:**

Downstream consequence of DF-001. When yt-dlp fails and _attempt_segment_resume() forces browser extraction (downloader.py:681-683), the quality_enum == QualityEnum.BEST check (line 690) always fails due to quality degradation. The else branch (line 699-704) logs "browser_streams_selected_with_preselected_url" and keeps the stale m3u8_url from the original yt-dlp extraction instead of using the fresh browser URL. Browser cookies are used, but the m3u8_url (pointing to token-protected playlist) is old/expired. This is the critical link in the failure cascade: DF-001 -> DF-012 -> DF-006.

**Evidence:**
- downloader.py:684-704: quality check fails, stale m3u8_url retained
- downloader.py:716-724: HLSDownloadRequest uses stale m3u8_url

**Recommendation:** Fix DF-001. This automatically resolves DF-012. Effort: small. Priority: recommended.

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 3 |
| MEDIUM | 5 |
| LOW | 1 |
| **Total** | **10** |

## Mandatory Fixes

1. **DF-001** (CRITICAL) -- Fix quality enum degradation in download_video -> perform_download boundary. Pass original QualityEnum instead of str(stream.quality).
2. **DF-007** (HIGH) -- Use secure file permissions (0o600) for temp cookie file created by _create_temp_cookie_file.

## Advisory Recommendations

1. **DF-002** -- Centralize correlation ID binding in download_video().
2. **DF-003** -- Add per-segment progress callback during download.
3. **DF-004** -- Use settings.max_retries instead of hardcoded MAX_RESUME_RETRIES.
4. **DF-005** -- Fix FFMPEG progress adapter to report actual progress, not 100% always.
5. **DF-006** -- Remove cookie_source guard in _refresh_token_and_retry during segment download.
6. **DF-008** -- Clean up partial output file on download failure in finally block.
7. **DF-009** -- Normalize progress units or add unit labels to ProgressManager display.
8. **DF-010** -- Use atomic writes (temp file + rename) for segment files.
9. **DF-011** -- Add --max-retries to single download command for CLI parity.
10. **DF-012** -- Resolved by fixing DF-001.

## Doc Updates Needed

- docs/11-guides/configuration.md:112 -- clarify max_retries does NOT control MAX_RESUME_RETRIES until DF-004 is fixed.
- docs/01-tools/vkdownloader-overview.md:248-254 -- progress format docs claim "segments/total" for all URLs; yt-dlp and ffmpeg report bytes. Update after DF-009.
- docs/01-tools/vkdownloader-overview.md:63 -- CookieSource.FILE documented as NotImplementedError; code raises ValidationError via Pydantic validator.

## Risk Assessment

**Critical failure cascade (DF-001 -> DF-012 -> DF-006):**

For default config (cookie_source=none, --quality best, method auto):

1. yt-dlp extraction selects best stream (quality="1080p")
2. download_video passes "1080p" (not "best") to perform_download
3. yt-dlp download fails (token expired or throttling)
4. _attempt_segment_resume forces browser extraction, gets fresh cookies and m3u8 URL
5. Due to DF-001, quality_enum is Q1080 (not BEST), so fresh browser m3u8_url is NOT selected
6. Stale m3u8_url with fresh cookies passed to download_hls_with_resume
7. Playlist fetch returns 403 (stale token)
8. _refresh_token_and_retry returns None due to DF-006 (cookie_source=NONE)
9. Entire download fails despite recovery mechanism

Fixing DF-001 resolves steps 5-6. Fixing DF-006 prevents step 8.
