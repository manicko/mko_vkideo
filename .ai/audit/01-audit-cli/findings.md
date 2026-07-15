# Phase 01 Audit Findings — CLI Entry Point & Command Layer

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/01-audit-cli.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 Import | `uv run python -c "import vkdownloader.cli ..."` | OK — all 14 submodules import cleanly |
| R2 Help | `vkdownloader --help`, `download --help`, `batch --help` | OK — all commands render without error |
| R3 Lint/Type | `uv run ruff check src/vkdownloader/cli.py` | Pass (exit 0) |
| R3 Lint/Type | `uv run mypy src/vkdownloader/cli.py` | Pass (exit 0) — note: "unused section(s): module = ['tests.*']" in pyproject |
| R4 Tests | `uv run pytest -q` | 201 passed, 4 warnings (test-side `coroutine never awaited`, not CLI production) |

No CRITICAL runtime breakage found. All problems below are from code-level audit of the CLI command layer, error presentation, and config/state access.

---

## Findings

### CLI-001: `ValueError` handler misattributes all ValueErrors as "Invalid URL format"

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 152-157) |
| **Classification** | mandatory |

**Description:** The `download` command's error handler catches a bare `ValueError` and unconditionally prints "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}", then exits 1. But `ValueError` is raised from more than one source inside the wrapped coroutine:

- `QualitySelector.select` raises `ValueError("Cannot select from empty streams list")` when `video.streams` is empty (quality.py:62-63). This is an *extraction* failure (video was found but has no playable streams), not a URL-format problem.
- Any Pydantic/env/Settings validation or path-processing `ValueError` would also be mislabeled.

The user is given incorrect guidance ("fix your URL") for a completely different root cause, and the real error is discarded (`raise typer.Exit(code=1) from None`).

**Evidence:**
```python
# cli.py:152-157
except ValueError:
    typer.echo(
        "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}",
        err=True,
    )
    raise typer.Exit(code=1) from None
```
Trigger path: `extractor.extract_streams(url)` returns a video with `streams == []` → `selector.select(video.streams, quality)` → `raise ValueError("Cannot select from empty streams list")` (quality.py:63) → caught here → wrong message.

**Recommendation:** Do not blanket-catch `ValueError` for URL validation. Either (a) let `QualitySelector.select` raise a dedicated typed error (e.g. reuse `QualityNotAvailableError` or a new `NoStreamsError`) and add a specific handler, or (b) narrow the URL-format `ValueError` to the exact `extract_streams` call and keep extraction failures under the generic handler with logging (see CLI-003). Effort: small. Priority: recommended.

---

### CLI-002: `QualityNotAvailableError` presentation depends on brittle message string-parsing

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 161-172), `src/vkdownloader/services/quality.py` (lines 80-83) |
| **Classification** | advisory |

**Description:** `QualityNotAvailableError` carries semantic data (requested quality + available list) but only as a formatted string. The CLI reverses that string with positional `'`/`"Available: "` splitting instead of reading structured fields:

```python
# cli.py:163-166
requested = error_str.split("'")[1] if "'" in error_str else "unknown"
available_str = error_str.split("Available: ")[-1] if "Available: " in error_str else ""
available_qualities = available_str.replace("'", "").replace("[", "").replace("]", "")
```
Coupling risks:
- The exception message is produced at quality.py:81-82 as `f"Requested quality '{quality}' not available. Available: {available_qualities}"`. Any wording change (different quoting, reordering, localization) silently degrades CLI output to "unknown" / empty list.
- `split("'")[1]` assumes exactly the right number of single quotes; a quality token containing `'` shifts the index.
- The available list is rebuilt by stripping `[]`'`,` characters — hacky and lossy.

**Evidence:** quality.py:81-83 raises the message; cli.py:161-172 parses it. No contract ties the two together (the exception class has no fields).

**Recommendation:** Add structured fields to `QualityNotAvailableError` (e.g. `requested: str` and `available: list[str]`) and render them directly in the CLI handler. This removes the string-contract dependency and is robust to message wording changes. Effort: small. Priority: recommended.

---

### CLI-003: Generic `except Exception` discards the real error with no log record

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 173-175) |
| **Classification** | advisory |

**Description:** The final catch-all swallows every non-handled exception and prints only "An error occurred during download":
```python
# cli.py:173-175
except Exception:
    typer.echo("An error occurred during download", err=True)
    raise typer.Exit(code=1) from None
```
structlog is configured (`setup_logging()` at line 99), yet the exception is never logged. Operators get no record of the failure (no message, no traceback), and `from None` suppresses exception chaining. This is good for not leaking raw tracebacks to stdout, but it destroys diagnosability — the single most important signal for "why did the download fail" is lost.

**Evidence:** cli.py:173-175 — no `logger.exception(...)` before exit; `from None` hides the cause.

**Recommendation:** Log the exception at ERROR with traceback (`logger.exception("download_failed", ...)`) before presenting a concise user message. This keeps stdout clean while preserving an operator-facing record for maintenance. Effort: trivial. Priority: recommended.

---

### CLI-004: Repeated `Settings()` construction and inconsistent config sourcing in `batch`

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (lines 246, 297, 348) |
| **Classification** | advisory |

**Description:** Inside `batch_download`, `Settings()` is instantiated three times to read individual defaults, and a fresh `Settings(...)` is built per URL:
- line 246: `max_retries if max_retries is not None else Settings().max_retries`
- line 297: `asyncio.Semaphore(Settings().max_concurrent_downloads)`
- line 348: `max_concurrent = Settings().max_concurrent_downloads` (re-read for the summary)

Each construction re-reads env and re-validates. The per-URL `Settings(cookie_source=..., max_retries=..., ssl_verify=...)` only forwards three fields, so any other env-driven setting (e.g. `download_timeout`, `throttled_rate`) silently falls back to defaults rather than reflecting the user's env config. It is also wasteful and easy to get out of sync.

**Evidence:** cli.py:246, 297, 348 construct `Settings()` independently of the per-URL settings object.

**Recommendation:** Construct one `Settings` instance at the top of `batch_download` and reuse it (pass `max_retries`/`max_concurrent_downloads` from that single object, and reuse it when building per-URL settings). Effort: trivial. Priority: recommended.

---

### CLI-005: Progress callback writes `ProgressManager._state` directly, bypassing the public API and lock

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (line 43), `src/vkdownloader/services/downloader_throttle.py` (lines 78-91, 97-106) |
| **Classification** | advisory |

**Description:** The CLI progress callback mutates a private attribute of `ProgressManager` directly:
```python
# cli.py:43
_progress_manager._state[url_index] = (downloaded, total)
```
Meanwhile `get_formatted_progress` / `update` read and write the same `_state` under an `asyncio.Lock`. The design (documented in downloader_throttle.py:78-91) relies on "GIL-atomic tuple assignment in CPython" for safety. Problems:
- It accesses a `_private` attribute from outside the class, breaking encapsulation and the documented API (`update()` exists for this).
- The thread-/async-safety argument only holds on CPython; on PyPy or other runtimes the assumption breaks, and mixing locked-reads with unlocked-writes is inconsistent.
- The `(downloaded, total)` tuple shape is duplicated between the writer (cli.py) and the reader (`get_formatted_progress`), so a shape change must be edited in two places.

**Evidence:** cli.py:43 writes `_state` without lock; downloader_throttle.py:97-106 `update()` writes under lock; downloader_throttle.py:108-122 read under lock.

**Recommendation:** Have the callback call `await _progress_manager.update(url_index, downloaded, total)` (or expose a documented fire-and-forget method on `ProgressManager`) so writes go through the same API and lock. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

- **CLI-001** (MEDIUM, mandatory): `ValueError` handler misattributes extraction/empty-stream failures as "Invalid URL format". Narrow handling or use a typed error.

## Advisory Recommendations

- **CLI-002** (MEDIUM): Replace brittle `QualityNotAvailableError` message string-parsing with structured exception fields.
- **CLI-003** (MEDIUM): Log the real exception before the generic user-facing message in the catch-all handler.
- **CLI-004** (LOW): Construct `Settings` once in `batch_download` and reuse it.
- **CLI-005** (LOW): Route progress callbacks through `ProgressManager.update()` instead of writing `_state` directly.

## Doc Updates Needed

None — no documentation deviations were identified in this phase (docs were not present/required for these findings).

