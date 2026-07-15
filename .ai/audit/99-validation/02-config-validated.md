# Phase 02 Audit Findings — Configuration & Pydantic Models (Validated)

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/02-audit-config.md
**Status:** complete
**Validated:** yes (validation complete)

---

## Discovery Note (config architecture as actually implemented)

This project does **not** use the YAML + `TelepostConfigReader` + `init_project()` + `platformdirs` flow assumed by the generic phase template. The actual configuration architecture is:

- **Single Pydantic model:** `vkdownloader.config.Settings` (a `pydantic_settings.BaseSettings` subclass), sourced from environment variables / a CWD-relative `.env` file.
- **No YAML config files, no `config_example.yaml` template, no `init` service, no package-vs-user config separation.** Therefore audit dimensions 2 (YAML config loading / path resolution), 3 (init service), and 4 (config template quality) from the template have no corresponding code and are omitted (no findings — they are simply not applicable to this project).
- Discovery was performed by reading `config.py`, `models/enums.py`, `models/dtos.py`, `models/video.py`, `cli.py`, the service/infrastructure consumers, `docs/11-guides/configuration.md`, and by running the runtime verification below.

### Runtime Verification (per phase mandatory steps)

- **R1 — Model instantiation:** `Settings()` instantiates with documented defaults; validators fire on out-of-range values (`throttled_rate`, `http_chunk_size`) and on unknown keys (`extra="forbid"`). 12/12 config tests pass.
- **R2 — Config loading:** No YAML config exists; env-var loading verified by `tests/test_config.py::test_cookie_source_from_env` (passes). N/A for YAML.
- **R3 — Linter / type checker:** `uv run ruff check src/vkdownloader/config.py src/vkdownloader/models/dtos.py src/vkdownloader/cli.py` → "All checks passed!". `uv run mypy ...` → "Success: no issues found in 2 source files".
- **R4 — Tests:** `uv run pytest tests/test_config.py -q` → `12 passed`.

---

## Findings

### CFG-001: `download_dir` config field is never consumed (silent no-op)

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (field def), `src/vkdownloader/cli.py` (download/batch commands), `docs/11-guides/configuration.md` |
| **Classification** | mandatory |

**Description:** The `Settings.download_dir` field (default `Path.home() / "Downloads" / "vkdownloader"`, env var `VKDOWNLOADER_DOWNLOAD_DIR`) is documented as "Output directory for downloaded videos" and is even listed in the example `.env` file. However, no production code path ever reads `settings.download_dir`. The CLI `download`/`batch` commands use their own `--output` option (default `"."`) and pass that `output` value straight to `validate_output_path` / `perform_download`. As a result, setting `VKDOWNLOADER_DOWNLOAD_DIR` (or relying on the default) has **zero effect** — files are written to the current directory instead of the configured directory. This is a silent correctness defect: a user who configures an output location gets files placed elsewhere with no warning.

**Evidence:**
- Field defined `config.py:53-56` but never referenced in production code (grep for `settings.download_dir` across `src/` returns no hits).
- CLI `download` command at `cli.py:70-75` uses `--output` option with default `"."`, and `cli.py:120` passes `output` directly to `perform_download` without consulting `settings.download_dir`.
- CLI `batch` command at `cli.py:189-194` similarly uses `--output` with default `"."`, and `cli.py:257` passes `output` directly.
- Docs `configuration.md:30` documents `download_dir | VKDOWNLOADER_DOWNLOAD_DIR | ~/Downloads/vkdownloader | Output directory`.

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. `download_dir` is a documented configuration field that has zero effect on runtime behavior. Files are always written to the `--output` path (defaulting to `"."`) rather than the configured `download_dir`. This is a silent correctness defect where documentation promises functionality that does not exist.
> - **See also:** CFG-003 (similar pattern of documented-but-unconsumed stealth configuration)
> - **Note:** CFG-002 recommends removal of the unused `download_method` field; no coupling risk.

**Recommendation:** Either (a) make the CLI honor `settings.download_dir` as the fallback when `--output` is not supplied (and resolve it as an absolute path), or (b) remove the field and its documentation to avoid a misleading dead knob. Option (a) restores the documented behavior; if the CLI `--output` is intended to be authoritative, the docs must state that env var is ignored. Since the doc choice implies the field should work, fixing the code (route `--output` default through `settings.download_dir`) is preferred.

---

### CFG-002: `download_method` env var / Settings field is never read

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader.py`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** `Settings.download_method` (default `DownloadMethod.AUTO`, env var `VKDOWNLOADER_DOWNLOAD_METHOD`) is documented as a working configuration option, but it is never read anywhere in production code. The download method is decided exclusively by the CLI `--method` option, which is passed explicitly to `perform_download(..., method, ...)` and then `match`ed at `downloader.py:520`. Because the CLI constructs `Settings(cookie_source=..., ssl_verify=...)` without `download_method`, the model always falls back to its default (`AUTO`), and the explicit CLI option overrides it. Consequently `VKDOWNLOADER_DOWNLOAD_METHOD` is silently ignored, contradicting `docs/11-guides/configuration.md:34` and the example `.env` at `:79`.

**Evidence:**
- `download_method` defined `config.py:75-78` but never read in production code (grep for `settings.download_method` returns no hits).
- CLI `download` command at `cli.py:76-81` passes `method` directly to `perform_download` at `cli.py:132`.
- CLI `batch` command at `cli.py:195-200` passes `method` directly to `perform_download` at `cli.py:269`.
- `perform_download` at `downloader.py:520` matches on the `method` argument, not `settings.download_method`.
- Docs `configuration.md:34` lists `download_method` as configurable via env var, and `:79` shows it in example `.env`.

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. `VKDOWNLOADER_DOWNLOAD_METHOD` environment variable has zero effect. Users cannot configure download method via environment; only CLI `--method` option works. This contradicts documentation.
> - **See also:** CFG-003 (timezone field in same situation; unlike `download_dir`, timezone should be wired in since documentation indicates active intent)

**Recommendation:** Remove `download_method` field from `Settings` (config.py:75-78) and its documentation (configuration.md:34 and :79). The CLI `--method` option provides explicit control with a hardcoded `DownloadMethod.AUTO` default, and unlike `cookie_source` (which is passed into Settings and consumed), there is no architectural pattern for CLI options to fall back to config values. The env var has never been functional — removing the field eliminates a misleading dead knob and aligns code with actual behavior.

---

### CFG-003: `timezone` config field is never consumed

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/infrastructure/browser.py`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** `Settings.timezone` (default `"Europe/Moscow"`, env var `VKDOWNLOADER_TIMEZONE`) is documented as "Timezone for stealth configuration" but is never applied. `BrowserManager.create_stealth_page` configures the Playwright context with `user_agent` and `locale` only (`browser.py:64-68`); `timezone` is not passed to any stealth script or browser context setting. The `stealth.min.js` injection also does not receive it. So the field is dead config that misleads users into thinking timezone spoofing is active.

**Evidence:**
- Field defined `config.py:27-30` but never referenced in production code (grep for `settings.timezone` / `timezone` in `browser.py` returns only the field definition).
- `browser.py:64-68` sets `viewport`, `user_agent`, `locale` — no timezone. Playwright's `new_context()` supports `timezone_id` parameter but it is not used.
- Docs `configuration.md:25` lists `timezone` as "Timezone for stealth configuration".

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. `timezone` is documented as configuring browser stealth but Playwright's `timezone_id` context option is never set. Users cannot configure timezone via environment.
> - **See also:** CFG-001 (download_dir is a more severe case — silent correctness defect where files go to wrong location)

**Recommendation:** Wire `timezone` into browser stealth configuration in `browser.py`. Add `timezone_id=self.settings.timezone` to `self.browser.new_context()` at line 64-68, alongside the existing `user_agent` and `locale` parameters. This is a one-line fix that restores documented behavior and is consistent with Playwright's built-in stealth API. The documentation explicitly describes this as a stealth configuration feature, confirming the intent to apply timezone spoofing.

---

### CFG-004: `HLSDownloadRequest` DTO uses `arbitrary_types_allowed` + runtime `__init__` monkey-patch to resolve forward refs

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/dtos.py` |
| **Classification** | advisory |

**Description:** `HLSDownloadRequest` is a Pydantic model that holds runtime objects (`Settings`, `VKVideoExtractor`, `URLBackoffCoordinator`, `asyncio.Semaphore`, a `Callable`). To accept these non-Pydantic, non-serializable types it sets `model_config = ConfigDict(arbitrary_types_allowed=True)` (`dtos.py:27`) and then globally monkey-patches `HLSDownloadRequest.__init__` (`dtos.py:74-83`) to lazily call `model_rebuild()` and bind the forward-reference names into the module namespace (`dtos.py:59-70`). This pattern:

1. **Defeats Pydantic validation** — with `arbitrary_types_allowed=True` these fields are accepted as-is with no validation, so the model provides no safety for its most important fields.
2. **Hides real type errors** — the forward references use `# type: ignore[name-defined]` (`dtos.py:35-38`), so mypy cannot catch mismatches (and indeed mypy reports nothing despite the names being undefined at module load).
3. **Is fragile global mutation** — reassigning `HLSDownloadRequest.__init__` at import time breaks under subclassing, pickling/multiprocessing, and any code that imports the class before the patch; the `_model_rebuilt` flag is attached as a class attribute via `# type: ignore`.

This is a Pydantic Model Correctness concern: a "request" DTO that smuggles live service objects and callbacks inside a validated model is an anti-pattern that obscures the config→service boundary the phase is auditing.

**Evidence:**
- `dtos.py:27` `model_config = ConfigDict(arbitrary_types_allowed=True)`.
- `dtos.py:35-38` `settings: Settings | None = None  # type: ignore[name-defined]  # noqa: F821` (and same for `VKVideoExtractor`, `URLBackoffCoordinator`).
- `dtos.py:59-70` `_ensure_model_rebuilt()` mutates the module namespace and calls `model_rebuild()`.
- `dtos.py:74-83` replaces `HLSDownloadRequest.__init__`.
- `segment_downloader.py:173` calls `download_hls_with_resume(HLSDownloadRequest(..., settings=settings, ...))` at lines 314, 304, 547-558, 645, 791, 846, 1001.

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. The `HLSDownloadRequest` model uses `arbitrary_types_allowed=True` and module-level monkey-patching to work around circular imports, but this introduces real maintainability risks. `Settings`, `VKVideoExtractor`, and `URLBackoffCoordinator` are passed into the DTO and extracted in `segment_downloader.py` (lines 198-201) — they are used as regular objects, not validated data. The `__init__` monkey-patch is indeed fragile (breaks under subclassing, affects multiprocessing, and relies on `# type: ignore` to silence mypy).
> - **See also:** CFG-005 (related to Settings instantiation patterns)

**Recommendation:** Keep the *data* fields (`video_url`, `m3u8_url`, `output_file`, `quality`, `cookies`) in the Pydantic model and pass runtime collaborators (`settings`, `extractor`, `backoff_coordinator`, `semaphore`, `progress_callback`) as plain function/constructor arguments to the downloader instead of inside the validated model. If they must remain on the model, resolve forward refs properly with `TYPE_CHECKING` imports plus string annotations and a single `model_rebuild()` at module load — and drop `arbitrary_types_allowed=True` in favor of typed dependencies. This restores validation, real type-checking, and removes import-time global mutation.

---

### CFG-005: Module-level `settings = Settings()` is dead, and docstrings falsely claim "uses global settings"

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description:** `config.py:131` creates a module-level singleton `settings = Settings()` at import time. No production module ever imports this instance — every consumer imports only the `Settings` class and either receives a `Settings` instance as an argument or constructs a fresh `Settings()` when `settings is None`. As a result the global is dead code, and it also causes an import-time side effect (reads `.env`/env vars immediately on `import vkdownloader.config`).

Worse, the docstrings on the consumers are inaccurate: `HttpClient.__init__` (`http_client.py:21-28`) and `BrowserManager.__init__` (`browser.py:18-22`) both state "Uses global settings if not provided", but the code actually does `self.settings = settings if settings is not None else Settings()` — i.e., a brand-new instance, never the module global. This misleads maintainers about where configuration originates.

**Evidence:**
- `config.py:131` `settings = Settings()`; no production code imports this instance (grep for `config.settings` / `from ... import settings` / `vkdownloader.config.settings` returns no hits in `src/`).
- `http_client.py:29` `self.settings = settings if settings is not None else Settings()` with docstring `:21-28` claiming "Uses global settings if not provided".
- `browser.py:23` `self.settings = settings if settings is not None else Settings()` with docstring `:18-22` claiming "Uses global settings if not provided".
- Same pattern in `downloader.py:102`, `extractor.py:34`.

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. The module-level `settings` singleton at `config.py:131` is never imported or used by any production code. All consumers either receive settings as an argument or create a fresh `Settings()` instance. The docstrings in `HttpClient.__init__` and `BrowserManager.__init__` incorrectly state "Uses global settings if not provided" when the code actually constructs a new instance. This is a documentation inconsistency.
> - **See also:** CFG-004 (same settings instantiation pattern)

**Recommendation:** Remove the unused module-level `settings = Settings()` singleton (it also avoids the import-time env read) and correct the two docstrings to say "constructs a new `Settings()` from environment when not provided" (or, if a shared default is desired, actually import and use `vkdownloader.config.settings`). This removes dead code and aligns docs with real behavior.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | — |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Cross-Phase Conflicts

None detected. CFG-001 (wiring download_dir), CFG-002 (removal), CFG-003 (wiring timezone), and CFG-005 (removing dead singleton) can be implemented independently. The findings in this phase are consistent with CLI phase findings (CLI-004 mentions `Settings()` construction patterns that align with CFG-005).

### Rollout Safety Assessment

The recommended fixes for CFG-001 and CFG-003 have different risk profiles:

1. **CFG-001:** Wiring `download_dir` into CLI defaults is an architectural change that modifies how paths are resolved. This requires updating both `download` and `batch` commands to use `settings.download_dir` as the fallback default.
2. **CFG-003:** Adding `timezone_id=self.settings.timezone` to `browser.py:64` is a one-line addition that restores documented stealth configuration with minimal risk.
3. **CFG-004 implementation risk:** Refactoring `HLSDownloadRequest` to remove runtime collaborators requires changes to `perform_download` and `download_hls_with_resume` signatures. This is a larger refactor that should be isolated from the other config fixes.

### Architectural Impact

- **CFG-001:** Wiring `settings.download_dir` into CLI defaults restores documented behavior; this is a missing feature rather than incorrect architecture.
- **CFG-002:** Removing the unused `download_method` field cleans up dead code and eliminates user confusion about non-functional env var support.
- **CFG-003:** Adding `timezone_id` to browser stealth configuration restores documented stealth behavior; this is a missing feature.
- **CFG-004:** The `HLSDownloadRequest` pattern introduces unnecessary complexity and type-checking fragility. While functional, it obscures the boundary between "validated data" and "runtime services".
- **CFG-005:** The dead module-level singleton is leftover from a design iteration that moved to explicit settings passing. Removing it cleans up the codebase.

## Validation Summary Table

| Action | Count | IDs |
|--------|-------|-----|
| Validated (unchanged) | 5 | CFG-001, CFG-002, CFG-003, CFG-004, CFG-005 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |