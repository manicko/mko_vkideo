---
name: 08-quality
description: Code Quality, Security & Maintainability
agent: auditor
status: complete
validated: no
problems-only: true

## Findings

### QLT-001: Test expects ssl_verify default True but .env file overrides it

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/test_config.py, src/vkdownloader/config.py, .env |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` in `tests/test_config.py:20` asserts that `settings.ssl_verify is True`, but the `.env` file contains `VKDOWNLOADER_SSL_VERIFY=false` which overrides the Pydantic default of `True` when `Settings()` is instantiated. This causes the test to fail because Pydantic Settings loads environment variables including the `.env` file by default.

**Evidence:**
- Test failure: `tests/test_config.py:20: assert settings.ssl_verify is True` fails with `AssertionError: assert False is True`
- `.env` line 12: `VKDOWNLOADER_SSL_VERIFY=false`
- Config default `src/vkdownloader/config.py:47-50`: `ssl_verify: bool = Field(default=True, ...)`
- Settings uses pydantic_settings BaseSettings with `env_file: ".env"` in model_config

**Recommendation:** Either remove the `VKDOWNLOADER_SSL_VERIFY=false` line from `.env` if it's not needed for development, or update the test to explicitly pass `ssl_verify=True` to isolate the default value test from environment configuration. This is a test isolation issue that causes false negatives when the `.env` file is present.

---

### QLT-002: Large modules violate single responsibility principle

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The file `src/vkdownloader/services/downloader.py` contains 1130 lines, making it a god module that combines multiple responsibilities: ffmpeg download, HLS segment download, yt-dlp download with resume fallback, signal handlers, and merge operations. The project rule requires "Small modules and functions" for higher ROI in maintenance.

**Evidence:**
- `src/vkdownloader/services/downloader.py`: 1130 lines
- Functions exceeding 50 lines in this file:
  - `download_hls_with_resume()` - 150 lines
  - `download_with_ffmpeg()` - 113 lines
  - `_download_segment()` - 58 lines
  - `download_with_ytdlp_with_resume_fallback()` - 94 lines
  - `_download_with_ytdlp()` - 76 lines
  - `perform_download()` - 97 lines
  - `_retry_429_with_backoff()` - 94 lines (in downloader_throttle.py but related)

**Recommendation:** Split `downloader.py` into focused modules:
- `ffmpeg_downloader.py` - ffmpeg-related download logic
- `hls_downloader.py` - HLS segment download with resume
- `ytdlp_downloader.py` - yt-dlp download with fallback
- `merge_operations.py` - segment merging utilities

Effort: medium | Priority: recommended

---

### QLT-003: Use of Any type hints instead of concrete types

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/models/dtos.py, src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The codebase uses `Any` type hints in several places with comments indicating they are used to avoid circular import issues. While the comments explain the reasoning, the project rule requires "Type Safety Everywhere" and "No any types". Modern Python type systems support forward references and TYPE_CHECKING imports for this purpose.

**Evidence:**
- `src/vkdownloader/models/dtos.py:8`: `from typing import Any`
- `src/vkdownloader/models/dtos.py:38-42`: Uses `Any` for `settings`, `extractor`, and `backoff_coordinator` with comments about circular imports
- `src/vkdownloader/services/downloader.py:11`: `from typing import Any`
- `src/vkdownloader/services/downloader.py:525,1041`: Uses `Any` for `backoff_coordinator`

**Recommendation:** Replace `Any` with proper forward references using `from __future__ import annotations` and `TYPE_CHECKING` imports:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vkdownloader.config import Settings
    from vkdownloader.services.downloader_throttle import URLBackoffCoordinator

backoff_coordinator: URLBackoffCoordinator | None = None
```

Effort: small | Priority: recommended

---

### QLT-004: Multiple bare Exception catches suppress errors

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/downloader_throttle.py, src/vkdownloader/services/extractor.py, src/vkdownloader/utils/url_sanitizer.py |
| **Classification** | advisory |

**Description:** Several files catch bare `Exception` which can hide programming errors and make debugging difficult. The code catches `Exception` in multiple places where more specific exception types should be used.

**Evidence:**
- `src/vkdownloader/services/downloader.py:814`: `except Exception as e:` with only logging
- `src/vkdownloader/services/downloader.py:1029`: `except Exception as e:` for download fallback
- `src/vkdownloader/services/downloader_throttle.py:226`: `except Exception as e:` 
- `src/vkdownloader/services/extractor.py:260`: `except Exception:` followed by `pass` (click simulation)
- `src/vkdownloader/utils/url_sanitizer.py:65`: `except Exception:` for URL parsing fallback

**Recommendation:** Either use more specific exception types or restructure to avoid catching broad exceptions. For the URL sanitizer, catching specific parsing exceptions is appropriate. For the click simulation in extractor.py, logging at debug level would be more informative.

Effort: small | Priority: recommended

---

### QLT-005: Blocking file I/O in async functions

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Several async functions use blocking `open()` calls instead of async file I/O, which can block the event loop during file operations.

**Evidence:**
- `src/vkdownloader/services/downloader.py:548`: `with open(output_path, "wb") as f:` in async context
- `src/vkdownloader/services/downloader.py:565`: Same pattern
- `src/vkdownloader/services/downloader.py:668`: File write in `_merge_batch_segments`
- `src/vkdownloader/services/downloader.py:708`: File write in `_perform_final_merge`
- `src/vkdownloader/services/downloader.py:774,784`: JSON read/write in `_load_downloaded_count` and `_save_downloaded_count`

**Recommendation:** Replace with `aiofiles` or use `asyncio.to_thread()` for file I/O operations to avoid blocking the event loop. For small JSON metadata files, the async overhead may not be worth it, but for large file writes, async I/O improves concurrency.

Effort: small | Priority: recommended

---

### QLT-006: Unused lambda argument warnings in signal handlers

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** Lambda functions in signal handler fallback code have unused arguments (`s` and `f`), which trigger linting warnings and indicate incomplete handler implementation.

**Evidence:**
- `src/vkdownloader/services/downloader.py:851`: `signal.signal(sig, lambda s, f: _handle_signal())` - argument `s` unused
- `src/vkdownloader/services/downloader.py:856`: Same pattern

**Recommendation:** Use underscore prefix for unused arguments: `lambda _s, _f: _handle_signal()` or define a proper handler function.

Effort: trivial | Priority: recommended

---

### QLT-007: Global state pattern for signal handler setup

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `setup_signal_handlers()` function uses `global _signal_handlers_setup` to track state, which is discouraged in Python code as it makes the code harder to test and can cause issues in some contexts.

**Evidence:**
- `src/vkdownloader/services/downloader.py:821-826`: Global variable `_signal_handlers_setup` used to prevent duplicate signal handler registration

**Recommendation:** Refactor to use a class or closure pattern instead of global state. Consider using a singleton pattern or module-level initialization guard.

Effort: small | Priority: recommended

---

### QLT-008: Functions with too many arguments

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/downloader_throttle.py |
| **Classification** | advisory |

**Description:** Several functions have more than 5 arguments, exceeding the common threshold for function complexity and making them harder to test and call.

**Evidence:**
- `src/vkdownloader/services/downloader.py:464`: `_fetch_playlist_with_retry()` - 7 arguments
- `src/vkdownloader/services/downloader.py:518`: `_download_segment()` - 8 arguments
- `src/vkdownloader/services/downloader.py:860`: `download_with_ytdlp_with_resume_fallback()` - 7 arguments
- `src/vkdownloader/services/downloader.py:1034`: `perform_download()` - 9 arguments + 14 branches
- `src/vkdownloader/services/downloader_throttle.py:142`: `_retry_429_with_backoff()` - 9 arguments

**Recommendation:** Group related parameters into dataclasses or Pydantic models. For example, create a `SegmentDownloadRequest` model to hold the segment download parameters instead of passing 8 individual arguments.

Effort: medium | Priority: recommended

---

### QLT-009: Code formatting inconsistencies

| Field | Value |
|-------|-------|
| **ID** | QLT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | 10 source files |
| **Classification** | advisory |

**Description:** The codebase has formatting inconsistencies that would be caught by `ruff format --check`. While not functional issues, consistent formatting improves readability and maintainability.

**Evidence:**
- `ruff format --check src` reports 10 files would be reformatted
- Multiple COM812 (trailing comma missing) issues found
- PTH123 (use Path.open() instead of open()) issues

**Recommendation:** Run `ruff format` to standardize formatting. Consider adding format check to CI to prevent future inconsistencies.

Effort: trivial | Priority: recommended

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 5 |

## Mandatory Fixes

- QLT-001: Test expects ssl_verify default True but .env file overrides it (test isolation issue causing CI failures)

## Advisory Recommendations

- QLT-002: Large modules violate single responsibility principle
- QLT-003: Use of Any type hints instead of concrete types
- QLT-004: Multiple bare Exception catches suppress errors
- QLT-005: Blocking file I/O in async functions
- QLT-006: Unused lambda argument warnings in signal handlers
- QLT-007: Global state pattern for signal handler setup
- QLT-008: Functions with too many arguments
- QLT-009: Code formatting inconsistencies