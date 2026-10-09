# Execution Plan 19 — Entry-Architecture Audit Fixes (Remaining Blocks)

> **Source plan (read-only):** `.ai/plans/05-entry-architecture-audit-fixes_fix.md`
> **Audit report (read-only):** `.ai/audit/problems/05-entry-architecture-audit-fixes_audit_report.md`
> **Cross-phase audit report (read-only):** `.ai/audit/problems/06-config-audit-fixes.md`
> **Code context:** from initial Auditor (`ses_ede677c55ffecX9B0vRICdBoxl`) — four-command verification matrix ALL PASS (ruff check clean, ruff format clean, mypy src clean 31 files, pytest 1010 passed / 3 skipped).
> **Git HEAD:** `3a35b69`
> **Audit-report HEAD:** `009f9fc`

---

## 0. Current State (post-audit commits)

The audit report was written at commit `009f9fc`. Since that commit, the following commits were made (HEAD `3a35b69`):

| Commit | Subject | Block | Status |
|--------|---------|-------|--------|
| `b770e83` | `fix(config): restore .python-version, fix docs, remove Any types` | Pre-existing fixes (from 06-config audit) | Done |
| `981cead` | `fix(audit): repoint audit-refine base-context reads to the real rules files` | B10-D5 (partial, WRONG target) | Partial — needs correction |
| `e04659c` | `refactor(imports): empty the eager package roots and hoist the justified deferral` | B7 | **Done** |
| `90975a6` | `refactor(config): source every download-timeout default from one constant` | B8 | **Done** |
| `3b95d65` | `docs(structure): record the entry-layer import cost and reconcile the layer descriptions` | B13 | **Done** |
| `3a35b69` | `B12: anchor is_valid_video_url…` | Unrelated (not B12-block) | N/A |

### Already implemented
- **B1–B6:** Done (commits `d62671b`–`0790157`, before audit)
- **B7:** Done (commit `e04659c`) — empty package roots, hoisted deferrals, `test_import_graph.py` added, STRUCT.md utils listing corrected, `EXPECTED_SDIST_ENTRIES` updated
- **B8:** Done (commit `90975a6`) — constant renamed to public, 9 literals replaced, invariant test added
- **B13:** Done (commit `3b95d65`) — entry-layer import cost recorded in STRUCT.md
- **B10-D5 (partial):** Commit `981cead` repointed `audit-refine.md` from `AGENTS.md` to `.kilo/rules/project.md` + `.kilo/rules/commands.md` — **this is the WRONG target per the plan** (§10 code hint explicitly prohibits `.kilo/rules/project.md`; the correct target is `.ai/context/python-code-standards.md`). Also only `audit-refine.md` was changed, not `audit-multi-phase.md`.

### Remaining work

| Block | Finding | What remains |
|-------|---------|--------------|
| **B9** | VAL-110, VAL-111 | Report header still uses `**Executor:**` instead of `**Author:**` / `**Validated by:**`; decision-slot format differs from plan's Action/Detail/See-also structure; template frontmatter still names unreachable role |
| **B10-D4** | VAL-109, VAL-107, VAL-112 | Phase-qualified `VAL-{NN}-{NNN}` identifiers NOT applied in `99-audit-validate.md`; R0 identifier map not updated; Edge Cases bullet not updated; Validation Summary row not updated |
| **B10-D5 (correction)** | VAL-109 | Revert wrong `.kilo/rules/project.md` repoint in `audit-refine.md`; repoint both `audit-multi-phase.md` AND `audit-refine.md` to `.ai/context/python-code-standards.md` per the task brief §10 code hint |
| **B10-D6 (verification)** | VAL-107 | Verify gate removal and counter rebuild match the task brief §10; the audit report says "D6 gate removal done" but did not confirm the full counter-rebuild |

### Deferred (D7 = DEFER)
- **B11** (ENT-008) — not implemented, deferred
- **B12** (ENT-004) — not implemented, deferred

### Pre-existing issues (from 06-config-audit-fixes.md)
- Problem 1 (`.python-version` deletion) — **FIXED** by `b770e83`
- Problem 2 (stale Python version in `docs/01-tools/installation.md`) — **FIXED** by `b770e83` (now "Python 3.12 or higher")
- Problem 3 (`Any` in `config.py` and `cli.py`) — **FIXED** by `b770e83`
- Problem 3 additional (`Any` in `extractor.py` and `ytdlp_downloader.py`) — NOT in scope for this plan
- Problem 4 (`--max-retries` doc drift) — OUT OF SCOPE (phase 08)
- Problem 5 (BOM acceptance criterion) — DEFERRED to phase 10

### DoD gap note
The plan §8.9 requires "exactly 4 skips" but the current tree shows 3 skipped. The plan was authored against a 486-test baseline; the current tree has 1010 tests. The verification floor should be treated as **1010 passed, 3 skipped** for the remaining blocks. This metadata gap does not affect code correctness.

---

## 1. Remaining Execution Order

```
Block 9   audit report contract          (VAL-110, VAL-111)   — no incoming edge
Block 10  pipeline context, gate, IDs    (VAL-109, VAL-107, VAL-112) — depends on B1 (done)
```

B7, B8, B13 are already done and require only verification (tests pass, diffs reviewed).

**No new `src/` modules may be added** (packaging gate: `EXPECTED_SDIST_ENTRIES`).

### Agent matrix for remaining blocks

| Block | Auditor | Researcher | Planner | Implementor | Validator |
|-------|---------|------------|---------|-------------|-----------|
| B9 | not required (D3 already resolved in plan §9.2) | not required | not required (brief §9.2 exists) | **required** | **required** |
| B10 | not required (D4/D5/D6 already resolved in plan §10) | not required (decisions resolved) | not required (brief §10 exists) | **required** | **required** |

The code_context for B9/B10 files was not covered by the initial Auditor. A targeted Auditor inspection is launched first to capture the current state before implementation.

---

## 2. Block Specifications (remaining)

### Block 9 — Audit Report Contract (partial completion)

**Findings:** VAL-110 (HIGH), VAL-111 (MEDIUM)

**What was done (before audit):** Commits added `RUNTIME-ERROR` label to both role files; a decision slot exists in the template.

**What is missing (from audit report Problem 3):**
1. `.ai/audit/templates/audit-findings.md` report header still uses `**Executor:** auditor` instead of `**Author:** auditor` and `**Validated by:** {validator | not run}`
2. The decision-slot format differs from the plan's Action/Detail/See-also structure
3. Template frontmatter still names the unreachable executor role

**Task brief:** See plan §9.2 (Brief 2 — Block 9). All decisions (D3 Route A) already resolved.

**Files to touch:**
- `.ai/audit/templates/audit-findings.md` — frontmatter `agent` field, report header, finding-block decision slot, mandatory-fields reference, classification guide
- `.kilo/agents/auditor.md` — label list (add RUNTIME-ERROR if missing)
- `.kilo/agents/validator.md` — both label lists (add RUNTIME-ERROR if missing)

**Prohibition:** Do NOT edit any existing findings.md or validation file (D3 Route C is blocked by commit hygiene).

**Commit:** `git add .ai/audit/templates/audit-findings.md .kilo/agents/auditor.md .kilo/agents/validator.md`
Subject: `fix(audit): make the report template legal to the roles that write it`

---

### Block 10 — Pipeline Context, Gate, Identifier Honesty (partial completion)

**Findings:** VAL-109 (MEDIUM), VAL-107 (HIGH), VAL-112 (MEDIUM)

**What was done:**
- D6 gate removal: done (before audit, confirmed by audit report)
- D5 partial: commit `981cead` repointed `audit-refine.md` but to the WRONG target (`.kilo/rules/project.md` instead of `.ai/context/python-code-standards.md`), and did NOT touch `audit-multi-phase.md`

**What is missing:**
1. **D4:** Phase-qualified `VAL-{NN}-{NNN}` identifiers in `99-audit-validate.md` — not applied
2. **D5 correction:** Fix `audit-refine.md` to use `.ai/context/python-code-standards.md`; apply same repoint to `audit-multi-phase.md`; add existence guard
3. **D6 verification:** Confirm counter rebuild matches the task brief §10 specification

**Task brief:** See plan §10 (Task brief — Block 10). All decisions (D4 Route A, D5 Route B, D6 Route B) already resolved.

**Files to touch:**
- `.kilo/commands/audit/audit-multi-phase.md` — D5 repoint (base context read), D6 counter rebuild (if incomplete)
- `.kilo/commands/audit/audit-refine.md` — D5 correction (change `.kilo/rules/project.md` back to `.ai/context/python-code-standards.md`)
- `.kilo/commands/audit/phases/99-audit-validate.md` — D4 phase-qualified identifiers, R0 identifier map, Edge Cases bullet, Validation Summary row, Block-1 stale cross-reference

**Prohibition:** Do NOT touch any `.ai/audit/**/findings.md` or `.ai/audit/99-validation/*.md` files.

**Commit:** `git add .kilo/commands/audit/audit-multi-phase.md .kilo/commands/audit/audit-refine.md .kilo/commands/audit/phases/99-audit-validate.md`
Subject: `fix(audit): give the pipeline truthful context, an evaluable gate and non-colliding identifiers`

---

## 3. Verification floor

```
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest -q -rs
```

Current baseline: 1010 passed, 3 skipped. All blocks must not reduce the pass count (minus tests removed by signature changes, plus tests added by the block).

---

## 4. Commit hygiene

- Stage by explicit path only
- Never `git add -A`, `git add .`, `git add -u`, `git reset`, `git checkout`, `git stash`
- One block is one commit
- Never amend or force-push
- No `.ai/` paths staged except `.ai/audit/templates/audit-findings.md` (Block 9 only)
