---
name: 06-credentials-secrets
status: draft
validated: no
executor: auditor
problems-only: true
---

# 06 — Credentials and Secrets

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.
>
> **Binding rule 1 — synthetic tokens, never real ones.** Every value this phase
> captures is generated for the run: a session, a signed address, a file path, a
> header. No real credential is used anywhere in this phase, and none is
> obtainable. This is what makes the evidence plan in `## 5` safe to run, and it
> is why every finding here is a **route**, never an observed live token. A
> sentence claiming that a live credential was seen is inadmissible.
>
> **Binding rule 2 — severities are composed by this phase, never inherited.** The
> analysis that preceded this file carried a problem list with severities and
> ordering attached, and the decision document attached its own adjectives to
> subjects. Neither is citable. Every severity is composed here from this phase's
> own run against `## 9`. An executor who finds a subject already carrying a
> severity has misread this file.
>
> **Binding rule 3 — the headline question has two halves, and the silent one
> never suppresses the other.** *Can another local process read the live session
> while the download runs, and is it gone afterwards?* **The definitional half is
> fully answerable offline**, and what it must establish is three separate facts,
> each produced by its own row: whether any control in the tree confines the
> artefact, whether a child is handed it by path, and what an end the process
> cannot intercept leaves behind. **The empirical half
> requires a second local identity this platform does not provide, and is marked
> UNVERIFIED.** The unavailability of the second half **must never suppress the
> first half's finding**. A finding resting on the definitional half is
> admissible; one resting on the empirical half is not, and says so. Neither
> outcome is a silent skip.
>
> **Binding rule 4 — a check that can report success while asserting nothing is a
> defect of the verification, not a pass.** A platform-guarded assertion whose body
> never runs reports success while proving nothing. A green exit code is therefore
> not evidence of anything; R2 detects this by reading the assertion bodies and
> re-running the check out of band, and (a)4 files the missing guarantee.
>
> **Binding rule 5 — a subject already checked and found correct is absent, not
> annotated: no check row, no verification row, no note, no finding.** **No check is
> manufactured to fill a verbatim in-scope bullet that names one**, and the presence
> of such a bullet in `## 2` is not an instruction.

## 1. Goal

The complete life of borrowed third-party session material and of every other secret-bearing value, from acquisition to destruction, and the control that keeps it out of every sink.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| The credential on disk | The access mode requested, the access state in force, the file's fate on each way the process can end, and what a later run reclaims | A requested mode reported as the effective one; a guard with no oracle that can fail here; residue that *is* the credential and that nothing ever looks for |
| Channels out of this process | Every hand-off to a child and every outbound request, and the exact form a secret takes in each | One transport meeting a stated purpose and a sibling not meeting it; a path disclosed where a value was named; an unmarked carrier |
| Where a secret comes out | Every surface the process can be read on, and every carrier driven to it | A value protected on one route and exposed on another; the same bytes under two policies; a shape no transform can match |
| The written credential | Every field of what is written, and what the installed consumer does with it | An entry the consumer discards; a field written from a constant where the input carried a real one |
| What was taken | The set the browser hands over, every narrowing between there and use, and the reason given | No narrowing at all; a widening of every other zone's blast radius taken as a deliberate trade with no stated dependency |

**In scope:**
- Credential acquisition through browser automation; what is harvested and what is not.
- Serialisation format correctness, field-by-field injection defence (CR/LF stripping across name, value, domain, path), and preservation of the real domain attribute rather than a hardcoded one.
- Temp-file placement and its stated rationale; permission mode applied, and **what that mode actually means on the declared development platform**.
- Every channel by which the credential reaches a child process — the argument vector on one transport, the URL query string on another, a request header on a third.
- Cleanup on success, on failure, and on abrupt termination; whether the material can be recovered after the process exits.
- Redaction of signed URLs and of **child-process output** before it is persisted; redaction of supplied values in validation errors.
- **Completeness of redaction across every sink**: log file, console renderer, live display, terminal, captured child output. A value protected in one channel and exposed in another is a finding here, regardless of which channel.

**Out of scope:** what a credential setting *means* and how it is validated → `02`; the process boundary's argument design → `05` (this phase owns whether a secret appears in it); the rendering mechanics of the terminal → `08` (this phase owns whether a secret appears in what `08` renders); the permission rule, residue and cleanup of every artefact that is not the credential → `07`; signed-address staleness, the forced re-extraction path, the refresh policy and the degradation ladder → `03`; the mechanical facts of a child's capture path → `05`; the browser's release → `04`; a documented claim → `09`.

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` (from `.ai/context/commands.md`). `mypy` (strict) is the configured checker; a second checker present in the dev dependency group is **not** it — do not substitute it.
- **No Docker. No database. No third-party origin. No service is started.** This phase's real prerequisites:
  1. **Synthetic values only** (preamble rule 1) — a generated session, a generated signed address, a generated file path. **No real credential is used anywhere, and none is obtainable.**
  2. **A temporary directory** — for the artefacts, for everything the methods record, and for a controlled environment.
  3. **The installed third-party downloader**, imported as a library, used **as the consumer** the product hands its file to. Not an origin; not contacted over a network.
  4. **A stub origin** — a local server serving a synthetic playlist that stalls mid-transfer, used only where a run must be interrupted while work is in flight. If it cannot be built, R4 falls back to its documented skip; the method is never silently dropped.
  5. **A stand-in for the browser handle, context and page** — used only where a real object would require a real origin.
- **All captured output is written to a file.** The declared console encoding raises on third-party text containing box-drawing characters; printing would manufacture a failure that is not the product's.
- No product dependency is launched and no origin is contacted.

## 4. Discovery

Map the architecture before checking anything. **Use roles, not names.** Never reference a concrete file, module or class name in this file. **A subject that maps to nothing is reported as a gap — that is a finding.**

1. **Secret map** — every value a third party would not want written down, where each originates, how long each lives, and every place each is materialised. Distinguish a value from a file that holds one and from a path that names one.
2. **Route map** — every hand-off to another process and every outbound request, and the exact form a secret takes in each, including the in-process carriers between steps.
3. **Sink map** — every surface the process can be read on, and every place a value becomes text. This list is the denominator for block (c) and is built **before** anything is driven to it.
4. **Lifetime map** — every way the process can end, which of them the code can intercept, and per artefact whether it is removed, by what mechanism, and in what order relative to the child that reads it.
5. **Evidence map** — the test tree's reach into these subjects, searched **excluding every worktree directory**, whose stale copy will otherwise be searched by accident. A subject with no match is declared uncovered **before** it is checked. **The reachability of the credential subjects at the declared default configuration is recorded here** and is stated on every finding.
6. **Readiness map** — for every method in `## 5`, whether it runs here, and for every one that does not, the skip text that will be emitted instead.

*Role vocabulary: the browser-session harvest point · the store serialiser and the format writer · the temporary-artefact creator and its cleanup · the command-vector builder for each transport · the invocation-file writer · the outbound request path that sets header fields · the object that carries the session value between steps · the child-output echo · the batch-summary writer · the text and address transforms · the log handler and renderer pair · the exception-text writer · the input predicate that admits a supplied value · the start-up path, and whether it looks for anything.*

## 5. Runtime Verification (mandatory)

> **The evidence regime, stated once.** Every method below is local and offline. **No network, no browser, no third-party origin, no Docker, no service.** The one substitution primitive is a **stub origin** that stalls mid-transfer, used only where a run must be interrupted while work is in flight.
>
> **Three mechanical rules, all binding:**
> 1. **Synthetic tokens, never real ones** (preamble rule 1). The finding is the **route**; a live token is never claimed, and the evidence column says the value was generated for the run.
> 2. **The requested mode and the measured mode are recorded as two values, always.** A run reporting only the requested one has not answered the question, and the report reads "no finding" from silence.
> 3. **No assertion reached through the suite is the proof of anything** (preamble rule 4). A green result is a state in which a finding was observed, never its evidence. A guarded body reports success while executing nothing, so the bodies are read and the check re-run out of band. Where the suite is cited, it is cited for what it does *not* cover.

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | The on-disk guard: what is requested, what is in force, what else could confine it | (a) Create the credential artefact the way the product does, then `os.stat` it immediately and record `st_mode & 0o777` — the **measured** value — beside the **requested** one, read from the call site; repeat for every artefact that requests a mode. (b) Read the platform's own documentation of what its mode-setting call can change; record the mapping. (c) Search `src/` for every call that could restrict access independently of a mode — access-control, security descriptor, ownership, creation mask — and print a count per family. (d) Record the access state of the directory the artefact was placed in, as measured on this machine. | The requested value; the measured value per artefact as a distinct field; the platform's documented mapping; the per-family call counts; the directory's measured access state. |
| R2 | Whether the mode has an oracle that can fail **on this platform** | (a) Search the test tree for every assertion naming that mode; list them by file. (b) For each, **read the assertion body** and record two facts: skipped outright or wrapped in a platform guard, and whether the assertion lies inside that guard. (c) Run the containing file and record pass/skip counts — **labelled non-evidence**, because a guarded body reports success while executing nothing. (d) Then obtain the evidence out of band: run the guarded check yourself against the artefact R1 created, with the platform guard out of the equation, and record the value it produced. | The list of oracles; per oracle the guard form and whether its body executed; the pass/skip counts **labelled non-evidence**; the out-of-band measured value. |
| R3 | The artefact's fate on every end the process can intercept | (a) Drive each of: a completed run, a non-zero return, an exception raised before any child is started, and a cancellation through the real call; immediately after the call returns record whether the artefact exists, and record the child's own status. (b) Drive the path where writing the artefact itself fails; record which error surfaces and whether the artefact was removed. (c) After one ordinary completed run, read the artefact back and record its absence and the exact path the child was given, **as two separate facts**. | Per end: existence after the call and the child's status; the surfaced error and the removal outcome on the write-failure path; the read-back result and the path handed to the child. |
| R4 | The artefact's fate after an end it cannot intercept, and whether any later run notices | (a) Point the real command at the stub origin, begin a transfer, and end the process without giving it a chance to run cleanup; record the exact mechanism used. (b) Immediately enumerate the directory for the artefact's own name pattern and record every match with its **measured** mode (R1's method, reused). (c) Read each match back and record whether it contains what it was created to contain. (d) Search `src/` for any exit hook, any handler for the forcible-termination case, and any start-up enumeration of that name pattern; print a count per family. (e) Run the command a second time normally and record whether the first run's residue is touched at all. | The end mechanism used; every residue match with its measured mode; the content read-back per residue; the three per-family call counts; whether a second run touched the first run's residue. |
| R5 | Every channel a secret travels in, and every stated purpose it is measured against | (a) Build each child command vector directly with a synthetic media address and a synthetic credential-file path; capture both verbatim; for each record the exact element a secret occupies. (b) Capture the media address as placed inside the invocation file, verbatim. (c) Enumerate every outbound request path; for each record the header fields and object fields that can hold a session value, and whether the carrier declares itself sensitive. (d) Search `src/` for every comment or declared intent claiming a value is kept out of a process table, a command line or a log; for each, list every transport carrying the same value and record which meet the claim. | Both vectors verbatim; the occupied element per transport; the invocation file's content verbatim; the header and object field list with sensitive-marking status per carrier; each declared intent with its per-transport verdict. |
| R6 | The sink matrix: every carrier, every surface, and the comparison between surfaces | (a) Before driving anything, enumerate the surfaces: each log destination and renderer, the live display, standard output, standard error, each in-memory buffer that becomes text, each exception-text site, each object that renders. Print the list and use it as the denominator. (b) Fix the corpus — a signed media address with a token, a filesystem path in this platform's shape, a bare session pair, a whole header value, **and the refreshed form of each** — and drive each to each surface, capturing the bytes arriving. (c) In one run make the same carrier reach two surfaces and diff the two captures. (d) Per surface record whether it applies a transform; where it does not, record whether whatever produced its input did. (e) Pass each corpus shape through every transform reachable at the surfaces and record, per shape, whether the output differs from the input. (f) For every predicate that admits a supplied value into the pipeline, record whether it matches the value whole or only a part of it, and drive it with a value carrying a token in a part it matches. | The surface list; a per-carrier × per-surface grid of what arrived; the two-surface diffs; per surface the transform status and the producer's status; per shape the transform output; per predicate the whole-or-part verdict and the driving result. |
| R7 | Objects that carry a secret: how they render, and whether they are marked | (a) Construct each such object with a synthetic session value and capture every form it renders in. (b) Per object, record **from the declaration** whether the field declares itself sensitive or excludes itself from rendering. (c) Search `src/` for every call that would write, log, interpolate or format such an object into any sink; print a count per object. (d) Compare the count with R6(a)'s surface list. | Every rendered form verbatim; the sensitive-marking status per field; the per-object call count; the comparison against R6's surface list. |
| R8 | Exception text as a carrier | (a) Search `src/` for every site writing a caught exception's own text into any sink; print a count and the file list. (b) Per site, record whether anything is applied to that text first. (c) Attempt once to provoke a message carrying a request address and record verbatim what was obtained; **if nothing is obtained that is a documented skip, not a pass.** | The per-site list and count; per site the transform status; the verbatim provoked message, or the skip text. |
| R9 | The written file, read back by the real consumer | (a) Drive the serialiser with a synthetic session; write its output to a temporary file. (b) **Load that file with the installed third-party parser itself** — the same library the product hands the file to — and record every entry it kept, every entry it discarded, and its own diagnostics verbatim. (c) Repeat with no expiry, a future expiry and a past expiry; record which of the three survives. (d) Compare every field of every written line with the corresponding input attribute; record each field written from a constant. (e) Place a control-character pair in the name, the value, the domain and the path in turn; record the line count and field count for each. (f) Drive every input shape the serialiser accepts; record the output, and any shape no caller can produce as unreachable. (g) List every other component that reads a file of this kind and record whether it uses the same parser. (h) Locate the path by which a value is obtained again after rejection and record whether it returns through this serialiser. | The file content verbatim; the consumer's kept/discarded entries and diagnostics; the three-expiry comparison; the per-field input-vs-output diff; the four control-character results; the per-input-shape output and reachability; the other readers; the refresh path. |
| R10 | What is taken from the browser, and what is not | (a) Read the harvest call and record what it returns and whether anything filters it there. (b) Drive the serialiser with a synthetic set of distinguishable elements and record which reach the written file. (c) For each place the set is next used, record whether every element arrives. (d) Read and record verbatim every stated reason for carrying the whole set, and whether the uses that need it are identified. (e) Search the package for any narrowing symbol — an allowlist, a name filter, a domain filter, a minimum-necessary step — and print the count. | What the harvest returns; the per-element arrival at the written file; the per-consumer arrival; every stated reason verbatim; the narrowing-symbol count. |
| R11 | Baselines, the reachability gate, the coverage declaration, and the skip register | (a) Run the four verification commands from `## 3. Prerequisites` over this phase's surface; record exit codes, pass/fail/skip counts and skip reasons. **Do not substitute any other type checker.** (b) Record the **reachability gate**: whether the credential subjects exist at the declared default configuration or only under an explicit opt-in, and state that gate on every finding in (a)–(e). (c) Search the test tree — **excluding every worktree directory**, whose stale copy would otherwise be searched by accident — for the serialiser, the temp-file creator, the child-output echo, the text transform, the sink writers, the batch-summary writer and the session-carrying object; print a match count per symbol. Every subject with a count of zero is declared uncovered **before** it is checked. (d) Write the platform note and the eight documented skips below. | The four exit codes and outputs; the skip reasons; the reachability statement; the per-symbol match counts; the platform note and the skip texts. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how to obtain its evidence is rewritten here, not skipped at execution time. A `Method` of "inspect the implementation" is not admissible in this phase — every method must produce its evidence by running something.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.**

**Three rules that follow, all required:**

1. **R11's results are never filed as findings.** They are cited as the state in which a finding was observed. The absence of coverage is another phase's subject.
2. **A method that cannot say how is rewritten, not skipped at execution time.** If a row turns out to be unobtainable on the declared platform, the phase emits a **documented skip with justification** naming the effect, the platform and the reason. Under `problems-only`, silence reads as "no finding".
3. **The headline question has two halves and only one is answerable here** (preamble rule 3). The definitional half is fully answerable offline and its finding is admissible. The empirical half requires a second local identity, is marked **UNVERIFIED**, and **must not suppress the definitional half's finding**.

> **Platform note (mandatory — this phase touches permissions).** The declared development platform is Windows. Two things it prevents are load-bearing here and neither may be converted into "no finding": a mode-based permission assertion cannot be executed as phrased, because the platform's mode-setting call maps only the read-only bit and the effective access state after the call is a different question from the mode requested; and no readable third-party process command line is published for an observer. Both are handled below — by measurement where a measurement exists, by a documented skip where it does not. **The permission guarantee must not ship unaudited on the platform where the work happens.** This is an evidence-method note, not a filed finding.

1. **Real permission enforcement.** *The assertion that only the owner can read the artefact cannot be executed on the declared platform: its mode-setting call toggles only the read-only attribute, and the access state measured after the call is not owner-only.* The structural fact is **verified** by R1 — the code requests a mode, the measured value is recorded, and no other confining control exists in the tree. **The enforcement outcome on a POSIX host is UNVERIFIED and is not claimed; do not state a severity for a host that was not observed.** What is fileable: the requested mode, the measured mode, the count of confining controls, the measured access state of the directory that supplies the real protection, and the exact consequence.
2. **Whether another local process can actually read the artefact during a live transfer.** *Requires a second local identity on a POSIX host reading the artefact while a transfer is in flight. Not obtainable on the declared platform. **UNVERIFIED.*** The offline substitute is R1 + R4 together: the absence of any confining control, and the enumerated residue with its measured mode. That answers the question as a **structural claim about the code**, with the platform measurement as the observed half.
3. **Abrupt-termination residue.** *Executable if the stub origin can be built: R4 drives a real transfer and ends the process while work is in flight. If the stub cannot be built, the skip is:* "requires a stalling local origin; **UNVERIFIED**. The structural fact — no exit hook, no handler for the forcible-termination case, no start-up enumeration of the artefact's own name pattern — is verified by exhaustive search and is sufficient to establish the absence of a control." **Never silently omitted.**
4. **Whether a real child or the real muxer prints a signed address or the credential path.** *Requires a live origin. **UNVERIFIED** — the internal behaviour of a third-party tool is out of scope by design.* What is fileable: the **unredacted emission route**, verified by code read and by R6's captured bytes, plus the transform's inability to match a path. **Do not assert which token appears in real output, and do not assign a severity that depends on it.**
5. **Whether an exception message can embed a request address.** *Attempted once during analysis; no such message was obtained. **UNVERIFIED.*** R8 then reports the **class** — raw exception text entering the log layer at N sites with nothing applied to it — with the consequence limited to what is provable, never to a specific token.
6. **Whether the real muxer's own cookie reader accepts the serialiser's expiry value.** *Requires a real muxer's run against a signed address. **UNVERIFIED.*** R9 exercises the other consumer and records its verdict; the muxer's half is marked as not exercised and is **not** inferred from the other consumer's.
7. **Browser-side acquisition, and the contents of a real store.** *The browser context's cookie access is stubbed throughout the suite and no real origin is ever visited. The unfiltered-harvest structural fact is verified by code read; the contents of a real store are UNVERIFIED and out of scope. **Never claim which cookies the origin sets, or how many are taken.*** (e)5 makes that prohibition executable.
8. **Process-table exposure as an observer would see it.** *The declared platform publishes no readable command line for a third-party observer. The disclosure is read from the construction site and from the vector the product builds, which is the same string the platform would publish. The portable half — that the credential's path is an element of the vector — is the finding; the consequence on a POSIX host is a clearly-labelled projection, not an observation.*

## 6. Audit Dimensions (checks + evidence)

The five blocks are ordered by risk, **descending**. The letter order **is** the re-entry order (`## 10`): a pass cut short returns the blocks it reached. **Executability does not reorder risk** — (d) is the most provable subject in the phase and is still fourth, because a truncated pass must return the high-risk blocks.

### (a) The On-Disk Credential — Guard, Access, and Afterlife

> A borrowed session is written to a file so a foreign tool can read it. Ask three questions in order. **What is asked for** — the access mode the code requests, and the stated reason for choosing that directory. **What is in force** — the effective access state measured on the machine that will run this, and whether any control anywhere in the tree would confine it. **What is left** — the file's fate on each way the process can end, and whether a later run ever looks for what an earlier one left behind. Report the requested mode and the measured mode as two separate values, always.

| Check | Description | Evidence required |
|---|---|---|
| The stated reason for the placement is tested where the work happens | The recorded reason for putting the credential outside the output directory is compared with the access state of that directory as measured here. A reason that holds only on another platform is a finding | R1 |
| The requested mode is never reported as the effective mode | The mode the code asks for and the mode measured on the artefact after the call are captured and reported as two values. **Report both; do not collapse them, and do not generalise either one into a claim about the platform** | R1 |
| No second control confines it | The tree is searched, counts recorded, for every call that could restrict access independently of that mode — an access-control call, a restrictive creation mask, a security descriptor, an ownership change. Zero matches beside a measured state that is not owner-only is a finding | R1, R11 |
| The guard has an oracle that can actually fail | Every assertion about that mode is located; for each, record whether it is skipped outright or wrapped in a platform guard and **whether its assertion body executes here**. A guard with no oracle that can fail on the declared platform is a finding about the guarantee; the style of the guard is another phase's | R2 |
| Every end the process can intercept removes it | Success, a non-zero result, an exception raised before the child is started, and cancellation are each driven; after each, the artefact's presence is checked and the child's own lifetime compared against it. A survivor on any of them is a finding | R3 |
| An end it cannot intercept leaves a credential, and nothing notices | The process is ended without a chance to run cleanup and the directory is enumerated afterwards; the tree is searched, counts recorded, for any exit hook, any handler for the forcible-termination case, and any start-up enumeration of the artefact's own name pattern. **The finding is the enumerated absence of a control plus the observed survivor: do not name a token in it, do not claim a session was live, and do not claim a second process read it** | R4 |
| The removal ordering is the one the platform needs | Where the descriptor is closed relative to the removal is recorded, including the path where the write itself fails. An ordering that leaves an open handle, or removes a file the child still needs, is a finding | R3 |
| "Removed" and "the child could open it" are two claims | After a run that completed normally, the artefact's absence is confirmed and the path the child was given is recorded separately, so the two are not merged | R3 |

- Evidence: R1, R2, R3, R4, R11.

*Internal de-duplication rule: a survivor on an interceptable end is (a)5; (a)6 covers only the end the process cannot intercept and files the absence of any later notice. Where two blocks cite the same run, it is cited by its id once.*

### (b) The Channels That Carry a Secret Into a Child

> One secret, several ways out. List every place this process hands work to another process and every place it makes an outbound request; for each, record the exact form a secret takes — an argument element, a query string, a header field, a path a transport names. Then read every stated purpose anywhere in the codebase that claims a value is kept out of a place a third party can see, and check it against **every** transport carrying that same value. **A path is not a secret; a file that holds one is.** Report both facts wherever both apply.

| Check | Description | Evidence required |
|---|---|---|
| Every transport is enumerated before any is judged | Each hand-off to a child and each outbound request is listed with the form a secret would take in it. This list is the denominator for the rows below | R5 |
| The form is recorded as it is built | For each transport, the exact element, substring or field a secret occupies is captured from the construction site, not inferred from the result | R5 |
| A stated purpose is checked against every transport, not the one it names | Each declared intent to keep a value out of a process table, a command line or a log is read; **read both sides before calling it a contradiction — if the sibling's rationale is only implied, the finding is the omission, not the contradiction.** One transport meeting the intent and a sibling not meeting it is a finding | R5 |
| A named path is reported as a path, and what it opens is reported separately | For each transport that names a file by path, record what the process table would disclose **and** what a reader of that path could obtain. **Both facts belong to one finding; the path is not the credential, and the disclosure of the path is not filed at the severity of a disclosure of what the path opens** | R5, R1 |
| The in-process carriers are identified and marked | Every request header, and every field of every object carried between steps, that can hold a session value is listed; whether the carrier declares itself sensitive is recorded. An unmarked carrier is a finding | R5, R7 |
| The carrier is compared with the transports beside it | The session value's in-process form is compared with the same value's form on every child transport, and any difference in whether it is treated as sensitive is recorded | R5 |

- Evidence: R1, R5, R7, R11.

### (c) Where a Secret Can Come Out, Sink by Sink

> Exhaustion, not inspection. Fix a corpus of synthetic secrets in the shapes this system actually carries — a signed media address, a filesystem path in this platform's shape, a bare session pair, a whole header value — and drive each one to **every** place this process can be read: each log destination, each renderer, the live display, standard output, standard error, any buffer held in memory, any exception text, any object that renders. Two things are recorded per cell: whether the secret survives, and whether the same bytes were treated identically everywhere. **A value protected on one route and exposed on another is a finding, whichever route you found it on.** Include the refreshed form of every value, not only the first one.

| Check | Description | Evidence required |
|---|---|---|
| Every output surface is enumerated before any is tested | Each place the process can be read is listed, and each place a value becomes text is listed. Nothing is tested until the list exists | R6 |
| Each carrier is driven to each surface | Every corpus secret is driven down every transport to every surface on the list; the bytes arriving at each are captured. **Every value is synthetic: the finding is the route, and the evidence column says the value was generated for the run** | R6 |
| One value, one treatment | The same secret is made to reach two surfaces in one run and the captures are diffed. Identical input treated differently is a finding **on its own**, filed whether or not either side leaked — a policy that is merely inconsistent and a policy that leaks are two findings and are not merged. **Write the escalation mechanism, not the inference**: the admission predicate that lets a token-bearing value reach that output, and what it matches (a substring rather than an anchor admits a value carrying a token anywhere in it) | R6 |
| A surface protected only by what produced its input is recorded as such | Per surface, record whether it applies a transform; if not, record whether whatever produced its input did. **Which streams that surface reads, whether it invokes a transform, and whether it uses the result are another phase's facts — cite them, do not re-derive them, and file nothing about the missing call** | R6 |
| A shape no available transform can match is filed against the secret that takes it | For each shape in the corpus, record whether anything reachable at the surface can match it, using the transform's own behaviour on that exact shape. **File it against the credential that takes the shape, in this phase; do not restate the transform's coverage as this phase's finding** | R6 |
| A value the operator supplied is a carrier like any other | Every predicate that admits a supplied value into the pipeline is recorded, and for each whether it matches the value whole or only a part of it. A predicate that admits a value carrying a secret admits it whole | R6 |
| Exception text is a carrier | Every site that writes a caught exception's own text is listed with whether anything is applied to it. **The class is the finding; a specific token in a specific message is not claimed** | R8 |
| An object that carries a secret renders, and is unmarked | For each such object, its rendered forms are captured and whether the carrier declares itself sensitive is recorded. Whether any present call site writes it is recorded as a separate fact | R7 |

- Evidence: R6, R7, R8, R11.

### (d) What the File the Consumer Opens Actually Contains

> The credential is only as good as its serialisation, and the consumer is a third party with its own parser. Write the file for a synthetic session and read it back **with the installed consumer itself** — not with a reading of the format. Then check every field against what the producer actually reported: does a value that means "no expiry" mean that to the consumer; is the real scope of each entry preserved or replaced by a fixed one; can any field of any input introduce a line of its own.

| Check | Description | Evidence required |
|---|---|---|
| The written file is read back by the real consumer | The serialiser is driven with a synthetic session; the file it produces is loaded with the installed third-party parser itself. Every entry kept and every entry discarded is recorded, with what the parser said about each | R9 |
| The field that decides whether an entry lives is compared both ways | A session value with **no** expiry, one with a future expiry and one already past are each written and each read back; which of the three the consumer keeps is recorded. **An entry the consumer discards is the finding — the executable facts are the written line, the consumer's own warning, and the entry's absence from what it loaded. Do not write that the tool runs unauthenticated or that the download fails; neither was observed and both need a live origin** | R9 |
| A field the producer supplied is not replaced by a fixed one | Every field of the written line is compared with the corresponding input attribute. A field written from a constant where the input carried a real value is a finding | R9 |
| No input field can introduce a record of its own | A control-character pair is placed in the name, the value, the domain and the path in turn; the result is checked for one line per input and an unchanged field count. An extra line, or a changed field count, is a finding | R9 |
| Every input shape is covered, and reachability is recorded | The serialiser is driven through every input shape it accepts, and the output recorded for each. **A shape no caller can produce is recorded as unreachable and routed to `## 8` — it is not filed as a live defect** | R9 |
| A refresh re-enters this path | Where a value is obtained again after being rejected, whether it is passed back through this serialiser is recorded. A refreshed value that skips it is a finding; one that re-enters it inherits every row above | R9, R11 |

- Evidence: R9, R11.

### (e) What Is Taken From the Browser, and What Is Not

> The set that gets harvested is a decision, and a decision can be wrong without any line being wrong. Find the point where the browser's whole store is taken, list every narrowing that exists between that point and the places the set is next used, and record the reason given for each. Then ask the only question that decides the finding: **is the set the smallest one the task needs?** A deliberate over-collection with a stated reason is a judgement to be recorded, not a defect to be assumed.

| Check | Description | Evidence required |
|---|---|---|
| Every narrowing between harvest and use is enumerated | Each point where the set is reduced, and the reason given for it, is listed. Zero narrowings is a finding | R10 |
| The whole set is carried, not a subset, to each consumer | For each place the set is next used, whether every element arrives is recorded, and which use depends on the whole set | R10 |
| The harvest point admits the entire browser store | What the harvest call returns, and whether anything filters it at that point, is recorded | R10 |
| The stated reason is weighed against the widening | The reason given for carrying the whole set is read and recorded; whether the uses that actually need it are identified is recorded separately. An unstated dependency is the finding | R10 |
| The contents of a real store are not claimed | **This is a prohibition, not a check.** Only the absence of a narrowing is a finding here; the set's real composition is another system's behaviour. No sentence in this phase names a cookie the origin sets or counts the cookies taken | R10 |

- Evidence: R10, R11.

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **A file's permission mode, creation mode, atomicity, residue and cleanup** → `07`, **with the one exception this phase owns, ruled:** the credential temp file's **permission mode, the access state actually in force, and what that mode means on the declared development platform**, are `06`'s, and are the sharpest instance of this phase's own subject. **The test:** *would a reader still classify this as a credential finding if the artefact were any other file?* For the credential file **the artefact is the credential** — the finding is about the credential's confidentiality, not about a file — **so `06`.** For the child's invocation file, the log file, the segment directory, partial output and merge batches, the answer is no, and the finding is `07`'s. `07` carries the mirror statement in the same words.
- **Orphan residue, and whether a later run reclaims it** → **`06`, ruled by the residue's own nature.** **The test:** *is the residue itself the credential?* **Yes → `06`** — its recoverability is this phase's headline question and the reason it is dangerous. **No → `07`**, where the question is whether a leftover artefact was cleaned up at all. The question is not "does a sweep exist" but "**is what survives a credential, and can anything else reach it**".
- **The signed media address: `03` owns the address, `06` owns the token inside it.** *Staleness detection, the forced re-extraction path, the refresh policy and the degradation ladder → `03`.* **Whether the token inside that address is protected in every sink, and whether it survives in captured child output → `06`. Neither phase files the other's half.** A refreshed token is a credential again — re-serialised by the same code, landing in the same sinks — and that second fact is `06`'s and is invisible from inside `03`. Redaction applied *inside* the request path remains `03`'s.
- **Whether a secret-bearing value can reach a sink → `06`, always, and never re-assigned.** *The question is this phase's; the facts it rests on are cited, not re-derived.* **`05` owns only the mechanical facts of its own capture path** — which streams it reads, whether it invokes a transform on each, and whether it uses the transform's return value. **A capture path that reads a stream and applies no transform is `05`'s fact; a live session value reaching a log because of it is this phase's finding, filed once, here, with the fact cited.** This phase files the value's escape and **files no missing call**.
- **The argument vector's design and the invocation convention** → `05`, including whether the invocation file still exists when the child opens it. **The split, stated so one sentence of consequence is not filed twice: the child surviving an exception is `05`'s; the credential file being removed while that surviving child still needs it is `06`'s.** Cross-reference; do not merge.
- **The browser: everything before the resource is in use** — launch arguments, identity parameters, injected-script delivery, response interception, environment inheritance by the driver and its descendants → `05`. **Everything after it is in use: teardown and release → `04`.** This phase files only what leaves the browser: the set that was taken, and whether anything narrowed it.
- **The retrieval policy — why to back off, how long, against which origin, and the effective request rate** → `03`. **The connection-pool ceiling and the literal that overrides a configured ceiling → `04`.** This phase owns the credential only as it appears inside those paths.
- **What a declared credential setting means, what values it may take, how it is sourced, its precedence, and whether a supplied value reaches it** → `02` — including the fact that the environment-file route to it cannot take effect, which is `02`'s dead-configuration subject. **Cite it in one clause; do not file it and do not build a check on it.** This phase owns only the **effect** the value has: whether the subjects here exist at all under the declared default. **The reachability gate is stated on every finding here.**
- **Exit codes, TTY arbitration, the live display, progress rendering, renderer selection, stream discipline, and the rule that suppresses a child's output when a display is active** → `08`. **This phase owns one question inside that output: whether a secret appears in what `08` renders.** The rendering mechanics are never this phase's.
- **A file's placement, naming, containment and write atomicity for every artefact that is not the credential; title-to-filename derivation; the segment directory's staleness signature; merge-stage amplification** → `07`.
- **A documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09`; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`. **This phase files no `DOC-UPDATE`.** Three claims are already known to contradict the code and each is `09`'s wording, not this phase's finding: the child-output transform's own docstring claims a protection it does not deliver; the mode-setting call's justifying comment reasons from a creation mask; the credential file's placement comment claims a risk reduction that holds on another platform only. **Each behaviour is filed here once, behaviourally; each wording is `09`'s.**
- **Repository hygiene and ignore-file coverage** → `11`. **The question is `11`'s, and this phase asks it rather than answering it:** whether a repository-carried ignore rule names every path that can hold secret material, and whether any such rule's negation re-admits a real file. This phase records the credential artefact among the candidate paths and files nothing about the answer.
- **Structural arrangement** — import graph, layer direction, cycles, facades, bootstrap order → `01`. **File-local craft** — typing, naming, module size, a literal duplicated within one file → `09`.
- **Whether the test suite proves any of this, and the form its guards take** → `10`; this phase cites match counts and files nothing from them. **The one thing this phase does file about the suite is the guarantee:** a permission guarantee with no oracle that can fail on the declared platform is this phase's finding, because the guarantee is the subject. **A guard's *style* — an inline platform guard versus an explicit skip — is `10`'s.** **Whether a finding from this phase survives validation** → `99`.
- **Licence posture, terms acknowledgement, notice mechanism** → not an audit subject; inadmissible under `problems-only` and expressly rejected. Do not file.

## 8. Edge Cases

- The process is hard-killed, or loses power, mid-download; the credential file is still on disk and the next run never looks for it.
- The credential file is created, the write fails, and the descriptor is still open when the removal is attempted.
- The child is still running when the credential file is removed, on a path the code believes has already ended.
- Two tasks each create their own credential file in the same shared temporary directory and each removes only its own. *(Whether the interleaving is correct is another phase's; whether a credential is affected is this phase's.)*
- The credential file is created in a directory whose access state is not the one the code's stated reason assumes.
- A guard around the mode assertion is inactive on this platform, so the assertion never runs and the test still reports success.
- The serialiser receives a value that means "no expiry" and writes a number the consumer reads as invalid.
- The serialiser receives an input shape no caller can produce.
- A control-character pair appears in the name, the value, the domain, or the path.
- The signed address is obtained a second time after rejection and is passed back through the same serialiser.
- The same value reaches the log and the terminal inside one run, and the two differ.
- A child's non-progress line is written to one stream with nothing applied to it, while the same accumulated buffer is transformed before it is logged.
- A value the operator supplied carries a token in a part of it that the admission predicate matches.
- An exception's own text carries a request address, or is recorded as a class because the address could not be provoked.
- A log destination renders an object that carries the session value, and nothing marks that object as sensitive.
- The credential subjects are unreachable at the declared default configuration, so a checked route is never taken in an ordinary run.
- (Gap: what a real origin, a real child process or the real muxer prints, sets, or accepts. Observed where possible; otherwise documented. Verify or document — never report as verified.)

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are **not** redefined here.

| Severity | Conditions |
|---|---|
| CRITICAL | The credential survives the process on a path the product takes, and no control confines it; or a live session value is written to a surface the operator did not choose, untransformed, on a route the product takes. |
| HIGH | A value protected on one surface and exposed on another inside a single run; a value disclosed to anything that can observe a process, for a window the product controls; the requested access mode and the access state in force differ, and nothing else in the tree compensates; a third-party consumer discards the entry the product wrote, so the written credential does not contain the credential. |
| MEDIUM | A credential carrier that is not marked as sensitive; a route that exists with no transform at the surface, where the input was transformed by its producer by luck rather than by contract; a guard with no oracle that can fail on the declared platform; the same bytes treated differently at two surfaces where neither side leaked. |
| LOW | A field written from a constant where the input carried a real value, with no observed consequence; a deliberate over-collection with no stated dependency; an input shape no caller can produce; a removal ordering that leaves an open handle, where no leak was observed. |

**Type guidance.** `SPEC-DEVIATION` for behaviour contradicting the project's own declared setting, bound or comment. `RUNTIME-ERROR` for anything observed failing at runtime. `BEST-PRACTICE` for a defensible design with a demonstrated risk — the over-collection dimension is this case unless a stated dependency is absent. **This phase files no `DOC-UPDATE`** — a documented claim is `09`'s.

**These conditions are a classification vocabulary, not a verdict.** A finding's severity is composed by this phase from its own run; no severity carried by any preceding document, and none written beside a subject in advance, is inherited. A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an observed severity. **A policy that is merely inconsistent is filed separately from a policy that leaks; one finding must not be written to carry both.**

## 10. Recommended Sequence

1. Discovery (`## 4`).
2. R11 first — the baselines, the reachability gate, the coverage declaration and the skip register. Every later step is observed against it, and the reachability gate must be known before any subject is judged reachable.
3. R9, then R1, R2, R3, R4 — the written file and the on-disk guarantee are the two subjects whose findings are fully provable here, and the first things a truncated pass must have covered.
4. R5, then R6, R7, R8 — the routes, then the sinks, then the carriers, then the exception class.
5. R10 last.
6. Blocks (a) through (e) in the order they are written in `## 6`. **Do not reorder by convenience, and do not reorder by how easy a subject is to prove.**
7. Cross-cutting (`## 7`) and edge cases (`## 8`).
8. Consolidate findings, re-reading `## 7` before writing each one.

**Second-pass order.** If this phase is re-run after a thin result, do **not** start again from step 1. Re-enter at the first item below for which no evidence was recorded, and continue downward: **R11 → R9 → R1 → R2 → R3 → R4 → (a) → R5 → (b) → R6 → R7 → R8 → (c) → (d) → R10 → (e)**. R1 and R9 are re-run only if (a) or (d) has no evidence at all, since their harnesses are reused. A block with partial evidence is resumed; a block with complete evidence is skipped. A re-run that finds no new evidence writes `No problems found in this phase.` and stops.

## 11. Finding Prefix

Use `SEC-` for all findings in this phase. `SEC-` is unique in the catalogue: it shares no first two characters with any other phase prefix (`EN CF NE CO PR SE AR OU QL TS DE VA` are all distinct), and it is obtainable from no other prefix by a single plausible edit — the failure mode that produced two near-identical prefixes elsewhere in this catalogue. It does not encode the phase number, so renumbering never invalidates a published finding ID.

## 12. Reporting

- Write findings to: `.ai/audit/06-credentials-secrets/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) **the exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
  - **Every finding carries its reachability** — whether its subject exists at the declared default configuration or only under an explicit opt-in.
  - **Every finding is a route, not a token.** No finding claims that a live credential was observed, because none was. Synthetic values are used throughout and that is stated, not implied.
  - **The unavailability of the empirical half of the headline question never suppresses the definitional half's finding** (preamble rule 3).
  - **A policy that is inconsistent is filed separately from a policy that leaks.** They are different severities and one finding must not be written to carry both.
  - **No row from the verification table is reported as a clean bill of health**, and no subject already checked is given a row, a note or a finding.
