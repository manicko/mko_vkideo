---
name: 03-services
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 03 Audit — Service Layer & Business Logic

## Purpose

This phase audits the **core business logic**: service classes, processing units, data
transformations, and the data models that move between them. The goal is to find
violations of single responsibility, tangled dependencies, incorrect transformations,
and dead code.

This file is written as a **reusable handbook** for the service-layer phase of any
audit. It deliberately avoids naming specific files, function names, or paths — instead
it describes *what to discover and verify*. Apply it to whatever the system's core
processing units actually are (extractors, processors, caches, posters, downloaders,
etc.).

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the service-layer architecture:

1. **Service Discovery** — Locate all service/processing classes. Map their responsibilities: what does each do? What are its dependencies?
2. **Class Responsibility Mapping** — For each class: is it a service, a processor, a reader, a cache, a model? Does it have a single responsibility?
3. **Dependency Graph** — Map how services depend on each other. Identify the composition root (where services are instantiated and wired together).
4. **Data Transformation Chain** — Trace how raw external data is transformed into internal models, then into output/side-effects. Identify each transformation step.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Import Verification

Import all service modules. Verify no import errors or missing dependencies.

### Step R2 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.

### Step R3 — Run Test Suite

Run the project's test suite, focusing on service-layer tests.

- Record pass/fail counts and failure output.

### Step R4 — Dead Code Search

Search for functions/methods defined but never called outside tests.

- Record each instance with file path and line number.

---

## Audit Scope

Service classes, processing units, data models, business logic, and data transformations between layers.

---

## Audit Dimensions

> For each dimension, adapt the concrete checks to the processing units the system
> actually has. A dimension is omitted from the report if no problem is found in it.

### 1. Single Responsibility

| Check | Description |
|-------|-------------|
| Each class has one reason to change | A caching unit handles only caching. A processing unit handles only its transformation. A communication unit handles only external I/O. |
| No god classes | No single class handles config loading, data fetching, transformation, AND output. |
| Separation of concerns | Distinct responsibilities live in distinct units (transform vs I/O vs cache). |

**Evidence required:** Read each service class. If a class has methods that belong to different domains, that is a finding.

### 2. Dependency Direction

| Check | Description |
|-------|-------------|
| Services depend on models/abstractions | Services receive typed models, not raw dicts or parser output. |
| No circular dependencies | Service A does not import Service B while Service B imports Service A. |
| Composition root is clear | The top-level orchestrator composes sub-services; sub-services do not compose the orchestrator. |

**Evidence required:** Trace import chains between service classes. Verify the dependency graph is acyclic.

### 3. Transformation Correctness (per processing unit)

| Check | Description |
|-------|-------------|
| Caching works correctly | Derived artifacts are cached and reused. Cache keys are deterministic (same input → same cache path). |
| Errors handled gracefully | If an item cannot be transformed, the error is caught and a safe fallback is used (not a crash). |
| Cleanup removes unused files | Temporary/cached artifacts not used in the current run are removed. |
| No orphaned temp files | After the run completes (success or failure), no temporary files remain. |

**Evidence required:** Read each processing/cache unit. Trace the full lifecycle: transform → cache → use → cleanup. Check for `try/finally` around file operations.

### 4. Processing Logic Correctness

| Check | Description |
|-------|-------------|
| Filter logic is correct | Items are filtered by the configured column/value. Edge cases (out-of-range, empty) are handled as intended, not silently dropped. |
| Extraction handles variants | Input variants are handled (e.g., single vs multiple values, file vs directory). |
| Limits are enforced | Configured limits (max items, max size) are applied. |
| Empty results handled | Units with no data are handled gracefully (no empty/garbage output). |

**Evidence required:** Read the processing unit's core method. Trace the filter/extraction logic. Check edge cases.

### 5. Output / Posting Correctness

| Check | Description |
|-------|-------------|
| Retry logic works | Transient external errors (rate limits, temporary unavailability) trigger retries with appropriate backoff. |
| Non-retryable errors fail fast | Permanent errors do not trigger infinite retries. |
| Ordering/shuffling is correct | Item order is respected or randomized as configured. |
| Delay between items is respected | Per-item delay is converted to the correct unit and applied. |
| Target scoping is correct | Target identifiers (chat_id, topic, destination) are passed correctly to the external call. |

**Evidence required:** Read the output/posting unit and its loop. Verify retry logic, delay handling, and target scoping.

### 6. Data Model Integrity

| Check | Description |
|-------|-------------|
| Model carries all required data | The unit-of-work model includes all fields needed downstream. |
| Status tracking present | The model has a status field to track success/failure where relevant. |
| No business logic in model | The model is a data container, not a service. |

**Evidence required:** Read the model definition. Verify it is a pure data structure with no methods that belong in a service.

---

## Report Output

Write findings to: `/.ai/audit/03-services/findings.md` using template `/.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `SRV-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — import errors, test failures, dead code proof (file:line), logic bugs.
  2. **Not just:** "violates invariant X" — show the exact code that violates it and the exact consequence.
