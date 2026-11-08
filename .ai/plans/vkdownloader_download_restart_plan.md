# Why VKDownloader restarts HLS downloads and how to fix it

**Incident date** November 7, 2026. This analysis uses the source code in `01-mko_vkideo-main.zip` and two snapshots of the same job in `tmp.7z` and `tmp2.7z`. Job `video-113218548_456241617-q480-1491d5df679d` ran on Windows with yt-dlp’s native HLS downloader at 480p and had 12 fragments. Times below are Moscow time (UTC+3). The source JSONL files use UTC.

## Diagnosis

**The confirmed failure occurs during finalization.** Windows returns `WinError 32` when yt-dlp tries to rename the assembled `.mp4.part` to `.mp4` inside the job’s `ytdlp/` directory, before the application publishes the output. This happened six times. In each episode, three file-operation retries were exhausted within roughly 23–25 ms of the first error message. After five of the six failures, the next visible attempt reports `frag 0/12`. The first snapshot ends at its last rename failure. The second ends with cancellation at `frag 7/12`.

**The leading explanation for the earlier restarts is yt-dlp’s low-speed re-extraction.** `_build_ytdlp_cli_command` always passes `--throttled-rate`. `Settings.throttled_rate` defaults to 100,000 bytes/s, and validation currently rejects `0`. Below the configured rate, yt-dlp can re-extract the input. Its input here is the signed playlist URL, so another generic extraction does not obtain a fresh token through VK. `--no-warnings` suppresses warnings, and the parent’s retry budget does not account for extraction loops inside the child. Of the 25 `[generic] Extracting URL` entries, two open the snapshots, five follow terminal rename failures, and 18 occur without a preceding terminal rename failure in that attempt. This pattern is consistent with internal re-extraction. The archives lack PIDs, complete command arguments, the child’s actual version, and its warnings. Confirm the trigger in a controlled reproduction, separately from the Windows sharing violation. The project archive’s `uv.lock` pins yt-dlp `2026.7.4`.

**The application turns a local failure into another download.** `_download_with_ytdlp` returns `None` for a nonzero child exit, a missing output candidate, a validation failure, or a publication failure. `download_with_ytdlp_with_resume_fallback` treats those outcomes alike and schedules a retry using the HTTP 500 backoff. If it finds temporary artifacts, it tries `_attempt_segment_resume` with a browser-based stream refresh. The segment backend uses its own checkpoint and cannot resume from yt-dlp’s assembled file. If the fallback yields no result, the loop launches yt-dlp in the same directory again. The presence of a `.part` or `.ytdl` can qualify the workspace for recovery without a consistency check. The snapshots confirm repeated writes to the same temporary file. Check exactly when yt-dlp updates or removes its `.ytdl` on the version that ran.

### Evidence from both snapshots

| Observation | `tmp.7z` | `tmp2.7z` |
| --- | --- | --- |
| Generic extraction starts | 13 | 12 |
| Terminal rename failures with `WinError 32` | 23:05:27, 23:06:21, 23:07:04, 23:07:48 | 23:18:44, 23:19:55 |
| Example of a reset after failure | The 23:05:27 failure follows `frag 11/12`. The next attempt reports `frag 0/12` at 23:05:30. | The 23:19:55 failure follows `frag 11/12`. The next attempt reports `frag 0/12` at 23:20:01. |
| Assembled `.part` | 84,427,792 bytes. `ffprobe` identifies MPEG-TS with 852×480 H.264 video and AAC audio. | 44,239,032 bytes, with the same container and stream properties. |
| Repeated data in `.part` | Three byte-identical blocks of 22,396,252 bytes start at offsets 0, 39,635,288, and 62,031,540. The remaining pass has a different length. Video DTS resets from 118.668 s to 0 s three times. | The first 64 KiB repeats at offsets 15,877,916 and 34,278,792. Video DTS resets from 118.668 s to 0 s twice. |
| Job state and yt-dlp checkpoint | State is `refresh_stream`, with `retries_used=4` and `refresh_count=0`. No `.ytdl` is present. | State is `cancelled`, with `retries_used=2` and `refresh_count=0`. The `.ytdl` records index 5. Complete and partial fragment files are present. |

The analysis compared file bytes and used `ffprobe -show_packets` on the video stream to locate the timestamp resets. `ffprobe -show_format` still reports about 118.8 s for the first file. A plausible overall duration and the presence of audio and video are insufficient to accept the assembled file. The logs show that yt-dlp reused some individual fragments. Its percentages, sizes prefixed by `~`, and ETAs are estimates.

The logs establish a Windows sharing violation. They do not identify which process held the handle. A handle retained by yt-dlp after re-extraction and a handle held by an external process are both hypotheses. The supplied transcripts contain no HTTP 403, 410, 429, or 5xx errors. They contain only `child_output` records, so the outcome of each browser refresh attempt is unknown.

## Implementation order

| Task | Priority | Dependencies | Outcome |
| --- | --- | --- | --- |
| D0. Reproduce and correlate | P0 | None | Independent reproductions for slow transfer and a Windows sharing violation |
| D1. Keep slow transfers running | P0 | D0 | A slow transfer continues while bytes are arriving |
| D2. Classify failures and bound file retries | P0 | D0 | A local sharing violation stops triggering network work |
| D3. Validate resume artifacts | P0 | D2 | Compatible artifacts resume and ambiguous generations are isolated |
| D4. Recover finalization locally | P0 | D2, D3 | A verified candidate can be published without another download |
| D5. Bound network fallback and report progress | P1 | D1, D2, D3 | Network recovery preserves verified progress and stays within its budget |
| D6. Verify on Windows and release | P0 | D1–D5 | Release gates cover slow transfers, file contention, and both resume paths |

### D0. Reproduce and correlate

- **Targets** — `tests/integration/fixtures/hls_server.py`, `_download_with_ytdlp`, `_await_first_and_cancel_others`, and `utils/diagnostics.py`.
- Extend the HLS test server with a valid VOD containing 12 distinguishable MPEG-TS fragments. In one scenario, sustain a positive transfer rate below the current threshold for one fragment. In the other, use a controlled Windows process to open the assembled `.part` without `FILE_SHARE_DELETE`. Release the handle on a signal or hold it until retries are exhausted. Run the scenarios independently and together. Record Python, yt-dlp, and FFmpeg versions and the effective settings. Compare `-N 1` with the configured concurrency.
- Write child start and exit events to the same JSONL as the transcript. Include the PID, application run ID, attempt ID, exit code, failure category, phase, next action, and relative artifact names and sizes. Distinguish re-extraction within one PID from a child restart. Record `.part` and `.ytdl` state at the process boundary, after active writes have stopped. Drain trailing output with time and size limits so the last error survives the race between `process.wait()` and the reader. Keep cancellation and process cleanup bounded. Redact signed URLs and cookies before writing.
- During reproduction on Windows, use Process Monitor to filter for the `.mp4.part` path and `SHARING VIOLATION`. Correlate open and close events, PIDs, and share modes for the source and destination. If only the controlled lock reproduces, record that the original handle owner remains unknown.
- **Acceptance** — the slow transfer and local lock are distinguishable by independent signals. The child exit event and terminal error survive a fast process exit.

### D1. Keep slow transfers running

- **Targets** — `Settings.throttled_rate`, `_build_ytdlp_cli_command`, and `.env.example`.
- Omit `--throttled-rate` from managed HLS launches. Keep `VKDOWNLOADER_THROTTLED_RATE` and its currently accepted positive values as an optional diagnostic warning threshold. Add `0` as the default to disable the threshold. Base warnings on sustained measurements and suppress duplicates. A low but positive transfer rate leaves the job running and triggers no stream refresh.
- Test `--ignore-config` for the managed child so external yt-dlp configuration cannot restore the throttle threshold, disable `.part` files, or override fragment handling. Document the compatibility change for users who rely on an external config. Preserve the application’s settings, cookies, User-Agent, Referer, and quality selection.
- Track slow transfer with rising byte counts, a genuine stall with no byte growth, and finalization as separate conditions. The current `download_stall_timeout` in this path bounds the wait for the child after stdout has been drained. If a watchdog for active transfers is introduced, test it separately.
- **Acceptance** — the slow HLS fixture without network errors shows one child start, one generic extraction, and each fragment once in the output. Replace the expectation in `test_cli_command_includes_throttled_rate` and cover `0`, an existing positive setting, and an external yt-dlp config.

### D2. Classify failures and bound file retries

- **Targets** — `_download_with_ytdlp`, `_derive_last_error_code`, `download_with_ytdlp_with_resume_fallback`, and `DownloadStateMachine`.
- Introduce an internal child result with the phase, exit code, failure category, and candidate path when available. Preserve the external `Path | None` and cancellation contracts. Recognize terminal `WinError 32` and distinguish a fragment rename, the assembled `.part` rename, and publication from staging. Derive HTTP status only from explicit HTTP messages. Ignore numbers in paths, progress updates, and transfer rates when classifying errors.
- Add a bounded file-access retry with an explicit delay in yt-dlp. Start fixture testing with three retries at 0.5 s intervals using `--file-access-retries` and `--retry-sleep file_access:0.5`. Verify support in the locked version and supported installations. When the wait expires, preserve artifacts and report the local sharing violation. Route that outcome to D4. It triggers no browser refresh, HLS fallback, or new downloader process.
- Separate file, network, and stream-refresh budgets. Assign distinct outcomes to missing ffprobe, access denied, disk full, destination conflicts, and media validation failures. Handle an error involving an existing staging candidate outside the network retry loop.
- **Acceptance** — the child completes after a short lock clears. A persistent lock yields a specific outcome within the retry window. The request count for playlists and fragments stops increasing after a terminal file error. Cover localized `WinError 32`, terminal 403, cancellation, missing child output, and publication failure.

### D3. Validate resume artifacts

- **Targets** — `YtdlpArtifacts`, `_has_recoverable_ytdlp_artifacts`, `DownloadWorkspace`, and `reconcile_commit_state`.
- After confirming that the old child exited, classify its artifacts under the job lock before launching another child. Check the generation, video and variant identity, playlist compatibility, and consistency of the bytes with the checkpoint. For known VOD, use stable identifiers that exclude secrets and URL signatures. Account for fragment order, media sequence, byte ranges, initialization segments, and discontinuities where applicable. Verify the exact `.ytdl` format and behavior against the locked yt-dlp version. The recorded index alone does not establish the length of the committed prefix.
- Distinguish a valid resume, a candidate for local recovery, and ambiguous artifacts. Start a separate generation when compatibility cannot be established. Preserve legacy artifacts in isolation unless there is positive evidence of their integrity. Both incident snapshots fail that check. Avoid unnecessary media copies and reject artifacts from another job, adjacent workspaces, and symlinks. If isolation fails, stop and preserve the data. The recovery decision must survive a crash and be safe to retry.
- Align lock ownership with `perform_download`. Load or migrate state, inspect files, and choose the active generation under the same job lock. On cancellation, persist reliable state for the old attempt and give the next attempt its own identifier. Keep the segment backend’s checkpoint independent of `.part-Frag*`.
- **Acceptance** — a compatible modern `.part` and checkpoint continue from the first missing fragment. A `.part` without a `.ytdl`, a foreign or truncated checkpoint, and repeated TS blocks are preserved outside the active generation. A crash and retry cannot append to an ambiguous file. Neither archived partial becomes a final MP4.

### D4. Recover finalization locally

- **Targets** — `reconcile_commit_state`, `validate_media_file`, `publish_verified_file`, and `DownloadStateMachine` transitions.
- Give candidate preservation, remuxing, validation, and publication distinct outcomes. When staging already contains a verified candidate, retry only the unfinished publication step. After a terminal `WinError 32` on an assembled `.part`, recover it locally only if independent evidence establishes that all required fragments are present, the variant matches, and the timeline is intact. Persist completion evidence for new jobs against the generation and playlist. If yt-dlp cannot provide enough evidence, preserve the candidate and use the safe recovery path once the lock clears.
- Remux a proven complete MPEG-TS file into an MP4 in staging. Verify the container, streams, requested quality, VOD completeness, and timestamp continuity while allowing declared discontinuities. Use deep decoding as an additional check where needed. For VOD with known duration, require a measured duration within tolerance.
- Use the existing no-clobber publication path. Hold the job lock through the final state write and owned-artifact cleanup. When the destination exists, require reliable job or content identity before treating it as a previously published result. A restart after atomic publication must recognize the committed file. Clean up only this job’s artifacts after the result is confirmed.
- **Acceptance** — a valid staging candidate is published after the lock clears with zero HTTP requests. Incomplete, duplicated, and foreign candidates are preserved. Concurrent publishers cannot overwrite the existing result.

### D5. Bound network fallback and report progress

- **Targets** — `perform_download`, `download_with_ytdlp_with_resume_fallback`, `_attempt_segment_resume`, `refresh_stream`, `download_hls_with_resume`, and `ProgressSnapshot`.
- Route confirmed 401, 403, and 410 responses through the bounded refresh path, consuming the refresh allowance before invoking it and verifying that the refreshed stream is the same variant. For 429, use the existing coordinator and honor `Retry-After`. Bound retries for timeouts and transient 5xx responses. Route playlist mismatches, integrity errors, cancellation, and local errors to their stop or recovery states. Charge a network retry only when scheduled. Persist the reason and preserve artifacts when the budget is exhausted.
- Switch to the segment backend only after establishing a network failure and checking HLS compatibility. Pass the original variant binding and recheck the requested numeric quality. Reuse the segment backend’s compatible checkpoint when available. If it has none, report that a new segment download has started and preserve the yt-dlp artifacts. Bound backend changes within each job and log the reason for each one.
- For HLS VOD, fail when a required fragment remains unavailable after retries. Check that a zero child exit with incomplete media cannot lead to publication. Report verified data on disk, estimated child progress, and bytes transferred in the current session separately. Show the finalization phase during file retries. Exclude estimated percentages and negative ETAs from integrity and completion decisions.
- **Acceptance** — the 403 fixture triggers one refresh, 429 observes the server delay, and 5xx retries remain bounded. The requested 480p variant and verified fragments survive compatible recovery. An incompatible playlist cannot contribute an old fragment to the final MP4.

### D6. Verify on Windows and release

1. Run the targeted suites on Python 3.14 with the locked dependencies. Use Linux for HTTP scenarios, integrity checks, and simulated failures. Run a real sharing violation in Windows CI or on a controlled Windows machine.
2. Exercise single and batch downloads with both `--method auto` and `--method yt-dlp`. Cover normal and slow transfers, short and persistent locks, cancellation and resume, HTTP 403/429/503, a missing required fragment, incomplete staging, both legacy snapshot patterns, and concurrent attempts at the same destination. Verify completeness against the fixture’s expected duration, frame sequence, or reference checksums.
3. Gate the release on one downloader start and one extraction during uninterrupted slow transfer, zero additional HTTP requests after a terminal finalization failure, exactly one copy of every required fragment, and publication of only a verified MP4. Logs must identify the failing phase and next action. Preserve temporary artifacts on cancellation or unrecoverable failure.
4. Document the meaning of `VKDOWNLOADER_THROTTLED_RATE`, staging recovery, and how to identify a Windows handle owner in `.env.example`, `README.md`, and `docs/11-guides/troubleshooting.md`. Start rollout with a real VK VOD in a separate Windows output directory. For rollback, stop the active process and preserve artifact generations separately. Use a separate output directory for the old version to prevent it from appending to a new or damaged generation.

```bash
uv run pytest tests/test_ytdlp_downloader.py tests/test_hls_downloader.py -q
uv run pytest tests/test_download_state.py tests/test_workspace.py tests/test_media_validation.py -q
uv run pytest tests/test_checkpoint.py tests/test_diagnostics.py tests/integration/test_hls_fixture.py -q
uv run pytest tests/test_cli.py tests/test_batch_downloader.py tests/test_progress.py tests/test_progress_display.py -q
```

## Handling the two saved snapshots

Preserve the original archives and job directories. After the fix, use a clean generation or a new output directory for a fresh download. Both supplied `.part` files contain repeated data, and the `.ytdl` in `tmp2.7z` cannot establish that its assembled file is safe to resume. Any manual salvage should work on a copy and verify a candidate pass against the original playlist before using it.

## Verification scope

The investigation covered both JSONL transcripts, archive inventories, job state, the `.ytdl`, the bytes in both `.part` files, and the launch, retry, and publication paths in the source. Local checks verified media format, timestamp resets, and byte-for-byte repetition. The original Windows handle owner and the trigger for the intermediate extractions remain to be verified by reproduction. The project requires Python 3.14. The analysis environment had Python 3.12, so the project test suite is part of the release verification.

Reference for the downloader flags and file-access retries. [yt-dlp download options](https://github.com/yt-dlp/yt-dlp#download-options)
