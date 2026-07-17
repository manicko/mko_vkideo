---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 07 Audit Findings — Test Quality

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/07-audit-tests.md
**Status:** complete
**Validated:** no

---

## Findings

### TST-001: Empty `tests/integration/` package creates false impression of integration coverage

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/integration/` |
| **Classification** | advisory |

**Description:** The `tests/integration/` directory contains only `__init__.py` and stale `__pycache__/*.pyc` files (including a ghost `test_mock_vk_server.*.pyc` with no corresponding source). Git history confirms the only real integration test was removed in commit `cc9fb65` ("tests: remove tautological tests and implement placeholder security test"), and `git ls-files tests/integration/` returns only `__init__.py`. The package is therefore dead scaffolding: pytest collects zero tests from it, yet its existence suggests integration coverage that does not exist. The audit handbook explicitly flags "critical paths with low or zero coverage" — integration/auth/connection flows for the VK API and browser-cookie extraction are entirely untested at the boundary.

**Evidence:**
- `git ls-files tests/integration/` → `tests/integration/__init__.py` only.
- `Get-ChildItem tests/integration/ -Recurse -File` lists only `__init__.py` plus `.pyc` ghosts.
- No `MockVKServer` / live-API / browser-cookie integration test present anywhere under `tests/`.

**Recommendation:** Either (a) delete the empty `tests/integration/` package to stop implying coverage that does not exist, or (b) add at least one real integration test (e.g., a local mock VK-style HTTP server asserting end-to-end stream extraction / cookie flow). Given the handbook's emphasis on integration paths, (b) is preferred but small; (a) is acceptable for a CLI tool. Effort: small. Priority: recommended.

---

### TST-002: Core download orchestrator (`downloader.py`, 759 lines) has no behavioral test coverage

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `downloader.py` is the central critical path (entry `perform_download`, `download_with_ytdlp_with_resume_fallback`, `_attempt_segment_resume`, `_resolve_cookies`, `_download_with_ytdlp`, `_parse_quality_to_enum`). Existing tests touch it only at the dispatch/logging level:
- `tests/test_cli.py` mocks `vkdownloader.cli.perform_download` wholesale (lines 33, 174, 215, 264, 315, 368, 411, 461), so CLI tests never exercise orchestration logic.
- `tests/test_hls_downloader.py` invokes `perform_download`/`_download_with_ytdlp` but patches out the actual backends (`download_with_ytdlp_with_resume_fallback`, `yt_dlp`, `asyncio` loop) and asserts only that a log line was emitted (e.g. lines 1030-1069, 1121-1164).

Consequently, the actual behavior is unverified: the yt-dlp resume-fallback loop (`MAX_RESUME_RETRIES`), partial-file detection and switch to segment download (`_attempt_segment_resume`), the format-selector construction (`best[height<=720]` vs `best`), cookie-file generation and cleanup, and cancellation handling in `_download_with_ytdlp`. A regression in any of these (e.g. wrong format selector, leaked cookie file, broken fallback) would NOT be caught by the current suite. This is the "false sense of safety" the phase is designed to catch.

**Evidence:**
- `tests/test_hls_downloader.py:1030-1069` — `perform_download` patched `download_with_ytdlp_with_resume_fallback`, only `starting_download` log asserted.
- `tests/test_hls_downloader.py:1121-1164` — `_download_with_ytdlp` with `yt_dlp` and the event loop mocked; only `starting_ytdlp_download` log asserted, no assertion on `ydl_opts` (format selector, cookiefile, ssl).
- `tests/test_cli.py` — `perform_download` fully mocked in all 8 download tests.

**Recommendation:** Add focused unit tests that assert on the real orchestration outputs without invoking the network: (1) `_parse_quality_to_enum` valid/invalid/`-p`-suffix cases; (2) `_download_with_ytdlp` building correct `ydl_opts` (format string, `cookiefile` presence, `nocheckcertificate` from `ssl_verify`) by capturing the dict; (3) `perform_download` AUTO/YTDLP/FFMPEG dispatch and the resume-fallback path using a fake extractor rather than mocking `perform_download` itself. Effort: medium. Priority: recommended.

---

### TST-003: Untested production modules — `cookies.py`, `signal_handlers.py`, `exceptions.py`

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/cookies.py`, `src/vkdownloader/services/signal_handlers.py`, `src/vkdownloader/exceptions.py` |
| **Classification** | advisory |

**Description:** Three production modules have zero tests:
- `services/cookies.py` (`_cookies_to_netscape`, 56 lines): domain preservation for Cookie objects, `=` inside cookie values, empty input, and the backward-compatible string branch are unverified (segment/ffmpeg tests touch it indirectly but never assert its format correctness).
- `services/signal_handlers.py` (`setup_signal_handlers`, 54 lines): graceful-shutdown wiring (SIGINT/SIGTERM → shutdown event) is entirely untested, including the Windows `NotImplementedError` fallback and the duplicate-registration guard.
- `exceptions.py` (48 lines): `QualityNotAvailableError.requested`/`available` contract and message format are used across CLI/extractor but never asserted in a dedicated test.

None are critical hot paths, but they contain real edge-case logic (cookie value parsing, signal fallback) where silent breakage is plausible.

**Evidence:**
- No `test_cookies.py`, `test_signal_handlers.py`, or `test_exceptions.py` in `tests/`.
- `git ls-files tests/` lists 11 test modules; none target the three files above.

**Recommendation:** Add small, isolated unit tests: `cookies.py` (domain preserved from Cookie object, `=` in value, empty list → header-only, string branch → `.vkvideo.ru`); `exceptions.py` (`QualityNotAvailableError` attributes and message); `signal_handlers.py` at minimum a smoke test invoking `setup_signal_handlers()` under a running loop and asserting the shutdown event flips on a dispatched signal. Effort: small. Priority: recommended.

---

### TST-004: `ruff check tests/` fails — missing trailing newline in `test_security.py`

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `tests/test_security.py` |
| **Classification** | advisory |

**Description:** Running the project's mandated linter on the test suite reports a failure (line 74, missing trailing newline). This means `uv run ruff check` is not clean for the test tree, contradicting the project's lint-discipline expectations and any CI gate that runs ruff over `tests/`. It is a trivial but real hygiene defect in the test code itself.

**Evidence:**
```
$ uv run ruff check tests/
   |
74 |         assert result == "***REDACTED***"
   |                                      ^
help: Add trailing newline
Found 1 error.
[*] 1 fixable with the `--fix` option.
```
- `tests/test_security.py` line 74 is the final line of the file with no terminating newline.

**Recommendation:** Run `uv run ruff check --fix tests/` (or add the newline manually) and ensure CI lints `tests/` alongside `src/`. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 2 |

## Mandatory Fixes

None. (No security, data-loss, or correctness defects in the test suite itself; TST-002/TST-003 reduce real coverage but do not indicate a known production bug.)

## Advisory Recommendations

- TST-001: Remove or populate the empty `tests/integration/` package.
- TST-002: Add behavioral tests for `downloader.py` orchestration (resume fallback, format selector, cookie-file lifecycle).
- TST-003: Add unit tests for `cookies.py`, `signal_handlers.py`, `exceptions.py`.
- TST-004: Fix the `ruff` trailing-newline error in `tests/test_security.py` and lint `tests/` in CI.

## Doc Updates Needed

None required by this phase.
