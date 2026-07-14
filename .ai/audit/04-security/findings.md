# Phase 04 Audit Findings — Security & Secret Management

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### SEC-001: Test asserts wrong default for ssl_verify due to .env override

| Field | Value |
|-------|-------|
| **ID** | SEC-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_config.py:20, .env:12 |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` asserts that `settings.ssl_verify is True`, but the `.env` file on line 12 sets `VKDOWNLOADER_SSL_VERIFY=false`. Pydantic Settings loads environment variables before applying defaults, so the test receives `False` instead of `True`. This masks a real security concern: SSL verification is disabled by default in the environment configuration, which creates insecure connections to CDN endpoints.

**Evidence:**
- `.env:12` contains `VKDOWNLOADER_SSL_VERIFY=false`
- `tests/test_config.py:20` asserts `settings.ssl_verify is True` which fails with `AssertionError: assert False is True`
- Config model at `config.py:47-50` shows the intended default is `True`

**Recommendation:** Fix the test to check the actual behavior: either set `ssl_verify=True` in `.env` for secure defaults, or update the test to account for the `.env` override. The secure option is to remove the override and let the default `True` stand, since SSL verification is a security-critical setting. Effort: trivial. Priority: mandatory.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 0 |

## Mandatory Fixes

- SEC-001: Test asserts wrong default for ssl_verify due to .env override

## Advisory Recommendations

none

## Doc Updates Needed

none

---