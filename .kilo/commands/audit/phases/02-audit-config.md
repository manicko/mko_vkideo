---
name: 02-config
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 02 Audit — Configuration & Settings Models

## Purpose

This phase audits how the system is **configured**: the settings/data models, how
configuration is loaded and validated, where files live (user vs package), and how
config values reach consumers. The goal is to find validation gaps, path-resolution
bugs, leakage of secrets through templates, and dead or ignored config fields.

This file is written as a **reusable handbook** for the configuration phase of any
audit. It deliberately avoids naming specific files, function names, or paths — instead
it describes *what to discover and verify*. Apply it to whatever configuration system
the current project actually uses (Pydantic models + YAML/env, env-only, typed
settings, etc.).

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the configuration architecture:

1. **Config Model Discovery** — Locate all settings/data model classes. Map the model hierarchy (root model → sub-models). Identify all fields, their types, defaults, and validators.
2. **Config Loading Discovery** — Find where configuration is loaded (file/env/args), where validation happens, and where config is read from (package templates vs user directory).
3. **Path Resolution Discovery** — Map how paths are resolved. Identify where user config lives vs package templates, and whether a path-resolution utility is used consistently.
4. **Config Flow Discovery** — Trace how a config value travels from source → model → consumer. Identify every consumer of config values.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Import and Instantiate Models

Attempt to import all settings models. Instantiate the root model with valid and invalid data.

- Verify validators fire correctly on invalid data.
- Verify defaults are applied correctly.
- Capture any validation errors — they are evidence.

### Step R2 — Config Loading Verification

If a sample/test config exists, attempt to load it through the config reader.

- Verify the loaded model matches the source contents.
- Verify relative paths are resolved correctly.
- Test with missing/invalid config — verify clear error messages.

### Step R3 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.

### Step R4 — Run Test Suite

Run the project's test suite, focusing on config-related tests.

- Record pass/fail counts and failure output.

---

## Audit Scope

Settings/data models, configuration loading, path resolution, config validation, template/init copying, and config file templates.

---

## Audit Dimensions

> For each dimension, adapt the concrete checks to the configuration system the project
> actually has. A dimension is omitted from the report if no problem is found in it.

### 1. Settings Model Correctness

| Check | Description |
|-------|-------------|
| All config sections modeled | Every configuration area has a corresponding typed model/section. |
| No raw dicts in business logic | Services receive typed models, not raw dicts from the parser. |
| Field validation | Required fields have no defaults; optional fields have sensible defaults. Constraints are appropriate. |
| Custom validators | Domain-specific validation uses the framework's validator mechanism. |
| Enums for fixed values | Fixed-value fields (modes, statuses, types) use enums, not plain strings or magic constants. |
| Unknown keys rejected (where appropriate) | The root settings model rejects unknown keys to catch typos, unless the project intentionally allows extras. |

**Evidence required:** Read each model. Verify field types and validators. Search for raw dict usage in service code.

### 2. Config Loading & Path Resolution

| Check | Description |
|-------|-------------|
| User config separated from package templates | Config is read from the user's private directory, never from the package's template directory. |
| Path resolution is consistent | All relative paths resolve against the user directory using the project's path-resolution utility. |
| Missing config produces clear error | When config is missing, the error tells the user how to create it. |
| Config reader validates on load | Loading validates through the typed model, not just parsing. |

**Evidence required:** Read the config reader and path utilities. Trace the full path from source file to model in a consumer.

### 3. Init / Template Service Correctness

| Check | Description |
|-------|-------------|
| Templates copied correctly | The init/scaffold step copies from package templates to the user directory. |
| Force/overwrite flag works | With the flag, existing files are overwritten; without it, existing files are preserved. |
| No cross-package imports | The init service does not import from unrelated packages. |
| Return value is useful | The function returns the path to the created config directory. |

**Evidence required:** Read the init/scaffold service. Verify source and destination paths. Check for any hardcoded paths.

### 4. Config Template Quality

| Check | Description |
|-------|-------------|
| Example config matches model | The template matches the settings model structure exactly. |
| All fields documented | Every field in the template has a comment explaining its purpose. |
| No real secrets in templates | Template files contain only placeholder values, no real keys or tokens. |

**Evidence required:** Compare the template against the settings models. Check for mismatched field names or missing sections.

### 5. Config-to-Consumer Flow

| Check | Description |
|-------|-------------|
| Config reaches every consumer | Trace each config section from source → model → consumer. Every section is consumed somewhere. |
| No unused config fields | Every field in the model is actually used by some consumer. |
| No missing config fields | Every consumer parameter that should come from config does come from config (not hardcoded). |

**Evidence required:** For each model field, find at least one usage in consumer code. For each consumer parameter, verify it comes from config.

---

## Report Output

Write findings to: `/.ai/audit/02-config/findings.md` using template `/.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `CFG-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — model instantiation errors, config loading failures, path resolution bugs, test failures.
  2. **Not just:** "violates invariant X" — show the exact model/field/code that violates it and the exact consequence.
