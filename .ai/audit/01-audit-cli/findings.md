# Phase 01 Audit Findings - Entry Point & Command Layer

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** in-progress
**Validated:** no

---

## Runtime Verification Evidence

### R1 - Import Verification

`uv run python -c "import vkdownloader.cli"` produces `IMPORT OK` (exit 0).
The entry-point module and all downstream submodules (config, exceptions,
models.*, services.*, utils.*, infrastructure.*) are importable. No
broken dependencies.

### R2 - Entry Point Help / Schema Verification

| Command | Result |
|---------|--------|
| `app --help` (via CliRunner) | Exit 0 - lists `download` and `batch` commands |
| `download --help` | Exit 0 - all options documented |
| `batch --help` | Exit 0 - all options documented |
| `python -m vkdownloader.cli --help` | **Exit 0 - NO output produced** (see CLI-001) |
| `python -m vkdownloader --help` | **Exit 1 - no __main__.py** at package level |
| `download <invalid-url>` | Exit 1 - "Invalid URL format" |
| `download --cookie-source file` | Exit 1 - "Configuration error", no traceback |
| `download --quality invalid` | Exit 2 - Typer enum validation error |

### R3 - Linter and Type Checker

| Tool | Result |
|------|--------|
| `uv run ruff check src/ tests/` | **All checks passed!** (exit 0) |
| `uv run mypy src/vkdownloader/` | **Success** (exit 0) - one config note: unused tests.* section (see CLI-008) |

### R4 - Test Suite

`uv run pytest tests/test_cli.py -v` -> **23 passed** (0.70s)
`uv run pytest tests/` -> **248 passed** (9.64s)
No skipped or failing tests.

---

## Findings

### CLI-001: `python -m vkdownloader.cli` silently exits with no output

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:**

Running `python -m vkdownloader.cli --help` produces zero output and exits 0.
The module defines a `cli()` entry-point function (cli.py lines 606-608) but
never invokes it at module level -- there is no `if __name__ == "__main__":
cli()` guard, and no `src/vkdownloader/__main__.py` file exists. Users who
invoke the package or module via the standard `python -m` pattern get no
feedback whatsoever, contrary to every Python CLI convention.

**Evidence:**

- cli.py lines 606-608: `def cli() -> None: app()` -- no `__main__` guard.
- `glob("src/vkdownloader/**/__main__.py")` -> no files found.
- Runtime: `uv run python -m vkdownloader.cli --help` -> exit 0, no stdout/stderr.
- Runtime: `uv run python -m vkdownloader --help` -> exit 1 (no __main__.py).
- Console-script entry point (`vkdownloader = "vkdownloader.cli:cli"` in
  pyproject.toml line 42) works because it calls cli() explicitly, but
  `python -m` does not.
- Installation docs (docs/01-tools/installation.md line 145) only document
  `vkdownloader --help`, never `python -m`.

**Recommendation:**

Add `if __name__ == "__main__": cli()` at the bottom of cli.py and create
`src/vkdownloader/__main__.py` calling cli(). This enables both
`python -m vkdownloader` and `python -m vkdownloader.cli`. Effort: trivial.
Priority: recommended.

---

### CLI-002: Download orchestration logic duplicated in the entry layer

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:**

The `download()` command handler (lines 384-508) contains a nested async
function `_download()` (lines 418-455) that re-implements the exact same
download orchestration already encapsulated in `_download_single()` (lines
166-244) -- both functions live in the entry-point module. The `download()`
handler should delegate to a single shared service function instead of
re-implementing extraction, quality selection, output resolution, and
download invocation inline.

**Evidence:**

`download._download()` (cli.py lines 418-455) duplicates the core sequence
found in `_download_single()` (cli.py lines 195-227):

| Step | `_download_single()` (batch) | `download._download()` (single) |
|------|------------------------------|---------------------------------|
| Create extractor | `VKVideoExtractor(settings=settings)` (line 199) | `VKVideoExtractor(settings=settings)` (line 423) |
| Extract streams | `await extractor.extract_streams(url)` (line 200) | `await extractor.extract_streams(url)` (line 424) |
| Guard empty streams | `QualityNotAvailableError(...)` (lines 203-208) | `QualityNotAvailableError(...)` (lines 427-432) |
| Select quality | `selector.select(video.streams, quality)` (line 211) | `selector.select(video.streams, quality)` (line 439) |
| Resolve output | `_resolve_output_file(...)` (line 213) | `_resolve_output_file(...)` (line 441) |
| Download | `perform_download(...)` (lines 215-227) | `perform_download(...)` (lines 443-452) |

The only material differences are: (1) `_download_single` handles batch
context (semaphore, backoff coordinator, progress callback, index); (2)
`download._download()` logs available qualities (lines 436-437); (3) return
types differ (tuple vs Path). The shared extraction-to-download flow is
identical and should not be duplicated.

This violates the project guideline "Strict Separation of Concerns" and
"Single Responsibility" -- the entry layer should parse arguments, delegate
to a service, and present results, not contain parallel download
orchestration.

**Recommendation:**

Extract the shared download orchestration (extract + guard empty streams +
quality select + resolve output + `perform_download`) into a service-layer
function (e.g., `services/downloader.py:download_video()`). Have both
`download()` and `_download_single()` delegate to it, with batch-specific
context (semaphore, backoff, progress) passed as optional parameters.
Effort: medium. Priority: recommended.

---

### CLI-003: Path resolution and exception-mapping helpers live in the entry layer

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/utils/security.py` |
| **Classification** | advisory |

**Description:**

The entry-point module `cli.py` contains two data-processing helpers that
belong in the service/utils layer: `_resolve_output_file()` (lines 113-142,
resolves output paths, validates against traversal, creates directories, and
generates sanitized filenames) and `_map_exception_to_status()` (lines
145-163, classifies download exceptions into user-facing status labels).
These are not CLI-argument-handling concerns -- they are business-logic
utilities that couple the entry layer to data and model details.

**Evidence:**

- cli.py lines 113-142: `_resolve_output_file()` imports `validate_output_path`
  and `_sanitize_title` from `utils.security` (line 27), then adds path
  resolution, directory creation, and filename templating logic inline. This
  mixes path resolution (data concern) with filename generation (model
  concern) inside the entry layer.
- cli.py lines 145-163: `_map_exception_to_status()` maps
  `QualityNotAvailableError`, `VideoNotFoundError`, and `VKDownloadError`
  to string status labels. This classification logic is testable business
  logic that is currently untestable in isolation because it is embedded in
  the CLI module.
- The project guidelines require "clear boundaries between UI, API, business
  logic, and data layers" (project.md rule 3).

**Recommendation:**

Move `_resolve_output_file()` into `utils/security.py` alongside
`validate_output_path` and `_sanitize_title` (it already uses both). Move
`_map_exception_to_status()` into `exceptions.py` or a dedicated
`services/exception_mapper.py` so it can be unit-tested independently.
Effort: small. Priority: recommended.

---

### CLI-004: Batch command lacks catch-all exception handler

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:**

The `download()` command handler has a catch-all `except Exception` (line 505)
that logs the error internally and shows a friendly "An error occurred during
download" message to the user. The `batch_download()` command handler (lines
511-603) has **no equivalent catch-all** -- only `ValidationError`, `OSError`,
and `(KeyboardInterrupt, asyncio.CancelledError)` are caught. Any other
unexpected exception from `asyncio.run(_run_batch_with_progress(...))`
would propagate as a raw traceback, inconsistent with the `download()`
handler and the documented exit-code behavior.

**Evidence:**

`download()` error handling (cli.py lines 473-508):
```python
except ValidationError as e:
except ValueError:
except (KeyboardInterrupt, asyncio.CancelledError):
except QualityNotAvailableError as e:
except VideoNotFoundError:
except Exception:                    # catch-all (line 505)
    logger.exception("download_failed")
    typer.echo("An error occurred during download", err=True)
    raise typer.Exit(code=1) from None
```

`batch_download()` error handling (cli.py lines 595-603):
```python
except ValidationError as e:
except OSError as e:
except (KeyboardInterrupt, asyncio.CancelledError):
    # NO catch-all except Exception
```

If `_run_batch_with_progress()` raises an unexpected exception (e.g., a bug
in semaphore creation, progress-manager state, or `asyncio.gather`), the
user sees a full Python traceback instead of a clean error message and
exit code 1.

**Recommendation:**

Add a catch-all `except Exception` handler to `batch_download()` mirroring
`download()`'s pattern: `logger.exception("batch_download_failed")` followed
by `typer.echo("An error occurred during batch download", err=True)` and
`raise typer.Exit(code=1) from None`. Effort: trivial. Priority: recommended.

---

### CLI-005: Redundant double-await and redundant exception handling in batch loop

| Field | Value |
|-------|-------|
| **ID** | CLI-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:**

`_run_batch_with_progress()` (lines 247-335) iterates tasks via
`asyncio.as_completed()` (line 305) but discards each result with a bare
`await coro` (line 307). It then immediately calls
`asyncio.gather(*tasks, return_exceptions=True)` (line 323) to re-collect
the same already-completed task results. The `as_completed` loop's
`except Exception` handler (line 316) also logs exceptions that `gather`
already captures as return values, creating redundant exception handling.

**Evidence:**

cli.py lines 305-332:
```python
for coro in asyncio.as_completed(tasks):
    try:
        await coro                       # result discarded
    except asyncio.CancelledError:
        ...
        raise
    except Exception:
        logger.exception("unexpected_error_in_batch_progress")  # redundant
    typer.echo(f"\\r{await _format_progress(total)}", nl=False)

typer.echo()
results = await asyncio.gather(*tasks, return_exceptions=True)  # re-fetches
```

`_download_single()` (the task coroutine) catches `QualityNotAvailableError`,
`VideoNotFoundError`, and `VKDownloadError` internally (returning status
tuples), so the `as_completed` loop's `except Exception` only fires for truly
unexpected exceptions -- which `gather(return_exceptions=True)` then captures
again at line 323 and converts to status tuples at lines 325-332. The
logging at line 316 provides no additional information beyond what the
results processing already records.

**Recommendation:**

Simplify the pattern: use a single `asyncio.gather(return_exceptions=True)`
for result collection and process exceptions in the results-mapping step.
If live progress updates are needed, use a `progress_callback` parameter on
the tasks themselves rather than an `as_completed` loop that discards
results. Effort: small. Priority: recommended.

---

### CLI-006: Single `download` command shows no progress feedback

| Field | Value |
|-------|-------|
| **ID** | CLI-006 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `docs/99-reference/cli-reference.md`, `docs/99-reference/cli-reference-clean.md` |
| **Classification** | advisory |

**Description:**

The `download()` command invokes `perform_download()` without a
`progress_callback` (cli.py lines 443-452), so single-download users see no
live progress -- just a brief "Downloaded: <path>" message on success. The
`batch_download()` command uses `ProgressManager` and per-URL progress
callbacks (lines 279-294), and the docs explicitly acknowledge the gap: "the
single `download` command shows no live progress during execution"
(cli-reference.md line 17; cli-reference-clean.md line 17). This is an
inconsistent user experience between the two commands.

**Evidence:**

- cli.py lines 443-452: `perform_download(url, str(stream.quality),
  output_file, method, extractor, settings, video_data=video,
  selected_stream=stream)` -- no `progress_callback` kwarg passed.
- cli.py lines 279-294: `batch_download()` creates callbacks via
  `_create_progress_callback()` and wires them through
  `DownloadContext(progress_callback=callbacks[i])`.
- `docs/99-reference/cli-reference.md` line 17: "the single `download`
  command shows no live progress during execution."
- `docs/01-tools/vkdownloader-overview.md` lines 173-197: documents
  `FfmpegProgress`, `ProgressParser`, and `progress_callback` infrastructure
  that exists but is not wired into the single `download` command.

**Recommendation:**

Wire the existing `ProgressManager` + `_create_progress_callback()` mechanism
(already proven in batch) into the single `download` command so both commands
provide consistent progress feedback. At minimum, document the limitation
prominently in the `download` command's help text and the CLI reference docs
so users know to use `batch` for progress visibility. Effort: medium.
Priority: recommended.

---

### CLI-007: Incorrect thread-safety claim in progress callback docstring

| Field | Value |
|-------|-------|
| **ID** | CLI-007 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:**

The `_create_progress_callback()` docstring (cli.py lines 88-93) and the
`ProgressManager.update_sync()` docstring (downloader_throttle.py lines
106-121) both claim that progress callbacks "execute sequentially in the
single-threaded asyncio event loop" and are safe to call without lock
protection. In reality, yt-dlp progress hooks fire inside a thread-pool
executor (`loop.run_in_executor`), so callbacks execute from worker threads
-- not the event loop thread.

**Evidence:**

- cli.py lines 88-93: docstring states "callbacks execute sequentially in
  the single-threaded asyncio event loop."
- downloader.py lines 622-648: yt-dlp's `_download()` runs via
  `loop.run_in_executor(None, _download)`:
  ```python
  loop = asyncio.get_running_loop()
  download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))
  ```
  yt-dlp's progress hook (`_progress_hook`, lines 199-212) is called from
  within this executor thread, invoking `progress_callback(video_id,
  downloaded, total)` -- which calls `update_sync()` from a worker thread.
- downloader_throttle.py lines 106-121: `update_sync()` docstring states
  "This method is for use with sync callbacks that run within the asyncio
  event loop." -- incorrect; the callbacks run in executor threads.
- In CPython, dict assignment is GIL-atomic so no data corruption occurs in
  practice, but the documentation is misleading and the pattern is fragile
  if the GIL assumptions change.

**Recommendation:**

Correct both docstrings to accurately state that progress callbacks run in
executor threads (not the event loop). If thread-safety is a concern beyond
CPython's GIL, use the async `update()` method (which acquires the asyncio
lock) -- but note this would require the callback to schedule an async
callback via `asyncio.run_coroutine_threadsafe()`. Effort: trivial (docstring
fix) to small (locking change). Priority: recommended.

---

### CLI-008: mypy config has unused `tests.*` override section

| Field | Value |
|-------|-------|
| **ID** | CLI-008 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

**Description:**

Running `uv run mypy src/vkdownloader/` emits the warning
`unused section(s): module = ['tests.*']`. The `[[tool.mypy.overrides]]`
block for `tests.*` (pyproject.toml lines 89-91) is never matched because
the mypy invocation only scans `src/vkdownloader/`, not `tests/`. The override
is silently ignored, producing confusing noise for developers running type
checks.

**Evidence:**

- pyproject.toml lines 89-91:
  ```toml
  [[tool.mypy.overrides]]
  module = "tests.*"
  disallow_untyped_defs = false
  ```
- pyproject.toml lines 93-95 (the `vkdownloader.cli` override IS used and
  correct):
  ```toml
  [[tool.mypy.overrides]]
  module = "vkdownloader.cli"
  disallow_untyped_decorators = false
  ```
- Runtime: `uv run mypy src/vkdownloader/` -> "pyproject.toml: note: unused
  section(s): module = ['tests.*']"

**Recommendation:**

Either (a) add a separate mypy invocation for tests (e.g.,
`mypy src/ tests/`) so the override is exercised, or (b) scope the `tests.*`
override so it only appears when tests are included in the scan. The
`vkdownloader.cli` override should be retained -- it correctly suppresses
`disallow_untyped_decorators` for Typer's decorator-based command functions.
Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 3 |
| LOW | 5 |

## Mandatory Fixes

No findings classified as mandatory (security, data loss, or correctness
violations). All 8 findings are advisory.

## Advisory Recommendations

| ID | Severity | Summary |
|----|----------|---------|
| CLI-001 | MEDIUM | `python -m vkdownloader.cli` produces no output -- add `__main__` guard and `__main__.py` |
| CLI-002 | MEDIUM | Download orchestration duplicated in entry layer -- extract to service-layer function |
| CLI-003 | LOW | `_resolve_output_file` and `_map_exception_to_status` belong in utils/exceptions layer |
| CLI-004 | MEDIUM | `batch_download()` missing catch-all `except Exception` -- inconsistent error handling |
| CLI-005 | LOW | Redundant `as_completed` + `gather` double-await and exception logging in batch loop |
| CLI-006 | LOW | Single `download` command has no progress feedback -- wire in existing `ProgressManager` |
| CLI-007 | LOW | Progress callback docstrings falsely claim event-loop-thread execution |
| CLI-008 | LOW | mypy `tests.*` override section is unused when scanning `src/` only |

## Doc Updates Needed

| ID | Label | Description |
|----|-------|-------------|
| CLI-001 | [DOC-UPDATE] | Installation docs should document `python -m vkdownloader` invocation |
| CLI-006 | [DOC-UPDATE] | CLI reference docs should prominently warn that `download` shows no live progress |
