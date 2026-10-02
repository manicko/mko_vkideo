---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 04 Audit Findings — Concurrency and Cancellation

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/04-audit-concurrency-cancellation.md`
**Status:** complete
**Validated:** no

**Platform note.** Declared platform is Windows. Observed loop:
`asyncio.windows_events.ProactorEventLoop`; `loop.add_signal_handler` raises
`NotImplementedError` for both SIGINT and SIGTERM, so the process-level
`signal.signal` fallback (`signal_handlers.py:48`) is the path that actually
runs. `loop.add_signal_handler` is therefore **not** reported as broken — it is
unreachable here. Delivery of a real key press belongs to the console; the
installed handler was captured and invoked programmatically instead.

---

## Findings

### CON-001: A stop is never observed by a blocked read of a child's output, a second stop changes nothing, and the runtime's interrupt handler is left displaced

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
any in-process means.

**Evidence (R4, R5 — this is the reproduced shape, composed from all three legs):**

R1 leg — executed, **negative**. The primitive is sound; concurrent acquisition
does not serialise work into a standstill. `uv run python .temp/audit04/r1_primitive.py`:
```
{'ceiling': 4, 'units': 4, 'parts': 2, 'completed': 4, 'pending': 0, 'peak_reported': 4, 'permits_free': 4, 'waiters': 0, 'claims_per_unit': [3, 3, 3, 3]}
{'ceiling': 1, 'units': 1, 'parts': 1, 'completed': 1, 'pending': 0, 'peak_reported': 1, 'permits_free': 1, 'waiters': 0, 'claims_per_unit': [2]}
{'ceiling': 4, 'units': 1, 'parts': 4, 'completed': 1, 'pending': 0, 'peak_reported': 1, 'permits_free': 4, 'waiters': 0, 'claims_per_unit': [5]}
{'ceiling': 16, 'units': 3, 'parts': 2, 'completed': 3, 'pending': 0, 'peak_reported': 3, 'permits_free': 16, 'waiters': 0, 'claims_per_unit': [3, 3, 3]}
slow stage inside the outer claim: ceiling=4  -> 4 units entered, all completed, free=4,  waiters=0
                                          ceiling=16 -> 16 units entered, all completed, free=16, waiters=0
```

R4 leg — executed, **positive**. `uv run python .temp/audit04/r4_signal.py`:
```
loop class                  : asyncio.windows_events.ProactorEventLoop
SIGINT handler BEFORE install: functools.partial(<bound method Runner._on_sigint of asyncio.runners.Runner object ...>)
SIGINT handler AFTER install : <function setup_signal_handlers.<locals>.<lambda> at 0x...26122A0>
displaced the runtime's own  : True
after FIRST fire             : is_set=True
after SECOND fire            : is_set=True
second fire changed anything : False
SIGINT handler AFTER cleanup : <function setup_signal_handlers.<locals>.<lambda> at 0x...26122A0>
restored to pre-install?     : False
SIGTERM handler AFTER cleanup: <function setup_signal_handlers.<locals>.<lambda> at 0x...26120C0>
restored to pre-install?     : False
```

R5 leg — executed, **positive**. `uv run python .temp/audit04/r5_stop_reach.py`:
```
=== R5(i) blocked read of a silent child's output ===
  lines consumed before the stop : 1 [b'line one\r\n']
  reader returned after the stop : False (still blocked 3.0s after the stop)
  shutdown hook invoked          : False
  child returncode               : None (None = still running)
  child still alive?             : True
  reader returned only after the child was killed: True
=== R5(iii) the claim under a set stop state ===
  one unit  : one unit claimed and released
  second claim done while the stop is set : False
  semaphore waiters queued                : 1
  two units : the second claim NEVER returned (stop set; 3s bound expired)
```
All three legs executed. The R1 leg shows the primitive is **not** the cause;
the severity comes from the R4 and R5 legs, which meet the CRITICAL condition
directly (stop requested, never observed by the work it is meant to stop, no
bound, no repeat interrupt that changes it).

**Baseline in which this was observed (R8):** `244 passed, 2 skipped`;
`ruff check` exit 0; `ruff format --check` exit 0; `mypy` exit 0
(`Success: no issues found in 17 source files`). Coverage declaration: the
existing signal tests replace `signal.signal` wholesale
(`tests/test_hls_downloader.py:2655`, `:2686`), so no test in the tree can
observe what cleanup removed; `iter_process_lines` has 7 references.

**Recommendation:** make the stop observable *while* a read is in flight — race
the read against the shutdown event so `on_shutdown` runs while the reader is
blocked, not after it returns. Make the second interrupt escalate (forward to
the displaced handler or force-kill the child), and restore the previously
installed process-level handler in `cleanup_signal_handlers` on the branch that
actually runs on Windows. The correlation-id shadowing at `downloader.py:663-664`
is cross-referenced to ENT-012 and the registration *placement* to ENT-004;
neither is filed here.

---

### CON-002: The shipped condition that reaches the per-part transfer from inside the outer claim is not executed — `UNVERIFIED`

| Field | Value |
|-------|-------|
| **ID** | CON-002 |
| **Severity** | *none — not executed* |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

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
  inner2 IS outer2 wrapper?      : False
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

---

### CON-003: Work items are created without a bound — one task per missing part, and one task per URL

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

**Evidence (R3, R3b).** `uv run python .temp/audit04/r3_completion.py`:
```
=== R3(d) 5000 items under a claim of 4 ===
  claim ceiling           : 4
  items missing           : 5000
  tasks created up front  : 5000
  live tasks before any completed: 5000
  semaphore waiters queued       : 0
```
`uv run python .temp/audit04/r3b_batch_tasks.py` (batch runner driven with a
stubbed worker; `settings.max_concurrent_downloads` default 4):
```
  urls=   100  live tasks created up front=   100
  urls=  1000  live tasks created up front=  1000
  urls= 10000  live tasks created up front= 10000
```

**Recommendation:** keep the item count bounded by feeding the factory from a
worker pool or a bounded queue instead of materialising the whole list, so the
configured ceiling is the only thing that determines how much work is in flight.

---

### CON-004: The browser handle is never released on the stop path

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
of the two acquired resources is given back.

**Exact consequence:** interrupting a browser-backed extraction skips
`browser.close()` entirely. The `extractor` raises `CancelledError` immediately
after the stop check (`extractor.py:282-285`), so the skip is the normal path,
not a rare one: the launched browser, and everything inside it, is left running
for the remainder of the process while the driver is asked to stop.

**Evidence (R7).** `uv run python .temp/audit04/r7_teardown.py` — the manager is
constructed without entering it and stand-ins are assigned, so no browser is
launched:
```
=== R7(d) stop state already set ===
  trace        : ['playwright.stop:start', 'playwright.stop:done']
  browser.close invoked: False
  driver stopped      : True
```
For contrast, case (a) with the stop unset shows both steps in reverse
acquisition order:
```
  trace        : ['browser.close:start', 'browser.close:done', 'playwright.stop:start', 'playwright.stop:done']
```
Case (b) also shows a second, related fact: when the close exceeds its bound it
is *cancelled*, not retried — `['browser.close:start',
'browser.close:CANCELLED-by-wait_for', 'playwright.stop:start',
'playwright.stop:done']`, elapsed 1.00s against a production bound of 10.0s per
step. Whether the driver completes its own teardown after that cancellation is a
documented skip (see Skips).

**Recommendation:** release unconditionally. The reason the guard exists —
avoiding a slow close during shutdown — is already served by the 10s
`asyncio.wait_for` bound on the same call; drop `and not shutdown_event.is_set()`
so a stop shortens the close rather than skipping it.

---
### CON-005: A failing browser release replaces the failure that caused the exit

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

**Evidence (R7 case c).** `uv run python .temp/audit04/r7_teardown.py`, with a
`ValueError` in flight from the body:
```
=== R7(c) close raising a non-timeout error, with an exception in flight ===
  escaped exception: RuntimeError: driver exploded
  the in-flight body exception survived: False
  trace        : ['browser.close:start', 'browser.close:raised', 'playwright.stop:start', 'playwright.stop:done']
```

**Recommendation:** catch `BaseException` around each release step, log it with
the reason the step failed, and suppress it when an exception is already in
flight. The `finally` at `browser.py:84` already guarantees the second step
runs; the same guarantee is needed for the first step's own failure.

---

### CON-006: The completion helper returns the same value for "nothing to do" and "cancelled", so a fully resumed download never merges and is reported as failed

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

**Evidence (R3 case a).** `uv run python .temp/audit04/r3_completion.py`, all
three segments written to disk beforehand:
```
=== R3(a) empty item list ===
  _await_and_cancel([]) -> None   (None means both 'cancelled' and 'nothing to do')
  every segment already present -> task factory produced 0 tasks
  _process_downloaded_segments -> None  (merge never reached)
  _await_and_cancel(<genuinely cancelled>) -> None  <- identical value
```

**Recommendation:** separate the two outcomes. Return an empty result list for
"nothing to do" and keep `None` for cancellation only, so the consumer can reach
the merge in the resume case. The surrounding `_await_and_cancel` name already
promises a list on success and `None` on cancellation in its own docstring
(`segment_downloader.py:555`).

---

### CON-007: A raising part orphans every sibling part

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
finished, and keep retrying against the origin after a stop was requested.

**Evidence (R3 case b).** `uv run python .temp/audit04/r3_completion.py`, three
parts where the second raises:
```
  raised out of the helper: RuntimeError: boom
  order recorded inside tasks: ['item1 raised']
  sibling states IMMEDIATELY after the raise:
    task[0] <Task pending ... wait_for=<Future pending cb=[Task.task_wakeup()]> cb=[gather.<locals>._done_callback()]>
    task[1] <Task finished ... exception=RuntimeError('boom')>
    task[2] <Task pending ... wait_for=<Future pending cb=[Task.task_wakeup()]> cb=[gather.<locals>._done_callback()]>
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

**Evidence (R3 case c).** `uv run python .temp/audit04/r3_completion.py`, three
parts cancelled while running, with the holder task cancelled externally:
```
=== R3(c) three items cancelled while running ===
  order: ['cancelling the holder task', 'item0 observed cancel', 'item1 observed cancel', 'item2 observed cancel', 'holder returned normally: None']
  holder task after completion: <Task finished name='Task-11' coro=<_await_and_cancel() done, defined in C:\py_exp\mko_vkideo\src\vkdownloader\services\segment_downloader.py:546> result=None>
```
The stop state was never set in this probe, yet the helper logged
`download_cancelled reason="shutdown_requested"` immediately above the output.

**Recommendation:** re-raise `CancelledError` after the siblings are settled, and
log `reason="cancelled"` for that path, reserving `shutdown_requested` for the
case where the stop state is actually set.

---

### CON-009: The transport's pool ceiling is a literal that the declared setting does not imply, and the per-origin ceiling is unset

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

**Evidence (R6 c, d).** `uv run python .temp/audit04/r6_ceilings.py`:
```
  max_concurrent_downloads= 4 ssl_verify=True  -> limit=10 limit_per_host=0
  max_concurrent_downloads= 4 ssl_verify=False -> limit=10 limit_per_host=0
  max_concurrent_downloads=16 ssl_verify=True  -> limit=10 limit_per_host=0
  max_concurrent_downloads=16 ssl_verify=False -> limit=10 limit_per_host=0
  declared setting bound: [Ge(ge=1), Le(le=16)] default=4
  download sessions driven            : 5
  aiohttp sessions/connectors created : 5
  connectors per unit                : 1.0
  max_concurrent_downloads= 4: videos in flight=4, segment permits=4x4 units=16 transfers, TCP connections=10x4 units=40
  max_concurrent_downloads=16: videos in flight=16, segment permits=16x16 units=256 transfers, TCP connections=10x16 units=160
```

**Recommendation:** derive `limit` from `settings.max_concurrent_downloads` and
set an explicit `limit_per_host`, so one setting governs the whole process
rather than each unit re-interpreting it. This phase files the literal only; the
resulting request *rate* against one origin belongs to phase `03`.

---

### CON-010: An abandoned off-loop extraction holds the process for up to the interpreter's thread-join constant after the reported bound has fired

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
thread-join constant after the error is reported.

**Evidence (R5 ii).** `uv run python .temp/audit04/r5_stop_reach.py`, a blocking
call of 30 s behind the same 1 s bound shape:
```
  interpreter thread-join constant: constants.THREAD_JOIN_TIMEOUT = 300
  bound fired at t+1.0s (the shape at extractor.py:242-245)
  returning from the coroutine with the thread still running
  asyncio.run returned after 30.0s with the executor thread still alive
```
The 30.0 s is the abandoned thread's own remaining lifetime; the cap is the 300 s
constant.

**Recommendation:** state the exit-path bound where the timeout is configured,
and lower it for this call site — the extraction has already been declared failed
at that point, so joining it for five more minutes serves nothing.

---
## Documented Skips

Each of these was named in the phase and **not** run. They are recorded so their
absence is never read as a clean result.

| # | Skipped subject | Justification |
|---|---|---|
| S-1 | Real console delivery of a key press to a running process | Delivery belongs to the console, not to the code. The installed handler was captured by identity and invoked twice programmatically; its behaviour once invoked was executed (R4). |
| S-2 | Whether a browser driver completes its own teardown after a timeout | The driver is a third-party object and was never launched. `BrowserManager` was constructed without entering it and driven against stand-ins (R7). |
| S-3 | Whether a child writing more than its output buffer holds blocks | No product child was spawned. This is phase `05`'s subject — named, not run. |
| S-4 | The production condition that reaches the per-part transfer from inside the outer claim | Not executed by design. Filed as **CON-002**, marked `UNVERIFIED`, with no severity — not a skip-with-silence. |

## Cross-References (not filed here)

| Subject | Owner |
|---|---|
| Placement of the interrupt-handler registration (command layer for `download`, service module for `batch`) | ENT-004, phase `01` |
| Correlation-id regeneration and clearing at `downloader.py:663-664` | ENT-012, phase `01` |
| `clear_correlation_id()` clearing the whole structlog context | ENT-011, phase `01` |
| Meaning, bound and validation of `max_concurrent_downloads` / `download_timeout` | CFG-002, phase `02` |
| Neighbouring summary label `Total connections` (counts result tuples, not transfers) — observed verbatim in R6(a) | phase `08` |
| Effective request rate against one origin (the product in CON-009) | phase `03` |
| Certificate-verification policy built by the same constructor | phase `03` |
| Child-process argument vector, pipe wiring, kill escalation, exit-status interpretation | phase `05` |
| Residue on disk after a stop (preserved parts, hidden working directories) | phase `07` |
| Test-suite adequacy for every subject above | phase `10` |

## Verification Baseline (R8) — cited as the state findings were observed in, not filed as findings

| Command | Result |
|---|---|
| `uv run pytest tests/test_batch_downloader.py tests/test_segment_downloader.py tests/test_downloader_throttle.py tests/test_downloader.py tests/test_ffmpeg_utils.py tests/test_browser_infrastructure.py tests/test_hls_downloader.py -q` | `244 passed, 2 skipped in 19.93s` (exit 0) |
| `uv run ruff check src/vkdownloader/services src/vkdownloader/infrastructure src/vkdownloader/cli.py` | `All checks passed!` (exit 0) |
| `uv run ruff format --check src/vkdownloader/services src/vkdownloader/infrastructure src/vkdownloader/cli.py` | `17 files already formatted` (exit 0) |
| `uv run mypy src/vkdownloader/services src/vkdownloader/infrastructure src/vkdownloader/cli.py` | `Success: no issues found in 17 source files` (exit 0) |

**Coverage declaration** (searched over `tests/`, excluding worktree directories;
every subject below was declared before it was checked):

| Symbol | Matches | Declared |
|---|---|---|
| `_TrackedSemaphore` | 0 | **uncovered** — the primitive wrapper that produces the reported peak |
| `_await_and_cancel` | 0 | **uncovered** — the completion helper (CON-006, CON-007, CON-008) |
| `_create_segment_download_tasks` | 0 | **uncovered** — the task factory (CON-003, CON-006) |
| `_process_downloaded_segments` | 0 | **uncovered** |
| `_semaphore_context` | 0 | **uncovered** |
| `ConcurrencyTracker` | 2 | covered |
| `_download_single` | 2 | covered |
| `_run_batch_with_progress` | 5 | covered |
| `iter_process_lines` | 7 | covered (see CON-001: covered but does not observe the blocked-read case) |
| `run_batch` | 8 | covered |
| `_print_batch_summary` | 10 | covered |
| `setup_signal_handlers` / `cleanup_signal_handlers` | 6 / 4 | covered, but `tests/test_hls_downloader.py:2655` and `:2686` replace `signal.signal` wholesale, so nothing in the tree can observe what cleanup removed |
| `get_shutdown_event` | 16 | covered |
| `BrowserManager` | 23 | covered |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 3 |
| MEDIUM | 5 |
| LOW | 0 |
| none (`UNVERIFIED`, not executed) | 1 |

## Mandatory Fixes

| ID | One line |
|---|---|
| CON-001 | Make the stop observable while a child's output read is in flight; make a second interrupt escalate; restore the displaced process-level handler on the branch that runs on Windows. |
| CON-002 | Execute the D-01 production condition once, or amend the register — currently a CRITICAL claim that this code does not reproduce. |
| CON-003 | Bound the number of work items created, at both the segment and the batch layer. |
| CON-004 | Release the browser handle on the stop path instead of skipping it. |
| CON-005 | Stop a failing release from replacing the failure that caused the exit. |
| CON-006 | Distinguish "nothing to do" from "cancelled" in the completion helper so a complete resume merges. |
| CON-007 | Settle sibling part tasks when one part raises. |
| CON-008 | Re-raise the cancellation instead of absorbing it, and stop logging a shutdown that did not happen. |

## Advisory Recommendations

| ID | One line |
|---|---|
| CON-009 | Derive the transport pool ceiling from the setting and set an explicit per-origin ceiling. |
| CON-010 | State and lower the exit-path bound for abandoned off-loop extraction work. |

## Doc Updates Needed

None. This phase files no `DOC-UPDATE`: the wording of `.ai/problems/01-confirmed-code-defects.md`
is `09`'s subject; only its runtime behaviour is recorded here, in CON-002.
