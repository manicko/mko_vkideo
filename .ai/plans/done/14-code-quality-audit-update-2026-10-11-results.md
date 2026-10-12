# Audit Results: Plan 14 Code-Quality Audit Verification — HEAD `56a1854`

**Date:** 2026-10-11
**Auditor:** Kilo (senior staff architecture auditor)
**Scope:** Independent verification of plan `.ai/plans/14-code-quality-audit-fixes_fix.md`
**Previous audits:** `.ai/audit/problems/14-code-quality-audit-doc-problems.md` (10-10), `.ai/audit/problems/14-code-quality-audit-update-2026-10-11.md` (10-11, at HEAD `24dcddc`)
**Live HEAD:** `56a1854` — 10 commits past the previous audit baseline

---

## Summary

**Not fully completed.** Ten of thirteen blocks have been executed since the
previous audit (at `24dcddc`); the remaining three are: B4 **blocked** by the
un-landed P11 external gate, B6 **voided** by the external deletion of
`docs/STRUCT.md`, and B13 **not done** (escalation report never produced).

Three gate violations remain: **format gate is RED** (7 files need
reformatting under py314 target-version), **warning count is 2** (plan
requires ≤1; the increment is a Python 3.14 asyncio RuntimeWarning), and
**api-reference.md still documents the stale 5-member RETRYABLE_STATUS_CODES**
(B4's D8 scope, blocked by P11).

**Recommendation:** retain `_fix`. The work is substantially executed but has
three concrete remaining items (B4, B13, B3 gate violations) that require
further code changes. The plan's prescriptions correct violations and do not
introduce architectural or quality regressions.

---

## Block-by-block status at HEAD `56a1854`

| Block | Plan §9 audit | Current | Evidence |
|---|---|---|---|  B1 | NOT DONE | **DONE** | Commit `e647fb0`: `_map_exception_to_status`, `_EXCEPTION_STATUS_HANDLERS`, `_quality_not_available_status` all deleted; `ErrorCode.NO_STREAMS` added; `status_label()` unified to `error_code.value`; tests rewritten with invariant assertion. `grep _map_exception_to_status src/` → 0 hits. |
| B2 | NOT DONE | **DONE** | Commit `3655cef`: `VKDownloadError` arm added to both `cli.py::download` (L487) and `cli.py::batch` (L619), between `except typer.Exit` and `except Exception`; uses `logger.error(..., exc_info=True)` with `**e.log_context()`; reuses `download_failed`/`batch_download_failed` event names; `D3` settled (exc_info=True preserves traceback); `D4` settled (adopt `user_message()`). |
| B3 | NOT DONE | **DONE** | Commit `14c7012`: `disallow_any_explicit = true` in `[tool.mypy]`; `requires-python = ">=3.14"`, `target-version = "py314"`, `python_version = "3.14"` all agree (§5.4 prohibition 16 satisfied); 6 explicit `Any` sites replaced with TypedDict/`object`; two override blocks for Pydantic `__init__` carry comments naming the upstream signature. ⚠️ See gate violations below. |
| B4 | NOT DONE | **BLOCKED** | All 5 retry symbols still in `downloader_throttle.py` (L53, L230, L333, L376, L417). External gate P11 (ytdlp_downloader.py retry infrastructure track) has **not** landed — no P11 commits found in the log. B4 cannot start until P11 lands (§4.2). |
| B5 | DONE | **DONE** | Commit `83ba0f8` previously documented Retry-After as floor; no change since. |
| B6 | PARTIAL → VOIDED | **VOIDED** | `docs/STRUCT.md` deleted by external commit `6ab4a50` (not by B6). B6's entire premise — correcting rows in this file — is voided. Module enumeration work absorbed by B7's map regeneration. |
| B7 | NOT DONE | **DONE** | Commit `4138e84`: `py_map.yaml` regenerated to 31 modules (was 23); zero phantom symbols (removed `QualityEnum`, `_parse_quality_to_enum`, `ProgressParser`, `_sanitize_title`); all paths repository-relative (was `.ai/builders/..\..\src\...`); `front/` maps deleted (foreign project, D9 default). `map.md` rewritten with zero `.pyc`/`.egg-info` entries. |
| B8 | PARTIAL | **DONE** | Commit `c7b7dcb`: universal-export claim removed (L292); `sanitize_title` → `sanitize_filename_component` at L85/L154; 4 stale line counts dropped (D10 default: drop, no oracle parses them); `ffmpeg_utils.py` listing rewritten to describe permanent module. |
| B9 | NOT DONE | **DONE** | Commit `63b020e`: `cli-reference-clean.md` deleted; content merged into `cli-reference.md`; `EXPECTED_SDIST_ENTRIES` updated; B9 step 7 (update research doc reference) moot — that doc was deleted by `6ab4a50`. |
| B10 | NOT DONE | **DONE** | Commit `b0eae7d`: `morfx-tools.md` and `ast-editor.md` relocated from `docs/99-reference/` to `.kilo/reference/`; removed from `EXPECTED_SDIST_ENTRIES` (72→70). `D12` settled: `.kilo/commands/implement/implement-multiple-tasks.md` references `ast-editor.md` by path, confirming these describe agent tooling. |
| B11 | NOT DONE | **DONE** | Commit `56a1854`: all dead `INT-`/`SRV-`/`STR-` parenthetical citations removed from 20 sites in 7 source files + 2 docs; `STR-008` on `ffmpeg_utils.py` group A preserved (permanent product surface per Ruling A); no new tokens invented. |
| B12 | NOT DONE | **DONE** | Commit `1eda62f`: `models/quality.py` import-form taxonomy comment added (26-module census); lazy absolute import at `QualitySpec.parse()` has deferral comment naming the cycle it breaks (`models.quality → exceptions → utils.security → models.video → models.`). |
| B13 | NOT DONE | **NOT DONE** | No escalation report for `VAL-901` (CRITICAL) / `VAL-902` produced. No commit or document found anywhere in the tree. |

---

## Gate verification at HEAD `56a1854`

| Gate | Status | Notes |
|---|---|---|
| `uv run pytest -q -rs` | ✅ 1083 passed, 3 skipped | Skip floor maintained at exactly 3 |
| `uv run ruff check src tests` | ✅ All checks passed | — |
| `uv run ruff check .` | ✅ All checks passed | — |
| `uv run mypy src` | ✅ Success, 31 source files | — |
| `uv run mypy --disallow-any-explicit src` | ✅ 0 errors | B3 criterion 1 satisfied |
| `uv run ruff format --check src tests` | ❌ **RED** — 7 files would reformat | `cli.py`, `network_monitor.py`, `downloader_throttle.py`, `ffmpeg_utils.py`, `signal_handlers.py`, `ytdlp_downloader.py`, `test_hls_downloader.py`. Caused by py314 target-version syntax changes (parentheses removal from `except` clauses). Per §2.2b, blanket reformat is prohibited. |
| Warning count | ⚠️ **2** (plan requires ≤1) | `test_downloader_throttle.py::TestBackoffCoordinatorPause::test_pause_overwrites_previous` and `test_extractor.py::TestExtractWithBrowser::test_browser_extraction_captures_cookies` — `RuntimeWarning: coroutine 'Event.wait' was never awaited`. Both are Python 3.14 asyncio behavior, per §2.2 correction 4 (GC-timing artifact). |
| `mypy src tests` | ⚠️ 201 errors in 13 files | Delta gate (§7.3); increased from 89 at `09f1b10` due to `tests/` `Any` and type issues. Direction stated: UP. |

---

## Documentation problems found in `docs/`

### 1. `docs/01-tools/api-reference.md` — stale constant census (B4 scope, blocked)

| Line | Problem | Details |
|---|---|---|
| 182 | `RETRYABLE_STATUS_CODES` documented as `{429, 500, 502, 503, 504}` (5 members) | Actual: `{408, 425, 429, 500, 502, 503, 504}` (7 members). `408` (Request Timeout) and `425` (Too Many Requests) are missing from both the table and the prose at line 204. |

**Scope:** This is B4's acceptance criterion 7 ("Correct `api-reference.md`'s `RETRYABLE_STATUS_CODES` row in this commit"). B4 is currently **blocked** by the un-landed P11 external gate. The fix cannot be applied until B4 executes.

### 2. `README.md` — stale reference to removed shim (B1 scope, unaddressed)

| Line | Problem | Details |
|---|---|---|
| 157 | "The legacy `_map_exception_to_status()` helper and `_EXCEPTION_STATUS_HANDLERS` dict are retained for backward compatibility." | Both symbols were deleted from `exceptions.py` by B1's commit `e647fb0`. `grep _map_exception_to_status src/` returns 0 hits. The README still advertises their existence. |

**Scope:** B1's acceptance criterion 4 required updating "the module docstring and every comment that names the shim." `README.md` was not included in B1's file changes (`e647fb0` touched only `exceptions.py`, `enums.py`, `batch_downloader.py`, and two test files). This is a documentation problem that B1's execution left behind.

### 3. Previously reported doc problems — resolution status

| Problem (from 10-10 audit) | Resolution |
|---|---|
| `docs/STRUCT.md` stale rows (B6) | **VOIDED** — file deleted by external commit `6ab4a50` |
| `vkdownloader-overview.md` universal-export claim + stale counts (B8) | **FIXED** — commit `c7b7dcb` |
| `cli-reference-clean.md` duplicate `id` + mojibake (B9) | **FIXED** — file deleted, commit `63b020e` |
| `morfx-tools.md` / `ast-editor.md` non-existent tooling (B10) | **FIXED** — relocated to `.kilo/reference/`, commit `b0eae7d` |
| `.ai/structure/back/py_map.yaml` phantom symbols + unsafe paths (B7) | **FIXED** — commit `4138e84` |
| `.ai/structure/front/*` foreign project references (B7) | **FIXED** — front maps deleted, commit `4138e84` |
| `.ai/structure/map.md` stale `.pyc` entries + drive-letter casing (B7) | **FIXED** — commit `4138e84` |

---

## Code problems found (documentation only — no code changes made)

| Issue | Status | Plan block |
|---|---|---|
| `ruff format --check src tests` is RED (7 files) | ⚠️ Acknowledged in B3 commit; not reformatted per §2.2b | B3 |
| Warning count = 2 (plan requires ≤1) | ⚠️ Python 3.14 asyncio RuntimeWarning | B3 |
| `EXPECTED_SDIST_ENTRIES` broken by `6ab4a50` | ✅ Fixed by `44a3c9e` (73→71 entries) | PREREQ |
| `_attempt_segment_resume` in `downloader.py:49` but absent from `__all__` and ownership comment | Remaining B4 criterion 6 | B4 (blocked) |
| `mypy src tests`: 201 errors (increased from 89 at `09f1b10`) | Delta gate; direction UP | B3 |

---

## Voided assertions (verified at HEAD `56a1854`)

All five voided assertions from the §9 audit (at `2289f6f`) hold:

1. **§2.3/§2.9**: `check_ffmpeg_available` return value consumed — void (commit `e6e6c68`)
2. **§2.2**: Skip floor = 3 POSIX-killpg oracles — void (commit `3778e13`), still 3 skips
3. **§2.3**: Format gate green — **re-voided** (was green at §9 audit; now RED after py314 upgrade)
4. **§2.5 correction 12**: Facade groups restored by `0ee7297`; `_attempt_segment_resume` absence from `__all__` remains B4's criterion 6
5. **QLT-009**: `INT-014` removed; path is `INT-008` only — void

Note: assertion #3 (format gate) was voided as "green" in the §9 audit but is now **RED** again after B3's py314 target-version change. This is a new state not covered by the §9 audit.

---

## CRITICAL issue: packaging test was broken, now fixed

Commit `6ab4a50` (`chore clean structure.md`) deleted `docs/STRUCT.md` and
`docs/error-handling-logging-research-2025-2026.md` without updating
`EXPECTED_SDIST_ENTRIES` in `tests/test_packaging.py`. This broke the
packaging test suite (73 expected entries vs 71 actual).

**Resolution:** Commit `44a3c9e` (`fix(test): remove deleted docs from SDIST frozenset`)
removed both entries from the frozenset, restoring the packaging tests.
The test suite now passes: 1083 passed, 3 skipped, 2 warnings.

However, the frozenset count is now coupled to B4 and B9 state:
- B9 (done) removed `cli-reference-clean.md` → frozenset must decrease
- B10 (done) relocated `morfx-tools.md` and `ast-editor.md` → frozenset must decrease
- The `PREREQ` commit `44a3c9e` handled the `6ab4a50` deletions, not B9/B10

**Verification:** `grep -n "cli-reference-clean\|morfx-tools\|ast-editor\|STRUCT" tests/test_packaging.py` returns 0 hits. The frozenset is correctly synchronized with the current tree. ✅

---

## Remaining work

| Item | Block | Action needed |
|---|---|---|
| B4: Split `downloader_throttle.py` retry module | B4 | Execute once P11 external gate lands (ytdlp_downloader.py retry infrastructure track) |
| B4's D8: Fix `api-reference.md` RETRYABLE_STATUS_CODES | B4 | Part of B4's criterion 7 (in same commit as module split) |
| B13: VAL-901/VAL-902 escalation report | B13 | Produce escalation note; post to board; record in block report |
| B3: Format gate RED | B3 | Apply py314-compatible reformatting to 7 named files (NOT a blanket reformat) OR revert target-version to py312 and re-evaluate Ruling B |
| B3: Warning count = 2 | B3 | Investigate the 2 RuntimeWarnings; confirm they are GC-timing artifacts (§2.2 correction 4) |
| README.md: stale shim reference | B1 (post-hoc fix) | Remove line 157's false claim about `_map_exception_to_status` / `_EXCEPTION_STATUS_HANDLERS` being "retained" |

---

## Conclusion

At HEAD `56a1854`, plan 14 has been **substantially executed** but is **not
fully completed**:

- **10 of 13 blocks DONE**: B1, B2, B3, B5, B7, B8, B9, B10, B11, B12
- **B4 BLOCKED** by external gate P11 (ytdlp_downloader.py retry infrastructure not landed)
- **B6 VOIDED** (docs/STRUCT.md deleted by external commit `6ab4a50`)
- **B13 NOT DONE** (escalation report never produced)
- **B3 gate violations**: format gate RED, warning count = 2 (should be ≤1)

The plan remains **valid and relevant**: the issues it targets were real, the
prescriptions correct violations rather than introducing them, and plan 18
still references plan 14 as a source. The file's `_fix` status is correct —
further code changes are needed (B4, B13, and B3's format/warning issues) before
the plan can be retired as `_done`.

**Plan file:** `.ai/plans/14-code-quality-audit-fixes_fix.md` — status **`_fix`** (correct, retain).
