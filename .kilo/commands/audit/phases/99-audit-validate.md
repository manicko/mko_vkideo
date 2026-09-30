---
name: 99-validate
status: draft
validated: no
executor: validator
problems-only: true
---

# 99 — Audit Findings Validation

> Audit phase. LLM-auditor instruction. Architecture-agnostic: described via
> ARCHITECTURAL LAYERS, ZONES OF RESPONSIBILITY, KEY RISKS, GOALS. NOT tied to
> specific files, modules, or functions. Must stay valid if the architecture
> changes.
>
> **Output mode:** `problems-only` — report only findings; do not narrate a clean
> bill of health. The single artifact this phase writes is **exempt** — binding
> rule 2 below, and `## 11`.
>
> **Binding rule 1 — a severity is composed here; a decision is not a severity.**
> The source report arrives with severities attached. Each is re-derived from this
> phase's own verification of the finding, and **none is changed because of the
> decision recorded against it.** The decision is a field (`## 8`, `## 11`). No
> severity, count or verdict written beside a subject in any preceding document,
> in this file's `## 6`, or in the source report is inherited.
>
> **Binding rule 2 — the validated artifact is exempt from `problems-only`, and
> the exemption is bounded.** This artifact is a judgment record about findings,
> not a findings report. A rejected finding's content and its reason are the
> evidence the next run needs in order not to re-derive it; a merged finding's
> original text is the evidence that the merge lost nothing. Suppressing either is
> the defect. The exemption covers **exactly** the decision record and the
> retained rejected and merged content named in `## 11`, plus the action tally —
> and nothing else. Every check row whose subject verified clean is still absent;
> a run whose source report holds no findings writes the tally and nothing more.
>
> **Binding rule 3 — this file is never renamed, and this is the only phase that
> does not use the 12-section skeleton.** Its exact filename is hardcoded twice in
> the command that runs the audit — once to exclude it from the phase list, once
> to locate the validator — and its own section numbers are referenced by the
> rewrite that produced it. Both facts are load-bearing. Any instruction in this
> file that reads as a licence to rename it is void.

*`executor: validator` and this deviation are deliberate and apply to this file
alone. The skeleton fixes `executor: auditor` and a 12-section body for every
reworked and new phase; this is neither.*

## 1. Goal

Whether the audit's own output — its findings, and the documents that produce
them — is technically correct, currently applicable, non-duplicated, and worth
acting on.

## 2. System Under Audit (layers & zones)

| Zone | Concern | Key risks |
|---|---|---|
| Findings ingestion | Taking a copy of the source report as the working base, and keeping it read-only | Editing the source; an artifact that cannot be read without it |
| Cross-finding analysis | One root cause stated twice; two phases asserting incompatible facts | A merge that loses content; a conflict left standing |
| Per-finding adjudication | Technical correctness, current applicability, architectural fit, operational value | A finding approved because it was there; one re-derived from an earlier report |
| Fix ordering | What must land before what, and what cannot be ordered at all | Two fixes that cannot both ship; an insertion point that will not exist |
| The audit's own documents | What the pipeline says it does, what it does, and the vocabulary the reports are written in | A stage that is described and implemented by nothing; a legal report that a role file forbids |
| The report contract | The decision record, the retained decisions, and the format that must carry both | A decision with nowhere to live; a rejected claim that cannot be recovered |

**In scope:**
- The four-criteria per-finding validation: technical correctness, current applicability, architectural fit, operational value.
- Cross-finding merge candidates, and which ID absorbs which.
- Cross-phase conflicts, and the dependency chains between accepted findings.
- Rollout-safety assessment: circular dependencies, hidden chains, unsafe ordering, fragile insertion points.
- The type and classification labels, adjudicated against the report template.
- The dead-code spec cross-reference (specification, readme, data model, configuration templates).
- The per-finding decision record and the report field that must carry it.
- The audit pipeline's own execution claims versus its implementation — stages, agents, artifacts, gates.
- Defects in the audit pipeline's own documents, the report template, and the agent role files it launches.

*Claims made inside the bullets are this phase's scope, not its evidence. Each is re-derived by the block that owns it, and a claim re-derived as matching is filed as nothing. A bullet naming a subject that produces no check in `## 5` is not an instruction, and no check is manufactured to fill one.*

**Out of scope:**
- **The test suite itself → `10`.** This phase audits the *findings*; `10` audits the *tests*. The boundary is stated in both files, and neither files the other's defect.
- **A finding's technical content, its subject and its consequence → the phase that filed it.** This phase records a decision against it and never re-files, re-derives or restates it.
- **The definition of the severity, type and classification vocabularies → the report template**, which this phase treats as the authority and adjudicates against.
- **The phase catalogue's subjects → `01`–`11`.** This phase validates what those phases produced; it does not audit what they audit.
- **The pipeline's own code.** There is none. The pipeline is four command documents, a phase directory and a template; the documents are this phase's subject and are edited by no one inside a run.
- **Licence posture, terms acknowledgement, notice mechanism; a general performance, rate or capacity claim** → not audit subjects, inadmissible under `problems-only`, expressly rejected upstream. **Do not file.**

## 3. Prerequisites

- `uv run pytest <path>` · `uv run ruff check <path>` · `uv run ruff format --check <path>` · `uv run mypy <path>` (from `.ai/context/commands.md`).
- **No Docker. No database. No service must be started.** This phase reads reports, phase handbooks and pipeline documents; it executes no product code and starts nothing.
- `mypy` (strict) is the configured type checker. `basedpyright` is in the dev dependency group and is **not** the configured checker — do not substitute it.
- Completed auditor phase handbooks (`.kilo/commands/audit/phases/NN-*.md`, excluding `99-audit-validate.md`).
- The source findings file the orchestrator named for this phase: `.ai/audit/{NN}-{slug}/findings.md`, where `{slug}` is the filename stem after `NN-audit-`.
- Validation store path — per-phase copies named `.ai/audit/99-validation/{NN}-{slug}-validated-findings.md` (see Correction 2).
- The audit pipeline's own documents, for the pipeline-document ownership in §6.
- Project specification, README, Pydantic models / `StrEnum` values, configuration templates (for the dead-code mandatory cross-reference, §5).
- **The phase range is `01`–`11`, plus this file.** This phase validates the findings of every phase the orchestrator offers, and of no other. A findings file whose phase number is outside that range is reported, not validated.
- **Repository-wide searches exclude every worktree directory.** A stale copy of an earlier phase set is present and is not part of the catalogue; a match count taken from it is wrong in the direction that makes this phase look covered.

## 4. Runtime Verification (mandatory)

**R0 — Discovery** *(emits no checkpoint)*
Map the corpus before checking anything. **Use roles, not names** — no concrete
file, module or class name appears in this list.

1. **Corpus map** — every findings file the phase range contains, the phase that
   wrote it, its finding count, and whether a handbook exists for it. A handbook
   with no findings file is a gap; a findings file with no handbook is a gap. Both
   are reported.
2. **Identifier map** — every finding identifier in the corpus, its prefix, and
   the phase that owns it. A prefix no phase claims, and a collision between two
   live prefixes, are recorded here.
3. **Decision-record map** — for every finding, which of the four decisions the
   report format has room to carry, and where that room is. A decision with no
   slot is recorded as an **absent slot**, not as a missing decision.
4. **Pipeline-document map** — every document the pipeline reads or writes, what
   each declares it does, and which of them the pipeline never opens. The
   denominator for (g) and (h).

*Role vocabulary: the command that selects and runs phases · the command that
rewrites recommendations in the validation store · the command that re-derives the
catalogue · the repository-wide reachability census · the phase handbook directory ·
the report format · each agent role file the pipeline launches · each findings file
the pipeline has produced.*

**R1–R4 each emit a rolling anchored-summary checkpoint. R0 does not, and these
four are the only checkpoints this file defines.**

**R1 — Copy Source Findings**
Copy the auditor's per-phase findings file as the base for the validated report
in the validation store, named per phase — e.g. for phase `01-audit-entry-architecture.md`,
`.ai/audit/99-validation/01-entry-architecture-validated-findings.md`. This is the
exact string the orchestrator writes (`audit-multi-phase.md:94`); the orchestrator's
verification step is being corrected to match it. All edits are applied inline to this
copy. The final file must be fully self-contained — the reader should never need
to consult the original. **The source report is read-only to this phase; every edit
lands in the copy.**

Checkpoint 1 fields: stage = *R1 Copy Source Findings*, findings-in-scope count,
evidence anchor, blockers.

**R2 — Cross-Finding Analysis**
Scan findings across all phases in the range:

- **Same root cause** → mark as merge candidate. Note which finding IDs overlap
  and which absorbs which.
- **Conflicting evidence** (e.g. one phase says "all commands work", another
  says "run command crashes") → flag as cross-phase conflict. CRITICAL.
- **Dependency chains** → note if fixing one finding depends on another.

Checkpoint 2 fields: stage = *R2 Cross-Finding Analysis*, cross-phase conflict
count, merge-candidate count.

**R3 — Validate Each Finding**
For every finding, verify:

1. **Technical correctness** — is the problem real? Check the actual code.
2. **Current applicability** — is the codebase still in this state?
3. **Architectural fit** — does the recommendation align with project patterns?
4. **Operational value** — is the fix worth the effort at this project scale?

Checkpoint 3 fields: stage = *R3 Validate Each Finding*, per-finding decision tally
(Validated / Reclassified / Merged / Rejected). **A decision tally, not a severity
tally.**

**R4 — Assess Rollout Safety**
Check: circular dependencies, hidden dependency chains, unsafe rollout ordering,
fragile insertion points. Add any detected issues as new findings.

Checkpoint 4 fields: stage = *R4 Assess Rollout Safety*, unsafe-ordering count,
findings added, blockers.

## 5. Audit Dimensions (checks + evidence)

Nine blocks, each independently executable: a validator may run one with no other
context, from its title and description alone. The letter order **is** the
re-entry order (`## 9`). **No block title or description states an outcome**; each
is the question, and the finding is named as a condition to look for.

### (a) Per-finding validity

> Whether each finding is technically correct, still applicable, aligned with a pattern the project actually uses, and worth acting on at this scale. Every finding is decided on its own; none is presumed, and none is inherited from a previous run.

| Check | Description | Evidence required |
|---|---|---|
| Technical correctness | Re-derive the claim from the artifact it names, not from its wording. | The re-derived fact, quoted; the artifact read, named. |
| Current applicability | The named code, setting or state still exists as described. | Present or absent, with the search that established it. |
| Architectural fit | Does the fix match a pattern the project already uses, or does it introduce one? | The existing pattern, or its recorded absence. |
| Operational value | Effort against the exact consequence, at this project's size. | The consequence, stated exactly — not "violates invariant X". |

- Evidence: R3.

### (b) Merge candidates and cross-phase conflicts

> Whether one defect is stated twice, and whether two phases assert incompatible facts about one subject. A merge collapses one identifier into another; a conflict is filed as a new finding. Two findings that complement each other are neither.

| Check | Description | Evidence required |
|---|---|---|
| Same root cause | Two findings whose cause, once named, is one thing. | The shared cause; the absorbing ID; every absorbed ID. |
| Incompatible claims | Two phases, one subject, two answers that cannot both hold. | Both claims quoted; the subject; which one the evidence supports, or `UNVERIFIED`. |
| Genuine complement | Two findings covering the same subject from different sides. | Both retained, cross-referenced. **Not a merge.** |
| One finding, several phases | A claim that belongs to two phases' subjects. | Split or cross-reference; the absorbing finding carries the content. |

- Evidence: R2.

### (c) Fix ordering and rollout safety

> Whether the findings this phase accepts can be acted on in an order that is safe. Anything detected is filed as a **new** finding, never folded into one that already exists.

| Check | Description | Evidence required |
|---|---|---|
| Circular dependency | Two accepted fixes, each a prerequisite of the other. | The pair, quoted from the two findings. |
| Hidden chain | A prerequisite named by no finding and asserted by no one. | The missing link; which fix needs it. |
| Unsafe ordering | Two fixes that can be applied in the wrong order and one order breaks. | The order, and what breaks. |
| Fragile insertion point | A recommendation whose anchor is a line, a position or a name that will not exist. | The anchor; what makes it fragile. |

- Evidence: R4.

### (d) Type and classification adjudication

> Whether each finding carries a label and a classification the report format permits, and whether the code or the document should change. **All four type labels are in scope, including the one the role that executes this phase omits from its own list** — a legal report must not be illegal to the agent that writes it.

| Check | Description | Evidence required |
|---|---|---|
| Label legality | Is the label one the report format defines? | The label; the format's own list. |
| Code or document | When the two disagree, which is better. | The disagreement; the decision; the reason. |
| Observed failure | A finding describing something seen to fail is checked against the runtime-failure label **first**. | The observation. **Never reclassified away because a role file omits the label.** |
| Classification legality | Is the classification one the format defines, and is it the right one? | The value; the format's guide row. |

- Evidence: R3.

#### Type-specific rules, carried forward

**[BEST-PRACTICE]**
- Reject if overengineered or adds complexity without clear maintenance benefit.
- Reject if ROI is negative for project scale.
- **Splitting large files / smaller functions and modules is high ROI** — shorter
  code units are easier to edit, review, and maintain with lower risk of
  corruption. Do not reject modularization findings as "overengineering" unless
  the split introduces unnecessary indirection or abstraction.

**[DOC-UPDATE]**
- Verify the proposed doc change accurately reflects code reality.

### (e) Dead-code reconciliation

> Whether a component called dead is referenced by the specification, the readme, the declared data model, or the configuration templates. **This block is applied, not optional.** A reference in any of the four rejects the "dead code" label and reclassifies the finding as missing integration.

| Check | Description | Evidence required |
|---|---|---|
| Specification | Does the declared specification describe the component? | The passage, or its absence across a named search. |
| Readme | Does the project's own readme? | The passage, or its absence. |
| Declared data model | Does any declared type or enumeration member name it? | The member, or its absence. |
| Configuration templates | Does any shipped template enable it? | The entry, or its absence. |
| Verdict | Referenced anywhere → not dead code. | Reclassified as missing integration, with the reference quoted. |

- Evidence: R3, R2. **Never file a dead-code finding from any other block without running this one first.**

### (f) Rejection discipline and retention

> Whether a finding meets a stated ground for rejection, and whether its reason survives in the artifact. **Nothing decided here is deleted.** The rejection grounds: already implemented · stale · duplicate · low value at this scale · architecture-breaking · operationally unsafe · overly complex · against project direction.

| Check | Description | Evidence required |
|---|---|---|
| Ground stated | Is one of the grounds the actual reason? | The ground, named from the list above. |
| Reason written | Does every rejection carry a reason a later run can act on? | The reason text, present in the artifact. |
| Retained content | The rejected claim and its reason **stay in the artifact**. | The retained block, verified present in the copy. |
| Re-derivation guard | A later run meets the same claim again. | The retained reason is what stops it being re-derived; a record that the artifact carries it. |

- Evidence: R3, R1. **This block is why binding rule 2 exists; it is not overridden by it.**

### (g) The pipeline's own execution claims

> Whether the audit's own commands do what they say they do. Stages, agents launched, artifacts produced, gates enforced, and the number of stages the commands actually run. **A stage described in a command and implemented by none is a defect of that command** — filed here, with the artifact such a stage would have produced named as the artifact that does not exist.

| Check | Description | Evidence required |
|---|---|---|
| Stage count | How many stages does the pipeline run, against how many do its documents describe? | Both counts, with the lines that state each. |
| Agents launched | Which roles do the commands actually launch? | The launch lines, per command. |
| Stage artifacts | For each described stage, the artifact it declares. | The declared path; whether anything creates it. |
| Stage gates | For each described gate, what enforces it. | The gate; the enforcement, or its absence. |
| Parallel ceiling | What ceiling the commands declare, and what the launch sites honour. | The declared ceiling; the launch sites, counted. |
| Post-loop stages | What runs after the loop, and what it produces. | The command; whether it adds a stage or only edits in place. |

- Evidence: R0, R1. **The finding is the mismatch between what a command declares and what it runs — never the count of stages a document describes.**

### (h) Pipeline-document defects

> Whether the audit's own documents agree with one another and with what the pipeline executes. The write path and the check path · a gate whose condition nothing evaluates · a rule that deletes the record of a decision · a format that names a role the project does not have · a vocabulary one document defines and another omits · a number given as free that is in use · a required context file that is absent · a reachability census that reaches the catalogue itself. The eight are enumerated in `## 6`; this block is how each is checked.

| Check | Description | Evidence required |
|---|---|---|
| Path agreement | For every artifact, the string written and the string checked. | Both strings, with lines. A mismatch is the finding. |
| Gate evaluability | For every gate, the term it keys on and whether anything defines it. | The term; its definition, or its absence. |
| Decision preservation | Does any instruction delete a decision the next run needs? | The instruction; what it destroys. |
| Named roles | Does every declared role exist and is it the one launched? | The declared name; the roster; the launch line. |
| Vocabularies | For each enum, the format's list against each role file's list. | The enum; every place it is listed; the disagreement. |
| Number allocation | Every "next available number" instruction against the numbers in use. | The instruction; the numbers held. |
| Required context | Every mandatory read against what the tree holds. | The read; the file, present or absent. |
| Census reach | Does the reachability rule's protect-list cover the catalogue and the worktrees? | The scope; the protect-list; what falls through it. |

- Evidence: R0, R1. **A document-consistency remark is not a finding; both sides of the disagreement, with their lines, are.**

### (i) The per-finding decision record and the report contract

> Whether every decision taken about a finding is recorded in a place the report can carry, and whether the report format has room for it. This block defines the field and requires it of every decided finding; whether the format can carry it is read from the format and recorded either way.

| Check | Description | Evidence required |
|---|---|---|
| Every decision recorded | Does each decided finding carry a decision, a rationale where the decision is not the pass, and its cross-references? | The record, per finding. **A decision with no record is a finding.** |
| The field exists in the format | Does the report format have a slot for the decision, between the finding heading and the field table? | The format's own finding block; the absence. **This is the input defect this block owns.** |
| The retained content is present | Are the rejected and merged contents actually in the artifact? | The blocks, verified in the copy. |
| The tally reconciles | Does the action tally equal the per-finding records? | The tally; the per-finding count; the difference, or none. |
| No invented entries | Does the artifact contain any decision, cross-phase conflict or rollout finding that no source finding supports? | The count of each; a zero is not a reason to write a row. |
| Pre-answered sections deleted | Does the artifact still carry a summary, appendix or placeholder section the format supplies pre-answered? | The section, the placeholder in it, and its absence from the artifact. **A section every phase must delete is a defect of the format.** |

- Evidence: R1, R3, R4. **A count of zero is written as a tally of zero and nothing more** (binding rule 2).

## 6. Cross-Cutting (owned here, not duplicated)

- **Same root cause → merge candidate** (see `## 11`, *Merged*).
- **Conflicting evidence between phases → cross-phase conflict** (CRITICAL; see `## 8`).
- **A dependency chain between findings → a rollout-ordering constraint** (see `## 4` R4 and `## 8`).
- **The tests themselves → `10`. This phase audits the findings.** `10` audits the tests; this phase audits the findings, including whether a finding from `10` survives validation. **Neither files the other's defect**, and the boundary is stated on both sides so this phase's cross-finding conflict detection and `10`'s evidence-quality critique cannot converge on one defect.
- **A finding's technical content, its subject and its consequence → the phase that filed it.** This phase records a decision against it and never re-files it, re-derives its subject, or restates its consequence. A cross-reference to a sibling's finding is not a copy of it.
- **The definition of the severity, type and classification vocabularies → the report format**, which this phase treats as the authority and adjudicates against. A sibling that has already corrected a severity in its own run owns that correction; this phase re-derives it, it does not inherit it.
- **R-E — a document is owned by the phase that owns the code it describes; a document describing the audit pipeline itself → this phase.** Applied here: a claim in the project's own documentation → `02` for the settings model, `09` for a structural description, `08` for a command-line contract; a claim in a phase handbook about a catalogue subject → the phase owning the subject; **a claim in any pipeline document, in the report format, or in an agent role file → this phase.**
- **The audit catalogue's subject matter → `01`–`11`.** This phase files no finding about what those phases audit.

**The audit pipeline's own documents are owned here, and no other phase files a defect in them.** The following are this phase's subjects:

1. **A command that writes one file name and a step that checks another.** The write path and the check path must name the same artifact, or every run fails its own gate for a file that is on disk. *The write instruction is the form the pipeline has always produced; the check is the defective side.*
2. **A gate that cannot be evaluated.** A condition that launches a stage — "not trivial", "significant" — with no defined term and no implementation is a gate that silently never fires, while the run's closing output reports that stage's coverage. **A stage that never runs and a summary claiming it ran are one defect, not two.**
3. **An instruction that deletes the record of a decision.** A rule that strips rejected content from the artifact before it is merged destroys the evidence the next run needs. Where two documents disagree, **the preserving side governs this phase's output**, and the contradiction is filed with the side this phase took and the reason.
4. **A required context file that does not exist.** A command that reads a project-instructions file as mandatory base context, where the repository root holds none, assembles half its context and reports nothing about the miss. State where the rules actually live.
5. **A role or a vocabulary the pipeline declares and does not have.** A report format naming an executor that is not a role the pipeline can launch, and a role file listing fewer labels than the format defines, are the same class of defect: the pipeline's own documents disagree about what may be written and by whom. *The format is the authority for the vocabularies; the role file is the defective side — and the role that executes this phase is one of them.*
6. **A phase number given as free that is in use.** An instruction to take "the next available number", with a worked example, collides with numbers the directory already holds, and the pipeline globs the directory with no gap check. The rule must be "the lowest number not in use, and never the number this file holds".
7. **A reachability census that reaches the catalogue.** A command that lists files unreachable from the product's entry points will list this phase directory, the audit commands, the report format, and any worktree holding a copy of an earlier catalogue. **The audit's own documents, the phase directory, and every worktree are exempt from that census** — stated here because nothing else states it, and because the exemption is what keeps a run of it from listing the whole catalogue as removable.
8. **A command that cannot have run as written.** A command naming a role that does not exist, or referring to a step of itself that does not exist, is a defect of that command — and one that makes the provenance of every artifact it claims to have produced unverifiable.

**Each subject above is a subject to verify, not a finding.** It is filed only when this phase has executed the check named in block (h) and observed the consequence, and its severity is composed here (binding rule 1). **A subject that checks out is not written down**, and no severity, count or verdict is recorded beside any of the eight — a list of eight pre-scored defects is a pre-answered report, and this phase must not ship one.

## 7. Edge Cases

- **Conflict vs. complement** — a finding may conflict with one in another phase (escalate as `VAL-`) or legitimately complement it (retain both, cross-ref).
- **Merge where evidence is incomplete** — preserve original content for reference; record the decision in the `Decision` field (`## 11`) listing merged IDs.
- **Findings that span multiple phases** — split or cross-reference; the absorbing finding carries the merged content.
- **Stale-but-similar** — a finding may be rejected as stale while a sibling finding (same root cause) is validated; record the relationship in `## 11` Merged Findings.
- **A source report that is absent, empty, or holds only a pass line.** The decision is a non-reproduction with the inputs recorded — never a clean bill of health, and never a set of `VAL-` findings about a report that was never produced.
- **A finding whose evidence cites something that no longer exists.** Technical correctness fails on the citation, not on the claim; the finding is reclassified or rejected with the reason that the evidence is gone, and the claim is not re-derived from the finding's own wording.
- **An identifier in the corpus that no phase prefix claims, or that two live prefixes share.** Recorded in R0's identifier map and filed once here; the test suite and other artifacts may already carry forms of this shape, and this phase adopts none of them.
- **A finding from a phase number outside the range.** Reported as corpus drift, not validated.
- **A phase that produced findings and was never validated.** The coverage claim the run's closing output makes is checkable here, and is checkable only here.
- **A finding this phase rejected that a later run re-derives as valid.** The retained rejection reason is the evidence that decides it; a re-derivation that ignores it is a finding against the reason, not against the earlier decision.
- **A finding that is the only finding in the corpus.** No conflict, no merge, no ordering chain and no tally row exists. `No problems found in this phase.` is inadmissible; the artifact records the decision and stops.

## 8. Severity Taxonomy

**The findings template is the authority.** `.ai/audit/templates/audit-findings.md:69`
fixes `Severity ∈ CRITICAL | HIGH | MEDIUM | LOW` as the severity of a **defect**; `:68`
fixes `Type ∈ SPEC-DEVIATION | BEST-PRACTICE | DOC-UPDATE | RUNTIME-ERROR` and `:74`
fixes `Classification ∈ mandatory | advisory`. **The four severity words are not
redefined here**, and this file adds no fifth. Every sibling phase states the same
sentence and then gives only the conditions that are specific to its own subject.

| Severity | Condition in this phase |
|----------|-------------------------|
| CRITICAL | A cross-phase conflict, or a rollout-safety blocker: two phases assert incompatible facts about the same subject; or a fix that cannot be ordered safely because a prerequisite of it is itself a finding. |
| HIGH | A finding whose technical correctness or current applicability failed verification; or a rejected finding whose rejection changes a conclusion the report would otherwise carry. |
| MEDIUM | A reclassified finding (its `Type` changed) or a merged finding (its content moved under another ID). The subject survives; the framing changes. |
| LOW | A `DOC-UPDATE` candidate; any advisory finding with no security, data-loss or correctness consequence. |

**The per-finding decision is not a severity.** `Validated / Reclassified / Merged /
Rejected` is a *decision about a finding*, recorded in the `Decision` field
(`## 11`, *Validation Note Format*) and tallied in the Validation Summary (`## 11`).
**A decision never changes the severity column.** A rejected finding keeps the
severity it carried, and a reclassified finding keeps it: recording the decision in
the severity column is what made severity comparison across reports meaningless.

**Type guidance.** `SPEC-DEVIATION` — the finding contradicts the project's own
declared rule. `BEST-PRACTICE` — a defensible arrangement with a demonstrated gap.
`DOC-UPDATE` — code is correct and a document says otherwise. `RUNTIME-ERROR` —
anything observed failing. All four are admissible in every report this pipeline
writes, including the one this phase produces.

**These conditions are a classification vocabulary, not a verdict.** Every severity
is composed by this phase from its own run (binding rule 1). The conditions above
still apply in full: two claims must be **incompatible** to be a conflict, and the
consequence must be **observed**. A finding whose consequence was not observed is
filed with the structural fact and an explicit **`UNVERIFIED`** marker, never with an
observed severity. A finding that did not reproduce is filed as a non-reproduction
with the exact inputs recorded, never as a clean bill of health.

## 9. Recommended Sequence

**What the pipeline does, per selected phase, in the one command that runs it:**

1. **Executor subagent** → `.ai/audit/{NN}-{slug}/findings.md`.
   Gate: the file exists and is not empty. One retry, then escalation.
2. **Validator subagent — this file**, launched only when the command's own
   condition holds, which is stated in words nothing evaluates (see `## 6`
   subjects 1 and 2, and blocks (g) and (h)).
   → `.ai/audit/99-validation/{NN}-{slug}-validated-findings.md`.
   Gate: the artifact exists. One retry, then escalation.

A separate command then rewrites non-actionable recommendations **in place**
inside the validation store. It runs no phase, enforces no gate, and produces no
new artifact. Nothing follows it.

**Is there a researcher stage, a documentation stage or a final-consistency stage,
and is there a gate beyond the two above? Neither is answered here: the run
establishes the pipeline's stage inventory, and block (g) is the check that
establishes it.** A stage described in a command and implemented by none — and the
artifact such a stage would have produced — are defects of that command, filed
under block (g). They are not described here as a pipeline that exists, and a stage
name from a removed stage is not a stage of this phase.

**Order within this phase.** R0 · R1 · R2 · R3 · R4 · blocks (a) through (i) in the
order they are written · `## 6` and `## 7`, re-reading `## 6` before writing each
finding · `## 11`.

**Second-pass order.** If this phase is re-run after a thin result, do **not**
start again at step 1. Re-enter at the first item below for which no evidence was
recorded and continue downward: **R0 → R1 → R2 → R3 → R4 → (a) → (b) → (c) → (d) →
(e) → (f) → (g) → (h) → (i)**. A block with partial evidence is resumed; a block
with complete evidence is skipped. A tally of zero is admissible **only once R0's
corpus map, identifier map and decision-record map are all recorded** — those
three are the ways this phase manufactures a clean bill of health, and the first
line of the report must close that door.

## 10. Finding Prefix

Use `VAL-` for all findings in this phase. `VAL-` is unique among the phase
prefixes, shares no first two characters with any of them (`EN CF NE CO PR SE AR
OU QL TS DE VA` are all distinct), is obtainable from no other prefix by a single
plausible edit, and does not encode the phase number, so renumbering never
invalidates a published finding ID.

**`VAL-` is reserved for defects in the audit inputs themselves** — a conflict, a
merge, an unsafe ordering, a pipeline-document defect — **and is never used for a
product-code finding.** A finding about the product belongs to the phase that owns
its subject. A decision taken about a product finding is recorded in the
Validation Note; it is not itself a `VAL-` finding unless the decision *created*
something — a conflict between phases, an ordering constraint, or a new rollout
problem.

**No identifier is minted before its evidence exists.** A number written beside a
subject is a pre-answered outcome by another name, and the worked examples this
section used to carry — two concrete numbers attached to two named defect classes —
are removed for exactly that reason. **This phase adopts no identifier already
present in the tree**: a form another artefact or report already carries is
inventory for R0's identifier map, never one of this phase's own, and this phase
cannot resolve which catalogue a two-character collision belongs to.

## 11. Reporting

**The two paths, named exactly:**

- **Read, read-only:** the source findings file the orchestrator named —
  `.ai/audit/{NN}-{slug}/findings.md`, where `{slug}` is the filename stem after
  `NN-audit-`. **This phase never writes to it.**
- **Write, and only this:** `.ai/audit/99-validation/{NN}-{slug}-validated-findings.md`
  — the exact string the orchestrator's write step produces.
- Format: `.ai/audit/templates/audit-findings.md`.
- **Append incrementally — blocks of ≤100 lines per write. Never write the entire report in a single call.**

**The exemption (binding rule 2).** This artifact is a judgment record about
findings, not a findings report, and is exempt from `problems-only` in exactly
three places: the **decision record** on every decided finding; the **retained
content and reason** of a rejected or merged finding; and the **action tally**.
Nowhere else. A check row whose subject verified clean is still absent, a section
whose checks all passed is still absent, and a run whose source report holds no
findings writes the tally and nothing else.

**The filename's verb is not a verdict.** A file named `-validated-findings.md`
records that a run happened. It does not assert that the findings in it survived;
that is what the decision records say, one per finding.

Decisions are applied inline to the copied findings file:

| Action | How to apply |
|--------|-------------|
| **Validated** | Keep as-is. **The severity is re-derived from this phase's own verification, and is not changed by this decision.** |
| **Reclassified** | Update the `Type` field. Record the decision in the `Decision` field directly after the heading. |
| **Merged** | Keep the original content in the file. Record the decision in the `Decision` field directly after the heading, listing merged IDs and target location. |
| **Rejected** | Leave the block in the file as: `### {ID}: ~~{title}~~ [REJECTED]` + `> **Rejection reason:** {explanation}`. **Never delete it** — the claim and the reason are what stop the next run re-deriving it. |
| **Cross-phase conflicts** | Add as new finding entries (`VAL-`) at the end of the Findings section. |
| **Rollout safety issues** | Add as new finding entries (`VAL-`) if detected. |

**The retained Rejected and Merged rows are not a concession to the format. They
are the reason the exemption exists**, and they are the direct opposite of the
pipeline rule that strips rejected content from the artifact before it is merged.
Where the two disagree, the preserving side governs this phase's output and the
contradiction is filed (`## 6` subject 3).

### Validation Note Format

Write the decision into the `Decision` field the report format now carries, placed
directly after the `### {ID}:` heading, for **every** decision, not only for a
merge or a reclassification:

```markdown
**Decision:** {validated | reclassified | merged | rejected} · {decision_detail}
```

The `decision_detail` carries the rationale — required for every decision except
`validated` — and any cross-references.

### Rolling Checkpoint Format

Each of R1–R4 emits an anchored-summary checkpoint. R0 does not. **These four are
the only checkpoints this file defines.**

```markdown
## Checkpoint N — {stage name}

- **Stage:** {R1 Copy Source Findings | R2 Cross-Finding Analysis | R3 Validate Each Finding | R4 Assess Rollout Safety}
- **Findings in scope:** {count} (Validated {n}, Reclassified {n}, Merged {n}, Rejected {n})
- **Evidence anchor:** {self-contained file / line reference — no live source reads}
- **Dependencies / blockers:** {none | …}
- **Checkpoint status:** {open | closed}
```

### Validation Summary

Append at the end of the file:

```markdown
## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | N | — |
| Reclassified | N | ID1, ID2 |
| Merged | N | ID3 → ID4 |
| Rejected | N | ID5, ID6 |
| VAL- (cross-phase / rollout) | N | VAL-001, ... |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| ID5 | ... | ... |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| ID3 | ID4 (phase NN) | ... |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| ID1 | BEST-PRACTICE | SPEC-DEVIATION | ... |
```

**Every one of these four is retained.** Under `problems-only` the three appendices
would be exactly what the rule forbids; under the exemption they are the
definition of what this artifact is for. The Rejected table is the reason a
rejected claim is not re-derived next run. The Merged table is the reason a merge
is auditable. The Reclassified table is the only place a type change is
summarised, and a type change is not a severity change. **A zero count writes a
zero, and no empty appendix is manufactured to fill the shape.**

## Constraints

- DO NOT modify source code.
- DO NOT generate implementation code.
- DO NOT redesign architecture.
- ONLY validate safety, consistency, and applicability.
- Prefer conservative decisions. Prefer rejection over unsafe approval.
- Every report must be self-contained — the reader never needs to consult the
  original auditor finding or any source file.
- **This file is never renamed.** Its exact filename is hardcoded twice in the command that runs the audit, and its section numbers are referenced by the rewrite that produced it. **No other file is renamed by this phase either** — it writes one artifact and reads the rest.
- **This phase runs as one validator.** It launches no subagent. The command's own parallel ceiling governs the executor launches around it, not this phase.
