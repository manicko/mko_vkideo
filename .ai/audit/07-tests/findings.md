# Phase 07 Audit Findings — Test Quality

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/07-audit-tests.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

- **R1 — Full suite:** `uv run pytest tests/ -q` → `216 passed in 18.02s`. No failures, no errors.
- **R2 — Failures:** None to analyze.
- **R3 — Tautological/no-op tests:** 1 instance found (see TST-001).
- **R4 — Isolation:** Suite passes deterministically; throttle tests correctly mock `random.uniform` and shutdown events to avoid flakiness.
- **R5 — Coverage gaps:** Integration test directory contains only a stale compiled artifact and no source; no integration tests execute. No coverage tooling configured.

---

## Findings

### TST-001: Tautological test — structured-logging-on-retry path is never asserted

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/test_downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `TestRetry429WithBackoff.test_structured_logging_on_retry` (lines 379–422) is named and documented to verify "structured logging fields: attempt, status, retry_after, segment_index, url", but it asserts nothing about logging. It mocks `vkdownloader.services.downloader_throttle.logger.warning` **only in the non-retryable sibling test** (`test_structured_logging_on_non_retryable`, line 424, which does assert). In the retry test body the only assertions are `assert result == b"segment content"` plus a comment `# Verify structured logging was verified in separate test`. The comment points to a "separate test" that does not exist for this code path. As written, the function's structured-logging behavior on a 429→retry path can regress (e.g., a field renamed or dropped) and the test will still pass. It is effectively testing only the happy-path return value — identical to every other retry test.

**Evidence:**
- `tests/test_downloader_throttle.py:379-422` — no `mock_logger.assert_*` / `call_args` checks; only `result == b"segment content"`.
- Contrast with `tests/test_downloader_throttle.py:424-457` which correctly asserts `mock_warning.assert_called_once()` and inspects `call_kwargs`.

**Recommendation:** Either (a) add real assertions: spy on `logger.warning`/`logger.info`, invoke the function, and assert the structured fields (`attempt`, `status`, `retry_after`, `segment_index`, `url`) appear in the log call; or (b) delete the test if it is redundant with `test_structured_logging_on_non_retryable`. A test whose name promises a verification it does not perform gives false confidence in observability — a stated project goal.

---

### TST-002: Orphaned compiled integration test with no source — integration coverage is effectively zero

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `tests/integration/` |
| **Classification** | advisory |

**Description:** `tests/integration/` contains only `__init__.py` and two stale bytecode files:
- `tests/integration/__pycache__/test_mock_vk_server.cpython-312-pytest-9.0.3.pyc`
- `tests/integration/__pycache__/test_mock_vk_server.cpython-312-pytest-9.1.1.pyc`

There is **no `test_mock_vk_server.py` source file** (`Test-Path` returns `False`). The compiled artifacts are leftovers from a test that was deleted or never committed. Because pytest collects `.py` files, no integration test is collected or run — the project's end-to-end / mock-VK-server path has zero executable coverage, despite the presence of these artifacts implying it should exist.

**Evidence:**
- `Get-ChildItem tests\integration -Recurse -File -Name` (excluding `__pycache__`) → only `__init__.py`.
- `Test-Path tests\integration\test_mock_vk_server.py` → `False`.
- The `.pyc` filenames reference a module `test_mock_vk_server` that no longer has a source.

**Recommendation:** Restore/commit the missing `test_mock_vk_server.py` (or whatever integration tests were intended) under `tests/integration/`, or remove the stale `__pycache__` artifacts and delete the empty integration package if integration testing is not planned. Add a CI step that fails on orphaned `.pyc` without matching `.py`, or simply keep integration tests tracked. The current state silently hides a missing test suite.

---

### TST-003: No coverage tooling configured — coverage can regress silently

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

**Description:** `pyproject.toml` defines no `[tool.pytest.ini_options]`, no `addopts`, and no `pytest-cov`/`coverage` configuration. Unit coverage is strong for the active modules, but there is no enforced floor and no coverage report in CI. The brief notes coverage is advisory for a CLI tool, so this is not mandatory — however, the combination of (a) zero integration coverage (TST-002) and (b) no coverage measurement means a future refactor that drops unit coverage would pass CI undetected.

**Evidence:**
- `pyproject.toml` (full file, 101 lines) — no `pytest-cov` dependency, no `addopts`, no `[tool.coverage.*]` section.

**Recommendation:** Add `pytest-cov` to dev dependencies and a lightweight `addopts = "--cov=vkdownloader --cov-report=term-missing"` (or a CI-only flag) so coverage gaps are visible. No strict threshold is required, but the report prevents silent regressions and makes the integration gap in TST-002 obvious.

---

### TST-004: Audit phase scope is stale relative to actual architecture

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.kilo/commands/audit/phases/07-audit-tests.md`, `tests/` |
| **Classification** | advisory |

**Description:** The phase brief's expected components (PostProcessor, ImageCache, TelegramPoster, GSheetsReader, Init service) and CLI commands (init, run, config, version) do **not exist** in this repository. The actual system is a VK video downloader with services: `extractor`, `downloader`, `segment_downloader`, `downloader_throttle`, `ffmpeg_utils`, `quality`, `cookies`, and infrastructure `browser`/`network_monitor`. The CLI exposes only `download` and `batch` commands (confirmed in `src/vkdownloader/cli.py:253,368`). The "Critical Path Coverage" matrix in the phase therefore describes a different (or planned) system and would misreport coverage if followed literally.

**Evidence:**
- `src/vkdownloader/cli.py` — only `@app.command() def download` (line 254) and `@app.command("batch") def batch_download` (line 369); no init/config/version.
- `src/vkdownloader/services/` — no PostProcessor/ImageCache/TelegramPoster/GSheetsReader; `infrastructure/` contains `browser.py`, `network_monitor.py`.
- Phase file `.kilo/commands/audit/phases/07-audit-tests.md` "Critical Path Coverage" table lists the non-existent components and commands.

**Recommendation:** Update the phase's coverage matrix to the real architecture (downloader pipeline, extractor, quality selector, throttle/backoff, ffmpeg merge, browser-cookie path, CLI `download`/`batch`) so coverage findings are measured against code that exists. This is a documentation/process correction, not a code defect.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 2 |

## Mandatory Fixes

None.

## Advisory Recommendations

- **TST-001 (MEDIUM):** Add real logging assertions to `test_structured_logging_on_retry` or remove it.
- **TST-002 (MEDIUM):** Restore/commit the missing `tests/integration/test_mock_vk_server.py` or delete orphaned `.pyc` artifacts; the integration path currently has no executable tests.
- **TST-003 (LOW):** Add `pytest-cov` and a coverage report to CI to make coverage gaps visible.
- **TST-004 (LOW / DOC-UPDATE):** Refresh the phase's coverage matrix to match the real downloader architecture and actual CLI commands.

## Doc Updates Needed

- **TST-004:** Update `.kilo/commands/audit/phases/07-audit-tests.md` "Critical Path Coverage" table (and the "CLI commands" expectations) to reflect the actual `vkdownloader` services and `download`/`batch` CLI commands.
