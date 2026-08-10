# Phase 04 Validation Report — Security & Secret Management

**Validator:** conservative validator (architectural integrity, rollout safety, implementation correctness)
**Date:** 2026-08-09
**Source findings:** `.ai/audit/04-audit-security/findings.md`
**Output:** `.ai/audit/99-validation/04-audit-security-validated-findings.md`
**Phase template:** `.kilo/commands/audit/phases/99-audit-validate.md`
**Status:** validated
**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).

> **Truncation note:** Source `findings.md` was truncated at 58 lines (SEC-001 only, incomplete Evidence).
> Full findings (SEC-001 through SEC-007) reconstructed from generation source `.temp/write_findings.py`.
> The Runtime Verification table in `findings.md` references SEC-002 and SEC-004, confirming
> truncation was an interruption, not reduced scope.

This report is self-contained. Original findings are reproduced with inline validation decisions.

---

## Validation Methodology

Verified against: (1) implementation — source code at cited paths/line numbers; (2) dependencies — grep across `src/` and `tests/` for call sites and `__all__` exports; (3) documentation — `docs/01-tools/*.md`, `docs/11-guides/*.md`; (4) runtime — `uv run pytest`, `uv run ruff check`, `ruff format --check`, `uv run mypy` re-run; (5) cross-phase — compared against phases 01-03.

## Runtime Verification (re-run by validator)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 | Credential leak search | PASS (0 matches) | 0 matches across `src/`. |
| R2 | Logger audit | PASS (with noted gap) | All `url=` fields use `_strip_auth_params`. `_echo_ytdlp_line` writes raw output to stderr — see SEC-002. |
| R3 | VCS ignore & permissions | PARTIAL | `.env` ignored; `.env.local` NOT ignored. See SEC-004. |
| R4 | Import verification | PASS | All modules import cleanly. |
| R5 | Linter & type checker | PARTIAL | `ruff check` passes. One file fails `ruff fmt --check` (downloader.py). `mypy` 1 error (correlation.py:55). Pre-existing, tracked CLI-004/CLI-005. |
| R6 | Test suite | PASS (325) | 325 passed in 9.97s. |

---

## Findings

### SEC-001: Signed CDN tokens in ffmpeg subprocess command-line arguments

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Technical claim VERIFIED — `downloader.py:441` passes raw `m3u8_url` (CDN tokens: `expires`, `sig`, `urls` per limitations.md:49-53) directly as `-i <m3u8_url>` to ffmpeg, visible in process listings. Cookies ARE protected via `@file` at line 437. yt-dlp uses original VK URL (line 801) without tokens. `_strip_auth_params` is applied only to logging, never to the ffmpeg command argument. Reclassified from SPEC-DEVIATION to BEST-PRACTICE: docs at overview.md:151 and limitations.md:64 claim protection specifically for cookies/session tokens (correctly implemented), not m3u8 URL tokens. The code does not violate a documented spec — this is a security gap / best-practice opportunity. DOC-UPDATE to scope protection should accompany the fix.
> - **See also:** SEC-002 (subprocess output may echo this URL into logs — dependency chain)

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | MEDIUM |
| **Type** | ~~SPEC-DEVIATION~~ **BEST-PRACTICE** |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`HLSDownloader.download_with_ffmpeg`); `docs/01-tools/vkdownloader-overview.md:151` |
| **Classification** | mandatory |

**Description:** The ffmpeg download path passes the HLS m3u8 playlist URL — containing expiration-signed CDN tokens — directly as `-i <m3u8_url>`. Session cookies ARE protected via `@file` syntax (downloader.py:437), but m3u8 URL tokens are NOT. yt-dlp has no such exposure (downloader.py:801). The documentation advertises "Secret-safe ffmpeg cookie passing" (overview.md:151) — accurate for cookies, silent about URL tokens.

**Evidence (all verified by direct code inspection):**
- `downloader.py:441`: `cmd.extend(["-i", m3u8_url, "-c", "copy", str(output_file)])` — raw m3u8_url as command-line arg.
- `downloader.py:436-437`: `"-headers", f"@{headers_file}"` — cookies correctly protected via @file.
- `vkdownloader-limitations.md:49,64`: confirms m3u8 URLs contain expiring tokens; cookies protected via @file from process listings.
- `vkdownloader-overview.md:151`: "Secret-safe ffmpeg cookie passing" claim (accurate for cookies).
- `_strip_auth_params` (url_sanitizer.py:6-25) called for all URL logging but NOT for the `-i` argument.

**Impact:** Local users or co-located processes reading `/proc/<pid>/cmdline` during ffmpeg download can extract signed CDN tokens and access CDN segments directly, valid for up to ~2 hours (per project documentation: limitations.md:49).

**Recommendation:** Route the m3u8 URL through an ffmpeg argument file (`ffmpeg @argfile`) or switch to yt-dlp Python API. Update overview.md:151 to accurately scope protection (cookies only). Effort: medium.

> **Fix feasibility:** ffmpeg's `-i` does NOT support per-option `@file` syntax (unlike `-headers`). Correct approach is full-argument `@file` form (`ffmpeg @argfile`), an ffmpeg-supported pattern requiring restructuring command construction in `download_with_ffmpeg` (lines 430-441).

---

### SEC-002: Unsanitized yt-dlp/ffmpeg subprocess output logged verbatim on failure

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp`, `HLSDownloader.download_with_ffmpeg`) |
| **Classification** | mandatory |

**Description:** When yt-dlp or ffmpeg exits non-zero, the entire captured stdout/stderr is logged verbatim as `error=error_msg` without redaction. URL fields ARE sanitized via `_strip_auth_params`, but subprocess output is not. Both tools routinely echo request URLs in diagnostic output. Combined with SEC-003 (log file to disk), this persists signed tokens.

**Evidence (verified by direct code inspection):**
- `downloader.py:518-525` (ffmpeg): `error_msg = stderr_data.decode()` then `logger.error("ffmpeg_download_failed", url=_strip_auth_params(m3u8_url), error=error_msg)` — `error_msg` NOT sanitized.
- `downloader.py:878-885` (yt-dlp): `error_msg = output_data.decode()` then `logger.error("download_failed", url=_strip_auth_params(video_url), error=error_msg)` — `error_msg` NOT sanitized.
- `downloader.py:233-248` (`_echo_ytdlp_line`): writes raw subprocess lines to `sys.stderr` (called at lines 833, 856).

**Impact:** Signed m3u8 URLs or cookie file paths in subprocess output are persisted in logs. Coupled with SEC-003 (world-readable logs), this is a credential-exposure vector.

**Recommendation:** Apply `_strip_auth_params` or equivalent URL redaction to `error_msg` before logging. Consider logging subprocess output at `debug` level only. Effort: small.

---

### SEC-003: Log file created with default umask, not owner-only permissions

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` (`setup_logging`, lines 228-236) |
| **Classification** | advisory |

**Description:** `logging.FileHandler(settings.log_file)` at config.py:234 uses process umask (yields `0o644` on POSIX umask `0o022`), not `0o600`. The project uses `0o600` for credential files (cookies.py:72, downloader.py:87) but not for log files. Unsanitized subprocess output (SEC-002) may end up in the log.

**Evidence (verified by direct code inspection):**
- `config.py:228-236`: `logging.FileHandler(settings.log_file)` — no explicit mode.
- `config.py:107-110`: `log_file` field has no permission handling.

**Impact:** If `VKDOWNLOADER_LOG_FILE` points to a shared directory, logs (potentially containing signed URLs from SEC-002) are readable by other users.

**Recommendation:** Create log file with explicit `0o600` before `FileHandler`, or subclass to enforce owner-only mode. Effort: trivial.

---

### SEC-004: `.gitignore` covers `.env` but not `.env.*` variants

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.gitignore` (line 28) |
| **Classification** | mandatory |

**Description:** `.gitignore:28` has `.env` (exact match only). Variants like `.env.local`, `.env.backup`, `.env.production` are NOT ignored, risking accidental secret commits. `CookieSource.FILE` (enums.py:50) exists but is rejected at config construction (config.py:148-155).

**Evidence (verified at runtime):**
- `.gitignore:28`: `.env`
- `git check-ignore .env` exits 0 (ignored)
- `git check-ignore .env.local` exits 1 (NOT ignored)
- `git ls-files '.env*'` shows only `.env.example` tracked

**Recommendation:** Use `.env*` plus `!.env.example` (standard dotenv convention). Effort: trivial.

---

### SEC-005: Dead-code `_write_netscape_cookie_file` with divergent permission semantics

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified by grep across `src/` and `tests/`: `_write_netscape_cookie_file` appears ONLY at definition (cookies.py:58), `__all__` (cookies.py:77), and re-export (downloader.py:369). Zero call sites. Live path is `_create_temp_cookie_file` (downloader.py:71, called at 318, 321). Both write Netscape format with `0o600` intent but via different mechanisms (`os.open` vs `tempfile.mkstemp`). Cross-phase overlap with SRV-002 (phase 03): complementary ownership (dead-code vs permission-semantics). No conflict.
> - **See also:** SRV-002 (phase 03)

| Field | Value |
|-------|-------|
| **ID** | SEC-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/cookies.py` |
| **Classification** | advisory |

**Description:** `_write_netscape_cookie_file` (cookies.py:58-75) is defined with `os.open(..., 0o600)` and exported in `__all__`, but has zero callers. The live path `_create_temp_cookie_file` (downloader.py:71-95) uses `tempfile.mkstemp`. Two functions writing the same format with different permission mechanisms creates maintenance confusion.

**Evidence (verified by grep):** Only at cookies.py:58 (def), cookies.py:77 (__all__), downloader.py:369 (__all__ re-export). Zero invocations.

**Recommendation:** Remove `_write_netscape_cookie_file` and its `__all__` entries, or document intended use and converge on same permission approach. Effort: small.

---

### SEC-006: `validate_output_path` `..`-string check is a no-op for pre-resolved paths

| Field | Value |
|-------|-------|
| **ID** | SEC-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/utils/security.py:44-52, 89-92`; `src/vkdownloader/config.py:119-131`; `src/vkdownloader/services/downloader.py:605` |
| **Classification** | advisory |

**Description:** `validate_output_path()` checks `".." in str(path)` BEFORE `path.resolve()` (security.py:44-52). For paths already resolved by callers, `..` is collapsed and the check is dead. Three callers pre-resolve: `config.py:131` (`expand_tilde_paths`), `security.py:90` (`_resolve_output_file`), `downloader.py:605` (receives path from `_resolve_output_file` at line 1204). Only `segment_downloader.py:855` passes an unresolved path (via `HLSDownloadRequest` DTO at dtos.py:21 with no validators).

**Evidence (verified by code inspection):**
- `security.py:44-52`: `if ".." in path_str:` checked before `resolved = path.resolve()`.
- `security.py:89-92`: `_resolve_output_file`: `output_path = Path(output_path).resolve()` then `validate_output_path(output_path)`.
- `downloader.py:1204-1209`: `download_video` passes `_resolve_output_file` result to `perform_download`, which passes to `download_with_ytdlp_with_resume_fallback` (line 605).

**Impact:** Not practically exploitable today (all inputs from trusted config/CLI, titles sanitized). False sense of defense-in-depth.

**Recommendation:** Make traversal check resolve-first and compare against safe base dir, or document that `validate_output_path` requires unresolved paths. Effort: small.

---

### SEC-007: CRLF injection in `_cookies_to_netscape` not sanitized

| Field | Value |
|-------|-------|
| **ID** | SEC-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/cookies.py:38-47` (`_cookies_to_netscape`); `src/vkdownloader/services/extractor.py:252-263` (`_format_cookies_for_ffmpeg` — sanitized counterpart) |
| **Classification** | advisory |

**Description:** `_cookies_to_netscape` (cookies.py:38-47) writes raw cookie name/value into Netscape format without CRLF stripping. `_format_cookies_for_ffmpeg` (extractor.py:259-262) already strips `\r`/`\n` with a docstring citing header-injection prevention. The same data is sanitized for the ffmpeg path but NOT for the yt-dlp `--cookies` path.

**Evidence (verified by code inspection):**
- `cookies.py:39-40,47`: `name = cookie_item["name"]` / `value = cookie_item["value"]` — raw, no CRLF strip.
- `extractor.py:260-261`: `cookie.get("name", "").replace("\r", "").replace("\n", "")` — CRLF stripped.
- Runtime: a value `abc\r\nSet-Cookie: evil=hack` in `_cookies_to_netscape` would produce an injected cookie-file line.

**Impact:** Low in practice (cookies from user's own browser). Defense-in-depth already implemented elsewhere for same data — unjustified gap. Would become exploitable if `CookieSource.FILE` (enums.py:50) is ever implemented.

**Recommendation:** Apply CRLF stripping in `_cookies_to_netscape`, mirroring `_format_cookies_for_ffmpeg`. Effort: trivial.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 6 | SEC-002, SEC-003, SEC-004, SEC-005, SEC-006, SEC-007 |
| Reclassified | 1 | SEC-001: SPEC-DEVIATION → BEST-PRACTICE |
| Merged | 0 | — |
| Rejected | 0 | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SEC-001 | SPEC-DEVIATION | BEST-PRACTICE | Docs claim cookie protection only (correctly implemented). Docs do not claim m3u8 URL token protection. No spec violation; security gap = best-practice opportunity. |

### Merged Findings

_None._

### Cross-Phase Analysis

| Finding | Relationship | Verdict |
|---------|-------------|---------|
| SEC-001 → SEC-002 | Dependency: m3u8 URL on cmdline (SEC-001) gets echoed in ffmpeg stderr, then logged unredacted (SEC-002) | Fix SEC-001 reduces SEC-002 blast radius |
| SEC-002 → SEC-003 | Coupling: unsanitized subprocess output (SEC-002) in world-readable log file (SEC-003) | Fix both together |
| SEC-005 ↔ SRV-002 (phase 03) | Overlap: same `_write_netscape_cookie_file` symbol; SRV-002 = dead-code/ownership, SEC-005 = permission-semantics | Complementary, no conflict |

## Rollout Analysis

| Finding | Fix complexity | Dependencies | Rollout order |
|---------|---------------|--------------|---------------|
| SEC-001 | medium | None | 1st (reduces SEC-002 blast radius) |
| SEC-002 | small | SEC-001 | 2nd |
| SEC-003 | trivial | SEC-002 | 3rd |
| SEC-004 | trivial | None | parallel |
| SEC-005 | small | SRV-002 (phase 03) | parallel |
| SEC-006 | small | None | parallel |
| SEC-007 | trivial | None | parallel |

**Recommended order:** SEC-004, SEC-007, SEC-006, SEC-005, SEC-001, SEC-002, SEC-003

## Execution Validation

**Applicability:** All findings are currently applicable. Source code inspected at cited line numbers; no changes since audit.

**Execution readiness:** All findings approved. SEC-001, SEC-002, SEC-004 are mandatory (security-critical). SEC-003, SEC-005, SEC-006, SEC-007 are advisory. SEC-005 fix is safe (zero callers of dead function). No rollout safety risks.

## Warnings

- **Findings file truncation:** Source `findings.md` is 58 lines with incomplete SEC-001 Evidence. All 7 findings reconstructed from `.temp/write_findings.py`.
- **Pre-existing CI failures:** One file fails `ruff format --check` (`downloader.py`); `mypy` has 1 error (`correlation.py:55`). Both tracked in CLI-004/CLI-005 (phase 01).
- **SEC-001 fix complexity:** ffmpeg `-i` does not support per-option `@file`. Fix requires full-argument `@file` (`ffmpeg @argfile`), an ffmpeg-supported but less common pattern. Verify compatibility with existing progress parsing/shutdown logic (downloader.py:454-539).
- **SEC-005 vs SRV-002:** Both target `_write_netscape_cookie_file`. Ensure coordination — single action (remove or wire up), not two conflicting fixes.
- **SEC-002 severity coupling:** If SEC-001 is not fixed, ffmpeg's error output (which echoes the `-i` URL) will contain signed CDN tokens that SEC-002 logs unredacted.

## Required Fixes

1. **SEC-001:** Stop passing signed m3u8 URL as plaintext CLI arg to ffmpeg. Use `ffmpeg @argfile` or yt-dlp Python API. Update `vkdownloader-overview.md:151` to scope protection (cookies only).
2. **SEC-002:** Sanitize subprocess `error_msg` with `_strip_auth_params` or equivalent before logging.
3. **SEC-004:** Extend `.gitignore`: `.env*` plus `!.env.example`.

## Advisory Recommendations

| ID | Title | Effort | Priority |
|----|-------|--------|----------|
| SEC-003 | Create log files with explicit `0o600` in `setup_logging()` | trivial | recommended |
| SEC-005 | Remove or document dead `_write_netscape_cookie_file` | small | recommended |
| SEC-006 | Make `validate_output_path` resolve-first, validate against base dir | small | recommended |
| SEC-007 | Add CRLF stripping to `_cookies_to_netscape` | trivial | recommended |
