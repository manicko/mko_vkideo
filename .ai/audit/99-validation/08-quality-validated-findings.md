---
name: 08-quality
description: Phase 08 Audit Findings — Code Quality, Security & Maintainability (Validated)
agent: validator
alwaysApply: false
---

# Phase 08 Audit Findings — Code Quality, Security & Maintainability (Validated)

**Executor:** validator  
**Source:** `.ai/audit/08-quality/findings.md`  
**Status:** complete  
**Validated:** yes

---

## Findings

### QLT-001: Forbidden `print()` statements in production code

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | main.py |
| **Classification** | mandatory |

**Description:** The `main.py` file uses `print()` statements for output instead of the required `logger` pattern. This violates project rule #12 which states "No `print()` Statements - Use proper logging: `logger = logging.getLogger(__name__)`". While the code uses `structlog.get_logger(__name__)`, it still outputs user-facing messages via `print()` which bypasses structured logging and makes output harder to configure and control.

**Evidence:**
- main.py:49: `print(f"Available streams: {len(streams)}")`
- main.py:52: `print(f"Qualities: {', '.join(available[:8])}")`
- main.py:137: `print(f"Download interrupted. Switching to segment-based resume ({retry_count}/{MAX_RESUME_RETRIES})...")`
- main.py:155: `print(f"Failed to download after {MAX_RESUME_RETRIES} attempts. Stopping.", file=sys.stderr)`
- main.py:206-209: Multiple print calls for usage/help output
- main.py:217-218: Print calls for validation errors
- main.py:226-227: Print calls for validation errors
- main.py:233: `print(f"Downloaded: {result}")`
- main.py:235: `print("Download failed", file=sys.stderr)`

**Recommendation:** Replace all `print()` calls with `logger.info()` or `logger.error()` calls. For CLI usage/help output, use `typer.echo()` (already imported in cli.py but unused in main.py) or `logger.info()`. This ensures consistent output handling and enables structured logging.

---

### QLT-002: Unused import `typing.Any`

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | LOW |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-006 (Phase 05), SRV-004 (Phase 03), and CFG-004 (Phase 02). All cover the same unused import `typing.Any` in extractor.py. See CFG-004 for complete analysis.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

---

### QLT-003: Unused variable `domain` in cookie formatting

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-005 (Phase 05), SRV-005 (Phase 03), and CFG-004 (Phase 02). All cover the same unused variable `domain` in `_format_cookies_for_ffmpeg` method. See CFG-004 for complete analysis.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

---

### QLT-004: Missing type annotation for generic `dict` in type hints

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | MEDIUM |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/extractor.py |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-008 (Phase 05), SRV-007 (Phase 03), and CFG-004 (Phase 02). All cover the same type annotation issues for `dict` types across multiple files. See CFG-004 for complete analysis.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

---

### QLT-005: Missing type annotation on function parameter

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | MEDIUM |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-003 (Phase 05), SRV-006 (Phase 03), and CFG-004 (Phase 02). All cover the same missing type annotations for function parameters in downloader.py. See CFG-004 for complete analysis.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

---

### QLT-006: Return type annotation returning `Any` where specific type required

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | MEDIUM |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-004 (Phase 05), SRV-008 (Phase 03), and CFG-004 (Phase 02). All cover the same `no-any-return` mypy error in `_load_downloaded_count`. See CFG-004 for complete analysis.

**Merged Into:** See CFG-004 (Phase 02) for consolidated analysis.

---

### QLT-006b: Missing `await` on async function in `create_stealth_context`

| Field | Value |
|-------|-------|
| **ID** | QLT-006b |
| **Severity** | HIGH |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/infrastructure/browser.py |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-001 (Phase 05), SRV-009 (Phase 03), CFG-005 (Phase 02), and SEC-003 (Phase 04). The same `create_stealth_context` async return type issue is documented across all phases. The function is exported in `__init__.py` and has dedicated tests in `test_browser_infrastructure.py`, but is never used by `BrowserManager` (which uses `self.browser.new_context()` instead). This represents a single root cause. The function is documented in `vkdownloader-overview.md` and represents incomplete integration, not dead code. Per validation rules: "If the spec, models, or config reference the component → reject the 'dead code' label and reclassify as SPEC-DEVIATION (missing integration, not dead code)."

**Merged Into:** See CFG-005 (Phase 02) for consolidated analysis.

---

### QLT-007: Redefinition of test class `TestHLSDownloaderDownload`

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | MEDIUM |
| **Type** | MERGED |
| **Affected Modules** | tests/test_hls_downloader.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates INT-007 (Phase 05), DF-006 (Phase 06), and TST-001 (Phase 07). All cover the same duplicate test class definition. The duplicate class `TestHLSDownloaderDownload` at lines 166-224 duplicates lines 97-164. See INT-007 for complete analysis.

**Merged Into:** See INT-007 (Phase 05) for consolidated analysis.

---

### QLT-008: Missing newlines at end of files

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | LOW |
| **Type** | MERGED |
| **Affected Modules** | main.py, src/vkdownloader/services/downloader.py, src/vkdownloader/services/extractor.py, src/vkdownloader/services/quality.py, tests/integration/__init__.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Merged
> - **Detail:** This finding duplicates SRV-010 (Phase 03) and CFG-004 (Phase 02). All cover the same trailing newline formatting issues across multiple files. See SRV-010 for complete analysis.

**Merged Into:** See SRV-010 (Phase 03) for consolidated analysis.

---

### QLT-009: Hardcoded User-Agent string duplicated in main.py

| Field | Value |
|-------|-------|
| **ID** | QLT-009 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | main.py |
| **Classification** | advisory |

**Description:** The User-Agent string is hardcoded in `main.py` (line 182) instead of using the `Settings` configuration. This duplicates the value already defined in the Settings class's `user_agent` field.

**Evidence:**
- main.py:182-183: `"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"`
- config.py:27-29: Same value defined in `Settings.user_agent`

**Recommendation:** Use `settings.user_agent` instead of hardcoding the User-Agent string, ensuring consistency with the Settings configuration.

---

### QLT-010: Unused exception classes in exception hierarchy

| Field | Value |
|-------|-------|
| **ID** | QLT-010 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/exceptions.py |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Per validation rules for "dead code findings" (Step 3): "If the spec, models, or config reference the component → reject the 'dead code' label and reclassify as SPEC-DEVIATION (missing integration, not dead code)." The exception classes are documented in `docs/01-tools/api-reference.md` which references them as part of the public API. They are defined as part of a planned exception hierarchy (TASK_022) but not yet integrated into the service layer. This represents missing integration, not dead code.

**Description:** Exception classes `VideoNotFoundError`, `QualityNotAvailableError`, and `ExtractionError` are defined in the exception hierarchy but never raised or caught in the codebase. Only `DownloadError` is used (imported in http_client.py).

**Evidence:**
- Grep shows only `DownloadError` is imported/used in production code
- `docs/01-tools/api-reference.md:330-332` documents these as part of the exception hierarchy
- The classes extend `VKDownloadError` and follow a planned hierarchy

**Recommendation:** Either remove unused exception classes or integrate them into the service layer where appropriate (e.g., `VideoNotFoundError` when video not found, `ExtractionError` when extraction fails).

---

### QLT-011: Unused `StreamWithCookies` model

| Field | Value |
|-------|-------|
| **ID** | QLT-011 |
| **Severity** | LOW |
| **Type** | REJECTED |
| **Affected Modules** | src/vkdownloader/models/video.py |
| **Classification** | advisory |

> **Rejection reason:** Per validation rules: "Reject if overengineered or adds complexity without clear maintenance benefit" and "Reject if ROI is negative for project scale." `StreamWithCookies` (lines 51-54 in `video.py`) is a simple Pydantic model extending `Stream` with one optional field (`cookies: str | None`). It adds no validation logic beyond what Pydantic provides. The model will work correctly via Pydantic's implicit validation without dedicated tests. Additionally, this finding duplicates TST-009 (Phase 07) which was already rejected with the same rationale.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | QLT-001, QLT-009, QLT-010 |
| Merged | 7 | QLT-002 → CFG-004, QLT-003 → CFG-004, QLT-004 → CFG-004, QLT-005 → CFG-004, QLT-006 → CFG-004, QLT-006b → CFG-005, QLT-007 → INT-007, QLT-008 → SRV-010 |
| Rejected | 1 | QLT-011 |

---

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| QLT-011 | Unused `StreamWithCookies` model | Per validation rules, this represents low-value complexity. `StreamWithCookies` is a trivial Pydantic model with no custom validation logic. It will work correctly via Pydantic's implicit validation without dedicated attention. This duplicate was already rejected in TST-009 (Phase 07) with the same rationale. |

---

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| QLT-002 | CFG-004 (Phase 02) | Duplicate unused import issue |
| QLT-003 | CFG-004 (Phase 02) | Duplicate unused variable issue |
| QLT-004 | CFG-004 (Phase 02) | Duplicate missing type arguments for generic dict |
| QLT-005 | CFG-004 (Phase 02) | Duplicate missing type annotation for extractor parameter |
| QLT-006 | CFG-004 (Phase 02) | Duplicate returning Any from function |
| QLT-006b | CFG-005 (Phase 02) | Duplicate create_stealth_context async return type issue (also covered in INT-001, SRV-009, SEC-003) |
| QLT-007 | INT-007 (Phase 05) | Duplicate test class definition |
| QLT-008 | SRV-010 (Phase 03) | Duplicate missing trailing newlines issue |

---

## Cross-Phase Conflicts

None detected. All merged findings are consistent with validated findings in earlier phases. The Phase 08 findings are largely cross-cutting concerns (type annotations, code quality, formatting) that were already identified and validated in earlier audit phases. This consolidation is expected and correct.

---

## Warnings

- **Duplicate Findings:** QLT-006b (create_stealth_context) appears in 5 audit phases (01, 02, 03, 04, 08). This is a cross-cutting concern that represents a single root cause: the function is exported, documented, and tested but never used by `BrowserManager`. The recommendation is consistent: remove the function or properly integrate it.
- **Documentation Alignment:** QLT-009 (hardcoded User-Agent) and QLT-010 (unused exceptions) highlight inconsistency between code and documentation. The Settings class defines `user_agent`, but `main.py` hardcodes it. The exceptions are documented but not used in service code.
- **Code Quality Risk:** Multiple findings relate to type safety violations. Project rule #9 (Type Safety Everywhere) is violated across downloader.py and extractor.py. These issues are consolidated under CFG-004 in Phase 02.

---

## Required Fixes (from Validated Findings)

- **QLT-001:** Replace `print()` statements with `logger` calls in main.py
- **QLT-009:** Use `settings.user_agent` instead of hardcoded User-Agent string
- **QLT-010:** Either remove unused exception classes or integrate them into the service layer where appropriate
- All type annotation issues are consolidated under CFG-004 (Phase 02)
- The `create_stealth_context` function issue is covered under CFG-005 (Phase 02)
- The duplicate test class is covered under INT-007 (Phase 05)

---

## Advisory Recommendations

All other findings in Phase 08 are either merged into validated findings from earlier phases or rejected. See the relevant phase validation reports for complete details on recommended fixes.