---
name: 05-subprocess-browser
status: draft
validated: no
executor: auditor
problems-only: true
---

# 05 — Subprocess and Browser Lifecycle

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — severities are composed by this phase, never inherited.** The
> analysis that preceded this file enumerated a problem list **with a severity
> written next to each entry**, and the decision document attached its own
> adjectives to the subjects. Neither is citable. Every severity in the report is
> composed from this phase's own run against `## 9`. An executor who finds a
> subject already carrying a severity has misread this file: record the evidence
> first, then assign the severity.
>
> **Binding rule 2 — the nested-process subject is in scope; its recorded cause is
> wrong and must not be written down.** The analysis inferred that a child spawns
> a nested external process because the child's vector carries a flag that selects
> a third-party downloader. The installed tool's own option documentation for that
> flag says the opposite: it selects the tool's **native** downloader precisely
> *instead of* the external binary. **The scope ruling is unaffected** — every
> process the application causes is this phase's subject, whichever route produces
> it. **R1(b) records what processes actually appear. It never records
> confirmation that an option causes them.** Do not restate the recorded cause and
> do not attach the observed consequence of a nested process to any option.
>
> **Binding rule 3 — eight checks whose titles read like conclusions. Observe
> before asserting; the evidence is the observation, not the expected outcome.**
> 1. **(b)1** the named file's fate at child-read time is a race and **may not
>    manifest**. Twenty runs that all succeed **are a finding** — a race this
>    platform did not reproduce. State the ordering as structure and the run
>    distribution as distribution; never infer one from the other.
> 2. **(a)3** record the count a termination request actually reaches. The count is
>    the evidence; "so it does not reach the rest" is available only if the
>    recorded pids were probed afterwards.
> 3. **(c)3** a capture that is a prefix is provable only when the stub's tail is
>    written after the parent has **provably** stopped reading; otherwise it is
>    indistinguishable from a child that wrote nothing. R5(ii)'s evidence carries
>    the proof or the check is not filed.
> 4. **(c)4** the finding is the observation that the parent **did not return within
>    the wall clock** — not the absence of a bound read from the source.
> 5. **(d)3** the finding is the mechanism. The sentence *"and therefore the
>    credential path leaks"* is `06`'s; write a cross-reference or one defect is
>    filed twice.
> 6. **(e)3** "warning-only" is a finding **only** with the consequence observed in
>    R4(iii). A probe that warns and a command that then fails cleanly is not that
>    finding.
> 7. **(f)3** what is decidable offline is that the two surfaces express
>    **different filters**. Which stream a delegated selector admits is the
>    third-party tool's behaviour (documented skip 3).
> 8. **(g)6** acquire side only. Do not test release; that is `04`'s, and testing
>    it produces the double filing the ruling exists to prevent.

## 1. Goal

How every child process and the browser are located, launched without leaking, fed, drained, judged and killed.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| Process accounting | Every spawn, every process it can create, every boundary around them | A spawn with no wait and no kill; a tree with no group, session or job; a survivor on one exit path |
| The invocation contract | The argument vector, any file it names, the working directory, the environment | A named file gone when the child opens it; a create-or-destroy failure replacing the outcome; concealment that holds on one transport and not the other |
| Reading and judging a child | Stream wiring, the reader's bound, the reaper, the verdict | A capture that is a prefix; a reaper with no bound; a reader failure that becomes the verdict |
| Emitting what a child said | Every site that turns child output into a log record, a terminal write or a buffer | No transform at a site; a transform that cannot match the shape; the same bytes treated differently at two sinks |
| Finding the tool | The discovery probe, its caching, its callers, the absent case | An answer nobody branches on; a cached answer outliving the machine; an absence that surfaces as a traceback |
| The third-party downloader's contract | Its two surfaces, its version floor, the shape of its input | Divergence that can change which stream is selected; a flag the tool does not document; an unbounded input shape |
| Browser acquisition | Launch configuration, presented identity, injected asset, interception, and what the path binds nothing to | An asset silently not delivered; a literal bound among configured ones; a discarded launch cause; a resource created and bound to nothing |

**In scope:**
- Binary discovery, and the behaviour when the binary is **absent** (warn-only vs. gate).
- Argument-vector construction — including the response-file convention that exists **specifically** to keep signed URLs and the cookie path out of the process table, and the cookie path that nevertheless reaches the vector on the other transport.
- Pipe wiring, concurrent draining, and the pipe-buffer exhaustion question for a child that writes more than the buffer holds before anyone reads.
- Child-wait versus output-reader races.
- Parsing of the child's own progress protocol from its reporting channel, and the terminal-overwrite echo of child output.
- Exit-code interpretation, and error propagation with the child's output redacted before it is logged.
- The choice to invoke a third-party downloader as an interpreter module rather than as a pinned binary, and what that implies for reproducibility.
- **Parity between the two surfaces of the same third-party downloader**, including option propagation.
- **Kill escalation — of every process the application causes, including a process a child creates for itself — and the guarantee that it runs on every exit path.**
- **The process tree a child creates for itself: which processes appear, how they are located, and the fact that no process group, session or job boundary is established around them.**
- **The browser, acquire and setup only:** launch arguments, context fingerprint parameters, injected-script delivery, response interception, and environment inheritance by the driver and by its descendants. **Teardown and release are `04`'s** (see `## 7`).

**Out of scope:** the permission mode of the response file, and any file's residue, creation mode, atomicity and cleanup → `07`; the credential file's lifetime, content and format, and whether a value is a secret or reaches a sink → `06`; *when* to fall back between retrieval methods, and the child's own network behaviour, retry taxonomy and backoff → `03`; the browser's release and teardown → `04`; the kill's interaction with a blocked read of a child's output → `04`; exit-code mapping, TTY arbitration and the live display → `08`; a setting's meaning, bound and validation → `02`; a dependency declaration in the build manifest → `11`; a documented claim → `09`; whether the test suite is good → `10`.

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` (from `.ai/context/commands.md`). `mypy` (strict) is the configured checker; a second checker present in the dev dependency group is **not** it — do not substitute it.
- **No Docker. No database. No third-party origin. No service is started.** This phase's real prerequisites:
  1. **A stub executable** — a short script in a temporary directory, named for the tool it replaces, placed **earlier on the executable search path** than anything real. Every invocation names its tool by bare name, so one stub serves this application's invocation *and* any invocation a child makes for itself — which is what makes the nested-process check observable instead of inferred.
  2. **A temporary directory** for the stub, for everything the stubs record, and for a controlled environment.
  3. **Stand-in handles** — a process handle, a stream, a browser handle, a context, a page — used only where a real object would require an installed browser binary.
- **A real muxer is present on the machine that runs these methods.** The stub directory must precede it, and the absent-binary case must exclude every directory that contains one — asserted by the discovery probe returning false **before** the run, not after.
- **All captured child and driver output is written to a file.** The declared console encoding raises on third-party error text containing box-drawing characters; a probe that prints manufactures a failure that is not the product's.
- No product dependency is installed, launched or contacted. The third-party downloader is queried for its version and its option surface only.

## 4. Discovery

Map the architecture before checking anything. **Use roles, not names.** Never reference a concrete file, module or class name in this file. **A subject that maps to nothing is reported as a gap — that is a finding.**

1. **Spawn map** — every place the process starts something, what executable each names, what each is waited for, and what signals it.
2. **Tree map** — every process a child can create for itself, by which route, and whether any group, session or job boundary exists around an invocation.
3. **Invocation map** — every argument vector built, every temporary file a vector names, and the order between starting the child and destroying that file.
4. **Channel map** — every stream a child is given, every reader over it, every bound on it, every parser over what it returns, and every sink that receives the result.
5. **Verdict map** — every place a child's status and a child's output are turned into one outcome, and which of the two decides it.
6. **Dependency map** — every external tool the process looks for, every caller of that lookup, and every place the child's own version is assumed.
7. **Evidence map** — the test tree's reach into these subjects, searched **excluding every worktree directory**, whose stale copy of an earlier phase set will otherwise be searched by accident. A subject with no match is declared uncovered **before** it is checked, not after.

*Role vocabulary:* the argument-vector builder for each transport · the temporary-file holder that writes, yields and removes · the line-reading helper · the progress-protocol parser and its key handlers · the completion helper that waits for the first of two things and cancels the rest · the termination escalation ladder · the availability probe and its cached answer · the child-output transform · the terminal echo that rewrites a line in place · the browser manager's acquire path · the automation driver's start and stop · the command builder that fixes what the child is told · the batch-size constant.

## 5. Runtime Verification (mandatory)

> **The evidence regime, stated once.** This is the only phase in the catalogue that must start real processes. Every method below is local and offline. The substitution primitive is a **stub executable** (`## 3`); the substitution objects are **stand-in handles**.
>
> **Three mechanical rules, all binding:**
> 1. **A real muxer is installed on the machine that runs these methods.** The stub directory must precede it on the search path, and the absent-binary method must exclude every directory that actually contains one — verified by asserting the discovery probe returns false **before** the run, never after.
> 2. **All captured child and driver output is written to a file, never printed to the console.** The console encoding on the declared platform raises on third-party error text containing box-drawing characters; a probe that prints manufactures a failure that is not the product's.
> 3. **No test that patches the process boundary is admissible evidence for any row below.** The suite's stand-in for the spawn call reads the argument file synchronously inside the call — precisely the ordering this phase is here to examine — so the argument-file race, the probe's real answer and the delivery of any termination request are invisible to it by construction. Match counts are recorded (R9) as the state in which a finding was observed, and are never filed here.

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | The process tree: accounting, boundary, kill reach, survivors per exit path, ladder idempotence, verdict matrix | (a) Enumerate every spawn site and the executable each names. (b) Write a stub that records its own pid, spawns a further process **of its own choosing**, records that pid too, writes both to a file and sleeps; drive each transport that can reach a stub, then read the file — **record what appeared, and do not attribute it to any option** (binding rule 2). (c) After the parent's method returns, probe every recorded pid for liveness and record the survivor count — once per exit path: success, non-zero exit, an exception provoked inside the output reader, cancellation. (d) Drive the termination escalation against a stand-in handle through each of its branches, then a second time against the same handle, then against one already exited; record the return of each. (e) Record every bound granted before a process is forced, and every bound the surrounding code was given. | Spawn sites and executables; recorded pids and their liveness after each exit path; survivor count per path; branch taken and return of each escalation call; every grace bound and the bounds it is compared against. |
| R2 | The named temporary resource at the moment the child opens it | A stub named for the muxer, earlier on the search path, that takes the argument beginning with the file marker, opens it, and writes one word — **opened**, **missing**, or **denied** — plus its own start time, to a file; then exits. Drive the muxer path with a no-op progress callback **at least twenty times**, recording the outcome word each run, and record the parent's exit status or escaping exception per run. Separately, drive the destroy step against a path whose removal raises, and record which exception surfaces and whether the child was signalled. | The outcome word and elapsed time per run; the distribution across twenty runs; the surfaced exception and exit status per run; the outcome of the forced removal failure. |
| R3 | Both argument vectors, and what the child inherits | Call each of the two command builders **directly** with a synthetic media URL and a synthetic credential-file path; capture both returned vectors verbatim and diff their key sets. Separately, drive the muxer path with a stub that writes its own argv and its environment to a file; diff the captured environment against the parent's key by key and record the count and names of anything the parent added. | Both vectors verbatim; the key-set diff; the environment diff with counts; the argv as the child saw it. |
| R4 | The discovery probe and the absent-binary outcome | Three cases, **each in a fresh process** so no cached answer carries over: (i) call the probe twice with the stub directory first and record both answers and whether the second re-probes; (ii) call the probe, then run the muxer path, and record whether the caller's branch changed; (iii) run the muxer path with a search path containing **neither the stub directory nor any real muxer** — asserting the probe returns false **before** the run — and capture the surfaced outcome and the process exit status verbatim. Repeat (iii) against the other transport that needs an external tool. | Probe answers per call and whether a re-probe occurred; whether any branch changed; the verbatim surfaced outcome and exit status per absent case. |
| R5 | Reader, reaper and verdict: five stub behaviours | Five stub behaviours, each driven through the real download path with the stub earlier on the search path, **each captured to a file**: (i) write one line of one mebibyte, then stop; (ii) write a progress line, then a known four-kibibyte tail, then exit immediately — **and record the evidence that the parent had already stopped reading before the tail was written**, without which the check is not filed; compare the captured buffer against what was written; (iii) write the protocol's end-of-stream line, then sleep indefinitely — bound the parent with a fifteen-second wall clock, record whether it returned, then terminate the stub by pid so the probe leaves nothing behind; (iv) write a progress line whose value is a non-numeric token that is not the protocol's own placeholder; (v) emit fifty mebibibytes on one stream and record the parent's peak working set. For every case record what escaped, what the parent logged, and whether the child was alive after the parent returned. | Per case: what escaped, what was logged, the child's liveness afterwards; the stopped-reading proof and the captured-bytes comparison in (ii); whether the parent returned within the wall clock in (iii); the peak working set in (v). |
| R6 | The mechanism on every path that emits child output | Two parts, neither needing a process. (a) Feed the child-output transform a fixed corpus — an absolute URL carrying a token, a filesystem path in this platform's shape, an argument fragment, a plain non-URL token — and record, per input, whether the output differs from the input and what the output is. (b) Drive one stub that echoes its own argv and its credential-file argument to **every sink at once**; capture what is written to the terminal and what is written to the log file, then diff them. Then enumerate every site that emits child output and record each as transformed or raw. | Per corpus input: output verbatim and whether it changed; the terminal bytes and log bytes for the same run and their diff; the site list with each site's transform status. |
| R7 | The browser on the acquire side | (a) Start the automation driver — **it starts on this machine with no browser binary installed, so this method executes** — record the driver's process identity while it runs, then stop it. (b) Attempt a launch and capture the raised exception's text **verbatim to a file**. (c) Drive the acquire path with stand-ins for the browser handle, the context and the page, so the launch argument list, the identity parameters, the injection call and the interception registration are all captured with no browser present. (d) Point the manager at a settings object, rename the injected asset, drive the acquire path, and record whether injection still occurs and at what level it is reported. (e) Drive the acquire path and record, per resource created, whether any call returns it. | The driver process identity; the launch failure text verbatim; the launch argument list and identity parameters as passed; the injection call and the level reported in (c) and (d); the resource list with its binding status. |
| R8 | Surface parity and the version actually present | (a) Build both surfaces' option sets **for one synthetic item** and diff the key sets and their values. (b) For a hand-built format list containing an audio-only entry, record the filter expression each surface expresses, **verbatim**. (c) Read the installed third-party downloader's version by executing it, then query its own option surface for each flag the vector passes: whether the flag appears in its help text, and the exit status when the flag is passed alone. (d) Read the quantity that decides how much the child is asked to do in one call, and whether it is configurable. | Both option sets and the diff; both filter expressions verbatim; the installed version; per flag, present in help or not, and its exit status; the input-shape quantity and its configurability. |
| R9 | Baselines, coverage declaration, platform note | (a) Run the four verification commands from `## 3. Prerequisites` over this phase's surface; record exit codes, pass/fail/skip counts and skip reasons. **Do not substitute any other type checker.** (b) Search the test tree — **excluding every worktree directory**, whose stale copy will otherwise be searched by accident — for the spawn function, the discovery probe, the termination escalation, the temporary-file helper, the first-completed helper, the progress parser, the output echo, the child-output transform and the browser manager; print a match count per symbol. **Every subject with a count of zero is declared uncovered before it is checked.** (c) Record that the suite's spawn stand-in reads the named file inside the call. (d) Write the platform note and the documented skips below. | The four exit codes and outputs; the skip reasons; the per-symbol match counts; the platform note and skip texts. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how to obtain its evidence is rewritten here, not skipped at execution time. A `Method` of "inspect the implementation" is not admissible anywhere in this phase — every method must produce its evidence by running something.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.**

*Two rules that follow, both required:*
1. **R9's results are never filed as findings.** They are cited as the state in which a finding was observed. The absence of coverage is `10`'s subject.
2. **A method that cannot say how is rewritten, not skipped at execution time.** If a row is unobtainable on the declared platform, the phase emits a **documented skip with justification** naming the effect, the platform and the reason. Under `problems-only`, silence reads as "no finding".

> **Platform note (mandatory — this phase touches termination and third-party binaries).** The
> declared development platform is Windows. Signal and termination behaviour,
> process-tree observation, and third-party binary availability all differ from a
> Unix host. Three methods are platform-dependent: the termination escalation's
> grace branch (R1(d)), the absence of any readable third-party process command
> line (R3, R5), and everything about the automation browser binary (R7(a), R7(b)).
> Each is handled below — by observation where observation is possible, or by a
> documented skip with its justification. `problems-only` must not convert
> "unverifiable" into "no finding". **This is an evidence-method note, not a filed
> finding.**

1. **The graceful branch of the termination escalation.** *Not executable on this platform: the standard library maps the graceful request and the forceful one to the same unconditional termination call, so no child can be made to ignore the first request and the grace branch cannot be entered.* The bound is verified statically as the only grace in the process, against the bounds the rest of the code is given (R1(e), R9). **This is a documented skip — never a pass and never a fail, and never a pre-filed finding.**
2. **The automation browser binary.** *No browser binary is installed on this machine, so no launch, no navigation, no injected asset and no intercepted response can be observed.* **The skip is narrowed to that, and not broader:** the automation **driver starts** without a browser binary, so R7(a)'s driver identity, R7(b)'s verbatim launch-failure text and the acquire-side process tree are **executed, not skipped**. What is verified by stand-in and by capture: the launch argument list, the identity parameters, the injection guard and its silent branch, the resource bound to no release, the literal bound among configured ones, the discarded launch cause, and the driver's own process identity. Whether a real browser honours the automation-suppression flag is a property of the browser, out of scope by design.
3. **Whether the third-party downloader honours a flag it is given.** *The delivery of each option is observed in the argument vector; whether the child enforces it is a property of the child and is out of scope by design. State it; do not guess it.* Applies to certificate suppression, chunked range requests, the fragment-concurrency ceiling and the native-stream selection.
4. **Redaction completeness against a live child's output.** *Whether the third-party tool or the muxer prints a signed URL or a credential path in any given failure cannot be reproduced without a live origin. What is verified instead is the mechanism, which is decidable offline: the transform matches only absolute HTTP(S) URLs, and the terminal-echo path applies none at all. A stub that echoes its own argv reproduces the shape exactly.*
5. **A real muxer's behaviour when its own parent is terminated.** *Partially obtainable: the stub is the nested process, so its lifetime under a kill of its parent is directly observed by R1(b). What is skipped is only whether the real muxer, when a child invokes it, behaves the same way when its own parent is terminated — a property of a third-party binary, out of scope by design.*
6. **Process-table exposure as an operator would see it.** *The declared platform publishes no readable process command line for a third-party observer. The vector is therefore read from the construction site and from the stub's own argv, which is the same string the platform would publish.*

## 6. Audit Dimensions (checks + evidence)

The seven blocks are ordered by risk, **descending**. The letter order **is** the re-entry order (`## 10`): a pass cut short returns the blocks it reached.

### (a) Every Process the Application Causes Is Accounted For

> The process starts things it does not always construct. List every spawn, and for each ask: what the application believes it started, what the child may start on its own, and whether anything groups them. Then take each way the invocation can end and ask, one at a time, what is still running afterwards. A process that survives a path it should not is the finding; the absence of any boundary around a tree is the same finding one level up.

| Check | Description | Evidence required |
|---|---|---|
| Every spawn is accounted for | Each place a process is started is listed with the executable it names, and each is matched to the point where it is waited for or killed. A spawn with neither is a finding | R1 |
| Nothing groups the tree | Whether any process group, session or job boundary is established around an invocation is recorded. A tree with no boundary is a finding | R1 |
| The kill addresses one process, not a tree | What a termination request actually reaches is **recorded as a count**, and compared with the number of processes the run can create. The count is the evidence; a conclusion about survivors requires the probes | R1 |
| Nothing survives any exit path | Success, non-zero exit, an exception raised inside the output reader, and cancellation are each driven; after each, every pid the run created is probed. Any survivor is a finding | R1 |
| The ladder survives being run twice | The escalation is driven twice against the same handle, and against an already-exited one, and both returns are recorded. A second call that raises is a finding | R1 |
| Every grace period in the process is enumerated | Each bound granted to a process before it is forced is recorded, and compared with the bound the rest of the process is given | R1, R9 |

- Evidence: R1, R9.

### (b) What the Child Is Told, and What It Inherits

> A child's entire input is four things: its argument vector, any file that vector names, its working directory, and its environment. Take each. For a named file the question is not where it is written but **whether it still exists when the child opens it** — and what happens when creating it or destroying it fails. For the environment the question is whether the launch restricts anything at all.

| Check | Description | Evidence required |
|---|---|---|
| A named temporary resource outlives the spawn that needs it | The order between starting the process and destroying the file its vector names is recorded as **structure**; the child's own experience of opening it is recorded **separately, as a distribution over the runs**. Neither is inferred from the other, and twenty clean runs are themselves a finding | R2 |
| A failure to create or destroy does not replace the in-flight outcome | What surfaces when the file cannot be written, and when it cannot be removed while the child holds it, is recorded; and whether the child was signalled on that path | R2 |
| The stated purpose of the convention is achieved | Each transport's vector is read, and the sensitive forms it does and does not carry are recorded. What appears in one and not the other is a finding | R3 |
| Nothing constrains what the child inherits | Whether any launch restricts the child's environment or working directory is recorded. Full inheritance is a finding; the finding states the mechanism, never what was in it | R3 |
| A secret-free vector is not claimed as one | A vector whose stated purpose is concealment is checked against every sensitive form the invocation actually passes | R3 |

- Evidence: R2, R3.

### (c) The Reader, the Reaper, and the Verdict

> Between "the child is running" and "the parent knows what happened" there is a reader, a parser, a reaper and a verdict. Take them in that order. For each, ask what it does when the child writes more than expected, writes at the wrong moment, writes something the parser cannot read, and never writes again. **What the parent ends up believing is the subject** — not whether the child failed.

| Check | Description | Evidence required |
|---|---|---|
| Nothing can deadlock on a full pipe | Each spawn's stream wiring is recorded, and the draining is checked to be concurrent wherever both streams are captured | R5 |
| The reader's size bound is declared | The bound each reader imposes is read off the object it reads, not assumed; a default bound with no declared one is recorded | R5 |
| What is captured is what the child wrote | A child writes a known tail at a known moment; the captured buffer is compared against what was written. The check is filed **only** with the proof that the parent had already stopped reading | R5 |
| The reaper is bounded | The wait that follows output consumption is exercised with a child that stops producing but does not exit, under a wall clock. **The finding is that the parent did not return within it** | R5 |
| A reader failure does not become the verdict | Each way the reader can raise is provoked; what escapes, what the parent logs, and whether the child is signalled are recorded for each | R5 |
| Accumulation is bounded | What the parent holds while a child runs is measured against the child's own output volume | R5 |
| The verdict matches the child's own status | A success is reported only when the child's own status says success; the comparison is made on the status, not on the output | R1, R5 |

- Evidence: R1, R5.

### (d) The Report Made of the Child's Output

> Every place this phase turns child output into something an operator or a log sees is a filter or nothing. For each such place, ask two questions that are both about the **mechanism**: does anything run at all, and could what runs match the shapes this channel actually carries? A capability that is absent here is this phase's finding; where a value ends up is another phase's.

| Check | Description | Evidence required |
|---|---|---|
| Every emit site is listed | Each place child output becomes a log record, a terminal write or a stored buffer is enumerated. This list is the denominator for the rows below | R6 |
| A transform exists at every site | Each site on the list is recorded as transformed or raw. Raw is a finding at every raw site | R6 |
| The transform can match what the channel carries | A fixed corpus — an absolute URL with a token, a filesystem path in this platform's shape, an argument fragment, a plain token — is passed through the transform, and each result compared with its input. **An input returned unchanged is a finding about the mechanism.** What that input would mean elsewhere is not this check's finding | R6 |
| The same bytes take the same treatment everywhere | One child's output is captured at every sink simultaneously and the results compared. The same value treated differently at two sinks is a finding here; what the value is, is another phase's | R6 |
| The child's own status is the trigger | Whether the failure report is emitted because the child failed, or because the parent stopped listening, is recorded | R6, R5 |

- Evidence: R6, R5.

### (e) Whether the Binary Is There

> A dependency found at runtime is a gate only if something acts on the answer. Find the probe, find every caller, and record whether the caller's behaviour changes when it says no. Then remove the binary and record what the operator actually gets.

| Check | Description | Evidence required |
|---|---|---|
| The probe's answer is used | Every caller of the discovery check is listed, and for each it is recorded whether the returned value changes any branch. A caller that ignores it is a finding | R4 |
| The probe reflects the current machine | A cached answer is checked against the machine as it is now; a cached answer that survives a change is a finding. Each case runs in a fresh process | R4 |
| Absent is a gate or it is not | Whether the absence changes control flow before the failing launch is recorded, **together with the consequence actually observed.** A probe that warns and a command that then fails cleanly is not this finding | R4 |
| The failure names the missing thing | With the binary absent, the surfaced outcome is captured verbatim and checked for whether it identifies the missing executable and a way to obtain it | R4 |
| Every transport is treated the same | The absent-binary outcome is compared across the transports that need one. Two different surfacings of one absence is a finding | R4 |

- Evidence: R4.

### (f) Two Surfaces of One Tool, and Its Version

> One third-party downloader is used two ways — as a library inside this process, and as a child process. Build both calls for the same item and compare them as two answers to one question: what do they tell it to do. Then ask what the invocation form assumes about the version it will meet.

| Check | Description | Evidence required |
|---|---|---|
| Both surfaces are built for the same item | Each surface's option set is captured for one synthetic item, and the key sets are diffed. Each difference is a finding at the point of divergence | R8 |
| Divergence is judged, not listed | Each difference is judged against what the item needs; a difference that can change which stream is selected outranks one that cannot | R8 |
| A filter present on one surface is not assumed on the other | Where one surface expresses a filter the other delegates, **both expressions are recorded verbatim.** What is decidable offline is that the expressions differ; which stream a delegated selector admits is the tool's behaviour | R8 |
| The invocation form assumes a version | The declared lower bound is compared with the version actually present, and the tool's own option surface is queried for each flag the vector passes: whether it appears in the tool's help text, and whether it is accepted | R8 |
| An accepted but undocumented flag is a finding | A flag the invocation depends on that the installed tool does not document is a finding. So is a flag it does not accept | R8 |
| The child's input shape is declared | The quantity that decides how much the child is asked to do in one call is read, and whether it is configurable is recorded | R8 |

- Evidence: R8.

### (g) The Browser, Before It Is Used

> Everything that happens between deciding to automate a browser and the first use of it. Record the launch configuration, the identity it presents, anything injected, anything intercepted, and every bound applied on the way in. Then check the other direction: which resources this path acquires, and whether any of them is ever bound to a step that gives it back. **Release itself is not this phase's; only the absence of a binding on the acquire side is.**

| Check | Description | Evidence required |
|---|---|---|
| The launch configuration is recorded | Every launch argument is listed, and what each is for is recorded. An argument whose purpose cannot be identified is a finding | R7 |
| The presented identity is recorded | Each identity parameter passed to the context is listed, and whether a value is derived or fixed is recorded | R7 |
| Injection is confirmed, not attempted | Whether an injected asset is actually delivered is checked against the asset's presence, and the silent branch taken when it is missing is recorded together with the level it is reported at | R7 |
| Interception is bounded | Each wait and each read inside the interception path is checked for a bound, and the bounds are compared with each other. One literal among several configured bounds is a finding | R7 |
| A launch failure keeps its cause | The failure raised by the launch is captured verbatim, then what the application surfaces is captured, and the two are compared. A cause available and discarded is a finding | R7 |
| Acquired resources are bound to a release | Each resource the acquire path creates is listed with the step, if any, that returns it. A resource created and bound to nothing is a finding **— of the acquire side only** | R7 |
| The automation driver is part of the tree | The process the automation driver starts is identified and recorded, and whether it is inside any boundary this phase establishes is recorded | R1, R7 |

- Evidence: R1, R7.

*Internal de-duplication rule:* a surviving process is an **(a)** finding; **(c)** records only the *shape* of the exit path that produced it, as an input, and never files it. A transform gap is a **(d)** finding; **(b)** records only that the value reached the vector, as an input, and never files the exposure. Where two blocks cite the same run, the run is cited by its R-id once.

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **A file's permission mode, creation mode, atomicity, residue and cleanup** → `07`, regardless of content. **The credential file's content and redaction, its permission mode and the platform reality of that mode, → `06`.** **This phase's own exception, ruled:** this phase owns a temporary file *to the extent its availability when the child opens it is part of the invocation contract*, and whether an error while creating or destroying it replaces the in-flight failure. **The test:** *would the finding still exist if the file never touched disk?* **Yes → `05`; No → `07`.** Everything after the child has read it — what is left behind, with what mode, removed when — is `07`'s.
- **The credential file's lifetime, content, format and placement** → `06`, **including its removal on every path, even though it is created and destroyed inside this phase's own call sites.** The split, stated so one sentence of consequence is not filed twice: **the child surviving an exception is `05`'s; the credential file being removed while that surviving child still needs it is `06`'s.** Cross-reference; do not merge. It is a parameter handed to a foreign tool, not the invocation itself, so the disk test above does not move it to this phase.
- **Whether a value is a secret, and whether every sink applies the redaction** → `06`. **This phase owns the mechanism only** — whether its own output-capture and re-emission path applies a transform, and whether that transform can match the forms that path actually carries. **A missing capability is this phase's; a missing application where the capability exists is `06`'s.** So: a transform that cannot match a filesystem path, and an echo path with no transform at all, are filed here; a signed URL that reaches a log are not.
- **The browser: everything before the resource is in use** — launch arguments, identity parameters, injected-script delivery, response interception, and environment inheritance by the driver and its descendants, and any bound applied to a **setup** step → `05`. **Everything after the resource is in use: `04`.** The test is the lifecycle stage — *a step performed to acquire the resource is `05`'s; a step performed to give it back is `04`'s.* This phase files the acquire-side fact that a resource is created and bound to no release; `04` files whether release is reached, in what order, and under what bound. **Teardown and teardown timeouts are `04`'s.**
- **The kill escalation of an OS child, and the process tree it does not reach — including a process a child creates for itself** → `05`. **Whether a stop request can reach a blocked read of that child's output, and whether releasing it depends on the child producing output** → `04`. This phase records the wiring as a structural fact and files nothing on it.
- **Why to wait, how long, and against which origin** → `03`. **When to fall back from one retrieval method to another** → `03`. **The two-surface parity question — what each surface is told, and whether the two can select different results** → `05`. This phase files the divergence in what is passed; it does not file the policy that chooses between the methods.
- **The effective request rate** — any product of a concurrency figure with a request figure, as a rate against one origin → `03`. **The connection-pool ceiling as a property of the transport** → `04`. This phase files only a literal in its role as **an argument value the child's vector carries**, and only what that value asks the child to do.
- **The retrieval the child performs** — retry taxonomy, backoff distribution, signed-URL staleness, certificate-verification policy, response-size bounds → `03`. This phase owns only the invocation form, the child's own exit status, and the arguments this process constructs.
- **Exit-code mapping, TTY arbitration, the live display, progress rendering and the rule that suppresses child output when a display is active** → `08`. **This phase owns the child's own reporting channel** — the grammar it emits, how it is parsed, and the mechanism by which a line is rewritten and written to the terminal. Where a display exists, `08` decides whether anything is shown; this phase owns how the bytes reach the terminal when something is.
- **A declared setting's meaning, bounds, sourcing and validation** → `02`. This phase owns the **effect** the value has on a child — what it actually limits, and whether the code honours it. The example environment file's bounds → `02`.
- **A dependency declaration in the build manifest** → `11`. This phase owns only the runtime consequence of the invocation form against the version actually present.
- **A documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09` by R-E; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`. **This phase files no `DOC-UPDATE`.** Where a docstring describes a behaviour the code contradicts, the behaviour is filed here once and the wording is `09`'s. A documented backward-compatibility alias that is exported and asserted is **not** dead code and must not be filed here by anyone.
- **Structural arrangement** — import graph, layer direction, cycles, facades, bootstrap order → `01` by R-D. **File-local craft** — typing, naming, module size, a literal duplicated within one file with no runtime consequence → `09`.
- **Whether the test suite proves any of this** → `10`; this phase cites match counts and files nothing from them. **Whether a finding from this phase survives validation** → `99`.
- **Licence posture, terms acknowledgement, notice mechanism** → not an audit subject; inadmissible under `problems-only` and expressly rejected. Do not file.

## 8. Edge Cases

- A file the child's vector names is removed in the instant between the spawn returning and the child opening it.
- Removing that file fails because the child holds it open, on the very path that was supposed to signal it.
- The child writes one line longer than any declared read bound.
- The child writes its last bytes after the parent has already stopped reading.
- The child emits the protocol's end-of-stream marker and then never exits.
- The child's output arrives after the parent has begun tearing the invocation down.
- An exception is raised inside the reader rather than by the child, so no child status exists to judge.
- The child's own status is success and the parent has only a partial capture — or the reverse.
- A child creates a process of its own, and only the child is signalled.
- The escalation is invoked twice, and once against a process that has already exited.
- The escalation is invoked for a process that was never started.
- The availability probe is answered once and the machine changes.
- The tool is absent and one transport reports it as a failure while the other reports it as a status.
- The same child output is emitted to the log and to the terminal, and the two differ.
- The child's output carries a value shaped like a path rather than a URL, and passes through unchanged.
- The downloader's option surface accepts a flag its own help text does not list.
- One surface expresses a filter that the other delegates to the tool.
- The injected asset is not present and the acquisition proceeds anyway.
- The browser's launch fails with an actionable cause and the operator is shown a generic one.
- A resource is created during acquisition and nothing is ever bound to it.
- (Gap: whether the third-party tool or a real muxer enforces or survives what it is given. Observed where possible; otherwise documented. Verify or document — never report as verified.)

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are **not** redefined here.

| Severity | Conditions |
|---|---|
| CRITICAL | An external process outlives the command on a path the product takes, holding a credential, inside no boundary this process can reach or address. |
| HIGH | A named resource the child needs is gone or unusable at the moment the child opens it; a failure to create or destroy it replaces the in-flight outcome and the child is never signalled; the parent's verdict is replaced by a failure in its own reading; a wait with no bound can leave the process unable to return. |
| MEDIUM | What the parent believes a child did is not what the child did, and the difference is silent; a site emits child output with no transform, or a transform cannot match the shape that site carries; an absent dependency is not a gate; two surfaces of one tool diverge in a way that can change the result. |
| LOW | A shape, bound or configuration deviation with no runtime consequence, including an inherited environment nothing restricts, an unbounded accumulation with no observed peak, and a literal where a configured value sits beside it. |

**Type guidance.** `SPEC-DEVIATION` for behaviour contradicting the project's own declared setting, bound or comment. `RUNTIME-ERROR` for anything observed failing at runtime. `BEST-PRACTICE` for a defensible design with a demonstrated risk. **This phase files no `DOC-UPDATE`** — a documented claim belongs to `09` by R-E.

**These conditions are a classification vocabulary, not a verdict.** A finding's severity is composed by this phase from its own run; no severity carried by any preceding document, and none written beside a subject in advance, is inherited. A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity.

## 10. Recommended Sequence

1. Discovery (`## 4`).
2. R9 first — the baseline and the coverage declaration. Every later step is observed against it.
3. R1, then R2. The process tree and the invocation contract are the two highest-risk subjects and the first things a truncated pass must have covered.
4. Blocks (a) through (g) in the order they are written in `## 6`. **Do not reorder by convenience.** This is risk order, descending: a pass cut short must return the high-risk blocks, never the easy ones.
5. R3–R8 as their blocks are reached, each producing the evidence named in that block's `- Evidence:` line.
6. Cross-cutting (`## 7`) and edge cases (`## 8`).
7. Consolidate findings, re-reading `## 7` before writing each one.

**Second-pass order.** If this phase is re-run after a thin result, do **not** start again from step 1. Re-enter at the first block below for which no evidence was recorded, and continue downward: `(a)` every process the application causes is accounted for → `(b)` what the child is told, and what it inherits → `(c)` the reader, the reaper, and the verdict → `(d)` the report made of the child's output → `(e)` whether the binary is there → `(f)` two surfaces of one tool, and its version → `(g)` the browser, before it is used → R9 refreshed last, so it reflects what was actually run. A block with partial evidence is resumed; a block with complete evidence is skipped. R1 and R2 are re-run only if `(a)` has no evidence at all, since their harness is reused. A re-run that finds no new evidence writes `No problems found in this phase.` and stops.

## 11. Finding Prefix

Use `PRC-` for all findings in this phase. `PRC-` is unique in the catalogue: it shares no first two characters with any other phase prefix, and it is obtainable from no other prefix by a single plausible edit — the failure mode that produced two near-identical prefixes elsewhere in this catalogue. It does not encode the phase number, so renumbering never invalidates a published finding ID.

## 12. Reporting

- Write findings to: `.ai/audit/05-subprocess-browser/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) **the exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
  - **No test that patches the process boundary is admissible as evidence for any finding in this phase.** Where the suite is cited, it is cited as the state in which the finding was observed — never as its proof.
  - **No severity is inherited.** A finding carries the severity this phase's own run composes (binding rule 1).
  - **Every documented skip appears in the report, verbatim, with its justification.** Silence reads under `problems-only` as "no finding".
