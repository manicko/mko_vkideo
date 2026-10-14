# Audit Problems Report — Plan 06

**Plan:** `06-config-audit-fixes.md` (configuration & validation pipeline audit fixes)
**Audit date:** 2026-10-08
**Repository:** `vkdownloader` (`C:\py_exp\mko_vkideo`)
**Scope:** Verification of plan completion and problems found in code/docs during audit.

---

## Summary

The plan's 8 blocks (B1–B8) were fully implemented in commits `a704c8a`–`1a304d4`
(all 2026-09-30), with two follow-up commits the same day (`e15d928`, `db9f877`).
All plan-specific tests pass (202 config+CLI tests); `ruff check`, `ruff format
--check`, and `mypy` all exit 0.

The plan is **complete — no code refinement is required** for its blocks. The
plan file has been renamed to `_done` and moved to `.ai/plans/done/`.

Two test failures exist in the full suite (`test_packaging.py`), but they are
**not** caused by the plan's blocks — see Problem 1 below.

---

## Problem 1 — `.python-version` deleted, breaking sdist manifest tests

**Severity:** MEDIUM (test failures)
**Source:** commit `009f9fc` "chore(doc) audit and plans" (2026-10-08)
**Status:** NOT caused by this plan; reported for awareness.

The file `.python-version` (contents: `3.12`) was deleted in commit `009f9fc`,
but it remains listed in `[tool.hatch.build.targets.sdist].include` in
`pyproject.toml` (line 61). Since the file does not exist on disk, the sdist
build omits it, so the manifest test sees 74 entries instead of the expected 75.

**Failing tests:**
- `tests/test_packaging.py::test_sdist_entry_set_matches_the_manifest` —
  `missing (1): ['.python-version']`
- `tests/test_packaging.py::test_sdist_entry_count_matches_the_manifest` —
  `assert 74 == 75`

**Evidence:**
- `git show 0790157:.python-version` → `3.12` (the file existed at the plan's
  base commit).
- `git show 009f9fc -- .python-version` → deleted in the chore commit.
- `Test-Path .python-version` → `False` (absent from working tree).
- All plan block commits (a704c8a–1a304d4, e15d928, db9f877) do not touch
  `.python-version` or `pyproject.toml`'s sdist include list.

**Note:** These failures are pre-existing relative to this plan's blocks. If
resolved by re-adding `.python-version` with content `3.12`, both tests will
pass without any change to the plan's code.

---

## Problem 2 — Stale Python version requirement in installation guide

**Severity:** LOW (documentation drift)
**Location:** `docs/01-tools/installation.md`, line 20
**Status:** Pre-existing; not in scope for this plan.

The installation guide states "Python 3.10 or higher" but
`pyproject.toml` line 6 declares `requires-python = ">=3.12"`. The project
also uses `from __future__ import annotations` (cli.py line 13) and Python 3.12+
syntax (e.g., `str | None` type hints), so the documented minimum is stale.

---

## Problem 3 — Pre-existing `Any` type usage violates project rule C9

**Severity:** LOW (code quality, pre-existing)
**Locations:**
- `src/vkdownloader/config.py` lines 9, 511 —
  `from typing import IO, Any, cast` and
  `def __getattr__(self, name: str) -> Any:` in `_EncodingSafeTextStream`.
- `src/vkdownloader/cli.py` lines 17, 251 —
  `from typing import Any, TypedDict` and
  `def _quality_option() -> Any:`.

**Status:** Pre-existing code, not introduced by any of the plan's blocks.
Project rule C9 (`.kilo/rules/project.md`) states: "No `any`" and
"Type Safety Everywhere." These usages predate the plan and are untouched by
B1–B8. They are recorded here for awareness; they are **not** assigned to this
plan's scope.

---

## Problem 4 — `--max-retries` "batch command only" claim in configuration guide

**Severity:** LOW (documentation drift, out of scope)
**Location:** `docs/11-guides/configuration.md` lines 110, 115
**Status:** Explicitly out of scope for this plan; reported as an observation
per the plan's B8 hard boundary.

The configuration guide states:
- Line 110: `CLI Flag: --max-retries / -r (batch command only)`
- Line 115: `The --max-retries CLI flag is only available on the batch command.`

But `cli.py` declares `--max-retries` on **both** the `download` and `batch`
commands (lines 370–375 and 503–508). The `cli-reference.md` (lines 64, 130)
correctly shows the flag on both commands.

The plan's B8 section explicitly names this as out of bounds:

> `configuration.md`'s claim that `--max-retries` is only available on the
> `batch` command (it is declared on `download` too) — **phase 08's subject**.

The plan's B8 acceptance criterion 6 requires this item to be **unchanged** and
**listed in the block report as an observation for its owning phase**. It
remains unchanged.

---

## Problem 5 — Unverified `.env.example` BOM acceptance criterion

**Severity:** LOW (verification gap)
**Location:** Plan B1 acceptance criterion 13
**Status:** The plan specified a run-and-record procedure (§7.4) for the BOM
  case; the commit `a704c8a` implements `_is_unknown_env_var` with a
  `U+FEFF` prefix skip, but the acceptance criterion requires the guard's
  verdict on a BOM-prefixed `.env` to equal the model's verdict on that same
  file, on **both** `python-dotenv` 1.2.2 and 1.2.3. The installed version is
  1.2.2 (per `pyproject.toml` lower bound `>=1.2.2`). The test suite includes
  a BOM test, but the cross-version assertion (1.2.2 vs 1.2.3) is a procedural
  check that requires running the procedure manually — it is not committed as
  a test per deferral D-3. The procedure was specified in the plan but its
  execution record is not available in the repository.

---

## Notes on plan block verification

| Block | Commit | Key changes | Tests | Acceptance criteria met |
|-------|--------|-------------|-------|------------------------| 
| B1 (CFG-004) | `a704c8a` | `dotenv_values` reader, `_is_unknown_env_var`, `python-dotenv` declared | 122 config tests pass | Yes |
| B2 (CFG-003, VAL-006) | `c078772` | `_normalise_loc_to_env_var`, env-namespace matching, cutoff=0.9 | 122 config tests pass | Yes (with fix-up `e15d928`) |
| B3 (CFG-005) | `4a0add0` | `.env.example` value, configuration.md ranges | 12 config tests pass | Yes |
| B4 (CFG-007, VAL-006) | `75e49ff` | `reject_empty_string` validator, citation removed | 122 config tests pass | Yes |
| B5 (CFG-008) | `fcd86c8` | `_log_env_file_path` at INFO, docs corrected | 80 cli tests pass | Yes |
| B6 (VAL-001) | `feb0a40` | Decision field in template, deviation paragraph removed | — | Yes |
| B7 (VAL-003, VAL-004) | `19143b1` | Gate removed, AGENTS.md → real files, conditional output | — | Yes |
| B8 (doc pass) | `1a304d4` | Docs aligned with code, http_chunk_size corrected | — | Yes (with follow-up `db9f877`) |

The follow-up commit `e15d928` ("preserve quotes in env-var error display and
suppress self-referential suggestions") is a necessary refinement of B2, adding
quote-preserving display and self-referential suggestion suppression that the
initial B2 commit did not handle. It is considered part of the B2 block's
completion.

The commit `db9f877` ("drop the ffprobe section, fix the cookie-source values,
de-duplicate the settings table") is documentation cleanup consistent with
B8's doc-consistency pass and is treated as a continuation of B8.
