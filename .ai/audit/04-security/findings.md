---
name: audit-findings
description: Structured findings template for audit phase output
agent: audit-executor
alwaysApply: false
---

# Phase 04 Audit Findings — Security & Secret Management

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/04-audit-security.md
**Status:** complete
**Validated:** no

---

## Findings

### SEC-001: VK session cookies passed as ffmpeg command-line arguments (visible in process listings)

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_build_ffmpeg_cmd`, `download_with_ffmpeg`) |
| **Classification** | mandatory |

**Description:** When `cookie_source = browser`, the extractor captures live VK cookies (including `remixsid`, the VK session authentication token) from `page.context.cookies()` (`src/vkdownloader/services/extractor.py:213-214, 234-245`). These cookies are then passed to ffmpeg as a `-headers "Cookie: ..."` command-line argument via `asyncio.create_subprocess_exec` (`downloader.py:117-139, 171`).

Command-line arguments are NOT secret on Linux/container hosts: any local user or process can read them via `ps aux`, `/proc/<pid>/cmdline`, `htop`, `docker top`, or `docker inspect`. This exposes the authenticated VK session token to other users/processes on a shared host or inside a container for the entire duration of the download. The same cookies are also written to a temporary `._cookies.txt` file (`downloader.py:464-465`), which is cleaned up in `finally` — but the CLI-argument exposure window remains throughout the subprocess lifetime.

Logging does NOT leak the cookie value (logger calls use `has_cookies=bool(cookies)`, not the raw value), so the exposure vector is specifically the process argument list, not the logs.

**Evidence:**
- `src/vkdownloader/services/downloader.py:121` — `cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""`
- `src/vkdownloader/services/downloader.py:130-131` — cookies embedded in `headers` arg passed to `asyncio.create_subprocess_exec(*cmd, ...)`
- `src/vkdownloader/services/extractor.py:213-214` — `cookies = await page.context.cookies()` captures authenticated session cookies from vkvideo.ru
- `src/vkdownloader/services/extractor.py:245` — `return "; ".join(cookie_parts[:20])` (includes `remixsid` and other auth cookies)
- Best-practice confirmation: secrets in CLI args are visible via `ps`/`/proc/<pid>/cmdline`/`docker inspect` (GitGuardian "Secrets at the Command Line", ORNL S3M docs, multiple CVE-style disclosures e.g. openclaw #27948).

**Recommendation:** Avoid passing the cookie string as a process argument. Preferred options (in increasing effort):
- (trivial) Pass cookies via ffmpeg's `-headers` read from a file using ffmpeg's `@filename` syntax (e.g. write headers to a temp file and pass `"@/tmp/headers.txt"`), so the secret never appears in `argv`. Reuse the existing temp `_cookies.txt` cleanup pattern.
- (small) Build the ffmpeg command with cookies supplied through a file descriptor / env-driven input only.
This keeps the secret out of the process argument list while preserving the existing logging-safe behavior.

---

### SEC-002: `.env` is tracked by git despite being listed in `.gitignore` (latent secret-leak risk)

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.gitignore` (line 28), repository index |
| **Classification** | mandatory |

**Description:** `.gitignore` contains `.env` (line 28), but `git ls-files --error-unmatch .env` succeeds, proving `.env` is already tracked in the repository index. `git check-ignore -v .env` returns nothing, confirming the ignore rule no longer applies to the tracked file.

The current committed `.env` contains only commented-out placeholder values (no live secrets), so there is no active leak. However, this is a latent risk: any real secret added to `.env` in the future will be committed and pushed, permanently entering git history. The same hazard applies to `.env.*` variants.

**Evidence:**
- `C:\py_exp\mko_vkideo\.gitignore:28` — `# Environment configuration` / `.env`
- `git ls-files --error-unmatch .env` → exits 0 (file IS tracked)
- `git check-ignore -v .env` → empty (ignore rule not effective for tracked file)
- Current `.env` content: all `VKDOWNLOADER_*` entries are commented out (lines 4-28); no secrets present today.

**Recommendation:** Decide on intended behavior and enforce it:
- If `.env` should NEVER be committed: remove it from the index with `git rm --cached .env` (history already contains the placeholder file; acceptable since it has no secrets) and ensure the ignore rule takes effect. Document that real secrets go in a local, untracked `.env`.
- If a committed `.env` template is desired: rename the tracked file to `.env.example` (with placeholders only) and keep `.env` ignored.
Either way, add a pre-commit guard (e.g. gitleaks / detect-secrets) so a future real secret added to a tracked `.env` is caught before commit.

---

### SEC-003: Security audit phase describes a secret surface that does not exist in this codebase

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.kilo/commands/audit/phases/04-audit-security.md` |
| **Classification** | advisory |

**Description:** The phase task instructs the auditor to verify Telegram `api_id`/`api_hash`/`bot_token`, Google OAuth2 `credentials.json`/`token.json`, spreadsheet IDs, Telethon session files, and `PathResolver`/`USER_DIR` (platformdirs) credential storage. None of these exist in the delivered `vkdownloader` project. The actual configuration surface is a single `pydantic_settings.BaseSettings` subclass (`src/vkdownloader/config.py`) driven by `VKDOWNLOADER_*` environment variables and an optional `.env`, with no Google Sheets / Telethon / Telegram integrations. The only credential-adjacent surface is VK browser cookies (see SEC-001).

The discovery grep for `api_id|api_hash|bot_token|credentials.json|token.json|oauth|spreadsheet` returned zero matches in `src/`. The only `session` references are `aiohttp.ClientSession`, unrelated to Telethon.

This is the same doc/reality mismatch already recorded for the config phase (`02-audit-config.md`, finding CFG-001). The security checklist dimensions 1, 2 (credentials.json/token.json/Telethon), 4 (path traversal for photo paths from sheets), and 6 (Telethon session) cannot be evaluated against this codebase because the referenced subsystems are absent.

**Evidence:**
- `grep -r "api_id|api_hash|bot_token|credentials.json|token.json|oauth|spreadsheet" src/` → 0 matches
- `src/vkdownloader/config.py` — only `VKDOWNLOADER_*` settings, no Telegram/Google fields
- `.kilo/commands/audit/phases/04-audit-security.md:26-27, 90-93, 102, 141-149` — references to non-existent secrets/session files
- Cross-reference: `.ai/audit/02-config/findings.md` CFG-001 documents the identical mismatch

**Recommendation:** Rewrite `.kilo/commands/audit/phases/04-audit-security.md` to match the delivered VK downloader security surface:
- Remove Telegram/Google Sheets/Telethon/spreadsheet checks.
- Add a dimension covering VK browser-cookie handling (capture, file write, gitignore coverage of `*_cookies.txt`, and CLI-argument exposure as in SEC-001).
- Keep the `.env`/config-secret and logging-sanitization checks (these apply and surfaced SEC-002 and the positive logging-safety result).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 1 |

## Mandatory Fixes

- **SEC-001** (HIGH) — Stop passing VK session cookies as ffmpeg command-line arguments; use a file/heredoc-based header input so secrets are not exposed via `ps`/`/proc`/`docker inspect`.
- **SEC-002** (MEDIUM) — Resolve the tracked-`.env` vs `.gitignore` conflict so real secrets cannot be committed (untrack `.env` or rename to `.env.example`); add a secret-scanning pre-commit hook.

## Advisory Recommendations

- **SEC-003** (LOW) — Update the audit phase doc to reflect the real security surface (VK cookies + env config), removing the non-existent Telegram/Google/Telethon checks.

## Doc Updates Needed

- **SEC-003** — `.kilo/commands/audit/phases/04-audit-security.md` must be rewritten to match the VK downloader codebase (see recommendation).

---

## Runtime Verification Record

| Step | Command | Result |
|------|---------|--------|
| R1 — Credential leak search | `grep -rE "api_id|api_hash|bot_token|client_secret|password|secret|token=" src/` | No hardcoded secrets. `.env` tracked but contains only commented placeholders (see SEC-002). |
| R2 — Logger audit | grep of all `logger.*` calls in `src/` | No secret values logged. URL logger calls use `_strip_auth_params`; cookie logger calls use `has_cookies=bool(cookies)`. Safe. |
| R3 — File permission / gitignore | `git ls-files`, `git check-ignore`, `.gitignore` review | `*_cookies.txt` gitignored (line 22). `.env` gitignored in file but still tracked in index (SEC-002). No `.session`/`token.json`/`credentials.json` present. |
| R4 — Import verification | `uv run python -c "import vkdownloader.config, ...security, ...url_sanitizer"` | Imports succeed, no import-time side effects leak credentials. |
| R5 — Linter & type checker | `uv run ruff check src/vkdownloader` / `uv run mypy src/vkdownloader` | ruff: All checks passed. mypy: Success, no issues found in 23 source files. |
| R6 — Test suite | `uv run pytest tests` | 216 passed in 11.09s. |

