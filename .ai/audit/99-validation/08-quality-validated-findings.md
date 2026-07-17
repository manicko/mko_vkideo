---
name: validated-audit-findings
description: Phase 08 code quality, security & maintainability validated findings
agent: validator
alwaysApply: false
---

# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** auditor (validated)  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** yes  

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 | `uv run ruff check src/vkdownloader/` | `All checks passed!` — no lint findings |
| R1 | `uv run ruff format --check src/vkdownloader/` | `23 files already formatted` — no format findings |
| R1 | `uv run mypy src/vkdownloader/` | `Success: no issues found in 23 source files` (strict mode); note about unused tests.* section confirmed |
| R2 | `uv run pytest tests/ -q` | `223 passed in 10.75s` — no failures |
| R3 | Dead-code search (grep for definitions vs call sites) | Verified — `_build_ffmpeg_cmd` only called in tests |
| R4 | Security search (`print(`, bare `except:`, secrets, credential logging) | No issues found |

---

## Findings

### QLT-001: `HLSDownloader._build_ffmpeg_cmd` is dead production code with an unsafe cookie pattern

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `tests/test_hls_downloader.py` |
| **Classification** | advisory |

**Description:** `HLSDownloader._build_ffmpeg_cmd` (downloader.py:144–166) is never called by any production code path. The only actual ffmpeg invocation, `download_with_ffmpeg` (downloader.py:204–218), builds its command inline and deliberately writes headers to a temporary file (`@{headers_file}` syntax, lines 72–78, 204–212) precisely to avoid putting cookies on the process argument list. `_build_ffmpeg_cmd`, by contrast, embeds `Cookie: {cookies}` directly into the `-headers` argument (lines 148, 158), which is exactly the leak the production path was refactored to prevent. The method is kept alive only by `tests/test_hls_downloader.py` (lines 56, 73, 88, 101, 110, 120), so the tests validate a code path that production no longer uses.

**Evidence:**
- grep for `_build_ffmpeg_cmd` returns definition at `downloader.py:144` and 6 call sites, all in `tests/test_hls_downloader.py`; zero non-test callers.
- `download_with_ffmpeg` uses `_temp_headers_file(...)` + `f"@{headers_file}"` (downloader.py:204–212) instead of `_build_ffmpeg_cmd`.
- `_build_ffmpeg_cmd`: `cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""` then `headers` passed via `-headers` in argv (lines 148–158).

**Validation Note:**
> **Action:** validated
> **Detail:** Finding is technically correct. The method exists, is unused in production, and contains the cookie-in-argv pattern that was intentionally removed from the actual implementation. The tests exclusively exercise this dead code path.

**Recommendation:** Investigate why the method exists (likely a leftover from before the temp-headers refactor). If it is truly unused, remove it and its tests, or if a shared command-builder is desired, refactor `download_with_ffmpeg` to use a single builder that itself uses the temp-file pattern. Keeping a second, less-safe command builder alive via tests risks it being reintroduced into production. Effort: small.

---

### QLT-002: `.env` documents `VKDOWNLOADER_DOWNLOAD_METHOD` but `Settings` forbids extras — following the docs crashes the CLI

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `.env` |
| **Classification** | mandatory |

**Description:** `.env` (line 26) documents `# VKDOWNLOADER_DOWNLOAD_METHOD=auto` as a valid setting, but `Settings` (config.py:15–106) declares no `download_method` field, and `model_config` sets `"extra": "forbid"` (config.py:104) with `"env_prefix": "VKDOWNLOADER_"` (config.py:105). If a user uncomments that documented line, every `Settings(...)` construction in the CLI (`cli.py:312`, `cli.py:441`) raises a Pydantic `ValidationError` for an unexpected field, aborting `download`/`batch` before any work begins. The download method is actually only selectable via the `--method` CLI flag, so the documented env var is both non-functional and actively harmful.

**Evidence:**
- `.env:26`: `# VKDOWNLOADER_DOWNLOAD_METHOD=auto`
- `config.py:101–106`: `model_config = { ... "extra": "forbid", "env_prefix": "VKDOWNLOADER_" }`
- grep for `download_method` in `src/` returns no field definition (only the unrelated log key `unknown_download_method` at downloader.py:758).
- The `--method` flag in `cli.py:288–293` and `cli.py:411–416` provides the only way to set download method.

**Validation Note:**
> **Action:** validated
> **Detail:** Finding is correct. The `.env` documentation claims an env var exists that would crash the application if enabled. The `extra="forbid"` setting causes Pydantic to reject unknown fields. This is a documentation-code mismatch that creates a latent crash scenario.

**Recommendation:** Resolve the doc/code mismatch. Either (a) remove the `VKDOWNLOADER_DOWNLOAD_METHOD` line from `.env` and note that method is CLI-only, or (b) add a real `download_method: DownloadMethod` field to `Settings` and have `download`/`batch` fall back to it when `--method` is not overridden. Option (a) is `[DOC-UPDATE]` and trivial; option (b) is small and makes the documented behavior real. Given `extra="forbid"`, leaving the doc as-is is a latent crash. Effort: trivial–small.

---

### QLT-003: `accept_language` setting is defined but never applied to browser requests

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | advisory |

**Description:** `Settings.accept_language` (config.py:27–30) is declared with a description implying it sets the `Accept-Language` header for browser requests, but it is never read anywhere. `BrowserManager.create_stealth_page` (browser.py:64–69) configures `user_agent`, `locale`, and `timezone_id` from settings, but does not pass `extra_http_headers={"Accept-Language": ...}` or otherwise consume `accept_language`. The setting is effectively dead configuration: users can set `VKDOWNLOADER_ACCEPT_LANGUAGE` (documented in `.env:10`) with no effect.

**Evidence:**
- `config.py:27`: `accept_language: str = Field(default="ru-RU,ru;q=0.9,...")`
- grep for `accept_language` in `src/` returns only the definition at `config.py:27`; no consumer.
- `browser.py:64–69`: `new_context(...)` sets `viewport`, `user_agent`, `locale`, `timezone_id` — no Accept-Language.

**Validation Note:**
> **Action:** validated
> **Detail:** Confirmed. The field is defined with a descriptive docstring about setting the Accept-Language header, but `BrowserManager.create_stealth_page` never uses it. The `.env` documentation (line 10) also references this setting, creating a false promise of functionality.

**Recommendation:** Investigate intended purpose. Either wire `accept_language` into the browser context (e.g. `extra_http_headers={"Accept-Language": self.settings.accept_language}`), which improves the stealth consistency the field was clearly meant for, or remove the unused field and its `.env` documentation. Effort: trivial.

---

### QLT-004: `HLSDownloadRequest` monkey-patches its own `__init__` for lazy forward-reference rebuild — fragile, hard-to-maintain workaround

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/dtos.py` |
| **Classification** | advisory |

**Description:** `dtos.py` (lines 33–61) replaces the Pydantic model's `__init__` at import time (`HLSDownloadRequest.__init__ = _lazy_init`, line 61) so that forward references to `Settings`, `VKVideoExtractor`, and `URLBackoffCoordinator` are resolved on first instantiation. To do this it also mutates its own module namespace (lines 43–45 set `dtos_module.Settings = ...` etc.) and stashes a private flag on the class (`_model_rebuilt`, line 57). This is a heavy, non-idiomatic mechanism to dodge a circular import: the DTO layer imports upward from `config` and `services`, which is itself a layering inversion (a model reaching into services). It relies on several `# type: ignore` escape hatches (lines 43–45, 57, 58, 61) and undocumented Pydantic internals (`model_rebuild`, method reassignment) that can break on Pydantic upgrades.

**Evidence:**
- `dtos.py:50–61`: `_original_init = HLSDownloadRequest.__init__` ... `HLSDownloadRequest.__init__ = _lazy_init  # type: ignore[method-assign]`.
- `dtos.py:43–45`: runtime mutation of module globals with `# type: ignore[attr-defined]`.
- `dtos.py:23–26`: fields typed via string forward refs with `# type: ignore[name-defined]  # noqa: F821`.
- Root cause: a model in `models/` depending on `config.Settings`, `services.extractor.VKVideoExtractor`, and `services.downloader_throttle.URLBackoffCoordinator` (a model → services → config upward dependency).

**Validation Note:**
> **Action:** validated
> **Detail:** Code inspection confirms the monkey-patch pattern at lines 50-61. The `HLSDownloadRequest` DTO carries runtime service objects (`settings`, `extractor`, `backoff_coordinator`, `semaphore`) that create the circular import. This is a layering violation and a maintenance risk.

**Recommendation:** Investigate whether the DTO needs to embed these runtime service objects at all. Preferred direction: stop carrying `settings`/`extractor`/`backoff_coordinator`/`semaphore` inside a Pydantic model and pass them as plain function arguments (they are already threaded through the call chain), leaving `HLSDownloadRequest` as a pure data holder (`video_url`, `m3u8_url`, `output_file`, `quality`, `cookies`, `progress_callback`). That removes the circular import, the monkey-patch, and all the `type: ignore` markers, restoring clean `models → (no deps)` layering. Effort: medium.

---

### QLT-005: `black`, `isort`, and `basedpyright` are declared dev dependencies but are unused and redundant with the ruff/mypy toolchain

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | ~~BEST-PRACTICE~~ [REJECTED] |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

> **Rejection reason:** This is a cosmetic/low-ROI finding. While `black`, `isort`, and `basedpyright` are declared in `pyproject.toml` (lines 37–38, 99–100), they are not actively breaking anything. The project works correctly with ruff + mypy. Removing unused dependencies is a minor cleanup with no operational impact. For a small/alpha project, this falls under "low-value complexity" per the validator guidelines.

**Evidence:**
- `pyproject.toml:31–39` (`dev` optional deps include `black`, `isort`).
- `pyproject.toml:97–101` (`[dependency-groups].dev` includes `basedpyright`, `pyyaml` duplicate).
- grep for `black`, `isort`, `basedpyright` across the repo returns no config sections, no imports, and no command usage.
- Formatting/imports handled by ruff (`select = [..., "I", ...]`, `[tool.ruff.lint.isort]`); typing by mypy strict.

---

### QLT-006: mypy emits an "unused section" note for the `tests.*` override

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | LOW |
| **Type** | ~~BEST-PRACTICE~~ [REJECTED] |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

> **Rejection reason:** This is a cosmetic issue (note, not error) with no functional impact. The mypy run succeeds cleanly. The `tests.*` override exists for legitimate reasons (allowing untyped defs in tests), but is only relevant when tests are included in the type check. Fixing this would be either (a) removing the override (loses the benefit for test runs), or (b) changing the project's mypy invocation to include tests. Neither has operational value for a project that only type-checks source code. Falls under "low ROI" per validator guidelines.

**Evidence:**
- `uv run mypy src/vkdownloader/` output: `pyproject.toml: note: unused section(s): module = ['tests.*']` followed by `Success: no issues found in 23 source files`.
- `pyproject.toml:89–91`: `[[tool.mypy.overrides]] module = "tests.*"` with `disallow_untyped_defs = false`.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | QLT-001, QLT-002, QLT-003, QLT-004 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 2 | QLT-005, QLT-006 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| QLT-005 | `black`, `isort`, and `basedpyright` are declared dev dependencies but are unused | Low ROI: cosmetic cleanup with no operational impact; project works correctly with ruff/mypy toolchain |
| QLT-006 | mypy emits an "unused section" note for the `tests.*` override | Low ROI: cosmetic note with no functional impact; mypy passes successfully |

### Merged Findings

N/A

### Reclassified Findings

N/A

---

## Validated Findings

| ID | Title | Classification Note |
|----|-------|---------------------|
| QLT-001 | `_build_ffmpeg_cmd` is dead production code | MEDIUM severity: dead code + unsafe cookie pattern kept alive by tests |
| QLT-002 | `.env` documents `VKDOWNLOADER_DOWNLOAD_METHOD` but `Settings` forbids extras | HIGH severity: SPEC-DEVIATION causing potential crash on uncommenting documented setting |
| QLT-003 | `accept_language` setting is defined but never applied | LOW severity: dead configuration with documented expectation of functionality |
| QLT-004 | `HLSDownloadRequest` monkey-patches `__init__` | MEDIUM severity: architectural layering violation with maintenance risk |