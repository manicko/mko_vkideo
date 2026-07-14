---
name: 01-cli
description: CLI Entry Point & Command Layer
executor: auditor
status: complete
validated: no
---

# Phase 01 Audit Findings — CLI Entry Point & Command Layer

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### CLI-001: Test failure due to .env configuration overriding Settings defaults

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/test_config.py |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` in `tests/test_config.py:20` asserts that `settings.ssl_verify is True`, but this test fails because the `.env` file at line 12 sets `VKDOWNLOADER_SSL_VERIFY=false`. Pydantic-settings automatically loads `.env` files, causing the test to receive `ssl_verify=False` instead of the expected `True`. This is a test isolation issue where environment configuration leaks into tests.

**Evidence:** 
- Test output: `AssertionError: assert False is True` at `tests/test_config.py:20`
- `.env` file line 12: `VKDOWNLOADER_SSL_VERIFY=false`
- Settings class in `src/vkdownloader/config.py:47-50` uses Pydantic BaseSettings with `env_file=".env"`

**Recommendation:** Modify the test to either: (1) create Settings with explicit `ssl_verify=True` to override the `.env` value, or (2) use `patch.object(Settings, 'model_config', {'env_file': None})` or mock the environment variable before the test. This ensures test isolation from environment configuration.

---

### CLI-002: Business logic function `_sanitize_title` placed in CLI layer

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py:25-33 |
| **Classification** | advisory |

**Description:** The `_sanitize_title` function (lines 25-33) implements filesystem sanitization logic - replacing invalid characters, stripping whitespace, and limiting string length to 100 characters. This is data transformation/business logic that should reside in the utils layer (`src/vkdownloader/utils/`) rather than in the CLI module, to maintain proper separation of concerns and enable reuse if needed elsewhere.

**Evidence:** 
```python
# cli.py:25-33
def _sanitize_title(title: str) -> str:
    for char in '/\\:*?"<>|':
        title = title.replace(char, "_")
    return title.strip()[:100]
```

**Recommendation:** Move `_sanitize_title` to `src/vkdownloader/utils/sanitizer.py` or similar utility module. The CLI should import and use it, keeping command handlers focused on argument parsing and service invocation. Effort: small. Priority: recommended.

---

### CLI-003: Significant business logic embedded in `batch_download` command handler

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py:240-283 |
| **Classification** | advisory |

**Description:** The `_download_single` inner async function within `batch_download` command (lines 240-283) contains substantial business logic including: stream extraction, quality selection, output path validation, Settings instantiation with conditional cookie handling, and output filename generation. This violates the "commands are thin" principle - the CLI handler should only parse arguments and invoke a service function, not contain the download orchestration logic.

**Evidence:** 
- Lines 249-254: Settings instantiation and extraction orchestration
- Lines 256-267: Path validation and filename generation logic
- Lines 269-274: Download invocation with multiple parameters
- Lines 279-330: Progress tracking orchestration in `_run_batch_with_progress`

**Recommendation:** Extract the `_download_single` and `_run_batch_with_progress` logic into a dedicated service function in `src/vkdownloader/services/batch_downloader.py` or similar. The CLI should call this service function. Effort: medium. Priority: recommended.

---

### CLI-004: Direct access to private `_progress_manager._state` attribute in CLI

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py:53 |
| **Classification** | advisory |

**Description:** The `_create_progress_callback` function in cli.py (line 53) directly accesses `_progress_manager._state[url_index]`, which is a private attribute of the ProgressManager class. This breaks encapsulation and creates tight coupling between CLI and service implementation details. The ProgressManager already has an async `update` method that should be used instead.

**Evidence:**
```python
# cli.py:50-55
def callback(video_id: str, downloaded: int, total: int) -> None:
    # Non-blocking - just update shared state
    _progress_manager._state[url_index] = (downloaded, total)
    return callback
```

**Recommendation:** The ProgressManager should provide a synchronous update method that uses thread-safe operations, or the callback design should be refactored to use the existing async API. Consider adding a `update_sync(self, url_index: int, downloaded: int, total: int) -> None` method to ProgressManager. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- CLI-001: Test failure due to .env configuration overriding Settings defaults

## Advisory Recommendations

- CLI-002: Business logic function `_sanitize_title` placed in CLI layer
- CLI-003: Significant business logic embedded in `batch_download` command handler
- CLI-004: Direct access to private `_progress_manager._state` attribute in CLI