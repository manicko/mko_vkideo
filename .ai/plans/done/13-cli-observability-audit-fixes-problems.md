# Audit Problems Report — Plan: 13-cli-observability-audit-fixes

**Plan status:** COMPLETE — all 17 blocks (B1–B17) implemented and verified. Plan renamed to `_done`, moved to `.ai/plans/done/`.
**Re-audit date:** 2026-10-12
**Verification method:** code inspection, commit log analysis, test suite execution, documentation cross-check.

## Executive Summary

All 17 blocks described in the plan have been fully implemented in the source tree.
The stale audit report dated 2026-10-09 (which claimed 8 blocks NOT DONE and 2 PARTIAL)
was written **before** the implementation commits landed. The implementation is complete,
tested, and documented. No code changes are required.

Test gate: **1084 passed, 3 skipped** (plan floor was 759 passed, 3 skipped). Lint clean,
format clean, mypy clean (32 source files, 0 issues).

## Block-by-Block Verification

| Block | Status | Evidence |
|-------|--------|----------|
| **B1** | DONE | `56258e2 fix(cli): give configuration failures their own exit code` — `cli.py` raises `typer.Exit(code=3)` in both `except _PreambleFailure` clauses (lines 482–484, 611–613). Reference docs list code `3` as configuration error. Tests: `test_download_preamble_failure`, `test_batch_preamble_failure`, `test_exit_code_3_distinct_from_1`. |
| **B2** | DONE | `3cc2897 feat(cli): add --log-level option and fix Live-1 hint (P13-B2)` — `--log-level` option declared byte-identically in both commands (`cli.py` lines 391, 541). `LogLevel` enum imported. `format_validation_error` hint references `--log-level`, not `--log-file`. Tests: `TestLogLevel`, `test_log_level_appears_in_both_help_with_identical_text`, `test_log_level_documented_in_both_reference_docs`. |
| **B3** | DONE | `65d1c0a fix(logging): clear exc_info on LogRecord to prevent double traceback (P13-B3)` — dedicated processor at `config.py:591–605` clears `record.exc_info` and `record.exc_text`. Tests in `test_config.py` verify traceback redaction through the processor chain. |
| **B4** | DONE | `17b0b8b feat(observability): add correlation_id + video_id to log records (P13-B4)` — `correlation_id` bound via `bind_correlation_id` contextvar; `video_id` added to `download_finished` record. Tests in `test_correlation.py` and `test_url_sanitizer.py`. |
| **B5** | DONE | `600af4d fix(cli): name max_retries bound in validation message (P13-B5)` — `Settings` model enforces `max_retries` range 1–10; out-of-range values exit `3`. Reference docs document bounds 1-10. Tests: `test_max_retries_out_of_range_exits_3` (lines 2749, 2775, 3147, 3171). |
| **B6** | DONE | `6a62e6c fix(logging): derive ConsoleRenderer colors from sys.stderr.isatty() (P13-B6)` — `config.py:677` calls `ConsoleRenderer(colors=sys.stderr.isatty())`. Terminal runs get color; redirected/CI runs get plain text. The "no escape codes" doc claim is now TRUE (not a deviation). Tests in `test_config.py` (115 insertions). |
| **B7** | DONE | `24dcddc feat(observability): record suppressed non-progress child output (P13-B7)` — non-progress yt-dlp lines now emit a structured `ytdlp_progress_suppressed` record instead of being dropped silently. |
| **B8** | DONE | `a2e6723 fix(batch): report the video count under a label that names videos` — `batch_downloader.py:636` prints `Total videos: {len(results)}`. Tests: `test_total_videos` asserts presence of the label. |
| **B9** | DONE | `270ab93 fix(batch): report a skipped item as skipped rather than failed` + `0cfe47f` — `ProgressStatus.SKIPPED` counted explicitly (line 623). `failed` derived by explicit count, not subtraction. `ProgressStatus.IN_PROGRESS` and `TERMINAL_STATUSES` frozenset in `enums.py`. |
| **B10** | DONE | `bfcac71 fix(progress): resolve the terminal question once per reporter` — `ProgressDisplay.is_enabled` (line 135) memoises `console.is_terminal` so the predicate is resolved once per instance. Tests: 86 insertions in `test_progress_display.py`. |
| **B11** | DONE | `94bfacf fix(progress): make teardown order-safe and terminalise in-flight tasks` — `stop()` (line 177) uses nested `try/finally` to guarantee `progress.stop()` and `_restore_log_handlers()` each run independently. Tests: 102 insertions in `test_progress_display.py`. |
| **B12** | DONE | `94bfacf` + `0cfe47f` — `_terminalise_tasks()` called before `progress.stop()` (line 206) so in-flight tasks get `CANCELLED`. `TERMINAL_STATUSES` frozenset guards terminal membership. Tests: `test_stop_terminalises_in_flight_task`, `test_in_progress_status_produced_and_terminalised`. |
| **B13** | DONE | `e6e6c68 TRN-008: use the ffmpeg availability answer at its single call site` — `except (ExtractionError, OSError)` narrowed to `except ExtractionError` (line 1088, comment "narrowed from (ExtractionError, OSError)"). OSError/FileNotFoundError now caught at merge level (arm b) with `merge_spawn_failed` event. 7 B13 tests added. Tests: `TestB13AvailabilityProbe`, `TestB13MergeMissingMuxer`, `TestB13ResumeErrorHandling`, `TestB13DownloadMissingBinary`. |
| **B14** | DONE | `0a1772a audit(B14): add working-tree provenance and dirty-tree gate to audit pipeline` — `BASE_CONTEXT` in audit commands now includes git SHA and dirty-tree check. |
| **B15** | DONE | `e9bafb2 audit(B15): add path-based exclusion list to orphaned-files audit` — explicit path-based exclusions added to `audit-orphaned.md` for `.ai/audit/**`, `.git/**`, `.venv/**`, `**/.kilo/worktrees/**`, etc. |
| **B16** | DONE | `fc3725f docs(B16): remove stale ffmpeg references from docstrings` — all three `method:` docstrings in `batch_downloader.py` corrected; unknown-total comment in `progress_display.py` updated. `grep` finds zero `ffmpeg`-as-download-method docstrings. |
| **B17** | DONE | `5fe961f fix(cli): name ffmpeg removal in --method help text (P13-B17)` — `--method` help text states: "The ffmpeg download method was removed; ffmpeg is still required to merge downloaded segments." Identical in both commands. Reference docs updated (lines 68, 137, 215). `TestMethodFfmpegRemoved` tests preserved. |

## Documentation Problems — Resolved

### 1. False claim about escape codes in non-terminal output — RESOLVED by B6

**Was:** `docs/99-reference/cli-reference.md` line 174, `docs/01-tools/api-reference.md`, `docs/01-tools/vkdownloader-overview.md` all claimed "no escape codes are written" to non-terminal output. This was FALSE because `ConsoleRenderer()` had no `colors=` argument, defaulting to colored output.

**Now:** B6 (`6a62e6c`) set `ConsoleRenderer(colors=sys.stderr.isatty())`. The claim is now TRUE — no escape codes reach non-terminal output. No doc edit was needed; the code fix made the statement accurate. All three doc files remain correct as-is.

### 2. Missing `--log-level` option documentation — RESOLVED by B2

**Was:** No `--log-level` CLI option existed; docs didn't document it; hint referenced `--log-file`.

**Now:** `--log-level` option exists in both commands, documented in `cli-reference.md` (lines 65, 134), and asserted by `test_log_level_documented_in_both_reference_docs`.

### 3. Stale `cli-reference-clean.md` references — RESOLVED by plan 14 B9

**Was:** Two files named `cli-reference` (QLT-006), one was mojibake-damaged.

**Now:** `63b020e docs(b9): collapse cli-reference-clean.md into cli-reference.md, delete the fork` merged the fork into the survivor and deleted `cli-reference-clean.md`. `_REFERENCE_DOC_NAMES` in `test_cli.py` updated to `("cli-reference.md",)`. `EXPECTED_SDIST_ENTRIES` updated (73 → 72). No references to the deleted file remain in `docs/` or `tests/`.

## Code Problems — All Resolved

All "Live-1 defects" listed in the prior report have been fixed by the corresponding block commits. No remaining code problems were found in the `docs/` folder audit scope.

## Remaining Notes (Out of Scope — Not Problems)

1. **CF-12 (`ffmpeg_not_found` hint):** Rewritten to `_MERGE_HINT` by `e6e6c68` as part of TRN-008/P16-B8. The hint now reads `"ffmpeg binary not found on PATH; segment merge will fail after download"` — names no deleted `DownloadMethod` member. Resolved.

2. **Eight-file `--method ffmpeg` documentation surface:** Owned by plan 10 B10. Confirmed clean — no remaining references to `ffmpeg` as a download transport in `docs/01-tools/` or `docs/11-guides/`.

3. **`docs/11-guides/configuration.md` log-file settings:** References `VKDOWNLOADER_LOG_FILE` as an environment-configurable destination (not a CLI option). This is correct and out of scope (phase 02 CFG-008).

## Rollout Assessment

The plan was executed in dependency order per §4.2. All commits are present, tests pass, lint/format/mypy are clean, and no code changes are required. The plan is CLOSED.
