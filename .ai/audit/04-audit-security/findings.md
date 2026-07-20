---
name: audit-findings
description: Phase 04 Security & Secret Management audit findings
agent: auditor
alwaysApply: false
---

# Phase 04 Audit Findings — Security & Secret Management

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/04-audit-security.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Evidence

- **R1 (Credential leak search):** Grep for `api_key|token|secret|password|credential|session_id|access_token|client_secret` across `src/` and `tests/`. All matches are: (a) runtime variables named `token`/`cookies` (not hardcoded values), (b) test fixtures using obviously fake values (`vk=secret123`, `token=mytoken123`, `session_id=abc123`). No hardcoded real secrets found. `.env` is a fully-commented template with no real values and is git-ignored. `.env` tracked? `git ls-files | Select-String .env` -> empty (not tracked).
- **R2 (Logger audit):** All log calls that receive URLs pass them through `_strip_auth_params()` (url_sanitizer.py). Verified across extractor.py, downloader.py, segment_downloader.py, network_monitor.py, downloader_throttle.py. Cookie values are never passed to log calls; only the cookie *file path* is logged at debug (`cookie_file_cleaned_up`, downloader.py:587). No config model is dumped to logs.
- **R3 (File permission / ignore):** `.gitignore` covers `.env` and `*_cookies.txt`. Verified `git check-ignore ".video_cookies.txt"` and `"myvideo_cookies.txt"` both match. Cookie/session files are not committed.
- **R4 (Import verification):** All secret-handling modules imported without side effects leaking credentials. `config.py` `Settings()` loads from `.env`/env vars only.
- **R5 (Linter/type):** `uv run ruff check src/` -> "All checks passed!". `uv run mypy src/` -> "Success: no issues found in 23 source files".
- **R6 (Tests):** `uv run pytest tests/` -> 217 passed.

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

**Recommendation:** Either (a) remove `FILE` from the enum and CLI choices until implemented, or (b) keep it but validate at CLI parse time and emit a clear, early error. Per the auditor guidance ("Is the code choice better than the doc?"): the `NotImplementedError` guard is reasonable; the documentation/CLI advertising an unimplemented secret-source is the deviation. Recommend updating docs/CLI to not present `file` as a usable option.
- **why:** Avoids a confusing crash and prevents users from assuming a credential-file store exists (security-relevant feature that is not actually available).
- **effort:** trivial
- **priority:** recommended

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
- **SEC-002** (LOW): Stop advertising unimplemented `--cookie-source file` in CLI/docs; validate at parse time or remove the enum value.
- **SEC-003** (LOW): Validate batch URL file entries before enqueueing.

## Doc Updates Needed

- **SEC-002** ([DOC-UPDATE]): `docs/01-tools/api-reference.md:657` and `docs/99-reference/cli-reference.md` (and CLI help in `cli.py`) should not present `file` as a usable cookie source, or should clearly mark it as disabled/unimplemented at the CLI layer.
