---
name: 02-config
description: Configuration & Pydantic Models
executor: validator
status: complete
validated: yes
---

# Phase 02 Audit Findings — Configuration & Pydantic Models

**Executor:** validator (validated from auditor findings)  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** yes

---

## Findings

### CFG-001: Test failure due to .env configuration overriding Settings defaults

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_config.py:10-24, src/vkdownloader/config.py:101-106 |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` asserts that `settings.ssl_verify is True`, but this test fails because the `.env` file sets `VKDOWNLOADER_SSL_VERIFY=false`. Pydantic-settings automatically loads `.env` files via `env_file=".env"` in the model_config, causing the test to receive `ssl_verify=False` instead of the expected `True`. This is a test isolation issue where environment configuration leaks into tests.

**Evidence:**
- Test output: `AssertionError: assert False is True` at `tests/test_config.py:20` (confirmed via `uv run pytest`)
- `.env` file line 12: `VKDOWNLOADER_SSL_VERIFY=false`
- Settings class in `src/vkdownloader/config.py:101-106` uses Pydantic BaseSettings with `env_file=".env"` in model_config
- `Settings().model_fields["ssl_verify"].default` returns `True` but `.env` override takes precedence

**Recommendation:** Modify the test to either: (1) create Settings with explicit `ssl_verify=True` to override the `.env` value, or (2) use `Settings(model_config={"env_file": None})` to disable .env loading during the test. This ensures test isolation from environment configuration.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type was RUNTIME-ERROR. Reclassified as SPEC-DEVIATION because the code (Settings default=True, .env value=false) correctly implements configuration loading, but the test assertion incorrectly assumes defaults without accounting for .env. The code behaves correctly; the test expectation violates the Separation of Concerns principle (test should not depend on environment).
> - **See also:** CLI-001 (duplicate finding in Phase 01); fixing either resolves both.

---

### CFG-002: Missing exports for CookieSource and DownloadMethod in models/__init__.py

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/__init__.py:4-19 |
| **Classification** | mandatory |

**Description:** The `CookieSource` and `DownloadMethod` enums are used directly in `src/vkdownloader/config.py:10` and `src/vkdownloader/cli.py:12`, but they are not exported in the models package `__init__.py`. The `.enums` module defines 6 enums (`QualityEnum`, `StreamFormat`, `LogLevel`, `DownloadStatus`, `DownloadMethod`, `CookieSource`), but only 4 are re-exported (`QualityEnum`, `StreamFormat`, `LogLevel`, `DownloadStatus`). This creates inconsistency and forces consumers to import directly from the submodule rather than using the package public API.

**Evidence:**
- `src/vkdownloader/models/__init__.py:4` imports only 4 enums: `from .enums import DownloadStatus, LogLevel, QualityEnum, StreamFormat`
- `src/vkdownloader/config.py:10` imports via `from vkdownloader.models.enums import CookieSource, DownloadMethod, LogLevel`
- `src/vkdownloader/cli.py:12` imports via `from .models.enums import CookieSource, DownloadMethod, QualityEnum`
- `src/vkdownloader/models/enums.py` defines all 6 enums (lines 6-60)

**Recommendation:** Add `DownloadMethod` and `CookieSource` to the imports and `__all__` list in `src/vkdownloader/models/__init__.py` to provide a complete public API for the models package. Effort: trivial. Priority: mandatory.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type was SPEC-DEVIATION with advisory classification. Reclassified with mandatory classification because the project rules mandate "Single Responsibility" and "Separation of Concerns" - the public API surface should be intentional and complete. Incomplete exports force external modules to reach into submodules, which violates layer boundaries.
> - **See also:** CLI-002 (related layer boundary issue).

---

### CFG-003: Missing config loading mechanism referenced in audit template

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | .kilo/commands/audit/phases/02-audit-config.md |
| **Classification** | advisory |

**Description:** The audit phase documentation references `TelepostConfigReader`, `PathResolver`, `platformdirs`, `init_project()`, and `config_example.yaml` as expected components of the configuration architecture. However, this project (vkdownloader) does not use YAML-based configuration loading - it uses Pydantic Settings with environment variables (`.env` file). There is no `config_reader.py`, `paths.py`, or YAML config template. The audit template appears to be from a different project (Telepost) and does not match this codebase's architecture.

**Evidence:**
- No `config_reader.py` file exists in the codebase
- No `paths.py` or `PathResolver` class exists
- No `settings/` directory with YAML templates
- Configuration is handled via `src/vkdownloader/config.py` using Pydantic BaseSettings with `.env` env_file
- `pyproject.toml` shows `pydantic_settings>=2.0.0` as dependency but not `pyyaml` for config loading
- `docs/11-guides/configuration.md` correctly documents Pydantic Settings with .env approach

**Recommendation:** Update the audit phase documentation (`.kilo/commands/audit/phases/02-audit-config.md`) to reflect the actual configuration architecture (Pydantic Settings with .env), removing outdated Telepost-specific references. The current configuration approach is valid and follows Pydantic v2 best practices. Effort: trivial. Priority: recommended.

> **Validation Note:**
> - **Action:** confirmed
> - **Detail:** This is a legitimate DOC-UPDATE issue. The audit template in `.kilo/commands/audit/phases/02-audit-config.md` references components from a different project (Telepost) and needs to be updated for vkdownloader's actual architecture. The code itself is correct.
> - **See also:** —

---

### CFG-004: Missing validator for download_dir path resolution

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py:53-56 |
| **Classification** | advisory |

**Description:** The `download_dir` field in `Settings` uses `Path.home() / "Downloads" / "vkdownloader"` as a default, but there is no `@field_validator` or `AfterValidator` to ensure the path is properly resolved and validated when set via environment variable. Unlike `ssl_verify`, `download_timeout`, and other fields that have constraints, `download_dir` lacks validation for path traversal attacks or invalid paths at Settings instantiation time. However, `validate_output_path` in `src/vkdownloader/utils/security.py` is called by services before using the path.

**Evidence:**
- `src/vkdownloader/config.py:53-56` shows `download_dir` field without any validators
- `src/vkdownloader/utils/security.py` contains `validate_output_path` function used by services (lines 12-51)
- `src/vkdownloader/services/downloader.py:339` calls `validate_output_path(request.output_file)`
- `src/vkdownloader/cli.py:130` calls `validate_output_path(output, warning=False)`

**Recommendation:** Consider adding a `field_validator` for `download_dir` to validate paths at Settings instantiation time, ensuring invalid paths are caught early. Effort: small. Priority: recommended.

> **Validation Note:**
> - **Action:** confirmed
> - **Detail:** Valid BEST-PRACTICE finding. The deferred validation approach (validate at usage time via `validate_output_path`) is acceptable, but early validation at Settings instantiation would provide better error messages. This is a valid improvement opportunity with positive ROI for maintainability.
> - **See also:** —

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | CFG-003, CFG-004 |
| Reclassified | 2 | CFG-001 (RUNTIME-ERROR→SPEC-DEVIATION), CFG-002 (SPEC-DEVIATION→mandatory) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Cross-Phase Conflicts

**CFG-001 and CLI-001 are duplicate findings** describing the same test failure (`test_settings_creates_with_defaults` failing due to `.env` value overriding default). Both phases correctly identify the same root cause. Fixing either resolves the issue.

### Cross-Phase Dependencies

| Finding | Depends On | Notes |
|---------|------------|-------|
| CFG-001 | — | Standalone test fix |
| CFG-002 | — | Standalone package export fix |
| CFG-003 | — | Documentation template fix |
| CFG-004 | — | Standalone Settings validation improvement |

---

## Rollout Analysis

- CFG-001 and CFG-002 can be fixed independently
- CFG-003 is documentation-only; no code changes required
- CFG-004 is optional improvement that can be deferred
- No circular dependencies detected
- No rollout conflicts between findings