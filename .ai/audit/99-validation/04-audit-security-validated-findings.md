---
name: audit-findings
description: Phase 04 Security & Secret Management audit findings (validated)
agent: validator
status: validated
validated_date: 2026-07-20
---

# Phase 04 Audit Findings — Security & Secret Management (Validated)

**Executor:** auditor  
**Template:** .kilo/commands/audit/phases/04-audit-security.md  
**Status:** complete  
**Validated:** validator  

---

## Runtime Verification Evidence

The auditor's evidence has been verified:

- **R1 (Credential leak search):** Confirmed. The grep search found no hardcoded real secrets. All matches are runtime variables or test fixtures with obviously fake values (`vk=secret123`, `token=mytoken123`, `session_id=abc123`). The `.env` file is a fully-commented template with no real values and is git-ignored.

- **R2 (Logger audit):** Confirmed. All log calls receive URLs through `_strip_auth_params()` in `url_sanitizer.py`. Cookie values are never logged; only the cookie file path is logged at debug level (line 587 in downloader.py). No config model is dumped to logs.

- **R3 (File permission / ignore):** Confirmed. `.gitignore` covers `.env` (line 28) and `*_cookies.txt` (line 22). `git check-ignore` confirms both patterns match cookie files. Cookie/session files are not committed.

- **R4 (Import verification):** Confirmed. All secret-handling modules import without side effects leaking credentials.

- **R5 (Linter/type):** Confirmed. `uv run ruff check src/` and `uv run mypy src/` both pass.

- **R6 (Tests):** Confirmed. `uv run pytest tests/` → 217 passed.

---

## Findings

### SEC-001: Browser-captured session cookies persisted to disk with default (world-readable) permissions

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/cookies.py` |
| **Classification** | advisory |

**Description:** When `cookie_source=BROWSER`, the yt-dlp download path writes a Netscape cookie file containing the user's live VK session cookies to `output_file.parent` (default `~/Downloads/vkdownloader`) using `cookie_file.write_text(...)`. `Path.write_text()` creates the file with the process umask (typically `0644` on Unix / inheritable ACLs on Windows), i.e. readable by other local users for the duration of the download. These are valid, reusable authentication secrets. The file is removed in a `finally` block, but it persists on disk with weak permissions during the entire download, and the cleanup only runs on the yt-dlp code path.

**Evidence:**
- `downloader.py:183-184` and `downloader.py:187-188`: `cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"; cookie_file.write_text(_cookies_to_netscape(raw_cookies))` — no permission hardening.
- `cookies.py:45`: writes `name\tvalue` pairs (the session cookie value) verbatim to that file.
- Contrast: the ffmpeg path uses `_temp_headers_file()` (`downloader.py:71`) via `tempfile.mkstemp`, which creates the file `0600` (owner-only). The cookie-file path does NOT get equivalent hardening.

**Recommendation:** Create the cookie file with restrictive permissions (e.g. `os.open` with `0o600`, or `chmod 0o600` immediately after creation). Optionally write it to the same `mkstemp`-style temp location instead of the world-readable download directory. This limits local credential-theft exposure on shared/multi-user machines.
- **why:** Session cookies are bearer credentials; a world-readable file in a shared downloads folder is a real (if local) secret-leak vector.
- **effort:** small
- **priority:** recommended

---

### SEC-002: `--cookie-source file` is selectable but raises NotImplementedError at runtime

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py`, `src/vkdownloader/cli.py`, `src/vkdownloader/models/enums.py`, `docs/01-tools/api-reference.md`, `docs/99-reference/cli-reference.md` |
| **Classification** | advisory |

**Description:** The `CookieSource.FILE` value is a first-class enum member, is advertised in the CLI `--cookie-source` help text ("none, browser, or file"), and is documented as a "placeholder for future enhancement" (api-reference.md:657). However, selecting it at runtime immediately raises `NotImplementedError` from `extract_streams_with_cookies` (extractor.py:124-126). This is a misleading security/config surface: a user following the documented CLI option gets a hard crash rather than an early validation error. It also widens the apparent credential-handling surface (a "file" cookie store) that is unimplemented.

**Evidence:**
- `cli.py:312-317` / `cli.py:438-443`: help text lists "none, browser, or file".
- `extractor.py:123-126`: `if self.settings.cookie_source == CookieSource.FILE: raise NotImplementedError(...)`.
- `models/enums.py:50`: `FILE = "file"` is a valid selectable enum value.
- `api-reference.md:657`: "FILE — Load cookies from external file (placeholder for future enhancement)".

**Recommendation:** Add a fail-fast validator in `src/vkdownloader/config.py` on the `cookie_source` field that raises `ValueError("cookie_source=FILE is not yet implemented; use 'none' or 'browser' instead")` when `CookieSource.FILE` is selected. This ensures consistent behavior across all entry points (CLI, env var, programmatic API) and matches the documented contract. Then update the CLI help text in `cli.py` (lines 316 and 442) to read `help="Cookie source: none or browser (file not yet implemented)"` and update `docs/01-tools/api-reference.md:657` to clearly mark FILE as unimplemented rather than a future enhancement placeholder. Keep `CookieSource.FILE` enum value for API compatibility but make its selection consistently fail before any download work begins.
- **why:** Prevents silent no-op behavior in the primary download flow (CFG-001) while honoring the existing `NotImplementedError` guard (SEC-002) - users receive an immediate, actionable error instead of confusing silent or disparate behaviors.
- **effort:** trivial (single field_validator in config.py + CLI help text update)
- **priority:** recommended

> **Cross-phase Resolution:** SEC-002 and CFG-001 share the same root cause (`CookieSource.FILE` is unimplemented). CFG-001 recommended rejecting FILE explicitly at the CLI/Settings validation boundary - this recommendation implements that approach. The validator ensures FILE fails consistently whether invoked via CLI (`--cookie-source file`), environment variable (`VKDOWNLOADER_COOKIE_SOURCE=file`), or programmatic API instantiation (`Settings(cookie_source=CookieSource.FILE)`), unifying both findings' concerns into a single fix.

> **Implementation Details:**
> - Add `@field_validator("cookie_source")` in `Settings` class to reject FILE at instantiation
> - CLI help text: change "none, browser, or file" to "none or browser (file not implemented)"
> - Docs/api-reference.md:657: change description to indicate FILE is explicitly rejected with error
> - Do NOT remove `CookieSource.FILE` enum member - this is intentional for future use and API compatibility

> **Validation Note:**
> - **Action:** Replaced ambiguous two-alternative recommendation with single actionable fix aligned with CFG-001
> - **Detail:** This addresses both the silent no-op (CFG-001) and the misleading crash path (SEC-002) by failing early at Settings construction.
> - **See also:** CFG-001 (Phase 02)

---

### SEC-003: Batch URL file content is not validated before use

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** In `batch_download`, the URL list file is read with `urls_file.read_text()` and each non-empty, non-comment line is passed straight to the extractor (`cli.py:466-470`). There is no pre-validation that lines are well-formed VK video URLs. Malformed or non-VK URLs only fail later inside `VKVideoExtractor.parse_video_id` with a generic `ValueError`. While `parse_video_id` does sanitize the URL through `_strip_auth_params` before logging, there is no early reject of obviously invalid input, and the batch loop swallows per-URL errors into a summary (cli.py:162-163, 279-283) so a bad entry is easy to miss.

**Evidence:**
- `cli.py:466-470`: lines split and stripped with no format/whitelist check.
- `extractor.py:48-50`: validation only happens at extract time via `VIDEO_ID_PATTERN`, raising `ValueError(f"Invalid VK video URL: ...")`.

**Recommendation:** Validate each batch line against the VK URL pattern (or a URL scheme/host allowlist) before enqueueing, logging a clear per-line warning for rejected entries. This is input-validation hardening (dimension 5) and improves operator feedback.
- **why:** Early, explicit input validation prevents silent partial failures in batch mode and limits the blast radius of a malformed input file.
- **effort:** small
- **priority:** recommended

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 2 |

## Mandatory Fixes

None. No security vulnerability rises to mandatory (data loss / correctness / leaked real secret) severity. Finding SEC-001 is the most operationally relevant but is local-exposure only and advisory.

## Advisory Recommendations

- **SEC-001** (MEDIUM): Harden permissions on the Netscape cookie file written during BROWSER-mode yt-dlp downloads.
- **SEC-002** (LOW): Reject `cookie_source=FILE` early via a `field_validator` in `config.py` and mark it unimplemented in CLI help/docs (aligned with CFG-001).
- **SEC-003** (LOW): Validate batch URL file entries before enqueueing.

## Doc Updates Needed

- **SEC-002**: `src/vkdownloader/config.py` (`cookie_source` field_validator), `cli.py` (help text lines ~316 and ~442), `docs/01-tools/api-reference.md:657` and `docs/99-reference/cli-reference.md` should mark `file` as unimplemented and not present it as a usable cookie source; selection must fail with a clear early error (see CFG-001 resolution).

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | SEC-001, SEC-002, SEC-003 |
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

### CFG-001 / SEC-002 Conflict (Critical)

**Finding:** Both CFG-001 (Phase 02) and SEC-002 (Phase 04) identify issues with `CookieSource.FILE`, but with contradictory behaviors:

- **CFG-001** claims: `cookie_source=FILE` silently behaves like `none` in the primary download flow (no `NotImplementedError` raised)
- **SEC-002** claims: `cookie_source=FILE` raises `NotImplementedError` at runtime

**Investigation Result:** Both findings are correct but describe different code paths:

1. **Direct API usage via `extract_streams_with_cookies()`**: Raises `NotImplementedError` as described in SEC-002.

2. **Primary CLI flow via `download`/`batch` commands**: Never calls `extract_streams_with_cookies()`. Instead:
   - `cli.py:111` (`download`) calls `extractor.extract_streams(url)` — ignores `cookie_source` entirely
   - `downloader.py:631` (`_resolve_cookies`) only calls `extract_streams_with_cookies()` when `cookie_source == BROWSER`

3. **Segment-download token refresh path**: `segment_downloader.py:381` logs a warning and skips browser flow when `cookie_source != BROWSER`.

**Resolution:** The inconsistent behaviors are unified by a single fix: a fail-fast `field_validator` on `cookie_source` in `config.py` that rejects `CookieSource.FILE` at `Settings` construction with a clear error. This makes FILE fail consistently (whether via CLI, env var, or API) and eliminates both the silent no-op (CFG-001) and the late `NotImplementedError` crash (SEC-002). The enum member is retained for future use; documentation and CLI help are updated to mark FILE as unimplemented.

### Dependencies

- SEC-002 and CFG-001 share the same root cause (unimplemented `CookieSource.FILE` value) and are resolved together by the `config.py` `field_validator` described in CFG-001.