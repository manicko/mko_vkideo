---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 06 Audit Findings — End-to-End Data Flow

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### DF-001: Segment download results discarded without checking for failures

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** In `download_hls_with_resume`, the return values from `asyncio.gather(*tasks)` on line 395 are assigned to `results` but never checked. This means segment download failures are silently ignored - if some segments fail to download, the code proceeds to merge incomplete data without logging or handling the failures.

**Evidence:**
```python
# downloader.py:395-406
results = await asyncio.gather(*tasks)
except asyncio.CancelledError:
    # Cancel any still-running tasks on interruption
    for task in tasks:
        if not task.done():
            task.cancel()
    # Wait for cancellation to complete, ignoring results
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("download_cancelled", reason="shutdown_requested")
    return None
downloaded_count = len(segments)
```
The `results` list containing boolean success indicators is never inspected. The code blindly assumes all segments downloaded successfully and sets `downloaded_count = len(segments)`.

**Recommendation:** Check results for failures before proceeding to merge. Either log warnings for failed segments or return early if any downloads failed. Effort: small. Priority: recommended.

---

### DF-002: Inconsistent error handling between yt-dlp and ffmpeg async contexts

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:901-973` |
| **Classification** | advisory |

**Description:** The `_download_with_ytdlp` function creates a task via `asyncio.ensure_future()` on line 957 and attempts to cancel it on CancelledError (line 968-969). However, this cancellation is ineffective because yt-dlp runs in a thread pool executor via `run_in_executor()`. The blocking thread will continue running until completion, potentially leaving partial downloads or temp files.

**Evidence:**
```python
# downloader.py:954-973
# Create task for the executor to allow cancellation
async def coro() -> str:
    return str(result)
return coro()

try:
    result = await download_task
    return Path(result)
except asyncio.CancelledError:
    logger.info("yt_dlp_download_cancelled")
    # Cancel the executor task (though the thread will continue, it will be
    # cleaned up when the process exits or on subsequent runs)
    if not download_task.done():
        download_task.cancel()
    raise
```
The comment acknowledges the thread continues running. This can leave partial `.mp4` files or yt-dlp temp files on disk.

**Recommendation:** Implement file cleanup in the CancelledError handler for yt-dlp downloads, or document that partial files may remain. Effort: small. Priority: recommended.

---

### DF-003: SSL verification setting not used in segment download

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:335-336` |
| **Classification** | advisory |

**Description:** The `ssl_verify` setting from Settings is properly used in `HttpClient` (http_client.py:50-57) and yt-dlp options (downloader.py:924), but NOT in the segment download flow (`download_hls_with_resume`). The `aiohttp.TCPConnector()` on line 335 is created without SSL context, ignoring the configured setting.

**Evidence:**
```python
# downloader.py:335-336
connector = aiohttp.TCPConnector(limit=10)
async with aiohttp.ClientSession(connector=connector) as session:
```
Compare to http_client.py:50-57 where SSL context is conditionally created based on settings.

**Recommendation:** Apply the same SSL verification logic to the segment download connector. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 0 |

## Mandatory Fixes

- DF-001: Segment download results discarded without checking for failures (HIGH severity)

## Advisory Recommendations

- DF-002: Inconsistent error handling between yt-dlp and ffmpeg async contexts (MEDIUM severity)
- DF-003: SSL verification setting not used in segment download (MEDIUM severity)