---
name: validated-audit-findings
description: Validated findings report for phase 08 - Code Quality, Security & Maintainability
agent: validator
alwaysApply: false
---

# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/08-audit-quality.md
**Status:** complete
**Validated:** yes
**Validator:** validator
**Date:** 2026-07-16

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 — Linter | `uv run ruff check src/` | Passed (configured rules E/W/F/I/B/C4/UP) |
| R1 — Formatter | `uv run ruff format --check src/` | **FAILED** — 7/23 files would be reformatted |
| R1 — Type checker | `uv run mypy src/` | Passed (strict mode, 23 files) |
| R2 — Tests | `uv run pytest` | Passed — 216 passed |
| R3 — Dead code | grep for unused defs/imports/fields | See findings QLT-003..005, QLT-007 |
| R4 — Security | grep for secrets/print/bare-except | See findings QLT-002, QLT-006 |

Note: `print()` statements, bare `except:`, hardcoded secrets, and `TODO`/`FIXME`
were searched explicitly and **none were found** in production code. Secrets are
only present in `.env` as commented-out examples. These dimensions are omitted per
the `problems-only` rule.

---

## Findings

### QLT-001: Source code is not formatted per the project's own tooling

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | cli.py, config.py, services/downloader.py, services/downloader_throttle.py, services/extractor.py, services/quality.py, services/segment_downloader.py |
| **Classification** | mandatory |

**Description:** The project's documented verification command `uv run ruff format --check <path>`
fails. 7 of 23 source files would be reformatted by `ruff format`. Any CI/commit
gate that runs the project's own verification commands will break. The ruff config
sets `line-length = 100` and relies on the formatter for line-length (E501 is
ignored), so inconsistent formatting also means inconsistent line breaks across the
codebase.

**Evidence:**
```
$ uv run ruff format --check src/
Would reformat: src\vkdownloader\cli.py
Would reformat: src\vkdownloader\config.py
Would reformat: src\vkdownloader\services\downloader.py
Would reformat: src\vkdownloader\services\downloader_throttle.py
Would reformat: src\vkdownloader\services\extractor.py
Would reformat: src\vkdownloader\services\quality.py
Would reformat: src\vkdownloader\services\segment_downloader.py
7 files would be reformatted, 16 files already formatted
```

**Recommendation:** Run `uv run ruff format src/` once to normalize all files, then
enforce `ruff format --check` in CI. This keeps the codebase consistent with the
project's stated tooling and prevents future drift.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Changed from BEST-PRACTICE to SPEC-DEVIATION. The project's ruff config
>   declares `line-length = 100` and `E501` is ignored (handled by formatter). The
>   formatter is an integral part of the project's own verification tooling. When the
>   verification command fails, it represents a deviation from the declared specification.
> - **See also:** Project ruff config at pyproject.toml:51-68

---

### QLT-002: `Any` type used, violating the "no Any" type-safety rule

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/infrastructure/network_monitor.py |
| **Classification** | advisory |

**Description:** Project rule #9 states: "Type Safety Everywhere ... Avoid `any`
completely." The `network_monitor.py` module imports `Any` from `typing` and uses it
for the Playwright response object and the recursive JSON walker, losing all type
safety on data that flows from untrusted network responses.

**Evidence:**
- `network_monitor.py:4` — `from typing import Any`
- `network_monitor.py:47` — `async def _intercept_response(self, response: Any) -> None:`
- `network_monitor.py:72` — `def _extract_urls_from_json(self, data: Any) -> None:`

mypy (strict) passes only because `Any` silently disables checking. These are the
only `Any` usages in the source tree.

**Recommendation:** Replace `Any` with concrete types. The Playwright response is
`playwright.async_api.Response` (already imported elsewhere in the package), and
the JSON walker can be typed with a `Protocol`/`TypeAlias` such as
`JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None`.
This restores static checking on the network-ingestion boundary, which is the most
important place to have it.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Changed from BEST-PRACTICE to SPEC-DEVIATION. Project rule #9 explicitly
>   requires avoiding `any` completely. This is a direct violation of the project's declared
>   architectural standard, not merely a best practice suggestion.
> - **See also:** Project rule #9 in .kilo/rules/project.md

---

### QLT-003: Dead function `_should_abort_retry` has zero callers

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | advisory |

**Description:** `_should_abort_retry` (line 128) is defined but never called from any
production or test code. Grep for `_should_abort_retry(` returns only the definition
in `segment_downloader.py` and references inside prior audit markdown files. It
duplicates the backoff/shutdown check that is already performed inline by
`_check_backoff_before_attempt` (line 137) and `_download_segment_parallel`.

**Evidence:**
```python
# segment_downloader.py:128
def _should_abort_retry(
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
    shutdown_event: asyncio.Event,
) -> bool:
    """Check if retry should be aborted due to backoff/shutdown."""
    return backoff_coordinator is not None and video_url is not None
```
Note the body only checks that coordinator/url are not None — it never inspects
`shutdown_event` or actual backoff state, so even if wired in it would be incorrect.

**Recommendation:** Remove the function. If the intent was a real abort check, fold
it into `_check_backoff_before_attempt` (which already inspects the shutdown event)
rather than re-adding a dead helper. Per dead-code policy, first confirm intent
before deletion.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed `_should_abort_retry` has no callers in production code.
>   Grep search returns only the definition at segment_downloader.py:128. The function's
>   implementation is also logically incorrect (does not check shutdown_event as its
>   docstring claims). This is valid dead code per project rule #10 (StrEnum for constants)
>   and rule #15 (small modules and functions) - unused functions should be removed.

---

### QLT-004: `DownloadStatus` enum is exported but never used

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/enums.py, src/vkdownloader/models/__init__.py |
| **Classification** | advisory |

**Description:** `DownloadStatus` (PENDING/DOWNLOADING/COMPLETED/FAILED) is defined in
`enums.py:38` and re-exported from `models/__init__.py`, but no module or test
references it. The CLI tracks status via plain strings (`"success"`/`"failed"`/
`"error: ..."`) in `cli.py`. The enum is documented-as-present but unused, adding a
maintenance surface that can silently drift from the string-based reality.

**Evidence:**
- `enums.py:38-44` — `class DownloadStatus(StrEnum): ...`
- `models/__init__.py:4,11` — exported in `__all__`
- Grep for `DownloadStatus` across `src/` returns only those two definition/export
  sites (no usage).

**Recommendation:** Either (a) adopt `DownloadStatus` in `cli.py`/`downloader.py`
result tuples so the enum is the single source of truth, or (b) remove it until a
consumer exists. Avoid keeping an enum that parallels string literals used elsewhere.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Changed from BEST-PRACTICE to SPEC-DEVIATION. The enum is documented
>   in api-reference.md (lines 660-672) and vkdownloader-overview.md (line 62), making
>   it part of the declared public API. Documentation states it exists for "Download state
>   tracking" but the implementation uses plain strings. This is a spec deviation - either
>   the docs should be updated to remove the enum, or the code should use it. Code has
>   priority per project rule #2.
> - **See also:** Docs at docs/01-tools/api-reference.md:660-672, docs/01-tools/vkdownloader-overview.md:62

---

### QLT-005: `StreamFormat.DASH` member is never used

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/models/enums.py |
| **Classification** | advisory |

**Description:** `StreamFormat` declares `HLS`, `DASH`, and `MP4`. Only `HLS` is ever
assigned (in `extractor.py` and `services/downloader_throttle` tests); `DASH` and
`MP4` are never produced or read. The extractor hard-codes `StreamFormat.HLS` or
`StreamFormat.MP4` branches but `DASH` is dead.

**Evidence:**
- `enums.py:20-25` — `class StreamFormat(StrEnum): HLS/DASH/MP4`
- Grep for `StreamFormat\.` returns only `StreamFormat.HLS` usages in `extractor.py`
  (lines 171, 225) and tests. No `StreamFormat.DASH` or `StreamFormat.MP4` usage
  anywhere.

**Recommendation:** Remove `DASH` (and `MP4` if genuinely unused) until the extractor
emits those formats. Keep the enum minimal to match actual capability.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Partially confirmed. `StreamFormat.DASH` is indeed unused - grep found no
>   references in src/. However, `StreamFormat.MP4` IS used (extractor.py:173) in the
>   conditional branch. The finding's evidence is partially incorrect. `DASH` should be
>   removed; `MP4` is actively used. This remains a BEST-PRACTICE finding for DASH removal.
> - **See also:** extractor.py:173 shows MP4 usage in conditional branch

---

### QLT-006: Console logger uses `structlog.PrintLoggerFactory`, emitting via `print()`

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/config.py |
| **Classification** | advisory |

**Description:** Project rule #12 forbids `print()` in production code ("use proper
logging"). `setup_logging` selects `structlog.PrintLoggerFactory()` for the console
path (`config.py:121`). That factory's `msg()` calls Python's built-in `print()`,
so in the default (non-file) run mode every application log line is written with
`print()`. This contradicts the stated convention and bypasses the stdlib `logging`
stack, which can cause interleaving/ordering issues with third-party libraries that
log via `logging`.

**Evidence:**
```python
# config.py:110-123
structlog.configure(
    processors=[...],
    logger_factory=structlog.PrintLoggerFactory(),   # <-- emits via print()
    cache_logger_on_first_use=True,
)
```

**Recommendation:** Use `structlog.WriteLoggerFactory(sys.stdout)` (still stdio, no
`print()`) or `structlog.stdlib.LoggerFactory()` wired to `logging`, so output goes
through a proper stream/logging layer and aligns with rule #12. Low effort.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Changed from BEST-PRACTICE to SPEC-DEVIATION. Project rule #12 explicitly
>   states "No `print()` Statements - use proper logging: `logger = logging.getLogger(__name__)`".
>   The `PrintLoggerFactory` internally uses `print()`, which is a direct violation of
>   this rule. Even if the effect is similar (writing to stdout), the mechanism violates
>   the architectural standard.
> - **See also:** Project rule #12 in .kilo/rules/project.md, config.py:121

---

### QLT-007: `Video` model fields are never read

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/models/video.py |
| **Classification** | advisory |

**Description:** `Video` declares `description`, `duration`, `thumbnail`,
`upload_date`, `views`. None of these are read anywhere in production code, and
`extractor.py` only populates `id`, `streams`, and `title` when building
`VideoWithStreams`. The remaining fields always stay `None`, so they are effectively
unused model surface.

**Evidence:**
- `video.py:12-17` — fields declared with `None` defaults.
- Grep for `.description`, `.duration`, `.thumbnail`, `.upload_date`, `.views`
  across `src/` — zero matches.

**Recommendation:** Remove the unused fields, or, if metadata is intended for future
output, populate and consume them deliberately and document the purpose. Per the
"Production Code is King" rule, avoid carrying fields that nothing reads.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Changed from BEST-PRACTICE to SPEC-DEVIATION. Project rule #2 states
>   "Production Code is King. If tests conflict with architecture or business logic — fix
>   or remove the tests. Never distort production code for tests." Combined with rule #15
>   (small modules and functions), carrying unused model fields represents dead weight that
>   should be removed unless there is an active intent to use them. The test file
>   test_models.py tests these fields (lines 14-15, 33-35) but does not demonstrate
>   any production need.
> - **See also:** test_models.py:14-15, 33-35 (tests fields that production code never reads)

---

### QLT-008: Fragile forward-reference hack in `dtos.py` (monkeypatched `__init__` + module-global mutation)

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/models/dtos.py |
| **Classification** | advisory |

**Description:** `HLSDownloadRequest` references runtime types (`Settings`,
`VKVideoExtractor`, `URLBackoffCoordinator`) that are not imported at module load.
Instead of a normal `TYPE_CHECKING` + `model_rebuild()` pattern, the module:
1. annotates fields with `# type: ignore[name-defined]` (lines 23-26),
2. defines `_ensure_model_rebuilt()` that mutates the module's own globals
   (`dtos_module.Settings = ...`, etc.) and calls `model_rebuild()`,
3. monkeypatches `HLSDownloadRequest.__init__` with `_lazy_init` at import time
   (lines 50-58).

This couples model construction to import-time side effects, hides real
name-resolution problems behind type-ignores, and is hard to follow. The
`# type: ignore[name-defined]` also risks masking genuine undefined-name errors if
`warn_unused_ignores` is ever tightened.

**Evidence:**
```python
# dtos.py:23-26
settings: Settings | None = None  # type: ignore[name-defined]
extractor: VKVideoExtractor | None = None  # type: ignore[name-defined]
backoff_coordinator: URLBackoffCoordinator | None = None  # type: ignore[name-defined]
...
# dtos.py:35-58  _ensure_model_rebuilt mutates module globals + patches __init__
```

**Recommendation:** Switch to the standard Pydantic v2 pattern: import the runtime
types under `if TYPE_CHECKING:` (or as strings) and call
`HLSDownloadRequest.model_rebuild()` once at module import after the real imports are
available. Remove the `__init__` monkeypatch and the `# type: ignore[name-defined]`
comments. This is the conventional, maintainable approach and keeps mypy strict.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed the non-standard forward-reference pattern. The code uses
>   `# type: ignore[name-defined]` + module-global mutation + `__init__` monkeypatch
>   instead of the standard Pydantic v2 `TYPE_CHECKING` + `model_rebuild()` approach.
>   While this works, it violates the project's preference for conventional patterns
>   (rule #7) and introduces complexity that could break with stricter mypy settings.
>   This is a valid BEST-PRACTICE finding for improved maintainability.

---

### QLT-009: Redundant `Settings()` construction just to read defaults

| Field | Value |
|-------|-------|
| **ID** | QLT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** `cli.py` constructs a full `Settings()` (which reads env/.env and
builds a Pydantic model) in three places solely to read a single default value
(`max_retries`, `max_concurrent_downloads`). This is wasteful and inconsistent with
the surrounding code that passes explicit `Settings(...)` instances.

**Evidence:**
```python
# cli.py:92
actual_max_retries = max_retries if max_retries is not None else Settings().max_retries
# cli.py:169
shared_semaphore = asyncio.Semaphore(Settings().max_concurrent_downloads)
# cli.py:431
_print_batch_summary(results, Settings().max_concurrent_downloads)
```
Note line 92-95 is also internally redundant: it builds `Settings()` then immediately
builds a second `Settings(cookie_source=..., max_retries=..., ssl_verify=...)`.

**Recommendation:** Read defaults from a single shared `Settings` instance (or module
constants) rather than instantiating the settings object repeatedly. Pass the
existing `settings` object into `_run_batch_with_progress` instead of re-reading
`Settings().max_concurrent_downloads`.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. The `Settings()` constructor involves Pydantic validation
>   and potentially reads .env files. Constructing it repeatedly (lines 92, 169, 431 in
>   cli.py) is wasteful. Line 92 is particularly redundant as it builds a Settings
>   instance just to read one field, then immediately discards it when building another
>   Settings with actual parameters. This violates rule #15 (small modules/functions)
>   and adds unnecessary overhead. Valid BEST-PRACTICE finding.

---

### QLT-010: High-complexity functions exceed single-responsibility guideline

| Field | Value |
|-------|-------|
| **ID** | QLT-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The phase guideline states functions should be focused and short
(~50 lines) with clear responsibility. `download_with_ffmpeg` (complexity C901 = 16)
and `_download_with_ytdlp` (C901 = 11) are the two most complex functions and combine
process spawning, progress monitoring, stderr draining, cancellation, and error
handling in one method each. `download_with_ffmpeg` is ~110 lines.

**Evidence:**
```
$ uv run ruff check --select C901 src/
C901 `download_with_ffmpeg` is too complex (16 > 10)  --> services/downloader.py:141
C901 `_download_with_ytdlp` is too complex (11 > 10)  --> services/downloader.py:416
```
(C901 is not in the project's active ruff `select` set, so it does not currently fail
CI — reported as forward-looking advice.)

**Recommendation:** Extract the progress-monitoring loop and the stderr-drain loop in
`download_with_ffmpeg` into small named coroutines (the inner `_monitor_progress` /
_drain_stderr` already exist but are wrapped in large branching blocks). For
`_download_with_ytdlp`, separate cookie-file handling and the cancellation wrapper
from the core download call. Keeps each function testable in isolation.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. `download_with_ffmpeg` is a class method (~110 lines) combining
>   subprocess management, progress monitoring, stderr handling, cancellation, and error
>   handling. `_download_with_ytdlp` (~95 lines) combines retry logic, token refresh, and
>   download orchestration. Per rule #15 (small modules and functions - "shorter code units
>   are easier to edit, review, and maintain"), decomposition would improve maintainability.
>   Valid BEST-PRACTICE finding. Low architectural risk.

---

## Cross-Finding Analysis

### Merged Findings
None - findings are distinct and address separate issues.

### Cross-Phase Conflicts
None detected - no conflicting evidence across phases in this single-phase report.

### Dependency Chains
- QLT-008 (model_rebuild pattern) and QLT-009 (Settings() repeated construction) could be
  addressed together since both relate to initialization patterns in entry points.

---

## Rollout Safety Assessment

### Execution Safety
- **QLT-001 (formatting)**: Safe - purely cosmetic, no behavior change.
- **QLT-002 (Any types)**: Safe - adding type hints, no runtime change.
- **QLT-003 (dead function)**: Safe - removing unused code.
- **QLT-004 (DownloadStatus)**: Depends on decision to remove vs. adopt. Removing is safe;
  adopting would require CLI string status → enum migration.
- **QLT-005 (DASH)**: Safe if removing - unused member with no references.
- **QLT-006 (PrintLoggerFactory)**: Low risk - behavior change but functionally equivalent.
- **QLT-007 (Video unused fields)**: Safe if removing - no production usage.
- **QLT-008 (model_rebuild)**: Low risk - standard Pydantic pattern.
- **QLT-009 (Settings() repetition)**: Safe - behavior preserving refactoring.
- **QLT-010 (complexity)**: Low risk - internal extraction, no API change.

### Architectural Consistency
The project follows established patterns (Pydantic v2, StrEnum, structlog). Changes should
maintain these conventions. The `Any` type usage (QLT-002) and `PrintLoggerFactory` (QLT-006)
are the most significant architectural deviations.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | QLT-003, QLT-005, QLT-008, QLT-009, QLT-010 |
| Reclassified | 5 | QLT-001, QLT-002, QLT-004, QLT-006, QLT-007 |
| Merged | 0 | — |
| Rejected | 0 | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| QLT-001 | BEST-PRACTICE | SPEC-DEVIATION | Project's own verification command fails; formatting is declared tooling |
| QLT-002 | BEST-PRACTICE | SPEC-DEVIATION | Project rule #9 requires avoiding `any` completely |
| QLT-004 | BEST-PRACTICE | SPEC-DEVIATION | Enum documented in API reference but unused; code should align with docs |
| QLT-006 | BEST-PRACTICE | SPEC-DEVIATION | Project rule #12 forbids print() in production code |
| QLT-007 | BEST-PRACTICE | SPEC-DEVIATION | Project rule #2 ("Production Code is King") + rule #15 - unused model fields |

### Rejected Findings

None. All findings were technically correct and address real issues.

---

## Required Fixes

Per SPEC-DEVIATION reclassifications, the following issues MUST be addressed to comply with
project architectural rules:

| ID | Priority | Action Required |
|----|----------|-----------------|
| QLT-001 | MEDIUM | Run `ruff format src/` to normalize formatting and align with project tooling |
| QLT-002 | MEDIUM | Replace `Any` with `playwright.async_api.Response` and typed JSON alias in network_monitor.py |
| QLT-004 | LOW | Either remove `DownloadStatus` enum or adopt it in CLI for status tracking |
| QLT-006 | LOW | Replace `PrintLoggerFactory` with `WriteLoggerFactory` or `stdlib.LoggerFactory` |
| QLT-007 | LOW | Remove unused Video fields (description, duration, thumbnail, upload_date, views) |

### Mandatory Fixes (per original findings)

| ID | Action |
|----|--------|
| QLT-001 | Normalize formatting with `ruff format` and gate it in CI. The project's own verification command currently fails; this is a process/correctness break. |

---

## Advisory Recommendations

| ID | Recommendation |
|----|---------------|
| QLT-003 | Remove dead `_should_abort_retry` (confirm intent first) |
| QLT-005 | Remove unused `StreamFormat.DASH` (MP4 is used, keep it) |
| QLT-008 | Replace the `dtos.py` `__init__` monkeypatch with standard `model_rebuild` |
| QLT-009 | Stop constructing `Settings()` repeatedly just to read defaults |
| QLT-010 | Decompose the two over-complex download functions |

---

## Warnings

- **QLT-004 and QLT-005**: Documentation lists these enums as present. Any removal
  should be accompanied by doc updates to avoid future confusion about "missing" features.
- **QLT-010**: Complexity threshold (C901 > 10) is not currently enforced in ruff
  `select`. If adding C901 to lint rules, consider the 10 threshold is quite low for
  async download orchestration code.

---

## Conclusion

All findings are valid. Five findings (QLT-001, QLT-002, QLT-004, QLT-006, QLT-007)
represent spec deviations from declared project rules rather than best-practice suggestions.
The remaining findings (QLT-003, QLT-005, QLT-008, QLT-009, QLT-010) are valid
BEST-PRACTICE recommendations for improved code quality and maintainability.