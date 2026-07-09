---
name: 04-security
description: Phase 04 Audit Findings — Security & Secret Management (Validated)
agent: validator
alwaysApply: false
---

# Phase 04 Audit Findings — Security & Secret Management (Validated)

**Executor:** validator  
**Source:** `.ai/audit/04-security/findings.md`  
**Base:** Phase 04 Audit  
**Status:** complete  
**Validated:** yes

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
- `src\vkdownloader\infrastructure\http_client.py:48-51`
```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
```

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The code evidence confirms SSL verification is disabled. The comment on line 48 states "needed for VK CDN" but this does not mitigate the MITM risk. VK's CDN should support valid certificates. No configuration option exists to enable verification. This is a confirmed SPEC-DEVIATION.

**Recommendation:** Add `ssl_verify: bool` setting to Pydantic Settings with default `True`. Pass `ssl=settings.ssl_verify` to aiohttp's TCPConnector. If disabled, emit a security warning at startup. VK's CDN should work with valid certificates; if specific cert errors occur, investigate them individually rather than disabling all verification. Code:
```python
# In Settings model
ssl_verify: bool = Field(default=True, description="Verify SSL certificates for CDN connections")

# In HttpClient.__aenter__
connector = aiohttp.TCPConnector(ssl=self.settings.ssl_verify)
```
Effort: small. Priority: mandatory fix (eliminates MITM vulnerability).

---

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

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** All four evidence locations were verified in the source code. The URLs are logged with full query parameters including authentication tokens. This is a valid BEST-PRACTICE finding as it improves security hygiene without adding significant complexity.

**Recommendation:** Strip query parameters (including tokens) before logging URLs. Log only the base URL without authentication parameters. Example: log `https://example.com/video.m3u8` instead of `https://example.com/video.m3u8?token=abc123&expires=...`. Effort: small. Priority: recommended.

---

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
- `src\vkdownloader\infrastructure\browser.py:13-37`
- Line 30: `user_data_dir=str(user_data_dir) if user_data_dir else ""`

> **Validation Note:**
> - **Action:** Reclassified
> - **Original Type:** BEST-PRACTICE
> - **New Type:** SPEC-DEVIATION
> - **Detail:** Per cross-phase analysis, `create_stealth_context` is also covered in CFG-005 (Phase 02) for its async return type mismatch. The function is exported in `__init__.py` and has dedicated tests in `test_browser_infrastructure.py`. However, the actual `BrowserManager` class (lines 40-103) does NOT use this function - it uses `self.browser.new_context()` instead. This function is dead code that creates a security risk. Per validation rules: "If the spec, models, or config reference the component → reject the 'dead code' label and reclassify as SPEC-DEVIATION (missing integration, not dead code)." This is SPEC-DEVIATION because an exported function exists that is never properly integrated.

**Recommendation:** Remove the unused `create_stealth_context` function from `browser.py` and its exports in `__init__.py`. It is not used by `BrowserManager` and creates an async type error. Effort: trivial. Priority: mandatory fix.

---

### SEC-004: Incomplete .gitignore for Downloaded Content

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Classification** | advisory |

**Description:** The `.gitignore` file does not include patterns for downloaded video content or temporary segment files. The project downloads videos to user directories but also creates temporary `.{stem}_segments` directories and `.{stem}_progress.json` files in the output location. While not a direct security vulnerability, downloaded content could inadvertently be committed if saved to the repository directory.

**Evidence:**
- `.gitignore` contains only Python-generated file patterns (10 lines)
- No patterns for `*.mp4`, `*_segments/`, `*_progress.json`, or other download artifacts
- An actual downloaded file `225794656_456243239_1080p.mp4` exists in the repository root (verified at `C:\py_exp\mko_vkideo\225794656_456243239_1080p.mp4`)

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The `.gitignore` file was verified to contain only Python patterns. The downloaded MP4 file exists in the repository root. This is a valid BEST-PRACTICE finding - the downloaded content in the repo is concrete evidence the recommendation is needed.

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

---

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

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** All three evidence locations were verified. The `Path` objects are created from user input without any validation. The default value is `"."` (current directory). No path sanitization exists in the codebase. This is a valid BEST-PRACTICE finding addressing a real security risk.

**Recommendation:** Create `security.py` module with `validate_output_path(path: Path, warning: bool = True) -> Path` function. Implementation:
```python
def validate_output_path(path: Path, warning: bool = True) -> Path:
    path = path.resolve()
    if ".." in str(path):
        raise DownloadError("Path traversal not allowed")
    repo_root = Path(__file__).resolve().parent.parent
    if str(path).startswith(str(repo_root)):
        if warning:
            logger.warning(f"Output directory inside repository: {path}")
    return path
```
Apply at cli.py:48, main.py:57, and downloader.py:103. Uses CodeQL-recognized pattern for static analysis compatibility. Effort: small. Priority: recommended.

---

### SEC-006: ~~Cookies Logged with Download URLs~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | SEC-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src\vkdownloader\services\downloader.py` |
| **Classification** | advisory |

> **Rejection reason:** The `has_cookies=bool(cookies)` logging on line 50 does not expose cookie values or individual cookie names. It only indicates whether cookies are present (boolean). The actual security concern (cookies in process listings) is covered more accurately by SEC-002's recommendation to strip tokens from URLs. This finding conflates session correlation (low risk) with credential exposure (higher risk) and duplicates concerns already addressed. The session indicator alone provides minimal security risk and operational value for debugging.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 4 | SEC-001, SEC-002, SEC-004, SEC-005 |
| Reclassified | 1 | SEC-003 (BEST-PRACTICE → SPEC-DEVIATION) |
| Merged | 0 | — |
| Rejected | 1 | SEC-006 (overlapping concern, minimal risk) |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| SEC-006 | Cookies session indicator logged | The `has_cookies=bool(cookies)` logging only exposes a boolean indicator, not actual credentials. The real concern (cookies in process listings) is already covered by URL token stripping in SEC-002. This finding duplicates concerns with minimal individual risk. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SEC-003 | BEST-PRACTICE | SPEC-DEVIATION | The `create_stealth_context` function is exported, tested, and documented as intended, but is never used by the actual BrowserManager. It creates a security risk via undefined user data directory location and an async type error. Per validation rules, this is "missing integration, not dead code" - the component exists but is not properly integrated into the application flow. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | SEC-003 was reclassified instead of merged. The async type issue is covered in CFG-005 but this finding addresses different security aspects. |

---

## Cross-Phase Conflicts

None detected. However, SEC-003 overlaps with:
- CFG-005 (Phase 02): `create_stealth_context` async return type mismatch
- SRV-009 (Phase 03): Same function, same issue

The async type error in `create_stealth_context` is a SPEC-DEVIATION that should be fixed alongside removing this unused function.

---

## Warnings

- **Security Risk (SEC-001):** Disabling SSL verification is a critical MITM vulnerability. The comment "needed for VK CDN" is speculation - VK's infrastructure should support valid certificates.
- **Cross-cutting Concern:** The `create_stealth_context` function issues (SEC-003) span multiple audit phases but represent a single root cause: the function should be removed as it's unused and creates both security and type safety issues.
- **Reproducibility Risk (SEC-004):** Downloaded content in repository root confirms the `.gitignore` issue is already causing operational problems.

---

## Required Fixes (from Validated Findings)

- SEC-001: Remove SSL verification bypass in HttpClient or make it configurable with security warning
- SEC-002: Strip query parameters from URLs before logging
- SEC-003: Remove unused `create_stealth_context` function from `browser.py` and its exports
- SEC-004: Add downloaded content patterns to `.gitignore`
- SEC-005: Validate output paths to prevent path traversal

---

## Advisory Recommendations

All validated findings are security-related and should be addressed. No additional advisory recommendations.