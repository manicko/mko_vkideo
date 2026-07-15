---
name: audit-findings
phase: 04-audit-security
description: Security & secret management audit findings for mko_vkideo (VK video downloader)
status: complete
validated: yes
problems-only: true
---

# Phase 04 Audit Findings â€” Security & Secret Management

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/04-audit-security.md
**Status:** complete
**Validated:** yes

> **Scope note:** The phase template was written for a Telegram/Google-Sheets project
> (`api_id`/`api_hash`, `credentials.json`, `token.json`, Telethon sessions, Spreadsheet IDs).
> None of those subsystems exist in `mko_vkideo`. The audit was adapted to this project's
> actual security surface: VK CDN auth tokens, browser-captured session cookies, SSL
> verification handling, subprocess (ffmpeg / yt-dlp) invocation, secure logging, and
> output-path validation.

## Runtime Verification Summary

| Step | Result |
|------|--------|
| R1 â€” Credential leak search | No hardcoded API keys/passwords/tokens in source. `.env` present but **not** git-tracked (`git ls-files --error-unmatch .env` â†’ not found). |
| R2 â€” Logger audit | Cookie/token values are not logged directly (`has_cookies=bool(cookies)` only). URL logging relies on `_strip_auth_params` â€” see SEC-003. |
| R3 â€” File permission / gitignore | `.env` is gitignored. Downloaded media, `*_segments/`, `*_progress.json` are gitignored. **`*_cookies.txt` is NOT** â€” see SEC-001. |
| R4 â€” Import verification | No import-time credential side effects observed. `Settings()` instantiated at import in `config.py:131` (reads `.env`) â€” see SEC-002. |
| R5 â€” Linter / type checker | `uv run ruff check src/vkdownloader` â†’ exit 0 ("All checks passed!"). `uv run mypy src/vkdownloader` â†’ exit 0 (no issues, 23 files). |
| R6 â€” Test suite | `uv run pytest` â†’ exit 0, **201 passed**, 4 warnings (unrelated `coroutine 'Event.wait' never awaited` mock warnings). |

---

## Findings

### SEC-001: Browser session cookies written to output directory as plaintext, never deleted, and not gitignored

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `.gitignore` |
| **Classification** | mandatory |

**Description:** When `cookie_source=BROWSER` (or during a forced token-refresh resume),
Playwright captures the full VK session cookie jar and it is written to a Netscape cookie
file in the *download output directory*. These cookies are live CDN/session authentication
material. The file is created but **never removed** after the download finishes or fails, so
authentication secrets persist on disk in cleartext. It is also **not covered by
`.gitignore`**, so if a user downloads into a repository/working tree the cookie file can be
committed and pushed. The `.` filename prefix is only a hiding convention on Unix, not
protection.

**Evidence:**
- `src/vkdownloader/services/downloader.py:385-388`
  ```python
  if cookies:
      cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
      cookie_file.write_text(_cookies_to_netscape(cookies))
      ydl_opts["cookiefile"] = str(cookie_file)
  ```
- No `cookie_file.unlink(...)` anywhere in the codebase (grep for `_cookies` shows creation only, never deletion).
- `_cookies_to_netscape` (`downloader.py:75-89`) writes every `name=value` pair verbatim into `.vkvideo.ru\tTRUE\t/\tFALSE\t0\t<name>\t<value>`.
- `.gitignore` (lines 1-25) lists `*.mp4`, `*_segments/`, `*_progress.json`, `.env` — but **no** `*_cookies.txt` entry.

**Recommendation:** (1) Delete the cookie file in a `finally` block once yt-dlp completes (or write it to a private temp dir via `tempfile`/`platformdirs` user dir with `0o600` permissions instead of the user-controlled output directory). (2) Add `*_cookies.txt` to `.gitignore` as defense-in-depth. Effort: small. Priority: mandatory — persisting reusable session credentials in an unmanaged, potentially version-controlled location is a real credential-exposure vector.

---

### SEC-002: Shipped `.env` disables SSL verification by default, silently overriding the documented secure default

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.env`, `src/vkdownloader/config.py`, `src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `config.py` declares `ssl_verify` default `True` and `README.md:29` states
"SSL verification enabled by default", but the `.env` present in the repo sets
`VKDOWNLOADER_SSL_VERIFY=false`. Because `Settings` is configured with `env_file=".env"`
(`config.py:101-106`) and a module-level `settings = Settings()` is created at import
(`config.py:131`), **every invocation run from this directory loads with certificate
verification disabled** — contradicting the documented and code-declared secure default. When
disabled, the code sets `ssl_context.check_hostname = False` and `verify_mode = ssl.CERT_NONE`,
fully removing MITM protection for all CDN/HLS traffic (and yt-dlp `nocheckcertificate`).

**Evidence:**
- `.env:12` > `VKDOWNLOADER_SSL_VERIFY=false` (only *active*, non-commented setting in the file).
- `config.py:47-50` default `ssl_verify: bool = True`; `config.py:101-106` `env_file=".env"`, `env_prefix="VKDOWNLOADER_"`.
- `README.md:29` > "SSL verification enabled by default" (reality diverges).
- `http_client.py:54-57` and `segment_downloader.py:224-227`:
  ```python
  ssl_context.check_hostname = False
  ssl_context.verify_mode = ssl.CERT_NONE
  ```
- `downloader.py:370` > `"nocheckcertificate": not settings.ssl_verify`.

**Recommendation:** Remove the `VKDOWNLOADER_SSL_VERIFY=false` line from the tracked/shipped `.env` (leave it commented like the other keys) so the secure default holds. If a `.env` with a real value must exist for local testing, keep it out of the delivered artifact and document that disabling SSL is opt-in only. Effort: trivial. Priority: mandatory — an insecure-by-default network posture that also contradicts the documentation.

---

### SEC-003: URL log-sanitizer uses a fragile blocklist and ignores path-embedded tokens, risking signed-CDN-URL leakage in INFO logs

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/utils/url_sanitizer.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** `_strip_auth_params` protects logs by removing a *fixed allowlist-of-known-bad*
query parameter names. This blocklist approach fails open in two ways: (1) it only inspects
the query string, so any auth token embedded in the URL **path** (common for VK signed HLS
segment/playlist URLs, e.g. `.../<signature>/index.m3u8`) is logged verbatim; (2) VK CDN
signed URLs frequently use parameter names that are **not** in `AUTH_PARAMS` (e.g. `siv`,
`extra`, `long_chunk`, `srcIp`, `clientType`), which therefore survive sanitization. The
sanitized m3u8 URL is emitted at **INFO** level (`starting_ffmpeg_download`,
`starting_ytdlp_download`), so a signed, reusable stream URL can end up in normal logs / log
files.

**Evidence:**
- `url_sanitizer.py:6-27` — hardcoded `AUTH_PARAMS` frozenset; anything not listed is preserved (`url_sanitizer.py:54-56`).
- `url_sanitizer.py:43-44` — returns URL unchanged if there is no `?`, so path-only tokens are never touched.
- `downloader.py:148-154` > `logger.info("starting_ffmpeg_download", url=_strip_auth_params(m3u8_url), ...)` (INFO level, token-bearing m3u8).
- `downloader.py:347-352` > `logger.info("starting_ytdlp_download", url=_strip_auth_params(video_url), ...)`.
- With `log_file` set, `config.py:118` uses `JSONRenderer` > leaked URLs are persisted to disk.

**Recommendation:** Switch to an allowlist strategy that logs only the scheme + host + a redacted path (e.g. keep host, replace path segments and all query values with `***`), rather than trying to enumerate every sensitive parameter. At minimum, drop the entire query string when logging and redact obvious high-entropy path segments. Effort: small. Priority: mandatory for secret-hygiene, though impact is limited to log readers.

---

### SEC-004: Cookies and headers passed to ffmpeg via command-line arguments are exposed in process listings

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `_build_ffmpeg_cmd` embeds the full `Cookie:` header (session cookies) and
`User-Agent`/`Referer` into the `-headers` argv value passed to `ffmpeg`. Command-line
arguments are visible to any other user on the host via process listings (Task Manager,
`Get-Process`, `/proc/<pid>/cmdline`, `ps -ef`). On a shared/multi-user machine another local
user could read the live VK session cookies while a download runs.

**Evidence:**
- `downloader.py:108-124`:
  ```python
  cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""
  headers = f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n{cookie_part}"
  cmd = ["ffmpeg", "-y", ..., "-headers", headers, "-i", m3u8_url, ...]
  ```
- Invoked via `asyncio.create_subprocess_exec(*cmd, ...)` (`downloader.py:158-162`) — argv, not stdin.

**Recommendation:** For single-user CLI usage this is low risk. If hardening for shared hosts is desired, prefer passing headers/cookies to ffmpeg via a file-based mechanism or write cookies to a `0o600` temp file (as the yt-dlp path already does) rather than argv. Effort: small. Priority: advisory.

---

### SEC-005: ffmpeg `-headers` built by unescaped string concatenation allows CRLF header injection via cookie values

| Field | Value |
|-------|-------|
| **ID** | SEC-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** The ffmpeg `-headers` value is assembled by concatenating cookie
name/value pairs into a `\r\n`-delimited string. Cookie values originate from the browser
context (`page.context.cookies()`) and are joined without any validation/escaping
(`f"{name}={value}"`). If a cookie name or value ever contained a CR/LF sequence, it would
inject additional (attacker-influenced) request headers into ffmpeg's HTTP requests. Real
browser cookies almost never contain raw CRLF, so exploitability is low, but the code trusts
externally sourced data when constructing a protocol-sensitive string.

**Evidence:**
- `extractor.py:238-246` — `_format_cookies_for_ffmpeg` joins `f"{name}={value}"` with `"; "`, no sanitization of `name`/`value`.
- `downloader.py:108-109` — cookie string spliced directly into the CRLF-separated header block.

**Recommendation:** Strip/reject `\r` and `\n` from cookie names/values before building the header string (or drop malformed cookies). Effort: trivial. Priority: advisory.

---

### SEC-006: Output-path traversal check is a naive substring test that both over-blocks and under-protects

| Field | Value |
|-------|-------|
| **ID** | SEC-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/utils/security.py` |
| **Classification** | advisory |

**Description:** `validate_output_path` rejects paths purely because the raw string contains
`".."`. This is simultaneously too strict and too weak: (1) it rejects legitimate paths that
merely contain `..` (e.g. a directory literally named `my..videos`), and (2) it does not
constrain absolute paths at all — an absolute destination outside any intended base
(`C:\Windows\...`, `/etc/...`) passes, since the only remaining control is a *warning* when
the path happens to be inside the repo root. For this local single-user CLI the practical risk
is low (the user supplies their own `-o`), but the function's name implies a containment
guarantee it does not provide.

**Evidence:**
- `security.py:41-47`:
  ```python
  path_str = str(path)
  if ".." in path_str:
      raise DownloadError(f"Path traversal detected in output path: {path}")
  resolved = path.resolve()
  ```
- `security.py:49-61` — only *warns* when the resolved path is inside the repo root; no rejection of arbitrary absolute paths.

**Recommendation:** If real containment is intended, resolve the path and assert it is within an explicit allowed base directory using `Path.resolve()` + `is_relative_to(base)`, instead of substring matching. Otherwise, rename/clarify the function so callers do not assume traversal protection that is not enforced. Effort: small. Priority: advisory.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 3 |

## Mandatory Fixes

- **SEC-001 (HIGH)** — Delete/relocate the plaintext session-cookie file after use and add `*_cookies.txt` to `.gitignore`.
- **SEC-002 (MEDIUM)** — Remove `VKDOWNLOADER_SSL_VERIFY=false` from the shipped `.env`; restore the documented secure default.
- **SEC-003 (MEDIUM)** — Redact path + all query values when logging URLs instead of relying on a parameter-name blocklist.

## Advisory Recommendations

- **SEC-004 (LOW)** — Avoid passing cookies/headers to ffmpeg via argv on shared hosts.
- **SEC-005 (LOW)** — Sanitize CR/LF out of cookie name/value before building ffmpeg headers.
- **SEC-006 (LOW)** — Replace the naive `".."` traversal check with proper base-dir containment, or clarify the guarantee.

## Doc Updates Needed

- **SEC-002** — Reconcile `README.md:29` ("SSL verification enabled by default") with the actual shipped `.env`. Either fix the `.env` (preferred) or document that the delivered `.env` disables SSL.
