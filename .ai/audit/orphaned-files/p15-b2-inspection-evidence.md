# P15-B2 Inspection — Positive log-record oracle + NEW-07 exit-code partition

**HEAD:** `151ea9f` · **Baseline:** `58bb7ce` · **Plan:** `.ai/plans/15-test-coverage-audit-fixes.md` §3 P15-B2
**Scope:** read-only audit. No file under `src/`, `tests/`, `docs/`, or `.ai/plans/` was modified.
**Commits since `58bb7ce` touching `tests/test_cli.py` / `src/vkdownloader/cli.py`:**
`56258e2 fix(cli): give configuration failures their own exit code` (NEW-07/Decision B impl),
`5fe961f fix(cli): name ffmpeg removal in --method help text`,
`48e4472 fix(cookies): add clean-cookies command`,
`e4889fe fix(b3): reformat 7 files for py314`,
`63b020e docs(b9): collapse cli-reference-clean.md`,
`3655cef feat(cli): log VKDownloadError arms with structured context`,
`17b0b8b feat(observability): add correlation_id + video_id`,
`0cfe47f fix(batch): align exit contract`, `1d09009 fix(batch): deduplicate`,
`b770e83 fix(config): restore .python-version`, `24dcddc`, `dbace19`, `a2e6723`,
`ea80799`, `0c704de`, `e6e6c68`, `f6e8ebe`, `5143dfc`, `e9bafb2`, `9a218ae`, `12af840`, `151ea9f`.

The commit `56258e2` landed Decision B in production (`cli.py` ValidationError→3 / `_PreambleFailure`→3) and the `cli-reference.md` tables.

---

## (a) Is the existing negative log assertion load-bearing?

**Location:** `tests/test_cli.py:3416-3417`, inside `TestPreSinkDiagnostic::test_download_dir_debug_record_is_not_emitted`
(defined `tests/test_cli.py` lines 3338-3417).

```python
3416:        log_contents = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
3417:        assert "download_dir_empty_string_using_default" not in log_contents
```

**Verdict: NOT load-bearing for any other finding.**
- It is a standalone test. The `log_path.read_text` call is local to this one method — no other test imports or re-uses it.
- It asserts only **absence** of the debug event `download_dir_empty_string_using_default` (itself triggered by `VKDOWNLOADER_DOWNLOAD_DIR=""`, set at line 3402). It is not referenced by `P15-B3`'s strike nor by `P11-B3`/`P14-B4`.
- Converting the `read_text` into a parse step does **not** change the existing negative assertion's intent. Per plan §3 P15-B2 acceptance criterion 1, the negative assertion must be **retained**; the parse is an additive extension of the same read. No behaviour change to another test.
- **Caveat (risk I-4):** the parse must assert that *every* non-empty line parses (criterion 3). If a future edit swallows a `json.JSONDecodeError` into an empty list, `not in` over an empty collection is vacuously true — worse than no oracle. The parse helper must surface unparseable lines, not silence them.

---

## (b) Configuration failures that must map to exit code 3 — current status

Decision B: `3` = configuration error; `1` = download failure (and only that); `2` = usage error.

### All config-failure arms currently return 3 (implementation is DONE by `56258e2`)

**`download` command — `src/vkdownloader/cli.py` (try block lines 431-501):**
| Arm | Trigger | Exit | cli.py |
|---|---|---|---|
| `ValidationError` | out-of-range `--max-retries` (model `Ge(1)/Le(10)`), invalid env var type (`VKDOWNLOADER_MAX_RETRIES=notanint`), malformed `.env`/rejected setting | **3** | 449-451 |
| `_PreambleFailure` | `OSError` in env scan (`warn_unknown_env_vars`), settings construction (`_build_settings`), or logging setup (`setup_logging` — e.g. log dir not creatable, or `VKDOWNLOADER_LOG_FILE` inside a regular file) | **3** | 483-485 |

**`batch` command — `src/vkdownloader/cli.py` (try block lines 555-638):**
| Arm | Exit | cli.py |
|---|---|---|
| `ValidationError` | **3** | 609-611 |
| `_PreambleFailure` | **3** | 612-614 |

**`clean-cookies` command — `src/vkdownloader/cli.py` (lines 666-687):**
| Arm | Exit | cli.py |
|---|---|---|
| `_PreambleFailure` | **3** | 673-675 |

`_PreambleFailure` is raised in `_run_command_preamble` at:
- cli.py:228-230 — `OSError` from env scan / settings construction (`logging_related=False`)
- cli.py:238-241 — `OSError` from `setup_logging` (`logging_related=True`)

It is rendered by `_render_preamble_failure` (cli.py:71-103), which emits the stderr message and — *only if `_logging_configured`* — `logger.error("preamble_failed", error_type=...)` (cli.py:100-103).

### Concrete test evidence (all currently green, all return 3)
- `test_out_of_range_max_retries_download` — `0/-1/11` → 3 (`tests/test_cli.py:2730-2753`)
- `test_out_of_range_max_retries_batch` — `0/-1/11` → 3 (`tests/test_cli.py:2755-2779`)
- `test_download_invalid_env_var_shows_concise_error` — `VKDOWNLOADER_MAX_RETRIES=notanint` → 3 (`tests/test_cli.py:2186-2197`)
- `TestPreambleFailureRendering` — logging-setup `OSError` (`VKDOWNLOADER_LOG_FILE` inside a regular file, `tests/test_cli.py:3553-3555`) → 3 on **both** commands, identical stderr (`tests/test_cli.py:3539-3629`)
- `test_exit_code_3_distinct_from_1` — `--max-retries 0` → 3 (`tests/test_cli.py:2605`)

### Non-config arms (for the partition table, D-8)
**`download` arms returning 1 (download failure, nothing else):** perform_download returns None (cli.py:445-447), `InvalidVideoUrlError` (cli.py:452-457), `QualityNotAvailableError` (cli.py:461-479), `VideoNotFoundError` (cli.py:480-482), `VKDownloadError` (cli.py:488-496), generic `Exception` catch-all (cli.py:497-501).
**`batch` arms returning 1:** unreadable URL file `OSError` (cli.py:570-574), "No URLs found" (cli.py:593-595), `VKDownloadError` (cli.py:620-629), generic `Exception` catch-all (cli.py:630-638).
**Arms returning 130:** `KeyboardInterrupt`/`CancelledError` on both commands (cli.py:458-460, 615-617).
**Arms returning 2:** Typer parser rejections — non-numeric `--max-retries` (`test_non_numeric_max_retries_download`, `tests/test_cli.py:2781-2799`), invalid `--cookie-source file` (cli.py callback), invalid `--method`/`--quality` tokens.

**So: every config failure currently returns 3; none returns another code.** The NEW-07 contract gap is the *partition oracle* (D-8 table), not the production implementation.

---

## (c) Success-path named events + single-line-JSON guarantee (Researcher)

### Named events the success/preamble path emits (structlog)
**Guaranteed on every successful preamble** — `_run_command_preamble` calls `_log_env_file_path()` after `setup_logging` succeeds (cli.py:234-235):
- `env_file_resolved` (path=...) — cli.py:123 — when `.env` exists in CWD
- `env_file_not_found_using_environment_or_defaults` — cli.py:125 — when no `.env` in CWD

Exactly one of these fires per invocation (the found/not-found branches are mutually exclusive).

**Service-layer success events** (only reached on an exit-0 run with the real downloader, i.e. Settings NOT mocked by the test):
- `starting_download` — `services/downloader.py:178-184` (method, url, quality, output)
- `available_streams` / `available_qualities` — `services/downloader.py:363-364` (only when `log_available_qualities=True`, set by the `download` command at cli.py:417)
- `batch_download_started` — `services/batch_downloader.py:384-387`
- `filename_collision_skipped` — `services/batch_downloader.py:475`
- `duplicate_url_skipped` — `services/batch_downloader.py:501`
- `download_progress` / `download_finished` — `services/progress_display.py:471-482` (CI/non-TTY fallback path; `download_finished` carries `video_id`, `status`, `downloaded`, `total`)

### Critical nuance: the exit-0 success tests do NOT write the JSON log file
The exit-0 tests in `tests/test_cli.py` **mock `vkdownloader.cli.Settings`** (e.g. `tests/test_cli.py:260`, `:2445`, `:2643`) with `MagicMock(log_file=None)`. Because `_build_settings` returns that mock and `setup_logging(settings)` then sees `log_file=None`, the renderer falls back to `ConsoleRenderer` to stderr (`config.py:676-677`) — **no JSON file is written** on the exit-0 path.

The **only** test that writes a real single-line-JSON log file through the CLI is `TestPreSinkDiagnostic::test_download_dir_debug_record_is_not_emitted` (`tests/test_cli.py:3397-3417`), which sets `VKDOWNLOADER_LOG_FILE` and runs the **real** preamble (no Settings mock). That run exits 1 (empty URLs file → "No URLs found", cli.py:593-595), but its **preamble succeeds** and emits exactly one `env_file_*` event into the JSON log file. (The autouse `isolate_settings_source` fixture chdir's to `tmp_path` with no `.env`, so the emitted event is `env_file_not_found_using_environment_or_defaults`.)

**=> the provable named event for P15-B2's positive oracle is `env_file_not_found_using_environment_or_defaults`, written as single-line JSON into the `VKDOWNLOADER_LOG_FILE` target.**

### Are they all single-line JSON? YES (on the preamble-success path)
`setup_logging` (`src/vkdownloader/config.py:610-682`):
- When `settings.log_file` is set, selects `structlog.processors.JSONRenderer()` (config.py:675-677) → one JSON object per record.
- The `FileHandler` is wrapped in `_ExcInfoClearingFormatter(fmt="%(message)s")` (config.py:655, defined config.py:588-607), which clears `record.exc_info`/`record.exc_text` **before** the base `Formatter.format` runs — so the stdlib never appends a second traceback line outside the JSON envelope.
- On the preamble-success path there is no exception, so `exc_info` is `None` regardless. One JSON object per line, every platform.
- `tests/test_config.py::TestExcInfoClearing::test_log_file_every_line_is_valid_json` (test_config.py:1116-1141) already proves this for exception-bearing records: `assert len(lines) == 1` + `json.loads(lines[0])`.

---

## (d) Is there already a shared log-parse helper in `conftest.py` or elsewhere?

**conftest.py: NO.** `tests/conftest.py` (89 lines) contains only fixtures — `isolate_settings_source` (autouse env/cwd pin), `test_settings`, `sample_video_url`, `mock_m3u8_content`, `mock_m3u8_single_stream`, `mock_invalid_url`. No parse helper.

**Elsewhere: YES, but private and CliRunner-incompatible.**
`tests/test_url_sanitizer.py:117-122` — `_read_real_chain_records`:
```python
def _read_real_chain_records(log_file: Path) -> list[dict[str, object]]:
    """Read every JSON record the real chain just emitted to ``log_file``."""
    for handler in logging.getLogger().handlers:
        handler.flush()
    text = log_file.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]
```
- It is gated on the `_real_chain` context manager (test_url_sanitizer.py:84-114), which drives `config.setup_logging` **directly** — it is NOT wired to the CliRunner path that `test_cli.py` uses. It reads files that `_real_chain` wrote, not files the CLI wrote via `VKDOWNLOADER_LOG_FILE`.
- Under §2.3 the suite is coupled by **import, not interface**, and `create=True` appears 0 times in `tests/`. A private function in `test_url_sanitizer.py` is not importable without risking the same rename-breaks-collection hazard. So it is a real parser, but **not a shared conftest utility** — P15-B2 should treat its *parse line* (`[json.loads(line) for line in text.splitlines() if line.strip()]`) as the canonical shape to reuse, not a helper to import across modules.

---

## (e) Plan 13 concurrent overlap + re-anchor target

**YES — overlap is real and already landed.**
- Commit `56258e2` "fix(cli): give configuration failures their own exit code" implemented Decision B for plan 13: production in `cli.py` (ValidationError→3 at cli.py:449-451/609-611; `_PreambleFailure`→3 at cli.py:483-485/612-614/673-675) and the doc tables at `docs/99-reference/cli-reference.md:89` (download) and `:183` (batch). The prior auditor report confirms the exit-code-3 contract is DONE.
- Plan 13's **observability** strand landed the product-side logging changes that produced the existing parse helper: `24dcddc` "echo=False non-progress line emits exactly one record" and `e6e6c68` "TRN-008: use check_ffmpeg_available return value". These are the upstream of `_read_real_chain_records`/`_real_chain` in `test_url_sanitizer.py`.

**Re-anchor target for P15-B2 (D-7):** `_read_real_chain_records` (test_url_sanitizer.py:117) is the **only** existing log parser in the tree. D-7's criterion is "if plan 13 has already landed a log-oracle helper, re-anchor onto what exists — never create a second." That re-anchor is a **parse-shape** reuse (the one-liner in (d)), not a cross-module import, because:
1. The helper is private to `test_url_sanitizer.py` and bound to `_real_chain`, which does not model the CliRunner `VKDOWNLOADER_LOG_FILE` path.
2. Importing it across modules would violate the suite's by-name import coupling (§2.3: 0 `create=True`).
3. P15-B2's reader reads a *different* file (the CLI's run output) than `_real_chain` reads.

**What must NOT be duplicated:** P15-B2's acceptance criterion 5 requires "exactly one log parser and one partition test for the tree." The partition test currently exists only as a **pairwise** assertion (`test_exit_code_3_distinct_from_1`, test_cli.py:2605 covers 1-vs-3) plus a **membership** check (`TestExitCodeContract::test_every_observable_exit_code_is_documented`, test_cli.py:2389 asserts `{0,1,2,3,130}`). Neither is the **parameterised table** D-8 route (a) demands — a single table asserting each category maps to exactly one code with no status shared across categories. That table is the remaining P15-B2 work.

---

## Open items this inspection leaves to the Implementor (P15-B2)

1. **Positive oracle on `env_file_not_found_using_environment_or_defaults`** — extend the existing `read_text` at `tests/test_cli.py:3416` into a parse (reuse the `_read_real_chain_records` parse line), assert the event's `event` field equals `env_file_not_found_using_environment_or_defaults` and that every non-empty line parses as JSON. Do **not** assert a record `count` (brittle); do **not** assert failure-path shapes (`DEF-1`, plan 13 / `OUT-002`).
2. **Partition table** (D-8 route (a)) — one parameterised test mapping `{configuration failure → 3, download failure → 1, usage error → 2}`, asserting exclusivity (no status shared across two categories) and that the enumeration is non-empty (risk I-15).
3. **`cli-reference.md` coupling** — per criterion 6, record (do not edit) the dependency on plan 13's reference edit.
