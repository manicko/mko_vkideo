---
name: 08-cli-observability
status: draft
validated: no
executor: auditor
problems-only: true
---

# 08 — CLI and Observability

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — the platform is this phase's largest quality risk, and block
> (g) is where it bites.** The live-display block is **last** by risk order, and
> it is also the only block whose enabled path cannot be reached on the declared
> platform. Three of its subjects therefore produce a structural fact marked
> `UNVERIFIED`, or a documented skip. **Under `problems-only` that reads exactly
> like "nothing wrong here."** The platform note in `## 5` and skip **R-N** are
> therefore binding obligations, not a trailing note, and **silence on this block
> is not an admissible outcome.** Two consequences are rules, not advice:
> - **No colour-forcing environment variable, no forced flag and no in-memory
>   stream may stand in for a real terminal.** Where one flips one predicate and
>   not another, that is a *predicate disagreement* and is recorded as such.
>   Treating any of them as a terminal **substitutes a false positive for an
>   observation** and the resulting finding is inadmissible.
> - **No through-the-binary claim about the display arbitration, the borrowed
>   handlers or the suppressed child output is admissible.** Such a claim is
>   filed as the structural fact with an explicit `UNVERIFIED` marker, or not at
>   all.
>
> **Binding rule 2 — severities are composed by this phase, never inherited.** The
> analysis that preceded this file carried a problem list with severities written
> beside each entry, and the decision document attached its own adjectives to
> subjects. Neither is citable. Every severity in the report is composed from
> this phase's own run against `## 9`: **record the evidence first, then assign
> the severity.** A reproduction that does not recur is recorded with the exact
> inputs that failed to produce it, and is **never** reported as a clean bill of
> health.
>
> **Binding rule 3 — the two worst subjects are questions, not results.** A run
> that fails during its own start-up and terminates by a path the entry layer
> does not declare, and a run that was stopped and is reported as though it had
> merely failed, were both reproduced before this file was written. **This file
> does not say whether they still occur.** It states the question each answers
> and the harness that answers it — `(b)` with R4, and `(a)` with R2 — and
> nothing else. An executor who finds either outcome written beside its subject
> in this file has misread it.
>
> **Binding rule 4 — the status map is wider than any description of it in the
> decision, and no enumeration of it is written in this file.** R1 enumerates the
> map and tags each status by who chooses it; the map itself is **evidence, not
> scope.** The specific case to look for — a
> status the product's own code never chooses, reached by the product's own
> recovery message that recommends argument values the argument layer then
> rejects — is a case to **establish, not to assume**; R1 establishes it.
>
> **Binding rule 5 — a subject already checked and found correct is absent, not
> annotated: no check row, no verification row, no note, no finding.** This
> holds for the two commands' option surfaces being identical, for the rendering
> of a quality label, and for the display's throttling, zero-total and
> truncation behaviour. **No check is manufactured to fill a verbatim in-scope
> bullet that names one** — several bullets in `## 2` name subjects that
> correctly yield nothing, and their presence there is not an instruction. The
> seam between `03` and `08` over a quality label is **carried by `03` and is not
> carried into this file**; this phase's own half of it is checked and yields
> nothing, and a check invented to fill the `03` half here is itself a defect of
> this phase. A phase that spends a pass confirming correctness is a phase that
> reports nothing.

## 1. Goal

Everything the process emits to its caller — exit status, terminal streams, and the log stream — and whether a failure is diagnosable after the process exits.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| The status the caller receives | Every value the process can return, who chooses each, and which real outcome becomes which | Two outcomes a caller would act on differently sharing one status; a status named in a message but chosen nowhere in the code |
| The account the run renders | The aggregate the status summarises, its labels, and the per-item lines beside them | A label naming a quantity the value does not match; a per-item class the aggregation rule is silent about |
| Declared failures against delivered ones | Every failure the entry layer pairs with a message and a status, and every way a run can end outside that list | A run ending by an undeclared path; a report written to a surface the caller is not reading |
| The records one operation emits | Shape, join key, binding visibility at every dispatch point, and clearing order | Records that cannot be joined; a failure record that names no item; a binding cleared before the failure record is written |
| The log file and the captured streams | The format the file declares against the format it contains; which class of message lands on which stream | A file declared machine-readable that no parser reads whole; a fact readable on one stream only |
| The option surface | What each option declares, against what a value outside that promise does | A help text stating a bound its value does not obey, or naming a source that cannot reach its consumer |
| The live display | What it is handed, which predicate decides it, and what its being active costs the caller | Two predicates that decide one surface disagreeing; a line left non-terminal; borrowed handlers not restored |

**In scope:**
- Command and option design; option precedence between environment and command line, including overrides that bypass re-validation.
- The outcome→exit-code mapping, and nothing about how many values it has, and the **asymmetry between the two commands**; the "non-zero if any item failed" aggregation rule. **R1 enumerates the map; no enumeration of it is written here.**
- Stream discipline: which channel carries which class of message.
- TTY detection and the resulting arbitration between the live display and the child's own native output — including the rule that suppresses the child's output when the display is active.
- The laziness and ordering constraints that keep display construction safe under test (a stream-swap hazard).
- Correlation of emitted records across nesting levels; renderer selection keyed on a setting.
- Repointing root log handlers onto the live display's proxy and restoring them.
- Progress throttling, the never-forwarded zero-total rule, title truncation, and the fallback event emitted when the display is disabled.
- Diagnostic completeness of failure paths; the documented single-vs-batch feature asymmetry (no live display, no peak accounting, no skip accounting).

*Read the second bullet with binding rule 4: the verification row enumerates the
map, and no enumeration of it is written in this file. Read the eighth and ninth
bullets with binding rule 5: they name subjects that produce no check in this
file.*

**Out of scope:**
- Whether a secret appears in what is emitted → `06`.
- The derivation of shutdown state from a signal → `04`.
- The validity of the settings behind an option → `02`.

## 3. Prerequisites

- The project's own verification commands, quoted from `.ai/context/commands.md`: `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>`. `mypy` (strict) is the configured checker; a second checker present in the dev dependency group is **not** it and must not be substituted.
- **No Docker. No database. No service is started.** This phase's real prerequisites are four:
  1. **The installed entry point**, on PATH or invoked through the project's own runner. The exact invocation used is stated once in the report and reused by every row.
  2. **A scratch working directory per run** — a fresh empty directory, never a shared one, so one run's residue cannot answer the next.
  3. **Two distinct capture files per run**, one per standard stream, and a writable log destination.
  4. **In-process reach to the command function and the display object**, for the outcomes no argument shape can produce.
- **All captured output is written to a file and read from a file.** The declared console encoding raises on third-party text containing box-drawing characters; a probe that prints manufactures a failure that is not the product's.
- The declared development platform is Windows. The platform note in `## 5` is binding under preamble rule 1.

## 4. Discovery

Map the contract before checking anything. **Use roles, not names.** No concrete file, module or class name appears in this file. **A subject that maps to nothing is a gap, and a gap is reported.**

1. **Status map** — every value the process can return, the site that chooses each, the per-item statuses that feed the aggregate, and the conditions the argument layer imposes on invocation. The denominator for (a).
2. **Account map** — everything rendered to a caller at the end of a run: the aggregate account, the per-item result lines, every label, and the count beside each label.
3. **Failure-declaration map** — every failure the entry layer pairs with a message and a status, and every site that can end a run outside that list. The denominator for (b).
4. **Record map** — every record one logical operation emits, per sink, with its shape and its join key; every place work is dispatched to; every place a binding is set or cleared. The denominator for (c).
5. **Surface map** — every stream, every log destination, every renderer, and the live display; which is chosen under which declared value. *The declared value's typing, bound and reachability are `02`'s; only which surface is selected, and what the selection makes of the output, is mapped here.*
6. **Option map** — every option each command declares, with type, choices, default and help text; every setting that governs what the process emits, and whether an option reaches it.
7. **Predicate map** — every predicate that decides whether the display is active, every other predicate that decides the display's own behaviour, and the place each is read. Also recorded here as structure: the deferred construction and its ordering, which exist to keep construction safe under a swapped stream.
8. **Evidence map** — the test tree's reach into these subjects, searched **excluding every worktree directory**, whose stale copy of an earlier phase set would otherwise be searched by accident. A subject with no match is declared uncovered **before** it is checked. The mechanisms the search covers are named in `## 5`.
9. **Readiness map** — for every row in `## 5`, which variant produces it, and for any row that cannot run here, the skip text that will be emitted instead.

*Role vocabulary: the two command entry points · the pre-construction environment pass · the status-choosing site · the argument layer's rejection path · the account renderer · the per-item result line writer · the failure-handler table · the correlation-identifier binding site · the log handler and renderer pair · the renderer selection keyed on a declared value · the live display surface and the console object behind it · the terminal-reading predicate · the condition attached to the child-output echo · each place work is dispatched to · each place a binding is cleared · the command runner that replaces the standard streams · the capture fixture · the site that replaces a stream the display module itself holds · the site that forces a terminal onto an injected stream.*

## 5. Runtime Verification (mandatory)

> **The evidence regime, stated once. One harness: the captured run.** Every method below runs the product's own installed entry point locally, in a scratch working directory, with **standard output and standard error redirected to two distinct files** and the process status read from the shell. Two variants are used, and **every row states which variant produced its evidence** and every finding names the variant that produced it: **through the binary** (argument shapes and the process status) and **in process** (the value the entry point returns, for outcomes no argument shape can reach). The project's own runner and the installed console script are both acceptable invocations; state which was used.
>
> **Three mechanical rules, all binding:**
> 1. **Stream separation is done by redirecting the two streams to two files.** A shell's merge redirection renders a native error stream indistinguishably from the shell's own error record. **Evidence gathered that way is not admissible for any stream-discipline finding**, and any method mentioning a stream is inadmissible if its capture merged them.
> 2. **Every capture is written to a file and read from a file.** A probe that prints manufactures a failure that is not the product's.
> 3. **No result reached through the test suite is the evidence for any row below.** A green result is the state in which a finding was observed; the evidence is the capture. Where the suite is cited it is cited for what it does *not* cover, and match counts are recorded as coverage, never filed.

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | Every status the process can return, and who chooses it | **Through the binary.** Invoke the entry point across a fixed argument-shape set — no command, an unknown command, a missing required argument, an unknown option, a value outside a declared choice list, a path argument that does not exist, and one ordinary run that fails — and read the shell's status for each. Separately, capture verbatim the product's own recovery message given for a rejected value, feed **every value it recommends** back to the same entry point, and record the status for each. Then read the product's own status-choosing sites and record which statuses its code names at all. | The argument-shape list; the status per shape; a product-chosen / argument-layer-chosen tag per status; the recovery message verbatim; the status for each recommended value; the set of statuses the product's own code names. |
| R2 | What a stop becomes, per command | **In process.** Set the shutdown state before work begins, drive each unit of work to the value the code returns when it observes a stop, and read three things: the value the command returned, the account it rendered, and the per-item status it assigned. Drive **the identical state** through the other command and read the same three things. Compare the two as a pair. A signal is neither sent nor required — a signal's delivery is another phase's subject and is unreliable on the declared platform. | The returned value, the rendered account and the per-item status, per command; whether either account names the stop; whether the per-item status distinguishes a stop from a failure. |
| R3 | The account's labels, and the rule that aggregates them | **Through the binary.** Drive a batch over a result set whose size and per-item outcomes you chose, read the rendered account verbatim, and for each label record the quantity the label names against the quantity the value is. Do the same for the per-item result lines. Then read the rule that turns per-item statuses into one process status and record, per status class, whether that rule counts it as success, as failure, or is silent about it. | The account verbatim; per label the named quantity and the actual quantity; the per-item lines; the aggregation rule as read and the per-class verdict it gives. |
| R4 | Every declared failure, and what the caller actually receives | **Through the binary, each provocation in a fresh working directory.** Enumerate the failure paths the entry layer declares a message and a status for, and provoke each from what the code's own failure paths key on: an input the configuration layer rejects, a file that cannot be written, a file that cannot be read, a value the parser rejects, and an environment file that is not decodable. For each, capture both streams to two files, read the shell's status, and record three facts: whether the declared message appears at all, which file each part of the output landed in, and whether the terminating exception is one the product raises. | Per provocation: both captures, the status, the declared message present or absent, the stream assignment of each part, and the terminating exception's type and origin. |
| R5 | The record set of one run, and what can be joined from it | **Through the binary** for the run; **in process** for the structure. Drive the batch command over a list that fails, with the log stream captured to a file, and read the record set as a table: per record, the identifier field it carries, the value, the item identity it names, and whether that value equals the one on the enclosing operation's first record. Then, per place work is dispatched to, record whether the operation's binding is visible inside it. Then record, per place a binding is cleared, whether the record describing the failure is written before or after that clearing. | The record set verbatim; per record the identifier presence, value and item identity; the count of distinct identifier values in one run; the parent-reference presence; the per-dispatch-path binding visibility; the clear-versus-write order. |
| R6 | The log file a parser can read | **Through the binary.** Run a real failing command with the log destination enabled, under the configuration the run itself loads. Read the declared format, then read the file: total physical lines, the lines that parse under the declared format, and the class each non-parsing line belongs to — a record split across physical lines, a line with no envelope, a line whose value carries a raw control character. Record one verbatim example per class. Then record what a consumer can extract without stripping anything. | The declared format; the total line count; the parse count and non-parse count; the per-class breakdown with one verbatim example each; the unextracted result. |
| R7 | What the log stream contains when nobody is watching it | **Through the binary.** With both streams redirected to files, read the log stream's bytes and count terminal control sequences; read the other stream's bytes the same way. Then read the configuration that builds the log renderer and record whether a colour decision is passed to it and whether it is conditioned on the stream being a terminal. | The control-sequence count per captured stream; the renderer's construction as read; whether a terminal condition is present or absent on it. |
| R8 | Stream discipline, side by side | **Through the binary.** Run each command once with the streams captured to two distinct files. Fix the message-class partition first, then partition both files and record per class which file it landed in and how many times. Record every class present in both files, and every class whose presence depends on the run having been captured rather than watched. | Both captures; the per-class stream assignment and occurrence count; the classes appearing in both files, with both locations; the classes whose presence is capture-dependent. |
| R9 | The declared option surface, both commands | **Through the binary.** Capture each command's help output to a file. Per option record the declared type, declared choices, declared default and declared help text, and diff the two surfaces. Then record, per option, what a value outside its promise does when supplied. Then list the settings that govern the process's own output and record whether an option exists for each. **The ownership test: does the candidate survive replacing the command line with a direct call into the same function?** Record the verdict; file nothing on a candidate that survives. | Both help captures; the per-option record; the surface diff; per option the promise and the observed behaviour; the output-governing settings with their option presence; the survival verdict per candidate. |
| R10 | Which predicate decides the display, and whether they agree | **In process.** At three moments — before the display starts, at start, and during work — read every predicate the display and the child's echo use, and record each value. Then set, one at a time, each environment variable the terminal-reading code consults as read from that code, and record all three moments again. **No colour-forcing variable is used as a substitute for a terminal:** where one flips one predicate and not the other, that is recorded as a predicate disagreement, never as an enabled display, and no finding built on it is admissible (preamble rule 1). | The predicate values at three moments; the same three per environment variable; the list of variables the terminal-reading code consults, as read. |
| R11 | The display's own lifecycle | **In process.** Construct the display with an explicit console backed by a file, and drive start, work, a terminal transition and stop. Record the value handed in as the per-item label and where that value was produced; whether every line that began work reached a terminal state before stop returned; what the process's own log handlers were bound to before, during and after; and, for each step that raises, whether stop restored them. | The label value and its source; the per-line terminal-state record; the handler binding before, during and after; the restore outcome under each raising step. |
| R12 | Baselines, the coverage declaration and the skip register | **Through the binary and in process, plus one static pass over the test tree.** (a) Run the four verification commands from `## 3. Prerequisites` over this phase's surface; record exit codes and pass/fail/skip counts. **Do not substitute another type checker.** (b) Search the test tree — **excluding every worktree directory**, whose stale copy of an earlier phase set would otherwise be searched by accident — for four mechanisms: a command runner that replaces the standard streams, a capture fixture, a site that replaces a stream the display module itself holds, and a site that forces a terminal onto an injected stream. For each, record the file, the count, and **what the mechanism replaces**. (c) Record separately whether any site asserts that a stream is a terminal, and the count. (d) Record, per row above, which variant produced it, and write the platform note and both documented skips. | The four command results; the per-mechanism file list, count and "what it replaces"; the real-terminal-assertion count; the per-row variant actually used; the platform note and the two skip texts. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how is rewritten here, not skipped at execution time. A `Method` of "inspect the implementation" is not admissible in this phase: every method must produce its evidence by running something.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.** R12's results are never filed as findings; they are the state in which a finding was observed, cited as coverage.

**The stream-swap premise, corrected. It is scoped, not universal.** One command-level test module drives the CLI through a runner that replaces both standard streams for the duration of the call; one other module uses a capture fixture; two sites replace the display module's own view of a stream; two sites force a terminal onto an in-memory stream. **No site anywhere in the suite asserts that a stream is a terminal.** The two sites that exercise terminal-mode behaviour inject a forced-terminal flag on an in-memory stream, which **bypasses the very detection being audited** — they are evidence that the display renders correctly when told to render, and not evidence about when the product decides to render.

**Four consequences, all binding:**

1. **No stream-discipline claim is evidenced from the suite.** A capturing runner collects both streams into one buffer, so a test that "proves" stream discipline proves only that a message was emitted. **Every stream finding in this phase comes from a capture to two distinct files.** The suite is not an admissible oracle for blocks (a), (b), (f) or the account's labels.
2. **Under that runner the display is permanently inactive, so the enabled path cannot be reached through it.** Neither the echo negation, nor the handler repoint and restore, nor the construction the laziness exists to protect, is exercised by any test that goes through the entry point. The two tests that do reach that path inject an override; they **bypass** the decision, they do not test it.
3. **A disagreement between the predicates has no oracle.** Because the two terminal-mode sites bypass the predicate and the non-terminal sites never construct a real stream, a change that made the product read its streams at a different moment would split the predicates and **no test in the suite would notice**. The disagreement is therefore filed as a structural fact with the coverage counted beside it, and **no oracle is manufactured for it.**
4. **The suite's one correct invariant is asserted only on paths that never reach the product's own handlers.** A guard asserting that no traceback reaches the captured output is the right invariant and is correctly written; it is applied to a parser rejection that the product never sees. **The two ways a run actually dies with a traceback on the error stream are on paths the suite does not exercise. Run the binary.**

> **R-N (documented skip — no real terminal on the declared platform).** The live-display path is verified **not** through the binary. Both standard streams report themselves as non-terminals in this environment, so the display the production code constructs is inactive and the enabled path — the lazily built console, the stream proxy it installs over the error stream, and the handler repoint and restore — cannot be reached from outside the process. It is verified in process instead, by constructing the display with an explicit console and driving its lifecycle directly. **Consequence for the report: no finding in this phase may state a runtime consequence observed through the binary for the display-arbitration, handler-repointing or child-output-suppression subjects.** Such a finding is filed with the structural fact and an explicit **`UNVERIFIED`** marker on the through-the-binary claim. **Silence is not an option: under `problems-only`, silence reads as "no finding".**
>
> **Do not** substitute a colour-forcing environment variable for a terminal. Those flip the display's own terminal reading while leaving the activity decision where it is. They demonstrate a predicate disagreement; they do not enable the display, and treating one as a terminal substitutes a false positive for an observation.
>
> **What a real terminal would unblock:** a genuine interactive console session, or a pseudo-terminal. Neither is a declared dependency and **adding one is out of scope for an audit phase.** The documented skip is the correct outcome.

> **R-S (second documented skip — the teardown's exception-safety trigger is not observable).** It requires a failure injected at one instant inside the display's teardown, which is a **substitution, not an observation.** That subject is filed as **ordering**, with the trigger marked `UNVERIFIED`. **Do not manufacture a reproduction for it.**

## 6. Audit Dimensions (checks + evidence)

The seven blocks are ordered by risk, **descending**. The letter order **is** the re-entry order (`## 10`): a pass cut short returns the blocks it reached. **Executability does not reorder risk** — the live-display block is the most mechanical subject in the phase and is still last, because a truncated pass must return the high-risk blocks first. **No block title or description states an outcome**; each is the question, and the finding is named as a condition to look for.

### (a) The Status and the Account That Produces It

> Everything the run ends with that its caller reads: the status the process returns, and the account it renders that the status summarises. Enumerate the statuses the process can actually produce and tag each by whether the product's own code or the argument layer chooses it. Drive each real outcome — a completed run, a handled failure, a stop, a misused command line, a run that did no work — through each command and record which status it becomes. Then read the rendered account against what it claims to count: per item, per class of item, in aggregate. Where an interrupted run, a rejected argument, or a run in which nothing happened reports the same status as an ordinary failure, that indistinguishability is the finding. *The accuracy of a concurrency figure inside the account is `04`'s; the label that names it and the counts beside it are this phase's.*

| Check | Description | Evidence required |
|---|---|---|
| The status set is enumerated, not inherited | Every status the process can return is read off the code, and each is tagged product-chosen or argument-layer-chosen. A status named in a message and chosen nowhere in the code is a finding about the product's own contract | R1 |
| Each real outcome is driven through each command | A completed run, a handled failure, a stop, a misused command line, and a run in which nothing happened; the status each becomes is recorded for both commands | R1, R2 |
| The two commands are compared as a pair | The identical outcome driven through the other command, and the account each rendered. A difference between the two is the finding and is not averaged into a description of either | R2 |
| A stop is distinguishable from an ordinary failure in what the caller receives | Returned value, rendered account and per-item status are read for a stop and for an ordinary failure. The same status and the same account for both is the finding. **This file does not say which of the two behaviours the product has** (preamble rule 3) | R2 |
| The recovery instruction is followed to its end | The product's own message given for a rejected value is captured verbatim, **every value it recommends** is fed back, and the status each produces is recorded. A recommendation routed into a status the product's own code never chooses is a finding; the case is **established by R1, not assumed here** (preamble rule 4) | R1 |
| Each label is read against the quantity beside it | Per label, the quantity the label names against the quantity the value is, in the aggregate account and in the per-item lines | R3 |
| The aggregation rule is read per status class | For each per-item status class, whether the rule counts it as success, as failure, or is silent about it | R3 |

- Evidence: R1, R2, R3, R12.

*Internal de-duplication rule: indistinguishability between two outcomes is (a)4; a label whose quantity does not match is (a)6. Where two rows cite the same run, it is cited by its id once.*

### (b) A Failure That Escapes the Handler Meant to Report It

> The entry layer declares a message and a status for each way a run can fail. Ask, for each declared failure, whether provoking it produces that message on that status — or whether the run terminates by a path the product does not describe: an exception raised while the failure is being reported, a handler that reports on a value it never received, a report written to a surface the caller is not reading. Provocations are chosen from what the code's own failure paths key on, and each runs in a fresh working directory so one run's residue cannot answer the next. The finding is the divergence between the failure the product declares and the failure the caller receives, not the type of the exception that escaped.

| Check | Description | Evidence required |
|---|---|---|
| The declared failure set is enumerated first | Every failure the entry layer pairs with a message and a status, listed before any is provoked. This list is the denominator | R4 |
| A failure outside the declared set is recorded as such | Every site that can end a run without passing through that list is enumerated, and for each the status and message the caller receives. A path the product does not describe is the finding, filed once, here. **This file does not say that one exists** (preamble rule 3) | R4 |
| Each declared failure is provoked from the code's own trigger | An input the configuration layer rejects, a file that cannot be written, a file that cannot be read, a value the parser rejects, an environment file that is not decodable — each in a fresh working directory | R4 |
| The declared message and the declared status are read together | Per provocation: whether the declared message appears at all, and what status the shell recorded. A failure declared on one status and delivered on another is the finding | R4 |
| A report written to a surface the caller is not reading is named | Per provocation, which of the two distinct capture files each part of the output landed in. A capture that merged the streams is inadmissible here and the provocation is re-run | R4 |
| A handler that never received its value is distinguished from one that was never reached | Per provocation, the terminating exception's type and origin. **The escape is the finding; the exception's type is never filed as a second finding** | R4 |

- Evidence: R4, R12.

### (c) The Records That Can Be Joined to One Failure

> One logical operation emits many records, across nesting levels, in more than one shape. Read the record set of a single real failing run as a table: for each record, the identifier field it carries, its value, the item it names, and whether that value walks back to the operation that began it. Record, separately and as structure, whether each place work is dispatched to can see the operation's binding at all, and whether anything clears the binding before the record describing the failure is written. Record, per sink, the shape a record takes there and what a reader must strip before it can parse one. A run whose records cannot be joined, or whose failure record names no item, is the finding. *The identifier's lifecycle is `01`'s; whether a secret appears in a record is `06`'s.*

| Check | Description | Evidence required |
|---|---|---|
| The record set is enumerated before any record is judged | Every record one logical operation emits, per sink, read as a table. This list is the denominator | R5 |
| Each record's join key is read | Per record: the identifier field it carries, its value, and whether that value equals the one on the enclosing operation's first record. More than one distinct value inside a single run is the finding | R5 |
| A failure record that names no item is found | Per record, the item identity it names; a failure record naming none is the finding | R5 |
| Binding visibility is recorded per dispatch path | For each place work is dispatched to, whether the operation's binding is visible inside it | R5 |
| Clearing order is read against the failure record | For each place a binding is cleared, whether the record describing the failure is written before or after that clearing | R5 |
| Per sink, what a reader must strip is recorded | The shape a record takes at each sink and the transformation a parser needs before it can read one. **Whether a given transformation is invoked at a given sink is cited, not re-derived** | R5, R6 |

- Evidence: R5, R6, R12.

*Independence note: (c) and (d) share a surface and nothing else. (c) is answered by reading and joining a run's records; (d) by parsing the file that run wrote. They are not merged, so a truncated pass returns one whole and not half of each.*

### (d) The Log File a Machine Is Expected to Read

> When the process is told to write a log file, it declares a format for it. Read the declaration, then read the file a real failing run produced: total physical lines, the lines that parse under the declared format, and the class each non-parsing line belongs to — a record split across physical lines, a line with no envelope, a line whose value carries a raw control character. A file the product declares machine-readable that no parser reads as a whole is the finding. Record, once, what a consumer can extract without stripping anything. *What a secret appears in is `06`'s; the file's own access mode and location are `07`'s.*

| Check | Description | Evidence required |
|---|---|---|
| The declared format is read from the configuration the run loads | The format is what the code actually asks the writer for under the configuration that run used — not a default, and not a comment | R6 |
| The file is parsed, not skimmed | Total physical lines, the lines that parse under the declared format, and the count that does not | R6 |
| Every non-parsing line is classified, with one verbatim example per class | A record split across physical lines, a line with no envelope, a line whose value carries a raw control character | R6 |
| The unextracted result is recorded once | What a consumer obtains from the file with nothing stripped | R6 |
| A declared format and a delivered format are compared in one finding | The declaration, the measured parse count and one verbatim non-parsing line are its evidence. **The count on its own is not a finding and is never filed as one** | R6 |

- Evidence: R6, R12.

### (e) The Declared Option Surface

> What the command line promises, against what it does. For each option on each command, record the declared type, the declared choices, the declared default and the declared help text. Then record, per option, what happens when a value outside its promise is supplied, and whether the help text states the bound that value obeys, the source it can be reached from, or the fact that the source it documents cannot take effect. Finally, list the settings that govern the process's own output and record whether an option exists for each. *A defect of the model behind an option is `02`'s; the test for which is whether the finding survives replacing the command line with a direct call into the same function.*

| Check | Description | Evidence required |
|---|---|---|
| The declared surface is recorded per option, per command | Declared type, declared choices, declared default and declared help text, captured from each command's own help output. The two surfaces are diffed as part of the capture; a difference is a **question about intent**, not a defect on its own, and the subjects already checked here produce no row (preamble rule 5) | R9 |
| A value outside an option's promise is supplied | Per option, the promise and the observed behaviour when it is exceeded | R9 |
| The help text is read against what the option does | Per option, whether the help states the bound the value obeys, the source it can be reached from, or that the documented source cannot take effect | R9 |
| Every output-governing setting is matched against the options | A setting that governs what the process emits, with no option that reaches it, is a finding **about the option surface**. The setting's own typing, bound, sourcing and reachability are `02`'s and are cited, not filed | R9 |
| Each candidate passes the ownership test before it is filed | Does it survive replacing the command line with a direct call into the same function? Yes → `02`, cited and not filed. No → this phase. The verdict is recorded per candidate | R9 |

- Evidence: R9, R12.

### (f) Which Stream Carries Which Class of Message

> The process writes to more than one stream, and the caller may read only one. For a single run of each command, capture the streams to two distinct files and build a table: for every distinguishable class of message the run produced, which file it landed in, and how many times. Record every class that appears in more than one file, and every class whose arrival depends on whether the run was captured rather than watched. Then read the conditions attached to the log renderer itself and record whether the stream it writes to is ever treated as a terminal. A fact the caller can read on one stream and not on the other is the finding.

| Check | Description | Evidence required |
|---|---|---|
| Both streams are captured to two distinct files, per command | A shell's merge redirection is **inadmissible** for every row in this block. Where a capture merged them, the run is repeated with separate redirection | R8 |
| The class partition is fixed before the counts are read | Every distinguishable class of message the run produced, listed first; then per class, which file it landed in and how many times | R8 |
| A class present in both files is named | The class, both files and both counts | R8 |
| A capture-dependent class is found | The same command run watched rather than captured, and the two class tables diffed. A class that appears only under capture is the finding | R8 |
| The log renderer's own stream conditions are read | Whether a colour decision is passed to it, and whether it is conditioned on the stream being a terminal. Control sequences written into a captured stream are the finding; the per-stream counts are its evidence | R7 |
| No row in this block is evidenced from the suite | A runner that collects both streams into one buffer cannot decide stream discipline. Every row here comes from the two distinct files (consequence 1 above) | R8, R12 |

- Evidence: R7, R8, R12.

### (g) The Live Display and What It Decides

> The display is a surface the product builds, arbitrates, and repoints the process's own log records onto. Record three things about it. What value it is handed as the per-item label, and whether that value is the one a reader would recognise. Which predicate decides whether it is active, whether that predicate agrees with the ones deciding the rest of its own behaviour, and whether they are read at the same moment. What its being active costs the caller: the channel it suppresses, and whether what it suppressed reaches any surface the caller reads. Then drive its lifecycle in process — start, work, terminal transition, stop — and record whether every line that began work reached a terminal state, and whether the handlers it borrowed are restored when a step raises. **No real terminal exists on the declared platform; R-N and preamble rule 1 govern this whole block, and an unevidenced subject here reads as clean.**

| Check | Description | Evidence required |
|---|---|---|
| The per-item label is recorded and traced | The value handed in as the label, and where that value was produced. A value a reader could not recognise as an item is the finding | R11 |
| Every predicate is read at three moments | Before the display starts, at start, and during work; each value recorded for each predicate | R10 |
| The moment each predicate is read is recorded | Whether the predicates that decide one surface are read at the same moment | R10 |
| A predicate disagreement is filed as a structural fact, with coverage beside it | The coverage count is **evidence, never a finding of its own.** The suite has no oracle for a disagreement and none is manufactured (consequence 3 above) | R10, R12 |
| No substitute stands in for a terminal | **Where a colour-forcing variable flips one predicate and not another, that is recorded as a disagreement and nothing else.** No such run is reported as an enabled display and no finding rests on one (preamble rule 1) | R10 |
| What being active costs the caller is recorded | The channel it suppresses, and whether what it suppressed reaches any surface the caller reads. The child's own reporting channel and the pipes are `05`'s; **this is the arbitration only** | R8, R10 |
| Every line that began work reaches a terminal state | Start, work, a terminal transition and stop driven in process against a file-backed console; the per-line terminal-state record captured | R11 |
| The borrowed handlers are bound and restored | What they were bound to before, during and after, recorded as three separate facts | R11 |
| The teardown's exception-safety is filed as ordering only | It is filed as **ordering**, with the trigger marked `UNVERIFIED` under R-S. **No reproduction is manufactured for it** | R11 |

- Evidence: R8, R10, R11, R12. **Governed by R-N and preamble rule 1: no through-the-binary claim in this block is admissible, and a subject left unevidenced is reported, not omitted.**

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **Renderer selection and its effect on the emitted output** → **this phase.** *Ruled:* the **declared setting** that governs it — whether it is typed, bounded, reachable and consumed — is `02`'s; the **selection, and the difference the selection makes to what a reader receives**, is this phase's. The two are one line so neither half is filed twice.
- **The declared format of the log file, and whether a parser can read what it declares** → **this phase.** *Ruled:* the decision assigned only the file's permission mode and left its format unowned. A log stream's format is an output-surface decision and belongs with the sink.
- **A file's permission mode, creation mode, atomicity and cleanup** → `07`, regardless of what the file contains. The credential file's mode, and the access state actually in force, → `06`. **The log file's mode is `07`'s; only its format is this phase's.**
- **Whether a secret appears in anything emitted** → `06`, always and never re-assigned. This phase files a record's shape and its join key, never its contents.
- **Correlation-identifier generation, binding, inheritance and clearing** → `01`. **Rendering and sink of the identifier** → this phase. This phase owns only that the identifier appears in the record, under what key, and whether a reader can join on it.
- **Shutdown-state derivation from a signal, the event's creation, ownership and cross-loop visibility** → `04`. **The stop → outcome translation — which process status the observation becomes, and what the account says about it** → **this phase**, by elimination: the decision assigned the observation to `04` and left the translation unwritten, and `04`'s own file states the mirror. **Residue a stopped run left on disk is `07`'s; the silence about that residue is this phase's, and is filed once, here.**
- **The `02`/`08` override seam** → *a construction applied programmatically that skips re-validation is `02`'s; the declared option contract is this phase's.* **Test:** *does the finding survive replacing the command line with a direct call into the same function?* If yes → `02`, cited and not filed. If no → this phase. A value the model admits outside its declared range survives; an option whose own declaration omits the range does not, and is this phase's.
- **Whether a declared value is typed, bounded, sourced and reaches its consumer** → `02`. This phase owns only whether an option exists for it and what that option declares. The example environment file's claims about the command line are `02`'s to validate and this phase's to state; the *wording* of every other document is `09`'s.
- **The placement and ordering of the start-up steps, and the wiring of the pre-construction pass into each entry point** → `01`. **What the caller receives when a failure happens inside that pass — what reaches each stream, whether the declared message survives, what status the process returns** → **this phase. The emission of the diagnostic, and the consequence of the inconsistent output it produces, are `02`'s; what the caller receives is this phase's.**
- **A service module that decides the process outcome, and the entry layer's own thinness** → `01`. This phase owns only the status that decision produces.
- **The error taxonomy's internal consistency — code to exception to label to user message** → `09`. **Whether a run terminates by a path its own handlers do not declare, observable only by reading both streams and the status together** → **this phase.** The taxonomy is `09`'s; a handler that cannot report the failure it exists for is this phase's, and `09` carries the mirror: *"The taxonomy's own consistency — declared code to condition to label to user message → `09`. The taxonomy is `09`'s; a handler that cannot report the failure it exists for is `08`'s, and `08` carries the mirror."*
- **The child's own reporting channel — the progress grammar, the in-place rewrite, which pipe carries what** → `05`. This phase owns only **the arbitration**: when the child's output is suppressed, which predicate decides, and where the suppressed output goes.
- **A quality label a selection produced, and its appearance in an error's list of alternatives** → `03`, and **that half is not carried.** This phase's own half of it yields nothing; **no check, no row and no finding exist for it in this file, and none is to be manufactured to fill an in-scope bullet that names it.**
- **The accuracy of a reported concurrency figure, and whether a permit was actually acquired** → `04`. **The label that names that figure, and the counts beside it** → this phase.
- **A documented claim about anything other than the command-line contract** → `09`. **File-local craft** — typing, naming, module size, and the consistency of one module's own message text → `09`.
- **Whether the test suite proves any of this, and the form its guards take** → `10`; this phase cites mechanism counts and files nothing from them. **The absence of a real-terminal oracle is `10`'s; the predicate disagreement it leaves without a witness is this phase's, and the coverage is cited in the evidence.**
- **A dependency declaration in the build manifest, secret scanning, repository hygiene** → `11`. Whether a finding from this phase survives validation → `99`.
- **Licence posture, terms acknowledgement, notice mechanism** → not an audit subject; inadmissible under `problems-only` and expressly rejected. **Do not file.**

## 8. Edge Cases

- No command at all · an unknown command · a missing required argument · an unknown option · a value outside a declared choice list · a path argument that does not exist.
- An environment file that cannot be decoded · a log destination whose parent cannot be created · a log destination that is itself a directory.
- A run in which every item fails · a run in which every item is skipped · an empty URL list · a run in which nothing happened.
- A run that is stopped before any work begins · a run stopped part-way with some items already finished.
- A value supplied twice, once by environment and once by argument · an option whose value is outside a bound the model enforces elsewhere.
- A run whose output is watched rather than captured · a run whose output is piped rather than written to a file · a consumer that reads one stream and not the other.
- A display that starts after work has already begun · a display stopped while a line is still in a non-terminal state · a step in the display's teardown that raises.
- A predicate flipped by an environment variable in one place and read before it is set in another — **recorded as a disagreement, never as an enabled display** (preamble rule 1).

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are **not** redefined here.

| Severity | Conditions |
|---|---|
| CRITICAL | A run terminates by a path the product's own handlers do not declare, and the status the caller reads does not distinguish that from success or from an ordinary failure. Or a failure of any kind leaves the caller unable to tell what failed, because no surface the caller reads records it. |
| HIGH | A stop and an ordinary failure produce the same status and the same account, so a cancelled run and a failed run are indistinguishable to any caller reading either. Or a log file the product declares machine-readable contains lines no parser reads as a whole, so the diagnosis the file was written to carry is not recoverable from it. Or a fact a caller must act on appears on one stream and not the other, and the caller reads the one that omits it. |
| MEDIUM | Two outcomes a caller would act on differently report the same status. A record set from one run that cannot be joined on its own join key. An account label naming a quantity its value does not match. An option whose help text states a bound its value does not obey, or names a source that cannot reach its consumer. A message class whose arrival depends on whether the run was captured rather than watched. |
| LOW | A per-item status class the aggregation rule is silent about. A record whose shape at a sink needs a transformation before a reader can parse it, where none was lost. A failure record that names the operation but no item. A help-text omission with no observed consequence. |

**Type guidance.** `SPEC-DEVIATION` for behaviour contradicting the product's own declared status, message, format or help text. `RUNTIME-ERROR` for anything observed failing at runtime, including a run that terminates by an undeclared path. `BEST-PRACTICE` for a defensible contract with a demonstrated gap. **This phase files no `DOC-UPDATE`** — a documented claim is `09`'s, and the example environment file's claims about the command line are `02`'s.

**These conditions are a classification vocabulary, not a verdict.** A finding's severity is composed by this phase from its own run; no severity carried by any preceding document, and none written beside a subject in advance, is inherited (preamble rule 2). A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity. **A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded, never as a clean bill of health.**

## 10. Recommended Sequence

1. Discovery (`## 4`).
2. **R12** first — the baselines, the coverage declaration and the skip register. Every later step is observed against it, and the platform note and both skips are written before the first subject is checked, so a later silence is a reported skip and not an omission.
3. R1, R2, R3 — the status contract, both commands.
4. R4 — every declared failure provoked, each in a fresh working directory.
5. R5, R6, R7, R8 — the records, the log file, the captured stream, and the two streams side by side.
6. R9 — the option surface.
7. R10, R11 — the display, in process.
8. Blocks (a) through (g) in the order they are written in `## 6`. **Do not reorder by convenience, and do not reorder by how easy a subject is to prove** — (g) is last because it is lowest risk, not because it is easiest.
9. Cross-cutting (`## 7`) and edge cases (`## 8`), re-reading `## 7` before writing each finding.
10. Consolidate findings.

**Second-pass order.** If this phase is re-run after a thin result, do **not** start again from step 1. Re-enter at the first item below for which no evidence was recorded, and continue downward: **R12 → R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → (a) → (b) → (c) → (d) → (e) → (f) → (g)**. A block with partial evidence is resumed; a block with complete evidence is skipped. A re-run that finds no new evidence writes `No problems found in this phase.` and stops — **and, under preamble rule 1, that line is only admissible once (g)'s subjects have been reported as structural facts, `UNVERIFIED` markers or documented skips rather than omitted.**

## 11. Finding Prefix

Use `OUT-` for all findings in this phase. `OUT-` is unique in the catalogue: it shares no first two characters with any other phase prefix (`EN CF NE CO PR SE AR OU QL TS DE VA` are all distinct), and it is obtainable from no other prefix by a single plausible edit — the failure mode that produced two near-identical prefixes elsewhere in this catalogue. It does not encode the phase number, so renumbering never invalidates a published finding ID.

## 12. Reporting

- Write findings to: `.ai/audit/08-cli-observability/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) **the exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
  - **Every finding names which harness variant produced it** — through the binary with the two streams captured to two files, or in process. A finding whose consequence was observed in process is **never** described as observed through the binary.
  - **Every finding carries the admissibility of its own capture** — for a stream finding, the two distinct files it was read from. A finding read from a merged capture is not reportable.
  - **A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded**, never as a clean bill of health.
  - **No row, table or note is offered for a subject that was checked and found correct**, and none is manufactured to fill an in-scope bullet that names one (preamble rule 5).
  - **The `08` half of the live-display block is always reported** — as a structural fact with an `UNVERIFIED` marker, or as documented skip R-N or R-S. **Silence is not an admissible report** for that block (preamble rule 1).
  - **The report contains no severity, no outcome and no quoted text inherited from any preceding analysis or from the decision document**, including any enumeration of the status map and including any wording this file quotes only to place it in `## 2`.
