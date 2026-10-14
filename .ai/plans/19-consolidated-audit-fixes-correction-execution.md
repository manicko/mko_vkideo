# 19 — Consolidated Audit Fixes: Correction Execution

> **Status:** `ready-for-execution`
>
> **Purpose:** Execute the fixes identified in the audit problems report
> (`18-consolidated-audit-fixes-audit-problems.md`) against the live HEAD
> (`a03f823`).
>
> **Source context:** The auditor's full inspection report is at
> `.ai/audit/problems/18-consolidated-audit-fixes-inspection-report.md`.
>
> **All findings were verified** at HEAD `a03f823` (2 commits ahead of `151ea9f`).
>
> ### Binding decisions (carried from plan 18)
>
> | ID | Decision |
> |---|---|
> | `DEC-X` | Exit code 130 is retained (six-row contract: 0/1/2/3/130). |
> | `DEC-Y` | P12-B11 re-scoped, not dropped. |
> | `DEC-Z` | P18-B14 owns `services/downloader.py::__all__` — already completed by `151ea9f`. |
> | `DEC-V` | Risk tiering and agent-assignment rule. |
> | `DEC-W` | No speculative redesign; `downloader_throttle.py` split stays last in W6. |

---

## §1 Scope

### Fix-plan issues (from audit problems §2, §3, §5, §9)

| Issue | Type | Scope | Severity |
|---|---|---|---|
| C12-VIOLATION | Rule breach | 5 test files unformatted after `151ea9f` | High (universal gate) |
| P18-B14-STALE | Plan staleness | P18-B14 marked in-progress; YAML + §4.2 stale | Medium |
| READS-ONLY-STALE | Plan staleness | `reads_only` paths point to archived plans | Low |
| APPENDIX-STALE | Plan staleness | R4 claim, `__all__` count, gate table, mypy pin contradiction | Medium |
| P18-B28-PARTIAL | Code incomplete | `URLBackoffCoordinator` not moved to `retry_policies.py` | High |
| STALE-COMMENT | Code defect | `downloader.py` comment misattributes `_retry_429_with_backoff` to `downloader_throttle.py` | Low |

### Documentation issues (from audit problems §4)

| # | File | Problem | Fix |
|---|---|---|---|
| Doc-1 | `docs/01-tools/api-reference.md` | `sanitize_title` (nonexistent) | → `sanitize_filename_component` |
| Doc-2 | `docs/01-tools/vkdownloader-overview.md:130` | "two commands" | → "three commands" (download, batch, clean-cookies) |
| Doc-3 | `docs/01-tools/vkdownloader-overview.md:16` | "direct HLS-to-MP4 conversion" | → "merge engine for stitching segments" |
| Doc-4 | `docs/11-guides/configuration.md:75` | `auto` + `BROWSER`: "No browser involvement" | → browser IS launched |
| Doc-5 | `docs/00-overview/doc-maintenance-rules.md:101-104` | `core/`, `app.py`, `logging.getLogger` | → `src/vkdownloader/`, `cli.py`, `structlog.get_logger` |
| Doc-6 | `docs/00-overview/doc-maintenance-rules.md:9` | `related: overview.md` | → `related: vkdownloader-overview` |
| Doc-7 | `docs/01-tools/installation.md:101,107` | ruff `src/` only | → `src tests` |

---

## §2 Execution Order

```
Block 1 (C12 fix)        ─→  Implementor (trivial)
                              │
Block 2 (P18-B28)             ▼
Researcher → Implementor → Validator

Block 3 (plan staleness) ─→  Implementor (metadata)
Block 4 (docs)               │
                             └── in parallel: Doc-specialist + Implementor (different files)
```

### Ordering rationale

1. **Block 1 first** — C12 is a universal integrity gate. Format must be GREEN
   before any other code change, because the gate checks `src tests` in full.
2. **Block 2 after Block 1** — P18-B28 touches `services/downloader_throttle.py`,
   `services/retry_policies.py`, `services/downloader.py`. Must start from a green
   format gate.
3. **Block 3 after Block 1–2** — Plan-file corrections must reflect the post-fix
   state (format GREEN, P18-B14 DONE, `__all__` at 25 names, P18-B28 complete).
4. **Block 4** — Pure documentation changes in `docs/`. Independent of code. May
   run in parallel with Block 3 (different file trees).

### Agent assignments

| Block | Agents | Rationale |
|---|---|---|
| Block 1 | Implementor | Just run `ruff format`; no design uncertainty |
| Block 2 | Researcher → Implementor → Validator | Placement of `URLBackoffCoordinator` is a design decision the auditor flagged as unmeasured; 8 external gates must be verified |
| Block 3 | Implementor | Pure metadata edits to `.md`/`.yaml` |
| Block 4 | Doc-specialist | 7 independent doc fixes |

> **Constraint:** Max 2 parallel subagents. Never parallel Implementor agents.

---

## §3 Block briefs

### Block 1 — Fix C12 formatting gate violation

```yaml
id: fix-c12
title: "Restore green format gate (Rule C12)"
priority: critical
depends_on: []
agents: [Implementor]
description: >
  Commit `151ea9f` left 5 test files unformatted, turning the universal
  format gate RED. Run `uv run ruff format src tests` to format all files,
  then commit only the reformatted files.
files:
  - tests/test_cli.py
  - tests/test_config.py
  - tests/test_downloader_throttle.py
  - tests/test_hls_downloader.py
  - tests/test_segment_downloader.py
acceptance_criteria:
  - "uv run ruff format --check src tests → exit 0, 56 files formatted"
  - "git diff contains ONLY formatting changes (no logic changes)"
  - "no test count change; pytest still ≥ 1097 passed, 3 skipped"
  - "git status --porcelain -- src tests docs pyproject.toml shows only the 5 reformatted files"
gates:
  - "uv run ruff format --check src tests"
  - "uv run pytest -q -rs"
commit_scope: explicit paths only (5 test files)
```

### Block 2 — Complete P18-B28: downloader_throttle.py split

```yaml
id: fix-p18-b28
title: "P18-B28 — complete downloader_throttle.py split"
priority: high
depends_on: [fix-c12]
agents: [Researcher, Implementor, Validator]
description: >
  Commit `723cb16` moved retry *functions* to `retry_policies.py` but left
  `URLBackoffCoordinator` (class managing per-URL backoff state + shutdown
  signaling) in `downloader_throttle.py` (line 87). The auditor flagged
  this as a design decision: the class manages backoff *state* which
  overlaps with but is distinct from retry *policy*.

  Phase A (Researcher): Read source plan B4 (archived at
  `done/14-code-quality-audit-fixes_done.md`) to understand the original
  split intent and the 8 external gates. Determine the correct placement
  of `URLBackoffCoordinator`. Record D7/D8 choices and their bases.

  Phase B (Implementor): Move `URLBackoffCoordinator` to the location
  determined by research, update all imports in `downloader.py` and any
  other consumers, fix the stale comment in `downloader.py` about
  `_retry_429_with_backoff` ownership.

  Phase C (Validator): Re-measure all 8 external gates. Confirm mypy
  src+tests = 0, all universal gates green.
files:
  - src/vkdownloader/services/downloader_throttle.py
  - src/vkdownloader/services/retry_policies.py
  - src/vkdownloader/services/downloader.py
acceptance_criteria:
  - "URLBackoffCoordinator placed in the correct module"
  - "all imports updated; no broken references"
  - "stale comment in downloader.py about _retry_429_with_backoff fixed"
  - "all 8 external gates re-measured post-fix and green"
  - "mypy src tests = 0 errors"
  - "ruff format --check src tests = exit 0"
  - "pytest = 1097 passed, 3 skipped (composition unchanged)"
gates: [U, mypy src tests, "8 external gates"]
```

### Block 3 — Fix plan file staleness

```yaml
id: fix-plan-staleness
title: "Update plan file 18 + P18-B14.yaml to reflect completed work"
priority: high
depends_on: [fix-c12, fix-p18-b28]
agents: [Implementor]
description: >
  The plan file `18-consolidated-audit-fixes-execution_fix.md` and the
  task file `P18-B14.yaml` contain stale claims. Update them to reflect
  the actual state at HEAD.
files:
  - .ai/plans/18-consolidated-audit-fixes-execution_fix.md
  - .ai/plans/tasks/P18-B14.yaml
acceptance_criteria:
  - "P18-B14 marked DONE in §4.2 and in P18-B14.yaml"
  - "reads_only paths updated to .ai/plans/done/ with correct archived filenames"
  - "gate table §2.1 updated: ruff format is GREEN after Block 1"
  - "appendix R4 claim updated: --log-file reference removed by 3cc2897"
  - "appendix __all__ claim updated: 25 names (was 20 + 6 omitted)"
  - "mypy pin contradiction (§5.1 V9 vs §3 P18-B30) resolved"
  - "P18-B28 status updated to reflect completion after Block 2"
gates: []
commit_scope: explicit paths only
```

### Block 4 — Fix 7 documentation issues

```yaml
id: fix-docs
title: "Correct 7 documentation inaccuracies"
priority: medium
depends_on: []
agents: [Doc-specialist]
description: >
  Fix all 7 doc issues verified by the auditor. Each is a targeted text
  correction; no structural doc changes.
files:
  - docs/01-tools/api-reference.md
  - docs/01-tools/vkdownloader-overview.md
  - docs/11-guides/configuration.md
  - docs/00-overview/doc-maintenance-rules.md
  - docs/01-tools/installation.md
acceptance_criteria:
  - "Doc-1: api-reference.md uses sanitize_filename_component, not sanitize_title"
  - "Doc-2: vkdownloader-overview.md says 'three commands' with clean-cookies listed"
  - "Doc-3: vkdownloader-overview.md line 16 says 'merge engine', not 'direct HLS-to-MP4'"
  - "Doc-4: configuration.md says browser IS launched for auto+BROWSER"
  - "Doc-5: doc-maintenance-rules.md uses src/vkdownloader/, cli.py, structlog.get_logger"
  - "Doc-6: doc-maintenance-rules.md related → vkdownloader-overview"
  - "Doc-7: installation.md ruff commands use src tests"
gates: []
commit_scope: explicit paths only
```

---

## §4 Constraints inherited from plan 18

- **C1** — Symbols only, no `file:line` in messages
- **C2** — `structlog.get_logger`, not stdlib `logging`
- **C3** — All enums in `models/enums.py`
- **C4** — `services/downloader.py` re-exports are plumbing, never the remedy
- **C5** — Packaging-frozenset single-writer lock
- **C6** — `create=True` appears 0 times in `tests/`
- **C7** — `asyncio_mode` is strict; every `async def` test needs `@pytest.mark.asyncio`
- **C8** — `git add <explicit paths>` only
- **C9** — `.ai/audit/**` is read-only (inspection report and audit problems file)
- **C10** — `AGENTS.md` does not exist; `.kilo/rules/project.md` binds
- **C11** — `mypy src` is the type gate; never relax
- **C12** — Format gate green at every block boundary
