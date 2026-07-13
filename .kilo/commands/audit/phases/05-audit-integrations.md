---
name: 04-integrations
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 05 Audit — External Integrations

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the integration architecture:

1. **Google Sheets Integration Discovery** — Locate the GSheetsReader class. Map the OAuth2 flow: credentials → token → service → API calls. Identify how spreadsheet data is fetched and returned.
2. **Telegram Integration Discovery** — Locate the Telethon client setup. Map the auth flow: api_id/api_hash → session → client → send operations. Identify how messages and files are sent.
3. **Error Handling Discovery** — For each integration: what happens when the API is unreachable? When credentials are invalid? When rate limits are hit?
4. **Config Injection Discovery** — Trace how API credentials and settings flow from Pydantic models into the integration clients.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Import Verification

Import all integration modules. Verify no import errors.

### Step R2 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.

### Step R3 — Run Test Suite

Run the project's test suite, focusing on integration-related tests.

- Record pass/fail counts and failure output.

---

## Audit Scope

Google Sheets API integration (GSheetsReader), Telegram API integration (TelegramPoster, TelegramClient), OAuth2 flow, API error handling, credential management.

---

## Audit Dimensions

### 1. Google Sheets Integration

| Check | Description |
|-------|-------------|
| OAuth2 flow is complete | Token loading → refresh → re-authentication works. All three paths are implemented. |
| Credential paths are resolved correctly | `credentials_file` and `token_file` paths are resolved relative to `USER_DIR`, not the package directory. |
| Service degrades gracefully | If credentials are missing, the service logs a clear error and returns empty data (does not crash). |
| API errors are caught | `HttpError` and other API exceptions are caught and logged, not propagated as unhandled exceptions. |
| Data format is correct | Returned data is a list of lists (rows → cells), matching what `PostProcessor.get_posts()` expects. |
| No global state | `GSheetsReader` does not use a global `CONFIG` singleton; it receives config via constructor. |

**Evidence required:** Read `gsheets_reader.py` end-to-end. Trace the OAuth2 flow. Verify error handling at each step.

### 2. Telegram Integration

| Check | Description |
|-------|-------------|
| Client creation is correct | `TelegramClient` is created with the correct session name, api_id, and api_hash from config. |
| Auth supports both user and bot | The `is_user` flag correctly switches between phone auth and bot token auth. |
| Messages sent with correct parameters | `send_message` and `send_file` are called with the correct chat_id, text, photos, and topic_id. |
| Flood control is handled | `FloodWaitError` triggers a wait-and-retry with the specified duration plus jitter. |
| Other transient errors are retried | `WorkerBusyTooLongRetryError`, `RPCError`, `OSError` trigger retries with exponential backoff. |
| Permanent errors are not retried indefinitely | After max retries, the error is logged and the post is skipped (not retried forever). |
| Client lifecycle is managed | The Telegram client is properly started and stopped (`async with client.start()`). |

**Evidence required:** Read `telegram_service.py` — the `TelegramPoster`, `_try_send_message`, and `run` methods. Verify retry logic and client lifecycle.

### 3. Credential & Secret Handling

| Check | Description |
|-------|-------------|
| No hardcoded credentials | API IDs, hashes, tokens, and spreadsheet IDs come from config, not hardcoded values. |
| Credentials not logged | API keys, tokens, and secrets are never passed to `logger.info()` or `logger.debug()`. |
| Session files are user-local | Telethon session files are stored in the user directory, not in the package directory. |

**Evidence required:** Search for any hardcoded secrets. Search for `logger` calls near credential-handling code.

### 4. Config-to-Integration Flow

| Check | Description |
|-------|-------------|
| Google Sheets config reaches GSheetsReader | `GoogleSheetsConfig` model fields (spreadsheet_id, credentials_file, token_file, scopes) are correctly passed to `GSheetsReader`. |
| Telethon config reaches TelegramClient | `TelethonConfig` model fields (api_id, api_hash, session) are correctly passed to `TelegramClient`. |
| No config fields are ignored | Every field in the config models is used by the corresponding integration. |
| No hardcoded fallbacks | Integrations do not fall back to hardcoded values when config is missing. |

**Evidence required:** Trace each config field from Pydantic model → constructor → API call. Verify no field is silently ignored.

---

## Report Output

Write findings to: `/.ai/audit/05-integrations/findings.md` using template `/.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `INT-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — import errors, test failures, code analysis showing the bug.
  2. **Not just:** "violates invariant X" — show the exact code that violates it and the exact consequence.
