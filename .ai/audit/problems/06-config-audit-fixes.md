# Audit Problems Report — Plan 06: Configuration & Validation Pipeline Fixes

**Audited plan:** `06-config-audit-fixes.md`
**Audit date:** 2026-10-08
**Repository:** `vkdownloader` (`C:\py_exp\mko_vkideo`)
**Scope:** Verification of plan completion and problems found in code/docs during audit.

---

## Plan Completion Status: ALL 8 BLOCKS IMPLEMENTED

All 8 blocks (B1–B8) were committed in one commit each on 2026-09-30:

| Block | Commit | Status |
|---|---|---|
| B1 (CFG-004) | `a704c8a` | Implemented |
| B2 (CFG-003, VAL-006) | `c078772` | Implemented (+ follow-up `e15d928`) |
| B3 (CFG-005) | `4a0add0` | Implemented |
| B4 (CFG-007, VAL-006) | `75e49ff` | Implemented |
| B5 (CFG-008) | `fcd86c8` | Implemented |
| B6 (VAL-001) | `feb0a40` | Implemented |
| B7 (VAL-003, VAL-004) | `19143b1` | Implemented |
| B8 (doc pass) | `1a304d4` | Implemented (+ follow-up `db9f877`) |

**Plan-specific tests:** 122 config tests + 80 CLI tests all pass (202 total).
**Lint/format/mypy:** All exit 0.
**No code changes made by this audit pass.**

---

## Problem 1 — Packaging test failures (pre-existing, post-plan regression)

**Severity:** MEDIUM (test failures)
**Files:** `pyproject.toml`, `.python-version`
**Tests affected:** `tests/test_packaging.py::test_sdist_entry_set_matches_the_manifest`, `test_sdist_entry_count_matches_the_manifest`

### Description

Two packaging tests fail because `.python-version` is listed in the sdist include
list (`pyproject.toml` line 61) but does not exist on disk.

### Root Cause

The `.python-version` file (contents: `3.12`) was deleted in commit `009f9fc`
("chore(doc) audit and plans", 2026-10-08). This commit is the **current HEAD**
and is **not** one of the plan's eight block commits (all from 2026-09-30).

Evidence:
- `git show 0790157:.python-version` → `3.12` (existed at plan's base commit)
- `git show 009f9fc -- .python-version` → `deleted file mode 100644`
- `Test-Path .python-version` → `False`
- The 8 block commits (a704c8a–1a304d4) do not touch `.python-version`

### Impact

```
test_sdist_entry_set_matches_the_manifest:
  missing (1): ['.python-version']
  actual count: 74, expected count: 75

test_sdist_entry_count_matches_the_manifest:
  assert 74 == 75
```

### Must fix

Restore `.python-version` with contents `3.12` (or remove the `/.python-version`
line from `pyproject.toml`'s sdist include list and update
`EXPECTED_SDIST_ENTRIES` in `tests/test_packaging.py`).

### Plan's role

None. The plan's blocks do not touch `.python-version` or the sdist manifest.
At the time the blocks landed (2026-09-30), `.python-version` existed and the
packaging tests passed.

---

## Problem 2 — Stale Python version requirement in installation guide

**Severity:** LOW (documentation drift)
**File:** `docs/01-tools/installation.md`, line 20

### Description

The installation guide states "Python 3.10 or higher" but `pyproject.toml`
line 6 declares `requires-python = ">=3.12"`. The codebase uses 3.12-only syntax
(e.g., `str | None` union types in `cli.py` lines 140-142, `from __future__ import
annotations`).

### Evidence

- `pyproject.toml:6` → `requires-python = ">=3.12"`
- `docs/01-tools/installation.md:20` → `- Python 3.10 or higher`

### Plan's role

None. B5 corrected the `ssl_verify`/`cookie_source` reachability claim but
did not address the version floor.

---

## Problem 3 — Pre-existing `Any` type usage (violates project rule C9)

**Severity:** LOW (code quality, pre-existing)
**Files:** `src/vkdownloader/config.py`, `src/vkdownloader/cli.py`

### Description

Project rule C9 (`.kilo/rules/project.md`) states: "No `Any`." However, two
pre-existing code units use `Any`:

1. `src/vkdownloader/config.py` line 9: `from typing import IO, Any, cast`
   line 511: `def __getattr__(self, name: str) -> Any:` (in
   `_EncodingSafeTextStream`)

2. `src/vkdownloader/cli.py` line 17: `from typing import Any, TypedDict`
   line 251: `def _quality_option() -> Any:`

### Plan's role

None. These code units are pre-existing infrastructure (`_EncodingSafeTextStream`
and the Typer option builder) and were not touched by any of the plan's blocks
B1–B8. The `Any` usage in `_quality_option` is a common Typer pattern: the
function returns `typer.Option(...)`, whose return type is `Any`.

---

## Problem 4 — `--max-retries` "batch command only" doc drift

**Severity:** LOW (documentation drift, explicitly out of scope)
**File:** `docs/11-guides/configuration.md`, lines 110, 115
**Status:** Out of scope — belongs to phase 08

### Description

The configuration guide states:
- Line 110: `CLI Flag: --max-retries / -r (batch command only)`
- Line 115: `The --max-retries CLI flag is only available on the batch command.`

But `cli.py` declares `--max-retries` on **both** the `download` command
(lines 370-375) and the `batch` command (lines 503-508). The `cli-reference.md`
(lines 64, 130) correctly shows the flag on both commands.

### Plan's role

None. §1.3 of the plan explicitly names this as **phase 08's subject** and the
B8 hard boundary forbids touching it. The configuration guide was left
unchanged per the boundary.

---

## Problem 5 — Unverified BOM acceptance criterion (D-3 deferral)

**Severity:** LOW (verification gap)
**Block:** B1, acceptance criterion 13
**File:** `tests/test_config.py`

### Description

B1 criterion 13 requires that a `.env` written with a UTF-8 BOM is checked for
**agreement with the model** on the same file, not against a fixed expectation:
on `python-dotenv` 1.2.2 the BOM stays in the first key (model rejects → guard
must report), on 1.2.3 the reader strips the BOM (model accepts → guard reports
nothing). The assertion must compare the guard's verdict to the model's verdict.

Per §1.4 **D-3**, this is explicitly **deferred** to phase 10 as a recurrence
test. The §7.4 run-and-record procedure is a verification procedure, not a code
change, and its execution record was not available in the repository at audit
time.

### Must implement

No. This is explicitly deferred. **This procedure is NOT a task to implement in
this plan.**

---

## Additional observation — inter-phase changes detected

During the audit, the working tree showed uncommitted modifications to files
outside this plan's scope, likely from a parallel agent (phase 07 or 08):

- `src/vkdownloader/services/downloader_throttle.py` — 24 lines changed
- `src/vkdownloader/services/ffmpeg_utils.py` — 12 lines changed
- `src/vkdownloader/services/segment_downloader.py` — 21 lines changed
- `tests/test_downloader_throttle.py` — 34 lines added
- `tests/test_ffmpeg_utils.py` — 44 lines added
- `docs/11-guides/configuration.md` — 1 line added (download_timeout docs)
- `src/vkdownloader/config.py` — 8 lines changed (download_timeout description)

These changes affect the `download_timeout`/`ffmpeg` boundary, which is **not**
covered by any block in this plan (B1–B8). The changes were left untouched.
