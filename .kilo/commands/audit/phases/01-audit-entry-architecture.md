---
name: 01-entry-architecture
status: draft
validated: no
executor: auditor
problems-only: true
---

# 01 — Entry Points & Module Architecture

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.

## 1. Goal

Whether the one-shot process starts, wires and unwinds in the correct order, and whether module dependencies flow in one direction.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| Command layer | Parse arguments, build the configuration object, configure logging, delegate, map the result to an outcome. | Work below the command; divergent preambles; framework imported in a service. |
| Pre-delegation bootstrap | Environment scan, configuration construction, log-sink setup — the work done before the first service call. | Emission before the sink exists; a failure path that masks its own cause. |
| Service layer | The work each command delegates to. | A service producing user output or deciding the process outcome. |
| Cross-layer infrastructure | Integration adapters the service layer calls. | An adapter importing upward into the service layer. |
| Utility and model packages | Shared helpers and data shapes used by every layer. | Eager re-export roots; module-scope state with an unbounded lifetime. |
| Package roots | What executes when any submodule of a package is first imported. | A root that republishes a subpackage and makes a cycle load-bearing. |

**In scope:**
- Bootstrap ordering across both commands, including pre-construction environment scanning and log setup.
- Import-time side effects and module-level mutable state.
- Layer and dependency direction; the existence, form, and justification of deferred imports — distinguishing load-bearing cycle breaks from unjustified deferrals; type-checking-only blocks are not in this check; eager package-level imports that make a cycle load-bearing.
- Entry-layer thinness: a service module importing the presentation framework and deciding the process outcome.
- Re-export facade discipline: a module re-exporting private symbols from siblings it does not own.
- Generation, binding and clearing of the correlation identifier across both nesting levels.

**Out of scope:** the *meaning* of an exit code → `08`; the *derivation* of shutdown state from a signal → `04`; the permission mode of any file → `07`; file-local craft conformance → `09`; option design and precedence → `08`.

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` (from `.ai/context/commands.md`).
- **No Docker. No database. No service must be started.** Every verification runs offline against the installed package.
- The declared development platform is Windows; see the platform note in §5.
- `mypy` (strict) is the configured type checker. `basedpyright` is in the dev dependency group and is **not** the configured checker — do not substitute it.

## 4. Discovery

Map the architecture before checking anything. **Use roles, not names.** Never reference a concrete file, module, or class name.

1. **Command discovery** — Locate every command the process exposes and the service entry point each delegates to. Record, per command, the exact ordered list of steps that run before that first delegation; mark where the commands agree and where they diverge.
2. **Layer map** — Read the project's own declared layering. Build the module-level import graph of the source tree and tag each module with its layer.
3. **Deferral inventory** — List every import placed inside a function or a type-checking block, with the deferring function and the target's own module-level imports.
4. **Module-scope inventory** — List every module-scope binding, its type, and the operation it serves.
5. **Surface inventory** — List every declared re-export and every command path, with the production and test consumer count of each.

*Role vocabulary:* the single-download command entrypoint · the batch command entrypoint · the pre-construction environment scan · the log-sink setup step · the service-graph facade module · the cross-layer integration adapter · the utility package root · the correlation-identifier helper · the interrupt-registration helper · the presentation framework · the live display · the command declaration module.

## 5. Runtime Verification (mandatory)

**Run before evaluating any dimension.**

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | Import graph, cycles, layer direction, import-time effects | (a) `uv run python -c "import vkdownloader"` and `uv run python -c "import vkdownloader.cli"` — record success or the full traceback. (b) **Cycle-causation experiment:** a `uv run python -` script that replaces each eager package root in `sys.modules` with an empty module carrying the correct `__path__`, re-imports the module holding the offending edge, and records whether the failure disappears. (c) `uv run python -X importtime -c "import vkdownloader.cli"` — record module count and total import time. (d) An AST pass over the source tree emitting module-level import edges tagged with each module's layer; read the edge list for upward edges. (e) The same pass restricted to function and type-checking blocks, printing each deferring function's target and the target's own module-level imports. | Tracebacks before and after the neutralisation experiment; the edge list and its upward-edge subset; the deferral inventory; module count and import time. |
| R2 | Bootstrap order, sink configuration, failure safety | (a) With a log file configured and a deliberately misspelled prefixed environment variable present, run **each** command once; capture the terminal stream and the log file **separately**; diff the two record sets — records present on the terminal and absent from the log file are ordering evidence. (b) Force a preamble failure for **each** command (a value outside a declared bound, or a log path that cannot be created) and record the exception type, the exception's own message, and the exit status. (c) Instrument nothing: re-read each command's preamble and record the step order and the point at which its failure handler begins. | Terminal-vs-file record diff per command; exception type and status per forced failure; the two step orders side by side. |
| R3 | Static-check baseline | `uv run ruff check src tests`; `uv run ruff format --check src tests`; `uv run mypy src`. Run all three; record exit codes and full output. **Do not substitute `basedpyright`.** | Three exit codes and the output of each. |
| R4 | Suite baseline | `uv run pytest -q -rs`; record passed / failed / skipped counts and the reason string for every skip. | Pass/fail/skip counts and skip reasons. |
| R5 | Module-scope bindings and import-time derivation | An AST pass listing every module-scope binding (mutable containers, sentinel caches, context variables, and any binding whose value is obtained by reflecting over a declared schema). For each, `uv run python -c "import <module>; print(<name>, type(<name>))"` to record its value and type after a cold import. Separately search the tree for the same literal or attribute access reached by a second, independent mechanism. | The binding inventory with values; the search results showing each value's second derivation, or an explicit "no second derivation found". |
| R6 | Facade consumer counts and entry-layer surface | (a) For every name in a re-export list, count import sites **split by production source vs test source**; report both counts. (b) List the command declaration module's imports and mark each public or private against the exporting module's own declared surface. (c) Search the tree for imports of the presentation framework outside the entry layer, and for any function below the entry layer that returns a value the entry layer then raises as an exit status. | Per-name production/test consumer counts; the marked import list; the located framework import sites and status-returning functions. |
| R7 | Correlation-identifier lifecycle | A `uv run python -c` harness that, through the public helpers only: binds an identifier, binds an unrelated context key, calls the clear helper, and prints the resulting context after each step; then repeats the sequence nested three deep, printing the enclosing identifier after the innermost clear. | The printed context after each step; the surviving identifiers at each nesting depth. |
| R8 | Platform note — interrupt registration placement and reachability | The declared platform is Windows. State the non-Unix method explicitly: a two-line probe that obtains a running loop and calls the loop-level signal registration for both handled signals, printing the exception type raised. This phase records only **which layer** registers and deregisters and whether deregistration is reached on the same path. | The probe's output; a documented-skip line for any effect that cannot be executed here. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how to obtain its evidence is rewritten here, not skipped at execution time. Every method above runs offline with no service started.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.**

*Baselines, not findings:* R3 and R4 are the state the rest is observed against. Under `problems-only` their own results are never filed as findings; they are cited only as the state in which an R1/R2/R5/R6/R7 finding was observed.

**Platform note (mandatory — this phase touches signal registration):** on the declared Windows development platform, effects that cannot be executed must be emitted as a **documented skip with justification — never silence**; a silent skip reads under `problems-only` as "no finding". This note is scoped to *placement and reachability* only: which layer registers and deregisters interrupt handling, and whether the deregistration path is reached. The **fallback mechanism, the shutdown event, its cross-loop visibility, and the context-copy workaround are `04`'s** — this phase must not file them, and must not restate their severity.

## 6. Audit Dimensions (checks + evidence)

### (a) Bootstrap Order, Failure Safety, and Sink Configuration

> Both commands must reach their first delegation through the same ordered preamble. Look at what emits before the emitter is configured, where the two commands diverge before delegating, and whether each command's failure handler is safe to run after any preamble step has failed. Record the exact order — the order is the evidence.

| Check | Description | Evidence required |
|---|---|---|
| Preamble order parity | Both commands perform the same preamble steps in the same order, and neither does service work before completing them. | R2 |
| Output only through a configured sink | No preamble step emits before the sink that emission is meant to reach exists; a record routed around the configured logging chain is a finding here. | R2 |
| Failure handler bootstrap-safe | Every command's catch-all can execute after *any* preamble step fails, without referencing state the failure prevented from existing, and still reports the original cause rather than a secondary one. | R2 |
| One construction on the configured path | The configuration object built in the preamble is the one handed to the service; a later implicit reconstruction is a second, unsignalled read of the same environment. | R2, R5 |
| Handler registration on the same path | Both commands register and deregister interrupt handling at the same point in their bootstrap; one doing it in the command layer and the other inside a service module is a finding here. | R1, R2 |

- Evidence: R1, R2, R5

### (b) Import-Time Effects and Module-Level State

> Everything created when a module is first imported, before any command line runs. Look for work done at import rather than on call, values derived by reflecting over another module's declared schema, state whose lifetime exceeds the operation it serves, and deferrals that exist for a stated reason — a justified deferral is correct and must not be filed. Eager *loading* cost is not a defect on its own; eager *effect* is.

| Check | Description | Evidence required |
|---|---|---|
| No side effect at import | Importing any module performs no network, filesystem, or process work. | R1 |
| No schema reflection at import | No constant is derived by reading another module's declared fields at import time. | R5 |
| One derivation per value | A value derived from a single declared source is not also hardcoded by a second mechanism elsewhere. | R5 |
| Module-scope lifetime | Every module-scope binding is cleared at the end of the operation it serves, or its staleness window is bounded and stated. | R5 |
| Justified deferral recognised | A deliberately deferred construction that exists for a stated reason is correct. File it only if the stated reason is absent or has lapsed. | R1 |
| Heavy integration library loaded unconditionally | A third-party integration library is loaded at module scope by a module every command path imports, whether or not the run reaches it. | R1 |

- Evidence: R1, R5

### (c) Layer Direction and Cycle Avoidance

> Does every module import only downward through the declared layers? Enumerate the module-level import edges and name every edge that crosses a layer in the wrong direction. A package root that eagerly republishes its subpackage's contents can make a cycle load-bearing even when no individual edge looks wrong. Where the project's own written layering *permits* a direction, following it is not a deviation.

| Check | Description | Evidence required |
|---|---|---|
| Downward-only imports | No module imports a layer above itself. | R1 |
| Declared layering honoured | Every cross-layer edge the code takes is permitted by the project's own declared layering; a declared-but-unpermitted direction is the finding. | R1 |
| Cycle breaker named and load-bearing | Every cross-layer cycle names the import that breaks it, and that import is genuinely required to break it. | R1 |
| Package roots do not manufacture cycles | A package root that eagerly re-exports from its subpackage does not force an import order that creates a cycle a module would not otherwise have. | R1 |

- Evidence: R1

### (d) Deferred-Import Justification

> Every import placed inside a function is a deferral and needs a reason. Classify each one: a break of a cycle that would otherwise occur, a defence against a cycle that does not currently exist, or a deferral with no cycle behind it. Type-checking-only blocks are not deferrals and are outside this check. Filing a justified break and missing an unjustified one are both failures here.

| Check | Description | Evidence required |
|---|---|---|
| Load-bearing break | The deferral prevents an import-time failure that occurs without it. | R1 |
| Defensive break of a latent cycle | No import-time cycle exists today; the deferral guards one that would form under a plausible reordering. Acceptable; file only if the guard is now unreachable in the other direction. | R1 |
| Unjustified deferral | No cycle exists that the deferral could break; the stated reason names one that is not present. | R1 |

- Evidence: R1

### (e) Entry-Layer Thinness and Outcome Ownership

> A command's job ends when it hands off. Ask whether anything below the command layer reaches back up to the presentation framework or to user input, formats user-facing text, or decides the process outcome, and whether the work it performs is reachable without going through the command at all. Returning a user-visible string or a status to the caller instead of producing it is the signal to look for.

| Check | Description | Evidence required |
|---|---|---|
| No presentation framework below the entry layer | Only the command layer imports the CLI/terminal framework. | R6 |
| No user-facing formatting below the entry layer | Text intended for the user is produced by the command layer, not formatted inside a service. | R6 |
| Process outcome decided below the entry layer | No service returns or dictates the process exit status. | R6 |
| Reachable only through the command | The behaviour a command is supposed to own cannot be triggered by a path that bypasses it. | R6 |

- Evidence: R6

### (f) Re-Export Facade Discipline

> A module that republishes names it does not own turns its import sites into a second public API. For each re-export, count who imports it and from which layer; a re-export whose only consumers are the tests that would be rewritten alongside it is a self-validating loop. Check the list itself for entries that are duplicated, missing, or inconsistent about which of a pair of related names is published.

| Check | Description | Evidence required |
|---|---|---|
| Production consumers | Each re-exported name has at least one consumer in production code, or the re-export is removed. | R6 |
| Test-only consumers | A re-export consumed only by the test suite validates the facade and is validated by it. | R6 |
| Export-list hygiene | No name appears twice; a registered name and its cleanup counterpart are published together or not at all. | R6 |
| Private names not published | A package root or facade does not republish names its own declaring module treats as private. | R6 |

- Evidence: R6

### (g) Correlation-Identifier Lifecycle

> One identifier per logical operation: bound before the first record is emitted, inherited by nested work, and cleared without disturbing anything else. Trace the binds and clears through every nesting level the process creates, and ask of each clear whether it removes what its name says it removes. Where the identifier is also passed explicitly as a log field, treat that as evidence that the bound value does not survive on its own.

| Check | Description | Evidence required |
|---|---|---|
| Generate once per operation | One identifier per logical operation; not regenerated per nested step, not shared between concurrent operations. | R7 |
| Bound before first emission | The identifier is bound before any record the operation produces is emitted. | R7 |
| Inherited by nested work | A nested operation inherits the enclosing identifier instead of shadowing it with a different one that later records cannot be joined to. | R7 |
| Clear removes only what it names | A clear helper removes the identifier it names and nothing else bound in the same context. | R7 |
| Clear at the right depth | An inner operation's clear does not remove the enclosing operation's identifier. | R7 |

- Evidence: R7

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **Exit-code meaning and its derivation from an outcome → `08`.** This phase owns only that the command *reaches* the point where a code is chosen.
- **Option design, precedence, and overrides that bypass re-validation → `08`** (the user-visible outcome) and `02` (the validity, bounds, and sourcing of the setting). This phase owns only *how many times* and *where* the configuration object is built, and whether a build happens outside the configured preamble.
- **Shutdown state derived from a signal, the signal's own delivery, the event it sets, and whether that event is visible outside the run loop → `04`.** This phase owns only *which layer* registers and deregisters, and whether deregistration is reached when an earlier step fails.
- **Correlation identifier:** generation, binding, inheritance and clearing → **this phase**. Creation, ownership and cross-loop visibility of the shutdown event → `04`. Rendering and sink of both → `08`.
- **Permission mode, creation mode, atomicity, and cleanup of any file → `07`**, regardless of what the file contains. **The credential file's content and redaction → `06`; the credential file's permission mode and the platform reality of that mode → `06`.** (By R-A a file's mode is `07`'s; `06` owns the credential's mode and its content.)
- **Whether a secret or signed value appears in anything emitted → `06`.** Whether one appears in a child process's argument vector → `06`; the vector's design is `05`'s.
- **The runtime lifetime of credential material → `06`.** The *meaning* of a credential setting → `02`.
- **File-local craft** — typing, naming, module size, duplication inside one file, and the accuracy of an individual module's or function's own docstring → `09`. Test: does the finding survive moving the file? If yes, it is this phase's, not `09`'s.
- **A documented claim** → the phase owning the code it describes: a **settings-model claim** → `02`; a **structural description** → `09`; a **command-line contract claim** → `08`. A document describing the audit pipeline itself → `99`.
- **A declared setting field → `02`.** A dependency declaration in the build manifest → `11`.
- **Dead configuration** — a declared setting field that nothing consumes, **and** a documented-as-active runtime component that nothing wires into the flow → `02`. The documentation claims describing such a component as active → `09`. `99` arbitrates if both report the same object. **This phase files neither.**
- **Launching, feeding, or killing a child process; the browser driver → `05`.**
- **Whether the same concurrency primitive is acquired more than once on one path, and its runtime consequence → `04`.** Re-acquisition across nesting levels that changes the meaning of an operation's own return → `04`. This phase must not file it and must not restate its severity.
- **What the operator is shown** — terminal streams, live display, progress, renderer selection, log records and their content → `08`. This phase owns only that the bound identifier is generated, bound, inherited, and cleared.
- **What lands on disk and survives the process → `07`.** The rate and backoff policy of the transfer → `03`. Concurrency limits and their effect → `04`.
- **Whether the test suite proves any of the above → `10`.** Whether a *finding* from this phase survives validation → `99`.

## 8. Edge Cases

- A log sink is configured and a record is emitted before it exists.
- A failure occurs in the preamble, before the failure handler's own state exists.
- A failure occurs in the preamble of the *other* command, whose handler is written differently.
- An interrupt is delivered during the preamble rather than during the work.
- The configuration object is built implicitly a second time, after the preamble, and the two disagree.
- A constructor's own documentation promises a shared global configuration object that the wiring does not provide.
- An import-time derived constant survives a change to the thing it was derived from.
- A justified deferral later becomes a real cycle after an unrelated import is added.
- A re-export gains a production consumer, and the facade's own justification is now stale.
- An inner operation's clear removes the enclosing operation's identifier; records emitted afterwards carry none.
- A caller relies on a clear helper preserving context it bound for its own use.
- Both commands are run concurrently in one working directory; module-scope state is process-wide but the working directory is not.

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`.

| Severity | Conditions |
|---|---|
| CRITICAL | The process cannot start, cannot report why it failed, or corrupts an artifact before the operator sees anything. |
| HIGH | The process runs, but what it emits is unattributable, unobservable in the configured sink, or wrong in a way that survives to the end of the run. |
| MEDIUM | Structure that is wrong but currently masked: a latent cycle, module state whose lifetime exceeds its operation, a facade only the tests consume. |
| LOW | Naming-level or cosmetic deviations with no runtime consequence. |

**Type guidance:** `SPEC-DEVIATION` for a structure that contradicts the project's own declared rule; `BEST-PRACTICE` for a structure that is defensible but risky; `RUNTIME-ERROR` for anything observed failing at runtime. **This phase does not file `DOC-UPDATE`** — a document claim belongs to `09` (or `02` for the example environment file). A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.

## 10. Recommended Sequence

1. Discovery (§4).
2. Runtime verification (§5) — R3 and R4 first, as the baseline the rest is observed against.
3. Per-dimension checks (§6), (a) through (g).
4. Cross-cutting (§7) and edge cases (§8).
5. Consolidate findings, re-reading §7 before writing each one.

## 11. Finding Prefix

Use `ENT-` for all findings in this phase. `ENT-` is unique in the catalogue and shares no first two characters with any other phase prefix.

## 12. Reporting

- Write findings to: `.ai/audit/01-entry-architecture/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row, or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) the **exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
