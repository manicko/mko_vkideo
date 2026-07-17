# Phase 01 Audit Findings — Entry Point & Command Layer

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/01-audit-cli.md
**Status:** complete
**Validated:** no

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 3 |

## Mandatory Fixes

- **CLI-001** (MEDIUM): `download` command must catch `VideoNotFoundError` and print an actionable message (currently falls through to a generic error).
- **CLI-002** (HIGH): `batch` command can crash with a raw traceback when a single download raises an unexpected exception; wrap per-task completion so failures are recorded as per-URL errors and the summary still prints.

## Advisory Recommendations

- **CLI-004** (LOW): Correct the documented `--max-retries` default and clarify the `VKDOWNLOADER_MAX_RETRIES` binding.
- **CLI-005** (LOW): Unify `download`/`batch` fallback filename generation via a shared helper.

## Doc Updates Needed

- **CLI-003** (DOC-UPDATE): Document the `--ssl-verify/--no-ssl-verify` flag for both `download` and `batch` in cli-reference.md.
- **CLI-004** (DOC-UPDATE): Fix the `--max-retries` default and environment-binding description in cli-reference.md.

---

## Runtime Verification Log (Phase 01)

| Step | Command | Result |
|------|---------|--------|
| R1 Import | `uv run python -c "import vkdownloader.cli; ..."` | PASS — `IMPORT OK` |
| R2 Help/Schema | `uv run vkdownloader --help`, `download --help`, `batch --help` | PASS — all commands enumerated, no crash; `--ssl-verify` surfaced (see CLI-003) |
| R3 Lint | `uv run ruff check src/vkdownloader/cli.py` | PASS (exit 0) |
| R3 Format | `uv run ruff format --check src/vkdownloader/cli.py` | PASS (already formatted) |
| R3 Types | `uv run mypy src/vkdownloader/cli.py` | PASS (no issues; note: unused `tests.*` override warning) |
| R4 Tests | `uv run pytest tests -k "cli or batch or download" -q` | PASS — 134 passed, 89 deselected |

**Note:** Linter/type/test gates pass; all findings above are behavioral/spec-deviation issues discovered by code reading and doc cross-checking, not by failing CI gates.

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
- cli.py lines 360–391: `download()` catches `QualityNotAvailableError` (line 378) but NOT `VideoNotFoundError`.
- cli.py lines 149–150: `batch` path correctly handles `VideoNotFoundError`.
- extractor.py lines 82/119/132: `raise VideoNotFoundError(...)` is a real, expected runtime path.
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

In `_run_batch_with_progress` (cli.py lines 214–228) the `asyncio.as_completed` loop only catches `asyncio.CancelledError`:

```python
for coro in asyncio.as_completed(tasks):
    try:
        await coro
    except asyncio.CancelledError:
        ...
        raise
    typer.echo(...)
```

A non-cancelled exception raised by any task is **not** caught here, so it propagates out of the `for` loop. The `asyncio.gather(...)` at line 229 is never reached, the progress loop exits, and the exception propagates to `asyncio.run(...)` in `batch_download`, whose `try` (cli.py lines 455–463) only catches `(KeyboardInterrupt, CancelledError)`. The result is an **uncaught exception with a raw Python traceback** printed to the user, no per-URL summary, and no clean exit code. One unexpected error in any single URL aborts the entire batch instead of being reported as a per-URL failure.

**Evidence:**
- cli.py lines 153–156: `except Exception: ... raise`.
- cli.py lines 214–226: only `CancelledError` handled in the result-collection loop; other exceptions propagate.
- cli.py lines 455–463: `batch_download` try only catches `KeyboardInterrupt`/`CancelledError` → traceback leaks.
- Contrast: the surrounding design intent (lines 153 comment "instead of silently swallowing them") is sound for surfacing bugs, but the entry layer provides no final guard, contradicting the phase invariant "Every handler catches exceptions and presents user-friendly messages" and "All commands/endpoints functional … without crashing."

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

**Description:** Both `download` (cli.py lines 300–304) and `batch` (cli.py lines 423–427) expose a `--ssl-verify/--no-ssl-verify` boolean option (default `True`), and the help output confirms it is surfaced:

```
| --ssl-verify  --no-ssl-verify  Verify SSL certificates for CDN connections [default: ssl-verify]
```

However, `docs/99-reference/cli-reference.md` does **not** list `--ssl-verify` in either the `download` options table or the `batch` options table. A user reading the docs cannot discover this security-relevant flag.

**Evidence:**
- Help output (runtime, captured during verification): `--ssl-verify/--no-ssl-verify` present for both commands.
- cli.py line 300–304 (`download`) and 423–427 (`batch`): option definition.
- cli-reference.md "Options" tables for `download` and `batch`: no `--ssl-verify` row.

**Recommendation:** Add a `--ssl-verify` row (default: verify) to both command option tables in cli-reference.md. Because disabling SSL verification is a security-relevant choice, documenting it (and cautioning against `--no-ssl-verify` on untrusted networks) is valuable for operators. This is a documentation fix, not a code change.

---

### CLI-004: `--max-retries` documented default and environment binding are inaccurate

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py, docs/99-reference/cli-reference.md |
| **Classification** | advisory |

**Description:** The `batch` command option table in `cli-reference.md` states:

> `--max-retries | -r | int | 3 | Maximum retry attempts … (env: VKDOWNLOADER_MAX_RETRIES)`

Two inaccuracies vs the code:

1. **Default is `None`, not `3`.** cli.py line 428: `max_retries: int | None = typer.Option(None, "--max-retries", ...)`. The effective default comes from `Settings.max_retries` (config.py line 39, default `3`), not from the CLI option. The doc implies the CLI flag itself defaults to `3`.
2. **Environment binding is indirect.** `VKDOWNLOADER_MAX_RETRIES` is read by `Settings` (config.py, `env_prefix="VKDOWNLOADER_"`), and the CLI value only overrides it when explicitly passed (cli.py lines 94–96: `if max_retries_override is not None`). The doc presents the env var as if it is a direct alias of the `--max-retries` flag, which is misleading.

Additionally, the `download` command has **no** `--max-retries` flag at all, yet its retries are still governed by `VKDOWNLOADER_MAX_RETRIES` via `Settings` — an asymmetry the docs do not mention.

**Evidence:**
- cli.py line 428: `max_retries: int | None = typer.Option(None, ...)`.
- cli.py lines 94–96: override applied only when `is not None`.
- config.py lines 39–44, 101–106: `max_retries` field + `env_prefix="VKDOWNLOADER_"`.
- cli-reference.md `batch` options/env tables list `--max-retries` default `3` and `VKDOWNLOADER_MAX_RETRIES`.

**Recommendation:** Update cli-reference.md to state the CLI default is "unset (falls back to `VKDOWNLOADER_MAX_RETRIES`, default 3)" and clarify that `VKDOWNLOADER_MAX_RETRIES` configures `Settings`, which applies to both commands. Optionally, add a `--max-retries` flag to `download` for symmetry and explicit control.

---

### CLI-005: Inconsistent fallback output filename between `download` and `batch` commands

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:** When a video has no title, the two commands generate different fallback filenames for the same video, so running `download` and `batch` on the same URL can produce two different files:

- `download` (cli.py lines 343–347): `validated_output / f"{video.id}_{stream.quality}.mp4"`
- `batch` `_download_single` (cli.py lines 114–118): `validated_output / f"{index}_{video.id}.mp4"`

The `download` fallback also omits the quality suffix in `batch` would not matter, but the ordering and exact composition differ. This is a cosmetic inconsistency that can confuse users expecting deterministic, identical output naming across both entry points.

**Evidence:**
- cli.py line 347: `output_file = validated_output / f"{video.id}_{stream.quality}.mp4"`
- cli.py line 118: `output_file = validated_output / f"{index}_{video.id}.mp4"`

**Recommendation:** Extract the output-filename construction into a single shared helper used by both `download` and `_download_single` so naming is identical across commands. Pick one canonical scheme (e.g. `{sanitized_title}_{video.id}.mp4`, with a stable no-title fallback). This reduces duplication and user confusion.

---
