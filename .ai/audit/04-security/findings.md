---
name: 04-security
description: Phase 04 Audit Findings — Security & Secret Management
agent: auditor
alwaysApply: false
---

# Phase 04 Audit Findings — Security & Secret Management

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### SEC-001: SSL Certificate Verification Disabled

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src\vkdownloader\infrastructure\http_client.py` |
| **Classification** | mandatory |

**Description:** The `HttpClient` class disables SSL certificate verification via `ssl_context.verify_mode = ssl.CERT_NONE` and `ssl_context.check_hostname = False`. This creates a critical security vulnerability by making all HTTPS connections susceptible to man-in-the-middle (MITM) attacks. Sensitive data including video URLs, user cookies, and any session tokens could be intercepted by attackers.

**Evidence:**
- `src\vkdownloader\infrastructure\http_client.py:47-50`
```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```
- This affects all HTTP requests made through the HttpClient, including potential requests to VK's API endpoints

**Recommendation:** Remove SSL verification bypass or make it configurable with a security warning. VK's CDN should work with valid certificates. If certificate errors occur, investigate specific CDN cert issues rather than disabling all verification. Effort: small. Priority: mandatory fix.

### SEC-002: M3U8 URLs with Authentication Tokens Logged

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\infrastructure\network_monitor.py`, `src\vkdownloader\services\extractor.py`, `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** M3U8 playlist URLs containing expiring authentication tokens are logged in multiple locations. While the tokens expire after 1-2 hours (per documentation), logging tokens establishes a bad security practice and could expose credentials in log files that are retained longer than the tokens remain valid.

**Evidence:**
- `src\vkdownloader\infrastructure\network_monitor.py:58` - `logger.debug("m3u8_url_captured", url=normalized)` logs the full URL
- `src\vkdownloader\infrastructure\network_monitor.py:81` - `logger.debug("m3u8_url_found_in_json", url=normalized)` logs full URL
- `src\vkdownloader\services\extractor.py:53` - `logger.debug("parsed_video_id", owner_id=owner_id, video_id=video_id, url=url)` logs full video URL
- `src\vkdownloader\services\downloader.py:50` - `logger.info("starting_ffmpeg_download", url=m3u8_url, ...)` logs m3u8 URL

**Recommendation:** Strip query parameters (including tokens) before logging URLs. Log only the base URL without authentication parameters. Example: log `https://example.com/video.m3u8` instead of `https://example.com/video.m3u8?token=abc123&expires=...`. Effort: small. Priority: recommended.

### SEC-003: Browser Persistent Context Without Path Specification

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\infrastructure\browser.py` |
| **Classification** | advisory |

**Description:** The `create_stealth_context` function uses `user_data_dir=str(user_data_dir) if user_data_dir else ""` which, when empty, uses the default system location. Combined with `launch_persistent_context`, this could create browser profile directories in unpredictable locations. The main `BrowserManager` class doesn't use persistent context, but the helper function exists and should be either fixed or removed.

**Evidence:**
- `src\vkdownloader\infrastructure\browser.py:13-29`
```python
def create_stealth_context(..., user_data_dir: Path | None = None) -> "BrowserContext":
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir) if user_data_dir else "",
```
- An empty string is passed to `user_data_dir` when not specified, which uses an undefined location

**Recommendation:** Either remove the unused `create_stealth_context` function if not needed, or update it to use a proper user data directory via `platformdirs` in the standard user config location. Effort: small. Priority: recommended.

### SEC-004: Incomplete .gitignore for Downloaded Content

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.gitignore` |
| **Classification** | advisory |

**Description:** The `.gitignore` file does not include patterns for downloaded video content or temporary segment files. The project downloads videos to user directories but also creates temporary `.{stem}_segments` directories and `.{stem}_progress.json` files in the output location. While not a direct security vulnerability, downloaded content could inadvertently be committed if saved to the repository directory.

**Evidence:**
- `.gitignore` contains only Python-generated file patterns
- No patterns for `*.mp4`, `*_segments/`, `*_progress.json`, or other download artifacts
- An actual downloaded file `225794656_456243239_1080p.mp4` exists in the repository root (found during discovery)

**Recommendation:** Add patterns for downloaded content and temporary files to `.gitignore`:
```
# Downloaded content
*.mp4
*.mkv
*.avi
# Temporary segment files
*_segments/
*_progress.json
```
Effort: trivial. Priority: recommended.

### SEC-005: Output Path Not Validated for Path Traversal

| Field | Value |
|-------|-------|
| **ID** | SEC-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\cli.py`, `main.py` |
| **Classification** | advisory |

**Description:** The output directory path provided via CLI (`--output/-o` option) or command-line argument is used directly without validation. While the path is resolved as a `Path` object, there is no validation to prevent path traversal attacks (e.g., `../../../etc/passwd` on Unix or `..\\..\\..\\Windows\System32` on Windows). Users could accidentally or maliciously overwrite system files.

**Evidence:**
- `src\vkdownloader\cli.py:48` - `output.mkdir(parents=True, exist_ok=True)` uses user-provided path directly
- `main.py:57` - `output_dir.mkdir(parents=True, exist_ok=True)` uses user-provided path directly
- `src\vkdownloader\services\downloader.py:103` - `segments_dir.mkdir(parents=True, exist_ok=True)` creates hidden directories based on user output

**Recommendation:** Validate output paths to ensure they are within expected directories. Consider:
1. Resolving the path to absolute and checking if it's within `Path.home()` or a designated download directory
2. Rejecting paths containing `..` or that resolve to system directories
3. Adding a warning when output is specified as the repository directory

Effort: small. Priority: recommended.

### SEC-006: Cookies Logged with Download URLs

| Field | Value |
|-------|-------|
| **ID** | SEC-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

**Description:** The `download_with_ffmpeg` function logs `has_cookies=bool(cookies)` which, while not logging the actual cookie values, creates a boolean indicator that could be combined with other logs to track user sessions. More critically, when cookies are formatted into ffmpeg headers, they could appear in process listings or logs.

**Evidence:**
- `src\vkdownloader\services\downloader.py:50` - `logger.info("starting_ffmpeg_download", url=m3u8_url, output=str(output_file), quality=quality, has_cookies=bool(cookies))`
- Cookies are passed to ffmpeg command as `-headers` argument (line 31-34)

**Recommendation:** Remove the `has_cookies` log field to prevent any session correlation. Consider whether cookies need to be passed to ffmpeg at all, or if a cookie file would be more secure. Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 2 |

## Mandatory Fixes

- SEC-001: SSL Certificate Verification Disabled in HttpClient

## Advisory Recommendations

- SEC-002: M3U8 URLs with authentication tokens logged
- SEC-003: Browser persistent context without proper path specification
- SEC-004: Incomplete .gitignore for downloaded content
- SEC-005: Output path not validated for path traversal
- SEC-006: Cookies session indicator logged

---

## Runtime Verification Results

### Step R1 — Credential Leak Search

No hardcoded secrets found (api_id, api_hash, bot_token, password, credentials) in source files. The project does not have Telegram or Google OAuth integration - it's a pure video downloader.

### Step R2 — Logger Audit

Found m3u8 URLs being logged in multiple locations (SEC-002). No direct logging of credentials found, but tokens in URLs are security-sensitive.

### Step R3 — File Permission Check

`.gitignore` lacks patterns for downloaded content and temporary files (SEC-004). Actual downloaded MP4 file found in repository root.

### Step R4 — Import Verification

All modules import cleanly without credential leakage on import.

### Step R5 — Linter and Type Checker

- ruff: 6 errors (import sorting, missing newlines, unused import, unused variable)
- mypy: 8 errors (missing type annotations, async return type mismatch, Any return types)

### Step R6 — Test Suite

53 tests passed.