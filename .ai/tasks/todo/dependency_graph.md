# Dependency Graph / Execution DAG

```
Task Dependency Analysis for vkdownloader Rollout Plan
```

## Execution Groups (Parallelizable)

### Group 1: Foundational Fixes (No Dependencies - Can Run in Parallel)
- `task_001_fix_test_assertion_ssl_verify` - Fix failing test
- `task_002_move_sanitize_title_to_security` - Move function to correct layer
- `task_003_add_enum_exports` - Complete public API exports
- `task_004_refactor_perform_download_signature` - Eliminate logic duplication
- `task_005_remove_dead_code_functions` - Remove unused functions
- `task_006_replace_any_with_typechecking` - Type safety improvement
- `task_007_replace_bare_exception_catches` - Error handling improvement
- `task_010_fix_batch_command_settings_instantiation` - Lint fix
- `task_011_run_ruff_format` - Formatting fix

### Group 2: God Module Refactoring (Depends on task_004)
- ~~task_008_split_downloader_module~~ - **DONE** - Split 1130-line downloader.py into focused modules
  - Depends on: task_004 (signature changes affect module structure)

- ~~task_009_verify_module_split~~ - **DONE** - Verification task
  - Depends on: task_008

## Dependency Matrix

| Task | Depends On | Blocks | Risk Level |
|------|------------|--------|------------|
| 001 | - | - | Low |
| 002 | - | - | Low |
| 003 | - | - | Low |
| 004 | - | 008 | Medium |
| 005 | - | - | Low |
| 006 | - | - | Low |
| 007 | - | - | Medium |
| ~~008~~ | 004 | 009 | ~~High~~ DONE |
| ~~009~~ | 008 | - | ~~Medium~~ DONE |
| 010 | - | - | Low |
| 011 | - | - | Low |

## Cross-Phase Duplicates Handled

The following findings were duplicates across phases and consolidated:
- CLI-001, CFG-001, DF-001, TST-001, QLT-001, SEC-001 → Single task_001 for test fix
- CLI-002, CFG-002 → task_002 and task_003 (separate but related)
- SRV-003, QLT-002, STR-007 → task_008 (module split)
- SRV-002, QLT-008 → task_004 (perform_download refactor) + task_005 (dead code removal)

## Advisory Recommendations (Not Created As Tasks)

The following were marked as advisory and can be addressed independently:
- CFG-004: download_dir validator (optional improvement)
- QLT-005: asyncio.to_thread for file I/O (optional, current code acceptable)
- QLT-006: Unused lambda arguments (incorporated into QLT-007)
- QLT-007: Global state in signal handlers (optional refactoring)
- TST-002: Tautological integration tests (optional removal)
- TST-003: Skipped security test (documented limitation, optional)
- TST-006: Weak test assertions (optional improvement)
- DF-004: Inconsistent Settings instantiation (style issue, not functional)