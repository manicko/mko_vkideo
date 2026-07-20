---
name: audit-findings-01-cli
description: Phase 01 Audit Findings - Entry Point & Command Layer
agent: auditor
status: complete
validated: no
---

# Phase 01 Audit Findings — Entry Point & Command Layer

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/01-audit-cli.md
**Status:** complete
**Validated:** no

---

## Findings

### CLI-001: Unexpected batch exceptions are silently relabeled as "cancelled"

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py` (`_download_single`, `_run_batch_with_progress`) |
| **Classification** | mandatory |

**Description:**
`_download_single` catches all unexpected exceptions with a broad `except Exception:` (cli.py:166-169) and re-raises them after logging. When this happens inside the batch runner, the re-raised exception is captured by `asyncio.gather(*tasks, return_exceptions=True)` (cli.py:247) and then **coerced into a "cancelled" status** by the post-processing at cli.py:249-251:

```python
return [
    r if isinstance(r, tuple) else (urls[i], "", "cancelled") for i, r in enumerate(results)
]
```

Any non-tuple result (including a genuine `Exception`/traceback) is turned into `("...", "", "cancelled")`. The real error is only present in a log line (cli.py:168 `logger.exception(...)`); the user-facing batch summary reports it as a user-initiated cancellation. This hides real failures (e.g. unexpected `RuntimeError`, `OSError`, programming errors) and misrepresents them as intentional cancels, undermining the "Actionable error messages" dimension and complicating support/debugging.

**Evidence:**
- Source: cli.py:166-169 (broad re-raise), cli.py:247-251 (relabel to "cancelled").
- Reproduced: a task that raises `RuntimeError('boom unexpected')` inside `_download_single` yields result `('url', '', 'cancelled')` after `asyncio.gather(..., return_exceptions=True)` + the list comprehension — the exception type is lost.
- Tests: `tests/test_cli.py` has no case exercising an unexpected exception in the batch path; `test_batch_statistics_summary` only mocks `VideoNotFoundError`/`empty streams`, so the relabeling is untested.

**Recommendation:**
Distinguish cancellation from genuine failures. Either (a) let the broad `except Exception` in `_download_single` return a distinct status like `("url", "", f"error: {e}")` instead of re-raising into the gather path, or (b) in the post-processing at cli.py:249-251, check `isinstance(r, BaseException)` and map it to an `"error"` status, preserving `str(r)`. This keeps the `logger.exception` traceback while presenting an accurate, actionable status ("download_error: ...") rather than "cancelled".

---

### CLI-002: Generic `ValueError` in `download` command reports wrong "Invalid URL format" message

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py` (`download`), `src/vkdownloader/services/quality.py` (`QualitySelector.select`) |
| **Classification** | advisory |

**Description:**
The `download` command wraps `asyncio.run(_download())` in `except ValueError:` (cli.py:387-392) and prints a hard-coded message:

```python
except ValueError:
    typer.echo(
        "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}",
        err=True,
    )
```

This assumes the only `ValueError` source is URL parsing. But `QualitySelector.select()` raises `ValueError("Cannot select from empty streams list")` (quality.py:63) when `video.streams` is empty. The `download` command calls `selector.select(video.streams, quality)` directly (cli.py:348) before any stream-existence guard. A valid URL whose extraction returns zero streams therefore produces the misleading "Invalid URL format" error — wrong diagnosis for the user, who is told to fix the URL when the real problem is no available streams / extraction failure. Even the `batch` path (cli.py:154) labels this `invalid_url`, compounding the misdiagnosis.

**Evidence:**
- cli.py:348 calls `selector.select(video.streams, quality)` with no empty-stream guard.
- quality.py:62-63 raises `ValueError("Cannot select from empty streams list")`.
- cli.py:387-392 catches `ValueError` universally and prints "Invalid URL format".
- cli.py:154 labels `ValueError` as `invalid_url: {e}` in batch — same mislabeling.

**Recommendation:**
Catch `QualityNotAvailableError`/`ValueError` from `select()` explicitly and produce a correct message (e.g. "No streams found for this video; the video may be private or unavailable"). Narrow the `except ValueError` in the `download` command so it only fires for actual URL-format validation, or better: have the command verify `video.streams` is non-empty before `select()` and raise a dedicated, clearly-named error. Align the batch `invalid_url` label with the corrected semantics.

---

### CLI-003: `cli-reference.md` is binary-corrupted (trailing NUL bytes)

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/99-reference/cli-reference.md` |
| **Classification** | advisory |

**Description:**
The CLI reference documentation file contains 2 trailing NUL (`\x00`) bytes (file size 7308 bytes; NUL positions at offset 7305-7306), immediately after the "See Also" section. A markdown file with NUL bytes is not valid UTF-8 text and will fail strict readers/linters and any tooling that loads the doc as text (structlog/JSON doc pipelines, doc-lint, or future `basedpyright` doc checks). The corruption also makes the doc appear as "binary" to editors/readers, blocking normal maintenance. This violates the project guideline "Keep documentation updated continuously" and makes the entry-point contract for the CLI undocumented/reliably-unparseable.

**Evidence:**
- `Get-Content` reported `NUL count: 2`; the file read via `Read` tool returned "binary — contains NUL bytes that cannot be represented as text".
- Byte scan confirmed `data.count(b'\x00') == 2` within `docs/99-reference/cli-reference.md`; no other `docs/**/*.md` file contains NUL bytes.
- The NUL bytes sit at end-of-file right after the "See Also" links block.

**Recommendation:**
- Strip the 2 trailing NUL bytes (re-save the file as valid UTF-8 without NULs) and add a CI/doc lint guard that fails on NUL bytes in `docs/`.
- Re-verify the "See Also" links target the intended `.md` files and that the documented options (quality, method, cookie-source, ssl-verify, max-retries, output) match `cli.py` (they currently do match the live `--help` output, so only the corruption needs fixing — `[DOC-UPDATE]`, not a content deviation).

---

### CLI-004: Signal handlers register once per process but are bound to the first event loop only

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/signal_handlers.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:**
`setup_signal_handlers()` (signal_handlers.py:21-53) uses a module-global flag `_signal_handlers_setup` so handlers are registered only once per process. Each CLI command invokes it inside `asyncio.run(...)`. On POSIX, `loop.add_signal_handler` registers the handler on the *currently running loop*; after `asyncio.run` returns, that loop is closed. On a second command invocation in the same process (e.g. test session, or a future REPL/multi-invoke wrapper), the flag is already `True`, so the new loop never gets signal handlers — SIGINT/SIGTERM on the second run would no longer trigger graceful shutdown via the (now stale, closed) first loop. On Windows the fallback uses `signal.signal` (process-global, persists), masking the issue there, but the design is loop-fragile and platform-dependent. This weakens the "Graceful interruption" dimension when a process issues more than one download command.

**Evidence:**
- signal_handlers.py:15 `_signal_handlers_setup = False`; lines 24-25 early-return if already set; lines 40-49 register only on the running loop.
- cli.py:336 (`download` inner) and cli.py:194 (`_run_batch_with_progress`) both call `setup_signal_handlers()` after `asyncio.run` starts the loop.
- `get_shutdown_event()` (downloader_throttle.py:28-40) returns a `ContextVar`-scoped `asyncio.Event`; on a fresh `asyncio.run` a new event is created, but the signal handler installed on the *previous* loop still references the *previous* event — so even if a stale handler fired, it would set the wrong event.

**Recommendation:**
Re-register (or clear and re-register) signal handlers per event loop, or register them against the running loop each time the command starts and remove them on shutdown. Simplest robust fix: reset `_signal_handlers_setup = False` and remove handlers (`loop.remove_signal_handler`) at the end of the async command, so each `asyncio.run` gets a correctly-bound handler. This keeps graceful Ctrl+C behavior consistent across multiple invocations without relying on Windows-only `signal.signal` behavior.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- **CLI-001** (HIGH): Unexpected batch exceptions are relabeled as "cancelled", hiding real failures and misinforming the user. Fix the post-processing at cli.py:249-251 to distinguish genuine errors from `asyncio.CancelledError`.

## Advisory Recommendations

- **CLI-002** (MEDIUM): Narrow/`ValueError` handling in `download` so empty-stream errors are not reported as "Invalid URL format".
- **CLI-003** (MEDIUM): Strip NUL-byte corruption from `docs/99-reference/cli-reference.md` and add a doc-lint guard.
- **CLI-004** (LOW): Make signal-handler registration loop-scoped rather than process-global to preserve graceful shutdown on repeated invocations.

## Doc Updates Needed

- **CLI-003**: `docs/99-reference/cli-reference.md` — remove trailing NUL bytes; confirm links/option list still match `cli.py --help` (they do). No content/spec change required beyond de-corruption.
