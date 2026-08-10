# Phase 07 Audit Finding -- Test Quality

**Executor:** auditor (Senior architecture auditor)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/07-audit-tests.md
**Status:** complete
**Validated:** no
**Problems-only:** yes

---

## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 -- Full test suite | python -m pytest | PASS -- 325 passed, 12.75s | 325 passed in 12.75s (run 1); 325 passed in 14.55s (run 2). No failures, no skips. |
| R2 -- Analyze failures | N/A (0 failures) | PASS -- no failures to analyze | 325/325 passed; no tracebacks. |
| R3 -- Detect tautological/no-op tests | ruff check tests/ + manual review | PARTIAL -- 2 problems | Ruff F841 at test_correlation.py:28. test_cli.py:155 under-asserts. See TST-001, TST-002. |
| R4 -- Verify test isolation | order probes | PASS -- no order dependence | Forward+reverse order: 135 passed each. No shared state leaks. |
| R5 -- Coverage gap analysis | code-path review (no coverage tool) | PARTIAL -- 2 gaps | No pytest-cov configured. See TST-004, TST-005. |

---

## Findings

### TST-001: Unused variable full with misleading docstring

| Field | Value |
|-------|-------|
| **ID** | TST-001 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_correlation.py:26-33 |
| **Classification** | advisory |

**Description:** test_generate_correlation_id_truncates_uuid assigns full = uuid.uuid4().hex at line 28 but never uses it. Docstring claims to verify the generated ID is a prefix of a uuid4 hex, but no such assertion exists. Test only checks len(cid) == 8 and int(cid, 16).

**Evidence:**
- tests/test_correlation.py:28: full assigned, never used (Ruff F841)
- Ruff: F841 Local variable full is assigned to but never used at tests/test_correlation.py:28:5

**Impact:** False sense of coverage for truncation-to-prefix relationship. If implementation returned random 8-char hex instead of uuid4 prefix, test would still pass.

**Recommendation:** Either add assert full.startswith(cid) or remove unused variable and update docstring. Effort: trivial.

---

### TST-002: test_batch_statistics_summary under-asserts error reasons

| Field | Value |
|-------|-------|
| **ID** | TST-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_cli.py:155-203 |
| **Classification** | advisory |

**Description:** Docstring says summary includes failed URLs with error reasons. Test sets up: first URL returns MagicMock with streams=[] (empty->QualityNotAvailableError), second raises VideoNotFoundError. But assertions at lines 198-203 only check section headers and exit code, NOT error reason text.

**Evidence:**
- tests/test_cli.py:155: docstring claims error reasons are verified
- tests/test_cli.py:198-203: asserts only section headers (Download Summary, Successful, Failed) -- no assert on error text

**Impact:** False sense of coverage for batch error display. Regression stripping error messages would not be caught.

**Recommendation:** Add assertions verifying specific error reason text appears in output. Effort: small.

---

### TST-003: 15 missing type annotations on inner test helper functions

| Field | Value |
|-------|-------|
| **ID** | TST-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_downloader_throttle.py (10 sites); tests/test_hls_downloader.py (5 sites) |
| **Classification** | advisory |

**Description:** Project configures mypy strict=true, disallow_untyped_defs=true (pyproject.toml:75-78). Running mypy tests/ produces 15 no-untyped-def errors on inner helper functions used as side_effect callbacks.

**Evidence:** 15 mypy errors at test_downloader_throttle.py:59,100,167,207,247,287,351,458,566,582 and test_hls_downloader.py:1752,1858,1988,2026,2031. All no-untyped-def. Example: def get_side_effect(*args, **kwargs): and async def mock_wait_for(coro, timeout):.

**Impact:** If mypy tests/ is added to CI, build fails. Reduces IDE/static-analysis quality for test maintenance.

**Recommendation:** Add type annotations to all 15 inner helper functions. Effort: small.

---

### TST-004: _create_temp_cookie_file lacks direct unit tests for security-sensitive behavior

| Field | Value |
|-------|-------|
| **ID** | TST-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py:71-95 |
| **Classification** | advisory |

**Description:** _create_temp_cookie_file writes live VK session cookies to a temp file via tempfile.mkstemp (0o600 perms). Only indirect test at test_hls_downloader.py:896 verifies file creation and cleanup but NOT: (1) file permissions are 0o600, (2) file content matches Netscape format, (3) error handling on os.write failure, (4) temp dir location vs download output dir.

**Evidence:**
- src/vkdownloader/services/downloader.py:71-95: uses tempfile.mkstemp and os.write
- Called at lines 318, 321 in _resolve_cookies
- tests/test_hls_downloader.py:896-935: indirect test only checks --cookies flag and file cleanup
- grep for _create_temp_cookie_file across tests/ > 0 direct references

**Impact:** Cookie credential file security guarantees (permissions, content, location) are not enforced by tests. Bug writing insecure perms or to synced directory would go undetected.

**Recommendation:** Add dedicated unit tests covering permissions, content, location, and write-error cleanup path. Effort: medium.

---

### TST-005: Dead code _write_netscape_cookie_file with divergent security implementation

| Field | Value |
|-------|-------|
| **ID** | TST-005 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/cookies.py:58-74; src/vkdownloader/services/downloader.py:71-95 |
| **Classification** | advisory |

**Description:** services/cookies.py:58 defines _write_netscape_cookie_file using os.open with 0o600 perms, exported in __all__ at line 77. But it is NEVER called anywhere in src/ or tests/ -- zero call sites. The actual production cookie-file writer is _create_temp_cookie_file in downloader.py:71, which uses a completely different mechanism (tempfile.mkstemp). Two divergent implementations of cookie file creation, neither directly tested.

**Evidence:**
- src/vkdownloader/services/cookies.py:58-74: definition using os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
- src/vkdownloader/services/cookies.py:77: __all__ includes _write_netscape_cookie_file
- grep for _write_netscape_cookie_file across src/ and tests/ > only definition and __all__; zero call sites
- src/vkdownloader/services/downloader.py:71-95: canonical _create_temp_cookie_file using tempfile.mkstemp

**Impact:** Maintenance confusion. Developer might fix a bug in the dead function while actual code uses _create_temp_cookie_file. Divergent permission mechanisms create security ambiguity.

**Recommendation:** Either remove _write_netscape_cookie_file and its __all__ entry, or document its purpose and add tests. Effort: trivial (remove) or small (document + test).

---

### TST-006: Fragile generator-expression hack for CancelledError simulation

| Field | Value |
|-------|-------|
| **ID** | TST-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | tests/test_hls_downloader.py:2260-2261 |
| **Classification** | advisory |

**Description:** Test test_ytdlp_cancelled_on_shutdown_returns_none simulates subprocess stdout readline raising CancelledError using an opaque one-liner lambda with generator-expression hack: (_ for _ in ()).throw(asyncio.CancelledError()). mock_stdout_line is initialized as empty list [], so the else branch (pop) is dead code within the test.

**Evidence:**
- tests/test_hls_downloader.py:2260: mock_stdout_line: list[bytes] = []
- tests/test_hls_downloader.py:2261: lambda uses (_ for _ in ()).throw(asyncio.CancelledError()) if not mock_stdout_line else mock_stdout_line.pop(0)
- not mock_stdout_line is always True (empty list), so pop(0) branch never executes

**Impact:** Future maintainers cannot easily understand or modify this test. Non-idiomatic pattern that may behave differently across Python versions.

**Recommendation:** Replace lambda with a named function: async def mock_readline(): raise asyncio.CancelledError(). Effort: trivial.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 5 |

## Advisory Recommendations

- TST-001 (LOW): Remove unused full variable in test_correlation.py:28 or add the missing prefix assertion. Effort: trivial.
- TST-002 (LOW): Add error-reason assertions to test_batch_statistics_summary (test_cli.py:155). Effort: small.
- TST-003 (LOW): Add type annotations to 15 inner test helper functions. Effort: small.
- TST-004 (MEDIUM): Add dedicated unit tests for _create_temp_cookie_file (downloader.py:71) covering permissions, content, location, write-error cleanup. Effort: medium.
- TST-005 (LOW): Investigate and either remove or document _write_netscape_cookie_file (cookies.py:58). Effort: trivial or small.
- TST-006 (LOW): Replace generator-expression lambda in test_hls_downloader.py:2261 with readable named function. Effort: trivial.
