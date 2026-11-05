# Execution Plan — MKO VKIDEO HLS Download Reliability Refactoring

**Source plan:** `.ai/plans/MKO_VKIDEO_Refactoring_Plan.md`
**Baseline SHA:** `665c6ac0e8e8a9d26b69ae12e608db829ba212a2`
**Current HEAD:** `35114866e8ae6eda3f9cf3009f3bce4a6705979d`
**Code context:** produced by Auditor (session). See auditor report in conversation.

## Blocks (from source plan §3)

| # | Block | Status | Depends |
|---|-------|--------|---------|
| A | Baseline, commit forensics, test harness | Partial (A1 forensics done by auditor; A2/A3 deferred) | none |
| B | Preserve partials, prohibit destructive cleanup | In progress | A |
| C | Diagnostics | Pending | A |
| D | output/tmp workspace | Pending | B, C |
| E | Durable checkpoint | Pending | B, D |
| F | Exact quality refresh | Pending | E |
| G | Retry state machine | Pending | C, E, F |
| H | FFmpeg transport | Pending | D–G |
| I | Progress/ETA | Pending | C, E, G |
| J | Final validation/release | Pending | all |

## Block B — task tracking

Task spec: `.ai/tasks/task_B_preserve_partials.yaml` (id: `block_b_preserve_partials`).

- [x] B researcher (read-only inspection of cleanup paths + tests)
- [x] B planner (exact edit list, interface contracts) — task spec written
- [ ] B validator RED (tests asserting preservation; expect failure on old code)
- [ ] B implementor (code changes + commit)
- [ ] B auditor (data-loss/security review)
- [ ] B validator GREEN (run tests)

### Block B execution commands
- `uv run pytest tests/test_segment_downloader.py tests/test_hls_downloader.py tests/test_ffmpeg_utils.py -q`
- `uv run ruff check src tests`
- `uv run ruff format --check src tests`
- `git diff --check`
- Commit message: `fix(segment-downloader): preserve partials on failure (Block B)`

## Notes
- Scope decisions: A2 HTTP fixture server and A3 baseline measurements deferred to Block J to prioritize P0 data preservation. Documented here per workflow.
- Max 2 parallel subagents; no background. Implementor runs alone.
