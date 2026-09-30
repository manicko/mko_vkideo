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
Read `.kilo/rules/project.md` for project guidelines.
Read `.kilo/rules/commands.md` for command conventions.
List documentation structure from `docs/` folder.

Set variables:
- `{BASE_CONTEXT}` = summary of the above files
- `{REPORT_TEMPLATE_PATH}` = `.ai/audit/templates/audit-findings.md`

*DO NOT* Read executor role or executor tasks and templates, just provide links
*DO NOT* Read production code, full documentation content


## 2. Execute Phase Loop

`{TOTAL_PHASES}` = number of entries in `{SELECTED_PHASES}`.
Before the loop, initialise `{COMPLETED_PHASES}`, `{VALIDATED_PHASES}`,
`{VALIDATED_FINDINGS}`, `{CRITICAL_COUNT}`, `{HIGH_COUNT}`,
`{MEDIUM_COUNT}` and `{LOW_COUNT}` to 0.

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

When the check passes, increment `{COMPLETED_PHASES}`.

### 2.4 Launch Validator

Launch the Validator for every selected phase. The gate that previously
decided whether to do so is removed: its condition was not defined anywhere
in the command, the validator's handbook, or the report format, so it could
never be evaluated and was always applied by unrecorded judgement. The
validator's per-finding decisions carry the triage instead.

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

When the file is present — i.e. the Validator ran for this phase — increment
`{VALIDATED_PHASES}`, add the number of findings it kept (not rejected) to
`{VALIDATED_FINDINGS}`, and fold its severity tally into `{CRITICAL_COUNT}`,
`{HIGH_COUNT}`, `{MEDIUM_COUNT}` and `{LOW_COUNT}`. A phase whose findings file
held no findings increments `{VALIDATED_PHASES}` but contributes nothing to
`{VALIDATED_FINDINGS}`, so it cannot claim validation coverage it did not
produce.

</phase_loop>

</process>

<output>

---------------------
AUDIT COMPLETE

Phases completed: {COMPLETED_PHASES}/{TOTAL_PHASES}

Emit the validated-findings block only while `{VALIDATED_PHASES}` > 0
(the Validator runs for every selected phase, so the block is absent only
when no phase was executed):
Validated findings: {VALIDATED_FINDINGS} total

By severity:
- CRITICAL: {CRITICAL_COUNT}
- HIGH: {HIGH_COUNT}
- MEDIUM: {MEDIUM_COUNT}
- LOW: {LOW_COUNT}
---------------------

</output>

<retry_rules>

- Max 2 retry per phase (3 total attempts maximum)
- On second failure: escalate to user with structured failure report (phase number, error, missing outputs)
</retry_rules>
