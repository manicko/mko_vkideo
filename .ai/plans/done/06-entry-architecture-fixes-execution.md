# Execution Plan — Entry Architecture Audit Fixes (Blocks 7, 8, 13, AGENTS.md fix)

> **Source plan:** `.ai/plans/05-entry-architecture-audit-fixes_fix.md`
> **User decision:** Implement the plan's remaining blocks 7, 8, 13, and the partial
> 9/10 fix (the broken `AGENTS.md` reference in `audit-refine.md`). Blocks 11 and 12
> remain deferred per D7=DEFER. Blocks 9 and 10 are functionally complete; only the
> AGENTS.md reference fix remains.
> **Baseline:** HEAD `b770e83`, test suite: 948 passed, 3 skipped (POSIX-only killpg skips).

## Scope

### IN — blocks to implement

1. **Block 7** — Package-root and deferred-import hygiene (ENT-005, ENT-007, ENT-009)
   - Empty four `__init__.py` roots (`services`, `utils`, `models`, `infrastructure`) to docstrings
   - Hoist deferred import in `exceptions.py` (`InvalidVideoUrlError.__init__`) to module scope
   - Create `tests/test_import_graph.py` (isolated import + re-export invariant tests)
   - Add `tests/test_import_graph.py` to `EXPECTED_SDIST_ENTRIES` in `tests/test_packaging.py`
   - Update `docs/STRUCT.md` `utils/` listing line (remove stale 3-name export)

2. **Block 8** — Download-timeout single source of truth (ENT-010)
   - Rename `_DEFAULT_DOWNLOAD_TIMEOUT` → `DEFAULT_DOWNLOAD_TIMEOUT` in `downloader_throttle.py`
   - Replace 9 hardcoded `300`/`300.0` literals with the constant (6 in `segment_downloader.py`, 3 in `ffmpeg_utils.py`)
   - Add import in `ffmpeg_utils.py` and `segment_downloader.py`
   - Add invariant tests to `tests/test_config.py`

3. **Block 13** — Structural documentation reconciliation (ENT-013 cheap half)
   - Measure import cost on post-Block-7 tree
   - Update `docs/STRUCT.md` entry-layer description line (record measured cost)
   - Verify `docs/11-guides/configuration.md` (expected: no change)

4. **AGENTS.md fix** — Partial Block 9/10
   - Repoint `audit-refine.md` line 19 from `AGENTS.md` to `.kilo/rules/project.md` + `.kilo/rules/commands.md`
   - Make consistent with `audit-multi-phase.md` lines 43–44

### OUT — explicitly not in scope
- Block 11 (ENT-008, batch presentation) — DEFERRED per D7
- Block 12 (ENT-004, signal-handler ownership) — DEFERRED per D7
- Block 9 full rework (template label changes, decision slot) — functionally complete
- Block 10 full rework (identifier prefix, gate, counters) — functionally complete

## Execution order

```
Step 1: AGENTS.md fix (audit-refine.md)        — trivial, independent, 1 file
Step 2: Block 7 (package-root hygiene)          — prerequisite for Block 13
Step 3: Block 8 (timeout constant)              — independent of Block 7
Step 4: Block 13 (structural docs)              — depends on Block 7 (import cost measurement)
Step 5: Doc-specialist update                    — after all implementation
Step 6: Validator final review                  — after all implementation
```

## Integration invariants

1. `.ai/` exclusion: no block stages anything under `.ai/` except the tracked template (Block 9). The AGENTS.md fix touches `.kilo/commands/audit/audit-refine.md` — a tracked file, not `.ai/audit/`.
2. Packaging gate: Block 7 adds exactly one new file (`tests/test_import_graph.py`) to `EXPECTED_SDIST_ENTRIES`.
3. No new module under `src/`.
4. `git add` by explicit path only.
