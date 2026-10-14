# Audit Problems Report — Plan 05

**Plan:** `05-entry-architecture-audit-fixes.md` (entry-architecture audit fixes)
**Audit date:** 2026-10-08
**Repository:** `vkdownloader` (`C:\py_exp\mko_vkideo`)
**Scope:** Verification of plan completion and problems found in code/docs during audit.

---

## Summary

The plan describes 13 blocks (B1–B13). Verification against the working tree at
`HEAD` (commit `009f9fc`) and the commit `d62671b..HEAD` range shows:

- **Blocks 1–6: Fully implemented.** Commits match the plan's expected subjects.
  `ruff check`, `ruff format --check`, `mypy src`, and `pytest` (excluding
  packaging tests) all pass.
- **Block 7: NOT implemented.** Package-root `__init__.py` files still carry
  re-exports and `__all__`; deferred imports remain; `test_import_graph.py`
  does not exist.
- **Block 8: NOT implemented.** Nine hardcoded timeout literals remain in
  `segment_downloader.py` and `ffmpeg_utils.py`; the constant retains a private
  name (`_DEFAULT_DOWNLOAD_TIMEOUT`).
- **Block 9: Partially implemented.** The `RUNTIME-ERROR` label was added to
  both role handbooks and a decision slot exists in the template, but the report
  header still uses `**Executor:**` instead of the planned `**Author:**` and
  `**Validated by:**` pair; the decision-slot format differs from the plan's
  Action/Detail/See-also structure.
- **Block 10: Partially implemented.** The gate was removed in
  `audit-multi-phase.md` (commit `19143b1`), but `audit-refine.md` still reads
  `AGENTS.md` (a non-existent file), the repoint target was `.kilo/rules/project.md`
  rather than `.ai/context/python-code-standards.md`, and the phase-qualified
  identifier format (`VAL-{NN}-{NNN}`) was not applied to the validate handbook.
- **Blocks 11–12: Not implemented (conditional on `D7`).** `D7` defaults to
  DEFER, so the absence of these blocks is expected. `ENT-008` is still
  classified as `mandatory` in the findings file, which conflicts with the
  plan's deferral recommendation.
- **Block 13: NOT implemented.** `docs/STRUCT.md` does not record the
  measured entry-layer import cost; the layer descriptions are not reconciled.

**Verdict:** The plan is **not complete** and **requires code rework**. It is
marked `_fix`.

---

## Problem 1 — Block 7: Package-root `__init__.py` files still carry re-exports

**Severity:** HIGH (plan not complete; code change required)

**Location:** `src/vkdownloader/{services,utils,models,infrastructure}/__init__.py`

**Status:** NOT implemented.

All four package-root `__init__.py` files still contain eager imports and
`__all__` re-export lists. The plan requires reducing each to just the package
docstring so that importing a package no longer transitively imports its
submodules.

| File | Current state | Plan requirement |
|------|--------------|-----------------|
| `services/__init__.py` | `from .quality import QualitySelector` + `__all__` | Docstring only |
| `utils/__init__.py` | Five-name `__all__` + four re-exports | Docstring only |
| `models/__init__.py` | Twelve-name `__all__` + re-exports | Docstring only |
| `infrastructure/__init__.py` | Three-name `__all__` + re-exports | Docstring only |

**Secondary effects:**
- `src/vkdownloader/exceptions.py` line 97–100 still has a deferred import
  (`from vkdownloader.utils.url_sanitizer import _strip_auth_params`) guarded by
  a comment explaining the import cycle. Block 7 would hoist this to module
  scope once the package roots are emptied.
- `tests/test_import_graph.py` (the plan's new invariant test) does not exist.
- `docs/STRUCT.md` line 41 still documents the five-name export list for
  `utils/__init__.py`, which would become wrong after Block 7.

---

## Problem 2 — Block 8: Hardcoded timeout literals persist

**Severity:** HIGH (plan not complete; code change required)

**Location:** `src/vkdownloader/services/segment_downloader.py`,
`src/vkdownloader/services/ffmpeg_utils.py`,
`src/vkdownloader/services/downloader_throttle.py`

**Status:** NOT implemented.

The constant exists in `downloader_throttle.py` line 20:

```python
_DEFAULT_DOWNLOAD_TIMEOUT: int = Settings.model_fields["download_timeout"].default
```

…but it is (a) still private (underscore prefix) and (b) unused — nine call
sites across `segment_downloader.py` and `ffmpeg_utils.py` still hard-code the
literal `300` (or `300.0` as a `float`).

| File | Line(s) | Literal |
|------|--------|---------|
| `segment_downloader.py` | 85, 165, 251, 316, 348, 404, 448 | `300` |
| `ffmpeg_utils.py` | 333, 403, 546 | `300.0` (float, also mis-typed: spec is `int`) |

No invariant test was added to `tests/test_config.py` asserting that every
`download_timeout` default equals `Settings.download_timeout.default`.

---

## Problem 3 — Block 9: Report-header provenance format not changed

**Severity:** MEDIUM (documentation drift; plan's format not applied)

**Location:** `.ai/audit/templates/audit-findings.md` lines 10–13

**Status:** Partially implemented.

The template frontmatter names `auditor` and the `RUNTIME-ERROR` label is
present in both role files (auditor.md line 260, validator.md lines 246 and
360). However, the report header at line 10 still reads:

```
**Executor:** auditor
```

The plan requires:

```
**Author:** auditor
**Validated by:** {validator | not run}
```

The existing `**Validated:** {yes|no}` status line is expected to remain
unchanged, which it does.

The decision slot at line 21 (`**Decision:** …`) uses a different field shape
than the plan's Action/Detail/See-also structure.

---

## Problem 4 — Block 10: D4 (phase-qualified identifiers) not applied to validate handbook

**Severity:** HIGH (plan not complete; identifier rule unenforced)

**Location:** `.kilo/commands/audit/phases/99-audit-validate.md` lines 435–441

**Status:** NOT implemented.

The Finding-Prefix section still states:

> "Use `VAL-` for all findings in this phase … and does not encode the phase
> number, so renumbering never invalidates a published finding ID."

The plan's D4 Route A requires phase-qualified identifiers
(`VAL-{NN}-{NNN}`) with a `{NN}` zero-padded phase number and a fixed-width
three-digit selector. This change was not applied.

---

## Problem 5 — Block 10: D5 repoint incomplete and wrong target

**Severity:** MEDIUM (broken reference + wrong target)

**Location:** `.kilo/commands/audit/audit-refine.md` line 19,
`.kilo/commands/audit/audit-multi-phase.md` line 43–44

**Status:** NOT implemented as planned.

- `audit-refine.md` line 19 still reads `AGENTS.md`, which **does not exist** in
  the repository (`Test-Path AGENTS.md → False`). This is a broken reference.
- `audit-multi-phase.md` was repointed to `.kilo/rules/project.md` and
  `.kilo/rules/commands.md` (commit `19143b1`), but the plan's D5 Route B
  requires repointing to `.ai/context/python-code-standards.md`, which does
  exist. The mismatch is recorded as an observation for phase 08 per the plan's
  D5 acceptance criterion, but the actual target diverges from the plan.

---

## Problem 6 — Block 13: `docs/STRUCT.md` entry-layer import cost not recorded

**Severity:** MEDIUM (documentation gap)

**Location:** `docs/STRUCT.md` line 50

**Status:** NOT implemented.

The entry-layer description reads:

```
- **Entry layer**: `cli.py`, `__main__.py` — argument parsing, Settings
  construction, error presentation, exit codes. No business logic or
  private-symbol imports from service/utils layers.
```

Block 13 requires recording the measured import cost (e.g., "importing the
entry layer takes N ms") in this line so the next reader sees the constraint
that justifies the deferred imports discussed in Block 7's E1 cycle experiment.
This cost is not present.

---

## Problem 7 — Pre-existing: `.python-version` deleted, breaks packaging tests

**Severity:** MEDIUM (pre-existing; not caused by this plan's blocks)

**Location:** Repository root (`.python-version` absent)

**Status:** Reported for awareness; also documented in
`.ai/audit/problems/06-config-audit-fixes.md` Problem 1.

Commit `009f9fc` deleted `.python-version` (content `3.12`), which remains in
`[tool.hatch.build.targets.sdist].include` at `pyproject.toml` line 61. This
causes two test failures:

- `tests/test_packaging.py::test_sdist_entry_set_matches_the_manifest`
- `tests/test_packaging.py::test_sdist_entry_count_matches_the_manifest`

Re-adding `.python-version` with content `3.12` resolves both without touching
this plan's code.

---

## Test verification

| Command | Result |
|---------|--------|
| `uv run ruff check src tests` | All checks passed |
| `uv run ruff format --check src tests` | 54 files already formatted |
| `uv run mypy src` | Success: no issues found in 31 source files |
| `uv run pytest -q -rs --ignore=tests/test_packaging.py` | 934 passed, 3 skipped |
| `uv run pytest -q -rs tests/test_packaging.py` | 2 failed (see Problem 7) |

The 3 skips are POSIX-only `killpg` tests, not the D-11 Windows
permission-mode skips referenced in the plan's baseline. The test count has
grown from the plan's baseline of 486 because subsequent audit phases added
test suites; the plan's block-specific tests are present where the blocks were
implemented (Blocks 1–6) and absent where they were not (Block 7's
`test_import_graph.py`, Block 8's invariant test).

---

## Notes on plan block verification

| Block | Commit(s) | Status | Evidence |
|-------|----------|--------|----------|
| B1 (VAL-106, VAL-108) | `d62671b` | Done | Gate filename alignment, rejected-findings preserved |
| B2 (VAL-103, ENT-014, CFG-001, CFG-002) | `ea44b3d` | Done | `_build_settings`, no `max_retries_override`, no `model_copy` |
| B3 (VAL-105) | `a335b2a` | Done | `_run_command_preamble` extracted; both commands call it |
| B4 (VAL-101, ENT-001, CFG-006) | `9394999` | Done | stderr route chosen (D1 Route B); `warn_unknown_env_vars` return consumed |
| B5 (ENT-002, ENT-003) | `397b62f` + `532f861` | Done | Error reporting decoupled from log sink; OSError arm narrowed to URL-file read |
| B6 (VAL-104, ENT-011, ENT-012) | `0790157` | Done | `clear_correlation_id` unbinds single key; no inner bind/clear in `download_video` |
| B7 (ENT-005, ENT-007, ENT-009) | — | **NOT done** | 4 package roots still have re-exports; deferred import in `exceptions.py` persists |
| B8 (ENT-010) | — | **NOT done** | 9 hardcoded literals remain; constant private; no invariant test |
| B9 (VAL-110, VAL-111) | `e443448` + `feb0a40` | Partial | RUNTIME-ERROR label present; decision slot present; header format wrong |
| B10 (VAL-109, VAL-107, VAL-112) | `19143b1` + `0a8fa97` | Partial | Gate removed (D6); D4 identifier format unchanged; D5 repoint incomplete |
| B11 (ENT-008) | — | Not done (D7=DEFER) | `_print_batch_summary` still in service layer; presentation not moved to CLI |
| B12 (ENT-004) | — | Not done (D7=DEFER) | Signal-handler ownership not unified |
| B13 (ENT-013 half) | — | **NOT done** | STRUCT.md import cost not recorded; layer reconciliation pending |
