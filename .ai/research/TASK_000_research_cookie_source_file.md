# Research Report: Impact of Rejecting CookieSource.FILE at Config Boundary

**Task:** TASK_000_research_cookie_source_file  
**Date:** 2026-07-20  
**Status:** Complete  

---

## 1. Consumers / Entry Points for cookie_source

### Production Code Consumers

| Entry Point | File | Line | Behavior |
|-------------|------|------|----------|
| CLI `download` command | `src/vkdownloader/cli.py` | 330 | Creates `Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)` |
| CLI `batch_download` command | `src/vkdownloader/cli.py` | 462 | Creates `Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)` |
| Environment variable | `src/vkdownloader/config.py` | 117-121 | `VKDOWNLOADER_COOKIE_SOURCE` env var loaded via pydantic-settings |
| Programmatic API | Multiple modules | — | Create `Settings()` with keyword args, including `Settings(cookie_source=CookieSource.FILE)` |

### Service-Level Usage

| Module | Line | Condition | Behavior |
|--------|------|-----------|----------|
| `downloader.py:_resolve_cookies` | 631-655 | `cookie_source == CookieSource.BROWSER` | Calls `extract_streams_with_cookies()`; FILE mode skipped (falls through to return None) |
| `segment_downloader.py:_refresh_token` | 381-387 | `cookie_source != CookieSource.BROWSER` | Logs warning and returns None; FILE mode silently skips |
| `extractor.py:extract_streams_with_cookies` | 123-126 | `cookie_source == CookieSource.FILE` | Raises `NotImplementedError` (never reached in primary flow) |

---

## 2. Current Tests Passing cookie_source="file" or "FILE"

| Test File | Test Function | Line Range | Current Expectation |
|-----------|---------------|------------|---------------------|
| `tests/test_config.py` | `test_cookie_source_validation` | 77-89 | **Accepts** `CookieSource.FILE`; asserts it's stored successfully |
| `tests/test_extractor.py` | `test_extract_streams_with_cookies_file_mode_raises_not_implemented` | 258-267 | Tests `NotImplementedError` for FILE mode (tests the late-error path) |

### Tests That Will Break

1. **`test_cookie_source_validation` (test_config.py:77-89)** - Will fail because `Settings(cookie_source=CookieSource.FILE)` will now raise `ValidationError`
2. **`test_extract_streams_with_cookies_file_mode_raises_not_implemented` (test_extractor.py:258-267)** - Will need adjustment; the error will now occur at Settings construction, not during extraction

---

## 3. CookieSource.FILE Retention Requirement

**CONFIRMED:** The `CookieSource.FILE` enum member **must be retained** for API compatibility.

- Multiple audit findings explicitly state: "Do NOT remove `CookieSource.FILE` enum member - this is intentional for future use and API compatibility"
- TASK_001 acceptance criteria: "CookieSource.FILE enum member still exists (importable)"
- Removal would be a breaking change for any downstream consumers importing `CookieSource.FILE`

---

## 4. Impact Assessment

### Breaking vs Non-Breaking Analysis

| Scenario | Current Behavior | Post-Change Behavior | Impact |
|----------|-----------------|-------------------|--------|
| CLI: `--cookie-source file` | Silently behaves like `none` | Raises `ValidationError` at startup | **Breaking** (user-facing) |
| Env: `VKDOWNLOADER_COOKIE_SOURCE=file` | Silently behaves like `none` | Raises `ValidationError` at startup | **Breaking** (user-facing) |
| API: `Settings(cookie_source=CookieSource.FILE)` | Accepted, no error until extraction | Raises `ValidationError` at construction | **Breaking** (API consumer) |
| API: `Settings(cookie_source="file")` | Accepted, no error until extraction | Raises `ValidationError` at construction | **Breaking** (API consumer) |
| API: `Settings(cookie_source=CookieSource.BROWSER)` | Works as expected | Works as expected | Non-breaking |
| API: `Settings(cookie_source=CookieSource.NONE)` | Works as expected | Works as expected | Non-breaking |

### Batch/CI Invocation Impact

No evidence of batch/CI invocations relying on `cookie_source=FILE` no-op behavior. The silent no-op only occurred in the `extract_streams_with_cookies` code path, which is not called by the primary `download`/`batch` CLI flow.

---

## 5. Error Message and Exception Type Compatibility

### Current Error Handling in CLI

- `cli.py` handles `ValueError` specifically (line 387-392) for invalid URLs
- CLI handles `QualityNotAvailableError`, `VideoNotFoundError`, `VKDownloadError` explicitly
- All other exceptions fall through to the generic `except Exception` block (line 409-412)

### Validator Error Analysis

- `field_validator` raising `ValueError` is **automatically wrapped** by Pydantic into `ValidationError`
- Pydantic `ValidationError` is a subclass of `ValueError` (via `Exception`)
- CLI does NOT catch `ValidationError` explicitly, so it would fall to the generic handler

**Recommended Action:** The CLI already handles unexpected exceptions gracefully with `typer.echo("An error occurred during download", err=True)`. The `ValidationError` will display a user-friendly message containing the validator error text.

---

## Recommendation: **GO with Changes**

### Rationale

1. **Fail-fast is superior to silent no-op** - The current behavior silently accepts `FILE` and behaves identically to `NONE`, which can lead to:
   - Users unknowingly downloading unauthenticated content
   - Confusion when documented behavior promises an error
   - No indication that the chosen mode is unsupported

2. **Consistent behavior across all entry points** - Adding the validator ensures `FILE` is rejected whether via CLI, environment variable, or programmatic API

3. **Clear error message** - Users get actionable guidance: "CookieSource.FILE is not implemented. Use 'none' or 'browser' instead."

4. **API compatibility preserved** - The enum member is retained, so downstream code importing `CookieSource.FILE` continues to work

### Required Updates (for TASK_001 follow-up)

1. **`tests/test_config.py`** - Modify `test_cookie_source_validation` to expect `ValidationError` for FILE mode
2. **`tests/test_extractor.py`** - Remove or adjust `test_extract_streams_with_cookies_file_mode_raises_not_implemented` since the error now occurs earlier
3. **`src/vkdownloader/cli.py`** - Update `--cookie-source` help text (handled by TASK_002)
4. **Documentation** - Mark FILE as rejected/unimplemented (addressed by TASK_007, TASK_012)

---

## Summary

- **Go/No-Go:** GO
- **Impact:** Breaking change for users explicitly selecting `--cookie-source file` or `VKDOWNLOADER_COOKIE_SOURCE=file`
- **Mitigation:** Clear error message guides users to valid alternatives
- **Tests to update:** 2 tests in `test_config.py` and `test_extractor.py` must be modified