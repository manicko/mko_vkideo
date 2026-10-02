# Plan 09 — Phase 04 Audit Fixes: Completion

**Source artifact (read-only, authoritative for *what* must change):**
`.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` (1359 lines, now **tracked**).
**Predecessor plan (read-only, authoritative for *how* B8–B11 were decomposed):**
`.ai/plans/08-concurrency-cancellation-audit-fixes.md` (3549 lines, **still untracked**).
**Scope:** the **four blocks plan 08 left open** — `B8`, `B9`, `B10`, `B11`. Plan 08's `B1`–`B7` are
**CLOSED and committed**; this plan does not re-plan, re-verify or re-order them.

**Tree state this plan was composed against:** branch `main`, **`HEAD = 0a8fa97`**
(`chore(audit): renumber audit reports to the 01-11 phase taxonomy`), sitting directly on
`7d02a30` (`fix(quality): complete the QualityEnum to QualitySpec migration`).

> **The tree moved twice while this plan was being written.** It moved once before planning
> (`7d02a30`: the quality-selection feature went from half-applied to committed) and **once during
> planning** (`0a8fa97`: the audit corpus went from untracked to tracked and committed). Both moves
> invalidated part of the inherited brief. §1.5 states exactly which plan-08 constraints died, which
> changed and which survive. **Every block re-runs §2.1 before it edits anything** — a baseline
> re-measurement is a block's first action, not an inherited fact.

**Coverage:** 2 product findings (`CON-009`, `CON-010`) + 1 verification-record finding (`CON-002`)
+ 1 pipeline finding (`phase04/VAL-404`), in **4 blocks**. Block ids are **inherited from plan 08 and
must not be renumbered**, which is why §3 is presented in execution order (`B8`, `B9`, `B11`, `B10`)
rather than id order.

> **Identifier convention — binding on every block, every block report, every task id and every
> commit message of this plan.**
> `VAL-` is a **colliding prefix**. Every per-phase validation run mints `VAL-001…` independently:
> `VAL-001`…`VAL-006` (phase 02), `VAL-001`…`VAL-007` (phase 03), `VAL-101`…`VAL-112` (phase 01),
> `VAL-401`…`VAL-410` (phase 04). **Every phase-04 `VAL-` id is written `phase04/VAL-NNN`.** An
> unqualified `VAL-4xx` in a block report, a commit message or a task id is a **defect** and must be
> rejected at review. `CON-` ids are unique to phase 04 and are written unqualified.

> **Nothing in this plan is anchored by line number.** Every target is a semantic anchor — a file, a
> module, a class, a function, a method, a field, a table row, a guard expression. The line numbers
> in the inherited brief were verified during planning and are recorded **here** as locators only, so
> a reader can check them once; **no block may depend on them.** The tree has already moved twice.

---

## §1 Scope

### §1.1 How this block set was derived

Plan 08 decomposed the artifact into 11 blocks. `B1`–`B7` are **closed** — `CON-001` (all three
legs), `CON-002`'s code half is untouched by design, `CON-003` (both layers), `CON-004`, `CON-005`,
`CON-006`, `CON-007`, `CON-008` are all committed. The committed lineage, newest first:

```
0a8fa97 chore(audit): renumber audit reports to the 01-11 phase taxonomy   <- third tree move; .ai/ only
7d02a30 fix(quality): complete the QualityEnum to QualitySpec migration     <- second tree move
0867b3f test(concurrency): add B7 batch live-task bounding test coverage     <- B7
268a99e fix(concurrency): bound the live batch task set by the ceiling       <- B7
d462ce4 fix(concurrency): bound the live segment task set by the ceiling    <- B6
82a3c09 test(signal-handlers): add B5 escalation test coverage
2ceb434 fix(concurrency): make a repeated interrupt escalate                <- B5
55f2ee6 fix(browser): release the handle unconditionally …                   <- B4 (CON-004+CON-005, VAL-401)
d7d5657 fix(concurrency): restore the process-level signal handler …        <- B3
f6ed0cf fix(concurrency): observe the stop while a child's output read …    <- B1 (CON-001 leg 1)
```

`phase04/VAL-401`, `phase04/VAL-402` and `phase04/VAL-403` were **ordering constraints**, not findings
with content, and all three are **discharged**: `VAL-401` by the single-commit `B4`, `VAL-402` by the
single-commit `B2`, and `VAL-403`'s prerequisite (`B2` before `B5`) by the fact that `2ceb434` landed
*after* `2f3543c`'s `B2` lineage despite plan 08 having ordered `B5` last. `phase04/VAL-405`…
`phase04/VAL-409` were closed by `d62671b`, `19143b1`, `8366964` and `e443448`;
`phase04/VAL-410` remains deliberately deferred (§1.4).

**Four findings remain open. Four blocks carry them, one each.** §3 justifies each grouping and
explicitly declines to split or merge.

### §1.2 IN — every remaining item

| Block | Findings | One-line goal | Why in this block | Plan that would otherwise carry it |
|---|---|---|---|---|
| **B8** | `CON-009` *(advisory · BEST-PRACTICE · MEDIUM)* | Derive the transport pool ceiling from the setting; give the per-origin ceiling an explicit value | The literal is byte-identical to `HEAD` and the defect is visible in the source; nothing needs re-deriving. It is the only remaining block that changes **runtime behaviour on the hot path**, so it goes first. | Plan 07 `B14` — deferred here, prohibition released |
| **B9** | `CON-010` *(advisory · BEST-PRACTICE · MEDIUM)* | State the exit-path thread-join bound where the timeout is configured | The only remaining block whose **remedy shape is genuinely unresolved** (documentation-only vs a code remedy) and which carries a **cross-plan ownership escalation**. Second so the escalation has lead time. | Plan 07 `B11`/`B15` (`C12`) — cross-plan, §9 Q1 |
| **B11** | `phase04/VAL-404` | Give the report format a legal encoding for a not-executed finding | The **largest blast radius in the plan** (five corpus files minimum, up to twenty-four if a fifth enum member is added). Placed after both advisory blocks so its retag is reviewed against a settled tree, and **before `B10`** so `B10`'s durable record can cite a landed mechanism. | — (plan 08 claimed it; this plan executes it) |
| **B10** | `CON-002` | Record `CON-002`'s verification outcome **without code change, without a severity, and without deleting the finding** | Zero code risk; content is a judgement about audit provenance. **Last** because its record must reflect the final state of the concurrency picture `B8` changes and must cite `B11`'s landed encoding. | — (plan 08 claimed it; this plan executes it) |

**2 advisory product findings + 1 record finding + 1 pipeline finding = 4 findings, 4 blocks, zero
findings unassigned, zero findings merged.**

### §1.3 OUT — and where each item went

| Item | Disposition | Where it went, and why |
|---|---|---|
| **`CON-001`, `CON-003`, `CON-004`, `CON-005`, `CON-006`, `CON-007`, `CON-008`** | **OUT — landed and committed** | `B1`–`B7`. **No block in this plan may re-verify, re-order or re-scope them.** The end gate (§8.2) confirms their tests are green; it does not re-litigate them. |
| **`phase04/VAL-401`, `phase04/VAL-402`, `phase04/VAL-403`** | **OUT — discharged** | Ordering constraints, enforced as plan 08's single-commit `B4`/`B2` groupings and the `B2`-before-`B5` landing order. **No block.** |
| **`phase04/VAL-405`…`phase04/VAL-409`** | **OUT — already fixed** | `d62671b`, `19143b1`, `8366964`, `e443448`. **No block.** |
| **`CON-002`'s severity cell** | **OUT — prohibited** | `*none — not executed*` **may not** be replaced with `LOW` or with any observed severity. **Binding on `B10`.** |
| **`CON-002`'s closure by the primitive-identity observation** | **OUT — prohibited** | The validator was explicit: "The structural identity comparison is not proof of the condition's behaviour." **Binding on `B10`.** |
| **`CON-009` as a *rate* finding** | **OUT — scope boundary, phase 03** | The request *rate* against one origin belongs to phase 03's `NET-014`, already adjudicated in `CON-009`'s favour by that phase's `VAL-001`. `B8` owns the literal and must become neither a rate limiter nor a pool. **Binding on `B8`.** |
| **`CFG-002`** as `CON-010`'s cross-reference | **OUT — misattributed, do not act** | Phase 02's `CFG-002` is about the post-construction **`max_retries`** override, is fixed by `ea44b3d`, and no override exists in `src/`. **Binding on `B9`.** |
| **`ENT-004`** (handler-registration *placement*) | **OUT — phase 01, deferred** | Plan 05 `D7`. No block in this plan touches signal handlers. |
| **`ART-002` / `ART-004` / `ART-012`** (filesystem residue, merge heuristic) | **OUT — phase 07** | `B9`'s exit-path discussion touches the merge timeout's reach; it must not change the residue or the `2×` heuristic. |
| **`ProgressManager` deprecation; the `structlog`/rule-12 divergence** | **OUT — flagged, not fixed** | Correcting `.kilo/rules/project.md` is an audit-pipeline change; changing the code to match the rule text would break the renderer split in `config.setup_logging`. **Binding on `B11`.** |
| **Test coverage for symbols with zero references** | **OUT — phase 10** | Blocks here add tests **for the finding they carry**, not for coverage's sake. The exception is `B8`, where `tests/` holds **zero** `aiohttp` references and the new test necessarily introduces the first — that is testing the finding, not chasing a metric. |
| **The `segment_downloader.py` / `downloader_throttle.py` exception-catch asymmetry** | **OUT of scope, but RECORDED and ESCALATED** | Measured, real, and it is **not** a phase-04 finding; phase 03 owns transport. `B8` *removes* its exposure but does not fix it. `B8`'s report must record it and §9 Q5 asks the Tech Lead whether to file it. |
| **`__all__`'s duplicate `_format_argfile` in `downloader.py`** | **OUT — pre-existing, harmless** | Recorded so a block that touches `downloader.py` (none do) does not mistake it for new. |
| **The suite's one `RuntimeWarning`** (`tests/test_downloader_throttle.py::TestProgressManager::test_overwrites_existing_progress`) | **OUT — pre-existing, unrelated** | Do not fix it in a concurrency block. **But its count is a gate**: §8.1 requires the warning count to stay at **1**. |

### §1.4 Deferred — explicitly not in this plan

| Deferred item | Owner / trigger |
|---|---|
| **`phase04/VAL-410` — correcting `CON-002`'s two path references from `.ai/problems/01-confirmed-code-defects.md` to `.ai/plans/done/01-confirmed-code-defects_DONE.md`, and recording that D-01 was *fixed* (its Fix, Option A), not merely unexecuted** | **Not claimed. Decision, stated once.** The primary target is `.ai/audit/04-concurrency-cancellation/findings.md`, which is **read-only for this engagement**. *Note the change:* that file is now **tracked** (`0a8fa97`), so the correction is no longer blocked by an untracked-file problem — it is blocked **only** by the read-only constraint. The second half — the archived register's own stale `Location` list — is phase 09's subject by R-E and the artifact says so. **Trigger:** a documentation plan explicitly allowed to edit `.ai/audit/*/findings.md` must correct both paths and record the Option A fix. `B10` **records that this correction is outstanding and does not perform it.** |
| The request *rate* against one origin, and any process-wide connection pool | **Phase 03's `NET-014`**, adjudicated in `VAL-001`'s favour of `CON-009`. `B8` owns the literal only. |
| **Whether the audit corpus being committed is authorised and permanent** | **§9 Q2.** `0a8fa97` committed the corpus, which converted this plan's read-only gate from vacuous to live. Nothing prevents a future `git rm --cached` from silently restoring the vacuity. |
| **Whether `.ai/templates/audit-findings.md` is retired or aligned** | **§9 Q3.** A second, unreferenced, structurally incompatible copy of the report template. `B11` edits only the authoritative one and records that the second is untouched. |
| **Whether `B11` may touch `.kilo/agents/*`** | **§9 Q4.** Plan 08's prohibition against it holds **only** under one of the two remedies. |
| **Filing the exception-catch asymmetry as a new finding** | **§9 Q5.** |
| Any change to `.kilo/rules/project.md` | **Flagged, not fixed.** Plan 08 §5.6's `structlog` decision carries forward verbatim. |
| `ENT-004` handler-registration placement | **Phase 01, plan 05 `D7`, DEFERRED.** |
| The `read_progress` `shutdown_event` parameter | **Deliberate and permanent** (`ffmpeg_utils.py` is a leaf). Its owning block landed. No block here may convert it to a module lookup. |

### §1.5 Plan 08 constraints: what survives, what changed, what died

**Read this section before planning any block.** Each row is a decision, not a preference.

| Plan 08 constraint | Status | Reason |
|---|---|---|
| §2.3 layering: `cli → services → infrastructure`; `ffmpeg_utils.py` is a **leaf**; `browser.py` holds **exactly one** function-scope lazy import; `downloader.py` is a **re-export facade** — every fix goes in the owning module | **SURVIVES** | No block touches `ffmpeg_utils.py`, `browser.py` or `downloader.py`. `B9`'s potential code remedy would live in `extractor.py` (an owning module), not the facade. |
| §2.3 `tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` is a hard gate; **no block adds a `src/` or `tests/` file** | **SURVIVES** | Verified: the frozenset now legitimately covers `models/quality.py` from the quality work. The *rule* is unchanged. `B8`'s new tests go into the **existing** `tests/test_segment_downloader.py`; `B9`'s into the existing `tests/test_config.py`. |
| §2.3 conftest `isolate_settings_source` is `autouse`; `test_settings` pins **`max_concurrent_downloads = 2`** | **SURVIVES, and is load-bearing for `B8`** | Verified at `tests/conftest.py:50`. A data-driven `B8` test across the declared range **must construct `Settings(...)` itself** — the fixture would collapse the whole matrix to one value. |
| §2.3 the `_shutdown_event_ctx` token idiom | **SURVIVES as a repository rule** | No block in this plan sets a stop state. Recorded so a block that later needs one uses the idiom rather than leaking a loop-bound `Event`. |
| §2.3 `Windows` facts: `ProactorEventLoop`, `add_signal_handler` raising `NotImplementedError`, `THREAD_JOIN_TIMEOUT = 300`, Ctrl-C also reaching children | **SURVIVES** | Measured again during planning: `asyncio.constants.THREAD_JOIN_TIMEOUT = 300`, `Python 3.12.1`, `Windows-10-10.0.17763-SP0`. `THREAD_JOIN_TIMEOUT` and `shutdown_default_executor` appear **nowhere** in `src/`; `loop.run_in_executor` has **exactly one** call site. `B9` is the block this binds. |
| §2.3 exit codes are documented: `130` = interrupted | **SURVIVES as an invariant** | No block changes an exit code. The end gate confirms `docs/99-reference/cli-reference*.md` are unchanged. |
| §2.4 **per-path staging discipline** — never `git add -A` / `git add .` / `git commit -a`; show `git diff --cached --stat` before committing | **SURVIVES — and is now the *only* landing defence** | See §2.4. |
| §2.4 "the working tree is dirty with an uncommitted quality-selection feature" | **DIED** | It is committed (`7d02a30`). `src/`, `tests/`, `docs/`, `README.md`, `.env.example`, `.kilo/`, `.gitignore` are **clean**. |
| §2.4 "the pre-existing `TestYtdlpProgressLineDetection` `NameError` flake" | **DIED** | 762 passed, 4 skipped, **1** warning. The class is green. The *rule* survives in weakened form: no block may edit that test file. |
| §2.5 test layout table | **SURVIVES, narrowed** | Only three rows are in play: `segment_downloader.py → tests/test_segment_downloader.py`, `extractor.py → tests/test_extractor.py`, `config.py → tests/test_config.py`. `tests/test_segment_downloader.py` grew by the quality work, so **class positions moved** — anchor by name. |
| §5.2(1) yt-dlp "no application-level download timeout" decision | **NOT APPLICABLE** | Its owning block landed. Carried as a **verification invariant**: `B8` touches `segment_downloader.py` and `B9` touches `extractor.py`; neither is that docstring. The end gate asserts it is unchanged. |
| §5.2(2) `D-01`'s non-reentrant-semaphore invariant | **SURVIVES — and gains a new reader** | Verified: `segment_downloader.py`'s `D-01` comment now also cites `CON-003` and describes the `B6` counting window. `B8` makes the setting a **third** bound; `B10` must **re-derive and record** it. |
| §5.2(3) the lying `INT-004` browser-exit comment | **DIED** | Corrected by `B4` (`55f2ee6`). |
| §5.2(4) `read_progress`'s `shutdown_event` parameter | **DIED for this plan** | Its owning block landed; no block here touches `ffmpeg_utils.py`. |
| §5.5 "a new `Settings` field changes nothing existing" | **CONDITIONAL** | Applies only if `B8` selects the new-setting option. |
| §5.5 "**`limit_per_host` becomes a real ceiling** … setting it explicitly **reduces** the achievable per-origin concurrency … a behavioural change on the hot path" | **FALSIFIED — do not carry forward** | The verified aiohttp rule is `min(limit, limit_per_host)`. With `limit_per_host == limit` the value is **provably non-binding**. Worse for plan 08's assumption: the aggregate ceiling **rises** at high settings (§5.6 H2). Plan 08's compatibility claim is wrong in **direction** and must not be repeated. |
| §5.6 the `structlog` trap — follow the code, not `.kilo/rules/project.md` rule 12's text | **SURVIVES** | **Binding on `B11`**, which edits `.kilo/commands/audit/*` and must not reach `.kilo/rules/`. |
| §5.8 the boundary: no block may claim what a real VK origin does; **no verification step may require network access** | **SURVIVES — binding on every block** | Verified: `tests/` contains **zero** `aiohttp` / `TCPConnector` / `ClientTimeout` / `ClientSession` references. `B8`'s new test introduces the first and must use a local stand-in. `B10`'s record must contain **no verdict** on the unexecuted condition. |
| **`B10`'s gate** — `git diff --exit-code` over two paths | **RESOLVED, then REHARDENED** | `0a8fa97` committed the corpus; both paths are now tracked and the gate is **live**. But it is now guarded by nothing. §8.1 replaces it with `git diff --exit-code HEAD -- <paths>` **plus** a `git ls-files --error-unmatch` assertion, so a future un-tracking cannot silently restore the vacuity. |
| **`B11` prohibition 2 — "no change to `.kilo/agents/*`"** | **CONDITIONALLY VOID** | Its stated ground is "`phase04/VAL-409` is already fixed by `e443448`; there is nothing here." That holds **only if no fifth `type` label is added**. Remedy (a) — which the artifact offers **first** and plan 08 deliberately did **not** pre-select — adds "a fifth type label with the same meaning". Under (a) the prohibition's reasoning fails and `.kilo/agents/*` becomes in-scope. **Whether phase 04 may touch role files that govern the whole agent estate is §9 Q4 — an escalation, not a block decision.** |
| **`B9` prohibition 2 — the guide's `download_timeout` row is plan 07's `C12`** | **JUSTIFICATION DEAD · DIRECTION SURVIVES** | Plan 07's `B11`/`B15` **never landed**: there is no composed `ClientTimeout` helper, and `sock_read=60` is still a literal at `downloader_throttle.py:239`, `segment_downloader.py:262` and `:614`. So `C12` has never touched the row and the row is **unowned in practice**. `B9` still does not touch it — and **escalates ownership instead of resolving it** (§9 Q1). |
| **Plan 08 §1.2 / §4: `B8`, `B9`, `B10`, `B11` all `depends_on: []`** | **CHANGED** | `B10` gains `depends_on: [B8, B11]`. `B8`, `B9`, `B11` stay at `[]`. |
| **Plan 08 §4.2 order: `… B8, B9, B10, B11, B6, B7, B5`** | **CHANGED for `B10`/`B11`** | This plan linearises `B8 → B9 → B11 → B10`. `B11` is moved **ahead of** `B10` so `B10`'s durable record cites a **landed** mechanism instead of a forward promise. Rationale at §4.2. |
| **Plan 08 §6: "5 blocks require a Researcher (`B6`, `B7`, `B8`, `B9`, `B11`)"** | **NARROWED** | `B6`/`B7` are landed. `B8`'s research is delivered and §6 rules it sufficient. **This plan requires 2 Researchers: `B9` and `B11`.** |

---

## §2 Baseline

### §2.1 The four verification commands — re-measured at `HEAD = 0a8fa97`

Re-run by the Planner against the live tree, not copied from any inherited record.

```
$ uv run pytest -q
762 passed, 4 skipped, 1 warning in 46.47s                              EXIT=0
$ uv run pytest -q                                    (re-run at 0a8fa97)
762 passed, 4 skipped, 1 warning in 35.26s                              EXIT=0

$ uv run ruff check src tests
All checks passed!                                                       EXIT=0

$ uv run ruff format --check src tests
54 files already formatted                                               EXIT=0

$ uv run mypy src
Success: no issues found in 31 source files                              EXIT=0
```

**Plan 08 §2.1's `731 passed, 2 warnings` is stale and must not be used.** The delta is the quality
work plus `B1`–`B7`'s tests.

- **The expected passed floor is 762 and the expected skip count is 4.** All four skips are the
  `D-11` Windows owner-only-confinement cases (`os.chmod` on Windows toggles only the read-only
  attribute, so the measured mode is `0o666`, not the requested `0o600`) — two in
  `tests/test_config.py`, two in `tests/test_hls_downloader.py`. **They are not a phase-04 subject and
  no block may change their count**, neither to hide a failure nor to tidy the number.
- **The expected warning count is 1**, and it is a different site from plan 08's two:
  `tests/test_downloader_throttle.py::TestProgressManager::test_overwrites_existing_progress`,
  `RuntimeWarning: coroutine 'Event.wait' was never awaited`. Pre-existing and unrelated to every
  `CON-*` anchor. **The count is a gate** (§8.1). *(The parenthetical reason plan 08 and §3 `B8`
  gave — that an unclosed connector adds its own warning — was **measured and falsified**; see
  §6.2. The gate is unchanged; only its mechanism was wrong.)*
- **The two hang guards plan 08's brief claimed were removed are INTACT**: `tests/test_hls_downloader.py`
  has `asyncio.wait_for(_drain(), timeout=5.0)` + `pytest.fail` at two sites, plus one
  `setup_signal_handlers` assertion; `tests/test_segment_downloader.py` carries four `pytest.fail`
  nets. **Do not carry the removal claim forward.** These are the regression net for anything `B8`
  touches in the segment layer.

**Working tree at `HEAD = 0a8fa97`:** `git status --short` → **14 entries, all under `.ai/`** —
eight tracked **deletions** (`.ai/plans/00_overview.md`, `01`–`04`, `VALIDATION_REPORT.md`,
`error_ref.md`, `.ai/audit/03-network-resilience/findings.md`), one modification
(`.ai/problems/PROBLEM.md`), and five untracked entries (`.ai/plans/05`–`08`, `tmp/`).
**`src/`, `tests/`, `docs/`, `README.md`, `.env.example`, `.kilo/`, `.gitignore` are CLEAN.**

### §2.2 Platform facts — binding on `B9`, recorded for `B8`

Measured on this machine during planning:

| Fact | Measured value | Where it binds |
|---|---|---|
| OS | `Windows-10-10.0.17763-SP0` | `B9` |
| Interpreter | CPython `3.12.1` (MSC v.1937, 64-bit) | all |
| Event loop | `asyncio.windows_events.ProactorEventLoop` | `B9` |
| **`asyncio.constants.THREAD_JOIN_TIMEOUT`** | **`300`** — numerically identical to `download_timeout`'s default | **`B9`**: the coincidence that hides `CON-010` |
| `THREAD_JOIN_TIMEOUT` / `shutdown_default_executor` in `src/` | **zero occurrences** | `B9` — the bound is documented nowhere |
| `loop.run_in_executor` call sites in `src/` | **exactly one** — `extractor.py`'s `_extract_with_ytdlp` | `B9` — `B9`'s fork is bounded to one site |
| `aiohttp` installed version | **`3.14.1`** | `B8` — the `min(limit, limit_per_host)` rule is verified against this version's `connector.py`; re-verify if the pin moves |
| `aiohttp.TCPConnector(...)` construction | requires a **running event loop** (`RuntimeError: no running event loop` when built synchronously) | **`B8`** — the new test **must** be `@pytest.mark.asyncio`, not a sync test |

### §2.3 Binding project rules — every block

| Rule | What it binds here |
|---|---|
| **1. English only** | Comments, log event names, docstrings, error text, the `B10` record, the `B11` prose. |
| **2. Production code is king** | No test in this plan pins defective behaviour. If `B8`'s new test fails against a *correct* implementation, the test is wrong. If `B9`'s fork selects a code remedy and the existing `test_extract_with_ytdlp_timeout_raises_extraction_error` (which patches `asyncio.wait_for` wholesale) blocks it, **fix the test**. |
| **3–4. Separation of concerns / single responsibility** | **`config.py` imports no `asyncio`** (verified: `difflib, logging, os, pathlib, structlog, dotenv, pydantic, pydantic_settings, models.enums`). It therefore **cannot compute `THREAD_JOIN_TIMEOUT`**; a description string is the only carrier. A `B9` remedy that imports `asyncio` into `config.py`, or that gives `extractor.py` an executor lifecycle, must justify the breach. |
| **5. Avoid overengineering** | **The single most load-bearing rule in this plan.** Both product findings are **`advisory`**: the over-engineering risk is *higher* than the defect. `B8` must resolve to the simplest option that closes the finding. `B9` may legitimately ship documentation only. |
| **6. Composition over inheritance** | `B9`'s potential executor is not a base class; `B8` adds no class. |
| **7. Follow existing patterns** | Dense decision-carrying comments (`D-01`, `INT-003`, `INT-006`, `CON-*`). Any behaviour change **must** update the tag comment that justifies the old behaviour. |
| **8. Meaningful, consistent naming** | `B8`'s chosen setting (if any) and `B9`'s bound name. |
| **9. Type safety** | `mypy` is on. **No `any`.** |
| **10. `StrEnum` for all constants** | `B8`'s new ceiling derivation is a *value*, not a named constant — if a block introduces a named outcome it is a `StrEnum` member. **Never a bare literal, never a dict.** |
| **11. Pydantic** | A new `Settings` field (only under one `B8` option) is `Field(default=…, ge=…, le=…, description=…)` and appears in **three** places. `model_config`'s `extra="forbid"` makes this correctness, not tidiness. |
| **12. No `print()`** | **Read the trap:** the rule's *text* prescribes stdlib `logging`; the codebase universally uses `structlog`. **Follow the code** (plan 08 §5.6). |
| **13. Migrations for schema changes** | Not applicable — no database. Recorded so no block looks for one. |
| **14. Documentation stays current** | `B8` (the setting's meaning gains a level) and `B9` (the field description). `docs/01-tools/vkdownloader-overview.md` gains its **first ever** mention of a transport connection ceiling. |
| **15. Small modules and functions** | No new module. `EXPECTED_SDIST_ENTRIES` is the enforcement. |

### §2.4 The landing rule — rewritten, because the dirty-tree premise is dead

**Plan 08 §2.4 is factually stale and its premise must not be reused.** The quality-selection feature
is committed. There is no dirty `src/`, no dirty `tests/`.

> **What survives: the per-path staging discipline. It is now the only landing defence.**
>
> 1. **A block's commit contains only its own work item.** Stage by **explicit semantic path**, never
>    `git add -A`, never `git add .`, never `git commit -a`. Before committing, the block report shows
>    `git diff --cached --stat` and confirms every staged path belongs to the block.
> 2. **The remaining working-tree delta is 14 entries and it is all `.ai/`, including eight tracked
>    deletions and a modification to `.ai/problems/PROBLEM.md`.** `git add -A` would sweep the deleted
>    `Mko-AINotify` plan files and the unrelated Russian batch-progress note into a phase-04 commit.
>    **This is the plan's largest process risk and it is now a purely mechanical one.**
> 3. **`.ai/audit/**` is read-only for this engagement**, and — as of `0a8fa97` — **tracked**. That
>    combination is what makes §8.1's read-only gate meaningful. `.ai/plans/**` is *not* read-only;
>    this plan file is the only `.ai/plans/**` file any block may write.
> 4. **The `TestYtdlpProgressLineDetection` flake is gone.** The rule survives in weakened form: no
>    block may edit that test file or attribute anything to it.
> 5. **`EXPECTED_SDIST_ENTRIES` is no longer pre-edited by uncommitted work** — it now legitimately
>    covers `models/quality.py`. §2.3's "no block adds a `src/` or `tests/` file" is unchanged.
> 6. **The tree has moved twice during planning.** Every block re-runs §2.1 as its first action and
>    records the observed numbers, rather than trusting this document.

### §2.5 Test layout — the file each block's tests go into

| Module under test | Existing test file | Note |
|---|---|---|
| `services/segment_downloader.py` | **`tests/test_segment_downloader.py`** | `B8`'s new connector test. Grew by the quality work — **anchor by class/test name, never by position.** Four `pytest.fail` hang nets already live here. |
| `services/extractor.py` | **`tests/test_extractor.py`** | `B9` only if a behavioural remedy is selected. |
| `config.py` | **`tests/test_config.py`** | `B9`'s field-description test. `Settings.model_fields[...]` metadata already has precedent here (four sites read it); **no test currently pins a `description=` string** — see `B9`'s §3 for why that matters. |

---

## §3 Execution blocks

Four blocks, presented in **linearised execution order**. Each is **one commit** and independently
verifiable against §2.1's four commands. **Read only the block you are handed** — §3 is
self-contained per block; §4 is needed only if you are scheduling.

---

### B8 — Derive the transport pool ceiling from the setting and give the per-origin ceiling a value

**Findings carried:** `CON-009` — **MEDIUM** · `BEST-PRACTICE` · **`advisory`**.

**Goal.** `TCPConnector`'s `limit` must be derived from `max_concurrent_downloads` rather than being a
literal, and `limit_per_host` must carry an explicit value instead of the aiohttp default `0`
(unbounded).

**Why alone, why first.** It is the only remaining block that changes **runtime behaviour on the hot
path**, and the only one whose new tests are behavioural. `B9`, `B11` and `B10` are documentation or
prose. Committing behaviour first means the two documentation blocks are reviewed against settled
code, and `B10`'s record can describe the final concurrency picture truthfully.

**What is measured (Planner-verified against `HEAD = 0a8fa97`).**
`services/segment_downloader.py`, function `_create_connector(settings, video_url) -> aiohttp.TCPConnector`:

```python
    if settings.ssl_verify:
        return aiohttp.TCPConnector(limit=10)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))
    return aiohttp.TCPConnector(ssl=ssl_context, limit=10)
```

Byte-identical to the audit's measurement. `limit=10` is a literal on **both** paths;
`limit_per_host` is passed on **neither**, so the aiohttp default `0` applies; no `resolver=` is
passed, so `DefaultResolver` applies. The sole call site is `_run_download_session`, which builds
**one connector per video** paired with its own `ClientSession` (`async with aiohttp.ClientSession(connector=connector)`);
teardown is delegated to the session. There is **no process-wide pool anywhere**.
`Settings.max_concurrent_downloads` is `default=4, ge=1, le=16`. Four concurrency levels exist and
the connector literal is the only one not derived from the setting. A fifth, out-of-process level:
`ytdlp_downloader.py` passes `-N str(settings.max_concurrent_downloads)` to the yt-dlp child, which
has its own sockets and never touches this connector.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `services/segment_downloader.py` | `_create_connector` — **both** `aiohttp.TCPConnector(...)` return paths | `limit` becomes derived, not literal. `limit_per_host` gains an explicit value. |
| `services/segment_downloader.py` | `_create_connector`'s `ssl_verify` branch, its `ssl_context` construction and its `ssl_verification_disabled` warning | **Preserved.** Only the ceiling arguments move. The `ssl` argument shape is unchanged. |
| `services/segment_downloader.py` | `_run_download_session` — the connector construction paired with its own `ClientSession`, and the segment-local `asyncio.Semaphore(settings.max_concurrent_downloads)` | **Read-only obligation.** One connector per download session ⇒ **the aggregate is per-download × downloads, not process-wide.** No process-wide bound exists and this block must not introduce one. |
| `services/segment_downloader.py` | the `D-01` comment above the segment semaphore | **Read-only obligation.** It states the fan-out is "bounded by a semaphore this layer owns, sized by the same `max_concurrent_downloads` setting" and now also cites `CON-003`'s counting window. Still true. **If the setting becomes a third bound, the comment must be re-read for accuracy and updated in the same commit.** |
| `config.py` | `Settings.max_concurrent_downloads`'s `Field(description=…)` | The description today enumerates **two** levels (batch gate + segment fan-out). The transport ceiling becomes a **third**, and the description must say so accurately. |
| `config.py` | a **new** `Settings` field, **iff** the chosen shape introduces one | Bounded (`ge`/`le`), a real `description`, and **three** places — field description, `.env.example`, `docs/11-guides/configuration.md` (table row **and** prose section) — because `extra="forbid"` turns a missing entry into `extra_forbidden` on upgrade. Any `.env.example` value must be **constructed against the model and the construction recorded**. |
| `docs/01-tools/vkdownloader-overview.md` | the concurrency prose that describes what the setting bounds (locator `:226`, and the related passage at `:289`) | The **first mention of a transport connection ceiling anywhere in `docs/`**. Verified: `docs/` contains **zero** occurrences of `TCPConnector`, `limit_per_host` or any connection-limit prose. (`ClientSession` appears only as a *parameter type* in `docs/01-tools/api-reference.md` — six sites, none about limits.) |
| `.env.example` | `VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS` | Only if a field is added. |

**Tests required**

- **ADD** — a data-driven test reading the **constructed connector** across the declared range of
  `max_concurrent_downloads` and both `ssl_verify` values, asserting `limit` **follows the setting**
  and `limit_per_host` is the intended explicit value.
  - **Four-of-four identical values IS the defect.** A test asserting `limit == <a constant>` would
    encode the defect.
  - **It must construct `Settings(...)` itself.** `tests/conftest.py`'s `test_settings` pins
    `max_concurrent_downloads = 2`; using the fixture collapses the matrix.
  - **It must be `@pytest.mark.asyncio`.** `aiohttp.TCPConnector(...)` raises
    `RuntimeError: no running event loop` when constructed synchronously (verified against
    `aiohttp 3.14.1`).
  - **It must close every connector it constructs** (`await connector.close()` or a session context).
    An unclosed connector emits its own warning and would move the suite's warning count off its
    baseline of **1** (§8.1).
  - **Read the public properties only.** `connector.limit` and `connector.limit_per_host` are
    public read-only properties (verified at runtime). **No private `_limit` / `_limit_per_host`
    access.**
  - Project conventions: `pytest.mark.asyncio`; plain classes, no base class; `unittest.mock` with
    fully-qualified dotted targets; `asyncio.wait_for(…, timeout=…)` + an explicit `pytest.fail`
    message around anything that could hang; assertions carry a diagnostic string.
- **ADD** — a test asserting the **aggregate is the product the commit body claims**, so the
  arithmetic cannot drift from the code.
- **MUST STAY GREEN UNCHANGED** — `tests/test_config.py` in full; the four existing `pytest.fail`
  hang nets in `tests/test_segment_downloader.py`; the four `D-11` skips.

**Dependencies:** `depends_on: []`. It blocks `B10` (§4.1 `C2`).

**Risk class: MEDIUM (advisory), and the only block here with real behavioural risk.** The defect is
real; the finding is `advisory`; **the over-engineering risk is higher than the defect.** Rule 5 is
the binding constraint. Two specific behavioural facts must be reported, not discovered by an
operator: the aggregate ceiling **falls** at the default and **rises** at the ceiling (§5.6 H2), and
the remedy **removes** a live queueing exposure (§5.6 H3).

**Prohibitions inherited and binding (negative acceptance criteria)**

1. **No process-wide pool and no rate limiter.** The literal only; the request *rate* against one
   origin is phase 03's `NET-014`.
2. **No new `src/` or `tests/` file.**
3. **Phase 03's `NET-014` is read *through* its store's `VAL-001` adjudication**, which ruled for
   `CON-009`. `B8` cites that adjudication.
4. **If a setting is added**: the three-place rule, an `.env.example` value **constructed against the
   model with the construction recorded**, and **no CLI option** unless it is `None`-defaulted.
5. **The `ssl_verify` branch, its `ssl_context` and its warning are preserved.**
6. **Neither `except` clause in the segment download path is widened.** The asymmetry at
   `segment_downloader.py` (catches `aiohttp.ClientError` **only**) versus the throttle path
   (catches `(aiohttp.ClientError, TimeoutError)`, with an `INT-006` comment that names the reason)
   is a **separate observation** (§9 Q5), not part of `CON-009`. Widening it inside `B8` would be an
   unrequested behaviour change on the same hot path.
7. **The report states the arithmetic explicitly**, in this shape — before *and* after, with both
   deltas, and with yt-dlp's out-of-process level excluded and named:
   - **Today** — per-download connector `limit = 10`, constant; per-origin `limit_per_host = 0`
     (unbounded). Effective per-video connections `min(10, N)`. **Aggregate `10 × N`** = 40 at the
     default `N = 4`, 160 at the ceiling `N = 16`. No process-wide bound exists.
   - **After** — per-download `limit = N`; per-origin `limit_per_host = N` (explicit, provably
     non-binding). Effective per-video connections `N`. **Aggregate `N × N`** = 16 at the default,
     256 at the ceiling. No process-wide bound exists.
   - **Excluded**: yt-dlp's connections — a separate child process with its own sockets, which never
     touches this connector. The honest aggregate is `N²` for the aiohttp segment path only.
8. **The report states the ownership handover** from plan 07's `B14` (whose prohibition — "MUST NOT
   touch `_create_connector`" — is released by this block) and that plan 07's blocks are landed.
9. **`limit_per_host` must not acquire a value that binds.** With `limit_per_host == limit` it is
   provably inert (`min(limit, limit_per_host)`). A "helpful" fraction would silently cut
   concurrency the operator asked for **and** smuggle in phase 03's rate subject, which prohibition 1
   forbids. The report must say the value is **intentionally** non-binding, so a later reader does
   not "fix" it.

**Decisions `B8`'s Planner makes, and the question each answers**

| Decision | Status | Note |
|---|---|---|
| The remedy shape (derive vs new setting vs process-wide pool) | **the block's Planner must record the selection and the rejected options** | A Researcher deliverable already exists and §6 rules it **sufficient** — but the deliverable **selects**, and this plan does not ratify a selection made outside a block report. The Planner confirms, records, and owns it. |
| The documentation landing site | **settled** | The setting's meaning changes ⇒ `config.py`'s description **must** be corrected, and `docs/01-tools/vkdownloader-overview.md`'s concurrency prose gains the first connection-ceiling mention. Not a fork. |
| Whether the block is documentation-only | **no — ruled out** | `CON-009` asks for an explicit `limit_per_host` value, which is a code change. |

---

### B9 — State the exit-path thread-join bound where the timeout is configured

**Findings carried:** `CON-010` — **MEDIUM** · `BEST-PRACTICE` · **`advisory`**.

**Goal.** The bound the interpreter actually applies when an abandoned off-loop extraction is joined
at teardown is stated where the timeout is configured — and, **if** a code remedy is justified, it is
applied at that call site.

**What is measured.** `extractor.py`, method `VKVideoExtractor._extract_with_ytdlp`, wraps
`loop.run_in_executor(None, _sync_extract)` in `asyncio.wait_for(…, timeout=self.settings.download_timeout)`.
On expiry the **asyncio future is cancelled; the executor thread is not, and cannot be.** `asyncio.run`
then blocks in `loop.shutdown_default_executor(asyncio.constants.THREAD_JOIN_TIMEOUT)` — measured
**300** — while tearing the interpreter down. `extractor.py` is the **only** `run_in_executor` call
site in `src/`, and `THREAD_JOIN_TIMEOUT` appears **nowhere** in `src/`. The consequence is a **silent
stall after the summary and the exit code have already been produced**.

**Two claims in the code lie, and both are in scope:**

1. `_extract_with_ytdlp`'s **docstring** says the `wait_for` wrap exists "so the event loop is not
   blocked indefinitely (INT-003)" — true of the *loop*, silent about the *process*.
2. The **`INT-003` comment** above the dispatch says the same.

**The third lie is outside this block's write set and belongs to `B8`'s read-only check:** `B9`'s
report must note that `download_timeout` also bounds **yt-dlp's `socket_timeout`** — both as a library
option in `extractor.py`'s options dict and as a CLI flag in `ytdlp_downloader.py`. So the setting
bounds **four** consumers, not the three the artifact named. **The field description must name
whatever the selected remedy leaves true**; if it names three of four, the description is still
lying.

**Semantic anchors owned**

| Module | Semantic unit | Change |
|---|---|---|
| `config.py` | `Settings.download_timeout`'s `Field(description=…)` | **The documentation landing site, and it is always in scope.** The description today reads *"HTTP client timeout in seconds for individual segment requests and playlist fetches."* It actually bounds the per-request segment/playlist HTTP, **each ffmpeg merge batch**, **the off-loop extraction's `wait_for`**, **and yt-dlp's `socket_timeout`**. State the exit-path bound and state that it is **not** the bound applied on the exit path. |
| `services/extractor.py` | `_extract_with_ytdlp` — the `asyncio.wait_for(loop.run_in_executor(None, _sync_extract), timeout=…)` and its `except TimeoutError` arm | **Documentation always; code change only if the fork resolves to one.** The `ExtractionError` message and the `ytdlp_extraction_timeout` record stay. |
| `services/extractor.py` | the `_extract_with_ytdlp` **docstring** and the **`INT-003`** comment above the executor dispatch | Both are corrected so they describe the loop-vs-process distinction accurately. |
| `docs/11-guides/configuration.md` | the `download_timeout` **table row** | **MUST NOT BE TOUCHED.** See prohibition 2 — the ownership question is escalated (§9 Q1), not resolved here. |
| `docs/11-guides/vkdownloader-limitations.md` | the existing yt-dlp executor-thread limitation passage (locator `:109`) | **Read-only.** Verify it stays accurate after the change; correct it only if the change makes it wrong, in the same commit. |

**Tests required — fork-dependent, and the block report states which it wrote**

- **If the documentation-only branch is selected:** a test in `tests/test_config.py` asserting the
  field description carries the exit-path bound.
  - **Constraint on how it asserts.** No test anywhere pins a `Field(description=…)` string, and
    pinning the whole string is a maintenance cost that fails on any reword — rule 5 applies to
    tests too. **Assert a stable semantic invariant, not the whole sentence**: that the description
    names the exit-path / thread-join subject, and that it does **not** claim the setting is the bound
    applied on the exit path. Prefer a narrow token over a full-string equality.
- **If a code-remedy branch is selected:** a **behavioural** test instead, and the existing
  `tests/test_extractor.py::TestExtractionErrors::test_extract_with_ytdlp_timeout_raises_extraction_error`
  — which currently patches `asyncio.wait_for` wholesale, so it sees only the `except TimeoutError`
  arm — may need re-scoping **because** the behaviour changed, **not** because it is inconvenient
  (rule 2).
- **MUST STAY GREEN UNCHANGED** — all of `tests/test_config.py` and all of `tests/test_extractor.py`
  on the documentation-only branch.

**Dependencies:** `depends_on: []`.

**Risk class: MEDIUM (advisory), LOW code risk, HIGH cross-plan collision risk.**

**Prohibitions inherited and binding**

1. **`CFG-002` is misattributed — do not act on it.** Phase 02's `CFG-002` is about the
   post-construction **`max_retries`** override, is fixed by `ea44b3d`, and no override exists in
   `src/`. `B9` must not re-derive or re-reference it.
2. **The configuration guide's `download_timeout` row is untouched.** Plan 08 attributed it to plan
   07's `C12`. **That attribution's prerequisite never landed** (§1.5), so the row is unowned in
   practice — but the direction of the prohibition is right and this plan does **not** resolve the
   ownership question. `B9` escalates it (§9 Q1) and **its report must say explicitly that the row is
   unchanged and that ownership is escalated, not decided.**
3. **No new `src/` or `tests/` file.**
4. **The fix must not be "raise a `TimeoutError` earlier"** or otherwise change what the operator is
   promised by `download_timeout`.
5. **`config.py` gains no import.** It does not import `asyncio` today, and importing it to compute
   `THREAD_JOIN_TIMEOUT` would breach rule 3. A description string is the only carrier — the report
   must say so.
6. **The report must name the residual stall and its cap if the documentation-only branch is
   selected**, and state plainly that the finding's recommendation was met by documentation and that
   the residual stall is **accepted**.

**Decisions `B9` explicitly does NOT make — the fork, flagged, not pre-selected**

**This block carries real technical uncertainty and this plan does not choose.** Three options, with
their honest trade-offs:

- **(a) Documentation only.** State the exit-path bound where the timeout is configured and stop.
  *Pro:* closes the finding's actual recommendation; zero runtime risk; no executor lifecycle. *Con:*
  the stall remains, up to the cap.
- **(b) A dedicated executor for this call site**, shut down so the abandoned thread is not joined by
  `loop.shutdown_default_executor`. *Pro:* removes the stall's cap. *Con:* an executor lifecycle per
  extraction; a real behaviour change to thread accounting; grows `_extract_with_ytdlp`'s
  responsibility (rule 4).
- **(c) A shared long-lived executor** for off-loop extractions. *Pro:* one executor, amortised.
  *Con:* a module-level resource with a teardown obligation, in a module that currently owns none —
  rules 3 and 4 push against it.

Plan 08 recorded (a) as its default under rule 5. **This plan relays that as a fact about the
predecessor and does not pre-select.** `B9`'s **Researcher** must additionally address the modern
idiom for bounding an abandoned `run_in_executor` job **and** whether `download_timeout`'s fourth
consumer (yt-dlp's `socket_timeout`) changes the answer. `B9`'s **Planner** then selects, records the
rejected options, and states the residual.

---

### B11 — Give the report format a legal encoding for a not-executed finding

> **SUPERSEDED IN PART by `§10 D10`. Read `§7 B11` — it is the executable specification.** The fork this
> section left open is **closed**: `D10` adopts the Researcher's remedy **(c) — no enum change**, so the
> edit set is **three files**, not fifteen or twenty-two. Three statements below are therefore **dead**
> and must not be acted on: (i) the "largest blast radius in the plan" and the twenty-two-file reach are
> **retired** — remedy (c) removes the sibling updates that were the risk; (ii) naming
> `99-audit-validate.md`'s `## Validation Summary` **action** table as a severity-counting surface is a
> **defect in this section** (`D10` item 7) — it is an **action** tally (Validated / Reclassified /
> Merged / Rejected / `VAL-`), **not** a severity surface, and the block must not edit it; (iii) the
> `UNVERIFIED` figures stated below are **superseded** by `D10` item 9 and do not reproduce — see
> `§7 B11`'s `extra_context` for the measured counts and why 141 and 205 are structurally unstable.
> What **survives** and still binds: ownership is claimed here; the change is **prospective**;
> `CON-002`'s cell is evidence and is never edited; `.kilo/rules/*` is never in scope; and the eleven
> sibling handbooks are not touched.

**Findings carried:** `phase04/VAL-404` — **MEDIUM** · `SPEC-DEVIATION` · **mandatory**.

**Goal.** `.ai/audit/templates/audit-findings.md` must be able to express a finding whose runtime
consequence was not observed, so a W-4-compliant report is not illegal by construction.

**Why claimed here, and why third.** It is the only `phase04/VAL-4xx` still open that is neither an
ordering constraint, nor already fixed, nor read-only-blocked. Phase 04's own `CON-002` is the
concrete live instance: the validation **had** to leave an out-of-enum severity in place and file the
format defect instead of correcting it. Plan 07's `B3` set the precedent that an audit-fixes plan may
edit a shared pipeline document after claiming ownership explicitly. **Ownership is claimed here; any
future plan that would have carried `phase04/VAL-404` must be struck.** Third because it is the
**largest blast radius in the plan** and should be reviewed against a settled tree — but **before**
`B10`, so `B10`'s durable record cites a landed mechanism.

**The defect.** The template fixes `severity ∈ CRITICAL, HIGH, MEDIUM, LOW` and offers exactly four
`type` labels. Three documents mandate an encoding the template cannot express:

| Document | The mandate, verbatim |
|---|---|
| `.kilo/commands/audit/phases/04-audit-concurrency-cancellation.md` — type guidance | *"…filed with the structural fact and an explicit `UNVERIFIED` marker, never with an observed severity"* |
| the same file — **binding rule W-4** | *"The **production trigger** carries `UNVERIFIED` and **no severity**."* |
| `.kilo/commands/audit/phases/99-audit-validate.md` — `## 8` | the same, and *"The four severity words are not redefined here, and this file adds no fifth."* |

**It is a corpus-wide convention, not a phase-04 quirk.** Verified during planning: `UNVERIFIED`
appears **64** times across `.kilo/**/*.md` (the single unrelated hit is
`.kilo/agents/researcher.md`, about web-search confidence) and **151** times across `.ai/**/*.md`, of
which **131** are inside `.ai/audit/**` and 20 inside `.ai/plans/**`. **Every one of the twelve phase
handbooks** (`01`…`11` and `99`) restates the mandate or the enum, not just `04` and `99`.

**The template's own internal surfaces a fifth member must touch:**

| Template semantic unit | Why a fifth member lands here |
|---|---|
| the skeleton field `| **Severity** | {severity} |` | The value it accepts must be able to hold the new state. |
| the `## Summary` severity-count table — **four hard-coded rows** (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`, each `| … | 0 |`) | A finding that is in none of the four buckets makes the tally not sum to the finding count. |
| the `## Template Field Reference` row `` | `severity` | enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | `` | The declared authority for the vocabulary. |
| the `## Template Field Reference` row `` | `type` | enum | `SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, `RUNTIME-ERROR` | `` | Same question, for the type label — **only** if the remedy adds one. |

**The identical enum restatement in the sibling handbooks** (each phase file states it in its own
wording; the `findings template is the authority` sentence is verbatim in all twelve):

`01-audit-entry-architecture.md` · `02-audit-config.md` · `03-audit-network-resilience.md` ·
`04-audit-concurrency-cancellation.md` · `05-audit-subprocess-browser.md` ·
`06-audit-credentials-secrets.md` · `07-audit-filesystem-artifacts.md` · `08-audit-cli-observability.md` ·
`09-audit-code-quality.md` · `10-audit-test-coverage.md` · `11-audit-supply-chain.md`

**Plus the severity-counting surfaces**, if the remedy adds a fifth member: the orchestrator's
counter initialisation and closing output (`audit-multi-phase.md`: `{CRITICAL_COUNT}`, `{HIGH_COUNT}`,
`{MEDIUM_COUNT}`, `{LOW_COUNT}`), and the validation task's `## Validation Summary` action table.

**Semantic anchors owned**

| File | Semantic unit | Change |
|---|---|---|
| `.ai/audit/templates/audit-findings.md` | the `## Template Field Reference` `severity` and `type` rows; the skeleton `Severity`/`Type` fields; the `## Summary` severity-count table; the classification guide | Add the encoding the pipeline documents mandate, **or** state the substitute rule. **This is the declared authority** — it changes **first**, always. |
| `.kilo/commands/audit/phases/04-audit-concurrency-cancellation.md` | the `UNVERIFIED` requirement and binding rule W-4 | Reconcile with the template so the two agree. |
| `.kilo/commands/audit/phases/99-audit-validate.md` | `## 8` and `## 12`, and — **if a fifth member is added** — the severity taxonomy table and the `## Validation Summary` counts | Same reconciliation. `## 8` currently says the file "adds no fifth", which a fifth member makes false. |
| **The other ten sibling phase handbooks** | their identical enum restatements and their `UNVERIFIED` mandates | **Reach depends entirely on the remedy** (§ below). Each file that states the four-member enum in its own words must agree with the template, or the pipeline contradicts itself across phases. |
| `.ai/audit/04-concurrency-cancellation/findings.md` | `CON-002`'s field table | **MUST NOT BE TOUCHED.** Its out-of-enum cell is the **evidence** for this finding. Editing it would destroy the instance and retro-fit the format to the answer. |
| `.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` | — | **MUST NOT BE TOUCHED.** The change is **prospective**. |

**Tests required:** none — prose. **The oracle is specified explicitly at §8.3**, because a
documentation block that governs the pipeline has no test and therefore needs a *mechanical* gate
rather than an assurance.

**Dependencies:** `depends_on: []`. It blocks `B10` (§4.1 `C3`).

**Risk class: MEDIUM (process), with the highest reach in the plan.** These are **shared** pipeline
documents governing phases `01`–`11` and every future phase. The risk is not the edit; it is an agent
over-reaching into `.kilo/rules/` or a role file while in there, or silently updating only the two
handbooks plan 08 named and leaving ten others asserting the old enum.

**Prohibitions inherited and binding**

1. **No change to `.kilo/rules/project.md`** — the `structlog` divergence is flagged, not fixed.
2. **No change to `.kilo/agents/*` — *conditionally*.** Plan 08's ground (`phase04/VAL-409` is fixed
   by `e443448`; there is nothing here) **holds only if no fifth `type` label is added.** Remedy (a)
   adds one, and under (a) the role files become **in-scope for consistency** — but whether phase 04
   may edit role files that govern the whole agent estate is **§9 Q4, an escalation**. Until that is
   answered, the prohibition **stands as written** and any role-file touch is a gate failure.
3. **No change to `.ai/audit/04-concurrency-cancellation/findings.md` or to the validated artifact.**
4. **No retroactive rewriting of any existing finding's severity or type**, including `CON-002`'s.
5. **The change is prospective.** It governs future reports.
6. **No change to `.ai/templates/audit-findings.md`** — the second, unreferenced, structurally
   incompatible copy. Editing it is not this block's job; retiring it is **§9 Q3**.

**Decisions `B11` explicitly does NOT make — the fork, flagged, not pre-selected**

**This block has the largest unresolved design question in the plan and this plan does not pre-select
it.** The artifact offers both remedies, deliberately, because their blast radii differ materially:

- **(a) Add a fifth severity member `UNVERIFIED`** — *"the structural fact is recorded; the runtime
  consequence was not observed"* — **and a fifth type label with the same meaning.**
  *Pro:* one self-describing mechanism; matches what twelve handbooks already demand, so they need
  **no** semantic change — only reconciliation of the enum restatements and the counting surfaces.
  *Con:* adds a severity that **is not a severity**; every place that ranks or counts must learn to
  handle it — the template's own four-row summary table, the orchestrator's four counters and closing
  output, the validation task's taxonomy table and `## Validation Summary`; and it **voids** plan 08's
  `.kilo/agents/*` prohibition, escalating to §9 Q4.
- **(b) State that `UNVERIFIED` findings are filed as `LOW` / `BEST-PRACTICE` with a mandatory marker
  field.** *Pro:* no enum change; the existing severity and type machinery is untouched; the marker
  carries the real information; the blast radius is three documents. *Con:* the filing then **carries
  an observed severity it did not earn** — which is exactly what `## 8` forbids — so `## 8` must be
  amended too, and the contradiction is preserved in a new place.

→ **`B11`'s Researcher** investigates how audit pipelines in general encode a not-executed observation
(this is the genuinely external question in the plan). **`B11`'s Planner** selects, and **must record
the full edit list before editing**, because the reach under (a) is up to **twenty-two files** and a
partial update across twelve phase handbooks is worse than no update.

**Sequencing rule inside the block:** the **template changes first, always** — it is the declared
authority and every sibling defers to it. The sibling-handbook and counting-surface reconciliation
follows, as a second sequenced step inside the same block. This block may be committed as **one commit
or an ordered set**, and the block's Planner decides and states which — **but it must not pre-split it
in this plan**, because the split depends on the remedy, which is open.

---

### B10 — Record `CON-002`'s verification outcome without touching code or severity

**Findings carried:** `CON-002` — severity cell reads **`*none — not executed*`** (out of enum, by
design) · `SPEC-DEVIATION` · **mandatory**. Related: **`phase04/VAL-410`** — *not claimed*.

**Goal.** Establish and record what is and is not known about D-01's production condition, so the
registered CRITICAL claim is not read as confirmed against this code — **without** changing product
code, **without** deleting the finding, and **without** giving it a severity.

**Why last.** Its content is a record of **final** state. `B8` changes what `max_concurrent_downloads`
bounds, and `B11` changes how a not-executed finding is encoded — a record written before either
would describe a state that no longer exists.

**What is actually left, precisely.** Three things were checked before deciding not to remove it:
(a) it **may not be deleted** — the owning phase's binding rule W-4 requires the claim subject to be
filed as *exactly two* findings, and states "The two are never merged and never omitted; under
`problems-only`, omitting either reads as 'no finding'"; (b) its **structural fact is true** and
re-derivable — `perform_download` takes the per-video permit exactly once around the whole ladder,
`segment_downloader.py` builds its own `asyncio.Semaphore(settings.max_concurrent_downloads)`, and the
outer object crosses the boundary only as the boolean `is_bounded_batch`, so the registered D-01
nested-claim shape **does not reproduce**; (c) it is **not a well-formed finding**, and this phase
cannot make it one — the out-of-enum cell cannot be corrected in place, because the only admissible
substitute is `LOW`, which **is** an observed severity and which `99-audit-validate.md` `## 8`
forbids.

**Semantic anchors owned**

| File | Semantic unit | Change |
|---|---|---|
| `.ai/plans/done/01-confirmed-code-defects_DONE.md` | D-01's summary entry, its section, and its **Fix, Option A** | **Read-only.** The block **cites** it as the authority for *what actually shipped*. This is the key fact `CON-002`'s recommendation got half right: the nested-claim shape is absent because **Option A was implemented**, not merely because the condition was never exercised. |
| `src/vkdownloader/services/downloader.py` | `perform_download` — the single per-video permit, taken once around the whole ladder — and `_semaphore_context` | **Read-only.** Re-derive the structural fact against the live code with **semantic** anchors and record it. |
| `src/vkdownloader/services/segment_downloader.py` | `_run_download_session` — the segment-local `asyncio.Semaphore`, and the `is_bounded_batch` boolean it carries and consumes; plus the `D-01` comment `B8` may have amended | **Read-only.** Same. **Read this after `B8` lands**, because `B8` may change what the comment says the setting bounds. |
| `src/vkdownloader/config.py` | `Settings.max_concurrent_downloads`'s field description | **Read-only.** Read it **after `B8` lands** — the description will name a third level. Verify it is accurate and record that. |
| **A new prose verification record** under `.ai/audit/99-validation/` | `CON-002`'s verification | **The block's only write.** Prose only. |

**The write surface — decision, carried forward from plan 08 and still correct.** The finding **may
not be deleted**, its severity cell **may not be corrected**, and both the source report and the
validated artifact are **read-only**. The durable record must go somewhere writable that is neither.
**Decision: exactly one new prose file under `.ai/audit/99-validation/`, named so it cannot be mistaken
for a validation artifact** — it **must not** wear the `-validated-findings.md` suffix, which is the
pipeline's artifact convention. It is outside `src/` and `tests/`, so `EXPECTED_SDIST_ENTRIES` is
unaffected.
*Alternatives considered and rejected, once:* (i) record it only in the block report — not durable,
not auditable, and the finding would look resolved with no evidence; (ii) edit `.ai/problems/PROBLEM.md`
— it is in the working-tree delta and the register it names does not exist at the cited path
(`phase04/VAL-410`); (iii) edit the source report — **read-only**.

**The record must state, in this order:**

1. The structural fact, re-derived against the live code with **semantic** anchors and **no line
   numbers**.
2. That the **production condition** — batch mode, videos in flight ≥ the ceiling, and at least one
   video taking the segment path — was **NOT executed** against a live origin, and why (no network
   access in this engagement; §2/§5.8's boundary). **No inference about what a real origin would do.**
3. That the **primitive-identity comparison is not proof** of the condition's behaviour — the validator
   was explicit, and the block must not quietly close the finding on it.
4. That **D-01 was fixed** (its Fix, Option A), which **retires** the "execute the production
   condition" half of `CON-002`'s recommendation and leaves only the register-wording half.
5. That the register's own **Location** list is stale, that correcting it is **phase 09's** subject by
   R-E, and that **`phase04/VAL-410`'s path correction is not claimed by this plan** (§1.4).
6. That `CON-002` **remains filed, remains `UNVERIFIED`, and carries no severity** — and that
   `phase04/VAL-404`'s block (`B11`) is what gives that state a legal encoding. **Cite `B11` by its
   block id and title, not by asserting its remedy** — this record is durable and must not contain a
   forward promise (§4.2).

**Tests required:** none. There is no test that can see a `.md` file. **The oracle is specified
explicitly at §8.3** — for this block it is a *negative* one: no product file may change.

**Dependencies:** `depends_on: [B8, B11]`. `B8` first so the re-derived structural fact describes the
final state; `B11` first so the durable record cites a landed mechanism. Neither is a *code*
dependency; both are **record-accuracy** dependencies, and that is the whole point of the ordering.

**Risk class: LOW (code) / MEDIUM (process).** The risk is an agent under gate pressure "fixing" a
finding whose entire content is *that it was not verified*.

**Prohibitions inherited and binding**

1. **No code change. Not one character of `src/`.**
2. **No severity is written, and `LOW` in particular is forbidden.**
3. **The finding is not deleted, merged, reclassified, or given a severity.**
4. **The primitive-identity observation does not close it.**
5. **No claim about what a real VK origin or a real batch would do.** The record contains **no
   verdict** on the unexecuted condition — neither "safe" nor "broken".
6. **`.ai/audit/04-concurrency-cancellation/findings.md` and the validated artifact are byte-identical**
   before and after. **Both are now tracked**, so this is a real gate, not a vacuous one.
7. **The record is exactly one file.** Not a directory, not a set.

**Commit shape.** One prose commit, citing `CON-002` and `phase04/VAL-410` (as *not claimed*). The body
states the outcome and, explicitly, that **no code changed and no severity was assigned**.

---

## §4 Dependency graph, linearised order, conflict matrix

### §4.1 The graph

```
        ┌──────────────────────────────────────────────────────────┐
        │  WAVE 0 — no dependencies (3 blocks)                     │
        │                                                          │
        │   B8  CON-009   transport pool ceiling      ──┐           │
        │   B9  CON-010   exit-path thread-join bound   │           │
        │   B11 phase04/VAL-404  format encoding      ──┼──┐        │
        └───────────────────────────────────────────────┼──┼────────┘
                                                        │  │
        ┌───────────────────────────────────────────────┼──┼────────┐
        │  WAVE 1 — record accuracy (1 block)                │        │
        │   B10 CON-002  verification record  ← B8, B11 ─────┘        │
        └────────────────────────────────────────────────────────────┘
```

**Formal edges (4 blocks, 2 edges):**

| From | To | Conflict | Why |
|---|---|---|---|
| `B8` | `B10` | `C2` | `B10` must **re-derive and record** the structural fact from `Settings.max_concurrent_downloads`' description, from `segment_downloader.py`'s `D-01` comment, and from the segment semaphore. **`B8` amends the first two.** A record written against the pre-`B8` description describes a two-level setting that no longer exists. |
| `B11` | `B10` | `C3` | `B10`'s required statement (6) says `B11` is what gives `CON-002`'s state a legal encoding. If `B10` lands first, that sentence is a **forward promise in a durable artifact**. If `B11` lands first, it is a **checkable statement about a landed, named mechanism**. |

**Acyclicity proof.** `rank(B8) = rank(B9) = rank(B11) = 1`; `rank(B10) = 2`. Both edges strictly
increase the rank (`1 → 2`), so no cycle can exist: a cycle would require a non-increasing step around
the loop, and there is none. `B9` is an isolated vertex. **The graph is a DAG.** A topological order is
`B8, B9, B11, B10`, and any order consistent with the rank assignment is valid.

**Both edges are record-accuracy edges, not code edges.** No block waits for another to *compile*.

### §4.2 The linearised order, and the reason for each position

Three blocks are unconstrained; one is constrained by two edges. The order below is the
**recommended** sequence, not a dependency chain. Execution is **sequential with one Implementor at a
time** — the blocks share `config.py`, share review attention on two `advisory` findings, and the
documentation blocks are cheap enough that parallelising them buys nothing.

| # | Block | Why here |
|---|---|---|
| 1 | **`B8`** `CON-009` | The only block that changes **runtime behaviour on the hot path**. First, so behaviour is committed while the tree is quietest and the three documentation blocks are reviewed against settled code. Also the highest-value research *already exists*, so its lead time is zero and it can start immediately. |
| 2 | **`B9`** `CON-010` | Second because it is the other `advisory` block, because its **cross-plan ownership escalation needs lead time** (§9 Q1 — the Tech Lead should be asked while `B8` is landing), and because it is the block most likely to resolve **to documentation-only**, which is cheaper to discover before two prose blocks are committed. |
| 3 | **`B11`** `phase04/VAL-404` | Third: the **largest reach** (five files minimum, up to twenty-two), so it is reviewed against a fully settled tree. But **before `B10`**, so `B10`'s durable record cites a landed mechanism rather than a promise. **This reverses plan 08's `B10`-then-`B11` order deliberately**, and it is the one ordering this plan changes from its predecessor. |
| 4 | **`B10`** `CON-002` | Last. Pure prose, zero code risk, and its content is a record of **final** state — it must describe the concurrency picture `B8` produced and cite `B11`'s landed encoding. |

### §4.3 Conflict matrix — every pair sharing a semantic anchor

`C1`–`C6`. **Semantic names are the key; line numbers are only historical locators and are
deliberately absent from every task specification.**

| # | Findings · blocks | **Shared semantic anchor** (semantic key) | Nature | Resolution |
|---|---|---|---|---|
| **C1** | `CON-009` ↔ `CON-010` · **B8 ↔ B9** | `config.py` → `Settings`: two adjacent **field descriptions**; and `docs/11-guides/configuration.md`: two adjacent rows and two prose sections | **File co-location, disjoint hunks.** Different fields, different rows, different prose sections. | **No edge.** The per-block file lists must name the **field**, not the file, when stating what may be edited. The end gate (§8.2) diffs both hunks. Neither block may re-read the other's field as licence to edit it. |
| **C2** | `CON-009` ↔ `CON-002` · **B8 → B10** | `Settings.max_concurrent_downloads`'s `Field(description=…)`; the `D-01` comment above the segment semaphore; the segment-local semaphore itself | **Record accuracy.** `B8` **amends** the text `B10` must **cite as accurate**. | **Edge: `B8` first.** `depends_on: [B8, B11]`. `B10`'s report must state which `B8` amendments it observed. |
| **C3** | `CON-002` ↔ `phase04/VAL-404` · **B11 → B10** | The not-executed encoding itself: `CON-002`'s out-of-enum severity cell, the `UNVERIFIED` marker, the template's severity vocabulary | **Narrative accuracy.** `B10` writes the record; `B11` changes the vocabulary that record describes. | **Edge: `B11` first.** `B10` cites `B11` by block id and title, never by asserting its remedy. |
| **C4** | `CON-009` ↔ `CON-010` · **B8 ↔ B9** | Not an anchor — a **finding class**: both are `advisory` / `BEST-PRACTICE`, both carry rule 5 as their binding constraint, and both face the same "documentation or code?" question | **Grouping hazard, not an anchor conflict.** The over-engineering risk is higher than the defect in both, and a reviewer who has calibrated on one will have the wrong prior for the other. | **No edge; a shared review question at the end gate:** for each, "is the code change the simplest option that closes the finding, and is the residual stated?" |
| **C5** | `CON-010` ↔ plan 07 `B11`/`B15` (`C12`) · **B9** | `docs/11-guides/configuration.md`'s `download_timeout` **row**, and `Settings.download_timeout`'s `Field(description=…)` | **Cross-plan, with an unlanded prerequisite.** Verified: plan 07's `B11`/`B15` never landed (no composed `ClientTimeout` helper; `sock_read=60` is still a literal in three places), so `C12` never touched the row and the row is **unowned in practice**. | **Prohibition: `B9` does not touch the row** and **escalates ownership rather than resolving it** (§9 Q1). `B9`'s report says so explicitly. |
| **C6** | `phase04/VAL-404` ↔ `.kilo/agents/*` and ↔ `.ai/templates/audit-findings.md` · **B11** | The **type-label vocabulary** in the role files (`.kilo/agents/auditor.md`, `validator.md` — four label lists each) and a **second, structurally incompatible copy of the report template** | **Two conditional reaches**, both contingent on the open remedy. Plan 08's `.kilo/agents/*` prohibition is void under remedy (a). | **The prohibition stands until §9 Q4 is answered**; any role-file touch before then is a gate failure. The second template is **out of scope by prohibition 6** and escalated (§9 Q3). |

### §4.4 Every grouping changed from the artifact's own finding order, and why

The validated artifact publishes **no numbered fix list**. Its ordering content is (i) the finding
order `CON-001` … `CON-010` then `VAL-401` … `VAL-410`, and (ii) **`Checkpoint 4 — R4 Assess
Rollout Safety`**, which records *circular dependencies: 0*, *unsafe-ordering pairs: 3*, *hidden
chains: 2*, *blockers: none*.

| Artifact's finding order | This plan | Why it changed |
|---|---|---|
| `CON-002` second | **`B10` last** | It has **no code change**, so position is free — but its *content* is a record of final state. Plan 08 put it ninth of eleven for the same reason; here it goes last because only four blocks remain and two of them change what it records. |
| `CON-009` ninth | **`B8` first** | Plan 08 deferred it behind the six product blocks because it was advisory. Those are landed. It is now the **only** block with runtime behaviour, so it leads. |
| `CON-010` tenth | **`B9` second** | Unchanged in spirit from plan 08 (advisory, research-gated, cross-plan collision) — it simply inherits the second slot now that the product blocks are gone. |
| `VAL-404` last of the pipeline findings | **`B11` third of four** | Plan 08 put it last for blast-radius reasons. This plan keeps it late but moves it **ahead of `B10`**, because `B10` cites it and a durable artifact should not carry a forward promise. |
| `VAL-401` … `VAL-410` as findings | **Enforced, closed, or not claimed** | `401`/`402`/`403` discharged by landed commits; `405`…`409` closed by `d62671b`, `19143b1`, `8366964`, `e443448`; `404` claimed here; `410` **not claimed** (§1.4). All remain traceable through §4.3 and §8.4. |
| "Fix Order" as such | **`B8 → B9 → B11 → B10`** | Driven by the two edges in §4.1 and by risk: behaviour first, then advisory-with-escalation, then largest blast radius, then zero-code-risk record last. |

---

## §5 Risks

### §5.1 The test-pinning risk

Plan 08's confirmed pin (a `pytest.raises` that encoded `CON-005`'s defect) **landed and was
re-scoped inside `B4`**. No test in this plan pins defective behaviour. Two residual risks remain:

| Block | Test / surface | What it pins | Disposition |
|---|---|---|---|
| **B8** | `tests/test_segment_downloader.py`'s four `pytest.fail` hang nets and the two `asyncio.wait_for(_drain(), timeout=5.0)` guards in `tests/test_hls_downloader.py` | That a regression in the segment layer **fails instead of hanging** | **Must stay green unchanged.** These are the regression net for the module `B8` edits. (The brief's claim that they had been removed is **false** and is not carried forward.) |
| **B8** | `tests/test_config.py` in full | The `Settings` model, including `extra="forbid"` and the `max_concurrent_downloads` bounds | **Must stay green unchanged.** If `B8` adds a field, this is where `extra_forbidden` bites. |
| **B9** | `tests/test_extractor.py::TestExtractionErrors::test_extract_with_ytdlp_timeout_raises_extraction_error` — patches `asyncio.wait_for` wholesale, so it sees only the `except TimeoutError` arm | The `ExtractionError` message and the `ytdlp_extraction_timeout` record | **Green unchanged on the documentation-only branch.** On a code-remedy branch it may be re-scoped **because the behaviour changed** — never for convenience (rule 2). |
| **B9** | `tests/test_config.py` — **no test anywhere pins a `Field(description=…)` string** | Nothing today | `B9`'s new test would be the **first** description-pinning test in the repo. See `B9`'s §3: assert a **semantic invariant**, not the whole string, or the block adds a test that fails on any reword. |

The failure mode is uniform: an agent under gate pressure **weakens an assertion rather than fixes the
code**. Each block's Validator is briefed on it.

### §5.2 The prohibitions that survive a fix — the plan's biggest hazard

Plan 08's four surviving prohibitions and what happened to each:

1. **The yt-dlp "no application-level download timeout" decision** — **NOT APPLICABLE.** Its owning
   block landed; no block here touches that docstring. Carried as a §8.2 verification invariant.
2. **`D-01`'s non-reentrant-semaphore invariant** — **SURVIVES and gains readers.** The comment now
   also cites `CON-003`'s counting window. `B8` makes the setting a **third** bound and must re-read
   the comment; `B10` must re-derive and record it.
3. **The lying `INT-004` browser-exit comment** — **DIED**, corrected by `B4`.
4. **`read_progress`'s `shutdown_event` parameter** — **DIED for this plan**; no block touches
   `ffmpeg_utils.py`.

**Two new prohibitions, specific to the remaining scope:**

5. **`config.py` stays free of `asyncio`.** It does not import `asyncio` today. The exit-path bound is
   an interpreter constant; `config.py` **cannot compute it** without a new import that breaches
   rule 3. **A description string is the only carrier**, and any block tempted to compute it is
   breaching separation of concerns.
6. **`download_timeout`'s description must not become a partial truth.** It bounds **four**
   consumers: per-request segment/playlist HTTP, each ffmpeg merge batch, the off-loop extraction's
   `wait_for`, and **yt-dlp's `socket_timeout`** (library option *and* CLI flag). The artifact named
   three. A description corrected to name three is still wrong.

### §5.3 Implementation risks

| Risk | Blocks | Containment |
|---|---|---|
| **`B8` becomes a redesign.** A process-wide pool, or a new setting, for an **advisory** finding. | B8 | Rule 5; no process-wide pool by prohibition 1; the three-place cost of a new setting is stated in `B8`'s decision table. |
| **`B8`'s new test is written against the wrong harness** — sync (constructor raises `RuntimeError: no running event loop`), built on the `conftest` fixture (collapses the matrix to `max_concurrent_downloads = 2`), or leaking unclosed connectors (moves the suite's warning count off 1). | B8 | All three are explicit acceptance criteria in `B8`'s test section. |
| **`B9`'s remedy grows `extractor.py` past single responsibility.** | B9 | Rule 4; options (b)/(c) both carry this cost in `B9`'s fork table; a selection of (b)/(c) requires written justification that an advisory's operator-visible gap justifies it. |
| **`B9`'s description test becomes a brittle full-string assertion.** | B9 | `B9`'s §3 constraint: assert a semantic invariant, not the sentence. |
| **`B10` "fixes" an unverified finding** — assigns a severity, deletes it, or writes a verdict. | B10 | Prohibitions 2, 3, 5; the negative grep in §8.3 is the executable gate. |
| **`B10` writes a record describing the *pre-`B8`* concurrency picture.** | B10 | Edge `C2`; the report must state which `B8` amendments it observed. |
| **`B11` over-reaches** into `.kilo/rules/` or a role file while editing shared pipeline documents. | B11 | Prohibitions 1 and 2; §9 Q4 gates the role-file question. |
| **`B11` updates only the two handbooks plan 08 named** and leaves ten siblings asserting the four-member enum. | B11 | §8.3's mechanical enum-consistency oracle makes the un-updated sites **enumerable**, so a partial update is a gate failure rather than an invisible defect. |
| **A test-pinned assertion is weakened instead of the code fixed.** | B9 (conditional) | §5.1. |
| **A structlog / stdlib-`logging` slip.** | all | §5.6. |
| **A new constant as a literal or a dict instead of a `StrEnum` member.** | any block adding a constant | Rule 10. |

### §5.4 Rollout risks

| Risk | Detail |
|---|---|
| **The remaining working-tree delta is absorbed into a phase-04 commit.** | §2.4. The 14 entries are all `.ai/`, including **eight tracked deletions** of the old `Mko-AINotify` plan files and a modification to `.ai/problems/PROBLEM.md`. `git add -A` sweeps all of it. **This is the plan's largest process risk and it is now purely mechanical.** |
| **The `VAL-` namespace.** | An unqualified `VAL-4xx` makes a reader validate the wrong documents. The convention is stated at the top of this plan, before any block is written. |
| **A wrong concurrency figure shipped in `B8`'s commit body or documentation.** | Prohibition 7 states the arithmetic in a fixed shape, with **both** deltas and with yt-dlp excluded by name. |
| **A withdrawn claim reintroduced in prose.** | The source report `.ai/audit/04-concurrency-cancellation/findings.md` still contains every withdrawn and severity-corrected sub-claim. **Every block cites the validated artifact only.** A block report that implements a withdrawn recommendation is wrong on its face. |
| **A block editing a file another phase owns.** | `B8` ↔ plan 07 `B14` (`_create_connector`, released here); `B9` ↔ plan 07 `B11`/`B15` (the guide's `download_timeout` row, ownership escalated); `B10` ↔ `.ai/audit/**` (read-only); `B11` ↔ `.kilo/rules/`, `.kilo/agents/`, `.ai/templates/`. Each is a **stated boundary with a negative acceptance criterion**. |
| **The tree moves a third time mid-engagement.** | It has already moved twice. §2.4.6 makes the baseline re-measurement a block's first action rather than an inherited fact. |

### §5.5 Compatibility risks

| Risk | Detail |
|---|---|
| **A new `Settings` field** (`B8`, only if that option is selected). | Backward-compatible: a new bounded field with a default changes no existing setting's meaning. `extra="forbid"` means an unrecognised `VKDOWNLOADER_` variable is an error, so the new variable must be in `.env.example` **and** the configuration guide, or operators get `extra_forbidden` on upgrade. Phase 02 already found a shipped `.env.example` value the model rejects — **any value `B8` adds must be constructed against `Settings` and the construction recorded.** |
| **`limit_per_host` acquires a value** (`B8`). | Plan 08 recorded this as a concurrency *reduction*. **That is wrong in direction** — see §5.6 H2. With `limit_per_host == limit` the value is provably non-binding; the real compatibility event is the aggregate ceiling **rising** at high settings. |
| **A cancellation now propagates where it used to be absorbed** (`B2`, landed). | Already shipped. `B8` does not touch it, but §5.6 H3 explains why the asymmetry matters *more* now that `B2` has landed. |
| **`B9`'s documentation-only branch changes no runtime behaviour at all.** | Recorded so a reader does not mistake its absence from the code diff for an omission. A code-remedy branch is the only thing that changes behaviour, and it must justify itself. |
| **`B10` and `B11` change no product behaviour at all.** | Same. `B11` changes the *audit pipeline's* vocabulary, which is a different kind of behaviour entirely, and is the one prose change with real downstream reach. |

### §5.6 The hazard list — the five things that must be in every block report

**H1 — The read-only `git diff --exit-code` gate was vacuous, and the fix was accidental.**
Plan 08's `B10` and `B11` gates were `git diff --exit-code` over two paths that were **untracked**, so
the command exits 0 whether or not they changed — it proved nothing. `0a8fa97` committed the corpus
and the gate is now **live** (verified: `git ls-files --error-unmatch` exits 0 on both, and
`git diff --exit-code HEAD --` on both exits 0 on a clean tree).
**But the fix is unguarded**: nothing prevents a future `git rm --cached .ai/audit/**` from silently
restoring the vacuity, and a block that trusts a bare `git diff --exit-code` would pass vacuously
again.
**→ What replaces it (§8.1):** the gate is **two** commands, and both must pass —
`git diff --exit-code HEAD -- <read-only paths>` **and** `git ls-files --error-unmatch -- <read-only
paths>` (exit 0, proving the paths are still tracked). A green `git diff` with a red `ls-files` is a
**gate failure**, not a pass. For `B10`'s *new* record file the gate is different by construction —
the file does not exist at `HEAD` — so its proof is `git status --short -- <new file>` showing it
**committed**, not `git diff` over it.

**H2 — `limit_per_host == limit` is provably inert, and that turns the pool ceiling into one operator
number — which moves the worst case in the wrong direction.**
The verified aiohttp rule is that the effective per-origin ceiling is `min(limit, limit_per_host)`, so
`lph == limit` cannot bind. That is correct and it is what the remedy selects. **But the same identity
means `max_concurrent_downloads` becomes the single number governing every level**, and the resulting
aggregate moves in **opposite directions** at the two ends of the declared range:

| `N` = `max_concurrent_downloads` | today, effective per-video | after, per-video | today aggregate `10 × N` | after aggregate `N × N` | direction |
|---|---|---|---|---|---|
| 1 | 1 | 1 | 10 | 1 | falls |
| 4 (default) | 4 | 4 | 40 | **16** | **falls 60 %** |
| 10 | 10 | 10 | 100 | 100 | unchanged |
| 12 | **10** | 12 | 120 | 144 | **rises** |
| 16 (ceiling) | **10** | **16** | 160 | **256** | **rises 60 %** |

**What happens to an operator who sets 16 — precisely:** today they silently get **10** connections
per video: a legal configuration at the declared ceiling, silently clipped by a literal. That **is**
`CON-009`, and it is a real defect, not tidiness. After the fix they get **what they asked for** —
and the process can hold up to **16 videos × 16 = 256 concurrent sockets**, on Windows, with **no
process-wide bound**, a 60 % increase in the worst legal configuration. **There is no process-wide
pool to cap it**, and building one is phase 03's, not this plan's.
**→ Containment:** (i) `B8`'s commit body and its documentation clause state **both** deltas and the
new ceiling at the setting's **floor and ceiling**; (ii) `docs/01-tools/vkdownloader-overview.md`
gains the third level so an operator can see what 16 costs before setting it; (iii) **no** rate
limiter and **no** process-wide pool, per prohibition 1; (iv) the report states plainly that
`limit_per_host` is **intentionally non-binding**, so no later reader "fixes" it into a cut (which
would also smuggle in phase 03's rate subject).

**H3 — The exception-catch asymmetry: `B8` removes the exposure, and that is the argument for it.**
`segment_downloader.py`'s parallel download path catches `aiohttp.ClientError` **only**. The parallel
throttle path catches `(aiohttp.ClientError, TimeoutError)`, with an `INT-006` comment that names the
reason explicitly: *"`aiohttp.ClientError` does not cover all asyncio-level errors (e.g. `TimeoutError`
in some aiohttp versions), so both are listed explicitly."* Both paths set
`ClientTimeout.connect = min(30, download_timeout // 4)`, which bounds the **pool wait** as well as
the connect — 7 s at the setting's floor, 30 s at its default. A request queued past that budget
raises `TimeoutError` from aiohttp's timeout helper, **not** a `ClientError`.
**This is live today, not something `B8` introduces.** With `limit = 10` constant and a semaphore of
`N`, the connector permits `min(10, N)`; for **`N` in 11…16 the semaphore admits more tasks than the
connector permits connections**, so requests queue today at those settings. After `B2` landed, the
completion helper settles siblings and **re-raises**, so such a `TimeoutError` now fails the **whole
video** rather than being retried.
**→ Containment:** (i) `B8`'s report states the asymmetry and the live exposure, and states that
`limit = N` **removes** it because `min(limit=N, semaphore=N) = N` — no request ever queues, which is
the containment-by-construction argument for the remedy; (ii) **`B8` must not widen either `except`
clause** — that is a separate observation, not `CON-009` (prohibition 6); (iii) the asymmetry is
**escalated** as §9 Q5, because it is a real finding and it is **not** phase 04's — phase 03 owns
transport; (iv) if `B8` were ever implemented with `limit_per_host < N`, the queueing returns with no
local handler, which is why prohibition 9 forbids it.

**H4 — Two `audit-findings.md` templates, structurally incompatible.**
`.ai/audit/templates/audit-findings.md` (83 lines) is the **declared authority**: referenced by all
twelve phase handbooks, by `audit-multi-phase.md`, by `99-audit-validate.md`, by plans 05–08, and by
all eleven validation artifacts. `.ai/templates/audit-findings.md` (108 lines) is **tracked and
referenced zero times**: it has **no enum table**, uses `#### ID — [SEV]` blocks instead of the
template's field table, carries YAML frontmatter with
`severity_taxonomy: ".kilo/commands/audit/phases/{NN}-audit-{phase-name}.md#severity-taxonomy"`, and
is structurally incompatible with the authority it shadows.
**→ Containment:** `B11` edits **only** the authoritative template and **records in its report that the
second is untouched** (prohibition 6). Leaving a second, contradictory format definition in the corpus
after `B11` is a known, recorded, **not-fixed** state — whether to retire or align it is **§9 Q3**, an
ownership decision this plan does not make.

**H5 — Two competing `download_timeout` owners: plan 07's `C12` vs `B9`.**
Plan 08's prohibition told `B9` the configuration guide's `download_timeout` row belongs to plan 07's
`C12` and must not be touched. **The prerequisite never landed**: there is no composed
`ClientTimeout` helper anywhere in `src/`, and `sock_read = 60` is still a literal at three sites
(verified). So `C12` has never touched the row, and the row is **unowned in practice** while the
prohibition's stated owner is absent.
**→ Containment:** `B9` **still does not touch the row** — the direction of the prohibition is right,
and taking another plan's surface on the strength of its owner not having run is precisely the failure
mode the prohibition exists to prevent. `B9` instead **escalates** the ownership question (§9 Q1) and
its report states that the row is unchanged and that ownership is escalated, not decided.
**A second, adjacent collision:** if `B9`'s field description names the exit-path bound while the
guide's row still says only "Download timeout in seconds (30-3600)", **the two disagree**. That
disagreement is the *visible symptom* of the unresolved ownership, and §9 Q1 must state whether the
row or the description is the doc of record.

### §5.7 Documentation risks

| Risk | Detail |
|---|---|
| **The documentation rules file is another project's.** `docs/00-overview/doc-maintenance-rules.md` exists at exactly the path the engagement template names — 147 lines, tracked — but it prescribes `01-auth/`, `02-dashboards/`, `core/`, `app.py` and `schema-core.md`, **none of which exist here**. In force order: that file nominally, then `.kilo/rules/project.md` rule 14, then `.ai/context/python-code-standards.md` (whose glob is `**/*.{py}`, so `docs/` is outside it). **Blocks follow rule 14 and the repository's actual layout; the mismatch is escalated (§9 Q7).** |
| **The configuration guide drifts from the model.** `docs/11-guides/configuration.md`'s `download_timeout` row is the plan's only cross-plan documentation collision (H5). `B8` writes `max_concurrent_downloads`' **prose section**; `B9` writes `config.py`'s **field description** and not the row. |
| **A behaviour change leaves its justifying comment lying.** `B8` must re-read the `D-01` comment above the segment semaphore — it now describes two bounds and will describe three. `B9` must make both the `_extract_with_ytdlp` docstring and the `INT-003` comment true. |
| **A block writes a new setting into `.env.example` with an illegal value.** Any value `B8` adds must be **constructed against `Settings`** and the construction recorded in the report. |
| **The source report is mistaken for the validated artifact.** The source report still contains every withdrawn sub-claim. **Every block cites the validated artifact only.** |
| **Documentation noise for self-evident changes.** `B10` and `B11` are documentation blocks and need no `docs/` edit — their edit **is** the documentation and is the whole finding. **No block adds a new doc page.** |

### §5.8 The boundary no block may cross

**No finding in this corpus asserts what a real VK origin does.** Every live claim is structural: a
measured task count, a read of a return annotation, a control-flow argument, an interpreter constant.

**Therefore, binding on every block and every verification step:**

1. **No block may be justified by** "a real VK origin would 403 the part", "a real CDN would serve
   `*.m3u8` from this host", or any equivalent. Those are the assumptions the audit declined to make.
2. **No verification step may require network access.** `tests/test_packaging.py` is the only test that
   may touch the network and it skips off-CI. This plan adds none.
3. **Every new test uses a local stub, a `MagicMock`, or a stand-in.** There is no `aiohttp` fixture,
   no ffmpeg-subprocess fixture and no fake clock; **none may be added**. `tests/` holds **zero**
   `aiohttp` references today; `B8`'s test introduces the first, against a connector built in-process.
4. **`B10`'s record must not contain a verdict on the unexecuted condition.** "The condition is safe"
   or "the condition is broken" is exactly the over-claim the validator warned against.
5. **`B9`'s claims about the interpreter's thread-join behaviour** rest on the measured
   `asyncio.constants.THREAD_JOIN_TIMEOUT = 300` and on the measured `run_in_executor` call-site count
   of **one** — not on an assumption that the constant is 300 on other platforms. A document written
   for this repository may state the measured value; it may **not** generalise it.

---

## §6 Agent usage per block

**Which of Auditor / Researcher / Planner / Validator each block requires, and why.** The rule applied:
risk and **real uncertainty** buy agents; a mechanical change with a determined remedy needs none.
Low-risk mechanical work is **Implementor only**.

| Block | Auditor | Researcher | Planner | Validator | Risk | The question that earns each agent |
|---|---|---|---|---|---|---|
| **B8** | **—** | **— (existing deliverable ruled sufficient — see below)** | **YES** | **YES** | MEDIUM (advisory), the only behavioural block | *Planner:* the **remedy-shape selection must be recorded and owned by the block**, not ratified from a deliverable written outside a block report — plus the arithmetic and the documentation landing site. *Validator:* the aggregate arithmetic must match the code; a description that names two levels after the setting became three is a silent lie; and the "no forbidden enabler" question (the eight gate items) has no test. **Not an Auditor block:** the defect is byte-identical to the audit's own measurement and visible in one 18-line function — there is nothing left to re-derive. |
| **B9** | **—** | **YES** | **YES** | **YES** | MEDIUM (advisory), LOW code, HIGH collision | *Researcher:* **the modern idiom for bounding an abandoned `run_in_executor` job** — whether a dedicated or shared executor is the accepted answer or whether documentation alone is — **plus whether `download_timeout`'s fourth consumer (yt-dlp's `socket_timeout`) changes the answer**. **No deliverable exists for this block**, so this is a genuine gap, not a formality. *Planner:* whether a code remedy is justified **at all** for an advisory finding. *Validator:* a documentation-only block has **no oracle**, so the independent read *is* the gate — and the cross-plan `C12` boundary must be confirmed. |
| **B11** | **—** | **YES** | **YES** | **YES** | MEDIUM (process), **largest reach in the plan** | *Researcher:* **how audit pipelines in general encode a not-executed observation.** The two in-repo remedies have materially different blast radii across twelve phase handbooks, and the external convention is the genuinely open question. **No deliverable exists for this block.** *Planner:* the selection, **the full edit list recorded before any edit**, and the inside-block sequencing (template first, then reconciliation). *Validator:* **no oracle exists for prose that governs the pipeline itself**, and the two failure modes are invisible — over-reach into `.kilo/rules/`/`.kilo/agents/`, and a partial update that leaves ten sibling handbooks asserting the old enum. |
| **B10** | **—** | **—** | **YES** | **YES** | LOW code / MEDIUM process | *Planner:* the durable record's **location and its six required statements in order** are a judgement about audit provenance, not a copy — and the decision to cite `B11` by id rather than by asserted remedy is a durability judgement. *Validator:* the gate is an **independent read** proving no code changed, no severity was assigned, no verdict was written, and the finding was not quietly closed. **No Researcher:** the approach is fully specified — there is no design fork, and `B10` is Implementor-plus-Validator work. |

**Aggregate agent budget.** 4 blocks: **3 require a Planner** (every block with a fork, a contract
change, or a judgement about what a durable record may claim), **4 require a Validator** (every block
whose failure is invisible to a passing test run), **2 require a Researcher** (`B9` and `B11` — both
have genuine open design questions and **no deliverable exists**), **0 require an Auditor.**
**No block is Implementor-only**, because every block carries at least one negative acceptance criterion
that only an independent read can confirm.

### §6.1 `B8`'s Researcher decision — the existing deliverable is sufficient, and here is why

**Decision: no fresh Researcher pass for `B8`.** `tmp/plan_updates/b8_research.md` (546 lines) exists
and its substantive claims hold. The Planner re-verified the load-bearing ones against the live tree:

| Research claim | Planner verification at `HEAD = 0a8fa97` | Verdict |
|---|---|---|
| `limit = 10` on both paths, `limit_per_host` absent, `DefaultResolver` | `_create_connector` byte-identical to the audit's measurement | **Holds** |
| One connector + one `ClientSession` per video; no process-wide pool | `_run_download_session` builds one of each; teardown delegated to the session | **Holds** |
| The segment semaphore is sized by the setting | `asyncio.Semaphore(settings.max_concurrent_downloads)` in `_run_download_session` | **Holds** |
| Effective ceiling is `min(limit, limit_per_host)`; `lph == limit` is provably inert | Enforced in aiohttp's `connect()` per-host bookkeeping; `aiohttp 3.14.1` installed | **Holds** |
| `connector.limit` / `.limit_per_host` are public read-only properties | Verified at runtime | **Holds** |
| Pool-wait budget is `ClientTimeout.connect = min(30, download_timeout // 4)` | Present in both download paths | **Holds** |
| No `aiohttp` references in `tests/` today | **Zero matches** for `aiohttp` / `TCPConnector` / `ClientTimeout` / `ClientSession` | **Holds** |

**Why nothing needs re-researching.** The research's dependencies are (i) the shape of
`_create_connector`, (ii) the shape of `_run_download_session`, (iii) `aiohttp 3.14.1`'s connector
enforcement, and (iv) the state of `tests/`. **Neither tree move touched any of them.** `7d02a30` did
not change `_create_connector` (byte-identical) and `0a8fa97` touched **zero** paths outside `.ai/`.
A fresh pass would re-derive the same numbers and cost a lead time the block does not need.

**Two obligations that follow, and they are not optional:**

1. **Promote the evidence before it can be lost.** The deliverable lives in `tmp/`, which is
   **untracked and not gitignored** — it can disappear at any cleanup. **`B8`'s block report must
   carry the load-bearing claims and the verified arithmetic inline**, and the commit body must carry
   the arithmetic in `B8`'s prohibition-7 shape. A commit that cites a path in `tmp/` as its evidence
   is a gate failure.
2. **Re-verify the two version-dependent claims at execution time.** `aiohttp 3.14.1` and the
   `min(limit, limit_per_host)` enforcement come from *this* install. If `pyproject.toml`'s pin moves,
   the block re-checks both before relying on them, and the report records the version it verified
   against.

**The deliverable *selects* option (a); this plan does not ratify that selection.** The **block's
Planner** confirms it, records it, owns it, and records the rejected alternatives. A decision made in a
research file is not a block decision.

### §6.2 `B8`'s Planner re-verification — what held, what did not, what is now binding

`B8`'s Planner re-measured every load-bearing claim against the live tree at
**`HEAD = 0a8fa97d81f48fe4faac289b3fbbbfa5a567b8b1`** and against the installed
**`aiohttp 3.14.1`** (`aiohttp>=3.9.0` is the declared floor; `pyproject.toml` pins no upper bound).
**Ten of twelve claims held unchanged. Two did not, and both are corrected here** rather than
carried forward. `§7 B8` is written against the corrected facts.

| # | Claim under test | Measurement | Verdict |
|---|---|---|---|
| 1 | `limit = 10` on **both** `_create_connector` return paths; `limit_per_host` absent from both; no `resolver=` | Read in full. The `ssl_verify` branch returns `aiohttp.TCPConnector(limit=10)`; the disabled branch builds `ssl_context` from `ssl.create_default_context()`, sets `check_hostname = False` and `verify_mode = ssl.CERT_NONE`, logs `ssl_verification_disabled` with `_strip_auth_params(video_url)`, and returns `aiohttp.TCPConnector(ssl=ssl_context, limit=10)`. Neither passes `limit_per_host` or `resolver=`. | **Holds** |
| 2 | Sole call site; one connector + one `ClientSession` per call; teardown delegated to the session | `_create_connector` is called once, from `_run_download_session`, immediately before `async with aiohttp.ClientSession(connector=connector)`. No other construction site in `src/`. | **Holds** |
| 3 | The segment-layer semaphore and the `is_bounded_batch` flag it feeds | `semaphore_to_use = asyncio.Semaphore(settings.max_concurrent_downloads)`; `is_bounded_batch = video_semaphore is not None`; both feed `DownloadPolicy`. | **Holds** |
| 4 | `Settings.max_concurrent_downloads` is `default=4, ge=1, le=16` | Constructed for `N ∈ {1, 4, 16}`; field metadata is `[Ge(ge=1), Le(le=16)]`, default `4`. | **Holds** |
| 5 | `connector.limit` / `connector.limit_per_host` are **public read-only properties** | Both are `property` objects with `fset is None`; `connector.limit = 100` raises `AttributeError: property 'limit' of 'TCPConnector' object has no setter`, same for `limit_per_host`. Reading them returns `int`. | **Holds** |
| 6 | The effective per-origin ceiling is `min(limit, limit_per_host)`, so `limit_per_host == limit` is provably non-binding | `BaseConnector._available_connections` computes `total_remain = self._limit - len(self._acquired)` and then, inside `if host_remain := self._limit_per_host:`, returns `host_remain` whenever `total_remain > host_remain` — the `min`, expressed as a guard. With `_limit_per_host == _limit`, `acquired_per_host ⊆ acquired`, so `host_remain >= total_remain` always and the per-host term can never bind. | **Holds — with a qualification, see #7** |
| 7 | …and today's `min(10, 0) == 0`, i.e. the arithmetic can be written naively | **This is the nuance plan 09 states too loosely.** `limit_per_host = 0` is aiohttp's **unbounded sentinel**, not a ceiling of zero: the whole per-host term is skipped when it is falsy, and `connect()` guards the entire `_acquired_per_host` bookkeeping with `if self._limit_per_host:`. Measured on the unfixed tree, `min(connector.limit, connector.limit_per_host)` returns **0**, which is meaningless as a ceiling. **Correct form:** the `min` identity holds only when `limit_per_host > 0`. Today the per-origin ceiling is *unbounded*, and the effective per-video concurrency is `min(10, N)` where the `N` term is the **semaphore**, not the connector. After the fix `limit_per_host = N > 0`, the per-origin term becomes active and equals the total term, and `min(N, N) = N` genuinely applies. | **Corrected** |
| 8 | The pool-wait budget is `ClientTimeout.connect = min(30, download_timeout // 4)` on both download paths | Present in `_run_parallel_download_with_backoff` (`connect_timeout = min(30, download_timeout // 4)`) and in `_fetch_playlist_with_retry` (`connect=min(30, settings.download_timeout // 4)`). `sock_connect=30`, `sock_read=60` on both. | **Holds** |
| 9 | The two `except` clauses the block must not widen | `_try_single_download_attempt` catches `aiohttp.ClientError` **only**. `_fetch_single_playlist` catches `(aiohttp.ClientError, TimeoutError)`. `downloader_throttle.py`'s parallel path catches `(aiohttp.ClientError, TimeoutError)` under the `INT-006` comment. The asymmetry is between the **segment** path and the **throttle** path, and the playlist path already matches the throttle path. | **Holds** |
| 10 | `tests/` holds **zero** `aiohttp` / `TCPConnector` / `limit_per_host` / `ClientSession` / `ClientTimeout` references | `grep` over `tests/` returns **no files found**. `B8`'s new test introduces the first. | **Holds** |
| 11 | A synchronously constructed `TCPConnector` raises `RuntimeError: no running event loop` | Measured: `RuntimeError: no running event loop`. `@pytest.mark.asyncio` is required. | **Holds** |
| 12 | "An unclosed connector emits its own warning and would move the suite's warning count off 1" | **Falsified, three ways.** `aiohttp 3.14.1`'s `BaseConnector.__del__` begins `if self._closed: return` / `if not self._conns: return` — a connector that was constructed and read but never opened a connection has an **empty pool**, so it returns before the `ResourceWarning`. Measured **0** captured warnings with `warnings.simplefilter("always")` **and** an explicit `gc.collect()`; **0** warnings in the pytest summary for a deliberately leaked connector run with `-W always::ResourceWarning`. | **Falsified — mechanism only** |

**What follows from #12, precisely.** The **rule** — *close every connector the test constructs* —
**stands and is unchanged**. Only the plan's justification for it was wrong. The rule now rests on
three measured facts: (i) production gets teardown free from
`async with aiohttp.ClientSession(connector=connector)`, and the test must mirror that ownership
rather than invent a second teardown convention; (ii) a leaked connector keeps its pool's
keepalive-cleanup handle and SSL-transport list reachable after the loop closes; and (iii) if a
future version of this test ever lets a connector **open a connection**, `__del__` no longer returns
early and the leak *does* become a `ResourceWarning` that would move the count. **A new constraint
falls out of #7 and #12 together: the test must read the connector's ceilings only — it must not
drive a request through it.** A connector whose pool is non-empty is a connector that can warn.

**And what follows from #7 for the report and the commit body.** Prohibition 7's "effective
per-video connections `min(10, N)`" is **shorthand that must be unpacked, not copied**. Both deltas
are unchanged and both are still correct — **40 → 16 at the default, 160 → 256 at the ceiling** — but
the honest derivation is:

- **Today:** `limit = 10` constant; `limit_per_host = 0` = **unbounded per origin**; the total term
  admits `10` connections per download and the segment semaphore admits `N` in-flight transfers, so
  the effective per-video concurrency is `min(10, N)`, **whichever of those two is smaller** — and for
  `N ∈ 11…16` the connector is the binding one, which *is* `CON-009`. Aggregate `10 × N`.
- **After:** `limit = N` **and** `limit_per_host = N`, both positive, so both terms are active and
  equal; effective per-video concurrency is `min(N, N) = N` and **no request ever queues for a
  connector slot**, because each in-flight segment permit issues exactly one request — verified:
  `segment_downloader.py` has exactly **two** `session.get` call sites, the segment fetch and the
  one-off playlist fetch that runs before the fan-out and outside the semaphore. Aggregate `N × N`.

**Nothing in `B8`'s scope, arithmetic or remedy changes.** What changes is that the report and the
commit body must state the *derivation*, not the shorthand, or a reader who checks it will find an
expression that evaluates to `0`.

---

## §7 Task specifications

One specification per block, in `.ai/tasks/templates/task_template.yaml` shape. Semantic code units
only — files, modules, classes, functions, methods, fields, table rows. **Never line numbers.**

### B8

```yaml
id: plan09-b8-transport-pool-ceiling
title: Derive the transport pool ceiling from the setting and give the per-origin ceiling a value
priority: medium
depends_on: []

source_reference: .ai/plans/09-concurrency-cancellation-audit-fixes-completion.md
predecessor_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B8 — Derive the transport pool ceiling from the setting and give the per-origin ceiling a value
source_blocks: ["B8"]
source_findings: ["CON-009"]

description: >
  CON-009 — advisory / BEST-PRACTICE / MEDIUM. RE-VERIFIED by the block's Planner against the live
  tree at HEAD 0a8fa97 and the installed aiohttp 3.14.1 (the declared floor is aiohttp>=3.9.0 and
  pyproject.toml pins no upper bound); plan 09 §6.2 carries the twelve-claim table, ten holding
  unchanged and two corrected. _create_connector hard-codes limit=10 on BOTH return paths and passes
  no limit_per_host, so the per-origin ceiling is aiohttp's UNBOUNDED sentinel 0. Measured
  max_concurrent_downloads in {1, 4, 16} x ssl_verify in {True, False} gives limit=10 and
  limit_per_host=0 in all SIX combinations, identical across the whole declared range ge=1, le=16
  (default 4). The sole call site is _run_download_session, which pairs one connector with its own
  ClientSession per video and delegates teardown to the session's async with, so the aggregate is
  per-download times concurrent downloads and NO process-wide bound exists. Plan 07's B14 deferred
  this literal here and carried the prohibition "MUST NOT touch _create_connector"; that prohibition
  is RELEASED by this block. The risk class is ADVISORY — the over-engineering risk is higher than
  the defect, and rule 5 is the binding constraint. A Researcher deliverable exists at
  tmp/plan_updates/b8_research.md and §6.1 rules a fresh pass unnecessary; its selection is NOT
  ratified — the block's Planner confirms and owns it, and records it under remedy_selection below.
  ARITHMETIC CORRECTION, BINDING ON THE REPORT AND THE COMMIT BODY. Plan 09 §5.6 H2's shorthand
  "effective per-video connections min(10, N)" must not be copied as an expression.
  min(limit, limit_per_host) is a valid ceiling only when limit_per_host > 0: 0 is aiohttp's
  UNBOUNDED sentinel, BaseConnector._available_connections skips the entire per-host term when it is
  falsy, and connect() guards the whole _acquired_per_host bookkeeping the same way. Measured on the
  unfixed tree, min(connector.limit, connector.limit_per_host) returns 0, which is meaningless as a
  ceiling. Honest form — TODAY the per-origin ceiling is UNBOUNDED, the total term admits 10
  connections per download, the segment semaphore admits N in-flight transfers, and the effective
  per-video concurrency is min(10, N) with whichever of those two is smaller, which for N in 11..16 is
  the connector, and that IS CON-009; AFTER the fix both terms are positive and equal so min(N, N) = N
  genuinely applies and no request ever queues for a connector slot. Both deltas are unchanged and
  both must be stated — the aggregate FALLS 40 -> 16 at the default and RISES 160 -> 256 at the
  ceiling. No request ever queues after the fix because each in-flight segment permit issues exactly
  one request: verified, segment_downloader.py has exactly TWO session.get call sites — the segment
  fetch, and the one-off playlist fetch that runs before the fan-out and outside the semaphore.
  ARCHITECTURE, NON-NEGOTIABLE. No new module, and config.py gains NO import of aiohttp or asyncio —
  the derivation belongs in segment_downloader.py, which already imports aiohttp and already owns the
  segment semaphore. The ceiling is a derived VALUE read off an existing setting, never a new named
  module-level constant, so rule 10 (StrEnum for fixed values) is not engaged and no enum member is
  added. The two ceiling arguments must come from ONE local bound before the ssl_verify branch so they
  cannot drift apart, and the ssl= argument shape, the ssl_context construction and the
  ssl_verification_disabled warning are untouched.

goals:
  - the connector's limit is derived from a declared setting, not a literal
  - limit_per_host carries an explicit value instead of being unbounded, and that value is provably
    non-binding so the segment semaphore remains the single binding authority
  - the transport ceiling is named as a THIRD level in all three places the setting's two-level claim
    currently stands — config.py's field description, docs/11-guides/configuration.md's table row and
    prose section, and docs/01-tools/vkdownloader-overview.md's Shared Concurrency Control section
  - the aggregate arithmetic is pinned by a test so it cannot drift from the code, and both deltas
    (40 -> 16 falling at the default, 160 -> 256 rising at the ceiling) are stated with yt-dlp's
    separate child process excluded by name
  - no process-wide pool is introduced and no request rate is limited — those are other phases' subjects
  - no new Settings field, no .env.example entry, no new src/ or tests/ file

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

  - path: docs/01-tools/vkdownloader-overview.md
    targets:
      - type: section
        name: Shared Concurrency Control
    semantic_anchors:

  - path: docs/11-guides/configuration.md
    targets:
      - type: section
        name: max_concurrent_downloads
    semantic_anchors:

  - path: tests/test_segment_downloader.py
    targets:
    semantic_anchors:

  # .env.example is DELIBERATELY ABSENT. Remedy (a) adds no Settings field, so no .env.example entry
  # is required and none is added; the file is a flat commented list with no per-setting prose and its
  # existing max_concurrent_downloads value is unchanged. The Implementor records the deliberate
  # omission in the report so it does not read as an oversight.

changes:

  - action: modify
    description: >
      REMEDY SELECTED BY THE BLOCK'S PLANNER — option (a), now ratified. On BOTH return paths of
      _create_connector, derive BOTH ceilings from the ONE existing setting, so that
      limit = settings.max_concurrent_downloads and limit_per_host = settings.max_concurrent_downloads
      — the same value in both arguments, bound to ONE local before the ssl_verify branch so the two
      cannot drift apart. No new Settings field.
      WHY (a) WINS. It is the finding's own recommendation, quoted from CON-009 in
      04-concurrency-cancellation-validated-findings.md — "derive limit from
      settings.max_concurrent_downloads and set an explicit limit_per_host, so one setting governs
      the whole process rather than each unit re-interpreting it". It is plan 08's recorded DEFAULT
      (§3.4 decision list), and rule 5 is the binding constraint plan 08's B8 itself names for this
      block, because the risk class is ADVISORY and the over-engineering risk exceeds the defect. It
      is provably non-binding on the per-origin term, measured against aiohttp 3.14.1: with
      limit_per_host == limit > 0, BaseConnector._available_connections computes
      total_remain = _limit - len(_acquired) and returns host_remain only when
      total_remain > host_remain; acquired_per_host is a subset of acquired, so host_remain >=
      total_remain always and the per-host term can never be the binding one. Setting the value to
      the SAME number is therefore free of behavioural risk — it documents a ceiling the total term
      already implies.
      REJECTED — (b), a new Settings field for the transport ceiling. A real operator knob, but it
      costs the three-place rule (field description, .env.example, and
      docs/11-guides/configuration.md's table row AND prose section), extra="forbid" upgrade work so
      a missing entry becomes an extra_forbidden error on upgrade, an .env.example value that must
      be CONSTRUCTED against the model with the construction recorded, an EXPECTED_SDIST_ENTRIES
      review, and guide prose — all to replace one literal with one expression, on an ADVISORY
      finding. Worse, it invites the operator to set a transport ceiling that DISAGREES with the
      semaphore, reintroducing CON-009 in a more expensive and more configurable form.
      REJECTED — (c), a process-wide shared connector or pool. A redesign, not a fix: it moves
      connector ownership from per-download to per-process and changes session and connector
      lifetimes, and CON-009 does not ask for it. Prohibited by §5.5 prohibition 1, and contradicted
      by phase 03's VAL-001, which ruled AGAINST the process-wide framing.
      REJECTED VARIANT — limit_per_host as a deliberate FRACTION of limit. Plan 08's §5.5 risk row
      assumes a smaller value "reduces the achievable per-origin concurrency" and calls it a
      behavioural change on the hot path; with limit_per_host == limit it provably cannot, while a
      fraction would (i) invent a politeness number with no evidence behind it, (ii) silently reduce
      the concurrency the operator asked for, and (iii) implement phase 03's request-RATE subject in
      disguise, which prohibition 1 forbids outright.
      REJECTED VARIANT — limit as a small MULTIPLE of the setting for headroom. It changes the
      commit body's arithmetic away from N squared, doubles the socket burst at N=16, and buys
      headroom against a hazard that does not exist, since every in-flight request issues exactly one
      session.get.
      The Implementor records the selection, the four rejections and their reasons in the block report.
    code_hint: |
      # _create_connector — both return paths; ONE local, so the two ceilings cannot drift
      connection_ceiling = settings.max_concurrent_downloads
      if settings.ssl_verify:
          return aiohttp.TCPConnector(
              limit=connection_ceiling,
              limit_per_host=connection_ceiling,
          )
      ssl_context = ssl.create_default_context()
      ssl_context.check_hostname = False
      ssl_context.verify_mode = ssl.CERT_NONE
      logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))
      return aiohttp.TCPConnector(
          ssl=ssl_context,
          limit=connection_ceiling,
          limit_per_host=connection_ceiling,
      )
      # UNCHANGED: the ssl= argument shape, the ssl_context construction, the warning event name and
      # its _strip_auth_params(video_url) argument, the signature, the return type. Only the two
      # ceiling arguments move. The ssl_verify=False path exists precisely so the test's ssl_verify
      # axis catches a forgotten second return path — do not collapse them into one.

      # the invariant comment belongs at the construction site, in the style of the D-01 comment:
      # CON-009: both ceilings are the same setting, so limit_per_host can never be the binding term
      # (aiohttp enforces min(limit, limit_per_host) only when limit_per_host > 0, and acquired
      # per-host connections are a subset of all acquired). The segment semaphore stays the single
      # binding authority and the transport never clips an operator's setting. This is per download,
      # NOT a process-wide pool: the aggregate is per-download times concurrent downloads.

  - action: modify
    description: >
      DOCUMENTATION — three EXISTING surfaces. Rule 14 governs (D7): no new doc page, no new doc
      structure, and docs/00-overview/doc-maintenance-rules.md is NOT rewritten. Both docs already
      carry frontmatter and a "## Purpose" section; leave that as it is.
      (1) src/vkdownloader/config.py, the Field(description=...) of Settings.max_concurrent_downloads.
      It currently enumerates TWO levels — "The batch semaphore gates one permit per video (acquired
      once per video); each video's segment fan-out is bounded separately by a semaphore of the same
      size owned by the segment layer" — plus the anti-detection clause about setting it to 1. Name
      the transport ceiling as a THIRD level and KEEP the anti-detection clause.
      (2) docs/11-guides/configuration.md, the max_concurrent_downloads TABLE ROW and its PROSE
      SECTION. Both repeat the same two-level claim and both must gain the connector level. This is
      B8's to own: plan 09 §5.7 states B8 writes max_concurrent_downloads' prose section and §8.2's
      end-state gate 5 requires it to change. B9 owns download_timeout's row and prose instead, and
      D1 keeps B9 out of that row, so the two settings' hunks are disjoint. Leave the
      VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS example value alone.
      (3) docs/01-tools/vkdownloader-overview.md, the Shared Concurrency Control section. This gains
      the FIRST mention of a transport connection ceiling anywhere in docs/ — measured at HEAD,
      docs/ holds zero occurrences of TCPConnector, limit_per_host, "connection pool" or "pool
      ceiling". State that each download owns its own connector, that the ceiling is per download,
      and explicitly that this is NOT a process-wide pool. Keep the existing work-stealing narrative
      and its diagram intact.
      .env.example is DELIBERATELY UNTOUCHED and is not in files: remedy (a) adds no field, its value
      is unchanged, and the file is a flat commented list with no per-setting prose. State the
      deliberate omission in the report so it is not read as an oversight.
    code_hint: |
      # config.py — the Field description, today TWO levels, becomes THREE. Same shape, longer prose.
      max_concurrent_downloads: int = Field(
          default=4,
          ge=1,
          le=16,
          description="Maximum number of videos downloading concurrently in a batch. "
          "The batch semaphore gates one permit per video (acquired once per video); "
          "each video's segment fan-out is bounded separately by a semaphore of the "
          "same size owned by the segment layer; each download's aiohttp connection "
          "pool is sized to the same value for both the total and the per-origin "
          "ceiling, so the transport never clips this setting. Setting this to 1 "
          "enables an anti-detection delay between sequential segment downloads.",
      )
      # The same three-level claim is appended to the configuration guide's table row and to the
      # description bullet of its prose section. Nothing else in either file changes.

  - action: modify
    description: >
      READ-OBLIGATION ON THE OWNERSHIP COMMENT, QUOTED IN FULL. The comment standing immediately above
      the segment semaphore in _run_download_session reads — "D-01: The batch semaphore gates *videos*
      (one permit per video, acquired once in perform_download). asyncio.Semaphore is not reentrant:
      reusing the caller's batch permit here for per-segment acquisition would deadlock once all video
      permits are held, because every inner acquisition would wait on a permit the same task already
      holds. The segment fan-out is therefore bounded by a semaphore this layer owns, sized by the
      same max_concurrent_downloads setting. The live task set is further bounded by a counting window
      of that same ceiling in the segment pump (len(pending) >= policy.max_concurrent_downloads), so no
      more than max_concurrent_downloads task objects exist at once (CON-003)."
      WHAT MUST CHANGE, PRECISELY. The clause "sized by the same max_concurrent_downloads setting"
      describes TWO layers today — the semaphore and the counting window — and after this block the
      same setting sizes THREE, because the connector's pool ceiling becomes a third bound. Nothing
      the comment currently asserts becomes false: the reentrancy argument, the deadlock analysis and
      the CON-003 bound are all untouched and remain correct. Update the comment in the SAME commit
      so it records that the connector's total and per-origin ceilings carry the same value and are
      provably non-binding, that the semaphore therefore remains the single binding authority and the
      transport never clips an operator's setting, and that this is per download with no process-wide
      bound. Add a clause; do not rewrite or delete the existing sentences.
      The neighbouring line that reports the segment fan-out's two bounds is likewise re-read for
      accuracy. Nothing else in _run_download_session changes: the connector construction, the
      ClientSession pairing, the teardown, the is_bounded_batch flag and the DownloadPolicy it feeds
      are all unchanged.
    code_hint: |
      # _run_download_session — ADD a clause to the existing D-01 comment; delete nothing from it.
      # Existing (unchanged): "D-01: The batch semaphore gates *videos* ... asyncio.Semaphore is not
      # reentrant ... (CON-003)."
      # Added: CON-009: the connector this function constructs carries the SAME value as both its
      # total and its per-origin ceiling, and limit_per_host == limit is provably non-binding, so the
      # semaphore stays the single binding authority and the transport never clips this setting. The
      # connector is per download — this is not a process-wide pool; the aggregate is per-download
      # times concurrent downloads.

  - action: add_test
    description: >
      TWO new tests in tests/test_segment_downloader.py, added to the EXISTING file as a NEW plain
      test class. Follow the conventions already in that file — `from __future__ import annotations` is
      already present, async tests carry `@pytest.mark.asyncio`, and a class docstring states what the
      group covers.
      TEST 1 — the ceiling follows the setting, data-driven. `@pytest.mark.parametrize` over
      max_concurrent_downloads in {1, 4, 16} (the declared floor, the default, and the declared
      ceiling — the three values the commit body must quote) crossed with ssl_verify in {True, False}
      via `@pytest.mark.asyncio`. Six cases. For each, construct `Settings(...)` yourself and call the
      production `_create_connector` with a fixed video URL, then assert:
        - `connector.limit` EQUALS the parameterised `max_concurrent_downloads` — assert equality to
          the PARAMETER, never to a constant. A test asserting `limit == 10` would encode the defect.
        - `connector.limit_per_host` EQUALS the same parameter — the intended explicit value.
        - `connector.limit_per_host >= connector.limit` — the structural statement that the per-origin
          term can never be the binding one. This is the assertion that encodes "non-binding" without
          relying on aiohttp internals.
      The cross of both ssl_verify values exists to catch a forgotten second return path, so both
      branches MUST be exercised; ssl_verify=False additionally logs the `ssl_verification_disabled`
      event, which is a structlog event and NOT a Python warning — do not assert on it and do not
      suppress it. Widening the parameter set beyond {1, 4, 16} is permitted provided 1, 4 and 16 all
      remain in it.
      TEST 2 — the aggregate arithmetic cannot drift. Data-driven over max_concurrent_downloads in
      {4, 16}. For each, construct one connector per in-flight download — that is, N connectors, each
      from its own `Settings(max_concurrent_downloads=N)` — then assert the aggregate equals
      `N * min(connector.limit, connector.limit_per_host)`, and that it equals the exact figure the
      commit body states for that N. Pin both directions explicitly, because they move in OPPOSITE
      directions and quoting only one is as wrong as quoting the other: at N=4 the aggregate is 16 and
      is LOWER than today's 10 x N = 40; at N=16 the aggregate is 256 and is HIGHER than today's
      160. Close every connector in this test too.
      HARD CONSTRAINTS — each of these is a VERIFIED FAILURE or a VERIFIED TRAP at HEAD, not a
      preference:
      - MUST be `@pytest.mark.asyncio`. A synchronously constructed TCPConnector raises
        `RuntimeError: no running event loop` (measured against aiohttp 3.14.1). There is no
        `[tool.pytest.ini_options]` and no `asyncio_mode` setting in this repository, so the marker is
        required, not optional.
      - MUST construct `Settings(...)` itself, per case. tests/conftest.py's `test_settings` fixture
        pins `max_concurrent_downloads=2` and would collapse the whole matrix to a single value. The
        autouse `isolate_settings_source` fixture is fine and must simply be left alone — it already
        pins the env source and chdirs to tmp_path, so a bare `Settings(max_concurrent_downloads=N,
        ssl_verify=...)` constructs cleanly (measured).
      - MUST close every connector it constructs, via `await connector.close()` in a `finally`, or
        `async with`. THE RULE STANDS; its previously stated reason was WRONG and is corrected here —
        plan 09 and plan 08 attributed the warning-count risk to an unclosed connector's own warning,
        and that mechanism is FALSIFIED. aiohttp 3.14.1's `BaseConnector.__del__` begins `if
        self._closed: return` then `if not self._conns: return`, so a connector that was built and
        read but never opened a connection has an EMPTY pool, returns early, and emits NO
        ResourceWarning — measured zero captured warnings with `warnings.simplefilter("always")` and
        an explicit `gc.collect()`, and zero in the pytest summary under `-W always::ResourceWarning`.
        Close them anyway, for the three reasons that DO hold: production gets teardown free from
        `async with aiohttp.ClientSession(connector=connector)` and the test must mirror that same
        ownership rather than invent a second teardown convention; a leaked connector keeps its
        pool's keepalive-cleanup handle and SSL-transport list reachable after the loop closes; and
        the moment a connector opens a connection its pool stops being empty and the leak WOULD warn,
        moving the suite's count off its baseline of 1.
      - MUST NOT drive a request through the connector. This follows from the point above and is a
        hard constraint: the test reads ceilings only. A connector with a non-empty pool is a
        connector that can warn. No network under any circumstances.
      - MUST read the PUBLIC properties `connector.limit` and `connector.limit_per_host` only. Both
        are `property` objects with no setter, and assignment raises `AttributeError` (measured).
        No `_limit`, no `_limit_per_host`, and do not assert on `_ssl` either — the ssl= argument shape
        is unchanged and is not what this block tests.
      - MUST NOT add a new fixture, and MUST NOT give the new class a base class. Plain class, in the
        style of the file's existing test classes.
      - MUST put a diagnostic string on EVERY assertion, in the style already used in the file.
      - `aiohttp` becomes the FIRST `aiohttp` import anywhere in `tests/` — grep confirms tests/ holds
      zero references to aiohttp, TCPConnector, limit_per_host, ClientSession or ClientTimeout at HEAD.
      That is intended and necessary; say so in the commit body. No `Any` anywhere (rule 9).
    code_hint: |
      class TestConnectorCeilingsFollowTheSetting:
          """CON-009: both connector ceilings derive from max_concurrent_downloads.

          Two tests cover:
            1. limit follows the setting across the declared range x both ssl_verify values.
            2. the aggregate arithmetic the commit body claims cannot drift from the code.
          """

          @pytest.mark.parametrize("ssl_verify", [True, False])
          @pytest.mark.parametrize("max_concurrent_downloads", [1, 4, 16])
          @pytest.mark.asyncio
          async def test_both_ceilings_follow_the_setting(
              self, max_concurrent_downloads: int, ssl_verify: bool
          ) -> None:
              settings = Settings(max_concurrent_downloads=max_concurrent_downloads, ssl_verify=ssl_verify)
              connector = _create_connector(settings, _VIDEO_URL)
              try:
                  # equality to the PARAMETER, never to a constant: asserting limit == 10 would
                  # encode CON-009 rather than fix it.
                  assert connector.limit == max_concurrent_downloads, (...)
                  assert connector.limit_per_host == max_concurrent_downloads, (...)
                  # the per-origin term can never be the binding one, stated structurally so the
                  # assertion does not depend on aiohttp internals.
                  assert connector.limit_per_host >= connector.limit, (...)
              finally:
                  await connector.close()

          @pytest.mark.asyncio
          async def test_aggregate_matches_the_claimed_arithmetic(self) -> None:
              """N connectors, one per in-flight download: the aggregate is N x min(limit, per_host)."""
              for videos_in_flight, claimed in ((4, 16), (16, 256)):
                  connectors = []
                  try:
                      for _ in range(videos_in_flight):
                          settings = Settings(max_concurrent_downloads=videos_in_flight)
                          connectors.append(_create_connector(settings, _VIDEO_URL))
                      one = connectors[0]
                      aggregate = sum(c.limit for c in connectors)
                      assert aggregate == videos_in_flight * min(one.limit, one.limit_per_host), (...)
                      assert aggregate == claimed, (...)  # the figure the commit body states
                      # both deltas, pinned in OPPOSITE directions:
                      #   40 -> 16 at N=4 (falls), 160 -> 256 at N=16 (rises)
                  finally:
                      for connector in connectors:
                          await connector.close()

  - action: prohibited
    description: >
      RESTATED AS EXECUTABLE NEGATIVE CRITERIA. Each is a thing the block must be able to point at and
      say is absent — checkable by grep, by a diff, or by reading the staged file list.
      1. NO PROCESS-WIDE POOL. Exactly one connector is constructed per _run_download_session, paired
         with its own ClientSession, and closed by that session's async with. Connector ownership does
         not move. Check: the number of TCPConnector construction sites in src/ is UNCHANGED at one,
         inside _create_connector.
      2. NO REQUEST-RATE LIMITING. Nothing in the change set throttles, delays, rate-limits or paces
         requests against an origin. The request RATE against one origin is phase 03's subject —
         NET-014, adjudicated in that phase's VAL-001, which ruled in favour of CON-009 and ruled
         AGAINST the process-wide framing. Check: the change touches no coordinator, no sleep, no
         backoff, and neither path's ClientTimeout.
      3. NO ClientTimeout CHANGE. Both are untouched — the segment path's connect=min(30,
         download_timeout // 4) and the playlist path's connect=min(30, settings.download_timeout //
         4), with sock_connect=30 and sock_read=60 on both.
      4. NO limit_per_host VALUE THAT BINDS. The two ceiling arguments carry the SAME value. Check:
         connector.limit_per_host >= connector.limit holds at every legal setting value, and no
         fraction, offset or separate constant appears.
      5. NO WIDENED `except` CLAUSE. _try_single_download_attempt still catches aiohttp.ClientError
         only; _fetch_single_playlist still catches (aiohttp.ClientError, TimeoutError);
         downloader_throttle.py's parallel path still catches (aiohttp.ClientError, TimeoutError) under
         its INT-006 comment. The asymmetry between the segment path and the throttle path is a
         SEPARATE observation — recorded in the report per D5, escalated in plan 09 §11 as E3, and
         NOT fixed here. Check: all three except clauses are byte-identical before and after.
      6. NO NEW `src/` FILE and NO NEW `tests/` FILE. Check: `git diff --cached --stat` lists only the
         six files this block names, five modified and none added.
      7. NO NEW `Settings` FIELD, NO `.env.example` ENTRY, NO CLI OPTION. Remedy (a) adds no field.
         The three-place rule, the extra="forbid" upgrade check and the EXPECTED_SDIST_ENTRIES review
         therefore do not arise. Check: config.py gains no `Field(` other than a description edit, and
         .env.example is byte-identical before and after.
      8. NO NAMED CONSTANT for the ceiling and NO aiohttp OR asyncio IMPORT IN config.py. The
         derivation belongs in segment_downloader.py; the value is derived, not declared; rule 10 is
         not engaged and no enum member is added.
      9. NOTHING STAGED FROM `.ai/audit/`, `.ai/plans/`, `.ai/problems/` OR `tmp/`. Stage by explicit
         path only. The ten pre-existing `.ai/` working-tree entries and the untracked plans are NOT
         this block's and must not ride along — `git add -A` and `git add .` are forbidden.
      10. NO CHANGE TO `.ai/templates/audit-findings.md`, to `.kilo/rules/*`, or to
         docs/00-overview/doc-maintenance-rules.md. D3 and D7 make all three a gate failure.
    code_hint: |
      # the checks above are mechanical — run these and read the output, do not assert from memory:
      #   uv run pytest -q
      #   uv run ruff check src tests
      #   uv run ruff format --check src tests
      #   uv run mypy src
      #   git diff --cached --stat
      #   git status --short
      #   git diff --exit-code HEAD -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
      #   git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
      #   git diff -U0 -- src/vkdownloader/services/segment_downloader.py | Select-String "except"   # expect NO output

acceptance_criteria:
  - The connector's limit follows a declared setting; no literal 10 remains in _create_connector
  - limit_per_host carries an explicit value, and the report states it is INTENTIONALLY non-binding
  - The ssl_verify branch, its ssl_context construction and its ssl_verification_disabled warning are preserved
  - No process-wide pool exists and the block claims none
  - The D-01 comment above the segment semaphore is re-read and accurate after the change
  - >
    The report states the arithmetic EXACTLY in this shape, both deltas, yt-dlp excluded by name.
    CAREFUL — min(limit, limit_per_host) is only a valid ceiling when limit_per_host is POSITIVE,
    because 0 is aiohttp's unbounded sentinel, not a ceiling of zero. Quote the derivation, not the
    shorthand; a reader who evaluates min(10, 0) literally will find 0 and conclude the report is wrong.
    Today — per-download limit=10 constant; per-origin limit_per_host=0 which is UNBOUNDED, not zero;
    the total term admits 10 connections per download and the segment semaphore admits N in-flight
    transfers, so effective per-video concurrency is min(10, N) with whichever is smaller — and for N
    in 11..16 that is the connector, which IS CON-009; aggregate 10 x N = 40 at N=4 and 160 at N=16;
    no process-wide bound.
    After — per-download limit=N and per-origin limit_per_host=N, both positive and equal, so
    min(N, N) = N genuinely applies and NO request ever queues for a connector slot; aggregate
    N x N = 16 at N=4 and 256 at N=16; no process-wide bound.
    Deltas — 40 -> 16 at the default FALLS; 160 -> 256 at the ceiling RISES. State both. Quoting
    only one is as wrong as quoting only the other.
    Excluded — yt-dlp's own -N connections are NOT counted in this arithmetic. yt-dlp runs as a
    SEPARATE CHILD PROCESS with its own sockets and its own transport; it does not share this
    connector. Exclude it by name so no reader adds its sockets to the aggregate.
  - The report states the ownership handover from plan 07's B14 and that plan 07's blocks are landed
  - The report records the exception-catch asymmetry, states that limit=N REMOVES its exposure, and
    states that neither except clause was widened
  - The report names the aiohttp version verified against (3.14.1) and records that the per-origin
    non-binding property was MEASURED on the installed version, not assumed from documentation
  - The report carries the research deliverable's load-bearing claims INLINE — a commit citing tmp/ as
    its evidence is a gate failure
  - The new test is @pytest.mark.asyncio, builds Settings itself, closes every connector, reads only
    public properties, never drives a request through a connector, and asserts equality to the
    PARAMETER rather than to a constant
  - The suite's warning count is still exactly 1
  - The four D-11 Windows-confinement skips are still exactly 4
  - tests/test_config.py is green UNCHANGED; the four pytest.fail hang nets in
    tests/test_segment_downloader.py are green UNCHANGED
  - No new src/ or tests/ file
  - pytest, ruff check, ruff format --check and mypy all pass
  - git diff --cached --stat shows only this block's files
  - The D-01 comment is re-read and its third-bound clause added in the SAME commit, and its existing
    reentrancy and deadlock sentences are left intact
  - config.py's max_concurrent_downloads field description and docs/11-guides/configuration.md's
    max_concurrent_downloads TABLE ROW and PROSE SECTION all name THREE levels; the guide's example
    value is unchanged; .env.example is byte-identical and the report says the omission is deliberate
  - docs/01-tools/vkdownloader-overview.md's Shared Concurrency Control section carries the first
    mention of a transport connection ceiling anywhere in docs/, states that the connector is per
    download, and states that no process-wide pool exists
  - READ-ONLY GATE, AS AMENDED BY D2 — BOTH commands, both must pass, over the two corpus paths
    (.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md and
    .ai/audit/04-concurrency-cancellation/findings.md). A GREEN git diff with a RED git ls-files is a
    FAILURE, never a pass. No new guard, CI check or repository file is added (D2); this section is
    the guard.
  - D5 verbatim — the segment-path exception-catch asymmetry is recorded prominently in the report,
    the report states that limit = N REMOVES its exposure, and NEITHER except clause is widened. No
    new finding, no new ID and no new audit artifact is created by this block; the follow-up is
    plan 09 §11 E3, owned by phase 03.
  - D3 verbatim — .ai/templates/audit-findings.md is left exactly as it is and the report records it
    as untouched drift, not a fix.
  - D6 verbatim — tmp/ is never committed. The block report AND the commit body carry the
    load-bearing claims and the verified arithmetic INLINE. A commit citing a tmp/ path as its
    evidence is a gate failure. Stage by explicit path; git add -A and git add . are forbidden,
    because ten pre-existing .ai/ working-tree entries would ride along.
  - D7 verbatim — rule 14 governs the docs. No new doc page, no new doc structure, and
    docs/00-overview/doc-maintenance-rules.md is NOT rewritten.
  - The report carries the re-verification inline INCLUDING the two corrections recorded in plan 09
    §6.2 — the corrected unclosed-connector mechanism and the corrected min() sentinel nuance. The
    Implementor states the corrected facts, not this plan's superseded wording
  - The report states the remedy selection, the four rejected alternatives and why each was rejected
  - The report states the residual risk honestly — the change does NOT create a process-wide bound,
    N squared is still the ceiling, and at N=16 that is 256 connections. Anyone reading "one setting
    governs the whole process" as "the process is now bounded" is wrong, and the report must not say so
  - git status --short showed src/, tests/ and docs/ CLEAN before staging, so every file in this
    block's change set is this block's and nothing else rode along

# §8 END GATES — the four command gates, the two read-only commands, and the exact file list.
end_gates:
  commands_all_must_pass:
    - uv run pytest -q                      # >= 762 passed, exactly 4 skipped, exactly 1 warning
    - uv run ruff check src tests           # All checks passed!
    - uv run ruff format --check src tests  # files already formatted
    - uv run mypy src                       # Success: no issues found
  read_only_gate_D2_both_commands_required:
    - git diff --exit-code HEAD -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
    - git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
  files_this_block_may_stage_all_modified_none_added:
    - src/vkdownloader/services/segment_downloader.py
    - src/vkdownloader/config.py
    - tests/test_segment_downloader.py
    - docs/11-guides/configuration.md
    - docs/01-tools/vkdownloader-overview.md
    # five. There is no sixth file: the block report is returned as the block's deliverable text
    # unless the Implementor is also this block's Implementor, and nothing under .ai/ is staged.

planner_verification: |
  The block's Planner re-measured all twelve load-bearing claims against the live tree and the
  installed aiohttp before writing this task. The full table is plan 09 §6.2. Ten hold unchanged.
  Two are CORRECTED and this task is written against the corrected facts:
    - The unclosed-connector warning mechanism is FALSIFIED. aiohttp 3.14.1's BaseConnector.__del__
      returns early when the connection pool is empty, so a connector that was built and read but
      never opened a connection emits nothing. The rule (close every connector) stands on three other
      grounds, restated in changes[3].
    - min(limit, limit_per_host) is a valid ceiling ONLY when limit_per_host is positive. 0 is
      aiohttp's unbounded sentinel. Measured on the unfixed tree the expression returns 0. The report
      and commit body must quote the derivation, not the shorthand.
  Verified and relied upon: the two limit=10 return paths with limit_per_host absent and no resolver=;
  the ssl_verify branch, its ssl_context construction and its ssl_verification_disabled warning; the
  sole call site in _run_download_session with one connector and one ClientSession per call and
  teardown delegated to the session; the segment semaphore and the is_bounded_batch flag; Settings'
  ge=1, le=16 and default 4; limit and limit_per_host as public read-only properties; the effective
  per-origin ceiling's dependence on limit_per_host being positive; both ClientTimeout.connect values
  and all three except clauses; zero aiohttp references in tests/; and RuntimeError on synchronous
  construction.

remedy_selection: |
  SELECTED (a) — derive BOTH the total and the per-origin ceiling from Settings.max_concurrent_downloads
  and pass the SAME value to both. No new setting. Full reasoning and the four rejected alternatives
  are under changes[0].description; the plan's own summary is that (a) is CON-009's recommendation, is
  plan 08's recorded default, is the smallest change rule 5 asks for, and is provably free of
  behavioural risk because limit_per_host == limit can never be the binding term.

baseline_recorded_by_the_planner: |
  Plan 09 §2.4 forbids inheriting a baseline, so the Planner ran these as its own first action at
  HEAD 0a8fa97d81f48fe4faac289b3fbbbfa5a567b8b1 on Windows. Verbatim:

    uv run pytest -q
      762 passed, 4 skipped, 1 warning in 38.01s
      (the 1 warning is tests/test_downloader_throttle.py::TestProgressManager::
       test_overwrites_existing_progress — RuntimeWarning: coroutine 'Event.wait' was never awaited —
       pre-existing and unrelated to CON-*)
      (the 4 skips are the D-11 Windows-confinement pair in tests/test_config.py and the same pair in
       tests/test_hls_downloader.py)

    uv run ruff check src tests
      All checks passed!

    uv run ruff format --check src tests
      54 files already formatted

    uv run mypy src
      Success: no issues found in 31 source files

    git status --short
      only the ten .ai/ entries plan 09 §2.4 enumerates as pre-existing:
        D .ai/audit/03-network-resilience/findings.md
        D .ai/plans/00_overview.md
        D .ai/plans/01_backend_connector.md
        D .ai/plans/02_notification_provider.md
        D .ai/plans/03_security_state.md
        D .ai/plans/04_lifecycle_config_testing.md
        D .ai/plans/VALIDATION_REPORT.md
        D .ai/plans/error_ref.md
        M .ai/problems/PROBLEM.md
      plus untracked plans 05 through 09 and tmp/.
      src/, tests/ and docs/ are CLEAN — the research deliverable's caveat that
      docs/01-tools/vkdownloader-overview.md was dirty is DEAD; the quality-selection work landed in
      7d02a30. Stage the five files by explicit path.

  The read-only gate was also measured at HEAD: `git diff --exit-code HEAD` over the two corpus paths
  exits 0, and `git ls-files --error-unmatch` prints both paths and exits 0. BOTH are required (D2).

  The Implementor re-measures all four commands and diffs against this record rather than trusting it.
```

### B9

```yaml
id: plan09-b9-exit-path-thread-join-bound
title: State the exit-path thread-join bound where the timeout is configured
priority: medium
depends_on: []

source_reference: .ai/plans/09-concurrency-cancellation-audit-fixes-completion.md
predecessor_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B9 — State the exit-path thread-join bound where the timeout is configured
source_blocks: ["B9"]
source_findings: ["CON-010"]

description: >
  Two shipped strings in this repository assert something false about the same
  mechanism, and that falsity is what CON-010 records. The first is
  `Settings.download_timeout`'s Pydantic field description: it names only the
  segment and playlist HTTP consumers, so it is a partial truth about a setting
  that in fact bounds four consumer classes, and it states no bound at all for
  the path where the setting is NOT the bound. The second is the
  `_extract_with_ytdlp` docstring and the `INT-003` comment above the executor
  dispatch, which both claim the `asyncio.wait_for` wrap means a hung yt-dlp
  extraction "cannot block ... indefinitely" — true of the event loop, false of
  the process, which `asyncio.run` holds open while it joins the abandoned
  executor thread during teardown.

  D9 settled the remedy: option (a), documentation only. Measured on this
  platform, every code remedy either relocates the wait to
  `concurrent.futures.thread._python_exit` at interpreter exit with total
  process time unchanged, or is disproportionate; `asyncio.to_thread` is
  measured identical; and nothing in `tests/` observes the mechanism, so none of
  it is verifiable here. This task therefore changes three strings and adds one
  guard, and changes no behaviour whatsoever.

  The one judgement this Planner had to make and the Implementor must not
  re-open is the WORDING of the new field description. D8 item 1 forbids both
  "300 s" (false on the pinned CPython 3.12.1, where the thread-join timeout is
  not applied) and "unbounded" (false from 3.12.2, where it is). The wording
  drafted below is the resolution and is supplied ready to paste.

goals:
  - id: g1
    text: >
      Replace `Settings.download_timeout`'s `Field(description=...)` string with
      the drafted wording, which (a) names all four consumer classes the setting
      actually bounds, (b) states that the abandoned extraction thread is joined
      at interpreter shutdown under the interpreter's own thread-join rule, and
      (c) states that that rule — not this setting — is the bound on that path.
      It contains no number, so it is true on CPython 3.12.1 and on 3.12.2+.
  - id: g2
    text: >
      Correct the `_extract_with_ytdlp` docstring and the `INT-003` comment
      above the executor dispatch so both state the loop-vs-process distinction
      and the absence of a bound on the process side. Documentation only — the
      method body is byte-for-byte unchanged.
  - id: g3
    text: >
      Add one test class to `tests/test_config.py` pinning the description's
      semantic invariant (consumer completeness, exit-path subject named,
      "not the bound here" stated) by narrow tokens, never by full-string
      equality. This will be the repository's only assertion on a
      `Field(description=...)` string, so it must be robust to rewording.
  - id: g4
    text: >
      Re-read `docs/11-guides/vkdownloader-limitations.md`'s yt-dlp
      executor-thread passage and record the verdict. The Planner's verdict is
      that it stays accurate under (a) and is therefore read-only; the
      Implementor confirms and does not edit it.
  - id: g5
    text: >
      Produce a report that closes CON-010's first recommendation clause
      ("state the exit-path bound where the timeout is configured") and records
      plainly that the second clause ("lower it for this call site") is NOT
      taken, so the residual stall is ACCEPTED.

files:
  - path: src/vkdownloader/config.py
    targets:
      - Settings.download_timeout (Field(description=...))
    semantic_anchors:
      - replace: the `description=` argument of the `download_timeout` Field only
  - path: src/vkdownloader/services/extractor.py
    targets:
      - VKVideoExtractor._extract_with_ytdlp
    semantic_anchors:
      - replace: the method's docstring
      - replace: the comment block whose first line begins "Run in thread pool to avoid blocking"
  - path: tests/test_config.py
    targets:
      - TestDownloadTimeoutDescriptionStatesTheExitPath (new class)
    semantic_anchors:
      - add: a new plain class at end of module, no base class, no fixture
  - path: docs/11-guides/configuration.md
    targets:
      - the `download_timeout` table row
    read_only: true
    reason: >
      Tech Lead D1 — untouched. The field description in `config.py` is the doc
      of record; the row is a true-but-incomplete operator summary. Escalated,
      not edited.
  - path: docs/11-guides/vkdownloader-limitations.md
    targets:
      - the "yt-dlp cancellation in batch mode" limitation item
    read_only: true
    reason: >
      Verified accurate under (a) — see `planner_verification.docs_verdict`.
      Nothing in this change makes it wrong, so it is not edited.
  - path: src/vkdownloader/services/extractor.py
    targets:
      - VKVideoExtractor._extract_with_ytdlp / ydl_opts / the INT-003 comment above "socket_timeout"
    read_only: true
    reason: >
      Re-read and confirmed accurate ("propagate Settings to yt-dlp library-mode
      so it respects the same timeout/retry/throttle config as the subprocess
      CLI path"). Unchanged by this block; do not fold the two INT-003 comments
      together.

changes:
  - action: modify
    description: >
      Replace the `download_timeout` field description. This is the doc of
      record for what the setting bounds, and CON-010's entire remedy under D9
      lands in this string.
    code_hint: |-
      BEFORE (one line, current):
          download_timeout: int = Field(
              default=300,
              ge=30,
              le=3600,
              description="HTTP client timeout in seconds for individual segment requests and playlist fetches.",
          )

      AFTER (paste exactly; implicit string concatenation, so the resulting
      description is ONE line with no newline character inside it — the file's
      existing idiom for long descriptions, as on `max_concurrent_downloads`,
      `http_chunk_size` and `backoff_pause_seconds`):
          download_timeout: int = Field(
              default=300,
              ge=30,
              le=3600,
              description="Timeout in seconds applied to individual segment and playlist "
              "HTTP requests, to each ffmpeg merge subprocess, to the off-loop yt-dlp "
              "extraction's wait_for, and to yt-dlp's socket timeout as a library option and "
              "as a CLI flag. On expiry of that wait_for the extraction thread is not "
              "stopped and is joined at interpreter shutdown under the interpreter's own "
              "thread-join rule, not under this setting.",
          )

      Nothing else in the field changes: `default=300`, `ge=30`, `le=3600` are
      untouched. `config.py` gains NO import — it does not import `asyncio`
      today and must not; the description string is the only carrier of this
      fact.

  - action: modify
    description: >
      Correct the `_extract_with_ytdlp` docstring. The current text claims the
      wrap means the event loop "is not blocked indefinitely", which is true of
      the loop and false of the process.
    code_hint: |-
      BEFORE:
          """Extract streams and title using yt-dlp (handles VK protections).

          Propagates relevant :class:`Settings` fields (``socket_timeout``,
          ``retries``, ``fragment_retries``, ``throttled_rate``) into the
          yt-dlp options dict and wraps the blocking extraction in
          ``asyncio.wait_for`` with ``settings.download_timeout`` so the
          event loop is not blocked indefinitely (INT-003).
          """

      AFTER:
          """Extract streams and title using yt-dlp (handles VK protections).

          Propagates relevant :class:`Settings` fields (``socket_timeout``,
          ``retries``, ``fragment_retries``, ``throttled_rate``) into the
          yt-dlp options dict and wraps the blocking extraction in
          ``asyncio.wait_for`` with ``settings.download_timeout`` (INT-003).

          The wrap bounds the EVENT LOOP, not the PROCESS: on expiry the
          asyncio future is cancelled, but the executor thread is not and
          cannot be. ``asyncio.run`` joins that thread while tearing the
          interpreter down, so the process can stay alive after the
          ``ExtractionError`` has been raised. That exit-path wait is
          bounded by the interpreter's own thread-join rule, NOT by
          ``download_timeout``, and no bound is applied to it here
          (CON-010).
          """

      Scope note: the first paragraph's field list is preserved verbatim. It
      calls `socket_timeout` a `:class:`Settings`` field name, which is
      imprecise — `socket_timeout` is the yt-dlp option name, the Settings
      field is `download_timeout`. That imprecision predates this block and is
      NOT fixed here; record it in the report as an observation. Do not widen
      the diff to cover it.

  - action: modify
    description: >
      Correct the `INT-003` comment above the executor dispatch. This is the
      second of the two `INT-003` comments in this method; the first sits above
      the `"socket_timeout"` entry in `ydl_opts` and is accurate and read-only.
    code_hint: |-
      BEFORE (the comment block immediately preceding the
      `if self.backoff_coordinator is not None:` guard):
          # Run in thread pool to avoid blocking, with a timeout (INT-003)
          # so a hung yt-dlp extraction cannot block the event loop
          # indefinitely.

      AFTER:
          # Run in thread pool to avoid blocking, with a timeout (INT-003)
          # so a hung yt-dlp extraction cannot block the EVENT LOOP
          # indefinitely. It does not bound the PROCESS: on expiry only the
          # asyncio future is cancelled and the executor thread cannot be, so
          # asyncio.run joins that thread at teardown under the interpreter's
          # own thread-join rule, not under this setting, and no bound is
          # applied to that path (CON-010).

      This comment is the FIRST statement of the tail of the method: the
      `backoff_coordinator` guard, `loop = asyncio.get_running_loop()` and the
      `asyncio.wait_for(loop.run_in_executor(...))` call all follow it. It is a
      comment, so moving it is not required and would be gratuitous churn —
      replace its text in place and leave its position alone.

  - action: add_test
    description: >
      Add ONE new plain class to `tests/test_config.py`. It is the repository's
      only assertion on a `Field(description=...)` string, so it pins three
      SEMANTIC FACTS by narrow token and never the sentence. Full-string
      equality is deliberately rejected: prose fields fail on any reword, which
      is a maintenance cost with no oracle value (rule 5 — a test that fails on
      a mere rewording would push an Implementor to distort the documentation).
    code_hint: |-
      Add `import re` to the stdlib import block of tests/test_config.py
      (between `import os` and `import subprocess`; isort order). This is the
      ONLY new import in the block, and it is in a test file — the "config.py
      gains no import" prohibition is scoped to src/vkdownloader/config.py and
      is not relaxed by this.

      Then append this class at the end of the module:

          class TestDownloadTimeoutDescriptionStatesTheExitPath:
              """CON-010: download_timeout's description is the doc of record, and
              CON-010's remedy under D9 is a statement in it that may not be a
              partial truth.

              Three semantic facts are pinned, never the wording. Full-string
              equality is deliberately not used: the description is prose, and
              a test that failed on any reword would be a maintenance cost with
              no oracle value (rule 5).

                1. every consumer class the setting actually bounds is named;
                2. the exit-path subject -- the abandoned extraction thread
                   joined at interpreter shutdown -- is named;
                3. the description states that THIS SETTING is not the bound
                   applied on that path.
              """

              # Consumer classes, each verified present in src/: segment and
              # playlist HTTP (segment_downloader.py aiohttp.ClientTimeout and
              # downloader_throttle.download_segment_throttled);
              # each ffmpeg merge subprocess (segment_downloader.py ->
              # ffmpeg_utils._merge_segments_batched -> _merge_batch_segments
              # and _perform_final_merge, via policy.download_timeout);
              # the off-loop extraction's wait_for
              # (VKVideoExtractor._extract_with_ytdlp); and yt-dlp's socket
              # timeout as BOTH a library option (the ydl_opts dict) and a CLI
              # flag (ytdlp_downloader._build_ytdlp_cli_command's
              # --socket-timeout).
              _CONSUMER_TOKENS = (
                  "segment",
                  "playlist",
                  "ffmpeg",
                  "yt-dlp",
                  "extraction",
              )

              # The mechanism is CPython's thread-pool join, so any wording
              # that still states the finding must name the thread, the
              # executor, or the shutdown. An "any of three" test rather than
              # one fixed word keeps a legitimate rewording green.
              _EXIT_PATH_SUBJECT_TOKENS = ("thread", "executor", "shutdown")

              # "this setting is not the bound on that path", in the ordinary
              # English forms that claim takes. The character class forbids a
              # sentence break between the negator and its referent, so a
              # negation about some other subject cannot satisfy it.
              _EXIT_PATH_DISCLAIMER_RE = re.compile(
                  r"\b(?:not|never|no|neither|rather|instead)\b[^.?!]*"
                  r"\b(?:this setting|download_timeout|this timeout)\b",
                  re.IGNORECASE,
              )

              def _description(self) -> str:
                  description = Settings.model_fields["download_timeout"].description
                  assert isinstance(description, str), (
                      "download_timeout must carry a description -- it is the doc "
                      f"of record for what the setting bounds; got {description!r}"
                  )
                  return description

              def test_names_every_consumer_class_the_setting_bounds(self) -> None:
                  """A description corrected to name three of four is still wrong."""
                  lowered = self._description().lower()

                  missing = [t for t in self._CONSUMER_TOKENS if t not in lowered]
                  assert not missing, (
                      "download_timeout's description must name every consumer class "
                      f"the setting bounds; missing {missing} from "
                      f"{self._description()!r}"
                  )

              def test_names_the_exit_path_subject(self) -> None:
                  """CON-010's first clause: state the exit-path bound here."""
                  lowered = self._description().lower()

                  assert any(t in lowered for t in self._EXIT_PATH_SUBJECT_TOKENS), (
                      "download_timeout's description must name the exit-path "
                      "subject -- the extraction thread joined at interpreter "
                      f"shutdown; found none of {self._EXIT_PATH_SUBJECT_TOKENS} "
                      f"in {self._description()!r}"
                  )

              def test_states_this_setting_is_not_the_exit_path_bound(self) -> None:
                  """D8 item 1: the description must disclaim the exit path."""
                  description = self._description()

                  assert self._EXIT_PATH_DISCLAIMER_RE.search(description), (
                      "download_timeout's description must state that this setting "
                      "is not the bound applied on the exit path (a negator and "
                      "'this setting'/'download_timeout' in one clause); got "
                      f"{description!r}"
                  )

  - action: prohibited
    description: >
      Do not touch `ExtractionError`'s message and do not touch the
      `ytdlp_extraction_timeout` log record — Tech Lead D9 preserves both
      unchanged, and the report must show them byte-identical in the diff. Do
      not raise a `TimeoutError` earlier than `asyncio.wait_for` does, and do
      not change what the operator is promised. Do not add an import to
      `src/vkdownloader/config.py`. Do not create any new file under `src/` or
      `tests/`. Do not act on or re-reference `CFG-002` — the "See also" in
      CON-010's validation note is misattributed (its subject is the setting's
      meaning, bound and validation, not the exit path) and is explicitly out of
      scope. Do not file or widen anything on the segment-path exception-catch
      asymmetry (D5; already escalated as §11 E3, owned by phase 03). Do not
      raise the interpreter floor to >=3.12.2 (D8 item 4; that is §11 E6, out of
      scope). Do not edit `docs/11-guides/configuration.md`'s `download_timeout`
      row or prose (D1). Do not commit `tmp/` (D6), and do not commit anything
      under `.temp/` — it is gitignored, but confirm the staged set explicitly.

accept_the_remedy: |-
  Three files change. Nothing else in the tree moves.

    src/vkdownloader/config.py                             (1 hunk: the description string)
    src/vkdownloader/services/extractor.py                 (2 hunks: docstring, INT-003 comment)
    tests/test_config.py                                   (1 hunk: 1 import + 1 new class)

  The two hunks in config.py and extractor.py are documentation only. The
  method body of `_extract_with_ytdlp` — the `ydl_opts` dict, `_sync_extract`,
  the `backoff_coordinator` guard, the `asyncio.wait_for`, the `except
  TimeoutError` arm, the `ExtractionError` construction and the
  `ytdlp_extraction_timeout` record — is byte-for-byte unchanged. This is the
  load-bearing claim of the whole block and the report must demonstrate it with
  `git diff` restricted to the file, not assert it.

planner_verification:
  performed_by: Planner, on commit 514a210, independent of the Researcher's deliverable
  baseline:
    command: uv run pytest -q
    result: "769 passed, 4 skipped, 1 warning in 36.55s"
    other_gates: |
      uv run ruff check src tests          -> "All checks passed!" (exit 0)
      uv run ruff format --check src tests -> "54 files already formatted" (exit 0)
      uv run mypy src                      -> "Success: no issues found in 31 source files"
    note: >
      Plan 09 §2.1/§8.1 record a floor of 762 passed; that figure is stale
      because B8 landed as 514a210 immediately before this block. The measured
      baseline is 769, and the gate is >= 769 passed.
  interpreter_facts_reverified_from_the_installed_source:
    - "asyncio.constants.THREAD_JOIN_TIMEOUT == 300 on the pinned 3.12.1"
    - "asyncio/runners.py calls loop.shutdown_default_executor(constants.THREAD_JOIN_TIMEOUT)"
    - >
      asyncio/base_events.py shutdown_default_executor(self, timeout=None) awaits the
      shutdown future UNBOUNDED and only then does thread.join(timeout) in a finally.
      _do_shutdown resolves that future solely after
      self._default_executor.shutdown(wait=True) returns, i.e. after every pool
      thread has finished. So on 3.12.1 the join timeout can never bind and the
      RuntimeWarning branch is unreachable. Confirmed directly by the
      Researcher's scaled-cap runs: shutdown_default_executor(3.0) on a 20 s
      thread returned only at 20.016 s with no warning raised.
    - "the CLI reaches that path: src/vkdownloader/cli.py uses asyncio.run(...) for both the single and the batch command"
    - "pyproject.toml declares requires-python = '>=3.12' — the floor that makes 3.12.1 the pinned interpreter (§11 E6)"
  no_description_reader:
    claim: >
      No code and no test reads a Pydantic `Field(description=...)` string, so
      rewording the description cannot change behaviour.
    evidence: >
      Repo-wide search for `.description` across all .py files returns only
      `progress_display.py`'s `description=` keyword for rich-console tasks
      (unrelated) and a `TextColumn("{task.description}")` format string. A
      search for `json_schema|model_json_schema|FieldInfo` returns nothing that
      reads a description. `Settings.model_fields[...]` is read in exactly three
      places — config.py's own `normalize_download_dir`,
      downloader_throttle.py's `_DEFAULT_DOWNLOAD_TIMEOUT`, and tests/conftest.py
      plus tests/test_config.py's `max_retries` bounds test — and all of them
      read `.default` or `.metadata`, never `.description`.
    safety_of_rewording: >
      downloader_throttle.py reads
      `Settings.model_fields["download_timeout"].default` at import time. Only
      the `description` keyword changes, so that binding is unaffected.
      Confirmed by the unchanged 769-passing baseline.
  test_extractor_cannot_observe_this:
    test: "tests/test_extractor.py :: TestExtractionErrors :: test_extract_with_ytdlp_timeout_raises_extraction_error"
    reason: >
      It patches `asyncio.wait_for` with a `fake_wait_for` that raises
      `TimeoutError` immediately, and separately patches
      `asyncio.get_running_loop`. The coroutine handed to the fake `wait_for` is
      never awaited, so `run_in_executor` is called on a MagicMock and its
      result discarded: NO executor thread is ever created, so there is nothing
      for `shutdown_default_executor` to join and `THREAD_JOIN_TIMEOUT` is never
      consulted. The test exercises only the `except TimeoutError` arm — the
      `ytdlp_extraction_timeout` record and the `ExtractionError` message —
      which D9 preserves unchanged. It therefore cannot observe the mechanism
      and is correctly left untouched.
  docs_verdict:
    file: docs/11-guides/vkdownloader-limitations.md
    passage: >
      "yt-dlp cancellation in batch mode - yt-dlp runs in an executor thread that
      cannot be terminated by `asyncio.CancelledError`; the thread persists as a
      zombie until process exit. This is a CPython `concurrent.futures` limitation:
      `Future.cancel()` returns `False` for running futures. No workaround within
      the current architecture."
    verdict: >
      STAYS ACCURATE — read-only, not edited. Option (a) changes no runtime
      behaviour, so all three claims are unaffected. It is in fact BETTER
      SUPPORTED than before: "No workaround within the current architecture" was
      previously an assertion, and D9's measurements (options (b)/(c) relocate
      the wait to `concurrent.futures.thread._python_exit` with total process
      time unchanged; `to_thread` identical; subprocess and ProcessPoolExecutor
      disproportionate and untestable) turn it into a measured result. The
      passage would only become wrong if the change altered the executor
      mechanism, which it does not. No edit is required or permitted.
  research_deliverable_caveat:
    note: >
      `.temp/b9/` contains BOTH successful and failed runs, and the failures are
      not obvious from the listing. Every `out_*.txt` file is the output of
      `probe.py` and is a FAILED run — it aborts with
      `TypeError: 'str' object is not callable`, and the text is UTF-16 because
      PowerShell redirection encoded it. Do not cite any `out_*.txt` as evidence.
      The load-bearing artefacts are the `M_*.log`, `N_*.log`, `P_*.log`,
      `R_*.log` and `T_shipped2.log` files, written by the later probes with
      explicit UTF-8 handles. Spot-checked and confirmed: M_default (asyncio.run
      returns only when the thread finishes), M_custom_no_shutdown (asyncio.run
      returns at 1.016 s with the thread still alive, yet the process still
      exits at 4.031 s — the stall RELOCATES to interpreter exit, total process
      time unchanged), M_to_thread (identical to M_default), P_cap
      (shutdown_default_executor(2.0) still returned at 8.015 s for a thread
      finishing then), R_cap20_3 (shutdown_default_executor(3.0) on a 20 s thread
      returned at 20.016 s with `warnings raised during shutdown: []` — the cap
      is provably not applied on 3.12.1), and T_shipped2 (shipped call shape:
      ExtractionError raised at 1.703 s, asyncio.run returned only at 8.734 s — a
      7 s silent stall after the error was reported; also confirms the current
      description string verbatim and that `socket_timeout` reaches yt-dlp).
  d9_not_reopened: >
    The fork is closed by the Tech Lead and this task does not re-argue it. The
    Planner re-verified the load-bearing interpreter facts that the selected
    option (a) rests on (above) and found them accurate. No code remedy is
    proposed, evaluated or partially adopted anywhere in this task.

extra_context:
  binding_decisions: |
    D1  docs/11-guides/configuration.md's `download_timeout` table row and prose
        are NOT touched. The field description in config.py is the doc of record
        and the row is a true-but-incomplete operator summary. ESCALATE, do not
        edit. Coordination obligation, in the report: name plan 07's C12, name
        the row, and name the trigger — if the field description grows consumer
        classes, the row's summary stops covering the setting and must be
        revisited by whoever owns that row, not here.
    D2  Read-only gate is TWO commands, and both must pass:
          git diff --exit-code HEAD -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
          git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
        A green diff with a red ls-files is a FAILURE. (Planner: both exit 0
        before this task starts.)
    D5  The segment-path exception-catch asymmetry is NOT this block's. B9
        neither files it nor widens anything.
    D6  tmp/ is never committed. Evidence goes inline in the report and in the
        commit body. `.temp/` is gitignored; confirm the staged set anyway.
    D8  No number in the operator-facing description. No generalisation beyond
        the measured platform. No claim about real-origin behaviour. Raising the
        interpreter floor to >=3.12.2 is OUT OF SCOPE (escalated as §11 E6).
    D9  ExtractionError's message and the ytdlp_extraction_timeout log record
        are PRESERVED UNCHANGED. The remedy is (a), documentation only.
  platform_specific_truth_goes_here_not_in_the_description: |
    The measured, version-specific detail belongs in the report and the commit
    body, NOT in config.py. That includes: CPython gh-111358 by number; that on
    3.12.1 the join timeout is not applied and the abandoned thread is joined for
    its full remaining lifetime; that 3.12.2+ (upstream PR 115622, 3.12 backport
    115641, merged 2024-02-18) applies the 300 s cap; and the explicit statement
    that download_timeout is not the bound on that path. The operator
    description carries the mechanism, not the version matrix.
  report_obligations: |
    1. The residual stall is ACCEPTED. CON-010's recommendation has two clauses
       — "state the exit-path bound where the timeout is configured" and "lower
       it for this call site". Option (a) closes the FIRST and NOT the second.
       Say so plainly. Do NOT claim the recommendation was fully met.
    2. Record that the lowering half is NOT TAKEN, and why: options (b)/(c)
       relocate the wait to `concurrent.futures.thread._python_exit` at
       interpreter exit with total process time unchanged; `asyncio.to_thread` is
       measured identical; subprocess and `ProcessPoolExecutor` work but are
       disproportionate and untestable; a bare daemon thread is untestable; and
       nothing in `tests/` observes the mechanism, so no remedy is verifiable
       here.
    3. Record the interpreter-floor escalation (E6): the pinned CPython 3.12.1
       carries gh-111358, so the documented cap is not real on this interpreter;
       raising the floor to >=3.12.2 is the only change that bounds the
       exit-path wait, and it is a dependency/interpreter decision, not this
       block's.
    4. Record the D1 coordination obligation (plan 07's C12, the
       configuration.md row, the trigger).
    5. Record that config.py gained NO import and that the description string is
       the only carrier of this fact.
    6. Record the no-description-reader verification and that
       downloader_throttle.py reads `.default`, so the rewording is safe.
    7. Record the vkdownloader-limitations.md verdict: stays accurate, read-only,
       better supported than before.
    8. Record the D5 non-scope: nothing filed about the segment-path
       exception-catch asymmetry.
    9. Record the `socket_timeout`-as-a-Settings-field-name imprecision in the
       docstring as an observation, explicitly not fixed here.
    10. Do not cite the failed `out_*.txt` artefacts as evidence
       (see `research_deliverable_caveat`).
  commit_body_must_carry: |
    The two-branch truth (unbounded on 3.12.1, 300 s cap from 3.12.2, neither of
    which is this setting), the gh-111358 reference, and the statement that the
    residual is accepted and the lowering half is not taken.
  hard_boundaries: |
    - English only. No `print()` — use `logger = logging.getLogger(__name__)` /
      `get_logger(__name__)` as the surrounding code does. (No logging is added
      by this block at all.)
    - Small, focused change: three strings and one test class.
    - Documentation kept current — that IS the deliverable here.
    - Production code is king. If the new test conflicts with production code,
      fix the test, never the code. In practice the only production change is
      the description string, which no code reads.
    - Semantic code units only. Never line numbers, in the diff narration, in
      the report, or in the commit body.

acceptance_criteria:
  - "uv run pytest -q reports at least 769 passed, exactly 4 skipped, and exactly 1 warning (measured baseline: 769 passed, 4 skipped, 1 warning in 36.55s at commit 514a210)."
  - "The 4 skips are exactly the D-11 Windows-confinement skips; still exactly 4."
  - "uv run ruff check src tests exits 0."
  - "uv run ruff format --check src tests exits 0."
  - "uv run mypy src exits 0."
  - "tests/test_extractor.py is green and unchanged; `git diff -- src tests` shows no hunk in it, and the report records the reason it cannot observe this mechanism (the fake wait_for never awaits its coroutine, so no executor thread is ever created)."
  - "tests/test_config.py gains exactly one new class, TestDownloadTimeoutDescriptionStatesTheExitPath, with three test methods, plus one stdlib `import re`. No fixture, no base class, no conftest change."
  - "No new file anywhere under src/ or tests/; the new test class lives in the existing tests/test_config.py."
  - "`git diff -- src` shows exactly one hunk in src/vkdownloader/config.py's download_timeout Field and exactly two in src/vkdownloader/services/extractor.py (the _extract_with_ytdlp docstring and the INT-003 comment above the executor dispatch). No hunk touches the method body, the ydl_opts dict, the first INT-003 comment, the asyncio.wait_for call, the except TimeoutError arm, the ExtractionError construction, or the ytdlp_extraction_timeout record."
  - "The new download_timeout description contains no digit, is a single line with no newline character inside it, and asserts no version-specific, platform-specific or real-origin behaviour."
  - "The rewritten docstring and INT-003 comment both state the loop-vs-process distinction and the absence of a bound on the process side, and neither claims the loop can block indefinitely."
  - "git diff --exit-code HEAD -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md exits 0."
  - "git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md exits 0 and prints both paths. A green diff with a red ls-files is a failure."
  - "src/vkdownloader/config.py gains no import; it still does not import asyncio."
  - "docs/11-guides/configuration.md is untouched, and the report names plan 07's C12, the download_timeout row, and the escalation trigger."
  - "docs/11-guides/vkdownloader-limitations.md is untouched, and the report records that its yt-dlp executor-thread passage stays accurate under option (a)."
  - "git diff --cached --stat lists exactly the three files of this block and nothing else. The tree's pre-existing dirty entries (the tracked .ai/plans deletions, the .ai/problems/PROBLEM.md modification, the untracked plan files, and tmp/) are NOT staged."
  - "tmp/ is not committed and nothing under .temp/ is committed."
  - "The report states that the residual stall is accepted and that the lowering half of CON-010's recommendation is not taken; it does not claim the recommendation was fully met."
  - "The report carries the two-branch interpreter truth and the gh-111358 reference, and the commit body carries them too."
```

### B11

> **Rewritten by the `B11` block Planner at `HEAD = 8611a31`.** The Tech Lead's `D10` adopts the
> Researcher's remedy **(c) — no enum change**, and the fork this section previously left open is
> **closed**. Two facts about the tree are recorded here because they were measured, not inherited:
> **`B8` (`514a210`) and `B9` (`8611a31`) have landed**, so `B11` has no upstream block remaining and
> is the only unstarted block before `B10`; and **neither commit touched any of `B11`'s three files**,
> which were verified clean against `HEAD` before this specification was written.

```yaml
id: plan09-b11-unverified-severity-encoding
title: Give the report format a legal encoding for a not-executed finding
priority: medium
depends_on: []

source_reference: .ai/plans/09-concurrency-cancellation-audit-fixes-completion.md
predecessor_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: D10 (new, from the B11 Researcher pass) — remedy (c) is adopted, and the finding is re-characterised.
source_file: .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
source_blocks: ["B11"]
source_findings: ["phase04/VAL-404"]

description: >
  The finding was filed SPEC-DEVIATION against the report template, and D10 re-characterises it: THE
  FORMAT IS NOT THE DEFECTIVE SIDE; PHASE 04'S HANDBOOK IS. Eleven of the twelve phase handbooks and
  99-audit-validate.md "## 8" forbid "an OBSERVED severity" — a prohibition this remedy satisfies
  without a word changing. Only phase 04 forbids "severity" at all, at four sites, and one of them
  contradicts phase 04's OWN "## 9" LOW row, which already defines the band this block needs: "A
  shape, naming or structure deviation with no runtime consequence." The corpus has answered the
  question thirty times already: phase 08's OUT-010/OUT-011/OUT-012 are filed LOW with an UNVERIFIED
  marker, and the validator wrote, verbatim, "Severity: LOW, UNVERIFIED through the binary, correctly
  marked."
  THE ADOPTED REMEDY (c): NO ENUM CHANGE. Add a mandatory Verification field to the authoritative
  template as the machine-checkable carrier of UNVERIFIED; state there that when a runtime consequence
  was not observed the severity band is composed from the STRUCTURAL FACT under the owning phase's own
  severity table; reconcile phase 04's four "no severity" prohibitions to that rule; add the
  validator's matching check. PROSPECTIVE ONLY.
  REACH IS EXACTLY THREE FILES. The eleven sibling handbooks, audit-multi-phase.md, .kilo/agents/* and
  .ai/templates/audit-findings.md are NOT touched. No fifth type label is added, so D4's condition is
  not met and plan 08's prohibition on .kilo/agents/* stands absolutely.
  OWNERSHIP IS CLAIMED HERE; any future plan that would have carried phase04/VAL-404 must be struck.

goals:
  - a W-4-compliant report is legal against its own template
  - the template is the single place the not-executed encoding is defined, and phase 04 and the
    validation task are reconciled to it by reference rather than by restatement
  - the change is prospective — no existing finding's severity or type is rewritten, and the corpus's
    one historical non-conforming severity cell stays exactly as it is
  - three files change. Not four.

# ── REACH: exactly three files. Verified clean against HEAD before this specification was written. ──
files:

  - path: .ai/audit/templates/audit-findings.md
    description: >
      THE DECLARED AUTHORITY. Every one of the twelve handbooks, audit-multi-phase.md and
      99-audit-validate.md defer to it; phase 04's "## 9" and 99's "## 8" both open with "The
      findings template is the authority." It changes FIRST and it changes here — the reconciliation in
      the other two files derives from this one, never the reverse.
    targets:
      - type: section
        name: Findings
      - type: section
        name: Template Field Reference
      - type: section
        name: Classification Guide
    semantic_anchors:
      insert_after:
        type: table_row
        value: '| **Classification** | {mandatory\|advisory} |'
      insert_before:
        type: table_row
        value: '| `description` | string | Detailed problem description with context |'
      note: >
        TWO SEPARATE TABLES. The skeleton field table under "## Findings" (rows ID / Severity / Type /
        Affected Modules / Classification) receives the new Verification row. The Mandatory Fields Per
        Finding table under "## Template Field Reference" receives the new `verification` row and the
        rewritten `severity` row. Both are named because D10 item 8 requires the skeleton table in the
        anchor list; without it the new field would be written to an unlisted anchor.

  - path: .kilo/commands/audit/phases/04-audit-concurrency-cancellation.md
    description: >
      The defective side. Its four "no severity" prohibitions are reconciled to the template's
      composition rule. Its "## 9" and "## 12" UNVERIFIED sentences are ALREADY in the satisfied form
      ("never with an observed severity") and are NOT edited.
    targets:
      - type: section
        name: Preamble — binding rule 3
      - type: section
        name: Prerequisites
      - type: section
        name: Reporting
    semantic_anchors:
      note: >
        The preamble is not a numbered section; its anchor is the four-bullet list under the blockquote
        that opens the file. Each of the four amendments below is identified by the CURRENT TEXT of the
        sentence it replaces, quoted verbatim — never by position, which moves.

  - path: .kilo/commands/audit/phases/99-audit-validate.md
    description: >
      One check row added, and nothing else. "## 8"'s "adds no fifth" clause and "## 2"'s
      template-is-the-authority clause are the reason this remedy is lawful WITHOUT amending "## 8";
      both are untouched, and the report must say so.
    targets:
      - type: section
        name: (i) The per-finding decision record and the report contract
    semantic_anchors:
      insert_after:
        type: table_row
        value: '| The field exists in the format | Does the report format have a slot for the decision, between the finding heading and the field table? | The format''s own finding block; the slot is present. |'

changes:

  # ─────────────────────── THE AUTHORITY — four edits ───────────────────────

  - action: add_code
    target: .ai/audit/templates/audit-findings.md — the skeleton field table
    description: >
      Add the Verification row to the finding block's field table. It goes LAST, after Classification:
      the existing rows keep their order, and Verification is not placed between Severity and Type,
      where a reader could take it for a severity qualifier rather than the independent evidence-status
      field it is.
    code_hint: |
      | **Classification** | {mandatory\|advisory} |
      | **Verification** | {verification} |

  - action: modify
    target: .ai/audit/templates/audit-findings.md — the `severity` row of the Mandatory Fields table
    description: >
      Replace the current row —

        | `severity` | enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |

      — with the row below. D10 ITEM 4 IS BINDING ON THE WORDING, AND IT IS THE ONE GENUINE RISK OF
      THIS REMEDY: the row must NOT be written as "an unexecuted finding is LOW". That would turn a
      composition rule into a ranking rule, would reinterpret phase 04's own LOW row, and would make LOW
      mean two things. The row must say the band is composed from the structural fact under the owning
      phase's own severity table, and must CITE phase 04's own LOW row as the precedent rather than
      assert a mapping. The prospective clause is the last sentence.
    code_hint: |
      | `severity` | enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. **When the runtime consequence of a finding was not observed, the band is composed from the structural fact under the owning phase's own severity table.** It is never a severity the run observed, and this row prescribes no band of its own: the owning phase's table decides. That table already carries a band a structural fact alone satisfies — for example phase `04`'s own `LOW` row, *"A shape, naming or structure deviation with no runtime consequence."* **The rule is prospective: a severity already written is not re-read under it.** |

  - action: add_code
    target: .ai/audit/templates/audit-findings.md — the Mandatory Fields Per Finding table
    description: >
      Add the `verification` row immediately AFTER the `severity` row it qualifies, so the authority
      states the two together and in that order. The field is MANDATORY ON EVERY FINDING, not only on
      the ones that need it — a field written only when it has something to say cannot be checked for
      absence.
    code_hint: |
      | `verification` | enum | `observed` · `unverified` — **required on every finding.** `observed` when the runtime consequence was executed and seen; `unverified` when it was not. A finding filed `unverified` carries the structural fact, and its `severity` band is composed from that fact under the owning phase's own severity table. This field is the machine-checkable carrier of the `UNVERIFIED` marker; the marker prose is its human-readable form. |

  - action: add_code
    target: .ai/audit/templates/audit-findings.md — the `## Classification Guide`
    description: >
      Add a third bullet beside the existing `mandatory` and `advisory` bullets, matching their shape
      (a bolded field name, a colon, one sentence of definition, then the consequence). The guide is
      where a reader looks to learn what a field means, and a field defined only in a table row is
      half-adopted.
    code_hint: |
      - **verification**: `observed` — the runtime consequence was executed and seen. `unverified` — it was not, and no band is asserted for a consequence nobody watched. A finding filed `unverified` is still assigned a severity: the band is composed from the structural fact under the owning phase's own severity table, which is what "composed from the structural fact" means and what this report format does not decide. What records that the consequence was not observed is the field, never the absence of a band.

  # ─────────────────────── PHASE 04 — four amendments, four sites ───────────────────────
  #
  # Phase 04 is the only handbook of the twelve that forbids "severity" rather than "an observed
  # severity". It has EXACTLY FOUR such sites; all four are amended; no fifth exists. The two files'
  # other UNVERIFIED sentences — phase 04's "## 9" closing paragraph and its "## 12" bullet — already
  # read "never with an observed severity" and are ALREADY in the satisfied form. They are NOT edited.

  - action: modify
    id: P1
    target: .kilo/commands/audit/phases/04-... — the preamble bullet "The subject is exactly two findings, never one and never zero."
    description: >
      Replace ONLY the trailing clause "…, and **no severity**." with the composition rule. Everything
      else in the bullet is preserved verbatim, including "The subject is exactly two findings, never
      one and never zero", the "carrying the structural fact, the literal marker **`UNVERIFIED`**"
      wording, and the "is not asserted as fact anywhere in this file, and may not be" clause.
    code_hint: |
      - **The subject is exactly two findings, never one and never zero.** The
      >   reproduced shape is the first, its severity composed from the run's own R1, R4
      >   and R5 evidence. The **production trigger** — the shipped condition that
      >   reaches the inner claim from inside the outer one — is the second, carrying
      >   the structural fact, the literal marker **`UNVERIFIED`**, and a severity band
      >   composed from that structural fact under **this phase's own `## 9` table** —
      >   the rule the report template states, and the table this phase's own `LOW` row
      >   already applies. It is not executed by design, is not asserted as fact
      >   anywhere in this file, and may not be.

  - action: modify
    id: P2
    target: .kilo/commands/audit/phases/04-... — the preamble bullet headed "No structure-only severity."
    description: >
      THE ROOT CAUSE. This bullet forbids exactly what this phase's own "## 9" LOW row defines — "A
      shape, naming or structure deviation with no runtime consequence" IS a shape deviation with no
      observed runtime output. The bullet names the wrong prohibition: what is inadmissible is a band
      the run did not support, not a band read off an observed structural fact under the phase's own
      table. Rename the bullet to name the real prohibition and keep BOTH of its other prohibitions
      (collapsing the subject into a single finding; collapsing it into none) intact and verbatim. This
      is the amendment a reviewer must read first: without it, P1 and P8 contradict it.
    code_hint: |
      > - **No severity the run did not observe.** A severity assigned from the code's
      >   shape with no `R1`–`Rn` output behind it is inadmissible — read as *a band no
      >   observed output supports*, not as *a band read off an observed structural fact*.
      >   Where the run recorded the structural fact and did not record its consequence,
      >   the band is composed from that fact under **`## 9`**, whose own `LOW` row — *"A
      >   shape, naming or structure deviation with no runtime consequence"* — is exactly
      >   such a band. So is collapsing this subject into a single finding, and so is
      >   collapsing it into none.

  - action: modify
    id: P3
    target: .kilo/commands/audit/phases/04-... — the "## 3" documented-skips bullet for the production condition
    description: >
      Replace ONLY the trailing clause "— not as a skip, and never with a severity." The rest of the
      bullet — the italics title, "R2 establishes that the **path** is reachable with the media method
      replaced", and "is not executed by design" — is preserved verbatim.
    code_hint: |
        - *The production condition that reaches the per-part transfer from inside the outer claim.* R2 establishes that the **path** is reachable with the media method replaced. The condition itself is not executed by design and is carried as a finding marked `UNVERIFIED` — not as a skip, and never with a severity the run did not observe. Its band is composed from the structural fact under `## 9`.

  - action: modify
    id: P8
    target: .kilo/commands/audit/phases/04-... — the "## 12" `problems-only` bullet that begins "W-4, and this bullet is binding on the report"
    description: >
      Replace the TWO "no severity" clauses inside W-4 with the composition rule, and change nothing
      else in the bullet. VERBATIM-PRESERVED, CHARACTER FOR CHARACTER: "the claim subject is filed as
      **exactly two** findings"; "The two are never merged and never omitted; under `problems-only`,
      omitting either reads as "no finding"."; the reproduced-shape sentence with its CRITICAL-only-
      when-all-three-legs-are-observed ceiling and its "with the leg that did not execute named"; and
      the closing "Do not cite any document's characterisation of the subject as a severity."
      The RETENTION RULE — a rejected finding is never deleted, its claim and its reason stay in the
      artifact — is PRESERVED BY NOT BEING TOUCHED. It lives in 99-audit-validate.md's `## 5` block
      (f) rows "Retained content" and "Re-derivation guard" and in `## 11`'s Rejected row; this block
      edits NEITHER, and adding a retention clause here would restate a rule in a second document for
      no gain (rule 5).
    code_hint: |
        - **W-4, and this bullet is binding on the report:** the claim subject is filed as **exactly two** findings. The **reproduced shape** carries an observed severity composed from the run's own R1, R4 and R5 evidence — `CRITICAL` only when all three legs are **observed**, otherwise capped at `HIGH` with the leg that did not execute named. A leg that was not executed is `UNVERIFIED`, and its band is composed from the structural fact under `## 9`. The **production trigger** carries `UNVERIFIED` and a band composed from its structural fact under `## 9`. The two are never merged and never omitted; under `problems-only`, omitting either reads as "no finding". Do not cite any document's characterisation of the subject as a severity.

  # ─────────────────────── 99-audit-validate.md — one check row ───────────────────────

  - action: add_code
    id: V4
    target: .kilo/commands/audit/phases/99-audit-validate.md — block (i)'s check table, immediately after the row "The field exists in the format"
    description: >
      The report contract's own check gains one row. It sits beside "The field exists in the format"
      because that is the row which asks whether the format has room for the field at all, and the
      format now has room for this one. The evidence column states what makes the row decidable
      instead of assertion-shaped, matching every other row in the table.
    code_hint: |
      | Verification recorded | Does a finding whose runtime consequence was not executed carry the format's `verification` field, and is its severity band composed from the structural fact under the owning phase's severity table rather than asserted? | The field's value; the structural fact recorded; the owning phase's severity-table row the band was composed under. **A band no observed output supports is the finding**, and a missing field on a finding whose consequence was not executed is the finding. |

  - action: prohibited
    target: .kilo/commands/audit/phases/99-audit-validate.md — everything else
    description: >
      `## 8`'s "The four severity words are not redefined here, and this file adds no fifth" stays true
      and is NOT TOUCHED — no fifth member is added, so it does not become false. `## 2`'s clause "The
      definition of the severity, type and classification vocabularies → the report template, which
      this phase treats as the authority and adjudicates against" is what makes this remedy lawful
      without amending `## 8` at all, and is NOT TOUCHED. `## 6`'s closing paragraph ("Each subject
      above is a subject to verify, not a finding…") contains the phrase "no severity, count or verdict
      is recorded beside any of the eight" — that is the do-not-pre-score rule, NOT a UNVERIFIED rule,
      and it is NOT TOUCHED; a grep for "no severity" will match it and it is a false positive.
      `## 11`'s `## Validation Summary` ACTION table (Validated / Reclassified / Merged / Rejected /
      VAL-) is NOT A SEVERITY SURFACE — it is an action tally — and is NOT TOUCHED. D10 ITEM 7 RECORDS
      THAT PLAN 09 §3 B11's reach list naming it WAS A DEFECT IN THAT PLAN; this block corrects it.
      `## 5` block (f)'s retention rows and `## 11`'s Rejected row are NOT TOUCHED.

  - action: prohibited
    target: the whole repository outside the three files above
    description: >
      The ELEVEN SIBLING PHASE HANDBOOKS (01-audit-entry-architecture, 02-audit-config,
      03-audit-network-resilience, 05-audit-subprocess-browser, 06-audit-credentials-secrets,
      07-audit-filesystem-artifacts, 08-audit-cli-observability, 09-audit-code-quality,
      10-audit-test-coverage, 11-audit-supply-chain, and — as the twelfth handbook — 99-audit-validate.md's
      already-touched `## 5`) are NOT touched, and the report must list each with this reason: THEIR
      MANDATE IS ALREADY IN THE SATISFIED FORM. Each already forbids "an OBSERVED severity" and nothing
      more, which is precisely what this remedy satisfies; they need no semantic change and no
      reconciliation, and remedy (c) removes the sibling updates that were the plan's largest process
      risk. `audit-multi-phase.md`'s four counters and closing "By severity" output are NOT touched —
      no fifth member exists for them to count. `.kilo/agents/auditor.md` and `validator.md` are NOT
      touched: NO FIFTH `type` LABEL IS ADDED, so D4's condition is not met and plan 08's prohibition
      stands absolutely; their type lists already match the authority's four members.
      `.kilo/commands/audit/tests/*.md` are NOT touched — a separate, non-conforming vocabulary family
      (recorded, not filed; plan 09 §11 E7). `.kilo/rules/project.md` and `.kilo/rules/*` are NEVER in
      scope for any block; if either remedy required it the block would stop and escalate.
      `.ai/templates/audit-findings.md` is NOT touched (D3), and the report must record that it already
      carries an UNADOPTED evidence-status field — a `Checked: ran | static | not-checked` field that is
      present in HTML comments and so has never been adopted — which is why this block adds the
      `verification` field to the AUTHORITY rather than adopting the shadow's.
      `.ai/audit/04-concurrency-cancellation/findings.md` and
      `.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` are READ-ONLY; the
      out-of-enum cell is the EVIDENCE for this finding and editing it would destroy the instance and
      retro-fit the format to the answer. NO existing finding's severity or type is rewritten ANYWHERE.
      CON-002's `*none — not executed*` cell REMAINS PERMANENTLY — an accepted, recorded state, not a
      residual defect. tmp/ is never committed; every load-bearing fact is carried inline in the report.

acceptance_criteria:

  # ── the encoding ──
  - The authoritative template states the composition rule on its `severity` row: the band is composed
    from the structural fact under the owning phase's own severity table, and NO fixed band is asserted.
    The row does NOT contain any wording equivalent to "an unexecuted finding is LOW".
  - The `severity` row CITES phase 04's own `LOW` row as the precedent, and quotes its wording
    ("A shape, naming or structure deviation with no runtime consequence").
  - The `severity` row carries the PROSPECTIVE clause: a severity already written is not re-read under
    the rule.
  - The template carries a `verification` row in the Template Field Reference table and a
    `| **Verification** | {verification} |` row in the SKELETON FIELD TABLE. Both exist.
  - The `verification` field is stated as required on EVERY finding, with the values `observed` and
    `unverified`.
  - The `## Classification Guide` carries the third bullet defining `verification`.
  - The template's `## Summary` four-row severity-count table is UNCHANGED — no fifth member exists,
    and the corpus proves a fifth Summary row can be written ad hoc when a report needs one (phase 04's
    own report already carries `| none (UNVERIFIED, not executed) | 1 |`).

  # ── the reconciliation ──
  - Phase 04 has NO remaining statement that forbids a severity outright. Verified by grep for "no
    severity", "never with a severity" and "No structure-only severity" over the file: the only hits
    left are the `## 9` and `## 12` sentences that forbid "an OBSERVED severity", which are correct and
    untouched.
  - All four of phase 04's former "no severity" sites are amended: the preamble's two-findings bullet,
    the preamble's "No structure-only severity" bullet, the `## 3` documented-skips bullet, and W-4 in
    `## 12`. No fifth site exists and none was invented.
  - P2's bullet no longer forbids what the phase's own `## 9` `LOW` row defines, and retains BOTH of its
    other prohibitions verbatim (single finding; no finding).
  - W-4's clauses "the claim subject is filed as **exactly two** findings" and "The two are never merged
    and never omitted; under `problems-only`, omitting either reads as "no finding"." are byte-identical
    to their current text.
  - The retention rule is intact: 99-audit-validate.md's `## 5` block (f) rows "Retained content" and
    "Re-derivation guard", and its `## 11` Rejected row's "**Never delete it**", are all untouched.
  - 99-audit-validate.md block (i) carries the new `Verification recorded` check row, and NOTHING ELSE in
    that file changed except that row.
  - The report states that `## 8`'s "adds no fifth" clause and `## 2`'s template-is-the-authority clause
    are UNTOUCHED and why the prohibition survives — `## 2` routes the vocabulary definition to the
    template, so adding the field to the template is amending the authority and not the validator.
  - The report states the D10 ITEM 1 RE-CHARACTERISATION EXPLICITLY: VAL-404 is filed SPEC-DEVIATION
    against the template, the defect is mostly in phase 04's handbook, and the template is NOT abandoned
    — it gains the field and the composition rule. Without this sentence a reviewer reads the edit set
    as narrower than the finding.
  - The report records the D10 ITEM 3 JUDGEMENT: the three optional clarity edits were considered and NOT
    taken, and the reason.

  # ── the boundaries, all three files, provable ──
  - `git diff --exit-code HEAD -- .ai/audit/templates/audit-findings.md
    .kilo/commands/audit/phases/04-audit-concurrency-cancellation.md
    .kilo/commands/audit/phases/99-audit-validate.md` reports changes in EXACTLY those three paths and
    in no other file anywhere in the repository.
  - `git diff --exit-code HEAD -- .kilo/rules .kilo/agents .ai/templates` is EMPTY.
  - `git diff --exit-code HEAD -- .ai/audit` names ONLY `.ai/audit/templates/audit-findings.md`. The
    pre-existing tracked deletion of `.ai/audit/03-network-resilience/findings.md` is not this block's
    and must not be staged.
  - The eleven sibling handbooks, `audit-multi-phase.md`, `.kilo/agents/*` and
    `.ai/templates/audit-findings.md` are each listed in the report as untouched, each with its reason.

  # ── the read-only gate (D2 — TWO commands, both must pass) ──
  - `git diff --exit-code HEAD -- .ai/audit/04-concurrency-cancellation/findings.md
    .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` exits 0.
  - `git ls-files --error-unmatch -- .ai/audit/04-concurrency-cancellation/findings.md
    .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` exits 0. A green diff with
    a red ls-files is a FAILURE, not a pass.
  - CON-002 is not deleted, not merged, not reclassified, and its `*none — not executed*` cell is
    byte-identical before and after.

  # ── the oracle — three assertions, run and re-run verbatim ──
  - Assertion (a): all 14 files that restate an enum declare member sets IDENTICAL to the template's
    field reference. Zero invented members, zero partial sets.
  - Assertion (b): every finding block containing `UNVERIFIED` is classified `prospective-conforming` or
    `pre-existing-unchanged`, with ZERO unclassified; and the out-of-enum severity-cell count does not
    increase from exactly 1.
  - Assertion (c): `git diff --exit-code HEAD -- .kilo/rules .kilo/agents .ai/templates` is EMPTY.
  - The report carries the three assertions' verbatim output.
  - No test can see this change and none is written: `tests/test_packaging.py` names `.ai/` and `.kilo/`
    only as `FORBIDDEN_SDIST_PREFIXES` — trees that must never ship — which is a packaging exclusion and
    cannot observe the content of either. There is no CI check over `.kilo/**` or `.ai/**`. The oracle
    IS the gate, and the Validator's independent read is the second half.

extra_context: |

      MEASURED BASELINE (Planner, at HEAD = 8611a31, re-measured not inherited)

      The tree has moved FOUR times since this plan was composed. 514a210 is B8 and 8611a31 is B9; both
      landed. Neither touched .ai/audit/templates/audit-findings.md,
      .kilo/commands/audit/phases/04-audit-concurrency-cancellation.md or
      .kilo/commands/audit/phases/99-audit-validate.md — all three were verified clean against HEAD before
      this specification was written, so every anchor below is confirmed present.

      THE EVIDENCE THE REMEDY RESTS ON (all re-verified)

      1. Eleven of the twelve handbooks forbid only "an OBSERVED severity". Only phase 04 forbids "severity"
         at all, at exactly FOUR sites: the preamble's two-findings bullet ("and **no severity**"), the
         preamble's "No structure-only severity" bullet, the "## 3" documented-skips bullet ("never with a
         severity"), and W-4 in "## 12" ("no severity is written for it" and "carries `UNVERIFIED` and **no
         severity**"). Phase 04's "## 9" and "## 12" UNVERIFIED sentences already read "never with an
         observed severity" and need nothing.
      2. Phase 04's own "## 9" LOW row reads, verbatim: "A shape, naming or structure deviation with no
         runtime consequence, including a branch that cannot be reached and a value computed and never
         used." That is the band `CON-002` needs, stated by the phase itself. P2 forbids it.
      3. 99-audit-validate.md "## 2" carries: "The definition of the severity, type and classification
         vocabularies -> the report template, which this phase treats as the authority and adjudicates
         against." "## 8" opens "The findings template is the authority." and closes the taxonomy with "The
         four severity words are not redefined here, and this file adds no fifth."
      4. 14 files restate an enum: the twelve phase handbooks, .kilo/agents/auditor.md (both enums) and
         .kilo/agents/validator.md (the TYPE enum only — it contains no severity word at all). Measured:
         every set any file states is exactly the authority's set.
      5. The corpus already answers the question. 76 finding blocks contain `UNVERIFIED`; 75 carry a
         severity whose band is an enum member and 1 does not. Phase 08's OUT-010, OUT-011 and OUT-012 are
         each "| **Severity** | LOW |" with an `UNVERIFIED` marker, and the validator wrote, verbatim:
         "Severity: LOW, `UNVERIFIED` through the binary, correctly marked."
      6. 266 `| **Severity** |` cells exist across the 21 finding reports under .ai/audit (a 267th is the
         template's own `{severity}` placeholder, which is not a finding). Exactly ONE is out-of-enum:
         CON-002's `*none — not executed*` in the SOURCE report. The validated artifact's CON-002 carries no
         field table at all and no severity row. The other 18 non-bare cells are a legal enum word plus a
         parenthetical or a re-derivation note — the audit's "~18 out-of-enum" is really "18 free-text".
      7. Phase 04's own report `## Summary` already carries the fifth row
         "| none (`UNVERIFIED`, not executed) | 1 |", and it sums to the finding count. The four-row
         `## Summary` table in the template therefore needs no change under a no-enum-change remedy, and
         phase 04's report is the proof.

      TWO COUNTS IN D10 ITEM 9 DO NOT REPRODUCE — recorded so nothing downstream cites them

      D10 item 9's 58 and 110 reproduce exactly: 58 `UNVERIFIED`-bearing lines across the 12 phase
      handbooks under .kilo/commands/audit/phases (case-sensitive, worktree directories excluded), and 110
      across .ai/audit/**. Its 141 for .ai/** and its 205 total DO NOT: .ai/** measures 147 lines
      (case-insensitive) today, and the figure is structurally unstable because .ai/plans/** — plan 09
      itself included — carries the token and grows as this plan is written. The qualitative claim — all
      twelve handbooks, a corpus-wide convention — HOLDS. NO ACCEPTANCE CRITERION AND NO ORACLE ASSERTION
      IN THIS TASK DEPENDS ON 141 OR 205.

      THE TWO ORACLE SCOPE TRAPS, ALREADY APPLIED IN THE COMMANDS BELOW

      Trap 1: a recursive sweep of .kilo/commands/audit INCLUDES .kilo/commands/audit/tests/*.md — four
      files (audit-bad-tests.md, audit-test-performance.md, audit-tests-failures.md, audit-tests-full.md)
      which are NOT phase handbooks and are NOT governed by 99-audit-validate.md. audit-bad-tests.md lists
      only two of the four type labels and audit-tests-full.md carries its own HIGH/MEDIUM/LOW column. An
      oracle that sweeps the directory recursively pushes the Implementor into over-reach. The commands
      below enumerate the phase handbooks non-recursively instead.
      Trap 2: a severity-word grep across .kilo/agents produces false positives that have nothing to do with
      severities — researcher.md carries "honest confidence levels (HIGH/MEDIUM/LOW)" and "marked LOW
      confidence"; planner.md and validator.md carry "low coupling" and "high reliability"; auditor.md
      carries "blind spec compliance without critical thinking" and an effort scale reading
      "trivial / small / medium / large". The commands below avoid the trap structurally: they match the
      enum members case-sensitively with letter/hyphen boundaries, which excludes every one of those, and
      they permit a file to state ONE of the two enums (validator.md states only the type enum) while
      forbidding any file from stating a PARTIAL set.

      NO TEST CAN BE WRITTEN FOR THIS BLOCK

      Verified: tests/ and .github/ contain no reference to .kilo/ or .ai/** content. The single reference is
      tests/test_packaging.py, where ".ai/" and ".kilo/" appear only inside FORBIDDEN_SDIST_PREFIXES — trees
      that must never ship in the sdist. That is a packaging exclusion and cannot observe whether
      Verification was added. pyproject.toml's ruff extend-exclude names ".ai/builders" and is likewise not a
      content check. The oracle below IS the gate, and it is an assertion that passes or fails — never an
      enumeration.

      THE EXECUTABLE ORACLE — three assertions, PowerShell, run from the repository root.
      The Implementor runs these and pastes the verbatim output; the Validator re-runs them VERBATIM.

      (a) ENUM MEMBER-SET IDENTITY across all 14 restating files.

      ```powershell
      $sev = @('CRITICAL','HIGH','MEDIUM','LOW'); $typ = @('SPEC-DEVIATION','BEST-PRACTICE','DOC-UPDATE','RUNTIME-ERROR')
      function Get-Members([string]$text, [string[]]$words) { @($words | Where-Object { $text -cmatch "(?<![A-Za-z-])$([regex]::Escape($_))(?![A-Za-z-])" }) }
      $tpl = [IO.File]::ReadAllText('.ai\audit\templates\audit-findings.md')
      $tplSev = Get-Members $tpl $sev; $tplTyp = Get-Members $tpl $typ
      "AUTHORITY .ai\audit\templates\audit-findings.md"
      "  severity members = $($tplSev -join ' | ')"; "  type members = $($tplTyp -join ' | ')"
      if ($tplSev.Count -ne 4 -or $tplTyp.Count -ne 4) { 'ASSERTION (a) FAILED: authority does not declare four members per enum.'; exit 1 }
      $targets = @(); $targets += (Get-ChildItem -File -Filter *.md .kilo\commands\audit\phases).FullName
      $targets += @('.kilo\agents\auditor.md','.kilo\agents\validator.md')
      ""; "RESTATING FILES  count = $($targets.Count)"
      $bad = 0
      foreach ($f in $targets) {
      $txt = [IO.File]::ReadAllText($f); $s = Get-Members $txt $sev; $t = Get-Members $txt $typ
      $sBad = ($s.Count -ne 0 -and (@(Compare-Object $s $tplSev -CaseSensitive).Count -ne 0))
      $tBad = ($t.Count -ne 0 -and (@(Compare-Object $t $tplTyp -CaseSensitive).Count -ne 0))
      if ($sBad -or $tBad) { $state='MISMATCH'; $bad++ } else { $state='ok' }
      "  {0,-8} {1,-40} sev=[{2}] typ=[{3}]" -f $state, (Split-Path $f -Leaf), ($s -join ','), ($t -join ',')
      }
      ""
      if ($targets.Count -ne 14) { "ASSERTION (a) FAILED: expected 14 restating files, found $($targets.Count)."; exit 1 }
      if ($bad -ne 0) { "ASSERTION (a) FAILED: $bad file(s) differ from the authority."; exit 1 }
      "ASSERTION (a) PASS: 14/14 files declare member sets identical to the authority."
      ```

      ```powershell
      (b) EVERY UNVERIFIED-CARRYING BLOCK CLASSIFIED, AND THE OUT-OF-ENUM CELL COUNT UNCHANGED.
      $members = @('CRITICAL','HIGH','MEDIUM','LOW')
      $legacy  = '*none ' + [char]0x2014 + ' not executed*'
      $reports = @(Get-ChildItem -Recurse -File -Filter *.md .ai\audit |
                Where-Object { $_.Name -eq 'findings.md' -or $_.Name -like '*-validated-findings.md' })
      "finding reports in scope = $($reports.Count)"
      $cells = @(); $blocks = @()
      foreach ($f in $reports) {
      $lines = [IO.File]::ReadAllLines($f.FullName); $heads = @()
      for ($i=0; $i -lt $lines.Length; $i++) { if ($lines[$i] -match '^#{1,6}\s+\S') { $heads += $i } }
      $heads += $lines.Length
      for ($h=0; $h -lt $heads.Count-1; $h++) {
        $start=$heads[$h]; $end=$heads[$h+1]-1; $cell=$null
        for ($j=$start; $j -le $end; $j++) { if ($lines[$j] -match '^\|\s*\*\*Severity\*\*\s*\|\s*(.+?)\s*\|\s*$') { $cell=$Matches[1]; break } }
        if ($null -ne $cell) { $cells += $cell }
        if ((($lines[$start..$end] -join "`n").Contains('UNVERIFIED'))) {
          $cls = if ($null -eq $cell) { 'prospective-conforming' }
                 elseif ($cell -ceq $legacy) { 'pre-existing-unchanged' }
                 elseif ($members | Where-Object { $cell -cmatch "^(\*\*)?$([regex]::Escape($_))(\*\*)?\b" }) { 'prospective-conforming' }
                 else { 'UNCLASSIFIED' }
          $blocks += [pscustomobject]@{ Head=$lines[$start].Trim(); File=$f.Name; Cell=$cell; Cls=$cls }
        }
      }
      }
      ""
      "severity cells in finding reports = $($cells.Count)"
      "out-of-enum cells               = " + (@($cells | Where-Object { $c=$_; -not ($members | Where-Object { $c -cmatch "^(\*\*)?$([regex]::Escape($_))(\*\*)?\b" }) }).Count)
      $blocks | Group-Object Cls | ForEach-Object { "  {0,-24} x{1}" -f $_.Name, $_.Count }
      $blocks | Where-Object { $_.Cls -eq 'pre-existing-unchanged' } | ForEach-Object { "  PRE-EXISTING: {0} <- {1} cell={2}" -f $_.Head, $_.File, $_.Cell }
      ""
      $unclassified = @($blocks | Where-Object { $_.Cls -eq 'UNCLASSIFIED' }).Count
      $outOfEnum    = @($cells | Where-Object { $c=$_; -not ($members | Where-Object { $c -cmatch "^(\*\*)?$([regex]::Escape($_))(\*\*)?\b" }) }).Count
      if ($unclassified -ne 0) { "ASSERTION (b) FAILED: $unclassified UNVERIFIED block(s) unclassified."; exit 1 }
      if ($outOfEnum -ne 1)    { "ASSERTION (b) FAILED: out-of-enum severity cells = $outOfEnum, expected exactly 1."; exit 1 }
      "ASSERTION (b) PASS: zero unclassified; out-of-enum severity-cell count unchanged at exactly 1."
      ```

      ```powershell
      (c) BOUNDARY GREPS — the three trees that must be untouched.
      "--- .kilo/rules ---"
      git diff --exit-code HEAD -- .kilo/rules
      "    EXIT=$LASTEXITCODE (0 = untouched)"
      "--- .kilo/agents (auditor.md, validator.md and every other role file) ---"
      git diff --exit-code HEAD -- .kilo/agents
      "    EXIT=$LASTEXITCODE (0 = untouched)"
      "--- .ai/templates (the unreferenced shadow, D3) ---"
      git diff --exit-code HEAD -- .ai/templates
      "    EXIT=$LASTEXITCODE (0 = untouched)"
      "--- the two read-only audit artifacts (D2 gate, both commands required) ---"
      git diff --exit-code HEAD -- .ai/audit/04-concurrency-cancellation/findings.md .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
      "    EXIT=$LASTEXITCODE (0 = byte-identical)"
      git ls-files --error-unmatch -- .ai/audit/04-concurrency-cancellation/findings.md .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
      "    EXIT=$LASTEXITCODE (0 = still tracked; a green diff with a red ls-files is a FAILURE)"
      "--- .ai/audit as a whole: only the template may differ ---"
      git diff --name-status HEAD -- .ai/audit
      "    every path listed must be exactly: M .ai/audit/templates/audit-findings.md"
      ```

      EXPECTED (a) AND (b) OUTPUT AT HEAD = 8611a31, VERIFIED BY THIS PLANNER

      (a) AUTHORITY severity = CRITICAL | HIGH | MEDIUM | LOW; type = SPEC-DEVIATION | BEST-PRACTICE |
          DOC-UPDATE | RUNTIME-ERROR. RESTATING FILES count = 14. All 14 ok. validator.md is the only
          file with an EMPTY severity set, because it states only the type enum. PASS.
      (b) finding reports in scope = 21. severity cells = 266. out-of-enum cells = 1
          (`*none — not executed*`, CON-002 in the source report). prospective-conforming x75,
          pre-existing-unchanged x1. PASS.
      (c) all three diffs EMPTY (EXIT=0); the read-only artifacts byte-identical and still tracked;
          .ai/audit lists only the template as modified.

      IF AN ASSERTION FAILS, STOP. Do not amend the corpus to make it pass. Report the failure verbatim.

      D10 ITEM 3 — THE OPTIONAL CLARITY EDITS: DECIDED NOT TAKEN

      Considered and REJECTED: phase 04's "## 9" closing paragraph, phase 04's "## 12" UNVERIFIED bullet, and
      99-audit-validate.md "## 8"'s closing paragraph. All three already read "never with an observed
      severity" — the satisfied form — and the remedy adds no word they need. The composition rule is
      carried once, by the declared authority; "## 2" and "## 6" in the validator and "## 9"'s opening
      sentence in phase 04 already route the vocabulary to the template, so each sibling is disambiguated by
      DERIVATION rather than by repetition. Phase 04's "## 9" closing paragraph already defers composition to
      the preamble's binding rule 3, and P1/P2/P8 amend exactly that preamble — so it is corrected
      transitively, with no edit of its own. RESIDUAL AMBIGUITY IS NOT MATERIAL: after P1/P2/P3/P8, no
      statement in any of the three files forbids a severity outright, and phase 04's two remaining
      "observed severity" sentences are correct. Taking the three edits would restate one authority row
      into three files for no gain — documentation noise, and rule 5.

      D10 ITEM 4 — THE WORDING HAZARD, RESTATED AS A PRE-COMMIT REVIEW GATE

      Before committing, re-read the rewritten `severity` row and confirm all four: (i) it says the band is
      composed from the structural fact under the owning phase's own severity table; (ii) it asserts NO
      fixed band, and in particular never says an unexecuted finding is LOW; (iii) it cites phase 04's own
      LOW row as a precedent rather than as a mapping; (iv) it carries the prospective clause.

      IDENTIFIER CONVENTION, BINDING ON THIS BLOCK

      Every phase-04 `VAL-` id is written `phase04/VAL-NNN`. The finding this block carries is
      `phase04/VAL-404`. An unqualified `VAL-4xx` in the report or the commit message is a defect.

      COMMIT

      ONE commit, staged by explicit semantic path — never `git add -A`, never `git add .`, never
      `git commit -a`. `git diff --cached --stat` must show exactly the three files above. The tree's
      pre-existing dirty entries (the tracked .ai/plans deletions, the modified .ai/problems/PROBLEM.md, the
      tracked deletion of .ai/audit/03-network-resilience/findings.md, the untracked plan files and tmp/) are
      NOT staged. The commit message cites `phase04/VAL-404`, states that the template gains the
      `Verification` field and the composition rule, states that phase 04's four "no severity" prohibitions
      are reconciled to it, and states that the change is prospective and that CON-002's
      `*none — not executed*` cell is untouched and permanently out-of-enum.
```

### B10

```yaml
id: plan09-b10-con002-verification-record
title: Record CON-002's verification outcome without code change, severity, or deletion
priority: medium
depends_on: ["B8", "B9", "B11"]

source_reference: .ai/plans/09-concurrency-cancellation-audit-fixes-completion.md
predecessor_reference: .ai/plans/08-concurrency-cancellation-audit-fixes.md
source_section: B10 — Record CON-002's verification outcome without touching code or severity
source_blocks: ["B10"]
source_findings: ["CON-002", "phase04/VAL-410"]

phase: plan-09-concurrency-cancellation-audit-fixes-completion
block_id: B10
audit_tier: Tier 1 — pipeline-critical or user-data-critical
finding_id: CON-002

description: >
  CON-002's severity cell reads `*none — not executed*`, which is outside the format's enum and which
  this validation phase may not correct: the only admissible substitute is LOW, which IS an observed
  severity and which 99-audit-validate.md "## 8" forbids. The finding may also not be deleted — the
  owning phase's binding rule W-4 requires the claim subject to be filed as exactly two findings and
  states that omitting either reads as "no finding". The structural fact is true and re-derivable:
  perform_download takes the per-video permit exactly once around the whole ladder, the segment layer
  builds its own semaphore, and the outer object crosses the boundary only as the boolean
  is_bounded_batch — so the registered D-01 nested-claim shape does not reproduce. But the PRODUCTION
  CONDITION was never executed, and the primitive-identity comparison is NOT proof of the condition's
  behaviour. Establish and record what is and is not known. NO CODE CHANGE.
  This block is LAST because its content is a record of FINAL state: it must describe the concurrency
  picture B8 produced and cite B11's landed encoding. All three dependencies are RECORD-ACCURACY
  dependencies, not code dependencies. B8 (514a210) made max_concurrent_downloads a THIRD bound;
  B9 (8611a31) is in the dependency set because it is the last commit to touch the same
  max_concurrent_downloads field description this record reads; B11 (3c25dda) landed the encoding
  this finding's state now rests on. Edge C2 and edge C3 are DISCHARGED at this block's tree state:
  the record describes post-B8 reality, and the record file itself is authored here.
  THIS IS THE ONLY BLOCK IN PLAN 09 THAT CREATES A NEW FILE. Every other block edits existing files.

goals:
  - a durable, auditable record of what is known and what is not
  - CON-002 remains filed, remains UNVERIFIED, and carries no severity
  - no product code changes at all
  - the outstanding phase04/VAL-410 corrections are recorded as not claimed, with their owner

files:
  # THE DELIVERABLE. Exactly one new file. Read by this block; created by it.
  # Edge C3, filename justification — five constraints, each verified at this tree state:
  #   1. It sits under .ai/audit/99-validation/ beside the eleven validation artifacts it qualifies,
  #      and all ELEVEN of those end in -validated-findings.md. Verified: Get-ChildItem over that
  #      directory returns exactly 11 files and every one wears that suffix, so a file that does not
  #      wear it cannot be collected by any reader, glob or tool that keys on the suffix.
  #   2. It carries the 04- phase token, so it sorts beside the phase-04 artifact and inherits the
  #      phase identity every sibling in that directory uses. A record with no phase token would be
  #      ambiguous in a directory shared by twelve phases.
  #   3. It carries the FINDING id CON-002, so it cannot be read as a phase-level status file. There
  #      is no registry, index or status file anywhere in .ai/ (verified: .ai/ holds only context/,
  #      models/, plans/, problems/, research/, structure/map.md and templates/ — none of which
  #      indexes findings), so a phase-named record with no finding id would invite the next reader to
  #      treat it as the phase's verification summary. It is not one.
  #   4. "verification-record" states the artefact's KIND in the pipeline's own vocabulary —
  #      Verification is the field B11 landed, R-Validate and R-E are the checkpoint names. It claims
  #      to be neither a finding, nor an artifact, nor a decision.
  #   5. It is not findings.md, not a template, not a summary. One file. One.
  # Rejected alternatives: "04-concurrency-cancellation-verification-notes.md" (no finding id — reads
  # as the phase's overall verification status, which it is not); "CON-002-verification-record.md"
  # without the phase prefix (ambiguous in a twelve-phase directory).
  - path: .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md
    read_only: false
    is_new: true
    targets:
      - type: module
        name: whole file
    semantic_anchors:
      - "## What this record is, and what it is not"
      - "## 1. The structural fact, re-derived against the live code"
      - "## 2. What was NOT executed, and why"
      - "## 3. A structural identity comparison is not proof"
      - "## 4. The register's remedy was implemented; the live-batch half of the recommendation is still outstanding"
      - "## 5. The register's Location list is stale, and `phase04/VAL-410` is deferred"
      - "## 6. This finding's state, and the encoding that now exists for it"
      - "## 7. Standing statement"

  # READ-ONLY. Re-derived for the record, never edited.
  - path: .ai/audit/04-concurrency-cancellation/findings.md
    read_only: true
    targets:
      - type: module
        name: CON-002 finding block
      - type: module
        name: Documented Skips — row S-4
    semantic_anchors:

  - path: .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
    read_only: true
    targets:
      - type: module
        name: CON-002 finding block, including its Validation Note
      - type: module
        name: phase04/VAL-410 finding block
      - type: module
        name: Identifier numbering header note
    semantic_anchors:

  - path: .ai/plans/done/01-confirmed-code-defects_DONE.md
    read_only: true
    targets:
      - type: section
        name: D-01
      - type: module
        name: D-01 summary table row
    semantic_anchors:
      - Fix
      - Option A
      - Location
      - Trigger condition

  # READ-ONLY. Cited by the record's statements 1.3 and 1.5.
  - path: src/vkdownloader/services/downloader.py
    read_only: true
    targets:
      - type: function
        name: perform_download
      - type: function
        name: _semaphore_context
    semantic_anchors:
      - the single `async with` over `_semaphore_context(semaphore)` wrapping the dispatch ladder
      - the comment stating one permit per video, acquired exactly once

  - path: src/vkdownloader/services/batch_downloader.py
    read_only: true
    targets:
      - type: class
        name: _TrackedSemaphore
      - type: class
        name: ConcurrencyTracker
    semantic_anchors:
      - the batch entry point's single `asyncio.Semaphore(settings.max_concurrent_downloads)` construction
      - the `_TrackedSemaphore` wrapper passed to `download_video` as the `semaphore` argument

  - path: src/vkdownloader/services/segment_downloader.py
    read_only: true
    targets:
      - type: function
        name: _run_download_session
      - type: function
        name: _download_segment_concurrent
      - type: class
        name: DownloadPolicy
      - type: function
        name: _create_connector
    semantic_anchors:
      - "semaphore_to_use — the segment layer's own fresh asyncio.Semaphore"
      - "is_bounded_batch = video_semaphore is not None — the only use of the batch permit in this layer"
      - "the D-01 and CON-009 comment block above that construction"
      - "DownloadPolicy.is_bounded_batch, the only consumer of the boolean"
      - "connection_ceiling = settings.max_concurrent_downloads, bound to both connector ceilings"

  - path: src/vkdownloader/config.py
    read_only: true
    targets:
      - type: field
        name: Settings.max_concurrent_downloads
    semantic_anchors:
      - the field description naming three levels of bounding

changes:

  - action: add_code
    description: >
      Create EXACTLY ONE new prose file:
      .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md
      It lives outside src/ and tests/, so EXPECTED_SDIST_ENTRIES is unaffected. It MUST NOT wear the
      -validated-findings.md suffix. THE RECORD'S FULL TEXT IS SPECIFIED VERBATIM IN record_content
      BELOW — the Implementor writes THAT TEXT, with no additions, no omissions and no re-wording. The
      six statements below are the same content in specification form, for the Implementor's check.

  - action: document
    description: |
      THE SIX REQUIRED STATEMENTS, re-derived at HEAD = 3c25dda from CON-002, phase04/VAL-404,
      phase04/VAL-410 and WHAT B11 ACTUALLY SHIPPED. Plan 08's version of this list predates B8, B9,
      B11, D8, D9, D10 and section 12 X1; the three marked CHANGED below are the corrections, with
      their reasons, and they are binding over plan 08's wording.

      (1) THE STRUCTURAL FACT, re-derived against the live tree, with SEMANTIC anchors and NO line
          numbers. It has FOUR parts, not three:
          (1a) `perform_download` in src/vkdownloader/services/downloader.py takes the per-video
               permit EXACTLY ONCE, in a single `async with` over `_semaphore_context(semaphore)` that
               wraps the ENTIRE method-dispatch ladder, so every branch runs inside one acquisition. In
               single-download mode `_semaphore_context` returns a no-op context manager and NO permit
               is taken at all — consistent with the condition, which requires batch mode.
          (1b) The batch layer builds exactly ONE `asyncio.Semaphore(settings.max_concurrent_downloads)`
               per batch run, wraps it in `_TrackedSemaphore`, and passes the wrapper to
               `download_video` as the `semaphore` argument; `ConcurrencyTracker` is incremented on
               acquire and decremented on release, so the reported peak counts VIDEOS, and its own
               docstring says so.
          (1c) The segment layer builds its OWN fresh `asyncio.Semaphore` — the local
               `semaphore_to_use` in `_run_download_session` — and hands it to `DownloadPolicy.semaphore`.
               The batch permit enters that layer ONLY as the parameter `video_semaphore`, consumed for
               ONE purpose: the boolean `is_bounded_batch = video_semaphore is not None`. NO semaphore
               object is forwarded from the batch layer into the segment layer. Measured exhaustively:
               the only `async with` claims against any semaphore in the whole of src/ are
               `async with semaphore_context:` (the per-video permit) and `async with policy.semaphore:`
               (the segment-local one); the only `.acquire()` calls in src/ are `_TrackedSemaphore`'s own.
          (1d) CONSEQUENCE: the D-01 nested-claim shape does NOT reproduce. This is a structural fact
               read off the source, NOT a runtime observation.
          (1e) CHANGED BY EDGE C2 — `max_concurrent_downloads` IS NOW A THIRD BOUND. Before the
               transport work it sized TWO mechanisms (the batch per-video semaphore with its live-task
               counting window, and the segment per-download semaphore with its own counting window);
               the connection pool was NOT sized by the setting — `_create_connector` passed a constant
               total ceiling and no per-origin ceiling at all, so the per-origin bound was the HTTP
               library's UNBOUNDED sentinel. What the record observed after that work landed: both
               connector ceilings now bind to the same setting value through one local on BOTH return
               paths; the segment layer's D-01 comment gained a CON-009 clause recording that the
               per-origin term therefore cannot be the binding one, that the segment semaphore stays the
               single binding authority, and that the connector is PER DOWNLOAD with no process-wide
               bound; and the field description now names THREE levels where it named two.
               THE RECORD MUST NOT DESCRIBE THE PRE-B8 PICTURE AS CURRENT — it states what the older
               description said and that it is superseded, and it asserts NOTHING about how the HTTP
               library enforces its own ceilings, because that is a property of an installed library
               and not of this repository's source.

      (2) THAT THE PRODUCTION CONDITION WAS NOT EXECUTED, and why. The condition is: batch mode,
          videos in flight at or above the ceiling, and at least one video taking the segment path.
          It has NOT been executed — not by the phase that filed the finding, by that phase's own
          design, and not by this block. This engagement has no network access and seeks none. What
          WAS executed was the ROUTE, with the session and the media-method result substituted, and a
          substituted route is not the condition. **NO INFERENCE IS DRAWN**: the record states neither
          that the condition would be harmless nor that it would fail, in either direction.

      (3) THAT THE PRIMITIVE-IDENTITY COMPARISON IS NOT PROOF OF THE CONDITION'S BEHAVIOUR. It shows
          WHICH object the segment layer claims; it cannot show WHAT HAPPENS when the condition runs.
          ADDITIONALLY, and this is new: this block's own re-derivation does not change that — it was
          made by reading the source, not by running the condition, and re-deriving a fact statically
          does not convert it into an observation. Nothing here closes the finding.

      (4) CHANGED — D-01 WAS FIXED, BUT THE "EXECUTE THE PRODUCTION CONDITION" HALF REMAINS
          OUTSTANDING. Plan 08 said Option A being implemented "retires" that half. That is what
          phase04/VAL-410's recommendation proposes, and it is NOT what the evidence supports as a
          statement about what has been done: a remedy that is in place and a condition that was
          never run are two different facts. WHAT IS TRUE: the archived register's Fix entry offered
          two ownership models and OPTION A IS WHAT THE CODE IMPLEMENTS — one permit per video, with
          the segment layer creating and owning its own semaphore sized by the same setting. The
          shipped code satisfies Option A in a STRONGER FORM THAN ITS WORDING REQUIRES: the shared
          permit is not forwarded into the segment layer at all, so it cannot be re-claimed there, and
          the peak accounting Option A asks for is performed by the wrapper at the video level.
          Option A explains WHY the nested-claim shape is absent. It does NOT execute the condition.
          THEREFORE THE RECOMMENDATION IS OUTSTANDING IN BOTH HALVES, and the record says so:
            - First half — execute the condition once against a live batch and retire the register's
              claim. NOT PERFORMED and NOT PERFORMABLE HERE: it requires a live origin, which this
              engagement's boundary forbids. OWNER: the phase that owns concurrency and cancellation
              findings. TRIGGER: a run permitted to contact a live origin and to execute the condition
              end to end.
            - Second half — amend the register to record that the nested claim was replaced by a
              segment-layer-owned primitive. Deferred to statement (5).
          The record also states that the register's D-01 entry itself is untouched, is not retired,
          is not amended, and is not claimed to be wrong.

      (5) THAT THE REGISTER'S OWN LOCATION LIST IS STALE, THAT CORRECTING IT IS PHASE 09's SUBJECT BY
          R-E, AND THAT phase04/VAL-410 IS NOT CLAIMED. UNCHANGED IN SUBSTANCE, SHARPENED IN TWO WAYS:
            - The staleness has GROWN. Measured against the live tree, EVERY line reference in the
              register's Location entry now fails to point at the statement it names, and each has
              moved since the validation measured it — the validation recorded the shipped positions
              and the statements have shifted again since. The statements are all still present in the
              shipped code, under the semantic anchors statement (1) names. The record states this
              WITHOUT quoting a single line number, because it is the same rule it is documenting.
            - phase04/VAL-410 HAS TWO HALVES AND BOTH ARE OUTSTANDING. Correcting the two path
              references inside CON-002 — in the source report and in the validated artifact — and
              recording there that D-01 was fixed rather than merely unexecuted: OWNER a documentation
              plan explicitly permitted to edit .ai/audit/**/findings.md; TRIGGER such a plan; BLOCKED
              HERE because both targets are read-only for this engagement. The register's own stale
              Location list and its wording generally: OWNER phase 09, by the validation's own R-E
              allocation; TRIGGER phase 09's run. THE RECORD PERFORMS NEITHER CORRECTION AND CLAIMS
              NEITHER. Recording the deferral is the whole of its obligation.
          THE RECORD MUST NOT REPRODUCE THE STALE REGISTER PATH LITERALLY. It names only the location
          that exists, .ai/plans/done/01-confirmed-code-defects_DONE.md. A durable record must not
          propagate the very path defect the correction is about, and section 8.3's negative grep for
          that literal is part of the gate. The record describes the defect without restating the
          broken reference.

      (6) CHANGED — THAT CON-002 REMAINS FILED, REMAINS UNVERIFIED, AND ITS HISTORICAL CELL REMAINS
          PERMANENTLY, UNCORRECTED; AND THE ENCODING IS CITED BY WHAT B11 ACTUALLY DID.
          Plan 08 said to cite B11 "by block id and title, not by asserting its remedy". That
          instruction was correct when B11 was a plan; B11 has now LANDED, so the forward promise is
          replaced by a verifiable fact and the prohibition survives in the only form that still makes
          sense: cite the SHIPPED MECHANISM, verified against the commit, never an assumed outcome.
          THE RECORD MUST CITE:
            - block `B11` by block id and title, and commit `3c25dda`;
            - the mandatory `Verification` field added to the authoritative template, present in BOTH
              its finding-block field table and its field reference, values `observed` and `unverified`,
              defined in its classification guide, required on EVERY finding;
            - the template's `severity` row stating that when a runtime consequence was NOT observed the
              band is COMPOSED FROM THE STRUCTURAL FACT UNDER THE OWNING PHASE'S OWN SEVERITY TABLE,
              and that the row prescribes no band of its own;
            - phase 04's FOUR absolute "no severity" prohibitions reconciled to that rule — the
              preamble's two-findings bullet, the structure-only-severity bullet, the documented-skips
              bullet, and binding rule W-4 of the reporting section;
            - ONE matching check row added to the validation task, "Verification recorded";
            - that NO fifth severity member and NO fifth type label were added, so the validation task's
              own prohibition against a fifth word is untouched and still true.
          AND IT MUST STATE, PLAINLY:
            - the rule is PROSPECTIVE — a severity already written is not re-read under it;
            - CON-002's cell was ALREADY WRITTEN, so NO band is composed for it now and none ever will
              be by this mechanism;
            - composing one today WOULD BE reading an already-written cell under a prospective rule,
              which is forbidden — and this is the clause that stops a future reader from "fixing" it;
            - the composition rule governs FUTURE reports and says nothing about what this finding's
              cell should have said.
          THE RECORD MUST NOT NAME WHICH BAND WOULD BE COMPOSED. It describes the mechanism and stops.

  - action: prohibited
    description: >
      MUST NOT change a single character of src/, tests/, docs/, README.md, .env.example or .kilo/.
      MUST NOT write any .py file — THIS BLOCK WRITES NO CODE AT ALL, so the project rule against
      print() has nothing to attach to and is satisfied by construction. MUST NOT create any file other
      than the one named above — no scratch file, no plan file, no summary, no index. MUST NOT assign a
      severity, and LOW in particular is FORBIDDEN: the record MUST NOT contain the token LOW in any
      case and MUST NOT name which band the composition rule would yield for CON-002. MUST NOT delete,
      merge or reclassify CON-002. MUST NOT close it on the primitive-identity observation. MUST NOT
      contain a verdict on the unexecuted production condition — "safe", "broken", "harmless because",
      "would not happen", or any prediction in either direction is the over-claim the validator warned
      against. MUST NOT touch .ai/audit/04-concurrency-cancellation/findings.md or the validated
      artifact; both must be byte-identical before and after, proved with the two-command D2 gate.
      MUST NOT touch .ai/audit/03-network-resilience/findings.md — section 12 X1 records that B11
      returned it to the working tree byte-identical to HEAD, and this block MUST NOT recreate,
      re-delete or "fix" that path in any direction. MUST NOT touch .ai/plans/00_overview.md or
      .ai/plans/01 through 04 — those are tracked DELETIONS belonging to a different project
      (Mko-AINotify) that this engagement did not make, and section 11 E5 owns them. MUST NOT stage
      any path under .ai/audit/ except its own new record file (D2). MUST NOT commit tmp/ and MUST NOT
      cite a tmp/ path as evidence (D6). MUST NOT touch
      docs/00-overview/doc-maintenance-rules.md and MUST NOT create any docs/ file (D7). MUST NOT write
      an unqualified VAL-4xx identifier anywhere — every phase-04 pipeline finding is written fully
      qualified, and the record's references are correct.
    code_hint: |

# THE RECORD'S FULL TEXT. The Implementor writes exactly this, into the path named in files[].
# Verified against all four section 8.3 negative greps at authoring time: 0 matches for each, and 0
# matches for a bare LOW token and for an unqualified VAL-4xx id.
record_content: |-
    # CON-002 — Verification Record

    **Finding recorded:** `CON-002` — *"The shipped condition that reaches the per-part transfer from
    inside the outer claim is not executed"*.
    **Filed in:** `.ai/audit/04-concurrency-cancellation/findings.md` (source report) and
    `.ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md` (validated artifact).
    **Written by:** block `B10` of `.ai/plans/09-concurrency-cancellation-audit-fixes-completion.md`,
    against tree state `HEAD = 3c25dda`.
    **Kind:** a verification record. This file is **not** a validation artifact, **not** a finding, and
    **not** a severity assignment.

    **Anchoring rule for this file.** Every code reference below is **semantic** — a module, a function,
    a class, a field. **No line number appears in this file, deliberately**: the register this record
    discusses is itself stale in exactly that respect (section 5), and a durable record must not
    reintroduce the defect it documents.

    ---

    ## What this record is, and what it is not

    `CON-002` **remains filed**, **remains marked `UNVERIFIED`**, and **continues to carry no severity**.
    Nothing here changes that, and nothing here should be read as a step towards changing it. Its
    severity cell in the source report reads `*none — not executed*` and **remains exactly as filed**.

    This record answers two questions only: what was *structurally observed* about the production
    condition, and what was *not* executed. It assigns no severity, reaches no verdict on the condition,
    and does not delete, merge, reclassify, close or retire the finding.

    ---

    ## 1. The structural fact, re-derived against the live code

    **1.1 — The per-video permit is taken exactly once, around the whole ladder.**
    `src/vkdownloader/services/downloader.py`, function `perform_download`: a single
    `async with` over `_semaphore_context(semaphore)` wraps the entire method-dispatch ladder, so every
    branch of that ladder runs inside one acquisition of the per-video permit. The comment above it
    states the intent: one permit per video, acquired exactly once at that point, and the segment layer
    does not re-acquire from it. In single-download mode `_semaphore_context` returns a no-op context
    manager and **no** permit is taken at all — consistent with the condition, which requires batch mode.

    **1.2 — The batch layer builds one primitive for the whole run.**
    `src/vkdownloader/services/batch_downloader.py`, the batch entry point: constructs **one**
    `asyncio.Semaphore(settings.max_concurrent_downloads)` per batch run, wraps it in `_TrackedSemaphore`,
    and passes that wrapper into `download_video` as the `semaphore` argument. `_TrackedSemaphore`
    increments `ConcurrencyTracker` on acquire and decrements it on release, so the reported peak counts
    **videos**; `ConcurrencyTracker`'s own docstring says so in as many words.

    **1.3 — The segment layer builds its own primitive and carries only a boolean across.**
    `src/vkdownloader/services/segment_downloader.py`, function `_run_download_session`: constructs a
    **fresh** `asyncio.Semaphore(settings.max_concurrent_downloads)` — the local `semaphore_to_use` — and
    passes it to `DownloadPolicy.semaphore`. The batch permit enters this layer as the parameter
    `video_semaphore` and is consumed for **one purpose only**, the boolean
    `is_bounded_batch = video_semaphore is not None`. **No semaphore object is forwarded from the batch
    layer into the segment layer.** The only claim made against any semaphore inside the segment
    transfer path is `async with policy.semaphore:` in `_download_segment_concurrent`, and
    `policy.semaphore` is the segment-local object. The only `.acquire()` calls anywhere in `src/` are
    `_TrackedSemaphore`'s own.

    **1.4 — The consequence, and its exact limit.**
    The nested-claim shape the archived register's `D-01` describes — one non-reentrant primitive claimed
    once per video and again per segment — **does not reproduce in this code.** That is a structural
    fact read off the source and re-derived for this record. It is **not** a runtime observation, and
    section 3 says why that distinction is load-bearing.

    **1.5 — The setting is a third bound, and this record observed the amendment.**
    Before the transport work, `Settings.max_concurrent_downloads` sized **two** mechanisms: the batch
    layer's per-video semaphore with its live-task counting window, and the segment layer's per-download
    semaphore with its own counting window. The transport connection pool was **not** sized by the
    setting — `_create_connector` passed a constant total ceiling and no per-origin ceiling at all, so
    the per-origin bound was the HTTP library's *unbounded* sentinel.

    **What this record observed after that work landed**, read from the source:

    - `_create_connector` now binds **both** its total ceiling and its per-origin ceiling to the same
      setting value, through a single local, on **both** of its return paths;
    - the segment layer's `D-01` comment has gained a clause recording that the two connector ceilings
      carry the same value, that the per-origin term therefore cannot be the binding one, that the
      segment semaphore remains the single binding authority, and that the connector is **per download**
      with no process-wide bound;
    - `Settings.max_concurrent_downloads`'s field description now names **three** levels — the batch
      gate, the segment fan-out, and the per-download connection pool — where it previously named two.

    **What that means for a reader holding an older description of this setting:** the two-level picture
    is superseded. There is still **no process-wide bound**; the honest aggregate is per-download
    multiplied by videos in flight. This record asserts nothing about how the HTTP library enforces its
    own ceilings — that is a property of an installed library, not of this repository's source, and it
    is not what this record is about.

    ---

    ## 2. What was NOT executed, and why

    **2.1 — The condition.** Batch mode, videos in flight at or above the ceiling, and at least one
    video taking the segment path.

    **2.2 — It has not been executed.** No batch was run against a live origin by the phase that filed
    the finding — by that phase's own design — and none was run for this record. This engagement has no
    network access, and this record neither requires nor seeks any.

    **2.3 — What was executed instead.** The **route** to the per-part transfer, with the session and
    the media-method result substituted. A substituted route is not the condition.

    **2.4 — No inference is drawn.** This record states neither that the condition would be harmless nor
    that it would fail. It offers no prediction about what a live origin or a live batch would do, in
    either direction. That question is open, and this record leaves it open.

    ---

    ## 3. A structural identity comparison is not proof

    The comparison that establishes section 1 is an **identity** comparison between two semaphore
    objects. It shows *which object* the segment layer claims. It cannot show *what happens* when the
    condition runs. The validator that decided this finding said exactly that, and this record repeats
    it rather than improving on it: **the structural identity comparison is not proof of the
    condition's behaviour.**

    **This record's own re-derivation does not change that.** It was made by reading the source, not by
    running the condition, and re-deriving a fact statically does not convert it into an observation.

    **Nothing here closes the finding.** No reader may take section 1 as a clean result, and no reader
    may treat the register's registered claim as confirmed against this code.

    ---

    ## 4. The register's remedy was implemented; the live-batch half of the recommendation is still outstanding

    **4.1 — Option A was implemented.** The archived register's **Fix** entry offered two ownership
    models for the permit. **Option A** — one permit per video, with segments bounded by a separate
    inner semaphore that the segment layer creates and owns — is what the code implements. The shipped
    code satisfies Option A in a stronger form than its wording requires: the shared permit is not
    forwarded into the segment layer at all, so it cannot be re-claimed there, and the peak accounting
    that Option A asks for is performed by the wrapper at the video level.

    **4.2 — What that explains, and what it does not.** It explains **why the nested-claim shape is
    absent**: Option A is the reason. It does **not** execute the condition. A remedy that is in place and
    a condition that was never run are two different facts, and a record that conflates them has
    over-claimed.

    **4.3 — Therefore the recommendation is outstanding in both halves.**

    - **First half — execute the condition once against a live batch and retire the register's claim.**
      **Not performed, and not performable here:** it requires a live origin, which this engagement's
      boundary forbids. **Owner:** the phase that owns concurrency and cancellation findings.
      **Trigger:** a run permitted to contact a live origin and to execute the condition end to end.
    - **Second half — amend the register to record that the nested claim was replaced by a
      segment-layer-owned primitive.** Deferred to section 5.

    **4.4 — The register's entry itself is untouched by this record.** It still stands as registered. This
    record does not retire it, does not amend it, and does not claim it is wrong.

    ---

    ## 5. The register's Location list is stale, and `phase04/VAL-410` is deferred

    **5.1 — The Location list fails.** The archived register's **Location** entry cites line numbers.
    **Every line reference in it now fails to point at the statement it names**, and the drift is larger
    than when the validation measured it: the statements are all still present in the shipped code, under
    the semantic anchors named in section 1, and each has moved since. A reader following the register's
    own numbers lands on unrelated statements.

    **5.2 — The stale path is deliberately not reproduced here.** The finding and the register citation
    point at a register location that no longer exists; the register was archived, and the directory it
    was cited in holds unrelated files. A durable record must not propagate the very path defect the
    correction is about, so this file names only the location that exists:
    `.ai/plans/done/01-confirmed-code-defects_DONE.md`.

    **5.3 — `phase04/VAL-410` is NOT claimed** by this record or by the block that wrote it. Its work
    has two halves and **both are outstanding**:

    - **Correcting the two path references inside `CON-002`** — in the source report and in the validated
      artifact — and recording there that `D-01` was fixed rather than merely unexecuted. **Owner:** a
      documentation plan explicitly permitted to edit `.ai/audit/**/findings.md`. **Trigger:** such a
      plan. **Blocked here** because both targets are read-only for this engagement.
    - **The archived register's own stale `Location` list, and the register's wording generally**, is
      **phase `09`'s subject** by the validation's own `R-E` allocation. **Owner:** phase `09`.
      **Trigger:** phase `09`'s run.

    **5.4 — This record performs neither correction** and claims neither. Recording the deferral is the
    whole of its obligation here.

    ---

    ## 6. This finding's state, and the encoding that now exists for it

    **6.1 — State.** `CON-002` **remains filed**, **remains `UNVERIFIED`**, and **carries no severity**.
    It is not deleted, not merged, not reclassified, not closed.

    **6.2 — The historical cell stays permanently, uncorrected.** `*none — not executed*` sits outside
    the report format's severity vocabulary by design. It is **not** a defect awaiting repair.

    **6.3 — The encoding exists and is landed, not promised.** Block `B11` of
    `.ai/plans/09-concurrency-cancellation-audit-fixes-completion.md` — *"Give the report format a legal
    encoding for a not-executed finding"* — shipped it in commit `3c25dda`. What it did, verified
    against that commit rather than assumed:

    - the authoritative report template gained a mandatory **`Verification`** field, present in both its
      finding-block field table and its field reference, with the values `observed` and `unverified`, and
      defined in its classification guide. It is required on **every** finding;
    - the template's `severity` row states that when a runtime consequence was **not observed**, the band
      is **composed from the structural fact under the owning phase's own severity table**, and that the
      row prescribes no band of its own;
    - phase `04`'s handbook had its four absolute "no severity" prohibitions reconciled to that rule — in
      the preamble's two-findings bullet, in the structure-only-severity bullet, in the
      documented-skips bullet, and in binding rule **W-4** of the reporting section;
    - the validation task gained one matching check row, `Verification recorded`;
    - **no fifth severity member and no fifth type label were added**, so the validation task's own
      prohibition against a fifth word is untouched and still true.

    **6.4 — The rule is PROSPECTIVE, and that is precisely why this finding's cell is untouched.** The
    template states it in terms: a severity already written is not re-read under the rule. `CON-002`'s
    cell was already written. **No band is composed for it now, and none ever will be by this
    mechanism.** Composing one today would be reading an already-written cell under a prospective rule,
    which is forbidden.

    **6.5 — Scope of the rule.** The composition rule governs **future** reports. It says nothing about
    what this finding's cell should have said, and this record does not either.

    ---

    ## 7. Standing statement

    The structural fact is recorded in section 1. The condition was not executed, and section 2 says so
    without inferring anything about it. **No severity is assigned. No verdict is recorded. The finding
    is not closed.**

    Outstanding, with the owners and triggers stated above: executing the condition against a live batch
    (section 4.3), and the two corrections `phase04/VAL-410` describes (section 5.3).

verification:
  # No test can see a .md file. The gate is an INDEPENDENT READ plus MECHANICAL PROOFS.
  # Every value below was measured at HEAD = 3c25dda during this task's planning and is the expected
  # output of the corresponding command. The Implementor runs all of them; the Validator re-runs them
  # verbatim and compares.
  baseline_measured_at: "HEAD = 3c25dda"

  step_1_baseline_record:
    commands: |
      uv run pytest -q
      uv run ruff check src tests
      uv run ruff format --check src tests
      uv run mypy src
    expected:
      pytest: "772 passed, 4 skipped, 1 warning"      # floor is 762 per section 8.1; it rose because B9 added tests
      ruff_check: "All checks passed!"
      ruff_format: "54 files already formatted"
      mypy: "Success: no issues found in 31 source files"
    note: >
      The skip count MUST remain exactly 4 and the warning count exactly 1. A change in either means a
      test was added, removed or deselected by this block, which is a gate failure. This block writes
      no test, so the counts cannot legitimately move.

  step_2_d2_read_only_gate:
    commands: |
      git diff --exit-code HEAD -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
      git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
    expected:
      first: "no output, EXIT=0"
      second: |
        .ai/audit/04-concurrency-cancellation/findings.md
        .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
        EXIT=0
    note: >
      BOTH commands are required (D2). A green diff with a red ls-files is a FAILURE, never a pass. Both
      were measured green at HEAD = 3c25dda before this block ran.

  step_3_negative_product_gate:
    commands: |
      git diff --exit-code HEAD -- src tests docs README.md .env.example .kilo
    expected: "no output, EXIT=0"
    measured_before_block: "no output, EXIT=0"

  step_4_new_file_proof:
    commands: |
      git status --short -- .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md
      git diff --cached --name-status
      git diff --name-status HEAD -- .ai/audit
      git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md
    expected_staged:
      git_status_short: "A  .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md"
      diff_cached: "exactly one line: A<TAB>.ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md"
      diff_name_status_audit: "exactly one line: A<TAB>.ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md"
      ls_files_error_unmatch: "prints the path, EXIT=0"
    expected_committed:
      git_status_short: "empty (the path is clean against HEAD)"
      diff_cached: "empty"
      diff_name_status_audit: "empty (the file is now IN HEAD)"
      ls_files_error_unmatch: "prints the path, EXIT=0"
    why_not_git_diff_exit_code: >
      THE PLAN'S OWN PROOF IS VACUOUS HERE, AND THIS BLOCK MUST NOT USE IT AS ITS PRIMARY PROOF.
      Measured at HEAD = 3c25dda, BEFORE this block runs:
        git ls-files --error-unmatch -- <the new path>  ->  error, EXIT=1 ("did not match any file(s) known to git")
        git diff --exit-code HEAD -- <the new path>     ->  no output, EXIT=0
      A file absent from HEAD makes `git diff --exit-code HEAD` over it succeed trivially — it cannot
      distinguish "created and committed" from "never existed". The proof for a NEW file is therefore
      `git status --short` (staged or committed), `git diff --cached --name-status` (the staged set is
      exactly one file), and `git ls-files --error-unmatch` (it is tracked). All three are run.
    measured_before_block:
      git_status_short: "no output, EXIT=0 (pathspec matches nothing yet)"
      diff_cached: "no output, EXIT=0 (nothing staged)"
      ls_files_error_unmatch: "error: pathspec ... did not match any file(s) known to git, EXIT=1"

  step_5_only_the_new_file_changed:
    commands: |
      git diff --name-status HEAD
    expected_exact: |
      D	.ai/plans/00_overview.md
      D	.ai/plans/01_backend_connector.md
      D	.ai/plans/02_notification_provider.md
      D	.ai/plans/03_security_state.md
      D	.ai/plans/04_lifecycle_config_testing.md
      D	.ai/plans/VALIDATION_REPORT.md
      D	.ai/plans/error_ref.md
      M	.ai/problems/PROBLEM.md
      A	.ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md
    note: >
      The first nine entries are the PRE-EXISTING working-tree delta that this engagement did not make:
      eight tracked deletions of another project's plan files (Mko-AINotify — verified by reading their
      content at HEAD) and one modified file under .ai/problems/. They are measured at HEAD = 3c25dda
      and MUST be byte-identical afterwards. The ONLY difference this block introduces is the single
      added line. Any other added, modified or deleted entry is a gate failure. Compare with the
      pre-edit `git status --short`, which shows exactly those same nine tracked entries plus five
      untracked paths (.ai/plans/05 through 09 and tmp/).

  step_6_x1_absence_proof:
    commands: |
      git diff --name-status HEAD -- .ai/audit/03-network-resilience/findings.md
      git status --short -- .ai/audit/03-network-resilience/findings.md
      git diff --exit-code HEAD -- .ai/audit/03-network-resilience/findings.md
    expected: "all three produce no output; the first and second EXIT=0"
    note: >
      Section 12 X1: B11 (3c25dda) returned this path to the working tree byte-identical to HEAD, and
      `git diff --name-status HEAD -- .ai/audit` was empty at that point. THIS BLOCK MUST NOT RECREATE,
      RE-DELETE OR "FIX" THAT PATH IN ANY DIRECTION. All three commands above were measured producing
      no output at HEAD = 3c25dda, and step 4's `git diff --name-status HEAD -- .ai/audit` must show
      the new record as the ONLY entry under .ai/audit — which proves this path is absent from the
      block's staged set.

  step_7_negative_greps_on_the_record:
    description: >
      Four greps from section 8.3 plus two the plan requires. ALL SIX return no match in the new record.
      All six were run against the exact text in record_content during this task's planning and each
      returned 0 matches. Run them again against the file as written.
    commands_and_meaning:
      - "rg -n -i 'severity.{0,80}LOW|LOW.{0,80}severity' <path>   -> 0 matches (the forbidden observed-severity substitute)"
      - "rg -n -i '\\bis\\s+safe|is\\s+broken|confirmed\\s+safe|refuted' <path>   -> 0 matches (a verdict on the unexecuted condition)"
      - "rg -n -F '.ai/problems/01-confirmed-code-defects.md' <path>   -> 0 matches (the record names the corrected path only, and states the correction is not claimed)"
      - "rg -n -i '\\.(py|md):0*[0-9]+' <path>   -> 0 matches (semantic anchors only, no line number)"
      - "rg -n '(?<![0-9/])VAL-4[0-9][0-9]' <path>   -> 0 matches (every phase-04 id is written phase04/VAL-NNN)"
      - "rg -n '(?<![A-Za-z-])LOW(?![A-Za-z-])' <path>   -> 0 matches (no severity word at all, in any case)"
    note: >
      The third grep is the one with an apparent tension and it is deliberate: section 8.3 requires the
      record to NAME THE CORRECTED PATH and to STATE THAT THE CORRECTION IS NOT CLAIMED, and it
      simultaneously forbids the stale literal. Both hold if the record describes the defect without
      restating the broken reference — which is what record_content section 5.2 does.

  step_8_positive_enumeration:
    description: >
      "It reads well" is not the gate. The six statements ARE enumerable, so for each of the six, the
      report shows the record section that satisfies it and the line that carries it.
    mapping:
      - "statement 1 (structural fact)        -> record sections 1.1, 1.2, 1.3, 1.4, 1.5"
      - "statement 2 (not executed, no inference) -> record sections 2.1, 2.2, 2.3, 2.4"
      - "statement 3 (identity is not proof)  -> record section 3"
      - "statement 4 (Option A fixed; live-batch half outstanding) -> record sections 4.1, 4.2, 4.3, 4.4"
      - "statement 5 (Location list stale; phase04/VAL-410 deferred) -> record sections 5.1, 5.2, 5.3, 5.4"
      - "statement 6 (state permanent; B11 by what it shipped) -> record sections 6.1, 6.2, 6.3, 6.4, 6.5"

  step_9_validator_independent_read:
    description: >
      The Validator reads the whole file. The mechanical proofs prove the file is the RIGHT prose and
      that nothing else changed; the read proves it is coherent and that it reads as a record rather
      than as a verdict. Both are required. The Validator confirms, in writing: no severity is assigned
      anywhere; no verdict on the unexecuted condition appears in either direction; the finding is not
      closed, deleted, merged or reclassified; the live-batch half is recorded as outstanding WITH an
      owner and a trigger; phase04/VAL-410 is recorded as deferred and NOT claimed; and B11 is cited by
      block id, title, commit and shipped mechanism rather than by an asserted outcome.

acceptance_criteria:
  - Exactly ONE new file exists at
    .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md, its content is
    the record_content specified above, and it does NOT wear the -validated-findings.md suffix
  - The record contains NO line number for any cited code unit — every reference is a module, function,
    class or field name
  - The record states all six required points, in the required order, and each is traceable to a named
    section by the statement-8 mapping
  - The record cites B11 by block id, title AND commit 3c25dda, and states the mechanism B11 shipped —
    the mandatory Verification field, the composition rule on the severity row, the four reconciled
    phase-04 prohibitions, the one validator check row, and the absence of any fifth member — and cites
    NO assumed or asserted outcome
  - The record states that the rule is PROSPECTIVE and that CON-002's historical `*none — not executed*`
    cell remains permanently and uncorrected, and that composing a band for it today would be forbidden
  - The record contains NO token LOW in any case, and does not name which band the composition rule
    would yield for CON-002
  - CON-002 is not deleted, not merged, not reclassified, not closed, and carries no severity; both its
    source report and its validated artifact are byte-identical before and after
  - The record does NOT contain a verdict on the unexecuted production condition in either direction,
    and does not predict what a live origin or a live batch would do
  - The record records the "execute the production condition against a live batch" half as OUTSTANDING,
    with its owner (the phase that owns concurrency and cancellation findings) and its trigger (a run
    permitted to contact a live origin)
  - The record names phase 09 as the owner of the register's stale Location list and the register's
    wording, by R-E, and states that phase04/VAL-410 is NOT claimed, naming the deferral, its owner and
    its trigger for BOTH of its halves
  - The record reproduces NO stale register path literally; it names only
    .ai/plans/done/01-confirmed-code-defects_DONE.md
  - The record describes the post-B8 concurrency picture as current — the setting as a THIRD bound — and
    explicitly marks the two-level picture as superseded, so no reader can mistake it for the state of
    the code
  - The record asserts nothing about how the HTTP library enforces its own connector ceilings
  - All six negative greps of step 7 return no match in the record
  - The baseline is green and UNCHANGED in shape — 772 passed, 4 skipped, 1 warning; ruff clean; format
    clean; mypy clean on 31 source files
  - git diff --exit-code HEAD -- src tests docs README.md .env.example .kilo is EMPTY — this block
    changes no product file of any kind, and writes no code at all
  - The two-command D2 gate over the two read-only audit artifacts is GREEN — git diff --exit-code HEAD
    empty AND git ls-files --error-unmatch printing both paths
  - The new file is TRACKED and its staged set is exactly one path — git status --short over the record
    path shows it staged (A) before commit and clean after, and
    git diff --cached --name-status shows exactly one added path
  - git diff --name-status HEAD shows the nine pre-existing entries byte-identical and EXACTLY ONE added
    entry — the new record file — and no other addition, modification or deletion
  - .ai/audit/03-network-resilience/findings.md is absent from every diff the block produces; all three
    X1 commands return no output
  - .ai/plans/00_overview.md and .ai/plans/01 through 04 are NOT staged, NOT restored and NOT recreated;
    tmp/ is NOT staged and NOT cited as evidence
  - No file under docs/ is created or modified, and docs/00-overview/doc-maintenance-rules.md is
    untouched
  - No identifier in the record, the report or the commit body is an unqualified VAL-4xx; every
    phase-04 identifier is written fully qualified
  - No test can see this change; the mechanical proofs of steps 2 through 7 plus the Validator's
    independent read of step 9 are the entire gate

extra_context: |
  ## Measured at HEAD = 3c25dda (this block's tree state) — every value the Implementor must reproduce

  ```
  $ uv run pytest -q
  772 passed, 4 skipped, 1 warning in 35.00s

  $ uv run ruff check src tests
  All checks passed!

  $ uv run ruff format --check src tests
  54 files already formatted

  $ uv run mypy src
  Success: no issues found in 31 source files
  ```

  ```
  $ git diff --exit-code HEAD -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
  (no output)                                                          EXIT=0

  $ git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md .ai/audit/04-concurrency-cancellation/findings.md
  .ai/audit/04-concurrency-cancellation/findings.md
  .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
                                                                    EXIT=0

  $ git diff --exit-code HEAD -- src tests docs README.md .env.example .kilo
  (no output)                                                          EXIT=0

  $ git diff --name-status HEAD -- .ai/audit
  (no output)                                                          EXIT=0      <- section 12 X1

  $ git status --short -- .ai/audit/03-network-resilience/findings.md
  (no output)                                                          EXIT=0      <- section 12 X1
  ```

  **The vacuity proof, measured.** Before the file exists:

  ```
  $ git ls-files --error-unmatch -- .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md
  error: pathspec '...' did not match any file(s) known to git
  Did you forget to 'git add'?                                          EXIT=1

  $ git diff --exit-code HEAD -- .ai/audit/99-validation/04-concurrency-cancellation-CON-002-verification-record.md
  (no output)                                                          EXIT=0      <- SUCCEEDS ON A FILE THAT DOES NOT EXIST
  ```

  **The pre-existing working-tree delta, measured** — nine tracked entries this engagement did not make:

  ```
  $ git status --short
   D .ai/plans/00_overview.md
   D .ai/plans/01_backend_connector.md
   D .ai/plans/02_notification_provider.md
   D .ai/plans/03_security_state.md
   D .ai/plans/04_lifecycle_config_testing.md
   D .ai/plans/VALIDATION_REPORT.md
   D .ai/plans/error_ref.md
   M .ai/problems/PROBLEM.md
  ?? .ai/plans/05-entry-architecture-audit-fixes.md
  ?? .ai/plans/06-config-audit-fixes.md
  ?? .ai/plans/07-network-resilience-audit-fixes.md
  ?? .ai/plans/08-concurrency-cancellation-audit-fixes.md
  ?? .ai/plans/09-concurrency-cancellation-audit-fixes-completion.md
  ?? tmp/

  $ git diff --name-status HEAD
  D	.ai/plans/00_overview.md
  D	.ai/plans/01_backend_connector.md
  D	.ai/plans/02_notification_provider.md
  D	.ai/plans/03_security_state.md
  D	.ai/plans/04_lifecycle_config_testing.md
  D	.ai/plans/VALIDATION_REPORT.md
  D	.ai/plans/error_ref.md
  M	.ai/problems/PROBLEM.md
  ```

  The seven deletions are another project's — their content at HEAD reads `Mko-AINotify` throughout
  (section 11 E5). The five untracked paths are plans 05 through 09 and tmp/, none of which this block
  touches. **The ONLY change this block introduces is one added line in the list above.**

  ## Location prerequisites, all verified at HEAD = 3c25dda

  - `.ai/audit/99-validation/` holds **exactly eleven files, and every one ends in
    `-validated-findings.md`.** No non-conforming prose file exists there yet, so the chosen filename
    creates no collision and cannot be confused with a sibling.
  - `.ai/tasks/{todo,validation,done}` all exist and are **empty** (the only files under `.ai/tasks`
    are the three templates). There is nothing to update in a task queue.
  - `.ai/plans/00_overview.md` and `.ai/plans/01` through `04` are **tracked deletions belonging to
    Mko-AINotify**, confirmed by reading their content at HEAD. They are **not** this project's plans,
    they are **not** a place to put this record, and this block MUST NOT stage, restore or recreate
    them.
  - There is **no status file, registry, index or summary anywhere under `.ai/`** that tracks findings.
    `.ai/` holds only `context/`, `models/`, `plans/`, `problems/`, `research/`,
    `structure/map.md` and `templates/`, and none of them indexes findings. **Nothing to update.**

  ## Commit

  Stage **exactly one path** — the record — and commit with the two-command D2 gate re-run first. The
  commit message cites `CON-002`, cites `phase04/VAL-410` as **NOT claimed** and deferred, cites `B11`
  by block id and commit `3c25dda`, and states explicitly that no code changed, no test changed, no
  severity was assigned, no verdict was recorded, and the finding is not closed. It carries the
  eight tracked deletions of the other project's plans, the `tmp/` directory and the untracked plan
  files **unstaged**. Do not skip the pre-commit hook; a hook that rejects this commit must be
  diagnosed, not bypassed.
```

---

## §8 Verification strategy

### §8.1 The per-block gate — every block runs all four

No block is complete until all four of these pass, in this order, from the repository root, **and
until it has re-measured them itself** (§2.4.6 — the tree has already moved twice).

| # | Command | Pass criterion |
|---|---|---|
| 1 | `uv run pytest -q` | exit 0; passed count **≥ 762** and **may only rise**; **skips exactly 4**; **warnings exactly 1**. |
| 2 | `uv run ruff check src tests` | exit 0 · `All checks passed!` |
| 3 | `uv run ruff format --check src tests` | exit 0 · `54 files already formatted` (or higher — it may only rise) |
| 4 | `uv run mypy src` | exit 0 · `Success: no issues found` |

**Plus the block's own gate, run by name:**

```powershell
uv run pytest tests/test_segment_downloader.py -q      # B8   (also: the four pytest.fail hang nets)
uv run pytest tests/test_config.py -q                  # B8, B9
uv run pytest tests/test_extractor.py -q               # B9 (only if a code remedy is selected)
```

**Plus the read-only gate, which is TWO commands and both must pass** (see §5.6 H1):

```powershell
# 1. byte-identity — this is the real check now that the corpus is tracked
git diff --exit-code HEAD -- .ai/audit/04-concurrency-cancellation/findings.md `
                             .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
# 2. tracking proof — a bare git diff is VACUOUS over an untracked path, so prove they are tracked
git ls-files --error-unmatch -- .ai/audit/04-concurrency-cancellation/findings.md `
                                  .ai/audit/99-validation/04-concurrency-cancellation-validated-findings.md
```

**A green `git diff` with a red `git ls-files` is a GATE FAILURE, not a pass.** `0a8fa97` made this
gate live by committing the corpus; nothing guards it, so every block re-asserts it.

**Rules for a block report.**

1. Quote the **exact output** of all four commands. "Tests pass" without output is not a report.
2. **The passed count must not decrease.** The four `D-11` Windows-confinement skips must remain
   exactly **4**, and the suite's warning count must remain exactly **1**. A rise is a failure too.
   **The stated cause for `B8` was wrong and is corrected in §6.2:** a `TCPConnector` that is built
   and read but never used to open a connection does **not** warn in `aiohttp 3.14.1` — its
   `BaseConnector.__del__` returns before the `ResourceWarning` when the connection pool is empty.
   The gate itself stands unchanged; only its mechanism was misattributed.
3. **List every test file and test name you edited**, with one line on why the edit was required by a
   behaviour change rather than by convenience. On the current scope only `B9`'s conditional
   re-scope of `test_extract_with_ytdlp_timeout_raises_extraction_error` is authorised.
4. **Confirm no network was contacted.** `tests/test_packaging.py` is the only test that may, and it
   skips off-CI.
5. **Confirm the block's negative acceptance criteria** — the "byte-identical", "MUST NOT" and "no new
   file" items — with a `git diff --stat` **and** the `git ls-files` tracking proof, never with an
   assurance.
6. **Record every deferred decision the block's Planner resolved**, with the option rejected and why.
   For `B8` that includes the remedy shape; for `B9` and `B11` it is the whole substance of the block.
7. **`git diff --cached --stat` before committing** (§2.4). Every staged path belongs to the block.
   **Never `git add -A`, never `git add .`, never `git commit -a`.**
8. **Qualify every `VAL-` id** as `phase04/VAL-NNN` in the report and in the commit message. An
   unqualified `VAL-4xx` is a defect.

### §8.2 The end-of-engagement gate — after `B10`

| # | Gate | Pass criterion |
|---|---|---|
| 1 | All four baseline commands, in order | exit 0. Expected floor: **≥ 762 passed, 4 skipped, 1 warning** — the count may only rise; the skip and warning counts may not move. |
| 2 | `ruff check` · `ruff format --check` · `mypy` | exit 0, all three. |
| 3 | The read-only gate, **both commands** (§8.1) | `git diff --exit-code HEAD` empty **AND** `git ls-files --error-unmatch` exit 0 on both audit paths. |
| 4 | **`git diff --exit-code HEAD -- src tests docs README.md .env.example .kilo`** | **EMPTY.** Nothing outside `.ai/` was touched by a block, except `docs/` where `B8`/`B9`'s documentation writes are expected and named. |
| 5 | `docs/11-guides/configuration.md`'s `download_timeout` **row** | **Unchanged** (`B9` prohibition 2). Its prose section and `max_concurrent_downloads`' section **are** expected to change — verify the change is the intended one and that the model and the guide still agree field-for-field. |
| 6 | `.kilo/rules/project.md` and `.kilo/agents/*` | **Unchanged**, unless `B11`'s remedy (a) was selected **and** §9 Q4 was answered authorising it. Either way the report states which. |
| 7 | `.ai/templates/audit-findings.md` | **Unchanged** (`B11` prohibition 6). The second template's survival is a recorded, escalated state. |
| 8 | The `ClientTimeout` literals | `sock_read = 60` is **still a literal** at all three sites, and no composed timeout helper appeared. Proof that `B9` did not drift into plan 07's unlanded work. |
| 9 | **`limit = 10` does not exist anywhere in `src/`** | Proof that `B8` closed the literal. |
| 10 | `EXPECTED_SDIST_ENTRIES` | Untouched — no `src/` or `tests/` file was added. `uv run pytest tests/test_packaging.py -q` green. |
| 11 | The landed `B1`–`B7` regression net | `tests/test_batch_downloader.py::TestBatchDownloaderSemaphore` (both cases) and `::TestBatchCancellationReporting` green **and unedited**; the four `pytest.fail` hang nets green **and unedited**. |
| 12 | The documented `130` still holds | `docs/99-reference/cli-reference.md` and `cli-reference-clean.md` **unchanged**. |
| 13 | **No block implemented a withdrawn claim** | Grep the reports for: a permanent-leak claim; "told the download finished"; the R5(iii) leg as a defect; "only `on_shutdown` terminates the child"; a correlation-id obligation; a truthiness guard on `download_results`; a `SIG_DFL` reset for SIGINT; blocking work in a signal handler. **All absent.** |
| 14 | **No plan-08 falsified claim carried forward** | The reports do **not** state that `limit_per_host` "reduces the achievable per-origin concurrency" or that it is "a behavioural change on the hot path". That claim is **false in direction** (§5.6 H2) and its repetition is a review failure. |
| 15 | **Identifier hygiene** | No unqualified `VAL-` id in any commit message, block report or task id. |
| 16 | **`B8`'s arithmetic** | Present in the commit body in prohibition-7 shape, with both deltas, and **matching the code**. |

### §8.3 Oracles for the documentation-only blocks

Two of the four blocks (`B11`, `B10`) change **no runtime behaviour and are invisible to every test**.
Their gate is therefore a **mechanical** one, not an assurance. Both oracles are specified here
exactly.

**`B11`'s oracle — superseded. `D10` adopted remedy (c) and the block's Planner replaced it with three
assertions. The authoritative oracle is in `§7 B11`'s `extra_context`, and the Implementor runs it and
the Validator re-runs it verbatim.**

**Why it was replaced, and why the replacement is stronger.** The enumeration below was written for the
remedy that would have had to touch every restating file, and its pass criterion was *"every hit is
classified"* — which is an **enumeration, not an assertion**: a reviewer cannot tell from the output
whether the enumeration is complete, so a missed site is invisible. Under `D10`'s remedy (c) **no enum
member changes**, so the failure mode it guarded against — a *partial sibling update* — **cannot occur**:
remedy (c) removes the sibling updates entirely. What remains to be checked is three things, and each is
a pass/fail:

| # | Assertion | Fails when |
|---|---|---|
| **(a)** | All **14** files that restate an enum declare member sets **identical** to the template's field reference | any file invents a member, or states a partial set |
| **(b)** | Every finding block containing `UNVERIFIED` is classified `pre-existing-unchanged` / `prospective-conforming`, **zero unclassified**, and the out-of-enum severity-cell count **does not increase** from exactly **1** | a block's severity cell is out-of-enum and is not the recorded legacy cell, or the out-of-enum count moves off 1 |
| **(c)** | `git diff --exit-code HEAD -- .kilo/rules .kilo/agents .ai/templates` is **empty** | any role file, rule file or the shadow template changed |

**Two scope traps the old enumeration walked straight into, recorded so they are not reintroduced.**

1. `Get-ChildItem -Recurse` over `.kilo\commands\audit` **includes** `.kilo\commands\audit\tests\*.md` —
   four files that are **not** phase handbooks and are **not** governed by `99-audit-validate.md`. Under the
   old `"CRITICAL"` pattern they contribute **8 hits, every one of them the English word "critical" used
   adverbially** (*"missing critical coverage"*, *"Critical path coverage"*, *"Critical problems: M"*), and
   under a member-set comparison they would read as a **partial set** — a false failure that pushes the
   Implementor into over-reach on files the block may not touch. `§7 B11`'s assertion (a) enumerates
   `.kilo\commands\audit\phases` **non-recursively** instead.
2. A severity-word grep across `.kilo\agents` produces false positives from three unrelated vocabularies:
   `researcher.md` carries *"honest confidence levels (HIGH/MEDIUM/LOW)"* and *"marked LOW confidence"*;
   `planner.md` and `validator.md` carry *"low coupling"* / *"high reliability"*; `auditor.md` carries
   *"blind spec compliance without critical thinking"* and an effort scale *"trivial / small / medium /
   large"*. `§7 B11`'s assertion (a) matches members **case-sensitively with letter/hyphen boundaries**,
   which excludes every one of those structurally rather than by scoping — and it permits a file to state
   **one** of the two enums (`validator.md` states only the `type` enum and contains no severity word at
   all) while forbidding any file from stating a **partial** set.

**Measured expectation, re-measured by the `B11` Planner at `HEAD = 8611a31`:** (a) 14 files, all `ok`,
`validator.md` the only empty severity set; (b) 21 finding reports, 266 severity cells, **1** out-of-enum
(`CON-002`'s `*none — not executed*`), 75 `prospective-conforming`, 1 `pre-existing-unchanged`, **0**
unclassified; (c) all three diffs empty. **If an assertion fails the block stops — the corpus is not
amended to make an assertion pass.**

Combined with §8.1's two-command read-only gate and D2, that is the whole of `B11`'s verification.

**`B10`'s oracle — the negative product gate plus a positive-content enumeration.**

*Negative (the load-bearing half — this block changes no product file):*

```powershell
git diff --exit-code HEAD -- src tests docs README.md .env.example .kilo     # MUST be empty
```

*Positive (the six required statements are **enumerable**, so "it reads well" is not the gate):*
the report must show, for each of the six points in `B10`'s ordered list, the line that satisfies it,
and the following negative greps must return **no match** in the new record:

| Negative grep | What it catches |
|---|---|
| `severity.*LOW` or `LOW.*severity` | the forbidden observed-severity substitute |
| `is safe` / `is broken` / `confirmed safe` / `refuted` | a verdict on the unexecuted production condition |
| `\.ai/problems/01-confirmed-code-defects\.md` | the stale path `phase04/VAL-410` describes — the record must name the corrected path **and** state the correction is not claimed |
| `:0*[0-9]+` after any cited module name | a **line number** in a record that must use semantic anchors only |

And the Validator reads the whole file. **The record is prose; the oracle proves it is the *right*
prose, and the read proves it is coherent.**

### §8.4 Per-finding verification trace — every remaining finding

| Finding | Block | Oracle | Notes |
|---|---|---|---|
| **`CON-009`** | **B8** | The new data-driven connector test across `max_concurrent_downloads ∈ {1, 4, 16}` × `ssl_verify ∈ {True, False}`, reading the **constructed** connector's public `.limit` and `.limit_per_host`; **plus** the aggregate-arithmetic test | Four-of-four identical values IS the defect. The test builds `Settings(...)` itself, is `@pytest.mark.asyncio`, and closes every connector. `tests/test_config.py` green **unchanged**. |
| **`CON-010`** | **B9** | **Fork-dependent, and the block report states which.** Documentation-only: a `tests/test_config.py` assertion on the field description's **semantic invariant** (not the whole string). Code remedy: a behavioural test, with `test_extract_with_ytdlp_timeout_raises_extraction_error` re-scoped **only because the behaviour changed**. | On the documentation-only branch `TestExtractionErrors` and all of `test_config.py` are green **unchanged**. |
| **`CON-002`** | **B10** | *(no test — prose)* §8.3's **negative** oracle: `git diff --exit-code HEAD` over `src tests docs README.md .env.example .kilo` is **empty**; plus §8.1's two-command read-only gate; plus the six-statement positive enumeration and four negative greps. | No code. No severity. Not deleted. No verdict. |
| **`phase04/VAL-404`** | **B11** | *(no test — prose)* §8.3's **mechanical enum-consistency enumeration** — every hit classified, template and all twelve handbooks in agreement — plus §8.1's two-command read-only gate. | No oracle exists for prose that governs the pipeline itself; this substitutes an enumerable one. |

**Findings carried by earlier phases, re-confirmed at the end gate rather than re-planned:**

| Finding | Disposition | End-gate check |
|---|---|---|
| `phase04/VAL-401`, `phase04/VAL-402`, `phase04/VAL-403` | **Discharged** by plan 08's landed single-commit groupings and the `B2`-before-`B5` order | §8.2 item 11 — the `B1`–`B7` regression net is green and **unedited**. |
| `phase04/VAL-405` … `phase04/VAL-409` | **Closed** by `d62671b`, `19143b1`, `8366964`, `e443448` | §8.2 items 3 and 6 — the audit paths and `.kilo/agents/*` are unchanged. |
| `phase04/VAL-410` | **Not claimed** (§1.4) | The `B10` record **states** it is not claimed and names its owner. |

**Findings whose verification is a negative assertion** (no test can see them — §8.3's oracles and the
Validator's read are the gate): `CON-002` (`B10`), `phase04/VAL-404` (`B11`), and every block's
byte-identical / `MUST NOT` / no-new-file criterion.

---

## §9 Open questions escalated to the Tech Lead

**These are scope, ownership and coordination decisions, not technical ones. This plan does not decide
any of them.** Each names the decision, the evidence, and what this plan does in the meantime.

### Q1 — Who owns `docs/11-guides/configuration.md`'s `download_timeout` row now?

**Evidence.** Plan 08's `B9` prohibition attributed the row to plan 07's `C12` (`B11` then `B15`
there). **Plan 07's `B11`/`B15` never landed**: there is no composed `ClientTimeout` helper anywhere
in `src/`, and `sock_read = 60` is still a literal at three sites. So `C12` has never touched the row
and the row is **unowned in practice**.
**Decision needed.** Does `B9` own the row now, or does it stay out and plan 07 resume? Related: if
`B9` writes the field description while the row still reads only *"Download timeout in seconds
(30-3600)"*, **the two disagree** — which of them is the doc of record?
**In the meantime.** `B9` does not touch the row and escalates. `B9`'s report states the row is
unchanged and that ownership is escalated, not decided.

### Q2 — Is the audit corpus's commitment (`0a8fa97`) authorised, and how is its new state guarded?

**Evidence.** `0a8fa97` committed the audit corpus and converted this plan's read-only gate from
**vacuous** to **live** — an outcome the engagement did not plan for and cannot take for granted.
Nothing now prevents a future `git rm --cached .ai/audit/**` from silently restoring the vacuity,
after which a block's `git diff --exit-code` would pass whether or not it changed anything.
**Decision needed.** Is the committed state permanent? And should the repository carry a guard — a
CI check, a packaging assertion, or at minimum a written rule — that the audit artifacts the pipeline
treats as authoritative remain tracked?
**In the meantime.** §8.1's gate is **two** commands and requires both, so every block re-proves the
gate rather than trusting it.

### Q3 — Is `.ai/templates/audit-findings.md` retired, aligned, or left?

**Evidence.** The repository carries **two** report templates. `.ai/audit/templates/audit-findings.md`
is the declared authority — referenced by all twelve phase handbooks, by the orchestrator, by the
validation task, by plans 05–08 and by all eleven validation artifacts. `.ai/templates/audit-findings.md`
is tracked, **referenced zero times**, has **no enum table**, uses a structurally different
`#### ID — [SEV]` block shape and different frontmatter, and shadows the authority it cannot
reconcile with. `B11` will change the authority, after which the two definitions are **definitively**
contradictory.
**Decision needed.** Retire it, align it, or leave it as recorded drift? Retiring a tracked file is an
ownership call this plan does not make.
**In the meantime.** `B11` edits only the authoritative template and **records in its report that the
second is untouched** (`B11` prohibition 6, §5.6 H4).

### Q4 — May phase 04 touch `.kilo/agents/*`?

**Evidence.** Plan 08 prohibited it on the ground that `phase04/VAL-409` is already fixed by
`e443448` and "there is nothing here". That ground **holds only if no fifth `type` label is added** —
and remedy (a), which the artifact offers **first** and which plan 08 deliberately did **not**
pre-select, explicitly adds *"a fifth type label with the same meaning"*. Under (a) the role files'
four-label lists become inconsistent with the format. But `.kilo/agents/auditor.md` and
`validator.md` govern the **whole agent estate**, not only the audit pipeline, so editing them from a
phase-04 audit-fixes block is a coordination decision.
**Decision needed.** If `B11`'s remedy resolves to (a), may this block update the role files'
vocabulary — or is that deferred to a dedicated pipeline plan?
**In the meantime.** The prohibition **stands as written** until this is answered, and any role-file
touch before then is a gate failure (§8.2 item 6).

### Q5 — Should the segment-path exception-catch asymmetry be filed as a finding?

**Evidence.** `segment_downloader.py`'s parallel download path catches `aiohttp.ClientError` **only**;
the throttle path catches `(aiohttp.ClientError, TimeoutError)` with an `INT-006` comment that names
the reason exactly. A request queued past the `ClientTimeout.connect` budget raises `TimeoutError`,
**not** a `ClientError`. The exposure is **live today** for `max_concurrent_downloads ∈ 11…16`, where
the constant `limit = 10` admits fewer connections than the semaphore admits tasks — and after `B2`
landed, such a timeout now fails the **whole video**. `B8`'s remedy **removes** the exposure but does
not fix the asymmetry.
**Decision needed.** File it — it is a real finding, but it is **not** phase 04's: phase 03 owns
transport. Or carry it as a note in `B8`'s report?
**In the meantime.** `B8` records it prominently and **widens neither `except` clause** (`B8`
prohibition 6), because that would be an unrequested behaviour change on the same hot path.

### Q6 — Should plans 05–08 be committed alongside this plan?

**Evidence.** `.ai/plans/08-concurrency-cancellation-audit-fixes.md` and plans `05`–`07` are
**untracked**, while the audit corpus they derive from is now tracked and committed. The engagement's
progress record is therefore half-committed. `tmp/` is also untracked and **not gitignored**, and it
holds `b8_research.md` — the deliverable §6.1 rules sufficient for `B8`.
**Decision needed.** Commit plans 05–09 and the research deliverables, or keep them local? If
`tmp/` stays untracked, the `B8` evidence chain depends on a path that can vanish at any cleanup —
which is why `B8`'s acceptance criteria require the load-bearing claims **inline** in the report and
commit body regardless of the answer.
**In the meantime.** `B8` carries its evidence inline; `B10` is the only block this plan authorises
writing under `.ai/plans/**`, and this file is that block's output.

### Q7 — Is `docs/00-overview/doc-maintenance-rules.md` this project's rules?

**Evidence.** The file exists at exactly the path the engagement template names, is tracked, and is a
**copy of another project's rules**: it prescribes `01-auth/`, `02-dashboards/`, `core/`, `app.py`
and `schema-core.md`, **none of which exist in this repository**. In force order it nominally
outranks `.kilo/rules/project.md` rule 14 (*"Keep documentation updated continuously"*), and
`.ai/context/python-code-standards.md` does not apply to `docs/` at all (its glob is `**/*.{py}`).
**Decision needed.** Replace it with rules that match this repository, or retire it in favour of
`.kilo/rules/project.md` rule 14 — before or after this engagement? It is a documentation-correctness
question, not a technical one, and it affects every documentation write `B8` and `B9` make.
**In the meantime.** Blocks follow **rule 14** and the repository's actual layout; the mismatch is
recorded at §5.7 and the mismatch is not treated as licence to create new doc structure.

---

## §10 Tech Lead decisions on the escalated questions

**Binding on every block, every block report, every commit and every test.** These resolve §9 Q1–Q7.
They are ownership and scope rulings, not technical findings; none reopens a `CON-` or `phase04/VAL-`
finding, and none licenses work outside the four blocks of §1.2.

### D1 (Q1) — The configuration guide's `download_timeout` row stays out of `B9`. The prohibition STANDS.

Plan 07's `C12` never ran, so the row is unowned in practice. **An absent owner is not a licence to take
another plan's surface.** `B9` **does not edit** `docs/11-guides/configuration.md`'s `download_timeout`
table row, and does not edit its prose section for that setting.

- **Doc of record:** `config.py`'s `Settings.download_timeout` field description is the authoritative
  statement of **what the setting bounds**. The guide's row is an **operator-facing summary**, and
  *"Download timeout in seconds (30-3600)"* remains **true** — it is **incomplete, not contradictory**.
  A summary that is true but narrower than the code of record is not a defect and is not repaired here.
- **Coordination obligation, mandatory in `B9`'s report:** name plan 07's `C12`, name the row, and name
  the **trigger** — when plan 07's `B11`/`B15` land and a composed `ClientTimeout` helper appears, that
  work must reconcile the guide's row with the field description this block writes.
- **If `B9` judges the row to have become actively misleading** (not merely incomplete), it **escalates
  back to the Tech Lead and leaves the row untouched**. Editing it is a gate failure.

### D2 (Q2) — `0a8fa97` is a given. §8.1's two-command gate is binding on every block. No new guard is added.

The corpus commitment is **not reverted, re-committed or second-guessed** by this engagement, and no
block stages a path under `.ai/audit/` except `B10`'s own new record file. **§8.1's gate is two commands
and both must pass**: `git diff --exit-code HEAD -- <read-only paths>` **and**
`git ls-files --error-unmatch -- <read-only paths>`. A green `git diff` with a red `ls-files` is a
**gate failure**, never a pass.

No CI check, packaging assertion or new repository file is added to guard the tracked state — that would
breach the plan's no-new-file rule for an advisory engagement, and the correct home for it is a pipeline
plan, not this one. **The guard for this engagement is this section**, and the escalated follow-up is
recorded in §11.

### D3 (Q3) — `.ai/templates/audit-findings.md` is left exactly as it is. Recorded as drift, not fixed.

`B11` edits **only** the authoritative `.ai/audit/templates/audit-findings.md` and **records in its
report** that the second template is untouched and now definitively contradicts the authority. **No block
deletes, aligns or edits it** — retiring a tracked file that a validation artifact still cites is an
ownership call outside this engagement. Escalated in §11.

### D4 (Q4) — `.kilo/agents/*` is in scope **conditionally and only for label lists**.

- If `B11`'s selected remedy **adds a fifth `type` label**, then — and only then — the `type` label lists
  in `.kilo/agents/auditor.md` and `.kilo/agents/validator.md` (both blocks each file lists them) are
  **in scope for that same change set**, because leaving them at four labels would reintroduce exactly
  the defect `phase04/VAL-409` was filed for and fixed by `e443448`.
- If the selected remedy **does not** add a `type` label, plan 08's prohibition on `.kilo/agents/*`
  **stands absolutely**.
- **`.kilo/rules/*` is never in scope for any block.** If either remedy would require it, the block stops
  and escalates.
- Any role-file edit is **additive to a list only** — no rewording, no restructuring, no other file in
  `.kilo/agents/` touched.

### D5 (Q5) — The segment-path exception-catch asymmetry is **not filed** by this engagement.

It is a real observation and it is **not phase 04's** — phase 03 owns transport. `B8` records it
prominently in its block report, states that `limit = N` **removes** its exposure, and **widens neither
`except` clause**. The follow-up is recorded in §11 for the phase that owns it. **No block creates a new
finding, a new ID, or a new audit artifact.**

### D6 (Q6) — `tmp/` stays local and is never committed. Plans 05–08 stay untracked and out of scope.

`tmp/` is **working material, not a deliverable**; it is not committed and not gitignored by this
engagement. Therefore **§6.1's inline-evidence obligation is absolute**: `B8`'s block report and commit
body carry the load-bearing claims and the verified arithmetic inline. **A commit that cites a `tmp/` path
as its evidence is a gate failure.**

Plans `05`–`08` are **not** committed by any block — they are other engagements' artifacts. **Plan 09
itself is committed once, by the documentation phase**, and `B10`'s record is committed by `B10`'s
Implementor as that block's own work item.

### D7 (Q7) — The documentation rules divergence is out of scope. Rule 14 governs.

`docs/00-overview/doc-maintenance-rules.md` is **another project's rules** and this repository does not
satisfy it. **No block and no documentation phase rewrites it.** For this engagement the governing order
is: `.kilo/rules/project.md` **rule 14**, then this repository's actual `docs/` layout, then the subset of
`doc-maintenance-rules.md` this repository can actually satisfy — frontmatter on every **touched** doc,
a `## Purpose` section, and **no new doc page**. The divergence is escalated in §11; it is **not licence**
to create doc structure, and not a reason to touch unrelated docs.

---

### D8 (new, from the `B9` Researcher pass) — the documentation must not depend on a CPython bug.

The Researcher **measured** that on this project's pinned interpreter (CPython **3.12.1**, Windows,
`ProactorEventLoop`) `asyncio.constants.THREAD_JOIN_TIMEOUT = 300` is **not applied**: in 3.12.1
`BaseEventLoop.shutdown_default_executor` does `await future` (unbounded) **before** `thread.join(timeout)`,
so the abandoned extraction thread is joined for its **full remaining lifetime** — measured, unbounded, no
`RuntimeWarning`. This is CPython **gh-111358**, fixed upstream by PR 115622 and backported to 3.12 as
115641, merged 2024-02-18 — **after** the pin. The Researcher also measured that a **custom executor only
relocates** the stall into `concurrent.futures.thread._python_exit` at interpreter exit (total process time
unchanged), so options (b) and (c) buy nothing.

**Binding ruling on what `B9` may write:**

1. **`config.py`'s `download_timeout` description states the mechanism, not a number, and states that this
   setting is NOT the bound on the exit path.** It must be **true on both** 3.12.1 (join timeout not
   applied) and 3.12.2+ (join timeout applied, 300 s). Writing "300 s" would be false on the pinned
   interpreter; writing "unbounded" becomes false on the next patch bump. **Neither is acceptable.** The
   wording is the `B9` Planner's, subject to this constraint.
2. **The measured platform-specific truth lives in `B9`'s block report and commit body, not in the
   operator-facing description** — including gh-111358 by number, and the explicit statement that the
   setting is not the bound there.
3. **`CON-010`'s recommendation has two clauses — "state the exit-path bound where the timeout is
   configured" and "lower it for this call site".** Option (a) closes the **first** and not the second.
   `B9`'s report must say so plainly; the residual is **accepted**, and the lowering half is recorded as
   **not taken**. It may not claim the recommendation was fully met.
4. **Raising the interpreter floor to ≥3.12.2 is OUT OF SCOPE for this block.** It is a real operational
   hazard and a product decision, escalated in §11. `B9` records it and does not act on it.
5. **The description must not generalise beyond the measured platform** (§5.8 item 5). No claim about a
   real origin's behaviour, and no claim about other platforms.

### D9 (new) — `B9` selects option (a), documentation only, on the Researcher's evidence.

`§3 B9` deliberately left the fork open; the Researcher resolved it and the ruling is now binding:

- **(a) documentation only — SELECTED.** The code options are either **ineffective** ((b), (c): measured
  relocation, not removal; (d1) `to_thread`: measured identical) or **disproportionate** ((d2) subprocess,
  (d3) `ProcessPoolExecutor`, (d4) daemon thread) or **untestable** — **nothing in `tests/` observes this
  mechanism**, and the existing `test_extract_with_ytdlp_timeout_raises_extraction_error` provably cannot
  (it mocks `run_in_executor` away, so no thread is ever created).
- The change is: the `download_timeout` field description (per D8), the `_extract_with_ytdlp` **docstring**,
  and the **`INT-003` comment** above the executor dispatch — corrected to state the **loop-vs-process**
  distinction and the absence of a bound on the process side.
- The `ExtractionError` message and the `ytdlp_extraction_timeout` record are **preserved unchanged**.

---

### D10 (new, from the `B11` Researcher pass) — remedy (c) is adopted, and the finding is re-characterised.

The Researcher's measured evidence inverts `phase04/VAL-404`'s premise, and the ruling follows the
evidence:

- **The format is not the defective side; phase 04's handbook is.** Eleven of the twelve handbooks and
  `99-audit-validate.md` `## 8` all forbid *"an **observed** severity"*. **Only phase 04 forbids
  *"severity"* at all**, in four places — and in doing so it **overrides its own `## 9` `LOW` row**, which
  already defines the band: *"A shape, naming or structure deviation with no runtime consequence."*
  `CON-002` is exactly that. This mirrors the pipeline's own standing adjudication pattern
  (`phase04/VAL-409`: *"The format is the authority; the role files are the defective side."*).
- **The corpus already answers the question, thirty times.** 30 of the 31 `UNVERIFIED`-carrying findings
  carry a severity band **and** the marker; phase 08's `OUT-010`/`OUT-011`/`OUT-012` are `LOW` + marker,
  and the validator wrote *"LOW, `UNVERIFIED` through the binary, **correctly marked**."* Phase 04's own
  report already writes the fifth Summary row `| none (`UNVERIFIED`, not executed) | 1 |`.
- **SARIF 2.1.0 §3.27.9–§3.27.10** puts "unable to prove there is none" on a *different axis*
  (`kind = "open"`) and then makes `level` default to `none` whenever `kind ≠ "fail"` — so the industry
  answer is *"not executed is not a severity"* **and** *"a finding with no severity must still be
  representable."* `Verification` + structural composition satisfies both.
- **Blast radius collapses** from ~50 sites / 15 files to ~9 sites / **3 files**, retiring the plan's own
  largest process risk (a partial sibling update) by removing the sibling updates entirely.

**Adopted remedy (c):** no enum change. Add a mandatory **`Verification`** field to the authoritative
`.ai/audit/templates/audit-findings.md` as the machine-checkable carrier of `UNVERIFIED`; state there that
when a runtime consequence was not observed the severity band is composed from the **structural fact**
under the owning phase's own severity table; and reconcile phase 04's four "no severity" prohibitions to
that rule. **Prospective only.**

**Binding on `B11`:**

1. **The re-characterisation is accepted and must be stated.** `VAL-404` is filed `SPEC-DEVIATION` against
   the template; the fix is mostly in phase 04's handbook. `B11`'s report **must say so explicitly**, or a
   reviewer will read the edit set as narrower than the finding. The template is **not** abandoned — it
   gains the field and the composition rule.
2. **Reach is exactly three files**: the authoritative template, `04-audit-concurrency-cancellation.md`, and
   `99-audit-validate.md`. **The eleven sibling handbooks, `audit-multi-phase.md`, `.kilo/agents/*` and
   `.ai/templates/audit-findings.md` are not touched** — the siblings' mandate is *already* in the
   satisfied form. **No fifth `type` label is added, so D4's condition is not met and plan 08's
   prohibition on `.kilo/agents/*` stands absolutely.**
3. **The optional clarity edits (the phase-04 `## 9` closing paragraph and `## 12` bullet, and
   `99-audit-validate.md` `## 8`'s closing paragraph) are NOT taken.** Rule 5; the template is the declared
   authority, so the siblings are disambiguated by derivation. Take them only if the `B11` Planner judges a
   residual ambiguity **material**, and record the judgement. Default: **not taken** — three files.
4. **Wording hazard, binding (the one genuine risk of this remedy).** The template's `severity` row **must
   not** be written as *"an unexecuted finding is `LOW`"* — that would become a ranking rule, reinterpret
   phase 04's own `LOW` row and make `LOW` mean two things. It must be written as *"the band is composed
   from the structural fact under the owning phase's own severity table"*, and must **cite phase 04's own
   `LOW` row as the precedent** rather than assert a mapping.
5. **The rule is prospective.** It **must** state that a severity already written is not re-read under it.
   The corpus keeps **exactly one** historical non-conforming severity cell — `CON-002`'s
   `*none — not executed*` — permanently. That is an **accepted, recorded state**, not a residual defect,
   and **prohibition 4 forbids correcting it**.
6. **`99-audit-validate.md` `## 8`'s *"The four severity words are not redefined here, and this file adds
   no fifth"* stays true and is not touched.** Its `## 2` clause — *"The definition of the severity, type
   and classification vocabularies → the report template"* — is what makes this remedy lawful without
   amending `## 8` at all. `B11`'s report **must** state that the prohibition survives and why.
7. **`99-audit-validate.md`'s `## Validation Summary` action table is NOT a severity surface** — it is an
   **action** tally (Validated / Reclassified / Merged / Rejected / `VAL-`). Plan 09 `§3 B11`'s reach list
   naming it is a **defect in this plan**, recorded and corrected; the block must not edit it.
8. **The task specification's anchor list must be widened** to include the template's **skeleton field
   table**, not only its `Template Field Reference` and `## Summary` sections. Without this the new field
   would be written to an unlisted anchor.
9. **`§3 B11`'s `UNVERIFIED` counts are corrected** before any block cites them: measured **58** occurrences
   in `.kilo/` (12 files) and **141** in `.ai/` (17 files: 110 under `.ai/audit/`, 31 under `.ai/plans/`),
   **205 total**. Plan 09's figures (64 / 151 / 131 / 20) do not reproduce. The **qualitative claim — all
   twelve handbooks, a corpus-wide convention — holds.**
10. **`CON-002`'s out-of-enum cell count:** of 267 `| **Severity** |` cells in `.ai/audit/`, **exactly one**
    is truly out-of-enum (`CON-002`); the other 18 free-text cells are a legal enum word plus a
    parenthetical. The audit's *"~18 out-of-enum"* is really *"18 free-text"*. Corrected here so the block
    report states it accurately.
11. **The oracle must be three assertions, not one enumeration**, per the Researcher's improved gate:
    **(a)** all 14 files that restate the enum carry **identical member sets** to the template's field
    reference; **(b)** every finding block containing `UNVERIFIED` is classified `pre-existing-unchanged`
    or `prospective-conforming` with **zero unclassified**, and the out-of-enum severity-cell count **does
    not increase** (currently exactly 1); **(c)** boundary greps proving `.kilo/rules/`, `.kilo/agents/*`
    and `.ai/templates/` are untouched.
    **Two scope traps, binding:** a recursive sweep of `.kilo/commands/audit` **includes**
    `.kilo/commands/audit/tests/*.md` (4 files, 8 enum hits) which are **not** phase handbooks and are not
    governed by `99-audit-validate.md` — the oracle **must exclude that directory**, or the Implementor
    will be pushed into over-reach; and a severity-word grep across `.kilo/agents` produces false positives
    from `researcher.md`'s `HIGH/MEDIUM/LOW` **confidence** levels — scope it to `auditor.md`/`validator.md`.

---

## §11 Escalated to the coordinator — outside this engagement

| # | Item | Owner / trigger |
|---|---|---|
| E7 | `.kilo/commands/audit/tests/*.md` is a **second, non-conforming severity/type vocabulary family** — 4 files, 8 enum hits; `audit-bad-tests.md` lists only 2 of the 4 type labels and `audit-tests-full.md` carries its own `HIGH/MEDIUM/LOW` evidence column. It is a command family outside `phases/` and is **not** governed by `99-audit-validate.md`. Measured; not filed by `phase04/VAL-404`; **untouched** by `B11` because remedy (c) creates no new inconsistency there. | Pipeline/document ownership. The natural trigger is the same documentation plan that resolves **E2**. |

| # | Item | Owner / trigger |
|---|---|---|
| E6 | **The pinned interpreter (CPython 3.12.1) carries CPython gh-111358**: `asyncio`'s `shutdown_default_executor` timeout is not applied, so an abandoned off-loop thread is joined for its **full remaining lifetime, unbounded**. Fixed upstream by PR 115622 / 3.12 backport 115641 (merged 2024-02-18). Raising the floor to **≥3.12.2** turns the documented cap real and is the only change that bounds the exit-path wait. Out of scope for `B9` per D8 item 4. | Coordinator — a dependency/interpreter decision. `.python-version` and `pyproject.toml`'s `requires-python`. |

Recorded so nothing is silently dropped. **No block acts on any of these.**

| # | Item | Owner / trigger |
|---|---|---|
| E1 | The audit corpus's tracked state has no mechanical guard against `git rm --cached .ai/audit/**` silently restoring the vacuous read-only gate (D2). | A pipeline plan; a CI or packaging check. |
| E2 | `.ai/templates/audit-findings.md` is a tracked, zero-referenced, structurally incompatible shadow of the authoritative template; after `B11` the two are definitively contradictory (D3). | Pipeline/document ownership. Retire or align. |
| E3 | The segment-path exception-catch asymmetry (`aiohttp.ClientError` only on the parallel path vs `(aiohttp.ClientError, TimeoutError)` on the throttle path), live today for `max_concurrent_downloads ∈ 11…16` (D5). | **Phase 03** — transport. |
| E4 | `docs/00-overview/doc-maintenance-rules.md` prescribes directories and files that do not exist in this repository (D7). | Documentation ownership, before the next documentation write. |
| E5 | `.ai/plans/` holds six tracked **deletions** of `Mko-AINotify` plan files (`00_overview.md`, `01`–`04`, `VALIDATION_REPORT.md`, `error_ref.md`) that this engagement did not make, plus a modified `.ai/problems/PROBLEM.md` carrying an unrelated statement. **No block stages any of them.** | Coordinator — a history/ownership decision. |

---

## §12 Disclosures — unrelated working-tree changes made by phase-04 blocks

Recorded so nothing is silently absorbed. **No block may revert another block's work, and these are
disclosed rather than undone** — reversing them is itself an unrequested working-tree change, and the
coordinator owns the decision (§11 E5).

| # | Disclosure | Made by | Assessment |
|---|---|---|---|
| X1 | **`.ai/audit/03-network-resilience/findings.md` was returned to the working tree.** The pre-existing uncommitted deletion recorded in `§2.4` no longer appears in `git status`. The file on disk is **byte-identical to `HEAD`** — no content was authored or changed by any phase-04 block, and `git diff --name-status HEAD -- .ai/audit` is **empty**. It was restored to satisfy `B11`'s own oracle (c), which asserts that `.ai/audit` as a whole differs **only** in the template. | `B11` (`3c25dda`) | **No product, test, documentation or finding content was affected**, and nothing under `.ai/audit/**/findings.md` was edited. The side effect is that an unrelated uncommitted deletion is no longer **visible** in `git status`. It remains in `§11 E5` as a coordinator decision. **No block may recreate, re-delete or "fix" this path again.** |

---

*Plan 09 ends. Four blocks: `B8` (`CON-009`), `B9` (`CON-010`), `B11` (`phase04/VAL-404`), `B10`
(`CON-002`). The seven questions of §9 are decided in §10; five follow-ups are escalated in §11.*
 
