---
name: CLI Audit Findings - Validated
description: Phase 01 Audit — CLI Entry Point & Command Layer (Validated)
agent: validator
alwaysApply: false
---

# Phase 01 Audit Findings — CLI Entry Point & Command Layer (Validated)

**Executor:** validator  
**Source:** `.ai/audit/01-cli/findings.md`  
**Base:** Phase 01 Audit  
**Status:** complete  
**Validated:** yes

---

## Findings

### CLI-001: Missing Exception Handling in download Command

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src\vkdownloader\cli.py |
| **Classification** | mandatory |

**Description:** The `download` command does not wrap the `asyncio.run(_download())` call in a try-except block. When an exception occurs (e.g., invalid URL format), the full Python traceback is exposed to the user instead of a user-friendly error message. This violates the requirement for consistent error handling where "No raw tracebacks leak to the user."

**Evidence:** Verified by running `uv run vkdownloader download "invalid-url"` which produces a full traceback ending with:
```
src\vkdownloader\cli.py:61 in download
    result = asyncio.run(_download())
...
ValueError: Invalid VK video URL: invalid-url
```
The command at lines 22-67 in cli.py has no exception catching around the async execution.

**Recommendation:** Wrap the async download execution in a try-except block and present user-friendly error messages. Catch specific exceptions like `ValueError` from URL parsing and provide actionable guidance (e.g., "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}").

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Empirical testing confirms the exception is raised and traceback exposed to user. The code at line 61 calls `asyncio.run(_download())` without any try-except wrapper.

---

### CLI-002: Missing KeyboardInterrupt Handling

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src\vkdownloader\cli.py |
| **Classification** | advisory |

**Description:** Neither `download` nor `batch_download` commands handle `KeyboardInterrupt` gracefully. Long-running download operations (including batch downloads) will display raw stack traces when the user presses Ctrl+C, violating the user experience requirement for "Graceful interruption — KeyboardInterrupt is caught and handled cleanly without stack traces."

**Evidence:** No `try-except KeyboardInterrupt` blocks exist in cli.py. The `download` command at lines 22-67 and `batch_download` at lines 70-161 have no interruption handling. Note: `batch_download` does have exception handling inside `_download_single` (line 130) but not for the outer command.

**Recommendation:** Add KeyboardInterrupt handling to both commands to print a clean message like "Download cancelled" and exit with code 0 or 130 (standard for SIGINT).

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Code inspection confirms no KeyboardInterrupt handling in either command. Long-running downloads would expose stack traces on user interruption.

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
- No SPEC.md exists to override this documentation
- Running `uv run vkdownloader --help` confirms actual commands

**Recommendation:** Remove `docs/99-reference/cli-reference.md` or rewrite it for vkdownloader CLI. The current document is from a different project (mko-telebot) and provides misleading information.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Documentation is from a different project entirely. pyproject.toml entry point and CLI help output confirm vkdownloader is the correct application name.

---

### CLI-004: Duplicate Entry Point in main.py

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | main.py, src\vkdownloader\cli.py |
| **Classification** | mandatory |

**Description:** There are two separate entry points: `main.py` (root-level, argument-parsing based on `sys.argv`) and `src\vkdownloader\cli.py` (Typer-based). The `main.py` duplicates business logic already in the service layer and uses `print()` statements (violating project rule #12) for user output. While the pyproject.toml entry point references the Typer CLI, main.py is still documented and used for specific workarounds.

**Evidence:**
- pyproject.toml line 40: `vkdownloader = "vkdownloader.cli:cli"` (Typer CLI is the installed entry point)
- main.py lines 203-236 implements `main()` function with manual `sys.argv` parsing
- main.py uses `print()` statements (violating project rule #12) at lines 49, 52, 137, 155, 206, 207, 208, 209, 217, 218, 226, 227, 233, 235, 235
- docs/11-guides/vkdownloader-limitations.md references main.py for recommended workarounds (lines 92, 101)

**Recommendation:** Remove `main.py` entirely and consolidate into the registered Typer CLI (`cli.py`). Add `--method` option using the `DownloadMethod` enum to preserve the yt-dlp/ffmpeg/auto selection capability. Port `download_with_ytdlp_with_resume_fallback()` into the downloader service layer. Update `docs/11-guides/vkdownloader-limitations.md` to use `vkdownloader download --method ffmpeg URL` syntax. This eliminates the duplicate entry point while preserving documented workaround functionality. Effort: medium. Priority: mandatory (removes SPEC-DEVIATION and rule #12 violation).

> **Validation Note:**
> - **Action:** Reclassified
> - **Original Type:** BEST-PRACTICE
> - **New Type:** SPEC-DEVIATION
> - **Detail:** The `print()` statements violate project rule #12. While main.py is documented for workarounds, it needs to comply with project coding standards.

---

### CLI-005: Missing Type Annotations in Service Functions

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src\vkdownloader\services\downloader.py |
| **Classification** | mandatory |

**Description:** Several helper functions in the downloader service lack proper type annotations, which violates the project's mypy strict mode configuration and reduces code maintainability.

**Evidence:**
- mypy output confirmed:
  - `download_hls_with_resume` (line 71): Missing type annotation for `extractor` parameter
  - `_fetch_playlist_with_retry` (line 148): Missing type annotation for `extractor` parameter
  - `_download_segment` (line 188): Missing type arguments for generic type "dict" (headers parameter)
  - `_load_downloaded_count` (line 296): Returning `Any` from function declared to return `int` (no explicit return type)
  - `browser.py` line 13: `create_stealth_context` is missing `async` keyword for function calling coroutine
  - `extractor.py` line 168: Argument type mismatch for `_format_cookies_for_ffmpeg` (list[Cookie] vs list[dict])
  - `extractor.py` line 186: Missing type arguments for generic type "dict"

**Recommendation:** Add proper type annotations to these functions. Use `VKVideoExtractor | None` for the extractor parameter and `dict[str, str]` for headers. This aligns with project rule #9 (Type Safety Everywhere).

> **Validation Note:**
> - **Action:** Reclassified
> - **Original Type:** BEST-PRACTICE
> - **New Type:** SPEC-DEVIATION
> - **Detail:** The project enforces strict mypy configuration (strict = true, disallow_untyped_defs = true). These are violations, not suggestions.

---

### CLI-006: Unused Import and Variable in extractor.py

| Field | Value |
|-------|-------|
| **ID** | CLI-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src\vkdownloader\services\extractor.py |
| **Classification** | mandatory |

**Description:** The `typing.Any` import on line 5 is unused, and the `domain` variable on line 192 is assigned but never used, creating noise in the codebase. These violate project coding standards.

**Evidence:**
- extractor.py line 5: `from typing import Any` — ruff confirms unused, no usages found in the file
- extractor.py line 192: `domain = cookie.get("domain", "")` — variable never referenced again in `_format_cookies_for_ffmpeg` method
- ruff confirms both violations

**Recommendation:** Remove the unused import and remove the unused domain variable.

> **Validation Note:**
> - **Action:** Reclassified
> - **Original Type:** BEST-PRACTICE
> - **New Type:** SPEC-DEVIATION
> - **Detail:** These are code quality violations, not best practice suggestions. Unused code violates the "avoid low-value complexity" principle in the project rules.

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
- CLI-004: Duplicate Entry Point in main.py (print() statements violate project rules)
- CLI-005: Missing Type Annotations in Service Functions (violates mypy strict config)
- CLI-006: Unused Import and Variable in extractor.py (code quality violation)

## Advisory Recommendations

- CLI-002: Missing KeyboardInterrupt Handling

## Runtime Verification Results

- **Step R1 — Import Verification:** Passed - CLI module imports successfully
- **Step R2 — CLI Help Verification:** Passed - Both `download` and `batch` commands produce help output without errors
- **Step R3 — Linter and Type Checker:** 
  - ruff check: Failed - 5 errors confirmed in downloader.py and extractor.py
  - mypy: Failed - 8 type annotation errors confirmed across downloader.py, browser.py, and extractor.py
- **Step R4 — Run Test Suite:** Passed - 53 tests passed
- **Step R5 — Exception Handling Test:** Verified - Full traceback exposed on invalid URL

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | CLI-001, CLI-002, CLI-003 |
| Reclassified | 3 | CLI-004 (BEST-PRACTICE → SPEC-DEVIATION), CLI-005 (BEST-PRACTICE → SPEC-DEVIATION), CLI-006 (BEST-PRACTICE → SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | No findings rejected. All findings have valid evidence. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | No findings merged. Each issue has distinct root cause. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CLI-004 | BEST-PRACTICE | SPEC-DEVIATION | The `print()` statements violate project rule #12 (No print() statements). This is a code standard violation, not an optional improvement. |
| CLI-005 | BEST-PRACTICE | SPEC-DEVIATION | The project enforces strict mypy configuration. Missing type annotations are violations, not suggestions. |
| CLI-006 | BEST-PRACTICE | SPEC-DEVIATION | Unused imports and variables are code quality violations that add noise without value. |

## Warnings

- **Architectural Risk:** Two conflicting entry points could confuse developers about which CLI to maintain.
- **Documentation Risk:** cli-reference.md is completely misaligned with the actual application, potentially misleading users.
- **Type Safety Risk:** mypy strict mode failures indicate the codebase may be harder to maintain and refactor safely.