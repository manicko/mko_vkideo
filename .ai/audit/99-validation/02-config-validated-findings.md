---
name: 02-config
description: Phase 02 Audit Findings — Configuration & Pydantic Models (Validated)
agent: validator
alwaysApply: false
---

# Phase 02 Audit Findings — Configuration & Pydantic Models (Validated)

**Executor:** validator  
**Source:** `.ai/audit/02-config/findings.md`  
**Base:** Phase 02 Audit  
**Status:** complete  
**Validated:** yes

---

## Findings

### CFG-001: download_method field uses str instead of StrEnum

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** The `download_method` field in the `Settings` model is defined as `str` type but the project has a `DownloadMethod` StrEnum in `models/enums.py` with values `YTDLP="yt-dlp"`, `FFMPEG="ffmpeg"`, and `AUTO="auto"` that matches the expected values. The enum exists but is not used, and the field accepts any string value including invalid ones without validation.

**Evidence:**
- `src/vkdownloader/config.py:89-92` - `download_method: str = Field(default="auto", ...)`
- `src/vkdownloader/models/enums.py:35-40` - `DownloadMethod` enum exists with matching values
- No usage of `download_method` field found in any service code (`downloader.py`, `extractor.py`, `quality.py`, `cli.py`)
- Runtime test: `Settings(download_method='invalid_method')` accepts invalid value without validation error

**Recommendation:** Change `download_method` field type from `str` to `DownloadMethod` to enforce valid values at the Pydantic validation level. This provides type safety and prevents configuration typos. Effort: small. Priority: recommended.

---

### CFG-002: Multiple unused config fields in Settings model

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** Several fields defined in the `Settings` model are never consumed by any service code in production. However, these fields are referenced in documentation and test fixtures, indicating planned features without complete integration.

**Evidence:**
- `src/vkdownloader/config.py:17-24` - `vk_api_url` and `vk_api_version` defined but not used in any service
- `src/vkdownloader/config.py:43-52` - `request_delay_min` and `request_delay_max` defined but not used in production code
- `src/vkdownloader/config.py:59-64` - `concurrency` defined but not used; `max_concurrent_downloads` is used in `cli.py:138`
- `src/vkdownloader/config.py:83-88` - `timeout_seconds` not used in production services
- `tests/conftest.py:14-16` - Test fixtures use `timeout_seconds` and `concurrency` fields
- `docs/01-tools/api-reference.md:330-332` - Documentation references these fields as settings
- `.ai/plans/02-implementation-details.md:129-132` - Implementation plans reference `request_delay_min`, `request_delay_max`, `concurrency`

> **Validation Note:**
> - **Action:** Reclassified
> - **Original Type:** SPEC-DEVIATION (dead code removal)
> - **New Type:** SPEC-DEVIATION (missing integration)
> - **Detail:** These are NOT dead code. The fields are documented and used in tests. Per validation rules: "If the spec, models, or config reference the component → reject the 'dead code' label and reclassify as SPEC-DEVIATION (missing integration, not dead code)." The finding author incorrectly labeled these as dead code, but the underlying issue (missing integration) is valid.

**Recommendation:** Integrate these fields into the service layer if the planned features are to be implemented, or remove them from both code and documentation to maintain consistency. Effort: variable. Priority: context-dependent.

---

### CFG-003: Settings model uses extra="ignore" instead of extra="forbid"

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** The Settings model's `model_config` sets `extra="ignore"` which silently drops unknown configuration keys instead of rejecting them. This can lead to typos in config files going unnoticed.

**Evidence:** `src/vkdownloader/config.py:104-108` shows `"extra": "ignore"` in model_config

**Recommendation:** Change to `extra="forbid"` to catch configuration typos and undocumented fields. This follows the audit checklist requirement that "root settings model rejects unknown keys to catch typos in config". Effort: trivial. Priority: recommended.

---

### CFG-004: Missing type annotations in config-related functions

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | mandatory |

**Description:** Multiple functions lack proper type annotations, violating the project's strict mypy configuration (strict = true, disallow_untyped_defs = true). The project rule #9 explicitly requires "Type Safety Everywhere" and rule #12 forbids `any` completely.

**Evidence:** mypy output shows 8 errors across 3 files:
- `downloader.py:71` - Function missing type annotation for `extractor` parameter
- `downloader.py:148` - `_fetch_playlist_with_retry` missing type annotation on `extractor`
- `downloader.py:151` - `headers: dict` missing type arguments (should be `dict[str, str]`)
- `downloader.py:192` - `headers: dict` missing type arguments (should be `dict[str, str]`)
- `downloader.py:301` - `json.load()` returns `Any`, function declared to return `int` without proper cast
- `browser.py:29` - `create_stealth_context` returns `Coroutine[Any, Any, BrowserContext]` but declared as `BrowserContext`
- `extractor.py:168` - `list[Cookie]` passed to `_format_cookies_for_ffmpeg` which expects `list[dict]`
- `extractor.py:186` - `list[dict]` missing explicit type arguments or proper Cookie type

**Recommendation:** 
- Add `VKVideoExtractor | None` type for extractor parameters
- Use `dict[str, str]` for headers types
- Add `async` keyword to `create_stealth_context` or use `typing.cast()` for proper handling
- Use `list[Cookie]` type from Playwright's async_api for cookie parameters (requires importing Cookie type)
- Use explicit cast or validation for `json.load()` return type
Effort: small. Priority: mandatory (mypy strict config violation).

---

### CFG-005: create_stealth_context function has incorrect return type for async Playwright API

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description:** The `create_stealth_context` function (line 13) is declared to return `BrowserContext` but calls `playwright.chromium.launch_persistent_context()`. In Playwright's async API, this method returns a coroutine. The function should either be async with proper type hints, or use sync API methods.

**Evidence:** `browser.py:17-37` shows synchronous function returning `BrowserContext` but mypy reports "Incompatible return value type (got Coroutine[Any, Any, BrowserContext], expected BrowserContext)". Tests pass because they mock the coroutine with MagicMock which doesn't enforce async behavior.

**Recommendation:** Add `async` keyword to function and wrap in `typing.coroutine` or adjust return type. Effort: small. Priority: recommended.

---

### CFG-006: ~~Missing init service and path resolution infrastructure~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/` (missing) |
| **Classification** | advisory |

~~Description: The audit checklist references `config_reader.py`, `PathResolver`, `init_service.py`, and `settings/config_example.yaml` which are expected patterns for configuration management. These components do not exist in the codebase, but the documentation and audit phases expect them. The project uses `pydantic_settings.BaseSettings` directly without a config reader layer, and has no user config directory separation.~~

~~Evidence:~~
- ~~No `config_reader.py` found in `src/vkdownloader/`~~
- ~~No `paths.py` or `PathResolver` class found~~
- ~~No `init_service.py` found~~
- ~~No `settings/` directory with config templates~~
- ~~Audit phase `02-audit-config.md` references these as expected components (lines 28, 92-93, 103-108, 114-118)~~

~~Recommendation: Consider adopting the expected config architecture pattern with:
- `paths.py` using `platformdirs` to define `USER_DIR` and `APP_PATHS`
- `config_reader.py` to load and validate YAML config files
- `settings/` package directory with `config_example.yaml` template
- `init_service.py` to copy templates to user directory on first run
Effort: large (architectural change). Priority: recommended if configuration complexity grows.~~

> **Rejection reason:** This finding identifies a mismatch between a generic audit checklist and the project's actual architecture. The project uses `pydantic_settings.BaseSettings` directly without the patterns mentioned (`config_reader.py`, `PathResolver`, `init_service.py`, `settings/`). These patterns are NOT project requirements - they were carried over from a template checklist for a different project (mko-telebot). The current architecture is simpler and valid for this project's scope. The audit checklist, not the implementation, is incorrect.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 3 |
| LOW | 0 |

## Mandatory Fixes

- CFG-003: Change `extra="ignore"` to `extra="forbid"` in Settings
- CFG-004: Add missing type annotations (mypy strict mode violations)

## Advisory Recommendations

- CFG-001: Change `download_method` to use `DownloadMethod` StrEnum
- CFG-002: Integrate or remove unused config fields consistently across code and docs  
- CFG-005: Fix create_stealth_context async return type in browser.py

---

## Runtime Verification Results

### Linter Output (ruff check)

Found 6 errors in 3 files:
- `src\vkdownloader\services\downloader.py:3:1` - I001 Import block is un-sorted
- `src\vkdownloader\services\downloader.py:319:42` - W292 No newline at end of file
- `src\vkdownloader\services\extractor.py:5:20` - F401 `typing.Any` imported but unused
- `src\vkdownloader\services\extractor.py:192:13` - F841 Local variable `domain` is assigned but never used
- `src\vkdownloader\services\extractor.py:281:23` - W292 No newline at end of file
- `src\vkdownloader\services\quality.py:77:25` - W292 No newline at end of file

### Type Checker Output (mypy)

Found 8 errors in 3 files:
- `src\vkdownloader\services\downloader.py:71` - no-untyped-def: Function missing type annotation
- `src\vkdownloader\services\downloader.py:148` - no-untyped-def: Function missing type annotation
- `src\vkdownloader\services\downloader.py:151` - type-arg: Missing type arguments for generic type "dict"
- `src\vkdownloader\services\downloader.py:192` - type-arg: Missing type arguments for generic type "dict"
- `src\vkdownloader\services\downloader.py:301` - no-any-return: Returning Any from function declared to return "int"
- `src\vkdownloader\infrastructure\browser.py:29` - return-value: Incompatible return value type (got "Coroutine[Any, Any, BrowserContext]", expected "BrowserContext")
- `src\vkdownloader\services\extractor.py:168` - arg-type: Argument has incompatible type "list[Cookie]"; expected "list[dict[Any, Any]]"
- `src\vkdownloader\services\extractor.py:186` - type-arg: Missing type arguments for generic type "dict"

---

## Cross-Phase Conflicts

None detected. All findings are consistent with CLI phase findings (CFG-004 and CLI-005 both address type annotation issues in the same files).

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | CFG-001, CFG-003, CFG-004, CFG-005 |
| Reclassified | 1 | CFG-002 (dead code → missing integration) |
| Merged | 0 | — |
| Rejected | 1 | CFG-006 (checklist mismatch, not actual problem) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| CFG-006 | Missing init service and path resolution infrastructure | The audit checklist template references patterns (`config_reader.py`, `PathResolver`, `init_service.py`, `settings/`) that are NOT project requirements. These patterns were inherited from a different project template. The current architecture using `BaseSettings` directly is valid and simpler for this project's scope. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | No findings merged. Each issue has distinct root cause. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CFG-002 | SPEC-DEVIATION (dead code removal) | SPEC-DEVIATION (missing integration) | Fields are documented and used in tests. Per validation rules, this is "missing integration, not dead code" — the spec and models reference these components, indicating planned but incomplete implementation. |

---

## Warnings

- **Type Safety Risk:** mypy strict mode failures indicate the code lacks type annotations required by project rule #9.
- **Configuration Drift:** `timeout_seconds` is defined in Settings but `download_timeout` is used in `http_client.py:41`. Documentation references `timeout_seconds`, creating user confusion.
- **Cookie Type Inconsistency:** The `_format_cookies_for_ffmpeg` method uses `list[dict]` but receives `list[Cookie]` from Playwright's async API, requiring either type widening or proper typing.
- **Documentation Misalignment (CFG-002):** The api-reference.md documents `timeout_seconds` and `request_delay_min/max` as settings, but these fields are not integrated into production services. This creates inconsistency between docs and behavior.