# Plan 15 vs Current Tree — Audit Report

## Summary

**Plan 15** (`15-test-coverage-audit-fixes`) was baselined against commit `58bb7ce` and describes 14 blocks (`P15-B1`…`P15-B14`) that modify only `tests/`, `pyproject.toml`, `.ai/`, and `.kilo/commands/audit/`. The current `HEAD` is `151ea9f`. Of the 14 blocks, **6 are already fully or partially implemented** by prior plans (11, 12, 13, 16, and the TRN-008/B13 work), **5 are implemented with divergence** from the plan's specified approach, and **4 remain unimplemented**. The end-of-plan format gate (`ruff format --check`) is RED, failing the §7.2 exit criteria.

The measured support figures in §2.4 are stale — the test suite grew ~48% between baseline and HEAD (755→~1100 collected). Every §2.4 count must be re-derived, not assumed.

---

## Measured Baselines (Current Tree at `151ea9f`)

| Check | Result | Plan §2.1 claim |
|-------|--------|-----------------|
| `git rev-parse --short HEAD` | `151ea9f` | n/a |
| `uv run pytest -q -rs` | 1097 passed, 3 skipped, 0 failed (81.32s) | 752 passed, 3 skipped, 755 collected |
| `uv run ruff check src tests` | All checks passed! | not claimed |
| `uv run ruff format --check src tests` | RED — 5 files reformatted | RED — 1 file (`test_hls_downloader.py`) |
| `uv run mypy src` | Success: 0 issues, 32 source files | 31 source files |
| `uv run pytest tests/test_packaging.py --collect-only` | 14 tests collected | 14 tests |
| `patch("vkdownloader.cli.Settings")` in tests/ | **35** sites | 24 |
| `patch("asyncio.create_subprocess_exec")` in tests/ | **~56** patch calls | 37 |
| `aiohttp` references in tests/ | 4 code imports + 4 comments/docstrings | 4 |
| `chmod` / `os.chmod` in tests/ | Multiple (test_config.py: 4 real calls, test_hls_downloader.py: 3) | 4 (3 skip reasons + 1 real) |
| `logger.exception` in src/ | 4 code calls (cli.py ×3, batch_downloader.py ×1) + 1 docstring (config.py) | 3 (cli.py ×2, batch_downloader.py ×1) |
| `os.replace` in tests/ | 0 | 0 ✓ |
| `mix_stderr` in tests/ | 0 | 0 ✓ |
| `create=True` in tests/ | 0 | 0 ✓ |
| `asyncio.get_event_loop` in src/ | 0 | n/a (plan risk I-18) |
| `tests/integration/__init__.py` exists | Yes (58 bytes, docstring only) | expected |
| `.ai/context/test-oracle-inventory.md` exists | **No** | new file (P15-B14) |
| `[tool.pytest.ini_options]` in pyproject.toml | **Absent** | absent (P15-B10) |
| `requires-python` in pyproject.toml | `>=3.14` | `>=3.12` (baseline) / `>=3.14` (Decision D) |
| `pytest-asyncio` floor in pyproject.toml | `>=1.1.0` | `>=0.23.0` (plan's claim) |

### Skip count (exactly 3, all POSIX-only):

1. `test_ffmpeg_utils.py:166` — `test_descendant_killed_on_posix` (killpg reaches descendants)
2. `test_ffmpeg_utils.py:189` — `test_pid_file_permissions_*` (chmod form)
3. `test_hls_downloader.py:4773` — `test_descendant_killed_on_posix` (killpg reaches descendants)

### Format diff character

The 5 RED files are: `test_cli.py`, `test_config.py`, `test_downloader_throttle.py`, `test_hls_downloader.py`, `test_segment_downloader.py`. All format diffs are **mechanical** (line-length wrapping of list comprehensions, multi-line function signatures). No semantic changes.

---

## Commits Between `58bb7ce` and `151ea9f` That Pre-empt Blocks

| Commit | Message | Pre-empts |
|--------|---------|-----------|
| `f6e8ebe` | fix(cookies): derive include_subdomains from domain dot prefix (SEC-009) | P15-B1 |
| `e6e6c68` | TRN-008: use check_ffmpeg_available return value at call site | P15-B8 (production half) |
| `0c704de` | fix(ffmpeg): correct merge multiplier 2x→3x + download-stage space probe | P15-B8 context |
| `24dcddc` | fix(ytdlp): echo=False non-progress line emits exactly one record (P13-B7) | P15-B7 (NEW-08) |
| `56258e2` | fix(cli): give configuration failures their own exit code 3 (NEW-07/Decision B) | P15-B2, P15-B5 |
| `48e4472` | fix(cookies): add clean-cookies command for legacy bare file residue (R3) | affects logger.exception count |
| `5143dfc` | build: raise Python floor to 3.14 + dev-tool floors (B10) | Decision D, P15-B10 context |
| `e9bafb2` | audit(B15): add path-based exclusion list to orphaned-files audit (VAL-124) | P15-B13 |
| `eaea694` | build: declare annotated-types in dev group (B6) | dependency context |
| `9a218ae` | build: enforce CI verification gate with coverage (B3) | gate context |
| `12af840` | fix(security): traversal detected by path component via fullmatch (ART-010/PLAN-12) | P15-B4 context |
| `151ea9f` | Fix `__all__` in downloader.py and resolve all mypy errors in tests | HEAD |

---

## Per-Block Analysis

### P15-B1 — TST-002 (host-only cookie round-trip)

**Status: ALREADY IMPLEMENTED** (by commit `f6e8ebe`)

**Evidence:**
- `src/vkdownloader/services/cookies.py:70`: `include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"` — the SEC-009 product fix landed. The literal `TRUE` is no longer hardcoded.
- `tests/test_cookies.py:187`: `test_host_only_cookie_survives_consumer_round_trip` — drives a dotless domain through the real consumer.
- `tests/test_cookies.py:211`: `test_mixed_dotted_and_host_only_cookies_survive_consumer_round_trip` — both shapes in one file.
- No `xfail` markers on either test — both shapes load successfully.
- `SEC-009` reference in test docstrings (lines 187, 211).

**Divergence from plan spec:**
- The plan (P15-B1 §3, line 1386+) describes adding a `domain` parameter to the existing `_cookie` / `_cookie_without_expiry_key` / `_cookie_with_null_expiry` builders, defaulting to `_DOMAIN`.
- The actual implementation uses a new `_cookie_with_domain` helper function instead (test_cookies.py:56-69). Both achieve the same goal — the host-only shape reaches the real consumer — but the implementation approach differs.
- Decision D-1 (line 1188) anticipated this: if `P11-B1` (SEC-009 product fix) has already landed, take route (b) with the host-only case inverted to *loads*. The implementation took the "loads" path directly.

**Recommendation:** Update plan §3 P15-B1 to reflect the actual implementation approach (new helper vs. builder parameterization). The outcome is correct; the divergence is structural, not semantic.

---

### P15-B2 — VAL-120f + NEW-07 (exit-code partition + positive log oracle)

**Status: PARTIALLY IMPLEMENTATED**

**Evidence already present:**
- `tests/test_cli.py:2605` — `test_exit_code_3_distinct_from_1` (in `TestExitCodeContract`): asserts exit 1 for download failure (`mock_download.return_value = None`) vs exit 3 for configuration error (`--max-retries 0`).
- `tests/test_cli.py:2186` — `test_download_invalid_env_var_shows_concise_error` (in `TestConfigurationErrors`): asserts `result.exit_code == 3` for invalid env var.
- `src/vkdownloader/cli.py:483-485` — `except _PreambleFailure as exc:` → `raise typer.Exit(code=3) from None` — Decision B's implementation is live.
- `docs/99-reference/cli-reference.md:82-91` — exit code table includes `3` for configuration errors, including preamble failures.

**Evidence NOT present (plan acceptance criteria unmet):**
- **Criterion 2**: "at least one named event the run provably emits is found among the records parsed from the log file, with an expected field value asserted" — **NO**. The only log-file read is at `test_cli.py:3416` (`log_contents = log_path.read_text(...)`) which asserts only **absence** of `"download_dir_empty_string_using_default"`. No positive assertion on a record the product emitted.
- **Criterion 3**: "every non-empty line of the success-path log file parses as JSON" — **NO**. No test parses the log file as JSON.
- **Criterion 4**: "THE EXIT-STATUS PARTITION IS ASSERTED AS A TABLE (D-8 route (a))" — **PARTIAL**. `test_exit_code_3_distinct_from_1` covers two cases (exit 1 vs exit 3) but is not a parameterised table. It does not enumerate all download failure arms (TST-008 says there are 25 `exit_code == 1` assertions, but the `VideoNotFoundError` arm is not specifically targeted).
- **Criterion 5**: "exactly one log parser AND one partition test exist for the tree" — **NO**. No positive log parser test exists.

**Divergence:** The plan's §1.3/§1.4 originally assigned this to P15-B2, but the findings table (§2.4, line 63) now assigns VAL-120 split: forward half → P15-B2, strike half → P15-B3. The plan text is internally inconsistent (§2.4 line 63 says "P15-B2 + P15-B3", but §3 describes P15-B2 and P15-B3 as separate blocks).

**Recommendation:** Complete criteria 2, 3, 4, and 5. Add a positive log-record assertion that parses the log file as JSON and asserts a named event (e.g., `download_dir_resolved` or `starting_download`) with an expected field value. Parameterise the exit-code partition as a table. Effort: **medium**.

---

### P15-B3 — VAL-120s (strike non-reproduction from findings.md)

**Status: NOT IMPLEMENTED**

**Evidence:**
- `.ai/audit/10-test-coverage/findings.md:881-889` still contains the stale non-reproduction paragraph:
  > "no test reads the log file's content at all (`test_config.py:328-370` asserts `.exists()` and two modes)"
- This claim is **FALSE** as of the current tree — `tests/test_cli.py:3416` reads log file content:
  ```python
  log_contents = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
  assert "download_dir_empty_string_using_default" not in log_contents
  ```
- The paragraph also claims "4 of 4 physical lines parse as JSON" from the audit phase's probe — but VAL-120's validation record (line 2010-2012) describes a more nuanced shape table (success path = 4/4 parseable, one single-link `logger.exception` record, one two-link chained record). That shape table has NOT been inserted into findings.md.

**Out of scope (confirmed untouched):**
- `.ai/audit/08-cli-observability/` and `OUT-002` — the surviving finding.
- `.ai/audit/99-validation/` — immutable.

**Recommendation:** Strike the non-reproduction paragraph (lines 881-889) and replace it with the measured shape table as VAL-120 records it. Effort: **trivial** (text edit, ~15 lines).

---

### P15-B4 — TST-004 (traversal guard rename)

**Status: NOT IMPLEMENTED**

**Evidence:**
- `tests/test_security.py:252` still has the original name: `test_validate_output_path_rejects_traversal_even_if_resolved`.
- The plan says to rename it so the event name matches the product it exercises. The traversal guard (`ART-010`) was implemented by commit `12af840` (`fix(security): traversal detected by path component via fullmatch`).
- A new test `test_post_resolution_double_dot_component_rejected` exists at `test_security.py:280` — but this was added by `P12-B1`/`P12-B2` (PLAN-12), not by P15-B4. It tests the guard but doesn't rename the old test.

**The plan's §2.4 says:** "TST-004 — STILL_PRESENT. `tests/test_security.py:195-209` claims a guard its own comments say it does not reach; `security.py:60-62` is never executed." But the product was since fixed (`12af840`), making the guard reachable. The test name is now misleading.

**Recommendation:** Rename `test_validate_output_path_rejects_traversal_even_if_resolved` to match the product's actual behavior (post-resolution path-component check). Effort: **trivial**.

---

### P15-B5 — TST-008 (VideoNotFoundError arm oracle + partition)

**Status: PARTIALLY IMPLEMENTED**

**Evidence already present:**
- `TestExitCodeContract::test_exit_code_3_distinct_from_1` (test_cli.py:2605) — proves exit 1 (download failure) ≠ exit 3 (configuration error). This is the "Decision B partition half."
- `test_batch_statistics_summary` (test_cli.py:431, in `TestBatchCommand`) — raises `VideoNotFoundError` in batch extraction at lines 442/460, asserts `"video_not_found" in result.output` at line 504.
- `TestBatchSummaryDocumentation` (test_cli.py:2823) — B9 oracle for batch summary docs consistency.

**Evidence NOT present:**
- The `download` command's `VideoNotFoundError` arm at `src/vkdownloader/cli.py:480-482`:
  ```python
  except VideoNotFoundError:
      typer.echo("Video not found. Verify the URL is correct and the video is public.", err=True)
      raise typer.Exit(code=1) from None
  ```
  This arm is reached when a user passes a valid VK URL for a deleted/private video. No test drives the `download` command (single URL) specifically through this arm.
- The plan's acceptance criterion (line 1762) requires: "a named log EVENT is asserted for the `VideoNotFoundError` arm, and the report enumerates every `download` failure arm as covered or not."
- The assertion at line 504 (`"video_not_found" in result.output`) is a **substring match on rendered output**, not a structured log event assertion. The plan's extra_context (line 1722) says "The assertion names an EVENT, not a message substring."
- The plan says "25 `exit_code == 1` assertions exist across the CLI suite" — the current count is 108 tests in test_cli.py, but the specific VideoNotFoundError oracle for the `download` command is missing.

**Recommendation:** Add a test that drives the `download` command (single URL) through the `VideoNotFoundError` arm and asserts the structured event name. The batch coverage is insufficient because the batch and download functions have separate code paths. Effort: **small**.

---

### P15-B6 — NEW-01+02 (removed `--method` surface)

**Status: ALREADY IMPLEMENTED (with divergence)**

**Evidence:**
- `src/vkdownloader/models/enums.py`: `DownloadMethod` has only `YTDLP` and `AUTO` — `FFMPEG` is absent. ✓
- `tests/test_cli.py:1929` — `TestMethodFfmpegRemoved` class exists with 7 tests:
  - `test_download_method_ffmpeg_rejected` (asserts exit 2)
  - `test_batch_method_ffmpeg_rejected` (asserts exit 2)
  - `test_method_help_text_names_ffmpeg_removal` (asserts "ffmpeg" IS in help text — **DIVERGENCE**)
  - `test_method_option_still_present_in_download_help`
  - `test_method_option_still_present_in_batch_help`
  - `test_download_ffmpeg_rejection_carries_migration_note` (asserts "was removed" in output)
  - `test_batch_ffmpeg_rejection_carries_migration_note`

**Divergence from plan spec:**
- The plan (NEW-01, line 1184) says: "Rename `test_method_help_text_excludes_ffmpeg` to `test_method_help_text_excludes_ffmpeg_from_value_list` and add the presence assertion."
- The actual implementation CHANGED the test to `test_method_help_text_names_ffmpeg_removal` which asserts `"ffmpeg" in result.output` — the OPPOSITE of the plan's intent (asserting ffmpeg IS mentioned in help, not that it's excluded from the value list).
- This divergence was introduced by commit `5fe961f` (`fix(cli): name ffmpeg removal in --method help text (P13-B17)`) — a prior plan's block, not P15-B6.
- The migration note tests (`test_download_ffmpeg_rejection_carries_migration_note`) assert `"was removed"` in output — this is a message assertion that partially satisfies the plan's "names ffmpeg" requirement.

**Recommendation:** Update plan §3 P15-B6 to describe the actual implementation (help text names the removal rather than excluding from value list; migration note tests added). The outcome satisfies the spirit of NEW-01 (ffmpeg removal is visible in help), if not the letter. Effort: **trivial** (doc update).

---

### P15-B7 — NEW-03 + NEW-08 + format precondition

**Status: PARTIALLY IMPLEMENTED**

**NEW-08 (Decision C rewrite — DONE):**
- `tests/test_hls_downloader.py:3698` — `test_ytdlp_echo_false_suppresses_stderr_while_logging_non_progress`:
  - Asserts "stderr must remain clean" (line 3741)
  - Asserts "Exactly one debug record for the non-progress line" (line 3745)
  - This IS the Decision C rewrite: one log record per line, clean stderr. Implemented by commit `24dcddc` (P13-B7).
- Two sibling `echo=False` tests (progress-line and no-callback cases) pass unmodified.

**NEW-03 (bare MagicMock — NOT FIXED):**
- `tests/test_hls_downloader.py:2909` — `TestMergeSegmentsBatchedRealExecution` class.
- `test_merge_segments_batched_success` (line 2913) uses `MagicMock(spec=asyncio.subprocess.Process)` at line 2920 WITHOUT the `_failing_exec` helper that materialises the output file.
- The plan says this is "a test that substitutes the very thing it names" — the mock never creates the output file, so the code under test takes a path a real ffmpeg would not.
- The plan raises this to HIGH under Decision A: `_merge_segments_batched` is now the product's ONLY merge path, so a wrong batching order could ship green.

**Format precondition — STALE:**
- The plan (§2.1.2, line 1919) says: "ruff format --check src tests is RED on a clean tree, on exactly two `with patch(...)` sites in `TestYtDlpSubprocessShutdown` in this file."
- **Reality**: Format is RED on **5 files** (`test_cli.py`, `test_config.py`, `test_downloader_throttle.py`, `test_hls_downloader.py`, `test_segment_downloader.py`), all with mechanical line-wrapping changes. The `TestYtDlpSubprocessShutdown` class no longer has `with patch(logger)` blocks — it was restructured to patch `cancel_subprocess` instead.
- The specific `with patch(...)` sites described in the plan no longer exist.

**Recommendation:** Fix NEW-03 by converting `TestMergeSegmentsBatchedRealExecution::test_merge_segments_batched_success` to use the `_failing_exec` helper. Re-derive the format precondition — the plan's §2.1.2 description is stale. Effort: **small**.

---

### P15-B8 — NEW-06 (merge missing-binary oracle)

**Status: ALREADY FULLY IMPLEMENTED**

**Evidence — OSError arms in source:**
- `src/vkdownloader/services/ffmpeg_utils.py:390` — `_merge_batch_segments`:
  ```python
  except OSError as exc:
      # TRN-008 / B13 arm (b): a missing ffmpeg binary surfaces here as
      # FileNotFoundError (an OSError subclass) from create_subprocess_exec.
      logger.error("merge_spawn_failed", error=str(exc), hint=_MERGE_HINT)
      return None
  ```
- `src/vkdownloader/services/ffmpeg_utils.py:455` — `_perform_final_merge`: identical `except OSError` arm logging `merge_spawn_failed`, returning `False`.

**Evidence — Oracle tests:**
- `tests/test_hls_downloader.py:5201` — `TestB13MergeMissingMuxer` class:
  - `test_merge_batch_catches_missing_ffmpeg` (line 5205): drives `_merge_batch_segments` with `FileNotFoundError(2, "No such file", "ffmpeg")`, asserts `result is None`, `mock_error.assert_called_once()`, `mock_error.call_args[0][0] == "merge_spawn_failed"`, `"ffmpeg" in mock_error.call_args[1]["hint"]`.
  - `test_final_merge_catches_missing_ffmpeg` (line 5228): drives `_perform_final_merge` with same `FileNotFoundError`, asserts `result is False` and same `merge_spawn_failed` assertions.

**Analysis:** This is exactly what P15-B8's acceptance criteria describe:
- ✓ Oracle drives both `_merge_batch_segments` and `_perform_final_merge` with binary missing
- ✓ Fails if the raw `OSError` escapes (FileNotFoundError is caught, returns None/False)
- ✓ Asserts event name `merge_spawn_failed` and hint field

The plan's §2.4 table says "NONE" for "Missing-binary merge (NEW-06)" — this is STALE. The arms and oracle were implemented by TRN-008/B13 commits (`e6e6c68`, `0c704de`).

**Recommendation:** Update plan §2.4 and §3 P15-B8 to reflect that NEW-06 is resolved. The block's commit message should record the NEW-05 correction (plan 14's skip-ceiling). Effort: **trivial** (doc update / report).

---

### P15-B9 — TST-016 + TST-006 residual (never-executed bodies)

**Status: PARTIALLY IMPLEMENTED**

**Evidence already present:**
- `_parse_retry_after` HTTP-date branch: `tests/test_downloader_throttle.py:542` — `TestParseRetryAfter::test_retry_after_header_forms` covers IMF-fixdate (`"Mon, 01 Jan 2094 00:00:00 GMT"` → positive), RFC 850 (`"Monday, 01-Jan-68 00:00:00 GMT"`), asctime (`"Tue Jan  1 00:00:00 2094"`). The HTTP-date branch IS exercised.
- `_await_and_cancel` body: `tests/test_segment_downloader.py:1435` — four tests call the function with real async tasks and verify behavior (NOTHING_TO_DO outcome, sibling settlement, re-raised CancelledError). The body IS executed.

**Evidence NOT present:**
- The plan's P15-B9 file targets include `TestGracefulDegradation` class in `test_hls_downloader.py` — **THIS CLASS DOES NOT EXIST.** The six non-merge graceful-degradation `except` arms enumerated in TST-016 are not entered by any test.
- The plan's acceptance criterion 3: "exactly SIX graceful-degradation arms are entered" — 0 of 6 are entered.

**Plan's findings table status:** §2.4 (line 52) says TST-006 is "STALE CLAIM, corrected" — the premise that aiohttp has zero references is false (`test_segment_downloader.py` imports it). Only `_await_and_cancel` and `_parse_retry_after`'s HTTP-date branch remain unexercised. But both now appear to be covered.
- §2.4 (line 62): TST-016 — "STILL_PRESENT. Eight graceful-degradation except arms never execute." This is still true for 6 of 8 (the 2 merge-timeout sinks are P10-B14's).

**Recommendation:** Add `TestGracefulDegradation` class with one test per arm (6 tests, excluding the P10-B14-owned merge-timeout sinks). Verify which specific arms remain unentered. Effort: **medium**.

---

### P15-B10 — TST-010 (declare pytest config)

**Status: NOT IMPLEMENTED**

**Evidence:**
- `pyproject.toml` has NO `[tool.pytest.ini_options]` table.
- No `pytest.ini`, `tox.ini`, `setup.cfg` with pytest config.
- `pytest-asyncio>=1.1.0` is in dependencies (line 130) — the plan notes the floor should be raised (Decision D) but `>=1.1.0` is higher than plan's baseline `>=0.23.0`.
- 174 `@pytest.mark.asyncio` markers rest on the implicit `asyncio_mode=strict` default of pytest-asyncio 1.4.0, which is installed but not declared in config.
- `conftest.py` (line 13-42) has an autouse `isolate_settings_source` fixture — this is test-side isolation, not pytest config declaration.

**Recommendation:** Add `[tool.pytest.ini_options]` with `asyncio_mode = "strict"` and `testpaths = ["tests"]`. Effort: **trivial**.

---

### P15-B11 — TST-011 (empty integration tier)

**Status: PARTIALLY IMPLEMENTED**

**Evidence:**
- `tests/integration/__init__.py` exists (58 bytes, one-line docstring: `"""Integration tests package for VK Video Downloader."""`).
- `EXPECTED_SDIST_ENTRIES` in `test_packaging.py:117` includes `"tests/integration/__init__.py"` — it's a packaging-asserted entry.
- `tests/integration/` contains ONLY `__init__.py` — 0 test files.
- No stale `.pyc` found (Python 3.14 + uv doesn't leave them by default).

**Plan's claim (§2.4, line 57):** "A stale `.pyc` proves a deleted sibling module." — The plan expected a stale `.pyc` at execution time. None is found (the venv is clean).

**Status nuance:** The plan says "STILL_PRESENT" and marks it as "IN (decide)". The `tests/integration/` directory exists with `__init__.py` in the sdist frozenset, but has no tests. This is a packaging-asserted promise: the sdist includes a package that ships empty.

**Recommendation:** Either (a) add at least one integration test to the package, or (b) remove `tests/integration/__init__.py` from `EXPECTED_SDIST_ENTRIES` and the directory. Decision required. Effort: **small** (route a) or **trivial** (route b).

---

### P15-B12 — TST-015 (TST- prefix cleanup in test tree)

**Status: NOT IMPLEMENTED**

**Evidence — 3 `TST-` prefixed identifiers still in tests/:**

1. `tests/test_cli.py:502` — `# TST-002: Assert error reasons appear in Failed URLs section`
2. `tests/test_hls_downloader.py:369` — `"""Direct unit tests for _create_temp_cookie_file (TST-004)."""`
3. `tests/test_hls_downloader.py:3436` — `# TST-006: Use named function instead of fragile`

**Plan's acceptance criteria (lines 991-997):**
1. Exactly three identifiers renamed; zero `VAL-` identifiers created or removed — **3 TST- refs remain**.
2. Every string literal or docstring updated — **NOT DONE**.
3. `pytest -q -rs` collects 752, skip count 3 — current: 1097 collected, 3 skipped (floor exceeded, but TST- refs still present).
4. `grep tests/ VAL-105` returns 2 sites untouched — verified: `test_cli.py:3267` and `test_cli.py:3296` carry `VAL-105` in docstrings (these are plan 14's, not to be touched).

**Recommendation:** Rename the 3 `TST-` prefixed identifiers in test tree comments/docstrings to a non-collision form (e.g., `CK-` for cookie, `TR-` for traversal, `RA-` for retry-after). This is a DOC-UPDATE class finding. Effort: **trivial**.

---

### P15-B13 — VAL-124 (census exemptions for audit corpus)

**Status: ALREADY IMPLEMENTED**

**Evidence:**
- `.kilo/commands/audit/audit-orphaned.md` protect-list (lines 39-51) already includes:
  - `.ai/audit/**` — "the audit pipeline's own output (findings, reports, validation stores)" (line 43)
  - `.kilo/commands/audit/**` — "the audit command definitions themselves" (line 44)
  - `*kilo/worktrees/**` — "all worktree directories" (line 46)
  - `.ai/audit/orphaned-files/` — "the orphan audit's own output directory" (line 51)
- Commit `e9bafb2` ("audit(B15): add path-based exclusion list to orphaned-files audit") added these entries.
- The commit's "B15" attribution may be from a different plan's block numbering, but the exemptions ARE present and in the command's own vocabulary (glob patterns).

**The three required exemptions map to existing entries:**
| Plan requirement | Existing protect-list entry |
|---|---|
| Audit corpus | `.ai/audit/**` (line 43) ✓ |
| Phase catalogue | `.kilo/commands/audit/**` (line 44) + `.kilo/agents/**` (line 45) ✓ |
| Worktrees | `*kilo/worktrees/**` (line 46) ✓ |

**Recommendation:** Update plan to record this block as already resolved by commit `e9bafb2`. No action needed. Effort: **trivial** (doc update).

---

### P15-B14 — Oracle Inventory

**Status: NOT IMPLEMENTED**

**Evidence:**
- `.ai/context/test-oracle-inventory.md` does **NOT exist**.
- The plan (§3 P15-B14, line 1046) says to create this file under `.ai/context/` (not shipped, no frozenset edit needed).
- The inventory should contain:
  - §2.4 table (REAL / INDIRECT / NONE classification per subject area)
  - Status column (what each block changed)
  - Ceded section (subjects this plan did not act on, with owner names)
  - Corrected §2.4 figures (the measured support figures are stale)

**Recommendation:** This is the final block — it depends on all 13 preceding blocks completing. Since B1-B13 are either unimplemented or already done by prior work, the inventory must reflect the actual post-execution state, not the baseline state. Effort: **medium** (must be done last, after all blocks settle).

---

## End-of-Plan Gate Status (§7.2)

| Gate Check | Required | Actual | Status |
|-----------|----------|--------|--------|
| `pytest -q -rs` | 0 failed, skip=3 | 1097 passed, 3 skipped, 0 failed | **PASS** |
| `ruff check src tests` | All pass | All checks passed! | **PASS** |
| `ruff format --check src tests` | Clean | 5 files would reformat | **FAIL** |
| `mypy src` | 0 errors | 0 issues, 32 files | **PASS** |
| `git status --porcelain -- src tests docs pyproject.toml .github` | Clean | Clean | **PASS** |
| `git log --oneline -15` count | 14 commits (one per block) | Shows mixed-plan commits | **FAIL** |

**Gate status: NOT MET** — the format check fails on 5 files, and the git log does not show 14 dedicated commits from plan 15.

---

## Key Discrepancies Between §2.4 and Current Tree

| Figure | §2.4 Claim | Actual | Delta |
|--------|-----------|--------|-------|
| `patch("vkdownloader.cli.Settings")` | 24 | 35 | +11 |
| `create_subprocess_exec` patch calls | 37 | ~56 | +19 |
| `logger.exception` code calls in src/ | 3 | 4 | +1 (clean_cookies command added) |
| `aiohttp` in tests/ | 4 | 4 code + 4 comments | +4 comments |
| `chmod` real calls in tests/ | 1 (`log_file, 0o600`) | 4 | +3 |
| `requires-python` | `>=3.12` | `>=3.14` | Changed by Decision D |
| `pytest-asyncio` floor | `>=0.23.0` | `>=1.1.0` | Changed (commit `5143dfc` or later) |
| mypy source file count | 31 | 32 | +1 module |
| Test suite collected | 755 | ~1100 | +48% |
| Format RED files | 1 (`test_hls_downloader.py`) | 5 files | +4 files |
| Format RED description | 2 `with patch(logger)` blocks | 5 files, mechanical wrapping | Stale |
| Skip floor | 3 | 3 | No change ✓ |

---

## Classification of Findings

| ID | Subject | Type | Severity | Status | Owner |
|----|---------|------|----------|--------|-------|
| P15-B1 | TST-002 host-only cookie | SPEC-DEVIATION | CRITICAL | Already implemented (divergence) | P11-B1 (product) |
| P15-B2 | VAL-120f positive log oracle | SPEC-DEVIATION | CRITICAL | Partially implemented | — (needs completion) |
| P15-B2 | NEW-07 exit code 3 partition | SPEC-DEVIATION | HIGH | Implemented | Plan 13 (product) |
| P15-B3 | VAL-120s strike non-reproduction | SPEC-DEVIATION | CRITICAL | Not implemented | — |
| P15-B4 | TST-004 traversal rename | SPEC-DEVIATION | LOW | Not implemented | — |
| P15-B5 | TST-008 VideoNotFoundError arm | SPEC-DEVIATION | HIGH | Partially implemented | — (needs download-arm oracle) |
| P15-B6 | NEW-01+02 removed --method surface | SPEC-DEVIATION | MEDIUM | Implemented (divergence) | — |
| P15-B7 | NEW-03 bare MagicMock | SPEC-DEVIATION | HIGH | Not implemented | — |
| P15-B7 | NEW-08 echo=False rewrite | SPEC-DEVIATION | MEDIUM | Already implemented | P13-B7 |
| P15-B7 | Format precondition | SPEC-DEVIATION | MEDIUM | Stale (5 files, not 2) | — |
| P15-B8 | NEW-06 merge missing-binary oracle | SPEC-DEVIATION | HIGH | Already fully implemented | TRN-008/B13 |
| P15-B9 | TST-016 six degradation arms | SPEC-DEVIATION | LOW | Not implemented | — |
| P15-B9 | TST-006 _await_and_cancel / _parse_retry_after | SPEC-DEVIATION | MEDIUM | Already implemented | — |
| P15-B10 | TST-010 pytest config | SPEC-DEVIATION | MEDIUM | Not implemented | — |
| P15-B11 | TST-011 empty integration tier | SPEC-DEVIATION | MEDIUM | Partially implemented (decision needed) | — |
| P15-B12 | TST-015 TST- prefix cleanup | DOC-UPDATE | LOW | Not implemented | — |
| P15-B13 | VAL-124 census exemptions | SPEC-DEVIATION | MEDIUM | Already implemented | commit `e9bafb2` |
| P15-B14 | Oracle inventory | DOC-UPDATE | MEDIUM | Not implemented | — |
