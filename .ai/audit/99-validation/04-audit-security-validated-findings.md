# Phase 04 Audit Findings — Security & Secret Management (VALIDATED)

**Phase:** 04-audit-security (Security & Secret Management)
**Source (audited):** `.ai/audit/04-audit-security/findings.md`
**Validator:** validator (evidence-driven, conservative)
**Scope:** live-session-cookie handling on disk, secret/redaction hygiene in logs and error output
**Status:** complete
**Validated:** yes

> Validator note: this file is a self-contained, verified copy of the source findings with inline
> validation decisions applied. The reader need not consult the original. Validated against the working
> tree at `C:\py_exp\mko_vkideo` on 2026-08-05 (Python 3.12.1, pydantic 2.13.4 / pydantic-settings 2.14.2,
> structlog 26.1.0). `ruff check src/vkdownloader` -> All checks passed; `pytest` -> 248 passed (9.87s).
> No source code was modified.

---

## Validation Methodology

1. **Source** — read `src/vkdownloader/services/downloader.py`, `services/cookies.py`,
   `cli.py`, `config.py`, `utils/url_sanitizer.py`, `services/downloader_throttle.py`,
   `services/extractor.py`, `models/enums.py`.
2. **Static enumeration** — grep for *every* logger-emitted URL (`logger\.\w+\(.*(url|video_url|m3u8_url|segment_url)=`)
   **and** f-string URL interpolation (`logger\.\w+\(f"...url`) to validate SEC-002's "sole outlier" scope claim.
3. **Runtime evidence** — `ruff` (pass) and `pytest` (248 passed) confirm the tree is in the audited green state;
   findings describe latent/design issues, not currently-failing behavior.
4. **Cross-phase** — compared against Phase 01 (CLI), Phase 02 (Config), Phase 03 (Services) findings
   for overlapping root causes and conflicting evidence.
5. **Docs/config** — read `.gitignore`, `config.py` (`Settings` model), confirmed `download_dir` default and `0o600`.

### Decision legend

- **[VALIDATED]** Root cause verified against current code; recommendation stands.
- **[RECLASSIFIED]** Valid issue, but `Type` adjusted per the validator taxonomy
  (`SPEC-DEVIATION` / `BEST-PRACTICE` / `DOC-UPDATE`).
- **[REJECTED]** Issue not present, stale, duplicate, low-ROI, architecture-breaking, operationally unsafe.

### Validator taxonomy note

`RUNTIME-ERROR` (Phase 02 CFG-001 / Phase 03 SRV-001) is the auditor's severity tag and falls outside the
validator's classification set. Phase 04 already uses the validator taxonomy directly (SEC-001 =
`SPEC-DEVIATION`, SEC-003 = `BEST-PRACTICE`), so no reclassification is needed here.

---

## Runtime Verification Summary

Re-confirmed against the current tree. Retained only findings-relevant items (problems_only=TRUE).

| Step | Check | Result |
|------|-------|--------|
| R1 | Hardcoded-secret scan (findings: none in repo / `.env`; fixtures fake) | No secret required by any remediation; claims consistent with audit scope. |
| R2 | Logger audit — enumerate ALL raw-URL logger emissions | **Partially inaccurate (corrected under SEC-002):** audit claims "except one outlier"; systematic grep finds TWO raw-URL logger sites (`cli.py:243`, `cli.py:575`). See SEC-002 note. |
| R3 | `.gitignore` coverage (`.env`, `*_cookies.txt`); `0o600` creation | `.gitignore:22` (`*_cookies.txt`) + `:28` (`.env`) match (verified via `git check-ignore`); `cookies.py:72` uses `os.open(..., 0o600)`. |
| R5 | `ruff check src/vkdownloader` | All checks passed! |
| R6 | `pytest` | 248 passed (9.87s) |

---

## Findings

### SEC-001: Live session-cookie file written to shared downloads directory and not crash-safe  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** validated (root cause confirmed; recommendation stands unchanged).
> - **Detail:** Verified against current source. (1) `_build_ytdlp_options` writes the Netscape cookie file
>   to `output_file.parent / f".{output_file.stem}_cookies.txt"` at `downloader.py:188-189` (raw_cookies
>   branch) and `downloader.py:192-193` (cookies branch) — i.e. the user's download output directory.
>   (2) `output_file` derives from `settings.download_dir`, whose default is
>   `Path.home() / "Downloads" / "vkdownloader"` (`config.py:76`) — a commonly cloud-synced/shared folder.
>   (3) `_write_netscape_cookie_file` creates the file `0o600` via `os.open` (`cookies.py:72`) — a
>   mitigation that is present but insufficient for the abnormal-termination window. (4) Cleanup is in a
>   `finally` inside the `_download()` closure (`downloader.py:639-643`), which runs in an executor
>   thread (`loop.run_in_executor`, `downloader.py:648`) and does **not** execute on SIGKILL / OOM-kill /
>   power loss, leaving plaintext session credentials persisted in the downloads folder (and synced-cloud
>   trash). (5) The secure contrast pattern already exists: `_temp_headers_file` uses
>   `tempfile.mkstemp(...)` at `downloader.py:70`.
> - **Architectural fit:** relocating to `tempfile.mkstemp` (system temp, `0o600`), cleaned in the
>   existing `finally`, mirrors `_temp_headers_file`; yt-dlp reads the file by path, so the happy-path
>   behavior is unchanged. Backward-compatible, low coupling.
> - **Residual note:** even with `mkstemp`, a SIGKILL/power-loss would leave a temp file in the (private,
>   non-synced) system temp dir. That is the same residual as the existing headers-file pattern and is
>   acceptable; it removes the *synced-cloud-trash* exposure, which is the reported hazard.
> - **See also:** cookie file is consumed by `perform_download` (`downloader.py:610`); Phase 03 SRV-001
>   touches the browser-cookie *acquisition* path (`_resolve_cookies`) but a distinct root cause.
> - **Rollout safety:** no dependency on other findings; no circular/hidden dependency.

**Description:** When browser cookies are captured for authenticated downloads, live VK session cookies are
serialized into a Netscape-format cookie file and written into the **download output directory**
(`output_file.parent`), which defaults to `~/Downloads/vkdownloader` — a folder commonly cloud-synced
(OneDrive, Dropbox, iCloud) and shared. The file is deleted only inside a `finally` block of the inner
`_download()` closure, so an abnormal termination (SIGKILL, OOM-kill, hard crash, power loss) leaves
plaintext session credentials persisted on disk in the user's downloads folder (and synced-cloud trash).
This deviates from the credential-file invariant that live credentials must reside in a private,
crash-reclaimable location.

**Evidence (verified against current source):**

- `src/vkdownloader/services/downloader.py:188-189` — cookie file path is the output directory (raw_cookies branch):
  ```python
  cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
  _write_netscape_cookie_file(cookie_file, raw_cookies)
  ```
  (identical pattern at `downloader.py:192-193` for the `cookies` branch — same deviation)
- `src/vkdownloader/services/downloader.py:639-643` — cleanup only in `finally` (not crash-safe):
  ```python
  finally:
      # Clean up cookie file after download completes (success or failure)
      if cookie_file is not None and cookie_file.exists():
          cookie_file.unlink()
          logger.debug("cookie_file_cleaned_up", path=str(cookie_file))
  ```
  This `finally` is inside `_download()`, which runs via `loop.run_in_executor(None, _download)`
  (`downloader.py:648`); it cannot run on SIGKILL/OOM-kill/power-loss.
- `downloader.py:70` — secure contrast pattern already used for ffmpeg headers:
  ```python
  fd, path = tempfile.mkstemp(suffix=".headers", prefix="vk_ffmpeg_")
  ```
- `src/vkdownloader/services/cookies.py:72` — file created `0o600` (mitigation present, insufficient):
  ```python
  fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
  ```
- `config.py:76` — default download dir confirms shared-folder exposure:
  ```python
  download_dir: Path = Field(default=Path.home() / "Downloads" / "vkdownloader", ...)
  ```
- `.gitignore:22` (`*_cookies.txt`) and `:28` (`.env`); `git check-ignore` confirms both match.

**Recommendation (confirmed):** Write the Netscape cookie file to a private temp file via
`tempfile.mkstemp` (matching `_temp_headers_file`), cleaned up in the existing `finally`. Trivial, low-risk,
architecturally consistent.

**Validation decision: VALIDATED.** All claims reproduced against current source; the secure contrast
pattern exists; the crash-safety gap is real; scope is complete (grep shows no other cookie-file write site).

---

### SEC-002: Raw user-supplied URL logged verbatim in batch-invalid-URL warning, bypassing `_strip_auth_params`  [VALIDATED — SCOPE CORRECTED]

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Validation Status** | VALIDATED (scope corrected — 2 raw-URL logger sites, not 1) |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (core deviation confirmed) — scope corrected.
> - **Detail:** The cited problem is real: `cli.py:575` logs `url=stripped` (raw) via
>   `logger.warning("invalid_url_in_batch", ...)`, bypassing `_strip_auth_params`. The codebase-wide
>   invariant is that every URL log call wraps the URL in `_strip_auth_params` (34 call sites across
>   `extractor.py`, `downloader.py`, `segment_downloader.py`, `network_monitor.py`,
>   `downloader_throttle.py`); `cli.py` is the **only** module that does not import `_strip_auth_params`
>   at all.
> - **Evidence correction (validator methodology):** the finding's "This is the sole outlier" claim and
>   the audit's Runtime-Verification R2 ("except one outlier") are **inaccurate**. A systematic grep of
>   every logger-emitted URL (`logger\.\w+\(.*(url|video_url|m3u8_url|segment_url)=`) plus f-string
>   interpolation (`logger\.\w+\(f"...url`) identifies **two** raw-URL logger call sites in `cli.py`:
>   1. `cli.py:575` — `logger.warning("invalid_url_in_batch", url=stripped)` (the cited site)
>   2. `cli.py:243` — `logger.exception("unexpected_error_in_batch_download", url=url)` — `url` is the
>      **raw** user URL passed into `_download_single` (used unsanitized at `extractor.extract_streams(url)`
>      `:200` and `perform_download(url, ...)` `:216`); it is never routed through `_strip_auth_params`.
>   A third candidate, `downloader_throttle.py:321` (`logger.info("download_cancelled", ..., url=url)`), is
>   **not** a leak: its only caller (`downloader_throttle.py:206`) passes `sanitized_url`
>   (already `_strip_auth_params`'d at line 169); the parameter name `url` is merely misleading.
>   `extractor.py:176`/`241` are `Stream(...)` constructor kwargs, not loggers.
> - **Architectural fit / ROI:** importing `_strip_auth_params` into `cli.py` and applying it at both
>   `:243` and `:575` (or logging only the parsed `video_id`) is consistent with the established pattern.
>   Logs-only change — no behavioral impact on downloads.
> - **See also:** SEC-003 (same "CLI redaction gap" theme; distinct code path/fix); SEC-001 (unrelated).
> - **Rollout safety:** independent; no dependency on other findings.

**Description:** In the batch command, URLs read from the user's URL file that fail the video-ID pattern
check are logged verbatim via `logger.warning("invalid_url_in_batch", url=stripped)`. Every other URL log
call in the codebase wraps the URL in `_strip_auth_params()`. **Correction:** it is not the sole outlier —
`cli.py:243` logs the raw user URL identically. VK video URLs may carry an `access_key` query parameter
(a credential for private videos); logging them raw to structured logs (which may be redirected to a file)
violates the "Secrets never logged" invariant.

**Evidence (verified):**

- `src/vkdownloader/cli.py:574-575` (cited site):
  ```python
  if not VIDEO_ID_PATTERN.search(stripped):
      logger.warning("invalid_url_in_batch", url=stripped)
  ```
- `src/vkdownloader/cli.py:242-244` (additional, NOT cited by the finding):
  ```python
  except Exception:
      logger.exception("unexpected_error_in_batch_download", url=url)
      raise
  ```
- `url` at `:243` is the raw parameter of `_download_single` (passed to `extractor.extract_streams(url)`
  at `:200` and `perform_download(url, ...)` at `:216`); never routed through `_strip_auth_params`.
- `_strip_auth_params` (`utils/url_sanitizer.py:6`) reduces URLs to
  `scheme://netloc/***REDACTED***`; used at 34 sites; `cli.py` has **0** imports/usages
  (`cli.py` is absent from the `_strip_auth_params` grep results).

**Recommendation (expanded):** Pass both `url=stripped` (`:575`) and `url=url` (`:243`) through
`_strip_auth_params()` before logging, consistent with the rest of the codebase. `cli.py` must import
`_strip_auth_params` from `utils.url_sanitizer`. (Alternatively log only the parsed `video_id`.)
Effort: trivial.

**Validation decision:** VALIDATED as `SPEC-DEVIATION` (code deviates from the codebase-wide
sanitization invariant; docs don't govern this). The scope claim is corrected: there are two raw-URL
logger sites, and the recommendation is expanded accordingly. No reclassification.

---

### SEC-003: Validation error handler echoes raw received config values to stderr (latent secret leakage)  [VALIDATED]

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Validation Status** | VALIDATED |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated (latent leak confirmed; no reclassification).
> - **Detail:** Verified: `_format_validation_error` (`cli.py:61-64`) appends `err.get("input")` raw via
>   `f"    Received: {received!r}"`, emitted to stderr with `typer.echo(..., err=True)` at `cli.py:474`
>   (single-download path) and `cli.py:596` (batch path) — both confirmed by direct read. The `Settings`
>   model (`config.py:16-145`) defines **no** secret-bearing fields (all bool/int/str/Path/enum);
>   cookies are obtained via live browser automation (see `CookieSource`), not config — so the leak is
>   currently latent, exactly as the audit states.
> - **Classification rationale:** forward-looking defense-in-depth, not an active secret leak today ->
>   `BEST-PRACTICE` (advisory) is the correct taxonomy. Not `SPEC-DEVIATION` (no current secret exposed);
>   not `DOC-UPDATE` (neither code nor docs are "correct" relative to each other).
> - **Architectural fit / ROI:** redacting `received` to a placeholder (e.g. `"<redacted>"`) for
>   known-sensitive field names is trivial, adds forward-compatibility, and is not overengineered.
>   Positive-but-low ROI at this scale (no current secret fields) — accepted as advisory.
> - **See also:** SEC-002 (CLI-layer redaction gap, different path); Phase 02 CFG-001/CFG-010
>   (the `_format_validation_error` surface at `:474`/`:596`).
> - **Rollout safety:** self-contained in `cli.py`; no dependency on other findings.

**Description:** `_format_validation_error` appends the raw, unvalidated config input value
(`err.get("input")`) to the user-facing error message via `f"    Received: {received!r}"`. This message
is emitted with `typer.echo(..., err=True)` (`cli.py:474,596`), which in production/systemd contexts is
captured into log files. The "Error messages don't leak secrets" invariant is therefore violated by
pattern: the code has no guard against echoing sensitive input. No finding is rated higher only because
`Settings` currently defines no secret-bearing fields (cookies are obtained via live browser automation,
not config) — the leak is latent and would become active if any secret field is ever added to configuration.

**Evidence (verified):**

- `src/vkdownloader/cli.py:61-64`:
  ```python
  received = err.get("input")
  lines.append(f"  - {loc}: {msg}")
  if received is not None:
      lines.append(f"    Received: {received!r}")
  ```
- `src/vkdownloader/cli.py:474` and `:596`: `typer.echo(_format_validation_error(e), err=True)`.
- `src/vkdownloader/config.py:16-145`: `Settings` fields — `headless`, `user_agent`, `timezone`,
  `locale`, `max_retries`, `download_timeout`, `browser_pre_interaction_wait`,
  `browser_post_interaction_wait`, `ssl_verify`, `download_dir`, `max_concurrent_downloads`,
  `throttled_rate`, `http_chunk_size`, `cookie_source`, `log_level`, `log_file`. None are secret
  credentials.

**Recommendation (confirmed):** Do not echo raw received values; emit a redacted placeholder
(e.g. `"<redacted>"`) or a type-only summary for sensitive field names. Effort: trivial.

**Validation decision: VALIDATED (`BEST-PRACTICE`, unchanged).**

---

## Cross-Finding Analysis

**Scope:** Phase 04 findings cross-referenced against Phase 01 (CLI), Phase 02 (Config), Phase 03 (Services).

**Same root cause (merge candidates):**

- **SEC-002 ↔ SEC-003** share a theme — "the CLI entry layer lacks a systematic redaction guard." They target
  **distinct code paths** (`logger` URL emission at `cli.py:243/575` vs. `_format_validation_error` echo at
  `cli.py:61-64`) with **distinct remediations**. Kept separate for independent fixability and review.
- SEC-001 is unrelated (cookie-file location / crash-safety on disk).

**Conflicting evidence (cross-phase):** None. No other phase asserts that raw URLs are logged safely, that
cookie files are crash-safe, or that validation errors redact input. Phase 04's own Runtime-Verification
R2 ("URLs sanitized via `_strip_auth_params` except one outlier") is **partially inaccurate** — it omits
`cli.py:243` (see SEC-002 note). This is an in-phase evidence overstatement, not a cross-phase conflict.

**Dependency chains:**

- **None.** SEC-001 touches `downloader.py`/`cookies.py`; SEC-002 and SEC-003 touch `cli.py`. No finding's
  fix depends on another's.
- **Cross-phase relevance (informational, not a dependency):** SEC-001's cookie file is written by
  `_build_ytdlp_options` (`downloader.py:188-194`) and consumed downstream by `perform_download`.
  Phase 03 SRV-001 concerns browser-cookie *acquisition* (`_resolve_cookies`, `downloader.py:665+`) and
  quality parsing. They touch neighboring code but **distinct root causes** (file location/crash-safety
  vs. quality-string parsing) — not a dependency.

## Rollout Analysis

- **Independence / ordering:** All three are localized and backward-compatible; order independent.
  - **SEC-001 (HIGH, mandatory):** stop writing the cookie file to `output_file.parent`. Create it via
    `tempfile.mkstemp` (system temp, owner-only `0o600`) — mirroring `_temp_headers_file` (`downloader.py:70`)
    — and clean it up in the existing `finally` (`downloader.py:639-643`). yt-dlp reads by path -> no API
    change. On success/failure paths the file is still deleted; only the abnormal-termination residue moves
    out of the synced downloads folder. First.
  - **SEC-002 (LOW, advisory):** wrap `url=stripped` (`:575`) and `url=url` (`:243`) in `_strip_auth_params`;
    import the helper into `cli.py`. Logs-only change.
  - **SEC-003 (LOW, advisory):** redact `received` in `_format_validation_error` (`cli.py:61-64`).
    Messages-only change.
- **Circular / hidden dependencies:** none.
- **Backward compatibility:** SEC-001 changes only the cookie-file *location* (downloads dir -> system
  temp); observable only on abnormal termination (file no longer persists in the synced folder) — a strict
  improvement. SEC-002/SEC-003 change log/error text only.
- **Anchors:** fixes target stable functions/locations (`_build_ytdlp_options`, the `_download()` `finally`,
  `_format_validation_error`, the two logger call sites) — no fragile line-only anchors.

## Execution Validation

- **Targets exist:** `downloader.py:188-189/192-193/639-643/70`, `cookies.py:72`, `cli.py:61-64/243/575`,
  `cli.py:474/596`, `config.py:76`, `url_sanitizer.py:6`, `downloader_throttle.py:206/321` — all read-confirmed
  in the current tree.
- **Plan not stale:** tree is green (`ruff` pass, 248 tests pass); cited line contents match the findings
  exactly, including the second raw-URL logger at `cli.py:243`.
- **Architecture consistent:** SEC-001's fix mirrors the existing `_temp_headers_file` `tempfile.mkstemp`
  pattern; SEC-002 reuses the existing `_strip_auth_params` utility.
- **Applicability:** all three findings applicable and executable. Scope: safety, consistency,
  applicability only — no source code was modified.
- **Scope correction applied:** had SEC-002 been implemented exactly as originally recommended (fix only
  `:575`), `cli.py:243` would continue leaking. The corrected recommendation covers both sites.

## Warnings

- **Architectural risk (low):** SEC-001's cleanup `finally` lives inside `_download()` (an executor-thread
  function). Even on normal `asyncio.CancelledError` (the main coroutine cancels the executor future at
  `cli.py:658`), the worker thread is not interrupted and its `finally` runs only when the thread finishes;
  if the process is then killed before that, the file is not cleaned. The `mkstemp` fix does not depend on
  `finally` for *security* (the file is already in a private, non-synced temp dir) — only for tidiness.
- **Rollout risk (low):** SEC-001 relocates a transient credential file. Because yt-dlp consumes it by path
  and the `finally` still attempts deletion, the only behavioral delta is the absence of a persisted cookie
  file in the synced downloads folder after abnormal termination — a strict improvement.
- **Dependency risk:** none.
- **Documentation / evidence inconsistency:** Phase 04 Runtime-Verification R2 and the SEC-002 body both
  understate scope ("sole outlier" / "except one outlier"); corrected to two raw-URL logger sites.

## Required Fixes (mandatory)

- **SEC-001 (HIGH, mandatory):** In `src/vkdownloader/services/downloader.py`, stop writing the Netscape
  cookie file to `output_file.parent`. Create it via `tempfile.mkstemp` (system temp dir, owner-only
  `0o600`) — mirroring `_temp_headers_file` (`downloader.py:70`) — and clean it up in the existing
  `finally` at `downloader.py:639-643`. Eliminates live session-cookie persistence in a cloud-synced
  downloads folder after abnormal termination. (Write sites: `downloader.py:188-189` and `:192-193`.)

## Advisory Recommendations

- **SEC-002 (LOW, advisory):** Import `_strip_auth_params` into `cli.py` and route both URL-emitting logger
  calls through it:
  - `cli.py:575` — `logger.warning("invalid_url_in_batch", url=...)` -> `url=_strip_auth_params(stripped)`
    (or log only `video_id`).
  - `cli.py:243` — `logger.exception("unexpected_error_in_batch_download", url=url)` ->
    `url=_strip_auth_params(url)`.
  - Effort: trivial.
- **SEC-003 (LOW, advisory):** In `_format_validation_error` (`cli.py:61-64`), do not echo the raw
  `received` value; emit a redacted placeholder (e.g. `"<redacted>"`) or a type-only summary for sensitive
  field names. Defense-in-depth against future secret-bearing config fields. Effort: trivial.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | SEC-001, SEC-003 |
| Validated + scope corrected | 1 | SEC-002 (two raw-URL logger sites found at `cli.py:243` + `:575`, not one; "sole outlier" claim overstated) |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| _(none)_ | — | All three findings verified against current code; none stale/duplicated/low-ROI/unsafe. (SEC-002's "sole outlier" *scope claim* is corrected and the recommendation expanded, but the underlying deviation is real and the finding is retained.) |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| _(none)_ | — | SEC-002 and SEC-003 share a "CLI redaction gap" theme but distinct code paths and fixes; kept separate for independent remediation. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| _(none)_ | — | — | All types already align with the validator taxonomy: SEC-001 = `SPEC-DEVIATION` (code violates the codebase-wide secure-file invariant; the secure pattern already exists at `downloader.py:70`); SEC-003 = `BEST-PRACTICE` (latent, forward-looking hardening). No `DOC-UPDATE` candidates (no finding has correct code + stale docs). |
