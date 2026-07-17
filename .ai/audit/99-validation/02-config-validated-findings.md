# Phase 02 Audit Findings — Configuration & Settings Models (Validated)

**Executor:** audit-executor  
**Validator:** validator  
**Source:** `.ai/audit/02-config/findings.md`  
**Status:** validated

---

## Findings

### CFG-001: `download_dir` from `.env` with `~/` is not expanded and produces a literal `~` path

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (`Settings.download_dir`, line 57-60), `src/vkdownloader/config.py` (`Settings.log_file`, line 89-92) |
| **Classification** | mandatory |

**Description:** `download_dir` is a `Path` field. Its model default uses `Path.home()` (correct), but when the value is supplied via the `.env` file (or any env override) as `~/Downloads/vkdownloader`, Pydantic stores the raw `Path("~/Downloads/vkdownloader")` **without expanding the tilde**. The same applies to `log_file` when set via env. Consumers call `validated_output.mkdir(parents=True, exist_ok=True)` (cli.py:111, 340), so the tool would silently create/download into a bogus `~\Downloads\...` directory relative to the current working directory rather than the intended home location.

**Evidence:**
- Runtime verification:
  ```python
  os.environ["VKDOWNLOADER_DOWNLOAD_DIR"] = "~/Downloads/vkdownloader"
  s = Settings()
  print(s.download_dir)  # -> ~\Downloads\vkdownloader ; startswith ~ ? True
  os.environ["VKDOWNLOADER_LOG_FILE"] = "~/vkdownloader.log"
  s2 = Settings()
  print(s2.log_file)  # -> ~\vkdownloader.log ; startswith ~ ? True
  ```
- `config.py` line 57-60: `download_dir: Path = Field(default=Path.home() / "Downloads" / "vkdownloader", ...)` - default is correct; env override is not tilde-expanded because Pydantic treats the string as a plain `Path()` argument.
- `config.py` line 89-92: `log_file: Path | None = Field(...)` - same issue.
- `docs/01-tools/installation.md:118` documents `DOWNLOAD_DIR=~/Downloads/vkdownloader` (without prefix).
- `docs/11-guides/configuration.md:95` documents `VKDOWNLOADER_DOWNLOAD_DIR=~/Downloads/vkdownloader` (with prefix but still with tilde).

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Classified as SPEC-DEVIATION because the code violates the documented expectation that `download_dir` and `log_file` accept paths. The default uses `Path.home()` correctly, but env-provided values with `~` are broken.
> - **See also:** CFG-002 (prefix issue compounds this problem)

### CFG-002: Installation guide documents wrong env-var names — none of them load

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/installation.md` (lines 106-128), `src/vkdownloader/config.py` (`model_config`, line 101-106) |
| **Classification** | mandatory |

**Description:** `Settings.model_config` sets `"env_prefix": "VKDOWNLOADER_"` and `"env_file": ".env"`. Therefore the ONLY env vars that load are `VKDOWNLOADER_*`. The `installation.md` guide instructs users to create a `.env` using **unprefixed** names that will be silently ignored.

**Evidence:**
- `config.py` line 101-106:
  ```python
  model_config = {
      "env_file": ".env",
      "env_file_encoding": "utf-8",
      "extra": "forbid",
      "env_prefix": "VKDOWNLOADER_",
  }
  ```
- `installation.md` lines 106-128 show bare vars: `USER_AGENT=...`, `DOWNLOAD_DIR=...`, `DOWNLOAD_METHOD=auto`, etc.
- Runtime verification confirms: setting `VKDOWNLOADER_DOWNLOAD_METHOD` (non-existent field) has no effect; the bare `DOWNLOAD_METHOD=` form cannot be read because Pydantic-settings only looks for prefixed keys.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. All 16 documented environment variables in the installation guide are missing the required `VKDOWNLOADER_` prefix. Additionally, `CONCURRENT_FRAGMENTS` and `DOWNLOAD_METHOD` are not valid config fields at all (see CFG-004).

### CFG-003: `accept_language` config field is defined but never consumed (dead config)

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (`accept_language`, line 27-30), `src/vkdownloader/infrastructure/browser.py`, `docs/11-guides/configuration.md:25`, `docs/01-tools/api-reference.md:847` |
| **Classification** | advisory |

**Description:** `Settings.accept_language` (default `"ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"`) is declared and documented as "Accept-Language header for browser requests", but it is **never read by any consumer**. The browser context in `browser.py` is built from `user_agent`, `locale`, and `timezone_id` (lines 64-69) — there is no `accept_language` / `Accept-Language` header set anywhere. Playwright's `new_context` does not take an `accept_language` argument; the closest concept is `locale`, which is already covered by the separate `locale` field.

**Evidence:**
- `config.py` line 27-30 declares `accept_language`.
- Repo-wide grep for `accept_language` returns exactly **1 match** in `config.py`. Zero usages in `services/`, `infrastructure/`, or `cli.py`.
- `browser.py` lines 64-69 use `locale=self.settings.locale` and `timezone_id=self.settings.timezone`; no accept-language injection.
- Docs in `configuration.md:25` and `api-reference.md:847` document this as a functional setting.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. The field is defined, tested in `tests/test_config.py`, and documented, but never consumed. Per the project's dead code rule, this is reclassified as SPEC-DEVIATION (missing integration, not dead code) because docs explicitly state this field controls Accept-Language header.

### CFG-004: `DOWNLOAD_METHOD` documented/referenced but is not a config field (misleading dead knob)

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (no `download_method` field), `.env` (line 26), `docs/01-tools/installation.md:123` |
| **Classification** | mandatory |

**Description:** Multiple configuration surfaces reference a `download_method` setting that does not exist in the `Settings` model. The actual download method is selected **only** via the Typer CLI option. An operator who sets `VKDOWNLOADER_DOWNLOAD_METHOD` will believe they configured a persistent default, but the value is silently ignored.

**Evidence:**
- Runtime verification: `"download_method" in Settings.model_fields` → `False`.
- `cli.py` lines 288-293, 411-416: `method: DownloadMethod = typer.Option(...)` — method is CLI-only.
- `.env` line 26: `# VKDOWNLOADER_DOWNLOAD_METHOD=auto`.
- `installation.md:123`: `DOWNLOAD_METHOD=auto`.
- `installation.md:120` documents `CONCURRENT_FRAGMENTS=4` which also does not exist as a config field.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. Both `DOWNLOAD_METHOD` and `CONCURRENT_FRAGMENTS` are documented in installation.md but are not valid Settings fields. The latter is not mentioned in the original finding but represents the same category of error.

### CFG-005: No `init`/template/scaffold service exists despite config dimensions assuming one

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/cli.py` (only `download` + `batch` commands) |
| **Classification** | advisory |

**Description:** The phase handbook's Audit Dimensions 3 ("Init / Template Service Correctness") and 4 ("Config Template Quality") assume a config-template/init-scaffold mechanism. This project has **neither**: configuration is purely environment-based via `.env` + `VKDOWNLOADER_` env vars (no YAML/JSON config file, no `init` CLI command, no package templates).

**Evidence:**
- `cli.py` defines `@app.command()` (download, line 278) and `@app.command("batch")` (line 394). No `init`/`config`/`template` command.
- No `*.template`, `*.example`, or config-template files found in `src/` or repo root.
- `Settings` uses `BaseSettings` with `env_file=".env"` — no file-based config schema to template.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. The project uses env-only configuration. The audit dimensions were correctly identified as inapplicable for this project.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | — |
| Reclassified | 1 | CFG-001 (RUNTIME-ERROR → SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CFG-001 | RUNTIME-ERROR | SPEC-DEVIATION | The tilde expansion issue represents implementation not matching documented behavior - a spec deviation rather than pure runtime error. |

### Cross-Phase Conflicts

None detected. All findings are internally consistent and corroborated by runtime testing.

### Rollout Safety Notes

| ID | Risk | Mitigation |
|----|------|------------|
| CFG-001 | HIGH | Adding `field_validator(mode="after")` on Path fields is low-risk; validators run on instantiation and do not affect default behavior. |
| CFG-002 | HIGH | Documentation fix only; no code changes required. |
| CFG-003 | MEDIUM | Either wire up the field (requires browser.py changes) or remove it (requires config.py changes and doc updates). |
| CFG-004 | MEDIUM | Either add the field to Settings or remove from docs/.env; both approaches are safe. |

### Dependency Chain

- CFG-002 (prefix fix) affects CFG-001 and CFG-004 — users need correct prefixes to use any env-based configuration.
- CFG-003 and CFG-004 are independent — can be addressed in any order.

---

## Required Fixes

1. **CFG-001** — Add `field_validator` on `download_dir` and `log_file` to call `Path.expanduser().resolve()`; update docs to either support tilde or require absolute paths.
2. **CFG-002** — Fix `installation.md` `.env` block to use `VKDOWNLOADER_` prefix for all real fields.
3. **CFG-004** — Either add `download_method` and `concurrent_fragments` fields to `Settings`, or remove them from all documentation and `.env`.

## Advisory Recommendations

1. **CFG-003** — Remove `accept_language` field or implement actual Accept-Language header injection in browser context.
2. **CFG-005** — Add note to configuration docs stating this tool is env/CLI-configured only.