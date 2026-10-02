---
name: audit-findings
description: Structured findings template for audit phase output
agent: auditor
alwaysApply: false
---

# Phase N Audit Findings — {Phase Name}

**Executor:** auditor
**Template:** {phase-template-file}
**Status:** {pending|in-progress|complete}
**Validated:** {yes|no}

---

## Findings

### {ID}: {Title}

**Decision:** {validated | reclassified | merged | rejected} · {decision_detail}

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

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |

## Mandatory Fixes

{List all findings classified as mandatory}

## Advisory Recommendations

{List all findings classified as advisory}

## Doc Updates Needed

{List all findings classified as DOC-UPDATE type}

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
| `decision` | enum | `validated` · `reclassified` · `merged` · `rejected` |
| `decision_detail` | string | Optional rationale and cross-references; required for every decision except `validated` |

### Classification Guide

- **mandatory**: Security vulnerabilities, data loss risks, correctness issues, spec deviations requiring immediate fix
- **advisory**: Code quality improvements, refactoring suggestions, best practice enhancements
- **verification**: `observed` — the runtime consequence was executed and seen. `unverified` — it was not, and no band is asserted for a consequence nobody watched. A finding filed `unverified` is still assigned a severity: the band is composed from the structural fact under the owning phase's own severity table, which is what "composed from the structural fact" means and what this report format does not decide. What records that the consequence was not observed is the field, never the absence of a band.