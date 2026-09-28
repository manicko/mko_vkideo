# Specification: Batch Download Concurrent Progress Display

**Problem ID:** 01  
**Title:** Clean per-file progress display during concurrent batch downloads  
**Date:** 2026-09-27  
**Author:** Senior Product Analyst  
**Decision source:** `.ai/problems/PROBLEM.md` (user-reported)  
**Status:** DONE — implemented, validated and committed  
**Completed:** 2026-09-28 — tasks T1-T12 delivered; 415 tests pass, 1 skipped; ruff and mypy strict clean. See the deviations recorded in the implementation history below.  

---

## 1. Problem Statement

When running `vkdownloader batch urls.txt` with concurrent downloads (default `max_concurrent_downloads=4`), the terminal output is visually chaotic. Lines from multiple concurrent yt-dlp subprocesses, the ProgressManager's 1 Hz poll, and structlog log messages all interleave on the same terminal using conflicting control characters (`\r` vs `\n`), making it impossible to read any single download's progress.

The desired behavior: for each file currently being downloaded concurrently, display a dedicated progress line that overwrites itself in-place, mirroring the self-overwriting behavior of single-file mode but extended to multiple concurrent downloads.

---

## 2. Business Goal

Eliminate visual chaos during batch downloads by replacing the three uncoordinated output sources with a single, coherent multi-line progress display where each active download has its own self-updating progress line.

---

## 3. Scope

### In Scope
- `vkdownloader batch` command progress display during concurrent downloads
- Integration with yt-dlp, ffmpeg, and segment-download progress callbacks
- TTY detection and non-TTY fallback behavior
- Log message interleaving handling during live progress
- yt-dlp native echo suppression during batch mode
- Existing test compatibility and new test coverage

### Out of Scope
- Single-file `download` command progress (currently shows no live progress; untouched by this work)
- Progress display in non-TTY piped output beyond logging fallback
- Deriving real percentage from ffmpeg `out_time_ms` (SRV-003 is already fixed; full enhancement deferred)
- Adding `tqdm` as a dependency (rejected in favor of `rich`)
- Changes to download concurrency limits or semaphore behavior
- Changes to URL validation, quality selection, or error recovery logic

---

## 4. Confirmed Requirements

R1. **Per-file progress lines:** Each concurrently active download must have its own progress line in the terminal.

R2. **In-place overwrite:** Progress lines must update in-place (no scroll accumulation) using a live display library, not raw `\r`.

R3. **Dynamic line management:** When a download completes, its line must be replaced with a status line (`[✓] done` / `[✗] failed` / `[⊘] skipped`). When it was the last active download, the terminal must be restored to normal output.

R4. **Concurrent source support:** The display must work with all three progress sources: yt-dlp byte-based progress, ffmpeg byte-based (unknown-total) progress, and segment-count-based progress.

R5. **yt-dlp echo suppression:** In batch mode, yt-dlp's native progress echo (`_echo_ytdlp_line`) must be suppressed from the console. The same progress data is already extracted via `progress_callback` and will be shown through the rich display.

R6. **Log interleaving:** structlog INFO/WARNING log messages must briefly pause the live progress display, print above it, and then resume — preserving visibility of rate-limit warnings, errors, and other events.

R7. **TTY detection:** The rich live display must only activate when the output stream is a TTY (`isatty()`). When piped/CI, progress updates must fall back to INFO-level structlog messages and yt-dlp echo remains on stderr.

R8. **Video identification:** Progress lines must show `video_{N}: {sanitized_title}` where title is known; fall back to `video_{N}` during extraction phase.

R9. **Progress columns:** The display must use rich's default Progress columns including download bar, percentage, transfer speed, and ETA.

R10. **No `print()`:** All output must go through `rich` console or `structlog` logger (project rule: no `print()` statements).

R11. **Cross-platform:** Must work on Windows (primary user environment) and Unix terminals, including Windows legacy console.

R12. **No new runtime dependencies:** `rich` is already installed transitively via `typer>=0.12.0 → rich>=13.8.0`. Must be declared as a direct dependency in `pyproject.toml`.

R13. **Existing tests must continue to pass.** New tests must cover the new progress display behavior.

R14. **Project conventions:** Strict type hints (Pydantic v2, `from __future__ import annotations`), `StrEnum` for constants, structlog logging, module-level `__all__`, small focused functions.

---

## 5. Product Owner Decisions

| # | Decision | Chosen Option | Rationale |
|---|----------|---------------|-----------|
| Q1 | Progress display layout | **Option A** | One line per currently active download; completed downloads get a status line. Matches user's description ("for each file currently being downloaded"). |
| Q2 | yt-dlp native echo | **Option A + B** | Suppress yt-dlp's native console echo; log progress data at DEBUG level if `--log-file` configured. The same data already flows through `progress_callback`. |
| Q3 | Log messages during progress | **Option A** | Log messages temporarily pause the Live display, print above it, then resume. Users see warnings/errors without losing progress context. |
| Q4 | TTY detection / fallback | **Option A** | Disable rich Live display when not a TTY. Fall back to INFO-level structlog progress updates and yt-dlp stderr echo. No escape codes in piped output. |
| Q5 | Progress display fields | **Option D** | Use rich's default Progress columns (bar, percentage, elapsed time, transfer speed, ETA). |
| Q6 | Video identification | **Option D** | `video_{N}: {sanitized_title}`, falling back to `video_{N}` during extraction. |
| Q7 | ffmpeg progress (SRV-003) | **Option A** | Leave as-is. ffmpeg path shows indeterminate (spinner style, `total=None`). SRV-003 already fixed in current code. |

---

## 6. Research Summary

### Root Cause (confirmed via code trace)

Three uncoordinated output sources write to the same terminal during concurrent batch downloads:

| Source | Function | Stream | Control Char | Frequency |
|--------|----------|--------|-------------|-----------|
| A | `_echo_ytdlp_line()` (`ytdlp_downloader.py:195-210`) | stderr | `\r` + ljust | ~4/s per subprocess |
| B | `_poll_progress_display()` (`batch_downloader.py:139-151`) | stdout via `typer.echo` | `\r`, `nl=False` | 1 Hz |
| C | structlog ConsoleRenderer (`config.py:319-377`) | stderr via `StreamHandler` | `\n` | Event-driven |

Sources A and B compete for cursor position using `\r` (one per active subprocess vs. 1 Hz poll). Source C's newline-terminated logs break both `\r`-based overwrites.

### Recommended Technical Approach: `rich` Progress + Live Display

**Why `rich` (not `tqdm` or custom ANSI):**

1. **Zero install overhead** — `rich` 15.0.0 is already installed transitively via `typer>=0.12.0`. Declaring it as a direct dependency is a one-line `pyproject.toml` change.
2. **Solves tqdm's known deficiencies** — GitHub Issues #1496, #1000 confirm `tqdm` has unresolved bar-jumping and ghost-artifact problems with non-sequential completion (exactly the batch download scenario where URLs finish in arbitrary order). Rich handles task removal smoothly.
3. **Built-in log integration** — `rich.logging.RichHandler` + `Live` coordination eliminates the structlog/typer.echo interleaving problem at the root.
4. **Superior Windows support** — Uses Windows Console API (not just VT100), critical since the user runs on Windows.
5. **Testable without a terminal** — `Console(file=StringIO())` enables headless test assertions.
6. **10 Hz auto-refresh** eliminates the need for `_poll_progress_display()` entirely.

### SRV-003 Assessment

**Already fixed.** The current code at `downloader.py:516-522` passes `total=0` (unknown) rather than `total=downloaded` (always 100%). Test `test_perform_download_ffmpeg_progress_adapter_sends_unknown_total` (`test_hls_downloader.py:1842-1910`) verifies this. SRV-003 is **not** part of this work.

### Approaches Evaluated

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **A: tqdm + position** | Well-known, `tqdm.write()` for logs | Ghost artifacts on non-sequential completion (GitHub #1496, #1000); new dependency; asyncio support via wrapper only | **Rejected** |
| **B: rich Progress + Live** | Zero install overhead; handles non-sequential removal; built-in log pausing; Windows Console API; testable | Single Live per Console (by design, not a problem for batch) | **Selected** |
| **C: Custom ANSI** | No new dependency | ~200-300 LOC to reimplement rich subset; Windows VT100 enablement; difficult to test; not community-tested | **Rejected** |

---

## 7. Assumptions

A1. The `rich` library version 13.8.0+ (required by `typer>=0.12.0`) provides all needed features: `Progress`, `Live`, `RichHandler`, `SpinnerColumn` for indeterminate state.

A2. yt-dlp progress data extracted via `_parse_ytdlp_progress()` (`ytdlp_downloader.py:168-192`) is sufficient to drive rich's byte-based progress — no additional parsing of yt-dlp subprocess output is needed.

A3. ffmpeg downloads (which report `total=0` / unknown) will display as an indeterminate spinner, which rich handles natively via `total=None`.

A4. Segment-download progress (`progress_callback(video_id, downloaded_count, len(segments))` in `segment_downloader.py:705`) produces integer segment counts, which rich will display as `completed/total` with a bar.

A5. The `output_index` parameter already passed to `download_video()` (`downloader.py:596`) can be used for `video_{N}` labeling without additional changes to the download pipeline.

A6. The module-level `_progress_manager = ProgressManager()` singleton in `batch_downloader.py:41` can be replaced by a rich-based reporter without affecting other modules that import `ProgressManager` from `downloader_throttle` (it remains for backward compatibility / non-batch use).

A7. The `--log-file` option (if configured) will capture DEBUG-level progress events for auditability.

---

## 8. Constraints

C1. **No `print()` statements** — must use `rich` Console or `structlog` logger (project rule #12).
C2. **No new runtime dependencies beyond `rich`** which is already transitive. Adding `tqdm` or other libraries is prohibited.
C3. **Strict type hints** — all new code must use full type annotations (project rule #9).
C4. **No `any` type** — must use precise types (project rule #9).
C5. **StrEnum for constants** — progress status labels, display modes, etc. must use enums (project rule #10).
C6. **Pydantic v2 + type hints** for any data models (project rule #11).
C7. **Small, focused modules** — the progress reporter must be in its own module, not embedded in `batch_downloader.py` (project rule #4, #15).
C8. **Database migrations** — not applicable (no schema changes).
C9. **Documentation must be updated** — CLI reference and overview docs must reflect new progress behavior (project rule #14).

---

## 9. Risks

R1. **Windows legacy console** — If `rich` cannot detect/enable VT100 on older Windows, the terminal may show raw escape codes. Mitigation: rich's Windows Console API fallback; add CI test on Windows.

R2. **Typer/CliRunner test interference** — `typer.testing.CliRunner` captures stdout/stderr in a non-TTY buffer. The rich Live display may produce unanticipated escape sequences in captured output. Mitigation: detect `CliRunner` context or `isatty()==False` and disable Live display in tests.

R3. **Performance impact** — Rich Live display refreshes at 10 Hz by default. With 4 concurrent downloads, this may produce visible CPU usage. Mitigation: configurable `refresh_per_second` (default 10, can reduce to 4).

R4. **Progress callback timing** — yt-dlp progress callbacks fire from the event loop thread. Rich's `Progress.update()` acquires an internal lock. Under high-frequency yt-dlp output (~4/s × 4 processes = 16 updates/s), lock contention could slow the event loop. Mitigation: rich's lock is held for microseconds; 16/s is far below any practical threshold.

R5. **Backward compatibility** — External code importing `ProgressManager` from `downloader_throttle` must continue to work. The new reporter must not break existing imports.

R6. **Log format change** — If `RichHandler` replaces the current `ConsoleRenderer` during batch mode, the log format may change. Risk: existing log-parsing tooling may break. Mitigation: only use `RichHandler` for the console handler during batch; file logging (if configured) continues using the current format.

---

## 10. Open Questions

O1. Should the rich display also be enabled for the single-file `download` command in a future phase? *(Deferred — out of scope.)*

O2. Should there be a `--no-progress` CLI flag to disable the rich display even on a TTY? *(Deferred — may be added if user requests.)*

O3. When `--log-file` is configured, should batch progress events also be written to the log file for later analysis? *(Assumption A7 covers this, but PO should confirm.)*

---

## 11. Conceptual Development Tasks

| ID | Task | Purpose | Expected Outcome | Dependencies |
|----|------|---------|-----------------|--------------|
| T1 | Add `rich` as direct dependency | Declare the already-transitive dependency explicitly | `pyproject.toml` lists `rich>=14.0.0` in dependencies | None |
| T2 | Create `RichProgressReporter` module | Encapsulate rich Progress + Live lifecycle management | `services/progress_display.py` with class managing N tasks, add/update/complete/remove, TTY detection, log pausing | T1 |
| T3 | Create progress status enums | Replace string literals with StrEnum | `models/enums.py` adds `ProgressStatus(StrEnum)` with values: `IN_PROGRESS`, `SUCCESS`, ` FAILED`, `SKIPPED`, `CANCELLED` | Project rule #10 |
| T4 | Bridge callbacks to RichProgressReporter | Replace `_create_progress_callback` to call reporter instead of ProgressManager | `_create_progress_callback` calls `reporter.update(index, downloaded, total)` | T2 |
| T5 | Suppress yt-dlp echo in batch mode | Pass flag to `_echo_ytdlp_line` / `_monitor_progress` to skip console echo | `_echo_ytdlp_line` accepts `echo=True` param; batch mode passes `echo=False` | Project rule on no `print()` |
| T6 | Integrate structlog RichHandler during batch | Use `RichHandler` so logs pause/resume with Live display | `setup_logging` or `_run_batch_with_progress` configures RichHandler for console when batch + TTY | T2 |
| T7 | Refactor `_run_batch_with_progress` | Replace `_poll_progress_display` (1 Hz typer.echo) with RichProgressReporter (10 Hz auto) | No more `_poll_progress_display`; reporter started/stopped around download tasks | T2, T4, T6 |
| T8 | Add TTY detection guard | Check `sys.stdout.isatty()` before creating Live display | Non-TTY: skip reporter, fall back to existing ProgressManager + structlog INFO logs | T2 |
| T9 | Update ProgressManager usage (preserve backward compat) | Keep `ProgressManager` in `downloader_throttle.py` for non-batch use; batch uses RichProgressReporter | No breaking imports; tests using `ProgressManager` still pass | T2, T7 |
| T10 | Add tests for RichProgressReporter | Unit tests for add/update/complete/remove, TTY fallback, non-TTY fallback | `tests/test_progress_display.py` with `Console(file=StringIO())` headless tests | T2, T3 |
| T11 | Update existing batch tests | Ensure `TestBatchCommand` tests still pass with new output format | `tests/test_cli.py` — update any assertions that check progress output format | T7, T8 |
| T12 | Update documentation | CLI reference and overview docs reflect new progress behavior | `docs/99-reference/cli-reference-clean.md` and `docs/01-tools/vkdownloader-overview.md` updated | T2, T7 |

---

## 12. Definition of Ready

A development task is considered ready when:

1. ✅ The Product Owner has confirmed all behavior questions (Q1–Q7) — **Completed**
2. ✅ A researcher has investigated the current architecture and modern best practices — **Completed**
3. ✅ The recommended technical approach (`rich` Progress + Live) is selected — **Completed**
4. ✅ All constraints (no new deps beyond rich, strict typing, StrEnum, small modules, no print) are documented — **This spec**
5. ✅ Conceptual tasks are broken down with clear dependencies — **This spec**
6. ✅ Acceptance criteria for each task are derivable from the requirements — **This spec**
7. ✅ Risks and mitigations are documented — **This spec**
8. ✅ Testing strategy is identified — **This spec** (Section 6)

**The implementation team can proceed to sprint planning using the conceptual tasks in Section 11.**

---

## 13. Acceptance Criteria Summary

| Criterion | Test |
|-----------|------|
| AC1: Each active download shows a dedicated progress line | Manual: run `vkdownloader batch urls.txt` with 4+ URLs; verify N progress bars appear |
| AC2: yt-dlp native echo is suppressed in batch mode | Verify no `[download] X% of ...` lines appear during batch; same data shown in rich bar |
| AC3: Completed downloads show status line | `[✓] video_0: 100% done` or `[✗] video_2: failed` replaces progress bar |
| AC4: Log messages pause progress display | WARN/ERROR messages appear above progress bar, progress resumes below |
| AC5: Non-TTY output has no escape codes | `vkdownloader batch urls.txt 2>&1 | cat` produces clean text output |
| AC6: Existing tests pass | `pytest tests/test_cli.py` and `pytest tests/test_downloader_throttle.py` pass unedited |
| AC7: New tests cover reporter | `pytest tests/test_progress_display.py` — 90%+ coverage of `RichProgressReporter` |
| AC8: ffmpeg path shows indeterminate spinner | With `--method ffmpeg`, progress bar shows spinner (no percentage) |
| AC9: `rich` declared as direct dependency | `grep "rich" pyproject.toml` returns a match in `[project].dependencies` |
| AC10: No `print()` in new code | `ruff check` passes on new/modified files |
