---
name: 07-tests
description: Test Quality Audit Phase
executor: auditor
status: complete
validated: no
---

# Phase 07 Audit Findings — Test Quality

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
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

**Recommendation:** Replace these tautological tests with actual integration tests that exercise real application code. The recommended approach is to test the extractor service against mock HTTP responses:

```python
# tests/integration/test_extractor_integration.py
from unittest.mock import AsyncMock, patch
from vkdownloader.services.extractor import VKVideoExtractor
from vkdownloader.models.video import Stream


def test_extractor_parses_m3u8_content():
    """Test that extractor correctly parses m3u8 playlist content."""
    m3u8_content = "#EXTM3U\n#EXTINF:10,\nhttps://cdn.example.com/1080p.m3u8\n"
    mock_response = AsyncMock()
    mock_response.text.return_value = m3u8_content

    with patch("aiohttp.ClientSession.get", return_value=mock_response):
        extractor = VKVideoExtractor(settings=Settings())
        # Test _parse_m3u8_segments or related parsing logic
```

For the mock server tests, replace with tests that:
1. Use `responses` library to mock actual HTTP endpoints
2. Test `VKVideoExtractor.extract_streams()` with mock responses
3. Verify m3u8 URL extraction logic
4. Test segment parsing with real content structures

If integration tests are not feasible, delete the file entirely - it provides no coverage value.

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

**Recommendation:** Implement the test using mocking of `Path.resolve()` and `Path(__file__).parent.parent.parent` to control the repository root detection. The implementation approach:

```python
def test_path_inside_repo_warns(tmp_path: Path) -> None:
    """Test that path inside repository root triggers warning."""
    # Create a path inside the actual repo directory
    repo_root = Path(__file__).resolve().parent.parent  # tests/.. = project root
    inside_path = repo_root / "output" / "video.mp4"
    
    with patch("vkdownloader.utils.security.logger") as mock_logger:
        result = validate_output_path(inside_path)
        
        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert "output_path_inside_repository" in call_kwargs.get("event", "")
        assert str(inside_path) in call_kwargs.get("path", "")
```

Alternatively, if mocking is too complex for the project scope, remove the test and add a manual verification note to `docs/11-guides/configuration.md` under security considerations.

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
> - **Detail:** Confirmed - lines 257 and 309 use `assert result.exit_code != 0` without verifying error messages. The actual exit code for invalid enum options is 2 (typer's standard for argument validation errors). This is valid improvement but low impact. Per validation rules, this is valid BEST-PRACTICE with advisory classification.
> - **See also:** —

**Description:** Tests `test_invalid_quality_option` and `test_invalid_method_option` use `assert result.exit_code != 0` which only checks that the exit code is non-zero. They don't verify that the correct error message is displayed or that the proper exception path is taken. This could allow unrelated failures to pass as "correct" validation.

**Evidence:**
- tests/test_cli.py:257: `assert result.exit_code != 0`
- tests/test_cli.py:309: `assert result.exit_code != 0`
- Actual exit code for invalid enum values is 2 (typer argument parsing error)

**Recommendation:** Strengthen assertions to check for specific exit code and error messages that verify the enum validation path. The expected error message contains "invalid" or "not a valid" for typer enum validation:

```python
# Before:
assert result.exit_code != 0

# After:
assert result.exit_code == 2  # Typer's exit code for argument validation errors
assert "invalid" in result.output.lower() or "not a valid" in result.output.lower()
```

For `test_invalid_quality_option` (lines 249-257), the assertion should be:
```python
assert result.exit_code == 2
assert "invalid" in result.output.lower() or "quality" in result.output.lower()
```

For `test_invalid_method_option` (lines 301-309), the assertion should be:
```python
assert result.exit_code == 2
assert "invalid" in result.output.lower() or "method" in result.output.lower()
```

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 1 |

## Mandatory Fixes

- TST-001: Test failure due to environment configuration leak (CRITICAL - causes false-negative test)

## Advisory Recommendations

- TST-002: Remove tautological integration tests or replace with real integration tests
- TST-003: Implement skipped security test with proper mocking
- TST-006: Strengthen invalid option test assertions with specific exit codes and error message checks

---