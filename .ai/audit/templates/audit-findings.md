---
name: audit-findings
description: Structured findings template for audit phase output
agent: auditor
alwaysApply: false
---

# Phase N Audit Findings — {Phase Name}

**Author:** auditor
**Validated by:** {validator | not run}
**Template:** {phase-template-file}
**Status:** {pending|in-progress|complete}
**Validated:** {yes|no}

---

## Findings

### {ID}: {Title}

> **Validation Note:**
> - **Action:** {validated | reclassified | merged | rejected}
> - **Detail:** {rationale — required for every decision except `validated`}
> - **See also:** {other finding IDs or sections}

| Field | Value |
|-------|-------|
| **ID** | {id} |
| **Severity** | {severity} |
| **Type** | {type} |
| **Affected Modules** | {modules} |
| **Classification** | {mandatory\|advisory} |
| **Verification** | {verification} |

**Description:** {description}

**Evidence:** {evidence}

**Recommendation:** {recommendation}

---

## Summary

{Tally the findings above by severity. Count the number of findings in each band **as
recorded in this phase's own findings file**, each finding counted once under the `Severity`
it carries after this report's own decisions; a finding that was merged or rejected is not
counted here. A severity with no findings is written as `0`. An unexecuted or unverified
phase is **counted, not omitted** — add a row `none (UNVERIFIED, not executed)` carrying
the count, matching the model carried by `04-concurrency-cancellation/findings.md`. A
severity with no findings is written as `0`. Add a row for a severity the owning phase's
table defines and this format does not.}

| Severity | Count |
|----------|-------|
| CRITICAL | {count} |
| HIGH | {count} |
| MEDIUM | {count} |
| LOW | {count} |
| none (UNVERIFIED, not executed) | {count} |

## Mandatory Fixes

{Every finding classified `mandatory`, by ID, with what must change and why. If there are
none, write "none".}

## Advisory Recommendations

{Every finding classified `advisory`, by ID, with what to change and why. If there are
none, write "none".}

## Doc Updates Needed

{Every finding of type `DOC-UPDATE`, by ID, with the document and the claim to correct.
If there are none, write "none".}

---

## Template Field Reference

### Mandatory Fields Per Finding

| Field | Type | Values/Format |
|-------|------|---------------|
| `id` | string | Unique identifier within phase (e.g., `BE-001`, `FE-003`) |
| `title` | string | Human-readable one-line summary |
| `type` | enum | `SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, `RUNTIME-ERROR` |
| `severity` | enum | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. **When the runtime consequence of a finding was not observed, the band is composed from the structural fact under the owning phase's own severity table.** It is never a severity the run observed, and this row prescribes no band of its own: the owning phase's table decides. That table already carries a band a structural fact alone satisfies — for example phase `04`'s own `LOW` row, *"A shape, naming or structure deviation with no runtime consequence."* **The rule is prospective: a severity already written is not re-read under it.** |
| `verification` | enum | `observed` · `unverified` — **required on every finding.** `observed` when the runtime consequence was executed and seen; `unverified` when it was not. A finding filed `unverified` carries the structural fact, and its `severity` band is composed from that fact under the owning phase's own severity table. This field is the machine-checkable carrier of the `UNVERIFIED` marker; the marker prose is its human-readable form. |
| `description` | string | Detailed problem description with context |
| `evidence` | string | File paths, line references, log excerpts, code snippets |
| `affected_modules` | list | Affected module paths (e.g., `src/**/`, `frontend/src/features/auth/`) |
| `recommendation` | string | Concrete fix direction: what to change and why |
| `classification` | enum | `mandatory` (security, data loss, correctness) or `advisory` (improvement, refactoring) |
| `validation_note` | block | Decision (`validated`, `reclassified`, `merged`, `rejected`), the rationale, and the cross-reference. Placed between the finding heading and the field table. |

### Classification Guide

- **mandatory**: Security vulnerabilities, data loss risks, correctness issues, spec deviations requiring immediate fix
- **advisory**: Code quality improvements, refactoring suggestions, best practice enhancements
- **verification**: `observed` — the runtime consequence was executed and seen. `unverified` — it was not, and no band is asserted for a consequence nobody watched. A finding filed `unverified` is still assigned a severity: the band is composed from the structural fact under the owning phase's own severity table, which is what "composed from the structural fact" means and what this report format does not decide. What records that the consequence was not observed is the field, never the absence of a band.
- **decision**: `validated`, `reclassified`, `merged` or `rejected`, recorded in `validation_note`.
  A decision is never a severity and is never recorded in the severity column; a rejected finding
  keeps the severity it carried and a reclassified finding keeps it.