---
name: 02-config
status: draft
validated: no
executor: auditor
problems-only: true
---

# 02 — Configuration

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health.

## 1. Goal

Whether every declared setting is typed, bounded, sourced correctly, and reaches its consumer unmodified.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| Settings model | Field types, defaults, declared ranges, the accepted variable prefix, unknown-key policy, value concealment in errors | A setting accepted in a form it cannot use; an error echoing a rejected value; a validator that raises outside the validation path |
| Environment resolution | Where the environment file is found, which sources exist, which one wins, whether the pre-flight reader and the consuming parser agree | Silent fallback to defaults; two readers disagreeing about the same file; a documented source that never wins |
| Configuration to consumer | Every setting's read sites, the values arriving at them, and the paths that change a value after it is declared | A value substituted for a supplied one; an override admitted outside the declared range; a setting no consumer reads |
| Example artifact and settings documents | The committed template and the documents repeating its claims, validated against the live model | A line that fails validation when uncommented; a value named as legal that the type does not accept; two documents contradicting each other |

**In scope:**
- The settings field model, environment-variable prefix, unknown-key rejection, and secret-hiding on validation errors.
- Every validator and numeric bound, and the interaction of bounds with the values a user can actually supply.
- Environment-file resolution semantics, including its dependence on the working directory.
- Pre-construction unknown-variable scanning and the validation-error rendering path.
- Configuration→consumer propagation, including command-line overrides that bypass re-validation.
- **Dead configuration:** a declared setting — or a declared *source* for a setting — that no user-supplied value can reach, including a field nothing consumes and a component documented as active that nothing wires into the flow.
- The example environment file as a **validated artifact** — bound compliance, complete option lists, and claims about which values are implemented; and every document claim checkable against the live settings model.

**Out of scope:** the runtime lifetime of credential material → `06`; the *effect* of a concurrency bound → `04`; the permission mode of a file a setting names → `07`; exit-code derivation → `08`; dependency declarations in the build manifest → `11`; the composition of a timeout budget → `03`; the command-line option contract → `08`; secret scanning and ignore-file coverage → `11`; structural documentation claims → `09`; the internal failure behaviour of third-party downloader and browser-driver libraries — out of scope by design, so state it rather than guess.

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` (from `.ai/context/commands.md`).
- **No Docker. No database. No service must be started.** Every verification runs offline against the installed package.
- A writable temporary directory for fixture environment files, and the ability to invoke the process's own command-line entry point.
- Assume no populated environment file exists in the working tree: create every fixture in the temporary directory. Do not rely on the working tree.
- `mypy` (strict) is the configured type checker. A second checker present in the dev dependency group is **not** the configured one — do not substitute it.
- The declared development platform is Windows; see R-S1.

## 4. Discovery

Map the configuration surface before checking anything. **Use roles, not names.** Never reference a concrete file, module, or class name.

1. **Settings-model discovery** — Locate the settings model. Record every declared field with its type, default, declared range, any enum membership, and every validator attached to it, with the stage at which each runs.
2. **Source discovery** — Enumerate every source the model reads configuration from, in the order it resolves them, and the order the model's own documentation claims.
3. **Pre-construction discovery** — Locate the diagnostic step that runs before the configuration object is built, the entry points that invoke it, and the validation-failure rendering path.
4. **Post-declaration discovery** — Find every path that can change a setting's value after the object is constructed, and record whether that path re-validates.
5. **Consumer discovery** — For every declared field, record every read of it and its location, split by production source and test source.
6. **Artifact discovery** — Locate the committed example configuration file and every document whose subject is the settings model or its variable mapping.

*Role vocabulary:* the settings model · the environment-file reader used before construction · the consuming configuration parser · the pre-construction unknown-variable scan · the validation-error renderer · the command declaration layer · the post-construction settings copy · the committed example configuration file · the settings guide · the command reference.

## 5. Runtime Verification (mandatory)

**Run before evaluating any dimension.**

| ID | Verification | Method | Evidence to capture |
|---|---|---|---|
| R1 | Declared-setting inventory and consumer trace | In one `uv run python -c` session, introspect the settings model and print every declared field with its type, default, declared range, enum membership and declared metadata (accepted prefix, unknown-key policy, error value-hiding). Then record every read of each field's attribute, by search over the source tree, and split the count by production source vs test source. | Per field: type, default, range, enum members. Per field: the read-site list with production/test counts, and any field with an empty list. |
| R2 | Unknown-key handling and error value concealment | Create a temporary directory containing an environment file with one unrecognised prefixed key; construct the model with that directory as the working directory and capture the raised error and its rendered form. Repeat with the same key in the process environment only. Then construct from a Python caller with a non-text value for an enum-typed field and for a range-typed field, recording the exception type. | Exception class and error-type code for each of the four cases; the exact rendered line for each, stating whether the supplied value appears. |
| R3 | Bound enforcement matrix | In one `uv run python -c` session, loop over every numerically bounded field and construct at floor−1, floor, ceiling, ceiling+1 and the declared default, recording accept or reject and the message. Separately assert each declared default lies inside its own range. | The accept/reject matrix, one row per field per value; the default-inside-range result. |
| R4 | Declared range against the constants the consumer substitutes | For every bounded field, record every read site and the literal constants composed alongside the value, in the consumer's own unit. Where a value can be assembled without contacting an origin, assemble it at the range's floor by calling the same composition with a stubbed transport and print the assembled result. | Per field: declared range, the substituted literals, the assembled value at the floor, and any end of the range the consumer cannot express. |
| R5 | Environment-file resolution and per-source reachability | Create a temporary directory containing an environment file that sets **every** declared field to a value distinguishable from its default. Construct the model three times: (a) with that directory as the working directory; (b) with an empty directory as the working directory; (c) with the same values in the process environment and the file absent. Diff the resulting field values against the file, per field, for every run. Then repeat construction **through the process's own command-line entry point** with the same file present, capturing the process's own report of which file it read. | The per-field diff naming every field whose value in any run does not match the source that was set, tagged with the source and the run; the working directory of each run; the entry point's reported file path. **Judge reachability per source, not per field: a field that a consumer reads is not evidence that its sources work.** |
| R6 | Override paths that skip re-validation | Construct the model, then apply the post-construction override the way production code applies it, with values below the floor, above the ceiling and of the wrong type; read the field back from the resulting live object. Then confirm each admitted value reaches the downstream consumer by substituting a recording stub at the consumer's read site. | The override read-back matrix; the values the consumer recorded for each admitted override. |
| R7 | Pre-flight scanner against the consuming parser | Build fixture environment files, one assignment form each: plain assignment; assignment preceded by an export keyword; assignment with a trailing inline comment; assignment with a quoted value; assignment with a shell-style variable reference; assignment padded with whitespace. For each, record the keys and values the pre-flight scanner reports against the keys and values the model actually consumes, then construct the model to see whether it fails. | A two-column table per fixture — scanner key/value vs. consumed key/value — with mismatches marked, and the construction outcome for each. |
| R8 | Diagnostic emission, ordering and suggestion quality | Run the process's own entry point with a fixture environment file containing an unrecognised key; capture the standard output and standard error streams separately and the log artifact if one is configured. Then repeat for a set of plausible misspellings of real names, one file per misspelling. | The rendered message per misspelling and whether the suggested name is one the user could have meant; the interleaved stream transcript showing where the diagnostic appears relative to other output; the first records of the log artifact for format comparison. |
| R9 | The example artifact and the settings documents against the live model | Extract every assignment line from the committed example configuration file and from every document whose subject is the settings model. Uncomment each in isolation into a fixture file and construct the model per line, recording accept or reject. Diff the option-name set both ways against the model's declared fields. Enumerate every value the artifacts present as legal and check each against the declared type. | Per-line accept/reject for the example file and each document; the two-way name diff; the list of values named as legal that the declared type does not accept. |
| R10 | Static checks over the configuration surface | `uv run ruff check <settings module and its declared consumers>`; `uv run ruff format --check <same>`; `uv run mypy <same>`. Use exactly these; no other checker is configured. | Exit code and full output for each of the three. |
| R11 | Existing test coverage of the configuration surface | `uv run pytest <the configuration test file>`. Then read the test names and map the behaviours they exercise against blocks (a)–(g), recording which check in each block has no test exercising it. | Pass/fail counts; the behaviours covered; the block checks with no covering test. |
| R-S1 | **Documented skip — the effective access mode of a file the settings cause to be created.** The settings create a log file and set an access mode on it. On the declared development platform an access mode is set but not enforced, so the mode cannot be observed. | **SKIPPED with justification:** the declared development platform does not enforce the mode, so no observation distinguishes a correct mode from a wrong one. Recorded as a skip, never as a clean result. | The platform statement, and the acknowledgement that whether the mode is correct belongs to the filesystem-artifacts phase. |
| R-S2 | **Documented skip — the effect of a range value that only manifests against a live third-party origin.** R4 assembles the value without contacting the origin. Whether a substituted or admitted value degrades a real transfer cannot be observed here. | **SKIPPED with justification:** obtaining it requires the live third-party origin, which this phase must not require. R4's value assembly is the substitute. | For any finding depending on it, the structural fact and an explicit `UNVERIFIED` marker — **never** an observed severity. |

**The `Method` column is mandatory and must name how the evidence is obtained.** A verification that cannot say how to obtain its evidence is rewritten here, not skipped at execution time. Every method above runs offline with no service started.

*Admissibility gate:* **Findings without R1–Rn evidence are not admissible under `problems-only`.**

*Baselines, not findings:* R10 and R11 are the state the rest is observed against. Under `problems-only` their own results are never filed as findings; they are cited only as the state in which another R-row's finding was observed.

*Documented skips:* a named method that cannot be run is emitted as a **documented skip with justification — never silence**. A silent skip reads under `problems-only` as "no finding". A skip never closes the check it belongs to.

## 6. Audit Dimensions (checks + evidence)

### (a) Declared Setting Model

> Every setting the process declares must be typed, bound, and sourced from a name a user can actually type. Look at the model's own declaration — field types, the environment-variable prefix it accepts, whether an unrecognised key is rejected or ignored, and whether a rejected value's content is echoed back in the error. Also look at the model's own documentation of its resolution order: it is a claim about behaviour and must match what the process does. A value that reaches the model from a declared source but leaves it through an unhandled failure is a finding here. State the reachability of such an input — a programmatic caller and a text-only source are different reachability classes — so the finding is not over-claimed.

| Check | Description | Evidence required |
|---|---|---|
| Every declared field is typed | No setting is accepted as untyped, and no setting's value can be something its type forbids | R1 |
| Prefix scoping | Only the declared prefix is consumed; a near-miss prefix is not silently accepted as a setting | R1, R2 |
| Unknown-key handling | A key from the environment file and a key from the process environment behave the same way to the user: both rejected, or both warned — whichever the model claims | R2 |
| Value concealment in errors | A rejected value's content never appears in the rendered error | R2 |
| Declared resolution order is truthful | The model's documented source order matches observed behaviour for every source | R5 |
| Validation path is total | Every input the declared sources can produce leaves through a validation failure, never through an unhandled error; the reachability class of any counterexample is stated | R2, R6 |

- Evidence: R1, R2, R5, R6.

### (b) Validation and Declared Bounds

> Every declared range is checked against two things: the values a user can put in the file or the environment, and the values a consumer can actually honour. Look at each range's floor, ceiling and type, exercise the extremes, then read the consumer to see whether the whole range is usable. A range whose extreme is accepted at construction and then produces a consumer configuration outside the range is a finding here; the consumer's own constants belong to the phase that owns that consumer.

| Check | Description | Evidence required |
|---|---|---|
| Range enforced as declared | The floor, the ceiling and one step outside each behave as the declaration states, for every range | R3 |
| Type enforced | A value of the wrong type is rejected at the boundary, and the failure is a validation failure | R3, R6 |
| Whole range usable | At the range's floor and ceiling the consumer can honour the value; record any end at which it cannot | R4, R-S2 |
| Defaults inside the range | No declared default falls outside its own range | R3 |
| Validators are total | A before- or after-validator cannot raise on any value the declared sources can produce | R2, R6 |

- Evidence: R3, R4, R6, R-S2.

### (c) Environment Resolution

> Where the environment file is found, who reads it, and which source wins. The location of the file is a function of the working directory, and the pre-flight reader of that file is not the component that consumes it. Look at both parsers and at what each does with an assignment the other one reads differently.

| Check | Description | Evidence required |
|---|---|---|
| Resolution location is stated and stable | The file's location does not change with the working directory, or the dependence is stated where a user will see it | R5 |
| Resolution is observable | The process reports which file it read, and from where, when more than one candidate exists | R5 |
| Source precedence is uniform | Every setting resolves from the sources in one order; no setting's order is an exception | R5 |
| No silent fallback to defaults | Running where no environment file exists is distinguishable from running where one exists with no values | R5 |
| Reader and consumer agree | The pre-flight reader and the consuming parser agree on every assignment form the file syntax allows | R7 |

- Evidence: R5, R7.

### (d) Pre-Construction Configuration Diagnostics

> The diagnostics that exist to catch a bad configuration before the process commits to it: the scan for unrecognised variables, and the rendering of the resulting failure. Look at whether the diagnostic fires in the situations it was written for, whether its content points at the right fix, and how it is emitted relative to everything else the process prints.

| Check | Description | Evidence required |
|---|---|---|
| Diagnostic fires on the case it targets | For each class of unrecognised variable the diagnostic claims to catch, the diagnostic does fire | R7 |
| Diagnostic agrees with the outcome | When the diagnostic is silent, construction does not then fail; when it fires, construction behaves as the diagnostic said | R7, R2 |
| Suggestion points at the intended name | For a range of plausible misspellings of real names, the suggested name is one a user could have meant | R8 |
| Failure is explicit and value-free | A rejected configuration ends the process with a non-zero status and a message naming the offending key without echoing its value | R8 |
| Emission is consistent | The diagnostic is emitted through the same machinery, in the same format, and at the same verbosity as every other line the process prints | R8 |

- Evidence: R7, R8.

### (e) Configuration to Consumer Propagation

> A declared value is only configuration if the consumer receives it, unchanged, and acts on it. Look at every read of every setting, and at every path that can change a setting's value after it is declared. Where the two override paths in this process are structurally different they fail differently; both belong here.

| Check | Description | Evidence required |
|---|---|---|
| Every setting is consumed | Every declared setting is read by at least one production consumer | R1 |
| Value arrives unmodified | The value the consumer acts on equals the value the model holds, with no substitution between them | R1, R4 |
| No hidden literal in place of a setting | A consumer does not substitute a constant for a value the user supplied | R4 |
| Post-declaration overrides preserve validation | A value assigned to the live settings object after construction is re-validated against the field's declared range and type | R6 |
| Override reaches every consumer | A value changed after construction reaches the same consumers the original value would have | R6 |

- Evidence: R1, R4, R6.

### (f) Dead Configuration and Unreachable Sources

> A setting is dead configuration when **no user-supplied value can reach it** — not merely when nothing reads it. A field with no consumer is one case. A field whose only documented source is shadowed by a value the process always supplies is the more common case, and the more damaging one: the user is given a documented control that silently does nothing. Also look for a component the documentation describes as active that nothing in the flow constructs. Presence of a consumer is not a finding of health; the test is whether a value a user supplies is observed at the field.

| Check | Description | Evidence required |
|---|---|---|
| Every field has a production consumer | No declared setting is read by nothing | R1 |
| Every documented source is reachable | For each setting, a value placed in each source the documentation offers is observed at the field through the process's own entry point; a source that never wins is a finding | R5 |
| No shadowed source | No source is unconditionally shadowed by a lower-priority value the process always supplies. A value a user places in that source and never observes at the field is a finding **even when the field itself has a consumer** | R5 |
| Documented-as-active components are wired | Every component the documentation describes as active is constructed somewhere in the flow | R1, R5 |
| Unwired components are not documented as live | A component nothing constructs is not described by the documentation as part of the running flow | R1, R9 |

- Evidence: R1, R5, R9. **This block is not closed by a consumer trace** — reachability of each source is the test, and R5 is where it is obtained.

### (g) The Example Configuration Artifact

> The committed template a user is told to copy is an artifact, and it is validated against the live model like any other. Check it in both directions, check the values it names, and check the settings documents that repeat the same claims.

| Check | Description | Evidence required |
|---|---|---|
| Every example line validates | Each commented assignment, uncommented in isolation, is accepted by the model | R9 |
| Every declared setting appears | No declared setting is absent from the example file | R9 |
| No name appears that is not declared | Every name in the example file corresponds to a declared setting | R9 |
| Named values are real | Every value the file offers as legal exists in the declared type | R9 |
| Structure is coherent | Section headings in the file contain the assignments they name | R9 |
| No real values in the artifact | The file contains no real credential, key or account value | R9 |
| Settings documents agree | Every settings-model claim repeated in a document matches the live model | R9 |

- Evidence: R9.

## 7. Cross-Cutting (owned here, not duplicated)

Each line names the phase that owns the facet. **Do not file a finding in this phase on any facet named below.**

- **The runtime lifetime, permission and redaction of credential material → `06`.** This phase owns only the *setting* that selects a credential source — its existence, its legal values, and whether a user-supplied value reaches it.
- **The permission mode, creation mode, atomicity and cleanup of any file → `07`**, including a file this phase's settings cause to be created, and including the access mode named in R-S1. **The credential file's content and redaction → `06`; the credential file's permission mode and the platform reality of that mode → `06`.**
- **The effect of a concurrency bound → `04`.** A bounded setting whose consumer acquires a non-reentrant primitive more than once on one path, and that path's runtime consequence, is `04`'s in full. This phase must not file it and must not restate its severity.
- **The composition of a timeout budget and the policy of when to retry or pause → `03`.** The *declared range* of a timeout or rate setting is this phase's; the hardcoded constants a consumer substitutes into the same unit, and the resulting budget, are `03`'s. A declared range is this phase's defect when no legal value of the setting can be honoured by its consumer.
- **The command-line option contract → `08`** — which options exist, their declared defaults, the drift between the two commands' option sets, and the options that are not settings fields at all.
- **The seam between this phase and `08` for overrides: this phase owns an override applied through a programmatic construction that skips re-validation; `08` owns the declared option contract itself.** Test: *does the finding survive replacing the command-line entry point with a direct call into the same function?* If yes → this phase (a defect of the settings model). If no → `08` (a defect of the CLI surface). A value the model admits outside its declared range survives → `CFG-`. An option whose own declaration omits the range disappears → `08`. A documented source that never reaches its consumer survives, because any caller passing a keyword argument hits the same precedence → `CFG-`; `08` may cross-reference and must not file it.
- **Secret scanning, ignore-file coverage, and whether a real environment file is tracked → `11`.** A dependency declaration in the build manifest → `11`.
- **Whether a secret appears in what the process emits → `06`.** Renderer selection, stream discipline and terminal arbitration → `08`. **The one exception, owned here:** the emission of *configuration* diagnostics before the logging system is configured, and the consequence of the resulting inconsistent output. How the pre-construction step is wired into each entry point, and whether any path bypasses it, is `01`'s.
- **Documentation.** A document claim that is **checkable against the live settings model** — a field's existence, type, default, declared range, legal value list, environment-variable name, or source precedence — is **this phase's**, including in the committed example configuration file and in the settings documents. A document's **structural** description of the system — modules, layers, flows, architecture, removed features — is `09`'s. A document's **command-line contract** — which options exist, their declared defaults, exit status — is `08`'s. A document describing the audit pipeline itself, or a dangling reference in source to a finding that no report contains, is `99`'s.
- **Signal delivery and the derivation of shutdown state → `04`.** The meaning of an exit code → `08`. The path validity and containment of a directory a setting names → `07`. The correctness of a validator's type annotation → `09`; whether an input can escape the validation-failure handler at runtime is this phase's.
- **Whether the test suite proves any of the above → `10`.** Whether a *finding* from this phase survives validation → `99`.

## 8. Edge Cases

- An unrecognised key in the environment file (rejected) versus the same key in the process environment (ignored) — two behaviours for one user mistake.
- A numeric value one step below the floor, or one above the ceiling.
- A value of the wrong type for an enum-typed or a range-typed setting.
- An empty value for a setting that has no meaningful empty form.
- A shell-style variable reference that expands to nothing.
- The working directory differs from the directory the environment file lives in.
- An assignment preceded by an export keyword.
- An assignment with a trailing inline comment, or a quoted value.
- The same setting supplied through two sources with different precedence.
- A setting supplied once and overridden afterwards, bypassing validation.
- A document naming as legal a value the declared type does not accept.
- An example assignment that passes in isolation but contradicts another document.

## 9. Severity Taxonomy

The findings template is the authority. `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW`; `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR`; `Classification ∈ mandatory | advisory`. The four words and the four type labels are fixed there and are not redefined here.

| Severity | Conditions |
|---|---|
| CRITICAL | A value the user supplied is silently discarded or silently replaced; a declared range is not enforced on a path the process itself takes. |
| HIGH | A documented source cannot reach its setting; a value outside the declared range reaches a consumer; a value inside the declared range cannot be honoured by its consumer. |
| MEDIUM | A diagnostic misses the case it targets, or names a suggestion that is wrong; the example artifact or a settings document contradicts the live model. |
| LOW | Resolution depends on the working directory with no diagnostic; a validator accepts a value with no consumer-visible effect. |

A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.

## 10. Recommended Sequence

1. Discovery (§4).
2. Runtime verification (§5) — R10 and R11 first, as the baseline the rest is observed against.
3. Per-dimension checks (§6), (a) through (g).
4. Cross-cutting (§7) and edge cases (§8).
5. Consolidate findings, re-reading §7 before writing each one.

## 11. Finding Prefix

Use `CFG-` for all findings in this phase. `CFG-` is unique in the catalogue, shares no first two characters with any other phase prefix, and is obtainable from no other prefix by a single plausible edit.

## 12. Reporting

- Write findings to: `.ai/audit/02-config/findings.md`
- Template: `.ai/audit/templates/audit-findings.md`
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**
- `problems-only: true`:
  - The report contains **only** findings. Omit any dimension, table row, or section where everything is correct.
  - If all verifications and all dimensions yield nothing, write exactly one line: `No problems found in this phase.`
  - Every finding MUST carry (1) **runtime evidence** obtained by a named method, and (2) the **exact consequence** — not "violates invariant X".
  - A finding whose runtime consequence was not observed is filed with the structural fact and an explicit **UNVERIFIED** marker, never with an observed severity.
  - Findings without R1–Rn evidence are not admissible.
