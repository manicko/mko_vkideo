# Phase 02 Audit Findings — Configuration & Settings Models (VALIDATED)

**Executor:** auditor (poolside/laguna-m.1:free)
**Validator:** validator (poolside/laguna-m.1:free)
**Template:** `.ai/audit/templates/audit-findings.md`
**Source findings:** `.ai/audit/02-audit-config/findings.md`
**Status:** complete
**Validated:** yes

> Validator note: this file is a verified copy of the source findings with inline validation
> decisions applied. It is self-contained. Validation was performed against the working tree at
> `C:\py_exp\mko_vkideo` on 2026-08-05, Python 3.12, pydantic 2.13.4 / pydantic-settings 2.14.2.

---

## Validation Methodology

1. **Source** — read `src/vkdownloader/config.py`, `cli.py`, `models/enums.py`,
   `services/extractor.py`, `services/downloader.py`.
2. **Docs** — read `.env`, `.gitignore`, `docs/01-tools/installation.md`,
   `docs/01-tools/api-reference.md`, `docs/11-guides/configuration.md`,
   `docs/99-reference/cli-reference-clean.md`.
3. **Runtime evidence** — reproduced the auditor's R1/R2 probes and additionally exercised the real
   CLI via Typer `CliRunner` (`vkdownloader download` / `vkdownloader batch`) with
   `VKDOWNLOADER_LOG_FILE=` set to an empty string.
4. **Verification suite** — `pytest` (248 passed), `ruff check src/` (all passed),
   `mypy src/vkdownloader/` (no issues in 23 files). All match audit R3/R4.
5. **Cross-phase** — compared against Phase 01 (CLI) findings; one consistency note (CFG-001 vs CLI-003).

### Decision legend

- **[VALIDATED]** Root cause verified against current code; recommendation stands unchanged.
- **[RECLASSIFIED]** Valid, but `Type` adjusted: code-is-better-than-docs -> `DOC-UPDATE`.
- **[KEEPS]** Hybrid finding retained because both code and docs deviate.

### Validation-rule for SPEC-DEVIATION findings

Applied verbatim: "Determine whether code should change or docs should change. If code is better than
docs -> reclassify as DOC-UPDATE. If docs are better than code -> keep as spec deviation."

---

## Findings

### CFG-001: Empty string env var for `log_file`/`download_dir` resolves to CWD, not None  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Validation Status** | VALIDATED (impact wording corrected — see note) |
| **Affected Modules** | `config.py` (112-117, 140-145), `cli.py` (461-464, 505-508, 598-600), `installation.md` (124) |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** validated (root cause confirmed; impact wording corrected).
> - **Detail:** Verified empirically: `VKDOWNLOADER_LOG_FILE=` -> `Path("")` -> `expanduser().resolve()` ->
>   CWD, bypassing the `if v is None` guard (`config.py:115-116`). `setup_logging()` then constructs
>   `logging.FileHandler(CWD)` (`config.py:214`), raising an `OSError` subclass. The auditor wrote
>   `IsADirectoryError`; on POSIX that is accurate; on Windows the verified exception is
>   `PermissionError: [Errno 13] Permission denied: 'C:\py_experiment\mko_vkideo'` (both are
>   `OSError` subclasses). Not caught by the narrow `try/except OSError` around `mkdir`
>   (`config.py:201-206`) because `FileHandler` is instantiated outside that block (`config.py:214`).
> - **Impact correction:** The finding says "the exception propagates up and crashes the CLI." In the
>   current CLI the exception is *caught*: `download` catches it via `except Exception` (`cli.py:505`,
>   -> traceback + "An error occurred during download", exit 1); `batch` catches it via `except OSError`
>   (`cli.py:598`, -> misleading "Failed to read URL file: .env -- PermissionError", exit 1). Verified by
>   running the real CLI (CliRunner). Net outcome: a **startup failure with exit code 1 and a confusing
>   traceback (download) / misleading message (batch)** when following the documented `installation.md:124`
>   example — not an unhandled traceback, but still a broken startup, justifying HIGH/mandatory priority.
> - **Cross-phase:** see CLI-003 (Phase 01), which documents `download`'s catch-all and `batch`'s
>   narrower `except OSError`.
> - **Fix refinement:** empty-string->None is correct and safe for `log_file` (`Path | None`). For
>   `download_dir` (non-optional `Path`) the same transform yields None -> pydantic ValidationError
>   (fail-fast). See Rollout Analysis for the behavior decision.
> - **See also:** CFG-007 (Phase 02).

**Description:** (source finding — reproduced for self-containment). The `Settings` model declares
`log_file: Path | None` and `download_dir: Path` with an `expand_tilde_paths` field validator
(mode="after") that calls `v.expanduser().resolve()`. When an environment variable or `.env` value is
an empty string (e.g., `VKDOWNLOADER_LOG_FILE=`), pydantic-settings coerces the empty string to
`Path("")` (equivalent to `Path(".")`), which is not `None`. The validator's `if v is None` guard is
bypassed, and `Path("").expanduser().resolve()` resolves to the current working directory. This means
an empty `VKDOWNLOADER_LOG_FILE=` value — shown as a copy-pasteable example at `installation.md:124` —
produces a `log_file` pointing at a directory, not `None`. When `setup_logging()` (config.py:196-216)
is called, it passes that CWD path to `logging.FileHandler()` (`config.py:214`), which raises an
`OSError` because a directory cannot be opened as a file. This error is not caught by the
`try/except OSError` around `mkdir()` (`config.py:201-206`) because `FileHandler` is created outside it.

**Evidence:** (verified)
```text
VKDOWNLOADER_LOG_FILE=''  ->  Settings().log_file == WindowsPath('C:/py_experiment/mko_vkideo')  (CWD, not None)
Settings().log_file is None  ->  False
setup_logging(settings) -> PermissionError: [Errno 13] Permission denied: 'C:\py_experiment\mko_vkideo'
                             at logging.FileHandler(settings.log_file)  ->  config.py:214
Real CLI (CliRunner):
  download: exit_code=1, caught by except Exception (cli.py:505) -> traceback + "An error occurred during download"
  batch:    exit_code=1, caught by except OSError (cli.py:598) -> "Failed to read URL file: .env — PermissionError"
```
Validator (`config.py:112-117`):
```python
@field_validator("download_dir", "log_file", mode="after")
@classmethod
def expand_tilde_paths(cls, v: Path | None) -> Path | None:
    if v is None:
        return v
    return v.expanduser().resolve()
```
`Path("")` is not `None`, so the guard is skipped. Same for `download_dir`.

**Recommendation (confirmed):** Add a `mode="before"` validator (following the existing pattern at `validate_cookie_source`, config.py:126-138) that converts empty strings to `None` for both `log_file` and `download_dir` **before** pydantic coerces them to `Path`. For `download_dir` specifically: an empty `VKDOWNLOADER_DOWNLOAD_DIR=` should produce a `ValidationError` (fail-fast), consistent with the project's `validate_cookie_source` pattern that rejects invalid `CookieSource.FILE` at construction (config.py:126-138) and the `extra='forbid'` configuration. The `ValidationError` is caught by `cli.py:475` (`except ValidationError as e:`) and rendered via `_format_validation_error`, giving the user a clear error message. This avoids the silent fall-back to CWD (current behavior) and aligns with the project's fail-fast convention for misconfigured settings. Effort: trivial. Priority: mandatory.

**Effort:** trivial · **Priority:** mandatory — startup failure when following the documented example.

### CFG-002: `.env` template file missing `headless` setting  [RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Validation Status** | RECLASSIFIED from SPEC-DEVIATION |
| **Affected Modules** | `.env` (root), `config.py` (29-32), `configuration.md` (23, 49-53), `installation.md` (111) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified (code correct; template stale).
> - **Detail:** `Settings.headless` (config.py:29-32, default `False`) is defined and documented
>   (`configuration.md:23,49-53`; `installation.md:111`). The `.env` template omits
>   `VKDOWNLOADER_HEADLESS` (verified by reading the 31-line `.env`). Code is better than the template.
> - **See also:** CFG-007 — note `installation.md:111` *does* include headless (docs are internally
>   inconsistent: installation example has it, `.env` template does not).

**Description:** The `.env` file at the repository root serves as a local config template with all
settings commented out, but it does not include a `VKDOWNLOADER_HEADLESS` entry, despite `headless`
being a valid `Settings` field (config.py:29-32, default `False`), documented in `configuration.md:23`
and `installation.md:111`.

**Evidence:** `.env` root (read in full) contains no `VKDOWNLOADER_HEADLESS`. `Settings.model_fields`
includes `headless`:
```python
headless: bool = Field(default=False, description="Run browser in headless mode (no GUI)")
```

**Recommendation:** Add a commented-out `VKDOWNLOADER_HEADLESS` entry to the `.env` template.
**Effort:** trivial · **Priority:** recommended

---

### CFG-003: API reference shows wrong `throttled_rate` default (100000 vs 10000)  [RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Validation Status** | RECLASSIFIED from SPEC-DEVIATION |
| **Affected Modules** | `api-reference.md` (852), `installation.md` (119), `config.py` (86) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified (code correct; docs stale).
> - **Detail:** Default is `10000` (verified at runtime: `Settings().throttled_rate == 10000`),
>   matching `configuration.md:34` and the `.env` template. Only `api-reference.md:852` (`100000`) and
>   `installation.md:119` (`100000`) are wrong.
> - **See also:** CFG-007 overlaps on `installation.md:119`.

**Evidence:** Code (`config.py:85-89`, verified):
```python
throttled_rate: int = Field(default=10000, ge=1000, le=1000000, description="...yt-dlp will abort below this threshold.")
```
Runtime: `Settings().throttled_rate` -> `10000`. API ref (`api-reference.md:852`): `100000`.
Installation (`installation.md:119`): `VKDOWNLOADER_THROTTLED_RATE=100000`. Config guide
(`configuration.md:34`): `10000`.

**Recommendation:** Update `api-reference.md:852` and `installation.md:119` to `10000`.
**Effort:** trivial · **Priority:** recommended

---

### CFG-004: API reference missing `browser_pre_interaction_wait` and `browser_post_interaction_wait`  [RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Validation Status** | RECLASSIFIED from SPEC-DEVIATION |
| **Affected Modules** | `api-reference.md` (840-856), `config.py` (57-68), `extractor.py` (220-222) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified (code correct; docs incomplete).
> - **Detail:** Both fields exist (config.py:57-68), are consumed by `extractor.py:220,222`, and are
>   documented in `configuration.md:27-28`. Verified defaults: `5` and `8`. The `api-reference.md`
>   settings table omits both rows.

**Evidence:** Code (config.py:57-68, verified):
```python
browser_pre_interaction_wait: int = Field(default=5, ge=1, le=30, ...)
browser_post_interaction_wait: int = Field(default=8, ge=1, le=30, ...)
```
Consumer (extractor.py:220-222, verified):
```python
await asyncio.sleep(self.settings.browser_pre_interaction_wait)
await self._simulate_video_interaction(page)
await asyncio.sleep(self.settings.browser_post_interaction_wait)
```

**Recommendation:** Add both rows (default `5`/`8`, range 1-30) to the API reference settings table.
**Effort:** trivial · **Priority:** recommended

---

### CFG-005: `.env` template lists `file` as valid `cookie_source` option but code rejects it  [RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Validation Status** | RECLASSIFIED from SPEC-DEVIATION |
| **Affected Modules** | `.env` (line 26), `config.py` (97-99, 126-138), `enums.py` (49) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified (code correct/intentional; template stale).
> - **Detail:** `CookieSource.FILE` exists in the enum but `validate_cookie_source` rejects it at
>   construction (config.py:126-138). The `.env` line 26 lists `file` as valid, contradicting the code.
>   Verified: `VKDOWNLOADER_COOKIE_SOURCE=file` -> `ValidationError: CookieSource.FILE is not
>   implemented`. The field description itself (config.py:99) already says "file not implemented"; only
>   the `.env` comment is stale.

**Evidence:** Enum (enums.py:45-50, verified). Validator (config.py:126-138, verified). Runtime:
`VKDOWNLOADER_COOKIE_SOURCE=file` -> `ValidationError: CookieSource.FILE is not implemented. Use
'none' or 'browser' instead.` `.env` line 26: `# Cookie Source (none, browser, file) - controls browser launch for cookies`.

**Recommendation:** Update the `.env` template comment to `(none, browser)` only.
**Effort:** trivial · **Priority:** recommended

---

### CFG-006: `CookieSource.FILE` documentation is inconsistent across docs + unreachable `NotImplementedError`  [KEEPS — SPEC-DEVIATION]

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Validation Status** | VALIDATED (hybrid: docs-wrong AND dead code) |
| **Affected Modules** | `configuration.md` (66), `cli-reference-clean.md` (198), `config.py` (126-138), `extractor.py` (129-132), `cli.py` (461) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (kept as SPEC-DEVIATION).
> - **Detail:** All sub-claims verified:
>   1. `configuration.md:66` says FILE "raises NotImplementedError" — false; actual is
>      `ValidationError` (config.py:126-138), confirmed at runtime and by
>      `tests/test_extractor.py:289-294` (asserts construction-time rejection).
>   2. `cli-reference-clean.md:198` says "future enhancement" — contradicts the rejection.
>   3. `extractor.py:129-132` (`if self.settings.cookie_source == CookieSource.FILE: raise
>      NotImplementedError(...)`) is **unreachable** in normal flow: the validator blocks `FILE` at
>      construction, so a validly-built `Settings` never carries `cookie_source == FILE`.
>      `extract_streams_with_cookies` is reachable (downloader.py:539,688; segment_downloader.py:389),
>      but the FILE branch is dead. CLI `--cookie-source file` -> `CookieSource.FILE` -> validator
>      raises `ValidationError` -> caught at `cli.py:473`, never reaching the extractor.
> - **Rationale:** Both code (dead branch) and docs (wrong exception type) deviate -> not a pure
>   DOC-UPDATE. Retained.
> - **See also:** CFG-005 (Phase 02) shares the `CookieSource.FILE` root cause; separate because it
>   targets the `.env` comment, not the cross-doc inconsistency + dead code.

**Recommendation:** Remove the unreachable `NotImplementedError` branch at `extractor.py:129-132` (the `validate_cookie_source` validator at config.py:126-138 already rejects `CookieSource.FILE` at construction, making this branch dead code). Retain the `CookieSource.FILE` enum value in `enums.py:49` for forward compatibility. Update the `.env` template comment (line 26) to list only `(none, browser)` to match the validator. Align `configuration.md:66` and `cli-reference-clean.md:198` to state `ValidationError` is raised at construction (not `NotImplementedError`). Effort: small. Priority: recommended.
**Effort:** small · **Priority:** recommended

### CFG-007: Installation `.env` example is incomplete, has wrong `throttled_rate`, and contains empty `LOG_FILE`  [RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | CFG-007 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Validation Status** | RECLASSIFIED from SPEC-DEVIATION |
| **Affected Modules** | `installation.md` (106-125), `config.py` (defaults) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified (defaults correct; example wrong).
> - **Detail:** Defaults verified correct (`throttled_rate=10000`, `headless` exists, etc.). The
>   `installation.md:106-125` example is wrong/incomplete (verified by direct read): missing the three
>   browser/cookie fields, `throttled_rate=100000`, and empty `VKDOWNLOADER_LOG_FILE=`.
> - **Cross-finding:** sub-issue (3) is the same root cause as CFG-001. CFG-001 fixes the code
>   (validator); CFG-007 fixes the docs example (non-empty LOG_FILE). Complementary, independent.

**Evidence:** `installation.md:106-125` (verified): missing
`VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT` / `_POST_` / `VKDOWNLOADER_COOKIE_SOURCE`;
`VKDOWNLOADER_THROTTLED_RATE=100000`; `VKDOWNLOADER_LOG_FILE=` (empty, triggers CFG-001).

**Recommendation:** `throttled_rate=10000`; give `LOG_FILE` a concrete path; add the three missing
fields (commented).
**Effort:** trivial · **Priority:** recommended

---

### CFG-008: No tracked `.env.example` template for new users  [VALIDATED — BEST-PRACTICE]

| Field | Value |
|-------|-------|
| **ID** | CFG-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `.gitignore` (28), `.env` (gitignored), `installation.md` (102-125) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated.
> - **Detail:** `.gitignore:28` ignores `.env`. `Get-ChildItem -Force` of repo root confirms only
>   `.env` exists — no `.env.example`/`.env.template`/`.env.sample` anywhere. A tracked template is the
>   standard Python bootstrap pattern; low complexity, high onboarding value. Not rejected as
>   overengineering.

**Recommendation:** Create a tracked `.env.example` with all 16 settings (commented).
**Effort:** small · **Priority:** recommended

---

### CFG-009: CLI reference shows `ssl_verify` default as `verify` instead of `true`  [RECLASSIFIED]

| Field | Value |
|-------|-------|
| **ID** | CFG-009 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Validation Status** | RECLASSIFIED from SPEC-DEVIATION |
| **Affected Modules** | `cli-reference-clean.md` (68, 126), `cli.py` (406-410) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified (code correct; docs stale).
> - **Detail:** `ssl_verify` defaults to `True` (cli.py:406-410; verified
>   `Settings().ssl_verify is True`). `configuration.md:31` (`true`) and `api-reference.md:849`
>   (`True`) are correct; only `cli-reference-clean.md:68,126` show the invalid token `verify`.

**Recommendation:** Change `verify` -> `true` at `cli-reference-clean.md:68,126`.
**Effort:** trivial · **Priority:** recommended

---

### CFG-010: `throttled_rate` field description is misleading ("triggers re-extract")  [KEEPS — SPEC-DEVIATION]

| Field | Value |
|-------|-------|
| **ID** | CFG-010 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `config.py` (89), `api-reference.md` (852), `configuration.md` (34) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (kept as SPEC-DEVIATION).
> - **Detail:** The misleading text lives in the code (`Field(description=...)`, config.py:89), which
>   `api-reference.md:852` and `configuration.md:34` mirror. Because the *source of truth* (code
>   description) is itself wrong, this is not a doc-only fix. Verified: `throttledratelimit` is passed
>   to yt-dlp (downloader.py:174); re-extraction is a **separate** retry loop
>   `download_with_yydlp_with_resume_fallback` (downloader.py:455-491) -> `_attempt_segment_resume`
>   (fresh token). The description conflates yt-dlp's abort with the app's retry. Recommendation
>   accepted as accurate.

**Recommendation:** Rewrite the description to: "Minimum download rate in bytes/sec. If yt-dlp's
download rate falls below this threshold, yt-dlp aborts the download; the application then retries
with a fresh token re-extract. Default is 10000 (10KB/s)." Propagate to `api-reference.md:852` and
`configuration.md:34`.
**Effort:** trivial · **Priority:** recommended

---

## Runtime Verification Summary

| Step | Status | Details |
|------|--------|---------|
| R1 — Model instantiation | Pass | Defaults correct (`throttled_rate=10000`, `ssl_verify=True`, `headless=False`, waits=5/8, `cookie_source=NONE`); `FILE` rejected with `ValidationError`; unknown kwargs rejected (`extra='forbid'`). |
| R2 — Config loading | Pass (with bug) | Env vars load correctly. **Bug confirmed:** empty `VKDOWNLOADER_LOG_FILE=` -> CWD (not None); `setup_logging()` raises OSError (`PermissionError` Windows / `IsADirectoryError` POSIX) at `FileHandler` (config.py:214), uncaught by the mkdir guard. Real CLI: `download`->exit 1 via `except Exception`; `batch`->exit 1 via `except OSError` (misleading msg). |
| R3 — Linter | Pass | `ruff check src/` -> All checks passed; `mypy src/vkdownloader/` -> Success, 23 files. |
| R4 — Test suite | Pass | 248 passed (15 config tests). |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 6 |
| LOW | 3 |
| **Total** | **10** |

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | CFG-001, CFG-006, CFG-008, CFG-010 |
| Reclassified | 6 | CFG-002, CFG-003, CFG-004, CFG-005, CFG-007, CFG-009 — SPEC-DEVIATION -> DOC-UPDATE (code correct; docs/templates stale) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| _(none)_ | — | All findings verified against current code; none stale/duplicated/low-ROI/unsafe. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| _(none)_ | — | CFG-003 & CFG-007 overlap on `installation.md:119`; CFG-005 & CFG-006 share the `CookieSource.FILE` root cause. Retained separately (distinct artifacts/fix sites). |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CFG-002 | SPEC-DEVIATION | DOC-UPDATE | `headless` defined+documented; `.env` omits it. |
| CFG-003 | SPEC-DEVIATION | DOC-UPDATE | Default `10000` verified; only api-ref/installation show `100000`. |
| CFG-004 | SPEC-DEVIATION | DOC-UPDATE | Both wait fields defined+consumed+documented; api-ref omits. |
| CFG-005 | SPEC-DEVIATION | DOC-UPDATE | `file` rejection intentional; only `.env` lists it. |
| CFG-007 | SPEC-DEVIATION | DOC-UPDATE | Defaults correct; only `installation.md` example is wrong. |
| CFG-009 | SPEC-DEVIATION | DOC-UPDATE | Default `True` verified; only cli-ref shows `verify`. |

---

## Cross-Phase Analysis (Phase 01 CLI vs Phase 02 Config)

- **CFG-001 (config) <-> CLI-003 (CLI):** Resolved by evidence. CFG-001 claims the empty-LOG_FILE
  error "crashes the CLI"; CLI-003 documents that `download` has a catch-all `except Exception`
  (`cli.py:505`) and `batch` has `except OSError` (`cli.py:598`) but no catch-all. Verified by
  running the real CLI: the `PermissionError` is **caught** in both — not an unhandled traceback.
  The findings are therefore **consistent** (both accurately describe handler structure); only
  CFG-001's impact wording is overstated (corrected above).
- **Remediation independence:** CLI-003's catch-all fix improves diagnostics but does **not** fix
  CFG-001's root cause (empty string -> CWD). CFG-001 must be fixed at the root (validator). Order:
  CFG-001 first (root cause), CLI-003 second (defense-in-depth).
- **No conflicting runtime claims** between phases: R1-R4 summaries agree (248 tests pass,
  ruff/mypy clean, same default values).

## Rollout Analysis

- **CFG-001 (code root-cause fix):** Add a `mode="before"` validator mapping `""` -> `None` on
  `log_file` and `download_dir`, following the existing `validate_cookie_source` pattern (config.py:126-138).
  - `log_file` (`Path | None`): `""` -> `None` -> no `FileHandler` -> safe, backward-compatible
    (previously crashed).
  - `download_dir` (`Path`, non-optional, default `Path.home()/Downloads/vkdownloader`): `""` -> `None`
    -> pydantic `ValidationError` (fail-fast). This is a **behavior change** (silent CWD -> fail-fast
    config error caught at `cli.py:475` and shown via `_format_validation_error`). **Decision: fail-fast** —
    consistent with the project's existing `validate_cookie_source` rejection pattern (config.py:126-138)
    and the `extra='forbid'` convention. An empty `download_dir` is a misconfiguration, not a value to
    silently fall back. The `ValidationError` is user-facing via `_format_validation_error`. Not architecture-breaking.
- **CFG-006 (dead-code removal):** The unreachable `NotImplementedError` branch at `extractor.py:129-132`
  should be **removed** (not inert-marked), since the `validate_cookie_source` validator at config.py:126-138
  already blocks `CookieSource.FILE` at construction, making the branch truly dead. The `CookieSource.FILE`
  enum value is retained in `enums.py:49` for forward compatibility. Removal is safe — `tests/test_extractor.py:289-294`
  asserts construction-time rejection (not the extractor branch), so no test depends on it. The `.env` template
  comment (line 26) listing `file` as valid should be updated to `(none, browser)` to match the validator. Low risk.
- **Doc/template batch (CFG-002, 003, 004, 005, 007, 009, 010):** pure text changes, no runtime
  impact; can be applied together.
- **CFG-008 (`.env.example`):** additive, no runtime impact.
- **Circular/hidden dependencies:** none. CFG-001 and CFG-007 share the empty-LOG_FILE root cause but
  have independent fix sites (code validator vs. docs example).
- **Anchors:** all fixes target stable artifacts (field definitions, doc files, the validator, the
  dead branch) — no fragile line-only anchors.

## Execution Validation

- **Targets exist:** `config.py` validators, `.env`, `.gitignore`, `extractor.py:129-132`,
  `cli.py:505/598`, and all cited doc files are present (read-confirmed).
- **Plan not stale:** all findings reproduced against the current working tree (defaults, empty-string
  coercion, `CookieSource.FILE` rejection, dead branch) — codebase state matches the audit.
- **Architecture consistent:** fixes follow existing patterns (a `mode="before"` validator already
  exists for `cookie_source`/`log_level`; `.env` already uses commented-out template style).
- **Task applicability:** all 10 findings applicable and executable. This report validates safety,
  consistency, and applicability only — no source code was modified.

## Warnings

- **Architectural risk:** none. CFG-006's dead branch is inert; removal is safe.
- **Rollout risk (medium):** CFG-001's `download_dir` empty-string handling is a silent->fail-fast
  behavior change. Assess before shipping (see Rollout Analysis).
- **Dependency risk:** none.
- **Documentation inconsistency (process):** Phase 01's
  `.ai/audit/99-validation/01-audit-cli-validated-findings.md` is empty (0 bytes) — flagged for
  maintainer process awareness.

## Required Fixes (mandatory)

- **CFG-001 (HIGH, mandatory):** Add a `mode="before"` validator to convert empty-string env values
  to `None` for `log_file` (and `download_dir`), preventing the startup crash when the documented
  empty `VKDOWNLOADER_LOG_FILE=` example is followed. For `download_dir`, the empty-string-to-None
  transform produces a `ValidationError` (fail-fast), consistent with the project's
  `validate_cookie_source` rejection pattern — **this is the chosen approach, not left as an option**.
  The `ValidationError` is caught at `cli.py:475` and shown via `_format_validation_error`.

## Advisory Recommendations

- **CFG-002 (DOC-UPDATE):** Add commented `VKDOWNLOADER_HEADLESS` to `.env`.
- **CFG-003 (DOC-UPDATE):** Correct `throttled_rate` default to `10000` in `api-reference.md:852` and
  `installation.md:119`.
- **CFG-004 (DOC-UPDATE):** Add `browser_pre_interaction_wait`/`browser_post_interaction_wait` rows to
  `api-reference.md` settings table.
- **CFG-005 (DOC-UPDATE):** Remove `file` from the `.env` cookie_source comment (line 26).
- **CFG-006 (SPEC-DEVIATION):** Remove the unreachable `NotImplementedError` branch at `extractor.py:129-132` (the `validate_cookie_source` validator at config.py:126-138 already blocks `CookieSource.FILE` at construction). Retain the `CookieSource.FILE` enum value in `enums.py:49` for forward compatibility. Update `.env` template comment (line 26) to list only `(none, browser)`. Align `configuration.md:66` and `cli-reference-clean.md:198` to state `ValidationError` is raised at construction (not `NotImplementedError`).
- **CFG-007 (DOC-UPDATE):** Fix `installation.md:106-125` example: `throttled_rate=10000`, non-empty
  `LOG_FILE`, and add the three missing fields.
- **CFG-008 (BEST-PRACTICE):** Add a tracked `.env.example` with all 16 settings (commented).
- **CFG-009 (DOC-UPDATE):** Change `verify` -> `true` at `cli-reference-clean.md:68,126`.
- **CFG-010 (SPEC-DEVIATION):** Rewrite the `throttled_rate` description in `config.py:89` and
  propagate to `api-reference.md:852` and `configuration.md:34`.

