# Audit Problems Report — Plan 14 Documentation Check (Updated)

**Date:** 2026-10-12
**Auditor:** Kilo (senior staff architecture auditor)
**Scope:** Verification of plan `14-code-quality-audit-fixes` and documentation issues in `docs/`
**Note:** The user requested checks against `C:\py_dev\mko_bazuna\docs`, but that path does not exist in this environment. This report covers `C:\py_exp\mko_vkideo\docs` (the live workspace) instead, which is the project the plan targets.

---

## Summary

Plan 14 (`14-code-quality-audit-fixes_fix.md`) describes 13 execution blocks (B1–B13) targeting code-quality audit findings (`QLT-001` through `QLT-013`, plus `VAL-901/902/903`). **All 13 blocks have been executed** (B6 was voided by an external deletion of `docs/STRUCT.md`; B13 produced an escalation note and board post with no code). The plan is now fully complete and all gates pass.

**Conclusion: rename to `_done`.** The work is complete, no code refinement is needed, the plan's prescriptions corrected violations without introducing architectural or quality regressions, and all acceptance criteria have been met.

---

## Block-by-block execution status

| Block | Description | Status | Evidence |
|---|---|---|---|
| B1 | Delete `_map_exception_to_status` shim; unify `status_label()` against `ErrorCode`; add `NO_STREAMS` | **DONE** | Commit `e647fb0` (10-11): `_map_exception_to_status`, `_EXCEPTION_STATUS_HANDLERS`, `_quality_not_available_status` all deleted; `ErrorCode.NO_STREAMS` added to `enums.py` (L74); `status_label()` unified to `error_code.value`; 6 overrides collapsed to one; `tests/test_exceptions.py` rewritten with invariant assertion. `grep _map_exception_to_status src/` → 0 hits. README shim reference fixed by `666666d`. |
| B2 | Add logging to silent exception ladder clauses in `cli.py` and `batch_downloader` | **DONE** | Commit `3655cef` (10-11): `VKDownloadError` arm added to both `cli.py::download` (L488) and `cli.py::batch` (L620), placed after `except typer.Exit` and after `except _PreambleFailure`; uses `logger.error(..., exc_info=True)` with `**e.log_context()`; reuses `download_failed`/`batch_download_failed` event names. |
| B3 | Enable `disallow_any_explicit`; reconcile Python version pins | **DONE** | Commit `14c7012` (10-11): `disallow_any_explicit = true` in `[tool.mypy]`; `requires-python = ">=3.14"`, `target-version = "py314"`, `python_version = "3.14"` all agree. Commit `e4889fe` (10-12): format gate GREEN (56 files formatted); warning count = 0. |
| B4 | Split `downloader_throttle.py` (retry policy → new module) | **DONE** | Commit `723cb16` (10-12): 5 retry symbols moved to `services/retry_policies.py`; `_retry_429_with_backoff` re-exported from `downloader.py` via explicit `as` form; `_attempt_segment_resume` reconciled; `api-reference.md` RETRYABLE_STATUS_CODES corrected (5→7 members); `EXPECTED_SDIST_ENTRIES` and `EXPECTED_WHEEL_ENTRIES` updated. |
| B5 | Document Retry-After as a floor (not an override) | **DONE** | Commit `83ba0f8` (10-05): comment and docstring corrected to state `max(backoff, retry_after)` floor semantics. |
| B6 | Fix `docs/STRUCT.md` stale rows | **VOIDED** | `docs/STRUCT.md` was deleted by external commit `6ab4a50` (`chore clean structure.md`, 10-11). B6's entire premise — correcting rows in this file — is voided. Module enumeration work absorbed by B7's map regeneration (`py_map.yaml`). |
| B7 | Fix `.ai/structure/` stale maps | **DONE** | Commit `4138e84` (10-11): `py_map.yaml` regenerated to 31 modules (was 23); zero phantom symbols; all paths repository-relative; `front/` maps deleted (foreign project, D9 default); `map.md` rewritten with zero `.pyc`/`.egg-info` entries. |
| B8 | Fix `vkdownloader-overview.md` universal-export claim and stale line counts | **DONE** | Commit `c7b7dcb` (10-11): universal-export claim removed (L292); `sanitize_title` → `sanitize_filename_component` at L85/L154; all four stale line-count annotations dropped (D10 default); `ffmpeg_utils.py` listing rewritten to "FFmpeg commands, availability probe, merge engine" (progress parsing removed). |
| B9 | Delete `cli-reference-clean.md`; merge into `cli-reference.md` | **DONE** | Commit `63b020e` (10-11): `cli-reference-clean.md` deleted; content merged into `cli-reference.md`; `EXPECTED_SDIST_ENTRIES` updated; `--ssl-verify` default and 7-step batch list verified. Commit `44a3c9e`: frozenset reconciled after `6ab4a50` deletions. |
| B10 | Resolve misplaced `morfx-tools.md` / `ast-editor.md` | **DONE** | Commit `b0eae7d` (10-11): both files relocated from `docs/99-reference/` to `.kilo/reference/`; removed from `EXPECTED_SDIST_ENTRIES` (72→70); `related` arrays use document IDs, not paths — no changes needed. |
| B11 | Resolve dead `INT-`/`SRV-`/`STR-` provenance citations | **DONE** | Commit `56a1854` (10-11): all dead citations removed from 20 sites in 7 source files + 2 docs; `STR-008` on `ffmpeg_utils.py` group A preserved (permanent product surface per Ruling A); no new tokens invented. |
| B12 | Record the mixed import form in `models/quality.py` | **DONE** | Commit `1eda62f` (10-11): import-form taxonomy comment added (26-module census); lazy absolute import at `QualitySpec.parse()` has deferral comment naming the cycle it breaks (`models.quality → exceptions → utils.security → models.video → models.`). |
| B13 | Produce escalation note for `VAL-901`/`VAL-902` | **DONE** | Escalation note composed and posted to board (no code). VAL-901 (CRITICAL) and VAL-902 remain unimplemented by design — both require writing under `.ai/audit/99-validation/`, which plan 11 B10 prohibits. |

---

## Documentation problems found in `docs/`

### All previously reported doc problems — RESOLVED

| Problem (from 10-10 audit) | Resolution | Evidence |
|---|---|---|
| `docs/STRUCT.md` stale rows (B6) | **VOIDED** — file deleted by external commit `6ab4a50` | `Test-Path docs/STRUCT.md` → not found |
| `vkdownloader-overview.md` universal-export claim (B8) | **FIXED** — commit `c7b7dcb` removed L292 claim | `grep "All modules export" docs/` → 0 hits |
| `vkdownloader-overview.md` stale line counts (B8) | **FIXED** — commit `c7b7dcb` dropped all 4 counts (D10 default) | `grep "~350\|~722\|~901\|~360" docs/01-tools/vkdownloader-overview.md` → 0 hits |
| `vkdownloader-overview.md` `sanitize_title` stale refs (B8) | **FIXED** — commit `c7b7dcb` renamed both refs to `sanitize_filename_component` | `grep "sanitize_title" docs/` → 0 hits |
| `vkdownloader-overview.md` ffmpeg_utils.py listing (B8) | **FIXED** — commit `c7b7dcb` updated to "FFmpeg commands, availability probe, merge engine" (progress parsing removed) | `grep "progress parsing" docs/01-tools/vkdownloader-overview.md` → 0 hits |
| `api-reference.md` stale RETRYABLE_STATUS_CODES (B4/D8) | **FIXED** — commit `723cb16` corrected to 7 members; also notes new module location | `api-reference.md:182` shows `{408, 425, 429, 500, 502, 503, 504}`; `api-reference.md:184` notes `vkdownloader.services.retry_policies` |
| `cli-reference-clean.md` duplicate `id` + mojibake (B9) | **FIXED** — file deleted, commit `63b020e` | `Test-Path docs/99-reference/cli-reference-clean.md` → not found |
| `morfx-tools.md` / `ast-editor.md` non-existent tooling (B10) | **FIXED** — relocated to `.kilo/reference/`, commit `b0eae7d` | Both files exist in `.kilo/reference/`; removed from `docs/99-reference/` and `EXPECTED_SDIST_ENTRIES` |
| `.ai/structure/back/py_map.yaml` stale (B7) | **FIXED** — commit `4138e84` regenerated with 31 modules | `py_map.yaml` has 31 entries, zero phantom symbols |
| `.ai/structure/back/py_anchors.yaml` unsafe paths (B7) | **FIXED** — commit `4138e84` made paths repository-relative | No `.ai/builders/` prefixes remain |
| `.ai/structure/front/*` foreign project (B7) | **FIXED** — front maps deleted, commit `4138e84` (D9 default) | `Test-Path .ai/structure/front/` → not found |
| `.ai/structure/map.md` stale `.pyc` entries (B7) | **FIXED** — commit `4138e84` rewrote with zero `.pyc`/`.egg-info` entries | `grep ".pyc" .ai/structure/map.md` → 0 hits |
| `README.md` stale shim reference (B1-README) | **FIXED** — commit `666666d` removed L157 false claim | `grep "_map_exception_to_status" README.md` → 0 hits |
| `docs/01-tools/installation.md` stale Python version (P13-B10) | **FIXED** — commit `5143dfc` updated minimum to 3.14 | `installation.md` says "Python 3.14 or higher" |
| `docs/99-reference/cli-reference.md` --ssl-verify default | **FIXED** — commit `63b020e` merged correct `true` default | `cli-reference.md` states `true` matching `config.py` |

### No remaining doc problems found

During a thorough audit of `docs/` at HEAD `48e4472`, **zero remaining documentation problems** were found. All issues identified in the original (10-10) audit and the follow-up (10-11) audit have been resolved by the plan's block executions.

---

## Code problems found (verification only — no code changes made)

| Check | Status | Evidence |
|---|---|---|
| `_map_exception_to_status` in `src/` | 0 hits | B1 criterion 7 met |
| `ErrorCode.NO_STREAMS` in `enums.py` | Present (L74) | B1 accepted |
| `VKDownloadError` arms in `cli.py` | Present (L488, L620) | B2 accepted |
| `disallow_any_explicit` in `pyproject.toml` | `= true` (L94) | B3 accepted |
| `requires-python`, `target-version`, `python_version` | All `>=3.14` / `py314` / `"3.14"` | D16 satisfied |
| `mypy --disallow-any-explicit src` | 0 errors | B3 criterion 1 met |
| `retry_policies.py` module exists | Present | B4 accepted |
| `_attempt_segment_resume` re-export | Explicit `as` form (L49) | B4 criterion 6 met |
| `TestYtDlpSubprocessShutdown` format | GREEN | B3-FU resolved |

---

## Gate verification at HEAD `48e4472`

| Gate | Status | Notes |
|---|---|---|
| `uv run pytest -q -rs` | ✅ 1097 passed, 3 skipped, 0 warnings | Skip floor maintained at exactly 3; warning count = 0 |
| `uv run ruff check src tests` | ✅ All checks passed | — |
| `uv run ruff check .` | ✅ All checks passed | — |
| `uv run ruff format --check src tests` | ✅ 56 files already formatted | Green (was RED after B3; fixed by B3-FU `e4889fe`) |
| `uv run mypy src` | ✅ Success, 32 source files | 31 + `retry_policies.py` |
| `uv run mypy --disallow-any-explicit src` | ✅ 0 errors | B3 criterion 1 satisfied |
| `tests/test_packaging.py` | ✅ Green | Frozensets synchronized (PREREQ `44a3c9e`, B4 `723cb16`) |

---

## Conclusion

At HEAD `48e4472`, plan 14 is **fully executed and complete**:

- **All 13 blocks resolved**: B1–B5, B7–B13 DONE; B6 VOIDED (external file deletion)
- **All gates green**: pytest 1097 passed/3 skipped/0 warnings; ruff clean; format green; mypy clean
- **All documentation issues resolved**: zero remaining doc problems found
- **No code changes needed**: the plan's prescriptions corrected violations without regressions

The plan file has been renamed from `_fix` to `_done` and moved to `.ai/plans/done/14-code-quality-audit-fixes_done.md`.
