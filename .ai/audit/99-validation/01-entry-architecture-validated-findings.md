---
name: 01-entry-architecture-validated-findings
description: Validation record for audit phase 01 — Entry Points & Module Architecture
agent: validator
alwaysApply: false
---

# Phase 01 Validation Record — Entry Points & Module Architecture

**Validator:** validator
**Handbook:** `.kilo/commands/audit/phases/99-audit-validate.md`
**Source report (read-only):** `.ai/audit/01-entry-architecture/findings.md` — 14 findings, `ENT-001`…`ENT-014`
**This artifact:** `.ai/audit/99-validation/01-entry-architecture-validated-findings.md`
**Findings in scope:** 14 · **Decided:** 14 (Validated 11, Reclassified 2, Merged 1, Rejected 0)
**Validation-added findings:** 12 (`VAL-101`…`VAL-112`)
**No code file was read-modified; no product file was written.**

**Deviation from the report format, stated once.** `.ai/audit/templates/audit-findings.md:19-33` runs the
finding block heading → fixed field table → Description/Evidence/Recommendation, and its nine mandatory
fields (`:64-74`) carry no decision. There is no slot for a per-finding validation decision. This record
places the `Validation Note` directly after each heading, and the absence of the slot is filed as
`VAL-111`. Severities in the tables below are re-derived from this run's own verification; none is
inherited from the source report, and none is changed by the decision recorded against it.

---

## Scope and inputs

| Input | State |
|---|---|
| Source findings file | present, 1008 lines, 14 findings, `Validated: no` |
| Phase handbook `01-audit-entry-architecture.md` | present |
| Sibling findings file `.ai/audit/02-config/findings.md` | present, 8 findings — read for cross-phase analysis only (R2), not validated |
| Report format `.ai/audit/templates/audit-findings.md` | present |
| Orchestrator `.kilo/commands/audit/audit-multi-phase.md` | present |
| Role files `.kilo/agents/auditor.md`, `.kilo/agents/validator.md` | present |
| `AGENTS.md` at repository root | **absent** — see `VAL-109` |

Repository-wide searches for this run excluded `.git`, `.kilo/worktrees`, `.venv`, `__pycache__`,
`.ruff_cache`, `.mypy_cache` and `node_modules`. One temporary copy of the package was made outside
the repository to run the import A/B experiment; no repository file was modified by it.

## Baseline re-verified this run

Every baseline the source report was observed against was re-run. All four reproduce exactly.

| Baseline | Command | Result this run | Source report |
|---|---|---|---|
| Static | `uv run ruff check src tests` | exit 0 — `All checks passed!` | matches |
| Static | `uv run ruff format --check src tests` | exit 0 — `52 files already formatted` | matches |
| Static | `uv run mypy src` | exit 0 — `Success: no issues found in 30 source files` | matches |
| Suite | `uv run pytest -q -rs` | exit 0 — `481 passed, 4 skipped in 24.30s` | matches |

The four skips are the D-11 Windows permission-mode skips at `tests/test_config.py:337`, `:353`,
`tests/test_hls_downloader.py:533`, `:678` — the exact lines and the exact reason the source report
names. The baseline against which every finding below was observed is therefore current; nothing in
this phase is stale on the ground that the code moved.

## R0 — Discovery maps

**Corpus map.** Handbooks in `.kilo/commands/audit/phases/`: `01-audit-entry-architecture` …
`11-audit-supply-chain` (11) plus `99-audit-validate`. Findings files present: `01-entry-architecture`
(14 findings) and `02-config` (8 findings). Both have handbooks. **No handbook without findings and no
findings without a handbook.** The validation store held no artifact for either phase at the start of
this run; the phase-02 store was written concurrently by a sibling validator and was present when this
run closed.

**Identifier map.** `ENT-` (phase 01, 14, sole owner). `CFG-` (phase 02, 8, sole owner). `VAL-` is
claimed by **both** validator runs and both minted numbers from the same starting point — recorded and
filed as `VAL-112`. The prior catalogue's identifiers (`01-audit-cli`, `02-audit-config`, …) are
deleted from the working tree and are not part of the current corpus.

**Decision-record map.** The format carries none of the four decisions. `validated`, `reclassified`,
`merged` and `rejected` have no slot between the finding heading and the field table. Absent slot for
all four, for all 14 findings. Filed as `VAL-111`.

**Pipeline-document map.** Documents the pipeline reads: `.kilo/commands/audit/audit-multi-phase.md`,
the 12 phase handbooks, `.ai/audit/templates/audit-findings.md`, `.kilo/agents/auditor.md`,
`.kilo/agents/validator.md`, `.ai/context/commands.md`, `AGENTS.md`. Documents it writes:
`.ai/audit/{NN}-{slug}/findings.md` and `.ai/audit/99-validation/{NN}-{slug}-validated-findings.md`.
`.kilo/commands/audit/audit-refine.md` is not opened by the orchestrator; it is a separate command
that edits the validation store in place. `AGENTS.md` is read by the orchestrator and held by nothing.

## Checkpoint 1 — R1 Copy Source Findings

- **Stage:** R1 Copy Source Findings
- **Findings in scope:** 14 (Validated 0, Reclassified 0, Merged 0, Rejected 0 at copy time)
- **Evidence anchor:** `.ai/audit/01-entry-architecture/findings.md`, 1008 lines, 14 finding blocks
  `ENT-001`…`ENT-014`, each carrying a 5-row field table plus Description / Evidence / Recommendation.
  The source file was opened read-only and is unmodified.
- **Dependencies / blockers:** none.
- **Checkpoint status:** closed

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 14
- **Cross-phase conflicts:** 0 — no two phases assert incompatible facts about one subject. The
  phase-01 and phase-02 reports agree on every subject they both touch.
- **Merge candidates:** 2 (both confirmed by re-derivation, see `VAL-101` and `VAL-102`)
- **Dependency chains:** 2 ordering constraints found against accepted phase-02 findings, 2 internal to
  phase 01, 1 shared-anchor constraint. Filed as `VAL-103`, `VAL-104`, `VAL-105`.
- **Evidence anchor:** `.ai/audit/02-config/findings.md` `CFG-001`, `CFG-002`, `CFG-006`; this run's
  re-derivation of `cli.py:123-131` and `cli.py:232-242`.
- **Dependencies / blockers:** none.
- **Checkpoint status:** closed

### Cross-phase comparison against the sibling report

| Subject | Phase 01 | Phase 02 | Verdict |
|---|---|---|---|
| Pre-sink emission of the unknown-variable warning | `ENT-001` HIGH, RUNTIME-ERROR | `CFG-006` MEDIUM, SPEC-DEVIATION | **one root cause** → merge, `VAL-101` |
| Second `Settings` built by `model_copy` in the service layer | `ENT-014` — *where* it is built | `CFG-002` — *what happens to the value* | genuine complement, both retained, cross-referenced |
| The `max_retries` override and the two shadowed settings | `ENT-014` — placement | `CFG-001` CRITICAL — reachability | ordering constraint, `VAL-103` |
| `setup_logging` raising `OSError` | `ENT-002`, `ENT-003` | not filed by phase 02 | no overlap |
| Exit codes, signal handlers, correlation identifiers | `ENT-004`, `ENT-008`, `ENT-011`, `ENT-012` | not filed by phase 02 | no overlap |

Phase 01's own boundary statement is correct in every instance: where it deferred a facet to phase
`02` (`max_retries` bounds) or phase `08` (exit-code meaning, terminal streams) or `09`
(`docs/STRUCT.md`), the sibling report holds the deferred facet and the two reports do not duplicate
it.

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 14 — **Validated 11, Reclassified 2, Merged 1, Rejected 0**
- **A decision tally, not a severity tally.**
- **Dependencies / blockers:** none.
- **Checkpoint status:** closed

---

## Findings

### ENT-001: Preamble records are emitted to structlog's default stdout sink, not the configured log sink

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** HIGH
> - **Type:** RUNTIME-ERROR (retained) · **Classification:** mandatory (retained)
> - **See also:** `VAL-101` (merge with `CFG-006`); `VAL-105` (shared preamble anchor with `ENT-002`,
>   `ENT-003`)

**Claim.** Both commands run `warn_unknown_env_vars()` and construct `Settings` before
`setup_logging(...)`, so every log record emitted on that path is rendered by structlog's library
default — `PrintLoggerFactory` to `sys.stdout`, plain `ConsoleRenderer` — instead of the sink the
operator configured. Two records are affected: the unknown-variable warning and the empty-`download_dir`
notice raised from a field validator inside `Settings.__init__`.

**Re-derived from source, not from the wording.** `src/vkdownloader/cli.py:125-128` and `:237-240`
run the four preamble steps in the order *warn → construct → configure sink → log env path*.
`src/vkdownloader/config.py:313-319` is the `logger.warning("unknown_env_var_ignored", …)`;
`src/vkdownloader/config.py:145` is `logger.debug("download_dir_empty_string_using_default")` inside
`Settings.normalize_download_dir`, which runs during `Settings.__init__`.
`config.setup_logging` is the only caller of `structlog.configure` (`config.py:368-382`) and installs
the `FileHandler` at `config.py:358-366`. Both citations are exact.

**Re-derived at runtime.** With `VKDOWNLOADER_LOG_LEVL=INFO` (misspelled), `VKDOWNLOADER_LOG_LEVEL=DEBUG`
and `VKDOWNLOADER_LOG_FILE=r1.log`, `uv run python -m vkdownloader download "not-a-url"` produced on
the terminal:

```
2026-09-29 11:45:48 [warning  ] unknown_env_var_ignored  … var=VKDOWNLOADER_LOG_LEVL
```

in structlog's pre-configuration `ConsoleRenderer` shape, while the configured JSON file contained
exactly one record, and it was a **post**-setup one:

```json
{"path": "C:\\py_exp\\mko_vkideo\\.env", "event": "env_file_resolved", "level": "debug", "timestamp": "…"}
```

The pre-sink warning is absent from the artifact the operator configured. The split reproduces.

**Severity, composed from this run.** Observed, not inferred: the record is lost from the configured
sink and rendered in a second format. HIGH. The `RUNTIME-ERROR` type is correct and is not one of the
three labels `auditor.md` lists — see `VAL-110`.

**Note on the merge.** `CFG-006` states the same cause. `ENT-001` is the absorbing identifier because it
names the same `config.py:313-319` emission *and* the second pre-sink record at `config.py:145` that
`CFG-006` did not identify, and it is typed `RUNTIME-ERROR` on an observed failure. `CFG-006` is
retained in full in the phase-02 store. See `VAL-101` for the absorbed ID and the one reconciliation
the two recommendations require.

---

### ENT-002: The single-download command's catch-all uses a log sink the failing preamble step was supposed to create

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** HIGH
> - **Type:** RUNTIME-ERROR (retained) · **Classification:** mandatory (retained)
> - **See also:** `VAL-105`

**Claim.** `setup_logging` can raise `OSError` while creating the log file's parent directory, before it
configures anything. The `download` command's catch-all then runs `logger.exception(…)` while structlog
is still on its library default, so the record and a full rich-rendered traceback go to **stdout** in
the default renderer while stderr receives only a generic one-liner.

**Re-derived from source.** `src/vkdownloader/cli.py:180-183` is the catch-all. `config.py:340-344`
raises `OSError` at `log_path.parent.mkdir(parents=True, exist_ok=True)`, and both `logging.basicConfig`
(`config.py:358`) and `structlog.configure` (`config.py:368`) are **below** it. One correction to the
source report's prose: it describes the raise as "five lines above" those calls; the raise block ends at
`config.py:344` and `basicConfig` begins at `:358`. The structural claim — the raise precedes every
configuration call — is correct; only the line arithmetic is off.

**Re-derived at runtime, on the declared platform.** With the log file's parent set to an existing
regular file, `download` produced:

```
2026-09-29 11:47:38 [error    ] download_failed                url=***REDACTED***
┌───────────────────── Traceback (most recent call last) ─────────────────────┐
│ C:\py_exp\mko_vkideo\src\vkdownloader\config.py:340 in setup_logging        │
│   340 │   │   │   log_path.parent.mkdir(parents=True, exist_ok=True)        │
…
│ │            settings = Settings( headless=False, user_agent='Mozilla/5.0 …  │
```

The intended `An error occurred during download` never reached stderr, and the configured log file was
never created. The same content raised `UnicodeEncodeError: 'charmap' codec can't encode characters`
on a `cp1251` stdout, which is the console-encoding facet the source report correctly assigns to
phase `08` and cites here only as evidence. The layer that emitted to the wrong sink is this phase's,
and it reproduces.

**Severity, composed from this run.** The command's own error handler fails on a configuration error,
on the declared platform, with a multi-frame traceback naming absolute source paths and the whole
`Settings` object. HIGH. `RUNTIME-ERROR` correct.

---

### ENT-003: The batch command's OSError handler reports a log-directory failure as a URL-file read failure

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM
> - **Type:** RUNTIME-ERROR (retained) · **Classification:** mandatory (retained)
> - **See also:** `VAL-105`

**Claim.** `download` declares no `except OSError`, so a preamble `OSError` falls into its catch-all.
`batch` declares `except OSError as e` around the whole body and prints a hard-coded
`"Failed to read URL file: …"` prefix. That handler also covers `setup_logging(settings)`, which runs
**before** `urls_file.read_text()` — so a log-directory failure is reported as a URL-file read failure
for a read that had not started.

**Re-derived from source.** `cli.py:139-183` — handlers are `ValidationError`, `QualityParseError`,
`InvalidVideoUrlError`, `KeyboardInterrupt`/`CancelledError`, `QualityNotAvailableError`,
`VideoNotFoundError`, `typer.Exit`, `Exception`. No `OSError`. `cli.py:281-283` is the batch handler
with the fixed prefix. The two `OSError` sources inside the batch `try` are `setup_logging(settings)`
at `cli.py:240` and `urls_file.read_text()` at `cli.py:245`. One citation correction: the declared
bound is `le=10` at `config.py:58`, not `:59`.

**Re-derived at runtime, same forced failure as ENT-002, second command.**

```
batch exit_code=1
  | Failed to read URL file: urls.txt — Failed to create log file parent directory
    '…\blocked.txt': [WinError 183] Cannot create a file when that file already exists
configured log dir exists? True
app.log created? False
```

The prefix names a failure that had not occurred, and the configured log file was never created. The
divergence from `download` is real and specific to `OSError`: the same forced bound violation
(`ValidationError`) is handled correctly and identically by both commands. The consequence the finding
states — an operator who rewrites or deletes their URL file in response — follows directly from the
message.

**Severity, composed from this run.** One command, one error class, real cause preserved in `{e}`.
MEDIUM. `RUNTIME-ERROR` correct.

---

### ENT-004: Interrupt-handler registration lives in the command layer for one command and in a service module for the other

> **Validation Note:**
> - **Action:** reclassified
> - **Severity (re-derived):** MEDIUM
> - **Type:** `SPEC-DEVIATION` → `BEST-PRACTICE`
> - **Classification:** advisory (retained)
> - **See also:** `VAL-105`; the signal-handler mechanism itself is phase `04`'s

**Claim.** The two commands run identical four-step preambles and then diverge on who owns interrupt
handling: `download` registers in the entry layer (`cli.py:100`, deregisters `:112`), `batch` registers
in a service module (`services/batch_downloader.py:322`, deregisters `:401`).

**Re-derived from source.** `cli.py:100` `setup_signal_handlers()` immediately precedes `try:` at
`cli.py:101`; `batch_downloader.py:322` `setup_signal_handlers()` precedes the bind at `:323-324` and
the `try:` at `:325`, with `cleanup_signal_handlers()` in the `finally` at `:401`. Both modules import
the same helper — `cli.py:34`, `batch_downloader.py:32` — and call it from different layers. The
divergence is exactly as filed.

**Re-derived at runtime.** On this Windows platform, `loop.add_signal_handler` raises
`NotImplementedError` for **both** handled signals:

```
add_signal_handler(2)  -> NotImplementedError
add_signal_handler(15) -> NotImplementedError
```

so the `signal.signal` fallback at `signal_handlers.py:45-49` is what runs. The source report's R8
"documented skip with justification" is therefore sound: the layer-placement difference is not masked
by platform behaviour. This run also confirms the finding's own discipline — the fallback mechanism,
the shutdown `Event` and the context-copy workaround are left to phase `04`.

**Why the Type changes.** `SPEC-DEVIATION` requires that the finding contradict a rule the project
declares. `docs/STRUCT.md:48` declares the entry layer to own "argument parsing, Settings construction,
error presentation, exit codes" — process-wide signal registration is not among them, and no
declaration anywhere requires it to live in the entry layer. The rule the finding cites is the
*phase's own* rule ("both commands do it at the same point in their bootstrap"), which is a phase
rule, not a project rule. What remains is a defensible arrangement with a demonstrated gap in
consistency: `BEST-PRACTICE`. Severity MEDIUM follows the reclassification band.

**Unverifiable detail, recorded as the source report records it.** The window between
`setup_signal_handlers()` and the `try:` that deregisters is real, and `download` has the same shape
(`cli.py:100` before `cli.py:101`). No step in that window was observed to fail. It stays UNVERIFIED.
The source report lists `services/signal_handlers.py` under `Affected Modules` while correctly not
faulting it; the module is not a subject of this finding.

---

### ENT-005: Eager package roots republish submodules' contents that nothing imports, and they are what makes two cross-layer cycles load-bearing

> **Validation Note:**
> - **Action:** validated — **absorbs `ENT-007`** (merge decision filed as `VAL-102`)
> - **Severity (re-derived):** MEDIUM
> - **Type:** `SPEC-DEVIATION` → `BEST-PRACTICE`
> - **Classification:** advisory (retained)
> - **See also:** `ENT-007`; `VAL-102`; `ENT-009` depends on this finding; `VAL-105`

**Claim.** All four package roots eagerly re-export names their submodules own. Nothing imports any
published name through a root. The re-export is also what creates two import cycles the code must
defer around, and the price of that coupling is paid by modules with no logical stake in it.

**Re-derived from source.**

| root | published names | own lines |
|---|---|---|
| `services/__init__.py` | `HLSDownloader`, `QualitySelector` | `:3-6` |
| `utils/__init__.py` | 5 names, two of them private to siblings | `:3-12` |
| `models/__init__.py` | 10 names | `:3-18` |
| `infrastructure/__init__.py` | `BrowserManager`, `JsonValue`, `NetworkMonitor` | `:3-10` |

All four citations are exact. The two deferrals and their own comments are exactly as quoted:
`exceptions.py:97-100` — *"Imported lazily to avoid a circular import: `vkdownloader.utils` package
`__init__` imports `security.py`, which imports `DownloadError` from this module at module load time"* —
and `infrastructure/browser.py:68-70` — *"Lazy import to avoid circular dependency: browser.py →
services.`__init__` → downloader → extractor → browser"*. The edge the first names closes is
`utils/security.py:8` `from ..exceptions import DownloadError` — exact.

**Re-derived by consumer scan, production vs test, worktrees excluded.** Zero imports of any published
name through any of the four roots, in production **or** test. Every site addresses the owning
submodule: `cli.py:35`, `services/downloader.py:28-29`, `services/segment_downloader.py:20-21`,
`services/extractor.py:15-16,20`, `services/downloader_throttle.py:14`,
`services/batch_downloader.py:34`, `services/ytdlp_downloader.py:30,32-33`,
`infrastructure/network_monitor.py:9`; tests `test_url_sanitizer.py:3`, `test_security.py:11`,
`test_browser_infrastructure.py:10-11`. The only consumers of the `services` root are five test sites
and all of them import **submodules** (`test_cli.py:21`, `test_ffmpeg_utils.py:155`,
`test_hls_downloader.py:2645,2671,3202`). The source report says four; the fifth
(`import vkdownloader.services.ffmpeg_utils as fu`, `test_hls_downloader.py:3202`) also executes the
root eagerly. The claim is unaffected.

**Re-derived by controlled A/B experiment.** A copy of the package was taken outside the repository.
Arm A: the four roots emptied to a docstring, and the three function-scope imports hoisted to module
scope. Arm B: identical, with the four eager roots restored.

```
ARM A (roots empty, deferrals hoisted)      ARM B (roots eager, deferrals hoisted)
OK   vkdownloader.exceptions                 FAIL vkdownloader.exceptions
OK   vkdownloader.infrastructure.browser     FAIL vkdownloader.infrastructure.browser
OK   vkdownloader.services.downloader        FAIL vkdownloader.cli
OK   vkdownloader.utils.correlation
OK   vkdownloader.cli
OK   vkdownloader.services.batch_downloader
OK   vkdownloader.models
OK   vkdownloader.utils
```

Arm B's failure, verbatim:

```
ImportError: cannot import name 'DownloadError' from partially initialized module
'vkdownloader.exceptions' (most likely due to a circular import)
```

The eager roots are **proven** load-bearing for `exceptions.py:100`, and emptying them is sufficient
to make all three deferrals ordinary module-scope imports. The finding's causal claim — that the roots
manufacture the cycles rather than the cycles being inherent — reproduces exactly.

**Why the Type changes.** No project rule or `docs/STRUCT.md` line declares that package roots must be
empty or must not re-export. `STRUCT.md:20,21,26,38` lists the four `__init__.py` files without
constraining their contents. Eager re-export is a standard Python arrangement, and here it is used
deliberately. What the finding demonstrates is a gap with a cost that is paid elsewhere, which is
`BEST-PRACTICE`. Severity MEDIUM follows the reclassification band.

---

### ENT-006: The service-layer compatibility facade publishes 26 names — 12 private, one twice, and a registration helper without its cleanup counterpart

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM
> - **Type:** `SPEC-DEVIATION` → `BEST-PRACTICE`
> - **Classification:** advisory (retained)
> - **See also:** `ENT-005` (the same defect class in the package roots); `VAL-102`
> - **Corrections to the finding's evidence counts** — see the two rows below

**Claim.** `services/downloader.py:175-202` is a documented compatibility facade with three defects: a
duplicated export-list entry, a large number of underscore-private names published as if public, and
a registration helper published without its own cleanup counterpart. Fifteen of its entries have no
production consumer, and the tests that "validate" it are the tests that would be rewritten with it.

**Re-derived from source — the facade is exactly as described.**

- 26 entries, 25 unique. `_format_argfile` appears at `:195` **and** `:200`. Confirmed.
- `setup_signal_handlers` is published at `:201` and imported at `:56` for that purpose; its own module
  publishes **both** names together at `services/signal_handlers.py:18`
  (`__all__ = ["setup_signal_handlers", "cleanup_signal_handlers"]`); `cleanup_signal_handlers` is
  absent from the facade. Confirmed.
- The comment block at `:144-174` names every symbol's real owner. Confirmed, and it is what makes the
  migration the finding recommends mechanical.

**Re-derived by AST consumer scan, production vs test, over every `ImportFrom` resolving to the facade.**

| name | prod | test | | name | prod | test |
|---|---|---|---|---|---|---|
| `FfmpegProgress` | 0 | 3 | | `_cleanup_segments` | 0 | 1 |
| `HLSDownloader` | 0 | 3 | | `_cookies_to_netscape` | 0 | 2 |
| `ProgressParser` | 0 | 5 | | `_download_segment` | 0 | 0 |
| `cancel_subprocess` | 0 | 0 | | `_download_segment_parallel` | 0 | 0 |
| `check_ffmpeg_available` | 0 | 0 | | `_download_segment_sequential` | 0 | 0 |
| `download_hls_with_resume` | 0 | 7 | | `_fetch_playlist_with_retry` | 0 | 0 |
| `download_with_ytdlp_with_resume_fallback` | 0 | 2 | | `_format_argfile` | 0 | 1 |
| **`download_video`** | **2** | 3 | | `_merge_segments_batched` | 0 | 0 |
| **`perform_download`** | **1** | 6 | | `_parse_m3u8_segments` | 0 | 1 |
| `read_progress` | 0 | 5 | | `_retry_429_with_backoff` | 0 | 0 |
| `_await_first_and_cancel_others` | 0 | 0 | | `_temp_argfile` | 0 | 1 |
| `_build_ffmpeg_concat_command` | 0 | 0 | | `setup_signal_handlers` | 0 | 0 |
| `_build_ytdlp_cli_command` | 0 | 1 | | | | |

**Two counts in the source report are wrong and are corrected here.**

1. The title and the body say **12** private names. The `__all__` block holds **14** underscore-prefixed
   entries (15 entries counting the duplicate), and the finding's own enumerated list contains 14. The
   number 12 is a miscount; the substance — private implementation detail published under `__all__` —
   is unaffected and if anything understated.
2. The body says *"15 of 26 entries have zero production consumers"*, which is inconsistent with its own
   table (six names listed as having production consumers implies 20). The measured figure is
   **23 of 25 unique entries (24 of 26 listed entries) have zero production consumers**; only
   `download_video` (2 sites — `cli.py:31`, `batch_downloader.py:29`) and `perform_download` (1) are
   reached from production code through the facade. The direction of the finding is strengthened, not
   weakened.

**Why the Type changes.** As with `ENT-005`, no declared project rule forbids a compatibility facade,
and `downloader.py:144-150` documents the facade as an intentional, deliberately maintained public
surface. What is demonstrated is a gap inside a defensible arrangement — private symbols exposed as
stable names, a duplicate entry, an unpaired lifecycle helper, and a surface kept alive only by the
tests that would be rewritten alongside it. `BEST-PRACTICE`, MEDIUM.

**Not rejected.** The finding was tested against every rejection ground. It is not already implemented
(the surface is live), not stale (re-measured this run), not a duplicate (`ENT-005` is the *package*
roots, this is a *module* facade), not low value (a second unofficial public API over 14 private
symbols), not architecture-breaking, not unsafe, not overengineered to fix, and not against project
direction — the project rule "avoid overengineering" cuts the other way here.

---

### ENT-007: The utility package root publishes two private symbols belonging to sibling modules

> **Validation Note:**
> - **Action:** merged → `ENT-005` (phase 01)
> - **Severity (re-derived):** MEDIUM
> - **Type (as filed):** `SPEC-DEVIATION` · **Classification (as filed):** advisory
> - **See also:** `ENT-005`; `VAL-102`; the documentation claim is phase `09`'s and is cross-referenced,
>   not re-filed

**Original content, retained in full.** `utils/__init__.py:3-4` imports and `:9,11` publish
`_resolve_output_file` (declared private at `utils/security.py:82`) and `_strip_auth_params` (declared
private at `utils/url_sanitizer.py:11`) — names their own declaring modules treat as private.
`docs/STRUCT.md:39` documents the export list, and the source report itself concedes the code and the
structural description agree, so the contradiction it alleges is internal to that agreement. The
`__all__` block holds five names, `['validate_output_path', 'sanitize_title', '_resolve_output_file',
'sanitize_url_for_log', '_strip_auth_params']`, and **zero consumers of any kind, production or test**.
The finding also notes that `_strip_auth_params` already has a public alias, `sanitize_url_for_log`
(`utils/url_sanitizer.py:50-63`), and that the duplication of *names* is not itself the defect.

**Why it is merged rather than kept.** One root cause, once named: an eager package root that
republishes sibling names nothing imports, and that is load-bearing for a cross-layer cycle. That is
`ENT-005`, whose own root table already carries the `utils/__init__.py` row verbatim — "5 names, two of
them private to siblings" — and whose recommendation already proposes deleting this exact block. Two
identifiers, one cause, one fix; keeping both would file the same four-line deletion twice.

**What the merge preserves that `ENT-005` does not say.** The `docs/STRUCT.md:39` claim, which
documents an export list that will be wrong the moment the block is deleted. The source report routes
this to phase `09` rather than re-filing it, which is the correct boundary under the pipeline's own
R-E rule; the cross-reference is retained here so it is not lost with the merge.

**Severity, composed from this run.** A merged finding is MEDIUM. Its `SPEC-DEVIATION` type does not
survive independently either — `docs/STRUCT.md:48` constrains the **entry layer**, and `:49` explicitly
permits the service layer to "import private symbols from `utils/` internally", which is exactly what a
utils-layer root does. There is no declared rule violated; the type would have been `BEST-PRACTICE`
had the finding not merged.

---

### ENT-008: The batch service module imports the presentation framework, formats all user-facing batch text, and returns the process exit status

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **See also:** `VAL-105`

**Claim.** Three entry-layer responsibilities sit in `services/batch_downloader.py`: it imports Typer
at module scope, it formats every user-facing batch line, and it decides the process exit status,
which `cli.py:276` raises verbatim.

**Re-derived from source.** `import typer` at `batch_downloader.py:18`. `typer.echo` appears **exactly
eleven times**, at lines `432, 441, 442, 444, 445, 446, 447, 449, 459, 461, 467` — per-result lines
(`:432`), the summary block (`:441-449`), the failed-URL list (`:459-461`) and the interrupted notice
(`:467`). `_print_batch_summary` (`:405-474`) is the whole user-visible contract. It returns `130` at
`:471` and `1 if failed > 0 else 0` at `:474`; `run_batch` returns that at `:509`; `cli.py:276` is
`raise typer.Exit(code=exit_code)`. Every count and every line the source report cites is exact. The
only imprecision is that it cites the echo groups as ranges where the last member of a range falls on
the following line; no cited line is wrong.

**Why the Type is retained.** Unlike `ENT-004`, `ENT-005` and `ENT-006`, this one contradicts a
declaration the project actually makes, twice over. `docs/STRUCT.md:48` assigns "error presentation,
exit codes" to the entry layer. And the module's own docstring at `batch_downloader.py:3-5` still
claims the extraction kept the entry layer as "argument parsing -> service call -> **result
presentation**" — after the extraction, the *service* performs the result presentation and computes the
code, and the command's remaining contribution to the output is `cli.py:265-276`. A docstring that
describes the opposite of what the module does is a declared claim the code contradicts.
`SPEC-DEVIATION` is correct.

**Scope boundary held.** The exit-code *meaning* — which code means what, and what the user sees for
each — is phase `08`'s. This finding files only which layer decides it, and says so.

---

### ENT-009: The correlation helpers are imported inside the hot download function with no cycle behind them and no stated reason

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** LOW
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **See also:** `ENT-005` (the cycle that *is* real); `ENT-011`, `ENT-012` (the callers)

**Claim.** `services/downloader.py:657-661` imports the correlation helpers from inside
`download_video` with no reason stated, and the import graph shows the target has no module-level
`vkdownloader` imports of its own, so nothing it pulls in can come back.

**Re-derived from source.** The deferred import is at `:657-661`, inside `download_video`. The target
`utils/correlation.py:10-12` imports only `uuid` and `structlog.contextvars` — re-read this run, and
`url_sanitizer.py` is the same shape (`re` and `urllib.parse` only). No cycle.

**Re-derived by experiment.** The controlled A/B in `ENT-005` isolates this case. In arm B, where the
deferral is hoisted and the eager roots are **restored**, the only failure is the `exceptions` cycle;
`services.downloader` and `utils.correlation` import cleanly on their own, and arm A confirms the
hoist is safe with the roots emptied. This is the only one of the three function-scope imports in the
project with no import-time failure behind it, exactly as filed.

**Wording correction.** The source report says *"There is no comment naming a reason"*. There **is** a
comment at `downloader.py:655-656` — `# DF-002: Bind a correlation ID so log entries in both
single-download and batch-download paths include a correlation_id field.` It states **what** the code
does, not **why the import is deferred**. The finding's distinction survives intact, and its
recommendation is the right one for exactly that reason: the two justified deferrals carry a reason and
this one carries a purpose statement, which is what makes the three indistinguishable to a reader.

**Severity, composed from this run.** LOW. No behavioural defect — the helpers are in `sys.modules`
after the first call, and the cost is one dict lookup per download. The cost is diagnostic, as the
finding states.

---

### ENT-010: A module-scope constant is derived by reflecting over the settings schema at import, and nine sibling call sites hardcode the same value

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **See also:** none

**Claim.** `services/downloader_throttle.py:18-19` claims a single source of truth for the download
timeout while freezing the value by reflecting over the settings schema at import time; the same value
is then reproduced by a literal in nine parameter and field defaults, and the two mechanisms can never
re-converge.

**Re-derived from source — all nine locations exact.**

| location | second derivation |
|---|---|
| `services/segment_downloader.py:66` | `DownloadPolicy.download_timeout: int = 300` |
| `services/segment_downloader.py:146, 217, 282, 314, 370` | `download_timeout: int = 300` (5 functions) |
| `services/ffmpeg_utils.py:273, 323, 452` | `download_timeout: float = 300.0` (3 functions) |

1 + 5 + 3 = 9. The reflected constant is declared at `downloader_throttle.py:19` and consumed at `:180`
as `_retry_429_with_backoff`'s default. The declared schema value is `config.py:62`
(`download_timeout: int = Field(default=300, …)`).

**Re-derived at runtime.**

```
_DEFAULT_DOWNLOAD_TIMEOUT = 300 int
DownloadPolicy.download_timeout default       = 300
ffmpeg_utils._merge_segments_batched  default = 300.0
ffmpeg_utils._perform_final_merge     default = 300.0
segment_downloader._download_segment         default = 300
downloader_throttle._retry_429_with_backoff  default = 300
```

The framing survives a challenge this run put to it. The three `ffmpeg_utils` defaults govern the
**ffmpeg subprocess** timeout, a different quantity from the HTTP request timeout that only shares its
name — but `segment_downloader.py:849` passes `settings.download_timeout` into that merge path on the
production route, so the same declared value really does reach all nine defaults. "Same declared
value" is correct, not merely "same name".

**Latency, confirmed as the finding states.** Every call site that matters passes the value explicitly
— `segment_downloader.py:496-497`, `:700`, `:833`, `:849` all read `settings.download_timeout` — so an
operator's `VKDOWNLOADER_DOWNLOAD_TIMEOUT` **is** honoured today. The finding marks its consequence
**UNVERIFIED as a live runtime defect** and does not claim otherwise; that marker is correct and is
retained. MEDIUM is composed for the latent break: nine defaults that can silently disagree with a
value the code declares to be owned elsewhere, against a mechanism frozen at first import.

---

### ENT-011: `clear_correlation_id()` removes every bound context variable, not the one it names

> **Validation Note:**
> - **Action:** reclassified
> - **Severity (re-derived):** MEDIUM
> - **Type:** `SPEC-DEVIATION` -> `BEST-PRACTICE`
> - **Classification:** `mandatory` -> **`advisory`**
> - **See also:** `ENT-012` — **the two are a chain; neither resolves alone** (`VAL-104`)

**Claim.** `utils/correlation.py:38-44` is named `clear_correlation_id` and its body is
`structlog.contextvars.clear_contextvars()`, which takes no key and empties the whole structlog
context. Any other key a caller bound in the same context is destroyed by a function whose name
promises to remove one key.

**Re-derived from source and at runtime.** The function is exactly as quoted. The docstring's first
line — "Clear all context variables from the structlog context" — documents what the code does; the
name and the rest of the docstring document what it promises. Using only the public helpers:

```
generated id len/type: 8 str
after bind                 -> 258db78a {'correlation_id': '258db78a'}
after binding 2 others     -> 258db78a ['correlation_id', 'request_id', 'unrelated_key']
after clear_correlation_id -> None      {}
unrelated_key survived?     False
```

The name/behaviour mismatch is fully confirmed, and the call sites are as filed:
`services/downloader.py:705-708`, `services/batch_downloader.py:295-296` and `:399-402` — three calls
per batch item.

**Consequence corrected — narrower than the source report states.** The finding asserts that *"a
caller that binds its own context keys before handing work to the downloader loses them at the end of
the download, with no error and no log line."* That does not reproduce in either entry path, because
`asyncio.Task` copies the context, so a clear inside the download cannot reach keys bound outside it.
Measured:

```
before asyncio.run  -> run-level-id ['caller_key', 'correlation_id']
  inside task, after clear -> None []
after  task returns -> run-level-id ['caller_key', 'correlation_id']
caller_key survived the task? True
```

`cli.py:131` and `batch_downloader.py:344` both enter the work through a task boundary, so a caller's
outer keys survive today. The residual defect is real but confined: any key bound **inside** the same
async context is still wiped, and the function's name still misleads the next caller who reads the
name rather than the body.

**Why Type and Classification both change.** No declared functional rule is violated — the docstring is
honest about the behaviour, and the defect is a name that does not match it, which is project rule 8,
"Meaningful & Consistent Naming". That is `BEST-PRACTICE`. And the template's classification guide
reserves `mandatory` for security, data loss, correctness and spec deviations requiring immediate fix;
a naming inaccuracy whose stated blast radius does not reproduce is none of those, so `advisory`.
MEDIUM follows the reclassification band, with the consequence narrowing above as the material fact for
whoever implements it.

---

### ENT-012: The nested download operation regenerates the correlation identifier and then clears the enclosing one

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** HIGH
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **See also:** `ENT-011` — **the two are a chain; neither resolves alone** (`VAL-104`)

**Claim.** The batch path binds a correlation identifier at two nesting levels and the inner bind
overwrites the outer one instead of inheriting it; the inner `finally` then clears the whole structlog
context, taking the enclosing identifier with it. The code already works around this by passing the
identifier as an explicit log field.

**Re-derived from source.** All six anchors are exact: item bind `batch_downloader.py:197-198`, item
clear `:295-296`; run bind `:323-324`, run clear `:399-402`; `download_video` bind
`services/downloader.py:663-664`, clear `:705-708`. `download_video` is awaited **directly** from
`_download_single` at `batch_downloader.py:234` — no `asyncio.create_task` between the two binds, so
they share one context. The two explicit-field workarounds are real and are at
`batch_downloader.py:274` and `:291`, with the run identifier passed as `batch_correlation_id` at
`:334` rather than relied on as a bound value.

**Re-derived at runtime, reproducing the exact bind/clear shape.**

```
outer bound (batch:198)      bound=b30ec8fe local=b30ec8fe
inner bound (downloader:664) bound=4ce9d908 local=4ce9d908
after inner finally (708)    bound=None      outer-local=b30ec8fe
```

Nested three deep, a single clear at the innermost level:

```
enclosing ids: ['64306583', '0e9cbb15', '8f66abfa'] -> bound now: 8f66abfa
innermost clear -> bound: None (all three removed)
```

**One evidence cell corrected.** The source report's harness table shows the `bind inner` row with
`bound-in-context='dadf2546'` — the *outer* value — which contradicts its own conclusion on the same
page. The measured value after the inner bind is the inner one. The conclusion is right and the cell
is wrong; nothing in the finding depends on the cell.

**Why the Type is retained and the severity is HIGH.** `utils/correlation.py:5-7` declares the
purpose: the helper exists so log output can be filtered and grouped "across the extract -> select ->
download pipeline, **including in concurrent batch mode**". On the batch path the code does the
opposite — every record inside the download carries an inner identifier that appears nowhere else, so a
log cannot be joined to the item's own summary line, and every record after `download_video` returns
carries no identifier at all, confirmed above as `bound=None`. A declared intent the code contradicts on
the path the feature was added for is `SPEC-DEVIATION` at HIGH.

---

### ENT-013: Heavy integration libraries are loaded at module scope on every command path, including `--help`

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **See also:** `ENT-005` (the same import graph, a different lever); `ENT-009`

**Claim.** `cli.py:30-33` imports the service layer at module scope, which reaches `yt_dlp`,
`playwright`, `rich` and `aiohttp` unconditionally, so `--help`, `--version` and every argument error
pay for the full integration stack before Typer parses anything.

**Re-derived from source.** `cli.py:30-33` imports `run_batch`, `download_video`, `get_shutdown_event`
and `is_valid_video_url` from the service layer at module scope. Those reach
`services/extractor.py:7` (`import yt_dlp`) and `:8-10` (the three `playwright.async_api` imports),
`services/progress_display.py:16-28` (`rich.console`, `rich.progress` columns, `rich.text`),
`services/downloader_throttle.py:9` (`import aiohttp`) and `services/segment_downloader.py:16`
likewise. Every line the source report cites is exact.

**Re-derived at runtime.**

```
$ uv run python -X importtime -c "import vkdownloader.cli"
import time:       1009 |        1539 |           rich
import time:       3139 |      134413 |           yt_dlp
import time:        704 |         704 |             playwright
import time:       1293 |      163314 |           aiohttp
import time:       1759 |      890452 | vkdownloader.cli      <- 890 ms cumulative

$ uv run python -c "import vkdownloader.cli, sys; ..."
cli import ms: 727
total modules: 727
heavy loaded: True
```

The source report measured 856 ms and 739 modules; this run measures 890 ms and 727 modules. Same
order of magnitude, same shape, same four libraries confirmed loaded. The measured cost is reproduced.

**Severity, composed from this run.** MEDIUM, on the finding's own terms — a per-invocation cost paid
on every command path, including the cheapest. The finding states plainly that nothing is functionally
wrong today and that the change is "recommended, but not urgent", and that framing is honest and
retained. Its alternative recommendation — if the cost is judged acceptable, say so in
`docs/STRUCT.md:48` so the next reader does not have to measure it — is the cheaper half and is worth
more than the refactor at this project scale.

**Dependency, stated rather than assumed.** The recommendation rests on `ENT-009`'s result that a
function-scope import of an integration-free module imports cleanly. That result is re-derived above
and holds. Applying `ENT-009` and `ENT-013` in either order is safe; neither depends on the other
landing first.

---

### ENT-014: The configuration object is rebuilt inside the service layer, outside the configured preamble

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **See also:** `CFG-002` (complement, not duplicate); **`VAL-103` — two ordering constraints against
>   `CFG-001` and `CFG-002` that this finding does not state**

**Claim.** Each command builds `Settings` exactly once in its preamble and hands that object to its
service. The service then builds a second configuration object before doing any work, by
`model_copy(update=…)`, which does not re-validate. The object `setup_logging` configured is therefore
not the object the download runs on, and the command has no visibility of the copy.

**Re-derived from source.** `cli.py:127` and `cli.py:239` each build `Settings` once; both call sites
are `Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)`. `services/downloader.py:652-653` is
the second construction, exactly as quoted, and it is reached from both paths because
`cli.py:102-110` and `cli.py:265-275` both funnel into `download_video` at `services/downloader.py:601`.

**Re-derived at runtime.**

```
preamble object max_retries = 3
service  object max_retries = 99  (declared bounds ge=1 le=10)
same object? False
re-validated? Settings -> out-of-range value accepted by model_copy
```

**Why the Type and Severity are retained.** The claim is a placement and object-identity fact, and the
placement is a defensible arrangement with a demonstrated gap — `BEST-PRACTICE`. The consequence is
real but currently latent in the same way `ENT-010`'s is, and the finding marks the value-validity
facet as phase `02`/`08`'s and does not claim it. MEDIUM.

**Two constraints this finding does not state, and that bind whatever is done to it.** Filed as
`VAL-103`. In short: its recommended shape is the very mechanism `CFG-001` classifies CRITICAL, on the
same two lines; and `CFG-002`'s fix and this one are mutually exclusive rather than sequential. A
fixer reading this finding alone will produce a third shadowed setting.

---

## Cross-phase and rollout findings

These are defects in the audit inputs, not in the product. `VAL-` is used only for them.

### VAL-101: `ENT-001` and `CFG-006` are one defect stated twice

| Field | Value |
|-------|-------|
| **ID** | VAL-101 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.ai/audit/01-entry-architecture/findings.md` `ENT-001`; `.ai/audit/02-config/findings.md` `CFG-006` |
| **Classification** | mandatory |

**Shared cause, once named.** A log record emitted before `structlog.configure` runs reaches structlog's
library default — `PrintLoggerFactory` to `sys.stdout`, plain `ConsoleRenderer` — instead of the
configured sink. Both findings name the same emission site (`config.py:313-319`) and the same ordering
(`cli.py:125`/`237` before `cli.py:128`/`240`) and the same modules.

**Absorbing ID: `ENT-001`.** `ENT-001` is the more complete account: it names the **second** pre-sink
record at `config.py:145` that `CFG-006` did not identify, it records the case where the configured log
file is never created at all, and it is typed `RUNTIME-ERROR` on a failure this run observed directly.
`CFG-006` is a strict subset. `CFG-006` is retained in full in
`.ai/audit/99-validation/02-config-validated-findings.md`; nothing is lost by the merge.

**One thing a fixer must not do: apply both recommendations.** They are mutually exclusive in shape.
`ENT-001` reorders the sink — move `setup_logging` earlier, or buffer and flush after
`structlog.configure`. `CFG-006` removes the emission from the logging path entirely — return the keys
from the scan and render them to stderr through `typer.echo(..., err=True)`. Applying both yields the
record twice. The reconciliation is already written in `CFG-006`'s own text: *"If the warning should
also reach the log artifact, emit it a second time after `setup_logging`"* — take that clause, or
`ENT-001`'s buffering, not both.

**Not a conflict.** No two phases assert incompatible facts about this subject. The claims agree; only
the framing and the fix direction differ. That is a merge, not a CRITICAL cross-phase conflict.

---

### VAL-102: `ENT-005` and `ENT-007` are one defect stated twice

| Field | Value |
|-------|-------|
| **ID** | VAL-102 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.ai/audit/01-entry-architecture/findings.md` `ENT-005`, `ENT-007` |
| **Classification** | mandatory |

**Shared cause, once named.** An eager package root republishes sibling names that nothing imports,
and the republish is what makes a cross-layer cycle load-bearing. `ENT-007` is the `utils/` instance of
`ENT-005`; `ENT-005`'s own root table already carries the row "utils/`__init__.py` | 5 names, two of
them private to siblings", and its recommendation already proposes deleting this exact block.

**Absorbing ID: `ENT-005`** (wider scope, proven causal chain, the fix that also unblocks
`ENT-009`). **Absorbed: `ENT-007`.** `ENT-007`'s full text is retained above and is not deleted.

**What only `ENT-007` carries, and is therefore not lost:** the `docs/STRUCT.md:39` claim, which
documents an export list that becomes wrong the moment the block is deleted. The source report routes
that to phase `09` under the pipeline's R-E rule rather than re-filing it. That cross-reference is
preserved in `ENT-007`'s retained block so the merge does not silently drop a documentation obligation.

---

### VAL-103: `ENT-014`'s recommended fix is anchored to the mechanism `CFG-001` classifies CRITICAL, on the same two lines, and is mutually exclusive with `CFG-002`

| Field | Value |
|-------|-------|
| **ID** | VAL-103 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `ENT-014`; `.ai/audit/02-config/findings.md` `CFG-001`, `CFG-002`; `src/vkdownloader/cli.py:127,239` |
| **Classification** | mandatory |

**The ordering constraint.** `ENT-014`'s recommendation is: *"resolve the override in the command
preamble, where the other CLI overrides already are resolved — `cli.py:127` and `cli.py:239` pass
`cookie_source` and `ssl_verify` as constructor arguments for exactly this reason. Pass `max_retries`
the same way."* `CFG-001` proves, with a controlled positive control through the process's own entry
point, that passing those constructor arguments is **the defect**: the Typer options default to
`CookieSource.NONE` and `True`, are never `None`, so a keyword is always passed and always wins the
model's documented precedence, and `VKDOWNLOADER_SSL_VERIFY` and `VKDOWNLOADER_COOKIE_SOURCE` can never
reach their fields.

**Unsafe ordering — either sequence breaks.**

- `CFG-001` first, then `ENT-014` as written: the anchor text is gone. "Pass `max_retries` the same way"
  points at a pattern `CFG-001` has just removed, and the two edits collide on `cli.py:127` and
  `cli.py:239`.
- `ENT-014` first: the shadowing is extended to a **third** setting. `max_retries` would become
  unreachable from `.env` and from `VKDOWNLOADER_MAX_RETRIES` exactly as `ssl_verify` and
  `cookie_source` are today.

**Fragile insertion point, and the specific trap.** The obvious fix — give every override a `None`
sentinel and pass it through — does not survive. `max_retries` is declared `int` with default `3`
(`config.py:55-60`), so `Settings(max_retries=None)` is a validation failure, not a pass-through. The
three options need one conditional-overrides construction applied together, not three separate edits.

**Mutually exclusive, not sequential, with `CFG-002`.** `CFG-002` says re-validate the override instead
of `model_copy`; `ENT-014` says delete `services/downloader.py:652-653` and resolve it in the preamble.
Landing one makes the other redundant and leaves dead code if applied after. **Pick one.**

**Severity, composed from this run.** CRITICAL under the rolloutsafety condition: a fix that cannot be
ordered safely because a prerequisite of it is itself a finding. Two of `ENT-014`'s three
prerequisites — the constructor-kwarg shape and the `model_copy` site — are the subjects of
`CFG-001` and `CFG-002`, both of them mandatory, one of them CRITICAL in its own right. `ENT-014` as
filed is not wrong; it is **unsafe to act on without the sibling findings**, and nothing in the source
report says so.

---

### VAL-104: `ENT-011` and `ENT-012` each require the other, and neither names it

| Field | Value |
|-------|-------|
| **ID** | VAL-104 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `ENT-011`, `ENT-012`; `src/vkdownloader/utils/correlation.py:38-44`; `src/vkdownloader/services/downloader.py:663-664,705-708`; `src/vkdownloader/services/batch_downloader.py:197-198,295-296,323-324,399-402` |
| **Classification** | mandatory |

**The hidden chain.** Both findings are individually correct and neither resolves the other's stated
consequence.

- `ENT-011` says make the clear key-scoped (`unbind_contextvars("correlation_id")`). Applied alone,
  the inner `download_video` bind at `downloader.py:664` still overwrites the batch item's bound
  identifier — same key — so `ENT-012`'s core defect, records carrying an identifier that appears
  nowhere else, **survives intact**.
- `ENT-012` says remove the bind/clear pair at `downloader.py:663-664` and `:705-708`. Applied alone,
  `_download_single`'s `finally` at `batch_downloader.py:296` and the run's `finally` at `:402` still
  call the whole-context clear, so `ENT-011`'s defect — a function named for one key that empties all
  of them — **survives intact**.

Neither source finding cross-references the other. A fixer who takes the first one off the list and
moves on will believe the correlation-identifier lifecycle is fixed when neither half is.

**Severity, composed from this run.** CRITICAL under the rollout-safety condition: `ENT-012`'s fix
cannot be ordered safely on its own because its prerequisite — a keyed clear — is `ENT-011`, itself a
finding. The same holds in reverse.

**Required sequencing, stated once:** `ENT-011` first (it is the one-line change and it is a
precondition), then `ENT-012` (which deletes the now-unnecessary inner bind/clear). Applying them in
the other order leaves `ENT-012` looking already-done and invites its deletion.

---

### VAL-105: `ENT-001`, `ENT-002` and `ENT-003` all target the same duplicated preamble, and no accepted finding owns the duplication

| Field | Value |
|-------|-------|
| **ID** | VAL-105 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `ENT-001`, `ENT-002`, `ENT-003`; `src/vkdownloader/cli.py:123-131,232-242` |
| **Classification** | mandatory |

**The shared anchor.** Three accepted mandatory findings fix the same eight lines, twice over:

```
cli.py:125-128                                   cli.py:237-240
  warn_unknown_env_vars()                          warn_unknown_env_vars()
  settings = Settings(cookie_source=…, …)         settings = Settings(cookie_source=…, …)
  setup_logging(settings)                          setup_logging(settings)
  _log_env_file_path()                             _log_env_file_path()
```

`ENT-001` moves `setup_logging` ahead of the emission. `ENT-002` makes the catch-all independent of the
sink whose creation it needs. `ENT-003` narrows the batch `except OSError` and adds "a preamble-level
handler shared with `download`". All three are the same block, in both commands, and there is no shared
function behind it.

**The missing link.** The source report names the duplication as the reason this class recurs —
`ENT-003` closes with *"Both commands should share one preamble and one failure-reporting path so this
class of divergence cannot recur"* — and then does not file the duplication. No accepted finding
extracts it. Three fixes therefore land on two hand-maintained copies of one block, and a fourth
divergence in this class is the expected outcome of applying all three.

**Ordering.** Safe in any sequence; the constraint is the shared anchor, not a blocking prerequisite,
which is why this is composed at MEDIUM rather than CRITICAL. Recorded so the implementer extracts the
preamble once — the change `ENT-003` already asks for — instead of patching it three more times.

---

### VAL-106: The orchestrator writes one validation filename and checks another

| Field | Value |
|-------|-------|
| **ID** | VAL-106 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:94` (write), `:105` (check) |
| **Classification** | mandatory |

**Both strings, with lines.**

```
:94   "Write validation report to: .ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md\n"
:105  Check that `.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated.md` exists.
      If missing or empty: retry once, then escalate on second failure.
```

`-validated-findings.md` against `-validated.md`. The check can never be satisfied by the write.

**Observed consequence.** Every validated phase ends in a false failure: the artifact is on disk under
the name the write step produced, the gate looks for a different one, finds nothing, burns the retry,
and escalates a phase whose validation actually completed. This run and the sibling phase-02 run both
wrote to the `:94` path and both satisfy the `:105` check for no file.

**Which side is defective.** The check. `:94` is the form the pipeline has always produced, and the
validator handbook's `## 11` names the same string as the one it writes. The fix is one string at
`:105`. This run wrote to `:94`.

**Severity, composed from this run.** CRITICAL as a rollout-safety blocker: the validation stage cannot
complete its own gate, so no phase's validation can report success. The artifact is produced and the
stage is reported as failed, on every phase, on every run.

---

### VAL-107: The condition that launches the validator cannot be evaluated, while the closing output reports validation coverage unconditionally

| Field | Value |
|-------|-------|
| **ID** | VAL-107 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:86` (gate), `:118` (output) |
| **Classification** | mandatory |

**The gate, and why it can never fire.**

```
:86   Launch the Validator **only** when Findings are **not trivial** ands relate to
      **significant code changes** or **architecture modifications**.
      In all other cases — skip.
```

Neither "not trivial" nor "significant" is defined anywhere in the pipeline. A tree-wide search for
both terms returns this line, the validator handbook quoting it back as a known defect, and
unrelated uses in other commands and role files — an *effort-estimate* vocabulary in `auditor.md:253`
and a *feature-significance* vocabulary in the docs commands. Nothing evaluates the condition and
nothing defines its terms.

**The summary that claims the coverage anyway.**

```
:118  Validated findings: {N} total
```

Printed unconditionally. There is no counter, no conditional, and no record of whether `:86` fired.
A stage that never runs and a summary asserting it ran are one defect, not two, and both sides are
filed here.

**Severity, composed from this run.** HIGH. The run's closing report cannot be trusted to describe
what executed, which is the output a reader uses to decide what was audited at all.

---

### VAL-108: The orchestrator instructs that rejected findings be deleted, contradicting the retention rule this artifact is built on

| Field | Value |
|-------|-------|
| **ID** | VAL-108 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:133`; `99-audit-validate.md` binding rule 2 and `## 11` |
| **Classification** | mandatory |

**Both instructions, quoted.**

```
audit-multi-phase.md:133   Rejected findings cleaned from file before merge
99-audit-validate.md:      | **Rejected** | Leave the block in the file as:
                                       `### {ID}: ~~{title}~~ [REJECTED]`
                                       + `> **Rejection reason:** {explanation}`.
                                       **Never delete it** — the claim and the reason are what stop
                                       the next run re-deriving it.
```

**What `:133` destroys.** The rejected claim and its reason — the two artefacts that stop the next run
re-deriving a claim already adjudicated. Stripping them before merge converts a decision record into
a silent deletion, and the next run re-derives the finding from scratch with no memory of the
rejection.

**The side this phase took, and why.** The preserving side governs this artifact's output. Every
rejected block in this record is retained with its reason. This run's tally is **Rejected 0**, so the
instruction has nothing to destroy *here*; it is filed because it is live in the pipeline and will
destroy the record of the first run that does reject something.

**Severity, composed from this run.** HIGH. The defect is not hypothetical loss of tidiness: retention
is the mechanism that makes an audit cumulative rather than repetitive, and this instruction removes
it at the last step, after the decision has been made.

---

### VAL-109: The orchestrator's mandatory context read names a file the repository does not hold

| Field | Value |
|-------|-------|
| **ID** | VAL-109 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:42-44,73`; repository root |
| **Classification** | mandatory |

**The read.**

```
:42   Read `.ai/context/commands.md` for verification commands.
:43   Read `AGENTS.md` for project guidelines.
:44   List documentation structure from `docs/` folder.
:73   + "Base context: {BASE_CONTEXT}\n"
```

**What the tree holds.** `.ai/context/commands.md` is present. `docs/` is present. **`AGENTS.md` is
not present** — not at the repository root and not anywhere within two levels of it. The project's
rules live in `.kilo/rules/` — `commands.md`, `project.md` — and the coding standards in
`.ai/context/`.

**Consequence.** `{BASE_CONTEXT}` is assembled from three reads, one of which yields nothing, and the
command reports nothing about the miss. The half-missing base context is then handed to **every**
executor subagent (`:73`) and every validator subagent (`:95`) in the run. No executor or validator in
this pipeline receives the project guidelines by that route.

**Required fix, stated once because the file is not there to be fixed:** `:43` should name
`.kilo/rules/project.md` (plus `.kilo/rules/commands.md`) — where the rules actually live — or the
read should be dropped so the omission is visible.

---

### VAL-110: The report format defines four type labels; both role files list three, and the format names an executor role the pipeline does not have

| Field | Value |
|-------|-------|
| **ID** | VAL-110 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.ai/audit/templates/audit-findings.md:4,68`; `.kilo/agents/auditor.md:257-259`; `.kilo/agents/validator.md:243-245,356-358`; `audit-multi-phase.md:75,98` |
| **Classification** | mandatory |

**A legal report is illegal to the agent that writes it.** The format fixes four type labels at
`:68` — `SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, `RUNTIME-ERROR`. Both role files list three:

```
auditor.md:257-259     [SPEC-DEVIATION]  [BEST-PRACTICE]  [DOC-UPDATE]
validator.md:243-245   SPEC-DEVIATION    BEST-PRACTICE    DOC-UPDATE
validator.md:356-358   SPEC-DEVIATION    BEST-PRACTICE    DOC-UPDATE
```

`RUNTIME-ERROR` is absent from both. **Three of the fourteen findings in the source report carry it** —
`ENT-001`, `ENT-002`, `ENT-003` — filed by a role whose own label list does not contain it, and
adjudicated by a role whose own label list does not contain it either. `ENT-001`, `ENT-002` and
`ENT-003` are all validated by this run with `RUNTIME-ERROR` retained; the labels are correct on the
merits, and the pipeline's own documents are what disagree.

**And the role name.** `audit-findings.md:4` declares `agent: audit-executor`; the source report's own
header carries `**Executor:** audit-executor`. The orchestrator launches `agent="auditor"`
(`audit-multi-phase.md:75`) and `agent="validator"` (`:98`). The role roster is
`analyst, auditor, docs-specialist, implementor, planner, researcher, tech-lead, test-engineer,
validator` — **`audit-executor` is not among them.** The format names an executor the pipeline cannot
launch, and every artifact it governs records that unreachable name as its provenance.

**Severity, composed from this run.** HIGH. The pipeline's documents disagree about what may be
written and by whom, and the disagreement is not cosmetic: the missing label is exactly the one the
three most severe runtime findings need, and the wrong role name is stamped on every report produced.

---

### VAL-111: The report format has no slot for the per-finding validation decision

| Field | Value |
|-------|-------|
| **ID** | VAL-111 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.ai/audit/templates/audit-findings.md:19-33,64-74` |
| **Classification** | mandatory |

**The finding block, quoted in full.**

```
:19   ### {ID}: {Title}
:21   | Field | Value |
:23   | **ID** | {id} |
:24   | **Severity** | {severity} |
:25   | **Type** | {type} |
:26   | **Affected Modules** | {modules} |
:27   | **Classification** | {mandatory\|advisory} |
:29   **Description:** {description}
:31   **Evidence:** {evidence}
:33   **Recommendation:** {recommendation}
```

The block runs from the heading straight into a fixed field table, and the nine mandatory fields at
`:64-74` — `id`, `title`, `type`, `severity`, `description`, `evidence`, `affected_modules`,
`recommendation`, `classification` — carry **no decision**. There is nowhere to record
`validated` / `reclassified` / `merged` / `rejected`, a rationale, or a cross-reference.

**Absent slot for all four decisions, for all 14 findings in scope.** Recorded in R0's decision-record
map before any per-finding decision was taken, so no decision in this artifact is unrecorded because
the format had nowhere to put it.

**Required fix.** The format's finding block must gain a decision field between the heading and the
field table. Until it does, every validator deviates in the same way and every deviation is
undiscoverable to a reader who has the template.

**Deviation used by this artifact.** The `Validation Note` block, placed directly after each heading, as
the validator handbook's `## 11` prescribes. The filename's verb is not a verdict: this file records
that a run happened, not that its contents survived.

---

### VAL-112: `VAL-` is minted independently by every per-phase validation run, so `VAL-001` means two different subjects

| Field | Value |
|-------|-------|
| **ID** | VAL-112 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.ai/audit/99-validation/01-entry-architecture-validated-findings.md`; `.ai/audit/99-validation/02-config-validated-findings.md`; `99-audit-validate.md` `## 10` |
| **Classification** | mandatory |

**The collision, from R0's identifier map.** `## 10` reserves `VAL-` for "defects in the audit inputs
themselves" and requires that no identifier already present in the tree be adopted. Two validator runs
have now executed against two phases. Both minted from the same starting point:

| ID | phase-01 store (this artifact) | phase-02 store |
|---|---|---|
| `VAL-001` | merge `ENT-001`/`CFG-006` | report format has no decision slot |
| `VAL-002` | merge `ENT-005`/`ENT-007` | orchestrator checks a filename it never writes |
| `VAL-003` | `ENT-014` ordering against `CFG-001`/`CFG-002` | validator-launch gate not evaluable |
| `VAL-004` | `ENT-011`/`ENT-012` chain | mandatory `AGENTS.md` read names an absent file |
| `VAL-005` | shared preamble anchor | rejected findings cleaned before merge |
| `VAL-006` | orchestrator write/check path mismatch | `CFG-001`/`CFG-002` collide with source comments |

Five of the six subjects in the phase-02 store are **the same five pipeline defects this run
independently re-derived and filed** — template slot, path mismatch, gate, `AGENTS.md`, rejected-content
deletion. The same defect now carries two different IDs in two stores, and a reader joining the two
reports by ID joins the wrong subjects.

**Resolution taken by this run.** This artifact numbers its findings `VAL-101`…`VAL-112` so that no ID
it mints collides with anything already in the tree, per `## 10`. The `VAL-001`…`VAL-006` block in the
phase-02 store is left exactly as that run wrote it; this run neither renumbers nor edits it.

**Required fix, architectural rather than cosmetic.** The prefix is per-*phase-run* where it needs to
be per-*pipeline*. Either the identifier carries the phase (`ENT` and `CFG` both do), or the validation
store is a single consolidated file rather than one copy per phase. Until then, cross-phase
adjudication has no stable key.

---

## Checkpoint 4 — R4 Assess Rollout Safety

- **Stage:** R4 Assess Rollout Safety
- **Findings in scope:** 14 accepted (11 validated, 2 reclassified, 1 merged)
- **Circular dependencies:** 0. No two accepted fixes are prerequisites of each other in a cycle.
- **Unsafe-ordering pairs:** 1 — `VAL-103`, `ENT-014` against `CFG-001` and `CFG-002`.
- **Hidden chains:** 2 — `VAL-104` (`ENT-011` requires `ENT-012` and vice versa, neither says so);
  `VAL-105` (three fixes share a duplicated block no finding owns).
- **Fragile insertion points:** 2 — both inside `VAL-103`: `ENT-014`'s anchor text names a pattern
  `CFG-001` removes, and the obvious `None`-sentinel shape fails validation against `int` default `3`.
- **Findings added:** 12 (`VAL-101`…`VAL-112`) — 2 merges, 3 ordering, 5 pipeline-document, 1
  report-contract, 1 identifier.
- **Blockers:** none for this phase. Every accepted finding is implementable; three are not
  implementable *as written* until a sibling finding lands first, and that is recorded above rather
  than assumed away.
- **Checkpoint status:** closed

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 11 | ENT-001, ENT-002, ENT-003, ENT-005, ENT-006, ENT-008, ENT-009, ENT-010, ENT-012, ENT-013, ENT-014 |
| Reclassified | 2 | ENT-004, ENT-011 |
| Merged | 1 | ENT-007 → ENT-005 |
| Rejected | 0 | — |
| VAL- (cross-phase / rollout) | 12 | VAL-101 … VAL-112 |

Four of the eleven validated findings had their **severity re-derived downward or corrected** against
the source report's evidence without the decision changing; the decisions and the severities are
recorded independently, and no severity was changed because of a decision. `ENT-006` and `ENT-012` were
validated with corrections to their supporting counts; `ENT-011` was reclassified and its consequence
narrowed. No finding was rejected, so the Rejected Findings table records a zero and no claim is
withheld from the next run.

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | No finding met a stated rejection ground. All 14 reproduced against source or were decided as merges or reclassifications. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| ENT-007 | ENT-005 (phase 01) | One cause: an eager package root republishing sibling names nothing imports, and load-bearing for a cross-layer cycle. `ENT-007` is the `utils/` instance; `ENT-005`'s table already carries the row and its recommendation already deletes this exact block. Its `docs/STRUCT.md:39` obligation is retained in the block above and routed to phase `09`. |
| CFG-006 | ENT-001 (phase 01) — absorbed, decided by the phase-02 validation | One cause: a record emitted before `structlog.configure` reaches structlog's default stdout sink. `ENT-001` names the same emission plus a second pre-sink record `CFG-006` missed. Content retained in full in the phase-02 store. The two recommendations are mutually exclusive in shape — recorded as `VAL-101`. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| ENT-004 | SPEC-DEVIATION | BEST-PRACTICE | No declared project rule places signal-handler registration in the entry layer. `docs/STRUCT.md:48` does not list it; the rule cited is the audit phase's own. A demonstrated consistency gap in a defensible arrangement. |
| ENT-011 | SPEC-DEVIATION | BEST-PRACTICE | No declared functional rule violated — the docstring documents the real behaviour. The defect is a name that does not match its body (project rule 8). Classification also corrected `mandatory` → `advisory`: the stated consequence does not reproduce, because `asyncio.Task` copies the context. |

## Warnings

**Architectural.** The entry layer owns two copies of one four-step preamble
(`cli.py:125-130`, `:237-242`) and three accepted fixes target it; extracting it once is the change
`ENT-003` already asks for and the only one that stops the class recurring (`VAL-105`). The service
layer reaches upward twice — presentation framework and exit-status decision (`ENT-008`) — and the
process-wide signal side effect lives below the entry layer for one of two commands (`ENT-004`).
Neither is urgent; both are the reason the layer boundaries are hard to state in one sentence.

**Maintainability / evolvability.** Three findings describe public surfaces that exist for nobody:
the four package roots (`ENT-005`), the 26-entry module facade over 14 private symbols with one
duplicated entry and an unpaired lifecycle helper (`ENT-006`). Both are kept alive by the tests that
would be rewritten alongside them, so neither will be removed by ordinary pressure. The correlation
helpers keep three unrelated facts in one place — a name that does not match its body (`ENT-011`), a
nested bind that orphans an enclosing identifier (`ENT-012`), and a single source of truth that nine
signatures reproduce as literals (`ENT-010`).

**Rollout.** Three accepted findings are not safe to act on as written. `ENT-014` extends a defect
phase 02 classifies CRITICAL and is mutually exclusive with `CFG-002` (`VAL-103`). `ENT-011` and
`ENT-012` each require the other and neither says so (`VAL-104`). `ENT-001` and `CFG-006` propose
mutually exclusive fixes to one cause (`VAL-101`). Two of the three would be applied wrong by a fixer
reading only their own finding.

**Pipeline.** The validation stage cannot pass its own gate (`VAL-106`); its launch condition is
unevaluable while its closing output claims the coverage anyway (`VAL-107`); its retention rule is
contradicted by the orchestrator's merge step (`VAL-108`); its base context is missing the project
rules entirely (`VAL-109`); and the format it writes is illegal to the role that writes it
(`VAL-110`) and has nowhere to record a validation decision (`VAL-111`). Cross-phase adjudication has
no stable key (`VAL-112`). A pipeline whose findings are sound and whose own gates do not close is the
state this run found.

## Required Fixes

Composed from this run's verification, not inherited.

1. `VAL-106` — align `audit-multi-phase.md:105` with the write string at `:94`. One string; unblocks
   every phase's validation gate.
2. `VAL-108` — delete or scope `audit-multi-phase.md:133`; the preserving side governs.
3. `VAL-110` — add `RUNTIME-ERROR` to `auditor.md:257-259` and `validator.md:243-245,356-358`, and
   replace `agent: audit-executor` in the format with a role the pipeline launches.
4. `VAL-103` — resolve `ENT-014` **with** `CFG-001` and `CFG-002` in one edit, as one
   conditional-overrides construction over `cookie_source`, `ssl_verify` and `max_retries`. Do not
   apply `ENT-014` as written; a per-option `None` sentinel fails against `max_retries: int = 3`.
5. `VAL-104` — `ENT-011` before `ENT-012`, in that order, as one change.
6. `VAL-101` — choose `ENT-001`'s sink ordering **or** `CFG-006`'s stderr rendering, not both.
7. `VAL-107` — define "trivial" and "significant", or remove the condition; either way make `:118`
   report what actually ran.
8. `VAL-109` — repoint `audit-multi-phase.md:43` at `.kilo/rules/project.md` and
   `.kilo/rules/commands.md`.
9. `VAL-111` — add a decision field to the format's finding block.
10. `VAL-112` — make the `VAL-` prefix carry the phase, or consolidate the validation store.

## Advisory Recommendations

| Area | Recommendation | Effort | Priority |
|---|---|---|---|
| `ENT-005` / `ENT-007` | Empty the four package roots; both deferrals then become ordinary module-scope imports. A/B-proven in this run. | small | recommended — highest ratio in the report |
| `ENT-009` | Hoist the correlation import to module scope next to `downloader.py:28-29`, or add the reason as a comment. A/B-proven safe. | trivial | recommended |
| `ENT-006` | Delete the `__all__` and the compatibility imports at `downloader.py:31-68`; point the test import sites at their owning modules — 14 of the 25 unique names are reached from tests and none from production. The comment at `:144-174` already names every owner. | small | recommended |
| `ENT-010` | Delete the nine literals or source them from the settings model, so the "single source of truth" comment at `downloader_throttle.py:18` becomes true. | small | recommended |
| `ENT-013` | Defer `yt_dlp` and `playwright` to `extractor.py`'s extraction functions and `rich`'s column classes to `RichProgressReporter.start()`. If the ~730–890 ms is judged acceptable, say so in `docs/STRUCT.md:48` instead — that is the cheaper half. | medium | recommended, not urgent |
| `ENT-004` | Move signal registration to the command layer for both commands, inside the `try`, so registration and deregistration are one `try/finally` in one layer. | small | recommended |
| `ENT-008` | Have `run_batch` return data plus the outcome enum the model layer already has, and leave the text and the exit-status choice to `cli.py`. | medium | recommended |
| `ENT-014` | Resolve the override in the preamble — **only** together with `CFG-001` and `CFG-002`, per `VAL-103`. | trivial | blocked on `VAL-103` |
| `docs/STRUCT.md` | `:39` documents a five-name export list as three, and `:48`'s layering description is what `ENT-008` contradicts. Phase `09`'s subject, cross-referenced here rather than re-filed. | trivial | recommended |

