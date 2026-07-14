---
name: 03-services
description: Service Layer & Business Logic
executor: validator
status: complete
validated: yes
---

# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** validator (validated from auditor findings)
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes

---

## Findings

### SRV-001: ~~Dead code - AdaptiveThrottle class exported but never used in application~~ [REJECTED]

> **Rejection reason:** The `AdaptiveThrottle` class (lines 11-66 in `infrastructure/adaptive_throttle.py`) is exported in `__init__.py` but not actively used in the download flow. However, it is listed in the codebase structure maps (`.ai/structure/back/py_anchors.yaml` and `.ai/structure/back/py_map.yaml`) indicating architectural intent. Per project rules on dead code: when a component appears in documentation/spec but is unused, it should be classified as SPEC-DEVIATION (missing integration) rather than dead code. However, this component has no spec documentation—only code intent. The class provides a valid rate limiting strategy alternative that could be used in future. Recommendation is valid but classification as dead code is premature.

### SRV-002: Dead code - `get_video_duration` and `_parse_target_duration` functions never called

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py:578-622 |
| **Classification** | mandatory |

**Description:** The functions `get_video_duration` (line 578) and `_parse_target_duration` (line 607) in `downloader.py` are defined to retrieve video duration but are never called anywhere in the codebase outside their definitions. `get_video_duration` attempts to run ffprobe on an m3u8 URL which is unlikely to work as intended (ffprobe typically needs a media file, not a playlist URL).

**Evidence:**
- `downloader.py:578-604` defines `get_video_duration` function
- `downloader.py:607-622` defines `_parse_target_duration` function
- PowerShell `Select-String` search confirms no calls to these functions outside their definitions
- The `FfmpegProgress` dataclass (lines 36-47) does not include duration tracking

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type was BEST-PRACTICE. Reclassified as SPEC-DEVIATION because dead code without spec reference indicates incomplete implementation—code was written but never integrated. Per project rules: "If the spec, models, or config reference the component → reject the 'dead code' label and reclassify as SPEC-DEVIATION (missing integration, not dead code)." Since there is no spec reference but the code exists in the codebase, this represents unfinished implementation rather than opportunistic cleanup.
> - **See also:** —

**Recommendation:** Remove both functions as dead code. If duration tracking is desired, implement it properly using ffprobe on the final MP4 file rather than the m3u8 playlist. Effort: trivial. Priority: mandatory.

---

### SRV-003: God class - HLSDownloader contains mixed concerns including segment downloading, retry logic, and process management

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py:162-818 |
| **Classification** | mandatory |

**Description:** The `HLSDownloader` class and the module-level functions in `downloader.py` violate single responsibility by combining multiple concerns: (1) ffmpeg command building and execution, (2) segment-level download orchestration, (3) HLS playlist fetching with retry, (4) yt-dlp download wrapper, (5) segment merging logic, (6) progress tracking, and (7) signal handling for shutdown. The module has 1130 lines with 31 functions/methods.

**Evidence:**
- Module contains: `HLSDownloader` class (download orchestration), `ProgressParser` class (parsing), `FfmpegProgress` dataclass
- Module-level functions: `read_progress`, `cancel_ffmpeg_process`, `download_hls_with_resume`, `_fetch_playlist_with_retry`, `_download_segment`, `_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `_load_downloaded_count`, `_save_downloaded_count`, `_cleanup_segments`, `_cancel_all_downloads`, `setup_signal_handlers`, `download_with_ytdlp_with_resume_fallback`, `_download_with_ytdlp`, `perform_download`
- All these are in a single 1130-line file
- Project rule #5 mandates: "Small modules and functions give higher ROI in maintenance"

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type was BEST-PRACTICE. Reclassified as SPEC-DEVIATION because the codebase violates the explicit project rule: "Small modules and functions give higher ROI in maintenance — they are easier to edit, review, and less prone to corruption." This is an architectural rule violation, not a suggestion.
> - **See also:** QLT-002 (duplicate finding in Phase 08)

**Recommendation:** Consider splitting the module into focused components:
- `ffmpeg_utils.py` - ffmpeg command building and process management
- `segment_downloader.py` - segment download orchestration and merging
- Effort: medium. Priority: mandatory (per project rules).

---

### SRV-004: ~~CLI directly accesses private `_progress_manager._state` attribute breaking encapsulation~~ [REJECTED]

> **Rejection reason:** This is intentional design documented in ProgressManager class docstring (downloader_throttle.py:84-91). The code explicitly states: "Direct tuple assignment to `_state[url_index]` is GIL-atomic in CPython, providing safe fire-and-forget semantics for progress callbacks invoked from async tasks. The async lock protects the read path in get_formatted_progress, ensuring consistent reads while callbacks may write concurrently." This is a valid concurrency pattern that avoids blocking in sync callbacks. The pattern is consistent with CLI-004 which was also rejected in Phase 01 validation.

---

### SRV-005: Missing Task model referenced in audit phase documentation

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | .kilo/commands/audit/phases/03-audit-services.md |
| **Classification** | advisory |

**Description:** The audit phase documentation references a `Task` model with fields `chat_id, topic_id, text, photos, chat_name, count, max_count` and status tracking. This model does not exist in the vkdownloader project. The documentation appears to be copied from a different project (Telepost) and does not match the actual codebase architecture.

**Evidence:**
- No `task.py` file exists in `src/vkdownloader/models/`
- Grep search finds no `Task` model definition in the codebase
- The referenced attributes (chat_id, topic_id, text, photos) are Telegram/posting related, not video downloading related

> **Validation Note:**
> - **Action:** confirmed
> - **Detail:** Valid DOC-UPDATE. The audit phase template references components from a different project. This is a documentation mismatch issue.
> - **See also:** INT-001, CFG-003 (same root cause - copied templates)

**Recommendation:** Update the audit phase documentation to reflect the actual models: `Video`, `Stream`, `VideoWithStreams`, `DownloadProgress`, `DownloadRequest`, `HLSDownloadRequest`, `DownloadResult`. Effort: trivial. Priority: recommended.

---

### SRV-006: Missing service classes referenced in audit phase documentation

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | .kilo/commands/audit/phases/03-audit-services.md |
| **Classification** | advisory |

**Description:** The audit phase documentation references `TelegramService`, `PostProcessor`, `ImageCache`, `TelegramPoster`, and `GSheetsReader` service classes that do not exist in the vkdownloader project.

**Evidence:**
- No `telegram.py`, `post_processor.py`, `image_cache.py`, `gsheets_reader.py` files exist in `src/vkdownloader/services/`
- Only `downloader.py`, `quality.py`, `extractor.py`, `downloader_throttle.py` exist as services
- Grep search confirms no references to Telegram-related services

> **Validation Note:**
> - **Action:** confirmed
> - **Detail:** Valid DOC-UPDATE. Same root cause as SRV-005 - the audit phase template was copied from a different project.
> - **See also:** SRV-005

**Recommendation:** Update the audit phase documentation to reflect the actual service layer architecture of vkdownloader: `HLSDownloader`, `QualitySelector`, `VKVideoExtractor`, `HttpClient`, `BrowserManager`, `NetworkMonitor`, `URLBackoffCoordinator`, `ProgressManager`, and `AdaptiveThrottle`. Effort: trivial. Priority: recommended.

---

## Cross-Phase Conflict Detected

**SRV-002 and QLT-002 are duplicate findings** describing the same god module issue in `downloader.py`. Both phases correctly identify the architectural problem but QLT-002 is more comprehensive.

### Cross-Phase Dependencies

| Finding | Depends On | Notes |
|---------|------------|-------|
| SRV-001 | — | Standalone removal decision |
| SRV-002 | QLT-002 | Both address the same module size issue |
| SRV-005 | INT-001, CFG-003 | All stem from copied audit templates |
| SRV-006 | INT-001, CFG-003 | All stem from copied audit templates |

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 0 | — |
| Reclassified | 2 | SRV-002 (BEST-PRACTICE→SPEC-DEVIATION), SRV-003 (BEST-PRACTICE→SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 2 | SRV-001 (not dead code), SRV-004 (intentional concurrency design) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| SRV-001 | Dead code - AdaptiveThrottle class exported but never used | Code exists in architecture maps indicating intent; not true dead code per project rules |
| SRV-004 | CLI directly accesses private `_progress_manager._state` attribute | Intentional GIL-atomic write design documented in ProgressManager; valid pattern |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SRV-002 | BEST-PRACTICE | SPEC-DEVIATION | Unreferenced code without spec reference indicates incomplete implementation, violating project's "problems-only" rule against speculative dead code removal without proper classification |
| SRV-003 | BEST-PRACTICE | SPEC-DEVIATION | Violates explicit project rule #5: "Small modules and functions give higher ROI in maintenance" |

### Documentation Issues (Cross-Phase)

| Issue | Root Cause |
|-------|------------|
| SRV-005 | Audit template copied from Telepost project |
| SRV-006 | Audit template copied from Telepost project |
| INT-001 | Audit template copied from Telepost project |
| CFG-003 | Audit template copied from Telepost project |

---

## Rollout Analysis

- SRV-002 (dead code removal) can be executed independently
- SRV-003 (module split) has medium complexity; should coordinate with QLT-002 if addressed
- SRV-005 and SRV-006 are documentation-only fixes
- No circular dependencies detected
- No rollout conflicts between findings

---

## Remaining Issues After Validation

| ID | Issue | Classification |
|----|-------|----------------|
| SRV-002 | Remove unused `get_video_duration` and `_parse_target_duration` functions | Mandatory fix |
| SRV-003 | Split `downloader.py` into smaller modules per project rule #5 | Mandatory fix |
| SRV-005 | Update audit phase documentation to reflect actual models | Documentation update |
| SRV-006 | Update audit phase documentation to reflect actual services | Documentation update |

> **Note:** SRV-001 was rejected - the `AdaptiveThrottle` class should remain as it represents architectural intent. The audit template documentation issues (SRV-005, SRV-006) should be fixed once across all phases.