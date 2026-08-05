# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification

| Step | Command | Result |
|------|---------|--------|
| R1 (linter) | `uv run ruff check src` | Pass — "All checks passed!" |
| R1 (types) | `uv run mypy src` | Pass — "Success: no issues found in 23 source files" (note: emits `unused section(s): module = ['tests.*']`, already tracked as CLI-008) |
| R1 (noqa meta) | `uv run ruff check --select RUF100 src` | 11 unused `noqa` directives (see QLT-001) |
| R2 (tests) | `uv run pytest` | 248 passed in 10.91s |
| R3 (dead code) | `ruff --select F401,F811,F841` + AST reference scan | No unused imports/variables. Re-exports in `downloader.__all__` are a documented backward-compat facade used by tests/docs — not dead code. `ExtractionError`/`DownloadError` both raised and caught. |
| R4 (secrets) | grep `password\|secret\|api_key\|token\|credential` | No hardcoded secrets. `.env` is a commented template only. |
| R4 (print) | grep `print(` in `src` | None. |
| R4 (bare except) | grep `except\s*:` in `src` | None. (broad `except Exception` present in error-handling paths; not bare.) |
| R4 (sensitive logging) | trace URL log calls | All CDN URLs routed through `_strip_auth_params`. One raw-URL outlier at `cli.py:575` already filed as SEC-002 (phase 04). |

---

## Findings

### QLT-001: Redundant `# noqa` directives in cli.py and network_monitor.py

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/infrastructure/network_monitor.py` |
| **Classification** | advisory |

**Description:** Eleven `# noqa` suppression comments are redundant under the project's own ruff configuration. Nine `# noqa: B008` comments sit on Typer `Option`/`Argument` defaults in `cli.py`, but `B008` is listed in `ignore` (`pyproject.toml:65-68`), so the rule never fires and the comments suppress nothing. Two `# noqa: BLE001` comments in `network_monitor.py` reference `BLE001`, which is **not** in the `select` list (`pyproject.toml:56-64` enables only `E,W,F,I,B,C4,UP`) — so BLE001 is not enforced at all, and the noqa provides neither suppression nor documentation value. This is config/code drift: the annotations signal intent that the active config contradicts, misleading maintainers about which rules are actually enforced.

**Evidence:**
- `uv run ruff check --select RUF100 src` → 11 errors:
  - `cli.py:387,388,394,400,513,518,522,528,534` — `# noqa: B008` (B008 in `ignore`)
  - `network_monitor.py:91,116` — `# noqa: BLE001` (BLE001 not in `select`)
- `pyproject.toml:65-68` — `ignore = ["E501", "B008"]`
- `pyproject.toml:56-64` — `select = ["E","W","F","I","B","C4","UP"]` (no `BLE`)

**Recommendation [BEST-PRACTICE]:** Remove the 11 stale `# noqa` comments. If broad-`except` (BLE001) coverage is desired, add `BLE` to `select`; if not, delete the comments so the broad `except Exception` sites are visible as intentional rather than silently unguarded. Effort: trivial. Priority: recommended.

---

### QLT-002: FFMPEG download method silently drops `progress_callback`

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`perform_download` FFMPEG branch, `HLSDownloader.download_with_ffmpeg` signature) |
| **Classification** | advisory |

**Description:** `perform_download` accepts a `progress_callback` parameter and forwards it to the yt-dlp branch (`download_with_ytdlp_with_resume_fallback`, `downloader.py:796`) and the segment-download fallback (`download_hls_with_resume` via `HLSDownloadRequest`, `downloader.py:814-822`), but **the FFMPEG method branch never passes it** to `download_with_ffmpeg` (`downloader.py:811`). `download_with_ffmpeg` declares a `progress_callback: Callable[[FfmpegProgress], None] | None` parameter and the docs (`docs/01-tools/vkdownloader-overview.md:177-197`) describe ffmpeg progress tracking, so the wiring exists at the method level but is unreachable from the orchestrator. The gap is structural, not accidental: `perform_download`'s callback type is `Callable[[str, int, int], None]` (segment-style: video_id, downloaded, total) which is **incompatible** with `download_with_ffmpeg`'s `Callable[[FfmpegProgress], None]`, so a direct forward would be a type error. Complements CLI-006 (progress not wired into the single `download` command at the CLI layer).

**Evidence:**
- `downloader.py:798-811`:
  ```python
  case DownloadMethod.FFMPEG:
      ...
      result = await downloader.download_with_ffmpeg(m3u8_url, output_file, quality, cookies)  # no progress_callback
  ```
- `downloader.py:281-288` — `download_with_ffmpeg(..., progress_callback=None)` accepts a callback type (`Callable[[FfmpegProgress], None]`) incompatible with `perform_download`'s `Callable[[str, int, int], None]` (`downloader.py:725`).
- Contrast: yt-dlp branch forwards it (`downloader.py:785-797`); AUTO branch forwards it (`downloader.py:838-850`); FFMPEG branch does not.
- `HLSDownloadRequest.progress_callback` is `Callable[[str, int, int], None]` (`models/dtos.py:24`) — the type the orchestrator actually holds.

**Recommendation [BEST-PRACTICE]:** Bridge the two progress shapes: wrap `perform_download`'s per-URL callback into a `Callable[[FfmpegProgress], None]` adapter (mapping `FfmpegProgress.total_size`/`out_time_us` → `(video_id, downloaded, total)`) and forward it to `download_with_ffmpeg`, or hoist a shared progress abstraction. At minimum, document that `--method ffmpeg` does not report per-segment progress. Effort: small. Priority: recommended.

---

### QLT-003: Stale comment promises `DownloadError` re-raise that never happens

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`) |
| **Classification** | advisory |

**Description:** The comment at `downloader.py:635` states `# Re-raise as DownloadError to distinguish from cancellation`, but `DownloadError` is not imported in this module (the import at `downloader.py:18` is `from ..exceptions import ExtractionError, QualityNotAvailableError`) and the code that follows does not raise `DownloadError` — it raises `RuntimeError("Download cancelled")` on shutdown or re-raises the original exception (`raise` / `raise ... from e`). The comment describes behavior that does not exist, misleading maintainers into believing cancellation is wrapped in a recognizable exception type that the caller can act on.

**Evidence:**
- `downloader.py:18`: `from ..exceptions import ExtractionError, QualityNotAvailableError` — `DownloadError` not imported.
- `downloader.py:634-638`:
  ```python
  except Exception as e:
      # Re-raise as DownloadError to distinguish from cancellation
      if "cancelled" in str(e).lower() or shutdown_event.is_set():
          raise RuntimeError("Download cancelled") from e
      raise
  ```
- `DownloadError` is defined at `exceptions.py:54` and raised only in `utils/security.py:44`; it is never raised in `downloader.py`.

**Recommendation [BEST-PRACTICE]:** Correct the comment to match actual behavior (re-raise original on cancellation-via-shutdown, re-raise unchanged otherwise), or implement the stated intent (wrap non-cancellation exceptions in `DownloadError` and import it). Effort: trivial. Priority: recommended.

---

### QLT-004: Public `Settings` field validators lack docstrings

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` (`expand_tilde_paths`, `normalize_log_level`) |
| **Classification** | advisory |

**Description:** Two public field-validator methods on the `Settings` model have no docstring, violating project rule 14 ("Docstrings on public APIs") and the phase 08 "docstrings on public APIs" check. The sibling validator `validate_cookie_source` (`config.py:128`) is documented, so the omission is inconsistent. Both validators encode non-obvious normalization logic (empty/tilde path expansion to `Path | None`, and case-insensitive `LogLevel` coercion) that future maintainers must reverse-engineer.

**Evidence:**
- `config.py:112-117`:
  ```python
  @field_validator("download_dir", "log_file", mode="after")
  @classmethod
  def expand_tilde_paths(cls, v: Path | None) -> Path | None:
      if v is None:
          return v
      return v.expanduser().resolve()
  ```
  (no docstring)
- `config.py:119-124`:
  ```python
  @field_validator("log_level", mode="before")
  @classmethod
  def normalize_log_level(cls, v: str | LogLevel) -> LogLevel:
      if isinstance(v, LogLevel):
          return v
      return LogLevel(v.upper())
  ```
  (no docstring)
- Contrast: `config.py:126-138` `validate_cookie_source` has a one-line docstring.

**Recommendation [BEST-PRACTICE]:** Add docstrings to `expand_tilde_paths` and `normalize_log_level` describing their normalization behavior (notably that empty-string inputs are *not* converted to `None` here — see CFG-001). Effort: trivial. Priority: recommended.

---

### QLT-005: One log call pre-formats with an f-string, defeating structured logging

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` (`_log_env_file_path`) |
| **Classification** | advisory |

**Description:** The project configures structlog with a JSON renderer for file logging and a console renderer for terminal output (`config.py:218-225`), so log events are expected to be structured (`logger.event("event_name", key=value)`). The call at `cli.py:39` instead pre-formats the value into the event string via an f-string: `logger.debug(f".env file resolved to: {env_file.resolve()}")`. With the JSON renderer this collapses the path into an opaque event string rather than a queryable `path` field, breaking the structured-log invariant the rest of the codebase follows (e.g. `cli.py:436-437`, `downloader.py:747-753`).

**Evidence:**
- `cli.py:39`: `logger.debug(f".env file resolved to: {env_file.resolve()}")`
- `cli.py:41`: `logger.debug(".env file not found; using environment variables or defaults only")` (plain event string — acceptable structlog form)
- `cli.py:436-437`: `logger.info("available_streams", count=...)` / `logger.info("available_qualities", qualities=available[:8])` (structured)
- `config.py:218-228`: structlog configured with `JSONRenderer()` / `ConsoleRenderer()`.

**Recommendation [BEST-PRACTICE]:** Convert to `logger.debug("env_file_resolved", path=str(env_file.resolve()))` to match the structured-logging convention used everywhere else. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 5 |

## Mandatory Fixes

No findings classified as mandatory in this phase — the codebase passes `ruff check`, `mypy` (strict), and the full `pytest` suite (248 passed), with no hardcoded secrets, no `print()` statements, no bare `except:` clauses, no unused imports, and no layer-separation violations (verified clean in phases 01–07). All findings in this pass are advisory quality/hygiene issues.

## Advisory Recommendations

| ID | Severity | Summary |
|----|----------|---------|
| QLT-001 | LOW | 11 stale `# noqa` directives (9x `B008` in cli.py, 2x `BLE001` in network_monitor.py) are redundant under the active ruff config — remove the comments. |
| QLT-002 | LOW | `perform_download` FFMPEG branch never forwards `progress_callback` to `download_with_ffmpeg`; callback types are incompatible. Bridge the two progress shapes. |
| QLT-003 | LOW | Stale comment at `downloader.py:635` claims to re-raise as `DownloadError`, which is not imported/used — fix comment to match code. |
| QLT-004 | LOW | `Settings.expand_tilde_paths` and `normalize_log_level` field validators lack docstrings — add them for consistency. |
| QLT-005 | LOW | `cli.py:39` pre-formats a log arg with an f-string, defeating structlog structured logging — convert to `logger.debug("env_file_resolved", path=...)`. |

## Doc Updates Needed

- (None)
