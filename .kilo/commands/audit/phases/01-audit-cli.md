---
name: 01-cli
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 01 Audit — CLI Entry Point & Command Layer

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the CLI application's structure:

1. **Entry Point Discovery** — Locate the CLI entry point (Typer app), identify all registered commands, discover command options/flags, map the CLI-to-service call chain.
2. **Command Layer Mapping** — For each command: what service does it invoke? What config does it require? How are errors caught and displayed?
3. **Dependency Flow** — Trace how the CLI layer imports from the service/core layer. Verify no reverse imports (core importing from CLI).
4. **Runtime Behavior** — How does the app start? How are async operations bridged to the sync CLI context? How is the event loop managed?

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Import Verification

Attempt to import the CLI entry point module. Verify no dependency is missing or broken.

- Capture traceback on failure. A broken import is CRITICAL.
- Verify all submodules (core, models, services) are importable.

### Step R2 — CLI Help Verification

Run each CLI command with `--help` flag. Verify:

- All commands produce help output without errors.
- All options/flags are documented.
- No crashes on help display.

### Step R3 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.
- Any errors or warnings are direct evidence.

### Step R4 — Run Test Suite

Run the project's test suite.

- Record pass/fail counts, skipped tests, and failure output.
- Any failing test is evidence of a real bug.

---

## Audit Scope

CLI entry point, command definitions, option parsing, error presentation, layer boundary between CLI and service/core.

---

## Audit Dimensions

### 1. Command Layer Integrity

| Check | Description |
|-------|-------------|
| Commands are thin | CLI handlers contain only argument parsing, service invocation, and error display — no business logic. |
| No business logic in CLI | Calculations, data transformations, and API calls live in the service layer, not in command handlers. |
| Consistent error handling | Every command catches exceptions and presents user-friendly messages. No raw tracebacks leak to the user. |
| All commands functional | Every registered command can be invoked (with `--help` at minimum) without crashing. |
| Options validation | Invalid options/flags are rejected with clear error messages, not silent defaults. |

**Evidence required:** Read each command handler. Verify it delegates to a service/core function rather than implementing logic inline. Run `--help` for each command.

### 2. Layer Boundary Enforcement

| Check | Description |
|-------|-------------|
| CLI imports only from core/service | The CLI layer never imports from unrelated modules or implements its own business logic. |
| No reverse imports | Core/service modules do not import from the CLI layer. |
| Dependency direction | Dependencies flow: CLI → Service → Core (models, utils, readers). No circular imports. |

**Evidence required:** Trace import chains. Search for any `from ...app` or `from ...cli` imports inside core/service modules.

### 3. Async/Sync Bridge Correctness

| Check | Description |
|-------|-------------|
| Async operations properly bridged | If the service layer uses async (e.g., Telethon), the CLI properly manages the event loop (`asyncio.run()` or equivalent). |
| No event loop conflicts | No nested event loops, no `asyncio.run()` inside already-running loop. |
| Graceful interruption | `KeyboardInterrupt` is caught and handled cleanly without stack traces. |

**Evidence required:** Read the CLI entry point and the service's sync wrapper. Trace how `asyncio` is used. Check for `KeyboardInterrupt` handling.

### 4. User Experience

| Check | Description |
|-------|-------------|
| Progress feedback | Long-running operations show progress indicators or status messages. |
| Error messages are actionable | Error messages tell the user what went wrong and what to do next (e.g., "Run 'mko init' first"). |
| Exit codes are meaningful | Success returns 0, errors return non-zero. Different error types use distinct exit codes where appropriate. |

**Evidence required:** Read error handling code. Trigger error conditions (e.g., missing config) and verify the output is helpful.

---

## Report Output

Write findings to: `.ai/audit/01-cli/findings.md` using template `.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `CLI-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — import errors, CLI output, linter errors, test failures.
  2. **Not just:** "violates invariant X" — show the exact code that violates it and the exact consequence.
