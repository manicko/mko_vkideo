---
name: 04-security
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 04 Audit — Security & Secret Management

## Purpose

This phase audits the system's **security surface**: how secrets and credentials are
stored, loaded, and used; how sensitive data is (or isn't) logged; file permissions and
version-control hygiene; and how external input is validated against path traversal and
injection. The goal is to find credential leaks, unsafe storage, and input-handling
vulnerabilities.

This file is written as a **reusable handbook** for the security phase of any audit. It
deliberately avoids naming specific files, function names, or paths, and avoids
naming specific third-party services — instead it describes *what to discover and
verify*. Apply it to whatever credentials, secrets, and external inputs the current
system actually has.

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the security surface:

1. **Secret Discovery** — Identify all secrets and sensitive values: API keys, tokens, passwords, private keys, session identifiers, account identifiers. Map where each is stored and how it flows through the code.
2. **Credential File Discovery** — Locate credential/token/session files. Check where they are stored, how they are created, who has access.
3. **Logging Discovery** — Search all log calls. Identify any that might log sensitive data (tokens, keys, credentials, secret file paths).
4. **Config Security Discovery** — Check how secrets are loaded: from files, environment variables, or hardcoded. Verify config file permissions and version-control ignore coverage.
5. **Input Validation Discovery** — Identify all external inputs: config values, fetched data, file paths from external sources. Check for path traversal, injection, or other input attacks.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Credential Leak Search

Search the entire codebase for hardcoded secrets: API keys, tokens, passwords, private keys.

- For each match, determine if it is: a hardcoded value (CRITICAL), an environment variable reference (OK), a placeholder/default (OK if clearly marked), or a test fixture (verify it's not a real value).
- Check `.env*` files: if committed to the repo with real values, that is CRITICAL.
- Check config templates for real credentials.

### Step R2 — Logger Audit

Search all log calls for potential secret leakage:

- Any log call that includes a variable containing a key, token, password, or credential is CRITICAL.
- Any log call that dumps an entire config model (which may contain secrets) is a finding.

### Step R3 — File Permission / Ignore Check

Check the version-control ignore status and storage location of sensitive files:

- Credential/token/session files — are they ignored by the version-control system?
- Config/secrets directory — does it have appropriate permissions (user-only access)?

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

Secret management (external API credentials, OAuth/token files, session identifiers), credential file handling, logging security, config security, input validation, and path traversal prevention.

---

## Audit Dimensions

> For each dimension, adapt the concrete checks to the credentials and inputs the system
> actually has. A dimension is omitted from the report if no problem is found in it.

### 1. Hardcoded Secrets

| Check | Description |
|-------|-------------|
| No hardcoded API keys/tokens | Keys, tokens, and passwords come from config or a secret store, never from source code. |
| No hardcoded credential paths | Paths to credential/token files use the project's path-resolution utility, not hardcoded strings. |
| No hardcoded account/session IDs | Identifiers come from config. |
| Test fixtures use fake values | Test mocks use obviously fake values, not real credentials. |

**Evidence required:** Grep results for hardcoded values. Read config loading code. Read test fixtures.

### 2. Credential File Security

| Check | Description |
|-------|-------------|
| Credentials in user directory | Credential/token/session files are stored in the user's private directory, not in the package directory. |
| Credentials ignored by VCS | All credential and session files are listed in the version-control ignore file. |
| No credentials in config templates | Templates contain only placeholder values. |
| Token contents not logged | The path to a token file may be logged, but its contents are never logged. |

**Evidence required:** Read the version-control ignore file. Read config templates. Check file paths in code.

### 3. Logging Security

| Check | Description |
|-------|-------------|
| Secrets never logged | Keys, tokens, passwords, and session identifiers are never passed to any log call. |
| Config models not dumped | Entire settings models are not logged (they may contain secrets). |
| Error messages don't leak secrets | Exception messages and error responses don't include credential values. |
| Paths to secrets are OK | Logging the *path* to a credentials file is acceptable; logging the *contents* is not. |

**Evidence required:** Read all log calls. Search for any log call near credential-handling code.

### 4. Config Security

| Check | Description |
|-------|-------------|
| Secrets loaded from private files, not env (as appropriate) | Credentials are loaded from files in the user's private config directory, not from environment variables that may be leaked in process listings or logs — unless the project intentionally uses env. |
| Config validation rejects empty secrets | Validators reject empty or obviously invalid credential values. |
| Production config is separate | User config is separate from package templates. |

**Evidence required:** Read config models and validators. Verify empty/invalid values are rejected.

### 5. Input Validation & Path Security

| Check | Description |
|-------|-------------|
| Path traversal prevention | File paths from external sources are validated before use. No user-supplied path can escape the intended directory. |
| Path validation | Paths from config/external input are checked for existence and validity before processing. |
| Config value validation | All config values are validated by the settings model before use (no raw strings passed to file operations). |
| Identifier format validation | External identifiers are validated for basic format (non-empty, no path separators). |

**Evidence required:** Read external path handling code. Read config validators. Check for path operations on user-supplied paths.

### 6. Session / Token Security

| Check | Description |
|-------|-------------|
| Session file in user directory | Session/token files are stored in the user directory, not in the package directory or a global temp directory. |
| Session file ignored by VCS | Session files are in the version-control ignore file. |
| Session not shared | Session files are per-user, not shared between different users or environments. |

**Evidence required:** Read the client/session creation code. Check the session file path. Read the version-control ignore file.

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
  1. **Runtime evidence** — grep results, file:line of problematic code, log calls that leak secrets, missing ignore entries.
  2. **Not just:** "violates invariant X" — show the exact code, the exact secret at risk, and the exact exposure vector.
