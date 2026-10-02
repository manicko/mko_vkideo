---
name: 09-code-quality-validated-findings
description: Validation of Phase 09 code-quality findings (13 findings, 3 VAL entries)
agent: validator
alwaysApply: false
---

# Phase 09 Audit Findings — Code Quality — Validated

**Source report (read-only):** `.ai/audit/09-code-quality/findings.md` — 13 findings, 0 CRITICAL, 2 HIGH, 7 MEDIUM, 4 LOW; 7 `SPEC-DEVIATION`, 6 `DOC-UPDATE`; 3 mandatory, 10 advisory.
**Validator:** `99-audit-validate.md` · **Format:** `.ai/audit/templates/audit-findings.md` · **Status:** complete
**Decided:** Validated 8 · Reclassified 1 · Merged 0 · Rejected 0 · New `VAL-` 3

**Deviations from the format, declared once, as §11 requires.**

1. **The `Validation Note` field has no slot in the format.** The format's finding block runs `### {ID}: {Title}` straight into a fixed nine-field table (`.ai/audit/templates/audit-findings.md:19-27`) whose fields carry no decision. Every decided finding below therefore carries a `> **Validation Note:**` block written in the position §11 defines. This input defect is **already filed** — `02-config-validated-findings.md` `VAL-001`, `03-network-resilience-validated-findings.md` `VAL-006`, `08-cli-observability-validated-findings.md` (template half of `VAL-002`) — and is cross-referenced, not re-filed.
2. **No finding is Rejected and none is Merged**, so §11's verbatim-retention requirement is not triggered by any block. Each finding is instead carried as a self-contained record: its field table, the claim, the evidence **re-derived by this run** with the artifact read named, and its decision. The reader needs no access to the source report.
3. **`### Severity Re-derivations` is added to the Validation Summary.** §11's summary table has a row for a `Type` change but none for a `Severity` change, and binding rule 1 requires every severity to be re-derived. Four findings changed severity. Recording that in the prescribed table would either overload the `Reclassified` table (which is defined for `Type`) or lose the evidence; a named fifth table carries it. No prescribed table is altered.

**Measured against:** the **working tree** at `HEAD = a335b2a` plus uncommitted edits to `src/vkdownloader/cli.py` and `src/vkdownloader/config.py`. Both trees were measured; the two-way check is recorded in full below and was re-performed by this run rather than inherited.

**Platform:** Windows. Entirely static plus in-process probes through `uv run python -`. No container, no database, no service, no terminal. Every repository-wide search excluded `.kilo/worktrees/`, `.venv/`, `__pycache__/` and `.temp/`.

**Baselines re-run by this run, on the working tree:**

| Command | Result |
|---|---|
| `uv run ruff check src tests` | `All checks passed!` (exit 0, 52 files) |
| `uv run ruff format --check src tests` | `52 files already formatted` (exit 0) |
| `uv run mypy src` | `Success: no issues found in 30 source files` (exit 0) |
| `uv run mypy src tests` | 55 errors in 6 files, every one in `tests/` — the source half is clean |

The source report's R1 baseline reproduces exactly. No finding below depends on which of the two trees was measured; the two-way check is stated per finding where a `cli.py` or `config.py` line is cited.

---

## R0 — Discovery

### Corpus map

Nine findings files, nine phase handbooks, one validation store. No handbook without a findings file; no findings file without a handbook.

| Phase | Findings file | Handbook | Findings | Validated artifact |
|---|---|---|---|---|
| 01 | `.ai/audit/01-entry-architecture/findings.md` | `01-audit-entry-architecture.md` | 14 | present |
| 02 | `.ai/audit/02-config/findings.md` | `02-audit-config.md` | 8 | present |
| 03 | `.ai/audit/03-network-resilience/findings.md` | `03-audit-network-resilience.md` | 18 | present |
| 04 | `.ai/audit/04-concurrency-cancellation/findings.md` | `04-audit-concurrency-cancellation.md` | 10 | present |
| 05 | `.ai/audit/05-subprocess-browser/findings.md` | `05-audit-subprocess-browser.md` | 14 | present |
| 06 | `.ai/audit/06-credentials-secrets/findings.md` | `06-audit-credentials-secrets.md` | 10 | present |
| 07 | `.ai/audit/07-filesystem-artifacts/findings.md` | `07-audit-filesystem-artifacts.md` | 16 | present |
| 08 | `.ai/audit/08-cli-observability/findings.md` | `08-audit-cli-observability.md` | 17 | present |
| 09 | `.ai/audit/09-code-quality/findings.md` | `09-audit-code-quality.md` | 13 | **this file** |
| 10, 11 | not produced | `10-audit-test-coverage.md`, `11-audit-supply-chain.md` | — | — |

`VAL-903` records the corpus-drift condition this run was handed: the audit's own history is a **stale, superseded catalogue** (`01-audit-cli`, `02-audit-config`, `03-audit-services`, `04-audit-security`, `05-audit-integrations`, `06-audit-data-flow`, `07-audit-tests`, `08-audit-quality`, `09-structural-quality`), present in the repository and deleted-but-unstaged in the working tree, and copied in full into `.kilo/worktrees/southern-bandana/.ai/audit/`. Any count taken from either is wrong.

### Identifier map

Live finding prefixes across the nine findings files: `ENT` (14), `CFG` (8), `NET` (18), `SKIP` (6), `CON` (10), `SEC` (10), `OUT` (17), `QLT` (13) — 96 findings, no prefix collision among them.

`VAL-` is a **flat namespace**: 44 identifier occurrences across eight validation files, **33 distinct**. Thirteen identifiers are duplicated: `VAL-001` ×3, `VAL-002` ×3, `VAL-003` ×3, `VAL-004` ×3, `VAL-005` ×3, `VAL-006` ×2. Filed once as **`VAL-901`**. `VAL-901` through `VAL-903` are the identifiers this run mints; they are deliberately outside the 001–007 and 101–112 ranges already in use so they collide with nothing.

No identifier no phase claims was found in the findings files. `INT-`, `SRV-`, `BE-` and `FE-` appear in the corpus but not as live prefixes: the first two are citation tokens quoted inside QLT-007 and `docs/`, the last two are the worked examples in the report format (`.ai/audit/templates/audit-findings.md:66`).

### Decision-record map

The report format defines nine mandatory fields; none carries a decision. One decision field (`Validation Note`) is defined by `99-audit-validate.md` §11 and has no home. Every one of the 13 findings therefore has an **absent slot**, and the deviation is declared in this file's header rather than assumed away. Already filed three times; cross-referenced.

### Pipeline-document map

Nine documents in the audit pipeline's own surface. Read, verified, and the two that reproduce as defects are recorded in `VAL-901` and `VAL-902`; the two that check out are not written down.

| Document | Declares it does | Launched / read by | Verified |
|---|---|---|---|
| `.kilo/commands/audit/audit-multi-phase.md` | selects phases, runs executor + validator subagents, two gates | the user | path agreement holds; the launch gate is unevaluable (already filed) |
| `.kilo/commands/audit/audit-refine.md` | rewrites non-actionable recommendations in place | manual | base-context read names an absent file (already filed) |
| `.kilo/commands/audit/audit-orphaned.md` | orphaned-file census | manual | protect-list does not exempt the catalogue or worktrees (already filed) |
| `.kilo/commands/audit/audit-phase-gaps.md` · `audit-phase-refine.md` | phase-level gap/refinement | manual | no defect observed by this run's scope; not examined further |
| `.kilo/commands/audit/tests/audit-tests-*.md` | four test-suite audit variants | manual | out of this run's scope |
| `.kilo/commands/audit/phases/01`–`11` | one handbook per phase | `audit-multi-phase.md:22` | all eleven present, all with a handbook |
| `.kilo/commands/audit/phases/99-audit-validate.md` | this phase | `audit-multi-phase.md:92` | binding rule 3 honoured; filename unchanged |
| `.ai/audit/templates/audit-findings.md` | the report contract | `audit-multi-phase.md:48` | no decision slot (already filed) |
| `.kilo/agents/auditor.md` · `validator.md` | the two roles the pipeline launches | `audit-multi-phase.md:75,98` | both exist; both omit `RUNTIME-ERROR` (already filed) |

---

## The tree-drift measurement, re-performed

`HEAD` is `a335b2a`. Two source files carry uncommitted edits from a concurrent agent. The pipeline records a commit in the report header and audits a working directory; all four baselines pass on both trees, so no gate catches it. This run measured both trees itself rather than inheriting the source report's table.

`git diff HEAD --numstat -- src/vkdownloader/cli.py src/vkdownloader/config.py` → `21  3  src/vkdownloader/cli.py`, `0  10  src/vkdownloader/config.py`. Physical line counts: `cli.py` 383 working tree / 365 `HEAD`; `config.py` 372 working tree / 382 `HEAD`.

**`cli.py` — every content edit lies above `HEAD` line 141, which is above the lowest anchor any phase-09 finding cites.** The three hunks are the `.config` import block (`HEAD` 23 → working tree 23–29, net +6), the `_run_command_preamble` docstring (net +2) and the `warn_unknown_env_vars()` call replaced by a nine-line stderr render (net +8). Nothing below working-tree line 134 differs. Ten anchors were cited across QLT-002 and QLT-006; each was read at `HEAD` and at the working tree:

| Working tree | `HEAD` | Line at both trees | Shift | Content differs? |
|---|---|---|---|---|
| `cli.py:159` | `141` | `cookie_source: CookieSize \| None = typer.Option(` — the `--cookie-source` / `-c` declaration | +18 | no |
| `cli.py:165` | `147` | `ssl_verify: bool \| None = typer.Option(` | +18 | no |
| `cli.py:222` | `204` | `except ValidationError as e:` | +18 | no |
| `cli.py:225` | `207` | `except QualityParseError as e:` | +18 | no |
| `cli.py:232` | `214` | `except InvalidVideoUrlError:` | +18 | no |
| `cli.py:241` | `223` | `except QualityNotAvailableError as e:` | +18 | no |
| `cli.py:258` | `240` | `except VideoNotFoundError:` | +18 | no |
| `cli.py:263` | `245` | `except Exception:` | +18 | no |
| `cli.py:328` | `310` | `if not is_valid_video_url(stripped):` | +18 | no |
| `cli.py:356` | `338` | `except ValidationError as e:` | +18 | no |

**`config.py` — the edits are three deletions, all above `HEAD` line 142.** The module logger (`HEAD:14-15`), one `logger.debug` inside a field validator (`HEAD:143`) and the six-line `unknown_env_var_ignored` warning loop (`HEAD:313-318`). The three cited anchors: `config.py:12` identical at `HEAD:12` (shift 0); `config.py:15` → `HEAD:17`; `config.py:77` → `HEAD:79` (uniform −2). Content identical at all three.

**Verdict on the drift.** It is real, it is a line-number shift only at every cited anchor, and it is **not a defect** — the concurrent edit is the CFG-003/CFG-004 typo-guard fix, its own subject, owned by phase 02. Nothing in this report is filed on the drift. The source report's table is correct on substance; its header says "all 13 cited anchors" while the table lists 10 mappings, and all 10 of the listed ones verify. The `+18`/`−2` offsets, the "content-identical" conclusion and the "line numbers reported are the working tree's" convention are all confirmed independently.

---

## Checkpoint 1 — R1 Copy Source Findings

- **Stage:** R1 Copy Source Findings
- **Findings in scope:** 13
- **Evidence anchor:** `.ai/audit/09-code-quality/findings.md` (read-only; 645 lines); this artifact; the tree-drift table above
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 13
- **Cross-phase conflicts:** 2 — one identifier carrying three mutually exclusive claims (`VAL-003`), and two cross-phase claims that no longer reproduce at `HEAD` (`VAL-902`)
- **Merge candidates:** 0 — one complement pair identified and retained (`QLT-001` ↔ `QLT-010`, cross-referenced, with an ordering constraint recorded under R4)
- **Evidence anchor:** this artifact, `VAL-901`, `VAL-902`, `VAL-903`; the eight validation files in `.ai/audit/99-validation/`
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 13 — Validated 8 · Reclassified 1 · Merged 0 · Rejected 0
- **Severities re-derived:** 13 of 13; 4 changed (QLT-003, QLT-004, QLT-005, QLT-009, each MEDIUM → LOW)
- **Evidence anchor:** per-finding `Validation Note` below; the artifacts each names
- **Dependencies / blockers:** none
- **Checkpoint status:** closed

## Checkpoint 4 — R4 Assess Rollout Safety

- **Stage:** R4 Assess Rollout Safety
- **Findings in scope:** 13
- **Unsafe-ordering count:** 1 — `QLT-001` and `QLT-010` both prescribe edits inside `exceptions.py:141-149` and cannot be applied independently
- **Findings added:** 3 (`VAL-901` namespace collision · `VAL-902` non-reproducing cross-phase claims · `VAL-903` the `QLT-011` split's unstated test-side blast radius)
- **Circular dependencies:** 0 · **Hidden chains:** 0 · **Fragile anchors:** 0 (every anchor this run re-derived resolves in both trees)
- **Evidence anchor:** `VAL-903`; the `QLT-001` / `QLT-010` ordering constraint under `VAL-903`'s "See also"
- **Checkpoint status:** closed

---

## Findings

### QLT-001: `QualityNotAvailableError` carries two identifiers, and the two ladders that derive its label have already diverged

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived independently and the divergence reproduces exactly. `QualityNotAvailableError.error_code` is `ErrorCode.QUALITY_NOT_AVAILABLE` on both outcomes (`exceptions.py:117`); `status_label()` returns `"no_streams"` when `available` is empty and `"quality_not_available"` otherwise (`exceptions.py:141-149`); `ErrorCode` (`models/enums.py:52-67`) has eight members and none is `no_streams`. The legacy shim's guard requires `exc.requested` to be truthy (`exceptions.py:212-217`), and the object raised at `quality.py:70` supplies `requested=""`. In-process probe of the three shapes:
>
> | instance | `error_code` | `status_label()` | `_map_exception_to_status()` |
> |---|---|---|---|
> | `quality.py:70` — `requested=""`, `available=[]` | `quality_not_available` | `no_streams` | `quality_not_available: requested p, available: ` |
> | `downloader.py:669` — `requested="<quality>"`, `available=[]` | `quality_not_available` | `no_streams` | `no_streams: No streams found for this video` |
> | `available=["1080p"]` | `quality_not_available` | `quality_not_available` | `quality_not_available: requested 1440pp, available: 1080p` |
>
> The two ladders disagree on the identical object, as claimed. Reachability confirmed at `downloader.py:668-673` (identical in both trees; `downloader.py` is unmodified), and the label reaches the terminal verbatim through `batch_downloader.py:263` → `:426` and `:455`.
>
> **One correction to the severity rationale, which does not change the decision.** `_map_exception_to_status` has **zero production call sites** — the only definition is `exceptions.py:196` and the only callers are eleven in `tests/test_exceptions.py` (the source report's "tests: 12" counts the import at `:11`). So of the "three identifiers for one condition", **two are live** (`no_streams` printed by the batch summary, `quality_not_available` in `ErrorCode`) and one is dead in production. The two live ones are not a defect on their own — a user-facing label and a machine code are allowed to differ — what is a defect is that the live one is not a member of the enumeration `models/enums.py:53-58` declares "so that log aggregators and users can filter and group by specific failure modes", and that the batch ladder records no log line at all for this condition. The second half of that is `QLT-002`'s subject, not this one. The finding's core claim stands; HIGH is retained because a green test suite ships a user-visible label that no declared filter can match.
> - **See also:** `QLT-002` (the missing log call on this same clause) · `QLT-010` (the same ladder, one rung down) · `VAL-903` ordering constraint

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | HIGH — **re-derived, unchanged** |
| **Type** | `SPEC-DEVIATION` — confirmed |
| **Affected Modules** | `src/vkdownloader/exceptions.py`, `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/models/enums.py` |
| **Classification** | mandatory — confirmed |

**Description.** One declared condition — the requested quality cannot be satisfied — is reported under three names depending on which rung of the taxonomy the reader consults, and the two independent implementations of that condition's label already disagree with each other. `ErrorCode` is `QUALITY_NOT_AVAILABLE` on both outcomes, but `status_label()` splits the condition into `no_streams` and `quality_not_available`, and the label the batch summary prints is not a member of the enumeration the log is filtered by.

**Evidence (re-derived).** `exceptions.py:117`, `:141-149`, `:196`, `:212-217`, `:220`; `models/enums.py:52-67`; `services/quality.py:70`; `services/downloader.py:668-673`; `services/batch_downloader.py:261-278`, `:399`, `:426`, `:455`. Both trees identical — no `cli.py` or `config.py` anchor is load-bearing here. Probe run: `uv run python -`, no file created.

**Call-site census (re-derived, `src/` and `tests/` counted separately).** `status_label(` — 7 definitions in `exceptions.py`, **4 production calls**, all at `batch_downloader.py:263,266,275,278`; 9 in `tests/`. `log_context(` — definition `exceptions.py:58` plus **exactly one** production call, `batch_downloader.py:272`; 2 in `tests/`. `user_message(` — definition `exceptions.py:54` only; **zero** production calls; 1 in `tests/`. `_map_exception_to_status` — definition `exceptions.py:196` only; **zero** production calls; **11** in `tests/`.

**Exact consequence.** A user running `vkdownloader batch urls.txt` on a private or removed video sees `<url>: no_streams`. An operator filtering the structured log by `error_code=quality_not_available` — the vocabulary `models/enums.py:53-58` exists to provide — cannot, because `ErrorCode.NO_STREAMS` does not exist. The three readers of one failure get names that cannot be correlated.

**Recommendation (accepted).** Pick one identifier per condition. Either delete the two-outcome branch in `status_label()` and return `ErrorCode.QUALITY_NOT_AVAILABLE.value`, deleting `_quality_not_available_status` and the `QualityNotAvailableError` row from `_EXCEPTION_STATUS_HANDLERS`; or keep `no_streams` as the user-facing wording and add `NO_STREAMS = "no_streams"` to `ErrorCode`, deriving both from the same member. Either way `exceptions.py:141-149` and `:212-217` must be made to agree. The second option is preferred: it preserves the user-facing wording the batch summary was written for, and it removes the filter gap without a batch-output change.

---

### QLT-002: The taxonomy's log-context rung is reached by one condition out of six, and the two commands disagree about which

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from the tree, and the headline number is exact. `log_context(` occurs at `exceptions.py:58` (the definition) and `batch_downloader.py:272` (the only call) — **one** production call site in the whole source tree, on the single condition that has its own ladder clause. `services/batch_downloader.py:261-293` re-read clause by clause: `QualityNotAvailableError` (261-263) emits `e.status_label()` and no log call; `VideoNotFoundError` (264-266) likewise; `ExtractionError` (267-275) is the only one calling `logger.error(..., **e.log_context())`; `VKDownloadError` (276-278) likewise. Three of four log nothing.
>
> The `cli.py` anchors are cited at working-tree line numbers and were re-derived at `HEAD` as well; both are content-identical at a uniform +18 shift (`cli.py:222-266`→`HEAD:204-248`, `cli.py:263-266`→`HEAD:245-248`, `cli.py:356-374`→`HEAD:338-356`). The ladder names the same conditions in the same order on both trees, so the finding does not depend on the drift. `cli.py:263-266` is `except Exception:` → `logger.exception("download_failed", url=sanitize_url_for_log(url))` → `"An error occurred during download"`, carrying no code. Confirmed.
>
> The per-condition reachability table reproduces: `ExtractionError` is raised at `infrastructure/browser.py:47` and `services/extractor.py:215,231,252,275`; `DownloadError` at `services/ffmpeg_utils.py:444`; neither is named by `cli.py`'s ladder, so both fall to `cli.py:263`. `VKDownloadError` is never raised directly in `src/`. The claim "five of the six subclasses the product can raise have zero log-context call sites" holds.
> - **See also:** `QLT-001` (the `QualityNotAvailableError` clause is one of the three that logs nothing) · `08-cli-observability` phase corpus (exit codes and message surfaces are that phase's subject, not this one)

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | HIGH — **re-derived, unchanged** |
| **Type** | `SPEC-DEVIATION` — confirmed (`exceptions.py:1-9` declares the vocabulary; the ladders do not deliver it) |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/cli.py`, `src/vkdownloader/exceptions.py` |
| **Classification** | mandatory — confirmed |

**Description.** The module docstring declares that every domain exception carries a machine-readable `ErrorCode` and a polymorphic `status_label()` "so that structured JSON logs and batch results can be filtered deterministically", and `log_context()` exists to feed structlog. In production, `log_context()` has one call site, and the single-video command records no `error_code` on any path.

**Evidence (re-derived).** `exceptions.py:1-9`, `:58-67`; `batch_downloader.py:261-293`; `cli.py:222-266`, `:356-374` (both trees); `infrastructure/browser.py:47`; `services/extractor.py:215,231,252,275`; `services/ffmpeg_utils.py:444`; `services/ytdlp_downloader.py:130`.

**Exact consequence.** The same browser-launch failure is `{"event": "extraction_error", "error_code": "extraction_error", …}` under `batch` and `{"event": "download_failed", "url": "…"}` with no code under `download`. An operator cannot tell from the log which of the six domain conditions ended a single-video run, on the command most users run.

**Recommendation (accepted, and preferred over the source report's alternative).** Make the two terminal handlers symmetric rather than adding new ones. In `cli.py`, catch `VKDownloadError` before the generic `Exception` clause and emit `logger.error("download_failed", url=…, **e.log_context())`, matching `batch_downloader.py:267-275`; add the same one-line call to `batch_downloader.py:261-263` and `:264-266`. The source report's fallback — delete `log_context()` and `error_code` — is recorded here as **rejected as the alternative**: the `error_code` vocabulary is the mechanism the project built for exactly this and `models/enums.py:53-58` states its purpose; removing it costs more than the two call sites it costs to wire up.

---

### QLT-003: `docs/STRUCT.md` omits one source file and three of its rows contradict the file they name

> **Validation Note:**
> - **Action:** validated · **severity re-derived MEDIUM → LOW**
> - **Detail:** Every claim reproduces. The document's fenced tree (`docs/STRUCT.md:7-44`) names 30 paths, all of which resolve — `stealth.min.js` included (`Test-Path` → `True`). One source file is unnamed: `src/vkdownloader/services/ytdlp_downloader.py`. The three contradicted rows reproduce verbatim:
>
> | Document row | What the named file declares | Verdict |
> |---|---|---|
> | `STRUCT.md:28` `concurrency.py # Concurrency primitives (re-export / compatibility)` | 16 lines; one `class SemaphoreLike(Protocol)` at `:8-16`; no `__all__`, no re-export, no shim | contradicted |
> | `STRUCT.md:22` `dtos.py # Data transfer objects (Stream, StreamInfo)` | one class, `HLSDownloadRequest` (`dtos.py:11`); `Stream` is at `models/video.py:15`; `StreamInfo` occurs 0 times in `src/` and `tests/` | contradicted |
> | `STRUCT.md:39` `utils/__init__.py # Exports sanitize_url_for_log, _strip_auth_params, validate_output_path` | the file's own `__all__` (`:6-12`) has five entries; `sanitize_title` and `_resolve_output_file` are unnamed | contradicted |
>
> The unfiled imprecision at `STRUCT.md:23` (`Quality`/`Method` for `QualityEnum`/`DownloadMethod`) is confirmed. A **fourth** imprecision the source report did not file is confirmed at `STRUCT.md:24`, `video.py # Video metadata dataclass` — `models/video.py` declares three `pydantic.BaseModel` subclasses and no dataclass. It is recorded here and not filed, for the same reason the third was not: it does not change a reader's action.
>
> **Denominator corrected.** The title and the body both say "one of 31 source files". The source tree holds **30** `.py` files. The document names 29 of them (30 paths, one of which is `stealth.min.js`). The missing file count of 1 is right; the denominator is not. The finding's own Denominator row, "30 paths named", is the correct figure and contradicts its own headline.
>
> **Severity re-derived LOW.** `99-audit-validate.md` §8 reserves LOW for "a `DOC-UPDATE` candidate". This is one, it is advisory, and it changes no product behaviour — the code is the defensible side on all three contradicted rows, so the fix is four one-line edits to one document. MEDIUM was not supportable under this phase's table.
> - **See also:** `QLT-004` (the same tree, described by two generated maps) · `QLT-005` (a third document describing the same tree)

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW — **re-derived from MEDIUM** |
| **Type** | `DOC-UPDATE` — confirmed (code is correct; the document is wrong) |
| **Affected Modules** | `docs/STRUCT.md`, `src/vkdownloader/**` |
| **Classification** | advisory — confirmed |

**Description.** The project's own architecture document is the navigation map for `src/vkdownloader`. Checked in both directions, one module is missing and three rows describe something the named file does not contain. No product behaviour follows; the map a new maintainer trusts first is wrong in four places out of thirty.

**Evidence (re-derived).** `docs/STRUCT.md:7-44`, and per row: `services/concurrency.py` (16 lines), `models/dtos.py:11`, `models/video.py:15`, `models/enums.py:6,37`, `utils/__init__.py:6-12`, `services/ytdlp_downloader.py:313,564,731`. Denominator: the 30 `.py` files under `src/vkdownloader/`, enumerated.

**Recommendation (accepted).** Add the `services/ytdlp_downloader.py` row; correct the three descriptions to what the files declare; correct `Quality`/`Method` to `QualityEnum`/`DownloadMethod`; correct `video.py`'s "dataclass" to "Pydantic models". Five one-line edits to one document. No code change — on all three contradicted rows the code is the more defensible choice.

---

### QLT-004: The generated structure maps record 23 of 30 source files and two symbols that no longer exist

> **Validation Note:**
> - **Action:** validated · **one supporting claim re-derived as false** · **severity re-derived MEDIUM → LOW**
> - **Detail:** The claim reproduces exactly. `.ai/structure/back/py_map.yaml` holds 23 entries against 30 `.py` files on disk, 0 recorded-but-absent, **7 present-but-unrecorded**: `__main__.py`, `services/batch_downloader.py`, `services/concurrency.py`, `services/progress_display.py`, `services/ytdlp_downloader.py`, `utils/correlation.py`, `utils/formatting.py`. Two recorded symbols do not exist: `models/enums.py` records class `SegmentRetryResult` (`py_map.yaml:116`) where the module declares seven `StrEnum` classes and none of them that; `cli.py` records function `_create_progress_callback` (`py_map.yaml:22`) and no such symbol exists. The recorded `cli.py` entry describes a superseded module: `classes: [DownloadContext]`, `functions: [_create_progress_callback, callback, _print_batch_summary, download, batch_download, cli]`, `imports: [… dataclasses … services.quality …]` (`py_map.yaml:1-27`) — `DownloadContext` and `_print_batch_summary` are now top-level names of `services/batch_downloader.py`, and `cli.py` imports neither `dataclasses` nor `services.quality` (read at both trees; the import block is one of the two hunks the concurrent edit changed, and neither module appears on either side of it). `.ai/structure/map.md` omits the same 7 files, at `:4-9` (no `__main__.py`), `:35-44` (services) and `:57-60` (utils) — all confirmed.
>
> **One supporting claim does not hold, and it is the claim the recommendation rests on.** The report states: *"`.ai/builders/` is tracked (`.ai/builders/back/run.md`, `.ai/builders/front/run.md`), so every recorded path resolves from a clean checkout. No unresolvable path."* `git ls-files .ai/builders` returns **empty**, and `git check-ignore -v .ai/builders/back/run.md` reports `.gitignore:41: .ai/builders/`. The directory exists in this working copy and the recorded path resolves here (`Test-Path "…\.ai\builders\..\..\src\vkdownloader\cli.py"` → `True`), but a clean checkout contains no `.ai/builders/`. So the inference "resolves from a clean checkout" is unsupported, and the report's own conclusion — that the `.ai\builders\..\..\src\` prefix is the defect to fix — is the one thing the false tracking claim was being used to rule out. The verdict "no unresolvable path" survives on this tree; its stated reason does not, and the reason is the part a reader would act on.
>
> **Severity re-derived LOW**, on the same row as `QLT-003`: a `DOC-UPDATE` candidate, advisory, no product behaviour affected. The two generated maps are declared generated and nothing regenerates them, so the drift widens on its own — that is a maintenance cost, not a correctness one.
> - **See also:** `QLT-003` (the hand-maintained map of the same tree)

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | LOW — **re-derived from MEDIUM** |
| **Type** | `DOC-UPDATE` — confirmed |
| **Affected Modules** | `.ai/structure/back/py_map.yaml`, `.ai/structure/map.md`, `src/vkdownloader/**` |
| **Classification** | advisory — confirmed |

**Description.** Both machine-generated structure maps are stale against the tree they describe: 23 of 30 files recorded, two named symbols absent, and a `cli.py` entry describing a module that `a335b2a` and `ea44b3d` replaced. `.ai/structure/map.md` records the same 7 omissions as a raw `tree /F` dump.

**Evidence (re-derived).** `.ai/structure/back/py_map.yaml:1-27` (`cli.py`), `:105-117` (`models/enums.py`), 23 `- path:` keys; `git ls-files .ai/builders` → empty; `git check-ignore -v .ai/builders/back/run.md` → `.gitignore:41`; `.ai/structure/map.md:4-9`, `:35-44`, `:57-60`; `git log --oneline` for the four commits the maps predate (`eedfff0`, `d62671b`, `ea44b3d`, `a335b2a`).

**Two further staleness facts, recorded and not filed.** `map.md:17,19` still list `adaptive_throttle.cpython-312.pyc` and `http_client.cpython-312.pyc` under `__pycache__` — modules that no longer exist in `src/`. And the two maps use different inclusion rules: `docs/STRUCT.md:3-5` explicitly excludes build artifacts, while `map.md` records `__pycache__/` and `vkdownloader.egg-info/`. A regeneration that adopts the `STRUCT.md` rule would be the correct fix for both.

**Recommendation (accepted, with the correction above applied).** Regenerate both artefacts from the tree rather than hand-patching; every one of the seven omissions and both absent symbols disappear in one pass. If regeneration is not available in this pipeline, delete them — a stale generated map that is never regenerated is trusted and is wrong. Separately, change the recorded prefix from `.ai\builders\..\..\src\` to `src\`, and correct the report's claim that the directory is tracked: it is gitignored, which is why the prefix is unsafe rather than merely ugly.

---

### QLT-005: `vkdownloader-overview.md` states a universal export claim that fails for 25 of 28 names, and describes a model that does not exist

> **Validation Note:**
> - **Action:** validated · **severity re-derived MEDIUM → LOW**
> - **Detail:** All three claims reproduce, and the arithmetic is exact.
>
> 1. **The universal export claim.** `docs/01-tools/vkdownloader-overview.md:330`, verbatim: *"All modules export their public APIs through `downloader.py` for backward compatibility."* The claim is a **document** claim, not a code docstring — `services/downloader.py`'s own module docstring (`:1-7`) says nothing about re-exporting other modules' APIs; the backward-compat intent lives in per-import `# noqa: F401 — backward-compat re-export` comments (`downloader.py:31,33,58-60`) and in the narrower claim at `:328` ("The `__all__` re-export facade in `downloader.py` preserves all public symbol paths"). The universal claim at `:330` is a separate sentence and it is false. Re-derived by AST over all nine `__all__` lists: `services/downloader.py` holds **26 entries / 25 unique** (it repeats `_format_argfile`); the other eight lists declare **28 entries**; exactly three are reachable through it — `HLSDownloader`, `_cookies_to_netscape`, `setup_signal_handlers`. 25 of 28 are not. The finding's absent-name enumeration is itself correct, checked name by name: the three it omits from `services/__init__.py`, `services/cookies.py`, `services/signal_handlers.py` and `utils/url_sanitizer.py` are precisely the reachable ones.
> 2. **The named model.** `:212-218` describes a `DownloadProgress` model with `speed`, `eta_seconds`, `percent`. `DownloadProgress` occurs in **0** files under `src/` and **0** under `tests/`; `eta_seconds` occurs **0** times under `src/`. The document also contradicts itself: `:202` correctly states that `progress_callback` receives `FfmpegProgress` objects. Both confirmed.
> 3. **The line count.** `:324` states `ffmpeg_utils.py (~360 lines)`; the file is **515** lines. The three adjacent counts (`:321-323` `~582`, `~722`, `~901` for `downloader.py`, `ytdlp_downloader.py`, `segment_downloader.py`) measure 703, 779, 939 — within ~20 %, and correctly not filed.
>
> **Severity re-derived LOW**, on the same row as `QLT-003` and `QLT-004`: a `DOC-UPDATE` candidate, advisory, no product behaviour affected. A reader who follows `:330` reaches an `ImportError` on four named symbols — real, but the fix is one deleted sentence, and an `ImportError` is self-announcing rather than silent.
> - **See also:** `QLT-003` · `QLT-004` (the same tree, four documents stale) · `01-entry-architecture` ENT-005/006 (the `downloader.py` facade itself is that phase's subject, not this one)

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW — **re-derived from MEDIUM** |
| **Type** | `DOC-UPDATE` — confirmed |
| **Affected Modules** | `docs/01-tools/vkdownloader-overview.md`, `src/vkdownloader/**` |
| **Classification** | advisory — confirmed |

**Description.** Three claims in one tool document fail against the code they name: a universal claim about how the package exports its API, a model described field by field that does not exist, and a stated line count the tree contradicts.

**Evidence (re-derived).** `docs/01-tools/vkdownloader-overview.md:202`, `:212-218`, `:321-324`, `:328`, `:330`; the nine `__all__` lists enumerated by AST; repository-wide search for `DownloadProgress` and `eta_seconds`; `services/ffmpeg_utils.py` line count 515.

**Exact consequence.** A maintainer told this document is where the package's API is re-exported from reaches an `ImportError` for `RichProgressReporter`, `NetworkMonitor`, `sanitize_url_for_log` or any model type. A reader of §"DownloadProgress Model Enhancement" is told a model has three named fields and finds no such model.

**Recommendation (accepted).** Delete `:330` and replace it with the true statement — `services/downloader.py` re-exports its own module's surface; the package's other modules export through their own `__all__`. Delete the `DownloadProgress Model Enhancement` section at `:212-218` outright. Correct `~360` to `~515` at `:324`, or drop the counts at `:321-324` entirely, since a hand-maintained count drifts again.

---

### QLT-006: Two copies of the CLI reference declare the same document id, have already diverged on facts, and nothing chooses between them

> **Validation Note:**
> - **Action:** validated · **severity re-derived MEDIUM → MEDIUM (unchanged)**
> - **Detail:** Every substantive claim reproduces, measured on raw bytes. Both files open with `---` / `id: cli-reference` at line 2. Encoding: `cli-reference.md` = 10 233 bytes, **12** U+2014 em-dashes, **1** `?`, LF; `cli-reference-clean.md` = 10 196 bytes, **0** em-dashes, **15** `?`, CRLF throughout. The copy named "clean" is the typographically damaged one, exactly as claimed. The four divergent rows all check out against the code:
>
> | Row | `cli-reference.md` | `cli-reference-clean.md` | What the code says |
> |---|---|---|---|
> | `--cookie-source` short flag | none listed | `-c` | `cli.py:159-164` (working tree) = `HEAD:141-146`: `typer.Option(None, "--cookie-source", "-c", …)`. **`-c` exists** → `cli-reference.md` wrong |
> | `--cookie-source` values | "`none`, `browser`, or `file`", plus a `file` row at `:212` "Load cookies from external file (future enhancement)" | "`none` or `browser`" | `models/enums.py:45-49` declares `CookieSource` with exactly `NONE` and `BROWSER`. **No `file` source exists** → `cli-reference.md` documents a feature that does not exist |
> | `--ssl-verify` default | `verify` | `true` | `cli.py:165-169` (working tree) = `HEAD:147-151` declares `bool \| None` defaulting to `None`; `config.py:77-80` (working tree) = `HEAD:79-82` declares `ssl_verify: bool = Field(default=True, …)`. **`verify` is not a producible value** → `cli-reference.md` wrong |
> | `batch` step list | 7 steps (`:141`, `:145`) | 6 steps (`:141-144`) | `cli.py:328-338` = `HEAD:310-320` validates and counts skipped URLs; `batch_downloader.py:437-438` prints the count. **`cli-reference-clean.md` wrong** |
>
> The rule being broken is stated at `docs/00-overview/doc-maintenance-rules.md:18`: *"**Single source of truth:** Each fact lives in exactly one file."* Both trees agree on all four code anchors.
>
> **Citation corrections, which do not change any claim.** The two options tables are at physical lines **67/128** (`--cookie-source`) and **68/129** (`--ssl-verify`), not the 69/130 and 70/131 cited. The `file` row is at `:212` and the step-list rows at `:141`/`:145` exactly as cited. The document lengths "179 lines" and "177 lines" are **non-blank** line counts; the physical files hold **254** and **252** lines. The "462 lines between them" in `QLT-008` is affected by the same method.
>
> **Severity held at MEDIUM, and this is the one place the source report's severity is right for a `DOC-UPDATE`.** Unlike `QLT-003`/`QLT-004`/`QLT-005`, the two errors here are not self-announcing: a reader who opens `cli-reference.md` concludes the tool has a `file` cookie source and no `-c` flag, and writes a configuration against a feature that does not exist. Nothing errors; the false premise is acted on directly. And neither copy can simply be deleted, because the factually-wrong one holds the correct typography and the factually-correct one the damaged typography — the fix is a merge, which is why this is the only `DOC-UPDATE` in the corpus filed **mandatory**.
> - **See also:** `QLT-007` (the same document set, provenance citations) · phase `08`'s corpus (the CLI option surface itself is that phase's subject; this finding is about two documents' agreement with it)

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | MEDIUM — **re-derived, unchanged** |
| **Type** | `DOC-UPDATE` — confirmed |
| **Affected Modules** | `docs/99-reference/cli-reference.md`, `docs/99-reference/cli-reference-clean.md` |
| **Classification** | mandatory — confirmed |

**Description.** Two copies of the same document share the frontmatter `id: cli-reference`, so the repository's own identity scheme cannot tell them apart. They have diverged on facts about the command line in **opposite** directions, and neither can be deleted on its own.

**Evidence (re-derived).** Byte-level measurement of both files; `git diff --no-index` between them; `cli.py:159-169` and `:328-338` read at both trees; `config.py:77-80` at both trees; `models/enums.py:45-49`; `services/batch_downloader.py:437-438`; `docs/00-overview/doc-maintenance-rules.md:18`.

**Exact consequence.** There is no rule anywhere in the repository naming either copy authoritative. A maintainer told to check "the CLI reference" opens one of two documents and reaches a false premise either way — a `file` cookie source, or a missing invalid-URL-skipping step and skipped-count output.

**Recommendation (accepted).** Merge into `docs/99-reference/cli-reference.md`: keep that file's em-dashes; take `-c`, the two-value cookie source, the `true` default and the 7-step batch list from `cli-reference-clean.md`; correct the `file` row and the `ssl-verify` default against `cli.py` and `models/enums.py`. Then delete `cli-reference-clean.md`. To stop the fork recurring, add one line to `docs/00-overview/doc-maintenance-rules.md` stating that a document's `id` is unique per repository and a second file carrying an existing `id` is a defect — the duplicate is currently invisible to every check the pipeline runs.

---

### QLT-007: Three defect identifiers cited from source code and from tool documents are defined nowhere in the repository

> **Validation Note:**
> - **Action:** validated · **severity re-derived LOW → LOW (unchanged)**
> - **Detail:** Re-derived by search across every `.py`, `.md`, `.yaml` and `.toml` in `src/`, `tests/`, `docs/`, `.ai/`, `.kilo/` and `pyproject.toml`, excluding `.kilo/worktrees/`, `.venv/` and `.temp/`. Occurrence counts match exactly; definition count is zero for all three.
>
> | Identifier | Occurrences | Definitions | Sites re-derived |
> |---|---|---|---|
> | `INT-001` | **8** | 0 | `services/downloader.py:230` (`(SEC-003/INT-001)`), `:256`, `:275`; `tests/test_hls_downloader.py:694,700,745,755,764` |
> | `SRV-006` | **4** | 0 | `services/ytdlp_downloader.py:393`; `docs/01-tools/api-reference.md:580`; `docs/01-tools/vkdownloader-overview.md:41`; **`tests/test_hls_downloader.py:3309`** |
> | `SRV-001` | **1** | 0 | `docs/01-tools/vkdownloader-overview.md:328` |
>
> Two evidence corrections that do not change the claim. The source report's site list for `SRV-006` omits a fourth site, `tests/test_hls_downloader.py:3309` (a class docstring: *"Tests for SRV-006: backoff between yt-dlp retry attempts"*) — a dead citation in the test tree, which is the same defect one file over. And the report's list of prefixes "actually in use in the shipped audit corpus", `ART, BE, BRW, CFG, CON, DF, ENT, FE, NET, OUT, SEC, SHA, TRN, VAL`, includes `BE` and `FE`, which occur in **no** findings file. They are the worked examples in the report format's own field guide (`.ai/audit/templates/audit-findings.md:66`). The load-bearing half of the claim — "No `INT-` prefix and no `SRV-` prefix exists" among live prefixes — is confirmed: the live set is `ART, BRW, CFG, CON, DF, ENT, NET, OUT, QLT, SEC, SHA, TRN`, plus `VAL` in the store.
>
> The contrast the report draws also reproduces: `D-01`/`D-04`/`D-11` resolve to `.ai/plans/done/01-confirmed-code-defects_DONE.md`, and `AC2`/`AC8`/`T9` to `.ai/plans/done/01_batch_progress_display_spec_DONE.md`.
> - **See also:** `QLT-006` (the same document set) · `QLT-008` (the same folder, wrong-project documents)

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | LOW — **re-derived, unchanged** |
| **Type** | `DOC-UPDATE` — confirmed (no code behaviour changes; three provenance trails dead-end) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `docs/01-tools/vkdownloader-overview.md`, `docs/01-tools/api-reference.md` |
| **Classification** | advisory — confirmed |

**Description.** Source comments and tool documents cite `INT-001`, `SRV-006` and `SRV-001` as the provenance for a security invariant, an inter-retry backoff decision and a refactor. None of the three is defined anywhere in the repository.

**Evidence (re-derived).** As tabulated above. `SEC-003` — the other half of the citation at `downloader.py:230` — does resolve, to a real finding in phase 06's corpus, so the sentence has one live pointer and one dead one.

**Exact consequence.** A maintainer changing `_create_temp_cookie_file` cannot find the requirement `INT-001` records; a maintainer changing the inter-retry backoff cannot find what `SRV-006` records. No code behaviour changes.

**Recommendation (accepted).** Resolve each to the document that records it, or delete it. Point the five `INT-001` sites at the real finding ID for the ffmpeg `-headers @file` misuse. Remove the `SRV-006` and `SRV-001` parentheticals at `ytdlp_downloader.py:393`, `vkdownloader-overview.md:41` and `:328`, and `api-reference.md:580` — the surrounding prose already states the rationale in full. **Do not invent new IDs to fill the gap**; an ID with no requirement behind it is the same defect one level down.

---

### QLT-008: Two documents in `docs/99-reference/` describe no code in this repository

> **Validation Note:**
> - **Action:** validated · **severity re-derived LOW → LOW (unchanged)**
> - **Detail:** Both claims reproduce.
>
> `docs/99-reference/ast-editor.md` — **41 physical lines** (the report's "31" is the non-blank count). Its opening instruction at `:16` is *"**Always run first:** `list_symbols` to discover exact names"*, and its pre-edit checklist at `:32` names `read_symbol`. `list_symbols` occurs in exactly **one** file in the repository — `ast-editor.md` itself — and in this validation artifact. It is not defined in `.kilo/agents/`, `.kilo/commands/`, `kilo.json`, `pyproject.toml` or any source file. Two further non-existent tools are named and not listed by the report: `replace_in_body` (`:33`) and `replace_function` (`:34`).
>
> `docs/99-reference/morfx-tools.md` — **600 physical lines** (the report's "431" is the non-blank count). Its own note at `:16-17` states: *"The DSL examples in this document reference `telegram_service.py` and other files that are synthetic examples for illustration purposes only. They do not correspond to actual files in this codebase. This project is a VK Video Downloader, not a Telegram posting application."* — verbatim, confirmed. The document describes no code in this repository, **and says so**.
>
> The placement rule the report invokes is confirmed at `docs/00-overview/doc-maintenance-rules.md:42`: *"Use `99-reference/` for guides and external docs."* The pair totals 641 lines, not 462.
> - **See also:** `QLT-006` (the same folder's other two files)

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | LOW — **re-derived, unchanged** |
| **Type** | `DOC-UPDATE` — confirmed |
| **Affected Modules** | `docs/99-reference/morfx-tools.md`, `docs/99-reference/ast-editor.md` |
| **Classification** | advisory — confirmed |

**Description.** `docs/99-reference/` holds four documents; two of them, 641 lines between them, describe tooling and a project this repository does not contain. `morfx-tools.md` says so in its own note; `ast-editor.md` does not.

**Evidence (re-derived).** `ast-editor.md:16,32,33,34`; `morfx-tools.md:16-17`; repository-wide search for `list_symbols`, `read_symbol`, `replace_in_body`, `replace_function`; `doc-maintenance-rules.md:42`.

**Exact consequence.** A maintainer who opens `docs/99-reference/` finds two of its four documents describing a Telegram posting application and an AST tool this project does not ship. `ast-editor.md` is the sharper case: its opening instruction is to run a command that does not exist, and a reader who follows it has no way to tell the document is inapplicable. Neither document changes product behaviour.

**Recommendation (accepted).** Move both out of the project's `docs/` tree. `morfx-tools.md` is a reasonable agent-tooling reference and belongs with the tooling that provides `morfx`. If they must stay, add a one-line banner to each naming this repository and stating that the tools described are not installed here; `morfx-tools.md:16-17` already contains that sentence and needs only promoting from a blockquote into a header. **`ast-editor.md` needs a banner, not a promotion** — it contains no such sentence, and its `:16` instruction is the specific thing a reader acts on.

---

### QLT-009: The configured mypy profile cannot enforce the project's own "no `any`" rule, and one dependency is invisible to it

> **Validation Note:**
> - **Action:** validated · **the supporting evidence is materially mischaracterised and is corrected here** · **severity re-derived MEDIUM → LOW**
> - **Detail:** The configuration claim is **confirmed exactly**. `[tool.mypy]` is `pyproject.toml:90-104` with the per-module override at `:106-108`. `strict = true` at `:92`; `ignore_missing_imports = true` at `:104`; the override relaxes `disallow_untyped_decorators` for `vkdownloader.cli` only. There is **no** `plugins` key, so pydantic's mypy plugin is not active. `disallow_any_explicit`, `disallow_any_expr` and `disallow_any_unimported` are absent from both the `strict` expansion and the explicit block. `uv run mypy --disallow-any-unimported src` → `Success: no issues found in 30 source files`, which does support "every other dependency ships `py.typed`, so `yt_dlp` is the only unmarked boundary". `yt_dlp` is imported in exactly one file (`services/extractor.py:1`) and its single attribute site `yt_dlp.YoutubeDL` is consumed at `extractor.py:211`. `uv run mypy src` passes on the working tree, so the rule has no enforcement point. **That part of the finding is right and it is the reason the finding exists.**
>
> **The "eight sites" claim is wrong, and the recommendation built on it cannot be executed at five of them.** `uv run mypy --disallow-any-explicit src` does report 8 errors in 6 files at the lines the report names — but the errors are not eight explicit `Any` annotations. Reading each line, and isolating the trigger with a minimal reproduction:
>
> | Reported site | What is actually on that line | Why mypy flags it |
> |---|---|---|
> | `services/extractor.py:40` | `def _build_streams(formats: list[dict[str, Any]]) -> list[Stream]:` | **a real explicit `Any`** |
> | `services/ytdlp_downloader.py:86-88` | `def _partition_tasks(…) -> tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]` | **real explicit `Any`**, ×2 on one line |
> | `exceptions.py:220` | `_EXCEPTION_STATUS_HANDLERS: dict[type[Exception], Callable[..., str]]` | `Callable[..., str]` is an **implicit** `Any` signature, not an explicit one. The report calls this "a concrete type already" — it accepts arbitrary arguments, which is the `Any` mypy is objecting to |
> | `models/video.py:8,15,27`, `models/dtos.py:11`, `config.py:15` | `class Video(BaseModel)`, `class Stream(BaseModel)`, `class VideoWithStreams(Video)`, `class HLSDownloadRequest(BaseModel)`, `class Settings(BaseSettings)` | **no `Any` in any of them.** Reproduced in isolation: a bare `class A(BaseModel): x: int = 1` on line 3 of an otherwise clean file yields `line 3: error: Explicit "Any" is not allowed`. The class inherits pydantic's `__init__(**data: Any)` and mypy reports it against the `class` line |
>
> The report's characterisation — "the other four being non-annotation uses inside Pydantic `model_config` dicts and a callable alias" — is wrong on every part: there are **six** such sites, not four; there is no `model_config` dict in `models/video.py` or `models/dtos.py`; and "a callable alias" describes `exceptions.py:220`, which is a module-level annotated assignment, not an alias. A grep for `\bAny\b` across `src/` returns **6** lines in **2** files (`services/extractor.py:5,40`; `services/ytdlp_downloader.py:13,87,88`) — two real annotation sites, not four. Consequently the recommendation to "fix the eight sites", and in particular to type the `models/` and `config.py` ones as `JsonValue`, **is not executable**: the `Any` is in pydantic's inherited signature, not in this repository's source.
>
> One more supporting figure is off: `uv run mypy --disallow-any-expr src` reports **216** errors in 18 files on this tree, not 224. The conclusion drawn from it — do not enable `disallow_any_expr` — is unaffected.
>
> **Severity re-derived LOW.** The claim that survives is a `BEST-PRACTICE` observation dressed as a `SPEC-DEVIATION`: the project's rule 9 says "avoid `any` completely", the profile cannot enforce it, and two real `Any` uses exist. Two sites, zero enforcement, and one unmarked boundary is a genuine gap with a small clear fix, but the consequence is a convention with no gate — not a correctness or data-loss risk, and not the 8-site remediation the report describes.
> - **See also:** the corrected remediation below · `QLT-010` (the same "derive from the enum rather than re-spell it" principle applied to `ErrorCode`)

| Field | Value |
|-------|-------|
| **ID** | QLT-009 |
| **Severity** | LOW — **re-derived from MEDIUM** |
| **Type** | `SPEC-DEVIATION` — confirmed. Rule 9 of `.kilo/rules/project.md` is a declared rule; the profile does not carry it. The `Type` stands even though the *scale* of the gap was overstated |
| **Affected Modules** | `pyproject.toml`, `src/vkdownloader/exceptions.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/ytdlp_downloader.py`. **The source report's `models/video.py`, `models/dtos.py` and `config.py` entries are withdrawn** — none of the three contains an `Any` |
| **Classification** | advisory — confirmed (the source report lists this finding under Advisory Recommendations, and it stays there) |

**Description.** Rule 9 of `.kilo/rules/project.md` says "Avoid `any` completely". The configured checker cannot enforce it: `strict = true` expands to thirteen flags, none of which is `--disallow-any-explicit`, and the three keys that would enforce it are absent from `pyproject.toml:90-104` as well. A green `mypy src` therefore certifies a rule the profile does not carry. `--disallow-any-unimported` reports nothing, so `yt_dlp` — reached from exactly one attribute site, `extractor.py:211` — is the only boundary the checker cannot see, and `ignore_missing_imports = true` stands between the caller and it.

**Evidence (re-derived).** `pyproject.toml:90-104`, `:106-108`; `uv run mypy --help` expansion of `strict`; `uv run mypy --disallow-any-explicit src` → 8 errors / 6 files; `uv run mypy --disallow-any-unimported src` → Success; `uv run mypy --disallow-any-expr src` → 216 errors / 18 files; `\bAny\b` across `src/` → 6 lines in 2 files; minimal reproduction of the `BaseModel` trigger; `services/extractor.py:1,211`; suppression inventory — one `# type: ignore[union-attr]` at `infrastructure/browser.py:103`, **0** `cast(Any, …)` sites, **0** `type: ignore` in `tests/`, all three confirmed.

**Exact consequence.** `mypy src` passes with two explicit `Any` uses in the tree, and nothing in the configured pipeline fails if a third is added. The single third-party integration the checker cannot see has no signature check at all.

**Recommendation (corrected, and materially smaller than the report's).** Add `disallow_any_explicit = true` to `pyproject.toml:90-104` and expect **five** of the eight diagnostics, not three of eight: `exceptions.py:220` — narrow the `Callable[..., str]` to the signature the handlers actually share, or type the dict as `Mapping[type[Exception], Callable[[Exception], str]]` and fix the one handler that needs more. `services/extractor.py:40` and `services/ytdlp_downloader.py:86-88` — the real two, each a concrete narrowing at the point of use. The remaining five (`models/video.py:8,15,27`, `models/dtos.py:11`, `config.py:15`) are pydantic's inherited `__init__(**data: Any)` and **cannot be fixed in this repository's source**; they need either a per-module `[[tool.mypy.overrides]]` disabling `disallow_any_explicit` for the `models` and root modules, or a `# mypy: disable-error-code="explicit-any"` on the five class lines, or acceptance of a permanently red `mypy src`. Choose one explicitly rather than discovering it when the key is switched on. Do **not** add `disallow_any_expr` — 216 sites, almost all structlog and Typer surface.

---

### QLT-010: `ErrorCode` member values are re-spelled as bare string literals in every `status_label()` override

> **Validation Note:**
> - **Action:** validated · **one descriptive sentence corrected** · **severity re-derived MEDIUM → MEDIUM (unchanged)**
> - **Detail:** The evidence table reproduces site for site, and I re-checked every row against `models/enums.py`:
>
> | Site | Literal | `ErrorCode` member it duplicates |
> |---|---|---|
> | `exceptions.py:77` | `"video_not_found"` | `VIDEO_NOT_FOUND` (`enums.py:60`) |
> | `exceptions.py:106` | `"invalid_url"` | `INVALID_URL` (`enums.py:61`) |
> | `exceptions.py:149` | `"quality_not_available"` | `QUALITY_NOT_AVAILABLE` (`enums.py:62`) |
> | `exceptions.py:183` | `"extraction_error"` | `EXTRACTION_ERROR` (`enums.py:64`) |
> | `exceptions.py:193` | `"download_error"` | `DOWNLOAD_ERROR` (`enums.py:65`) |
>
> `exceptions.py:173` returns `"invalid_quality"`, which is **not** an `ErrorCode` member — `QualityParseError.error_code` is `ErrorCode.QUALITY_PARSE_ERROR` (`enums.py:63`, value `quality_parse_error`) — so that condition carries a second identifier too, as the report records. The base `status_label()` at `exceptions.py:52` derives its label from `self.error_code`, which is the correct pattern and the report says so.
>
> **The descriptive sentence is wrong, and the evidence table is right.** The report says: *"Five of the six subclasses do this; the sixth (the base) derives the label from `self.error_code`."* There are **seven** classes — one base (`VKDownloadError`) and **six** subclasses — and all six subclasses override. The accurate statement is: six overrides, of which **five** duplicate their own `ErrorCode` member's value and **one** (`QualityParseError`) diverges from it entirely. The base is not a subclass. The finding's own next paragraph gets this right, so the slip is in one sentence and does not touch the evidence.
>
> The test-pinning claim reproduces: `tests/test_exceptions.py:123,128,133,138,143,148,153,158` hard-code the eight expected label strings rather than reading them from `ErrorCode`, so a rename passes the suite. The report's "not filed" list of legitimate literal sites also holds — `ffmpeg_utils.py:80,256`, `downloader.py:303` spell the `ffmpeg` **binary name**; `extractor.py:51` compares yt-dlp's own `vcodec` value; `ytdlp_downloader.py:257` is a format selector; `:158-165` parses yt-dlp's progress suffixes; `ffmpeg_utils.py:111` keys on ffmpeg's `-progress` keys; and `progress_display.py:83-93` returns display words, with its own comment at `:80-82` recording the `match`-over-StrEnum choice as rule 10 applied. That exclusion is correct and is recorded as justified, not filed.
> - **See also:** `QLT-001` (complement, **not** a merge — different subjects, same root cause) · the ordering constraint in `VAL-903`

| Field | Value |
|-------|-------|
| **ID** | QLT-010 |
| **Severity** | MEDIUM — **re-derived, unchanged** |
| **Type** | `SPEC-DEVIATION` — confirmed. `ErrorCode` is the project's declared source of truth for these identifiers (`enums.py:53-58`); re-spelling them in a second place is a deviation from the declared design, not a preference |
| **Affected Modules** | `src/vkdownloader/exceptions.py`, `src/vkdownloader/models/enums.py`, `tests/test_exceptions.py` |
| **Classification** | advisory — confirmed |

**Description.** Every exception subclass overrides `status_label()` with a hand-written string that duplicates — or, in one case, contradicts — the value of its own `ErrorCode` member, and nothing checks that the two agree. The one override that derives from `self.error_code` is the base, and it is the correct pattern.

**Evidence (re-derived).** `exceptions.py:52`, `:77`, `:106`, `:149`, `:173`, `:183`, `:193`, `:220`; `models/enums.py:52-67`; `tests/test_exceptions.py:123-158`; `services/progress_display.py:80-93`.

**Exact consequence.** Renaming an `ErrorCode` member's value — a supported operation, since the values are the strings log aggregators filter on — silently leaves `status_label()` returning the old string. Nothing in `mypy`, `ruff` or `pytest` can catch it, because both spellings are valid `str` and the suite hard-codes the literals. The failure surfaces only as a log filter that no longer matches.

**Recommendation (accepted, with a sequencing constraint).** Make the label a single derivation from the enumeration. Either delete the five duplicating overrides and let the base at `exceptions.py:52` do the work — accepting the `"error: "` prefix — or, preferred, change the base to return `self.error_code.value` and delete **all six** overrides, which additionally makes `QualityParseError`'s `"invalid_quality"` divergence disappear without inventing an `INVALID_QUALITY` member. Then change `tests/test_exceptions.py:123-158` to assert against `ErrorCode.<MEMBER>.value` so a rename fails the suite. **The second form must not be applied together with `QLT-001`'s fix** — both prescribe edits inside `exceptions.py:141-149`. See `VAL-903`.

---

### QLT-011: `services/downloader_throttle.py` carries four unrelated concerns in 371 lines under one module name

> **Validation Note:**
> - **Action:** validated · **every recomputed number confirmed** · **rollout constraint filed as `VAL-903`**
> - **Detail:** The source report records that its first AST pass missed `AnnAssign` and that the recomputed values are what this finding cites. **I recomputed the measurement from scratch, counting assignments and annotated assignments both, and every figure reproduces exactly.**
>
> | Measure | `downloader_throttle.py` | Claimed | Match |
> |---|---|---|---|
> | physical lines | 371 | 371 | yes |
> | top-level definitions | **11** = 7 functions/classes + 4 module-level constants | 11 (7 + 4) | yes |
> | longest single definition | 96 (`_retry_429_with_backoff`, `:174-269`) | 96 | yes |
> | definitions per 100 lines | 2.96 | 2.96 | yes |
> | `services/segment_downloader.py` | 30 definitions / 940 lines = **3.19** | 3.19 | yes |
> | `services/ytdlp_downloader.py` | 13 definitions / 780 lines = **1.67** | 1.67 | yes |
>
> The four constants are `logger` (`:16`), `_DEFAULT_DOWNLOAD_TIMEOUT` (`:19`), `RETRYABLE_STATUS_CODES` (`:22`) and `_shutdown_event_ctx` (`:26`) — the `AnnAssign` forms the first pass missed. The labelled inventory reproduces span for span: shutdown signalling 18 lines (`:26-43`), `URLBackoffCoordinator` 30 (`:46-75`), `ProgressManager` 94 (`:78-171`), retry policy **198** (`:174-371` = 96 + 32 + 33 + 31, at `:174-269`, `:272-303`, `:306-338`, `:341-371`).
>
> The report is also right to state that density alone does not separate this file — `services/ffmpeg_utils.py` sits at 3.68 and `exceptions.py` at 4.37, both higher, and neither is filed. The separation is made by the labelled inventory, which is the method the phase asked for, and the report says so explicitly rather than overclaiming. The `docs/STRUCT.md:31` row — *"Adaptive throttling (ProgressManager, URLBackoffCoordinator, get_shutdown_event)"* — names three of the four concerns and none of the four retry-policy functions, confirmed.
>
> Reachability is confirmed: `ProgressManager` occurs at `downloader_throttle.py:78` and `:87` only, and **zero** times elsewhere in `src/`. The class is documented as retained at `:84-87`, so the dead-code reconciliation of block (e) returns "not dead code — future-proofing, documented", and it is correctly not filed as such. `tests/test_downloader_throttle.py:686-748` does instantiate it six times, and `tests/test_cli.py:690` asserts `not hasattr(batch_downloader, "ProgressManager")` — so the class is exercised by the suite while no production caller instantiates it, which is exactly the "documented retained" state the report describes.
> - **See also:** `VAL-903` (the recommended split is not safe to apply as written) · `QLT-013` (a comment inside one of the four functions this finding would move)

| Field | Value |
|-------|-------|
| **ID** | QLT-011 |
| **Severity** | MEDIUM — **re-derived, unchanged** |
| **Type** | `SPEC-DEVIATION` — confirmed against `docs/STRUCT.md:31` and the project rule that a module holds one concern; `.ai/context/python-code-standards.md` requires small single-responsibility modules, and 198 of 371 lines serve a concern neither the module name nor the architecture document names |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `docs/STRUCT.md`, `tests/test_downloader_throttle.py`, `tests/test_hls_downloader.py` |
| **Classification** | advisory — confirmed |

**Description.** One module named for throttling holds four concerns that share no state and no caller: process-level shutdown signalling, per-URL backoff coordination, a legacy progress-state manager, and an HTTP 429 retry policy. The cost filed is navigation, and the report is explicit that the file is not declared wrong for being large.

**Evidence (re-derived).** Per-file AST measurement of all 30 source files on three axes; the labelled inventory above; `docs/STRUCT.md:31`; `segment_downloader.py:23-28,162,251-252,254`; `ytdlp_downloader.py:24-25,399,402`; `services/downloader.py:33,198`; the `ProgressManager` occurrence census.

**Exact consequence.** A maintainer looking for the 429 retry policy has no entry point into this file — neither the module name nor the architecture document's one-line row points at `_retry_429_with_backoff`, `_parse_retry_after`, `_compute_backoff_delay` or `_wait_with_shutdown`, which are 198 of the file's 371 lines and are called from two other modules. Finding them means reading the file. Nothing breaks at runtime; the cost is entirely the search.

**Recommendation (accepted as a direction; the cost estimate is incomplete — see `VAL-903`).** Split the retry policy into its own module — `services/http_retry.py` — holding `_retry_429_with_backoff`, `_parse_retry_after`, `_compute_backoff_delay`, `_wait_with_shutdown` and `RETRYABLE_STATUS_CODES`, and add the row to `docs/STRUCT.md:31`. That leaves three concerns whose existing module name already describes two of them. Do **not** attempt a broader reorganisation of the service layer; nothing in the measurement calls for one. The source report describes the change as "a file move plus an import change in each of the two callers" — that is four changes, and there are nine. See `VAL-903` for the six it omits and for the order they must be applied in.

---

### QLT-012: Import form is relative in 15 files and absolute in 3

> **Validation Note:**
> - **Action:** reclassified · `SPEC-DEVIATION` → `BEST-PRACTICE`
> - **Detail:** **The measurement is exact and reproduces perfectly.** Excluding the four `__init__.py` files, the 25 remaining modules split as follows, confirmed by AST classification of every `ImportFrom` node:
>
> | Form | Count | Files |
> |---|---|---|
> | relative only | 15 | `cli.py`, `infrastructure/browser.py`, `infrastructure/network_monitor.py`, `models/video.py`, `services/batch_downloader.py`, `services/downloader.py`, `services/downloader_throttle.py`, `services/extractor.py`, `services/ffmpeg_utils.py`, `services/progress_display.py`, `services/quality.py`, `services/segment_downloader.py`, `services/signal_handlers.py`, `services/ytdlp_downloader.py`, `utils/security.py` |
> | absolute `vkdownloader.*` | 3 | `__main__.py`, `config.py`, `exceptions.py` |
> | neither | 7 | `models/dtos.py`, `models/enums.py`, `services/concurrency.py`, `services/cookies.py`, `utils/correlation.py`, `utils/formatting.py`, `utils/url_sanitizer.py` |
>
> Both lists match the report file for file. The four absolute statements are `__main__.py:3`, `config.py:12`, `exceptions.py:13` and the in-function `exceptions.py:100`; the last one's comment at `:97-99` gives the reason — *"Imported lazily to avoid a circular import"* — and is load-bearing (proved by phase 01's validator), which the report records as justified.
>
> **Why the `Type` changes.** `99-audit-validate.md` §8 defines `SPEC-DEVIATION` as "the finding contradicts **the project's own declared rule**." I searched `.kilo/rules/project.md`, `.kilo/rules/commands.md`, `.ai/context/python-code-standards.md`, `.ai/context/commands.md`, `docs/00-overview/doc-maintenance-rules.md` and `docs/STRUCT.md` for any declared rule on import form. **There is none.** The only `import` statements in those documents concern *which layers may import which* — `docs/STRUCT.md:48-49` — never relative versus absolute. `mypy src` accepts both (`Success: no issues found in 30 source files`), and `ruff check src tests` passes with both. A deviation from an undeclared convention is `BEST-PRACTICE`: "a defensible arrangement with a demonstrated gap" (§8), which is precisely what this is.
>
> The `Type` change is not cosmetic, and it is what changes the recommendation's standing. Rule 7 of `.kilo/rules/project.md` says *"Follow Existing Patterns"* — the existing pattern is 15 to 3, which points the same way as the finding. But the **three** exceptions are the package's import spine: `__main__.py` is the `python -m vkdownloader` entry point, and `config.py` and `exceptions.py` are the two modules nearly every other module depends on. `__main__.py` executing as a module makes a relative import legal, so the change is not a correctness matter; it is a three-line stylistic normalisation with a real but small payoff (a tree-wide search for either form now finds every file) and a small real cost (the boundary files stop looking like boundary files). The finding is right that the asymmetry trips a search and wrong to call it a spec deviation.
> - **See also:** `01-entry-architecture` ENT-005/006/007 (import graph, cycles, re-export facades are that phase's subject) · `exceptions.py:97-99` (the justified deferral, retained)

| Field | Value |
|-------|-------|
| **ID** | QLT-012 |
| **Severity** | LOW — **re-derived, unchanged** |
| **Type** | **`BEST-PRACTICE`** — reclassified from `SPEC-DEVIATION` |
| **Affected Modules** | `src/vkdownloader/__main__.py`, `src/vkdownloader/config.py`, `src/vkdownloader/exceptions.py` |
| **Classification** | advisory — confirmed |

**Description.** Of the 25 non-package-root modules, 18 import a sibling at all. Fifteen use the relative form and three the absolute `vkdownloader.…` form, so a tree-wide search for the dominant form misses three files — two of which, the settings model and the exception hierarchy, are imported by most of the other eighteen. Neither form is wrong and the checker accepts both.

**Evidence (re-derived).** AST classification of every `ImportFrom` in the 30 source files; the three absolute statements at `__main__.py:3`, `config.py:12`, `exceptions.py:13`, `exceptions.py:100`; the deferral comment at `exceptions.py:97-99`; `mypy src` and `ruff check src tests` both clean on the working tree.

**Exact consequence.** A tree-wide search for the form fifteen files use returns nothing for `config.py`, `exceptions.py` or `__main__.py`, and a reader moving between modules must know which convention each file follows before a name resolves. Nothing fails.

**Recommendation (accepted as optional, and downgraded from a fix to a normalisation).** If the tree is to be uniform, convert the three to the relative form the other fifteen use — `from .models.enums import …` in `config.py:12`, `from .cli import cli` in `__main__.py:3`, and `from .utils.url_sanitizer import …` in `exceptions.py:100`. Three lines, no behaviour change. Leave `exceptions.py:100` lazy; change only its import style. **If instead the boundary is meant to read as a boundary**, record the convention in `docs/STRUCT.md`'s Layering section — that turns an undeclared convention into a declared one, which is what this finding actually needs to become a `SPEC-DEVIATION`. Recording the convention is worth more than the three-line conversion, and neither is urgent.

---

### QLT-013: The comment on `_compute_backoff_delay` says `Retry-After` overrides the calculated delay; the code treats it as a floor, and a test pins that

> **Validation Note:**
> - **Action:** validated · **severity re-derived LOW → LOW (unchanged)**
> - **Detail:** Re-derived verbatim, and the finding is exact on every element.
>
> `services/downloader_throttle.py:334-336`, unchanged in both trees (this file is not one of the two under concurrent edit):
>
> ```python
>     # Prefer Retry-After header over calculated delay
>     if retry_after_seconds is not None:
>         delay = max(delay, retry_after_seconds)
> ```
>
> `max()` makes `Retry-After` a **lower bound**: the delay is only ever raised to it, never lowered. The two pinning tests reproduce at the lines cited — `tests/test_downloader_throttle.py:598-603` `test_retry_after_overrides_delay` asserts the raising case (`jitter 0.5, Retry-After 5.0 → 5.0`), and `:605-610` `test_retry_after_ignored_when_smaller` asserts the floor case (`jitter 2.0, Retry-After 1.0 → 2.0`), naming the behaviour in the test name itself. The two callers reproduce: `services/segment_downloader.py:251-252` supplies the parsed header, and `services/ytdlp_downloader.py:399` calls `_compute_backoff_delay(500, retry_count, None)` — no header, so the branch is not taken on the yt-dlp path, exactly as the report says.
>
> The report is also right that the docstring one level up is **not** part of this finding: `downloader_throttle.py:314` says *"Respects Retry-After header if present"*, which `max()` satisfies exactly. Scoping the finding to the inline comment is the correct call, and it is the difference between a one-word fix and a behavioural change.
> - **See also:** `QLT-011` (`_compute_backoff_delay` is one of the four functions that finding would move — the comment fix is independent of the move) · phase `03` (whether the floor policy is *right* is that phase's subject; it routed the comment here for the comment only)

| Field | Value |
|-------|-------|
| **ID** | QLT-013 |
| **Severity** | LOW — **re-derived, unchanged** |
| **Type** | `SPEC-DEVIATION` — confirmed (an in-code comment states a rule the two lines beneath it implement in the opposite sense) |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `tests/test_downloader_throttle.py` |
| **Classification** | advisory — confirmed |

**Description.** An inline comment states a precedence rule that the code implements in the opposite sense. A maintainer who acts on the comment changes correct code and breaks a passing test.

**Evidence (re-derived).** `services/downloader_throttle.py:306-338` (the function), `:334-336` (the comment and the `max()`), `:314` (the docstring, correct); `tests/test_downloader_throttle.py:598-610`; `services/segment_downloader.py:251-252`; `services/ytdlp_downloader.py:399`.

**Exact consequence.** A maintainer reading `:334` and trusting it replaces `max(delay, retry_after_seconds)` with `retry_after_seconds`, which makes a 429 wait **less** than its own backoff schedule whenever the server sends a small `Retry-After` — the opposite of the intent — and fails `test_retry_after_ignored_when_smaller`.

**Recommendation (accepted).** Change the comment at `downloader_throttle.py:334` to state the implemented rule — e.g. *"Treat Retry-After as a floor: wait at least that long, never less than the calculated delay"*. Do not change `max()` and do not change the tests; the floor behaviour is what `test_retry_after_ignored_when_smaller` pins and what the two callers rely on. One word, and it is the word the code already implements.

---

## Non-reproductions and cross-references

### `services/ffmpeg_utils.py:471-478` — the comment claiming a `FileNotFoundError` is not an `OSError` subclass: **NOT REPRODUCED. The source report is right and the phase-07 non-reproduction stands.**

This was routed to phase 09 as a known-wrong comment. I read the full docstring rather than the routed fragment, and checked both of its premises against the code.

> **Raises:**
> `FileNotFoundError`: If segment files are missing.
> `DownloadError`: If the volume lacks the free space the merge requires.
> &nbsp;&nbsp;&nbsp;&nbsp;A precondition failure like the missing-segment one above, not a merge failure — which is why it raises rather than returning None.
> &nbsp;&nbsp;&nbsp;&nbsp;It is deliberately not an ``OSError`` subclass: the yt-dlp resume path wraps this call in ``except (ExtractionError, OSError)`` (ytdlp_downloader.py), which would swallow a FileNotFoundError here, relabel it "failed_to_refresh_token" and return None, losing the message.

The antecedent of *"It"* is `DownloadError`, not `FileNotFoundError` — the immediately preceding clause is about `DownloadError` raising rather than returning `None`, and the sentence that follows is about that same class. Both premises verify:

- `issubclass(DownloadError, OSError)` → `False`. `DownloadError` (`exceptions.py:186`) extends `VKDownloadError` (`exceptions.py:16`) which extends `Exception`.
- `issubclass(FileNotFoundError, OSError)` → `True`.
- `ytdlp_downloader.py:547` is `except (ExtractionError, OSError) as e:`, which logs `failed_to_refresh_token` at `:549` and falls through to `return None` at `:561`.

So the handler **does** swallow a `FileNotFoundError` raised by this function, which is precisely the stated reason for preferring `DownloadError` — the comment is asserting the swallowing, not denying it. The phase-07 ground, which recorded the comment as claiming `FileNotFoundError` is not an `OSError` subclass, inverts the sentence. This independently matches the phase-06 validator's finding that SEC-001's ground misread the same comments. **No finding is filed, and no `QLT-` identifier is minted.** Had the auditor been wrong, a real finding would have been lost; it was checked, and the non-reproduction holds.

### `services/progress_display.py:62-63` — the unreachable `except ValueError` arm: **reported, not filed.** The sole writer of `task.fields["status"]` is `finish_task` (`progress_display.py:270`, `:277`), which passes `status.value`; the arm is a defensive coercion over a `dict[str, Any]` that `rich` owns, and the coercion is documented at `:58-59`. No severity condition covers an unreachable defensive branch, and manufacturing one would be a defect in the report.

### `services/downloader.py`'s repeated `__all__` entry: **cross-referenced, not re-filed.** `__all__` is 26 entries and 25 unique; `_format_argfile` appears twice. Inert at runtime — `__all__` is a list of strings and the repetition changes no import. Already filed as `ENT-006` by phase 01; the facade question is that phase's subject, not this one's.

### Pipeline defects this run verified and did **not** re-file

Each was executed against the pipeline's own documents per blocks (g) and (h), each reproduces, and each is **already carried** in the validation store. Re-filing would be a duplicate (§4(b), *same root cause*).

| Pipeline subject | Verified at | Already filed as |
|---|---|---|
| Launch gate keys on "not trivial" / "significant" — undefined, unevaluated, while `<output>` reports `Validated findings: {N} total` | `audit-multi-phase.md:86` vs `:118` | `02-config` `VAL-003` **and** `08-cli-observability` `VAL-001` — the same defect, two IDs |
| Report format has no slot for the per-finding decision | `.ai/audit/templates/audit-findings.md:19-27` | `02-config` `VAL-001`, `03-network-resilience` `VAL-006`, `08-cli-observability` `VAL-002` |
| Role files list three finding types; the format defines four (`RUNTIME-ERROR` omitted) | `.kilo/agents/auditor.md:256-259`, `.kilo/agents/validator.md:241-245,352-358` vs `templates/audit-findings.md:68` | `03-network-resilience` `VAL-004`, `08-cli-observability` `VAL-002` |
| Commands read `AGENTS.md` as mandatory base context; the repository root holds none | `audit-multi-phase.md:43`, `audit-refine.md:19`; `Test-Path AGENTS.md` → `False`; rules live in `.kilo/rules/project.md` and `.ai/context/` | `01-entry-architecture` `VAL-109`, `03-network-resilience` `VAL-005`, `08-cli-observability` `VAL-004` — **three** IDs |
| Orphaned-file census reaches the audit catalogue, the phase directory and the worktree copy | `audit-orphaned.md:30-34` (category list only) vs `.kilo/worktrees/southern-bandana/.ai/audit/` holding a full stale catalogue | `08-cli-observability` `VAL-005` |
| Validation stage's severity table has no row for a finding that passes verification, making "re-derive one" unexecutable | `99-audit-validate.md` §8 table | `06-credentials-secrets` `VAL-601` |

That table is the evidence for `VAL-901`: **five distinct pipeline defects, one subject each, filed eleven times under nine different identifiers across five files.** The two that check out — the write-path/check-path agreement (`audit-multi-phase.md:94` vs `:105`, identical strings) and the decision-preservation rule (no instruction anywhere strips rejected content) — are not written down, per binding rule 2.

---

## New findings (VAL-)

### VAL-901: The `VAL-` namespace is flat, so one identifier carries three mutually exclusive claims and one pipeline defect is filed eleven times

| Field | Value |
|-------|-------|
| **ID** | VAL-901 |
| **Severity** | **CRITICAL** — re-derived. `99-audit-validate.md` §8 reserves CRITICAL for "a cross-phase conflict, or a rollout-safety blocker", and §7 requires an identifier collision between two live prefixes to be "recorded in R0's identifier map and filed once here". The collision is not cosmetic: the same identifier names three different, mutually exclusive claims about the same machinery |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.ai/audit/99-validation/*.md` (8 files), `.kilo/commands/audit/phases/99-audit-validate.md` §10 |
| **Classification** | mandatory |

**Description.** The pipeline gives every finding phase its own prefix (`ENT`, `CFG`, `NET`, `SKIP`, `CON`, `SEC`, `OUT`, `QLT`) but gives **all eight validation phases one shared prefix on a flat namespace**. There is no phase component in a `VAL-` identifier, and no uniqueness check.

**Evidence.** 44 `VAL-` identifier occurrences across eight files; **33 distinct**. Thirteen are duplicated: `VAL-001` ×3, `VAL-002` ×3, `VAL-003` ×3, `VAL-004` ×3, `VAL-005` ×3, `VAL-006` ×2. `VAL-003` names three claims that cannot all hold:

| `VAL-003` in | Title |
|---|---|
| `02-config-validated-findings.md:1024` | "The condition that launches the validator cannot be evaluated, while the closing output reports validation coverage unconditionally" |
| `03-network-resilience-validated-findings.md:1420` | "The validation stage's write path and its check path name **different files**, so every run fails its own gate for an artifact that is on disk" |
| `08-cli-observability-validated-findings.md:1411` | "The pipeline pins a commit in the report header but records nothing about the tree it read, and the tree is not the pinned commit" |

The first says the launch gate cannot be evaluated. The second says the gate *is* evaluated and fails on a filename mismatch. Both cannot be true of the same stage at the same commit, and the evidence in `VAL-902` below settles which: the second does not reproduce at `HEAD`.

The collision also defeats the purpose `99-audit-validate.md` §10 states for the prefix — *"renumbering never invalidates a published finding ID"*. It cannot: the ID does not identify a finding. Five of the six pipeline subjects executed above are filed **eleven times under nine identifiers across five files** — the unevaluable launch gate twice, the absent decision slot three times, the role-vocabulary omission twice, the `AGENTS.md` read three times, and once each for the census and the severity table. A reader resolving "VAL-003" needs the filename; this very run was handed a base context that cited "VAL-003 in that artifact" and could resolve it only by file.

**Exact consequence.** Two phases' duplicate claims of one defect are invisible to cross-finding analysis, because each phase scans its own file. A fix tracker keyed on the identifier would resolve `VAL-003` to whichever artifact it opened first and silently drop the other two. The `VAL-` prefix does the opposite of what §10 claims for it.

**Recommendation.** Give each validation phase a distinct sub-namespace, exactly as the finding phases have theirs — `VAL-01-001`, `VAL-09-001` — and add the check to the rewrite command: before minting an identifier, confirm it is unused across the whole store, not only within the file being written. Re-key the eight existing artifacts in the same change; a partial re-key makes the store strictly harder to read than it is now. The eleven duplicate filings of the five pipeline subjects should then collapse to five, with the absorbing ID recorded in each artifact's `Validation Note`.

---

### VAL-902: Two cross-phase claims in the validation store assert a pipeline state that `a335b2a` fixed, and both remain standing

| Field | Value |
|-------|-------|
| **ID** | VAL-902 |
| **Severity** | MEDIUM — re-derived. Not CRITICAL: no phase's product finding depends on either claim. A finding whose *supporting* claim no longer reproduces is the LOW/MEDIUM band, not the conflict band — the conflict band is reserved for two phases asserting incompatible facts about one **product** subject, and these are about a command's text |
| **Type** | `SPEC-DEVIATION` |
| **Affected Modules** | `.ai/audit/99-validation/03-network-resilience-validated-findings.md` (`VAL-003`, `VAL-007`), `.kilo/commands/audit/audit-multi-phase.md`, `audit-refine.md` |
| **Classification** | mandatory |

**Description.** Two findings filed by phase 03 describe defects of the audit pipeline's own commands. Commit `d62671b` — *"fix(audit): align validation gate filename and stop destroying rejected findings"* — removed both. Neither artifact was updated, so the store now asserts a pipeline state that does not exist.

**Evidence.** At `HEAD` = `a335b2a`:

- **Path agreement now holds.** `audit-multi-phase.md:94` writes `.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md`; `audit-multi-phase.md:105` checks `.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md`. The strings are byte-identical, including the `{PHASE_NAME}` suffix, which is parsed from the filename stem after `NN-audit-` (`:62`). `03-network-resilience` `VAL-003` claims they "name different files" and that "every run fails its own gate for an artifact that is on disk". Both halves are now false. This run wrote to the path `:94` names and `:105` checks, and the gate is the correct one.
- **No instruction deletes a decision any more.** A search across all five audit commands and all twelve phase handbooks for `remove rejected` / `delete rejected` / `strip rejected` / `discard rejected` / `drop rejected` / `remove non-actionable` / `delete non-actionable` returns **no match**. `audit-refine.md:71-78` — the command that rewrites recommendations in place, and the one place such a rule would live — instructs only *"Modify the audit file directly"*, *"Preserve existing structure and formatting"*, *"Replace ambiguous recommendations with a single actionable recommendation"*. `03-network-resilience` `VAL-007`, which names an orchestrator instruction to "clean" rejected findings from the artifact, cites text that is no longer there.

**Exact consequence.** `VAL-003` is not merely stale — it is the third claimant of the `VAL-003` identifier whose other two claimants say the opposite thing, and its claim is the one the evidence rejects. A later run that re-derives the path mismatch will find a filed finding asserting it, and cannot tell from the store that the finding was superseded; a later run that trusts it will look for a gate failure that cannot occur.

**Recommendation.** In `03-network-resilience-validated-findings.md`, mark `VAL-003` and `VAL-007` as superseded by `d62671b`, recording the commit and the verification above, and leave the text in place — per `99-audit-validate.md` §11, a rejected claim's text is what stops the next run re-deriving it, and the same holds for a superseded one. Add a line to the validation-store rewrite command: a `VAL-` finding about a pipeline document is re-checked against that document's current text on every run, and a claim that no longer reproduces is annotated rather than deleted.

---

### VAL-903: `QLT-011`'s recommended module split breaks four test-side import and patch targets the finding does not enumerate, and `QLT-001` and `QLT-010` prescribe overlapping edits

| Field | Value |
|-------|-------|
| **ID** | VAL-903 |
| **Severity** | MEDIUM — re-derived. Rollout-safety: a recommendation that cannot be applied as written, and an ordering constraint between two accepted findings. Not CRITICAL — no fix is *blocked*; both are recoverable in the same change that carries the fix |
| **Type** | `BEST-PRACTICE` |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/downloader.py`, `tests/test_downloader_throttle.py`, `tests/test_hls_downloader.py`, `src/vkdownloader/exceptions.py` |
| **Classification** | mandatory |

**Description.** Two accepted findings prescribe changes that cannot be applied independently, and one of them understates its own blast radius by a factor of three. `QLT-011` is validated; its recommendation is not safe to execute as written.

**Evidence, part 1 — the split's unstated cost.** `QLT-011` describes its fix as *"a file move plus an import change in each of the two callers"*. The four functions plus `RETRYABLE_STATUS_CODES` are bound into **nine** places:

| # | Site | Kind | Breaks on the move? |
|---|---|---|---|
| 1 | `services/segment_downloader.py:23-28` | `from .downloader_throttle import (_compute_backoff_delay, _parse_retry_after, _retry_429_with_backoff, _wait_with_shutdown)` | yes — import edit |
| 2 | `services/ytdlp_downloader.py:24-25` | same, four names | yes — import edit |
| 3 | `services/downloader.py:33`, `__all__` at `:198` | `# noqa: F401 — backward-compat re-export` of `_retry_429_with_backoff` | yes — the public re-export path `vkdownloader.services.downloader._retry_429_with_backoff` must be preserved or the facade narrows |
| 4 | `tests/test_downloader_throttle.py:9-17` | one `from … import (` block naming 7 symbols | yes — `ImportError` |
| 5 | `tests/test_downloader_throttle.py:462` | `patch("vkdownloader.services.downloader_throttle._wait_with_shutdown", …)` | yes — `AttributeError` |
| 6 | `tests/test_hls_downloader.py:2344` | same string | yes — `AttributeError` |
| 7 | `tests/test_hls_downloader.py:2509` | same string | yes — `AttributeError` |
| 8 | `docs/STRUCT.md:31` | the row naming three of the four concerns | yes — the finding's own second edit |
| 9 | `QLT-013`'s `downloader_throttle.py:334` | the comment inside `_compute_backoff_delay` | ordering, below |

`patch()` raises `AttributeError` when its target does not exist, and `create=True` appears **zero** times in the test tree — so sites 5–7 fail hard rather than silently. Sites 5–7 are additionally worth a note for phase 10, not for this phase: `segment_downloader.py:23` is a from-import, so patching the *throttle* module's attribute does not reach the name `segment_downloader` calls. Those two patches are already inert today; the move converts two inert patches into two failures, which is a behaviour change in the suite even though no assertion changes.

**Evidence, part 2 — the ordering constraint.** `QLT-001`'s accepted recommendation edits `exceptions.py:141-149` (delete the two-outcome branch in `status_label()`) **or** keeps it and adds `ErrorCode.NO_STREAMS`. `QLT-010`'s accepted recommendation deletes the overrides at `exceptions.py:77`, `:106`, `:149`, `:183`, `:193` — `:149` is the second return of the same method `QLT-001` is editing. Applying `QLT-001`'s first option and `QLT-010`'s independently produces a half-deleted method; applying them in the other order deletes the branch `QLT-001` was going to reconcile. `QLT-013`'s comment fix is independent of both and of the module move, and can land at any time.

**Exact consequence.** Applying `QLT-011` as written turns a green suite red on four targets and drops a documented backward-compat export; applying `QLT-001` and `QLT-010` as two independent changes corrupts `exceptions.py:141-149` whichever order they land in.

**Recommendation.** Land `QLT-013` first — it is independent, one word, and it touches a line that `QLT-011` will move, so doing it before the move avoids a second edit. Then land `QLT-001` and `QLT-010` as **one** change to `exceptions.py`, choosing the single option that satisfies both: derive the label from `ErrorCode` in the base at `exceptions.py:52`, add `NO_STREAMS` to `ErrorCode`, and delete all six overrides. That resolves the `no_streams` / `quality_not_available` split, the `invalid_quality` divergence, and the five duplicated literals in one edit, and it is the only ordering in which all three findings are satisfied. Amend `tests/test_exceptions.py:123-158` in the same change. Then land `QLT-011` with all nine sites above, carrying `RETRYABLE_STATUS_CODES` into the new module and keeping the `services/downloader.py` re-export intact.

---

## Warnings

**Architectural.** The four documents describing this tree are all stale, in the same direction, and none of them is regenerated by anything: `docs/STRUCT.md` (QLT-003), `.ai/structure/py_map.yaml` and `map.md` (QLT-004), `docs/01-tools/vkdownloader-overview.md` (QLT-005), and the split CLI reference (QLT-006). A new maintainer's first map of the codebase is wrong in at least nine places across four documents, and the drift only widens. The common cause is that no document declares who updates it.

**Maintainability / evolvability.** The exception taxonomy carries three independent ladders for one condition — `error_code`, `status_label()` and the legacy `_map_exception_to_status` shim — and the shim is the one with **zero production callers** and 11 test callers, so the suite is the only thing keeping it alive. `QLT-001` and `QLT-010` both propose deleting it; nothing else proposes it, and while it survives it will drift again, which it has already done.

**Rollout.** See `VAL-903`. Additionally, `docs/STRUCT.md` omits `services/ytdlp_downloader.py` and the same document's `downloader_throttle.py` row names three of four concerns — a maintainer following the architecture document reaches the wrong module for 198 lines of live retry policy. `QLT-003` and `QLT-011` are one edit apart in that file and should land together.

**Dependency.** `yt_dlp` is the only installed dependency without a `py.typed` marker, is imported in exactly one file, and is reached through exactly one attribute site (`services/extractor.py:211`). With `ignore_missing_imports = true` (`pyproject.toml:104`), a renamed or misspelled `yt_dlp` attribute produces no diagnostic in `mypy src` and fails only at runtime. Confirmed: `--disallow-any-unimported src` reports nothing while this is true.

**Documentation consistency.** The project's own rules (`docs/00-overview/doc-maintenance-rules.md:18`) require each fact to live in exactly one file; `docs/99-reference/` holds two files with the same `id`, and `.ai/structure/` and `docs/` disagree about whether build artifacts belong in a structure map. The `D-01`/`AC2` citation scheme resolves and `INT-001`/`SRV-006`/`SRV-001` do not (QLT-007) — so the repository has at least two provenance schemes, one live and one half-dead.

**Pipeline-document defects verified in this run and recorded in `VAL-901` and `VAL-902`.** One further defect is verified and recorded here rather than filed, because it is in a command this run did not exercise and no artifact's provenance depends on it: `.kilo/commands/audit/audit-refine.md` is structurally malformed. `{REQUIRE_RESEARCH}` is referenced at `:41` and `:60` and never defined; the `<subagent_prompt>` block at `:58-69` is followed by a second, empty `<subagent_prompt>` block at `:80-81`; and `### 3.` at `:43` has no terminator before `<refine_loop>` closes at `:82`. A human-invoked refine pass would emit an empty subagent prompt. Its `AGENTS.md` read at `:19` is the already-filed half.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 8 | QLT-001, QLT-002, QLT-006, QLT-007, QLT-008, QLT-010, QLT-011, QLT-013 |
| Reclassified | 1 | QLT-012 (`SPEC-DEVIATION` → `BEST-PRACTICE`) |
| Merged | 0 | — |
| Rejected | 0 | — |
| VAL- (cross-phase / rollout) | 3 | VAL-901, VAL-902, VAL-903 |

**Tally reconciliation.** 8 + 1 + 0 + 0 = **13**, the findings in scope. One `Validation Note` per finding, thirteen in total, one per `###` heading. Three `VAL-` entries added. Nothing else was invented: no second `VAL-` identifier, no cross-phase conflict beyond the two in `VAL-901` and `VAL-902`, and no rollout finding beyond the one in `VAL-903`.

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | **Zero rejections.** No finding in the source report met a stated rejection ground. Nine reproduced in full, one reproduced with a material evidence correction (`QLT-009`), one reproduced with a type correction (`QLT-012`), and two were re-derived to a lower severity on this phase's own severity table. The grounds available — already implemented, stale, duplicate, low value at this scale, architecture-breaking, operationally unsafe, overly complex, against project direction — were each checked and none applied. Two candidate rejections were considered and **refused**: `QLT-012` was close to "low value at this scale" and was instead reclassified, because its measurement is exact and its `Type` was wrong rather than its substance; `QLT-011` was considered for "overengineering" and refused outright, because a straight file move of four functions to a new module introduces no new abstraction, and `99-audit-validate.md` §4(d) holds that modularization findings must not be rejected as overengineering unless the split adds indirection |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| — | — | **Zero merges.** The one candidate pair was examined and rejected as a merge. `QLT-001` and `QLT-010` share a root cause — status labels are hand-written rather than derived from `ErrorCode` — but they cover different subjects: `QLT-001` is one condition carrying two live identifiers, `QLT-010` is five overrides not deriving from the enumeration. `99-audit-validate.md` §4(b) classes that as *genuine complement*: both retained, cross-referenced, **not a merge**. The adjacency that does need recording is their edit collision inside `exceptions.py:141-149`, and that is an ordering constraint, filed in `VAL-903` |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| QLT-012 | `SPEC-DEVIATION` | `BEST-PRACTICE` | `99-audit-validate.md` §8 defines `SPEC-DEVIATION` as contradicting **the project's own declared rule**. I searched `.kilo/rules/project.md`, `.kilo/rules/commands.md`, `.ai/context/python-code-standards.md`, `.ai/context/commands.md`, `docs/00-overview/doc-maintenance-rules.md` and `docs/STRUCT.md`: no document declares a rule on import form, and both forms pass `mypy` and `ruff`. The finding is exact about the 15/3/7 split and right that the asymmetry trips a tree-wide search — that is a defensible arrangement with a demonstrated gap, which is `BEST-PRACTICE` |

### Severity Re-derivations

Every severity was re-derived from this run's own verification (binding rule 1). No severity changed because of the decision recorded against it; a decision never moves a severity.

| ID | Source | Re-derived | Row of `99-audit-validate.md` §8 the re-derivation used |
|----|--------|-----------|---------------------------------------------------|
| QLT-001 | HIGH | **HIGH** | no row — see note below. Retained: technical correctness and applicability both passed, and the consequence is a user-visible label that no declared filter can match |
| QLT-002 | HIGH | **HIGH** | no row. Retained: the declared `error_code` vocabulary is delivered on neither of the two commands' terminal handlers |
| QLT-003 | MEDIUM | **LOW** | "a `DOC-UPDATE` candidate" — advisory, no product behaviour affected, four one-line edits to one document |
| QLT-004 | MEDIUM | **LOW** | "a `DOC-UPDATE` candidate" — the drift widens on its own, but nothing is incorrect at runtime |
| QLT-005 | MEDIUM | **LOW** | "a `DOC-UPDATE` candidate" — and the consequence is self-announcing: the reader gets an `ImportError` |
| QLT-006 | MEDIUM | **MEDIUM** | no row. Retained above the DOC-UPDATE rung: the two errors are *not* self-announcing — a reader writes a configuration against a `file` cookie source that does not exist — and neither copy can be deleted alone, so the fix is a merge |
| QLT-007 | LOW | **LOW** | "any advisory finding with no security, data-loss or correctness consequence" |
| QLT-008 | LOW | **LOW** | same row |
| QLT-009 | MEDIUM | **LOW** | "any advisory finding with no security, data-loss or correctness consequence" — the surviving claim is a convention with no enforcement point and two real `Any` uses, not the 8-site remediation the report describes |
| QLT-010 | MEDIUM | **MEDIUM** | no row. Retained: a rename of an `ErrorCode` value silently breaks log filtering with nothing able to catch it, which is a correctness consequence on the observability path |
| QLT-011 | MEDIUM | **MEDIUM** | no row. Retained: 198 of 371 lines of live retry policy have no entry point in the module name or the architecture document |
| QLT-012 | LOW | **LOW** | "any advisory finding with no security, data-loss or correctness consequence" |
| QLT-013 | LOW | **LOW** | "a `DOC-UPDATE` candidate" and consequence-free: a maintainer who trusts the comment breaks a test, not a user |

**Note on the taxonomy gap, recorded because this run hit it on eight of thirteen findings.** `99-audit-validate.md` §8's table has four rows, and every one is keyed to the *validation act* — CRITICAL for a cross-phase conflict or a rollout blocker, HIGH for a finding whose verification failed, MEDIUM for a reclassification or a merge, LOW for a `DOC-UPDATE` candidate or a consequence-free advisory. It has **no row for a finding that passes verification, is not a `DOC-UPDATE`, and carries a correctness consequence** — which is the majority class of a code-quality phase's output, and which `QLT-001`, `QLT-002`, `QLT-006`, `QLT-010` and `QLT-011` all are. Binding rule 1 requires each such severity to be re-derived; the table gives nothing to re-derive from, so the only non-arbitrary options are to leave the source severity standing unre-examined or to invent a mapping. This run did the former and marked each such row "no row" above. **The gap is already filed** — `06-credentials-secrets-validated-findings.md` `VAL-601`, *"The severity table the validation stage must compose from has no row for a finding that passes verification, so the instruction to re-derive one is unexecutable"* — and is cross-referenced, not re-filed. The same run records two other encounters: `03-network-resilience` noted the owning phase's table lacks a row for `CON-007`/`CON-009`, and `04-concurrency-cancellation` composed two rungs for the same reason. **Three validation runs have now hit the same gap.** It is the single highest-value fix in the pipeline's own documents.
