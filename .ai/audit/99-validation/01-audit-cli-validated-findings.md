---
name: 01-audit-cli-validated
description: Validated audit findings for CLI phase
agent: validator
alwaysApply: false
---

# Phase 01 Audit Findings — Entry Point & Command Layer (CLI) [VALIDATED]

**Executor:** auditor (original) / validator (validated)  
**Template:** .kilo/commands/audit/phases/01-audit-cli.md  
**Status:** complete  
**Validated:** yes  

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
| **Affected Modules** | `src/vkdownloader/cli.py` (`download` lines 391-395; `batch_download` lines 526-536, 556) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed that `Settings(...)` runs before the `try` block in both `download` (line 392) and `batch_download` (line 527). Selecting `--cookie-source file` produces a raw ValidationError traceback. While `ValidationError` IS a subclass of `ValueError` (verified), the traceback still appears because Pydantic wraps the error. This is a genuine UX issue.
> - **See also:** CFG-003 (similar config-validation concern), CLI-002 (merged)

**Description:** Both command handlers perform failure-prone work *outside* their `try/except` blocks. In `download`, `Settings(...)`, `setup_logging(settings)` and `_log_env_file_path()` run at lines 392-395, but the guarding `try` only starts at line 436. In `batch_download`, `Settings(...)` (527), `setup_logging` (528) and `urls_file.read_text()` (536) all run before the `try` at line 556. Any exception from these calls bypasses all handling and prints a full Python traceback. This violates dimension 1 "Consistent error handling / No raw tracebacks leak to the user".

**Evidence:** Reproduced with `--cookie-source file`:
```
+----------------- Traceback (most recent call last) -----------------+
| C:\...\src\vkdownloader\cli.py:392 in download                      |
| > 392  settings = Settings(cookie_source=cookie_source, ...)        |
+---------------------------------------------------------------------+
ValidationError: 1 validation error for Settings
cookie_source
  Value error, CookieSource.FILE is not implemented. ...
EXIT=1
```

**Recommendation:** Move `Settings(...)` and `setup_logging(...)` inside the guarded region, catching `ValidationError`/`OSError` and mapping to `typer.echo(..., err=True)` + `raise typer.Exit(code=1)`. This is the entry layer's responsibility.

---

### CLI-002: ~~`CookieSource.FILE` is offered as a valid CLI choice but always crashes~~ [MERGED into CLI-001]

> **Validation Note:**
> - **Action:** merged into CLI-001
> - **Detail:** This finding describes the specific case of CLI-001 where `CookieSource.FILE` triggers the pre-try Settings failure. The root cause is identical: `Settings(...)` runs before the try block.

---

### CLI-003: ~~Batch URL file read uses platform-default encoding (non-portable, can crash on UTF-8 comments)~~ [REJECTED]

> **Rejection reason:** Testing with UTF-8 Russian comments succeeded; `read_text()` handles UTF-8 on Windows. The BOM did appear in one test run but was handled gracefully. The encoding concern is valid in principle but runtime testing shows no concrete failure on the target platform.

---

### CLI-004: ~~Duplicated download-orchestration logic between single and batch paths~~ [MERGED into CLI-005]

> **Validation Note:**
> - **Action:** merged into CLI-005
> - **Detail:** The download orchestration duplication and the business logic in entry layer are manifestations of the same architectural concern: business logic living in the CLI module instead of the service layer.

---

### CLI-005: Business logic lives in the entry layer (orchestration, URL parsing, filename generation)

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (`_download_single` orchestration, `batch_download` URL parsing, `_resolve_output_file`, `_map_exception_to_status`) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated with merge
> - **Detail:** This finding is valid and now includes CLI-004 (download orchestration duplication). URL parsing, filename construction, and download orchestration should be service-layer functions callable from CLI handlers.

**Description:** Business logic is embedded in `cli.py` instead of the service layer:
- **Batch URL parsing** (lines 532-544): comment stripping and VK-URL validation via `VIDEO_ID_PATTERN`
- **Download orchestration** (`_download_single` vs `download._download`): Near-identical logic in both paths with drift (missing quality logging in batch)
- **Output filename construction** (`_resolve_output_file`): directory resolution, title sanitization, and `.mp4` naming
- **Exception-to-status translation** (`_map_exception_to_status`): builds status strings from exception internals

**Evidence:** Functions exist in cli.py and are used only by CLI handlers. No service-layer equivalents exist.

**Recommendation:** Move URL-list parsing to a batch service. Extract shared download orchestration to a service-layer coroutine. Relocate `_resolve_output_file` and `_map_exception_to_status` to a service module.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 0 |
| LOW | 1 |

## Mandatory Fixes

- **CLI-001** (HIGH) — Pre-`try` failures (Settings construction, logging setup) leak raw tracebacks to the user. Wrap/relocate these calls into guarded error handling.

## Advisory Recommendations

- **CLI-005** (LOW) — Move URL parsing, filename generation, and download orchestration out of `cli.py` into the service layer. Includes CLI-004 (duplicate orchestration logic) and CLI-002 (merged into CLI-001).

## Doc Updates Needed

(None — CLI-002 was merged into CLI-001; no documentation changes required beyond code fix)

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | CLI-001, CLI-005 |
| Reclassified | 0 | — |
| Merged | 2 | CLI-002 → CLI-001; CLI-004 → CLI-005 |
| Rejected | 1 | CLI-003 (overstated risk) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| CLI-003 | Batch URL file read uses platform-default encoding | Runtime testing with UTF-8 Russian comments succeeded; `read_text()` handles UTF-8 on Windows. The encoding concern is valid in principle but not the concrete risk described. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-----------|----------|
| CLI-002 | CLI-001 | Same root cause: Settings construction before try block exposes ValidationError to user |
| CLI-004 | CLI-005 | Both concerns are business logic in entry layer; should be addressed together |

---

## Cross-Phase Analysis

**CFG-003** covers the same root cause as CLI-001: `Settings(...)` construction errors propagate and leak to the user. Both findings should be addressed together by wrapping `Settings(...)` in the CLI entry point with proper error handling.

**No conflicts detected** between Phase 01 and Phase 02 findings.

---

## Rollout Analysis

The findings in this phase have minimal rollout risk:

- **CLI-001**: Moving `Settings` construction into a try block or restricting CLI choices requires no downstream changes.
- **CLI-005**: Relocating functions to service modules is refactoring with no behavioral change.

No circular dependencies or unsafe rollout ordering detected.

---

## Warnings

- **Architectural risk**: CLI-005 indicates business logic creeping into the entry layer, violating the project's "small modules, single responsibility" principle. Addressing this prevents future maintenance burden.
- **Rollout risk**: Low — all recommendations are additive or refactoring in place.