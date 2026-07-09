---
name: 02-config
description: Phase 02 Audit Findings — Configuration & Pydantic Models
agent: auditor
alwaysApply: false
---

# Phase 02 Audit Findings — Configuration & Pydantic Models

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

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

**Description:** The `download_method` field in the `Settings` model is defined as `str` type but the project has a `DownloadMethod` StrEnum in `models/enums.py` with values `YTDLP`, `FFMPEG`, and `AUTO` that matches the expected values. The enum exists but is not used, and the field accepts any string value including invalid ones without validation.

**Evidence:**
- `src/vkdownloader/config.py:89-92` - `download_method: str = Field(default="auto", ...)`
- `src/vkdownloader/models/enums.py:35-40` - `DownloadMethod` enum exists with `YTDLP = "yt-dlp"`, `FFMPEG = "ffmpeg"`, `AUTO = "auto"`
- `src/vkdownloader/services/extractor.py` - no usage of `download_method` field in extractor code
- Runtime test: `Settings(download_method='invalid_method')` accepts invalid value without validation error

**Recommendation:** Change `download_method` field type from `str` to `DownloadMethod` to enforce valid values at the Pydantic validation level. This provides type safety and prevents configuration typos. Effort: small. Priority: recommended.

### CFG-002: Multiple unused config fields in Settings model

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/services/*` |
| **Classification** | advisory |

**Description:** Several fields defined in the `Settings` model are never consumed by any service code, making them dead code that adds confusion for users and maintenance burden.

**Evidence:**
- `request_delay_min` (line 43-47) - defined but never referenced in any source file
- `request_delay_max` (line 48-52) - defined but never referenced in any source file  
- `vk_api_url` (line 17-20) - defined but never used (VK API not implemented in this tool)
- `vk_api_version` (line 21-24) - defined but never used
- `timeout_seconds` (line 83-88) - defined but only `download_timeout` is used in `http_client.py:41`
- `concurrency` (line 59-64) - defined but never referenced; `max_concurrent_downloads` is used instead in `cli.py:138`

**Recommendation:** Remove unused fields (`request_delay_min`, `request_delay_max`, `vk_api_url`, `vk_api_version`, `timeout_seconds`, `concurrency`) from the Settings model. Alternatively, if these represent planned features, add TODO comments documenting their intended future use. Effort: trivial. Priority: recommended.

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

### CFG-004: Missing type annotations in config-related functions

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** Multiple functions lack proper type annotations, violating the project's strict mypy configuration. The `download_hls_with_resume` function (line 71) has untyped parameter `extractor`, `_fetch_playlist_with_retry` (line 148) has untyped `extractor` parameter and bare `dict` types, `_load_downloaded_count` (line 296) returns `Any` from `json.load()`, and `_format_cookies_for_ffmpeg` (line 186) has incorrect type `list[dict]` when actual Playwright `Cookie` type is `list[Cookie]`.

**Evidence:** mypy output shows 8 errors across 2 files:
- `downloader.py:71` - no-untyped-def: Parameter `extractor` missing type annotation (typed as `None`)
- `downloader.py:148` - no-untyped-def: `_fetch_playlist_with_retry` missing annotation on `extractor`
- `downloader.py:151` - type-arg: `headers: dict` missing type arguments (should be `dict[str, str]`)
- `downloader.py:192` - type-arg: `headers: dict` missing type arguments (should be `dict[str, str]`)
- `downloader.py:296-301` - no-any-return: `json.load()` returns `Any`, function declared to return `int`
- `extractor.py:168` - arg-type: `list[Cookie]` passed to `_format_cookies_for_ffmpeg` which expects `list[dict[Any, Any]]`
- `extractor.py:186` - type-arg: `list[dict]` should be explicit about key/value types or use proper Cookie type

**Recommendation:** Add type annotations to all function parameters. Use `dict[str, Any]` instead of bare `dict`. Consider using `typing.cast()` or explicit validation for JSON return types. Effort: small. Priority: recommended.

### CFG-005: create_stealth_context function has incorrect return type for async Playwright API

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description:** The `create_stealth_context` function (line 13) is declared to return `BrowserContext` but calls `playwright.chromium.launch_persistent_context()`. In Playwright's async API, this method returns a coroutine. The function should either be async with proper type hints, or use sync API methods.

**Evidence:** `browser.py:17` returns `BrowserContext` but mypy reports "Incompatible return value type (got Coroutine[Any, Any, BrowserContext], expected BrowserContext)". Tests pass because they mock the method.

**Recommendation:** Add `async` keyword to function and return `BrowserContext` (the awaited result). Or keep function synchronous but document that it must be called in async context. Effort: small. Priority: recommended.

### CFG-006: Missing init service and path resolution infrastructure

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/` (missing) |
| **Classification** | advisory |

**Description:** The audit checklist references `config_reader.py`, `PathResolver`, `init_service.py`, and `settings/config_example.yaml` which are expected patterns for configuration management. These components do not exist in the codebase, but the documentation and audit phases expect them. The project uses `pydantic_settings.BaseSettings` directly without a config reader layer, and has no user config directory separation.

**Evidence:**
- No `config_reader.py` found in `src/vkdownloader/`
- No `paths.py` or `PathResolver` class found
- No `init_service.py` found
- No `settings/` directory with config templates
- Audit phase `02-audit-config.md` references these as expected components (lines 28, 92-93, 103-108, 114-118)

**Recommendation:** Consider adopting the expected config architecture pattern with:
- `paths.py` using `platformdirs` to define `USER_DIR` and `APP_PATHS`
- `config_reader.py` to load and validate YAML config files
- `settings/` package directory with `config_example.yaml` template
- `init_service.py` to copy templates to user directory on first run
Effort: large (architectural change). Priority: recommended if configuration complexity grows.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 0 |

## Mandatory Fixes

None

## Advisory Recommendations

- CFG-001: Change `download_method` to use `DownloadMethod` StrEnum
- CFG-002: Remove or document unused config fields
- CFG-003: Change `extra="ignore"` to `extra="forbid"` in Settings
- CFG-004: Add missing type annotations in downloader.py
- CFG-005: Fix create_stealth_context async return type in browser.py
- CFG-006: Consider implementing standard config architecture with PathResolver and config_reader

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

## Template Field Reference

### Mandatory Fields Per Finding

| Field | Type | Values/Format |
|-------|------|---------------|
| `id` | string | Unique identifier within phase (e.g., `CFG-001`, `CFG-002`) |
| `title` | string | Human-readable one-line summary |
| `type` | enum | `SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, `RUNTIME-ERROR` |
| `severity` | enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `description` | string | Detailed problem description with context |
| `evidence` | string | File paths, line references, log excerpts, code snippets |
| `affected_modules` | list | Affected module paths |
| `recommendation` | string | Concrete fix direction |
| `classification` | enum | `mandatory` or `advisory` |