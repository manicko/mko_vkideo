# MKO VKIDEO — HLS Download Reliability Refactoring Plan

**Status:** Implementation specification for an LLM coding agent, with independent subagent gates  
**Repository:** https://github.com/manicko/mko_vkideo  
**Baseline (known stable):** `665c6ac0e8e8a9d26b69ae12e608db829ba212a2`  
**Current reported HEAD:** `35114866e8ae6eda3f9cf3009f3bce4a6705979d`  
**Target environment:** Windows, Python >= 3.14, yt-dlp, FFmpeg, long HLS downloads  
**Priority:** Data preservation > correctness > recoverability > observability > speed > ETA aesthetics

> **For the implementing LLM:** This is an execution plan, not permission to change everything at once. Work in the ordered blocks below. Create one focused PR/commit series per block; complete each acceptance gate before proceeding. Never delete or overwrite a user's existing `.part`, `.part-Frag*`, `.ytdl`, or `.ts` files as part of a refactor or failed download. All illustrative code must be reconciled with the actual APIs and tests at the checked-out revision, not pasted blindly.

---

## 0. User scenario and non-negotiable behavior

The user's long-standing invocation must continue to work unchanged:

```powershell
vkdownloader download "https://vkvideo.ru/video-225794656_456244209" --quality 1440 --method yt-dlp --output "C:\data\Video\Shows" --no-ssl-verify
```

Observed on current revision:

- The downloader repeatedly emits `[generic] Extracting URL`, `Downloading m3u8 manifest`, and `Destination` for the **same** HLS playlist.
- It repeatedly encounters `...mp4.part-FragNNN has already been downloaded`.
- Fragment progress grows toward `603/1895`, then jumps back to early fragments, with repeated `10/1895`, `12/1895`, etc.
- Estimated size jumps from tens of GiB to `1–2 TiB`; reported ETA becomes highly unstable, unavailable, or negative.
- A large working file can reach approximately 15 GiB, with hundreds/thousands of fragment files beside it.
- The user suspects CDN anti-bot behavior but has not supplied HTTP response codes or the process exit reason. **Do not treat anti-bot blocking as proven.**

### Required final layout

For output directory `C:\data\Video\Shows`, all new temporary/download files must live in an isolated, per-job folder below **`Shows\tmp`**, not directly in `Shows`:

```text
C:\data\Video\Shows\
├── Vechnaia_volia_..._225794656_456244209.mp4    # completed and validated ONLY
└── tmp\
    ├── jobs\
    │   └── video-225794656_456244209-q1440-<stable-id>\
    │       ├── state.json                         # atomic nonsecret checkpoint
    │       ├── lock                                # exclusive job lock
    │       ├── ytdlp\
    │       │   ├── ...mp4.part
    │       │   ├── ...mp4.part-Frag1
    │       │   ├── ...mp4.part-Frag2
    │       │   └── ...ytdl                          # if emitted by yt-dlp
    │       ├── segments\
    │       │   ├── 000001.ts
    │       │   └── 000002.ts
    │       ├── staging\
    │       │   └── ...mp4                         # completed but not yet promoted
    │       └── diagnostics\
    │           └── metadata.json                  # nonsecret, bounded
    └── logs\
        └── <job-id>.jsonl                         # persistent diagnostic log
```

The example filenames are schematic. Preserve the existing final basename resolution, Cyrillic titles, and video-ID suffix. **`tmp` must be inside the designated output directory and on the same filesystem as the final MP4** to allow atomic promotion. Once the final media is validated, remove only that job's owned intermediate artifacts, following an explicit retention policy. Retain error logs under `tmp\logs` even when a job succeeds, subject to rotation/retention. On any failure/cancellation, keep usable working files. In-progress files, including a growing multi-GiB `.part`, must never be written at output root.

### Invariants

1. **Never lose valid progress on retry, process interruption, transport switch, or application upgrade.**
2. **Never silently substitute another height** for explicitly selected `--quality 1440`.
3. **Never mix bytes from different media variants**, even when segment indexes are equal.
4. **Never expose live tokens, cookies, Authorization headers, signed URLs, or private browser profiles in logs/checkpoints/command-line arguments.**
5. **Do not degrade existing CLI usage:** `--method yt-dlp`, `--method auto`, `--output`, `--no-ssl-verify`, batch mode, cancellation, and paths containing Unicode must remain compatible.
6. **New direct FFmpeg mode is optional and explicit** until benchmarks prove safe automatic use. An FFmpeg transport fallback must not discard a yt-dlp partial file.
7. **Only one writer per job.** Multiple CLI processes must not concurrently mutate the same working files.
8. **No cleanup by broad glob of the output directory.** Clean only owned paths after an explicit successful commit.
9. **No false certainty in ETA.** Unknown ETA is acceptable. Negative time or terabyte-sized fantasy totals are not.
10. **Segment/file cache safety is more important than maximizing throughput.** Do not increase concurrency in order to mask failures.

---

## 1. Verified source findings vs. remaining hypotheses

This assessment is grounded in the source visible at the two provided SHAs. The implementing agent MUST perform a complete local diff as Block A; browser-based source inspection is not a substitute for a checked-out test run.

| Evidence | Stable `665c6ac` | Current `3511486` | Meaning |
|---|---|---|---|
| `services/downloader.py`, `perform_download()` | Explicit `DownloadMethod.FFMPEG` constructs `HLSDownloader` and, on failure, switches to segment download | Only `YTDLP` and `AUTO` branches | **Direct FFmpeg downloading existed in stable**, but not as automatic fallback for a command explicitly specifying `--method yt-dlp`. |
| `services/downloader.py`, `AUTO`/`YTDLP` branches | Delegate to `download_with_ytdlp_with_resume_fallback()` | Same high-level yt-dlp → segment path | Verify actual differences before claiming removal of FFmpeg caused the user's specific regression. |
| `services/ytdlp_downloader.py`, `download_with_ytdlp_with_resume_fallback()` | Contains retry/fallback logic | Contains outer retry loop plus internal yt-dlp retries | Retry layering can lead to repeated child-process launches; prove actual triggers with diagnostic logs. |
| `services/ytdlp_downloader.py`, `_attempt_segment_resume()` | Compare behavior in the local diff | On transition, explicitly unlinks `.part` and restarts via segment downloader | This can discard substantial downloaded data. |
| `services/ytdlp_downloader.py`, `_attempt_segment_resume()` | Compare quality selection | Refreshed browser streams only replace URL for `QualityKind.BEST`; exact height can retain old URL | Refresh is incomplete for `--quality 1440`. Browser streams may lack height metadata; do not blindly choose one. |
| `services/segment_downloader.py`, `download_hls_with_resume()` | Compare cleanup semantics | Non-success `finally` calls `_cleanup_segments(segments_dir)` | Destructive cleanup is incompatible with reliable resume. |
| `services/segment_downloader.py`, `_compute_playlist_signature()` | Diff required | Hashes full signed segment URL list; on mismatch deletes cached `.ts` | Token changes can invalidate otherwise compatible media. Must replace with strict, content-oriented identity checks. |
| `src/vkdownloader/config.py`, `Settings.log_file` | File logging existed | Defaults to `None`; when set, emits JSON structured logs | Logs are **not automatically written to a file**. |
| `services/ytdlp_downloader.py`, `_echo_ytdlp_line()` | Review per-version behavior | Child output is echoed to stderr and logged differently depending on `echo` | `--log-file` does not automatically guarantee every child transcript line is persisted. |
| Current `services/ytdlp_downloader.py`, `_build_ytdlp_cli_command()` | Diff required | Uses absolute `-o <output_file>`, `-N`, retries, `--throttled-rate` | Default yt-dlp fragment/temp files land near the final output. |

**Do not overclaim:** There are already retry/cleanup patterns in old code; the full commit-by-commit diff and reproducible tests must distinguish *new regressions* from *pre-existing defects*. The log alone cannot establish whether the first failure is HTTP 403, HTTP 429, an expired token, a read timeout, throttling, a playlist issue, or the subprocess state machine.

**Source anchors:**

- Stable direct FFmpeg dispatch: https://github.com/manicko/mko_vkideo/blob/665c6ac0e8e8a9d26b69ae12e608db829ba212a2/src/vkdownloader/services/downloader.py#L447-L523
- Current dispatch: https://github.com/manicko/mko_vkideo/blob/35114866e8ae6eda3f9cf3009f3bce4a6705979d/src/vkdownloader/services/downloader.py#L145-L194
- Current yt-dlp wrapper: https://github.com/manicko/mko_vkideo/blob/35114866e8ae6eda3f9cf3009f3bce4a6705979d/src/vkdownloader/services/ytdlp_downloader.py#L918-L1155
- Current yt-dlp command builder: https://github.com/manicko/mko_vkideo/blob/35114866e8ae6eda3f9cf3009f3bce4a6705979d/src/vkdownloader/services/ytdlp_downloader.py#L823-L899
- Current segment cleanup: https://github.com/manicko/mko_vkideo/blob/35114866e8ae6eda3f9cf3009f3bce4a6705979d/src/vkdownloader/services/segment_downloader.py#L1224-L1284
- Current playlist signature: https://github.com/manicko/mko_vkideo/blob/35114866e8ae6eda3f9cf3009f3bce4a6705979d/src/vkdownloader/services/segment_downloader.py#L144-L187
- Existing log setting: https://github.com/manicko/mko_vkideo/blob/35114866e8ae6eda3f9cf3009f3bce4a6705979d/src/vkdownloader/config.py#L579-L637
- Existing CLI reference: https://github.com/manicko/mko_vkideo/blob/35114866e8ae6eda3f9cf3009f3bce4a6705979d/docs/99-reference/cli-reference.md

---

## 2. Rules for LLM execution and subagents

The four named subagents have **noninterchangeable responsibilities**:

| Subagent | Responsibility | Required handoff artifact | Forbidden behavior |
|---|---|---|---|
| `researcher` | Inspect both pinned revisions, commit history, dependent library versions, HLS specifications, CLI and existing tests. Distinguish evidence from conjecture. | `research/<block>.md`: file:line references, diff summary, constraints, edge cases | Changing production code or declaring unrun tests passed |
| `planner` | Select the smallest correct change, interface contracts, migration strategy, test-first sequencing, and rollback boundary. | `plans/<block>.md`: exact edit list and dependency map | Expanding scope without explicit justification |
| `auditor` | Independently challenge the design/code for data loss, security, race conditions, backwards compatibility, API assumptions, and regressions. | `audits/<block>.md`: blocking findings rated P0/P1/P2 and remediation | Rubber-stamping the author; fixing code silently |
| `validator` | Write/execute deterministic tests, fault injection, acceptance matrix, Windows path checks, smoke tests, performance comparison, and proof of results. | `validation/<block>.md`: commands, pass/fail output, changed tests, known gaps | Claiming successful Windows/live CDN testing when not run |

The **main coding agent** (or a dedicated implementer) owns code changes. Named subagents never write concurrently into the same files. Delegate read-only research and validation design in parallel only where safe; implement sequentially.

### Mandatory stage gate, used in every block

```text
researcher (inspect evidence)
    ↓
planner (agree exact interfaces and minimal diff)
    ↓
validator (write RED / fault-injection tests; report expected failures)
    ↓
MAIN IMPLEMENTER (edit production code)
    ↓
auditor (independent code + security + data-loss review)
    ↓
MAIN IMPLEMENTER (resolve every blocking finding)
    ↓
validator (run GREEN tests + regression + lint; publish proof)
    ↓
Merge ONLY when reviewer and validator gates are green
```

For documentation-only Block A, the validator verifies the recorded commands and comparisons rather than writing failing tests. For Block J, the validator runs the final integrated matrix, and the auditor signs off after results. **If a subagent is unavailable**, the main agent performs the function sequentially and labels the report `role emulated`; never claim a nonexistent subagent ran.

Every PR must contain:

1. Evidence report and *exact* stable/current diff for touched functions.
2. Explicit invariants protected and a rollback/feature-flag path.
3. Tests proving the bug before the fix, then passing after.
4. Check of any old test whose assertion encodes destructive behavior; change its specification, not only its assertion.
5. Auditor review, validator test log, and a concise user-visible behavior note.
6. `git diff --check`, project-defined lint/type checks, and all relevant `pytest` tests (do not invent successful run results).

---

## Block A — Baseline, commit forensics, and test harness (NO production behavior changes)

**Priority:** P0  
**Depends on:** none  
**Expected output:** immutable baseline report + reproducible local fixture  
**Subagent order:** `researcher → planner → validator → auditor`  
**Main implementer:** build fixtures only; do not refactor downloads.

### A1. Pin the real worktree and compare

```bash
git status --short
git rev-parse HEAD
git show --no-patch --format=fuller 665c6ac0e8e8a9d26b69ae12e608db829ba212a2
git show --no-patch --format=fuller 35114866e8ae6eda3f9cf3009f3bce4a6705979d
git merge-base 665c6ac0e8e8a9d26b69ae12e608db829ba212a2 35114866e8ae6eda3f9cf3009f3bce4a6705979d
git log --oneline --reverse 665c6ac0e8e8a9d26b69ae12e608db829ba212a2..35114866e8ae6eda3f9cf3009f3bce4a6705979d
git diff --stat 665c6ac0e8e8a9d26b69ae12e608db829ba212a2 35114866e8ae6eda3f9cf3009f3bce4a6705979d
git diff 665c6ac0e8e8a9d26b69ae12e608db829ba212a2 35114866e8ae6eda3f9cf3009f3bce4a6705979d -- src/vkdownloader/services/downloader.py src/vkdownloader/services/ytdlp_downloader.py src/vkdownloader/services/segment_downloader.py src/vkdownloader/services/ffmpeg_utils.py src/vkdownloader/config.py src/vkdownloader/cli.py
```

Create read-only worktrees for stable/current comparisons. Do not run either branch against the user's live `Shows` directory. Confirm the direction of the diff: stable must actually be an ancestor or document divergence. Locate the exact commit(s) that introduced each faulty behavior; if a defect existed in stable, mark it as **existing defect**, not **regression**. Confirm how the old `HLSDownloader.download_with_ffmpeg` worked and exactly when it was selected; cite `perform_download()` branches in both revisions. Examine tests that were removed or rewritten along with FFmpeg.

### A2. Reproducible testing fixture

Implement a local, loopback-only HTTP server that serves a VOD master playlist and media playlists (including a 1,895-fragment synthetic case) with deterministic test bytes. It must support fault scripts:

- 403 after N fragments, then return a freshly signed URL;
- 429 with `Retry-After` and a count of requests;
- 500/503 and connection resets;
- slow responses/timeouts;
- same segment bytes but different signed URL query strings;
- different media bytes at the same index; discontinuity/init-map changes;
- process interruption and resume;
- a corrupt/truncated segment;
- output directory with spaces, Cyrillic, brackets and Windows path normalization.

Use distinct requests per fixture variant, fixed seed, no actual CDN credentials. Produce an HTTP request audit file with URL **paths and counters**, with sensitive query values redacted. Add a fixture to compare yt-dlp and FFmpeg where executable dependencies are available.

### A3. Baseline measurements

Record tool versions (not just minimum constraints), retry parameters, concurrent segment count, speed/size estimates, genuine bytes saved, number of child launches, number of duplicate HTTP segment requests, number of state/playlist refreshes, memory peak, exit code and final `ffprobe` metadata.

**Acceptance:** SHA identity verified; history/diff report complete; deterministic fixture can reproduce at least one restart and one token-change scenario; no user content modified. If live speed cannot be measured, mark as `NOT RUN`, not `PASS`.

---

## Block B — Preserve all existing partial data and prohibit destructive cleanup

**Priority:** P0 / urgent  
**Depends on:** Block A's function map; can be implemented before other redesigns  
**Likely files:** `services/ytdlp_downloader.py`, `services/segment_downloader.py`, relevant tests  
**Subagent order:** `researcher → planner → validator (RED) → implementer → auditor → validator (GREEN)`

### B1. Change failure semantics

- `download_hls_with_resume()` must **not** call `_cleanup_segments()` on failure, cancellation, timeout, disk-full, merge failure, or token refresh failure.
- `_tally_and_merge()` may remove completed segment files only **after** final media verification and atomic commit; it must not delete on a successful merge that has not been verified/published.
- `download_with_ytdlp_with_resume_fallback()` must not unlink `.part` after maximum retries.
- `_attempt_segment_resume()` must not unlink an existing yt-dlp `.part` when another method is attempted.
- Avoid treating a missing/zero-size `.part` as proof that no recoverable `.part-Frag*`, `.ytdl`, or segment-directory files exist.
- A fallback that cannot reuse the current backend's partial representation must either (a) stay with the same backend and preserve its artifacts, or (b) use a separate **new** staging area and preserve the original artifact. It must never claim to have resumed bytes it discarded.

### B2. Suggested control-flow shape

```python
async def download_hls_with_resume(request, *, workspace, settings, **kwargs):
    # Illustrative pseudocode: adjust function signatures to current project APIs.
    success = False
    try:
        staged_path = await _run_download_session(
            request=request,
            segments_dir=workspace.segments_dir,
            staging_dir=workspace.staging_dir,
            settings=settings,
            **kwargs,
        )
        if staged_path is None:
            return None
        await verify_media(staged_path, request)
        final_path = publish_verified_file(staged_path, workspace.final_path)
        success = True
        return final_path
    finally:
        if success:
            cleanup_owned_job_artifacts(workspace)  # NOT a broad output-directory glob
        else:
            log_preserved_artifacts(workspace)
            # No deletion, including on asyncio.CancelledError.
```

Handle `BaseException`/cancellation correctly when ensuring cleanup does not mask the original failure; do not silently swallow exceptions. Do not delete files in exception logging. Do not auto-purge stranded old files at startup.

### B3. Legacy files

When a user has `Shows\<long title>.mp4.part` and `Shows\<long title>.mp4.part-FragNN` from an old run, **do not move or delete them while the original process may be running**. First detect ownership/inactivity and obtain an exclusive lock; offer a dry-run migration/registration into a compatible workspace (Block D). If compatibility or `.ytdl` state cannot be guaranteed, leave files untouched, emit an actionable warning, and allow a legacy `--resume-legacy` path or explicit documented manual recovery later. Never auto-restart a 15 GiB download at byte zero because of a migration.

**Acceptance:** injected failures at 30%, 90% and during merge leave identical stored segment/partial checksums; cancellation leaves recoverable data; original successful outputs are never deleted; tests originally expecting cleanup are updated to assert preservation.

---

## Block C — Make diagnostics actionable; log the exact cause of restart

**Priority:** P0 (small change)  
**Depends on:** Block A; coordinate with B to avoid conflicting edits  
**Likely files:** `config.py`, `cli.py`, `services/ytdlp_downloader.py`, `services/segment_downloader.py`, `utils/url_sanitizer.py`  
**Subagent order:** `researcher → planner → validator (RED) → implementer → auditor (secret-leak review) → validator (GREEN)`

### C1. What exists today

- Existing `--log-file` is supported by `cli.py`; `Settings.log_file` defaults to `None`.
- When set, `setup_logging()` writes structured JSON to that file; otherwise structlog uses stderr.
- yt-dlp subprocess output is independently echoed to stderr by `_echo_ytdlp_line()` and only a bounded transcript tail is retained for failure. **A configured application log file is not necessarily a complete child transcript.**
- To collect evidence immediately, the operator may run:

```powershell
vkdownloader download "https://vkvideo.ru/video-225794656_456244209" --quality 1440 --method yt-dlp --output "C:\data\Video\Shows" --no-ssl-verify --log-level DEBUG --log-file "C:\data\Video\Shows\tmp\logs\manual-diagnostic.jsonl"
```

This command records structured application logs; a child transcript improvement is part of this block. **Do not assume changing `--log-file` alone captures all child lines.** A separately captured terminal transcript can help temporarily, but verify that no credentials or signed URLs leak before sharing it.

### C2. Structured events

Emit consistent fields for all new events: `job_id`, `attempt_id`, `correlation_id`, `backend`, `stream_variant_id`, `quality_requested`, `fragment_done`, `fragment_total`, `resume_bytes`, `elapsed_seconds`, `reason_code`, `retry_in_seconds`, `http_status`, and safely sanitized host/path. Include:

```text
job_started
workspace_opened
backend_started
backend_stopped
child_exit                  {returncode, elapsed_seconds, last_error_code}
segment_request_failed       {index, http_status, exception_type, attempt}
retry_scheduled              {scope, reason_code, delay_seconds}
refresh_requested            {reason_code}
refresh_completed            {quality_match, variant_match}
backend_switch_blocked       {reason_code: incompatible_partial_state}
resume_checkpoint_loaded     {verified_segments, verified_bytes}
progress_estimate_unreliable {reason_code}
job_failed_preserved         {state_path, artifact_count, artifact_bytes}
media_verified
job_committed
```

**Do not emit raw URLs, tokens, cookie values, unrestricted exception `.args`, or raw subprocess argv.** Structure URL logging through existing `sanitize_text_for_log`, `_strip_auth_params`, and `redact_log_event` (audit their edge cases, including URLs in exceptions). Keep raw child-output buffering bounded and sanitize **before** file writes. Log one restart reason per actual restart and include a monotonically increasing attempt index.

### C3. Implementation approach

- Add an optional sanitized child-transcript sink that streams lines into the JSONL diagnostic channel (rather than storing an unbounded string in memory), with per-line caps and progress rate limiting.
- Preserve the existing human-readable console behavior for single downloads.
- Put auto-created per-job logs in `output/tmp/logs/`; do not mix log files with `.part-Frag*`.
- Add a retention policy (`max_file_bytes`, `backup_count` or age-based cleanup) for *logs only*, and document Windows ACL limitations (POSIX `0o600` is not a sufficient confidentiality guarantee on Windows).
- Configure both logging handlers deterministically, respecting tests and avoiding accidental duplicate records if `setup_logging()` is called more than once.
- Use a config option to disable log persistence when explicitly requested; logging errors must never corrupt a download.

**Acceptance:** simulated 403/429/timeout/exit each produces an unambiguous redacted cause+attempt event; logging continues after a child restart; 100,000 progress lines do not exhaust memory or create huge logs; a secrets-canary test finds zero unredacted tokens/cookies in logs and state.

---

## Block D — New `output/tmp` workspace and safe yt-dlp artifact routing

**Priority:** P0 / user-visible requirement  
**Depends on:** B and basic C diagnostics  
**Likely files:** new `services/workspace.py`, `services/ytdlp_downloader.py`, `services/segment_downloader.py`, `services/downloader.py`, `utils/security.py`, `cli.py` (only if new flags)  
**Subagent order:** `researcher (yt-dlp -P semantics + Windows) → planner (workspace contract/migration) → validator (RED) → implementer → auditor (path-security/data preservation) → validator (GREEN)`

### D1. A single workspace contract shared by all backends

```python
from dataclasses import dataclass
from pathlib import Path
from hashlib import sha256

@dataclass(frozen=True)
class DownloadWorkspace:
    final_path: Path
    root: Path
    ytdlp_dir: Path
    segments_dir: Path
    staging_dir: Path
    state_path: Path
    log_path: Path
    lock_path: Path

def stable_job_id(video_id: str, quality: str, final_basename: str) -> str:
    # Hash identifiers and a normalized output basename; NEVER hash live tokens.
    logical = f"{video_id}|{quality}|{final_basename.casefold()}"
    digest = sha256(logical.encode("utf-8")).hexdigest()[:12]
    return f"video-{video_id}-q{quality}-{digest}"

def make_workspace(final_path: Path, video_id: str, quality: str) -> DownloadWorkspace:
    final_path = final_path.resolve()
    # In the actual implementation, validate that final_path is an approved target
    # and that resolved directory components cannot escape through symlinks/junctions.
    tmp = final_path.parent / "tmp"
    job = tmp / "jobs" / stable_job_id(video_id, quality, final_path.name)
    return DownloadWorkspace(
        final_path=final_path, root=job,
        ytdlp_dir=job / "ytdlp", segments_dir=job / "segments",
        staging_dir=job / "staging", state_path=job / "state.json",
        log_path=tmp / "logs" / f"{job.name}.jsonl", lock_path=job / "lock",
    )
```

This is **illustrative**, not a drop-in path validation or cross-platform locking implementation. Reuse the existing path-safety utilities. Avoid overlong Windows paths by bounding the job-name length and using a short stable suffix. Ensure concurrency: same video/quality but different final filename may have different workspaces; same target filename must fail fast or share a lock safely. Use a proper atomic OS lock with Windows support, stale-lock recovery, and ownership verification; presence of a file named `lock` is not enough.

### D2. Route yt-dlp using native staging/temp paths

Current code uses `-o str(output_file)` (often an absolute final path), so yt-dlp derives `.part` and fragment names beside it. **Simply adding `-P temp:...` while keeping an absolute `-o` is not sufficient; yt-dlp can ignore paths for absolute templates.** Verify this against the pinned yt-dlp version.

Preferred command shape:

```python
# Illustrative argument fragment; append to the existing subprocess argument builder.
# Both -P paths and -o template must be tested with the installed yt-dlp.
cmd = [
    sys.executable, "-u", "-m", "yt_dlp",
    "-P", f"home:{workspace.staging_dir}",
    "-P", f"temp:{workspace.ytdlp_dir}",
    "-o", workspace.final_path.name.replace("%", "%%"),
    "--continue",
    "--newline",
    "--hls-prefer-native",
    # existing user agent, referer, retry, cookie, SSL and concurrency args...
]
```

Test the precise behavior of `--paths`/`-P` with HLS `--concurrent-fragments` and the installed yt-dlp release. Confirm actual `.part`, `.part-Frag*` and `.ytdl` locations. If yt-dlp's home/temp feature is incompatible with a supported version, use a temporary output template under the workspace and explicitly promote only a **validated final file**; avoid copying 15+ GiB in normal operation. Since the workspace is within `output`, file moves stay on the same volume.

The existing `_ytdlp_temp_name(output_file)` helper assumes `<final>.part`; replace that with a backend-specific `YtdlpArtifacts` object tracking the **actual** temp path and all related fragments, not by guessing from `final_path`. Update all callers, tests, resume probes, and cleanup assumptions together.

### D3. Segment backend and FFmpeg output

- Change `segments_dir = output_file.parent / f".{output_file.stem}_segments"` to `workspace.segments_dir`.
- FFmpeg merge output and any direct FFmpeg download must target `workspace.staging_dir`, not `workspace.final_path`.
- Use `os.replace(staged_path, final_path)` only after all validation has passed, on the same filesystem, with defined collision semantics (do **not** overwrite an existing user file without explicit permission). Ensure files are closed before the Windows rename. Optional durability: flush/fsync completed file and parent where supported, and document platform limitations.
- Leave `tmp/` root and `tmp/logs/` intact after success; remove only owned job files when explicitly safe.

```python
def publish_verified_file(staged: Path, final: Path) -> Path:
    # PRECONDITIONS: staged has passed media and identity checks, is closed,
    # final path was validated, collision policy has been enforced.
    if final.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {final}")
    # Example only: this check + os.replace is not atomic no-overwrite on every OS.
    # Implement collision-safe publish / exclusive reservation and test on Windows.
    staged.replace(final)
    return final
```

### D4. Legacy migration contract

- Default new downloads use `tmp` from their first byte.
- Old root `.part`, `.part-Frag*`, `.ytdl`, and `.mp4` are treated as **user data**, never trash.
- Implement discovery with dry-run output: `found N old artifacts / total bytes / candidate job / safe-to-adopt?`.
- Adoption requires matching video ID, quality, final target, yt-dlp state compatibility, inactive writers, and an exclusive lock. Use verified atomic moves *on the same volume* with rollback on partial failure. Do not relocate `.part` without matching fragment and `.ytdl` metadata.
- Where adoption cannot be proven safe, keep original files untouched, explicitly log `legacy_resume_manual_action_required`, and allow an independent new workspace only with the user's informed choice.

**Acceptance:** for one complete download, `Shows` contains **only** a final video plus the `tmp` directory (and unrelated pre-existing user files); all in-progress data is inside `tmp/jobs/<job>`; interruption and retry reuse the same stable workspace; other jobs' files remain intact; 15 GiB legacy partial is never silently discarded; Cyrillic/long-path/Windows process-lock cases pass.

---

## Block E — Durable per-segment checkpoint and safe content identity

**Priority:** P0  
**Depends on:** B, D  
**Likely files:** `services/segment_downloader.py`, new `services/checkpoint.py`, HLS parser abstraction, tests  
**Subagent order:** `researcher (HLS identity) → planner (schema + versioned migration) → validator (RED) → implementer → auditor → validator (GREEN)`

### E1. Replace unsafe URL-list signature semantics

A SHA-256 hash of full signed segment URLs is not a media identity. A token-only change must not delete previous segments, while an actual media variant change must never reuse them blindly. Retain old `playlist_signature` as legacy diagnostic metadata if useful, but stop using it as a destructive cache-invalidation gate.

Define an HLS segment identity contract with, where available: original video ID, exact selected variant, track type, CODECS, resolution, playlist type, media-sequence number, discontinuity sequence, segment sequence/index, byte-range, init-map identity/content, key/method/key-ID (never key material), duration, and a content integrity record for every persisted segment. Plain `URL path` alone is not a guarantee; stripping signed query params without verification is not sufficient when CDN paths or media can change.

### E2. Versioned state and atomic updates

```python
from dataclasses import dataclass, asdict
from pathlib import Path
import json, os

@dataclass
class SegmentRecord:
    sequence: int
    relative_file: str          # confined to the owned workspace
    size: int
    sha256: str                 # computed after a fully completed segment write
    duration_seconds: float | None
    byte_range: str | None
    discontinuity_sequence: int

@dataclass
class JobCheckpoint:
    schema_version: int
    video_id: str
    quality_requested: str
    stream_variant_id: str
    playlist_fingerprint: str  # derived from verified media structure, not tokens
    segments: dict[str, SegmentRecord]

# On updates, serialize to a new file in the same directory, flush+fsync,
# then atomically replace the old state file. The actual implementation must
# also validate schema version, relative paths, duplicate sequence indexes,
# file size/hash, and cross-platform rename rules.
def write_state_atomic(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".new")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
```

Never store authentication tokens, signed URL queries, cookies, full sensitive request headers, or plaintext AES-128 keys. Use file-based/streaming SHA-256, not `read_bytes()` on a 15 GiB artifact. Persist checkpoint entries **only after** a complete segment is written to a `.tmp` and atomically renamed to its owned final segment name. Unknown or malformed checkpoint fields must fail safely without deleting files.

### E3. Compatibility / refresh rules

- On reconnect, verify the checkpoint's video, requested quality, variant identity, playlist structure, relevant HLS metadata, and segment sequence/byte-range boundaries.
- Verify each reused segment's size and (when recorded) SHA-256. If a signed URL changes but media identity remains demonstrably identical, skip redownloading cached segments.
- If identity is ambiguous, verify against a known authoritative media/content fingerprint or download a controlled reference segment and compare bytes. **Fail closed** if compatibility cannot be demonstrated; quarantine old artifacts in their job directory, do not delete them or mix content.
- If the same index maps to different bytes, start an **isolated new generation** (new workspace subfolder) without erasing the old one.
- Support HLS features actually present in test streams (and explicitly reject unsupported ones): `EXT-X-MAP`, `EXT-X-BYTERANGE`, audio renditions, discontinuities, encryption, `EXT-X-ENDLIST`, possible fMP4, segment duration/sequence. Do not silently concatenate incompatible media.
- If a playlist is live/changing rather than finite VOD, do not apply the fixed 1,895-fragment logic blindly.

**Acceptance:** token-only URL refresh reuses valid segments; changed bytes/variant does not reuse them; crash immediately before/after checkpoint publication leaves a recoverable state; checksum failure redownloads only the bad item; no temporary segment or corrupt partial is marked verified; no URL secrets are stored.

---

## Block F — Refresh expired tokens while preserving exact requested quality

**Priority:** P0  
**Depends on:** E's media-identity interface; may prototype earlier  
**Likely files:** `services/extractor.py`, `services/quality.py`, `services/ytdlp_downloader.py`, `services/segment_downloader.py`, `models/quality.py`  
**Subagent order:** `researcher (extractor formats/quality mapping) → planner → validator (RED) → implementer → auditor → validator (GREEN)`

### F1. One refresh interface, not duplicated shortcuts

Implement an explicit `refresh_stream()` operation returning a validated stream binding, not merely refreshed cookies:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class StreamBinding:
    media_playlist_url: str   # sensitive; NEVER log/serialize as plain text
    requested_quality: str   # e.g. "1440"
    actual_height: int | None
    variant_id: str
    codecs: str | None
    cookies: object | None    # opaque in-memory credentials

async def refresh_stream(
    original_vk_url: str,
    requested_quality: str,
    previous: StreamBinding,
    extractor,
) -> StreamBinding:
    fresh_candidates = await extractor.extract_streams(original_vk_url)
    # Resolve exact height via authoritative variant metadata / master playlist.
    # A browser-extracted UNKNOWN-height stream cannot verify an exact request.
    selected = select_exact_or_fail(fresh_candidates, requested_quality)
    result = binding_from_selected(selected)
    if requested_quality.isdecimal() and result.actual_height != int(requested_quality):
        raise QualityMismatchError("Exact quality is unavailable or unverified")
    return result
```

Here `select_exact_or_fail`, `binding_from_selected`, and `QualityMismatchError` are **design placeholders**; reuse/refactor existing `QualitySpec`/`QualitySelector` and domain exceptions as appropriate. In particular, an HLS browser-captured URL labeled `unknown` with `height=None` must not be accepted as a fresh `1440p` stream without independently reading verifiable master-playlist/variant metadata. Do not assume old signed URLs stay valid after refreshing cookies.

### F2. Update every relevant call site

- `_resolve_cookies()` must not leave an expired `m3u8_url` unchanged merely because quality is not `BEST`.
- `_attempt_segment_resume()` must not follow the old `quality_spec.kind is QualityKind.BEST` branch for refreshing URL while `EXACT` keeps the old address.
- `_refresh_token_and_retry()` / `_fetch_playlist_with_retry()` must propagate a new verified URL + credentials + variant identity to the owner state machine.
- Distinguish playlist-level 403/410 from individual segment 403, preserving already downloaded segments in both cases.
- Reuse the same `StreamBinding` through the yt-dlp, custom segment and optional FFmpeg adapters so a backend change cannot silently lose the requested quality.

### F3. Tests

Mock an old expired signed URL and a new URL pointing at the same variant, both with height=1440. Verify the new URL was passed to the backend. Test missing 1440, master-playlist ambiguity, unknown-height browser capture, refresh loops, and quality reordering. Inexact quality must cause an explicit error **without cleanup**.

**Acceptance:** `--quality 1440` consistently downloads a verified 1440-pixel-high variant or fails with an actionable error, preserving the whole job; refreshed URLs are demonstrably used; no silent downgrade.

---

## Block G — Replace nested retries with an observable download state machine

**Priority:** P1  
**Depends on:** B, C, E, F  
**Likely files:** `services/ytdlp_downloader.py`, `services/retry_policies.py`, `services/downloader_throttle.py`, `services/segment_downloader.py`, new orchestration helper  
**Subagent order:** `researcher (retry layers + status semantics) → planner (state diagram) → validator (RED) → implementer → auditor → validator (GREEN)`

### G1. Explicit states

```text
CREATED → RESOLVE_STREAM → VALIDATE_VARIANT → DOWNLOAD
                                           |        |
                                           |        ├─ transient timeout/5xx → RETRY_SAME_SEGMENT
                                           |        ├─ 401/403/410 with expiry signal → REFRESH_STREAM
                                           |        ├─ 429 → RATE_LIMIT_WAIT → RETRY
                                           |        ├─ backend incompatibility → PRESERVE_AND_STOP
                                           |        └─ all data complete → VERIFY_MEDIA → COMMIT → DONE
                                           |
                                   incompatible quality → PRESERVE_AND_STOP
```

Represent `CANCELLED`, `DISK_FULL`, `FAILED_RETRY_BUDGET`, and `INTEGRITY_FAILED` as explicit terminal states with preserved artifacts. An outer retry may restart a child **only** if it records why, respects a bounded total budget, and can reuse the same job state.

### G2. Error classification

| Symptom | Policy |
|---|---|
| Connection timeout/reset | bounded retry of failed request only; randomized backoff |
| 401/403/410 indicating expired authentication | refresh stream and revalidate exact variant; cap refresh attempts |
| 429 | honor `Retry-After`; reduce request concurrency; do not hammer CDN |
| 500/502/503/504 | bounded jittered exponential backoff |
| 404 on one segment | verify refreshed playlist and sequence; fail safely if persistently missing |
| Slow throughput | observe over time; don't restart solely from a momentary low sample |
| Disk full / permission error / invalid output path | stop immediately; preserve checkpoint |
| User cancellation | terminate/reap child and retain working files |
| Incompatible playlist or codec change | quarantine generation; do not concatenate mismatched media |

The existing `--throttled-rate` option is passed through `_build_ytdlp_cli_command()`. Examine its setting and actual behavior. If it produces avoidable restarts, make it opt-in/tunable, but do not disable protective rate limiting or increase `-N` indiscriminately. Evaluate nested `-R`, `--fragment-retries`, and app-level loops as a **bounded combined budget**; avoid multiplicative retries without diagnostics.

### G3. No hidden retry/reset

Every child start and restart must carry the same job ID and a new `attempt_id`. Capture return code, error category, resume state and selected fresh stream ID. Keep retryable state through an interrupted process; don't equate “yt-dlp re-read the manifest” with “all fragments were redownloaded.” Count actual segment HTTP fetches separately from `.part-Frag already been downloaded` notices.

**Acceptance:** induced failures produce a finite known number of retries; 429 respects cooldown; no tight loop re-extracts the same stale URL; percent and job state survive child restarts; no test relies on live CDN responses.

---

## Block H — Restore direct FFmpeg transport as an isolated, optional adapter

**Priority:** P1; **do not block P0 data preservation on this**  
**Depends on:** D, E, F, G  
**Likely files:** new `services/ffmpeg_transport.py` (extract narrowly from stable code), `services/downloader.py`, `models/enums.py`, `cli.py`, `services/ffmpeg_utils.py`, tests  
**Subagent order:** `researcher (stable old HLSDownloader and ffmpeg version options) → planner (adapter contract and switching rules) → validator (RED) → implementer → auditor (command safety/stream identity) → validator (GREEN)`

### H1. Historical facts to preserve

At stable SHA, `DownloadMethod.FFMPEG` did this:

1. Resolve stream URL/cookies.
2. Invoke `HLSDownloader.download_with_ffmpeg(...)`.
3. **If FFmpeg fails**, invoke `download_hls_with_resume(...)` custom segment download.

For `DownloadMethod.YTDLP` and `AUTO`, stable used `download_with_ytdlp_with_resume_fallback(...)`; the FFmpeg direct path was **not** an unconditional fallback for the user's pinned `--method yt-dlp` command. Thus adding a yt-dlp → FFmpeg fallback would be a **new behavior**, not an exact restoration; implement only after explicit compatibility and cost assessment.

### H2. Adapter architecture

```python
from typing import Protocol

class DownloadTransport(Protocol):
    name: str
    async def download(self, binding: StreamBinding, workspace: DownloadWorkspace) -> Path | None:
        """Produce a completed media artifact in workspace.staging_dir, not final output."""

# Concrete adapters:
# YtdlpTransport
# SegmentTransport
# FfmpegTransport
```

Extract only the stable direct FFmpeg transport, progress parser, timeout/cancellation safeguards, and cookie/header handling that are still valid; reconcile with current subprocess security utilities. Run FFmpeg using `asyncio.create_subprocess_exec(*args)` with argument arrays (not `shell=True`). Direct output goes to `workspace.staging_dir`; leave the user's final output untouched until validation+commit. Use `-progress pipe:1 -nostats` where supported and parse numeric fields; a FFmpeg `total_size` field is bytes written so far, **not** the predicted final size. Reuse current `ffmpeg_utils.py` merge code where possible without duplicating helpers.

### H3. Switching policy

- `--method ffmpeg`: user opts into direct FFmpeg; if it fails, may fall back to the segment adapter **within a separate non-destructive workspace generation**. Do not claim FFmpeg can resume arbitrary partial MP4 output.
- `--method yt-dlp`: remain yt-dlp-first as before; do not silently switch to direct FFmpeg unless a separately documented and tested `--fallback-policy` explicitly allows it.
- `--method auto`: start with documented policy; add FFmpeg as a guarded optional candidate only once comparative tests prove it does not worsen reliability and existing partial state is kept.
- `--method ffmpeg` must not require the old code's APIs to reappear wholesale. Keep direct FFmpeg transport distinct from FFmpeg **merge/remux**, which remains necessary in custom segment downloads.

**Acceptance:** direct FFmpeg CLI mode exists again and works with signed HLS under supported tests; failures retain artifacts; cancellation reaps subprocess; cookies/tokens don't appear in logs/argv; single backend fallback does not erase another backend's data; full regression test matrix applies to all supported methods.

---

## Block I — Trustworthy progress, bytes, speed and ETA

**Priority:** P1  
**Depends on:** C, D, E, G  
**Likely files:** `services/ytdlp_downloader.py`, CLI progress renderer, `services/batch_downloader.py`, new `services/progress.py`  
**Subagent order:** `researcher (yt-dlp output semantics) → planner (progress domain model) → validator (RED) → implementer → auditor (unit semantics/races) → validator (GREEN)`

### I1. Separate the measurements

Do **not** overload a `(downloaded, total)` callback with “fragment counts sometimes, bytes other times” unless type information accompanies every update. Define separate fields with explicit units:

```python
from dataclasses import dataclass
from enum import Enum

class JobPhase(str, Enum):
    DOWNLOADING = "downloading"
    REFRESHING_TOKEN = "refreshing_token"
    WAITING = "waiting"
    MERGING = "merging"
    VERIFYING = "verifying"

@dataclass(frozen=True)
class ProgressSnapshot:
    job_id: str
    phase: JobPhase
    verified_segments: int
    expected_segments: int | None
    verified_bytes_on_disk: int
    network_bytes_this_session: int
    transfer_rate_bytes_per_sec: float | None
    eta_seconds: float | None
    is_estimate: bool
    attempt_id: int
```

`verified_bytes_on_disk` comes from verified artifact sizes/checkpoint; `network_bytes_this_session` is used for transfer-rate calculation. Do not derive physically downloaded bytes by multiplying yt-dlp's `%` by a speculative total size. A 1–2 TiB estimated size for a long HLS playlist must be flagged as unreliable rather than propagated as fact.

### I2. ETA policy

- Prefer completed-segment rate on a sliding window (e.g. 30–90 seconds) after enough actual observations, supplemented by real byte throughput when reliable.
- Estimate remaining work from media segment durations and measured cost where segment sizes vary significantly; do not assume every segment has the same byte size.
- Exclude intentional wait/backoff periods from network transfer rate while including expected retry/wait behavior in the **overall** completion estimate only when defensible.
- On restart, preserve job-level verified-progress counters from checkpoint; a new child's “frag 10” does not roll the whole job back from “603 verified.”
- When insufficient data or inconsistent manifests make ETA invalid, render `ETA: unknown`, never negative hours.
- Indicate `refreshing URL`, `waiting after HTTP 429`, `resuming`, `verifying`, etc., rather than showing fake active transfer.
- Preserve compatibility with the existing `progress_callback` API through an adapter until all callers (including batch) migrate.

### I3. Tests

Feed parser samples from the user's log, including:

```text
[download]  20.0% of ~  42.03GiB at  696.50KiB/s ETA 26:40:31 (frag 380/1895)
[download]   0.5% of ~   1.65TiB at  259.73KiB/s ETA --:--:-- (frag 10/1895)
[download]   0.6% of ~   1.38TiB at  438.36KiB/s ETA -4377:33:21 (frag 12/1895)
```

Verify impossible size/ETA is not accepted, `%` never exceeds bounds, no negative ETA leaks to UI, and multi-run progress uses verified checkpoint rather than current child output. Test TTY and redirected output, Unicode, and batch progress isolation.

**Acceptance:** progress survives retry without false backward jumps; ETA either plausibly bounded or unknown; fragment counts and bytes are never confused; log parser handles malformed/nonprogress lines without crashing; display does not overwrite/log child tokens.

---

## Block J — Full integration, Windows acceptance, release and rollback

**Priority:** P0/P1 final gate  
**Depends on:** all enabled blocks  
**Subagent order:** `planner (release checklist) → researcher (dependency/version cross-check) → validator (all tests + benchmarks) → auditor (independent final review) → implementer (only targeted fixes) → validator (rerun final matrix)`

### J1. Deterministic acceptance matrix

| Test | Required result |
|---|---|
| Basic HLS VOD, same CLI invocation | Completed valid MP4 in output root; all work files only under `tmp` |
| Kill process at 30% then rerun | Resume available; previously verified artifacts survive unchanged |
| Kill process at 90% then rerun | Does not start from zero or delete a large valid partial |
| Manifest token/query refresh, identical media | Reuses compatible fragments; no destructive invalidation |
| Manifest changed, same fragment index but different media | Does **not** mix bytes; preserves old generation |
| Exact `--quality 1440` with fresh matching URL | Downloads the new 1440 stream, never old expired URL |
| Exact 1440 unavailable or ambiguous | Clear error; no silent downgrade; all partials preserved |
| HTTP 403/410 | Bounded URL refresh, logged reason; no infinite loop |
| HTTP 429 + Retry-After | Respects cooldown, no retry storm |
| HTTP 5xx/timeouts | Bounded retries of failing items; no blanket restart |
| Invalid/truncated segment | Detects and redownloads only corrupt item |
| Disk full / read-only dir | Error without data deletion or corrupted checkpoint |
| Failed FFmpeg merge | Segments still present; output root not polluted |
| Cancellation | Child reaped; job recoverable and logs flushed |
| Concurrent same job | One writer only; second is rejected/attaches read-only |
| Concurrent different jobs | Separate workspaces and independent progress |
| 1,895 HLS segments | Stable memory/disk behavior; no broken merge; correct fragment counts |
| Windows with Cyrillic, spaces, brackets, long names | No shell-quoting, path-escape, or rename failures |
| Existing final output filename | No silent overwrite or corruption |
| Existing 15 GiB legacy `.part` + fragments | Not deleted/moved unsafely; deliberate compatible recovery or explicit warning |
| Credential canary in URL/cookies | Zero secret values in JSONL, console and checkpoint |
| FFmpeg optional backend | Success/failure and cancellation obey same artifact invariants |
| Parser receives false TiB estimate/negative ETA | Shows known verified bytes and `ETA: unknown` |
| Repeated `--log-file` runs | No duplicate handlers; logs have cause+attempt+sanitized details |

### J2. Verification commands

```bash
# Use the project's documented environment manager and exact tool versions.
uv sync
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
git diff --check

# Run focused tests and optional integration tests separately.
# Adapt test path/markers to actual existing project test structure.
uv run pytest tests -q

# On the completed output, inspect streams/duration with FFprobe.
ffprobe -v error -show_entries format=duration,size -show_entries stream=index,codec_type,codec_name,width,height -of json "C:\data\Video\Shows\<completed-file>.mp4"
```

Other type/security checks may exist in `.github/workflows` and `pyproject.toml`; discover and run them. Use bounded fixture sizes for CI; mark live CDN and Windows integration tests as optional/manual only when not executable in CI. Provide concrete logs for any skipped tests.

### J3. Compare stable vs current vs fixed

Use identical test assets, settings, machine, client versions, concurrency, and network conditions. Record median and dispersion over repeated runs, not a single anecdotal rate. Measure:

- success percentage, retry count, process launches, total wall time;
- duplicate HTTP bytes, disk bytes retained, corrupt/verified segments;
- time-to-recover after a forced token expiry;
- RAM peak, disk overhead, number of visible root files;
- correctness of quality and `ffprobe` metadata;
- fraction of cases in which ETA is provided *and valid*.

Set a **hard no-regression gate** for data survival and output correctness. For throughput, require no statistically meaningful degradation from stable on comparable fixtures, or document/explain any tradeoff and obtain approval before changing defaults. Do not promise an exact download speed because CDN behavior is external.

### J4. Documentation and rollback

- Update README, installation guide, CLI reference and troubleshooting guide for `tmp`, retention, resume, `--log-file`, optional `--method ffmpeg`, and exact-quality failures.
- Explain that the familiar command still works; first new run uses per-job `tmp` automatically.
- Provide explicit commands to view log location and a redacted diagnostics bundle. Don't require a user to share cookies or full signed URLs.
- Explain how to inspect and **manually** clean abandoned job folders, with a safe dry-run; no irreversible automatic cleanup of incomplete jobs.
- Add a `--keep-temp` or equivalent option only if it has a clear interaction with default preservation semantics; by default, failed jobs always keep usable temp data.
- Preserve feature flags/independent backend selection so direct FFmpeg can be disabled without reverting checkpoint/`tmp` improvements.
- Tag the first validated release and publish a migration/rollback note; reverting application code must not cause deletion of job workspaces created by the newer version.

**Final acceptance:** every required matrix item has a recorded result, reviewer approval, and artifact integrity evidence. Any failure in preservation, exact-quality selection, or secret redaction blocks release. There must be no known path that deletes valid downloaded bytes following a transient error.

---

## 3. Implementation order, deliverables and safe parallelism

| Order | Block / PR | Purpose | Dependency | Required subagent sequence | Exit gate |
|---|---|---|---|---|---|
| 1 | A / `forensics-and-fixtures` | Establish the true diff and deterministic failures | none | `researcher → planner → validator → auditor` | evidence and fixture reproducible |
| 2 | B / `preserve-partials` | Stop destructive cleanup everywhere | A | `researcher → planner → validator RED → implementer → auditor → validator GREEN` | zero artifact loss after failure |
| 3 | C / `diagnostics` | Capture real failure and retry reasons | A; coordinate B | same standard gate | redacted structured evidence |
| 4 | D / `isolated-temp-workspaces` | Put `.part` / fragments / segments in `output/tmp` | B, C | same standard gate | no in-progress artifacts at root |
| 5 | E / `durable-resume-checkpoint` | Safe segment identity and recovery | B, D | same standard gate | token rotation reuses verified bytes |
| 6 | F / `exact-quality-refresh` | Refresh `1440` without downgrade | E | same standard gate | stale URL replaced or safe error |
| 7 | G / `retry-state-machine` | Stop unbounded nested restarts | C, E, F | same standard gate | bounded, explicit retries |
| 8 | H / `ffmpeg-transport` | Bring back optional direct FFmpeg path | D–G | same standard gate | isolated, non-destructive mode |
| 9 | I / `progress-and-eta` | Truthful job-wide progress | C, E, G | same standard gate | no fake TiB/negative ETA |
| 10 | J / `final-verification-release` | Full Windows/HLS regression and release | A–I | `planner → researcher → validator → auditor → implementer → validator` | full signed-off acceptance matrix |

**Parallelism:** Blocks B and C may have parallel *read-only* research but must not be edited concurrently if touching `ytdlp_downloader.py`. Blocks H and I can begin separate research/plans in parallel after G, but their code merges sequentially; run the whole suite after each merge. Do not combine all ten blocks in one mega-PR.

### Per-PR report template (LLM must fill with evidence)

```markdown
## PR <ID> — <short name>
- HEAD before/after: <SHA> → <SHA>
- Baseline comparison: <SHA/lines and tests>
- Behavior changed: <precise description>
- Preserved invariants: <list>
- Code files: <paths / functions>
- Tests added/updated: <test names>
- RED evidence: <command + failure summary>
- GREEN evidence: <command + pass summary>
- Auditor P0/P1 findings: <list / resolved status>
- Validator gaps: <skipped tests, with reason>
- Data migration and rollback: <details>
- Resulting root/temp file layout: <example>
```

---

## 4. Operator diagnostics while refactoring

**Current behavior:** `--log-file` is already available at the pinned current HEAD. Absent that option (or `VKDOWNLOADER_LOG_FILE` in the environment), the application defaults to stderr/console structured logging rather than a persistent file. A large `.mp4.part` plus `.mp4.part-FragNN` files is consistent with a native yt-dlp HLS download; the mere existence of both is **not evidence** that the CDN is a bot blocker or that the exact same bytes are being redownloaded.

**Before updating the application:** Do not delete or rearrange the 15 GiB `.part`, `*.part-Frag*` or `.ytdl` artifacts while the download is active. Collect the first failure event and its context, the child return code, yt-dlp/FFmpeg versions and directory inventory (filenames and sizes only). Remove signed URLs and cookies from any support bundle. Avoid rerunning the old binary against partially migrated files.

**User-compatible diagnostic invocation now:**

```powershell
vkdownloader download "https://vkvideo.ru/video-225794656_456244209" --quality 1440 --method yt-dlp --output "C:\data\Video\Shows" --no-ssl-verify --log-level DEBUG --log-file "C:\data\Video\Shows\tmp\logs\diagnostic.jsonl"
```

**After the refactor:** the original unchanged command must automatically produce a discoverable per-job log under `output/tmp/logs` (unless persistent diagnostics are explicitly disabled) and all working artifacts under `output/tmp/jobs/<id>`; terminal output must display the log path. Verify the security implications of persistent logs and document the retention policy.

**Important:** `--no-ssl-verify` only disables TLS certificate verification. It does not fix expired URLs, HTTP 403/429, rate limiting, or download-state corruption. Keep TLS verification enabled by default and do not advise disabling it as a standard remedy.

---

## 5. Done means done

The work is **not complete** merely when a sample video downloads successfully. It is complete when:

- [ ] Current and stable revisions are diffed at the exact user-provided SHAs, and regressions are distinguished from pre-existing flaws.
- [ ] Root `Shows` remains clean of `.part`, `.part-Frag*`, `.ts`, intermediate `.mp4`, `.ytdl` and checkpoint files for all **new** jobs.
- [ ] Failure/cancellation cannot erase valid downloaded progress; existing legacy 15 GiB artifacts are never auto-deleted.
- [ ] Exact 1440p is preserved across refresh, retry and backend selection.
- [ ] Token rotation without content change preserves verified segments; actual content changes never silently mix media.
- [ ] Every child restart has a recorded and redacted reason; retries are bounded.
- [ ] Optional direct FFmpeg mode is restored independently of FFmpeg merge, with non-destructive fallback semantics.
- [ ] No terabyte fantasy total or negative ETA is presented as real progress.
- [ ] Output is validated with `ffprobe`, and only then published as final.
- [ ] Windows/Unicode/locking/interrupt/HTTP fault-injection tests and security redaction tests have concrete passing logs.
- [ ] Each PR has its specified subagent handoffs and acceptance report.
- [ ] Documentation, migration, and rollback instructions are published.

**Primary goal:** A long-running 1440p VK Video HLS job can safely run for many hours, survive expiring CDN links or process restarts, reuse verified on-disk work, and produce one correct MP4 while keeping all intermediate files organized beneath `output/tmp`.
