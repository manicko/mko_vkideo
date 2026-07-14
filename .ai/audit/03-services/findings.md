---
name: 03-services
description: Service Layer & Business Logic
executor: auditor
status: complete
validated: no
---

# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### SRV-001: Dead code - AdaptiveThrottle class exported but never used in application

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/infrastructure/adaptive_throttle.py, src/vkdownloader/infrastructure/__init__.py:3,9 |
| **Classification** | advisory |

**Description:** The `AdaptiveThrottle` class (lines 11-66) in `infrastructure/adaptive_throttle.py` is exported via `__all__` in the infrastructure package `__init__.py` but is never imported or used anywhere in the application code. The downloader instead implements its own rate limiting via `URLBackoffCoordinator` and `_retry_429_with_backoff` in `downloader_throttle.py`. This unused class adds maintenance burden and creates confusion about the intended rate limiting strategy.

**Evidence:**
- `infrastructure/adaptive_throttle.py:11-66` defines `AdaptiveThrottle` class
- `infrastructure/__init__.py:3,9` exports it in `__all__`
- No imports of `AdaptiveThrottle` exist in the codebase (grep confirms 0 usages)
- Rate limiting is handled by `URLBackoffCoordinator` in `downloader_throttle.py` and `_retry_429_with_backoff` function

**Recommendation:** Remove `AdaptiveThrottle` class and its export from `__init__.py`, or if intended for future use, add a comment explaining its purpose and intended use case. Effort: trivial. Priority: recommended.

---

### SRV-002: Dead code - `get_video_duration` and `_parse_target_duration` functions never called

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py:578-622 |
| **Classification** | advisory |

**Description:** The functions `get_video_duration` (line 578) and `_parse_target_duration` (line 607) in `downloader.py` are defined to retrieve video duration using ffprobe by parsing m3u8 content, but they are never imported or called anywhere in the codebase. `get_video_duration` attempts to run ffprobe on an m3u8 URL which is unlikely to work as intended (ffprobe typically needs a media file, not a playlist URL). These functions were likely intended for progress percentage calculation but are dead code.

**Evidence:**
- `downloader.py:578-604` defines `get_video_duration` function
- `downloader.py:607-622` defines `_parse_target_duration` function
- grep search finds no calls to `get_video_duration` or `_parse_target_duration` outside their definitions
- The `FfmpegProgress` dataclass (lines 36-47) does not include duration tracking

**Recommendation:** Remove both functions as dead code. If duration tracking is desired, implement it properly using ffprobe on the final MP4 file rather than the m3u8 playlist. Effort: trivial. Priority: recommended.

---

### SRV-003: God class - HLSDownloader contains mixed concerns including segment downloading, retry logic, and process management

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py:162-818 |
| **Classification** | advisory |

**Description:** The `HLSDownloader` class and the module-level functions in `downloader.py` violate single responsibility by combining multiple concerns: (1) ffmpeg command building and execution, (2) segment-level download orchestration, (3) HLS playlist fetching with retry, (4) yt-dlp download wrapper, (5) segment merging logic, (6) progress tracking, and (7) signal handling for shutdown. The module has 1130 lines with 31 functions/methods, making it difficult to maintain and test individual concerns.

**Evidence:**
- Module contains: `HLSDownloader` class (download orchestration), `ProgressParser` class (parsing), `FfmpegProgress` dataclass
- Module-level functions: `read_progress`, `cancel_ffmpeg_process`, `download_hls_with_resume`, `_fetch_playlist_with_retry`, `_download_segment`, `_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `_load_downloaded_count`, `_save_downloaded_count`, `_cleanup_segments`, `_cancel_all_downloads`, `setup_signal_handlers`, `download_with_ytdlp_with_resume_fallback`, `_download_with_ytdlp`, `perform_download`
- All these are in a single 1130-line file

**Recommendation:** Consider splitting the module into focused components:
- `ffmpeg_utils.py` - ffmpeg command building and process management
- `segment_downloader.py` - segment download orchestration and merging
- `ytdlp_wrapper.py` - yt-dlp download logic
- Effort: medium. Priority: recommended.

---

### SRV-004: CLI directly accesses private `_progress_manager._state` attribute breaking encapsulation

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py:53, src/vkdownloader/services/downloader_throttle.py:94-97 |
| **Classification** | advisory |

**Description:** The `_create_progress_callback` function in cli.py (line 53) directly accesses `_progress_manager._state[url_index]`, which is a private attribute of the ProgressManager class. This breaks encapsulation and creates tight coupling between CLI and service implementation details. The ProgressManager already has an async `update` method designed for this purpose.

**Evidence:**
```python
# cli.py:50-55
def callback(video_id: str, downloaded: int, total: int) -> None:
    # Non-blocking - just update shared state
    _progress_manager._state[url_index] = (downloaded, total)
```

**Recommendation:** Add a synchronous update method to ProgressManager (e.g., `update_sync`) that uses thread-safe operations for the fire-and-forget callback pattern, or refactor callbacks to use the async API properly. Effort: small. Priority: recommended.

---

### SRV-005: Missing Task model referenced in audit phase documentation

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | .kilo/commands/audit/phases/03-audit-services.md:63,123-131 |
| **Classification** | advisory |

**Description:** The audit phase documentation references a `Task` model with fields `chat_id, topic_id, text, photos, chat_name, count, max_count` and status tracking. This model does not exist in the vkdownloader project. The documentation appears to be copied from a different project (Telepost) and does not match the actual codebase architecture.

**Evidence:**
- No `task.py` file exists in `src/vkdownloader/models/`
- grep search finds no `Task` model definition in the codebase
- The referenced attributes (chat_id, topic_id, text, photos) are Telegram/posting related, not video downloading related

**Recommendation:** Update the audit phase documentation to reflect the actual models: `Video`, `Stream`, `VideoWithStreams`, `DownloadProgress`, `DownloadRequest`, `HLSDownloadRequest`, `DownloadResult`. Effort: trivial. Priority: recommended.

---

### SRV-006: Missing service classes referenced in audit phase documentation

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | .kilo/commands/audit/phases/03-audit-services.md:63,89,100,111,121,127 |
| **Classification** | advisory |

**Description:** The audit phase documentation references `TelegramService`, `PostProcessor`, `ImageCache`, `TelegramPoster`, and `GSheetsReader` service classes that do not exist in the vkdownloader project. The actual services are: `HLSDownloader`, `QualitySelector`, `VKVideoExtractor`, `HttpClient`, `BrowserManager`, `NetworkMonitor`, `URLBackoffCoordinator`, `ProgressManager`, and `AdaptiveThrottle`.

**Evidence:**
- No `telegram.py`, `post_processor.py`, `image_cache.py`, `gsheets_reader.py` files exist in `src/vkdownloader/services/`
- Only `downloader.py`, `quality.py`, `extractor.py`, `downloader_throttle.py` exist as services
- grep search confirms no references to Telegram-related services

**Recommendation:** Update the audit phase documentation to reflect the actual service layer architecture of vkdownloader. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 3 |

## Mandatory Fixes

none

## Advisory Recommendations

- SRV-001: Dead code - AdaptiveThrottle class exported but never used in application
- SRV-002: Dead code - `get_video_duration` and `_parse_target_duration` functions never called
- SRV-003: God class - HLSDownloader contains mixed concerns including segment downloading, retry logic, and process management
- SRV-004: CLI directly accesses private `_progress_manager._state` attribute breaking encapsulation

## Doc Updates Needed

- SRV-005: Missing Task model referenced in audit phase documentation
- SRV-006: Missing service classes referenced in audit phase documentation

---