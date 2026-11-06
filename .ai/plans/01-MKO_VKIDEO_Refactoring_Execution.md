# Execution Plan — MKO VKIDEO HLS Download Reliability Refactoring

**Source plan:** `.ai/plans/MKO_VKIDEO_Refactoring_Plan.md`
**Baseline SHA:** `665c6ac0e8e8a9d26b69ae12e608db829ba212a2`
**Current HEAD:** `283f4157ae6d7dbb6f1a3df32e5ebad5c81c0da4`
**Code context:** produced by Auditor (session). See auditor report in conversation.

## Blocks (from source plan §3)

| # | Block | Status | Depends |
|---|-------|--------|---------|
| A | Baseline, commit forensics, test harness | Partial (A1 forensics done by auditor; A2/A3 deferred to J) | none |
| B | Preserve partials, prohibit destructive cleanup | Complete | A |
| C | Diagnostics | Complete | A |
| D | output/tmp workspace | Complete | B, C |
| E | Durable checkpoint | Complete | B, D |
| F | Exact quality refresh | Complete | E |
| G | Retry state machine | Complete | C, E, F |
| H | FFmpeg transport | Complete | D–G |
| I | Progress/ETA | Complete | C, E, G |
| J | Final validation/release | Pending (planner done) | all |

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

## Block I — task tracking

Task spec: `.ai/tasks/task_I_progress_eta.yaml` (id: `block_i_progress_eta`).

- [x] I researcher (progress architecture map, gaps, proposed ProgressSnapshot/JobPhase, ETA policy, minimal change set, risks, RED test plan) — context captured in `.ai/audit/block_i_research.md`
- [x] I planner (exact edit list, interface contracts) — task spec written
- [ ] I validator RED (tests asserting trustworthy progress/ETA; expect failure on old code)
- [ ] I implementor (code changes + commit)
- [ ] I auditor (unit semantics/race review)
- [ ] I validator GREEN (run tests)

### Block I execution commands
- `uv run pytest tests/test_progress.py tests/test_hls_downloader.py tests/test_progress_display.py tests/test_downloader_throttle.py tests/test_batch_downloader.py tests/test_segment_downloader.py tests/test_packaging.py -q`
- `uv run ruff check src tests`
- `uv run ruff format --check src tests`
- `git diff --check`
- Commit message: `feat(progress): trustworthy progress, bytes, speed and ETA (Block I)`

## Block J — task tracking

Task spec: `.ai/tasks/task_J_final_validation_release.yaml` (id: `block_j_final_validation_release`).

- [x] J planner (release checklist, acceptance matrix, verification commands, known gaps) — task spec written
- [ ] J researcher (dependency/version cross-check)
- [ ] J validator (all tests + benchmarks)
- [ ] J auditor (independent final review)
- [ ] J implementer (only targeted fixes)
- [ ] J validator (rerun final matrix)

### Block J execution commands
- `uv sync`
- `uv run pytest -q`
- `uv run ruff check .`
- `uv run ruff check src tests`
- `uv run ruff format --check .`
- `uv run ruff format --check src tests`
- `uv run mypy src`
- `git diff --check`
- `uv run pytest tests -q`
- `ffprobe -v error -show_entries format=duration,size -show_entries stream=index,codec_type,codec_name,width,height -of json "C:\\data\\Video\\Shows\\<completed-file>.mp4"`
- Commit message (targeted fixes): `fix(integration): close Block J verification gaps (Block J)`

## Notes
- Scope decisions: A2 HTTP fixture server and A3 baseline measurements deferred to Block J to prioritize P0 data preservation. Documented here per workflow.
- Max 2 parallel subagents; no background. Implementor runs alone.
