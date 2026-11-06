# Block G Audit Findings — retry state machine (commit 2cc3fa4)

**Author:** auditor
**Validated by:** not run
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no
**Commit measured:** 2cc3fa43ef3495cff13db6f3520801d2d0257008
**Working-tree state:** dirty
**Dirty paths:** .ai/plans/01-MKO_VKIDEO_Refactoring_Execution.md, .ai/audit/block_f.md, .ai/tasks/task_F_quality_refresh.yaml, .ai/tasks/task_G_retry_state_machine.yaml

## Verification performed

- `uv run pytest tests/test_download_state.py tests/test_ytdlp_downloader.py -q` -> 29 passed.
- `uv run pytest tests/test_packaging.py -q` -> 14 passed.
- `uv run ruff check src tests` -> All checks passed.
- `uv run ruff format --check src tests` -> 69 files already formatted.
- `git diff --check` -> no whitespace errors.
- `uv run pytest -q` -> 39 failed, 1188 passed, 5 skipped. The 39 failures are pre-existing on base commit b82911c (identical set; not introduced by Block G).
- `uv run mypy src` -> 36 errors (base b82911c: 28). Block G introduces 8 new explicit-`Any` errors in `src/vkdownloader/services/state_machine.py` and `src/vkdownloader/services/segment_downloader.py`.
- Secret-safety check: `tests/test_no_secrets_persisted` passes; persisted `state.json` contains no token/cookie/signed-URL fields; `retry_scheduled`/`refresh_requested` log payloads contain only job id, attempt id, scope, reason code, and delay.

## Findings

### BG-001: State machine is plumbed but does not own retries, budget, cancellation, or disk-full

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection of `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, and `src/vkdownloader/services/segment_downloader.py`: `state_machine` is threaded through signatures and created/loaded, but `record_retry`, `is_budget_exhausted`, `record_cancellation`, `record_disk_full`, `classify_error`, and `transition` are never invoked outside `state_machine.py`. The yt-dlp outer loop still uses `while retry_count <= settings.max_retries` and segment resume runs independently.
> - **See also:** BG-005

| Field | Value |
|-------|-------|
| **ID** | BG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/state_machine.py, src/vkdownloader/services/ytdlp_downloader.py, src/vkdownloader/services/segment_downloader.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** Block G's acceptance criteria require a single combined retry budget, observable state transitions, and cancellation/disk-full terminal states. The implementation adds the `DownloadStateMachine` and `retry_policies` modules and lowers yt-dlp's internal `-R`/`--fragment-retries` to `1`, but the download paths do not consult `is_budget_exhausted()` or call `record_retry()`, `record_cancellation()`, `record_disk_full()`, `classify_error()`, or `transition()`. As a result the combined budget is not enforced, state remains `created` for the whole run, and cancellation/disk-full are not recorded as terminal states. The state machine is currently a passive sidecar rather than the owner of retry behaviour.

**Evidence:** `grep`/`Select-String` over `src/` shows `record_retry`, `is_budget_exhausted`, `record_cancellation`, `record_disk_full`, and `classify_error` defined only in `src/vkdownloader/services/state_machine.py`. In `src/vkdownloader/services/ytdlp_downloader.py` the outer loop is still `while retry_count <= settings.max_retries:` (default 3) and calls `_attempt_segment_resume` on each failure without a budget check.

**Recommendation:** Wire the state machine into the yt-dlp outer loop and segment path: call `classify_error` on failures, `record_retry` before each retry (and stop when it returns `False`, transitioning to `FAILED_RETRY_BUDGET`), `record_cancellation` on shutdown, and `record_disk_full` on `OSError`/`DownloadError` disk-full conditions. Advance states via `transition()` on each phase change. If the full wiring is deferred, document the module as scaffolding and do not claim the combined budget is enforced.

---

### BG-002: Refresh completion is recorded as a perfect match unconditionally

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `src/vkdownloader/services/segment_downloader.py` calls `state_machine.record_refresh_completed(quality_match=True, variant_match=True)` immediately after a successful token refresh, without comparing the refreshed binding's variant/height against the preselected identity.
> - **See also:** BG-001

| Field | Value |
|-------|-------|
| **ID** | BG-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/state_machine.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** After a 403/410 token refresh succeeds, the code records `quality_match=True` and `variant_match=True` regardless of whether the refreshed playlist/variant actually matches the previously verified one. This defeats the Block F goal of preserving exact requested quality across refresh and makes the state machine's refresh log misleading.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines ~979-983:
```python
if state_machine is not None:
    try:
        state_machine.record_refresh_completed(
            quality_match=True, variant_match=True
        )
    except Exception:  # noqa: BLE001
        pass
```

**Recommendation:** Compare the refreshed binding's `variant_id`/`actual_height` against the preselected values and pass the real booleans to `record_refresh_completed`. On a mismatch, do not continue silently; raise or transition to `PRESERVE_AND_STOP`/`INTEGRITY_FAILED` as appropriate.

---

### BG-003: Refresh cap can be bypassed on exception and is absent when no state machine exists

> **Validation Note:**
> - **Action:** validated
> - **Detail:** In `_fetch_playlist_with_retry`, `request_refresh` is guarded by `if state_machine is not None`, and its `except Exception: pass` swallows failures and falls through to the refresh path. A state machine is created with `workspace=None` at function entry, so the cap works in-memory in that path, but any exception in `request_refresh` silently disables it.
> - **See also:** BG-001

| Field | Value |
|-------|-------|
| **ID** | BG-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/state_machine.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** The refresh cap is the only Block G limit actually consulted in the download paths, but its enforcement is fragile: an exception from `request_refresh` is swallowed and execution proceeds to refresh anyway, and the cap is skipped entirely when `state_machine is None`. This can allow unlimited token re-extraction under error conditions.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines ~937-944:
```python
if state_machine is not None:
    try:
        if not state_machine.request_refresh("token_expired"):
            return None
    except Exception:  # noqa: BLE001
        pass
```

**Recommendation:** Treat a failed `request_refresh` as "refresh not allowed" and return `None` instead of swallowing it. Ensure every call path that can refresh has a non-None state machine (or apply the cap independently of the state machine).

---

### BG-004: Corrupt state file is silently overwritten, losing progress counters

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `DownloadStateMachine.load` catches any exception and returns a state with `job_id="unknown"`; `downloader.py` then falls back to `DownloadStateMachine.create`, which persists a fresh state and overwrites the unreadable file.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BG-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/state_machine.py, src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** If `state.json` exists but is corrupt or from an incompatible schema, `load` discards it and `create` overwrites it on the next persist. This loses any recoverable progress counters (`verified_segments`, `attempt_id`, `refresh_count`, etc.) and hides the corruption from operators.

**Evidence:** `src/vkdownloader/services/state_machine.py` `load()`:
```python
try:
    data = json.loads(path.read_text(encoding="utf-8"))
    job_state = DownloadJobState.model_validate(data)
except Exception:  # noqa: BLE001
    job_state = DownloadJobState(job_id="unknown")
```
and `src/vkdownloader/services/downloader.py` fallback:
```python
state_machine = DownloadStateMachine.create(
    job_id=workspace.root.name, quality_requested=quality, workspace=workspace
)
```

**Recommendation:** Preserve the corrupt file (rename to `.corrupt` or back it up) before overwriting, log a warning with the parse error, and only then create a fresh state. Consider schema-version migration instead of hard failure on extra fields.

---

### BG-005: State-machine mutation helpers do not persist or self-transition

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `record_retry` returns `False` when the budget is exhausted but neither transitions to `FAILED_RETRY_BUDGET` nor persists that decision. `record_cancellation` and `record_disk_full` set flags but persist only when a transition succeeds; `observe_throughput` and the counter helpers (`increment_verified_segment`, `set_network_bytes`, `set_fragment_progress`) never persist.
> - **See also:** BG-001

| Field | Value |
|-------|-------|
| **ID** | BG-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/state_machine.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** The state machine's mutation helpers update in-memory fields but leave persistence and terminal transitions to callers. Because the callers do not invoke them today (BG-001), even a future wiring would require every caller to remember to persist and transition. Making the helpers self-contained would reduce the chance of a partially updated state file.

**Evidence:** `record_retry` ends with `self.persist() if self.workspace is not None else None` and returns `False` on exhaustion without transitioning. `record_cancellation`/`record_disk_full` call `persist()` only inside `transition()`, which is skipped when `can_transition` is false. `observe_throughput`, `increment_verified_segment`, `set_network_bytes`, and `set_fragment_progress` never call `persist()`.

**Recommendation:** When `record_retry` exhausts the budget, transition to `FAILED_RETRY_BUDGET` (if allowed) and persist. Have `record_cancellation`/`record_disk_full` persist the flag even when no state transition occurs. Persist in the counter helpers (or document that callers must persist after batching updates).

---

### BG-006: Block G introduces mypy strict-mode violations

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `uv run mypy src` reports 36 errors vs 28 on base b82911c; the 8 new errors are explicit `Any` in `state_machine.py` (constructor, `create`, `load`, `transition`, `classify_error`, and `workspace`/`error` parameters) and `segment_downloader.py` (`state_machine: Any`).
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BG-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/state_machine.py, src/vkdownloader/services/segment_downloader.py |
| **Classification** | advisory |
| **Verification** | observed |

**Description:** The project config enables `disallow_any_explicit = true`. Block G adds `Any`-typed parameters and return-related annotations in the new module and in the segment downloader signature, so the strict type gate fails. This is a quality regression even though the runtime tests pass.

**Evidence:** `uv run mypy src`:
```
src/vkdownloader/services/state_machine.py:94: error: Explicit "Any" is not allowed  [explicit-any]
src/vkdownloader/services/state_machine.py:137: error: Explicit "Any" is not allowed  [explicit-any]
src/vkdownloader/services/state_machine.py:149: error: Explicit "Any" is not allowed  [explicit-any]
src/vkdownloader/services/state_machine.py:168: error: Explicit "Any" is not allowed  [explicit-any]
src/vkdownloader/services/state_machine.py:196: error: Explicit "Any" is not allowed  [explicit-any]
src/vkdownloader/services/state_machine.py:223: error: Explicit "Any" is not allowed  [explicit-any]
src/vkdownloader/services/state_machine.py:258: error: Explicit "Any" is not allowed  [explicit-any]
src/vkdownloader/services/segment_downloader.py:824: error: Explicit "Any" is not allowed  [explicit-any]
```

**Recommendation:** Replace explicit `Any` with concrete types (`object`, `DownloadWorkspace | None`, `DownloadJobState | dict[str, object]`, etc.) or introduce a `Protocol` for the workspace/state-machine dependencies. Keep `Any` only behind typed boundaries that ruff/mypy already allow.

---

### BG-007: State-machine identity uses raw paths/URLs

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `DownloadStateMachine.create` is called with `job_id=str(output_file)` in `ytdlp_downloader.py` and `job_id=video_url or "job"` in `segment_downloader.py`. These values are persisted in `state.json` and used in log lines.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BG-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/ytdlp_downloader.py, src/vkdownloader/services/segment_downloader.py, src/vkdownloader/services/state_machine.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** Job identity is derived from a full output path or a page URL. While not a secret by itself, this leaks local filesystem paths and page URLs into the persisted state file and structured logs, and makes state files non-portable. The rest of the codebase already has `stable_job_id` for this purpose.

**Evidence:** `src/vkdownloader/services/ytdlp_downloader.py`:
```python
state_machine = DownloadStateMachine.create(
    job_id=str(output_file), quality_requested=quality, workspace=workspace
)
```
`src/vkdownloader/services/segment_downloader.py`:
```python
state_machine = DownloadStateMachine.create(job_id=video_url or "job", workspace=None)
```

**Recommendation:** Use `stable_job_id(video_id, quality, final_basename)` (or a similarly sanitized, bounded identifier) for `job_id`, and keep paths/URLs out of the persisted state and log payloads. Continue to sanitize URLs in logs via `_strip_auth_params`.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 3 |

## Mandatory Fixes

- BG-001: Wire the state machine into the download paths so the combined retry budget, cancellation, disk-full, and error classification are actually enforced and state transitions are recorded.
- BG-002: Record real refresh quality/variant match results instead of hardcoding `True`.
- BG-003: Do not swallow `request_refresh` failures or skip the cap when no state machine is present.
- BG-004: Preserve corrupt/unreadable state files before overwriting them.

## Advisory Recommendations

- BG-005: Make mutation helpers persist and self-transition (exhaustion -> `FAILED_RETRY_BUDGET`).
- BG-006: Remove explicit `Any` to satisfy strict mypy.
- BG-007: Sanitize `job_id` derivation using the existing `stable_job_id` helper.

## Doc Updates Needed

none
filePath">
C:\py_exp\mko_vkideo\.ai\audit\block_g.md