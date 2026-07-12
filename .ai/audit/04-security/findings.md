---
name: audit-findings
description: Security & Secret Management Audit Findings
agent: auditor
status: complete
validated: no
template: .ai/audit/templates/audit-findings.md
---

# Phase 04 Audit Findings — Security & Secret Management

**Executor:** auditor  
**Template:** .ai/audit/templates/audit-findings.md  
**Status:** complete  
**Validated:** no

---

## Findings

### SEC-001: HTTP client logs URLs without sanitization potentially exposing auth tokens

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/infrastructure/http_client.py` |
| **Classification** | mandatory |

**Description:** `HttpClient.download_file()` logs full URLs including query parameters at line 174. While `url_sanitizer._strip_auth_params()` exists and is used elsewhere (downloader.py, downloader_throttle.py), it is NOT applied to the URL before logging in http_client.py. This creates an information disclosure risk where authentication tokens or other sensitive query parameters could accidentally be logged.

**Evidence:**
```python
# src/vkdownloader/infrastructure/http_client.py:174
logger.info("download_completed", url=url, path=str(output_path))
```

The logger call passes `url` directly without sanitization. Compare with other modules that properly sanitize:
```python
# src/vkdownloader/services/downloader.py:997
logger.info("starting_download", url=_strip_auth_params(url), ...)
```

**Recommendation:** Apply `_strip_auth_params()` to the URL before logging in `http_client.py:174` and `http_client.py:177`. This ensures consistent security posture across all HTTP operations.

---

### SEC-002: SSL verification can be globally disabled creating MITM vulnerability

| Field | Value |
|-------|-------|
| **ID** | SEC-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** The `Settings.ssl_verify` option (default `True`) allows users to disable SSL certificate verification. When disabled, the code creates an SSL context with `check_hostname=False` and `verify_mode=ssl.CERT_NONE`, leaving all HTTPS connections vulnerable to man-in-the-middle attacks. Combined with the logging issue (SEC-001), this could expose credentials to network attackers.

**Evidence:**
```python
# src/vkdownloader/infrastructure/http_client.py:49-57
if self.settings.ssl_verify:
    connector = aiohttp.TCPConnector()
else:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    logger.warning("ssl_verification_disabled", message="SSL certificate verification is disabled - connections may be insecure")
```

**Recommendation:** Consider removing the `ssl_verify` option entirely or adding additional safeguards (e.g., require explicit user confirmation, limit scope, or fail loudly). At minimum, document the security implications prominently. The current warning at INFO level may not be sufficient.

---

### SEC-003: Broken test file with syntax error prevents test execution

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `tests/test_hls_downloader_patch.py` |
| **Classification** | mandatory |

**Description:** The file `tests/test_hls_downloader_patch.py` contains a `nonlocal` statement referencing a variable that doesn't exist in an enclosing scope, causing a `SyntaxError` that prevents pytest from collecting tests. This masks real security test failures.

**Evidence:**
```python
# tests/test_hls_downloader_patch.py:1-5
async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
            nonlocal gather_called
            gather_called = True
            # Return True for each task
            return [True] * len(tasks)
```

The `nonlocal gather_called` fails because `gather_called` is never declared in an enclosing scope. Additionally, `Any` is not imported, causing `F821 Undefined name 'Any'` error.

**Recommendation:** Either fix the test file (add proper imports and define `gather_called` in enclosing scope) or remove it if it's incomplete/discarded code.

---

### SEC-004: Global shutdown event causes cross-test contamination in async tests

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `tests/test_downloader_throttle.py`, `tests/test_hls_downloader.py` |
| **Classification** | mandatory |

**Description:** The `_shutdown_event` global in `downloader_throttle.py` is an `asyncio.Event` that gets bound to a specific event loop on first access. When tests run in different event loops, the event cannot be waited upon, causing `RuntimeError: 'asyncio.locks.Event object is bound to a different event loop'`. This breaks 10 tests and indicates a potential concurrency bug.

**Evidence:** Test output shows:
```
RuntimeError: '<asyncio.locks.Event object at 0x000001C5A770C470 [unset]> is bound to a different event loop'
```

The issue originates in:
```python
# src/vkdownloader/services/downloader_throttle.py:100-102
try:
    await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
```

**Recommendation:** Reset the global `_shutdown_event` between tests or use a context-local/event-loop-aware pattern. Add a `reset_shutdown_event()` function for testing, and consider whether the global pattern is appropriate for production use.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 0 |

## Mandatory Fixes

1. SEC-001: Apply URL sanitization in http_client.py before logging URLs
2. SEC-002: Review/remove SSL verification disable capability or add stronger safeguards
3. SEC-003: Fix broken test file `test_hls_downloader_patch.py`
4. SEC-004: Fix global shutdown event cross-test contamination

## Advisory Recommendations

None

## Doc Updates Needed

None

---

## Verification Commands Output

**Ruff Check:** 13 errors found (import sorting, unused variables, deprecated `asyncio.TimeoutError` usage)

**Mypy Check:** 4 errors in src files (unused type ignores, coroutine attribute errors)

**Test Results:** 10 failed, 170 passed (1 broken test file, 9 failures due to event loop contamination)

---

## Audit Notes

### Positive Security Practices Found

- No hardcoded secrets (api_id, api_hash, bot_token) in source code
- `.env` file contains only commented placeholders, no real credentials
- `.gitignore` excludes `.env` (though missing session/credentials file patterns)
- URL sanitizer (`_strip_auth_params`) properly strips auth params: token, access_token, auth, auth_token, session, session_id, sid, key, signature, sig, expire, expires, expires_in, timestamp, nonce, hash, hmac, secret
- Path traversal prevention implemented in `validate_output_path()` with ".." detection
- SSL verification disabled produces a warning log message