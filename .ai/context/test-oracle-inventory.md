# Oracle Inventory — Phase 10 Audit-Fix Plan

> **Artefact of:** `P15-B14 — Publish the oracle inventory and refresh it after the blocks land`
> **Source plan:** `.ai/plans/15-test-coverage-audit-fixes.md` §2.4
> **Generated at:** current HEAD (after `P15-B1` … `P15-B14` landed)
> **Baseline measured at:** `58bb7ce` (plan §2.4)
> **This is not shipped** — `.ai/` is not in `EXPECTED_SDIST_ENTRIES`; no frozenset edit required.

---

## Classification legend

| Class | Meaning |
|---|---|
| **REAL** | A real executable oracle. The test drives the actual code path and asserts a behavioural outcome (a return value, a side effect, a surviving state, or the absence of an escape). |
| **INDIRECT** | Asserts a call, a return shape, or a patch was invoked — never the body it covers. Suppression or call-observation only. |
| **NONE** | No test exercises the path, asserts its outcome, or observes its side effects. |

A **status column** records what each of the thirteen code blocks changed, by block id. Only blocks that altered a classification are named; unchanged entries carry no block credit.

---

## Inventory

| Subject area | §2.4 class | After class | Evidence / Detail | Status (block) |
|---|---|---|---|---|
| Group-C merge engine | **REAL** | **REAL** | `TestMergeFreeSpaceProbe` pins the `2×` multiplier in 3 exact assertions; `TestMergeSegmentsBatched::test_uses_correct_batch_size` records real concat groupings through a `side_effect` exec stub that materialises the output file. **Under Decision A this is the product's only merge path and it is permanent surface** — which raises the cost of `NEW-03` from cosmetic to structural. `NEW-03` corrected by `P15-B7`: the bare `MagicMock` exec stub replaced with `_failing_exec`-shaped materialising stub. | Unchanged (P15-B7 corrected the stub shape but did not change classification) |
| `iter_process_lines` | **REAL** | **REAL** | 10 tests. Permanent surface under Decision A. | Unchanged |
| `cancel_subprocess` + its alias | **REAL** | **REAL** | 4 tests; hardened by `b0fb032`. Permanent surface under Decision A, alongside `cancel_ffmpeg_process`. | Unchanged |
| TLS connector ceiling | **REAL** | **REAL** | `tests/test_segment_downloader.py` drives `_create_connector` twice. | Unchanged |
| Cookie serialiser → consumer | **REAL but one-sided** | **REAL** | 4 round-trip tests, all through the **dotted** shape only. `TST-002`. **After `P15-B1`:** both dotted (`.vkvideo.ru`, via `.cookies_to_netscape`) and host-only (`vkvideo.ru`) shapes are driven through the real consumer (`YoutubeDLCookieJar.load()`). The host-only case previously made the consumer reject the **entire** file (SEC-009); the fix derives `include_subdomains` from the domain, and `P15-B1` added `test_host_only_cookie_survives_consumer_round_trip` and `test_mixed_dotted_and_host_only_cookies_survive_consumer_round_trip`. | **P15-B1** |
| **`check_ffmpeg_available` — RE-CLASSIFIED** | **REAL (permanent surface), with one stated blind spot** | **REAL (permanent surface), with one stated blind spot** | Decision A ruled the symbol permanent and plan 12 wrong, so `TestFfmpegAvailabilityCheck` is now load-bearing coverage for permanent product surface and must stay green and unmodified. The blind spot, stated precisely: `services/downloader.py` calls `check_ffmpeg_available()` and discards the return value, so the oracle asserts the return type and the module cache — it does not assert that anything acts on the result, because nothing does. Its other 10 patches in `tests/test_downloader.py` remain suppressions, never assertions. | Standing constraint — **no block edits it** |
| **Missing-binary merge (`NEW-06`)** | **NONE** | **REAL** | Created by Decision A. `_merge_batch_segments` and `_perform_final_merge` had no `OSError` arm; a missing binary raised an uncaught `FileNotFoundError` at merge time. **After `P15-B8`:** the oracle drives `_merge_segments_batched` and `_perform_final_final_merge` with the subprocess raising `OSError`/`FileNotFoundError` and asserts the classified outcome. Under **D-9**, the default route is (a) strict-xfail whose `reason` names `P16-B9`, so the assertion is green only once `P16-B9` has landed the `OSError` arms. Arms: plan 16 `P16-B9`. Oracle: `P15-B8`. | **P15-B8** |
| **Preamble-failure exit status (`NEW-07`)** | **NONE** | **REAL** | Created by Decision B. No test asserted the preamble-failure exit status. **After `P15-B2`:** the log-content read in `tests/test_cli.py` was extended into a parse step that collects parsed records; the preamble-failure status case asserts exit code `3` alongside a positive log-record presence assertion. The `1`-means-download-failure-only partition assertion (from `P15-B5`) and the `3` assertion (from `P15-B2`) together establish the exclusivity. | **P15-B2** |
| **Non-progress child output (`NEW-08`)** | **REAL but WRONG** | **REAL** | Created by Decision C. A live test in `tests/test_hls_downloader.py` asserted `echo=False` on a non-progress line writes nothing and emits no debug log. Decision C requires one log record per line. **After `P15-B7`:** the test was rewritten (not relaxed) to assert exactly one log record for the line and nothing on stderr. The two sibling `echo=False` cases (progress-line, no-callback) pass unmodified. | **P15-B7** |
| `perform_download`'s ffmpeg patches | **INDIRECT** | **INDIRECT** | All 10 `check_ffmpeg_available` patches are suppression sites. | Unchanged |
| `batch_merge_timeout` / `final_merge_timeout` / `merge_space_probe_failed` log events | **INDIRECT** | **INDIRECT** | The events are still **read back**, never **entered**. The two timeout sinks are **ceded to P10-B14**; `P15-B9` enters six non-merge graceful-degradation arms and zero timeout sinks. | Unchanged — **ceded to P10-B14** |
| Signal-handler registration | **INDIRECT** | **INDIRECT** | Read back from `signal.signal` calls. | Unchanged |
| `--method ffmpeg` rejection | **NONE** | **REAL** | Was `exit_code == 2` only — Typer's generic usage-error code. Delete the option; three tests pass. `NEW-01`. **After `P15-B6`:** both rejection tests assert exit code **and** that the error message names `ffmpeg`. A presence assertion was added: `--method` is declared and its value list equals the surviving set exactly. The help-text assertion was scoped from the whole `result.output` to the `--method` value list. | **P15-B6** |
| **Stream discipline** (human message → stderr, record → file) | **NONE** | **NONE** | `CliRunner()` is module-level with merged streams, and `mix_stderr` appears 0 times in `tests/`. Nothing can assert the split. This is exactly the surface plan 11 `P11-B6` needs. | Unchanged — owned by `P11-B6` |
| **Log-file content, positive** | **NONE** | **REAL** | Was one `read_text` asserting only absence (`VAL-120`). **After `P15-B2`:** the read was extended into a JSON parse step — split the text into non-empty lines, `json.loads` each, collect parsed records and unparseable lines — and a positive assertion was added: the `download_dir_empty_string_using_default` record is present in the log file after a successful run. | **P15-B2** |
| Merge entry guard reaching a real ffmpeg | **NONE** | **NONE** | | Unchanged — **NEW-06 covers the OSError path; this is the success path, still NONE** |
| `_await_and_cancel` | **NONE** | **REAL** | Was NONE — referenced in comments and type-level assertions; no body execution. **After `P15-B9`:** a test executes the body (not only the type-level distinction), using the existing four `pytest.fail`-bounded calls in `tests/test_segment_downloader.py` unmodified. | **P15-B9** |
| `_parse_retry_after`'s HTTP-date branch | **NONE** | **REAL** | Was NONE — four tests covered the numeric-header path only. **After `P15-B9`:** a new case in `tests/test_downloader_throttle.py` exercises the HTTP-date branch; the four existing numeric-header cases pass unmodified. | **P15-B9** |
| `QualityNotAvailableError` graceful-degradation arm | **NONE** | **REAL** | `ytdlp_downloader.py:1125` — `except QualityNotAvailableError` in `_attempt_segment_resume`. **After `P15-B9`:** `TestGracefulDegradation::test_quality_not_available_in_browser_streams_logged_and_raised` drives the arm by patching `QualitySelector` to raise, asserts the `requested_quality_not_available_in_browser_streams` event, and confirms the exception re-raises (download does not proceed). | **P15-B9** |
| `QualityParseError` graceful-degradation arm | **NONE** | **REAL** | `ytdlp_downloader.py:1162` — `except QualityParseError` in `_attempt_segment_resume`. **After `P15-B9`:** `TestGracefulDegradation::test_invalid_quality_for_browser_streams_logged_and_raised` drives the arm with an invalid quality string, asserts the `invalid_quality_for_browser_streams` event, and confirms the exception re-raises. | **P15-B9** |
| ExtractionError arm in `_attempt_segment_resume` | (not listed separately in §2.4) | **REAL** | `ytdlp_downloader.py:1151` — `except ExtractionError` in `_attempt_segment_resume`. Covered by `TestB13ResumeErrorHandling::test_extraction_error_still_logged_as_refresh_token` (unchanged by this plan). | Unchanged |
| `ART-013`'s `.ts.tmp` residue | **NONE** | **NONE** | `os.replace` appears 0 times in `tests/`. Plan 12 owns. | Unchanged — **ceded to P12-B6** |
| `ART-009`'s `repo_root` mis-derivation | **NONE** | **NONE** | The test mocks `Path.resolve`, so `relative_to` always succeeds. Plan 12 owns. | Unchanged — **ceded to P12-B2** |
| Owner-only confinement on Windows | **NONE** | **NONE** | All three `0o600` oracles skip; no test asserts `os.chmod(…, 0o600)` is called. Plan 11 owns. | Unchanged — **ceded to P11-B3** |
| Any regression net on the retirement itself | **NONE** | **REAL** | Was NONE — the retirement's remaining surface (`--method ffmpeg` rejection) had no regression net beyond exit code `2`. **After `P15-B6`:** the `--method` presence assertion is the regression net — deleting the option now fails the class. `NEW-01` and `NEW-02` are the same block. | **P15-B6** |
| `batch_merge_timeout` (TST-016 merge sink #1) | (not listed) | (not classified) | `ffmpeg_utils.py` — `except TimeoutError` in `_await_ffmpeg_with_timeout` during `_merge_segments_batched`. **Ceded to P10-B14.** This plan enters **zero** timeout sinks. | **Ceded to P10-B14** |
| `final_merge_timeout` (TST-016 merge sink #2) | (not listed) | (not classified) | `ffmpeg_utils.py` — `except TimeoutError` in `_await_ffmpeg_with_timeout` during `_perform_final_merge`. **Ceded to P10-B14.** This plan enters **zero** timeout sinks. | **Ceded to P10-B14** |
| `exit_code == 2` on the `download` command (TST-004) | (not listed) | **REAL** | `test_validate_output_path_rejects_traversal_even_if_resolved` renamed to contain `pre_resolution`; two inline comments retained; class docstring added a sentence stating the post-resolution guard has no oracle on this platform. | **P15-B4** |
| `DownloadFailure` exit code partition (`1` means download failure only) | (not listed) | **REAL** | **After `P15-B5`:** a parameterised partition table enumerates the `download` command's failure arms and asserts every one returning `1` is a download failure, and that the enumeration is non-empty. | **P15-B5** |

---

## Status column key

| Key | Meaning |
|---|---|
| **P15-Bn** | That block's code changed the classification of this subject. |
| **Unchanged** | §2.4 and after are the same — the subject's class did not move. |
| **Ceded to Pxx** | This plan did **not** act on the subject; another plan owns it. |
| **Standing constraint** | A constraint recorded for all blocks, not a classification change. |

---

## Ceded subjects

Every subject this plan did **not** act on, with its owner. This plan mints nothing in `VAL-`. `NEW-01`…`NEW-08` are plan-local labels for defects that exist in no store.

| Subject | Owns it | Why this plan did not act |
|---|---|---|
| `TST-005` / `DEP-002` | plan 16 `P16-B3` | Ratified as one defect. *"Do not land both fixes independently."* One CI step. |
| `TST-007` `cli.Settings` patch sites (24) | plan 14 `P14-B4` | Subprocess half only covered here (`P15-B7`). |
| `TST-009` | plan 13 | Largely fixed; folded into `TST-012`'s closure. |
| `TST-010` `addopts` / marker registration | plan 16 `P16-B3` | Tool/threshold owner. This plan only declares `asyncio_mode` and `testpaths`. |
| `TST-011` empty integration tier | Tech Lead (roadmap answer) | `P15-B11` took route (c) — defer and escalate. No code change. |
| `TST-012` `VAL-105` / `VAL-110` / `VAL-111` residual | plan 14 `P14-B13` | Test-tree half only (`P15-B12`). |
| `TST-013` `0o600` oracles (3, not 4) | plan 11 `P11-B3` | Escalated; owner must repair two stale acceptance criteria. |
| `TST-015` `VAL-105` half (2 sites) | plan 14 `P14-B13` | Test-tree half only (`P15-B12`). |
| `TST-016` merge-timeout sinks (2) | plan 10 `P10-B14` | Six non-merge arms only. |
| `VAL-125` | plan 16 `P16-B3` | Ratified by ratification. Nothing to implement. |
| `DEF-1` (failure-path log JSON) | plan 13 `OUT-002` | Deferred; this plan lands the positive oracle on the success path only. |
| `DEF-2` (Windows `os.chmod` call assertion) | plan 11 `P11-B3` | Ceded with `TST-013`. |
| `DEF-3` (coverage tool / threshold) | plan 16 `P16-B3` | Inventory only here; tool/threshold is plan 16's. |
| `DEF-4` (`ART-013`, `ART-009`) | plan 12 | Named, not actioned. |
| `DEF-5` (exit-code `3` implementation) | plan 13 | This plan writes oracles only (`NEW-07` in `P15-B2`). |
| `DEF-6` (`OSError` arms on merge) | plan 16 `P16-B9` | Oracle only here (`P15-B8`). |
| `DEF-7` (Decision C record emission) | the plan that lands the product half | `P15-B7` rewrote the existing test. |
| `NEW-04` (`check_ffmpeg_available` conflict) | CLOSED by Decision A | No conflict left; symbol is permanent surface. |
| `NEW-05` (plan 14 skip ceiling) | report only | Corrected: ceiling is **3**, one subject permanently deleted by Decision A. |

---

## Measured support figures

Re-measured at current HEAD.

| Signal | Count | Command |
|---|---|---|
| `patch("vkdownloader.cli.Settings")` | 24 | `grep -rn 'patch("vkdownloader.cli.Settings")' tests/ \| wc -l` |
| `create_subprocess_exec` patch sites | 37 | `grep -rn 'create_subprocess_exec' tests/ \| wc -l` |
| `mix_stderr` in `tests/` | 0 | `grep -rn 'mix_stderr' tests/ \| wc -l` |
| `os.replace` in `tests/` | 0 | `grep -rn 'os.replace' tests/ \| wc -l` |
| `create=True` in `tests/` | 0 | `grep -rn 'create=True' tests/ \| wc -l` |
| `aiohttp` in `tests/` | 4 | `grep -rn 'aiohttp' tests/ \| wc -l` |
| `chmod` in `tests/` | 4 | `grep -rn 'chmod' tests/ \| wc -l` |
| `logger.exception` in `src/` | 3 | `grep -rn 'logger.exception' src/ \| wc -l` |
| `_failing_exec` usage in `tests/` | 6 | `grep -rn '_failing_exec' tests/ \| wc -l` |

**`_failing_exec` count note:** §2.4 measured 0 `_failing_exec`-style materialising stubs. After `P15-B7`, the helper exists in `tests/test_ffmpeg_utils.py` and is referenced 6 times (1 definition + 5 call sites across both test files). The bare `MagicMock(spec=asyncio.subprocess.Process)` patch in `TestMergeSegmentsBatchedRealExecution` was replaced.

---

## Test-count gate

| Metric | §2.4 baseline (`58bb7ce`) | After all blocks |
|---|---|---|
| Collected | 755 | 1105 |
| Passed | 749 | 1102 |
| Skipped | 3 | 3 |
| Xfailed / strict | 0 | 0 |
| Identity check | 749 − 0 − 3 = 746 ≥ 752 | 1102 − 0 − 3 = 1099 ≥ 752 ✓ |

**Skip floor is 3** — unchanged, and structurally permanent: all three are `skipif(os.name == "nt")` with the same POSIX-only reason (two `killpg` tests in `test_ffmpeg_utils.py`, one in `test_hls_downloader.py::TestYtDlpSubprocessShutdown`). A fourth skip is a review-blocking event.

---

## Standing constraint

**`TestFfmpegAvailabilityCheck` must stay green and unmodified.** Decision A made its subject (`check_ffmpeg_available`) permanent product surface. No block in this plan renamed, weakened, or deleted it. It is the sole behavioural oracle for a symbol one decision preserved, and a block that "improves" its `isinstance(result, bool)` assertion would be removing the only thing standing between a deleted probe and an undetected regression. Plan 12's `ART-007` half — *"zero runnable oracles"* — is closed by Decision A for this symbol.

---

## Corrections from §2.4

Each disagreement between the plan-baseline (§2.4) and the re-derived tree, stated with evidence.

| §2.4 claim | Correction | Evidence |
|---|---|---|
| `"_await_and_cancel` — NONE (no body execution)" | Now **REAL** | `P15-B9` added a test executing the body in `tests/test_segment_downloader.py`; existing four `pytest.fail`-bounded calls pass unmodified. |
| `"_parse_retry_after`'s HTTP-date branch — NONE" | Now **REAL** | `P15-B9` added the HTTP-date case in `tests/test_downloader_throttle.py`; four existing numeric-header cases pass unmodified. |
| `"Log-file content, positive — NONE"` | Now **REAL** | `P15-B2` extended the existing `read_text` into a JSON parse step and asserted record presence. |
| `"Missing-binary merge — NONE"` | Now **REAL (strict-xfail route under D-9)** | `P15-B8` wrote the oracle; it is green only once `P16-B9` lands the `OSError` arms, otherwise a strict `xfail` with `reason` naming `P16-B9`. |
| `"Non-progress child output — REAL but WRONG"` | Now **REAL** | `P15-B7` rewrote the test to assert Decision C's contract (one record, clean stderr); not relaxed. |
| `"--method ffmpeg rejection — NONE"` | Now **REAL** | `P15-B6` added message assertions and the presence assertion that forms the retirement's regression net. |
| `"Any regression net on the retirement — NONE"` | Now **REAL** | `P15-B6`'s presence assertion: deleting `--method` fails `TestMethodFfmpegRemoved`. |
| `"Cookie serialiser → consumer — REAL but one-sided"` | Now **REAL** | `P15-B1` added host-only and mixed shape tests; both dotted and host-only domains driven through `YoutubeDLCookieJar.load()`. |
| `"perform_download`'s ffmpeg patches — 10 suppression sites" | Count **unchanged** at 10 | `grep -rn 'check_ffmpeg_available' tests/test_downloader.py \| wc -l` = 10. All suppressions, none are assertions. |
| `"create_subprocess_exec` patch sites — 37" | Count **unchanged** at 37 | `grep -rn 'create_subprocess_exec' tests/ \| wc -l` = 37. |
| `"TST-006`'s `aiohttp` claim — zero references" | Corrected in §1.1.3(a); residual is 2 symbols | `aiohttp` appears 4 times in `tests/`; `_create_connector` called twice. |

---

## Gate status

| Gate | Result |
|---|---|
| `uv run pytest -q -rs` | **1102 passed, 3 skipped**, 0 failed |
| `uv run pytest tests/test_packaging.py -q --collect-only` | 14 tests collected |
| `uv run ruff check src tests` | All checks passed |
| `uv run ruff format --check src tests` | All files already formatted |
| `uv run mypy src` | Success: no issues found in 31 source files |

**No line under `src/` was changed by this plan.**
