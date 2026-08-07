# Phase 03 Audit Findings -- Validated Report

**Phase:** 03-audit-services (Service Layer & Business Logic)
**Source (audited):** `.ai/audit/03-audit-services/findings.md`
**Validator:** validator (evidence-driven, conservative)
**Scope:** `src/vkdownloader/services/` -- downloader.py, segment_downloader.py, downloader_throttle.py, extractor.py, quality.py, cookies.py, signal_handlers.py
**Status:** validated
**Validated:** yes

This report validates each Phase 03 finding against the current source tree and runtime behavior. It is self-contained; the original findings file need not be consulted.

---

## Runtime Verification Summary

Re-confirmed the auditor R1-R4 checks against the current tree:

| Step | Command | Result |
|------|---------|--------|
| R1 Import | all 8 service modules import cleanly | OK |
| R2 Lint | `ruff check src/vkdownloader/services` | Pass ("All checks passed!") |
| R2 Format | `ruff format --check src/vkdownloader/services` | Pass ("9 files already formatted") |
| R2 Types | `mypy src/vkdownloader/services` | Pass ("Success: no issues found in 9 source files") |
| R3 Tests | `pytest tests` | 248 passed in 9.51s |
| R4 Dead code | AST + reference scan | See findings |

---

## Validation Evidence Log

Each finding was verified against current source and re-run at runtime:

| Check | Method | Finding(s) |
|-------|--------|------------|
| Runtime -- `_parse_quality_to_enum` on p-suffix / bare / named inputs | `python -c` direct invocation | SRV-001 |
| Runtime -- `QualityEnum("Q720")` lookup | direct StrEnum construction | SRV-001 |
| Runtime -- `issubclass(asyncio.CancelledError, Exception)` | `python -c` | SRV-004 |
| Runtime -- shutdown-signal path through `download_hls_with_resume` | simulated `shutdown_event.set()` + mocked deps | SRV-004 |
| Runtime -- external `task.cancel()` on `download_hls_with_resume` | `asyncio.create_task` + cancel | SRV-004 |
| Runtime -- `_await_and_cancel` swallowing CancelledError | direct invocation with raising child | SRV-004 |
| Source -- `QualityEnum` StrEnum values | `enums.py:6-17` | SRV-001 |
| Source -- `Stream.quality` type | `models/video.py:20` | SRV-001 |
| Source -- extractor sets `"{height}p"` | `extractor.py:180` | SRV-001 |
| Source -- `str(stream.quality)` at call site | `cli.py:217` | SRV-001 |
| Source -- `_parse_quality_to_enum` call sites | `downloader.py:544` + `690` (grep) | SRV-001 |
| Source -- misleading `except ValueError` handler | `cli.py:476-481` | SRV-001 |
| Source -- test grep for `_parse_quality_to_enum` | `tests/` -> 0 matches | SRV-001 |
| Source -- test grep for `_resolve_cookies` | `tests/` -> 5 matches (all bare, not p-suffix) | SRV-001 |
| Source -- parallel path passes `None` | `segment_downloader.py:170` | SRV-002 |
| Source -- sequential path calls `_parse_retry_after` | `downloader_throttle.py:194-195` | SRV-002 |
| Source -- `_parse_retry_after` not imported in segment_downloader | `segment_downloader.py:21-26` | SRV-002 |
| Source -- default `max_concurrent_downloads=4` | `config.py:80` | SRV-002 |
| Source -- `_do_parallel_download_attempt` def + call | `segment_downloader.py:190` (def), `236` (call) | SRV-003 |
| Source -- `except Exception` in `download_hls_with_resume` | `segment_downloader.py:829-831` | SRV-004 |
| Source -- `_await_and_cancel` catches `CancelledError` | `segment_downloader.py:506` | SRV-004 |
| Source -- CancelledError raises in `_download_segment_concurrent` | `segment_downloader.py:614`, `647` | SRV-004 |
| Source -- `_cleanup_segments` only on success path | `segment_downloader.py:558` | SRV-004/005 |
| Source -- test grep for preservation / cancellation log | `tests/` -> 0 matches | SRV-004/005 |
---

## Findings

### SRV-001: `_parse_quality_to_enum` raises ValueError for all p-suffixed quality strings, breaking browser cookie source

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION *(reclassified from RUNTIME-ERROR -- see note)* |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** `RUNTIME-ERROR` is outside the validator taxonomy (`SPEC-DEVIATION` / `BEST-PRACTICE` / `DOC-UPDATE`). The implementation fails the functional requirement to support `--cookie-source browser` for every quality request. Code must change; documentation is already correct. Reclassified as `SPEC-DEVIATION`, consistent with Phase 01 CLI-003 (same reclassification).
> - **Evidence correction:** The finding claim that "grep in `tests/` returns zero matches" for `_resolve_cookies` is **inaccurate** -- `TestResolveCookies` (test_hls_downloader.py:1826-1944, 5 tests) does exercise `_resolve_cookies`. However, none pass a p-suffixed quality string -- they use `"best"` and `"720"` (bare). `_parse_quality_to_enum` itself has **zero** test coverage. The underlying lack-of-coverage for the p-suffix path is real; the blanket "zero matches for `_resolve_cookies`" assertion is not.
> - **Additional call site (not cited in finding):** `_parse_quality_to_enum` is also called at `downloader.py:544` (`_attempt_segment_resume`), not only at `downloader.py:690` (`_resolve_cookies`). Both receive the same p-suffixed `quality` and would crash. The recommended fix to the function itself covers both call sites.
> - **See also:** cli.py:476-481 (`except ValueError` handler printing the misleading "Invalid URL format" message); Phase 01 CLI-003.

**Description:** `_parse_quality_to_enum` (downloader.py:104-126) is called by `_resolve_cookies` (downloader.py:690) whenever `cookie_source == CookieSource.BROWSER`, and by `_attempt_segment_resume` (downloader.py:544) on the yt-dlp-to-segment resume fallback. The `quality` argument originates from `str(stream.quality)` in cli.py (cli.py:217). `Stream.quality` is typed `str` (video.py:20), and the yt-dlp extractor sets it to `f"{height}p"` format (extractor.py:180). The fallback path tries `QualityEnum(f"Q{normalized}")` (downloader.py:124), but `QualityEnum` is a `StrEnum` (enums.py:6-17) whose values are bare digits (`"240"`, `"720"`, etc.), not `"Q720"`. So `QualityEnum("Q720")` raises `ValueError`, making the fallback a no-op. Every `"Xp"` string raises `ValueError` -- only `"best"`, `"worst"`, and bare `"720"` succeed. Since yt-dlp extraction produces `"Xp"` exclusively (never bare `"best"`/`"worst"`), the browser-cookie path is completely broken for every quality request -- including `--quality best`, because `str(stream.quality)` reflects the selected stream label (e.g. `"1080p"`), not the requested enum name.

**Evidence:** Runtime verification -- all p-suffixed inputs raise `ValueError`; bare and named qualities succeed:

```
'720p'   -> ValueError: Invalid quality value: 720p
'1080p'  -> ValueError
'480p'   -> ValueError
'360p'   -> ValueError
'240p'   -> ValueError
'1440p'  -> ValueError
'unknown' -> ValueError
'best'   -> OK: best
'worst'  -> OK: worst
'720'    -> OK: 720
QualityEnum.Q720.value = '720'
QualityEnum('Q720') -> ValueError  (confirms the Q-prefix fallback is broken)
```

Static -- data flow:

```python
# extractor.py:180
quality=f"{height}p" if height else "unknown"

# cli.py:217
str(stream.quality)   # "720p" -- never "best"

# downloader.py:690  (cookie_source == BROWSER)
quality_enum = _parse_quality_to_enum(quality)   # crashes on "720p"

# downloader.py:117-124  (broken fallback)
try:
    return QualityEnum(quality)               # fails for "720p"
except ValueError:
    normalized = quality.rstrip("p")            # "720p" -> "720"
    return QualityEnum(f"Q{normalized}")       # QualityEnum("Q720") -> ValueError!

# cli.py:476-481  (misleading handler catches the quality ValueError as URL error)
except ValueError:
    typer.echo("Invalid URL format. ...", err=True)
```

Static -- test coverage: `_parse_quality_to_enum` has 0 references in `tests/`. `_resolve_cookies` has 5 tests (`TestResolveCookies`, test_hls_downloader.py:1826-1944) but all pass bare or named quality strings (`"best"`, `"720"`), never `"720p"`, so none reproduce the bug.

**Recommendation:** Fix the fallback in `_parse_quality_to_enum` to look up the bare stripped value: `QualityEnum(normalized)` instead of `QualityEnum(f"Q{normalized}")`. Preferably, pass the `QualityEnum` directly from the composition root instead of round-tripping through `str(stream.quality)`, eliminating the parse step entirely (also addresses the shared root cause with Phase 01 CLI-002). Add test coverage for the p-suffix path. Effort: trivial. Priority: mandatory.

**Validation decision: VALIDATED (reclassified RUNTIME-ERROR to SPEC-DEVIATION).** Runtime confirmation: all p-suffixed quality strings raise `ValueError`; `QualityEnum("Q720")` is provably broken (StrEnum values are bare digits `"240"`...`"2160"`, `"best"`, `"worst"`). Data flow confirmed end-to-end (`Stream.quality: str` to `f"{height}p"` to `str(stream.quality)` to `_resolve_cookies` to `_parse_quality_to_enum`). The misleading "Invalid URL format" message at cli.py:476-481 is confirmed and catches quality-parsing ValueErrors as URL errors. The finding stands with reclassification to align with the validator taxonomy (code must change; docs are correct).

### SRV-002: Parallel download path ignores Retry-After header

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** When `max_concurrent_downloads > 1` (default is 4), segment downloads use the parallel path (`_run_parallel_download_with_backoff`, segment_downloader.py:143-174). This function calls `_compute_backoff_delay` with `None` for `retry_after_seconds` (segment_downloader.py:170), ignoring the `Retry-After` response header. In contrast, the sequential path (`_retry_429_with_backoff`, downloader_throttle.py:194-195) properly calls `_parse_retry_after(response)` and passes the result. The `Retry-After` header is a server directive; ignoring it in the default (parallel) download path means the client may retry too early, triggering cascading 429s from the CDN.

**Evidence:**
- segment_downloader.py:170: `delay = _compute_backoff_delay(response.status, attempt, None)` -- hardcodes `None`, ignoring `Retry-After` even though the `response` object is in scope.
- downloader_throttle.py:194-195: sequential path correctly does `retry_after_seconds = _parse_retry_after(response)` then `delay = _compute_backoff_delay(response.status, attempt, retry_after_seconds)`.
- `_parse_retry_after` is imported in `downloader_throttle.py` but is **not** imported into `segment_downloader.py` (imports at segment_downloader.py:21-26 are: `RETRYABLE_STATUS_CODES`, `_compute_backoff_delay`, `_retry_429_with_backoff`, `get_shutdown_event`).
- `_parse_retry_after` is tested in test_downloader_throttle.py (`TestParseRetryAfter`, 4 tests) for the sequential path.
- `_run_parallel_download_with_backoff` has zero direct test coverage. Indirect coverage exists via `_download_segment_parallel` tests (test_hls_downloader.py:1520-1619), but none exercise a 429 with a `Retry-After` header -- the 503 retry test (line 1550) mocks `response.headers.get` to return `None`.
- Default `Settings.max_concurrent_downloads` is 4 (config.py:80), confirming the parallel path is the default.

**Recommendation:** Import `_parse_retry_after` into segment_downloader.py and pass the parsed header value to `_compute_backoff_delay` in `_run_parallel_download_with_backoff`, mirroring the sequential path. Add test coverage for the 429 + Retry-After case in the parallel path. Effort: small. Priority: recommended.

**Validation decision: VALIDATED (no change).** Source inspection confirms the parallel path at segment_downloader.py:170 passes `None` for `retry_after_seconds`, while the sequential path at downloader_throttle.py:194-195 properly calls `_parse_retry_after(response)`. The `response` object is in scope in the parallel path but the header is never parsed. `_parse_retry_after` is not imported into segment_downloader.py. The inconsistency between the two retry implementations for the same `Retry-After` directive is a genuine spec deviation. No test exercises a 429 + Retry-After scenario in the parallel path. The finding stands unchanged as `SPEC-DEVIATION`.

---

### SRV-003: _do_parallel_download_attempt is a no-op wrapper with zero added logic

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_do_parallel_download_attempt` (segment_downloader.py:190-216) is a pure pass-through wrapper around `_run_parallel_download_with_backoff`. Its entire body is a single call that forwards all nine arguments and returns the result with no transformation, no logging, no exception handling, and no validation. It is called only once, from `_try_single_download_attempt` (segment_downloader.py:236), which already adds real value by catching `aiohttp.ClientError`.

**Evidence:**
- segment_downloader.py:190-216: body is `result = await _run_parallel_download_with_backoff(...)` then `return result`.
- grep confirms defined at line 190, called only at line 236. No other references in `src/` or `tests/`.

**Recommendation:** Inline the call in `_try_single_download_attempt`, removing the intermediate function. Effort: trivial. Priority: recommended.

**Validation decision: VALIDATED (no change).** Source inspection confirms `_do_parallel_download_attempt` (lines 190-216) forwards all arguments to `_run_parallel_download_with_backoff` and returns the result with no added logic -- no logging, no exception handling, no validation. Grep confirms it is defined once (line 190) and called once (line 236). Removing this indirection layer reduces cognitive load in an already deep call chain at trivial risk, introducing no new abstraction. Per the validator rules, removing unnecessary indirection is high-ROI at this project scale. The finding stands unchanged as `BEST-PRACTICE`.

### SRV-004: ~~`download_hls_with_resume` skips segment-preservation log on CancelledError during shutdown~~ [REJECTED]

> **Rejection reason:** The finding stated mechanism is incorrect. The finding claims that `asyncio.CancelledError` from the shutdown-signal path "propagates" to `download_hls_with_resume`'s `except Exception` handler. Runtime verification disproves this: when `shutdown_event.is_set()`, `_download_segment_concurrent` raises `asyncio.CancelledError("Download cancelled by user")` inside child `asyncio.Task` objects (segment_downloader.py:614, 647). Those tasks are awaited via `asyncio.gather` inside `_await_and_cancel` (segment_downloader.py:504-514), which has `except asyncio.CancelledError` (line 506) that catches the error, cancels remaining tasks, logs `"download_cancelled"` (line 513), and returns `None`. The `CancelledError` therefore never reaches `download_hls_with_resume`'s `except Exception` block -- `_run_download_session` returns `None` via the normal return path, and `download_hls_with_resume` returns `None` without entering the except handler. Confirmed by runtime simulation (shutdown event set): `_log_preserve_segments` is NOT called; the function returns `None`; the only log emitted is `"download_cancelled"` from `_await_and_cancel`. Consequently, the recommendation (change `except Exception` to `except BaseException` in `download_hls_with_resume`) would **not** fix the described shutdown-signal scenario -- that code path is never reached. The actual gap (preservation logged nowhere on shutdown) stems from `_await_and_cancel` catching `CancelledError` without calling `_log_preserve_segments`, not from the `except Exception` clause. **Note:** external task cancellation (a distinct scenario, verified separately) DOES propagate `CancelledError` past `except Exception`. That narrower concern is captured in the new finding SRV-005 below.

---

### SRV-005 (NEW): Shutdown-signal path preserves segments without any preservation log

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

> **Origin Note:**
> - **Action:** detected during validation of SRV-004
> - **Detail:** SRV-004 correctly identified that segment preservation is not logged on cancellation, but misdiagnosed the location. The CancelledError from the shutdown-signal path is caught by `_await_and_cancel` (not propagated to `download_hls_with_resume`'s `except Exception`). The real gap is that `_await_and_cancel` catches `CancelledError` at line 506, cancels remaining tasks, and returns `None` -- without calling `_log_preserve_segments`. Segments are preserved on disk (cleanup only on the success path in `_tally_and_merge`, line 558) but no `preserving_segments_for_resume` log is emitted.
> - **See also:** SRV-004 (rejected -- same symptom, wrong mechanism/location); `_log_preserve_segments` (segment_downloader.py:834-843); `_tally_and_merge` cleanup only on success (line 558); `_await_and_cancel` CancelledError handler (line 506).

**Description:** When the shutdown signal triggers `asyncio.CancelledError` inside segment download tasks, `_await_and_cancel` (segment_downloader.py:504-514) catches the error and returns `None` without logging that segments were preserved for resume. The segments themselves remain on disk (segment cleanup only runs on the success path in `_tally_and_merge`, line 558), so resume state IS preserved -- but there is no log message to make this visible to the user or operator.

**Evidence:**
- Runtime verification (shutdown event set, mocked deps): `_log_preserve_segments` is NOT called; `download_hls_with_resume` returns `None`; the only log emitted is `"download_cancelled"` (segment_downloader.py:513); no `"preserving_segments_for_resume"` log.
- `_await_and_cancel` (segment_downloader.py:506-514): `except asyncio.CancelledError` handler cancels tasks and returns `None` -- no `_log_preserve_segments` call.
- `_log_preserve_segments` (segment_downloader.py:834-843) is only called from the `except Exception` block in `download_hls_with_resume` (line 830), which is not reached in the shutdown-signal path (CancelledError is caught earlier by `_await_and_cancel`).
- `_tally_and_merge` calls `_cleanup_segments` (line 558) only inside `if downloaded_count == len(segments):` (line 554) -- the success path; on cancellation, segments remain.
- No test covers the cancellation-with-preservation-logging path (grep for `preserving_segments_for_resume` in `tests/` returns 0 matches).

**Recommendation:** Ensure `_log_preserve_segments` is called on the cancellation exit path. The most robust approach is a `finally` block in `download_hls_with_resume` (segment_downloader.py:816-831) with a `success` flag that calls `_log_preserve_segments(segments_dir)` when the download did not complete successfully -- this covers `Exception`, internal `CancelledError` (caught by `_await_and_cancel`), and external cancellation uniformly and has direct access to `segments_dir`. Effort: small. Priority: recommended (advisory).

**Validation decision:** Detected during validation (Step 4 -- rollout safety assessment; add detected issues). The symptom overlaps with SRV-004 but the root cause is correctly identified here. Recommended for follow-up.

---

## Cross-Finding Analysis

**Scope:** Phase 03 findings cross-referenced against Phase 01 (CLI), Phase 02 (Config), and other Phase 03 findings for overlapping root causes, conflicting evidence, and dependency chains.

**Same root cause (merge candidates):**
- **SRV-001 and Phase 01 CLI-002** share the root cause of `str(stream.quality)` round-tripping through the cli.py to `perform_download` call chain (cli.py:217; downloader.py:544, 690). CLI-002 classifies this as a structural/separation-of-concerns issue; SRV-001 classifies it as a functional crash. They are distinct findings at different layers (structure vs. behavior). The long-term fix recommended in both -- pass `QualityEnum` directly instead of `str(stream.quality)` -- addresses the shared root cause. **Not merged** (different classifications, different concerns).
- **SRV-001 and Phase 02 CFG-005** both concern `cookie_source` settings. CFG-005 is about `CookieSource.FILE` being listed in `.env` but rejected at construction; SRV-001 is about `CookieSource.BROWSER` being functionally broken due to quality-string parsing. **Not merged** -- distinct root causes.
- **SRV-002 and SRV-003** both touch `_run_parallel_download_with_backoff` in segment_downloader.py. SRV-002 fixes the Retry-After call (line 170); SRV-003 removes the no-op wrapper (lines 190-216) that calls it. **Not merged** -- distinct issues, but related to the same file/region.

**Conflicting evidence (cross-phase):** None. No other phase asserts that the browser-cookie path works correctly, that `Retry-After` is respected in the parallel path, or that cancellation logging is complete. All findings are mutually consistent.

**Dependency chains:**
- **SRV-001 to Phase 01 CLI-003:** SRV-001's bug triggers the misleading "Invalid URL format" message at cli.py:476-481. Fixing SRV-001 eliminates the spurious quality-parsing `ValueError` that leaks to that handler; the `except ValueError` clause should remain for genuine URL errors (`parse_video_id` at extractor.py:56).
- **SRV-002 depends on SRV-003 (ordering preference):** SRV-003 inlines `_do_parallel_download_attempt` into `_try_single_download_attempt`, which calls `_run_parallel_download_with_backoff`. SRV-002 modifies `_run_parallel_download_with_backoff`'s body (line 170). Applying SRV-003 first reduces diff churn but is not a hard dependency. No circular dependency.
- **SRV-004 (rejected) to SRV-005:** SRV-005 is the correctly-localized remediation for SRV-004's symptom. Implement SRV-005 instead of SRV-004's recommendation.

---

## Rollout Analysis

**Independence / ordering:**
- **SRV-001 (mandatory):** trivial fix to `_parse_quality_to_enum` (1-line change at downloader.py:124). Highest priority -- completely breaks `--cookie-source browser`. Independent of all other findings. Backward-compatible: `QualityEnum("720")` already works; the fix only newly enables p-suffixed inputs (`"720p"` to `"720"`). No behavioral change for `"best"`, `"worst"`, or bare numeric inputs.
- **SRV-003 (recommended, trivial):** inline `_do_parallel_download_attempt` into `_try_single_download_attempt`. Behavior-preserving. Should precede SRV-002 for minimal diff overlap in segment_downloader.py, but not a hard dependency.
- **SRV-002 (recommended, small):** import `_parse_retry_after`, call it at segment_downloader.py:170, pass the result to `_compute_backoff_delay`. Backward-compatible: when `Retry-After` header is absent, `_parse_retry_after` returns `None`, identical to current behavior.
- **SRV-005 (advisory, small):** add preservation logging on the cancellation exit path via a `finally` block. Low risk. Independent.
- **SRV-004:** do NOT implement (rejected -- wrong mechanism, ineffective recommendation).

**Circular / hidden dependencies:** None. SRV-001 touches `downloader.py`; SRV-002/003/005 touch `segment_downloader.py`; SRV-005 may touch `downloader.py` if the `finally` approach is used in `download_hls_with_resume`. No cross-module coupling is introduced.

**Backward compatibility:**
- SRV-001: no change for existing valid inputs; only newly accepts p-suffixed strings.
- SRV-002: only adds Retry-After respect; absent header changes nothing.
- SRV-003: behavior-preserving inlining.
- SRV-005: only adds a log message; no behavioral change.

**Rollout sequencing recommendation:** SRV-001 (mandatory) to SRV-003 (trivial, same file) to SRV-002 (small) to SRV-005 (advisory). SRV-003 before SRV-002 is preferred (reduces diff overlap) but not required.

---

## Execution Validation

All change targets were confirmed to still exist in the current source:

| Finding | Target | Line(s) | Exists? | Stale? |
|---------|--------|---------|---------|--------|
| SRV-001 | `_parse_quality_to_enum` definition | downloader.py:104-126 | yes | no |
| SRV-001 | broken fallback `QualityEnum(f"Q{normalized}")` | downloader.py:124 | yes | no |
| SRV-001 | call in `_resolve_cookies` | downloader.py:690 | yes | no |
| SRV-001 | call in `_attempt_segment_resume` | downloader.py:544 | yes | no |
| SRV-001 | `str(stream.quality)` to `perform_download` | cli.py:217 | yes | no |
| SRV-001 | misleading `except ValueError` handler | cli.py:476-481 | yes | no |
| SRV-001 | extractor sets `quality=f"{height}p"` | extractor.py:180 | yes | no |
| SRV-001 | `QualityEnum` StrEnum values (bare digits) | enums.py:6-17 | yes | no |
| SRV-002 | parallel path passes `None` | segment_downloader.py:170 | yes | no |
| SRV-002 | sequential path calls `_parse_retry_after` | downloader_throttle.py:194-195 | yes | no |
| SRV-002 | `_parse_retry_after` not imported in segment_downloader | segment_downloader.py:21-26 | yes | no |
| SRV-002 | default `max_concurrent_downloads=4` | config.py:80 | yes | no |
| SRV-003 | `_do_parallel_download_attempt` (no-op wrapper) | segment_downloader.py:190-216 | yes | no |
| SRV-003 | single call site | segment_downloader.py:236 | yes | no |
| SRV-004 | `except Exception` in `download_hls_with_resume` | segment_downloader.py:829-831 | yes | no |
| SRV-004 | `_await_and_cancel` catches `CancelledError` | segment_downloader.py:506 | yes | no |
| SRV-005 | `_log_preserve_segments` definition | segment_downloader.py:834-843 | yes | no |
| SRV-005 | `_cleanup_segments` only on success path | segment_downloader.py:558 | yes | no |

**Applicability and readiness:** All targets are present in the current source tree and the codebase is in the described state. No finding is rejected on staleness or applicability grounds. SRV-004 is rejected on mechanism-correctness grounds (the described `CancelledError` propagation does not occur -- it is caught by `_await_and_cancel`). The recommended replacement (SRV-005) targets the correct location.

---

## Warnings

- **SRV-001 -- evidence discrepancy (partial):** The finding claim that "grep in `tests/` returns zero matches" for `_resolve_cookies` is incorrect. `TestResolveCookies` (test_hls_downloader.py:1826-1944) has 5 tests that call `_resolve_cookies`. However, none pass a p-suffixed quality string -- they use `"best"` and `"720"` (bare). `_parse_quality_to_enum` itself has zero test coverage. The lack-of-coverage for the p-suffix path is real; the blanket "zero matches for `_resolve_cookies`" assertion is not.
- **SRV-001 -- expensive browser extraction before crash:** The `ValueError` is raised at downloader.py:690 inside `_resolve_cookies`, which runs after `extractor.extract_streams_with_cookies(url)` (line 688) -- which launches Playwright and navigates the page. Users on `--cookie-source browser` wait for a full browser session to complete before hitting the crash. Fixing `_parse_quality_to_enum` eliminates this wasted work.
- **SRV-004 -- mechanism misdiagnosis:** The finding confuses two cancellation scenarios. The shutdown-signal path (CancelledError from `_download_segment_concurrent`) is caught by `_await_and_cancel` and does NOT reach `download_hls_with_resume`'s `except Exception`. Only external task cancellation (a separate scenario) propagates `CancelledError` past that handler. Do not implement SRV-004 as written.
- **SRV-004/SRV-005 -- no cancellation-exit test coverage:** No test in `tests/` covers the `download_hls_with_resume` cancellation or external-cancellation path with preservation-logging verification. A regression test should accompany the SRV-005 fix.
- **SRV-002 -- `_parse_retry_after` scope:** The function handles integer-seconds and HTTP-date formats (downloader_throttle.py:226-257) but returns `None` for unparseable values. Importing it into the parallel path introduces no new edge cases beyond what the sequential path already handles and tests.

---

## Required Fixes

1. **SRV-001** *(mandatory)*: Fix `_parse_quality_to_enum` fallback in `downloader.py:124` -- change `QualityEnum(f"Q{normalized}")` to `QualityEnum(normalized)`. This makes `"720p"` to `quality.rstrip("p")` to `"720"` to `QualityEnum("720")` to `Q720`, which already works via the primary lookup at line 118. Add a unit test: `_parse_quality_to_enum("720p") == QualityEnum.Q720`. Optionally, refactor cli.py to pass `QualityEnum` directly to `perform_download` instead of `str(stream.quality)` (addresses shared root cause with Phase 01 CLI-002 and eliminates both call sites at downloader.py:544 and 690).

---

## Advisory Recommendations

1. **SRV-002** *(small)*: Import `_parse_retry_after` into `segment_downloader.py` and pass `retry_after_seconds = _parse_retry_after(response)` to `_compute_backoff_delay` at segment_downloader.py:170, mirroring the sequential path (downloader_throttle.py:194-195). Add a 429 + Retry-After test for `_run_parallel_download_with_backoff` (or `_download_segment_parallel`).
2. **SRV-003** *(trivial)*: Inline `_do_parallel_download_attempt` into `_try_single_download_attempt` (remove lines 190-216, call `_run_parallel_download_with_backoff` directly at line 236). Behavior-preserving.
3. **SRV-005** *(small)*: Add a `finally` block in `download_hls_with_resume` (segment_downloader.py:816-831) with a `success` flag that calls `_log_preserve_segments(segments_dir)` when the download did not complete successfully. Covers `Exception`, internal `CancelledError` (via `_await_and_cancel`), and external cancellation uniformly. Add a regression test that sets the shutdown event and asserts `preserving_segments_for_resume` is logged.
4. **SRV-001 follow-up** *(small)*: Refine the `except ValueError` handler at cli.py:378 to distinguish quality-parsing errors from URL-format errors. **Chosen approach**: Create a dedicated `QualityParseError` exception (subclass of `ValueError`) in `exceptions.py`, raise it from `_parse_quality_to_enum` (replacing the generic `ValueError`), and add a separate `except QualityParseError` handler in `download()` (cli.py:378) placed **before** the generic `except ValueError` clause. The `QualityParseError` handler should emit "Invalid quality value: {quality}. Use one of: {available_qualities}." This follows the project's existing exception hierarchy pattern (`VKDownloadError` → `QualityNotAvailableError`, etc.) and avoids message-string inspection. The generic `ValueError` handler remains for genuine URL-format errors from `extractor.parse_video_id` (extractor.py:55). Effort: small. Priority: recommended.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | SRV-002, SRV-003 |
| Reclassified | 1 | SRV-001 (RUNTIME-ERROR to SPEC-DEVIATION) |
| Merged | 0 | -- |
| Rejected | 1 | SRV-004 |
| Added (new, from validation) | 1 | SRV-005 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| SRV-004 | `download_hls_with_resume` skips segment-preservation log on CancelledError during shutdown | Mechanism incorrect: the shutdown-signal-path `CancelledError` (raised in `_download_segment_concurrent`, lines 614/647) is caught by `_await_and_cancel` (line 506), which returns `None` -- it never reaches `download_hls_with_resume`'s `except Exception` handler. Runtime verification confirms `_await_and_cancel` swallows the `CancelledError` and returns `None`; `_log_preserve_segments` is not called because the except block is never entered. The recommendation (change `except Exception` to `except BaseException`) would not fix the described scenario. The real gap is correctly identified in new finding SRV-005 (location: `_await_and_cancel`, not `download_hls_with_resume`). |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| (none) | -- | -- |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SRV-001 | RUNTIME-ERROR | SPEC-DEVIATION | `RUNTIME-ERROR` is outside the validator taxonomy. Reproduced at runtime: all p-suffixed quality strings raise `ValueError`; `QualityEnum("Q720")` fallback is broken (StrEnum values are bare digits). The implementation fails the functional requirement to support `--cookie-source browser`. Code must change; documentation is already correct. |
