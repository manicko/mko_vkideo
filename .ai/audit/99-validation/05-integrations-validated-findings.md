---
name: Phase 05 Validation — External Integrations
description: Validated audit findings for integration components in VK Video Downloader
template: .ai/audit/templates/audit-findings.md
executor: validator
status: complete
validated: yes
---

# Phase 05 Validation — External Integrations

**Executor:** validator  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** yes

---

## Findings

### INT-001: ~~Audit phase references non-existent Google Sheets integration~~ [REJECTED]

> **Rejection reason:** This finding correctly identifies that the audit phase document references non-existent integrations, but the problem is with the audit phase template itself, not the codebase. The audit phase document (`.kilo/commands/audit/phases/05-audit-integrations.md`) is a generic template that was incorrectly applied to this project. This finding should be addressed by updating the audit phase template, not as a code/spec deviation.

---

### INT-002: ~~Audit phase references non-existent Telegram integration~~ [REJECTED]

> **Rejection reason:** Same as INT-001. The audit phase document references Telegram/Telethon integration patterns that do not apply to this codebase. This is a template documentation issue, not a code/spec deviation in the actual application.

---

### INT-003: Remove or complete incomplete test file `test_hls_downloader_patch.py`

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `tests/test_hls_downloader_patch.py` |
| **Classification** | mandatory |

**Description:** The test file contains a syntax error causing pytest collection to fail.

**Evidence:**
- pytest collection error: `SyntaxError: no binding for nonlocal 'gather_called' found`
- File is 5 lines with a bare function using `nonlocal` outside any enclosing scope
- No imports, no test functions defined - appears to be orphaned/incomplete code

**Recommendation:** Remove the incomplete `test_hls_downloader_patch.py` file.

---

### INT-004: Fix coroutine/task handling in `cli.py` batch download CancelledError handler

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** The `_run_batch_with_progress` function creates coroutine objects but attempts to call Task methods on them.

**Evidence:**
- mypy error at lines 223-224: `"Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"`
- mypy error: `"Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "cancel"`
- Line 210: `tasks = [_limited_download(url) for url in urls]` creates coroutine objects
- Lines 222-224: Iterating over `tasks` and calling `.done()` and `.cancel()` on coroutines is invalid

**Recommendation:** Convert coroutines to Task objects using `asyncio.create_task()` before the loop, then iterate over Task objects returned by `asyncio.as_completed()`.

---

### INT-005: Address unused `results` variable in `downloader.py`

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Classification** | mandatory |

**Description:** The `results` variable from `asyncio.gather(*tasks)` is assigned but never used. Instead, `downloaded_count` is set to `len(segments)` regardless of actual download success.

**Evidence:**
- ruff F841 error at line 395: `Local variable 'results' is assigned to but never used`
- Line 395: `results = await asyncio.gather(*tasks)`
- Line 405: `downloaded_count = len(segments)` - uses total segments, not actual successful downloads

**Recommendation:** Either use `results.count(True)` for `downloaded_count` to accurately track successful downloads, or remove the unused `results` assignment and fix the logic.

---

### INT-006: Inconsistent SSL verification handling between integrations

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/infrastructure/http_client.py` |
| **Classification** | advisory |

**Description:** ffmpeg and yt-dlp integrations bypass the `ssl_verify` configuration setting, creating inconsistent security posture.

**Evidence:**
- `http_client.py` lines 50-57: SSL verification properly handled with configurable `ssl_verify` setting
- `downloader.py` line 924: `"nocheckcertificate": True` hardcoded in yt-dlp options - ignores `settings.ssl_verify`
- ffmpeg commands in `downloader.py`: No SSL verification options passed

**Recommendation:** Pass SSL verification settings to yt-dlp (`nocheckcertificate` should respect `settings.ssl_verify`) and consider SSL options for ffmpeg when appropriate.

---

### INT-007: yt-dlp `nocheckcertificate` ignores user SSL verification preference

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** The `Settings.ssl_verify` field exists and is used in `HttpClient`, but yt-dlp configuration hardcodes certificate verification as disabled regardless of user preference.

**Evidence:**
- `config.py` line 47-50: `ssl_verify: bool = Field(default=True, ...)` setting exists
- `downloader.py` line 924: `"nocheckcertificate": True` hardcoded in `_download_with_ytdlp`

**Recommendation:** Set `nocheckcertificate` based on `settings.ssl_verify` to respect user's security preference.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | INT-003, INT-004, INT-005, INT-006, INT-007 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 2 | INT-001, INT-002 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| INT-001 | Audit phase references non-existent Google Sheets integration | Template documentation issue, not a code/spec deviation |
| INT-002 | Audit phase references non-existent Telegram integration | Template documentation issue, not a code/spec deviation |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| — | — | — | — |

---

## Mandatory Fixes

1. INT-003: Remove or complete the incomplete `test_hls_downloader_patch.py` file
2. INT-004: Fix coroutine/task handling - use `asyncio.create_task()` to create Task objects before iterating with `as_completed()`
3. INT-005: Fix the unused `results` variable - use actual results to track successful downloads or remove the assignment

## Advisory Recommendations

1. INT-006: Align SSL verification behavior across all external integrations
2. INT-007: Respect SSL verification setting in yt-dlp configuration

---

## Actual External Integrations Confirmed

The project integrates with:
1. **yt-dlp** (`src/vkdownloader/services/downloader.py`) - Video extraction and download
2. **ffmpeg/ffprobe** (`src/vkdownloader/services/downloader.py`) - HLS stream processing and merging
3. **Playwright** (`src/vkdownloader/infrastructure/browser.py`, `src/vkdownloader/services/extractor.py`) - Browser automation for token/cookie capture
4. **aiohttp** (`src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/services/downloader.py`) - HTTP client with retry logic