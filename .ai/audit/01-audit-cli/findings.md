---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 01 Audit Findings — Entry Point & Command Layer (CLI)

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/01-audit-cli.md
**Status:** complete
**Validated:** no

**Output mode:** `problems-only: true` — only problems are documented.

## Runtime Verification Summary (evidence baseline)

| Step | Command | Result |
|------|---------|--------|
| R1 Import | `uv run python -c "import vkdownloader.cli"` | OK (no import/dependency errors) |
| R2 Help | `uv run vkdownloader --help` / `download --help` / `batch --help` | Exit 0, all commands & options enumerated |
| R3 Lint | `uv run ruff check src/vkdownloader/cli.py` | `All checks passed!` (exit 0) |
| R3 Format | `uv run ruff format --check src/vkdownloader/cli.py` | `1 file already formatted` (exit 0) |
| R3 Types | `uv run mypy src/vkdownloader/cli.py` | `Success: no issues found` (exit 0) |
| R4 Tests | `uv run pytest tests/test_cli.py -q` | `19 passed` (exit 0) |

> R1–R4 pass. The findings below come from behavior exercised at runtime and code inspection of paths **not** covered by the passing tests (all CLI tests mock `vkdownloader.cli.Settings`, so the real settings-construction and file-read paths are never exercised).

---

## Findings

### CLI-001: Raw traceback leaks to user for pre-`try` failures (Settings construction, logging setup, batch file read)

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py` (`download` lines 391-395, 436; `batch_download` lines 526-536, 556) |
| **Classification** | mandatory |

**Description:** Both command handlers perform failure-prone work *outside* their `try/except` blocks. In `download`, `Settings(...)`, `setup_logging(settings)` and `_log_env_file_path()` run at lines 392-395, but the guarding `try` only starts at line 436. In `batch_download`, `Settings(...)` (527), `setup_logging` (528) and `urls_file.read_text()` (536) all run before the `try` at line 556. Any exception from these calls (invalid config value, `OSError` creating the log-file directory, `UnicodeDecodeError`/`OSError` reading the URL file) bypasses all handling and prints a full Python traceback. This violates dimension 1 "Consistent error handling / No raw tracebacks leak to the user".

**Evidence:** Reproduced with a value that fails `Settings` validation:
```
$ uv run vkdownloader download "https://vkvideo.ru/video-1_1" --cookie-source file
+----------------- Traceback (most recent call last) -----------------+
| C:\...\src\vkdownloader\cli.py:392 in download                      |
| > 392  settings = Settings(cookie_source=cookie_source, ...)        |
| C:\...\pydantic_settings\main.py:247 in __init__ ...                |
+---------------------------------------------------------------------+
ValidationError: 1 validation error for Settings
cookie_source
  Value error, CookieSource.FILE is not implemented. ...
EXIT=1
```
The 130-char stack trace is shown to the end user instead of a one-line message. Note `pydantic.ValidationError` is not a subclass of `ValueError`, so even the existing `except ValueError` (line 445) would not catch it — but it is unreachable anyway because construction is outside the `try`.

**Recommendation:** Move `Settings(...)`, `setup_logging(...)`, and `urls_file.read_text()` inside the guarded region (or wrap them in a dedicated `try` that maps `ValidationError`/`OSError`/`UnicodeDecodeError` to a concise `typer.echo(..., err=True)` + `raise typer.Exit(code=1)`). This is the entry layer's responsibility: no downstream/config exception should reach the terminal as a traceback.

---

### CLI-002: `CookieSource.FILE` is offered as a valid CLI choice but always crashes

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py` (`--cookie-source` options, lines 374-379 & 503-508), `src/vkdownloader/models/enums.py` (line 50), `src/vkdownloader/config.py` (lines 124-136) |
| **Classification** | mandatory |

**Description:** The `--cookie-source` option is typed as the full `CookieSource` enum, so `file` is advertised as a selectable value in `--help` (`[none|browser|file]`) and passes Typer's enum validation. However `Settings.validate_cookie_source` unconditionally raises `ValueError` for `file`. The result is that the CLI presents an option it can never honor, and selecting it produces the CLI-001 traceback rather than a clean rejection. Dimension 1 "Input validation: invalid options rejected with clear error messages, not silent defaults / crashes" is violated: the value is accepted at the parser layer and only rejected via an uncaught deep-stack error.

**Evidence:** `uv run vkdownloader download --help` renders `--cookie-source ... [none|browser|file]` with help text "none or browser (file not implemented)". Runtime invocation with `--cookie-source file` crashes (see CLI-001 evidence). No test covers this path (all `test_cli.py` cases patch `Settings`).

**Recommendation:** Make the exposed choice match reality. Either (a) restrict the CLI option to the implemented subset (e.g. a two-value enum or `click.Choice(["none","browser"])`) so `file` is rejected by Typer with a standard "invalid value" message, or (b) if `file` must remain in the domain enum for future use, catch the validation error at the handler boundary and print an actionable message. Preferred: option (a) — do not surface unimplemented choices in help.

### CLI-003: Batch URL file read uses platform-default encoding (non-portable, can crash on UTF-8 comments)

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (`batch_download`, line 536) |
| **Classification** | advisory |

**Description:** `urls_file.read_text()` is called with no `encoding=` argument, so it decodes using `locale.getpreferredencoding(False)`. On the project's stated target (Windows) this is typically `cp1252`, not UTF-8. A URL list authored in UTF-8 that contains non-ASCII characters — e.g. a Russian-language comment line (`# описание`), which is plausible for a ru-RU-focused tool — will either be mis-decoded or raise `UnicodeDecodeError`. Because the read is outside the `try` (see CLI-001), a decode failure surfaces as a raw traceback. Behavior also differs across machines/locales, undermining reproducibility.

**Evidence:** Line 536: `for line in urls_file.read_text().splitlines():` — no encoding specified. `Settings` targets a Windows/ru-RU environment (`locale="ru-RU"`, `timezone="Europe/Moscow"` in `config.py`), making non-ASCII batch files a realistic input. Existing batch tests only write pure-ASCII content (`test_cli.py` lines 119, 133, 147, 161, 211, 251), so this path is untested.

**Recommendation:** Read with an explicit `encoding="utf-8"` (optionally `errors="replace"` or `utf-8-sig` to tolerate a BOM), and handle `OSError`/`UnicodeDecodeError` at the handler boundary with a concise error message. This makes batch input deterministic across platforms.

---

### CLI-004: Duplicated download-orchestration logic between single and batch paths (already diverged)

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (`_download_single` lines 140-218; `download._download` lines 397-434) |
| **Classification** | advisory |

**Description:** The core "extract streams -> guard empty streams -> select quality -> resolve output file -> perform_download" sequence is implemented twice: once in `_download_single` (batch) and once in the nested `_download()` inside the `download` command. The two copies have already drifted, which is exactly the failure mode duplication causes:
- The single path logs `available_streams` / `available_qualities` (lines 414-416); the batch path does not, so batch runs give the user no visibility into what qualities existed.
- Error handling differs: the single path raises typed exceptions to the outer handler; the batch path maps them to status strings via `_map_exception_to_status`.
Any future change to the extraction/selection flow must be made in both places or they diverge further. This is orchestration logic living in the entry layer that should be a single shared service function.

**Evidence:** Compare lines 173-201 (`_download_single`) with lines 402-431 (`download._download`) — near-identical bodies differing only in logging and context/semaphore handling. The divergence in quality-logging is observable at runtime (batch summary output contains no available-quality info).

**Recommendation:** Extract one shared coroutine (e.g. `download_one(url, quality, method, settings, ctx) -> result`) in the service layer that both commands call. The CLI handlers then only parse args, invoke the service, and present results/errors. This removes drift risk and thins the handlers per dimension 1.

---

### CLI-005: Business logic (URL parsing/filtering, filename generation, error->status mapping) lives in the entry layer

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (`batch_download` lines 532-544; `_resolve_output_file` lines 87-116; `_map_exception_to_status` lines 119-137) |
| **Classification** | advisory |

**Description:** Dimension 1/2 require the entry layer to contain only parsing, delegation, and presentation. Several pieces of domain logic are instead embedded in `cli.py`:
- **Batch URL parsing/filtering** (lines 532-544): comment/blank stripping and VK-URL validation via `VIDEO_ID_PATTERN.search` is domain input processing performed inline in the handler.
- **Output filename construction** (`_resolve_output_file`): directory resolution, title sanitization, and `.mp4` naming policy are business rules living in the entry module.
- **Exception-to-status translation** (`_map_exception_to_status`): builds user/domain status semantics from exception internals.

None of these are covered by service-layer tests because they are CLI-local; they also cannot be reused by any non-CLI caller.

**Evidence:** `batch_download` imports and uses `VIDEO_ID_PATTERN` from the extractor (line 23, used line 540) to filter inputs; `_resolve_output_file` (lines 104-114) implements naming policy; `_map_exception_to_status` (lines 128-137) encodes domain status strings — all inside `cli.py`.

**Recommendation:** Move URL-list parsing/validation into a service helper (e.g. `load_batch_urls(path) -> (valid, skipped)`), and consider relocating filename policy to the download/service layer. Keep handlers limited to parse -> call service -> present. Advisory; low risk for current size, but it improves testability and reuse.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 1 |

## Mandatory Fixes

- **CLI-001** (HIGH) — Pre-`try` failures (Settings construction, logging setup, batch file read) leak raw tracebacks to the user. Wrap/relocate these calls into guarded error handling.
- **CLI-002** (MEDIUM) — `--cookie-source file` is advertised as a valid choice but always crashes; restrict the exposed CLI choices to implemented values (or reject cleanly).

## Advisory Recommendations

- **CLI-003** (MEDIUM) — Read the batch URL file with explicit `encoding="utf-8"` and handle decode/OS errors; current platform-default decoding is non-portable.
- **CLI-004** (MEDIUM) — Deduplicate the single/batch download orchestration into one shared service coroutine; the two copies have already diverged (missing available-quality logging in batch).
- **CLI-005** (LOW) — Move URL parsing/filtering, filename generation, and exception->status mapping out of `cli.py` into the service layer.

## Doc Updates Needed

- The `--cookie-source` help text and `config.py` docstrings acknowledge "file not implemented", yet the value remains selectable. If CLI-002 is fixed by removing `file` from the exposed choices, the "(file not implemented)" note in the option help (cli.py lines 378, 507) and the `cookie_source` field description (`config.py` line 97) become obsolete and should be updated.

---

## Notes / Non-findings (context only, not counted)

- No reverse imports found: a search for imports of `vkdownloader.cli` inside `src/` returned nothing — layer-boundary import direction (dimension 2) is clean.
- Async bridging via `asyncio.run` and signal-handler setup/cleanup inside the async context is structurally sound; no nested-loop or double-run issues observed in code. (Windows `add_signal_handler` NotImplementedError fallback to `signal.signal` exists in `services/signal_handlers.py`; deeper runtime interruption behavior belongs to the services phase.)
- Exit codes are meaningful (0 success, 1 failure, 130 on interrupt) — no finding.
