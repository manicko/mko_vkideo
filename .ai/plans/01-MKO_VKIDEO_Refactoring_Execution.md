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
| D | output/tmp workspace | In progress (planner done) | B, C |
| E | Durable checkpoint | Pending | B, D |
| F | Exact quality refresh | Pending (planner done) | E |
| G | Retry state machine | Pending (planner done) | C, E, F |
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

## Block D — task tracking

Task spec: `.ai/tasks/task_D_workspace.yaml` (id: `block_d_workspace`).

- [x] D researcher (yt-dlp -P semantics + Windows; filelock verified importable)
- [x] D planner (workspace contract/migration) — task spec written
- [ ] D validator RED (tests asserting workspace routing; expect failure on old code)
- [ ] D implementor (code changes + commit)
- [ ] D auditor (path-security/data preservation review)
- [ ] D validator GREEN (run tests)

### Block D execution commands
- `uv run pytest tests/test_workspace.py tests/test_ytdlp_downloader.py tests/test_segment_downloader.py tests/test_downloader.py tests/test_security.py -q`
- `uv run ruff check src tests`
- `uv run ruff format --check src tests`
- `git diff --check`
- Commit message: `feat(workspace): isolate per-job temp under output/tmp and route yt-dlp artifacts (Block D)`

## Block E — task tracking
Task spec: `.ai/tasks/task_E_checkpoint.yaml` (id: `block_e_checkpoint`).

- [x] E researcher (HLS identity) — context captured in task spec
- [x] E planner (schema + versioned migration) — task spec written
- [ ] E validator RED (tests asserting checkpoint identity/quarantine; expect failure on old code)
- [ ] E implementor (code changes + commit)
- [ ] E auditor (data-loss/security review)
- [ ] E validator GREEN (run tests)

### Block E execution commands
- `uv run pytest tests/test_checkpoint.py tests/test_hls_parser.py tests/test_segment_downloader.py tests/test_hls_downloader.py -q`
- `uv run ruff check src tests`
- `uv run ruff format --check src tests`
- `git diff --check`
- Commit message: `feat(checkpoint): durable per-segment checkpoint and safe content identity (Block E)`

## Block F — task tracking
Task spec: `.ai/tasks/task_F_quality_refresh.yaml` (id: `block_f_quality_refresh`).

- [x] F researcher (quality/refresh architecture map, gaps, proposed StreamBinding/refresh_stream/select_exact_or_fail/QualityMismatchError, call-site updates, checkpoint interface, risks, RED test plan)
- [x] F planner (exact edit list, interface contracts) — task spec written
- [ ] F validator RED (tests asserting exact-quality refresh and browser unknown-height rejection; expect failure on old code)
- [ ] F implementor (code changes + commit)
- [ ] F auditor (data-loss/security review)
- [ ] F validator GREEN (run tests)

### Block F execution commands
- `uv run pytest tests/test_quality_refresh.py tests/test_segment_downloader.py tests/test_hls_downloader.py tests/test_ytdlp_downloader.py tests/test_downloader.py -q`
- `uv run ruff check src tests`
- `uv run ruff format --check src tests`
- `git diff --check`
- Commit message: `feat(quality): exact-quality refresh without silent downgrade (Block F)`

## Block G — task tracking
Task spec: `.ai/tasks/task_G_retry_state_machine.yaml` (id: `block_g_retry_state_machine`).

- [x] G researcher (retry layers + status semantics) — context captured in task spec
- [x] G planner (state diagram) — task spec written
- [ ] G validator RED (tests asserting bounded explicit retries; expect failure on old code)
- [ ] G implementor (code changes + commit)
- [ ] G auditor (data-loss/security review)
- [ ] G validator GREEN (run tests)

### Block G execution commands
- `uv run pytest tests/test_state_machine.py tests/test_ytdlp_downloader.py tests/test_segment_downloader.py tests/test_downloader.py tests/test_packaging.py -q`
- `uv run ruff check src tests`
- `uv run ruff format --check src tests`
- `git diff --check`
- Commit message: `feat(retry): replace nested retries with observable download state machine (Block G)`

## Notes
- Scope decisions: A2 HTTP fixture server and A3 baseline measurements deferred to Block J to prioritize P0 data preservation. Documented here per workflow.
- Max 2 parallel subagents; no background. Implementor runs alone.
