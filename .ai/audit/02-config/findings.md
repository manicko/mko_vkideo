---
name: audit-findings
description: Phase 02 Audit Findings — Configuration & Pydantic Models
agent: auditor
alwaysApply: false
---

# Phase 02 Audit Findings — Configuration & Pydantic Models

**Executor:** auditor
**Template:** `.kilo/commands/audit/phases/02-audit-config.md`
**Status:** complete
**Validated:** no

---

## Findings

### CFG-001: Audit phase scope does not match delivered configuration architecture

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/phases/02-audit-config.md`, `src/vkdownloader/config.py`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** The phase task (`02-audit-config.md`) describes a configuration subsystem that does not exist in this repository. The task instructs the auditor to audit `config_reader.py`, `paths.py` (`PathResolver`), `init_service.py` (`init_project`), `config_example.yaml`, `APP_PATHS`/`USER_DIR` (via `platformdirs`), and config sections `google_sheets`, `telethon`, `posts`, `chats` consumed through a `TelepostConfigReader.load()`. None of these files, modules, or config sections exist anywhere in the codebase. The delivered project (`vkdownloader`) is a VK video downloader whose entire configuration surface is a single `pydantic_settings.BaseSettings` subclass (`Settings` in `src/vkdownloader/config.py`) driven by environment variables (`VKDOWNLOADER_*`) and a `.env` file — not YAML, not `platformdirs`, and with no Google Sheets / Telethon / posts / chats integrations.

This strongly indicates the phase file was authored for a different project (a "telepost" tool) or for a planned architecture that was never built. Because none of the audit dimensions (1–5) can be meaningfully evaluated against the named components, the phase produces a structural false-positive: a reviewer following the task literally would conclude non-existent components are "missing" rather than recognizing the task is out of sync with reality.

**Evidence:**
- Grep across `src/vkdownloader/**/*.py` for `config_reader`, `PathResolver`, `TelepostConfigReader`, `init_project`, `config_example`, `platformdirs`, `APP_PATHS`, `USER_DIR` returned **no files found**.
- Actual config module is `src/vkdownloader/config.py` — a single class `Settings(BaseSettings)` with 19 fields, `model_config = {"env_file": ".env", "extra": "forbid", "env_prefix": "VKDOWNLOADER_"}`. No YAML loading, no `init` command, no template copying.
- `src/vkdownloader/cli.py` exposes only `download` and `batch` Typer commands; there is no `init` subcommand (referenced by the task as `init_project()`).
- `docs/11-guides/configuration.md` documents only environment-variable-based settings and `.env` usage — consistent with the actual code, contradictory to the YAML/telepost task scope.
- Actual config consumers (verified via grep): `infrastructure/browser.py`, `services/downloader.py`, `services/extractor.py`, `services/segment_downloader.py` all instantiate `Settings()`; none read YAML or user-dir templates.

**Recommendation:** Treat this as a documentation/process deviation, not a code defect. Update `.kilo/commands/audit/phases/02-audit-config.md` to describe the *actual* configuration model (single `pydantic_settings.BaseSettings` + `.env`, no YAML templates, no `init`/template-copy, no telepost sections). Then re-scope the audit dimensions to the real surface: (1) `Settings` field/validator correctness, (2) env-var + `.env` loading behavior, (3) `setup_logging` config coupling, (4) example `.env` template quality in `docs/11-guides/configuration.md`, (5) config-to-service flow. Alternatively, if a telepost-style YAML config system is genuinely planned, file it as a roadmap item rather than an audit expectation.

---

### CFG-002: `ruff format` non-compliant across config and related source files

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/quality.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** The project enforces `ruff format` as a verification gate (base context lists `uv run ruff format --check <path>` as a required command, and the project rules emphasize continuous compliance). Running `ruff format --check` reports that 7 of the source files would be reformatted, including the configuration module `config.py`. This means the repo does not currently pass the documented formatting check, so any CI gating on `ruff format --check` would fail. While this is a formatting-only issue with no runtime impact, it is a correctness/dev-discipline deviation from the project's stated quality gate and will block CI.

**Evidence:**
- Command: `uv run ruff format --check src/vkdownloader/`
- Output:
  ```
  Would reformat: src\vkdownloader\cli.py
  Would reformat: src\vkdownloader\config.py
  Would reformat: src\vkdownloader\services\downloader.py
  Would reformat: src\vkdownloader\services\downloader_throttle.py
  Would reformat: src\vkdownloader\services\extractor.py
  Would reformat: src\vkdownloader\services\quality.py
  Would reformat: src\vkdownloader\services\segment_downloader.py
  7 files would be reformatted, 16 files already formatted
  ```
- Contrast: `uv run ruff check src/vkdownloader/config.py` → `All checks passed!`; `uv run mypy src/vkdownloader/config.py` → `Success: no issues found in 1 source file`; `uv run pytest tests/test_config.py` → `12 passed`. Only the format gate fails.

**Recommendation:** Run `uv run ruff format src/vkdownloader/` to apply formatting, then commit. Add the format check to CI so the gate stays green. Given `config.py` is the audited module and is among the non-compliant files, this is the most directly relevant fix for this phase. (Note: do not hand-edit formatting; let `ruff format` normalize, since the discrepancies are style-level, not semantic.)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 0 |
| LOW | 1 |

## Mandatory Fixes

- **CFG-002** — `ruff format --check` fails on 7 source files including the config module; will block CI. Apply `ruff format` and gate it in CI.

## Advisory Recommendations

- **CFG-001** — Realign the `02-audit-config.md` phase task with the actual configuration architecture (single `pydantic_settings.BaseSettings` + `.env`), or move the telepost/YAML design to a roadmap item, so future audits evaluate the real surface instead of non-existent components.

## Doc Updates Needed

- **CFG-001** — `.kilo/commands/audit/phases/02-audit-config.md` must be rewritten to match the delivered VK downloader config system (env-var `Settings`, no YAML templates, no `init_project`, no Google Sheets/Telethon/posts/chats sections).
- **CFG-002** — Optional: confirm in contributing/CI docs that `ruff format --check` is a required gate and that source is expected to be pre-formatted.

---

## Notes on Audit Dimensions (Phase 02)

The five audit dimensions in the task could only be partially evaluated because the components they name do not exist. Findings against the *actual* configuration code:

- **Dim 1 (Pydantic Model Correctness):** The real `Settings` model is correct. `extra="forbid"` verified at runtime (`Settings(unknown_field=1)` → `ValidationError`); numeric constraints verified (`max_retries=999` → `ValidationError`); `StrEnum` used for `cookie_source` (`CookieSource`) and `log_level` (`LogLevel`); `log_level` has a `@field_validator(mode="before")` normalizing case. No raw dict config is consumed — services receive `Settings` instances. **No finding.**
- **Dim 2 (Config Loading & Path Resolution):** Not applicable as described — there is no YAML loading, `PathResolver`, `platformdirs`, or `USER_DIR`. Config loads from env vars + `.env` via `pydantic_settings`. Path resolution for outputs is handled in `cli.py` via `validate_output_path`, not config templates. **No applicable finding** beyond scope mismatch (CFG-001).
- **Dim 3 (Init Service Correctness):** `init_project()` / `init_service.py` do not exist; CLI has no `init` command. **No applicable finding** (scope mismatch CFG-001).
- **Dim 4 (Config Template Quality):** No `config_example.yaml`; the closest artifact is `docs/11-guides/configuration.md` (`.env` example), which matches the model field-for-field. **No finding.**
- **Dim 5 (Config-to-Service Flow):** All 19 `Settings` fields are reachable; `Settings()` is instantiated in `browser.py`, `downloader.py` (×3), `extractor.py`, `segment_downloader.py`, and `cli.py`. The only fields not obviously consumed in the audited path are `timezone` and `locale` (browser stealth) — these are used inside `infrastructure/browser.py`. **No unused-field finding** within the actual code.
