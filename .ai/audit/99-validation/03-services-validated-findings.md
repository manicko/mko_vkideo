---
name: Phase 03 Audit Findings — Service Layer & Business Logic (Validated)
description: Validated findings from audit of the vkdownloader service layer (VK video downloader).
agent: audit-executor
validator: validator
template: .kilo/commands/audit/phases/03-audit-services.md
status: complete
validated: yes
---

# Phase 03 Audit Findings — Service Layer & Business Logic (Validated)

**Executor:** audit-executor
**Validator:** validator
**Template:** .kilo/commands/audit/phases/03-audit-services.md
**Status:** complete
**Validated:** yes

> Note: The phase description references a Telegram/Google-Sheets codebase (TelegramService, PostProcessor, ImageCache, GSheetsReader, Task model). The actual repository is a VK video downloader. This audit covers the **real** service layer: `HLSDownloader`, `VKVideoExtractor`, `QualitySelector`, `segment_downloader`, `ffmpeg_utils`, `cookies`, `downloader_throttle`, `signal_handlers`, and `HLSDownloadRequest` DTO.

## Runtime Verification Summary

- **R1 — Imports:** `uv run python -c "import ..."` for all 9 service/model modules → `IMPORTS_OK` (exit 0).
- **R2 — Linter/Type:** `uv run ruff check src/vkdownloader/services src/vkdownloader/models` → "All checks passed!" (exit 0). `uv run mypy src/vkdownloader/services src/vkdownloader/models` → "Success: no issues found in 13 source files" (exit 0).
- **R3 — Tests:** `uv run pytest tests -q` → **216 passed**.
- **R4 — Dead code:** `_should_abort_retry` defined at `segment_downloader.py:128` but never called anywhere. `ProgressManager.update()` and `ProgressManager.get_progress()` are only referenced from tests, never from production code.

---

## Findings

### SRV-001: yt-dlp failure → segment-resume fallback is effectively unreachable (partial-file check wrong)

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION (runtime correctness) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** The documented "automatic segment-based resume on failure" (`download_with_ytdlp_with_resume_fallback`, docstring lines 280-285) relies on a partial file being present at the final `output_file` path after yt-dlp fails. The guard at `downloader.py:317-320` is:

```python
validated_output = validate_output_path(output_file, warning=False)
if not validated_output.exists() or validated_output.stat().st_size == 0:
    return None
# Attempt segment resume with fresh token
```

yt-dlp writes the final file to `output_file` only on **successful** completion; during a failed/incomplete download it leaves a temporary `output_file.part` (or `.ytdl`) file and the target `output_file` does **not** exist. Therefore `validated_output.exists()` is `False`, the function returns `None` early, and the segment-resume branch (lines 322-329) is **never reached** for the real yt-dlp failure path. The recovery mechanism that the resume feature depends on is dead in practice.

This is corroborated by the test suite: `tests/test_hls_downloader.py` either mocks `download_with_ytdlp_with_resume_fallback` entirely (line 1006) or tests `download_hls_with_resume` in isolation with pre-created segment dirs (lines 266, 298). No test exercises a real yt-dlp failure leaving a partial at `output_file`, so the gap is unguarded.

**Evidence:**
- `downloader.py:307-333` — retry loop and the `validated_output.exists()` guard.
- `downloader.py:318-320` — early `return None` when the final file is absent.
- `tests/test_hls_downloader.py:1006` — the fallback is mocked, not exercised.
- yt-dlp standard behavior: uses `.part` extension for in-progress downloads; final output only written on completion.

**Impact:** When yt-dlp fails mid-download (network drop, throttle, expired token), the tool reports failure and silently discards the in-progress download. The advertised "resume from last checkpoint" behavior does not occur, wasting bandwidth and forcing a full re-download on the next attempt.

**Recommendation:** Detect the real yt-dlp artifacts (`*.part` / `*.ytdl`) rather than the final `output_file`, or have `_download_with_ytdlp` return the partial path on failure. Base the resume decision on the temporary file's presence/size. Add an integration test that simulates a yt-dlp failure with a leftover `.part` file and asserts the segment resume path is taken.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The `validate_output_path(output_file)` check at lines 317-320 returns early when `output_file` does not exist. yt-dlp's standard behavior is to write partial downloads to `.part` files, not the target path. The segment-resume branch at lines 322-329 is unreachable for real yt-dlp failures. No test exercises this path with real yt-dlp artifacts.
> - **See also:** SRV-002 (related resume logic); docs/reference incorrectly states resume behavior works

---

### SRV-002: `_attempt_segment_resume` discards the partial download then re-downloads from scratch (misleading "resume")

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION (documented behavior mismatch) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** Even when the resume branch is reached, it does not resume — it restarts. `_attempt_segment_resume` unlinks the partial output and launches a brand-new full segment download:

```python
# downloader.py:401-417
downloader.py:402   output_file.unlink()          # delete the partial file
...                 return await download_hls_with_resume(
    HLSDownloadRequest(video_url=..., output_file=output_file, ...)
)   # fresh segments_dir, no reuse of yt-dlp bytes
```

`download_hls_with_resume` (segment_downloader.py:629-697) creates a **new** `.{stem}_segments` directory and downloads every segment from scratch. The bytes yt-dlp had already fetched are thrown away. The function/module docstrings claim "Segment download resumes from last checkpoint" (downloader.py:285), but the yt-dlp→segment fallback never reuses any prior progress — it is a clean restart wrapped in "resume" naming.

**Evidence:**
- `downloader.py:401-417` — `output_file.unlink()` then fresh `download_hls_with_resume`.
- `segment_downloader.py:658-660` — segments_dir is always created fresh per call.
- `downloader.py:267-333` docstring claims resume-from-checkpoint behavior.

**Impact:** Misleading behavior: users expect interrupted downloads to continue from where they stopped. In reality the tool either fails silently (SRV-001) or restarts a full segment download, doubling network usage on a flaky connection. Maintainability risk: the "resume" contract is documented but not implemented, which will confuse future maintainers.

**Recommendation:** Rename `_attempt_segment_resume` to `_attempt_fresh_segment_fallback` and update its docstring to state "Initiates a fresh segment download when yt-dlp fails; does NOT resume partial bytes (yt-dlp partial files cannot be reused in segment pipeline)." Update `download_with_ytdlp_with_resume_fallback` docstring to remove "resumes from last checkpoint" claim. Effort: small. Priority: recommended.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. `output_file.unlink()` at line 402 deletes any partial before calling `download_hls_with_resume`. The segment downloader creates fresh `.{stem}_segments` directories (line 658) and has no mechanism to reuse yt-dlp-partial bytes. The docstring at line 285 claims "resumes from last checkpoint" but the implementation performs a full restart.
> - **See also:** SRV-001 (fallback never reached); SRV-003 (loop continues after unlink)

---

### SRV-003: Resume retry loop re-runs yt-dlp after browser token refresh fails (wasted work, possible redundant browser launches)

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE (operational efficiency) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** In `download_with_ytdlp_with_resume_fallback`, the loop `while retry_count <= MAX_RESUME_RETRIES` (lines 307-333) re-invokes `_download_with_ytdlp` on every iteration. If `_attempt_segment_resume` returns `None` (e.g., browser extraction raised `ExtractionError`/`OSError`, caught at lines 418-419, or `QualityNotAvailableError` re-raised at 420-422), `retry_count` is incremented and the loop calls yt-dlp **again** on the now-deleted output file:

```python
# downloader.py:315-329
retry_count += 1
validated_output = validate_output_path(output_file, warning=False)
if not validated_output.exists() or validated_output.stat().st_size == 0:
    return None                      # reaches here because file was unlinked
# attempt segment resume again -> fails again -> loops
```

Because the partial was unlinked in the previous iteration (SRV-002), the next iteration hits the `return None` guard immediately — but only after yt-dlp has already been re-executed and failed once more. Each failed segment-resume attempt can also trigger a full browser launch (`extract_streams_with_cookies(force_browser=True)`), up to `MAX_RESUME_RETRIES` (3) times, for a recovery path that cannot succeed.

**Evidence:**
- `downloader.py:305-333` — retry loop structure.
- `downloader.py:376-424` — `_attempt_segment_resume` error handling and `unlink()`.
- `downloader.py:63` — `MAX_RESUME_RETRIES = 3`.
- Segment resume returns `None` on `ExtractionError`/`OSError` (lines 418-419).

**Impact:** On a recovery-failure scenario the tool launches the browser and runs yt-dlp repeatedly (up to 3×) before giving up, wasting time and triggering multiple headless-browser sessions. Degrades UX on flaky networks and increases detectability footprint.

**Recommendation:** Break the loop (or `return None`) immediately when `_attempt_segment_resume` returns `None`, instead of re-running yt-dlp. Distinguish "retryable yt-dlp failure" from "irrecoverable segment-resume failure". Effort: small. Priority: recommended.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. When `_attempt_segment_resume` returns `None` (extraction failure), the loop increments `retry_count` and calls `_download_with_ytdlp` again. Since `output_file.unlink()` was called in SRV-002, the subsequent partial-file check fails, but yt-dlp has already been re-executed before this check. No early exit on irrecoverable segment-resume failure exists.
> - **See also:** SRV-001, SRV-002 (root cause of this behavior)

---

### SRV-004: Dead code — `_should_abort_retry` defined but never called

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE (dead code) |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | advisory |

**Description:** `_should_abort_retry` (segment_downloader.py:128) is defined but has zero call sites anywhere in the repository (verified via repo-wide grep). It is a vestige of an earlier retry/backoff design that was superseded by `_check_backoff_before_attempt` / `_run_parallel_download_with_backoff`.

```python
# segment_downloader.py:128-132
def _should_abort_retry(
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
    shutdown_event: asyncio.Event,
) -> bool:
    return backoff_coordinator is not None and video_url is not None
```

**Evidence:**
- `segment_downloader.py:128` — sole definition; no references in `src/` or `tests/`.
- grep across entire repository found only the definition itself.

**Impact:** Minor. Dead code adds reader confusion about the actual control flow of the retry path and is carried by the linter/type-checker for no benefit.

**Recommendation:** Remove `_should_abort_retry`, or (if it is intended future proofing) document its purpose per the project's dead-code policy. Effort: trivial. Priority: recommended.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via grep search across `/src` directory. No call sites found. The function body at lines 128-132 is dead code, never invoked. The active backoff logic uses `_check_backoff_before_attempt` (line 135) and `_run_parallel_download_with_backoff` (line 143) instead.
> - **See also:** —

---

### SRV-005: `ProgressManager.update()` / `get_progress()` are test-only; documented thread-safety model is inconsistent

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION (documentation inconsistency) |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `ProgressManager` exposes two write/read paths:
- `update_sync()` — direct assignment, no lock, documented as safe *only* because "these callbacks execute sequentially in the single-threaded asyncio event loop" (cli.py:36-43, downloader_throttle.py:102-117).
- `update()` — async, `asyncio.Lock`-protected.
- `get_progress()` — async, `asyncio.Lock`-protected.

Grep confirms `update()` and `get_progress()` are referenced **only from tests** (`tests/test_downloader_throttle.py`), never from production code. The production path calls `update_sync()` (cli.py:43). The class docstring (downloader_throttle.py:78-85) claims the async lock "protects the read path in `get_formatted_progress()`", but `get_formatted_progress` uses its own lock acquisition and does not call `get_progress()`. So the lock-protected async API is effectively unused in production, while the single-threaded assumption it relies on is never validated against the one place a real thread is used — `_download_with_ytdlp` runs yt-dlp in a `run_in_executor` thread (downloader.py:494-511) — which does **not** invoke the progress callback, so the assumption currently holds by accident, not by design.

**Evidence:**
- `downloader_throttle.py:91-150` — `update`/`get_progress` definitions.
- `cli.py:36-43, 43` — only `update_sync` used in production.
- `tests/test_downloader_throttle.py:664, 673-674, etc.` — test-only usage of `update` and `get_progress`.
- `downloader.py:494-511` — yt-dlp runs in an executor thread (no progress callback).

**Impact:** Misleading API surface: a thread-safe async interface exists but is dead in production, while the safety of `update_sync` depends on an unstated, untested invariant. A future change that wires a progress callback into the yt-dlp executor thread would silently introduce a data race on `_state`.

**Recommendation:** Either remove the unused async `update`/`get_progress` (keep only the path actually used) or add a guard/test asserting `update_sync` is never called from a non-event-loop thread. Document the threading contract explicitly. Effort: small. Priority: recommended.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type was BEST-PRACTICE but the class docstring makes explicit claims about thread-safety that are incorrect (`get_formatted_progress` does not call `get_progress`, so the lock does not "protect the read path"). This is a documentation inconsistency — the code is correct but the docstring is misleading.
> - **See also:** —

---

### SRV-006: SIGINT does not stop the blocking yt-dlp thread; shutdown is best-effort

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE (operational reliability) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `_download_with_ytdlp` runs yt-dlp inside `loop.run_in_executor(None, _download)` (downloader.py:494-511). On `CancelledError` the code cancels the *asyncio task* (download_task.cancel()) but the comment at lines 504-505 explicitly admits: "the thread will continue, it will be cleaned up when the process exits or on subsequent runs."

```python
# downloader.py:502-508
except asyncio.CancelledError:
    if not download_task.done():
        download_task.cancel()   # cancels the future, NOT the yt-dlp thread
    raise
```

`download_task.cancel()` on a future wrapping `run_in_executor` does not interrupt the worker thread; yt-dlp keeps writing to disk (and to `output_file`/`.part`) after the user presses Ctrl+C. The partial bytes are then either left on disk or overwritten on the next run. This interacts with SRV-001: because yt-dlp's partial is a `.part` (not `output_file`), the tool neither resumes it nor reliably cleans it up on interrupt.

**Evidence:**
- `downloader.py:494-511` — executor thread + acknowledged non-cancellation.
- `downloader.py:504-505` — comment acknowledging the limitation.

**Impact:** On Ctrl+C, downloads continue in the background, leaving `.part` files and consuming bandwidth; the process may not exit cleanly until yt-dlp finishes. Affects operational reliability and user trust in the cancel action.

**Recommendation:** Signal the worker thread to abort (e.g., a per-download threading.Event checked inside the yt-dlp progress hook, or `ydl.post_process`/`_download` loop), and remove the partial `.part` in a `finally` on cancellation. Effort: medium. Priority: recommended.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The comment at lines 504-505 explicitly acknowledges the thread cannot be cancelled. `download_task.cancel()` only cancels the asyncio future, not the underlying worker thread. yt-dlp continues running in the thread pool after SIGINT.
> - **See also:** SRV-001 (partial file handling); SRV-002 (cleanup on interrupt)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 3 |

## Mandatory Fixes

- **SRV-001** (HIGH): yt-dlp failure → segment-resume fallback is unreachable due to wrong partial-file detection (checks final `output_file`, but yt-dlp leaves a `.part`).

## Advisory Recommendations

- **SRV-002** (MEDIUM): Rename `_attempt_segment_resume` to `_attempt_fresh_segment_fallback`; remove misleading 'resumes from last checkpoint' claims in docstrings.
- **SRV-003** (MEDIUM): resume loop re-runs yt-dlp after irrecoverable segment resume — break early on `None`.
- **SRV-004** (LOW): dead code `_should_abort_retry`.
- **SRV-005** (LOW): unused thread-safe `ProgressManager.update`/`get_progress`; threading contract unstated.
- **SRV-006** (LOW): SIGINT does not stop the yt-dlp executor thread.

## Doc Updates Needed

- **SRV-001 / SRV-002**: docs/reference text describing "resume from last checkpoint" should be corrected to match actual behavior (fresh segment fallback, or real resume once SRV-001/SRV-002 are fixed).
- **SRV-005**: docstring claim that the async lock "protects the read path" should be corrected or removed.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | SRV-001, SRV-002, SRV-003, SRV-004, SRV-006 |
| Reclassified | 1 | SRV-005: BEST-PRACTICE → SPEC-DEVIATION (docstring inaccuracy) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | — |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SRV-005 | BEST-PRACTICE | SPEC-DEVIATION | The docstring makes explicit thread-safety claims ("async lock protects the read path in `get_formatted_progress`") that are factually incorrect — `get_formatted_progress` uses its own lock and never calls `get_progress()`. This is a documentation inconsistency where code behavior does not match documented claims. |

---

## Rollout Safety Analysis

No rollout safety issues detected. These findings are isolated to the service layer and can be addressed independently:

1. **SRV-001** and **SRV-002** are related but can be fixed together — both involve the ytdlp→segment fallback logic
2. **SRV-003** is a minor optimization that can be applied after SRV-001/SRV-002 fixes
3. **SRV-004** (dead code removal) has no backward compatibility concerns
4. **SRV-005** (docstring fix) is documentation-only
5. **SRV-006** (thread cancellation) is isolated to the yt-dlp download path

No circular dependencies or hidden dependency chains identified between these findings.