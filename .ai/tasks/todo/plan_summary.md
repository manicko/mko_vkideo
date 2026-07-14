# Rollout Plan Summary

## Mandatory Fixes (Must Address Before Production)

| Task ID | Finding ID | Priority | Description |
|--------|------------|----------|-------------|
| task_001 | CLI-001/CFG-001/DF-001/TST-001/QLT-001/SEC-001 | high | Fix test assertion for ssl_verify default |
| task_002 | CLI-002 | medium | Move _sanitize_title to utils/security.py |
| task_003 | CFG-002 | medium | Add DownloadMethod and CookieSource to exports |
| task_004 | CLI-003/SRV-002/QLT-008 | medium | Refactor perform_download signature |
| task_005 | SRV-002 | low | Remove dead code functions |

## Advisory Improvements (Recommended)

| Task ID | Finding ID | Priority | Effort | Description |
|--------|------------|----------|--------|-------------|
| task_006 | QLT-003 | low | small | Replace Any with TYPE_CHECKING imports |
| task_007 | QLT-004 | medium | small | Replace bare Exception catches |
| ~~task_008~~ ~~task_009~~ | SRV-003/QLT-002/STR-007 | high | large | **DONE** Split downloader.py god module |
| task_010 | DF-002 | low | small | Fix batch command Settings instantiation |
| task_011 | QLT-009 | low | trivial | Run ruff format |

## Execution Order

```
Group 1 (No Dependencies - Can Run in Parallel):
  001, 002, 003, 004, 005, 006, 007, 010, 011

DONE Group 2 (Depends on task_004):
  008 → 009 (module split with verification) - COMPLETED
```

## Risk Assessment

### High Risk
- **task_008**: Module splitting affects core download functionality. Requires careful extraction and verification.

### Medium Risk
- **task_004**: Changes to perform_download affect download flow. Must ensure quality selection works correctly.
- **task_007**: Exception handling changes could mask errors if not done carefully.

### Low Risk
- **task_001, 002, 003, 005, 006, 010, 011**: Isolated changes with minimal impact.

### Task Dependencies Summary
- task_008 depends on task_004 because the PerformDownload signature changes affect how functions are split during refactoring.

## Notes

- Documentation-only fixes (INT-001, SRV-005, SRV-006, CFG-003) were excluded as they don't require implementation tasks.
- Rejection reasons (SRV-001, CLI-004/CLI-004/SRV-004, STR-006, STR-008, TST-003, TST-004, TST-005) were respected - no tasks created.
- Advisory items remain unassigned as optional improvements.