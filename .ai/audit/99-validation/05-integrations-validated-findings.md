---
name: Phase 05 Validation — External Integrations
description: Validated audit findings for integration components in VK Video Downloader
template: .ai/audit/templates/audit-findings.md
executor: validator
status: complete
validated: yes
---

# Phase 05 Validation — External Integrations

**Executor:** validator  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** yes

---

## Findings

### INT-001: ~~Audit phase references non-existent Google Sheets integration~~ [REJECTED]

> **Rejection reason:** This finding correctly identifies that the audit phase document references non-existent integrations, but the problem is with the audit phase template itself, not the codebase. The audit phase document (`.kilo/commands/audit/phases/05-audit-integrations.md`) is a generic template that was incorrectly applied to this project. This finding should be addressed by updating the audit phase template, not as a code/spec deviation.

---

### INT-002: ~~Audit phase references non-existent Telegram integration~~ [REJECTED]

> **Rejection reason:** Same as INT-001. The audit phase document references Telegram/Telethon integration patterns that do not apply to this codebase. This is a template documentation issue, not a code/spec deviation in the actual application.

---

### INT-003: Remove or complete incomplete test file `test_hls_downloader_patch.py`

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `tests/test_hls_downloader_patch.py` |
| **Classification** | mandatory |

**Description:** The test file contains a syntax error causing pytest collection to fail.

**Evidence:**
- pytest collection error: `SyntaxError: no binding for nonlocal 'gather_called' found`
- File is 5 lines with a bare function using `nonlocal` outside any enclosing scope
- No imports, no test functions defined - appears to be orphaned/incomplete code

**Recommendation:** Remove the incomplete `test_hls_downloader_patch.py` file.

---

### INT-004: Fix coroutine/task handling in `cli.py` batch download CancelledError handler

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** The `_run_batch_with_progress` function creates coroutine objects but attempts to call Task methods on them.

**Evidence:**
- mypy error at lines 223-224: `"Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "done"`
- mypy error: `"Coroutine[Any, Any, tuple[str, str, str]]" has no attribute "cancel"`
- Line 210: `tasks = [_limited_download(url) for url in urls]` creates coroutine objects
- Lines 222-224: Iterating over `tasks` and calling `.done()` and `.cancel()` on coroutines is invalid

**Recommendation:** Convert coroutines to Task objects using `asyncio.create_task()` before the loop, then iterate over Task objects returned by `asyncio.as_completed()`.

---

### INT-005: Address unused `results` variable in `downloader.py`

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Classification** | mandatory |

**Description:** The `results` variable from `asyncio.gather(*tasks)` is assigned but never used. Instead, `downloaded_count` is set to `len(segments)` regardless of actual download success.

**Evidence:**
- ruff F841 error at line 395: `Local variable 'results' is assigned to but never used`
- Line 395: `results = await asyncio.gather(*tasks)`
- Line 405: `downloaded_count = len(segments)` - uses total segments, not actual successful downloads

**Recommendation:** Either use `results.count(True)` for `downloaded_count` to accurately track successful downloads, or remove the unused `results` assignment and fix the logic.

---

### INT-006: ~~Inconsistent SSL verification handling between integrations~~ [MERGED INTO INT-SSL]

> **Merged into:** INT-SSL (see Merged Findings section)

### INT-007: ~~yt-dlp `nocheckcertificate` ignores user SSL verification preference~~ [MERGED INTO INT-SSL]

> **Merged into:** INT-SSL (see Merged Findings section)

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | INT-003, INT-004, INT-005 |
| Reclassified | 0 | — |
| Merged | 2 | INT-006 + INT-007 → INT-SSL |
| Rejected | 2 | INT-001, INT-002 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| INT-001 | Audit phase references non-existent Google Sheets integration | Template documentation issue, not a code/spec deviation |
| INT-002 | Audit phase references non-existent Telegram integration | Template documentation issue, not a code/spec deviation |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| INT-006, INT-007 | INT-SSL | Both addressed the same SSL verification inconsistency; ffmpeg needs no changes (HTTPS input uses system verification by default) |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| — | — | — | — |

---

## Mandatory Fixes

1. INT-003: Remove or complete the incomplete `test_hls_downloader_patch.py` file
2. INT-004: Fix coroutine/task handling - use `asyncio.create_task()` to create Task objects before iterating with `as_completed()`
3. INT-005: Fix the unused `results` variable - use actual results to track successful downloads or remove the assignment

## Advisory Recommendations

1. INT-SSL: Fix yt-dlp SSL verification to respect `settings.ssl_verify` - change line 924 from `"nocheckcertificate": True` to `"nocheckcertificate": not settings.ssl_verify`
2. No ffmpeg changes needed - HTTPS input uses system certificate verification by default

---

## Actual External Integrations Confirmed

The project integrates with:
1. **yt-dlp** (`src/vkdownloader/services/downloader.py`) - Video extraction and download
2. **ffmpeg/ffprobe** (`src/vkdownloader/services/downloader.py`) - HLS stream processing and merging
3. **Playwright** (`src/vkdownloader/infrastructure/browser.py`, `src/vkdownloader/services/extractor.py`) - Browser automation for token/cookie capture
4. **aiohttp** (`src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/services/downloader.py`) - HTTP client with retry logic

---

## SSL Verification Deep Dive (Research)

### Analysis of HttpClient SSL Handling (http_client.py:50-57)

```python
if self.settings.ssl_verify:
    connector = aiohttp.TCPConnector()
else:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    logger.warning("ssl_verification_disabled", message="SSL certificate verification is disabled - connections may be insecure")
```

**Behavior:**
- When `ssl_verify=True` (default): Uses default SSL context with verification enabled
- When `ssl_verify=False`: Creates SSL context with `CERT_NONE` mode, skips hostname verification

### Analysis of yt-dlp SSL Handling (downloader.py:919-936)

```python
ydl_opts = {
    ...
    "nocheckcertificate": True,  # Line 924 - HARDCODED
    ...
}
```

**Problem:** The `nocheckcertificate` option is hardcoded to `True`, ignoring `settings.ssl_verify`.

**yt-dlp Documentation:**
- `nocheckcertificate` (or `no_check_certificate` in older docs) corresponds to `--no-check-certificate`
- When `True`: Disables SSL certificate verification
- When `False`/omitted: Uses system certificate store for verification (default secure behavior)

### FFmpeg SSL Verification Analysis

**Research Findings (ffmpeg.org official documentation):**

1. **TLS Protocol Options:** FFmpeg supports `-tls_verify` and `-tls_ca_file` options for the `tls://` protocol (used for RTMPS/RTSPS)
2. **HTTPS Input:** For HLS streams accessed via `https://` URLs, FFmpeg relies on the underlying TLS library (OpenSSL/GnuTLS)
3. **Default Behavior:** Modern FFmpeg builds enable certificate verification by default for HTTPS input
4. **No `-tls_verify` for HTTPS:** The `-tls_verify` option is specifically for the `tls://` protocol, not `https://` URLs
5. **CA Certificate Handling:** FFmpeg uses system CA bundle on Linux (`/etc/ssl/certs/ca-certificates.crt`) and Windows certificate store

**Conclusion for ffmpeg:** No SSL options are needed or appropriate. FFmpeg's HTTPS input handling uses system certificates and modern builds verify by default.

### Specific Recommendation

**Merge INT-006 and INT-007 into a single targeted fix for yt-dlp only.**

#### Exact Code Change Required

**File:** `src/vkdownloader/services/downloader.py`  
**Line:** 924

**Change:**
```python
# BEFORE
"nocheckcertificate": True,

# AFTER
"nocheckcertificate": not settings.ssl_verify,
```

This single-line change ensures:
- When `ssl_verify=True` (default): `nocheckcertificate=False` → certificate verification enabled
- When `ssl_verify=False`: `nocheckcertificate=True` → certificate verification disabled

#### Why ffmpeg Needs NO Changes

1. **No `-tls_verify` support for HTTPS input:** The option applies to `tls://` protocol (RTMPS), not HLS over HTTPS
2. **Default secure behavior:** Modern FFmpeg builds verify HTTPS certificates by default
3. **System CA integration:** FFmpeg uses OS certificate store - no configuration needed
4. **Use case mismatch:** The `-tls_verify` option is for RTSPS/RTMPS, not HLS segment fetching

#### Updated Advisory Recommendation

**Merged Recommendation (INT-006 + INT-007):** Fix yt-dlp SSL verification to respect `settings.ssl_verify`

| Field | Value |
|-------|-------|
| **ID** | INT-SSL |
| **Priority** | HIGH (for spec deviation) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` line 924 |
| **Required Change** | Change `"nocheckcertificate": True` to `"nocheckcertificate": not settings.ssl_verify` |
| **ffmpeg Action** | NO ACTION NEEDED - uses system certificates with default verification |