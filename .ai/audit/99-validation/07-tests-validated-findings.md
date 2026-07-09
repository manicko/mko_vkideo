---
name: Phase 07 Audit Findings — Test Quality (Validated)
agent: validator
alwaysApply: false
---

# Phase 07 Audit Findings — Test Quality (Validated)

**Executor:** validator  
**Source:** `.ai/audit/07-tests/findings.md`  
**Status:** complete  
**Validated:** yes

---

## Findings

### TST-001: ~~Duplicate Test Class Definitions in test_hls_downloader.py~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_hls_downloader.py |
| **Classification** | advisory |

**Rejection reason:** The duplicate class `TestHLSDownloaderDownload` at lines 166-224 is confirmed. However, this finding was already validated and documented in DF-006 (Phase 06) and INT-007 (Phase 05). The duplicate class exists but Python silently allows class redefinition where the second overwrites the first. The test suite still passes (53 tests). This is a cross-phase duplicate finding - already validated elsewhere. See DF-006 and INT-007 for the complete analysis.

---

### TST-002: Missing Tests for CLI Module

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py, tests/ |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The CLI module has 165 lines with `download` and `batch_download` commands but no dedicated `test_cli.py` file exists. CLI is a user-facing component that should be tested per the project's Single Responsibility principle (rule #4). The recommendation to add tests for argument parsing, output directory creation, and error handling is architecturally sound.
> - **See also:** CLI-005, CLI-006 in Phase 01 also identified this gap.

**Description:** The CLI module (`src/vkdownloader/cli.py`) contains 165 lines of code including two commands (`download` and `batch_download`) and critical error handling logic, but has zero test coverage. Per the project's coding standards (Single Responsibility, Small Modules), CLI commands are a critical user-facing component that should be tested for: command invocation, argument parsing, output directory creation, error output handling, and exit codes on failure.

**Evidence:** No test file exists for CLI (`test_cli.py` not found in tests directory). The file `tests/test_hls_downloader.py` contains 224 lines testing the downloader, but CLI has no dedicated tests.

**Recommendation:** Create `tests/test_cli.py` using `typer.testing.CliRunner()`:
```python
from typer.testing import CliRunner
from vkdownloader.cli import app

runner = CliRunner()

def test_download_success():
    result = runner.invoke(app, ["download", "https://vkvideo.ru/video-123_456"])
    assert result.exit_code == 0
    assert "Downloaded" in result.output

def test_download_invalid_url():
    result = runner.invoke(app, ["download", "invalid-url"])
    assert result.exit_code != 0
    assert "Invalid" in result.output

def test_batch_empty_file():
    result = runner.invoke(app, ["batch"], input="")
    assert result.exit_code == 1
    assert "empty" in result.output.lower()
```
Effort: small. Priority: mandatory.

---

### TST-003: Missing Tests for download_hls_with_resume Function and Resume Logic

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The `download_hls_with_resume` function (lines 71-145) and its helper functions (`_fetch_playlist_with_retry`, `_parse_m3u8_segments`, `_download_segment`, `_merge_segments_batched`, `_load_downloaded_count`, `_save_downloaded_count`, `_cleanup_segments`) have zero test coverage. This is critical logic for segment-level resume support. Per validation rules, splitting large files/smaller functions is high ROI - these functions should be tested.
> - **See also:** DF-012 (Phase 06) identifies a critical bug in this same function (m3u8 URL passed to extractor expecting video URL on token refresh). Testing would have caught this.

**Description:** The `download_hls_with_resume` function (lines 71-145 in `src/vkdownloader/services/downloader.py`) implements segment-level resume support - a core feature for reliability. This function calls private helpers `_fetch_playlist_with_retry`, `_parse_m3u8_segments`, `_download_segment`, `_merge_segments_batched`, `_load_downloaded_count`, `_save_downloaded_count`, and `_cleanup_segments`. None of these functions have any test coverage despite implementing critical logic for download resumption and segment merging.

**Evidence:** `grep` search for these function names in tests returns no results. The function `download_hls_with_resume` handles retry logic for 403/410 responses (token refresh), segment downloading with progress tracking, and batched ffmpeg merging - all untested.

**Recommendation:** Add tests using pytest-asyncio and aioresponses for async testing:
```python
# tests/test_downloader.py
import pytest
from pathlib import Path
import tempfile

async def test_parse_m3u8_segments_success():
    content = "#EXTM3U\n#EXTINF:10.0\nhttps://example.com/seg1.ts\n"
    segments = downloader._parse_m3u8_segments(content, "http://base.com/")
    assert len(segments) == 1
    assert "seg1.ts" in segments[0]

async def test_download_segment_success(aioresponses_mock):
    aioresponses_mock.get("https://example.com/seg.ts", payload=b"content")
    result = await downloader._download_segment(session, "seg.ts", Path("out.ts"), {})
    assert result is True

async def test_merge_segments_batched():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test segment files
        # Call _merge_segments_batched
        # Verify merged output exists
```
Effort: small. Priority: mandatory.

---

### TST-004: Missing Tests for Main Entry Point Functions

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | main.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The `main.py` module's `download_video`, `download_with_ytdlp_with_resume_fallback`, and `_download_with_ytdlp` functions are untested. Additionally, the `print()` statements on lines 49, 52, 137, 155, 206, 217, 226, 233, 235 violate project rule #12 (no print() statements). This finding is consistent with DF-009 (Phase 06) which also identified print statement violations. DF-012 (Phase 06) identified a critical bug in `download_with_ytdlp_with_resume_fallback` that testing would have caught.

**Description:** The `main.py` module contains `download_video`, `download_with_ytdlp_with_resume_fallback`, and `_download_with_ytdlp` functions implementing the core download orchestration logic with retry counts, partial file handling, and method selection. These functions are untested, leaving a critical path without verification. The `print()` statements on lines 49, 52, 137, 155, 206, 217, 226, 233, 235 violate project rule #12 (no print() statements).

**Evidence:** No tests reference `main.py`, `download_video`, `download_with_ytdlp_with_resume_fallback`, or `_download_with_ytdlp` functions. The print() calls are used for user output instead of proper logging.

**Recommendation:** Per CLI-004 resolution, main.py should be removed. If kept temporarily, replace `print()` with `logger.info()` and add tests. However, the recommended path is to port functionality to cli.py and delete main.py. See CLI-004 for full resolution. Effort: defer to CLI-004 consolidation. Priority: superseded by CLI-004.

---

### TST-005: ~~Tautological Integration Tests~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | tests/integration/test_mock_vk_server.py |
| **Classification** | advisory |

**Rejection reason:** While the description of tautological tests is technically correct (tests asserting hardcoded mock values), these tests serve a documentation purpose and have not been flagged as high priority issues in other validated phases. They test the mock setup patterns that other tests rely on, and removing them would not provide significant architectural value. The tests pass and do not introduce runtime errors. Per validation rules, reject if "low ROI for project scale."

---

### TST-006: Missing Tests for Extractor Async Methods

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** `VKVideoExtractor` has 240+ lines of async extraction logic (lines 22-281) including `extract_streams`, `extract_streams_with_cookies`, `_extract_with_ytdlp`, `_extract_with_browser`, `_parse_m3u8_playlist`, and `_format_cookies_for_ffmpeg`. The test file has only 47 lines testing `parse_video_id`. This is a SPEC-DEVIATION because per rule #4, modules should be small and focused on one thing - the extractor is a critical service and should have proper test coverage.
> - **See also:** SRV-001 (Phase 03) identified `_parse_m3u8_playlist` as dead code; this affects testing strategy.

**Description:** `VKVideoExtractor` (lines 22-281 in `src/vkdownloader/services/extractor.py`) has async methods `extract_streams`, `extract_streams_with_cookies`, `_extract_with_ytdlp`, `_extract_with_browser`, `_parse_m3u8_playlist`, and `_format_cookies_for_ffmpeg`. The test file `tests/test_extractor.py` only tests `parse_video_id` (47 lines), leaving ~240 lines of async extraction logic untested. This includes yt-dlp integration, browser automation orchestration, and cookie handling for ffmpeg authentication.

**Evidence:** `test_extractor.py` has 47 lines with 4 tests total. The test file contains no async tests, no mocking of `BrowserManager` or `yt_dlp`, and no tests for `_format_cookies_for_ffmpeg` (lines 186-195) which formats cookies for authentication headers.

**Recommendation:** Add pytest-asyncio async tests:
```python
# tests/test_extractor.py
@pytest.mark.asyncio
async def test_extract_streams_with_cookies_success():
    with patch('vkdownloader.services.extractor.BrowserManager') as mock_browser:
        mock_network = AsyncMock()
        mock_network.m3u8_urls = ["https://cdn.video.m3u8"]
        mock_browser.return_value.__aenter__.return_value.network_monitor = mock_network
        # Test extract_streams_with_cookies returns streams

@pytest.mark.asyncio
async def test_format_cookies_for_ffmpeg():
    result = extractor._format_cookies_for_ffmpeg([
        {"name": "sid", "value": "abc123", "domain": ".vk.com"}
    ])
    assert "sid=abc123" in result
```
Note: Exclude `_parse_m3u8_playlist` (SRV-001 dead code). Effort: small. Priority: mandatory.

---

### TST-007: Missing Tests for AdaptiveThrottle Infrastructure

| Field | Value |
|-------|-------|
| **ID** | TST-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/infrastructure/adaptive_throttle.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated but note: AdaptiveThrottle is dead code / incomplete integration. Per SRV-002 (Phase 03), this class is documented and planned but never imported or used. However, it is still exported and part of the public API, so testing would verify correct implementation.
> - **See also:** SRV-002 (Phase 03) reclassified this as SPEC-DEVIATION for incomplete integration, not dead code.

**Description:** `AdaptiveThrottle` class (lines 11-65 in `src/vkdownloader/infrastructure/adaptive_throttle.py`) implements rate limiting with exponential backoff (`on_rate_limited`) and recovery (`on_success`). This infrastructure code has zero test coverage despite being imported and used for production traffic control.

**Evidence:** No tests found for `AdaptiveThrottle`. The class contains `_calculate_base_delay` (line 26), `wait` (lines 30-34), `on_rate_limited` (lines 36-48), and `on_success` (lines 50-62) methods that all need verification.

**Recommendation:** Per CFG-005/CFG-005-resolution.md, `AdaptiveThrottle` should be removed as dead code. Testing unused code has negative ROI. If rate limiting is needed later, re-implement with proper integration. Effort: defer to CFG-005. Priority: superseded.

---

### TST-008: Missing Tests for DTO Models

| Field | Value |
|-------|-------|
| **ID** | TST-008 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/dtos.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** `DownloadRequest` and `DownloadResult` in `dtos.py` (28 lines) are exported from `models/__init__.py` and define the request/response contracts for the download API. Per project rule #9 (Type Safety Everywhere), these models should have validation tests. While they are Pydantic models with implicit validation, explicit tests for field validation and defaults would improve maintainability. However, this represents low ROI given the straightforward model definitions.

**Description:** The DTO models `DownloadRequest` and `DownloadResult` in `src/vkdownloader/models/dtos.py` (28 lines) have no test coverage. These models define the request/response contracts for the download API and should have validation tests for Pydantic model behavior.

**Evidence:** `test_models.py` only tests `Video`, `Stream`, `VideoWithStreams`, `DownloadProgress`, and models in `video.py` and `enums.py`. No tests for `dtos.py` models.

**Recommendation:** Add tests in `tests/test_models.py`:
```python
def test_download_request_validation():
    req = DownloadRequest(url="https://vkvideo.ru/video-1_2", quality="720p")
    assert req.quality == "720p"
    assert req.output_path == Path(".")

def test_download_request_invalid_url():
    with pytest.raises(ValidationError):
        DownloadRequest(url="not-a-url")

def test_download_result_optional_fields():
    result = DownloadResult(file_path=Path("out.mp4"))
    assert result.error_message is None
    result2 = DownloadResult(error_message="Failed")
    assert result2.file_path is None
```
Effort: trivial. Priority: advisory (low priority per validation note).

---

### TST-009: Missing Tests for StreamWithCookies Model

| Field | Value |
|-------|-------|
| **ID** | TST-009 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/video.py |
| **Classification** | advisory |

**Rejection reason:** This finding is rejected as low-value complexity. `StreamWithCookies` (lines 51-54 in `video.py`) is a simple Pydantic model extending `Stream` with one optional field (`cookies: str | None`). It adds no validation logic beyond what Pydantic provides. Per validation rules: "Reject if overengineered or adds complexity without clear maintenance benefit" and "Reject if ROI is negative." The model will work correctly via Pydantic's implicit validation without dedicated tests.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | TST-002, TST-003, TST-004, TST-006, TST-007 |
| Rejected | 3 | TST-001 (cross-phase duplicate), TST-005 (low ROI), TST-009 (low ROI) |
| Reclassified | 0 | — |
| Merged | 0 | — |

---

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| TST-001 | Duplicate Test Class Definitions | Cross-phase duplicate - already validated in DF-006 (Phase 06) and INT-007 (Phase 05) |
| TST-005 | Tautological Integration Tests | Low ROI - tests pass and serve documentation purpose without runtime risk |
| TST-009 | Missing Tests for StreamWithCookies Model | Low ROI - trivial Pydantic model with no custom validation logic |

---

## Cross-Phase Conflicts

None detected. All validated findings align with other phases:

- TST-001 → DF-006 / INT-007 (duplicate class issue)
- TST-002 → CLI-005 / CLI-006 (CLI testing gap) - consistent
- TST-004 → DF-009 (print statements), DF-012 (critical bug in same function) - consistent
- TST-006 → SRV-001 (dead code in extractor) - relevant context
- TST-007 → SRV-002 (AdaptiveThrottle incomplete integration) - consistent
- TST-008 → No cross-phase conflicts (new finding)

---

## Warnings

- **Critical Bug Risk:** TST-003 and DF-012 identify that `download_hls_with_resume` has a critical bug where m3u8 URL is passed to extractor expecting video URL on token refresh. This will crash during resume operations. Testing would have caught this.
- **Documentation Drift:** TST-006 should note that `_parse_m3u8_playlist` (SRV-001) is dead code - tests should focus on tested paths, not dead code paths.
- **Incomplete Integration:** TST-007 references AdaptiveThrottle which is planned but not integrated (SRV-002). Testing should prioritize actually-used code.

---

## Required Fixes (from Validated Findings)

- **TST-002 (HIGH):** Create `tests/test_cli.py` for CLI command testing
- **TST-003 (HIGH):** Add tests for `download_hls_with_resume` and helper functions (critical for catching DF-012 bug)
- **TST-004 (MEDIUM):** Add tests for `main.py` functions and replace print() with logging
- **TST-006 (HIGH):** Add async tests for VKVideoExtractor extraction methods
- **TST-007 (MEDIUM):** Add tests for AdaptiveThrottle OR prioritize integration before testing

---

## Advisory Recommendations

- **TST-008:** Add tests for DownloadRequest and DownloadResult DTO models - optional improvement with low priority