# Execution Plan — Plan 15: Test Coverage & Oracles

**Source plan:** `.ai/plans/15-test-coverage-audit-fixes.md` (baselined at `58bb7ce`)
**Current HEAD:** `151ea9f`
**Auditor report:** `.ai/audit/orphaned-files/plan-15-vs-current-tree-audit-report.md`
**Last updated:** 2026-10-12

## State Summary

The plan was baselined against commit `58bb7ce` (755 collected tests, `requires-python >=3.12`).
Since then, sibling plans (11, 12, 13, 16, TRN-008/B13) have moved the tree. The current tree
at `151ea9f` has **~1100 collected tests** (1097 passed, 3 skipped, 0 failed).

### Per-Block Status (at `151ea9f`)

| Block | Status | Detail |
|-------|--------|--------|
| P15-B1 | **DONE** (prior plan) | P11-B1 `f6e8ebe` — SEC-009 product fix + host-only cookie tests. Divergence: new `_cookie_with_domain` helper vs builder parameterization. |
| P15-B2 | **PENDING** | Exit code 3 partition done (`56258e2`), but **positive log-record oracle MISSING** — no test parses log as JSON or asserts a named event's presence. |
| P15-B3 | **PENDING** | Stale non-reproduction paragraph still in `findings.md:881-889`. Must strike + add measured shape table. |
| P15-B4 | **PENDING** | `test_validate_output_path_rejects_traversal_even_if_resolved` still has old name. Plan 12 added a separate test but didn't rename. |
| P15-B5 | **PENDING** | `VideoNotFoundError` arm for `download` command not directly driven. Exit-code partition exists via P15-B2. |
| P15-B6 | **DONE** (prior plan, DIVERGENT) | P13 `5fe961f` changed help-text test to assert ffmpeg IS mentioned (opposite of plan's "exclude" intent). `TestMethodFfmpegRemoved` has 7 tests. Acceptance: recorded, not re-done. |
| P15-B7 | **PENDING** | NEW-08 done (`24dcddc`), but NEW-03 (bare MagicMock in `TestMergeSegmentsBatchedRealExecution`) NOT fixed. Format precondition STALE: 5 files RED, not 2. |
| P15-B8 | **DONE** (prior plan) | TRN-008/B13 — OSError arms in `ffmpeg_utils.py:390,455` + `TestB13MergeMissingMuxer` oracle. |
| P15-B9 | **PENDING** | `_parse_retry_after` HTTP-date + `_await_and_cancel` body now covered. **Six graceful-degradation arms NOT entered.** `TestGracefulDegradation` doesn't exist. |
| P15-B10 | **PENDING** | No `[tool.pytest.ini_options]` in pyproject.toml. `requires-python` already `>=3.14`, `target-version` already `py314`. |
| P15-B11 | **PENDING** | `tests/integration/__init__.py` exists, 0 tests. No stale `.pyc` found. Route (c) default. |
| P15-B12 | **PENDING** | 3 `TST-` prefixed identifiers in test tree (test_cli.py:502, test_hls_downloader.py:369, test_hls_downloader.py:3436). |
| P15-B13 | **DONE** (prior plan) | Census exemptions in `audit-orphaned.md` (`e9bafb2`). |
| P15-B14 | **PENDING** | `.ai/context/test-oracle-inventory.md` does not exist. Must be last. |

### Revised Execution Order

```
B2 → B3 → B4 → B5 → B7 → B9 → B10 → B11 → B12 → B14
(B1, B6, B8, B13 already done — skipped)
(B8 independent, already done)
```

### Key Discrepancies from §2 Baseline

| Figure | §2.4 Claim | Actual (at `151ea9f`) | Impact |
|--------|-----------|------------------------|--------|
| Test suite collected | 755 | ~1100 | Floor identity updated |
| `requires-python` | `>=3.12` | `>=3.14` | Decision D done by plan 16 |
| `target-version` | `py312` | `py314` | Decision D done by plan 16 |
| Format RED files | 1 (test_hls_downloader.py) | 5 files | B7's precondition stale |
| `cli.Settings` patches | 24 | 35 | P14-B4 progress |
| `create_subprocess_exec` patches | 37 | ~56 | Suite grew 48% |
| `logger.exception` in src | 3 | 4 | `clean-cookies` command added |
| Skip floor | 3 | 3 | Unchanged ✓ |

## Revised Floor

```
uv run pytest -q -rs  →  1097 passed, 3 skipped, 0 failed
collected − xfailed − skipped ≥ 1094  (floor adjusted for growth)
Skip count: exactly 3 (all POSIX-only)
```

## Format Gate Note

`ruff format --check src tests` is RED on 5 files: `test_cli.py`, `test_config.py`,
`test_downloader_throttle.py`, `test_hls_downloader.py`, `test_segment_downloader.py`.
All diffs are mechanical (line-length wrapping). The plan's §2.1.2 described 2 specific
`with patch(...)` sites that no longer exist in `TestYtDlpSubprocessShutdown`.

P15-B7 must re-derive the format precondition from the current tree. The narrow-fallback
rule (no whole-file reformat) still applies. See the per-block Auditor for B7.

## Blocks Already Implemented — No Action

These blocks are complete. Their work is recorded here for the P15-B14 inventory's
status column:

- **P15-B1** — `f6e8ebe` (P11-B1): host-only cookie via consumer. Divergence noted.
- **P15-B6** — `5fe961f` (P13): method removal regression net. Divergence noted.
- **P15-B8** — `e6e6c68` + `0c704de` (TRN-008/B13): missing-binary oracle + OSError arms.
- **P15-B13** — `e9bafb2`: census exemptions in protect-list.

---

## Block Sequencing (Revised)

```
CRITICAL (test_cli.py writer): B2 → B3 → B4 → B5 → B7
PARALLEL (independent files):  B10, B11, B12
DEPENDENT (B9 needs B7's exec-stub): B9
FINAL: B14 (after all above)
```

B2 and B3 share `test_cli.py` and `findings.md` respectively. B2 must precede B3 because
B3's corrected wording must match B2's oracle. B5 and B7 both write test_cli.py /
test_hls_downloader.py — B5 precedes B7 by file (test_cli.py) and B7 precedes B9 by file
(test_hls_downloader.py).
