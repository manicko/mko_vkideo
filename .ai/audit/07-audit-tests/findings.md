# Phase 07 Audit Findings — Test Quality

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/07-audit-tests.md
**Status:** complete
**Validated:** no

## Runtime Verification Summary (Step R1–R5)

- **R1 — Full suite:** `uv run pytest -q` → **201 passed, 4 warnings, 4.74s**. No failures (exit 0).
- **R2 — Failures:** None. No production-bug-in-test found.
- **R3 — Tautological/no-op:** Found (see TST-004, TST-005, TST-006).
- **R4 — Isolation:** No order-dependent or non-deterministic failures observed on a single run; however two tests rely on real wall-clock `time.sleep` (see TST-008).
- **R5 — Coverage gaps:** Confirmed via grep — `adaptive_throttle.py`, `ffmpeg_utils.py`, and the real bodies of `segment_downloader` functions are never executed by tests (always mocked). Net: the headline "adaptive throttling" feature and the segment fetch/merge core path have zero execution coverage.

> Note: the phase template references components (PostProcessor, ImageCache, TelegramPoster, GSheetsReader) that do not exist in this project. Findings below are mapped to this project's actual architecture (`src/vkdownloader/...`).

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

- `segment_downloader._download_segment` (line 42, ~58 LOC) — performs the real per-segment fetch + backoff — is replaced by a trivial `mock_download_segment` that just writes bytes and returns `True` (e.g. `test_hls_downloader.py:521-531`, `:619-629`, `:761-770`, `:873-881`).
- `segment_downloader._fetch_playlist_with_retry` (line 129) — replaced by `return_value="#EXTM3U\nseg1.ts..."` (e.g. `test_hls_downloader.py:265`, `:534`, `:578`, `:632`, `:778`, `:833`, `:889`, `:988`).
- `ffmpeg_utils._merge_segments_batched` (line 235) — replaced by `return_value=output_path` (e.g. `test_hls_downloader.py:542`, `:586`, `:640`, `:786`, `:842`, `:897`, `:996`).

A defect in real segment fetching (wrong retry semantics, dropped segments, corrupted bytes) or in the merge (incorrect concat file list, wrong ffmpeg args, partial-output handling) would pass CI silently. The orchestration `download_hls_with_resume` is tested only for logging, cleanup, sequential/parallel delay, and semaphore plumbing — not for producing a correct output file.

**Evidence:** `grep` over `tests/` shows every reference to `_download_segment`, `_fetch_playlist_with_retry`, `_merge_segments_batched` is a `patch(...)`/`side_effect=`; no test imports or calls the real implementation. Real coverage: 0 of ~336 LOC of `segment_downloader.py` and 0 of `ffmpeg_utils._merge_*` (the `read_progress`/`ProgressParser` helpers are tested, but merge is not).

**Recommendation:** Add tests that exercise the real `_download_segment` against an `aiohttp` mock server (or a `unittest.mock` session whose `get` returns staged responses), the real `_fetch_playlist_with_retry` with simulated 429/5xx sequences, and `_merge_segments_batched` with a fake `ffmpeg` subprocess (or by asserting the generated concat list + command). This is the single highest-value coverage investment.

---

### TST-002: Adaptive throttling feature has zero test coverage

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/adaptive_throttle.py` |
| **Classification** | advisory |

**Description:** The project's defining capability — "adaptive throttling" — is implemented in `adaptive_throttle.py` (class `AdaptiveThrottle`, 66 LOC) and is never referenced by any test (`grep "adaptive_throttle" tests/` → no matches). Throttle calculation, network-condition-driven delay adjustment, and reset/escalation behavior are entirely unverified. A regression that breaks throttle computation (e.g., wrong delay, divide-by-zero on missing metrics, never-throttling) would ship undetected.

**Evidence:** `adaptive_throttle.py` = 66 LOC, single `AdaptiveThrottle` class; zero test files import it.

**Recommendation:** Add unit tests for `AdaptiveThrottle`: delay increases under throttled-rate conditions, decays toward baseline, clamps to configured min/max, and respects shutdown/cancel. Keep it pure (no real network) by injecting metrics.

---

### TST-003: ffmpeg_utils merge/cancel utilities untested

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** `ffmpeg_utils.py` (269 LOC) contains the merge pipeline used by every successful download: `_build_ffmpeg_concat_command` (line 127), `_merge_batch_segments` (line 154), `_perform_final_merge` (line 197), `_merge_segments_batched` (line 235), `cancel_ffmpeg_process` (line 99), plus `read_progress`/`ProgressParser` (only the latter pair is covered via `test_hls_downloader.py`). The merge command construction and process lifecycle are never executed; only the orchestrating `_merge_segments_batched` is mocked away. A malformed concat command or a broken final-merge fallback would pass CI.

**Evidence:** `grep "ffmpeg_utils" tests/` → no matches. Real coverage limited to `read_progress`/`ProgressParser` (re-exported into `downloader` and tested in `test_hls_downloader.py:1110-1335`).

**Recommendation:** Test `_build_ffmpeg_concat_command` output (file list ordering, escaping), `_merge_batch_segments`/`_perform_final_merge` against a stubbed `ffmpeg` subprocess (assert command + success/failure handling), and `cancel_ffmpeg_process` termination behavior.

---

### TST-004: Integration tests are tautological no-ops (exercise no production code)

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/integration/test_mock_vk_server.py` |
| **Classification** | advisory |

**Description:** The entire `tests/integration/` directory gives the false impression of end-to-end coverage, but none of its tests call any production code. They only build local fixtures (MagicMock / f-strings) and assert on values they defined themselves:

- `test_mock_video_page_response` (lines 9-28): creates `mock_response` with `status=200` then asserts `mock_response.status == 200`. Always true; no code under test.
- `test_mock_m3u8_response` (lines 30-47): asserts `"#EXTM3U" in m3u8_content` on a string literal it just defined.
- `test_mock_video_page_various_ids` (lines 49-63): asserts `vid in html_content` where `html_content` is `f"..."` built from `vid` in the same function.

These cannot fail and detect nothing. They are the most misleading tests in the suite because the directory name implies real network/extraction integration that does not exist.

**Evidence:** `tests/integration/test_mock_vk_server.py` lines 9-63 (full file). No import of `vkdownloader.*` anywhere in the file.

**Recommendation:** Either delete the file (it adds false coverage and pollutes `pytest` counts) or replace it with a genuine integration test that drives `VKVideoExtractor`/`download_hls_with_resume` against a local `aiohttp` mock server (request/response round-trip), so the extraction → playlist → segment flow is actually exercised.

---

### TST-005: No-op placeholder test for security-relevant path

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_security.py` (`test_path_inside_repo_warns`) |
| **Classification** | advisory |

**Description:** `test_path_inside_repo_warns` (lines 55-64) has a body of `pass` with only an explanatory comment ("Full integration test would require mocking Path.resolve() which is complex"). It always passes and verifies nothing. The behavior it names — warning when the output path is inside the repo root — is a security/operational guard (prevents clobbering the project tree) and remains completely unverified, while contributing to the passing test count.

**Evidence:** `tests/test_security.py:55-64` — function body is `pass`.

**Recommendation:** Implement the test by monkeypatching `Path.resolve`/`repo root` so the "inside repo" branch is reached and `logger.warning` is asserted. If the branch is too hard to reach, remove the placeholder and track a real TODO rather than shipping a `pass` test.

---

### TST-006: Source-text assertion instead of behavioral assertion

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_hls_downloader.py` (`test_structured_logging_fields`) |
| **Classification** | advisory |

**Description:** `test_structured_logging_fields` (lines 913-927) inspects the function's *source code* via `inspect.getsource` and asserts that strings `"attempt"`, `"status"`, `"retry_after"`, `"segment_index"`, `"url"` appear in it. This verifies presence of words in source, not that logging actually emits those fields at runtime. A real behavioral test already exists (`test_downloader_throttle.py::test_structured_logging_on_retry` and `::test_structured_logging_on_non_retryable`) which captures `logger.warning` and asserts the actual kwargs. The source-inspection test is redundant and brittle: renaming a variable or restructuring the log call keeps it green even if the structured fields are dropped.

**Evidence:** `tests/test_hls_downloader.py:913-927`; duplicate of runtime coverage in `tests/test_downloader_throttle.py:395-487`.

**Recommendation:** Remove `test_structured_logging_fields`; rely on the existing behavioral logging tests, or convert it to assert on real `logger.warning` kwargs if additional field coverage is wanted.

---

### TST-007: Unawaited-coroutine RuntimeWarnings mask real bugs and indicate weak async tests

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_cli.py::test_download_keyboard_interrupt`, `tests/test_downloader_throttle.py::test_wait_if_paused_returns_on_shutdown` |
| **Classification** | advisory |

**Description:** The suite emits 4 `RuntimeWarning: coroutine '...' was never awaited` (from `unittest/mock.py`) during the run:
- `coroutine 'download.<locals>._download' was never awaited` — caused by `test_download_keyboard_interrupt` (`test_cli.py:100`) patching `vkdownloader.cli.asyncio.run` with `side_effect=KeyboardInterrupt()`. The production `_download` coroutine is created but never awaited, so the test verifies only the outer CLI `except` block; the actual download body (signal-handler setup, partial-state cleanup) is never executed. The unawaited coroutine leaks.
- `coroutine 'Event.wait' was never awaited` — caused by `test_wait_if_paused_returns_on_shutdown` (`test_downloader_throttle.py:539-557`) setting `mock_event.wait = AsyncMock()` while the shutdown path returns early (is_set=True) without awaiting `wait`, leaving the coroutine unawaited.

These warnings are noise that would hide a genuine "coroutine never awaited" bug in production code (a classic asyncio mistake), degrading the diagnostic value of the test run.

**Evidence:** `uv run pytest -q` warnings summary (4 RuntimeWarnings, 4.74s); `test_cli.py:100`, `test_downloader_throttle.py:539-557`.

**Recommendation:** In `test_download_keyboard_interrupt`, instead of mocking `asyncio.run` wholesale, let the real coroutine run and inject `KeyboardInterrupt` inside it (e.g., via a side-effect on an awaited dependency) so the body executes. In the backoff test, await/cancel the `wait` coroutine or assert the early-return path more precisely so no coroutine leaks. Consider promoting `filterwarnings = error` for `RuntimeWarning` in `pyproject.toml` `[tool.pytest.ini_options]` to fail on such leaks.

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
- `test_pause_overwrites_existing_backoff` (lines 570-580): `pause(url, 1.0)` then `time.sleep(0.02)` then `pause(url, 10.0)` — relies on the first 1.0s backoff still being active after 20ms (fine here, but couples to scheduler behavior) and on second-precision wall clock.

On a loaded/slow CI runner these can intermittently fail or, worse, pass for the wrong reason. They are non-deterministic by construction.

**Evidence:** `tests/test_downloader_throttle.py:510-520`, `:570-580` (`time.sleep` against short `pause` durations).

**Recommendation:** Use a manually advanced fake clock or `freezegun`/`pytest-freezer`, or assert relative ordering without fixed sleeps (e.g., capture `time.monotonic` deltas). At minimum widen margins and avoid coupling to real `time.sleep` for state transitions.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 3 |

## Mandatory Fixes

None (all findings are advisory coverage/quality improvements; no failing tests or confirmed production bug were found).

## Advisory Recommendations

- **TST-001** — Add real execution tests for `_download_segment`, `_fetch_playlist_with_retry`, `_merge_segments_batched` (highest-value coverage gap).
- **TST-002** — Add unit tests for `AdaptiveThrottle` (headline feature, currently 0% coverage).
- **TST-003** — Add tests for `ffmpeg_utils` merge/cancel command construction and process lifecycle.
- **TST-004** — Delete or replace the tautological `tests/integration/test_mock_vk_server.py` with a real round-trip integration test.
- **TST-005** — Implement or remove the `pass`-only `test_path_inside_repo_warns` placeholder.
- **TST-006** — Remove source-inspection `test_structured_logging_fields` (redundant with behavioral logging tests).
- **TST-007** — Fix unawaited-coroutine leaks; consider `filterwarnings = error` for RuntimeWarning.
- **TST-008** — Remove real-clock `time.sleep` dependencies from backoff timing tests.

## Doc Updates Needed

None.
