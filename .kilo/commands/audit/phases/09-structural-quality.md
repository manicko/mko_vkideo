---
name: 09-structural-quality
status: complete
validated: no
executor: auditor
problems-only: true
---

# Phase 09 Audit — Structural Code Quality

## Output Mode

`problems-only: true` — **only problems, bugs, and deviations are documented.**

- **Do NOT** write sections that say "X is correct" or "no issues found in Y".
- **Do NOT** include checklist rows where the check passes — omit them entirely.
- If a dimension has zero findings after investigation, **omit the dimension entirely**.
- Every finding must be actionable: it describes a real problem, its evidence (code/logs/output), and its impact.

---

## Objective

Audit the codebase for **structural code quality** — the shape and complexity of functions, methods, and control flow. This phase targets the "arrow code" / "pyramid of doom" anti-pattern, excessive nesting, bloated functions, and other structural issues that degrade readability and maintainability.


---

## Discovery Stage

Before performing audit checks, discover the structural landscape:

1. **File Inventory** — List all source files with line counts. Identify files exceeding 300 lines (potential god modules).
2. **Function/Method Inventory** — For each source file, list all functions and methods with their line counts. Identify any function exceeding 50 lines.
3. **Nesting Depth Scan** — For each function/method, measure the maximum nesting depth of `if`/`for`/`while`/`try`/`with` blocks. Identify any function with nesting depth > 3.
4. **Control Flow Scan** — Identify `for...else` usage, deeply nested `if/else` chains, and functions with multiple return points.

---

## Mandatory Runtime Verification

**Before evaluating any checklist item, you MUST complete these steps. Skip only if a step is impossible — document why.**

### Step R1 — Run Radon Cyclomatic Complexity

Run `uv run radon cc src/ -a -nc` to get cyclomatic complexity for all functions and methods.

- Record every function with complexity rank C or worse (≥11).
- Record the total average complexity.

### Step R2 — Run Radon Maintainability Index

Run `uv run radon mi src/ -s` to get the maintainability index.

- Record any file with MI rank B or C.
- Record the actual MI scores.

### Step R3 — Function Length Analysis

For each source file, count lines per function/method (excluding blank lines and comments). Identify any function/method exceeding 50 lines.

### Step R4 — Nesting Depth Analysis

For each function/method, count the maximum indentation depth of control flow statements (`if`, `for`, `while`, `try`, `with`). Identify any function with max nesting depth > 3.

### Step R5 — Control Flow Pattern Search

Search for structural anti-patterns:
- `for...else` usage (often confusing, better written with a flag or guard)
- `if/else` chains that could be guard clauses or lookup tables
- Functions with > 3 return statements
- Functions with > 5 parameters

---

## Audit Scope

All source code files in `src/**/`. Focus on structural properties: complexity, length, nesting, and control flow patterns.

---

## Audit Dimensions

### 1. Cyclomatic Complexity

| Check | Description |
|-------|-------------|
| Per-function CC ≤ 10 | No function/method should have cyclomatic complexity exceeding 10 (Radon rank A or B). |
| Average CC ≤ 5 | The average cyclomatic complexity across the project should be ≤ 5. |
| No CC rank D or worse | No function should have complexity ≥ 21 (rank D, E, or F). |

**Evidence required:** `radon cc` output with scores and rankings.

### 2. Nesting Depth

| Check | Description |
|-------|-------------|
| Max nesting depth ≤ 3 | No function should have control flow nested more than 3 levels deep (e.g., `if` inside `for` inside `if` inside `def` = 3 levels). |
| Guard clauses preferred | Deeply nested `if/else` should be replaced with early returns (guard clauses) where possible. |

**Evidence required:** File:line references with nesting depth measurement.

### 3. Function/Method Length

| Check | Description |
|-------|-------------|
| Max 50 lines per function | No function or method should exceed 50 lines (excluding blank lines and comments). |
| Max 300 lines per file | No source file should exceed 300 lines (excluding blank lines and comments). |

**Evidence required:** File:line references with line counts.

### 4. Control Flow Patterns

| Check | Description |
|-------|-------------|
| No `for...else` anti-pattern | `for...else` is often confusing. Use explicit flags or guard variables instead. |
| No excessive return points | Functions should have ≤ 3 return statements. More indicates complex control flow. |
| No excessive parameters | Functions should have ≤ 5 parameters. More indicates the function does too much. |
| No arrow code | Deeply nested `if/else` chains (pyramid of doom) should be refactored using guard clauses, extraction, or polymorphism. |

**Evidence required:** File:line references with pattern description.

### 5. Cognitive Load Indicators

| Check | Description |
|-------|-------------|
| Single responsibility per function | Each function does one thing. If a function has multiple `for` loops, multiple `try` blocks, or multiple `if` branches at the same level, it likely does too much. |
| Linear flow preferred | Functions should read top-to-bottom. Deeply nested `if/else` trees that branch on multiple conditions are harder to follow than sequential guard clauses. |

**Evidence required:** File:line references with description of cognitive load.

---

## Report Output

Write findings to: `.ai/audit/09-structural-quality/findings.md` using template `.ai/audit/templates/audit-findings.md`.

Use prefix `STR-` for finding IDs.

**`problems-only: true` rules:**
- The report contains **only findings** — real problems discovered during investigation.
- Do NOT include sections, dimensions, or checklist rows where everything is correct.
- If after completing all Runtime Verification steps and all Audit Dimensions, no problems were found, write a single line: `No problems found in this phase.`
- Every finding MUST include:
  1. **Runtime evidence** — radon output, file:line, nesting depth measurement, line counts.
  2. **Not just:** "function is too long" — show the exact function, its length, and the maintenance consequence (e.g., "hard to test in isolation", "multiple responsibilities").
  3. **Concrete refactoring recommendation** — what pattern to apply (extract method, guard clause, lookup table, etc.).

---

## Severity Classification Guide

| Severity | When to use |
|----------|-------------|
| CRITICAL | Function with CC > 20 AND nesting depth > 4 — bug-prone, untestable |
| HIGH | Function with CC > 15 OR nesting depth > 4 OR length > 100 lines — hard to maintain |
| MEDIUM | Function with CC 11-15 OR nesting depth 3-4 OR length 50-100 lines — should be refactored |
| LOW | Minor pattern violations (for-else, 4 returns) — advisory |

---

## References

- Radon complexity rankings: A (1-5), B (6-10), C (11-20), D (21-30), E (31-40), F (41+)
- Pylint defaults: max-complexity=10, max-nested-blocks=5, max-statements=50
- Refactoring.Guru: Arrow Code smell, Nested Conditionals smell
- Industry standard: function length ≤ 50 lines, nesting depth ≤ 3
