---
description: Validation report for Phase 01 audit findings -- Entry Point & Command Layer
source: .ai/audit/01-audit-cli/findings.md
validated_by: validator
status: complete
validated: yes
---

# Phase 01 Audit Findings — Entry Point & Command Layer

**Executor:** audit-executor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes
**Validator:** validator
**Validation Status:** complete
**Source findings:** .ai/audit/01-audit-cli/findings.md
**Phase template:** .kilo/commands/audit/phases/01-audit-cli.md
**Scope:** Entry point, command definitions, argument/parameter parsing, error presentation, and the boundary between the entry layer and the service/core layers.

**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).
Entry point: `vkdownloader.cli:cli` (Typer app in src/vkdownloader/cli.py), invokable via the
`vkdownloader` console script or `python -m vkdownloader` (__main__.py).

---

## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 — Import | `uv run python -c "from vkdownloader.cli import app, cli"` | PASS | Entry point and all submodules (config, exceptions, models.*, services.*, utils.*) import cleanly. |
| R2 — Help/schema | `python -m vkdownloader --help` / `download --help` / `batch --help` | PASS | Both commands enumerated; all options documented; no crashes (exit 0). `--cookie-source` lists [none\|browser\|file] (see CLI-006). |
| R3 — Lint + types | `uv run ruff check` / `ruff format --check` / `uv run mypy src/vkdownloader` | FAIL | see CLI-003, CLI-004, CLI-005. (`mypy cli.py` alone passes.) |
| R4 — Tests | `uv run pytest` | PASS | 325 passed (incl. 23 in test_cli.py). |

---

## Findings

### CLI-001: Batch orchestration and concurrency helpers are embedded in the entry layer instead of a service facade

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed against the live codebase. cli.py is 654 lines and contains the full batch orchestration layer: ConcurrencyTracker (lines 70-88), _TrackedSemaphore (91-116), DownloadContext (119-127), _download_single (181-264), _run_batch_with_progress (267-369), _print_batch_summary (372-409). The download command (418-539) is thin and delegates to download_video(). The batch_download command (542-644) calls the inline orchestration helpers rather than a service facade. The docstring at services/downloader.py:1158-1159 confirms the shared orchestration intent. No architectural drift since audit.
> - **See also:** CLI-002 (entry-layer coupling), CLI-005 (downloader.py formatting gate)

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE / SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** cli.py (654 lines) is not a thin command layer. In addition to the two Typer
commands, it owns the entire batch orchestration and concurrency-tracking machinery:
ConcurrencyTracker + _TrackedSemaphore + DownloadContext dataclasses, _download_single,
_create_progress_callback, _format_progress, _poll_progress_display, _run_batch_with_progress
(~100 lines of task scheduling, semaphore/backoff wiring, as_completed drain, cancellation,
result aggregation) and _print_batch_summary.

The `download` command IS thin (delegates to download_video), but `batch_download`
reimplements parallel orchestration inline in the entry layer rather than delegating to a service
facade. services/downloader.py download_video is documented as "Shared orchestration for
single-download and batch-download CLI handlers" (downloader.py:1158-1159), yet the
batch-level concurrency/progress orchestration lives in cli.py, not in services/.

This contradicts project rules #3 (strict separation of concerns), #4 (single responsibility),
and #15 (small focused modules/functions), and the Clean Architecture intent in
docs/01-tools/vkdownloader-overview.md.

**Evidence:**
- src/vkdownloader/cli.py:70-88 — ConcurrencyTracker dataclass (peak tracking).
- src/vkdownloader/cli.py:91-116 — _TrackedSemaphore wrapping asyncio.Semaphore.
- src/vkdownloader/cli.py:119-127 — DownloadContext batch-scoped state.
- src/vkdownloader/cli.py:130-178 — progress callback + polling helpers.
- src/vkdownloader/cli.py:181-264 — _download_single (per-URL orchestration: correlation bind,
  semaphore wrap, status-tuple mapping, exception handling).
- src/vkdownloader/cli.py:267-369 — _run_batch_with_progress (semaphore + backoff coordinator
  creation, asyncio.create_task fan-out, as_completed drain, progress task, cleanup).
- src/vkdownloader/cli.py:372-409 — _print_batch_summary (also raises typer.Exit).
- Contrast: services/downloader.py:1156-1160 (docstring) vs cli.py:542-644 (batch handler body).

**Recommendation (advisory):** Move the batch orchestration (task fan-out, semaphore + backoff
coordination, progress display, summary) into a dedicated batch service (e.g.
services/batch_downloader.py) exposing a single run_batch(...) async function. Reduce the
`download`/`batch` Typer handlers to argument parsing -> service call -> result/error
presentation. This makes the orchestration unit-testable without invoking the CLI and restores the
documented entry -> service -> core boundary. Effort: large; priority: recommended.

---

### CLI-002: Entry layer imports private/internal symbols across module boundaries

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed. All three private-symbol imports verified at cited locations: _strip_auth_params imported cli.py:30, used at 248/259/537/606; _map_exception_to_status imported cli.py:22, used at 262 (exceptions.py docstring lines 5-8 explicitly says new call sites should prefer status_label()); VIDEO_ID_PATTERN imported cli.py:27, used at 605. Note: the specific exception paths (lines 242/244/252/254) already use e.status_label(); only the generic Exception fallback at line 262 uses the legacy _map_exception_to_status.
> - **See also:** CLI-001 (entry-layer coupling)

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py <-> utils/url_sanitizer.py, exceptions.py, services/extractor.py |
| **Classification** | advisory |

**Description:** cli.py imports and calls underscore-prefixed (private) symbols defined in other
modules, coupling the entry layer to implementation details that are not part of any module
public API:

1. _strip_auth_params (utils/url_sanitizer.py:6) — imported at cli.py:30, used at
   cli.py:248, 259, 537, 606. (Also used widely across services/, but the entry layer should not
   reach into a private utility.)
2. _map_exception_to_status (exceptions.py:196) — imported at cli.py:22, used at cli.py:262 for
   the unexpected-exception path. The exceptions.py docstring (lines 4-8) explicitly states the
   legacy helper "is retained for backward compatibility; new call sites should prefer
   status_label() directly." cli.py is a new call site using the legacy path, diverging from the
   documented guidance.
3. VIDEO_ID_PATTERN (services/extractor.py:24) — imported at cli.py:27 and used inline at
   cli.py:605 for batch URL validation, reaching into the extractor internals to duplicate
   validation logic in the entry layer.

**Evidence:** src/vkdownloader/cli.py:22, 27, 30, 248, 259, 262, 537, 605, 606;
services/extractor.py:24; utils/url_sanitizer.py:6; exceptions.py:4-8, 196.

**Recommendation (advisory):** Expose public, stable helpers for the operations the entry layer
needs (e.g. a VideoUrl.parse / is_valid_video_url on the extractor, a public
format_validation_error in config, a sanitize_url_for_log in url_sanitizer) and have
_download_single use exc.status_label() (the documented replacement) instead of the legacy
_map_exception_to_status. Keep private symbols out of the entry layer to widen the refactor
freedom of the service/utils layers. Effort: small; priority: recommended.
### CLI-003: `ruff check` fails on a real lint error and stray tooling files

> **Validation Note:**
> - **Action:** reclassified (RUNTIME-ERROR -> SPEC-DEVIATION)
> - **Detail:** Confirmed by re-running uv run ruff check: exits non-zero with exactly 3 errors matching the finding: E401 + I001 in .temp/deadcheck.py:1; F841 in tests/test_correlation.py:28. The F841 is a genuine defect: full = uuid.uuid4().hex is assigned but never used; the test test_generate_correlation_id_truncates_uuid asserts only len(cid)==8 and int(cid,16), never comparing against full. .temp/deadcheck.py is a 30-line stray dead-code-analysis script. pyproject.toml [tool.ruff] has no exclude key so .temp/ and .ai/ are linted. No drift since audit.
> - **See also:** CLI-005 (shared root cause: missing ruff exclude for scaffolding paths)

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR -> SPEC-DEVIATION (reclassified) |
| **Affected Modules** | tests/test_correlation.py; .temp/deadcheck.py; src/vkdownloader/ (ruff scope) |
| **Classification** | mandatory |

**Description:** `uv run ruff check` exits non-zero (3 errors). One is a genuine defect in a
test; the others are a stray, unmaintained script committed at the repo root that the project
lints because there is no ruff `exclude` for tooling paths.

The `tests/test_correlation.py:28` F841 (local variable `full` assigned but never used) is inside
`test_generate_correlation_id_truncates_uuid`, which claims to verify 8-hex-char truncation but
never asserts against `full` — so the test does not actually test what its name/documented
behavior states. The `.temp/deadcheck.py` script has E401 (multiple imports on one line) and
I001 (unsorted imports); it is a developer dead-code-analysis snippet left in the working tree
and is not part of the application or test code.

**Evidence:**
```
E401 [*] Multiple imports on one line
 --> .temp\deadcheck.py:1:1
F841 Local variable `full` is assigned to but never used
  --> tests\test_correlation.py:28:5
Found 3 errors.
RUFF CHECK EXIT: False
```
- Ruff config in pyproject.toml has `[tool.ruff]` with only line-length/target-version and
  `[tool.ruff.lint]` selects — no `[tool.ruff] exclude`, so `.temp/` and `.ai/` are linted.

**Recommendation (mandatory):** Fix the unused variable in `tests/test_correlation.py:28`
(restore the assertion or remove the line). Either delete `.temp/deadcheck.py` (and the
`.ai/builders/` scaffolding files, see CLI-005) or add an `exclude` under `[tool.ruff]` so
non-application tooling is not part of the lint gate. Effort: trivial (test) + small (exclude);
priority: mandatory (restores the project lint gate).

---

### CLI-004: `mypy src/vkdownloader` fails on a shared entrypoint dependency

> **Validation Note:**
> - **Action:** reclassified (RUNTIME-ERROR -> SPEC-DEVIATION)
> - **Detail:** Confirmed by re-running uv run mypy src/vkdownloader: src/vkdownloader/utils/correlation.py:55: error: Unused type: ignore comment [unused-ignore]. Found 1 error in 1 file (checked 26 source files). The stale comment is on line 54 with # type: ignore[no-any-return]. pyproject.toml sets warn_unused_ignores=true and follow_imports=silent. Re-confirmed: uv run mypy src/vkdownloader/cli.py alone returns Success: no issues found in 1 source file (the error is masked by follow_imports=silent). cli.py:29 imports from correlation.py. No drift since audit.
> - **See also:** CLI-003, CLI-005 (shared: restore quality gates before structural refactors)

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR -> SPEC-DEVIATION (reclassified) |
| **Affected Modules** | src/vkdownloader/utils/correlation.py |
| **Classification** | mandatory |

**Description:** `uv run mypy src/vkdownloader` exits non-zero with one error:
`src/vkdownloader/utils/correlation.py:55: error: Unused "type: ignore" comment
[unused-ignore]`. The project mypy config sets `warn_unused_ignores = true`, so the stale
`# type: ignore[no-any-return]` on the `return context_vars.get("correlation_id")` line is
treated as an error. This module is a direct dependency of the entry layer
(`from .utils.correlation import ... bind_correlation_id, ... clear_correlation_id` at
cli.py:29), so the package the CLI imports from does not type-check clean.

Note: `uv run mypy src/vkdownloader/cli.py` alone reports SUCCESS (the error is masked because
`follow_imports = "silent"` suppresses errors in silently-followed modules when checking cli.py
in isolation). The failure only surfaces when the whole package is checked, which is the
project intent (strict, whole-package typing).

**Evidence:**
```
src\vkdownloader\utils\correlation.py:55: error: Unused "type: ignore" comment  [unused-ignore]
Found 1 error in 1 file (checked 26 source files)
MYPY EXIT: False
```
- cli.py:29 (entry layer import of the failing module).
- pyproject.toml `[tool.mypy]` has `strict = true`, `warn_unused_ignores = true`.

**Recommendation (mandatory):** Remove the now-unnecessary `# type: ignore[no-any-return]` on
correlation.py:54 (or, if the ignore is still needed for some consumer, investigate why mypy no
longer flags it and delete it). Re-run `uv run mypy src/vkdownloader` to confirm zero errors.
Effort: trivial; priority: mandatory (restores the project type-check gate, which the entry layer
depends on).
### CLI-005: `ruff format --check` fails including production downloader.py and CLI tests

> **Validation Note:**
> - **Action:** reclassified (RUNTIME-ERROR -> SPEC-DEVIATION)
> - **Detail:** Confirmed by re-running uv run ruff format --check: exits non-zero with 7 files would be reformatted: .ai/builders/back/py_map.py, .ai/builders/back/py_map_libcst.py, .temp/deadcheck.py, src/vkdownloader/services/downloader.py, tests/test_cli.py, tests/test_hls_downloader.py, tests/test_security.py (39 files already formatted). cli.py itself is clean. The stragglers .ai/builders/back/*.py and .temp/deadcheck.py overlap with CLI-003 exclude-config concern. No drift since audit.
> - **See also:** CLI-003 (shared root cause: missing ruff exclude for scaffolding paths)

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR -> SPEC-DEVIATION (reclassified) |
| **Affected Modules** | src/vkdownloader/services/downloader.py; tests/test_cli.py; tests/test_security.py; tests/test_hls_downloader.py; .ai/builders/back/*.py, .temp/deadcheck.py |
| **Classification** | mandatory |

**Description:** `uv run ruff format --check` exits non-zero: "7 files would be reformatted".
This includes `services/downloader.py` (the production service the `download`/`batch` commands
delegate to for downloads) and `tests/test_cli.py` (the entry-layer test suite). The entry
module itself (`cli.py`) is correctly formatted — confirmed by `ruff format --check
src/vkdownloader/cli.py` -> "1 file already formatted" — so the format drift is in the service
layer the CLI calls and in its tests, not in cli.py itself. The two `.ai/builders/back/*.py`
files and `.temp/deadcheck.py` are stray AI/tooling artifacts also caught by the format check.

**Evidence:**
```
Would reformat: .ai\builders\back\py_map.py
Would reformat: .ai\builders\back\py_map_libcst.py
Would reformat: .temp\deadcheck.py
Would reformat: src\vkdownloader\services\downloader.py
Would reformat: tests\test_cli.py
Would reformat: tests\test_hls_downloader.py
Would reformat: tests\test_security.py
7 files would be reformatted, 39 files already formatted
RUFF FORMAT EXIT: False
```
- cli.py format check: "1 file already formatted" (clean).

**Recommendation (mandatory):** Run `ruff format` over the repo (or just the drifted files) to
restore formatting and unblock the format gate. Add an `exclude` to `[tool.ruff]` for
`.ai/` and `.temp/` so non-application scaffolding is not part of the format/lint gate, and
consider whether `tests/test_cli.py` formatting drift indicates a missing pre-commit/format
hook in CI. Effort: trivial (format) + small (exclude + hook); priority: mandatory.

---

### CLI-006: `--help` advertises the unimplemented `file` cookie-source option; docs disagree on its behavior

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed by re-running python -m vkdownloader download --help and batch --help: both list --cookie-source -c [none|browser|file] with help text none or browser (file not implemented). CookieSource.FILE = file exists at enums.py:50. config.py:145-157 validate_cookie_source raises ValueError (not NotImplementedError). Pydantic converts to ValidationError, surfaced at cli.py:483/592 as Configuration error. Doc cross-check: api-reference.md:99 and vkdownloader-overview.md:63 say NotImplementedError (stale); api-reference.md:656 says Rejected with ValueError (correct); cli-reference-clean.md:67 says file not implemented (vague); cli-reference-clean.md:198 says Raising ValidationError at construction (correct). The runtime issue is real and unchanged.
> - **See also:** CLI-007 item 3 (overlapping CookieSource.FILE stale doc)

| Field | Value |
|-------|-------|
| **ID** | CLI-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py; src/vkdownloader/config.py; src/vkdownloader/models/enums.py; docs/99-reference/cli-reference-clean.md; docs/01-tools/api-reference.md |
| **Classification** | advisory |

**Description:** The Typer-generated `--help` for both `download` and `batch` lists
`--cookie-source -c [none|browser|file]`, presenting `file` as a selectable value. But `file` is
not actually implemented: the `CookieSource` enum still defines `FILE = "file"`
(enums.py:50), and the `Settings` validator (config.py:145-157) raises `ValueError` (surfacing
as a `pydantic.ValidationError`) only at Settings construction — after argument parsing already
accepted it. The CLI therefore silently accepts an option it cannot fulfill, then fails later
with a "Configuration error". This is an input-validation/UX deviation: invalid options should be
rejected up front with a clear message, not deferred.

The documentation itself is internally inconsistent about what `file` does:
- cli-reference-clean.md:67 says "file not implemented"
- api-reference.md:99 says "Raises NotImplementedError"
- api-reference.md:656 says "Rejected with ValueError"
- vkdownloader-overview.md:63 says "is not implemented and raises NotImplementedError"
The actual code raises `ValueError` (config.py:150-156) which Pydantic converts to
`ValidationError`; it never raises `NotImplementedError`.

**Evidence:**
- R2 `download --help` output: `--cookie-source -c [none|browser|file] ... [default: none]`.
- src/vkdownloader/models/enums.py:50 — `FILE = "file"`.
- src/vkdownloader/config.py:145-157 — `validate_cookie_source` raises ValueError for "file".
- src/vkdownloader/cli.py:592, 483 — Settings construction catches the error and prints
  "Configuration error: ..." (handled gracefully, exit 1), so no crash but poor discoverability.

**Recommendation (advisory/suggested):** Either (a) remove `FILE` from the `CookieSource` enum
so Typer stops advertising an unimplemented option (cleaner, least surprise), or (b) implement
file-based cookie loading. Simultaneously reconcile the docs: the code raises
`ValueError`/`ValidationError`, never `NotImplementedError`. Effort: small; priority: recommended.
If `FILE` is meant to remain a placeholder, document the placeholder semantics consistently and
consider rejecting it at the Typer enum parsing layer instead of deferring to Settings.
### CLI-007: Architecture and API reference documentation is stale relative to the codebase

> **Validation Note:**
> - **Action:** validated
> - **Detail:** All six sub-claims confirmed against the live codebase: (1) STRUCT.md omits __main__.py, services/concurrency.py, utils/correlation.py -- all confirmed to exist and are used by the entry layer; (2) overview.md:294-296 line counts stale -- downloader.py 487->actual 1219, segment_downloader.py 336->actual 902, ffmpeg_utils.py 269->actual 361 (verified by line count); (3) overview.md:63 claims FILE raises NotImplementedError -- code raises ValueError/ValidationError (see CLI-006); (4) research doc:34 claims missing merge_contextvars -- config.py:240 already registers structlog.contextvars.merge_contextvars; :77 claims no correlation-ID infrastructure -- utils/correlation.py exists and is imported by cli.py:29; (5) api-reference.md:664 documents vkdownloader.infrastructure.http_client -- confirmed non-existent via import failure; infrastructure/ contains only browser.py, network_monitor.py, __init__.py; (6) api-reference.md:720 documents ProgressManager.get_progress -- confirmed non-existent; actual ProgressManager methods are clear, get_formatted_progress, update, update_sync (verified via dir()). No drift since audit.
> - **See also:** CLI-006 (overlapping CookieSource.FILE stale doc)

| Field | Value |
|-------|-------|
| **ID** | CLI-007 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | docs/STRUCT.md; docs/01-tools/vkdownloader-overview.md; docs/01-tools/api-reference.md; docs/error-handling-logging-research-2025-2026.md |
| **Classification** | advisory |

**Description:** Project rule #14 (keep documentation updated continuously) is violated across
several docs referenced by/around the entry point. These are stale descriptions, not code bugs,
but they actively mislead maintainers auditing the CLI and contradict the runtime verification
done this phase.

1. docs/STRUCT.md is a stale folder listing. It omits modules that exist and are used by the
   entry layer: src/vkdownloader/__main__.py (the `python -m vkdownloader` entry point — used in
   R2), src/vkdownloader/services/concurrency.py (defines the SemaphoreLike Protocol imported by
   services/downloader.py and services/segment_downloader.py), and src/vkdownloader/utils/
   correlation.py (correlation-ID infrastructure imported by cli.py).
2. docs/01-tools/vkdownloader-overview.md:294-296 lists module line counts that no longer match:
   downloader.py "~487 lines" (actual 1219), segment_downloader.py "~336" (actual 902),
   ffmpeg_utils.py "~269". The "Module Architecture" section also does not mention
   concurrency.py or correlation.py.
3. docs/01-tools/vkdownloader-overview.md:63 claims CookieSource.FILE "is not implemented and
   raises NotImplementedError"; the code raises ValueError/ValidationError (see CLI-006).
4. docs/error-handling-logging-research-2025-2026.md:34 claims structlog is "missing
   merge_contextvars" as the first processor, and :77 claims "there is no correlation-ID
   infrastructure" — but config.py:240 already registers
   structlog.contextvars.merge_contextvars as the first processor, and utils/correlation.py +
   cli.py (lines 29, 219-220, 263-264, 290-291, 366-369) already implement correlation-ID
   binding. The research doc describes a pre-implementation state that the code has since solved.
5. docs/01-tools/api-reference.md:664 documents `vkdownloader.infrastructure.http_client`
   (HttpClient) which does not exist — infrastructure/ contains only browser.py, network_monitor.py
   and __init__.py (a stale http_client.cpython-312.pyc lingers in __pycache__).
6. docs/01-tools/api-reference.md:720 documents `ProgressManager.get_progress(url_index)` which
   does not exist in services/downloader_throttle.py; the actual ProgressManager exposes only
   update, update_sync, get_formatted_progress and clear.

**Evidence:** src glob (infrastructure/ has no http_client.py); services/downloader.py = 1219
lines; segment_downloader.py = 902 lines; config.py:240 (merge_contextvars present);
utils/correlation.py exists and is imported by cli.py:29.

**Recommendation (advisory):** Regenerate/refresh docs against the actual source: update
STRUCT.md with current modules, correct the overview module line counts and add concurrency.py
/ correlation.py / __main__.py, fix the CookieSource.FILE semantics to match code
(ValueError/ValidationError), archive or annotate the research doc to note merge_contextvars +
correlation IDs are now implemented, remove the non-existent HttpClient and get_progress entries
from api-reference.md. Effort: small-medium; priority: recommended for documentation accuracy.

---


## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 (CLI-003, CLI-004, CLI-005) |
| MEDIUM | 3 (CLI-001, CLI-002, CLI-006) |
| LOW | 1 (CLI-007) |
| **Total** | **7** |

## Mandatory Fixes

- CLI-003 (SPEC-DEVIATION) -- Fix F841 unused variable in tests/test_correlation.py:28 and exclude .temp/.ai tooling paths from the ruff lint scope.
- CLI-004 (SPEC-DEVIATION) -- Remove the unused type: ignore comment in utils/correlation.py:54 so mypy src/vkdownloader is clean.
- CLI-005 (SPEC-DEVIATION) -- Run ruff format to fix formatting drift in services/downloader.py and tests, and exclude .ai/.temp scaffolding from the format gate.

## Advisory Recommendations

- CLI-001 (BEST-PRACTICE/SPEC-DEVIATION) -- Move batch orchestration (ConcurrencyTracker, _download_single, _run_batch_with_progress, _print_batch_summary, progress helpers) out of cli.py into a services/batch_downloader facade so the Typer handlers stay thin.
- CLI-002 (BEST-PRACTICE) -- Expose public helpers for URL validation, URL sanitization logging, and validation-error formatting; switch _download_single to exc.status_label() and drop the private-symbol imports from the entry layer.
- CLI-006 (SPEC-DEVIATION) -- Remove the unimplemented FILE value from the CookieSource enum (or implement it) so --help no longer advertises an option that errors at construction time; reconcile the docs.
- CLI-007 (DOC-UPDATE) -- Bring documentation (STRUCT.md, overview, api-reference, research doc) back in sync with the source.

## Doc Updates Needed

- CLI-006 -- Correct CookieSource.FILE documentation across cli-reference-clean.md, api-reference.md and vkdownloader-overview.md to state it raises ValueError/ValidationError (not NotImplementedError).
- CLI-007 -- Refresh STRUCT.md, the module line-counts/architecture and module list in the overview, remove the non-existent HttpClient and ProgressManager.get_progress entries in api-reference.md, and annotate the research doc to reflect the now-implemented merge_contextvars/correlation-ID support.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | CLI-001, CLI-002, CLI-006, CLI-007 |
| Reclassified | 3 | CLI-003, CLI-004, CLI-005 |
| Merged | 0 | see Merge Notes below |
| Rejected | 0 | all findings validated against live code |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| (none) | -- | All seven findings confirmed real against the live codebase. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| (none) | -- | No findings share a single root cause warranting a hard merge. See Merge Notes for overlapping-but-distinct findings. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CLI-003 | RUNTIME-ERROR | SPEC-DEVIATION | RUNTIME-ERROR is not a standard validator type. The ruff check failure is a deviation from the project enforced quality gate (verification commands must pass). |
| CLI-004 | RUNTIME-ERROR | SPEC-DEVIATION | RUNTIME-ERROR is not a standard validator type. The mypy failure is a deviation from the project enforced type-check gate. |
| CLI-005 | RUNTIME-ERROR | SPEC-DEVIATION | RUNTIME-ERROR is not a standard validator type. The ruff format failure is a deviation from the project enforced format gate. |

### Merge Notes (overlapping-but-distinct findings)

1. CLI-003 <-> CLI-005 -- shared root cause: missing ruff exclude for scaffolding paths. Both findings cite .temp/deadcheck.py as a lint/format offender and both recommend adding an exclude under [tool.ruff] for .temp/ and .ai/. However, they are not merged because: they target different ruff subcommands (ruff check vs ruff format --check); they have distinct mandatory fixes (F841 code defect in test_correlation.py vs formatting drift in downloader.py/test_cli.py); the exclude config is only shared context for scaffolding files, not source/test files. Decision: keep separate; the exclude config fix is a shared recommendation applied under both.

2. CLI-006 (doc aspect) <-> CLI-007 item 3 -- shared root cause: stale CookieSource.FILE doc. Both describe the stale claim that CookieSource.FILE raises NotImplementedError. They are not merged because: CLI-006 is primarily a runtime/SPEC deviation (Typer advertises file as a selectable option, but it is rejected at Settings construction); CLI-007 is a broad DOC-UPDATE finding covering six independent doc-drift items across four files. Decision: keep separate. CLI-006 doc-update scope absorbs the specific NotImplementedError claim; CLI-007 covers it as one of six items.

## Rollout Analysis

### Risks, Dependencies, and Sequencing

Gate fixes must precede structural refactors. CLI-003 (ruff check), CLI-004 (mypy), and CLI-005 (ruff format) are the project quality gates. New or refactored code produced by CLI-001 and CLI-002 must pass all three. The gates are currently broken, so any refactor effort should start by restoring them.

**Sequencing (recommended):**

1. **Phase A -- Gate restoration (independent, can parallelize):**
   - CLI-003: fix F841 in tests/test_correlation.py:28; add extend-exclude for .temp/ and .ai/ under [tool.ruff] in pyproject.toml.
   - CLI-004: remove unused type: ignore comment at correlation.py:54-55.
   - CLI-005: run ruff format on the 7 drifted files; add same extend-exclude from CLI-003.
   - Note: CLI-003 and CLI-005 share the extend-exclude config change -- apply once, covers both.
   - No rollout risk: all changes are deletions/removals (dead variable, dead type:ignore, formatting normalization). No behavioral change.

2. **Phase B -- Behavioral fix (depends on Phase A gates):**
   - CLI-006: resolve CookieSource.FILE -- either remove FILE from the enum (enums.py:50) so Typer stops advertising it, or implement file-based loading. Requires coordinated changes to enums.py + config.py:145-157 + docs. Removing FILE from the enum automatically updates --help (Typer reads the enum). Low risk if the FILE code path is confirmed unused by tests (verified: no production code branches on CookieSource.FILE except the validator that rejects it).

3. **Phase C -- Structural refactoring (depends on Phase A gates; touches cli.py):**
   - CLI-001: extract batch orchestration into services/batch_downloader.py.
   - CLI-002: replace private-symbol imports with public helpers.
   - Rollout conflict risk: both findings modify cli.py and exceptions.py. They must be sequenced or merged into a single PR to avoid inter-diff conflicts. CLI-002 rewrite of _download_single overlaps with CLI-001 orchestration extraction (same function). Recommend doing CLI-001 first (move orchestration to service), then CLI-002 (clean up private imports).
   - Dependency: CLI-001 services/batch_downloader.py would import from services/ (download_video, downloader_throttle) and utils/ (correlation, url_sanitizer) -- no new circular dependencies introduced if done as a service-layer module.
   - No circular dependency: services/batch_downloader -> services/downloader is a valid direction. cli -> services/batch_downloader is a valid direction.

4. **Phase D -- Documentation sync (no code dependency, but best done last):**
   - CLI-007: refresh docs. Some items depend on Phase B (CLI-006 FILE doc fix should follow the code decision on whether FILE is removed or implemented).

### Rollout Safety Checks

- **Circular dependencies:** None detected. cli -> services -> utils/models/enums is a clean direction. Moving batch orchestration into services/batch_downloader keeps the same direction.
- **Backward compatibility:** CLI-006 removing CookieSource.FILE changes the public API surface. Within this repo, the only reference is config.py:145-157 (the rejecting validator), so the risk is contained. External consumers using CookieSource.FILE would break -- but this is an internal CLI package (v0.1.0, Alpha maturity), so the blast radius is minimal.
- **Test impact of CLI-003 fix:** tests/test_correlation.py:28 -- the full variable is unused. Either removing the line or adding an assertion is safe (the test currently passes with 5 tests in test_correlation.py; 325 total).
- **Rollback feasibility:** All Phase A fixes are trivially reversible (re-add the type:ignore comment, re-introduce the dead variable, revert formatting via git checkout). Phase B/C/D are structural and should use feature branches with review.

## Execution Validation

### Applicability and Execution Readiness

- **CLI-001:** Ready. Targets verified: ConcurrencyTracker, _TrackedSemaphore, DownloadContext, _download_single, _run_batch_with_progress, _print_batch_summary all present in cli.py at cited line ranges. The download command is thin; batch_download calls inline helpers. Recommendation targets a new services/batch_downloader.py -- greenfield addition, not a modification of existing module.
- **CLI-002:** Ready. All three private-symbol references confirmed at cited locations. exceptions.py docstring (lines 5-8) documents status_label() as the preferred replacement.
- **CLI-003:** Ready / mandatory. F841 confirmed by ruff check output. .temp/deadcheck.py confirmed (30-line stray script). No [tool.ruff] exclude in pyproject.toml confirmed.
- **CLI-004:** Ready / mandatory. correlation.py:55 unused type:ignore confirmed by mypy. Entry layer (cli.py:29) depends on this module.
- **CLI-005:** Ready / mandatory. ruff format --check confirmed 7 files drifted. Production services/downloader.py and tests/test_cli.py among offenders.
- **CLI-006:** Ready. download --help and batch --help confirmed advertising [none|browser|file]. CookieSource.FILE in enums.py:50. config.py:145-157 raises ValueError (not NotImplementedError).
- **CLI-007:** Ready. All six doc staleness claims confirmed against live source. No code changes required.

### Execution Prerequisites

1. Restore quality gates (CLI-003, CLI-004, CLI-005) before any structural change.
2. Do CLI-006 before CLI-007 doc refresh so docs reflect the final CookieSource state.
3. Sequence CLI-001 before CLI-002 in cli.py, or combine into a single change to avoid merge conflicts.
4. Verify ruff check, ruff format --check, and mypy src/vkdownloader all pass after each change.

## Warnings

### Architectural Risks

- **CLI-001 (entry-layer orchestration):** The batch orchestration in cli.py is untestable in isolation without invoking the Typer CLI or running asyncio.run. Extracting it to services/batch_downloader.py restores unit-testability and keeps the same dependency direction (cli -> services -> utils/models/enums). No circular dependencies introduced.
- **CLI-006 (enum removal impact):** Removing CookieSource.FILE changes the public API surface. Within this repo, the only reference is config.py:145-157 (the rejecting validator). External consumers using CookieSource.FILE would break -- but this is an internal CLI package (v0.1.0, Alpha maturity), so blast radius is minimal.

### Rollout Risks

- **CLI-005 (formatting drift):** The drift affects services/downloader.py (1219 lines). Applying ruff format produces a large diff that obscures semantic review. Recommend separating formatting from logic changes in commits.
- **CLI-003 + CLI-005 (scaffolding exclusion):** Both recommend excluding .temp/ and .ai/ from ruff. If the exclude is too broad (e.g., .ai/), it may suppress lint errors in legitimate project-config files under .kilo/. Recommend targeted exclude: extend-exclude = [.temp, .ai/builders], not a blanket .ai exclusion.

### Dependency Risks

- **CLI-004 blocks CLI-001/CLI-002:** The entry layer imports utils/correlation.py (cli.py:29). Until the mypy gate is restored, new code cannot be type-checked cleanly. Fix CLI-004 first.
- **CLI-003 + CLI-005 share the [tool.ruff] exclude config change.** Apply once; resolves .temp/ and .ai/ offenders in both. Source/test file fixes (F841 in test_correlation.py, formatting in downloader.py/test_cli.py) remain independent.

### Documentation Inconsistencies

- **api-reference.md vs vkdownloader-overview.md vs cli-reference-clean.md:** Three docs disagree on CookieSource.FILE behavior. api-reference.md:99 says NotImplementedError (stale); api-reference.md:656 says Rejected with ValueError (correct); vkdownloader-overview.md:63 says NotImplementedError (stale); cli-reference-clean.md:67 says file not implemented (vague); cli-reference-clean.md:198 says Raising ValidationError at construction (correct). Code raises ValueError which Pydantic converts to ValidationError. Tracked under CLI-006 and CLI-007.

## Required Fixes

1. **CLI-003:** Remove the unused full variable at tests/test_correlation.py:28 (or restore the truncation assertion). Add extend-exclude = [.temp, .ai/builders] under [tool.ruff] in pyproject.toml.
2. **CLI-004:** Remove the # type: ignore[no-any-return] comment at correlation.py:55.
3. **CLI-005:** Run ruff format on the 7 drifted files (or ruff format .). Apply the same extend-exclude from CLI-003.
4. **CLI-006:** Remove FILE = file from the CookieSource enum (enums.py:50) and the now-dead validate_cookie_source branches (config.py:149-156), OR implement file-based cookie loading. Update --cookie-source help text in cli.py if needed.
5. **CLI-007:** Refresh docs -- update STRUCT.md, overview line counts + module list, remove HttpClient and ProgressManager.get_progress entries, correct CookieSource.FILE semantics, annotate research doc.

## Advisory Recommendations

1. **CLI-001:** Extract batch orchestration (ConcurrencyTracker, _TrackedSemaphore, DownloadContext, _download_single, _run_batch_with_progress, _print_batch_summary, progress helpers) into services/batch_downloader.py with a run_batch(...) async entry point. Reduce Typer handlers to argument parsing -> service call -> result/error presentation.
2. **CLI-002:** Expose public helpers (is_valid_video_url / VideoUrl.parse on extractor, format_validation_error on config, sanitize_url_for_log on url_sanitizer). Replace _map_exception_to_status(e) at cli.py:262 with e.status_label() or a documented fallback. Remove all private-symbol imports from cli.py.
3. **CLI-006 (if FILE kept as placeholder):** Reject file at the Typer enum-parsing layer rather than deferring to Settings construction.
4. **CLI-005:** Add a pre-commit hook (.pre-commit-config.yaml) running ruff check, ruff format --check, and mypy to prevent future gate drift.
5. **CLI-007:** Consider generating STRUCT.md from the actual src/vkdownloader/ tree so it stays in sync automatically.

---

## Validator Attestation

All seven findings were validated against the live codebase by:

- Executing uv run ruff check (3 errors confirmed -- CLI-003)
- Executing uv run ruff format --check (7 files drifted confirmed -- CLI-005)
- Executing uv run mypy src/vkdownloader (1 error at correlation.py:55 confirmed -- CLI-004)
- Executing uv run mypy src/vkdownloader/cli.py (passes in isolation -- CLI-004 masking confirmed)
- Executing uv run pytest (325 passed, 23 in test_cli.py -- runtime verification confirmed)
- Executing python -m vkdownloader download --help and batch --help (advertises [none|browser|file] -- CLI-006 confirmed)
- Reading and verifying every cited source file and line range (cli.py, exceptions.py, config.py, enums.py, correlation.py, url_sanitizer.py, extractor.py, downloader.py, __main__.py, concurrency.py)
- Reading and verifying every cited doc file (STRUCT.md, vkdownloader-overview.md, api-reference.md, cli-reference-clean.md, error-handling-logging-research-2025-2026.md)
- Verifying non-existence of documented-but-missing APIs via Python introspection (dir(ProgressManager) shows only clear, get_formatted_progress, update, update_sync; import of infrastructure.http_client fails with ModuleNotFoundError)

**Conclusion:** All 7 findings are real, current, and correctly scoped. 4 are validated unchanged in type; 3 are reclassified from RUNTIME-ERROR to SPEC-DEVIATION (non-standard type). No findings rejected. No cross-phase conflicts (this is the sole phase validated). Rollout ordering and dependencies are documented in the Rollout Analysis and Execution Validation sections.

---

*Generated by: validator role -- .kilo/agents/validator.md*
*Source findings: .ai/audit/01-audit-cli/findings.md*
*Report: .ai/audit/99-validation/01-audit-cli-validated-findings.md*
