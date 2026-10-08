# Plan 08 — Phase 04 Audit Fixes: Concurrency and Cancellation

**Source artifact (read-only, authoritative for *what* must change):**
`.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` (1359 lines).
**Code context (read-only, authoritative for *where* it changes):** `tmp/code_context_phase04.md`
(1297 lines, produced by the Auditor against the live tree).
**Source report (read-only):** `.ai/audit/04-concurrency-cancellation/findings.md`.
**Precedent matched:** `.ai/plans/07-network-resilience-audit-fixes.md` (16 blocks).
**Tree state this plan was composed against:** branch `main`, `HEAD = 2cf754f`
(`fix(extractor): remove duplicate browser_stream_selected log record`), **working tree dirty** —
10 `src/` files and 7 test files carry an unrelated, uncommitted quality-selection feature. See
§2.4; the landing rule is binding on every block.
**Coverage:** 10 product findings `CON-001` … `CON-010` + 4 still-open pipeline findings
(`phase04/VAL-401` … `phase04/VAL-404`), in **11 blocks**.

> **Identifier convention — binding on every block, every block report, every task id and every
> commit message of this plan.**
> `VAL-` is a **colliding prefix**. Every per-phase validation run mints `VAL-001…` independently and
> the numbers name different subjects: `VAL-001`…`VAL-006` (phase 02), `VAL-001`…`VAL-007`
> (phase 03), `VAL-101`…`VAL-112` (phase 01), `VAL-401`…`VAL-410` (phase 04). Plan 06 already
> documents the collision it caused. **Every phase-04 `VAL-` id in this plan is written
> `phase04/VAL-NNN`** — e.g. `phase04/VAL-401`. An unqualified `VAL-401` in a block report, a
> commit message or a task id is a **defect** and must be rejected at review. `CON-` ids are not
> qualified: `CON-` is unique to phase 04 in the whole store. This convention is inherited verbatim
> from plan 07, which states the same rule for `phase03/VAL-NNN`.

> **Nothing in this plan is anchored by line number.** Every target is a semantic anchor — a file, a
> module, a class, a function, a method, a guard expression, a return statement, a parameter. The
> artifact's `file:line` references are stale for every moved file (the drift table is in the code
> context §2.1) and the working tree can move again. **Re-anchor semantically at execution time.**

---

## §1 Scope

### §1.1 How this block set was derived

The block set is **not** the artifact's finding order. It is that order re-derived against four
things the artifact could not see.

1. **The tree moved and is dirty.** `CON-001`'s four modules are unmodified at `HEAD` except the
   dirty quality-selection work, and every line reference into `segment_downloader.py`,
   `downloader.py`, `ytdlp_downloader.py` and `extractor.py` is stale by a positive offset. Blocks
   are anchored semantically (§ header note), not by line.
2. **Five of the ten `VAL-4xx` findings are already fixed** by `d62671b`, `19143b1`, `8366964` and
   `e443448`. Planning a block for an already-fixed pipeline defect would be wasted work and would
   re-edit a document that now carries the slot.
3. **Three rollout-ordering findings (`phase04/VAL-401/402/403`) are *not* findings in their own
   right** — they are constraints over how the product blocks are grouped and ordered. Each is
   *enforced* (in-block, or as a `depends_on` edge) rather than given a block of its own. Planning a
   block whose entire content is "do B4 before B4" would be theatre.
4. **Three groups of currently-green tests interact with the defective behaviour** — one confirmed
   pin (`CON-005`), one exact near-miss that must be *verified* rather than assumed
   (`CON-006`/`CON-007`), and two regression-net tests that must stay green **unchanged** under any
   `CON-003` remedy. Under project rule 2 the pinned test is edited *in the same change*.

**Grouping rule applied throughout:** two findings share a block only when they share a **semantic
anchor** *and* the grouping reduces conflict, review surface, or risk. Conversely, **one finding may
be split across blocks** when its halves live in different modules, carry different failure modes,
have different ordering gates, or different verification shapes — which is why `CON-001` is three
blocks (`B1`, `B3`, `B5`) and `CON-003` is two (`B6`, `B7`). Every split and every grouping is
justified at the block heading and in §4.4.

### §1.2 IN — every still-open finding

| Block | Findings | One-line goal | Why here | Plan that would otherwise carry it |
|---|---|---|---|---|
| **B1** | `CON-001` *(leg 1 of 3)* | Make the stop observable **while** a child's output read is in flight | The one leaf-module, one-function, CRITICAL hang fix with no dependencies. It must land first because everything else in the cancellation story assumes the child can actually be reached. | — (this plan) |
| **B2** | `CON-006` + `CON-007` + `CON-008`, enforced by `phase04/VAL-402` | Make the completion helper settle its siblings and stop conflating "nothing to do" with "cancelled" | `phase04/VAL-402` names the exact set and the exact reason: all three edits land in one 25-line function whose only consumer branches on a single `None`. | — (this plan) |
| **B3** | `CON-001` *(leg 3 of 3)* | Restore the **previously installed** process-level signal handler on the branch that actually runs on Windows | Different module, different failure mode (post-`asyncio.run` process state, not an in-transfer hang), different verification (handler identity). Separate commit; it is also the precondition for `B5`'s forward route. | — (this plan) |
| **B4** | `CON-004` + `CON-005`, enforced by `phase04/VAL-401` | Release the browser handle unconditionally and stop letting a release failure replace the failure that caused the exit | `phase04/VAL-401` states that `CON-004` **alone is a correctness regression** on the path it fixes, because the stop path is exactly the path where a `CancelledError` is in flight. One block or the ordering is unsafe. | — (this plan) |
| **B5** | `CON-001` *(leg 2 of 3)*, enforced by `phase04/VAL-403` | Make a second interrupt escalate instead of being a no-op | `phase04/VAL-403` is a **severity** dependency, not a hygiene one: shipping the escalation before `CON-008` makes the repaired hang produce a wrong exit code and a false failure list on exactly the interaction the user was performing. | — (this plan) |
| **B6** | `CON-003` *(segment layer)* | Bound the live segment-task set by the configured ceiling | `CON-003`'s segment half. Its factory's **return type feeds `_process_downloaded_segments`**, whose contract `B2` rewrites — a statement-level dependency, not file co-location (`C1`). | — (this plan) |
| **B7** | `CON-003` *(batch layer)* | Bound the live per-URL task set by the configured ceiling | `CON-003`'s batch half. Its fan-out carries the cancel-and-gather branch that `B2` **activates** (`C6`) — so it is reviewed against the live behaviour, not against the dead one. | — (this plan) |
| **B8** | `CON-009` | Derive the transport pool ceiling from the setting and give the per-origin ceiling a value | Plan 07 deferred the `TCPConnector(limit=10)` literal here and its `B14` carries a **prohibition**: "MUST NOT touch `_create_connector`". That prohibition is now **released** by this block. | Plan 07 `B14` — deferred to phase 04 |
| **B9** | `CON-010` | State the exit-path thread-join bound where the timeout is configured, and decide the code-side remedy | Plan 07's `C12` owns the guide's `download_timeout` row; `B9` writes the **field description only** and must not touch that row. | Plan 07 `B11`/`B15` — cross-plan, coordinated (§5.7) |
| **B10** | `CON-002` | Record `CON-002`'s verification outcome **without** code change, **without** a severity, and **without** deleting the finding | The owning phase's binding rule W-4 requires the claim subject to be filed as *exactly two* findings and forbids omitting either. It is a verification/documentation task, not a code task. | — (this plan) |
| **B11** | `phase04/VAL-404` | Give the report format a legal encoding for a not-executed finding | The only `VAL-4xx` still open that is neither an ordering constraint, nor already fixed, nor blocked by a read-only file. Leaving it makes every future W-4 report illegal by construction. | — (this plan) |

**10 `CON-` + 4 `VAL-` = 14 findings, 11 blocks, zero findings unassigned.**

### §1.3 OUT — and where each item went

| Item | Disposition | Where it went, and why |
|---|---|---|
| `phase04/VAL-405` (orchestrator writes one validation filename, gate checks another) | **OUT — already fixed** | `d62671b`. `audit-multi-phase.md` checks `…{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md`, matching the write. **No block.** |
| `phase04/VAL-406` (unevaluable validator gate + unconditional coverage claim) | **OUT — already fixed** | `19143b1`, `8366964`. The gate is removed and the removal is stated; `{VALIDATED_PHASES}/{TOTAL_PHASES}` advances only for verified output. **No block.** |
| `phase04/VAL-407` (orchestrator orders rejected findings deleted) | **OUT — already fixed** | `d62671b`. The `<retry_rules>` block holds no "Rejected findings cleaned" line. **No block.** |
| `phase04/VAL-408` (mandatory context read names a non-existent `AGENTS.md`) | **OUT — already fixed** | `19143b1`. The step names `.ai/context/commands.md`, `.kilo/rules/project.md`, `.kilo/rules/commands.md`. **No block.** |
| `phase04/VAL-409` (both role files omit `RUNTIME-ERROR`) | **OUT — already fixed** | `e443448`. All four labels listed in `auditor.md` and twice in `validator.md`. **No block.** |
| **`phase04/VAL-410` — path/line-reference correction in the source report** | **NOT CLAIMED — see §1.4** | Its primary target is `.ai/audit/04-concurrency-cancellation/findings.md`, **read-only for this plan**. Recorded as not claimed, with the owner and the trigger. |
| **`CON-004`'s "permanent leak" consequence** | **OUT — withdrawn by the validator** | Must not be written into a fix, a commit body, a doc claim or a test docstring. The accurate consequence is: **the graceful close is skipped, so the browser is torn down by driver shutdown rather than by the close path, and if `playwright.stop()` exceeds its 10 s `asyncio.wait_for` bound the teardown is unbounded.** Severity (HIGH) is unchanged; only the wording changes. **Binding negative constraint on `B4`.** |
| **`CON-007`'s "the caller was told the download *finished*"** | **OUT — corrected by the validator** | The caller was told it **failed**. `download_hls_with_resume`'s `finally` logs `preserving_segments_for_resume` while the siblings are still writing. **Binding on `B2`.** |
| **`CON-007`'s "its HTTP session slot"** | **OUT — imprecise** | The session's `async with` exits as the exception propagates, so a surviving sibling's next request fails on a **closed session**, not on an occupied slot. **Binding on `B2`.** |
| **`CON-001`'s R5(iii) leg** | **OUT — not evidence of a defect** | `_download_segment_concurrent` checks the stop state immediately after acquiring the permit and the wait is bounded by each in-flight transfer's own `download_timeout`. That is ordinary blocking, not a standstill. **Must not be implemented as a defect.** |
| **`CON-001`'s "only `on_shutdown` terminates the child"** | **OUT — over-stated, narrowed** | `cancel_subprocess` has **six** live call sites: two `on_shutdown` closures plus the post-drain/`finally` guards in `downloader.py` and the two yt-dlp sites. The conclusion stands; the phrasing must be narrowed wherever it is restated. **Binding on `B1`, `B3`, `B5`.** |
| **`CON-001`'s cross-reference to correlation-id shadowing in `downloader.py`** | **OUT — dead reference** | `ENT-012` was fixed by `0790157`; `downloader.py` contains **no correlation-id code at all**. **`CON-001` carries no correlation-id obligation.** **Binding on `B1`, `B3`, `B5`.** |
| **Any reclassification of the nine `RUNTIME-ERROR` labels** | **OUT — prohibited** | All nine are **retained**. A role file lacking the vocabulary is not grounds to reclassify an observed failure. **Binding on every block.** |
| **`CON-002`'s severity cell** | **OUT — prohibited** | `*none — not executed*` **may not** be replaced with `LOW` and **may not** be given any observed severity. **Binding on `B10`.** |
| **`CON-002`'s closure by the primitive-identity observation** | **OUT — prohibited** | The validator was explicit: "The structural identity comparison is not proof of the condition's behaviour." **Binding on `B10`.** |
| **`CON-009` as a *rate* finding** | **OUT — scope boundary, phase 03** | This plan owns the **literal** only. The request *rate* against one origin is phase 03's. **Binding on `B8`.** |
| **`NET-014`** | **OUT — already adjudicated** | Phase 03's `VAL-001` adjudicated the connection-ceiling conflict **in favour of `CON-009`**. `B8` cites that adjudication and must read `NET-014` *through* it. |
| **`CFG-002`** as `CON-010`'s cross-reference | **OUT — misattributed, do not act** | Phase 02's `CFG-002` is about the post-construction **`max_retries` override**, not `download_timeout`; it is already fixed by `ea44b3d` and there is no override in `src/`. **`B9` must not re-derive it.** |
| **`ENT-004`** (handler-registration *placement*) | **OUT — phase 01, deferred** | Plan 05 §6.7 `D7` DEFERRED. `CON-001`'s fix lands in `signal_handlers.py` and must **not** move registration between `cli.py` and `batch_downloader.py`. **Binding on `B3`, `B5`.** |
| **The archived register's own stale line references** | **OUT — phase 09 by R-E** | `VAL-410`'s second half is explicitly `09`'s subject. **Not claimed.** |
| **`_TrackedSemaphore`, `ConcurrencyTracker`, `_await_and_cancel`, `_create_segment_download_tasks`, `_process_downloaded_segments`, `_semaphore_context`, `_create_connector` coverage** | **OUT — a phase-10 subject, not a phase-04 one** | All seven have **zero** references in `tests/` today. That is a test-coverage observation, and phase 10 (`test-coverage`) owns it. Blocks here add tests **for the finding they carry**, not for coverage's sake. |
| **`ProgressManager` deprecation; the `structlog`/rule-12 divergence** | **OUT — flagged, not fixed** | §5.6. Correcting `.kilo/rules/project.md` is an audit-pipeline change; changing the code to match the rule text would break the renderer split in `config.setup_logging`. |
| **`__all__`'s duplicate `"_format_argfile"` in `downloader.py`** | **OUT — pre-existing, harmless** | Recorded so a block that touches `__all__` does not mistake it for new. **No block may touch it.** |

### §1.4 Deferred — explicitly not in this plan

| Deferred item | Owner / trigger |
|---|---|
| **`phase04/VAL-410` — correcting `CON-002`'s two path references from `.ai/problems/01-confirmed-code-defects.md` to `.ai/plans/done/01-confirmed-code-defects_DONE.md`** | **Not claimed by this plan. Decision, stated once.** The primary target is `.ai/audit/04-concurrency-cancellation/findings.md`, which is **read-only** for this plan: (i) this engagement's audit constraint makes `.ai/audit/` read-only, and (ii) plan 07's `B2` set the precedent that a validated artifact must be **byte-identical** before and after, which is the discipline that applies to a read-only source report. The second half — the archived register's own stale `Location` list — is `09`'s subject by R-E and the artifact says so. **Trigger for a future plan:** a documentation plan that is explicitly allowed to edit `.ai/audit/*/findings.md` **must** correct both path references, and **must** record that D-01 was **fixed** (its Fix, Option A), not merely unexecuted — which retires the "execute the production condition" half of `CON-002`'s recommendation and leaves only the register-wording half. **`B10` records that this correction is outstanding and does not perform it.** |
| The request *rate* against one origin, and any process-wide connection pool | **Phase 03's `NET-014`**, already adjudicated in `VAL-001`'s favour of `CON-009`. `B8` owns the literal and must not become a rate limiter or a pool. |
| The `read_progress` shutdown-event parameter | **Deliberate and permanent.** It takes `shutdown_event` as a **parameter** (defaulting to a throwaway `asyncio.Event()`), not from a module lookup, precisely because `ffmpeg_utils.py` is a leaf. **No block may convert it to a module lookup.** |
| Test coverage for the seven zero-reference symbols | **Phase 10 (`test-coverage`).** |
| Any change to `.kilo/rules/project.md` | **Flagged, not fixed.** §5.6. |
| `ENT-004` handler-registration placement | **Phase 01, plan 05 `D7`, DEFERRED.** |
| `ART-002` / `ART-004` / `ART-012` (filesystem residue, merge heuristic) | **Phase 07.** `B9`'s exit-path discussion touches the merge timeout's reach; it must not change the residue or the `2×` heuristic. |
| The pre-existing full-suite `NameError` in `tests/test_hls_downloader.py::TestYtdlpProgressLineDetection` | **Not a phase-04 defect. Not this plan's.** See §2.4 — it is a property of the uncommitted quality-selection work. |

---

## §2 Baseline

### §2.1 The four verification commands — re-run by the Planner against the live tree

```
$ uv run pytest -q -rs
731 passed, 4 skipped, 2 warnings in 34.97s                              EXIT=0

$ uv run ruff check src tests
All checks passed!                                                       EXIT=0

$ uv run ruff format --check src tests
54 files already formatted                                               EXIT=0

$ uv run mypy src
Success: no issues found in 31 source files                              EXIT=0
```

Re-run by the Planner against the live tree at `HEAD = 2cf754f` with the dirty quality-selection
work present. **Not copied from the code context.** The code context's own four-command baseline
agrees (`731 passed, 4 skipped`; `All checks passed!`; `54 files already formatted`; `31 source
files`) — and it agrees with the *dirty* tree, not with `HEAD`.

**`pytest` was run three times.** Runs 2 and 3 (`-q`, no `-rs`) both returned
`731 passed, 4 skipped, 2 warnings` (33.07 s, 32.89 s). **The flake the code context recorded did
not reproduce in any of the Planner's three runs.** It is still treated as real (§2.4): the code
context observed it once in three full runs, which is exactly the rate at which an agent would
encounter it, and its diagnosis (a collection-order artefact of the **uncommitted** changes) is
structural, not probabilistic noise to be ignored.

**The correct expected skip count is 4, and the reason is a single Windows gate.**
All four are the `D-11` owner-only-confinement cases: `os.chmod` on Windows toggles only the
read-only attribute, so the measured mode is `0o666` rather than the requested `0o600`. Two sites in
`tests/test_config.py` and two in `tests/test_hls_downloader.py`. **They are not a phase-04 subject
and no block may change their count** — neither to hide a failure nor to "tidy" the count.

The two warnings are `RuntimeWarning: coroutine 'Event.wait' was never awaited`, from
`tests/test_exceptions.py::TestStructuredAttributes::test_status_label_video_not_found` and
`tests/test_extractor.py::TestExtractionErrors::test_extract_with_ytdlp_no_info_raises_extraction_error`.
Both are **pre-existing and unrelated to any `CON-*` anchor**. Do not fix them in a concurrency block.

### §2.2 Binding project rules — every block

| Rule | What it binds in this plan |
|---|---|
| **1. English only** | Comments, log event names, docstrings, error text, test docstrings. |
| **2. Production code is king** | The one confirmed pin (`B4`) is re-scoped **because** it pins the defect, and in the **same change**. A block that cannot make a pinned test pass by fixing the code has misread its finding. |
| **3–4. Separation of concerns / single responsibility** | `CON-009` spans `segment_downloader.py` (transport) and `config.py` (declared bound). A `VAL-402` outcome type belongs in `segment_downloader.py`, **not** in `models/`. A live-child registry (§3 `B5` fork) must not be born in `signal_handlers.py`. |
| **5. Avoid overengineering** | **The single most load-bearing rule in this plan.** `CON-009` and `CON-010` are **`advisory`** — the over-engineering risk is *higher* than the defect. `B8` must resolve to the simplest option that closes the finding, and a new `src/` module is the failure mode. `B9` may legitimately ship documentation only. |
| **6. Composition over inheritance** | The `VAL-402` outcome must not become a class hierarchy. A frozen dataclass or a `StrEnum` member is the ceiling. |
| **7. Follow existing patterns** | `logger = get_logger(__name__)` then `logger.<event>(key=value)`. Dense decision-carrying comments (`D-01`, `D-04`, `INT-003`, `INT-004`, `STR-008`, `SEC-*`, `DF-*`). Any behaviour change **must** update the tag comment that justifies the old behaviour. |
| **8. Meaningful, consistent naming** | `CON-008`'s new `reason` value must be named consistently with the existing event fields (`shutdown_requested` is the incumbent; the artifact proposes `cancelled`). |
| **9. Type safety** | `mypy` is on; `strict` with one override (`vkdownloader.cli`). **No `any`.** The `VAL-402` annotation (`list[tuple[int, bool]] | None`) must be made to **carry** the empty-vs-cancelled distinction, not merely to document it. |
| **10. `StrEnum` for all constants** | Any new named outcome — the `VAL-402` sentinel is the near-certain case, and `B5`'s escalation *reason* is the other — must be a `StrEnum` member or a frozen dataclass. **Never a bare literal, never a dict.** |
| **11. Pydantic** | A new `Settings` field (`B8`) is a `Field(default=..., ge=..., le=..., description=...)` on `Settings`, and appears in **three** places — field description, `.env.example`, and `docs/11-guides/configuration.md` (table row + prose section). `model_config`'s `extra="forbid"` makes this a correctness requirement, not tidiness. |
| **12. No `print()`** | **Read the trap: this rule's *text* prescribes `logging.getLogger(__name__)`, and the codebase universally uses `structlog`.** A block that follows the rule text breaks the `JSONRenderer`/`ConsoleRenderer` split in `config.setup_logging`. **Follow the code.** §5.6. |
| **13. Migrations for schema changes** | Not applicable — no database in this project. Recorded so no block looks for one. |
| **14. Documentation stays current** | `B8` (if a setting changes) and `B9` both write prose. `browser.py`'s `__aexit__` docstring currently **lies** (`B4` corrects it). |
| **15. Small modules and functions** | `_await_and_cancel` is 25 lines and carries three findings; **keep the fix inside it** rather than growing a new module — which would also trip `EXPECTED_SDIST_ENTRIES`. |

### §2.3 Repository constraints every block must respect

- **Layering is one-directional and acyclic**: `cli → services → infrastructure`;
  `services → models | utils | config | exceptions`; `models` and `utils` depend on nothing.
  Three specific acyclicity constraints are binding on this plan:

  1. **`services/ffmpeg_utils.py` is a leaf.** It imports **only** `..exceptions`
     (`DownloadError`) and `..utils.formatting` (`format_bytes`). **A `CON-001` fix must NOT add an
     import of `downloader_throttle` into it.** That edge happens to be acyclic today
     (`downloader_throttle` imports only `config`, `utils.formatting`, `utils.url_sanitizer`) but it
     would couple two modules that are deliberately independent and would drag `config.py` into a
     subprocess utility. The stop state already arrives at `iter_process_lines` **as a parameter**;
     the fix must keep using it.
  2. **`infrastructure/browser.py` holds exactly one deliberate function-scope lazy import** —
     `get_shutdown_event` inside `__aexit__`, with the cycle written inline
     (`browser.py → services.__init__ → downloader → extractor → browser`). **Do not move it to
     module scope and do not add a second.** `B4` does not need to touch it at all.
  3. **`services/downloader.py` is a backward-compat re-export facade**, each re-export marked
     `# noqa: F401 — backward-compat re-export`, with a 30-line ownership comment and an explicit
     `__all__`. **Every fix goes in the owning module**: `iter_process_lines` / `cancel_subprocess` →
     `ffmpeg_utils.py`; `_await_first_and_cancel_others` / `_download_with_ytdlp` →
     `ytdlp_downloader.py`; the segment layer → `segment_downloader.py`; `BrowserManager.__aexit__`
     → `infrastructure/browser.py`; the batch layer → `batch_downloader.py`; the off-loop extraction
     → `extractor.py`. **Editing a re-export line in `downloader.py` is never the fix.**

- **`tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` is a hard gate**, asserted twice —
  `test_sdist_entry_set_matches_the_manifest` and `test_sdist_entry_count_matches_the_manifest`.
  **Decision, stated once: no block in this plan adds a `src/` or `tests/` file.** New tests go into
  the **existing** test file that already owns the module under test (§2.5's table). The one block
  with a plausible reason to add a `src/` module is `B5` (a live-child registry), and rule 5 plus
  the gate both push against it; if a `B5` Planner concludes a new module is unavoidable, the
  frozenset is edited **in the same change** and the report says why no existing owner fits.
- **`tests/conftest.py` carries an `autouse` fixture, `isolate_settings_source`**, which chdirs to
  `tmp_path` and deletes every `VKDOWNLOADER_*` for each test. Any new test that reads `.env` or the
  environment must work inside it. The `test_settings` fixture carries **`max_retries=1`**.
- **Any new test that needs a set or unset stop state must use the project's own token idiom** —
  `set` a fresh `asyncio.Event` into `_shutdown_event_ctx` and `reset(token)` afterwards. The
  event is a `contextvars.ContextVar` whose value is **never reset** once created, so a leaked
  loop-bound `Event` silently poisons every later test in the session. This is a real mechanism for
  the `NameError`-class flake in §2.4 and is a hard requirement on `B1`, `B2`, `B3`, `B5`.
- **There is no `aiohttp` session fixture, no ffmpeg-subprocess fixture and no fake clock.**
  `tests/` contains **zero** occurrences of `aiohttp`, `ClientTimeout`, `TCPConnector`,
  `ClientSession`, `ssl.`, `CERT_NONE` or `check_hostname`. **No verification step in this plan may
  require network access.** Every new test builds its own stand-in.
- **A new `Settings` field has no CLI option today** and both existing settings are env-only. A new
  option that is not `None`-defaulted silently shadows the `.env`; prefer **no option at all**
  (plan 07 §5.5's rule).
- **Windows runtime facts, binding on `B1`, `B3`, `B5` and `B9`:**
  - The loop is `asyncio.windows_events.ProactorEventLoop`, and **`loop.add_signal_handler` raises
    `NotImplementedError`** — measured. So `setup_signal_handlers`' `signal.signal` fallback is the
    branch that *actually runs*, not a defensive branch, and `loop.remove_signal_handler` fails the
    same way, which is why `cleanup_signal_handlers`' loop branch achieves nothing.
  - **The displaced SIGINT handler is `asyncio.runners.Runner._on_sigint`**, a
    `functools.partial` of a bound method — **not** `SIG_DFL`. SIGTERM's pre-install value **is**
    `SIG_DFL`. **A single "reset to default" restore is insufficient**; the two signals need
    *different* restore values. **Binding on `B3`.**
  - `Runner.run()` restores `default_int_handler` **only when it is still installed**. Because it is
    not, after `asyncio.run` returns SIGINT is still the project's lambda. **Binding on `B3`** —
    `B3` is what makes `Runner`'s own restore succeed.
  - **`signal.signal` handlers run on the main thread between bytecodes, not in the loop.**
    `Event.set()` is safe there because it only schedules waiters' futures. **Any fix that does real
    work in the handler (e.g. `process.kill()`) must schedule it onto the loop instead of doing it
    in the signal context.** **Binding on `B5`.**
  - `asyncio.constants.THREAD_JOIN_TIMEOUT = 300`, which is numerically identical to
    `download_timeout`'s default of 300 — the coincidence that makes `CON-010` easy to miss.
    **Binding on `B9`.**
  - A Ctrl-C in a console window also delivers `CTRL_C_EVENT` to child processes by default on
    Windows. **A fix must not assume the child survives.** **Binding on `B1`, `B5`.**
- **Exit codes are documented.** `130` = "Interrupted by user (Ctrl+C)" in
  `docs/99-reference/cli-reference.md` and `cli-reference-clean.md`; `1` = failure. **A `B2` + `B5`
  pair must not break the documented `130`.** **Binding on `B2`, `B5`.**

### §2.4 The landing rule — binding on every block

The working tree is **dirty**: 10 `src/` files and 7 test files carry an unrelated, uncommitted
**quality-selection feature** (plus one new `src/vkdownloader/models/quality.py` and one new
`tests/test_quality_spec.py`). None of it touches a `CON-*` anchor, but it moved every anchor in
`segment_downloader.py` by +171…+191 lines and it changes one helper's signature.

> **The dirty state is pre-existing. It must NOT be absorbed into any phase-04 commit.**
>
> 1. **A block's commit contains only its own work item.** Stage by **explicit semantic path**, never
>    `git add -A`, never `git add .`, never `git commit -a`. Before committing, the block report must
>    show `git diff --cached --stat` and confirm every staged path belongs to the block.
> 2. **If the quality-selection work is committed before a phase-04 block lands**, that is fine and
>    changes nothing in this plan: every target in this plan is a **semantic anchor**, so the block
>    re-anchors rather than breaks. **This plan's decision is that blocks land on top of the dirty
>    tree**, one work item per commit, with the per-path staging restriction above.
> 3. **The pre-existing full-suite `NameError` in
>    `tests/test_hls_downloader.py::TestYtdlpProgressLineDetection` (19 parametrized cases) is NOT a
>    phase-04 defect and must NOT be "fixed" inside a concurrency block.** It is green in isolation
>    (19/19), green for the whole file, green paired with every other test file individually, and
>    produced by the *uncommitted* changes only (`HEAD:tests/test_hls_downloader.py` contains zero
>    occurrences of the symbol). If a block's gate hits it, the block report records the flake and
>    reports the isolated re-run — it does not edit that test file, does not touch the import, and
>    does not attribute it to `CON-*`. **The Planner observed it zero times in three full runs
>    (§2.1); the code context observed it once in three. The rule holds either way.**
> 4. **`EXPECTED_SDIST_ENTRIES` in `tests/test_packaging.py` was already edited by that uncommitted
>    work** to cover the new `models/quality.py`. A phase-04 file addition would need the same
>    treatment in the same change — which is why §2.3 decides that no block adds a file.

### §2.5 Test layout — the file each block's tests go into

| Module under test | Test file (existing) | Class / area |
|---|---|---|
| `services/ffmpeg_utils.py` | `tests/test_ffmpeg_utils.py`, plus the `iter_process_lines` area of `tests/test_hls_downloader.py` | `TestIterProcessLines` lives in `test_hls_downloader.py`, **not** in `test_ffmpeg_utils.py` |
| `services/signal_handlers.py` | `tests/test_hls_downloader.py` | `TestSetupSignalHandlers` — the **only** coverage |
| `services/ytdlp_downloader.py` | `tests/test_hls_downloader.py` | `TestYtDlpSubprocessShutdown` |
| `services/segment_downloader.py` | `tests/test_segment_downloader.py` + `tests/test_hls_downloader.py` | `TestParallelSegmentsDownload`, `TestDownloadHlsWithResume`, `TestPreserveSegmentsReporter` |
| `services/batch_downloader.py` | `tests/test_batch_downloader.py` | `TestBatchDownloaderSemaphore`, `TestBatchCancellationReporting`, `TestCorrelationInheritance` |
| `infrastructure/browser.py` | `tests/test_browser_infrastructure.py` | `TestBrowserManager` |
| `services/extractor.py` | `tests/test_extractor.py` | incl. the browser-shutdown case |
| `config.py` | `tests/test_config.py` | sees a new `Settings` field automatically |
| packaging gate | `tests/test_packaging.py` | `EXPECTED_SDIST_ENTRIES` — only if a file was added |

---

## §3 Execution blocks

Eleven blocks. Each is **one commit** and **independently verifiable** against §2.1's four
commands. **Read only the block you are handed** — §3 is self-contained per block; §4 is needed only
if you are scheduling.

---

### B1 — Make the stop observable while a child's output read is in flight

**Findings carried:** `CON-001` leg 1 of 3 — **CRITICAL** · `RUNTIME-ERROR` · **mandatory**.

**Goal.** `iter_process_lines` must run `on_shutdown` while the reader is **blocked**, not after
`readline()` returns on its own — so a stop during a yt-dlp or ffmpeg transfer reaches
`cancel_subprocess` and the child's await can return.

**Why alone, why first.** This is the only leaf-module, single-function CRITICAL fix in the corpus.
It has **no dependencies**, breaks the fewest tests, and everything else in the cancellation story
assumes the child can actually be reached. It is the reason `B5` is even meaningful.

**The validator's corrections applied to this block's wording:**
- The stop is checked only **between** lines today; `on_shutdown` is invoked from inside the *next*
  loop iteration, i.e. only after the blocked read returns. That is the defect.
- **"Only `on_shutdown` terminates the child" is over-stated.** `cancel_subprocess` is also reached
  at the two post-drain/`finally` guards in `downloader.py` and at the two yt-dlp sites — **six call
  sites in total**, of which the two `on_shutdown` closures become reachable under this fix. Narrow
  the phrasing wherever it is restated.
- **There is no correlation-id obligation.** The artifact's cross-reference to correlation-id
  shadowing in `downloader.py` is **dead**: `ENT-012` was fixed by `0790157` and `downloader.py`
  contains no correlation code.
- **The R5(iii) leg is not a defect and must not be implemented as one.**

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/ffmpeg_utils.py` | `iter_process_lines` | Make the shutdown state observable **while `stream.readline()` is in flight**, and invoke `on_shutdown` on that path — so a stop unblocks the drain without waiting for the child to emit another line. |
| `services/ffmpeg_utils.py` | `iter_process_lines` (the `while True:` loop head) | The between-lines stop check and its `on_shutdown` call must remain, **or** be subsumed by the in-flight path — but `on_shutdown` must fire **at most once** for the whole generator (a currently-green test asserts exactly-once). |
| `services/ffmpeg_utils.py` | `iter_process_lines` docstring | The docstring's stated termination condition ("an optional `on_shutdown` callback **can cancel the subprocess so `readline` unblocks**") describes the *intent*, not the behaviour. It must be made true, not deleted. |
| `services/ffmpeg_utils.py` | `read_progress` | **Read-only obligation.** It delegates to `iter_process_lines` and takes `shutdown_event` as a **parameter** (defaulting to a throwaway `asyncio.Event()`). **That is deliberate and stays deliberate.** Verify it still works against the changed helper. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp`'s `_monitor_progress` and `_drain_output`; `_on_shutdown` | **Read-only obligation.** Both drains pass `on_shutdown=_on_shutdown`; both are raced against `process.wait()` through `_await_first_and_cancel_others`. Verify the drain now returns on the stop so the race completes. |
| `services/downloader.py` | `_monitor_progress` and `_drain_stderr`; their local `_on_shutdown` closures | **Read-only obligation.** Same two drains on the ffmpeg path. |
| `services/ytdlp_downloader.py` | `_download_with_ytdlp` docstring — the "no application-level download timeout is imposed" decision | **MUST SURVIVE BYTE-IDENTICAL.** This block must not add a timeout to `process.wait()` or to the drain. §5.2's prohibition applies. |

**Tests required**

- **ADD** `tests/test_hls_downloader.py::TestIterProcessLines` — a test that **can actually observe
  the blocked-read case**, which none of the four existing ones can (they all either pre-set the
  event or exhaust a finite `side_effect` list, and two of them replace `signal.signal` wholesale).
  Drive it with a real `asyncio.StreamReader` fed by `feed_data` on one line and then nothing, set
  the event while the reader is blocked, and assert `on_shutdown` ran **and** the generator
  terminated. No subprocess, no network.
- **ADD** a "callback fires exactly once" assertion alongside the existing
  `test_invokes_on_shutdown_callback`, or extend it. This is the guard that catches a race-based
  fix that can double-fire.
- **MUST STAY GREEN UNCHANGED** `tests/test_hls_downloader.py::TestIterProcessLines`'s four existing
  cases, and `::TestYtDlpSubprocessShutdown::test_ytdlp_cancelled_on_shutdown_returns_none` (it
  pre-sets the event and asserts `cancel_subprocess` was awaited).

**Dependencies:** `depends_on: []`. It blocks `B5` (`C2`).

**Risk class: HIGH.** CRITICAL finding; a shared primitive with seven test references; the
failure mode of a *partial* fix is a drain that returns without killing anything.

**Prohibitions inherited (binding, negative acceptance criteria)**
1. `ffmpeg_utils.py` gains **no** new import — in particular no `downloader_throttle`. It must remain
   a leaf.
2. `read_progress` keeps `shutdown_event` as a **parameter**.
3. No timeout is added to any transfer stage; the yt-dlp decision comment is byte-identical.
4. The commit body states the narrow finding: the stop is invisible to a read **in flight**; the
   await never returns; `cancel_subprocess` is not reached **through the drain**. It does **not** say
   the `on_shutdown` callback is the only kill path.
5. The commit body states there is **no correlation-id obligation**.
6. The R5(iii) leg is **not** claimed as fixed.
7. No re-export line in `downloader.py` is edited.

**Commit shape.** One commit, subject naming `iter_process_lines` and the in-flight stop
observation, body carrying the measured before/after (reader returned within N s of the stop:
before → not; after → yes) and corrections 4–6 above. Findings cited as `CON-001`.

---

### B2 — Settle the siblings, and stop conflating "nothing to do" with "cancelled"

**Findings carried:** `CON-006` + `CON-007` + `CON-008` — **MEDIUM** each · `RUNTIME-ERROR` ·
**mandatory**. Ordering enforced: **`phase04/VAL-402`**.

**Goal.** `_await_and_cancel` must distinguish its three outcomes at the **type level**, settle
every sibling task before returning *or* re-raising, and stop logging `shutdown_requested` for a
cancellation the stop state never requested.

**Why one block.** `phase04/VAL-402` names the exact set and the exact reason: all three edits land
in the **same 25-line function**, and both `CON-006` and `CON-008` move the meaning of the single
`None` its one consumer branches on. `CON-007`'s settle work belongs in the same change: "all three
findings target one helper whose reason for existing is to settle its tasks."

**The validator's corrections applied to this block's wording:**
- The siblings outlive a caller that was told the download **failed**, not *finished*.
  `download_hls_with_resume`'s `finally` logs `preserving_segments_for_resume` **while they are
  still writing** `.ts` files. That is the sharper statement and it is what the fix closes.
- **"Its HTTP session slot" is imprecise.** The session's `async with` exits as the exception
  propagates, so a surviving sibling's next request fails on a **closed session**, not on an
  occupied slot.
- The siblings are **not leaked permanently** — each is bounded by its own transfer's
  `download_timeout`. What is real is that they **outlive the operation that owned them**, still
  holding a permit and a file handle.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/segment_downloader.py` | `_await_and_cancel` — the `if not tasks:` early return | "Nothing to do" must **not** be `None`. It reaches `_tally_and_merge`, so a fully-resumed download merges instead of being reported as failed. |
| `services/segment_downloader.py` | `_await_and_cancel` — `await asyncio.gather(*tasks)` without `return_exceptions` | A raising part must **not** orphan its siblings. The cancel-and-re-await settle sequence must run on **any** exception, not only on `CancelledError`. |
| `services/segment_downloader.py` | `_await_and_cancel` — the `except asyncio.CancelledError` branch's `logger.info("download_cancelled", reason=...)` and `return None` | `CancelledError` must be **re-raised** after the siblings settle, and the log's `reason` must distinguish a stop-state-driven shutdown from a plain cancellation. |
| `services/segment_downloader.py` | `_await_and_cancel`'s return annotation and its docstring | The signature must **carry** the three-way distinction. The docstring already promises "List … on success, None if cancelled" — make the code keep that promise, and make the annotation express it. |
| `services/segment_downloader.py` | `_process_downloaded_segments` — the single consumer's `if download_results is None:` guard | Must branch on the **identity** of the outcome, never on truthiness. **A falsy "nothing to do" result reaching `if not download_results` silently reinstates `CON-006`.** |
| `services/segment_downloader.py` | `_tally_and_merge` | Its two existing `None`-returning arms are `Path | None` and are unaffected; verify the empty-list case reaches the merge branch and that the "no explicit failure recorded" arm still works. |
| `services/segment_downloader.py` | `download_hls_with_resume`'s `finally` → `_log_preserve_segments` | **Read-only obligation.** Re-read it: with the settle fix, the siblings are gone by the time it logs. The block report must state whether `preserving_segments_for_resume` is still accurate. |

**Tests required**

- **ADD** `tests/test_segment_downloader.py` or the segment area of `tests/test_hls_downloader.py` —
  **the missing resume-case test**: every segment already present on disk ⇒ the factory produces zero
  tasks ⇒ the merge **is** reached and the finished video is produced. **This test does not exist
  today and is the whole point of `CON-006`.**
- **ADD** a sibling-settle test: one part raises ⇒ **no** sibling task is left pending after the
  helper returns, and each released its permit.
- **ADD** a cancellation-propagation test: cancelling the holder ⇒ `CancelledError` **propagates**,
  and the log's `reason` is the cancellation value, **not** `shutdown_requested`.
- **VERIFY, do not assume** — `tests/test_hls_downloader.py::TestDownloadHlsWithResume::test_preserves_segments_on_segment_download_failure`
  asserts `result is None` while one of two segments is missing. That is the **failed-transfer**
  path (`_await_and_cancel` receives one real task returning `(1, False)`, `_tally_and_merge` runs,
  the not-all-succeeded arm fires). The code context believes it stays green; **the block must run
  it and state the result.** If it does not stay green, it is re-scoped with the reason.
- **MUST STAY GREEN UNCHANGED** — `tests/test_batch_downloader.py::TestBatchCancellationReporting`,
  in particular `::test_uninterrupted_failed_download_is_still_a_failure`: an **un-cancelled** `None`
  must remain `FAILED` with exit `1`. That is the live-semantics constraint `CON-008`'s fix must not
  break.

**Dependencies:** `depends_on: []`. It blocks `B5` (`C3`), `B6` (`C1`) and `B7` (`C6`).

**Risk class: MEDIUM-HIGH.** A return-contract change with one consumer, a falsy-value hazard the
validator spelled out, and a live interaction with the documented exit code `130`.

**Prohibitions inherited (binding)**
1. `[]`-versus-`None` **alone** is not sufficient — `phase04/VAL-402` requires the empty case to be
   explicit **at the type level**. The outcome must be a `StrEnum` member or a **frozen dataclass**
   defined in `segment_downloader.py` (**not** in `models/`), per rules 4, 6 and 10.
2. The consumer must **not** branch on truthiness.
3. No class hierarchy.
4. The fix stays **inside `_await_and_cancel` and its one consumer** — no new module (§2.3).
5. `_classify_download_result`'s invariant is preserved: a download that raised `CancelledError`
   never reaches it, and a genuinely-`None` result with the stop state unset is still `FAILED`.
6. The commit body's consequence statement is the **corrected** one (failed, not finished; closed
   session, not occupied slot).
7. The siblings are **not** described as permanently leaked.

**Commit shape.** One commit covering all three findings, cited `CON-006`, `CON-007`, `CON-008` and
`phase04/VAL-402`. The body states the outcome type chosen and the rejected alternatives with the
reason, plus corrections 6–7 above.

#### §3.1 Decisions `B2` explicitly does **not** make

**The shape of the outcome — the sentinel.** Four viable shapes, and they are not equivalent:

- (a) **Empty list for "nothing to do", `None` for cancelled** — the minimal fix. *Pro:* smallest
  diff, and it is what the helper's docstring already says. *Con:* `phase04/VAL-402` names this
  explicitly as the shape that survives neither a later truthiness tidy nor a type checker;
  `[]` and `None` are not distinguished by the annotation.
- (b) **A `StrEnum`-backed outcome** (`COMPLETED` / `NOTHING_TO_DO` / `CANCELLED`) carried alongside
  the results. *Pro:* rule 10's shape; greppable; the distinction survives a refactor. *Con:* a
  second value threading through a 7-argument helper; `NOTHING_TO_DO` and `COMPLETED` differ only in
  list length, which re-introduces a length check somewhere.
- (c) **A frozen dataclass result** carrying the outcome **and** the results — e.g.
  `SegmentBatchOutcome(results, outcome)`. *Pro:* one return value, no parallel channel, immutable,
  rule 6-safe. *Con:* the largest diff of the four; every call site of `_tally_and_merge`'s argument
  list must be reviewed.
- (d) **A module-private singleton sentinel object** (`_CANCELLED`) distinct from `None`. *Pro:* the
  smallest change that is identity-checked. *Con:* a bare singleton is rule 10's "bare literal" in
  spirit, and a sentinel that is not a `StrEnum` is harder to log.

→ **RESOLVED by `B2`'s block-level Planner, measured on the live tree: `(c)`, a frozen
dataclass result carrying the outcome and the results.** Two module-private types in
`segment_downloader.py`: `class _SegmentFanoutOutcome(StrEnum)` with **exactly two** members —
`COMPLETED`, `NOTHING_TO_DO` — and `@dataclass(frozen=True) class _SegmentFanoutResult` with fields
`outcome: _SegmentFanoutOutcome` and `results: list[tuple[int, bool]]`. There is **no `CANCELLED`
member**: `CON-008`'s fix makes cancellation an *exception that is re-raised*, not a returned value,
so a third member would be vocabulary the code can never produce — and a fixer who "uses" it
reinstates `CON-008`. Rejected:

- **(a)** — the floor. It leaves `list[tuple[int, bool]] | None` unable to distinguish an empty
  result from a populated one (rule 9), which is the defect `VAL-402` exists to remove.
- **(b)** — a `StrEnum` alongside the results. Cheaper by one 4-line dataclass, and it does pass
  `mypy --strict` against the live `_tally_and_merge` signature (measured). **Rejected on the
  consumer, not on size:** the unpacking puts a bare, falsy `list` in the consumer's scope next to
  the guard, so `if not results: return None` is a local, behaviour-preserving "tidy" — the exact
  edit `VAL-402` names. Its three-member form also carries a `CANCELLED` member the fixed code can
  never return. `(c)` leaves the guard reading a *named member* of a *named field*, and the list is
  only ever reached as `fanout.results`.
- **(d)** — a bare module-private sentinel. Rule 10's "bare literal" in spirit, worse to log than a
  `StrEnum` member, and no stronger than `(c)` on the identity check that invariant 1 requires.

**Measurement that pinned `(c)`'s one implementation trap:** the results field **must be a `list`**,
not a `tuple`. With a `tuple`, the consumer's call into `_tally_and_merge` fails `mypy --strict` with
`Argument 1 to "_tally_and_merge" has incompatible type "tuple[tuple[int, bool], ...]"; expected
"list[tuple[int, bool]]"`, which would force a **third** function's annotation to change and breach
"the fix stays inside `_await_and_cancel` and its one consumer". With a `list`, `_tally_and_merge` is
untouched — only its call site's first argument expression changes. Measured at the same time: `[]`
reaching the real `_tally_and_merge` with all segments on disk **is** correct (the merge branch
runs), so its `if download_results and not all(...)` guard needs no behavioural change — it becomes
reachable with an empty list for the first time, and a one-line comment must record that.

**Residual weakness, stated once:** `outcome` is derivable from `len(results)`, so the field is
redundant. It is kept because the redundancy is *named and documented in the docstring* — the next
editor learns the invariant instead of rediscovering it — and because it is the difference between
the distinction being stated in the type and being carried by a positional convention.

**Call sites, measured:** `_await_and_cancel` **1** (`_process_downloaded_segments`),
`_process_downloaded_segments` **1** (`_run_download_session`), `_tally_and_merge` **1** (the same
consumer), **0** in `tests/`. The "second value threading through a 7-argument helper" objection to
`(b)` and the "widened argument list" objection to `(c)` are both inert at that count.

---

### B3 — Restore the previously installed process-level handler on the branch that runs

**Findings carried:** `CON-001` leg 3 of 3 — **CRITICAL** · `RUNTIME-ERROR` · **mandatory**.

**Goal.** `cleanup_signal_handlers` must put back the handler that was installed **before** this
module displaced it, so `asyncio.run`'s own SIGINT restore is no longer skipped.

**Why separate from `B1`.** Different module, different failure mode (process-level state *after*
`asyncio.run` returns, not an in-transfer hang), different verification (handler identity, not
subprocess liveness). It is also the precondition that makes `B5`'s forward route implementable.
Splitting keeps the CRITICAL hang fix (`B1`) committable today without waiting for anything.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/signal_handlers.py` | `setup_signal_handlers` — the two `signal.signal(sig, lambda s, f: _handle_signal())` install sites | Capture each signal's **pre-install** handler at install time and retain it in module state, keyed by signal. Both signals must be captured, because **their pre-install values differ**. |
| `services/signal_handlers.py` | `cleanup_signal_handlers` — the `if loop is not None:` branch that calls `loop.remove_signal_handler(sig)` inside `except (NotImplementedError, KeyError, RuntimeError): pass` | This branch is **the one that runs** at both shipped call sites, and it currently achieves nothing. It must perform the process-level restore as well (or the process-level restore must become reachable). |
| `services/signal_handlers.py` | `cleanup_signal_handlers` — the `else:` branch's `signal.signal(sig, signal.SIG_DFL)` | A single "reset to default" restore is **insufficient and wrong for SIGINT**: the displaced handler is `Runner._on_sigint`, not `SIG_DFL`. The restore value is per-signal and comes from the capture. |
| `services/signal_handlers.py` | module-level `_registered_signals` bookkeeping | Whatever holds the captured previous handlers must be cleared alongside `_registered_signals` so a second `setup`/`cleanup` cycle on a new event loop re-captures rather than reuses a stale value. |
| `services/signal_handlers.py` | `_handle_signal`'s `if not shutdown_event.is_set():` guard | **NOT this block's to change.** The idempotence guard is what `B5` revisits; `B3` must leave it intact and must not "improve" it. |
| `services/signal_handlers.py` | `setup_signal_handlers` / `cleanup_signal_handlers` registration **call sites** (`batch_downloader.py`, `cli.py`) | **MUST NOT BE MOVED.** `ENT-004` (registration placement) is phase 01's and plan 05 `D7` defers it. |

**Tests required**

- **ADD** `tests/test_hls_downloader.py::TestSetupSignalHandlers` (the only existing coverage of this
  module) — a test that installs, asserts the handler is the module's, runs `cleanup_signal_handlers`,
  and asserts the **pre-install handler is back**, per signal, with the two signals asserted
  **separately**. A test that asserts "the handler was reset" without checking *which* value cannot
  see this defect and must not be written.
- **ADD** an assertion that a **second** setup/cleanup cycle re-captures rather than restoring a
  stale value.
- **MUST STAY GREEN UNCHANGED** `TestSetupSignalHandlers`'s existing cases. They replace
  `signal.signal` wholesale, so they must still pass — and they are the *mocked-registration* net,
  which is why they can never observe this defect. They are NOT the idiom for a new test here: a test
  that patches `signal.signal` cannot observe a real pre-install value and therefore cannot prove the
  fix. The new cases exercise the real path with no patching at all.

**Dependencies:** `depends_on: []`. It blocks `B5` (`C4`).

**Risk class: MEDIUM-HIGH.** Signal-handler identity is process-global state; the failure mode is a
handler left displaced (today) or a wrong handler restored (a plausible over-correction).

**Prohibitions inherited (binding)**
1. **No reset-to-`SIG_DFL`.** SIGINT's restore value is the captured `Runner._on_sigint` partial.
2. **No blocking work in the signal context.** `B3` installs and restores handlers only.
3. **No registration move** (`ENT-004`).
4. `ffmpeg_utils.py` and `browser.py` are untouched by this block.
5. The commit body states **six** `cancel_subprocess` call sites, not "only `on_shutdown`".
6. No correlation-id obligation is claimed or discharged here.

**Commit shape.** One commit, cited `CON-001` (leg 3). The body must record the **measured**
pre-install values for both signals — SIGINT `functools.partial(<bound method Runner._on_sigint …>)`,
SIGTERM `Handlers.SIG_DFL` — and state that after `asyncio.run` SIGINT is currently still the
project's own handler and is the same afterwards.

#### B3 — Planner resolutions (the six questions the block left open)

Recorded here so a reader of §3 sees the settled shape. The full reasoning, with the measurements
that decided it, is in §7's `B3 — Planner decisions`.

1. **State.** Two private signal-keyed dicts beside `_registered_signals`: `_previous_handlers` (the
   displaced value) and `_installed_handlers` (the callable installed here, for the identity guard).
   No redundant "did we capture" set — `_registered_signals` stays the single registration gate. The
   value type is `signal._HANDLER | None`; the module may not gain an import.
2. **Capture once per signal**, from `signal.getsignal(sig)` read *before* the install attempt, never
   overwritten on a second setup — otherwise a cleanup would restore this module's own handler and
   re-create the leak.
3. **The restore is `is`-guarded** against the separately stored installed marker: a signal whose
   current handler is no longer the one installed here is left alone. Two maps, two different facts;
   they are cleared as one group.
4. **The restore is hoisted out of the `if` / `else` split** so both branches share one restore, and
   the `else:` branch's `signal.signal(sig, signal.SIG_DFL)` is **deleted**, not corrected.
5. **Docstrings.** Both function docstrings and the `# Track registered signals for loop-scoped
   cleanup` comment are corrected in the same commit (§5.7).
6. **Tests.** Three new cases in the existing class, all on the **real** `signal.signal` with no
   patching, each restoring both pre-test dispositions in an unconditional `finally`: per-signal
   restore by identity; two-setups-one-cleanup (capture-once); and a **synchronous** three-cycle
   `asyncio.run` compounding oracle — the only shape in which three distinct captures and
   `default_int_handler` after every run are observable.

---

### B4 — Release the browser handle unconditionally, and never let a release failure replace the failure that caused the exit

**Findings carried:** `CON-004` + `CON-005` — **HIGH** each · `RUNTIME-ERROR` · **mandatory**.
Ordering enforced: **`phase04/VAL-401`**.

**Goal.** Drop the stop-state guard so `browser.close()` always runs, and widen the release's
exception handling so a release failure is logged and suppressed when an exception is already in
flight.

**Why one block.** `phase04/VAL-401` is explicit: **`CON-004` alone is a correctness regression on the
path it fixes.** On the stop path `_extract_with_browser` raises `CancelledError` immediately after
its stop check, so the exit runs with an exception in flight; once `CON-004` lands, a `close()`
failure there propagates out of `__aexit__` and **replaces the `CancelledError`** — converting an
orderly shutdown into an unhandled driver error. `VAL-401`'s recommendation is to apply `CON-005`'s
suppression **before or with** `CON-004`'s unconditional release, **in one change**.

**The validator's corrections applied to this block's wording:**
- **`CON-004`'s permanent-leak consequence is WITHDRAWN.** The same exit calls `playwright.stop()`,
  and the report's own skip S-2 records that the driver was never launched, so driver teardown
  behaviour was never observed. **The accurate consequence is: the graceful close is skipped, so the
  browser is torn down by driver shutdown rather than by the close path; and if `playwright.stop()`
  exceeds its 10 s bound the teardown is unbounded.** The 10 s `asyncio.wait_for` bound already
  serves the reason the guard exists. **Severity (HIGH) is unchanged.**
- **`CON-005`'s precision correction:** the in-flight body exception is **not** erased — it survives
  as `__context__` and is visible on the traceback. What is lost is that it is **never the exception
  that reaches the operator's summary**, which is exactly what the fix must restore. The consumer
  chain holds: `_download_single`'s catch-all classifies by `type(e).__name__` and would report
  `unexpected_error: <Playwright error type>` instead of the domain status label.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `infrastructure/browser.py` | `BrowserManager.__aexit__` — the `if self.browser and not shutdown_event.is_set():` guard | Drop `and not shutdown_event.is_set()`. The close becomes unconditional; a stop **shortens** the close (via the existing `wait_for` bound) rather than skipping it. |
| `infrastructure/browser.py` | `BrowserManager.__aexit__` — the two `except TimeoutError:` arms around `wait_for(browser.close())` and `wait_for(playwright.stop())` | Widen to catch a **release failure**, log it with the reason the step failed (structlog, `key=value`), and **suppress it when an exception is already in flight**. |
| `infrastructure/browser.py` | `BrowserManager.__aexit__` — the `finally:` that guarantees the driver release | **Preserved exactly.** The `finally` guarantee is real and `CON-005`'s recommendation keeps it: the block report and the re-scoped test must both keep asserting it. |
| `infrastructure/browser.py` | `BrowserManager.__aexit__` **docstring** (the `INT-004` ownership note) | **Currently lies.** It states the exit "checks the shared `shutdown_event` before each step"; the code guards **only the first** step. Correct it as part of this change — this is documentation drift, not a separate finding. |
| `infrastructure/browser.py` | the function-scope lazy `get_shutdown_event` import inside `__aexit__` | **If** the stop-state lookup becomes unused after the guard is dropped, the block must decide explicitly: keep it (with an updated inline reason) or remove it **and** remove the now-unused local. **It must not be moved to module scope and no second lazy import may be added.** |
| `infrastructure/browser.py` | `_BROWSER_CLOSE_TIMEOUT` | **Unchanged.** The 10 s bound is the reason the guard existed; it stays. |
| `services/extractor.py` | `_extract_with_browser`'s stop check raising `asyncio.CancelledError` | **Read-only obligation.** Re-read it and state in the report that the `CancelledError` still reaches `__aexit__` in flight — that is the invariant `CON-005`'s suppression depends on. |

**Tests required — the one confirmed pin in this plan**

- **RE-SCOPE (not delete, not weaken)** `tests/test_browser_infrastructure.py::TestBrowserManager::test_browser_manager_context_exit_stops_playwright_on_browser_close_error`.
  Its `pytest.raises(RuntimeError, match="close failed")` **and its comment** encode the defect. The
  re-scoped test must still assert **`playwright.stop()` ran** (the `finally` guarantee is real) and
  must **add** the new contract: with an exception in flight, the release failure is suppressed and
  the in-flight exception is what escapes.
- **ADD** — a `close()` failure with **no** exception in flight. This is the case the artifact does
  not decide: what should escape? See §3.2.
- **ADD** — the `CON-004` case that does not exist today: **no** test anywhere asserts the close is
  *skipped* on the stop path, and there is none to re-scope; the block must add the missing one —
  **with the stop event set, `browser.close()` is still invoked**, and `playwright.stop()` still runs.
- **MUST STAY GREEN UNCHANGED** `::test_browser_manager_context_exit` (no stop event set — it stays
  green under this fix), `::test_browser_manager_context_exit_handles_close_timeout` and
  `::test_browser_manager_context_exit_handles_playwright_stop_timeout` (both `INT-004`).

**Dependencies:** `depends_on: []`.

**Risk class: HIGH.** Two HIGH findings in one 20-line block, a confirmed test pin, a suppressed
exception in an exit path, and a real (not hypothetical) interaction with a `CancelledError`.

**Prohibitions inherited (binding)**
1. **No permanent-leak claim** in the fix, the commit body, a docstring or a test docstring. The
   narrow consequence only (§ above).
2. The `finally` guarantee is **preserved**, and the re-scoped test still asserts it.
3. The lazy import is **not moved to module scope**; no second lazy import is added.
4. The `INT-004` ownership comment must remain **accurate**; a behaviour change under an existing tag
   is updated or retired, never left lying.
5. The validator's `CON-005` precision is preserved: the in-flight exception survives as
   `__context__`; the fix restores it as the exception that escapes.
6. No claim about what a *real* VK origin or a real Chromium does — this block is verified against
   stand-ins, exactly as the artifact did.

**Commit shape.** One commit carrying both findings, cited `CON-004`, `CON-005`, `phase04/VAL-401`.
The body states the withdrawn claim explicitly (so a reader does not reintroduce it) and the narrow
consequence in its place.

#### §3.2 Decisions `B4` explicitly does **not** make

**What escapes `__aexit__` when a release step fails and no exception is in flight.** The
artifact's recommendation only covers the "already in flight" case. Two coherent readings, and they
differ observably:

- (a) **Suppress always.** Log the failure, never let a release failure escape the context manager.
  *Pro:* consistent; a teardown step never changes what the caller learns; the classification chain
  stays domain-typed. *Con:* a genuine driver crash during a *successful* extraction becomes a log
  line, and the caller believes the teardown succeeded.
- (b) **Suppress only when an exception is in flight; otherwise re-raise.** Matches the finding's
  wording most literally and keeps the diagnostic when there is no competing failure. *Con:* the exit
  has two different behaviours depending on `exc_type`, which is easy to get wrong and easy to
  regress; and a slow-close `TimeoutError` must still be swallowed, so "re-raise" needs an explicit
  exception-set.

→ **Deferred to `B4`'s block-level Planner.** `B4`'s report must state the choice and the rejected
option. Either is acceptable **provided** the timeout arms stay swallowing-only and the in-flight
case is suppressed.

---

### B5 — Make a second interrupt escalate instead of doing nothing

**Findings carried:** `CON-001` leg 2 of 3 — **CRITICAL** · `RUNTIME-ERROR` · **mandatory**.
Ordering enforced: **`phase04/VAL-403`**.

**Goal.** The idempotence guard in `_handle_signal` currently makes a second Ctrl-C a silent no-op.
A second interrupt must **escalate**.

**Why last.** `phase04/VAL-403` is a **severity** dependency, not a hygiene one. The escalating
interrupt never sets the stop state; `B2` fixes the defect that makes such a cancellation vanish;
`_classify_download_result` decides cancelled-vs-failed purely by reading the stop state; so if the
escalation lands first, an escalated interrupt cancels the batch, every item returns `None`, the
batch reports them **failed**, and the process exits `1` instead of the `130` the summary reserves
for an interrupted run — **on exactly the interaction the user was performing, and only on the
second interrupt, so the first still behaves.** The artifact's own tiebreaker: *"Shipping the
escalation first is the one ordering that makes a shipped defect worse than the one it repairs."*

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/signal_handlers.py` | `_handle_signal`'s `if not shutdown_event.is_set():` guard | The **second** fire must take the escalation path instead of returning silently. The first fire's behaviour (one `shutdown_signal_received` record, then `set()`) is unchanged. |
| `services/signal_handlers.py` | the captured previous handler state that `B3` introduces | The forward route consumes it. **`B3` must expose it in a shape `B5` can use; `B3` must not pre-decide how `B5` uses it.** |
| `services/signal_handlers.py` | the handler body | **No blocking work in the signal context.** If the chosen route needs to kill a child or cancel a task, it must be **scheduled onto the loop**, not performed between bytecodes. |
| `services/ffmpeg_utils.py` | `cancel_subprocess` | **Read-only obligation** unless the chosen route needs a live-child registry (see §3.3). The terminate → `wait_for(wait(), 5.0)` → `kill()` → `wait()` sequence and its `ProcessLookupError → False` contract are unchanged. |
| `services/segment_downloader.py` | `_await_and_cancel`'s cancellation branch (**after `B2`**) | **Read-only obligation.** `B5` must not reach into `B2`'s code. The reason it depends on `B2` is that the escalation's cancellation must *survive* to the batch summary. |
| `services/batch_downloader.py` | `_classify_download_result`'s stop-state read; `_run_batch_with_progress`'s `except asyncio.CancelledError` fan-out branch; the summary's `130` return | **Read-only obligation.** Re-read and state in the report that a second interrupt now reaches `_print_batch_summary` as a **cancellation** and yields `130`, not `1`. |

**Tests required**

- **ADD** `tests/test_hls_downloader.py::TestSetupSignalHandlers` — first fire sets the stop state and
  records exactly one event; second fire takes the escalation path; a third fire does not re-escalate.
- **ADD** — an exit-code test proving the escalation **yields `130`, not `1`**, driving the real
  classification chain (`_classify_download_result` → the summary's return). This is the test
  `phase04/VAL-403` exists to demand, and it is the reason `B5` is serialised behind `B2`.
- **MUST STAY GREEN UNCHANGED** — `tests/test_batch_downloader.py::TestBatchCancellationReporting`
  (both halves: event set ⇒ `[CANCELLED]*n` and exit `130`; event unset ⇒ `[FAILED]*n` and exit `1`),
  and the documented `130` in `docs/99-reference/cli-reference.md`.

**Dependencies:** `depends_on: [B1, B2, B3]`. `C2` (`B1`), `C3` (`B2`), `C4` (`B3`).

**Risk class: HIGH.** The escalation interacts with three other modules, is gated by a severity
dependency, and touches the one documented exit code for user interruption.

**Prohibitions inherited (binding)**
1. **No blocking work in the signal context** (Windows fact).
2. The fix must **not assume the child survives** — a console Ctrl-C also delivers `CTRL_C_EVENT` to
   child processes on Windows.
3. **`ENT-004` is not touched**: registration placement stays where it is.
4. **No correlation-id obligation.**
5. The first interrupt's observable behaviour is **unchanged**: one record, the stop state set.
6. `phase04/VAL-403`'s chain must be re-verified in the report, step for step, against the **landed**
   `B2` code — not against the artifact's description of it.

#### §3.3 Decisions `B5` explicitly does **not** make

**The escalation route.** Three viable shapes, and the choice has a real architectural consequence:

- (a) **Forward to the displaced handler** — re-invoke the captured pre-install SIGINT handler
  (`asyncio.runners.Runner._on_sigint`), whose first action is to cancel the main task.
  *Pro:* smallest change; no new concept; reuses the state `B3` already captures; restores the
  behaviour the runtime had before this module displaced it. *Con:* **this is the route
  `phase04/VAL-403` warns about** — it is precisely the cancellation `B2` was absorbing, which is
  why `B5` is serialised behind `B2`; and it depends on a CPython private (`Runner._on_sigint`).
- (b) **Force-kill the live child(ren)** on the second interrupt.
  *Pro:* closes the gap `VAL-403` identifies **without** depending on `B2`, and it is the only route
  that helps when the hang is in the subprocess rather than in the await chain. *Con:* requires a
  **live-child registry**, which is a genuinely new cross-module concept — and a signal handler
  cannot call `terminate()`/`kill()` without blocking the main thread, so it must be scheduled onto
  the loop. Where does the registry live? That is a second fork (see below).
- (c) **Forward, then force-kill after a short grace** — escalation ladder.
  *Pro:* covers both gaps; matches operator expectation for "the first one didn't work". *Con:* two
  mechanisms, a new timing constant, and the largest surface of the three; rule 5 penalises it
  hardest.

→ **Deferred to `B5`'s block-level Planner**, informed by an **Auditor** pass that re-derives the
subprocess/signal interaction against the landed `B1`/`B3` code. **A Planner that selects (b) alone
must still justify it against (a)** — (a) is materially smaller and its only real cost is the
dependency on `B2`, which this plan already honours.

**The home of a live-child registry (only if route (b) or (c) is selected).** Three options:
inside `ffmpeg_utils.py` (which already owns `cancel_subprocess` and is a **leaf**, so a registry
there drags no new module edge); inside `downloader_throttle.py` (which owns the stop state, but
would then be imported by subprocess utilities and would make `ffmpeg_utils` a non-leaf — **forbidden
by §2.3**); or a **new `src/` module** (cleanest layering, **but trips `EXPECTED_SDIST_ENTRIES` and
must be justified against rule 5's "prefer the simplest obvious solution"**).
→ **Deferred to `B5`'s Planner**, and only live if route (b)/(c) is chosen. §2.3's no-new-file
decision is the default.

---

### B6 — Bound the live segment-task set by the configured ceiling

**Findings carried:** `CON-003` *(segment layer)* — **HIGH** · `RUNTIME-ERROR` · **mandatory**.

**Goal.** `_create_segment_download_tasks` must not materialise one task per missing part. The
configured ceiling must be the only thing determining how much work is in flight.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/segment_downloader.py` | `_create_segment_download_tasks` — the plain `for` loop with `tasks.append(asyncio.create_task(...))` returning the whole list | Produce tasks **bounded by the ceiling** — from a worker pool or a bounded queue — instead of materialising every missing part up front. |
| `services/segment_downloader.py` | `_download_segment_concurrent` — `async with policy.semaphore:` inside the task body | The claim that actually limits transfers stays where it is. The fix changes **how much work exists**, not **where the claim is taken**. |
| `services/segment_downloader.py` | `_download_segment_concurrent` — the stop check immediately after acquiring, and its retry delay `await asyncio.wait_for(shutdown_event.wait(), timeout=delay)` | **Preserved.** A stop must still be observed while a transfer waits for a permit, and the per-transfer `download_timeout` bound is unchanged. |
| `services/segment_downloader.py` | `_run_download_session` — the segment-local `asyncio.Semaphore(settings.max_concurrent_downloads)` and the `is_bounded_batch` boolean | **Preserved.** The segment layer owns its own primitive and carries only the boolean. |
| `services/segment_downloader.py` | the `D-01` non-reentrancy invariant comment | **Preserved and kept accurate.** `asyncio.Semaphore` is not reentrant; the batch permit is acquired **once per video**, never per segment. |
| `services/segment_downloader.py` | `_process_downloaded_segments` and `_await_and_cancel` (**after `B2`**) | **Read-only obligation.** `B6`'s output feeds them. The block report must state explicitly how a bounded producer's output reaches `B2`'s outcome type. |

**Tests required**

- **ADD** — the live-task-count measurement the artifact made: with N missing segments and a ceiling
  of C, the number of **live tasks** stays at or near C instead of N. Assert the bound, not the peak
  (the existing semaphore tests assert peak and are unaffected).
- **ADD** — a correctness test that **every** segment is still attempted and the results still reach
  the merge (a bounded producer that drops items is the obvious failure mode).
- **ADD** — a stop test: a stop while the producer is still producing **terminates** the producer
  and does not leave orphan tasks.
- **MUST STAY GREEN UNCHANGED** — `tests/test_batch_downloader.py::TestBatchDownloaderSemaphore::test_segment_layer_does_not_acquire_caller_video_semaphore`
  and `::test_batch_completes_without_deadlock_when_max_reached`. **These two are the regression net
  for any `CON-003` remedy** and neither may be edited.

**Dependencies:** `depends_on: [B2]` (`C1`). The factory's return type feeds
`_process_downloaded_segments`, whose contract `B2` rewrites — a statement-level dependency, not file
co-location.

**Risk class: HIGH.** The obvious failure mode of a bounded producer is **dropping work** or
**deadlocking**; and `D-01` is an invariant that a wrong remedy violates silently.

**Prohibitions inherited (binding)**
1. **No new `src/` or `tests/` file** (§2.3).
2. **`D-01` preserved**: the batch permit is acquired once per video, never re-acquired per segment.
   The remedy is **not** "gate the segment fan-out on the batch semaphore".
3. `is_bounded_batch` remains a boolean carried across; the segment layer keeps owning its primitive.
4. The per-transfer `download_timeout` bound and the post-acquire stop check are unchanged.
5. The **R5(iii) behaviour is explicitly not being fixed here** — waiting for a permit while a stop
   is set is ordinary bounded blocking, already covered by `B1`'s reachability and not a `CON-003`
   subject.

**Commit shape.** One commit, cited `CON-003` (segment layer). The body must state the **live-task
bound** the remedy achieves and must not claim the batch layer is bounded (that is `B7`).

---

### B7 — Bound the live per-URL task set by the configured ceiling

**Findings carried:** `CON-003` *(batch layer)* — **HIGH** · `RUNTIME-ERROR` · **mandatory**.

**Goal.** `_run_batch_with_progress` must not create one task per URL. The live set must track the
configured ceiling, not the input size.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/batch_downloader.py` | `_run_batch_with_progress` — the list comprehension `asyncio.create_task(_download_single(...)) for i, url in enumerate(urls)` | Bound the live task set by `settings.max_concurrent_downloads`. |
| `services/batch_downloader.py` | `_run_batch_with_progress` — the `for coro in asyncio.as_completed(tasks)` loop and its `except asyncio.CancelledError` fan-out branch | **Preserved, and reviewed against the landed `B2`.** The fan-out is the route by which a cancellation reaches siblings and the route the summary's `130` depends on. A bounded producer must not remove or restructure it. |
| `services/batch_downloader.py` | `_run_batch_with_progress` — `reporter.start()` and the comment explaining that no `await` occurs between task creation and `start()` | **Re-read.** A bounded producer introduces an `await` (or a producer task) and this comment's invariant must be re-derived, not assumed. |
| `services/batch_downloader.py` | `_run_batch_with_progress` — `setup_signal_handlers()`, the correlation bind, `finally: cleanup_signal_handlers(); clear_correlation_id()` | **Preserved exactly.** Ordering of the setup/cleanup around the new production is unchanged. |
| `services/batch_downloader.py` | `_TrackedSemaphore` / `ConcurrencyTracker` and the `shared_semaphore` construction | **Preserved.** `D-01` still holds: one permit per video, acquired once, tracked for peak. |
| `services/batch_downloader.py` | `_download_single` and `_classify_download_result` | **Read-only obligation.** The `None`-vs-`Path` classification contract `B2` interacts with is untouched here. |

**Tests required**

- **ADD** — the live-task-count measurement: with N URLs and ceiling C, live tasks stay bounded while
  **every** URL is still attempted and still appears in the summary.
- **ADD** — a stop test: a stop while URLs remain unstarted **stops producing**, cancels what is in
  flight, and the summary still returns the documented interrupted result.
- **MUST STAY GREEN UNCHANGED** — `tests/test_batch_downloader.py::TestBatchDownloaderSemaphore::test_batch_completes_without_deadlock_when_max_reached`
  (asserts `peak <= max_concurrent_downloads`), and the whole of
  `::TestBatchCancellationReporting`.

**Dependencies:** `depends_on: [B2]` (`C6`). `B2` **activates** the cancel-and-gather fan-out that
`B7`'s producer must preserve; reviewing `B7` against the dead branch would be reviewing the wrong
code.

**Risk class: HIGH.** Same failure modes as `B6` (dropped work, deadlock), plus the batch layer's
`130` path and the reporter's lifecycle.

**Prohibitions inherited (binding)**
1. **No new `src/` or `tests/` file.**
2. **The `except asyncio.CancelledError` fan-out branch is not removed or restructured** — that is
   the route `B2` makes live, and the summary's `130` depends on it.
3. `D-01` preserved: the permit is acquired once per video.
4. `setup_signal_handlers` / `cleanup_signal_handlers` / `clear_correlation_id` placement unchanged.
5. The commit body must not claim the **segment** layer is bounded (that is `B6`).

**Commit shape.** One commit, cited `CON-003` (batch layer). The body states the measured live-task
bound before and after.

---

### B8 — Derive the transport pool ceiling from the setting and give the per-origin ceiling a value

**Findings carried:** `CON-009` — **MEDIUM** · `BEST-PRACTICE` · **`advisory`**.

**Goal.** `TCPConnector`'s `limit` must be derived from `max_concurrent_downloads` rather than being
a literal, and `limit_per_host` must carry an explicit value instead of being left at `0`
(unbounded).

**Ownership seam, stated once.** Plan 07 §1.4 deferred this literal here and its `B14` carries a
**prohibition**: *"MUST NOT touch `_create_connector`."* `_create_connector` is **untouched** by
plan 07's landed commits and still reads `limit=10`. **The seam held; this plan owns it and the
prohibition is released by this block.** `B8` must read phase 03's `NET-014` **through** that
store's `VAL-001` adjudication, which ruled in favour of `CON-009`.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/segment_downloader.py` | `_create_connector` — both `aiohttp.TCPConnector(..., limit=10)` return paths | `limit` becomes derived, not literal. `limit_per_host` gains an explicit value. |
| `services/segment_downloader.py` | `_run_download_session` — the connector construction paired with its own `ClientSession`, and the segment-local semaphore | **Read-only obligation.** One connector per download session, each with its own session: **the aggregate is per-download × downloads, not process-wide.** No process-wide pool exists and this block must not introduce one. |
| `config.py` | `Settings.max_concurrent_downloads`'s `Field(description=...)` | Only if the chosen shape changes the setting's meaning. The description currently documents the **two-level** sizing (batch gate + segment fan-out); the transport ceiling becomes a **third** level and the description must say so accurately. |
| `config.py` | a new `Settings` field, **iff** the chosen shape introduces one | Rules: bounded (`ge`/`le`), a `Field` with a real `description`, and **three** places — field description, `.env.example`, `docs/11-guides/configuration.md` (table row **and** prose section) — because `extra="forbid"` turns a missing entry into `extra_forbidden` on upgrade. Any `.env.example` value must be **constructed against the model and the construction recorded**. |
| `services/segment_downloader.py` | `_create_connector`'s `ssl_verify` branch and its `ssl_verification_disabled` warning | **Preserved.** The `ssl` argument shape is unchanged; only the ceiling arguments move. |

**Tests required**

- **ADD** — a data-driven test reading the constructed connector across the declared range of
  `max_concurrent_downloads` (and both `ssl_verify` values), asserting `limit` **follows the setting**
  and `limit_per_host` is the intended explicit value. **Four of four identical values are the
  defect**; a test that only asserts `limit == <a constant>` would encode it.
- **ADD** — a test asserting the **aggregate is the product the commit body claims**, so the
  arithmetic cannot drift from the code.
- **MUST STAY GREEN UNCHANGED** — `tests/test_config.py` in full; the config guide stays consistent
  with the model.

**Dependencies:** `depends_on: []`.

**Risk class: MEDIUM (advisory).** The defect is real; the finding is `advisory`; **the
over-engineering risk is higher than the defect.** Rule 5 is the binding constraint.

**Prohibitions inherited (binding)**
1. **No process-wide pool and no rate limiter.** The literal only; the request *rate* against one
   origin is phase 03's.
2. `B8`'s report must carry the arithmetic explicitly: **per-download ceiling; aggregate
   `10 × max_concurrent_downloads` today = 40 at the default, 160 at the declared ceiling; no
   process-wide bound exists** — and after the fix, the *new* arithmetic, stated the same way.
3. **No new `src/` or `tests/` file** unless justified.
4. Phase 03's `NET-014` is read **through** its store's `VAL-001` adjudication, which ruled for
   `CON-009`.
5. If a setting is added: three-place rule, `.env.example` value constructed against the model, and
   **no CLI option** unless it is `None`-defaulted.

#### §3.4 Decisions `B8` explicitly does **not** make

**The remedy shape.** Three viable options, and this is the plan's clearest over-engineering trap:

- (a) **Derive `limit` from `max_concurrent_downloads`** (e.g. the setting itself, or a small multiple
  of it), and set `limit_per_host` to an explicit value.
  *Pro:* one-line-ish change; **no new setting**; one setting then governs the whole process, which
  is the finding's own recommendation; no `EXPECTED_SDIST_ENTRIES` cost; no `.env.example` change;
  rule 5 strongly favours it. *Con:* a **single setting now governs three levels with different
  units** (videos, segments, connections), which is arguably the confusion the finding is about — so
  the field description must name all three.
- (b) **Add a new setting** for the transport ceiling (e.g. a connection-pool size).
  *Pro:* the operator gets a real knob; each level's unit is explicit; the guide's table gains an
  honest row. *Con:* a new `Settings` field means the **three-place rule**, `extra="forbid"`
  compatibility work, an `.env.example` value that must be proven legal, guide prose, and a larger
  review surface — for an **advisory** finding.
- (c) **Introduce a process-wide shared connector/pool.**
  *Pro:* a genuine process-wide bound, which is what the phrase "one setting governs the whole
  process" might suggest. *Con:* **this is a redesign, not a fix.** It changes connector ownership
  from per-download to per-process, alters session/connector lifetimes, and `CON-009` explicitly does
  not ask for it. **Rule 5 forbids it by default.**

→ **Deferred to `B8`'s Researcher** (multiple viable approaches with architectural implications) and
then to the block's **Planner** for the concrete selection. **Rule 5 makes (a) the default and the
starting hypothesis**; (b) requires a written justification for the operator-facing cost; (c) is out
of scope for this finding and would need a separate plan.

---

### B9 — State the exit-path thread-join bound where the timeout is configured

**Findings carried:** `CON-010` — **MEDIUM** · `BEST-PRACTICE` · **`advisory`**.

**Goal.** The bound the interpreter actually applies when an abandoned off-loop extraction is joined
at teardown is stated where the timeout is configured — and, if a code remedy is justified, it is
applied at that call site.

**What is measured.** `_extract_with_ytdlp` wraps `loop.run_in_executor(None, _sync_extract)` in
`asyncio.wait_for(..., timeout=self.settings.download_timeout)`. On expiry the **asyncio future is
cancelled; the executor thread is not, and cannot be.** `asyncio.run` then blocks on
`loop.shutdown_default_executor(constants.THREAD_JOIN_TIMEOUT)` while tearing the interpreter down.
`asyncio.constants.THREAD_JOIN_TIMEOUT` is **300** — numerically identical to `download_timeout`'s
default of **300**, which is exactly why this is easy to miss. The consequence is a **silent stall
after the summary and the exit code have already been produced**.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `config.py` | `Settings.download_timeout`'s `Field(description=...)` | **The documentation landing site.** State that the setting's reported bound is not the bound applied on the exit path, and name that bound. The description today says only "HTTP client timeout … for individual segment requests and playlist fetches", while in reality it also bounds the local merge and the off-loop extraction. |
| `services/extractor.py` | `_extract_with_ytdlp` — the `asyncio.wait_for(loop.run_in_executor(None, _sync_extract), timeout=…)` and its `except TimeoutError` arm | **Documentation always; code change only if the fork below resolves to one.** The `ExtractionError` message and the `ytdlp_extraction_timeout` record stay. |
| `services/extractor.py` | the `INT-003` comment above the executor dispatch | **Re-read and keep accurate** if the shape changes. |
| `docs/11-guides/configuration.md` | the `download_timeout` row | **MUST NOT BE TOUCHED.** Plan 07's `C12` owns it (`B11` then `B15` there). Coordinate; do not collide. |

**Tests required**

- **ADD** `tests/test_config.py` — an assertion that the field description carries the exit-path
  bound, if the choice is documentation-only. **If the fork resolves to a code change, the test is a
  behavioural one instead** and the block report states which it wrote and why.
- **MUST STAY GREEN UNCHANGED** — `tests/test_extractor.py::TestExtractionErrors::test_extract_with_ytdlp_no_info_raises_extraction_error`
  and the whole of `tests/test_config.py`.

**Dependencies:** `depends_on: []`.

**Risk class: MEDIUM (advisory), low code risk, HIGH cross-plan collision risk.**

**Prohibitions inherited (binding)**
1. **`CFG-002` is misattributed — do not act on it.** Phase 02's `CFG-002` is about the
   post-construction **`max_retries`** override, is already fixed by `ea44b3d`, and there is no
   override in `src/`. `B9` must not re-derive or re-reference it.
2. **The configuration guide's `download_timeout` row is plan 07's `C12`.** `B9` writes the
   **field description only** and its report must say so explicitly.
3. No new `src/` or `tests/` file.
4. The fix must **not** be "raise a `TimeoutError` earlier" or otherwise change what the operator is
   promised by `download_timeout`.

#### §3.5 Decisions `B9` explicitly does **not** make

**Whether a code remedy is justified at all, and if so which.** The finding is **`advisory`**, and
the interpreter's thread-join cap is an **interpreter constant** that no per-call-site option can
lower:

- (a) **Documentation only.** State the exit-path bound where the timeout is configured and stop.
  *Pro:* closes the finding's actual recommendation ("state the exit-path bound where the timeout is
  configured"); zero runtime risk; no new executor lifecycle; rule 5's answer. *Con:* the stall
  itself remains, up to the cap.
- (b) **A dedicated executor for this call site**, shut down with `wait=False` so the abandoned
  thread is not joined by `loop.shutdown_default_executor`. *Pro:* actually removes the stall's
  cap. *Con:* a new executor lifecycle per extraction (create/destroy), a real behaviour change to
  thread accounting, and it grows `_extract_with_ytdlp`'s responsibility.
- (c) **A shared long-lived executor for off-loop extractions.** *Pro:* one executor, amortised.
  *Con:* a module-level resource with a teardown obligation, in a module that currently owns none —
  rules 3 and 4 push against it.

→ **Deferred to `B9`'s Researcher** (the modern idiom for bounding an abandoned `run_in_executor`
job) and the block's **Planner** for the selection. **Rule 5 makes (a) the default**, and a `B9`
Planner who selects (a) **must state in the report that the finding's recommendation was met by
documentation and that the residual stall is accepted**, with the cap named. Selecting (b)/(c)
requires a written justification that the advisory's operator-visible gap justifies the change.

---

### B10 — Record `CON-002`'s verification outcome without touching code or severity

**Findings carried:** `CON-002` — severity cell reads **`*none — not executed*`** (out of enum, by
design) · `SPEC-DEVIATION` · **mandatory**.

**Goal.** Establish and record what is and is not known about D-01's production condition, so the
registered CRITICAL claim is not read as confirmed against this code — **without** changing product
code, **without** deleting the finding, and **without** giving it a severity.

**What is actually left, precisely.** Three things were checked before deciding not to remove it:
(a) it **may not be deleted** — the owning phase's binding rule W-4 requires the claim subject to be
filed as *exactly two* findings, and states "The two are never merged and never omitted; under
`problems-only`, omitting either reads as 'no finding'"; (b) its **structural fact is true** and
re-derived from source — `perform_download` takes the per-video permit exactly once around the whole
ladder, the segment layer builds its own `asyncio.Semaphore(settings.max_concurrent_downloads)`, and
the outer object crosses the boundary only as the boolean `is_bounded_batch`; the registered D-01
nested-claim shape therefore **does not reproduce**; (c) it is **not a well-formed finding**, and
this phase cannot make it one — the out-of-enum cell cannot be corrected in place, because the only
admissible substitute is `LOW`, which **is** an observed severity and which
`99-audit-validate.md` `## 8` forbids ("never with an observed severity").

**Semantic anchors owned**

| File | Semantic unit | Change |
|---|---|---|
| `.ai/plans/done/01-confirmed-code-defects_DONE.md` | D-01's summary entry and its section, and its **Fix, Option A** | **Read-only.** The block **cites** it as the authority for *what actually shipped*. This is the key fact `CON-002`'s recommendation got half right: the nested-claim shape is absent because **Option A was implemented**, not merely because the condition was never exercised. |
| `src/vkdownloader/services/downloader.py` | `perform_download` — the single per-video permit, taken once around the whole ladder, and `_semaphore_context` | **Read-only.** Re-derive the structural fact against the live code with **semantic** anchors, and record it. |
| `src/vkdownloader/services/segment_downloader.py` | `_run_download_session` — the segment-local `asyncio.Semaphore`, and the `is_bounded_batch` boolean it carries and consumes | **Read-only.** Same. |
| `src/vkdownloader/config.py` | `Settings.max_concurrent_downloads`'s field description | **Read-only.** It already documents the per-layer sizing. **Verify** that and record whether it is accurate. |
| **A new verification record** under `.ai/audit/99-validation/` | `CON-002` verification — see the decision below | **The block's only write.** Prose only. |

**The write surface — decision, stated once.** The finding **may not be deleted**, its severity cell
**may not be corrected**, and the source report is **read-only** for this plan. So the durable record
must go somewhere writable that is neither the source report nor the validated artifact. **Decision:
a new prose file under `.ai/audit/99-validation/`, named so that it cannot be mistaken for a
validation artifact** — the `-validated-findings.md` suffix is the pipeline's artifact convention and
this file must not wear it. **It does not touch `EXPECTED_SDIST_ENTRIES`**, because that frozenset
covers `src/` and `tests/` only.
*Alternatives considered and rejected:* (i) record it only in the block report — not durable, not
auditable, and the finding would look resolved with no evidence; (ii) edit
`.ai/problems/PROBLEM.md` — that file is in the uncommitted dirty set and the register it names does
not exist at the cited path (`VAL-410`); (iii) edit the source report — **read-only for this plan**.

**The record must state, in this order:**
1. The structural fact, re-derived against the live code with **semantic** anchors (no line numbers).
2. That the **production condition** — batch mode, videos in flight ≥ the ceiling, and at least one
   video taking the segment path — was **NOT executed** against a live origin, and why (no network
   access in this engagement; §5.8's boundary). **No inference about what a real origin would do.**
3. That the **primitive-identity comparison is not proof** of the condition's behaviour — the
   validator was explicit, and the block must not quietly close the finding on it.
4. That **D-01 was fixed** (its Fix, Option A), which **retires** the "execute the production
   condition" half of `CON-002`'s recommendation and leaves only the register-wording half.
5. That the register's own **Location** list is stale, that correcting it is **phase 09's** subject by
   R-E, and that `phase04/VAL-410`'s path correction is **not claimed by this plan** (§1.4).
6. That `CON-002` **remains filed, remains `UNVERIFIED`, and carries no severity** — and that
   `B11` is what gives that state a legal encoding.

**Tests required:** none. There is no test that can see a `.md` file. **The Validator's read is the
gate**, plus `git diff --exit-code` proving no `src/`, `tests/`, `docs/` or `.ai/audit/*/findings.md`
changed.

**Dependencies:** `depends_on: []`.

**Risk class: LOW (code) / MEDIUM (process).** The risk is an agent under gate pressure "fixing" a
finding whose whole content is *that it was not verified*.

**Prohibitions inherited (binding)**
1. **No code change.** Not one character of `src/`.
2. **No severity** is written, and `LOW` **in particular** is forbidden.
3. **The finding is not deleted, merged, reclassified, or given a severity.**
4. The primitive-identity observation **does not close it**.
5. **No claim about what a real VK origin or a real batch would do.**
6. `.ai/audit/04-concurrency-cancellation/findings.md` and the validated artifact are **byte-identical**
   before and after.

**Commit shape.** One prose commit, cited `CON-002` and `phase04/VAL-410` (as *not claimed*). The
body states the outcome and, explicitly, that no code changed and no severity was assigned.

---

### B11 — Give the report format a legal encoding for a not-executed finding

**Findings carried:** `phase04/VAL-404` — **MEDIUM** · `SPEC-DEVIATION` · **mandatory**.

**Goal.** `.ai/audit/templates/audit-findings.md` must be able to express a finding whose runtime
consequence was not observed, so a W-4-compliant report is not illegal by construction.

**Why claimed here.** This is the only `VAL-4xx` still open that is not an ordering constraint
(enforced in `B2`/`B4`/`B5`), not already fixed (`VAL-405`…`VAL-409`), and not blocked by a
read-only file (`VAL-410`, §1.4). Phase 04's own `CON-002` is the concrete live instance: the
validation **had** to leave an out-of-enum severity in place and file the format defect instead of
correcting it. Plan 07's `B3` set the precedent that an audit-fixes plan may edit a shared pipeline
document after claiming ownership explicitly. **Ownership is claimed here, and any future plan that
would have carried `phase04/VAL-404` must be struck.**

**The defect.** The format fixes `severity ∈ CRITICAL, HIGH, MEDIUM, LOW` and offers exactly four
`type` labels. Three documents mandate an encoding the format cannot express: the phase handbook
requires "an explicit `UNVERIFIED` marker, never with an observed severity" and its binding rule
W-4 goes further — "**The production trigger** carries `UNVERIFIED` and **no severity**"; the
validation task says the same at `## 8` and `## 12`. None of the four type labels admits an
unverified observation (`SPEC-DEVIATION` requires a contradicted declared rule, `RUNTIME-ERROR` an
observed failure, `BEST-PRACTICE` a demonstrated risk), the phase closes with "This phase files no
`DOC-UPDATE`", and `## 8` forbids adding a fifth label. **A conforming report must write something
the enum forbids.**

**Semantic anchors owned**

| File | Semantic unit | Change |
|---|---|---|
| `.ai/audit/templates/audit-findings.md` | the `Template Field Reference` row `| severity | enum | CRITICAL, HIGH, MEDIUM, LOW |` | Add the encoding the pipeline documents mandate, **or** state the substitute rule (see §3.6). |
| `.ai/audit/templates/audit-findings.md` | the `Template Field Reference` row `| type | enum | SPEC-DEVIATION, BEST-PRACTICE, DOC-UPDATE, RUNTIME-ERROR |` | Same question, for the type label. |
| `.ai/audit/templates/audit-findings.md` | the finding-block shape and its `Decision:` line | Only if the chosen encoding needs a marker field. |
| `.kilo/commands/audit/phases/04-audit-concurrency-cancellation.md` | the `UNVERIFIED` requirement and binding rule W-4 | Reconcile the handbook's mandate with whatever the format now permits, so the two agree. |
| `.kilo/commands/audit/phases/99-audit-validate.md` | `## 8` and `## 12` | Same reconciliation. |
| `.ai/audit/04-concurrency-cancellation/findings.md` | `CON-002`'s field table | **MUST NOT BE TOUCHED.** Its out-of-enum cell is the *evidence* for this finding. Editing it would destroy the instance and retro-fit the format to the answer. |
| `.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` | — | **MUST NOT BE TOUCHED.** The change is **prospective**. |

**Tests required:** none. Prose. **The Validator's read is the gate**, plus a `git diff --exit-code`
on the two read-only paths above.

**Dependencies:** `depends_on: []`. **`B10` references `B11` as what gives `CON-002`'s state a legal
encoding, but does not require it** — `B10`'s record is accurate whether or not `B11` has landed.

**Risk class: MEDIUM (process).** These are three **shared** pipeline documents that govern phases
`01`–`11` and every future phase. The risk is not the edit; it is an agent over-reaching into
`.kilo/rules/` or "fixing" a role file while in there.

**Prohibitions inherited (binding)**
1. **No change to `.kilo/rules/project.md`** — the `structlog` divergence is flagged, not fixed (§5.6).
2. **No change to `.kilo/agents/*`** — `VAL-409` is already fixed by `e443448`; there is nothing here.
3. **No change to `.ai/audit/04-concurrency-cancellation/findings.md` or to the validated artifact.**
4. **No retroactive rewriting of any existing finding's severity or type**, including `CON-002`'s.
5. The change is **prospective**: it governs future reports.

#### §3.6 Decisions `B11` explicitly does **not** make

**Which of the artifact's two remedies is taken.** The artifact offers both, deliberately:

- (a) **Add a fifth severity member `UNVERIFIED`** — "the structural fact is recorded; the runtime
  consequence was not observed" — **and** a fifth type label with the same meaning.
  *Pro:* one mechanism, self-describing, matches what the three pipeline documents already demand, so
  the handbook and the validation task need **no** semantic change (only reconciliation). *Con:* adds
  a severity that is **not** a severity — every place that ranks or counts severities must learn to
  handle it, including the finding Summary table's severity rows; and it interacts with
  `99-audit-validate.md`'s counting.
- (b) **State that `UNVERIFIED` findings are filed as `LOW` / `BEST-PRACTICE` with a mandatory marker
  field.** *Pro:* no enum change; the existing severity and type machinery is untouched; the marker
  carries the real information. *Con:* **the filing then carries an observed severity it did not
  earn** — which is precisely what `99-audit-validate.md` `## 8` forbids ("never with an observed
  severity") — so (b) requires that document to be amended too, or the contradiction is preserved in
  a new place.

→ **Deferred to `B11`'s Researcher** (how audit pipelines in general encode a not-executed
observation) and the block's **Planner** for the selection. **The artifact states both are
acceptable; the plan does not pre-select**, because (a) and (b) have materially different blast radii
across the whole pipeline and the choice is a contract decision rather than an implementation detail.

---

## §4 Dependency graph and execution order

### §4.1 The graph

```
                ┌───────────────────────────────────────────────────────┐
                │  WAVE 0 — no dependencies (8 blocks)                   │
                │                                                       │
    B1  CON-001 leg 1 ──────────────────────────┐                     │
    B2  CON-006/007/008 (VAL-402) ──┬─────────┼─────────────────►     │
    B3  CON-001 leg 3 ──────────────┼─────────┼───────────►           │
    B4  CON-004/005   (VAL-401)      │         │                       │
    B8  CON-009                      │         │                       │
    B9  CON-010                      │         │                       │
    B10 CON-002                      │         │                       │
    B11 VAL-404                      │         │                       │
                └─────────────────────┼─────────┼───────────────────────┘
                                      │         │
                ┌─────────────────────┴─────────┴───────────────────────┐
                │  WAVE 1 (2 blocks)                                   │
                │  B6  CON-003 segment  ← B2   (C1)                   │
                │  B7  CON-003 batch    ← B2   (C6)                   │
                └──────────────────────────────────────────────────────┘
                                      │
                ┌─────────────────────┴──────────────────────────────┐
                │  WAVE 2 (1 block)                                   │
                │  B5  CON-001 leg 2 (VAL-403)  ← B1, B2, B3          │
                └─────────────────────────────────────────────────────┘
```

**Formal edges (11 blocks, 5 edges):**

| From | To | Conflict | Why |
|---|---|---|---|
| B2 | B6 | `C1` | `_create_segment_download_tasks`'s **return type** is `B6`'s subject and is the argument to `_process_downloaded_segments`, whose contract `B2` rewrites. A bounded producer changes what the consumer receives; reviewing `B6` against the pre-`B2` consumer would be reviewing the wrong contract. |
| B2 | B7 | `C6` | `B7`'s producer rewrite must **preserve** the `except asyncio.CancelledError` fan-out branch that `B2` **activates**. Reviewing `B7` against the dead branch is reviewing the wrong behaviour. |
| B1 | B5 | `C2` | The escalation's value presupposes the stop is observable and the drain returns (`B1`). Without it, a second interrupt escalates against a still-blocked read. |
| B2 | B5 | `C3` | **`phase04/VAL-403`.** The forward route's cancellation vanishes at `_await_and_cancel` until `B2` makes it propagate; otherwise the escalation yields exit `1` and a false failure list. A severity dependency. |
| B3 | B5 | `C4` | The forward route consumes the **captured previous handler** that `B3` introduces. Routes (b)/(c) do not need it, but the edge is **retained anyway** as a safety ordering rather than dropped. |

**Acyclicity proof.** Assign ranks: `rank(B1) = rank(B2) = rank(B3) = rank(B4) = rank(B8) =
rank(B9) = rank(B10) = rank(B11) = 1`; `rank(B6) = rank(B7) = 2`; `rank(B5) = 3`. For every edge
`u → v` in the table above: `(B2, B6)` gives `1 < 2`; `(B2, B7)` gives `1 < 2`; `(B1, B5)` gives
`1 < 3`; `(B2, B5)` gives `1 < 3`; `(B3, B5)` gives `1 < 3`. **Every edge strictly increases the
rank**, so no cycle can exist: a cycle would require a non-increasing step around the loop, and there
is none. The six isolated blocks (`B4`, `B8`, `B9`, `B10`, `B11`, and `B1`/`B3` beyond their edges)
are singleton vertices. **The graph is a DAG.** Formally: a topological order is
`B1, B2, B3, B4, B8, B9, B10, B11, B6, B7, B5`, and any ordering consistent with the rank
assignment is valid.

### §4.2 The linearised order, and the reason for each position

Eight blocks are unconstrained; three are constrained. The order below is the **recommended
sequence**, not a dependency chain. Execution is **sequential with one Implementor at a time**
(maximum 2 parallel subagents, and in practice the blocks are not independent enough to parallelise
safely — see §5.5).

| # | Block | Why here |
|---|---|---|
| 1 | **B1** `CON-001` leg 1 | The CRITICAL hang fix, in a **leaf** module, in **one** function, with **no** dependencies and the **fewest** tests to re-scope. Nothing may be ahead of it: everything downstream assumes the child can be reached. |
| 2 | **B2** `CON-006/007/008` | Unblocks **three** blocks (`B5`, `B6`, `B7`) and is `phase04/VAL-403`'s prerequisite. Second because it is the highest-leverage unconstrained item, and because `phase04/VAL-402` makes it a single indivisible change — best done while the tree is quiet. |
| 3 | **B4** `CON-004/005` | Self-contained `phase04/VAL-401` group, one 20-line block, one confirmed test pin. Third because it is the other HIGH group with a test edit, and it touches a module nothing else in this plan edits. |
| 4 | **B3** `CON-001` leg 3 | Unblocks `B5` via `C4` and is the smallest of the three `CON-001` legs. Fourth — after the two highest-severity product fixes are committed, so its diff is reviewed against a known baseline. |
| 5 | **B6** `CON-003` segment | Wave 1. **Researcher-blocked** (bounded-production idiom) — start the research at position 1 if capacity allows, because it has the longest lead time. Its implementation waits on `C1`. |
| 6 | **B7** `CON-003` batch | Wave 1. Shares `B6`'s Researcher deliverable (same idiom, two layers), and waits on `C6`. |
| 7 | **B8** `CON-009` | **Researcher-blocked** (remedy shape). Advisory — placed after both HIGH groups so the plan's irreversible and test-pinned work is committed first. |
| 8 | **B9** `CON-010` | **Researcher-blocked**, advisory, and the only block with a cross-plan documentation collision (plan 07's `C12`). Placed where a coordination conversation can happen before the commit. |
| 9 | **B10** `CON-002` | Prose, zero code risk. Placed after `B8`/`B9` because its record should reflect the *final* state of the concurrency picture those blocks changed. |
| 10 | **B11** `phase04/VAL-404` | Prose, zero product risk, but three **shared** pipeline documents. Placed late so its blast radius is reviewed against a fully-settled plan, and so `B10`'s record can reference it accurately. |
| 11 | **B5** `CON-001` leg 2 | Wave 2, last. **`phase04/VAL-403`**: shipping the escalation before `B2` is the one ordering that makes a shipped defect worse than the one it repairs. It also depends on `B1` and `B3`, and is the block with the largest open design fork. **It may be dropped entirely if capacity is short — it is the only block in the plan whose absence leaves the shipped product no worse than it is today.** |

### §4.3 Conflict matrix — every pair sharing a semantic anchor

`C1`–`C6`. **Semantic names are the key; line numbers are only historical locators and are
deliberately absent.**

| # | Findings · blocks | **Shared semantic anchor** (semantic key) | Nature | Resolution |
|---|---|---|---|---|
| **C1** *(new)* | `CON-003`-segment ↔ `CON-006/007/008` · **B6 ← B2** | The function `_create_segment_download_tasks` and the value it hands to `_process_downloaded_segments` → `_await_and_cancel` | **Signature + contract.** `B6` changes what the factory produces; `B2` changes what the consumer accepts. Both cannot be reviewed against the other's pre-change form. | **Edge: `B2` first.** `depends_on: [B2]`. `B6`'s report must state how its output reaches `B2`'s outcome type. |
| **C2** *(new)* | `CON-001` leg 1 ↔ `CON-001` leg 2 · **B1 → B5** | `iter_process_lines`'s in-flight stop observation; the drain→`process.wait()` race in `_download_with_ytdlp` and `perform_download` | **Prerequisite.** The escalation presupposes the stop is observable at all. | **Edge: `B1` first.** `B1` is unconstrained and lands first regardless. |
| **C3** | `CON-001` leg 2 ↔ `CON-008` · **B5 ← B2** | The cancellation path: `_await_and_cancel`'s absorption, `_classify_download_result`'s stop-state read, `_run_batch_with_progress`'s fan-out, the summary's `130` return | **Severity dependency**, filed as `phase04/VAL-403`. | **Edge: `B2` first.** `B5`'s `depends_on` includes `B2`, and `B5`'s report re-verifies the chain against the **landed** code. |
| **C4** *(new)* | `CON-001` leg 3 ↔ `CON-001` leg 2 · **B3 → B5** | The module-level captured previous-handler state in `signal_handlers.py` | **Data dependency.** The forward route reads what `B3` writes. | **Edge: `B3` first.** Retained even if the Planner selects the force-kill route, as a safety ordering. |
| **C5** | `CON-004` ↔ `CON-005` · **B4, B4** | One `try`/`except`/`finally` chain in `BrowserManager.__aexit__` — the guard at its head, the two `except TimeoutError` arms, the `finally` | **Same statement group.** `CON-004` deletes the guard; `CON-005` widens the arms. Neither names the other. Filed as `phase04/VAL-401`. | **Resolved *within* `B4`, not by ordering.** Suppression first, then the unconditional release. No cross-block edge. |
| **C6** *(new)* | `CON-003`-batch ↔ `CON-008` · **B7 ← B2** | The `for coro in asyncio.as_completed(tasks)` loop's `except asyncio.CancelledError` fan-out branch in `_run_batch_with_progress` | **Prohibition + review obligation.** `B2` makes the cancellation reach that branch; `B7` rewrites the producer that feeds it. | **Edge: `B2` first**, plus a binding prohibition: `B7` must not remove or restructure the fan-out branch. |
| **C7** *(new)* | `CON-009` ↔ plan 07 `B14` · **B8** | `_create_connector`'s `TCPConnector(limit=10)` and the per-download connector/session pairing | **Cross-plan ownership handover.** Plan 07's `B14` carried a *prohibition*; this plan releases it. | **No ordering edge** (plan 07's blocks are landed). `B8`'s report states the handover and carries the arithmetic. |
| **C8** *(new)* | `CON-010` ↔ plan 07 `B11`/`B15` · **B9** | `Settings.download_timeout`'s `Field(description=...)` **and** the `download_timeout` row of `docs/11-guides/configuration.md` | **Cross-plan, statement-level.** Plan 07 owns the row under its `C12`; the field description is shared surface. | **Prohibition: `B9` writes the field description only** and must not touch the guide's row. `B9`'s report says so. |
| **C9** *(new)* | `CON-001` ↔ `ENT-004`/`ENT-012` · **B1, B3, B5** | Signal-handler **registration placement** (`cli.py` vs `batch_downloader.py`); correlation-id state | **Cross-phase, dead references.** `ENT-004` is plan 05's deferred `D7`; `ENT-012` was fixed by `0790157`. | **No edge. Explicit prohibitions** on moving registration and on any correlation-id obligation. |

### §4.4 Every grouping changed from the artifact's own Fix Order, and why

**A note on the artifact's Fix Order, stated once so no block report mis-cites it.** The validated
artifact publishes **no numbered fix list**. Its ordering content is (i) the finding order,
`CON-001` … `CON-010`, followed by `VAL-401` … `VAL-410`, and (ii) **Checkpoint 4 — R4 Assess
Rollout Safety**, which records *circular dependencies: 0*, *unsafe-ordering pairs: 3*, *hidden
chains: 2*, and *blockers: none*. **The "Fix Order" compared against below is that order plus R4's
three pairs** — i.e. `CON-001` as one indivisible item, `CON-002` second, `CON-003` third, and so on.
This plan is built against R4's *constraints*, which it honours exactly (§4.3 `C3`, `C5`), and
against the finding order, which it does not follow.

| Artifact's Fix Order | This plan | Why it changed |
|---|---|---|
| `CON-001` as one item (three fixes) | **B1 + B3 + B5, split three ways** | The three fixes live in **different modules with different failure modes and different verification shapes**: a leaf-module drain race (`ffmpeg_utils.py`), process-level handler state after `asyncio.run` (`signal_handlers.py`), and an escalation that has a **hard ordering gate** (`phase04/VAL-403`). Splitting lets the CRITICAL hang fix land **today** with no dependencies, keeps the escalation last where its gate belongs, and makes each commit independently verifiable. Merging them would serialise the cheapest fix in the corpus behind the most uncertain one. |
| `CON-003` as one item (both layers) | **B6 + B7, split two ways** | Different modules, **no shared statement**, and a **shared Researcher deliverable** rather than a shared implementation. Splitting produces two independently verifiable commits; keeping them together would produce one commit whose review surface spans the batch lifecycle, the reporter, the signal setup/cleanup and the segment factory. |
| `CON-002` as the second item | **B10, tenth** | It has **no code change**, so position is free. It goes late so its verification record reflects the final concurrency picture. Its *content* obligations are unchanged and are stated at the block. |
| `VAL-401`, `VAL-402`, `VAL-403` as findings | **Enforced, not blocked** | A block whose entire content is "order `B4` before `B4`" is theatre. Each is instead enforced as: an in-block single commit + a negative acceptance criterion (`VAL-401`, `VAL-402`), or a `depends_on` edge (`VAL-403`). All three remain traceable via the conflict matrix. |
| `VAL-405`…`VAL-409` as findings | **No blocks** | Already fixed by `d62671b`, `19143b1`, `8366964`, `e443448`. |
| `VAL-404` as a finding | **B11, claimed** | §3 `B11`. The only open `VAL-4xx` that is neither an ordering constraint, nor fixed, nor read-only-blocked. |
| `VAL-410` as a finding | **Not claimed** | Its primary target is read-only for this plan and its second half is `09`'s subject by R-E. §1.4 records the owner and the trigger. |
| The ten findings in ID order | **The order in §4.2** | The reordering is driven by the five edges in §4.1 and by risk: irreversible/high first, advisory last, the gated escalation last of all. |

---

## §5 Risks

### §5.1 The test-pinning risk

Project rule 2: *if tests conflict with architecture or business logic, fix or remove the tests;
never distort production code for tests.* One test group in this plan **asserts the defective
behaviour**; two more are **exact near-misses** that must be verified rather than assumed; and four
are the **regression net** for the riskiest remedy in the plan.

| Block | Test | What it pins | Disposition |
|---|---|---|---|
| **B4** | `tests/test_browser_infrastructure.py::TestBrowserManager::test_browser_manager_context_exit_stops_playwright_on_browser_close_error` | **Confirmed pin.** The `pytest.raises(RuntimeError, match="close failed")` **and its comment** encode `CON-005`'s defect. | **Re-scoped, not deleted, not weakened.** Must keep asserting `playwright.stop()` ran (the `finally` guarantee is real and `CON-005`'s remedy preserves it) and must add the new contract. |
| **B2** | `tests/test_hls_downloader.py::TestDownloadHlsWithResume::test_preserves_segments_on_segment_download_failure` | **Near-miss.** Asserts `result is None` — but on the **failed-transfer** path (`_await_and_merge` runs, the not-all-succeeded arm fires), not the **nothing-to-do** path. | **Verify by running it. Do not assume.** If it stays green, say so in the report; if not, re-scope it with the reason. Never edit it speculatively. |
| **B2** | `tests/test_batch_downloader.py::TestBatchCancellationReporting::test_uninterrupted_failed_download_is_still_a_failure` | **Live-semantics constraint.** An un-cancelled `None` must remain `FAILED` with exit `1`. | **Must stay green unchanged.** This is what `CON-008`'s fix must not break. |
| **B1** | `tests/test_hls_downloader.py::TestIterProcessLines::test_invokes_on_shutdown_callback` | Asserts the callback fires **exactly once** — a genuine invariant a race-based fix could break. | **Preserve and extend.** All four existing cases stay green unchanged. |
| **B6**, **B7** | `TestBatchDownloaderSemaphore::test_batch_completes_without_deadlock_when_max_reached` and `::test_segment_layer_does_not_acquire_caller_video_semaphore` | Assert `peak <= max_concurrent_downloads` and that the segment layer does not re-acquire the caller's video semaphore. They assert **peak**, never **live task count**, so a bounded-producer remedy leaves them green. | **Must stay green unchanged — no edits at all.** They are the regression net for `D-01` and for the deadlock failure mode. |
| **B5** | `tests/test_batch_downloader.py::TestBatchCancellationReporting` (both halves) and the documented `130` in `docs/99-reference/cli-reference.md` | The documented exit code for an interrupted run. | **Must stay green unchanged.** |

The failure mode this risk creates is uniform: an agent under gate pressure **weakens an assertion
rather than fixes the code**. Every block's Validator is briefed on it, and re-scoped tests must
assert the **new** contract, not a weaker one.

### §5.2 The prohibitions that survive a fix — the plan's biggest hazard

Four things the code says or the validator narrowed, which a fix must not quietly undo.

1. **The yt-dlp "no application-level download timeout" decision.** `_download_with_ytdlp`'s
   docstring states that no application-level download timeout is imposed, avoiding premature kill
   of legitimate long downloads. Wrapping `process.wait()` — the single most natural-looking place
   to add a budget — re-introduces exactly that. **`B1` and `B5` must not add a timeout to any
   transfer stage**, and the decision comment must be byte-identical after `B1`.
2. **`D-01`'s non-reentrant-semaphore invariant.** `asyncio.Semaphore` is not reentrant; the batch
   permit is acquired **once per video**. This is *why* `CON-003`'s remedy is **not** "gate the
   segment fan-out on the batch semaphore". **`B6` and `B7` must keep the comment accurate.**
3. **The `INT-004` browser-exit ownership comment** currently **lies** (it says the exit checks the
   stop state before each step; the code guards only the first). **`B4` corrects it** — it is not
   optional tidying, it is the block's own documentation drift.
4. **`read_progress`'s `shutdown_event` parameter.** Deliberate, because `ffmpeg_utils.py` is a
   leaf. **No block may convert it to a module lookup**, and none may add a `downloader_throttle`
   import to `ffmpeg_utils.py`.

### §5.3 Implementation risks

| Risk | Blocks | Containment |
|---|---|---|
| **`B1`'s partial fix is worse than nothing** — the drain returns but the child is never killed, or the callback double-fires. | B1 | The exactly-once assertion is extended; the AC requires a *measurable* before/after (reader returns within N s of the stop). |
| **`B2`'s outcome shape collides with `B6`/`B7`'s producer output.** | B2, B6, B7 | `C1` and `C6` edges; each block's report states the other half of the contract in semantic terms. |
| **`B3` restores the wrong handler** — over-correcting to `SIG_DFL` for SIGINT. | B3 | The two signals are asserted **separately** in the new test; the commit body records the measured pre-install values. |
| **`B4`'s suppression swallows a real teardown failure** when no exception is in flight. | B4 | §3.2's fork is unresolved by design; the report must state the choice and the rejected option. |
| **`B5` runs blocking work in the signal context** (Windows: handlers run between bytecodes on the main thread). | B5 | Binding criterion; schedule onto the loop instead. |
| **`B6`/`B7`'s bounded producer **drops work** or **deadlocks** — the two obvious failure modes. | B6, B7 | A test asserting **every** item is still attempted and still reaches the summary; the four peak/non-reentrancy tests must stay green unchanged. |
| **`B8` becomes a redesign.** A process-wide pool for an **advisory** finding. | B8 | Rule 5; option (c) is out of scope by default; §3.4's alternatives and trade-offs are in the block. |
| **`B9` collides with plan 07's `C12` on the `download_timeout` row.** | B9 | Binding prohibition: field description only; the report says so. |
| **`B10` "fixes" an unverified finding.** | B10 | Binding prohibition: no code, no severity, no deletion; the report proves `src/` is unchanged with `git diff --exit-code`. |
| **`B11` over-reaches** into `.kilo/rules/` or a role file while editing three shared pipeline documents. | B11 | Four binding prohibitions; the Validator's read is the gate. |
| **A test-pinned assertion is weakened instead of the code fixed.** | B4 (and the near-misses in B2) | §5.1. |
| **A structlog / stdlib-`logging` slip.** | all | §5.6. |
| **A new constant as a literal or a dict instead of a `StrEnum` member.** | B2, B5, and any block adding a constant | Rule 10; the reviewer's first question on any new value. |
| **A stop-state `Event` leaked between tests** via a test that sets `_shutdown_event_ctx` without resetting its token. | B1, B2, B3, B5 | §2.3's token-idiom requirement. |

### §5.4 Rollout risks

| Risk | Detail |
|---|---|
| **The dirty working tree is absorbed into a phase-04 commit.** | §2.4's landing rule. This is the plan's largest **process** risk, and the only one that can contaminate every block at once. |
| **The `VAL-` namespace.** An unqualified `VAL-401` makes a reader validate the wrong documents. Plan 06 already documents the collision. | Mitigated by the convention at the top of this plan, which is a **naming decision taken before any block is written**, not a review step. |
| **`phase04/VAL-403` violated for convenience** — landing `B5` early because it "looks like part of `CON-001`". | The dependency is structural (`depends_on: [B1, B2, B3]`) and the artifact's tiebreaker is explicit: shipping the escalation first "is the one ordering that makes a shipped defect worse than the one it repairs". |
| **A wrong concurrency figure shipped in `B8`'s commit body.** | `C7` + `B8`'s binding arithmetic; the corrected figure is already in the validated artifact and phase 03's `VAL-001` adjudication. |
| **A withdrawn claim reintroduced in prose.** The source report `.ai/audit/04-concurrency-cancellation/findings.md` still contains every withdrawn and severity-corrected sub-claim. | **Every block cites the validated artifact only.** A block report that implements a withdrawn recommendation is wrong on its face. |
| **A block editing a file another phase owns.** | `B8` ↔ plan 07 `B14` (`_create_connector`, released here); `B9` ↔ plan 07 `B11`/`B15` (the guide's `download_timeout` row); `B10` ↔ `.ai/audit/04-concurrency-cancellation/findings.md` (read-only); `B11` ↔ `.kilo/rules/` and `.kilo/agents/` (forbidden); `B3`/`B5` ↔ plan 05 `D7` (`ENT-004` placement). Each is a **stated boundary with a negative acceptance criterion**, not a preference. |

### §5.5 Compatibility risks

| Risk | Detail |
|---|---|
| **`iter_process_lines`'s signature and semantics change** (`B1`). | It is re-exported through `downloader.py`'s facade and has seven test references. The signature must be **unchanged**; only the *termination* semantics tighten. The facade's 20 re-exports are untouched by every block in this plan. |
| **`_await_and_cancel`'s return contract changes** (`B2`). | Module-private with **one** consumer. The change is source-compatible inside the package, but it is the single point of `phase04/VAL-402`'s fragility — hence the type-level encoding requirement. |
| **Cancellation now propagates where it used to be absorbed** (`B2`, then `B5`). | Behavioural, and **correct**. A cancelled item reaches `_download_single`'s `except asyncio.CancelledError` and re-raises; the batch's fan-out fires; the summary returns `130`. This is the **documented** contract, so the change is a restoration, not a break — but any code that relied on a cancelled download returning `None` is affected, and there is exactly one such site (`_process_downloaded_segments`). |
| **A new `Settings` field** (`B8`, option (b) only). | Backward-compatible: a new bounded field with a default changes no existing setting's meaning. `extra="forbid"` means an unrecognised `VKDOWNLOADER_` variable is an error, so the new variable must be in `.env.example` **and** the configuration guide or operators get `extra_forbidden` on upgrade. |
| **`limit_per_host` becomes a real ceiling** (`B8`). | Today it is `0` (unbounded) at every value of every setting. Setting it explicitly **reduces** the achievable per-origin concurrency. That is the finding's point, but it is a behavioural change on the hot path — the report must state the new ceiling's derivation and its value at the setting's floor and ceiling. |
| **The browser close now runs on the stop path** (`B4`). | On an interrupted browser-backed extraction, `browser.close()` executes where it previously did not. That is the intended fix, and the 10 s `wait_for` bound is what keeps it short — the block must not remove or lengthen the bound. |
| **`B3` changes process-global signal state.** | After the fix, a handler this project displaced is put back. That is strictly less intrusive than today. The risk is restoring the **wrong** value, which §5.3 contains. |
| **`B10` and `B11` change no product behaviour at all.** | Recorded so a reader does not mistake their absence from the code-diff summary for an omission. |

### §5.6 The `structlog` trap — a doc-vs-code divergence flagged, not fixed

`.kilo/rules/project.md` rule 12 literally prescribes `logger = logging.getLogger(__name__)`. The
**codebase universally uses `structlog`**: every module does `from structlog import get_logger` then
`logger = get_logger(__name__)`, and `config.setup_logging` wires `structlog.stdlib.LoggerFactory`
over `logging.basicConfig` with a `JSONRenderer`/`ConsoleRenderer` split. Two deliberate exceptions
exist and are not to be touched: `config.py`'s `import logging`, which configures the stdlib handler
structlog wraps, and `progress_display.py`'s re-pointing of that handler's stream.

**Decision, identical to plan 07's and binding here: follow the code, not the rule text, and do not
"fix" the rule file as part of phase 04.** Changing `.kilo/rules/project.md` is an audit-pipeline
change, not a product change. **Binding on `B11`**, which edits `.kilo/commands/audit/phases/*` and
must not reach `.kilo/rules/`. A new module, or any new `import logging` in a service, would break
the renderer split for the whole process.

### §5.7 Documentation risks

| Risk | Detail |
|---|---|
| **A behaviour change leaves its justifying comment lying.** | `B4`'s `INT-004` ownership note currently **lies** about the exit checking the stop state before each step; correcting it is part of the block. `B6`/`B7` must keep `D-01`'s non-reentrancy statement accurate. `B1` must keep yt-dlp's "no application-level download timeout" decision byte-identical. `B3` must keep `signal_handlers`' docstrings accurate about what cleanup restores. |
| **The configuration guide drifts from the model.** | `docs/11-guides/configuration.md`'s `download_timeout` row is owned by **plan 07's `C12`** and is the plan's only cross-plan documentation collision. `B9` writes `config.py`'s **field description** and says so. If `B8` adds a setting, the three-place rule applies to **both** the new field and the amended `max_concurrent_downloads` description. |
| **A block writes a new setting into `.env.example` with an illegal value.** | Phase 02 found a shipped `.env.example` value the model rejects. **Any value `B8` adds must be constructed against `Settings` and the construction recorded in the block report.** |
| **The source report is mistaken for the validated artifact.** | `.ai/audit/04-concurrency-cancellation/findings.md` still contains **every** withdrawn and severity-corrected sub-claim — `CON-004`'s permanent leak, `CON-007`'s "told the download finished", the R5(iii) leg, `CON-002`'s out-of-enum cell. **Every block cites the validated artifact only.** A block report that implements one of the withdrawn recommendations is wrong on its face. |
| **Documentation noise for self-evident changes.** | `B10` and `B11` are documentation blocks and need no doc edit — their edit **is** documentation and is the whole finding. No block adds a new doc page. |

### §5.8 The boundary no block may cross

**No finding in this corpus asserts what a real VK origin does.** Every live claim is structural: a
measured task count, a measured handler identity, a read of a return annotation, a control-flow
argument, an interpreter constant. The artifact that produced this plan had no network access.

**Therefore, binding on every block and every verification step:**

1. **No block may be justified by** "a real VK origin would 403 the part", "a real CDN would serve
   `*.m3u8` from this host", "a real Chromium would hang on `browser.close()`", or any equivalent.
   Those are the assumptions the audit explicitly declined to make.
2. **No verification step may require network access.** `tests/test_packaging.py` is the only test
   that may touch the network and it skips off-CI. This plan adds none.
3. **Every new test uses a local stub, a `MagicMock`, or a stand-in.** There is no `aiohttp` fixture,
   no ffmpeg-subprocess fixture and no fake clock; none may be added for these blocks. The suite's
   zero-`aiohttp` property is a fact about the codebase, not a gap to close here.
4. **`B10`'s verification record must not contain a verdict on the unexecuted condition.** It records
   what is not known. Writing "the condition is safe" or "the condition is broken" is exactly the
   over-claim the validator warned against.
5. **`B1`'s and `B5`'s subprocess behaviour is verified against real children only where the artifact
   did** (a silent child, a child that emits one line); anything beyond that is a stand-in.

---

## §6 Agent usage per block

**Which of Auditor / Researcher / Planner / Validator each block requires, and why.** The rule applied:
risk and **real uncertainty** buy agents; a mechanical change with a determined remedy needs none.
Low-risk mechanical work is **Implementor only**.

| Block | Auditor | Researcher | Planner | Validator | Risk | The question that earns each agent |
|---|---|---|---|---|---|---|
| **B1** | — | — | **YES** | **YES** | HIGH | *Planner:* the exact race shape inside a leaf async generator, and how `on_shutdown` stays exactly-once across the between-lines and in-flight paths. *Validator:* after the change, does a stop during a real blocked read actually reach `cancel_subprocess`, and is the exactly-once guarantee still true? **Not an Auditor block:** the file is byte-identical to `HEAD`, both the artifact and the code context re-derived the defect, and there is nothing left to re-derive. |
| **B2** | — | — | **YES** | **YES** | MEDIUM-HIGH | *Planner:* **the sentinel shape** — four viable options in §3.1, and the plan deliberately does not choose. *Validator:* a return-contract change with a live `None`/`FAILED` invariant and a documented exit code; the failure mode is a silent reopen of `CON-006`. |
| **B3** | **YES** | — | **YES** | **YES** | MEDIUM-HIGH | *Auditor:* **re-derive the process-level signal interaction** — which branch actually runs on `ProactorEventLoop`, what each signal's pre-install value is, and what `Runner.run()` does with it on the way out. *Planner:* where the captured previous handlers live and how cleanup reuses them on a second cycle. *Validator:* an independent read of the per-signal restore, since a "reset to default" over-correction is the obvious wrong turn. |
| **B4** | — | — | **YES** | **YES** | HIGH | *Planner:* **what escapes when a release step fails with no exception in flight** — §3.2's fork, which the artifact does not decide. *Validator:* a **confirmed test pin** is being re-scoped, and the re-scoped test must assert the **new** contract, not a weaker one; plus the suppressed-exception path is invisible to any other reader. |
| **B5** | **YES** | — | **YES** | **YES** | HIGH | *Auditor:* **the subprocess/signal interaction against the landed `B1`/`B3` code** — what a second interrupt can actually reach once the drain returns and the displaced handler is captured. *Planner:* the escalation route (§3.3) and, if the force-kill route is chosen, the registry's home. *Validator:* **mandatory** — `CON-001` is CRITICAL, this block interacts with `phase04/VAL-403`, and it is the one block whose wrong outcome makes a shipped defect worse than the one it repairs. |
| **B6** | — | **YES** | **YES** | **YES** | HIGH | *Researcher:* **bounded task-production idioms** in `asyncio` — worker pool vs bounded queue vs a semaphore-wrapped producer — and which preserves ordering, cancellation and per-item error reporting. *Planner:* the concrete shape and how its output reaches `B2`'s outcome type. *Validator:* the obvious failure mode is **dropped work or a deadlock**, and the four regression-net tests must stay green unchanged. |
| **B7** | — | **YES** *(shared with `B6`)* | **YES** | **YES** | HIGH | Same Researcher deliverable — one idiom question, two layers — so the research is not paid for twice. *Planner:* the concrete shape and its interaction with the reporter lifecycle and the `as_completed` fan-out. *Validator:* the summary's contents must be unchanged for every URL, and the fan-out branch must survive. |
| **B8** | — | **YES** | **YES** | **YES** | MEDIUM (advisory) | *Researcher:* **the transport-ceiling remedy shape** — three viable options with different architectural footprints (§3.4), including the operator-facing cost of a second setting. *Planner:* the selection under rule 5, and the arithmetic the commit body must carry. *Validator:* a setting change must construct against the model, satisfy the three-place rule, and the report's arithmetic must match the code. |
| **B9** | — | **YES** | **YES** | **YES** | MEDIUM (advisory) | *Researcher:* **the modern idiom for bounding an abandoned `run_in_executor` job** — whether a dedicated or shared executor is the accepted answer or whether documentation alone is. *Planner:* whether a code remedy is justified at all for an **advisory** finding (§3.5). *Validator:* a documentation-only block has no oracle, so the independent read is the gate — and the cross-plan `C12` boundary must be confirmed. |
| **B10** | — | — | **YES** | **YES** | LOW / MEDIUM (process) | *Planner:* the durable record's location and its six required statements are a judgement about audit provenance, not a copy. *Validator:* the gate is an **independent read** proving no code changed, no severity was assigned, and the finding was not quietly closed. |
| **B11** | — | **YES** | **YES** | **YES** | MEDIUM (process) | *Researcher:* **how audit pipelines generally encode a not-executed observation** — the two in-repo options have materially different blast radii across phases `01`–`11`. *Planner:* the selection and the reconciliation of three shared documents. *Validator:* **no oracle exists for prose that governs the pipeline itself**, and the risk is an over-reach into `.kilo/rules/` or `.kilo/agents/`. |

**Aggregate agent budget.** 11 blocks: **7 require a Planner** (every block with an open fork or a
contract change), **7 require a Validator** (every block whose failure is invisible to a passing test
run), **5 require a Researcher** (`B6`, `B7`, `B8`, `B9`, `B11`), **2 require an Auditor** (`B3`,
`B5` — the two blocks where the runtime interaction itself must be re-derived). **No block is
Implementor-only**, because every block carries at least one negative acceptance criterion that only
an independent read can confirm. The **cheapest** block in the plan is `B3`: one function, one module,
one new test class, no test pin.

---

## §7 Task specifications

One specification per block, in `.ai\tasks\templates\task_template.yaml` shape. **This is the
`{task_description}` format the block-level Planner uses at execution time.** Semantic code units
only — files, modules, classes, functions, methods, guard expressions. **Never line numbers.**

An Implementor is handed **one** of these and nothing else. Read your block in §3 first if any
question in the spec is unclear; the spec does not restate the block.

---

### B1

```yaml
id: plan08-b1-stop-observable-during-blocked-read
title: Make the stop observable while a child's output read is in flight
priority: critical
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B1 — Make the stop observable while a child's output read is in flight
source_blocks: ["B1"]
source_findings: ["CON-001"]

description: >
  iter_process_lines consults the shutdown event only BETWEEN lines and invokes on_shutdown from
  inside the NEXT loop iteration, so the kill is reachable only once the child produces more output.
  A stop during a yt-dlp or ffmpeg transfer leaves the reader blocked in readline(), on_shutdown
  never fires, cancel_subprocess is never reached THROUGH THE DRAIN, and the caller's await never
  returns. Make the stop observable WHILE the read is in flight.

SELECTED SHAPE (Planner decision, evidence below): keep `line = await stream.readline()` exactly
  as it is, and add ONE watcher task per generator that awaits the shutdown event and invokes
  on_shutdown when the stop lands mid-read. The read is NOT wrapped in a task. A single `fired`
  flag shared by the between-lines path and the watcher is the single-fire mechanism.

goals:
  - on_shutdown runs while the reader is blocked, not after readline() returns on its own
  - the drain terminates promptly after a stop, so the process.wait() race completes
  - on_shutdown still fires at most once per generator
  - EOF stays distinguishable from a stop: a b"" read ends the drain WITHOUT on_shutdown
  - no task of ours survives the generator: no leaked task, no "Task was destroyed but it is pending"
  - an already-available line must cost NO extra event-loop suspension (see REGRESSION below)
  - no transfer-stage timeout is introduced anywhere

files:
  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets:
      - type: function
        name: iter_process_lines
      - type: function
        name: read_progress
    semantic_anchors:
      modify:
        - type: guard_expression
          value: "if shutdown_event.is_set():"
        - type: assignment
          value: "line = await stream.readline()"
      insert_before:
        type: assignment
        value: "line = await stream.readline()"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestIterProcessLines
    semantic_anchors:
      insert_after:
        type: class
        name: TestIterProcessLines

changes:

  - action: modify
    description: >
      Add a generator-scoped watcher task that awaits shutdown_event.wait() and invokes on_shutdown,
      so a stop landing mid-read is observed while the reader is blocked. The read itself stays a
      plain `await stream.readline()`. The between-lines `if shutdown_event.is_set():` guard is
      KEPT. A single `fired` flag is set inside the one shared `fire()` helper BEFORE awaiting
      on_shutdown, so both paths cannot double-fire. The `finally` clause cancels the watcher and
      awaits it.
    code_hint: |
      async def iter_process_lines(stream, shutdown_event, *, on_shutdown=None):
          fired = False

          async def fire() -> None:
              """The ONLY place on_shutdown is invoked, so it cannot fire twice."""
              nonlocal fired
              if on_shutdown is None or fired:
                  return
              fired = True
              await on_shutdown()

          async def _watch_shutdown() -> None:
              """Unblocks a read that is already in flight."""
              await shutdown_event.wait()
              await fire()

          watch_task = asyncio.create_task(_watch_shutdown())
          try:
              while True:
                  if shutdown_event.is_set():
                      await fire()
                      break
                  line = await stream.readline()
                  if not line:
                      break
                  yield line
          finally:
              if not watch_task.done():
                  watch_task.cancel()
                  try:
                      await watch_task
                  except asyncio.CancelledError:
                      pass

  - action: add_test
    description: >
      Add tests INSIDE the existing TestIterProcessLines class (no new tests/ file, so
      tests/test_packaging.py EXPECTED_SDIST_ENTRIES is untouched). Each drives an
      asyncio.StreamReader fed with data and then left silent, so the read blocks for real; no
      subprocess and no network. Cover, as separate cases: (1) a stop landing while the read is in
      flight invokes on_shutdown and the generator ends, asserting no pending task remains;
      (2) EOF with no stop yields every line and never invokes on_shutdown; (3) the stop is already
      set before iteration, invoking on_shutdown exactly once (the existing coverage, kept as the
      between-lines regression net); (4) the consumer breaks out mid-stream, after which no task of
      ours is left pending. Assert on BEHAVIOUR (what the callback did, what was yielded, what
      remains pending) — never on task identities or implementation shape.
    code_hint: |
      # the in-flight case, which none of the four existing tests can reach
      stream = asyncio.StreamReader()
      stream.feed_data(b"line one\n")   # one line, then silence -> the next read blocks
      shutdown_event = asyncio.Event()

      async def _stop_soon() -> None:
          await asyncio.sleep(0)
          shutdown_event.set()

      stopper = asyncio.create_task(_stop_soon())
      callback_calls: list[str] = []

      async def on_shutdown() -> None:
          callback_calls.append("fired")
          stream.feed_eof()   # stand-in for cancel_subprocess closing the pipe

      lines = [line async for line in iter_process_lines(stream, shutdown_event, on_shutdown=on_shutdown)]
      await stopper

      assert lines == [b"line one\n"]
      assert callback_calls == ["fired"]
      assert not [t for t in asyncio.all_tasks()
                  if t is not asyncio.current_task() and t is not stopper]

  - action: prohibited
    description: >
      MUST NOT add an import to ffmpeg_utils.py — in particular MUST NOT import
      downloader_throttle. The module must remain a leaf (it imports only ..exceptions and
      ..utils.formatting). The watcher uses asyncio only.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT wrap the read in a task (create_task(stream.readline())) or race it with
      asyncio.wait. Measured on this machine: doing so costs ~35 us/line against ~1.6 us/line, and
      -- decisively -- it breaks SIX currently-green tests, because the extra suspension lets
      process.wait() win the caller's FIRST_COMPLETED race and cancel the drain before it yields a
      single line. Observable losses: progress callbacks stop firing, and SEC-002 stderr
      sanitisation degrades to "Unknown ffmpeg error". A `wait_for`/`asyncio.sleep(0)` "peek"
      variant was measured too and still loses lines (1 of 2, and 0 of 2 respectively).
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT convert read_progress's shutdown_event parameter into a module lookup. The
      parameter is deliberate; the default throwaway asyncio.Event() is deliberate.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT add a timeout to any transfer stage. The yt-dlp "no application-level download
      timeout is imposed" decision in _download_with_ytdlp's docstring is load-bearing and must
      survive byte-identical. No re-export line in downloader.py may be edited.
    code_hint: |

acceptance_criteria:
  - A stop during a blocked read invokes on_shutdown while the reader is blocked
  - The drain ends promptly after that stop, so the caller's process.wait() race completes
  - on_shutdown fires at most once per generator, from ONE shared helper both paths call
  - A b"" read (EOF) ends the generator WITHOUT invoking on_shutdown
  - The four existing TestIterProcessLines cases are green UNCHANGED
  - TestYtDlpSubprocessShutdown::test_ytdlp_cancelled_on_shutdown_returns_none is green UNCHANGED
  - >
    The FULL suite is green — in particular the six drain tests a task-wrapped read breaks:
    test_error_handling_ffmpeg_failure_sanitizes_url_in_error,
    test_download_with_ffmpeg_with_progress_callback,
    test_perform_download_ffmpeg_progress_adapter_sends_unknown_total,
    test_ytdlp_stdout_progress_written_to_console,
    test_ytdlp_echo_false_suppresses_stderr_while_callback_fires,
    test_ytdlp_echo_false_progress_emits_debug_log
  - >
    No task of ours outlives the generator: no leftover task after a break, an aclose, or a
    consumer cancellation, and no NEW "Task was destroyed but it is pending" in the suite output
  - The new tests assert behaviour (callback invocation, yielded lines, pending tasks), never
    implementation shape
  - ffmpeg_utils.py has no new import; read_progress keeps its parameter
  - The yt-dlp no-application-level-timeout docstring is byte-identical before and after
  - The COMMIT BODY states the narrow finding, names SIX cancel_subprocess call sites rather than
    claiming on_shutdown is the only kill path, claims NO correlation-id obligation, and does NOT
    claim the R5(iii) leg is a defect
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files (landing rule, plan §2.4)
```

#### B1 — Planner decisions (measured on this machine: CPython 3.12.1, ProactorEventLoop)

The plan left four questions open. All four are now decided, each against a probe rather than an
assertion. The probes were throwaway files under `tmp/` and have been deleted.

**1. The race shape — a per-generator watcher, NOT a raced read.**
Selected: keep `line = await stream.readline()` untouched and add one watcher task per generator
that awaits `shutdown_event.wait()` and fires `on_shutdown`. Rejected, with reasons:

- *Racing the read task against `shutdown_event.wait()` via `asyncio.wait`* — fixes the stop, but
  breaks the callers. The extra suspension lets `process.wait()` win the
  `_await_first_and_cancel_others` FIRST_COMPLETED race and cancel the drain before it yields
  anything. Measured: 6 green tests fail; progress callbacks stop firing and SEC-002 stderr
  sanitisation degrades to `Unknown ffmpeg error`. That is a diagnostic regression, not a test
  artefact — an ffmpeg that exits immediately is a real case. Cost also measured at ~35 us/line
  against ~1.6 us/line baseline.
- *Bare coroutines into `asyncio.wait`* — rejected outright. Python 3.12 raises
  `TypeError: Passing coroutines is forbidden, use tasks explicitly`, plus two
  `coroutine ... was never awaited` warnings. Measured.
- *A `wait_for` / `asyncio.sleep(0)` "peek" before racing* — measured to still lose lines: the
  `sleep(0)` peek drains 1 of 2, the `wait(timeout=0)` peek drains 0 of 2.
- *A single long-lived stop waiter reused across lines* — no saving: it must be rebuilt per line
  once settled, so it measured identically at ~35 us/line.
- *A per-generator watcher that cancels the registered read task* — behaviourally correct and
  cheapest (~12 us/line), but it FAILS the pre-set-event case: with the event already set the
  watcher has not yet run, so the loop breaks and `on_shutdown` never fires — which breaks the
  existing `test_invokes_on_shutdown_callback`. Rejected on that measurement.
- *A bounded `wait_for` polling loop* — rejected by the prohibitions: it introduces a timeout into
  a transfer stage, which §5.2 forbids, and it needs a new module-level constant.

**Why the watcher shape keeps EOF and stop distinguishable.** The drain still ends on `b""` from
`readline()` without touching `fire()`. If a stop and an EOF land in the same instant, the `b""`
wins and no kill comes from the drain — verified safe, because the callers already re-check the
event after the race and call `cancel_subprocess` themselves (`downloader.py`'s post-race guard,
and `_download_with_ytdlp`'s `if shutdown_event.is_set():` arm). Measured: `_download_with_ytdlp`
still awaits `cancel_subprocess` exactly once in that tie.

**2. Exactly-once `on_shutdown`.** One shared `fire()` closure holding a `fired` flag, set BEFORE
`await on_shutdown()`. Both the between-lines guard and the watcher call it. Which green test proves
it: `test_invokes_on_shutdown_callback` asserts `len(callback_called) == 1` and stays green — it is
the between-lines arm. The in-flight arm needs its own new case, and that new test must assert the
count too: a naive fix that fires in flight and then falls through to the next iteration's guard
was measured firing twice on the discriminator sequence (stop set while a read is blocked, more
data arriving, generator continuing). That is the specific wrong implementation the count
assertion is there to catch.

**3. Cleanup on close, early break, and cancellation.** The `finally` cancels the watcher and awaits
it. Measured for the selected shape: `aclose()` → 0 leftover; consumer `break` → 0 leftover once
the generator is finalized; consumer task cancelled → `on_shutdown` NOT fired (the callers own that
path via their own `CancelledError` arms) and 0 leftover. **Residual risk the Implementor must
verify, not assume:** if a consumer abandons the generator WITHOUT finalizing it and the loop is
closed without `shutdown_asyncgens`, the watcher is destroyed pending — I reproduced both the
`Task was destroyed but it is pending` line and the extra `coroutine 'Event.wait' was never
awaited` warning that way. `asyncio.run` and `pytest-asyncio` both finalize async generators, which
is why the full suite passes; but the Implementor must confirm the suite's warning count does not
grow, and if it does, the watcher must be created lazily (only once a read is about to block)
rather than eagerly at generator entry.

**Gate.** Full suite green plus the no-new-warning check, not just the four cases in
`TestIterProcessLines` — that narrower gate is exactly what would have let the six-test regression
through.

---

### B2

```yaml
id: plan08-b2-segment-completion-helper-contract
title: Settle the siblings, and stop conflating nothing-to-do with cancelled
priority: high
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B2 — Settle the siblings, and stop conflating "nothing to do" with "cancelled"
source_blocks: ["B2"]
source_findings: ["CON-006", "CON-007", "CON-008", "phase04/VAL-402"]

description: >
  _await_and_cancel has one early return for "nothing to do" and an identical return on
  cancellation, so a fully-resumed download never reaches _tally_and_merge and is reported as
  FAILED. Its gather has no return_exceptions, so a raising part orphans every sibling: they keep
  writing .ts files after download_hls_with_resume's finally has logged
  preserving_segments_for_resume, against an aiohttp session whose async with has already closed.
  And on cancellation it logs reason="shutdown_requested" and returns None instead of re-raising,
  so a caller that cancels gets a normal return and the batch classifies the item as failed with
  exit 1 instead of 130. ALL THREE EDITS LAND IN ONE CHANGE SET (phase04/VAL-402).

  The outcome shape is DECIDED by the block Planner - see §3.1: a two-member StrEnum plus a frozen
  dataclass carrying the outcome and the results, both module-private in segment_downloader.py.

goals:
  - "nothing to do" and "completed" are two distinguishable outcomes at the TYPE level, and
    cancellation is NEITHER of them: it is a CancelledError that is re-raised
  - every sibling task is settled before the helper returns or re-raises
  - CancelledError propagates to the caller after the siblings settle
  - the log reason distinguishes a stop-state-driven shutdown from a plain cancellation, and the
    stop-driven reason value stays byte-identical
  - a fully-present resume reaches the merge and produces the finished video
  - an un-cancelled None is still FAILED and still exits 1; the second-interrupt route still 130s

files:
  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: class
        name: _SegmentFanoutOutcome
      - type: class
        name: _SegmentFanoutResult
      - type: function
        name: _await_and_cancel
      - type: function
        name: _process_downloaded_segments
      - type: function
        name: _tally_and_merge
      - type: function
        name: download_hls_with_resume
    semantic_anchors:
      insert_before:
        type: function
        value: _await_and_cancel
      modify:
        - type: guard_expression
          value: "if not tasks: return None"
        - type: call
          value: asyncio.gather
        - type: except_clause
          value: "except asyncio.CancelledError:"
        - type: call
          value: logger.info
        - type: return_statement
          value: return None
        - type: assignment
          value: download_results = await _await_and_cancel(tasks)
        - type: guard_expression
          value: "if download_results is None: return None"
        - type: call
          value: _tally_and_merge
        - type: docstring
          value: Returns
        - type: guard_expression
          value: "if download_results and not all(r for _, r in download_results):"

  - path: tests/test_segment_downloader.py
    targets:
      - type: class
        name: TestSegmentFanoutCompletion
    semantic_anchors:

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestDownloadHlsWithResume
    semantic_anchors:
      preserve:
        - type: function
          value: test_preserves_segments_on_segment_download_failure
          note: RUN ONLY - must stay green unchanged, do not edit

  - path: tests/test_batch_downloader.py
    targets:
      - type: class
        name: TestBatchCancellationPropagates
    semantic_anchors:
      preserve:
        - type: class
          value: TestBatchCancellationReporting
          note: must stay green UNCHANGED - put the new test in a NEW class, never inside this one

changes:

  - action: add_code
    description: >
      THE OUTCOME TYPE - DECIDED, see §3.1. Two module-private types in segment_downloader.py, NOT
      in models/ and not a class hierarchy (rules 4 and 6): a two-member StrEnum and a frozen
      dataclass whose results field is a LIST, not a tuple. The tuple variant is a measured trap -
      it fails mypy --strict against _tally_and_merge's live `download_results:
      list[tuple[int, bool]]` parameter, which would force a third function's annotation to change
      and breach "the fix stays inside _await_and_cancel and its one consumer". There is NO
      CANCELLED member: cancellation is re-raised, never returned, so a third member would be
      vocabulary the code cannot produce and a fixer who uses it reinstates CON-008. Two
      module-level Final reason constants so no new named value is a bare literal (rule 10); the
      SHUTDOWN reason's value must stay byte-identical to today's.
    code_hint: |
      from enum import StrEnum
      from typing import Final

      _REASON_SHUTDOWN: Final = "shutdown_requested"
      _REASON_CANCELLED: Final = "cancelled"


      class _SegmentFanoutOutcome(StrEnum):
          """Why the segment fan-out produced no result tuples (CON-006, phase04/VAL-402).

          COMPLETED: the factory produced at least one task and every task settled.
          NOTHING_TO_DO: no segment was missing, so the merge must still be attempted
          from what is already on disk. Cancellation is not a member - it is raised.
          """

          COMPLETED = "completed"
          NOTHING_TO_DO = "nothing_to_do"


      @dataclass(frozen=True)
      class _SegmentFanoutResult:
          """_await_and_cancel's return value: the outcome plus the results it produced.

          `results` is a list, not a tuple, so it reaches _tally_and_merge unchanged.
          It is empty exactly when the outcome is NOTHING_TO_DO; the outcome is still
          carried explicitly, because a consumer must not be left inferring the
          distinction from a falsy length.
          """

          outcome: _SegmentFanoutOutcome
          results: list[tuple[int, bool]]

  - action: modify
    description: >
      _await_and_cancel returns the typed result on every path, settles every sibling on ANY
      exception, and re-raises in every case. The settle sequence (cancel the not-done tasks, then
      gather them with return_exceptions=True) moves out of the `except asyncio.CancelledError` arm
      into an `except BaseException` arm, so a raising part cannot orphan its siblings, and a bare
      `raise` follows the settle. The `download_cancelled` record is emitted ONLY on the
      cancellation arm, once, before the re-raise, with the stop-driven value when the stop state is
      set and the plain-cancellation value otherwise. Rewrite the docstring: the return is the
      result object; CancelledError, and any task's own exception, is raised after the settle.
      Note for the report: the settle is bounded by each sibling's own transfer
      `download_timeout` - not a permanent leak, and no new timeout constant is introduced.
    code_hint: |
      async def _await_and_cancel(
          tasks: list[asyncio.Task[tuple[int, bool]]],
      ) -> _SegmentFanoutResult:
          """Await segment download tasks, settling every sibling before returning or raising.

          Args:
              tasks: Download tasks to await. Each returns (segment_index, success).

          Returns:
              _SegmentFanoutResult with outcome COMPLETED and one (index, success) tuple per
              task, or outcome NOTHING_TO_DO and an empty list when nothing was to download.

          Raises:
              asyncio.CancelledError if the enclosing task is cancelled, after every
              sibling is settled. Any other exception from a task is re-raised, also
              after every sibling is settled.
          """
          if not tasks:
              return _SegmentFanoutResult(_SegmentFanoutOutcome.NOTHING_TO_DO, [])

          try:
              results = await asyncio.gather(*tasks)
          except BaseException as exc:
              # CON-007: a raising part must not orphan its siblings. CON-008: a
              # cancellation is re-raised, never turned into a return value.
              for task in tasks:
                  if not task.done():
                      task.cancel()
              await asyncio.gather(*tasks, return_exceptions=True)
              if isinstance(exc, asyncio.CancelledError):
                  logger.info(
                      "download_cancelled",
                      reason=_REASON_SHUTDOWN if get_shutdown_event().is_set() else _REASON_CANCELLED,
                  )
              raise

          return _SegmentFanoutResult(_SegmentFanoutOutcome.COMPLETED, results)

  - action: modify
    description: >
      _process_downloaded_segments, the one consumer: branch on the OUTCOME'S IDENTITY, never on
      truthiness. The local is the result OBJECT, so the falsy results list is never a bare local
      beside the guard and `if not fanout.results` cannot be written as a local "tidy" - that edit
      is the exact regression VAL-402 exists to prevent. The NOTHING_TO_DO -> return None mapping is
      unchanged, so this function's own `Path | None` contract, _tally_and_merge's signature and
      everything above it are untouched, and _classify_download_result cannot be reached by a
      different value than before.
    code_hint: |
      fanout = await _await_and_cancel(tasks)
      if fanout.outcome is _SegmentFanoutOutcome.NOTHING_TO_DO:
          return None
      return await _tally_and_merge(
          fanout.results,
          segments,
          segments_dir,
          output_file,
          progress_callback,
          video_url,
          download_timeout,
      )

  - action: modify
    description: >
      _tally_and_merge: NO behavioural change. Measured - an empty results list with every segment
      on disk reaches the merge branch and returns the merged path, and a partial directory returns
      None. Its `if download_results and not all(...)` guard becomes reachable with an empty list
      for the first time, so it gains a one-line comment recording that an empty list means "no
      explicit per-segment failure was recorded" and that the merge is then decided by the on-disk
      count. The guard's behaviour must be equivalent.
    code_hint: |
      # download_results is empty on the resume path (CON-006): no segment failed
      # explicitly, so the merge is decided by the on-disk count below.

  - action: add_test
    description: >
      THE MISSING RESUME-CASE TEST - it does not exist today and it is the whole point of CON-006.
      Put it in tests/test_hls_downloader.py::TestDownloadHlsWithResume, because it drives
      download_hls_with_resume, which is what the finding is about. Two runs against the real
      session, playlist parse, stale-segment sweep and merge: run 1 with _merge_segments_batched
      stubbed to return None (a failed merge leaves the segments AND the playlist signature on
      disk), then run 2 with the same stubs. Assert run 2 returns the output path, that
      _merge_segments_batched was called again on run 2, and that _download_segment was NOT called
      on run 2 - the factory produced zero tasks because every segment is already present. Drive
      the real signature file; do not hand-write it. This exact shape is measured: today run 2
      returns None, calls the merge zero times, and the factory produces 0 tasks.
    code_hint: |
      # pre-fix this test fails: run 2 returns None and the merge is never attempted

  - action: add_test
    description: >
      A new class TestSegmentFanoutCompletion in tests/test_segment_downloader.py, covering the
      helper's contract directly, each with a BOUNDED wait: (1) the nothing-to-do case returns
      outcome NOTHING_TO_DO with results == [] - the type-level oracle, red today because the helper
      returns None and has no .outcome; (2) one task raises - no sibling is left pending once the
      helper's exception has propagated, and every sibling released its permit (assert the tasks'
      done() states AND the semaphore's value); (3) cancelling the holder propagates
      CancelledError AND the logged reason is the plain-cancellation value, not
      shutdown_requested; (4) with the stop state SET the logged reason IS shutdown_requested - the
      other half of the distinction. Capture the log FIELD with patch on segment_downloader's
      logger.info and assert the (event, fields) pair, the pattern already used by
      tests/test_progress_display.py - never rendered text. Any test that needs a set or unset stop
      state must use the token idiom (`_shutdown_event_ctx.set(asyncio.Event())` /
      `.reset(token)`) inside the test coroutine; a bare set() leaks a loop-bound Event into every
      later test in the session.
    code_hint: |
      try:
          await asyncio.wait_for(segment_downloader._await_and_cancel(tasks), timeout=5.0)
      except TimeoutError:
          pytest.fail(
              "a raising part left a sibling unsettled: pending after 5.0s; "
              f"done states: {[t.done() for t in tasks]}"
          )

  - action: add_test
    description: >
      A new class TestBatchCancellationPropagates in tests/test_batch_downloader.py, added
      ALONGSIDE TestBatchCancellationReporting and never inside it, which must stay green
      unchanged: a download that RAISES asyncio.CancelledError is not classified as FAILED -
      run_batch propagates the cancellation and _print_batch_summary is never called. This is the
      end-to-end observable that CON-008's fix stopped absorbing. State the measured route in the
      test's docstring: the cancellation exits through cli.py's
      `except (KeyboardInterrupt, asyncio.CancelledError)` -> typer.Exit(130), NOT through the
      summary. B5 reuses this test rather than duplicating it.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT branch on truthiness anywhere on the consumer's path - no `if not
      fanout.results`, no `if not download_results`, and no `if not tasks` that returns None. A
      falsy nothing-to-do result reaching a truthiness test silently reinstates CON-006. MUST NOT
      add a CANCELLED member to the outcome, or return one instead of re-raising - that reinstates
      CON-008. MUST NOT type the dataclass's results field as a tuple. MUST NOT change
      _tally_and_merge's guard behaviour, its annotation, or any parameter; MUST NOT change
      _create_segment_download_tasks or _download_segment_concurrent's semaphore claim (they are
      B6's) or the D-01 comment; MUST NOT touch _create_connector (B8's), ffmpeg_utils.py, or
      batch_downloader.py in src/. MUST NOT change _classify_download_result. MUST NOT put the
      outcome type, a sentinel, or any new type in models/. MUST NOT add a new src/ or tests/ file -
      a new src/ file also trips EXPECTED_SDIST_ENTRIES. MUST NOT introduce a timeout constant to
      bound the settle.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT edit tests/test_hls_downloader.py::TestDownloadHlsWithResume::
      test_preserves_segments_on_segment_download_failure, and MUST NOT edit any test inside
      tests/test_batch_downloader.py::TestBatchCancellationReporting. MUST NOT absorb the
      uncommitted quality-selection work that is ALREADY dirty in segment_downloader.py and in all
      three test files: stage by explicit path, and by hunk (`git add -p`) for those four files -
      `git add <path>` alone sweeps the uncommitted work into the commit. Never `git add -A`,
      `git add .`, or `git commit -a`.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT claim in the commit body, a docstring or a report that the caller was told the
      download FINISHED (it was told it FAILED), that a sibling occupied an HTTP session SLOT (the
      session's `async with` had already closed, so its next request fails on a CLOSED session), or
      that the siblings are permanently LEAKED (each is bounded by its own transfer
      `download_timeout`). MUST NOT describe the fix as making the resume path merge
      unconditionally - a directory count that does not match the playlist still returns None.
    code_hint: |

tests_to_run:
  - uv run pytest tests/test_segment_downloader.py -q
  - uv run pytest tests/test_batch_downloader.py -q
  - uv run pytest tests/test_hls_downloader.py -q
  - uv run pytest "tests/test_hls_downloader.py::TestDownloadHlsWithResume::test_preserves_segments_on_segment_download_failure" -q
  - uv run pytest -q -rs
  - uv run ruff check src tests
  - uv run ruff format --check src tests
  - uv run mypy src

acceptance_criteria:
  - A fully-present resume reaches _tally_and_merge and produces the finished video, and the new
    test is proved RED against the pre-fix module (a pre-fix copy under tmp/, the method B1 used
    in 0b80f55) - not merely green after
  - _await_and_cancel never returns None: its annotation is _SegmentFanoutResult, and the
    consumer's own `Path | None` contract is unchanged
  - The consumer branches on `fanout.outcome is _SegmentFanoutOutcome.NOTHING_TO_DO`; the diff
    contains no truthiness test on a results value
  - A raising part leaves no sibling task pending and every sibling released its permit
  - CancelledError propagates out of the helper after the siblings settle
  - The logged reason is the plain-cancellation value when the stop state is unset and
    shutdown_requested when it is set; the shutdown value is byte-identical to today's
  - TestBatchCancellationReporting is green and UNCHANGED, including
    test_uninterrupted_failed_download_is_still_a_failure: a genuinely-None result with the stop
    state unset is still FAILED with exit 1
  - The second-interrupt route is re-verified by reading the chain and stated in the report, step
    for step: _await_and_cancel -> _process_downloaded_segments -> _run_download_session ->
    download_hls_with_resume -> _download_single -> _run_batch_with_progress's
    `except asyncio.CancelledError` fan-out -> re-raise -> cli.py's CancelledError arm ->
    typer.Exit(130). _print_batch_summary is NOT on that route (measured: 0 calls) and the report
    must say so, because plan §5.5 phrases it the other way round
  - test_preserves_segments_on_segment_download_failure is RUN and its outcome quoted, not assumed
  - _log_preserve_segments and download_hls_with_resume's `finally` are unchanged, and the report
    states whether preserving_segments_for_resume is still accurate: it is, and strictly MORE
    accurate - after the fix the record fires only when a merge genuinely produced nothing. Its two
    pre-existing caveats (batch_*.ts merge temps; a working-directory count rather than a
    resumable-segment count) are unchanged and stay documented in its own count_note
  - Every new await is bounded by asyncio.wait_for with a generous bound and a pytest.fail message
    naming what was not observed, following B1's 5.0s precedent - a regression is a red test in
    seconds, never a hang
  - No new src/ or tests/ file; EXPECTED_SDIST_ENTRIES untouched
  - Baseline floor 737 passed, 4 skipped, 2 warnings - the count may only rise, and the four D-11
    Windows-confinement skips stay exactly four
  - `git diff --cached --stat` and `git diff --cached` show only this block's hunks in
    segment_downloader.py, test_segment_downloader.py, test_hls_downloader.py and
    test_batch_downloader.py, with no quality-selection hunk among them
  - Commit subject `fix(concurrency): ...`; the body cites CON-006, CON-007, CON-008 and
    phase04/VAL-402 (VAL- qualified, never bare), states the outcome type chosen and the rejected
    options with the reason, and carries corrections 6-7 of §3 B2's inherited prohibitions
  - pytest, ruff check, ruff format --check and mypy all pass, with the exact output quoted
```

---

### B3

```yaml
id: plan08-b3-restore-displaced-signal-handler
title: Restore the previously installed process-level signal handler on the branch that runs
priority: critical
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B3 — Restore the previously installed process-level handler on the branch that runs
source_blocks: ["B3"]
source_findings: ["CON-001"]

description: >
  On Windows ProactorEventLoop.add_signal_handler raises NotImplementedError, so the
  signal.signal fallback is the branch that actually installs — and loop.remove_signal_handler
  fails the same way, so cleanup's loop branch swallows the error and achieves nothing. After
  cleanup, SIGINT is STILL setup_signal_handlers' own handler; because it is no longer installed,
  asyncio.run's Runner.run() cannot restore default_int_handler. The displaced SIGINT handler is
  asyncio.runners.Runner._on_sigint (a functools.partial), NOT SIG_DFL, while SIGTERM's pre-install
  value IS SIG_DFL — so a single reset-to-default restore is insufficient.

  THE COMPOUNDING CONSEQUENCE, which the plan did not state and which the Implementor must fix
  together with the restore: because cleanup leaves the project's own handler installed, the
  SECOND cycle's pre-install value is the FIRST cycle's handler, so Runner only arms _on_sigint on
  entry when SIGINT `is default_int_handler` — after one cycle, nothing in the process will again
  cancel the main task or raise KeyboardInterrupt. Measured over three consecutive asyncio.run
  cycles against the current code: cycle 1's pre-install is the Runner's partial, cycles 2 and 3's
  are this module's own handler, and after every cycle SIGINT is still this module's handler.

  SELECTED SHAPE (Planner decision, evidence in the decisions section below): two private,
  signal-keyed dicts beside the existing `_registered_signals` set — `_previous_handlers` (the
  displaced value) and `_installed_handlers` (the callable installed here, for the identity guard) —
  plus two private helpers, `_capture_previous_handler` and `_restore_previous_handler`. Capture
  reads `signal.getsignal(sig)` BEFORE the install attempt and happens ONCE per signal. The restore
  is HOISTED out of the `if loop is not None:` / `else:` split, so both branches share one restore
  and the `else:` branch's `signal.signal(sig, signal.SIG_DFL)` is deleted rather than corrected.

goals:
  - each signal's pre-install handler is captured at install time and restored at cleanup, per signal
  - the restore value is the captured one, never signal.SIG_DFL, and never a single shared value
  - a restore is skipped when the installed handler is no longer the one installed here
  - after asyncio.run returns, SIGINT is the runtime's own handler, so every later cycle re-captures
  - a second setup without a cleanup cannot overwrite the captured value with this module's handler
  - all three module stores are cleared together, so a later cycle re-captures
  - the idempotence guard is untouched — that is B5's subject

files:
  - path: src/vkdownloader/services/signal_handlers.py
    targets:
      - type: function
        name: setup_signal_handlers
      - type: function
        name: cleanup_signal_handlers
    semantic_anchors:
      insert_before:
        - type: function
          name: setup_signal_handlers
      modify:
        - type: assignment
          value: "_registered_signals: set[signal.Signals] = set()"
        - type: guard_expression
          value: "if loop is not None:"
        - type: function_call
          value: signal.signal
        - type: function_call
          value: signal.getsignal
      delete:
        - type: function_call
          value: "signal.signal(sig, signal.SIG_DFL)"

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestSetupSignalHandlers
    semantic_anchors:
      insert_after:
        type: class
        name: TestSetupSignalHandlers

changes:

  - action: modify
    description: >
      Add the module state. `_HANDLED_SIGNALS: Final[tuple[signal.Signals, ...]]` replaces the two
      inline `(signal.SIGINT, signal.SIGTERM)` tuples (a third copy would appear in cleanup).
      `_previous_handlers` holds the displaced value per signal; `_installed_handlers` holds the
      callable installed here, for the identity guard; `_registered_signals` stays the single
      registration gate and the iteration set. New state is private, single-underscore, and NOT
      added to `__all__`, which must stay exactly the two function names. The value type is
      `signal._HANDLER | None` — the private typeshed alias — because `signal.getsignal` returns
      `None | _HANDLER` and the module may not gain an import.
    code_hint: |
      _HANDLED_SIGNALS: Final[tuple[signal.Signals, ...]] = (signal.SIGINT, signal.SIGTERM)

      # Three distinct facts, kept apart on purpose:
      #   _registered_signals  - signals installed for; the single gate and iteration set
      #   _previous_handlers  - what was installed BEFORE this module displaced it (may differ
      #                          per signal: SIGINT is the runtime's partial, SIGTERM is SIG_DFL)
      #   _installed_handlers - the callable installed here; the identity guard reads it
      _registered_signals: set[signal.Signals] = set()
      _previous_handlers: dict[signal.Signals, signal._HANDLER | None] = {}
      _installed_handlers: dict[signal.Signals, signal._HANDLER] = {}

  - action: modify
    description: >
      `setup_signal_handlers` captures each signal's pre-install value before the install attempt,
      ONCE per signal, through a new private helper `_capture_previous_handler(sig)`. The install
      sites stay where they are, but the `lambda s, f: _handle_signal()` becomes a named
      `def _process_signal(_sig: int, _frame: object) -> None` so the installed object can be
      recorded in `_installed_handlers` — a lambda may NOT be bound to a name here, `ruff`'s E731
      is selected and fails the build. `_handle_signal` itself, including its
      `if not shutdown_event.is_set():` idempotence guard, is NOT touched.
    code_hint: |
      def _capture_previous_handler(sig: signal.Signals) -> None:
          """Record the process-level handler this module is about to displace.

          Captured once per signal: a second setup with no intervening cleanup must keep the
          ORIGINAL pre-install value, or the cleanup that follows would restore this module's own
          handler and the displacement would survive it. signal.getsignal returns None for a signal
          never set from Python, and there is then nothing to put back, so it is not stored.
          """
          if sig in _previous_handlers:
              return
          previous = signal.getsignal(sig)
          if previous is not None:
              _previous_handlers[sig] = previous

      # inside setup_signal_handlers, once per setup, before the per-signal loop:
      def _process_signal(_sig: int, _frame: object) -> None:
          _handle_signal()

      # inside the per-signal loop, for each of the two signal.signal install sites:
      _capture_previous_handler(sig)
      signal.signal(sig, _process_signal)
      _installed_handlers[sig] = _process_signal
      _registered_signals.add(sig)

  - action: modify
    description: >
      `cleanup_signal_handlers` keeps the loop-level `loop.remove_signal_handler(sig)` attempt and
      its `except (NotImplementedError, KeyError, RuntimeError): pass` — it is correct where the
      loop supports it — and then, HOISTED OUT of the `if` / `else` split so both branches share
      it, performs the process-level restore through a new private helper
      `_restore_previous_handler(sig)`. The `else:` branch is DELETED: its
      `signal.signal(sig, signal.SIG_DFL)` is the wrong restore value for SIGINT and is unreachable
      from both shipped call sites. The three stores are then cleared together, adjacently, at the
      end of the function. `cleanup_signal_handlers()` with no prior setup stays a harmless no-op.
    code_hint: |
      def _restore_previous_handler(sig: signal.Signals) -> None:
          """Put back the handler captured at install time, once.

          Skipped when nothing was captured, and skipped when the installed handler is no longer
          the one installed here — a third party owns the disposition then, and clobbering it would
          be worse than leaving it. Never signal.SIG_DFL for SIGINT: the displaced handler is
          asyncio.runners.Runner._on_sigint, and resetting to the default would turn Ctrl-C from
          "cancel the main task" into "terminate the process".
          """
          previous = _previous_handlers.get(sig)
          if previous is None:
              return
          if signal.getsignal(sig) is not _installed_handlers.get(sig):
              return
          try:
              signal.signal(sig, previous)
          except (OSError, ValueError, RuntimeError):
              # Ignore errors if the signal is not restorable from this thread or context
              pass

      # end of cleanup_signal_handlers, after the hoisted restore loop:
      # Cleared as one group: a store that outlives a cycle makes the next one re-use a stale
      # value instead of re-capturing.
      _registered_signals.clear()
      _previous_handlers.clear()
      _installed_handlers.clear()

  - action: modify
    description: >
      Correct the documentation that this change falsifies, in the same commit (plan §5.7).
      `setup_signal_handlers`'s "Handlers are loop-scoped and must be cleaned up" is false once
      cleanup restores a process-level handler, and `cleanup_signal_handlers`'s "Remove signal
      handlers and reset registration state" does not say what is restored. The module comment
      "# Track registered signals for loop-scoped cleanup" above `_registered_signals` is false for
      the same reason. All three must state, in English, that the process-level handler displaced at
      install time is captured per signal and that cleanup restores exactly those values — and that
      the values differ per signal, so neither is assumed to be signal.SIG_DFL.
    code_hint: |

  - action: add_test
    description: >
      Three new cases INSIDE the existing `tests/test_hls_downloader.py::TestSetupSignalHandlers`.
      No new file, so `tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` is untouched, and every
      import is FUNCTION-LOCAL (`import signal as signal_module`, `from vkdownloader.services
      import signal_handlers`, and `_shutdown_event_ctx` only where used) so each new case is one
      contiguous hunk at the end of the class and cannot collide with the unrelated uncommitted
      quality-selection work in the same file (plan §2.4).

      (1) `test_cleanup_restores_each_signals_previous_handler` — an async case with NO patching at
      all: no `_FakeLoop`, no patch of `asyncio.get_running_loop`, no patch of `signal.signal`. The
      real `ProactorEventLoop` in the pytest-asyncio loop raises `NotImplementedError` from
      `add_signal_handler`, so the process-level path runs for real, which is the only way to
      observe a real pre-install value. Both dispositions are captured with `signal.getsignal`
      BEFORE the call and restored in an UNCONDITIONAL `finally` — not dependent on
      `cleanup_signal_handlers()` having worked, so a failing fix yields exactly one red test
      instead of an unpredictable suite. Assert per signal, separately: after setup the disposition
      is NOT the pre-install value, and after cleanup it IS, for SIGINT and for SIGTERM as two
      separate assertions. A test asserting "the handler was reset" without checking WHICH value
      passes against today's code and must not be written.

      (2) `test_second_setup_keeps_the_first_captured_handler` — the capture-once oracle, also on
      the real path with the same unconditional `finally`: capture the pre-install values, setup,
      note the installed handler, setup again, assert the second installed handler is a DIFFERENT
      object, then ONE cleanup, then assert BOTH signals' original pre-install values are back.
      Follow with one more setup/cleanup cycle asserting the same originals, which is what proves
      the stores were cleared rather than left holding a stale value.

      (3) `test_handler_is_not_displaced_across_consecutive_event_loops` — a SYNCHRONOUS case that
      drives `asyncio.run(...)` itself, three consecutive times, which is the shipped call shape and
      the only way to observe a fresh `asyncio.runners.Runner` per cycle. It uses the project token
      idiom — `token = _shutdown_event_ctx.set(asyncio.Event())` and
      `_shutdown_event_ctx.reset(token)` in `finally` — because that idiom IS load-bearing in the
      sync-test / `asyncio.run`-inside-a-sync-test configuration, and restores both pre-test
      dispositions in the same `finally`. Per cycle assert the pre-install value is back after
      cleanup; after each `asyncio.run` returns assert SIGINT `is signal.default_int_handler`; and
      assert the three captured pre-install values are three DISTINCT objects. Today this case fails
      from cycle 1, because `default_int_handler` is never reached and the captures are this module's
      own handler from cycle 2 on.

      The two existing cases `test_windows_fallback_registers_signal_handlers` and
      `test_registered_handler_triggers_shutdown` are green and their source UNCHANGED. Do NOT
      "modernise" them, do NOT delete their `_FakeLoop`, and do NOT re-point them at the real path:
      they are the mocked-registration net, and the new real-path cases sit beside them. Neither can
      observe the capture and neither breaks under this fix — measured: with the guard in place both
      make ZERO real `signal.signal` calls during cleanup, exactly as today.

      Any await a new case needs must be bounded with `asyncio.wait_for` and a generous bound plus a
      `pytest.fail` naming what was not observed (the B1/B2 precedent). This design needs no await;
      if one is added it must be bounded. Tests assert logic and component interaction — a signal's
      disposition identity before/after — never the shape of a private store.
    code_hint: |
      @pytest.mark.asyncio
      async def test_cleanup_restores_each_signals_previous_handler(self) -> None:
          """Assert each signal's OWN pre-install handler comes back, per signal.

          Before the fix the displaced handler was not restored on the branch that actually runs,
          so asyncio.run's own SIGINT restore was skipped and the displacement compounded across
          cycles.
          """
          import signal as signal_module

          from vkdownloader.services import signal_handlers

          pre_int = signal_module.getsignal(signal_module.SIGINT)
          pre_term = signal_module.getsignal(signal_module.SIGTERM)
          try:
              signal_handlers.setup_signal_handlers()
              assert signal_module.getsignal(signal_module.SIGINT) is not pre_int
              assert signal_module.getsignal(signal_module.SIGTERM) is not pre_term
              signal_handlers.cleanup_signal_handlers()
              assert signal_module.getsignal(signal_module.SIGINT) is pre_int
              assert signal_module.getsignal(signal_module.SIGTERM) is pre_term
          finally:
              # Unconditional: a half-finished fix must not leave pytest-asyncio's own restore
              # suppressed for the rest of the session.
              signal_module.signal(signal_module.SIGINT, pre_int)
              signal_module.signal(signal_module.SIGTERM, pre_term)

  - action: prohibited
    description: >
      MUST NOT reset SIGINT to signal.SIG_DFL. The restore value is the captured per-signal value;
      a single shared "reset to default" is the over-correction this block exists to prevent. The
      `else:` branch's `signal.signal(sig, signal.SIG_DFL)` is DELETED, not corrected or kept for
      a non-async context.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT add an import to signal_handlers.py. It imports `asyncio`, stdlib `signal`,
      `structlog.get_logger` and `.downloader_throttle.get_shutdown_event`, and it must stay a leaf
      of that trio. This is why the stored value is typed `signal._HANDLER | None` rather than
      `Callable[..., object]`, and why the installed handler is a `def` with an `object` frame
      parameter rather than one typed `types.FrameType`. `__all__` MUST NOT change: still exactly
      the two function names, and the new state stays private.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT do blocking work in the signal context, and MUST NOT store anything in
      `_previous_handlers` that is not a handler object — a value stored there may be re-invoked
      from a signal handler by B5, so an awaitable, a coroutine or a `lambda` holding work is out.
      This block only installs and restores. MUST NOT move signal-handler REGISTRATION between
      `cli.py` and `batch_downloader.py` (`ENT-004` is phase 01's, plan 05 `D7` defers it) and MUST
      NOT touch `_handle_signal`'s `if not shutdown_event.is_set():` guard, which is B5's subject.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT build B5's forwarding path. Do not invoke the captured handler, do not escalate, do
      not add a live-child registry, and do not add a new `src/` module. The captured store is
      exposed to B5 as a read of `_previous_handlers`; this block only writes and clears it.
    code_hint: |

acceptance_criteria:
  - >
    After `cleanup_signal_handlers()`, SIGINT's pre-install value is back AND SIGTERM's pre-install
    value is back — asserted SEPARATELY, by identity, in a test that exercises the real
    `signal.signal` with no patching of `asyncio.get_running_loop` or `signal.signal`
  - Neither restore value is `signal.SIG_DFL` for SIGINT; the SIGINT restore value is the captured
    `asyncio.runners.Runner._on_sigint` partial in the shipped shape
  - After `asyncio.run` returns, SIGINT is `signal.default_int_handler`, so the runtime's own exit
    restore is no longer skipped
  - >
    Across three consecutive `asyncio.run` cycles SIGINT ends at `signal.default_int_handler` every
    time, and the three captured pre-install values are three distinct objects
  - >
    Two setups with one intervening cleanup restore the ORIGINAL pre-install value, and a further
    cycle re-captures the same original — the capture is once-per-signal, not once-per-setup
  - >
    A signal whose current handler is no longer the one installed here is left alone by the restore
  - The idempotence guard in `_handle_signal` is unchanged, and no new log record is added
  - signal_handlers.py gains no import; `__all__` is unchanged; the new state is private
  - >
    `setup_signal_handlers`'s docstring, `cleanup_signal_handlers`'s docstring and the
    `# Track registered signals for loop-scoped cleanup` comment all state that the displaced
    process-level handler is captured per signal and restored per signal, and that the two values
    differ
  - The two existing `TestSetupSignalHandlers` cases are green and their source UNCHANGED
  - >
    The full suite is green: `uv run pytest -q -rs` exits 0, the passed count RISES by the three new
    cases, no test is deleted or skipped to get there, and the four `D-11` Windows-confinement skips
    remain exactly four. `ruff check src tests`, `ruff format --check src tests` and `mypy src`
    all exit 0
  - >
    Registration placement is unchanged: `cli.py`'s and `batch_downloader.py`'s setup/cleanup call
    sites are untouched, and the setup/cleanup ordering in `batch_downloader.py` is untouched
  - No new `src/` or `tests/` file; `EXPECTED_SDIST_ENTRIES` untouched
  - >
    The COMMIT BODY cites `CON-001` (leg 3 of 3) and no bare `VAL-` id; records the MEASURED
    pre-install values for BOTH signals (SIGINT `functools.partial(<bound method Runner._on_sigint
    of asyncio.runners.Runner ...>, main_task=<Task ...>)`, SIGTERM `Handlers.SIG_DFL`); states that
    after `asyncio.run` SIGINT is currently still this module's handler and is the same afterwards;
    states the compounding consequence across cycles; names SIX `cancel_subprocess` call sites
    rather than "only `on_shutdown`"; and claims NO correlation-id obligation
  - git diff --cached --stat shows only this block's files, staged by explicit path and by hunk
```

#### B3 — Planner decisions (measured on this machine: CPython 3.12.1, ProactorEventLoop, pytest 9.1.1, pytest-asyncio 1.4.0)

The plan left six questions open. All six are decided, each against a measurement rather than an
assertion. The probes were throwaway files kept in the OS temp directory, outside the repository;
none of them wrote to the tree, and `src/`, `tests/` and `tmp/` are exactly as they were found.

**1. Home and shape of the captured handlers — two signal-keyed dicts, capture from `signal.getsignal` before the install, no redundant "did we capture" set.**
Selected: `_previous_handlers: dict[signal.Signals, signal._HANDLER | None]` and
`_installed_handlers: dict[signal.Signals, signal._HANDLER]` beside the existing
`_registered_signals`, with the capture in `_capture_previous_handler` and the restore in
`_restore_previous_handler`. Rejected, with the measurement that decided it:

- *Capture from `signal.signal(sig, handler)`'s return value* — atomic, and the audit brief prefers
  it. It is nevertheless **rejected**, and the reason is measured, not stylistic. Under the existing
  `test_windows_fallback_registers_signal_handlers`, `patch.object(signal_module, "signal")` is a
  plain `MagicMock`, and a call on a plain `MagicMock` returns **another `MagicMock`**, not `None`
  (only the `side_effect=_record_signal` case returns `None`). The capture therefore stores a mock as
  "the handler that was previously installed", and `cleanup_signal_handlers()` — which that test
  calls *outside* the patch — then hands that mock to the REAL `signal.signal`. Measured with a
  counting wrapper around the real function: **two real installs, and SIGINT's disposition changed
  from the runtime's `functools.partial` to a `MagicMock`.** That is a fix that silently installs a
  test double as the process's interrupt handler and suppresses pytest-asyncio's own `Runner`
  restore for the rest of the session — i.e. it would reproduce, inside the suite, the very
  compounding leak this block removes, in the one test the plan says must stay unchanged. With the
  identity guard of decision 3 in place the same combination is harmless, so the guard is the
  load-bearing choice; `getsignal` is belt-and-braces, and it is also the only source that is
  correct on a platform where `loop.add_signal_handler` succeeds. The narrow TOCTOU window it opens
  is one bytecode on the main thread, in a path that runs twice per download, and its worst outcome
  is restoring a value that is still the current one.
- *A redundant "did we capture" set* — rejected. It is a second source of truth for a fact the
  capture map already carries, and it can drift. `_registered_signals` stays the single registration
  gate and the iteration set, and `if sig in _previous_handlers` is the capture-once guard
  (decision 2).
- *One map of `(previous, installed)` pairs* (a frozen dataclass, rule 6's composition shape) —
  rejected on rule 5 and rule 15: a new type with two fields in a module that is otherwise two
  functions and one set, for no behavioural gain. Two flat dicts are smaller, and they keep
  B5's read of the previous value a single `.get`.
- *Deleting `_registered_signals` and deriving everything from the maps* — rejected: it removes
  existing module state for no gain and turns a two-line change into a rewrite.

`signal._HANDLER` is the private typeshed alias, and it is the right type precisely because
`signal.getsignal` returns `_HANDLER | None` and **the module may not gain an import** (the
`Callable` needed for the obvious spelling is a `typing`/`collections.abc` name, and
`disallow_untyped_defs` would additionally force a `types.FrameType` import on the installed
handler's `def`). Verified: `mypy --strict` accepts `dict[signal.Signals, signal._HANDLER | None]`
and `signal.signal(sig, previous)` with no narrowing. The accepted fallback, if a future typeshed
drops the alias, is `dict[signal.Signals, object]` plus a `callable()` narrowing at the use site —
**not** a new import, and **not** a behaviour change.

**2. Capture-once, not overwrite-on-every-setup.** Measured on the current code: two setups with no
cleanup in between leave `_registered_signals` unchanged (a `set`, with no reference count), and
**one** cleanup restores only the second setup's handler — the first displacement stays live, and the
handler in place afterwards is this module's own. With capture-once, that same sequence restores the
ORIGINAL pre-install value for both signals, and a following cycle re-captures the same original.
Overwrite-on-every-setup would store this module's own handler as "previous" and re-create the leak
the block exists to remove.

**3. The restore is `is`-guarded against a separately stored installed marker.** Selected: the
guard compares `signal.getsignal(sig) is not _installed_handlers.get(sig)` and skips. Three reasons,
in order of weight:

- *It is what makes "the two existing cases are UNCHANGED" literally true.* Under both existing tests
  the real process disposition is never displaced, so the guard reads "not ours", the restore is
  skipped, and — measured — **both cases make zero real `signal.signal` calls during cleanup**,
  exactly as today. The unconditional alternative makes two real (idempotent) installs per test; the
  return-value-capture alternative makes two real installs of a `MagicMock`.
- *It is the same discipline the runtime itself uses.* `asyncio.Runners.Runner.run()` restores
  `default_int_handler` only `if signal.getsignal(signal.SIGINT) is sigint_handler`, and arms
  `_on_sigint` only when SIGINT `is default_int_handler`. Copying that identity-guard idiom is
  rule 7, not a new concept.
- *It refuses to clobber a disposition this module no longer owns.* Verified: install, replace the
  handler with a third party's, cleanup — the third party's handler survives.

`_previous_handlers` and `_installed_handlers` are two different facts and must not be merged or
confused: the first is what was there before, the second is what was installed here. They are
declared adjacent, written in one place each, and cleared as one group at the end of
`cleanup_signal_handlers`, because a store that outlives a cycle is what makes the next cycle
re-use a stale value. The store is also what `B5` reads; the guard is on the *restore*, so `B5`'s
read is unaffected.

**4. The restore is hoisted out of the `if` / `else` split; the `else:` branch is deleted.** The
`if loop is not None:` branch keeps the loop-level `remove_signal_handler` attempt and its swallow —
it is correct where the loop supports it — and the process-level restore follows for **both**
branches, as one loop. Weighed against keeping the dead branch "honest": keeping it means two
`signal.signal` call sites, one of which would have to keep a value that is wrong for SIGINT, and a
reader could copy it. Deleting it makes the over-correction unrepresentable, and the branch's
comment changes from "reset signal handlers to default in non-async context" to the truth, which is
that the loop-level removal is unavailable and the process-level restore below is what takes effect.
On a platform where `add_signal_handler` succeeds the guard reads "not ours" and the loop's own
`remove_signal_handler` performs the restore — the same end state, and no worse than today.

**5. Docstrings.** Both become false the moment cleanup restores a process-level handler, so all
three are corrected in the same commit (plan §5.7, rule 14): `setup_signal_handlers`'s "Handlers are
loop-scoped and must be cleaned up after the async context exits", `cleanup_signal_handlers`'s
"Remove signal handlers and reset registration state", and the `# Track registered signals for
loop-scoped cleanup` comment above `_registered_signals`. Each must state that the displaced
process-level handler is captured per signal and restored per signal, and that the two values differ
so neither may be assumed to be `signal.SIG_DFL`. No new log record is added: the module's only
current record is the user-visible `shutdown_signal_received`, and a per-signal debug line on a path
that runs twice per download adds noise without adding a diagnostic the tests do not already give.

**6. How the tests prove it.** The oracle is **handler identity on the real `signal.signal`**,
because the two existing cases patch `signal.signal` wholesale and therefore cannot observe the
disposition at all. Three cases in the existing class, no new file: a per-signal restore
assertion; a two-setups-one-cleanup capture-once assertion; and a synchronous three-cycle
`asyncio.run` compounding oracle. Two properties of that layout are load-bearing and were measured:
each new case restores **both** pre-test dispositions in an unconditional `finally`, so a *failing*
fix produces exactly one red test instead of a suite whose every later `Runner` silently fails to arm
`_on_sigint`; and the compounding case is a **sync** test that calls `asyncio.run` itself, because
inside a pytest-asyncio async test the two cycles share one `Runner` and therefore one pre-install
object, and the "three distinct captures, each cycle ending at `default_int_handler`" oracle is only
observable across real `Runner` boundaries. That sync shape is also the configuration in which the
`_shutdown_event_ctx` token idiom is load-bearing, so the case uses it.

**The one thing the Implementor must not assume.** `signal.signal(sig, None)` is **not** a legal
no-op query on this interpreter — measured: `TypeError: signal handler must be signal.SIG_IGN,
signal.SIG_DFL, or a callable object`. A stored `None` is therefore never passed to `signal.signal`;
`signal.getsignal` returning `None` (never set from Python) means nothing was captured and there is
nothing to put back, so the capture does not store it and the restore's `previous is None` guard
returns. That guard is what keeps `TypeError` unreachable, so the `except` tuple stays
`(OSError, ValueError, RuntimeError)` and is not widened to swallow a programming error.

**Exposure to `B5` (`C4`).** `B5` consumes `_previous_handlers`: for route (a), the forward
escalation reads `_previous_handlers.get(signal.SIGINT)` and re-invokes that handler. The constraint
on `B5` is that the store is **empty between cycles** — `cleanup_signal_handlers` clears it — so a
forward route must read the captured value from inside a cycle in which `setup_signal_handlers()` has
run, and must handle the `.get()` miss. The value is a handler object, never an awaitable, and
invoking it is `B5`'s blocking-in-the-signal-context obligation, not this block's. This block does
not build that path.

---

### B4

```yaml
id: plan08-b4-browser-release-unconditional-and-non-replacing
title: Release the browser handle unconditionally and never let a release failure replace the exit
priority: high
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B4 — Release the browser handle unconditionally, and never let a release failure replace the failure that caused the exit
source_blocks: ["B4"]
source_findings: ["CON-004", "CON-005", "phase04/VAL-401"]

description: >
  BrowserManager.__aexit__ conditions browser.close() on the stop state NOT being set, so on the
  stop path — which _extract_with_browser takes routinely, raising CancelledError immediately
  after its stop check — exactly one of the two acquired resources is given back. And the two
  release steps catch only TimeoutError, so any other release failure propagates out of the exit
  and REPLACES the exception the async with body was unwinding. phase04/VAL-401: applying CON-004
  alone is a correctness REGRESSION on the path it fixes. Apply CON-005's suppression BEFORE OR
  WITH CON-004's unconditional release, IN ONE CHANGE.

goals:
  - browser.close() runs on the stop path as well
  - a release failure never replaces an exception already in flight
  - the release failure is logged with the reason the step failed
  - playwright.stop() still runs via the finally, always
  - the __aexit__ docstring stops claiming it checks the stop state before each step

files:
  - path: src/vkdownloader/infrastructure/browser.py
    targets:
      - type: method
        name: __aexit__
        class_name: BrowserManager
    semantic_anchors:
      insert_before:
        type: call
        value: asyncio.wait_for

  - path: src/vkdownloader/services/extractor.py
    targets:
      - type: function
        name: _extract_with_browser
    semantic_anchors:

  - path: tests/test_browser_infrastructure.py
    targets:
      - type: class
        name: TestBrowserManager
    semantic_anchors:

changes:

  - action: modify
    description: >
      Drop `and not shutdown_event.is_set()` from the guard so the close is unconditional. The
      10s _BROWSER_CLOSE_TIMEOUT bound already serves the reason the guard existed: a stop
      SHORTENS the close rather than skipping it. The bound is NOT removed and NOT lengthened.
    code_hint: |

  - action: modify
    description: >
      Widen each release step's `except TimeoutError:` to catch a release failure, log it with the
      reason the step failed using structlog key=value, and SUPPRESS IT WHEN AN EXCEPTION IS ALREADY
      IN FLIGHT. Preserve the finally guarantee exactly.
    code_hint: |

  - action: modify
    description: >
      Correct the __aexit__ docstring / INT-004 ownership note: it currently states the exit "checks
      the shared shutdown_event before each step"; the code guards only the first step. If the
      stop-state lookup becomes unused, decide EXPLICITLY whether to keep it with an updated inline
      reason or to remove it and its now-unused local. It must NOT be moved to module scope and no
      second lazy import may be added.
    code_hint: |

  - action: modify
    description: >
      RE-SCOPE, do not delete and do not weaken,
      TestBrowserManager::test_browser_manager_context_exit_stops_playwright_on_browser_close_error.
      Its pytest.raises AND its comment encode the defect. It must STILL assert playwright.stop()
      ran (the finally guarantee is real and preserved) and must ADD the new contract: with an
      exception in flight, the release failure is suppressed and the in-flight exception escapes.
    code_hint: |

  - action: add_test
    description: >
      (1) A close failure with NO exception in flight — the case the artifact does not decide.
      (2) THE MISSING CON-004 TEST: with the stop event SET, browser.close() is STILL invoked and
      playwright.stop() still runs. No test anywhere asserts this today.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT write a permanent-leak claim into the fix, the commit body, a docstring or a test
      docstring. The narrow consequence is: the graceful close is skipped, so the browser is torn
      down by driver shutdown rather than by the close path; if playwright.stop() exceeds its 10s
      bound the teardown is unbounded. Severity HIGH is unchanged.
    code_hint: |

acceptance_criteria:
  - With the stop event set, browser.close() IS invoked
  - A release failure with an exception in flight does NOT replace the in-flight exception, and the
    in-flight exception survives as __context__
  - playwright.stop() runs in every case — the finally guarantee is preserved and asserted
  - The re-scoped test asserts the NEW contract and still asserts the finally guarantee
  - test_browser_manager_context_exit, ::test_browser_manager_context_exit_handles_close_timeout and
    ::test_browser_manager_context_exit_handles_playwright_stop_timeout are green UNCHANGED
  - The __aexit__ docstring is accurate and INT-004 remains accurate
  - The lazy get_shutdown_event import is not moved to module scope; no second lazy import added
  - No claim about what a real Chromium does — verification uses stand-ins
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files
```

---

### B5

```yaml
id: plan08-b5-second-interrupt-escalates
title: Make a second interrupt escalate instead of being a no-op
priority: critical
depends_on:
  - plan08-b1-stop-observable-during-blocked-read
  - plan08-b2-segment-completion-helper-contract
  - plan08-b3-restore-displaced-signal-handler

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B5 — Make a second interrupt escalate instead of doing nothing
source_blocks: ["B5"]
source_findings: ["CON-001", "phase04/VAL-403"]

description: >
  _handle_signal is idempotent by construction, so a second Ctrl-C is a no-op — and the runtime's own
  handler that would raise KeyboardInterrupt was displaced at install and is not restored. Make the
  second interrupt escalate. SERIALISED BEHIND B2 BY phase04/VAL-403: the escalating interrupt never
  sets the stop state, and until B2 makes the cancellation propagate out of _await_and_cancel, an
  escalated interrupt makes every item return None, the batch report them FAILED, and the process
  exit 1 instead of the 130 the summary reserves for an interrupted run — on exactly the interaction
  the user was performing, and only on the second interrupt.

goals:
  - a second interrupt escalates; a third does not re-escalate
  - the escalation yields exit code 130, NOT 1
  - the first interrupt's observable behaviour is unchanged
  - no blocking work happens in the signal context

files:
  - path: src/vkdownloader/services/signal_handlers.py
    targets:
      - type: function
        name: setup_signal_handlers
    semantic_anchors:
      insert_before:
        type: if_statement
        value: not shutdown_event.is_set

  - path: src/vkdownloader/services/batch_downloader.py
    targets:
      - type: function
        name: _classify_download_result
      - type: function
        name: _run_batch_with_progress
    semantic_anchors:

  - path: tests/test_hls_downloader.py
    targets:
      - type: class
        name: TestSetupSignalHandlers
    semantic_anchors:

changes:

  - action: modify
    description: >
      DEFERRED TO THE BLOCK PLANNER, informed by an AUDITOR pass that re-derives the
      subprocess/signal interaction against the LANDED B1 and B3 code. Route (a): forward to the
      displaced handler — re-invoke the captured pre-install SIGINT handler, whose first action
      cancels the main task; smallest, reuses B3's state, but is exactly the cancellation B2 was
      absorbing. Route (b): force-kill the live child(ren); needs a live-child registry and
      scheduling onto the loop, but does not depend on B2's propagation. Route (c): forward then
      force-kill after a grace; largest surface, rule 5 penalises it hardest.
    code_hint: |

  - action: modify
    description: >
      If a live-child registry is required, decide its HOME. ffmpeg_utils.py already owns
      cancel_subprocess and is a LEAF, so a registry there adds no module edge. downloader_throttle.py
      would make ffmpeg_utils a non-leaf — FORBIDDEN. A new src/ module trips EXPECTED_SDIST_ENTRIES
      and needs justification against rule 5. The plan's default is NO new file.
    code_hint: |

  - action: add_test
    description: >
      (1) First fire sets the stop state and records exactly one event; second fire takes the
      escalation path; a third does not re-escalate. (2) An EXIT-CODE test driving the real
      classification chain (_classify_download_result to the summary's return) proving the
      escalation yields 130, not 1. This test is what phase04/VAL-403 exists to demand.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT do blocking work in the signal context — signal.signal handlers run on the main
      thread between bytecodes; schedule onto the loop instead. MUST NOT assume the child survives
      (a Windows console Ctrl-C also delivers CTRL_C_EVENT to child processes). MUST NOT move
      signal-handler REGISTRATION (ENT-004). MUST NOT reach into B2's code.
    code_hint: |

acceptance_criteria:
  - A second interrupt escalates and a third does not re-escalate
  - The first interrupt still sets the stop state and records exactly one shutdown_signal_received
  - The escalation reaches _print_batch_summary as a CANCELLATION and yields 130, not 1
  - The phase04/VAL-403 chain is re-verified in the report against the LANDED B2 code, step for step
  - TestBatchCancellationReporting stays green UNCHANGED, both halves
  - No blocking work in the signal context
  - The COMMIT BODY names SIX cancel_subprocess call sites, claims NO correlation-id obligation, and
    does NOT claim the R5(iii) leg is a defect
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files
```

---

### B6

```yaml
id: plan08-b6-bounded-segment-task-production
title: Bound the live segment-task set by the configured ceiling
priority: high
depends_on:
  - plan08-b2-segment-completion-helper-contract

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B6 — Bound the live segment-task set by the configured ceiling
source_blocks: ["B6"]
source_findings: ["CON-003"]

description: >
  _create_segment_download_tasks builds one asyncio.Task per missing segment inside a plain loop and
  returns the whole list. The claim that actually limits transfers is taken INSIDE the task body, so
  the live task set scales with input size rather than with the ceiling: measured 5000 tasks created
  up front under a ceiling of 4, with zero semaphore waiters queued at the moment of creation. Feed
  the work from a bounded producer instead of materialising the whole list.

goals:
  - the live segment-task set is bounded by settings.max_concurrent_downloads
  - every missing segment is still attempted and still reaches the merge
  - a stop terminates the producer and leaves no orphan tasks
  - D-01's non-reentrancy invariant is preserved and its comment stays accurate

files:
  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _create_segment_download_tasks
      - type: function
        name: _download_segment_concurrent
      - type: function
        name: _run_download_session
      - type: class
        name: DownloadPolicy
    semantic_anchors:
      insert_before:
        type: call
        value: policy.semaphore

  - path: tests/test_segment_downloader.py
    targets:
    semantic_anchors:

changes:

  - action: modify
    description: >
      DEFERRED TO THE BLOCK PLANNER on a shared RESEARCHER deliverable with B7 — the bounded
      task-production idiom (worker pool vs bounded queue vs a semaphore-wrapped producer) that
      preserves ordering, cancellation and per-item error reporting. The remedy changes HOW MUCH
      WORK EXISTS, not WHERE THE CLAIM IS TAKEN: `async with policy.semaphore:` stays inside the
      task body.
    code_hint: |

  - action: add_test
    description: >
      (1) The live-task-count measurement: N missing segments, ceiling C — live tasks stay at or
      near C, not N. Assert the BOUND, not the peak. (2) A correctness test that EVERY segment is
      still attempted and the results still reach the merge — a bounded producer that drops items is
      the obvious failure mode. (3) A stop test: a stop while the producer is still producing
      terminates it with no orphan tasks.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT add a new src/ or tests/ file. MUST NOT gate the segment fan-out on the batch
      semaphore — D-01: asyncio.Semaphore is not reentrant and the batch permit is acquired ONCE per
      video, never per segment. is_bounded_batch stays a boolean carried across; the segment layer
      keeps owning its own primitive. The per-transfer download_timeout bound and the post-acquire
      stop check are unchanged. The R5(iii) behaviour is NOT a defect and is not fixed here.
    code_hint: |

acceptance_criteria:
  - The live segment-task set is bounded by the configured ceiling
  - Every missing segment is still attempted and reaches the merge
  - A stop during production terminates the producer and leaves no orphan task
  - TestBatchDownloaderSemaphore::test_segment_layer_does_not_acquire_caller_video_semaphore and
    ::test_batch_completes_without_deadlock_when_max_reached are green UNCHANGED — no edits at all
  - D-01 is preserved and its comment is accurate
  - The report states how the bounded producer's output reaches B2's outcome type
  - The COMMIT BODY states the live-task bound achieved and does NOT claim the batch layer is bounded
  - No new src/ or tests/ file
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files
```

---

### B7

```yaml
id: plan08-b7-bounded-batch-task-production
title: Bound the live per-URL task set by the configured ceiling
priority: high
depends_on:
  - plan08-b2-segment-completion-helper-contract

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B7 — Bound the live per-URL task set by the configured ceiling
source_blocks: ["B7"]
source_findings: ["CON-003"]

description: >
  _run_batch_with_progress creates one task per URL in a list comprehension; the claim that limits
  videos is taken two frames deeper, inside perform_download. Measured with _download_single
  stubbed: 100 URLs -> 101 live tasks, 1000 -> 1001, 5000 -> 5001. The live set tracks input size, not
  the ceiling. Bound it. SERIALISED BEHIND B2 because B2 activates the
  `except asyncio.CancelledError` fan-out branch this producer must preserve.

goals:
  - the live per-URL task set is bounded by settings.max_concurrent_downloads
  - every URL is still attempted and still appears in the summary
  - the cancel-and-gather fan-out branch survives and the summary still returns 130
  - the reporter's start/stop lifecycle is unchanged

files:
  - path: src/vkdownloader/services/batch_downloader.py
    targets:
      - type: function
        name: _run_batch_with_progress
      - type: function
        name: _download_single
      - type: function
        name: _classify_download_result
      - type: class
        name: _TrackedSemaphore
    semantic_anchors:
      insert_before:
        type: call
        value: asyncio.as_completed

  - path: tests/test_batch_downloader.py
    targets:
      - type: class
        name: TestBatchDownloaderSemaphore
      - type: class
        name: TestBatchCancellationReporting
    semantic_anchors:

changes:

  - action: modify
    description: >
      DEFERRED TO THE BLOCK PLANNER on the SHARED B6 RESEARCHER deliverable — the same bounded
      production idiom, applied to a consumer that is materially different: as_completed fan-out,
      a cancel-and-gather branch, a reporter lifecycle, and a correlation id bound around the run.
    code_hint: |

  - action: modify
    description: >
      Re-read the comment stating that no await occurs between task creation and reporter.start().
      A bounded producer introduces an await or a producer task, so the invariant must be
      RE-DERIVED, not assumed, and the comment updated if it no longer holds.
    code_hint: |

  - action: add_test
    description: >
      (1) The live-task-count measurement: N URLs, ceiling C — live tasks bounded while EVERY URL is
      still attempted and still appears in the summary. (2) A stop test: a stop with URLs unstarted
      stops production, cancels what is in flight, and the summary still returns the documented
      interrupted result.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT remove or restructure the `except asyncio.CancelledError` fan-out branch — that is the
      route B2 makes live and the summary's 130 depends on it. MUST NOT add a new src/ or tests/ file.
      D-01 preserved. setup_signal_handlers / cleanup_signal_handlers / clear_correlation_id
      placement unchanged.
    code_hint: |

acceptance_criteria:
  - The live per-URL task set is bounded by the configured ceiling
  - Every URL is still attempted and still appears in the summary
  - The except asyncio.CancelledError fan-out branch is intact and the summary still returns 130
  - The reporter lifecycle is unchanged and its no-await-before-start comment is accurate
  - TestBatchDownloaderSemaphore::test_batch_completes_without_deadlock_when_max_reached and the
    whole of TestBatchCancellationReporting are green UNCHANGED
  - D-01 is preserved
  - The COMMIT BODY states the measured live-task bound before and after and does NOT claim the
    SEGMENT layer is bounded — that is B6
  - No new src/ or tests/ file
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files
```

---

### B8

```yaml
id: plan08-b8-transport-pool-ceiling
title: Derive the transport pool ceiling from the setting and give the per-origin ceiling a value
priority: medium
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B8 — Derive the transport pool ceiling from the setting and give the per-origin ceiling a value
source_blocks: ["B8"]
source_findings: ["CON-009"]

description: >
  _create_connector hard-codes limit=10 and never sets limit_per_host, so the per-origin ceiling is
  0 — unbounded. Neither value is derived from max_concurrent_downloads. Measured across the whole
  declared range and both ssl_verify values: four of four identical, identical from 1 to 16. One
  connector is created per download session, each paired with its own ClientSession, so the
  aggregate is per-download times downloads, and NO process-wide bound exists. Plan 07's B14
  deferred this literal here and carried the prohibition "MUST NOT touch _create_connector" — that
  prohibition is RELEASED by this block. Classified ADVISORY: the over-engineering risk is higher
  than the defect.

goals:
  - the connector's limit is derived from a declared setting, not a literal
  - limit_per_host carries an explicit value instead of being unbounded
  - no process-wide pool is introduced and no request rate is limited — those are other phases' subjects
  - if a setting is added it appears in all three places and its .env.example value is proven legal

files:
  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _create_connector
      - type: function
        name: _run_download_session
    semantic_anchors:
      insert_before:
        type: call
        value: aiohttp.TCPConnector

  - path: src/vkdownloader/config.py
    targets:
      - type: class
        name: Settings
    semantic_anchors:
      insert_after:
        type: field
        value: max_concurrent_downloads

  - path: tests/test_segment_downloader.py
    targets:
    semantic_anchors:

changes:

  - action: modify
    description: >
      DEFERRED TO THE BLOCK RESEARCHER then PLANNER — the remedy shape. (a) derive limit from
      max_concurrent_downloads and set an explicit limit_per_host — no new setting; rule 5 favours
      it and it is the plan's recorded DEFAULT. (b) add a new setting for the transport ceiling —
      real operator knob, but the three-place rule, extra="forbid" compatibility work, a .env.example
      value that must construct against the model, and guide prose, for an ADVISORY finding.
      (c) introduce a process-wide shared connector — a redesign, not a fix; out of scope by default.
      Rule 5 makes (a) the starting hypothesis.
    code_hint: |
      # before, four of four identical across the declared range:
      #   max_concurrent_downloads in {1,4,16} x ssl_verify in {True,False} -> limit=10 limit_per_host=0

  - action: modify
    description: >
      IF a setting is added or the meaning of max_concurrent_downloads changes, update its field
      description to name all THREE levels (batch gate, segment fan-out, transport ceiling) and add
      the new field to .env.example AND to docs/11-guides/configuration.md (table row AND prose
      section). extra="forbid" makes a missing entry an extra_forbidden error on upgrade.
    code_hint: |

  - action: add_test
    description: >
      A data-driven test reading the constructed connector across the declared range of
      max_concurrent_downloads and both ssl_verify values, asserting limit FOLLOWS THE SETTING and
      limit_per_host is the intended explicit value. Four-of-four-identical IS the defect — a test
      asserting limit == <a constant> would encode it. Plus a test asserting the AGGREGATE is the
      product the commit body claims, so the arithmetic cannot drift from the code.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT introduce a process-wide pool and MUST NOT limit the request RATE against one origin
      — the literal only; the rate is phase 03's. MUST NOT act on phase 03's NET-014 except through
      its store's VAL-001 adjudication, which ruled for CON-009. MUST NOT add a new src/ or tests/
      file. If a setting is added, no CLI option unless it is None-defaulted.
    code_hint: |

acceptance_criteria:
  - The connector's limit follows a declared setting; no literal 10 remains
  - limit_per_host carries an explicit, intended value
  - No process-wide pool exists and the block claims none
  - The block report states the arithmetic explicitly: per-download ceiling, the aggregate as
    10 x max_concurrent_downloads TODAY (40 at the default, 160 at the ceiling) and the NEW
    aggregate after the change, no process-wide bound
  - The report states the ownership handover from plan 07's B14
  - If a setting was added: it appears in the field description, .env.example and the configuration
    guide, and its .env.example value is CONSTRUCTED against the model and the construction recorded
  - The ssl_verify branch and its ssl_verification_disabled warning are preserved
  - No new src/ or tests/ file
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files
```

---

### B9

```yaml
id: plan08-b9-exit-path-thread-join-bound
title: State the exit-path thread-join bound where the timeout is configured
priority: medium
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B9 — State the exit-path thread-join bound where the timeout is configured
source_blocks: ["B9"]
source_findings: ["CON-010"]

description: >
  _extract_with_ytdlp bounds a synchronous yt-dlp extraction dispatched to the default executor
  with asyncio.wait_for(..., timeout=settings.download_timeout). On expiry the asyncio future is
  cancelled; the executor thread is not, and cannot be. asyncio.run then blocks on
  loop.shutdown_default_executor(asyncio.constants.THREAD_JOIN_TIMEOUT) while tearing the
  interpreter down — a silent stall AFTER the summary and the exit code have already been produced.
  THREAD_JOIN_TIMEOUT is 300, numerically identical to download_timeout's default of 300, which is
  why this is easy to miss. State the exit-path bound where the timeout is configured. Classified
  ADVISORY.

goals:
  - the bound actually applied on the exit path is stated where the timeout is configured
  - download_timeout's field description accurately names what it bounds
  - plan 07's C12 boundary on the configuration guide's download_timeout row is respected

files:
  - path: src/vkdownloader/config.py
    targets:
      - type: class
        name: Settings
    semantic_anchors:
      insert_after:
        type: field
        value: download_timeout

  - path: src/vkdownloader/services/extractor.py
    targets:
      - type: method
        name: _extract_with_ytdlp
        class_name: VKVideoExtractor
    semantic_anchors:
      insert_before:
        type: call
        value: loop.run_in_executor

  - path: tests/test_config.py
    targets:
    semantic_anchors:

changes:

  - action: modify
    description: >
      DEFERRED TO THE BLOCK RESEARCHER then PLANNER — whether a code remedy is justified AT ALL for
      an advisory finding. (a) documentation only: state the exit-path bound where the timeout is
      configured and stop; closes the finding's actual recommendation with zero runtime risk and is
      the plan's recorded DEFAULT. (b) a dedicated executor for this call site shut down with
      wait=False, so the abandoned thread is not joined; removes the stall's cap but introduces an
      executor lifecycle per extraction. (c) a shared long-lived executor; a module-level resource
      with a teardown obligation in a module that owns none. Rule 5 makes (a) the default; selecting
      (a) requires the report to state that the recommendation was met by documentation and that
      the residual stall is accepted, with the cap named.
    code_hint: |

  - action: modify
    description: >
      THE DOCUMENTATION LANDING SITE: Settings.download_timeout's Field(description=...). It today
      says only "HTTP client timeout ... for individual segment requests and playlist fetches",
      while it also bounds the local merge and the off-loop extraction. Name the exit-path bound and
      state that it is NOT the bound applied on the exit path.
    code_hint: |

  - action: add_test
    description: >
      If documentation-only: an assertion that the field description carries the exit-path bound. If
      a code change was selected: a behavioural test instead. The report states which it wrote and
      why.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT touch the download_timeout ROW of docs/11-guides/configuration.md — that is plan 07's
      C12 (its B11 then B15). MUST NOT act on CFG-002: it is MISATTRIBUTED in the artifact's
      cross-reference (phase 02's CFG-002 is about the post-construction max_retries override, is
      already fixed by ea44b3d, and no override exists in src/). MUST NOT raise a TimeoutError
      earlier or otherwise change what the operator is promised by download_timeout. No new src/
      or tests/ file.
    code_hint: |

acceptance_criteria:
  - The exit-path bound is stated where the timeout is configured
  - download_timeout's field description accurately names everything it bounds
  - docs/11-guides/configuration.md's download_timeout row is UNCHANGED, and the report says so
  - CFG-002 is not referenced as owning download_timeout
  - TestExtractionErrors::test_extract_with_ytdlp_no_info_raises_extraction_error and the whole of
    tests/test_config.py are green UNCHANGED
  - If documentation-only was selected, the report names the residual stall and the cap
  - No new src/ or tests/ file
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files
```

---

### B10

```yaml
id: plan08-b10-con002-verification-record
title: Record CON-002's verification outcome without code change, severity, or deletion
priority: medium
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B10 — Record CON-002's verification outcome without touching code or severity
source_blocks: ["B10"]
source_findings: ["CON-002", "phase04/VAL-410"]

description: >
  CON-002's severity cell reads `*none — not executed*`, which is outside the format's enum and which
  this validation phase may not correct: the only admissible substitute is LOW, which IS an observed
  severity and which 99-audit-validate.md `## 8` forbids. The finding may also not be deleted — the
  owning phase's binding rule W-4 requires the claim subject to be filed as exactly two findings.
  The structural fact is true and re-derivable: perform_download takes the per-video permit exactly
  once around the whole ladder, the segment layer builds its own semaphore, and the outer object
  crosses the boundary only as the boolean is_bounded_batch — so the registered D-01 nested-claim
  shape does not reproduce. But the PRODUCTION CONDITION was never executed, and the
  primitive-identity comparison is NOT proof of the condition's behaviour. Establish and record what
  is and is not known. NO CODE CHANGE.

goals:
  - a durable, auditable record of what is known and what is not
  - CON-002 remains filed, remains UNVERIFIED, and carries no severity
  - no product code changes at all
  - the outstanding VAL-410 corrections are recorded as not claimed, with their owner

files:
  - path: .ai/plans/done/01-confirmed-code-defects_DONE.md
    targets:
      - type: section
        name: D-01
    semantic_anchors:

  - path: src/vkdownloader/services/downloader.py
    targets:
      - type: function
        name: perform_download
      - type: function
        name: _semaphore_context
    semantic_anchors:

  - path: src/vkdownloader/services/segment_downloader.py
    targets:
      - type: function
        name: _run_download_session
    semantic_anchors:

changes:

  - action: add_code
    description: >
      Write ONE prose verification record under .ai/audit/99-validation/, named so it cannot be
      mistaken for a validation artifact — it MUST NOT wear the -validated-findings.md suffix. It
      lives outside src/ and tests/, so EXPECTED_SDIST_ENTRIES is unaffected. The record states, in
      order: (1) the structural fact, re-derived with SEMANTIC anchors and no line numbers;
      (2) that the PRODUCTION CONDITION — batch mode, videos in flight >= the ceiling, at least one
      video taking the segment path — was NOT executed against a live origin, and why;
      (3) that the primitive-identity comparison is NOT proof of the condition's behaviour;
      (4) that D-01 was FIXED (its Fix, Option A), which retires the "execute the production
      condition" half of the recommendation and leaves only the register-wording half;
      (5) that the register's Location list is stale, that correcting it is phase 09's subject by R-E,
      and that phase04/VAL-410's path correction is NOT CLAIMED by this plan;
      (6) that CON-002 remains filed, remains UNVERIFIED, and carries NO severity.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT change a single character of src/. MUST NOT assign a severity, and LOW in particular
      is FORBIDDEN. MUST NOT delete, merge or reclassify CON-002. MUST NOT close it on the
      primitive-identity observation. MUST NOT contain a verdict on the unexecuted condition —
      "safe" or "broken" is exactly the over-claim the validator warned against. MUST NOT touch
      .ai/audit/04-concurrency-cancellation/findings.md or the validated artifact — both must be
      byte-identical before and after (git diff --exit-code).
    code_hint: |

acceptance_criteria:
  - A durable prose record exists stating all six required points
  - git diff --exit-code proves src/, tests/, docs/ and .ai/audit/*/findings.md are unchanged
  - CON-002 is not deleted, not merged, not reclassified, and carries no severity
  - The record does NOT contain a verdict on the unexecuted production condition
  - The record names phase 09 as the owner of the stale register Location list and states that
    phase04/VAL-410's path correction is not claimed here
  - The COMMIT BODY cites CON-002 and phase04/VAL-410 (as not claimed) and states explicitly that
    no code changed and no severity was assigned
  - No test can see this change; the Validator's independent read is the gate
```

---

### B11

```yaml
id: plan08-b11-unverified-severity-encoding
title: Give the report format a legal encoding for a not-executed finding
priority: medium
depends_on: []

source_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B11 — Give the report format a legal encoding for a not-executed finding
source_blocks: ["B11"]
source_findings: ["phase04/VAL-404"]

description: >
  Two pipeline documents mandate an encoding the report format cannot express. The format fixes
  severity as CRITICAL|HIGH|MEDIUM|LOW and offers exactly four type labels. The phase handbook
  requires "an explicit UNVERIFIED marker, never with an observed severity", and its binding rule
  W-4 goes further — "The production trigger carries UNVERIFIED and no severity"; the validation task
  says the same at `## 8` and `## 12`. No type label admits an unverified observation, the phase
  files no DOC-UPDATE, and `## 8` forbids adding a fifth label. A conforming report must therefore
  write something the enum forbids. Phase 04's own CON-002 is the live instance: this validation
  had to leave an out-of-enum severity in place and file the format defect instead of correcting it.
  OWNERSHIP IS CLAIMED HERE; any future plan that would have carried phase04/VAL-404 must be struck.

goals:
  - a W-4-compliant report is legal against its own template
  - the template and the two pipeline documents agree
  - the change is prospective — no existing finding's severity or type is rewritten

files:
  - path: .ai/audit/templates/audit-findings.md
    targets:
      - type: section
        name: Template Field Reference
    semantic_anchors:
      insert_before:
        type: table_row
        value: severity

  - path: .kilo/commands/audit/phases/04-audit-concurrency-cancellation.md
    targets:
      - type: section
        name: W-4
    semantic_anchors:

  - path: .kilo/commands/audit/phases/99-audit-validate.md
    targets:
      - type: section
        name: Validation Rules
    semantic_anchors:

changes:

  - action: modify
    description: >
      DEFERRED TO THE BLOCK RESEARCHER then PLANNER — which of the artifact's two remedies is taken.
      (a) add a fifth severity member UNVERIFIED ("the structural fact is recorded; the runtime
      consequence was not observed") AND a fifth type label with the same meaning — one mechanism,
      matches what the three documents already demand, but adds a severity that is not a severity,
      so every place that ranks or counts severities must handle it. (b) state that UNVERIFIED
      findings are filed as LOW/BEST-PRACTICE with a mandatory marker field — no enum change, but
      the filing then carries an observed severity it did not earn, which `## 8` forbids, so that
      document must be amended too. The artifact states both are acceptable; this plan does NOT
      pre-select, because the blast radii differ materially across phases 01-11.
    code_hint: |

  - action: modify
    description: >
      Reconcile the phase handbook's UNVERIFIED requirement and binding rule W-4, and the validation
      task's `## 8` and `## 12`, with whatever the template now permits, so all three agree.
    code_hint: |

  - action: prohibited
    description: >
      MUST NOT change .kilo/rules/project.md — the structlog divergence is FLAGGED, not fixed.
      MUST NOT change .kilo/agents/* — VAL-409 is already fixed by e443448 and there is nothing here.
      MUST NOT change .ai/audit/04-concurrency-cancellation/findings.md: its out-of-enum cell is the
      EVIDENCE for this finding, and editing it would destroy the instance. MUST NOT change the
      validated artifact. MUST NOT retroactively rewrite any existing finding's severity or type,
      including CON-002's. The change is PROSPECTIVE.
    code_hint: |

acceptance_criteria:
  - The template can express a finding whose runtime consequence was not observed
  - The template, the phase handbook and the validation task agree
  - No existing finding's severity or type is rewritten anywhere
  - .ai/audit/04-concurrency-cancellation/findings.md and
    .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md are byte-identical
    before and after (git diff --exit-code)
  - .kilo/rules/project.md and .kilo/agents/* are untouched
  - The report states the ownership claim, so a future plan does not duplicate it
  - No test can see this change; the Validator's independent read is the gate
```

---

## §8 Verification strategy

### §8.1 The per-block gate — every block runs all four

No block is complete until all four of these pass, in this order, from the repository root.

| # | Command | Pass criterion |
|---|---|---|
| 1 | `uv run pytest -q -rs` | exit 0; the passed count has **risen** by the block's new tests and no test has been deleted or skipped to get there. |
| 2 | `uv run ruff check src tests` | exit 0 · `All checks passed!` |
| 3 | `uv run ruff format --check src tests` | exit 0 · all files formatted |
| 4 | `uv run mypy src` | exit 0 · `Success: no issues found` |

**Plus the block's own gate**, run by name:

```powershell
uv run pytest tests/test_hls_downloader.py -k "IterProcessLines" -q          # B1
uv run pytest tests/test_segment_downloader.py -q                            # B2, B6
uv run pytest tests/test_batch_downloader.py -q                              # B2, B7
uv run pytest tests/test_hls_downloader.py -k "SetupSignalHandlers" -q      # B3, B5
uv run pytest tests/test_browser_infrastructure.py -q                        # B4
uv run pytest tests/test_config.py -q                                        # B8, B9
uv run pytest tests/test_packaging.py -q                                     # only if a file was added
```

**Rules for a block report.**

1. Quote the **exact output** of all four commands. "Tests pass" without output is not a report.
2. **The passed count must not decrease.** A drop means a test was deleted, renamed without
   replacement, or skipped. **The four `D-11` Windows-confinement skips must remain exactly four.**
3. **List every test file and test name you edited**, with one line on why the edit was required by a
   behaviour change rather than by convenience. **Only `B4`'s re-scope is authorised.**
4. **Confirm no network was contacted.** `tests/test_packaging.py` is the only test that may, and it
   skips off-CI.
5. **Confirm the block's negative acceptance criteria** — the "byte-identical", "MUST NOT" and
   "no new file" items — with a `git diff --stat` on the named paths, not with an assurance.
6. **Record every deferred decision the block's Planner resolved**, with the option rejected and why.
7. **`git diff --cached --stat` before committing** (§2.4's landing rule). Every staged path belongs
   to this block. **Never `git add -A`, never `git add .`, never `git commit -a`.**
8. **If the gate hits the pre-existing `TestYtdlpProgressLineDetection` `NameError`**: record the
   flake, re-run the class in isolation, and do **not** edit that test file, do **not** touch the
   import, and do **not** attribute it to a `CON-*` finding. §2.4.
9. **Qualify every `VAL-` id** as `phase04/VAL-NNN` in the report and in the commit message.

### §8.2 The end-of-plan gate — after `B5` (or after the last block that runs)

| # | Gate | Pass criterion |
|---|---|---|
| 1 | All four baseline commands, in order | exit 0. Expected floor: **≥ 731 passed, 4 skipped** — the count may only rise. |
| 2 | `ruff check` · `ruff format --check` · `mypy` | exit 0, all three. |
| 3 | The re-scoped test group, re-run individually | `B4`'s test asserts its **new** contract, not a weakened one. Read the diff, not the exit code. |
| 4 | The four regression-net tests, re-run | `TestBatchDownloaderSemaphore`'s two cases and `TestBatchCancellationReporting` — green **and unedited**. |
| 5 | **No new file under `src/` or `tests/` outside `EXPECTED_SDIST_ENTRIES`** | `tests/test_packaging.py` green. |
| 6 | **No new `Settings` field missing from `.env.example` or the configuration guide** | Every new field appears in all three places and every `.env.example` value **constructs against the model**. |
| 7 | **`git diff` on the files other phases own** | `docs/11-guides/configuration.md`'s `download_timeout` row unchanged (`B9`); `.kilo/rules/project.md` and `.kilo/agents/*` unchanged (`B11`); `.ai/audit/04-concurrency-cancellation/findings.md` unchanged (`B10`, `B11`); the validated artifact unchanged (every block); the yt-dlp no-application-level-timeout docstring unchanged (`B1`); signal-handler registration placement unchanged (`B3`, `B5`); `read_progress`'s parameter unchanged (`B1`). |
| 8 | **No block implemented a withdrawn recommendation** | Grep the reports for: a permanent-leak claim; "told the download finished"; the R5(iii) leg as a defect; "only `on_shutdown` terminates the child"; a correlation-id obligation; a severity substituted for `CON-002`; a truthiness guard on `download_results`; a `SIG_DFL` reset for SIGINT; blocking work in a signal handler. **All nine must be absent.** |
| 9 | **Acronym hygiene** | No unqualified `VAL-` id in any commit message, block report or task id. |
| 10 | **No new-file regression** | `EXPECTED_SDIST_ENTRIES` untouched, or edited in the same change as an added file with the reason stated. |
| 11 | **The documented `130` still holds** | `docs/99-reference/cli-reference.md` unchanged; `B5`'s exit-code test proves `130` for an escalated interrupt. |

### §8.3 How "no new file without a frozenset edit" is enforced

**No block in this plan adds a `src/` or `tests/` file** (§2.3). If `B5`'s Planner concludes a live-child
registry needs its own module, then:

- `tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` is edited **in the same change**, or
- `tests/test_packaging.py` fails on the exact-entry-set assertion **and** on the
  exact-count assertion at `len(EXPECTED_SDIST_ENTRIES)` — which is why the count assertion exists.

A new **test** file is a packaging-gate edit too: the frozenset covers `tests/` as well as `src/`.
`B10`'s record lives under `.ai/` and is therefore outside the gate.

### §8.4 Per-finding verification trace

Every accepted finding and every claimed `phase04/VAL-` finding, mapped to the block that carries it
and the test that proves it.

| Finding | Block | Proving test / gate | Notes |
|---|---|---|---|
| `CON-001` leg 1 | **B1** | `tests/test_hls_downloader.py::TestIterProcessLines` — the blocked-read case (new) + the exactly-once assertion (extended) | All four existing cases green **unchanged**. `test_ytdlp_cancelled_on_shutdown_returns_none` green unchanged. |
| `CON-001` leg 2 | **B5** | `::TestSetupSignalHandlers` — second-fire escalation (new); the **exit-code** test proving `130` not `1` (new) | Serialised behind `B2`, `B1`, `B3` by `phase04/VAL-403`. |
| `CON-001` leg 3 | **B3** | `::TestSetupSignalHandlers` — per-signal pre-install restore (new); second-cycle re-capture (new) | Existing cases green unchanged. |
| `CON-002` | **B10** | *(no test — prose)* Validator gate: `git diff --exit-code` over `src/`, `tests/`, `docs/`, `.ai/audit/*/findings.md` | No code. No severity. Not deleted. |
| `CON-003` segment | **B6** | live-task-bound test (new); every-segment-still-attempted test (new); producer stop test (new) | `TestBatchDownloaderSemaphore`'s two cases green **unchanged** — the regression net. |
| `CON-003` batch | **B7** | live-task-bound test (new); every-URL-in-summary test (new); producer stop test (new) | `::test_batch_completes_without_deadlock_when_max_reached` and all of `TestBatchCancellationReporting` green **unchanged**. |
| `CON-004` | **B4** | stop-set-still-closes test (new) | **No test existed to re-scope** — only a missing one to add. |
| `CON-005` | **B4** | `::test_browser_manager_context_exit_stops_playwright_on_browser_close_error` — **re-scoped**; plus the no-exception-in-flight case (new) | The only confirmed pin in the plan. The `finally` assertion is preserved. |
| `CON-006` | **B2** | **the missing resume-case test** (new) — every segment present ⇒ the merge IS reached | `test_preserves_segments_on_segment_download_failure` must be **run and reported**, not assumed. |
| `CON-007` | **B2** | sibling-settle test (new) — no sibling pending after the raise | The commit body carries the **corrected** consequence. |
| `CON-008` | **B2** | cancellation-propagation test (new) | `::test_uninterrupted_failed_download_is_still_a_failure` green **unchanged**. |
| `CON-009` | **B8** | data-driven connector test across the declared range (new); aggregate-arithmetic test (new) | Research-gated; rule 5 makes option (a) the default. |
| `CON-010` | **B9** | `tests/test_config.py` — field-description assertion (documentation-only) or a behavioural test | `TestExtractionErrors` and all of `test_config.py` green unchanged. |
| `phase04/VAL-401` | **B4** | *Enforced as a grouping*, not a test: one commit covering `CON-004` **and** `CON-005`, plus criterion "a release failure does not replace an in-flight exception". | |
| `phase04/VAL-402` | **B2** | *Enforced as a grouping* plus criterion "the outcome is explicit at the type level and the consumer branches on identity, never truthiness". | |
| `phase04/VAL-403` | **B5** | *Enforced as `depends_on: [B1, B2, B3]`* plus the **exit-code** test. | |
| `phase04/VAL-404` | **B11** | *(no test — prose)* Validator gate: the three documents agree; two read-only paths byte-identical. | |

**Findings whose verification is a negative assertion** (no test can see them — the Validator's read
is the gate): `CON-002` (`B10`), `phase04/VAL-404` (`B11`), and every block's byte-identical /
`MUST NOT` / no-new-file criterion. Each is written as an explicit acceptance criterion for that
reason.
