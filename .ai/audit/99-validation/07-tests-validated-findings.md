# Phase 07 Audit Findings — Test Quality (Validated)

**Executor:** audit-executor → validated by: validator  
**Source:** `/.ai/audit/07-tests/findings.md`  
**Status:** validated  

---

## Runtime Verification Summary

- **R1 — Full suite:** `uv run pytest tests/ -q` → `216 passed in 18.02s`. No failures, no errors.
- **R2 — Failures:** None to analyze.
- **R3 — Tautological/no-op tests:** 1 instance found (validated below).
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

**Description:** `TestRetry429WithBackoff.test_structured_logging_on_retry` (lines 379-422) is named and documented to verify "structured logging fields: attempt, status, retry_after, segment_index, url", but it asserts nothing about logging. The test mocks `_strip_auth_params` and `random.uniform` and invokes `_retry_429_with_backoff` with a 429 response followed by success. The only assertion is `assert result == b"segment content"` plus a comment `# Verify structured logging was verified in separate test`. The production code `src/vkdownloader/services/downloader_throttle.py:200-207` does log `"segment_retry_429"` with exactly those fields. The test cannot catch regressions in this logging behavior.

**Evidence:**
- `tests/test_downloader_throttle.py:379-422` — no `mock_logger.assert_*` / `call_args` checks; only `result == b"segment content"`.
- `tests/test_downloader_throttle.py:438-440` — in the sibling test, `logger.warning` is properly mocked and asserted.
- `src/vkdownloader/services/downloader_throttle.py:200-207` — logging call exists with fields: `attempt`, `status`, `retry_after`, `segment_index`, `url`.

**Recommendation:** Add logging assertions to `test_structured_logging_on_retry`: mock `logger.warning`, invoke the function, and assert that `call_kwargs` contains `attempt`, `status`, `retry_after`, `segment_index`, `url`. The retry behavior itself is correctly tested; only the logging verification is missing.

---

### TST-002: Orphaned compiled integration test artifacts

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `tests/integration/` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Per phase file line 80: "If no coverage tool is configured, note it (but it is not a finding for a CLI tool — coverage is advisory)." The stale `.pyc` artifacts are a housekeeping issue, not a missing coverage requirement.
> - **See also:** TST-003

**Description:** `tests/integration/` contains `__pycache__/` with two stale bytecode files:
- `test_mock_vk_server.cpython-312-pytest-9.0.3.pyc`
- `test_mock_vk_server.cpython-312-pytest-9.1.1.pyc`

There is no `test_mock_vk_server.py` source file. These compiled artifacts are leftovers from a test that was deleted or never committed.

**Evidence:**
- `tests/integration/__pycache__/` contains only `.pyc` files; no `.py` source exists.
- `pyproject.toml` has no pytest configuration for coverage or integration test discovery.

**Recommendation:** Remove stale `__pycache__` artifacts. Add cleanup procedure to CI or `.gitignore`. This is a maintenance task, not a coverage gap.

---

### TST-003: No coverage tooling configured — coverage can regress silently

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

**Description:** `pyproject.toml` defines no `[tool.pytest.ini_options]`, no `addopts`, and no `pytest-cov`/`coverage` configuration. Unit coverage is strong for the active modules (216 tests pass), but there is no enforced floor and no coverage report in CI. Per the phase file's own rules (line 80), coverage tooling for CLI tools is advisory — not mandatory.

**Evidence:**
- `pyproject.toml` (lines 1-101) — no `pytest-cov` dependency, no `addopts`, no `[tool.coverage.*]` section.

**Recommendation:** Per phase rules, this is advisory, not mandatory. Optional improvement: add `pytest-cov` to dev dependencies and a lightweight `addopts = "--cov=vkdownloader --cov-report=term-missing"` (or a CI-only flag) so coverage gaps are visible. No strict threshold is required.

---

### TST-004: Audit phase scope is stale relative to actual architecture

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.kilo/commands/audit/phases/07-audit-tests.md` |
| **Classification** | advisory |

**Description:** The phase brief's "Critical Path Coverage" table (lines 94-104) references components that do not exist in this repository: PostProcessor, ImageCache, TelegramPoster, GSheetsReader, Init service, and CLI commands `init`, `config`, `version`. The actual system is a VK video downloader with services: `extractor`, `downloader`, `segment_downloader`, `downloader_throttle`, `ffmpeg_utils`, `quality`, `cookies`, and infrastructure `browser`/`network_monitor`. The CLI exposes only `download` and `batch` commands (confirmed in `src/vkdownloader/cli.py:253,368`).

**Evidence:**
- `src/vkdownloader/cli.py` — only `@app.command() def download` (line 254) and `@app.command("batch") def batch_download` (line 369).
- `src/vkdownloader/services/` — `extractor.py`, `downloader.py`, `downloader_throttle.py`, `quality.py`, `ffmpeg_utils.py`, `cookies.py` exist; no PostProcessor/ImageCache/TelegramPoster/GSheetsReader.
- `src/vkdownloader/infrastructure/` — contains `browser.py`, `network_monitor.py`; matches actual architecture.

**Recommendation:** Update `.kilo/commands/audit/phases/07-audit-tests.md` "Critical Path Coverage" table to reflect actual components: extractor, downloader pipeline, quality selector, throttle/backoff, ffmpeg merge, browser-cookie path, and CLI `download`/`batch` commands.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | TST-001, TST-002, TST-003, TST-004 |
| Reclassified | 1 | TST-002 (severity: MEDIUM → LOW) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Reclassified Findings

| ID | Original Type | New Type | Original Severity | New Severity | Rationale |
|----|---------------|----------|-------------------|--------------|-----------|
| TST-002 | BEST-PRACTICE | DOC-UPDATE | MEDIUM | LOW | Stale `.pyc` artifacts are housekeeping, not a missing coverage requirement. Coverage is advisory for CLI tools per phase file line 80. |

---

## Required Fixes

None. All findings are advisory.

## Advisory Recommendations

- **TST-001 (MEDIUM):** Add logging assertions to `test_structured_logging_on_retry` to verify structured fields are logged on retry path.
- **TST-002 (LOW):** Clean up stale `.pyc` artifacts in `tests/integration/__pycache__/`.
- **TST-003 (LOW):** Optionally add `pytest-cov` and coverage reporting to CI for visibility.
- **TST-004 (LOW):** Update the audit phase template to reflect actual architecture.