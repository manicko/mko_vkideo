# Phase 04 Audit Findings — Concurrency and Cancellation (validated)

**Executor:** audit-executor · **Validated by:** validator
**Template:** `.kilo/commands/audit/phases/04-audit-concurrency-cancellation.md`
**Validator task:** `.kilo/commands/audit/phases/99-audit-validate.md`
**Source report (read-only):** `.ai/audit/04-concurrency-cancellation/findings.md`
**Status:** complete · **Validated:** yes

> **Deviation from the report format, stated once here.** The template
> (`.ai/audit/templates/audit-findings.md:19-33`) defines a finding block that runs from the
> heading straight into a fixed field table; none of its nine mandatory fields carries a
> validation decision. The `Validation Note` this phase is required to attach to **every**
> decided finding therefore has no slot in the format. It is written directly below each
> `### {ID}:` heading, above the field table. The absence of the slot is already filed
> (`VAL-111` in `01-entry-architecture-validated-findings.md`, `VAL-001` in
> `02-config-validated-findings.md`, `VAL-006` in `03-network-resilience-validated-findings.md`);
> it is **not** re-filed here. A second format gap, which the sibling runs did not hit, is
> filed as `VAL-404`: the template's `severity` enum has no member for the not-executed
> encoding that two pipeline documents require.

**Identifier numbering.** `99-audit-validate.md` `## 10` requires that this phase adopt no
identifier already present in the tree. `VAL-` is already in use in this store — `VAL-001`…
`VAL-006` (phase 02), `VAL-001`…`VAL-007` (phase 03), `VAL-101`…`VAL-112` (phase 01) — and the
collision itself is already filed as `VAL-112` in the phase-01 store. This artifact therefore
numbers from **`VAL-401`**, following the offset precedent `VAL-112` established. The earlier
blocks are left exactly as those runs wrote them.

**Scope note.** Findings use concrete `file:line` references for traceability; every check was
reasoned against the phase's role vocabulary (the stop state and its handler · the line-reading
helper and the child processes it drains · the video-level concurrency primitive and the batch
task factory · the per-part transfer layer and its completion helper · the browser handle
lifecycle · the transport pool). Conclusions about severity are composed from this run's own
verification, not inherited from the source report.

---

## Baseline observed by this run (re-derived, not cited)

```
$ uv run pytest tests/test_batch_downloader.py tests/test_segment_downloader.py \
      tests/test_downloader_throttle.py tests/test_downloader.py tests/test_ffmpeg_utils.py \
      tests/test_browser_infrastructure.py tests/test_hls_downloader.py -q
244 passed, 2 skipped in 20.45s                                   EXIT=0

$ uv run ruff check src/vkdownloader/services src/vkdownloader/infrastructure src/vkdownloader/cli.py
All checks passed!                                                EXIT=0

$ uv run ruff format --check src/vkdownloader/services src/vkdownloader/infrastructure src/vkdownloader/cli.py
17 files already formatted                                        EXIT=0

$ uv run mypy src/vkdownloader/services src/vkdownloader/infrastructure src/vkdownloader/cli.py
Success: no issues found in 17 source files                       EXIT=0
```

Environment re-derived: CPython 3.12.1; loop class `asyncio.windows_events.ProactorEventLoop`;
`asyncio.constants.THREAD_JOIN_TIMEOUT = 300`.

Probes written for this run, all under the gitignored `.temp/val04/`. None of them is product
code and none modifies it.

---

## Checkpoint 1 — R1 Copy Source Findings

- **Stage:** R1 Copy Source Findings
- **Corpus map:** `.ai/audit/` holds findings files for phases `01`, `02`, `03`, `04`; handbooks
  exist for `01`–`11` plus `99`. Phases `05`–`11` have a handbook and no findings file — they
  have not been run, which is not a gap. No findings file without a handbook; no handbook
  without a findings file among the phases that have run.
- **Identifier map:** prefixes in the store — `ENT-` (01), `CFG-` (02), `NET-` (03), `CON-` (04),
  `VAL-` (99). No prefix is unclaimed and no two live prefixes collide. `CON-001`…`CON-010` occur
  only in `.ai/audit/04-concurrency-cancellation/findings.md`.
- **Decision-record map:** the format's finding block has no decision field (stated above); the
  deviation is already filed elsewhere in the store.
- **Findings in scope:** 10 (`CON-001` … `CON-010`), plus 4 documented skips and 10 cross-references.
- **Evidence anchor:** this file is self-contained; every finding below carries the code excerpt
  or probe output it rests on.
- **Blockers:** none.
- **Checkpoint status:** closed

---
## Findings

### CON-001: A stop is never observed by a blocked read of a child's output, a second stop changes nothing, and the runtime's interrupt handler is left displaced

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived end to end against the shipped objects; nothing in the claim is
>   inferred. **Severity re-derived from this run's own evidence: CRITICAL — confirmed.**
>   The owning phase's binding rule W-4 (`04-audit-concurrency-cancellation.md:348`) permits
>   `CRITICAL` only when all three legs are observed; all three were re-executed here.
>   *Leg R1 (primitive) — executed, negative:* `ConcurrencyTracker`/`_TrackedSemaphore` under
>   four ceilings, 8/1/4/6 inner claims all completed, every permit released, zero waiters left,
>   measured peak equal to the ceiling — the shared primitive is not the cause.
>   *Leg R4 (handler) — executed, positive:* before install
>   `functools.partial(<bound method Runner._on_sigint of asyncio.runners.Runner ...>)`; after
>   install `setup_signal_handlers.<locals>.<lambda>`; after `cleanup_signal_handlers()` still
>   the lambda for both SIGINT and SIGTERM (restored to pre-install: `False`); and **after
>   `asyncio.run` returns, SIGINT is still the lambda** — `Runner.run()` restores
>   `default_int_handler` only when that is still installed, which it is not. One
>   `shutdown_signal_received` line was emitted across two fires, which is the idempotence guard
>   observed directly rather than inferred from `signal_handlers.py:31-33`.
>   *Leg R5 (blocked read) — executed, positive:* against the real `iter_process_lines` and a
>   real child that writes one line and then falls silent: `reader returned within 3s of the
>   stop: False`, `shutdown hook invoked: False`, `child returncode: None`,
>   `child still alive: True`, and the reader returned only after the child was killed. Repeated
>   at the production call shape (`process.wait()` raced against the drain through
>   `_await_first_and_cancel_others`): `AWAIT COMPLETED WITHIN 5s OF THE STOP : False`,
>   `on_shutdown fired: False`, `child still running: True`. No bound exists on either route —
>   `_download_with_ytdlp` imposes none by design (`ytdlp_downloader.py:579-582`) and the ffmpeg
>   HLS path applies none.
>   Two corrections to the source text, neither of which changes the conclusion. (i) "The only
>   thing that terminates a child is the `on_shutdown` callback" is over-stated:
>   `cancel_subprocess` is also reached at `downloader.py:376`, `downloader.py:404` and
>   `ytdlp_downloader.py:718`. All three sit downstream of `_await_first_and_cancel_others`
>   returning (`ytdlp_downloader.py:97-100`, `FIRST_COMPLETED`, no timeout, no stop check), which
>   is precisely what does not happen — so the conclusion stands and only the phrasing needs
>   narrowing. (ii) The R5(iii) leg (`second claim done while the stop is set : False`) supports
>   no claim in this finding and is not evidence of a defect: `_download_segment_concurrent`
>   checks the stop state immediately after acquiring (`segment_downloader.py:680`) and the wait
>   is bounded by each in-flight transfer's own `download_timeout`
>   (`downloader_throttle.py:200-205`), so it is ordinary blocking, not a standstill.
> - **See also:** `VAL-403` — the recommended escalation re-activates `CON-008`'s
>   misclassification path; `ENT-004` and `ENT-012` (phase `01`) own the registration *placement*
>   and the correlation-id shadowing, and are cross-referenced by the source report rather than
>   re-filed here.

| Field | Value |
|-------|-------|
| **ID** | CON-001 |
| **Severity** | CRITICAL |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/signal_handlers.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** The shipped line-reading helper consults the stop state only
*between* lines (`ffmpeg_utils.py:56`), never while a read is in flight
(`ffmpeg_utils.py:60`). The only thing that terminates a child is the
`on_shutdown` callback, which that same helper invokes from inside the *next*
loop iteration (`ffmpeg_utils.py:57-58`) — i.e. only after the blocked read has
returned on its own. So the kill is reachable only once the child produces more
output. Both the yt-dlp drain (`ytdlp_downloader.py:650-651`, `:664-665`) and
the ffmpeg drain (`downloader.py:328-333`, `:349-351`) pass exactly that
callback as their kill path.

Compounding it, the handler is idempotent by construction
(`signal_handlers.py:31-33`: `if not shutdown_event.is_set()`), so a second
Ctrl-C is a no-op, and `cleanup_signal_handlers()` runs inside a live loop, so
it takes the `loop.remove_signal_handler` branch (`signal_handlers.py:68-74`)
whose `NotImplementedError` is swallowed at `signal_handlers.py:72`. The
process-level branch that would restore the previous handler
(`signal_handlers.py:76-82`) is unreachable from the shipped call sites, both of
which run cleanup inside `asyncio.run`.

**Exact consequence:** during a yt-dlp or ffmpeg transfer, a Ctrl-C sets the
shutdown state, the reader stays blocked in `readline()`, `on_shutdown` never
fires, `cancel_subprocess` is never called, and the child process is never
terminated. The item's await never returns. A second Ctrl-C changes nothing (the
handler is guarded, and the runtime's own handler that would raise
`KeyboardInterrupt` was displaced at install and is not restored). No timeout
bounds it: `_download_with_ytdlp` imposes none by design
(`ytdlp_downloader.py:579-582`). The process reaches a state it cannot leave by
any in-process means.**Evidence (this run's own re-execution; the three legs, verbatim).**

Leg R1 — executed, **negative**. `.temp/val04/p7_primitive.py`:
```
  ceiling= 4 units= 4 parts= 2 -> completed=  8 peak= 4 permits_free= 4 waiters=0
  ceiling= 1 units= 1 parts= 1 -> completed=  1 peak= 1 permits_free= 1 waiters=0
  ceiling= 4 units= 1 parts= 4 -> completed=  4 peak= 1 permits_free= 4 waiters=0
  ceiling=16 units= 3 parts= 2 -> completed=  6 peak= 3 permits_free=16 waiters=0
no standstill in any trial; the primitive releases every permit it takes
```

Leg R4 — executed, **positive**. `.temp/val04/p2_signal.py`:
```
loop class: asyncio.windows_events
SIGINT handler BEFORE install: functools.partial(<bound method Runner._on_sigint of
  <asyncio.runners.Runner object at ...> main_task=<Task pending name='Task-1' ...>>)
SIGTERM handler BEFORE install: <Handlers.SIG_DFL: 0>
runtime own handler present  : True
SIGINT handler AFTER install : setup_signal_handlers.<locals>.<lambda>
SIGTERM handler AFTER install: setup_signal_handlers.<locals>.<lambda>
displaced the runtime own    : True
[info] shutdown_signal_received              <-- exactly one line across BOTH fires
after FIRST fire  is_set: True
after SECOND fire is_set: True
SIGINT handler AFTER cleanup : setup_signal_handlers.<locals>.<lambda>
restored to pre-install?     : False
SIGTERM handler AFTER cleanup: setup_signal_handlers.<locals>.<lambda>
restored to pre-install?     : False
after asyncio.run, SIGINT handler: setup_signal_handlers.<locals>.<lambda>
```

Leg R5(i) — blocked read of a silent child's output, through the shipped helper.
`.temp/val04/p1_blocked_read.py`:
```
loop class: asyncio.windows_events.ProactorEventLoop
lines consumed before the stop: 1 [b'line one\r\r\n']
child returncode before the stop: None
reader returned within 3s of the stop: False
shutdown hook invoked: False
child returncode 3s after the stop: None
child still alive: True
reader returned only after the child was killed: True
```

Leg R5(i) repeated at the production call shape — `process.wait()` raced against a drain that
uses `iter_process_lines`, with `on_shutdown = cancel_subprocess`, exactly as
`ytdlp_downloader.py:639-678` builds it. `.temp/val04/p6_con001_e2e.py`:
```
AWAIT COMPLETED WITHIN 5s OF THE STOP : False
lines drained                          : 1
on_shutdown fired                      : False
child returncode                       : None
child still running                    : True
=> the item's await never returns; cancel_subprocess is never called
```

**Baseline in which this was observed:** the four commands at the head of this artifact, all
exit 0. Coverage declaration, re-derived by search over `tests/` excluding worktree
directories: `_TrackedSemaphore` and `_await_and_cancel`, `_create_segment_download_tasks`,
`_process_downloaded_segments`, `_semaphore_context` — 0 references each; `iter_process_lines` —
7 references, none of which can observe the blocked-read case because
`tests/test_hls_downloader.py:2655` and `:2686` replace `signal.signal` wholesale.

**Recommendation:** make the stop observable *while* a read is in flight — race
the read against the shutdown event so `on_shutdown` runs while the reader is
blocked, not after it returns. Make the second interrupt escalate (forward to
the displaced handler or force-kill the child), and restore the previously
installed process-level handler in `cleanup_signal_handlers` on the branch that
actually runs on Windows. The correlation-id shadowing at `downloader.py:663-664`
is cross-referenced to ENT-012 and the registration *placement* to ENT-004;
neither is filed here. *Accepted as written; see `VAL-403` for the interaction
this escalation creates with `CON-008`.*

---
### CON-002: The shipped condition that reaches the per-part transfer from inside the outer claim is not executed — `UNVERIFIED`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Kept, and the severity cell left exactly as the owning phase wrote it. Three
>   things were checked before deciding not to remove it.
>   *(a) May it be deleted? No.* The owning phase's binding rule W-4
>   (`04-audit-concurrency-cancellation.md:348`) requires the claim subject to be filed as
>   **exactly two** findings and states that "The two are never merged and never omitted;
>   under `problems-only`, omitting either reads as 'no finding'." Deleting this one would
>   itself be a defect of this validation, not a correction of the report.
>   *(b) Is its structural fact true? Yes, re-derived from source rather than from the text.*
>   `perform_download` takes the per-video permit exactly once, around the whole ladder
>   (`downloader.py:500-502`, with the rationale in the comment at `:496-499`); the segment
>   layer builds its own `asyncio.Semaphore(settings.max_concurrent_downloads)`
>   (`segment_downloader.py:822`); and the outer object is carried across only as the boolean
>   `is_bounded_batch` (`:823`, consumed at `:713`). The nested-claim shape D-01 describes does
>   not reproduce. The retired register's own **Fix**, Option A
>   (`.ai/plans/done/01-confirmed-code-defects_DONE.md:61`), is what the code implements, and
>   `config.py:93-98` documents the per-layer sizing in the setting's field description.
>   *(c) Is it a well-formed finding? No — and this phase cannot make it one.* The
>   `Severity` cell reads `*none — not executed*`, which is not a member of the format's
>   `CRITICAL | HIGH | MEDIUM | LOW` (`.ai/audit/templates/audit-findings.md:69`); and no label
>   in the phase's own vocabulary admits an unverified observation — `SPEC-DEVIATION` requires a
>   contradicted declared rule, `RUNTIME-ERROR` an observed failure, `BEST-PRACTICE` a
>   demonstrated risk, and the phase's `## 9` states "This phase files no `DOC-UPDATE`".
>   Substituting `LOW` would manufacture an observed severity that `99-audit-validate.md` `## 8`
>   forbids ("never with an observed severity") and would still not be an observed severity.
>   The cell is therefore left as filed, and the input defect is filed as **`VAL-404`**.
> - **See also:** `VAL-404` — the report format has no legal encoding for a not-executed
>   finding; `VAL-410` — the cited register path does not exist and the register's own line
>   references are stale against the code it describes; `S-4` in Documented Skips.

**`UNVERIFIED`** — no severity is written for this finding, by the phase's own
admissibility rule.

**Description:** The production condition behind the project's registered
CRITICAL concurrency defect (`.ai/problems/01-confirmed-code-defects.md:38-69`,
D-01) is: batch mode, videos in flight >= `max_concurrent_downloads`, and at
least one video taking the segment path — the segment layer then claiming the
*same* non-reentrant primitive the outer claim already holds. That condition was
**not executed**, by design of this phase; no batch was run against a live
origin, and none is claimed here.

What *was* executed (R2) is the route, with only the session and the
media-method result substituted. `uv run python .temp/audit04/r2_reachability.py`:
```
=== R2 path (i): media method returns no result ===
  captured policy.semaphore      : <asyncio.locks.Semaphore object at 0x...AD1A0 [unlocked, value:4]>
  is_bounded_batch flag stored   : True
  policy.max_concurrent_downloads: 4
  inner IS outer wrapper?        : False
  inner IS outer raw semaphore?  : False
  segments fanned out            : 2
=== R2 path (ii): non-empty partial file present ===
  captured policy.semaphore      : <asyncio.locks.Semaphore object at 0x...4420 [unlocked, value:4]>
  is_bounded_batch flag stored   : True
  inner2 IS outer wrapper?       : False
  inner2 IS outer_shared2?       : False
```

**Structural fact, not a severity:** both shipped routes reach the per-part
transfer from inside the outer claim, and on both the primitive the download
policy receives is a **distinct object** from the one handed to the outer claim
(`segment_downloader.py:822` builds a fresh `asyncio.Semaphore`); the only thing
carried across is the boolean `is_bounded_batch`
(`segment_downloader.py:823`, consumed at `segment_downloader.py:713`). The
D-01 nested-claim shape therefore does **not** reproduce on either path in the
shipped code — but the production condition itself remains unexecuted, so this is
recorded as unverified rather than as a clean result, and the register's
CRITICAL claim for D-01 must not be read as confirmed against this code.

**Recommendation:** execute the condition once against a live batch and retire
the D-01 claim, or amend `.ai/problems/01-confirmed-code-defects.md:38` to record
that the nested claim was replaced by a segment-layer-owned primitive. The
structural identity comparison is not proof of the condition's behaviour.
*Amended by this validation: the target file does not exist at that path — see
`VAL-410`.*

---
### CON-003: Work items are created without a bound — one task per missing part, and one task per URL

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived from source and measured. **Severity re-derived: HIGH — confirmed.**
>   The owning phase's `## 9` HIGH row lists this subject verbatim: "work items are created
>   without a bound".
>   *Segment layer.* `_create_segment_download_tasks` builds one `asyncio.Task` per missing
>   segment inside a plain loop (`segment_downloader.py:742-761`) and returns the whole list;
>   the claim that actually limits transfers is taken *inside* the task body
>   (`segment_downloader.py:679`, `async with policy.semaphore:`). Measured with 5 000 missing
>   segments under a ceiling of 4: `tasks created up front: 5000`, `live tasks: 5000`,
>   `semaphore waiters queued: 0` at the moment of creation — the ceiling is not yet in play
>   when the work is materialised.
>   *Batch layer.* `batch_downloader.py:343-362` creates one task per URL in a list
>   comprehension; the claim that limits videos is taken two frames deeper still, inside
>   `perform_download` (`downloader.py:500-502`). Measured with `_download_single` stubbed and
>   the default `max_concurrent_downloads=4`: `urls=100 -> 101 live tasks`,
>   `urls=1000 -> 1001`, `urls=5000 -> 5001` held by the runner. The live set tracks input
>   size, not the ceiling.
>   The source text's consequence sentence is accurate as written and is not overstated.
> - **See also:** `NET-014` in phase `03` (complementary, not duplicated — the same
>   "no third bound" concern from the request-count side, recorded as such in
>   `03-network-resilience-validated-findings.md:1064`); `VAL-001` in the same store, the
>   already-adjudicated cross-phase conflict on the connection ceiling, which names this
>   finding's sibling `CON-009` and adjudicates **in favour of `CON-009`**.

| Field | Value |
|-------|-------|
| **ID** | CON-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/batch_downloader.py` |
| **Classification** | mandatory |

**Description:** Both task factories create every task up front, before any
permit is claimed. The segment factory (`segment_downloader.py:742-761`) creates
one task per missing part; the claim that actually limits transfers
(`segment_downloader.py:679`) is taken inside the task. The batch factory
(`batch_downloader.py:343-362`) creates one task per URL; the claim that limits
videos is taken deeper still, inside `perform_download`. The ceilings bound how
much work *runs*, not how much work *exists*.

**Exact consequence:** the live task set scales with input size, not with the
configured ceiling, so memory and scheduler cost are unbounded by any setting the
operator can change, and a stop has to unwind every one of them.

**Evidence (re-executed this run).** Segment layer, `.temp/val04/p3_segments.py` case (d):
```
=== R3(d) task factory creates every task up front ===
  claim ceiling           : 4
  items missing           : 5000
  tasks created up front  : 5000
  live tasks              : 5000
  semaphore waiters queued: 0
```
Batch layer, `.temp/val04/p5b.py`:
```
  urls=   100  items entering the worker=   100  live tasks held by the runner=   101
  urls=  1000  items entering the worker=  1000  live tasks held by the runner=  1001
  urls=  5000  items entering the worker=  5000  live tasks held by the runner=  5001
```

**Recommendation:** keep the item count bounded by feeding the factory from a
worker pool or a bounded queue instead of materialising the whole list, so the
configured ceiling is the only thing that determines how much work is in flight.

---

### CON-004: The browser handle is never released on the stop path

> **Validation Note:**
> - **Action:** validated
> - **Detail:** The defect reproduces exactly; **the stated consequence does not, and is
>   corrected here.** **Severity re-derived: HIGH — confirmed** on the structural fact, which
>   the owning phase's `## 9` HIGH row lists verbatim: "a resource is not released on one or
>   more exit paths". Measured against the real `BrowserManager.__aexit__` with stand-in
>   browser and driver (no Chromium launched): stop unset gives
>   `['browser.close:start', 'browser.close:done', 'playwright.stop:start', 'playwright.stop:done']`;
>   stop set gives `['playwright.stop:start', 'playwright.stop:done']` with
>   `browser.close invoked: False` and `driver stopped: True`. The guard is
>   `browser.py:75`; the driver release in the `finally` (`:84-92`) is unconditional.
>   **Correction:** "the launched browser, and everything inside it, is left running for the
>   remainder of the process while the driver is asked to stop" is not supported by the
>   finding's own evidence. The same exit *does* call `playwright.stop()`, and the report's own
>   skip S-2 records that "the driver is a third-party object and was never launched" — so
>   driver teardown behaviour was never observed, and the report nonetheless asserts a
>   permanent leak. The true consequence is narrower and must be stated as: **the graceful
>   close is skipped, so the browser is torn down by driver shutdown rather than by the close
>   path, and if `playwright.stop()` itself exceeds its 10 s bound the teardown is
>   unbounded.** The recommendation stands — dropping `and not shutdown_event.is_set()` is
>   correct and the 10 s bound already serves the reason the guard exists.
>   Related doc drift, not a separate finding: `browser.py:63` states the exit "checks the
>   shared `shutdown_event` before each step"; the code guards only the first step.
> - **See also:** `VAL-401` — this fix and `CON-005`'s touch the same 20-line block, and
>   applying this one alone enlarges the failure `CON-005` describes.

| Field | Value |
|-------|-------|
| **ID** | CON-004 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | mandatory |

**Description:** `BrowserManager.__aexit__` conditions the browser release on
the stop state *not* being set (`browser.py:75`:
`if self.browser and not shutdown_event.is_set():`). The driver release in the
`finally` (`browser.py:84-92`) is unconditional, so on the stop path exactly one
of the two acquired resources is given back.**Exact consequence (as filed):** interrupting a browser-backed extraction skips
`browser.close()` entirely. The `extractor` raises `CancelledError` immediately
after the stop check (`extractor.py:282-285`), so the skip is the normal path,
not a rare one: the launched browser, and everything inside it, is left running
for the remainder of the process while the driver is asked to stop.

> **Correction to the consequence above, composed by this validation:** the permanent leak is
> not established and is withdrawn. `browser.py:84-92` calls `playwright.stop()` on the same
> exit; the browser is therefore torn down by driver shutdown rather than by the close path,
> and the residual risk is the 10 s bound on that call being exceeded. The defect — a release
> step skipped on a path that the extractor takes routinely — stands, and the severity is
> unchanged.

**Evidence (re-executed this run).** `.temp/val04/p4_browser.py`, the real
`BrowserManager.__aexit__` against stand-ins, so no browser is launched:
```
=== R7(a) stop unset ===
  trace        : ['browser.close:start', 'browser.close:done', 'playwright.stop:start', 'playwright.stop:done']
  browser.close invoked: True
=== R7(d) stop state already set ===
  trace        : ['playwright.stop:start', 'playwright.stop:done']
  browser.close invoked: False
  driver stopped      : True
=== R7(b) close exceeding the bound ===
  trace        : ['browser.close:start', 'playwright.stop:start', 'playwright.stop:done']
  elapsed 10.00s vs production bound 10.0s
```
Case (b) confirms the source report's related observation: the close is
*cancelled* by `asyncio.wait_for`, not retried, at exactly the production bound.

**Recommendation:** release unconditionally. The reason the guard exists —
avoiding a slow close during shutdown — is already served by the 10s
`asyncio.wait_for` bound on the same call; drop `and not shutdown_event.is_set()`
so a stop shortens the close rather than skipping it.

---

### CON-005: A failing browser release replaces the failure that caused the exit

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived. **Severity re-derived: HIGH — confirmed**; the owning phase's
>   `## 9` HIGH row lists this subject verbatim: "a release replaces the failure that caused the
>   exit". `browser.py:78` and `:88` catch only `TimeoutError`; nothing else is caught, and the
>   `finally` at `:84` guarantees only that the *second* step still runs. Measured with the
>   real `__aexit__` and a body exception in flight: `escaped exception:
>   RuntimeError('driver exploded')`, trace
>   `['browser.close:start', 'browser.close:raised', 'playwright.stop:start', 'playwright.stop:done']`.
>   The consumer chain holds: `_download_single`'s catch-all
>   (`batch_downloader.py:282-294`) classifies by `type(e).__name__`, so the item is reported
>   as `unexpected_error: RuntimeError` instead of the domain status label.
>   One precision correction, no change of severity: the in-flight body exception is not
>   erased — it survives as `__context__` (measured: `True`) and is visible on the raised
>   traceback. What is lost is that it is never the exception that reaches the operator's
>   summary, which is what the finding says and what the fix must preserve.
> - **See also:** `VAL-401` — ordering constraint against `CON-004`, same block.

| Field | Value |
|-------|-------|
| **ID** | CON-005 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` |
| **Classification** | mandatory |

**Description:** `__aexit__` catches only `TimeoutError`
(`browser.py:78`, `:88`). Any other exception from `browser.close()` or from
`playwright.stop()` propagates out of the exit path and replaces whatever
exception the `async with` body was already unwinding.

**Exact consequence:** when a browser-backed extraction fails and the browser is
already unhealthy — the ordinary case for a crashed or forcibly-killed Chromium —
the diagnostic the operator loses is the domain one. `extractor.py:274-276`
raises `ExtractionError("Failed to navigate to video page: ...")`, but the
replacement is the driver's own error, which `_download_single` classifies with
its catch-all as `unexpected_error: <Playwright error type>`
(`batch_downloader.py:282-294`) instead of a status label. The user is told the
programme has a bug, not that the page failed to load.

**Evidence (re-executed this run), `.temp/val04/p4_browser.py` case (c).**
```
=== R7(c) close raising a non-timeout error, with an exception in flight ===
  escaped exception: RuntimeError('driver exploded')
  the in-flight body exception survived as __context__: True
  trace        : ['browser.close:start', 'browser.close:raised', 'playwright.stop:start', 'playwright.stop:done']
```

**Recommendation:** catch `BaseException` around each release step, log it with
the reason the step failed, and suppress it when an exception is already in
flight. The `finally` at `browser.py:84` already guarantees the second step
runs; the same guarantee is needed for the first step's own failure.

---
### CON-006: The completion helper returns the same value for "nothing to do" and "cancelled", so a fully resumed download never merges and is reported as failed

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived end to end against the real factory and the real helper.
>   **Severity re-derived: MEDIUM — confirmed**; the owning phase's `## 9` MEDIUM row lists
>   this subject verbatim: "an empty result is not distinguished from a cancelled one at its
>   consumer". With all three segments already written to disk, the real factory produced
>   `0 tasks`, the real `_await_and_cancel` returned `None`, and the real
>   `_process_downloaded_segments` returned `None` — the merge at `:650-658` is never reached.
>   The identity of the two `None`s is in the source: `:557-558` (empty) and `:570`
>   (cancelled). The helper's own docstring (`:555`) already promises the distinction the code
>   does not keep.
>   The downstream claim was checked rather than assumed: `_classify_download_result(None)`
>   returns `ProgressStatus.FAILED` only when the stop state is unset
>   (`batch_downloader.py:150-156`), and a fresh process run starts with a fresh event because
>   the stop state is a context variable created on first read
>   (`downloader_throttle.py:26-43`). A fully-present resume is therefore reported as a
>   failure, and the report's "the user re-runs the command indefinitely" is a correct reading
>   of a resume that can never complete.
> - **See also:** `CON-007` and `CON-008` (same function, same return value);
>   `VAL-402`.

| Field | Value |
|-------|-------|
| **ID** | CON-006 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `_await_and_cancel` has one early return,
`if not tasks: return None` (`segment_downloader.py:557-558`), and its
cancellation path returns the identical `None`
(`segment_downloader.py:570`). Its only consumer
(`segment_downloader.py:647-649`) cannot tell them apart.

**Exact consequence:** when every part is already present on disk — the resume
case the whole segment layer exists for — the task factory correctly produces
zero tasks (`segment_downloader.py:745-747`), the helper returns `None`, and
`_tally_and_merge` (`segment_downloader.py:650-658`) is never called. The merge
that would produce the finished video is skipped, `download_hls_with_resume`
returns `None` (`segment_downloader.py:924`), and the batch layer classifies
that as a failure (`batch_downloader.py:156`). A download that is 100% complete
on disk is reported as failed, and the user re-runs the command indefinitely.

**Evidence (re-executed this run), `.temp/val04/p3_segments.py` case (a).**
```
=== R3(a) nothing to do (all segments already on disk) ===
  task factory produced: 0 tasks
  _await_and_cancel([]) -> None
  _process_downloaded_segments -> None (merge never reached)
```

**Recommendation:** separate the two outcomes. Return an empty result list for
"nothing to do" and keep `None` for cancellation only, so the consumer can reach
the merge in the resume case. The surrounding `_await_and_cancel` name already
promises a list on success and `None` on cancellation in its own docstring
(`segment_downloader.py:555`).

---

### CON-007: A raising part orphans every sibling part

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived. **Severity re-derived: MEDIUM — confirmed**, composed from this
>   run's own evidence rather than inherited: the owning phase's `## 9` table has no row for
>   this subject, so the rung was composed here. The siblings are not leaked permanently —
>   each is bounded by the per-request `download_timeout` its own transfer applies
>   (`downloader_throttle.py:200-205`) — which is what separates this from the HIGH row's
>   "a resource is not released on one or more exit paths". What is real is that the sibling
>   tasks outlive the operation that owned them: measured, `RuntimeError('boom')` escapes the
>   helper while `task[0]` and `task[2]` remain `<Task pending ...>` immediately after the
>   raise and still `<Task pending>` one loop iteration later, each holding its permit
>   (`segment_downloader.py:679`) and its segment file handle.
>   One correction to the consequence sentence, no change of severity: "keep writing `.ts`
>   files after the caller has been told the download **finished**" is wrong — the caller was
>   told it *failed*; `_process_downloaded_segments` raised and
>   `download_hls_with_resume`'s `finally` (`segment_downloader.py:926-927`) logged
>   `preserving_segments_for_resume` **while those siblings were still writing**. That is the
>   sharper statement and it is what the fix must close. Likewise "its HTTP session slot" is
>   imprecise: the session's `async with` (`segment_downloader.py:797`) exits as the exception
>   propagates, so a surviving sibling's next request fails on a closed session rather than
>   occupying a slot.
> - **See also:** `CON-006` and `CON-008` (same helper, same settle discipline); `VAL-402`.

| Field | Value |
|-------|-------|
| **ID** | CON-007 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `_await_and_cancel` gathers without `return_exceptions`
(`segment_downloader.py:561`). The `except asyncio.CancelledError` branch that
cancels and re-awaits the siblings (`:562-570`) exists only for cancellation;
any other exception escapes immediately with the siblings untouched.

**Exact consequence:** one part that raises leaves every other part task running
and unawaited, holding its permit, its HTTP session slot and its file handle. The
video is already abandoned — `download_hls_with_resume` logs
`preserving_segments_for_resume` (`segment_downloader.py:926-927`) — yet its
siblings keep writing `.ts` files after the caller has been told the download
finished, and keep retrying against the origin after a stop was requested.**Correction to the consequence above, composed by this validation:** the siblings outlive a
*failed* caller, not a finished one — `preserving_segments_for_resume` is logged at
`segment_downloader.py:926-927` while they are still writing, and the aiohttp session's
`async with` has already closed underneath them (`segment_downloader.py:797`). The severity is
unchanged; the sentence must be rewritten before it is acted on.

**Evidence (re-executed this run), `.temp/val04/p3b.py` case (b).**
```
=== R3(b) one part raises, siblings ===
  raised out of the helper: RuntimeError boom
  order: ['item0 start', 'item1 raised', 'item2 start']
  sibling states IMMEDIATELY after the raise:
    task[0] <Task pending ... wait_for=<Future pending ...>>
    task[1] <Task finished ... exception=RuntimeError('boom')>
    task[2] <Task pending ... wait_for=<Future pending ...>>
  after one loop iteration:
    task[0] <Task pending ...>
    task[2] <Task pending ...>
```

**Recommendation:** wrap the gather in `except BaseException` (not just
`CancelledError`) and run the same cancel-and-reawait sequence, or pass
`return_exceptions=True` and let the caller decide. Either way the sibling tasks
must be settled before the helper returns.

---

### CON-008: The completion helper swallows the cancellation it was asked to propagate, and logs it as a shutdown that never happened

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived. **Severity re-derived: MEDIUM — confirmed**, with the table
>   mismatch recorded rather than concealed. The owning phase's `## 9` HIGH row contains a
>   condition that reads as this subject — "a stop is indistinguishable from an ordinary failure
>   at an entry point" — and the MEDIUM rung is what this run composes because the *trigger*
>   was not shown to be reachable from the shipped entry point on the declared platform: the
>   only canceller in that flow is the runtime's own `Runner._on_sigint`, and `CON-001` proves
>   it is displaced at install. The code that would consume the cancellation
>   (`batch_downloader.py:374-379`, and `_download_single`'s `except CancelledError` at
>   `:252-263`) therefore cannot be reached by Ctrl-C today. This is a rung held down by a
>   sibling defect, and it must be revisited the moment `CON-001` lands — see `VAL-403`.
>   The mechanism itself reproduces exactly: stop state `False` throughout, yet
>   `download_cancelled reason="shutdown_requested"` logged; all three items observed the
>   cancel; the holder task finished normally with `result=None` instead of re-raising.
>   The consumer chain is confirmed by reading: `asyncio.as_completed` never sees a
>   `CancelledError`, so the fan-out branch is skipped, and
>   `_classify_download_result(None)` with the event unset returns
>   `ProgressStatus.FAILED` (`batch_downloader.py:150-156`) — the item is reported as failed
>   and the process exits `1` instead of `130`.
> - **See also:** `CON-001` (the defect that currently keeps this one unreachable);
>   `VAL-403` — fixing `CON-001` by escalating to the displaced handler activates this path;
>   `CON-006` and `CON-007` (same helper); `VAL-402`.

| Field | Value |
|-------|-------|
| **ID** | CON-008 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** On cancellation the helper cancels and re-awaits its tasks and
then returns `None` (`segment_downloader.py:562-570`) instead of re-raising. It
also logs `download_cancelled reason="shutdown_requested"`
(`segment_downloader.py:569`) unconditionally, whether or not the stop state was
ever set.

**Exact consequence:** a caller that cancels the item gets a normal `None`
return instead of a `CancelledError`. `asyncio.Task.cancel()` on the enclosing
work therefore has no effect: the task completes "successfully" with `None`, and
the batch's classification — which decides cancelled vs failed purely by reading
the stop state (`batch_downloader.py:152-156`) — records the item as **failed**,
because nothing set the event. The batch's cancel-and-gather branch
(`batch_downloader.py:374-379`) exists to fan cancellation out to siblings; a
cancellation absorbed here never reaches it, and `asyncio.run` never sees it
either.

**Evidence (re-executed this run), `.temp/val04/p3b.py` case (c).**
```
=== R3(c) holder task cancelled externally while items run ===
  stop event set before the probe: False
[info] download_cancelled   reason=shutdown_requested        <-- emitted with the state unset
  order: ['cancelling the holder task', 'item0 observed cancel', 'item1 observed cancel',
          'item2 observed cancel', 'holder returned normally: None']
  holder task after completion: <Task finished ... coro=<holder() done> result=None>
```

**Recommendation:** re-raise `CancelledError` after the siblings are settled, and
log `reason="cancelled"` for that path, reserving `shutdown_requested` for the
case where the stop state is actually set.

---
### CON-009: The transport's pool ceiling is a literal that the declared setting does not imply, and the per-origin ceiling is unset

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived against the real constructor for every combination the finding names.
>   **Severity re-derived: MEDIUM — confirmed.** The owning phase's `## 9` table has no row for
>   this subject; MEDIUM is composed here as the rung below HIGH ("a number the operator is
>   shown does not mean what it is named" — the number here is accurate, only the ceiling it
>   implies is not derived) and above LOW, which the table reserves for deviations with no
>   runtime consequence and this plainly has one.
>   Measured: `_create_connector` returns `limit=10 limit_per_host=0` for
>   `max_concurrent_downloads` ∈ {4, 16} × `ssl_verify` ∈ {True, False} — four of four
>   identical, and identical across the declared range `ge=1, le=16`. The multiplier in the
>   consequence sentence is structurally sound, not measured: one connector is constructed
>   per `_run_download_session` (`segment_downloader.py:795`) and paired with its own session
>   (`:797`), and the per-unit transfer semaphore is sized by the same setting (`:822`). The
>   connection figures are therefore an upper bound the setting can reach, which is how the
>   finding words them ("can reach").
>   The scope boundary the finding draws is correct and is respected: the literal only; the
>   request *rate* against one origin belongs to phase `03`.
> - **See also:** **`VAL-001` in `03-network-resilience-validated-findings.md` — already
>   adjudicated, not re-filed here.** That store records the cross-phase conflict in which
>   `NET-014` (phase 03) and this finding state incompatible facts about the same
>   `limit=10`, and adjudicates **in favour of this finding**: the ceiling is per download,
>   the aggregate is 10 × `max_concurrent_downloads`, and no process-wide pool exists. A
>   fixer must read `NET-014` through that correction. Complementary, not duplicated:
>   `NET-014` and `CON-003` are recorded as such at
>   `03-network-resilience-validated-findings.md:1064`.

| Field | Value |
|-------|-------|
| **ID** | CON-009 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** `_create_connector` hard-codes `limit=10`
(`segment_downloader.py:537`, `:543`) and never sets `limit_per_host`, so the
per-origin ceiling is `0` (unbounded). Neither value is derived from
`max_concurrent_downloads`. One connector is created per unit — measured, not
inferred — and each unit also builds its own transfer semaphore of the
configured size (`segment_downloader.py:822`), so the configured ceiling is a
*per-unit* quantity at both layers.

**Exact consequence:** at the declared default the segment fan-out can reach
4 x 4 = 16 concurrent transfers and 4 x 10 = 40 concurrent TCP connections; at
the declared maximum it reaches 16 x 16 = 256 transfers and 16 x 10 = 160
connections against a single CDN, from a setting documented as
"Maximum number of videos downloading concurrently in a batch"
(`config.py:89-98`). Nothing the operator can change in that setting keeps the
connection count at the setting's value above 10, and nothing keeps the
per-origin count bounded at any value.

**Evidence (re-executed this run), `.temp/val04/p4_browser.py`, connector section.**
```
  max_concurrent_downloads= 4 ssl_verify=True  -> limit=10 limit_per_host=0
  max_concurrent_downloads= 4 ssl_verify=False -> limit=10 limit_per_host=0
  max_concurrent_downloads=16 ssl_verify=True  -> limit=10 limit_per_host=0
  max_concurrent_downloads=16 ssl_verify=False -> limit=10 limit_per_host=0
  declared setting bound: [Ge(ge=1), Le(le=16)]
  declared default: 4
```

**Recommendation:** derive `limit` from `settings.max_concurrent_downloads` and
set an explicit `limit_per_host`, so one setting governs the whole process
rather than each unit re-interpreting it. This phase files the literal only; the
resulting request *rate* against one origin belongs to phase `03`.

---

### CON-010: An abandoned off-loop extraction holds the process for up to the interpreter's thread-join constant after the reported bound has fired

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Re-derived against the shipped call shape. **Severity re-derived: MEDIUM —
>   confirmed.** `extractor.py:242-245` wraps `loop.run_in_executor(None, _sync_extract)` in
>   `asyncio.wait_for(..., timeout=self.settings.download_timeout)`; on expiry the asyncio
>   future is cancelled but the worker thread is not, and cannot be. Measured on CPython
>   3.12.1: `constants.THREAD_JOIN_TIMEOUT = 300`; a 1 s bound fired at t+1.0 s; the
>   coroutine returned with the thread still running; `asyncio.run` returned only after
>   **9.3 s** for an 8 s thread — i.e. `loop.shutdown_default_executor` joins the abandoned
>   thread before the interpreter is torn down, and the 300 s constant is the cap.
>   The finding's characterisation of the reported bound is verified against the model:
>   `download_timeout` default 300, `ge=30`, `le=3600` (`config.py:61-66`), and the exit-path
>   bound is a different, unnamed constant.
>   The consequence is a silent stall *after* the summary and the exit code have already been
>   produced, which is the operational point the recommendation addresses. Bounded, so not
>   HIGH; a real gap against a bound the operator is shown, so not LOW.
> - **See also:** `CFG-002` (phase `02`) owns the meaning, bound and validation of
>   `download_timeout`; complementary, not duplicated — this finding is about the exit path's
>   own unstated bound, not about the setting.

| Field | Value |
|-------|-------|
| **ID** | CON-010 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `extractor.py:242-245` bounds a synchronous yt-dlp extraction
dispatched to the default executor with `asyncio.wait_for(...,
timeout=settings.download_timeout)`. When that bound fires, the wrapper future is
cancelled but the executor thread is not — and it cannot be. `asyncio.run` then
blocks on `loop.shutdown_default_executor(constants.THREAD_JOIN_TIMEOUT)` while
it tears the interpreter down.

**Exact consequence:** after the reported timeout is raised as an
`ExtractionError`, the process does not exit; it waits for the abandoned thread
for up to 300 s, silently, after the summary and the exit code have already been
produced. The operator was shown `download_timeout` (default 300 s, maximum
3600 s); the bound actually applied to the exit path is 300 s and is stated
nowhere. A 3600 s extraction that times out still hangs the process for the full
thread-join constant after the error is reported.**Evidence (re-executed this run), `.temp/val04/p5b.py`.**
```
=== abandoned off-loop extraction (extractor.py:242-245 shape) ===
  interpreter thread-join constant: constants.THREAD_JOIN_TIMEOUT = 300
  bound fired at t+1.0s (the shape at extractor.py:242-245)
  returning from the coroutine with the thread still running
  asyncio.run returned after 9.3s with the executor thread still alive
```
The 9.3 s is the abandoned thread's own remaining lifetime; the cap is the 300 s constant.

**Recommendation:** state the exit-path bound where the timeout is configured,
and lower it for this call site — the extraction has already been declared failed
at that point, so joining it for five more minutes serves nothing.

---

## Checkpoint 2 — R2 Cross-Finding Analysis

- **Stage:** R2 Cross-Finding Analysis
- **Findings in scope:** 10 (`CON-001` … `CON-010`)
- **Cross-phase conflict count:** 0 filed here; **1 already filed elsewhere and cross-referenced
  rather than re-filed** — the connection-ceiling conflict between `NET-014` (phase 03) and
  `CON-009`, adjudicated in favour of `CON-009` at
  `03-network-resilience-validated-findings.md:1344` (`VAL-001`, CRITICAL).
- **Merge-candidate count:** 0. Within this report the ten findings name eight distinct
  defects across six modules; the closest pair is `CON-006`/`CON-008`, which share one function
  and one return value but describe two different consequences (a resume that cannot merge, and
  a cancellation that cannot propagate) and are fixed by different edits. Not a merge; they are
  handled together as an ordering constraint in `VAL-402`.
- **Genuine complements retained and cross-referenced:** `CON-009` ↔ `NET-014` (phase 03);
  `CON-003` ↔ `NET-014`; `CON-010` ↔ `CFG-002` (phase 02); `CON-001`'s registration-placement
  subject ↔ `ENT-004` and its correlation-id subject ↔ `ENT-012` (phase 01).
- **Conflicts with sibling phases checked:** `ENT-004` (registration placement) and `ENT-012`
  (correlation-id rebound at `downloader.py:663-664`) do not contradict anything here — this
  report cross-references rather than re-files them, as it states. No phase asserts an
  incompatible fact about a subject this report also asserts.
- **Checkpoint status:** closed

---

## Checkpoint 3 — R3 Validate Each Finding

- **Stage:** R3 Validate Each Finding
- **Findings in scope:** 10 — decisions: **Validated 10, Reclassified 0, Merged 0, Rejected 0.**
- **This is a decision tally, not a severity tally.** Two source severities were re-derived and
  corrected *in the text of their findings' consequence or evidence*, not in the severity column:
  `CON-004`'s permanent-leak claim is withdrawn and `CON-007`'s "told the download finished" is
  corrected. Both severities stand.
- **Runtimes confirmed by observation:** `CON-001` (three legs, plus a fourth at the production
  call shape), `CON-003` (both layers, measured), `CON-004`, `CON-005`, `CON-006`, `CON-007`,
  `CON-008`, `CON-009`, `CON-010`. `CON-002` is structural and carries the `UNVERIFIED` marker.
- **Type adjudication:** all nine `RUNTIME-ERROR` labels are **retained**. The report format
  defines four types (`.ai/audit/templates/audit-findings.md:68`) and `RUNTIME-ERROR` is one of
  them; the role files that wrote and now adjudicate them list three and omit it — see
  `VAL-409`. Per block (d), a finding describing something observed to fail is checked against
  the runtime-failure label first and is never reclassified away because a role file omits it.
  `CON-009` and `CON-010` are `BEST-PRACTICE`, matching the format's guide row for a defensible
  arrangement with a demonstrated gap. `CON-002`'s `SPEC-DEVIATION` is left as filed and the
  illegality is filed against the format as `VAL-404`.
- **Classification legality:** every `mandatory` / `advisory` value is in the format's enum
  (`.ai/audit/templates/audit-findings.md:74, :78-79`) and each sits on the right side of the
  guide row — the seven correctness findings are `mandatory`, the two design-gap findings are
  `advisory`. `CON-002` stays `mandatory` as filed; this phase does not change a classification
  the owning phase set.
- **Dead-code reconciliation (block e):** not invoked — no finding in this report calls any
  component dead, so the mandatory cross-reference against the specification, the readme, the
  declared data model and the configuration templates has no subject. No dead-code finding is
  manufactured to fill it.
- **Fragile insertion points (block c):** none in the source recommendations. Every anchor this
  report verifies is a semantic one — a guard expression (`browser.py:75`), a return
  (`segment_downloader.py:557-558`), a call (`downloader.py:500-502`), a loop head
  (`ffmpeg_utils.py:55-63`) — not a line number. The three real ordering hazards are filed as
  `VAL-401`…`VAL-403`.
- **Checkpoint status:** closed

---
## Findings added by this phase (`VAL-`)

These are defects in the audit inputs themselves — rollout-safety constraints over the fixes
this report accepts, and defects of the pipeline's own documents. None is a product-code
finding; per `## 10` this phase never re-files one.

### VAL-401: `CON-004` and `CON-005` prescribe edits inside the same 20-line block, and applying `CON-004` alone enlarges the failure `CON-005` describes

| Field | Value |
|-------|-------|
| **ID** | VAL-401 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` (`:63-92`) |
| **Classification** | mandatory |

**Description:** Both accepted findings target one `async def __aexit__`
(`browser.py:53-92`) and, inside it, one `try` / `except` / `finally` chain (`:74-92`).
`CON-004` deletes the guard `and not shutdown_event.is_set()` from `:75` so the close becomes
unconditional. `CON-005` widens the `except TimeoutError` at `:78` to catch and suppress a
release failure when an exception is already in flight. Neither names the other and neither
states an order.

**Exact consequence:** `CON-004` alone is a correctness *regression* on the very path it fixes.
Today the stop path never calls `browser.close()`, so a browser that is unhealthy during a
shutdown cannot raise from it. Once `CON-004` lands, that call runs on the stop path — and the
stop path is the one where the extractor raises `CancelledError` immediately after the stop
check (`extractor.py:282-285`) — so a close failure would propagate out of `__aexit__` and
**replace the `CancelledError`**, converting an orderly shutdown into an unhandled driver error.
That is precisely the substitution `CON-005` exists to prevent.

**Evidence:** `browser.py:74-92` read in full; `extractor.py:282-285`; both findings' quoted
recommendations; the ownership comment at `browser.py:62-66` and the doc drift it introduces
(noted in `CON-004`'s Validation Note) all name the same block.

**Recommendation:** apply `CON-005`'s suppression **before or with** `CON-004`'s unconditional
release, in one change. A fixer who lands `CON-004` first and runs the stop path against an
unhealthy browser will observe the regression and may attribute it to the wrong finding.

---

### VAL-402: `CON-006` and `CON-008` both rewrite the same function's return contract, and neither fix survives the other being applied as a local simplification

| Field | Value |
|-------|-------|
| **ID** | VAL-402 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py` (`:546-570`, `:647-649`) |
| **Classification** | mandatory |

**Description:** `CON-006` changes the empty-input return (`:557-558`) so "nothing to do" stops
being `None`. `CON-008` changes the cancellation return (`:562-570`) so it re-raises instead of
returning `None`. Both edits land in the same 25-line helper and both move the meaning of the
single `None` its one consumer branches on (`:647-649`, `if download_results is None`).

**Exact consequence:** the two are individually safe and jointly order-independent, but the
distinction they establish is carried entirely by an identity check the compiler does not
enforce. `CON-006`'s fix introduces `[]` — a **falsy** value — as the "nothing to do" result.
The consumer tests `is None`, which is correct; a fixer who tidies that to `if not
download_results`, or who routes "nothing to do" through the same `None` the merge path already
returns, silently reinstates the defect `CON-006` exists to remove. Nothing in the type
signature (`list[tuple[int, bool]] | None`, `:546-548`) distinguishes an empty result from a
populated one either.

**Recommendation:** land both edits in one change set, and make the empty case explicit at the
type level — a distinct sentinel or a `dataclass` result carrying the outcome — rather than
relying on `[]`-versus-`None`. Extend `CON-007`'s settle-the-siblings work at the same time:
all three findings target one helper whose reason for existing is to settle its tasks.

---

### VAL-403: Fixing `CON-001` by escalating the second interrupt activates `CON-008`'s misclassification path, and neither finding names the link

| Field | Value |
|-------|-------|
| **ID** | VAL-403 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py`, `src/vkdownloader/services/signal_handlers.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/batch_downloader.py` |
| **Classification** | mandatory |

**Description:** `CON-001` recommends two of three fixes; the second is "make the second
interrupt escalate (forward to the displaced handler or force-kill the child)". Forwarding to the
displaced handler is `asyncio.runners.Runner._on_sigint`, whose first action is to cancel the
main task. `CON-008` is the defect that makes such a cancellation vanish: the segment helper
absorbs it and returns `None`, and the batch layer then classifies the item by reading the stop
state (`batch_downloader.py:150-156`) — which the escalating interrupt, unlike the first one,
never sets. Neither finding names the other.

**Exact consequence:** on the escape route `CON-001` opens, an escalated interrupt cancels the
batch; every item returns `None`; the batch reports them **failed** and the process exits `1`
instead of the `130` the summary reserves for an interrupted run
(`batch_downloader.py:463-471`). Fixing the hang therefore produces a wrong exit code and a
false failure list on the exact interaction the user was trying to perform — and only on the
second interrupt, so the first still behaves.

**Evidence:** `signal_handlers.py:31-33` (idempotence — the first interrupt sets the event, the
second cannot); `segment_downloader.py:562-570` (absorption); `batch_downloader.py:150-156`
and `:374-379` (classification and the fan-out branch that never runs); `batch_downloader.py:
463-471` (the `130` that is thereby lost). Re-derived by reading; no product code was executed
for this link, and none was needed — every step is a straight-line fact.

**Recommendation:** treat `CON-008` as a prerequisite of the escalating half of `CON-001`'s
fix, or scope `CON-001`'s escalation to the force-kill branch only. Shipping the escalation
first is the one ordering that makes a shipped defect worse than the one it repairs.

---
### VAL-404: The report format has no legal encoding for a not-executed finding, and two pipeline documents require one

| Field | Value |
|-------|-------|
| **ID** | VAL-404 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.ai/audit/templates/audit-findings.md:68-69`; `.kilo/commands/audit/phases/04-audit-concurrency-cancellation.md:317, :319, :348`; `.kilo/commands/audit/phases/99-audit-validate.md` `## 8`, `## 12` |
| **Classification** | mandatory |

**Description:** Two documents mandate an encoding the format cannot express.

The format fixes the field as `| **Severity** | {severity} |` with
`severity ∈ CRITICAL, HIGH, MEDIUM, LOW` (`.ai/audit/templates/audit-findings.md:24`, `:69`).
The phase handbook requires the opposite: "A finding whose runtime consequence was not observed
is filed with the structural fact and an explicit `UNVERIFIED` marker, never with an observed
severity" (`04-audit-concurrency-cancellation.md:319`), and its binding rule W-4 goes further —
"The **production trigger** carries `UNVERIFIED` and **no severity**" (`:348`). The validation
task says the same at `## 8` and `## 12`.

A conforming report must therefore write something the enum forbids. `CON-002` writes
`*none — not executed*` — out of enum, and unfixable in place, because the only admissible
substitute is `LOW`, which *is* an observed severity and would contradict all three documents.

The **type** field is equally unable to carry it. The format offers four labels
(`audit-findings.md:68`); the phase's own guidance (`:317`) admits `SPEC-DEVIATION` only for
behaviour contradicting a declared rule, `RUNTIME-ERROR` only for something observed failing and
`BEST-PRACTICE` only for a demonstrated risk — none of which an unverified observation is — and
closes with "This phase files no `DOC-UPDATE`". There is no fifth label, and `## 8` of the
validation task forbids adding one.

**Exact consequence:** every future audit that follows W-4 emits a report that violates its own
template on a mandatory field, and the validator that adjudicates it must either accept an
illegal value or rewrite a field the source report owns. `CON-002` is the concrete instance in
this run: this validation had to leave an out-of-enum severity in place and file the defect
instead of correcting it.

**Evidence:** the three quoted lines, each read in the file named in the field table above; the
`CON-002` field table in the source report and in this artifact, both carrying
`*none — not executed*`.

**Recommendation:** add a fifth severity member — `UNVERIFIED`, defined as "the structural fact
is recorded; the runtime consequence was not observed" — and add a fifth type label with the
same meaning, or state that `UNVERIFIED` findings are filed as `LOW`/`BEST-PRACTICE` with a
mandatory marker field. Either restores agreement. Leaving it makes every W-4 report illegal by
construction, and the pipeline has now produced one.

---

### VAL-405: The orchestrator writes one validation filename and its own gate checks another, so every run fails its gate for a file that is on disk

| Field | Value |
|-------|-------|
| **ID** | VAL-405 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:94`, `:105` |
| **Classification** | mandatory |

**Description:** The validator launch writes
`.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md`
(`audit-multi-phase.md:94`). The verification step six lines later checks
`.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated.md` — no `-findings`
(`:105`). The two strings differ, and the `-validated.md` form matches no file any stage
produces.

**Exact consequence:** a validator that does its job perfectly writes the correct artifact and
is then told the artifact is missing. The gate's failure path is `retry once, then escalate on
second failure` (`:106`, `:131-132`), so every run of a phase that produces findings costs a
wasted validator execution and ends in an escalation reporting a defect that does not exist. The
failure is silent in the sense that matters: the artifact is on disk, correct, and is reported
as absent.

**Evidence:** both strings, quoted from the lines named above. Confirmed against the store:
three validation artifacts exist, all in the `-validated-findings.md` form, and none in the
`-validated.md` form the gate checks. Same defect as `VAL-106` in the phase-01 store and
`VAL-003` in the phase-03 store; **the write side is the side this pipeline has always
produced and the check is the defective side**, per `99-audit-validate.md` `## 6` subject 1.

**Recommendation:** correct `:105` to
`.ai/audit/99-validation/{PHASE_NUMBER}-{PHASE_NAME}-validated-findings.md`. The `-validated-findings.md`
form is authoritative and this artifact is written to it.

---

### VAL-406: The condition that launches the validator cannot be evaluated, while the closing output reports validation coverage unconditionally

| Field | Value |
|-------|-------|
| **ID** | VAL-406 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:85-88`, `:112-125` |
| **Classification** | mandatory |

**Description:** `### 2.4 Launch Validator` opens "Launch the Validator **only** when Findings
are **not trivial** ands relate to **significant code changes** or **architecture
modifications**" (`:86`). Neither "not trivial" nor "significant" is defined anywhere in the
command, in any phase handbook, or in the report format, and nothing in the command evaluates
either term before deciding to launch. The stage that never fires and the closing output that
claims it ran are one defect: `<output>` prints "Validated findings: {N} total" and a
per-severity breakdown (`:118-124`) with no indication of how many phases were validated and how
many were skipped by the undefined gate.

**Exact consequence:** the run reports complete validation coverage for whichever phases it
happened to validate. A reader has no way to tell from the closing output that other phases'
findings were never adjudicated — which is the opposite of the record's purpose.

**Evidence:** `:86` quoted; the terms searched across `.kilo/commands/audit/` and
`.ai/audit/templates/` — no definition, no evaluator. `:118-124` quoted. Same defect as
`VAL-107` in the phase-01 store and `VAL-003` in the phase-03 store.

**Recommendation:** either define the term with a testable predicate (for example: launch when
the findings file contains at least one finding of severity `CRITICAL` or `HIGH`), or drop the
gate and always validate, and have the closing output report the count of phases validated
against the count selected.

### VAL-407: The orchestrator instructs that rejected findings be deleted, contradicting the retention rule this artifact is built on

| Field | Value |
|-------|-------|
| **ID** | VAL-407 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:133`; `.kilo/commands/audit/phases/99-audit-validate.md` `## 11` |
| **Classification** | mandatory |

**Description:** `audit-multi-phase.md:133`, under `<retry_rules>`, reads "Rejected findings
cleaned from file before merge". `99-audit-validate.md` `## 11` requires the opposite and states
it as binding rule 2: a rejected finding is written as
`### {ID}: ~~{title}~~ [REJECTED]` plus its reason, and "**Never delete it** — the claim and the
reason are what stop the next run re-deriving it."

**Side this phase takes, and why:** the **preserving side governs**. A rejection reason is the
only thing that distinguishes "this claim was considered and rejected" from "this claim was
never considered". Deleting it converts every rejection into a re-derivation on the next run —
precisely the cost this phase's own contract is written to avoid. Where the two documents
disagree, this artifact preserves, and the contradiction is filed here.

**Exact consequence:** if the deleting rule is applied at merge time, this artifact loses the
evidence that `CON-002` was considered and why it was kept, and the next validation of phase
`04` will re-derive the whole D-01 question from scratch. No product risk; a permanent loss of
audit provenance.

**Evidence:** both lines quoted. Same defect as `VAL-108` in the phase-01 store and `VAL-007`
in the phase-03 store.

**Recommendation:** delete `:133` from the orchestrator, or scope it to findings that were
rejected *because* their evidence no longer exists, with the reason retained inline.

---

### VAL-408: The orchestrator's mandatory context read names a file the repository does not contain

| Field | Value |
|-------|-------|
| **ID** | VAL-408 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.kilo/commands/audit/audit-multi-phase.md:43` |
| **Classification** | mandatory |

**Description:** `### 1 Gather Base Layer Context (once)` instructs "Read `AGENTS.md` for
project guidelines" (`:43`) with no conditional, and `{BASE_CONTEXT}` — the value passed to
every executor and validator — is defined as the summary of that read together with
`.ai/context/commands.md` and the `docs/` listing (`:46-48`). `Test-Path AGENTS.md` at the
repository root returns `False`; the file is not there.

**Where the rules actually live:** `.kilo/rules/project.md` (the fifteen project rules) and
`.kilo/rules/commands.md` (the verification commands). Neither is named anywhere in the
orchestrator.

**Exact consequence:** half of every `{BASE_CONTEXT}` the pipeline assembles is empty, and the
run reports nothing about the miss. The auditors that executed did have the rules — this
validation received them as base context — so the defect is currently masked by the harness
rather than absent.

**Evidence:** `Test-Path -LiteralPath "AGENTS.md"` → `False`; `.kilo/rules/project.md` and
`.kilo/rules/commands.md` present. Same defect as `VAL-109` in the phase-01 store and `VAL-005`
in the phase-03 store.

**Recommendation:** point `:43` at `.kilo/rules/project.md` and `.kilo/rules/commands.md`, and
state the miss when a declared context file is absent rather than assembling half the context
silently.

---

### VAL-409: Both role files list three of the four type labels the format defines, and nine of the ten findings in this report carry the omitted label

| Field | Value |
|-------|-------|
| **ID** | VAL-409 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Artefacts** | `.ai/audit/templates/audit-findings.md:68`; `.kilo/agents/auditor.md:256-259`; `.kilo/agents/validator.md:241-245`, `:354-358` |
| **Classification** | mandatory |

**Description:** The report format defines four type labels:
`SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, `RUNTIME-ERROR`
(`.ai/audit/templates/audit-findings.md:68`). The auditor role file lists three and omits
`RUNTIME-ERROR` (`.kilo/agents/auditor.md:256-259`: "Use labels: `[SPEC-DEVIATION]` …
`[BEST-PRACTICE]` … `[DOC-UPDATE]`"). The validator role file that executes this phase lists
the same three, twice — in its Classification block (`:241-245`) and in its own Output Format
block (`:354-358`).

The **format is the authority**; the role files are the defective side, and the role that
executes this phase is one of them.

**Exact consequence:** nine of the ten findings in this report — `CON-001`, `CON-003`, `CON-004`,
`CON-005`, `CON-006`, `CON-007`, `CON-008`, `CON-009`, `CON-010` — carry `RUNTIME-ERROR`, a
label the agent that wrote them has no vocabulary entry for, and the agent adjudicating them has
none either. A role agent following its own instructions could classify all nine as
`SPEC-DEVIATION` and record a different finding set in its decision table.

**Evidence:** both role files quoted at the lines named above; the template's own enum quoted;
the count of `RUNTIME-ERROR` labels in this report's field tables, nine.

**Adjudication recorded here so the labels are not lost:** per block (d), a finding describing
something observed to fail is checked against the runtime-failure label **first**, and is never
reclassified away because a role file omits it. All nine `RUNTIME-ERROR` labels are therefore
**retained unchanged** in this artifact. This is a defect of the role files, not of the report.

**Recommendation:** add `RUNTIME-ERROR` to both role files' label lists and to the validator's
Output Format block. Same defect as `VAL-110` in the phase-01 store and `VAL-004` in the
phase-03 store.

---

### VAL-410: `CON-002`'s cited register path does not exist, and the archived register's own line references are stale against the code it describes

| Field | Value |
|-------|-------|
| **ID** | VAL-410 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Artefacts** | `.ai/audit/04-concurrency-cancellation/findings.md:146`, `:182`; `.ai/plans/done/01-confirmed-code-defects_DONE.md:38-69` |
| **Classification** | mandatory |

**Description:** `CON-002` cites `.ai/problems/01-confirmed-code-defects.md:38-69` as the
project's registered CRITICAL concurrency defect, and recommends amending
`.ai/problems/01-confirmed-code-defects.md:38`. **That path does not exist.** The register was
archived to `.ai/plans/done/01-confirmed-code-defects_DONE.md`; D-01 is in its summary table at
`:20` and its own section at `:38-69`, which is the content the finding cites.

The archived register's location is not the only staleness. Its **Location** list
(`:41-47`) points at `batch_downloader.py:281` for the shared semaphore, `:153` for the tracked
wrapper and `:202` for the call, and at `downloader.py:491-493` for the semaphore context. In
the shipped code those are `batch_downloader.py:328`, `:193` and `:242`, and
`downloader.py:500-502`. A reader following the register's own line numbers lands on unrelated
statements.

**Exact consequence:** a fixer who acts on `CON-002`'s recommendation opens a path that is not
there and may conclude the register has been deleted. A reader who does find the archived
register follows line references that no longer point at the code. And the finding's central
point — that a CRITICAL entry in the register describes a shape the code no longer has — is
only half true: the shape is absent because the register's own **Fix**, Option A
(`:61`), was implemented, and `:61` is the line that says so.

**Evidence:** `Test-Path .ai/problems/01-confirmed-code-defects.md` → the directory holds only
`PROBLEM.md`; `.ai/plans/done/01-confirmed-code-defects_DONE.md:20` and `:38` read; the four
line references compared against the shipped files.

**Recommendation:** correct `CON-002`'s two path references to
`.ai/plans/done/01-confirmed-code-defects_DONE.md:38` and `:61`, and note in the finding that
D-01 was **fixed**, not merely unexecuted — which retires the "execute the production condition"
half of its recommendation and leaves only the register-wording half. The wording of the archived
register is `09`'s subject by R-E and is **not** re-filed here.

## Checkpoint 4 — R4 Assess Rollout Safety

- **Stage:** R4 Assess Rollout Safety
- **Findings in scope:** 10 accepted, all actionable; 10 findings added (`VAL-401` … `VAL-410`).
- **Circular dependencies:** 0. No two accepted fixes are prerequisites of each other in a
  cycle. The one genuine prerequisite runs forward, not backward, and is recorded as
  `VAL-403`.
- **Unsafe-ordering pairs:** 3.
  - `VAL-401` — `CON-004` before `CON-005` turns a shutdown `CancelledError` into an unhandled
    driver error, in the same 20-line block.
  - `VAL-402` — `CON-006` and `CON-008` are one change set; the `[]`-versus-`None`
    distinction they establish rests on an identity check a later cleanup would erase.
  - `VAL-403` — the escalating-interrupt half of `CON-001` activates `CON-008`'s
    misclassification, turning the repaired hang into a wrong exit code on the second interrupt.
- **Hidden chains:** 2 — `VAL-403` (`CON-001`'s escalation needs `CON-008`, neither says so)
  and the corollary below.
  - **Held-down severity, recorded so it is not mistaken for a settled rung:** `CON-008` is
    filed `MEDIUM` because its trigger is unreachable today — the only canceller in the flow is
    the runtime handler `CON-001` proves is displaced. The owning phase's HIGH row describes
    this subject ("a stop is indistinguishable from an ordinary failure at an entry point").
    The moment `CON-001` lands and an interrupt can reach the batch, `CON-008` re-reads as HIGH.
- **Fragile insertion points:** 0 in the accepted recommendations — every anchor is a guard
  expression, a return, a call site or a loop head, not a line number. This was checked by
  reading each recommendation's target, not assumed.
- **Findings added:** 10 — 3 rollout-ordering, 6 pipeline-document, 1 report-contract, 1
  evidence-citation.
- **Not filed, deliberately:** the `VAL-` identifier collision across per-phase runs is a real
  defect and is **already filed** as `VAL-112` in the phase-01 store. This artifact does not
  re-file it; it adopts `VAL-401`… as a non-colliding range and says so in its header.
- **Blockers:** none. Every accepted finding is implementable; three are not implementable
  *correctly* out of order, and that is recorded above rather than assumed away.
- **Checkpoint status:** closed

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 10 | `CON-001`, `CON-002`, `CON-003`, `CON-004`, `CON-005`, `CON-006`, `CON-007`, `CON-008`, `CON-009`, `CON-010` |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |
| VAL- (cross-phase / rollout) | 10 | `VAL-401`, `VAL-402`, `VAL-403`, `VAL-404`, `VAL-405`, `VAL-406`, `VAL-407`, `VAL-408`, `VAL-409`, `VAL-410` |

**Severity re-derivation, stated once.** No finding's severity changed. Two findings' *consequence
sentences* were found unsupported and corrected in place — `CON-004`'s permanent-leak claim
(withdrawn; the driver release in the same exit bounds it) and `CON-007`'s "told the download
finished" (corrected: told it *failed*, and `preserving_segments_for_resume` is logged while the
siblings still write). Two rungs were composed here because the owning phase's severity table
has no row for them — `CON-007` and `CON-009` — and one rung was held below the table's HIGH row
on stated evidence — `CON-008` — with the condition that would lift it recorded in Checkpoint 4.
`CON-002` carries an out-of-enum severity that this phase may not correct; it is filed as
`VAL-404`.

### Rejected Findings

Zero. No source finding met a stated rejection ground — none was stale-but-unrelated, none was a
duplicate, none was already-correct-by-design, and none was stylistic. `CON-002` came closest
and was kept for the reason in its Validation Note: the owning phase's binding rule W-4
forbids omitting it, and its structural fact is true. The one defect this phase identified and
**declined to file** — the `VAL-` prefix collision across per-phase runs — is a duplicate of
`VAL-112` in the phase-01 store and is cross-referenced instead, in this artifact's header.

### Merged Findings

Zero. The ten findings name eight distinct defects across six modules; no two share one root
cause. The nearest pair, `CON-006` and `CON-008`, share a function and a return value but
describe two different consequences repaired by two different edits — complementary, and carried
together as an ordering constraint in `VAL-402` rather than collapsed.

### Reclassified Findings

Zero. No `Type` changed. In particular the nine `RUNTIME-ERROR` labels were **retained** despite
both role files omitting that label from their vocabulary: the report format is the authority,
it defines the label, and block (d) forbids reclassifying an observed failure away because a role
file does not list it. That role-file defect is filed as `VAL-409`. `CON-002`'s `SPEC-DEVIATION`
is likewise left as filed, with the input defect that makes it unplaceable filed as `VAL-404`.