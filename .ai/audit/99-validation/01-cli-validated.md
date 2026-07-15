# Phase 01 Audit Findings — CLI Entry Point & Command Layer

**Executor:** auditor  
**Template:** .kilo/commands/audit/phases/01-audit-cli.md  
**Status:** complete  
**Validated:** yes

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 Import | `uv run python -c "import vkdownloader.cli ..."` | OK — all 14 submodules import cleanly |
| R2 Help | `vkdownloader --help`, `download --help`, `batch --help` | OK — all commands render without error |
| R3 Lint/Type | `uv run ruff check src/vkdownloader/cli.py` | Pass (exit 0) |
| R3 Lint/Type | `uv run mypy src/vkdownloader/cli.py` | Pass (exit 0) — note: "unused section(s): module = ['tests.*']" in pyproject |
| R4 Tests | `uv run pytest -q` | 201 passed, 4 warnings (test-side `coroutine never awaited`, not CLI production) |

No CRITICAL runtime breakage found. All problems below are from code-level audit of the CLI command layer, error presentation, and config/state access.

---

## Findings

### CLI-001: ~~ValueError handler misattributes all ValueErrors as "Invalid URL format"~~ [REJECTED]

> **Rejection reason:** The trigger path for `QualitySelector.select()`'s `ValueError("Cannot select from empty streams list")` is blocked by the conditional `if video.streams:` at cli.py:110. The code at lines 109-114 only invokes the selector when streams exist. While broad exception catching is an architectural concern, this specific execution path does not exist in production code.

---

### CLI-002: `QualityNotAvailableError` presentation depends on brittle message string-parsing [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 161-172), `src/vkdownloader/services/quality.py` (lines 80-83) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified at cli.py:163-166 and exceptions.py:16-19. The `QualityNotAvailableError` class has no structured fields, forcing the CLI to parse the exception message string. This is a current vulnerability affecting diagnostic quality.

**Description:** `QualityNotAvailableError` carries semantic data (requested quality + available list) but only as a formatted string. The CLI parses the message using `split("'")` and `split("Available: ")`:

```python
# cli.py:163-166
requested = error_str.split("'")[1] if "'" in error_str else "unknown"
available_str = error_str.split("Available: ")[-1] if "Available: " in error_str else ""
available_qualities = available_str.replace("'", "").replace("[", "").replace("]", "")
```

**Evidence:** quality.py:81-83 raises the message; exceptions.py:16-19 shows the exception has no fields.

**Recommendation:** Add structured fields (`requested: str`, `available: list[str]`) to `QualityNotAvailableError`.

---

### CLI-003: Generic `except Exception` discards the real error with no log record [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 173-175) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified at cli.py:173-175. The catch-all prints generic message without `logger.exception()`. `setup_logging()` is called but the exception is never logged, destroying diagnosability.

**Evidence:** cli.py:173-175 has no logging; `from None` suppresses chaining.

**Recommendation:** Add `logger.exception("download_failed", ...)` before the user-facing message.

---

### CLI-004: Repeated `Settings()` construction and inconsistent config sourcing in `batch` [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 246, 297, 348) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified at lines 246, 297, 348. Each `Settings()` instantiation re-reads environment variables. Per-URL settings only forward 3 fields, ignoring `download_timeout`, `throttled_rate`, `http_chunk_size` from env.

**Evidence:** cli.py:246, 297, 348 construct independent `Settings()` instances.

**Recommendation:** Construct one `Settings` instance at top of `batch_download` and reuse.

---

### CLI-005: ~~Progress callback writes `ProgressManager._state` directly, bypassing the public API and lock~~ [REJECTED]

> **Rejection reason:** The code is intentionally designed this way. The `_create_progress_callback` docstring (lines 35-38) explicitly states: "This callback uses GIL-atomic tuple assignment for fire-and-forget semantics. The asyncio.Lock in ProgressManager protects the read path." This is a documented architectural trade-off, not a defect.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- **CLI-002** (MEDIUM): `QualityNotAvailableError` lacks structured fields, forcing brittle string parsing in CLI.
- **CLI-003** (MEDIUM): Generic exception handler discards errors without logging.
- **CLI-004** (LOW): Multiple `Settings()` instantiations waste cycles and drop env config.

## Advisory Recommendations

None — all remaining advisory findings were rejected.

## Doc Updates Needed

None — no documentation deviations were identified.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | CLI-002, CLI-003, CLI-004 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 2 | CLI-001, CLI-005 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| CLI-001 | ValueError handler misattributes all ValueErrors as "Invalid URL format" | Trigger path for empty-streams `ValueError` is blocked by conditional `if video.streams:` at line 110 |
| CLI-005 | Progress callback writes ProgressManager._state directly | Intentional design documented at lines 35-38; GIL-atomic tuple assignment is explicitly chosen |

### Merged Findings

None

### Reclassified Findings

None

---

## Rollout Analysis

All validated findings are independent. No circular dependencies or rollout conflicts detected.

## Execution Validation

All target modules verified to exist at referenced lines. Findings are applicable.
