---
name: 02-audit-config-validated-findings
description: Validator-validated findings for Phase 02 (Configuration & Settings Models)
agent: validator
---

# Phase 02 Audit Findings (Validated) — Configuration & Settings Models

**Executor:** auditor (Senior architecture auditor)
**Validator:** validator (conservative, evidence-driven)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/02-audit-config.md
**Status:** complete
**Validated:** yes
**Problems-only:** yes (passing checks are omitted per phase output mode)

## Validation Methodology

Per .kilo/commands/audit/phases/99-audit-validate.md, each finding was validated against:

1. Source code (src/vkdownloader/config.py, src/vkdownloader/cli.py, src/vkdownloader/models/enums.py)
2. Tests (tests/test_config.py, tests/test_cli.py)
3. Documentation (docs/11-guides/configuration.md, docs/01-tools/vkdownloader-overview.md, docs/01-tools/api-reference.md, docs/99-reference/cli-reference.md, docs/01-tools/installation.md)
4. Actual runtime behavior - re-executed the auditor R1 scenarios with pydantic-settings 2.14.2 / pydantic 2.13.4 (Python 3.12)

### Environment

- pydantic-settings: 2.14.2
- pydantic: 2.13.4
- Ruff: ruff check src/vkdownloader/ -> all checks passed; ruff format --check src/vkdownloader/ -> flags services/downloader.py only
- mypy src/vkdownloader/ -> 1 error at utils/correlation.py:55 (unused type:ignore); config.py and cli.py are mypy-clean
- pytest: 325 total passed (Phase 01 record); config+CLI subset: 40 passed

---

## Runtime Verification Records (confirmed)

| Step | Command | Result |
|------|---------|--------|
| R1 | Instantiate Settings with valid/invalid/edge data | Confirmed. .env typo VKDOWNLOADER_MAXRETRIES=9 -> ValidationError (extra_forbidden); warn_unknown_env_vars() returns []; OS-env typo -> silently ignored, default 3 used, helper returns [VKDOWNLOADER_MAXRETRIES]; .env valid override MAX_RETRIES=5 -> loaded (proves .env IS read; failure is the unknown key, not loading) |
| R2 | Load sample/test config through reader | Confirmed. No shipped .env or init/scaffold command exists; config is .env + VKDOWNLOADER_* env vars only |
| R3 | uv run ruff check src/vkdownloader/ | Confirmed. Passed (0 errors). ruff format --check src/vkdownloader/ flags services/downloader.py (pre-existing, outside config scope). uv run mypy src/vkdownloader/ reports 1 error in utils/correlation.py:55 (unused type:ignore) -- unrelated to config; config.py/cli.py are mypy-clean |
| R4 | uv run pytest (full suite; focus: tests/test_config.py + tests/test_cli.py) | Confirmed. 40 passed (config+CLI focus) |

> Note: .gitignore:28 ignores .env; no .env or example template is committed, so there is no secret-leakage surface to report in this phase (template/secret checks pass -> omitted).

---

## Findings

### CFG-001: .env-file unknown-variable typos raise an opaque ValidationError and bypass the documented typo guard

> **Validation Note:**
> - **Action:** validated (reclassified)
> - **Detail:** Empirically confirmed with pydantic-settings 2.14.2. A .env file containing a typo key (VKDOWNLOADER_MAXRETRIES=9) causes Settings() to raise ValidationError with [type=extra_forbidden], because extra='forbid' (config.py:162) does reject unknown keys sourced from the .env file. Meanwhile warn_unknown_env_vars() (config.py:176-202) scans os.environ only and returns [] for .env-sourced typos, so the helper cannot detect them. By contrast, an identical typo set in the OS environment (os.environ['VKDOWNLOADER_MAXRETRIES']='9') is silently ignored (default used) and IS caught by warn_unknown_env_vars(). The docs (config.py:19-26 docstring, config.py:179-183 warn_unknown_env_vars docstring, configuration.md:171-175) inaccurately state that all misspelled VKDOWNLOADER_* env vars are "silently ignored / silently dropped" -- this is true only for OS env vars, not .env file vars. Since .env is the documented primary configuration method (installation.md:104), the doc/code mismatch is a real deviation. Per type-specific rule "if code is better than docs -> reclassify as DOC-UPDATE": the code's fail-fast behavior for .env typos is acceptable, but the docs/docstring describing it are wrong -> the SPEC-DEVIATION portion is reclassified as DOC-UPDATE. The BEST-PRACTICE recommendations (extend typo guard to .env; surface valid names + "did you mean" on extra_forbidden) remain valid code improvements.
> - **See also:** CLI-006 (Phase 01) shares overlap on .env/config error presentation; no conflict.

| Field | Value |
|(originally)| — |
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | DOC-UPDATE, BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py, src/vkdownloader/cli.py, docs/11-guides/configuration.md |
| **Classification** | advisory |

**Description:** The Settings model sets extra='forbid' and ships warn_unknown_env_vars() to catch VKDOWNLOADER_* typos before construction. The docstrings (config.py:19-26, config.py:179-183) and configuration.md ("Environment Variable Caveats", configuration.md:171-175) state that misspelled VKDOWNLOADER_* variables are "silently ignored / silently dropped and the default is used," with the warning helper as the detection path. This is accurate ONLY for OS environment variables. For the .env file, extra='forbid' actually REJECTS unknown keys -- Settings() raises a hard ValidationError -- and warn_unknown_env_vars() cannot see .env content at all (it scans os.environ only, config.py:193). Since .env is the documented primary configuration method (installation.md:104), a single typo yields a dead-end error with no list of valid names and no remediation hint.

**Evidence:** Runtime (R1), re-executed in a temp CWD with a .env file (pydantic-settings 2.14.2):

- OS-env typo -- VKDOWNLOADER_MAXRETRIES=9 set in os.environ: Settings() succeeds, max_retries == 3 (default silently used); warn_unknown_env_vars() returns ['VKDOWNLOADER_MAXRETRIES'] and logs a valid_vars hint. Behavior matches the docs.
- .env typo -- .env containing only VKDOWNLOADER_MAXRETRIES=9: os.environ before load is []; warn_unknown_env_vars() returns []; Settings() raises: ValidationError: vkdownloader_maxretries -> Extra inputs are not permitted [type=extra_forbidden]
- .env valid override -- .env containing VKDOWNLOADER_MAX_RETRIES=5: Settings().max_retries == 5 (proves .env IS loaded; the failure is the unknown key, not loading itself).
- Doc/code contradiction: config.py:19-26 / config.py:179-183 / configuration.md:171-175 all claim misspellings are "silently dropped, default used, warnable," but runtime shows .env typos are rejected outright and are unreachable by the warning helper.
- Aggravator: cli.py:47-67 _format_validation_error labels every field as Received: <redacted, and model_config sets hide_input_in_errors=True (config.py:164), so the CLI-facing message hides the offending value entirely.

**Recommendation:** Two complementary, advisory changes:
1. Make the pre-construction typo guard cover the .env file: parse the resolved .env (same key=value semantics pydantic-settings uses), strip the VKDOWNLOADER_ prefix, and compare against _build_valid_env_vars() so the existing valid_vars hint also fires for .env typos. It is already invoked before construction in cli.py:481/590.
2. Improve the extra_forbidden UX: on an extra-field error, surface the valid VKDOWNLOADER_* names (reuse _build_valid_env_vars()) and a nearest-match "did you mean" hint instead of the bare pydantic message.
3. Correct the docs (config.py:19-26, config.py:179-183, configuration.md:171-175) to state the true behavior: unknown OS-env vars are silently ignored (with warning); unknown .env keys raise ValidationError; advise users to inspect the .env file for typos.

Effort: medium. Priority: recommended.

---

### CFG-002: Empty-string download_dir raises an opaque path_type ValidationError (asymmetric with log_file)

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Empirically confirmed. Settings(download_dir='') raises ValidationError: download_dir -> Input is not a valid path for <class 'pathlib.Path'> [type=path_type] (input hidden by hide_input_in_errors=True, config.py:164). Settings(log_file='') instead succeeds with log_file=None (type NoneType). The asymmetry is real: the empty_string_to_none validator (config.py:112-117) maps "" -> None for both fields; None is valid for log_file (typed Path | None) but invalid for download_dir (typed Path), so the subsequent path_type coercion fails. Re-confirmed via env var: VKDOWNLOADER_DOWNLOAD_DIR="" -> identical path_type ValidationError. The inline comment at config.py:126-127 ("see CFG-001 ... when LOG_FILE is an empty string") misnames the field: LOG_FILE="" succeeds; DOWNLOAD_DIR="" is what crashes. No external doc claims different behavior, so this is a genuine code-consistency issue (BEST-PRACTICE/SPEC-DEVIATION), not a doc-vs-code mismatch. Recommendation is sound and low-risk (map "" to default or raise an actionable error). Settings.model_fields['download_dir'].default = Path.home() / "Downloads" / "vkdownloader" (config.py:76), available for the "use default" mapping.

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE, SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/config.py |
| **Classification** | advisory |

**Description:** The empty_string_to_none validator (config.py:112-117) converts "" -> None for BOTH download_dir and log_file. This is correct for log_file (typed Path | None, so None is valid). But download_dir is typed Path (non-optional), so None is not a valid path and the subsequent path_type coercion fails with an opaque message. The two path fields therefore handle an empty string asymmetrically: log_file degrades gracefully to "no file logging"; download_dir hard-fails. The inline comment at config.py:126-127 even misnames the field ("see CFG-001 ... when LOG_FILE is an empty string") -- in reality LOG_FILE="" succeeds while DOWNLOAD_DIR="" is what crashes.

**Evidence:** Runtime (R1), re-confirmed:
- Settings(download_dir="") -> ValidationError: download_dir -> Input is not a valid path for <class 'pathlib.Path'> [type=path_type] input=None (input hidden by hide_input_in_errors=True).
- Settings(log_file="") -> log_file=None, no error (type NoneType).
- Same via env: VKDOWNLOADER_DOWNLOAD_DIR="" -> identical path_type ValidationError.
- CLI-facing message (via CliRunner, download command with VKDOWNLOADER_DOWNLOAD_DIR=""): exit code 1, output: "Configuration error: one or more settings have invalid values. Check your .env file or VKDOWNLOADER_* environment variables: - download_dir: Input is not a valid path for <class 'pathlib.Path'> Received: <redacted> Fix the offending value(s) and try again."

**Impact:** A user who clears VKDOWNLOADER_DOWNLOAD_DIR (e.g. VKDOWNLOADER_DOWNLOAD_DIR= in .env, intending "use default") gets an opaque, redacted error pointing at download_dir with no indication that the value was the empty string. The natural expectation -- empty means "use default", consistent with how log_file="" already behaves -- is not met.

**Recommendation:** Unify empty-string handling for path fields and fix the misleading comment. Either:
- (preferred) Treat "" for download_dir as "use default" by mapping it to Settings.model_fields["download_dir"].default in the existing empty_string_to_none/path validator (mirrors log_file graceful None), optionally logging a debug note; OR
- raise an explicit, actionable error that names the variable (VKDOWNLOADER_DOWNLOAD_DIR), states the empty value was supplied, and suggests removing the line to use the default.

Either approach is strictly better than the current redacted path_type error. Also correct the inline comment at config.py:126-127 to reference download_dir, not LOG_FILE.

Effort: trivial. Priority: recommended.

---

### CFG-003: Docs misstate the exception for CookieSource.FILE and are internally inconsistent

> **Validation Note:**
> - **Action:** reclassified (SPEC-DEVIATION -> DOC-UPDATE)
> - **Detail:** Code at config.py:145-157 (validate_cookie_source) raises ValueError("CookieSource.FILE is not implemented..."), which pydantic surfaces as ValidationError at construction. Re-confirmed: Settings(cookie_source=CookieSource.FILE) -> ValidationError, loc ('cookie_source',), msg "CookieSource.FILE is not implemented. Use none or browser instead." tests/test_config.py:96-104 asserts the ValidationError and the message substring. The code is correct (a field validator raising ValueError/ValidationError is the idiomatic Pydantic pattern). The docs are the problem: vkdownloader-overview.md:63 claims "raises NotImplementedError"; api-reference.md:99 claims "Raises NotImplementedError"; while api-reference.md:656 (same doc) correctly states "Rejected with ValueError" -- an internal contradiction. Per type-specific rule "if code is better than docs -> reclassify as DOC-UPDATE": code is correct and idiomatic, docs are wrong -> reclassified to DOC-UPDATE. The FILE member remains in the CookieSource enum (enums.py:50) intentionally as an intent-documenting placeholder, so no code change is required.
> - **See also:** CLI-006 (Phase 01) -- same root cause (CookieSource.FILE documentation does not match code). CFG-003 is the narrow doc-only subset (exception type); CLI-006 additionally covers --help advertising file as a selectable option. Marked as merge candidate / shared root cause; no code conflict between findings.

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | src/vkdownloader/config.py, docs/01-tools/vkdownloader-overview.md, docs/01-tools/api-reference.md |
| **Classification** | advisory |

**Description:** config.py:145-157 validate_cookie_source raises ValueError("CookieSource.FILE is not implemented...") inside a pydantic field_validator, which pydantic surfaces as a ValidationError at construction. Two docs instead claim NotImplementedError is raised, and one of them (api-reference.md) contradicts ITS OWN enum table.

**Evidence:**
- Code: config.py:145-157 raises ValueError; runtime (R1) / test_config.py:96-104 confirm Settings(cookie_source=CookieSource.FILE) -> ValidationError, loc ('cookie_source',), msg "CookieSource.FILE is not implemented. Use none or browser instead."
- docs/01-tools/vkdownloader-overview.md:63: "file is not implemented and raises NotImplementedError"
- docs/01-tools/api-reference.md:99: "When cookie_source=FILE: Raises NotImplementedError (not implemented)"
- docs/01-tools/api-reference.md:656 (same doc, its own CookieSource table): "FILE ... Rejected with ValueError. Not implemented" -- i.e. api-reference.md contradicts itself.

**Recommendation:** Update overview.md:63 and api-reference.md:99 to state that CookieSource.FILE is rejected at construction with a ValidationError (backed by ValueError in validate_cookie_source), matching api-reference.md:656. Keep file in the CookieSource enum (it documents intent and the validator message) but ensure all references agree on the exception type.

Effort: trivial. Priority: recommended.

---

### CFG-004: configuration.md implies --max-retries is available for the single download command, but it is batch-only

> **Validation Note:**
> - **Action:** reclassified (SPEC-DEVIATION -> DOC-UPDATE)
> - **Detail:** Code confirms the download command (cli.py:418-445) exposes options url, quality, output, method, cookie_source, ssl_verify -- there is no --max-retries option. Only batch_download() (cli.py:542-581) defines --max-retries / -r (cli.py:576-581). Meanwhile cli-reference.md:121 correctly scopes --max-retries to the batch command only. The discrepancy is entirely in configuration.md:105-117, which lists "CLI Flag: --max-retries / -r" alongside "Applies to single downloads as well as batch downloads" without qualifying the flag is batch-scoped. Per type-specific rule "if code is better than docs -> reclassify as DOC-UPDATE": the code is correct (setting applies via env var to single downloads; the CLI flag is batch-only), the doc is misleading -> reclassified to DOC-UPDATE. The max_retries setting (env var VKDOWNLOADER_MAX_RETRIES) does apply to single downloads via Settings() construction, so the underlying behavior claim is half-right; only the CLI-flag scoping text is wrong.

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | docs/11-guides/configuration.md, src/vkdownloader/cli.py, docs/99-reference/cli-reference.md |
| **Classification** | advisory |

**Description:** configuration.md documents max_retries with a CLI Flag: --max-retries / -r and text "Applies to single downloads as well as batch downloads," without qualifying that the flag is batch-only. The single download command exposes no --max-retries option, so a user following the guide and running vkdownloader download URL --max-retries 5 hits a Typer "no such option" error. (The max_retries setting does apply to single downloads via the VKDOWNLOADER_MAX_RETRIES env var -- only the CLI flag is batch-scoped.)

**Evidence:**
- src/vkdownloader/cli.py: download() (cli.py:418-445) options are url, quality, output, method, cookie_source, ssl_verify -- no --max-retries. Only batch_download() (cli.py:542-581, option at cli.py:576-581) defines --max-retries / -r.
- docs/11-guides/configuration.md:105-117: lists CLI Flag: --max-retries / -r and "Applies to single downloads as well as batch downloads."
- docs/99-reference/cli-reference.md:121 correctly scopes --max-retries to the batch command only.

**Recommendation:** Clarify in configuration.md that --max-retries is a batch-only CLI flag and that single-download retry behavior is configured via the VKDOWNLOADER_MAX_RETRIES environment variable. Optionally consider whether the single download command should gain a --max-retries override for parity (design decision, not mandated).

Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 (CFG-001) |
| MEDIUM | 1 (CFG-002) |
| LOW | 2 (CFG-003, CFG-004) |

## Mandatory Fixes

_No findings classified as mandatory. All findings fail fast (no data loss / no silent insecure config): CFG-001's .env typo does raise (not silently misconfigure), and CFG-002's empty download_dir raises a ValidationError (caught and surfaced by the CLI)._

## Advisory Recommendations

- **CFG-001 (HIGH / DOC-UPDATE + BEST-PRACTICE):** Extend the typo guard (warn_unknown_env_vars) to also scan the resolved .env file, and improve the extra_forbidden message to list valid VKDOWNLOADER_* names / suggest nearest match; correct docs/docstring to reflect that .env typos raise (not silently-ignored) while OS-env-var typos are silently ignored. [SUPPORTS] operational reliability of the primary config path.
- **CFG-002 (MEDIUM / BEST-PRACTICE):** Make empty-string handling consistent across path fields (treat download_dir="" as "use default", as log_file="" already degrades gracefully); fix the config.py:126-127 comment that misnames the crashing field. [BEST-PRACTICE] config robustness / UX.
- **CFG-004 (LOW / DOC-UPDATE):** Document that --max-retries is batch-only and that single-download retries use VKDOWNLOADER_MAX_RETRIES. [DOC-UPDATE] clarity.

## Doc Updates Needed

- **CFG-001:** config.py docstring (lines 19-26, 179-183) and docs/11-guides/configuration.md ("Environment Variable Caveats", 171-175) -- state the true .env vs OS-env-var behavior.
- **CFG-003:** docs/01-tools/vkdownloader-overview.md:63 and docs/01-tools/api-reference.md:99 -- CookieSource.FILE raises ValidationError (not NotImplementedError); align with api-reference.md:656.
- **CFG-004:** docs/11-guides/configuration.md:105-117 -- scope --max-retries to the batch command.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 1 | CFG-002 |
| Reclassified | 3 | CFG-001 (SPEC-DEVIATION -> DOC-UPDATE, kept BEST-PRACTICE), CFG-003 (SPEC-DEVIATION -> DOC-UPDATE), CFG-004 (SPEC-DEVIATION -> DOC-UPDATE) |
| Merged | 0 | -- |
| Rejected | 0 | -- |

### Rejected Findings

_None._ All four findings are technically correct, currently applicable, and architecturally sound. Each was empirically re-verified against the running codebase (pydantic-settings 2.14.2).

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| CFG-003 | CLI-006 (Phase 01) | Same root cause: CookieSource.FILE documentation does not match code (ValueError/ValidationError, not NotImplementedError). CFG-003 is the narrow doc-only subset; CLI-006 additionally covers --help advertising file as selectable. Kept separate per-phase but flagged as shared root cause. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CFG-001 | SPEC-DEVIATION, BEST-PRACTICE | DOC-UPDATE, BEST-PRACTICE | Code behavior is correct/acceptable (fail-fast for .env typos); docs/docstring inaccurately claim all env-var typos are silently ignored. Code is better than docs -> DOC-UPDATE. BEST-PRACTICE (extend typo guard, improve error UX) retained. |
| CFG-003 | DOC-UPDATE, SPEC-DEVIATION | DOC-UPDATE | Code correctly raises ValueError/ValidationError; docs wrongly claim NotImplementedError and contradict themselves. Code is correct -> DOC-UPDATE. |
| CFG-004 | DOC-UPDATE, SPEC-DEVIATION | DOC-UPDATE | Code is correct (download command has no --max-retries); configuration.md misleadingly implies otherwise. Code is better than docs -> DOC-UPDATE. |

## Rollout Analysis

**Risks:** None. All four findings are advisory (non-mandatory). CFG-001 and CFG-002 involve small, isolated code changes; CFG-003 and CFG-004 (reclassified) are doc-only fixes requiring no code changes and zero execution risk.

**Dependencies:** Independent. CFG-001 (typo guard + doc fix), CFG-002 (path handling + comment), CFG-003 (doc exception type), and CFG-004 (doc flag scoping) touch disjoint code/docs with no inter-dependency. No circular dependencies.

**Sequencing:** No ordering constraint. Doc fixes (CFG-003, CFG-004) can land first with no code risk; code changes (CFG-001, CFG-002) are independent of each other. All four can be applied in any order.

**Backward compatibility:** CFG-001 recommendation #3 (doc corrections) is purely descriptive. CFG-001 recommendations #1-#2 and CFG-002 recommendation change user-facing error messages only (error paths, not success paths); no API/CLI contract change. No migration needed.

## Execution Validation

**Applicability & readiness:**
- CFG-001: Targets warn_unknown_env_vars() (config.py:176), _build_valid_env_vars() (config.py:171), _format_validation_error() (cli.py:47), and model_config (config.py:159). All targets confirmed to exist and match line references. Ready.
- CFG-002: Target empty_string_to_none validator (config.py:112-117), expand_tilde_paths (config.py:119-131), download_dir field (config.py:75-78), log_file field (config.py:107-110). All confirmed. Ready.
- CFG-003: Targets doc files only (vkdownloader-overview.md:63, api-reference.md:99). Code (config.py:145-157, enums.py:50) confirmed unchanged. Ready.
- CFG-004: Targets doc file only (configuration.md:105-117). Code (cli.py:418-445, cli.py:542-581, cli-reference.md:121) confirmed. Ready.

No stale assumptions, no drifted dependencies, no architectural integrity risk.

## Warnings

- **Documentation inconsistency (CFG-001):** The Settings class docstring (config.py:19-26) and warn_unknown_env_vars docstring (config.py:179-183) both state that extra='forbid' "only applies to explicit kwargs passed to the model constructor, not to environment variables." Runtime testing disproves this for .env-sourced variables (they ARE rejected). This docstring is actively misleading to maintainers and should be corrected alongside the user-facing docs.
- **Cross-phase overlap (CFG-003 / CLI-006):** Phase 01 CLI-006 and Phase 02 CFG-003 address the same CookieSource.FILE documentation defect from different angles. Recommend consolidating the doc fixes to avoid duplicate effort and ensure consistent wording.
- **Opaque error UX (CFG-001 / CFG-002):** hide_input_in_errors=True (config.py:164) combined with _format_validation_error hardcoding "Received: <redacted>" (cli.py:65) means users cannot see the offending value for any configuration error, increasing support friction for typo diagnosis.
- **Latent test gap:** No test currently covers .env-file typo behavior or download_dir="" empty-string behavior. Adding pytest cases for both (using tmp_path + monkeypatch.chdir) would lock in the verified behavior and guard against regressions.
