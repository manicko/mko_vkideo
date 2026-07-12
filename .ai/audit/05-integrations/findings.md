---
name: Phase 05 Audit Findings — External Integrations
description: Audit findings for integration components in VK Video Downloader
template: .ai/audit/templates/audit-findings.md
executor: auditor
status: complete
validated: no
---

# Phase 05 Audit Findings — External Integrations

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### INT-001: Audit phase references non-existent Google Sheets integration

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/phases/05-audit-integrations.md` |
| **Classification** | mandatory |

**Description:** The audit phase document specifies checking `GSheetsReader` class and Google Sheets API integration, but this integration does not exist in the codebase. The project is a VK Video Downloader that does not use Google Sheets for any purpose.

**Evidence:** 
- grep for "gsheets|google.*sheets|GSheetsReader|TelegramPoster|telethon|TelegramClient" returns no results (verified)
- `pyproject.toml` dependencies: playwright, aiohttp, pydantic, typer, structlog, yt-dlp - no google-api-python-client or telethon packages
- No Google Sheets or Telegram integration modules found in `src/vkdownloader/`

**Recommendation:** Update the audit phase document to reflect actual integrations (yt-dlp, ffmpeg, Playwright) or remove references to non-existent integrations.

---

### INT-002: Audit phase references non-existent Telegram integration

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/phases/05-audit-integrations.md` |
| **Classification** | mandatory |

**Description:** The audit phase document specifies checking `TelegramPoster` and Telethon integration, but this integration does not exist in the codebase. The project does not have Telegram messaging capabilities.

**Evidence:**
- No telethon package in `pyproject.toml` dependencies
- No telegram-related files in `src/vkdownloader/` or tests
- No messaging or notification features in CLI

**Recommendation:** Update the audit phase document to focus on actual external integrations present in the project.

---

### INT-003: Syntax error in test file breaks test collection

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `tests/test_hls_downloader_patch.py` |
| **Classification** | mandatory |

**Evidence:**
```
ERROR collecting tests/test_hls_downloader_patch.py
tests/test_hls_downloader_patch.py:2:1: SyntaxError: no binding for nonlocal 'gather_called' found
```

The file contains:
```python
1: async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
2:             nonlocal gather_called
```
- A bare function with no enclosing scope cannot use `nonlocal` statement
- File is incomplete (only 5 lines) and appears to be leftover/orphaned code

**Recommendation:** Remove the incomplete `test_hls_downloader_patch.py` file or complete the implementation with proper enclosing scope.

---

### INT-004: Type checker error - coroutine methods called on coroutine object

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Evidence:**
```
src\vkdownloader\cli.py:223: error: "Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"
src\vkdownloader\cli.py:224: error: "Coroutine[Any, Any, tuple[str, Any, Any]]" has no attribute "cancel"
```

Code at lines 169-178, 217-227:
```python
async def _download_single(url: str) -> tuple[str, str, str]:
    ...

async def _run_batch_with_progress() -> list[tuple[str, str, str]]:
    ...
    tasks = [_limited_download(url) for url in urls]  # Line 210: creates coroutine objects

    for coro in asyncio.as_completed(tasks):  # Line 217
        try:
            await coro
        except asyncio.CancelledError:
            # Cancel remaining tasks on interrupt
            for task in tasks:
                if not task.done():       # Line 223: tasks contains coroutines, not Task objects
                    task.cancel()         # Line 224: coroutines don't have cancel() method
```

The `tasks` list in `_run_batch_with_progress()` contains coroutine objects from `_limited_download()`, not Task objects. Calling `.done()` and `.cancel()` on coroutines is invalid - these methods only exist on `asyncio.Task` instances.

**Recommendation:** Convert coroutines to Task objects using `asyncio.create_task()` before adding to tasks list, or iterate over Task objects returned by `asyncio.as_completed()`.

---

### INT-005: Unused variable may indicate broken control flow logic

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Evidence:**
```
src\vkdownloader\services\downloader.py:395:21: F841 Local variable `results` is assigned to but never used
```

Code at lines 392-406:
```python
tasks = [
    asyncio.create_task(download_segment_concurrent(i, seg))
    for i, seg in enumerate(segments)
    if not (segments_dir / f"{i:05d}.ts").exists()
]
if tasks:
    try:
        # Wait for all tasks to complete, but allow shutdown interruption
        results = await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        ...
    downloaded_count = len(segments)  # Uses len(segments), not results - logic bug
```

The `results` variable from `asyncio.gather(*tasks)` is never used. Instead, `downloaded_count` is set to `len(segments)` regardless of actual download success. This means if some downloads fail, the count still reflects total segments, potentially causing incorrect merge decisions.

**Recommendation:** Use `results.count(True)` for `downloaded_count` to accurately track successful downloads, or remove the unused `results` assignment.

---

### INT-006: Inconsistent SSL verification handling between integrations

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/infrastructure/http_client.py` |
| **Classification** | advisory |

**Evidence:**
- `http_client.py` lines 50-57: SSL verification properly handled with configurable `ssl_verify` setting
- `downloader.py` line 924: `"nocheckcertificate": True` hardcoded in yt-dlp options - ignores `settings.ssl_verify`
- ffmpeg commands (lines 150-163) in `downloader.py`: No SSL verification options passed

ffmpeg and yt-dlp integrations bypass the `ssl_verify` configuration setting, creating inconsistent security posture.

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

**Evidence:**
```python
# downloader.py line 924
ydl_opts = {
    ...
    "nocheckcertificate": True,  # Hardcoded - ignores settings.ssl_verify
    ...
}
```

The `Settings.ssl_verify` field exists and is used in `HttpClient`, but yt-dlp configuration hardcodes certificate verification as disabled regardless of user preference.

**Recommendation:** Set `nocheckcertificate` based on `settings.ssl_verify` to respect user's security preference.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 3 |
| LOW | 0 |

## Mandatory Fixes

- INT-003: Remove or complete incomplete test file `test_hls_downloader_patch.py`
- INT-004: Fix coroutine/task handling in `cli.py` batch download CancelledError handler
- INT-005: Address unused `results` variable in `downloader.py`

## Advisory Recommendations

- INT-001: Update audit phase to reference actual integrations
- INT-002: Update audit phase to remove Telegram integration references
- INT-006: Align SSL verification behavior across all external integrations
- INT-007: Respect SSL verification setting in yt-dlp configuration

---

## Actual External Integrations Discovered

The project integrates with:
1. **yt-dlp** (`src/vkdownloader/services/downloader.py`) - Video extraction and download
2. **ffmpeg/ffprobe** (`src/vkdownloader/services/downloader.py`) - HLS stream processing and merging
3. **Playwright** (`src/vkdownloader/infrastructure/browser.py`, `src/vkdownloader/services/extractor.py`) - Browser automation for token/cookie capture
4. **aiohttp** (`src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/services/downloader.py`) - HTTP client with retry logic