---
name: 09-code-quality
status: draft
validated: no
executor: auditor
problems-only: true
---

# 09 — Code Quality

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — a green result from the configured checks is this phase's
> largest quality risk, and block (c) is where it bites.** **The clean output is
> the evidence of a gap in what the checks cover, not a pass.** A finding may not
> be closed on the grounds that a tool reported nothing, and R1's key-by-key
> configuration record and per-dependency marker table are **binding obligations,
> not a preamble note.**
>
> **Binding rule 2 — the two largest subjects are questions, not results.** The
> error taxonomy and the documentation are stated below as subjects with a method
> attached. **This file does not say what either of them currently does** — only
> the question each answers and the rows that answer it: (a) with R2 and R3, (b)
> with R4, R5 and R6. An executor who finds an outcome written beside either
> subject has misread the file.
>
> **Binding rule 3 — the documentation subject is four comparisons, never a
> sweep.** Each of the four document classes has **its own denominator and its own
> method**, and a general statement about documentation's accuracy is evidence for
> none of them. The block is not "are the documents stale"; it is "does this claim
> match the code it names", asked four times.
>
> **Binding rule 4 — severities are composed by this phase, never inherited.** No
> severity carried by any preceding analysis, and no adjective attached to a
> subject in any preceding document, is citable. **Record the evidence first, then
> assign the severity.**
>
> **Binding rule 5 — a subject already checked and found correct is absent, not
> annotated: no check row, no verification row, no note, no finding.** No check is
> manufactured to fill an in-scope bullet that names one. A check invented to
> cover such a subject is itself a defect of this phase.
>
> **Binding rule 6 — the phases this one is measured against.** Run this phase
> **after `01`, `02` and `08`**, or expect the seams in `## 7` to be unverifiable.
> Where an adjacent phase has not run, the seam is **cited as stated in `## 7`,
> not independently re-derived** — re-deriving a neighbour's subject from this file
> is how the catalogue already came to claim the same subject twice.

## 1. Goal

Conformance to the project's own written engineering rules, the internal consistency of the error model, and whether the documentation still describes the code.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| The error model | One declared condition, read end to end: code → exception → the label the caller reads → the text the user reads → the context the log records. | One condition ending with two identifiers or with none; a rung nothing reaches; the same ladder written more than once and already diverged. |
| Documentation-to-code drift | Four document classes checked against the code each names: the navigation documents, the generated structure maps, the project's own maintenance rules, in-code documentation. | A claim that contradicts the code it names; a claim that cannot be checked at all; two copies of one document with no rule choosing between them. |
| The configured checker's reach | What the type checker is declared to cover, against what the code hands it. | A project typing rule the configured profile cannot enforce; an untyped third-party boundary that makes the largest integration invisible. |
| Fixed values as enumerations | A value the project already declares as an enumeration member, re-expressed as a raw string, a collection literal, or a second identifier. | The same concept with three representations and nothing that checks they agree. |
| Declared types at boundaries | The type a boundary value is declared to have, per source that can supply it. | An annotation that promises a type a reachable source can violate, in a way the checker cannot see. |
| Responsibilities per file | Line count, top-level definition count, and the responsibility set of the tail. | A file whose definitions belong to several unrelated concerns; the cost stated is navigation, not a defect. |
| File-local consistency | One file's own export lists and its own import form. | A name listed twice in one list; a convention applied to most files and not the rest. |

**In scope:**
- Strict typing; constants as enumerations rather than ad-hoc literals/dicts/lists; logging discipline and the absence of ad-hoc printing; separation of concerns; module size and single responsibility; validation at boundaries; naming and language.
- The error taxonomy end to end: code → exception → status label → user message → log context → exit code, including a single exception carrying two labels under different conditions, and the retained legacy status-mapping shim.
- **Documentation-to-code drift:** module/class/function docstrings, the architecture document (which omits one service module and misdescribes three others, and does not mention the re-export facade), the tool documents (which still describe a removed progress flow), and the stale structure maps.
- File-local duplication: a symbol listed twice in one export list.
- Platform-sensitive string handling that is a *code* concern rather than a filesystem concern.

*Read the in-scope bullets as the decision wrote them and not as a checklist of dimensions. The bullet naming logging discipline and the absence of ad-hoc printing, and the half of the separation-of-concerns bullet that is not about one file's own contents, **name subjects that produce no check in this file** — the first because the search is clean, the second because it is `01`'s. Their presence here is not an instruction, and **no check is manufactured to fill a bullet that names one.** The parenthesised counts inside the third bullet are the decision's own scope, not this phase's evidence: every one of them is re-derived by R4–R6, and a claim re-derived as matching is filed as nothing.*

**Out of scope:**
- The structural arrangement of modules and the direction of imports → `01` (test: does the finding survive moving the file? if yes → `01`). Migration discipline → deleted, no migrations exist. The audit's own severity taxonomy → `99`.

## 3. Prerequisites

- **The project's own verification commands, quoted from `.ai/context/commands.md`:** `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>`. `mypy` (strict) is the configured checker; **a second checker present in the dev dependency group is not it and must not be substituted.**
- **The evidence regime: entirely static.** File reads, searches, line and symbol counts, and one in-process probe run through the project's own runner, written **outside the workspace** so no project file is created or modified. **No container, no database, no service is started. No code is modified — audit only.**
- **Scope discipline.** The type-checker configuration declares no file list, so the scope is whatever the caller passes: **the source tree and the test tree are separate invocations**, and a pass that checks one has not checked the other. **Every search over the tree excludes every worktree directory**, whose stale copy of an earlier phase set would otherwise be searched by accident.
- **The production-code-is-king rule** → `10`. This phase cites it and does not act on it.

## 4. Discovery

Map the contract before checking anything. **Use roles, not names.** No concrete file, module or class name appears in this section. **A subject that maps to nothing is a gap, and a gap is reported.**

1. **Condition map** — every condition the error hierarchy declares, its branches, and the handler ladder each command entry point declares. The denominator for (a).
2. **Rung map** — per condition, the declared code, the derived label, the user-facing text, and the log context, with each rung's call sites counted in the source tree and the test tree separately.
3. **Document map** — every document directory and its file list, grouped into the four classes: navigation documents, generated structure maps, the project's own maintenance rules, in-code documentation. Also every pair of documents describing the same code, and every document describing no code here. The denominator for (b).
4. **Reach map** — the type checker's configured key set, the per-dependency typing-marker verdict, and every module and call site standing behind each boundary that lacks one. The denominator for (c).
5. **Enumeration map** — every enumeration the project declares with its members, and every module-level constant binding whose value is a collection literal, each classified as a project value or an external protocol's vocabulary. The denominator for (d).
6. **Boundary map** — every value crossing into a declared signature, with the source that supplies it, and each source's reachability class. The denominator for (e).
7. **File map** — per file: line count, top-level definition count, longest single definition, the labelled responsibility set, the export lists it declares, and its import form. The denominator for (f) and (g).
8. **Evidence map** — per row in `## 5`, which method produces it, which of the two documented skips covers it, and which of the two trees is searched. **A row with no method mapped is not executed and is reported as not executed.**

*Role vocabulary: the error hierarchy's base class and each derived condition · the site that derives a label from a condition · the site that exposes user-facing text · the site that builds log context · each command entry point's handler ladder · the retained legacy mapping shim · the architecture document's tree · the tool documents' per-file sections · the generated structure maps · the project's own maintenance rules · each module, class and function docstring · the type checker's configuration block · each installed dependency package directory · each enumeration class and its members · each module-level collection-literal binding · each command-line argument, environment read, environment-file read, list-file read and direct programmatic argument · each file's export list · each file's import form.*

## 5. Runtime Verification (mandatory)

> **Baseline, re-measured, and to be re-measured at execution** (a measurement, never evidence for a finding): the type checker is configured over no file list, so the two invocations cover **47 files** — **29 in the source tree, 18 in the test tree**. The suite reports **415 passing and 1 skipped**; the count is cited as coverage and nothing else. The verdict of the four configured commands is **not written here** — R1 records it, and **a green result is the state in which a finding was observed** (preamble rule 1).

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | The four configured checks, the checker's declared reach, and the skip register | Run the four commands from `## 3. Prerequisites` over the source tree **and** the test tree as **two separate invocations**, and record each exit code, each output verbatim, and the file count each reports. Then read the type checker's configured key set and record, key by key, which of the strict profile's checks for the fully-unknown type are present and which are absent, and whether the missing-imports policy is on. For **every** runtime dependency the project imports, assert the presence or absence of a typing marker in its installed package directory and record the result per package. Write both skip texts and the platform note before the first subject is checked. | The four outputs verbatim with their file counts; the key-by-key configuration record including the absent keys; the per-dependency typing-marker table; the two skip texts; the platform note. **Admissibility note: a green result from any of the four commands is recorded as the state in which a finding was observed, never filed as a finding and never as a pass.** |
| R2 | The error taxonomy, rung by rung | **In process.** A throwaway probe outside the workspace, run through the project's own runner. Construct one instance of every condition the hierarchy declares — **including the base class and both branches of every condition that has two outcomes** — and for each print four things side by side: the declared code, the derived label, the user-facing text, the context it hands the log layer. Then, for each of those four names, count its call sites across the source tree and the test tree **separately**. Then read the handler ladder each command entry point declares, list the conditions each names, and diff both lists against what the hierarchy can raise. Then search the source tree for every site that raises a condition **no** ladder names. | The probe table verbatim; the per-name call-site counts split source/test; both ladders as lists; the diff; the list of raised conditions no ladder names. |
| R3 | Which surface carries which identifier, and on which command | **In process, then read.** For each vocabulary term R2 produced, record which handler enumerates it, which command's declared failure set carries it, and which of the process's declared output surfaces it reaches. Record every term that surfaces on one command and not the other, explicitly. **The reachability of each divergence is established here, not assumed** — a divergence whose label appears only on a path the single command does not take is recorded as such. | The per-term record: handler, command, surface; every command asymmetry; every divergence whose reachability the record establishes or fails to establish. |
| R4 | The navigation documents | **Three passes, one per claim type, each with its own denominator.** (a) *Path claims:* list every path the architecture document's tree names; diff the list against the source tree **in both directions** — a path named but absent, and a file present but unnamed. (b) *Content claims:* for every row of that tree, read the named file's own declared contents and compare against the document's one-line description. (c) *Tool-document claims:* for every file the tool documents list, count its lines and list its declared public surface; count the import sites of the surface the document says everything is exported through; then test that universal claim by listing every export list in the source tree and testing membership. | The bidirectional path diff; the per-row content comparison; the per-file line counts; the import-site count; the membership test with its counterexamples. **A count that contradicts a stated count is a finding; a count stated nowhere is a measurement, not a finding.** |
| R5 | The machine-read documents | **Two passes.** (a) *Structure maps:* count the entries recorded against the count of files in the tree; for every recorded path, assert it **resolves from a clean checkout** — a path that resolves only from a directory the ignore file excludes does not resolve; for every symbol the maps name, grep the source tree **both** directions, recording what is named and absent and what exists and is unnamed. (b) *The project's own maintenance rules:* for every path the rules name, assert the path exists; for every rule the rules state, read the source and record whether the rule holds. | The entry count against the file count; the per-path resolvability verdict; the bidirectional symbol diff; the per-rule verdict with the code that was read. **Where a rule names a layout and a code file owns the same subject, the document claim is the finding and the behaviour is cited to its owning phase, not filed here.** |
| R6 | In-code documentation, and the documents no ownership rule reaches | (a) For every docstring, module comment or function comment that names an object, a class, a global or a fixed value, grep the source tree for that object; record present, absent, and **renamed-but-equivalent** separately. For every docstring describing a *contract* — a default, a guarantee, a constraint — read the code the contract is about and record whether the code honours it. (b) *Ownerless documents:* list every document directory's contents; for each pair of documents describing the same code, run a no-index diff between them and record the size of the difference; for each document describing no code in this repository, record that fact. | The per-docstring name-match table; the per-contract verdict; the diff statistic per document pair; the list of documents describing no code here. |
| R7 | The typing surface the configured checker cannot reach | Against R1's baseline and its per-dependency table. Enumerate every annotation in the source tree that admits the fully-unknown type — search for the explicit annotation form and, separately, for every suppression comment and every cast to that type; record file, line and count. For every package R1 found lacking a typing marker, list every source file that imports it and, per file, the count of call sites into it. Then per boundary record what a signature change inside that package would cost, and **what, if anything, the checker stands between the caller and it**. | The annotation inventory; the per-package import-and-call-site table; the per-boundary stand-between record. **A boundary with nothing between it and the caller is a finding about the configured reach, not about the code.** |
| R8 | One fixed value, several spellings | Search the source tree for module-level bindings whose name is entirely upper case and whose value is a dict or a list literal; for each, record the binding and decide — by reading what the values are — whether they are the project's own fixed values or an external protocol's. Then, for every enumeration member the project declares, search the source tree for that member's raw value used as a bare literal and record each site. Where a value is converted back into the enumeration, trace the conversion's only caller, record the domain of values that caller can supply, and state whether each branch of the conversion is reachable from that domain. | The constant-binding inventory with a per-binding verdict of project-value or external-vocabulary; the per-member raw-literal site list; the per-conversion reachability record. |
| R9 | The type a boundary value is declared to have, per source | For every value that crosses into a declared signature — a command-line argument, a value read from the process environment, a value read from an environment file, a value read from a list file, and a value a programmatic caller passes directly — record three things per source: the declared type at the receiving point, the type that source can actually produce, and **the source's reachability class**. A source that is always text — an environment file, the process environment — can only supply text, so a divergence there is a coercion or a parse; a source reachable only from a programmatic caller can supply any value its type admits, so a divergence there is an unannounced contract. | The per-boundary table: declared type, producible type, reachability class, and the divergence if any. **A row with no recorded reachability class is not admissible.** |
| R10 | Responsibilities per file | For every file in the source tree, record its line count and its count of top-level definitions — functions, classes, module-level constants — and the length of its longest single definition. Compute definitions per hundred lines. For each file in the upper tail, read every top-level definition and label it with one word; record the set of distinct labels and its size. | The per-file table with all three columns; the per-file labelled definition inventory; the distinct-label set per file in the tail. **The definitions-per-hundred-lines column is the discriminator between several responsibilities and one long one; the line count alone decides neither.** |
| R11 | One file's own internal consistency | For every declared export list in the source tree, parse it and record entries, unique entries, and every name appearing more than once with its two positions. For every file, record whether its import statements use the absolute or the relative form, and tally the tree. | The per-list record; the per-file import form; the tree tally. **A repeated name whose repetition is inert at runtime is reported as inert.** |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how is rewritten here, not skipped at execution time. A `Method` of "inspect the implementation" is not admissible in this phase: every method must produce its evidence by running something, or by reading a named artefact and recording what it says.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.** R1's four outputs and the suite count are never filed as findings; they are the state in which a finding was observed, cited as coverage.

> **R-N — the type checker cannot be made to fail by this code, only by its configuration.** Every annotation naming the fully-unknown type passes under the configured profile, and every untyped third-party boundary passes under the configured missing-imports policy. **This block's finding is therefore evidenced by reading the configured key set and by asserting a typing marker per installed package — not by making the checker emit a diagnostic.** No runtime observation of a third-party signature error is obtainable here and none may be claimed. **The clean output is the finding's evidence, not its refutation, and a clean output is never a reason to skip R7.**
>
> **R-S — one path guard's command-line trigger is not reachable as the product is wired.** One caller normalises its input before the guard inspects it, so a value supplied from the command line cannot arrive in a form the guard examines; the guard's own public entry point can still be called directly by any Python caller. **That reachability belongs to `02` and is cited, not filed.** Consequence for this report: the finding here is filed on the **executed** divergence between the declared code and the label, and on the **executed** fact that no handler names that condition; anything whose consequence depends on the command-line trigger is filed with the structural fact and an explicit `UNVERIFIED` marker. **Do not attempt to trigger it from the command line, and do not report a severity that depends on a trigger nobody has produced.**

**Platform note (binding).** The declared platform is Windows. This phase is **entirely static** and requires no terminal, no network, no subprocess and no elevated permission. **No finding in this phase may state a runtime consequence that requires a real terminal.** The one subject that would — whether a progress surface is active — is not this phase's; where a document rule about progress placement is checked, it is checked **by reading the two files that own the display and the batch account**, which is static and needs no terminal.

**The two largest subjects both have a home.** Taxonomy → block (a), evidenced by R2 and R3. Documentation → block (b), evidenced by R4, R5 and R6, decomposed into four independently executable passes with four distinct denominators. **No row in this table is a "documents are stale" sweep**, and no row produces a general statement about documentation; each produces a comparison between one document's claim and the code the claim names.

## 6. Audit Dimensions (checks + evidence)

The seven blocks are ordered by risk, **descending**. The letter order **is** the re-entry order (`## 10`): a pass cut short returns the blocks it reached. **Executability does not reorder risk** — blocks (f) and (g) are the most mechanical in the phase and are still last, because a truncated pass must return the high-risk blocks first. **No block title or description states an outcome**; each is the question, and the finding is named as a condition to look for.

### (a) The Error Taxonomy, End to End

> The failure the product declares travels through several rungs: a code, the exception that carries it, the label the caller reads, the text the user reads, the context the log records. Read one condition end to end through all of them, and read both branches wherever a condition can produce two outcomes. Then find every rung implemented more than once, and every failure the hierarchy can raise that no handler in the product names. A condition that ends with two identifiers, or with a rung nothing reaches, is the finding. *What the caller receives on the terminal and the status the process returns are `08`'s; this block files what those are built from.*

| Check | Description | Evidence required |
|---|---|---|
| The condition set is enumerated first | Every condition the hierarchy declares, with both branches where a condition has two outcomes, listed before any is judged. This list is the denominator | R2 |
| One condition is read end to end | Declared code, derived label, user-facing text, and log context side by side, per condition. A condition ending in two identifiers is the finding | R2 |
| Every rung is counted in source and test separately | Per rung name, its call-site count in each tree as two denominators. A rung nothing reaches is the finding | R2 |
| Each handler ladder is diffed against the hierarchy | The conditions each entry point's ladder names, as a list, diffed against what the hierarchy can raise. A raised condition no ladder names is the finding | R2 |
| A ladder implemented more than once is recorded as a second implementation | Every rung with more than one implementation site, and whether the copies already differ | R2 |
| Per term, the handler, the command and the surface are recorded | Which handler enumerates each term, which command's failure set carries it, which output surface it reaches. A term surfacing on one command and not the other is the finding; a divergence whose label appears only on a path that command does not take is recorded as such. **Reachability is established here, not assumed** | R3 |

- Evidence: R1, R2, R3.

### (b) Documents Checked Against the Code They Name

> Four document classes, checked against the code each names, and **never as a sweep**. The navigation documents: every path, module list, line count and universal claim they make, diffed against the tree. The generated structure maps: every recorded path asserted resolvable, and every recorded symbol matched in both directions. The project's own maintenance rules: every path they name, and whether each rule they state holds. In-code documentation: every object a docstring names, matched against the tree. A claim that does not match the code it names is the finding; a claim that cannot be checked at all is recorded as such and is not passed. *Claims about a setting's field, type, default, range, variable name or precedence are `02`'s; claims about the command-line contract are `08`'s.*

| Check | Description | Evidence required |
|---|---|---|
| Navigation documents, path claims | Every path the architecture document's tree names, diffed against the source tree in both directions: named but absent, and present but unnamed. **Denominator: the document's own path list** | R4 |
| Navigation documents, content claims | For every row of that tree, the named file's own declared contents read and compared with the document's one-line description. **Denominator: the document's row list** | R4 |
| Navigation documents, the universal claim | For every file the tool documents list: its line count, its declared public surface, the import-site count of the surface the document says everything is exported through, and the membership test against every export list in the tree. **Denominator: the document's file list** | R4 |
| Generated structure maps | Entries recorded against the count of files in the tree; every recorded path asserted resolvable from a clean checkout; every recorded symbol matched in both directions. **Denominator: the maps' own entry list** | R5 |
| The project's own maintenance rules | Every path they name asserted to exist; every rule they state read against the source, with a per-rule verdict. Where a rule names a layout and a code file owns the same subject, the document claim is the finding and the behaviour is cited to its owning phase. **Denominator: the rules' own statement list** | R5 |
| In-code documentation | Every docstring or comment naming an object, class, global or fixed value, matched against the tree — present, absent and renamed-but-equivalent recorded separately; every docstring describing a contract read against the code the contract is about. **Denominator: the docstrings themselves** | R6 |
| Ownerless documents | Each document directory listed; for each pair describing the same code, a no-index diff with the size of the difference; for each document describing no code in this repository, that fact recorded. **Denominator: the document set itself** | R6 |

- Evidence: R1, R4, R5, R6.

*Preamble rule 3 is the rule this block is enforced under: **four denominators, four methods, no general statement.** A claim that cannot be checked is recorded as such and is not passed as a match.*

### (c) What the Type Checker Is Configured to See

> **The checker's clean result is this block's evidence, not its refutation.** Read the configured key set and record, key by key, which of the strict profile's checks for the fully-unknown type are present and which are absent. For every third-party package the project imports, record whether it ships a typing marker, and count the modules and call sites behind each boundary that lacks one. Then ask, per such boundary, what a signature change or a misspelling inside it would cost, and what the checker stands between the caller and it. *What a third-party library does internally is out of scope by design — state it, do not guess; what the configured reach does to the surface the checker does see is this block's.*

| Check | Description | Evidence required |
|---|---|---|
| The configured key set is read key by key | Which of the strict profile's checks for the fully-unknown type are present, which are absent, and whether the missing-imports policy is on. A key the project's own typing rule needs and the profile does not carry is the finding | R1 |
| A typing marker is asserted per installed package | For every runtime dependency the project imports, the presence or absence of a typing marker in its installed package directory, recorded per package. **A green result is recorded, never filed** (preamble rule 1) | R1 |
| The fully-unknown type is inventoried in the tree | Every annotation admitting it — the explicit annotation form, every suppression comment, every cast to it — with file, line and count | R7 |
| Every unmarked boundary is measured | Per package lacking a marker: every source file importing it, and per file the count of call sites into it | R7 |
| Per boundary, what the checker stands between is recorded | What a signature change inside that package would cost, and what, if anything, the checker stands between the caller and it. A boundary with nothing between it and the caller is the finding — **about the configured reach, not about the code** | R7 |
| No row here is evidenced from a green test run | The suite is cited as a count only. **R-N governs this block and a clean output is never a reason to skip it** | R1 |

- Evidence: R1, R7.

### (d) One Fixed Value, Several Spellings

> A fixed value the project already declares as an enumeration member, re-expressed as a raw string, a collection literal, or a second identifier. Enumerate the module-level constant bindings in the tree and decide, per binding, whether its values are the project's own fixed values or an external protocol's. Then search for each enumeration member's raw value used as a bare literal. Where a value is converted back into the enumeration, record the domain its only caller can supply and whether every branch of that conversion is reachable. A value with a member and a spelling is the finding. *The validity of a declared setting is `02`'s; what the value means to the reader is `08`'s.*

| Check | Description | Evidence required |
|---|---|---|
| Constant bindings are inventoried and classified | Every module-level binding whose name is entirely upper case and whose value is a collection literal; per binding, a verdict of project-value or external-vocabulary, read from what the values are | R8 |
| Every enumeration member is searched for as a bare literal | For every member the project declares, every site where that member's raw value appears as a literal. A value carrying both a member and a spelling is the finding | R8 |
| A conversion back into an enumeration is traced to its only caller | Per conversion site: the domain of values that caller can supply, and whether each branch of the conversion is reachable from that domain. An unreachable branch is recorded as such | R8 |
| An external protocol's vocabulary is not read as the project's own | The per-binding verdict is the evidence. **A value that belongs to an external protocol is not a finding against the enumeration rule and is not filed as one** | R8 |

- Evidence: R1, R8.

### (e) The Type a Boundary Value Is Declared To Have

> For every value that crosses into a declared signature, record the type the receiving point declares and the type each source of that value can actually produce. **Record the reachability class of every source as part of the evidence, never as an assumption:** a source that is always text can only supply text, so a divergence there is a coercion or a parse, while a source reachable only from a programmatic caller can supply anything its type admits, so a divergence there is an unannounced contract. *Whether an input escapes the validation-failure handler at runtime is `02`'s; the annotation and the reachability class are this block's.*

| Check | Description | Evidence required |
|---|---|---|
| Every boundary value is listed first | Command-line argument, process environment, environment file, list file, and a programmatic caller's direct argument. This set is the denominator | R9 |
| Declared type against producible type, per source | Per source: the type the receiving point declares, and the type that source can actually produce | R9 |
| The reachability class is recorded as evidence, not assumed | **A source that is always text — an environment file, the process environment — can only supply text, so a divergence there is a coercion or a parse. A source reachable only from a programmatic caller can supply any value its type admits, so a divergence there is an unannounced contract.** **A row with no recorded class is not admissible** | R9 |
| The escape is cited, not filed | Whether an input reaches past its validation-failure handler is `02`'s; the annotation and the class are this block's. The verdict per row is recorded so the cite is a record and not a guess | R9 |
| No severity rests on a trigger nobody produced | A consequence that depends on the command-line trigger is filed with the structural fact and an explicit `UNVERIFIED` marker, under R-S | R2, R9 |

- Evidence: R1, R9.

### (f) How Many Responsibilities One File Carries

> Measure every file in the source tree on three axes, not one: its line count, its count of top-level definitions, and the length of its longest single definition — so one long unit is never mistaken for several responsibilities. For each file in the tail, label every top-level definition with one word and read the set of distinct labels. A file whose labels name several unrelated concerns is the finding. **The cost is navigational, and the consequence stated is the navigation — not a defect in behaviour, and not a claim that the file is wrong.** *Which direction an import points is `01`'s.*

| Check | Description | Evidence required |
|---|---|---|
| Every file is measured on three axes | Line count, top-level definition count, and longest single definition, with definitions per hundred lines computed. **That last column is the discriminator between several responsibilities and one long one; the line count alone decides neither** | R10 |
| Every top-level definition in the tail is labelled | One word per definition; the set of distinct labels and its size recorded per file | R10 |
| The consequence filed is navigation | A file whose labels name several unrelated concerns is the finding, filed as a cost of navigation. **It is not filed as a behaviour defect, and a file is never declared wrong for being large** | R10 |
| The tail is defined before it is read | The upper tail is fixed by the per-file table, so no file is selected because its definition count was already known | R10 |

- Evidence: R1, R10.

### (g) One File's Own Internal Consistency

> Two things that never leave one file. Its declared export lists: entries, unique entries, and any name that appears twice. Its import statements: the form each file uses, tallied across the tree, with the per-file record. Where a repetition has a runtime consequence, state it; **where it is inert at runtime, say so and do not inflate it.** *A re-export facade's existence and its consumers are `01`'s; a name repeated inside one list is this block's.*

| Check | Description | Evidence required |
|---|---|---|
| Every export list is parsed | Entries, unique entries, and every name appearing more than once with both of its positions. **This list is the denominator** | R11 |
| A repeated name's runtime consequence is stated, or its absence is | Where the repetition has a consequence, state it; **where it is inert at runtime, report it as inert and do not inflate it** | R11 |
| The import form is tallied with the per-file record | Absolute or relative, per file, tallied across the tree. A form applied to most files and not the rest is the finding | R11 |
| The facade question is cited, not filed | Whether a re-export facade exists, and who consumes it, is `01`'s. A name repeated inside one list is this block's, and the two are recorded separately | R11 |

- Evidence: R1, R11.

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **The error taxonomy's internal consistency — the codes, the labels, the messages and the log context, and whether one condition carries one identifier or two** → **this phase.** **The escape, the exit status and the stream content** → `08`.

> **`08` owns the escape — the process terminating by a path other than the one its own handlers declare, observable only by running the binary and reading the exit status and both streams. `09` owns the taxonomy's internal consistency — the labels, codes, messages and log-context the handlers are built from, and whether the same condition carries one identifier or two. This phase files the taxonomy; it does not file the escape, the exit status, or the stream content.**

- **A validator's runtime escape — whether an input can reach past its validation-failure handler** → `02`. **A validator's declared type, and the reachability class of every source that can supply the value** → **this phase.** The reachability class is part of the finding's evidence and is **never assumed**: a source that is always text — an environment file, the process environment — can only supply text, so a divergence there is a coercion or a parse; a source reachable only from a programmatic caller can supply any value its type admits, so a divergence there is an unannounced contract.
- **Structural arrangement — the import graph, layer direction, cycles, re-export facades, bootstrap order** → `01`. **File-local craft — typing reach, naming, module size, a literal duplicated inside one file where it has no runtime consequence** → **this phase.** Test: *does the finding survive moving the file?* Yes → `01`.
- **A presentation-framework call in a service module, and a service that decides the process outcome** → `01` by the structural rule and `08` by its own claim. **This phase files no check for it and does not restate it as one.**
- **Documentation ownership, three ways.** A document claim **checkable against the live settings model** — a field's existence, type, default, declared range, legal value list, environment-variable name, or source precedence — is `02`'s, including in the example environment file. A document's **structural** description of the system — modules, layers, flows, architecture, removed features — and the accuracy of an individual module's or function's own docstring, is **this phase's**. A document's **command-line contract** — which options exist, their declared defaults, the status the process returns — is `08`'s. A document describing the audit pipeline itself is `99`'s.
- **Two copies of one document with no rule choosing between them, and a document describing no code in this repository** → **this phase.** The ownership rule has no referent for either case, and the gap is closed here rather than left to arbitration: the duplicate and the foreign document are **documentation defects this phase files once**. `08` owns a contract claim **inside whichever copy is authoritative once the fork is settled**, and this phase owns the fork. **This is a deliberate, stated extension beyond the scope this phase was given** — the wider than the decision line is recorded here on purpose, not adopted silently, and R6(b) exists only to evidence it. *(This three-way boundary is the position.)*
- **A file's permission mode, creation mode, atomicity and cleanup** → `07`, regardless of what the file contains. **The credential file's mode, and the access state actually in force on the declared platform** → `06`. **Every other artefact's mode** → `07`.
- **A third-party library's own signature, internals and behaviour under failure** → out of scope by design. State it; do not guess. This phase files what the configured reach does to the surface the checker **does** see, never what a library does internally.
- **Repository hygiene and what leaves the repository** → `11`.
- **A declared setting field — its type, bound, sourcing and whether it reaches its consumer** → `02`. **A dependency declaration in the build manifest** → `11`. **A fixed value's validity once declared** → `02`.
- **A credential's lifetime, and whether a secret reaches a sink** → `06`, always and never re-assigned. This phase files the identifier a condition carries, never its content.
- **The argument vector's design** → `05`. **Whether a secret appears in it** → `06`. This phase files neither.
- **Whether the test suite proves any of this, and the form its guards take** → `10`. This phase cites mechanism counts and files nothing from them.
- **Dead code in code, alive in documents** → `99`'s rule. `10` and this phase own the code side; the documentation claims describing such a component are this phase's.
- **Whether a finding from this phase survives validation** → `99`.
- **Licence posture, terms acknowledgement, notice mechanism** → not an audit subject; inadmissible under `problems-only` and expressly rejected. **Do not file.** The same applies to any performance, rate or capacity framing: the auditable residue is `03`, `04`, `07` and `02`; a general performance claim is inadmissible here.

## 8. Edge Cases

- A fixed value added as a raw string in one place and as an enumeration member in another.
- One file holding several unrelated concerns — **filed as navigation, never as a behaviour defect** (block (f)).
- The fully-unknown type used to make the checker pass.
- A validator annotated more narrowly than it is called.
- A value that can be a type its receiving point's annotation excludes, where the source that supplies it is always text.
- Two comments describing a global that does not exist.
- A document naming a module that does not exist.
- A condition that carries two identifiers for the same thing — **a question; the wording that asserts it is a finding pre-announced, and the corresponding row becomes ceremonial.**
- A component described as active that nothing wires in.
- Two copies of the same document with no rule choosing between them.
- A document that describes no code in this repository.

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are **not redefined here**.

| Severity | Conditions |
|---|---|
| CRITICAL | A condition the hierarchy raises that no handler in the product names, on a path the product takes, so the failure ends the run with no label, no text and no log context any caller can read. Or a document claim that names a behaviour the code contradicts in the opposite direction, where a reader following the document acts on a false premise. |
| HIGH | A declared condition that carries two different identifiers under different conditions, so one failure is reported under two names and no reader can correlate them. Or an annotation that promises a type a source reachable only from a programmatic caller can supply, with no contract stating it — an unannounced contract rather than a coercion. Or a rung of the taxonomy that no call site reaches, so the declared vocabulary and the delivered one differ. |
| MEDIUM | A document claim that does not match the code it names, with no observed consequence for a reader who did not rely on it. A fixed value carrying both an enumeration member and a raw spelling, where nothing checks they agree. A file whose top-level definitions belong to several unrelated concerns, where the cost is navigation. A type checker configured without a check the project's own typing rule needs, over a boundary with no test at all behind it. |
| LOW | A name repeated inside one export list and inert at runtime. A docstring naming an object that was renamed but not updated, where the code is otherwise equivalent. A convention applied to most files and not the rest. A document claim that cannot be checked at all and is recorded as such. |

**Type guidance.** `SPEC-DEVIATION` for behaviour or a configuration that contradicts the project's own declared rule. `DOC-UPDATE` **for a document claim that does not match the code it names** — this is the phase's most frequent type, and the one type no sibling phase but `02` files. `BEST-PRACTICE` for a defensible contract with a demonstrated gap. `RUNTIME-ERROR` for anything observed failing at runtime — expected to be rare here, because this phase is static.

**These conditions are a classification vocabulary, not a verdict.** Every severity is composed by this phase from its own run. **No severity carried by any preceding analysis, and no adjective attached to a subject in any preceding document, is inherited** (preamble rule 4). A finding whose consequence was not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity. **A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded, never as a clean bill of health.** A subject with no observed consequence does not get a condition here.

## 10. Recommended Sequence

1. Discovery (`## 4`).
2. **R1 first** — the baselines, the key-by-key configuration record, the per-dependency marker table, the platform note and both documented skips, written before the first subject is checked, so a later silence is a reported skip and not an omission.
3. R2, R3 — the error taxonomy and the surfaces that carry its identifiers.
4. R4, R5, R6 — the four document passes, each with its own denominator.
5. R7 — the typing surface the configured checker cannot reach.
6. R8, R9 — one fixed value's spellings, and one boundary value's declared type per source.
7. R10, R11 — responsibilities per file, and one file's own internal consistency.
8. Blocks (a) through (g) in the order they are written in `## 6`. **Do not reorder by convenience, and do not reorder by how easy a subject is to prove** — (g) is last because it is lowest risk, not because it is easiest.
9. Cross-cutting (`## 7`) and edge cases (`## 8`), re-reading `## 7` before writing each finding.
10. Consolidate findings.

**Second-pass order.** If this phase is re-run after a thin result, do **not** start again from step 1. Re-enter at the first item below for which no evidence was recorded, and continue downward: **R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → (a) → (b) → (c) → (d) → (e) → (f) → (g)**. A block with partial evidence is resumed; a block with complete evidence is skipped. `No problems found in this phase.` is admissible **only once R1's key-by-key configuration inventory and its per-dependency typing-marker table are both recorded** — a green checker and a green document read are the two ways this phase manufactures a clean bill of health, and the first line of the report must close that door.

## 11. Finding Prefix

Use `QLT-` for all findings in this phase. `QLT-` is unique in the catalogue: it shares no first two characters with any other phase prefix (`EN CF NE CO PR SE AR OU QL TS DE VA` are all distinct), and it is obtainable from no other prefix by a single plausible edit. It does not encode the phase number, so renumbering never invalidates a published finding ID.

## 12. Reporting

- Write findings to: `.ai/audit/09-code-quality/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.` — and only once R1's key-by-key configuration inventory and its per-dependency typing-marker table are both recorded.
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) **the exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible. **Every finding names the R-row that produced its evidence**, and every R-row states which of the two trees it searched.
  - **No row, table or note is offered for a subject that was checked and found correct**, and none is manufactured to fill an in-scope bullet that names one (preamble rule 5). A check invented to cover such a subject is itself a defect of this phase.
  - **A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded**, never as a clean bill of health.
  - **No finding is closed on the grounds that a configured check reported nothing.** Block (c) is reported from the configuration and the per-dependency marker table, and a green result is never a reason to skip R7 (preamble rule 1).
  - **A documentation finding names the document, the claim verbatim, the denominator it was checked against, and the code the claim names.** A general statement about documentation's accuracy is not a finding and is not filed.
  - **A boundary-typing finding names the source, the declared type, the producible type, and the recorded reachability class.** A row with no recorded class is not admissible.
  - **The report contains no severity, no outcome and no quoted text inherited from any preceding analysis or from the decision document**, including the in-scope parentheticals quoted only to place them in `## 2`.
