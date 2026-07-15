# Phase 07 Audit Findings — Test Quality (Validated)

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/07-audit-tests.md
**Status:** validated
**Validated by:** validator
**Date:** 2026-07-14

---

## Runtime Verification Summary (Step R1–R5)

| Check | Result |
|-------|--------|
| R1 — Full suite | `uv run pytest -q` → **201 passed, 4 warnings, 5.15s**. No failures (exit 0). |
| R2 — Failures | None. No production-bug-in-test found. |
| R3 — Tautological/no-op | **Confirmed** (see TST-004, TST-005, TST-006). |
| R4 — Isolation | Time-dependent tests use `time.sleep` with tight margins (see TST-008). |
| R5 — Coverage gaps | **Confirmed**: `adaptive_throttle.py`, `ffmpeg_utils._merge_*`, and the real bodies of `segment_downloader` functions are never executed (always mocked). |

---

## Findings

### TST-001: Core segment download & merge logic is never executed (only mocked)

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** The most bug-prone, business-critical paths of the downloader — actual HTTP segment retrieval, retry/backoff orchestration at the segment level, and the ffmpeg concat merge — are never run by the test suite. Every test in `test_hls_downloader.py` patches them out.

- `segment_downloader._download_segment` (line 42, ~52 LOC) — performs the real per-segment fetch + backoff — is replaced by a trivial `mock_download_segment` that just writes bytes and returns `True`.
- `segment_downloader._fetch_playlist_with_retry` (line 129) — replaced by `return_value="#EXTM3U\nseg1.ts..."` in all tests.
- `ffmpeg_utils._merge_segments_batched` (line 235) — replaced by `return_value=output_path` in all tests.

A defect in real segment fetching (wrong retry semantics, dropped segments, corrupted bytes) or in the merge (incorrect concat file list, wrong ffmpeg args, partial-output handling) would pass CI silently.

**Evidence:**
- `src/vkdownloader/services/segment_downloader.py` lines 42-97 contain real logic but no test imports the actual function body.
- `src/vkdownloader/services/ffmpeg_utils.py` lines 99-269 contain merge/process lifecycle code but no tests exercise `_build_ffmpeg_concat_command`, `_merge_batch_segments`, `_perform_final_merge`, or `cancel_ffmpeg_process`.
- Grep shows all references to `_merge_segments_batched` in tests are `patch(...)` calls returning mock values.

**Validation:** ✅ VALIDATED — Coverage gap confirmed. Tests mock these functions instead of exercising real implementations.

---

### TST-002: Adaptive throttling feature has zero test coverage

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/adaptive_throttle.py` |
| **Classification** | advisory |

**Description:** The project's defining capability — "adaptive throttling" — is implemented in `adaptive_throttle.py` (class `AdaptiveThrottle`, 66 LOC) and is never referenced by any test.

**Evidence:**
- `adaptive_throttle.py` = 66 LOC.
- `grep "adaptive_throttle" tests/` returns no matches.
- The class provides `wait()`, `on_rate_limited()`, `on_success()` methods for dynamic delay adjustment that are completely untested.

**Validation:** ✅ VALIDATED — Zero test coverage confirmed. The `AdaptiveThrottle` class is defined but never imported in any test file.

---

### TST-003: ffmpeg_utils merge/cancel utilities untested

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** `ffmpeg_utils.py` (269 LOC) contains the merge pipeline used by every successful download: `_build_ffmpeg_concat_command` (line 127), `_merge_batch_segments` (line 154), `_perform_final_merge` (line 197), `_merge_segments_batched` (line 235), `cancel_ffmpeg_process` (line 99). Only `read_progress`/`ProgressParser` are covered via tests; the merge command construction and process lifecycle are never executed.

**Evidence:**
- `grep "ffmpeg_utils" tests/` → no matches (only `segment_downloader._merge_segments_batched` is patched).
- Tests in `test_hls_downloader.py` patch `_merge_segments_batched` with `return_value=output_path` instead of testing real merge behavior.

**Validation:** ✅ VALIDATED — Merge/cancel functions are never tested. Only `ProgressParser` and `read_progress` (lines 32-97 in ffmpeg_utils.py) have test coverage.

---

### TST-004: Integration tests are tautological no-ops (exercise no production code)

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/integration/test_mock_vk_server.py` |
| **Classification** | advisory |

**Description:** The entire `tests/integration/` directory gives the false impression of end-to-end coverage, but none of its tests call any production code. They only build local fixtures (MagicMock / f-strings) and assert on values they defined themselves.

**Evidence:**
- `tests/integration/test_mock_vk_server.py` lines 9-63 create mock objects and assert on their own values.
- No import of `vkdownloader.*` anywhere in the file.
- `test_mock_video_page_response`: creates `mock_response` with `status=200` then asserts `mock_response.status == 200` — always true.
- `test_mock_m3u8_response`: asserts `"#EXTM3U" in m3u8_content` on a string literal it defined.

**Validation:** ✅ VALIDATED — Tests are tautological no-ops that verify nothing about production code.

---

### TST-005: No-op placeholder test for security-relevant path

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_security.py` (`test_path_inside_repo_warns`) |
| **Classification** | advisory |

**Description:** `test_path_inside_repo_warns` (lines 55-64) has a body of `pass` with only an explanatory comment. The behavior it names — warning when the output path is inside the repo root — is a security/operational guard (prevents clobbering the project tree) and remains completely unverified.

**Evidence:**
- `tests/test_security.py:55-64` — function body is empty `pass`.
- `src/vkdownloader/utils/security.py:49-58` — the warning code path exists and is functional.

**Validation:** ✅ VALIDATED — Placeholder test with `pass` body provides no verification of the warning behavior.

---

### TST-006: Source-text assertion instead of behavioral assertion

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_hls_downloader.py` (`test_structured_logging_fields`) |
| **Classification** | advisory |

**Description:** `test_structured_logging_fields` (lines 913-927) inspects the function's source code via `inspect.getsource` and asserts that strings `"attempt"`, `"status"`, `"retry_after"`, `"segment_index"`, `"url"` appear in it. This verifies presence of words in source, not that logging actually emits those fields at runtime.

**Evidence:**
- `tests/test_hls_downloader.py:913-927` — uses `inspect.getsource()` and string matching.
- Behavioral logging tests exist in `test_downloader_throttle.py:395-487` that capture real `logger.warning` calls.
- Source-inspection test is redundant and brittle — renaming a variable would keep it green even if structured fields are dropped.

**Validation:** ✅ VALIDATED — Redundant source-inspection test; behavioral tests in `test_downloader_throttle.py` provide actual coverage.

---

### TST-007: Unawaited-coroutine RuntimeWarnings mask real bugs and indicate weak async tests

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_cli.py::test_download_keyboard_interrupt`, `tests/test_downloader_throttle.py::test_wait_if_paused_returns_on_shutdown` |
| **Classification** | advisory |

**Description:** The suite emits 4 `RuntimeWarning: coroutine '...' was never awaited` during the run.

**Evidence:**
- `pytest -q` output shows 4 RuntimeWarnings.
- `test_cli.py:100` patches `asyncio.run` with `side_effect=KeyboardInterrupt()`, leaving an unawaited coroutine.
- `test_downloader_throttle.py:539-557` sets `mock_event.wait = AsyncMock()` but the shutdown path returns early without awaiting it.

**Validation:** ✅ VALIDATED — Unawaited coroutine warnings confirmed. Could mask genuine asyncio bugs.

---

### TST-008: Time-dependent tests with tight real-clock margins are flaky

| Field | Value |
|-------|-------|
| **ID** | TST-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_downloader_throttle.py` |
| **Classification** | advisory |

**Description:** Several `URLBackoffCoordinator` tests depend on real wall-clock timing with a thin safety margin:
- `test_is_paused_returns_false_after_backoff_expires` (lines 510-520): `pause(url, 0.01)` then `time.sleep(0.02)` — only ~10ms of slack.
- `test_pause_overwrites_existing_backoff` (lines 570-580): `pause(url, 1.0)` then `time.sleep(0.02)` then `pause(url, 10.0)`.

**Evidence:**
- `tests/test_downloader_throttle.py:510-520` — uses `time.sleep(0.02)` against 0.01s backoff.
- `tests/test_downloader_throttle.py:570-580` — uses `time.sleep(0.02)` against 1.0s backoff.

**Validation:** ✅ VALIDATED — Tests use real `time.sleep` with tight margins; could fail intermittently on slow CI runners.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 8 | TST-001, TST-002, TST-003, TST-004, TST-005, TST-006, TST-007, TST-008 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Cross-Phase Analysis

No cross-phase conflicts detected. Phase 07 findings are orthogonal to Phase 03 service-layer findings. TST-001/003 overlap with SRV-003 (parallel retry coverage) but address different concerns: SRV-003 identifies a production bug in retry logic, while TST-001/003 identify missing test coverage.

### Rollout Safety Analysis

All recommended fixes are test-only improvements with no rollout risks:
- TST-001/003: Adding real execution tests cannot break production code.
- TST-004: Deleting tautological tests or replacing with real integration tests improves signal-to-noise.
- TST-005: Implementing the placeholder test adds verification only.
- TST-006: Removing redundant source-inspection test simplifies the suite.
- TST-007: Fixing unawaited coroutines improves diagnostic quality.
- TST-008: Using fake clocks or wider margins reduces flakiness.

No hidden dependencies or unsafe execution sequences identified.

---

## Recommendations (Unchanged from Original)

- **TST-001** — Add real execution tests for `_download_segment`, `_fetch_playlist_with_retry`, `_merge_segments_batched` (highest-value coverage gap).
- **TST-002** — Add unit tests for `AdaptiveThrottle` (headline feature, currently 0% coverage).
- **TST-003** — Add tests for `ffmpeg_utils` merge/cancel command construction and process lifecycle.
- **TST-004** — Delete or replace the tautological `tests/integration/test_mock_vk_server.py` with a real round-trip integration test.
- **TST-005** — Implement the `pass`-only `test_path_inside_repo_warns` placeholder.
- **TST-006** — Remove source-inspection `test_structured_logging_fields` (redundant with behavioral logging tests).
- **TST-007** — Fix unawaited-coroutine leaks; consider `filterwarnings = error` for RuntimeWarning.
- **TST-008** — Remove real-clock `time.sleep` dependencies from backoff timing tests.