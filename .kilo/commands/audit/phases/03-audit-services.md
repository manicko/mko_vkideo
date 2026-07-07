---
name: 03-services
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 03 Audit — Service Layer & Business Logic

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Discovery Stage

Before performing audit checks, discover the service layer architecture:

1. **Service Discovery** — Locate all service classes. Map their responsibilities: what does each service class do? What are its dependencies?
2. **Class Responsibility Mapping** — For each class: is it a service, a processor, a reader, a cache, a model? Does it have a single responsibility?
3. **Dependency Graph** — Map how services depend on each other. Identify the composition root (where services are instantiated and wired together).
4. **Data Transformation Chain** — Trace how raw data (from Google Sheets) is transformed into posts, then into Telegram messages. Identify each transformation step.

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

Service classes (TelegramService, PostProcessor, ImageCache, TelegramPoster, GSheetsReader), Task model, business logic, data transformations.

---

## Audit Dimensions

### 1. Single Responsibility

| Check | Description |
|-------|-------------|
| Each class has one reason to change | `ImageCache` handles only image caching. `PostProcessor` handles only post extraction. `TelegramPoster` handles only Telegram API communication. |
| No god classes | No single class handles config loading, data fetching, image processing, AND posting. |
| Separation of concerns | Image processing is separate from post processing, which is separate from Telegram communication. |

**Evidence required:** Read each service class. If a class has methods that belong to different domains, that is a finding.

### 2. Dependency Direction

| Check | Description |
|-------|-------------|
| Services depend on abstractions/models | Services receive Pydantic models, not raw dicts or YAML data. |
| No circular dependencies | Service A does not import Service B while Service B imports Service A. |
| Composition root is clear | The main service (`TelegramService`) composes all sub-services. Sub-services do not compose the main service. |

**Evidence required:** Trace import chains between service classes. Verify the dependency graph is acyclic.

### 3. Image Processing Correctness

| Check | Description |
|-------|-------------|
| Image cache works correctly | Resized images are cached and reused. Cache key is deterministic (same input → same cache path). |
| Resize handles errors gracefully | If an image cannot be opened/resized, the error is caught and the original path is returned (not a crash). |
| Cleanup removes unused files | `cleanup_unused()` removes cached files that were not used in the current run. |
| No orphaned temp files | After posting completes (success or failure), no temporary image files remain. |

**Evidence required:** Read `ImageCache` class. Trace the full lifecycle: resize → cache → use → cleanup. Check for `try/finally` around file operations.

### 4. Post Processing Correctness

| Check | Description |
|-------|-------------|
| Filter logic is correct | Rows are filtered by the configured column and value. Rows where the filter column is out of range are included (not silently dropped). |
| Photo extraction handles both cases | Photo column content is handled whether it is a directory path (multiple photos) or a single file path. |
| Max photos limit is enforced | `max_photos` is applied to limit the number of photos per post. |
| Empty posts handled | Posts with no text and no photos are handled gracefully (not sent as empty messages). |

**Evidence required:** Read `PostProcessor.get_posts()`. Trace the filter logic and photo extraction logic. Check edge cases.

### 5. Telegram Posting Correctness

| Check | Description |
|-------|-------------|
| Retry logic works | `FloodWaitError`, `SlowModeWaitError`, and other transient errors trigger retries with appropriate backoff. |
| Non-retryable errors fail fast | Permanent errors (e.g., chat not found) do not trigger infinite retries. |
| Posts are shuffled | Post order is randomized before sending (if configured). |
| Delay between posts is respected | `delay_minutes` is converted to seconds and applied between posts. |
| Topic/forum support | `topic_id` is passed correctly to `send_message` and `send_file` for forum topics. |

**Evidence required:** Read `TelegramPoster` and the posting loop. Verify retry logic, delay handling, and topic support.

### 6. Task Model Integrity

| Check | Description |
|-------|-------------|
| Task carries all required data | The `Task` model includes chat_id, topic_id, text, photos, chat_name, count, max_count. |
| Task status tracking | Task has a status field to track success/failure. |
| No business logic in Task | Task is a data container (dataclass), not a service. |

**Evidence required:** Read `task.py`. Verify it is a pure data class with no methods that belong in a service.

---

## Report Output

Write findings to: `.ai/audit/03-services/findings.md` using template `.ai/audit/templates/audit-findings.md`.

**Write the file incrementally — append blocks of ≤100 lines each. Never write the entire report in a single call.**

Use prefix `SRV-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — import errors, test failures, dead code proof (file:line), logic bugs.
  2. **Not just:** "violates invariant X" — show the exact code that violates it and the exact consequence.
