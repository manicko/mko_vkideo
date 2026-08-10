# Phase 07 Audit Findings - Test Quality (VALIDATED)

**Executor:** validator
**Template:** .kilo/commands/audit/phases/99-audit-validate.md
**Status:** complete
**Validated:** yes (validator agent - 2026-08-09)
**Source:** .ai/audit/07-audit-tests/findings.md
**System under audit:** vkdownloader v0.1.0 - VK Video Downloader CLI (Python 3.12, uv, MIT).

---

## Validator Scope

Validated against the live source tree at `src/vkdownloader/` and `tests/`. Line-number anchors in the source findings were re-checked against the files as they exist today. Runtime evidence was re-verified with the project's own commands (`uv run ruff`, `uv run mypy`, `uv run pytest`) and by direct inspection of the implementations referenced by each finding.

## Verification Results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| V1 - Full test suite | `uv run pytest` | PASS | 325 passed (R1/R2 in source findings; spot-checked targeted subset: 9 passed). No failures, no skips. |
| V2 - Lint (tests) | `uv run ruff check tests/` | FAIL (1 error, pre-existing) | F841 at `tests/test_correlation.py:28` (unused `full`) - confirmed identical to CLI-003 Phase 01. |
| V3 - Type-check (tests) | `uv run mypy tests/` | FAIL (15 errors) | 15 `no-untyped-def` errors at exactly the lines listed by TST-003 (10 in `test_downloader_throttle.py`, 5 in `test_hls_downloader.py`). |
| V4 - Implementation inspection | direct source read | PASS | `cli.py:400-405` prints `Failed URLs:` with status text; `cookies.py:58`, `downloader.py:71-95`; `correlation.py:22`; `exceptions.py:75,109`. |

---

## Cross-Phase Analysis

### Duplicates / Merge Candidates

| Finding | Related Phase Finding | Action |
|---------|-----------------------|--------|
| TST-001 | CLI-003 (Phase 01) | **DUPLICATE - REJECTED.** Same root cause: unused `full` at `test_correlation.py:28`, F841, in `test_generate_correlation_id_truncates_uuid`. Phase 08 R1/R3 explicitly restate it as runtime evidence ("CLI-003/TST-001") and do NOT re-file. CLI-003 is mandatory and higher-priority (HIGH). |
| TST-005 | SRV-002 (Phase 03) | **DUPLICATE - REJECTED.** Same root cause: `_write_netscape_cookie_file` (`cookies.py:58-74`) defined + exported in `__all__` with zero callers; live path is `_create_temp_cookie_file`. Phase 08 R3 explicitly states "_write_netscape_cookie_file dead code already filed SRV-002 (phase 03)". Phase 04 SEC-005 (permission semantics) and Phase 06 DF-007 (live-path permissions) further cover the security angle. |

### Cross-Phase Conflicts

None detected. No phase asserts "all commands/tests pass" while another asserts a test/command fails. Test-suite results are consistent across Phases 01-08 (325 passed).

### Dependency Chains

- **TST-004 -> DF-007 (Phase 06):** TST-004 recommends a unit test asserting `_create_temp_cookie_file` writes permissions of `0o600`. The current implementation uses `tempfile.mkstemp` (downloader.py:87), which on Unix with default umask `022` yields `0644` (no `os.chmod`). A permission-assertion test would FAIL against current code; it is only meaningful after DF-007's mandatory `os.chmod(path, 0o600)` fix. Sequence recommendation: apply the DF-007 fix first, then add the TST-004 tests to lock the guarantee.
- **TST-005 -> SRV-002 (Phase 03) / DF-007 (Phase 06):** Consolidation of the dead function must be coordinated with the live-path permission fix so cookie-file creation is consolidated into one secured path.
- No circular dependencies.

---

## Findings

### TST-001: ~~Unused variable full with misleading docstring~~ [REJECTED]

> **Rejection reason:** Duplicate of CLI-003 (Phase 01), already filed as mandatory/HIGH. Phase 08 audit-quality (R1/R3) explicitly restates `tests/test_correlation.py:28` F841 unused `full` as "filed CLI-003 (phase 01) / TST-001 (phase 07)" and does not re-file. Grep confirms the single source location: `correlation.py:22` returns `uuid.uuid4().hex[:8]`; the unused `full` is at `test_correlation.py:28`.
>
> **Additional defect in this finding:** TST-001's preferred fix (`assert full.startswith(cid)`) is technically incorrect. `full = uuid.uuid4().hex` and `cid = generate_correlation_id()` are independently generated random uuid4 hexes, so `full.startswith(cid)` would be false ~99.99% of the time. CLI-003's sounder recommendation ("restore the assertion or remove the line") is the correct direction - remove `full` and fix the misleading docstring. Canonical fix tracked under CLI-003.

### TST-002: test_batch_statistics_summary under-asserts error reasons [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory, LOW)**

**Verification:**

`_print_batch_summary` (cli.py:372-409) prints a `Failed URLs:` block with `typer.echo(f"    - {url}: {status}")` (cli.py:400-405). The `status` value for each failure originates from `_download_single` (cli.py:241-262), which maps exceptions to status labels: `QualityNotAvailableError` -> `e.status_label()` (cli.py:242), `VideoNotFoundError` -> `e.status_label()` (cli.py:244), `ExtractionError` -> `e.status_label()` (cli.py:252), `VKDownloadError` -> `e.status_label()` (cli.py:254), and generic `Exception` -> `_map_exception_to_status(e)` (cli.py:262). `status_label()` is confirmed to exist on `VideoNotFoundError` (exceptions.py:75) and `QualityNotAvailableError` (exceptions.py:109).

The implementation therefore emits concrete error-reason text into stdout. However, `test_batch_statistics_summary` (test_cli.py:155-203) asserts only `exit_code == 1` and the section headers `Download Summary:`, `Total connections:`, `Peak concurrency:`, `Successful:`, `Failed:` (lines 198-203). It never asserts on `Failed URLs:` or any status-label text. The docstring (line 156) claims to verify "failed URLs with error reasons"; the assertions do not. A regression stripping error-reason display would not be caught.

**Note on a secondary inaccuracy:** The finding's setup description ("first URL returns MagicMock with streams=[] -> QualityNotAvailableError") is misleading - the test mocks `QualitySelector` entirely (test_cli.py:170-180) with `select.return_value = MagicMock(quality="720")`, so the first URL effectively succeeds via the mock and does not raise `QualityNotAvailableError`. The second URL raises `VideoNotFoundError` in `extract_streams`. This does not invalidate the core finding: error reasons ARE produced for the failing URL, and the test does not assert them.

**Recommendation stands:** Add assertions verifying the specific error-reason/status text appears in the `Failed URLs:` output. Effort: small.

---

### TST-003: 15 missing type annotations on inner test helper functions [APPROVED]

> **Validator Decision:** **VALIDATED -- SPEC-DEVIATION (advisory, LOW)**

**Verification:**

`pyproject.toml:73-84` configures `[tool.mypy]` with `strict = true`, `disallow_untyped_defs = true`, `disallow_incomplete_defs = true`, `warn_return_any = true`. Running `uv run mypy tests/` produces exactly 15 `no-untyped-def` errors at the 15 line numbers cited (10 in `test_downloader_throttle.py`: 59, 100, 167, 207, 247, 287, 351, 458, 566, 582; 5 in `test_hls_downloader.py`: 1752, 1858, 1988, 2026, 2031). Spot-checked each site: all are inner `def`/`async def` helpers used as `side_effect` callbacks (`def get_side_effect(*args, **kwargs)`, `async def mock_wait_for(coro, timeout)`, `def mock_get(*args, **kwargs)`, `async def mock_communicate()`, `def track_batch(*cmd, **kwargs)`).

The project rule #9 mandates "Type Safety Everywhere." Note: current CI only runs `mypy src/vkdownloader` (Phase 01 R1), not `mypy tests/`, so this is a latent gate - it would break CI if `mypy tests/` is added. The untyped helpers are real, the line numbers match, and the fix is trivial-to-small with positive ROI (enables type-checking tests, improves IDE support).

**Recommendation stands:** Add type annotations to all 15 inner helper functions. Effort: small.

---

### TST-004: _create_temp_cookie_file lacks direct unit tests for security-sensitive behavior [APPROVED]

> **Validator Decision:** **VALIDATED -- BEST-PRACTICE (advisory, MEDIUM)**

**Verification:**

`_create_temp_cookie_file` is defined at `downloader.py:71-95`: it calls `_cookies_to_netscape(cookies)` (cookies.py:13), then `tempfile.mkstemp(suffix=".cookies.txt", prefix="vk_cookies_")` (downloader.py:87), `os.write`/`os.close` (downloader.py:89-90), with a `try/except` cleanup (downloader.py:91-94). It is called at downloader.py:318 and 321 inside `_resolve_cookies`.

Grep for `_create_temp_cookie_file` across `tests/` returns **zero** direct references. The only relevant test is `test_cookies_passed_to_ytdlp_creates_cookie_file` (test_hls_downloader.py:896-935), which exercises `_download_with_ytdlp` end-to-end and asserts the `--cookies` flag is in the captured command plus that the temp file is cleaned up (test_cli.py assertion at line 935). It does NOT directly invoke `_create_temp_cookie_file` and asserts none of: (1) file permissions, (2) Netscape-format content, (3) write-error handling, (4) temp-dir location vs. the download output directory.

The finding's underlying claim is correct: there is no direct unit test for this security-sensitive helper (it writes live VK session cookies to disk). The source evidence notation "grep ... > 0 direct references" is garbled (should read "= 0"); grep confirms zero.

**Dependency:** A test asserting `0o600` permissions would fail against current code (mkstemp + umask 022 -> 0644) until the Phase 06 DF-007 fix (`os.chmod(path, 0o600)`) is applied. Recommend sequencing DF-007's fix before the TST-004 permission test.

**Recommendation stands:** Add dedicated unit tests covering permissions, content format, temp-dir location, and the write-error cleanup path. Effort: medium.

---

### TST-005: ~~Dead code _write_netscape_cookie_file with divergent security implementation~~ [REJECTED]

> **Rejection reason:** Duplicate of SRV-002 (Phase 03), already validated. Grep confirms `_write_netscape_cookie_file` appears ONLY at its definition (cookies.py:58) and `__all__` export (cookies.py:77); zero call sites in `src/` or `tests/`. This is identical to SRV-002 (Phase 03, validated, BEST-PRACTICE) and the security-angle variant SEC-005 (Phase 04, planned) / DF-007 (Phase 06, validated). Phase 08 R3 restates this exact dead-code fact and attributes it to SRV-002. Consolidating the dead/unused function is already tracked under SRV-002 and the Phase 06 DF-007+SRV-002 consolidation item - no separate action needed here.

---

### TST-006: Fragile generator-expression hack for CancelledError simulation [APPROVED]

> **Validator Decision:** **VALIDATED -- BEST-PRACTICE (advisory, LOW)**

**Verification:**

At test_hls_downloader.py:2260: `mock_stdout_line: list[bytes] = []` (empty list). At line 2261 the side-effect is `lambda: (_ for _ in ()).throw(asyncio.CancelledError()) if not mock_stdout_line else mock_stdout_line.pop(0)`. Since `mock_stdout_line` is an empty list, `not mock_stdout_line` is always `True`, so the `else mock_stdout_line.pop(0)` branch is dead code within the test. The `(_ for _ in ()).throw(...)` idiom is a non-obvious, fragile way to raise `asyncio.CancelledError` and may confuse maintainers or behave differently across Python minor versions.

The test passes (confirmed in V1), so the harness currently exercises the intended `CancelledError` path via the `if` branch. Replacing the lambda with a named `async def mock_readline(): raise asyncio.CancelledError()` preserves behavior, removes the dead `else` branch, and improves readability. ROI is clearly positive (trivial change, maintenance clarity).

**Recommendation stands:** Replace the generator-expression lambda with a named function. Effort: trivial.

---

### Cross-Phase Finding CP-01: TST-001 is a duplicate restatement of CLI-003 (Phase 01)

> **Validator Decision:** **REJECTED (duplicate)**

`test_correlation.py:28` F841 (unused `full`) is filed as CLI-003 in Phase 01 (mandatory/HIGH) and restated as R1 lint evidence in Phase 08 (R3) — which explicitly labels it "CLI-003/TST-001" and says it is not re-filed. TST-001 re-asserts the same defect with a weaker fix recommendation. No action required beyond CLI-003.

### Cross-Phase Finding CP-002: TST-005 overlaps SRV-002 (Phase 03), SEC-005 (Phase 04), DF-007 (Phase 06)

> **Validator Decision:** **REJECTED (duplicate, complementary ownership)**

The dead `_write_netscape_cookie_file` is owned by three prior-phase findings with complementary angles: SRV-002 (dead-code/ownership, Phase 03, validated), SEC-005 (divergent permission semantics, Phase 04), and DF-007 (live-path `_create_temp_cookie_file` permissions 0644->0o600, Phase 06, validated, related-merge with SRV-002). TST-005 adds a "test" framing of the same symbol but introduces no new defect. Coordination already planned in the Phase 06 validated report.

### Cross-Phase Finding CP-003: TST-004 permission test depends on DF-007 fix (Phase 06)

> **Validator Decision:** **DEPENDENCY - sequencing required (no rejection)**

TST-004 recommends asserting `_create_temp_cookie_file` writes `0o600` permissions. Current code (`tempfile.mkstemp`, no `os.chmod`) produces `0644` under umask `022`, so the test would fail until DF-007's `os.chmod(path, 0o600)` fix is applied. Both findings are approved; they must be implemented in order (DF-007 fix, then TST-004 test) to avoid a failing test.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 3 | TST-002, TST-003, TST-006 |
| Reclassified | 0 | — |
| Merged | 0 | TST-001 and TST-005 are duplicates of findings in earlier phases (CLI-003, SRV-002), not same-phase merges; rejected instead. |
| Rejected | 2 | TST-001 (duplicate of CLI-003, PH01), TST-005 (duplicate of SRV-002, PH03) |
| Cross-phase findings added | 3 | CP-001, CP-002, CP-003 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| TST-001 | Unused variable full with misleading docstring | Duplicate of CLI-003 (Phase 01), already mandatory/HIGH. Phase 08 R3 restates it as evidence and does not re-file. TST-001's preferred fix (`full.startswith(cid)`) is also technically invalid (two independent uuid4s). |
| TST-005 | Dead code _write_netscape_cookie_file with divergent security implementation | Duplicate of SRV-002 (Phase 03, validated), with SEC-005 (Phase 04) and DF-007 (Phase 06) covering the security angle. Phase 08 R3 explicitly attributes this dead-code fact to SRV-002. |

### Reclassified Findings

(none)

### Rollout Analysis

- **TST-002, TST-003, TST-006:** Independent, test-only changes with no production code impact. Safe to apply in any order. TST-002/TST-006 are trivial; TST-003 is small. Low risk.
- **TST-004:** Depends on DF-007 (Phase 06, mandatory fix: `os.chmod(path, 0o600)` in `_create_temp_cookie_file`). The permission assertion test must be written AFTER the DF-007 fix to avoid a failing test. Sequence: DF-007 fix -> TST-004 tests.
- **No circular dependencies.** The only ordering constraint is TST-004 after DF-007.
- **TST-001/TST-005:** No rollout needed - already tracked under CLI-003 and SRV-002 in earlier phases.

### Warnings

- **Documentation inconsistency:** TST-001's evidence notation "grep ... > 0 direct references" is garbed (should be "= 0"). The finding's claim is correct (zero direct tests) but the evidence row is misleading.
- **Docstring inaccuracy:** TST-002's own setup description ("first URL ... -> QualityNotAvailableError") does not match runtime behavior because the test mocks `QualitySelector` entirely, making the first URL succeed. The core finding (under-asserted error reasons) remains valid.
- **Latent CI gate:** TST-003's errors only surface when `mypy tests/` is run; current CI runs `mypy src/vkdownloader` only (Phase 01 R1). Adding `mypy tests/` to CI would fail until TST-003 is fixed.
- **Pre-existing gates already tracked:** `ruff check` fails on CLI-003 (test correlation), `ruff format --check` drifts per CLI-005 (Phase 01), `mypy src/vkdownloader` fails on CLI-004 (Phase 01). These are out of scope for this test-quality phase but noted for consistency.

### Required Fixes (Mandatory)

| Fix | Tracked under | Action |
|-----|--------------|--------|
| Remove unused `full` / fix misleading docstring in `test_correlation.py:28` | CLI-003 (Phase 01, mandatory) | Remove `full = uuid.uuid4().hex` line; correct the test/docstring to assert what it actually verifies (8-char hex). |
| Add error-reason assertions to `test_batch_statistics_summary` | TST-002 (this phase) | Assert `Failed URLs:` and the relevant status-label text appear in output. |
| Type-annotate 15 inner test helper functions | TST-003 (this phase) | Annotate helpers in `test_downloader_throttle.py` and `test_hls_downloader.py`. |
| Add direct unit tests for `_create_temp_cookie_file` | TST-004 (this phase) | Cover permissions, Netscape format content, temp-dir location, write-error cleanup. Apply AFTER DF-007 fix. |
| Replace CancelledError lambda hack | TST-006 (this phase) | Replace `(_ for _ in ()).throw(...)` lambda with named `async def mock_readline()`. |

### Advisory Recommendations (Optional)

- TST-001 (rejected): no action - tracked under CLI-003.
- TST-005 (rejected): no action - tracked under SRV-002 (remove/wire `_write_netscape_cookie_file`) and DF-007 (consolidate cookie-file writes through the secured `_create_temp_cookie_file`).
- Consider adding `mypy tests/` to CI once TST-003 is resolved, to lock in type safety for the test suite (aligns with project rule #9).
- Consider consolidating the two cookie-file writers after DF-007 + SRV-002 are both applied, removing the dead `_write_netscape_cookie_file` entirely.
