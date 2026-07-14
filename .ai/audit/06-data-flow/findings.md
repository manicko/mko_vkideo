---
name: audit-findings
description: Phase 06 - Data Flow Audit Findings
agent: auditor
alwaysApply: false
---

# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** /.ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

- **Import Full Pipeline:** All modules import successfully
- **Linter (ruff check):** All checks passed (exit code 0)
- **Type Checker (mypy):** Success - no issues found in 21 source files (exit code 0)
- **Test Suite (pytest):** 1 failed, 200 passed, 5 warnings (exit code 1)

---

## Findings

### DF-001: Config Test Fails Due to Environment File Overriding Defaults

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_config.py |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` fails because it asserts `ssl_verify is True` but the loaded `.env` file sets `VKDOWNLOADER_SSL_VERIFY=false`, overriding the default value. The Settings class loads from `.env` by default via `env_file=".env"` in model_config, causing environment configuration to interfere with test expectations.

**Evidence:**
- Test assertion at `tests/test_config.py:20`: `assert settings.ssl_verify is True`
- `.env` file contains: `VKDOWNLOADER_SSL_VERIFY=false`
- Settings.model_config at `src/vkdownloader/config.py:101-106` includes `"env_file": ".env"`

**Recommendation:** The test should either:
1. Mock or remove the `.env` file during the test, or
2. Use `Settings(_env_file=None)` to prevent loading the environment file, or
3. Assert against the actual loaded value (`False`) to match the environment file

---

### DF-002: Batch Command Default Value Evaluates Settings at Import Time

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** The `batch_download` command uses `Settings().max_retries` as the default value for `max_retries` option (line 216). This evaluates at module import time, meaning any environment configuration or `.env` values are captured before the user can provide CLI arguments. It also creates unnecessary Settings instances.

**Evidence:**
- `src/vkdownloader/cli.py:215-216`: `max_retries: int = typer.Option(Settings().max_retries, ...)`
- This pattern is flagged by linter as `# noqa: B008` (function call in argument defaults)

**Recommendation:** Use a sentinel value or `None` as default and resolve the actual default inside the function. For example:
```python
max_retries: int | None = typer.Option(None, "--max-retries", "-r")
# Then inside function: actual_retries = max_retries if max_retries is not None else Settings().max_retries
```

---

### DF-003: Unused Settings Fields Not Propagated in Download Flow

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py, src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Several Settings fields are not propagated through the download flow:
- `timezone` and `locale` are only used in BrowserManager but not passed to VKVideoExtractor or other services
- `throttled_rate` is used in yt-dlp but `HttpClient.download_file` doesn't utilize settings for timeout or retry logic

**Evidence:**
- `timezone` and `locale` in Settings (config.py) are used only in BrowserManager.create_stealth_page (browser.py:66-67)
- `throttled_rate` is in Settings but the gap between config defaults and actual usage is not verified

---

### DF-004: Inconsistent Settings Instantiation Pattern

| Field | Value |
|-------|-------|
| **ID** | DF-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** The CLI creates Settings instances in multiple places with inconsistent field coverage:
- `download()` command (line 115): Creates Settings with `cookie_source` and `ssl_verify` only
- `batch_download()` command (line 249): Creates Settings with `cookie_source`, `max_retries`, `ssl_verify` only

The batch command receives `user_agent`, `accept_language`, `timezone`, `locale` from environment but doesn't pass them explicitly, while the download command doesn't either. Both rely on Settings defaults.

**Evidence:**
- `src/vkdownloader/cli.py:115`: `Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)`
- `src/vkdownloader/cli.py:249`: `Settings(cookie_source=cookie_source, max_retries=max_retries, ssl_verify=ssl_verify)`

**Recommendation:** Consider creating Settings with all CLI-provided options explicitly, or create a single Settings instance at the command entry point and pass it through.

---

### DF-005: Unused DTO Models (DownloadRequest and DownloadResult)

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/dtos.py |
| **Classification** | advisory |

**Description:** The `DownloadRequest` and `DownloadResult` DTOs are defined in `models/dtos.py` and exported in `__init__.py` but are never actually instantiated or used anywhere in the codebase. The codebase uses `HLSDownloadRequest` extensively but these other DTOs appear to be dead code.

**Evidence:**
- `src/vkdownloader/models/dtos.py:16-23`: `DownloadRequest` class definition (no instantiations found)
- `src/vkdownloader/models/dtos.py:50-58`: `DownloadResult` class definition (no instantiations found)
- `src/vkdownloader/models/__init__.py:3,8-9`: Both exported in `__all__`
- No imports or usages found outside of definition and model exports

**Recommendation:** Either remove unused DTOs or document their intended future use. Per project rules on dead code, investigate purpose before removal.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 3 |

## Mandatory Fixes

- DF-001: Config test fails due to environment file overriding defaults

## Advisory Recommendations

- DF-002: Batch command default value evaluates Settings at import time
- DF-003: Unused Settings fields not propagated in download flow
- DF-004: Inconsistent Settings instantiation pattern
- DF-005: Unused DTO models (DownloadRequest and DownloadResult)

## Doc Updates Needed

- DF-005: Consider documenting future use of DownloadRequest or removing it