---
name: audit-findings
description: Phase 04 Security & Secret Management findings
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

### SEC-001: Cookie credential files written with world/group-readable permissions

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download` ~L537-538, L542-543), `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |

**Description:** When authenticated downloads run via yt-dlp with `cookie_source=BROWSER`, live VK session cookies (including `remixsid`) are serialized with `_cookies_to_netscape()` and written to a file in the **user-selected download directory** using `Path.write_text()`:

```python
cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
cookie_file.write_text(_cookies_to_netscape(raw_cookies))
```

`Path.write_text()` does not set an explicit mode, so the file is created with the process umask applied. On POSIX this yields mode `0o666` minus umask (commonly `0o644` / world-readable). Verified at runtime:

```
uv run python -c "p.write_text('session=secret'); print(oct(stat.S_IMODE(p.stat().st_mode)))"
-> 0o666   (world-readable bit set, group-readable bit set)
```

These cookie files contain valid, reusable authentication tokens that grant access to the victim's VK account. Any other local user or process able to read the download directory can harvest them. This directly contradicts the project's own documented security guarantee in `docs/01-tools/vkdownloader-overview.md` (L151): *"VK session cookies ... are written to a temporary headers file ... This prevents session tokens from leaking"* — the documented "secret-safe" design applies only to the ffmpeg `@file` headers path (which uses `tempfile.mkstemp`, mode `0600`), not to this yt-dlp cookie-file path.

**Evidence:**
- `src/vkdownloader/services/downloader.py:537-538` and `L542-543` — `cookie_file.write_text(...)` with no `mode` argument.
- `src/vkdownloader/services/cookies.py:11-53` — `_cookies_to_netscape()` writes raw cookie `name\tvalue` pairs (live tokens).
- Runtime check: `Path.write_text()` produced `0o666` (world/group readable).
- Contrast: `downloader.py:72` `_temp_headers_file` correctly uses `tempfile.mkstemp` (secure `0600` on POSIX), proving the secure pattern already exists in the same module.

**Recommendation:** Write cookie files with restrictive permissions — pass `mode=0o600` to `write_text()` on POSIX, or build them through `tempfile.mkstemp`/`os.open(..., 0o600)` like the existing `_temp_headers_file` helper. Also consider placing cookie files in a private per-user cache dir rather than the shared download directory. Effort: trivial. Priority: recommended (security hardening; reconciles code with documented guarantee).

---

### SEC-002: Fragile path-traversal detection and repo-root write allowed

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/utils/security.py` (`validate_output_path` L23-63, `_sanitize_title` L12-20) |
| **Classification** | advisory |

**Description:** `validate_output_path()` detects traversal only via a literal substring check `if ".." in path_str` (L43). This approach is brittle: it (a) blocks legitimate paths that merely contain `..` as a substring (e.g. `C:/a/..b/c` is rejected even though it is not traversal), and (b) is a pure string heuristic that ignores symlinks, NTFS junctions, and `..` occurring after `resolve()`. The actual traversal protection works only because `_sanitize_title()` strips `/` and `\` from filenames — the `".."` guard is a redundant, fragile second line of defense rather than a robust one.

Additionally, when a resolved path falls inside the repository root, the function only emits a `logger.warning` (L54-58) and still returns the path. Writing downloaded videos (and the cookie files from SEC-001) inside the repo risks committing credentials if the user points `download_dir` at the project tree, and the warning is easy to miss.

`_sanitize_title()` also does not strip leading dots, so titles like `.hidden` become hidden files (`validator` allowed `.hidden` → `/tmp/out/.hidden`), which can hide artifacts and confuse cleanup.

**Evidence:**
- `src/vkdownloader/utils/security.py:43` — `if ".." in path_str: raise DownloadError(...)`.
- `src/vkdownloader/utils/security.py:49-61` — repo-root detection logs a warning but does not block.
- `src/vkdownloader/utils/security.py:18` — sanitize loop `for char in '/\\:*?"<>|'` omits `.` and control chars.
- Runtime test: `validate_output_path(Path("C:/a/..b/c"))` → BLOCKED (false positive on non-traversal); `validate_output_path(Path("/tmp/out/.hidden"))` → ALLOWED.

**Recommendation:** Replace the substring `".."` heuristic with a resolve-and-containment check: resolve the final joined path and assert it stays within the intended base directory (e.g. `download_dir` for yt-dlp, or a fixed acceptable root), instead of string matching. Harden `_sanitize_title()` to also strip/collapse leading dots and reject control characters. Consider treating "inside repo root" as a hard error (or a `--yes` opt-in) rather than a silent warning. Effort: small. Priority: recommended.

---

### SEC-003: Auth-failure error strings logged verbatim

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (L470), `src/vkdownloader/services/extractor.py` (L216) |
| **Classification** | advisory |

**Description:** Two log calls emit `error=str(e)` from cookie/token handling:

```python
# downloader.py:470
logger.warning("failed_to_refresh_token", error=str(e))
# extractor.py:216
logger.debug("failed_to_capture_cookies", error=str(e))
```

Exception messages from the underlying browser/network stack can include URL fragments, request metadata, or auth-context that, while not the raw cookie value, can leak environment details useful to an attacker or pollute audit logs. The codebase already demonstrates good practice elsewhere (`_strip_auth_params` is applied to every URL logged), so these two spots are inconsistent with that standard.

**Evidence:**
- `src/vkdownloader/services/downloader.py:470` — `logger.warning("failed_to_refresh_token", error=str(e))`.
- `src/vkdownloader/services/extractor.py:216` — `logger.debug("failed_to_capture_cookies", error=str(e))`.
- Contrast: all URL-bearing log calls in `segment_downloader.py`, `network_monitor.py`, `extractor.py` route through `_strip_auth_params()`.

**Recommendation:** Scrub or generalize these error messages (e.g. log `error_type=type(e).__name__` instead of full `str(e)`, or redact URL/header content within the message). Effort: trivial. Priority: recommended (consistency with existing secret-safe logging standard).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 1 |

## Mandatory Fixes

- **SEC-001** (HIGH) — Cookie credential files written with world/group-readable permissions (`0o666`/`0o644`). Live VK session tokens in the download directory are readable by other local users/processes. Fix: write with `mode=0o600` (or reuse the existing `mkstemp` helper) and store outside the shared download dir.

## Advisory Recommendations

- **SEC-002** (MEDIUM) — Replace fragile substring `".."` traversal check with a resolve-and-containment assertion; harden `_sanitize_title` (leading dots, control chars); treat repo-root writes as errors rather than silent warnings.
- **SEC-003** (LOW) — Stop logging raw `str(e)` from token/cookie auth failures; align with the existing `_strip_auth_params` secret-safe logging standard.

## Doc Updates Needed

- **SEC-001** — `docs/01-tools/vkdownloader-overview.md` (L151) states cookies are written only to a secure temp headers file and removed; this omits the yt-dlp cookie-file path in `downloader.py` that writes live tokens to the download dir with default (world-readable) permissions. Update the doc to either (a) describe the real behavior accurately, or (b) reflect the hardened fix once SEC-001 is addressed. Recommend updating docs after the code fix lands.

---
