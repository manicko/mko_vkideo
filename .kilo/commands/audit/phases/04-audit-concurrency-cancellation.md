---
name: 04-concurrency-cancellation
status: draft
validated: no
executor: auditor
problems-only: true
---

# 04 — Concurrency and Cancellation

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — the decision's own anchor for this subject is stale, and is
> recorded here rather than contradicted silently.** It describes the nested-claim
> shape as structurally verified with its runtime consequence unverified, and
> repeats that as a warning. **That is superseded for the shape and stands for
> the trigger.** The production trigger has not been executed at all. Reading the
> anchor as covering both is how the highest-severity check in this phase gets
> skipped.
>
> **Binding rule 2 — the highest-severity check here is offline, and "requires
> network" is forbidden.** The claim, the completion and the cancellation subjects
> are the **most** executable subjects in the catalogue, not the least. R1, R3, R4
> and R5 need `asyncio`, a temporary directory and the production objects — no
> socket, no service, no binary, no child process, no third-party package. It is
> forbidden to record the nested-claim shape as requiring a network, a live
> origin, a binary, or otherwise being irreproducible offline, and forbidden to
> skip it at execution time for any such reason. If a method cannot say how, the
> method is wrong — not the subject.
>
> **Binding rule 3 — the reproduced shape is the claim subject, and the run
> produces it.** Whether concurrent acquisition serialises work, whether a second
> stop changes anything, and whether any kind of work observes the stop while it
> is running, are one claim with three legs. **The legs are questions, not
> answers: R1, R4 and R5 produce the evidence, and nothing in this file states
> what they will show.** The claim is filed once, after the run, and the severity
> is composed from what the run observed — the missing leg is named, never
> assumed. *The decision document's own characterisation of the subject is not
> citable as a severity.*
>
> - **The subject is exactly two findings, never one and never zero.** The
>   reproduced shape is the first, its severity composed from the run's own R1, R4
>   and R5 evidence. The **production trigger** — the shipped condition that
>   reaches the inner claim from inside the outer one — is the second, carrying
>   the structural fact, the literal marker **`UNVERIFIED`**, and a severity band
>   composed from that structural fact under **this phase's own `## 9` table** —
>   the rule the report template states, and the table this phase's own `LOW` row
>   already applies. It is not executed by design, is not asserted as fact
>   anywhere in this file, and may not be.
> - **The two are never merged.** One finding would apply the reproduced part's
>   severity to the unexecuted part, which the admissibility rule forbids.
> - **Silence is not available.** Under `problems-only`, an omitted finding reads
>   as "no finding". The reproduced shape is filed even if the trigger route is
>   never attempted; the trigger is filed even if the route is attempted and the
>   attempt is inconclusive. The attempt changes only the marker.
> - **No severity the run did not observe.** A severity assigned from the code's
>   shape with no `R1`–`Rn` output behind it is inadmissible — read as *a band no
>   observed output supports*, not as *a band read off an observed structural
>   fact*. Where the run recorded the structural fact and did not record its
>   consequence, the band is composed from `## 9`'s own `LOW` row — *"A shape,
>   naming or structure deviation with no runtime consequence"* — and so is
>   composing this subject into a single finding, and so is composing it into
>   none.

## 1. Goal

Who holds a concurrency permit, how cancellation propagates and unwinds, and what work cannot actually be stopped.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| The limiting primitive | Its creation, its holders, its claims per path, the span a claim covers | The same object claimed twice on one path; a claim held across a slow stage; a claim no stop or deadline can release |
| Completion and cancellation | Creating work in bulk, iterating for it, gathering it, one outcome per item | A raising item orphaning its siblings; a value meaning both "cancelled" and "nothing to do"; work created without a bound |
| Stop delivery | Signal installation, the state it sets, that state's identity and lifetime | A handler that is not removed; a displaced runtime handler; a second stop that changes nothing; a stop indistinguishable from failure |
| Stop reach | Whether each kind of work observes the stop while it is in flight | A blocked read released only by output arriving; off-loop work outliving its own bound; a process outliving the timeout it reported |
| Release | Order, bounds and exception safety of everything given back | A release skipped on the stop path; a release that replaces the failure that caused the exit; an unbounded release |
| Ceilings | The number reported to the operator and the number the transport enforces | A figure counting claims and named as transfers; a literal overriding a bounded setting; a per-origin ceiling derived from neither |

**In scope:**
- Semaphore creation, ownership, propagation and **acquisition count** on every path that reaches it, including whether the same object is acquired more than once (the primitive is not reentrant).
- Accuracy of peak-concurrency accounting.
- The connection-pool ceiling at the transport layer versus the configured ceiling; hardcoded literals overriding a bounded setting.
- Task creation, completion iteration and result gathering; the interaction between the two; exception normalisation into per-item outcomes.
- `CancelledError` fan-out, cancel-then-gather, and re-raise.
- Signal registration (with its platform fallback), the shutdown event held in a context variable, and **whether that state is visible outside the loop**; handler deregistration and re-registration on a later loop.
- Teardown ordering and timeouts for every resource torn down on shutdown.
- **Work that is abandoned rather than stopped** — a blocking call in an executor thread whose await is cancelled while the thread continues, **and the bound that places on the process's remaining lifetime.**
- **Bounded teardown of the browser context and its driver** — *release only*: whether release is reached on the stop path, the order of release, and whether a release replaces the failure that caused the exit. (Setup is `05`'s — see `## 7. Cross-Cutting`.)

**Out of scope:** the kill escalation of an OS child → `05`; the policy of *why* to back off → `03`; residue left on disk after cancellation → `07`; the exit code derived from the outcome → `08`. Additionally: the browser's configuration and setup → `05`; certificate-verification policy and the effective request rate against one origin → `03`; the summary's rendering and labels → `08`; a setting's meaning, bound and validation → `02`; a documented claim → `09`; a file's permission mode, atomicity and cleanup → `07`; dead code → `99`'s rule, `10`/`09`'s code side.

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` (from `.ai/context/commands.md`). `mypy` (strict) is the configured checker; a second checker present in the dev dependency group is **not** it — do not substitute it.
- **No Docker. No database. No third-party origin. No service is started. This phase is executable entirely offline.** Its real prerequisites are two substitution primitives and a temporary directory:
  1. **A network stub at the session boundary** — an object exposing the session's `get`, returning an async context manager that yields a scripted `(status, headers, body)`, plus a fixed in-memory manifest. Used by R2 only, to establish *reachability*. The genuine production condition is not executed and is carried as `UNVERIFIED`.
  2. **Stand-ins for two third-party objects** — a browser handle and a driver for R7, each exposing a coroutine that can complete, time out, or raise on demand. **No browser is launched and no driver is started.**
  3. A **temporary directory** for R2, R3(d) and R6.
- One probe (R5(i)) launches **the project's own interpreter** with a fixed two-line script, so that "a child that emits one line and then goes silent" exists. It is not a product child process, needs no binary on `PATH`, and does no network. **No probe launches the media tool, the third-party downloader, or a browser.**
- The declared development platform is Windows; see the platform note in `## 5`.
- **Documented skips — each must appear in the report, never as silence** (under `problems-only`, silence reads as "no finding"):
  - *Real console delivery of a key press to a running process.* R4 invokes the installed handler programmatically. Delivery belongs to the console, not to the code; the handler's behaviour **once invoked** is executed.
  - *Whether a browser driver completes its own teardown after a timeout.* The driver is a third-party object and is never launched here.
  - *Whether a child writing more than its output buffer holds blocks.* No product child is spawned; that is `05`'s subject — named, not run.
  - *The production condition that reaches the per-part transfer from inside the outer claim.* R2 establishes that the **path** is reachable with the media method replaced. The condition itself is not executed by design and is carried as a finding marked `UNVERIFIED` — not as a skip, and never with a severity the run did not observe. Its band is composed from the structural fact under `## 9`.

## 4. Discovery

Map the architecture before checking anything. **Use roles, not names.** Never reference a concrete file, module, or class name in this file.

1. **Primitive map** — where the limiting primitive is created, who holds a reference to it, every site that claims it, and which object each holder actually has.
2. **Path map** — every path that reaches the guarded work, and with what claim; the fallback paths that re-enter the same work from inside a claim already held.
3. **Work-unit map** — every kind of work the process performs, and which of them can outlive a stop request.
4. **Release map** — every resource acquired, in acquisition order, and the step that gives it back.
5. **State map** — every piece of state that outlives a single unit of work: the stop state, the registration record, the measured-peak record, the per-item outcome labels.
6. **Evidence map** — the test tree's reach into these subjects, searched **excluding every worktree directory**, whose stale copy of an earlier phase set will otherwise be searched by accident. A subject with no match is declared uncovered **before** it is checked, not after.

*Role vocabulary:* the primitive that limits how much work runs at once · the wrapper that tracks the measured peak · the per-unit context helper that yields a no-op claim when none is supplied · the part-fetching worker that claims the primitive · the task factory that creates one task per missing part · the completion helper that gathers and cancels · the batch runner that creates one primitive per run and shares it · the result normaliser that maps each item to a label · the summary renderer · the transport connector factory · the line-reading helper for a child's output · the kill escalation ladder · the browser context manager's exit path · the dispatch entry point that installs and removes the signal handler · the context-variable holder of the stop state.

## 5. Runtime Verification (mandatory)

**Run before evaluating any dimension.**

> **Every method below is offline and executable in this process.** No method contacts a third-party origin, starts a service, or requires a database, a container, a network, a product child process, a browser, or a third-party binary. The substitutions are the two stand-in objects in `## 3`; the single process ever launched is the project's own interpreter for a fixed two-line script.
>
> **The claim, completion and cancellation subjects sit entirely inside that envelope.** R1 needs nothing but `asyncio` and the production objects. **Run them here and record this phase's own output. Do not defer, and do not record "requires network" against any of them.**

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | The limiting primitive: identity, claims per path, nested claim, claim span, reported peak | Drive the production wrapper, the production peak tracker, the production per-unit context helper and the production completion helper inside a bare `asyncio.run`, replacing the transfer with a short sleep. Run the grid: (ceiling = declared default, units = ceiling, parts = 2), (ceiling = 1, units = 1, parts = 1), (ceiling = default, units = 1, parts = ceiling), (ceiling = declared maximum, units = 3, parts = 2). Bound each row with a three-second wait; record completed-or-not, the reported peak, permits free, waiter count. Then repeat with a slow stage (a sleep standing in for a page load) inserted inside the outer claim, and record how many units entered it at a ceiling of 4 and at 16. | Completion state per row; peak, free permits and waiter count per row; units entering the slow stage at each ceiling; claims made by one unit on each path. |
| R2 | The nested claim is reachable in the shipped code | With the network stubbed at the session boundary only, drive the shipped code down each of the two paths by which the per-part transfer is reached from inside an outer claim: (i) the media method returning no result; (ii) the downloader exiting with a non-empty partial file present. Where the per-part transfer policy is built, capture the primitive it received, compare it **by identity** with the one handed to the outer claim, and record the shared flag the policy stores. Do not modify production code; substitute only the session and the media-method result. | The identity comparison on each path; the shared-flag value on each path; the outer object's identity. |
| R3 | Completion, cancellation, empty input, per-item outcomes | Four cases against the shipped completion helper: (a) an empty item list — record the returned value; (b) three items where the second raises — record the state of the other two immediately after the raise; (c) three items cancelled while running — record the order of cancel and await, and whether the cancellation is re-raised; (d) a synthetic list of 5 000 items under a claim of 4 — record live task count and waiter count before any item completes. Then feed one results list containing success, a domain failure, an unexpected exception and a cancellation into the result normaliser, and record the label produced for each. | Returned value for the empty list; sibling states in (b); recorded order and the re-raise in (c); live task and waiter counts in (d); label per outcome. |
| R4 | The stop signal: installed path, removal, displacement, second fire, state identity, stop-vs-failure | Inside one `asyncio.run`: record the loop class and whether loop-level signal registration is supported; read the process-level interrupt handler **before** installing; install; read it again; invoke the captured handler once and record what changed; invoke it a second time and record what changed; run the cleanup; read the handler again and the registration record. Separately: set the stop state inside `asyncio.run`, read it after `asyncio.run` returns, compare identity. Separately: drive each of the two entry points with a worker that observes the stop and returns no result, and record the outcome and the process status each produces. | Loop class and whether loop-level registration was used; handler identity at all four points; effect of the first and second invocation; identity across the run boundary; outcome and status per entry point. |
| R5 | Whether a stop reaches each kind of work | Three sub-probes. (i) Launch the project's own interpreter with a fixed script that prints one line then sleeps; consume its output through the shipped line-reading helper until it blocks; set the stop state; after three seconds record whether the reader returned, whether the shutdown hook ran, and the child's exit status. (ii) Dispatch a blocking call to the default executor through a bounded await, let the bound fire, and time how long the enclosing run takes to return; record the interpreter's thread-join constant. (iii) Set the stop state, then attempt to claim the limiting primitive from one unit and from two, and record whether the claim returns. | (i) reader returned or not, hook invoked or not, child exit status; (ii) elapsed time from the bound firing to the run returning, and the constant; (iii) whether the claim returns with the stop set. |
| R6 | The reported number and the enforced ceiling | (a) Call the summary renderer **directly** with a synthetic results list and a synthetic peak value, and capture the emitted text verbatim — the figure needs no run, no process and no network. (b) Read the reported peak from R1 and compare it with the largest number of units in flight in the same row. (c) Construct the transport connector once with verification on and once off; read the total ceiling and the per-origin ceiling from each, with the setting at its default and at its declared maximum. (d) Count the connectors one unit creates by instrumenting the construction call, and compute the product. | Emitted summary text; reported peak against observed in-flight maximum; both ceilings at both settings; connector count per unit and the computed product. |
| R7 | Teardown: order, bounds, exception safety | Construct the browser manager **without entering it** and assign stand-ins for the browser handle and the driver, so no browser is launched. Call the exit path four times: (a) stop state unset, close completing; (b) close exceeding the bound; (c) close raising a non-timeout error, with an exception in flight; (d) stop state already set. Record which steps ran, which were skipped, which exception escaped. Then read the release order of the other two resource classes and of the reporting surface, and compare it with their acquisition order. | Per case: steps run, steps skipped, exception that escaped; release order per resource class against acquisition order; each release bound. |
| R8 | Baselines, coverage declaration, platform note | (a) Run the four verification commands from `## 3` over this phase's surface; record exit codes, pass/fail/skip counts and skip reasons. **Do not substitute any other type checker.** (b) Search the test tree — **excluding every worktree directory** — for the primitive wrapper, the peak tracker, the completion helper, the task factory, the batch runner and the signal setup; print the match count per symbol. **Every subject with a count of zero is declared uncovered before it is checked.** (c) Write the platform note. | The four exit codes and outputs; the skip reasons; the per-symbol match counts; the platform note text. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how to obtain its evidence is rewritten here, not skipped at execution time.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.**

*Baselines, not findings:* R8's results are **never** filed as findings. They are cited as the state in which an R1–R7 finding was observed. A zero match count is a statement about the evidence base, and the absence of coverage is `10`'s subject — the one exception is the displaced-runtime-handler observation in R4, which is a runtime observation in its own right and is filed here.

*Documented skips:* a named method that cannot be run is emitted as a **documented skip with justification — never silence**. A silent skip reads under `problems-only` as "no finding". A skip never closes the check it belongs to.

> **Platform note (mandatory — this phase touches signals).** The declared
> development platform is Windows, where loop-level signal registration is
> available on only some loop implementations, so the shipped code takes its
> process-level interrupt path. **The non-Windows evidence method is the
> read-back:** capture the process-level interrupt handler **by identity** at
> four points — before install, after install, after the cleanup call, and after
> the enclosing run returns — and invoke the captured handler twice
> programmatically, recording what changed each time. Delivery of a real key
> press belongs to the console rather than to the code and is a documented skip
> with justification; the handler's behaviour once invoked is executed. The
> existing signal test replaces the process-level registration call wholesale,
> so it cannot observe what cleanup did or did not remove and **must not be
> relied on by any method in this phase.**
>
> **This note is scoped to registration *reachability* only.** It does not
> audit *where* the registration is placed, whether the process wires it at
> bootstrap, or the form of any bootstrap ordering — that is `01`'s by R-D. It
> does not audit the transport's own platform-conditional policy or a
> platform-specific connection ceiling semantics — that is `03`'s.

## 6. Audit Dimensions (checks + evidence)

### (a) One Claim, Many Claims

> One primitive limits how much work runs at once. Find where it is created, who holds a reference to it, and every site that claims it. For each path, count the claims **one unit of work** makes — not how many units exist — and record whether a claim is nested inside another claim on the same object. Then record the span between claiming and releasing, and everything that runs inside it. A primitive claimed twice on one path is the first subject; a primitive held across a slow stage is the second.

| Check | Description | Evidence required |
|---|---|---|
| One object, not several | Every holder is confirmed to hold the **same** object, by identity, not by equal configuration | R1 |
| One claim per path, counted | Per path, the claims a single unit of work makes are counted and recorded | R1 |
| No claim nested on one object | No path claims a primitive it, or a descendant, already holds. **The reproduction is the evidence; the structure is not** | R1, R2 |
| The nested claim is reachable in the shipped code | At least one shipped path is shown, by object identity, to reach the inner claim from inside the outer one | R2 |
| Nothing reaches the guarded work unclaimed | Every path performing the guarded work is listed, and each reaches it with a claim or declares itself unbounded | R1 |
| The claim is not bound by a stop or a deadline | Whether a claim consults the stop state, and whether any bound wraps it, is recorded. A deadline bounding sockets but not claims is the finding | R1, R5 |
| The claim's span matches what it is named | The span the claim covers is compared with the name of the setting it is bound to and with what the operator is told it limits | R1, R6 |

- Evidence: R1, R2, R5, R6.

### (b) A Stop That Never Reaches the Work

> A stop is a request, not a cancellation. For every kind of work the process performs — a network read, a read of a child's output, a blocking call on a worker thread, a wait for a claim — ask three questions: is the stop state consulted **while the work is in flight**; is there a bound on how long the work may ignore it; and what does the process do after the work is abandoned. Measure the elapsed time from setting the stop to the first observable reaction. Work that can finish only when the process is destroyed is the finding.

| Check | Description | Evidence required |
|---|---|---|
| Every kind of work is enumerated | The kinds of work that can outlive a stop request are listed first; that list is the denominator for the rows below | R5 |
| Stop is consulted in flight | Each kind of work is observed to consult the stop while running, not only before it starts | R5 |
| A blocked read is released | A read waiting on a child's output is observed to return when the stop is set, and the process-side kill is observed to run | R5 |
| The kill does not depend on output arriving | No step required to release a blocked read is reachable only after that read produces something | R5 |
| Off-loop work is bounded in lifetime | A blocking call dispatched to a worker thread is observed to end, and the time from its abandoned await until the run actually returns is measured against the interpreter's thread-join constant | R5 |
| The exit path is a bound, not a hope | Where a unit of work is abandoned, the bound on the process's remaining lifetime is recorded and compared with the bound the operator was shown | R5 |

- Evidence: R5.

### (c) The Stop Signal and the State It Sets

> A signal becomes state, and that state is read in several places. Record who installs the handler, on which platform path it actually takes, what the handler does when it fires more than once, and whether the state it sets is the same object everywhere it is read — including outside the run that created it, and including the handler the runtime had installed before the process touched it. Then record whether removing the handler removes it, and whether a stop is distinguishable from an ordinary failure at each entry point.

| Check | Description | Evidence required |
|---|---|---|
| The installed path is the one that runs | The platform path actually taken on the declared platform is observed, not inferred from intent, and the identity of the handler the runtime had installed beforehand is captured | R4 |
| Removal is observed, not asserted | After cleanup, the process-level handler is read back and compared by identity with its state before installation | R4 |
| A displaced runtime handler is restored | Where installing replaced a handler the runtime had installed, cleanup is observed to restore it. **A runtime safety mechanism left displaced is the finding, and it is the executed second leg of the severity composition** | R4 |
| A second stop is not a no-op | Firing the captured handler a second time is observed to change the process. A no-op is the finding | R4 |
| One state, one identity | The stop state read inside the run and the state read after it returns are compared by identity. A different object is the finding | R4 |
| Clearing is defined | Whether anything clears the stop state between units of work or between runs is recorded, and the consequence of its never being cleared is stated | R4 |
| Stop is distinguishable from failure | At each entry point, a stopped run is observed to produce an outcome distinguishable from an ordinary failure. Where one entry point has the translation and another does not, the asymmetry is the finding | R4 |
| A registration record is not state that outlives the command | A module-level record of what is registered, mutated by more than one entry point, is recorded **only** with an observable consequence; otherwise it is a cross-reference to `01`, not a finding here | R4 |

- Evidence: R4.

### (d) Completion, Cancellation and Per-Item Outcomes

> Work is created in bulk, iterated for completion, gathered, and mapped to one outcome per item. For each of those four steps, record what happens when a sibling raises, when the run is cancelled, when there is nothing to do, and when the input list is large. A return value that means more than one thing is a finding at every place it is consumed, and only where the meanings collide.

| Check | Description | Evidence required |
|---|---|---|
| One outcome per item | Every input item ends with exactly one outcome, index-aligned with the input list | R3 |
| A raising item does not orphan its siblings | When one item raises, the state of every other item is observed immediately after the raise. Items left neither cancelled nor awaited are the finding | R3 |
| Cancellation reaches the items and is re-raised | On cancellation the items are cancelled and awaited before the cancellation is re-raised; the observed order is the evidence, not the code's shape | R3 |
| Empty is not cancelled | The completion step's return value is recorded for an empty item list, and its consumer is checked to distinguish it from the cancellation value | R3 |
| Work is created under a bound | The live items created up front are recorded against the number permitted to run at once. A claim bounding requests but not items is the finding — filed **only** with a measured count, never as a structure-only claim | R3, R1 |
| Completion iteration does not wrap twice | The iteration helper is checked to consume the tasks it is given without wrapping each in a second task; the wrappers are observed on the cancellation path | R3 |
| Per-item normalisation is total | Every failure mode an item can produce maps to a label its consumer recognises, and no label is produced by exactly one layer | R3 |

- Evidence: R1, R3.

### (e) Teardown: Order, Bounds, Exception Safety

> Every resource the process holds is given back on the way out — the browser context and its driver, each child process, each temporary file, each reporting surface. For each, record the order of release against the order of acquisition, the bound on each step, and what happens when a step times out or raises. A release skipped on the very path it exists for, and a release whose exception replaces the failure that caused the exit, are both findings.

| Check | Description | Evidence required |
|---|---|---|
| Reverse order | Release order is the reverse of acquisition order for every resource, observed rather than inferred | R7 |
| Every exit path releases | Success, failure, cancellation, and an exception raised inside the body are each exercised; release is observed to run on all four | R7 |
| Release is not skipped by the stop | Whether a release step is conditioned on the stop state **not** being set is recorded. A release skipped on the stop path is the finding | R7 |
| A timed-out release still releases the rest | When one release step times out, the remaining release steps are observed to run | R7 |
| A failing release does not mask the failure | When a release step raises while another failure is in flight, the in-flight exception is observed to survive. The replacement is the finding | R7 |
| Bounds are stated and comparable | Each release bound is recorded and compared with the bound the rest of the process is given. An unbounded release is a finding | R7 |

- Evidence: R7.

### (f) The Ceiling Reported and the Ceiling Enforced

> The operator is shown a number, and a transport enforces a different one. Record what the reported number counts by feeding it a known result set. Then record the largest number of simultaneous requests one unit can actually make, and the number the declared process-wide setting implies. Where the reported number counts claims rather than transfers, or the transport's ceiling is a literal, each is a finding — filed as a number whose meaning is wrong, never as a style observation about a literal.

| Check | Description | Evidence required |
|---|---|---|
| The reported figure is measured, not assumed | The reported number is compared against the largest number of units actually in flight under the same conditions | R1, R6 |
| Labels match what is counted | Each reported label is checked against the quantity its name denotes. A label over a different quantity is the finding | R6 |
| The enforced ceiling is the declared one | The transport's per-unit ceiling is compared with the declared process-wide ceiling at its default and at its declared maximum | R6 |
| The per-origin ceiling is read, not inferred | The per-origin ceiling is read from the transport and compared against the same two settings | R6 |
| Ceilings are counted per unit | The number of transports a single unit creates is recorded, so the process-wide ceiling can be computed as their product | R6 |
| A bounded setting is not overridden by a literal | A literal in the transport path that duplicates a bounded setting's purpose is a finding **only** when the product with the per-unit count exceeds what the setting implies | R6 |

- Evidence: R1, R6.

*Internal de-duplication rule:* the reported figure is a (f) finding. (a) records the claim count it is derived from, as an input to the composition, and never files it. Where both blocks cite the same run, the run is cited by its R-id once.

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **The child process that performs the work** — argument-vector design, pipe wiring, concurrent draining, child-wait races, exit-status interpretation, and kill escalation → `05`. This phase owns only *whether a stop request can reach a blocked read of that child's output*, and whether releasing it depends on the child producing output.
- **The browser: everything before the resource is in use** — launch arguments, context fingerprint, injected-script delivery, response interception, environment inheritance by children, and any bound applied to a **setup** step → `05`. **Everything after → `04`.** The test is the lifecycle stage: *a step performed to acquire the resource is `05`'s; a step performed to give it back is `04`'s.* `04` owns the release only — whether it is reached on the stop path, the order of release, the bound on each step, and whether a release that raises replaces the failure that caused the exit. Neither phase may file the same teardown method.
- **The transport connector's construction site** → split by property, never by function. The **pool ceiling it builds is `04`'s**, as a property. The **certificate-verification policy it builds, and whether that policy reaches every transport, are `03`'s.** Neither phase may file the construction function itself: a function that builds two things is file-local craft at most, and is not a runtime property.
- **The effective request rate** — the product of the whole-item bound and the per-child bound as a rate against one origin → `03`. `04` files **the literal only**, and only when that product exceeds what the declared setting implies.
- **Why to wait, how long, and against which origin** — retry taxonomy, backoff distribution, server-supplied delays, per-origin pause → `03`. This phase owns only whether a wait observes the stop state.
- **The credential's lifetime, its file's permission mode, its cleanup, and whether a secret reaches any sink** → `06`. **The permission mode, creation mode, atomicity and cleanup of every other file, including the temporary files released on the stop path** → `07` by R-A. This phase files neither; it owns only that a release happens, in what order, and under what bound.
- **What lands on disk after a stop** — residue, partials, preserved parts, hidden working directories → `07`. This phase files no residue question, only the ordering and exception-safety of the code that decides to leave it.
- **What the operator is shown** — exit status, terminal streams, progress, renderer selection, and the summary's labels → `08`. This phase owns **what the reported number means** and whether it matches what is in flight; `08` owns how it is printed and what the neighbouring labels count.
- **The stop → outcome translation seam** → this phase owns **whether a stop is distinguishable from an ordinary failure where it is observed**; `08` owns **which process status that distinction becomes**. File the missing distinction once, at the point of observation; do not file the status.
- **The meaning, bound, sourcing and validation of a declared setting** → `02`. This phase owns the **effect** the value has — what it actually limits, and whether the code honours it. The example environment file's bounds → `02`.
- **The correlation identifier and the shutdown event — all three legs.** **Generation, binding and clearing** → `01`. **Shutdown-state derivation from a signal, and the event's creation, ownership and cross-loop visibility** → `04` (this phase). **Rendering and sink of both** → `08`. This phase owns only the event's leg.
- **Module-level mutable state, and the existence and form of a cycle-breaking import** → `01`. This phase owns only what the returned object's lifetime does to a second run in the same process, and files it **only** with an observable consequence.
- **Bootstrap placement and ordering of the interrupt registration** → `01` by R-D. This phase owns the registration's *reachability and lifecycle*, never where it sits.
- **A documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09` by R-E; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`. This phase files **no** `DOC-UPDATE`. Where a docstring describes a behaviour the code contradicts, the runtime behaviour is filed here once and the wording is `09`'s.
- **Whether a finding survives being moved** — import graph, layer direction, cycles, facades, bootstrap order → `01`. **File-local craft** — typing, naming, module size, a literal duplicated within one file where it has no runtime consequence → `09`.
- **A dependency declaration in the build manifest** → `11`.
- **Dead code in code, alive in documents** → `99`'s rule, `10` and `09`'s code side. This phase files no dead-code finding; a component imported by nothing is not a concurrency property.
- **Whether the test suite proves any of this** → `10`. Whether a **finding** from this phase survives validation → `99`.
- **Licence posture, terms acknowledgement, notice mechanism** → not an audit subject; inadmissible under `problems-only` and expressly rejected. Do not file.

## 8. Edge Cases

- A stop arrives while a claim is held, and the release is the only thing that would let another unit start.
- A claim is held across a stage that itself takes seconds, and every other unit is queued behind it.
- Two units reach the same guarded work at once — the nested claim, at the configured ceiling.
- The stop arrives a second time, after the process has already been told once.
- The stop arrives while a read of a child's output is blocked, and the child produces nothing further.
- The stop arrives while a blocking call is running off the loop thread, after its own bound has already fired.
- Every part is already present, so there is nothing to download and nothing to claim.
- One item in a large list raises while every other item is still running.
- A release step times out, and the next release step then raises.
- A release step raises while an unrelated failure is still in flight.
- Two entry points register in the same process.
- (Gap: the production condition that reaches the per-part transfer from inside the outer claim is not executed here. Reachability **is** executed; the condition is carried as `UNVERIFIED`. Verify or document; never report it as verified.)
- (Gap: a child writing more than its output buffer holds is not reproducible without a product child; named, and not run here — `05`'s subject.)
- (Gap: the platform's delivery of an actual key press cannot be observed from within the process; the installed handler is invoked programmatically instead. Verify or document.)

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are not redefined here.

| Severity | Conditions |
|---|---|
| CRITICAL | The process can reach a state it cannot leave: no progress, and no stop, no timeout and no repeat interrupt that changes it. A stop is requested and is never observed by the work it is meant to stop, with no bound on how long that work runs. |
| HIGH | A number the operator is shown does not mean what it is named; a primitive is claimed on an object already held; work items are created without a bound; a resource is not released on one or more exit paths; a release replaces the failure that caused the exit; a stop is indistinguishable from an ordinary failure at an entry point. |
| MEDIUM | A shared record of claims or registrations is mutated from more than one entry point; a completion step wraps its input a second time; an empty result is not distinguished from a cancelled one at its consumer; a release is skipped, or bounded more loosely than the rest of the process. |
| LOW | A shape, naming or structure deviation with no runtime consequence, including a branch that cannot be reached and a value computed and never used. |

**Type guidance.** `SPEC-DEVIATION` for behaviour that contradicts the project's own declared setting, bound or rule. `RUNTIME-ERROR` for anything observed failing at runtime. `BEST-PRACTICE` for a defensible design with a demonstrated risk. **This phase files no `DOC-UPDATE`** — a documented claim belongs to `09` by R-E.

A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity. **The severity ceiling and the composition for the claim subject are set by the preamble's binding rule 3, not by this table's adjectives read in isolation, and the decision document's own characterisation of the subject is not citable as a severity.**

## 10. Recommended Sequence

1. Discovery (`## 4`).
2. R8 first — the static baseline and the coverage declaration. Every later step is observed against it, and a zero-match subject is declared uncovered before it is checked, not after.
3. R1, then R2. R1 is the highest-risk subject in the phase and the first thing a truncated pass must have covered.
4. Blocks (a) through (f) in the order they are written in `## 6`. **Do not reorder by convenience.** This is risk order, descending: a pass cut short must return the high-risk blocks, never the easy ones.
5. R3–R7 as their blocks are reached, each producing the evidence named in that block's `- Evidence:` line.
6. Cross-cutting (`## 7`) and edge cases (`## 8`).
7. Consolidate findings, re-reading `## 7` before writing each one.

**Second-pass order.** If this phase is re-run after a thin result, do **not** start again from step 1. Re-enter at the first block below for which no evidence was recorded, and continue downward: `(a)` one claim, many claims → `(b)` a stop that never reaches the work → `(c)` the stop signal and the state it sets → `(d)` completion, cancellation and per-item outcomes → `(e)` teardown → `(f)` the ceiling reported and the ceiling enforced → R8 refreshed last, so it reflects what was actually run. A block with partial evidence is resumed; a block with complete evidence is skipped. R1 and R2 are re-run only if (a) has no evidence at all, since their harness is reused. A re-run that finds no new evidence writes `No problems found in this phase.` and stops.

## 11. Finding Prefix

Use `CON-` for all findings in this phase. `CON-` is unique in the catalogue, shares no first two characters with any other phase prefix, and is obtainable from no other prefix by a single plausible edit. It does not encode the phase number, so renumbering never invalidates a published finding ID.

## 12. Reporting

- Write findings to: `.ai/audit/04-concurrency-cancellation/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row, or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) the **exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
  - **W-4, and this bullet is binding on the report:** the claim subject is filed as **exactly two** findings. The **reproduced shape** carries an observed severity composed from the run's own R1, R4 and R5 evidence — `CRITICAL` only when all three legs are **observed**, otherwise capped at `HIGH` with the leg that did not execute named. A leg that was not executed is `UNVERIFIED`, and its band is composed from the structural fact under `## 9`. The **production trigger** carries `UNVERIFIED` and a band composed from its structural fact under `## 9`. The two are never merged and never omitted; under `problems-only`, omitting either reads as "no finding". Do not cite any document's characterisation of the subject as a severity.
