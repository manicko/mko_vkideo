# Audit Problems Report — Plan: 13-cli-observability-audit-fixes

**Plan status:** INCOMPLETE (renamed to `_fix`)
**Plan path:** `.ai/plans/13-cli-observability-audit-fixes_fix.md`
**Audit date:** 2026-10-09

## Plan Execution Summary

| Block | Status | Notes |
|-------|--------|-------|
| B1 | DONE | Exit code 3 for preamble failures |
| B2 | NOT DONE | No `--log-level` option; hint says `--log-file` (Live-1) |
| B3 | NOT DONE | No `exc_info`-clearing processor |
| B4 | NOT DONE | `correlation_id` missing from error records; `video_id` missing from `download_finished` |
| B5 | PARTIAL | Exit code 3 + tests pass; message still points to `.env` |
| B6 | NOT DONE | `ConsoleRenderer()` missing `colors=` argument |
| B7 | NOT DONE | Non-progress lines dropped silently |
| B8 | DONE | "Total videos:" label |
| B9 | DONE | Explicit `skipped` count |
| B10 | DONE | Single TTY predicate with memoisation |
| B11 | DONE | `stop()` nested try/finally |
| B12 | DONE | Terminal status for in-flight tasks |
| B13 | DONE | `failed_to_refresh_token` narrow except |
| B14 | NOT DONE | No git provenance in audit pipeline; no dirty-tree hard stop |
| B15 | NOT DONE | No path-based exclusions in `audit-orphaned.md` |
| B16 | NOT DONE | 4 stale docstrings referencing ffmpeg path |
| B17 | PARTIAL | Docs mention removal but help text doesn't name it |

## Documentation Problems

### 1. False claim about escape codes in non-terminal output

**Files:**
- `docs/99-reference/cli-reference.md` line 168
- `docs/99-reference/cli-reference-clean.md` (same content)
- `docs/01-tools/api-reference.md` line 278
- `docs/01-tools/vkdownloader-overview.md` line 243

**Problem:** Documentation states "no escape codes are written" when output is redirected to a non-terminal. This is FALSE. Block B6 is not done — `ConsoleRenderer()` at `src/vkdownloader/config.py:627` has no `colors=False` argument, so escape codes are written unconditionally. This creates a SPEC-DEVIATION between documentation and implementation.

**Severity:** MEDIUM — can break log parsing for operators expecting clean text.

### 2. Missing `--log-level` option documentation

**Files:**
- `docs/99-reference/cli-reference.md`
- `docs/99-reference/cli-reference-clean.md`

**Problem:** Block B2 is not done — there is no `--log-level` option in the CLI. Reference docs do not document it, but the code also doesn't have it. The hint message at `cli.py:91` still references `--log-file` when it should reference `--log-level`.

## Code Problems (Live-1 defects)

### B2: `format_validation_error` hint references wrong option

**File:** `src/vkdownloader/cli.py` line 91

**Problem:** The hint message says "Check the --log-file option" but the plan requires a `--log-level` option. The hint should reference `--log-level` instead.

### B3: No `exc_info`-clearing processor

**File:** `src/vkdownloader/config.py:617-628`

**Problem:** The `ConsoleRenderer()` call does not have `colors=False`, and there is no processor to clear `exc_info` before rendering. This means:
1. Escape codes are written even to non-terminals (false docs claim)
2. Tracebacks may leak to console output

### B4: Missing correlation context in error records

**File:** `src/vkdownloader/services/extractor.py:292-296`

**Problem:** `ytdlp_extraction_error` records lack `correlation_id` field. The `run_in_executor` call at this location does not propagate contextvars, making correlation impossible.

**Also:** `src/vkdownloader/services/progress_display.py:468` — `download_finished` record lacks `video_id`.

### B6: No conditional rendering for non-terminal output

**File:** `src/vkdownloader/config.py:627`

**Problem:** `ConsoleRenderer()` is called without `colors=False`, so rich writes ANSI escape codes regardless of whether stdout is a terminal. Documentation claims otherwise (see Documentation Problem 1).

### B7: Silent dropping of non-progress lines

**File:** `src/vkdownloader/services/ytdlp_downloader.py:686-695`

**Problem:** The `_echo_ytdlp_line` method only forwards lines that contain progress regex matches (`\r` + percentage). All other lines (warnings, errors, info) are silently dropped. The test at `tests/test_hls_downloader.py:3595` still asserts the old behavior of dropping non-progress lines.

### B14: No git provenance tracking in audit pipeline

**File:** `.kilo/commands/audit/audit-multi-phase.md:42-44`

**Problem:** `BASE_CONTEXT` does not include `git rev-parse HEAD` or `git status --porcelain`. There is no dirty-tree hard stop to warn auditors about uncommitted changes that could affect results.

### B15: No path-based exclusions in orphaned-file audit

**File:** `.kilo/commands/audit/audit-orphaned.md:32-37`

**Problem:** Exclusions are only category-based (e.g., "generated docs"). There are no path-based exclusions for `.ai/audit/**`, `.git/**`, or `.venv/**`, which could cause false positives in the orphaned-file scan.

### B16: Stale docstrings referencing ffmpeg path

**Files:**
- `src/vkdownloader/services/batch_downloader.py:174`
- `src/vkdownloader/services/batch_downloader.py:306`
- `src/vkdownloader/services/batch_downloader.py:565`
- `src/vkdownloader/services/progress_display.py:288`

**Problem:** Three `method: Download method (yt-dlp, ffmpeg, or auto).` docstrings in `batch_downloader.py` and one "the ffmpeg path" comment in `progress_display.py` still reference ffmpeg as a download method, even though yt-dlp now handles downloading (ffmpeg is only used for post-processing/merge).

## Rollout Notes

The remaining 8 unexecuted blocks (B2, B3, B4, B6, B7, B14, B15, B16) are individually feasible. No circular dependencies exist between them. Blocks B3 and B6 are closely related (both involve `ConsoleRenderer` configuration) and should be implemented together. Block B7's test update must accompany its code change.
