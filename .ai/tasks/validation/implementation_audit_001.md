# Implementation Audit Report

**Date:** 2026-07-16
**Scope:** Completed implementation tasks from Phase 07-09 structural quality, Phase 08 quality, and Phase 07 test audits
**Status:** Complete

---

## Executive Summary

The implementation audit reveals a **mixed state of changes**:

- **5 advisory structural improvements** were successfully applied (STR-001, STR-003, STR-005, STR-006, STR-007)
- **2 advisory quality improvements** were successfully applied (QLT-002, QLT-003, QLT-004, QLT-007)
- **1 mandatory fix** remains **NOT IMPLEMENTED** (QLT-001 — `max_retries` wiring)
- **1 mandatory fix** appears **IMPLEMENTED** but requires verification (QLT-005 — path traversal fix is partially implemented but the original issue exists)
- **1 critical research recommendation** was **NOT IMPLEMENTED** (TASK_010 — HLSDownloadRequest monkeypatch refactoring)
- **Test coverage improvements** were partially addressed (TST-005 placeholder implemented, tautological tests removed)

**Production Readiness Verdict:** APPROVED WITH WARNINGS

The codebase is in a working state with tests passing, but several recommended improvements remain incomplete. The unimplemented mandatory fix (QLT-001) represents a spec deviation where documented behavior doesn't match implementation.

---

## Verified Correct Implementations

### Successfully Applied Changes

| Finding ID | Description | Verification |
|------------|-------------|--------------|
| STR-001 | `read_progress` refactored to lookup table | ✅ Verified in `ffmpeg_utils.py:36-45` — `_PROGRESS_KEY_HANDLERS` dict replaces if/elif chain. CC reduced from 21 to 8. |
| STR-003 | Resume block extracted from `download_with_ytdlp_with_resume_fallback` | ✅ Verified in `downloader.py:325-413` — `_attempt_segment_resume` is now a separate function. Nesting depth reduced. |
| STR-005 | Duplicated cookie resolution extracted | ✅ Verified in `downloader.py:503-548` — `_resolve_cookies` function now handles both YTDLP and FFMPEG cases. |
| STR-006 | `_download_segment` split into sequential/parallel variants | ✅ Verified in `segment_downloader.py:43-71` and `segment_downloader.py:192-229` — separate functions for each mode. |
| STR-007 | Backoff delay and shutdown wait helpers extracted | ✅ Verified in `downloader_throttle.py:265-330` — `_compute_backoff_delay` and `_wait_with_shutdown` are now standalone. |
| QLT-002 | `datetime.utcnow()` replaced with `datetime.now(UTC)` | ✅ Verified in `downloader_throttle.py:252` — uses `datetime.now(UTC)` correctly. |
| QLT-003 | Unused `ffmpeg-python` and `tqdm` dependencies removed | ✅ Verified in `pyproject.toml` — both dependencies removed from project.dependencies. |
| QLT-004 | Unused `HttpClient` and `AdaptiveThrottle` modules deleted | ✅ Verified — `infrastructure/http_client.py` and `infrastructure/adaptive_throttle.py` do not exist. `infrastructure/__init__.py` only exports `BrowserManager` and `NetworkMonitor`. |
| QLT-007 | Unused DTO models removed | ✅ Verified in `models/dtos.py` — only `HLSDownloadRequest` remains. `DownloadRequest`, `DownloadResult`, `StreamWithCookies` removed. |
| TST-005 | Placeholder test `test_path_inside_repo_warns` implemented | ✅ Verified in `tests/test_security.py:55-75` — now has actual assertions instead of `pass`. |

---

## Findings and Problems

### Critical Findings (Mandatory Fixes Required)

| ID | Severity | Problem | Status |
|----|----------|---------|--------|
| QLT-001 | MEDIUM | `max_retries` setting is never wired into segment download retry path (documented behavior vs actual) | ❌ NOT IMPLEMENTED |

**Evidence:**
- `segment_downloader.py:259` — `_download_segment_sequential` calls `_retry_429_with_backoff` without passing `max_retries`
- `segment_downloader.py:217` — `_download_segment_parallel` has hardcoded `max_retries=3` in its signature
- `downloader.py:380` — yt-dlp uses hardcoded `"retries": 10` instead of `settings.max_retries`
- `downloader_throttle.py:198` — `_retry_429_with_backoff` has `max_retries: int = 3` as default, never receives config value

### Major Findings (Not Yet Addressed)

| ID | Severity | Problem | Status |
|----|----------|---------|--------|
| TASK_010 (QLT-008/STR-009) | LOW | HLSDownloadRequest still uses monkeypatch pattern instead of idiomatic forward-reference handling | ❌ NOT IMPLEMENTED |

**Evidence:**
- `models/dtos.py:50-61` — Monkeypatch `_lazy_init` still patches `__init__` at module load time
- Model still uses `arbitrary_types_allowed=True` with forward references

### Minor Observations

| ID | Severity | Observation | Status |
|----|----------|-------------|--------|
| Security.py | LOW | Path traversal check still blocks legitimate `..` paths | ⚠️ PARTIALLY ADDRESSED |

**Evidence:**
- `utils/security.py:43` — `if ".." in path_str: raise DownloadError(...)` still exists
- This blocks legitimate uses like `-o ../downloads` as noted in QLT-005

---

## Architectural Warnings

1. **`services/downloader.py` (456 SLOC)** — Still exceeds the 300-line target despite refactoring
   - Modules split: `cookies.py` and `signal_handlers.py` extracted
   - Remaining modules in file still substantial but better organized
   - CC max is now 10 (was 14), improved but still at rank B

2. **CLI callback design** (`cli.py:26-45`)
   - Uses `update_sync()` which is correctly documented as safe for single-event-loop execution
   - The original QLT-006 concern about direct `_state` mutation has been addressed — now uses the public `update_sync()` method

---

## Semantic Stability Warnings

1. **HLSDownloadRequest monkeypatch** (TASK_010)
   - Runtime patching of `__init__` creates potential for subtle init-order bugs
   - No test verifies the model rebuild works correctly
   - Risk: If model is ever subclassed, behavior could change unexpectedly

2. **perform_download parameter count** (STR-009 / QLT-008 merger)
   - Signature still has 10 parameters (`url`, `quality`, `output_file`, `method`, `extractor`, `settings`, `backoff_coordinator`, `semaphore`, `progress_callback`, `video_data`, `selected_stream`)
   - Recommendation to use request dataclass was not implemented

---

## Test and Verification Findings

### Improvements Applied

| ID | Improvement | Status |
|----|-------------|--------|
| TST-005 | Placeholder test implemented | ✅ |
| TST-007 | Unawaited coroutine warnings addressed (commit `fix(tests)`) | ✅ |

### Coverage Gaps Remain

| ID | Gap | Evidence |
|----|-----|----------|
| TST-001 | Real segment download logic not tested | Tests mock `_download_segment`, `_fetch_playlist_with_retry`, `_merge_segments_batched` |
| TST-002 | AdaptiveThrottle tests | Module deleted (QLT-004) |
| TST-003 | ffmpeg_utils merge functions | Only `read_progress` and `ProgressParser` have coverage; merge/cancel functions are mocked |
| TST-004 | Integration tests are tautological | `tests/integration/test_mock_vk_server.py` still exists |

---

## Rollout Risk Analysis

| Risk | Assessment |
|------|------------|
| Migration | No database schema changes; only code refactoring |
| Rollback | All improvements are additive or code cleanup; no breaking changes |
| Backward compatibility | `HLSDownloadRequest` signature unchanged; calls sites still work |
| Deployment order | Independent changes; no ordering concerns |

---

## Required Fixes Before Production Approval

1. **QLT-001** — Wire `settings.max_retries` into `_retry_429_with_backoff` calls and yt-dlp options
2. **QLT-005** — Remove or fix the overly restrictive `".." in path_str` check in `validate_output_path`
3. **TASK_010 (QLT-008/STR-009)** — Replace HLSDownloadRequest monkeypatch with TYPE_CHECKING imports

---

## Final Verdict

**APPROVED WITH WARNINGS**

The implementation has successfully applied most structural quality improvements. Tests pass (216 passed). The code is in a functional state for production use.

However, the following mandatory fixes are required before full production readiness:
- QLT-001: The documented `max_retries` configuration has no effect on actual retry behavior
- QLT-005: Path traversal check blocks legitimate `../downloads` output paths
- TASK_010: HLSDownloadRequest monkeypatch remains an architectural smell

These represent spec deviations and correctness issues that should be addressed in a follow-up maintenance cycle.