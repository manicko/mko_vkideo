---
name: 11-supply-chain
status: draft
validated: no
executor: auditor
problems-only: true
---

# 11 — Supply Chain

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — the inherited severity section is deleted with no
> successor, no summary and no pointer.** It carried entries marked as already
> satisfied and one entry declared as the open gap, every one of them asserted
> against artefacts that do not exist in this repository. **An executor reading a
> pre-satisfied phase emits a clean bill of health for a phase that was never
> run.** Nothing in this file states an outcome, and no annotation of any kind —
> resolved, open, known, accepted — may appear in any section. The no-problems
> line is gated on named verification rows in `## 10` and cannot be reached
> without them.
>
> **Binding rule 2 — no measurement is inherited.** A count, a ratio, an entry
> total, a file name or an adjective attached to a subject by any preceding
> document is a pre-answered outcome by another name. What may be carried
> forward is the *method* that obtains a measurement, never the measurement's
> result. The in-scope bullets in `## 2` are the decision's claims, not this
> phase's evidence; a claim re-derived as matching is filed as nothing, and a
> check is never manufactured to fill one. **Where an exclusion source differs
> between a local machine and a clean checkout, the phase records the source and
> never the answer.**
>
> **Binding rule 3 — the artefacts are settled by building, never by reading the
> configuration.** Silence in the packaging configuration is not evidence that a
> file is absent from an artefact, and presence is not evidence of a guarantee.
> The enumeration is the evidence; the configuration is one input to it.
>
> **Binding rule 4 — this phase is a boundary phase.** Its subjects are what
> leaves the repository, what reaches an artefact, and what a gate lets through.
> It files no internal correctness defect: those belong to the phase that owns
> the code. Every finding is stated as *what a consumer or a contributor
> receives*.
>
> **Binding rule 5 — a subject already checked and found correct is absent, not
> annotated:** no check row, no verification row, no note, no finding. Under
> `problems-only` a clean subject produces no report row, and **a present,
> correct, undefended artefact is still a finding.**

## 1. Goal

What leaves the repository — the declared dependency set, the built artifacts, the
declared entry points, and what the gate set lets through before anyone installs
it.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| Dependency declarations | Every mechanism in the build manifest that can name a distribution, and the bound each carries. | A declaration nothing reaches; one name declared by several mechanisms; two mechanisms giving one name different bounds. |
| Build and packaging configuration | Every declaration the build backend reads, per build target, and which target has none. | A file that reaches an artifact by default rather than by declaration; a target whose inclusion set is whatever the toolchain happens to do. |
| Built artifacts | The two distributable forms as an installer receives them: what is in them, what their metadata claims, and what a publish would release. | Material in a publishable artifact that has no business being there; an assertion with no artifact behind it. |
| Invocation surfaces | Every way the installed product is started, declared or not, and what each emits and returns. | Two supported invocations a caller cannot reproduce or tell apart. |
| Resolution record | The locked resolution of the declared set, and whether anything verifies it. | A manifest edited without a re-lock; a resolution that drifts from the declaration. |
| The gate set | Every automation the repository carries, what each enforces, and what its trigger admits. | A change merged on a check unrelated to it; a declared verification that nothing enforces. |
| Repository boundary | What the index carries that no tool reads, what the working tree carries that the index does not, and the rules deciding both. | Material outside both the index and the rules; a rule that protects exactly one machine. |

**In scope:**
- Production-versus-dev dependency declaration hygiene; declared-but-unused dependencies; formatters declared beside a linter that already owns their function.
- The built artifact's contents and whether shipped package data is actually packaged.
- Equivalence of the two declared entry points.
- Lockfile reproducibility; dependency-update automation.
- Dependency scanning and secret scanning.
- The repository's complete workflow set: what it enforces and what it does not — **excluding the test-execution job, which is Phase 10's**.
- Repository hygiene: committed editor fragments, output files, and stale bytecode for deleted modules.
- **The source distribution as a publishable artifact in its own right:** its composition, and whether a path reaches it because the repository excludes it or merely because nothing tracks it.
- **Repository-carried ignore coverage for secret-bearing paths**, and the scanning controls that would notice their loss.

*Claims made inside the bullets are the decision's scope, not this phase's evidence. Each is re-derived by the R-row named in the block that owns it, and a claim re-derived as matching is filed as nothing. A bullet naming a subject that produces no check in this file is not an instruction, and no check is manufactured to fill one (binding rule 5).*

**Out of scope:**
- Whether the tests themselves are good, and the job that executes them → `10`.
- Settings fields → `02`. The runtime mechanism of any redaction, and whether a secret reaches a sink → `06`. A documented claim → `09`.
- Certificate-verification policy and its propagation to every transport → `03`.
- Licence posture, terms acknowledgement, notice mechanism, and any general performance, rate or capacity framing → not audit subjects; inadmissible under `problems-only` and expressly rejected. **Do not file.** The artifact that ships a licence assertion with no licence text is this phase's; the licence claim itself is not.

## 3. Prerequisites

- The project's own verification commands, quoted from `.ai/context/commands.md`: `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>`. The configured type checker is the strict one named there; a second checker present in the development dependency group is not it and must not be substituted.
- **No container, no database, no service, no network.** Nothing is published to a real index and no advisory database is queried.
- A scratch directory **outside the repository** for both build outputs and anything an enumeration leaves behind. A clean working-tree check is run after every build.
- The ability to execute the installed product by **each** invocation form the package structure permits, and to read each exit status.
- **Every repository-wide search applies the exclusion list in `## 5` before matching.** A count taken over an un-excluded tree is not admissible evidence.

## 4. Discovery

Map the boundary before checking anything. **Use roles, not names.** No concrete file, module or class name appears in this section. **A subject that maps to nothing is a gap, and a gap is reported.**

1. **Declaration map** — every mechanism in the build manifest that can name a distribution, the name set each carries, and the bound it gives. The denominator for (d).
2. **Consumer map** — for each declared name, the import surface that would reach it, split by production source, test source and documentation, and every other mechanism that declares the same name. The denominator for (d).
3. **Packaging-configuration map** — every declaration the build backend reads, per build target, and which target has no declaration at all. The denominator for (a) and (b).
4. **Runtime-read map** — every file the installed product reads by a path it derives from its own location, and what the code does when that path is absent. The denominator for (b).
5. **Invocation map** — every way the installed product is started, which are declared and which merely work, and what each emits and returns. The denominator for (g).
6. **Gate map** — every automation definition the repository carries: per definition the trigger and its filter, per job its commands and its failure condition, and every recognised configuration for each scanning, update, ownership and pre-commit class. The denominator for (c) and (e).
7. **Boundary map** — every path in the working tree, marked tracked, untracked-and-ignored, or untracked-and-unexcluded, with the file each exclusion depends on. The denominator for (f) and for the ignore-coverage row of (e).
8. **Evidence map** — for every row in `## 5`, which method produces it, and for any row that cannot run here, the exact skip text that will be emitted instead. **A row with no method mapped is not executed, and is reported as not executed.**

*Role vocabulary: the build manifest and each of its declaration mechanisms · the build backend's per-target configuration · the two distributable artifact forms · the metadata block of a built artifact · the file the installed product reads by a derived path · the console-script declaration and the module entry point · the automation directory and each definition in it · the recognised configuration for each scanning, update, ownership and pre-commit class · the version-control index · the repository's ignore rules · any rule held outside the repository · a nested ignore file written by a tool · the compiled-cache directory and the source basename set.*

## 5. Runtime Verification (mandatory)

> **The evidence regime, stated once. Five families, and only five:** *build and enumerate* a distributable artifact and list what is inside it, then exercise what was built; *read the manifest* and record what it declares; *read the built artifact* and record what its own metadata claims and carries; *read the complete gate set* and record what each definition runs and admits; *search a bounded corpus* and record its counts. Every row below belongs to one of them. Nothing here needs a network, a service, an index, or a published package.
>
> **Search exclusion rule — binding, and part of every search method below.** Before matching, every repository-wide search excludes: **a stale worktree copy of an earlier catalogue; any vendored dependency tree; this audit's own report corpus and findings; the build-residue directory that mirrors a past manifest state; and every compiled-cache directory.** The last is not optional — the orphaned-bytecode subject is satisfied by its own evidence if the search looking for it also matches the objects it is looking for. Use the index-scoped form, which self-excludes the first two, and confine hygiene work to the index; where a filesystem walk is unavoidable, apply every exclusion explicitly, including the cache directories. **A count taken over an un-excluded tree is not admissible evidence, and a finding is not filed on one.**
>
> **Two rules that follow.** 1. *No artefact property is asserted before its enumeration.* 2. *A method that cannot run here emits a documented skip in fixed wording* — what was attempted, why the evidence is unobtainable, what remains verifiable — because under `problems-only`, silence reads as "no finding".

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | The two built artifacts, enumerated | *Build and enumerate.* `uv build --out-dir <scratch outside the repository>` for both targets; then list the wheel's central directory and the source archive's member list (`python -m zipfile -l`, `tar -tzf`), recording for each the entry count, the archive size, and a per-top-level-path entry count and byte total. Run a clean working-tree check afterwards. | Both full member lists; the two counts; the two sizes; the per-top-level breakdown. |
| R2 | What the wheel's metadata claims and carries | *Read the built artifact.* From the built wheel, read the `.dist-info` entry list and the metadata block: the licence expression, whether any licence text is shipped, the extras declared, and every `Requires-Dist` line — flagging any distribution named more than once with different bounds. Separately, from the source tree, record whether a typed-distribution marker and a licence file exist at all. | The `.dist-info` entry list; the metadata header; the duplicate-with-different-bounds list; the two existence answers. |
| R3 | Whether a file the installed product reads at runtime is a stated guarantee | *Build and enumerate, then read the load site.* (a) From R1's wheel listing, extract every path the package would resolve at runtime by a path derived from its own location, with its size. (b) Read the packaging declaration that admits it, or record that none names it and the file is present regardless. (c) Read the load site and record the condition guarding it and the level at which a missing file is reported. | The runtime-read file list; the admitting declaration or its recorded absence; the guard's form; the reporting level. **A present file is not a pass; an absent one is not predicted.** |
| R4 | The source archive's composition and the mechanism that admitted each path | *Build and enumerate, then classify.* From R1's member list: per-top-level counts and sizes. For each contributor, `git ls-files` scoped to it — does the index track it? — and the repository's ignore rules — do they name it? **Untracked-and-unignored is a different state from untracked-and-excluded, and only the second keeps a path out.** For any tree admitted or excluded only because a tool wrote its own nested ignore file, record that the file is untracked, so the exclusion does not travel with a clean checkout. | The contributor list with both answers per contributor; the archive total against the wheel's; every exclusion that depends on a file the repository does not carry. |
| R5 | Declared dependencies: coverage, agreement, reachability | *Read the manifest, then search a bounded corpus.* Read every mechanism that can name a distribution, section by section, recording the name set and bound each carries. For each name, search the source tree, the test tree and the documentation (index-scoped, exclusion rule applied) for the import that would reach it, and record the hit count per tree. Record every name declared by more than one mechanism, and every pair of mechanisms giving one name different bounds. Cross-check the name set against the resolved lock record. | The per-mechanism name sets and bounds; the per-name hit counts per tree; the duplicate list; the conflicting-bounds list; the lock cross-check. |
| R6 | What a clean environment actually installs | *Read the manifest, then execute the projection.* `uv sync --dry-run` (does not modify the environment): record the exit code and the full install/uninstall list. Then record which of the four verification commands resolve in the current environment, and which would not under that projection — decided by resolution, without performing the uninstall. The two questions: which mechanism carries the tools the project verifies itself with, and which mechanism the default provisioning path installs. | The dry-run exit code and list; the resolved/unresolved verdict per verification command; the declaring mechanism per tool. |
| R7 | Declared tools that nothing invokes | *Search a bounded corpus, then read the configured rule set.* For each declared development tool, search every tracked file (exclusion rule applied) for an invocation of it, subtracting the declaration itself, the lock record and this audit's corpus. Then read the rule set the tool the project does use is configured with, and record whether it already performs the named tool's function. | The per-tool invocation counts; the configured rule set; the per-tool verdict on whether the function is already covered. |
| R8 | The resolution record, and whether anything checks it | *Read the manifest, then read the gate set.* `uv lock --check`: record exit code and message. Read the record's header for its format version, its package count, and whether every entry carries a content hash and an upload time. Then, from R9's enumeration, record whether any job or hook runs that check. The record's own properties and the absence of an enforcer are two facts and are recorded as two. | Exit code and message; the header fields; the hash-presence count; the enforcer count. |
| R9 | The complete job set and what each job enforces | *Read the complete gate set.* Enumerate the automation directory recursively **and** `git ls-files` scoped to it — a definition can exist and be untracked. For each definition record the trigger, whether it is path-filtered, and which paths the filter admits; for each job, the commands it runs and what it fails on. Then record, against this catalogue's job classes, which exist and which do not — **lint, format check, type check, dependency scan, secret scan, lockfile check, build and publish, excluding the test-execution job, which another phase owns** — and record the filter's effect on a change to the source tree, the test tree and the manifest. | The definition list; per definition the trigger and filter; per job its commands and failure condition; the present/absent class list; the three filter verdicts. |
| R10 | Scanning, update automation, ownership, pre-commit — and the committed-secret measurement | *Search a bounded corpus; path-check the configurations.* (a) Path-check each recognised configuration for each class and record present/absent; `git grep` tracked files (exclusion rule applied) for the tool names each class implies, recording the hit counts. (b) Separately, sweep tracked files for third-party session-credential names and record the count. **A zero-hit material sweep is a measurement; a zero-hit tool search is the absence of a scanner. They are two rows and are never merged.** (c) From the boundary map, record every secret-bearing path and whether a repository-carried ignore rule names it, and read each such rule's negation. | The path checks; the per-class tool-name hit counts; the material sweep count; the per-path ignore verdict including each negation. |
| R11 | Equivalence of the declared invocation forms | *Build and enumerate, then exercise what was built.* Using R1's build, for each declared console-script form and each module form the package structure permits, including any undocumented one: run `--help` and diff the bodies, then a command missing a required argument, an unknown command, and no arguments; capture each exit status in every form. Record the two usage-string variants as a separate datum from the option and status comparison. | Both help bodies and their diff; the exit status per form per case; the two usage strings; any undocumented form. |
| R12 | Repository hygiene: the tracked class, and the untracked-and-unexcluded class | *Search a bounded corpus, then enumerate the working tree.* (a) `git ls-files` filtered to root-level entries and to non-source extensions; read each candidate and record what it is, whether the ignore rules name it, and whether it also reached the built source archive. (b) Enumerate the working tree; for every path the index does not track, record whether the rules name it and, where they do not, whether an exclusion comes from a nested file a tool wrote or from a rule held outside the repository. **Three states, recorded as three: tracked-and-ignored, untracked-and-ignored, untracked-and-unexcluded.** | The tracked-candidate list with contents; the per-candidate ignore verdict; the working-tree paths the index does not track; the exclusion-source class per untracked path. |
| R13 | Compiled artifacts whose source is gone | *Search a bounded corpus, then diff name sets.* Enumerate compiled cache files under the source and test trees, with the cache directories excluded from every other row's search; strip the interpreter and test-plugin version tags; diff the resulting module-name set against the source basenames. Record the count, the names, and how many cache generations coexist. Record separately whether the ignore rules already cover this class — **a class already excluded produces no finding, and the reason it is already excluded is the evidence.** | The compiled-file count; the orphaned names; the coexisting generations; the ignore verdict for the class. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how is rewritten here, not skipped at execution time. A `Method` of "inspect the manifest" or "look at the workflows" is not admissible: every method must produce its evidence by building and enumerating something, by reading a named artifact and recording what it says, or by running a search and recording its count.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.** R1, R2, R5, R6 and R8's own results are never filed as findings; they are the state in which a finding was observed.

> **Documented-skip register — emit these in the fixed wording, never as silence.** *Live advisory-database access* (which dependencies carry a known vulnerability): requires a network an advisory database is not reachable from here; **no vulnerability count is asserted**, and the fileable subject is the absence of a scanner from R10. *Publishing to a real index* (what a real release would expose): not performed; the fileable subject is the archive's measured composition from R1 and R4, and the publication consequence is stated as a projection. *A real install from source* (what a consumer's build does with the archive): not performed offline; the fileable subject is the archive's contents. *Live behaviour of a third-party transport, downloader or browser library*: out of scope by design — state it, never guess it.

## 6. Audit Dimensions (checks + evidence)

Seven blocks, ordered by risk, **descending**. The letter order **is** the re-entry order (`## 10`): a pass cut short returns the blocks it reached. **Executability does not reorder risk** — the most mechanical block is still third. **No block title or description states an outcome**; each is the question, and the finding is named as a condition to look for. No block is merged: a build-and-enumerate subject and a search-tracked-files subject admit different evidence.

### (a) Source-archive composition — what a publishable artefact carries

> What reaches the source archive, and what decides it. Enumerate the archive, group the members by top-level path, and for each contributor ask two separate questions: does the version-control index track it, and do the repository's ignore rules name it. **Untracked and unignored is a different state from untracked and excluded, and only the second keeps a path out** — record which of the two each contributor is, and record any contributor whose exclusion depends on a file the repository does not carry. Compare the archive against the wheel by the same enumeration. Judge the result against what an index consumer would receive.

| Check | Description | Evidence |
|---|---|---|
| Contributor classification | Every top-level path in the archive is classified tracked / untracked-and-ignored / untracked-and-unexcluded, with the rule or file each classification depends on. | R4 |
| Repository-carried exclusion | Every excluded contributor is excluded by a rule the repository carries, not by a rule written by a tool or held outside the repository. **Where the source differs between this machine and a clean checkout, record the source; the answer is the other phase's step, not this block's.** | R4, R12 |
| Duplication of shipped source | A second copy of the shipped package inside an artefact derived from that package is recorded as a copy, with its path and entry count. | R1, R4 |

- Evidence: R1, R4, R12

**Do not write** "the archive ships the whole repository". The enumeration produces the numbers; the consequence sentence is the auditor's. **The archive's size relative to the wheel's is a composition datum and never a performance, rate or capacity claim** — that framing was expressly rejected and is not a subject here.

### (b) The shipped data file — a stated guarantee or an inherited default

> Whether a file the installed product reads at runtime is present **by declaration or by default**, and what would notice its loss. Find the runtime-read files from the discovery map, look for each in the built wheel, then read the packaging declaration that admits it — or record that no declaration names it. Read the load site and record the condition guarding it and the level at which a missing file is reported. **The subject is the undefended state, not the current one: a file that is present today is evidence about today, and a correct outcome defended by nothing is the finding.** Neither "it ships without being declared" nor "it is packaged" is written as the outcome: both are conclusions the enumeration and the declaration read produce, and the absence of the declaration is recorded as an absence, never as a predicted absence from the artefact.

| Check | Description | Evidence |
|---|---|---|
| Declared, not defaulted | Every file the product reads at runtime by a derived path is named by a packaging declaration, so narrowing the artefact's file set cannot remove it. | R3 |
| Loss is observable | A missing runtime-read file is reported above the lowest logging level, and the code path that would fail without it is reachable. | R3 |
| Degradation is not silent | The consequence of the file's absence is bounded and stated, rather than the product running on without it. | R3 |

- Evidence: R3

**This is a guarantee question, not a packaging-mechanics question and not a licence question.** A metadata assertion the artefact carries, and the artefact's carrying of it, are this block's subjects; the assertion's merit is not.

### (c) The gate set — what the pipeline enforces before anyone installs

> The repository's complete job set: what exists, what each job fails on, and what its trigger admits. Enumerate every automation definition present **and** tracked, because a definition can exist and be untracked. For each job record the commands it runs and its failure condition, then record which job classes are present and which are absent — **excluding the test-execution job, which another phase owns**. Then ask what the trigger admits: a filter that excludes the source tree, the test tree and the manifest means the definition does not run for the change it appears to guard.

| Check | Description | Evidence |
|---|---|---|
| Complete enumeration | Every automation definition is found by directory walk and by index-scoped listing; the two agree, or the disagreement is the finding. | R9 |
| Declared verification is enforced | Each of the project's own four verification commands is run by some job or hook, or its absence is recorded as an absence of enforcement. | R9, R8 |
| Trigger admits the change | Every definition's path filter admits a change to the source tree, the test tree and the manifest, or the filter is recorded as the reason the definition is not a gate. | R9 |
| Job classes | Lint, format check, type check, dependency scan, secret scan, lockfile check, build and publish: each present or absent. **Test execution is excluded from this list.** | R9 |

- Evidence: R8, R9

### (d) The declared and resolved dependency surface

> Every mechanism in the build manifest that can name a distribution: what each declares, whether anything reaches it, whether one name is declared more than once, and whether two mechanisms give it different bounds. Then the resolved record: whether it is in sync, whether every entry carries a hash, and whether anything checks it. Two questions that are routinely confused and must stay separate: **which mechanism carries the tools the project verifies itself with**, and **which mechanism the default provisioning path actually installs**. A tool declared beside a tool that already performs its function is the shape to look for; the manifest's own configured rule set is the evidence.

| Check | Description | Evidence |
|---|---|---|
| Declaration is reachable | Every declared distribution is imported by something in the source, the tests or the documentation, or its absence is recorded. | R5 |
| One name, one mechanism, one bound | No distribution is declared by two mechanisms, and no two mechanisms give one name different bounds. | R5, R2 |
| The default path installs the gates | A default provisioning step leaves every tool the project's own verification commands name available. | R6 |
| Nothing declared and never invoked | Every declared development tool has at least one tracked invocation, or is reported. | R7 |
| Resolution is recorded and checked | The resolution record is in sync, every entry carries a hash, and something verifies it. | R8 |

- Evidence: R2, R5, R6, R7, R8

### (e) The repository boundary — scanning and ignore coverage for secret-bearing paths

> Two measurements that are constantly merged and must not be. **What is committed:** sweep the tracked files for third-party session-credential names and record the count — a zero-hit sweep is a measurement of committed material, and it is evidence that must be recorded even when it is zero. **What would notice if it stopped being zero:** whether a scanner exists at all, and whether the repository's ignore rules name every path that can hold secret material. A secret that escapes at runtime is another phase's; **a rule that stops covering a path is this phase's, and the two are filed separately.**

| Check | Description | Evidence |
|---|---|---|
| Committed material | The tracked-file sweep for third-party session-credential names, recorded as a count, including the zero. | R10 |
| A scanner exists | A secret-scanning control is configured and something runs it; the absence of the control is the finding, never the absence of material. | R10 |
| Ignore coverage is complete | Every path that can hold secret material is named by a repository-carried ignore rule, and each such rule's negation is read — a negation that re-admits a real file is the finding. | R10, R12 |
| The other scanning classes | Dependency scanning, update automation, ownership and pre-commit controls: each configured, each run by something. | R10 |

- Evidence: R10, R12

### (f) Repository hygiene — what the index carries and what the working tree does not exclude

> Everything the index tracks that no tool reads, and everything the working tree holds that the index does not track **and** the ignore rules do not name. Read each tracked candidate and say what it is. For the untracked set, record three states as three: tracked-and-ignored, untracked-and-ignored, untracked-and-unexcluded — the last is the one to characterise, and its exclusion source is the question, because a rule held outside the repository protects exactly one machine. **Where the source of an exclusion differs between this machine and a clean checkout, the source is recorded and no answer is written for the other machine.** Fold in the compiled artefacts whose source is gone: a class the ignore rules may already cover produces **no** finding, and the reason it is already covered is the evidence.

| Check | Description | Evidence |
|---|---|---|
| Tracked debris | Every index-tracked entry no tool reads is identified, with its content read and its mechanism recorded. | R12 |
| Untracked-and-unexcluded | Every working-tree path the index does not track and the rules do not name is listed, with the file its exclusion depends on where one exists. | R12 |
| Orphaned compiled artefacts | Every compiled artefact with no source beside it is listed, with the coexisting cache generations, and the class's existing ignore coverage is recorded. | R13 |
| Not a filesystem sweep | No hygiene claim is established from a walk that included a worktree copy, a vendored tree, the audit corpus or a compiled-cache directory. | §5 exclusion rule |

- Evidence: R12, R13

### (g) Invocation equivalence — the two declared ways in

> Every way the installed product is started, and whether the declared ones agree. Execute each declared console-script form and each module form the package structure permits, including any that merely works without being declared. Compare the option bodies, the exit statuses and the usage strings **as three separate comparisons** — a help line that differs is a different fact from a status that differs, and a documented-but-undeclared third form is a third fact again. The question is whether a caller can tell the forms apart and reproduce what one of them printed.

| Check | Description | Evidence |
|---|---|---|
| Behavioural equivalence | Every option, subcommand, help body and exit status agrees across the declared forms. | R11 |
| String identity | The usage and error text is identical across the declared forms, or the divergence is recorded. | R11 |
| Declared set is complete | Every form the package structure permits is either declared or recorded as an undocumented invocation path. | R11 |

- Evidence: R11

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.** The first three are the catalogue's general ownership rules as they bear on this phase.

- **R-A — a file's permission mode, creation mode, atomicity and cleanup** → `07`, whatever the file contains; **the credential file's content and redaction, and its permission mode with the platform reality of that mode, → `06`.** **This phase owns what an artefact's *contents* are** — which paths reached it, which the index tracks, which the ignore rules name — **and never its mode or its cleanup.** A contaminated archive is `11`'s on the contents and `07`'s on any mode-or-residue question, and the two are never filed as one finding.
- **R-C — a declared setting field** → `02`; **a dependency declaration in the build manifest** → **this phase**; **a documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09`; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`. **Whether the declared set is right** → **this phase. Whether the installation or provisioning documents describe it correctly** → `09`'s wording. The two are cited, never merged.
- **R-E — a document** is owned by the phase owning the code it describes; a document describing the audit pipeline itself → `99`. Applied here: a document claim about packaging, provisioning, publication or installation is **this phase's**; the pipeline's own documents remain `99`'s.
- **The gate set — this line settles the seam for both siblings.** *The job that executes the test suite, and whether the tests are good → `10`.* **Every other job is this phase's: lint, format check, type check, dependency scan, secret scan, lockfile check, build, and publish. A job that runs the configured linter or the configured type checker is this phase's, not `10`'s.** This phase files the *shape* of the set — which job classes exist, what each fails on, what its trigger admits — and never files whether the tests prove anything.
- **Secret-bearing paths.** *Whether a secret reaches a sink, and the secret's own lifetime → `06`.* **Whether the repository's ignore rules cover the paths that hold secret material — and therefore whether those paths can reach the index or a built artefact — is this phase's, ruled.** The two are filed separately: a rule that stops covering a path is this phase's finding; a secret that escapes at runtime is `06`'s, and this phase must not file it.
- **A compiled artefact whose source was deleted** → **this phase**, ruled; it is struck from the code-quality phase. `09` owns the documentation claims about the component that is gone; `99` arbitrates the dead-code reclassification. This phase files the orphaned artefact and says nothing about the code it used to hold.
- **The source-level no-`print` rule** → `09`. The log stream, the renderer selection and the handler wiring → `08`. The redaction of a value, and whether a secret reaches a sink → `06`. **This phase owns none of them** and names no logging subject in any dimension. It owns only whether a declared dependency set, a built artefact and a gate set are correct.
- **Certificate-verification policy and its propagation to every transport** → `03`. **This phase owns neither.** The one adjacent subject that remains this phase's: whether a third-party transport library is a declared dependency, whether it is reachable, and whether it is scanned.
- **Where a setting is sourced, its type and its bound** → `02`. The credential's lifetime, and whether a secret reaches a sink → `06`. The repository's ignore coverage of secret-bearing paths, and the secret-scanning control → this phase. **No secret is read, written or observed by this phase; only the coverage that keeps one out of the repository and out of an artefact.**
- **Structural arrangement — the import graph, layer direction, cycles, facades, bootstrap order** → `01`. **File-local craft** → `09`. Test: *does the finding survive moving the file?* If yes, it is `01`'s and is not this phase's, even when the file is debris.
- **The concurrency, extraction, transport-resilience, filesystem, subprocess, browser, output and layer subjects** → `04`, `03`, `03`, `07`, `05`, `05`, `08`, `01`. **This phase files the artefact each of them produces, never the behaviour inside it.** A file at rest is this phase's; what the process does with it is its owner's.
- **A defect in the audit catalogue's own documents, corpus or tooling** → `99`. **The presence of that corpus inside a publishable artefact is this phase's finding** — it is artefact contents — **while the condition of the corpus itself is `99`'s**, cited and never filed here.
- **Whether a finding from this phase survives validation** → `99`. **A sibling phase's measurement may be cited; no sibling's finding, severity or conclusion is inherited, restated or re-filed.**
- **Licence posture, terms acknowledgement, notice mechanism; any general performance, rate or capacity framing** → not audit subjects; inadmissible under `problems-only` and expressly rejected. **Do not file.** An artefact that ships a licence assertion with no licence text is this phase's; the licence claim itself is not.

## 8. Edge Cases

- Two contributors publish the same commit and the artifacts differ, because one machine's ignore state is not the repository's.
- A distribution is declared twice with different bounds, and the looser one reaches the extra.
- A tool writes its own nested ignore file, so a clean checkout has no exclusion that this machine relies on.
- A vendored tree sits inside the working tree, is tracked by nothing, and reaches the artifact anyway.
- A path is excluded from the index but included in the archive, or the reverse.
- The rule that keeps a secret-bearing path out is narrowed, and a negation re-admits a real file.
- A guard around a runtime-read file is the only thing between a shipped file and a silent degradation, and it reports at a level nobody reads.
- A definition exists, is tracked, and its path filter excludes the tree it appears to guard.
- A scan is configured and nothing runs it on a schedule or on a change.
- A resolution record is in sync today, and a manifest edit is never followed by a re-lock.
- A documentation-tool run leaves a cache that is ignored only by the file the tool itself wrote.
- An index-tracked artefact no tool reads, and the scratch script that plausibly committed it, ship inside the same artifact as the code.
- The only exclusion protecting a machine-local path lives in a file that is not in the repository.
- A finding is reachable from two phases and gets filed twice, or restated with a severity this phase did not observe.
- A cleanup clears one cache generation and leaves the other, so the class of artifact survives the fix.

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are **not redefined here**.

| Severity | Conditions |
|---|---|
| CRITICAL | Material that must not be released is present in an artefact that the ordinary release path would publish, and the exposure is not confined to the author who created it. |
| HIGH | A guarantee the product or the repository depends on is undefended: a file the installed product reads at runtime, or a check the project declares and nothing enforces — so a change to the packaging, the manifest or the ignore state degrades or exposes it with nothing reporting it. |
| MEDIUM | A declaration, a bound or a record is wrong or unenforced while the current run is unaffected: an unreached dependency, one name declared twice with different bounds, a resolution nothing checks, a scanner nothing runs, an exclusion that protects one machine. |
| LOW | An equivalence or a hygiene defect with no effect on what an installer receives: divergent usage text between declared invocation forms, index-tracked debris no tool reads, a compiled artefact with no source. |

**No count, file name, ratio or subject appears in this table**, because a condition written beside a subject is a pre-answered outcome by another name. These four rows are a classification vocabulary; every severity is composed by this phase from its own run.

**Type guidance.** `SPEC-DEVIATION` for a declaration or configuration that contradicts the project's own stated intent. `BEST-PRACTICE` for an arrangement that works today and is defended by nothing. `RUNTIME-ERROR` for a build or invocation observed failing, or a divergence observed between two supported invocation forms. `DOC-UPDATE` only for a document that describes packaging, provisioning, publication or installation incorrectly — the wording is this phase's, the behaviour it describes is also this phase's, and they are one finding.

**A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded, never as a clean bill of health.** A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity. **No severity carried by any preceding analysis, and no adjective attached to a subject in any preceding document, is inherited.**

## 10. Recommended Sequence

1. Discovery (`## 4`), and the evidence map's verdict recorded before any subject is checked.
2. **R1 first** — one build feeds R2, R3, R4 and R11, and a subject established before the build is a recollection.
3. R2, R3, R4 — the artefact cluster, in the order metadata, guarantee, composition.
4. R5, R6, R7, R8 — the declaration cluster, ending with the record that the first three either do or do not feed.
5. R9, R10 — the enforcement cluster: what exists, then what is missing, then the measurement that keeps the two apart.
6. R11, R12, R13.
7. Blocks (a) through (g) in the order they are written.
8. Cross-cutting (`## 7`) and edge cases (`## 8`), re-reading `## 7` before writing each finding.
9. Consolidate findings.

**Second-pass order.** If this phase is re-run after a thin result, do **not** start again at step 1. Re-enter at the first item below for which no evidence was recorded and continue downward: **R1 → R2 → R3 → R4 → R5 → R6 → R7 → R8 → R9 → R10 → R11 → R12 → R13 → (a) → (b) → (c) → (d) → (e) → (f) → (g)**. A block with partial evidence is resumed; a block with complete evidence is skipped. `No problems found in this phase.` is admissible **only once R1, R5, R9, R12 and R13 are all recorded** — those five rows are the ways this phase manufactures a clean bill of health, and the first line of the report must close that door.

## 11. Finding Prefix

Use `DEP-` for all findings in this phase. `DEP-` is unique in the catalogue, shares no first two characters with any other phase prefix (`EN CF NE CO PR SE AR OU QL TS DE VA` are all distinct), is obtainable from no other prefix by a single plausible edit, and does not encode the phase number, so renumbering never invalidates a published finding ID.

**This phase adopts no identifier already present in the tree** — a form another artefact or report already carries is inventory, never this phase's own, and the validator cannot resolve which catalogue a collision belongs to. A number minted before its evidence exists is a pre-answered outcome by another name.

## 12. Reporting

- Write findings to: `.ai/audit/11-supply-chain/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, check row or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.` — and only once R1, R5, R9, R12 and R13 are all recorded.
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, **naming the R-row that produced it**, and (2) **the exact consequence** — not "violates invariant X".
  - **An artefact finding is admissible only with the enumeration that produced it**: the member list, the per-top-level counts, the metadata block. A recollection of what an artefact contained is not evidence.
  - **A count taken over an un-excluded tree is not admissible.** If a search was run without the exclusion list, the finding is re-run or it is not filed.
  - **A correct outcome observed today is not a finding, and an undefended one is.** Where a file is present and nothing states that it must be, the finding is the absent guarantee, and the present state is its evidence — the reverse framing is not filed. **A present, correct, undefended artefact *is* the finding.**
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - **A subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded**, never as a clean bill of health.
  - **No row, note or finding exists for a subject that was checked and found correct**, and none is manufactured to fill an in-scope bullet that names one.
  - **Every documented skip is written in the fixed wording.** `n/a` and silence are inadmissible.
  - **The report contains no severity, count, outcome or quoted text inherited from any preceding analysis or from the decision document**, including the in-scope claims quoted only to place them in `## 2`.
