# Plan 13 — CLI and Observability Audit Fixes

**Source of truth:** `.ai/audit/99-validation/08-cli-observability-validated-findings.md` (1881 lines)
**Baseline commit:** `d572d96` — `TRN-001: Remove FFMPEG download transport (DownloadMethod.FFMPEG)`
**Plan kind:** Development execution plan. Planning only — no code, no tests, no `.ai/audit/**` edits.
**Companion documents:** `.ai/plans/06-config-audit-fixes.md` (house skeleton), `.ai/plans/10-subprocess-browser-audit-fixes.md`, `.ai/plans/11-credentials-secrets-audit-fixes.md`, `.ai/plans/12-filesystem-artifacts-audit-fixes.md`.

**Working-tree note.** `src/vkdownloader/services/ytdlp_downloader.py` and `tests/test_hls_downloader.py` are **modified right now**, alongside `.ai/problems/PROBLEM.md`, `.kilo/commands/implement/implement-plan-multiagent.md`, seven tracked deletions under `.ai/plans/`, and untracked `tmp/`, `tmp_old_sec.md`, `tmp_old_sec2.md`. None of these is owned by this plan. Two of them (`ytdlp_downloader.py`, `test_hls_downloader.py`) are written by blocks in this plan; those blocks **must wait** until their diff is separable or must be sequenced after plans 10/11 release the files.

---

## 1. Scope

### 1.0 Binding Product Owner decision (governs this plan in full)

**yt-dlp is the loader. ffmpeg is not a download/loader transport. Segment download stays, and
ffmpeg stays as the segment merge engine.** This decision is binding on every block below and is not
re-litigated anywhere in this document.

| Fate | Symbols | Consequence for this plan |
|---|---|---|
| **Stays deleted, permanently** | `DownloadMethod.FFMPEG`, `HLSDownloader`, `download_with_ffmpeg`, `_temp_argfile`, `_format_argfile`, `FfmpegProgress`, `ProgressParser`, `read_progress`, `_PROGRESS_KEY_HANDLERS`, and every ffmpeg-as-loader help string, log record and doc claim | `d572d96` is **correct and permanent**. No restoration, no second removal pass, no re-filing of `OUT-014` or `OUT-017`. `B16`'s docstring fix becomes a correctness obligation, not a tidy-up. |
| **Stays permanently, as product surface** | `_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `_build_ffmpeg_concat_command`, `_required_merge_bytes`, `_check_merge_space`, `_await_ffmpeg_with_timeout`, `_MERGE_SPACE_MARGIN_BYTES`, and **`check_ffmpeg_available`** | `services/ffmpeg_utils.py` **can never be deleted whole**. **`check_ffmpeg_available` survives** — `CF-7` / `DV-4` is **CLOSED**. The group split in §4.4 is corrected and final. |

**Three consequences this plan acts on, and one it explicitly does not:**

1. **`B17`'s note changes content, not existence.** A migration note reading "ffmpeg is no longer
   used" is now **factually wrong**. The note must say the **loader** is gone and the **merger**
   stays. §3.18 carries the surviving wording and the rejected wordings with reasons.
2. **`B13` rises from conditional to settled importance.** The token-refresh fallback is the
   **segment** path. The segment path is now **permanent product surface**, so `B13` fixes the last
   diagnostic on the only merge path, and that path is not going away. §3.14 states this as settled.
3. **The `ffmpeg_not_found` hint string is **NOT** this plan's.** Measured in the live tree, its
   `hint` reads *"ffmpeg binary not found on PATH; downloads using ffmpeg or segment merge will
   fail"*. Under this decision the first clause names a `DownloadMethod` member that no longer
   exists, and the second **understates** the merge, which is now required rather than optional.
   Plan 16 owns the binary's constraint and the `OSError` arms (`P16-B8` / `P16-B9`); **the hint
   string in `ffmpeg_utils.check_ffmpeg_available` is the explicit boundary** — recorded in §4.3
   as `CF-12` and **not written by this plan**. §1.4 records the deferral.

### 1.0.1 Further binding Product Owner decisions — the CLI contract (A, B, C)

Three decisions, all binding, all closing decisions this plan previously carried open.

**Decision A — a four-code exit contract. Closes `D-1`; with the Tech Lead ruling it closes `D-6`
too.**

| Code | Meaning | Everything it covers |
|---|---|---|
| **`0`** | success | unchanged |
| **`1`** | **download failure, and nothing else** | invalid URL, unreadable URL file, no URLs found, missing streams, download error |
| **`2`** | **usage error — rejected before the command body ran** | unknown option/command, `--method ffmpeg` rejection, invalid `--cookie-source` / `--method` value, a `--quality` token that is neither keyword nor positive height, missing argument, a non-numeric `--max-retries` |
| **`3`** | **configuration error — the operator's setup is wrong** | **`--max-retries` out of range** (enforced by the model's validation in the command body — see `D-6`'s ruling in §3.6; **not** by Click's parse-time `IntRange`, which would exit `2`), and **any preamble failure** (`OUT-001`: a malformed `.env`, a setting the model rejects, a log directory that cannot be created) |
| **`4` and above** | **unallocated** | deliberately reserved so the contract has room; a future code does not have to renumber an existing one |

**The rationale, kept because it is the test the ruling was made against:** a script must be able to
tell "your setup is wrong" from "the download failed" **without parsing text**. That was `D-1`'s
stated criterion — *"choose `2` if the owner accepts widening the `2` row's prose, because `2` closes
the finding without adding a code"* — and the Owner declined it, because widening `2`'s prose to cover
a bad `.env` would have made a configuration error indistinguishable from a typo on the command line.
**A dedicated code is the criterion's only satisfaction.** `D-1`'s Alt B (`78` / `EX_CONFIG`) was
rejected in favour of a smaller, project-local `3`; the reasoning against `78` in the original block
— a POSIX sysexits convention that is Windows-meaningless, adding a code from outside the product's
own vocabulary — is what the Owner adopted.

**Two consequences that reach beyond the blocks named in the ruling:**

1. **`2` is now strictly narrower than it was.** The reference's `2` row currently reads "rejected by
   the argument parser before anything ran", and `3` takes a slice out of what `1` used to cover
   ("invalid URL, **configuration error**, download error"). **Both reference files' tables must be
   rewritten, not extended** — this is a re-partition of three rows, not a fourth row appended.
2. **`C5` now covers four code values instead of one.** `tests/test_cli.py` reads both reference
   files, so the doc edit and the code edit remain one commit — but the surface is larger and `B1`
   must state which rows it re-partitioned.

**Decision B — one log record per dropped line; stderr stays clean. Closes `D-8`.**

`D-8`'s default was chosen and is now the ruling: **one record per non-progress child line carrying
its text, and `sys.stderr` receives nothing.** This is the option that satisfies plan 11 `B5`'s
pinned clause and `OUT-007`'s requirement simultaneously (§3.8), so the collision recorded in `CF-2`
resolves in `B7`'s favour on the record half and in `B5`'s favour on the stderr half.

**What the rejection removes.** `D-8` Alt B (route dropped lines into the reporter's throttled
progress channel, i.e. **batching** or rate-limiting) stays rejected, and **stays rejected until a
per-video volume measurement exists.** Nothing in the repository records such a measurement; the
sibling progress branch already emits one record per line **without** throttling, so per-line records
are the established pattern. **A future reader may not re-open batching on intuition** — the only
thing that would justify it is a measured per-video non-progress line count above a stated threshold,
and no block in this plan produces that number.

**Decision C — `--log-level` only; no `--log-file`. Closes `D-2`; reverses half of `B2`.**

| Setting | Option? | Status |
|---|---|---|
| `Settings.log_level` | **`--log-level` is added** — annotated `LogLevel`, so Click derives the choice set and rule 10 is satisfied | **IN SCOPE** — half of `OUT-015` |
| `Settings.log_file` | **NO option.** The log file stays **environment-configured** — `VKDOWNLOADER_LOG_FILE` and `.env` only | **OUT OF SCOPE** — the other half of `OUT-015` |

**The hard consequence, and it changes `B2`'s fix.** `D-2` Alt A's justification was that adding
`--log-file` makes the existing hint in `_render_preamble_failure` *true as written*. Decision C
removes the option, so **that route is closed and the hint must be edited instead** — corrected to
point at `VKDOWNLOADER_LOG_FILE` and at `.env`, and to name no option at all. **This is the exact fix
for `Live-1`, and it is the `D-2 = Alt B` route, not the `Alt A` route `B2` was built on.** `B2`'s
scope, goal and acceptance criteria are rewritten accordingly in §3.3.

**What happens to the half of `OUT-015` that does not land.** `OUT-015` is **half closed, not
closed**: `log_level` gains an option; `log_file` does not. The residue is recorded in §1.4 and is
**not silently dropped**: the reference must state that log *destination* is environment-only, so the
asymmetry is a **stated decision** rather than the gap the finding describes. The residual cost is
stated plainly — an operator still cannot switch the sink, and therefore the `JSONRenderer` branch,
per run without editing a file on disk — which is the precondition `OUT-002`'s and `OUT-006`'s
per-run debugging wanted. Both blocks are unaffected in scope; `B3` and `B6` operate on whichever
renderer `setup_logging` selects, and neither assumes the option exists.

### 1.1 How this plan was derived

The only input is the **validated** findings file. Its method `R12` — re-derive every defect independently, anchor on a symbol rather than a position — was checked for soundness and accepted: each defect re-derives against the real tree and none depended on the auditor's own unwindowed assumptions.

The auditor's **provenance claim** ("no commit has landed") was true only of the validator's observation window. It is now false. `d572d96` landed the ffmpeg transport retirement, and that commit is the **owner of record** for everything it changed:

- **`OUT-014` is already fixed by the retirement's doc pass.** Nothing to plan; not re-filed.
- **The `--method ffmpeg` documentation surface is plan 10 `B10`'s obligation, not this plan's.** The eight files it spans (`README.md`, `docs/01-tools/api-reference.md`, `docs/01-tools/installation.md`, `docs/01-tools/quality-selection.md`, `docs/01-tools/vkdownloader-overview.md`, `docs/11-guides/configuration.md`, `docs/11-guides/vkdownloader-limitations.md`, and the two reference files) are **out of scope here**. Plan 10 `B10` did **not** deliver the doc pass with the deletion, so the drift is live — but it is not ours to close, and closing it here would collide with the owner.
- **`OUT-013` and `OUT-017`** are rejected and stay rejected. `OUT-017`'s residual (`"unknownp"` on a non-numeric quality label) is `NET-008`'s, at HIGH, in phase 03.
- **`VAL-001`, `VAL-002`** (both halves) are fixed.
- **`ProgressStatus` lost two of its four producers** with the transport; `test_ffmpeg_utils.py` (834 lines, 32 tests) survived **entirely** and still covers the merge engine that still spawns ffmpeg.

Findings are used as **measurements**, not as instructions. Where a finding's claim is contradicted by the current tree, the tree wins.

### 1.2 IN SCOPE

| Ref | Subject | Block |
|---|---|---|
| OUT-001 | Preamble failure shares the failed-download exit status | `B1` (status → **`3`**, Decision A) + `B2` (message's option name) |
| OUT-002 | Exception rendered twice; declared-JSON log mostly unparseable | `B3` |
| OUT-003 / OUT-004 | Correlation id: `ytdlp_extraction_error` has none; `video_id` absent from three events | `B4` |
| OUT-005 | `--max-retries` declares no range; out-of-range exits 1 | `B5` (→ **`3`**, model-enforced; Decision A + Tech Lead ruling) |
| OUT-006 | Terminal control sequences written into redirected runs | `B6` |
| OUT-007 | Non-progress child lines dropped with no destination | `B7` (**one record per line, stderr clean** — Decision B) |
| OUT-008 | `Total connections:` reports the video count | `B8` |
| OUT-009 | `ProgressStatus.SKIPPED` unaggregated and has no producer | `B9` |
| OUT-010 | Two predicates for one TTY surface (`is_enabled`, `Console.is_terminal`) | `B10` |
| OUT-011 | `stop()` has no `try`/`finally` around the handler restore | `B11` |
| OUT-012 | A line that began work is left non-terminal | `B12` |
| OUT-015 | `Settings.log_level` / `log_file` have no option | `B2` — **half in scope**: `--log-level` **only** (Decision C); `log_file` residue recorded (§1.4) |
| OUT-016 | Any `OSError` in the token-refresh fallback published as `failed_to_refresh_token` | `B13` |
| VAL-003 | Pipeline pins a commit **and** reads a working directory | `B14` |
| VAL-004 | One command reads a non-existent `AGENTS.md` | `B15` |
| VAL-005 | Census reaches the audit corpus, the phase directory and a stale worktree copy | `B15` |
| Live-1 | `_render_preamble_failure` advertises a non-existent `--log-file` | `B2` (owner), `B1` (consumer) |
| Live-2 | Stale ffmpeg **loader** claims in surviving code | `B16` |
| Live-3 | `--method ffmpeg` exits 2 with no migration note | `B17` (bounded — §1.4; **content changed by §1.0**) |
| Conflict-3 | OUT-002 needs a third writer slot after plan 11 `B6` and plan 12 `B11` | recorded in `B3` |
| Conflict-4 | OUT-007 contradicts plan 11 `B5`'s pinned clause | recorded in `B7` |
| Conflict-5 | OUT-001/OUT-015 vs plan 12 `B10` route (a) | recorded in `B2` |
| Conflict-6 | OUT-016 vs plan 12 `B6`/`B8` on the merge deferral comment | recorded in `B13` |
| Conflict-8 | Plan 11 `B3`: two of six acceptance criteria unsatisfiable as written | recorded, **not worked around** (`B14`) |
| Conflict-9 | Plan 11's `ffmpeg_utils` group split is wrong on two symbols | **RESOLVED** — corrected split is plan-of-record in §4.4; plan 11 wrong on `_merge_batch_segments` / `_perform_final_merge` **and** on `check_ffmpeg_available`; plan 12 §2.4.4 **wrong on `check_ffmpeg_available`** |
| CF-12 | `ffmpeg_not_found`'s hint string names a loader that no longer exists and understates the merge | **Recorded as plan 16's** (`P16-B8`/`P16-B9` own the binary's constraint; the hint string is the named boundary). **Not written by this plan.** |

### 1.3 OUT OF SCOPE

- **`check_ffmpeg_available`'s disposition — CLOSED by §1.0. The symbol stays permanently.** No block
  in this plan deletes, moves, renames, redefines or re-orders it. `CF-7` / `DV-4` is resolved in
  favour of plan 10's "preserve" position and is **no longer an open item**; §4.4 records the
  decision and the corrected group split.
- **The `ffmpeg_not_found` hint string.** Recorded in `CF-12` as plan 16's boundary. **Not written
  by this plan** (§1.0, §1.4).
- **The merge engine itself** (`ffmpeg_utils` group C). Permanent product surface; no block touches
  its behaviour, only `B16`'s adjacent comment in `progress_display.py`.
- **`docs/STRUCT.md`** — plan 12 `P12-B12`'s alone. Not re-filed.
- **`Settings.log_file` as a command-line option.** Ruled out by Decision C (§1.0.1). The log file
  stays environment-configured. `B2` adds **`--log-level` only**, and `_render_preamble_failure`'s
  hint is **corrected** to name `VKDOWNLOADER_LOG_FILE` and `.env` — never edited to advertise an
  option that does not exist.
- **Any change to `download`'s or `batch_download`'s exception clause that is not a `typer.Exit(code=3)`
  on a preamble failure**, and any change to `run_batch`'s own exit-code computation, which is
  correct and is phase 08's `OUT-013` territory.
- **The token-refresh fallback's own logic.** The fallback is the **segment** path, which the
  Product Owner has ruled **permanent product surface** (§1.0). `B13` fixes only the error
  attribution.
- **Plans 10/11/12 blocks.** They own the code. This plan supplies sequencing, alternatives and oracles; it duplicates no block.
- **Already-fixed findings** — `VAL-001`, `VAL-002`, `OUT-013`, `OUT-014`, `OUT-017`.
- **Any redesign of the observability stack.** No new logging facade, no renderer abstraction, no shared-constants module. `B6` and `B10` are bounded to the existing `Console` symbol.
- **The dirty `ytdlp_downloader.py` / `test_hls_downloader.py`** — recorded as `DV-2`, not owned.

### 1.4 DEFERRED (owner + re-entry condition)

| Ref | Deferred to | Re-entry |
|---|---|---|
| OUT-002's redaction processor | plan 11 `B6` + plan 12 `B11` | Three writers, one function (`setup_logging`'s processor list). `B3` re-verifies at execution time and writes **only** if the list literal is still open; otherwise `B3` ships the double-render half alone and defers the redaction slot. |
| OUT-007's test-contradiction edit | plan 11 `B5` | `B5` pins as live and non-weakened that `echo=False` writes **nothing** and emits **no record**. `OUT-007` requires the opposite. Production code is king → the test is wrong, but the edit belongs after `B5` lands and `B7` may not weaken a clause `B5` pinned. |
| OUT-001's message body beyond the option name | plan 12 `B10` | `B2` resolves `--log-file` first; only then may `B1` touch message text. |
| The eight-file `--method ffmpeg` doc surface | plan 10 `B10` | `B17` is bounded to the `--method` option's own help text plus the two `--method` rows in the two reference files. It may not touch the other six. |
| ~~OUT-015's second half — `Settings.log_file` as an option~~ | **RULED OUT by Decision C, recorded as a stated limitation.** `B2` adds `--log-level` and **no** log-file option. **The residue, stated rather than dropped:** (a) both reference files must say the log **destination** is environment-only (`VKDOWNLOADER_LOG_FILE` / `.env`), so the asymmetry is a **decision** and not the gap `OUT-015` describes; (b) an operator still cannot switch the sink — and therefore the `JSONRenderer` branch — per run without editing a file on disk; (c) that residual cost is the precondition `B3`'s JSON surface and `B6`'s redirected-run surface both wanted. **Neither `B3` nor `B6` changes scope** — both operate on whichever renderer `setup_logging` selects. Re-opens only if the Owner reverses Decision C. |
| ~~`check_ffmpeg_available`~~ | **CLOSED — no deferral.** Decided by the Product Owner (§1.0): the symbol **stays permanently**. It was never re-filed and is now not an item at all. |
| The `ffmpeg_not_found` hint string in `check_ffmpeg_available` | plan 16 (`P16-B8` / `P16-B9` own the binary's constraint and the `OSError` arms) | The hint is the named boundary (`CF-12`). It names a loader that no longer exists and understates a merge that is now required. **This plan does not write it** and records the boundary so exactly one plan owns the edit. |
| The 31-test oracle deficit | partially this plan | `B7` restores the dropped-line oracle. Strengthening `TestMethodFfmpegRemoved` — whose three tests assert only `exit_code == 2` and a whole-`--help` substring, neither of which distinguishes "value rejected" from "flag removed" — is recorded in `B14`'s oracle table, **not worked**. |
| Polars divergence | rule 11 vs. reality | Recorded as `DV-1`. Rule 11 requires Polars for data processing; the project has none and none is warranted here. No block may introduce it or re-file it. |

---

## 2. Baseline

### 2.1 Gates re-run by this Planner against `d572d96`

Every gate marked *measured* was executed in this session against `HEAD = d572d96`, not inherited from the brief.

| Command | Result | Gate? |
|---|---|---|
| `uv run pytest -q -rs` | **747 passed, 3 skipped, 1 warning, 34.66s** | **yes — pass count is a floor** |
| `uv run ruff check src tests` | `All checks passed!` | **yes** |
| `uv run ruff check .` | **not measured** — see note below | **no** |
| `uv run ruff format --check src tests` | `54 files already formatted` | **yes** |
| `uv run mypy src` | `Success: no issues found in 31 source files` | **yes** |
| `uv run mypy src tests` | **not re-measured**; brief reports 79 errors in 8 files | **no — delta only** |

**Where the measurement differs from the brief, the measurement wins.** The brief reported `745 collected / 742 passed / 3 skipped`. Measured is **747 passed / 3 skipped** — three more passing tests, the same skip count. The brief's figures are superseded; this plan's floor is **747 passed, 3 skipped**, and a block reporting fewer has deleted or weakened a test.

**`ruff check .` was deliberately not measured.** The working tree carries untracked `tmp/` scratch that is not ruff-excluded, so a repo-wide run is red for a reason that is not the product's. `ruff check src tests` is the gate; a repo-wide run is neither required nor permitted as one, and no block may touch `tmp/`, `tmp_old_sec.md` or `tmp_old_sec2.md`.

**`mypy src tests` was not re-measured** and its absolute count is not a gate in any case: it is already red, so only the change in its error count is informative. `mypy src` is the real type gate.

**The single warning is observed, never gated.** It is the known `RuntimeWarning: coroutine 'Event.wait' was never awaited` from `tests/test_downloader_throttle.py::TestProgressManager::test_overwrites_existing_progress`. A block that changes the count **reports** it; none may gate on it.

### 2.2 Binding project rules (`.kilo/rules/project.md` — the authority)

Rule 2 (production code is king — fix the tests, never the code) · Rule 3 (strict layer separation) · Rule 4 (single responsibility) · Rule 5 (no overengineering) · Rule 7 (follow existing patterns) · Rule 8 (meaningful naming) · Rule 9 (strict typing, no `any`) · Rule 10 (`StrEnum` for every fixed value, kept separately in models) · Rule 11 (Pydantic + Polars — **divergent, see `DV-1`**) · Rule 12 (no `print()`; `logging.getLogger(__name__)`) · Rule 13 (migrations for schema change) · Rule 14 (documentation stays current) · Rule 15 (small focused modules).

**`AGENTS.md` does not exist.** `.kilo/rules/project.md` is binding; the file `AGENTS.md` that two audit commands still name is absent — which is `VAL-004`'s subject and `B15`'s work.

### 2.3 Repository constraints

| # | Constraint |
|---|---|
| **C1** | **Cite symbols, never line numbers.** The tree is moving; `cli.py`, `config.py`, `segment_downloader.py` and every test file have drifted by tens of lines between the audit base and `HEAD`. Every block re-verifies its anchors **by symbol** at execution time and records the resolved symbol, never a position. |
| **C2** | **`cli.py` may not import a private symbol from `services/`.** Editing a re-export line in `services/downloader.py`'s `__all__` to make a private name importable is **never** the fix for any block here. The entry-layer boundary is declared in `docs/STRUCT.md`, which is plan 12's alone. |
| **C3** | **`patch("vkdownloader.cli.warn_unknown_env_vars")` must keep resolving.** Two live sites use that exact string path and `_run_command_preamble`'s docstring records that the call is resolved through the module global **deliberately**. A block may change what the function returns; it may not change how `cli.py` resolves it. |
| **C4** | **The two commands' Typer option blocks stay byte-identical except `--max-retries`'s help string** (`download`: "Maximum retry attempts for failed downloads"; `batch`: "…for failed segment downloads"). `B5` adds `min`/`max` to both `--max-retries` declarations; **no other option may diverge.** |
| **C5** | **`tests/test_cli.py` asserts the reference document.** `_REFERENCE_DOC_NAMES = ("cli-reference.md", "cli-reference-clean.md")` — a test reads both, so **doc and code move together in one commit or the suite fails.** |
| **C6** | **structlog, not stdlib `logging`, for application records.** `logger = get_logger(__name__)`; `logging.basicConfig(format="%(message)s")` exists only to receive structlog's rendered output. Rule 12 bans `print()`. |
| **C7** | **All enums live in `src/vkdownloader/models/enums.py`.** There is **no** shared-constants module and no `src/vkdownloader/constants.py`; do not create one. Rule 10 means `B13`'s new event name and `B9`'s third branch must be a `StrEnum` member or consistent with one. |
| **C8** | **`create=True` appears zero times.** A new module or package would edit **both** packaging frozensets in the same commit. This plan adds no file under `src/`, `tests/` or `docs/`. |
| **C9** | **`asyncio_mode` is unstated**, so `pytest-asyncio` runs **strict**: every `async def` test needs `@pytest.mark.asyncio`. An unmarked async test does not run and reads as a silent pass-count drop against §2.1. |
| **C10** | **Commit hygiene.** Stage by explicit path only — never `git add -A`/`.`/`-u`, `git reset`, `git checkout`, `git restore`, `git stash`, `--amend`, `--force`. Every block's pre-commit check is `git status --porcelain -- src tests docs pyproject.toml` and must show only that block's own edits. A block that cannot separate its diff from the dirty `ytdlp_downloader.py` **waits**. Message format `{type}({scope}): {description}`. |

### 2.4 The skip floor, and the packaging manifests

**The skip floor is 3, not 4.** The retirement killed `test_temp_argfile_permissions_are_0600` together with its subject `downloader._temp_argfile`. The three survivors are two in `tests/test_config.py` and one in `tests/test_hls_downloader.py`, all carrying the `D-11` reason. A **fourth** skip anywhere is review-blocking; a **lower** count is an improvement, not a violation — the rule is "never more than the `D-11` skips", not "always three".

**`tests/test_packaging.py` frozensets are measured at 73 (`EXPECTED_SDIST_ENTRIES`) and 32 (`EXPECTED_WHEEL_ENTRIES`)**, asserted against a **real build**. Any file added or removed under `src/`, `tests/` or `docs/` edits **both** sets in the same commit.

### 2.5 Documentation sites

| Document | Status |
|---|---|
| `docs/99-reference/cli-reference.md` + `cli-reference-clean.md` | **IN**, jointly (C5). `B2` (`--log-level`/`--log-file` rows, `--max-retries` range), `B5` (status map), `B7` (child-output suppression sentence), `B8` (summary unit), `B17` (`--method` migration note). The "no escape codes are written" sentence is `OUT-006`'s contradicted guarantee and is corrected by `B6`, **not** by a doc edit alone. |
| The eight-file `--method ffmpeg` surface | **OUT.** Plan 10 `B10`'s obligation; it did not land with the deletion, so the drift is live but not ours. `B17` is bounded to the `--method` help text and the two `--method` reference rows. |
| `docs/STRUCT.md` | **OUT — plan 12 `P12-B12`'s alone.** Not re-filed, not touched, not cited as a fix target. |
| `docs/11-guides/configuration.md`, `docs/01-tools/installation.md` | **OUT** for log-configuration claims (phase 02's `CFG-008`) and for ffmpeg claims (plan 10's). |

### 2.6 Test layout and the oracle gaps this plan inherits

| File | What it pins |
|---|---|
| `tests/test_cli.py` | `_REFERENCE_DOC_NAMES` (C5); `assert "Total connections:"` and `assert "Total connections: 2"` — **both break under `B8`**; two `warn_unknown_env_vars` patch sites (C3); the echo-suppression tests that read `echo` off `download_video`'s call kwargs; **no test asserts a preamble failure's exit status** — `OUT-001`'s open half. |
| `tests/test_hls_downloader.py` | **Four** `_echo_ytdlp_line` `echo=False` tests, including `test_ytdlp_echo_false_non_progress_line_no_output_no_log` — *"writes nothing and emits no debug log"*. That is the clause plan 11 `B5` pins as live and `OUT-007` requires inverted. **Currently modified in the working tree**; owned by plan 11 `B2`/`B3`/`B5`. |
| `tests/test_progress_display.py` | Four sites: two replace the module's `sys.stderr`, two inject `Console(..., force_terminal=True)` on an in-memory buffer — which **bypasses** the detection `OUT-010` audits. |
| `tests/test_config.py` | `setup_logging` tests; two of the three surviving `D-11` skips. |
| `tests/test_packaging.py` | Both frozensets (73/32). |
| `tests/test_ffmpeg_utils.py` | **834 lines, 32 tests, survived the retirement entirely** — proof that group C (`_merge_batch_segments`, `_perform_final_merge`, `_check_merge_space`, `_merge_segments_batched`) is alive and still spawns ffmpeg. |

**The gap that matters most: the suite has no stream-discipline oracle at all.** `CliRunner()` is **module-level with merged streams**, and **`mix_stderr` appears zero times** anywhere in the repository, as does `create=True`. The coverage census found **zero** sites asserting a stream is a terminal. Therefore **no test can distinguish stdout from stderr in any command**, `OUT-006`'s control-sequence claim and plan 11 `B6`'s pipeline transform have **no in-suite witness**, and `B6` cannot be verified by a test alone — it needs a two-file
`Start-Process -NoNewWindow -Wait -RedirectStandardOutput … -RedirectStandardError …` harness, the harness the phase-08 validator used and declared in `R12`. This is why `B6`'s Validator is required and why `B7` is sequenced after plan 11 `B5`, not beside it.

**Second gap, from the retirement.** It **killed 34 oracles** and **added 3** (`TestMethodFfmpegRemoved`), net **−31**. All three added tests assert only `exit_code == 2` and a whole-`--help` substring; **neither assertion distinguishes "value rejected by the enum" from "flag removed entirely"** — both would still pass if `--method` were deleted outright.

### 2.7 Recorded divergences and standing hazards

| # | Item | Disposition |
|---|---|---|
| **DV-1** | Rule 11 requires Polars; the project has none and none is warranted for the CLI/observability surface. | Standing divergence. No block introduces Polars and none re-files it. The batch summary aggregates a list of per-item tuples — control flow over a handful of items, not data processing; importing Polars would violate rule 5 far more seriously than it satisfies rule 11. |
| **DV-2** | `ytdlp_downloader.py` and `test_hls_downloader.py` are dirty now. | `B7` and `B13` write into `ytdlp_downloader.py`; `B7` writes into `test_hls_downloader.py`. Neither commits until its diff is separable; neither runs concurrently with plan 11 `B2`/`B3`/`B5`. |
| **DV-3** | `OUT-003`/`OUT-004`'s cores merged into phase 01's `ENT-012`, which does **not** close the remainders; no `REF-` identifier was minted for them. | `B4` explicitly adopts them. Recorded as an **ownership claim**, not a re-filing of `ENT-012`. |
| **DV-4** | **`check_ffmpeg_available` — RESOLVED, no longer a divergence.** Plan 10 `B10` preserved it and forbade deletion; plan 11 §2.2 called it group C; plan 12 §2.4.4 called it group B and retired it; `d572d96` preserved it in fact. **The Product Owner has decided: it stays permanently, as part of the segment merge engine.** Resolved in favour of plan 10; plan 12 §2.4.4 is wrong on this symbol. The symbol also has a live two-test oracle (`TestFfmpegAvailabilityCheck`). | **CLOSED (§1.0, §4.4). No block in this plan touches it; the hint string inside it is plan 16's (`CF-12`).** |

### 2.8 Baseline re-verification — `HEAD` moved to `b0fb032`

**§2.1–§2.7 above were measured at `d572d96`.** `HEAD` has since moved twice and every gate
was re-run. **Where the two measurements disagree, the later one governs and the earlier one
is superseded.** The floor for the whole plan is the `b0fb032` row.

| Command | `d572d96` (superseded) | `b0fb032` (**governing**) | Changed? |
|---|---|---|---|
| `uv run pytest -q -rs` | 747 passed, 3 skipped, 1 warning, 34.66s | **749 passed, 3 skipped, 1 warning, 34.06s** | **yes — floor is 749** |
| `uv run ruff check src tests` | clean | `All checks passed!` | no |
| `uv run ruff format --check src tests` | 54 files already formatted | **1 file would be reformatted, 53 files already formatted** | **yes — GATE IS RED** |
| `uv run mypy src` | clean, 31 files | `Success: no issues found in 31 source files` | no |

**Two commits landed, and both are plans 10/11's:**

- `435ba0b` `fix(downloader): make cookie-file cleanup unable to replace the download outcome` — plan 11 `B2` (cookie-file lifecycle).
- `b0fb032` `fix(ffmpeg): read cancel_subprocess's return contract correctly at its call sites`.

**Consequence 1 — `DV-2` is resolved.** `git status --porcelain -- src tests docs pyproject.toml`
now returns **empty**. The two formerly-dirty files were committed by those two commits. `B7`
and `B13` no longer carry a separability wait. The remaining untracked and modified paths
(`.ai/problems/PROBLEM.md`, `.kilo/commands/implement/implement-plan-multiagent.md`, seven
tracked `.ai/plans/` deletions, `tmp/`, `tmp_old_sec*.md`, the untracked plan files) are
outside `src tests docs pyproject.toml` and outside this plan.

**Consequence 2 — a gate is RED at baseline, and it is not ours.** `b0fb032` landed
`tests/test_hls_downloader.py` unformatted: two `with patch("vkdownloader.services.ytdlp_downloader.logger") as mock_logger:`
blocks were committed split across lines, which `ruff format` joins. `uv run ruff format --check src tests`
therefore exits **1** on a clean tree. This is a formatting-only defect introduced by a commit
that is not this plan's, and it **blocks `B7`**, the one block that writes into that file.

**`G0` — pre-flight gate clearing (not a numbered block; a precondition).**

- **Default:** `B7` **waits**. The owning plan (10/11) clears the formatting in its own
  commit — it is a `ruff format tests/test_hls_downloader.py` away and touches nothing else.
- **Criterion for the alternative:** if the owning plan has not cleared it by the time
  `B7` is released, `B7` carries a **formatting-only co-edit** of the same two `with patch(...)`
  blocks, declared explicitly in its commit message and recorded here. It is never folded
  silently into a behavioural change.
- **What `B7` may not do:** reformat the whole file, or reformat any region outside the two
  offending blocks. A blanket `ruff format` over `tests/` is forbidden — it would produce an
  unrelated multi-hundred-line diff.

**Consequence 3 — neither competing writer has landed.** `setup_logging`'s processor list is
still exactly `merge_contextvars → add_log_level → TimeStamper(fmt="iso", utc=True) →
format_exc_info → UnicodeDecoder() → JSONRenderer()/ConsoleRenderer()`, and `_echo_ytdlp_line`
still carries no transform. Plan 11 `B5` and `B6`, and plan 12 `B11`, are **all still pending** —
so every conflict slot declared in §4 is still genuinely contended.

### 2.9 Second re-verification — `HEAD` moved again to `58bb7ce`, and the floor moved again

**This is the second time during this plan's own preparation that `HEAD` moved under the
measurements, and the second time the floor changed.** It is also the exact failure `VAL-003`
describes, recurring live while the block that fixes it is being written.

| Command | `b0fb032` (superseded) | `58bb7ce` (**governing**) | Changed? |
|---|---|---|---|
| `uv run pytest -q -rs` | 749 passed, 3 skipped, 1 warning | **752 passed, 3 skipped, 1 warning, 36.24s** | **yes — floor is 752** |
| `uv run ruff check src tests` | clean | `All checks passed!` | no |
| `uv run ruff format --check src tests` | 1 file would be reformatted | **1 file would be reformatted** (`tests/test_hls_downloader.py`) | **no — still RED** |
| `uv run mypy src` | clean, 31 files | `Success: no issues found in 31 source files` | no |

**Third commit landed:** `58bb7ce` `fix(ytdlp): surface a failed reader task instead of discarding
it` — again plan 10/11's, again writing `ytdlp_downloader.py` and `tests/test_hls_downloader.py`.
The pass count rose by three; the skip count did not move; **the format gate did not clear.**

**`DV-2` recurred and then cleared again — the sequence is the evidence.** At one measurement
`git status --porcelain -- src tests docs` showed **both** files modified; minutes later, with
`58bb7ce` landed, the same command returned **empty**. A concurrent implementer was mid-edit. That
transient dirty state is precisely what an audit phase silently reads through, and precisely what
`P13-B14` is written to make impossible to hide. **`DV-2` stands as a recurring hazard, not a
one-time cleanup.**

**What this changes in the plan:**

1. **The floor is now 752 passed, 3 skipped.** Every occurrence of the previous `749+ passed` floor
   in §3, §6 and §7 is superseded by this section.
2. **`G0` is now the single most-urgent precondition in the plan.** It has survived two commits
   since it was identified, and it blocks the two blocks (`P13-B7`, `P13-B13`) that are otherwise
   ready. A formatting-only fix to two `with patch(...)` blocks has now survived three audits' worth
   of gate runs.
3. **§7.2's protocol is validated rather than theoretical.** "Every block re-runs all five gates and
   stops if the baseline differs" was written defensively; this section is the demonstration that
   the defence is necessary.

### 2.10 Third re-baseline — `HEAD` confirmed at `58bb7ce`, and `G0`'s location pinned

The Product Owner's re-baseline instruction names `58bb7ce` and a clean tree under `src`/`tests`.
Both were re-verified. **`HEAD = 58bb7ce`** (`fix(ytdlp): surface a failed reader task instead of
discarding it`) and `git status --porcelain -- src tests docs` returns **empty**. This is the
**fourth** commit observed moving during this plan's preparation.

| Gate | §2.9 (`58bb7ce`) | **Re-measured at `58bb7ce`** | Changed? |
|---|---|---|---|
| `uv run pytest -q -rs` | 752 passed, 3 skipped, 1 warning, 36.24s | **752 passed, 3 skipped, 1 warning, 38.91s** | **no — confirmed** |
| `uv run ruff check src tests` | clean | `All checks passed!` | no |
| `uv run ruff format --check src tests` | 1 file would be reformatted | **1 file would be reformatted, 53 files already formatted** | **no — STILL RED** |
| `uv run mypy src` | clean, 31 files | `Success: no issues found in 31 source files` | no |

**§2.9 is confirmed, not superseded.** The floor stands at **752 passed, 3 skipped**, lint clean,
format red, mypy clean. Nothing in §3, §6 or §7 needed to change, and this is the first
re-verification in this plan's history that did **not** move a number.

**`G0` — plain answer to the Owner's question: still blocking, and here is exactly why.**

The red is in `tests/test_hls_downloader.py`. It is **two** `with patch(...)` blocks, each split
across three lines where ruff joins them to one, and both sit inside the test class
**`TestYtDlpSubprocessShutdown`**. Their subject is subprocess shutdown, `cancel_subprocess`'s
return contract and the reader-task failure path — the subjects of `b0fb032` and `58bb7ce`.

| Question | Answer |
|---|---|
| Does `G0` still block `B7` and `B13`? | **Yes.** The format gate is red, and it is red in **the exact file both blocks must commit into**. A block that commits while the gate is red breaks the gate for the next block too. |
| Is the red **inside** `B7`'s / `B13`'s own scope? | **No — it is outside it, and that distinction changes what they may do.** `B7` edits `test_ytdlp_echo_false_non_progress_line_no_output_no_log`, one of the four `_echo_ytdlp_line` contract tests. `B13` adds two new tests for the token-refresh handler. Neither touches `TestYtDlpSubprocessShutdown`, and neither block has any business editing a test class owned by plans 10/11. |
| Is the red **inside their file**? | **Yes.** `tests/test_hls_downloader.py` is the file. That is why the gate matters to them even though the defect is not theirs. |

**Adjusted precondition, replacing §2.8's `G0`.** The default is unchanged — the owning plan (10/11)
clears it in its own commit, and it is a `ruff format` away and touches nothing else. The
alternative, available only if the owning plan has not cleared it, is **narrower than §2.8 stated**:
`B7` or `B13` may carry a **formatting-only co-edit of the two offending `with patch(...)` blocks
inside `TestYtDlpSubprocessShutdown` and nothing else** — declared explicitly in the commit message
and recorded here. **A blanket `ruff format` over `tests/` or over the file remains forbidden**: it
would sweep in regions neither block owns and produce an unrelated multi-hundred-line diff. Neither
block may make a behavioural change and a formatting change to the same region in one commit.

**A second fact, measured in the same session, that bears directly on `CF-7`.** The tree contains a
**live test class for `check_ffmpeg_available`**: `tests/test_hls_downloader.py` class
**`TestFfmpegAvailabilityCheck`**, two tests — one asserting the function returns a `bool`, one
asserting it caches its result across calls. The symbol has a dedicated oracle, and the Product
Owner has now ruled it permanent product surface. The two facts agree; §4.4 records this as
supporting evidence rather than as a separate argument.

### 2.11 Fourth re-baseline — `HEAD` at `09f1b10`, **`G0` resolved**, and a new transient red

Two more commits landed during this decision cycle: `db0e33e`
`fix(ffmpeg): keep the reader draining when a child line exceeds the stream limit` and
`09f1b10` `docs(sanitizer): correct the redaction capability claim`.

| Gate | §2.10 (`58bb7ce`) | **Re-measured at `09f1b10`** | Changed? |
|---|---|---|---|
| `uv run pytest -q -rs` | 752 passed, 3 skipped | **759 passed, 3 skipped, 1 warning, 34.81s** | **yes — floor is 759** |
| `uv run ruff check src tests` | clean | **`I001` — 1 error, `src/vkdownloader/services/ffmpeg_utils.py`** | **yes — RED** |
| `uv run ruff format --check src tests` | 1 file would be reformatted (`tests/test_hls_downloader.py`) | **1 file would be reformatted (`src/vkdownloader/services/ffmpeg_utils.py`)** | **the offender CHANGED** |
| `uv run mypy src` | clean, 31 files | `Success: no issues found in 31 source files` | no |

**`G0` — RESOLVED. `B7` and `B13` are no longer blocked.** Verified directly:

```
uv run ruff format --check tests\test_hls_downloader.py   ->  1 file already formatted
uv run ruff check       tests\test_hls_downloader.py     ->  All checks passed!
```

The two `with patch(...)` blocks in `TestYtDlpSubprocessShutdown` that `b0fb032` committed
unformatted, and that survived `435ba0b`, `b0fb032` and `58bb7ce` unfixed, **are now formatted.** The
narrowed fallback — a formatting-only co-edit of exactly those two blocks — is **retained as
insurance only** and is not to be exercised. §6's `P13-B7` and `P13-B13` `extra_context` are updated
accordingly.

**But the gate is red again, in a different file, for a different reason, and it is not this plan's.**
`src/vkdownloader/services/ffmpeg_utils.py` is **modified in the working tree** (`+6 / −2`,
uncommitted) and is mid-edit by a concurrent agent: its import block is un-sorted (`I001`) and its
formatting is off. Both reds come from that one in-flight file.

**How `B7` and `B13` handle this, stated so neither has to guess:**

1. **Their own precondition is met.** `tests/test_hls_downloader.py` is lint-clean and format-clean,
   verified per-file. `G0` no longer gates them.
2. **A whole-tree gate can still be red for someone else's in-flight work.** `B7` and `B13` run the
   scoped check on the file they touch and **report** any pre-existing whole-tree red in the commit
   message, naming the file — exactly the pattern §7.1 already defines for a pre-existing condition.
   They do **not** fix it, and they do **not** wait on it: an uncommitted edit in `ffmpeg_utils.py` is
   another agent's work in progress, and blocking on it would make this plan hostage to an
   uncommitted diff.
3. **If the concurrent edit commits without fixing its own formatting**, the red becomes a committed
   defect in `ffmpeg_utils.py` — **group C, permanent product surface, and not this plan's subject.**
   `B16`'s Auditor re-verifies `ffmpeg_utils.py`'s docstrings against §4.4.2's nine-symbol permanent
   list at execution time regardless of who edited it, but **no block in this plan edits that file.**

**`DV-2` again.** The tree under `src tests docs` is **not** clean again, for the same reason it was
not clean twice before. This is the **fourth** observed recurrence and it validates §7.2's
re-verification protocol rather than undermining it. The floor moves to **759 passed, 3 skipped**;
every occurrence of `759+ passed` in §3, §6 and §7 is superseded by this section.

---

## 3. Execution blocks

Seventeen blocks, one commit each. Blocks are presented in **risk order, not execution order**;
the linearisation and the reason for each position are in §4.

### 3.0 Conventions that bind every block

- **Anchors are symbol names only.** No `file:line` appears in any block's scope (`C1`). Every
  block re-verifies its anchors by symbol at execution time and records the resolved symbol.
  If a symbol named here does not exist, **the block stops and reports** — it does not
  substitute a neighbouring name.
- **`Teardown order`:** every block runs `pytest -q -rs`, `ruff check src tests`,
  `ruff format --check src tests`, `mypy src` before its commit. The floors are **759 passed,
  3 skipped**, lint clean, format clean, mypy clean. `ruff format` is red at baseline (§2.8);
  a block that does not touch `tests/test_hls_downloader.py` reports the pre-existing red and
  does **not** fix it; `B7` is the only block for which `G0` applies.
- **`tests/test_packaging.py`:** no block adds or removes a file under `src/`, `tests/` or
  `docs/`, so both frozensets stay at **73/32**. A block that needs a new module edits both
  sets in the same commit and justifies the file; none of these seventeen does.
- **Doc coupling (`C5`):** `docs/99-reference/cli-reference.md` and `cli-reference-clean.md`
  are read by one test. A block that edits either edits both in the same commit.
- **Test oracle deficit.** `B1`, `B2`, `B6`, `B7` and `B8` each need an oracle that **does not
  exist today**. Writing it is part of the block, not a follow-up.

### 3.1 Severity → block assignment

| Block | Finding | Severity | Risk tier | Decides | Agents |
|---|---|---|---|---|---|
| `B1` | OUT-001 (status half) | CRITICAL | **High** | `D-1` | A · R · P · V |
| `B2` | OUT-015 + Live-1 | LOW | **High** | `D-2`, `D-3` | A · R · P · V |
| `B3` | OUT-002 | MEDIUM | **High** | `D-4` | A · R · P · V |
| `B4` | OUT-003/004 remainders | MEDIUM | Medium | `D-5` | A · P · V |
| `B5` | OUT-005 | MEDIUM | Medium | `D-6` **(CLOSED — model-enforced)** | A · V |
| `B6` | OUT-006 | MEDIUM | Medium | `D-7` | A · P · V |
| `B7` | OUT-007 | MEDIUM | Medium | `D-7` | A · P · V |
| `B13` | OUT-016 | LOW | Medium | `D-8` | A · P · V |
| `B8` | OUT-008 | LOW | Low | — | A · V |
| `B9` | OUT-009 | LOW | Low | `D-9` | A · P · V |
| `B10` | OUT-010 | LOW | Low | `D-10` | A · P · V |
| `B11` | OUT-011 | LOW | Low | — | A · V |
| `B12` | OUT-012 | LOW | Low | — | A · V |
| `B14` | VAL-003 | HIGH | **High** | — | A · R · P · V |
| `B15` | VAL-004 + VAL-005 | MEDIUM | Medium | — | A · R · P · V |
| `B16` | Live-2 | LOW | Low | — | A · V |
| `B17` | Live-3 | LOW | Low | `D-11` | A · P · V |

A = Auditor · R = Researcher · P = Planner · V = Validator. **All four required for `B1`, `B2`,
`B3`, `B14`** (shared exit contract; two coupled option blocks; a three-writer function; the
pipeline's provenance gate). `B15` takes Researcher because it edits command documents whose
own format rules must be read, not guessed.

### 3.2 `B1` — A preamble failure must not exit with a failed download's status (OUT-001, CRITICAL)

**Carries:** `OUT-001`, **status half only**. The `_PreambleFailure` / `_render_preamble_failure` /
`_logging_configured` machinery exists and both commands catch the wrapper; the half that is open
is the exit status. **Partially fixed on arrival.**

**Goal.** Today `download` and `batch_download` both handle a `_PreambleFailure` with
`raise typer.Exit(code=1)` — the identical status the `Download failed` branch uses. A caller
that branches on exit status cannot tell "the bootstrap never ran" from "the download ran and
failed", which is the whole point of the status. **Decision A (§1.0.1) rules: the preamble failure
exits `3`**, the dedicated configuration-error code, in both commands.

**Exact semantic scope.**

- `cli.py::download` — the `except _PreambleFailure` clause. **The status becomes `3`.** Its body
  stays `_render_preamble_failure(exc)`; the message is `B2`'s.
- `cli.py::batch_download` — the same clause, the same one-token change.
- `docs/99-reference/cli-reference.md` and `cli-reference-clean.md` — **both** commands' exit-code
  tables, rewritten as a **re-partition of three rows, not a fourth row appended** (`C5`). Today the
  `1` row for `download` reads *"Failure — the command ran and failed: invalid URL, **configuration
  error**, download error, or missing streams"* and the `2` row is scoped to *"rejected by the
  argument parser before anything ran"*. Decision A moves configuration errors out of `1` into a new
  `3`, and narrows `1` to download failures alone. Both tables also gain a **`4`-and-above-unallocated**
  line so the contract's shape is stated once.
- `tests/test_cli.py` — a **new** test class or set for the preamble failure path. There is
  **no oracle for this status anywhere today** (§2.6) — and under Decision A this is now also the
  **only** oracle for the new `3` code, so the test must pin `3` **by name**, not "non-zero" and not
  "different from `1`". **Both** commands.

**`D-1` — CLOSED by Decision A (§1.0.1). Retained as the decision record.**

- **RULING: the preamble failure exits `3`.** `1` is the download-failure code and nothing else;
  `2` remains the usage-error code; `3` is the configuration-error code covering both the
  `--max-retries` out-of-range case and the preamble failure; `4` and above are unallocated.
- **What `D-1` was, and what replaced it.** The open decision offered **Alt A: `2`**, widening the
  `2` row's prose from "rejected by the argument parser" to "rejected before the command body ran";
  and **Alt B: `78` / `EX_CONFIG`**, naming the class exactly at the cost of importing a POSIX
  sysexits convention. The default was Alt A.
- **Why the default lost.** `D-1`'s own criterion — *"choose `2` if the owner accepts widening the
  `2` row's prose, because `2` closes the finding without adding a code"* — is what the ruling was
  tested against, and widening `2` was refused: a bad `.env` and a typo on the command line are not
  the same class of operator mistake, and collapsing them into one code defeats the finding. The
  criterion's demand for a **dedicated** code is satisfied by `3` rather than `78`, which also
  answers the objection recorded against `78` — a Windows-meaningless external convention, and a
  wider number than the contract needs.
- **`D-1` is closed and must not be re-opened by an implementer.** Any block that finds a reason to
  prefer `2` records it against this section rather than acting on it.

**Acceptance criteria.**

1. Both commands exit **`3`** on a preamble failure, and the assertion **names the number**.
2. `3` differs from `1` (download failure) and from `2` (usage error) — all three asserted, because a
   contract with three codes is only useful if the three are distinguishable.
3. `pytest tests/test_cli.py -q` includes **new** assertions for both commands.
4. Both reference files list all four states (`0`, `1`, `2`, `3`, plus `4`-and-above-unallocated),
   and the prose distinguishes `1` "the command ran and failed" from `3` "your setup is wrong" —
   **without relying on the `2` row's "nothing was attempted" rationale, which no longer covers `3`.**
5. A failed download still exits `1` — asserted, not assumed — and the `1` row no longer lists
   "configuration error".
6. `_render_preamble_failure`'s **message text is unchanged** unless `B2` has landed first; if `B2`
   has not, `B1` does not touch the message and says so in its commit.
7. `patch("vkdownloader.cli.warn_unknown_env_vars")` still resolves (C3) — the new test must use that
   path, not a private import.
8. The `CF-13` clause neighbourhood is respected: `B5` owns the `ValidationError` clause and `B1`
   owns `_PreambleFailure`; if both produce `3`, their reference edits must be reconciled in **one**
   commit or sequenced — they write the same table.
9. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** The `except Exception` catch-alls (their status is correct at `1`); the
`ValidationError` / `InvalidVideoUrlError` / `VideoNotFoundError` / `QualityNotAvailableError`
clauses; `run_batch`'s own exit-code computation, which is phase 08's `OUT-013` territory and
already correct.

**Agents.** **Auditor** (re-derive every exit status both commands can return, including the ones
raised from inside the preamble helper, so `D-1` is chosen against the full vocabulary and not a
partial one) · **Researcher** (Click/Typer's documented exit-code convention — whether a
non-`UsageError` exception inside a command may raise `Exit` with an arbitrary code without
Click rewriting it, which is a library contract, not an assumption) · **Planner** (`D-1` changes
what four reference table rows say) · **Validator** (the finding is that two outcomes are
indistinguishable; only an independent check that the new statuses actually differ proves it).

**Commit:** `fix(cli): give a preamble failure its own exit status`

---

### 3.3 `B2` — `--log-level` becomes an option, and the failure hint stops naming one that does not exist (OUT-015 half + Live-1, HIGH)

**Carries:** **half** of `OUT-015` — `log_level` only — and **Live-1**, a defect in no store:
`_render_preamble_failure` tells the operator to *"Check the `--log-file` option"* when `download` and
`batch` declare no such option. Live-1 is a **new spec-deviation introduced by `OUT-001`'s own fix**
and a direct consequence of `OUT-015` being open. It is the reason this block is HIGH risk despite a
LOW finding: **the message is wrong today, and every message edit that does not land here reproduces
it.**

**Rewritten by Decision C (§1.0.1).** This block was built on the assumption that **both** options
would be added, which would have made the existing hint true by adding the flag it names. **Decision C
rules that out**: the log file stays environment-configured, so **the message is corrected rather than
the option added.** `OUT-015` lands **half in scope**: `log_level` gains an option; `log_file` does
not, and its residue is recorded in §1.4, not dropped.

**Goal.** `Settings.log_level` and `Settings.log_file` are the only two fields that decide what the
process emits, and neither reaches the caller as an option. Both are reachable from `VKDOWNLOADER_*`
and `.env` alone, while the options that *do* exist (`--cookie-source`, `--ssl-verify`) each name
their environment source in their help text. This block closes the asymmetry for **verbosity**, makes
`_render_preamble_failure`'s hint **true by naming only what exists**, and — because `log_file` gains
nothing — makes the reference **state** that log destination is environment-only, so the residual is a
decision rather than a gap.

**Exact semantic scope.**

- `cli.py::_SettingsOverrides` — a key for the new option, `total=False` so an unsupplied option
  occupies no configuration source and leaves the env/`.env` precedence intact.
- `cli.py::_build_settings` — forwards the key, same shape as the three existing keys.
- `cli.py::_run_command_preamble` — its keyword-only parameter list gains the key.
- `cli.py::download` and `cli.py::batch_download` — the **`--log-level`** declaration. **The two
  blocks stay byte-identical except `--max-retries`'s help string** (`C4`). A block that adds the
  option to one command and not the other has failed. **`--log-file` is NOT added.**
- `models/enums.py` — **verify** `LogLevel` exists and is the `StrEnum` the option annotates. No new
  enum is minted here (`C7`); if `LogLevel` does not exist, **stop and report** rather than creating
  one in this block.
- `cli.py::_render_preamble_failure` — the log-file hint string, **corrected to name
  `VKDOWNLOADER_LOG_FILE` and `.env` and to name no option.** This is Live-1's fix.
- `docs/99-reference/*.md` — both files (`C5`): the `--log-level` row for both commands, **and a
  stated-limitation sentence that the log destination is environment-only.**

**`D-2` — CLOSED by Decision C (§1.0.1). Retained as the decision record.**

- **RULING: `--log-level` only. No `--log-file`. The log file stays environment-configured.**
- **What `D-2` was.** Alt A (default) declared **both** options, on the reasoning that adding
  `--log-file` makes the existing hint true *as written* and makes the per-run debugging `OUT-002` and
  `OUT-006` need available without editing a file on disk. Alt B declared `--log-level` only and
  reworded the hint to name `VKDOWNLOADER_LOG_FILE` alone. Alt C declared neither and stated that log
  configuration is environment-only.
- **Why Alt A lost, recorded so it is not re-proposed as if it were the plan's idea.** The Owner chose
  **Alt B**, with a piece of Alt C: `log_level` becomes an option (Alt B) **and** the reference states
  the environment-only destination explicitly (Alt C). The cost Alt A was chosen to avoid — an extra
  option on two commands that must stay byte-identical, and a per-run sink switch that widens the
  surface `C4` guards — outweighed the debugging convenience. **The consequence is the point of the
  decision:** `_render_preamble_failure` must now be *edited*, not *justified*, and the edit is what
  closes Live-1.
- **`D-2` is closed and must not be re-opened by an implementer.**

**`D-3` — where the new option routes into `Settings`. Still open, unchanged by Decision C.**

- **Alt A (default, and effectively the only admissible option):** `_SettingsOverrides` →
  `_build_settings` → `Settings(**overrides)`, exactly as `cookie_source`, `ssl_verify` and
  `max_retries` already do. Preserves the documented precedence (constructor keyword, then
  `VKDOWNLOADER_*`, then `.env`, then field default) that `_build_settings`'s docstring states.
- **Alt B:** have the command assign onto the constructed `Settings` afterwards. Rejected —
  mutating a validated model post-construction bypasses Pydantic validation and breaks the
  "one `Settings` instance" identity the preamble returns. Recorded so it is not re-proposed.

**Acceptance criteria.**

1. `download --help` and `batch --help` list **`--log-level`** and its declaration is byte-identical
   in both commands (`C4`, verified by reading both, not by diffing a captured help).
2. **Neither help output contains `--log-file`**, and no option declaration for it exists.
3. Supplying `--log-level` changes verbosity; **not** supplying it leaves `VKDOWNLOADER_LOG_LEVEL` /
   `.env` reachable — asserted **in both directions**, because the failure mode of this block is
   silently shadowing the environment.
4. **Live-1 is closed by construction:** the hint in `_render_preamble_failure` names **no option**,
   names `VKDOWNLOADER_LOG_FILE` (and `.env`), and a test asserts that **every option-looking token in
   the message resolves against the captured `--help`.** That assertion is the direct fix for the
   defect, which was a message naming a flag that did not exist.
5. **The log-destination residue is stated, not dropped:** both reference files say the log file is
   environment-configured via `VKDOWNLOADER_LOG_FILE` / `.env` and that no option selects it (§1.4).
6. The two option blocks differ **only** in `--max-retries`'s help string.
7. `patch("vkdownloader.cli.warn_unknown_env_vars")` still resolves (C3) — the new tests use the
   string path.
8. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** `setup_logging`'s processor list (`OUT-002` is `B3`'s; plan 11 `B6` and plan 12
`B11` are the other two writers) · the renderer/sink selection logic itself, which `B2` only
makes reachable · any change to how the log file's permissions are requested — plan 11 `B3` owns
the `SEC-003:` comment above the `touch`/`chmod` branches and plan 12 `P12-B11` owns the posture.

**Collision.** Plan 12 `P12-B10` route (a) is **the only block plan 12 called unconstrained** —
it was granted freedom over the option block that declares output settings. This phase removes
that freedom: **`B2` is the owner of `--log-level`**, and `P12-B10` must either re-sequence behind
`B2` or narrow its route. Recorded in §4's conflict matrix; not resolved here. **Decision C narrows
`B2`'s claim further** — the block now adds exactly one option, so plan 12's route (a) is even less
likely to have room on the option surface.

**Agents.** **Auditor** (enumerate every option both commands declare and prove the "exactly two
near-identical blocks" blast radius is still two after any intervening commit) · **Researcher**
(Typer/Click `Path` option handling and whether an explicit `--log-file` default of `None`
preserves the "unsupplied occupies no configuration source" rule; also whether Click's envvar
mechanism interacts with a constructor-keyword route) · **Planner** (`D-2` and `D-3`, and the
four reference rows that change) · **Validator** (the failure this block exists to prevent is a
*message naming a non-existent option*; only an independent reader checking the hint against the
captured `--help` proves it is gone).

**Commit:** `fix(cli): expose log level and log file as options and correct the failure hint`

### 3.4 `B3` — One exception renders once, and the declared JSON is parseable (OUT-002, MEDIUM — HIGH contention)

**Carries:** `OUT-002`. **Three writers touch `setup_logging`; this is the third.**

**Goal.** Two distinct defects, one cause. `format_exc_info` clears `exc_info` from the **structlog
event dict only**, converting it into an `exception` string key; the stdlib `logging.Formatter`
underneath then re-appends the traceback from the **LogRecord**. Result: the traceback is
rendered **twice**, and every record carrying an exception makes the log file **unparseable as
one-JSON-object-per-line** — the JSON object is followed by a multi-line traceback.

**Exact semantic scope.**

- `config.py::setup_logging` — `structlog.configure(processors=[...])` and, only if `D-4` selects
  Alt B, `logging.basicConfig`. The chain is exactly
  `structlog.contextvars.merge_contextvars → structlog.stdlib.add_log_level →
  structlog.processors.TimeStamper(fmt="iso", utc=True) → structlog.processors.format_exc_info →
  structlog.processors.UnicodeDecoder() → structlog.processors.JSONRenderer() if settings.log_file
  else structlog.dev.ConsoleRenderer()`. Verify each element by symbol at execution time.
- `config.py::setup_logging`'s docstring — it states what it configures and must state the new
  guarantee.
- `tests/test_config.py` — **new** oracles: a log file written with an exception-carrying record
  parses **line-by-line** as JSON, and the traceback appears **once**. There is no such test today
  (§2.6) and two of this file's existing tests skip on Windows (`D-11`).
- **Not** the call sites. Sixteen records across `infrastructure/browser.py`, `cli.py`,
  `services/batch_downloader.py` and `services/extractor.py` carry exception text; plan 11 `B6`
  owns redaction over all of them and `B3` changes none of them.

**`D-4` — how the second render is suppressed. Not chosen here.**

- **Alt A (default): clear `exc_info` on the `LogRecord` before the handler formats it.** One
  small processor placed **after** `format_exc_info` and **before** `UnicodeDecoder`, whose only
  action is to clear the `exc_info` attribute on the stdlib logger it is handed. `format_exc_info`
  has already moved the traceback into the event dict, so nothing is lost; the traceback then
  travels **once**, as a JSON key, and each log line is exactly one JSON object. One list entry,
  no handler change, no change to any call site.
- **Alt B: `structlog.stdlib.ProcessorFormatter`.** The canonical structlog answer — the handler
  renders the event dict itself and the stdlib formatter stops participating. Costs: it replaces
  `logging.basicConfig(format="%(message)s")` wholesale, which is `C6`'s stated arrangement, and it
  changes where rendering happens for **every** record in the process, including records emitted
  before `setup_logging` runs. Larger blast radius than the finding warrants.
- **Alt C: stop passing exception info and pass the text explicitly at each call site.** Rejected:
  sixteen records across four files, three of which belong to other plans. Recorded so it is not
  re-proposed.

**Criterion.** Choose **A** unless the owner wants structlog to become the sole renderer for the
process — `B3`'s scope is a MEDIUM observability defect with a bounded cause, and Alt A closes
both halves at the narrowest possible site. Choose **B** only if a second requirement exists that
stdlib handlers must render structlog events; no such requirement is recorded in the repository.

**Collision — declared slots, not acknowledgement.** `setup_logging` has three writers:

| Writer | What it writes | Region of the function |
|---|---|---|
| **plan 11 `B6`** | a redaction processor, placed **immediately after `format_exc_info`** | the processor list — **adjacent lines** to `B3`'s slot |
| **plan 12 `P12-B11`** (`ART-007`) | the `SEC-003:` comment above the log-file `touch`/`chmod` branches, and the confinement posture | the log-file creation branch, above `basicConfig` |
| **`B3`** (`D-4`) | the `exc_info`-clearing processor | the processor list, after `format_exc_info` |

**Rules.** (a) `B3` may not land while plan 11 `B6` is pending **unless** `B3` places its entry at
the **end** of the list, where a later `B6` insertion above it cannot merge-conflict; the
preferred order is `B6` → `B3`. (b) `B3` may not edit the `SEC-003:` comment at all — that is
plan 11 `B3`'s and plan 12 `P12-B11`'s. (c) If `D-4` resolves to Alt B, `B3` **must** wait for
both other writers, because Alt B rewrites the `basicConfig` call that `P12-B11`'s posture
comment sits above.

**Acceptance criteria.**

1. A log file written with `VKDOWNLOADER_LOG_FILE` set, containing a record carrying exception
   info, parses **every line** as a JSON object. This is the core assertion and it has no test today.
2. The traceback appears **exactly once** in that file, and it appears **inside** the JSON object,
   as a key — not appended after it.
3. The non-exception records in the same file still parse, and `TimeStamper`'s ISO/UTC stamp and
   `add_log_level`'s level key are unchanged.
4. The `ConsoleRenderer` (stderr) path still renders the traceback, exactly once.
5. No call site was edited, and the sixteen-record count from plan 11 `B6` is unchanged.
6. The `SEC-003:` comment and the log-file creation branch are byte-unchanged (plan 12 `P12-B11`'s).
7. Floors: 759+ passed, **3** skipped — **neither new test may skip on Windows**; `B3` adds no
   permission assertion and must not convert or touch the two `D-11` oracles in this file.

**Out of scope.** The redaction processor (plan 11 `B6`) · the `SEC-003:` comment and the
confinement posture (plan 12 `P12-B11`) · the log file's permission request (plan 11 `B3`) ·
`log_level`/`log_file` reachability (`B2`) · `UnicodeDecoder`'s necessity, which is unchanged.

**Agents.** **Auditor** (re-derive the chain **and** count the exception-carrying records, so
`B3` proves it changed none of them — this is the assertion most likely to be quietly violated) ·
**Researcher** (structlog's `ProcessorFormatter` contract and whether a processor may legally
mutate the stdlib logger it receives under `cache_logger_on_first_use = True`; **library
behaviour, not assumption**) · **Planner** (`D-4`, and the three-writer slot arithmetic) ·
**Validator** (a JSON-parseability claim is only worth what an independent parse of a real file
is; the Implementor writing both the fix and the parser would be the weakest possible evidence).

**Commit:** `fix(logging): render an exception once and keep the JSON log parseable`

---

### 3.5 `B4` — The correlation id reaches every extraction record, and `video_id` names the video (OUT-003 / OUT-004 remainders, MEDIUM)

**Carries:** the **remainders** of `OUT-003` and `OUT-004`, adopted explicitly per `DV-3`. Their
cores merged into phase 01's `ENT-012`, which does **not** close them and minted no `REF-`
identifier. This block is an **ownership claim**, not a re-filing.

**Goal.** Two gaps survive on the current tree:

1. `services/extractor.py::ytdlp_extraction_error` carries **no `correlation_id`**, even though
   the operation bound one. Cause: the extraction call goes through `run_in_executor`, which runs
   the function on a worker thread that **does not inherit `contextvars`**. The bind never reaches
   the thread that emits the record.
2. `video_id` is **absent** from `extraction_error`, `ytdlp_extraction_error` and
   `download_finished` — the three records a caller would aggregate to answer "which video
   failed", while the sibling records carry it.

**Exact semantic scope.**

- `services/extractor.py` — the two extraction records; whatever thread-execution call the
  extraction path uses (`run_in_executor` or equivalent), located **by symbol**.
- The record emitting `download_finished` (the progress/observability surface) — add `video_id`
  where it can be read without a new parameter reaching it.
- The correlation-id contextvar's **bind/clear** helpers — the one-bind-per-operation and the
  `clear_correlation_id()` scoped to `unbind_contextvars("correlation_id")` are already correct and
  are **not** this block's subject.
- `tests/test_cli.py` and/or the extractor/observability test files — **new** assertions that the
  three records carry `video_id`, and that the extraction record carries a `correlation_id`.

**`D-5` — how the correlation id crosses the thread boundary. Not chosen here.**

- **Alt A (default): capture the context in the calling coroutine and apply it inside the
  worker.** Read the current `correlation_id` before dispatch and re-bind it as the first thing
  the worker function does. Uses only what the project already depends on (`structlog.contextvars`),
  is local to the extraction path, and does not touch `run_in_executor`'s contract.
- **Alt B: `contextvars.copy_context()` around the executor submission.** Correct by construction
  — it propagates *every* contextvar, not one — but it changes behaviour for any other contextvar
  a future call site relies on, and it is the kind of change whose blast radius is invisible until
  something else appears. Costs one import and is easy to over-apply.
- **Alt C: thread-local or explicit parameter pass-through.** Rejected: structlog's context is
  contextvar-based by design, and a parallel mechanism is a second source of truth for one id.

**Criterion.** Choose **A** if exactly one contextvar needs to cross and the extraction path is
the only executor submission in the codebase — **verify that count first**, because Alt A's cost is
proportional to it and Alt B's cost is not. Choose **B** if the measurement finds **more than one**
executor submission, or if `ENT-012`'s merged core implies other ids are already expected to cross
the same boundary. The measurement decides, and this Planner does not guess it.

**Acceptance criteria.**

1. Every record emitted on the extraction path carries the operation's `correlation_id`, and the
   id equals the one bound at the operation's start — asserted **through** the thread boundary,
   not by inspecting the bind call.
2. `extraction_error`, `ytdlp_extraction_error` and `download_finished` each carry `video_id`, and
   the value is the video's id for the operation that emitted the record.
3. One bind per operation and exactly one `clear_correlation_id()` per operation, still scoped to
   `unbind_contextvars("correlation_id")` — asserted, because the regression this block could
   introduce is a leaked id, which is worse than a missing one.
4. No record's **name** changed. These are aggregatable event names; renaming one silently breaks
   every log query. Any rename must be a separate, declared decision.
5. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** `ENT-012`'s merged correlation-id core — already done, not re-touched.
The `clear_correlation_id()` binding discipline. Any other record's field set.

**Agents.** **Auditor** (count the executor submissions in `src/` — this is `D-5`'s measurement and
it is the difference between Alt A and Alt B) · **Validator** (the assertion has to cross the
thread boundary; an assertion made in the calling coroutine proves nothing) · **Planner**
(`D-5`'s selection against the measured count). **Researcher not required** unless the count
exceeds one, in which case `contextvars.copy_context()`'s propagation semantics must be read
from the stdlib documentation rather than recalled.

**Commit:** `fix(observability): carry correlation id across extraction and add video_id`

### 3.6 `B5` — `--max-retries` is enforced by the model, in the command body (OUT-005, MEDIUM)

**Carries:** `OUT-005`. **Measured on arrival:** `--max-retries 0` exits **1** with a message that
misdirects the operator toward `.env`; `--max-retries abc` exits **2**. `Settings.max_retries`
already declares `ge=1, le=10`. The **option** declares no `min`/`max` — so the range exists in
exactly one of the two places that must agree, and the wrong one is the one the user reaches.

**Goal.** A value outside the range is currently reported as **exit `1`** with a message that
misdirects the operator toward `.env`. **Decision A (§1.0.1) classifies it as a configuration error:
it must exit `3`.** The reference also omits `--max-retries` from both commands' option tables
entirely.

**The mandatory test — retained, and now a statement of fact rather than a constraint on a choice.**
It was written while `D-6` was open, to stop an implementor from landing the wrong exit code. The
ruling makes it the block's specification:

> **An out-of-range `--max-retries` exits `3`, not `2`. A non-numeric `--max-retries` exits `2`.**
> Both sides are asserted, in the same test class, because the boundary is the ruling's.

**`R3b` is now a prohibition, not a risk.** No edit may reintroduce a parse-time range rejection on
this option — no `min=`, no `max=`, no `IntRange`, no callback that raises a parse-time error for a
value that is a number outside the range. See §5.

**Exact semantic scope.**

- `cli.py::download` and `cli.py::batch_download` — the `--max-retries` / `-r` declaration. **The
  option is left WITHOUT `min=`/`max=`.** No range literal is added to either command. **The two
  blocks stay byte-identical except this option's help string** (`C4`).
- **The enforcement point is the model, not the option.** `Settings.max_retries`'s `ge=1, le=10`
  already exist and are the single source; an out-of-range value reaches `Settings` through
  `_build_settings` and is rejected by **Pydantic validation inside the command body**.
- The command's `except ValidationError` clause — this is where the rejection surfaces, and where the
  status must become **`3`**. The message must name **the setting and its bounds**. **This is the same
  clause `B1` must not confuse with its own:** `B1` owns `_PreambleFailure`; if `ValidationError` must
  also yield `3` then **the two blocks edit one clause's neighbourhood** — see `CF-13`.
- `docs/99-reference/cli-reference.md` and `cli-reference-clean.md` — `--max-retries` gains a row in
  **both** commands' option tables, carrying its range and its environment source (`C5`). The exit
  table's **`3` row** names this case explicitly, alongside `B1`'s preamble case — **one commit or a
  reconciled sequence**, because both blocks write the same table.
- `tests/test_cli.py` — **new** assertions: out-of-range values exit **`3`** for **both** commands;
  a non-integer exits **`2`**; a valid value still works. No such oracle exists today (§2.6).

**`D-6` — CLOSED by the Tech Lead ruling. Retained as the decision record.**

- **RULING: `--max-retries` must NOT use Click's parse-time range rejection.** The range is declared
  **in the Pydantic model** — where `Settings.max_retries` already carries it — and enforced
  **inside the command body**, so an out-of-range value produces a configuration-error exit **`3`**
  with a message naming the setting and its bounds. **No `min=` and no `max=` is declared on the
  option.**
- **Why parse-time rejection is ruled out.** Click's `IntRange` rejects during **argument parsing**,
  which yields exit **`2`** — the usage-error code. That would make a configuration error
  indistinguishable from a typo on the command line, destroying exactly the distinction Decision A
  created when it reserved `3`. The ruling's whole purpose is that a script can tell *"your setup is
  wrong"* from *"you mistyped a flag"*; a parse-time rejection collapses the two.
- **Why non-numeric input stays `2`.** `--max-retries abc` is not an out-of-range value — the token is
  not a number at all, so it is a usage error by Decision A's own table. **This is the ruling's
  boundary, not a weakening of it**, and it is why the boundary must be tested **from both sides**:
  out-of-range asserts `3`, non-numeric asserts `2`, in the same test class.
- **Why the model, specifically.** Declaring the bounds **twice** — once in `min=`/`max=` and once in
  the model — **is the defect, not the fix.** With enforcement in one place, the option declaration,
  the help text, the validation and the error message cannot drift apart. The alternative this plan
  originally defaulted to was Alt A, and Alt A's own cost line already admitted "the range lives in
  two places and can drift"; the ruling removes the duplication rather than adding an assertion to
  police it.
- **`D-6` is CLOSED and must not be re-opened by an implementer.** The bounded assertion originally
  attached to it — *a declared range must equal the model's `ge`/`le`* — **does not apply**, because
  there is now **no declared range on the option**. Its replacement is the prohibition in `R3b`.

**The rejected alternative, by name, and what it would have cost.** `D-6` Alt A (and Alt C, which
inherited the same mechanism) proposed **`min=`/`max=` on both option declarations, mirroring
`Settings.max_retries`**. Adopting it would have cost:

| Cost | Detail |
|---|---|
| **The wrong exit code** | Every out-of-range value would exit `2`, the usage-error class — the opposite of Decision A. |
| **A destroyed distinction** | A script could no longer separate a bad setting from a bad flag, which is the entire reason `3` was reserved. |
| **A duplicated bound** | The range stated twice, free to drift; the help text could announce a range the model no longer enforces. |
| **A misleading help row** | `--help` would show Click's own range, implying the option validates itself, while enforcement actually happens later and elsewhere. |
| **A message naming the wrong layer** | Click's `IntRange` error describes a command-line token, not a setting whose value came from an option, a `VKDOWNLOADER_*` variable or a `.env` file — the three routes `_build_settings` supports. |

**The chosen option, and what it costs instead.** Enforcement in the body means the bound is not
visible in `--help`'s metavar. **That cost is accepted and is mitigated by documentation:** the
`--max-retries` row in both reference files carries the range, so the bound is stated where an
operator reads it, and `B1`'s `3` row names the code an operator's script should branch on.

**Acceptance criteria.**

1. An out-of-range `--max-retries` exits **`3`** for **both** commands; the ceiling-breaker is
   verified against `Settings.max_retries`'s `le`, **read from the model field**, not against this
   document.
2. The rejection message names **the setting and its bounds** — `max_retries` and `1..10` — and no
   longer points at `.env` as the thing to fix.
3. `--max-retries abc` exits **`2`** — Decision A keeps non-numeric input in the usage-error class.
   **Asserted in the same test class as criterion 1**, because the pair is the ruling's boundary and
   asserting only one side would let the other drift.
4. A value inside the range is accepted and **reaches `Settings`** — asserted, because the failure
   mode of a too-strict bound is a silently unusable option.
5. **Neither option declaration carries `min=` or `max=`**, and no parse-time range check exists on
   this option. This is the **prohibition** of `R3b` restated as an executable check.
6. The two option blocks differ only in `--max-retries`'s help string.
7. Both reference files carry the `--max-retries` row for both commands, **including the range** —
   this is the mitigation for the bound not appearing in `--help`'s metavar — **and** the `3` row
   names this case.
8. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** `Settings.max_retries`'s own bounds — they exist, they are correct, and they are now
the **enforcement point** · `format_validation_error`'s general behaviour, except as this block's
message requirement touches it · any other option's validation (`--quality` has its own callback and
its own decision, `OUT-017`'s territory, phase 03's) · **remapping Click's `UsageError` exit code**,
which would change `2` for every command · **and `min=`/`max=` on this option, which is prohibited.**

**Agents.** **Auditor** (enumerate the values that reach the `max_retries` field from every
source — option, `VKDOWNLOADER_*`, `.env`, default — so it is confirmed that the model's bound
governs **all four** routes, which is the whole point of enforcing there) · **Validator** (criterion 5
is a prohibition and must be checked by someone who did not write the fix: `grep` the declarations
for `min=`/`max=`; and the `3`-vs-`2` boundary must be checked against **the ruling's table**, not
against the block's own reasoning) · **Planner** (the `CF-13` clause neighbourhood). **Researcher
not required** — the ruling settles the mechanism, and `Settings.max_retries`'s bounds were verified
in this session.

**Commit:** `fix(cli): declare the max-retries range and document the option`

---

### 3.7 `B6` — A redirected run receives no terminal control sequences (OUT-006, MEDIUM)

**Carries:** `OUT-006`, plus a scope refinement this Planner measured in the installed library and
records as such.

**Goal.** Every redirected run — piped, redirected to a file, or CI — receives ANSI control
sequences in its stderr, because `setup_logging` builds `ConsoleRenderer()` with **no `colors=`
argument** and the installed structlog's default is `colors: bool = True`, and the sink is a bare
`StreamHandler()`, which resolves to `sys.stderr`.

**Measured refinement — the escape source is narrower than one lever suggests.** `structlog` 26.1.0
was read in this session. `ConsoleRenderer.__call__` pops `exception` and `exc_info` from the
event dict, then invokes `self._exception_formatter(sio, exc_info)` **only when `exc_info` is
still truthy**; when the `exception` key holds a pre-rendered string it writes that string
directly with no formatter. Because `format_exc_info` sits **before** `ConsoleRenderer` in this
chain, the traceback is always already a plain string by the time the renderer sees it. **The
default `exception_formatter=RichTracebackFormatter(color_system='truecolor', …)` is therefore
never invoked in this configuration**, and the escapes in a redirected run come from the
`colors=True` level and key styling alone. **One lever is sufficient: `colors=`.** This is stated
as a measured fact about the installed version and must be re-verified, not assumed, at execution
time.

**Exact semantic scope.**

- `config.py::setup_logging` — the `ConsoleRenderer()` construction gains an explicit `colors=`
  argument, and the argument's value is derived from a capability check on the sink's stream.
  The `JSONRenderer()` branch is untouched.
- `config.py::setup_logging`'s docstring — states the guarantee it now delivers.
- `tests/test_config.py` — **new** oracle: with a non-terminal sink, a rendered record contains
  **no** escape character; with a terminal sink it does. **The suite cannot do this through
  `CliRunner`** — see the verification requirement below.
- `docs/99-reference/*.md` — the sentence at the progress section that today reads *"When the
  output stream is not a terminal (piped, redirected, or CI) the display is never started and no
  escape codes are written"* is currently **false for the log stream** and is corrected in the
  same commit. Both files (`C5`).

**Verification requirement — the two-file harness.** There is **no stream-discipline oracle in
the suite** (§2.6): `CliRunner()` is module-level with merged streams, `mix_stderr` appears zero
times, `create=True` appears zero times, and no test asserts a stream is a terminal. `CliRunner`
therefore **cannot** verify this block. `B6` requires the external harness the phase-08 validator
used: `Start-Process -NoNewWindow -Wait -RedirectStandardOutput <out> -RedirectStandardError <err>`
against the installed console script, with and without `VKDOWNLOADER_LOG_LEVEL` raised so a
record is certainly emitted, then a byte scan of both files for escape sequences. The
in-suite test asserts the **renderer's configuration** (what `colors` was set to); the harness
asserts the **bytes**.

**`D-7` — how the capability check is made. Not chosen here.**

- **Alt A (default): `colors=sys.stderr.isatty()` at configuration time.** One call, evaluated in
  `setup_logging`, which runs inside the preamble after argument parsing — so a redirection
  performed by the shell or the test harness is already in effect. Simple and honest.
- **Alt B: consult the same predicate the progress display already uses.** `OUT-010` finds
  `RichProgressReporter.is_enabled` and `Console.is_terminal` disagreeing across six call sites.
  Reusing one of them here would couple the log renderer to the display's lifecycle — the
  renderer is configured once, the display is started and stopped per run. Rejected for now;
  recorded because `B10` changes the shape of that predicate and a later reader may think Alt B
  became available.
- **Alt C: decide per record rather than per configuration.** Rejected: structlog's `colors` is a
  renderer construction argument, not a per-call one, so this would require a custom renderer —
  a new abstraction, forbidden by §1.3 and rule 5.

**Criterion.** Choose **A**. The known weakness of A, stated rather than hidden: the decision is
made **once**, at configuration time, so a redirection that happens **after** `setup_logging` runs
is not seen. That case is real but belongs to the caller, not to the logging stack — and
`B6`'s alternative is to re-evaluate per record, which `C` rejects. If a caller that redirects
after the preamble is found in `src/`, `B6` **stops and reports** rather than widening the fix.

**Coupling with `B3` — declared, because it is not obvious.** `B6`'s single-lever sufficiency
depends on `format_exc_info` running **before** `ConsoleRenderer` and pre-rendering the traceback
into a plain string. `B3 = Alt A` preserves exactly that ordering. **If `B3` ever resolves to
Alt B** (`ProcessorFormatter`, which moves rendering into the handler), `B6`'s `colors=` lever
stops being sufficient and a second lever — the `exception_formatter` argument — becomes
required. `B6` must therefore verify `B3`'s outcome before declaring itself single-lever, and if
`B3` chose Alt B, `B6` adds the second lever in its own commit rather than assuming.

**Acceptance criteria.**

1. The two-file harness shows **zero** escape sequences in both redirected files, with a record
   certainly emitted.
2. The same harness against a real terminal (or a pty) shows escapes **present** — asserted, so
   the block cannot pass by disabling colour everywhere.
3. `colors=` is set explicitly on `ConsoleRenderer()`; the JSON branch is byte-unchanged.
4. The reference's progress-section sentence is now true and both files carry it.
5. An in-suite test asserts the renderer's `colors` value for both a terminal and a non-terminal
   sink — this is the substitute oracle `CliRunner` can support, and it is explicitly **not**
   claimed to prove the byte-level property.
6. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean. **No new test
   may skip on Windows.**

**Out of scope.** The rich progress display's own escape behaviour — that is `OUT-010`/`B10` and
`OUT-012`/`B12` · `NO_COLOR`/`FORCE_COLOR`/`TERM` handling, which is rich's and structlog's, and
which `OUT-010` already measured as affecting only rich's predicate and not the activity decision ·
the log **file** path, whose renderer is `JSONRenderer()` and already escape-free.

**Agents.** **Auditor** (re-verify the processor chain's order and the installed structlog's
`ConsoleRenderer` signature at execution time — the whole block rests on `colors` being the
lever, and on the exception formatter being bypassed) · **Validator** (the byte-level claim
cannot be checked by the Implementor in-process, and a `colors=False` that silently disabled
colour on terminals must be caught by someone who did not write the fix) · **Planner** (`D-7`,
and the `B3` coupling). **Researcher required only if the installed structlog's
`ConsoleRenderer.__call__` no longer bypasses the exception formatter** — in which case the
library's dispatch must be read from its documentation before the scope is finalised.

**Commit:** `fix(logging): suppress terminal control sequences when the sink is not a terminal`

### 3.8 `B7` — A dropped child line has a destination (OUT-007, MEDIUM)

**Carries:** `OUT-007`. **Sequenced strictly after plan 11 `B5`** — see the collision block below.

**Goal.** When the rich live display is active, `batch_downloader` sets
`echo = not reporter.is_enabled`, so `perform_download` reaches `_echo_ytdlp_line` with
`echo=False`. That branch handles a **progress** line by emitting one `ytdlp_progress_suppressed`
DEBUG record, and handles a **non-progress** line by returning **silently** — the child's errors,
its `[download] Destination:` line and any warning it printed are discarded with no record, no
count and no destination anywhere. An operator whose batch fails under a live display sees a
failed line and nothing that says why.

**Narrowing the collision — the conflict is smaller than plan 11 `B5` frames it.** Plan 11 `B5`'s
clause 3 pins **two** halves, and `OUT-007` breaks only the second:

| Half of plan 11 `B5`'s clause 3 | `OUT-007`'s position | Decision B | Conflict? |
|---|---|---|---|
| `echo=False` writes **nothing to stderr** | stays true — the live display owns stderr; writing there would interleave with the bars | **kept** | **no conflict** |
| `echo=False` on a non-progress line emits **no record** | the line must reach *some* destination, and a log record is one | **overturned** | **the only conflict, and it is now decided** |

So the fix that satisfies both is: **stderr stays empty; the line becomes a record.** The empty-stderr
assertion `B5` pins survives untouched. **What is overturned is `B5`'s "emits no record" clause**, and
that clause is wrong by rule 2 (production code is king — fix the test). **Decision B (§1.0.1) ratifies
exactly this outcome.** This block owns that test edit, after `B5` has landed.

**Exact semantic scope.**

- `services/ytdlp_downloader.py::_echo_ytdlp_line` — the `echo=False` non-progress branch.
- The event name for the dropped line, which is a **string literal at its call site**, consistent
  with every other record in the codebase — see `B13`'s "Correction to the finding's
  recommendation" for why this is *not* an enum member.
- `services/ytdlp_downloader.py::_echo_ytdlp_line`'s docstring — it currently states that
  non-progress lines are *"dropped silently"*; that sentence becomes false and is corrected here.
- `tests/test_hls_downloader.py::test_ytdlp_echo_false_non_progress_line_no_output_no_log` — the
  **one** of the four `echo=False` tests this block edits. Its name, its docstring and its
  assertion change together. The other three are green unchanged.
- The line carrying the child's own error text is in scope for redaction **only** insofar as plan
  11 `B6`'s transform covers exception-text records; `B7` writes raw child text into a record, so
  **`B7` must confirm whether plan 11 `B6`'s pipeline transform covers it** and, if it does not,
  say so in its commit rather than silently shipping unredacted child text.

**`D-8` — CLOSED by Decision B (§1.0.1). Retained as the decision record.**

- **RULING: one log record per dropped non-progress child line, carrying its text. `sys.stderr`
  receives nothing.**
- **What `D-8` was.** Alt A (default) emitted one record per line; Alt B routed dropped lines into the
  reporter's throttled progress channel, which bounds volume but threads a new dependency through a
  signature the yt-dlp transport owns; Alt C wrote to the stream the display repointed away from —
  rejected outright as worse than the silence the block exists to end.
- **Why Alt B is gone, stated so it cannot be re-opened on intuition.** Alt B is **batching**. The
  only thing that would justify it is a **measured** per-video count of non-progress child lines
  above a stated threshold. **No such measurement exists anywhere in the repository**, and the
  sibling progress branch already emits one record per line **without** throttling, so per-line
  records are the established pattern rather than a new cost. **Batching stays rejected until
  someone produces the measurement.** A future reader who believes batching is needed must produce
  that number first, not argue from taste.
- **`D-8` is closed and must not be re-opened by an implementer.**

**Collision — a declared slot, and the reason for the ordering.**

- **Plan 11 `B5`** rewrites `_echo_ytdlp_line` and its call sites, and pins clause 3 as live and
  non-weakened. **Plan 11 `B5` is the writer of record for that clause.**
- **`B7` is the second writer** and is the block that invalidates the "emits no record" half.
- **Ordering is strict: `B5` → `B7`.** If `B7` ran first, `B5` would pin a clause `B7` is about to
  break, and `B5`'s AC2 ("the existing case is not weakened") would be violated by `B7`'s edit.
- **`B7` may not weaken the empty-stderr half**, and it may not touch the other three `echo=False`
  tests. If plan 11 `B5` has not landed when `B7` is released, **`B7` waits** — it does not run in
  parallel and it does not pre-empt the clause.
- **`G0` precondition — RESOLVED (§2.11).** `tests/test_hls_downloader.py` is lint-clean and
  format-clean, verified per-file at `09f1b10`. `B7` is **no longer blocked**. The narrowed
  formatting-only fallback is **insurance only** and must not be exercised. If the whole-tree format
  check is red, it is a concurrent in-flight edit elsewhere: run the check scoped to this file and
  **report** the pre-existing red, naming the file — do not fix it, do not wait on it.

**Acceptance criteria.**

1. With the display active, a non-progress child line — **including an error line** — reaches a
   destination: exactly one record, carrying its text.
2. `sys.stderr` receives **nothing** for that line. Asserted separately from criterion 1, because
   this is the half plan 11 `B5` pinned and the half `B7` must not break.
3. The other three `echo=False` tests are green **unchanged** — progress-line suppression record,
   the empty-stderr case, and the progress DEBUG record's `downloaded`/`total`.
4. The edited test's name and docstring describe the new behaviour; a reviewer reading the test
   name alone cannot conclude that lines are still dropped.
5. `_echo_ytdlp_line`'s docstring no longer claims non-progress lines are "dropped silently".
6. Whether plan 11 `B6`'s transform covers the new record is **stated in the commit message**
   either way. If it does not, `B7` records the residual as unowned rather than shipping it
   silently.
7. Floors: 759+ passed, **3** skipped — the edited test must not start skipping; lint clean,
   **format clean** (`G0` cleared — §2.11), mypy clean.

**Out of scope.** The progress-line branch and its `ytdlp_progress_suppressed` record · the
`echo = not reporter.is_enabled` decision itself, which `OUT-010`/`B10` owns and which `B7` reads
but does not change · the `output_chunks` buffer, which must stay raw (plan 11 `B5`) · redaction
(plan 11 `B6`/`B5`).

**Agents.** **Auditor** (re-derive every `echo=False` producer and confirm the four tests' current
identities at execution time — this block edits exactly one of four, and misidentifying which is
the whole risk) · **Planner** (`D-8`, and the redaction-coverage question, which is a coverage
question about another block's scope) · **Validator** (the empty-stderr half is the constraint
`B5` pinned; only an independent check that stderr is still empty proves `B7` did not quietly
satisfy the finding by interleaving with the live display). **Researcher not required.**

**Commit:** `fix(downloader): record suppressed child output instead of dropping it`

---

### 3.9 `B8` — The summary names the quantity it reports (OUT-008, LOW)

**Carries:** `OUT-008`.

**Goal.** `_print_batch_summary` prints `Total connections: {len(results)}`, where `results` holds
one entry per **video**. The label names a unit the value does not have. Every sibling line in the
same account uses the video unit, and the concurrency tracker already says "videos" — so the one
line a reader would use to reconcile the URLs they supplied against the videos attempted is the
one line that cannot be reconciled. The supplied count is never stated anywhere.

**Exact semantic scope.**

- `services/batch_downloader.py::_print_batch_summary` — the summary label, and (only under
  `D-9 = B`) one additional line carrying the supplied count.
- `tests/test_cli.py` — **two** assertions break on a rename: the test that asserts
  `"Total connections:"` and the one that asserts `"Total connections: 2"`. Both change in this
  commit.
- `docs/99-reference/*.md` — the batch summary section, both files (`C5`).

**`D-9` — rename only, or rename and add the supplied count. Not chosen here.**

- **Alt A (default): rename the label to `Total videos:`** and change nothing else. One string,
  two test assertions, one or two doc lines. Closes the finding exactly as filed.
- **Alt B: rename the label and add the supplied count.** The count is available at the print site
  without a new parameter — the caller already receives the skipped count and holds the validated
  list, so *supplied = validated + skipped*. This is what actually closes the reconciliation gap
  the finding describes, and it is cheap. Cost: it adds a line to a user-facing account, which is a
  product-surface decision rather than a defect repair.
- **Alt C: rename to `Total items:`** — rejected: vaguer than the truth, and it would break
  agreement with the summary's other rows and with the concurrency tracker's existing wording.

**Criterion.** Choose **A** unless the owner wants the account to be self-reconciling, in which case
**B** — the measurement that decides it is whether the reference already documents a supplied-count
line for `batch`. If it does, `B` is a consistency fix rather than an addition and the default
should move to `B`.

**Acceptance criteria.**

1. The summary line's unit matches what the value holds, and matches the unit the rest of the
   account and the concurrency tracker already use.
2. Both affected `tests/test_cli.py` assertions are updated in the same commit; the count itself
   (`2`) is still asserted, so the test still pins the value and not only the label.
3. Both reference files describe the line with the new label.
4. Nothing else in the summary changes — the successful / failed / cancelled counts, the
   `Failed URLs:` block and the interruption note are untouched.
5. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** The accuracy of `Peak concurrent videos:` — the finding correctly assigns that
to phase 04, and this plan does not re-file it · `skipped_count`'s existing line and its label,
which are correct · the aggregation rule itself (`OUT-009` is `B9`'s).

**Agents.** **Auditor** (re-read the whole summary account and confirm `len(results)` is the video
count and that nothing else prints a `connections`-named quantity) · **Validator** (two pinned
assertions move; an independent check that the value is still pinned, not just the label, is the
whole content of this block's verification). **Planner not required unless `D-9 = B`**, which adds
a line and a decision about the account's shape.

**Commit:** `fix(batch): name the summary line for the quantity it reports`

### 3.10 `B9` — `ProgressStatus.SKIPPED` is either counted or documented as unreachable (OUT-009, LOW)

**Carries:** `OUT-009`.

**Goal.** `ProgressStatus.SKIPPED` is a live `StrEnum` member, rendered by `_StatusColumn.render`
(`[⊘]`, yellow) and by `_format_outcome` (`"skipped"`), and documented with a marker in
`cli-reference.md`. But `_print_batch_summary`'s aggregation names `SUCCESS` and `CANCELLED` in
explicit branches and derives `FAILED` **by subtraction**, so a fourth status could not appear in
the counts even if a producer existed — it would be reported as **failed**. No producer exists
today: the invalid-URL path never creates a `DownloadContext`, never enters `results`, and is
counted separately as `skipped_count` under its own label. The class is therefore dead **and**
unaccountable, and the reference tells a reader its marker is reachable.

**Exact semantic scope.**

- `services/batch_downloader.py::_print_batch_summary` — the aggregation. Under `D-10 = A`, a
  third explicit count is added and `failed` becomes a count rather than a remainder.
- `models/enums.py::ProgressStatus` — **unchanged.** The member stays under rule 10; this block
  deletes nothing (`C7`).
- `docs/99-reference/*.md` — the reference line documenting the `[⊘]` marker states whether the
  status is currently reachable. Both files (`C5`).
- `tests/test_cli.py` — the aggregation is asserted per class today; a new assertion pins that a
  `SKIPPED` entry, **if one were ever produced**, is counted as skipped and not as failed. This is
  a direct unit of the aggregation rule, not a manufactured reproduction.

**`D-10` — establish the class, or declare it unreachable. Not chosen here.**

- **Alt A (default): add `SKIPPED` as a third explicit count and make `failed` a count.** Three
  lines. The count is always `0` today, so this is forward-proofing — but it removes the **latent**
  defect the finding actually names, which is that the rule cannot represent any status it does not
  name. Pair it with the reference sentence from Alt C, because a reader still needs to know the
  marker is not yet produced.
- **Alt B: give the class a producer** — route the invalid-URL path into `results` as `SKIPPED`.
  Rejected: it changes what `results` holds, which changes `len(results)`, which is the value
  `B8` renames and the aggregation counts. That is a semantic change to the account's meaning, far
  beyond a LOW finding, and it would collide with `B8`.
- **Alt C: change no code; state in the reference that the marker is not currently reachable.**
  Closes the reader-facing half only. The subtraction rule stays able to misclassify a future
  status.

**Criterion.** Choose **A + C together** (which is what Alt A says): the code change removes the
latent misclassification for the cost of three lines, and the doc sentence removes the reader-facing
lie. Choose **C alone** if the owner considers an always-zero count to be speculative
state — defensible under rule 5, and the reason the reference half is not optional either way.

**Acceptance criteria.**

1. The aggregation rule names every `ProgressStatus` member that can reach it, or the reference
   states which cannot.
2. A `SKIPPED` entry in `results` is counted as skipped and is **not** counted as failed — asserted
   directly against the aggregation.
3. `ProgressStatus.SKIPPED` still exists; no member was deleted.
4. The reference's marker line states reachability, in both files.
5. The three existing per-class counts are byte-unchanged.
6. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** The invalid-URL path's separate `skipped_count` accounting, which is correct ·
creating a producer (Alt B) · `Total videos:` (`B8`) · `transient` behaviour in the display
(`B12`).

**Agents.** **Auditor** (re-derive every producer of every `ProgressStatus` and confirm none exists
— the finding's claim is that absence was *confirmed*, not assumed, and that confirmation must be
re-made) · **Validator** (an always-zero branch is exactly the kind of code an over-eager test
"proves" by asserting nothing) · **Planner** (`D-10`). **Researcher not required.**

**Commit:** `fix(batch): count the skipped status explicitly and state its reachability`

---

### 3.11 `B10` — One predicate decides whether the display is active (OUT-010, LOW)

**Carries:** `OUT-010`. **Six call sites; no oracle exists for the disagreement.**

**Goal.** `RichProgressReporter.is_enabled` returns `self._console.is_terminal` when a console
exists and `sys.stderr.isatty()` when it does not. `start()` decides **on `is_enabled`** at one
moment, then constructs the console, then reads `Console.is_terminal` **twice more** — once to
decide `_repoint_log_handlers()` and once for `auto_refresh`. Two predicates over one surface,
read at three moments, able to disagree. The measured disagreement runs in the harmless direction
(colour-forcing variables flip rich's predicate and not the activity decision), and the harmful
direction is `UNVERIFIED` because no real terminal exists on the declared platform.

**Six call sites, all of which observe a value that changes if the decision moves:**
`RichProgressReporter.start`, `start_task`, `set_title`, `update`, `finish_task`, and
`batch_downloader`'s `echo = not reporter.is_enabled` — the last of which is `OUT-007`'s subject
and therefore **`B7`'s dependency**.

**Exact semantic scope.**

- `services/progress_display.py::RichProgressReporter.is_enabled` — the property.
- `services/progress_display.py::RichProgressReporter.start` — the ordering of the decision
  relative to the console's construction.
- The `sys.stderr.isatty()` mirror and its explanatory comment, which under `D-11 = A` no longer
  exists.
- `tests/test_progress_display.py` — **new** assertion that both decisions (`is_enabled` and the
  repoint / `auto_refresh` reads) are taken from **one** predicate in one moment. There is **no
  such oracle today**: the two terminal-mode sites inject `force_terminal=True` on an in-memory
  stream and therefore bypass the detection under audit, and the two sites that replace the
  module's `sys.stderr` do not compare the two predicates.

**`D-11` — one predicate, without paying for an eager console. Not chosen here; this is the block's
real uncertainty.**

- **Alt A (default): keep the lazy construction and move the decision.** `start()` builds the
  console **first**, then reads `is_enabled` once; the property resolves to `console.is_terminal`
  whenever a console exists and falls back to `sys.stderr.isatty()` only before one does. The
  repoint and the `auto_refresh` decision then read the same value as the decision to start.
  The mirror comment becomes a statement of a real precondition rather than a duplication of
  another predicate. Preserves the current property that the reporter never binds a stream at
  import or construction time.
- **Alt B: resolve the console eagerly** at reporter construction and delegate `is_enabled` to
  `console.is_terminal` unconditionally, deleting the `sys.stderr.isatty()` fallback. Strictly
  simpler — one predicate, no mirror — but it binds the reporter to a stream at construction,
  which is the behaviour the existing lazy comment says is deliberate, and rich's guidance on
  `Console` construction cost and reuse is a **library question this Planner has not verified**.
- **Alt C: leave both predicates and add the missing oracle only.** Rejected as a resolution: it
  documents a defect without removing it. Recorded so it is not mistaken for a conservative option.

**Criterion.** Choose **A** unless the measured cost of constructing `Console(stderr=True)` is
negligible **and** rich's documented guidance does not object to per-reporter construction — in
which case **B** is genuinely simpler and the remaining difference is only whether a reporter
constructed before a redirection sees the redirected stream. **The deciding measurement is
`Console(stderr=True)`'s construction cost, and rich's own documented position on constructing
one; neither is answered in this file.** Note the direction of Alt B's risk: it would make `B6`'s
capability check and this block's predicate the *same* predicate, which is attractive and is not a
reason to choose it.

**Cross-block dependency, declared.** `B7` reads `is_enabled` through
`echo = not reporter.is_enabled`. If `B10` changes **when** the decision is taken, `B7`'s
suppression behaviour changes with it. **`B7` must re-read this property after `B10` lands**;
`B7` may not assume the current timing. `B6`'s `D-7` Alt B is likewise affected and is already
recorded as rejected for this reason.

**Acceptance criteria.**

1. `is_enabled`, the repoint decision and the `auto_refresh` decision are taken from **one**
   predicate at **one** moment. Asserted by a test that makes the two disagree under the old shape
   and requires the new shape to be consistent.
2. No real-terminal environment is substituted for a non-terminal one, and no test claims to have
   observed the harmful direction (`R-N`; the declared platform has no real terminal).
3. The two sites that inject `force_terminal=True` still pass unchanged — they pin the display's
   behaviour, not the detection.
4. The seven `assert "Traceback" not in result.output` sites in `tests/test_cli.py` are green
   unchanged — they are the downstream evidence that the log stream is still clean.
5. If `D-11 = B`, the existing comment claiming deliberate laziness is corrected in this commit.
6. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** The env-var layer rich consults (`FORCE_COLOR`, `TTY_COMPATIBLE`, `TERM`,
`NO_COLOR`) — measured as affecting rich's predicate only, and rich's business · the display's
escape behaviour (`B6`) · what happens to a task in flight at `stop()` (`B12`) · the dropped-child-line
destination (`B7`).

**Agents.** **Auditor** (re-count the six call sites and re-run the differential measurement —
one variable set at a time, both predicates read before and after `start()` — so the decision is
made against today's disagreement, not the report's) · **Researcher** (**required**: rich's
documented position on `Console` construction cost and reuse, which decides `D-11`) ·
**Planner** (`D-11`, and the `B7`/`B6` coupling) · **Validator** (the block's whole claim is that
two reads are one; only an independent check that no moment exists where they can differ proves it).

**Commit:** `fix(progress): decide display activity from a single predicate`

### 3.12 `B11` — `stop()` restores what it borrowed whatever the teardown does (OUT-011, LOW)

**Carries:** `OUT-011`. **Ordering defect; trigger `UNVERIFIED`, and no reproduction is
manufactured.** `stop()` runs `progress.stop()`, then `_restore_log_handlers()`, then four
unconditional `.clear()` calls, with **no `try`/`finally` anywhere in the method**. If the first
raises, the handlers stay bound to rich's `FileProxy` — which rich tears down **inside** `Live.stop()`
— and the process then writes structured log lines into a closed live render; because
`redirect_stderr=True`, the app's own output is mediated by a display that is no longer running.
If the second raises, the four maps leak for the process's lifetime.

**Exact semantic scope.**

- `services/progress_display.py::RichProgressReporter.stop` — the release of `self._progress` and
  the call to `_restore_log_handlers()`, plus the four `clear()` calls.
- `services/progress_display.py::RichProgressReporter.stop`'s docstring — it currently promises
  *"Safe to call without `start()` and idempotent"*, which says nothing about its post-conditions
  on a raising path. It states them after this change.
- `tests/test_progress_display.py` — a test that drives the raising case by substituting a
  `progress` whose `stop()` raises, and asserts the handler streams were restored and the four
  maps were cleared. **This is a synthetic substitute for the unverified trigger, and its
  docstring must say so** — it demonstrates the ordering, it does not claim a natural trigger.

**Shared-slot declaration.** `stop()` is written by **two blocks in this plan and one external
plan**: `B11` (the release ordering), `B12` (a terminal state for in-flight tasks, inserted into
the same method before the task map is cleared), and — not at present, but possibly later — nothing
else. `B11` and `B12` are the same risk tier, the same file, the same method, and have no external
dependency between them.

**Criterion for one commit or two.** If `B11` and `B12` are released in the **same** window, they
**may** land as one commit — same method, same tier, no ordering between them — and the commit
message names both findings. If anything separates them (an external landing, a separate
implementer), they are **two** commits and **`B12` re-reads `stop()` after `B11` lands.** They must
never be in flight from two agents at once. No other block in this plan touches `stop()`.

**Acceptance criteria.**

1. If `progress.stop()` raises, `_restore_log_handlers()` **still** runs and the four maps **still**
   clear. Asserted through the substitute.
2. If `_restore_log_handlers()` raises, the four maps **still** clear.
3. The happy path is byte-unchanged: after `stop()`, `sys.stderr` is the original object,
   `_saved_handler_streams` is empty, and the root handler count is unchanged.
4. `stop()` remains safe to call without `start()` and remains idempotent.
5. The docstring states the post-conditions the method now guarantees.
6. The substitute test's docstring states that the trigger is unverified and that the test drives a
   stand-in, not the product.
7. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** Whether `progress.stop()` **can** raise — the finding's recommendation is to
remove the dependency, and this block does not attempt to establish the trigger (`R-S`) ·
`_repoint_log_handlers()` (`B10`'s predicate, read but not changed) · `_log_message`'s throttling.

**Agents.** **Auditor** (confirm `stop()`'s callers and that no caller depends on the current
sequential ordering, so wrapping it in `finally` cannot change an observable sequence) ·
**Validator** (a `try`/`finally` that is correct in the source can still be wrong in the ordering —
an independent check of both raise paths is the entire content of this block). **Planner and
Researcher not required**; the recommendation is settled and no external behaviour is in question.

**Commit:** `fix(progress): release borrowed handlers unconditionally in stop`

---

### 3.13 `B12` — No line is left mid-flight on the terminal (OUT-012, LOW)

**Carries:** `OUT-012`. **`UNVERIFIED` through the binary — and the reachability argument was
verified rather than accepted.** All eight paths out of `_download_single` call `_finish(...)`
**before** returning or re-raising, including the cancellation path, so the only way `stop()` can
observe a task with no terminal status is a task cancelled before its first line runs — and such a
task never reaches `reporter.start_task`. `stop()` itself runs only in the `finally` of
`_run_batch_with_progress`, after `gather(..., return_exceptions=True)`. **The frame was observed
in-process; no live defect exists on the product today.**

**Goal.** The display is built with `transient=False`, so the last frame stays on the terminal.
`stop()` clears the task map without writing a terminal status for any task that had begun work,
and `_StatusColumn.render` returns `Text("")` while `task.fields["status"]` is `None`. A reader
sees a download at 10% with no marker and no outcome word, on a process that has already exited.
The guarantee that cannot happen rests on **eight call sites** rather than one — that is the
finding's actual content: a maintenance property, not a runtime defect.

**Exact semantic scope.**

- `services/progress_display.py::RichProgressReporter.stop` — before the task map is cleared, every
  task that is not yet terminal receives a terminal state. `CANCELLED` is the truthful one, since
  the batch is over.
- `services/progress_display.py::_StatusColumn.render` — **unchanged.** The fix is in the producer,
  not in the renderer that displays "no status".
- `services/progress_display.py::RichProgressReporter.stop`'s docstring — shares `stop()` with
  `B11`; see the shared-slot declaration there.
- `tests/test_progress_display.py` — a test that drives a started task, stops without finishing it,
  and asserts the frame left on the terminal carries a terminal marker. This is the frame the
  finding reproduces in-process, made executable.

**`D-12` — cancel, or report the truthful unknown.** A per-task status enum has no "abandoned"
member, and adding one would be a new `StrEnum` member with no producer (`B9`'s exact subject).
`CANCELLED` is the only truthful terminal state available at teardown. Chosen by elimination and
recorded here rather than carried as an open decision: the alternative is a new member nothing
produces, which rule 10 forbids.

**Acceptance criteria.**

1. After `stop()` with a task that had begun work, the surviving frame carries a terminal marker and
   an outcome word — asserted, not asserted-absent.
2. A task that **was** finished keeps the status it was given; `stop()` never overwrites a terminal
   status.
3. `stop()` with no tasks, and with tasks never started, is unchanged.
4. The happy path is byte-unchanged.
5. `stop()` remains idempotent and safe without `start()`.
6. The test's docstring states that the reachable-product claim is "no" and that this test pins the
   teardown's behaviour, not an observed product failure.
7. Floors: 759+ passed, 3 skipped, lint clean, format as at baseline, mypy clean.

**Out of scope.** The eight `_finish` call sites in `_download_single` — they are the reason the
defect is unreachable, and they are correct · `ProgressStatus.SKIPPED` (`B9`) · the `transient`
flag, which is what makes the surviving frame visible and is correct as-is · the display's escape
behaviour (`B6`).

**Agents.** **Auditor** (re-verify all eight paths out of `_download_single` call `_finish` before
returning **or re-raising** — this is the finding's reachability argument, and if one path does not,
the finding is not LOW) · **Validator** (criterion 2 is the regression this block could introduce:
overwriting a real terminal status with `CANCELLED` would corrupt every successful line, and only
an independent check of that case is worth having). **Planner and Researcher not required.**

**Commit:** `fix(progress): give an unfinished task a terminal status at teardown`

---

### 3.14 `B13` — The fallback's two failure classes stop sharing one event name (OUT-016, LOW, mandatory)

**Carries:** `OUT-016` — routed to phase 08 by phase 07, reclassified by validation from
`RUNTIME-ERROR` to `SPEC-DEVIATION`, severity re-derived to LOW. **The handler and its spans.**

**Goal.** The yt-dlp fallback's handler is `except (ExtractionError, OSError) as e:` and emits
`logger.warning("failed_to_refresh_token", url=..., error=str(e))` for **both**. The guarded span
reaches far past any token refresh: `output_file.unlink()` and the entire
`download_hls_with_resume(...)` call. Every `OSError` in that span — a file locked elsewhere, a
full volume, a path the platform refuses — is published to the caller under a token-refresh name,
so an operator is told to refresh authentication when the disk rejected a write.

**This block's importance is now SETTLED, not conditional.** The finding recorded that the fallback
is the **segment** path, which survives the retirement and therefore becomes more important. **The
Product Owner has now ruled that the segment path and the whole merge engine are permanent product
surface (§1.0).** So this is no longer "the fallback's path happens to survive": `B13` fixes the
**last diagnostic on the only merge path**, and that merge is permanent. The misnamed record is on
product surface that will not be retired, which is the strongest form the argument can take. A
future reader must not have to reconstruct that reasoning to justify the block.

**Exact semantic scope.**

- `services/ytdlp_downloader.py` — the handler's `except` clause, split into two, with a distinct
  event name for the filesystem class. Locate by the guard's span, not by a position.
- `tests/test_hls_downloader.py` — **new**: one test per branch, so the two cannot collapse again.
  No test in the repository mentions `failed_to_refresh_token` today (§2.6).
- The docstring of whatever function owns the handler.

**Correction to the finding's recommendation, recorded rather than followed.** The finding says the
new event name "is a `StrEnum` member in this codebase's own convention". **It is not.** Every log
event name in this codebase is a **string literal** at its call site — `ytdlp_progress_suppressed`,
`preamble_failed`, `merge_space_probe_failed`, `download_progress`. `ErrorCode` in `models/enums.py`
is a **domain-exception code**, not an event-name registry, and it is not what a structlog event name
resolves against. Adding an enum member for one event name would be a new abstraction no other
record uses, and rule 5 forbids it. **The new name is a string literal**, consistent with the other
eight-plus records.

**`D-13` — how far the split goes. Not chosen here.**

- **Alt A (default): split the handler into `except ExtractionError` and `except OSError`,** each
  with its own event name, both inside the same guarded span. One extra clause and one literal.
  Preserves the current control flow exactly.
- **Alt B: narrow the guarded span** so the unlink and the segment download are not inside a
  token-refresh handler at all. Cost: this restructures the fallback's exception flow, which is
  plan 10/11's and plan 12 `P12-B6`/`P12-B8`'s territory. Rejected here; recorded so it is not
  proposed twice. **Strengthened by §1.0**: the segment path is permanent, so "we will restructure it
  when the transport goes away" is no longer a reason to defer — it is a reason to do `Alt A` now
  and revisit `Alt B` only on its own merits.
- **Alt C: keep one handler and add a `cause=` field** to the existing record. Rejected: the event
  name is what an operator greps for and what a log aggregator groups by, which is the whole point
  `ErrorCode`'s docstring makes about this codebase's own vocabulary. A field does not fix a name.

**Criterion.** Choose **A** unless the owner wants the fallback's exception flow restructured, which
is a different plan's work.

**Collision — declared slot.** Plan 12 `P12-B6` and `P12-B8` both rewrite
`ffmpeg_utils._merge_segments_batched`'s deferral comment, and plan 12's verification list names
`ffmpeg_utils._merge_segments_batched`'s comment block as a deferral pointer that must be
discharged. **`B13` does not touch that comment** — its spans are `output_file.unlink()` and
`download_hls_with_resume`, in `ytdlp_downloader.py`, not in `ffmpeg_utils.py`. But both files are
in the same subsystem and `download_hls_with_resume` is **called from** the merge-adjacent code, so
`B13` must confirm at execution time that `P12-B6`/`P12-B8` have not already restructured the
fallback's span. **If they have, `B13` re-derives the guarded span by symbol and stops if it
cannot.**

**Acceptance criteria.**

1. An `ExtractionError` in the guarded span emits the token-refresh event; an `OSError` emits a
   filesystem-named event. **Two tests, one per branch** — the finding is that they cannot collapse
   again, and one test cannot prove that.
2. Neither event name is `failed_to_refresh_token` unless the cause is an `ExtractionError`.
3. Both records carry `url` (sanitised per the existing convention) and `error`.
4. The finding's measured consequence is **not** inflated in the commit message: the record surfaces
   in one `logger.warning`, **not** in the batch account's per-item line, because
   `_classify_download_result(None)` yields the literal `failed` and the account prints a status
   label. Asserted or explicitly noted as unasserted — whichever is true after `B13`'s change.
5. The commit message states that the fallback is the **segment** path and that the segment path is
   **permanent product surface** under the Product Owner decision (§1.0) — so a later reader knows
   this diagnostic is not awaiting a transport's retirement.
5. Floors: 759+ passed, **3** skipped — `B13` adds no permission assertion and must not convert or
   touch the remaining `D-11` oracle in this file; lint clean, **format clean** (**`G0` cleared —
   §2.11**; the narrowed co-edit is insurance only), mypy clean.

**Out of scope.** The fallback's own logic and the segment path's error taxonomy (phase 04's) ·
`ART-002`, the title-character defect on the same path, which shares the origin of the string but
not the label (phase 07's) · `SEC-007`, error text in log records (plan 11's) · the merge engine
(plan 12's).

**Agents.** **Auditor** (re-derive the guarded span by symbol at execution time and confirm it still
reaches the unlink and the segment download after `435ba0b`, which edited this file) ·
**Planner** (`D-13` and the naming convention correction above) · **Validator** (the finding is
that two causes share one name; only two independent tests prove they no longer do). **Researcher
not required.**

**Commit:** `fix(downloader): distinguish filesystem failures from token refresh failures`

### 3.15 `B14` — The pipeline records the tree it read, and refuses a dirty one (VAL-003, HIGH)

**Carries:** `VAL-003` (**open and recurring** — this plan is itself the second occurrence, see
below) and the recorded, **not worked around**, contradiction in plan 11 `B3`'s acceptance criteria
(Conflict-8).

**Goal.** The report format gives every phase exactly one provenance field — the commit it
measured — and the pipeline gives the executor and the validator **no other handle on what they
actually read**. Measured in this session: `audit-multi-phase.md` builds `{BASE_CONTEXT}` as a
*"summary of the above files"* and contains **no `git rev-parse HEAD` and no
`git status --porcelain`**. Both agents read the **working directory**. Nothing in
`.kilo/commands/audit/` checks for a dirty tree, records one, or refuses to run against one.

**Why it recurred, and this plan is the evidence.** During this plan's own baseline work, `HEAD`
moved twice (`d572d96` → `435ba0b` → `b0fb032`) and one gate went **red** from a commit that landed
between measurements (§2.8). A finding set validated against a tree that has since moved is exactly
the failure this finding describes; the incident is the reproduction, and this block's motivation
is that the same class of error has already cost one audit cycle a **withdrawn false finding** — a
first `VAL-003` alleging systematic per-file line-number drift in a report, which was wrong: the
offsets it reported were real, and their cause was the difference between the committed files and
the working-tree edits.

**Exact semantic scope.**

- `.kilo/commands/audit/audit-multi-phase.md` — the `{BASE_CONTEXT}` construction gains
  `git rev-parse HEAD` **and** `git status --porcelain`; the per-phase output gains a line recording
  both; a dirty tree becomes a **hard stop**, not a note.
- `.ai/audit/templates/audit-findings.md` — the single "commit measured" provenance line becomes a
  **block**: commit, working-tree state, and the paths if dirty.
- `.kilo/commands/audit/audit-refine.md` — the same treatment, so the refine path is not left with
  the defect the multi-phase path just fixed.

**`D-14` — how hard the dirty-tree stop is. Not chosen here.**

- **Alt A (default): hard stop.** The pipeline refuses to start a phase against a dirty tree. The
  finding's own words: *"a finding set is only useful if it can be re-verified against the tree it
  claims, and on this commit it cannot be, silently"* and *"the gate should be a hard stop rather
  than a note"*. Costs: an audit cannot be run mid-change, which is occasionally inconvenient and
  occasionally correct.
- **Alt B: record and continue** — the provenance block is written with the dirty paths listed, and
  the run proceeds. Cost: this is precisely what already happened; the report was then read against
  the wrong tree by a validator who concluded the report was wrong. A softer gate reproduces the
  failure it was added to stop.
- **Alt C: stop only for tracked modifications, ignoring untracked files.** Rejected: untracked
  `tmp/` scratch exists in this repository right now, and a gate that trips on it will be disabled.

**Criterion.** Choose **A**. Choose `C` only with an explicit ignore list, which converts Alt C
into Alt A with a configuration file — a new file under no versioned tree this plan may add, so it
is out of scope either way.

**Recorded conflict — plan 11 `B3`, Conflict-8. Recorded, not worked around.** Plan 11 `B3` is now
unblocked (`_temp_argfile` was deleted by `d572d96`, which is what AC6 was waiting for). Its six
acceptance criteria include **two that are unsatisfiable as written**, and one whose premise is
stale:

| Plan 11 `B3` criterion | Status at `b0fb032` | Why |
|---|---|---|
| **AC4** — *"a reviewer can name, from the commit message alone, which of the four oracles were converted, which were retired with their subject, and which remain POSIX-only"* | **unsatisfiable** | One of the four oracles, `test_temp_argfile_permissions_are_0600`, **was already deleted** with its subject in `d572d96` — a different commit. `B3` did not retire it and cannot name a disposition it did not perform. |
| **AC6** — *"`tests/test_hls_downloader.py` is one commit co-edited with the removal track's deletion of `_temp_argfile`"* | **unsatisfiable** | The deletion **has already happened**, in a commit that is already in history. A new commit cannot be "co-edited with" a commit that predates it. The precondition AC6 was designed to enforce has been satisfied by history rather than by a co-edit. |
| **AC1** — skip count *"strictly lower than 4"* | **premise stale** | The floor is **3**, not 4 (§2.4). The criterion remains satisfiable — converting the two `test_config.py` oracles reaches 1 — but its stated baseline is wrong. |

**This plan does not amend plan 11's block and does not re-file it.** The correction belongs to
plan 11's owner; `B14` records it because `B14` is the block that makes the pipeline's own records
trustworthy, and a criterion that cannot be satisfied is a record defect of the same class. **If
plan 11's `B3` lands against its criteria as written, this is the record of why they cannot all
hold.**

**Acceptance criteria.**

1. `audit-multi-phase.md`'s `{BASE_CONTEXT}` carries the resolved commit **and** the working-tree
   state; the per-phase output records both.
2. `.ai/audit/templates/audit-findings.md`'s provenance block names the commit, the clean/dirty
   state, and every dirty path when dirty.
3. A phase cannot start against a dirty tree without the refusal being visible — asserted by the
   document's own wording, which names the stop, not a note.
4. `audit-refine.md` is not left holding the defect `audit-multi-phase.md` just fixed.
5. The existing audit corpus is **not** re-run by this block. `B14` changes the instructions; it
   does not retro-fit the reports already produced. Any report whose provenance is now known to be
   a commit plus an unrecorded tree is re-verified on demand, not by default.
6. Conflict-8 is recorded in this plan's own verification table and in `B14`'s commit message.
7. Floors: the full suite is unaffected — `B14` touches **no** file under `src/`, `tests/` or
   `docs/`, so 759+ passed, 3 skipped, lint clean, format clean, mypy clean, and **both packaging
   frozensets unchanged at 73/32.**

**Out of scope.** Re-running or repairing any existing audit report · the withdrawn first
`VAL-003` (retained in the source file so it is not re-derived, and not re-filed) · `VAL-001` and
`VAL-002`, both fixed · any `.kilo/agent/` file.

**Agents.** **Auditor** (confirm the defect is still open at execution time — `audit-multi-phase.md`
gained `kilo.json` handling in a recent commit, so a concurrent fix is possible) · **Researcher**
(**required**: these are Kilo command documents whose `{BASE_CONTEXT}` placeholder substitution and
output-contract format must be read from the command definitions, not assumed from their prose) ·
**Planner** (`D-14` and the three-criterion table above) · **Validator** (a provenance gate is only
worth what a reader's ability to trust it is worth; an independent check must confirm the recorded
state is the state a reader would measure).

**Commit:** `fix(audit): record working-tree provenance and stop on a dirty tree`

---

### 3.16 `B15` — The two audit commands read files that resolve, and the census stops eating its own instructions (VAL-004 + VAL-005, MEDIUM)

**Carries:** `VAL-004` (**partial** — measured) and `VAL-005` (**partial** — measured).

**Measured status, re-derived in this session.**

- **VAL-004 is half-fixed.** `audit-multi-phase.md` now reads `.kilo/rules/project.md` and
  `.kilo/rules/commands.md` — corrected. **`audit-refine.md` still reads `AGENTS.md`**, which does
  not exist at the repository root. Exactly one command remains, which matches the brief. Neither
  file says what to do about an absent input; both should **report** it rather than continue
  silently. Neither names `kilo.json`, `kilo.local.json` or the phase report template, which both
  reference.
- **VAL-005 is open in substance, closed in form.** `audit-orphaned.md` *has* a "Protect and
  exclude from the removal candidates" section, but it is **category-based** ("Documentation",
  "Configuration and tooling"), not path-based. Nothing names `.ai/audit/**`,
  `.kilo/commands/audit/**`, `.kilo/agents/**`, any `**/.kilo/worktrees/**` directory, `.git/**`,
  `.venv/**`, build or cache directories, or the census's own output directory. A category-based
  guard is not a guard the executing agent can apply mechanically, and the finding's own argument —
  that a census which can propose deleting its own instructions is not a census of product code —
  stands.

**Exact semantic scope.**

- `.kilo/commands/audit/audit-refine.md` — the `AGENTS.md` line names the paths that exist, and the
  instruction says to report an absent file rather than continue. The missing references to
  `kilo.json` / `kilo.local.json` / the report template are added.
- `.kilo/commands/audit/audit-orphaned.md` — an explicit **path-based** exclusion list, added
  alongside (not replacing) the existing category guard. The census's own output directory is on
  it, for the same reason.

**`D-15` — where the exclusion list lives: in the command document, or in a new shared file.**

- **Alt A (default): in `audit-orphaned.md`, inline.** The census is the only consumer, the list is
  short, and a new shared file would itself be an unexcluded unreferenced file — the exact shape the
  finding is about. Self-referential irony avoided.
- **Alt B: a shared exclusion file read by every audit command.** Cost: a new file that the census
  must itself exempt, plus a loader every command needs. Strictly worse for a single consumer.

**Criterion.** Choose **A**. There is one consumer and the list is finite.

**Acceptance criteria.**

1. Neither audit command names a file that does not resolve. Verified by existence, not by reading.
2. Both commands say to **report** an absent input rather than continue silently.
3. `audit-refine.md` names the same rule files `audit-multi-phase.md` already names, so the two
   paths cannot drift again.
4. `audit-orphaned.md`'s exclusion list is **path-based** and names, at minimum: `.ai/audit/**`,
   `.kilo/commands/audit/**`, `.kilo/agents/**`, every `**/.kilo/worktrees/**` directory,
   `.git/**`, `.venv/**`, build and cache directories, and `.ai/audit/orphaned-files/` itself.
5. The existing category guard is retained, not replaced.
6. The stale-worktree corpus in `.kilo/worktrees/southern-bandana/` — a **different, superseded**
   phase generation with its own role roster the live `.kilo/agents/` does not match — is covered by
   the worktree exclusion. Its existence is recorded so a later run does not "discover" it again.
7. Floors: 759+ passed, 3 skipped, lint clean, format clean, mypy clean, both packaging frozensets
   **unchanged at 73/32** — `B15` adds no file under `src/`, `tests/` or `docs/`.

**Out of scope.** The stale worktree's **contents** — this block excludes it from the census and does
**not** delete it; removal is an owner's decision · `audit-multi-phase.md`'s already-corrected rule
references · the audit corpus itself.

**Agents.** **Auditor** (re-verify at execution time that `audit-refine.md` still names `AGENTS.md`
and that `audit-multi-phase.md` has not drifted back) · **Researcher** (**required**: Kilo command
documents' structure — what a command may reference, how `{...}` substitution works, and whether an
agent reads a directory listing as readily as a named file, which decides whether the instruction
should name two files or the directory) · **Validator** (the finding's sharpest sentence is that
the census would delete its own instructions; an independent check must confirm the list would in
fact stop that) · **Planner** (`D-15`).

**Commit:** `fix(audit): read files that resolve and exclude the census's own corpus`

### 3.17 `B16` — Stale ffmpeg claims in the code that survived the retirement (Live-2, LOW)

**Carries:** Live-2 — a defect in no store. **No finding ID exists for it**; it was found by
re-reading the surviving code against `d572d96`.

**Goal.** The retirement removed the transport but not every sentence describing it. **Under the
Product Owner decision (§1.0) this is a correctness obligation rather than a tidy-up**: ffmpeg is
not a loader transport at all, so every sentence presenting it as one is now false, and the
distinction between *loader* and *merger* is the distinction the whole product rests on. Measured in
the live tree:

| Site | Stale claim | Why it is now wrong |
|---|---|---|
| `services/batch_downloader.py` — **three** occurrences of the same docstring line on `method` | `method: Download method (yt-dlp, ffmpeg, or auto).` | It lists `ffmpeg` as a **download method** — a `DownloadMethod` member that is permanently deleted. The parameter's accepted values are `yt-dlp` and `auto` and nothing else. |
| `services/progress_display.py` — the unknown-total comment in the progress-reporting path | *"…the size is unknown (the ffmpeg path)"* | It attributes unknown totals to the **loader** path, which no longer exists. The unknown-total case belongs to the **segment** path, which is permanent. |

Both are **docstrings and comments in surviving code**, which is what makes them this plan's rather
than plan 10's: they are not in the eight-file documentation surface, and they are not in
`docs/STRUCT.md` (plan 12's). A reader of `batch_downloader` today is told a transport exists that
`d572d96` deleted **permanently**; a reader of the progress path is sent looking for a loader when
the cause is a permanent merger.

**Exact semantic scope.**

- `services/batch_downloader.py` — the three `method:` docstring lines. **Three occurrences of one
  string**, verified by symbol and by count: an implementation that fixes two and leaves the third
  has failed, and the count is the assertion.
- `services/progress_display.py` — the one unknown-total comment.
- No test is added. This is a comment fix; the correct number of new tests is zero, and adding one
  would be testing a string literal.

**`D-16` — what the unknown-total comment should now name. Still open; the decision supplies its
shape.**

- **Alt A (default): name the segment path.** The unknown-total case belongs to the segment/HLS path,
  because the ffmpeg **loader** is permanently gone and the transport that survives and reports
  unknown totals is the segment downloader. A reader can then find the code that actually produces
  the condition. **This is the shape the Product Owner decision supplies**: attributing an unknown
  total to a removed loader is wrong, and the segment path is the surviving cause.
- **Alt B: describe the condition without naming a transport** — "the size is unknown (no total
  reported by the producer)". Truest, loader/merger-agnostic, and immune to the next change. Cost: it
  gives a reader one more hop to find which producer.
- **Alt C: delete the parenthetical.** Rejected: the comment loses the only hint about when the
  condition holds.

**Criterion — unchanged and still governing.** Choose **A** if the segment path is the only remaining
producer of an unknown total, **measured first**: that one-line measurement is what decides Alt A
from Alt B, and this Planner has not made it. **The Product Owner decision does not answer that
measurement** — it establishes that the segment path is permanent, not that it is the *only*
producer. Choose **B** if more than one producer exists, since a comment naming one of several would
be a new stale claim. **What the decision does settle is the error class:** a comment attributing
unknown totals to a permanently-removed loader is wrong under every branch, so `Alt C` is excluded
and both survivors must name the segment path or no transport at all.

**Acceptance criteria.**

1. `grep` over `src/` finds **zero** occurrences of a `method:` docstring naming `ffmpeg` as a
   download method. The count of replacements is exactly **three**, and it is stated in the commit
   message.
2. The unknown-total comment names whatever `D-16` selected, and names something that exists.
3. No executable line changed. `git diff --stat` shows comment and docstring lines only.
4. **`check_ffmpeg_available` is permanent product surface** (§1.0). `B16`'s diff contains **no**
   reference to the symbol — not added, not removed, not reworded. The corrected group split (§4.4)
   puts it in the permanent merge group; this block neither confirms nor contests that, it simply
   does not touch it.
5. Floors: 759+ passed, 3 skipped, lint clean, **format clean**, mypy clean. `ruff` does not reflow
   docstrings, so this block is format-neutral by construction — which also means a format failure
   here is a pre-existing condition and is reported, not fixed.

**Out of scope.** The eight-file documentation surface (plan 10 `B10`'s) · `docs/STRUCT.md`'s
`ffmpeg_utils.py` description (plan 12 `P12-B12`'s) · `ffmpeg_utils.py`'s own module docstring, which
is **accurate** — the module is permanent product surface and still does what its name says ·
**`check_ffmpeg_available` and its `ffmpeg_not_found` hint string** (permanent per §1.0; the hint is
plan 16's boundary, `CF-12`) · `DownloadMethod`'s members (`d572d96` removed `FFMPEG` permanently;
`B17` covers the help text only).

**Agents.** **Auditor** (count the occurrences and enumerate **every** remaining ffmpeg mention in
`src/`, separating the ones that are correct — `ffmpeg_utils.py`, `extractor`'s cookie formatting,
`segment_downloader`'s merge import — from the stale ones, so the block neither over-fixes nor
under-fixes) · **Validator** (criterion 1 is a `grep`, which the Implementor can run; the Validator's
value is confirming that the *other* mentions were correctly left alone, which is the failure mode
of an over-broad comment sweep). **Planner required only if `D-16` resolves to Alt B**, which turns a
one-line fix into a decision about the comment's long-term shape.

**Commit:** `docs(services): remove stale ffmpeg claims from surviving code`

---

### 3.18 `B17` — `--method`'s own help says the value no longer exists (Live-3, LOW)

**Carries:** Live-3, **bounded**. The full eight-file surface is plan 10 `B10`'s obligation
(§1.4); this block may not touch it.

**Goal.** `--method ffmpeg` now exits **2** with Typer's invalid-choice error and no migration note,
while shipped documentation still describes a live transport. The parser's recovery message lists
only the accepted values and does not say that `ffmpeg` was **deliberately removed** rather than
mistyped — which is the whole distinction a user hitting this needs. Note this is the *same class*
of defect as the now-fixed `OUT-014` (`--cookie-source file` was documented and rejected): a value
the product once accepted, now rejected with no explanation. `OUT-014` was closed by the retirement's
doc pass; this is the residue that pass did not reach.

**The note's content is fixed by the Product Owner decision (§1.0), and the fix to this block's
predecessor is instructive.** A note reading *"ffmpeg is no longer used"* would now be **factually
wrong**: ffmpeg is used, as the segment merge engine, permanently. The note must carry the
**loader / merger distinction**, and every wording option below is checked against that requirement.

| Wording | Verdict | Why |
|---|---|---|
| **"The ffmpeg download method was removed. yt-dlp is the only download transport; ffmpeg is still required to merge downloaded segments."** | **SURVIVES — recommended** | Names what was removed (the **loader / method**), states what replaced it, and states what stayed **and why it matters** — an operator seeing this must not conclude their ffmpeg install is now optional. Matches `B16`'s loader-vs-merger framing exactly, so the two blocks cannot contradict each other. |
| **"The ffmpeg download method was removed; segment merging still uses ffmpeg."** | Survives, acceptable | Accurate and shorter. Weaker only in that it does not say the merge is *required*, which is the part an operator could act on wrongly. |
| **"ffmpeg is no longer used for downloads."** | **REJECTED** | True but invites the false inference that ffmpeg is now optional. Under §1.0 the merge is permanent product surface, so this wording is misleading by omission — worse than saying nothing. |
| **"ffmpeg support was removed."** | **REJECTED** | Unambiguously wrong. ffmpeg support is permanent; the *method* was removed. This is the specific error the Owner's decision exists to prevent. |
| **"`--method` accepts only `yt-dlp` and `auto`; `ffmpeg` was a method that never executed the transport anyway."** | Rejected as the *note*; retained as rationale | Factually the deepest truth (plan 10 `B10` found the method executed none of its transport), but it explains a long-obsolete defect instead of telling the user what to do. Belongs in a changelog, not in `--help`. |

**Recommended alternative, carried forward:** the first row. **`D-17` is nevertheless not closed by
this table** — the table fixes the *content class*; it does not choose the final sentence, which
belongs with the owner who also owns plan 10's documentation track. The block's default is the
recommended row; the criterion is that **no surviving wording may leave an operator believing ffmpeg
is no longer required.**

**Exact semantic scope — deliberately narrow.**

- `cli.py::download` and `cli.py::batch_download` — the `--method` option's **help text only**. It
  may name that `ffmpeg` was removed. **No option is added, removed, or re-typed** (`C4` preserved:
  the two blocks stay byte-identical except `--max-retries`'s help).
- `docs/99-reference/cli-reference.md` and `cli-reference-clean.md` — the `--method` row for both
  commands, and nothing else in either file (`C5`).
- **TestMethodFfmpegRemoved** — see the warning below. `B17` **may** add a sibling assertion that
  the help text **names** `ffmpeg`; it may not weaken, delete, or re-scope any of the three existing
  assertions.

**The three tests the retirement added, and why they cannot detect this defect.** All three assert
only `exit_code == 2` and a whole-`--help` substring. **Neither assertion distinguishes "the value
was rejected by the enum" from "the flag was removed entirely"** — both would still pass if
`--method` were deleted outright. So `B17` **cannot** be verified by the suite as it stands, and a
green `TestMethodFfmpegRemoved` after `B17` is **not** evidence that the migration note reached the
user. Strengthening those three is **recorded and not worked** (§1.4): it is a test-suite-quality
decision about another plan's block, and `B17`'s own new assertion is the narrow, honest witness.

**`D-17` — how the removal is communicated. Not chosen here.**

- **Alt A (default): one sentence in the `--method` help text** naming that the ffmpeg transport was
  removed, plus the `--method` row in both reference files. Reaches the user at the two moments they
  would ask: reading `--help`, and reading the reference after a `2`.
- **Alt B: a dedicated error message for the removed value.** Requires intercepting the enum's
  rejection — a callback on the option, which is a new mechanism on a surface where two commands must
  stay identical, for a value the parser already rejects correctly. Rejected: more machinery than
  the defect warrants, and the status is already right.
- **Alt C: a deprecation notice / tombstone member.** Rejected and explicitly forbidden: plan 10
  `B10` took the decision *"no deprecation shim, no feature flag, no tombstone enum member"*, and a
  tombstone would violate rule 10.

**Criterion.** Choose **A** — a sentence in the `--method` help text, carrying the recommended
wording above, plus the `--method` row in both reference files. `B17` exists because the
*explanation* is missing, not the rejection: the rejection is already correct and correctly
documented as exit `2`, and `DownloadMethod`'s members are permanently settled by §1.0. **The
criterion that decides the wording is §1.0's: no surviving sentence may leave an operator believing
ffmpeg is no longer required.**

**Acceptance criteria.**

1. `download --help` and `batch --help` name the removal in the `--method` help text, using the
   recommended wording or another that passes §1.0's criterion; the two help strings are identical
   to each other.
2. The `--method` row in **both** reference files states that the **value** no longer exists **and**
   that ffmpeg remains required for segment merging. Any other file that still describes `ffmpeg` as
   a live transport is **named in the commit message** and referred to plan 10 `B10` — `B17` does not
   fix it and does not pretend to.
3. `TestMethodFfmpegRemoved`'s three assertions remain **green and unweakened**. If any cannot be
   kept as written, `B17` **stops and reports** rather than adjusting them.
4. A new assertion exists that the help text names `ffmpeg`, so the note's presence is pinned — and
   its docstring states plainly that this, unlike `exit_code == 2`, distinguishes the note's presence
   from its absence.
5. `--method ffmpeg` still exits `2`. The status is not changed by this block.
6. No option was added, removed or re-typed; `DownloadMethod`'s members are unchanged.
7. Floors: 759+ passed, 3 skipped, lint clean, format clean, mypy clean, both packaging frozensets
   unchanged at 73/32.

**Out of scope.** The other six documentation files naming a live ffmpeg transport (plan 10 `B10`'s)
· `README.md` · `docs/STRUCT.md` · **`check_ffmpeg_available` and its `ffmpeg_not_found` hint**
(permanent per §1.0; the hint is plan 16's boundary, `CF-12`) · the parse-time rejection mechanism,
which is correct · strengthening `TestMethodFfmpegRemoved` (recorded, not worked).

**Out of scope — and deliberately.** `B17` does **not** add a segment-merge note anywhere else, and
does not warn about a missing ffmpeg binary. Under §1.0 the merge is required, so the honest
user-facing statement about a missing binary belongs to whoever owns that surface — plan 16, per
`CF-12`. Two plans must not both tell the operator about the same missing binary, and this plan has no
block whose scope reaches it.

**Agents.** **Auditor** (enumerate every file that still describes `ffmpeg` as a live transport, so
the commit message's referral list is complete and `B17` knows exactly what it is *not* fixing) ·
**Validator** (criterion 3 — three assertions that must stay unweakened — and criterion 4's honesty
about what the new assertion does and does not prove) · **Planner** (`D-17`). **Researcher not
required.**

**Commit:** `docs(cli): state that the ffmpeg method was removed`

---

## 4. Dependency graph and linearised order

### 4.1 The graph

**External nodes this plan does not own.**

| Node | What it is | Blocks that wait on it |
|---|---|---|
| `X1` | **plan 11 `B5`** — redaction at the terminal echo; pins the `echo=False` clauses | `B7` (strict) |
| `X2` | **plan 11 `B6`** — redaction processor in `setup_logging`, placed after `format_exc_info` | `B3` (required only if `D-4 = Alt B`) |
| `X3` | **plan 12 `P12-B11`** — `ART-007` in `setup_logging` (comment + posture) | `B3` (required only if `D-4 = Alt B`); `B2` must not touch the `SEC-003:` comment |
| `X4` | **plan 12 `P12-B6` / `P12-B8`** — merge sweeps and the `_merge_segments_batched` deferral comment | `B13` (span re-derivation) |
| `X5` | **plan 10 `B10`'s** eight-file documentation obligation | `B17` does **not** wait — it is bounded around it |
| `X6` | **`G0` — RESOLVED (§2.11).** `tests/test_hls_downloader.py` is lint- and format-clean at `09f1b10`. Retained only as insurance. | `B7`, `B13` — **no longer blocked**; both may report a whole-tree red from another agent's in-flight file |
| `X7` | **plan 12 `P12-B10` route (a)** — the block plan 12 called unconstrained | `B2` |

**Internal edges.**

```
B2 ──▶ B5 ──▶ B17 ──▶ B1            cli.py command bodies + both reference files
                                      (B5 and B1 both produce 3 — CF-13)
B3 ──▶ B6                          config.setup_logging
B8 ──▶ B9                          batch_downloader._print_batch_summary
B10 ──▶ (B11, B12) ──▶ B7          progress_display, then _echo_ytdlp_line
X1 ─┘
X6 ─┴──▶ B7
X6, X4 ──▶ B13
X2, X3 ──▶ (B3 if D-4 = Alt B)
X7 ═══▶ B2                         (mutual exclusion; one owner of the option blocks)
```

**Two edges are *not* dependencies and must not be treated as such.** `B3 → B6` is a **coupling,
not an order**: `B6` must read `B3`'s outcome before claiming one lever suffices, but either can land
first if the other re-verifies. And `B10 → B7` is a **re-read requirement**, not a hard edge — `B7`
must read the property after `B10` lands, but need not wait for it if it re-reads at execution time.

### 4.2 Linearised order, with the reason for each position

| # | Block | Why here |
|---|---|---|
| **1** | `B14` | Zero dependencies, zero external waits, zero file overlap with any product block. Safe to land first and it makes every subsequent block's provenance honest. |
| **2** | `B15` | Same. Touches only `.kilo/commands/audit/`, which nothing else in this plan touches. |
| **3** | `B2` | First of the `cli.py` chain, and the reason `B5` and `B1` follow it. It must land **before** any message edit — that is what keeps Live-1 from being reproduced by `B1`'s own fix. Also resolves the `X7` collision by claiming the option blocks before plan 12 uses its unconstrained route. |
| **4** | `B3` | Second of the `config.setup_logging` chain. Lands while `X2`/`X3` are still pending, which is fine **only** if `D-4 = Alt A`; `B3` must verify that at execution time and stop if it is not. |
| **5** | `B5` | After `B2`: both edit the same two option blocks, and `C4` requires them byte-identical except `--max-retries`'s help. Two agents in those blocks would produce a divergence `C4` forbids. Under Decision A this block is also the **first producer of `3`**, which fixes the shape of what `B1` must later write. |
| **6** | `B8` | First of the `_print_batch_summary` pair. Before `B9`, because `B9`'s rejected Alt B collided with `B8`'s `len(results)` label and `B9` needs to know what the line is called. |
| **7** | `B10` | First of the `progress_display` group. Before `B11`/`B12` (same file) and before `B7` (`B7` reads `is_enabled`). Also before `B6`'s decision `D-7`, whose Alt B was rejected partly for depending on this predicate. |
| **8** | `B16` | After `B10` only to avoid two agents in `progress_display.py` at once; the comment it fixes and the code `B10` changes are different regions, so this is a collision-avoidance position, not a dependency. |
| **9** | `B6` | After `B3` — `D-7`'s single-lever sufficiency is conditional on `B3`'s outcome, and `B6` must state which lever it used. |
| **10** | `B9` | After `B8`. |
| **11** | `B11` + `B12` | After `B10`. **One commit if released in the same window, two if separated** — the shared-slot criterion in §3.12. |
| **12** | `B13` | After `X6` (`G0`) and a re-derivation against `X4`. Independent of every product block above; it is here only because both `B7` and `B13` write `ytdlp_downloader.py` and **must not be in flight together**. |
| **13** | `B1` | **Last of the `cli.py` chain.** Decision A makes this block's reference edit the **largest in the plan**: it is not an appended row but a **re-partition** of `1`, `2` and a new `3` across both commands' tables, in both files. It lands last because **`B5` produces the `3` row's first entry** and because it must not have its prose re-written afterwards — Decision A also removes the `2` row's "nothing was attempted" rationale as `3`'s justification, so the two rows' prose becomes interdependent. `CF-13` holds `B5` and `B1` to a shared `3` row. |
| **14** | `B7` | **Last overall.** It has the longest external chain (`X1`, `X6`) and the only one that **must not run before another plan's block has landed**, plus it re-reads `B10`'s predicate. Decision B ratified its outcome but did not shorten its chain. |

**Parallel windows.** Positions 1–2 pair with 3–8 freely (distinct files). Positions 3/5/13,
4/9, 6/10, 7/11 and 12/14 are **strictly serial within their own group** and never concurrent with
each other member of that group. **`B17` joins the `cli.py` group at position 5.5**, between `B5` and
`B1`: it edits `--method`'s help text inside the same two option blocks (`C4`) and writes the same two
reference files, so it is serial with them.

### 4.3 Conflict matrix — declared slots, not acknowledgements

| # | Subject | Writers | Declared slot | Who resolves | Status |
|---|---|---|---|---|---|
| **CF-1** | `setup_logging`'s processor list | plan 11 `B6` (redaction processor, **immediately after `format_exc_info`** — adjacent lines) · plan 12 `P12-B11` (`ART-007`, comment + posture, above `basicConfig`) · **`B3`** (`D-4`'s `exc_info`-clearing processor) | Three writers, one function. **Order `B6` → `B3`.** `B3 = Alt A` may land first only if it places its entry at the **end** of the list. `B3 = Alt B` **must** wait for both. `B3` may not touch the `SEC-003:` comment. | **Open.** `B3` verifies at execution time; if `B6` has not landed it either defers or uses the end-of-list placement, and says which. | **Contended — `B6` and `P12-B11` both pending** |
| **CF-2** | `_echo_ytdlp_line` and the `echo=False` contract | plan 11 `B5` (writer of record; pins clause 3 live and non-weakened) · **`B7`** (breaks the "emits **no record**" half; leaves the "writes nothing to stderr" half intact) · plan 10 `B2`/`B6` (drain loop) | **Strict order `B5` → `B7`.** `B7` edits exactly **one** of the four `echo=False` tests and may not weaken the other three. Production code is king, so the "no record" clause is the wrong one. **Decision B ratifies this outcome** — one record per line, stderr clean. | **Resolved by Decision B + narrowing:** the conflict is one half of one clause, not the clause. `B7` owns the test edit, after `B5`. | **Ruled; `B5` still pending** |
| **CF-3** | The two commands' Typer option blocks | plan 12 `P12-B10` **route (a)** — *"the only block plan 12 called unconstrained"* · **`B2`** (`--log-level`) · **`B5`** (`--max-retries`) · **`B17`** (`--method`'s help text) | **This phase removes plan 12's unconstrained freedom.** `B2` is the owner of `--log-level`; `B5` of `--max-retries`; `B17` of `--method`'s help. `P12-B10` must either re-sequence behind `B2` or narrow route (a) to whatever it needs that is not one of those three. `C4` is the arbitration rule and it is not negotiable. **Decision C narrows `B2`'s claim to a single option**, so route (a) has even less room. | **Open — requires plan 12's owner to re-sequence or re-scope `P12-B10`.** Not resolved here. | **Open — `P12-B10` pending** |
| **CF-13** | The `except ValidationError` clause and the **`3` row of the exit table** | **`B5`** (out-of-range `--max-retries` must exit `3`) · **`B1`** (preamble failure must exit `3`, and it rewrites the whole table) | **Both blocks produce `3`; both write the same reference table and the same neighbourhood of `cli.py`'s exception clauses.** Slot: **`B5` before `B1`** on the existing chain, and the `3` row is written **once**, by whichever lands last, naming **both** producers. If they are released together they MAY share one commit — the same shared-slot logic as `B11`/`B12`. **Neither may rename the other's `3` case.** | **This plan** — sequencing; no external plan involved. | **New — internal slot declared** |
| **CF-4** | `_merge_segments_batched`'s deferral comment | plan 12 `P12-B6` · plan 12 `P12-B8` · (`OUT-016` was identified as "a third writer") | **`B13` is not a writer of that comment** — its spans are `output_file.unlink()` and `download_hls_with_resume`, in `ytdlp_downloader.py`. The third-writer concern is discharged by `B13` **re-deriving the guarded span by symbol** and stopping if it cannot. | **`B13`**, at execution time. | **Resolved in principle; re-verify required** |
| **CF-5** | `docs/STRUCT.md` | plan 12 `P12-B12` only | **Not re-filed. Not touched. Not cited as a fix target by any block here.** `B16` explicitly leaves `ffmpeg_utils.py`'s own docstring alone because it is accurate — the module still does what its name says. | — | **Closed — no re-filing** |
| **CF-6** | Plan 11 `B3`'s acceptance criteria | plan 11 `B3` (writer) · **`B14`** (recorder) | **Two of six unsatisfiable as written** (AC4's enumeration of four oracles, one already retired by `d572d96`; AC6's co-edit with a deletion already in history) and one stale (AC1's baseline of 4, actually 3). **Recorded, not worked around; not amended by this plan.** | **Plan 11's owner.** | **Recorded — see §3.15** |
| **CF-7** | `check_ffmpeg_available` | plan 10 `B10` (preserve, forbid deletion) · plan 11 §2.2 (calls it **group C**) · plan 12 §2.4.4 (calls it **group B**, retires it) · **`d572d96` preserved it** · **Product Owner (§1.0): it stays permanently** | **RESOLVED in favour of plan 10.** The symbol is permanent product surface. Plan 12 §2.4.4 is **wrong** on this symbol; plan 11 is right. `ffmpeg_utils.py` can never be deleted whole. No block in this plan touches the symbol. | **Product Owner — CLOSED.** | **CLOSED** |
| **CF-12** | The `ffmpeg_not_found` **hint string** inside `check_ffmpeg_available` | plan 16 (`P16-B8` / `P16-B9` own the binary's constraint and the `OSError` arms) · **this plan's `B13` writes the same file, a different function** | **Plan 16 owns the hint. This plan does not write it.** The string measured today is *"ffmpeg binary not found on PATH; downloads using ffmpeg or segment merge will fail"* — the first clause names a permanently-deleted `DownloadMethod` member, and the second **understates** a merge that is now **required**. Named as the boundary so exactly one plan edits it. | **Plan 16.** | **Recorded, not duplicated** |
| **CF-8** | The eight-file `--method ffmpeg` surface | plan 10 `B10` (obligation) · **`B17`** (bounded: `--method`'s own help + the two `--method` reference rows) | `B17` may not touch the other six files. It names them in its commit message and refers them to plan 10. | **Plan 10's owner.** | **Bounded and declared** |
| **CF-9** | `tests/test_hls_downloader.py` | plan 11 `B2`/`B3`/`B5` · plan 10 · **`B7`**, **`B13`** | `B7` and `B13` **must not be in flight together** (positions 12 and 14). `B7` edits one of the four `echo=False` tests; `B13` adds two new ones for a different subject. `G0` is **resolved**, so neither is blocked by the file's formatting (§2.11). | **Sequencing — this plan.** | **Sequenced; `G0` resolved** |
| **CF-10** | `OUT-002` ↔ `OUT-006` decision coupling | `B3` (`D-4`) · `B6` (`D-7`) | `B6`'s single-lever sufficiency depends on `format_exc_info` running before `ConsoleRenderer` and pre-rendering the traceback into a plain string, which the installed structlog's `ConsoleRenderer.__call__` confirms. **`D-4 = Alt B` breaks that assumption** and makes a second lever (`exception_formatter`) required. Declared so `B6` is not shipped on a stale premise. | **`B6`**, by reading `B3`'s outcome. | **Coupled, not conflicting** |
| **CF-11** | `TestMethodFfmpegRemoved`'s three assertions | `d572d96` (author) · **`B17`** | `B17` may **add** a sibling assertion; it may not weaken, delete or re-scope the three. If any cannot be kept as written, `B17` **stops and reports**. Strengthening them is recorded and not worked. | **The retirement's owner.** | **Recorded, not worked** |

### 4.4 RESOLVED: `check_ffmpeg_available` stays, and the group split is corrected

**This section was an open decision with a criterion. It is now closed by the Product Owner (§1.0).
The decision and its rationale are retained so a later reader does not re-derive them.**

### 4.4.1 The decision

**`check_ffmpeg_available` stays. Permanently. As product surface.** `services/ffmpeg_utils.py` is
permanent product code and **can never be deleted whole**. The three-way conflict is resolved **in
favour of plan 10's position** (preserve, do not delete).

| Authority | Said | Verdict |
|---|---|---|
| **Product Owner (§1.0)** | ffmpeg is not a loader transport; the segment merge engine and its availability probe **stay permanently** | **BINDING — this is the decision** |
| plan 10 `B10` | Preserve the symbol; explicitly forbid deletion | **UPHELD** |
| plan 11 §2.2 | Calls it **group C** — "needed by the segment merge" | **accidentally right, for the wrong reason** |
| plan 12 §2.4.4 | Calls it **group B** — "retires with the transport" | **WRONG** |
| `d572d96` (fact) | Preserved the symbol; it is re-exported by `services/downloader.py` and called from `download_video` | consistent with the decision |

**Two supporting facts measured in this session**, recorded as evidence rather than as a separate
argument: the symbol has a **live test class** — `tests/test_hls_downloader.py`'s
**`TestFfmpegAvailabilityCheck`**, two tests, one asserting the return type is a `bool` and one
asserting the result is cached across calls — and the symbol is the **only** thing that probes the
binary's presence at all, which is exactly what a permanent required merge needs.

### 4.4.2 The corrected group split — plan-of-record, final

**Plan 11 §2.2 gets `check_ffmpeg_available` and `_merge_batch_segments` / `_perform_final_merge`
both wrong, and the second is the dangerous one.** The corrected split:

| Group | Members | Fate |
|---|---|---|
| **(A) generic subprocess infra, shared with yt-dlp** — **SURVIVES** | `iter_process_lines`, `cancel_subprocess`, `cancel_ffmpeg_process` | `ytdlp_downloader` imports the first two **directly and unconditionally** for the child's stdout draining and cancellation. Deleting them takes the yt-dlp transport down. |
| **(B) transport support** — **GONE** | `FfmpegProgress`, `_PROGRESS_KEY_HANDLERS`, `ProgressParser`, `read_progress` — **already deleted** by `d572d96`, plus `DownloadMethod.FFMPEG`, `HLSDownloader`, `download_with_ffmpeg`, `_temp_argfile`, `_format_argfile` | Deleted permanently with the loader transport (§1.0). No restoration, no second pass. |
| **(C) segment merge engine** — **PERMANENT PRODUCT SURFACE, still spawns ffmpeg** | `_merge_batch_segments`, `_perform_final_merge`, `_merge_segments_batched`, `_build_ffmpeg_concat_command`, `_required_merge_bytes`, `_check_merge_space`, `_await_ffmpeg_with_timeout`, `_MERGE_SPACE_MARGIN_BYTES`, **and `check_ffmpeg_available`** | The segment path has no other merge. **Group C is permanent** and requires the binary. **`shutil` must survive** — `_check_merge_space` calls `shutil.disk_usage` and `check_ffmpeg_available` calls `shutil.which`. |

**Two errors this corrects, stated so they are not re-introduced:**

1. **Plan 11 §2.2 files `_merge_batch_segments` and `_perform_final_merge` as group B — "dies with
   the transport".** They are group C and **permanent**. Evidence: `tests/test_ffmpeg_utils.py` —
   834 lines, 32 tests — **survived `d572d96` entirely**, and every one of those tests covers group C.
   A module whose entire test file passes unchanged is not a module whose merge engine was scheduled
   for deletion.
2. **Plan 12 §2.4.4 places `check_ffmpeg_available` in group B.** Wrong. It is group C's availability
   probe and it stays.

### 4.4.3 Consequences for this plan, now binding

| Consequence | Where it lands |
|---|---|
| **No block touches `check_ffmpeg_available`** — not deleted, moved, renamed, redefined or re-ordered. | §1.3, `B16` criterion 4, `B17` out-of-scope |
| **No block touches the `ffmpeg_not_found` hint string.** Plan 16 owns it (`CF-12`). | §1.0, §1.4, `CF-12` |
| **`B17`'s note must carry the loader / merger distinction.** Wording table with rejected forms in §3.18. | `B17` |
| **`B13` is the last diagnostic on a permanent path** — its importance is settled, not conditional. | §3.14 |
| **`B16`'s `method:` docstrings and the unknown-total comment are correctness obligations**, because they name a permanently-removed loader. | §3.17 |
| **`B16` does not add or remove the symbol**, which was previously a neutrality rule under an open decision and is now a positive rule under a closed one. | §3.17 criterion 4 |
| **`DownloadMethod`'s members are settled.** No tombstone, no restoration, no second removal pass. | `B17` |

### 4.5 Consolidated decision register — the checkable count

**Every `D-*` this plan carries, and its state.** This table exists so the open count can be verified
in one place rather than reconstructed from seventeen block bodies. **Open: 12. Closed: 5.**

| `D` | Subject | Block | State | Default / ruling |
|---|---|---|---|---|
| `D-1` | Preamble-failure exit code | `B1` | **CLOSED** | **`3`** — Decision A |
| `D-2` | How many log options | `B2` | **CLOSED** | **`--log-level` only** — Decision C |
| `D-3` | Routing the new option into `Settings` | `B2` | **OPEN** | `_SettingsOverrides` → `_build_settings` |
| `D-4` | Suppressing the second exception render | `B3` | **OPEN** | clear `exc_info` on the `LogRecord` |
| `D-5` | Correlation id across `run_in_executor` | `B4` | **OPEN** | capture-and-rebind |
| `D-6` | `--max-retries` range enforcement | `B5` | **CLOSED** | **model-enforced; no `min=`/`max=`** — Tech Lead ruling |
| `D-7` | Capability check for the renderer | `B6` | **OPEN** | `sys.stderr.isatty()` at configuration |
| `D-8` | Destination for a dropped child line | `B7` | **CLOSED** | **one record per line, stderr clean** — Decision B |
| `D-9` | Batch-summary rename scope | `B8` | **OPEN** | rename only |
| `D-10` | Establish `ProgressStatus.SKIPPED` | `B9` | **OPEN** | explicit count **and** the reachability sentence |
| `D-11` | One TTY predicate, with or without an eager console | `B10` | **OPEN** | keep the lazy construction |
| `D-12` | Terminal state for an in-flight task | `B12` | **settled by elimination** | `CANCELLED` — the only truthful option; recorded, not carried |
| `D-13` | How far the handler split goes | `B13` | **OPEN** | split the clause |
| `D-14` | How hard the dirty-tree gate is | `B14` | **OPEN** | hard stop |
| `D-15` | Where the exclusion list lives | `B15` | **OPEN** | inline in `audit-orphaned.md` |
| `D-16` | The unknown-total comment's wording | `B16` | **OPEN** | name the segment path — criterion unchanged |
| `D-17` | How the removal is communicated | `B17` | **OPEN** | one help sentence carrying loader/merger |

**Rules for this table.** A closed `D` may not be re-opened by an implementor; objections are
recorded against the block's decision record. An open `D` must be recorded as **chosen**, with the
criterion that chose it, before its block is called done. **`D-6` is not in the open set**, and no
section of this plan describes it as awaiting a decision.

---

## 5. Risks

### 5.1 Implementation risk

| ID | Risk | Blocks | Containment |
|---|---|---|---|
| **R1** | **A three-writer function is edited by two agents at once.** `setup_logging` has plan 11 `B6`, plan 12 `P12-B11` and `B3` writing it. A textually clean merge can still produce a *semantically* wrong processor order. | `B3` | CF-1's slot. `B3` re-reads the whole chain by symbol before and after, and states in its commit message which writer preceded it. `D-4 = Alt A` places the new entry **after** `format_exc_info` and **before** `UnicodeDecoder` — a position a later insertion above it cannot merge-conflict with. |
| **R2** | **`C4` is silently violated.** The two commands' option blocks must stay byte-identical except `--max-retries`'s help. A block that adds `--log-level` to `download` and forgets `batch` compiles, passes, and ships an inconsistent surface. | `B2`, `B5` | Acceptance criterion in both blocks, verified by reading both declarations rather than by diffing a captured `--help` — a captured help cannot show a byte difference the eye skips. |
| **R3** | **The plan's own fix reproduces Live-1.** `B1` edits `_render_preamble_failure`'s message; that message names `--log-file`, which does not exist. **Decision C changed the fix, not the hazard:** `B2` no longer adds the flag, so the message must be *corrected* rather than *justified*. | `B1`, `B2` | `B2` is position 3, `B1` is position 13, and `B1`'s criterion 6 keeps the message untouchable unless `B2` landed. **Added:** `B2`'s acceptance criterion 4 now asserts that **every option-looking token in the hint resolves against the captured `--help`** — that assertion is the direct structural fix for Live-1, and it holds whichever way the wording goes. |
| **R3b** | **PROHIBITION — no edit may reintroduce a parse-time range rejection on `--max-retries`.** **This is not a risk; it is a rule.** Converted from the open-risk form it held while `D-6` was live. **Prohibited, in every form:** `min=` or `max=` on either option declaration; `IntRange`; a `callback=` that raises a parse-time error for a value that *is* a number outside the range; or any equivalent that rejects before the command body runs. **Why, in one line:** a parse-time rejection exits `2`, which is the usage-error class, and would make a configuration error indistinguishable from a mistyped flag — destroying the distinction Decision A created when it reserved `3`. **Verified by** `B5`'s acceptance criterion 5 (executable) and by `B5`'s Validator, whose first job is to `grep` both declarations for `min=`/`max=`. **The model is the single source of the bound**; declaring it twice is the defect, not the fix. |
| **R3c** | **`3` is a new public code and `1`'s meaning narrows.** Decision A re-partitions three rows rather than appending one. A reference table that keeps `1`'s old "configuration error" wording, or that justifies `3` with `2`'s "nothing was attempted" rationale, documents a contract that does not exist. | `B1`, `B5` | `B1`'s criteria 4 and 5: the `1` row must no longer list "configuration error", and `3`'s prose must distinguish "your setup is wrong" from `1`'s "the command ran and failed" **without borrowing `2`'s rationale**. `CF-13` holds the shared `3` row to one writer. |
| **R4** | **`D-4 = Alt B` invalidates `B6`'s premise.** `ProcessorFormatter` moves rendering into the handler, at which point `format_exc_info` no longer pre-renders the traceback and the default `RichTracebackFormatter(color_system='truecolor')` becomes reachable — re-introducing escapes that `colors=False` cannot suppress. | `B3`, `B6` | CF-10. `B6` must read `B3`'s outcome and add the second lever if `Alt B` was chosen. Declared, not discovered. |
| **R5| | **A fix that passes by disabling the feature.** `B6`'s `colors=False` and `B10`'s single predicate can each be made green by turning colour or the display off unconditionally. | `B6`, `B10` | Both carry an explicit **positive** criterion: escapes **present** on a terminal, display **starts** when the predicate is true. Neither may pass by suppression. |
| **R6** | **`B11`/`B12` both rewrite `stop()`.** | `B11`, `B12` | The shared-slot criterion in §3.12: one commit if released together, two if separated, `B12` re-reading after `B11`, never concurrent. |
| **R7** | ~~**A duplicated bound drifts.**~~ **RESOLVED BY THE `D-6` RULING.** This risk existed because the plan's default put `ge=1, le=10` on the option *and* in `Settings.max_retries`. The ruling enforces the bound **in the model only** and prohibits the option-level declaration outright (`R3b`), so there is no second copy and nothing to drift. **Retained as a record**, because the failure it described is exactly what the ruling's "declaring the bounds twice is the defect, not the fix" clause forbids. | `B5` | `R3b`'s prohibition plus `B5`'s acceptance criterion 5. The mitigation is *removal*, not an assertion. |
| **R8** | **Over-broad comment sweep.** `B16` sits in a codebase where `ffmpeg` legitimately appears ~65 times, most of them correct. | `B16` | Acceptance criterion 1 names an exact count (**three**) and criterion 4 forbids touching `check_ffmpeg_available`. The Auditor enumerates *all* remaining mentions and classifies them. |
| **R8b** | **A "finish the ffmpeg cleanup" reading of §1.0 would delete permanent product surface.** The decision names **nine** symbols that **stay**. A block that reads the retirement as a licence to complete the job would take out group C — and two audits already placed the merge engine in the retiring group. | `B16`, `B17` | §4.4.2 lists all nine by symbol with the corrected split; §1.3 removes `check_ffmpeg_available`'s disposition from scope entirely; `B16` and `B17` name the nine-symbol list in their out-of-scope clauses. |

### 5.2 Rollout risk

| ID | Risk | Containment |
|---|---|---|
| **R9** | **The baseline moves under the plan.** Demonstrated **four times**, not hypothetical: `HEAD` moved `d572d96` → `435ba0b` → `b0fb032` → `58bb7ce` → `09f1b10` during this plan's preparation, the pass count rose 747 → 749 → 752 → 759, a gate went **red** from a commit that landed between measurements, a **second** gate went red from an uncommitted in-flight edit, and `DV-2` recurred as a transient dirty state three times (§2.8 – §2.11). | Every block re-runs all five gates and reports against **759 passed / 3 skipped**; a block whose measured baseline differs **stops and reports** rather than proceeding against a floor it has not verified. §2.8 through §2.11 are the model, all four written before the blocks were. |
| **R10** | ~~**`G0` is never cleared.**~~ **RESOLVED (§2.11).** The formatting defect that `b0fb032` committed into `tests/test_hls_downloader.py` survived three audits' worth of gate runs and is now fixed upstream; `B7` and `B13` are unblocked. **Retained as a record** of the one precondition that actually bit in this plan's history. | The narrowed co-edit is **insurance only** and must not be exercised. The live residual is `R9`/`R10b`: a whole-tree gate can be red for another agent's in-flight file, which `§7.1`'s "report, do not fix" rule and the scoped per-file check now cover. |
| **R10b** | **A whole-tree gate goes red for another agent's uncommitted work.** At `09f1b10` both `ruff` gates were red solely because `src/vkdownloader/services/ffmpeg_utils.py` is modified in the working tree (`+6 / −2`, mid-edit by a concurrent agent: unsorted imports, `I001`). `B7` and `B13` do not touch that file; `B16` does not either. | A block whose own files are clean runs its gate **scoped to those files** and **reports** any pre-existing whole-tree red in its commit message, naming the file — §7.1's existing rule. **No block fixes another plan's in-flight diff, and none waits on it:** blocking on an uncommitted change would make this plan a hostage to someone else's working state. If the concurrent edit commits unfixed, the red becomes a committed defect in **group C, permanent product surface** (§4.4.2) and belongs to plan 12 or plan 10, not here. |
| **R11** | **Commit contamination from a dirty tree.** `DV-2` was resolved at `b0fb032`, recurred at least three times, and **recururred again** at `09f1b10`. `src/vkdownloader/services/ffmpeg_utils.py` is now dirty alongside `.ai/problems/PROBLEM.md`, `.kilo/commands/implement/implement-plan-multiagent.md`, seven tracked `.ai/plans/` deletions and untracked `tmp/`. | `C10`'s scoped `git status --porcelain -- src tests docs pyproject.toml` before every commit. That scope is chosen **because** it excludes the known-dirty non-product paths **and** because it lets a block distinguish its own diff from a concurrent agent's. **Never** `git add -A`. |
| **R12** | **Two plans both "own" the option blocks** (CF-3), and plan 12 was told route (a) was unconstrained. | `B2` claims the blocks first by landing at position 3. Plan 12's `P12-B10` must re-sequence or re-scope; if it has not, `B2`'s pre-commit check will show `cli.py` modified by someone else and `B2` **waits**. |

### 5.3 Regression risk

| ID | Risk | Containment |
|---|---|---|
| **R13** | **Weakening a pinned clause while fixing the finding.** `B7` must break the "emits **no record**" half of a clause plan 11 `B5` pinned as non-weakened; `B17` must not weaken any of `TestMethodFfmpegRemoved`'s three assertions; `B12` must not overwrite a real terminal status with `CANCELLED`. | Each is an explicit acceptance criterion naming the clause, and each has a **positive** counterpart (`B7`: stderr still empty; `B12`: a finished task keeps its status). A Validator checks the counterpart, because a fix that satisfies the finding by breaking the pin is the expected failure mode here. |
| **R14** | **The 31-test oracle deficit from the retirement hides a regression in a block's own area.** The retirement killed 34 oracles and added 3. | §2.6 records the count and the fact that all three additions assert only `exit_code == 2` and a whole-`--help` substring. **A green suite is weaker evidence on the ffmpeg surface than its pass count suggests**, and no block may treat a pass as sufficient there. |
| **R15** | **The suite cannot see this plan's central surface.** No stream-discipline oracle exists; `CliRunner()` merges streams and `mix_stderr` appears zero times. `B6`'s property is byte-level and cannot be tested in-suite. | `B6` requires the two-file `Start-Process` harness explicitly, splits its evidence into *renderer configuration* (in-suite) and *emitted bytes* (external), and states that the second is not substitutable. |
| **R16** | **A new test skips on Windows**, silently converting into a pass-count drop against §2.8's floor. | Every block's criteria state **3** skipped, and `B3`'s and `B6`'s say explicitly that their new tests may not skip. A block that adds a permission-shaped assertion is the specific hazard — plan 11 `B3` and plan 12 `P12-B11` own every permission oracle, and none of this plan's seventeen may convert or touch one. |
| **R17** | **The reference and the code drift apart.** `C5` means `tests/test_cli.py` fails the moment one reference file moves without the other — but only for what a test reads. Five of seventeen blocks edit the reference. | Each such block edits **both** files in the same commit, and the packaging frozensets stay at 73/32 because no file is added or removed under `src/`, `tests/` or `docs/`. |
| **R18| | **`B10` changes the value `B7` depends on.** `echo = not reporter.is_enabled` reads a property whose decision moment moves. | `B7` re-reads the property after `B10` lands; the edge is a re-read requirement, not an assumption. |

### 5.4 Compatibility risk

| ID | Risk | Containment |
|---|---|---|
| **R19** | **The exit-status change is a breaking change for scripts — larger than originally scoped.** Decision A makes it a **four-code re-partition**: a preamble failure moves `1`→`3`, an out-of-range `--max-retries` moves `1`→`3`, `1`'s meaning narrows to download failure alone, and `2` narrows to true parser rejections. **Any script branching on `1` to detect "the setup is wrong" breaks.** | Both changes are **toward the code the reference documents for the situation** — a configuration error is not a failed download, and that is the finding. `B1`'s criteria 2 and 4 assert all three of `1`/`2`/`3` are distinguishable and that the tables state `4`-and-above as unallocated. `B5`'s criterion 3 asserts non-numeric input stays in `2`, so the two boundaries are pinned from both sides. **No shim, no flag, no compatibility alias** — consistent with plan 10 `B10`'s standing decision that this programme takes breaking changes rather than deprecations, and with the Owner's choice of a dedicated code over widening `2`. |
| **R20** | **Renaming a log record breaks log aggregation.** `B13` introduces a new event name; `B4` adds fields to three. | `B4`'s criterion 4 forbids renaming any record — the names are the aggregation keys. `B13` **replaces one name's meaning for one cause** and keeps it for the other, which is the narrowest possible change; the commit message names the old-to-new mapping so a query can be updated. |
| **R21| | **`--method ffmpeg` was a working argument for existing scripts.** It is already rejected at `d572d96`; `B17` only adds the explanation. | `B17` does not change the status (`2`), does not add a tombstone, and does not touch `DownloadMethod`'s members. The compatibility break already happened in the retirement; this block only makes it legible. |
| **R22** | **Renaming the batch summary line breaks output-scraping scripts.** | `B8` renames a label; the value is unchanged and the line's position is unchanged. Accepted, because the label was wrong — it named a unit the value never had. Both affected assertions are updated in the same commit so the suite states the new truth. |

### 5.5 Risks this plan accepts rather than removes

| ID | Accepted risk | Why |
|---|---|---|
| **R23** | **`TestMethodFfmpegRemoved` remains unable to distinguish a removed flag from a rejected value.** | Recorded, not worked (§1.4). It is another plan's block's quality question. `B17` adds its own narrow witness and states what it does and does not prove. |
| **R24** | **Plan 11 `B3` has two unsatisfiable acceptance criteria.** | Recorded, not worked around (§3.15, CF-6). The correction belongs to plan 11's owner; amending another plan's criteria from here would be worse than the defect. |
| **R25** | **The six documentation files outside this plan's scope still describe a live ffmpeg transport** until plan 10 `B10`'s doc track lands. | Plan 10's obligation (§1.4, CF-8). `B17` names them in its commit message so the residue is visible rather than silent. |
| **R26| | **Polars remains absent while rule 11 requires it** (`DV-1`). | Introducing Polars for a handful of per-item tuples would violate rule 5 far more seriously than it satisfies rule 11. |
| **R27| | **`OUT-006`'s capability check is made once, at configuration time.** | `D-7 = Alt A`'s known weakness, stated in the block rather than hidden. A redirection performed *after* `setup_logging` is the caller's, not the logging stack's; the alternative requires a custom renderer, which §1.3 and rule 5 forbid. |
| **R28** | **`OUT-002`'s JSON is parseable only after `B3` lands**; the declared-JSON contract is false until then. | The reference's JSON claim is `B3`'s to fix. No block may document the JSON as parseable before `B3` lands. |
| **R29** | **Decision C leaves `OUT-015` half closed, and the residual is easy to forget.** The log **destination** has no option and will not get one, so the per-run debugging that `OUT-002`'s and `OUT-006`'s investigations wanted still requires editing a file on disk. | §1.4 records the residue with its cost stated; `B2`'s acceptance criterion 5 requires **both** reference files to say the destination is environment-only; §1.3 lists the option as out of scope. Re-opens only if the Owner reverses Decision C. |
| **R30** | **Decision B forecloses batching without evidence, and a future reader may treat that as a settled technical claim.** The rejection rests on an **absence of measurement**, not on a measurement showing the volume is acceptable. | `D-8`'s retained record states the condition that would reopen it — **a measured per-video non-progress line count above a stated threshold** — and `D-8` is marked closed, so a re-proposal must produce that number rather than argue from taste. Decision B did not create the evidence; it recorded the absence honestly. |

## 6. Task specifications

Seventeen tasks, one per block, using `.ai/tasks/templates/task_template.yaml`. **Anchors are
`semantic_anchors` only** — `insert_after` / `insert_before` by symbol. **No task may add a file
under `src/`, `tests/` or `docs/`**, so `tests/test_packaging.py`'s frozensets stay at **73/32** in
every task. Every task's `acceptance_criteria` includes the shared floor.

**Shared floor, appended to every task below:**
`uv run pytest -q -rs` reports **759+ passed and exactly 3 skipped** · `uv run ruff check src tests`
clean · `uv run ruff format --check src tests` as at baseline (**`G0` resolved** — §2.11; a red in a
file this plan does not touch is reported, not fixed) · `uv run mypy src` clean · `git status
--porcelain -- src tests docs pyproject.toml` shows only this task's own edits.

### 6.1 Wave 1 — independent foundations

```yaml
id: P13-B14
title: "Record working-tree provenance and refuse a dirty tree in the audit pipeline"
priority: high
depends_on: []
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.15 `B14` — pipeline provenance (VAL-003, HIGH)"
description: >
  Make the audit pipeline record the tree it actually read, not only the commit it names, and
  refuse to start a phase against a dirty tree. Verified at execution time: audit-multi-phase.md
  builds {BASE_CONTEXT} with no `git rev-parse HEAD` and no `git status --porcelain`.
goals:
  - "Replace the single 'commit measured' line with a provenance block: commit, working-tree state, dirty paths"
  - "Add `git rev-parse HEAD` and `git status --porcelain` to the {BASE_CONTEXT} construction and the per-phase output"
  - "Make a dirty tree a hard stop, not a note (D-14 Alt A)"
  - "Leave audit-refine.md holding the same defect the multi-phase path just fixed"
  - "Record plan 11 B3's two unsatisfiable acceptance criteria (Conflict-8 / CF-6) without amending them"
files:
  - path: .kilo/commands/audit/audit-multi-phase.md
    targets: [{ type: section, name: "{BASE_CONTEXT} construction" }]
    semantic_anchors:
      insert_before:
        type: literal
        value: "Base context: {BASE_CONTEXT}"
  - path: .ai/audit/templates/audit-findings.md
    targets: [{ type: section, name: "provenance header" }]
    semantic_anchors:
      insert_after:
        type: literal
        value: "**Commit measured:**"
  - path: .kilo/commands/audit/audit-refine.md
    targets: [{ type: section, name: "base context" }]
changes:
  - action: add_code
    description: "Add the two git invocations to BASE_CONTEXT and a per-phase provenance line."
  - action: add_code
    description: "Add the dirty-tree hard stop and its stated behaviour."
acceptance_criteria:
  - "{BASE_CONTEXT} carries the resolved commit AND the working-tree state"
  - "The report template's provenance block names commit, clean/dirty, and every dirty path"
  - "A phase cannot start against a dirty tree without a visible refusal"
  - "audit-refine.md does not retain the defect audit-multi-phase.md just fixed"
  - "Conflict-8's three-criterion table is recorded; plan 11's block is NOT amended"
  - "No existing audit report is re-run or retro-fitted"
  - "Shared floor"
```

```yaml
id: P13-B15
title: "Point the audit commands at files that resolve and exclude the census's own corpus"
priority: medium
depends_on: []
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.16 `B15` — VAL-004 + VAL-005 (MEDIUM)"
description: >
  VAL-004 is half-fixed: audit-multi-phase.md now names .kilo/rules/project.md and
  .kilo/rules/commands.md, while audit-refine.md still names a non-existent AGENTS.md. VAL-005's
  guard is category-based, not path-based, so a census can still propose deleting its own
  instructions.
goals:
  - "Replace audit-refine.md's AGENTS.md reference with the paths that exist, matching audit-multi-phase.md"
  - "State in both commands that an absent input is REPORTED, not silently skipped"
  - "Add the missing references to kilo.json / kilo.local.json / the phase report template"
  - "Add a PATH-BASED exclusion list to audit-orphaned.md alongside the existing category guard (D-15 Alt A)"
files:
  - path: .kilo/commands/audit/audit-refine.md
    targets: [{ type: literal, name: "AGENTS.md" }]
    semantic_anchors:
      insert_after:
        type: literal
        value: "Read `.ai/context/commands.md` for verification commands."
  - path: .kilo/commands/audit/audit-orphaned.md
    targets: [{ type: section, name: "Protect and exclude from the removal candidates" }]
    semantic_anchors:
      insert_after:
        type: literal
        value: "Protect and exclude from the removal candidates:"
changes:
  - action: add_code
    description: >
      Path-based exclusion list naming .ai/audit/**, .kilo/commands/audit/**, .kilo/agents/**,
      every **/.kilo/worktrees/** directory, .git/**, .venv/**, build and cache directories, and
      .ai/audit/orphaned-files/ itself. The existing category guard is RETAINED, not replaced.
acceptance_criteria:
  - "Neither audit command names a file that does not resolve — verified by existence, not by reading"
  - "Both commands say to report an absent input rather than continue silently"
  - "audit-refine.md names the same rule files audit-multi-phase.md names, so the two cannot drift"
  - "The exclusion list is path-based and names all nine categories above"
  - "The existing category guard is retained"
  - "The stale .kilo/worktrees/southern-bandana/ corpus is covered by the worktree exclusion and is NOT deleted"
  - "Shared floor; both packaging frozensets unchanged at 73/32"
```

```yaml
id: P13-B2
title: "Add --log-level as an option and correct the failure hint to name only what exists"
priority: high
depends_on: []
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.3 `B2` — OUT-015 half + Live-1 (HIGH)"
extra_context: >
  DECISION C (§1.0.1) IS BINDING AND HALF-REVERSES THIS BLOCK. --log-level ONLY. NO --log-file. The
  log file stays environment-configured via VKDOWNLOADER_LOG_FILE / .env. This block was built on the
  assumption that BOTH options would be added, which would have made the existing hint in
  _render_preamble_failure true by adding the flag it names. That route is CLOSED.

  THE CONSEQUENCE: the hint must be CORRECTED, not justified. _render_preamble_failure currently says
  "Check the --log-file option or VKDOWNLOADER_LOG_FILE environment variable." It must name NO
  option — only VKDOWNLOADER_LOG_FILE and .env. THAT IS THE EXACT FIX FOR Live-1, and it is the
  former D-2 Alt B route, not the Alt A route this task was written against.

  OUT-015 IS HALF CLOSED, NOT CLOSED. log_level gains an option; log_file does not. The residue is
  recorded in §1.4 — the reference MUST state that log destination is environment-only, so the
  asymmetry is a stated decision rather than the gap the finding describes, and the residual cost
  (no per-run sink switch) is recorded rather than dropped. Do NOT silently drop the other half.

  D-2 IS CLOSED — do not re-open it. D-3 (routing through _SettingsOverrides) remains OPEN with its
  default Alt A.

  CF-3: plan 12 P12-B10 route (a) was called the only unconstrained block and may write these option
  blocks. This task owns --log-level. If plan 12 has written cli.py, this task WAITS.
description: >
  Settings.log_level and Settings.log_file decide what the process emits and neither reaches the
  caller as an option. Decision C closes the asymmetry for verbosity only: --log-level is added,
  --log-file is not, and the log destination stays environment-configured. Separately,
  _render_preamble_failure tells the operator to check a --log-file option that does not exist — a
  spec-deviation introduced by OUT-001's own fix, and the reason this block is HIGH risk despite a
  LOW finding.
goals:
  - "Add --log-level (annotated LogLevel) in BOTH commands, byte-identical (C4)"
  - "Route it through _SettingsOverrides -> _build_settings -> Settings(**overrides)"
  - "Add NO --log-file option, in either command"
  - "CORRECT the hint in _render_preamble_failure to name VKDOWNLOADER_LOG_FILE and .env and NO option — the direct fix for Live-1"
  - "State in BOTH reference files that the log destination is environment-only, so OUT-015's residue is a decision and not a gap"
files:
  - path: src/vkdownloader/cli.py
    targets:
      - { type: class, name: _SettingsOverrides }
      - { type: function, name: _build_settings }
      - { type: function, name: _run_command_preamble }
      - { type: function, name: _render_preamble_failure }
      - { type: function, name: download }
      - { type: function, name: batch_download }
    semantic_anchors:
      insert_after:
        type: function_call
        value: _build_settings
  - path: src/vkdownloader/models/enums.py
    targets: [{ type: enum, name: LogLevel }]
    semantic_anchors: {}
  - path: tests/test_cli.py
    targets: [{ type: variable, name: _REFERENCE_DOC_NAMES }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference.md
    targets: [{ type: section, name: "log options" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference-clean.md
    targets: [{ type: section, name: "log options" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "One key in _SettingsOverrides for log_level (total=False); one forwarding branch in _build_settings; one keyword-only parameter in _run_command_preamble; the --log-level declaration in BOTH commands."
  - action: modify
    description: "The hint string in _render_preamble_failure — remove the option token, keep the environment variable, add .env."
  - action: add_code
    description: "A test asserting every option-looking token in the hint resolves against the captured --help."
acceptance_criteria:
  - "Both --help outputs list --log-level and its declaration is byte-identical in both commands (C4), verified by reading both declarations"
  - "NEITHER help output contains --log-file, and no option declaration for it exists anywhere in cli.py"
  - "Supplying --log-level changes verbosity AND not supplying it leaves VKDOWNLOADER_LOG_LEVEL / .env reachable — asserted in BOTH directions"
  - "Live-1 is closed BY CONSTRUCTION: the hint names no option, names VKDOWNLOADER_LOG_FILE and .env, and a test asserts every option-looking token in the message resolves against the captured --help"
  - "Both reference files carry the --log-level row AND a stated-limitation sentence that the log file is environment-configured and no option selects it (§1.4's residue)"
  - "patch(\"vkdownloader.cli.warn_unknown_env_vars\") still resolves (C3) — the new tests use the string path"
  - "LogLevel exists and is the StrEnum the option annotates; NO new enum is minted"
  - "setup_logging's processor list and the SEC-003: comment are byte-unchanged"
  - "The two option blocks differ ONLY in --max-retries's help string"
  - "Shared floor"
```

```yaml
id: P13-B3
title: "Render an exception once and keep the declared JSON log parseable"
priority: high
depends_on: []
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.4 `B3` — OUT-002 (MEDIUM, HIGH contention)"
extra_context: >
  CF-1: setup_logging has THREE writers. plan 11 B6 places a redaction processor IMMEDIATELY AFTER
  format_exc_info (adjacent lines in one list literal); plan 12 P12-B11 owns the SEC-003: comment and
  the confinement posture above basicConfig. Preferred order is B6 then B3. If D-4 = Alt A and B6
  has not landed, place the new entry at the END of the processor list so a later insertion above it
  cannot merge-conflict, and say so in the commit message. If D-4 = Alt B, WAIT for both writers.
  DO NOT touch the SEC-003: comment.
description: >
  format_exc_info clears exc_info from the structlog event dict only; the stdlib logging.Formatter
  underneath re-appends the traceback from the LogRecord. The traceback therefore renders twice and
  every exception-carrying record makes the log file unparseable as one-JSON-object-per-line.
goals:
  - "Suppress the second render (D-4 Alt A: clear exc_info on the LogRecord after format_exc_info, before UnicodeDecoder)"
  - "Leave the traceback exactly once, INSIDE the JSON object, as a key"
  - "Keep every non-exception record parsing, with TimeStamper and add_log_level unchanged"
  - "Edit ZERO call sites — the sixteen-record count must be unchanged"
files:
  - path: src/vkdownloader/config.py
    targets: [{ type: function, name: setup_logging }]
    semantic_anchors:
      insert_after:
        type: function_call
        value: structlog.processors.format_exc_info
  - path: tests/test_config.py
    targets: [{ type: class, name: "setup_logging tests" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "One processor in the existing list whose only action is clearing exc_info on the stdlib logger it receives."
acceptance_criteria:
  - "A log file written with VKDOWNLOADER_LOG_FILE set, containing an exception-carrying record, parses EVERY line as a JSON object"
  - "The traceback appears EXACTLY once and inside the JSON object, as a key"
  - "Non-exception records still parse; TimeStamper's ISO/UTC stamp and add_log_level's key unchanged"
  - "The ConsoleRenderer (stderr) path renders the traceback exactly once"
  - "ZERO call sites edited; the sixteen-record count unchanged and stated in the commit message"
  - "The SEC-003: comment and the log-file creation branch are byte-unchanged (plan 12 P12-B11's)"
  - "Neither new test skips on Windows; the two D-11 oracles in this file are NOT touched — 3 skipped"
  - "Shared floor"
```

```yaml
id: P13-B8
title: "Name the batch summary line for the quantity it reports"
priority: low
depends_on: []
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.9 `B8` — OUT-008 (LOW)"
description: >
  _print_batch_summary prints `Total connections: {len(results)}`, where results holds one entry per
  VIDEO. The label names a unit the value does not have, and it is the one line a reader would use to
  reconcile supplied URLs against attempted videos. D-9 decides rename-only (Alt A) vs. also adding
  the supplied count (Alt B).
goals:
  - "Rename the label to match the unit the value holds and the unit the rest of the account already uses"
  - "Update both affected test_cli.py assertions — the VALUE (2) stays asserted, not only the label"
  - "Describe the line with the new label in BOTH reference files"
files:
  - path: src/vkdownloader/services/batch_downloader.py
    targets: [{ type: function, name: _print_batch_summary }]
    semantic_anchors:
      insert_before:
        type: function_call
        value: typer.echo
  - path: tests/test_cli.py
    targets: [{ type: literal, name: "assert \"Total connections:\"" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference.md
    targets: [{ type: section, name: "batch summary" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference-clean.md
    targets: [{ type: section, name: "batch summary" }]
    semantic_anchors: {}
changes:
  - action: modify
    description: "The summary label string; plus one added line only if D-9 = Alt B."
acceptance_criteria:
  - "The label's unit matches what the value holds and matches the account's other rows and the concurrency tracker"
  - "Both affected assertions updated; the count itself is still pinned"
  - "Both reference files describe the line with the new label"
  - "Nothing else in the summary changes: successful / failed / cancelled counts, Failed URLs: block, interruption note untouched"
  - "Shared floor"
```

```yaml
id: P13-B16
title: "Remove stale ffmpeg claims from surviving code"
priority: low
depends_on: [P13-B10]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.17 `B16` — Live-2 (LOW)"
description: >
  Three occurrences of `method: Download method (yt-dlp, ffmpeg, or auto).` in batch_downloader.py,
  and one unknown-total comment in progress_display.py naming "the ffmpeg path". Both name ffmpeg as
  a LOADER. Under §1.0 the loader is permanently gone and the segment merge is permanent, so both
  statements are now false and fixing them is a correctness obligation. A docstring and a comment
  block; the correct number of new tests is ZERO.

  §1.0 PERMANENT LIST — touch nothing: _merge_batch_segments, _perform_final_merge,
  _merge_segments_batched, _build_ffmpeg_concat_command, _required_merge_bytes, _check_merge_space,
  _await_ffmpeg_with_timeout, _MERGE_SPACE_MARGIN_BYTES, check_ffmpeg_available. The
  ffmpeg_not_found hint string inside check_ffmpeg_available is plan 16's (CF-12) — DO NOT write it.
goals:
  - "Replace all THREE method docstrings so none names ffmpeg as a download method — a correctness obligation under §1.0, not a tidy-up"
  - "Make the unknown-total comment name whatever D-16 selects (segment path / no transport named), never a permanently-removed loader. D-16's criterion is UNCHANGED — measure the producer count first — but §1.0 settles the error class: Alt C is excluded"
  - "Touch NOTHING in the permanent list: _merge_batch_segments, _perform_final_merge, _merge_segments_batched, _build_ffmpeg_concat_command, _required_merge_bytes, _check_merge_space, _await_ffmpeg_with_timeout, _MERGE_SPACE_MARGIN_BYTES, check_ffmpeg_available"
files:
  - path: src/vkdownloader/services/batch_downloader.py
    targets: [{ type: literal, name: "method: Download method (yt-dlp, ffmpeg, or auto)." }]
    semantic_anchors: {}
  - path: src/vkdownloader/services/progress_display.py
    targets: [{ type: literal, name: "the ffmpeg path" }]
    semantic_anchors: {}
changes:
  - action: modify
    description: "Three docstring lines and one comment line. No executable line changes."
acceptance_criteria:
  - "grep over src/ finds ZERO `method:` docstrings naming ffmpeg; the replacement count is exactly THREE and is stated in the commit message"
  - "The unknown-total comment names something that EXISTS (D-16 decided by measuring the producer count first) and does NOT attribute unknown totals to a permanently-removed loader"
  - "No executable line changed — git diff --stat shows comment and docstring lines only"
  - "check_ffmpeg_available is PERMANENT product surface (§1.0) — the diff adds NO reference to it, removes none, and rewords neither it nor its hint string"
  - "Zero new tests"
  - "Shared floor; format-neutral by construction"
```

### 6.2 Wave 2 — after wave 1

```yaml
id: P13-B10
title: "Decide display activity from a single predicate"
priority: low
depends_on: []
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.11 `B10` — OUT-010 (LOW)"
extra_context: >
  D-11 is a RESEARCH question: rich's documented position on Console construction cost and reuse
  decides Alt A (keep the lazy construction, move the decision after the console exists) from
  Alt B (resolve the console eagerly, delete the sys.stderr.isatty() fallback). Do not decide it
  from memory. Six call sites observe this property: RichProgressReporter.start, start_task,
  set_title, update, finish_task, and batch_downloader's `echo = not reporter.is_enabled`.
  No real terminal exists on the declared platform and none may be substituted (R-N).
goals:
  - "Make is_enabled, the _repoint_log_handlers decision and the auto_refresh decision ONE predicate at ONE moment"
  - "Re-run the differential measurement (one variable at a time, both predicates before and after start()) as the input to D-11"
  - "Preserve the deliberate laziness unless D-11 = Alt B, in which case correct the comment claiming it"
files:
  - path: src/vkdownloader/services/progress_display.py
    targets:
      - { type: property, name: RichProgressReporter.is_enabled }
      - { type: method, name: RichProgressReporter.start }
    semantic_anchors:
      insert_before:
        type: function_call
        value: self._repoint_log_handlers
  - path: tests/test_progress_display.py
    targets: [{ type: literal, name: "force_terminal=True sites" }]
    semantic_anchors: {}
changes:
  - action: modify
    description: >
      start() builds the console first and reads the decision once; is_enabled resolves to
      console.is_terminal when a console exists. The sys.stderr.isatty() mirror comment becomes a
      statement of a real precondition, or the fallback is deleted under D-11 = Alt B.
acceptance_criteria:
  - "A test makes the two predicates disagree under the OLD shape and requires consistency under the new one"
  - "No real terminal is substituted for a non-terminal one; no test claims to have observed the harmful direction"
  - "The two force_terminal=True sites pass UNCHANGED"
  - "The seven `assert \"Traceback\" not in result.output` sites in test_cli.py are green unchanged"
  - "If D-11 = Alt B, the comment claiming deliberate laziness is corrected in this commit"
  - "The block does not pass by disabling the display — the positive direction is asserted"
  - "Shared floor"
```

```yaml
id: P13-B5
title: "Declare the max-retries range and document the option"
priority: medium
depends_on: [P13-B2]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.6 `B5` — OUT-005 (MEDIUM)"
extra_context: >
  D-6 IS CLOSED — THE TECH LEAD HAS RULED. --max-retries must NOT use Click's parse-time range
  rejection. The range is declared in the Pydantic model (Settings.max_retries already carries
  ge=1, le=10) and enforced INSIDE THE COMMAND BODY, so an out-of-range value produces a
  configuration-error exit 3 with a message naming the setting and its bounds.

  ADD NO min= AND NO max= TO EITHER OPTION DECLARATION. This is a PROHIBITION, not a preference
  (R3b). Parse-time rejection is ruled out because Click's IntRange rejects during ARGUMENT PARSING
  and yields exit 2 — the usage-error class — which would make a configuration error
  indistinguishable from a mistyped flag and destroy the distinction Decision A created by reserving
  3. Declaring the bounds twice, once in min=/max= and once in the model, IS the defect.

  THE BOUND MUST GOVERN ALL FOUR ROUTES into the field: the option, VKDOWNLOADER_MAX_RETRIES, .env,
  and the field default. That is the point of enforcing in the model, and the Auditor must confirm
  all four.

  NON-NUMERIC STAYS 2. `abc` is not out of range — it is not a number — so it is a usage error by
  Decision A's table. This is the ruling's BOUNDARY, not a weakening, and the pair
  (out-of-range -> 3, non-numeric -> 2) must be asserted in the SAME test class.

  ACCEPTED COST, MITIGATED IN DOCS: the bound will not appear in --help's metavar. Both reference
  files' --max-retries row must carry the range instead.

  CF-13: this task is the FIRST producer of 3 (B1 writes the same row and the same neighbourhood of
  cli.py's exception clauses, for the preamble case). This task goes BEFORE B1 on the chain. This task
  owns the ValidationError clause; B1 owns the _PreambleFailure clause. Neither may rename the other's
  3 case, and the 3 row is written once, by whichever lands last, naming BOTH producers.

  Measured at 09f1b10: --max-retries 0 exits 1 with a message that misdirects toward .env; abc exits 2.
  Settings.max_retries ALREADY declares ge=1, le=10 — which is why it is the enforcement point.
description: >
  --max-retries out of range is currently reported as exit 1 with a message that misdirects toward
  .env. Decision A classifies it as a configuration error and the Tech Lead has ruled that the
  Tech Lead-ruled enforcement point is the model's own validation in the command body, producing exit
  3. The reference also omits --max-retries from both commands' option tables entirely.
goals:
  - "Make an out-of-range --max-retries exit 3 in BOTH commands, enforced by the model's validation in the command body"
  - "Declare NO min=/max= on the option — the model is the single source of the bound"
  - "Name the setting and its bounds in the rejection message, so it no longer misdirects toward .env"
  - "Keep --max-retries abc in the 2 class, asserted in the same test class, so the 3-vs-2 boundary is pinned from both sides"
  - "Carry the range in both commands' --max-retries row in BOTH reference files, and name this case in the 3 row"
files:
  - path: src/vkdownloader/cli.py
    targets:
      - { type: function, name: download }
      - { type: function, name: batch_download }
    semantic_anchors:
      insert_after:
        type: function_call
        value: _quality_option
  - path: src/vkdownloader/config.py
    targets: [{ type: model_field, name: Settings.max_retries }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference.md
    targets: [{ type: section, name: "max-retries option row" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference-clean.md
    targets: [{ type: section, name: "max-retries option row" }]
    semantic_anchors: {}
  - path: tests/test_cli.py
    targets: [{ type: section, name: "option validation tests" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "NO range literal on either option declaration — that is the prohibited edit. The option stays as it is today."
  - action: modify
    description: "The ValidationError path so an out-of-range max_retries yields 3, and the message names the setting and its bounds."
  - action: add_code
    description: "New assertions: out-of-range (expects 3) and non-numeric (expects 2) in the SAME test class, plus a valid value — for BOTH commands."
acceptance_criteria:
  - "An out-of-range --max-retries (0, -1, and the ceiling-breaker) exits 3 for BOTH commands; the ceiling-breaker is verified against Settings.max_retries's le, READ FROM THE MODEL FIELD"
  - "--max-retries abc exits 2 — asserted IN THE SAME TEST CLASS as the 3 case, because the pair is the ruling's boundary"
  - "The rejection message names the setting AND its bounds (max_retries, 1..10), and no longer points at .env as the thing to fix"
  - "A value inside the range is accepted AND reaches Settings — asserted"
  - "NEITHER option declaration carries min= or max=, and no parse-time range check exists on this option (R3b, restated as an executable check)"
  - "The model bound governs ALL FOUR routes into the field: option, VKDOWNLOADER_MAX_RETRIES, .env, field default — confirmed by the Auditor"
  - "The two option blocks differ only in --max-retries's help string"
  - "Both reference files carry the --max-retries row for both commands INCLUDING the range (mitigating the absent metavar), AND the 3 row names this case"
  - "CF-13 honoured: this block does not rename B1's preamble entry in the 3 row"
  - "Click's UsageError exit code is NOT remapped, and 2 keeps its meaning for every other command"
  - "Shared floor"
```

```yaml
id: P13-B6
title: "Suppress terminal control sequences when the log sink is not a terminal"
priority: medium
depends_on: [P13-B3]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.7 `B6` — OUT-006 (MEDIUM)"
extra_context: >
  The suite CANNOT verify this block. CliRunner() is module-level with merged streams, mix_stderr
  appears ZERO times, create=True appears ZERO times, and no test asserts a stream is a terminal.
  Verification is therefore split: the in-suite test asserts the RENDERER'S CONFIGURATION; the
  byte-level property needs the two-file harness —
  Start-Process -NoNewWindow -Wait -RedirectStandardOutput <out> -RedirectStandardError <err>
  against the installed console script, with VKDOWNLOADER_LOG_LEVEL raised so a record is
  certainly emitted, then a byte scan of both files for escape sequences.

  CF-10 COUPLING: D-7's single-lever sufficiency depends on format_exc_info running BEFORE
  ConsoleRenderer and pre-rendering the traceback into a plain string — which structlog 26.1.0's
  ConsoleRenderer.__call__ confirms (it invokes _exception_formatter only when exc_info is STILL
  truthy). If B3 resolved D-4 to Alt B (ProcessorFormatter), that no longer holds and B6 MUST add
  the second lever, exception_formatter.
goals:
  - "Pass colors= to ConsoleRenderer() explicitly, derived from a capability check on the sink's stream (D-7 Alt A: sys.stderr.isatty() at configuration time)"
  - "Correct the reference sentence that today claims no escape codes are written when redirected — it is FALSE for the log stream"
  - "Split the evidence: renderer configuration in-suite, emitted bytes via the external harness"
files:
  - path: src/vkdownloader/config.py
    targets: [{ type: function, name: setup_logging }]
    semantic_anchors:
      insert_after:
        type: function_call
        value: structlog.processors.UnicodeDecoder
  - path: tests/test_config.py
    targets: [{ type: class, name: "setup_logging tests" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference.md
    targets: [{ type: section, name: "progress and output" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference-clean.md
    targets: [{ type: section, name: "progress and output" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "An explicit colors= argument on ConsoleRenderer(), plus the exception_formatter lever if D-4 = Alt B."
acceptance_criteria:
  - "The two-file harness shows ZERO escape sequences in both redirected files, with a record certainly emitted"
  - "The same harness against a terminal (or pty) shows escapes PRESENT — the block may not pass by disabling colour everywhere"
  - "colors= is set explicitly; the JSONRenderer branch is byte-unchanged"
  - "The reference's progress-section sentence is now true, in BOTH files"
  - "An in-suite test asserts the renderer's colors value for terminal and non-terminal sinks, and is NOT claimed to prove the byte-level property"
  - "If a caller that redirects stderr AFTER the preamble is found in src/, the block STOPS and reports rather than widening the fix"
  - "No new test skips on Windows — 3 skipped"
  - "Shared floor"
```

```yaml
id: P13-B9
title: "Count the skipped status explicitly and state its reachability"
priority: low
depends_on: [P13-B8]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.10 `B9` — OUT-009 (LOW)"
extra_context: >
  ProgressStatus.SKIPPED is a live StrEnum member, rendered by _StatusColumn.render ([o], yellow)
  and _format_outcome ("skipped"), and documented with a marker — but the aggregation names only
  SUCCESS and CANCELLED and derives FAILED BY SUBTRACTION, so a fourth status would be reported as
  failed. No producer exists: the invalid-URL path never enters results and is counted separately
  as skipped_count. D-10 default is Alt A + the Alt C reference sentence TOGETHER.
  ProgressStatus.SKIPPED is NOT deleted — rule 10 and C7 forbid minting or removing members here.
goals:
  - "Add SKIPPED as a third explicit count so failed becomes a count, not a remainder (D-10 Alt A)"
  - "State in BOTH reference files whether the [o] marker is currently reachable (D-10 Alt C)"
files:
  - path: src/vkdownloader/services/batch_downloader.py
    targets: [{ type: function, name: _print_batch_summary }]
    semantic_anchors:
      insert_after:
        type: function_call
        value: _classify_download_result
  - path: src/vkdownloader/models/enums.py
    targets: [{ type: enum, name: ProgressStatus }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference.md
    targets: [{ type: section, name: "status marker" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference-clean.md
    targets: [{ type: section, name: "status marker" }]
    semantic_anchors: {}
  - path: tests/test_cli.py
    targets: [{ type: section, name: "batch summary tests" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "A third explicit count and failed as a count rather than a remainder."
  - action: add_code
    description: "A direct assertion against the aggregation: a SKIPPED entry is counted as skipped and NOT as failed."
acceptance_criteria:
  - "The aggregation names every ProgressStatus member that can reach it, or the reference states which cannot"
  - "A SKIPPED entry in results is counted as skipped and is NOT counted as failed — asserted directly"
  - "ProgressStatus.SKIPPED still exists; no member deleted"
  - "The reference's marker line states reachability, in BOTH files"
  - "The three existing per-class counts are byte-unchanged"
  - "Shared floor"
```

```yaml
id: P13-B11
title: "Release borrowed handlers unconditionally in stop"
priority: low
depends_on: [P13-B10]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.12 `B11` — OUT-011 (LOW)"
extra_context: >
  ORDERING DEFECT; TRIGGER UNVERIFIED. No reproduction is manufactured (R-S) and no claim is made
  that progress.stop() can raise — the recommendation is to remove the dependency. stop() currently
  runs progress.stop(), then _restore_log_handlers(), then four unconditional .clear() calls with
  NO try/finally anywhere in the method.

  SHARED SLOT: stop() is written by B11 and B12 in this plan. If they are released in the SAME
  window they MAY land as ONE commit naming both findings; if anything separates them they are TWO
  commits and B12 re-reads stop() after B11 lands. They must NEVER be in flight from two agents.
  No other block in this plan touches stop().
goals:
  - "Make the handler restore and the four map clears unconditional, so neither can starve the other"
  - "State the post-conditions stop() now guarantees in its docstring"
files:
  - path: src/vkdownloader/services/progress_display.py
    targets: [{ type: method, name: RichProgressReporter.stop }]
    semantic_anchors:
      insert_before:
        type: function_call
        value: self._restore_log_handlers
  - path: tests/test_progress_display.py
    targets: [{ type: section, name: "stop tests" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "try/finally so _restore_log_handlers() runs regardless, and the four clear() calls run in an outer finally."
  - action: add_code
    description: "A test substituting a progress whose stop() raises, asserting the streams were restored and the maps cleared."
acceptance_criteria:
  - "If progress.stop() raises, _restore_log_handlers() STILL runs and the four maps STILL clear"
  - "If _restore_log_handlers() raises, the four maps STILL clear"
  - "The happy path is byte-unchanged: sys.stderr is the original object, _saved_handler_streams is empty, root handler count unchanged"
  - "stop() remains safe without start() and remains idempotent"
  - "The docstring states the post-conditions"
  - "The substitute test's docstring states the trigger is unverified and the test drives a stand-in, not the product"
  - "Shared floor"
```

```yaml
id: P13-B12
title: "Give an unfinished task a terminal status at teardown"
priority: low
depends_on: [P13-B10]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.13 `B12` — OUT-012 (LOW)"
extra_context: >
  UNVERIFIED through the binary, and the reachability argument was VERIFIED rather than accepted:
  all eight paths out of _download_single call _finish BEFORE returning or re-raising, so the only
  way stop() sees a task with no terminal status is a task cancelled before its first line runs — and
  such a task never reaches reporter.start_task. The display is built with transient=False, so the
  surviving frame stays on screen showing a download at 10% with no marker, on a process that has
  already exited. The finding's content is that the guarantee rests on EIGHT call sites, not one.

  D-12 is settled by elimination, not carried: CANCELLED is the only truthful terminal state
  available at teardown, because adding an "abandoned" member would be a new StrEnum member with no
  producer, which B9's own subject forbids.

  SHARED SLOT with B11 — see its extra_context. Re-read stop() after B11 lands if they are separate.
goals:
  - "Give every not-yet-terminal task a terminal state before stop() clears the task map"
  - "NEVER overwrite a status that is already terminal — a finished task keeps what it was given"
files:
  - path: src/vkdownloader/services/progress_display.py
    targets:
      - { type: method, name: RichProgressReporter.stop }
      - { type: method, name: RichProgressReporter._StatusColumn.render }
    semantic_anchors:
      insert_before:
        type: function_call
        value: self._tasks.clear
  - path: tests/test_progress_display.py
    targets: [{ type: section, name: "stop tests" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "Before clearing the task map, write CANCELLED to any task with no terminal status. _StatusColumn.render is UNCHANGED — the fix is in the producer."
  - action: add_code
    description: "A test that starts a task, stops without finishing it, and asserts the surviving frame carries a terminal marker."
acceptance_criteria:
  - "After stop() with a task that had begun work, the surviving frame carries a terminal marker and an outcome word"
  - "A task that WAS finished keeps its status — stop() never overwrites a terminal status"
  - "stop() with no tasks, and with tasks never started, is unchanged"
  - "The happy path is byte-unchanged; stop() remains idempotent and safe without start()"
  - "The test's docstring states the reachable-product answer is 'no' and that this pins teardown behaviour, not an observed failure"
  - "Shared floor"
```

### 6.3 Wave 3 — the externally blocked and the exit-status blocks

```yaml
id: P13-B13
title: "Distinguish filesystem failures from token refresh failures"
priority: medium
depends_on: []
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.14 `B13` — OUT-016 (LOW, mandatory)"
extra_context: >
  CORRECTION to the finding's recommendation, recorded rather than followed: the finding says the
  new event name "is a StrEnum member in this codebase's own convention". IT IS NOT. Every log event
  name here is a STRING LITERAL at its call site (ytdlp_progress_suppressed, preamble_failed,
  merge_space_probe_failed, download_progress). ErrorCode in models/enums.py is a DOMAIN-EXCEPTION
  code, not an event-name registry. The new name is a string literal.

  This block's importance is SETTLED, not conditional (see description). The commit message must say
  so, so a later reader does not reconstruct the reasoning.

  CF-4: this block is NOT a writer of ffmpeg_utils._merge_segments_batched's deferral comment — its
  spans are output_file.unlink() and download_hls_with_resume, in ytdlp_downloader.py. But 435ba0b
  and 58bb7ce edited this file and plan 12's P12-B6/P12-B8 touch the same subsystem. RE-DERIVE the
  guarded span BY SYMBOL at execution time; if it cannot be located unambiguously, STOP and report.

  G0 (revised per §2.11): RESOLVED. tests/test_hls_downloader.py is lint-clean and format-clean,
  verified per-file. The formatting-only co-edit fallback is RETAINED AS INSURANCE ONLY and must
  NOT be exercised. If the whole-tree check is red, it is a concurrent in-flight edit elsewhere —
  run the check scoped to this file, REPORT any pre-existing whole-tree red naming the file, and
  do not fix or wait on it.

  §1.0 PERMANENT LIST — this task's spans include the merge's caller, but the merge engine itself
  (_merge_batch_segments, _perform_final_merge, _merge_segments_batched, _build_ffmpeg_concat_command,
  _required_merge_bytes, _check_merge_space, _await_ffmpeg_with_timeout, _MERGE_SPACE_MARGIN_BYTES,
  check_ffmpeg_available) is PERMANENT and is not modified here.

  The fallback is the SEGMENT path, which plan 10 B10's deletion made the only route into the
  transport — and which §1.0 has now made PERMANENT PRODUCT SURFACE.
goals:
  - "Split `except (ExtractionError, OSError)` into two clauses with two event names (D-13 Alt A)"
  - "Add one test per branch so the two classes cannot collapse again"
  - "Keep ExtractionError under the token-refresh name; give OSError a filesystem-named event"
files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: [{ type: literal, name: "failed_to_refresh_token" }]
    semantic_anchors:
      insert_after:
        type: function_call
        value: output_file.unlink
  - path: tests/test_hls_downloader.py
    targets: [{ type: section, name: "yt-dlp fallback tests" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "A second except clause for OSError with its own event name, inside the same guarded span. Control flow otherwise unchanged."
  - action: add_code
    description: "Two tests, one per branch. The finding's measured consequence is that the record surfaces in ONE logger.warning and NOT in the batch account's per-item line, because _classify_download_result(None) yields the literal `failed`."
acceptance_criteria:
  - "An ExtractionError emits the token-refresh event; an OSError emits a filesystem-named event — TWO tests, one per branch"
  - "Neither event name is failed_to_refresh_token unless the cause is an ExtractionError"
  - "Both records carry a sanitised url and error"
  - "The commit message states, or asserts, that the record does NOT surface in the batch account's per-item line"
  - "The guarded span was re-derived by symbol after 435ba0b and 58bb7ce, and the commit message says so"
  - "The commit message states that the fallback is the SEGMENT path and that the segment path is PERMANENT product surface under §1.0, so this diagnostic is not awaiting a transport's retirement"
  - "tests/test_hls_downloader.py formatting is clean; the formatting co-edit, if taken, touches only the two blocks in TestYtDlpSubprocessShutdown; NO blanket reformat of the file"
  - "B7 was not in flight — CF-9; both write ytdlp_downloader.py"
  - "The remaining D-11 oracle in this file is NOT touched — 3 skipped"
  - "Shared floor"
```

```yaml
id: P13-B17
title: "State in --method's own help that the ffmpeg method was removed"
priority: low
depends_on: [P13-B5]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.18 `B17` — Live-3 (LOW)"
extra_context: >
  BOUNDED BY DESIGN (CF-8). Plan 10 B10 owns the eight-file documentation surface; this task may
  touch ONLY the --method option's own help text and the --method row in the two reference files.
  Every other file that still describes ffmpeg as a live transport is NAMED in the commit message
  and referred to plan 10 — not fixed here, not pretended fixed.

  CONTENT IS FIXED BY §1.0 — THE NOTE MUST CARRY THE LOADER / MERGER DISTINCTION. A note reading
  "ffmpeg is no longer used" is FACTUALLY WRONG; "ffmpeg support was removed" is worse. SURVIVING
  WORDING, RECOMMENDED (default for D-17):
    "The ffmpeg download method was removed. yt-dlp is the only download transport; ffmpeg is still
     required to merge downloaded segments."
  ACCEPTABLE, shorter: "The ffmpeg download method was removed; segment merging still uses ffmpeg."
  REJECTED — "ffmpeg is no longer used for downloads": invites the false inference that ffmpeg is now
  optional, and the merge is permanent product surface.
  REJECTED — "ffmpeg support was removed": unambiguously wrong.
  REJECTED as the note, retained as rationale — the deep truth that --method ffmpeg never executed
  its transport anyway: belongs in a changelog, not in --help.
  CRITERION: no surviving wording may leave an operator believing ffmpeg is no longer required.

  PLACEMENT: this task edits the --method help text inside the two option blocks, so C4 puts it on
  the cli.py chain after P13-B5, not on the independent track.

  CF-11: TestMethodFfmpegRemoved's three assertions assert only exit_code == 2 and a whole---help
  substring. NEITHER distinguishes "the value was rejected by the enum" from "the flag was removed
  entirely" — both would still pass if --method were deleted outright. So this task CANNOT be
  verified by the suite as it stands, and a green TestMethodFfmpegRemoved afterwards is NOT evidence
  the note reached the user. This task may ADD a sibling assertion that the help text NAMES ffmpeg.
  It may NOT weaken, delete or re-scope any of the three. If any cannot be kept as written, STOP
  and report. Strengthening the three is recorded and NOT worked (see R23).

  §1.0 PERMANENT LIST — touch nothing: the nine ffmpeg_utils symbols including check_ffmpeg_available,
  whose ffmpeg_not_found hint string is plan 16's (CF-12). DO NOT write that hint.
goals:
  - "Name the removal in --method's help text, identically in both commands, using the recommended wording"
  - "State in both --method reference rows that the VALUE no longer exists AND that ffmpeg remains required for segment merging"
  - "Add a sibling assertion that the help text names ffmpeg, with a docstring saying what it does and does not prove"
files:
  - path: src/vkdownloader/cli.py
    targets:
      - { type: function, name: download }
      - { type: function, name: batch_download }
    semantic_anchors:
      insert_after:
        type: function_call
        value: _quality_option
  - path: docs/99-reference/cli-reference.md
    targets: [{ type: section, name: "method option row" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference-clean.md
    targets: [{ type: section, name: "method option row" }]
    semantic_anchors: {}
  - path: tests/test_hls_downloader.py
    targets: [{ type: class, name: TestMethodFfmpegRemoved }]
    semantic_anchors: {}
changes:
  - action: modify
    description: "The --method help string only. No option added, removed or re-typed. C4 preserved."
  - action: modify
    description: "The --method row in both reference files."
  - action: add_code
    description: "One new sibling assertion in TestMethodFfmpegRemoved that the help text names ffmpeg."
acceptance_criteria:
  - "Both --help outputs name the removal in --method's help text using the recommended wording or another passing §1.0's criterion, and the two help strings are identical to each other"
  - "The --method row in BOTH reference files states the value no longer exists AND that ffmpeg remains required for segment merging; every other file still describing a live ffmpeg transport is NAMED in the commit message and referred to plan 10"
  - "TestMethodFfmpegRemoved's three assertions remain GREEN AND UNWEAKENED — if any cannot be kept as written, STOP and report"
  - "The new sibling assertion's docstring states that, unlike exit_code == 2, it distinguishes the note's presence from its absence"
  - "--method ffmpeg still exits 2; the status is NOT changed by this task"
  - "No option added, removed or re-typed; DownloadMethod's members unchanged; no tombstone; §1.0's nine-symbol permanent list untouched"
  - "The ffmpeg_not_found hint string is NOT written by this task — it is plan 16's (CF-12)"
  - "Shared floor; both packaging frozensets unchanged at 73/32"
```

```yaml
id: P13-B1
title: "Give a preamble failure its own exit status"
priority: high
depends_on: [P13-B2, P13-B5, P13-B17]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.2 `B1` — OUT-001 status half (CRITICAL)"
extra_context: >
  DECISION A (§1.0.1) IS BINDING: the preamble failure exits 3. The four-code contract is
    0 success / 1 download failure (and nothing else) / 2 usage error / 3 configuration error /
    4-and-above unallocated. D-1 IS CLOSED — its former default (2, with the 2 row's prose widened)
  was rejected because a bad .env and a typo on the command line are not the same operator mistake.
  DO NOT re-open D-1; record any objection against §3.2 instead.

  THIS IS A RE-PARTITION, NOT AN APPENDED ROW. Today the 1 row for download reads "invalid URL,
  CONFIGURATION ERROR, download error, or missing streams" and the 2 row is scoped to "rejected by
  the argument parser before anything ran". Move configuration errors out of 1 into the new 3, narrow
  1 to download failure alone, and do NOT justify 3 with 2's "nothing was attempted" rationale — 3's
  justification is "your setup is wrong". Add a 4-and-above-unallocated line so the contract's shape
  is stated once.

  CF-13: B5 also produces 3 (out-of-range --max-retries) and both blocks write the same exit table
  and the same neighbourhood of cli.py's exception clauses. B5 goes first; the 3 row is written ONCE,
  by whichever lands last, naming BOTH producers. If released together they MAY share one commit.
  B1 owns the _PreambleFailure clause; B5 owns the ValidationError clause. Neither may rename the
  other's 3 case.

  RESEARCH question: whether a non-UsageError exception inside a Typer command may raise Exit with
  an arbitrary code without Click rewriting it. A library contract, not an assumption.
description: >
  download and batch_download both handle a _PreambleFailure with `raise typer.Exit(code=1)` — the
  identical status the "Download failed" branch uses. A caller branching on exit status cannot tell
  "the bootstrap never ran" from "the download ran and failed". The _PreambleFailure /
  _render_preamble_failure / _logging_configured machinery already exists; only the status is open.
  Decision A resolves it: the status becomes 3.
goals:
  - "Make both commands exit 3 on a preamble failure, asserting the NUMBER for both commands"
  - "Assert 1, 2 and 3 are all distinguishable — a contract with three codes is only useful if the three differ"
  - "Rewrite BOTH reference files' exit tables as a re-partition, and state 4-and-above as unallocated"
  - "Coordinate the shared 3 row with B5 under CF-13"
files:
  - path: src/vkdownloader/cli.py
    targets:
      - { type: function, name: download }
      - { type: function, name: batch_download }
    semantic_anchors:
      insert_before:
        type: function_call
        value: _render_preamble_failure
  - path: docs/99-reference/cli-reference.md
    targets: [{ type: section, name: "exit codes" }]
    semantic_anchors: {}
  - path: docs/99-reference/cli-reference-clean.md
    targets: [{ type: section, name: "exit codes" }]
    semantic_anchors: {}
  - path: tests/test_cli.py
    targets: [{ type: class, name: "_REFERENCE_DOC_NAMES" }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "The status changes to 3. The body stays _render_preamble_failure(exc)."
  - action: add_code
    description: "New assertions for BOTH commands, naming the code rather than asserting non-zero or merely different-from-1."
acceptance_criteria:
  - "Both commands exit 3 on a preamble failure, and the assertion NAMES the number"
  - "3 differs from 1 (download failure) and from 2 (usage error) — all three asserted"
  - "Both reference files list 0, 1, 2, 3 and 4-and-above-unallocated, and the prose distinguishes 1's 'the command ran and failed' from 3's 'your setup is wrong' WITHOUT borrowing 2's 'nothing was attempted' rationale"
  - "A failed download still exits 1 — asserted, not assumed — and the 1 row no longer lists 'configuration error'"
  - "_render_preamble_failure's MESSAGE TEXT is unchanged unless P13-B2 landed first; if it has not, this task does not touch the message and says so in its commit"
  - "patch(\"vkdownloader.cli.warn_unknown_env_vars\") still resolves (C3) — the new test uses that path, not a private import"
  - "The except Exception catch-alls, the domain-exception clauses and run_batch's exit-code computation are UNCHANGED"
  - "CF-13 honoured: the 3 row names BOTH B1's preamble case and B5's out-of-range case, and neither block renamed the other's entry"
  - "Shared floor"
```

```yaml
id: P13-B7
title: "Record suppressed child output instead of dropping it"
priority: medium
depends_on: [P13-B14, P13-B10]
source_reference: .ai/plans/13-cli-observability-audit-fixes.md
source_blocks:
  - "3.8 `B7` — OUT-007 (MEDIUM)"
extra_context: >
  STRICT EXTERNAL DEPENDENCY: plan 11 B5 must have LANDED. B5 is the writer of record for the
  echo=False contract and pins its clause 3 live and non-weakened. B7 is the SECOND writer and is
  the block that invalidates the "emits NO RECORD" half of that clause.

  DECISION B (§1.0.1) IS BINDING AND RATIFIES D-8's former default: ONE LOG RECORD PER DROPPED LINE
  carrying its text, and stderr stays clean. D-8 IS CLOSED — do not re-open it. BATCHING STAYS
  REJECTED until someone produces a MEASURED per-video non-progress line count above a stated
  threshold; no such measurement exists in the repository, and the sibling progress branch already
  emits one record per line WITHOUT throttling. A re-proposal must produce that number, not argue
  from taste.

  THE COLLISION IS NARROWER THAN B5 FRAMES IT. Clause 3 has two halves:
    (a) echo=False writes NOTHING TO STDERR  — NOT in conflict; Decision B KEEPS it; assert it.
    (b) echo=False on a non-progress line emits NO RECORD — Decision B OVERTURNS this; it is wrong.
  So: STDERR STAYS EMPTY, THE LINE BECOMES A RECORD. The empty-stderr assertion B5 pinned survives
  untouched. B7 edits EXACTLY ONE of the four echo=False tests
  (test_ytdlp_echo_false_non_progress_line_no_output_no_log) and may not weaken the other three.
  If plan 11 B5 has not landed, B7 WAITS — it does not run in parallel and does not pre-empt the
  clause.

  G0 IS RESOLVED (§2.11) — tests/test_hls_downloader.py is lint-clean and format-clean, verified
  per-file. The formatting-only co-edit fallback is RETAINED AS INSURANCE ONLY and must NOT be
  exercised. If the whole-tree format check is red, it will be a concurrent in-flight edit in
  another file: run the check scoped to tests/test_hls_downloader.py, and REPORT any pre-existing
  whole-tree red in the commit message, naming the file. Do NOT fix it and do NOT wait on it.

  CF-9: B7 and B13 both write ytdlp_downloader.py and MUST NOT be in flight together.

  RE-READ REQUIREMENT: B10 changes WHEN is_enabled is decided, and batch_downloader's
  `echo = not reporter.is_enabled` reads it. Re-read the property after B10 lands; do not assume
  the current timing.

  The new event name is a STRING LITERAL consistent with every other record — see B13's correction.
  B7 must also state in its commit message whether plan 11 B6's pipeline transform covers the new
  record, and if it does not, record the residual as unowned rather than shipping it silently.
goals:
  - "Give a dropped non-progress child line — including an error line — a destination: exactly one record carrying its text"
  - "Keep stderr empty for that line, asserted SEPARATELY, because this is the half plan 11 B5 pinned"
  - "Correct _echo_ytdlp_line's docstring, which currently claims non-progress lines are 'dropped silently'"
files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: [{ type: function, name: _echo_ytdlp_line }]
    semantic_anchors:
      insert_before:
        type: function_call
        value: _parse_ytdlp_progress
  - path: tests/test_hls_downloader.py
    targets: [{ type: class, name: test_ytdlp_echo_false_non_progress_line_no_output_no_log }]
    semantic_anchors: {}
changes:
  - action: add_code
    description: "One record per dropped non-progress line, carrying its text (subject to B6's transform, if it covers this path). The echo gate is still evaluated first, so B5's AC5 holds."
  - action: modify
    description: "The ONE test's name, docstring and assertion, together."
acceptance_criteria:
  - "With the display active, a non-progress child line INCLUDING AN ERROR LINE reaches exactly one record carrying its text"
  - "sys.stderr receives NOTHING for that line — asserted separately from the record assertion"
  - "The other three echo=False tests are green UNCHANGED (progress-line record, empty-stderr case, downloaded/total)"
  - "The edited test's NAME and docstring describe the new behaviour — a reviewer reading the name alone cannot conclude lines are still dropped"
  - "_echo_ytdlp_line's docstring no longer claims non-progress lines are dropped silently"
  - "The commit message states whether plan 11 B6's transform covers the new record either way"
  - "Plan 11 B5's echo=False branch (the progress-line record) is UNCHANGED"
  - "The batch_downloader `echo = not reporter.is_enabled` line is READ, not CHANGED — it is B10's"
  - "Shared floor, with format clean — G0 resolved (§2.11), formatting NOT touched"
```

---

## 7. Verification strategy

### 7.1 The gate ladder — five gates, one direction that matters

Every block runs all five before its commit and reports the numbers. **The pass count and the skip
count are the only two that gate; the warning count is observed.**

| Gate | Floor | Gates? |
|---|---|---|
| `uv run pytest -q -rs` | **759+ passed**, **exactly 3 skipped** | **yes, both directions** |
| `uv run ruff check src tests` | clean | **yes** |
| `uv run ruff format --check src tests` | as at baseline. **`G0` resolved** (§2.11) — `P13-B7` and `P13-B13` are **not** gated on it | **yes** — with §7.1's rule: a pre-existing red in a file this plan does not touch is **reported, not fixed** |
| `uv run mypy src` | `Success: no issues found in 31 source files` | **yes** |
| `uv run mypy src tests` | **delta only** — the change in the error count | **no** |

**Skip count gates in both directions and the two directions mean different things.** A **fourth**
skip is review-blocking. A **lower** count is an improvement, **not** a violation — the rule is
"never more than the `D-11` skips", not "always three". No block in this plan may create or retire a
skip: none of the seventeen touches a permission oracle, and `P13-B3` and `P13-B6` state explicitly
that their new tests may not skip.

**Warning counts are observed, never gated.** The single known warning is
`RuntimeWarning: coroutine 'Event.wait' was never awaited` from
`tests/test_downloader_throttle.py::TestProgressManager::test_overwrites_existing_progress`. A block
that changes the count **reports** it.

**Packaging manifests gate by construction.** No task adds or removes a file under `src/`, `tests/`
or `docs/`, so `EXPECTED_SDIST_ENTRIES` stays at **73** and `EXPECTED_WHEEL_ENTRIES` at **32**. A
block whose diff adds a path has failed its own scope.

### 7.2 Re-verification protocol — the baseline is not a constant

`HEAD` moved **twice** while this plan was being written (`d572d96` → `435ba0b` → `b0fb032`), the pass
count rose by two, and **one gate went red** from a commit that landed between measurements (§2.8).
`VAL-003` is precisely this failure recurring in the audit pipeline. Therefore:

1. **Every block re-runs all five gates at execution time.** It does not reason from §2.8's numbers.
2. **If the measured baseline differs from 759/3/clean/clean/clean, the block stops and reports it**
   before editing anything. It does not proceed against a floor it has not verified, and it does not
   silently adopt the new numbers as the target — a *lower* pass count is a regression to investigate,
   not a floor to move.
3. **Anchors are re-resolved by symbol** (`C1`). If a symbol named in a task spec does not exist, the
   block **stops and reports** rather than substituting a neighbour. This is not a formality: the
   validated findings file's own anchors drifted by tens of lines between the audit base and `HEAD`,
   and one earlier validation pass filed a **false finding** by reading anchors against a dirty tree.
4. **Every block's pre-commit check is scoped:**
   `git status --porcelain -- src tests docs pyproject.toml` must show only that block's own edits.
   The scope is narrow **because** the repository has known-dirty paths outside it.

### 7.3 The gap that shapes every verification decision

**`CliRunner()` is module-level with merged streams. `mix_stderr` appears zero times. `create=True`
appears zero times. No test asserts a stream is a terminal.** The suite therefore has **no
stream-discipline oracle at all** — it cannot distinguish stdout from stderr in any command, and
every one of its "no escapes" or "no traceback" assertions is about a **merged** stream.

Three consequences, each with a named compensation:

| Block | What the suite cannot prove | Compensation |
|---|---|---|
| `P13-B6` | that the emitted **bytes** contain no escapes | The two-file `Start-Process -NoNewWindow -Wait -RedirectStandardOutput … -RedirectStandardError …` harness, with `VKDOWNLOADER_LOG_LEVEL` raised so a record is certainly emitted, plus a byte scan of both files — and a **positive** control against a terminal or pty. The in-suite test asserts the renderer's **configuration** only, and says so. |
| `P13-B10` | that the two predicates cannot disagree at any moment | A test that **makes them disagree under the old shape** and requires consistency under the new one. The two existing `force_terminal=True` sites bypass the detection and are explicitly **not** counted as evidence. |
| `P13-B7` | that the suppressed line reaches a destination **without** touching stderr | Two separate assertions: one for the record, one for stderr's emptiness. The second is the compensation; a fix that satisfies the finding by interleaving with the live display is the expected failure mode. |

### 7.4 Per-block verification

| Block | Primary evidence | Independent check (Validator) |
|---|---|---|
| `P13-B14` | Document wording; the two git invocations present in `{BASE_CONTEXT}` | A reader can determine, from the provenance block alone, whether a report is re-verifiable |
| `P13-B15` | Existence check on every referenced path | The exclusion list would in fact stop the census deleting its own instructions |
| `P13-B2` | Option behaviour asserted **in both directions** — supplied changes it, unsupplied leaves env/`.env` reachable; plus `--log-file` is **absent** from both `--help` outputs | The hint is checked against the **captured `--help`**, not against the source string — every option-looking token in it must resolve. Live-1 was a message naming a flag that did not exist. Plus: the reference states the log destination is environment-only (Decision C's residue) |
| `P13-B3` | A real log file, every line parsed as JSON | The parse is done by someone who did not write the fix |
| `P13-B8` | The **value** (`2`) still asserted alongside the new label | Two assertions moved; an independent check that the value is still pinned, not only the label |
| `P13-B16` | `grep` count = **zero**; replacement count = **three** | That the *other* ffmpeg mentions were correctly left alone — the failure mode of an over-broad sweep. **Plus:** that the diff touches none of §1.0's nine permanent symbols (`R8b`). |
| `P13-B10` | Differential measurement, one variable at a time, both predicates before and after `start()` | No moment exists where the repoint decision and the start decision can differ |
| `P13-B5` | Exit **`3`** for out-of-range and **`2`** for non-numeric, **in the same test class**, both commands | **The prohibition first: `grep` both option declarations for `min=`/`max=` — they must be absent** (`R3b`). Then the ceiling-breaker is read from `Settings.max_retries`'s `le`, **from the model field**, not from a literal. The `3`-vs-`2` boundary is checked against **the ruling's table**, not the block's own reasoning |
| `P13-B6` | Two-file byte scan + positive terminal control | The block did not pass by disabling colour everywhere |
| `P13-B9` | A `SKIPPED` entry counted as skipped, not failed — asserted directly against the aggregation | The branch is not proven by asserting an always-zero result |
| `P13-B11` | A stand-in whose `stop()` raises | **Both** raise paths; `R-S` forbids manufacturing a natural reproduction and the docstring says so |
| `P13-B12` | The surviving frame carries a terminal marker | A task that **was** finished keeps its status — the regression this block could introduce |
| `P13-B13` | **Two** tests, one per branch | That the two classes can no longer collapse; one test cannot prove it. **Plus:** that the commit message states the segment path is permanent product surface, so the diagnostic is not read as awaiting a retirement |
| `P13-B17` | The new sibling assertion naming `ffmpeg` in the help, **plus a check that the wording carries the loader/merger distinction** — an operator must not be left believing ffmpeg is no longer required | `TestMethodFfmpegRemoved`'s three assertions remain green **and unweakened**; and the note does not read as "ffmpeg is no longer used" or "ffmpeg support was removed" (§3.18's rejected wordings) |
| `P13-B1` | New exit-status assertions naming **`3`**, both commands | The status **differs** from a failed download's, **all three of `1`/`2`/`3` are distinguishable**, a failed download still exits `1`, and the `1` row no longer lists "configuration error" |
| `P13-B7` | Record assertion + separate stderr-emptiness assertion | stderr is still empty — **Decision B keeps this half**; the three sibling tests are untouched; no batching or rate-limiting was introduced; and the file's formatting was **not** touched (`G0` resolved) |

### 7.5 Oracle register — what exists, what this plan adds, what stays missing

| Oracle | State | Owner |
|---|---|---|
| Preamble failure exit status (`3`) | **ABSENT — the gap Decision A now makes load-bearing.** Nothing asserts it today, because `OUT-001`'s status half was exactly what was open. Added by `P13-B1`. | this plan |
| `3` vs `1` vs `2` mutual distinguishability | **ABSENT** — no test asserts the three codes differ. Added by `P13-B1` (all three asserted) | this plan |
| Out-of-range `--max-retries` → `3` | **ABSENT** — the case exits `1` today. Added by `P13-B5` | this plan |
| Non-numeric `--max-retries` → `2` | **ABSENT** — added by `P13-B5`, so the `3`/`2` boundary is pinned from both sides | this plan |
| The four-code contract as documented (`0`/`1`/`2`/`3`/`4`+ unallocated) in both reference files | **ABSENT** — added by `P13-B1`, via `C5`'s doc-and-code-in-one-commit rule | this plan |
| `OUT-005`'s option-table row | **ABSENT** — `--max-retries` is omitted from both reference tables. Added by `P13-B5` | this plan |
| `--max-retries` range enforcement | **does not exist** — added by `P13-B5` | this plan |
| Option-versus-environment precedence for the new options | **does not exist** — added by `P13-B2` | this plan |
| JSON log parseability | **does not exist** — added by `P13-B3` | this plan |
| Escape sequences in a redirected run | **not testable in-suite** — external harness only, `P13-B6` | this plan, out-of-suite |
| Two-predicate disagreement | **does not exist** — added by `P13-B10` | this plan |
| Dropped non-progress child line | **exists and pins the wrong behaviour** — inverted by `P13-B7`, after plan 11 `B5` | this plan + plan 11 |
| `failed_to_refresh_token` split | **does not exist** — two tests added by `P13-B13` | this plan |
| Batch summary unit | **exists and pins the wrong label** — updated by `P13-B8` | this plan |
| Stream discipline (stdout vs stderr) | **does not exist and is not created** | **remains missing** — recorded, not worked |
| `TestMethodFfmpegRemoved` distinguishing a rejected value from a removed flag | **does not exist** | **remains missing** — `R23` |
| Pipeline working-tree provenance | **does not exist** — added by `P13-B14` | this plan |
| `echo=False` empty-stderr | exists — **must survive** `P13-B7` | plan 11 `B5` |
| **`check_ffmpeg_available` return type + result caching** (`TestFfmpegAvailabilityCheck`, 2 tests) | **exists and is now a PERMANENT-surface oracle** — must be green and unmodified at the end of this plan | **Product Owner (§1.0)** — no block touches it |
| `ffmpeg_not_found` hint text | **no oracle exists** — and none is added here | **plan 16 (`CF-12`)** |
| `B17`'s note text | **cannot be verified by `TestMethodFfmpegRemoved`** — only by the new sibling assertion | `P13-B17` |

### 7.6 Risks requiring out-of-band verification

- **R3 (this plan reproduces Live-1).** Verified by reading `P13-B1`'s commit message: if `P13-B2`
  did not land first, the message must say the message text was not touched. If it says otherwise,
  the commit is rejected.
- **R9 / R10b / R11 (moving baseline, another agent's in-flight diff, dirty tree).** Verified by the
  scoped `git status --porcelain`, the re-measured gate numbers, and — where a whole-tree gate is red
  for a file this plan does not touch — a commit message that **names** the file and does not fix it.
- **CF-1 (three writers in one function).** Verified by reading `setup_logging`'s processor list in
  full after the edit, and by the commit message naming which writer preceded it.
- **CF-2 (`B5` → `B7`).** Verified by `git log` showing plan 11 `B5`'s commit as an ancestor of
  `P13-B7`'s, and by the three sibling `echo=False` tests being byte-unchanged.
- **CF-3 (plan 12's unconstrained route).** Verified by the scoped `git status` showing `cli.py`
  unmodified by anyone else at `P13-B2`'s pre-commit check. If plan 12 has written `cli.py`, `P13-B2`
  waits.
- **CF-7 (`check_ffmpeg_available`) — CLOSED and verified by absence.** The symbol is permanent
  product surface (§1.0). Its verification is now negative and simple: **`P13-B16`'s diff contains no
  reference to it, and `P13-B17`'s contains no change to `DownloadMethod`'s members.** No block
  resolves it, because it is resolved. The supporting oracle — `TestFfmpegAvailabilityCheck`'s two
  tests — must be **green and unmodified** at the end of this plan, since the symbol now has a
  permanent owner and an existing test.
- **CF-12 (`ffmpeg_not_found`'s hint string) — recorded, not written.** Verification is that no task
  spec in §6 lists the hint string as a target. It must appear exactly once in this plan, as a
  **boundary naming plan 16** (§1.0, §4.3, §1.4).

### 7.7 Rollback

Every block is one commit touching one concern. The rollback for any block is `git revert` of that
commit — with two exceptions recorded here rather than discovered later:

- **`P13-B11` + `P13-B12` may be one commit** (the shared-slot criterion in §3.12). If they are, they
  revert together, and `P13-B7` must then re-read `stop()`'s neighbours — it reads `is_enabled`,
  which neither touches, so the coupling is unaffected.
- **`P13-B2` is the only block whose revert has a downstream consequence inside this plan.** `P13-B1`
  and `P13-B17` depend on it; reverting `P13-B2` while either has landed **reintroduces Live-1**, so
  `P13-B2` is reverted last of the three, and `P13-B1`/`P13-B17` revert first.

### 7.8 Definition of done

1. All five gates green at the re-measured baseline, with **759+ passed and exactly 3 skipped**.
2. Every acceptance criterion in the executed task met, with the evidence named in its commit message.
3. **All 12 open decisions recorded as chosen** (`D-3`, `D-4`, `D-5`, `D-7`, `D-9`, `D-10`, `D-11`,
   `D-13`, `D-14`, `D-15`, `D-16`, `D-17` — see §4.5), each with the criterion that chose it. None
   left as "whichever seemed right", none silently resolved.
4. **The five closed decisions honoured and not re-opened**: `D-1` (`3` on both configuration paths),
   `D-2` (`--log-level`, no `--log-file`), `D-6` (**no `min=`/`max=` anywhere on the option**),
   `D-8` (one record per line, stderr clean), plus the ffmpeg ruling. **`R3b`'s prohibition is
   verified by `grep`, not by inspection.**
5. **`CF-7` closed and respected; `CF-12` recorded and not duplicated; `CF-13` honoured.**
   `check_ffmpeg_available` untouched by this plan and its two-test oracle green; the
   `ffmpeg_not_found` hint string named as **plan 16's** boundary exactly once, and written by no
   block here; and `B1`/`B5`'s shared `3` row written once, naming both producers.
6. **CF-5, CF-6, CF-8, CF-11 and the eight-file referral list** carried into the record, none worked
   around: `docs/STRUCT.md` not re-filed, plan 11 `B3`'s two unsatisfiable criteria left for its owner,
   the eight-file surface left to plan 10, `TestMethodFfmpegRemoved`'s three assertions unweakened.
7. Packaging frozensets still **73/32**; no file added or removed under `src/`, `tests/`, `docs/`.
8. **`G0` resolved** (§2.11) — `tests/test_hls_downloader.py` lint- and format-clean; the narrowed
   formatting-only fallback **not exercised**. Any whole-tree gate red from a concurrent agent's
   in-flight file is **reported, not fixed**.