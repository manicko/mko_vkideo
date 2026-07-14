---
name: 07-tests
description: Test Quality Audit Phase
executor: validator
status: complete
validated: yes
---

# Phase 07 Audit Findings — Test Quality (Validated)

**Executor:** validator  
**Source:** /.ai/audit/07-tests/findings.md  
**Status:** complete  
**Validated:** yes

---

## Findings

### TST-001: Test failure due to environment configuration leak into defaults test

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_config.py, src/vkdownloader/config.py, .env |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via execution - test fails with `ssl_verify=False` when `.env` sets `VKDOWNLOADER_SSL_VERIFY=false`. The Settings class uses `env_file: ".env"` in `model_config` (config.py:102), loading environment values that override defaults. This masks configuration behavior in testing.
> - **See also:** —

**Description:** The test `test_settings_creates_with_defaults` fails because the `.env` file in the project root sets `VKDOWNLOADER_SSL_VERIFY=false`, which Pydantic Settings loads as an environment variable. This causes the default value assertion `assert settings.ssl_verify is True` to incorrectly fail, as the actual value becomes `False` due to the environment file. The test suite passes 200/201 tests, but this failure masks a real configuration issue - tests should not depend on external environment file values when testing defaults.

**Evidence:** 
- Test output: `assert settings.ssl_verify is True` fails with `ssl_verify=False`
- `.env` line 12: `VKDOWNLOADER_SSL_VERIFY=false`
- The Settings class uses `env_file` configuration that loads this value

**Recommendation:** Either rename the test to `test_settings_creates_with_env_values` and adjust the assertion, or move the test to a separate file that doesn't load `.env`, or use `Settings(_env_file=None)` to skip environment file loading when testing defaults explicitly.

---

### TST-002: Integration tests are tautological/no-op tests

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/integration/test_mock_vk_server.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed - line 13 sets `mock_response.status = 200` and line 28 asserts `mock_response.status == 200`. Similarly, lines 41-42 and 44 show the same pattern. These tests only verify mock object configuration, not application behavior. They are truly tautological - cannot fail because they test what was just set. Per validation rules, this is valid but advisory (no architectural impact).
> - **See also:** —

**Description:** Integration tests in `test_mock_vk_server.py` assert on mock objects that are constructed and immediately checked within the same test. They cannot actually fail because they test the mock setup, not the application code. For example, `test_mock_video_page_response` asserts `mock_response.status == 200` when the mock was just set to 200 on the previous line. These tests provide no value and a false sense of coverage.

**Evidence:**
- Line 13: `mock_response.status = 200` followed by line 28: `assert mock_response.status == 200`
- Line 40: `mock_response.status = 200` followed by line 44: `assert mock_response.status == 200`
- Line 52: Hardcoded `video_ids` list followed by line 63: `assert vid in html_content` (always true)

**Recommendation:** Remove these tautological tests or replace them with actual integration tests that exercise real application code paths against mock HTTP servers.

---

### TST-003: Skipped test with only `pass` statement provides no coverage

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_security.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed - test contains only `pass` statement (line 64). However, author documented limitation in comments (lines 57-62): "Full integration test would require mocking Path.resolve() which is complex." This is an intentional limitation with documented rationale. The warning behavior exists in code but is not easily testable without complex mocking. Per project rules, this is valid but not high priority.
> - **See also:** —

**Description:** The test `test_path_inside_repo_warns` at line 55-64 contains only a `pass` statement. It was intended to verify that paths inside the repository root trigger a warning, but the implementation was never completed. This represents missing security coverage for the warning behavior.

**Evidence:** `tests/test_security.py:55-64` - the test body is `pass` with a comment explaining why it can't be easily tested.

**Recommendation:** Either implement the test with proper mocking of the repository detection logic, or remove the test and convert it to a manual verification note in documentation.

---

### TST-004: ~~Coverage gap - AdaptiveThrottle module has no tests~~ [REJECTED]

> **Rejection reason:** This finding was addressed in SRV-001 (Phase 03 validation). The `AdaptiveThrottle` class is listed in architecture documentation (`py_map.yaml` and `py_anchors.yaml`), indicating it represents intentional architectural design for future rate limiting strategy. Per project rules: "when a component appears in documentation/spec but is unused, it should be classified as SPEC-DEVIATION (missing integration, not dead code)." This is architectural intent, not a coverage gap.

---

### TST-005: ~~Coverage gap - DTO models have no validation tests~~ [REJECTED]

> **Rejection reason:** The `HLSDownloadRequest` DTO is extensively tested via usage in `test_hls_downloader.py` (7+ test cases use it). Pydantic models inherit automatic validation from the framework - `HttpUrl` validation is exercised when URLs are passed to `DownloadRequest`. Explicit validation tests for Pydantic models typically have low ROI since: (1) validation is automatic and well-tested by Pydantic itself, (2) the models are already exercised through integration in test_hls_downloader.py and production code. Per validation rules: reject when "ROI is negative for project scale."

---

### TST-006: Soft assertion in invalid option tests provides weak validation

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_cli.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed - lines 257 and 309 use `assert result.exit_code != 0` without verifying error messages. This is valid improvement but low impact. Per validation rules, this is valid BEST-PRACTICE with advisory classification.
> - **See also:** —

**Description:** Tests `test_invalid_quality_option` and `test_invalid_method_option` use `assert result.exit_code != 0` which only checks that the exit code is non-zero. They don't verify that the correct error message is displayed or that the proper exception path is taken. This could allow unrelated failures to pass as "correct" validation.

**Evidence:**
- tests/test_cli.py:257: `assert result.exit_code != 0`
- tests/test_cli.py:309: `assert result.exit_code != 0`

**Recommendation:** Strengthen assertions to check for specific error messages or exit codes to ensure the validation logic is actually being tested.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | TST-001, TST-002, TST-003, TST-006 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 2 | TST-004, TST-005 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| TST-004 | Coverage gap - AdaptiveThrottle module has no tests | AdaptiveThrottle is architectural intent per py_map.yaml/py_anchors.yaml; validated in SRV-001 |
| TST-005 | Coverage gap - DTO models have no validation tests | HLSDownloadRequest is extensively tested via usage; Pydantic validation is automatic; low ROI per project rules |

---

## Rollout Analysis

- **TST-001** has medium complexity: requires either test refactoring or .env isolation
- **TST-002** is low effort removal of tautological tests
- **TST-003** is optional - documented limitation in code
- **TST-006** is optional improvement - low impact
- No rollout conflicts detected
- All findings can be addressed independently

---

## Remaining Issues After Validation

| ID | Issue | Classification |
|----|-------|----------------|
| TST-001 | Test failure due to environment configuration leak into defaults test | Mandatory fix |
| TST-002 | Remove tautological integration tests | Advisory improvement |
| TST-003 | Implement or remove skipped security test | Advisory improvement |
| TST-006 | Strengthen invalid option test assertions for better validation | Advisory improvement |

---

## Cross-Phase References

- TST-004 relates to SRV-001 (AdaptiveThrottle coverage/questioned usage) - already validated in Phase 03