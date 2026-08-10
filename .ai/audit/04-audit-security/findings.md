# Phase 04 Audit Findings -- Security & Secret Management

**Executor:** auditor (Senior architecture auditor)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/04-audit-security.md
**Status:** complete
**Validated:** no
**Problems-only:** yes (passing checks are omitted per phase output mode)

**System under audit:** vkdownloader v0.1.0 -- VK Video Downloader CLI (Python 3.12, uv, MIT).
Security surface audited: credential/temp-file handling (`utils/security.py`, `services/cookies.py`,
`services/downloader.py` cookie/temp-file helpers), config loading (`config.py` / `.env`),
logging of secrets (`_strip_auth_params`, `warn_unknown_env_vars`), subprocess argument
construction (yt-dlp / ffmpeg), path-traversal validation, and VCS ignore hygiene (`.gitignore`).

Reference docs: `docs/01-tools/vkdownloader-overview.md`, `docs/11-guides/configuration.md`,
`docs/99-reference/cli-reference.md` / `cli-reference-clean.md`, `docs/11-guides/vkdownloader-limitations.md`.

---

## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 -- Credential Leak Search | grep `api_key`, `access_token`, `refresh_token`, `private_key`, `client_secret`, `password=` across `*.py`,`*.json`,`*.yaml`,`*.yml`,`*.toml`,`*.env`,`*.example` | PASS -- no hardcoded secrets | Zero matches in `src/`. `.env` is locally untracked, contains only commented placeholders; `.env.example` likewise. `tests/test_hls_downloader.py:959` uses fake fixture `access_token=mytoken` (not a real value). |
| R2 -- Logger Audit | grep all `logger.*` calls; check for `cookies`/`cookie_str`/`headers`/`settings` logged | PASS -- no direct secret values logged | `warn_unknown_env_vars` logs env-var *names* only (`var=key`). `_format_cookies_for_ffmpeg`/`perform_download`/`download_with_ffmpeg` log `has_cookies=bool(cookies)` / `cookie_source=str(enum)`, never cookie contents. Residual gap: unsanitized subprocess output (SEC-002). |
| R3 -- File Permission / Ignore Check | `git check-ignore .env`; inspect `.gitignore` | PARTIAL -- `.env` ignored; `.env.*` not covered | `git check-ignore .env` exit 0 (ignored). `git check-ignore .env.local` exit 1 (NOT ignored). `.gitignore:28` = `.env` (exact match). Only `.env.example` tracked. |
| R4 -- Import Verification | import all secret-handling modules | PASS -- no import-time leaks | `from vkdownloader.config import Settings`; `from vkdownloader.services.cookies import ...`; `from vkdownloader.services.downloader import _create_temp_cookie_file, _temp_headers_file`; `from vkdownloader.services.extractor import VKVideoExtractor`; `from vkdownloader.utils.security import validate_output_path`; `from vkdownloader.utils.url_sanitizer import _strip_auth_params`. All import cleanly. |
| R5 -- Linter & Type Checker | `uv run ruff check src/vkdownloader/`; `ruff format --check src/vkdownloader/`; `uv run mypy src/vkdownloader` | PARTIAL -- linter PASS; format FAIL; mypy FAIL | `ruff check`: "All checks passed!". `ruff format --check`: "1 file would be reformatted" -> `services/downloader.py` (pre-existing, tracked CLI-005 phase-01). `mypy`: `utils/correlation.py:55` unused `type: ignore` (pre-existing, tracked CLI-004 phase-01). Neither is security-relevant to this phase. |
| R6 -- Test Suite | `uv run pytest` | PASS -- 325 passed | `test_security.py` (21), `test_config.py` (17), `test_url_sanitizer.py` (8), `test_extractor.py` (24) all pass. |

---

## Findings

### SEC-001: Signed CDN tokens passed as plaintext ffmpeg command-line arguments

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`HLSDownloader.download_with_ffmpeg`); `docs/01-tools/vkdownloader-overview.md:151` |
| **Classification** | mandatory |

**Description:** The ffmpeg download path passes the HLS m3u8 playlist URL -- containing expiration-signed CDN tokens (per `vkdownloader-limitations.md:49`: "m3u8 URLs contain expiring tokens, typically valid 1-2 hours") -- directly as `-i <m3u8_url>`. This exposes signed CDN tokens in OS process listings (`ps`, `/proc/<pid>/cmdline`, `htop`, `docker inspect`) for the lifetime of the ffmpeg subprocess. The docs advertise process-listing protection for cookies (overview.md:151) but the same protection is NOT applied to the m3u8 URL. yt-dlp has no such exposure: it receives only the original VK video URL (`downloader.py:801`), without embedded tokens.

**Evidence:**
- `src/vkdownloader/services/downloader.py:441`: `cmd.extend(["-i", m3u8_url, "-c", "copy", str(output_file)])` -- raw `m3u8_url` as CLI arg.
- `src/vkdownloader/services/downloader.py:436-437`: `"-headers", f"@{headers_file}"` -- cookies correctly protected via `@file`, but the URL is not.
- `docs/01-tools/vkdownloader-limitations.md:49,64`: confirms m3u8 URLs contain expiring tokens; cookies protected via `@file` from process listings.
- `docs/01-tools/vkdownloader-overview.md:151`: documented "Secret-safe ffmpeg cookie passing" claim (accurate for cookies, silent about URL tokens).
- `src/vkdownloader/utils/url_sanitizer.py:6-25` (`_strip_auth_params`) is applied to all URL logging but NOT to the `-i` argument.

**Recommendation:** Route the m3u8 URL through ffmpeg's `@file` argfile syntax (`ffmpeg @argfile`) or switch to the yt-dlp Python API so no signed token enters a process argument vector. Update overview.md:151 to accurately scope protection (cookies only). Effort: medium.

---

### SEC-002: Unsanitized yt-dlp/ffmpeg subprocess output logged verbatim on failure

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`, `HLSDownloader.download_with_ffmpeg`); `src/vkdownloader/utils/url_sanitizer.py` (`_strip_auth_params`) |
| **Classification** | mandatory |

**Description:** When yt-dlp or ffmpeg exits non-zero, the entire captured stdout+stderr is logged verbatim as structured `error=error_msg` without redaction. URL fields in those same log calls ARE sanitized via `_strip_auth_params`, but subprocess output is not. yt-dlp and ffmpeg routinely echo request URLs in diagnostic output; yt-dlp's stdout includes the URL it processed and ffmpeg's stderr typically echoes the input (`-i`) URL on connection failures. Because the ffmpeg input URL is the signed m3u8 URL (SEC-001), a failed ffmpeg download logs the full signed CDN token into structured logs -- which persists to disk if `VKDOWNLOADER_LOG_FILE` is set (SEC-003).

**Evidence:**
- `src/vkdownloader/services/downloader.py:878-885` (yt-dlp): `error_msg = output_data.decode()` then `logger.error("download_failed", url=_strip_auth_params(video_url), error=error_msg)` -- `error_msg` NOT sanitized.
- `src/vkdownloader/services/downloader.py:518-525` (ffmpeg): `error_msg = stderr_data.decode()` then `logger.error("ffmpeg_download_failed", url=_strip_auth_params(m3u8_url), error=error_msg)` -- `error_msg` NOT sanitized.
- `src/vkdownloader/services/downloader.py:233-248` (`_echo_ytdlp_line`): yt-dlp output lines written directly to `sys.stderr` (called at lines 833, 856) without redaction.

**Recommendation:** Apply `_strip_auth_params` (or equivalent URL/token redactor) to subprocess output before logging; at minimum strip query-parameter values from any URL in `error_msg` and redact the temp cookie file path. Consider logging subprocess output at `debug` level only. Effort: small.

---

### SEC-003: Log file created with default umask, not owner-only permissions

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` (`setup_logging`, lines 228-236) |
| **Classification** | advisory |

**Description:** When `VKDOWNLOADER_LOG_FILE` is set, `setup_logging()` creates the log file via `logging.FileHandler(settings.log_file)` with no explicit mode. `FileHandler` opens with `open(path, "a")` under the process umask, yielding `0o644` on a standard POSIX umask (`0o022`) -- group/world-readable. The project already enforces `0o600` for credential files (`cookies.py:72` `os.open(..., 0o600)`; `downloader.py:87` `tempfile.mkstemp`), but not for log files. The log file may contain unsanitized subprocess output (SEC-002), tracebacks, and cookie file temp paths. Verified at runtime: `FileHandler` uses raw umask.

**Evidence:**
- `src/vkdownloader/config.py:228-236`: `logging.FileHandler(settings.log_file)` inside `logging.basicConfig` -- no `mode=` / explicit permission.
- `src/vkdownloader/config.py:107-110`: `log_file` field; `expand_tilde_paths` (config.py:119-131) does not set permissions.
- `src/vkdownloader/utils/security.py` (`validate_output_path`) is not applied to `log_file` -- no path containment check on log location.

**Recommendation:** Create the log file with explicit `0o600` before `FileHandler` (e.g. `fd = os.open(..., 0o600); handler = logging.FileHandler(os.fdopen(fd, "a"))`), or subclass `FileHandler` to enforce owner-only mode. Effort: trivial.

---

### SEC-004: `.gitignore` covers `.env` but not `.env.*` variants -- risk of accidental secret commit

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.gitignore` (line 28); `.env` / `.env.example` |
| **Classification** | mandatory |

**Description:** `.gitignore:28` contains only `.env` (exact match). It does not cover `.env.local`, `.env.development`, `.env.production`, `.env.backup`, or any `.env.*` variant. The project uses pydantic-settings with `env_file=".env"` (`config.py:160`), so only `.env` loads by default, but user habit and the `.env.example` template commonly lead to `.env.*` files. An untracked `.env.*` holding real credentials could be accidentally committed via `git add .`, leaking secrets to the remote. Verified: `git check-ignore .env` exits 0; `git check-ignore .env.local` exits 1 (NOT ignored).

**Evidence:**
- `.gitignore:28`: `.env` (no wildcard).
- `git ls-files '.env*'` shows only `.env.example` tracked.
- `git check-ignore .env` -> exit 0 (ignored).
- `git check-ignore .env.local` -> exit 1 (NOT ignored; would be committed if it existed).

**Recommendation:** Use the standard dotenv pattern: `.env*` plus `!.env.example` (re-include the template). Effort: trivial.

---

### SEC-005: Dead-code `_write_netscape_cookie_file` with divergent permission semantics

| Field | Value |
|-------|-------|
| **ID** | SEC-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/cookies.py` |
| **Classification** | advisory |

**Description:** `services/cookies.py` defines `_write_netscape_cookie_file(path, cookies_input)` (lines 58-75) with `os.open(..., 0o600)` and a docstring explaining the owner-only rationale. It is exported in `cookies.py:__all__` (line 77) and re-exported via `downloader.py:__all__` (line 369). Grep across `src/` and `tests/` shows **zero call sites** -- it is never invoked. The live cookie-file path is `_create_temp_cookie_file` in `services/downloader.py` (lines 71-95, called at 318, 321), which uses `tempfile.mkstemp` (also `0o600` on POSIX). Two functions writing the same Netscape-format file with different permission mechanisms (`os.open` vs `mkstemp`) creates maintenance ambiguity; a developer may pick the dead `__all__` function expecting it to be canonical, receiving different behavior (explicit `path`, not a temp file). Per dead-code policy, investigate intended use (future API) vs. leftover (remove).

**Evidence:**
- `src/vkdownloader/services/cookies.py:58-75` -- function definition.
- `src/vkdownloader/services/cookies.py:77` -- `__all__`.
- `src/vkdownloader/services/downloader.py:369` -- re-exported in `__all__`.
- Grep for `_write_netscape_cookie_file` across `src/` and `tests/`: only the definition and two `__all__` references; no invocations.
- `src/vkdownloader/services/downloader.py:71` -- `_create_temp_cookie_file` (used path): `_cookies_to_netscape(cookies)` then `tempfile.mkstemp`.

**Recommendation:** Either remove `_write_netscape_cookie_file` and both `__all__` entries, or document its intended use and converge on one permission approach. Effort: small.

---

### SEC-006: `validate_output_path` `..`-string check is a no-op for pre-resolved paths

| Field | Value |
|-------|-------|
| **ID** | SEC-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/utils/security.py:44-52, 89-92`; `src/vkdownloader/config.py:119-131`; `src/vkdownloader/services/downloader.py:605`; `src/vkdownloader/services/segment_downloader.py:855`; `src/vkdownloader/models/dtos.py` |
| **Classification** | advisory |

**Description:** `validate_output_path()` detects traversal via `".." in str(path)` on the **raw, unresolved** string **before** `path.resolve()` (security.py:44-52). Two callers pre-resolve the path before validation, making the `..` check dead: (1) `config.py:119-131` `expand_tilde_paths` runs `v.expanduser().resolve()` on `download_dir`/`log_file` during model construction; (2) `security.py:90` `_resolve_output_file` calls `Path(output_path).resolve()` before `validate_output_path` (security.py:92); (3) `downloader.py:605` passes an already-resolved `output_file`. Only `segment_downloader.py:855` passes a raw unresolved path (via the `HLSDownloadRequest` DTO at `dtos.py:21`, whose `output_file: Path` field has no path validator). Not exploitable today (inputs from trusted config/CLI; `video.title` sanitized by `_sanitize_title`), but gives false defense-in-depth.

**Evidence:**
- `src/vkdownloader/utils/security.py:44-52`: `path_str = str(path); if ".." in path_str: raise ...; resolved = path.resolve()`.
- `src/vkdownloader/config.py:119-131`: `expand_tilde_paths` resolves before any `validate_output_path` call.
- `src/vkdownloader/utils/security.py:89-92`: `_resolve_output_file` resolves then validates.
- `src/vkdownloader/services/downloader.py:605`: `validated_output = validate_output_path(output_file, warning=False)`.
- `src/vkdownloader/services/segment_downloader.py:855`: `output_file = validate_output_path(request.output_file)` -- the only unresolved-path call.
- `src/vkdownloader/models/dtos.py:21`: `HLSDownloadRequest.output_file: Path` -- no path containment validator on the DTO.

**Recommendation:** Make the traversal check resolve-first and validate against a safe base dir (e.g. reject resolved paths containing `..` or outside `settings.download_dir`), or document that `validate_output_path` requires an unresolved path. Effort: small.

---

### SEC-007: CRLF injection in `_cookies_to_netscape` not sanitized (inconsistent with `_format_cookies_for_ffmpeg`)

| Field | Value |
|-------|-------|
| **ID** | SEC-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/cookies.py:26-55` (`_cookies_to_netscape`); `src/vkdownloader/services/extractor.py:252-263` (`_format_cookies_for_ffmpeg` -- sanitized counterpart) |
| **Classification** | advisory |

**Description:** `_cookies_to_netscape()` writes Playwright `Cookie` name/value pairs directly into the tab-separated Netscape cookie-file format without stripping CRLF or control characters (`cookies.py:38-48`). A name/value containing `\r`/`\n` produces extra lines a parser (including yt-dlp via `--cookies`) reads as additional cookie entries -- an HTTP header/response-splitting-style injection. The codebase already recognizes this exact vulnerability class and fixes it for the ffmpeg path: `_format_cookies_for_ffmpeg` strips `\r`/`\n` from name and value (`extractor.py:260-261`) with a docstring citing "prevent header injection." The same protection is absent from `_cookies_to_netscape`, the function used for the yt-dlp `--cookies` path.

**Evidence:**
- `src/vkdownloader/services/cookies.py:38-48`: `name = cookie_item["name"]` / `value = cookie_item["value"]` -- raw, no CRLF strip; `lines.append(f"{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}")`.
- `src/vkdownloader/services/extractor.py:260-261`: `cookie.get("name", "").replace("\r", "").replace("\n", "")` -- CRLF stripped (sanitized counterpart).
- Runtime: a value `abc\r\nSet-Cookie: evil=hack` passed to `_cookies_to_netscape` yields a multi-line file where `Set-Cookie: evil=hack` appears as a separate (injected) cookie entry.

**Recommendation:** Apply the same CRLF stripping in `_cookies_to_netscape` (mirror `_format_cookies_for_ffmpeg`), or reject/strip all control characters from name and value. Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 (SEC-001, SEC-002) |
| LOW | 5 (SEC-003, SEC-004, SEC-005, SEC-006, SEC-007) |
| **Total** | **7** |

## Mandatory Fixes

- **SEC-001 (MEDIUM):** Stop passing the signed m3u8 URL as a plaintext CLI arg to ffmpeg. Route it through an ffmpeg argfile (`@file`) or switch to the yt-dlp Python API so no signed CDN token appears in `ps`/`/proc` output. Update `vkdownloader-overview.md:151` to scope protection (cookies only).
- **SEC-002 (MEDIUM):** Sanitize captured yt-dlp/ffmpeg stdout/stderr with `_strip_auth_params` or equivalent before logging as `error=error_msg`, so signed URLs and cookie file paths do not persist in structured logs.
- **SEC-004 (LOW):** Extend `.gitignore` to cover `.env.*` variants (`.env*` + `!.env.example`).

## Advisory Recommendations

- **SEC-003 (LOW):** Create log files with explicit `0o600` in `setup_logging()` instead of the process umask, so logs (which may contain unsanitized subprocess output) are not world-readable on shared/mult-user systems.
- **SEC-005 (LOW):** Investigate and either remove or document dead `_write_netscape_cookie_file` in `services/cookies.py` (zero callers; live path is `_create_temp_cookie_file`). Eliminates a divergent, confusing cookie-file code path.
- **SEC-006 (LOW):** Make `validate_output_path` resolve-first and validate against a safe base dir, so the `..` traversal check is effective regardless of caller pre-resolution.
- **SEC-007 (LOW):** Add CRLF stripping to `_cookies_to_netscape`, mirroring the existing `_format_cookies_for_ffmpeg` logic, to close the cookie-file injection gap for the yt-dlp `--cookies` path.

## Doc Updates Needed

- **SEC-001:** `docs/01-tools/vkdownloader-overview.md:151` -- revise the "Secret-safe ffmpeg cookie passing" statement to clarify that session cookies are protected via `@file` syntax but the signed m3u8 URL tokens passed via `-i` remain visible in process listings (unless SEC-001 fix is implemented).
- **SEC-004:** No user-facing doc update strictly required (`.gitignore` is not documentation), but `docs/99-reference/cli-reference.md:199` advertises `CookieSource.FILE` ("Load cookies from external file") as a supported value while the code rejects it (config.py:148-155) -- reconcile the doc with the not-implemented status before any cookie-file feature ships.
