---
name: 07-tests
description: Test Quality Audit Phase
executor: auditor
status: complete
validated: no
---

# Phase 07 Audit Findings — Test Quality

**Executor:** auditor  
**Template:** /.ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** no

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

**Description:** The test `test_path_inside_repo_warns` at line 55-64 contains only a `pass` statement. It was intended to verify that paths inside the repository root trigger a warning, but the implementation was never completed. This represents missing security coverage for the warning behavior.

**Evidence:** `tests/test_security.py:55-64` - the test body is `pass` with a comment explaining why it can't be easily tested.

**Recommendation:** Either implement the test with proper mocking of the repository detection logic, or remove the test and convert it to a manual verification note in documentation.

---

### TST-004: Coverage gap - AdaptiveThrottle module has no tests

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/infrastructure/adaptive_throttle.py |
| **Classification** | advisory |

**Description:** The `AdaptiveThrottle` class in `infrastructure/adaptive_throttle.py` provides rate limiting with dynamic delay adjustment based on response patterns. It has no dedicated test file. Bugs in the exponential backoff logic (`on_rate_limited`), delay recovery (`on_success`), or base delay calculation could go undetected.

**Evidence:** No test files reference `AdaptiveThrottle`. The module provides:
- `_calculate_base_delay` - potential calculation bugs
- `on_rate_limited` - delay cap at 10.0 seconds
- `on_success` - recovery to minimum 1.0 seconds

**Recommendation:** Add tests for `AdaptiveThrottle` covering: rate limit backoff increases, success recovery reduces delay, delay capping behavior, and initial delay calculation.

---

### TST-005: Coverage gap - DTO models have no validation tests

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/models/dtos.py |
| **Classification** | advisory |

**Description:** The `HLSDownloadRequest`, `DownloadRequest`, and `DownloadResult` Pydantic models in `models/dtos.py` have no dedicated tests for field validation, constraints, or edge cases. While these are used indirectly in other tests, there are no explicit tests for model validation behavior.

**Evidence:** No test file contains `test_.*dtos` or tests for `DownloadRequest`/`DownloadResult` models. The `HLSDownloadRequest` is only used as a test input, not validated itself via `HttpUrl` or other constraints.

**Recommendation:** Add tests for DTO models covering: required field validation, HttpUrl format validation for `DownloadRequest.url`, optional field defaults, and model serialization/deserialization.

---

### TST-006: Soft assertion in invalid option tests provides weak validation

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_cli.py |
| **Classification** | advisory |

**Description:** Tests `test_invalid_quality_option` and `test_invalid_method_option` use `assert result.exit_code != 0` which only checks that the exit code is non-zero. They don't verify that the correct error message is displayed or that the proper exception path is taken. This could allow unrelated failures to pass as "correct" validation.

**Evidence:**
- tests/test_cli.py:257: `assert result.exit_code != 0`
- tests/test_cli.py:309: `assert result.exit_code != 0`

**Recommendation:** Strengthen assertions to check for specific error messages or exit codes to ensure the validation logic is actually being tested.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- TST-001: Test failure due to environment configuration leak (CRITICAL - causes false-negative test)

## Advisory Recommendations

- TST-002: Remove tautological integration tests
- TST-003: Implement or remove skipped security test
- TST-004: Add tests for AdaptiveThrottle module
- TST-005: Add tests for DTO model validation
- TST-006: Strengthen invalid option test assertions

---