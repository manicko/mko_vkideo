---
name: 06-data-flow
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 06 Audit — End-to-End Data Flow

## Purpose

This phase audits how data moves through the system from the **entry point** to the
**final side effect** (a file written, a message sent, a download completed, etc.),
and back out as user-visible output. It focuses on the *integrity, completeness, and
correctness* of transformations across layers — not the internals of a single module.

This file is written as a **reusable handbook** for the data-flow phase of any audit.
It deliberately avoids naming specific files, function names, or paths — instead it
describes *what to trace and verify*. Apply it to whatever pipeline the current
system actually implements.

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, trace the complete data flow. The pipeline shape is
system-specific (e.g. CLI command → config load → external fetch → extract → process
→ write output → cleanup). Do not assume a fixed list of stages — enumerate the real
path the data actually takes.

1. **Full Pipeline Mapping** — Trace the entire path from the entry point through
   every layer: command/request parsing → configuration loading → external data
   acquisition → raw data → extraction/parsing → transformation/enrichment →
   dispatch to output → side-effect (file/binary/network) → cleanup/reporting.
2. **Config Propagation Trace** — For each configuration section, trace exactly how
   it flows from source (file/env/vars) → settings model → service constructor →
   function parameter. Identify every hop and any place a value is copied, renamed,
   or transformed.
3. **Unit-of-Work Lifecycle** — Pick a single unit of work (one item, one record,
   one URL) and trace it from input to output. Document every transformation and
   every point where data could be dropped, duplicated, or altered.
4. **Error Path Mapping** — For each stage, identify what happens on failure. Does
   the error propagate correctly? Is partial state cleaned up? Does one failed unit
   block the rest? Is the user told what failed and why?
5. **Concurrency Map (if applicable)** — If the system processes multiple units
   concurrently, map how shared state (progress, counters, output paths, backoff
   coordinators) is shared and whether it is safe.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the
commands provided in the project's commands file. Skip only if a step is impossible
— document why.**

### Step R1 — Import Full Pipeline

Import the entry point, the config/settings reader, and all service modules.
Verify the full chain is importable.

### Step R2 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.

### Step R3 — Run Test Suite

Run the complete test suite.

- Record pass/fail counts and failure output.

---

## Audit Scope

End-to-end data flow from invocation through config loading, data acquisition,
processing, output, and cleanup. Cross-layer interaction and data-integrity
verification.

---

## Audit Dimensions

> For each dimension, adapt the concrete checks to the pipeline the system actually
> has. A dimension is omitted from the report if no problem is found in it.

### 1. Config-to-Service Propagation

**Trace each configuration section from source to its final consumer. Document every hop.**

| Aspect | What to verify |
|--------|----------------|
| Each config section reaches its consumer | For every settings group, verify all fields propagate to the service/function that uses them — no silent drops. |
| Field-level trace | For each field: source key → model field → constructor parameter → function call. A missing or broken hop is a finding. |
| No ignored fields | Every field defined in the settings model is actually consumed somewhere; unused fields are dead config (investigate, do not assume delete). |
| No hardcoded overrides | The pipeline does not bypass configuration with literals when the value is configurable. |

**Evidence required:** For each field, document the full hop chain. If any hop is
missing, broken, or shadowed by a hardcoded value, that is a finding.

### 2. Unit-of-Work Lifecycle Trace

**Trace a single unit of work from input to output. Document every transformation.**

| Stage | What to verify |
|-------|----------------|
| Acquisition | The external/raw data is fetched with the correct inputs (id, range, URL, query). |
| Extraction / parsing | Raw data is parsed into the internal model with the correct filter and selection logic. |
| Transformation / enrichment | Each transformation (resize, sanitize, format, select) preserves the data it should and changes only what it should. |
| Dispatch object | The object handed to the output stage has all required fields populated. |
| Output stage | The dispatch reaches the external side-effect (write/network call) with the correct parameters. |
| Cleanup / summary | Temporary or cached artifacts are removed; the user-visible summary reflects reality. |

**If any transformation is incorrect, missing, or loses data, that is a finding.**

### 3. Multi-Target / Fan-Out Correctness (if applicable)

| Check | Description |
|-------|-------------|
| Each target gets its own data | Units scoped to target A are not sent/processed for target B. |
| Per-target parameters are respected | Target-specific parameters (delays, topics, ranges, options) are correctly scoped and not applied globally or cross-contaminated. |
| All targets are processed | Every item in the config/input list is handled, not just the first. |
| Empty targets are handled | A target with no matching work is skipped gracefully (no crash, no empty/garbage output). |

**Evidence required:** Read the fan-out loop. Verify units are correctly scoped to
each target and that the loop never silently stops early.

### 4. Error Propagation & Cleanup

| Check | Description |
|-------|-------------|
| Config error stops before side-effects | If configuration is invalid, the entry point reports the error and exits before attempting any external work. |
| Acquisition failure is handled | If the external fetch returns no data or errors, the system logs and continues (or exits gracefully) — it does not crash or hang. |
| One unit's failure is isolated | If processing one unit fails, other units are still processed (no global abort unless designed to). |
| Sub-operation failure is non-fatal where appropriate | A recoverable sub-step failure (e.g. one transformation) does not discard the whole unit unless required. |
| Cleanup runs on success | After the pipeline completes, temporary/cached artifacts are removed. |
| Cleanup runs on failure | If the pipeline fails mid-way, cleanup still runs (`try/finally` or equivalent). |
| Interruption is handled | Pressing Ctrl+C / sending SIGINT stops gracefully without stack traces or orphaned resources. |

**Evidence required:** Read error handling at each stage. Verify `try/finally` or
context managers are used where needed. Confirm cleanup is called in all exit paths.

### 5. Data Integrity

| Check | Description |
|-------|-------------|
| No data loss between stages | Every input that passes the filter becomes an output unit. No rows/items are silently dropped. |
| References are valid | Paths/IDs/URLs derived from input are resolved correctly against the intended base, with no traversal or mis-scoping. |
| Content is preserved | Text/content is not truncated, mutated, double-encoded, or escaped incorrectly during transformation. |
| Counts are accurate | Progress counters, totals, and indices correctly reflect actual work (watch for off-by-one errors). |
| Idempotency / output naming | Output filenames or keys are unique and deterministic; concurrent units do not collide or overwrite. |

**Evidence required:** Trace data through each transformation. Check for off-by-one
errors, truncation, incorrect path resolution, and naming collisions under concurrency.

### 6. Concurrency Safety (if applicable)

| Check | Description |
|-------|-------------|
| Shared state is synchronized | Progress managers, counters, and coordinators shared across concurrent units are protected against races. |
| Resources are not oversubscribed | A shared external client/session is not used in a way that violates the external system's concurrency assumptions. |
| Cancellation propagates | When one unit is cancelled (or the batch is interrupted), in-flight work is cancelled cleanly and remaining tasks are not orphaned. |

**Evidence required:** Identify every shared object across concurrent units. Verify
the synchronization claim holds by reading the access sites, not by assumption.

---

## Report Output

Write findings to: `/.ai/audit/06-data-flow/findings.md` using template `/.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `DF-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — traced data flow showing where the break occurs, test failures, missing error handlers, or captured runtime output.
  2. **Not just:** "violates invariant X" — show the exact stage, the exact data, and the exact consequence (lost unit, wrong target, orphaned artifact, miscounted progress, race condition).
