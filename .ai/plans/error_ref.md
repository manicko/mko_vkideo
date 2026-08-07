# Error Message & Logging Clarity Improvement Plan

> **Project:** vkdownloader CLI (`src/vkdownloader/`)
> **Target:** English, self-describing error messages in all logs so it is immediately obvious **where** and **what** error occurred.
> **Status:** Draft — Implementation guide only (no code changes in this document)
> **Date:** 2026-08-07

---

## 1. Executive Summary

The `vkdownloader` CLI uses `structlog` for logging and a custom exception hierarchy rooted in `VKDownloadError`. Current error messages in logs and user-facing output are inconsistent: some lack origin context (which URL, which function, which phase), some use stdlib `ValueError` instead of domain exceptions, and the structlog processor chain is missing processors that would provide structured tracebacks, context-variable merging (correlation IDs), and safe Unicode handling.

This plan defines a **backward-compatible, dependency-safe** rollout across six waves:

| Wave | Focus Area | Key Outcome |
|------|-----------|-------------|
| 1 | Exception model enrichment | Every domain exception carries `error_code`, `status_label()`, `user_message`; new `InvalidVideoUrlError`; `ValueError` → domain exceptions in `extractor.py` and `quality.py` |
| 2 | Logging infrastructure | Processor chain gains `merge_contextvars`, `format_exc_info`, `UnicodeDecoder`, `utc=True` on `TimeStamper` |
| 3 | Correlation IDs + context enrichment | Per-operation UUIDs in structlog context; URL/context added to every error log site |
| 4 | Exception dispatch modernization | `ExtractionError` and `DownloadError` get explicit `status_label()`; `DownloadError` used consistently |
| 5 | Tests | All existing tests updated; new tests for enriched attributes, correlation IDs, and new exception types |
| 6 | Documentation | Exception hierarchy and logging docs updated |

The plan touches **7 source files**, **5 test files**, and introduces **1 new utility module**. No breaking API changes are introduced — all changes are additive or refactor-in-place within the internal exception hierarchy. **`_map_exception_to_status()` and `_EXCEPTION_STATUS_HANDLERS` are retained for backward compatibility.**

---

## 2. Phased Rollout

```
Wave 1 (Exceptions)  →  Wave 2 (Logging Config)  →  Wave 3 (Context Enrichment)
                                              ↘
Wave 4 (Dispatch) — depends on Wave 1
        ↓
Wave 5 (Tests) — depends on Waves 1–4
        ↓
Wave 6 (Documentation)
```

**Dependency graph:**

```
ERR-001 ──→ ERR-002 ──→ ERR-004 ──→ EXC-001
  │          │
  ▼          ▼
ERR-003 ──→ ERR-005 ──→ ERR-006
  │
  ▼
LOG-001 ──→ LOG-002 ──→ LOG-003 ──→ LOG-004 ──→ LOG-005 ──→ LOG-006 ──→ LOG-007 ──→ LOG-008 ──→ LOG-009 ──→ LOG-010
                                                              │
                                                              ▼
                                                            EXC-002 ──→ EXC-003
```

Wave 2 (LOG-001 through LOG-004) is **independent** of Wave 1 (ERR-001 through ERR-003) and can be parallelized. Wave 3 (LOG-005 onward) depends on Waves 1+2. Wave 4 depends on Wave 1. Tests depend on all prior waves.

**Rollout safety note (ERR-005 + CLI-007):** ERR-005 (replacing `ValueError` with `InvalidVideoUrlError` in `extractor.py`) and the CLI `except ValueError → except InvalidVideoUrlError` catch update (CLI-007) must be deployed as an atomic pair. Without the CLI catch update, `InvalidVideoUrlError` (subclass of `VKDownloadError`, NOT `ValueError`) would fall through to the generic `except Exception:` at line 494 in `cli.py`, producing "An error occurred during download" instead of the helpful "Invalid URL format" message. This co-deployment constraint is reflected in TST-003/TST-004 (same wave as ERR-005).

---

## 3. Task Specifications

### Wave 1 — Exception Model Enrichment

#### ERR-001: Add StrEnum for error codes
- **type:** task
- **priority:** high
- **estimated_risk:** low
- **depends_on:** []
- **files:**
  - `src/vkdownloader/exceptions.py` (create: false)
  - `src/vkdownloader/models/enums.py` (create: false)
- **actions:**
  1. Create `ErrorCode(StrEnum)` in `src/vkdownloader/models/enums.py` with members: `VIDEO_NOT_FOUND`, `INVALID_URL`, `QUALITY_NOT_AVAILABLE`, `QUALITY_PARSE_ERROR`, `EXTRACTION_ERROR`, `DOWNLOAD_ERROR`, `PATH_TRAVERSAL`, `UNEXPECTED_ERROR`.
  2. Import `ErrorCode` into `exceptions.py`.
  3. Annotate each exception class with its corresponding `ErrorCode`.
- **acceptance_criteria:**
  - `ErrorCode` is a `StrEnum` with one member per domain exception type.
  - `import ErrorCode` succeeds from `vkdowloader.models.enums`.
  - No existing code is broken by the new enum.
- **rationale:** A machine-readable `StrEnum` for error codes lets log aggregators and users filter/group by specific failure modes in structured (JSON) logs.

#### ERR-002: Add structured attributes to base exception
- **type:** task
- **priority:** high
- **estimated_risk:** low
- **depends_on:** [ERR-001]
- **files:**
  - `src/vkdownloader/exceptions.py` (create: false)
- **actions:**
  1. Add `error_code: ErrorCode` class attribute to `VKDownloadError` (default: `ErrorCode.UNEXPECTED_ERROR`).
  2. Add `status_label() -> str` instance method returning a human-readable status string (e.g., `"video_not_found"`); default implementation returns `f"error: {self.error_code.value}"`.
  3. Add `user_message() -> str` instance method returning the user-facing message (default: `str(self)`).
  4. Add a `log_context() -> dict[str, object]` method that returns a dict suitable for structlog keyword arguments (e.g., `{"error_code": ..., "message": ...}`).
   5. Update `VKDownloadError.__init__` to accept an optional `message: str | None = None` parameter (default `None`). When `message` is `None`, the exception message defaults to the class name. When a string is passed (as all existing subclasses do), behavior is unchanged. Subclasses with custom `__init__` (`QualityNotAvailableError`, `QualityParseError`) already call `super().__init__(string)` — these remain compatible because they pass a string, not `None`.
   6. Set `error_code = ErrorCode.UNEXPECTED_ERROR` as a class attribute on the base; each subclass overrides with its specific code.
   - **acceptance_criteria:**
   - `VKDownloadError` instances expose `.error_code`, `.status_label()`, `.user_message()`, `.log_context()`.
   - All existing `super().__init__(...)` calls in subclasses remain compatible (they pass a string message).
   - `VKDownloadError()` with no args defaults to class name as message (e.g., `"VKDownloadError"`).
   - `log_context()` returns at least `error_code` and `message` keys.
   - Fixed typo: "vkdowloader" → "vkdownloader".
- **rationale:** Structured attributes eliminate the need to parse exception `str()` output in logs or tests, making error identification deterministic and greppable.

#### ERR-003: Replace dict-based exception dispatch with polymorphic `status_label()`
- **type:** task
- **priority:** high
- **estimated_risk:** medium
- **depends_on:** [ERR-001, ERR-002]
- **files:**
  - `src/vkdownloader/exceptions.py` (create: false)
- **actions:**
   1. Override `status_label()` on `QualityNotAvailableError` to return `"no_streams"` when `available` is empty, else `"quality_not_available"` (matching the prefix used by the existing `_quality_not_available_status` function, without the detail suffix). Note: `_map_exception_to_status()` / `_quality_not_available_status` still produces the full string like `"no_streams: <message>"` or `"quality_not_available: requested 1440p, available: 1080, 720"` — `status_label()` returns only the prefix for use in new code paths.
  2. Override `status_label()` on `QualityParseError` to return `f"invalid_quality"`.
  3. Override `status_label()` on `VideoNotFoundError` to return `f"video_not_found"`.
  4. Override `status_label()` on `ExtractionError` to return `f"extraction_error"`.
  5. Override `status_label()` on `DownloadError` to return `f"download_error"`.
   6. **Keep `_map_exception_to_status()` backward-compatible**: it retains the existing `_EXCEPTION_STATUS_HANDLERS` dict with its format-string lambdas (which produce strings like `"no_streams: ..."`, `"quality_not_available: requested 1440p, available: 1080, 720"`, `"download_error: ..."`). Do NOT replace these lambdas with `e.status_label()` — `status_label()` returns only the status code prefix (e.g., `"no_streams"`, `"download_error"`), and the existing tests check for the full format string with colon and details. The new `status_label()` method is used in **new code** (e.g., `_download_single` refactor in EXC-003), while `_map_exception_to_status()` remains for backward compatibility.
- **acceptance_criteria:**
  - Each domain exception returns its correct `status_label()`.
  - `_map_exception_to_status()` still works for all exception types (backward compatible).
  - `_EXCEPTION_STATUS_HANDLERS` is retained with its existing format-string lambdas for backward compatibility. New call sites use `status_label()` directly; the dict is not modified in this wave.
- **rationale:** Polymorphic dispatch replaces fragile `isinstance` dict iteration with self-describing exception types, making the status label an inherent property of the exception.

#### ERR-004: Add `hide_input_in_errors=True` to Settings model config
- **type:** task
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [ERR-001]
- **files:**
  - `src/vkdownloader/config.py` (create: false)
- **actions:**
  1. Add `"hide_input_in_errors": True` to `Settings.model_config` dict.
  2. Verify `_format_validation_error()` in `cli.py` still produces `<redacted>` for received values (it already does; this is defense-in-depth).
- **acceptance_criteria:**
  - Pydantic `ValidationError` messages no longer include raw input values.
  - `_format_validation_error()` output unchanged (still shows `<redacted>`).
- **rationale:** Prevents accidental leakage of sensitive configuration values (e.g., token-bearing URLs, cookie values) into error messages that may be logged or displayed.

#### ERR-005: Replace `ValueError` in `parse_video_id` with domain exception
- **type:** task
- **priority:** high
- **estimated_risk:** medium
- **depends_on:** [ERR-001]
- **files:**
  - `src/vkdownloader/services/extractor.py` (create: false)
  - `src/vkdownloader/exceptions.py` (create: false)
- **actions:**
  1. Create `InvalidVideoUrlError(VKDownloadError)` in `exceptions.py` with `error_code = ErrorCode.INVALID_URL` and `status_label() -> "invalid_url"`. Constructor accepts `url: str` and calls `super().__init__(f"Invalid VK video URL: {_strip_auth_params(url)}")`.
  2. Import `InvalidVideoUrlError` in `extractor.py`.
  3. Replace `raise ValueError(...)` in `parse_video_id()` with `raise InvalidVideoUrlError(url)`.
  4. Update the `Raises:` docstring in `parse_video_id()`, `extract_streams()`, and `extract_streams_with_cookies()` to reference `InvalidVideoUrlError` instead of `ValueError`.
  5. **Co-deployment (CLI-007):** In `cli.py` `download()` command, replace `except ValueError:` (line 465) with `except InvalidVideoUrlError:` and import the new exception. This MUST be done in the same commit/deployment as ERR-005 steps 1–4. Without it, `InvalidVideoUrlError` falls through to the generic `except Exception:` at line 494, producing "An error occurred during download" instead of "Invalid URL format".
- **acceptance_criteria:**
  - `parse_video_id()` raises `InvalidVideoUrlError` (a subclass of `VKDownloadError`) for invalid URLs.
  - `InvalidVideoUrlError` is also catchable as `VKDownloadError`.
  - `cli.py` `download()` command catches `InvalidVideoUrlError` and still displays "Invalid URL format".
  - Docstrings updated to reflect the new exception type.
- **rationale:** Using a domain exception instead of stdlib `ValueError` makes invalid-URL failures visible in the same error-mapping and status infrastructure as all other failures, and carries structured `error_code` for log filtering.
- **co-deployment constraint:** ERR-005 and the CLI `except ValueError → except InvalidVideoUrlError` swap (CLI-007) are an atomic pair — deploy together to avoid a window where invalid URLs produce a generic error message.

#### ERR-006: Replace `ValueError` in `quality.py` with domain exception
- **type:** task
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [ERR-001]
- **files:**
  - `src/vkdownloader/services/quality.py` (create: false)
- **actions:**
  1. Replace `raise ValueError("Cannot select from empty streams list")` in `QualitySelector.select()` with `raise QualityNotAvailableError("", [], "Cannot select quality from empty streams list")`.
  2. Update the `Raises:` docstring to reference `QualityNotAvailableError` instead of `ValueError`.
- **acceptance_criteria:**
  - `QualitySelector.select()` with an empty streams list raises `QualityNotAvailableError` (which maps to `"no_streams"` via `status_label()`).
  - No `ValueError` is raised for quality selection.
- **rationale:** Consistent with ERR-005 — a domain exception is more descriptive and integrates with the structured error dispatch.

---

### Wave 2 — Logging Infrastructure

#### LOG-001: Add `merge_contextvars` as first processor
- **type:** task
- **priority:** high
- **estimated_risk:** low
- **depends_on:** []
- **files:**
  - `src/vkdownloader/config.py` (create: false)
- **actions:**
  1. Import `structlog.contextvars.merge_contextvars`.
  2. Insert `structlog.contextvars.merge_contextvars` as the first item in the `processors` list in `setup_logging()`, before `structlog.stdlib.add_log_level`.
- **acceptance_criteria:**
  - `merge_contextvars` is the first processor in the configured chain.
  - All structlog calls in all modules still produce output without error.
- **rationale:** Enables structlog to pick up context variables (correlation IDs, batch metadata) that are bound per-async-task, so every log line within an operation carries identifying context automatically.

#### LOG-002: Add `format_exc_info` processor
- **type:** task
- **priority:** high
- **estimated_risk:** low
- **depends_on:** []
- **files:**
  - `src/vkdownloader/config.py` (create: false)
- **actions:**
  1. Add `structlog.processors.format_exc_info` to the `processors` list, placed after `TimeStamper` and before the renderer.
- **acceptance_criteria:**
  - When a log call includes `exc_info=True`, the JSON log output contains a structured `exception` field with traceback frames.
  - Console renderer still shows readable tracebacks.
- **rationale:** `logger.exception(...)` calls produce traceback frames that are otherwise lost in the JSON `ConsoleRenderer`/`JSONRenderer` pipeline. `format_exc_info` converts the raw `sys.exc_info()` tuple into a structured, serializable representation.

#### LOG-003: Add `UnicodeDecoder` processor
- **type:** task
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** []
- **files:**
  - `src/vkdownloader/config.py` (create: false)
- **actions:**
  1. Add `structlog.processors.UnicodeDecoder()` to the `processors` list, placed after `format_exc_info` (or after `TimeStamper` if `format_exc_info` is absent) and before the renderer.
- **acceptance_criteria:**
  - Log entries containing non-ASCII characters (e.g., Cyrillic URLs, Unicode error messages from yt-dlp) render correctly in both JSON and Console modes.
  - No `UnicodeEncodeError` or `UnicodeDecodeError` is raised during logging.
- **rationale:** Prevents serialization failures when external libraries (yt-dlp, Playwright) emit Unicode-heavy error messages or URLs containing non-ASCII characters.

#### LOG-004: Add `utc=True` to `TimeStamper`
- **type:** task
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** []
- **files:**
  - `src/vkdownloader/config.py` (create: false)
- **actions:**
  1. Change `structlog.processors.TimeStamper(fmt="iso")` to `structlog.processors.TimeStamper(fmt="iso", utc=True)`.
- **acceptance_criteria:**
  - All log timestamps include an explicit UTC offset (`+00:00`).
  - Timestamps are consistent regardless of the machine's local timezone.
- **rationale:** UTC timestamps make log correlation across timezones and machines deterministic.

#### LOG-005: Add correlation ID utility module
- **type:** task
- **priority:** high
- **estimated_risk:** low
- **depends_on:** [LOG-001]
- **files:**
  - `src/vkdownloader/utils/correlation.py` (create: true)
- **actions:**
  1. Create `src/vkdownloader/utils/correlation.py` with:
     - `generate_correlation_id() -> str`: returns an 8-character hex UUID (using `uuid.uuid4().hex[:8]`).
     - `bind_correlation_id(correlation_id: str) -> None`: calls `structlog.contextvars.bind_contextvars(correlation_id=correlation_id)`.
     - `clear_correlation_id() -> None`: calls `structlog.contextvars.clear_contextvars()`.
     - `get_correlation_id() -> str | None`: reads the current context var (returns `None` if not bound).
  2. Use `structlog.contextvars.get_contextvars()` internally for the getter.
- **acceptance_criteria:**
  - `generate_correlation_id()` returns a unique 8-char hex string.
  - `bind_correlation_id()` makes the ID available in all subsequent structlog log entries within the same async context.
  - `clear_correlation_id()` removes the ID from context.
- **rationale:** A dedicated utility module keeps correlation-ID logic isolated (single responsibility) and reusable across CLI, extractor, downloader, and batch flows.

---

### Wave 3 — Context Enrichment at Call Sites

#### LOG-006: Add per-operation correlation IDs to single and batch downloads
- **type:** task
- **priority:** high
- **estimated_risk:** medium
- **depends_on:** [LOG-005, ERR-001]
- **files:**
  - `src/vkdownloader/cli.py` (create: false)
- **actions:**
  1. In `_download_single()`, generate a correlation ID via `generate_correlation_id()` and bind it with `bind_correlation_id()` at the top of the `try` block.
  2. In the `finally` (or end of the `try`/`except`), call `clear_correlation_id()`.
  3. Add `correlation_id` as the first structured field in the `logger.exception("unexpected_error_in_batch_download", ...)` call (line 241).
  4. For batch downloads, also bind a batch-level correlation ID in `_run_batch_with_progress()` before creating tasks, so the batch orchestrator context carries it.
  5. Ensure `clear_correlation_id()` is called in the `finally` block of `_run_batch_with_progress()`.
- **acceptance_criteria:**
  - Every log entry within a `_download_single()` call includes `correlation_id`.
  - Each URL in a batch gets its own correlation ID (visible in per-URL log entries).
  - Batch-level orchestration logs carry a separate `batch_correlation_id`.
  - No correlation ID leaks between operations.
- **rationale:** A correlation ID lets users trace all log entries belonging to a single download operation across the extraction → quality selection → download pipeline, even in concurrent batch mode.

#### LOG-007: Enrich `download_failed` and `batch_download_failed` boundary handlers with URL
- **type:** task
- **priority:** high
- **estimated_risk:** low
- **depends_on:** [LOG-006]
- **files:**
  - `src/vkdownloader/cli.py` (create: false)
- **actions:**
  1. In `download()` command (line 495): change `logger.exception("download_failed")` to `logger.exception("download_failed", url=_strip_auth_params(url))`.
  2. In `batch_download()` command (line 594): change `logger.exception("batch_download_failed")` to `logger.exception("batch_download_failed", url_file=str(urls_file), url_count=len(valid_urls))`.
- **acceptance_criteria:**
  - `download_failed` log includes the sanitized URL.
  - `batch_download_failed` log includes the URL file path and count of URLs attempted.
- **rationale:** The boundary handlers currently log only the event name with no context, making it impossible to know which URL or batch caused the failure. Adding URL/file context makes the log immediately actionable.

#### LOG-008: Enrich `perform_download` log calls with URL and context
- **type:** task
- **priority:** high
- **estimated_risk:** low
- **depends_on:** [LOG-005, LOG-006]
- **files:**
  - `src/vkdownloader/services/downloader.py` (create: false)
- **actions:**
  1. Locate all `logger.error(...)` and `logger.warning(...)` calls in `downloader.py` (15 error+warning sites identified via grep; 29 total logger calls).
  2. For each call, add `url=_strip_auth_params(<video_url>)` where a video URL variable is in scope.
  3. For calls that lack a URL variable in scope, add a `context="perform_download"` or `phase="download"` field to indicate where in the pipeline the log originated.
  4. Specific targets (verified line numbers from current source):
     - `logger.error("max_retries_exceeded")` (line 524) → add `url`, `retries=settings.max_retries`.
     - `logger.error("download_failed", error=str(e))` (line 694) → add `url=_strip_auth_params(video_url)`.
     - `logger.info("yt_dlp_download_cancelled")` (line 687) → add `url=_strip_auth_params(video_url)` (existing info-level, no timeout handler exists).
     - `logger.error("no_streams_found", ...)` (line 808) → already has URL, add `error_code="no_streams"`.
     - `logger.error("unknown_download_method", ...)` (line 907) → add `url`, `method`.
     - `logger.error("ffmpeg_download_failed", ...)` (line 432) → add `url=_strip_auth_params(m3u8_url)`.
     - `logger.error("requested_quality_not_available_in_browser_streams", ...)` (line 588) → add `url`.
     - `logger.error("invalid_quality_for_browser_streams", error=str(e))` (line 614) → add `url`.
     - `logger.warning("failed_to_refresh_token", ...)` (line 612) → add `url`.
     - `logger.warning("download_interrupted_switching_to_segments", ...)` (line 561) → add `url`.
     - `logger.warning("ssl_verify_ignored_for_ffmpeg", ...)` (line 838) → already has URL, verify.
  5. For `logger.error("download_failed")` at line 694 — use `exc_info=True` so the traceback is captured in the structured `exception` field.
  6. Note: `logger.warning("ffmpeg_cancel_not_clean", ...)` appears at lines 386, 397, 427, 444 — these lack URL context (no URL variable in scope in the ffmpeg process-monitoring closure). Add `phase="ffmpeg_cleanup"` as a context field.
  - **acceptance_criteria:**
  - Every `logger.error` and `logger.warning` in `downloader.py` that has a URL in scope includes `url=_strip_auth_params(...)`.
  - All `logger.exception(...)` or `logger.error(..., exc_info=True)` calls produce structured tracebacks.
  - Log event names are descriptive English strings prefixed with the module area (e.g., `max_retries_exceeded`, `download_failed`, `no_streams_found`).
  - Removed reference to non-existent `download_timeout_exceeded` handler; line 687 is `yt_dlp_download_cancelled` (info-level, no timeout handler in current code).
  - **Line number correction verified:** downloader.py is 987 lines (not 992); all references use current line numbers.
  - **Event name correction:** line 588 is `requested_quality_not_available_in_browser_streams` (not `invalid_quality_for_browser_streams`); line 614 is `invalid_quality_for_browser_streams`.
  - **Logger call count corrected:** 15 error+warning sites (not 27); 29 total logger calls.
- **rationale:** Knowing *where* in the download pipeline (extraction, quality selection, yt-dlp, ffmpeg, segment download) the error occurred, plus which URL, makes logs immediately diagnosable.

#### LOG-009: Enrich `extractor.py` log calls with URL and phase context
- **type:** task
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [LOG-005, LOG-006]
- **files:**
  - `src/vkdownloader/services/extractor.py` (create: false)
- **actions:**
  1. `logger.warning("ytdlp_extraction_error", error=str(e))` (line 185) → add `url=_strip_auth_params(url)`.
  2. `raise ExtractionError(f"Failed to extract video data: {e}") from e` (line 186) → include `url` in the error message: `f"Extraction failed for {_strip_auth_params(url)}: {e}"`.
  3. `raise ExtractionError(f"Failed to navigate to video page: ...")` (line 212) → include `url` in message.
  4. `raise ExtractionError(f"No video info extracted for video: ...")` (line 155) → already has URL, keep as is.
  5. `raise VideoNotFoundError(f"No streams found for video: ...")` (lines 88, 125, 133) → already has URL, keep.
  6. `raise InvalidVideoUrlError(url)` (line 56, after ERR-005) → message already includes sanitized URL.
  7. `logger.debug("video_player_click_failed", exc_info=True)` (line 278) → already has `exc_info=True`; add `url=_strip_auth_params(url)` if in scope (note: this is in `_simulate_video_interaction` which doesn't receive URL — add `phase="video_interaction"` instead).
- **acceptance_criteria:**
  - Every `ExtractionError`, `VideoNotFoundError`, `InvalidVideoUrlError` raised in `extractor.py` includes the sanitized URL in its message.
  - `logger.warning("ytdlp_extraction_error", ...)` includes `url`.
  - Error messages clearly state what operation failed and for which URL.
- **rationale:** Extraction errors are the most common failure point. Including the URL and phase in both the exception message and structured log fields makes it immediately clear which video failed and why.

#### LOG-010: Enrich `security.py` error messages with context
- **type:** task
- **priority:** low
- **estimated_risk:** low
- **depends_on:** [ERR-001]
- **files:**
  - `src/vkdownloader/utils/security.py` (create: false)
- **actions:**
   1. `raise DownloadError(f"Path traversal detected in output path: {path}")` (line 46) → set `error_code = ErrorCode.PATH_TRAVERSAL` on the instance before raising:
      ```python
      exc = DownloadError(f"Path traversal detected in output path: {path}")
      exc.error_code = ErrorCode.PATH_TRAVERSAL
      raise exc
      ```
      This works because `error_code` is a class attribute on `VKDownloadError` (default `UNEXPECTED_ERROR`) that `DownloadError` overrides with `DOWNLOAD_ERROR`, and individual instances can override further.
  2. `logger.warning("output_path_inside_repository", ...)` (line 56) → already has `path` and `repo_root`; add `error_code="output_path_in_repo"` for structured filtering.
- **acceptance_criteria:**
  - `DownloadError` raised in `security.py` has `error_code = ErrorCode.PATH_TRAVERSAL`.
  - Warning log includes path context.
- **rationale:** Path traversal is a security-relevant error that should be identifiable by `error_code` in logs.

---

### Wave 4 — Exception Dispatch Modernization

#### EXC-001: Add `ExtractionError` to status label mapping
- **type:** task
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [ERR-003]
- **files:**
  - `src/vkdownloader/exceptions.py` (create: false)
  - `src/vkdownloader/cli.py` (create: false)
- **actions:**
  1. Ensure `ExtractionError.status_label()` returns `"extraction_error"` (added in ERR-003).
  2. In `_download_single()` in `cli.py`, add explicit `except ExtractionError as e:` clause (before the generic `VKDownloadError` clause) that logs the error with context and returns the status tuple.
   3. In the `_EXCEPTION_STATUS_HANDLERS` dict, add `ExtractionError: lambda e: f"extraction_error: {e}"` (matching the existing format-string pattern of other lambdas).
- **acceptance_criteria:**
  - `ExtractionError` produces status `"extraction_error"` in `_map_exception_to_status()`.
  - `ExtractionError` is caught separately from `VKDownloadError` in `_download_single()` so it can be logged with extraction-specific context.
- **rationale:** `ExtractionError` is currently falling through to the generic `VKDownloadError` handler, producing `"download_error: ..."` in batch status — it should produce `"extraction_error: ..."` to distinguish extraction failures from downstream download failures.

#### EXC-002: Make `DownloadError` consistently used for download-phase failures
- **type:** task
- **priority:** medium
- **estimated_risk:** medium
- **depends_on:** [ERR-003, LOG-008]
- **files:**
  - `src/vkdownloader/services/downloader.py` (create: false)
  - `src/vkdownloader/exceptions.py` (create: false)
- **actions:**
  1. Identify `RuntimeError("Download cancelled")` raises in `downloader.py` (lines 237, 659, 670) — these are control-flow exceptions, not user-facing errors; leave them as `RuntimeError` (they are caught as `asyncio.CancelledError`-like signals).
   2. In `perform_download()` (line 808), when `if not streams:` and `logger.error("no_streams_found", ...)`: change to `raise QualityNotAvailableError(...)` instead of returning `None`. This ensures empty streams after extraction produce a domain exception with `error_code` and `status_label()` rather than a `None` return. Verify that all callers of `perform_download()` handle this exception (the caller is `download_video()` at line 980, which passes the result to `_download_single()` in `cli.py` — `QualityNotAvailableError` is a subclass of `VKDownloadError` and is already caught).
   3. Add `DownloadError` to `_EXCEPTION_STATUS_HANDLERS` with `lambda e: f"download_error: {e}"` (matching the existing `VKDownloadError` lambda).
  4. Ensure `DownloadError.status_label()` returns `"download_error"` (from ERR-003).
- **acceptance_criteria:**
  - `DownloadError` is raised in at least one download-phase location (downloader.py or security.py).
  - `_EXCEPTION_STATUS_HANDLERS` includes `DownloadError`.
  - `DownloadError.status_label()` returns `"download_error"`.
- **rationale:** `DownloadError` is defined but only raised in `security.py` for path traversal. It should also represent download-phase failures (timeout, yt-dlp failure, ffmpeg failure) for richer status reporting in batch mode.

#### EXC-003: Use `status_label()` in `_download_single` and `_run_batch_with_progress`
- **type:** task
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [EXC-001, ERR-003]
- **files:**
  - `src/vkdownloader/cli.py` (create: false)
- **actions:**
  1. In `_download_single()`, replace `_map_exception_to_status(e)` calls with `e.status_label()` for domain exceptions (VKDownloadError subclasses). Keep `_map_exception_to_status(e)` for non-domain exceptions (e.g., `RuntimeError`, `OSError`).
  2. In `_run_batch_with_progress()`, replace the `f"download_error: {str(r)}"` fallback for unexpected exceptions (line 326) with `f"unexpected_error: {type(r).__name__}"` — matching the existing `_map_exception_to_status` fallback format.
- **acceptance_criteria:**
  - Domain exceptions in `_download_single()` use polymorphic `status_label()`.
  - Non-domain exceptions in `_download_single()` fall back to `_map_exception_to_status()`.
  - `_run_batch_with_progress()` produces consistent status strings.
- **rationale:** Using `status_label()` directly on domain exceptions is the intended pattern after ERR-003; the dict dispatch is retained only for non-domain fallbacks.

---

### Wave 5 — Test Updates

#### TST-001: Update `test_exceptions.py` for polymorphic `status_label()`
- **type:** test
- **priority:** high
- **estimated_risk:** low
- **depends_on:** [ERR-002, ERR-003, EXC-001, EXC-003]
- **files:**
  - `tests/test_exceptions.py` (create: false)
- **actions:**
  1. Add tests verifying `error_code` attribute on each exception class.
  2. Add tests verifying `status_label()` returns correct values for each exception type.
  3. Add tests verifying `user_message()` returns the exception string.
  4. Add tests verifying `log_context()` returns a dict with `error_code` and `message` keys.
  5. Add test for `InvalidVideoUrlError` (new exception).
  6. Add test for `ExtractionError.status_label()` → `"extraction_error"`.
  7. Add test for `DownloadError.status_label()` → `"download_error"`.
  8. Keep all existing `_map_exception_to_status` tests passing (backward compatibility — the function still works).
- **acceptance_criteria:**
  - All new attribute/method tests pass.
  - All existing `_map_exception_to_status` tests still pass.
- **rationale:** Tests must verify the new structured attributes while preserving backward compatibility of `_map_exception_to_status()`.

#### TST-002: Update `test_config.py` for `hide_input_in_errors`
- **type:** test
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [ERR-004]
- **files:**
  - `tests/test_config.py` (create: false)
- **actions:**
  1. Add a test that constructs `Settings` with an invalid field value and asserts that the `ValidationError` output does NOT contain the raw input value (only `<redacted>` or no input at all).
  2. Verify that `model_config["hide_input_in_errors"]` is `True`.
- **acceptance_criteria:**
  - `hide_input_in_errors` is `True` in `Settings.model_config`.
  - Validation errors no longer leak input values.
- **rationale:** Verifies the defense-in-depth measure against input value leakage in error messages.

#### TST-003: Update `test_extractor.py` for `InvalidVideoUrlError`
- **type:** test
- **priority:** high
- **estimated_risk:** low
- **depends_on:** [ERR-005]
- **files:**
  - `tests/test_extractor.py` (create: false)
- **actions:**
  1. Update `test_parse_video_id_invalid` (line 42): change `pytest.raises(ValueError, match="Invalid VK video URL")` to `pytest.raises(InvalidVideoUrlError, match="Invalid VK video URL")`.
  2. Update `test_parse_video_id_empty_string` (line 51): same change.
  3. Update `test_extract_streams_with_cookies_invalid_url` (line 292): change both `pytest.raises(ValueError, match="Invalid VK video URL")` to `pytest.raises(InvalidVideoUrlError, match="Invalid VK video URL")`.
  4. Import `InvalidVideoUrlError` at the top of `test_extractor.py`.
- **acceptance_criteria:**
  - `parse_video_id()` with invalid URL raises `InvalidVideoUrlError`.
  - `InvalidVideoUrlError` is a subclass of `VKDownloadError` (catchable as both).
  - All three updated tests pass with `InvalidVideoUrlError`.
- **rationale:** Tests must reflect the domain-exception replacement for `ValueError`.
- **note:** The CLI catch update (`except ValueError → except InvalidVideoUrlError`) is part of ERR-005's co-deployment constraint (action step 5), not a separate test task. TST-003's `test_cli.py` action was removed from this task — the CLI catch test is verified by the existing `test_download_invalid_url` test (line 63) which remains valid because ERR-005 step 5 updates the CLI catch simultaneously.

#### TST-004: Update `test_cli.py` for `InvalidVideoUrlError` catch (co-deploy with ERR-005)
- **type:** test
- **priority:** high
- **estimated_risk:** low
- **depends_on:** [ERR-005]
- **files:**
  - `tests/test_cli.py` (create: false)
- **actions:**
  1. Verify `test_download_invalid_url` (line 63) still passes after ERR-005 step 5 updates the CLI `except ValueError:` to `except InvalidVideoUrlError:`. No code change needed — the test already asserts `"Invalid URL format"` appears in output and `exit_code == 1`.
  2. Add a new assertion to `test_download_invalid_url` verifying that `InvalidVideoUrlError` (not a bare `ValueError`) is the exception type that triggers the "Invalid URL format" message — assert that no traceback is shown (`"Traceback" not in result.output`).
- **acceptance_criteria:**
  - `test_download_invalid_url` passes with "Invalid URL format" message and exit code 1.
  - No `Traceback` in output for invalid URL.
  - CLI catches `InvalidVideoUrlError` explicitly (not via `except ValueError` or `except Exception`).
- **rationale:** Verifies the co-deployment of ERR-005 (exception change) and the CLI catch update (ERR-005 step 5) produces correct user-facing behavior.

#### TST-005: Add tests for correlation ID logging
- **type:** test
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [LOG-005, LOG-006]
- **files:**
  - `tests/test_correlation.py` (create: true)
  - `tests/conftest.py` (create: false)
- **actions:**
  1. Create `tests/test_correlation.py` with tests:
     - `test_generate_correlation_id_returns_hex`: verify 8-char hex string.
     - `test_bind_and_clear_correlation_id`: bind, verify `get_correlation_id()` returns it, clear, verify it returns `None`.
     - `test_correlation_id_in_log_entry`: bind a correlation ID, capture a structlog log entry, verify the entry contains `correlation_id`.
  2. Add a `structlog_capture` fixture to `conftest.py` if not already present (or use an existing pattern).
- **acceptance_criteria:**
  - `generate_correlation_id()` returns a unique 8-char hex string.
  - `bind_correlation_id()` / `clear_correlation_id()` correctly set and unset the context var.
  - Structlog entries include `correlation_id` after binding.
- **rationale:** Correlation IDs are the primary mechanism for tracing operations in logs; they must be tested.

#### TST-006: Add tests for `quality.py` ValueError → QualityNotAvailableError
- **type:** test
- **priority:** low
- **estimated_risk:** low
- **depends_on:** [ERR-006]
- **files:**
  - `tests/test_quality_selector.py` (create: false)
- **actions:**
  1. Find the existing test that triggers `QualitySelector.select()` with an empty streams list (if any).
  2. Add a test (or update existing) verifying that `select([], QualityEnum.BEST)` raises `QualityNotAvailableError`.
- **acceptance_criteria:**
  - `QualitySelector.select` with empty streams raises `QualityNotAvailableError`.
  - The exception's `status_label()` returns `"no_streams"`.
- **rationale:** Verifies the domain-exception replacement for the empty-streams case.

#### TST-007: Add tests for `ExtractionError` status mapping
- **type:** test
- **priority:** low
- **estimated_risk:** low
- **depends_on:** [EXC-001]
- **files:**
  - `tests/test_exceptions.py` (create: false)
- **actions:**
  1. Add a test verifying `_map_exception_to_status(ExtractionError("..."))` returns a string starting with `"extraction_error:"`.
  2. Add a test verifying `ExtractionError("...").status_label()` returns `"extraction_error"`.
- **acceptance_criteria:**
  - `ExtractionError` is mapped to `"extraction_error"` status.
- **rationale:** Verifies the new exception-to-status mapping for `ExtractionError`.

---

### Wave 6 — Documentation

#### DOC-001: Update exception hierarchy documentation
- **type:** doc
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [ERR-002, ERR-003, ERR-005, ERR-006, EXC-001, EXC-002]
- **files:**
  - `README.md` (create: false) — exists at repo root, update exception hierarchy section
  - `AGENTS.md` (create: false) — does NOT exist on disk; skip this target. If an architecture doc exists in `docs/`, update it.
- **actions:**
  1. Update the exception hierarchy section in `README.md` or `AGENTS.md` to list all exception types with their `error_code` and `status_label()`.
  2. Document the `InvalidVideoUrlError` and its role.
  3. Document the polymorphic `status_label()` pattern and its relationship to the legacy `_map_exception_to_status()`.
  4. Document `DownloadError` usage (now raised in both `security.py` and `downloader.py`).
- **acceptance_criteria:**
  - Exception hierarchy is documented with `error_code` mappings.
  - The `status_label()` pattern is documented.
  - `InvalidVideoUrlError` is mentioned in the error handling flow.
- **rationale:** Documentation must stay current with architectural changes (per project rule #14).

#### DOC-002: Update logging configuration documentation
- **type:** doc
- **priority:** medium
- **estimated_risk:** low
- **depends_on:** [LOG-001, LOG-002, LOG-003, LOG-004, LOG-005, LOG-006]
- **files:**
  - `README.md` (create: false) — exists at repo root, update logging section
  - `AGENTS.md` (create: false) — does NOT exist on disk; skip this target.
- **actions:**
  1. Document the structlog processor chain and the purpose of each processor.
  2. Document the correlation ID mechanism and how it appears in JSON logs.
  3. Document the `utc=True` timestamp behavior.
  4. Provide example log output (JSON and Console) showing correlation IDs and structured tracebacks.
- **acceptance_criteria:**
  - Logging configuration is documented with processor chain explanation.
  - Correlation ID usage is documented with examples.
  - Timezone behavior is documented.
- **rationale:** New logging features must be documented for future maintainers.

---

## 4. Test Strategy

### Existing Tests (must remain green)
| Test File | Tests | What must stay green |
|-----------|-------|---------------------|
| `tests/test_exceptions.py` | 9 tests for `_map_exception_to_status` | All 9 must pass unchanged — backward compatibility of the dispatch function is preserved |
| `tests/test_config.py` | 15 tests for `Settings` and `warn_unknown_env_vars` | All 15 must pass — `hide_input_in_errors` is additive |
| `tests/test_cli.py` | 23 tests for CLI commands | All must pass except `test_download_invalid_url` which requires co-deployment with ERR-005 step 5 |
| `tests/test_extractor.py` | 14+ tests for extraction | 3 tests require `ValueError` → `InvalidVideoUrlError` update |
| `tests/test_quality_selector.py` | Tests for quality selection | Must pass — empty-streams case changes exception type |

### New Tests to Add
| Test File | New Tests | Rationale |
|-----------|----------|-----------|
| `tests/test_exceptions.py` | 4–6 tests for `error_code`, `status_label()`, `user_message()`, `log_context()`, `InvalidVideoUrlError` | Verify structured attributes |
| `tests/test_config.py` | 1–2 tests for `hide_input_in_errors` | Verify no input value leakage |
| `tests/test_correlation.py` | 3 tests for `generate_correlation_id`, `bind`/`clear`, log integration | Verify correlation ID infrastructure |
| `tests/test_cli.py` | 1–2 tests for correlation ID in batch logs | Verify end-to-end correlation |

### Test Execution Commands
```bash
# Run all tests
uv run pytest tests/

# Run specific test files
uv run pytest tests/test_exceptions.py tests/test_config.py tests/test_cli.py tests/test_extractor.py tests/test_correlation.py

# Lint
uv run ruff check src/vkdownloader/ tests/

# Format check
uv run ruff format --check src/vkdownloader/ tests/

# Type check
uv run mypy src/vkdownloader/
```

### Risk Mitigation for Tests
- `_map_exception_to_status()` is preserved as a thin wrapper — existing tests do not break.
- CLI `except ValueError:` is replaced with `except InvalidVideoUrlError:` — `InvalidVideoUrlError` inherits from `VKDownloadError`, not `ValueError`, so the catch must be explicit. The `test_download_invalid_url` test is updated in TST-003/TST-004.
- All structlog processor additions are additive — existing log output format is unchanged for Console mode (only enhanced with correlation IDs and structured tracebacks).

---

## 5. Backward Compatibility

### Guaranteed Non-Breaking
| Change | Why it's safe |
|--------|--------------|
| `hide_input_in_errors=True` on Settings | Additive Pydantic config; only hides values in error messages, does not change validation logic |
| New `ErrorCode` StrEnum | New symbol; no existing code references it |
| `error_code`, `status_label()`, `user_message()`, `log_context()` on base exception | Additive instance/class attributes; `Exception.__init__` signature is extended with optional `message=None` |
| `merge_contextvars`, `format_exc_info`, `UnicodeDecoder` processors | Additive processors in structlog chain; only add fields, never remove existing ones |
| `utc=True` on `TimeStamper` | Changes timezone representation, not availability of timestamp |
| Correlation ID utility module | New module; no existing imports |
| `_map_exception_to_status()` retained as wrapper | All existing callers and tests continue to work |

### Breaking Changes (Intentional, Scoped)
| Change | Impact | Migration Path |
|--------|--------|---------------|
| `ValueError` → `InvalidVideoUrlError` in `parse_video_id()` | Code that catches `ValueError` for URL parsing (specifically `cli.py` line 465) must be updated to catch `InvalidVideoUrlError` | ERR-005 + CLI-007 (TST-003/TST-004) updates the single CLI catch site |
| `ValueError` → `QualityNotAvailableError` in `quality.py` | Code that catches `ValueError` from `QualitySelector.select()` with empty streams must update | Only called internally in `downloader.py` within the `download_video()` flow (post-extraction, after `if not video.streams` guard) — no external callers affected |

### What Is NOT Changed
- Public CLI command signatures (`download`, `batch`) — unchanged.
- `--quality`, `--method`, `--cookie-source`, `--ssl-verify` options — unchanged.
- Exit codes — unchanged (exit 1 for errors, 130 for cancellation).
- User-facing `typer.echo()` messages — unchanged in content (except the `except ValueError → except InvalidVideoUrlError` swap, which preserves the same message).
- The `_EXCEPTION_STATUS_HANDLERS` dict — retained for backward compatibility, new entries added.

---

## 6. Appendix — Reference Code Templates

### A. Enhanced Exception Base Class
```python
# src/vkdownloader/exceptions.py (Wave 1)
from collections.abc import Callable

from vkdownloader.models.enums import ErrorCode


class VKDownloadError(Exception):
    """Base exception for all VK Video Downloader errors.

    Attributes:
        error_code: Stable machine-readable code for log filtering.
        Subclasses set this to their specific ErrorCode; the base
        defaults to ErrorCode.UNEXPECTED_ERROR.
    """

    error_code: ErrorCode = ErrorCode.UNEXPECTED_ERROR

    def __init__(self, message: str | None = None) -> None:
        """Initialize with an optional message.

        When ``message`` is ``None``, defaults to the class name
        (e.g., ``"VideoNotFoundError"``). Subclasses with custom
        ``__init__`` signatures (e.g., ``QualityNotAvailableError``)
        pass a string to ``super().__init__`` and remain compatible.
        """
        if message is not None:
            super().__init__(message)
        else:
            super().__init__(self.__class__.__name__)

    def status_label(self) -> str:
        """Return a short, machine-readable status label for batch results.

        Format: ``"error: <error_code_value>"`` — e.g., ``"error: UNEXPECTED_ERROR"``.
        Subclasses override to return codes like ``"no_streams"``, ``"video_not_found"``, etc.
        """
        return f"error: {self.error_code.value}"

    def user_message(self) -> str:
        """Return a human-readable message for end users."""
        return str(self)

    def log_context(self) -> dict[str, object]:
        """Return a dict of structured fields for structlog."""
        return {
            "error_code": self.error_code.value,
            "message": str(self),
        }
```

### B. New `InvalidVideoUrlError` Exception
```python
# src/vkdownloader/exceptions.py (Wave 1)
from vkdownloader.utils.url_sanitizer import _strip_auth_params


class InvalidVideoUrlError(VKDownloadError):
    """Raised when a URL does not match the VK video URL pattern."""

    error_code = ErrorCode.INVALID_URL

    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Invalid VK video URL: {_strip_auth_params(url)}")

    def status_label(self) -> str:
        return "invalid_url"
```

> **Note:** `_strip_auth_params` is in `vkdownloader.utils.url_sanitizer`. Importing it in `exceptions.py` creates a dependency from `exceptions` → `utils`. This is acceptable because `url_sanitizer` does not import from `exceptions`. Verify no circular import: `utils/url_sanitizer.py` imports only from `urllib.parse`, so no cycle exists.

### C. Updated Structlog Processor Chain
```python
# src/vkdownloader/config.py (Wave 2)
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,          # 1. Correlation IDs
        structlog.stdlib.add_log_level,                      # 2. log level
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # 3. UTC timestamp
        structlog.processors.format_exc_info,               # 4. Structured tracebacks
        structlog.processors.UnicodeDecoder(),              # 5. Unicode safety
        structlog.processors.JSONRenderer()
        if settings.log_file
        else structlog.dev.ConsoleRenderer(),               # 6. Output
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### D. Correlation ID Utility Module
```python
# src/vkdownloader/utils/correlation.py (Wave 2)
import uuid

import structlog.contextvars


def generate_correlation_id() -> str:
    """Generate a short 8-char hex correlation ID."""
    return uuid.uuid4().hex[:8]


def bind_correlation_id(correlation_id: str) -> None:
    """Bind a correlation ID to the structlog context."""
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_correlation_id() -> None:
    """Clear all context variables from structlog context."""
    structlog.contextvars.clear_contextvars()


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context, or None."""
    vars = structlog.contextvars.get_contextvars()
    return vars.get("correlation_id")  # type: ignore[no-any-return]
```

### E. Correlation ID in `_download_single`
```python
# src/vkdownloader/cli.py (Wave 3)
from vkdownloader.utils.correlation import (
    bind_correlation_id,
    clear_correlation_id,
    generate_correlation_id,
)


async def _download_single(url, quality, output, method, settings, ...):
    correlation_id = generate_correlation_id()
    bind_correlation_id(correlation_id)
    try:
        # ... existing download logic ...
    except QualityNotAvailableError as e:
        logger.error("quality_not_available", url=_strip_auth_params(url), **e.log_context())
        return (url, "", e.status_label())
    except VideoNotFoundError as e:
        logger.error("video_not_found", url=_strip_auth_params(url), **e.log_context())
        return (url, "", e.status_label())
    except ExtractionError as e:
        logger.error("extraction_error", url=_strip_auth_params(url), **e.log_context())
        return (url, "", e.status_label())
    except VKDownloadError as e:
        logger.error("download_error", url=_strip_auth_params(url), **e.log_context())
        return (url, "", e.status_label())
    except Exception as e:
        logger.exception("unexpected_error_in_batch_download", url=_strip_auth_params(url))
        return (url, "", _map_exception_to_status(e))
    finally:
        clear_correlation_id()
```

### F. Enriched Boundary Handler in `download()`
```python
# src/vkdownloader/cli.py (Wave 3)
except Exception:
    logger.exception("download_failed", url=_strip_auth_params(url))
    typer.echo("An error occurred during download", err=True)
    raise typer.Exit(code=1) from None
```

### G. Updated `_EXCEPTION_STATUS_HANDLERS` (Backward-Compatible — New Entries Added, Existing Preserved)
```python
# src/vkdownloader/exceptions.py (Wave 4)
# NOTE: This dict is retained for backward compatibility. Existing lambdas
# preserve their original format-string output (e.g., "download_error: <msg>").
# New entries for ExtractionError and DownloadError follow the same pattern.
# status_label() is used in NEW code paths (e.g., _download_single), not here.
_EXCEPTION_STATUS_HANDLERS: dict[type[Exception], Callable[..., str]] = {
    QualityNotAvailableError: _quality_not_available_status,  # unchanged
    QualityParseError: lambda e: f"invalid_quality: {e.quality}",          # unchanged
    VideoNotFoundError: lambda e: f"video_not_found: {e}",                # unchanged
    ExtractionError: lambda e: f"extraction_error: {e}",                  # NEW
    DownloadError: lambda e: f"download_error: {e}",                       # NEW
    VKDownloadError: lambda e: f"download_error: {e}",                     # unchanged
}
```

### H. Settings Model Config
```python
# src/vkdownloader/config.py (Wave 1/2)
model_config = {
    "env_file": ".env",
    "env_file_encoding": "utf-8",
    "extra": "forbid",
    "env_prefix": "VKDOWNLOADER_",
    "hide_input_in_errors": True,
}
```

### I. Example JSON Log Output (after Wave 2+3)
```json
{"timestamp": "2026-08-07T09:24:29+00:00", "level": "error", "event": "video_not_found", "url": "https://vkvideo.ru/***REDACTED***", "correlation_id": "a1b2c3d4", "error_code": "video_not_found", "message": "No streams found for video: https://vkvideo.ru/***REDACTED***"}
```

---

## 7. Execution Ordering

### Wave 1 (parallelizable)
1. **ERR-001** — `ErrorCode` StrEnum in `models/enums.py`
2. **ERR-004** — `hide_input_in_errors` in `config.py` (independent)
3. **ERR-002** — Structured attributes on `VKDownloadError` (depends on ERR-001)
4. **ERR-005** — `InvalidVideoUrlError` + `ValueError` replacement in `extractor.py` + CLI catch update in `cli.py` (depends on ERR-001; **co-deployment with CLI catch is mandatory**)
5. **ERR-006** — `ValueError` replacement in `quality.py` (depends on ERR-001)

### Wave 2 (parallelizable with Wave 1)
1. **LOG-001** — `merge_contextvars` processor
2. **LOG-002** — `format_exc_info` processor
3. **LOG-003** — `UnicodeDecoder` processor
4. **LOG-004** — `utc=True` on TimeStamper
5. **LOG-005** — Correlation ID utility module

### Wave 3 (depends on Waves 1 + 2)
1. **LOG-006** — Correlation IDs in `_download_single` and batch
2. **LOG-007** — Enrich boundary handlers with URL
3. **LOG-008** — Enrich `downloader.py` log calls
4. **LOG-009** — Enrich `extractor.py` log calls
5. **LOG-010** — Enrich `security.py` log calls

### Wave 4 (depends on Wave 1)
1. **EXC-001** — `ExtractionError` status mapping + explicit catch in `_download_single`
2. **EXC-002** — `DownloadError` consistent usage
3. **EXC-003** — Use `status_label()` in dispatch points

### Wave 5 (depends on Waves 1–4)
1. **TST-001** — Update `test_exceptions.py`
2. **TST-002** — Update `test_config.py`
3. **TST-003** — Update `test_extractor.py`
4. **TST-004** — Update `test_cli.py` (co-deploy with ERR-005)
5. **TST-005** — New `test_correlation.py`
6. **TST-006** — Update `test_quality_selector.py`
7. **TST-007** — Add `ExtractionError` status tests

### Wave 6 (final)
1. **DOC-001** — Exception hierarchy docs
2. **DOC-002** — Logging configuration docs

---

## 8. Files Touched Summary

| File | Type | Changes |
|------|------|---------|
| `src/vkdownloader/exceptions.py` | modify | ERR-002, ERR-003, ERR-005 (InvalidVideoUrlError), EXC-001, EXC-002 |
| `src/vkdownloader/models/enums.py` | modify | ERR-001 (new `ErrorCode` enum) |
| `src/vkdownloader/config.py` | modify | ERR-004, LOG-001, LOG-002, LOG-003, LOG-004 |
| `src/vkdownloader/cli.py` | modify | ERR-005 (CLI catch update, co-deployed), LOG-006, LOG-007, EXC-001, EXC-003 |
| `src/vkdownloader/services/extractor.py` | modify | ERR-005, LOG-009 |
| `src/vkdownloader/services/downloader.py` | modify | LOG-008, EXC-002 |
| `src/vkdownloader/services/quality.py` | modify | ERR-006 |
| `src/vkdownloader/utils/security.py` | modify | LOG-010 |
| `src/vkdownloader/utils/correlation.py` | create | LOG-005, LOG-006 |
| `tests/test_exceptions.py` | modify | TST-001, TST-007 |
| `tests/test_config.py` | modify | TST-002 |
| `tests/test_extractor.py` | modify | TST-003 |
| `tests/test_cli.py` | modify | TST-004 |
| `tests/test_quality_selector.py` | modify | TST-006 |
| `tests/test_correlation.py` | create | TST-005 |
| `tests/conftest.py` | modify | TST-005 (add structlog capture fixture if needed) |
| `README.md` | modify | DOC-001, DOC-002 (exists at repo root) |

---

## 9. Risk Assessment

| Task ID | Risk | Mitigation |
|---------|------|------------|
| ERR-005 | **medium** | Replaces `ValueError` with `InvalidVideoUrlError`. Only one CLI catch site (line 465) and 3 tests affected. Coordinated with TST-003/TST-004. |
| LOG-006 | **medium** | Contextvar binding in async tasks. `structlog.contextvars` is designed for asyncio; context is per-task. `finally` block ensures cleanup. |
| EXC-002 | **medium** | Changes `perform_download()` to raise instead of return `None` for empty streams. Must verify all callers handle the exception (the `download_video()` flow wraps `perform_download` and `ExtractionError`/`VKDownloadError` is caught upstream in `_download_single`). |
| ERR-003 | **low** | `_map_exception_to_status` retained as wrapper. Existing tests pass unchanged. |
| LOG-001–003 | **low** | Additive processors. Verify structlog version ≥24.0.0 supports `merge_contextvars` (it does, since 20.x). |
| LOG-005 | **low** | New module. No circular import risk (only depends on `structlog.contextvars` and stdlib `uuid`). |
| ERR-006 | **low** | `ValueError("Cannot select from empty streams list")` → `QualityNotAvailableError`. Only reachable as defensive guard; callers already check `if not streams`. |
| TST-004 | **low** | Single `except` clause swap in CLI. Test already validates exit code and message. |
| DOC-001/DOC-002 | **low** | Documentation-only. No code risk. |

---

*End of plan. All task IDs reference the YAML blocks in Section 3. Execution order follows Section 7. This document contains implementation guidance only — no source code changes have been made.*
