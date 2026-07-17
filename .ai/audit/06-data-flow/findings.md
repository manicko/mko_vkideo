### DF-004: Corrupt/partial segment file is treated as complete on resume

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (`_download_segment_concurrent`, `_create_segment_download_tasks`) |
| **Classification** | mandatory |

**Description:** The segment-level resume logic treats any existing `.ts` file with `size > 0` as successfully downloaded and skips re-downloading it (`segment_downloader.py:563`). A segment that was partially written when the process crashed (or was truncated by an interrupted write) leaves a non-empty `.ts` on disk. On the next run, `_create_segment_download_tasks` excludes it from the work list (`:645-646`), and `_download_segment_concurrent` returns `True` for it (`:563-564`). The merge then concatenates the corrupt segment into the final MP4, producing a broken/glitchy file — often with no error if ffmpeg still completes. This silently corrupts output while reporting success.

**Evidence:**
- `segment_downloader.py:563-564`: `if segment_path.exists() and segment_path.stat().st_size > 0: result = True`
- `segment_downloader.py:645-646`: tasks only created for segments that do not exist OR have `st_size == 0`, so a partial non-empty file is never re-fetched.
- `_process_downloaded_segments:504-511`: merge proceeds when `downloaded_count == len(segments)`; a corrupt segment counts toward completion.

**Recommendation:** Validate segment integrity before accepting a cached `.ts` (e.g. compare expected size from the playlist `#EXTINF`/byte-range, or re-fetch if a known-good size is available), or at minimum verify ffmpeg merge return code and treat merge failure as a retryable error rather than returning the corrupt output. At a minimum, do not treat `size > 0` as "complete" for resume.

---

### DF-005: AUTO download method does not apply cookie resolution

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download` AUTO branch) |
| **Classification** | advisory |

**Description:** Both `YTDLP` (`:704-720`) and `FFMPEG` (`:721-743`) branches call `_resolve_cookies()` to apply `cookie_source`-based authentication before download. The `AUTO` branch (`:744-756`) calls `download_with_ytdlp_with_resume_fallback` directly without `_resolve_cookies`. With `cookie_source=BROWSER`, the first yt-dlp attempt therefore runs without cookies; only the failure-triggered segment resume forces a browser refresh. This is an inconsistency that wastes the first attempt and diverges from the other methods' behavior.

**Evidence:**
- `downloader.py:744-756`: AUTO branch lacks the `_resolve_cookies` call present in the YTDLP/FFMPEG branches (`downloader.py:705-707`, `:722-724`).

**Recommendation:** Call `_resolve_cookies` in the AUTO branch as well so cookie auth is applied on the first attempt, matching YTDLP/FFMPEG and reducing avoidable failures. Effort: trivial.

---

### DF-006: Batch summary masks unexpected exceptions as "cancelled"

| Field | Value |
|-------|-------|
| **ID** | DF-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (`_run_batch_with_progress`, `_download_single`) |
| **Classification** | advisory |

**Description:** In `_run_batch_with_progress`, tasks are first awaited via `asyncio.as_completed`, then collected again via `asyncio.gather(*tasks, return_exceptions=True)`. A task whose `_download_single` raised an unexpected (non-CancelledError) exception is represented in `results` as the exception object; the fallback `r if isinstance(r, tuple) else (urls[i], "", "cancelled")` labels any such result as `"cancelled"`. A genuine bug surfaced as an exception is therefore reported to the user as an intentional cancellation, hiding the real failure and its cause in the summary.

**Evidence:**
- `cli.py:229-233`: `results = await asyncio.gather(*tasks, return_exceptions=True)` followed by fallback that maps non-tuple results to status `"cancelled"`.
- `cli.py:153-156`: `_download_single` re-raises `Exception` after logging, so it reaches `gather` as an exception object rather than a tuple.

**Recommendation:** Distinguish `asyncio.CancelledError` from other exceptions in the result normalization (e.g. check `isinstance(r, Exception)` and label as `"error"`/`"failed"` with the message), so real failures are visible in the summary. Effort: small.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

- DF-001 (HIGH): yt-dlp path ignores `Settings.download_timeout`.
- DF-002 (MEDIUM): Output filename collision on identical sanitized titles → silent overwrite (data loss).
- DF-003 (MEDIUM): `CookieSource.FILE` accepted by CLI but silently treated as NONE (doc/behavior deviation).
- DF-004 (MEDIUM): Corrupt/partial `.ts` segment accepted as complete on resume → broken output.

## Advisory Recommendations

- DF-005 (LOW): AUTO method should call `_resolve_cookies` like YTDLP/FFMPEG.
- DF-006 (LOW): Batch summary should not relabel unexpected exceptions as "cancelled".

## Doc Updates Needed

- DF-003: Docs state `CookieSource.FILE` raises `NotImplementedError`; in practice primary paths silently ignore it. Either fix code to fail fast (preferred) or correct the docs.
- DF-001: Docs advertise `DOWNLOAD_TIMEOUT` as the download timeout, but the yt-dlp path hardcodes 180s. Docs should reflect actual (broken) behavior until fixed, then be re-verified.

---

## Runtime Verification Record

- **R1 — Import full pipeline:** `uv run python -c "import vkdownloader.cli, vkdownloader.config, vkdownloader.services.downloader, vkdownloader.services.extractor, vkdownloader.services.downloader_throttle"` → `IMPORT OK`.
- **R2 — Linter / type checker:** `uv run ruff check src/vkdownloader` → `All checks passed!` (exit 0). `uv run mypy src/vkdownloader` → `Success: no issues found in 23 source files` (exit 0). Note: mypy reports `pyproject.toml: note: unused section(s): module = ['tests.*']`.
- **R3 — Test suite:** `uv run pytest` → `223 passed` (exit 0).

All findings in this report were identified by static trace of the data flow (cli → extractor → quality selector → downloader → segment/yt-dlp/ffmpeg → output) and cross-checking against docs; runtime verification confirms the pipeline is importable, type-clean, lint-clean, and green, so the issues are latent correctness/data-integrity defects rather than build/runtime failures.
