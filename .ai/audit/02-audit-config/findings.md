# Phase 02 Audit Findings — Configuration & Settings Models

**Executor:** auditor (Senior architecture auditor)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/02-audit-config.md
**Status:** complete
**Validated:** no
**Problems-only:** yes (passing checks are omitted per phase output mode)

## Runtime Verification Records

| Step | Command | Result |
|------|---------|--------|
| R1 | Instantiate `Settings` with valid/invalid/edge data | See CFG-001/CFG-002. `download_dir=""` -> opaque `path_type` ValidationError; `.env`-typo -> `extra_forbidden`; `cookie_source=FILE` -> `ValidationError` w/ clear message |
| R2 | Load sample/test config through reader | No shipped config file or `init`/scaffold command exists; config is `.env` + `VKDOWNLOADER_*` env vars only. Valid `.env` override loads (`max_retries=5`); unknown `.env` key is rejected (CFG-001) |
| R3 | `uv run ruff check src/vkdownloader/` | Passed (0 errors). `ruff format --check` flags `services/downloader.py` (pre-existing, outside config scope). `uv run mypy src/vkdownloader/` reports 1 error in `utils/correlation.py:55` (unused `type:ignore`) -- unrelated to config; `config.py`/`cli.py` are mypy-clean |
| R4 | `uv run pytest` (full suite; focus: tests/test_config.py + tests/test_cli.py) | 325 passed (full suite); config+CLI focus: 40 passed |

> Note: `.gitignore:28` ignores `.env`; no `.env` or example template is committed, so there is no secret-leakage surface to report in this phase (template/secret checks pass -> omitted).

---

## Findings

### CFG-001: `.env`-file unknown-variable typos raise an opaque ValidationError and bypass the documented typo guard

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION, BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/cli.py`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** The `Settings` model sets `extra='forbid'` and ships `warn_unknown_env_vars()` to catch `VKDOWNLOADER_*` typos before construction. The docstrings (`config.py:19-26`, `config.py:179-183`) and `configuration.md` ("Environment Variable Caveats", `configuration.md:171-175`) state that misspelled `VKDOWNLOADER_*` variables are "silently ignored / silently dropped and the default is used," with the warning helper as the detection path. This is accurate ONLY for **OS environment variables**. For the `.env` **file**, `extra='forbid'` actually REJECTS unknown keys -- `Settings()` raises a hard `ValidationError` -- and `warn_unknown_env_vars()` cannot see `.env` content at all (it scans `os.environ` only, `config.py:193`). Since `.env` is the documented primary configuration method (`installation.md:104`), a single typo yields a dead-end error with no list of valid names and no remediation hint.

**Evidence:** Runtime (R1), run in a temp CWD with a `.env` file:

- OS-env typo -- `VKDOWNLOADER_MAXRETRIES=9` set in `os.environ`: `Settings()` succeeds, `max_retries == 3` (default silently used); `warn_unknown_env_vars()` returns `['VKDOWNLOADER_MAXRETRIES']` and logs a `valid_vars` hint. Behavior matches the docs.
- `.env` typo -- `.env` containing only `VKDOWNLOADER_MAXRETRIES=9`: `os.environ` before load is `[]`; `warn_unknown_env_vars()` returns `[]`; `Settings()` raises:
  `ValidationError: vkdownloader_maxretries -> Extra inputs are not permitted [type=extra_forbidden] input=9`
- `.env` valid override -- `.env` containing `VKDOWNLOADER_MAX_RETRIES=5`: `Settings().max_retries == 5` (proves `.env` IS loaded; the failure is the unknown key, not loading itself).
- Doc/code contradiction: `config.py:19-26` / `config.py:179-183` / `configuration.md:171-175` all claim misspellings are "silently dropped, default used, warnable," but runtime shows `.env` typos are rejected outright and are unreachable by the warning helper.
- Aggravator: `cli.py:47-67` `_format_validation_error` labels every field as `Received: <redacted>`, and `model_config` sets `hide_input_in_errors=True`, so the CLI-facing message hides the offending value entirely.

**Recommendation:** Two complementary, advisory changes:
1. Make the pre-construction typo guard cover the `.env` file: parse the resolved `.env` (same `ConfigParser`-free key=value semantics pydantic-settings uses), strip the `VKDOWNLOADER_` prefix, and compare against `_build_valid_env_vars()` so the existing `valid_vars` hint also fires for `.env` typos. It is already invoked before construction in `cli.py:481`/`590`.
2. Improve the `extra_forbidden` UX: on an extra-field error, surface the valid `VKDOWNLOADER_*` names (reuse `_build_valid_env_vars()`) and a nearest-match "did you mean" hint instead of the bare pydantic message.
3. Correct the docs (`config.py:19-26`, `config.py:179-183`, `configuration.md:171-175`) to state the true behavior: unknown OS-env vars are silently ignored (with warning); unknown `.env` keys raise `ValidationError`; advise users to inspect the `.env` file for typos.

Effort: medium. Priority: recommended.

---

### CFG-002: Empty-string `download_dir` raises an opaque `path_type` ValidationError (asymmetric with `log_file`)

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE, SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** The `empty_string_to_none` validator (`config.py:112-117`) converts `""` -> `None` for BOTH `download_dir` and `log_file`. This is correct for `log_file` (typed `Path | None`, so `None` is valid). But `download_dir` is typed `Path` (non-optional), so `None` is not a valid path and the subsequent `path_type` coercion fails with an opaque message. The two path fields therefore handle an empty string asymmetrically: `log_file` degrades gracefully to "no file logging"; `download_dir` hard-fails. The inline comment at `config.py:126-127` even misnames the field ("see CFG-001 ... when `LOG_FILE` is an empty string") -- in reality `LOG_FILE=""` succeeds while `DOWNLOAD_DIR=""` is what crashes.

**Evidence:** Runtime (R1):
- `Settings(download_dir="")` -> `ValidationError: download_dir -> Input is not a valid path for <class 'pathlib.Path'> [type=path_type] input=None` (input hidden by `hide_input_in_errors=True`).
- `Settings(log_file="")` -> `log_file=None`, no error (type `NoneType`).
- Same via env: `VKDOWNLOADER_DOWNLOAD_DIR=""` -> identical `path_type` ValidationError.
- CLI-facing message (via `CliRunner`, `download` command with `VKDOWNLOADER_DOWNLOAD_DIR=""`): exit code `1`, output:
  `"Configuration error: one or more settings have invalid values.\nCheck your .env file or VKDOWNLOADER_* environment variables:\n  - download_dir: Input is not a valid path for <class 'pathlib.Path'>\n    Received: <redacted>\nFix the offending value(s) and try again."`

**Impact:** A user who clears `VKDOWNLOADER_DOWNLOAD_DIR` (e.g. `VKDOWNLOADER_DOWNLOAD_DIR=` in `.env`, intending "use default") gets an opaque, redacted error pointing at `download_dir` with no indication that the value was the empty string. The natural expectation -- empty means "use default", consistent with how `log_file=""` already behaves -- is not met.

**Recommendation:** Unify empty-string handling for path fields and fix the misleading comment. Either:
- (preferred) Treat `""` for `download_dir` as "use default" by mapping it to `Settings.model_fields["download_dir"].default` in the existing `empty_string_to_none`/path validator (mirrors `log_file`'s graceful `None`), optionally logging a debug note; OR
- raise an explicit, actionable error that names the variable (`VKDOWNLOADER_DOWNLOAD_DIR`), states the empty value was supplied, and suggests removing the line to use the default.

Either approach is strictly better than the current redacted `path_type` error. Also correct the inline comment at `config.py:126-127` to reference `download_dir`, not `LOG_FILE`.

Effort: trivial. Priority: recommended.

---

### CFG-003: Docs misstate the exception for `CookieSource.FILE` and are internally inconsistent

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE, SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `docs/01-tools/vkdownloader-overview.md`, `docs/01-tools/api-reference.md` |
| **Classification** | advisory |

**Description:** `config.py:145-157` `validate_cookie_source` raises `ValueError("CookieSource.FILE is not implemented...")` inside a pydantic field_validator, which pydantic surfaces as a `ValidationError` at construction. Two docs instead claim `NotImplementedError` is raised, and one of them (api-reference.md) contradicts ITS OWN enum table.

**Evidence:**
- Code: `config.py:145-157` raises `ValueError`; runtime (R1) / `test_config.py:96-104` confirm `Settings(cookie_source=CookieSource.FILE)` -> `ValidationError`, loc `('cookie_source',)`, msg `"CookieSource.FILE is not implemented. Use 'none' or 'browser' instead."`
- `docs/01-tools/vkdownloader-overview.md:63`: "`file` is not implemented and raises `NotImplementedError`"
- `docs/01-tools/api-reference.md:99`: "When `cookie_source=FILE`: Raises `NotImplementedError` (not implemented)"
- `docs/01-tools/api-reference.md:656` (same doc, its own CookieSource table): "`FILE` ... **Rejected with ValueError**. Not implemented" -- i.e. api-reference.md contradicts itself.

**Recommendation:** Update `overview.md:63` and `api-reference.md:99` to state that `CookieSource.FILE` is rejected at construction with a `ValidationError` (backed by `ValueError` in `validate_cookie_source`), matching `api-reference.md:656`. Keep `file` in the `CookieSource` enum (it documents intent and the validator message) but ensure all references agree on the exception type.

Effort: trivial. Priority: recommended.

---

### CFG-004: `configuration.md` implies `--max-retries` is available for the single `download` command, but it is batch-only

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE, SPEC-DEVIATION |
| **Affected Modules** | `docs/11-guides/configuration.md`, `src/vkdownloader/cli.py`, `docs/99-reference/cli-reference.md` |
| **Classification** | advisory |

**Description:** `configuration.md` documents `max_retries` with a `CLI Flag: --max-retries / -r` and text "Applies to single downloads as well as batch downloads," without qualifying that the flag is batch-only. The single `download` command exposes no `--max-retries` option, so a user following the guide and running `vkdownloader download URL --max-retries 5` hits a Typer "no such option" error. (The `max_retries` *setting* does apply to single downloads via the `VKDOWNLOADER_MAX_RETRIES` env var -- only the CLI flag is batch-scoped.)

**Evidence:**
- `src/vkdownloader/cli.py`: `download()` (`cli.py:418-445`) options are `url, quality, output, method, cookie_source, ssl_verify` -- no `--max-retries`. Only `batch_download()` (`cli.py:542-581`, option at `cli.py:576-581`) defines `--max-retries / -r`.
- `docs/11-guides/configuration.md:105-117`: lists `CLI Flag: --max-retries / -r` and "Applies to single downloads as well as batch downloads."
- `docs/99-reference/cli-reference.md:121` correctly scopes `--max-retries` to the `batch` command only.

**Recommendation:** Clarify in `configuration.md` that `--max-retries` is a batch-only CLI flag and that single-download retry behavior is configured via the `VKDOWNLOADER_MAX_RETRIES` environment variable. Optionally consider whether the single `download` command should gain a `--max-retries` override for parity (design decision, not mandated).

Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 2 |

## Mandatory Fixes

_No findings classified as mandatory. All findings fail fast (no data loss / no silent insecure config): CFG-001's `.env` typo does raise (not silently misconfigure), and CFG-002's empty `download_dir` raises a `ValidationError` (caught and surfaced by the CLI)._

## Advisory Recommendations

- **CFG-001 (HIGH):** Extend the typo guard (`warn_unknown_env_vars`) to also scan the resolved `.env` file, and improve the `extra_forbidden` message to list valid `VKDOWNLOADER_*` names / suggest nearest match; correct docs to reflect that `.env` typos raise (not silently-ignored). [SUPPORTS] operational reliability of the primary config path.
- **CFG-002 (MEDIUM):** Make empty-string handling consistent across path fields (treat `download_dir=""` as "use default", as `log_file=""` already degrades gracefully); fix the `config.py:126-127` comment that misnames the crashing field. [BEST-PRACTICE] config robustness / UX.
- **CFG-004 (LOW):** Document that `--max-retries` is batch-only and that single-download retries use `VKDOWNLOADER_MAX_RETRIES`. [DOC-UPDATE] clarity.

## Doc Updates Needed

- **CFG-001:** `config.py` docstring (lines 19-26, 179-183) and `docs/11-guides/configuration.md` ("Environment Variable Caveats", 171-175) -- state the true `.env` vs OS-env-var behavior.
- **CFG-003:** `docs/01-tools/vkdownloader-overview.md:63` and `docs/01-tools/api-reference.md:99` -- `CookieSource.FILE` raises `ValidationError` (not `NotImplementedError`); align with `api-reference.md:656`.
- **CFG-004:** `docs/11-guides/configuration.md:105-117` -- scope `--max-retries` to the `batch` command.
