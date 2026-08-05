# Phase 07 Audit Findings — Test Quality

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification

- **R1 — Full suite:** `uv run pytest tests/` — **248 passed**, 0 failed, ~10s (stable across 4 sequential runs: 10.05s, 9.60s, 9.87s, 9.78s). No flakes, no order dependence.
- **R2 — Failures:** None (no failures to classify as production-bug vs test-bug).
- **R3 — Tautologies:** See TST-001/TST-003/TST-005 below.
- **No coverage tool configured** (pytest-cov absent from `pyproject.toml` deps); coverage gaps in TST-006 were identified by static reading of tests vs source.
- **Note:** `pytest-randomly` is not installed, so test-order shuffling was unavailable; only repeated sequential runs were used for isolation/determinism checks.

---

## Findings

### TST-001: `TestYtdlpOptions` tests never invoke `_build_ytdlp_options` — they assert hand-written dict literals (tautological)

| Field | Value |
| **ID** | TST-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_hls_downloader.py` (`TestYtdlpOptions`, lines 403–437) |
| **Classification** | mandatory |

**Description:** Three tests — `test_ytdlp_options_includes_throttled_rate`, `test_ytdlp_options_includes_http_chunk_size`, `test_ytdlp_options_custom_values` — build a `ydl_opts = {...}` dict inline from `Settings` values and then assert the dict equals the values they just read out of it. They never call the production `_build_ytdlp_options`. That helper is only actually exercised by `TestYtDlpShutdownHook` (lines 1957, 1984, 2007). A regression in `_build_ytdlp_options` — wrong yt-dlp key name, dropped `cookiefile`/`http_headers`, or wrong `nocheckcertificate` mapping — would escape all three `TestYtdlpOptions` tests.

**Evidence:** Grep for `_build_ytdlp_options` in `tests/test_hls_downloader.py` returns the import (line 18) and references only inside `TestYtDlpShutdownHook`. `TestYtdlpOptions` methods instead construct `ydl_opts = {"throttledratelimit": test_settings.throttled_rate, "http_chunk_size": ...}` (lines 405, 415, 429) and assert `ydl_opts["throttledratelimit"] == 10000` — i.e. `10000 == 10000`, which cannot fail regardless of production code.

**Recommendation:** Replace the inline dict assertions with a real call to `_build_ytdlp_options(...)` and assert on the returned dict's `throttledratelimit`, `http_chunk_size`, `cookiefile`, `http_headers`, and `nocheckcertificate` keys. Effort: small.

---

### TST-002: Intended test `test_download_segment_main_sequential_dispatch` is missing — its body was appended to the preceding test

| Field | Value |
| **ID** | TST-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_hls_downloader.py` (`TestDownloadSegmentRealExecution`, lines 1591–1648) |
| **Classification** | mandatory |

**Description:** A parallel-dispatch test exists at line 1649 (`test_download_segment_main_parallel_dispatch`), but directly before it, `test_download_segment_parallel_fails_fast_on_non_retryable` (line 1591) ends with assertions at lines 1619–1620. Immediately after, an orphaned docstring string (line 1621) and then the entire body intended for `test_download_segment_main_sequential_dispatch` follow — but the `async def test_download_segment_main_sequential_dispatch(...)` definition line was dropped. As a result pytest collects no such test (confirmed: absent from the 248-test run), and the sequential-dispatch behavior runs only incidentally inside a test named for parallel fail-fast, with a stray no-op string literal.

**Evidence:** Lines 1619–1647:
```python
        assert result is False
        assert mock_session.get.call_count == 1
        """Test _download_segment dispatches to sequential mode when max_concurrent=1."""
        segment_url = "https://example.com/segment.ts"
        ...
            result = await _download_segment(
                ...
                max_concurrent_downloads=1,
            )
        assert result is True
        assert output_path.read_bytes() == b"main segment content"
```
`grep "def test_download_segment_main_sequential_dispatch"` → no match. Collection lists `..._fails_fast_on_non_retryable` then `..._main_parallel_dispatch` with nothing between.

**Recommendation:** Restore the dropped `async def test_download_segment_main_sequential_dispatch(self, test_settings, tmp_path) -> None:` definition so the sequential dispatch path has its own named test, and delete the orphaned docstring literal at line 1621. Effort: trivial.

---

### TST-003: `test_parallel_download_uses_gather` mocks `asyncio.gather` so download tasks never execute (tests the mock, not the logic)

| Field | Value |
| **ID** | TST-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_hls_downloader.py` (`TestParallelSegmentsDownload::test_parallel_download_uses_gather`, lines 494–535) |
| **Classification** | advisory |

**Description:** The test patches `asyncio.gather` with an `async def mock_gather` that returns `[True] * len(tasks)` without awaiting the task coroutines. The tasks (created via `asyncio.create_task` in `_create_segment_download_tasks`, `segment_downloader.py:676`) therefore never run. This is amplified by the fact that `_download_segment` is mocked with `return_value=True` — a plain `bool`, not a coroutine. The real `_download_segment_concurrent` (`segment_downloader.py:598`) does `result = await _download_segment(...)`, which would raise `TypeError: object bool can't be used in 'await' expression` if the task body ever executed. The only assertion is `assert gather_called` — so the test cannot detect defects in the parallel download path (semaphore dispatch, task creation, gather wiring). Pending tasks that are scheduled but never awaited also risk "Task was destroyed but it is pending" warnings at teardown.

**Evidence:** Lines 519–525 patch `_download_segment` (`return_value=True`) and `asyncio.gather` (`side_effect=mock_gather`); line 535 asserts only `gather_called`. Grep confirms `_download_segment` is mocked as a sync `return_value`, not an `AsyncMock`. The real `_download_segment_concurrent` path is never executed under this test.

**Recommendation:** Either make `_download_segment` an `AsyncMock` and let `asyncio.gather` run the real tasks (then assert on `download_count` and the segment output), or drop the gather mock and assert on the end-to-end outcome (merged output file / segment count). Effort: small.

---

### TST-004: `_download_with_ytdlp` tests patch `asyncio.get_event_loop` but production calls `get_running_loop` (dead executor mock)

| Field | Value |
| **ID** | TST-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `tests/test_hls_downloader.py` (`test_cookies_passed_to_ytdlp_creates_cookie_file` line 615; `test_download_with_ytdlp_logs_download_start` line 1046) |
| **Classification** | advisory |

**Description:** Both tests patch `vkdownloader.services.downloader.asyncio.get_event_loop` and install a custom `run_in_executor` on the mock's `return_value`. Production code (`downloader.py:645`) calls `asyncio.get_running_loop()`, which the patch does not affect — so the real event loop and its real `run_in_executor` are used and the intended executor mock is dead code. The tests pass only because `yt_dlp.YoutubeDL` is fully mocked, masking the mismatch and leaving the executor wiring untested.

**Evidence:** `src/vkdownloader/services/downloader.py:645`: `loop = asyncio.get_running_loop()`. Tests patch `asyncio.get_event_loop` (e.g. line 615: `patch("vkdownloader.services.downloader.asyncio.get_event_loop")`).

**Recommendation:** Patch `asyncio.get_running_loop` (or the loop's `run_in_executor`) instead of `get_event_loop`, so the executor wiring is genuinely covered rather than papered over by the yt-dlp mock. Effort: small.

---

### TST-005: Four `@pytest.mark.asyncio` tests perform no `await` (misleading async marking)

| Field | Value |
| **ID** | TST-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_extractor.py` (lines 127, 172, 185, 204) |
| **Classification** | advisory |

**Description:** `test_format_cookies_for_ffmpeg`, `test_format_cookies_for_ffmpeg_all_cookies_included`, `test_cookies_to_netscape_preserves_domain`, and `test_cookies_to_netscape_backward_compatible` are declared `async def` and decorated `@pytest.mark.asyncio`, but their bodies call only synchronous methods (`_format_cookies_for_ffmpeg`, `_cookies_to_netscape`) and never `await`. The async marking is misleading (implies an async code path is being tested) and adds unnecessary event-loop setup per test.

**Evidence:** Grep shows `@pytest.mark.asyncio` immediately before each of those four definitions; the function bodies contain no `await` keyword.

**Recommendation:** Drop `async`/`@pytest.mark.asyncio` on these four tests so the signature honestly reflects that they exercise synchronous methods. Effort: trivial.

---

### TST-006: Critical orchestration/config paths have no test coverage

| Field | Value |
| **ID** | TST-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `segment_downloader.py`, `downloader_throttle.py`, `ffmpeg_utils.py`, `signal_handlers.py` |
| **Classification** | advisory |

**Description:** Several critical paths are either untested or only exercised through tests that mock the unit itself away. Notable gaps (no direct test, only mocked/indirect coverage):
- `_run_download_session` (`segment_downloader.py:690`) — aiohttp `ClientSession`/`TCPConnector` + `DownloadPolicy` wiring; invoked only via `download_hls_with_resume` tests that mock the internals.
- `_create_connector` (`segment_downloader.py:470`) — the `ssl_verify` branch (builds a `TCPConnector` with a `CERT_NONE` SSL context) and the non-verified branch; never asserted.
- `download_with_ytdlp_with_resume_fallback` (`downloader.py:413`) + `_attempt_segment_resume` (`downloader.py:494`) — the yt-dlp→segment-resume retry/fallback decision tree (partial-file detection, fresh-token acquisition, segment resume) is untested.
- `_parse_quality_to_enum` (`downloader.py:104`) — `QualityEnum` literal / numeric / `Q`-prefix parsing not unit-tested.
- `cleanup_signal_handlers` (`signal_handlers.py:57`) — never tested (only `setup_signal_handlers` is).
- `_temp_headers_file` exception/cleanup path (`downloader.py:57`) and `_await_first_and_cancel_others` cancellation path (`downloader.py:79`) — untested.

**Evidence:** `grep -rn "_create_connector\|download_with_ytdlp_with_resume_fallback\|_attempt_segment_resume\|_parse_quality_to_enum\|cleanup_signal_handlers" tests/` returns no assertion-level references to these symbols (only incidental real usage inside `download_hls_with_resume` tests). No test asserts SSL-context construction, fallback switching, or quality-enum parsing.

**Recommendation (prioritized):** (1) add unit tests for `_parse_quality_to_enum` (trivial, high value); (2) test `_create_connector` SSL on/off branching; (3) a single `download_with_ytdlp_with_resume_fallback` fallback scenario (yt-dlp returns `None` with partial file → segment resume runs); (4) `cleanup_signal_handlers` reset behavior. Effort: medium.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 2 |

## Mandatory Fixes

- **TST-001:** Replace tautological `TestYtdlpOptions` tests with real calls to `_build_ytdlp_options`.
- **TST-002:** Restore the dropped `test_download_segment_main_sequential_dispatch` definition; remove the orphaned docstring literal at `test_hls_downloader.py:1621`.

## Advisory Recommendations

- **TST-003:** Stop mocking `asyncio.gather`; run real tasks with an `AsyncMock`-based `_download_segment` and assert on outcome.
- **TST-004:** Patch `asyncio.get_running_loop` (not `get_event_loop`) in the `_download_with_ytdlp` tests.
- **TST-005:** Remove misleading `async`/`@pytest.mark.asyncio` from the four synchronous extractor tests.
- **TST-006:** Add the prioritized coverage gaps above (quality parsing, SSL connector, yt-dlp fallback, signal cleanup).

## Doc Updates Needed

(none)
