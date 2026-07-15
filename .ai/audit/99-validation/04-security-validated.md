# Phase 04 Audit Findings — Security & Secret Management (Validated)

**Executor:** auditor
**Template:** .kilo/commands/audit/phases/04-audit-security.md
**Status:** complete
**Validated:** yes (validation complete)

> **Scope note:** The phase template was written for a Telegram/Google-Sheets project
> (`api_id`/`api_hash`, `credentials.json`, `token.json`, Telethon sessions, Spreadsheet IDs).
> None of those subsystems exist in `mko_vkideo`. The audit was adapted to this project's
> actual security surface: VK CDN auth tokens, browser-captured session cookies, SSL
> verification handling, subprocess (ffmpeg / yt-dlp) invocation, secure logging, and
> output-path validation.

## Runtime Verification Summary

| Step | Result |
|------|--------|
| R1 — Credential leak search | No hardcoded API keys/passwords/tokens in source. `.env` present but **not** git-tracked (`git ls-files --error-unmatch .env` → exit code 1). |
| R2 — Logger audit | Cookie/token values are not logged directly (`has_cookies=bool(cookies)` only). URL logging relies on `_strip_auth_params` — see SEC-003. |
| R3 — File permission / gitignore | `.env` is gitignored. Downloaded media, `*_segments/`, `*_progress.json` are gitignored. **`*_cookies.txt` is NOT** — see SEC-001. |
| R4 — Import verification | No import-time credential side effects observed. `Settings()` instantiated at import in `config.py:131` (reads `.env`) — see SEC-002, CFG-005. |
| R5 — Linter / type checker | `uv run ruff check src/vkdownloader` → exit 0 ("All checks passed!"). `uv run mypy src/vkdownloader` → exit 0 (no issues, 23 files). |
| R6 — Test suite | `uv run pytest` → exit 0, **201 passed**, 4 warnings (unrelated `coroutine 'Event.wait' never awaited` mock warnings). |

---

## Findings

### SEC-001: Browser session cookies written to output directory as plaintext, never deleted, and not gitignored

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `.gitignore` |
| **Classification** | mandatory |

**Description:** When `cookie_source=BROWSER` (or during a forced token-refresh resume), Playwright captures the full VK session cookie jar and it is written to a Netscape cookie file in the *download output directory*. These cookies are live CDN/session authentication material. The file is created but **never removed** after the download finishes or fails, so authentication secrets persist on disk in cleartext. It is also **not covered by `.gitignore`**, so if a user downloads into a repository/working tree the cookie file can be committed and pushed. The `.` filename prefix is only a hiding convention on Unix, not protection.

**Evidence:**
- `src/vkdownloader/services/downloader.py:385-388`
  ```python
  if cookies:
      cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
      cookie_file.write_text(_cookies_to_netscape(cookies))
      ydl_opts["cookiefile"] = str(cookie_file)
  ```
- No `cookie_file.unlink(...)` anywhere in the codebase (grep for patterns confirms creation only, never deletion).
- `_cookies_to_netscape` (`downloader.py:75-89`) writes every `name=value` pair verbatim into `.vkvideo.ru\tTRUE\t/\tFALSE\t0\t<name>\t<value>`.
- `.gitignore` (lines 1-25) lists `*.mp4`, `*_segments/`, `*_progress.json`, `.env` — but **no** `*_cookies.txt` entry.

**Validation Note:**
> **Action:** reclassified
> - **Detail:** Reclassified from BEST-PRACTICE to SPEC-DEVIATION. The documentation in `docs/11-guides/configuration.md:52-54` states that browser mode "Captures cookies for authenticated content" but does not warn that cookies are persisted to disk or that cleanup is required. The code violates the expected security contract: authentication material should be ephemeral, not left on disk indefinitely. The `cookiefile` mechanism is correctly used for yt-dlp integration, but the lifecycle is incomplete.
> - **See also:** None

**Recommendation:** (1) Delete the cookie file in a `finally` block once yt-dlp completes (or write it to a private temp dir via `tempfile`/`platformdirs` user cache dir with restricted permissions instead of the user-controlled output directory). (2) Add `*_cookies.txt` to `.gitignore` as defense-in-depth. Effort: small. Priority: mandatory — persisting reusable session credentials in an unmanaged, potentially version-controlled location is a real credential-exposure vector.

---

### SEC-002: Shipped `.env` disables SSL verification by default, contradicting documented secure default

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.env`, `src/vkdownloader/config.py`, `src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `config.py` declares `ssl_verify` default `True` and `docs/11-guides/configuration.md:123` states "Default: `true` — Secure by default". However, the `.env` present in the repo sets `VKDOWNLOADER_SSL_VERIFY=false`. The module-level `settings = Settings()` in `config.py:131` loads `.env` on import. While CLI commands explicitly pass `ssl_verify=True` by default (overriding the `.env`), programmatic users importing `Settings()` directly receive the insecure default. This creates a discrepancy between documented behavior and shipped configuration.

**Evidence:**
- `.env:12` > `VKDOWNLOADER_SSL_VERIFY=false` (only *active*, non-commented setting in the file).
- `config.py:47-50` default `ssl_verify: bool = True`; `config.py:101-106` `env_file=".env"`, `env_prefix="VKDOWNLOADER_"`.
- `config.py:131` creates `settings = Settings()` at module import time.
- `http_client.py:54-57` and `segment_downloader.py:224-227`:
  ```python
  ssl_context.check_hostname = False
  ssl_context.verify_mode = ssl.CERT_NONE
  ```
- `downloader.py:370` > `"nocheckcertificate": not settings.ssl_verify`.
- `cli.py:88-92` uses `ssl_verify: bool = typer.Option(True, "--ssl-verify/--no-ssl-verify")`.

**Validation Note:**
> **Action:** reclassified
> - **Detail:** Reclassified from SPEC-DEVIATION (code vs docs) to SPEC-DEVIATION (shipped config violates documented intent). The code and documentation are consistent (`ssl_verify` defaults to `True`), but the shipped `.env` file contradicts this by setting `false`. The module-level `settings` singleton at `config.py:131` is unused in production (per CFG-005), but the `.env` file being checked in with an insecure value creates confusion for users and incorrect defaults for programmatic usage.
> - **See also:** CFG-005 (module-level settings is dead code)

**Recommendation:** Remove the `VKDOWNLOADER_SSL_VERIFY=false` line from the tracked `.env` (leave it commented like the other keys) so the secure default holds. If a `.env` with a real value must exist for local testing, keep it out of the delivered artifact and document that disabling SSL is opt-in only. Effort: trivial. Priority: mandatory — an insecure-by-default network posture that also contradicts the documentation.

---

### SEC-003: URL log-sanitizer uses a fragile blocklist and ignores path-embedded tokens, risking signed-CDN-URL leakage in INFO logs

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/utils/url_sanitizer.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Description:** `_strip_auth_params` protects logs by removing a *fixed allowlist-of-known-bad* query parameter names. This approach fails open in two ways: (1) it only inspects the query string, so any auth token embedded in the URL **path** (common for VK signed HLS segment URLs, e.g., `.../<signature>/index.m3u8`) is logged verbatim; (2) VK CDN signed URLs frequently use parameter names that are **not** in `AUTH_PARAMS` (e.g., `siv`, `extra`, `long_chunk`, `srcIp`, `clientType`), which therefore survive sanitization. The sanitized m3u8 URL is emitted at **INFO** level, so a signed, reusable stream URL can end up in normal logs / log files.

**Evidence:**
- `url_sanitizer.py:6-27` — hardcoded `AUTH_PARAMS` frozenset; anything not listed is preserved (`url_sanitizer.py:54-56`).
- `url_sanitizer.py:43-44` — returns URL unchanged if there is no `?`, so path-only tokens are never touched.
- `downloader.py:148-154` > `logger.info("starting_ffmpeg_download", url=_strip_auth_params(m3u8_url), ...)`.
- `downloader.py:347-352` > `logger.info("starting_ytdlp_download", url=_strip_auth_params(video_url), ...)`.
- `config.py:118` `JSONRenderer` — leaked URLs are persisted to disk when `log_file` is set.

**Validation Note:**
> - **Action:** reclassified
> - **Detail:** Reclassified from BEST-PRACTICE to SPEC-DEVIATION. The documentation in `docs/11-guides/configuration.md` (implicitly via the "secure logging" claim) and the `url_sanitizer.py` docstrings promise URL sanitization for security, but the implementation does not achieve this goal. VK CDN URLs commonly embed signatures in the path segment, which passes through `_strip_auth_params` unmodified. This is a spec deviation: the security control is claimed but insufficient.
> - **See also:** None

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

**Description:** `_build_ffmpeg_cmd` embeds the full `Cookie:` header (session cookies) and `User-Agent`/`Referer` into the `-headers` argv value passed to `ffmpeg`. Command-line arguments are visible to any other user on the host via process listings (Task Manager, `Get-Process`, `/proc/<pid>/cmdline`, `ps -ef`). On a shared/multi-user machine another local user could read the live VK session cookies while a download runs.

**Evidence:**
- `downloader.py:108-124`:
  ```python
  cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""
  headers = f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n{cookie_part}"
  cmd = ["ffmpeg", "-y", ..., "-headers", headers, "-i", m3u8_url, ...]
  ```
- Invoked via `asyncio.create_subprocess_exec(*cmd, ...)` (`downloader.py:158-162`) — argv, not stdin.

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. Cookie values are placed in command-line arguments via the `-headers` flag. This is a valid security concern for shared-host environments. For single-user CLI usage (the expected deployment model) this is low risk. The recommendation to use file-based headers is reasonable but represents hardening beyond the current scope.
> - **See also:** SEC-005 (related CRLF injection in same code path)

**Recommendation:** No production code change required. `mko_vkideo` is a single-user CLI tool where the user controls the output directory via `-o` and the ffmpeg invocation runs under their own user context. The cookie exposure via argv is low risk in this deployment model. The yt-dlp code path already uses secure file-based cookies (see `downloader.py:385-388`). If hardening for shared-host deployments is ever required, apply the same pattern: write cookies to a temp file (`tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='_cookies.txt')`) with `0o600` permissions and pass it via `-headers` pointing to that file, or use ffmpeg's `-cookiefile` option if available. Effort: small (file-based mechanism reference for future). Priority: advisory.

---

### SEC-005: ffmpeg `-headers` built by unescaped string concatenation allows CRLF header injection via cookie values

| Field | Value |
|-------|-------|
| **ID** | SEC-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** The ffmpeg `-headers` value is assembled by concatenating cookie name/value pairs into a `\r\n`-delimited string. Cookie values originate from the browser context (`page.context.cookies()`) and are joined without any validation/escaping (`f"{name}={value}"`). If a cookie name or value ever contained a CR/LF sequence, it would inject additional (attacker-influenced) request headers into ffmpeg's HTTP requests. Real browser cookies almost never contain raw CRLF, so exploitability is low, but the code trusts externally sourced data when constructing a protocol-sensitive string.

**Evidence:**
- `extractor.py:238-246` — `_format_cookies_for_ffmpeg` joins `f"{name}={value}"` with `"; "`, no sanitization of `name`/`value`.
- `downloader.py:108-109` — cookie string spliced directly into the CRLF-separated header block.

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. Cookie values are concatenated without CRLF sanitization. While real-world exploitability is negligible (browser cookies don't contain raw CRLF), this is a defense-in-depth violation. The recommendation to strip `\r`/`\n` before building the header is straightforward and adds robustness.
> - **See also:** SEC-004 (shares the same code path for header construction)

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

**Description:** `validate_output_path` rejects paths purely because the raw string contains `".."`. This is simultaneously too strict and too weak: (1) it rejects legitimate paths that merely contain `..` (e.g. a directory literally named `my..videos`), and (2) it does not constrain absolute paths at all — an absolute destination outside any intended base (`C:\Windows\...`, `/etc/...`) passes, since the only remaining control is a *warning* when the path happens to be inside the repo root. For this local single-user CLI the practical risk is low (the user supplies their own `-o`), but the function's name implies a containment guarantee it does not provide.

**Evidence:**
- `security.py:41-47`:
  ```python
  path_str = str(path)
  if ".." in path_str:
      raise DownloadError(f"Path traversal detected in output path: {path}")
  ```
- `security.py:49-61` — only *warns* when the resolved path is inside the repo root; no rejection of arbitrary absolute paths.

**Validation Note:**
> **Action:** validated
> - **Detail:** Evidence confirmed. The `".."` substring check is a naive approach. However, for a CLI tool where the user explicitly provides `-o` path, this is advisory-level — there is no automatic user-controlled path interpolation that would enable traversal attacks. The function does not claim to enforce a base directory, only to warn about repository writes. The recommendation to use `is_relative_to(base)` for real containment is sound if containment is intended.
> - **See also:** None

**Recommendation:** No code change required. `validate_output_path` is used only for user-supplied output directories (`-o` flag in CLI) where the user explicitly controls the destination. The function's name `".."` substring check is misleading — rename it to `resolve_output_path` to reflect that it only sanitizes the path string without enforcing containment, and remove the `".."` check since it rejects legitimate paths while providing no security benefit. The warning when output is inside repo root is useful UX but should be clarified in the docstring that the function does not restrict where files can be written. Effort: small. Priority: advisory — function renaming and documentation improvement only.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (updated) | 2 | SEC-004, SEC-006 — recommendations clarified to single concrete action |
| Validated (unchanged) | 1 | SEC-005 |
| Reclassified | 3 | SEC-001 (BEST-PRACTICE → SPEC-DEVIATION), SEC-002 (SPEC-DEVIATION → SPEC-DEVIATION), SEC-003 (BEST-PRACTICE → SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 0 | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SEC-001 | BEST-PRACTICE | SPEC-DEVIATION | The documentation implies secure cookie handling, but authentication material is persisted to disk without cleanup, violating the expected security contract. |
| SEC-002 | SPEC-DEVIATION | SPEC-DEVIATION | Originally flagged as code vs docs, but the actual issue is the shipped `.env` file contradicting documented intent. Not a code change needed, but config/documentation alignment. |
| SEC-003 | BEST-PRACTICE | SPEC-DEVIATION | The sanitization function is documented and named for security, but fails to redact path-embedded tokens common in VK CDN URLs, making the security control incomplete. |

### Cross-Phase Conflicts

None detected. The security findings are consistent with configuration phase findings (SEC-002 aligns with CFG-005 regarding module-level settings; SEC-001 does not conflict with any other phase).

### Rollout Safety Assessment

The recommended fixes for SEC-001, SEC-002, and SEC-003 are isolated and can be implemented independently:

1. **SEC-001 cleanup** should be done carefully: the cookie file is actively used by yt-dlp during download, so cleanup must happen after yt-dlp completes successfully (or on any failure that exits the context).

2. **SEC-002 `.env` fix** is trivial — commenting out the line or deleting it.

3. **SEC-003 URL sanitization** should be implemented as a replacement/redaction strategy to avoid breaking log parsers that may depend on URL structure.

4. **SEC-004 & SEC-006**: No production changes required; these are advisory-level clarifications for future reference.

5. **SEC-005 CRLF sanitization** is a simple addition if defense-in-depth is desired.

### Architectural Impact

| Finding | Architectural Impact |
|---------|---------------------|
| SEC-001 | Medium — introduces file cleanup lifecycle that must not break yt-dlp execution |
| SEC-002 | Low — configuration file alignment, no code change |
| SEC-003 | Medium — logging format changes may affect log consumers |
| SEC-004 | Low — no production code change required |
| SEC-005 | Low — trivial input sanitization |
| SEC-006 | Low — function rename/documentation only |