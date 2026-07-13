---
name: 05-data-flow
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 06 Audit — End-to-End Data Flow

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, trace the complete data flow:

1. **Full Pipeline Mapping** — Trace the entire path: `CLI command` → `config loading` → `Google Sheets API call` → `raw data` → `post extraction` → `image processing` → `queue` → `Telegram API call` → `cleanup`.
2. **Config Propagation Trace** — For each config section, trace exactly how it flows from YAML → Pydantic model → service constructor → function parameter. Identify every hop.
3. **Message Lifecycle** — Pick a single post and trace it from the Google Sheets cell to the Telegram message. Document every transformation.
4. **Error Path Mapping** — For each stage in the pipeline, identify what happens on failure. Does the error propagate correctly? Is cleanup guaranteed?

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Use the commands provided in the project's commands file. Skip only if a step is impossible — document why.**

### Step R1 — Import Full Pipeline

Import the CLI entry point, config reader, and all service modules. Verify the full chain is importable.

### Step R2 — Linter and Type Checker

Run the project's configured linter and type checker commands.

- Record exit codes and output.

### Step R3 — Run Test Suite

Run the complete test suite.

- Record pass/fail counts and failure output.

---

## Audit Scope

End-to-end data flow from CLI invocation through config loading, data fetching, processing, posting, and cleanup. Cross-layer interaction verification.

---

## Audit Dimensions

### 1. Config-to-Service Propagation

**Trace each config section from YAML to its final consumer. Document every hop.**

| Config Section | Expected Consumer | Verification |
|----------------|-------------------|--------------|
| `google_sheets.*` | `GSheetsReader.__init__()` → API calls | Verify spreadsheet_id, credentials_file, token_file, scopes all reach the reader. |
| `telethon.*` | `TelegramPoster.__init__()` → `TelegramClient()` | Verify api_id, api_hash, session all reach the client. |
| `posts.*` | `PostProcessor` / `TelegramService` | Verify max_photos and cache_dir are used. |
| `chats.*` | `TelegramService._push_posts_to_queue()` | Verify chat_id, topic_id, range_names, delay_minutes all reach the posting loop. |

**For each field, document:** YAML key → Pydantic model field → constructor parameter → function call. If any hop is missing or broken, that is a finding.

### 2. Message Lifecycle Trace

**Trace a single post from Google Sheets to Telegram. Document every transformation.**

| Stage | Input | Output | Verification |
|-------|-------|--------|--------------|
| Google Sheets API | spreadsheet_id, range_name | `list[list]` (raw rows) | Verify data is returned correctly. |
| PostProcessor.get_posts() | raw rows, filter_col, filter_value, txt_col, photo_col, max_photos | `list[list]` ([text, [photo_paths]]) | Verify filter logic, photo extraction, max_photos limit. |
| ImageCache.resize_image() | original photo path | cached/resized photo path | Verify caching, resize, error handling. |
| Task creation | chat_id, topic_id, text, photos, chat_name, count, max_count | `Task` object | Verify all fields are populated. |
| Queue → Sender | `Task` from queue | Telegram API call | Verify chat_id, text, photos, topic_id are passed correctly. |
| Cleanup | used_cache_files set | unused files removed | Verify only used files are kept. |

**If any transformation is incorrect, missing, or loses data, that is a finding.**

### 3. Multi-Chat Flow Correctness

| Check | Description |
|-------|-------------|
| Each chat gets its own posts | Posts from `range_names` of chat A are not sent to chat B. |
| Chat-specific delays | `delay_minutes` is applied per-chat, not globally. |
| Chat-specific topics | `topic_id` is correctly scoped to its chat. |
| All chats are processed | Every chat in the config list is processed, not just the first one. |
| Empty chats are handled | A chat with no matching posts is skipped gracefully (no crash, no empty messages). |

**Evidence required:** Read the multi-chat loop in `TelegramService.run()`. Verify posts are correctly scoped to each chat.

### 4. Error Propagation & Cleanup

| Check | Description |
|-------|-------------|
| Config error stops before posting | If config is invalid, the CLI reports the error and exits without attempting to post. |
| Google Sheets failure is handled | If the API returns no data or an error, the service logs the error and continues (or exits gracefully). |
| Telegram failure doesn't crash the app | If sending to one chat fails, other chats are still processed. |
| Image processing failure is non-fatal | If one image fails to resize, the post is still sent (with original image or without it). |
| Cleanup runs on success | After all posts are sent, unused cache files are removed. |
| Cleanup runs on failure | If posting fails mid-way, cache cleanup still runs (via `try/finally` or similar). |
| KeyboardInterrupt is handled | Pressing Ctrl+C during posting stops gracefully without stack traces. |

**Evidence required:** Read error handling at each stage. Verify `try/finally` or context managers are used where needed. Check that `cleanup_unused()` is called in all exit paths.

### 5. Data Integrity

| Check | Description |
|-------|-------------|
| No data loss between stages | Every row that passes the filter becomes a post. No rows are silently dropped. |
| Photo paths are valid | Photo paths from Google Sheets are resolved correctly (relative to what base?). |
| Text content is preserved | Post text is not truncated, modified, or escaped incorrectly. |
| Post count is accurate | `count` and `max_count` in Task correctly reflect the actual post number and total. |

**Evidence required:** Trace data through each transformation. Check for off-by-one errors, truncation, or incorrect path resolution.

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
  1. **Runtime evidence** — traced data flow showing where the break occurs, test failures, missing error handlers.
  2. **Not just:** "violates invariant X" — show the exact stage, the exact data, and the exact consequence (lost post, wrong chat, orphaned file).
