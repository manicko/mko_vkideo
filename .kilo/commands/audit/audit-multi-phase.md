---
name: audit-multi-phase
description: Execute full multi-agent audit pipeline using orchestrator coordination, executor subagents, and validator subagents with retry logic
alwaysApply: false
---

<objective>
Execute the complete multi-agent audit pipeline: prepare context, execute all phases with executors, validate findings.
Max allowed parallel subagents = 2
Do not launch agents in background.
If stop or break prefer resume old session not launching new agent.

</objective>

<process>



## 0 Select Phases

list of files in `.kilo/commands/audit/phases/`
filter out `99-audit-validate.md`.

Present the list to the user as a numbered table:

| # | Phase | File |
|---|-------|------|
| {N} | {name} | `{filename}` |
...

**Ask the user:** which phases to execute? Options:
- `all` — run all listed phases
- comma-separated numbers (e.g. `1,3,4`) — run selected phases only

Store the result as `{SELECTED_PHASES}`.
From `{SELECTED_PHASES}` parse each remaining filename (`NN-audit-name.md`) to extract phase number and name.


## 1. Gather Base Layer Context (once)


Read `.ai/context/commands.md` for verification commands.
Read `.ai/context/python-code-standards.md` for project code standards.
List documentation structure from `docs/` folder.
Run `git rev-parse HEAD` and capture its output as `{COMMIT_SHA}`.
Run `git status --porcelain` and capture its output as `{WORKTREE_STATUS}`.

Set variables:
- `{BASE_CONTEXT}` = summary of the above files, **including** `{COMMIT_SHA}` and the
  working-tree state (clean if `{WORKTREE_STATUS}` is empty, dirty otherwise)
- `{REPORT_TEMPLATE_PATH}` = `.ai/audit/templates/audit-findings.md`

*DO NOT* Read executor role or executor tasks and templates, just provide links
*DO NOT* Read production code, full documentation content

Every file named in this step must exist. If one does not, name the missing file in the
run's closing output and continue with what is present — a read that silently yields nothing
is the defect this step exists to prevent.


## Refuse Dirty Tree (hard stop)

Run `git status --porcelain -- src tests docs pyproject.toml`.

If the output is non-empty, **STOP** — refuse to start phases:

> **AUDIT REFUSED: working tree is dirty.** The audit pipeline measures a
> resolved commit, not uncommitted changes. Commit or stash before starting.
>
> Dirty paths:
> {lines from `git status --porcelain -- src tests docs pyproject.toml`}

No phase may start against a dirty tree.


## 2. Execute Phase Loop

Set every counter below before the loop starts. **Each number the closing output prints
comes from exactly one of them, and no counter is printed that is not named here.**

- `{PHASES_SELECTED}` — the count of files in `{SELECTED_PHASES}`. Set here, never incremented.
- `{PHASES_COMPLETED}` = 0.
- `{PHASES_VALIDATED}` = 0.
- `{FINDINGS_VALIDATED}` = 0 — findings counted from a validation store.
- `{FINDINGS_UNVALIDATED}` = 0 — findings counted from a source report, because the
  validator did not run for that phase.
- `{SEV_CRITICAL}` = 0, `{SEV_HIGH}` = 0, `{SEV_MEDIUM}` = 0, `{SEV_LOW}` = 0.

For each phase file in `{SELECTED_PHASES}` 

<phase_loop>

### 2.1 Extract Phase Metadata
- `{TASK_PATH}` = full path to phase file
- `{PHASE_NUMBER}`, `{PHASE_NAME}` = parsed from filename `NN-audit-name.md`
- `{OUTPUT_PATH}` = `.ai/audit/{PHASE_NUMBER}-{PHASE_NAME}/findings.md`

### 2.2 Launch Executor
Max allowed parallel subagents = 2
```
Task(
  prompt="Read and execute phase task: {TASK_PATH}n"
       + "Write findings to: {OUTPUT_PATH}\n"
       + "Report template: {REPORT_TEMPLATE_PATH}\n"
       + "Base context: {BASE_CONTEXT}\n"
       + "problems_only = TRUE\n"
       + "**Important: Never change any code files.**\n",
  agent="auditor",
  mode = "subagent",
  description="Execute audit phase {PHASE_NUMBER} - {PHASE_NAME}"
)
```

### 2.3 Verify Executor Output
Check that `{OUTPUT_PATH}` exists and is not empty.
If missing or empty: retry once, then escalate on second failure.

On a pass: `{PHASES_COMPLETED}` = `{PHASES_COMPLETED}` + 1.

### 2.4 Launch Validator

Launch the Validator for **every** selected phase. There is no precondition and no
threshold: this step states no condition, so none is evaluated and none can be silently
skipped.

```
Task(
  prompt="Read validation task: .kilo/commands/audit/phases/99-audit-validate.md\n"
       + "Validate findings at: {OUTPUT_PATH}\n"
       + "Write validation report to: .ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md\n"
       + "Base context: {BASE_CONTEXT}\n"
       + "problems_only = TRUE\n"
       + "**Important: Never change any code files.**\n",
  agent = "validator",
  mode = "subagent",
  description="Validate phase {PHASE_NUMBER} - {PHASE_NAME}",
)
```

### 2.5 Verify Validation Output
Check that `.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md` exists.
If missing or empty: retry once, then escalate on second failure.

On a pass: `{PHASES_VALIDATED}` = `{PHASES_VALIDATED}` + 1, and accumulate this phase's
counts into the counters from one read of the store:

- `{FINDINGS_VALIDATED}` += the `Validated (unchanged)` count in the store's **Validation
  Summary** table. Read the number the store states. Do not recount the identifiers it
  lists, and do not sum a repeated table.
- `{SEV_CRITICAL}`, `{SEV_HIGH}`, `{SEV_MEDIUM}`, `{SEV_LOW}` += that store's per-severity
  counts, from the same read.

If the validator did not run for this phase, accumulate from `{OUTPUT_PATH}` instead and
label the source: `{FINDINGS_UNVALIDATED}` += its finding count, and the four `{SEV_*}`
bands += its per-severity counts, from the same read.

</phase_loop>

</process>

<output>

---------------------
AUDIT COMPLETE

Phases completed: {PHASES_COMPLETED}/{PHASES_SELECTED}

Phases validated: {PHASES_VALIDATED}/{PHASES_SELECTED}
Validated findings: {FINDINGS_VALIDATED} (read from validation stores)
Findings not validated: {FINDINGS_UNVALIDATED} (read from source reports; the validator did not run for these phases)

By severity:
- CRITICAL: {SEV_CRITICAL}
- HIGH: {SEV_HIGH}
- MEDIUM: {SEV_MEDIUM}
- LOW: {SEV_LOW}
---------------------

**Two lines are conditional, and the report says so.**
- When `{PHASES_VALIDATED}` is 0, the `Phases validated:` line and the `Validated findings:`
  line are replaced by the single line `Validated phases: 0 — the validator was launched for
  no phase.` No validation coverage is claimed.
- When `{FINDINGS_UNVALIDATED}` is 0, omit the `Findings not validated:` line.

Every placeholder above names exactly one counter initialised in `## 2`, and every counter
initialised in `## 2` is printed. The severity bands count the findings in scope for the
run, read from the validation store for each phase whose validator ran and from the source
report for each phase whose validator did not.

</output>

<retry_rules>

- Max 2 retry per phase (3 total attempts maximum)
- On second failure: escalate to user with structured failure report (phase number, error, missing outputs)
</retry_rules>

## Conflict Record — Plan 11 B3 Acceptance Criteria

**Conflict:** CF-6 / Conflict-8 — Plan 11 B3's acceptance criteria.

| Criterion | Status | Detail |
|---|---|---|
| AC1 | Stale | Baseline states 4 oracles; audit finds 3. |
| AC4 | Unsatisfiable | Enumerates four oracles, one already retired by `d572d96`. |
| AC6 | Unsatisfiable | Requires co-editing a clause alongside a deletion already in history. |

This is **RECORD-ONLY**: Plan 11's block is **not amended** by B14. The correction
belongs to Plan 11's owner.
