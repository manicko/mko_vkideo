---
name: 04-security
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 04 Audit — Security & Secret Management

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the security surface:

1. **Secret Discovery** — Identify all secrets and sensitive values: Telegram api_id/api_hash, bot tokens, Google OAuth2 credentials, spreadsheet IDs. Map where each is stored and how it flows through the code.
2. **Credential File Discovery** — Locate `credentials.json`, `token.json`, Telethon session files. Check where they are stored, how they are created, who has access.
3. **Logging Discovery** — Search all `logger` calls. Identify any that might log sensitive data (tokens, API keys, credentials, file paths to secrets).
4. **Config Security Discovery** — Check how secrets are loaded: from config files, environment variables, or hardcoded. Verify config file permissions and .gitignore coverage.
5. **Input Validation Discovery** — Identify all external inputs: config values, Google Sheets data, file paths from sheets. Check for path traversal, injection, or other input attacks.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Credential Leak Search

Search the entire codebase for hardcoded secrets: API keys, tokens, passwords, private keys.

- For each match, determine if it is: a hardcoded value (CRITICAL), an environment variable reference (OK), a placeholder/default (OK if clearly marked), or a test fixture (verify it's not a real value).
- Check `.env*` files: if committed to the repo with real values, that is CRITICAL.
- Check config templates for real credentials.

### Step R2 — Logger Audit

Search all `logger.info()`, `logger.debug()`, `logger.warning()` calls for potential secret leakage:

- Any logger call that includes a variable containing api_hash, bot_token, api_id, credentials path, or token content is CRITICAL.
- Any logger call that dumps an entire config model (which may contain secrets) is a finding.

### Step R3 — File Permission Check

Check the permissions and .gitignore status of sensitive files:

- `credentials.json`, `token.json`, Telethon session files — are they in `.gitignore`?
- Config directory — does it have appropriate permissions (user-readable only)?

### Step R4 — Import Verification

Import all modules that handle secrets. Verify no import-time side effects leak credentials.

### Step R5 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.

### Step R6 — Run Test Suite

Run the project's test suite.

- Record pass/fail counts and failure output.

---

## Audit Scope

Secret management (Telegram API credentials, Google OAuth2 tokens), credential file handling, logging security, config security, input validation, path traversal prevention.

---

## Audit Dimensions

### 1. Hardcoded Secrets

| Check | Description |
|-------|-------------|
| No hardcoded API keys | `api_id`, `api_hash`, `bot_token` come from config, never from source code. |
| No hardcoded OAuth2 credentials | Google `credentials.json` path comes from config, not hardcoded. |
| No hardcoded spreadsheet IDs | Spreadsheet ID comes from config. |
| No hardcoded file paths to secrets | Paths to `credentials.json`, `token.json` use `PathResolver`, not hardcoded strings. |
| Test fixtures use fake values | Test mocks use obviously fake values (`"test_token"`, `12345`), not real credentials. |

**Evidence required:** Grep results for hardcoded values. Read config loading code. Read test fixtures.

### 2. Credential File Security

| Check | Description |
|-------|-------------|
| Credentials in user directory | `credentials.json`, `token.json`, session files are stored in `USER_DIR` (via platformdirs), not in the package directory. |
| Credentials in `.gitignore` | All credential and session files are listed in `.gitignore`. |
| No credentials in config templates | `config_example.yaml` contains only placeholder values. |
| Token file not logged | The path to `token.json` may be logged, but its contents are never logged. |

**Evidence required:** Read `.gitignore`. Read config templates. Check file paths in code.

### 3. Logging Security

| Check | Description |
|-------|-------------|
| Secrets never logged | `api_hash`, `bot_token`, `api_id`, OAuth2 tokens are never passed to any logger call. |
| Config models not dumped | Entire Pydantic config models are not logged (they contain secrets). |
| Error messages don't leak secrets | Exception messages and error responses don't include credential values. |
| File paths to secrets are OK | Logging the *path* to a credentials file is acceptable; logging the *contents* is not. |

**Evidence required:** Read all logger calls. Search for any logger call near credential-handling code.

### 4. Config Security

| Check | Description |
|-------|-------------|
| Secrets loaded from files, not env | Credentials are loaded from files in the user's private config directory, not from environment variables (which may be logged or leaked in process listings). |
| Config validation rejects empty secrets | Pydantic validators reject empty or obviously invalid credential values. |
| Production config is separate | User config in `~/.config/` is separate from package templates. |

**Evidence required:** Read config models and validators. Verify empty/invalid values are rejected.

### 5. Input Validation & Path Security

| Check | Description |
|-------|-------------|
| Path traversal prevention | File paths from Google Sheets (photo paths) are validated before use. No user-supplied path can escape the intended directory. |
| Photo path validation | Photo paths from config/sheets are checked for existence and validity before processing. |
| Config value validation | All config values are validated by Pydantic before use (no raw strings passed to file operations). |
| Spreadsheet ID format | Spreadsheet ID is validated for basic format (non-empty, no path separators). |

**Evidence required:** Read photo path handling code. Read config validators. Check for `os.path` or `pathlib` operations on user-supplied paths.

### 6. Telethon Session Security

| Check | Description |
|-------|-------------|
| Session file in user directory | Telethon session file is stored in `USER_DIR`, not in the package directory or a global temp directory. |
| Session file in `.gitignore` | Session files (`.session`, `.session-journal`) are in `.gitignore`. |
| Session not shared | Session file is per-user, not shared between different users or environments. |

**Evidence required:** Read Telethon client creation code. Check session file path. Read `.gitignore`.

---

## Report Output

Write findings to: `/.ai/audit/04-security/findings.md` using template `/.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `SEC-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — grep results, file:line of problematic code, logger calls that leak secrets, missing .gitignore entries.
  2. **Not just:** "violates invariant X" — show the exact code, the exact secret at risk, and the exact exposure vector.
