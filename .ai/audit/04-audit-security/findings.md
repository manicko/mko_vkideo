---
name: 04-security-findings
description: Security & secret management audit findings for mko_vkideo
agent: audit-executor
alwaysApply: false
---

# Phase 04 Audit Findings — Security & Secret Management

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/04-audit-security.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

| Step | Result |
|------|--------|
| R1 — Credential Leak Search | No hardcoded secrets. `.env` gitignored + untracked; only fake test fixtures (`token=secret`, `vk=secret123`). |
| R2 — Logger Audit | All log calls either redact URLs via `_strip_auth_params` or log only cookie *paths* at debug. Cookie/settings contents never logged. |
| R3 — File Permission / Ignore Check | `.env` and `*_cookies.txt` are gitignored and untracked (`git check-ignore .env` → `.gitignore:28`). |
| R4 — Import Verification | `security.py`, `cookies.py` have no import-time side effects that leak credentials. |
| R5 — Linter / Type Checker | `ruff check` → All checks passed; `mypy` → Success, no issues (2 formatting-only nits in unrelated files). |
| R6 — Test Suite | 233 passed (incl. 35 security-relevant tests in `test_security.py`, `test_url_sanitizer.py`, `test_config.py`). |

---

## Findings

### SEC-001: yt-dlp cookie file is written into the user-chosen download directory instead of a private location

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (lines 186, 190), `src/vkdownloader/services/cookies.py` (`_write_netscape_cookie_file`) |
| **Classification** | advisory |

**Description:**
The yt-dlp download path writes live session cookies (a credential that authenticates the user's VK session) into `output_file.parent / f".{output_file.stem}_cookies.txt"` — i.e. the **download/output directory the user supplies on the CLI** (`--output` / `download_dir` setting). This is inconsistent with the ffmpeg path, which correctly writes the equivalent credential to a `tempfile.mkstemp(...)` private temp file (`_temp_headers_file`, `downloader.py:59-77`, created 0o600 and auto-cleaned).

Because the file lands in the user-selected output directory:
- If the user downloads to a cloud-synced folder (OneDrive/Dropbox/Google Drive) or any shared location, the credential file is briefly materialized there and can be uploaded/synced/exposed before its `finally`-based cleanup runs.
- Cleanup is **not** guaranteed: the file is created inside `_build_ytdlp_options` (line 187/191) *before* the executor task closure (whose `finally` deletes it, line 616-619) is even scheduled. If the executor task is cancelled between scheduling and execution, the file is orphaned in the output directory.

The file is correctly gitignored (`*_cookies.txt`) and created with `0o600` on Unix, and on Windows the `os.open` mode is a no-op (default user-only ACL), so this is not a critical leak — but it is a real deviation from the guideline that credentials belong in a private/temp location, and from the ffmpeg path's own secure pattern.

**Evidence:**
```python
# src/vkdownloader/services/downloader.py:184-192
cookie_file: Path | None = None
if raw_cookies:
    cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"   # <- output dir, not temp/private
    _write_netscape_cookie_file(cookie_file, raw_cookies)
    ydl_opts["cookiefile"] = str(cookie_file)
elif cookies:
    cookie_file = output_file.parent / f".{output_file.stem}_cookies.txt"
    _write_netscape_cookie_file(cookie_file, cookies)
```
```python
# src/vkdownloader/services/downloader.py:615-619  (cleanup only inside the closure)
finally:
    if cookie_file is not None and cookie_file.exists():
        cookie_file.unlink()
        logger.debug("cookie_file_cleaned_up", path=str(cookie_file))
```
Contrast with the ffmpeg path, which uses a guaranteed-cleanup private temp file:
```python
# src/vkdownloader/services/downloader.py:71-77
fd, path = tempfile.mkstemp(suffix=".headers", prefix="vk_ffmpeg_")
...
finally:
    Path(path).unlink(missing_ok=True)
```

**Recommendation:**
- **What:** Write the yt-dlp Netscape cookie file to a private temp location (e.g. `tempfile.mkstemp(suffix=".txt", prefix="vk_cookies_")`, which is 0o600 on all platforms) instead of `output_file.parent`, and rely on `tempfile`'s `finally`-based cleanup rather than the executor closure's `finally`. Keep yt-dlp's `cookiefile` option pointing at that temp path.
- **Why:** Removes the credential from the user-supplied output tree entirely (no cloud-sync / shared-folder exposure) and removes the dependency on the executor task reaching its `finally` for secure deletion — matching the already-correct ffmpeg path and eliminating an orphaned-credential edge case.
- **Effort:** small
- **Priority:** recommended (not mandatory)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 1 |

## Mandatory Fixes

None.

## Advisory Recommendations

- **SEC-001** (LOW): Write yt-dlp cookie file to a private temp location instead of the download directory, matching the ffmpeg path's secure pattern.

## Doc Updates Needed

None.
