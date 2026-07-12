---
name: 04-security-validated-findings
description: Validated findings for Security & Secret Management Phase
agent: validator
validated: yes
---

# Phase 04 Validated Findings - Security & Secret Management

**Source:** `.ai/audit/04-security/findings.md`  
**Validated:** yes  
**Validation Date:** 2026-07-11

---

## Cross-Finding Analysis

### Duplicate Findings Across Phases

| Original ID | Duplicate IDs | Target for Merge |
|-------------|---------------|-----------------|
| SEC-003 | TST-001, CFG-003, SRV-001 | TST-001 (Phase 07) |
| SEC-004 | TST-002, CFG-007, SRV-002 | CFG-007 (Phase 02) |

### Cross-Phase Conflicts

No conflicts detected. All phases consistently report the same issues.

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

The `_strip_auth_params` function is imported in `downloader.py` (line 21) and `downloader_throttle.py` (line 10), but NOT in `http_client.py` - confirming the omission.

**Recommendation:** Apply `_strip_auth_params()` to the URL before logging in `http_client.py:174` and `http_client.py:177`. This ensures consistent security posture across all HTTP operations.

---

### SEC-002: ~~SSL verification can be globally disabled creating MITM vulnerability~~ [REJECTED]

> **Rejection reason:** The `ssl_verify` setting is intentional and documented in `docs/11-guides/configuration.md` (lines 89-94): "Default: `true` — Secure by default" and "Setting to `false` — Logs a security warning; use only for edge cases". This is a valid use case for corporate proxies with self-signed certificates or other edge cases. The code already logs a warning (`logger.warning("ssl_verification_disabled", ...)`) when SSL verification is disabled. This is a deliberate user-configurable option with appropriate documentation and warning, not a security flaw.

---

### SEC-003: ~~Broken test file with syntax error prevents test execution~~ [MERGED]

> **Validation Note:**
> - **Action:** merged
> - **Detail:** Same finding as TST-001 (Phase 07), CFG-003 (Phase 02), and SRV-001 (Phase 03). Merged into TST-001 for consolidated tracking.
> - **See also:** TST-001 (Phase 07)

| Field | Value |
|-------|-------|
| **ID** | SEC-003 |
| **Severity** | CRITICAL |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `tests/test_hls_downloader_patch.py` |
| **Classification** | mandatory |

**Description:** The file `tests/test_hls_downloader_patch.py` contains a `nonlocal` statement referencing a variable that doesn't exist in an enclosing scope, causing a `SyntaxError` that prevents pytest from collecting tests.

**Evidence:**
```python
# tests/test_hls_downloader_patch.py:1-5
async def mock_gather(*tasks: Any, **kwargs: Any) -> list[bool]:
    nonlocal gather_called
    gather_called = True
    return [True] * len(tasks)
```

Runtime verification confirms: `SyntaxError: no binding for nonlocal 'gather_called' found` and tests fail to collect.

**Recommendation:** Remove this orphaned file as it provides no test value and blocks all test execution.

---

### SEC-004: ~~Global shutdown event causes cross-test contamination in async tests~~ [MERGED]

> **Validation Note:**
> - **Action:** merged
> - **Detail:** Same finding as CFG-007 (Phase 02), SRV-002 (Phase 03), and TST-002 (Phase 07). Merged into CFG-007 for consolidated tracking.
> - **See also:** CFG-007 (Phase 02)

| Field | Value |
|-------|-------|
| **ID** | SEC-004 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `tests/test_downloader_throttle.py`, `tests/test_hls_downloader.py` |
| **Classification** | mandatory |

**Description:** The `_shutdown_event` global in `downloader_throttle.py` is an `asyncio.Event` that gets bound to a specific event loop on first access. When tests run in different event loops, the event cannot be waited upon, causing `RuntimeError: 'asyncio.locks.Event object is bound to a different event loop'`.

**Evidence:**
```python
# src/vkdownloader/services/downloader_throttle.py:17-26
_shutdown_event: asyncio.Event | None = None

def get_shutdown_event() -> asyncio.Event:
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()  # Bound to first event loop
    return _shutdown_event
```

The Event created in one test's event loop is reused in another test's event loop, causing the binding error.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 1 | SEC-001 |
| Reclassified | 0 | — |
| Merged | 2 | SEC-003 → TST-001, SEC-004 → CFG-007 |
| Rejected | 1 | SEC-002 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| SEC-002 | SSL verification can be globally disabled creating MITM vulnerability | Intentional user-configurable feature with documented use case; secure-by-default with warning log; not a security flaw |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| SEC-003 | TST-001 (Phase 07) | Same broken test file issue reported across 4 phases |
| SEC-004 | CFG-007 (Phase 02) | Same global shutdown event issue reported across 4 phases |

### Reclassified Findings

None.

---

## Rollout Analysis

**No rollout safety issues detected within this phase.** The findings are isolated to:
- A security logging inconsistency (SEC-001) that can be fixed independently
- A broken test file (merged) that blocks test execution but doesn't affect production code
- An event loop configuration issue (merged) that affects testability but is architectural

---

## Warnings

- **CFG-007 / SEC-004**: Global `_shutdown_event` causes event loop binding failures - cross-phase architectural risk already tracked
- **TST-001 / SEC-003**: `test_hls_downloader_patch.py` syntax error blocks all test collection - cross-phase runtime issue

---

## Required Fixes

1. **SEC-001**: Apply URL sanitization in http_client.py before logging URLs (HIGH severity) - Security logging inconsistency
2. **CFG-003**: Fix broken test file `test_hls_downloader_patch.py` (CRITICAL severity) - Blocks all test execution

> Note: SEC-003 merged into TST-001; fix already tracked in Phase 07 validation.

---

## Advisory Recommendations

None.