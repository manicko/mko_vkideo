---
name: audit-findings
description: Phase 06 - Data Flow Audit Findings (Validated)
agent: validator
alwaysApply: false
---

# Phase 06 Audit Findings — End-to-End Data Flow (Validated)

**Executor:** auditor → validator
**Template:** /.ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes

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
- `.env` file contains: `VKDOWNLOADER_SSL_VERIFY=false` (line 12)
- Settings.model_config at `src/vkdownloader/config.py:101-106` includes `"env_file": ".env"`
- **Verified:** Test fails with `AssertionError: assert False is True` when run

**Recommendation:** The test should either:
1. Mock or remove the `.env` file during the test, or
2. Use `Settings(_env_file=None)` to prevent loading the environment file, or
3. Assert against the actual loaded value (`False`) to match the environment file

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Finding is technically correct and verified. The test fails because `.env` overrides defaults. This is a SPEC-DEVIATION requiring test fix.
> - **See also:** —

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
- `src/vkdownloader/cli.py:216`: `max_retries: int = typer.Option(Settings().max_retries, ...)`
- **Verified:** Code pattern confirmed at line 216 where the pattern exists without `# noqa: B008`

**Recommendation:** Use a sentinel value or `None` as default and resolve the actual default inside the function. For example:
```python
max_retries: int | None = typer.Option(None, "--max-retries", "-r")
# Then inside function: actual_retries = max_retries if max_retries is not None else Settings().max_retries
```

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Finding is technically correct. Using `Settings().max_retries` in function signature default evaluates at import time and is flagged by the B008 lint rule. The pattern exists and is a valid best-practice improvement.
> - **See also:** DF-004 (inconsistent Settings instantiation)

---

### DF-003: Unused Settings Fields Not Propagated in Download Flow

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py, src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Several Settings fields are not propagated through the download flow. The finding claims `timezone` and `locale` are only used in BrowserManager but not passed to VKVideoExtractor or other services, and that `HttpClient.download_file` doesn't utilize settings for timeout or retry logic.

**Evidence:**
- `timezone` and `locale` in Settings (config.py:27-34) are used in BrowserManager.create_stealth_page (browser.py:66-67)
- `throttled_rate` is in Settings and IS used in downloader.py:985 (passed to yt-dlp options as `"throttledratelimit"`)
- `http_chunk_size` IS used in downloader.py:986 (passed to yt-dlp options)
- `download_timeout` IS used in http_client.py:43 (used for `ClientTimeout`)
- `max_retries` IS used in http_client.py:91 (retry loop)

**Recommendation:** The finding is partially accurate. `timezone` and `locale` are correctly scoped to browser stealth configuration. The claim about `throttled_rate` and `http_chunk_size` is incorrect - they ARE used in yt-dlp options. The claim about `HttpClient.download_file` not using timeout/retry is incorrect - `download_timeout` and `max_retries` ARE used.

> **Validation Note:**
> - **Action:** rejected
> - **Detail:** Evidence is factually incorrect. `throttled_rate` and `http_chunk_size` ARE propagated (downloader.py:985-986). `HttpClient.download_file` DOES use `download_timeout` (http_client.py:43) and `max_retries` (http_client.py:91). The finding misrepresents the actual code behavior.
> - **See also:** —

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

Both commands receive additional CLI options (like `user_agent`, `accept_language`) but don't pass them, relying on Settings defaults.

**Evidence:**
- `src/vkdownloader/cli.py:115`: `Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)`
- `src/vkdownloader/cli.py:249`: `Settings(cookie_source=cookie_source, max_retries=max_retries, ssl_verify=ssl_verify)`
- **Verified:** Code confirmed. `user_agent`, `accept_language`, `timezone`, `locale` are not CLI options, they use Settings defaults.

**Recommendation:** Consider creating Settings with all CLI-provided options explicitly, or create a single Settings instance at the command entry point and pass it through.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Finding is accurate. The Settings instantiation is inconsistent between commands. However, this is by design: `user_agent`, `accept_language`, `timezone`, `locale` are NOT exposed as CLI options (lines 79-102 in download command only expose `quality`, `output`, `method`, `cookie_source`, `ssl_verify`). The inconsistency between commands is still valid to note but represents a code style issue rather than functional bug.
> - **See also:** DF-002

---

### DF-005: Unused DTO Models (DownloadRequest and DownloadResult)

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | src/vkdownloader/models/dtos.py |
| **Classification** | advisory |

**Description:** The `DownloadRequest` and `DownloadResult` DTOs are defined in `models/dtos.py` and exported in `__init__.py` but are never actually instantiated or used anywhere in the codebase. The codebase uses `HLSDownloadRequest` extensively but these other DTOs appear to be dead code.

**Evidence:**
- `src/vkdownloader/models/dtos.py:16-23`: `DownloadRequest` class definition (no instantiations found)
- `src/vkdownloader/models/dtos.py:50-58`: `DownloadResult` class definition (no instantiations found)
- `src/vkdownloader/models/__init__.py:3,8-9`: Both exported in `__all__`
- No imports or usages found outside of definition and model exports
- **Verified:** Search confirms no `= DownloadRequest(` or `= DownloadResult(` patterns in codebase

**Recommendation:** Either remove unused DTOs or document their intended future use.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Per project rules on "dead code" findings, the spec/documentation reference check must be performed first. `DownloadRequest` and `DownloadResult` ARE documented in `docs/01-tools/vkdownloader-overview.md` lines 54-56 as part of the public model API. This is not dead code but **missing integration** - the models exist in documentation but are not implemented in the codebase. Reclassified as DOC-UPDATE (documentation is ahead of implementation, not code behind docs).
> - **See also:** —

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
- DF-004: Inconsistent Settings instantiation pattern

## Doc Updates Needed

- DF-005: DownloadRequest and DownloadResult models documented but not implemented - either implement usage or remove from documentation

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | DF-001, DF-004 |
| Reclassified | 1 | DF-005 (SPEC-DEVIATION → DOC-UPDATE) |
| Rejected | 1 | DF-003 |
| Rejected (other) | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| DF-003 | Unused Settings fields not propagated in download flow | Evidence is factually incorrect: `throttled_rate` and `http_chunk_size` ARE used in downloader.py:985-986 for yt-dlp options; `download_timeout` and `max_retries` ARE used in http_client.py. The finding misrepresents the actual code behavior. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | No merge candidates identified |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|----------|
| DF-005 | SPEC-DEVIATION | DOC-UPDATE | Models are documented in vkdownloader-overview.md as public API. Per project rules, this represents documentation ahead of implementation (missing integration), not dead code. |

### Rollout Safety Analysis

No rollout safety issues detected for validated findings. The rejected finding (DF-003) would have represented no safety concerns as it was based on incorrect evidence about settings propagation that already works correctly.