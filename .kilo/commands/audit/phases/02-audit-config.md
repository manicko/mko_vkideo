---
name: 02-config
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 02 Audit — Configuration & Pydantic Models

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the configuration architecture:

1. **Config Model Discovery** — Locate all Pydantic model classes. Map the model hierarchy (root model → sub-models). Identify all fields, their types, defaults, and validators.
2. **Config Loading Discovery** — Find where YAML is loaded, where Pydantic validation happens, where config files are read from (package templates vs user directory).
3. **Path Resolution Discovery** — Map how `APP_PATHS`, `PathResolver`, and `platformdirs` work together. Identify where user config lives vs package templates.
4. **Config Flow Discovery** — Trace how a config value travels from YAML → Pydantic model → service function. Identify every consumer of config values.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Import and Instantiate Models

Attempt to import all Pydantic models. Instantiate the root model with valid and invalid data.

- Verify validators fire correctly on invalid data.
- Verify defaults are applied correctly.
- Capture any validation errors — they are evidence.

### Step R2 — Config Loading Verification

If a sample/test config file exists, attempt to load it through the config reader.

- Verify the loaded model matches the file contents.
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

Pydantic models, YAML config loading, path resolution, config validation, init service (template copying), config file templates.

---

## Audit Dimensions

### 1. Pydantic Model Correctness

| Check | Description |
|-------|-------------|
| All config sections modeled | Every configuration section (Google Sheets, Telethon, posts, chats) has a corresponding Pydantic model. |
| No raw dicts in business logic | Services receive Pydantic models, not raw dicts from `yaml.safe_load()`. |
| Field validation | Required fields have no defaults; optional fields have sensible defaults. Constraints (`ge`, `le`, `min_length`) are appropriate. |
| Custom validators | Domain-specific validation (e.g., spreadsheet ID format) uses `@field_validator`. |
| `StrEnum` for fixed values | Fixed-value fields (statuses, types, modes) use `StrEnum`, not plain strings or magic constants. |
| `extra="forbid"` on root model | The root settings model rejects unknown keys to catch typos in config. |

**Evidence required:** Read each model class. Verify field types and validators. Search for raw dict usage in service code.

### 2. Config Loading & Path Resolution

| Check | Description |
|-------|-------------|
| User config separated from package templates | Config is read from `USER_DIR` (via platformdirs), never from the package's `settings/` directory. |
| Path resolution is consistent | All relative paths in config resolve against `USER_DIR` using `PathResolver`. |
| Missing config produces clear error | When config file is missing, the error message tells the user to run `init`. |
| Config reader validates on load | `TelepostConfigReader.load()` validates through Pydantic, not just YAML parsing. |

**Evidence required:** Read `config_reader.py` and `paths.py`. Trace the full path from YAML file to Pydantic model in a service.

### 3. Init Service Correctness

| Check | Description |
|-------|-------------|
| Templates copied correctly | `init_project()` copies from package `settings/` to `USER_DIR/settings/`. |
| `--force` flag works | With `--force`, existing files are overwritten. Without it, existing files are preserved. |
| No cross-package imports | Init service does not import from unrelated packages. |
| Return value is useful | The function returns the path to the created config directory. |

**Evidence required:** Read `init_service.py`. Verify the source and destination paths. Check for any hardcoded paths.

### 4. Config Template Quality

| Check | Description |
|-------|-------------|
| Example config matches model | The `config_example.yaml` template matches the Pydantic model structure exactly. |
| All fields documented | Every field in the example config has a comment explaining its purpose. |
| No real credentials in templates | Template files contain only placeholder values, no real API keys or tokens. |

**Evidence required:** Compare `config_example.yaml` against the Pydantic models. Check for mismatched field names or missing sections.

### 5. Config-to-Service Flow

| Check | Description |
|-------|-------------|
| Config reaches every consumer | Trace each config section (google_sheets, telethon, posts, chats) from YAML → model → service function. Every section is consumed somewhere. |
| No unused config fields | Every field in the Pydantic model is actually used by some service. |
| No missing config fields | Every service parameter that should come from config does come from config (not hardcoded). |

**Evidence required:** For each model field, find at least one usage in service code. For each service parameter, verify it comes from config.

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
