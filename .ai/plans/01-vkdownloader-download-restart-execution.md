# Execution Plan — VKDownloader Download Restart Fix

Source plan: `.ai/plans/vkdownloader_download_restart_plan.md`
Code context: Auditor findings (session ses_e4846e44dffeFXBvbgk1vwIASN)

## Blocks (dependency order per source plan)

| Block | Priority | Depends on | Status |
|-------|----------|------------|--------|
| D0 Reproduction & correlation | P0 | — | completed (task: .ai/tasks/todo/D0_reproduction_correlation.yaml) |
| D1 Slow channel & managed child process | P0 | D0 | ready (task: .ai/tasks/todo/D1_slow_channel_managed_child.yaml) |
| D2 Typed outcome & file retry | P0 | D0 | ready (task: .ai/tasks/todo/D2_typed_outcome_file_retry.yaml) |
| D3 Artifact compatibility & resume | P0 | D2 | ready (task: .ai/tasks/todo/D3_artifact_compatibility_resume.yaml) |
| D4 Safe finalization & recovery | P0 | D2, D3 | ready (task: .ai/tasks/todo/D4_safe_finalization_recovery.yaml) |
| D5 Network fallback & progress | P1 | D1, D2, D3 | ready (task: .ai/tasks/todo/D5_network_fallback_progress.yaml) |
| D6 Windows acceptance & release | P0 | D1–D5 | ready (task: .ai/tasks/todo/D6_windows_acceptance_release.yaml) |

## Global constraints
- Python 3.14, uv, ruff/mypy strict.
- Never change audit phase files.
- Commit each block separately.
- Max 2 parallel subagents; no background.
- Preserve external contract `Path | None` of `_download_with_ytdlp` until D2 introduces typed result (internal) while keeping `Path | None` externally.

## Auditor summary (code_context)
- D1 inverted: --throttled-rate still injected; throttled_rate default 100000 ge=50000; no --ignore-config.
- D2: no typed launch result, no WinError 32 classification, no file-access retry flags.
- D3: ready; artifact compatibility classification and safe quarantine implemented.
- D4: partial; publish_verified_file, validate_media_file exist; deep_decode unused.
- D5: partial; fallback too broad; progress snapshot exists.
- D6: ready; task created (tests/docs/CI only).

## Notes
Each block will be executed with Auditor/Researcher/Planner as needed, then Implementor, then local validation + commit.
</content>
## D0 research notes (researcher, 2026-11-07)

### Chosen approach

1. **Programmable HLS server** — extend the existing aiohttp `tests/integration/fixtures/hls_server.py` instead of adding a second server. Add scenario-controlled byte delivery:
   - Fields: `slow_fragment: int | None`, `first_byte_delay_seconds: float`, `chunk_size: int`, `chunk_delay_seconds: float`, `fragment_count` (already, use 12 for D0).
   - For the slow fragment index, send a first byte/chunk after `first_byte_delay_seconds`, then `chunk_size` bytes followed by `asyncio.sleep(chunk_delay_seconds)`, so total throughput stays below `throttled_rate` while bytes still grow.
   - Keep distinct deterministic payloads per fragment index (already SHA-256 seeded) and correct `Content-Type: video/mp2t`.
   - Reuse the existing Range handling for byte-range checks; extend only to return the requested slice for the slow fragment so byte-range tests remain meaningful.
   - Bind to `127.0.0.1:0` and let the OS assign the port; no new dependencies.

2. **Windows file-lock simulation** — portable, no new dependencies:
   - Windows: a test helper/context manager opens the target `.part` with `ctypes.windll.kernel32.CreateFileW`, `dwDesiredAccess=GENERIC_READ|GENERIC_WRITE`, `dwShareMode=FILE_SHARE_READ|FILE_SHARE_WRITE` (deliberately omitting `FILE_SHARE_DELETE`), `dwCreationDisposition=OPEN_ALWAYS`/`OPEN_EXISTING`, and keeps the handle open until released by event or timeout.
   - POSIX: use `fcntl.flock(fd, LOCK_EX)` on the same path. This cannot reproduce delete-sharing semantics, so the WinError 32 path is covered by deterministic fault injection (monkeypatch `os.replace`/`Path.rename` to raise `PermissionError(winerror=32)`) plus a real-Windows integration test gated by `@pytest.mark.skipif(sys.platform != "win32", ...)`.
   - Rationale: matches the existing Windows ctypes probes in `ytdlp_downloader.py`/`workspace.py`; avoids adding `pywin32`/`portalocker`.

3. **Structured diagnostic events** — additive only:
   - Append `child_started` to `STRUCTURED_DIAGNOSTIC_EVENTS`; keep existing `child_exit`.
   - Extend `STRUCTURED_DIAGNOSTIC_FIELDS` with `pid`, `launch_number`, `phase`, `next_action`, `artifact_snapshot` (relative name -> size in bytes). `attempt_id` already exists.
   - Emit `child_started` immediately after `create_subprocess_exec` with `pid`, `launch_number`, `attempt_id`, redacted effective settings (`N`, throttled rate, ignore-config flag). Emit `child_exit` with `pid`, `launch_number`, `returncode`, `elapsed_seconds`, `last_error_code`, `phase`, `next_action`, and an artifact snapshot.
   - Capture artifact snapshots only when no write is active (before launch and after exit/reap), under the job lock, using relative paths and sizes; record `None` on `OSError`. Never include signed URLs, cookies, or absolute temp roots.

4. **Bounded final drain** — add a helper `bounded_drain(stream, *, timeout=2.0, max_bytes=262144, chunk_size=65536) -> bytes`:
   - Use a monotonic deadline; read chunks with `asyncio.wait_for(stream.read(chunk_size), timeout=remaining)`.
   - Stop at EOF, timeout, or byte cap; log `child_drain_truncated` with captured byte count when a cap is hit.
   - After the primary reader completes or is cancelled, call `bounded_drain` to capture the tail, append to `output_chunks` and the transcript sink with the same redaction, then perform the existing `_await_ytdlp_reap_with_timeout`.
   - This removes the race between `process.wait()` and the reader without making the normal path slower.

5. **Process Monitor guidance** (real Windows only):
   - Filter: `Path` contains `.mp4.part` (or the target `.part`) and (`Process Name` is `python.exe`/`yt-dlp.exe` equivalent, or `Result` is `SHARING VIOLATION`).
   - Capture operations: `CreateFile`, `CloseFile`, `ReadFile`, `WriteFile`, `SetRenameInformationFile`/rename, `SetDispositionInformationFile`.
   - Columns: Time, Process Name, PID, Operation, Path, Result, Detail (Desired Access, Share Mode).
   - Correlate the holder PID with the diagnostic `child_started.pid` and `launch_number`.
   - Save both `.PML` and `.CSV`; keep the capture window bounded (ProcMon overhead affects timing, so use it for correlation, not acceptance metrics).

### Risks
- Slow-chunk timing may be too coarse to reproduce yt-dlp's throttled-rate re-extraction; keep delays configurable and compare `-N 1` vs the configured `-N`.
- Cross-platform confidence in the WinError 32 path depends on injected faults plus a real-Windows run; Linux `flock` does not model delete sharing.
- Adding diagnostic fields is additive, but any test asserting an exact event/field tuple must be updated; current tests only assert non-empty.
- A finite drain cap can still drop an unusually large tail; truncation is logged and the artifact snapshot provides the missing evidence.
- ProcMon capture overhead can change timing; treat it as correlation evidence only.
## D1 research notes (researcher, 2026-11-07)

### Findings

1. **yt-dlp `--throttled-rate` semantics (verified in installed 2026.07.04).**
   - Source: `yt_dlp/downloader/http.py` around the progress loop:
     `if speed and speed < (self.params.get('throttledratelimit') or 0):` with a
     3-second sustained check (`ctx.throttle_start`), then
     `raise ThrottledDownload` (a subclass of `ReExtractInfo`).
   - Effect: a sustained low speed causes yt-dlp to close the stream and
     re-extract info, restarting the download. With `--no-warnings` the
     "throttled" message is hidden, so this re-extraction is invisible to the
     outer retry budget. This confirms the plan's root cause.
   - Default in yt-dlp is `None` (disabled); passing `0` is equivalent to
     disabled. Removing the flag (or not passing it) disables the check
     entirely. **Conclusion: removing `--throttled-rate` from the managed
     command fixes the hidden re-extraction.**

2. **`--ignore-config`.**
   - Help: "Don't load any more configuration files except those given to
     --config-locations." (Alias `--no-config`.) Back-compat note: when the
     option appears inside the system config file, only the user config is
     skipped.
   - As an explicit CLI flag it skips system + user config files, making argv
     reproducible and preventing an external config from reintroducing
     `--throttled-rate` or changing `.part`/fragment-skip policy.
   - Compatibility boundary: users relying on global yt-dlp config (proxy,
     cookies, output templates) lose automatic application. Our managed
     invocation already passes cookies via stdin, User-Agent, Referer, quality,
     and output template explicitly. Proxy can still be supplied through
     `HTTP_PROXY`/`HTTPS_PROXY` env vars (yt-dlp honors them independent of
     config files). Document this boundary in `.env.example`, README, and
     troubleshooting docs.

3. **Diagnostic low-speed warning (sustained sampling).**
   - Measure speed only from downloaded **byte counts** parsed from progress
     lines (`_parse_ytdlp_progress_state` -> `downloaded`), never from percent
     or ETA (percent uses an estimated total; ETA is derived). Compute
     bytes/sec over a sliding window of the last N samples (recommend N=3)
     spanning at least the sustained window (recommend >=3s, matching yt-dlp's
     own 3s check).
   - Warn only when the sustained rate is positive but below
     `throttled_rate` (when `throttled_rate > 0`); if `0`, disable the
     warning. Do not change task state or trigger refresh.
   - Suppress repeats: emit at most once per low-speed episode; reset the
     episode flag when the rate recovers above threshold or bytes stop growing.
     Additionally cooldown (recommend 30s) between warnings in a long episode.
   - Keep the three situations distinct: (a) low speed with byte growth ->
     diagnostic warning only; (b) no byte growth -> existing
     `download_stall_timeout` path; (c) finalization wait -> separate phase.
   - Do not use percent/ETA as proof of progress/completion (consistent with
     D5).

4. **Config contract.**
   - `Settings.throttled_rate`: default `0` (disable), bounds `ge=0`,
     `le=1000000`. Positive values are interpreted as the diagnostic low-speed
     threshold. Old positive values (50000..1000000) remain valid.
   - If stricter "0 or >=50000" is desired, use a `field_validator`; minimal
     recommendation is `ge=0, le=1000000` to keep validation simple and
     backward-compatible. Document the semantic change in `.env.example`.

5. **Extractor library-mode.**
   - `_extract_with_ytdlp` passes `"throttled_rate": self.settings.throttled_rate`
     in `ydl_opts`. Extraction uses `download=False`, so media is not
     downloaded and `throttled_rate` has no effect. **Recommend removing the
     key** to eliminate dead config coupling and keep extraction independent
     of the download threshold. `test_extractor` expectation must be updated.

### Chosen path

1. Remove `--throttled-rate` from `_build_ytdlp_cli_command` entirely (no
   conditional injection).
2. Add `--ignore-config` to the managed CLI command for reproducibility.
3. Change `Settings.throttled_rate` to `default=0`, `ge=0`, `le=1000000`.
4. Remove `"throttled_rate"` from `ydl_opts` in `extractor._extract_with_ytdlp`.
5. Repurpose `throttled_rate` as the diagnostic low-speed threshold with a
   sustained-sampling, repeat-suppressed warning in the child output reader;
   no state change or refresh.
6. Update affected tests (`test_cli_command_includes_throttled_rate` ->
   assert absence / new contract, `test_config` default 0, `test_extractor`
   no key) and documentation (`.env.example`, README, troubleshooting).

### Rationale

- Directly removes the confirmed trigger of hidden re-extraction
  (`ThrottledDownload` -> `ReExtractInfo`) on slow channels while keeping a
  user-facing diagnostic for genuinely slow links.
- `--ignore-config` makes the managed argv deterministic and prevents
  external config from silently re-enabling throttled re-extraction.
- Repurposing the existing setting preserves the env var name and backward
  compatibility for positive values, minimizing migration cost.
- Removing the dead key from extractor keeps library-mode aligned with the
  fact that extraction does not download media.

### Risks

- Without `--throttled-rate`, a CDN that genuinely throttles will no longer
  cause yt-dlp to re-extract automatically; D5's bounded network fallback
  and D3/D4 artifact handling must carry recovery. Acceptable per plan.
- `--ignore-config` removes global-config conveniences (proxy/cookies/output
  templates); must be documented. Env-based proxy still works.
- Sustained-sampling warning adds reader-side state; must avoid false
  positives during initial ramp-up (use a minimum sample count/window) and
  must not use percent/ETA.
- Default change breaks existing tests/assertions expecting 100000; tests
  are updated as part of the block.
- Extractor test change couples to the removed key; update in same commit.
\n\n## D2 research notes (researcher, 2026-11-08)\n\n### Verified facts\n\n1. **yt-dlp file-access retry flags (installed 2026.07.04, lockfile same).**\n   - `--file-access-retries RETRIES` exists; default is 3. `--retry-sleep [TYPE:]EXPR`\n     accepts `file_access` as a type (`http|fragment|file_access|extractor`).\n   - Implementation: `yt_dlp/downloader/common.py::wrap_file_access` wraps `sanitize_open`,\n     `try_remove`, and `try_rename`; it catches `OSError` and retries only when\n     `err.errno in (errno.EACCES, errno.EINVAL)`. On Windows `WinError 32`\n     (`ERROR_SHARING_VIOLATION`) surfaces as `PermissionError` with `errno == EACCES`\n     (13) and `winerror == 32`, so it is retried. Sleep is taken from\n     `params["retry_sleep_functions"]["file_access"]` (empty by default).\n   - Conclusion: explicitly passing `--file-access-retries 3` and\n     `--retry-sleep file_access:0.5` is supported and makes the 3 x 0.5 s budget\n     deterministic. Applicability verified on the installed/lockfile version.\n\n2. **WinError 32 mapping.**\n   - `PermissionError.winerror` is `32` on Windows and `None` on POSIX.\n   - On POSIX the equivalent is `errno.EACCES`/`EPERM`/`EBUSY` plus a sharing/lock\n     message; `fcntl.flock` tests cannot reproduce delete-sharing, so non-Windows\n     coverage relies on fault injection (`os.replace`/`Path.rename` raising\n     `PermissionError(winerror=32)` or a message containing \"sharing violation\").\n\n3. **Typed result contract.**\n   - `_download_with_ytdlp` must keep returning `Path | None` for all external\n     callers (batch, CLI, tests). The typed outcome is an internal detail: add an\n     internal coroutine `_download_with_ytdlp_result(...)` returning a frozen\n     dataclass, with `_download_with_ytdlp` as a thin compatibility wrapper.\n\n### Chosen approach\n\n1. **File-access retry flags in the managed argv.**\n   - Add to `_build_ytdlp_cli_command`:\n     `--file-access-retries 3` and `--retry-sleep file_access:0.5`.\n   - Keep them as module constants (`_YTDLP_FILE_ACCESS_RETRIES = 3`,\n     `_YTDLP_FILE_ACCESS_RETRY_SLEEP = 0.5`) rather than new settings fields for\n     this block; promotion to settings is optional later (D6 docs).\n\n2. **Internal typed launch result.**\n   - Add a frozen dataclass `YtdlpLaunchResult` in `ytdlp_downloader.py`:\n     phase: str              # \"completed\" | \"failed\" | \"cancelled\" |\n                             # \"file_locked\" | \"local_block\" | \"missing_output\"\n     returncode: int | None\n     error_category: ErrorCategory\n     candidate: Path | None = None   # staging candidate on success/partial\n     last_error_code: str | None = None\n     http_status: int | None = None\n     operation: str | None = None    # \"fragment_rename\" | \"part_rename\" |\n                                     # \"staging_publish\" | ...\n   - Add `_download_with_ytdlp_result(...)` returning it. Keep\n     `_download_with_ytdlp(...)` returning `Path | None` by mapping\n     `phase == \"completed\"` to `candidate`.\n   - `download_with_ytdlp_with_resume_fallback` calls the typed variant and\n     inspects `phase`/`error_category` before deciding fallback.\n\n3. **WinError 32 classification.**\n   - Add one new `ErrorCategory.FILE_LOCKED = \"file_locked\"` (additive, no new\n     persisted fields).\n   - Implement a helper `_is_file_lock_error(exc)`:\n     - `getattr(exc, \"winerror\", None) == 32`, OR\n     - `errno in (EACCES, EPERM, EBUSY, EAGAIN)` AND a lowercase message\n       containing one of `sharing violation`, `being used by another process`,\n       `resource busy`, `winerror 32`.\n   - In `state_machine.classify_error`, check this before the generic\n     `EACCES`/`EPERM` permission branch so a sharing violation is not collapsed\n     into `PERMISSION_ERROR`.\n   - For non-`OSError` objects, inspect `str(error).lower()` for the same\n     substrings.\n   - Record the operation (`operation=...`) and redacted path in logs, not in the\n     category.\n\n4. **Budget separation (no new counters).**\n   - File lock is a terminal local outcome: do **not** call `record_retry`, do\n     not increment `retries_used`, do not request a refresh, and do not invoke\n     browser/HLS fallback or a new child.\n   - Network/auth/timeout/5xx failures keep using `record_retry` and the combined\n     budget; refresh keeps using `request_refresh`/`refresh_cap`.\n   - ffprobe-missing / validation / publish-conflict outcomes are classified as\n     `INTEGRITY_FAILURE` / `INVALID_OUTPUT_PATH` (reused) with a distinct\n     `reason_code` and `operation`, and are also terminal (no retry, no fallback).\n\n5. **Candidate handling on terminal file lock.**\n   - After a failed launch, capture `candidate` as the staging `.part`/staged path\n     when it exists and is non-empty; otherwise `None`.\n   - The fallback loop skips segment resume when\n     `result.error_category == ErrorCategory.FILE_LOCKED` (or\n     `result.phase in {\"file_locked\", \"local_block\", \"missing_output\"}`).\n\n### State machine / schema implications\n\n- Adding `FILE_LOCKED` to `ErrorCategory` is additive; persisted\n  `job_state.v2.json` files remain valid (the field is an enum value, no new\n  columns). `extra=\"forbid\"` on `DownloadJobState` is unaffected because no\n  field is added.\n- `tests/test_download_state.py::test_error_category_is_strenum` must add\n  `\"file_locked\"` to its expected set.\n- No migration is required; old state files with `permission_error` stay\n  `PERMISSION_ERROR`.\n\n### Risks\n\n- yt-dlp only retries `EACCES`/`EINVAL`; a sharing violation that surfaces with\n  a different `errno` (e.g. `EBUSY` on some platforms) would not be retried\n  internally and would terminate after one attempt. The 3 x 0.5 s budget only\n  covers the `EACCES` path; this is acceptable and is documented.\n- Substring-based classification can over-match unrelated permission errors;\n  mitigated by requiring `winerror == 32` OR (`errno` in the sharing set AND a\n  sharing-specific substring).\n- Introducing the typed result requires updating `download_with_ytdlp_with_resume_fallback`\n  in the same commit; leaving the old `None`-only path would lose the category\n  and could re-trigger segment fallback on a file lock.\n- Candidate paths must not be persisted in state (no secrets, but paths are\n  local); keep `candidate` in the in-memory result only, and continue persisting\n  only `error_category`/`reason_code`.\n- Hard-coded 3 / 0.5 s may be too short for a holder that releases after >1.5 s;\n  the terminal outcome is still correct (local recovery D4), just slower.\n\n### Recommended follow-up for implementation\n\n- Update `tests/test_ytdlp_downloader.py` to assert the new flags and a\n  `FILE_LOCKED` classification via fault injection.\n- Update `tests/test_download_state.py` expected `ErrorCategory` set.\n- Keep `_download_with_ytdlp` returning `Path | None` so existing tests and\n  callers remain green.\n

## D3 research notes (researcher, 2026-11-08)

### Verified facts

1. **yt-dlp `.ytdl` format is identical in locked 2026.07.04 and installed 2026.10.26.**
   - File: `<final>.ytdl`, JSON object `{"downloader": {"current_fragment": {"index": int}, "extra_state"?: ..., "fragment_count"?: int}}`.
   - No schema/version field and no byte-length, fragment-hash, or media-duration field.
   - `current_fragment.index` is the count of fully appended fragments (0-based next fragment to download), written after each fragment append. It is a resume hint only.
   - On resume, yt-dlp requires `continuedl` and an existing `.ytdl`; a corrupt file or `index > 0` with `.part` size 0 resets both to 0. If `.part` exists without `.ytdl`, yt-dlp appends in `ab` mode starting at fragment 0, which can duplicate earlier bytes (matches the incident snapshots).
   - Conclusion: `.ytdl` alone cannot prove the committed prefix length. Parse it as an untrusted hint; never adopt a `.part` solely because `.ytdl` exists.

2. **Safe `.ytdl` parsing.**
   - Read bytes only; `json.loads`; validate the exact shape and bounds (`index >= 0`, `fragment_count is None or >= index`, no extra executable content). Reject symlink/foreign/non-regular files before reading.
   - Do not delete an unreadable `.ytdl`; preserve it. Mark artifact state ambiguous.

3. **Stable VOD manifest fingerprint already exists.**
   - `compute_playlist_fingerprint` excludes URLs/tokens and includes variant id, codecs, resolution, target duration, HLS version, media sequence, discontinuity sequence, init-map identity, endlist/live, and per-segment duration/byte range/discontinuity/media sequence/init identity/key method. Use this as the required identity key; do not hash segment URLs.

4. **Workspace ownership and locking.**
   - `perform_download` acquires the job lock before `reconcile_commit_state`. `download_with_ytdlp_with_resume_fallback` receives that same `job_lock`. Artifact classification must run under that lock, without acquiring a second lock.

5. **Quarantine primitive exists.**
   - `quarantine_generation` renames a directory to `generations/<sanitized-gen>` and recreates an empty active directory. This is rename-only, no media copy, and is crash-durable on the same filesystem.

### Chosen path (minimal)

1. **Do not treat `.ytdl` as proof of prefix length.** Use it only as an optional hint. For yt-dlp artifacts, compatibility requires all of:
   - job ownership guards (resolved path under `tmp/jobs/<job_id>`, not a symlink, marker `.vkdownloader-job` content == `job_id`, artifact `final_name` == workspace final basename);
   - exact persisted identity match (`stream_variant_id`, structural `playlist_fingerprint`, and `init_map_sha256` when available);
   - independent media evidence for a complete `.part` (ffprobe container/codec/resolution and VOD duration/timestamp continuity allowing declared discontinuities).
   An incomplete or unproven `.part` is never appended to; it is either a candidate for local recovery (D4) or ambiguous.

2. **Classify artifacts under the job lock before launching another child.** Add a read-only classification step to `YtdlpArtifacts`/`_has_recoverable_ytdlp_artifacts` returning one of:
   - `compatible_resume` (own job, identity match, `.ytdl` consistent, media evidence acceptable) -> allow yt-dlp to continue with the existing `.part`/`.ytdl`;
   - `recovery_candidate` (complete media with valid identity but not proven as a resumable prefix) -> preserve for D4 local recovery;
   - `ambiguous` (foreign/missing/inconsistent identity, truncated, repeated TS blocks, bad `.ytdl`, symlink/neighbor path) -> quarantine and start a new generation;
   - `none`.
   Ambiguous/foreign artifacts are quarantined by renaming the whole `ytdlp/` directory to `ytdlp/generations/<gen>` and recreating an empty `ytdlp/`; no media is copied. If the rename fails, stop and preserve the data (`reason_code=artifact_isolation_failed`) instead of reusing or deleting it.

3. **Generation identity.** Reuse the existing `gen-N` convention. Persist `artifact_generation: str = "gen-0"` (and the playlist fingerprint/variant id) in `DownloadJobState` so the decision survives restart. Increment and quarantine on incompatibility. Segment and yt-dlp generations remain independent; the segment checkpoint is never derived from `.part-Frag*`.

4. **Legacy artifacts.** Keep `discover_legacy_artifacts` read-only. Do not auto-copy media into a workspace. Adoption, if explicitly requested, happens only under the job lock with the same ownership/symlink guards and is quarantined when identity cannot be proven. Legacy sets are preserved in place unless positively verified.

5. **Crash-safe durable decision.** Encode the decision in filesystem layout plus persisted identity fields, not in an in-memory directive. A restarted run reclassifies under the lock; already-quarantined generations are ignored, so an ambiguous file cannot be appended to after a crash. The operation is idempotent and safe to retry.

6. **Manifest fingerprint.** Use `compute_playlist_fingerprint` (structural, secret-free) for both segment checkpoints and yt-dlp job identity. Require exact match before any resume/recovery; on mismatch, quarantine and start a new generation.

### Rationale

- Uses existing primitives (job lock, quarantine rename, structural fingerprint, cleanup guards) instead of introducing a new artifact store or copying media.
- Treats `.ytdl` according to its actual format: a fragment counter with no prefix-length proof, matching the plan's explicit warning.
- Keeps yt-dlp's native resume path available only for the narrow compatible case, while routing everything else to isolation or D4 recovery.
- Avoids cross-job and symlink adoption by reusing the containment checks already required for cleanup.

### Risks

- Classifying a complete `.part` as `compatible_resume` still depends on yt-dlp's own consistency; media evidence is required before trusting it, or a duplicated-prefix file could be reused.
- Rename-based quarantine assumes the active and quarantine directories are on the same filesystem/volume; a cross-device failure must leave the original untouched and mark the job terminal for manual handling.
- Adding persisted identity fields changes `DownloadJobState`; old state files remain valid only if defaults are provided and missing keys are tolerated.
- Keeping legacy artifacts in place leaves operator-visible residue; cleanup remains tied to successful final publication.
- ffprobe-based media evidence is a later D4 dependency; D3 can only classify and isolate, not prove completeness.

## D4 research notes (researcher, 2026-11-08)

### Verified facts

1. **ffmpeg stream copy is sufficient for TS->MP4.**
   - `ffmpeg -i input.ts -map 0:v:0 -map 0:a:0? -c copy ... output.mp4` remuxes without
     decoding; H.264 video and AAC audio are accepted by the MP4 muxer. AAC in TS is ADTS and
     must be converted with `-bsf:a aac_adtstoasc` for MP4. `-movflags +faststart` is optional
     and only reorders atoms after the copy.
   - The command changes the container only; it does not repair corrupt packets or timestamps.
     Therefore it is valid only after independent completeness proof of the TS candidate.

2. **ffprobe is the existing validation primitive.**
   - `validate_media_file` already checks existence, size, ffprobe JSON, streams, height,
     duration tolerance, container token, and optional deep decode.
   - For a TS candidate, call it with `expected_container="mpegts"` (or `"ts"`) before remux.
   - For the remuxed result and final MP4, call it with `expected_container="mp4"`.

3. **The incident candidate is complete-looking but duplicated.**
   - ffprobe reports a plausible ~118.8 s duration even though the TS contains repeated blocks
     and DTS resets. Duration alone is therefore insufficient; timeline continuity is required.

4. **deep_decode is already implemented but unused.**
   - `_deep_decode` runs `ffmpeg -i <file> -f null -` and fails on decode errors. It is an
     additional integrity check, not a container/timestamp check.

5. **Publication is already atomic and no-clobber.**
   - `publish_verified_file` copies to a temp file, fsyncs, commits with `os.link` (no-clobber),
     has an `os.replace` fallback only for unsupported hard-link errors, sweeps stale temp
     files, and refuses to overwrite an existing final.
   - `reconcile_commit_state` already recognizes a valid final or staging candidate after a
     crash.

### Chosen approach (minimal)

1. **Candidate proof before remux (under the job lock).**
   - Resolve the candidate path from `_ytdlp_candidate_path` / staging and require D3 identity
     match (job root, variant, playlist fingerprint, init-map, generation).
   - Run ffprobe with `expected_container="mpegts"` (or `"ts"`), expected height, and expected
     duration when available. Duration tolerance: `max(2.0, 0.01 * expected_duration)`.
   - Run a timeline-continuity check on the video stream using
     `ffprobe -select_streams v:0 -show_entries packet=dts`:
     * require at least two packets;
     * count backward DTS jumps larger than 0.1 s;
     * allow at most the declared discontinuity count from the playlist;
     * require the final DTS to be within the duration tolerance of the expected duration.
   - If any check fails, classify the candidate as `recovery_candidate` or `ambiguous`
     (per D3), preserve it, and do not remux or publish.

2. **Remux only a proven candidate.**
   - Build the ffmpeg argv as:
     `ffmpeg -hide_banner -loglevel error -y -i <candidate> -map 0:v:0 -map 0:a:0? -dn -sn -c copy`
     plus `-bsf:a aac_adtstoasc` only when ffprobe reports AAC audio, plus
     `-movflags +faststart`, writing to `<staging_dir>/.<final>.remux-<pid>.tmp`.
   - If ffmpeg is missing or exits non-zero, preserve the candidate and return a
     `local_block`/`ffmpeg_missing` or `remux_failed` outcome; do not delete the candidate.
   - After ffmpeg exits 0, validate the temp with ffprobe (`expected_container="mp4"`,
     height, duration). Then atomically `os.replace` it to `staging_path`.

3. **Optional deep decode.**
   - Call `validate_media_file(..., deep_decode=True)` on the remuxed staging file before
     publication only for D4-recovered candidates, or when the caller explicitly requests it.
   - Keep `deep_decode=False` for ordinary yt-dlp finalization to avoid avoidable CPU cost.
   - On failure, preserve the candidate and return `local_block`.

4. **Publish and finalize under the job lock.**
   - Acquire the publish lock inside the held job lock.
   - `publish_verified_file(staged, final, final_lock=publish_lock)`.
   - Validate the final MP4 with ffprobe (`deep_decode` only if requested for recovery).
   - Advance state to `FINAL_COMMITTED` / `CLEANUP_OWNED_TEMP_ARTIFACTS`, call
     `cleanup_owned_job_artifacts`, persist state, then release the job lock in `finally`.

5. **Durable completion evidence (reuse identity fields).**
   - Do not invent a separate completion flag. The evidence is the existing tuple
     `(artifact_generation, artifact_stream_variant_id, artifact_playlist_fingerprint,
     artifact_init_map_sha256)` plus `fragment_total`/`expected_segments` and, when available,
     an optional `artifact_expected_duration_seconds` (default `None` for old state files).
   - While a candidate is being recovered, keep `artifact_classification="recovery_candidate"`.
   - After successful publication, the durable proof is the committed MP4 plus
     `FINAL_COMMITTED`; restart recognition happens through `reconcile_commit_state`.

6. **No-clobber identity verification.**
   - If `final` already exists, `reconcile_commit_state` may return `ALREADY_COMMITTED`
     only after ffprobe validation and identity match against the persisted job state.
   - If the final exists but identity cannot be established, do not overwrite it; return a
     distinct `DESTINATION_CONFLICT` directive (preferred) or an equivalent reason code and
     preserve artifacts. `publish_verified_file` remains the hard no-clobber guard.

7. **Crash recovery.**
   - Reuse `reconcile_commit_state`: a valid final returns `ALREADY_COMMITTED`; a valid
     staging candidate returns `PUBLISH_STAGING`; otherwise preserve/reprove the TS candidate.
   - Leftover ffmpeg/publish temp files are swept by the next `publish_verified_file`.
   - Candidate proof and remux are idempotent; a crash before state persistence simply
     repeats the proof on restart.

### Rationale

- Reuses existing primitives (`validate_media_file`, `publish_verified_file`,
  `reconcile_commit_state`, job/publish locks, identity fields) instead of introducing a new
  artifact store or copying media.
- Separates proof (TS) from remux (MP4) from publication, giving distinct outcomes and
  preserving ambiguous candidates.
- Avoids re-encoding, preserving quality and keeping CPU cost low; deep decode is opt-in.
- Keeps the no-clobber and crash-recovery behavior already implemented for staging/final.

### Risks

- TS duration plus DTS continuity is strong but not a byte-for-byte fragment audit; a
  candidate could still contain an extra trailing fragment while remaining decodable. Mitigate
  by requiring exact expected duration tolerance and zero unexpected backward DTS jumps.
- ffmpeg codec compatibility is assumed (H.264/AAC for VK VOD). If a future source uses
  codecs the MP4 muxer rejects, remux fails and the candidate is preserved rather than
  published.
- deep_decode can be expensive and may time out on large files; keep it opt-in and bounded.
- Holding the job lock through ffmpeg remux serializes same-job work; acceptable because
  remux is bounded and runs only on the recovery path.
- `DESTINATION_CONFLICT` requires a small enum addition to `CommitRecoveryDirective`; if
  avoided, the same safety can be represented by a reason code, but the distinct directive is
  clearer.

## D5 research notes (researcher, 2026-11-08)

### Verified facts

1. **Reason classification primitives already exist.** `classify_http_status` in
   `retry_policies.py` maps 401/403/410 -> `AUTH_EXPIRED`, 429 -> `RATE_LIMITED`,
   5xx -> `SERVER_ERROR`, 408 -> `CONNECTION_TIMEOUT`. `YtdlpLaunchResult` already
   carries `error_category`, `last_error_code`, `http_status` (currently always
   `None`), `file_conflict`, `cancelled`. `_derive_last_error_code` extracts a
   3-digit status from the child tail. So routing can be done without new
   parsing code — only wiring.

2. **Refresh allowance exists but is not consumed on the segment path.** `_fetch_playlist_with_retry`
   calls `state_machine.request_refresh("token_expired")` before `_handle_token_refresh`
   and aborts when the cap (2) is exhausted. `_attempt_segment_resume` calls
   `refresh_stream` directly and never calls `request_refresh`, so the cap is
   bypassed there. Variant/quality re-check already exists in `_attempt_segment_resume`
   (lines ~2087-2111) and returns `PRESERVE_AND_STOP` on mismatch.

3. **Backend switch is unbounded today.** `download_with_ytdlp_with_resume_fallback`
   can call `_attempt_segment_resume` once per retry iteration; nothing prevents a
   second switch after the first fails. The diagnostic event `backend_switch_blocked`
   is reserved in `STRUCTURED_DIAGNOSTIC_EVENTS` but never emitted. No
   `segment_backend_used` field exists in `DownloadJobState`.

4. **Network retry charging is mostly correct but not segment-aware.** The yt-dlp
   loop increments `retry_count` and calls `record_retry` only after the terminal-local
   check and before the backoff wait, so local/file outcomes are not charged. The
   segment downloader does not call `record_retry` at all, so its retries do not
   share the combined budget (6).

5. **Progress already separates verified disk bytes from network bytes.**
   `ProgressSnapshot` has `verified_bytes_on_disk` and `network_bytes_this_session`;
   both yt-dlp and segment paths populate them from `job_state`. yt-dlp sets
   `eta_seconds=progress_state.eta_seconds` with `is_estimate=progress_state.is_estimate`,
   so negative/unreliable ETAs are already filtered by the parser. There is no
   `FINALIZING` phase in `JobPhase`.

6. **Missing-fragment handling exists but lacks a reason code.** `_tally_and_merge`
   returns `None` when `downloaded_count != len(segments)` and on any failed
   segment index; the caller preserves artifacts. No state transition or
   `reason_code` is recorded for "missing required fragment".

### Chosen approach (minimal)

1. **Populate `http_status` on the yt-dlp result.** In `_download_with_ytdlp_result`,
   set `http_status=int(last_error_code)` when `last_error_code` is a 3-digit HTTP
   status, else `None`. No new parsing. This is the single enabler for reason-based
   routing.

2. **Reason-based routing in `download_with_ytdlp_with_resume_fallback`.** After the
   existing terminal-local check, branch on `result.error_category` / `http_status`:
   - `CANCELLED` -> record cancellation, return `None`.
   - `FILE_LOCKED`, `INVALID_OUTPUT_PATH`, `INTEGRITY_FAILURE`,
     `INCOMPATIBLE_PLAYLIST`, `INCOMPATIBLE_CODEC`, `NOT_FOUND`, `DISK_FULL`,
     `PERMISSION_ERROR` -> persist reason + category, return `None` (no retry,
     no switch). Add `INCOMPATIBLE_*`/`INTEGRITY_FAILURE` to this terminal set.
   - `AUTH_EXPIRED` (401/403/410): consume refresh allowance *first* via
     `state_machine.request_refresh(...)`; on False, persist `refresh_cap_exhausted`,
     return `None`. On True, refresh stream, run the existing quality/variant check;
     on mismatch persist `refresh_mismatch` + `INTEGRITY_FAILURE`, return `None`.
     On success, attempt the segment switch (step 4) with the refreshed binding.
   - `RATE_LIMITED` (429): if a coordinator is present, `await coordinator.pause(...)`
     (using `pause_seconds`); otherwise use `_compute_backoff_delay(429, retry_count, None)`.
     Honor any `Retry-After` parsed from the sanitized tail if present. Then retry
     yt-dlp (do not switch backends for a pure rate limit).
   - `SERVER_ERROR`, `CONNECTION_TIMEOUT`, `CONNECTION_RESET`, `UNKNOWN` with a
     network-ish failure: bounded backoff retries (existing path). Only after the
     retry budget is exhausted *and* artifacts are `COMPATIBLE_RESUME` may the
     single segment switch (step 4) be attempted.

3. **Charge a retry only when actually scheduled.** Keep `record_retry` where the
   backoff wait is actually performed. For the segment backend, thread
   `state_machine` through `_run_download_session` (already present) and call
   `record_retry(scope="segment", ...)` inside `_fetch_playlist_with_retry` and the
   segment retry loops *only* when a retry wait is about to happen; on
   `is_budget_exhausted()` return `None`. This makes segment retries share the
   combined budget instead of an independent counter.

4. **Bounded backend switch (one per job).** Add `segment_backend_used: bool = False`
   to `DownloadJobState` (default False, persisted). Before calling
   `_attempt_segment_resume`:
   - if `segment_backend_used` is True, emit `backend_switch_blocked` with
     `reason_code="backend_switch_already_used"`, persist, return `None`.
   - set `segment_backend_used = True`, persist, then call `_attempt_segment_resume`.
   - regardless of its result, do **not** return to the yt-dlp loop afterwards
     (break / return its result) — this prevents unlimited alternation. On failure,
     return `None` and preserve artifacts.
   - pass the refreshed binding (from step 2) as `stream_binding` and the original
     `stream_variant_id`.

5. **HLS compatibility before/within the switch.** Keep the switch attempt inside
   `_attempt_segment_resume`, which already verifies quality + variant. Add one
   guard at its start: consume refresh allowance via `request_refresh` when the
   switch is triggered by an auth-expired result (already done in step 2, so do not
   double-count). The segment downloader's existing checkpoint reconciliation
   handles compatible vs incompatible manifests (quarantine + new generation), so an
   incompatible playlist cannot contribute an old fragment. No new quarantine logic.

6. **Fail on missing mandatory fragment.** In `_tally_and_merge`, when
   `downloaded_count != len(segments)` or any segment failed, if `state_machine`
   is present transition to `FAILED` (or `PRESERVE_AND_STOP`) with
   `reason_code="missing_required_fragment"` and `error_category=NOT_FOUND`/`UNKNOWN`,
   then return `None`. Preserve artifacts (already). Add the same reason when a
   zero-exit yt-dlp result has incomplete media (`missing_output`/`local_block`).

7. **Progress reporting.** Add `FINALIZING` to `JobPhase`. In `_download_with_ytdlp_result`,
   emit a final progress snapshot with `phase=JobPhase.FINALIZING` and
   `eta_seconds=None` during candidate validation/publication and file-access retries.
   Keep `verified_bytes_on_disk` from `job_state.verified_bytes` and
   `network_bytes_this_session` from `job_state.network_bytes_this_session` (never
   from yt-dlp's `~` estimate); keep `is_estimate` on child-driven snapshots.
   Ensure `verified_*` counters only move forward (already in
   `update_progress_counters`).

8. **No unlimited alternation.** Enforce via: refresh cap (2), combined retry
   budget (6), `segment_backend_used` flag (1), and the rule that a failed segment
   switch returns `None` instead of re-entering the yt-dlp loop.

### Rationale

- Reuses existing classification (`classify_http_status`, `ErrorCategory`), refresh
  cap, retry budget, checkpoint reconciliation, and progress snapshot machinery
  instead of introducing new subsystems.
- Makes routing depend on the *confirmed* failure reason rather than treating every
  yt-dlp failure as a network problem, which is the root cause of the "too broad"
  fallback.
- Consuming the refresh allowance *before* invoking refresh prevents a refresh that
  succeeds but is then discarded from silently consuming a later slot; it also makes
  the 403 fixture consume exactly one refresh.
- A single boolean guard is the smallest mechanism that bounds backend changes
  while remaining crash-durable (persisted in job state).
- Charging retries only at scheduling time keeps the budget honest for both yt-dlp
  and segment paths and avoids counting immediate failures.

### Risks

- `http_status` derivation from `last_error_code` depends on yt-dlp actually
  printing an HTTP status; some network failures (DNS, timeout) yield no status and
  fall into the retry bucket, which is acceptable but means routing is conservative.
- Adding `segment_backend_used` changes `DownloadJobState` (extra field with
  default) and requires migration tolerance for old state files; follow the same
  default-and-tolerate pattern used for `artifact_*` fields.
- Adding `JobPhase.FINALIZING` changes the `JobPhase` enum and any exhaustive
  match/display code; verify progress display handles unknown phases gracefully.
- Refresh consumption before variant verification means a variant mismatch still
  spends one refresh slot; this is intentional (the refresh happened) but should
  be documented. If the variant check is moved before refresh, the cap semantics
  change.
- Sharing the combined budget between yt-dlp and segment paths could exhaust it
  faster on jobs that legitimately need both; the existing cap (6) and refresh cap
  (2) are the agreed bounds and should not be raised in this block.
- Segment-path retry charging requires careful placement to avoid double-counting
  when `_fetch_playlist_with_retry` retries and then segment fan-out also retries;
  prefer charging at the playlist level only, and keep per-segment retries inside
  the existing `max_retries` budget without separate `record_retry` calls.

## D6 research notes (researcher, 2026-11-08)

### Verified facts

1. **Real Windows handle holder already exists.**
   - `tests/integration/fixtures/windows_lock.py` provides `WindowsDescriptorHolder` and
     `windows_lock`, which on Windows opens the target with `CreateFileW` using
     `FILE_SHARE_READ | FILE_SHARE_WRITE` (deliberately omitting
     `FILE_SHARE_DELETE`) and holds it until released by event/timeout.
   - `tests/test_windows_lock.py` exercises the holder and is gated by
     `@pytest.mark.skipif(sys.platform != "win32", ...)`. On POSIX the helper falls
     back to `fcntl.flock`, which cannot reproduce delete-sharing semantics.
   - Conclusion: the real-descriptor path can be exercised on `windows-latest` CI
     without new dependencies; Linux coverage stays on deterministic fault
     injection (monkeypatch `os.replace`/`Path.rename` to raise
     `PermissionError(winerror=32)` or a message containing "sharing violation").

2. **CI matrix already covers both platforms.**
   - `.github/workflows/packaging-check.yml` runs on `ubuntu-latest` and
     `windows-latest` with Python 3.14, `uv sync --locked`, ruff, mypy, full
     `pytest tests/ tests/integration/`, coverage `--fail-under=85`, packaging,
     wheel smoke (Linux), pip-audit (Linux), and gitleaks.
   - The four command groups in the plan are subsets of the full suite already run
     in CI; they remain useful as a fast, named release checklist.

3. **Documentation is largely already aligned.**
   - `.env.example`, `docs/11-guides/configuration.md`, and
     `docs/11-guides/troubleshooting.md` already document `VKDOWNLOADER_THROTTLED_RATE`
     semantics (0 disables, positive = diagnostic threshold), `--ignore-config`,
     staging recovery/preservation, and the Process Monitor correlation procedure
     for `SHARING VIOLATION`.
   - README already documents the per-job workspace, resume, and troubleshooting link.
   - Remaining doc work is additive and low-risk: an explicit rollout/rollback
     subsection and a staging-recovery note in troubleshooting.

4. **Rollout/rollback primitives already documented.**
   - Troubleshooting already states: failed/cancelled jobs retain temp data; successful
     jobs remove only owned intermediates; revert of application code ignores newer
     workspaces; do not run broad cleanup against `output/tmp`.
   - D3 quarantine (`quarantine_generation`) and D4 no-clobber publication provide
     the filesystem-level safety that the rollback note relies on.

### Chosen approach

1. **Windows acceptance strategy: two-tier, no new infrastructure.**
   - Tier 1 (Linux/CI simulation): keep deterministic fault injection for
     `WinError 32` / sharing-violation classification, used for all unit/integration
     tests and for the four command groups. This is the only portable way to assert
     exact retry budgets and HTTP-request counts.
   - Tier 2 (real Windows): rely on the existing `windows-latest` matrix job to run
     the real `WindowsDescriptorHolder` path (`test_windows_lock.py`) and any
     Windows-gated end-to-end scenario. For the end-to-end sharing-violation case,
     hold a descriptor over the staging `.part` during a real download and release it
     after the 3 x 0.5 s budget; assert terminal `file_locked` outcome, preserved
     artifacts, and zero post-failure HTTP requests. Keep Process Monitor capture
     as correlation evidence only (documented; never an acceptance metric, because
     ProcMon overhead changes timing).
   - Do not add a second Windows runner type, a self-hosted runner, or a new
     dependency (no `pywin32`/`portalocker`).

2. **Documentation: additive edits only, in the same release commit.**
   - `.env.example`: keep the existing `VKDOWNLOADER_THROTTLED_RATE=0` block and its
     explanation; no new keys (file-access retry counts stay internal constants
     per D2).
   - `README.md`: add a one-line pointer to the troubleshooting rollout/rollback
     subsection (no duplication of the workspace tree).
   - `docs/11-guides/troubleshooting.md`: add a short "Staging recovery" note
     (terminal `file_locked` preserves the candidate; recovery runs locally with zero
     HTTP requests after the lock clears) and a "Rollout and rollback" subsection:
     * Rollout: use a separate output directory on a real VK VOD; run with
       `--method auto` and `--method yt-dlp`; inspect `<output>/tmp/logs/<job>.jsonl`
       for one downloader start, one extraction, and the failing phase/next action.
     * Rollback: stop the active process; preserve `output/tmp/jobs/*` generations
       separately; run the old version in a *different* output directory so it
       cannot append to a new or damaged generation; never delete `output/tmp/logs`.
   - No changes to `docs/11-guides/configuration.md` beyond what D1/D5 already
     added; `throttled_rate` semantics are already there.

3. **CI/release gate: keep the existing matrix, add a documented command checklist.**
   - Keep `packaging-check.yml` as the single gate: both OSes, Python 3.14, locked
     deps, ruff check/format, mypy strict, full pytest, coverage >= 85, build,
     wheel smoke, packaging manifest test, secret scan.
   - Publish the four plan command groups as the *targeted* pre-merge checklist
     (run locally and in release notes), not as separate workflow jobs, to avoid
     duplicating the full suite:
     1. `uv run pytest tests/test_ytdlp_downloader.py tests/test_hls_downloader.py -q`
     2. `uv run pytest tests/test_download_state.py tests/test_workspace.py tests/test_media_validation.py -q`
     3. `uv run pytest tests/test_checkpoint.py tests/test_diagnostics.py tests/integration/test_hls_fixture.py -q`
     4. `uv run pytest tests/test_cli.py tests/test_batch_downloader.py tests/test_progress.py tests/test_progress_display.py -q`
   - Release acceptance (manual, recorded in the release notes):
     * one downloader start and one generic extraction during an uninterrupted slow
       transfer;
     * zero additional HTTP requests after a terminal finalization failure;
     * exactly one copy of every required fragment;
     * publication of only a verified MP4;
     * logs identify the failing phase and next action;
     * temp artifacts preserved on cancellation or unrecoverable failure.

4. **Rollout/rollback procedure (minimal, documented only).**
   - Rollout: ship the locked wheel/sdist from the CI artifacts; start with a real
     VK VOD in a separate output directory; keep the old version's output directory
     untouched; verify against the fixture's expected duration/frame sequence or
     reference checksums before declaring success.
   - Rollback: stop the active process; do not delete or rewrite generations; run
     the previous version in a separate output directory; quarantine (rename)
     ambiguous generations rather than deleting. Cross-device quarantine failure
     leaves the original untouched and marks the job terminal for manual handling.
   - No database migration is involved; `output/tmp` is user data and older code
     ignores unknown generations.

### Rationale

- The real-descriptor holder and the fault-injection path are both already
  implemented and tested; D6 only needs to *run* and *document* them, not build a
  new harness. This keeps the release gate honest on Windows while staying green on
  Linux CI.
- Keeping the four command groups as a documented checklist rather than new
  workflow jobs avoids duplicating the full suite and keeps CI cost unchanged.
- Additive documentation avoids touching the locked settings contract or the
  workspace layout, and reuses the existing quarantine/publication safety.
- A separate output directory for rollback is the smallest mechanism that prevents
  the old version from appending to a new or damaged generation, and matches the
  existing "treat `output/tmp` as user data" guidance.

### Risks

- Real Windows CI is the only place the delete-sharing path is exercised end to
  end; if `windows-latest` is unavailable or the holder test is skipped, the
  acceptance claim rests on fault injection plus a controlled manual run. Mitigate
  by recording the Windows run (and its Process Monitor correlation) in the release
  notes.
- Process Monitor capture is correlation-only; timing-sensitive acceptance
  metrics must come from the un-instrumented run.
- Documentation drift: the rollout/rollback subsection must be updated whenever the
  workspace layout or quarantine naming changes; keep it short and link to the plan.
- Coverage threshold (85%) applies to the whole suite; Windows-only branches
  (real holder) are excluded by skipif on Linux, so they do not affect the Linux
  coverage number. Ensure the Windows job also enforces the threshold or accept
  that Windows coverage is informational.
- No code or schema migration is performed in D6; if a later block adds fields to
  `DownloadJobState`, the release notes and troubleshooting must be refreshed.
