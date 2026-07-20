# Phase 02 Audit Findings — Configuration & Settings Models

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/02-audit-config.md
**Status:** complete
**Validated:** no

---

## Findings

### CFG-001: `cookie_source=FILE` silently no-ops instead of raising (primary download flow)

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** The `CookieSource.FILE` enum value and `configuration.md` (line 64) document that selecting `file` "raises `NotImplementedError`. Use `none` or `browser` instead." In reality the `NotImplementedError` is only raised inside `VKVideoExtractor.extract_streams_with_cookies()` (extractor.py lines 123-126). The primary `download`/`batch` CLI flow never calls that method for stream acquisition:

- `cli.py` download (line 111) and batch (line 338) call `extractor.extract_streams(url)`, which ignores `cookie_source` entirely (only checks `== NONE` to skip the browser).
- `downloader.py` `resolve_cookies` (line 631) only invokes `extract_streams_with_cookies` when `cookie_source == BROWSER`.
- `segment_downloader.py` `_refresh_token` (line 381) short-circuits with a warning when `cookie_source != BROWSER` and never reaches the FILE branch.

Consequently `cookie_source=file` (via `--cookie-source file` or `VKDOWNLOADER_COOKIE_SOURCE=file`) is accepted by the model and CLI, is stored without error, and then behaves **identically to `none`** — an anonymous download with no cookies and no error surfaced. A user trying to download authenticated/private content this way gets a silent failure with no indication that the chosen mode is unsupported.

**Evidence:**
```
uv run python -c "from vkdownloader.config import Settings; s=Settings(cookie_source='file'); print(s.cookie_source)"
# -> file   (accepted, no error)
```
`test_config.py::test_cookie_source_validation` (lines 84-85) asserts `FILE` is accepted by the model but never exercises the actual download path, so the gap is untested.

**Recommendation:** Either (a) enforce the FILE rejection at the config/CLI boundary — fail fast in `cli.py`/`Settings` validator when `cookie_source == FILE` is selected, so the documented `NotImplementedError` behavior is real for the user-visible path; or (b) update `configuration.md` and the enum docstring to state that `file` is currently treated as `none` (silent no-op). Option (a) is preferred because it matches the documented contract and prevents silent data/correctness loss on private videos.

---

### CFG-002: `extra="forbid"` does not protect the real config source (env / `.env`)

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py`, `tests/test_config.py` |
| **Classification** | advisory |

**Description:** `Settings.model_config` sets `"extra": "forbid"` (config.py line 119), and `configuration.md` plus `test_config.py` (`test_settings_rejects_unknown_keys`, `test_settings_rejects_multiple_unknown_keys`) imply that unknown configuration keys are rejected. In pydantic-settings v2, `extra="forbid"` only applies to **explicit model-construction kwargs / `model_validate` input** — it does NOT apply to environment variables or the parsed `.env` file. The actual configuration path (env vars + `.env`) therefore silently ignores unknown/mistyped keys with no error and no warning.

Runtime proof:
```
uv run python -c "import os; os.environ['VKDOWNLOADER_BOGUS']='5'; from vkdownloader.config import Settings; print(Settings())"
# -> Settings(...)  (no ValidationError, value ignored)
```
This gives false confidence: a typo such as `VKDOWNLOADER_MAX_RETRIES_` or a renamed setting is silently dropped, producing a misconfigured run that looks correct. The unit tests only exercise the kwargs path, so they pass while the real path is unprotected.

**Evidence:** `config.py` lines 116-121 (`extra: "forbid"`); `test_config.py` lines 48-68 (only `Settings(unknown_key=...)` kwargs). Reproduced above.

**Recommendation:** Validate the environment-derived config explicitly. Options (small effort): (a) read env via `os.environ` filtered by `Settings.model_fields` and feed through `Settings.model_validate(...)` so `extra=forbid` actually applies; (b) after construction, diff the resolved env keys against known field names and warn/log on unknown ones. At minimum, add a test that sets an unknown `VKDOWNLOADER_*` env var and asserts it is either rejected or warned about, so the protection is real for the primary config path.

---

### CFG-003: Repo `.env` template references a non-existent setting (`VKDOWNLOADER_DOWNLOAD_METHOD`)

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.env` (repo root), `docs/11-guides/configuration.md`, `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** The shipped `.env` (repo root) line 25 contains `VKDOWNLOADER_DOWNLOAD_METHOD=auto`, but no `download_method` field exists in `Settings` (config.py). The `DownloadMethod` enum is only used as a CLI option, not as a persisted setting. Because of CFG-002, this line is silently ignored at load time. `configuration.md` also does not list `download_method` as a setting, so the `.env` template disagrees with both the code and the docs.

**Evidence:**
```
.env (line 25): # VKDOWNLOADER_DOWNLOAD_METHOD=auto
Settings.model_fields keys: headless, user_agent, timezone, locale, max_retries,
  download_timeout, browser_pre_interaction_wait, browser_post_interaction_wait,
  ssl_verify, download_dir, max_concurrent_downloads, throttled_rate, http_chunk_size,
  cookie_source, log_level, log_file   (no download_method)
```

**Recommendation:** Remove the stale `VKDOWNLOADER_DOWNLOAD_METHOD` line from `.env`, or (if a persisted default download method is intended) add a typed `download_method: DownloadMethod` field to `Settings` and document it in `configuration.md`. Keeping a dead knob in the template misleads users into thinking it is configurable.

---

### CFG-004: `log_file`/`download_dir` resolved at construction; missing parent dir yields unhelpful error

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/config.py#setup_logging` |
| **Classification** | advisory |

**Description:** The `expand_tilde_paths` validator (config.py lines 102-107) calls `.expanduser().resolve()` on `download_dir` and `log_file` at model-construction time, eagerly resolving symlinks and making relative paths absolute against the current working directory. More importantly, when `log_file` points to a path whose parent directory does not exist, `setup_logging()` (config.py lines 124-137) calls `logging.FileHandler(settings.log_file)` directly, which raises a bare `FileNotFoundError` with no actionable message telling the user to create the directory. `configuration.md` (line 156-163) states only "Optional path to a file for structured JSON log output" with no prerequisite about the parent directory existing.

**Evidence:** `config.py` lines 129-137; runtime: setting `VKDOWNLOADER_LOG_FILE=/nonexistent_dir/vk.log` raises `FileNotFoundError: [Errno 2] No such file or directory: '/nonexistent_dir/vk.log'` before any CLI help text.

**Recommendation:** In `setup_logging`, ensure `settings.log_file.parent.mkdir(parents=True, exist_ok=True)` before constructing the `FileHandler`, and emit a clear log/error if the path is not writable. Also consider deferring `.resolve()` of `download_dir`/`log_file` until first use (or documenting that relative paths are resolved against CWD), to avoid surprising absolute paths when the tool is invoked from different directories.

---

### CFG-005: `.env` is loaded relative to CWD only — not portable for installed / console-script usage

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** `model_config` uses `"env_file": ".env"` (config.py line 117), which pydantic-settings resolves relative to the current working directory, not the package install location. When the tool is installed and run as a console script from an arbitrary directory (e.g. `vkdownloader download ...` from `C:\Users\...`), the repo-root `.env` is not found and env-based configuration is silently absent. Users have no documented way to supply a config file outside the repo.

**Evidence:** `config.py` lines 116-121; behavior confirmed by pydantic-settings semantics (`.env` resolved from CWD).

**Recommendation:** Document that configuration is env-only and `.env` must live in the working directory, OR support an explicit, documented config location (e.g. `VKDOWNLOADER_CONFIG` env var or a user-level path such as `%APPDATA%/vkdownloader/.env` on Windows). Keep it simple — a single documented location is enough; avoid introducing a full config-file parser for a CLI tool of this size.

---

### CFG-006: `throttled_rate` default (100 KB/s) may abort legitimate slow downloads

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `throttled_rate` (default 100000 bytes/sec ≈ 100 KB/s, range 50000-1000000) maps to yt-dlp's `throttledratelimit`, which **aborts** a download when throughput drops below the threshold and triggers re-extraction. On throttled CDN connections or large files, sustained throughput under 100 KB/s is common, so the default can cause spurious aborts/retries rather than protecting the user. The `configuration.md` wording ("Minimum download rate ... before throttling triggers re-extract") matches the code but does not warn about this trade-off.

**Evidence:** `config.py` lines 75-80; `downloader.py` line 169 (`"throttledratelimit": settings.throttled_rate`).

**Recommendation:** Either raise the default (e.g. to a value less likely to trip on normal VK throttling) or document the trade-off explicitly in `configuration.md` with a recommended value for slow connections. Low priority; flagged for operational clarity, not a defect.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 4 |

## Mandatory Fixes

- **CFG-001** — `cookie_source=FILE` silently behaves like `none` in the primary download flow instead of raising the documented `NotImplementedError`; fail fast at the config/CLI boundary or correct the docs. (correctness, HIGH)

## Advisory Recommendations

- **CFG-002** — `extra="forbid"` does not protect env/`.env` config; unknown keys are silently ignored. Validate env-derived config or warn on unknown keys; fix the misleading test.
- **CFG-003** — Repo `.env` references non-existent `VKDOWNLOADER_DOWNLOAD_METHOD`; remove or implement it.
- **CFG-004** — `log_file` parent dir not created; unhelpful `FileNotFoundError`. Create parent dir in `setup_logging`.
- **CFG-005** — `.env` resolved from CWD only; not portable for installed usage. Document or support a fixed config location.
- **CFG-006** — `throttled_rate` default may abort legitimate slow downloads; raise default or document trade-off.

## Doc Updates Needed

- **CFG-001** — `configuration.md` (cookie_source section) and `CookieSource.FILE` docstring imply a hard error that does not occur on the real path.
- **CFG-003** — `configuration.md` does not list `download_method`; `.env` does. Reconcile template and docs.
- **CFG-006** — `configuration.md` should note the abort/retry trade-off of `throttled_rate`.
