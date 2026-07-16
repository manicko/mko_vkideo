---
name: 01-cli
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 01 Audit — Entry Point & Command Layer

## Purpose

This phase audits the system's **user-facing entry point**: how commands/requests are
declared, parsed, and wired to the underlying layers. The goal is to find violations of
layer boundaries, business logic leaking into the entry layer, broken argument/option
handling, and poor error/UX presentation.

This file is written as a **reusable handbook** for the entry-point phase of any audit.
It deliberately avoids naming specific files, function names, or paths — instead it
describes *what to discover and verify*. Apply it to whatever entry mechanism the
current system actually has (CLI, web API, RPC, etc.).

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the entry-point structure:

1. **Entry Point Discovery** — Locate the application entry point (command router, app object, server bootstrap). Enumerate all registered commands/endpoints. Map the entry-to-service call chain.
2. **Command Layer Mapping** — For each command/endpoint: what downstream service does it invoke? What configuration does it require? How are errors caught and presented to the user?
3. **Dependency Flow** — Trace how the entry layer imports from the service/core layer. Verify no reverse imports (core importing from the entry layer).
4. **Runtime Behavior** — How does the app start? How are async/concurrent operations bridged to the entry context? How is the event loop / request lifecycle managed? How is cancellation or interruption handled?

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Import Verification

Attempt to import the entry-point module. Verify no dependency is missing or broken.

- Capture traceback on failure. A broken import is CRITICAL.
- Verify all downstream submodules (core, models, services) are importable.

### Step R2 — Entry Point Help / Schema Verification

Invoke the entry point's self-description (help output, OpenAPI schema, `--help`, route listing). Verify:

- All commands/endpoints are enumerated without errors.
- All options/parameters are documented.
- No crashes on self-description.

### Step R3 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.
- Any errors or warnings are direct evidence.

### Step R4 — Run Test Suite

Run the project's test suite, focusing on entry-layer tests.

- Record pass/fail counts, skipped tests, and failure output.
- Any failing test is evidence of a real bug.

---

## Audit Scope

Entry point, command/endpoint definitions, argument/parameter parsing, error presentation, and the boundary between the entry layer and the service/core layers.

---

## Audit Dimensions

> For each dimension, adapt the concrete checks to the entry mechanism the system
> actually has. A dimension is omitted from the report if no problem is found in it.

### 1. Command/Endpoint Layer Integrity

| Check | Description |
|-------|-------------|
| Handlers are thin | Entry handlers contain only parsing, downstream invocation, and result/error presentation — no business logic. |
| No business logic in entry layer | Calculations, data transformations, and external calls live in the service layer, not in handlers. |
| Consistent error handling | Every handler catches exceptions and presents user-friendly messages. No raw tracebacks leak to the user. |
| All commands/endpoints functional | Every registered route can be invoked (help/schema at minimum) without crashing. |
| Input validation | Invalid options/parameters are rejected with clear error messages, not silent defaults. |

**Evidence required:** Read each handler. Verify it delegates to a service/core function rather than implementing logic inline. Exercise help/schema for each command/endpoint.

### 2. Layer Boundary Enforcement

| Check | Description |
|-------|-------------|
| Entry imports only from core/service | The entry layer never imports unrelated modules or re-implements business logic. |
| No reverse imports | Core/service modules do not import from the entry layer. |
| Dependency direction | Dependencies flow: entry → service → core (models, utils). No circular imports. |

**Evidence required:** Trace import chains. Search for any import of the entry layer inside core/service modules.

### 3. Async/Concurrency Bridge Correctness

| Check | Description |
|-------|-------------|
| Async operations properly bridged | If the service layer uses async/concurrency, the entry layer manages the loop/context correctly (`asyncio.run`, background tasks, request scope). |
| No loop/context conflicts | No nested event loops, no double-running, no leaked contexts across requests. |
| Graceful interruption | Cancellation (Ctrl+C / request abort) is caught and handled cleanly without stack traces or orphaned work. |

**Evidence required:** Read the entry point and the service's sync/async wrapper. Trace how concurrency is managed. Check for interruption handling.

### 4. User Experience

| Check | Description |
|-------|-------------|
| Progress / status feedback | Long-running operations show progress indicators or status messages. |
| Actionable error messages | Errors tell the user what went wrong and what to do next (e.g., "run init first", "check config"). |
| Meaningful status codes | Success returns the success code; errors return distinct non-success codes where appropriate. |

**Evidence required:** Read error handling code. Trigger error conditions (e.g., missing config) and verify the output is helpful.

---

## Report Output

Write findings to: `/.ai/audit/01-cli/findings.md` using template `/.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `CLI-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — import errors, entry-point output, linter errors, test failures.
  2. **Not just:** "violates invariant X" — show the exact code that violates it and the exact consequence.
