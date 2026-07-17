---
name: audit-findings
description: Phase 08 code quality, security & maintainability findings
agent: auditor
alwaysApply: false
---

# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 | `uv run ruff check src/vkdownloader/` | `All checks passed!` — no lint findings |
| R1 | `uv run ruff format --check src/vkdownloader/` | `23 files already formatted` — no format findings |
| R1 | `uv run mypy src/vkdownloader/` | `Success: no issues found in 23 source files` (strict mode); 1 benign note (see QLT-006) |
| R2 | `uv run pytest tests/ -q` | `223 passed in 10.75s` — no failures |
| R3 | Dead-code search (grep for definitions vs call sites) | See QLT-001, QLT-004 |
| R4 | Security search (`print(`, bare `except:`, secrets, credential logging) | No `print()`, no bare `except:`, no hardcoded secrets, no plaintext credential logging found. `.env` contains only commented defaults; `.gitignore` excludes `.env` and `*_cookies.txt`. See QLT-002 for one security-relevant dead-code path. |

Automated tooling (ruff + mypy strict + full test suite) is clean. All findings below come from manual review of behavior and maintainability that the tooling does not catch.

---

## Findings

### QLT-001: `HLSDownloader._build_ffmpeg_cmd` is dead production code with an unsafe cookie pattern

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `HLSDownloader._build_ffmpeg_cmd` (downloader.py:144–166) is never called by any production code path. The only actual ffmpeg invocation, `download_with_ffmpeg` (downloader.py:204–218), builds its command inline and deliberately writes headers to a temporary file (`@{headers_file}` syntax, lines 72–78, 204–212) precisely to avoid putting cookies on the process argument list. `_build_ffmpeg_cmd`, by contrast, embeds `Cookie: {cookies}` directly into the `-headers` argument (lines 148, 158), which is exactly the leak the production path was refactored to prevent. The method is kept alive only by `tests/test_hls_downloader.py` (lines 56, 73, 88, 101, 110, 120), so the tests validate a code path that production no longer uses.

**Evidence:**
- grep for `_build_ffmpeg_cmd` returns definition at `downloader.py:144` and 6 call sites, all in `tests/test_hls_downloader.py`; zero non-test callers.
- `download_with_ffmpeg` uses `_temp_headers_file(...)` + `f"@{headers_file}"` (downloader.py:204–212) instead of `_build_ffmpeg_cmd`.
- `_build_ffmpeg_cmd`: `cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""` then `headers` passed via `-headers` in argv (lines 148–158).

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
- With `extra="forbid"`, an unknown `VKDOWNLOADER_DOWNLOAD_METHOD` env var makes Pydantic reject the whole `Settings()` load.

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

**Recommendation:** Investigate whether the DTO needs to embed these runtime service objects at all. Preferred direction: stop carrying `settings`/`extractor`/`backoff_coordinator`/`semaphore` inside a Pydantic model and pass them as plain function arguments (they are already threaded through the call chain), leaving `HLSDownloadRequest` as a pure data holder (`video_url`, `m3u8_url`, `output_file`, `quality`, `cookies`, `progress_callback`). That removes the circular import, the monkey-patch, and all the `type: ignore` markers, restoring clean `models → (no deps)` layering. Effort: medium.

---

### QLT-005: `black`, `isort`, and `basedpyright` are declared dev dependencies but are unused and redundant with the ruff/mypy toolchain

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

**Description:** `pyproject.toml` declares `black>=24.0.0` and `isort>=6.0.0` in `[project.optional-dependencies].dev` (lines 37–38) and `basedpyright>=1.39.9` in `[dependency-groups].dev` (line 99). None are referenced by any configuration or command: the project formats and sorts imports with ruff (`[tool.ruff.lint]` selects `I` for isort, and `ruff format` is the formatter per the audit's verify commands) and type-checks with mypy (`[tool.mypy] strict = true`). Having black + isort alongside ruff invites conflicting formatting rules (e.g. line length / import grouping) and, with three type checkers/formatters nominally present, contributors get inconsistent signals. There is also a duplicated `pyyaml` declaration (dev optional-deps line 36 and dependency-groups line 100, plus a runtime dep at line 27).

**Evidence:**
- `pyproject.toml:31–39` (`dev` optional deps include `black`, `isort`).
- `pyproject.toml:97–101` (`[dependency-groups].dev` includes `basedpyright`, `pyyaml`).
- grep for `black`, `isort`, `basedpyright` across the repo returns no config sections, no imports, and no command usage.
- Formatting/imports handled by ruff (`select = [..., "I", ...]`, `[tool.ruff.lint.isort]`); typing by mypy strict.

**Recommendation:** Investigate whether black/isort/basedpyright are intentional (e.g. an alternate type checker someone runs locally). If not used by the documented workflow, remove them to keep one formatter (ruff), one import sorter (ruff `I`), and one type checker (mypy), reducing dependency surface and contributor confusion. De-duplicate the `pyyaml` entries. Effort: trivial.

---

### QLT-006: mypy emits an "unused section" note for the `tests.*` override

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

**Description:** Running the source-only type check `uv run mypy src/vkdownloader/` prints `pyproject.toml: note: unused section(s): module = ['tests.*']`. The `[[tool.mypy.overrides]] module = "tests.*"` block (config.py/pyproject.toml lines 89–91) is only meaningful when `tests/` is included in the mypy run; the note surfaces every time the source-only command from the project's commands file is used, adding noise to CI/dev output. It is not an error, but it indicates the mypy invocation and the override configuration are not aligned.

**Evidence:**
- `uv run mypy src/vkdownloader/` output: `pyproject.toml: note: unused section(s): module = ['tests.*']` followed by `Success: no issues found in 23 source files`.
- `pyproject.toml:89–91`: `[[tool.mypy.overrides]] module = "tests.*"` with `disallow_untyped_defs = false`.

**Recommendation:** Align the type-check invocation with the config. Either type-check both packages (e.g. `uv run mypy src/vkdownloader/ tests/`) so the override applies, or move the `tests.*` override under a separate profile so the source-only run stays note-free. Cosmetic but keeps CI output clean. Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 3 |

## Mandatory Fixes

- **QLT-002** (HIGH): `.env` documents `VKDOWNLOADER_DOWNLOAD_METHOD`, but `Settings` uses `extra="forbid"` and has no such field — uncommenting the documented line crashes `download`/`batch` at startup.

## Advisory Recommendations

- **QLT-001** (MEDIUM): Remove/consolidate dead `HLSDownloader._build_ffmpeg_cmd`, which keeps a cookie-in-argv pattern alive only through tests.
- **QLT-004** (MEDIUM): Replace the `HLSDownloadRequest.__init__` monkey-patch/lazy-rebuild with plain function arguments to fix the model→services layering inversion.
- **QLT-003** (LOW): Wire up or remove the unused `accept_language` setting.
- **QLT-005** (LOW): Drop unused/redundant `black`, `isort`, `basedpyright` dev deps and de-duplicate `pyyaml`.
- **QLT-006** (LOW): Align the mypy invocation with the `tests.*` override to silence the "unused section" note.

## Doc Updates Needed

- **QLT-002** (if resolved via option a): Update `.env` to remove the non-functional `VKDOWNLOADER_DOWNLOAD_METHOD` line and document that download method is CLI-only (`--method`).
