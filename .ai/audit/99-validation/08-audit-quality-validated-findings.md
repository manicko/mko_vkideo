# Phase 08 Audit Findings -- Code Quality, Security & Maintainability (VALIDATED)

**Phase:** 08-audit-quality (Code Quality, Security & Maintainability)
**Source (audited):** `.ai/audit/08-audit-quality/findings.md`
**Validator:** validator (evidence-driven, conservative)
**Scope:** lint/type hygiene, progress-callback wiring, comment/code consistency, docstrings, structured-log invariant.
**Status:** complete
**Validated:** yes

> Validator note: this file is a self-contained, verified copy of the source findings with inline
> validation decisions applied. The reader need not consult the original. Validated against the working
> tree at `C:\py_exp\mko_vkideo` on 2026-08-05 (Python 3.12.1, pydantic 2.13.4 / pydantic-settings 2.14.2,
> structlog 26.1.0). `ruff check src` -> All checks passed!; `mypy src` -> Success (23 source files);
> `pytest` -> 248 passed (10.91s). `ruff check --select RUF100 src` -> 11 unused noqa directives confirmed.
> No source code was modified.

---

## Validation Methodology

1. **Source** -- read `src/vkdownloader/cli.py`, `config.py`, `services/downloader.py`,
   `infrastructure/network_monitor.py`, `pyproject.toml`.
2. **Static** -- `uv run ruff check --select RUF100 src` (re-run to confirm QLT-001 claim count and locations).
3. **Runtime evidence** -- `ruff` (pass), `mypy` (pass), `pytest` (248 passed) confirm the tree is green;
   findings describe latent/design issues, not currently-failing behavior.
4. **Cross-phase** -- compared against Phase 01 (CLI), Phase 02 (Config), Phase 03 (Services), Phase 04 (Security).
5. **Docs/config** -- read `pyproject.toml` ruff `[tool.ruff.lint]` select/ignore to verify QLT-001's claim
   that `B008` is in `ignore` and `BLE001` is not in `select`.

### Decision legend

- **[VALIDATED]** Root cause verified against current code; recommendation stands.
- **[RECLASSIFIED]** Valid issue, but `Type` adjusted per the validator taxonomy.
- **[REJECTED]** Issue not present, stale, duplicate, low-ROI, architecture-breaking, operationally unsafe.

---

## Findings

### QLT-001: Redundant `# noqa` directives in cli.py and network_monitor.py  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-ran `uv run ruff check --select RUF100 src` -> exactly 11 errors, matching the finding's
>   locations (cli.py:387,388,394,400,513,518,522,528,534 for `B008`; network_monitor.py:91,116 for `BLE001`).
>   Confirmed `pyproject.toml:65-68`: `ignore = ["E501", "B008"]` (B008 never fires -> noqa suppresses nothing).
>   Confirmed `pyproject.toml:56-64`: `select = ["E","W","F","I","B","C4","UP"]` (no `BLE`/`BLE001` -> not enforced).
>   The 9 `# noqa: B008` comments sit on Typer `Option`/`Argument` defaults (the documented project pattern);
>   the 2 `# noqa: BLE001` comments suppress a rule that isn't enabled. All real code.
> - **Architectural fit:** removing stale noqa is config/code hygiene; no behavioral change.
> - **See also:** Phase 01 CLI-008 touches *mypy* config unused-section noise (different tool, no conflict).
> - **Rollout safety:** independent; no dependency on other findings.

**Description:** Eleven `# noqa` suppression comments are redundant under the project's own ruff configuration.
Nine `# noqa: B008` comments sit on Typer `Option`/`Argument` defaults in `cli.py`, but `B008` is listed in
`ignore` (`pyproject.toml:65-68`), so the rule never fires and the comments suppress nothing. Two `# noqa: BLE001`
comments in `network_monitor.py` reference `BLE001`, which is **not** in the `select` list
(`pyproject.toml:56-64` enables only `E,W,F,I,B,C4,UP`) -- so BLE001 is not enforced at all, and the noqa provides
neither suppression nor documentation value. This is config/code drift: the annotations signal intent that the
active config contradicts, misleading maintainers about which rules are actually enforced.

**Evidence (verified):**
- `uv run ruff check --select RUF100 src` -> 11 errors (9 B008 in cli.py, 2 BLE001 in network_monitor.py).
- `pyproject.toml:65-68` -- `ignore = ["E501", "B008"]`
- `pyproject.toml:56-64` -- `select = ["E","W","F","I","B","C4","UP"]` (no `BLE`)

**Recommendation [BEST-PRACTICE]:** Remove the 11 stale `# noqa` comments. If broad-`except` (BLE001) coverage is
desired, add `BLE` to `select`; if not, delete the comments so the broad `except Exception` sites are visible as
intentional rather than silently unguarded. Effort: trivial. Priority: recommended.

---

### QLT-002: FFMPEG download method silently drops `progress_callback`  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download` FFMPEG branch, `HLSDownloader.download_with_ffmpeg` signature) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed at `downloader.py:811` the FFMPEG branch calls
>   `downloader.download_with_ffmpeg(m3u8_url, output_file, quality, cookies)` -- `progress_callback` is **not** passed.
>   Contrasts with the yt-dlp branch (`downloader.py:796`) and AUTO branch (`downloader.py:849`), both of which
>   forward `progress_callback`. The segment-download fallback (`:821`) also forwards it. The method signature
>   `download_with_ffmpeg(..., progress_callback: Callable[[FfmpegProgress], None] | None = None)` exists at
>   `:287` but is unreachable from the orchestrator. Type mismatch is real: `perform_download`'s
>   `progress_callback` is `Callable[[str, int, int], None]` (`:725`), incompatible with
>   `Callable[[FfmpegProgress], None]` (`:287`). `HLSDownloadRequest.progress_callback` is
>   `Callable[[str, int, int], None]` (`models/dtos.py:24`) -- the type the orchestrator actually holds.
> - **Architectural fit:** recommendation aligns with project rule 3 (separation of concerns) and rule 5
>   (no overengineering).
> - **See also:** Phase 01 CLI-006 (single `download` command does not pass `progress_callback` into
>   `perform_download` at the call site). QLT-002 is the *service-layer* gap; CLI-006 is the *call-site* gap.
>   Complementary, same progress-wiring theme, **distinct root causes and code paths** -- kept separate.
> - **Rollout safety:** QLT-002 fix is independent of CLI-006; no circular/hidden dependency.

**Description:** `perform_download` accepts a `progress_callback` parameter and forwards it to the yt-dlp branch
(`downloader.py:796`) and the segment-download fallback (`download_hls_with_resume` via `HLSDownloadRequest`,
`downloader.py:821`), but **the FFMPEG method branch never passes it** to `download_with_ffmpeg`
(`downloader.py:811`). `download_with_ffmpeg` declares a `progress_callback` parameter and docs
(`docs/01-tools/vkdownloader-overview.md:177-197`) describe ffmpeg progress tracking, so the wiring exists at the
method level but is unreachable from the orchestrator. The gap is structural: `perform_download`'s callback type
is `Callable[[str, int, int], None]` (segment-style), **incompatible** with `download_with_ffmpeg`'s
`Callable[[FfmpegProgress], None]`, so a direct forward would be a type error. Complements CLI-006.

**Evidence (verified):**
- `downloader.py:811` -- FFMPEG branch call omits `progress_callback`
- `downloader.py:287` -- `download_with_ffmpeg(..., progress_callback: Callable[[FfmpegProgress], None] | None = None)`
- `downloader.py:725` -- `perform_download`'s `progress_callback: Callable[[str, int, int], None] | None`
- `downloader.py:796` (yt-dlp) and `:849` (AUTO) forward `progress_callback`; `:821` (segment fallback) does
- `models/dtos.py:24` -- `HLSDownloadRequest.progress_callback` is `Callable[[str, int, int], None]`

**Recommendation [BEST-PRACTICE]:** Bridge the two progress shapes: wrap `perform_download`'s per-URL callback
into a `Callable[[FfmpegProgress], None]` adapter (mapping `FfmpegProgress.total_size`/`out_time_us` ->
`(video_id, downloaded, total)`) and forward it to `download_with_ffmpeg`, or hoist a shared progress abstraction.
At minimum, document that `--method ffmpeg` does not report per-segment progress. Effort: small. Priority: recommended.

---

### QLT-003: Stale comment promises `DownloadError` re-raise that never happens  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed `downloader.py:18` imports only
>   `from ..exceptions import ExtractionError, QualityNotAvailableError` -- `DownloadError` is **not** imported.
>   The comment at `downloader.py:635` (`# Re-raise as DownloadError to distinguish from cancellation`) sits
>   above code that raises `RuntimeError("Download cancelled")` (`:637`) on shutdown or re-raises the original
>   (`raise`, `:638`). No `DownloadError` is raised anywhere in this module. Confirmed `DownloadError` is defined
>   at `exceptions.py:54` and raised only in `utils/security.py:44`; never in `downloader.py`.
> - **Architectural fit:** comment/code consistency is a maintainability issue; recommendation is sound.
> - **Rollout safety:** independent; comments-only.

**Description:** The comment at `downloader.py:635` states `# Re-raise as DownloadError to distinguish from cancellation`,
but `DownloadError` is not imported in this module (the import at `downloader.py:18` is
`from ..exceptions import ExtractionError, QualityNotAvailableError`) and the code that follows does not raise
`DownloadError` -- it raises `RuntimeError("Download cancelled")` on shutdown or re-raises the original exception.
The comment describes behavior that does not exist, misleading maintainers into believing cancellation is wrapped
in a recognizable exception type that the caller can act on.

**Evidence (verified):**
- `downloader.py:18` -- `from ..exceptions import ExtractionError, QualityNotAvailableError` (no `DownloadError`)
- `downloader.py:634-638` -- comment then `raise RuntimeError("Download cancelled") from e` / `raise`
- `src/vkdownloader/exceptions.py:54` -- `DownloadError` defined; `utils/security.py:44` -- only raise site

**Recommendation [BEST-PRACTICE]:** Correct the comment to match actual behavior (re-raise original on
cancellation-via-shutdown; re-raise unchanged otherwise), or implement the stated intent (wrap non-cancellation
exceptions in `DownloadError` and import it). Effort: trivial. Priority: recommended.

---

### QLT-004: Public `Settings` field validators lack docstrings  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/config.py` (`expand_tilde_paths`, `normalize_log_level`) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed `config.py:112-117` `expand_tilde_paths` and `config.py:119-124` `normalize_log_level`
>   have **no docstrings**. Sibling `validate_cookie_source` (`config.py:126-138`) **does** have a one-line
>   docstring -- omission is inconsistent. Both validators encode non-obvious normalization logic (empty/tilde path
>   expansion to `Path | None`; case-insensitive `LogLevel` coercion), violating project rule 14 ("Keep
>   documentation updated continuously"). The recommendation to note that empty-string inputs are *not* converted
>   to `None` (referencing CFG-001) is **consistent** with Phase 02 CFG-001's documented gap -- no conflict.
> - **Architectural fit:** docstring addition is trivially backward-compatible and improves maintainability.
> - **Rollout safety:** independent; no dependency.

**Description:** Two public field-validator methods on the `Settings` model have no docstring, violating project rule
14 ("Docstrings on public APIs") and the phase 08 "docstrings on public APIs" check. The sibling validator
`validate_cookie_source` (`config.py:128`) is documented, so the omission is inconsistent. Both validators encode
non-obvious normalization logic (empty/tilde path expansion to `Path | None`, and case-insensitive `LogLevel`
coercion) that future maintainers must reverse-engineer.

**Evidence (verified):**
- `config.py:112-117` -- `expand_tilde_paths`, no docstring
- `config.py:119-124` -- `normalize_log_level`, no docstring
- `config.py:126-138` -- `validate_cookie_source`, has docstring (contrast)

**Recommendation [BEST-PRACTICE]:** Add docstrings to `expand_tilde_paths` and `normalize_log_level` describing
their normalization behavior (notably that empty-string inputs are *not* converted to `None` here -- see CFG-001).
Effort: trivial. Priority: recommended.

---

### QLT-005: One log call pre-formats with an f-string, defeating structured logging  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/cli.py` (`_log_env_file_path`) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed `cli.py:39` -- `logger.debug(f".env file resolved to: {env_file.resolve()}")`
>   pre-formats the path into the event string, collapsing it to an opaque string under the JSON renderer.
>   Confirmed `config.py:218-225` configures structlog with `JSONRenderer()` (file) and `ConsoleRenderer()` (terminal),
>   so events are expected to be structured (`logger.event("name", key=value)`). Confirmed the established
>   convention at `cli.py:436-437` (`logger.info("available_streams", count=...)` /
>   `logger.info("available_qualities", qualities=...)`). QLT-005's single outlier is accurate -- no f-string
>   pre-formatting exists elsewhere in `src` logger calls.
> - **Architectural fit:** recommendation aligns with the project's structured-logging invariant.
> - **Rollout safety:** independent; logs-only.

**Description:** The project configures structlog with a JSON renderer for file logging and a console renderer for
terminal output (`config.py:218-225`), so log events are expected to be structured
(`logger.event("event_name", key=value)`). The call at `cli.py:39` instead pre-formats the value into the event
string via an f-string: `logger.debug(f".env file resolved to: {env_file.resolve()}")`. With the JSON renderer
this collapses the path into an opaque event string rather than a queryable `path` field, breaking the
structured-log invariant the rest of the codebase follows (e.g. `cli.py:436-437`, `downloader.py:747-753`).

**Evidence (verified):**
- `cli.py:39` -- `logger.debug(f".env file resolved to: {env_file.resolve()}")`
- `cli.py:436-437` -- structured (`logger.info("available_streams", count=...)`, `logger.info("available_qualities", qualities=...)`)
- `config.py:218-225` -- `JSONRenderer()` / `ConsoleRenderer()`

**Recommendation [BEST-PRACTICE]:** Convert to `logger.debug("env_file_resolved", path=str(env_file.resolve()))`
to match the structured-logging convention used everywhere else. Effort: trivial. Priority: recommended.

---

## Cross-Finding Analysis

**Scope:** Phase 08 findings cross-referenced against Phase 01 (CLI), Phase 02 (Config), Phase 03 (Services),
Phase 04 (Security).

**Same root cause (merge candidates):**

- **QLT-002 <-> CLI-006** share a theme -- "progress callback not wired end-to-end." They target **distinct layers**:
  CLI-006 is the *call site* (`download()` does not pass `progress_callback` into `perform_download`); QLT-002 is the
  *service-orchestration gap* (the FFMPEG `case` branch drops it). **Kept separate:** distinct code paths and
  independent fixes; fixing one does not subsume the other. Dependency direction: CLI-006 (call-site wiring) is
  upstream of QLT-002 (once received), but the FFMPEG-branch gap is real regardless.
- **QLT-004 <-> CFG-001** -- QLT-004's recommendation explicitly defers to CFG-001's documented empty-string->CWD gap
  for the docstring note. **Consistent reference, not a duplicate.** CFG-001 is the config runtime-error
  (empty `LOG_FILE` crashes `FileHandler`); QLT-004 is a docstring hygiene issue. Distinct.
- QLT-001, QLT-003, QLT-005 are module-local and independent; no overlaps.

**Conflicting evidence (cross-phase):** None. No other phase asserts that noqa directives are meaningful, that the
FFMPEG branch forwards callbacks, that the `DownloadError` comment is accurate, that validators are documented, or
that f-string log formatting is acceptable.

**Dependency chains:**

- **None blocking.** All five are independent, comments/docstrings/logs-only changes. QLT-002 is conceptually
  downstream of CLI-006 (the callback only reaches `perform_download` if the CLI wires it), but QLT-002's fix
  (forward to FFMPEG branch) is meaningful independently and does not require CLI-006's fix to be valid.

---

## Rollout Analysis

- **Independence / ordering:** All five are localized, backward-compatible, advisory (LOW) changes; order independent.
  - **QLT-001:** remove 11 stale `# noqa` comments (ruff `--fix` or manual). Logs/lint only.
  - **QLT-002:** bridge `Callable[[str,int,int],None]` -> `Callable[[FfmpegProgress],None]` adapter in the FFMPEG
    `case`, forward to `download_with_ffmpeg`. Backward-compatible (callback remains `None` by default).
  - **QLT-003:** comment correction or (optionally) implement `DownloadError` wrap. Comments/behavior only.
  - **QLT-004:** add docstrings. No behavior change.
  - **QLT-005:** single logger call site. Log format only.
- **Circular / hidden dependencies:** none.
- **Backward compatibility:** all changes are additive or comments-only; no public API signature changes that
  break callers. QLT-002's adapter is internally scoped.
- **Anchors:** fixes target stable functions/signatures (`perform_download` FFMPEG `case`,
  `download_with_ffmpeg` signature, `_download_with_ytdlp` comment block, `Settings` validators,
  `_log_env_file_path`) -- no fragile line-only anchors.

---

## Execution Validation

- **Targets exist:** `cli.py:39`, `cli.py:436-437`, `config.py:218-225`, `config.py:112-138`, `downloader.py:18`,
  `downloader.py:287`, `downloader.py:634-638`, `downloader.py:725`, `downloader.py:796/811/821/849`,
  `network_monitor.py:91/116`, `exceptions.py:54`, `utils/security.py:44`, `models/dtos.py:24`,
  `pyproject.toml:56-68` -- all read-confirmed in the current tree.
- **Plan not stale:** tree is green (`ruff` pass, `mypy` pass, 248 tests pass); RUF100 re-run confirms QLT-001's
  exact count and line locations.
- **Architecture consistent:** QLT-002's adapter approach mirrors the existing `HLSDownloadRequest.progress_callback`
  (`Callable[[str,int,int],None]`) adapter pattern already used for the segment fallback; QLT-005 reuses the
  established structured-logging convention; QLT-001 aligns ruff annotations with the active config.
- **Applicability:** all five findings applicable and executable. No source code was modified -- scope is
  validation only.

---

## Warnings

- **Architectural risk (low):** QLT-002's callback-shape mismatch (`Callable[[str,int,int],None]` vs
  `Callable[[FfmpegProgress],None]`) reflects a broader progress-callback type inconsistency; resolving it with a
  shared abstraction (rather than a one-off adapter) would reduce future drift. Flagged for maintainers'
  discretion, not mandated.
- **Rollout risk (low):** none -- all changes are comments/docstrings/logs/optional-adapter only.
- **Dependency risk (low):** QLT-002 only becomes user-visible once CLI-006 is also resolved (call-site wiring);
  the two should be tracked together for UX consistency, but neither fix depends on the other to be correct.
- **Documentation / evidence inconsistency:** none introduced by this validation. All finding claims verified.

---

## Advisory Recommendations

- **QLT-001 (LOW, advisory):** Remove the 11 stale `# noqa` directives. If broad-`except` coverage is desired in
  `network_monitor.py`, add `BLE` to `select`; otherwise delete the comments. `uv run ruff check --select RUF100 src
  --fix` automates this. Effort: trivial.
- **QLT-002 (LOW, advisory):** In `perform_download`'s `case DownloadMethod.FFMPEG`, wrap the orchestrator's
  `Callable[[str,int,int],None]` callback into a `Callable[[FfmpegProgress],None]` adapter and forward it to
  `download_with_ffmpeg`; or hoist a shared progress abstraction. At minimum, document `--method ffmpeg` reports
  no per-segment progress. Effort: small.
- **QLT-003 (LOW, advisory):** Correct the comment at `downloader.py:635` to match actual behavior (re-raise
  original; `RuntimeError("Download cancelled")` on shutdown), or implement the stated intent by importing
  `DownloadError` and wrapping. Effort: trivial.
- **QLT-004 (LOW, advisory):** Add docstrings to `expand_tilde_paths` and `normalize_log_level`, noting that
  empty-string inputs are **not** coerced to `None` (see CFG-001 for the related crash). Effort: trivial.
- **QLT-005 (LOW, advisory):** Convert `cli.py:39` to
  `logger.debug("env_file_resolved", path=str(env_file.resolve()))`. Effort: trivial.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | QLT-001, QLT-002, QLT-003, QLT-004, QLT-005 |
| Reclassified | 0 | -- |
| Merged | 0 | QLT-002 / CLI-006 kept separate (distinct layers / root causes); QLT-004 / CFG-001 kept separate (hygiene vs config runtime-error). |
| Rejected | 0 | -- |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| _(none)_ | -- | All five findings verified against current code; none stale/duplicated/low-ROI/unsafe. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| _(none)_ | -- | QLT-002/CLI-006 and QLT-004/CFG-001 share themes but distinct root causes, code paths, and fix scopes; kept separate for independent remediation. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| _(none)_ | -- | -- | All findings already use the validator taxonomy. |

---

All five Phase 08 findings are **validated** with verified evidence, correct against the current tree, and safe to
remediate. No source code was modified.
