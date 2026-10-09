# Plan 07 — Phase 03 Audit Fixes: Network Resilience

**Source artifact (read-only):** `.ai/audit/99-validation/03-network-resilience-validated-findings.md` (1778 lines).
**Code context (read-only):** `tmp/code_context_phase03.md` (733 lines, produced by the Auditor against the live tree).
**Tree state this plan was composed against:** `HEAD = db9f877`, working tree clean except untracked audit/plans artefacts and `tmp/`.
**Coverage:** 18 product findings `NET-001` … `NET-018` + 2 still-open pipeline findings, in **16 blocks**.

> **Identifier convention — binding on every block and every report in this plan.**
> `VAL-` is a **colliding prefix**. Every per-phase validation run mints `VAL-001…` independently
> and the numbers name different subjects; eleven artifacts in `.ai/audit/99-validation/` do this
> today, and plans 05/06 already shipped the phase-01/02 namespaces. **Every phase-03 `VAL-` id
> in this plan is written `phase03/VAL-NNN`.** An unqualified `VAL-003` in a block report, a
> commit message, or a task id is a defect. Phase 04's mirror claim is `CON-009` in
> `.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md`, which already
> cross-references phase 03's `VAL-001` as adjudicated.

---

## §1 Scope

### §1.1 How this block set was derived

The block set is **not** the artifact's Fix Order. It is the Fix Order re-derived against three
things the artifact could not see:

1. **The tree moved after the artifact was written** (artifact mtime `2026-09-29 12:39`).
   Commits `d62671b`, `19143b1`, `feb0a40` implemented three of the artifact's own pipeline
   recommendations. **Four of the seven phase-03 `VAL-` findings are already fixed.** Planning a
   block for an already-fixed finding would be wasted work and, worse, would re-edit a template
   that now carries the slot.
2. **Three groups of currently-green tests actively pin the defective behaviour.** Under project
   rule 2 these tests are edited *in the same change* as the fix — so the test coupling, not the
   prose overlap, is what forces the block boundaries.
3. **Phases 04–11 have all been validated since.** Phase 07 (`filesystem-artifacts`) and phase 10
   (`test-coverage`) are present and validated and **each owns part of what phase 03 proposes.**
   Both were read; see §1.3.

Grouping rule applied throughout: **two findings share a block only when they share a semantic
anchor *and* the grouping reduces conflict, review surface, or risk.** Every grouping I changed
away from the artifact's Fix Order is justified at the block heading and in §4.4.

### §1.2 IN — every still-open finding

| Block | Findings | Why here | Plan file that would otherwise carry it |
|---|---|---|---|
| **B1** | `NET-001` | CRITICAL, irreversible, alone first, with its test edit | — (this plan) |
| **B2** | `phase03/VAL-001` | CRITICAL-severity finding whose only remaining action is prose | — (this plan) |
| **B3** | `phase03/VAL-004` | the only open pipeline defect in the pipeline documents | **claimed by plan 05 Block 9 (`VAL-110`) which did not land** — ownership moved here, see §1.3 |
| **B4** | `NET-009` → `NET-004` → `NET-002` → `NET-010` | one function, four prescriptions, one test class — `VAL-002` and the test coupling both force a single change | — (this plan) |
| **B5** | `NET-017` | head of the `C3` chain; settles what a quality label may be | — (this plan) |
| **B6** | `NET-016` | pure function, one file, zero existing tests | — (this plan) |
| **B7** | `NET-008` | the captured-address selection surface; research-gated | — (this plan) |
| **B8** | `NET-005` | tail of the `C3` chain; needs B5 and B7 first | — (this plan) |
| **B9** | `NET-003` | the ladder's selector inversion; test-pinning | — (this plan) |
| **B10** | `NET-015` **reduced** | the handoff-asymmetry half only; the `.part` half is phase 07's | — (this plan), reduced per §1.3 |
| **B11** | `NET-006` + `NET-007` | `C2`: shared `download_timeout` surface, must be decided together; **adopts plan 05 Block 8 (`ENT-010`)**, see §1.3 | **duplicate with plan 05 Block 8 (`ENT-010`)** — ownership moved here |
| **B12** | `NET-012` | the URL acceptance gate + four raw-string slicers; research-gated | — (this plan) |
| **B13** | `NET-013` | request-fidelity + verification posture; advisory | — (this plan) |
| **B14** | `NET-014` | the concurrency product; operator-visible semantics | — (this plan) |
| **B15** | `NET-018` | `Retry-After` parsing + ceiling ordering | — (this plan) |
| **B16** | `NET-011` | one comment; the highest ratio item in the corpus | — (this plan) |

**18 `NET-` + 2 `VAL-` = 20 findings, 16 blocks, zero findings unassigned.**

### §1.3 OUT — and where each item went

| Item | Disposition | Where it went, and why |
|---|---|---|
| `phase03/VAL-003` (write/check filename mismatch) | **OUT — already fixed** | `d62671b`. `audit-multi-phase.md` now names `…-validated-findings.md` at both the write and the check step; the `…-validated.md` form appears zero times. Re-editing would risk re-introducing the defect. **No block.** |
| `phase03/VAL-005` (`AGENTS.md` read as mandatory base context) | **OUT — already fixed** | `19143b1`. The step now reads `.ai/context/commands.md`, `.kilo/rules/project.md`, `.kilo/rules/commands.md`; `AGENTS.md` appears zero times. **No block.** |
| `phase03/VAL-006` (no slot for the per-finding decision) | **OUT — already fixed** | `feb0a40`. `.ai/audit/templates/audit-findings.md` now carries `**Decision:** …` between the heading and the field table, plus `decision` / `decision_detail` in the reference table. **No block.** |
| `phase03/VAL-007` (orchestrator orders rejected findings deleted) | **OUT — already fixed** | `d62671b`. The line is gone from `<retry_rules>`, which now holds only the retry cap and the escalation. **No block.** |
| `NET-007` half 2 — "replace the literal `= 300` defaults" | **IN — adopted into B11** | **Decision, not a deferral.** Plan 05 Block 8 (`ENT-010`) claimed the same nine literals and **did not land** (plan 05 stopped after block 6; blocks 7–13 are unstarted). Leaving `NET-007`'s half unowned because a possibly-never-resumed plan claimed it first is exactly the duplicate-ownership failure mode this plan's `VAL-` namespace note exists to prevent. Plan 05 Block 8 already carries a verified acyclicity argument for the `ffmpeg_utils → downloader_throttle` edge; B11 **adopts that argument rather than re-deriving it**. Consequence: **if plan 05 is ever resumed, its Block 8 must be struck and this plan named as the owner.** |
| `NET-007` half 2 (the "wrap the two transfer stages in `wait_for`" clause) | **OUT — withdrawn by the validator** | `ytdlp_downloader.py` carries the decision in prose: yt-dlp holds `--socket-timeout`, `-R`, `--fragment-retries` and `-N`, and "no application-level download timeout is imposed, avoiding premature kill of legitimate long downloads". Wrapping either `process.wait()` re-introduces the premature kill. **Must not be re-derived.** See §5.2. |
| `NET-011` — "skip the JSON branch when `Content-Length` is absent or unparseable" | **OUT — withdrawn by the validator** | It would disable m3u8 discovery for every chunked or streamed JSON response: a functional regression traded for a memory bound the Playwright `Response` API cannot express. B16 ships the comment correction only. |
| `NET-013` — the `throttled_rate` and `max_concurrent_downloads` documentation sub-claims | **OUT — rejected as already-correct-by-design** | `config.py` already scopes `throttled_rate` to yt-dlp in its own description and already records both concurrency levels and their relationship. `NET-014` keeps the *product* as the defect. B13 does not touch either description. **Must not be re-derived.** |
| `NET-007`/`NET-011` — see also the *withdrawn recommendations* table in the artifact | **OUT — not re-derived** | Retained there so a later run does not re-derive them. Any block report that implements one of them is wrong. |
| **`NET-015` — the `output_file` / `output_file.part` probe and cleanup half** | **OUT — duplicate of phase 07 `ART-002`** | **This is a cross-phase duplicate the code context did not identify; it was found by reading phase 07's validated artifact.** `ART-002` (phase 07, HIGH, mandatory, validated) names the *same three statements* — the probe at `ytdlp_downloader.py` `validated_output` predicate, the `DF-008` cleanup, and the `_attempt_segment_resume` `output_file.unlink()` — and recommends the same fix ("point both … at the name the child actually writes, or at the set the child can write"). It is **strictly stronger** than `NET-015` on the same subject: it is HIGH where `NET-015` is MEDIUM, it re-derives the child's own `temp_name()` (`yt_dlp/downloader/common.py`), and it observed the survivor growing across three runs against a loopback origin. Two plans editing three statements is a collision; the weaker finding loses. **B10 ships only the handoff-asymmetry half**, which is unique to `NET-015`: the ffmpeg branch in `perform_download` hands its path to `download_hls_with_resume` with no unlink, while the yt-dlp handoff at `_attempt_segment_resume` does unlink. |
| `NET-001` — the residue of `final_list.txt` and a failed `batch_*.ts` | **OUT — phase 07's subject** | The artifact's carve-out is accepted and is now *named*: `ART-004` (a leftover `batch_NNNNN.ts` is counted as a segment because the `*.ts` glob matches it and the staleness check short-circuits) and `ART-012` (the working set peaks at 3.15×; the `2×` in `_required_merge_bytes` is a heuristic). B1 fixes the *deletion timing*; it does not fix the *residue*. **Do not** extend B1 to exclude `batch_*.ts` from the count — that is `ART-004`'s recommendation and its owner. |
| `NET-001` — the disk-peak arithmetic in `_check_merge_space` / `_required_merge_bytes` | **OUT of B1, IN as a read-only obligation** | B1's change does **not** alter the *peak* footprint (the batch temps already coexisted with the segments inside the same stage window); it widens the *failure* window. So B1 must **re-read** `_required_merge_bytes`' docstring and state in its report whether the invariant it asserts still holds — it must not silently change the `2×`, which is `ART-012`'s subject. |
| `NET-001` — "nothing is recorded at all" | **OUT — corrected by the validator** | `_perform_final_merge` emits `final_merge_failed` and the batch stage emits `batch_merge_failed`. What is true is that nothing states *the whole transfer must be repeated*. B1's logging clause is scoped to that, and to the `count > 0` guard. |
| `NET-006` — "`sock_read` silently truncates a slow download at 60 s" | **OUT — corrected by the validator** | `sock_read` is an **inactivity** ceiling, not a duration ceiling. A slow-but-steady transfer is not killed by it. B11 must not implement a truncation fix. |
| `NET-006` — "at every value `sock_connect` is dead" | **OUT — narrowed by the validator** | It is **redundant**, not unreachable: at the default and the ceiling `connect == sock_connect == 30` and neither strictly shadows the other. B11 removes it because it adds nothing `connect` does not already bound — that is the finding's own wording. |
| `NET-002` — its "which policy table" ambiguity (`408`/`425`) | **NOT resolved here** | `C7`. Named and routed to B4's Planner. See §3 B4 and §5.5. |
| `NET-012`/`NET-008` — the "expected host" constant | **NOT resolved here** | No host constant, allow-list or origin string exists anywhere in the repository. Routed to a **Researcher** in B7 and B12. |

### §1.4 Deferred — explicitly not in this plan

| Deferred item | Owner / trigger |
|---|---|
| `.part` probe and cleanup | **Phase 07's `ART-002`.** Needs its own plan (`08-filesystem-artifacts-audit-fixes.md` or later). B10 must not touch it and must not weaken it. |
| `batch_*.ts` counted as a segment; the `2×` merge heuristic | **Phase 07's `ART-004` / `ART-012`.** |
| `TCPConnector(limit=10)` and the process-wide connection ceiling | **Phase 04's `CON-009`** (advisory). B14 must not touch the literal. |
| The concurrency product's documentation claim (`NET-013` lost it) | **Retained under `NET-014` → B14.** |
| Rendering a non-selectable quality label in operator output | **Phase 08** (`NET-005`, `NET-008` both name it and both decline to file it). |
| Comment/`max()` wording mismatch in `_compute_backoff_delay` | **Phase 09**, named by the artifact and confirmed present. B15 must not fix it. |
| `ProgressManager` deprecation note | Not a phase-03 subject; no production callers, retained for external importers. |
| `.kilo/rules/project.md` rule 12 says `logging.getLogger(__name__)`; the codebase universally uses `structlog` | **Flagged, not fixed.** See §5.4. Changing the rule file is an audit-pipeline change, not a product change; changing the code to match the rule would break the `JSONRenderer`/`ConsoleRenderer` split in `config.setup_logging`. B3 touches `.kilo/agents/*` and **must not** touch `.kilo/rules/project.md`. |

---

## §2 Baseline

### §2.1 The four verification commands — re-run for this plan

```
$ uv run pytest -q -rs
588 passed, 4 skipped in 26.62s                                    EXIT=0

$ uv run ruff check src tests
All checks passed!                                                 EXIT=0

$ uv run ruff format --check src tests
52 files already formatted                                         EXIT=0

$ uv run mypy src
Success: no issues found in 30 source files                        EXIT=0
```

All four re-run by the Planner against the live tree, not copied from the code context.
**The artifact's own baseline (486 passed) is stale** — plans 05 and 06 added 102 tests. Any block
report that quotes 486 is reporting against a dead baseline.

The four skips are **one** Windows gate (`D-11`, owner-only confinement not offered on Windows),
at `tests/test_config.py` and `tests/test_hls_downloader.py` — two sites each. They are not a
phase-03 subject and no block may change their count.

### §2.2 Binding project rules — every block

| Rule | What it binds in this plan |
|---|---|
| **1. English only** | Comments, log event names, docstrings, error text. |
| **2. Production code is king** | The three test groups in §5.1 are edited **because** they pin the defect. A block that cannot make a pinned test pass by fixing the code has misread its finding. |
| **3–4. Separation of concerns / single responsibility** | No block may grow a module past the responsibility it already has. The `NET-006` helper placement (B11) is governed by this. |
| **5. Avoid overengineering** | Every "deferred to Planner" fork in §3 must be resolved to the *simplest* option that closes the finding. A new abstraction needs a stated justification. |
| **7. Follow existing patterns** | `DownloadPolicy`, `SegmentTask`, `FfmpegProgress` are dataclasses; every log call is `logger.<event>(key=value)`; every new constant is a `StrEnum` member. |
| **9. Type safety** | `mypy strict` is on with one override (`vkdownloader.cli`). No `any`. |
| **10. `StrEnum` for all constants** | **`NET-008`'s `"unknown"` quality label is a direct hit on this rule** — a new literal would be a rule 10 violation. Same for any new status, tag or mode any block introduces. Never a dict, never a bare literal. |
| **11. Pydantic** | A new setting is a `Settings` field with a `Field(...)` description, not an env read. |
| **12. No `print()`** | **Read the trap: this rule's *text* prescribes `logging.getLogger(__name__)`, and the codebase universally uses `structlog`.** Every module does `from structlog import get_logger` then `logger = get_logger(__name__)`. A block that follows the rule text and imports stdlib `logging` breaks `config.setup_logging`'s renderer split. **Follow the code, not the rule text** — see §5.4. |
| **13. Migrations for schema changes** | No schema change in this plan. |
| **14. Documentation stays current** | `docs/11-guides/configuration.md` is edited by B11 and B15; `.env.example` by B11. |
| **15. Small modules and functions** | B4 is the one block that cannot be made smaller without breaking `VAL-002`; that is stated at the block, not waived silently. |

### §2.3 Repository constraints every block must respect

- **Layering is one-directional and acyclic**: `cli → services → infrastructure`; `services → models | utils | config | exceptions`; `models` and `utils` depend on nothing. Inside `services/` the sibling DAG is a strict DAG.
  - `ffmpeg_utils.py` imports **only** `..exceptions` and `..utils.formatting`. It imports neither `downloader_throttle` nor `config`. Any B11 change that gives `ffmpeg_utils` a new import is a **new edge** — plan 05 Block 8 proved `ffmpeg_utils → downloader_throttle` is acyclic, and B11 adopts that proof, but it must not add a second new edge in the same change without re-arguing.
  - The single deliberate violation is a function-scope lazy import in `infrastructure/browser.py` (commented as avoiding `browser.py → services.__init__ → downloader → extractor → browser`). **Do not add a second, and do not remove this one as a side effect.**
- **`downloader.py` is a backward-compat re-export facade** over 11 sibling names under `# noqa: F401`. `NET-003`, `NET-013` and `NET-015` must be implemented in the **owning** module, never in that import block.
- **`tests/test_packaging.py`'s `EXPECTED_SDIST_ENTRIES` is a hard gate.** Any new file under `src/` or `tests/` requires editing that frozenset in the same change. **Only B11 has a plausible reason to add a `src/` module.**
- **`tests/conftest.py` has an `autouse` fixture, `isolate_settings_source`**, that chdirs to `tmp_path` and deletes every `VKDOWNLOADER_*` for the duration of each test. Any new test that reads `.env` or the environment must work inside it. The `test_settings` fixture carries **`max_retries=1`** — a test that drives a retry loop through it gets a single attempt. `download_timeout` there is the schema default.
- **There is no `aiohttp` session fixture, no ffmpeg-subprocess fixture and no fake clock.** Every network-touching test builds its own `MagicMock` session inline; `tests/` contains **zero** occurrences of `aiohttp`, `ClientTimeout`, `TCPConnector`, `ClientSession`, `ssl.`, `CERT_NONE` or `check_hostname`. **No verification step in this plan may require network access.**
- **A new `Settings` field has no CLI option today** (`download_timeout` has none). Plan 05 Block 2 reshaped the option pattern: `int | None` with a `None` default, folded into a conditional-overrides mapping — a new option that is not `None`-defaulted silently shadows the `.env`.
- **Decision-carrying comments are the house style** (`D-01`, `D-04`, `D-10`, `D-11`, `D-12`, `INT-003`, `SEC-001/002/003`, `DF-003/006/008/010`, `TRN-001`, `SRV-006`). A block that changes behaviour **must update the tag comment that justifies the old behaviour**. Named survivors: the yt-dlp "no application-level download timeout" decision, `D-01`'s non-reentrant-semaphore invariant, `DF-008`'s partial-file cleanup, `D-12`'s browser-extraction body.

---

## §3 Blocks

Sixteen blocks. Each is one commit. **Read only the block you are handed** — §3 is
self-contained per block; §4 is needed only if you are scheduling.

---

### B1 — Make the batched merge non-destructive until the whole merge has succeeded

**Findings carried:** `NET-001` — CRITICAL · RUNTIME-ERROR · mandatory.

**Why alone, why first.** The only irreversible loss in the catalogue: 0 of 250 originals survive
a failed final merge, and 0 of 150 survive a failed first batch. It breaks a currently-green test,
and it sits on the disk-footprint assumption `_required_merge_bytes` documents. Nothing else in
this plan destroys data.

**Grouping.** Solo. It shares no semantic anchor with any other finding (its four anchors are
unique to it), and splitting it would leave the fix in a state that is *worse* than the defect —
partial deletion deferral still destroys inputs if the surviving half lands first.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ffmpeg_utils.py` | `_merge_batch_segments` | Stop unlinking the batch's input segments (and its concat list) on success. The batch stage becomes additive. |
| `services/ffmpeg_utils.py` | `_perform_final_merge` | Take ownership of deleting the input segments: on its **success** path, remove every input segment and every batch temp, then the final list. On its failure path, remove **nothing**. |
| `services/ffmpeg_utils.py` | `_merge_segments_batched` | The `finally` that unlinks every accumulated temp must be narrowed to the success path only. A stage failure must leave the already-merged batch temps on disk. |
| `services/ffmpeg_utils.py` | `_required_merge_bytes`, `_check_merge_space` | **Read-only obligation.** Re-read the docstring's invariant ("the segments *and* a full copy of them at the same time") and state in the block report whether it still holds. **Do not change the `2×`** — that is phase 07's `ART-012`. |
| `services/segment_downloader.py` | `_log_preserve_segments` | Report unconditionally, `count == 0` included, so "nothing was kept" is *stated* rather than inferred. The reporter must not be able to enumerate a failed `batch_*.ts` as a kept segment — but **excluding `batch_*.ts` from the count is `ART-004`'s change, not this block's**; this block only removes the `count > 0` gate. |

**Acceptance criteria**

1. A batched merge whose **final** stage fails leaves **every** original segment on disk, and the log states the preserved count.
2. A batched merge whose **second batch** stage fails leaves the segments of the failed batch **and** the already-produced `batch_*.ts` temps on disk. (Today: 150 of 250 survive and the temps do not.)
3. A batched merge that **succeeds** removes every input segment, every batch temp and the final list — the current success-path behaviour is preserved exactly.
4. `_log_preserve_segments` emits its record for a directory containing zero segments.
5. `_check_merge_space` is unchanged, and the block report states whether `_required_merge_bytes`'s docstring invariant still holds after the change.
6. The block does **not** exclude `batch_*.ts` from any glob, does **not** change the `2×`, and does **not** delete a `final_list.txt` on the failure path.
7. `tests/test_ffmpeg_utils.py::TestPerformFinalMerge::test_final_merge_removes_temp_files` and `::test_final_merge_removes_final_list` stay green **unchanged**.

**Tests — the one group that must be edited in this same change**

- **EDIT** `tests/test_ffmpeg_utils.py::TestMergeBatchSegments::test_merge_batch_removes_input_files_on_success` — this test *asserts the defect as the contract* (`assert not segment1.exists()` after a successful batch stage). Per rule 2 it is re-scoped, not deleted: it must now assert that a successful **batch** stage leaves its inputs in place, with a docstring saying why. A second test in the same class asserts the **final** stage is what removes them.
- **ADD** `tests/test_ffmpeg_utils.py` — a `_merge_segments_batched`-level test: final-stage failure ⇒ all inputs survive; second-batch failure ⇒ failed-batch inputs **and** earlier temps survive; success ⇒ everything is cleaned. Drive it with a local stub standing in for the process launch (the artifact's method), never with a real ffmpeg and never with a network call.
- **ADD** `tests/test_segment_downloader.py` (or `test_hls_downloader.py`'s segment-preservation area, which already exists at two sites) — a `_log_preserve_segments` test asserting a record for an empty directory.

**Dependencies:** `depends_on: []`. It blocks B11 (`C5`).

**Risk class: HIGH.** Irreversible-data-loss subject; breaks a green test; sits on a documented disk
invariant; boundary with phase 07.

**Agents required: Auditor, Researcher, Planner, Validator — all four.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "What exactly survives, today, in each of the three failure shapes — read from the code, not inferred from the finding's prose?" The artifact measured this; the tree has not moved in this file, but the re-derivation is the block's ground truth. |
| Researcher | **YES** | "Does phase 07's `ART-004` / `ART-012` constrain the change in a way the finding does not state — specifically, does a wider failure window collide with a residue sweep, a free-space probe, or a cleanup path that would now see a `batch_*.ts` it did not previously see on a failure?" Both artifacts are in-repo; the question is a cross-artifact read, not external research. |
| Planner | **YES** | "What is the exact new scope of the `finally`, and where does the input-segment deletion live?" Three shapes (delete-in-`_perform_final_merge`, delete-in-`_merge_segments_batched`'s success tail, or a caller-side sweep). **Deferred to this block's Planner** — see §3.1. |
| Validator | **YES** | "After the change, does every failure shape leave a recoverable working tree, and does the success path clean up completely?" The failure mode of a partial fix is a *worse* state than the defect, and no existing test can see it. |

#### §3.1 Decisions B1 explicitly does **not** make

**The exact ownership boundary between `_perform_final_merge` and `_merge_segments_batched` for
deleting input segments.**
- (a) `_perform_final_merge` receives the original segment paths and deletes them itself on
  success. *Pro:* the deletion sits where the "whole merge succeeded" knowledge already is; one
  place owns the success path. *Con:* it widens `_perform_final_merge`'s signature and its
  responsibility, against rules 3 and 4.
- (b) `_merge_segments_batched` retains ownership and deletes the originals on its own success
  tail, after the final merge returns true. *Pro:* smallest signature change, mirrors today's
  structure. *Con:* the knowledge "the whole merge succeeded" leaks one level up.
- (c) The caller (`segment_downloader.py`'s merge hand-off) sweeps. *Pro:* keeps `ffmpeg_utils`
  unchanged in shape. *Con:* puts a per-request decision in the wrong module and re-derives what
  the batch count already knows.
→ **Deferred to B1's Planner.** Rule 5 favours (b); rule 3 favours (a). The Planner must state
which and why, and must not introduce a new abstraction to reconcile the two.

---

### B2 — Correct the cross-phase connection-ceiling figure in the source report

**Findings carried:** `phase03/VAL-001` — CRITICAL · SPEC-DEVIATION · mandatory.

**What is actually left.** The validated artifact's own `NET-014` Description **already carries the
correction**; phase 04's `CON-009` carries the correct figure (`4 × 10 = 40` at the default) and
cross-references this finding as adjudicated. The wrong figure survives in exactly one place — the
read-only source report `.ai/audit/03-network-resilience/findings.md`, in `NET-014`'s own
consequence text.

**Semantic anchors owned**

| File | Semantic unit | Change |
|---|---|---|
| `.ai/audit/03-network-resilience/findings.md` | `### NET-014` → the consequence paragraph | Restate: the `TCPConnector(limit=10)` literal is **per download**, not process-wide; the aggregate is `10 × max_concurrent_downloads`; **no process-wide bound exists**. Cross-reference `CON-009` as the owner of the literal and retain the seam both findings already declare. |
| `.ai/audit/99-validation/03-network-resilience-validated-findings.md` | — | **MUST NOT BE TOUCHED.** It already records the correction. Any diff here is a defect in this block. |

**The decision this block requires, stated once.** The validation phase's own contract and its
closing line both say the source report *"was read only and is unmodified"*. **This block
deliberately breaks that invariant**, and the only reason it may: the file is a record of what was
*claimed*, and leaving a known-wrong cross-phase figure in it is precisely what `phase03/VAL-001`
was filed to prevent. The block report must (i) name the invariant it breaks, (ii) cite the
authority for the corrected figure, and (iii) confirm the validated artifact is byte-identical
before and after.

**Acceptance criteria**

1. The source report no longer asserts that the connector is a process-wide ceiling of 10, or that the product `4 × 4 = 16` is bounded by it.
2. The corrected statement matches phase 04's `CON-009` verbatim in substance: per-download ceiling, `10 × max_concurrent_downloads` aggregate, no process-wide bound.
3. The seam is retained: `CON-009` is cross-referenced as the owner of the literal; this block does not claim the literal.
4. `.ai/audit/99-validation/03-network-resilience-validated-findings.md` is **byte-identical** before and after (`git diff --exit-code` on the path).
5. Nothing under `src/` or `tests/` is touched.
6. No `NET-` finding's ID, severity, type or classification in the source report is altered — only the one consequence paragraph's arithmetic.

**Tests:** none. Prose. There is no test that can see a `.md` file; the Validator's read is the gate.

**Dependencies:** `depends_on: []`. **No other block depends on it** — B14's commit body cites the
*validated artifact's* `NET-014` Validation Note (which already carries the corrected figure
verbatim), not this block's output, so B14 is not serialised behind a document edit.

**Risk class: LOW (code) / MEDIUM (process).** The risk is not the edit; it is an agent touching
the validated artifact or the source report's finding metadata out of tidiness.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The defect and the correction are both quoted in the validated artifact; there is nothing to re-derive. |
| Researcher | no | No external system. |
| Planner | **YES** | "What is the exact replacement text, and what invariant is being broken?" Authoring the replacement so it matches `CON-009` in substance is a judgment about a cross-phase contract, not a copy. |
| Validator | **YES** | "Is the validated artifact byte-identical, and does the corrected figure match the adjudicated one?" A prose change with no oracle needs an independent read. |

---

### B3 — Add the missing finding label to the validator's role file, and reconcile the unlaunchable executor

**Findings carried:** `phase03/VAL-004` — MEDIUM · SPEC-DEVIATION · mandatory.

**Ownership decision — stated, not defaulted.** This work is **also claimed by plan 05 Block 9
(`VAL-110`)**, which targeted exactly this and **did not land** (plan 05 stopped after block 6).
B3 **adopts it here**. Rationale: it is the only open pipeline defect in the phase-03 corpus apart
from B2's prose correction; it is a three-line document edit that conflicts with nothing; and plan
05 Block 9 already carried the substance (its decision `D3` and the "do not restamp existing
reports" rule), so this is an adoption, not a re-design. **If plan 05 is resumed, its Block 9 must
be struck and this plan named as the owner** — the same rule that applies to `ENT-010` in §1.3.

**Semantic anchors owned**

| File | Semantic unit | Change |
|---|---|---|
| `.kilo/agents/validator.md` | the two places the type labels are enumerated | Add `RUNTIME-ERROR` to both, so the list matches the format's four-label enumeration. |
| `.kilo/agents/auditor.md` | the type-label list | Same addition. |
| `.ai/audit/templates/audit-findings.md` | frontmatter `agent:` and the `**Executor:**` header | Reconcile `audit-executor` with the role the pipeline actually launches. Plan 05's `D3` resolved this in favour of the **launched** role (`auditor` is the phase launch; `validator` is the validation launch) over the unreachable one. **B3 adopts `D3` verbatim and does not re-open it.** |
| `.ai/audit/*/findings.md` (the four existing reports) | the `**Executor:** audit-executor` line | **Do not restamp.** Those files are a *record* of what ran, not a defect. |
| `.kilo/rules/project.md` | — | **MUST NOT BE TOUCHED** — see §5.4. B3 edits agent role files; it is not a product-rule change. |

**Acceptance criteria**

1. `RUNTIME-ERROR` appears in **both** label lists in `.kilo/agents/validator.md` and in the list in `.kilo/agents/auditor.md`, and each list has exactly the four labels the format defines.
2. No other label in any of the three files is added, removed or reordered.
3. `audit-executor` appears **zero** times in `.ai/audit/templates/audit-findings.md` after the change, and the role it now names exists in `.kilo/agents/`.
4. The four existing `.ai/audit/*/findings.md` files are **byte-identical** before and after.
5. `.kilo/rules/project.md` is byte-identical before and after.
6. `.ai/audit/templates/audit-findings.md`'s **decision slot** — added by `feb0a40` — is untouched and still present, and the `<validation_note>` position it defines is unchanged.
7. The orchestrator's launch sites in `.kilo/commands/audit/audit-multi-phase.md` are byte-identical before and after.

**Tests:** none. Document-only. No test can see a `.md` file.

**Dependencies:** `depends_on: []`. Touches no `src/` file and cannot conflict with any product block.

**Risk class: MEDIUM (process).** Not a code risk at all; the risk is a well-meaning agent
"fixing" the four existing reports' executor stamp, or re-adding a field to the template that
`feb0a40` already gave a slot.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The two label lists and the two executor names are quoted in the finding and were re-verified against the live tree. |
| Researcher | no | The role roster is a directory listing. `D3` is already decided by plan 05. |
| Planner | **YES** | "Which of the two launch sites or the format is the defective side?" The answer is carried from plan 05's `D3`, but the adoption and the do-not-restamp rule must be written down as this block's decision, not assumed. |
| Validator | **YES** | "Is every label list now exactly the format's four, does the named role exist, and are the five files that must not change byte-identical?" Three of the seven criteria are negative and no oracle exists for any of them. |

---

### B4 — Give the manifest layer a retry policy, the address it actually used, and the shared pause

**Findings carried:** `NET-009` → `NET-004` → `NET-002` → `NET-010` (in that intra-block order).
MEDIUM/HIGH · `SPEC-DEVIATION` / `RUNTIME-ERROR` · all mandatory.

**Why one block — three independent reasons.**

1. `phase03/VAL-002`: four accepted recommendations prescribe edits inside one 41-line function,
   two of them on the same two lines. Applied independently, in either order, at least one edit
   lands on a line another has already moved. The artifact's own instruction: land them as **one**
   change, or `NET-004` first and the other three together.
2. **The test coupling forces it.** `tests/test_segment_downloader.py::TestFetchPlaylistWithRetry`
   is 5 tests, all on this function, and **all five** are edited by this block. Splitting the block
   means two commits each editing the same test class, with one of them asserting a contract the
   other has already changed.
3. **`C1` has no other resolution.** `NET-009` must precede `NET-002` (or the block must absorb
   `NET-009`'s change to the shared notifier). There is no ordering of separate blocks that avoids
   re-touching `_notify_backoff_for_retryable_status` from two commits.

**This is the largest block in the plan and that is a finding, not a planning failure.** The
function is the single densest convergence point in the corpus. Rule 15 would prefer smaller
functions; `phase03/VAL-002` and the test coupling prefer one change. **The block must not
re-split it, and must not respond by extracting new helper modules** — that would put a
`segment_downloader` → new module edge into a change that is already touching five call shapes and
five tests. If the block finds itself extracting a helper, it must justify it against rule 5
explicitly in its report.

**Semantic anchors owned**

| Module | Semantic unit | Finding | Change |
|---|---|---|---|
| `services/segment_downloader.py` | `_notify_backoff_for_retryable_status` | `NET-009` | The key becomes the **origin under pressure**, not the page URL; the `10.0` literal becomes derived. Its only caller (`_run_parallel_download_with_backoff`) and every other caller change with it. |
| `services/downloader_throttle.py` | `URLBackoffCoordinator.pause`, `.wait_if_paused` | `NET-009` | The key parameter is renamed to name what it now keys on. Its `str` type is unchanged. Three call sites: this module's own, the segment layer's, the yt-dlp ladder's. |
| `services/segment_downloader.py` | `_fetch_playlist_with_retry` | `NET-009`→`NET-004`→`NET-002`→`NET-010` | **Signature:** gains a `backoff_coordinator` parameter. **Return contract:** carries the address the manifest actually succeeded from, alongside the playlist text. **Status branch:** the retryable set gets the same policy table the media-part layers use — computed delay via `_compute_backoff_delay`, awaited via `_wait_with_shutdown`, shared pause notified, **status logged on every non-200 outcome**. 403/410 stay on the refresh path. **Transport branch:** the bare `continue` gains a delay and notifies the shared pause. |
| `services/segment_downloader.py` | `_is_retryable_status`, `_should_continue_on_retry`, and the module constant `RETRYABLE_STATUS_CODES` | `NET-002`/`NET-010` (`C7`) | **Three predicates exist and are not unified.** The block resolves this explicitly — it must not let two sub-edits each "add a predicate". |
| `services/downloader_throttle.py` | `_retry_429_with_backoff` | `NET-010` | Apply `_should_continue_on_retry` (or its equivalent) so the **final attempt does not sleep**; make a transport-level failure retry to the same `max_retries` budget the parallel strategy uses instead of returning `None` on the first `except`. |
| `services/segment_downloader.py` | `_download_segment_sequential` | `NET-009` | Gains the coordinator parameter and consults the shared pause — the strategy documented as the anti-detection mode (`max_concurrent_downloads == 1`) currently delays but does not **share**. |
| `services/segment_downloader.py` | `DownloadPolicy` | `NET-009` | Carries the coordinator (and whatever the pause key needs) to the parallel path. |
| `services/segment_downloader.py` | `_run_download_session` | `NET-004` | Builds `DownloadPolicy.m3u8_url` from **the address the manifest came from**, not the original argument. |
| `services/segment_downloader.py` | `_handle_token_refresh` | `NET-004` | **Ordering obligation:** the in-place `headers["Cookie"]` rewrite must not land before the base is switched. Getting this order wrong sends a fresh credential to the stale host — the exact thing `NET-004` is about. |
| `services/extractor.py` | the in-process extraction entry point | `NET-009` | Consults the shared pause before its first request. The artifact explicitly disclaims moving the library thread's own timeout semantics — **this block must not touch that.** |
| `services/ytdlp_downloader.py` | `download_with_ytdlp_with_resume_fallback` | `NET-009` | The one `wait_if_paused` call there is re-keyed to match. **No other statement in that function is in scope** (see `C9`). |

**Acceptance criteria**

1. A 429/5xx/408/425 on the manifest request is retried up to `max_retries` with a computed, interruptible delay, **notifies the shared pause**, and the status is present in a log record on every non-200 outcome.
2. A 403 or 410 still enters the refresh path and still succeeds against the refreshed address when the extractor answers.
3. A status outside the retryable set returns `None` after one attempt, and the status is recorded.
4. A transport-level failure on the manifest request is retried with a **non-zero** measured delay.
5. When a refresh succeeds, the media parts are requested against **the refreshed base address**, and the refreshed cookie is written **after** the base is switched — verified by asserting the order, not by reading it.
6. When no refresh occurs, the parts resolve against the original address (unchanged behaviour).
7. The shared pause is consulted at the **manifest** site, at the **sequential** site, and at the in-process extraction site, and is set at all of them; the key it is keyed on names the origin, and the duration is derived, not the `10.0` literal.
8. `_retry_429_with_backoff` performs **no** wait after its final attempt, and retries a transport-level failure to the same budget as the parallel strategy.
9. The two media-part strategies agree on whether a transport-level failure is retried, and both produce a non-zero inter-request gap for one.
10. `tests/test_segment_downloader.py::TestFetchPlaylistWithRetry`'s two positional patches of `_fetch_single_playlist` and `_handle_token_refresh` **still work unchanged** — those two helpers' signatures are not touched by this block.

**Tests — the second group that must be edited in this same change**

- **EDIT all 5** in `tests/test_segment_downloader.py::TestFetchPlaylistWithRetry`. Each pins a
  different part of the defect: `test_token_refresh_runs_on_403_then_retry_succeeds` asserts
  `result == playlist` (a bare string — `NET-004`'s return contract) and asserts the fetch list;
  `test_no_refresh_when_status_not_403_or_410` asserts 404 ⇒ `None` with **no retry**
  (`NET-002`'s subject); `test_refresh_failure_falls_through` asserts **`fetch_count == 1`**
  (asserting the loop does not retry); `test_no_refresh_and_no_retry_when_extractor_missing`;
  `test_token_refresh_runs_on_410_then_retry_succeeds`. Per rule 2 all five are re-scoped, none
  deleted.
- **EDIT (conditionally)** `tests/test_downloader_throttle.py::TestRetryableStatusCodes` —
  `test_excludes_non_retryable_codes` asserts the exact current composition. **Only if** the block
  widens the set (see §3.2 decision 4). If it uses a manifest-local set instead, this test is
  untouched and a new test pins the manifest set.
- **ADD** `tests/test_segment_downloader.py` — the retryable statuses each produce N attempts and
  a non-zero gap; the coordinator receives a `pause` call on a retryable status and a
  `wait_if_paused` consult at the sequential and manifest sites; the returned base address is the
  refreshed one; the `headers` rewrite is ordered after the base switch.
- **ADD** `tests/test_downloader_throttle.py` — the sequential strategy retries a
  `ClientError`/`TimeoutError` to the same budget; the final attempt sleeps zero seconds.
- Compatible and must stay green unchanged: `test_max_retries_exceeded_returns_none`
  (`NET-010`'s change removes a *sleep*, not a request).

**Dependencies:** `depends_on: []`. It blocks B15 (`C12`).

**Risk class: HIGH.** Changes a **return contract** of a function two callers consume and five
tests patch; requires an ordering decision between the base switch and the credential write;
`C7` is an unresolved predicate ambiguity; the block spans five modules.

**Agents required: all four.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "Re-derive the manifest layer's behaviour per status, per transport failure, and per refresh outcome, against the current tree — and confirm which of the five test assertions are pinning which prescription." The artifact's table is the ground truth but the block rewrites exactly the lines the table describes. |
| Researcher | **YES** | "Is there a precedent in this repository for a value that must reach a module that does not import the module that owns it — and specifically, does the `contextvars` pattern already used for `get_shutdown_event` apply to the coordinator, or is the coordinator genuinely per-batch-scoped such that it cannot?" This is an in-repo pattern question, not external research. |
| Planner | **YES** | Four forks, all listed in §3.2. This block must not proceed with any of them silently chosen. |
| Validator | **YES** | "For every status in the policy table and for the refresh path, does the request count, the recorded status, the coordinator call and the returned base address match the criteria — and do all five re-scoped tests assert the *new* contract rather than a weakened one?" The failure mode is a test that was edited to pass. |

#### §3.2 Decisions B4 explicitly does **not** make

1. **The return shape of `_fetch_playlist_with_retry`** (carries the refreshed address).
   A 2-tuple `(playlist_text, base_url)`; a small frozen dataclass; a `NamedTuple`.
   *The artifact says "a tuple".* But the house pattern for internal DTOs is a **dataclass**
   (`SegmentTask`, `DownloadPolicy`, `FfmpegProgress`), and a two-field tuple that five tests
   destructure is the shape most likely to be misread. Rule 5 (avoid overengineering) argues for
   the tuple; rule 7 (follow existing patterns) argues for the dataclass. **Deferred to B4's
   Planner.**
2. **The retryable-status set for the manifest layer** (`C7`). The media-part layers use
   `{429, 500, 502, 503, 504}` — which **excludes** `408` and `425`, yet `NET-002`'s
   recommendation names them. Three options: (a) widen `RETRYABLE_STATUS_CODES`, which changes the
   **sequential** layer's behaviour too and is a deliberate edit of
   `test_excludes_non_retryable_codes`; (b) a manifest-local set, which leaves the three layers
   disagreeing — in the *opposite* direction from today; (c) leave 408/425 unretried and correct
   the recommendation, which closes nothing the finding asks for. **Deferred to B4's Planner.**
   Whichever is chosen, the block must state the resulting per-status behaviour as a table.
3. **The pause key.** (a) The `netloc` of the resource about to be requested — fully observable,
   no external constant, and strictly more coordinating than today. (b) A canonicalised
   registrable domain of that netloc — more coordinating, but introduces a public-suffix notion
   the repository does not have. (c) The expected-CDN-suffix root — **blocked on B7's research**;
   B4 must not wait for it and must not use a guessed suffix. **Deferred to B4's Planner**, and
   the Planner must prefer (a) unless it can name the reason (b) is better *without* B7's answer.
4. **Where the in-process extraction's coordinator comes from.** (a) A constructor parameter on the
   extractor class — but the extractor is constructed per-download and the coordinator is
   per-batch. (b) A per-call parameter threaded down the extraction chain. (c) A `contextvars`
   binding alongside `get_shutdown_event` — **the codebase already uses exactly this pattern**
   (`downloader_throttle.py`'s `ContextVar`, loop-safe, created on first use per context) and it
   is the only one of the three that crosses the per-batch / per-download scope boundary without a
   signature change on every frame. **Deferred to B4's Planner.** No Researcher gate: the pattern
   is in the repository and the Researcher question above is what settles whether it applies.
5. **Where the pause duration comes from.** (a) A new bounded `Settings` field. (b) Deriving it
   from an existing field. (c) A module constant derived by reflecting over the settings schema at
   import time — `downloader_throttle.py` already does this for `_DEFAULT_DOWNLOAD_TIMEOUT`, but
   that constant is frozen at first import, which is a real defect for a value an operator can
   change. **Deferred to B4's Planner.** If (a) is chosen, §2.3's CLI-option rule applies.

---

### B5 — Read the stream's format by its parsed path, and rank a placeholder height as absent

**Findings carried:** `NET-017` — LOW · RUNTIME-ERROR · mandatory.

**Why first in the `C3` chain.** `NET-017` settles *what a quality label may be*, which is the
precondition for `NET-008` adding a member to the enumeration and for `NET-005` recording which
label it chose. It is the smallest of the three, it breaks no existing test (verified:
`test_build_streams_detects_hls_format` / `detects_mp4_format` are suffix-clean;
`test_build_streams_quality_unknown_without_height` and
`test_get_fallback_stream_handles_none_height` use no height at all), and its two anchors sit in
different modules from either of the other two.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/extractor.py` | `_build_streams` — the audio filter | The filter currently tests `f.get("vcodec") == "none"`, which excludes one literal and cannot distinguish "no codec key" from "video". Replace with a presence rule (**§3.3**). |
| `services/extractor.py` | `_build_streams` — the format classifier | Classify on the **parsed path's** suffix, not a substring over the whole reference. A progressive address whose *query* carries `.m3u8`, or that lives in a *directory* named with it, is currently misclassified `hls`. |
| `services/extractor.py` | `_build_streams` — the quality label | `height <= 0` is treated as absent, not as present. |
| `services/quality.py` | `QualitySelector._get_fallback_stream`, `QualitySelector.select` | The two ranker keys — `max(..., key=(s.height is not None, s.height or 0))` and `min(..., key=(s.height is None, s.height or 0))` — are **mutual inverses** and both rank `(True, 0)` above `(False, 0)`, so a set of `{height=0, height=None}` returns the *same* record for `best` and `worst`. They must stop being inverses on a placeholder value. |
| `services/quality.py` | `QualitySelector._find_quality_match` | Must accept whatever label `_build_streams` can now produce — including the heightless one. |

**Acceptance criteria**

1. A progressive address whose query string contains `.m3u8` is classified `mp4`, not `hls`.
2. A progressive address in a path segment named `*.m3u8` is classified `mp4`, not `hls`.
3. An HLS address whose query string carries `.mp4` is classified `hls`.
4. A record with `height = 0` produces the same label as a record with no height.
5. From the set `{height=0, height=None}`, `best` and `worst` do **not** return the same record.
6. A record with no `vcodec` key is not offered as a video stream **under the chosen rule**, and the rule is stated in the block report (see §3.3).
7. `list_available_qualities` output is unchanged for the existing 9 members, and every label it emits is accepted by `_find_quality_match`.
8. Every existing `TestBuildStreams` case and every `test_quality_selector.py` case stays green **unchanged**.

**Tests**

- **ADD** `tests/test_extractor.py::TestBuildStreams` — the two misclassification shapes (query-carries, directory-carries), the query-carries-`.mp4` counter-case, and the `height=0` label.
- **ADD** `tests/test_quality_selector.py` — a `{0, None}` set for `best` and for `worst`, asserted **separately** so a regression that re-inverts them fails one assertion, not both.
- Compatible, must stay green unchanged: `test_build_streams_detects_hls_format`,
  `test_build_streams_detects_mp4_format`, `test_build_streams_quality_unknown_without_height`,
  `test_get_fallback_stream_handles_none_height`.

**Dependencies:** `depends_on: []`. Blocks B7, B8 (`C3`), B12 and B13 (`C8`).

**Risk class: MEDIUM.** LOW severity, but it is the head of the most contended chain in the
corpus, and the ranker change is the one place where a wrong fix silently changes every quality
selection the product makes.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The eight-record table and the two ranker answers are quoted in the finding and were re-derived against the live tree. |
| Researcher | no | No external system. The parsed-path-suffix approach uses `urllib.parse`, already used in the codebase. |
| Planner | **YES** | §3.3 — the presence rule is genuinely underdetermined in the finding. |
| Validator | **YES** | Criteria 1–5 are all "the wrong shape must now be the right shape" assertions; a block that weakened an existing test to pass would satisfy the gate without satisfying the finding. |

#### §3.3 Decision B5 explicitly does **not** make

**The concrete rule that replaces "exclude a record that is neither video-bearing nor explicitly
audio-only".** As phrased it is **unimplementable**: the code cannot know whether a record with no
`vcodec` key is audio. The validator narrowed the claim to "the filter cannot express the
distinction". Candidate rules: (a) require `vcodec` to be **present** (drop records that omit it
— changes the survival rate for any origin that omits the key); (b) require `height` **or** `width`
to be present (a video-bearing proxy; drops audio-only records by a different test and agrees with
the classifier's intent); (c) require `vcodec` present **and** not `"none"` (strictest; drops
records the origin may legitimately omit). (a) and (b) can disagree; (b) and (c) can disagree.
Each has a different blast radius against a real origin, and **this plan asserts nothing about what
a real VK origin returns.** **Deferred to B5's Planner**, which must state the chosen rule, its
counter-examples, and why the rejected rules are worse.

---

### B6 — Make the address normaliser stop inventing a host

**Findings carried:** `NET-016` — LOW · RUNTIME-ERROR · mandatory.

**Scope decision, stated.** The finding has three clauses. Two are unambiguous. The third —
"resolve a root-relative address against the page's own origin" — the code context flags as
requiring research (§6.3), on the ground that the correct base for a JSON body's relative `hls`
value is the **API** origin, not the page origin, and that a `Response.url` is always absolute so
the response path never produces a relative value at all. **B6 resolves this by dropping, not
resolving** (see below), which closes the finding's substance without the research. The
"which base is correct" question is therefore a **deferred option, not a deferred requirement** —
it is only live if the block revisits the drop/resolve choice, and revisiting it then requires a
Researcher.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `infrastructure/network_monitor.py` | `NetworkMonitor._normalize_url` | Delete the unreachable branch: a string starting with `//` necessarily starts with `/`, so the `startswith("/")` test already caught it and the following `startswith("//")` arm is dead by control flow, not by counting. Stop promoting a bare relative path to a host — `a/stream.m3u8` currently becomes `https://a/stream.m3u8`, a host named `a`. Drop any candidate that does not resolve to an absolute `https://` address. |
| `infrastructure/network_monitor.py` | `NetworkMonitor._extract_urls_from_json` | Must not append a value the normaliser could not resolve. A JSON value of `720/stream.m3u8` currently normalises to `https://720/stream.m3u8` and is appended as a discovered address. |

**Decision taken, with its reason, so the block does not re-open it.** A root-relative or bare
relative candidate is **dropped**, not resolved. Reason: the constructor receives a `Page`, so
`page.url` *is* in scope without a signature change, and resolving against it would produce a
plausible-looking **wrong** host — a silent misdirection, which is the same failure class as the
invented host this block removes. Dropping is a visible, conservative, and testable outcome.
Resolving against `page.url` is recorded as the **rejected alternative** and the block report must
say why.

**Acceptance criteria**

1. Nine address forms driven through `_normalize_url` produce: absolute `https` unchanged; absolute `http` **dropped**; scheme-relative `//cdn.example/a/stream.m3u8` promoted to `https://…`; root-relative `/a/stream.m3u8` **dropped**; bare host `cdn.example/a/stream.m3u8` promoted; bare relative `a/stream.m3u8` **dropped**; bare filename **dropped**; whitespace-padded absolute stripped.
2. `_normalize_url` contains no branch that cannot be reached.
3. A JSON payload value of `720/stream.m3u8` is **not** appended to the discovered set.
4. The `M3U8_PATTERN` match set is unchanged — the pattern is not in this block's scope and a narrower pattern would silently lose legitimate captures.
5. No constructor signature changes. `NetworkMonitor` is constructed from exactly one place and B6 must not add a parameter.
6. The `_intercept_response` m3u8 branch (which reads no body) is behaviourally unchanged.

**Tests**

- **ADD** `tests/test_browser_infrastructure.py::TestNetworkMonitor` — the nine-form table above,
  asserted **as a table**, so a regression names the form that changed.
- Compatible, must stay green unchanged:
  `test_network_monitor_skips_oversized_body_without_content_length` (B16's neighbour, same file).

**Dependencies:** `depends_on: []`. Parallel to B16 and B7 (see `C13` — same file, disjoint
functions, no ordering constraint).

**Risk class: LOW.** Pure function, no I/O, zero existing tests touch it directly.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The nine-form table and the control-flow argument for the dead branch are quoted in the finding and re-verified. |
| Researcher | **CONDITIONAL** | Only if the block's Planner revisits drop-vs-resolve: "what serves a relative `hls` value in a JSON body, and is that base the page's origin or the API's?" Not answerable from the repository. **The block is not required to call the Researcher.** |
| Planner | **YES** | §3.4. |
| Validator | **YES** | Six criteria, five of them negative, no existing oracle. |

#### §3.4 Decision B6 explicitly does **not** make

**Whether the plaintext-carry-forward branch is a behaviour change this block makes, or a property
it documents.** The `http://` guard currently returns an `http://` address unchanged. Dropping it
(a criterion above) is a **behaviour change on a path this block cannot exercise** — the artifact
notes the branch is reachable from both the response path and the JSON path, but a modern page
does not serve `http://` media. Options: (a) drop it, as criterion 1 says; (b) keep it and record
in a comment that plaintext media addresses are carried forward deliberately. (a) matches
`NET-016`'s recommendation ("drop candidates that do not resolve to an absolute `https://`
address"); (b) matches rule 2 if a real origin ever depends on it. **This plan takes (a)** — it is
the finding's own recommendation and the artifact corrected only the *severity*, not the remedy.
The Planner may revisit it and must record why. **Deferred to B6's Planner.**

---

### B7 — Constrain the captured-address selection surface, and make its label re-requestable

**Findings carried:** `NET-008` — HIGH · RUNTIME-ERROR · mandatory.

**This block is research-gated and must not start before the Researcher answers §3.5 question 1.**
A guessed CDN suffix is **worse than the current defect**: an over-narrow filter silently discards
the only address and the download fails; an over-broad one is the status quo. The repository
contains **no** host constant, allow-list, or origin string anywhere, and this plan asserts nothing
about what a real VK origin serves.

**Grouping changed from the artifact's Fix Order.** The artifact's group 5 put `NET-005`, `NET-008`
and `NET-016` in one change, on the ground that a host filter in `NET-008` would otherwise have to
special-case the host `NET-016`'s normaliser invents. **B6 ships `NET-016` ahead of this block and
closes that dependency**: after B6, the normaliser never invents a host, so there is nothing left
to special-case. Keeping all three together would have made the cheapest, most independent item in
the corpus wait on the most research-gated one. `NET-005` moves to B8 because `C3` orders it after
both.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `infrastructure/network_monitor.py` | `NetworkMonitor._intercept_response` — the capture predicate | Currently `".m3u8" in url.lower() or M3U8_PATTERN.search(url)`, with **no host constraint, no quality constraint and no preference for a media playlist over a manifest**, then a dedup on exact string and an append in arrival order. |
| `services/extractor.py` | the `Stream(...)` construction in the browser extraction body | Takes element zero unconditionally and stamps `quality="best"` on a record with no height and no width. |
| `services/extractor.py` | `_build_streams` — the heightless label (read-only here) | B5 owns the `height <= 0` rule; this block consumes its outcome. **B5 first, or the two collide on the same statement.** |
| `models/enums.py` | `QualityEnum` | The nine members are `240 360 480 720 1080 1440 2160 best worst` — **no member for a heightless record**, so the label the enumeration produces cannot be re-requested and `QualityEnum("unknown")` raises. Add the member (rule 10: a `StrEnum` member, never a literal). |
| `services/quality.py` | `QualitySelector._find_quality_match`, `QualitySelector.list_available_qualities` | The label must be accepted on re-request, and the alternatives list must be deduplicated. |

**Acceptance criteria**

1. A captured address whose host is outside the expected set is **not** offered to either transfer stage, and the rejection is logged with the host.
2. A media playlist is preferred over a manifest when both are captured, and the preference is logged.
3. The host and the label chosen are recorded in one log record, per the finding.
4. Every label `list_available_qualities` emits is a member of `QualityEnum` **or** is mapped to one in `_find_quality_match`; the round trip `QualityEnum(label)` succeeds for every emitted label.
5. The alternatives list contains no duplicates.
6. A heightless captured stream's label is no longer a member of nothing.
7. The browser extraction body's `Stream` record no longer asserts a height or quality it did not measure.
8. **No verification step in this block contacts a network or a real origin.** The expected host set is the Researcher's deliverable, recorded in the block report and in a comment that names its authority.

**Tests**

- **EDIT or VERIFY** `tests/test_extractor.py::TestExtractWithBrowser::test_browser_extraction_uses_first_m3u8_url`.
  **This is a fourth test-pinning group the code context did not list.** It asserts
  `streams[0].url == first_url` and `len(streams) == 1` from a two-element captured list — i.e. it
  pins the element-zero selection as the contract. Both URLs share the host
  `cdn.example.com` and neither is distinguishable as media-vs-manifest, so a **host filter alone
  leaves it green**, but a **preference rule could change which one wins**. The block must either
  leave it green and say why, or re-scope it and say why. It must not be deleted.
- **ADD** `tests/test_browser_infrastructure.py::TestNetworkMonitor` — a captured list mixing an
  expected host, an unexpected host, a manifest and a media playlist; assert which survive, in
  what order, and that a rejected host is not offered.
- **ADD** `tests/test_quality_selector.py` — the label round trip; the deduplicated alternatives list.
- Compatible, must stay green unchanged: `test_browser_extraction_survives_cookie_capture_failure`
  (single-URL case) and B6's nine-form table.

**Dependencies:** `depends_on: [B5]`. Blocks B8 (`C3`).

**Risk class: HIGH.** Research-gated, and the failure mode is a *silently failing download* rather
than a visible error. `NET-008` is the finding whose wrong fix is invisible.

**Agents required: all four.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "Which capture sites produce a host, and which are absolute by construction?" Needed because the filter's placement differs for the response path and the JSON path. |
| Researcher | **YES — BLOCKING** | §3.5 question 1. The single question the repository cannot answer. |
| Planner | **YES** | §3.5 questions 2 and 3. |
| Validator | **YES** | "Given the Researcher's host set, does every captured address the product can see either survive or fail **visibly** — and is the round trip from a produced label to a re-requested label total?" A filter that drops the only address is the exact failure `NET-008` is about, and it is invisible without this read. |

#### §3.5 Decisions B7 explicitly does **not** make

1. **What the expected CDN host or suffix is.** *Blocking.* Options considered and **not chosen
   here**: a hard-coded suffix constant; a configured `Settings` field an operator declares; a
   derivation from the page's own host; a "no filter, but record the host and warn" posture. The
   artifact explicitly declines to assert what a real VK origin serves and this audit had no
   network access. **Requires a Researcher with network or documentary authority; no agent in this
   plan may guess.**
2. **How the host constraint is expressed** — a module constant, a `Settings` field, or a
   predicate over the `netloc` (exact host, suffix, registrable domain). Each has a different
   operator contract and a different failure mode on a CDN that rotates subdomains.
   **Deferred to B7's Planner, after the Researcher answers.**
3. **Whether the label becomes a new `QualityEnum` member or is mapped in `_find_quality_match`.**
   The finding offers both. A member is cleaner and satisfies rule 10 directly, but it adds a
   tenth member to a public enumeration that a CLI surface may surface to operators, and a member
   that names the absence of a measurement is a slightly odd thing to offer as a *quality*. A
   mapping keeps the enumeration at nine and localises the absence. **Deferred to B7's Planner**;
   whichever it chooses, the round trip in criterion 4 must hold.
4. **The media-playlist-vs-manifest preference.** What distinguishes them is a *research*
   question adjacent to question 1. If the Researcher cannot answer it, the block must ship the
   host filter and the label fix **without** the preference and say so — a wrong preference
   heuristic is worse than no preference.

---

### B8 — Select the requested quality from the refreshed stream set, and record what was delivered

**Findings carried:** `NET-005` — HIGH · RUNTIME-ERROR · mandatory.

**Why last in the `C3` chain.** The refresh path must *record* which label it chose, and that
label must be one the enumeration accepts — which is B5's outcome — and the set it chooses from
must be one B7 has already constrained. Both are preconditions.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/segment_downloader.py` | `_refresh_token_and_retry` | Its last statement returns `str(streams[0].url)` — element zero, unconditionally, with no quality argument in scope. The forced re-extraction it calls bypasses the cookie-source check and always takes the browser path, so in production the replacement is always the same `quality="best", height=None` record regardless of what the caller asked for. Selection must branch on the caller's quality and log the requested **and** delivered label in one record. |
| `services/quality.py` | `QualitySelector.select` | Reused, not modified: run the selector over the refreshed streams when the request is `best`; when it is numeric, retain the preselected URL — **the same explicit branch the two sibling helpers already use**. |
| `services/segment_downloader.py` | the log record in `_refresh_token_and_retry` | `token_expired_fetching_new` currently carries no address, no label and no selected value. |

**Explicitly mirrored, not invented.** The two sibling helpers in the same codebase
(`_attempt_segment_resume` in `ytdlp_downloader.py`, `_resolve_cookies` in the same module) each
test `quality_enum == QualityEnum.BEST` and emit a record with the quality fields. **B8 copies that
branch and that record shape.** It does not design a new one. This is the concrete "follow existing
patterns" obligation for this block.

**Acceptance criteria**

1. A refresh performed for a `best` request selects via `QualitySelector` over the refreshed stream set, and the record carries the selected label.
2. A refresh performed for a numeric request retains the preselected URL and the record says so explicitly.
3. **One** log record carries both the requested and the delivered value, on every refresh — not one record for the expiry and another for the selection.
4. The returned address is not unconditionally element zero.
5. `_attempt_segment_resume` and `_resolve_cookies` are **unchanged**; their tests stay green unchanged.
6. The carve-out to phase 08 (rendering a non-selectable label in an error's alternatives) is honoured: this block does not touch any error's `alternatives` rendering.

**Tests**

- **ADD** `tests/test_segment_downloader.py` — `_refresh_token_and_retry` with a `best` request and
  a multi-stream refreshed set (the selection must not be element zero); with a numeric request (the
  preselected URL is retained); and an assertion that the record carries both labels.
- Compatible and the pattern to mirror, must stay green unchanged:
  `tests/test_hls_downloader.py::TestResolveCookies` (5) and `::TestAttemptSegmentResumeQuality`.

**Dependencies:** `depends_on: [B5, B7]`.

**Risk class: MEDIUM-HIGH.** Depends on two upstream blocks' outcomes; changes which bytes a
refresh delivers; the only record on the path is a single line that currently carries nothing.

**Agents required: Auditor, Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "What does the two sibling helpers do, exactly, on each of the three request classes — and does the refresh path's own call chain have any quality value in scope, or must one be threaded in?" The threading question is a signature change the finding does not name. |
| Researcher | no | No external system; the pattern to mirror is in the repository. |
| Planner | **YES** | §3.6. |
| Validator | **YES** | "For each of the three request classes, is the returned address the one the record names?" A selection that is right and a record that is wrong is still an operator who cannot tell what they got. |

#### §3.6 Decision B8 explicitly does **not** make

**Where the caller's quality reaches `_refresh_token_and_retry`.** The helper's signature carries
no quality argument today, and the artifact's recommendation says "parse the caller's quality"
without saying from what. Options: (a) a new parameter on `_refresh_token_and_retry`, threaded by
its single caller; (b) derive it from the `m3u8_url` already in scope, if the caller is known to
always pass the selected stream; (c) return the whole refreshed stream set and let the caller
select, which makes the selection happen in one place but moves a decision out of the helper that
performs the refresh. (a) is the most explicit; (b) is the smallest and is only correct if the
invariant in the `m3u8_url` parameter's meaning is guaranteed at the call site. **Deferred to B8's
Planner**, which must state which and, if (b), what enforces the invariant.

---

### B9 — Give the child the selected address, and stop inverting `worst` into `best`

**Findings carried:** `NET-003` — HIGH · RUNTIME-ERROR · mandatory.

**Grouping changed from the artifact's Fix Order.** The artifact's group 4 paired `NET-003` with
`NET-015` as "the ladder's two handoffs". After `NET-015` is reduced (§1.3), its remaining half
lives entirely in `downloader.py`'s ffmpeg branch and this block lives entirely in
`ytdlp_downloader.py` + one line of `downloader.py`'s ladder call. **They share no module and no
statement.** Keeping them together would add a second source file and a second test file to each
commit for no conflict reduction, and would couple a HIGH-severity selector inversion to a
MEDIUM-severity handoff tidy. Split.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ytdlp_downloader.py` | `_build_ytdlp_cli_command` — the format-selector ternary | `f"best[height<={q}]" if q and q.isdigit() else "best"`, fed by a `quality.replace("p","")`. `QualityEnum.WORST` is the string `"worst"`, not a digit, so a user who asks for the worst quality gets the literal selector `best`. The `best` case is coincidentally correct and must stay correct. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` | Has **no** `m3u8_url` parameter, and appends the **page** URL as the child's positional argument. The selected address, computed and threaded through `perform_download`, never reaches the child. |
| `services/ytdlp_downloader.py` | `download_with_ytdlp_with_resume_fallback` | The address it already holds in scope is threaded down. |
| `services/downloader.py` | `HLSDownloader.download_video` — the ladder call | The selected stream's address is already computed here; pass it. **Not in the re-export facade's import block** (§2.3). |
| — | the log record | The selected address **and** the delivered format are logged, so the request is distinguishable from the delivery. Today the only quality record on the path is the request echoed into `starting_ytdlp_download`. |

**Acceptance criteria**

1. Driving the command builder once per `QualityEnum` member yields: every numeric member → `best[height<=N]`; `best` → `best`; **`worst` → a worst selector, not `best`**.
2. The child's positional argument is the **selected stream address**, not the page URL.
3. The delivered format and the selected address are recorded in a log record, distinct from the request record.
4. A `QualityNotAvailableError` is still raised by the app when no exact label matches — the app is **stricter** than the child's `<=` superset filter, and that strictness is not a defect to remove. The block must not weaken it.
5. `downloader.py`'s re-export facade is unchanged.
6. The child still receives its existing robustness flags unchanged (`--socket-timeout`, `-R`, `--fragment-retries`, `-N`, `--user-agent`, `--referer`, `--no-check-certificates`, `--throttled-rate`, `--hls-prefer-native`).

**Tests — the third group that must be edited in this same change**

- **EDIT** `tests/test_hls_downloader.py::TestYtdlpCliCommand::test_cli_command_format_best_when_quality_not_digit`.
  **This test is the `worst → best` inversion written as a specification.** Its docstring says
  "when quality is non-numeric", so the assertion is *correct for `best` and wrong for `worst`*.
  Per rule 2 it is **re-scoped, not deleted**: split so `best` (non-numeric, correctly `best`) and
  `worst` (non-numeric, must not be `best`) are separate assertions with separate docstrings.
- **ADD** `tests/test_hls_downloader.py` — a test that the positional argument is the selected
  address; a `worst` case in the per-member table.
- Compatible, must stay green unchanged: the other 17 cases in `TestYtdlpCliCommand`, and
  `TestYtDlpSubprocessShutdown` (8) — which exercise the ladder with `echo=False`.

**Dependencies:** `depends_on: []`. Co-locates with B12 in `_download_with_ytdlp` (`C10`) — no
ordering constraint.

**Risk class: MEDIUM-HIGH.** The address handoff changes what the third-party downloader is
pointed at; the selector change alters a documented-looking request; and it breaks a green test.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The per-member selector table and the signature gap are quoted in the finding and re-derived against the live tree. |
| Researcher | **POSSIBLE** | If the Planner chooses "the child re-selects by height", the correct yt-dlp selector syntax for a *worst* selection is a library question the repository cannot answer. **Not required on the "pass the address" route.** |
| Planner | **YES** | §3.7 — this is the block's central fork. |
| Validator | **YES** | Criteria 1–3 are exactly the three ways the fix can be claimed while the defect persists. |

#### §3.7 Decision B9 explicitly does **not** make

**Does the child receive the selected address, or does it re-select?** The finding offers both.
- **(a) Pass the selected `m3u8_url` as the child's positional argument** and let yt-dlp resolve
  that single HLS URL. *Pro:* the app's `QualitySelector` becomes the only selector; the `worst`
  inversion disappears because no selector is derived from the request string at all; the
  "stricter than the child" divergence disappears with it. *Con:* the child loses the ability to
  pick a variant from a **master** playlist; if the selected address is a master, the child's
  default behaviour applies, which is a behaviour this block would be choosing implicitly.
- **(b) Keep the page URL and derive the selector from the *selected stream's* height**,
  special-casing `worst`. *Pro:* a smaller change; keeps the child's multi-variant selection. *Con:*
  the address hand-off defect — the finding's other half — is not fixed; and a child-side
  `worst` selector is a yt-dlp syntax question.
→ **Deferred to B9's Planner.** The two halves of the finding can be shipped separately **only if
the shipped half is independently correct**; a block that fixes only the selector and leaves the
page URL in place must say which half it shipped and must not claim the other.

---

### B10 — Make the two ladder handoffs agree about the path they hand on

**Findings carried:** `NET-015` — **reduced to the handoff-asymmetry half** · MEDIUM ·
SPEC-DEVIATION · mandatory. The `output_file` / `output_file.part` probe-and-cleanup half is
**OUT** — phase 07's `ART-002` (§1.3).

**What is in.** Two handoffs pass a failed stage's output path to the next stage. `_attempt_segment_resume`
removes the predecessor's partial before handing the path on, with the comment "Remove partial
file to start clean segment download". `perform_download`'s ffmpeg branch goes from
`download_with_ffmpeg` returning `None` straight into `download_hls_with_resume` with the **same**
`output_file` and **no unlink anywhere in the block** — so the truncated, partially-written file
the ffmpeg stage left is still sitting at the path the merge stage is about to write.

**What is out, and why B10's blast radius shrank.** The one-name predicate and the `DF-008` cleanup
are `ART-002`'s. **Because B10 now touches no `ytdlp_downloader.py` statement at all, conflict
`C9` (with B4) is eliminated rather than merely declared non-blocking.**

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/downloader.py` | `HLSDownloader.download_video` — the ffmpeg branch | The failed ffmpeg stage's partial is removed (or the merge stage is made to reject a pre-existing file) before the path is handed to `download_hls_with_resume`. |
| `services/downloader.py` | the ffmpeg branch's return contract | `download_with_ffmpeg` returning `None` currently means "no output, or an output we have not inspected" — the two are indistinguishable, and the fix must not make them more so. |
| `services/ffmpeg_utils.py` | the merge's output handling | **Read-only obligation only.** The merge writes to `output_file` with `-y`. Whether the receiving stage should reject a pre-existing file is a cross-module contract; B10 must not change ffmpeg's own behaviour. |

**Acceptance criteria**

1. After an ffmpeg stage that returns `None` having written a non-empty partial, the segment stage does **not** find that partial at the output path.
2. The yt-dlp handoff's existing unlink is **unchanged** — B10 makes the two agree, it does not change the one that already works.
3. The receiving stage's contract is stated in a comment or docstring: what the presence of a file at the output path means when it arrives.
4. `ytdlp_downloader.py` is **byte-identical** before and after. This is criterion 4 because it is the block's scope boundary with phase 07.
5. No test is deleted, and no test is weakened to accommodate the change.

**Tests**

- **ADD** `tests/test_downloader.py::TestPerformDownload` — the ffmpeg branch: a stubbed
  `download_with_ffmpeg` that writes a non-empty partial and returns `None`, then an assertion
  about what the segment stage receives. **This handoff has no test at all today** — it is the
  sharpest coverage gap the code context identified.
- Compatible, must stay green unchanged: `TestYtDlpSubprocessShutdown` (8) and `TestResolveCookies`
  (5), which both drive the ladder.

**Dependencies:** `depends_on: []`.

**Risk class: MEDIUM.** Small and self-contained, but it changes a handoff contract that three
other blocks in this plan touch, and the phase-07 boundary is a statement-level constraint
(criterion 4), not a preference.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "What does `download_with_ffmpeg` actually leave at the output path on each of its failure modes, and can the two be distinguished from the return value alone?" The answer decides whether an unlink is even sufficient. |
| Researcher | no | No external system. |
| Planner | **YES** | §3.8. |
| Validator | **YES** | Criterion 4 is a negative constraint on a file this plan does not otherwise touch, and the phase-07 `ART-002` fix will land in the same file. No test can see it. |

#### §3.8 Decision B10 explicitly does **not** make

**Where the unlink goes: the sender unlinks, or the receiver refuses.** (a) The ffmpeg branch
unlinks before handing on, mirroring `_attempt_segment_resume`. *Pro:* symmetric with the existing
correct handoff; one line. *Con:* a delete in an orchestrator, and it races with anything else
holding the path. (b) `download_hls_with_resume` rejects or overwrites a pre-existing output.
*Pro:* the receiver owns its input precondition. *Con:* a behaviour change to the segment stage's
contract, and it may conflict with a legitimate re-download over an existing file. (c) The merge
stage refuses to start if the output exists. *Pro:* fails visibly. *Con:* pushes the decision into
`ffmpeg_utils`, which B10 does not otherwise touch, and duplicates the `-y` semantics.
**Deferred to B10's Planner.** The Planner must state which, and must confirm criterion 4 holds
under the choice.

---

### B11 — Separate the merge budget from the HTTP budget, and compose the client timeout once

**Findings carried:** `NET-006` (MEDIUM) + `NET-007` (MEDIUM) — both `SPEC-DEVIATION`, both
mandatory.

**Why one block.** `C2`: the two findings share the attribute `DownloadPolicy.download_timeout`
and the nine parameter/field defaults that repeat it. `NET-006`'s helper placement and `NET-007`'s
new merge budget **must be decided together**, because the new setting is very likely the helper's
parameter. Splitting them would make one of the two decisions wrong by construction.

**Plan-05 ownership — decided, see §1.3.** The "replace the literal `= 300` defaults" half is plan
05 **Block 8 (`ENT-010`)**, which did not land. **B11 adopts it**, including plan 05's verified
acyclicity argument for the `ffmpeg_utils → downloader_throttle` edge. The nine literals are
`DownloadPolicy.download_timeout` plus five `int` defaults in `segment_downloader.py` and three
`float` defaults in `ffmpeg_utils.py`; `downloader_throttle.py` already does this correctly with a
module constant derived from the settings schema. **If plan 05 is resumed, its Block 8 must be
struck and this plan named as the owner.**

**Semantic anchors owned**

| Module | Semantic unit | Finding | Change |
|---|---|---|---|
| NEW or `services/downloader_throttle.py` | the client-timeout composition helper | `NET-006` | Three **byte-identical** compositions exist, in three modules. Collapse into one helper so the floor (`30`), default (`300`) and ceiling (`3600`) are checkable in one place. **Placement is deferred — see §3.9.** |
| the same three sites | the composed `ClientTimeout` | `NET-006` | Remove `sock_connect` — it adds nothing `connect` does not already bound. Make `sock_read` a function of the setting rather than the literal `60`. **Its exact shape is deferred — see §3.9.** |
| `services/ffmpeg_utils.py` | `_merge_segments_batched`, `_merge_batch_segments`, `_perform_final_merge` | `NET-007` | The merge stages get **their own** budget, passed once rather than per subprocess — today the HTTP per-request setting is handed unchanged, **per subprocess**, to a purely local `concat` of files already on disk. |
| `services/segment_downloader.py` | the merge hand-off into `_merge_segments_batched` | `NET-007` | The one site that conflates the two budgets. |
| `config.py` | `Settings` | `NET-007` | A new bounded field, if the Planner chooses that shape. Its declared description must stop implying it bounds only HTTP. |
| `docs/11-guides/configuration.md` | the settings table row and the per-setting section | `NET-006`/`NET-007` | The row currently says only "Download timeout in seconds (30-3600)" — it does not say "HTTP client timeout for individual segment requests and playlist fetches" (`config.py`'s own text) and does not say it also bounds the local merge. |
| `.env.example` | the `download_timeout` block | `NET-007` | If a new field is added. Any value change must be validated line-by-line against the model. |
| `tests/test_packaging.py` | `EXPECTED_SDIST_ENTRIES` | `NET-006` | **If and only if** the helper goes in a new `src/` module. |

**What this block must NOT do.** It must **not** add a whole-operation budget to the two transfer
stages. See §5.2 — this is the plan's single most repeated wrong turn.

**Acceptance criteria**

1. The composed `ClientTimeout` is built in exactly **one** place, and all three former sites call it.
2. Read back at `download_timeout` = 30 / 300 / 3600: at no value does the read term exceed the total that contains it, and the connect term is not redundant with itself.
3. The merge stages' budget is **not** the HTTP per-request setting, and it is passed **once** for the whole operation rather than per subprocess.
4. At the default and with 250 segments, the worst-case merge budget is what the chosen formula produces, and the block report states the number.
5. Lowering `download_timeout` no longer shortens each merge stage — the `NET-001` trigger is removed.
6. All nine literals are derived from the settings model, not repeated.
7. `ytdlp_downloader.py`'s "no application-level download timeout is imposed" comment is **byte-identical** before and after, and neither `process.wait()` in the two transfer stages is wrapped.
8. If a new `Settings` field was added: it is a Pydantic field with a `Field(...)` description, appears in `.env.example` with a **legal** value, and appears in `docs/11-guides/configuration.md`.
9. `tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` is edited **in the same change** if and only if a file was added.

**Tests**

- **ADD** `tests/test_downloader_throttle.py` or a new home for the helper — the composed timeout
  read back at the floor, the default and the ceiling, as a table. (There is no `aiohttp`
  occurrence anywhere in `tests/` today, so this is the suite's first timeout assertion.)
- **EDIT or ADD** `tests/test_ffmpeg_utils.py` — the merge budget: that `_merge_batch_segments` and
  `_perform_final_merge` receive the merge budget and not the HTTP setting.
- **ADD** `tests/test_config.py` — the new field's resolution, if one was added. Note the
  `_build_valid_env_vars`-driven namespace tests will see a new field automatically.
- Compatible, must stay green unchanged: `TestMergeFreeSpaceProbe` (6) — `_check_merge_space` is
  untouched by this block; `TestSequentialDownloadMode`, `TestDownloadSegmentRealExecution` (6),
  `TestMergeSegmentsBatchedRealExecution` (3); and B1's final-stage cleanup tests.

**Dependencies:** `depends_on: [B1]` (`C5` — `NET-007` *mitigates* `NET-001`, so `NET-001` is
not a peer but a predecessor). Blocks B15 (`C12`).

**Risk class: HIGH.** A new `Settings` field is an operator-visible surface; the helper may add a
`src/` module and trip the packaging gate; the new setting has **no CLI option today**, and an
option that is not `None`-defaulted silently shadows the `.env`; and the block is the one most
likely to be misread as authorising a transfer-stage budget it must not add.

**Agents required: all four.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "Read the composed timeout back at the floor, default and ceiling from the current tree, and state the merge budget the current code actually permits at 250 segments." The artifact's numbers were re-derived at a different baseline. |
| Researcher | **YES** | §3.9 question 1 is partly a layering question: which existing module is reachable from all three sites without a cycle, and does the repository have a precedent for a settings-derived module constant (it does — `_DEFAULT_DOWNLOAD_TIMEOUT` — and that precedent has a known defect: it is frozen at first import). |
| Planner | **YES** | §3.9 — four forks. |
| Validator | **YES** | Criteria 2, 3, 5 and 7 are the four ways this block silently regresses. Criterion 5 in particular is a coupling that no existing test can see, and criterion 7 is a prohibition. |

#### §3.9 Decisions B11 explicitly does **not** make

1. **Where the client-timeout helper lives.** (a) In `downloader_throttle.py`, which
   `segment_downloader.py` already imports — **but the third site is inside
   `downloader_throttle.py` itself, so this is the only option that adds no new edge at all.**
   (b) A new `src/` module, e.g. a `http_timeouts` module — cleanest, and **trips
   `EXPECTED_SDIST_ENTRIES`**, requiring a `tests/test_packaging.py` edit in the same change.
   (c) In `ffmpeg_utils.py` — **impossible**: it imports neither `downloader_throttle` nor
   `config`, and giving it either is a new edge. **Deferred to B11's Planner.** Plan 05 Block 8
   proved the `ffmpeg_utils → downloader_throttle` edge acyclic; B11 adopts that proof for the
   *literal-replacement* half and must not assume it transfers to this decision.
2. **The `sock_read` shape.** `min(60, download_timeout)` keeps a read ceiling inside the budget;
   `download_timeout` itself makes it a true per-read ceiling that grows with the setting; a
   separate bounded setting makes the hard 60 s ceiling a declared product decision rather than a
   literal. Each gives a different operator contract, and the third adds a second new field.
   **Deferred to B11's Planner.**
3. **The merge-budget formula.** (a) A new bounded `Settings` field, passed once. (b) Derived from
   the stage count and the measured segment size. (c) A per-stage constant. The artifact gives no
   formula, no ceiling, and does not state whether the budget is `⌈N/100⌉+1` stages × per-stage or
   a single total — and its own numbers (`3 × 300 + 1 × 300 = 1200 s` at the default for 250
   segments) describe what the code has today, not what it should be. **Deferred to B11's
   Planner.**
4. **Whether the new setting gets a CLI option.** `download_timeout` has none today; plan 05 Block
   2 reshaped the pattern to `int | None` with a `None` default in a conditional-overrides mapping.
   Adding an option is operator-visible; omitting it makes the setting env/`.env`-only, which is
   the status quo for this setting. **Deferred to B11's Planner.**

---

### B12 — Anchor the URL gate to an origin and derive the identifier once

**Findings carried:** `NET-012` — MEDIUM · `SPEC-DEVIATION` · mandatory.

**Research-gated, same gate as B7** (and it may share B7's Researcher deliverable — see §3.10
question 1).

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/extractor.py` | `VKVideoExtractor.VIDEO_ID_PATTERN` | `re.compile(r"video-(-?\d+)_(\d+)")` with a `?` admitting a leading `-`, matched by an **unanchored** `search` over the whole reference. |
| `services/extractor.py` | `is_valid_video_url` | Its docstring says "True if the URL **contains** a valid VK video identifier" — the code matches its own contract, so this half is a **hardening** recommendation, not a deviation. The contract is the weak thing. |
| `services/cli.py` | the batch command's URL-reading loop — the `is_valid_video_url` skip path | **Anchor to the batch command's loop, not to a line in a helper that plan 05 Block 3 moved.** |
| `services/downloader.py` | `HLSDownloader.download_video` | A `url.split("_")[-1]` slice. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` | A `url.split("_")[-1]` slice. Co-locates with B9 (`C10`). |
| `services/segment_downloader.py` | `_run_download_session`, `_download_segments_from_playlist` | Two `url.split("_")[-1]` slices. Co-locates with B4 (`C11`). |

**The measured divergence this block exists to close.** The parser derives `1_2` and `123_456`
for two accepted inputs; the four raw slicers derive `456` and `2/extra` for the same inputs. The
identifier that names the video in the progress display is not the one the parser produced.

**Acceptance criteria**

1. Acceptance is anchored to the **parsed origin and the parsed path**, not a substring of the whole reference. A foreign origin whose path embeds the pattern, and a foreign origin whose *query value* embeds it, are **rejected**.
2. The bare pattern with no scheme or origin is **rejected**.
3. A negative owner component is rejected **at acceptance**, or its acceptance is explicitly retained with a stated reason (§3.10 question 3).
4. The canonical form with a trailing path is handled by the same rule as the canonical form without one.
5. The identifier is derived **once**, by the parser, and the four consumers receive it instead of re-slicing the raw URL. No `url.split("_")[-1]` remains in those four sites.
6. The identifier each consumer receives equals the one the parser produced, for every accepted form.
7. **The batch skip path is unchanged in its message and its exit code** — a rejected URL still produces the same operator-visible outcome it does today. Changing the label is phase 08's (`OUT-009` territory).
8. A too-strict anchor does not turn a legitimate canonical URL into a skip. The block must state the accepted-form table it lands on.

**Tests**

- **ADD** `tests/test_extractor.py` — the accept/reject table as a **data-driven table**, including
  the two near misses that must stay rejected (`video_123_456`, `videos-123_456`, `video-1O3_456`,
  the empty string) and the forms that are currently accepted and must stop being.
- **ADD** — one test per rewired consumer asserting it receives the parsed identifier rather than
  its own slice. Four consumers, four assertions; each must fail if that one site regresses.
- **EDIT or VERIFY** `tests/test_cli.py::TestBatchCommand` — the `is_valid_video_url` skip path.
  The valid-URL cases must stay green unchanged; a case that becomes a skip must be a deliberate,
  stated narrowing.
- Compatible, must stay green unchanged: the `sample_video_url` fixture
  (`https://vkvideo.ru/video-12345_67890`) is the canonical form and must remain accepted.

**Dependencies:** `depends_on: [B5]` (`C8`). Does **not** depend on B7 — see §3.10 question 1.

**Risk class: HIGH.** It touches the acceptance gate for **every URL the product accepts**. Low
blast radius per item, high blast radius per run: a too-strict anchor turns valid URLs into skips
with a skip count and exit code 1. And the finding is half-hardening, half-correctness, so the
"what is the accepted set" question is a **product** question, not a code one.

**Agents required: all four.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "Which forms does the product actually need to accept — enumerate the consumers of `is_valid_video_url` and what each does with a rejected URL?" The blast-radius argument needs the full consumer list. |
| Researcher | **YES — BLOCKING** | §3.10 question 1. The same host constant B7 needs. |
| Planner | **YES** | §3.10 questions 2 and 3. |
| Validator | **YES** | "Does the accepted set still contain every form the product needs, does every consumer receive the parser's identifier, and is the operator-visible skip outcome unchanged?" A too-strict gate is a product regression that no single assertion catches. |

#### §3.10 Decisions B12 explicitly does **not** make

1. **The expected host / accepted URL set.** *Blocking.* Same gap as B7 §3.5 question 1. **The two
   blocks may share one Researcher deliverable** — the host question is literally the same — but
   **B12 must not be made to wait for B7's filter to land**: the gate is a correctness question
   about URL acceptance, the filter is a selection question about captured addresses, and B7's
   answer may be "no filter at all". Whoever schedules must not serialise them by accident, and
   must not let one Researcher's answer be used unexamined by the other block.
2. **Where the parsed identifier lives.** (a) A field on `HLSDownloadRequest` — a Pydantic model
   whose docstring explicitly says "Contains only pure data fields — no service dependencies", so a
   string is legitimate but it widens a model's public shape. (b) A field on `Video` / on the
   `VideoWithStreams` record. (c) A parameter on four call chains — the most explicit and the most
   invasive. **Deferred to B12's Planner.** Rule 5 favours the narrowest change; rule 4 (single
   responsibility) argues the extractor is where a parse belongs and the identifier should be its
   output, not a parameter on four unrelated chains.
3. **Whether a negative owner id is genuinely invalid.** `video--123_456` currently parses to
   `owner_id = -123`. The `?` in the pattern may be load-bearing for a form this plan has no
   evidence about. **Deferred to B12's Planner, and it requires the Researcher's answer** — this
   is a product question about VK's id space, and `NET-012`'s accept/reject table is a *string-test*
   table that says nothing about which accepted forms the product wants.

---

### B13 — Make the two surfaces of the third-party downloader present the same identity

**Findings carried:** `NET-013` — LOW · `BEST-PRACTICE` · **advisory** (reclassified from
`recommended`, which is not a member of the format's enumeration).

**Lowest priority in the corpus.** Advisory, no observed security, data-loss or correctness
consequence. It ships because it is cheap and because two of its four sub-claims were the two the
validator rejected as already-correct (see §1.3), which is exactly why its scope must be stated
narrowly: **B13 does not touch `throttled_rate`'s description and does not touch
`max_concurrent_downloads`'s description.**

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/extractor.py` | the in-process option object | Carries `quiet`, `no_warnings`, `extract_flat`, `nocheckcertificate`, `socket_timeout`, `retries`, `fragment_retries`, `throttled_rate` — and **no** user agent and **no** referer, against the child-process argv which carries `--user-agent` and `--referer`. The same third-party downloader therefore presents two different identities to the origin. |
| `services/extractor.py` | the un-warned `ssl_verify` flag site | One of the **two** of four flag sites that disable certificate verification with no warning in their own module. |
| `services/downloader.py` | the other un-warned `ssl_verify` flag site | The other. The two that already warn are not in this block's scope. |
| `infrastructure/browser.py` | the context construction | The browser's TLS posture is **undeclared** — inherited rather than stated. Pass it explicitly. |
| `services/quality.py`, `services/segment_downloader.py` | — | **Not touched.** (`C8`: NET-013 ↔ NET-012 ↔ NET-017 share the extraction path; the parse site is declared once, here.) |

**Acceptance criteria**

1. The in-process option object and the child-process argv carry the same user agent and the same referer.
2. Each of the two un-warned `ssl_verify` flag sites emits a warning in its own module, worded like the two existing ones.
3. The two already-warning sites are **unchanged** — no duplicate warning, no reworded warning.
4. The browser context's TLS posture is passed **explicitly**, and the value it receives follows from `ssl_verify` rather than being a new independent choice.
5. `throttled_rate`'s and `max_concurrent_downloads`'s field descriptions are **byte-identical** before and after.
6. No verifier is enabled or disabled that was not before — this block changes *identity and
   declaredness*, not *posture*.

**Tests**

- **ADD** `tests/test_extractor.py` — the in-process option object carries the configured user agent
  and referer, matching what the argv builder produces from the same `Settings`.
- Compatible, must stay green unchanged:
  `test_extract_with_ytdlp_propagates_settings_to_ydl_opts` — it asserts specific keys
  (`socket_timeout`, `retries`, `fragment_retries`, `throttled_rate`) and **not** the absence of
  others, so adding `user_agent` and `http_headers` keeps it green. The block must verify this
  rather than assume it.
- **ADD** — a warning assertion for each of the two sites, and one asserting **no** duplicate
  warning at the two existing sites.

**Dependencies:** `depends_on: [B5]` (`C8` — declare the parse site once, after `NET-017` settles
it).

**Risk class: LOW.** Advisory, no consequence observed, no behaviour change to any transfer.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The six-transport inventory, the option object read in full, and the four-flag-site / two-warning-site count are all quoted and re-verified. |
| Researcher | **CONDITIONAL** | The yt-dlp option **key names** are a library API question. **Deferred to B13's Planner** (§3.11); if the Planner cannot settle them from the installed package, a Researcher is required. |
| Planner | **YES** | §3.11. |
| Validator | **YES** | Criteria 3, 5 and 6 are all "this must not have changed" — and the finding's whole history is two sub-claims that *looked* like defects and were not. |

#### §3.11 Decisions B13 explicitly does **not** make

1. **The in-process option key names.** The child argv uses `--user-agent` and `--referer`; the
   option object needs the library's own key names, and the finding does not state them. A wrong
   key name is silently ignored by the library — the exact failure mode this block exists to fix,
   reproduced on the other surface. **Deferred to B13's Planner**, with a Researcher fallback.
2. **The browser's TLS posture value.** `ignore_https_errors` must be passed explicitly. From
   what? `ssl_verify` is the obvious source, but the browser surface has its own history and the
   finding does not say the browser is in the `ssl_verify` scope. (a) derive from `ssl_verify` —
   one posture for the whole process; (b) declare the current inherited behaviour explicitly,
   changing nothing. (a) is a **behaviour change**; (b) is a **declaration**. The finding says
   "declared rather than inherited", which reads as (b), but the option's name invites (a).
   **Deferred to B13's Planner**, and the choice must be recorded as a declaration either way.

---

### B14 — Stop using one setting as both the whole-video gate and the per-item request fan-out

**Findings carried:** `NET-014` — MEDIUM · `SPEC-DEVIATION` · mandatory.

**This is a product decision with operator-visible semantics, expressed as a code change.** It is
in the plan because it is mandatory and open, not because it is mechanical. The implementation is
small; deciding what an upgrading operator must set is not.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/segment_downloader.py` | `_run_download_session` | The per-item segment semaphore, currently sized by `max_concurrent_downloads` — a setting declared for whole videos. |
| `services/batch_downloader.py` | the batch gate, the `_TrackedSemaphore` wrapper, and the per-video acquisition | The whole-item gate, which is what the setting's own description declares. |
| `services/ytdlp_downloader.py` | the child `-N` argument | The third application of the same value. |
| `config.py` | `Settings` | A second, separately bounded setting if the chosen shape introduces one. |
| `services/segment_downloader.py` | `_create_connector` | **MUST NOT BE TOUCHED.** `TCPConnector(limit=10)` is phase 04's `CON-009` (advisory) and the declared seam both findings already hold. |

**The corrected arithmetic is binding on this block's commit message (`C6`).** The aggregate ceiling
is `10 × max_concurrent_downloads` — **40 at the default, 160 at the ceiling** — because
`_create_connector` has exactly one call site, inside `_run_download_session`, which runs once per
video, and each call is paired with its own `ClientSession`. **There is no process-wide pool.** The
figure `4 × 4 = 16` bounded by a process-wide 10 is wrong, and it is wrong in the source report —
see B2. **The commit body for B14 must use the corrected figure and must cite the validated
artifact's `NET-014` Validation Note (or phase 04's `CON-009`) as its authority.** A commit body
carrying the wrong number is the failure `phase03/VAL-001` was filed to prevent, reproduced by
this plan instead of by a fixer.

**Acceptance criteria**

1. Exactly **one** level is governed by `max_concurrent_downloads`, and it is the level the setting's own description declares.
2. The per-item request fan-out and the child's `-N` are bounded by a value that is **separately** bounded and separately declared.
3. The aggregate simultaneous request count against one origin is expressible from the settings, and the block report states it for the default and the ceiling.
4. `_create_connector` is **byte-identical** before and after. This is criterion 4 because it is the phase-04 seam.
5. **No claim is made that this block bounds the connection count.** The `limit=10` literal is phase 04's and this block does not touch it; the report must say so rather than implying the aggregate is now bounded.
6. The D-01 invariant is preserved: the batch permit is acquired **once per video** and is **not** re-acquired per segment — a non-reentrant `asyncio.Semaphore` does not support it, and this is why the remedy is *not* "gate the segment fan-out on the batch semaphore". The `D-01` comment must remain accurate.
7. The setting descriptions for both levels are accurate after the change.

**Tests**

- **ADD** `tests/test_batch_downloader.py::TestBatchDownloaderSemaphore` — the peak-concurrency
  measurement, re-expressed for whichever level now governs.
- **ADD** `tests/test_hls_downloader.py` — the child's `-N` carries the new value, not
  `max_concurrent_downloads`.
- **ADD** — a test that reads both settings and asserts the aggregate is the product the report
  claims, so the commit message cannot drift from the code.
- Compatible, must stay green unchanged: the existing peak-concurrency and permit-accounting tests
  under the chosen shape.

**Dependencies:** `depends_on: []`. B2 does **not** gate it — the corrected figure is already in
the validated artifact, and the block cites that rather than B2's output.

**Risk class: HIGH.** Operator-visible semantics for a documented, commonly-raised setting; and the
finding's own remedy **cannot** bound the connection count, so a block that ships without saying so
manufactures the false assurance the finding complains about.

**Agents required: all four.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | **YES** | "Enumerate every site the setting reaches, and state the aggregate for the default and the ceiling from the current tree." The whole finding is that the number is not expressible; the audit must produce the number the block will claim. |
| Researcher | **CONDITIONAL** | If the chosen shape needs a new operator-facing concept, whether the repository has an existing naming precedent for a second concurrency setting. |
| Planner | **YES** | §3.12 — the central product fork. |
| Validator | **YES** | Criteria 1, 4, 5 and 6 are the four ways this block ships a false claim, and criteria 4 and 6 are prohibitions on files this block does not otherwise edit. |

#### §3.12 Decisions B14 explicitly does **not** make

**Which level `max_concurrent_downloads` governs, and what the second setting is called.** Three
shapes, differing in what an upgrading operator must set:
- **(a) `max_concurrent_downloads` governs whole videos only** (its declared meaning); a new setting
  — say `max_concurrent_segments` — governs the per-item fan-out. *Pro:* the existing setting
  means what it says; existing operators' video-level concurrency does not change. *Con:* a new
  setting with a new default, and existing operators silently get a different segment concurrency.
- **(b) `max_concurrent_downloads` governs the per-item fan-out** (where the traffic actually is);
  a new setting governs whole videos. *Pro:* the aggressive bound is the one operators tuning for
  throughput are already raising. *Con:* inverts the setting's declared meaning — the worst option
  for compatibility.
- **(c) Gate the batch on a different value without introducing a setting** — e.g. derive the
  video-level count from something already present. *Pro:* no new surface. *Con:* makes the
  video-level bound implicit, and the finding's complaint is that the bound is not expressible.
→ **Deferred to B14's Planner**, who must treat it as the product decision it is and record the
upgrade note an operator needs. The Planner must also decide whether the child `-N` follows the
segment level or the video level, and must not leave the setting's own description ambiguous
afterwards.

---

### B15 — Parse every `Retry-After` date form, and clamp the wait the process actually performs

**Findings carried:** `NET-018` — LOW · `SPEC-DEVIATION` · mandatory.

**Grouped alone, but serialised behind B4 and B11 (`C12`).** This block is a small, self-contained
parser fix — but two of its three findings touch anchors B4 and B11 also own: the retry loops it
feeds are rewritten in B4, and the timeout's declared description plus the configuration guide's
row are rewritten in B11. **B11 first**, so the description is written once.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/downloader_throttle.py` | `_parse_retry_after` | Parses a bare float — which may be **negative** — and exactly **one** of the three HTTP-date forms the specification permits. The other two return `None`. A lower-case IMF-fixdate **is** accepted (the parse matches case-insensitively) and then yields ≈ 8.26 years. |
| `services/downloader_throttle.py` | `_compute_backoff_delay` | The `min(delay, 30.0)` clamp is applied to the **local** term, and the `max(delay, retry_after_seconds)` against the server's value is applied **outside** it — so the server's value is never clamped. A legitimate `Retry-After: 600` produces `[600.0] × 6` at attempts 0–5. |
| `config.py` | `Settings.download_timeout`'s declared description | Records the ceiling's scope (§3.13). |
| `docs/11-guides/configuration.md` | the `download_timeout` row and section | The same statement, in prose. |

**What this block must NOT do.** It must **not** touch the comment/`max()` wording mismatch in
`_compute_backoff_delay` — that is **phase 09's**, named by the artifact and confirmed present.

**Acceptance criteria**

1. All three HTTP-date forms parse; a lower-case IMF-fixdate does not produce a multi-year delay.
2. A negative delay is rejected; a non-positive parsed value is rejected.
3. A past date is still ignored — that is **correct per specification** and is the code's stated
   rule. It must stay.
4. The ceiling is applied **after** the maximum with the server's value, so the wait the process
   actually performs is bounded. The block report states the new maximum wait for a
   `Retry-After: 600` and for no header at all.
5. The clamp does not change the value passed to `random.uniform` — `test_delay_caps_at_30_seconds`
   asserts that bound and must stay green **unchanged**.
6. The "correctly-designed part is left alone" clause holds: a past date is still ignored, and
   this block does not add a warning about it.
7. The ceiling's scope is recorded in both the field description and the configuration guide.

**Tests**

- **ADD** `tests/test_downloader_throttle.py::TestParseRetryAfter` — the thirteen-row header-form
  table as a data-driven table, including the three date forms, the lower-case variant, the
  negative, the whitespace-padded value and the absent header.
- **ADD** `tests/test_downloader_throttle.py::TestComputeBackoffDelay` — a `Retry-After: 600` case
  asserting the **clamped** value, and a no-header case over a wide attempt range.
- Compatible, must stay green unchanged: `test_delay_caps_at_30_seconds`,
  `test_retry_after_overrides_delay` (uses `5.0`; a clamp leaves it), `test_invalid_date_format_returns_none`.

**Dependencies:** `depends_on: [B4, B11]` (`C12`).

**Risk class: LOW-MEDIUM.** The code change is mechanical; the risk is the scope decision (§3.13)
being left unrecorded, which turns a bounded wait into an unrecorded one.

**Agents required: Planner, Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The thirteen-row table and the ceiling-ordering measurement are quoted in the finding and re-derived. |
| Researcher | no | No external system; the three date forms are in the specification the finding cites. |
| Planner | **YES** | §3.13 — the one product decision. |
| Validator | **YES** | Criteria 3 and 5 are "this must not change", and criterion 3 is a case a well-meaning fix would "improve" into a warning, which the finding explicitly says not to do. |

#### §3.13 Decision B15 explicitly does **not** make

**Whether the ceiling is per-request or per-video.** The finding asks for this to be decided
explicitly and the answer changes what the setting means. Per-request: every request can wait up
to the ceiling, so a batch of *N* videos can be in `⌈N/100⌉+1`-sized waits simultaneously.
Per-video: the ceiling is the total the video's whole retry budget may consume, so a slow origin
degrades the batch rather than the request. **Deferred to B15's Planner.** Whichever is chosen must
be stated in the `download_timeout` field description **and** in `docs/11-guides/configuration.md`
— an unrecorded choice here is what made the original finding possible.

---

### B16 — Correct the comment that claims the byte cap bounds memory

**Findings carried:** `NET-011` — LOW · `SPEC-DEVIATION` · mandatory. **Comment-only.**

**What ships.** The JSON branch's comment says "Enforce a byte cap even when `Content-Length` is
absent" — and that is **accurate about what it claims**: a byte cap *is* enforced. What is not
enforced is a **memory** bound, because on the declared-length-absent and unparseable paths the
body is materialised all-or-nothing first and the cap is applied afterwards, so it bounds *parsing
work*, not memory. **The fix is to make the comment say what the code does.**

**What must not ship.** The validator **withdrew** the behavioural half: skipping the branch when
`Content-Length` is absent or unparseable would disable m3u8 discovery for every chunked or
streamed JSON response, trading a functional regression for a memory bound the Playwright
`Response` API cannot express. **Do not implement it.** The m3u8 branch reads no body and is
unaffected.

**Placed last within its wave.** One comment, one file, zero semantic anchors shared with anything
(§ `C13`: `network_monitor.py` is also B6's and B7's file, but in different functions and at
different statements — all three may run in parallel). It is placed last because it is the only
block whose entire content is a comment, and a comment-only block is best reviewed after the code
blocks that establish what the code does. **It is also the one block that can be dropped from the
plan without changing any dependency** — the only dependency edge into B16 is from nothing.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `infrastructure/network_monitor.py` | `NetworkMonitor._intercept_response` — the comment in the JSON branch | Restate: the cap bounds parsing, not memory, on the paths where the declared length is absent or unparseable. Name the mechanism (all-or-nothing body read) so the next reader sees why. |

**Acceptance criteria**

1. The comment states that the cap bounds parsing rather than memory, on the path where it applies.
2. **No executable statement in the file changes.** The diff for this file is a comment and nothing else.
3. The branch is **not** skipped when `Content-Length` is absent or unparseable.
4. The m3u8 branch is unchanged.
5. The `MAX_JSON_BODY_BYTES` constant, the declared-length pre-read, and the post-read comparison are unchanged.
6. No behaviour, no log record and no error path changes anywhere.

**Tests**

- None added. A comment change cannot be tested, and inventing an assertion for it would be
  testing a string literal.
- **Must stay green unchanged:** `test_network_monitor_skips_oversized_body_without_content_length`
  (a 1 MB body with no `Content-Length` yields 0 URLs). Its passing is the block's evidence that
  criterion 3 held.

**Dependencies:** `depends_on: []`.

**Risk class: TRIVIAL.** The highest ratio item in the corpus. The only real risk is an agent
"improving" the code while it is in there — criterion 2 and criterion 3 exist for that.

**Agents required: Validator.**

| Agent | Required | The question it answers |
|---|---|---|
| Auditor | no | The mechanism is quoted in the finding and re-verified. |
| Researcher | no | No external system. |
| Planner | no | One comment, one sentence, no fork. |
| Validator | **YES** | "Is the diff for this file comments only, and is the branch still taken?" Both are negative constraints with no oracle, and the withdrawn recommendation sitting in the source report is an active temptation. |

---

## §4 Dependency graph and execution order

### §4.1 The graph

```
                     ┌──────────────────────────────────────────────┐
                     │  WAVE 0 — no dependencies, all parallel      │
                     │                                              │
   B1  NET-001 ──────┼──► (B11)                                       │
   B2  VAL-001      │                                               │
   B3  VAL-004      │                                               │
   B4  NET-009/004/002/010 ────────────────────────────► (B15)       │
   B5  NET-017 ─────┼──► B7 ──► B8                                   │
   B6  NET-016      │   └──► (B12)                                   │
   B9  NET-003      │   └──► (B13)                                   │
   B10 NET-015*     │                                               │
   B14 NET-014      │                                               │
   B16 NET-011      │                                               │
                     └──────────────────────────────────────────────┘
                                      │
                     ┌────────────────┴────────────────┐
                     │  WAVE 1                        │  WAVE 2   WAVE 3
                     │  B7  ← B5                     │  B8 ← B5,B7
                     │  B11 ← B1                     │  B15 ← B4,B11
                     │  B12 ← B5                     │
                     │  B13 ← B5                     │
                     └────────────────────────────────┘
```

Formal edges (16 blocks, 9 edges):

| From | To | Conflict | Why |
|---|---|---|---|
| B1 | B11 | `C5` | `NET-007`'s remedy *mitigates* `NET-001`'s blast radius by removing the trigger (a lowered `download_timeout` aborting a merge that destroys its inputs). `NET-001` is the predecessor, not a peer. |
| B5 | B7 | `C3` | `NET-017` settles what a quality label may be; `NET-008` then adds a member to the enumeration and consumes the label. Both write `Stream.quality` / `QualityEnum`. |
| B5 | B8 | `C3` | `NET-005` must *record* which label it delivered, and the label must be one the enumeration accepts. |
| B5 | B12 | `C8` | `NET-012` and `NET-017` share the extraction path; the parse/classification site is declared once, and `NET-017` settles it first. |
| B5 | B13 | `C8` | Same declaration, same reason. |
| B7 | B8 | `C3` | `NET-005` selects from the set `NET-008` constrains. |
| B4 | B15 | `C12` | `NET-018` feeds the retry loops `NET-002`/`NET-010` rewrite. |
| B11 | B15 | `C12` | Both edit `Settings.download_timeout`'s declared description and the `download_timeout` row of `docs/11-guides/configuration.md`. **Statement-level collision** — the only one in the plan that is not `C1`–`C8`. |

**Edges that exist and are deliberately *not* drawn.**

| Pair | Why there is no edge |
|---|---|
| B4 ↔ B9 | `NET-004` and `NET-003` both move a selected address toward a consumer, in different modules. |
| B2 → B14 | B14's commit body needs the *corrected figure*, which is already verbatim in the validated artifact's `NET-014` Validation Note. B14 cites that, not B2's output. Drawing the edge would serialise a product fix behind a prose edit. |
| B7 → B12 | Both are research-gated on the same host constant, so they may **share one Researcher deliverable** — but they are different questions (which captured addresses are selectable vs. which URLs are acceptable). Neither block's answer is an input to the other's. B12 must not wait for B7. |
| B6 → B7 | The artifact's group 5 made `NET-016` a companion of `NET-008` because a host filter would otherwise have to special-case the host `NET-016` invents. **B6 removes the invented host**, so the coupling is gone and B6 is independent. |

### §4.2 The linearised order, and the reason for each position

Nine blocks are unconstrained and may run in any order or in parallel. The order below is the
**recommended** sequence, not a dependency chain.

| # | Block | Why here |
|---|---|---|
| 1 | **B1** `NET-001` | The only irreversible loss. Alone, first, with its test edit in the same change. Nothing else in this plan destroys data, and `NET-007` can *trigger* this loss — so nothing may delay it. |
| 2 | **B2** `phase03/VAL-001` | Prose, zero code risk, and it settles the arithmetic that B14's commit body must carry. Early because it is cheap and because a wrong figure circulating in a source report is a live hazard for any agent that reads the report instead of the validated artifact. |
| 3 | **B3** `phase03/VAL-004` | Prose, zero code risk, and it must **claim ownership away from plan 05 Block 9** before anyone resumes plan 05. Early for the same ownership reason as B2. |
| 4 | **B4** the manifest block | The largest, highest-risk, most test-coupled change in the plan. Fourth — after the cheap and irreversible ones — so that the two test-pinning groups it depends on (B1's) are already committed and its own diff is reviewed against a known baseline. |
| 5 | **B5** `NET-017` | Head of the `C3` chain and the `C8` declaration. Must precede four blocks; starting it early unblocks the most work. Small, breaks no test, and is the correct thing to settle first. |
| 6 | **B6** `NET-016` | Pure function, one file, zero existing tests, no shared anchors. Placed here only because it is the second-cheapest unconstrained item and B5 is already warm on `extractor.py`/`quality.py` context. |
| 7 | **B9** `NET-003` | Unconstrained, test-pinning, and a distinct module from everything before it. Early among the unconstrained set because its pinned test must be re-scoped carefully and benefits from a quiet diff. |
| 8 | **B10** `NET-015` (reduced) | Unconstrained and small, but it changes a handoff contract three other blocks touch. Placed after B9 so its `ytdlp_downloader.py` scope-boundary criterion (byte-identical) is checked against a file B9 has just changed. |
| 9 | **B14** `NET-014` | Unconstrained, but it is the plan's other product-semantics decision and it must **not** be implemented before B1 and B2 are settled, because its commit body's arithmetic and its relationship to `NET-001`'s risk are both in play. |
| 10 | **B16** `NET-011` | The only comment-only block, and the only block that can be dropped without changing any dependency. Last within the wave so it is reviewed against the settled code. |
| 11 | **B7** `NET-008` | Wave 1. **Blocked on the Researcher**, which is the plan's only external gate. Started as early as its dependencies allow because the research has the longest lead time. |
| 12 | **B11** `NET-006`+`NET-007` | Wave 1, after B1 (`C5`). Second because it carries a new `Settings` field and possibly a new `src/` module, i.e. the plan's largest surface footprint. |
| 13 | **B12** `NET-012` | Wave 1, after B5. Also Researcher-blocked, and also carries a product question ("which URL forms are valid?") that the operator-visible skip path exposes. |
| 14 | **B13** `NET-013` | Wave 1, after B5. Lowest-severity item in the corpus; it is the one block in wave 1 that may be dropped last if capacity is short. |
| 15 | **B8** `NET-005` | Wave 2, after B5 and B7. Tail of the `C3` chain. |
| 16 | **B15** `NET-018` | Wave 3, after B4 and B11. Last because it shares two anchors with blocks that are themselves late, and because its own change is small enough to absorb any surprise. |

### §4.3 Conflict matrix — every pair sharing a semantic anchor

`C1`–`C8` are the code context's. `C9`–`C13` were found by re-reading the anchors for this
decomposition and are marked **(new)**. **Semantic names are the key; line numbers are secondary
locators only.**

| # | Findings · blocks | **Shared semantic anchor** (semantic key) | Nature | Resolution order |
|---|---|---|---|---|
| **C1** | `NET-002` ↔ `NET-009` · **B4 absorbs both** | Module-level function `_notify_backoff_for_retryable_status`; its only caller is `_run_parallel_download_with_backoff`; attribute `URLBackoffCoordinator.pause(video_url, 10.0)` | **Signature + call site + attribute value.** `NET-002` copies this helper's current semantics into a second site; `NET-009` changes those semantics. | **Resolved *within* B4, not by ordering.** The block does `NET-009` first, then `NET-002`. This is the artifact's second option and the one the test coupling forces. No cross-block edge. |
| **C2** | `NET-006` ↔ `NET-007` · **B11 carries both** | The attribute `DownloadPolicy.download_timeout`; five `int` defaults in `segment_downloader.py`; three `float` defaults in `ffmpeg_utils.py`; the `download_timeout` parameter of the two `_await_ffmpeg_with_timeout` call sites | **The setting's whole surface.** The helper placement and the merge-budget shape must be decided together because the new setting is likely the helper's parameter. | **Same block.** `NET-006`'s composition, then `NET-007`'s budget. |
| **C3** | `NET-017` → `NET-008` → `NET-005` · **B5 → B7 → B8** | The quality label produced by `_build_streams`; the model attribute `Stream.quality`; the member set of the `QualityEnum` enumeration; read by `QualitySelector._find_quality_match` and `QualitySelector.list_available_qualities` | **The most contended statement group in the corpus.** Three findings read or write the same attribute on the same model. | **The plan's only three-step chain.** `NET-017` (smallest, settles what a label may be, breaks no test) → `NET-008` (adds the member) → `NET-005` (records which label it chose). Cuts across the artifact's G5/G6 boundary, so the artifact's group 5 and group 6 **cannot** be parallelised as written. |
| **C4** *(renumbered — the artifact's Fix Order item 6's claim)* | — | — | The artifact's claim that group 6's members "share no insertion point" is **false**; `C2`, `C5`, `C7`, `C8` all sit inside it. | Recorded here so the artifact's claim is not repeated. The block structure above does not inherit it. |
| **C5** | `NET-001` ↔ `NET-007` · **B1 → B11** | The `download_timeout` argument threaded into `_await_ffmpeg_with_timeout`, via `_merge_segments_batched`'s own parameter, fed from `DownloadPolicy.download_timeout` | **Coupling, not a conflict.** Lowering the setting shortens every merge stage, and per `NET-001` such a timeout abort destroys the inputs. `NET-007`'s remedy removes the trigger. | **`NET-001` first, alone.** The artifact is right: the loss is irreversible and the coupling is not an ordering constraint. `NET-007` is a **mitigating successor**, not a peer. |
| **C6** | `NET-014` ↔ `phase03/VAL-001` · **B14, B2** | The arithmetic in `NET-014`'s own consequence text; the module-level function `_create_connector` and its single call site | **Documentation + commit hygiene, not code ordering.** | **No code edge.** B14's commit body must carry `10 × max_concurrent_downloads` and must not touch `TCPConnector(limit=10)`. B2 corrects the source report. B14 cites the validated artifact, not B2. |
| **C7** | `NET-002` ↔ `NET-010` ↔ `_is_retryable_status` ↔ `RETRYABLE_STATUS_CODES` · **B4** | The retryable-status **set** itself: two module-level predicates and one module-level constant, not unified | **Predicate ambiguity, inside one block.** "The same policy table the media-part layers use" is ambiguous precisely because three predicates exist. | **Resolved inside B4.** Deferred to B4's Planner (§3.2 item 2). No two sub-edits may each "add a predicate". |
| **C8** | `NET-013` ↔ `NET-012` ↔ `NET-017` · **B5, B12, B13** | The class attribute `VKVideoExtractor.VIDEO_ID_PATTERN`; the module-level function `is_valid_video_url`; the four raw-string `url.split("_")[-1]` slices; the batch gate; the in-process option object on the same extraction path | **All three argue over where the URL parse lives.** | **`NET-017` first, then B12 and B13 in either order.** Not grouped: they share no *statement* — the pattern and its predicate are at one end of the extraction path, the option object at the other. The **parse site is declared once**, in B13, and B12 must not move it. |
| **C9** **(new)** | `NET-009` ↔ `NET-015` · **B4 ↔ B10** | The function `download_with_ytdlp_with_resume_fallback` — the `wait_if_paused` consult and the `validated_output` predicate and the `DF-008` cleanup are all in its body | **Co-location, not ordering.** Three statements, no overlap. | **Eliminated by scope reduction.** After B10 is reduced to the handoff half, it touches **no `ytdlp_downloader.py` statement at all** (§1.3), so the co-location no longer exists. Recorded because it would have needed declaring had the reduction not happened. |
| **C10** **(new)** | `NET-003` ↔ `NET-012` · **B9 ↔ B12** | The function `_download_with_ytdlp` in `ytdlp_downloader.py` | **Co-location, not ordering.** `NET-003` adds an `m3u8_url` parameter and changes the child's positional argument; `NET-012` rewires the `url.split("_")[-1]` identifier derivation. Different statements. | **No edge.** But the two must not be implemented concurrently by two agents without a re-read: the identifier derivation and the address parameter are both in the same signature, and B12's rewiring touches a line B9's signature change moves. |
| **C11** **(new)** | `NET-004` ↔ `NET-012` · **B4 ↔ B12** | The function `_run_download_session` in `segment_downloader.py` — the `DownloadPolicy.m3u8_url` construction and one `url.split("_")[-1]` slice | **Co-location, not ordering.** ~230 lines apart, different statements. | **No edge.** Same concurrency caution as `C10`. |
| **C12** **(new)** | `NET-006`+`NET-007` ↔ `NET-018` · **B11 ↔ B15** | `Settings.download_timeout`'s `Field(description=...)` **and** the `download_timeout` row of `docs/11-guides/configuration.md` | **Statement-level collision.** The only one in the plan that is not `C1`–`C8`. Two blocks editing the same field description and the same doc row. | **B11 before B15** — `depends_on: [B4, B11]`. B11 writes the description once; B15 amends it with the ceiling's scope (§3.13). |
| **C13** **(new)** | `NET-011` ↔ `NET-016` ↔ `NET-008` · **B16 ↔ B6 ↔ B7** | The file `infrastructure/network_monitor.py` — three different functions: the JSON branch's comment, `_normalize_url`, and the capture predicate in `_intercept_response` | **File co-location only.** No statement is shared. | **No edge. All three parallel.** Recorded so a scheduler does not infer a serialisation from the shared filename. |
| **C14** **(new)** | `NET-015` ↔ phase 07's `ART-002` · **B10 (reduced)** | The `validated_output` probe, the `DF-008` cleanup, and `_attempt_segment_resume`'s `output_file.unlink()` | **Cross-phase duplicate ownership.** Same three statements, same fix shape, and `ART-002` is stronger (HIGH vs MEDIUM; re-derives the child's own `temp_name()`; observed across three runs). | **Resolved by deferral, not by ordering.** B10 ships only the handoff half. The `.part` half belongs to phase 07's `ART-002`. See §1.3. |

### §4.4 Every grouping changed from the artifact's Fix Order, and why

| Artifact's Fix Order | This plan | Why it changed |
|---|---|---|
| Group 2 — `VAL-003` as a block | **No block** | Already fixed by `d62671b`. |
| Groups 3 + 6 — `NET-004`/`NET-002`/`NET-009`/`NET-010` in group 3, and `NET-009` also in group 6 | **B4 carries all four** | `VAL-002` plus the single shared test class forces one change. The artifact's own second option ("or the G3 block must absorb the `NET-009` change") is the one taken. |
| Group 4 — `NET-003` with `NET-015` | **B9 and B10, split** | `NET-015` is reduced to the handoff half (§1.3), which lives in `downloader.py`; `NET-003` lives in `ytdlp_downloader.py`. They share no module and no statement, so the grouping became a coupling with no conflict-reduction benefit. |
| Group 5 — `NET-005` + `NET-008` + `NET-016` together | **B6, B7, B8, split three ways** | B6 removes the invented host, which is the *reason* the artifact coupled it to `NET-008`'s host filter — so the coupling is dissolved. `C3` then orders `NET-005` after `NET-008`, which the single group forbade. |
| Group 6 — eight findings "in any order, no two share an insertion point" | **B5, B11, B12, B13, B14, B15, B16, split seven ways** | The claim is false: `C2`, `C5`, `C7` and `C8` all sit inside it. The block set follows the anchors, not the group. |
| — | **B2, B3 added as separate blocks** | The artifact's Fix Order put `VAL-003` second and did not rank the pipeline findings as blocks. The code context's ordering is adopted for the two that remain open, split because they share no file. |

---

## §5 Risks

### §5.1 The test-pinning risk — the plan's largest mechanical hazard

Project rule 2: *if tests conflict with architecture or business logic, fix or remove the tests;
never distort production code for tests.* Three groups of currently-green tests assert the
**defective** behaviour and will fail when their finding is fixed. Each must be edited **in the same
change** as its fix, or the block's gate fails and the natural (wrong) response is to distort the
code.

| Block | Test | What it pins | Disposition |
|---|---|---|---|
| **B1** | `tests/test_ffmpeg_utils.py::TestMergeBatchSegments::test_merge_batch_removes_input_files_on_success` | The destructive-per-batch behaviour — `assert not segment1.exists()` after a successful batch stage | **Re-scoped, not deleted.** Split into "a batch stage preserves its inputs" and "the final stage removes them". |
| **B4** | `tests/test_segment_downloader.py::TestFetchPlaylistWithRetry` — **all 5** | `NET-004`'s bare-string return; `NET-002`'s single-attempt behaviour (`test_refresh_failure_falls_through` asserts `fetch_count == 1`); `NET-010`'s and `NET-002`'s manifest bullet; `NET-009`'s missing coordinator | **All 5 re-scoped.** Two of them patch `_fetch_single_playlist` and `_handle_token_refresh` **positionally** — B4 must not change those two helpers' signatures (criterion 10). |
| **B9** | `tests/test_hls_downloader.py::TestYtdlpCliCommand::test_cli_command_format_best_when_quality_not_digit` | The `worst → best` inversion, **written as a specification** | **Re-scoped, not deleted.** Its docstring says "when quality is non-numeric", so the `best` assertion is correct and only the `worst` case is wrong. Split into two assertions. |
| **B7** **(new — not in the code context's list)** | `tests/test_extractor.py::TestExtractWithBrowser::test_browser_extraction_uses_first_m3u8_url` | The element-zero selection — `streams[0].url == first_url` and `len(streams) == 1` from a two-element captured list | **Edit or verify.** Both URLs share the host `cdn.example.com` and neither is distinguishable as media-vs-manifest, so a **host filter alone leaves it green**; a **preference rule could change which one wins**. The block must state which case it is. It must not be deleted. |

The failure mode this risk creates is uniform: an agent under gate pressure weakens an assertion
rather than fix the code. **B9's Validator criterion and B1's are written to catch exactly that** —
a re-scoped test must assert the *new* contract, not a weaker one.

### §5.2 The prohibition: no whole-operation budget on the two transfer stages

**This is the one thing the artifact says not to do, and the most repeated wrong turn available.**

The two stages that actually transfer bytes — the yt-dlp child (`ytdlp_downloader.py`'s bare
`process.wait()`) and the ffmpeg live-stream stage in `downloader.py` — are **deliberately
unbounded**, and the code says so in prose: yt-dlp carries `--socket-timeout`, `-R`,
`--fragment-retries` and `-N`, and *"no application-level download timeout is imposed, avoiding
premature kill of legitimate long downloads."*

Wrapping either `process.wait()` in `asyncio.wait_for` re-introduces exactly that premature kill
and makes a legitimate long download fail. The validator **withdrew** that recommendation — but
**the withdrawn text is still in the source report**, and `process.wait()` is the most
natural-looking place to add a budget. `NET-007`'s surviving half is about the *local concat*,
which is a different function in a different module.

**Binding on B11**: criterion 7. The decision comment must be byte-identical before and after, and
neither `process.wait()` may be wrapped. **Binding on every block**: a report that finds itself
adding a transfer-stage budget is wrong, and must be rejected at review.

### §5.3 Implementation risks

| Risk | Blocks | Containment |
|---|---|---|
| **B1's partial fix is worse than the defect.** Deferring *some* deletions still destroys inputs if the surviving half lands first. | B1 | One block, criterion set built around all three failure shapes. A Researcher is required for the phase-07 residue interaction. |
| **B4 rewrites a return contract and a signature that five tests patch positionally.** | B4 | Criterion 10 forbids touching the two patched helpers' signatures. All four agents. |
| **B4's credential/base ordering.** Writing the refreshed cookie before switching the base sends a fresh credential to the stale host — the thing the finding is about. | B4 | Criterion 5 asserts the **order**, not the presence of each. |
| **A new `src/` module trips `EXPECTED_SDIST_ENTRIES`.** | B11 | Criterion 9: the frozenset is edited in the same change, if and only if a file was added. |
| **A new `Settings` field has no CLI option, and a non-`None`-defaulted option silently shadows the `.env`.** | B11, B14 | §2.3's option rule; the Planner must follow plan 05 Block 2's `int | None` pattern or add no option. |
| **A test-pinned assertion is weakened instead of the code fixed.** | B1, B4, B7, B9 | §5.1. Each block's Validator is briefed on it. |
| **A structlog/stdlib-`logging` slip.** A new module or a new `import logging` would break the renderer split. | all | §5.4. |
| **A new constant as a literal or a dict instead of a `StrEnum` member.** `NET-008`'s heightless label is a direct hit. | B7, and any block adding a constant | Rule 10; the reviewer's first question on any new value. |

### §5.4 The `structlog` trap — a doc-vs-code divergence flagged, not fixed

`.kilo/rules/project.md` rule 12 literally prescribes `logger = logging.getLogger(__name__)`.
**The codebase universally uses `structlog`**: every module does `from structlog import get_logger`
then `logger = get_logger(__name__)`, and `config.setup_logging` wires
`structlog.stdlib.LoggerFactory` over `logging.basicConfig` with a `JSONRenderer`/`ConsoleRenderer`
split.

The divergence is **universal and load-bearing**. A phase-03 fix that followed the rule text and
imported stdlib `logging` would bypass the renderer split and change the log format for the whole
process.

**Decision: follow the code, not the rule text, and do not "fix" the rule file as part of phase
03.** Correcting `.kilo/rules/project.md` is an audit-pipeline change, not a product change, and it
is outside this plan's scope. **Binding on B3**, which edits `.kilo/agents/*` and must not reach
`.kilo/rules/project.md`. Recorded here so no block re-opens it.

### §5.5 Rollout and regression risks

| Risk | Detail |
|---|---|
| **The `VAL-` namespace.** The highest **process** risk in the plan. An unqualified `VAL-003` in a block report, a commit message or a task id makes step 5 validate the wrong documents — plan 06 already lists phase **02**'s `VAL-002` and `VAL-004`, which happen to name phase **03**'s `VAL-003` and `VAL-005`. | Mitigated by the convention at the top of this plan, which is a **naming decision taken before any block is written**, not a review step. Every id in §6 is qualified. |
| **A wrong concurrency figure shipped in a commit body.** | `C6` + B14's binding arithmetic. The corrected figure is already in the validated artifact; B14 must cite it. |
| **Breaking a test that guards a real invariant while re-scoping a pinned one.** | Each block's re-scope is listed individually in §5.1 with what the assertion must now say. The compatible-test lists name the tests that must stay green **unchanged** — that list is the regression net. |
| **Ordering violated for convenience.** | The conflict matrix (§4.3) is the scheduler's reference. `C3` and `C5` are the two edges with a real correctness reason; `C12` is a statement collision; `C9`–`C11`, `C13` are explicitly *not* edges and must not be serialised. |
| **A block editing a file another phase owns.** | B1 ↔ phase 07 (`ART-004`/`ART-012`), B10 ↔ phase 07 (`ART-002`), B14 ↔ phase 04 (`CON-009`), B3 ↔ existing reports, B8/B7 ↔ phase 08 (error-alternatives rendering), B15 ↔ phase 09 (comment/`max()` wording). Each is a **stated boundary with a negative acceptance criterion**, not a preference. |

### §5.6 Compatibility risks

| Risk | Detail |
|---|---|
| **`_fetch_playlist_with_retry`'s return type changes** (B4). | It is module-private, has two in-tree callers, and is patched in tests. **No public API changes.** `downloader.py`'s 11 re-exports are untouched by every block. |
| **A new `Settings` field** (B11, possibly B14). | Backward-compatible: a new bounded field with a default does not change any existing setting's meaning. `extra="forbid"` means an unrecognised `VKDOWNLOADER_` variable is an error, so the new variable must be in `.env.example` **and** the configuration guide or operators get `extra_forbidden` on upgrade. |
| **`QualityEnum` gains a member** (B7). | The enumeration is 9 members; no test enumerates it. If any operator-facing surface renders it as a choice, a tenth member is user-visible — which is one of the reasons §3.5 question 3 is deferred. |
| **`download_with_ytdlp_with_resume_fallback`'s argv changes** (B9). | The child receives a different positional argument. Its existing robustness flags are unchanged (criterion 6), and no option is removed. |
| **Deleting the transfer-stage budget is *not* being done** — recorded here because a reader may mistake §5.2 for a compatibility item. | The design decision at `ytdlp_downloader.py` is **preserved verbatim**. |

### §5.7 Documentation risks

| Risk | Detail |
|---|---|
| **A block changes behaviour and leaves the justifying comment lying.** The house style is dense decision-carrying comments (`D-01`, `D-04`, `D-10`, `D-11`, `D-12`, `INT-003`, `SEC-001/002/003`, `DF-003/006/008/010`, `TRN-001`, `SRV-006`). | **Named survivors**: B11 must not touch the yt-dlp "no application-level download timeout" decision; B1 touches no `D-` tag; B14 must keep `D-01` accurate (the non-reentrant-semaphore invariant is *why* its remedy is not "gate the fan-out on the batch semaphore"); B12 touches `DF-003`-class comments around the URL gate and must re-read them. |
| **The configuration guide drifts from the model.** | `docs/11-guides/configuration.md`'s `download_timeout` row is already wrong in a third way: it says neither what `config.py` says ("HTTP client timeout for individual segment requests and playlist fetches") nor that it also bounds the local merge. B11 and B15 both own this row (`C12`), in that order. |
| **A block writes a new setting into `.env.example` with an illegal value.** | Phase 02 found a shipped `.env.example` value that the model rejects. **Any `.env.example` value this plan adds must be constructed against the model and recorded in the block report** — the same line-by-line validation plan 06 applied. |
| **The source report is mistaken for the validated artifact.** | `.ai/audit/03-network-resilience/findings.md` still contains **every** withdrawn and severity-corrected sub-claim — including the `wait_for` text and the `sock_read`-truncation claim. **Every block in this plan cites the validated artifact only.** A block report that implements one of the withdrawn recommendations is wrong on its face. |
| **Documentation noise for self-evident changes.** | B16 is a comment-only block and needs no doc edit. B16's edit *is* documentation, and it is the whole finding. No block adds a doc page. |

### §5.8 The boundary no block may cross

**No finding in this corpus asserts what a real VK origin does.** Every live claim is structural:
a count of requests, a measured inter-request gap, a read of a return annotation, a signature, a
control-flow argument. The artifact that produced this plan had no network access.

**Therefore, binding on every block and every verification step:**

1. **No block may be justified by "a real VK origin would 403 the part"**, "a real CDN would serve
   `*.m3u8` from this host", or any equivalent. Those are the assumptions the audit explicitly
   declined to make.
2. **No verification step may require network access.** `tests/test_packaging.py` is the only test
   that touches the network and it *skips* off-CI when `uv build` cannot reach one; that is the
   entire network-touching surface of the suite, and this plan adds none.
3. **B7's expected-host set is a Researcher deliverable, not a guess.** A guessed suffix is worse
   than the current defect: an over-narrow filter silently discards the only address and the
   download fails; an over-broad one is the status quo.
4. **B12's accepted-URL set is a product question** the artifact's accept/reject table — a
   *string-test* table — cannot answer.
5. **Every new test uses a local stub or a `MagicMock` session.** There is no `aiohttp` fixture and
   none may be added for these blocks; the suite's zero-`aiohttp` property is a fact about the
   codebase, not a gap to close here.

---

## §6 Task specifications

One specification per block, in `.ai\tasks\templates\task_template.yaml` shape. **Semantic code
units only — files, modules, classes, functions, methods. Never line numbers.**

An Implementor is handed **one** of these and nothing else. Read your block in §3 first if any
question in the spec is unclear; the spec does not restate the block.

---

### B1

```yaml
id: plan07-b1-nondestructive-batched-merge
title: Make the batched merge non-destructive until the whole merge has succeeded
priority: critical
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B1 — Make the batched merge non-destructive until the whole merge has succeeded
source_blocks: ["B1"]
source_findings: ["NET-001"]

description: >
  A batched merge currently deletes each batch's input segments the moment that batch
  merges, and deletes every accumulated batch temp on any non-success exit. If a later
  stage fails, both copies of the already-merged bytes are gone — the loss is total,
  deterministic, irreversible, and silent, because the residue reporter is guarded on
  count > 0 and emits nothing when nothing survived. Make the batch stage additive and
  move input deletion to the final merge's success path. Also make the reporter state a
  zero count instead of inferring it.

goals:
  - No failure shape of _merge_segments_batched destroys an input segment
  - The success path still removes every input segment, every batch temp and the final list
  - _log_preserve_segments reports unconditionally, count 0 included
  - The failure path of the merge leaves a recoverable working tree, and says so

files:
  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: _merge_batch_segments
      - type: function
        name: _perform_final_merge
      - type: function
        name: _merge_segments_batched
      - type: function
        name: _required_merge_bytes
      - type: function
        name: _check_merge_space
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _log_preserve_segments
    semantic_anchors:
      insert_after:
        type: call
        value: _log_preserve_segments

  - path: tests/test_ffmpeg_utils.py
    targets:
      - type: class
        name: TestMergeBatchSegments
      - type: class
        name: TestMergeSegmentsBatched

  - path: tests/test_segment_downloader.py
    targets:
      - type: function
        name: test_log_preserve_segments_reports_zero

changes:

  - action: modify
    description: >
      _merge_batch_segments stops unlinking its input segments and its concat list on
      success. The batch stage becomes purely additive. Update the function's docstring
      and the comment above the unlink loop, which currently states the opposite.
    code_hint: |
      # REMOVED from _merge_batch_segments' success path:
      #   for segment_path in batch_files:
      #       segment_path.unlink()
      #   file_list_path.unlink()
      # Inputs survive here; they are removed by _perform_final_merge on success.

  - action: modify
    description: >
      _perform_final_merge takes responsibility for deleting the input segments. It
      needs to know which paths were the originals, which today it is not told. Take
      the original segment paths alongside the batch temps and remove every one of them,
      plus every batch temp and the final list, on the success path only. Its failure
      path must remove nothing.
    code_hint: |
      # _perform_final_merge, success branch only — extend the existing cleanup:
      for path in (*temp_files, *input_segment_paths):
          path.unlink(missing_ok=True)
      final_list_path.unlink(missing_ok=True)
      # failure branch: return False  — remove nothing

  - action: modify
    description: >
      _merge_segments_batched narrows its finally block so accumulated batch temps are
      removed only when the whole operation succeeded. A stage failure must leave the
      already-produced temps on disk, because they are then the only copy of those bytes.
    code_hint: |
      # in _merge_segments_batched, replace the unconditional finally cleanup with a
      # success-path cleanup; on any failure return value, leave temp_dir contents intact

  - action: modify
    description: >
      _log_preserve_segments emits its record unconditionally. Remove the count > 0
      gate. Do NOT exclude batch_*.ts from the count — that is phase 07's ART-004.
    code_hint: |
      # before:
      #   if segment_count > 0:
      #       logger.info("preserving_segments_for_resume", count=segment_count)
      logger.info(
          "preserving_segments_for_resume",
          count=segment_count,
          segments_dir=str(segments_dir),
      )

  - action: review_only
    description: >
      _required_merge_bytes and _check_merge_space. Re-read the docstring's invariant
      ("the segments and a full copy of them at the same time") and state in the block
      report whether it still holds. Do NOT change the 2x multiplier — that is phase
      07's ART-012.
    code_hint: |

  - action: edit_test
    description: >
      Re-scope test_merge_batch_removes_input_files_on_success. It currently asserts the
      defect. Split it: a successful BATCH stage preserves its inputs; the FINAL stage is
      what removes them. Rule 2 — fix the test, do not distort the code.
    code_hint: |

  - action: add_test
    description: >
      Three _merge_segments_batched-level cases driven with a local stub standing in for
      the process launch (never a real ffmpeg, never a network): final-stage failure leaves
      every original; second-batch failure leaves the failed batch's inputs AND the earlier
      batch temps; success cleans everything up.
    code_hint: |

  - action: add_test
    description: >
      _log_preserve_segments emits its record for a directory containing zero segments.
    code_hint: |

acceptance_criteria:
  - A final-stage failure leaves every original segment on disk
  - A second-batch failure leaves the failed batch's segments and the earlier batch temps on disk
  - A successful merge removes every input segment, every batch temp and the final list
  - _log_preserve_segments emits a record for an empty directory
  - _check_merge_space is unchanged; the 2x multiplier is unchanged
  - No glob is changed to exclude batch_*.ts
  - The block does not delete final_list.txt on the failure path
  - test_final_merge_removes_temp_files and test_final_merge_removes_final_list stay green unchanged
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B2

```yaml
id: plan07-b2-val-001-connection-ceiling-figure
title: Correct the cross-phase connection-ceiling figure in the source report
priority: high
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B2 — Correct the cross-phase connection-ceiling figure in the source report
source_blocks: ["B2"]
source_findings: ["phase03/VAL-001"]

description: >
  Two phases stated incompatible facts about the same connection ceiling. Phase 03's
  NET-014 said the connector is a process-wide ceiling of 10 and that the 4x4 product is
  bounded by it; phase 04's CON-009 says the ceiling is per download (4 x 10 = 40). The
  evidence supports CON-009: _create_connector has one call site, inside
  _run_download_session, which runs once per video, each paired with its own ClientSession.
  The validated artifact's NET-014 already carries the correction. The wrong figure
  survives only in the read-only source report.

goals:
  - Remove the wrong figure from the source report
  - Match the adjudicated figure exactly
  - Deliberately break the "source report is unmodified" invariant, and say so
  - Leave the validated artifact byte-identical

files:
  - path: .ai/audit/03-network-resilience/findings.md
    targets:
      - type: section
        name: NET-014
    semantic_anchors:
      insert_before:
        type: paragraph
        value: "The remedy"

  - path: .ai/audit/99-validation/03-network-resilience-validated-findings.md
    targets:
      - type: document
        name: validated-findings
    semantic_anchors:

changes:

  - action: modify
    description: >
      In NET-014's consequence text only, restate the arithmetic: the TCPConnector
      literal is PER DOWNLOAD, not process-wide; the aggregate ceiling is
      10 x max_concurrent_downloads (40 at the default, 160 at the declared ceiling);
      no process-wide bound exists. Cross-reference CON-009 as the owner of the literal
      and retain the seam both findings already declare. Change nothing else in the
      report — not the finding's ID, severity, type, classification, description,
      evidence or recommendation.
    code_hint: |
      # The literal in _create_connector is PER DOWNLOAD: it has exactly one call site,
      # inside _run_download_session, which runs once per video, and each call is paired
      # with its own ClientSession. There is no process-wide pool. The aggregate ceiling
      # is therefore 10 x max_concurrent_downloads — 40 at the default, 160 at the
      # declared ceiling. See CON-009 (phase 04), which owns the literal.

acceptance_criteria:
  - The source report no longer asserts a process-wide ceiling of 10, nor that 4x4=16 is bounded by it
  - The corrected statement matches CON-009 in substance and cites it
  - The seam is retained: CON-009 is cross-referenced as the literal's owner
  - The validated findings artifact is byte-identical before and after
  - Nothing under src/ or tests/ is touched
  - No finding's ID, severity, type or classification in the source report is altered
  - The block report names the invariant it breaks and the authority for the corrected figure
```

---

### B3

```yaml
id: plan07-b3-val-004-role-label-and-executor
title: Add the missing finding label to the validator's role file and reconcile the unlaunchable executor
priority: medium
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B3 — Add the missing finding label to the validator's role file, and reconcile the unlaunchable executor
source_blocks: ["B3"]
source_findings: ["phase03/VAL-004"]

description: >
  The report format defines four type labels; the validator's role file lists three, in
  both places it enumerates them, omitting RUNTIME-ERROR — the label 8 of phase 03's 18
  findings use, including its only irreversible-loss finding. Separately, the format names
  an executor role (audit-executor) that does not exist in the role roster. Adopt plan
  05 Block 9's decision D3, which resolved the second half in favour of the launched
  role. Do NOT restamp the four existing findings reports.

goals:
  - Make each role file's label list exactly the format's four labels
  - Make the format's declared executor a role that exists and is launched
  - Leave the four existing reports byte-identical
  - Claim ownership away from plan 05 Block 9, which did not land

files:
  - path: .kilo/agents/validator.md
    targets:
      - type: section
        name: finding type labels
    semantic_anchors:

  - path: .kilo/agents/auditor.md
    targets:
      - type: section
        name: finding type labels
    semantic_anchors:

  - path: .ai/audit/templates/audit-findings.md
    targets:
      - type: frontmatter
        name: agent
      - type: field
        name: Executor
    semantic_anchors:
      insert_before:
        type: field
        value: "Type"

changes:

  - action: modify
    description: >
      Add RUNTIME-ERROR to BOTH label lists in .kilo/agents/validator.md and to the one in
      .kilo/agents/auditor.md, so each list matches the format's four-label enumeration.
      Add no other label; remove and reorder none.
    code_hint: |
      # SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR

  - action: modify
    description: >
      In .ai/audit/templates/audit-findings.md, replace audit-executor in the frontmatter
      `agent:` key and in the **Executor:** header with the role the pipeline actually
      launches. Adopt plan 05 Block 9's decision D3 verbatim; do not re-open it.
    code_hint: |
      # plan 05 Block 9 decision D3: the LAUNCHED role is correct; the format's
      # audit-executor is the defective side. auditem multi-phase launches `auditor`
      # for a phase and `validator` for a validation.

  - action: review_only
    description: >
      The four existing .ai/audit/*/findings.md reports keep their historical
      audit-executor stamp — they are a record of what ran, not a defect. Do not
      restamp them. Do not touch .kilo/rules/project.md.
    code_hint: |

acceptance_criteria:
  - RUNTIME-ERROR appears in both lists in validator.md and in the list in auditor.md
  - Each list has exactly the four labels the format defines
  - audit-executor appears zero times in the template after the change
  - The role the template now names exists in .kilo/agents/ and is a launched role
  - The four existing .ai/audit/*/findings.md files are byte-identical
  - .kilo/rules/project.md is byte-identical
  - The template's decision slot (added by feb0a40) is untouched and still present
  - .kilo/commands/audit/audit-multi-phase.md is byte-identical
  - The block report records that plan 05 Block 9 is superseded by this plan
```

---

### B4

```yaml
id: plan07-b4-manifest-retry-policy-base-address-and-pause
title: Give the manifest layer a retry policy, the address it used, and the shared pause
priority: high
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B4 — Give the manifest layer a retry policy, the address it actually used, and the shared pause
source_blocks: ["B4"]
source_findings: ["NET-009", "NET-004", "NET-002", "NET-010"]
source_intra_block_order: ["NET-009", "NET-004", "NET-002", "NET-010"]

description: >
  Four accepted findings prescribe edits inside one 41-line function, two of them on the
  same two lines; all four also edit the same five-test class. They land as ONE change.
  Intra-block order is NET-009, then NET-004, then NET-002, then NET-010: NET-009 first
  so the shared pause's key and duration are correct before NET-002 copies its semantics;
  NET-004 next because it owns the signature and the return contract; then the loop body.
  This block resolves VAL-002 and conflicts C1 and C7.

goals:
  - Every retryable status on the manifest request is retried with a measured, interruptible delay and the shared pause notified
  - Every non-200 outcome records its status
  - A refresh switches the base address before the credential is written, and the parts are requested from the refreshed base
  - The shared per-origin pause is reachable from the manifest, sequential and in-process extraction sites, keyed on the origin
  - The two media-part strategies agree on retrying a transport failure, and neither sleeps after its final attempt

files:
  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _notify_backoff_for_retryable_status
      - type: function
        name: _is_retryable_status
      - type: function
        name: _should_continue_on_retry
      - type: function
        name: _fetch_playlist_with_retry
      - type: function
        name: _handle_token_refresh
      - type: function
        name: _download_segment_sequential
      - type: function
        name: _run_download_session
      - type: class
        name: DownloadPolicy
    semantic_anchors:
      insert_after:
        type: function_call
        value: _is_retryable_status
      insert_before:
        type: return_statement

  - path: src/vkdownloader/services/downloader_throttle.py
    targets:
      - type: class
        name: URLBackoffCoordinator
      - type: method
        name: pause
      - type: method
        name: wait_if_paused
      - type: function
        name: _retry_429_with_backoff
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/services/extractor.py
    targets:
      - type: method
        name: _extract_with_ytdlp
    semantic_anchors:
      insert_before:
        type: call
        value: run_in_executor

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: download_with_ytdlp_with_resume_fallback
    semantic_anchors:
      insert_after:
        type: call
        value: _compute_backoff_delay

  - path: tests/test_segment_downloader.py
    targets:
      - type: class
        name: TestFetchPlaylistWithRetry
    semantic_anchors:

  - path: tests/test_downloader_throttle.py
    targets:
      - type: class
        name: TestRetryableStatusCodes
      - type: class
        name: TestRetry429WithBackoff
    semantic_anchors:

changes:

  - action: modify
    description: >
      NET-009. _notify_backoff_for_retryable_status keys on the ORIGIN under pressure
      rather than the page URL, and its duration becomes derived rather than the 10.0
      literal. Rename URLBackoffCoordinator's key parameter to name what it keys on. Its
      type stays str. Update all three call sites.
    code_hint: |
      await backoff_coordinator.pause(origin_key, _pause_duration_seconds(settings))
      # origin_key is derived from the resource about to be requested — its netloc.
      # DEFERRED: exact key derivation and duration source. See spec §3.2 items 3 and 5.

  - action: modify
    description: >
      NET-004. _fetch_playlist_with_retry returns the address the manifest actually
      succeeded from, alongside the playlist text. _run_download_session builds
      DownloadPolicy.m3u8_url from that address, not from the original argument. The
      refreshed cookie is written only AFTER the base is switched.
    code_hint: |
      # DEFERRED: the return shape. A 2-tuple, a frozen dataclass, or a NamedTuple.
      # The house pattern for an internal DTO is a dataclass (SegmentTask, DownloadPolicy,
      # FfmpegProgress); rule 5 favours the tuple. See spec §3.2 item 1.

  - action: modify
    description: >
      NET-002. The manifest layer gets the same policy table the media-part layers use:
      a computed delay via _compute_backoff_delay, awaited via _wait_with_shutdown, the
      shared pause notified, the status logged on every non-200 outcome. 403 and 410 stay
      on the refresh path. The transport-failure branch's bare continue gains a delay and
      notifies the shared pause.
    code_hint: |
      if not _is_retryable_status(status):
          logger.info("playlist_fetch_status", status=status, attempt=attempt, url=...)
          return None
      delay = _compute_backoff_delay(status, attempt, _parse_retry_after(response))
      if await _wait_with_shutdown(delay, shutdown_event, 0, current_url):
          return None
      # DEFERRED: the retryable set. See spec §3.2 item 2 and conflict C7.

  - action: modify
    description: >
      NET-010. _retry_429_with_backoff applies _should_continue_on_retry (or its
      equivalent) so the FINAL attempt does not sleep, and retries a transport-level
      failure to the same max_retries budget the parallel strategy uses instead of
      returning None on the first except. Do not let two sub-edits each add a predicate.
    code_hint: |
      if not _should_continue_on_retry(status, attempt, max_retries):
          break   # no wait after the final attempt

  - action: modify
    description: >
      NET-009. _download_segment_sequential gains the coordinator parameter and consults
      the shared pause. DownloadPolicy carries the coordinator to the parallel path. The
      in-process extraction entry point consults the pause before its first request — do
      NOT move that path's own timeout semantics, which the finding disclaims.
    code_hint: |
      # DEFERRED: how the in-process extraction reaches a per-batch coordinator. The
      # repository already binds one per-context primitive with a ContextVar
      # (get_shutdown_event). See spec §3.2 item 4.

  - action: edit_test
    description: >
      Re-scope ALL FIVE tests in TestFetchPlaylistWithRetry. They pin the current
      contract: the bare-string return, the single-attempt behaviour, and the absent
      coordinator. Rule 2 — fix the tests, do not distort the code. Two of them patch
      _fetch_single_playlist and _handle_token_refresh POSITIONALLY: do not change those
      two helpers' signatures.
    code_hint: |

  - action: edit_test
    description: >
      CONDITIONAL. TestRetryableStatusCodes::test_excludes_non_retryable_codes asserts the
      current set's exact composition. Edit it only if the retryable set is widened; if a
      manifest-local set is chosen instead, leave it untouched and pin the manifest set in
      a new test.
    code_hint: |

  - action: add_test
    description: >
      Per-status attempt counts and a non-zero inter-request gap; the coordinator
      receives pause and wait_if_paused at the manifest and sequential sites; the
      returned base address is the refreshed one; the headers rewrite is ordered after
      the base switch. MagicMock sessions only — the suite has no aiohttp fixture and
      this block must not add one.
    code_hint: |

acceptance_criteria:
  - A retryable manifest status is retried up to max_retries with a measured delay, notifies the pause, and is logged
  - 403 and 410 still enter the refresh path
  - A non-retryable status returns None after one attempt and is recorded
  - A manifest transport failure is retried with a non-zero delay
  - After a refresh, the parts are requested against the refreshed base and the cookie is written after the base switch
  - The shared pause is consulted and set at the manifest, sequential and in-process extraction sites, keyed on the origin
  - _retry_429_with_backoff does not wait after its final attempt and retries a transport failure to the same budget
  - The two positional patches of _fetch_single_playlist and _handle_token_refresh still work unchanged
  - The four forks in spec §3.2 are each decided and recorded in the block report
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B5

```yaml
id: plan07-b5-stream-enumeration-predicates-and-ranker
title: Read the stream's format by its parsed path and rank a placeholder height as absent
priority: medium
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B5 — Read the stream's format by its parsed path, and rank a placeholder height as absent
source_blocks: ["B5"]
source_findings: ["NET-017"]

description: >
  Three enumeration predicates read format metadata by inspection rather than by
  structure: a codec key tested for one literal, a format classified by a substring
  anywhere in the reference, and a height treated as present when it is zero. The two
  ranker keys in QualitySelector are mutual inverses and both rank a placeholder above an
  absent value, so best and worst select the SAME record from a set carrying no resolution
  information. This block settles what a quality label may be and is the head of the C3
  chain — B7 and B8 depend on it.

goals:
  - Classify a format by the parsed path's suffix, not a substring over the whole reference
  - Treat height <= 0 as absent in the label and in both ranker keys
  - Stop the two ranker keys from being inverses on a placeholder
  - Replace the unexpressive audio filter with a stated presence rule

files:
  - path: src/vkdownloader/services/extractor.py
    targets:
      - type: function
        name: _build_streams
    semantic_anchors:
      insert_after:
        type: function_call
        value: urlparse
      insert_before:
        type: return_statement

  - path: src/vkdownloader/services/quality.py
    targets:
      - type: method
        name: _get_fallback_stream
      - type: method
        name: select
      - type: method
        name: _find_quality_match
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: tests/test_extractor.py
    targets:
      - type: class
        name: TestBuildStreams
    semantic_anchors:

  - path: tests/test_quality_selector.py
    targets:
      - type: function
        name: test_placeholder_height_is_not_a_best_candidate
    semantic_anchors:

changes:

  - action: modify
    description: >
      _build_streams classifies the format from the parsed path's suffix instead of a
      substring over the whole reference, so a progressive address whose query carries
      .m3u8, or that lives in a directory named with it, is no longer misclassified.
    code_hint: |
      # before: StreamFormat.HLS if ".m3u8" in format_url else StreamFormat.MP4
      suffix = Path(urlparse(format_url).path).suffix.lower()
      stream_format = StreamFormat.HLS if suffix in (".m3u8", ".m3u") else StreamFormat.MP4

  - action: modify
    description: >
      _build_streams' quality label treats height <= 0 as absent, matching the ranker
      change. A height of 0 and an absent height produce the same label.
    code_hint: |
      # before: quality=f"{height}p" if height else "unknown"
      has_height = height is not None and height > 0
      quality = f"{height}p" if has_height else _HEIGHTLESS_LABEL

  - action: modify
    description: >
      The audio filter. `f.get("vcodec") == "none"` excludes one literal and cannot
      distinguish "no codec key" from "video". DEFERRED — see spec §3.3. Candidate rules:
      require vcodec present; require height or width present; require vcodec present and
      not "none". State the chosen rule, its counter-examples, and why the rejected rules
      are worse. Do not assert anything about what a real origin returns.
    code_hint: |
      # DEFERRED to this block's Planner. See spec §3.3.

  - action: modify
    description: >
      Both ranker keys in _get_fallback_stream and select must stop being mutual inverses
      on a placeholder. A set of {height=0, height=None} must not return the same record
      for best and for worst.
    code_hint: |
      # the two keys today:
      #   max(streams, key=lambda s: (s.height is not None, s.height or 0))
      #   min(streams, key=lambda s: (s.height is None,    s.height or 0))
      # a placeholder must rank BELOW an absent value, not above it, in both directions.
      def _is_measured(s: Stream) -> bool:
          return s.height is not None and s.height > 0

  - action: modify
    description: >
      _find_quality_match must accept every label _build_streams can now produce,
      including the heightless one.
    code_hint: |

  - action: add_test
    description: >
      The two misclassification shapes (query carries .m3u8, directory named .m3u8), the
      counter-case (query carries .mp4), and the height=0 label. Plus a {0, None} set
      asserted SEPARATELY for best and for worst, so a re-inversion fails one assertion.
    code_hint: |

acceptance_criteria:
  - A progressive address whose query carries .m3u8 is classified mp4
  - A progressive address in a directory named *.m3u8 is classified mp4
  - An HLS address whose query carries .mp4 is classified hls
  - height=0 produces the same label as no height
  - From {height=0, height=None}, best and worst return different records
  - The audio filter follows the rule stated in the block report
  - list_available_qualities is unchanged for the existing nine members, and every emitted label is accepted by _find_quality_match
  - The existing TestBuildStreams and test_quality_selector cases stay green unchanged
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B6

```yaml
id: plan07-b6-normalize-url-no-invented-host
title: Make the address normaliser stop inventing a host
priority: low
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B6 — Make the address normaliser stop inventing a host
source_blocks: ["B6"]
source_findings: ["NET-016"]

description: >
  _normalize_url is a fall-through chain that promotes a bare relative path to a host
  (a/stream.m3u8 becomes https://a/stream.m3u8), returns an http:// address in
  plaintext, and carries a branch no input can reach (a string starting with // also
  starts with /, so the startswith("/") test already caught it). Drop candidates that do
  not resolve to an absolute https address; do NOT resolve a relative one against the
  page's origin — that would produce a plausible-looking wrong host, which is the same
  failure class this block removes.

goals:
  - No input makes the normaliser invent a host
  - No unreachable branch remains
  - No non-https candidate is appended to the discovered set
  - No constructor signature changes

files:
  - path: src/vkdownloader/infrastructure/network_monitor.py
    targets:
      - type: method
        name: _normalize_url
      - type: method
        name: _extract_urls_from_json
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: tests/test_browser_infrastructure.py
    targets:
      - type: class
        name: TestNetworkMonitor
    semantic_anchors:

changes:

  - action: modify
    description: >
      _normalize_url: delete the unreachable startswith("//") branch — it is dead by
      control flow, not by counting. Stop promoting a bare relative path to a host. Drop
      any candidate that does not resolve to an absolute https:// address, including
      http:// addresses. Do not change M3U8_PATTERN.
    code_hint: |
      # before (promotes a bare relative path to a host):
      #   if not url.startswith("http"):
      #       url = f"https://{url}"
      # after: only promote a form that actually names a host; drop anything else.
      #   https://host/path          -> unchanged
      #   //host/path                -> https://host/path
      #   host/path                  -> https://host/path
      #   /path, path, filename      -> DROPPED  (root-relative, relative, bare)
      #   http://host/path           -> DROPPED  (not https)

  - action: modify
    description: >
      _extract_urls_from_json must not append a value the normaliser could not resolve.
      A JSON value of 720/stream.m3u8 currently normalises to https://720/stream.m3u8 and
      is appended as a discovered address.
    code_hint: |

  - action: add_test
    description: >
      The nine-form address table, asserted as a data-driven table so a regression names
      the form that changed.
    code_hint: |

acceptance_criteria:
  - The nine-form table produces the results in spec §3 B6 criterion 1
  - _normalize_url contains no unreachable branch
  - A JSON value of 720/stream.m3u8 is not appended to the discovered set
  - M3U8_PATTERN is unchanged
  - NetworkMonitor's constructor signature is unchanged
  - The _intercept_response m3u8 branch is behaviourally unchanged
  - test_network_monitor_skips_oversized_body_without_content_length stays green unchanged
  - The block report states why dropping was chosen over resolving against page.url
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B7

```yaml
id: plan07-b7-captured-address-selection-and-label
title: Constrain the captured-address selection surface and make its label re-requestable
priority: high
depends_on: [plan07-b5-stream-enumeration-predicates-and-ranker]

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B7 — Constrain the captured-address selection surface, and make its label re-requestable
source_blocks: ["B7"]
source_findings: ["NET-008"]

description: >
  Captured addresses are appended in arrival order with no host, quality or playlist-type
  constraint, and the extraction surface takes element zero unconditionally — so a
  third-party host whose URL ends in .m3u8 and is fetched first becomes the delivered
  source. The labels it attaches are not members of the declared quality enumeration, so
  they cannot be re-requested. BLOCKED until a Researcher supplies the expected CDN host
  or suffix: the repository contains no host constant, allow-list or origin string, and a
  guessed suffix is worse than the current defect.

goals:
  - A captured address outside the expected host set is never offered to either transfer stage, and its rejection is logged
  - A media playlist is preferred over a manifest when both are captured
  - Every label the enumeration produces is a member the enumeration accepts
  - The alternatives list is deduplicated
  - The chosen host and label are recorded in one log record

files:
  - path: src/vkdownloader/infrastructure/network_monitor.py
    targets:
      - type: method
        name: _intercept_response
    semantic_anchors:
      insert_before:
        type: assignment
        value: self.m3u8_urls

  - path: src/vkdownloader/services/extractor.py
    targets:
      - type: method
        name: _extract_with_browser
    semantic_anchors:
      insert_before:
        type: call
        value: Stream

  - path: src/vkdownloader/models/enums.py
    targets:
      - type: enum
        name: QualityEnum
    semantic_anchors:
      insert_after:
        type: assignment
        value: WORST

  - path: src/vkdownloader/services/quality.py
    targets:
      - type: method
        name: _find_quality_match
      - type: method
        name: list_available_qualities
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: tests/test_extractor.py
    targets:
      - type: class
        name: TestExtractWithBrowser
    semantic_anchors:

  - path: tests/test_browser_infrastructure.py
    targets:
      - type: class
        name: TestNetworkMonitor
    semantic_anchors:

  - path: tests/test_quality_selector.py
    targets:
      - type: function
        name: test_produced_label_is_re_requestable
    semantic_anchors:

changes:

  - action: research_required
    description: >
      BLOCKING. Establish the expected CDN host or suffix for VK video segments, and its
      authority. The artifact explicitly declines to assert what a real origin serves and
      this audit had no network access. Record the deliverable in the block report and in
      a comment that names its authority. Do not guess: an over-narrow filter silently
      discards the only address and the download fails; an over-broad one is the status quo.
    code_hint: |

  - action: modify
    description: >
      The capture predicate gains a host constraint, and the selection prefers a media
      playlist over a manifest. Log the host and the label chosen. DEFERRED — how the host
      constraint is expressed (module constant, Settings field, or a netloc predicate) and
      whether the preference heuristic is available at all. See spec §3.5 items 2 and 4.
    code_hint: |

  - action: modify
    description: >
      QualityEnum gains the member for a heightless record, so the label the enumeration
      produces is one the enumeration accepts. Rule 10: a StrEnum member, never a literal.
      DEFERRED — a new member, or a mapping in _find_quality_match. See spec §3.5 item 3.
    code_hint: |
      class QualityEnum(StrEnum):
          ...
          BEST = "best"
          WORST = "worst"
          UNKNOWN = "unknown"   # the candidate name; the member itself is deferred

  - action: modify
    description: >
      The Stream record constructed in the browser extraction body stops asserting a
      quality it did not measure, and the selection stops being unconditionally element
      zero.
    code_hint: |

  - action: modify
    description: >
      list_available_qualities deduplicates its alternatives.
    code_hint: |

  - action: edit_test
    description: >
      test_browser_extraction_uses_first_m3u8_url pins the element-zero selection: it
      asserts streams[0].url == first_url and len(streams) == 1 from a two-element
      captured list. Both URLs share the host cdn.example.com and neither is
      distinguishable as media-vs-manifest, so a host filter ALONE leaves it green, but a
      PREFERENCE rule could change which one wins. Edit it or verify it green — and say
      which, and why. Do not delete it.
    code_hint: |

  - action: add_test
    description: >
      A captured list mixing an expected host, an unexpected host, a manifest and a media
      playlist: which survive, in what order, and that a rejected host is not offered. Plus
      the label round trip and the deduplicated alternatives list.
    code_hint: |

acceptance_criteria:
  - An out-of-set host is not offered to either transfer stage, and the rejection is logged with the host
  - A media playlist is preferred over a manifest when both are captured, and the preference is logged
  - The host and the label chosen are recorded in one log record
  - QualityEnum(label) succeeds for every label list_available_qualities emits
  - The alternatives list contains no duplicates
  - A heightless captured stream's label is accepted on re-request
  - The Stream record asserts no height or quality it did not measure
  - The expected host set is the Researcher's deliverable, recorded with its authority
  - No verification step contacts a network or a real origin
  - test_browser_extraction_uses_first_m3u8_url is either green unchanged (and the reason stated) or re-scoped (and the reason stated)
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B8

```yaml
id: plan07-b8-refresh-path-quality-selection
title: Select the requested quality from the refreshed stream set and record what was delivered
priority: high
depends_on:
  - plan07-b5-stream-enumeration-predicates-and-ranker
  - plan07-b7-captured-address-selection-and-label

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B8 — Select the requested quality from the refreshed stream set, and record what was delivered
source_blocks: ["B8"]
source_findings: ["NET-005"]

description: >
  _refresh_token_and_retry returns streams[0] unconditionally, with no quality argument in
  scope and no branch on the caller's selection, while the two sibling helpers in the same
  codebase each test QualityEnum.BEST and log both the requested and the selected value.
  Copy the sibling branch and the sibling record shape — do not design a new one. Tail of
  the C3 chain: needs B5's label rule and B7's constrained set.

goals:
  - The refresh returns the requested quality's stream, not element zero
  - One log record carries both the requested and the delivered label on every refresh
  - The numeric branch retains the preselected URL, explicitly, as the siblings do
  - The two sibling helpers are unchanged

files:
  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _refresh_token_and_retry
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/services/quality.py
    targets:
      - type: method
        name: select
    semantic_anchors:

  - path: tests/test_segment_downloader.py
    targets:
      - type: function
        name: test_refresh_selects_requested_quality
    semantic_anchors:

changes:

  - action: modify
    description: >
      _refresh_token_and_retry branches on the caller's quality, reusing QualitySelector
      over the refreshed streams when the request is BEST, and retaining the preselected
      URL when it is numeric — the same explicit branch _attempt_segment_resume and
      _resolve_cookies already use. One record carries the requested AND the delivered
      label. DEFERRED — how the caller's quality reaches this helper. See spec §3.6.
    code_hint: |
      # the sibling pattern to COPY, not redesign (ytdlp_downloader._attempt_segment_resume,
      # ytdlp_downloader._resolve_cookies): each tests quality_enum == QualityEnum.BEST
      # and emits a record carrying the quality fields.
      if quality_enum == QualityEnum.BEST:
          selected = QualitySelector().select(streams, QualityEnum.BEST)
      else:
          selected = _preselected   # the caller's already-selected stream
      logger.info(
          "token_refreshed_stream_selected",
          requested=str(quality_enum),
          delivered=selected.quality,
          url=str(selected.url),
      )

  - action: add_test
    description: >
      A BEST request with a multi-stream refreshed set (the result must not be element
      zero); a numeric request (the preselected URL is retained); and an assertion that
      one record carries both labels.
    code_hint: |

acceptance_criteria:
  - A BEST request selects via QualitySelector over the refreshed set
  - A numeric request retains the preselected URL and the record says so explicitly
  - Exactly one log record carries both the requested and the delivered value, on every refresh
  - The returned address is not unconditionally element zero
  - _attempt_segment_resume and _resolve_cookies are unchanged
  - TestResolveCookies and TestAttemptSegmentResumeQuality stay green unchanged
  - No error's alternatives rendering is touched (phase 08's carve-out)
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B9

```yaml
id: plan07-b9-ytdlp-selector-and-address-handoff
title: Give the child the selected address and stop inverting worst into best
priority: high
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B9 — Give the child the selected address, and stop inverting `worst` into `best`
source_blocks: ["B9"]
source_findings: ["NET-003"]

description: >
  The ladder selects a stream with QualitySelector.select and passes its URL as m3u8_url,
  but that URL never reaches the child — the child is given the page URL and a format
  selector derived from the REQUEST STRING, so QualityEnum.WORST (the string "worst",
  not a digit) becomes the literal selector "best". A user who asks for the worst quality
  receives the best stream, and nothing in the log distinguishes request from delivery.
  Split from the artifact's group 4: after NET-015's reduction this block shares no module
  with it.

goals:
  - A WORST request produces a worst selector, not best
  - The child's positional argument is the selected stream address, not the page URL
  - The selected address and the delivered format are logged, distinctly from the request
  - The app's stricter exact-label matching is preserved

files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _build_ytdlp_cli_command
      - type: function
        name: _download_with_ytdlp
      - type: function
        name: download_with_ytdlp_with_resume_fallback
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/services/downloader.py
    targets:
      - type: method
        name: download_video
    semantic_anchors:
      insert_after:
        type: assignment
        value: m3u8_url

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestYtdlpCliCommand
    semantic_anchors:

changes:

  - action: modify
    description: >
      The format-selector ternary. `quality_str.isdigit()` is false for "worst", so WORST
      falls into the "best" arm. DEFERRED — does the child receive the selected address
      (route a), or does it re-select and the selector is derived from the SELECTED
      stream's height with worst special-cased (route b)? See spec §3.7. If only one half
      is shipped, the block must say which and must not claim the other.
    code_hint: |
      # before: f"best[height<={q}]" if q and q.isdigit() else "best"
      # after (route a):  the selector is derived from the SELECTED stream, never from
      #   the request string; the request string no longer produces "best" by accident.
      # after (route b):  the worst member gets an explicit worst arm.

  - action: modify
    description: >
      _download_with_ytdlp gains the selected m3u8_url and hands it to the child as the
      positional argument, replacing the page URL. download_with_ytdlp_with_resume_fallback
      threads the address it already holds. downloader.download_video passes the address it
      already computes. NEVER implement this in downloader.py's re-export facade.
    code_hint: |
      # in _download_with_ytdlp, replace the positional argument:
      #   cmd.append(video_url)          # the page URL — the defect
      cmd.append(selected_stream_url)   # the address QualitySelector chose

  - action: modify
    description: >
      Log the selected address and the delivered format, in a record distinct from the
      request record. Today the only quality record on the path is the request echoed
      into starting_ytdlp_download.
    code_hint: |
      logger.info(
          "ytdlp_stream_selected",
          requested=quality,
          selected_url=_strip_auth_params(selected_stream_url),
          delivered_format=delivered_format,
      )

  - action: edit_test
    description: >
      test_cli_command_format_best_when_quality_not_digit is the worst->best inversion
      written as a specification. Its docstring says "when quality is non-numeric", so
      the best assertion is CORRECT and only the worst case is wrong. Re-scope into two
      assertions with two docstrings. Rule 2 — do not delete it, and do not distort the
      code for it.
    code_hint: |
      # split into:
      #   test_cli_command_format_best_for_best_quality   -> "best"  (unchanged assertion)
      #   test_cli_command_format_worst_for_worst_quality -> NOT "best"

  - action: add_test
    description: >
      That the positional argument is the selected address; a worst case in the per-member
      selector table.
    code_hint: |

acceptance_criteria:
  - Every numeric QualityEnum member yields best[height<=N]; best yields best; worst yields NOT best
  - The child's positional argument is the selected stream address, not the page URL
  - The delivered format and the selected address are logged in a record distinct from the request record
  - QualityNotAvailableError is still raised when no exact label matches; the app is not weakened
  - downloader.py's re-export facade is unchanged
  - The child's existing robustness flags are unchanged
  - The other 17 cases in TestYtdlpCliCommand and all 8 in TestYtDlpSubprocessShutdown stay green unchanged
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B10

```yaml
id: plan07-b10-ladder-handoff-agreement
title: Make the two ladder handoffs agree about the path they hand on
priority: medium
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B10 — Make the two ladder handoffs agree about the path they hand on
source_blocks: ["B10"]
source_findings: ["NET-015 (reduced: handoff-asymmetry half only)"]
out_of_scope: ["phase 07 ART-002 — the output_file / output_file.part probe and cleanup"]

description: >
  Two handoffs pass a failed stage's output path to the next stage. _attempt_segment_resume
  removes the predecessor's partial before handing on; perform_download's ffmpeg branch goes
  from download_with_ffmpeg returning None straight into download_hls_with_resume with the
  SAME output_file and no unlink — so the truncated file the ffmpeg stage left is still
  sitting at the path the merge stage is about to write. The one-name predicate and the
  DF-008 cleanup are phase 07's ART-002 and are NOT in this block.

goals:
  - The ffmpeg branch does not leave its partial at the path it hands on
  - The yt-dlp handoff's existing unlink is unchanged
  - The receiving stage's contract about a pre-existing file is stated
  - ytdlp_downloader.py is byte-identical — this is the scope boundary with phase 07

files:
  - path: src/vkdownloader/services/downloader.py
    targets:
      - type: method
        name: download_video
    semantic_anchors:
      insert_after:
        type: call
        value: download_with_ffmpeg
      insert_before:
        type: call
        value: download_hls_with_resume

  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: _merge_segments_batched
    semantic_anchors:

  - path: tests/test_downloader.py
    targets:
      - type: class
        name: TestPerformDownload
    semantic_anchors:

changes:

  - action: review_only
    description: >
      What download_with_ffmpeg actually leaves at the output path on each of its failure
      modes, and whether the two are distinguishable from the return value alone. The
      answer decides whether an unlink is sufficient.
    code_hint: |

  - action: modify
    description: >
      The ffmpeg branch removes the failed stage's partial before handing the path on, or
      the receiving stage refuses a pre-existing file. DEFERRED — which. See spec §3.8.
      Do not change ffmpeg's own behaviour; the merge there is read-only obligation.
    code_hint: |
      # candidate (a), mirroring _attempt_segment_resume's existing behaviour:
      if ffmpeg_result is None:
          partial = validate_output_path(output_file, warning=False)
          try:
              partial.unlink(missing_ok=True)
          except OSError:
              logger.warning("failed_to_cleanup_partial_file", path=str(partial))
          return await download_hls_with_resume(...)

  - action: add_test
    description: >
      A stubbed download_with_ffmpeg that writes a non-empty partial and returns None,
      then an assertion about what the segment stage receives. This handoff has NO test
      today — it is the sharpest coverage gap in this plan.
    code_hint: |

acceptance_criteria:
  - After an ffmpeg stage returning None with a non-empty partial written, the segment stage does not find that partial
  - _attempt_segment_resume's existing unlink is unchanged
  - The receiving stage's contract for a pre-existing file is stated in a comment or docstring
  - ytdlp_downloader.py is byte-identical before and after
  - No test is deleted and no test is weakened
  - TestYtDlpSubprocessShutdown and TestResolveCookies stay green unchanged
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B11

```yaml
id: plan07-b11-timeout-composition-and-merge-budget
title: Separate the merge budget from the HTTP budget and compose the client timeout once
priority: high
depends_on: [plan07-b1-nondestructive-batched-merge]

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B11 — Separate the merge budget from the HTTP budget, and compose the client timeout once
source_blocks: ["B11"]
source_findings: ["NET-006", "NET-007"]
adopts_from: ".ai/plans/05-entry-architecture-audit-fixes.md Block 8 (ENT-010) — NOT LANDED; ownership moved here"

description: >
  Three byte-identical ClientTimeout compositions exist in three modules, with a read term
  that exceeds the total containing it at the configured floor and a connect term that
  duplicates one already set. Separately, a setting declared as a per-HTTP-request timeout
  is applied unchanged, PER SUBPROCESS, as the budget for a purely local concat — so
  lowering it to shorten network stalls also caps each merge stage, which is precisely what
  makes NET-001's loss likely. Collapse the compositions into one helper and give the merge
  stages their own budget, passed once. ADOPTS plan 05 Block 8 (ENT-010): the nine literal
  = 300 defaults. MUST NOT add a whole-operation budget to the two transfer stages.

goals:
  - The composed ClientTimeout is built in exactly one place
  - No read term exceeds the total that contains it, at any value in range
  - The merge stages' budget is not the HTTP setting, and is passed once for the operation
  - Lowering download_timeout no longer shortens any merge stage
  - All nine = 300 literals are derived from the settings model

files:
  - path: src/vkdownloader/services/downloader_throttle.py
    targets:
      - type: function
        name: _retry_429_with_backoff
      - type: module_constant
        name: _DEFAULT_DOWNLOAD_TIMEOUT
    semantic_anchors:
      insert_after:
        type: import
        value: aiohttp

  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: class
        name: DownloadPolicy
      - type: function
        name: _download_segment_sequential
      - type: function
        name: _download_segment_parallel
      - type: function
        name: _run_parallel_download_with_backoff
      - type: function
        name: _fetch_playlist_with_retry
      - type: function
        name: _tally_and_merge
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: _merge_batch_segments
      - type: function
        name: _perform_final_merge
      - type: function
        name: _merge_segments_batched
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/config.py
    targets:
      - type: class
        name: Settings
    semantic_anchors:
      insert_after:
        type: field
        value: download_timeout

  - path: docs/11-guides/configuration.md
    targets:
      - type: section
        name: download_timeout
    semantic_anchors:

  - path: .env.example
    targets:
      - type: section
        name: download_timeout
    semantic_anchors:

  - path: tests/test_packaging.py
    targets:
      - type: constant
        name: EXPECTED_SDIST_ENTRIES
    semantic_anchors:

changes:

  - action: modify
    description: >
      Collapse the three identical ClientTimeout compositions into one helper. Remove
      sock_connect — it adds nothing connect does not already bound. Make sock_read a
      function of the setting rather than the literal 60. DEFERRED — the helper's
      placement (a new src/ module trips EXPECTED_SDIST_ENTRIES; ffmpeg_utils.py imports
      neither downloader_throttle nor config) and the sock_read shape. See spec §3.9
      items 1 and 2.
    code_hint: |
      def _client_timeout(download_timeout: int) -> aiohttp.ClientTimeout:
          return aiohttp.ClientTimeout(
              total=float(download_timeout),
              connect=min(30.0, download_timeout / 4),
              sock_read=...,   # DEFERRED: min(60, n) | n | its own bounded setting
              # sock_connect REMOVED — redundant with connect
          )

  - action: modify
    description: >
      The merge stages get their own budget, passed ONCE for the whole operation rather
      than per subprocess. The hand-off that currently passes float(download_timeout) into
      _merge_segments_batched is the conflation point. DEFERRED — the formula (a new
      bounded Settings field | derived from stage count and measured segment size | a
      per-stage constant) and whether the new setting gets a CLI option. See spec §3.9
      items 3 and 4.
    code_hint: |
      # before: _merge_segments_batched(..., download_timeout=float(policy.download_timeout))
      #   -> _await_ffmpeg_with_timeout(process, download_timeout)   # PER SUBPROCESS
      # after:  one budget for the whole merge operation
      # DEFERRED: the formula. The block report states the worst case at the default
      # for 250 segments and at the floor.

  - action: modify
    description: >
      ADOPTED FROM PLAN 05 BLOCK 8 (ENT-010): replace the nine literal = 300 defaults —
      DownloadPolicy.download_timeout plus five int defaults in segment_downloader.py and
      three float defaults in ffmpeg_utils.py — with the value derived from the settings
      model, as downloader_throttle.py already does. Plan 05's verified acyclicity
      argument for the ffmpeg_utils -> downloader_throttle edge is ADOPTED, not re-derived.
    code_hint: |
      download_timeout: int = _DEFAULT_DOWNLOAD_TIMEOUT   # not 300

  - action: modify
    description: >
      If a new Settings field is added: a Pydantic field with a Field(...) description
      that no longer implies it bounds only HTTP. The description and the configuration
      guide's row are the statement-level collision C12 with B15 — write them ONCE here.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT wrap either process.wait() in the two transfer stages in asyncio.wait_for.
      The design decision recorded in ytdlp_downloader.py is that yt-dlp carries its own
      --socket-timeout, -R, --fragment-retries and -N, and that no application-level
      download timeout is imposed, avoiding premature kill of legitimate long downloads.
      That comment must be byte-identical after this block.
    code_hint: |

  - action: add_test
    description: >
      The composed timeout read back at the floor (30), the default (300) and the ceiling
      (3600) as a table. This is the suite's FIRST timeout assertion — tests/ currently
      contains zero occurrences of aiohttp or ClientTimeout.
    code_hint: |

  - action: add_test
    description: >
      That the merge stages receive the MERGE budget, not the HTTP setting. Plus the new
      Settings field's resolution in test_config.py, if one was added.
    code_hint: |

acceptance_criteria:
  - The composed ClientTimeout is built in exactly one place and all three sites call it
  - At 30 / 300 / 3600, no read term exceeds the total that contains it, and the connect term is not redundant with itself
  - The merge budget is not the HTTP setting and is passed once, not per subprocess
  - The block report states the worst-case merge budget at the default for 250 segments
  - Lowering download_timeout no longer shortens any merge stage
  - All nine = 300 literals are derived from the settings model
  - ytdlp_downloader.py's no-application-level-timeout comment is byte-identical, and neither transfer-stage process.wait() is wrapped
  - If a field was added: it is a Pydantic field with a description, in .env.example with a value CONSTRUCTED AGAINST THE MODEL and recorded, and in the configuration guide
  - EXPECTED_SDIST_ENTRIES is edited in the same change if and only if a file was added
  - TestMergeFreeSpaceProbe, TestSequentialDownloadMode, TestDownloadSegmentRealExecution and TestMergeSegmentsBatchedRealExecution stay green unchanged
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B12

```yaml
id: plan07-b12-url-gate-and-single-identifier
title: Anchor the URL gate to an origin and derive the identifier once
priority: high
depends_on: [plan07-b5-stream-enumeration-predicates-and-ranker]

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B12 — Anchor the URL gate to an origin and derive the identifier once
source_blocks: ["B12"]
source_findings: ["NET-012"]

description: >
  Acceptance is an unanchored substring search over the whole reference, admitting a
  foreign origin whose path embeds the pattern, a foreign origin whose query value embeds
  it, the bare pattern with no origin, a negative owner component, and the canonical form
  with a trailing path. The parser then derives the identifier correctly and four consumers
  re-derive a DIFFERENT one by slicing the raw string — so the identifier that names the
  video in the progress display is not the one the parser produced. BLOCKED on a Researcher
  for the accepted URL set; may share B7's Researcher deliverable but must not wait for
  B7's filter to land.

goals:
  - Acceptance is anchored to the parsed origin and path, not a substring of the reference
  - The identifier is derived once and the four consumers receive it
  - The operator-visible skip outcome for a rejected URL is unchanged
  - The accepted-form table after the change is stated

files:
  - path: src/vkdownloader/services/extractor.py
    targets:
      - type: class
        name: VKVideoExtractor
      - type: constant
        name: VIDEO_ID_PATTERN
      - type: function
        name: is_valid_video_url
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/cli.py
    targets:
      - type: function
        name: batch
    semantic_anchors:
      insert_after:
        type: call
        value: is_valid_video_url

  - path: src/vkdownloader/services/downloader.py
    targets:
      - type: method
        name: download_video
    semantic_anchors:

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _download_with_ytdlp
    semantic_anchors:

  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _run_download_session
      - type: function
        name: _download_segments_from_playlist
    semantic_anchors:

  - path: tests/test_extractor.py
    targets:
      - type: function
        name: test_video_url_acceptance_table
    semantic_anchors:

  - path: tests/test_cli.py
    targets:
      - type: class
        name: TestBatchCommand
    semantic_anchors:

changes:

  - action: research_required
    description: >
      BLOCKING. Establish the expected host and the accepted URL set for the batch-list
      gate, and whether a negative owner id is genuinely invalid. The finding's
      accept/reject table is a STRING-TEST table and says nothing about which accepted
      forms the product wants. May share B7's Researcher deliverable; must not wait for
      B7's filter. See spec §3.10 item 1.
    code_hint: |

  - action: modify
    description: >
      is_valid_video_url anchors acceptance to the parsed origin and the parsed path
      instead of a substring over the whole reference. Its docstring currently says
      "contains" — which is why the code matches its own contract and the contract is the
      weak thing. The docstring must be updated with the behaviour. A negative owner
      component is rejected at acceptance, or its acceptance is explicitly retained with a
      stated reason. DEFERRED — see spec §3.10 item 3.
    code_hint: |
      parsed = urlparse(url)
      if parsed.scheme not in ("http", "https"):
          return False
      if parsed.netloc.lower() != _EXPECTED_HOST:
          return False
      match = _ANCHORED_VIDEO_ID_PATTERN.match(parsed.path)   # anchored, not searched
      return match is not None and not match.group("owner").startswith("-")

  - action: modify
    description: >
      DEFERRED — where the parsed identifier lives: a field on HLSDownloadRequest (a
      Pydantic model whose docstring says it holds only pure data fields), a field on the
      video record, or a parameter on four call chains. See spec §3.10 item 2.
    code_hint: |

  - action: modify
    description: >
      Replace the four url.split("_")[-1] slices — in downloader.download_video,
      ytdlp_downloader._download_with_ytdlp, segment_downloader._run_download_session and
      segment_downloader._download_segments_from_playlist — with the identifier the parser
      produced. Co-locates with B9 (conflict C10) and B4 (C11): different statements, no
      ordering constraint, but re-read before editing.
    code_hint: |
      # before: video_id = url.split("_")[-1]        # yields "456" for a foreign-origin URL
      # after:  video_id = parsed.video_id_full      # yields what the parser derived

  - action: add_test
    description: >
      The accept/reject table as DATA-DRIVEN cases, including the near misses that must
      stay rejected (video_123_456, videos-123_456, video-1O3_456, the empty string) and
      the forms currently accepted that must stop being. Plus one test per rewired consumer
      asserting it receives the PARSED identifier — four consumers, four assertions.
    code_hint: |

acceptance_criteria:
  - A foreign origin whose path embeds the pattern is rejected
  - A foreign origin whose query value embeds the pattern is rejected
  - The bare pattern with no scheme or origin is rejected
  - A negative owner component is rejected at acceptance, or its retention is explicitly stated
  - The canonical form with a trailing path is handled by the same rule as without one
  - No url.split("_")[-1] remains in the four consumer sites
  - Each consumer receives exactly the identifier the parser produced
  - The batch skip path's message and exit code are unchanged (phase 08's OUT-009)
  - The accepted-form table after the change is stated in the block report
  - The canonical sample_video_url fixture remains accepted
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B13

```yaml
id: plan07-b13-request-fidelity-and-declared-tls
title: Make the two surfaces of the third-party downloader present the same identity
priority: low
depends_on: [plan07-b5-stream-enumeration-predicates-and-ranker]

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B13 — Make the two surfaces of the third-party downloader present the same identity
source_blocks: ["B13"]
source_findings: ["NET-013"]
out_of_scope:
  - "throttled_rate's field description — already scoped to yt-dlp, validator-rejected"
  - "max_concurrent_downloads' field description — already records both levels, retained as NET-014"
  - "the parse site — DECLARED HERE, per conflict C8; B12 must not move it"

description: >
  The same third-party downloader presents two different identities to the origin: the
  in-process extraction surface sends the library's own default user agent and no referer,
  the child-process surface sends the configured agent and referer. Two of the four sites
  that can disable certificate verification do so without warning in their own module, and
  the browser's TLS posture is inherited rather than declared. LOW, advisory, no observed
  security, data-loss or correctness consequence — it ships because it is cheap.

goals:
  - Both surfaces present the same identity
  - Each un-warned ssl_verify flag site warns in its own module
  - The browser's TLS posture is declared rather than inherited
  - No verifier is enabled or disabled that was not before

files:
  - path: src/vkdownloader/services/extractor.py
    targets:
      - type: method
        name: _extract_with_ytdlp
    semantic_anchors:
      insert_after:
        type: assignment
        value: ydl_opts

  - path: src/vkdownloader/services/downloader.py
    targets:
      - type: method
        name: download_video
    semantic_anchors:
      insert_after:
        type: assignment
        value: nocheckcertificate

  - path: src/vkdownloader/infrastructure/browser.py
    targets:
      - type: function
        name: new_context
    semantic_anchors:
      insert_after:
        type: call
        value: timezone_id

  - path: tests/test_extractor.py
    targets:
      - type: function
        name: test_extract_with_ytdlp_carries_configured_identity
    semantic_anchors:

changes:

  - action: modify
    description: >
      The in-process option object gains the configured user agent and referer, matching
      what the argv builder already produces from the same Settings. DEFERRED — the
      library's option KEY NAMES. A wrong key name is silently ignored, which is the exact
      failure this block exists to fix, reproduced on the other surface. See spec §3.11
      item 1.
    code_hint: |
      # before: ydl_opts carries quiet, no_warnings, extract_flat, nocheckcertificate,
      #           socket_timeout, retries, fragment_retries, throttled_rate — and NO user
      #           agent and NO referer
      # after:  the configured user agent and referer are present, under the library's
      #          own key names. DEFERRED which names.

  - action: modify
    description: >
      Add a warning beside each of the TWO un-warned ssl_verify flag sites (in the
      extractor and in downloader), worded like the two that already warn. Do not touch
      the two existing warnings — no duplicate, no rewording.
    code_hint: |
      if not settings.ssl_verify:
          logger.warning("ssl_verification_disabled", surface="extractor")

  - action: modify
    description: >
      Pass the browser context's TLS posture EXPLICITLY. DEFERRED — derive it from
      ssl_verify, or declare the current inherited behaviour without changing it. The
      finding says "declared rather than inherited", which reads as the second, but the
      option's name invites the first, and the first is a BEHAVIOUR CHANGE. See spec §3.11
      item 2.
    code_hint: |
      context = await browser.new_context(
          viewport=...,
          user_agent=...,
          locale=...,
          timezone_id=...,
          ignore_https_errors=...,   # DEFERRED: the value
      )

  - action: add_test
    description: >
      That the option object carries the configured user agent and referer, matching the
      argv from the same Settings. Plus a warning assertion for each of the two new sites
      and one asserting NO duplicate at the two existing sites.
    code_hint: |

acceptance_criteria:
  - The in-process option object and the child argv carry the same user agent and referer
  - Each of the two un-warned ssl_verify sites warns in its own module
  - The two already-warning sites are unchanged — no duplicate, no rewording
  - The browser context's TLS posture is passed explicitly and is recorded as a declaration either way
  - throttled_rate's and max_concurrent_downloads' field descriptions are byte-identical
  - No verifier is enabled or disabled that was not before
  - test_extract_with_ytdlp_propagates_settings_to_ydl_opts stays green unchanged — VERIFY, do not assume: it asserts specific keys, not the absence of others
  - The parse site is declared in this block's report, and B12 does not move it
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B14

```yaml
id: plan07-b14-concurrency-levels
title: Stop using one setting as both the whole-video gate and the per-item request fan-out
priority: high
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B14 — Stop using one setting as both the whole-video gate and the per-item request fan-out
source_blocks: ["B14"]
source_findings: ["NET-014"]

description: >
  max_concurrent_downloads is declared for whole videos and applied both as the whole-item
  gate and as the per-item segment fan-out (and as the child's -N), so the effective
  simultaneous request count against one origin is the square of a value the operator
  raises to download videos in parallel. This is a PRODUCT decision with operator-visible
  semantics, expressed as a code change. BINDING ON THE COMMIT BODY (conflict C6): the
  aggregate ceiling is 10 x max_concurrent_downloads — 40 at the default, 160 at the
  ceiling — because each video carries its own connector paired with its own ClientSession.
  There is NO process-wide pool. MUST NOT touch TCPConnector(limit=10) — that is phase
  04's CON-009.

goals:
  - Exactly one level is governed by max_concurrent_downloads, and it is the level its description declares
  - The per-item fan-out and the child's -N are separately bounded and separately declared
  - The aggregate request count is expressible from the settings
  - The D-01 non-reentrant-semaphore invariant is preserved

files:
  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _run_download_session
      - type: function
        name: _create_connector
    semantic_anchors:
      insert_before:
        type: call
        value: asyncio.Semaphore

  - path: src/vkdownloader/services/batch_downloader.py
    targets:
      - type: function
        name: run_batch_download
      - type: class
        name: _TrackedSemaphore
    semantic_anchors:

  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets:
      - type: function
        name: _build_ytdlp_cli_command
    semantic_anchors:
      insert_after:
        type: call
        value: _strip_auth_params

  - path: src/vkdownloader/config.py
    targets:
      - type: class
        name: Settings
    semantic_anchors:
      insert_after:
        type: field
        value: max_concurrent_downloads

  - path: tests/test_batch_downloader.py
    targets:
      - type: class
        name: TestBatchDownloaderSemaphore
    semantic_anchors:

changes:

  - action: modify
    description: >
      DEFERRED — which level max_concurrent_downloads governs, and what the second setting
      is called. This is the plan's central PRODUCT decision: (a) it governs whole videos
      only, and a new setting governs the fan-out; (b) it governs the fan-out, and a new
      setting governs whole videos; (c) gate the batch on a different existing value with
      no new setting. Record the upgrade note an operator needs. Also decide whether the
      child's -N follows the segment level or the video level. See spec §3.12.
    code_hint: |
      # before — one setting, three levels:
      #   batch_downloader:  Semaphore(settings.max_concurrent_downloads)   # per video
      #   segment_downloader: Semaphore(settings.max_concurrent_downloads)  # per video's segments
      #   ytdlp argv:         -N <max_concurrent_downloads>
      # after: one setting per level, each bounded and each declared.

  - action: prohibited
    description: >
      MUST NOT touch _create_connector. TCPConnector(limit=10) is phase 04's CON-009
      (advisory) and the declared seam both findings hold. This block's remedy CANNOT
      bound the connection count, and its report must say so rather than implying the
      aggregate is now bounded.
    code_hint: |

  - action: modify
    description: >
      Preserve the D-01 invariant: the batch permit is acquired ONCE per video and is
      NOT re-acquired per segment. asyncio.Semaphore is non-reentrant. This is why the
      remedy is NOT "gate the segment fan-out on the batch semaphore". The D-01 comment
      must remain accurate.
    code_hint: |

  - action: add_test
    description: >
      The peak-concurrency measurement re-expressed for the chosen level; the child's -N
      carrying the new value; and a test reading BOTH settings and asserting the aggregate
      is the product the commit message claims, so the commit body cannot drift from the
      code.
    code_hint: |

acceptance_criteria:
  - Exactly one level is governed by max_concurrent_downloads, and it is the level its description declares
  - The per-item fan-out and the child's -N are bounded by a separately bounded, separately declared value
  - The block report states the aggregate for the default and the ceiling
  - The COMMIT BODY carries 10 x max_concurrent_downloads (40 / 160) and cites the validated artifact's NET-014 Validation Note or phase 04's CON-009 as its authority
  - _create_connector is byte-identical before and after
  - The block makes NO claim that it bounds the connection count
  - The D-01 invariant is preserved and its comment remains accurate
  - Both settings' field descriptions are accurate after the change
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B15

```yaml
id: plan07-b15-retry-after-parsing-and-ceiling
title: Parse every Retry-After date form and clamp the wait the process actually performs
priority: low
depends_on:
  - plan07-b4-manifest-retry-policy-base-address-and-pause
  - plan07-b11-timeout-composition-and-merge-budget

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B15 — Parse every `Retry-After` date form, and clamp the wait the process actually performs
source_blocks: ["B15"]
source_findings: ["NET-018"]

description: >
  _parse_retry_after accepts one of the three HTTP-date forms the specification permits
  (plus a bare float that may be negative), so a lower-case IMF-fixdate is accepted and
  then yields about 8.26 years; and _compute_backoff_delay applies its 30 s clamp to the
  LOCAL term, with the max against the server's value applied OUTSIDE it, so the server's
  value is never clamped. Serialised behind B11 (conflict C12: both edit the
  download_timeout field description and the configuration guide's row). MUST NOT touch the
  comment/max() wording mismatch in _compute_backoff_delay — that is phase 09's.

goals:
  - All three HTTP-date forms parse, and a lower-case one does not yield a multi-year delay
  - A non-positive parsed value is rejected
  - The ceiling is applied after the maximum with the server's value
  - A past date is still ignored — correct per specification, and left alone
  - The ceiling's scope is recorded in the field description and the configuration guide

files:
  - path: src/vkdownloader/services/downloader_throttle.py
    targets:
      - type: function
        name: _parse_retry_after
      - type: function
        name: _compute_backoff_delay
    semantic_anchors:
      insert_before:
        type: return_statement

  - path: src/vkdownloader/config.py
    targets:
      - type: class
        name: Settings
    semantic_anchors:
      insert_after:
        type: field
        value: download_timeout

  - path: docs/11-guides/configuration.md
    targets:
      - type: section
        name: download_timeout
    semantic_anchors:

  - path: tests/test_downloader_throttle.py
    targets:
      - type: class
        name: TestParseRetryAfter
      - type: class
        name: TestComputeBackoffDelay
    semantic_anchors:

changes:

  - action: modify
    description: >
      _parse_retry_after attempts all three HTTP-date forms the specification permits and
      rejects a non-positive parsed value. A past date is still ignored — the code states
      that rule deliberately and the finding confirms it is correct. Do not add a warning
      about it.
    code_hint: |
      for fmt in (RFC7231_IMF_FIXDATE, RFC850_ASCTIME, ASCTIME):
          try:
              when = datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
          except ValueError:
              continue
          delta = (when - datetime.now(timezone.utc)).total_seconds()
          return delta if delta > 0 else None
      return None   # unparseable
      # the numeric form, separately:
      #   seconds = float(value); return seconds if seconds > 0 else None

  - action: modify
    description: >
      _compute_backoff_delay applies the ceiling AFTER the maximum with the server's
      value, so the wait the process actually performs is bounded. The clamp must not
      change the value passed to random.uniform — test_delay_caps_at_30_seconds asserts
      that bound and must stay green UNCHANGED.
    code_hint: |
      # before:  min(base_delay * (2**attempt), 30.0)   then  max(delay, retry_after)
      # after:   min(max(base_delay * (2**attempt), retry_after or 0.0), 30.0)

  - action: modify
    description: >
      DEFERRED — whether the ceiling is PER-REQUEST or PER-VIDEO, and record the answer in
      download_timeout's field description AND in the configuration guide's row. This is
      the statement-level collision C12 with B11: B11 writes the description once, this
      block amends it. An unrecorded choice here is what made the original finding possible.
      See spec §3.13.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT touch the comment/max() wording mismatch in _compute_backoff_delay. That is
      phase 09's, named by the artifact and confirmed present.
    code_hint: |

  - action: add_test
    description: >
      The thirteen-row header-form table as a data-driven table (three date forms, the
      lower-case variant, negative, whitespace-padded, absent). Plus a Retry-After: 600
      case asserting the CLAMPED value, and a no-header case over a wide attempt range.
    code_hint: |

acceptance_criteria:
  - All three HTTP-date forms parse; a lower-case IMF-fixdate does not produce a multi-year delay
  - A negative and a zero parsed value are rejected
  - A past date is still ignored, and no warning is added for it
  - The ceiling is applied after the maximum with the server's value
  - The block report states the new maximum wait for Retry-After: 600 and for no header
  - The value passed to random.uniform is unchanged
  - The comment/max() wording mismatch in _compute_backoff_delay is untouched
  - The ceiling's scope is recorded in the field description and in the configuration guide
  - test_delay_caps_at_30_seconds, test_retry_after_overrides_delay and test_invalid_date_format_returns_none stay green unchanged
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

### B16

```yaml
id: plan07-b16-json-byte-cap-comment
title: Correct the comment that claims the byte cap bounds memory
priority: low
depends_on: []

source_reference: .ai/plans/07-network-resilience-audit-fixes.md
source_section: B16 — Correct the comment that claims the byte cap bounds memory
source_blocks: ["B16"]
source_findings: ["NET-011"]

description: >
  On the paths where Content-Length is absent or unparseable, the JSON branch materialises
  the body all-or-nothing and only then applies the cap — so the cap bounds PARSING, not
  memory. The comment says "Enforce a byte cap even when Content-Length is absent", which is
  accurate about what it claims; what is inaccurate is the surrounding guard's implied
  intent. The fix is to make the comment say what the code does. Comment-only. The
  validator WITHDREW the behavioural half: skipping the branch would disable m3u8 discovery
  for every chunked or streamed JSON response.

goals:
  - The comment states that the cap bounds parsing, not memory, on the path where it applies
  - No executable statement in the file changes
  - The branch is still taken when Content-Length is absent or unparseable

files:
  - path: src/vkdownloader/infrastructure/network_monitor.py
    targets:
      - type: method
        name: _intercept_response
    semantic_anchors:
      insert_after:
        type: comment
        value: "Enforce a byte cap even when Content-Length is absent"

changes:

  - action: modify
    description: >
      Restate the comment. Name the mechanism — the all-or-nothing body read — so the next
      reader sees why a memory bound is not enforced here.
    code_hint: |
      # Enforce a byte cap even when Content-Length is absent. This bounds PARSING, not
      # memory: the Playwright Response API exposes body() as an all-or-nothing call, so
      # the body is materialised before the cap is consulted. A true memory bound is not
      # expressible at this surface.

  - action: prohibited
    description: >
      MUST NOT skip the JSON branch when Content-Length is absent or unparseable. That
      remedy was withdrawn by the validator: it would disable m3u8 discovery for every
      chunked or streamed JSON response — a functional regression traded for a memory bound
      this surface cannot express. The withdrawn text is still in the source report; do not
      re-derive it.
    code_hint: |

acceptance_criteria:
  - The comment states that the cap bounds parsing rather than memory
  - The diff for network_monitor.py is comments ONLY — no executable statement changes
  - The branch is still taken when Content-Length is absent or unparseable
  - The m3u8 branch is unchanged
  - MAX_JSON_BODY_BYTES, the declared-length pre-read and the post-read comparison are unchanged
  - test_network_monitor_skips_oversized_body_without_content_length stays green unchanged
  - pytest, ruff check, ruff format --check and mypy all pass
```

---

## §7 Verification strategy

### §7.1 The per-block gate — every block runs all four

No block is complete until all four of these pass, in this order, from the repository root.

| # | Command | Pass criterion |
|---|---|---|
| 1 | `uv run pytest -q -rs` | exit 0; the passed count has **risen** by the block's new tests and no test has been deleted or skipped to get there. |
| 2 | `uv run ruff check src tests` | exit 0 · `All checks passed!` |
| 3 | `uv run ruff format --check src tests` | exit 0 · all files formatted |
| 4 | `uv run mypy src` | exit 0 · `Success: no issues found` |

**Plus the block's own gate** — the specific assertions in its §3 acceptance criteria, run by
name:

```powershell
uv run pytest tests/test_ffmpeg_utils.py -k "merge" -q          # B1
uv run pytest tests/test_segment_downloader.py -q               # B4, B8
uv run pytest tests/test_hls_downloader.py -k "YtdlpCliCommand" -q   # B9
uv run pytest tests/test_config.py -q                           # B11, B14
uv run pytest tests/test_packaging.py -q                        # B11, if a file was added
```

**Rules for a block report.**

1. Quote the exact output of all four commands. A block report that says "tests pass" without
   output is not a report.
2. **The passed count must not decrease.** A drop means a test was deleted, renamed without
   replacement, or skipped.
3. **List every test file you edited**, by file and by test name, with one line on why the edit
   was required by a behaviour change rather than a convenience.
4. **Confirm no network was contacted.** `tests/test_packaging.py` is the only test that may, and
   it skips off-CI.
5. **Confirm the block's negative acceptance criteria** — the "byte-identical" and "MUST NOT"
   items — with a `git diff --stat` on the named paths, not with an assurance.
6. **Record every deferred decision you resolved**, with the option you rejected and why.

### §7.2 The end-of-plan gate — after B16

| # | Gate | Pass criterion |
|---|---|---|
| 1 | All four baseline commands, in order | exit 0. Expected floor: **≥ 588 passed, 4 skipped** — the count may only rise. |
| 2 | `uv run ruff check src tests` · `uv run ruff format --check src tests` · `uv run mypy src` | exit 0, all three. |
| 3 | The three pinned test groups, re-run individually | Each asserts its **new** contract, not a weakened one. Read the diff, not the exit code. |
| 4 | **No new file under `src/` or `tests/` outside `EXPECTED_SDIST_ENTRIES`** | `tests/test_packaging.py` green. |
| 5 | **No new `Settings` field is missing from `.env.example` or the configuration guide** | Every new field appears in all three places, and every `.env.example` value **constructs against the model**. |
| 6 | **`git diff` on the files other phases own** | `TCPConnector(limit=10)` region unchanged (B14); `.kilo/rules/project.md` unchanged (B3); `.kilo/commands/audit/audit-multi-phase.md` unchanged (B3); the four `.ai/audit/*/findings.md` unchanged (B3); `ytdlp_downloader.py`'s no-application-level-timeout comment unchanged (B11); the validated findings artifact unchanged (B2). |
| 7 | **No block implemented a withdrawn recommendation** | Grep the block reports for: `wait_for` around a transfer stage; skipping the JSON branch on absent `Content-Length`; the `throttled_rate` description change; the `max_concurrent_downloads` description change. All four must be absent. |
| 8 | **Identifier hygiene** | No unqualified `VAL-` id in any commit message, block report or task id. |
| 9 | **Ownership handover** | Plan 05's scope table is annotated: Block 8 (`ENT-010`) and Block 9 (`VAL-110`) are superseded by this plan's B11 and B3. |

### §7.3 How "no new file without a frozenset edit" is enforced

Only B11 has a plausible reason to add a `src/` module (§3.9 question 1). If it does:

- `tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` is edited **in the same change**, or
- `tests/test_packaging.py` fails on the exact-entry-set assertion *and* on the exact-count
  assertion at `len(EXPECTED_SDIST_ENTRIES)` — which is why the count assertion exists.

No other block may add a file under `src/` or `tests/`. A new test file is a packaging-gate edit
too: the frozenset covers `tests/` as well as `src/`.

### §7.4 How a new `.env.example` value is proven legal (B11, B14)

Phase 02 found a shipped `.env.example` value the model rejects. **Any value this plan adds must
be constructed against `Settings` and the construction recorded in the block report** — the same
line-by-line validation plan 06 applied to the file it shipped. The test that exercises it is
`tests/test_config.py`'s env-var-namespace suite, which sees a new field automatically.

### §7.5 Per-finding verification trace

Every one of the 18 product findings and the 2 still-open pipeline findings, mapped to the block
that carries it and the test that proves it.

| Finding | Block | Proving test | Notes |
|---|---|---|---|
| `NET-001` | **B1** | `tests/test_ffmpeg_utils.py::TestMergeSegmentsBatched::test_final_stage_failure_preserves_all_inputs`, `::test_second_batch_failure_preserves_inputs_and_temps`, `::test_success_removes_everything`; `TestMergeBatchSegments::test_batch_stage_preserves_inputs`; `tests/test_segment_downloader.py::test_log_preserve_segments_reports_zero` | `TestMergeBatchSegments::test_merge_batch_removes_input_files_on_success` **re-scoped**; `TestPerformFinalMerge::test_final_merge_removes_temp_files` and `::test_final_merge_removes_final_list` green **unchanged**. |
| `phase03/VAL-001` | **B2** | *(no test — prose)* Validator gate: `git diff --exit-code` on the validated artifact; the corrected figure matches `CON-009`. | |
| `phase03/VAL-004` | **B3** | *(no test — prose)* Validator gate: label lists are exactly four; the named role exists; five files byte-identical. | Supersedes plan 05 Block 9. |
| `NET-002` | **B4** | `TestFetchPlaylistWithRetry::test_retryable_status_is_retried_and_recorded` (new); `::test_refresh_failure_falls_through` **re-scoped** (was asserting `fetch_count == 1`); `::test_no_refresh_when_status_not_403_or_410` **re-scoped** | Depends on B4's fork 2 (`C7`) for the status set. |
| `NET-003` | **B9** | `TestYtdlpCliCommand::test_cli_command_format_worst_for_worst_quality` (re-scoped from `test_cli_command_format_best_when_quality_not_digit`); `::test_cli_command_format_best_for_best_quality` (the preserved half); `::test_child_receives_selected_address` (new) | The other 17 `TestYtdlpCliCommand` cases green unchanged. |
| `NET-004` | **B4** | `TestFetchPlaylistWithRetry::test_token_refresh_returns_the_refreshed_base` (new); `::test_token_refresh_runs_on_403_then_retry_succeeds` **re-scoped** (was asserting a bare-string return) | Criterion 5 asserts the cookie/base **order**. |
| `NET-005` | **B8** | `tests/test_segment_downloader.py::test_refresh_selects_requested_quality` (new); `::test_refresh_records_requested_and_delivered` (new) | `TestResolveCookies` (5) and `TestAttemptSegmentResumeQuality` green unchanged — the pattern mirrored, not modified. |
| `NET-006` | **B11** | `tests/test_downloader_throttle.py::TestClientTimeoutComposition::test_composed_timeout_at_floor_default_and_ceiling` (new) | The suite's **first** timeout assertion. `TestComputeBackoffDelay`'s `test_delay_caps_at_30_seconds` green unchanged. |
| `NET-007` | **B11** | `tests/test_ffmpeg_utils.py::TestMergeBatchSegments::test_merge_stages_receive_the_merge_budget` (new) | The `= 300` literals are covered by `TestSequentialDownloadMode` and `TestDownloadSegmentRealExecution` (6) staying green. `TestMergeFreeSpaceProbe` (6) untouched. |
| `NET-008` | **B7** | `TestNetworkMonitor::test_expected_host_is_offered_and_others_are_logged_and_dropped` (new); `test_quality_selector.py::test_produced_label_is_re_requestable` (new); `TestExtractWithBrowser::test_browser_extraction_uses_first_m3u8_url` — **edit or verify, with the reason stated** | Research-gated. |
| `NET-009` | **B4** | `TestFetchPlaylistWithRetry::test_manifest_consults_and_sets_the_shared_pause` (new); `test_sequential_strategy_consults_the_shared_pause` (new); `test_extractor_consults_the_shared_pause` (new) | All five original tests re-scoped. |
| `NET-010` | **B4** | `tests/test_downloader_throttle.py::TestRetry429WithBackoff::test_final_attempt_does_not_wait` (new); `::test_transport_failure_retries_to_the_same_budget` (new) | `test_max_retries_exceeded_returns_none` green **unchanged** (a sleep was removed, not a request). |
| `NET-011` | **B16** | `test_network_monitor_skips_oversized_body_without_content_length` — **green unchanged is the evidence** | Comment-only; the diff for the file must be comments. |
| `NET-012` | **B12** | `tests/test_extractor.py::test_video_url_acceptance_table` (new, data-driven); four per-consumer identifier tests (new) | `TestBatchCommand`'s valid-URL cases green unchanged. Research-gated. |
| `NET-013` | **B13** | `tests/test_extractor.py::test_extract_with_ytdlp_carries_configured_identity` (new); two warning-assertion tests (new) | `test_extract_with_ytdlp_propagates_settings_to_ydl_opts` green unchanged — **verify, do not assume.** |
| `NET-014` | **B14** | `tests/test_batch_downloader.py::TestBatchDownloaderSemaphore::test_peak_concurrency_for_the_governing_level` (new); `test_hls_downloader.py::test_child_N_carries_the_new_value` (new); `test_aggregate_is_the_documented_product` (new) | The third test exists so the **commit body cannot drift from the code**. |
| `NET-015` *(reduced)* | **B10** | `tests/test_downloader.py::TestPerformDownload::test_ffmpeg_partial_is_not_handed_to_the_segment_stage` (new) | The `.part` half is **phase 07's `ART-002`** — not traced here. |
| `NET-016` | **B6** | `tests/test_browser_infrastructure.py::TestNetworkMonitor::test_normalize_url_address_forms` (new, data-driven, nine forms) | |
| `NET-017` | **B5** | `TestBuildStreams::test_format_classified_by_parsed_suffix`, `::test_placeholder_height_labelled_as_absent` (new); `tests/test_quality_selector.py::test_placeholder_height_is_not_a_best_candidate` / `::test_placeholder_height_is_not_a_worst_candidate` (new, **asserted separately**) | All 13 `TestBuildStreams` cases and all 12 `test_quality_selector` cases green unchanged. |
| `NET-018` | **B15** | `TestParseRetryAfter::test_retry_after_header_forms` (new, data-driven, thirteen rows); `TestComputeBackoffDelay::test_ceiling_applies_after_the_maximum` (new) | `test_delay_caps_at_30_seconds`, `test_retry_after_overrides_delay`, `test_invalid_date_format_returns_none` green **unchanged**. |

**Findings whose verification is a negative assertion** (no test can see them — the Validator's
read is the gate): `phase03/VAL-001` (B2), `phase03/VAL-004` (B3), `NET-011`'s comment-only diff
(B16), and B1's / B10's / B11's / B14's byte-identical criteria. Each is written as an explicit
acceptance criterion for that reason.


