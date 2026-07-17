# Phase 02 Audit Findings — Configuration & Settings Models

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/02-audit-config.md
**Status:** complete
**Validated:** no

---

## Findings

### CFG-001: `download_dir` from `.env` with `~/` is not expanded and produces a literal `~` path

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/config.py` (`Settings.download_dir`, line 57-60) |
| **Classification** | mandatory |

**Description:** `download_dir` is a `Path` field. Its model default uses `Path.home()` (correct), but when the value is supplied via the `.env` file (or any env override) as `~/Downloads/vkdownloader`, Pydantic stores the raw `Path("~/Downloads/vkdownloader")` **without expanding the tilde**. The resulting path is a literal `~` path (e.g. `~\Downloads\vk` on Windows / `~/Downloads/vk` on POSIX) that is not resolved against the user home. The same applies to `log_file` when set via env. Consumers call `validated_output.mkdir(parents=True, exist_ok=True)` (cli.py:111, 340), so the tool would silently create/download into a bogus `~\Downloads\...` directory relative to the current working directory rather than the intended home location.

**Evidence:**
- Runtime probe (`uv run python`):
  ```
  os.environ["VKDOWNLOADER_DOWNLOAD_DIR"] = "~/Downloads/vk"
  s = Settings()
  print(s.download_dir)  # -> ~\Downloads\vk ; startswith ~ ? True
  ```
- `config.py` line 57-60: `download_dir: Path = Field(default=Path.home() / "Downloads" / "vkdownloader", ...)`. Default is fine; env override is not tilde-expanded because Pydantic treats the string as a plain `Path()` argument.
- Config docs (`docs/11-guides/configuration.md:95`, `docs/01-tools/installation.md:118`) explicitly instruct users to set `VKDOWNLOADER_DOWNLOAD_DIR=~/Downloads/vkdownloader`, encouraging the broken form.

**Recommendation:** Expand `~` (and resolve relative paths) for `Path` fields that may originate from env/`.env`. Either add a `field_validator(mode="after")` on `download_dir`/`log_file` that does `Path.expanduser().resolve()`, or document that env values must be absolute. Keep the `Path.home()` default as-is. This is a correctness fix — a misleading default in the docs leads to misplaced downloads.

---

### CFG-002: Installation guide documents wrong env-var names — none of them load

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/installation.md` (lines 106-128), `src/vkdownloader/config.py` (`model_config`, line 101-106) |
| **Classification** | mandatory |

**Description:** `Settings.model_config` sets `"env_prefix": "VKDOWNLOADER_"` and `"env_file": ".env"`. Therefore the ONLY env vars that load are `VKDOWNLOADER_*`. However `docs/01-tools/installation.md` instructs users to create a `.env` using **unprefixed** names: `USER_AGENT=`, `ACCEPT_LANGUAGE=`, `TIMEZONE=`, `LOCALE=`, `HEADLESS=`, `MAX_RETRIES=`, `DOWNLOAD_TIMEOUT=`, `SSL_VERIFY=`, `DOWNLOAD_DIR=`, `MAX_CONCURRENT_DOWNLOADS=`, `CONCURRENT_FRAGMENTS=`, `THROTTLED_RATE=`, `HTTP_CHUNK_SIZE=`, `DOWNLOAD_METHOD=`, `LOG_LEVEL=`, `LOG_FILE=`. None of these match the `VKDOWNLOADER_` prefix, so **every setting in the documented `.env` is silently ignored** and the tool runs entirely on hardcoded defaults. The guide's "Configuration" section is effectively non-functional.

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
- `installation.md` lines 106-128 show bare vars with no prefix, e.g. `USER_AGENT=Mozilla/5.0...`, `DOWNLOAD_DIR=~/Downloads/vkdownloader`, `DOWNLOAD_METHOD=auto`.
- Runtime: setting `VKDOWNLOADER_DOWNLOAD_METHOD` (a non-existent field) has no effect (confirmed it is not in `Settings.model_fields`); the bare `DOWNLOAD_METHOD=` form likewise cannot be read because Pydantic-settings only looks for prefixed keys.

**Recommendation:** Rewrite the `.env` block in `installation.md` to use the `VKDOWNLOADER_` prefix for all real fields (`VKDOWNLOADER_USER_AGENT`, `VKDOWNLOADER_DOWNLOAD_DIR`, etc.). Remove variables that do not exist as config fields (see CFG-004). This is a mandatory doc-correctness fix — following the install guide yields a non-configurable install.

---

### CFG-003: `accept_language` config field is defined but never consumed (dead config)

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` (`accept_language`, line 27-30), `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description:** `Settings.accept_language` (default `"ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"`) is declared and documented as "Accept-Language header for browser requests", but it is **never read by any consumer**. The browser context in `browser.py` is built from `user_agent`, `locale`, and `timezone_id` (lines 64-69) — there is no `accept_language` / `Accept-Language` header set anywhere. Playwright's `new_context` does not take an `accept_language` argument; the closest concept is `locale`, which is already covered by the separate `locale` field. The field therefore has no runtime effect, despite being presented as functional in the configuration docs.

**Evidence:**
- `config.py` line 27-30 declares `accept_language`.
- Repo-wide grep for `accept_language` returns exactly **1** match — the field declaration itself in `config.py`. Zero usages in `services/`, `infrastructure/`, or `cli.py`.
- `browser.py` lines 64-69 use `locale=self.settings.locale` and `timezone_id=self.settings.timezone`; no accept-language injection.

**Recommendation:** Either (a) remove `accept_language` if it is genuinely unused (and drop it from docs), or (b) if Accept-Language spoofing is intended, actually inject it (e.g. via a browser context HTTP header or `add_init_script`). Given the project rule on dead code ("investigate purpose, do not delete blindly"), confirm intent first; if stealth Accept-Language is desired, wire it up — otherwise remove it to avoid misleading operators who believe they are configuring it.

---

### CFG-004: `DOWNLOAD_METHOD` documented/referenced but is not a config field (misleading dead knob)

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (no `download_method` field), `.env` (line referencing `VKDOWNLOADER_DOWNLOAD_METHOD`), `docs/01-tools/installation.md:123` (`DOWNLOAD_METHOD=auto`) |
| **Classification** | mandatory |

**Description:** Multiple configuration surfaces reference a `download_method` setting that does not exist in the `Settings` model:
- The live `.env` contains `VKDOWNLOADER_DOWNLOAD_METHOD=auto` (commented, but present and implies configurability).
- `docs/01-tools/installation.md:123` documents `DOWNLOAD_METHOD=auto`.
- `docs/11-guides/configuration.md` references a download method only as a **CLI flag** (`--method`/`-m`), not as a config field — internally inconsistent.

The actual download method is selected **only** via the Typer CLI option `method: DownloadMethod` in `cli.py` (lines 288-293, 411-416). There is no `download_method` attribute on `Settings`. An operator who sets `VKDOWNLOADER_DOWNLOAD_METHOD` (or the bare `DOWNLOAD_METHOD`) will believe they configured a persistent default, but the value is silently ignored (it is not in `Settings.model_fields`; the unprefixed form isn't even read).

**Evidence:**
- Runtime probe: `"download_method" in Settings.model_fields` → `False`.
- `cli.py` lines 288-293: `method: DownloadMethod = typer.Option(DownloadMethod.AUTO, "--method", "-m", ...)` — method is CLI-only.
- `.env` line: `# VKDOWNLOADER_DOWNLOAD_METHOD=auto`.
- `installation.md:123`: `DOWNLOAD_METHOD=auto`.

**Recommendation:** Pick one source of truth: either add a `download_method: DownloadMethod` field to `Settings` with default `AUTO` and have the CLI option default to the settings value (so env can override the persistent default), or remove all `DOWNLOAD_METHOD` references from `.env` and `installation.md` and state clearly that method is CLI-only. The current state is a spec deviation that misleads operators.

---

### CFG-005: No `init`/template/scaffold service exists despite config dimensions assuming one

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/cli.py` (only `download` + `batch` commands), `.kilo/commands/audit/phases/02-audit-config.md` (Audit Dimensions 3 & 4) |
| **Classification** | advisory |

**Description:** The phase handbook's Audit Dimensions 3 ("Init / Template Service Correctness") and 4 ("Config Template Quality") assume a config-template/init-scaffold mechanism that copies package templates into a user directory and a config-file template that must match the model. This project has **neither**: configuration is purely environment-based via `.env` + `VKDOWNLOADER_` env vars (no YAML/JSON config file, no `init` CLI command, no package templates). The CLI exposes only `download` and `batch` commands (grep for `app.command` → lines 278, 394). Dimensions 3 & 4 are therefore N/A and were omitted from this report.

**Evidence:**
- `cli.py` defines `@app.command()` (download, line 278) and `@app.command("batch")` (line 394). No `init`/`config`/`template` command.
- No `*.template`, `*.example`, or config-template files found in `src/` or repo root (only a live, untracked `.env`).
- `Settings` uses `BaseSettings` with `env_file=".env"` — there is no file-based config schema to template.

**Recommendation:** Update the configuration docs to state explicitly that this tool is **env/CLI-configured only** (no init step, no config file template), so future auditors and users don't expect a scaffold. If a richer config (file-based) is planned, track it as a feature; otherwise the handbook dimensions should be treated as inapplicable for this project.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- **CFG-001** — Expand `~` in `download_dir`/`log_file` env overrides (correctness; misplaced downloads).
- **CFG-002** — Fix `installation.md` env-var names to use `VKDOWNLOADER_` prefix (documented config is entirely ignored).
- **CFG-004** — Resolve `DOWNLOAD_METHOD` mismatch between docs/`.env` and the CLI-only `method` option (misleading dead knob).

## Advisory Recommendations

- **CFG-003** — Remove or actually consume the unused `accept_language` field (dead config).
- **CFG-005** — Document that configuration is env/CLI-only; no init/template service exists (doc clarity).

## Doc Updates Needed

- **CFG-002** — `docs/01-tools/installation.md` `.env` block (wrong prefixes + nonexistent vars).
- **CFG-004** — `docs/01-tools/installation.md` (`DOWNLOAD_METHOD=auto`) and `.env` (`VKDOWNLOADER_DOWNLOAD_METHOD`).
- **CFG-005** — Configuration docs / handbook scope note for env-only config model.
