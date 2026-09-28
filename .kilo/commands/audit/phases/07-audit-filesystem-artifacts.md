---
name: 07-filesystem-artifacts
status: draft
validated: no
executor: auditor
problems-only: true
---

# 07 — Filesystem Artifacts

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — severities are composed by this phase's own run, never
> inherited.** The analysis that preceded this file carried a problem list and an
> ordering; the decision document attached adjectives to subjects. Neither is
> citable. Every severity comes from this phase's run against `## 9`.
>
> **Binding rule 2 — residue and silence are two findings in two phases.** This
> phase files that residue exists and was not cleaned. Whether the operator was
> ever told is `08`'s. One file may carry both and one fix may serve both, but a
> finding in this phase never carries both halves.
>
> **Binding rule 3 — the mode block's silence is this phase's likeliest failure.**
> Its confidentiality guarantee cannot be asserted as written on the declared
> platform. What the run *does* establish is the measured mode, the effective
> access-control state, the count of independent confining controls, and the mode
> of the directory that supplies the real protection. All four are fileable, and
> the absence of any of them is the failure. "Cannot be asserted here" is the
> platform note, not the finding.
>
> **Binding rule 4 — record the observation before the conclusion.** No check may
> state the outcome it is looking for, and no block description may be read as a
> premise. Where a fact belongs to another phase this phase cites it and files
> nothing about it; citing a fact is not a licence to restate that phase's
> conclusion, and a defect with two owners produces **one** finding per owner, on
> that owner's half.

## 1. Goal

Every persistent and temporary artifact: where it may be written, how it is written, what permission mode it carries, and what survives the process.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| What outlives the process | The hidden working tree, the final name, the child's own partial name and the merge intermediates — each across a completed run, a non-zero result, a retry exhaustion and an end the process cannot intercept | A cleanup targeting a name that does not exist; cleanup reachable only from the success path; a residue class no sweep matches; a survivor indistinguishable from a finished download |
| The mode on every artefact | What the code requests for each file it creates and what is measured in force afterwards, including the directory that supplies the real protection | A requested mode reported as the effective one; a hardened file in a directory created without one; a check-then-act window; a guarantee with no oracle that can fail on the declared platform |
| The name itself | What shape a name built from an untrusted string can take: the replaced character set, control characters, reserved device names, trailing separators, and what the truncation bounds | A hard failure on a string the origin supplied; a name the current derivation cannot produce, filed at the wrong scope; a truncation that bounds one component and not the path |
| Where the path may go | What the validator refuses, what it admits, the directory its containment comparison is made against, and which call sites enable it | No containment root at all; a comparison that warns and does not refuse; a composed path that never re-enters the validator; a security-labelled error raised at a legitimate user path |
| One path, many writers | Whether anything makes the derived name unique, and what every transport that can write the final name does when the name already exists | No deduplication anywhere; a batch position reaching only one fallback branch; two entries deriving one name, one tree and one partial; an overwrite flag on every transport |
| The working set | What the download costs on the volume while it runs, and whether anything bounds it | A peak several times the final artefact with no ceiling above it; no free-space probe and no size cap anywhere; an interruption between the two steps of a write leaving residue no sweep matches |

**In scope:**
- Output-path validation and containment — including the **absence** of a containment root.
- Title-to-filename derivation: character handling, length truncation, reserved device names, trailing separators, and the collision/overwrite behaviour of the derived name across single and batch runs.
- The hidden working directory for downloaded segments and its staleness signature.
- Atomicity of segment writes (write-to-temp then rename).
- Orphan, partial and residue cleanup on success, on failure, on retry exhaustion, and on interruption — and the fact that cleanup currently sits on the success path rather than in a `finally`.
- The two **opposing** retention policies on adjacent paths (segments deliberately preserved for resume vs. partial output deleted on retry exhaustion) — these must be judged together, not separately.
- Merge-stage disk amplification; the absence of any output-size or free-space ceiling.
- The permission mode of every file the process creates **except the credential file**, and the platform reality of that mode. **The credential file's mode and its platform reality are `06`'s** (`## 7`).

*Claims made inside the bullets are the decision's scope, not this phase's evidence.
Each is re-derived by the R-row named in the block that owns it, and a claim re-derived
as matching is filed as nothing. A bullet naming a subject that produces no check in
this file is not an instruction, and no check is manufactured to fill one.*

**Out of scope** (each item names its owner):
- Launching or killing a process → `05`.
- The cookie file's own lifecycle, its permission mode and the platform reality of that mode → `06`.
- Concurrency limits → `04`. Rate policy → `03`.
- The declared response-size bound, the response arriving with no declared length, and the in-memory read bound that follows from it → `03`.
- The partial file's **name**, and a file the vector names still existing when the child opens it → `05`. The silence about residue → `08`.
- The derivation's own documented claim → `09`. The ignore rules' coverage → `11`.

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` — quoted from `.ai/context/commands.md`. The configured checker is `mypy` in strict mode; another checker present in the dev dependency group is **not** it and must not be substituted.
- **No container. No database. No third-party origin. No service is started — a phase that needs one is misdesigned.** This phase is satisfiable entirely offline. Its real prerequisites:
  1. **A temporary directory** — for every artefact, every synthetic input and every snapshot taken during a run.
  2. **A loopback origin** — a local server on `127.0.0.1:0` serving a synthetic media payload with byte-range support, used wherever a run must be interrupted while work is in flight, and serving a synthetic playlist where a second residue class must be exercised. Nothing leaves the machine.
  3. **The real muxing binary** on `PATH` — used as a tool, never as an origin. It is the only external process this phase drives, and it is driven through the product's own code.
  4. **The platform's access-control listing tool** — the method used wherever a mode cannot be asserted.
  5. **Synthetic values only** — a title, an identifier, a media address. **No real credential is used anywhere and none is obtainable.**
- **All captured output is written to a file.** The declared console encoding raises on third-party text containing box-drawing characters; printing would manufacture a failure that is not the product's.
- **Repository-wide searches exclude every worktree directory.** A stale copy of a previous phase set and stale audit output would otherwise be searched by accident, and a match count taken from them is wrong in the direction that makes this phase look covered.

## 4. Discovery

Map the architecture before checking anything. **Use roles, not names** — never reference a concrete file, module or class name. **A subject that maps to nothing is reported as a gap, and a gap is a finding.**

1. **Artefact map** — every file and directory the process creates, the mode each requests, and the place it is created. Built **before** anything is measured; it is the denominator for block (f).
2. **Name map** — every input that becomes part of a name on disk, the transformation each goes through, and where each transformation is applied and where it is not. Distinguish a value, a file that holds one, and a path that names one.
3. **Path map** — every entry point that accepts or derives a path, the checks each applies, what each validates, and what it validates against. Note the entry points that compose a path and then stop.
4. **Residue map** — every path a download writes to, every path a run removes, and the condition under which each removal is reached. **The four adjacent paths are the column set for block (a)'s matrix and are fixed before any run is driven.**
5. **Working-set map** — every file that exists only while a download runs, the stage that creates it and the stage that removes it. The peak is the sum of the stages that overlap.
6. **Evidence map** — the test tree's reach into these subjects, searched excluding every worktree directory. A subject with no match is declared uncovered **before** it is checked, not after. **Whether each subject is reached at the declared default configuration is recorded here** and is stated on every finding.
7. **Readiness map** — for every method in `## 5`, whether it runs here; for every one that does not, the skip text that will be emitted instead.

*Role vocabulary:* the name sanitiser and the name builder beside it · the path validator and each of its call sites · the directory creator in the output path · the hidden working-directory builder and its staleness check · the single-unit writer and the operation that moves it into place · the working-tree cleanup and every call that reaches it · the batched merge and the final merge · the partial-file existence probe and the partial-file removal · the transports that write the final name and each one's overwrite behaviour · the list reader and the position value it passes down · the log-file creator and the directory it lives in · the temporary-file creators that request a mode · the platform-conditional guards around the suite's permission assertions · the start-up path, and whether it looks for anything.

## 5. Runtime Verification (mandatory)

> **Every method below is local and offline.** No network beyond loopback, no browser, no third-party origin, no container, no service, no credential. Three substitution primitives and only three: the **temporary directory**, the **loopback origin**, and the **real muxing binary** from `PATH`. Four mechanical rules, all binding:
> 1. **The four retention policies are judged as one matrix.** R1 produces a single 4×4 grid of *four adjacent paths × four end conditions*. **No cell is filed on its own**, and the finding is the grid's shape — the inconsistency between adjacent paths — never one cell.
> 2. **A requested mode and a measured mode are two values, always.** A run reporting only the requested one has not answered the question, and under `problems-only` the gap reads as "no finding".
> 3. **No assertion reached through the suite is the proof of anything.** A green result is a state in which a finding was observed, never its evidence. Where the suite is cited, it is cited for what it does *not* cover.
> 4. **A peak is a peak, not an endpoint.** R8 samples continuously; the amplification figure is the maximum, and a figure taken at the end of the run is not a substitute for it.

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | **The retention matrix: four adjacent paths × four end conditions, judged together** | (a) Point the real command at the loopback origin and run it four times, once per end condition: completes; returns non-zero; exhausts its retries; and is **ended without giving the process a chance to clean up** — force the termination and record the mechanism verbatim. (b) Before the first run, enumerate every directory the product writes into and every filename it names during a download, and print the list: it is the column set. (c) Snapshot those directories on a fixed cadence and again after the run returns, recording presence, byte size and measured mode per path. (d) After each run, read the cleanup path that run reached and record **the path it targets** beside **the path that exists**. (e) For each residue class present, test it against every pattern the product's own sweeps, counts and equality tests match, and against the repository's ignore rules; print the per-class verdict. (f) Leave one survivor in place, run the command again normally, and check it before and after. (g) Re-run each condition once to confirm stability and record the run-to-run variance. | The 4×4 matrix with presence/size/mode per cell; the enumeration that defined the columns; the target-versus-existing comparison per run; the per-class pattern verdicts; the before/after survivor check; the stability re-run and its variance. |
| R2 | **Mode: what is requested, what is in force, and what the platform's call can change** | (a) Create each artefact the way the product does — final output, the working directory and each of its file kinds, the merge intermediates, the child's partial, the log file, and the log file's parent directory — and `os.stat` each immediately, recording `st_mode & 0o777` as the **measured** value. Read the **requested** value from the construction site. Two fields per artefact, never merged. (b) Read the declared platform's own documentation of what its mode-setting call changes and record the mapping **as a mapping**. (c) For each artefact **and its parent directory**, capture the access-control listing verbatim, including whether the entry is inherited. (d) Count, by family, every call in the product's source that could restrict access independently of a mode — access-control, security descriptor, ownership change, creation mask — and print the counts. | Per artefact: requested value and measured value as two fields; the platform's documented mapping; the verbatim access listing per artefact and per parent directory with the inheritance state; the per-family control counts. |
| R3 | **Whether the mode guarantee has an oracle that can fail on this platform** | (a) Search the test tree — **excluding every worktree directory** — for every assertion naming a permission mode, and list them by file. (b) For each, **read the assertion body** and record three facts: skipped outright or inline-guarded; whether the assertion sits inside the guard; and whether the body executes on this platform. (c) Run the containing tests with `-v -rs` and record per-test pass/skip — **a sanity check only, explicitly not evidence**, because a guarded body reports success while executing nothing. (d) Then obtain the evidence out of band: run the guarded check yourself, against the artefacts R2 created, with the platform guard out of the equation, and record the value it produced. | The list of oracles; per oracle the guard form, whether the assertion is inside it, and whether the body executed here; the pass/skip counts **labelled non-evidence**; the out-of-band measured value per guarded property. |
| R4 | **The derived name under a hostile string** | (a) Drive the sanitiser and the derivation directly with a fixed case list, recording the returned string and the produced name for each: every character on the code's replacement list; a NUL; a C0 run; a newline; a reserved device name alone; a reserved device name in the derived shape; a trailing dot; a trailing space; a trailing separator; a 300-character component; a title that sanitises to nothing; an empty title. (b) Create each produced name in a temporary directory and read it back. (c) For each failure, record the **exception class**, the exact message and the operation that raised — resolution, directory creation or open. (d) Record the produced name's **length as a number**, and separately the platform's own limit on a path. (e) Record whether the batch-position value reaches the name, and through which branch. (f) Record where the input string comes from, and record explicitly that its real-world content is **not** asserted. | Per case: the sanitiser's return, the produced name, whether it was created, the read-back result, the failure class and site; the length figures; the position-reachability verdict; the origin statement and the non-assertion of content. |
| R5 | **Reserved device names — what this platform actually does** | (a) In a temporary directory, create: a bare device name; a device name with an extension; the derived shape of each; and a control file with an ordinary name. (b) `os.stat` each, record whether it is an ordinary file, and read the control's bytes back to confirm the directory is behaving. (c) Attempt a removal on each and record the outcome. **Record the caveat with the result:** a removal against a path that resolves to a device returns a permission error here for a reason unrelated to the residue, so the removal half is confounded and **only the creation half is evidence.** No claim is made from the removal half in either direction. (d) Read the suffix the current derivation appends and record whether the last component of a produced name can ever equal a bare device name. | Per name: whether it is an ordinary file, its size, the removal outcome; the caveat text; the derivation's suffix and the last-component verdict; the control's read-back. |
| R6 | **What the guard refuses, what it admits, and what it compares against** | (a) Call the validator directly with a fixed list and record, per input, accepted or rejected, the error code, the resolved value and the message text: a double-dot inside an otherwise ordinary component; a directory genuinely named with two dots; a system directory; a root-relative path; a network path; a path at the declared repository root; a path under the source tree. (b) Repeat each call with the diagnostic enabled and with it suppressed, and record which inputs emitted a warning. (c) **Independently** compute, without using the code, the directory the comparison derives from, and compare it with the declared repository root; record both as **two values**. (d) Enumerate every call site, recording for each the value it passes for the diagnostic and the thing it validates — a directory or a whole file. (e) For each call site, record whether the composed path re-enters the validator after the name is appended. (f) Drive the directory-creation call against an existing object of the wrong kind and record what surfaces. (g) Search the source tree for any allow-list, any root comparison that refuses, and any canonicalisation; print the per-family count. | Per input: accept/reject, error code, resolved value, message text; the enabled-versus-suppressed verdicts; the computed base and the declared repository root as two values; the call-site table with both columns; the re-entry verdicts; the creation-failure result; the per-family containment-control counts. |
| R7 | **How one unit lands, and what an interruption between the two steps leaves** | (a) Drive one unit's write through the real code and record the temporary name, the final name, the operation that moves it, and the order of the removal on the write-failure path. (b) `os.stat` the temporary name and the final name and record both modes, before and after the move, as two values. (c) End the process between the write and the move, then enumerate the directory and record every match. (d) Test each match against every pattern the product's own sweeps and counts use, and record the per-class verdict. (e) Read the write site and record whether the unit is streamed or held whole **as a citation for another phase**; record whether the same path carries any size limit, and record the limit that exists elsewhere in the tree with what it actually bounds. | The two names and the move operation; the failure-path removal order; both modes before and after the move; the post-interruption enumeration and its per-class verdicts; the streamed-or-buffered reading, recorded as a citation with its cross-reference. |
| R8 | **Merge amplification, measured, and whether anything bounds it** | (a) Confirm the real muxing binary is on `PATH` and record its path. (b) Generate one synthetic transport-stream segment and copy it to a numbered run inside a real working directory of the shape the product builds. (c) Run the **real** batched merge and, from a separate thread, sample the working directory's total size on a fixed short cadence for the whole run, recording the **maximum** and the instant it occurred. (d) Record the input total and the final artefact's size as two further numbers. (e) List the non-numbered files present in the sample that recorded the peak. (f) Force one batch merge to fail, enumerate the directory afterwards, record what remains, then invoke the product's own staleness check against the surviving directory and record whether it short-circuits. (g) Search the source tree for a size bound, a free-space probe, a volume query and a declared cap on the artefact; print the per-family count and record the one cap that exists with what it bounds. | The binary's path; the sampled series' **peak**; the input total and the artefact size; the two ratios; the non-numbered files at the peak; the post-failure enumeration and the staleness check's verdict; the per-family ceiling counts and the existing cap's actual subject. |
| R9 | **Collision, overwrite, and one path reached twice** | (a) Write one derived path twice in a temporary directory and read the bytes back after each write; record whether the first survives. (b) Drive the list reader twice — the same entry twice, and the same entry at two positions — and record, per entry, the name, the working tree and the partial name it derives. (c) Search the tree for any deduplication, suffix or disambiguation applied to a derived name; print the count. (d) Trace the position value from the list to the point the name is built and record the branch that consumes it. (e) For every transport that can write the final name, read its overwrite behaviour; record per transport, including any that cannot be configured. (f) Record whether the transports sharing one name also share one working tree and one partial name. | The two writes and the read-back; the per-entry name/tree/partial table; the deduplication count; the position trace and consuming branch; the per-transport overwrite verdicts; the shared-path verdicts. |
| R10 | **Baselines, the coverage declaration, and the skip register** | (a) Run the four verification commands from `## 3` over this phase's surface; record exit codes and pass/fail/skip counts and skip reasons. **Do not substitute any other type checker.** (b) Search the test tree — **excluding every worktree directory** — for the name derivation, the path validator, the working-directory builder, the working-tree cleanup, the batched merge, the batch and final merge, the partial-file cleanup and the mode-setting sites; print a match count per symbol. **Every subject with a count of zero is declared uncovered before it is checked.** (c) Record whether each of the phase's subjects is reached at the declared default configuration or only under an explicit opt-in, and state that gate on every finding. (d) Write the platform note and the eight documented skips. | The four exit codes and outputs; the skip reasons; the per-symbol match counts; the reachability statement; the platform note and the skip texts. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how to obtain its evidence is rewritten here, not skipped at execution time.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.**

*Three rules that follow:*
1. **R10's results are never filed as findings.** They are cited as the state in which a finding was observed. The absence of coverage is `10`'s subject.
2. **A method that cannot say how is rewritten, not skipped at execution time.** If a row turns out to be unobtainable on the declared platform, the phase emits a **documented skip with justification** naming the effect, the platform and the reason. Under `problems-only`, **silence reads as "no finding."**
3. **The mode dimension is the one place where the phase's most likely failure is emitting nothing.** Its confidentiality consequence cannot be asserted as written on the declared platform; what the run *does* establish is the measured mode, the effective access-control state, the count of independent confining controls, and the mode of the directory that supplies the real protection. **All four are fileable, and the absence of any of them is the failure.**

> **Platform note (mandatory — this phase touches permissions).** The declared development platform is Windows, and it prevents one thing this phase cannot assert as written: a mode-based permission statement. The platform's mode-setting call maps to the read-only attribute, and the access state in force afterwards is **a different question from the mode that was requested**. Separately, three of the suite's four mode oracles are inline-guarded and report success while executing no assertion body, so a green run here is a statement about the guard, not about the property. Both are handled by measurement where a measurement exists and by documented skip where one does not. **The method chosen is observation of the effective access-control state, paired with `os.stat` — not a blanket skip**, because a silent skip is indistinguishable from a clean result. **The permission guarantee must not ship unaudited on the platform where the work happens.**

**Documented skips — eight. Each names what the run *does* establish, so silence never reads as "no finding".**

1. **Real mode enforcement as a confidentiality control.** *The assertion that only the owner can read an artefact cannot be executed here: the mode-setting call toggles only the read-only attribute, and the mode measured after the call was not owner-only.* **The run does establish:** the requested value, the measured value, the verbatim access listing per artefact, the per-family count of independent confining controls, and the mode of each parent directory — all fileable. The enforcement outcome on a POSIX host is **UNVERIFIED** and is not claimed. **Do not state a severity for a host that was not observed.**
2. **Whether another local principal can read an artefact in practice.** *Requires a second local identity on a POSIX host reading the artefact while a download runs; not obtainable here. **UNVERIFIED.*** **The run does establish:** the verbatim access listing — the effective state, with no second identity needed — combined with R2(d)'s control count. That answers the question as a structural claim about the code, with the platform's own listing as the observed half. **Do not claim a second process read anything.**
3. **Atomicity of the temp-then-move write on a POSIX host.** *What R7 measures is the declared platform's rename behaviour; the POSIX atomic-rename guarantee is a property of that host's filesystem and is not exercised here. **UNVERIFIED on POSIX.*** **The run does establish:** the observed behaviour on the declared platform, and the structural fact that the two steps are separate operations — which is what makes an interruption between them possible at all — together with R7(c)'s measurement of what such an interruption leaves.
4. **Free-space exhaustion behaviour.** *Requires filling a volume. Not performed.* **UNVERIFIED as a behaviour.** **The run does establish:** the absence of any free-space probe, volume query or artefact-size cap, by exhaustive search and per-family count. **Documented skip, justified by that search. Do not assert what error a full volume produces.**
5. **The cascade from a leftover merge batch into a count mismatch and a raised error.** *R8(f) drives a failing batch and enumerates what remains and what the staleness check then does — the first two links.* **UNVERIFIED:** the final link, a subsequent merge attempt. It is filed with the structural fact and an explicit marker, **never with an observed severity.**
6. **What the third-party downloader writes when interrupted in a mode other than the one R1 exercises.** *R1 runs a real child against the loopback origin on the direct-media path; a fragment-resume path writes a different set of intermediate names and was not exercised.* **Either drive a synthetic playlist from the same loopback origin, or mark the second residue class UNVERIFIED. Do not assert it from the tool's documentation.**
7. **Whether a live origin's page metadata ever carries a character the derivation does not replace.** *Requires the real origin. **UNVERIFIED.*** **The run does establish:** the **origin** of the string (recorded) and a **local reproduction** of the failure (observed). The **trigger is not observed.** Block (b) 3 exists to make that prohibition executable: no finding may say an origin supplies such a string.
8. **Whether the two tasks that share one path corrupt each other's files.** *Requires two concurrent real runs against the origin. **UNVERIFIED beyond the shared-path fact.*** **The run does establish:** that two entries derive one name, one working tree and one partial name. The corruption outcome is `03`'s degradation-ladder consequence — cross-referenced, never filed here.

## 6. Audit Dimensions (checks + evidence)

> **The order below is risk order, descending, and it is also the re-entry order** (`## 10`). **(a)** is first because it is the only subject here whose consequence outlives the command. **(f)** is second **for correctness of output, not of consequence** — its consequence is bounded by the directory the operator chose, but it is the only block whose silence would make this phase's own report read as a clean bill of health. **(b)** is third because it is the only block driven by a string the origin supplied and it holds the phase's one hard naming failure. **(c)** is fourth because its own consequences are bounded and partly diagnostic, but it is where a security-labelled error is raised at a legitimate user path. **(d)** and **(e)** are last because neither is a security or a correctness-of-output risk. **Executability does not reorder risk.**

### (a) What Is Left on Disk After the Process Ends

> Enumerate every directory a download writes into and every file it names during a run, then drive the command four times — once per end condition: completes, returns non-zero, exhausts its retries, and is ended without giving the process a chance to clean up. Snapshot the enumerated directories during and after each run and record presence, size and measured mode per path. **Judge the four paths and the four ends together as one matrix; no cell is filed alone and a single policy judged alone is the wrong unit.** Where a run reached a cleanup step, record the path it targets beside the path that exists. **Whether the operator was told is not this block's and is not recorded here.**

| Check | Description | Evidence required |
|---|---|---|
| The four adjacent paths are enumerated before anything is driven | Every directory the product writes a file into, and every file it names during a download, is listed. This list is the denominator for every row below. | R1 |
| One matrix, four ends, four paths | The same harness drives each of the four end conditions and records presence, size and measured mode per path, per run. **No cell is judged on its own.** | R1 |
| A cleanup that targets a name the child never creates | For each run that reached a cleanup step, the path the cleanup targets is compared with the path that exists at that moment. A cleanup that never reaches a survivor is a finding at that cell. | R1 |
| Cleanup reachable only from the success path | Every cleanup call site is located, the condition guarding each is recorded, and the end conditions that bypass it are recorded. A cleanup that can only run on success is a finding, and the ends that bypass it are named. | R1, R10 |
| A removal that can raise where the caller does not expect it | Every removal is read for its failure mode. A removal that raises on an ordinary directory entry, in a place that converts a completed download into an error, is a finding at that cell. | R1 |
| Residue matched by no sweep of its own | For each residue class, the patterns the product's own sweeps, counts and equality tests match are recorded. **A class matched by none is a finding**; whether the repository's own ignore rules match it is recorded as a fact of the evidence. | R1, R10 |
| Whether a later run reclaims it | After a survivor is left, an ordinary second run is executed and the survivor is checked before and after. A survivor no later run touches is a finding. | R1 |
| What is preserved, and the reason given for it | Where residue is kept deliberately, the reason recorded at the site is read and recorded. A deliberate policy is recorded, not assumed; the finding is the **inconsistency between adjacent paths**, never the policy itself. | R1 |

- Evidence: R1, R10

*Internal de-duplication:* (a) 3 files the mismatch between the targeted path and the existing path; (a) 6 files a residue class the product's own mechanisms cannot reconcile. Where the same residue appears in both, (a) 3 is the finding and (a) 6 supplies its reach.

### (f) The Mode Every Artefact Carries, and the Mode In Force

> Enumerate every artefact the product creates — final output, the hidden working directory and everything in it, the merge intermediates, the child's partial, the log file, the log file's parent directory, and each temporary file the code hardens — and record, for each, what the code asks for and what is measured on disk after the call, **as two separate values**. Then capture the effective access-control state of each artefact and of its parent directory, which is the only access question this platform answers.

| Check | Description | Evidence required |
|---|---|---|
| Every artefact enumerated, two values always | For each artefact, the value the code asks for is read from the construction site and the value measured on disk after creation. **Recorded as two fields, never as one.** | R2 |
| The platform's own mapping of its mode-setting call | The platform's documented behaviour for the call the code uses is read and recorded **as a mapping, not as a generalisation about the platform.** | R2 |
| The effective access state, not the mode | The access listing of each artefact and of its parent directory is captured verbatim, including whether the entry is inherited. A mode reading owner-only beside an access listing that does not confine it is a finding, and both are reported. **Do not generalise from one artefact to the platform, and do not generalise from the platform to a host that was not observed.** | R2 |
| Which artefacts request a mode and which do not | A count per class: mode requested, mode not requested, mode requested only on the creation path and not on the update path. | R2 |
| A parent directory that supplies the real protection | For each artefact, the mode of the directory it lives in and the mode used to create that directory. A hardened file in a directory created without a mode is a finding at that cell. | R2 |
| A mode applied by a check-then-act | Each mode-setting site is read for the order of its existence test against its call. A file that can appear between the two is a finding. | R2 |
| A stated reason that does not hold on this platform | Every comment stating **why** a mode was chosen is read and compared with the value measured here. The comparison is the finding; the intent is not, and the wording itself belongs to `09`. | R2 |
| The guarantee has an oracle that can fail on this platform | Every assertion naming a mode is located. For each, record whether it is skipped outright or inline-guarded, and **whether its assertion body executes here.** A guarantee with no oracle that can fail on the declared platform is a finding **about the guarantee**; the guard's *style* is `10`'s and is not filed here. | R3 |
| No oracle's green run is evidence | The suite's result is recorded as **the state in which a finding was observed** and never as its proof. The evidence is obtained out of band, against the artefacts R2 created, with the guard out of the equation. | R3 |

- Evidence: R2, R3

*Internal de-duplication:* (f) 2 records the platform's mapping once. (f) 3 reports the artefact's effective state; it does not restate the mapping and it does not claim the call does nothing.

### (b) The Derived Name — Character Set, Length, Reserved Names

> Drive the derivation with a fixed case list covering every character the code replaces, a NUL, a run of control characters, a newline, a reserved device name alone and in the shape the derivation actually produces, a trailing dot, a trailing space, a trailing separator, an over-length component, and a title that sanitises to nothing. For each, record the string the sanitiser returns, the name the derivation builds from it, and what happens when that name is created and read back.

| Check | Description | Evidence required |
|---|---|---|
| Every replaced character is exercised | Each character on the code's replacement list is driven in and out of a title; the returned string is recorded for each. | R4 |
| Control characters | A NUL, a C0 run and a newline are each driven. For each, record the exception class, whether it is the product's own typed error or an unhandled one, and the operation that raised. **An unhandled failure originating from a string the origin supplied is the finding.** | R4 |
| The input's origin is recorded; its content is not | Where the string comes from is recorded. **Whether the real origin ever supplies such a string is not asserted, and the evidence column says so.** | R4 |
| Reserved device names — the creation half | A bare device name, a device name with an extension, and the derived shape of each, are created; which are ordinary files is recorded. | R5 |
| Reserved device names — the removal probe is confounded | A removal against a path that resolves to a device returns a permission error for an unrelated reason. **The caveat travels with the evidence, and the creation half is the evidence. No claim is made from the removal half in either direction.** | R5 |
| Whether the current derivation can produce a bare device name | The suffix the derivation appends is read and the last component of the produced name is recorded. **If it can never be a bare device name, the finding's scope is the shared utility, filed as a best practice with that scope stated — not as a write failure that occurs today.** No row in this block may carry "a write can land on a device" as a premise; that is what the measurement is for. | R4, R5 |
| Trailing separators and trailing dots | A trailing dot, a trailing space and a trailing separator in the title are each driven; the returned string and the created name are recorded. Same scope rule as the row above. | R4 |
| Truncation scope | An over-length component is driven. What is truncated and what is not are recorded separately, and the length of the produced name is recorded as a number against whatever limit the platform imposes on a path. | R4 |
| The empty-title fallback | A title that sanitises to nothing is driven; the name produced is recorded, and whether a batch position reaches it is recorded separately. | R4, R9 |

- Evidence: R4, R5, R9

*Internal de-duplication:* (b) 6 and (b) 7 share one scope rule. State it once, in (b) 6, and apply it. The derivation's own claim about what it replaces belongs to `09` — this block files the behaviour, cross-references the wording, and files no documentation finding.

### (c) Where the Path Is Allowed to Go, and What the Guard Refuses

> A guard has two independent obligations: it must refuse what should be refused, and it must permit what should be permitted. A guard that only warns is not a second line of defence; a guard built on a substring refuses a directory the user is entitled to name. Drive the validator with a fixed list covering a double-dot inside an otherwise ordinary component, a directory genuinely named with two dots, a system directory, a root-relative path, a network path, a path at the declared repository root, and a path under the source tree. For each, record accept, reject, the error code and the resolved value returned.

| Check | Description | Evidence required |
|---|---|---|
| There is a containment root, or there is not | The tree is read for any allow-list, any root the path must sit under, any refusal. Counts are recorded per family. **The finding is the absence, not the acceptance of any one path.** | R6 |
| A warn-only comparison is recorded as a warn-only comparison | The containment comparison's failure behaviour is recorded. A comparison whose failure branch does not refuse is a diagnostic, and calling it a guard is the finding. | R6 |
| The base the comparison is made against is computed, not assumed | The directory the comparison derives from is computed independently of the code, compared with the declared repository root, and the two recorded as **separate values**. | R6 |
| Which call sites enable the comparison and which suppress it | Every call site is listed with the value it passes and the thing it validates — a directory or a whole file. **Recorded as a set. No consequence is drawn until both this row and the row above are in hand, and neither half is a finding on its own: file one finding when both are in hand.** | R6 |
| The composed path never re-enters the validator | Whether the path is validated before or after the name is appended to it is recorded, per call site. A composed path that is never validated is a finding at that cell. | R6 |
| The guard's own false positives | A legitimate path containing a double-dot substring is driven. Accept or reject, the error code, and **the wording of the error** are recorded. File the rejection and the wording as two facts of one finding; **do not file it as a security control working correctly**, since this row is a substring test and the row above records whether any containment root exists at all. | R6 |
| The guard's reach | A path the platform resolves outside any root the operator chose is driven and its resolved value recorded. **The finding is the missing root, never the one path that was tried.** | R6 |
| Directory creation where the validator's subject is written | Whether the creation is guarded, and what surfaces when it cannot be performed against an existing object of the wrong kind, is recorded. | R6 |

- Evidence: R6

### (d) One Path, Two Writers

> The name the derivation produces is a pure function of a title and an identifier, so two runs — or two entries in one list — reach the same path, and nothing in the product notices. Establish whether anything makes the name unique: the list is read for a uniqueness filter, the batch position is traced to see whether it reaches the name at all, and every transport that can write the final name is read for an overwrite flag. Then write one derived path twice and read it back.

| Check | Description | Evidence required |
|---|---|---|
| Uniqueness, established or denied | The tree is read for any deduplication, suffix or disambiguation applied to the derived name. A count is recorded. Zero matches is a finding. | R9 |
| The batch position reaches the name, or it does not | The position value is traced from the list to the point the name is built, and the branch that consumes it is recorded. A position that reaches only one fallback branch is a finding. | R9 |
| Two writes to one path, observed | One derived path is written twice and the bytes are read back. What happens to the first write without a prompt, a suffix or a warning is the finding. | R9 |
| Every overwrite flag, per transport | Each transport that can write the final name is read for the flag that permits or forbids overwriting. Recorded per transport; a transport that cannot be configured is recorded as such. | R9 |
| Two tasks, one working tree | Whether two list entries deriving one name also derive one hidden working tree and one partial name is recorded. **The sharing of the path is the finding**; what concurrent writers then do to each other's files is recorded, not predicted. | R9 |
| The consequence stops at the shared path | Whether the resulting artefact ends up corrupted is **not this phase's** and is not asserted. Cross-reference the owning phase. | R9 |

- Evidence: R9

### (e) What the Work Costs on Disk While It Runs

> The working set is not the artefact. While a download runs, the input segments, the batched intermediates and the final output can all be on the same volume at the same moment, and the product has no instrument that would notice. Drive the real batched merge over a synthetic transport-stream set with the real muxing binary and sample the directory's total size continuously, recording the **peak**, not the endpoints. Alongside it: how one unit of work lands on disk, and whether an interruption between the two steps of that write is recoverable.

| Check | Description | Evidence required |
|---|---|---|
| The peak, measured | The real merge is run over a synthetic set. The directory total is sampled on a fixed cadence from a separate thread; the peak, the input total and the final artefact's size are recorded as **three numbers**. | R8 |
| The two ratios, reported separately | Peak over final artefact, and peak over input, are two figures and neither substitutes for the other. | R8 |
| What is present at the peak | The non-numbered files present in the sample that recorded the peak are listed. Their names are the evidence that the peak is not the endpoints. | R8 |
| Any ceiling at all | The tree is searched for a size bound, a free-space probe, a volume query and a declared cap on the artefact. Counts are recorded per family, and the one cap that exists is recorded **with what it actually bounds**. | R8 |
| Whether the working set is bounded by anything | The answer is recorded from the counts. **No exhaustion run is performed and none is claimed**; the finding is the absence, and the absence of a control is what the run establishes. | R8 |
| How one unit lands | The write's shape is recorded: the temporary name, the final name, the operation that moves it, and the order of the removal when the write fails. | R7 |
| An interruption between the two steps | The process is ended between the write and the move; the directory is enumerated for whatever is left, and each match is tested against the patterns the product's own sweeps and counts use. | R7 |
| Whether the move preserves the mode | The mode before the move and the mode after it are recorded as two values. | R7, R2 |
| The buffer is a fact, not this block's finding | Whether the unit is streamed or held whole is read and recorded **as a citation**. The bound that follows from it is another phase's, and (e) files nothing about it. | R7 |

- Evidence: R2, R7, R8

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **A file's permission mode, creation mode, atomicity and cleanup** → `07`, **regardless of what the file contains — with the one exception ruled, and mirrored here:** the credential temp file's **permission mode, the access state actually in force, and what that mode means on the declared development platform, are `06`'s, and are the sharpest instance of `07`'s own subject.** **The test:** *would a reader still classify this as a credential finding if the artefact were any other file?* For the credential file **the artefact is the credential** — the finding is about the credential's confidentiality, not about a file — **so `06`.** For the child's invocation file, the log file, the working directory, the partial output and the merge intermediates, the answer is no, and the finding is `07`'s. `06` carries the mirror statement.
- **Residue, and whether a later run reclaims it** → **`06`, ruled by the residue's own nature.** *Is the residue itself the credential?* **Yes → `06`** — its recoverability is that phase's headline question. **No → `07`**, where the question is whether a leftover artefact was cleaned up. The credential file's residue is `06`'s; the working tree's, the partial's and the merge intermediates' are `07`'s.
- **The response** → `03`, **and this phase cites it without re-deriving it.** *The declared response-size bound, the response that arrives with no declared length, and the unbounded in-memory read that ignores the declared bound are `03`'s* — each is a property of the transfer. **This phase owns the disk consequence:** what the working set costs on the volume while the download runs, and the absence of any ceiling on the artefact or on the free space it is written into. The same unbounded read reaches the disk through one non-streaming write; **the write's shape is this phase's, the bound that follows from it is `03`'s, and block (e) records the shape as a citation and files nothing about the bound.**
- **The partial file's name** → `05`, **and the orphan is this phase's.** *The name the child process is told to write follows from what the argument vector contains.* **The orphan that name leaves on the volume is `07`'s, and so is the cleanup that targets it.** One defect, two findings: *the vector does not ask for a different name* is `05`'s; *the residue is never removed* is this phase's — **and it is fileable even when the name is exactly what the vector asked for, because the finding is that the product's own cleanup does not target the path that exists.** Block (a) 3 is a target-versus-existing-path check and files nothing about the name.
- **Residue versus silence** → **two questions, two owners.** *Residue exists and was not cleaned* → **`07`**. *Residue remains and the operator was never told* → **`08`**, whose subject is the diagnostic completeness of failure paths. One file may carry both and one fix may serve both; **this phase files the residue, cross-references `08`, and files no finding about what was or was not reported.** That the residue classes are matched by the repository's own ignore patterns is recorded **as a fact in the evidence of block (a) 6**; the ignore rules' own coverage is `11`'s, and the silence is `08`'s.
- **Reserved device names and trailing separators in a derived name** → **`07`, alone, filed once.** *A name the derivation builds is a defect of derivation; the defect survives moving the file, and it is therefore this phase's rather than a structural one.* **the code's own claim about the derivation** — the docstring or comment stating what it replaces or guarantees — is a **structural description** → `09` by the documentation boundary, and a mismatch between that wording and the behaviour is `09`'s finding, filed there, on the wording. **This phase files the behaviour, cross-references the wording, and files no documentation finding.** **The consequence is bounded by what the current derivation can produce, and the phase measures that bound before filing anything:** a name the derivation cannot currently produce is a property of a shared utility and is filed as a best practice with that scope stated, not as a write failure that occurs today.
- **A collision producing a corrupted artefact** → `03`, **as the invariant that a degraded or shared path must not corrupt the artifact.** This phase files that **one path was reached by two writers**; whether the resulting file is corrupted is `03`'s consequence, cross-referenced and not filed.
- **The merge stage's destruction order** → `03`. This phase owns what the merge stage **costs on the volume** and what it **leaves behind**; the order in which the muxer's inputs and intermediates are destroyed is `03`'s.
- **Launching, feeding or killing a child process** → `05`, including whether the partial file's response-file convention still exists when the child opens it, the kill escalation, and the guarantee that it runs on every exit path. **Whether the child wrote a partial before it was killed is this phase's; whether it was killed correctly is `05`'s.**
- **Cancellation** → `04`. *Whether a cancellation reaches the download, and how it propagates and unwinds* is `04`'s. **What the cancelled run left on the volume is `07`'s**, and that is the fourth column of block (a)'s matrix.
- **Concurrency limits and permit ownership** → `04`. **Whether two tasks reach one path is this phase's** (block (d)); how many tasks may run at once is `04`'s.
- **Rate policy, retry policy and the degradation ladder** → `03`. *When to fall back from one method to another, and why to back off* are `03`'s. This phase owns only what each rung **leaves on disk**.
- **A declared setting field, its bound, and its precedence** → `02`. This phase owns only the **effect** a value has: whether the subjects above are reached at the declared default. **The reachability gate is stated on every finding.**
- **What the process emits** → `08`, including exit-status mapping, the live display, progress reporting and stream discipline. **This phase's only claim inside that output is the residue-versus-silence line above.**
- **Structural arrangement and file-local craft** → `01` and `09` respectively. *A derived name is a filesystem concern and stays here even though a naming convention is file-local craft; the test "does the finding survive moving the file?" answers yes, so it is `07`'s.* **A documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09`; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`. **This phase files no documentation finding.**
- **Whether the test suite proves any of this, and the form its guards take** → `10`; this phase cites match counts and files nothing from them. **The two things this phase does own about the suite are the guarantee and the platform note:** a mode guarantee with **no oracle that can fail on the declared platform** is this phase's finding, because the guarantee is the subject, and the effective access state has to be observed by hand. **A guard's *style* — an inline platform guard versus an explicit skip — is `10`'s.** **Whether a finding from this phase survives validation** → `99`.
- **Repository hygiene and ignore-file coverage** → `11`. The ignore rules match the residue classes this phase finds; that is recorded here as evidence, and the rules' own coverage is `11`'s.
- **Licence posture, terms acknowledgement, notice mechanism** → not an audit subject; inadmissible under `problems-only` and expressly rejected. **Do not file.**

## 8. Edge Cases

- The process is interrupted mid-download, and a truncated file is left **at the final name** — matching a media glob and a media player.
- The process is interrupted mid-download, the child's own partial name survives, and the final name never existed.
- A run exhausts its retries, reaches its partial-file cleanup, and the path it removes is not the path that exists.
- A run that completes still leaves the working tree, and the reason for keeping it is recorded.
- The working tree survives a run that failed, and no later run ever revisits it.
- A leftover merge batch file is matched by the same pattern as a numbered segment, and the next run's count test passes with a segment genuinely missing.
- A unit's temporary file is left between the two steps of its write, and matches no pattern the product's own sweeps use.
- Two entries in one list derive one name, one working tree and one partial name, and run at the same time.
- The same derived path is written twice and the first write is destroyed silently.
- A legitimate directory the user is entitled to name contains a double-dot substring, and the error message says *path traversal*.
- A title carries a NUL, a control-character run or a newline, and the failure surfaces as an unhandled error rather than the product's own typed one.
- A title sanitises to nothing, and the batch position either reaches the name or does not.
- An over-length component is truncated in one place and the path's own length is never bounded.
- A trailing dot, a trailing space or a trailing separator in the title survives into the name.
- A title is a reserved device name, and the derived name — suffix and extension included — is or is not a bare device name.
- The output directory already exists as a file, and the directory creation raises.
- A mode is applied by a check-then-act, and a file created in the window keeps the mode it had.
- A hardened file sits in a directory created without a mode, and the protection is the directory's, not the file's.
- A guard around a mode assertion is inactive on this platform, so the assertion never runs and the test still reports success.
- A guarantee is asserted only by oracles that cannot fail here, and no other control in the tree confines the artefact.
- The volume fills, and the failure surfaces as an error from whichever write happened to be running.
- *(Gap: what a real origin supplies in a title, and what a real child writes when interrupted on a path this phase did not exercise. Observed where possible; otherwise documented. Verify or document — never report as verified.)*

## 9. Severity Taxonomy

The findings template is the authority: `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`.

| Severity | Conditions |
|---|---|
| CRITICAL | A file that outlives the process is indistinguishable from a finished download to a glob, a browser or a player, and no later run reclaims it; or a name derived from a string the origin supplied causes an unhandled failure, so one bad title ends the run with a generic error. |
| HIGH | A cleanup that is reached targets a path that does not exist, so a residue class is never removed on any of the ends it can occur on; a residue class that no sweep in the tree can match or reconcile; one path reached by two concurrent writers, with the first artefact destroyed without a prompt or a warning; the requested mode and the mode in force differ for an artefact and no other control in the tree compensates. |
| MEDIUM | A residue class is left only because its cleanup is reachable solely from the success path; the working set peaks at a multiple of the final artefact with no ceiling above it and no free-space probe anywhere; a guard that refuses a legitimate user path under a security-labelled error; no containment root, so nothing refuses a path outside any directory the operator chose; the truncation bounds a component of a path but not the path. |
| LOW | A mode applied check-then-act; a hardened file in a directory created without a mode; **a name the current derivation cannot produce, filed with that scope stated and with the measured bound recorded**; a stale reason given for a mode that does not hold on the platform where the run happened. |

**Type guidance.** `SPEC-DEVIATION` for behaviour contradicting the project's own declared comment or bound. `RUNTIME-ERROR` for anything observed failing at runtime. `BEST-PRACTICE` for a defensible design with a demonstrated risk — the shared-derivation properties are this case unless a stated dependency is absent. **This phase files no `DOC-UPDATE`** — a documented claim is `09`'s. A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity; **no row of this table may be filled in from an anchor, an ordering, or a predecessor's problem list.** **A residue that is not removed and a residue the user was never told about are two findings, in two phases, and must not be merged into one here.**

## 10. Recommended Sequence

1. Discovery (`## 4`).
2. **R10 first** — the baselines, the reachability gate, the coverage declaration and the skip register. Every later step is observed against it, and the reachability gate must be known before any subject is judged reachable.
3. **R1, then R2, then R3** — the residue matrix, the mode, the oracles. These are the first three things a truncated pass must have covered, and (f)'s output must never be allowed to read as clean by default.
4. **R4, then R5, then R6** — the name, the platform's device-name reality, then the guard.
5. **R9, then R7, then R8** — the collision, the write, the working set. R8 is last by risk and the cheapest row in the table; run it even when the pass is short.
6. Blocks (a), (f), (b), (c), (d), (e) **in the order they are written in `## 6`. Do not reorder by convenience** — the letter order is the risk order.
7. Cross-cutting (`## 7`) and edge cases (`## 8`).
8. Consolidate findings, **re-reading `## 7` before writing each one**.

**Second-pass order.** On a re-run after a thin result, do **not** start again from step 1. Re-enter at the first item below with no recorded evidence and continue downward: **R10 → R1 → R2 → R3 → (a) → (f) → (b) → R4 → R5 → R6 → (c) → R9 → (d) → R7 → R8 → (e)**. R2, R3 and R8 are re-run only if (f) or (e) has no evidence at all, since their harnesses are reusable. A block with partial evidence is resumed; a block with complete evidence is skipped. A re-run that finds no new evidence writes `No problems found in this phase.` and stops.

## 11. Finding Prefix

Use `ART-` for all findings in this phase. `ART-` is unique in the catalogue, shares no first two characters with any other phase prefix (`EN CF NE CO PR SE AR OU QL TS DE VA`), and is obtainable from no other prefix by a single plausible edit. It does not encode the phase number, so renumbering never invalidates a published finding ID.

## 12. Reporting

- Write findings to: `.ai/audit/07-filesystem-artifacts/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row, or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) the **exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
  - **Every finding carries its reachability** — whether its subject is reached at the declared default configuration or only under an explicit opt-in.
  - **A mode finding carries two values or it is not filed:** the mode the code requests and the mode measured on disk, plus the effective access-control state. A finding reporting only the requested mode has not answered the question.
  - **The silence about residue is never filed here.** This phase files that the residue exists; that the operator was never told is `08`'s, and a finding carrying both halves is split.
  - **A cleanup that targets a name is not a naming finding.** The naming of the partial file is `05`'s; what this phase files is that the product's own cleanup does not reach the path that exists.
  - **The four retention policies are one artefact.** No cell of the matrix is filed on its own, and the finding is the inconsistency between adjacent paths.
  - **No row from the verification table is reported as a clean bill of health.** In particular the checks that came back clean produce no row, no note and no finding.
