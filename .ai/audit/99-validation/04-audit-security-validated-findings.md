---
name: 04-audit-security-validated
description: Validated security & secret management audit findings
agent: validator
alwaysApply: false
---

# Phase 04 Audit Findings — Security & Secret Management [VALIDATED]

**Executor:** audit-executor (original) / validator (validated)  
**Template:** .kilo/commands/audit/phases/04-audit-security.md  
**Status:** complete  
**Validated:** yes  

**Output mode:** `problems-only: true` — only problems are documented.

---

## Runtime Verification Summary (evidence baseline)

| Step | Result | Evidence |
|------|--------|----------|
| R1 — Credential Leak Search | No hardcoded secrets found | `.env` gitignored; `*_cookies.txt` gitignored; test fixtures use fake values (`token=secret`, `vk=secret123`) |
| R2 — Logger Audit | URLs redacted, no cookie leakage | `_strip_auth_params()` used for all URL logging; cookies never logged inline |
| R3 — File Permission / Ignore Check | Confirmed secure patterns | `.gitignore` line 22: `*_cookies.txt`; `cookies.py` uses `os.open(..., 0o600)` |
| R4 — Import Verification | No side-effect leaks | `security.py` and `cookies.py` imports are pure; no top-level credential operations |
| R5 — Linter / Type Check | All pass | `ruff check` and `mypy` successful |
| R6 — Test Suite | 233 passed | Includes 35 security-relevant tests in `test_security.py`, `test_url_sanitizer.py`, `test_config.py` |

---

## Findings

### SEC-001: yt-dlp cookie file is written into the user-chosen download directory instead of a private location

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (lines 184-192), `src/vkdownloader/services/cookies.py` (`_write_netscape_cookie_file`) |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The `_build_ytdlp_options()` function writes the Netscape cookie file to `output_file.parent / f".{output_file.stem}_cookies.txt"` (lines 186-191), while the `_temp_headers_file()` context manager uses `tempfile.mkstemp()` for ffmpeg headers (lines 59-77). Both use `0o600` permissions via `os.open`, but the yt-dlp cookie file location exposes credentials to the user-supplied output directory tree. The cleanup (`finally` block at lines 616-619) depends on the executor task completing; cancellation before execution could orphan the file.
> - **See also:** Documented security feature in `docs/01-tools/vkdownloader-overview.md` line 151 describes the ffmpeg temp-file pattern; the yt-dlp pattern is inconsistent with this documented secure design.

**Description:** The yt-dlp download path writes live session cookies (a credential that authenticates the user's VK session) into `output_file.parent / f".{output_file.stem}_cookies.txt"` — i.e. the **download/output directory the user supplies on the CLI** (`--output` / `download_dir` setting). This is inconsistent with the ffmpeg path, which correctly writes the equivalent credential to a `tempfile.mkstemp(...)` private temp file (`_temp_headers_file`, lines 59-77, created 0o600 and auto-cleaned).

Because the file lands in the user-selected output directory:
- If the user downloads to a cloud-synced folder (OneDrive/Dropbox/Google Drive) or any shared location, the credential file is briefly materialized there and can be uploaded/synced/exposed before its `finally`-based cleanup runs.
- Cleanup is **not** guaranteed: the file is created inside `_build_ytdlp_options` (line 186/190) *before* the executor task closure (whose `finally` deletes it, lines 616-619) is even scheduled. If the executor task is cancelled between scheduling and execution, the file is orphaned in the output directory.

The file is correctly gitignored (`*_cookies.txt`) and created with `0o600` on Unix, and on Windows the `os.open` mode is a no-op (default user-only ACL), so this is not a critical leak — but it is a real deviation from the documented secure pattern in `vkdownloader-overview.md` (ffmpeg uses temp files) and an inconsistency within the codebase itself.

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
    ydl_opts["cookiefile"] = str(cookie_file)
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
# src/vkdownloader/services/downloader.py:59-77
@asynccontextmanager
async def _temp_headers_file(headers: str) -> AsyncIterator[Path]:
    fd, path = tempfile.mkstemp(suffix=".headers", prefix="vk_ffmpeg_")
    try:
        os.write(fd, headers.encode())
        os.close(fd)
        yield Path(path)
    finally:
        Path(path).unlink(missing_ok=True)
```

**Recommendation:**
- **What:** Write the yt-dlp Netscape cookie file to a private temp location (e.g. `tempfile.mkstemp(suffix=".txt", prefix="vk_cookies_")`, which is 0o600 on all platforms) instead of `output_file.parent`, and rely on a context manager for guaranteed cleanup. Keep yt-dlp's `cookiefile` option pointing at that temp path.
- **Why:** Removes the credential from the user-supplied output tree entirely (no cloud-sync / shared-folder exposure) and removes the dependency on the executor task reaching its `finally` for secure deletion — matching the already-correct ffmpeg path and the documented secure design pattern.
- **Effort:** small
- **Priority:** recommended

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

None. (The documentation already describes the temp-file pattern as the secure approach; implementing the recommendation would bring the code into alignment with existing docs.)

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 1 | SEC-001 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Cross-Phase Analysis

No conflicts detected between Phase 04 (Security) and Phase 01 (CLI) or Phase 02 (Config) findings.

CLI-001 (CFG-003) covers Pydantic `Settings()` validation errors reaching the user. SEC-001 is orthogonal — it concerns credential file placement, not configuration validation.

CFG-004 covers misspelled environment variables; no interaction with SEC-001.

### Rollout Analysis

| Finding | Risk | Mitigation |
|---------|------|------------|
| SEC-001 | Low | Uses existing `tempfile.mkstemp()` pattern already proven in `_temp_headers_file`. No breaking changes to API or CLI. |

No circular dependencies or unsafe rollout ordering detected.

---

## Warnings

- **Architectural risk:** The codebase has an established secure pattern (`_temp_headers_file` context manager) that SEC-001 recommends extending to the yt-dlp cookie path. This inconsistency should be resolved for maintainability.
- **Credential exposure window:** While LOW severity due to gitignore and 0o600 permissions, the window between file creation and cleanup in a cloud-synced directory poses a theoretical risk that is eliminated by the recommended temp-file approach.