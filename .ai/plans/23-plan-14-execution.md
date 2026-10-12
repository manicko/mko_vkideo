# Execution plan: Plan 14 code-quality audit — remaining blocks (updated 2026-10-11)

**Source plan:** `.ai/plans/14-code-quality-audit-fixes_fix.md` (13 blocks B1-B13)
**Audit update (§9):** `.ai/audit/problems/14-code-quality-audit-update-2026-10-11.md` (at HEAD `24dcddc` — all blocks NOT DONE except B5/DONE, B6/VOIDED)
**Audit verification (results):** `.ai/audit/problems/14-code-quality-audit-update-2026-10-11-results.md` (at HEAD `56a1854` — 10 blocks DONE, B4 BLOCKED, B6 VOIDED, B13 NOT DONE). **Updated:** B4 committed `723cb16`; B3-FU committed `e4889fe`; B1-README committed `666666d`; B13 escalation posted. All 13 blocks now DONE or VOIDED.
**B4 unblock report:** `.ai/audit/problems/14-b4-unblock-report.md` (P11 gate RESOLVED — plan-renumbering artifact)
**Plan base:** `09f1b10` → **Live HEAD:** `723cb16` + `666666d`

---

## 1. Status Summary

**Already committed (HEAD `723cb16` + `666666d`):**

| Block | Commit | Status |
|-------|--------|--------|
| PREREQ | `44a3c9e` | DONE — fixed EXPECTED_SDIST_ENTRIES (73→69) |
| B1 | `e647fb0` | DONE — shim removed, ErrorCode.NO_STREAMS added |
| B2 | `3655cef` | DONE — VKDownloadError arms added to cli.py |
| B3 | `14c7012` | DONE — disallow_any_explicit enabled, 5 Any removed |
| B5 | `83ba0f8` | DONE — Retry-After floor comment |
| B7 | `4138e84` | DONE — structure maps regenerated |
| B8 | `c7b7dcb` | DONE — overview corrected |
| B9 | `63b020e` | DONE — cli-reference cleaned collapsed |
| B10 | `b0eae7d` | DONE — morfx-tools.md/ast-editor.md relocated |
| B11 | `56a1854` | DONE — dead citations resolved |
| B12 | `1eda62f` | DONE — quality.py import taxonomy documented |
| B4 | `723cb16` | DONE — retry symbols moved to `services/retry_policies.py`; `api-reference.md` corrected |
| B3-FU | `e4889fe` | DONE — format gate GREEN; warning count ≤1; unawaited coroutine fixed |
| B1-README | `666666d` | DONE — stale shim reference removed; `quality_parse_error` status label fixed |
| B13 | — | DONE — VAL-901/VAL-902 escalation posted (no code) |
| B6 | — | **VOIDED** — docs/STRUCT.md deleted by external commit `6ab4a50` |

**All blocks complete:** B1–B13 resolved (B4, B3-FU, B1-README, B13 landed after the prior snapshot). No remaining work.

---

## 2. Key Code Context (from Phase 0 Auditor)

### 2.1 B4 — downloader_throttle.py current state
- **5 retry symbols confirmed present** in `downloader_throttle.py` (447 lines):
  - `RETRYABLE_STATUS_CODES` (L53) — 7-member frozenset `{408, 425, 429, 500, 502, 503, 504}`
  - `_retry_429_with_backoff` (L230) — `async def` with 5 params
  - `_parse_retry_after` (L333) — `def` returning `float | None`
  - `_compute_backoff_delay` (L376) — `def` returning `float`, `max(backoff, retry_after)` floor semantics
  - `_wait_with_shutdown` (L417) — `async def` returning `bool`
- **5 residue symbols stay in downloader_throttle.py:**
  - `get_shutdown_event` (L76)
  - `URLBackoffCoordinator` (L91)
  - `ProgressManager` (L134)
  - `_resource_key` (L56)
  - `_shutdown_event_ctx` (L71)
- Module docstring: `"Throttle utilities for VK Video Downloader with retry logic for rate limiting."` — describes both concerns, needs post-split update

### 2.2 B4 — importers
- **7 residue importers** (must stay unchanged): `cli.py`, `batch_downloader.py`, `downloader.py` (TYPE_CHECKING), `extractor.py`, `segment_downloader.py` (TYPE_CHECKING), `ytdlp_downloader.py` (TYPE_CHECKING), `signal_handlers.py`
- **4 retry-symbol importers** (must update): `segment_downloader.py` (all 5), `ytdlp_downloader.py` (2), `downloader.py` (1, re-export), `tests/test_downloader_throttle.py` (one from-import block)

### 2.3 B4 — patch() string census (15 total)
- **3 MUST REPOINT** (name `downloader_throttle`'s own namespace):
  - `downloader_throttle._wait_with_shutdown` ×3 in `test_downloader_throttle.py:472`, `test_hls_downloader.py:2641`, `test_hls_downloader.py:2806`
- **12 MUST NOT CHANGE** (name importing-module's re-exported attribute):
  - `segment_downloader._retry_429_with_backoff` ×4
  - `segment_downloader._compute_backoff_delay` ×2
  - `segment_downloader._wait_with_shutdown` ×2
  - `ytdlp_downloader._compute_backoff_delay` ×2
  - `ytdlp_downloader._wait_with_shutdown` ×2

### 2.4 B4 — facade defect (downloader.py)
- `services/downloader.py` symbol-ownership comment (L80-107) lists 7 groups, all restored
- **3 names imported but not in `__all__` or comment:** `_attempt_segment_resume` (L49, noqa: F401), `_download_with_ytdlp` (L53), `_is_ytdlp_progress_line` (L55)
- **Live mypy error** at `tests/test_hls_downloader.py:5054`: `Module "vkdownloader.services.downloader" does not explicitly export attribute "_attempt_segment_resume"`
- B4 criterion 6: make `_attempt_segment_resume` presence in comment agree with presence in `__all__`, and restore the 4 ownership groups the retirement dropped

### 2.5 B4 — api-reference.md drift
- `docs/01-tools/api-reference.md:182` documents `RETRYABLE_STATUS_CODES` as `{429, 500, 502, 503, 504}` (5 members)
- Live code has **7 members** `{408, 425, 429, 500, 502, 503, 504}`
- Must be corrected in the same commit as the constant moves (D8)

### 2.6 B13 — .ai/audit/99-validation/ check
- Directory exists with 12 validation artifacts
- Plan 11 B10 carries absolute staging prohibition on `.ai/audit/99-validation/**`
- B13 writes no code, no tests, no `.ai/audit/` file — only an escalation note + board post

### 2.7 Packaging frozenset
- `EXPECTED_SDIST_ENTRIES` = **69 entries** (was 73 at plan base, 71 after PREREQ commit `44a3c9e`)
- If B4 creates `services/retry_policies.py`, frozensets must be updated in the same commit

### 2.8 B3 follow-up — gate violations at HEAD `56a1854`
- **Format gate RED:** 7 files would reformat (`cli.py`, `network_monitor.py`, `downloader_throttle.py`, `ffmpeg_utils.py`, `signal_handlers.py`, `ytdlp_downloader.py`, `test_hls_downloader.py`)
- **Warning count = 2** (plan requires ≤1): `test_downloader_throttle.py::test_pause_overwrites_previous` and `test_extractor.py::test_browser_extraction_captures_cookies` — both `RuntimeWarning: coroutine 'Event.wait' was never awaited`
- Per §2.2b: blanket `ruff format src tests` is **prohibited**; narrow fixes permitted only in `TestYtDlpSubprocessShutdown`

### 2.9 README.md stale reference
- `README.md:157`: "The legacy `_map_exception_to_status()` helper and `_EXCEPTION_STATUS_HANDLERS` dict are retained for backward compatibility."
- Both symbols were **deleted** by B1 commit `e647fb0` — `grep _map_exception_to_status src/` returns 0 hits

---

## 3. Block-by-block Task Specifications

---

### 3.1 B13 — VAL-901/VAL-902 escalation (no code)

**Preconditions:** None. Runs first, in parallel with anything.

**Goal:** Record that phase 09's `VAL-901` (CRITICAL) and `VAL-902` cannot be implemented under current authorisation, name the decision needed, and stop.

**Steps:**
1. Re-measure the `VAL-` namespace: occurrence count, distinct identifiers, bands in use, unparseable tokens. (Plan §3.13: measured 553 occurrences across 52 distinct identifiers at `09f1b10`; re-measure at HEAD.)
2. Verify the three mutually exclusive `VAL-003` claims still stand and which one `VAL-902` establishes as non-reproducing.
3. Confirm the authorisation wall: both remedies require editing under `.ai/audit/99-validation/`; plan 11 `B10` prohibits staging there; no document authorises this phase.
4. Compose the escalation note: what each finding is, why unimplementable, options (authorise phase 09; assign to a phase without the prohibition; record as permanently unfixed), recommendation.
5. Add: plan 11's two wrong `QLT-004` citations as a live instance; the four unowned `ffmpeg_utils.py` doc sites; the `D11` question; the malformed `refine.md`.
6. Post the note to the board.

**Acceptance criteria:**
1. Escalation states in one place: what VAL-901 and VAL-902 are, why unimplementable, options, recommendation.
2. Names plan 11's wrong `QLT-004` citations with locations.
3. Records four unowned ffmpeg_utils.py doc sites.
4. Records D11 question (which instruction produces a clean copy).
5. `git diff` shows no change under `.ai/audit/` and no change under `.kilo/`.
6. No file added/moved/deleted. No frozenset edit.

---

### 3.2 B4 — split downloader_throttle.py retry module

**Preconditions:** External gate P11 RESOLVED per `14-b4-unblock-report.md` (Phase 13 commits landed; "Plan 11" was a plan-renumbering artifact referring to Phase 13 = Plan 13). P12 segment_downloader track landed (`e2c5ad0`, `40404e2`, `767bb47`).

**Goal:** Move the 5 retry symbols into a new module named for retrying, leaving `downloader_throttle.py` with shutdown signalling and coordination. Update 4 production importers, the facade's ownership comment + `__all__`, fix the facade defect, correct `api-reference.md`'s RETRYABLE_STATUS_CODES row, update exactly 3 patch() strings, edit frozensets if a new file is created.

**Steps (per plan §6.6, adapted to current state):**
1. Re-derive the block's premise: 7 residue importers confirmed via Auditor census.
2. Re-census the patch() strings: 15 total, 3 must repoint, 12 move-robust.
3. Settle D7 (default: new module `services/retry_policies.py`; `downloader_throttle.py` keeps its name) and D8 (constant moves, doc corrected in same commit).
4. Create `src/vkdownloader/services/retry_policies.py` with the 5 moved symbols (no code changes to the symbols themselves — byte-identical arithmetic).
5. Update `services/segment_downloader.py` imports (all 5 symbols) and call sites.
6. Update `services/ytdlp_downloader.py` imports (2 symbols) and call sites.
7. Update `services/downloader.py` re-export: import from new module, keep `__all__` entry, update ownership comment.
8. Fix the facade defect: restore 4 dropped ownership groups; reconcile `_attempt_segment_resume` (add to `__all__` or remove from comment — must agree).
9. Update `tests/test_downloader_throttle.py` from-import block (repoint to new module).
10. Update exactly 3 patch() strings (the `downloader_throttle._wait_with_shutdown` ones at lines 472, 2641, 2806) — repoint to the new module name.
11. Update `docs/01-tools/api-reference.md` RETRYABLE_STATUS_CODES row (5→7 members).
12. If new file created, edit `tests/test_packaging.py` frozensets (EXPECTED_SDIST_ENTRIES, EXPECTED_WHEEL_ENTRIES) — add `src/vkdownloader/services/retry_policies.py`.
13. Confirm `_compute_backoff_delay` arithmetic byte-identical; both floor tests pass.
14. Confirm `git diff` over `services/ffmpeg_utils.py` is empty.

**Acceptance criteria:**
1. 5 retry symbols in one module (new retry module); residue stays in downloader_throttle.py.
2. All 7 residue importers unchanged and import successfully.
3. All 5 retry-policy importers import correctly.
4. Exactly 3 patch() strings change, all naming old module's own namespace; 12 untouched.
5. Facade comment + `__all__` both point at new owner; comment names every module owning a name in `__all__`; `_attempt_segment_resume` in `__all__` or absent from comment (must agree); mypy "does not explicitly export" error resolved.
6. `api-reference.md` RETRYABLE_STATUS_CODES row states live 7-member set.
7. No hunk touches `services/ffmpeg_utils.py`.
8. Gate: `uv run pytest -q -rs` → 3 skipped, ≤1 warning, no new failures. `ruff check src tests`, `ruff format --check src tests`, `mypy src` → clean.

**Agent roster:** Planner (D7/D8 decisions + task description), Validator (HIGH risk), Implementor (execution).

---

### 3.3 B3-FU — format gate + warning count follow-up

**Goal:** Resolve the two gate violations B3's commit `14c7012` acknowledged but did not fix.

**Steps:**
1. Run `ruff format --check src tests` to identify the 7 files.
2. Per §2.2b: ONLY narrow fixes in `TestYtDlpSubprocessShutdown` in `tests/test_hls_downloader.py` are permitted. Investigate whether the other 6 files' reformatting is py314-target-version related (parentheses removal from `except` clauses, per the audit results).
3. Investigate the 2 RuntimeWarnings — confirm they are GC-timing artifacts (§2.2 correction 4) per the plan's attribution.
4. Apply narrow fixes only.

**Acceptance criteria:**
1. `ruff format --check src tests` → green (all files formatted).
2. Warning count ≤ 1 (or 2 confirmed as GC-timing artifacts).
3. `uv run pytest -q -rs` → 3 skipped, warnings ≤ 1, no new failures.

**Agent roster:** Auditor (investigate), Planner (scope the narrow fix), Validator (review), Implementor (execute).

---

### 3.4 B1-README — stale shim reference (post-B1 fix)

**Goal:** Fix README.md:157 stale shim reference left behind by B1.

**Steps:**
1. Read README.md around line 157.
2. Remove or correct the sentence claiming `_map_exception_to_status()` and `_EXCEPTION_STATUS_HANDLERS` are "retained for backward compatibility."
3. Ensure README.md error-code table (L148-155) remains current.

**Acceptance criteria:**
1. `grep _map_exception_to_status src/` returns 0 hits (already confirmed).
2. `grep _map_exception_to_status README.md` returns 0 hits.
3. README.md error-code table is current.
4. Gate: `ruff check src tests` → clean (README is not checked, but no unrelated changes).

**Agent roster:** Planner (trivial), Implementor.

---

## 4. Execution Order

```
B13 (escalation, no code) ──► [board post]
  │
  ├── B4 (split downloader_throttle.py) ──► B3-FU (format gate + warnings)
  │                                           B1-README (stale shim ref)
  │
  └── B3-FU (parallel-safe, B13 produces no code)
  └── B1-README (parallel-safe, independent file)
```

**Total order for code changes:** `B4 → B3-FU → B1-README`
- B4 is independent of B3-FU and B1-README (touches `downloader_throttle.py`, `downloader.py`, `segment_downloader.py`, `ytdlp_downloader.py`, `test_packaging.py`, `api-reference.md`)
- B3-FU touches 7 source files (formatting) and 2 test files
- B1-README touches only `README.md`
- These three can run in parallel (max 2 subagents — so B4 and B3-FU in parallel, B1-README after)

**B13 runs first and in parallel** with everything (it produces no code).

---

## 5. Frozenset coupling

- B4: if creates `services/retry_policies.py`, must add to `EXPECTED_SDIST_ENTRIES` (69→70) and `EXPECTED_WHEEL_ENTRIES` (32→33) in same commit
- B3-FU: no frozenset edit (formatting only, no file add/delete)
- B1-README: no frozenset edit (README.md is not packaged... wait, need to verify)

## 6. Decisions (D1-D16 carry-forward)

- **D7** (default): new module for retry policy; `downloader_throttle.py` keeps its name (7 importers make renaming costlier)
- **D8** (default): `RETRYABLE_STATUS_CODES` moves with retry policy; `api-reference.md` corrected in same commit
