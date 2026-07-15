# Phase 02 Audit Findings — Configuration & Pydantic Models

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/02-audit-config.md
**Status:** complete
**Validated:** no

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
- Field defined but never referenced in production: `config.py:53-56`. Grep for `settings.download_dir` across `src/` returns no hits (only `tests/conftest.py` and `tests/test_cli.py` pass the value into `Settings(...)` with no consumer).
- CLI ignores it: `cli.py:105` builds `Settings(cookie_source=..., ssl_verify=...)` and `cli.py:120,257` use the `--output` option value, never `settings.download_dir`.
- Docs promise it works: `docs/11-guides/configuration.md:30` (`download_dir | VKDOWNLOADER_DOWNLOAD_DIR | ~/Downloads/vkdownloader | Output directory`) and `:150-153`.

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
- No production read of `settings.download_method` (grep returns none). `downloader.py:520` matches on the `method` *argument*, not `settings.download_method`.
- CLI: `cli.py:76-81` (`method` option, default `AUTO`) passed to `perform_download` at `cli.py:132,269`; `Settings(...)` built at `cli.py:105,247` does not include `download_method`.
- Docs: `configuration.md:34` and `:79`.

**Recommendation:** Either consume `settings.download_method` as the default when the CLI `--method` is not explicitly provided (so the env var has effect), or remove the field and its documentation. Note the doc table at `configuration.md:49-54` also describes `auto` behavior that depends on `cookie_source`, which is independent of this field's consumption.

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
- Field defined `config.py:27-30`; never referenced in `src/` production code (grep for `settings.timezone` / `timezone` in `browser.py` returns only the field definition and tests).
- `browser.py:64-68` sets `viewport`, `user_agent`, `locale` — no timezone.
- Docs: `configuration.md:25`.

**Recommendation:** Either wire `timezone` into the browser stealth configuration (e.g., Playwright `timezone_id` on the context at `browser.py:64`) or remove the field and its doc entry. If stealth timezone is a future intent, keep the field but mark it explicitly as "not yet applied" in docs to avoid implying working behavior.

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
- `dtos.py:59-70` `_ensure_model_rebuilt()` mutates the module namespace and calls `model_rebuild()`; `dtos.py:74-83` replaces `HLSDownloadRequest.__init__`.
- mypy on this file returns "no issues found" precisely because the `# type: ignore` suppresses the undefined-name errors.

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
- `config.py:131` `settings = Settings()`; grep for `config.settings` / `from ... import settings` / `vkdownloader.config.settings` across `src/` returns no production references (only the class is imported).
- `http_client.py:29` `self.settings = settings if settings is not None else Settings()` with docstring at `:21-28` claiming global usage.
- `browser.py:23` `self.settings = settings if settings is not None else Settings()` with docstring at `:18-22` claiming global usage.

**Recommendation:** Remove the unused module-level `settings = Settings()` singleton (it also avoids the import-time env read) and correct the two docstrings to say "constructs a new `Settings()` from environment when not provided" (or, if a shared default is desired, actually import and use `vkdownloader.config.settings`). This removes dead code and aligns docs with real behavior.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

- **CFG-001** — `download_dir` is silently ignored; files land in the CWD instead of the configured directory. Correctness defect requiring fix (wire `--output` default through `settings.download_dir`, or remove the field + docs).

## Advisory Recommendations

- **CFG-002** — `download_method` env var is never read; honor it as the CLI default or drop it from docs.
- **CFG-003** — `timezone` is never applied to browser stealth; wire it in or remove it.
- **CFG-004** — `HLSDownloadRequest` smuggles runtime objects via `arbitrary_types_allowed` + `__init__` monkey-patch; refactor to pass collaborators as arguments and validate only data.
- **CFG-005** — Dead module-level `settings` singleton and inaccurate "uses global settings" docstrings.

## Doc Updates Needed

- **CFG-002** — `docs/11-guides/configuration.md:34,79`: remove or qualify `download_method`/`VKDOWNLOADER_DOWNLOAD_METHOD` as working.
- **CFG-003** — `docs/11-guides/configuration.md:25`: mark `timezone` as not-yet-applied or remove.
- **CFG-005** — Fix docstrings in `http_client.py:21-28` and `browser.py:18-22`.
