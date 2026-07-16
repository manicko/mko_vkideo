# Phase 04 Audit Findings - Security & Secret Management (Validated)

**Executor:** audit-executor
**Validator:** validator
**Template:** .kilo/commands/audit/phases/04-audit-security.md
**Status:** complete
**Validated:** yes

---

## Findings

### SEC-001: VK session cookies passed as ffmpeg command-line arguments (visible in process listings)

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py (_build_ffmpeg_cmd, download_with_ffmpeg) |
| **Classification** | mandatory |

**Description:** When cookie_source = browser, the extractor captures live VK cookies (including remixsid, the VK session authentication token) from page.context.cookies() and passes them to ffmpeg as a -headers command-line argument via asyncio.create_subprocess_exec.

Command-line arguments are NOT secret on Linux/container hosts: any local user or process can read them via ps aux, /proc/<pid>/cmdline, htop, docker top, or docker inspect. This exposes the authenticated VK session token.

Logging does NOT leak the cookie value (logger calls use has_cookies=bool(cookies)), so the exposure vector is specifically the process argument list.

**Evidence:**
- src/vkdownloader/services/downloader.py:121 - cookie_part constructed for headers
- src/vkdownloader/services/downloader.py:130-131 - cookies embedded in headers arg
- src/vkdownloader/services/extractor.py:213-214 - cookies captured from page.context.cookies()
- src/vkdownloader/services/extractor.py:245 - cookies formatted for ffmpeg
- Direct code inspection confirms cookies embedded in command arguments
- Best-practice confirmation: secrets in CLI args are visible via ps/proc/cmdline/docker inspect

**Recommendation:** Avoid passing the cookie string as a process argument. Use ffmpegs -headers read from a temp file using @filename syntax.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Finding confirmed through direct code inspection. Cookies embedded in command arguments passed to asyncio.create_subprocess_exec. No logging exposure exists.
> - **See also:** -

---

### SEC-002: .env is tracked by git despite being listed in .gitignore (latent secret-leak risk)

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | .gitignore (line 28), repository index |
| **Classification** | mandatory |

**Description:** .gitignore contains .env (line 28), but git ls-files --error-unmatch .env succeeds, proving .env is already tracked in the repository index. git check-ignore -v .env returns nothing, confirming the ignore rule no longer applies.

The current committed .env contains only commented-out placeholder values (no live secrets), so there is no active leak. However, this is a latent risk: any real secret added to .env in the future will be committed and pushed, permanently entering git history.

**Evidence:**
- .gitignore:28 - .env entry
- git ls-files --error-unmatch .env - exits 0 (file IS tracked) - verified
- git check-ignore -v .env - empty output - verified
- Current .env contains only commented placeholders - verified

**Recommendation:** Remove .env from the index with git rm --cached .env and ensure the ignore rule takes effect. Document that real secrets go in a local, untracked .env.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified via git commands that .env is tracked despite being in .gitignore. The file contains only commented placeholders.
> - **See also:** -

---

### SEC-003: Security audit phase describes a secret surface that does not exist in this codebase

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | .kilo/commands/audit/phases/04-audit-security.md |
| **Classification** | advisory |

**Description:** The phase task instructs the auditor to verify Telegram api_id/api_hash/bot_token, Google OAuth2 credentials.json/token.json, spreadsheet IDs, and Telethon session files. None of these exist in the delivered vkdownloader project.

The actual configuration surface is a pydantic_settings.BaseSettings subclass (src/vkdownloader/config.py) driven by VKDOWNLOADER_* environment variables, with no Google Sheets / Telethon / Telegram integrations.

**Evidence:**
- Code search for api_id, api_hash, bot_token, credentials.json, token.json, oauth, spreadsheet across src returned 0 matches - verified
- src/vkdownloader/config.py - only VKDOWNLOADER_* settings, no Telegram/Google fields - verified
- .kilo/commands/audit/phases/04-audit-security.md - references non-existent components
- Cross-reference: CFG-001 documents identical mismatch

**Recommendation:** Rewrite .kilo/commands/audit/phases/04-audit-security.md to match the delivered VK downloader security surface (remove non-existent checks, add VK browser-cookie handling dimension).

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Verified no Telegram or Google secrets exist. The audit phase document references non-existent components. This finding shares the same root cause as CFG-001.
> - **See also:** CFG-001 (Phase 02)

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | SEC-001, SEC-002, SEC-003 |
| Reclassified | 0 | - |
| Merged | 0 | - |
| Rejected | 0 | - |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| - | - | - |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| - | - | - |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| - | - | - | - |

---

## Mandatory Fixes

- **SEC-001** (HIGH) - Stop passing VK session cookies as ffmpeg command-line arguments; use a file/heredoc-based header input so secrets are not exposed via ps/proc/docker inspect.
- **SEC-002** (MEDIUM) - Resolve the tracked .env vs .gitignore conflict so real secrets cannot be committed (untrack .env or rename to .env.example); add a secret-scanning pre-commit hook.

---

## Advisory Recommendations

- **SEC-003** (LOW) - Update the audit phase doc to reflect the real security surface (VK cookies + env config), removing the non-existent Telegram/Google/Telethon checks.

---

## Doc Updates Needed

- **SEC-003** - .kilo/commands/audit/phases/04-audit-security.md must be rewritten to match the VK downloader codebase.

---

## Runtime Verification Record

| Step | Command | Result |
|------|---------|--------|
| R1 - Credential leak search | Code search for api_id/api_hash/bot_token/credentials.json/token.json/oauth/spreadsheet | No hardcoded secrets found. .env tracked but contains only commented placeholders (see SEC-002). |
| R2 - Logger audit | Search of logger calls in src/ | No secret values logged. URL logger calls use _strip_auth_params; cookie logger calls use has_cookies=bool(cookies). Safe. |
| R3 - File permission / gitignore | git ls-files, git check-ignore review | *_cookies.txt gitignored (line 22). .env gitignored in file but still tracked in index (SEC-002). |
| R4 - Import verification | uv run python -c "import vkdownloader.config..." | Imports succeed, no import-time side effects leak credentials. |
| R5 - Linter & type checker | uv run ruff check / uv run mypy | ruff: All checks passed. mypy: Success, no issues found. |
| R6 - Test suite | uv run pytest tests | 216 passed. |

---

## Rollout Safety Analysis

No rollout safety issues detected within the security findings. Each can be addressed independently:

1. **SEC-001** - Isolated to ffmpeg command construction. Fix can be implemented by using temp file for headers without affecting other components.
2. **SEC-002** - Git index manipulation only. Can be fixed with git rm --cached .env.
3. **SEC-003** - Documentation-only change with no code impact.

SEC-003 should be addressed in coordination with CFG-001 to prevent duplicate rework.

---

## Execution Validation

All targets confirmed present in current codebase:
- SEC-001: _build_ffmpeg_cmd in downloader.py (lines 117-139) and download_with_ffmpeg (lines 141-253) - both exist
- SEC-002: .env and .gitignore - both files exist
- SEC-003: Documentation file .kilo/commands/audit/phases/04-audit-security.md - exists

---

## Warnings

- **SEC-001**: Architectural risk - secrets exposure via process listing is a documented security vulnerability pattern.
- **SEC-002**: Latent operational risk - future commits could leak real secrets if .env remains tracked.

---
