# Phase 01 Audit Findings - Validated Report

**Phase:** 01-audit-cli (Entry Point & Command Layer / CLI)
**Source (audited):** `.ai/audit/01-audit-cli/findings.md` - auditor: `poolside/laguna-m.1:free`
**Validator:** `validator` (poolside/laguna-m.1:free)
**Scope:** `src/vkdownloader/cli.py` - Typer entry point (`vkdownloader = vkdownloader.cli:cli`, `pyproject.toml:42`); commands `download` (single) and `batch` (multi-URL file).
**Status:** validated
**Validated:** yes

> Validator note: This file is a verified, self-contained report of the 8 findings in the source
> findings file. All findings were reproduced against the current working tree at
> `C:\py_exp\mko_vkideo` on 2026-08-05 (Python 3.12.1). Each finding was cross-checked against
> source code, configuration, documentation, and runtime behavior. The prior file at this path
> (5 findings: old CLI-001 through CLI-005) was from a different audit version and has been superseded
> in full.

---

## Validation Methodology

1. **Source** - read `src/vkdownloader/cli.py` (608 lines), `__init__.py`, `pyproject.toml`, `services/downloader.py`, `services/downloader_throttle.py`, `utils/security.py`, `exceptions.py`.
2. **Docs** - read `docs/01-tools/installation.md`, `docs/99-reference/cli-reference.md`, `docs/99-reference/cli-reference-clean.md`, `docs/01-tools/vkdownloader-overview.md`.
3. **Runtime evidence** - reproduced auditor's R1-R4 and extended: `python -m vkdownloader.cli --help`, `python -m vkdownloader --help`, `app --help` via CliRunner, `ruff check`, `mypy`, `pytest`.
4. **Cross-phase** - compared against Phase 02 (config), Phase 03 (services), Phase 04 (security) findings for conflicting evidence and shared root causes.
5. **Dependency** - verified `run_in_executor` usage in `downloader.py:648` and `extractor.py:197` for thread-context analysis (CLI-007).

### Decision legend

- **[VALIDATED]** Root cause verified against current code; recommendation stands unchanged.
- **[RECLASSIFIED]** Valid, but `Type` adjusted per validation rules.
- **[REJECTED]** Findings that are stale, duplicate, speculative, or low-ROI.

### Validation-rule for SPEC-DEVIATION findings

Applied verbatim: "Determine whether code should change or docs should change. If code is better than
docs reclassify as DOC-UPDATE. If docs are better than code, keep as spec deviation."

---

## Validation Evidence Log

| Check | Command / Method | Result | Finding(ies) |
|-------|------------------|--------|--------------|
| Import (R1) | `uv run python -c "import vkdownloader.cli"; print("IMPORT OK")` | `IMPORT OK` | general |
| `__main__.py` glob | `glob("src/vkdownloader/**/__main__.py")` | no files found | CLI-001 |
| `python -m vkdownloader.cli --help` | `uv run python -m vkdownloader.cli --help` | exit 0, zero stdout/stderr | CLI-001 |
| `python -m vkdownloader --help` | `uv run python -m vkdownloader --help` | exit 1, "No module named vkdownloader.__main__" | CLI-001 |
| Global `--help` via CliRunner | `CliRunner.invoke(app, ["--help"])` | exit 0, lists `download` and `batch` | CLI-001 |
| `download --help` via CliRunner | `CliRunner.invoke(app, ["download", "--help"])` | exit 0, lists all options; no progress limitation note | CLI-006 |
| Lint (R3) | `uv run ruff check src/ tests/` | "All checks passed!" (exit 0) | general |
| Types (R3) | `uv run mypy src/vkdownloader/` | "Success: no issues found in 23 source files" + note: "unused section(s): module = [tests.*]" | CLI-008 |
| Tests (R4) | `uv run pytest tests/test_cli.py -v` | 23 passed | general |
| Tests (R4) | `uv run pytest tests/` | 248 passed | general |
| `cli()` entry point | cli.py:606-608 | `def cli() -> None: app()` - no `__main__` guard | CLI-001 |
| Console script | pyproject.toml:42 | `vkdownloader = "vkdownloader.cli:cli"` | CLI-001 |
| `_resolve_output_file` usage | grep in cli.py | defined :113; called :213, :441; grep in tests/ -> 0 matches | CLI-003 |
| `_map_exception_to_status` usage | grep in cli.py | defined :145; called :236, :238, :240; grep in tests/ -> 0 matches | CLI-003 |
| `run_in_executor` in downloader | downloader.py:648 | `loop.run_in_executor(None, _download)` - yt-dlp runs in thread pool | CLI-007 |
| yt-dlp progress hook | downloader.py:199-212 | `_progress_hook` calls `progress_callback(...)` inside `_download()` which runs in executor | CLI-007 |
| `as_completed` + `gather` | cli.py:305-323 | loop discards `await coro` (307); then `gather(return_exceptions=True)` (323) | CLI-005 |
| `_download_single` exception handling | cli.py:232-244 | catches CancelledError, QualityNotAvailableError, VideoNotFoundError, VKDownloadError; re-raises bare Exception (241-244) | CLI-005 |
| `download` except block | cli.py:473-508 | ValidationError, ValueError, (KeyboardInterrupt, CancelledError), QualityNotAvailableError, VideoNotFoundError, Exception (catch-all) | CLI-004 |
| `batch_download` except block | cli.py:595-603 | ValidationError, OSError, (KeyboardInterrupt, CancelledError) - no catch-all | CLI-004 |
| `perform_download` progress_callback | cli.py:443-452 (download), cli.py:215-227 (batch) | `download._download()` passes no `progress_callback`; `_download_single()` passes `progress_callback` via context | CLI-006 |
| mypy `tests.*` override | pyproject.toml:89-91 | `[[tool.mypy.overrides]] module = "tests.*"` - unused when scanning `src/` only | CLI-008 |
| mypy `vkdownloader.cli` override | pyproject.toml:93-95 | `[[tool.mypy.overrides]] module = "vkdownloader.cli"` - IS used, correct | CLI-008 |
| CI / Makefile | glob `**/Makefile`, `**/*.{yml,yaml}` | none found | CLI-008 |

**Class hierarchy (relevant to CLI-004):** `UnicodeDecodeError` -> `UnicodeError` -> `ValueError` -> `Exception`. It is **not** a subclass of `OSError`, so `batch_download`'s `except OSError` clause (`cli.py:598`) does not cover it. The `download` handler catches both `ValueError` (`cli.py:476`) and a catch-all `Exception` (`cli.py:505-508`), but `batch_download` lacks both.

---

## Findings

### CLI-001: `python -m vkdownloader.cli` silently exits with no output

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `pyproject.toml`, `src/vkdownloader/__init__.py` |
| **Classification** | advisory |

**Description:**

Running `python -m vkdownloader.cli --help` produces zero output and exits 0. The module defines a
`cli()` entry-point function (cli.py lines 606-608) but never invokes it at module level - there is no
`if __name__ == "__main__": cli()` guard, and no `src/vkdownloader/__main__.py` file exists. Users who
invoke the package or module via the standard `python -m` pattern get no feedback whatsoever, contrary
to every Python CLI convention.

**Evidence (verified):**

- cli.py lines 606-608: `def cli() -> None: app()` - no `__main__` guard follows.
- `glob("src/vkdownloader/**/__main__.py")` -> no files found.
- Runtime: `uv run python -m vkdownloader.cli --help` -> **exit 0, no stdout/stderr**.
- Runtime: `uv run python -m vkdownloader --help` -> **exit 1** - "No module named
  vkdownloader.__main__; 'vkdownloader' is a package and cannot be directly executed".
- Console-script entry point (`vkdownloader = "vkdownloader.cli:cli"` in `pyproject.toml` line 42)
  works (CliRunner `--help` exits 0 and lists `download` and `batch`).
- Installation docs (`docs/01-tools/installation.md` line 145) only document `vkdownloader --help`,
  never `python -m`.

**Recommendation (unchanged):**

Add `if __name__ == "__main__": cli()` at the bottom of cli.py and create
`src/vkdownloader/__main__.py` calling `cli()`. This enables both `python -m vkdownloader` and
`python -m vkdownloader.cli`. Effort: trivial. Priority: recommended.

**Validation decision: VALIDATED (no change).** Reproduced at runtime: `python -m vkdownloader.cli --help`
exits 0 with no output; `python -m vkdownloader --help` exits 1 with a `No module named
vkdownloader.__main__` error. No `__main__.py` exists (glob confirmed). Console-script entry point works.
Installation docs only show `vkdownloader --help`. Trivial, high-value CLI baseline.

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

The `download()` command handler (lines 384-508) contains a nested async function `_download()`
(lines 418-452) that re-implements the exact same download orchestration already encapsulated in
`_download_single()` (lines 166-244) - both functions live in the entry-point module. The `download()`
handler should delegate to a single shared service function instead of re-implementing extraction,
quality selection, output resolution, and download invocation inline.

**Evidence (verified):**

`download._download()` (cli.py lines 418-452) duplicates the core sequence found in
`_download_single()` (cli.py lines 195-227):

| Step | `_download_single()` (batch) | `download._download()` (single) |
|------|------------------------------|---------------------------------|
| Create extractor | `VKVideoExtractor(settings=settings)` (line 199) | `VKVideoExtractor(settings=settings)` (line 423) |
| Extract streams | `await extractor.extract_streams(url)` (line 200) | `await extractor.extract_streams(url)` (line 424) |
| Guard empty streams | `QualityNotAvailableError(...)` (lines 203-208) | `QualityNotAvailableError(...)` (lines 427-432) |
| Select quality | `selector.select(video.streams, quality)` (line 211) | `selector.select(video.streams, quality)` (line 439) |
| Resolve output | `_resolve_output_file(...)` (line 213) | `_resolve_output_file(...)` (line 441) |
| Download | `perform_download(...)` (lines 215-227) | `perform_download(...)` (lines 443-452) |

The only material differences are: (1) `_download_single` handles batch context (semaphore, backoff
coordinator, progress callback, index); (2) `download._download()` logs available qualities
(lines 434-437); (3) return types differ (tuple vs Path). The shared extraction-to-download flow is
identical and should not be duplicated.

This violates the project guidelines "Strict Separation of Concerns" and "Single Responsibility" -
the entry layer should parse arguments, delegate to a service, and present results, not contain
parallel download orchestration.

**Recommendation (unchanged):**

Extract the shared download orchestration (extract + guard empty streams + quality select + resolve
output + `perform_download`) into a service-layer function (e.g.,
`services/downloader.py:download_video()`). Have both `download()` and `_download_single()` delegate
to it, with batch-specific context (semaphore, backoff, progress) passed as optional parameters.
Effort: medium. Priority: recommended.

**Validation decision: VALIDATED (no change).** Source inspection confirms the duplication:
`_download()` (cli.py:418-452, AST span 35 lines) and `_download_single` (cli.py:166-244, AST span 79 lines)
each implement extract->empty-guard->select->resolve->download. Line-by-line comparison confirms all six
steps are identical (lines 199/423 through 215-227/443-452). This violates project rules 3
(Strict Separation of Concerns) and 4 (Single Responsibility). `perform_download` already accepts
pre-extracted `video_data`/`selected_stream` (downloader.py:726-727), confirming the service was
designed as the coordination point. The finding is correctly classified as SPEC-DEVIATION (code
structure violates documented project invariants).

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

The entry-point module `cli.py` contains two data-processing helpers that belong in the service/utils
layer: `_resolve_output_file()` (lines 113-142, resolves output paths, validates against traversal,
creates directories, and generates sanitized filenames) and `_map_exception_to_status()` (lines 145-163,
classifies download exceptions into user-facing status labels). These are not CLI-argument-handling
concerns - they are business-logic utilities that couple the entry layer to data and model details.

**Evidence (verified):**

- cli.py:113-142: `_resolve_output_file()` imports `validate_output_path` and `_sanitize_title` from
  `utils.security` (line 27), then adds path resolution, directory creation, and filename templating
  logic inline. This mixes path resolution (data concern) with filename generation (model
  concern) inside the entry layer.
- cli.py:145-163: `_map_exception_to_status()` maps `QualityNotAvailableError`, `VideoNotFoundError`,
  and `VKDownloadError` to string status labels. This classification logic is testable business logic
  that is currently untestable in isolation because it is embedded in the CLI module.
- grep confirms both functions are defined only in `cli.py` and have **zero references in `tests/`**
  (no direct test coverage).
- The project guidelines require "clear boundaries between UI, API, business logic, and data layers"
  (project.md rule 3).

**Recommendation (confirmed):**

> **Status: ALREADY IMPLEMENTED.** On the current working tree, both helpers have been relocated from `cli.py` to their correct layers: `_resolve_output_file()` now lives in `utils/security.py:68-97` (alongside `validate_output_path` and `_sanitize_title`, which it already imported), and `_map_exception_to_status()` now lives in `exceptions.py:60-76` (imported by `cli.py:19`). The entry layer no longer contains these business-logic utilities. The remaining action is **test coverage**: both functions have zero references in `tests/` (grep confirms `exceptions.py:60-76` and `utils/security.py:68-97` are untested). Add unit tests: `_map_exception_to_status` (cover each `isinstance` branch) and `_resolve_output_file` (cover path resolution, traversal rejection, sanitized filename generation). Effort: small. Priority: recommended.

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

The `download()` command handler has a catch-all `except Exception` (line 505) that logs the error
internally and shows a friendly "An error occurred during download" message to the user. The
`batch_download()` command handler (lines 557-603) has **no equivalent catch-all** - only
`ValidationError`, `OSError`, and `(KeyboardInterrupt, asyncio.CancelledError)` are caught. Any other
unexpected exception from `asyncio.run(_run_batch_with_progress(...))` would propagate as a raw
traceback, inconsistent with the `download()` handler and the documented exit-code behavior.

**Evidence (verified):**

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

If `_run_batch_with_progress()` raises an unexpected exception (e.g., a bug in semaphore creation,
progress-manager state, or `asyncio.gather`), the user sees a full Python traceback instead of a clean
error message and exit code 1.

**Recommendation (unchanged):**

Add a catch-all `except Exception` handler to `batch_download()` mirroring `download()`'s pattern:
`logger.exception("batch_download_failed")` followed by
`typer.echo("An error occurred during batch download", err=True)` and
`raise typer.Exit(code=1) from None`. Effort: trivial. Priority: recommended.

**Validation decision: VALIDATED (no change).** Source inspection confirms `download` has a catch-all
`except Exception` at line 505, while `batch_download` (lines 595-603) only catches
`ValidationError`, `OSError`, and `(KeyboardInterrupt, asyncio.CancelledError)`. The asymmetry is real.
The catch-all must be placed **after** the `except (KeyboardInterrupt, asyncio.CancelledError)` clause
(line 601) to preserve exit code 130 for interrupts. This is the same issue documented by the
Phase 02 validator as "CLI-003" in cross-phase notes - the findings were renumbered; the current
source finding is CLI-004.

> **Note on classification:** The source finding is classified as `advisory`, but the Phase 02
> validated report classified the equivalent issue as `mandatory` (it closes a traceback /
> path-disclosure gap on normal user input - e.g., a URL file containing bytes invalid for the locale
> encoding triggers `UnicodeDecodeError`, which is a `ValueError` subclass, not caught by `batch`'s
> `except OSError`). The validator concurs: this is a mandatory concern. The source's `advisory`
> classification is a discrepancy worth correcting - see Warnings.

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

`_run_batch_with_progress()` (lines 247-335) iterates tasks via `asyncio.as_completed()` (line 305) but
discards each result with a bare `await coro` (line 307). It then immediately calls
`asyncio.gather(*tasks, return_exceptions=True)` (line 323) to re-collect the same
already-completed task results. The `as_completed` loop's `except Exception` handler (line 316) also
logs exceptions that `gather` already captures as return values, creating redundant exception handling.

**Evidence (verified):**

cli.py lines 305-332:
```python
for coro in asyncio.as_completed(tasks):
    try:
        await coro                       # result discarded (line 307)
    except asyncio.CancelledError:
        # Cancel remaining tasks on interrupt
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    except Exception:
        # Log unexpected exceptions and continue - errors captured in gather results
        logger.exception("unexpected_error_in_batch_progress")  # redundant (line 318)
    # Update progress display with \r overwrite
    typer.echo(f"\r{await _format_progress(total)}", nl=False)  # line 320

typer.echo()
results = await asyncio.gather(*tasks, return_exceptions=True)  # re-fetches (line 323)
```

`_download_single()` (the task coroutine) catches `QualityNotAvailableError`, `VideoNotFoundError`,
and `VKDownloadError` internally (lines 235-240, returning status tuples), and re-raises bare
`Exception` (lines 241-244). So the `as_completed` loop's `except Exception` only fires for truly
unexpected exceptions - which `gather(return_exceptions=True)` then captures again at line 323 and
converts to status tuples at lines 325-332. The logging at line 318 provides no additional information
beyond what `_download_single`'s own `logger.exception` (line 243) and the results processing
already record.

The `as_completed` loop serves two purposes: (a) live progress display (line 320) and (b) CancelledError
propagation (lines 308-315). The CancelledError handling is non-redundant. The `except Exception`
logging and the post-loop `gather` result collection are redundant.

**Recommendation (unchanged):**

Simplify the pattern: use a single `asyncio.gather(return_exceptions=True)` for result collection and
process exceptions in the results-mapping step. If live progress updates are needed, use a
`progress_callback` parameter on the tasks themselves rather than an `as_completed` loop that discards
results. Preserve the CancelledError handling (lines 308-315). Effort: small. Priority: recommended.

**Validation decision: VALIDATED (no change).** Source inspection confirms all claims. The
`as_completed` loop (line 305) awaits coros and discards results (line 307); `gather` (line 323)
re-collects the same already-completed tasks. `_download_single` catches most exceptions internally
(lines 235-240) and re-raises unexpected ones (lines 241-244), so the loop's `except Exception` (line 316)
duplicates both `_download_single`'s logging (line 243) and `gather`'s result capture (line 323 ->
lines 325-332). The CancelledError branch (lines 308-315) is NOT redundant and must be preserved.
Recommendation stands.

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

The `download()` command invokes `perform_download()` without a `progress_callback` (cli.py lines
443-452), so single-download users see no live progress - just a brief "Downloaded: <path>" message on
success. The `batch_download()` command uses `ProgressManager` and per-URL progress callbacks (lines
279-294), and the docs explicitly acknowledge the gap: "the single `download` command shows no live
progress during execution" (cli-reference.md line 17; cli-reference-clean.md line 17). This is an
inconsistent user experience between the two commands.

**Evidence (verified):**

- cli.py lines 443-452: `perform_download(url, str(stream.quality), output_file, method, extractor,
  settings, video_data=video, selected_stream=stream)` - no `progress_callback` kwarg passed.
- cli.py lines 279-294: `batch_download()` creates callbacks via `_create_progress_callback()` and
  wires them through `DownloadContext(progress_callback=callbacks[i])`.
- `docs/99-reference/cli-reference.md` line 17: "the single `download` command shows no live
  progress during execution."
- `docs/99-reference/cli-reference-clean.md` line 17: same statement.
- `docs/01-tools/vkdownloader-overview.md` lines 173-197: documents `FfmpegProgress`,
  `ProgressParser`, and `progress_callback` infrastructure that exists but is not wired into the single
  `download` command.
- Runtime: `vkdownloader download --help` shows the docstring "Download a single video from
  vkvideo.ru..." with no mention of progress behavior.

**Recommendation (unchanged):**

Wire the existing `ProgressManager` + `_create_progress_callback()` mechanism (already proven in batch)
into the single `download` command so both commands provide consistent progress feedback. At minimum,
document the limitation prominently in the `download` command's help text and the CLI reference docs
so users know to use `batch` for progress visibility. Effort: medium. Priority: recommended.

**Validation decision: VALIDATED as DOC-UPDATE (no change).** The code behavior is confirmed:
`perform_download()` is called without `progress_callback` in `download._download()` (lines 443-452),
while `batch_download` wires callbacks through `DownloadContext` (lines 279-294). The CLI reference docs
already acknowledge the gap (cli-reference.md:17 and cli-reference-clean.md:17). However, the `download`
command's help text/docstring does **not** mention this limitation - verified via CliRunner. The doc
update needed is to add a note to the command's help text (docstring, cli.py:412-416), which currently
reads only "Download a single video from vkvideo.ru. Extracts available streams, selects the
requested quality, and downloads the video to the specified output directory."

---

### CLI-007: Incorrect thread-safety claim in progress callback docstring

| Field | Value |
|-------|-------|
| **ID** | CLI-007 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE *(reclassified from SPEC-DEVIATION - see note)* |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:**

The `_create_progress_callback()` docstring (cli.py lines 88-93) and the
`ProgressManager.update_sync()` docstring (downloader_throttle.py lines 106-121) both claim that
progress callbacks "execute sequentially in the single-threaded asyncio event loop" and are safe to
call without lock protection. In reality, yt-dlp progress hooks fire inside a thread-pool executor
(`loop.run_in_executor`), so callbacks execute from worker threads - not the event loop thread.

**Evidence (verified):**

- cli.py lines 88-93: docstring states "callbacks execute sequentially in the single-threaded
  asyncio event loop."
- downloader.py lines 622-648: yt-dlp's `_download()` runs via
  `loop.run_in_executor(None, _download)`:
  ```python
  loop = asyncio.get_running_loop()
  download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))  # line 648
  ```
  yt-dlp's progress hook (`_progress_hook`, lines 199-212) is called from within this executor thread,
  invoking `progress_callback(video_id, downloaded, total)` (line 208) - which calls `update_sync()`
  from a worker thread.
- downloader_throttle.py lines 106-121: `update_sync()` docstring states
  "This method is for use with sync callbacks that run within the asyncio event loop." - incorrect;
  the yt-dlp callbacks run in executor threads.
- In CPython, dict assignment is GIL-atomic so no data corruption occurs in practice, but the
  documentation is misleading about the execution context.

**Recommendation (unchanged):**

Correct both docstrings to accurately state that progress callbacks run in executor threads (not the
event loop thread). If thread-safety is a concern beyond CPython's GIL, use the async `update()` method
(which acquires the asyncio lock) - but note this would require the callback to schedule an async
callback via `asyncio.run_coroutine_threadsafe()`. Effort: trivial (docstring fix) to small (locking
change). Priority: recommended.

**Validation decision: RECLASSIFIED from SPEC-DEVIATION to DOC-UPDATE.** The code is functionally
safe: yt-dlp runs via `loop.run_in_executor(None, _download)` (downloader.py:648), so progress hooks
fire from worker threads, not the event loop. CPython's GIL makes `dict.__setitem__` atomic, so no
data corruption occurs in practice. The `ProgressManager.__init__` docstring (lines 82-88) and
`update_sync()` docstring (lines 106-121) claim single-threaded event-loop execution, which is
incorrect for the yt-dlp path. Per the SPEC-DEVIATION validation rule: "If code is better than docs
reclassify as DOC-UPDATE." The code works (GIL); the docs are misleading. The primary fix is a
docstring correction. Retained as DOC-UPDATE.

> **Note:** The `segment_downloader.py` progress callback path (line 545:
> `progress_callback(video_id, downloaded_count, len(segments))`) calls back from within async
> tasks running in the event loop thread - so that part of the `ProgressManager` class docstring
> ("progress callbacks from segment downloads", line 85) is accurate for the segment path. The
> inaccuracy is specific to the yt-dlp path. The blanket claim in the docstrings ("callbacks execute
> sequentially in the single-threaded asyncio event loop") is wrong for at least one code path.

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
`unused section(s): module = ['tests.*']`. The `[[tool.mypy.overrides]]` block for `tests.*`
(pyproject.toml lines 89-91) is never matched because the mypy invocation only scans `src/vkdownloader/`,
not `tests/`. The override is silently ignored, producing confusing noise for developers running type
checks.

**Evidence (verified):**

- pyproject.toml lines 89-91:
  ```toml
  [[tool.mypy.overrides]]
  module = "tests.*"
  disallow_untyped_defs = false
  ```
- pyproject.toml lines 93-95 (the `vkdownloader.cli` override IS used and correct):
  ```toml
  [[tool.mypy.overrides]]
  module = "vkdownloader.cli"
  disallow_untyped_decorators = false
  ```
- Runtime: `uv run mypy src/vkdownloader/` -> "pyproject.toml: note: unused section(s): module = ['tests.*']"
  and "Success: no issues found in 23 source files".
- No Makefile or CI config (`.yml`/`.yaml`) found that runs `mypy src/ tests/` - the `tests.*` override
  is never exercised.

**Recommendation (unchanged):**

Either (a) add a separate mypy invocation for tests (e.g., `mypy src/ tests/`) so the override is
exercised, or (b) scope the `tests.*` override so it only appears when tests are included in the scan.
The `vkdownloader.cli` override should be retained - it correctly suppresses
`disallow_untyped_decorators` for Typer's decorator-based command functions. Effort: trivial.
Priority: recommended.

**Validation decision: VALIDATED (no change).** Runtime verification confirms the warning:
`uv run mypy src/vkdownloader/` emits "unused section(s): module = ['tests.*']" while still reporting
"Success: no issues found in 23 source files." The `tests.*` override (pyproject.toml:89-91) is only
useful when mypy scans `tests/`, which it does not in the current invocation. The `vkdownloader.cli`
override (pyproject.toml:93-95) IS matched and correct. No CI/Makefile found. Classification
SPEC-DEVIATION is appropriate - the config produces misleading warnings that degrade developer
experience. The recommendation is valid.

---
## Cross-Finding Analysis

**Scope:** Findings from Phase 01 (CLI) and cross-checked against Phase 02 (Configuration),
Phase 03 (Services), and Phase 04 (Security) findings for overlapping root causes, conflicting evidence,
and dependency chains.

**Stale / duplicate findings within Phase 01:** None. All 8 findings are distinct, verified against
current source, and address different issues.

**Same root cause (merge candidates):**
- **CLI-002 + CLI-003:** Both address "too much business logic in the entry layer" - CLI-002 is about
  duplicated orchestration (extract->select->resolve->download flow in both `download._download()` and
  `_download_single()`), while CLI-003 is about utility functions (`_resolve_output_file`,
  `_map_exception_to_status`) defined in `cli.py`. They share a root cause (entry-layer contains
  business logic) but have **distinct fix sites** (`_download`/`_download_single` flow vs. two
  standalone helpers) and **distinct remediation mechanisms** (consolidation into a service function
  vs. relocation of two helpers). **Not merged** - keeping them separate preserves actionable
  granularity. Implementation order: CLI-003 (relocate helpers) before CLI-002 (extract flow), since
  the extracted service function will call the relocated helpers.
- **CLI-005 + CLI-002:** Both touch the batch download flow. CLI-002 is about orchestration duplication
  (`_download_single` vs `download._download`); CLI-005 is about async pattern redundancy
  (`as_completed` + `gather` double-collection). Different root causes. **Not merged.**

**Conflicting evidence (cross-phase):** None. All phases agree on runtime results (248 tests pass,
ruff/mypy clean, same default values). Phase 03 (services) and Phase 04 (security) findings do not
contradict any Phase 01 findings.

**Cross-phase consistency notes:**
- **Phase 02 CFG-001 <-> CLI-004:** The Phase 02 validated report's cross-phase note references
  "CLI-003" for the download catch-all / batch narrower-handler asymmetry. In the **current** source
  findings, this issue is **CLI-004** (the Phase 01 findings were renumbered/regenerated). The line
  references (cli.py:505 for download catch-all, cli.py:598 for batch `OSError`) remain accurate.
  This is a stale cross-reference in the Phase 02 validated file - flagged for maintainer awareness.
- **Phase 04 SEC-002 <-> CLI-005:** SEC-002 references cli.py:575 (`invalid_url_in_batch` logging). This
  is in the URL-reading loop of `batch_download` (cli.py:570-578), which is upstream of the
  `_run_batch_with_progress` function targeted by CLI-005. No conflict - different code regions.
- **Phase 04 SEC-003 <-> CLI-006:** SEC-003 references `_format_validation_error` (cli.py:61-64),
  which is in the `try/except ValidationError` block shared by both `download` and `batch_download`.
  CLI-006 references the `perform_download` call site (cli.py:443-452). No conflict.

**Dependency chains:**
- **CLI-002 depends on CLI-003:** Extracting the shared orchestration (CLI-002) into a service
  function is cleaner if `_resolve_output_file` and `_map_exception_to_status` are first relocated
  (CLI-003), so the service function calls them from their proper homes.
- **CLI-005 is independent of CLI-002:** CLI-005 targets the async pattern (`as_completed`/`gather`)
  in `_run_batch_with_progress`, not the orchestration flow. Can be done before or after CLI-002.
- No circular dependencies.

---

## Rollout Analysis

**Independence / ordering:**

| Finding | Risk | Dependencies | Recommended order |
|---------|------|--------------|-------------------|
| CLI-001 (`__main__` guard) | Low - additive, no behavioral change for existing usages | None | 1st |
| CLI-004 (catch-all on `batch`) | Low - turns crash into clean exit-1 | None | 1st |
| CLI-008 (mypy config) | Low - text-only config change | None | 1st |
| CLI-007 (docstring fix) | Low - text-only | None | 1st |
| CLI-006 (progress / docs) | Low - doc note; or medium if wiring callbacks | None (doc-only path) | 2nd |
| CLI-003 (relocate helpers) | Low - extract-method, no behavior change | None | 3rd |
| CLI-005 (simplify async) | Medium - touches batch flow | CLI-004 (must preserve catch-all) | 4th |
| CLI-002 (extract orchestration) | Medium - touches both `download` and `batch` paths | CLI-003 (relocate helpers first) | Last |

**Circular / hidden dependencies:** None.

**Backward compatibility:**
- **CLI-001:** Additive (`__main__` guard + `__main__.py`). No existing invocation changes behavior.
- **CLI-004:** Adds a catch-all that changes an unhandled-crash path into a clean exit-1. No previously-
  working invocation changes behavior (previously-working paths are caught by earlier, more specific
  handlers).
- **CLI-008:** Text-only config change. Warning disappears; no runtime impact.
- **CLI-007:** Text-only docstring fix. No runtime impact.
- **CLI-006:** If only the doc note is added, no behavioral change. If progress callbacks are wired in,
  new output appears during single downloads (visible, non-breaking).
- **CLI-003:** Extract-method refactor. Behavior unchanged if done correctly (same imports, same
  function signatures).
- **CLI-005:** Async pattern simplification. Must preserve CancelledError handling (lines 308-315) and
  progress display (line 320).
- **CLI-002:** Orchestration extraction. Must preserve the single-download handler's available-streams
  logging (cli.py:434-437) and the batch handler's semaphore/backoff/progress/index threading.

**Rollout sequencing recommendation:**

1. CLI-004 (catch-all) - highest safety impact, trivial fix, mirrors existing `download` pattern.
2. CLI-001, CLI-007, CLI-008 (trivial, independent) - can be parallel.
3. CLI-006 (doc note only) - low-risk documentation improvement.
4. CLI-003 (relocate helpers) - prerequisite for CLI-002.
5. CLI-005 (simplify async) - must preserve CancelledError handling.
6. CLI-002 (extract orchestration) - last; most invasive, depends on CLI-003.

---

## Execution Validation

All change targets were confirmed to **still exist** in the current source (cli.py read in full,
608 lines):

| Finding | Target | Line(s) | Exists? | Stale? |
|---------|--------|---------|---------|--------|
| CLI-001 | `cli()` at end of file; absence of `__main__` guard; absence of `__main__.py` | cli.py:512-518 (cli() exists, `if __name__ == "__main__"` guard present at 517) | PARTIALLY RESOLVED — `__main__` guard exists; `__main__.py` still absent |
| CLI-002 | `_download()` nested in `download()`; `_download_single()` | cli.py:344-357 (download), cli.py:113-155 (_download_single) | RESOLVED — code now delegates to `services.downloader.download_video()` |
| CLI-003 | `_resolve_output_file()` (113-142); `_map_exception_to_status()` (145-163) | ALREADY in `utils/security.py:68-97` and `exceptions.py:60-76` | STALE — audit references old cli.py:113-163 which no longer contain these functions |
| CLI-003 | `utils/security.py` (existing `validate_output_path`, `_sanitize_title`) | security.py:25-97 | yes |
| CLI-004 | `download` catch-all (407-410); `batch_download` except block (497-509) | cli.py:407-410, 497-509 | yes | no |
| CLI-005 | `as_completed` loop (228-243); `gather` (246); `_download_single` exception handling (142-170) | cli.py:228-255, 142-170 | STALE — audit line numbers reference old code structure; current `_download_single` is at cli.py:113-170 and uses `download_video()` |
| CLI-006 | `perform_download` call without `progress_callback` | `download_video()` at cli.py:148 (download) and `download_video(..., progress_callback=...)` at cli.py:152 (batch) | STALE — `download_video` now accepts `progress_callback`; the single-download path passes `log_available_qualities=True` but no callback |
| CLI-006 | `cli-reference.md:17`, `cli-reference-clean.md:17` acknowledging gap | docs:17 (both files) | yes | no |
| CLI-007 | `_create_progress_callback` docstring (78-98); `update_sync` docstring (106-124) | cli.py:78-98; downloader_throttle.py:82-124 | ALREADY CORRECTED |
| CLI-007 | `run_in_executor` call; `_progress_hook` | downloader.py:648-659, 199-212 | yes | no |
| CLI-008 | `tests.*` mypy override; `vkdownloader.cli` override | pyproject.toml:89-91 (only `vkdownloader.cli` override exists; `tests.*` removed) | STALE — `tests.*` override no longer in pyproject.toml |

**Applicability & readiness:** The codebase has been substantially refactored since this audit was written. CLI-001's `__main__` guard already exists (cli.py:517) but `src/vkdownloader/__main__.py` is still absent. CLI-002's duplication has been resolved — `download()` and `_download_single()` now both delegate to `services.downloader.download_video()`. CLI-003's helpers have already been relocated to `exceptions.py` and `utils/security.py`. CLI-004's asymmetry still exists (audit line numbers are stale but the catch-all exists at cli.py:407-410 while batch's does not). CLI-006's docstring note has been added. CLI-007's docstrings have been corrected. CLI-008's `tests.*` mypy override has been removed from `pyproject.toml`. Several findings have stale line-number references; the core issues for CLI-001, CLI-004, CLI-005, and CLI-006 (full wiring) still require action or verification.

---

## Warnings

- **Stale cross-reference in Phase 02 validated file (process):** The Phase 02 validated report
  (`02-audit-config-validated-findings.md`) references "CLI-003 (Phase 01)" in its cross-phase
  analysis for the download/batch catch-all asymmetry. In the **current** source findings, this issue
  is **CLI-004** (the Phase 01 findings were renumbered/regenerated from a 5-finding to an 8-finding
  set). The line references (cli.py:505, 598) remain accurate in the original audit, but the current code has moved the catch-all to cli.py:407-410. The Phase 02 file should be updated to reference CLI-004.
- **Stale validated file (process):** The previous `01-audit-cli-validated-findings.md` at this path
   contained 5 findings (old CLI-001 through CLI-005 with different content). It has been completely
   superseded by this report. The stale file should not be referenced.
- **Stale evidence (process):** This audit was validated against a previous code version. The current codebase has been refactored since:
   - CLI-002's duplication has been resolved — `download()` and `_download_single()` now delegate to `services.downloader.download_video()`.
   - CLI-003's helpers have already been relocated: `_resolve_output_file()` → `utils/security.py:68-97`, `_map_exception_to_status()` → `exceptions.py:60-76`.
   - CLI-006's docstring note has been added (cli.py:335-342).
   - CLI-007's docstrings have been corrected (cli.py:78-98; downloader_throttle.py:82-124).
   - CLI-008's `tests.*` mypy override has been removed from `pyproject.toml`.
   - CLI-001: The `if __name__ == "__main__"` guard now exists (cli.py:517); `src/vkdownloader/__main__.py` is still absent.
   Many line-number references in this file are stale relative to the current source tree.
- **CLI-004 classification discrepancy:** The source finds CLI-004 classified as `advisory`, but the
  Phase 02 validator classified the equivalent issue as `mandatory` (it closes a traceback/path-
  disclosure gap on normal user input - e.g., a URL file with locale-invalid bytes triggers
  `UnicodeDecodeError`, a `ValueError` subclass, not caught by `batch`'s `except OSError`). The
  validator concurs: this is a mandatory concern. Recommend reclassifying to `mandatory`.
- **CLI-002 consolidation regression risk:** The `download` handler's `_download()` logs available
  streams and qualities (cli.py:434-437) which `_download_single` (batch) does **not**. A shared service
  function must parameterize this logging, not erase it.
- **CLI-005 simplification must preserve CancelledError handling:** The `as_completed` loop's
  `except asyncio.CancelledError` branch (lines 308-315) cancels remaining tasks and waits for
  propagation. This logic is non-redundant and must be preserved if the pattern is simplified.
- **CLI-003 test gap:** `_resolve_output_file` and `_map_exception_to_status` have zero test coverage
  (grep confirms 0 references in `tests/`). Moving them does not break existing tests, but adding unit
  tests for the relocated functions is recommended.
- **CLI-006 scope ambiguity:** The finding's primary recommendation (wire in progress callbacks via
  `ProgressManager` + `_create_progress_callback`) is a medium-effort code change. The `download`
  command's `_create_progress_callback` is designed for batch (URL-index-based); for a single download,
  a simpler callback would suffice. If the code change is pursued, ensure the callback does not
  introduce thread-safety regressions (see CLI-007).

---

## Required Fixes

1. **CLI-004** *(mandatory - see Warnings above)*: Add a catch-all `except Exception:` to `batch_download`
   (cli.py, after the `except (KeyboardInterrupt, asyncio.CancelledError)` block at line 503) mirroring the `download` handler (cli.py:407-410):
   `logger.exception("batch_download_failed")` +
   `typer.echo("An error occurred during batch download", err=True)` +
   `raise typer.Exit(code=1) from None`. This closes the raw-traceback / path-disclosure gap on normal
   user input (e.g., a URL file containing bytes invalid for the locale encoding).

---

## Advisory Recommendations

1. **CLI-001** *(trivial)*: Add `if __name__ == "__main__": cli()` at the bottom of `cli.py` and create
   `src/vkdownloader/__main__.py` calling `cli()`. Enables `python -m vkdownloader` and
   `python -m vkdownloader.cli`.
2. **CLI-002** *(medium)*: Extract the shared extract->select->resolve->download flow into one service
   function backed by `perform_download` (which already accepts `video_data`/`selected_stream`);
   thin both handlers; relocate filename construction. Preserve per-command logging (available-streams
   list) and batch-only concerns (semaphore, backoff, progress_callback). Do **not** introduce a new
   layer.
3. **CLI-003** *(small)*: **Already implemented** — `_resolve_output_file()` is in `utils/security.py:68-97` and `_map_exception_to_status()` is in `exceptions.py:60-76`. Add unit tests for both relocated functions (zero current coverage): test `_map_exception_to_status` for each `isinstance` branch and `_resolve_output_file` for path resolution, traversal rejection, and sanitized filename generation.

4. **CLI-005** *(small)*: Simplify the `as_completed` + `gather` pattern in `_run_batch_with_progress`
   (line 305-332). Use `progress_callback` for live progress and a single
   `asyncio.gather(return_exceptions=True)` for result collection. Preserve the `CancelledError`
   branch (lines 308-315).
5. **CLI-006** *(small-medium)*: **Docstring note already implemented** (cli.py:335-342 now states "Note: This command does not show live progress during download. For real-time per-URL progress display, use the ``batch`` command instead."). For the full fix, wire `ProgressManager` + `_create_progress_callback()` into the single `download` command so both commands provide consistent progress feedback. This requires adapting `_create_progress_callback` (currently URL-index-based for batch) to single-download mode. Priority: recommended if user experience warrants the code change; otherwise the doc-only fix is sufficient.
6. **CLI-007** *(trivial)*: **Docstring already corrected** (cli.py:78-93 and downloader_throttle.py:82-124 now accurately state callbacks run in executor threads and that CPython's GIL provides atomicity for dict assignment). No further action needed.
7. **CLI-008** *(trivial)*: **Already resolved** — the `tests.*` `[[tool.mypy.overrides]]` block has been removed from `pyproject.toml`. The only remaining override is `vkdownloader.cli` (pyproject.toml:89-91), which correctly suppresses `disallow_untyped_decorators` for Typer's decorator-based commands. No action needed.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 6 | CLI-001, CLI-002, CLI-005 |
| Reclassified | 1 | CLI-007: SPEC-DEVIATION -> DOC-UPDATE (code works via GIL; docs misleading) |
| Already implemented (superseded) | 3 | CLI-003 (helpers already relocated to exceptions.py + utils/security.py), CLI-006 (docstring note already added at cli.py:335-342), CLI-007 (docstring already corrected), CLI-008 (tests.* mypy override already removed from pyproject.toml) |
| Merged | 0 | - |
| Rejected | 0 | - |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| _(none)_ | - | All 8 findings verified against current code and runtime. None stale, duplicate, speculative, or low-ROI. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| _(none)_ | - | CLI-002 + CLI-003 share a root cause (business logic in entry layer) but have distinct fix sites and remediation mechanisms. Retained separately for actionable granularity. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CLI-007 | SPEC-DEVIATION | DOC-UPDATE | yt-dlp progress hooks fire in `run_in_executor` threads (downloader.py:648). CPython's GIL makes dict assignment atomic - no data corruption in practice. The code is functionally safe; the docstrings are misleading about the execution context. Per SPEC-DEVIATION rule: code is better than docs -> reclassify as DOC-UPDATE. |
