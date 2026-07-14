---
name: 02-config
description: Configuration & Pydantic Models
executor: auditor
status: complete
validated: no
---

# Phase 02 Audit Findings — Configuration & Pydantic Models

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** no

---

## Findings

### CFG-001: Test failure due to .env configuration overriding Settings defaults

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/test_config.py:10-24, src/vkdownloader/config.py:101-106 |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` asserts that `settings.ssl_verify is True`, but this test fails because the `.env` file sets `VKDOWNLOADER_SSL_VERIFY=false`. Pydantic-settings automatically loads `.env` files via `env_file=".env"` in the model_config, causing the test to receive `ssl_verify=False` instead of the expected `True`. This is a test isolation issue where environment configuration leaks into tests.

**Evidence:**
- Test output: `AssertionError: assert False is True` at `tests/test_config.py:20`
- `.env` file line 12: `VKDOWNLOADER_SSL_VERIFY=false`
- Settings class in `src/vkdownloader/config.py:47-50` uses Pydantic BaseSettings with `env_file=".env"` in model_config
- `Settings().model_fields["ssl_verify"].default` returns `True` but `.env` override takes precedence

**Recommendation:** Modify the test to either: (1) create Settings with explicit `ssl_verify=True` to override the `.env` value, or (2) temporarily disable `.env` loading during the test. This ensures test isolation from environment configuration.

---

### CFG-002: Missing exports for CookieSource and DownloadMethod in models/__init__.py

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/__init__.py:4-19 |
| **Classification** | advisory |

**Description:** The `CookieSource` and `DownloadMethod` enums are used directly in `src/vkdownloader/config.py:10` and `src/vkdownloader/cli.py:12`, but they are not exported in the models package `__init__.py`. The `.enums` module defines 6 enums (`QualityEnum`, `StreamFormat`, `LogLevel`, `DownloadStatus`, `DownloadMethod`, `CookieSource`), but only 4 are re-exported (`QualityEnum`, `StreamFormat`, `LogLevel`, `DownloadStatus`). This creates inconsistency and forces consumers to import directly from the submodule rather than using the package public API.

**Evidence:**
- `src/vkdownloader/models/__init__.py:4` imports only 4 enums, missing `CookieSource` and `DownloadMethod`
- `src/vkdownloader/config.py:10` imports via `from vkdownloader.models.enums import CookieSource, DownloadMethod, LogLevel`
- `src/vkdownloader/cli.py:12` imports via `from .models.enums import CookieSource, DownloadMethod, QualityEnum`

**Recommendation:** Add `CookieSource` and `DownloadMethod` to the imports and `__all__` list in `src/vkdownloader/models/__init__.py` to provide a complete public API for the models package. Effort: trivial. Priority: recommended.

---

### CFG-003: Missing config loading mechanism (TelepostConfigReader/PathResolver) referenced in docs

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | docs/11-guides/configuration.md, .kilo/commands/audit/phases/02-audit-config.md |
| **Classification** | advisory |

**Description:** The audit phase documentation references `TelepostConfigReader`, `PathResolver`, `platformdirs`, `init_project()`, and `config_example.yaml` as expected components of the configuration architecture. However, this project (vkdownloader) does not use YAML-based configuration loading - it uses Pydantic Settings with environment variables (`.env` file). There is no `config_reader.py`, `paths.py`, or `init_service.py`. The `.env` file serves as the configuration template, not a YAML file. The documentation and audit template appear to be from a different project (Telepost) and do not match this codebase's architecture.

**Evidence:**
- No `config_reader.py` file exists in the codebase
- No `paths.py` or `PathResolver` class exists
- No `settings/` directory with YAML templates
- Configuration is handled via `src/vkdownloader/config.py` using Pydantic BaseSettings with `.env` env_file
- `pyproject.toml` shows `pydantic_settings>=2.0.0` as dependency but not `pyyaml` for config loading

**Recommendation:** Update the audit phase documentation to reflect the actual configuration architecture (Pydantic Settings with .env), or remove the outdated references to Telepost-specific components. The current configuration approach is valid and follows Pydantic v2 best practices.

---

### CFG-004: Missing validator for download_dir path resolution

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py:53-56 |
| **Classification** | advisory |

**Description:** The `download_dir` field in `Settings` uses `Path.home() / "Downloads" / "vkdownloader"` as a default, but there is no `@field_validator` or `AfterValidator` to ensure the path is properly resolved and validated when set via environment variable. Unlike `ssl_verify`, `download_timeout`, and other fields that have constraints, `download_dir` lacks validation for path traversal attacks or invalid paths. However, `validate_output_path` in `src/vkdownloader/utils/security.py` does provide path validation when used.

**Evidence:**
- `src/vkdownloader/config.py:53-56` shows `download_dir` field without any validators
- `src/vkdownloader/utils/security.py` contains `validate_output_path` function used by services

**Recommendation:** Consider adding a `field_validator` for `download_dir` to validate paths at Settings instantiation time, ensuring invalid paths are caught early. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 2 |

## Mandatory Fixes

- CFG-001: Test failure due to .env configuration overriding Settings defaults

## Advisory Recommendations

- CFG-002: Missing exports for CookieSource and DownloadMethod in models/__init__.py
- CFG-003: Missing config loading mechanism (TelepostConfigReader/PathResolver) referenced in docs
- CFG-004: Missing validator for download_dir path resolution

---