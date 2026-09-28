---
name: 10-test-coverage
status: draft
validated: no
executor: auditor
problems-only: true
---

# 10 — Test Coverage

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — severities and subjects are composed by this phase's own
> run, never inherited.** The analysis that preceded this file carried
> measurements, a ranked subject list and severities attached to subjects. None
> of it is citable. **A number written beside a subject would be a pre-answered
> outcome by another name; there are none here, and none may be added.** Record
> the evidence first, then assign the severity.
>
> **Binding rule 2 — the inherited file's findings section is deleted with no
> replacement, no summary, no pointer and no successor carrying the same
> material.** It cited more than twenty artefacts that do not exist in this
> repository, and its closing line declared the suite trustworthy — a verdict
> measurement contradicts and no executor of this phase may inherit it. Worse, a
> pre-satisfied section reads as a completed phase: under `problems-only`,
> **silence about a defect that was not found is indistinguishable from a clean
> result.** No prior report is named here as a source of expected outcomes. A
> research document may be cited for the enumeration of subjects and for a
> method, never for an outcome.
>
> **Binding rule 3 — three subjects invite a conclusion before the check. Each is
> filed only in the form below.**
> - *Coverage.* The absence of a **name reference** to a body is a name-level
>   fact, not evidence of absence: a body reached indirectly can execute while no
>   test names it. The question is **what assertion could fail on it**, never
>   whether a file exists for it.
> - *Fidelity of a stand-in.* That a boundary is never crossed for real is a fact
>   and is filed. That the stand-in **misrepresents** the boundary is a
>   conclusion that requires running the real boundary, which this phase cannot
>   do, and **is not filed**.
> - *Agreement between guards.* Whether the platform guards agree with one
>   another is unobservable by construction — the guards are what make it so. The
>   **form** each oracle takes is filed; agreement between forms is not.
>
> **Binding rule 4 — repeating a run proves nothing.** A hermetic suite and an
> unisolated one both repeat identically, so stability is established by
> **varying** the environment (R5), never by re-running. An executor who files
> "deterministic" from R1 alone has not run the check.
>
> **Binding rule 5 — a subject already checked and found correct is absent, not
> annotated: no check row, no verification row, no note, no finding.** Bullets in
> `## 2` name such subjects; their presence there is not an instruction, and **a
> check invented to fill one is itself a defect of this phase.**

## 1. Goal

Whether the suite is a deterministic, non-tautological, measured and gated proof of the behaviour the other ten phases own.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| Oracles for the subjects other phases claim | Which production bodies a test can fail on | A body no assertion reaches while a test's name claims it |
| Inputs the suite does not supply | Environment, working directory, resolved files, clock, random source | A documented input silently deciding a test's outcome |
| Substituted objects | What the suite replaces, and what the replaced thing was | The subject, or a primitive the runtime schedules on, replaced — making any oracle impossible |
| Oracles under absent conditions | Terminal, signal delivery, access-control state | A reported pass that executed no assertion |
| What an assertion is made of | The provenance of every compared value | A value the test configured read back as a result |
| Configuration and enforcement | Implicit defaults, markers, coverage measurement, what runs on a change | Nothing declared, nothing measured, nothing enforced |
| Shared setup and references | Where setup lives, what restores it, what the documentation claims | Setup one file owns that another will need; a reference that no longer resolves |

**In scope:**
- Coverage of the highest-risk paths, weighted by the surface area claimed by the other phases rather than by line count.
- Mock discipline and the boundary at which mocking stops being legitimate — specifically: the entire process, browser and HTTP boundaries are mocked, so nothing exercises them.
- Tautology and self-confirming assertions; determinism and ordering dependence.
- The production-code-is-king rule.
- Fixture hygiene and the absence of a root conftest.
- The absence of any coverage measurement or gate; the absence of any test configuration file, and the plugin default that follows from it.
- The absence of an integration tier.
- **Platform coverage:** what is asserted on one platform only, and whether that platform is the one developers use.
- CI execution of the suite and of the static checks.

*Claims made inside the bullets — a boundary named as mocked, a file named as absent, a platform named as the only one — are the decision's scope, not this phase's evidence. Each is re-derived by the R-row named in the block that owns it, and a claim re-derived as matching is filed as nothing. Read the list as the decision wrote it and not as a checklist of dimensions: a bullet naming a subject that produces no check in this file is not an instruction, and no check is manufactured to fill one (binding rule 5).*

**Out of scope:**
- Pipeline jobs that are not test execution → `11`. Building an integration harness — **report the absence as a gap; do not file it a second time against production code.**

## 3. Prerequisites

- **The project's own verification commands, quoted from `.ai/context/commands.md`:** `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>`. `mypy` (strict) is the configured checker; **a second checker present in the dev dependency group is not it and must not be substituted.**
- **No container. No database. No service is started — a phase that needs one is misdesigned.** This phase's own prerequisites:
  1. **A scratch directory outside the repository's test tree**, for the R12 probe and for anything a tool leaves behind. It is written and deleted there, never in the tracked tree.
  2. **The ability to set and unset one process environment variable at a time, and to run the suite from a chosen working directory.** R5 cannot be performed without both.
  3. **An ephemeral dependency overlay that leaves the build manifest and the tracked tree byte-identical.** It is supplied for the duration of one command and is not added to the project; a clean working-tree check is run after R2 and after R12.
- **Repository-wide searches exclude every worktree directory.** A stale copy of an earlier phase set would otherwise be searched by accident, and a match count taken from it is wrong in the direction that makes this phase look covered.

## 4. Discovery

Map the contract before checking anything. **Use roles, not names** — no concrete file, module or class name appears in this section. **A subject that maps to nothing is a gap, and a gap is reported.**

1. **Subject map** — every behaviour each sibling phase names as its subject, and the production body behind each. The denominator for (a). *The naming of a subject is the owning phase's; only the body and its oracles are mapped here.*
2. **Oracle map** — per body, every assertion the suite can make fail on it: the test, the compared value, and where that value came from. The denominator for (a) and (e).
3. **Input map** — every input a run's result could depend on that the suite does not itself supply: the process environment, the working directory and anything resolved from it, the clock, the random source, and the process-global registries a test mutates. The denominator for (b).
4. **Substitution map** — every substituted object, per test, with the substituted symbol's dotted name; and every external boundary role with the count of unpatched constructions. The denominator for (c).
5. **Guard map** — every conditional and every skip guard in the suite, the condition each keys on, and whether the suite ever supplies that condition. The denominator for (d).
6. **Setup map** — where the suite's shared setup lives, how many files carry one, how much of it there is, what each piece mutates and what restores it. The denominator for (g).
7. **Configuration map** — every file the test framework recognises as its configuration, at the repository root and in the test tree, plus every marker the suite uses. The denominator for (f).
8. **Reference map** — every finding-shaped identifier and cross-reference the suite carries in its own documentation and comments, and every workflow definition in the repository. The denominator for (h) and for the enforcement half of (f).
9. **Evidence map** — for every row in `## 5`, which method produces it, and for any row that cannot run here, the skip text that will be emitted instead. **A row with no method mapped is not executed, and is reported as not executed.**

*Role vocabulary: the test runner · the suite's configuration file, if one exists · each test module · the shared setup module or modules · every substitution site and the stand-in it installs · every conditional guard and every skip guard · every marker the suite applies · the coverage measurement, if one is declared · each workflow definition and each job inside it · the environment-file reader · the process-global registry a test mutates · the production body behind each sibling-named subject.*

## 5. Runtime Verification (mandatory)

> **The evidence regime, stated once. Two harnesses and only two:** a **run of the suite** through the project's own runner against the product's own tree, and a **static pass** over the source tree and the test tree. Nothing is reached through a substituted object except where a method says so on purpose. Four mechanical rules, all binding:
> 1. **No assertion reached through the suite is the evidence for any row.** A green run is the state in which a finding was observed, never its evidence. Where the suite is cited it is cited for what it does *not* cover, and a match count is recorded as coverage, never filed.
> 2. **The coverage measurement is supplied ephemerally and is removed.** It is an instrument, not a dependency: this phase reports what is not declared and **prescribes no package** — declaring one belongs to `11`. Whatever the overlay leaves behind is deleted and a clean working tree is confirmed. **The ignoring of that artefact is `11`'s to change, and is cited, never filed.**
> 3. **A method that cannot run here emits a documented skip, in fixed wording:** *what was attempted, why the evidence is unobtainable, what remains verifiable, and which phase owns the unverifiable half.* **`n/a` and silence are inadmissible** — under `problems-only`, silence reads as "no finding".
> 4. **No method stands in for a condition the environment does not produce.** A variable or an injected flag that flips a predicate without producing the real thing is recorded as a disagreement and nothing else, and no finding rests on it.

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | Suite baseline and stability | `uv run pytest <path> -q -p no:cacheprovider` twice, plus `uv run pytest <path> --collect-only -q`; then a third run with the R2 overlay absent. | Collected / passed / failed / skipped / warning counts and wall time; whether the three runs agree. **Admissibility note: identical runs are the state in which a finding was observed, never evidence that the suite is isolated** (binding rule 4). |
| R2 | Coverage measurement, supplied ephemerally | `uv run --with pytest-cov pytest <path> --cov=<package> --cov-report=term-missing`. The overlay installs for that one command and writes nothing to the build manifest. **It leaves a coverage data file that is untracked and un-ignored:** delete it, then run a working-tree check and record that the tree is clean. | Per-module statements / missed / percent; the complete missing-line set; the project total; the clean-tree check. |
| R3 | Body coverage of a named subject | Intersect R2's missing-line set with the statement range of the production body a test's name or documentation claims; **obtain the range by parsing the source, not by reading it.** Fallback where R2 is unavailable: enumerate the body's statements and search the tests for a literal only that body can produce — **an inference, not a measurement, and a finding built on it is filed as the weaker form with the reason recorded.** | The body, its statement range, the missing lines inside it, the claiming test; the fallback marked as a fallback. |
| R4 | Bodies reachable only through a mocked boundary | For each boundary role, count the suite's substitution sites for its symbol and record the role each belongs to. **Crossing the boundary for real is a documented skip in the fixed wording** — it is unobtainable here and is not simulated. **A count tells you the boundary was never crossed for real; it does not tell you the stand-in is wrong, and that is not filed** (binding rule 3). | The boundary role; the site count; the skip text. |
| R5 | Environment dependence | For each documented product environment variable, set that one variable alone in the shell, run the suite subset that reads settings, and record the pass/fail delta against the same subset unset. Then repeat with an environment file present in the working directory, and again from a second working directory. | Per variable: the tests it moves and the delta. The two working-directory verdicts. **A variable that moves one test is a finding recorded by that variable's name — never summarised as "the environment".** |
| R6 | Per-test independence | Run each test file alone; run the whole suite; then run the suite with the files that mutate process-global state passed first as explicit path arguments. For every restoration mechanism the suite declares, run its owning test followed by a probe test that reads the state it mutates. | Per-file result against the whole-suite result; the reordered result; each probe's reading. |
| R7 | Real boundary crossings | For each external boundary role — network client, child-process spawn, browser driver, media-tool binary, filesystem root, PATH probe, clock, random source — search the suite for an unpatched construction of it, and check that every substitution site for that symbol is unconditional. | The count per role and the site list. **A role whose count is zero is the finding.** |
| R8 | Replaced-object triage | Resolve every substitution target to its dotted name and classify it: the subject itself / a primitive the runtime uses to schedule the test / a production model whose own validation is part of the subject / a legitimate external boundary. | The per-class counts, and every site in a disqualifying class with the class it was given. |
| R9 | Self-substitution and assertion subject | Per test, extract the dotted names it passes to substitution from its own source segment and intersect them with the symbols it imports from the product. Then, per assertion, record where the compared value came from: the code under test, a value the test configured into a stand-in, or a read-back of the stand-in's own call record. | The intersections; the classification of every assertion in either self-confirming class; and for each asserted count or ordering, whether a call from outside the subject could satisfy it. |
| R10 | Conditions the environment never supplies | For every conditional and skip guard in the suite, record the reported outcome and whether an assertion body executes. For each behaviour gated on a condition the environment does not produce, record whether **any** test supplies it — established by having a test read the real terminal-attachment state of each standard stream and the real access-control state of a file it creates, **not by searching for it.** | Reported outcome and assertion-body count per guard; per absent condition, whether a test supplies it and the reading that established it. |
| R11 | Declared versus implicit configuration | Inspect the build manifest and every file the test framework recognises as its configuration, at the repository root and in the test tree. Enumerate the markers the suite uses and compare against the registered set. | The configuration files found; the markers used; the markers registered; the difference. **A configuration that does not exist is recorded as absent, never assumed either way.** |
| R12 | The implicit default, executed | Write one throwaway test file into a scratch directory **outside the repository's test tree**, holding one async test with no decoration, and run `uv run pytest <scratch file> --rootdir=<repo> -q`. Delete the file, then run the working-tree check. | The reported outcome and the warning text, and therefore what one omitted decoration costs; the clean-tree check. **The suite is not modified to produce this.** |
| R13 | Enforcement outside a local run | Read every workflow definition in the repository. Per workflow: the trigger paths, the commands run, and what each fails on. Then record, against this catalogue's job classes, which exist and which do not — lint, format check, type check, dependency scan, secret scan, lockfile check, build and publish, excluding the test-execution job, which another phase owns. The enumeration exists **only** to establish whether the test-execution job is present and gated; every other job class is `11`'s, and the answer for those is a cross-reference, never a finding here. | The workflow count; the commands; which of lint / typecheck / test / coverage / dependency-scan / secret-scan appear. |
| R14 | Suite-internal references | Enumerate the finding-shaped identifiers and cross-references the suite carries in its own documentation and comments; resolve each against the current tree and against the catalogue's prefix list. | Per identifier: the site, whether it resolves, and **which owner claims it** — the split is in `## 11`. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how is rewritten here, not skipped at execution time. A `Method` of "inspect the tests" is not admissible in this phase: every method must produce its evidence by running something, or by reading a named artefact and recording what it says.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.** R1's counts are never filed as findings; they are the state in which a finding was observed, cited as coverage.

> **On the coverage number.** Coverage measures which statements of a module executed during a run. It is obtained by instrumentation, and the instrumentation is a dependency this project does not declare — supply it ephemerally, and remove what it leaves behind.
>
> A coverage figure **can** establish: which statements of a module never executed across the whole run, and therefore which bodies no assertion in the suite can have been reached through; the size of a gap; and a comparison between two modules under identical instrumentation.
>
> A coverage figure **cannot** establish: that an executing body is asserted on — execution is not assertion; that a test is meaningful; that an unexecuted line is a defect, since it may be a platform branch, a defensive guard, or code nothing reaches, and the last of those is an architecture and craft question rather than this phase's; that a whole-project percentage represents risk, since a high figure is fully compatible with zero coverage of a body's every line; or whether an absent oracle is the code's fault or the environment's.
>
> The number is a description. It is never a control, and it never stands in for the per-subject measurement R3 performs.

> **Platform note (binding).** The declared development platform is Windows. The permission assertions cannot be executed there. **R10 establishes the *form* each oracle takes — an assertion that executes, a reported pass with no assertion body, or a reported skip — and that form is obtainable.** Whether a permission mode is actually in force is `06`'s for the credential file and `07`'s for every other artefact, and is not asserted here. `problems-only` must not convert "unverifiable" into "no finding": the unverifiable half is recorded as a documented skip with its justification, and the verifiable half is the finding. **A reported pass that executed no assertion body is recorded as what it is — a reported pass — and never as a passing test.**

## 6. Audit Dimensions (checks + evidence)

Eight blocks, ordered by risk, **descending**. The letter order **is** the re-entry order (`## 10`): a pass cut short returns the blocks it reached. **No block title or description states an outcome**; each is the question, and the finding is named as a condition to look for. **Two pairs share a method and remain two subjects:** (a) and (c) both consume the coverage and boundary rows — (a) files **the absence of an oracle**, (c) files **the substitution that makes any oracle impossible**; (b) and (g) are behavioural and structural respectively, and either may hold while the other does not.

### (a) Subject Coverage Weighted by the Surfaces Other Phases Claim

> Rank the behaviour each sibling phase names as its subject against what the suite can actually make fail, and file the gaps the ranking surfaces. Weight by the consequence the owning phase assigns its subject, never by module size and never by a whole-project percentage. **The question per body is what assertion could fail on it, not whether any test names it: a body reached indirectly can execute while no test refers to it, so an absent name reference is not evidence that the body is untested and is never filed as one.** For each gap, record which production body has no assertion that can fail on it, and whether any test's name or documentation claims that body.

| Check | Description | Evidence required |
|---|---|---|
| The sibling subject set is enumerated first | Every behaviour each sibling phase names as its subject, with the production body behind it. This list is the denominator, and no subject is re-derived from this file | R1, R3 |
| Each body is scored on the three factors | O, C and E as defined below, per body, **recorded as a table before the ordering is applied** | R3, R7, R9 |
| The order is produced by the comparator alone | Apply the sequence below to the factor table. **No judgement enters between the table and the order** | R3, R7, R9 |
| Each gap names the body and the claiming test | The body with no assertion that can fail on it, and whether any test's name or documentation claims it. **A body no test names is not thereby unexercised** (binding rule 3) | R3 |
| The ranked list is the evidence; its gate is the finding | The finding is that the ordered list is non-empty and **nothing in the repository gates it** | R2, R13 |

- Evidence: R1, R2, R3, R7, R9, R13.

#### Weighting — the comparator, applied in a fixed sequence

Three factors per body, each measured by a named row. No judgement, no percentage, and no factor this phase assigns on its own authority.

| Factor | Values | Obtained by |
|---|---|---|
| **O — oracle strength** | `3` a test can fail on the body · `2` a test asserts a call or a return but not the body · `1` a test exists whose name or documentation claims it · `0` no test references it | R3, R9 |
| **C — consequence class** | `3` an invariant whose violation yields a wrong or unsafe artefact · `2` a failure-path or degradation behaviour · `1` a diagnostic or cosmetic behaviour | read from the **owning phase's own severity vocabulary, in that phase's own file.** Never assigned by this phase |
| **E — reachability** | `2` first observable state reachable without an external boundary · `1` reachable only behind a boundary the suite mocks · `0` not reachable in this environment | R7 |

**Apply the comparator in this sequence, top first:**

> `O` ascending → `C` descending → `E` ascending → **owning phase number ascending** → **subject name ascending**.

`O` ascending because the defect *is* the weakness of the oracle, so the weakest oracle leads. Every key after `O` is total and deterministic, and the last two are pure tiebreakers: **a re-run of the same instrumentation on the same tree produces the same order, with no human input at any step.** The executor records the three factor values per body as a table and then applies the comparator; **a tie the comparator cannot break is a defect in the factor table, not a licence to choose.** Report the ranked list as evidence. **The finding is not the list — the finding is that the list is non-empty and nothing in the repository gates it.**

### (b) Environment and Process-State Isolation

> Determine whether a run's result depends on anything the test did not supply: the process environment, the working directory and any file resolved from it, the clock, the random source, and the process-global registries the suite mutates. **The environment axis is this block's subject and is not optional**: the product declares its own environment inputs, the environment file resolves from the working directory, and the question here is whether the suite isolates that input. Establish the dependence by **varying** those inputs — repeating a run proves nothing, because an unisolated suite also repeats. Then determine whether a mechanism to isolate them exists, and where it lives.

| Check | Description | Evidence required |
|---|---|---|
| The un-supplied-input set is enumerated first | Every input a result could depend on that the test does not supply. This list is the denominator | R1, R5 |
| Each documented product input is varied one at a time | One variable alone, against the same subset unset, with the delta recorded per variable. **A variable is named in the finding and never summarised as "the environment"** | R5 |
| The working directory is varied, with and without a resolved file | The same subset from a second working directory, and with an environment file present. Where a file resolves from the working directory, the dependence is recorded against the input that supplies it | R5 |
| Repetition is not used as the test | R1's repeated runs are the baseline only. **Isolation is established by R5's variation; an identical re-run files nothing** (binding rule 4) | R1, R5 |
| The isolation mechanism is located, or its absence recorded | Whether a mechanism to supply and clear each such input exists, and where it lives. **The mechanism's absence is the finding; the state it fails to isolate is cited to that state's owner** | R5, R6 |

- Evidence: R1, R5, R6, R10.

### (c) Mocking Legitimacy and the Boundaries Never Crossed

> Decide, for every substituted object, whether it is one the process does not own. Three classes disqualify a substitution: **the subject itself; a primitive the runtime uses to schedule the test; a production model whose own validation is part of what the test is about.** Separately count how many external boundaries the suite crosses for real, including the tiers that exist in order to cross them and how many tests they contribute. **A boundary that is never crossed for real is a fact and is filed; that the stand-in misrepresents the boundary is a conclusion requiring the real boundary, is not obtainable here, and is not filed** (binding rule 3).

| Check | Description | Evidence required |
|---|---|---|
| Every substitution site is resolved to a dotted name | Per test, from its own source segment, and assigned one of the four classes | R8, R9 |
| A disqualifying class is a finding, counted per class | The subject, a scheduling primitive, a model whose validation is the point. **With the subject replaced, no oracle on it is possible — that is what the substitution makes true** | R8 |
| Every external boundary role is counted | Per role: the count of unpatched constructions, and whether every substitution site for that symbol is unconditional | R7 |
| A role crossed for real zero times is the finding | The count, and the number of tests the tiers existing to cross it contribute | R7 |
| Fidelity of a stand-in is never filed | No finding rests on a stand-in being wrong about the boundary it replaces. The real crossing is a documented skip; the count is the evidence | R4, R7 |

- Evidence: R4, R7, R8, R9.

### (d) Oracles Whose Subject the Test Environment Never Supplies

> For every behaviour gated on a condition the test environment does not produce — an interactive terminal, a delivered signal, an enforced access-control state — establish **the form the oracle takes on the declared platform**: an assertion that executes, a reported pass with no assertion body, or a reported skip. **The form is the finding. Whether the behaviour is correct under those conditions belongs to the phase that owns the behaviour and is not asserted here, and no claim is made about whether the guards agree with one another — that is unobservable by construction, because the guards are what make it so** (binding rule 3).

| Check | Description | Evidence required |
|---|---|---|
| Every conditional and skip guard is enumerated first | Each guard, the condition it keys on, and its reported outcome. This list is the denominator | R10 |
| The form each oracle takes is recorded | Per guard: assertion body executes / reported pass with no assertion body / reported skip. **A reported pass that executed no assertion is recorded as a reported pass and never as a passing test** | R10 |
| Each absent condition is checked for a supplier | Whether any test supplies the condition, established by having a test read the real state rather than by searching for it. A condition no test supplies is the finding | R10 |
| Agreement between forms is not asserted | No finding compares one guard's form with another's form, and no consistency claim is filed | R10 |
| The correctness of the gated behaviour is cited, not filed | The owning phase files what the guarantee is worth. This block files the shape of the oracle standing in for it, and marks the guarantee `UNVERIFIED` where it cannot be executed here | R10 |

- Evidence: R10.

### (e) Assertion Substance

> For each assertion, establish what the compared value came from: the code under test, a value the test configured into a stand-in, or a read-back of the stand-in's own call record. **The last two are self-confirming.** Separately, establish whether an asserted count or an asserted ordering can be satisfied by a call from outside the subject — which is what happens when the thing being counted is reachable from anywhere in the call graph.

| Check | Description | Evidence required |
|---|---|---|
| Every assertion is classified by the origin of its compared value | Code under test / a value the test configured into a stand-in / a read-back of the stand-in's own call record | R9 |
| Both self-confirming classes are counted | The per-class counts, and every assertion in either class with its test | R9 |
| Each asserted count and ordering is tested against the whole call graph | Whether a call from outside the subject could satisfy it. **A count satisfiable from anywhere is the finding, and is not filed as a wrong count** | R7, R9 |
| A tautology is distinguished from a weak oracle | A test that substitutes its own subject is a tautology and is this block's; a test that asserts a call but not the body is a weak oracle and is (a)'s. **The two are filed once each, in one block** | R8, R9 |

- Evidence: R7, R8, R9.

### (f) Configuration, Measurement and Enforcement Outside a Local Run

> Establish what the suite's behaviour depends on that no file declares: the framework's implicit defaults, the markers the suite uses against the set the framework has registered, and the measurement of its own coverage. Then establish what enforces any of it outside one developer's own machine — which jobs run on a change, and what each fails on. **Report each absence as an absence; never substitute a number the project does not declare, and never prescribe the dependency that would close the gap — declaring one belongs to `11`.**

| Check | Description | Evidence required |
|---|---|---|
| Every configuration file the framework recognises is located | At the repository root and in the test tree, plus the build manifest's own test and coverage sections | R11 |
| The implicit default is executed, not read | One undecorated async test in a scratch file outside the tracked tree, run against the repository root; the outcome and the warning recorded. **The suite is not modified to produce it** | R12 |
| The marker sets are diffed | Markers the suite uses against markers registered, with the difference named per marker | R11 |
| The coverage measurement is established as declared or absent | Whether a coverage tool and a gate are declared anywhere. **The instrument is supplied ephemerally to produce R2; the absence of a declaration is the finding** | R2, R11 |
| Every workflow is read, and each job's failure condition recorded | Trigger paths, the commands, and what each fails on; which of lint / typecheck / test / coverage / dependency-scan / secret-scan appear. Enumerated **only** to establish that the test-execution job exists and is gated; whether any other job class exists is `11`'s (`11`'s block (c), R9 there) and is recorded here as a cross-reference, never filed. | R13 |

- Evidence: R2, R11, R12, R13.

### (g) Shared Setup and Fixture Architecture

> Establish where the suite's shared setup lives, how much of it there is, and what restores the state each piece mutates. **The subject is the arrangement, not the data**: a piece of setup one file needs and another file will also need, and whether restoration is composed with the mechanism the framework already provides or layered over it.

| Check | Description | Evidence required |
|---|---|---|
| The setup is located and measured | Where it lives, how many files carry one, and how much of it there is. **A single shared module is a fact about the arrangement, not a defect in itself** | R6 |
| Each mutated piece of global state is paired with its restoration | Per piece: what it mutates, and what restores it | R6 |
| Restoration is composed or layered | Whether it uses the mechanism the framework already provides or adds a second one over it. A second mechanism is the finding | R6 |
| Overlap with (b) never becomes one finding | (b) is behavioural — whether a result actually moved; (g) is structural — what the arrangement is. **One may hold while the other does not, and each is filed once** | R5, R6 |

- Evidence: R5, R6.

### (h) Documentation and Identifiers Carried Inside the Suite

> Enumerate the finding-shaped identifiers and cross-references the suite carries in its own documentation and comments, and resolve each against the current tree. Ownership follows whose claim it is: a stale reference inside a test's own documentation is this phase's; a reference in production code is that code's own claim and belongs to the phase owning the code; a reference to the audit itself belongs to the validator. **Do not adopt or reuse any identifier the suite already carries** (`## 11`).

| Check | Description | Evidence required |
|---|---|---|
| Every identifier and cross-reference is enumerated | Per site: the identifier, its form, and whether it resolves against the current tree and against the catalogue's prefix list | R14 |
| Each is assigned to its owner before anything is filed | Test documentation → this phase · production code → the phase owning that code · the audit itself → `99`. **The verdict is recorded per site, and a claim another owner has already made is never re-filed here** | R14 |
| A form the catalogue does not use is recorded as such | A site carrying a form no phase prefix uses, and a site carrying a form two live prefixes share | R14 |
| No identifier in the tree is adopted | This phase mints a new number and reuses, extends and renumbers none (`## 11`) | R14 |

- Evidence: R14.

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.** The first five are the catalogue's general ownership rules as they bear on this phase.

- **R-A — a file's permission mode, creation mode, atomicity and cleanup** → `07`, whatever the file contains; **the credential file's content and redaction → `06`; the credential file's permission mode and the platform reality of that mode → `06`.** **The form a test's guard takes on the declared platform** → **this phase.** The guard style is a test-construction property; the guarantee the guard protects belongs to the artefact's owner, is not re-filed here, and is cited as `UNVERIFIED` where it cannot be executed.
- **R-B — the argument vector** → `05`; **the file on disk** → `07`; **whether a secret appears in either** → `06`. This phase cites all three and files only what a test asserts about them.
- **R-C — a declared setting field** → `02`; **a dependency declaration in the build manifest** → `11`; **a documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09`; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`. **What a declared setting means and where its environment file is resolved from** → `02`; **whether the suite's result depends on that input** → **this phase.** The resolution semantics are a configuration property, the hermeticity of the tests against them is a test property: one line, filed once. A dependency this phase's tooling would need is `11`'s to declare — this phase reports the absence and **prescribes nothing**.
- **R-D — structural arrangement** (import graph, layer direction, cycles, facades, bootstrap order) → `01`; **file-local craft** → `09`. Test: *does the candidate survive moving the file?* Yes → `01`. Applied to a production-side counterpart of an observation made here, the verdict is recorded and the counterpart is cited, not filed.
- **R-E — a document** is owned by the phase that owns the code it describes; a document describing the audit pipeline itself → `99`. Applied here, the split is stated in `## 11`.
- **The tests themselves** → **this phase.** `10` audits the tests; `99` audits the findings, including whether a finding from this phase survives validation. **Neither files the other's defect**, and the boundary is stated so the validator's cross-finding conflict detection and this phase's evidence-quality critique cannot converge on one defect.
- **A subject another phase owns, and the consequence of that subject being wrong** → **that phase.** This phase files the *absence of an oracle* and cites the measurement; the owning phase files *what the absence costs*, using this phase's evidence. A finding that the suite cannot fail on a body is not re-filed there as a defect in the body, and "no test covers it" is never re-filed there either.
- **The absence of a real-terminal oracle** → **this phase**, by delegation. The predicate disagreement that absence leaves without a witness → `08`; this phase cites the mechanism counts and files nothing from them. Executed here: the form the oracle takes. Not executed here: whether the arbitration is correct.
- **Whether a signal is delivered on the declared platform, and what the handler does with it** → `04`. **Whether any test supplies that delivery, and what the test's platform branch executes** → **this phase.**
- **Shutdown-state derivation from a signal** → `04`; **rendering and sink of what the process emits** → `08`; **correlation-identifier generation, binding and clearing** → `01`. This phase files only whether a test can fail on any of them.
- **A pipeline job that is not test execution** → `11`; so are the build manifest, the dependency declarations, repository hygiene, and **the ignoring of the artefact the audit's own tooling leaves behind** — cited, never filed. This phase audits *whether the suite runs and what enforces it*.
- **A declared setting's typing, bound and reachability** → `02`; **the option that reaches it** → `08`. Neither is restated as a check here.
- **Building an integration harness** → not an audit subject. **The absence of an integration tier is reported once, as a gap, and is not filed a second time against production code.**
- **Licence posture, terms acknowledgement, notice mechanism; a general performance, rate or capacity claim** → not audit subjects, inadmissible under `problems-only` and expressly rejected. **Do not file.**

## 8. Edge Cases

- A test that substitutes the very thing it names.
- A test that passes and would not catch a regression.
- A test whose asserted count can be satisfied from anywhere in the call graph.
- A result that changes with the working directory, or with a file that resolves from it.
- A result that changes when one documented environment variable is set.
- A guard that reports success while executing no assertion body.
- A restoration mechanism layered over one the framework already provides.
- A test whose documentation names a subject the code no longer contains.
- An identifier shared with another phase's prefix, or a form no phase uses.
- A test that, to pass, required the code to be wrong.
- Randomness and ordering dependence that has not yet bitten, filed as absence rather than as clean.
- An absent coverage gate where the number looks acceptable.
- **A body no test names that nevertheless executes** — absence of a name reference is not untested (binding rule 3).
- **Two runs that agree because the environment was never varied** (binding rule 4).
- An artifact the audit's own tooling leaves behind, untracked and un-ignored.

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are **not redefined here**.

| Severity | Conditions |
|---|---|
| CRITICAL | A subject a sibling phase names as its highest-consequence behaviour has no test that can fail on it, and the consequence is an artefact that is wrong or unsafe. Or a documented input the product itself declares changes a test's outcome. |
| HIGH | An oracle reports success while executing no assertion. A substituted object is the subject, a scheduling primitive, or a model whose validation is the point. A body is claimed by a test and never executed. Nothing in the repository measures or enforces the suite outside one machine. |
| MEDIUM | An assertion's compared value came from something the test configured. Shared setup is one file's private property. A framework default the suite depends on is declared nowhere. An untracked artefact is produced by the audit's own tooling. |
| LOW | A test's own documentation names a subject that no longer resolves. A test is coupled to an internal detail and would break on a behaviour-preserving refactor. |

**No percentage threshold appears in this table**, because none is declared anywhere in the project and any value written here would be arbitrary.

**Type guidance.** `SPEC-DEVIATION` for a test or configuration that contradicts the project's own declared rule. `DOC-UPDATE` for a reference in a test's own documentation that no longer resolves. `BEST-PRACTICE` for a defensible arrangement with a demonstrated gap. `RUNTIME-ERROR` for anything observed failing at runtime.

**These conditions are a classification vocabulary, not a verdict.** Every severity is composed by this phase from its own run. **No severity carried by any preceding analysis, and no adjective attached to a subject in any preceding document, is inherited** (binding rule 1). A finding whose consequence was not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity. **A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded, never as a clean bill of health.** A subject with no observed consequence does not get a condition here.

## 10. Recommended Sequence

1. Discovery (`## 4`).
2. **R1 and R2 first** — the baseline, the collect-only counts and the coverage instrument, written before the first subject is checked, so a later silence is a reported skip and not an omission.
3. **R5 and R10** — the two cheapest rows and the two most consequential: the environment axis and the form each platform oracle takes.
4. R7 and R8 — real boundary crossings, then the replaced-object triage built on them.
5. R3 and R9 — per-body coverage and the origin of every compared value.
6. R4 — the substitution counts for the boundaries, with the real crossing emitted as a documented skip.
7. R6 — per-test independence and the restoration probes.
8. R11 to R14 — declared versus implicit configuration, the implicit default executed, enforcement outside a local run, and the suite's own references.
9. The ranking under (a), then blocks (b) through (h) in the order they are written in `## 6`.
10. Cross-cutting (`## 7`) and edge cases (`## 8`), re-reading `## 7` before writing each finding.
11. Consolidate findings.

**Second-pass order.** If this phase is re-run after a thin result, do **not** start again at step 1. Re-enter at the first item below for which no evidence was recorded and continue downward: **R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → R12 → R13 → R14 → (a) → (b) → (c) → (d) → (e) → (f) → (g) → (h)**. A block with partial evidence is resumed; a block with complete evidence is skipped. `No problems found in this phase.` is admissible **only once R1, R5, R10 and R13 are all recorded** — those four rows are the ways this phase manufactures a clean bill of health, and the first line of the report must close that door.

## 11. Finding Prefix

Use `TST-` for all findings in this phase. `TST-` is unique among the phase prefixes, shares no first two characters with any of them (`EN CF NE CO PR SE AR OU QL TS DE VA` are all distinct), is obtainable from no other prefix by a single plausible edit, and does not encode the phase number, so renumbering never invalidates a published finding ID.

**The suite already contains identifiers of this form.** Test documentation and comments carry them, and among them forms that match a live phase prefix. **This phase adopts no identifier already present in the tree, and reuses, extends and renumbers none.** The validator owns cross-finding merge detection, will meet those identifiers, and cannot resolve which catalogue a two-character collision belongs to. **A number written beside a subject is a pre-answered outcome by another name** (binding rule 1); the same discipline applies to an identifier minted before the evidence exists. An identifier the suite carries is inventory for block (h), never one of this phase's own.

**The split, by whose claim it is:** a stale reference in a **test's own documentation** is **this phase's**; a reference in **production code** is that code's own claim and belongs to the phase owning that code; a reference to the **audit itself** is the validator's. Record the verdict per site, and never re-file a claim another owner has already made.

## 12. Reporting

- Write findings to: `.ai/audit/10-test-coverage/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.` — and only once R1, R5, R10 and R13 are all recorded.
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, **naming the R-row that produced it**, and (2) the **exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - **No finding is closed on the grounds that a run was green.** A green run is the state in which a finding was observed, never its evidence.
  - **A coverage figure is never filed as a control, never as a whole-project percentage representing risk, and never as a threshold.** Where the per-body instrument was unavailable, the finding is filed as the weaker inference with the reason recorded.
  - **No row, note or finding exists for a subject that was checked and found correct**, and none is manufactured to fill an in-scope bullet that names one (binding rule 5).
  - **A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded**, never as a clean bill of health.
  - **Every documented skip is written in the fixed wording** — what was attempted, why the evidence is unobtainable, what remains verifiable, and which phase owns the unverifiable half. `n/a` is not a substitute.
  - **No identifier already present in the tree is adopted, extended or renumbered**; no finding is filed against a sibling phase's claim, and no finding from any preceding analysis is restated.
  - **The report contains no severity, no outcome and no quoted text inherited from any preceding analysis or from the decision document**, including the in-scope claims quoted only to place them in `## 2`.
