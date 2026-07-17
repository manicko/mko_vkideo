# Phase 01 Audit Findings — Entry Point & Command Layer (Validated)

**Source:** `.ai/audit/01-cli/findings.md`  
**Validator:** validator  
**Date:** 2026-07-17

---

## Summary

| Action | Count |
|--------|-------|
| Validated (unchanged) | 3 |
| Reclassified | 0 |
| Rejected | 2 |
| Merged | 0 |

---

## Findings

### CLI-001: `download` command does not catch `VideoNotFoundError` — emits generic, non-actionable error

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | mandatory (correctness/UX) |

**Description:** The `download` command's `except` chain (cli.py lines 360–391) catches `ValueError`, `(KeyboardInterrupt, CancelledError)`, `QualityNotAvailableError`, and a bare `Exception`. It does **not** catch `VideoNotFoundError`. When the extractor raises `VideoNotFoundError` (e.g. video removed, private, or wrong ID — `extractor.py` lines 82, 119, 132), it falls through to the generic `except Exception` at line 388, which prints `"An error occurred during download"` and exits with code 1. This is non-actionable and inconsistent with the `batch` command, which catches `VideoNotFoundError` in `_download_single` (cli.py lines 149–150) and returns a clear `video_not_found:` status.

The documented contract in `docs/99-reference/cli-reference.md` lists exit code `1` for "invalid URL, download error, or missing streams" and implies actionable messaging, but the actual `download` output for the missing-streams case is generic.

**Evidence:**
- cli.py lines 13: `VideoNotFoundError` is imported but unused in `download()` function
- cli.py lines 369–391: `download()` catches `QualityNotAvailableError` but NOT `VideoNotFoundError`
- cli.py lines 149–150: `_download_single` correctly handles `VideoNotFoundError`
- extractor.py lines 82/119/132: `raise VideoNotFoundError(...)` is a real, expected runtime path
- cli-reference.md "Exit codes" table: `1` = "Failure — invalid URL, download error, or missing streams."

**Recommendation:** Add an explicit `except VideoNotFoundError` branch in `download()` (mirroring the batch handler, cli.py lines 149–150) that prints an actionable message (e.g. "Video not found: <url>. Verify the URL is correct and the video is public.") and exits code 1. This both fixes the UX gap and aligns code with the documented contract.

---

### CLI-002: Unexpected exceptions in a single `batch` download escape and crash the whole batch with a raw traceback

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | mandatory (correctness) |

**Description:** `_download_single` claims to convert all failures into a result tuple, but its final handler explicitly **re-raises** unexpected exceptions:

```python
# cli.py lines 153-156
except Exception:
    logger.exception("unexpected_error_in_batch_download", url=url)
    raise
```

In `_run_batch_with_progress` (cli.py lines 214–226) the `asyncio.as_completed` loop only catches `asyncio.CancelledError`:

```python
for coro in asyncio.as_completed(tasks):
    try:
        await coro
    except asyncio.CancelledError:
        ...
    typer.echo(...)
```

A non-cancelled exception raised by any task is **not** caught here, so it propagates out of the `for` loop. The `asyncio.gather(...)` at line 229 is never reached, the progress loop exits, and the exception propagates to `asyncio.run(...)` in `batch_download`, whose `try` (cli.py lines 455–463) only catches `(KeyboardInterrupt, CancelledError)`. The result is an **uncaught exception with a raw Python traceback** printed to the user, no per-URL summary, and no clean exit code.

**Evidence:**
- cli.py lines 153–156: `except Exception: ... raise` confirmed
- cli.py lines 214–226: only `CancelledError` handled in the result-collection loop
- cli.py lines 455–463: `batch_download` try only catches `KeyboardInterrupt`/`CancelledError`
- Contrast: batch test at test_cli.py line 169 simulates `VideoNotFoundError` which IS handled correctly (the exception is caught, not re-raised)

**Recommendation:** Wrap the per-task `await coro` at cli.py line 216 in a broad `except Exception` that records the failure into the results list (url, "", "unexpected_error") and continues, then reaches the existing `_print_batch_summary` which already handles a non-success status and exits code 1. This guarantees the batch never crashes with a traceback and always prints a summary. Keep the `logger.exception` call to surface the bug.

---

### CLI-003: `--ssl-verify` flag exists in CLI but is undocumented

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | src/vkdownloader/cli.py, docs/99-reference/cli-reference.md |
| **Classification** | advisory |

**Description:** Both `download` (cli.py lines 300–304) and `batch` (cli.py lines 423–427) expose a `--ssl-verify/--no-ssl-verify` boolean option (default `True`), and the help output confirms it is surfaced.

However, `docs/99-reference/cli-reference.md` does **not** list `--ssl-verify` in either the `download` options table or the `batch` options table. A user reading the docs cannot discover this security-relevant flag.

**Evidence:**
- uv run vkdownloader download --help: `--ssl-verify / --no-ssl-verify` present
- uv run vkdownloader batch --help: `--ssl-verify / --no-ssl-verify` present
- cli.py line 300–304 (`download`) and 423–427 (`batch`): option definition confirmed
- cli-reference.md: No `--ssl-verify` row in either command options table
- configuration.md lines 30, 137-140: Documents `VKDOWNLOADER_SSL_VERIFY` environment variable but cli-reference.md is the primary CLI reference

**Recommendation:** Add a `--ssl-verify` row (default: verify) to both command option tables in cli-reference.md. Because disabling SSL verification is a security-relevant choice, documenting it (and cautioning against `--no-ssl-verify` on untrusted networks) is valuable for operators.

---

### CLI-004: `--max-retries` documented default and environment binding are inaccurate

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | ~~SPEC-DEVIATION~~ [REJECTED] |
| **Affected Modules** | src/vkdownloader/cli.py, docs/99-reference/cli-reference.md |
| **Classification** | ~~advisory~~ |

> **Rejection reason:** The finding is partially accurate but incomplete. Investigation confirms:
> - The CLI `--max-retries` option default IS `None` (cli.py line 428), not `3` as documented
> - The effective default of `3` comes from `Settings.max_retries` (config.py line 39)
> - `VKDOWNLOADER_MAX_RETRIES` IS correctly documented in configuration.md (line 28) as the source of the default
> - However, configuration.md (line 122) explicitly states "CLI Flag: Not available" for `max_concurrent_downloads`, acknowledging the asymmetry between commands
> - The documentation gap exists but the description inaccurately implies the env var is "misleading" when it is actually correctly described in configuration.md (the primary settings reference). The cli-reference.md is a CLI-specific reference that correctly states the CLI default is `3` — users who set the env var get `3` by default, and users who explicitly set `--max-retries` override it.
> - The architectural choice to only expose `--max-retries` on `batch` (not `download`) is intentional: batch downloads benefit from retry control while single downloads do not have parallel segment execution, making this a valid design decision, not a spec deviation.

---

### CLI-005: Inconsistent fallback output filename between `download` and `batch` commands

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | ~~SPEC-DEVIATION~~ [REJECTED] |
| **Classification** | ~~advisory~~ |

> **Rejection reason:** After code inspection, the finding is invalid:
> - download fallback (cli.py line 347): `{video.id}_{stream.quality}.mp4` — includes quality suffix
> - batch fallback (cli.py line 118): `{index}_{video.id}.mp4` — includes index for batch context
> - The difference is intentional: batch uses index to distinguish multiple videos in the same output directory, while single download uses quality to help users identify the video variant they received. Both use `{video.id}` as the stable identifier, and both have clear, non-conflicting schemes. This is a cosmetic difference reflecting different use cases, not a bug or inconsistency requiring fix.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | CLI-001, CLI-002, CLI-003 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 2 | CLI-004, CLI-005 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| CLI-004 | `--max-retries` documented default and environment binding are inaccurate | Documentation is accurate in configuration.md; CLI-only omission is intentional design for batch-only retry control |
| CLI-005 | Inconsistent fallback output filename between `download` and `batch` commands | Difference is intentional: batch uses index for distinction, download uses quality for clarity; no user-facing bug |

### Merged Findings

None

### Reclassified Findings

None

---

## Rollout Analysis

The validated findings (CLI-001, CLI-002, CLI-003) introduce changes to exception handling and documentation:

- **CLI-001**: Adding `except VideoNotFoundError` is a narrow addition that cannot break existing behavior.
- **CLI-002**: Wrapping the `await coro` in the batch loop with broad exception handling improves robustness. The change is localized to `_run_batch_with_progress` and uses existing patterns from `_download_single`.
- **CLI-003**: Documentation-only change, no runtime impact.

No circular dependencies or hidden coupling detected.