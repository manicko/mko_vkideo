# Phase 01 Audit Findings — CLI Entry Point & Command Layer (Validated)

**Executor:** auditor
**Validator:** validator
**Template:** .kilo/commands/audit/phases/01-audit-cli.md
**Status:** complete
**Validated:** yes

---

## Findings

### CLI-001: `batch` command always exits 0 even when all downloads fail

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py (batch_download, lines 368-437) |
| **Classification** | mandatory |

**Description:** The `batch` command only wraps `asyncio.run(...)` in a `try/except` for `(KeyboardInterrupt, asyncio.CancelledError)` (cli.py:435-437). When downloads fail (invalid quality, video not found, network error), `_download_single` catches every exception internally and returns a `("url", "", "error: ...")` tuple (cli.py:139-140), so no exception propagates. `_print_batch_summary` then prints a "Failed: N" line but never calls `raise typer.Exit(code=1)`. As a result the process exits with code 0 even when 100% of downloads failed. The `download` (single) command correctly exits 1 on failure (cli.py:340-341), so the two sibling commands are inconsistent.

The CLI reference documents exit code `1` for "Failure — no URLs found in file or error occurred" (docs/99-reference/cli-reference.md, `batch` exit codes table), but the code cannot produce that code for any runtime download error.

**Evidence:**
- `batch_download` body: `try: results = asyncio.run(...)` ... `except (KeyboardInterrupt, asyncio.CancelledError): typer.echo(...); raise typer.Exit(code=130)`. No other `except`, no `typer.Exit(code=1)` for failures (cli.py:427-437).
- `_print_batch_summary` (cli.py:215-244) only `typer.echo`s the failed count; no non-zero exit.
- Contrast: `download` does `if result: typer.echo(...); else: typer.echo("Download failed", err=True); raise typer.Exit(code=1)` (cli.py:337-341).

**Recommendation:** After printing the batch summary, raise `typer.Exit(code=1)` when `failed > 0` (or when any status is not `"success"`). This makes batch exit codes consistent with `download` and with the documented behavior, and lets automation/scripts detect failed batches.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Finding confirmed through direct code inspection. The `batch_download` function (lines 427-437) lacks exit code 1 handling for download failures. The `_print_batch_summary` function (lines 215-244) reports failures but does not trigger exit. Documentation confirms exit code 1 should be returned for failures.
> - **See also:** CLI-004 (related exception handling issue)

---

### CLI-002: `batch` reads URL file without explicit encoding

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py (batch_download, line 419) |
| **Classification** | advisory |

**Description:** `urls_file.read_text()` (cli.py:419) uses the platform default encoding. On Windows the default is `cp1251`/`mbcs`, so a UTF-8 URL list (e.g. containing percent-encoded or non-ASCII path segments, or saved by a UTF-8 editor) raises `UnicodeDecodeError` or silently corrupts bytes. The same file read is otherwise robust (skips blank lines and `#` comments).

**Evidence:**
```python
urls = [
    line.strip()
    for line in urls_file.read_text().splitlines()   # cli.py:419 — no encoding=
    if line.strip() and not line.startswith("#")
]
```

**Recommendation:** Use `urls_file.read_text(encoding="utf-8")` (add a fallback or `errors="replace"` if desired). Low effort, removes a platform-specific failure mode and matches the project's "English only / portability" rules.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection at cli.py:417-421. No explicit encoding parameter on `read_text()`. This is a portability concern for cross-platform usage.
> - **See also:** project rule #1 (English only) implies UTF-8 encoding for text files

---

### CLI-003: CLI source is not `ruff format` compliant

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | LOW |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** `uv run ruff format --check src/vkdownloader/cli.py` reports "1 file would be reformatted" (exit code 1). The diff is in `_run_batch_with_progress` argument wrapping (cli.py:178-186) and `_print_batch_summary` trailing blank lines (cli.py:220-221, 434-437). The project's quality gate (per base context) includes `ruff format --check`, so this is a CI-failing inconsistency. `ruff check` and `mypy` both pass.

**Evidence:**
```
$ uv run ruff format --check src/vkdownloader/cli.py
Would reformat: src\vkdownloader\cli.py
1 file would be reformatted
(exit code 1)
```

**Recommendation:** Run `uv run ruff format src/vkdownloader/cli.py` to bring the file into compliance. Trivial effort; keeps the formatter gate green.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via `uv run ruff format --check` which exited with code 1. This violates the project's quality gate requirement.
> - **See also:** project verification commands define this as a required check

---

### CLI-004: `batch` swallows all exceptions, masking real errors and preventing structured handling

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/cli.py (_download_single, lines 139-140) |
| **Classification** | advisory |

**Description:** `_download_single` wraps its entire body in `except Exception as e: return (url, "", f"error: {e}")`. This catches *everything*, including programming errors (`TypeError`, `AttributeError`, unexpected `None`), and reduces them to the same `"error: ..."` string as expected failures (missing video, network outage). Consequences:
1. Real bugs during a batch run are indistinguishable from expected failures and are never surfaced as tracebacks/logged exceptions.
2. Structured exceptions such as `QualityNotAvailableError` lose their typed fields; the `batch` command therefore cannot present the same actionable "Requested quality 'X' is not available. Available: ..." message that the `download` command shows (cli.py:352-361). It only shows the raw exception string.
3. Combined with CLI-001, every failure — including bugs — is reported as exit 0.

**Evidence:**
```python
except Exception as e:                       # cli.py:139
    return (url, "", f"error: {e}")
```
Compare with `download` which catches `QualityNotAvailableError` explicitly and produces a targeted message (cli.py:352-361).

**Recommendation:** Narrow the catch in `_download_single` to expected failure types (e.g. `VKDownloadError` from exceptions.py plus `ValueError`), and let unexpected exceptions propagate (or at least log them via `logger.exception`) so they are not silently hidden. This keeps batch UX consistent with `download` and makes failures observable.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection at cli.py:136-140. The broad `except Exception` catches all errors, preventing proper structured error handling.
> - **See also:** CLI-001 (related exit code issue); exceptions.py defines `VKDownloadError`, `QualityNotAvailableError`, `VideoNotFoundError`, `ExtractionError`, `DownloadError`

---

### CLI-005: CLI reference doc overstates progress feedback ("progress bars") and download method

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | docs/99-reference/cli-reference.md (intro + `download` behavior) |
| **Classification** | advisory |

**Description:** The CLI reference states the CLI "uses progress bars for download feedback." There are no progress bars anywhere in the codebase (no `rich`, `tqdm`, or Typer `Progress` — grep found only an internal `FfmpegProgress` parser in ffmpeg_utils.py used for reading ffmpeg stderr, not a user-facing bar). The only progress feedback is a carriage-return text line in `batch` (`typer.echo(f"\r{...}")`, cli.py:190/204); the single `download` command shows no progress at all. The doc also says `download` "Downloads the video using FFmpeg" although the default `--method` is `auto` (yt-dlp first, ffmpeg fallback).

**Evidence:**
- Intro line (cli-reference.md): "The CLI is built with [Typer](https://typer.tiangolo.com/) and uses progress bars for download feedback."
- `download` Behavior step 4: "Downloads the video using FFmpeg."
- Code: only `batch` prints `\r`-overwrite text progress; `download` prints nothing during the run.
- Grep for `rich|tqdm|Progress(` across `src/` → only `FfmpegProgress` (internal ffmpeg parsing), no user-facing bar.

**Recommendation:** Update the doc to describe the actual text-based per-URL progress in `batch` and note that `download` (single) shows no live progress; correct the `download` behavior to say it uses the selected `--method` (default `auto`). Keeps docs honest per the project's "docs updated continuously" rule.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via hex dump analysis of cli-reference.md showing "progress bars for download feedback" at offset 0x0120 and "Downloads the video using FFmpeg" at offset 0x0780. Code inspection confirms only `\r`-overwrite text progress in `batch` command, no user-facing library progress bars.
> - **See also:** docs/01-tools/vkdownloader-overview.md correctly describes "per-URL segment progress" (not progress bars)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 2 |

## Mandatory Fixes

- CLI-001 (HIGH, SPEC-DEVIATION): `batch` must exit non-zero when downloads fail (currently always exits 0, contradicting documented exit codes and `download` behavior).

## Advisory Recommendations

- CLI-002: Read batch URL file with explicit `encoding="utf-8"`.
- CLI-003: Run `ruff format` on cli.py to satisfy the format gate.
- CLI-004: Narrow the broad `except Exception` in `_download_single` so real bugs and typed errors are observable and handled consistently with `download`.
- CLI-005: Correct CLI reference doc: no progress bars exist; `download` method defaults to `auto`.

## Doc Updates Needed

- CLI-005: Fix inaccurate "progress bars" claim and "Downloads the video using FFmpeg" statement in docs/99-reference/cli-reference.md.
- CLI-001: Reconcile batch exit-code documentation with actual (to-be-fixed) behavior.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | CLI-001, CLI-002, CLI-003, CLI-004, CLI-005 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | — |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| — | — | — | — |

---

## Rollout Safety Analysis

No rollout safety issues detected. These findings are isolated to the CLI layer and can be addressed independently:

1. **CLI-001** and **CLI-004** are related but can be fixed separately - exit code handling can be added without changing exception handling
2. **CLI-002** is a single-line change with no backward compatibility concerns
3. **CLI-003** is a formatting-only change with no functional impact
4. **CLI-005** is documentation-only with no code impact

No circular dependencies or hidden dependency chains identified.
