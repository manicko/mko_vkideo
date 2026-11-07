---
id: vkdownloader-troubleshooting
domain: guides
tags:
  - troubleshooting
  - diagnostics
  - resume
  - workspace
related:
  - vkdownloader-limitations-and-workarounds
  - configuration-guide
  - vkdownloader-overview
---

# Troubleshooting Guide

## Purpose

This guide explains the temporary workspace, retention, resume, diagnostics, exact-quality failures, optional direct FFmpeg backend, manual cleanup, and migration/rollback behavior for VK Video Downloader.

## Familiar Command Still Works

The long-standing invocation continues to work unchanged. The first new run creates the per-job temporary workspace automatically:

```powershell
vkdownloader download "https://vkvideo.ru/video-225794656_456244209" --quality 1440 --method yt-dlp --output "C:\data\Video\Shows" --no-ssl-verify
```

No migration step is required before running it.

## Temporary Workspace Layout

```text
C:\data\Video\Shows\
├── <final-video>.mp4                 # completed and validated only
└── tmp\
    ├── jobs\
    │   └── <job-id>\
    │       ├── job_state.v2.json           # durable job state
    │       ├── segment_checkpoint.v2.json  # HLS segment checkpoint
    │       ├── state.json                 # legacy read-only migration input
    │       ├── ytdlp\                     # yt-dlp fragments and partials
    │       ├── segments\                  # downloaded HLS segments
    │       ├── staging\                   # completed, not-yet-published media
    │       └── diagnostics\               # non-secret metadata
    ├── locks\
    │   └── <job-id>.lock                  # exclusive job lock (external)
    └── logs\
        └── <job-id>.jsonl                 # redacted per-job diagnostic log
```

- In-progress artifacts are never written at the output root.
- `tmp` is inside the designated output directory and on the same filesystem as the final MP4, which allows atomic promotion.
- Each job has its own directory; concurrent jobs do not share working files.

## Retention Policy

- Logs are retained even on success, subject to rotation. Configure rotation with `VKDOWNLOADER_LOG_MAX_BYTES` and `VKDOWNLOADER_LOG_BACKUP_COUNT`.
- Failed or cancelled jobs keep usable temp data for resume.
- Successful jobs remove only their owned intermediates after the final media is validated and published. Logs remain.
- There is no broad glob cleanup of the output directory and no irreversible automatic cleanup of incomplete jobs.

## Resume Behavior

- Resume uses the durable checkpoints at `job_state.v2.json` (job state) and `segment_checkpoint.v2.json` (HLS segment checkpoint). The legacy `state.json`, if present, is read-only migration input.
- Verified segments are recorded with size and SHA-256 and are checked before reuse.
- A token-only URL change reuses compatible segments; there is no false restart at byte zero.
- If media identity changes or is ambiguous, the old generation is quarantined in its job directory instead of being mixed or deleted.
- Corrupt or truncated segments are detected and redownloaded individually.

## Diagnostics and Logs

### Log location

When diagnostics are enabled (the default), a redacted per-job JSONL log is created automatically:

```text
<output>/tmp/logs/<job-id>.jsonl
```

View it:

```bash
# Linux/macOS
ls output/tmp/logs

# Windows PowerShell
Get-ChildItem -LiteralPath "output\tmp\logs"
```

`--log-file` adds or overrides the structured application log destination; per-job logs remain separate.

### Redacted diagnostics bundle

Collect filenames and sizes plus the JSONL logs. Do not include cookies or signed URLs:

```bash
# Linux/macOS
find output/tmp/jobs -type f -printf '%p %s bytes\n' | sort

# Windows PowerShell
Get-ChildItem -LiteralPath "output\tmp\jobs" -Recurse -File | Select-Object FullName, Length
```

Before sharing, verify that no signed URL parameters or cookie values are present:

```bash
grep -E 'sig=|expires=|cookie' output/tmp/logs/*.jsonl || true
```

Secrets are redacted from logs and checkpoints; never share cookies or full signed URLs.

## Exact-Quality Failures

`--quality 1440` (or any other height) is an exact match. If that height is unavailable, the command fails with exit code `1` and lists the qualities the video does offer. There is no silent downgrade. Partial data is preserved.

Example:

```text
Requested quality '1000' is not available for this video.
Available qualities: 106p, 178p, 268p, 358p, 536p, 804p, 1072p, 1610p
```

## Optional Direct FFmpeg Backend

`--method ffmpeg` is an optional, user-opt-in direct FFmpeg HLS transport. It is non-destructive: output is staged under `output/tmp` and published only after validation. A failure does not discard yt-dlp partials. Direct FFmpeg is distinct from the FFmpeg merge/remux step used by segment downloads.

Disable direct FFmpeg without reverting checkpoint or temporary-workspace improvements by choosing `--method yt-dlp` or `--method auto`. Those improvements remain available for every method.

## Feature Flags and Backend Selection

Backend selection is independent from workspace, checkpoint, and resume improvements. Direct FFmpeg can be disabled by method selection alone; no feature flag or rollback of those improvements is required.

## Manual Cleanup of Abandoned Job Folders

There is no irreversible automatic cleanup of incomplete jobs. Inspect first with a safe dry run:

```bash
# Linux/macOS
du -sh output/tmp/jobs/* 2>/dev/null

# Windows PowerShell
Get-ChildItem -LiteralPath "output\tmp\jobs" -Directory | ForEach-Object {
    $size = (Get-ChildItem -LiteralPath $_.FullName -Recurse -File | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{ Job = $_.Name; Bytes = $size }
}
```

Delete a specific abandoned job only after confirming no process holds its lock:

```bash
# Linux/macOS
rm -rf output/tmp/jobs/<job-id>

# Windows PowerShell
Remove-Item -LiteralPath "output\tmp\jobs\<job-id>" -Recurse -Force
```

Do not delete `output/tmp/logs` unless you intend to remove diagnostic history.

## `--keep-temp` Semantics

No `--keep-temp` flag is required: failed or cancelled jobs always retain usable temp data by default. If a future `--keep-temp` option is added, it would only control whether successful jobs also retain their intermediates beyond logs. It would not change failure-preservation semantics.

## Migration and Rollback

Reverting application code to an older version does not delete job workspaces created by the newer version. Treat `output/tmp` as user data: older code simply ignores it. Do not run broad cleanup commands against `output/tmp`.

## See Also

- [Limitations and Workarounds](vkdownloader-limitations.md)
- [Configuration Guide](configuration.md)
- [CLI Reference](../99-reference/cli-reference.md)

## Process Monitor (Windows) Correlation for SHARING VIOLATION

When a download fails with a Windows sharing violation, use Process Monitor to
correlate the holder of the `.mp4.part` file with the diagnostic child process.

1. Start Process Monitor and set a filter:
   - `Path` contains `.mp4.part`
   - AND (`Process Name` is `python.exe` or `yt-dlp.exe`-equivalent, OR `Result` is `SHARING VIOLATION`).
2. Capture operations: `CreateFile`, `CloseFile`, `ReadFile`, `WriteFile`,
   `SetRenameInformationFile` (rename), and `SetDispositionInformationFile`.
3. Display columns: `Time`, `Process Name`, `PID`, `Operation`, `Path`, `Result`,
   and `Detail` (including `Desired Access` and `Share Mode`).
4. Correlate the holder PID with the diagnostic `child_started.pid` and
   `launch_number` emitted by `_download_with_ytdlp`.
5. Save the capture as both `.PML` and `.CSV`. Keep the capture window bounded;
   Process Monitor overhead affects timing, so use it for correlation only, not
   acceptance metrics.
