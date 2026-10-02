---
name: 08-cli-observability-validated-findings
description: Phase 08 (CLI and Observability) audit findings, validated
agent: audit-executor
alwaysApply: false
---

# Phase 08 Audit Findings — CLI and Observability (VALIDATED)

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/08-audit-cli-observability.md`
**Status:** complete
**Validated:** yes
**Output mode:** problems-only
**Commit measured by the source report:** `a335b2a2e0270414f9f2923d1b4a8e038a8998b5` (`a335b2a`).

---

## Validation provenance (added by the validation phase)

**Validated by:** `99-audit-validate.md` (executor `validator`), against the commit
`a335b2a2e0270414f9f2923d1b4a8e038a8998b5` — the same commit the source report
measured, and still `HEAD` with `src/`, `docs/` and `tests/` clean in the working
tree. **No commit has landed since the source report was written**, so every
finding was re-verified against exactly the tree it was filed against; no
finding is stale on that account.

**Baselines, re-measured on this commit** (the source report's figures are
reproduced exactly):

| Command | Exit | Result |
|---|---|---|
| `uv run pytest -q` | 0 | `498 passed, 4 skipped in 26.88s` |
| `uv run ruff check src tests` | 0 | `All checks passed!` |
| `uv run ruff format --check src tests` | 0 | `52 files already formatted` |
| `uv run mypy src` | 0 | `Success: no issues found in 30 source files` |

Re-measured a second time at the end of the run, by which point `cli.py` and `config.py`
had acquired the uncommitted edits described under `VAL-003`: **all four baselines are
unchanged** (`498 passed, 4 skipped in 27.41s`; ruff 0; ruff format 0; mypy 0, 30 source
files). The in-flight edit passes the gates, so no gate anywhere in this repository would
have caught it вЂ” which is the point `VAL-003` makes.

**Deviation, stated once (binding rule to `99-audit-validate.md` §11).** The report
format `.ai/audit/templates/audit-findings.md` has **no slot for a validation
decision**: its finding block runs from the `### {ID}:` heading straight into a
fixed field table, and none of the nine mandatory fields it defines carries a
decision. The `Validation Note` block defined by the validation phase is therefore
written directly beneath each heading, outside the field table. This artifact
deviates from the format in exactly that one place.

**Anchor correction applied throughout — and the tree moved under this run.** The source report's
`file:line` anchors are **correct for the commit it names**, and were re-verified against that
commit: `git show a335b2a:<path>` was extracted and every cited line re-read, with
`cli.py` 365 lines and `config.py` 382 lines at that commit. `110-116` is the four-step
bootstrap, `193` is the traceback origin, `245-248` is the `except Exception` handler,
`188-189` is the stop check, `152-157` is the `--max-retries` option, and `358-366`, `373` and
`375-377` in `config.py` are `logging.basicConfig`, `format_exc_info` and the renderer selection.
**The working tree is not that commit.** `cli.py` and `config.py` carry uncommitted edits that
were absent at the start of this run, and on the edited tree every one of the report's 27
`cli.py`/`config.py` anchors is off by `+18` and `+10` respectively. Two small corrections in the
notes below are in files the edit never touched and stand as filed: `enums.py:78` → `:79`, and
`ytdlp_downloader.py:545-551` → `:547-552`. The whole incident is filed as `VAL-003`.

**Decisions:** 17 findings in scope — 12 validated, 1 reclassified, 2 merged into
`ENT-012` (phase 01), 2 rejected. 5 `VAL-` findings filed against the audit's own
documents. Tally and retained content are in *Validation Summary* at the end.

---

## Method, harness and admissibility (R12)

**Invocation (used by every "through the binary" row below):** `uv run vkdownloader <args>`, launched with `Start-Process -NoNewWindow -Wait -RedirectStandardOutput <file> -RedirectStandardError <file>`. The two standard streams are written to **two distinct files**; the process status is read from the shell. No row in this report is evidenced from a merged capture, and every capture was written to a file and read from a file. Each provocation ran in its own freshly created empty working directory.

**"In process" rows** drive the command function or the display object directly through `uv run python`, with results written to a file and read back from it. Rows produced in process are labelled as such and are never described as observed through the binary.

**Environment:** Windows, `rich` 15.0.0, `structlog` 26.1.0, `typer` 0.26.8. The host has no usable certificate chain for `vkvideo.ru`, so every download in this phase fails during extraction with a TLS error. That failure mode is the product's own and was used as the "ordinary run that fails" for R1/R3/R5/R6/R7/R8.

**Baselines (R12a), re-measured on this commit:**

| Command | Exit | Result |
|---|---|---|
| `uv run pytest -q` | 0 | `498 passed, 4 skipped in 25.27s` |
| `uv run ruff check src tests` | 0 | `All checks passed!` |
| `uv run ruff format --check src tests` | 0 | `52 files already formatted` |
| `uv run mypy src` | 0 | `Success: no issues found in 30 source files` |

Re-measured a second time at the end of the run, by which point `cli.py` and `config.py`
had acquired the uncommitted edits described under `VAL-003`: **all four baselines are
unchanged** (`498 passed, 4 skipped in 27.41s`; ruff 0; ruff format 0; mypy 0, 30 source
files). The in-flight edit passes the gates, so no gate anywhere in this repository would
have caught it вЂ” which is the point `VAL-003` makes.

These are the state the findings below were observed in, cited as coverage. They are not filed as findings.

**Coverage declaration (R12b/R12c), searched over `tests/` with worktree directories excluded:**

| Mechanism | Files | Count | What it replaces |
|---|---|---|---|
| Command runner that replaces both standard streams | `tests/test_cli.py:12,26` | 1 | both streams, for the duration of one `runner.invoke` |
| Capture fixture (`capsys`) | `tests/test_batch_downloader.py` (6 tests), `tests/test_hls_downloader.py` (4 tests) | 10 | `sys.stdout`/`sys.stderr`, into one buffer per fixture |
| Site that replaces a stream the display module itself holds | `tests/test_progress_display.py:254`, `:418` | 2 | `vkdownloader.services.progress_display.sys.stderr` |
| Site that forces a terminal onto an injected stream | `tests/test_progress_display.py:287`, `:329` | 2 | `Console(..., force_terminal=True)` on an in-memory buffer |
| **Site that asserts a stream is a terminal** | — | **0** | — |

Consequences, as measured. The two terminal-mode sites inject `force_terminal=True` and therefore bypass the detection under audit; the capturing runner merges both streams, so no stream-discipline claim in this report is evidenced from the suite. Seven `assert "Traceback" not in result.output` guards exist (`tests/test_cli.py:151, 1172, 1186, 1201, 1214, 1715, 1739`) and every one of them is applied to a handled rejection; the unhandled-exception path that this report observes printing a traceback is not among them.

**Platform note (binding under preamble rule 1).** The declared development platform is Windows and both standard streams report themselves as non-terminals in this environment (`sys.stderr.isatty()` is `False` for every capture above). The display the production code constructs is therefore inactive, and the enabled path — the lazily built console, the stream proxy installed over the error stream, the handler repoint and restore — cannot be reached from outside the process. No finding below states a runtime consequence observed through the binary for the display arbitration, the borrowed handlers, or the child-output suppression; those subjects are filed as structural facts with explicit `UNVERIFIED` markers.

**R-N (documented skip).** The live-display enabled path is verified in process only: `RichProgressReporter` is constructed with an explicit file-backed console and its lifecycle is driven directly (`OUT-010`, `OUT-011`, `OUT-012`). No colour-forcing environment variable was used as a substitute for a terminal anywhere in this phase; where one flipped a predicate and not the other, that is recorded as a disagreement and nothing else.

**R-S (documented skip).** The teardown's exception-safety trigger is filed as ordering with the trigger marked `UNVERIFIED` (`OUT-011`). No reproduction was manufactured for it.

---

## Findings

### OUT-001: A failure inside the command preamble ends the run by a path the entry layer does not declare, on the same status as a failed download

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** CRITICAL (was HIGH — see below)
> - **Type:** RUNTIME-ERROR (retained) · **Classification:** mandatory (retained)
> - **Detail:** Re-derived and reproduced on `a335b2a`, through the binary, two streams to two
>   distinct files, fresh working directory. A `.env` that cannot be decoded gives
>   **status 1, stdout 0 bytes, stderr 10 648 bytes**, a rich traceback originating at
>   `cli.py:211` inside `_run_command_preamble`, terminating in
>   `UnicodeEncodeError: 'charmap' codec can't encode characters in position 102-123` from
>   `encodings/cp1251.py:19`. A substring search for the declared message
>   `Configuration error: one or more settings have invalid values.` over the whole capture
>   returns **False** — the declared message never appears. The source report's figures
>   (status 1, stdout 0 bytes, 10 731 bytes stderr, same exception class and origin) are
>   reproduced; the 83-byte delta is run-to-run, not a discrepancy.
> - **Why the severity is CRITICAL, not HIGH.** The phase's own taxonomy
>   (`08-audit-cli-observability.md` §9) names this shape at CRITICAL: *"A run terminates by
>   a path the product's own handlers do not declare, and the status the caller reads does
>   not distinguish that from success or from an ordinary failure."* Both clauses hold and
>   both are measured: the run ends in Typer's pretty-exception handler, which no handler
>   in the product declares, and the status `1` is the same status
>   `typer.Exit(code=1)` returns for an ordinary download failure. The source report filed
>   it HIGH; that severity is corrected here and the correction is independent of the
>   decision (binding rule 1).
> - **Anchors: the report's are right for `a335b2a`.** `_run_command_preamble`'s executable
>   body is `cli.py:110-116` — `warn_unknown_env_vars()` at `:110`, `_build_settings` at `:111`,
>   `setup_logging(settings)` at `:114`, `_log_env_file_path()` at `:115`, `return settings` at
>   `:116` — and that is what the report cites. The generic handler is `cli.py:245-248` and the
>   traceback origin is `cli.py:193`, both as filed; the declared message is `config.py:216-219`,
>   the `lines` list whose first two entries are exactly the two the report quotes. All four
>   verified against `git show a335b2a:<path>`.
>   - **On the current working tree they resolve elsewhere** — the handler at `263-266`, the
>     origin at `211`, the message at `213-216` — because `cli.py` and `config.py` carry
>     uncommitted edits that were not there when this run began. That is `VAL-003`, and it is why
>     the traceback this phase reproduced names `cli.py:211` where the report names `193`.
> - **See also:** `ENT-002` (phase 01, the mechanism: `logger.exception` with no sink);
>   `ENT-003` (phase 01, the `batch` instance, named inside this finding and not re-filed);
>   `VAL-003` (the tree the report's anchors belong to).

| Field | Value |
|-------|-------|
| **ID** | OUT-001 |
| **Severity** | CRITICAL *(re-derived by the validation phase; filed HIGH)* |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** The four-step command bootstrap at `src/vkdownloader/cli.py:110-116` runs `warn_unknown_env_vars()` → `_build_settings()` → `setup_logging()` → `_log_env_file_path()`. Only the second step has a declared message. The first and the third can raise, and when they do the command reports them through its generic `except Exception` handler (`cli.py:245-248`), which calls `logger.exception(...)` while **no sink is configured**, because `setup_logging` had not run. That handler therefore dies inside structlog, the new exception escapes the command function, and Typer's pretty-exception handler renders it and returns `1`. The caller receives a raw traceback instead of any declared message, on the same status an ordinary download failure produces.

**Evidence (through the binary; two distinct capture files; fresh working directory per provocation):**

| Provocation | Status | stdout | stderr | Terminating exception |
|---|---|---|---|---|
| `.env` present but not decodable (`VKDOWNLOADER_LOG_FILE=…\xFF\xFE\n`), `download <url>` | **1** | **0 bytes** | **10 731 bytes** | `UnicodeEncodeError: 'charmap' codec can't encode characters in position 102-123`, raised from `encodings/cp1251.py:19` via structlog's `ConsoleRenderer` writer |

The declared message for a configuration error (`config.py:216-219`, `"Configuration error: one or more settings have invalid values."`) never appears anywhere in the 10 731 bytes. The traceback names `cli.py:193 in download` → `_run_command_preamble`, confirming the failure is raised inside the pass, not by the download.

Root cause is **ENT-002** (phase 01, HIGH): `logger.exception` with no sink. It is re-measured here on `a335b2a` and still reproduces, so it is **cross-referenced, not re-filed**. What is this phase's, per `## 7` ("What the caller receives when a failure happens inside that pass — what reaches each stream, whether the declared message survives, what status the process returns"), is the consequence: the declared message does not survive, stdout receives nothing at all, and the status `1` is indistinguishable from `Download failed`.

The same undeclared path is reached in `batch` when the log destination's parent cannot be created or the destination is itself a directory — there the message is `Failed to read URL file: <urls.txt> — Failed to create log file parent directory '<blocker>'` (**ENT-003**, re-measured on `a335b2a`, exit 1, stderr only). Both are consequences of the same missing entry in the declared-failure table and are named here so the table has one owner.

**Recommendation:** Give the preamble its own failure declaration and make the report path safe before any sink exists. Concretely: wrap steps 1 and 3 of `_run_command_preamble` and raise a single `StartupError` carrying the offending source; catch it in each command *before* the generic `except Exception`, print a declared message to stderr and return a status distinct from a download failure; and make the generic handler's `logger.exception` safe when `structlog` is unconfigured (log through `logging` directly, or configure a minimal stderr sink in a `finally` on the failure path). The status to return is the product's decision — the point this phase files is that it must be distinguishable from `Download failed`.

---

### OUT-002: The log file the product declares JSON contains 130 of 141 lines no parser reads, because one exception is rendered twice

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM (retained)
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **Detail:** The mechanism is **confirmed independently, not inherited**, and the
>   stdlib re-append is demonstrated rather than asserted. Three measurements:
>   (1) *Through the binary*, a real failing `download` with `VKDOWNLOADER_LOG_FILE` set:
>   the file is **22 075 bytes, 141 physical lines, 10 `Traceback (most recent call last)`
>   markers**. Byte-for-byte agreement with the source report's figure of 22 075 bytes and
>   141 lines.
>   (2) *Isolated control on the production record*: driving one `logger.exception` inside an
>   `except` block through the real `setup_logging()` leaves `record.exc_info` **not None**
>   and **truthy** (`exc_info[0].__name__ == "RuntimeError"`) *after*
>   `structlog.processors.format_exc_info` has run, and `logging.Formatter("%(message)s")`
>   then appends the chain — the same record formatted with `record.exc_info = None` yields
>   no traceback at all. This is the exact defect: `ExceptionRenderer.__call__` does
>   `event_dict.pop("exc_info", None)`, clearing the key from the **structlog event dict**,
>   while `structlog.stdlib.BoundLogger.exception` has already handed `exc_info=True` to
>   `logging.Logger.exception`, which sets the **LogRecord** attribute. The two are different
>   objects and only the first is cleared.
>   (3) A synthetic single record through `setup_logging` into a real `FileHandler`:
>   12 physical lines, 1 parseable, 11 not, 4 traceback markers.
> - **One evidence number corrected, and the finding is understated rather than
>   overstated.** The source report's headline is *"141 physical lines; 11 parse; 130 do
>   not"*. Re-measured: **141 physical lines, 3 parse, 138 do not.** The report's own prose
>   elsewhere concedes *"a consumer that parses line by line and stops at the first malformed
>   line recovers 3 of 11"* — which is only consistent with 3 parseable lines, so `11` is a
>   transcription slip against its own table. The corrected ratio is 97.9 % unparseable, not
>   92.2 %. The title's `130 of 141` should read `138 of 141`. Classification of the 138:
>   5 traceback-fragment lines, 125 other (source-line and continuation lines of the appended
>   chain), 8 blank; **0** lines begin with `{` and fail to parse, so the class is "a line
>   with no envelope", not "a record split across physical lines".
> - **Why MEDIUM stands.** The phase's §9 HIGH row for this class reads: *"a log file the
>   product declares machine-readable contains lines no parser reads as a whole, **so that**
>   the diagnosis the file was written to carry is not recoverable from it."* The qualifier
>   is not met, and a measurement the source report did not make is what settles it: **the
>   two shapes do not coincide.** Where the double render occurs the exception record is the
>   last record in the file, so a strict consumer loses nothing; where records continue after
>   it, no exception-bearing record was emitted at all — a 3-URL `batch` on the same commit
>   produced a 14-record file in which **14 of 14 lines parse**, because no
>   `logger.exception` fires on that path. The diagnosis is physically present in both cases.
> - **Anchors: the report's are right for `a335b2a`.** `logging.basicConfig` is
>   `config.py:358-366`, `structlog.processors.format_exc_info` is `config.py:373`, and the
>   renderer selection is `config.py:365-377`. All three verified against
>   `git show a335b2a:src/vkdownloader/config.py`, which is 382 lines; on the current working tree
>   the same code is at `348-356`, `363` and `365-367`, because of the uncommitted edit filed as
>   `VAL-003`.
> - **See also:** `SEC-007` (phase 06, the *contents* of the chain, not re-filed);
>   `VAL-003`.

| Field | Value |
|-------|-------|
| **ID** | OUT-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** When `log_file` is set, `setup_logging` selects `structlog.processors.JSONRenderer()` (`config.py:375-377`) and installs `logging.basicConfig(format="%(message)s", handlers=[logging.FileHandler(...)])` (`config.py:358-366`). The processor chain includes `structlog.processors.format_exc_info` (`config.py:373`), which renders the exception chain into the event but does **not** clear `record.exc_info`. The stdlib `Formatter` then appends the same chain a second time, **outside the JSON envelope**. One `logger.exception(...)` call therefore writes one valid record plus ~130 physical lines carrying no envelope at all.

**Evidence (through the binary; real failing `download`, `VKDOWNLOADER_LOG_FILE` set, two distinct capture files):**

- Declared format: JSON, one object per line.
- Delivered: **141 physical lines; 11 parse; 130 do not.**
- Verbatim, physical lines 3-5:

```
{"url": "https://vkvideo.ru/***REDACTED***", "event": "download_failed", "level": "error", "timestamp": "2026-09-29T19:05:24.954187Z", "exception": "Traceback (most recent call last):\n  File \"C:\\Program Files\\Python3...
Traceback (most recent call last):
  File "C:\Program Files\Python312\Lib\urllib\request.py", line 1344, in do_open
```

- Per class: **a record split across physical lines** (line 3's `exception` field, continued raw from line 4) and **a line with no envelope** (lines 4-141). The chain appears **10 times** as a `Traceback (most recent call last)` marker in a 22 075-byte file, for 5 chained blocks, i.e. the same traceback twice.
- **Unextracted result, recorded once:** a consumer that parses line by line and stops at the first malformed line recovers **3 of 11** records; a consumer that skips malformed lines recovers 11 of 11. The diagnosis itself survives, inside line 3's `exception` field, which is why this is not filed at the `## 9` HIGH bar ("the diagnosis the file was written to carry is not recoverable from it").

**Mechanism confirmed in process** (not inferred): one `logger.exception` call with a two-link chain driven through `setup_logging` into a `StringIO` handler produces **19 physical lines with the chain present twice**, once from `format_exc_info` and once appended by `logging.Formatter`.

The same double emission produced 10 `Traceback` markers and 2 `yt_dlp.utils.DownloadError:` lines in the 22 303-byte captured stderr of the equivalent run with no log file. The *content* of that traceback (a verbatim `yt_dlp.utils.DownloadError`) is **SEC-007** (phase 06) and is cross-referenced, not re-filed; what is filed here is the record's shape and the file's parseability, which `## 7` assigns to this phase.

**Recommendation:** Give the traceback one owner. Keep `format_exc_info` (it is what puts the diagnosis inside the envelope) and stop the stdlib formatter re-appending it: add a one-line processor after `format_exc_info` that pops `exc_info` from the event dict, or give the `FileHandler`/`StreamHandler` a formatter that ignores `record.exc_info`. Then add a regression check that a written log file parses end to end, so a future record type cannot silently reintroduce this.

---

### OUT-003: The batch binds a correlation id per video, then a second id overwrites it, so the failure record matches no other record of its own operation

> **Validation Note:**
> - **Action:** merged → `ENT-012` (phase 01, HIGH, already validated)
> - **Severity:** MEDIUM as filed; the absorbing finding `ENT-012` is already validated at
>   **HIGH**, so the merge raises nothing's severity and loses nothing from this one
> - **Detail:** The root cause is one thing, already owned, already validated and already
>   carrying the identical recommendation. `ENT-012` states: *"the inner bind at
>   `downloader.py:664` shadows the item identifier, and the inner `finally` at `:708`
>   clears the whole structlog context, taking the item identifier with it. The code already
>   works around this: the two error handlers in `_download_single` pass the identifier as an
>   explicit log field"* — which is precisely the `correlation_id=correlation_id` workaround
>   this finding re-derives at `batch_downloader.py:271`. Its recommendation is verbatim
>   this finding's: *"Removing the bind/clear pair at `services/downloader.py:663-664` and
>   `:708` — and moving them to the single-download command."* Filing this separately would
>   put the same one-line fix in two remediation queues. Merged, not re-filed.
> - **The evidence was independently reproduced before the merge was decided.** A 3-URL
>   `batch` with a log file, on `a335b2a`, read as a record table: 14 records, in the source
>   report's exact order — `invalid_url_in_batch` (no id) · `batch_download_started`
>   (`b06327e9` as both `correlation_id` and `batch_correlation_id`) · three
>   `extracting_streams` with three *different* ids (`e7a7d2c5`, `a214b4f5`, `b94c3da5`) ·
>   three `ytdlp_extraction_error` with **no** id · three `extraction_error` whose ids
>   (`8f4e1f8d`, `36e59882`, `b4df1707`) appear on **no other record in the run** · three
>   `download_finished` with no id. The table is exact; the prose is not.
> - **One evidence number corrected.** The source report's headline is *"Six distinct
>   correlation ids for three videos."* Its own evidence table lists **seven**: one batch, three
>   inner (`download_video`), three outer-item (`_download_single`). Measured: **7 distinct
>   values.** The table is right; the sentence is not.
> - **Unmerged remainder — retained, and it is not `ENT-012`'s.** Two observations in this
>   finding's body fall outside `ENT-012` and have no owner:
>   (a) `ytdlp_extraction_error` (`extractor.py:226-230`) carries no `correlation_id` for a
>   reason `ENT-012` does not describe. The call is inside `_sync_extract`, which is submitted
>   with `loop.run_in_executor(None, _sync_extract)` at `extractor.py:243`. `run_in_executor`
>   does **not** propagate the caller's `contextvars` context to the worker thread (unlike
>   `asyncio.to_thread`), so `structlog.contextvars.merge_contextvars` — first in the chain at
>   `config.py:360` — sees an empty context. This is a second, independent root cause for a
>   record that cannot be joined.
>   (b) The item-identity gap: `extracting_streams` carries `video_id`, while
>   `extraction_error`, `ytdlp_extraction_error` and `download_finished` carry no `video_id`
>   and no `video_index`, so a redacted `url` is the only identity on the failure records.
>   `ENT-012`'s recommendation does not cover either. `VAL-` is reserved for defects in the
>   audit's own inputs, so this phase does not file them; they are recorded here so the merge
>   does not silently absorb them, and a later run must not treat `ENT-012` as closing them.
> - **Anchors: exact.** `downloader.py:658-659`, `batch_downloader.py:195-196`, `:271`, `:318-319`,
>   `:338-356` and `:396` are all correct; `downloader.py` and `batch_downloader.py` carry no
>   uncommitted edit, so these hold in both the committed and the working tree.
> - **Phase 01's own drift, recorded so a remediation of `ENT-012` does not chase it.**
>   `ENT-012` cites `downloader.py:663-664` and `:705-708`, which are 5 lines high for
>   `658-659` and `700-703`, and `:274` / `:291` for `271` / `:288`. That drift is phase 01's
>   own and is **not** part of the working-tree change in `VAL-003`.
> - **See also:** `ENT-011` (phase 01, the chained half); `VAL-003`; `OUT-004` (merged into
>   the same target).

| Field | Value |
|-------|-------|
| **ID** | OUT-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/utils/correlation.py` |
| **Classification** | mandatory |

**Description:** `_download_single` binds a per-operation id (`batch_downloader.py:195-196`). `download_video`, which it then awaits, binds **a second, different id** in the same context (`downloader.py:658-659`), shadowing the first. Every record emitted *inside* `download_video` therefore carries the inner id; the `extraction_error` record written back in `_download_single` passes the outer, shadowed local explicitly (`batch_downloader.py:271`). The two values never match, and the batch id itself (`batch_downloader.py:318-319`) is carried by no child record. This contradicts the contract stated in `utils/correlation.py:1-8`: "every log entry emitted within a logical operation ... carries a `correlation_id` field ... possible to filter and group log output for a specific request".

**Evidence (through the binary; `batch` over 3 URLs, log file enabled; the record set read as a table, 14 records):**

| # | event | correlation_id | item identity carried |
|---|---|---|---|
| 1 | `invalid_url_in_batch` | *(absent)* | redacted url |
| 2 | `batch_download_started` | `7a77d909` | `url_file_count=3` |
| 3 | `extracting_streams` | `07d16a28` | `video_id=1_1` |
| 4 | `extracting_streams` | `62c27f05` | `video_id=2_2` |
| 5 | `extracting_streams` | `7431d4ab` | `video_id=3_3` |
| 6 | `ytdlp_extraction_error` | *(absent)* | redacted url, identical to the other two |
| 7 | **`extraction_error`** | **`908b8109`** | redacted url |
| 8 | `ytdlp_extraction_error` | *(absent)* | redacted url |
| 10 | **`extraction_error`** | **`fd5fb434`** | redacted url |
| 12 | `ytdlp_extraction_error` | *(absent)* | redacted url |
| 13 | **`extraction_error`** | **`ce4159af`** | redacted url |

**Six distinct correlation ids for three videos.** The failure record (7/10/13) carries an id that appears on **no other record in the run**; its own extract record carries a different one (3/4/5). The child-suppression record (6/8/12) carries no id at all and no `video_id`, and its `url` is redacted to the same `https://vkvideo.ru/***REDACTED***` for all three items, so it cannot be attributed to an item either. A reader who wants "everything that happened to video 3_3" must reconstruct it from timestamps and free text, not from the join key.

**Binding visibility per dispatch path:** the batch id is visible inside each task (asyncio copies the context at `create_task`, `batch_downloader.py:338-356`) and is then shadowed; the parent's `clear_correlation_id()` in the outer `finally` (`batch_downloader.py:396`) cannot clear a task's context. Visibility is therefore not the defect; the double bind is.

**Recommendation:** Bind the operation id exactly once, at the layer that owns the operation. Concretely: drop the bind/clear pair from `download_video` (`downloader.py:658-659`, `700-703`) and let the caller own it, so `_download_single`'s id is the one every record of that video carries; give the single-download path its own bind in `cli.py`'s command, around the whole `asyncio.run`. Then carry `video_index` on the `extraction_error` and `ytdlp_extraction_error` records so a redacted URL is not the only item identity. Cross-referenced, not re-filed: the redaction that collapses three distinct URLs into one is **SEC-007**'s neighbourhood (phase 06); the identity fields are this phase's.

---

### OUT-004: The record that names each item's terminal outcome is written after the binding is cleared, so it carries no join key at all

> **Validation Note:**
> - **Action:** merged → `ENT-012` (phase 01, HIGH, already validated)
> - **Severity:** LOW as filed; the absorbing finding is validated at **HIGH**
> - **Detail:** This is `ENT-012`'s own consequence paragraph, restated from the other end.
>   `ENT-012` states, verbatim: *"records emitted after `download_video` returns or raises
>   carry no correlation identifier at all."* That is this finding's entire claim, and
>   `ENT-012` was already validated on it with the identical fix. The phase-08 validator
>   reproduced both halves before merging:
>   (1) *Through the binary* — a 3-URL `batch` on `a335b2a` emits three
>   `download_finished` records carrying `video_index` 0, 1, 2 and **no `correlation_id`, no
>   `url`, no `video_id`**, while the same run's `extracting_streams` records identify the
>   same three items by `video_id`. The source report's verbatim sample line is exact.
>   (2) *In process* — driving `_download_single` with `download_video` stubbed, so its
>   `finally` never runs, produces `download_finished` records **with** a
>   `correlation_id`. This is an independent reproduction of the source report's own
>   control, and it localises the cause to the `clear_contextvars()` at `downloader.py:703`
>   rather than to the record's construction — exactly as filed.
>   `_log_finished` (`progress_display.py:383-393`) passes `video_index`, `video_label`,
>   `status`, `downloaded`, `total` and nothing else, so the key can only come from the
>   context.
> - **Unmerged remainder:** the additive half of this finding's recommendation — put
>   `video_id` on `download_finished` so both halves of one video's records are keyed the
>   same way — is **not** carried by `ENT-012`'s recommendation. Retained here for the same
>   reason as in `OUT-003`: the merge must not be read as closing it.
> - **Anchors:** `downloader.py:700-703` and `batch_downloader.py:245-247` and
>   `progress_display.py:383-393` are all **exact**.
> - **See also:** `OUT-003` (same target, same root cause); `ENT-012`.

| Field | Value |
|-------|-------|
| **ID** | OUT-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/progress_display.py` |
| **Classification** | mandatory |

**Description:** `download_video` clears every context variable in its `finally` (`downloader.py:700-703`). The batch layer writes the item's terminal record *after* that call returns (`batch_downloader.py:245-247` → `_finish` → `reporter.finish_task` → `progress_display.py:383-393`). So the one record that states "this item finished, with this outcome" is emitted with no `correlation_id` and no URL. It is written **after** the clearing, which is the order the check asks about; the same call site clears before the failure record in `OUT-003` is written, which is why that one had to pass the id by hand.

**Evidence (through the binary; same run as `OUT-003`, records 9, 11, 14):**

```
{"video_index": 2, "video_label": "video_2", "status": "failed", "downloaded": 0, "total": 0, "event": "download_finished", "level": "info", "timestamp": "2026-09-29T19:04:29.723548Z"}
```

No `correlation_id`, no `url`, no `video_id`. `video_index` is the only handle, and the same run's `extracting_streams` records identify their item by `video_id`, so the two halves of one video's record set do not even use the same key.

**Evidence that the cause is the clear (in process):** driving the same code path with `download_video` stubbed, so its `finally` never runs, produced `download_finished` records **with** `correlation_id=8d243b45` and `correlation_id=47b32df2` for the same two calls. The missing key is therefore caused by `downloader.py:703`, not by the record's own construction.

**Recommendation:** Let the caller own the binding lifetime end to end (same change as `OUT-003`) so the clearing happens after the terminal record, and add `video_id` to the `download_finished` event so both halves of a video's records are keyed the same way.

---

### OUT-005: `--max-retries` is a usage error the product reports on the status its own reference reserves for a failed download

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM (retained)
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **Detail:** Re-derived end to end, through the binary, thirteen argument shapes, one
>   fresh working directory each, two distinct capture files per shape. The measured status
>   table is the source report's table exactly: no command / unknown command / missing
>   argument / unknown option / `--quality bogus` / `--method bogus` /
>   `--cookie-source bogus` / `--max-retries abc` / `batch` on a non-existent file → **2**;
>   **`--max-retries 0` → 1** and **`--max-retries 99` → 1**; invalid URL → 1. The recovery
>   message is verbatim identical, including the two lines that are the substance of the
>   second consequence: `Check your .env file or VKDOWNLOADER_* environment variables:` for a
>   value that was typed on the command line.
> - **Severity:** the phase's §9 MEDIUM row reads *"Two outcomes a caller would act on
>   differently report the same status."* A rejected `--max-retries 0` is a usage error — on
>   the reference's own reading of status `2`, *"nothing was attempted"* — and it returns
>   `1`, the status of a failed download, against a reference that says at `cli-reference.md:87`
>   that a script *"must not treat it as a failed download."* The row is met verbatim.
> - **Document anchors, all exact and independently re-read against the committed tree:** the
>   download option table is `cli-reference.md:62-68` and omits `--max-retries`;
>   `--max-retries` appears only in the batch table at `:124` with its bound `(1-10)` at `:135`;
>   the status map and its *"terminal outcome in its own right"* sentence are at `:84`/`:87`
>   (download) and `:170`/`:173` (batch). The `download` command's own `--max-retries`
>   declaration is `cli.py:152-157` and its help text states neither the bound nor the env
>   source, while the two neighbouring options state both — the asymmetry the finding reports is
>   real. Every anchor the finding uses for an exit status was checked against
>   `git show a335b2a:src/vkdownloader/cli.py` and is a `typer.Exit` raise at the cited line:
>   `code=1` at `206, 213, 219, 239, 242, 248, 340, 343, 356` and `code=130` at `222` and `346`.
>   **The report's anchors are correct.**
> - **Not a re-file of `CFG-003`:** the recovery round trip was run to its end as the source
>   report states. The recommended name is a valid setting, so the binding-rule-4 case does
>   not arise; that the recommendation is the *wrong* setting stays `CFG-003`'s.
> - **See also:** `CFG-003` (phase 02); `ENT-008` (phase 01, the 0/1/130 decision's location);
>   `VAL-003`.

| Field | Value |
|-------|-------|
| **ID** | OUT-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py`, `docs/99-reference/cli-reference.md` |
| **Classification** | mandatory |

**Description:** The status the caller receives is chosen by two different authorities. The argument layer (Typer/Click) returns `2` for every rejection it makes; the product returns `1` from its own handlers (`cli.py:206, 213, 219, 222, 239, 242, 248` and `340, 343, 346, 356`) and `0`/`130` from its outcome logic. `--max-retries` is the one option that sits on the seam: its type is `int` at the parser and its bound (`ge=1, le=10`) is enforced only by the model, so a non-integer is rejected by the argument layer and an out-of-range integer by the product.

**Evidence (through the binary; thirteen argument shapes, one fresh working directory each; the product's own recovery message captured verbatim and every value it recommends fed back):**

| Shape | Status | Chosen by |
|---|---|---|
| no command · unknown command · missing argument · unknown option | **2** | argument layer |
| `--quality bogus` · `--method bogus` · `--cookie-source bogus` | **2** | argument layer |
| `--max-retries abc` | **2** | argument layer |
| `batch no_such_file.txt` (declared `exists=True`) | **2** | argument layer |
| **`--max-retries 0`** | **1** | **product** |
| **`--max-retries 99`** | **1** | **product** |
| invalid URL · no URLs in file · unreadable URL file · failed download | **1** | product |
| success | 0 | product |
| cancelled | 130 | product |

Recovery message for `--max-retries 0`, verbatim on stderr, exit 1:

```
Configuration error: one or more settings have invalid values.
Check your .env file or VKDOWNLOADER_* environment variables:
  - max_retries: Input should be greater than or equal to 1
    Received: <redacted>
Fix the offending value(s) and try again.
```

Two consequences follow. First, the message names `.env` and `VKDOWNLOADER_*` as the place to look, but the value the user typed was on the **command line**; nothing in `.env` is involved. Second, and worse for a script, `docs/99-reference/cli-reference.md:84,87` (and `:170,173`) declares: *"`2` is a terminal outcome in its own right, deliberately separate from `1`: on `2` nothing was attempted, so a script must not treat it as a failed download."* A script that follows that rule classifies a rejected `--max-retries` as a failed download. The same option is documented with its bound and its env source only in the `batch` table (`cli-reference.md:124,135`); the `download` option table (`:62-68`) omits `--max-retries` altogether although the command declares it (`cli.py:152-157`), and its `--help` text states neither the bound nor the env source that the two neighbouring options do state.

**Recovery round trip (R1, run to its end).** The only other product-issued recommendation, the "did you mean" line for an unknown `VKDOWNLOADER_*` variable, was captured verbatim (`Did you mean: VKDOWNLOADER_DOWNLOAD_TIMEOUT? (check for typos)`) and the recommended name fed back — it is a valid setting, so the binding-rule-4 case (a recommendation routed into a status the product's own code never chooses) **does not occur here**. That the recommendation is the *wrong* setting is **CFG-003** (phase 02) and is cross-referenced, not re-filed.

**Recommendation:** Move `--max-retries` onto the argument layer's side of the seam by giving it a Typer-bounded type (`min=1, max=10`), so a rejected value is `2` like every other option and the parser's message lists the range. Independently, make `format_validation_error` name the source that actually produced the bad value (it is told only the `ValidationError` today, so it has to guess), and add `--max-retries` plus its bound and env source to the `download` option table in the reference.

---

### OUT-006: The log stream is written with terminal control sequences in every redirected run, which the reference says never happens

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM (retained)
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **Detail:** Re-derived through the binary with the two streams to two distinct files and
>   the control bytes counted in the raw bytes of each. A 2-URL `batch` with no log file:
>   **stdout 332 bytes / 0 ESC, stderr 3 836 bytes / 187 ESC** — the source report's
>   headline figure of **187 ESC bytes on stderr** reproduced exactly; the byte totals differ
>   only because the run's record count differs. The first captured stderr line is verbatim
>   as filed, `[2m2026-09-29T19:32:59…[0m [[32m[1minfo     [0m] [1mbatch_download_started…`.
>   The code side is exact: `config.py:365-367` selects `structlog.dev.ConsoleRenderer()`
>   with **no colour argument and no `isatty()` condition**, and `config.py:348-356`
>   installs a bare `logging.StreamHandler()`, which resolves to stderr.
> - **Severity:** the contradicted sentence is `cli-reference.md:162` — *"When the output
>   stream is not a terminal (piped, redirected, or CI) the display is never started and
>   **no escape codes are written**."* The first clause holds (the display never started in
>   any capture); the second is false, and it is false in the direction the reference calls
>   safe. A CI log collector must strip ANSI before it can read a single line. The source
>   report's own framing — that the class is present in the captured direction and equally
>   present when a human watches a terminal, so it is not a capture-dependent class — is
>   correct and is retained.
> - **Type legality:** `SPEC-DEVIATION` is the right label and `DOC-UPDATE` is correctly
>   avoided. The phase's §9 states *"This phase files no `DOC-UPDATE` — a documented claim is
>   `09`'s"*, and the defect here is a renderer that contradicts the product's own declared
>   output property, not a document that misdescribes correct code.
> - **Anchors: the report's are right for `a335b2a`.** The renderer selection is
>   `config.py:365-377` (a `JSONRenderer()` / `ConsoleRenderer()` ternary with no colour
>   argument and no `isatty()` condition) and `logging.basicConfig` is `config.py:358-366`,
>   installing a bare `logging.StreamHandler()` that resolves to stderr. Both verified against
>   `git show a335b2a:src/vkdownloader/config.py`. `config.py:377`, cited in the recommendation
>   as the renderer line, is `else structlog.dev.ConsoleRenderer(),` at that commit, as filed.
> - **See also:** `OUT-002` (the same capture also shows the double-rendered chain, which is
>   that finding's mechanism, not re-filed here); `VAL-003`.

| Field | Value |
|-------|-------|
| **ID** | OUT-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py`, `docs/99-reference/cli-reference.md` |
| **Classification** | mandatory |

**Description:** `setup_logging` builds the console renderer with no colour decision and no condition on the stream being a terminal: `structlog.processors.JSONRenderer() if settings.log_file else structlog.dev.ConsoleRenderer()` (`config.py:375-377`). With no log file, `logging.basicConfig` installs a bare `logging.StreamHandler()` (`config.py:358-366`), which resolves to **stderr**, so every record the product emits goes to the error stream. Nothing in that path consults `isatty()`.

**Evidence (through the binary; both streams to two distinct files, control sequences counted in the raw bytes of each):**

| Run | stdout bytes | stdout ESC | stderr bytes | stderr ESC |
|---|---|---|---|---|
| `batch` over 2 URLs, no log file | 326 | **0** | 5 172 | **187** |
| `download`, no log file, failing | 0 | **0** | 22 303 | **45** |
| `batch` over 3 URLs, log file set | 457 | **0** | 1 522 | **0** |
| `download`, log file set, failing | 0 | **0** | 525 | **0** |

Verbatim first line of the captured stderr, `batch` with no log file (the `[2m` prefixes are real ESC bytes):

```
[2m2026-09-29T19:16:24.790669Z[0m [[32m[1minfo     [0m] [1mbatch_download_started        [0m ...
```

Every one of the 11 captured stderr lines in that run carries colour; the 187 ESC bytes are spread across them. A consumer of a redirected run — a CI log collector, `grep`, an aggregator, `less` — must strip ANSI before it can read a single line.

`docs/99-reference/cli-reference.md:162` states: *"When the output stream is not a terminal (piped, redirected, or CI) the display is never started and **no escape codes are written**."* The first half is correct and was confirmed (the display never started in any capture). The second half is false: escape codes are written, by the log renderer rather than by the display. The class is not capture-*dependent* — it is present in the captured direction and equally present when a human watches a terminal — so it is filed as a contradicted guarantee rather than as a capture-dependent class.

The same capture also carries the console-stream face of `OUT-002`: the exception chain appears twice in 22 303 bytes (10 `Traceback (most recent call last)` markers, 2 `yt_dlp.utils.DownloadError:` lines) because `format_exc_info` and the stdlib `Formatter` both render it. That duplication is `OUT-002`'s mechanism; only the record shape is re-filed here.

**Recommendation:** Pass a colour decision to the renderer derived from the stream it actually writes to — `ConsoleRenderer(colors=sys.stderr.isatty())` — and, if a colour decision must follow a declared setting, add that setting to the option surface (`OUT-013`). The bound is one argument at `config.py:377`; the work is deciding which stream the console renderer is for, and the answer is already forced by the `StreamHandler` two lines above it.

---

### OUT-007: The child's own error text reaches the caller only when the run is captured; when the display is active it is dropped with no destination

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM (retained)
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **Detail:** Admissibility checked against the phase's own preamble rule 1, which
>   forbids a through-the-binary claim about the suppressed child output. The finding is
>   admissible: its captured-direction evidence is about the direction in which the display
>   is **inactive** and the child echo is therefore **on**, and its watched direction carries
>   an explicit `UNVERIFIED` marker. The phase also *requires* this subject to be reported
>   rather than omitted. Structurally re-derived and exact: `batch_downloader.py:224`
>   `echo = not reporter.is_enabled`; `progress_display.py:126-136` resolves `is_enabled`
>   to `sys.stderr.isatty()`; `ytdlp_downloader.py:211-220` sends a **progress** line to
>   `logger.debug("ytdlp_progress_suppressed", …)` — discarded at the default `INFO` level —
>   and then `return`s **unconditionally at `:220`**, so every non-progress line, errors
>   included, reaches no stream and no log record.
> - **One thing the source report does not say, and which bounds the severity.** The
>   suppression is **declared by the code itself**: the docstring at
>   `ytdlp_downloader.py:206-209` states *"When `echo` is `False` (batch mode), nothing is
>   written to stderr at all — progress data is emitted at DEBUG level instead and
>   **non-progress lines are dropped silently**."* This is a deliberate arrangement, not an
>   oversight, and the defect is a **contract disagreement**, not a silent loss:
>   `cli-reference.md:160` describes only *"yt-dlp's own native progress **echo** is
>   suppressed"*, which is narrower than what the code does, and the source report is right
>   that the gap between the two sentences is the finding.
> - **Why the severity does not reach the §9 HIGH row.** That row requires *"a fact a caller
>   must act on appears on one stream and not the other, and the caller reads the one that
>   omits it."* The fact is **not lost**: on the same run the application emits its own
>   `ytdlp_extraction_error` (`extractor.py:226-230`) and `extraction_error`
>   (`batch_downloader.py:268-273`) records, which carry the same message and do reach the
>   surface — into the live region, because `_repoint_log_handlers` rebinds the root
>   `StreamHandler` at `progress_display.py:160`. What is lost is the child's own channel,
>   not the diagnosis. MEDIUM on a contradicted reference sentence stands.
> - **The `UNVERIFIED` marker is correctly placed and correctly retained.** No real terminal
>   exists on the declared platform and none may be substituted; the watched consequence was
>   not observed and is not claimed. The recommendation's own instruction — re-measure
>   through a real terminal before treating the watched consequence as confirmed — is the
>   correct disposition and is retained.
> - **See also:** `TRN-009` (phase 05, the child's reporting channel and redaction — the
>   arbitration is this phase's, per §7); `SEC-007` (phase 06, the error text's contents).

| Field | Value |
|-------|-------|
| **ID** | OUT-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `docs/99-reference/cli-reference.md` |
| **Classification** | mandatory |

**Description:** The arbitration is one line: `echo = not reporter.is_enabled` (`batch_downloader.py:224`), read after `reporter.start()`. `is_enabled` is `sys.stderr.isatty()` (`progress_display.py:136`). When the display is active, `echo` is `False` and `_echo_ytdlp_line` (`ytdlp_downloader.py:211-220`) sends a progress line to `logger.debug("ytdlp_progress_suppressed", ...)` — discarded at the default `INFO` level — and **returns for every other line**, dropping it with no destination at all. The suppression is therefore not "the progress echo"; it is the whole child output, errors included.

**Evidence — captured direction (through the binary; two distinct files):** the captured stderr of a 3-URL `batch` carried, and stdout carried nothing of the kind:

```
ERROR: [vk] -3_3: Unable to download JSON metadata: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1000) (caused by CertificateVerifyError(...)); please report this issue on https://github.com/yt-dlp/yt-dlp/issues?q= ...
ERROR: [vk] -1_1: Unable to download JSON metadata: [SSL: CERTIFICATE_VERIFY_FAILED] ...
ERROR: [vk] -2_2: Unable to download JSON metadata: [SSL: CERTIFICATE_VERIFY_FAILED] ...
```

The stdout account for the same run names only the status code, three times over:

```
https://vkvideo.ru/video-1_1: extraction_error
...
  Failed: 3
  Failed URLs:
    - https://vkvideo.ru/video-1_1: extraction_error
```

**Evidence — watched direction: `UNVERIFIED`.** No real terminal exists on the declared platform and none may be substituted (R-N, preamble rule 1), so the runtime consequence of an active display was not observed through the binary. What is established is structural and read from the code: the predicate at `batch_downloader.py:224`, the drop at `ytdlp_downloader.py:211-220`, and the fact that a dropped line is written to no stream and no log record. The nearest surviving copy is the application's own `ytdlp_extraction_error` / `extraction_error` records, which carry the message but not under the child's own channel and (per `OUT-003`) not joinable to the item.

`docs/99-reference/cli-reference.md:160` describes the suppression as *"yt-dlp's own native progress **echo** is suppressed while the display is active"*, and `:162` as the non-terminal case where the *"progress echo stays on stderr"*. Neither sentence says that non-progress lines — the only lines carrying a diagnosis — are discarded. That gap is what this finding is.

**Recommendation:** Narrow the suppression to what the display actually needs to own. Route non-progress child lines to a `logger.warning` (they are exactly the failure signal) instead of discarding them, and keep the in-place rewrite for progress lines only. That is a one-branch change inside `_echo_ytdlp_line` and it makes the watched terminal strictly more informative than it is today, without touching the display itself. Re-measure through a real terminal before treating the watched consequence as confirmed.

---

### OUT-008: The account's "Total connections" line reports the number of videos, and the reference is silent about what it counts

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM (retained)
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **Detail:** Reproduced through the binary. A 3-URL `batch` on `a335b2a` prints, from
>   `_print_batch_summary`:
>
>   ```
>     Total connections: 3
>     Skipped (invalid URLs): 1
>     Peak concurrent videos: 0
>     Successful: 0
>     Failed: 3
>     Failed URLs:
>       - https://vkvideo.ru/video-1_1: extraction_error
>   ```
>
>   The source report's headline — `Total connections: 3` printed on the line directly above
>   `Peak concurrent videos: 0`, for three videos — is reproduced exactly. The code anchors
>   are exact: `batch_downloader.py:436` `typer.echo(f"  Total connections: {len(results)}")`
>   and `:439` `typer.echo(f"  Peak concurrent videos: {peak_concurrent_videos}")`; the
>   `ConcurrencyTracker` docstring at `:45-46` states *"The unit is **videos**, not segments"*
>   and the segment-layer note at `:65-68` confirms the batch semaphore gates one permit per
>   video, so the peak is a video count. Both figures are therefore per-video and mutually
>   impossible: the batch measured no concurrency at all.
> - **Severity:** the phase's §9 MEDIUM row reads *"An account label naming a quantity its
>   value does not match."* Verbatim.
> - **One claim withdrawn as unsupported, and it is not needed.** The source report adds
>   *"off by two to three orders of magnitude"*. No connection count exists anywhere in the
>   product — there is no counter, so no connection figure was ever measured and the ratio
>   cannot be derived from anything. The magnitude claim is unmeasured and is **withdrawn**.
>   The finding does not depend on it: the mismatch between the label and the value is
>   established by the account itself, and the fix is the same either way (decide and
>   document one unit; if a connection count is wanted, count connections). A remediation
>   must not treat "three orders of magnitude" as a measured baseline.
> - **See also:** `ENT-008` (phase 01, `typer.echo` in `batch_downloader.py` — the location,
>   not the label); `OUT-009` (the same account, the same aggregation).

| Field | Value |
|-------|-------|
| **ID** | OUT-008 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py` |
| **Classification** | mandatory |

**Description:** The account's first line is `typer.echo(f"  Total connections: {len(results)}")` (`batch_downloader.py:436`). `results` holds one tuple per **video** in the batch. Every other statement of the product's own unit says videos: `ConcurrencyTracker`'s docstring is explicit — *"The unit is **videos**, not segments"* (`batch_downloader.py:45-46`) — and the very next concurrency line reads `Peak concurrent videos` (`batch_downloader.py:439`). One video is many HTTP connections (the segment layer fans out, `batch_downloader.py:65-68`), so the labelled quantity is not merely mislabelled, it is off by two to three orders of magnitude. No document defines the summary's format, so the reference is silent rather than contradicting it; the deviation is against the product's own declared unit.

**Evidence (through the binary; `batch` over a file of 3 valid URLs plus 1 invalid and 1 comment line; stdout and stderr to two distinct files).** The rendered account, verbatim:

```
https://vkvideo.ru/video-1_1: extraction_error
https://vkvideo.ru/video-2_2: extraction_error
https://vkvideo.ru/video-3_3: extraction_error


Download Summary:
  Total connections: 3
  Skipped (invalid URLs): 1
  Peak concurrent videos: 0
  Successful: 0
  Failed: 3
```

Per label, the quantity named against the quantity delivered: `Total connections: 3` names connections, delivers 3 videos. `Skipped (invalid URLs): 1` matches its value. `Successful: 0` and `Failed: 3` match the three per-item lines above. `Peak concurrent videos: 0` is accurate for what was measured but not for what was attempted; **the accuracy of a concurrency figure is phase 04's** (cross-referenced, not filed here) — what is this phase's is the label beside it, which correctly says "videos". Note also that the label is the one place a reader would go to reconcile the 5 lines they supplied against the 3 that were attempted, and it does not get them there either: the supplied count is never stated.

**Recommendation:** Rename the line to `Total videos:` (or `Total items:`) so the label names what `len(results)` holds, matching the unit the rest of the summary and the concurrency tracker already use. While there, state the number of URLs read from the file alongside the skipped count, so the three counts a reader can reconcile are all present. The label change is one string.

---

### OUT-009: `ProgressStatus.SKIPPED` is rendered by the display and documented, but the aggregation rule never decides what it becomes

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** LOW (retained)
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **Detail:** Re-derived structurally; every producer was traced, and the absence is
>   confirmed rather than assumed. `ProgressStatus.SKIPPED` exists as a `StrEnum` member
>   (`enums.py:79`) and is rendered in both surfaces — `_StatusColumn.render` returns
>   `Text("[⊘]", style="yellow")` at `progress_display.py:69-70` and `_format_outcome`
>   returns `"skipped"` at `:88-89` — and the reference documents the marker at
>   `cli-reference.md:158`. But no code path yields it: `_to_progress_status`
>   (`batch_downloader.py:161-171`) returns only `SUCCESS`, `FAILED` or `CANCELLED`; the
>   status literals `_download_single` returns and `_print_batch_summary` reads come from
>   `_classify_download_result` (`:152-156`), which returns only `SUCCESS.value`,
>   `CANCELLED.value` or `FAILED.value`; the invalid-URL path never creates a
>   `DownloadContext` at all and is counted separately as `skipped_count` (`:200-213`), a
>   different quantity which the account prints under its own label at `:437-438`. The
>   aggregation at `:431-433` names `SUCCESS` and `CANCELLED` and derives `FAILED` by
>   subtraction, so a fourth status could not appear in the counts even if one were produced.
> - **Severity:** the phase's §9 LOW row reads *"A per-item status class the aggregation
>   rule is silent about."* Verbatim. The source report's own reading — a class the
>   aggregation cannot name, awaiting a producer — is correct and is retained, and its
>   `unresolved` classification is honest: the intent behind `SKIPPED` (a per-video skip
>   distinct from a per-line invalid-URL rejection) is stated nowhere in the repository.
> - **Anchor correction (stands):** `enums.py:78` → `enums.py:79` for `SKIPPED = "skipped"`;
>   line 78 is blank. `enums.py` carries no uncommitted edit, so this one is a real, independent
>   one-line drift.
> - **Filing the check and answering it was correct, and is retained as such.** The phase
>   required this row (§7, "a per-item terminal status with no producer") and required the
>   answer to be the row itself rather than a manufactured finding. This row is the answer.

| Field | Value |
|-------|-------|
| **ID** | OUT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/models/enums.py`, `src/vkdownloader/services/progress_display.py` |
| **Classification** | advisory |

**Description:** The aggregation rule counts two classes explicitly and derives the third by subtraction (`batch_downloader.py:431-433`):

```
successful = sum(1 for _, _, status in results if status == ProgressStatus.SUCCESS.value)
cancelled  = sum(1 for _, _, status in results if status == ProgressStatus.CANCELLED.value)
failed     = len(results) - successful - cancelled
```

`ProgressStatus.SKIPPED` (`models/enums.py:78`) is in neither branch, so a skipped item would be reported as a **failed** item and would appear under `Failed URLs:` (`batch_downloader.py:447-455`). The class is rendered by the display (`progress_display.py:69`, `:88`) and documented with a marker at `docs/99-reference/cli-reference.md:158` (`[⊘]` for `skipped` or `cancelled`), so it is future-proofing rather than dead code and the recommendation here is to establish its purpose, not to remove it. Today no producer yields it: invalid URLs are counted as a separate `skipped_count` and never enter `results` at all, which is why the rule's silence is currently harmless.

**Evidence (read from the aggregation rule, and reproduced in process):** driving `run_batch` with a stop and with an ordinary failure produced accounts whose per-class counting is correct for the classes that exist — `Successful: 0 / Failed: 2` with a `Failed URLs:` block, and `Successful: 0 / Failed: 0 / Cancelled: 2` with the interruption note — and no path produced a `skipped` status. The silence was reached by reading the rule, not by a run.

**Recommendation:** Decide the class now rather than leaving it implied by subtraction: have `_classify_download_result` (or a future skip source) return `SKIPPED` and add it as a third explicit count next to `successful` and `cancelled`, so `failed` becomes a count rather than a remainder. If the class is not intended to be produced yet, say so in the reference line that documents its marker, so a future reader does not take the `[⊘]` skipped marker as reachable.

---

### OUT-010: Two predicates decide one surface and can disagree; the harmful direction is `UNVERIFIED`

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** LOW (retained)
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **Detail:** Re-derived and **executed as a differential measurement**, which the source
>   report correctly declined to claim. With `Console(file=..., force_terminal=True)` and
>   `sys.stderr` a non-TTY stream, the implementation's own two predicates return
>   `sys.stderr.isatty() == False` and `console.is_terminal == True`; with the roles
>   exchanged they disagree the other way. Neither reading is the harness's: `is_enabled`
>   returns `self._console.is_terminal` at `progress_display.py:131-132` when a console
>   exists and `sys.stderr.isatty()` at `:136` when it does not, and the console is
>   constructed later, at `:152-153`, from `Console(stderr=True)`. `Console.is_terminal` is
>   then read again at `:159` to decide repointing and at `:321` for `auto_refresh`. Every
>   anchor in the finding is exact.
> - **Severity:** LOW. The direction that would hurt — rich active while a log handler is
>   not repointed, so log lines write past the live display — needs `is_enabled` false while
>   `is_terminal` true, which the sequence at `:136`/`:152` does not produce. The reachable
>   disagreement is a `Console` constructed at `:152` when `sys.stderr` *is* a TTY but the
>   surrounding stream was swapped, which the live path is designed for. The source report
>   marks the harmful direction `UNVERIFIED` and claims no runtime consequence; that
>   discipline is correct and is retained.
> - **An advisory note, not a finding, recorded because the recommendation is broader than
>   the finding's evidence.** `is_enabled` is consulted in five places, not two: `start()`
>   (`:148`), `start_task` (`:192`), `set_title` (`:212`), `update` (`:230`) and
>   `finish_task` (`:248`) in this module, plus `batch_downloader.py:224` to decide `echo`.
>   Moving the decision after the console is built — the finding's recommendation — changes
>   the value observed by all six, including the one that decides the child's suppression in
>   `OUT-007`. The shape change is right; the blast radius belongs in the ticket. The
>   regression surface is the four `test_progress_display.py` anchors the finding lists
>   (`:254`, `:287`, `:329`, `:418`) plus the seven
>   `assert "Traceback" not in result.output` sites in `test_cli.py` (`:151`, `:1172`,
>   `:1186`, `:1201`, `:1214`, `:1715`, `:1739`) — all verified exact.
> - **See also:** `OUT-007` (shares the `echo = not reporter.is_enabled` decision);
>   `ENT-013` (phase 01, the invocation cost the test-guard argument leans on).

| Field | Value |
|-------|-------|
| **ID** | OUT-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/progress_display.py` |
| **Classification** | advisory |

**Description:** Whether the live display runs is decided by `sys.stderr.isatty()` (`progress_display.py:136`), which consults no environment variable. Whether the display renders *and repaints*, and whether the process's own log handlers are repointed onto the live region, is decided by rich's `Console.is_terminal` (`progress_display.py:131`, `:160`, `:321`) — a different predicate over the same stream, layered with `_force_terminal`, a Jupyter check, `TTY_COMPATIBLE` and `FORCE_COLOR` (read from the installed `rich` 15.0.0, `console.py:938-988`). `TERM` reaches the same surface through `is_dumb_terminal` (`console.py:979-988`, used by `live.py:141`). The two are read at different moments: `is_enabled` decides at `progress_display.py:148`, the console is built at `:152-153`, and the other two reads happen after it.

**Evidence (in process; production construction, one variable set at a time, both predicates read before and after `start()`):**

| Environment | `is_enabled` (`isatty`) | `Console(stderr=True).is_terminal` | Agree | Display started |
|---|---|---|---|---|
| *(baseline)* | False | False | yes | no |
| `FORCE_COLOR=1` | False | **True** | **no** | **no** |
| `FORCE_COLOR=` (empty) | False | False | yes | no |
| `TTY_COMPATIBLE=1` | False | **True** | **no** | **no** |
| `TTY_COMPATIBLE=` (empty) | False | False | yes | no |
| `TERM=dumb` | False | False | yes | no |
| `NO_COLOR=1` / `NO_COLOR=` | False | False | yes | no |

The measured disagreement is the harmless direction, and that is the point of recording it this way: a colour-forcing variable flips rich's predicate and **not** the activity decision, so in every row the display stayed disabled and the child echo stayed on (`echo` would be `True`). No finding rests on any of these runs.

**The harmful direction is `UNVERIFIED`.** With `is_enabled` True and `Console.is_terminal` False — reachable on a real terminal with `TTY_COMPATIBLE=0` — `start()` would open the display, `progress_display.py:160` would skip `_repoint_log_handlers()`, and `progress_display.py:321` would set `auto_refresh=False`. Log records would then write straight past the live bars, which is precisely the corruption the repoint exists to prevent (`progress_display.py:333-336`), and the display would render one frame and never repaint. **No real terminal exists on the declared platform and none may be substituted (R-N), so this consequence was not observed.**

**Coverage, counted beside the finding and not filed as one:** `0` sites in `tests/` assert that a stream is a terminal. The two terminal-mode sites inject `force_terminal=True` on an in-memory stream (`tests/test_progress_display.py:287`, `:329`) and therefore bypass the detection under audit; the two sites that replace the display module's own view of stderr are `:254` and `:418`; the one command-level runner (`tests/test_cli.py:12,26`) makes the display permanently inactive. **There is no oracle for this disagreement and none was manufactured** — a change that moved either read to a different moment would split the predicates and no test would notice.

**Recommendation:** Read the predicate once. Have `RichProgressReporter` resolve `Console(stderr=True)` and use `console.is_terminal` as the single answer for "am I active", keeping the lazy construction at `:152-153` but moving the `is_enabled` decision after the console exists, so the repoint and the auto-refresh decision cannot disagree with the decision to start. That also removes the need for the `sys.stderr.isatty()` mirror comment at `:133-135`. The disagreement has no regression test to satisfy, so this is a code-shape change, not a behavioural one.

---

### OUT-011: `stop()` restores the borrowed handlers only if the display's own teardown returns (ordering; trigger `UNVERIFIED`)

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** LOW (retained)
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **Detail:** Ordering re-derived and exact. `stop()` at `progress_display.py:171-180` runs
>   `progress.stop()` at `:175`, then `_restore_log_handlers()` at `:176`, then the four
>   unconditional `.clear()` calls at `:177-180` — with no `try`/`finally` anywhere in the
>   method. If `:175` raises, the handler restore is skipped, so the root `StreamHandler`s
>   stay bound to rich's `FileProxy`, which rich tears down inside `Live.stop()`; the
>   process then writes structured log lines into a closed live render, and because
>   `redirect_stderr=True` the app's own output is mediated by a display that is no longer
>   running. If `:176` raises, the four maps leak for the process's lifetime. Every anchor
>   is exact.
> - **Filing discipline confirmed, and it is the point of the finding.** The phase's R-S
>   mandates that a reachability-ordered defect be filed as an ordering defect with the
>   trigger `UNVERIFIED` and with no reproduction manufactured. This finding carries the
>   marker in the prescribed place, presents the happy-path table as in-process observation
>   rather than as a through-the-binary claim, and recommends removing the dependency rather
>   than observing a failure. That is exactly the disposition R-S requires; the validator
>   adds nothing to it and manufactures no reproduction.
> - **Severity:** LOW. The terminal form of the phase's §9 LOW row is *"A handler whose
>   behaviour is a private detail a caller cannot rely on"* — `stop()` is a public method of
>   a public class and its post-conditions are currently neither stated nor guaranteed. The
>   taxonomy has no exact row for "a teardown that can raise"; LOW is the nearest admissible
>   bucket, and the trigger is unobserved.

| Field | Value |
|-------|-------|
| **ID** | OUT-011 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/progress_display.py` |
| **Classification** | advisory |

**Description (ordering, per R-S; the trigger is `UNVERIFIED` and no reproduction was manufactured):** `stop()` releases the borrowed state in two statements and nothing guards the first (`progress_display.py:171-180`):

```
progress = self._progress
self._progress = None
if progress is not None:
    progress.stop()                 # :175  restores sys.stderr
    self._restore_log_handlers()    # :176  restores the handlers
self._tasks.clear()                 # :177
self._titles.clear()                # :178
self._last_values.clear()           # :179
self._last_log_time.clear()         # :180
```

If `:175` raises, `:176` never runs, so the handlers stay bound to the `FileProxy` that `:175` was in the middle of releasing, and the four `clear()` calls are skipped as well, leaking per-task state into a reporter that a later run could reuse. The order is the defect; whether `:175` can raise is not established and was not simulated.

**Evidence — the happy path, in process (R11).** The display was constructed with an explicit file-backed console and driven start → `start_task(0)`/`set_title`/`update`/`finish_task(SUCCESS)` → `start_task(1)`/`update` → `stop`, with a `StreamHandler` on the root logger bound to the real stderr beforehand:

| Moment | Handler's stream |
|---|---|
| before `start()` | `TextIOWrapper`, `is` the real stderr |
| during | `rich.file_proxy.FileProxy`, `is` the stream `Live` recorded as `_redirect_stderr` |
| after `stop()` | `TextIOWrapper`, `is` the original stream |

`sys.stderr` was the original object after `stop()`, `_saved_handler_streams` was empty, and the root handler count was unchanged. The repoint and the restore themselves are correct.

**Recommendation:** Make the restore unconditional rather than sequential: move `_restore_log_handlers()` into its own `try`/`finally` around `progress.stop()`, or run the two releases from separate `finally` blocks so neither can starve the other. The per-task `clear()` calls should be in the outer `finally` for the same reason. Cost is a few lines and no behaviour change on the path that works today.

---

### OUT-012: A line that began work is left non-terminal, with no marker and no outcome word, when `stop()` is driven with work in flight (`UNVERIFIED` through the binary)

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** LOW (retained)
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **Detail:** Re-derived, and the reachability argument **verified rather than accepted** —
>   a filing of this shape is where an unexamined assumption usually hides. The three
>   conditions are exact: `stop()` clears `self._tasks` at `progress_display.py:177` without
>   a terminal status; `transient=False` is passed at `:323`; and `_StatusColumn.render`
>   returns `Text("")` at `:56-57` when `task.fields["status"]` is `None`, which is what
>   leaves the outcome as the bare `video_{N}: title` line the finding describes. Then every
>   path out of `_download_single` was enumerated: `:246-247` (success), `:259-260`
>   (`CancelledError`, including a cancel delivered while awaiting `download_video`), `:262`
>   (`TimeoutError`), `:265` (bare `except Exception`), `:274` (`ExtractionError`), `:277`
>   (`DownloadError`) and `:290` (`unexpected_error_in_batch_download`). All eight call
>   `_finish(...)` **before** returning or re-raising, so the only way `stop()` can observe a
>   task with no terminal status is a task cancelled before its first line runs — and such a
>   task never reaches `reporter.start_task` at `:230`. `stop()` itself is reached only from
>   the `finally` at `batch_downloader.py:388-392`, which runs after
>   `asyncio.gather(..., return_exceptions=True)` at `:375`. The reachability claim holds as
>   filed.
> - **Severity:** LOW, `UNVERIFIED` through the binary, correctly marked. The terminal form
>   of the §9 LOW row is *"A per-run instance that discards a collected artefact on exit that
>   the user could otherwise inspect."* The reference at `cli-reference.md:158` promises
>   precisely the opposite of the finding's premise — *"A finished download becomes a status
>   line that stays on screen and scrolls up with the display"* — which is the accurate
>   record of what happens on every reachable path. The report's framing of the tension
>   (decision recorded, versus decision encoded) is right.
> - **Consequence of the answer, stated once:** the finding's value is that the guarantee is
>   contingent on eight separate call sites rather than on one. That is a maintenance
>   property, not a runtime defect on the current tree, and the finding is filed and
>   classified accordingly. The phase required this row to exist even though the answer is
>   "no", and required that the answer be the row and not a finding; the row is present and
>   answered, and nothing was manufactured to fill it.

| Field | Value |
|-------|-------|
| **ID** | OUT-012 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/progress_display.py` |
| **Classification** | advisory |

**Description:** `stop()` clears the task map (`progress_display.py:177`) without writing a terminal status for any task that had begun work, and the display is built with `transient=False` (`progress_display.py:323`), so the last frame stays on the terminal after output returns to normal.

**Evidence (in process, R11; exact input recorded: file-backed `Console(file=StringIO(), force_terminal=True, width=90, no_color=True)`, `enabled=True`; `start_task(0,"Alpha Title")`, `set_title(0,"Alpha")`, `update(0,50,100)`, `finish_task(0,SUCCESS)`, `start_task(1,"Beta Title")`, `update(1,10,100)`, then `stop()`).** The frame left on screen:

```
[✓] video_0: Alpha done ---------------------------------------- 100% ? 0:00:00
    video_1: Beta Title ----                                      10% ? -:--:--
```

`video_1` carries no status marker and no outcome word. `_StatusColumn.render` returns `Text("")` while `task.fields["status"]` is `None` (`progress_display.py:54-58`), and nothing in `stop()` sets it. A caller looking at that terminal sees a download that is 10% done and still going, on a process that has already finished and returned to normal output.

**Through the binary: `UNVERIFIED`, and not reachable through the product today.** `stop()` runs only in the `finally` of `_run_batch_with_progress` (`batch_downloader.py:388-392`), after `asyncio.gather(*tasks, return_exceptions=True)` (`:375`), and every path out of `_download_single` calls `_finish` before returning or re-raising — including the cancellation path (`:249-260`), which calls `_finish(ProgressStatus.CANCELLED)` before re-raising. A task cancelled before its body first runs never calls `start_task` and so never opens a line. No real terminal exists on the declared platform, so the on-screen consequence was not observed; the frame above is from the in-process harness only. This is a robustness gap in the teardown, not a live defect, and it is filed because the check exists and the answer is "no".

**Recommendation:** In `stop()`, before clearing the task map, give every task that is not yet terminal a terminal state (cancelled is the truthful one, since the batch is over) so no line is left mid-flight. If the display is never actually stopped with work in flight, this costs nothing; if a future change makes it possible, the terminal is already the right answer.

---

### OUT-013: ~~The shutdown state is never reset, so a later ordinary failure in the same process is reported as a user cancellation~~ [REJECTED]

> **Rejection reason:** The structural fact is true and the claimed consequence is not reachable
> through any shipped path, so the finding fails on its claim rather than on its citation.
>
> **The structural fact is confirmed and is not what is rejected.** `get_shutdown_event`
> (`downloader_throttle.py:31-43`) returns a `ContextVar` default and nothing in `src/` ever
> clears it — a repository-wide search for `shutdown_event.clear`, `_shutdown_event_ctx` and
> `.clear()` over the event returns no call site. Every anchor in the finding is exact
> (`batch_downloader.py:152-156`, `:317`, `:458-460`; the shutdown check is `cli.py:206-207`
>
> **The consequence does not reproduce, because the state cannot escape the coroutine that sets
> it.** `get_shutdown_event()` is a `ContextVar` accessor. A signal is handled by
> `_handle_signal` (`signal_handlers.py:29-33`), which closes over the event obtained inside
> the `asyncio` task that `asyncio.run` created; `asyncio.Task` copies the caller's context, so
> a `set()` performed inside the task never propagates back out. Three cases were driven
> through the production `run_batch` on this commit:
>
> ```
> CASE A  a stop raised inside the first run's own task context (what a signal does)
>   run 1  exit 130   account: "…: cancelled",  Cancelled: 1
>   get_shutdown_event().is_set() in the CALLER's context after the run -> False
>   run 2  (ordinary failing transfer, no reset)  exit 1   account: "…: failed",  Failed: 1
> CASE B  event pre-set in the CALLER's context before the run — no shipped code does this
>   exit 130   account: "…: cancelled",  Cancelled: 1,  Failed: 0
>            + "Interrupted by user: any partial segments already downloaded were preserved
>               for resume; re-run this command to resume them."
> CASE C  event cleared, then an ordinary run
>   exit 1   account: "…: failed",  Failed: 1
> ```
>
> Case A is the shipped path, and it is exactly the behaviour the finding says cannot happen:
> the second run reports the failure as a failure. The misclassification in Case B is real and
> is the finding's described consequence, but it is reachable **only** when a caller sets the
> ContextVar in its own context before calling in — which is what the source report's harness
> did, and what its own note concedes: *"the harness had to clear the event by hand between
> cases to get a clean reading."* The harness held the state; the product does not.
>
> **Reachability, independently.** The phase's declared platform executes one command per
> process, so a second unit of work in the same process requires an embedding caller, not the
> CLI. And the measurement above shows such a caller cannot reach it either, because
> `asyncio.run` discards the task's context on return.
>
> **Why rejected rather than demoted.** A severity is composed only for a finding whose claim
> survives. The claim is *"an ordinary failure after a stop in one process is reported as a
> user cancellation on 130"*, and on this commit it is not. A non-reproducing subject is
> recorded as a non-reproduction with the exact inputs recorded, never as a clean bill of
> health — which is what this reason is.
>
> **What is retained, so a later run does not re-derive it.** The recommendation (clear the
> event at the start of each unit of work) is harmless and remains defensible as hardening:
> the state would become observable across two `asyncio.run` calls if any future code set the
> ContextVar outside the task — from a caller-level signal handler, from a change that hoists
> `setup_signal_handlers()` out of the coroutine, or from any path that abandons the task's
> context copy. It is recorded as advisory, not as a defect.
>
> **On the `CON-008` question, answered separately:** this is **not** a duplicate of `CON-008`
> (phase 04, MEDIUM). `CON-008` is about `segment_downloader.py:562-570` absorbing a
> `CancelledError` and logging `download_cancelled reason="shutdown_requested"` whether or not
> the stop state was set — a swallowed cancellation with a false reason in a log record. This
> is a process-global stop state with no reset. Different mechanisms, different surfaces,
> different fixes; `CON-008` remains valid and is unaffected by this rejection.

| Field | Value |
|-------|-------|
| **ID** | OUT-013 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** `get_shutdown_event()` memoises one `asyncio.Event` per context (`downloader_throttle.py:26-43`) and **nothing in `src/` ever clears it** — a search for `shutdown_event.clear` returns no production call site. Two outcome translations consult it: `_classify_download_result` (`batch_downloader.py:152-156`) and the single command's cancellation check (`cli.py:188-189`). Once a stop has been observed in a process, every later item in that process that returns no file is classified as `cancelled` rather than `failed`.

**Evidence (in process; two `run_batch` invocations in one process, the second with an ordinary failing transfer and no reset in between).** First invocation, a stop: returned **130**, account `Cancelled: 1` plus the interruption note. Second invocation, an ordinary failure with the event still set (the harness printed `shutdown_event still set: True`):

```
{"case": "STEP2_FAILURE_AFTER_STOP_IN_SAME_PROCESS", "returned": 130}
https://vkvideo.ru/video-1_1: cancelled


Download Summary:
  Total connections: 1
  Peak concurrent videos: 0
  Successful: 0
  Failed: 0
  Cancelled: 1
  Interrupted by user: any partial segments already downloaded were preserved for resume; re-run this command to resume them.
```

A transfer that produced no file and was never interrupted is reported to the caller as a **user cancellation**, on the cancellation status, with `Failed: 0` — and the account additionally asserts that partial segments were preserved, which for this run is a claim about residue the batch layer never measured (`batch_downloader.py:458-460`).

**Reachability, stated plainly:** the shipped CLI runs one command per process, so this consequence was **not** observed through the binary; it is an in-process observation, and it is the same translation the CLI's own single-command path uses at `cli.py:188`. Any in-process caller — an embedding application, a test harness driving `run_batch` twice, or the future re-entry this ContextVar design implies — gets the wrong outcome. This phase's R2 harness had to clear the event by hand between cases to get a clean reading, which is the same trap.

Cross-referenced, not re-filed: cancellation being absorbed and logged as a shutdown that never happened is **CON-008** (phase 04), and the derivation of shutdown state from a signal is phase 04's. What is filed here is the translation and the fact that the state has no reset — the part `## 7` assigns to this phase.

**Recommendation:** Reset the event at the start of each unit of work rather than relying on it never having been set: clear it in `_run_batch_with_progress` before the first task is created (`batch_downloader.py:317`) and in `cli.py`'s `_download` before `download_video` is awaited, so a second run in a process begins from a known state. The derivation of the state itself stays phase 04's.

---

### OUT-014: `--cookie-source file` is an option value the product's own reference promises and the argument layer rejects

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** MEDIUM (retained)
> - **Type:** SPEC-DEVIATION (retained) · **Classification:** mandatory (retained)
> - **Detail:** Reproduced through the binary, `download --cookie-source file <url>`:
>   **status 2**, stdout 0 bytes, and stderr verbatim identical to the source report —
>   `Invalid value for '--cookie-source' / '-c': 'file' is not one of 'none', 'browser'.` The
>   enum side is exact: `CookieSource` (`enums.py:45-50`) declares exactly two members,
>   `NONE = "none"` and `BROWSER = "browser"` at `:48-49`, and the Typer option annotates the
>   enum, so Click derives its accepted set from the members. The reference side is exact:
>   both option tables promise the third value — `cli-reference.md:67` and `:128`
>   (`Cookie strategy: none, browser, or file`) and the value's own row at `:212`
>   (`Load cookies from external file (future enhancement)`).
> - **Ownership test, which is what decides this one.** The promise is not merely
>   unimplemented; its **member cannot be constructed**, so the promise does not survive
>   replacing the command line — a caller who follows it cannot proceed by any change of
>   invocation. That is the phase's §7 test (*"The token ... does not survive a caller
>   replacing the command line ... that is the argument layer's, and the reference is this
>   phase's"*), and it is met. The reference is phase 08's, which is why this is filed here
>   and not deferred.
> - **Anchor correction (stands):** `enums.py:45-48` → the class spans `45-50` and its members
>   are at `48-49`. `enums.py` carries no uncommitted edit, so this is a real one-line drift.
> - **Note on the reference's own hedge.** `(future enhancement)` at `:212` tells a reader the
>   value is not available, which is true and is what the reference should say. It does not
>   rescue the finding: the two option tables — what a caller reads before typing — list `file`
>   as an accepted value with no marker, and `future enhancement` is exactly the wording that
>   belongs in those two rows instead. The fix is two table rows plus keeping `:212`.

| Field | Value |
|-------|-------|
| **ID** | OUT-014 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/99-reference/cli-reference.md`, `src/vkdownloader/models/enums.py` |
| **Classification** | mandatory |

**Description:** `docs/99-reference/cli-reference.md:67` and `:128` list `--cookie-source` as taking `none`, `browser`, **or `file`**, and `:212` gives `file` its own row: *"Load cookies from external file (future enhancement)"*. The product has no such value. `CookieSource` has exactly two members (`models/enums.py:45-48`) and the captured `--help` for both commands shows `[none|browser]`.

**Evidence (through the binary; help captured to a file per command, and the value supplied):**

```
> vkdownloader download --cookie-source file https://vkvideo.ru/video-1_1
status 2, stderr only:
  | Invalid value for '--cookie-source' / '-c': 'file' is not one of 'none',   |
  | 'browser'.                                                                  |
```

The parser's own recovery message lists only the two values that exist and does not say that `file` is a planned value rather than a typo. A user following the reference gets a usage error for a value the reference documents.

**Ownership test, run and recorded:** does the finding survive replacing the command line with a direct call into the same function? **No.** `CookieSource.FILE` cannot be constructed — the member does not exist — so a programmatic caller cannot pass it either. The defect is therefore not in the model's typing or bound (phase 02's), it is in the **declared option contract**, which `## 7` assigns to this phase.

**Recommendation:** Pick one direction and make the reference match the code. Cheapest is documentation: mark `file` in `cli-reference.md:212` as not yet accepted, or remove it from the two option tables, so the reference stops promising a value the parser rejects. If the value is intended to ship, add `FILE = "file"` to `CookieSource` and the branch that loads it — but that is a feature, and the audit position is only that the two surfaces must not disagree today.

---

### OUT-015: Neither setting that governs what the process emits has an option

> **Validation Note:**
> - **Action:** validated
> - **Severity (re-derived):** LOW (retained)
> - **Type:** BEST-PRACTICE (retained) · **Classification:** advisory (retained)
> - **Detail:** Re-derived by enumerating the settings and the option surfaces rather than by
>   reading the recommendation. `Settings` declares exactly two fields that govern what the
>   process emits: `log_level` (`config.py:119-122`) and `log_file` (`:123-126`). Neither
>   reaches the caller as an option in either command — `download` carries `url`
>   (positional), `quality`, `output`, `method`, `cookie_source`, `ssl_verify` and
>   `max_retries`; `batch` carries `urls_file` (positional) plus the same six. Both settings
>   are reachable from the environment and from `.env` alone, and the only `typer.Option`
>   anywhere that names an environment variable is `max_retries`, whose reference row at
>   `cli-reference.md:124` says so. The asymmetry the finding reports — one option declaring
>   its env source and the other two silent — is real.
> - **Severity:** LOW, advisory. The phase's §9 LOW row *"A help-text omission with no
>   observed consequence"* is the nearest admissible shape, and this phase's own
>   `OUT-006`/`OUT-002` evidence demonstrates the consequence: a caller cannot turn on the log
>   file the reference's whole account section assumes, nor turn colour off at the source. The
>   §5(e) row — *"A setting that governs what the process emits, with no option that reaches
>   it, is a finding about the option surface"* — is what keeps this filed at all. Whether the
>   product should expose these two is a design decision the finding correctly leaves open.
> - **Anchor (the report's is right for `a335b2a`):** `log_level` is `config.py:121-124` and
>   `log_file` is `config.py:125-128`, so the cited range `config.py:121-128` is correct as
>   filed. The apparent drift is the uncommitted working-tree edit filed as `VAL-003`.
> - **See also:** `OUT-006` (colour decided with no option and no capability check);
>   `ENT-001` (phase 01, pre-sink records never reaching the configured file).

| Field | Value |
|-------|-------|
| **ID** | OUT-015 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** `log_level` and `log_file` (`config.py:121-128`) decide the renderer, the sink and the verbosity of everything the process emits. Neither is reachable from the command line: the captured help for both commands lists `--quality`, `--output`, `--method`, `--cookie-source`, `--ssl-verify/--no-ssl-verify` and `--max-retries`, and nothing else. The only routes are `VKDOWNLOADER_LOG_LEVEL` / `VKDOWNLOADER_LOG_FILE` and the `.env` file.

**Evidence (through the binary; help for both commands captured to files and diffed; the two settings traced to their consumers in this phase's own runs).** Both settings were exercised only by environment: `VKDOWNLOADER_LOG_FILE` alone switched the sink from the stderr `StreamHandler` to a `FileHandler` and the renderer from `ConsoleRenderer` to `JSONRenderer` (`OUT-002`, `OUT-006`), and no argument shape reaches either. The asymmetry is visible inside the help itself: `--cookie-source` and `--ssl-verify` both state their effective default *and* name their environment source, while `--max-retries` states neither (`OUT-005`), so the two settings that govern output are also the two a user is least likely to know exist.

**Recommendation:** Add `--log-level` as a choice option (`DEBUG/INFO/WARNING/ERROR/CRITICAL`, matching `LogLevel`) and, if a per-run log destination is wanted, `--log-file`. `--log-level` alone closes the asymmetry with the two options that already document their env source, is one `typer.Option` plus one key in `_SettingsOverrides`, and makes the per-run debugging that `OUT-006` and `OUT-002` both need available without editing a file on disk. If neither option is wanted deliberately, the help text for the settings that do have options should say plainly that log configuration is environment-only, so the absence is a stated decision rather than a gap.

---

### OUT-016: An `OSError` anywhere in the fallback block is reported to the caller as `failed_to_refresh_token`

> **Validation Note:**
> - **Action:** reclassified
> - **Severity (re-derived):** LOW (was MEDIUM)
> - **Type:** `RUNTIME-ERROR` → **`SPEC-DEVIATION`** · **Classification:** mandatory (retained)
> - **Detail:** The misnaming is confirmed and is structurally certain. The handler at
>   `ytdlp_downloader.py:547-552` is `except (ExtractionError, OSError) as e:` and emits
>   `logger.warning("failed_to_refresh_token", url=..., error=str(e))` for both. The guarded
>   span reaches far past any token refresh: `output_file.unlink()` at `:531` and the entire
>   `download_hls_with_resume(...)` call at `:533-546` — a filesystem call and a segment
>   download. An `OSError` from the unlink (the file open elsewhere, a read-only directory, a
>   partially written handle) is therefore published under a token-refresh name. The source
>   report's trigger note (`no filesystem fault was produced`) is honest and is retained.
> - **Why the Type is reclassified.** The phase's §9 reserves `RUNTIME-ERROR` for *"anything
>   observed failing at runtime, including a run that terminates by an undeclared path"*, and
>   §12 adds that a finding whose runtime consequence was not observed *"is never given an
>   observed severity"*. Nothing was observed failing here, and the finding does not claim
>   otherwise — it marks the trigger `UNVERIFIED` itself. The correct label is
>   `SPEC-DEVIATION`: the handler publishes a cause it does not test for, against the
>   product's own machine-readable vocabulary, whose `ErrorCode` enum (`enums.py:52-67`) and
>   docstring state that each domain exception carries one code *"so that log aggregators and
>   users can filter and group by specific failure modes in structured (JSON) logs"*. An
>   event name that does not identify the failure mode defeats that purpose.
> - **Why the severity is LOW, and one consequence statement in the source report is wrong.**
>   The source report asserts the record surfaces *"or the `url: failed_to_refresh_token` line
>   the batch account prints for a per-item outcome"*. It does not. The handler returns `None`
>   (`:561`); `_classify_download_result(None)` yields `ProgressStatus.FAILED.value`, the
>   literal string `failed`; and `_print_batch_summary` prints `f"    - {url}: {status}"` at
>   `batch_downloader.py:455`. Re-derived through the binary on a 3-URL `batch`, the account
>   printed `…: extraction_error` and `…: failed` — **never an event name**. The consequence is
>   confined to one `logger.warning` record, whose text is nonetheless what an operator greps
>   for. No test constrains the name. The taxonomy has no exact MEDIUM row for a mislabelled
>   record whose trigger is unobserved; LOW is the nearest admissible bucket, and the residual
>   diagnostic cost is real but bounded and is recorded here rather than inflated.
> - **Anchor correction (stands):** `ytdlp_downloader.py:545-551` → the handler is at `:547-552`.
>   `ytdlp_downloader.py` carries no uncommitted edit, so this is a real two-line drift,
>   independent of `VAL-003`. The `output_file.unlink()` anchor `:531` is exact.
> - **Not previously owned — the phase-07 handoff is legitimate.** Phase 07's *Not filed here*
>   table routes this explicitly: *"`failed_to_refresh_token` as a mislabel ... → phase 08"*
>   and *"[t]he precise missing-segment error being swallowed and relabelled by
>   `ytdlp_downloader.py:547` — is a diagnostics defect and is phase 08's."* Phase 07's own
>   anchor for the same handler is `:547`/`:548-552` — the **correct** real line numbers,
>   which independently confirms that the drift in this report is a phase-08 artefact and not
>   a change in the tree.
> - **See also:** `ART-002` (phase 07, the title-character defect on the same path — the
>   origin of the string, not the label); `SEC-007` (phase 06, error text in log records).

| Field | Value |
|-------|-------|
| **ID** | OUT-016 |
| **Severity** | LOW *(re-derived by the validation phase; filed MEDIUM)* |
| **Type** | SPEC-DEVIATION *(re-derived; filed RUNTIME-ERROR)* |
| **Affected Modules** | `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | mandatory |

**Routed here by phase 07**, which found the site and left the name to this phase.

**Description:** The yt-dlp fallback's handler names one cause and catches two (`ytdlp_downloader.py:545-551`):

```
except (ExtractionError, OSError) as e:
    logger.warning("failed_to_refresh_token", url=..., error=str(e))
```

The block it guards spans the partial-file removal at `:531` (`output_file.unlink()`) and the entire segment download it hands off to. Every `OSError` raised anywhere in that span — the file locked by another process, the volume full, a path the platform refuses, a read-only directory — is published to the caller under the name `failed_to_refresh_token`. A caller reading the record, or the `url: failed_to_refresh_token` line the batch account prints for a per-item outcome, is told to refresh an authentication token when the disk rejected a write.

**Evidence (read from the handler; the trigger is `UNVERIFIED` — reproducing it needs a real filesystem fault on the ffmpeg-fallback path, and this phase has no fault injector and must not build one):** the handler's own `except` clause admits `OSError`, and the only call inside its span that can raise one on this host is `output_file.unlink()` at `:531`, reached from the same span. `tests/` contains no test for this handler (searched: `failed_to_refresh_token` does not appear in any test file), so no oracle constrains the name.

**Recommendation:** Split the handler. Keep `ExtractionError` under `failed_to_refresh_token` and give `OSError` its own event name naming the filesystem cause, so the two classes stay distinguishable to the caller. The event name is a `StrEnum` member in this codebase's own convention, so this is one new member plus one extra `except` clause. Then add a test per branch so the two cannot collapse again.

---

### OUT-017: ~~The quality-error label glues a `p` onto a non-numeric value and offers a value the argument layer rejects~~ [REJECTED]

> **Rejection reason:** Rejected on two independent grounds, either of which is sufficient:
> the substance is already owned by a validated higher-severity finding in another phase, and
> the phase that filed it forbids manufacturing this check.
>
> **Ground 1 — already owned, and substantively contained.** `NET-008` (phase 03, HIGH) states
> the whole of it, and its evidence section carries this finding's evidence verbatim: *"The
> label it attaches, `"best"`, and the label enumeration produces for a record with no height,
> `"unknown"` (`extractor.py:63`), are **not members** of `QualityEnum`
> (`models/enums.py:6-17`), so neither can be re-requested"*; `list_available_qualities ->
> ['1080p','720p','480p','360p','unknown']`; and
> `QualityNotAvailableError: ... Available: ['1080p','720p','480p','unknown','unknown','360p']`,
> with the note that the alternatives list repeats `'unknown'` and that pasting a label back
> raises `ValueError: 'unknownp' is not a valid QualityEnum`. The source code is identical and
> was re-read here: `extractor.py:63`
> `quality=f"{height}p" if height else "unknown"`, and the CLI renders it at `cli.py:253`
> (`f"\nRequested quality '{requested}p' is not available…"`) and lists it at `cli.py:256`.
> The one element `NET-008` does not state in these words — the `+ 'p'` concatenation applied
> to a non-numeric label — is a rendering detail inside the defect it already names, and belongs
> in `NET-008`'s scope rather than in a second queue at a second severity.
>
> **Ground 2 — this phase's handbook forbids the check outright.** The phase-08 preamble,
> binding rule 5: *"The seam between `03` and `08` over a quality label is carried by `03` and
> is not carried into this file; this phase's own half of it is checked and yields nothing,
> and **a check invented to fill the `03` half here is itself a defect of this phase**."*
> §7 says the same in the row that names it: *"A quality label a selection produced, and its
> appearance in an error's list of alternatives → `03`, and that half is not carried. This
> phase's own half of it yields nothing; **no check, no row and no finding exist for it in
> this file, and none is to be manufactured to fill an in-scope bullet that names it**."*
> The routed handoff does not override this: the phase-03 route that carried the subject into
> this file is precisely the cross-phase route §7 excludes, and the handbook governs this
> phase's own subjects. Re-derivation on a rejected finding never happens, so the two lines
> above are the record of what was checked and where it lives.
>
> **What is retained, so a later run does not re-derive it.** The defect is real and
> unaddressed; it is `NET-008`'s to carry, at HIGH. If `NET-008` is ever closed, the `'p'`
> concatenation on a non-numeric label is the residual that must not be closed with it, and it
> is named here for that purpose.
>
> - **Anchors (the report's are right for `a335b2a`; recorded because the reject is not a
>   dismissal of the numbers):** the quality label is produced at `extractor.py:63` and rendered
>   at `cli.py:234`, the `typer.echo(` that opens the not-available message, with
>   `requested = e.requested` at `cli.py:225`. Verified against
>   `git show a335b2a:src/vkdownloader/cli.py`.

| Field | Value |
|-------|-------|
| **ID** | OUT-017 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | mandatory |

**Routed here by phase 03** (NET-008), which owns the selection defect and left the rendering here.

**Description:** `Stream.quality` is `f"{height}p" if height else "unknown"` (`extractor.py:63`), so `"unknown"` is a quality value the product itself produces and `unknown` is not a `QualityEnum` member. The single command's handler renders the requested quality with a hard-coded suffix (`cli.py:234`):

```
f"Requested quality '{requested}p' is not available for this video."
```

`requested` comes straight from the exception (`cli.py:225`). When it is not a bare number, the label the caller reads is malformed, and the recovery list on the next line offers a value that the argument layer will reject if pasted back.

**Evidence (in process; the two `QualityNotAvailableError` shapes rendered by the real handler, verbatim, both status 1):**

| `requested` / `available` | Rendered to the caller |
|---|---|
| `"unknown"` / `["unknown", "720p"]` | `Requested quality 'unknownp' is not available for this video.`<br>`Available qualities: unknown, 720p` |
| `"720"` / `["360p"]` (control) | `Requested quality '720p' is not available for this video.`<br>`Available qualities: 360p` |

`'unknownp'` is not a quality; `unknown` in the alternatives list is a value `--quality` refuses. Both halves are a rendering defect, and the rendering rule is exercised in process on the product's own handler rather than asserted from the source.

**Through the binary: `UNVERIFIED`.** Reaching it needs a real video with at least one stream carrying no height, which this host cannot produce. The rendering rule is confirmed; the input that supplies `requested="unknown"` is read from the product's own `extractor.py:63` and phase 03's NET-008 already established that `unknown` reaches `available_qualities` and the exception's alternatives.

**Recommendation:** Render the requested value verbatim rather than appending a suffix, and normalise the alternatives to the same form the `--quality` option accepts so a pasted-back value is accepted (`unknown` should be dropped from the list, or renamed to a value the enum holds). This is the same class the reference promises at `cli-reference.md:87` — "every value printed in the parser's own error message is accepted when pasted back into the command line" — extended to the product's own error messages, which today it does not cover.

---

### VAL-001: The gate that decides whether a phase's findings are validated keys on three terms that no pipeline document defines

> **Filed by:** the validation phase, against an audit input. `VAL-` is reserved for defects
> in the audit's own documents; it is never used for a product-code finding.

| Field | Value |
|-------|-------|
| **ID** | VAL-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/audit-multi-phase.md` |
| **Classification** | mandatory |

**Description:** `.kilo/commands/audit/audit-multi-phase.md:86` reads:

> `### 2.4 Launch Validator (skip for Phase 99)`
> `Launch the Validator **only** when Findings are **not trivial** ands relate to **significant code changes** or **architecture modifications**.`
> `In all other cases — skip.`

Three terms carry the whole decision — *not trivial*, *significant code changes*,
*architecture modifications* — and **none of them is defined anywhere in the pipeline**. A
literal search for all three across every file in `.kilo/commands/audit/` (including
`phases/`, which is 12 handbooks plus this validation phase) and
`.ai/audit/templates/` returns **no match other than this sentence itself**. No document
supplies a threshold, a quantity, or a procedure; no code implements the condition, because
`audit-multi-phase.md` is a prompt, not a program. The gate is therefore not evaluable, and
whether a phase is validated is decided by an unrecorded judgement.

**Consequence, observed.** The run's closing output at `audit-multi-phase.md:118` reports
`Validated findings: {N} total` followed by a per-severity breakdown, and §3.3 records that
this is *"the one class of defect a later run cannot catch"* and that it is *"checkable only
here."* It is not checkable, because the predicate that produced the number is unrecorded. The
condition is not inert today — phases 01 through 07 all have validation artifacts, so the gate
did fire in practice — but **the run does not record why**, and the artefact the coverage claim
counts is one an unevaluable gate produced.

**Evidence (block (h), "Gate evaluability").** The term each gate keys on is `trivial` /
`significant code changes` / `architecture modifications`; its definition is **absent**; the
instruction stands at `audit-multi-phase.md:86`.

**Recommendation:** either replace the three adjectives with a rule the orchestrator can state
in one line — for example, validate every phase that wrote a findings file containing at least
one finding of severity HIGH or above, and record the decision in the run's output — or drop
the gate and validate every phase, which is what has in fact happened for 01–08. The second is
cheaper and removes the unrecorded judgement. A run whose closing output claims coverage must be
able to name the predicate that produced it.

---

### VAL-002: The report format names an executor the pipeline cannot launch, and the validator's own role file omits one of the four finding types

| Field | Value |
|-------|-------|
| **ID** | VAL-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.ai/audit/templates/audit-findings.md`, `.kilo/agents/validator.md` |
| **Classification** | mandatory |

**Description:** two related disagreements between the report format (the authority) and the
documents that consume it.

1. **A role that does not exist.** `.ai/audit/templates/audit-findings.md:4` declares
   `agent: audit-executor` in its front matter and `:10` writes `**Executor:** audit-executor`
   into every report it produces. The orchestrator launches
   `agent="auditor"` (`.kilo/commands/audit/audit-multi-phase.md:75`), and the live roster in
   `.kilo/agents/` is `analyst`, `auditor`, `docs-specialist`, `implementor`, `planner`,
   `researcher`, `tech-lead`, `test-engineer`, `validator` — **nine roles, none of them
   `audit-executor`**. Every findings file in the corpus therefore carries an executor label
   that no role in this project can produce, and the seven validation artifacts inherit it
   through the template's header.
2. **A vocabulary one document defines and another omits.** `audit-findings.md:68` fixes
   `type` to `SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, `RUNTIME-ERROR`. The validator
   role file lists **three**: `SPEC-DEVIATION`, `BEST-PRACTICE`, `DOC-UPDATE`, at
   `.kilo/agents/validator.md:243-245` and again at `:356-358`. `RUNTIME-ERROR` is absent from
   both.

**Consequence, observed.** Three of the seventeen findings under adjudication — `OUT-001`
(HIGH, re-derived CRITICAL), `OUT-013` and `OUT-016` — are typed `RUNTIME-ERROR`. Under the
validator role file's own list they are **illegal labels**, and a validator working from that
file would have grounds to reclassify them away, the HIGH one included. This phase did not,
because the validation handbook's block (d) states that all four labels are in scope *"and
that a finding describing something seen to fail is checked against the runtime-failure label
first. Never reclassified away because a role file omits the label."* That rule exists
precisely because of this gap, which is how the gap is observable at all. The `audit-executor`
label meanwhile makes the provenance of every artifact in the corpus unverifiable: nothing in
the tree can launch it.

**Recommendation:** the format is the authority. Change `.kilo/agents/validator.md:243-245`
and `:356-358` to list all four labels, and change `audit-findings.md:4` and `:10` from
`audit-executor` to the role the orchestrator actually launches. Both are one-line edits; the
first removes a rule that would otherwise strip the type from the highest-severity finding in
this phase on every future run.

---

### VAL-003: The pipeline pins a commit in the report header but records nothing about the tree it read, and the tree is not the pinned commit

> **Filed by:** the validation phase. **This finding replaces an earlier `VAL-003` of the same
> number, which was withdrawn as a false positive and whose text is retained immediately below
> the findings table, so a later run does not re-derive it.**

| Field | Value |
|-------|-------|
| **ID** | VAL-003 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.ai/audit/templates/audit-findings.md`, `.kilo/commands/audit/audit-multi-phase.md` |
| **Classification** | mandatory |

**Description:** the report format gives every phase one provenance field — the commit it
measured (`audit-findings.md` and every findings file carry
`**Commit measured:** a335b2a2e0270414f9f2923d1b4a8e038a8998b5`) — and the pipeline gives the
executor and the validator no other handle on what they actually read. Both read the **working
directory**: `audit-multi-phase.md:63` names an output *path*, `:75` and `:97` launch agents
with no tree state, and no command in `.kilo/commands/audit/` checks for a dirty tree, records
one, or refuses to run against one.

**Consequence, observed — on this run, to this phase.** `src/vkdownloader/cli.py` and
`src/vkdownloader/config.py` were **clean** at the start of this validation (the phase-08
report's own provenance check, `git status --porcelain -- src docs tests`, returned nothing) and
carry **uncommitted modifications** now. `git diff --stat` against `a335b2a`:

```
 src/vkdownloader/cli.py    | 24 +++++++++++++++++++++---
 src/vkdownloader/config.py | 10 ----------
```

The committed files are 365 and 382 lines; the working copies are 383 and 372. Nothing in the
run noticed. The pipeline's own header — which asserts the tree is clean — is the only thing
that would have, and it was consulted by hand, not enforced.

**The failure this produces, demonstrated rather than predicted.** The uncommitted edit moves the
unknown-`VKDOWNLOADER_*` notice out of a `logger.warning("unknown_env_var_ignored", …)` record
in `config.py` and into a `typer.echo(..., err=True)` loop in `cli.py`, deleting 10 lines of
`config.py` and adding 18 to `cli.py`. Against the modified tree, **every one of the report's 27
`cli.py` and `config.py` anchors resolves to the wrong line** — `config.py:373` does not exist,
because the file is 372 lines; `cli.py:193` is three lines of argument plumbing instead of the
traceback origin; the seven `raise typer.Exit(code=1)` sites the report cites at
`206, 213, 219, 222, 239, 242, 248` sit at `224, 231, 237, 240, 257, 260, 266`. A validator or
auditor working on the modified tree concludes the report is wrong, exactly as this phase
initially did: it filed `VAL-003` as a systematic line-numbering defect in the report before
checking the committed file. **The report was right and the tree had moved.** The false finding
was withdrawn only because the committed version was extracted with `git show a335b2a:<path>`
and the anchors re-read against it — where `110-116` is the four-step bootstrap, `193` is the
traceback origin, `245-248` is the `except Exception` handler, `358-366` is
`logging.basicConfig`, `373` is `format_exc_info` and `375-377` is the renderer selection, all
as filed.

**Recommendation:** record tree state, not only a commit, and refuse to run against a dirty
one. Concretely, in `audit-multi-phase.md` §1, add `git status --porcelain` and
`git rev-parse HEAD` to the `{BASE_CONTEXT}` it builds, and add a line to the per-phase output
recording both — so the report's `Commit measured` field is either true or visibly qualified.
In the report format, replace the single commit line with a two-line provenance block (commit,
plus working-tree state, plus "clean"/"dirty with these paths"). The gate should be a hard stop
rather than a note: a finding set is only useful if it can be re-verified against the tree it
claims, and on this commit it cannot be, silently.

### Withdrawn `VAL-003` (retained, not deleted)

The first `VAL-003` this phase wrote alleged that *"every `file:line` anchor in this report is
wrong by a constant per-file offset"* — `+18` for `cli.py`, `+10` for `config.py` — and
attributed it to a lossy reader in the report's own reading step, citing the phase-01 `ENT-012`
drift and phase 07's correct `ytdlp_downloader.py` anchors as corroboration. **It was wrong, and
it is withdrawn.** The per-file offsets it reported were real; their cause was not a reader. They
are the difference between the committed files and the working-tree edits, in the opposite
direction, and every one of the 27 anchors it called wrong is right for the commit the report
names. Two further parts of it were also wrong: the phase-01 `ENT-012` drift is a *separate*
per-report artefact, not evidence of a shared one, and phase 07's correct anchors are evidence
**against** a tree-change explanation, which is what the withdrawn note overlooked. Nothing in
the other twenty-one findings depends on it; the `+18`/`+10` "corrections" carried in the
individual Validation Notes have been removed and replaced with the correct statement, and the
small corrections that do stand — `enums.py:78` → `:79` and
`ytdlp_downloader.py:545-551` → `:547-552` — are in files the working-tree edit never touched.
The incident is itself the evidence for this finding.

---

### VAL-004: Two commands read a project-instructions file as mandatory base context, and the repository root holds none

| Field | Value |
|-------|-------|
| **ID** | VAL-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/audit-multi-phase.md`, `.kilo/commands/audit/audit-refine.md` |
| **Classification** | mandatory |

**Description:** both commands that assemble the base context every phase receives read the
same two files. `.kilo/commands/audit/audit-multi-phase.md:42-44`:

> `Read .ai/context/commands.md for verification commands.`
> `Read AGENTS.md for project guidelines.`
> `List documentation structure from docs/ folder.`

and `.kilo/commands/audit/audit-refine.md:18-20` repeats it verbatim. **There is no `AGENTS.md`
at the repository root.** `Test-Path AGENTS.md` returns `False`. The project's rules live in
`.kilo/rules/project.md` (the fifteen numbered rules) and `.kilo/rules/commands.md`; the file
`.ai/context/commands.md`, which the same line names and which **does** exist, is the only one of
the three that resolves.

**Consequence, observed.** The base context handed to every phase is assembled from three
sources; one of them is absent and the instruction does not say what to do about it, so the
contents of the two real rule files reach each phase only if the agent happens to find them. The
project's own rule set — English only, production code is king, strict separation of concerns,
single responsibility, StrEnum for constants, Pydantic v2, no `print()`, small focused modules
— is the material that decides whether a phase files at all. Half the declared context is
missing and the run reports nothing about the miss. The same two commands also have no rule about
`kilo.json`, `kilo.local.json` or the phase's own report template, which they do reference.

**Recommendation:** change both files to name the paths that exist —
`.kilo/rules/project.md` and `.kilo/rules/commands.md` — or point them at the directory
(`.kilo/rules/`) and let the agent read it, so a future move does not re-break the instruction.
Whichever is chosen, the instruction should say to report an absent file rather than to continue
silently.

---

### VAL-005: The orphaned-file census reaches the audit's own catalogue, the phase directory, and a stale copy of a previous audit generation

| Field | Value |
|-------|-------|
| **ID** | VAL-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.kilo/commands/audit/audit-orphaned.md` |
| **Classification** | mandatory |

**Description:** `.kilo/commands/audit/audit-orphaned.md:47` instructs
`Identify files unreachable from known entry points.` and `:82` writes the report to
`.ai/audit/orphaned-files/report.md`. Neither line, nor any other in the file, exempts anything
from that census.

**Consequence, observed.** Three groups of files in this repository are unreachable from
`src/vkdownloader/cli.py` and every other production entry point, and none of them is
exempt:

- **The audit's own catalogue** — `.ai/audit/**` and `.kilo/commands/audit/**` are read by
  agents, never imported. A reachability census run as written proposes deleting the entire
  audit corpus.
- **The phase directory** — `.kilo/commands/audit/phases/` holds twelve handbooks and
  `99-audit-validate.md`; none is imported or referenced from code.
- **A stale copy of a previous audit generation, in a worktree.** `.kilo/worktrees/southern-bandana/`
  contains `.ai/audit/` with a *different, superseded* phase set (`01-audit-cli`,
  `02-audit-config`, `03-audit-services`, `04-audit-security`, `05-audit-integrations`,
  `06-audit-data-flow`, `07-audit-tests`, `08-audit-quality`, `09-structural-quality`, plus its
  own `99-validation` and `templates`) and `.kilo/agents/` holding **twelve** role files
  including `analyst.md`, `implementor.md`, `planner.md`, `tech-lead.md`, `recovery-ingener.md`,
  `test-engineer.md`, `docs-specialist.md`, `implementor-orchestrator.md`, `audit-orchestrator.md`,
  `researcher.md` — a roster the live `.kilo/agents/` (nine files) does not match. The live
  corpus is `01-entry-architecture` … `08-cli-observability`; the worktree's is a different
  generation entirely.

That last item is the one that actually causes damage: the worktree copy is unreachable **and**
it holds a plausible-looking audit catalogue, so it is exactly the shape a high-confidence
"orphaned, no importers, review/delete" candidate takes. The phase-07 handoff table routes
residue questions to phase 11 for the same reason, and this phase's own validation handbook
states the rule for its own searches: *"Repository-wide searches exclude every worktree
directory. A stale copy of an earlier phase set is present and is not part of the catalogue."*
Nothing in `audit-orphaned.md` says it.

**Recommendation:** add an explicit exclusion list to `audit-orphaned.md` covering
`.ai/audit/**`, `.kilo/commands/audit/**`, `.kilo/agents/**`, every `**/.kilo/worktrees/**`
directory, `.git/**`, `.venv/**` and any build or cache directory. The census's own output
directory (`.ai/audit/orphaned-files/`) belongs on the list for the same reason. A census that
can propose deleting its own instructions is not a census of product code.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 9 |
| LOW | 7 |

**Harness variant per finding** — through the binary (two streams to two distinct files, status from the shell): OUT-001, OUT-002, OUT-003, OUT-004, OUT-005, OUT-006, OUT-007 (captured direction only; watched direction `UNVERIFIED`), OUT-008, OUT-014, OUT-015. In process only: OUT-010, OUT-011, OUT-012, OUT-013, OUT-017. Structural with the trigger `UNVERIFIED`: OUT-016. No finding is evidenced from a merged capture or from the test suite.

> **Summary corrected by the validation phase.** The table above is the source report's, kept as
> filed. The re-derived severities, after the CRITICAL correction on `OUT-001`, the LOW
> correction on `OUT-016`, and the removal of the two merged and two rejected findings, are in
> *Validation Summary* at the end of this artifact. The harness-variant row is also superseded
> in one respect: `OUT-003`, `OUT-004`, `OUT-013` and `OUT-017` were each re-derived by this
> phase, and the variants it used are recorded in their Validation Notes rather than here.

## Mandatory Fixes

| ID | Severity | One line |
|---|---|---|
| OUT-001 | HIGH | A preamble failure is reported with no declared message, on the same status as a failed download, and the reporting itself dies before a sink exists. |
| OUT-002 | MEDIUM | One exception is rendered twice, so a declared-JSON log file has 130 of 141 lines no parser reads. |
| OUT-003 | MEDIUM | A second `bind_correlation_id` inside `download_video` makes every batch failure record's join key match nothing. |
| OUT-004 | LOW | The terminal record is written after the binding is cleared, so it carries no join key. |
| OUT-005 | MEDIUM | `--max-retries` out of range returns `1` where every other usage error returns the documented `2`. |
| OUT-006 | MEDIUM | The console renderer gets no colour decision and no terminal condition, so every redirected run writes 45-187 ESC bytes. |
| OUT-007 | MEDIUM | The child's non-progress output is dropped with no destination exactly when the display is active. |
| OUT-008 | MEDIUM | `Total connections:` reports the number of videos. |
| OUT-013 | MEDIUM | The shutdown event is never cleared, so a later failure in the same process is reported as a cancellation. |
| OUT-014 | MEDIUM | The reference documents `--cookie-source file`; the argument layer rejects it. |
| OUT-016 | MEDIUM | Any `OSError` in the fallback block is reported as `failed_to_refresh_token`. |
| OUT-017 | MEDIUM | The quality label renders `'unknownp'` and offers `unknown`, a value the argument layer rejects. |
| VAL-001 | HIGH | The validator gate keys on three undefined terms, so the run's coverage claim has no recorded predicate. |
| VAL-002 | MEDIUM | The report format names a role that does not exist; the validator's role file omits `RUNTIME-ERROR`. |
| VAL-003 | HIGH | The pipeline pins a commit in the report header but reads a working directory, and the two are not the same tree. |
| VAL-004 | MEDIUM | Two commands read `AGENTS.md` as mandatory base context; the repository root holds no such file. |
| VAL-005 | MEDIUM | The orphaned-file census has no exclusion list and reaches the audit catalogue and a stale worktree copy. |

> **Corrections applied by the validation phase to this table.** `OUT-001` is **CRITICAL**, not
> HIGH. `OUT-013` and `OUT-017` are **removed** — rejected, with their claims and reasons kept in
> place so a later run does not re-derive them. `OUT-003` and `OUT-004` are **moved to
> `ENT-012`** (phase 01, HIGH): one root cause, one recommendation, one queue; they leave this
> list but their content stays in this file. `OUT-016` stays, at **LOW**, reclassified to
> `SPEC-DEVIATION`. The five `VAL-` rows are added by this phase and concern the audit's own
> documents, not the product.

## Advisory Recommendations

| ID | Severity | One line |
|---|---|---|
| OUT-009 | LOW | The aggregation rule is silent about `SKIPPED` and would count it as a failure. |
| OUT-010 | LOW | `isatty()` and `Console.is_terminal` decide one surface and can disagree; read the predicate once. |
| OUT-011 | LOW | `stop()` restores the borrowed handlers only if the display's teardown returns. |
| OUT-012 | LOW | A line that began work is left non-terminal when `stop()` runs with work in flight. |
| OUT-015 | LOW | `log_level` and `log_file` govern the process's own output and have no option. |

> **Advisory item retained from `OUT-013`, which is rejected.** Clearing the shutdown event at
> the start of each unit of work is not a fix for an observable defect on this commit — the state
> cannot become stale — but it is cheap and it is the thing that would have to be true before a
> future refactor could make the state leak. It is recorded here rather than dropped, because the
> rejection is about the claim and not about the recommendation.

## Doc Updates Needed

None filed. This phase files no `DOC-UPDATE` by construction: a documented claim about anything other than the command-line contract belongs to phase 09, and the example environment file's claims about the command line belong to phase 02. The three command-line-contract claims this phase measured against the code (`cli-reference.md:84,87,170,173` on the status map, `:160,162` on the child-output suppression, `:67,128,212` on `--cookie-source file`) are folded into OUT-005, OUT-007 and OUT-014 as evidence rather than filed separately.

---

## Cross-references not re-filed

| Prior finding | Relationship |
|---|---|
| ENT-001, ENT-002 (phase 01) | The reporting handler dies with no sink. Re-measured on `a335b2a`; the caller-visible consequence is `OUT-001`, the mechanism is theirs. |
| ENT-003 (phase 01) | The `batch` `except OSError` reports a log-destination failure as `Failed to read URL file`. Re-measured on `a335b2a`; named inside `OUT-001` so the failure table has one owner. |
| ENT-008 (phase 01) | The 0/1/130 decision and the `typer.echo` calls living in a service. `OUT-008` and `OUT-005` are about the values, not the location. |
| ENT-013 (phase 01) | Import-graph cost. Not re-measured. |
| CFG-003, CFG-004, CFG-008 (phase 02) | The "did you mean" renderer and the typo guard. The recovery round trip in `OUT-005` was run to its end and lands on CFG-003. |
| NET-008 (phase 03) | The non-selectable `unknown` quality value **and** its appearance in an error's list of alternatives. `OUT-017` as filed was this finding again; it is **rejected** as a duplicate and as a check this phase's handbook forbids. The selection defect is not re-filed. |
| SEC-007 (phase 06) | The verbatim `yt_dlp.utils.DownloadError` in a log record. Re-measured on `a335b2a`; the record's *shape* is `OUT-002`/`OUT-003`, its contents are theirs. |
| CON-001, CON-008 (phase 04) | Cancellation absorption and the second-interrupt path. **Not** the same as `OUT-013`: `CON-008` is a swallowed `CancelledError` logged as a shutdown that never happened, in `segment_downloader.py`; `OUT-013` was a never-reset stop state. Different mechanisms, and `OUT-013` is rejected on its own claim, not as a duplicate. |
| ART-001, ART-013 (phase 07) | Filesystem residue and the surviving child partial. Not re-measured here; `OUT-016` files only the name the fallback reports them under. |
| ENT-012 (phase 01) | **The merge target for `OUT-003` and `OUT-004`.** The double bind at `downloader.py:658-659` and the clear at `:700-703`, and the two explicit-field workarounds, are `ENT-012`'s; so is the consequence that records emitted after `download_video` returns carry no identifier. |

## Handoffs received, and where each landed

| Routed by | Item | Disposition |
|---|---|---|
| Phase 03 | rendering of the non-selectable `unknown` quality label | **Rejected** as `OUT-017` — already `NET-008`'s, and the phase-08 handbook forbids manufacturing this check. |
| Phase 07 | the `failed_to_refresh_token` mislabel | **Filed** as `OUT-016`, reclassified to `SPEC-DEVIATION` and demoted to LOW. |
| Phase 07 | generic CLI error text | **Covered** by `OUT-001`. |
| Phase 07 | `_log_preserve_segments`'s `count > 0` silence | **Not filed, deliberately, and the judgement is confirmed correct.** Re-derived: the guard fires when there is something to report and stays quiet at zero, which is a correct guard — a zero count needs no record, and emitting one would put a meaningless event in every run's log. The account's own line about preserved segments (`batch_downloader.py:461-464`) is already phrased as a possibility rather than a measurement. Nothing was filed to fill the row, and the row's silence is the finding's disposition. |

## Confirmation against the task brief

- Commit measured: `a335b2a2e0270414f9f2923d1b4a8e038a8998b5`. `SEC-007`'s two `cli.py` sites were re-measured on it: the shared bootstrap has split them to `cli.py:246` (a single `logger.exception`, the only one in `download`) and `cli.py:350-354` (in `batch`). The leak itself is not re-filed.
  - **Confirmed correct by this phase.** Both anchors were verified against
    `git show a335b2a:src/vkdownloader/cli.py` and are exactly as the report states. On the
    current working tree they sit at `264` and `368-372`; that displacement is the
    uncommitted working-tree edit, not a report error, and is filed as `VAL-003`.
- `ENT-013` was not re-measured.
- `CFG-001` is fixed and `CFG-003`/`CFG-004`/`CFG-008` were not touched; `CFG-003` is reached only as the landing point of the recovery round trip in `OUT-005`.
- The stop path was read as instructed: `cli.py:188-189` (single) and `_classify_download_result` + `_print_batch_summary` (batch) both distinguish a stop from an ordinary failure, and that comparison is recorded as a **checked-and-correct** subject inside `OUT-013` rather than as a finding of its own. The only stop-path defect filed is the one phase 04 did not own: no reset of the state the translation reads.
  - **Confirmed by this phase.** The single-command stop check is at `cli.py:188-189` as
    filed, verified against `git show a335b2a:src/vkdownloader/cli.py`. The
    checked-and-correct judgement is **confirmed and kept** — `_classify_download_result` does distinguish the two outcomes, and the measurement in `OUT-013` Case A shows it doing so on a live run. The "no reset" half of `OUT-013` is **rejected**: the reset is unreachable, and the reasoning and the retained advisory item are in that finding's rejection reason.
- **The four outcomes the validation phase was asked to adjudicate, answered.**
  - **`OUT-002` re-derived on the current tree:** the stdlib re-append is **confirmed** — `format_exc_info` clears the key from the structlog event dict, not from the `LogRecord`, and the `Formatter` appends the chain a second time. A real failing download on `a335b2a` produces 22 075 bytes across 141 physical lines. The report's parse split is corrected from 11/130 to **3/138**; the title's `130 of 141` becomes `138 of 141`.
  - **`OUT-003` / `OUT-004` against `ENT-012`:** both are **restatements**, not new observations. `ENT-012`'s consequence paragraph states verbatim that *"records emitted after `download_video` returns or raises carry no correlation identifier at all"*, and its recommendation is the fix both findings propose. Both are **merged** into `ENT-012` rather than counted again. The genuinely new content — the `run_in_executor` context loss that strips the id from `ytdlp_extraction_error`, and the missing `video_id` on the terminal and failure records — is **not** `ENT-012`'s, is not merged with it, and is recorded in full inside `OUT-003`'s note so the merge does not absorb it.
  - **`OUT-007`'s `UNVERIFIED` marker:** which rule governs. The phase-04 handbook mandated the marker for `CON-002`; this phase's handbook mandates the same treatment, and both reach the same disposition. The binding constraint here is not the marker but `## 12`: a finding whose runtime consequence was not observed *"is never given an observed severity"*. The observed direction (`OUT-007`) shows the lines **arriving**; only the suppressed direction is unobserved, and what the fact loses there is the child's channel, not the diagnosis. `OUT-007` therefore **stays in the corpus** at MEDIUM, with the `UNVERIFIED` marker in place and the severity resting on the reference/code disagreement, which *is* observed in both directions. An `UNVERIFIED` finding is admissible; an `UNVERIFIED` **consequence** may not carry a severity. Where the only support for a MEDIUM were the unobserved consequence, the severity would be composed LOW instead, as it was for `OUT-016`.
  - **`OUT-013` severity and the `CON-008` overlap:** answered inside that finding's rejection. The claimed consequence is unreachable through any shipped path, and the finding is therefore **rejected** rather than demoted to LOW; it is also **not** a duplicate of `CON-008`.

---

## R0 discovery maps (added by the validation phase)

Recorded because a tally of zero, or a merge, is admissible only once these are on the record.

**Corpus map.** Twelve handbooks in `.kilo/commands/audit/phases/` (`01` … `11`, plus
`99-audit-validate.md`); eight have produced findings, four have not been run.

| Phase | Findings file | Validation artifact |
|---|---|---|
| 01-entry-architecture | yes (14) | yes |
| 02-config | yes (8) | yes |
| 03-network-resilience | yes (26) | yes |
| 04-concurrency-cancellation | yes (10) | yes |
| 05-subprocess-browser | yes (table form, `TRN-`) | yes |
| 06-credentials-secrets | yes (10) | yes |
| 07-filesystem-artifacts | yes (14) | yes |
| 08-cli-observability | yes (17) | **this file** |
| 09, 10, 11 | not yet run | — |
| 99-audit-validate | this phase's handbook | — |

No handbook is missing a findings file and no findings file is missing a handbook. Phases 09–11
are unexecuted, not gaps: the orchestrator asks which phases to run
(`audit-multi-phase.md:31-35`). A phase that produced findings and was never validated is
checkable only in this artifact — before this file was written, phase 08 was that phase, and
this run closes it.

**Identifier map.** `EN` (01), `CF` (02), `NE` (03), `CO` (04), `TRN` (05), `SE` (06), `AR`
(07), `OU` (08), `VA` reserved for this phase. Every live prefix is distinct and claimed by
exactly one phase; no prefix is in use by two, and no finding identifier falls outside its
phase's prefix. One adjacent hazard is recorded, not filed: phase 03's *Skip register* uses
`### SKIP-01` … `### SKIP-06` at heading level, the same visual level as its findings, so a
later tool that counts `^### [A-Z]{2}-\d+:` counts 26 when only 20 of them are findings.

**Decision-record map.** Seven validation artifacts exist, one per executed phase; each carries
its own decisions inline, and no instruction anywhere in the pipeline strips a decision —
`audit-refine.md` *rewrites recommendations in place* inside the validation store, which the
source report's own Method section anticipated, and it preserves structure and content. No
decision is deleted by any command. This is the subject the validation handbook asks to be
checked, and the commit history (`d62671b`, *"stop destroying rejected findings"*) shows it was
defective once and is no longer; it is not re-filed.

**Pipeline-document map.** The five commands in `.kilo/commands/audit/`, the twelve phase
handbooks, the single report template in `.ai/audit/templates/`, and the nine role files in
`.kilo/agents/`. Five disagreements among them were observed and are filed as `VAL-001` through
`VAL-005`; the write-path/check-path agreement was verified and is not filed. One further
defect of the same family - the pipeline records a commit but not the tree it read - is`n`VAL-003`, recorded in the map above rather than as a document disagreement.

## Checkpoints (added by the validation phase)

**1 — The source report is the base, not a summary of it.** Every block of
`.ai/audit/08-cli-observability/findings.md` is present here verbatim, in order, including the
Method section, the Evidence/Recommendation text, the Summary, the Mandatory Fixes, the
Advisory Recommendations, the Doc Updates, the cross-reference table and the handoff table.
Decisions are additions to that text, never replacements of it; the only edits to source prose
are the three field-table values the re-derivation changed (`OUT-001` severity, `OUT-016`
severity and type), each annotated in place. Nothing was summarised away.

**2 — Every finding carries a decision, and each decision is where its evidence is.** Seventeen
Validation Notes for the seventeen findings, one under each heading. The two rejected findings
use the reject form — struck title, `[REJECTED]`, a reason — and their original blocks below
are untouched. `OUT-013` and `OUT-017` were checked for the reject form and both carry it.
`OUT-003` and `OUT-004` keep their content in place and name `ENT-012` as the target; neither
was deleted.

**3 — Rerunning this run reproduces these decisions.** The baselines are pinned above and
reproduced exactly on the pinned commit. Every measurement named in a note is reproducible from
a named invocation. Where a conclusion depends on a single measurement, the measurement is
quoted inline so it can be re-run: the 141/3/138 line count for `OUT-002`, the 187 ESC bytes
for `OUT-006`, the thirteen-row status matrix for `OUT-005`, the three-case shutdown probe for
`OUT-013`, and the fourteen-record table for `OUT-003`. Where a conclusion rests on a value the
source report got wrong — `OUT-002`'s parse split, `OUT-003`'s id count, `OUT-008`'s magnitude,
`OUT-016`'s user-visible line — the corrected value is stated in the note next to the original,
not in place of it, so a later run can see what was measured and what was re-measured.

**4 — Nothing was manufactured.** Two `UNVERIFIED` subjects whose triggers are unreachable on
this platform (`OUT-011`'s teardown, `OUT-012`'s in-flight `stop()`) were kept as structural
orderings with their markers intact, and neither was promoted by a substitute terminal. One
phase-07 handoff that produced no finding (`count > 0`) was confirmed as a correct guard and
left unfiled. One in-scope row that produced no finding (the per-run display retention) **was**
filed, because the phase's own rule requires that row to exist and the answer is not "no" — the
retention depends on eight call sites rather than on one, which is a maintenance property worth
recording. The quality-label seam was **not** filed a second time, because the phase's handbook
names it as not carried here.

**5 — The tree moved under this run, and one finding this phase wrote was withdrawn
because of it.** `src/vkdownloader/cli.py` and `src/vkdownloader/config.py` were clean
when this validation began and carry uncommitted edits now; `HEAD` never moved. The
first `VAL-003` this phase wrote called the source report's 27 `cli.py`/`config.py`
anchors systematically wrong, on the strength of a per-file `+18` / `+10` offset that had
been measured against the working copy. The offset was real; the diagnosis was not.
`git show a335b2a:<path>` was then extracted and every one of those anchors re-read
against the commit the report names, and **all 27 are correct**. The finding was withdrawn,
replaced by the provenance defect it actually exposed, and every `+18`/`+10` correction was
removed from the individual Validation Notes. Two of this phase's own errors are recorded
rather than erased, because both are the evidence for `VAL-003` and because a next run must
not repeat them: the false finding, and the fact that the phase's provenance check was a
single `git status` at the start rather than one repeated before the decisions were written.

## Validation Summary

### Decisions, by identifier

| ID | Filed severity | Decision | Re-derived severity | Type after | Reason, in one line |
|---|---|---|---|---|---|
| OUT-001 | HIGH | validated | **CRITICAL** | `RUNTIME-ERROR` | Reproduced exactly; the phase's own §9 CRITICAL row names this shape and both its clauses are measured. |
| OUT-002 | MEDIUM | validated | MEDIUM | `SPEC-DEVIATION` | Mechanism confirmed independently; parse split corrected 11/130 → 3/138; the §9 HIGH qualifier is not met. |
| OUT-003 | MEDIUM | **merged → `ENT-012`** | — | `SPEC-DEVIATION` | `ENT-012` states the same cause, the same workaround and the same fix; content kept here, not counted twice. |
| OUT-004 | LOW | **merged → `ENT-012`** | — | `SPEC-DEVIATION` | `ENT-012`'s consequence paragraph states it verbatim; the additive identity-field half is retained unmerged. |
| OUT-005 | MEDIUM | validated | MEDIUM | `SPEC-DEVIATION` | Thirteen-shape status matrix reproduced verbatim; §9 MEDIUM row met exactly. |
| OUT-006 | MEDIUM | validated | MEDIUM | `SPEC-DEVIATION` | 187 ESC bytes on stderr reproduced; contradicts `cli-reference.md:162`. |
| OUT-007 | MEDIUM | validated | MEDIUM | `SPEC-DEVIATION` | Drop and the code's own declaration of it confirmed; severity rests on the reference/code disagreement, not on the `UNVERIFIED` direction. |
| OUT-008 | MEDIUM | validated | MEDIUM | `SPEC-DEVIATION` | Account reproduced verbatim; the unmeasured magnitude claim is withdrawn, the label/value mismatch is not. |
| OUT-009 | LOW | validated | LOW | `BEST-PRACTICE` | No producer traced for `SKIPPED`; the row existed and was answered. |
| OUT-010 | LOW | validated | LOW | `BEST-PRACTICE` | Differential measurement executed; the harmful direction stays `UNVERIFIED`. |
| OUT-011 | LOW | validated | LOW | `BEST-PRACTICE` | Ordering exact; trigger `UNVERIFIED` as R-S requires, no substitute terminal. |
| OUT-012 | LOW | validated | LOW | `BEST-PRACTICE` | Reachability enumerated across all eight exit paths; filed because the check exists, not against a defect. |
| OUT-013 | MEDIUM | **rejected** | — | — | Consequence unreachable: the `ContextVar` set inside the task never escapes `asyncio.run`. |
| OUT-014 | MEDIUM | validated | MEDIUM | `SPEC-DEVIATION` | `file` rejected with status 2 while three reference rows promise it; the member cannot be constructed. |
| OUT-015 | LOW | validated | LOW | `BEST-PRACTICE` | `log_level` and `log_file` reach no option in either command. |
| OUT-016 | MEDIUM | **reclassified** | **LOW** | `SPEC-DEVIATION` | Nothing observed failing, so `RUNTIME-ERROR` is wrong; the user-visible consequence the report asserts does not exist. |
| OUT-017 | MEDIUM | **rejected** | — | — | Already `NET-008`'s (phase 03, HIGH), and the phase's handbook forbids manufacturing this check. |
| VAL-001 | — | filed | HIGH | `SPEC-DEVIATION` | Validator gate keys on three terms no document defines. |
| VAL-002 | — | filed | MEDIUM | `SPEC-DEVIATION` | Format names a role that does not exist; validator role file omits `RUNTIME-ERROR`. |
| VAL-003 | — | filed | **HIGH** | `SPEC-DEVIATION` | The pipeline pins a commit and reads a working directory; on this run the two are not the same tree. |
| VAL-004 | — | filed | MEDIUM | `SPEC-DEVIATION` | `AGENTS.md` read as mandatory base context by two commands; absent at the root. |
| VAL-005 | — | filed | MEDIUM | `SPEC-DEVIATION` | Orphan census has no exclusion list and reaches the catalogue and a stale worktree copy. |

### Severity tally

Re-derived severities of the **seventeen product findings**, after the merge, the two rejections
and the two severity corrections:

| Severity | Filed | Re-derived | Findings |
|---|---|---|---|
| CRITICAL | 0 | **1** | `OUT-001` |
| HIGH | 1 | **0** | — (`OUT-001` moved to CRITICAL) |
| MEDIUM | 9 | **6** | `OUT-002`, `OUT-005`, `OUT-006`, `OUT-007`, `OUT-008`, `OUT-014` |
| LOW | 7 | **6** | `OUT-009`, `OUT-010`, `OUT-011`, `OUT-012`, `OUT-015`, `OUT-016` |
| not bucketed | 0 | **4** | 2 merged into `ENT-012` (`OUT-003`, `OUT-004`); 2 rejected (`OUT-013`, `OUT-017`) |
| **Total** | **17** | **17** | 12 validated, 1 reclassified, 2 merged, 2 rejected |

Plus the **five `VAL-` findings** filed by this phase against the audit's own documents, which
are not product severities and are tallied separately: `VAL-001` and `VAL-003` HIGH, and
`VAL-002` / `VAL-004` / `VAL-005` MEDIUM.
MEDIUM.

Cross-phase count after this run: the corpus drops by one HIGH and two MEDIUM (merged and
rejected), gains one CRITICAL (the `OUT-001` correction) and one LOW (the `OUT-016`
correction), and the only finding it adds to a *product* queue is `OUT-016` at LOW. A `REF-`
identifier is **not** minted for the `OUT-003`/`OUT-004` remainder: the corpus already has a
fixed identifier namespace per phase prefix and this phase does not introduce a second one, so
the remainder stays as prose inside `OUT-003`'s note where a remediation of `ENT-012` will read
it.

### Rejected findings

| ID | Rejection ground | What survives the rejection |
|---|---|---|
| OUT-013 | non-reproduction of the claimed consequence (a stated ground: *stale / superseded / not reproducible*). Not `CON-008`. | The structural fact, the three-case measurement, the reason the harness — not the product — held the state, and the hardening recommendation, which is carried into *Advisory Recommendations*. |
| OUT-017 | duplicate of `NET-008` (a stated ground) **and** against the phase's own project direction, which names this check as not to be manufactured. | The routing decision, the two grounds, and the `'p'`-concatenation residual to be carried if `NET-008` is ever closed. |

### Merged findings

| Merged ID | Target | Location of the target | Why this target, and not a new one |
|---|---|---|---|
| OUT-003 | `ENT-012` | `.ai/audit/01-entry-architecture/findings.md`; validated at `.ai/audit/99-validation/01-entry-architecture-validated-findings.md` | The absorbing finding is earlier, more severe, already validated, and its recommendation is character-for-character this finding's. |
| OUT-004 | `ENT-012` | as above | Same root cause seen from the terminal record; `ENT-012`'s consequence paragraph states it verbatim. |

Both merged blocks are retained in full in this file, so the fix queue carries one item and the
evidence for the merge is still here. The unmerged remnants — the `run_in_executor` context loss
at `extractor.py:243` and the missing item-identity field — are recorded inside `OUT-003`'s note
and are **not** closed by this merge.

### What this phase did not decide

Not re-filed, by design and not re-derived: `SEC-007`'s error-text leak (phase 06) including
its two `cli.py` sites, re-measured at `cli.py:264` and `cli.py:368-372`;
`ENT-001`, `ENT-002`, `ENT-003`, `ENT-008`, `ENT-013`; `CFG-003`, `CFG-004`, `CFG-008`;
`NET-008`; `CON-001`, `CON-008`; `ART-001`, `ART-013`. `ENT-013` and `ART-001` were not
re-measured, as the source report also did not. `OUT-001`'s mention of `ENT-003` is a
cross-reference so the failure table has one owner; `ENT-003` remains phase 01's.


