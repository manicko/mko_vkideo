---
name: 06-data-flow-validated-findings
description: Phase 06 Audit Findings - End-to-End Data Flow (Validated)
agent: validator
validated: yes
source: .ai/audit/06-data-flow/findings.md
---

# Phase 06 Audit Findings — End-to-End Data Flow (Validated)

**Executor:** validator  
**Source:** .ai/audit/06-data-flow/findings.md  
**Status:** complete  
**Validated:** yes

---

## Cross-Finding Analysis

### Duplicate Findings Across Phases

| Original ID | Duplicate IDs | Target for Merge |
|-------------|---------------|----------------|
| DF-001 | SRV-003, QLT-002 | Keep DF-001 (Phase 06) |

### Cross-Phase Conflicts

No conflicts detected. All phases consistently report the same issues.

---

## Findings

### DF-001: Segment download results discarded without checking for failures

| Field | Value |
|-------|-------|
| **ID** | DF-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:395` |
| **Classification** | mandatory |

**Description:** In `download_hls_with_resume`, the return values from `asyncio.gather(*tasks)` on line 395 are assigned to `results` but never checked. This means segment download failures are silently ignored - if some segments fail to download, the code proceeds to merge incomplete data without logging or handling the failures.

**Evidence:**
```python
# downloader.py:393-405
if tasks:
    try:
        results = await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        # Cancel any still-running tasks on interruption
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("download_cancelled", reason="shutdown_requested")
        return None
    downloaded_count = len(segments)  # Blindly assumes all succeeded
```
The `results` list containing boolean success indicators is never inspected. Additionally, `downloaded_count = len(segments)` on line 405 is set unconditionally, ignoring the actual count of successfully downloaded segments.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by ruff check (`F841` unused variable) and code inspection. The `results` variable holds download success booleans from `download_segment_concurrent`, but is never used. The code incorrectly assumes all segments downloaded successfully and proceeds to merge. This overlaps with SRV-003 and QLT-002 (duplicate findings from Phase 03/08).
> - **See also:** SRV-003 (Phase 03), QLT-002 (Phase 08) - same unused variable issue

**Status:** ✅ VALIDATED - SPEC-DEVIATION: Implementation silently ignores segment download failures instead of checking results before merge.

---

### DF-002: Inconsistent error handling between yt-dlp and ffmpeg async contexts

| Field | Value |
|-------|-------|
| **ID** | DF-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:901-973` |
| **Classification** | advisory |

**Description:** The `_download_with_ytdlp` function creates a task via `asyncio.ensure_future()` on line 957 and attempts to cancel it on CancelledError (line 968-969). However, this cancellation is ineffective because yt-dlp runs in a thread pool executor via `run_in_executor()`. The blocking thread will continue running until completion, potentially leaving partial downloads or temp files.

**Evidence:**
```python
# downloader.py:954-973
loop = asyncio.get_running_loop()
download_task = asyncio.ensure_future(
    loop.run_in_executor(None, _download)
)
try:
    result = await download_task
    return Path(result)
except asyncio.CancelledError:
    logger.info("yt_dlp_download_cancelled")
    if not download_task.done():
        download_task.cancel()
    raise
```
The comment acknowledges the thread continues running. The code at lines 966-970 shows the limitation is known but no mitigation is implemented.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by code inspection. The `run_in_executor` pattern cannot interrupt the running thread - cancellation only prevents the result from being awaited, but the underlying yt-dlp process continues. Partial `.mp4` files or temp files may remain on disk after cancellation.
> - **See also:** None

**Status:** ✅ VALIDATED - SPEC-DEVIATION: Partial download cleanup on cancellation is not implemented.

---

### DF-003: SSL verification setting not used in segment download

| Field | Value |
|-------|-------|
| **ID** | DF-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:335-336` |
| **Classification** | advisory |

**Description:** The `ssl_verify` setting from Settings is properly used in `HttpClient` (`infrastructure/http_client.py:50-57`) and yt-dlp options (`downloader.py:924`), but NOT in the segment download flow (`download_hls_with_resume`). The `aiohttp.TCPConnector()` on line 335 is created without SSL context, ignoring the configured setting.

**Evidence:**
```python
# downloader.py:335-336
connector = aiohttp.TCPConnector(limit=10)
async with aiohttp.ClientSession(connector=connector) as session:
```
Compare to `http_client.py:50-57` where SSL context is conditionally created based on settings.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by code inspection. The `Settings.ssl_verify` field (config.py:47-50) controls SSL verification in HttpClient and yt-dlp, but the segment download creates an unconfigured `TCPConnector` without SSL context. This ignores user configuration and creates inconsistent security posture.
> - **See also:** None

**Status:** ✅ VALIDATED - SPEC-DEVIATION: SSL verification configuration is ignored in segment download flow.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | DF-001, DF-002, DF-003 |
| Reclassified | 0 | — |
| Merged | 1 | DF-001 overlaps with SRV-003/QLT-002 |
| Rejected | 0 | — |

### Rejected Findings

None. All findings in this phase are valid.

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| SRV-003 | DF-001 (Phase 06) | Same unused `results` variable at same location (downloader.py:395) |
| QLT-002 | DF-001 (Phase 06) | Same unused `results` variable at same location (downloader.py:395) |

### Reclassified Findings

No reclassification needed. All three findings are SPEC-DEVIATION type - the code deviates from expected behavior where settings/configuration are correctly applied.

---

## Rollout Analysis

**No rollout safety issues detected within this phase.** The findings are isolated logic issues that do not affect architectural dependencies. However:

- **DF-001** (segment download results) - High risk: Incomplete downloads may produce corrupted output files
- **DF-002** (yt-dlp cancellation) - Low risk: Stale files may remain but will be cleaned on next run
- **DF-003** (SSL verification) - Medium risk: Security configuration inconsistency affects all segment downloads

---

## Warnings

- **Cross-phase architectural risk:** Global shutdown event (`_shutdown_event` in `downloader_throttle.py`) affects testability (CFG-007/SRV-002/TST-002) and may cause issues in concurrent execution scenarios
- **Blocking issue:** Syntax error in `tests/test_hls_downloader_patch.py` blocks all test collection (CFG-003/SRV-001/QLT-007/TST-001) - must be resolved before tests can run
- **DF-001 & DF-003 together** create a risk scenario: Failed segment downloads due to SSL issues would go undetected

---

## Required Fixes

- DF-001: Check `results` for failures before proceeding to merge; track actual downloaded count (HIGH severity)
- DF-003: Apply the same SSL verification logic to the segment download connector (MEDIUM severity)

---

## Advisory Recommendations

- DF-002: Document that partial yt-dlp downloads may remain on disk after cancellation, or implement file cleanup in CancelledError handler (MEDIUM severity)