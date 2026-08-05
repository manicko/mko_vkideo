# Phase 07 — Test Quality: Validated Findings

**Validated by:** validator
**Source:** `.ai/audit/07-audit-tests/findings.md`
**Method:** Each finding cross-checked against `src/`, `tests/`, and a live suite run.

## Runtime Verification

- **R1 — Full suite:** `uv run pytest tests/` → **248 passed**, 0 failed (~9.88s). Stable/deterministic; matches auditor's 4-run range (9.60–10.05s). ✅ validated
- **R2 — Failures:** None. ✅ validated
- **R3 — Tautologies:** Confirmed in TST-001, TST-003, TST-005. ✅ validated
- **Coverage tool:** `pytest-cov` absent from `pyproject.toml`. ✅ validated → TST-006 gaps found by static read.
- **Determinism caveat:** `pytest-randomly` not installed; only repeated sequential runs used. ✅ matches audit.

---

## Findings

### TST-001: `TestYtdlpOptions` tests never invoke `_build_ytdlp_options` — they assert hand-written dict literals (tautological)

> **Validation Verdict:** ✅ APPROVED (BEST-PRACTICE, HIGH, mandatory)
>
> - **Code check:** Production `_build_ytdlp_options` exists (`downloader.py:129`); it assembles the real opts dict with `nocheckcertificate: not settings.ssl_verify` (line 171), `throttledratelimit`, `http_chunk_size`, `http_headers`, `cookiefile` (line 184).
> - **Applicability:** `tests/test_hls_downloader.py:403-437` construct `ydl_opts = {...}` inline from `Settings` and assert `ydl_opts["throttledratelimit"] == 10000` — i.e. `10000 == 10000`. Grep confirms `_build_ytdlp_options` is imported (line 18) but referenced in tests only at lines 1957/1984/2007 (inside `TestYtDlpShutdownHook`); `TestYtdlpOptions` never calls it.
> - **Impact:** A regression in any yt-dlp key name or the `nocheckcertificate` mapping escapes these tests.
> - **Recommendation** is sound and aligns with the production signature. No change to recommendation.

### TST-002: Intended test `test_download_segment_main_sequential_dispatch` is missing — its body was appended to the preceding test

> **Validation Verdict:** ✅ APPROVED (SPEC-DEVIATION, HIGH, mandatory)
>
> - **Code check:** `_download_segment` (`segment_downloader.py:306`) dispatches to `_download_segment_sequential` when `max_concurrent_downloads == 1` (line 335). The sequential branch is the exact behavior the dropped test targets.
> - **Applicability:** `grep "def test_download_segment_main_sequential_dispatch"` → no match. Lines 1619-1620 end `test_download_segment_parallel_fails_fast_on_non_retryable`; line 1620 is an orphaned bare-string docstring; lines 1621-1647 contain the intended body (calls `_download_segment(..., max_concurrent_downloads=1, ...)` asserting `result is True` + written segment). Pytest collects the two surrounding tests with nothing between — the body is dead-attached.
> - **Impact:** Sequential-dispatch path lacks a named, collectible test.
> - **Recommendation** (restore `async def`, drop orphan docstring) is correct and trivial.

### TST-003: `test_parallel_download_uses_gather` mocks `asyncio.gather` so download tasks never execute (tests the mock, not the logic)

> **Validation Verdict:** ✅ APPROVED (BEST-PRACTICE, MEDIUM, advisory)
>
> - **Code check:** `_download_segment_concurrent` (`segment_downloader.py:598`) does `result = await _download_segment(...)` (line 627); `_create_segment_download_tasks` (`segment_downloader.py:654`) schedules via `asyncio.create_task`.
> - **Applicability:** Test (lines 494-535) patches `_download_segment` with `return_value=True` (plain bool) and `asyncio.gather` with a mock returning `[True] * len(tasks)` without awaiting; asserts only `gather_called` (line 535). Real path would hit `await True` → `TypeError`; tasks run only incidentally and may emit "Task was destroyed but it is pending".
> - **Note:** the sibling `test_shared_semaphore_parameter` (line 538) already uses a proper `async def side_effect` mock — so the recommended AsyncMock-based fix is consistent with existing project pattern.
> - **Recommendation** is actionable; no overengineering.

### TST-004: `_download_with_ytdlp` tests patch `asyncio.get_event_loop` but production calls `get_running_loop` (dead executor mock)

> **Validation Verdict:** ✅ APPROVED (SPEC-DEVIATION, LOW, advisory)
>
> - **Code check:** Production (`downloader.py:645`): `loop = asyncio.get_running_loop()`.
> - **Applicability:** Tests lines 615 and 1046 patch `vkdownloader.services.downloader.asyncio.get_event_loop`, so the installed `run_in_executor` mock (lines 627, 1054) is never reached by production; real loop is used. Tests pass only because `yt_dlp.YoutubeDL` is fully mocked.
> - **Note:** the correct pattern (`patch.object(asyncio, "get_running_loop")`) already exists at lines 1780 and 1811, confirming the recommended fix aligns with the codebase.
> - **Recommendation** (patch `get_running_loop`) is correct and small.

### TST-005: Four `@pytest.mark.asyncio` tests perform no `await` (misleading async marking)

> **Validation Verdict:** ✅ APPROVED (BEST-PRACTICE, LOW, advisory)
>
> - **Code check:** `_format_cookies_for_ffmpeg` (`extractor.py:251`) and `_cookies_to_netscape` (`cookies.py:13`) are synchronous.
> - **Applicability:** `test_extractor.py` lines 127, 172, 185, 204 are `async def` + `@pytest.mark.asyncio` with no `await` in body (verified by read of lines 128-212). They exercise synchronous methods.
> - **Recommendation** (drop async/await marking) is trivial and improves honesty.

### TST-006: Critical orchestration/config paths have no test coverage

> **Validation Verdict:** ✅ APPROVED (BEST-PRACTICE, MEDIUM, advisory)
>
> - **Code check:** All listed symbols confirmed in production: `_temp_headers_file` (`downloader.py:58`), `_await_first_and_cancel_others` (`downloader.py:79`), `_parse_quality_to_enum` (`downloader.py:104`), `_attempt_segment_resume` (`downloader.py:494`), `_create_connector` (`segment_downloader.py:470`), `_run_download_session` (`segment_downloader.py:690`).
> - **Applicability:** Grep of `tests/` shows no assertion-level references to any of these. `download_with_ytdlp_with_resume_fallback` appears only as a patch target (line 942, mocking it); `cleanup_signal_handlers` appears only as teardown reset (lines 1790, 1823), not as a behavior assertion.
> - **Priority** in recommendation is sensible: `_parse_quality_to_enum` (trivial, high value) → `_create_connector` SSL branches → one fallback scenario → `cleanup_signal_handlers` reset. All are high-value unit additions, not overengineered abstraction.

---

## Cross-Finding Analysis

- **No conflicting evidence** between Phase 07 and other phases. All phases report `pytest` → 248 passed (Phase 01: 9.64s, 03: 9.56s, 05: 9.54s, 08: 10.91s); none contradict Phase 07's tautology/structural findings.
- **No merges:** Each TST finding has a distinct root cause and distinct affected code.
- **Complementary coverage observation (not merged):** Phase 03 flags `_run_parallel_download_with_backoff` (`downloader_throttle.py`) as zero-coverage at the service layer; TST-006 flags orchestration gaps in `segment_downloader.py`/`downloader.py`. Different modules/functions → distinct root causes, no duplication.
- **Related pattern, different layer:** Phase 01 CLI-005 simplifies `as_completed`+`gather` double-await in *production* CLI progress code; TST-003 targets a *test* that mocks `gather`. No conflict.

## Rollout Analysis

- **TST-002** is the only structural defect (dropped definition). Fix is isolated: restore one `async def` line + delete one orphan string literal. No dependency on other fixes.
- **TST-004** fix (patch `get_running_loop`) is independent and low-risk; codebase already uses the target pattern, reducing risk of new behavior.
- **TST-001/TST-003/TST-005** are test-internal refactors with no production-code coupling → zero rollout risk to production behavior.
- **TST-006** coverage additions are purely additive; can be staged after TST-002/TST-004 since they share no edits in `test_hls_downloader.py`.
- **No circular dependencies, no hidden ordering constraints.**

## Execution Validation

- All targets verified to still exist at stated line numbers.
- Findings are not stale (validated against live checkout 2026-08-05; suite passes 248/248).
- No architectural drift detected; recommendations follow existing patterns (AsyncMock side_effect, `get_running_loop` patching).

## Warnings

- **TST-003 risk:** if the tasks *did* execute, `_download_segment` mocked as `return_value=True` would raise `TypeError`. Currently masked by the gather mock + short loop lifetime; do not leave the test as-is during unrelated refactors (latent failure).
- **TST-006 — `_temp_headers_file` / `_await_first_and_cancel_others`:** cleanup + cancellation paths are security/robustness-relevant (cookie-file cleanup, graceful shutdown); consider prioritizing their tests over pure orchestration.

## Required Fixes (mandatory)

- **TST-001:** Replace tautological `TestYtdlpOptions` inline-dict assertions with real calls to `_build_ytdlp_options(...)`, asserting returned `throttledratelimit`, `http_chunk_size`, `cookiefile`, `http_headers`, `nocheckcertificate`.
- **TST-002:** Restore `async def test_download_segment_main_sequential_dispatch(self, test_settings, tmp_path) -> None:`; remove orphaned docstring literal at `test_hls_downloader.py:1621`.

## Advisory Recommendations

- **TST-003:** Replace `return_value=True` mock with `AsyncMock`/`async side_effect`; stop mocking `asyncio.gather`; assert on outcome (`download_count`/segment output).
- **TST-004:** Patch `asyncio.get_running_loop` (pattern already used at lines 1780/1811).
- **TST-005:** Remove `async`/`@pytest.mark.asyncio` from the four synchronous extractor tests.
- **TST-006:** Add prioritized unit tests (quality parsing → SSL connector → yt-dlp fallback → signal cleanup).

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (approved, unchanged) | 6 | TST-001, TST-002, TST-003, TST-004, TST-005, TST-006 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Approved Findings

| ID | Severity | Type | Status |
|----|----------|------|--------|
| TST-001 | HIGH | BEST-PRACTICE | Approved — tautological tests confirmed |
| TST-002 | HIGH | SPEC-DEVIATION | Approved — dropped test def confirmed |
| TST-003 | MEDIUM | BEST-PRACTICE | Approved — gather mock confirmed |
| TST-004 | LOW | SPEC-DEVIATION | Approved — get_running_loop mismatch confirmed |
| TST-005 | LOW | BEST-PRACTICE | Approved — no-await async tests confirmed |
| TST-006 | MEDIUM | BEST-PRACTICE | Approved — coverage gaps confirmed |

### Rejected Findings

(none)

### Merged Findings

(none)

### Reclassified Findings

(none)