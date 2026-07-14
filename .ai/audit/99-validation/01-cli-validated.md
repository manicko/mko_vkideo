---
name: 01-cli
description: CLI Entry Point & Command Layer
executor: validator
status: complete
validated: yes
---

# Phase 01 Audit Findings — CLI Entry Point & Command Layer

**Executor:** validator (validated from auditor findings)
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes

---

## Findings

### CLI-001: Test failure due to .env configuration overriding Settings defaults

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_config.py |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` in `tests/test_config.py:20` asserts that `settings.ssl_verify is True`, but this test fails because the `.env` file at line 12 sets `VKDOWNLOADER_SSL_VERIFY=false`. Pydantic-settings automatically loads `.env` files, causing the test to receive `ssl_verify=False` instead of the expected `True`. This is a test isolation issue where environment configuration leaks into tests.

**Evidence:** 
- Test output: `AssertionError: assert False is True` at `tests/test_config.py:20` (confirmed via execution)
- `.env` file line 12: `VKDOWNLOADER_SSL_VERIFY=false`
- Settings class in `src/vkdownloader/config.py:101-106` uses `model_config = {"env_file": ".env", ...}`
- Default field value in Settings.ssl_verify is `True` (config.py:47-50)

**Recommendation:** Modify the test to either: (1) create Settings with explicit `ssl_verify=True` to override the `.env` value, or (2) use `Settings(model_config={"env_file": None})` or mock the environment variable before the test. This ensures test isolation from environment configuration.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type was RUNTIME-ERROR. Reclassified as SPEC-DEVIATION because the code (Settings default=True, .env value=false) correctly implements configuration loading, but the test assertion incorrectly assumes defaults without accounting for .env. The code is correct; the test expectation is wrong.
> - **See also:** —

---

### CLI-002: Business logic function `_sanitize_title` placed in CLI layer

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py:25-33, src/vkdownloader/utils/security.py |
| **Classification** | mandatory |

**Description:** The `_sanitize_title` function (lines 25-33 in cli.py) implements filesystem sanitization logic - replacing invalid characters, stripping whitespace, and limiting string length to 100 characters. The utils layer (`src/vkdownloader/utils/security.py`) already contains `validate_output_path` for path security. This function logically belongs alongside other sanitization utilities in the security module.

**Evidence:** 
```python
# cli.py:25-33
def _sanitize_title(title: str) -> str:
    """Sanitize title for filesystem safety."""
    for char in '/\\:*?"<>|':
        title = title.replace(char, "_")
    return title.strip()[:100]
```

- Function is used in cli.py lines 136 and 263 for filename generation
- utils/security.py exists for security-related utilities
- Project rule: "Strict Separation of Concerns" requires clear layer boundaries

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Downgraded severity from MEDIUM to LOW. Upgraded classification from advisory to mandatory. Original type was BEST-PRACTICE. Reclassified as SPEC-DEVIATION because the function is clearly utility code that violates the project's separation of concerns rule. The utils/security.py module already exists for this purpose.
> - **See also:** —

---

### CLI-003: Significant business logic embedded in `batch_download` command handler

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py:181-361 |
| **Classification** | mandatory |

**Description:** The `_download_single` and `_run_batch_with_progress` inner async functions within `batch_download` command contain download orchestration logic including stream extraction, quality selection, and progress tracking. The existing `perform_download` service function (services/downloader.py:1034-1130) already handles single video download orchestration, but batch-specific coordination (shared semaphore, backoff coordinator, progress aggregation) remains in the CLI.

**Evidence:** 
- cli.py lines 240-283: `_download_single` inner function with Settings, extractor, quality selection
- cli.py lines 285-330: `_run_batch_with_progress` with semaphore/backoff coordinator creation
- services/downloader.py: `perform_download()` already provides download orchestration
- Documentation STRUCT.md describes batch download architecture intentionally in CLI layer

> **Validation Note:**
> - **Action:** partially validated with caveat
> - **Detail:** Core download logic IS duplicated - `_download_single` repeats what `perform_download` does. However, the batch-specific coordination (shared resources, progress aggregation) is appropriately CLI-layer code. The `_download_single` logic should be refactored to reuse `perform_download`, but full extraction to a separate service has negative ROI.
> - **See also:** CLI-002 (filename sanitization could be extracted together)

---

### CLI-004: Direct access to private `_progress_manager._state` attribute in CLI

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | — |
| **Affected Modules** | src/vkdownloader/cli.py:53, src/vkdownloader/services/downloader_throttle.py:78-140 |
| **Classification** | — |

> ~~CLI-004: Direct access to private `_progress_manager._state` attribute in CLI~~ [REJECTED]
> 
> **Rejection reason:** This is intentional design documented in ProgressManager class docstring (downloader_throttle.py:84-91). The code explicitly states: "Direct tuple assignment to `_state[url_index]` is GIL-atomic in CPython, providing safe fire-and-forget semantics for progress callbacks invoked from async tasks. The async lock protects the read path in get_formatted_progress, ensuring consistent reads while callbacks may write concurrently." Using the async `update` method from a sync callback would require blocking, which this design intentionally avoids.

---

## Cross-Phase Conflict Detected

**CLI-001 and CFG-001 are duplicate findings** describing the same test failure. Both phases correctly identify the same root cause (test isolation from .env configuration). This represents a duplicate audit across phases rather than conflicting evidence.

### Cross-Phase Dependencies

| Finding | Depends On | Notes |
|---------|------------|-------|
| CLI-002 | CFG-002 | Both involve layer boundaries; CFG-002 addresses models package exports |
| CLI-001 | — | Standalone test fix |

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 0 | — |
| Reclassified | 3 | CLI-001 (RUNTIME-ERROR→SPEC-DEVIATION), CLI-002 (BEST-PRACTICE→SPEC-DEVIATION), CLI-003 (BEST-PRACTICE→SPEC-DEVIATION with caveat) |
| Merged | 0 | — |
| Rejected | 1 | CLI-004 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| CLI-004 | Direct access to private `_progress_manager._state` attribute | Intentional design per ProgressManager docstring; GIL-atomic write pattern with async-protected reads is valid concurrency approach |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CLI-001 | RUNTIME-ERROR | SPEC-DEVIATION | Code correctly loads .env config; test expectation is incorrect |
| CLI-002 | BEST-PRACTICE | SPEC-DEVIATION | Violates separation of concerns; function belongs in utils layer |
| CLI-003 | BEST-PRACTICE | SPEC-DEVIATION | Partial violation: download logic duplicated from `perform_download`, though batch coordination is appropriately placed |

### Remaining Issues After Validation

| ID | Issue | Classification |
|----|-------|----------------|
| CLI-001 | Test assertion needs fix for .env isolation | Mandatory fix |
| CLI-002 | `_sanitize_title` should move to utils/security.py | Mandatory fix |
| CLI-003 | Refactor `_download_single` to reuse `perform_download` instead of duplicating logic | Optional improvement |

>**Note:** CLI-001 and CFG-001 describe the same issue (duplicate finding across phases). Fixing CLI-001 will resolve CFG-001.

---

## Rollout Analysis

- CLI-001 and CLI-002 can be fixed independently
- CLI-003 refactor would reduce code duplication but requires careful testing of batch download flow
- No circular dependencies or rollout conflicts detected