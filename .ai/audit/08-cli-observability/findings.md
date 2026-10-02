---
name: 08-cli-observability-findings
description: Phase 08 (CLI and Observability) audit findings
agent: audit-executor
alwaysApply: false
---

# Phase 08 Audit Findings — CLI and Observability

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/08-audit-cli-observability.md`
**Status:** complete
**Validated:** no
**Output mode:** problems-only
**Commit measured:** `a335b2a2e0270414f9f2923d1b4a8e038a8998b5` (`a335b2a`, "refactor(cli): extract one shared command bootstrap"). Every `file:line` anchor below was re-measured against this tree; no anchor is carried over from a preceding phase.

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

| Field | Value |
|-------|-------|
| **ID** | OUT-001 |
| **Severity** | HIGH |
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

### OUT-013: The shutdown state is never reset, so a later ordinary failure in the same process is reported as a user cancellation

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

| Field | Value |
|-------|-------|
| **ID** | OUT-016 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
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

### OUT-017: The quality-error label glues a `p` onto a non-numeric value and offers a value the argument layer rejects

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

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 9 |
| LOW | 7 |

**Harness variant per finding** — through the binary (two streams to two distinct files, status from the shell): OUT-001, OUT-002, OUT-003, OUT-004, OUT-005, OUT-006, OUT-007 (captured direction only; watched direction `UNVERIFIED`), OUT-008, OUT-014, OUT-015. In process only: OUT-010, OUT-011, OUT-012, OUT-013, OUT-017. Structural with the trigger `UNVERIFIED`: OUT-016. No finding is evidenced from a merged capture or from the test suite.

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

## Advisory Recommendations

| ID | Severity | One line |
|---|---|---|
| OUT-009 | LOW | The aggregation rule is silent about `SKIPPED` and would count it as a failure. |
| OUT-010 | LOW | `isatty()` and `Console.is_terminal` decide one surface and can disagree; read the predicate once. |
| OUT-011 | LOW | `stop()` restores the borrowed handlers only if the display's teardown returns. |
| OUT-012 | LOW | A line that began work is left non-terminal when `stop()` runs with work in flight. |
| OUT-015 | LOW | `log_level` and `log_file` govern the process's own output and have no option. |

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
| NET-008 (phase 03) | The non-selectable `unknown` quality value. The rendering of the resulting message is `OUT-017`, filed on that handoff; the selection defect is not re-filed. |
| SEC-007 (phase 06) | The verbatim `yt_dlp.utils.DownloadError` in a log record. Re-measured on `a335b2a`; the record's *shape* is `OUT-002`/`OUT-003`, its contents are theirs. |
| CON-001, CON-008 (phase 04) | Cancellation absorption and the second-interrupt path. `OUT-013` files only the absence of a reset in the outcome translation, which `## 7` assigns here. |
| ART-001, ART-013 (phase 07) | Filesystem residue and the surviving child partial. Not re-measured here; `OUT-016` files only the name the fallback reports them under. |

## Handoffs received, and where each landed

| Routed by | Item | Disposition |
|---|---|---|
| Phase 03 | rendering of the non-selectable `unknown` quality label | **Filed** as `OUT-017`. |
| Phase 07 | the `failed_to_refresh_token` mislabel | **Filed** as `OUT-016`. |
| Phase 07 | generic CLI error text | **Covered** by `OUT-001`. |
| Phase 07 | `_log_preserve_segments`'s `count > 0` silence | **Not filed, deliberately.** The guard fires when there is something to report and stays quiet at zero, which is correct; a zero count needs no record. The account's own line about preserved segments (`batch_downloader.py:461-464`) is already phrased as a possibility rather than a measurement, and `OUT-013` records that the batch layer cannot substantiate it. |

## Confirmation against the task brief

- Commit measured: `a335b2a2e0270414f9f2923d1b4a8e038a8998b5`. `SEC-007`'s two `cli.py` sites were re-measured on it: the shared bootstrap has split them to `cli.py:246` (a single `logger.exception`, the only one in `download`) and `cli.py:350-354` (in `batch`). The leak itself is not re-filed.
- `ENT-013` was not re-measured.
- `CFG-001` is fixed and `CFG-003`/`CFG-004`/`CFG-008` were not touched; `CFG-003` is reached only as the landing point of the recovery round trip in `OUT-005`.
- The stop path was read as instructed: `cli.py:188-189` (single) and `_classify_download_result` + `_print_batch_summary` (batch) both distinguish a stop from an ordinary failure, and that comparison is recorded as a **checked-and-correct** subject inside `OUT-013` rather than as a finding of its own. The only stop-path defect filed is the one phase 04 did not own: no reset of the state the translation reads.

