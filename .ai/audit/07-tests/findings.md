---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 07 Audit Findings — Test Quality

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### TST-001: Duplicate Test Class Definitions in test_hls_downloader.py

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_hls_downloader.py |
| **Classification** | advisory |

**Description:** The file `tests/test_hls_downloader.py` contains two identical class definitions `TestHLSDownloaderDownload` (lines 97-164 and lines 166-224). These classes contain duplicate test methods with the same names: `test_download_with_ffmpeg_success`, `test_error_handling_ffmpeg_failure`, `test_ffmpeg_command_contains_expected_elements`, and `test_ffmpeg_command_output_path` (duplicate). This represents copy-paste error that doubles the test count without adding coverage, and the second class also contains a duplicate test method. The duplicate tests at lines 166-224 are identical to those at 97-164, and line 156-163 contains `test_ffmpeg_command_output_path` while lines 87-94 contain another identical test with the same name.

**Evidence:** Lines 97-224 in `tests/test_hls_downloader.py` show two identical `TestHLSDownloaderDownload` classes. Lines 87-94 and 156-163 show duplicate `test_ffmpeg_command_output_path` methods in the same file.

**Recommendation:** Remove the duplicate test class (lines 166-224) and the duplicate `test_ffmpeg_command_output_path` method within the first class. Consolidate to a single `TestHLSDownloaderDownload` class.

---

### TST-002: Missing Tests for CLI Module

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py, tests/ |
| **Classification** | advisory |

**Description:** The CLI module (`src/vkdownloader/cli.py`) contains 165 lines of code including two commands (`download` and `batch_download`) and critical error handling logic, but has zero test coverage. Per the project's coding standards (Single Responsibility, Small Modules), CLI commands are a critical user-facing component that should be tested for: command invocation, argument parsing, output directory creation, error output handling, and exit codes on failure.

**Evidence:** No test file exists for CLI (`test_cli.py` not found in tests directory). The file `tests/test_hls_downloader.py` contains 224 lines testing the downloader, but CLI has no dedicated tests.

**Recommendation:** Create `tests/test_cli.py` with tests for the `download` command (success path, error path, exit code on failure) and `batch_download` command (URL file parsing, empty file error, concurrency with semaphore).

---

### TST-003: Missing Tests for download_hls_with_resume Function and Resume Logic

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `download_hls_with_resume` function (lines 71-145 in `src/vkdownloader/services/downloader.py`) implements segment-level resume support - a core feature for reliability. This function calls private helpers `_fetch_playlist_with_retry`, `_parse_m3u8_segments`, `_download_segment`, `_merge_segments_batched`, `_load_downloaded_count`, `_save_downloaded_count`, and `_cleanup_segments`. None of these functions have any test coverage despite implementing critical logic for download resumption and segment merging.

**Evidence:** `grep` search for these function names in tests returns no results. The function `download_hls_with_resume` handles retry logic for 403/410 responses (token refresh), segment downloading with progress tracking, and batched ffmpeg merging - all untested.

**Recommendation:** Add tests for: 
1. `_parse_m3u8_segments` with valid playlist content
2. `_download_segment` with success and failure cases  
3. `_merge_segments_batched` with various segment counts
4. `_load_downloaded_count` / `_save_downloaded_count` with metadata file roundtrip
5. Integration test for `download_hls_with_resume` with mock aiohttp session

---

### TST-004: Missing Tests for Main Entry Point Functions

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | main.py |
| **Classification** | advisory |

**Description:** The `main.py` module contains `download_video`, `download_with_ytdlp_with_resume_fallback`, and `_download_with_ytdlp` functions implementing the core download orchestration logic with retry counts, partial file handling, and method selection. These functions are untested, leaving a critical path without verification. The `print()` statements on lines 49, 52, 137, 155, 206, 217, 233, 235 violates project rule #13 (no print() statements).

**Evidence:** No tests reference `main.py`, `download_video`, `download_with_ytdlp_with_resume_fallback`, or `_download_with_ytdlp` functions. The print() calls are used for user output instead of proper logging.

**Recommendation:** Add tests for `download_video` with different `DownloadMethod` enum values, and `download_with_ytdlp_with_resume_fallback` with partial file scenarios. Replace print() with structured logging.

---

### TST-005: Tautological Integration Tests

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/integration/test_mock_vk_server.py |
| **Classification** | advisory |

**Description:** The `TestMockServerIntegration` class contains three tests that only verify mock response setup, not actual application logic. `test_mock_video_page_response` asserts that `mock_response.status == 200` (always true by mock setup). `test_mock_m3u8_response` asserts mock property values that are hardcoded in the test. `test_mock_video_page_various_ids` only verifies string interpolation works (`assert vid in html_content`). These tests cannot fail and provide no value regarding the actual VK server integration.

**Evidence:** 
- `test_mock_video_page_response` (lines 9-28): only asserts mock property equals hardcoded value
- `test_mock_m3u8_response` (lines 30-47): asserts hardcoded string contains hardcoded string
- `test_mock_video_page_various_ids` (lines 49-63): asserts format string interpolation works

**Recommendation:** Either remove these tautological tests or replace them with actual integration tests that verify `_extract_urls_from_json` correctly parses VK video page responses, or test the m3u8 parsing logic against real playlist formats.

---

### TST-006: Missing Tests for Extractor Async Methods

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Classification** | advisory |

**Description:** `VKVideoExtractor` (lines 22-281 in `src/vkdownloader/services/extractor.py`) has async methods `extract_streams`, `extract_streams_with_cookies`, `_extract_with_ytdlp`, `_extract_with_browser`, `_parse_m3u8_playlist`, and `_format_cookies_for_ffmpeg`. The test file `tests/test_extractor.py` only tests `parse_video_id` (47 lines), leaving ~240 lines of async extraction logic untested. This includes yt-dlp integration, browser automation orchestration, and cookie handling for ffmpeg authentication.

**Evidence:** `test_extractor.py` has 47 lines with 4 tests total. The test file contains no async tests, no mocking of `BrowserManager` or `yt_dlp`, and no tests for `_format_cookies_for_ffmpeg` (lines 186-195) which formats cookies for authentication headers.

**Recommendation:** Add async tests for `extract_streams` with mocked yt-dlp response, `extract_streams_with_cookies` with mocked browser context, and `_format_cookies_for_ffmpeg` with sample cookie lists.

---

### TST-007: Missing Tests for AdaptiveThrottle Infrastructure

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/infrastructure/adaptive_throttle.py |
| **Classification** | advisory |

**Description:** `AdaptiveThrottle` class (lines 11-65 in `src/vkdownloader/infrastructure/adaptive_throttle.py`) implements rate limiting with exponential backoff (`on_rate_limited`) and recovery (`on_success`). This infrastructure code has zero test coverage despite being imported and used for production traffic control.

**Evidence:** No tests found for `AdaptiveThrottle`. The class contains `_calculate_base_delay` (line 26), `wait` (lines 30-34), `on_rate_limited` (lines 36-48), and `on_success` (lines 50-62) methods that all need verification.

**Recommendation:** Add tests for throttle initialization, wait delay calculation, backoff behavior, and recovery behavior.

---

### TST-008: Missing Tests for DTO Models

| Field | Value |
|-------|-------|
| **ID** | TST-008 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/dtos.py |
| **Classification** | advisory |

**Description:** The DTO models `DownloadRequest` and `DownloadResult` in `src/vkdownloader/models/dtos.py` (28 lines) have no test coverage. These models define the request/response contracts for the download API and should have validation tests for Pydantic model behavior.

**Evidence:** `test_models.py` only tests `Video`, `Stream`, `VideoWithStreams`, `DownloadProgress`, and models in `video.py` and `enums.py`. No tests for `dtos.py` models.

**Recommendation:** Add tests for `DownloadRequest` model validation (url, quality default, output_path default) and `DownloadResult` model with optional fields.

---

### TST-009: Missing Tests for StreamWithCookies Model

| Field | Value |
|-------|-------|
| **ID** | TST-009 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/video.py |
| **Classification** | advisory |

**Description:** The `StreamWithCookies` model (lines 51-54 in `src/vkdownloader/models/video.py`) extends `Stream` with optional cookies field, but has no test coverage.

**Evidence:** Not tested in `test_models.py`.

**Recommendation:** Add test for `StreamWithCookies` model creation with cookies field.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 4 |
| MEDIUM | 3 |
| LOW | 2 |

## Advisory Recommendations

- TST-001: Remove duplicate test class definitions in test_hls_downloader.py (166-224)
- TST-002: Create tests/test_cli.py for download and batch commands
- TST-003: Add tests for download_hls_with_resume and helper functions
- TST-004: Add tests for main.py functions and replace print() with logging
- TST-005: Remove or rewrite tautological integration tests
- TST-006: Add async tests for VKVideoExtractor extraction methods
- TST-007: Add tests for AdaptiveThrottle rate limiting behavior
- TST-008: Add tests for DownloadRequest and DownloadResult DTO models
- TST-009: Add test for StreamWithCookies model

---