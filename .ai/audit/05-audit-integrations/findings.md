---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 05 Audit Findings — External Integrations

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** no

---

## Findings

### INT-001: Audit scope targets Google Sheets & Telegram integrations that do not exist in the repository

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.kilo/commands/audit/phases/05-audit-integrations.md`, `src/vkdownloader/` (absent subsystems) |
| **Classification** | advisory |

**Description:**
The entire Phase 05 audit scope — Google Sheets integration (`GSheetsReader`, `GoogleSheetsConfig`, OAuth2 token-refresh flow) and Telegram integration (`TelegramPoster`, `TelegramClient`, `TelegramService`, `PostProcessor.get_posts()`, `FloodWaitError` handling, bot/user auth switching) — describes subsystems that are **not present** in this repository. The VK Video Downloader (`mko_vkideo`) is a self-contained CLI for extracting and downloading VK videos; it has no external publishing/posting integrations.

Because the in-scope modules, config models, dependencies, and tests are all absent, none of the Discovery Stage items or Audit Dimensions can be evaluated against real code. An executor taking the phase literally would either (a) report false positives against non-existent files, or (b) "implement" features that were never part of the project, introducing dead/speculative code.

**Evidence:**

1. Integration modules are absent (runtime import probe):
   ```
   uv run python -c "import importlib.util as u; ..."
   telegram_service present: False
   gsheets present: False
   ```

2. No references to the in-scope symbols anywhere in `src/`:
   ```
   grep pattern: gsheets|GSheets|google|oauth|telethon|telegram|Telethon|TelegramPoster|GSheetsReader
   in src/vkdownloader/ -> "No files found"
   ```

3. `pyproject.toml` declares only `aiohttp>=3.9.0` among networking deps — no `google-api-python-client`, `google-auth`, `telethon`, or `oauth2client`:
   ```
   "aiohttp>=3.9.0",
   ```
   (no google/gsheet/telethon/telegram/oauth entries)

4. `src/vkdownloader/config.py` (131 lines): `Settings` model contains only browser-automation, download, and logging fields. There is no `GoogleSheetsConfig` and no `TelethonConfig`.

5. `src/vkdownloader/cli.py` (370 lines): only `download` and `batch` Typer commands exist; no integration/publishing commands.

6. `tests/` contains 14 test files (test_cli, test_config, test_extractor, test_http_client, test_security, etc.); **none** target Google Sheets or Telegram. Full suite result:
   ```
   uv run pytest -q  -> 201 passed, 4 warnings in 4.95s
   ```
   The warnings are unrelated `RuntimeWarning: coroutine 'Event.wait' was never awaited` mock artifacts, not integration failures.

7. Runtime Verification steps R1–R3 could not be executed against the in-scope modules because the files do not exist (`ruff check <path>` / `mypy <path>` targets are invalid). R1/R3 were instead run against the whole package: core imports succeed (`IMPORTS OK`) and the existing suite passes.

**Recommendation:**
Clarify the intended scope of this audit phase before execution. Two valid resolutions:
- **If integrations were never intended:** remove or re-scope Phase 05 to the subsystems that actually exist (e.g., the HTTP client, browser extraction, and network-monitor integrations are the real "external" touchpoints). Document that `mko_vkideo` has no Google Sheets/Telegram components.
- **If integrations are planned but unimplemented:** mark Phase 05 as blocked/pending and track it under a feature roadmap rather than an audit, so it is not mistaken for a correctness review of existing code.
Either way, the phase file must not be executed against non-existent code. (advisory — recommended, not mandatory)

---

### INT-002: Documentation references `telegram_service.py` / `PostProcessor` / `TelegramService` as if they are real project files

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/99-reference/morfx-tools.md` |
| **Classification** | advisory |

**Description:**
`docs/99-reference/morfx-tools.md` — a reference guide for the external `morfx` AST-transformation tool — uses `telegram_service.py` as a recurring example file path containing `PostProcessor` (with `get_posts`), `TelegramService` (with `_try_send_message`), and `TelegramPoster` classes. These read as concrete project files but **no such file or classes exist** in the repository (confirmed via filesystem search and import probe, see INT-001 evidence).

This is the most likely source of the incorrect scope in Phase 05: the audit phase mirrors the class/method names from this doc (`PostProcessor.get_posts()`, `TelegramService`, `TelegramPoster`). A maintainer or agent reading the doc could infer that `telegram_service.py` and its classes are part of `mko_vkideo`, when they are merely illustrative DSL examples.

**Evidence:**

1. `docs/99-reference/morfx-tools.md` example references (all point to a non-existent file):
   - Line 273: `class:* >> method:get_posts` → "The match is the **class** `PostProcessor`."
   - Line 276: "Finds `PostProcessor` class (only class with `get_posts` method)."
   - Lines 359–437: repeated `"path": "telegram_service.py"` with DSL targeting `TelegramService >> method:_try_send_message`.
   - Lines 573–575: "insert before `class:PostProcessor`" / "Comment and helper class inserted before PostProcessor".

2. Filesystem search for `**/telegram_service.py` in the repo (excluding `.venv`) returns no project file; `importlib.util.find_spec('vkdownloader.telegram_service')` returns `None`.

**Recommendation:**
In `docs/99-reference/morfx-tools.md`, add a one-line note that all `path`/`telegram_service.py`/`PostProcessor`/`TelegramService` references are synthetic examples for the morfx DSL and are **not** part of this repository's codebase. This prevents future audit phases or agents from treating them as real modules. (advisory — recommended, not mandatory)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 1 |

## Mandatory Fixes

None. All findings are advisory (documentation/scope accuracy).

## Advisory Recommendations

- **INT-001** — Re-scope or remove Phase 05; the Google Sheets and Telegram integrations it audits do not exist in `mko_vkideo`.
- **INT-002** — Annotate `docs/99-reference/morfx-tools.md` example paths as illustrative, not real project files.

## Doc Updates Needed

- **INT-001** (DOC-UPDATE) — Phase file `.kilo/commands/audit/phases/05-audit-integrations.md` must reflect the actual repository scope (no Google Sheets/Telegram integrations).
- **INT-002** (DOC-UPDATE) — `docs/99-reference/morfx-tools.md` should state its example paths are synthetic.
