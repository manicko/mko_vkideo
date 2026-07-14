---
name: audit-findings
description: Phase 06 - Data Flow Audit Findings
agent: auditor
alwaysApply: false
---

# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
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
- `src/vkdownloader/cli.py:216`: `max_retries: int = typer.Option(Settings().max_retries, ...)`

**Recommendation:** Use `None` as default and resolve the actual default inside the function body. This follows the same pattern used elsewhere in the CLI where default enum values are handled (see `quality` and `method` options which correctly use class-level defaults without instantiation). The implementation should:

```python
# Before (line 215-220):
# max_retries: int = typer.Option(
#     Settings().max_retries,
#     "--max-retries",
#     "-r",
#     help="Maximum retry attempts for failed segment downloads",
# )

# After:
max_retries: int | None = typer.Option(
    None,
    "--max-retries",
    "-r",
    help="Maximum retry attempts for failed segment downloads",
)
```

Then inside `_run_batch_with_progress()` or at the start of the function body, resolve the default:

```python
settings = Settings(
    cookie_source=cookie_source,
    max_retries=max_retries if max_retries is not None else Settings().max_retries,
    ssl_verify=ssl_verify,
)
```

This pattern avoids the B008 lint violation and ensures the default is evaluated at runtime, not import time.

> **Validation Note:**
> - **Action:** validated with concrete implementation
> - **Detail:** The current pattern creates a Settings instance at module import time. The fix uses None sentinel with runtime resolution, consistent with Pydantic best practices and avoiding the B008 lint rule violation.
> - **See also:** —

---

### DF-005: Unused DTO Models (DownloadRequest and DownloadResult)

| Field | Value |
|-------|-------|
| **ID** | DF-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | src/vkdownloader/models/dtos.py, docs/01-tools/vkdownloader-overview.md |
| **Classification** | advisory |

**Description:** The `DownloadRequest` and `DownloadResult` DTOs are defined in `models/dtos.py` and exported in `__init__.py` but are never actually instantiated or used anywhere in the codebase. The codebase uses `HLSDownloadRequest` extensively but these other DTOs appear to be missing integration. Per project rule: "when a component appears in documentation/spec but is unused, classify as SPEC-DEVIATION (missing integration, not dead code)."

**Evidence:**
- `src/vkdownloader/models/dtos.py:16-23`: `DownloadRequest` class definition (no instantiations found)
- `src/vkdownloader/models/dtos.py:50-58`: `DownloadResult` class definition (no instantiations found)
- `docs/01-tools/vkdownloader-overview.md:54-56`: Both models documented as public API

**Recommendation:** Implement integration in the download flow to use these DTOs. The recommended approach is to integrate them into the core download orchestration:

1. **For DownloadRequest**: Use it to wrap the initial download request in `perform_download()` function. Replace the current multi-parameter function signature with a single DTO parameter that consolidates `url`, `quality`, and `output_file`:

```python
# In services/downloader.py, refactor perform_download signature:
async def perform_download(request: DownloadRequest, ...) -> Path | None:
    # Access via request.url, request.quality, request.output_path
```

2. **For DownloadResult**: Use it to wrap the return value from download functions. Modify `perform_download()` and related functions to return `DownloadResult` instead of plain `Path | None`:

```python
# Return structured result:
return DownloadResult(
    video_id=video.id,
    output_file=str(output_file),
    file_size=output_file.stat().st_size if output_file.exists() else 0,
    duration=await get_video_duration(m3u8_url),
    streams_used=[stream],
    success=True,
)
```

3. **Update exports**: Keep `DownloadRequest` and `DownloadResult` in `models/__init__.py` as they become part of the public API.

4. **Add tests**: Add `test_dtos.py` with validation tests for:
   - `DownloadRequest.url` HttpUrl validation
   - `DownloadRequest.quality` default value (QualityEnum.BEST)
   - `DownloadResult.success` boolean flag behavior

Alternatively, if these DTOs are not intended for implementation, remove them from both code (`models/dtos.py` and `models/__init__.py`) and documentation (`vkdownloader-overview.md`).

> **Validation Note:**
> - **Action:** validated with concrete implementation option
> - **Detail:** Models are part of documented public API. Two paths forward: (A) implement integration in download flow, or (B) remove from documentation and code. Implementation path is recommended to align documentation with code.
> - **See also:** —

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 2 |

## Mandatory Fixes

- DF-001: Config test fails due to environment file overriding defaults

## Advisory Recommendations

- DF-002: Batch command default value evaluates Settings at import time (with concrete implementation)
- DF-004: Inconsistent Settings instantiation pattern
- DF-005: DownloadRequest and DownloadResult models documented but not implemented - either implement usage or remove from documentation

## Doc Updates Needed

- DF-005: DownloadRequest and DownloadResult models documented but not implemented - either implement usage or remove from documentation