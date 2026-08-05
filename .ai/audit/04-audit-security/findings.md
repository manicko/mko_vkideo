# Phase 04 Audit Findings — Security & Secret Management

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification

| Step | Check | Result |
|------|-------|--------|
| R1 | Credential leak search (hardcoded keys/tokens/passwords/private keys across repo incl. `.env`) | No hardcoded secrets found. `.env` is untracked and contains placeholder-only (commented) values. Test fixtures use fake values (`mytoken`, `abc123`, `xyz789`). |
| R2 | Logger audit for secret leakage | No cookie/token/value contents logged. URLs sanitized via `_strip_auth_params` except one outlier (see SEC-002). |
| R3 | VCS ignore & file-permission check | `.env` ignored. `*_cookies.txt` ignored (verified `git check-ignore` matches dot-prefixed `.{stem}_cookies.txt`). Cookie files created with `0o600` via `os.open`. |
| R4 | Import verification (no import-time credential side effects) | `Import OK — no side effects` |
| R5 | Linter / type checker | `ruff check` OK; `ruff format --check` OK (38 files); `mypy` strict OK (23 files, no issues) |
| R6 | Test suite | `pytest` → 248 passed |

---

## Findings

### SEC-001: Live session-cookie file written to shared downloads directory and not crash-safe

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |

**Description:** When browser cookies are captured for authenticated downloads, live VK session cookies are serialized into a Netscape-format cookie file and written into the **download output directory** (`output_file.parent`), which defaults to `~/Downloads/vkdownloader` — a folder commonly cloud-synced (OneDrive, Dropbox, iCloud) and shared. The file is deleted only inside a `finally` block of the inner `_download()` closure, so an abnormal termination (SIGKILL, OOM-kill, hard crash, power loss) leaves plaintext session credentials persisted on disk in the user's downloads folder (and synced-cloud trash). This deviates from the credential-file invariant that live credentials must reside in a private, crash-reclaimable location.

**Evidence:**
- `src/vkdownloader/services/downloader.py:188-189` — cookie file path is the output directory:
  ```python
  cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
  _write_netscape_cookie_file(cookie_file, raw_cookies)
  ```
- `src/vkdownloader/services/downloader.py:639-643` — cleanup only in `finally` (not crash-safe):
  ```python
  finally:
      if cookie_file is not None and cookie_file.exists():
          cookie_file.unlink()
          logger.debug("cookie_file_cleaned_up", path=str(cookie_file))
  ```
- Contrast: secure pattern already used for ffmpeg headers at `downloader.py:70` uses `tempfile.mkstemp(...)` (system temp dir, `0o600`, owner-only). Cookie files use no private-temp placement.
- Mitigations present but incomplete: `_write_netscape_cookie_file` creates the file `0o600` (`services/cookies.py:72`); `*_cookies.txt` is gitignored. Neither covers the abnormal-termination window or the synced-folder exposure.

**Recommendation [BEST-PRACTICE]:** Write the Netscape cookie file to a private temp file via `tempfile.mkstemp` (matching `_temp_headers_file`) and clean it up in the same `finally`, so live credentials never land in a user-facing/synced downloads folder. Effort: trivial. Priority: recommended.

---

### SEC-002: Raw user-supplied URL logged verbatim in batch-invalid-URL warning, bypassing `_strip_auth_params`

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** In the batch command, URLs read from the user's URL file that fail the video-ID pattern check are logged verbatim via `logger.warning("invalid_url_in_batch", url=stripped)`. Every other URL log call in the codebase wraps the URL in `_strip_auth_params()` (see `extractor.py:59,83,88,125,138,161,218,236`; `downloader.py:303,598,628,707,750,775,802`; `segment_downloader.py:486,797`; `network_monitor.py:66,80,94,102,113,119,136`) precisely to prevent signed CDN / `access_key`-bearing VK URLs from leaking into logs. This is the sole outlier. VK video URLs may carry an `access_key` query parameter (a credential granting access to private videos); logging them raw to structured logs (which may be redirected to a file) violates the "Secrets never logged" invariant.

**Evidence:**
- `src/vkdownloader/cli.py:574-575`:
  ```python
  if not VIDEO_ID_PATTERN.search(stripped):
      logger.warning("invalid_url_in_batch", url=stripped)
  ```

**Recommendation [BEST-PRACTICE]:** Pass the URL through `_strip_auth_params(stripped)` (or log only the parsed `video_id`) before `logger.warning`, consistent with the rest of the codebase. Effort: trivial. Priority: recommended.

---

### SEC-003: Validation error handler echoes raw received config values to stderr (latent secret leakage)

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `_format_validation_error` appends the raw, unvalidated config input value (`err.get("input")`) to the user-facing error message via `f"    Received: {received!r}"`. This message is emitted with `typer.echo(..., err=True)` (cli.py:474,596), which in production/systemd contexts is captured into log files. The "Error messages don't leak secrets" invariant is therefore violated by pattern: the code has no guard against echoing sensitive input. No finding is rated higher only because `Settings` currently defines no secret-bearing fields (cookies are obtained via live browser automation, not config) — the leak is latent and would become active if any secret field is ever added to configuration.

**Evidence:**
- `src/vkdownloader/cli.py:61-64`:
  ```python
  received = err.get("input")
  lines.append(f"  - {loc}: {msg}")
  if received is not None:
      lines.append(f"    Received: {received!r}")
  ```

**Recommendation [BEST-PRACTICE]:** Do not echo raw received values; replace with a redacted placeholder (e.g., `"<redacted>"`) or a type-only summary for sensitive field names. Effort: trivial. Priority: recommended (forward-looking hardening).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 0 |
| LOW | 2 |

## Mandatory Fixes

- **[SEC-001]** Relocate the Netscape cookie file from the download output directory to a private `tempfile.mkstemp` location (owner-only, system temp), cleaned up in the existing `finally`. Eliminates live-session-cookie persistence in a commonly cloud-synced downloads folder after abnormal termination. `src/vkdownloader/services/downloader.py:188-189` (write site) and `downloader.py:639-643` (cleanup).

## Advisory Recommendations

- **[SEC-002]** Route the batch `invalid_url_in_batch` log through `_strip_auth_params` (or log only `video_id`) so invalid URLs — which may carry VK `access_key` credentials — are redacted like every other URL log call. `src/vkdownloader/cli.py:575`. Effort: trivial.
- **[SEC-003]** Stop echoing raw `received` config values in `_format_validation_error`; emit a redacted placeholder. Defense-in-depth against future secret-bearing config fields leaking to captured stderr/logs. `src/vkdownloader/cli.py:61-64`. Effort: trivial.

## Doc Updates Needed

- (None)

---

