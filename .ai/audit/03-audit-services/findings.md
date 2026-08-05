# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 Import | `uv run python -c "import vkdownloader.services.*"` | OK — all 8 service modules import cleanly. |
| R2 Lint | `uv run ruff check src/vkdownloader/services` | Pass ("All checks passed!"). |
| R2 Format | `uv run ruff format --check src/vkdownloader/services` | Pass ("9 files already formatted"). |
| R2 Types | `uv run mypy src/vkdownloader/services` | Pass ("no issues found in 9 source files"). |
| R3 Tests | `uv run pytest tests` | Pass — 248 passed in 9.56s. |
| R4 Dead code | AST + reference scan | See SRV-003. |

---

## Findings

### SRV-001: `_parse_quality_to_enum` raises ValueError for all p-suffixed quality strings, breaking browser cookie source

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** `_parse_quality_to_enum` (downloader.py:104-126) is called by `_resolve_cookies` (downloader.py:690) whenever `cookie_source == CookieSource.BROWSER`. The `quality` argument originates from `str(stream.quality)` in cli.py (cli.py:217), and the yt-dlp extractor always sets stream quality to `"{height}p"` format (extractor.py:180). The fallback path tries `QualityEnum(f"Q{normalized}")` (downloader.py:124), but `QualityEnum` is a `StrEnum` whose values are bare digits (`"240"`, `"720"`, etc.), not `"Q720"`. So `QualityEnum("Q720")` raises `ValueError`, making the fallback a no-op. Every `"Xp"` quality string raises `ValueError` — only `"best"` and `"worst"` succeed. Since yt-dlp extraction never produces bare `"best"`/`"worst"` strings, the browser-cookie path is completely broken for every quality request.

**Evidence:**
- extractor.py:180: `quality=f"{height}p" if height else "unknown"` — stream quality always carries the `p` suffix.
- cli.py:217: `str(stream.quality)` passed as `quality` to `perform_download`.
- downloader.py:690: `quality_enum = _parse_quality_to_enum(quality)` inside the `CookieSource.BROWSER` branch of `_resolve_cookies`.
- downloader.py:121-124: fallback computes `normalized = quality.rstrip("p")` then calls `QualityEnum(f"Q{normalized}")` — the `Q` prefix does not match any StrEnum value.
- Runtime confirmation (all p-suffixed qualities raise ValueError; only bare strings succeed): `720p -> ValueError`, `1080p -> ValueError`, `480p -> ValueError`, `360p -> ValueError`, `240p -> ValueError`, `best -> OK`, `worst -> OK`.
- The `ValueError` propagates to cli.py `download` command where `except ValueError` (cli.py:476-481) prints a misleading "Invalid URL format" message — the URL is valid; the real error is quality parsing.
- No test coverage exists for `_parse_quality_to_enum` or `_resolve_cookies` (grep in `tests/` returns zero matches).

**Recommendation:** Fix the fallback to look up the bare stripped value: `QualityEnum(normalized)` instead of `QualityEnum(f"Q{normalized}")`. Preferably, pass the `QualityEnum` directly from the composition root instead of round-tripping through `str(stream.quality)`. Add test coverage for the `p`-suffix path. Effort: trivial. Priority: mandatory.

---

### SRV-002: Parallel download path ignores Retry-After header

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** When max_concurrent_downloads > 1 (the default is 4), segment downloads use the parallel path (_run_parallel_download_with_backoff, segment_downloader.py:143-174). This function calls _compute_backoff_delay with None for retry_after_seconds (segment_downloader.py:170), passing None for the Retry-After header value. In contrast, the sequential path (_retry_429_with_backoff, downloader_throttle.py:194-195) properly calls _parse_retry_after(response) and passes the result. The Retry-After header is a server directive telling the client when it is safe to retry; ignoring it in the default download path means the client may retry too early, triggering cascading 429s from the CDN.
**Evidence:**
- segment_downloader.py:170: `delay = _compute_backoff_delay(response.status, attempt, None)` — hardcodes None, ignoring Retry-After header.
- downloader_throttle.py:194-195: sequential path correctly does `retry_after_seconds = _parse_retry_after(response)` then `delay = _compute_backoff_delay(response.status, attempt, retry_after_seconds)`.
- `_parse_retry_after` is tested in test_downloader_throttle.py (TestParseRetryAfter, 4 tests) for the sequential path. The parallel path function `_run_parallel_download_with_backoff` has zero test coverage.
- Default Settings.max_concurrent_downloads is 4 (config.py:79-84), so the parallel path is the default code path.

**Recommendation:** Import `_parse_retry_after` into segment_downloader.py and pass the parsed header value to `_compute_backoff_delay` in `_run_parallel_download_with_backoff`. Add test coverage. Effort: small. Priority: recommended.

---

### SRV-003: _do_parallel_download_attempt is a no-op wrapper with zero added logic

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_do_parallel_download_attempt` (segment_downloader.py:190-216) is a pure pass-through wrapper around `_run_parallel_download_with_backoff`. Its entire body is a single call that forwards all nine arguments and returns the result with no transformation, no logging, no exception handling, and no validation. It is called only once, from `_try_single_download_attempt` (segment_downloader.py:236), which already adds real value by catching aiohttp.ClientError.
**Evidence:**
- segment_downloader.py:190-216: body is just `result = await _run_parallel_download_with_backoff(...)` then `return result`.
- grep confirms defined at line 190, called only at line 236. No other references in src/ or tests/.
- _try_single_download_attempt (line 219-249) adds real value (catches aiohttp.ClientError); _do_parallel_download_attempt adds nothing comparable.

**Recommendation:** Inline the call in _try_single_download_attempt, removing the intermediate function. Effort: trivial. Priority: recommended.

---
### SRV-004: `download_hls_with_resume` skips segment-preservation log on CancelledError during shutdown

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `download_hls_with_resume` (segment_downloader.py:816-831) wraps `_run_download_session` in a `try/except Exception` block that calls `_log_preserve_segments` on failure. However, `asyncio.CancelledError` is a subclass of `BaseException`, not `Exception`, so it is NOT caught by this handler. When a download is cancelled via the shutdown signal path, the exception propagates without logging "preserving_segments_for_resume". The segments themselves are still preserved on disk (segment cleanup only happens on the success path in `_tally_and_merge`), but users receive no visibility that resume state was preserved.

**Evidence:**
- segment_downloader.py:829-831: `except Exception: _log_preserve_segments(segments_dir); raise` — does not catch CancelledError.
- `_download_segment_concurrent` (segment_downloader.py:611, 614, 642, 647) raises `asyncio.CancelledError("Download cancelled by user")` when shutdown is detected.
- Python 3.12: `asyncio.CancelledError` inherits from `BaseException`, not `Exception` (verified: `issubclass(asyncio.CancelledError, Exception)` is False).
- Segments are preserved because `_tally_and_merge` only calls `_cleanup_segments` on the success path; on cancellation the segments remain on disk.

**Recommendation:** Change `except Exception` to `except BaseException` (or add a separate `except asyncio.CancelledError` handler) so that segment preservation is logged on all exit paths. Alternatively, move `_log_preserve_segments` into a `finally` block guarded by a success flag. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 2 |

## Mandatory Fixes

- **SRV-001** (HIGH) — `_parse_quality_to_enum` raises ValueError for all p-suffixed quality strings, completely breaking `--cookie-source browser` for every quality request. Misleading "Invalid URL format" error shown to users.
- **SRV-002** (MEDIUM) — Parallel download path (the default when `max_concurrent_downloads > 1`) ignores the `Retry-After` HTTP header, violating the fail-fast/retry contract and risking cascading 429s from the CDN.

## Advisory Recommendations

- **SRV-003** (LOW) — `_do_parallel_download_attempt` is a no-op wrapper with zero added logic; unnecessary indirection in an already deep call chain.
- **SRV-004** (LOW) — `download_hls_with_resume` skips the segment-preservation log on `CancelledError` because `except Exception` does not catch `BaseException` subclasses.
