---
name: CLI Audit Findings
description: Phase 01 Audit — CLI Entry Point & Command Layer
agent: auditor
alwaysApply: false
---

# Phase 01 Audit Findings — CLI Entry Point & Command Layer

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### CLI-001: Missing Exception Handling in download Command

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src\vkdownloader\cli.py |
| **Classification** | mandatory |

**Description:** The `download` command does not wrap the `asyncio.run(_download())` call in a try-except block. When an exception occurs (e.g., invalid URL format), the full Python traceback is exposed to the user instead of a user-friendly error message. This violates the requirement for consistent error handling where "No raw tracebacks leak to the user."

**Evidence:** Running `uv run vkdownloader download "invalid-url"` produces full traceback ending with:
```
src\vkdownloader\cli.py:61 in download
    result = asyncio.run(_download())
...
ValueError: Invalid VK video URL: invalid-url
```
The command at lines 22-67 in cli.py has no exception catching around the async execution.

**Recommendation:** Wrap the async download execution in a try-except block and present user-friendly error messages. Catch specific exceptions like `ValueError` from URL parsing and provide actionable guidance (e.g., "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}").

---

### CLI-002: Missing KeyboardInterrupt Handling

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src\vkdownloader\cli.py |
| **Classification** | advisory |

**Description:** Neither `download` nor `batch_download` commands handle `KeyboardInterrupt` gracefully. Long-running download operations (including batch downloads) will display raw stack traces when the user presses Ctrl+C, violating the user experience requirement for "Graceful interruption — KeyboardInterrupt is caught and handled cleanly without stack traces."

**Evidence:** No `try-except KeyboardInterrupt` blocks exist in cli.py. The `download` command at lines 22-67 and `batch_download` at lines 70-160 have no interruption handling.

**Recommendation:** Add KeyboardInterrupt handling to both commands to print a clean message like "Download cancelled" and exit with code 0 or 130 (standard for SIGINT).

---

### CLI-003: Documentation Mismatch with Actual CLI

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | docs\99-reference\cli-reference.md |
| **Classification** | mandatory |

**Description:** The documented CLI reference describes a completely different application (`mko-telebot`) with commands `init`, `validate`, `run`, `config`, and `version`. The actual CLI is `vkdownloader` with commands `download` and `batch`. This misleads users about available functionality.

**Evidence:** 
- cli-reference.md documents: `mko-telebot init`, `mko-telebot validate`, `mko-telebot run`, etc.
- Actual CLI: `vkdownloader download`, `vkdownloader batch`
- pyproject.toml confirms: `vkdownloader = "vkdownloader.cli:cli"` (line 40)

**Recommendation:** Either update documentation to match the actual vkdownloader CLI, or if this is an old document from a different project, remove or clearly mark it as outdated.

---

### CLI-004: Duplicate Entry Point in main.py

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | main.py, src\vkdownloader\cli.py |
| **Classification** | advisory |

**Description:** There are two separate entry points: `main.py` (root-level, argument-parsing based on `sys.argv`) and `src\vkdownloader\cli.py` (Typer-based). The `main.py` duplicates business logic already in the service layer and provides a different CLI interface than the documented Typer CLI. The pyproject.toml entry point `vkdownloader = "vkdownloader.cli:cli"` references the Typer CLI, making `main.py` an unused or orphaned script.

**Evidence:**
- pyproject.toml line 40: `vkdownloader = "vkdownloader.cli:cli"` (Typer CLI is the installed entry point)
- main.py lines 203-236 implements `main()` function with manual `sys.argv` parsing
- Both files implement video download logic with overlapping service calls
- main.py uses `print()` statements (violating project rule #12) at lines 49, 52, 137, 155, 206-209, 217, 218, 226, 227, 233, 235

**Recommendation:** Either remove `main.py` if it's unused, or document its purpose. If both are intended to coexist, consolidate the CLI logic into a single layer with clear separation of concerns and use proper logging instead of `print()`.

---

### CLI-005: Missing Type Annotations in Service Functions

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src\vkdownloader\services\downloader.py |
| **Classification** | advisory |

**Description:** Several helper functions in the downloader service lack proper type annotations, which violates the project's mypy strict mode configuration and reduces code maintainability.

**Evidence:**
- mypy output shows 8 errors across 3 files:
  - `download_hls_with_resume` (line 77): Missing type annotation for `extractor` parameter
  - `_fetch_playlist_with_retry` (line 148): Functions missing type annotations
  - `_download_segment` (line 192): Missing type arguments for generic type "dict" (headers parameter)
  - `_load_downloaded_count` (line 301): Returning `Any` from function declared to return `int`
  - `browser.py` line 29: Incompatible return value type for `create_stealth_context` (missing `async` or `await`)
  - `extractor.py` line 168: Argument type mismatch for `_format_cookies_for_ffmpeg` (list[Cookie] vs list[dict])
  - `extractor.py` line 186: Missing type arguments for generic type "dict"

**Recommendation:** Add proper type annotations to these functions. Use `VKVideoExtractor | None` for the extractor parameter and `dict[str, str]` for headers. This aligns with project rule #9 (Type Safety Everywhere).

---

### CLI-006: Unused Import and Variable in extractor.py

| Field | Value |
|-------|-------|
| **ID** | CLI-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src\vkdownloader\services\extractor.py |
| **Classification** | advisory |

**Description:** The `typing.Any` import on line 5 is unused, and the `domain` variable on line 192 is assigned but never used, creating noise in the codebase.

**Evidence:**
- extractor.py line 5: `from typing import Any` — no usages found in the file
- extractor.py line 192: `domain = cookie.get("domain", "")` — variable never referenced again in `_format_cookies_for_ffmpeg` method

**Recommendation:** Remove the unused import and either remove or use the domain variable.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 1 |
| LOW | 2 |

## Mandatory Fixes

- CLI-001: Missing Exception Handling in download Command
- CLI-003: Documentation Mismatch with Actual CLI

## Advisory Recommendations

- CLI-002: Missing KeyboardInterrupt Handling
- CLI-004: Duplicate Entry Point in main.py
- CLI-005: Missing Type Annotations in Service Functions
- CLI-006: Unused Import and Variable in extractor.py

## Runtime Verification Results

- **Step R1 — Import Verification:** Passed - CLI module imports successfully
- **Step R2 — CLI Help Verification:** Passed - Both `download` and `batch` commands produce help output without errors
- **Step R3 — Linter and Type Checker:** 
  - ruff check: Passed for cli.py, but 6 errors found in downloader.py and extractor.py (unused import, unused variable, missing newlines, unsorted imports)
  - mypy: Failed - 8 type annotation errors across downloader.py, browser.py, and extractor.py
- **Step R4 — Run Test Suite:** Passed - 53 tests passed