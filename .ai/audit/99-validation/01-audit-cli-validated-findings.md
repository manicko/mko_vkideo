# Phase 01 Audit Findings - Entry Point & Command Layer (Validated)

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/01-audit-cli.md
**Status:** complete
**Validated:** validator
**Validated Date:** 2026-07-20

---

## Findings

### CLI-001: Unexpected batch exceptions are silently relabeled as canceled

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py (_download_single, _run_batch_with_progress) |
| **Classification** | mandatory |

**Description:**
_download_single catches all unexpected exceptions with a broad except Exception: (cli.py:166-169) and re-raises them after logging. When this happens inside the batch runner, the re-raised exception is captured by asyncio.gather(*tasks, return_exceptions=True) (cli.py:247) and then coerced into a canceled status by the post-processing at cli.py:249-251.

`python
return [
    r if isinstance(r, tuple) else (urls[i], '', 'cancelled') for i, r in enumerate(results)
]
`

Any non-tuple result (including a genuine Exception/traceback) is turned into ('...', '', 'cancelled'). The real error is only present in a log line (cli.py:168 logger.exception(...)); the user-facing batch summary reports it as a user-initiated cancellation. This hides real failures (e.g. unexpected RuntimeError, OSError, programming errors) and misrepresents them as intentional cancels, undermining the 'Actionable error messages' dimension and complicating support/debugging.

**Evidence:**
- Source: cli.py:166-169 (broad re-raise), cli.py:247-251 (relabel to canceled).
- Verified: asyncio.gather(..., return_exceptions=True) returns Exception objects as-is; the list comprehension at cli.py:249-251 does not check isinstance(r, BaseException), causing all non-tuple results to be labeled canceled.
- Tests: tests/test_cli.py has no case exercising an unexpected exception in the batch path; test_batch_statistics_summary only mocks VideoNotFoundError/empty streams, so the relabeling is untested.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The finding is technically correct. The code at cli.py:249-251 uses isinstance(r, tuple) which fails to distinguish between asyncio.CancelledError and other exceptions. When _download_single raises an exception at line 169, asyncio.gather(..., return_exceptions=True) captures it as the exception object, but the list comprehension converts it to a tuple with status canceled. This is a real SPEC-DEVIATION: the implementation violates the implicit requirement for accurate error reporting.
> - **See also:** None

**Recommendation:**
At cli.py:249-251, modify the list comprehension to check `isinstance(r, BaseException)` and map non-tuple, non-CancelledError exceptions to status `'download_error: {str(r)}'` instead of `'cancelled'`. This preserves the `logger.exception` traceback from cli.py:168 while accurately reporting genuine failures in the batch summary, distinguishing them from `asyncio.CancelledError` results.

_Investigation: asyncio.gather(..., return_exceptions=True) at cli.py:247 captures exceptions as Exception objects; the current isinstance(r, tuple) check incorrectly labels all non-tuple results as user-cancelled._

---

### CLI-002: Generic ValueError in download command reports wrong Invalid URL format message

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py (download), src/vkdownloader/services/quality.py (QualitySelector.select) |
| **Classification** | advisory |

**Description:**
The download command wraps asyncio.run(_download()) in except ValueError: (cli.py:387-392) and prints a hard-coded message:

`python
except ValueError:
    typer.echo(
        'Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}',
        err=True,
    )
`

This assumes the only ValueError source is URL parsing. But QualitySelector.select() raises ValueError('Cannot select from empty streams list') (quality.py:63) when video.streams is empty. The download command calls selector.select(video.streams, quality) directly (cli.py:348) before any stream-existence guard. A valid URL whose extraction returns zero streams therefore produces the misleading Invalid URL format error - wrong diagnosis for the user, who is told to fix the URL when the real problem is no available streams / extraction failure. Even the batch path (cli.py:154) labels this invalid_url, compounding the misdiagnosis.

**Evidence:**
- cli.py:348 calls selector.select(video.streams, quality) with no empty-stream guard (verified at lines 347-348).
- quality.py:62-63 raises ValueError('Cannot select from empty streams list') when streams list is empty.
- cli.py:387-392 catches ValueError universally and prints Invalid URL format (verified).
- cli.py:154 labels ValueError as invalid_url: {e} in batch - same mislabeling (verified).

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The finding is technically correct. The download function at cli.py:347-348 calls selector.select() after extractor.extract_streams() but without checking if video.streams is non-empty. When streams is empty, QualitySelector.select() raises ValueError('Cannot select from empty streams list'), which is caught by the broad except ValueError: handler at cli.py:387 that assumes URL parsing failures. This is a SPEC-DEVIATION: the error message is inaccurate and misleads users.
> - **See also:** None

**Recommendation:**
In cli.py:347-348 (download command), add a guard before `selector.select()` to check `if not video.streams:` and raise `QualityNotAvailableError(quality, [])` with the message 'No streams found for this video; the video may be private or unavailable'. In cli.py:114 (_download_single), add the same guard. Then narrow the broad `except ValueError` at cli.py:387-392 to only catch URL-format validation errors (catch `QualityNotAvailableError` explicitly for empty-stream cases). This replaces the generic ValueError with a dedicated domain exception that conveys accurate semantics.

_Investigation: QualitySelector.select() at quality.py:62-63 raises ValueError('Cannot select from empty streams list') when streams is empty; the CLI incorrectly assumes all ValueError instances stem from URL parsing._

---

### CLI-003: cli-reference.md is binary-corrupted (trailing NUL bytes)

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | docs/99-reference/cli-reference.md |
| **Classification** | advisory |

**Description:**
The CLI reference documentation file contains 2 trailing NUL bytes (file size 7308 bytes; NUL positions at offset 7305-7306), immediately after the See Also section. A markdown file with NUL bytes is not valid UTF-8 text and will fail strict readers/linters and any tooling that loads the doc as text (structlog/JSON doc pipelines, doc-lint, or future basedpyright doc checks). The corruption also makes the doc appear as binary to editors/readers, blocking normal maintenance. This violates the project guideline 'Keep documentation updated continuously' and makes the entry-point contract for the CLI undocumented/reliably-unparseable.

**Evidence:**
- Verified: File scan reports NUL count of 2 with file size 7308 bytes.
- No other docs markdown file contains NUL bytes (verified via scan).
- The NUL bytes sit at end-of-file right after the See Also links block.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The finding is technically correct. The file docs/99-reference/cli-reference.md has 2 trailing NUL bytes. The content otherwise matches the CLI help output (verified), so this is a file corruption issue, not a content deviation. Classification REMAINS DOC-UPDATE - the fix is to strip NUL bytes, not to change documented behavior.
> - **See also:** None

**Recommendation:**
- Strip the 2 trailing NUL bytes (re-save the file as valid UTF-8 without NULs) and add a CI/doc lint guard that fails on NUL bytes in docs/.
- Re-verify the See Also links target the intended md files and that the documented options (quality, method, cookie-source, ssl-verify, max-retries, output) match cli.py --help (they currently do match the live --help output, so only the corruption needs fixing - [DOC-UPDATE], not a content deviation).

---

### CLI-004: Signal handlers register once per process but are bound to the first event loop only

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/signal_handlers.py, src/vkdownloader/cli.py |
| **Classification** | advisory |

**Description:**
setup_signal_handlers() (signal_handlers.py:21-53) uses a module-global flag _signal_handlers_setup so handlers are registered only once per process. Each CLI command invokes it inside asyncio.run(...). On POSIX, loop.add_signal_handler registers the handler on the currently running loop; after asyncio.run returns, that loop is closed. On a second command invocation in the same process (e.g. test session, or a future REPL/multi-invoke wrapper), the flag is already True, so the new loop never gets signal handlers - SIGINT/SIGTERM on the second run would no longer trigger graceful shutdown via the (now stale, closed) first loop. On Windows the fallback uses signal.signal (process-global, persists), masking the issue there, but the design is loop-fragile and platform-dependent. This weakens the 'Graceful interruption' dimension when a process issues more than one download command.

**Evidence:**
- signal_handlers.py:15 _signal_handlers_setup = False; lines 24-25 early-return if already set; lines 40-49 register only on the running loop.
- cli.py:336 (download inner) and cli.py:194 (_run_batch_with_progress) both call setup_signal_handlers() after asyncio.run starts the loop.
- get_shutdown_event() (downloader_throttle.py:28-40) returns a ContextVar-scoped asyncio.Event; on a fresh asyncio.run a new event is created, but the signal handler installed on the previous loop still references the previous event - so even if a stale handler fired, it would set the wrong event.

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The finding is technically correct. The module-level _signal_handlers_setup flag at signal_handlers.py:15-25 prevents re-registration on subsequent calls. When asyncio.run() creates a new event loop, loop.add_signal_handler() at lines 41-49 registers handlers on that specific loop. After the loop closes, handlers are orphaned. On a second invocation in the same process, the early-return at line 24-25 skips registration, leaving the new loop without handlers. However, the ContextVar-based get_shutdown_event() at downloader_throttle.py:28-40 provides loop isolation - each asyncio.run() gets its own Event. The real issue is that signal handlers are never installed on subsequent loops.
> - **See also:** None

**Recommendation:**
Re-register (or clear and re-register) signal handlers per event loop, or register them against the running loop each time the command starts and remove them on shutdown. Simplest robust fix: reset _signal_handlers_setup = False and remove handlers (loop.remove_signal_handler) at the end of the async command, so each asyncio.run gets a correctly-bound handler. This keeps graceful Ctrl+C behavior consistent across multiple invocations without relying on Windows-only signal.signal behavior.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- **CLI-001** (HIGH): Unexpected batch exceptions are relabeled as canceled, hiding real failures and misinforming the user. Fix the post-processing at cli.py:249-251 to distinguish genuine errors from asyncio.CancelledError.

## Advisory Recommendations

- **CLI-002** (MEDIUM): Narrow ValueError handling in download so empty-stream errors are not reported as Invalid URL format.
- **CLI-003** (MEDIUM): Strip NUL-byte corruption from docs/99-reference/cli-reference.md and add a doc-lint guard.
- **CLI-004** (LOW): Make signal-handler registration loop-scoped rather than process-global to preserve graceful shutdown on repeated invocations.

## Doc Updates Needed

- **CLI-003**: docs/99-reference/cli-reference.md - remove trailing NUL bytes; confirm links/option list still match cli.py --help (they do). No content/spec change required beyond de-corruption.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | CLI-001, CLI-002, CLI-003, CLI-004 |
| Reclassified | 0 | - |
| Merged | 0 | - |
| Rejected | 0 | - |

### Rejected Findings

None

### Merged Findings

None

### Reclassified Findings

None

---

## Cross-Phase Analysis

### CFG-001 Cross-Reference (COOKIE_SOURCE.FILE silent no-op)

The CLI-002 finding partially overlaps with CFG-001 from Phase 02. CFG-001 identifies that CookieSource.FILE silently behaves like none in the primary download flow. However, CLI-002 focuses on error message accuracy, not cookie source handling. These are distinct issues with different root causes and do not merge.

### CFG-002 Cross-Reference (extra=forbid env limitation)

The CFG-002 finding identifies that Settings.model_config with extra: forbid does not protect environment variables. While this affects configuration reliability, it is not directly related to CLI-001-004 findings. No merge or conflict detected.
