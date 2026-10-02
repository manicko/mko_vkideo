---
name: 01-entry-architecture-findings
description: Audit phase 01 — Entry Points & Module Architecture findings
agent: audit-executor
alwaysApply: false
---

# Phase 01 Audit Findings — Entry Points & Module Architecture

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/01-audit-entry-architecture.md
**Status:** complete
**Validated:** no

**Baseline the findings below were observed against (R3, R4 — not findings themselves):**

| Baseline | Command | Exit | Output |
|---|---|---|---|
| Static checks (R3) | `uv run ruff check src tests` | 0 | `All checks passed!` |
| | `uv run ruff format --check src tests` | 0 | `52 files already formatted` |
| | `uv run mypy src` | 0 | `Success: no issues found in 30 source files` |
| Suite (R4) | `uv run pytest -q -rs` | 0 | `481 passed, 4 skipped in 27.02s` — all 4 skips are Windows permission-mode skips (D-11, `tests/test_config.py:337,353`, `tests/test_hls_downloader.py:533,678`) |

---

## Findings

### ENT-001: Preamble records are emitted to structlog's default stdout sink, not the configured log sink

| Field | Value |
|-------|-------|
| **ID** | ENT-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** Both commands run `warn_unknown_env_vars()` **before** `Settings(...)` and `setup_logging(...)`
(`cli.py:125-128` and `cli.py:237-240`). Two records are emitted on that path — before any sink is configured:

- `config.py:313-319` — `logger.warning("unknown_env_var_ignored", ...)`
- `config.py:145` — `logger.debug("download_dir_empty_string_using_default")`, raised from a field validator
  that runs inside `Settings.__init__`

At that moment structlog is still on its library default (`structlog.PrintLoggerFactory` → `sys.stdout`,
plain `ConsoleRenderer`), because `config.setup_logging` is the only thing that calls
`structlog.configure(...)` (`config.py:368-382`) and installs the `FileHandler` (`config.py:358-366`).
The records therefore bypass the configured logging chain entirely, are rendered in a *different format*
from every other record, and never reach the file the operator configured.

**Evidence (R2(a) — terminal stream and log file captured separately, per command).**
`.env` in the working directory: `VKDOWNLOADER_DOWNLOAD_DIR=` / `VKDOWNLOADER_LOG_LEVEL=DEBUG` /
`VKDOWNLOADER_LOG_FILE=app4.log`. Command run: `uv run python -m vkdownloader download "not-a-url"`.

```
--- TERMINAL stdout ---
2026-09-29 11:37:09 [debug    ] download_dir_empty_string_using_default
--- CONFIGURED SINK app4.log ---
{"path": "C:\\...\\.env", "event": "env_file_resolved", "level": "debug", "timestamp": "..."}
```

`uv run python -m vkdownloader batch urls_invalid.txt` — identical split:

```
--- TERMINAL stdout ---
2026-09-29 11:37:10 [debug    ] download_dir_empty_string_using_default
--- CONFIGURED SINK app4.log ---
{"path": "...", "event": "env_file_resolved", ...}
{"url": "***REDACTED***", "event": "invalid_url_in_batch", ...}
{"url": "ftp://example.com/***REDACTED***", "event": "invalid_url_in_batch", ...}
```

`env_file_resolved` (`cli.py:44`, emitted *after* `setup_logging`) reaches the file; the two records emitted
*before* it do not. Adding the misspelled `VKDOWNLOADER_LOG_LEVL=INFO` adds a second misplaced record —
`unknown_env_var_ignored` appears on stdout and is absent from the log file, for both commands. When the
typo is in `.env` itself, `extra='forbid'` (`config.py:193`) makes `Settings()` raise before
`setup_logging`, and the configured log file is **never created at all** while both pre-sink records are
still written to stdout.

**Consequence:** every run in which the operator configured `VKDOWNLOADER_LOG_FILE` has the first
configuration diagnostics — the misspelled-variable warning and the empty-`download_dir` notice — outside
the artifact they configured for exactly this purpose, in an unparseable second format. An operator
diagnosing a typo by tailing the log file sees nothing about it.

**Recommendation:** configure the sink before anything can emit. Either move `setup_logging` ahead of
`warn_unknown_env_vars()`/`Settings()` (it already accepts `settings: Settings | None` and builds a
default when given `None`, `config.py:323-335`), or buffer the pre-sink records and flush them after
`structlog.configure`. Either way the two commands must keep doing it in the same place — see ENT-004 for
the place they currently diverge.

---

### ENT-002: The single-download command's catch-all uses a log sink that the failing preamble step was supposed to create

| Field | Value |
|-------|-------|
| **ID** | ENT-002 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py` |
| **Classification** | mandatory |

**Description:** The `download` command's catch-all at `cli.py:180-183` calls
`logger.exception("download_failed", ...)` and then `typer.echo(...)`. `setup_logging` can raise *before*
it configures anything — `config.py:340-344` raises `OSError` at `log_path.parent.mkdir(...)`, which is
five lines above the `logging.basicConfig` (`config.py:358`) and `structlog.configure` (`config.py:368`)
calls. When it does, the handler runs with structlog still on its library default, so the record and the
full traceback are printed on **stdout** in the default renderer, while the operator's stderr receives only
the generic one-liner.

On the declared development platform the handler does not even reach that line.

**Evidence (R2(b) — forced preamble failure: `VKDOWNLOADER_LOG_FILE=urls_invalid.txt\app.log`).**

`uv run python -m vkdownloader download "not-a-url"`:

*With the platform's default stdout encoding (measured: `sys.stdout.encoding == 'cp1251'`)*

```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 83-104: character maps to <undefined>
  ... structlog/_output.py:113 in msg -> print(message, file=f, flush=True)
```

The intended `An error occurred during download` is never printed; a raw multi-frame traceback naming
absolute source paths and the full `Settings(...)` object is dumped to stderr instead.

*With `PYTHONIOENCODING=utf-8` (handler survives, output still goes to the wrong place)*

```
[stdout]  2026-09-29 11:32:11 [error    ] download_failed   url=***REDACTED***
         ┌──── Traceback (most recent call last) ────┐  (rich-rendered, default renderer)
         │ ... setup_logging ... OSError: Failed to create log file parent directory ...
[stderr]  An error occurred during download
exit=1
```

`structlog.dev.ConsoleRenderer` renders `exc_info` through `rich.traceback`, whose box-drawing characters
are not representable in `cp1251`; that is what raises inside `structlog._output.PrintLogger.msg`.

**Consequence:** on a configuration error the single-download command either crashes inside its own error
handler (cp1251 console) or routes the entire diagnostic to a sink the operator did not choose, while the
chosen sink does not exist. In both cases the operator gets either an unstructured traceback or a
one-line message with no indication of the actual cause.

**Recommendation:** make the handler independent of the sink it depends on. The preamble should be split so
that a failure *to create* the sink is reported through a path that cannot itself need the sink — e.g.
`setup_logging` returns a `bool`/raises a dedicated `LogSinkUnavailable` that both commands catch and
present directly, or the sink is installed before the fallible directory creation. The terminal-rendering
and console-encoding facet of the `cp1251` crash belongs to phase `08`; the layer that emitted to the
wrong sink is this phase's.

---

### ENT-003: The batch command's OSError handler reports a log-directory failure as a URL-file read failure

| Field | Value |
|-------|-------|
| **ID** | ENT-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** The two commands declare different handler sets over the same preamble. `download`
(`cli.py:139-183`) has no `except OSError`, so an `OSError` raised by the preamble falls into the
catch-all. `batch_download` (`cli.py:278-296`) declares `except OSError as e` at `cli.py:281-283` with a
hard-coded attribution:

```python
except OSError as e:
    typer.echo(f"Failed to read URL file: {urls_file} — {e}", err=True)
```

That handler is not scoped to the URL-file read it describes. It also covers
`urls_file.read_text()` (`cli.py:245`) **and** `setup_logging(settings)` (`cli.py:240`), which is the only
other `OSError` source inside the `try`. When the preamble fails, the handler prints a statement about a
file read that had not started yet and had already succeeded.

**Evidence (R2(b) — same forced failure as ENT-002, second command):**

```
$ VKDOWNLOADER_LOG_FILE='urls_invalid.txt\app.log'   # a file, not a directory
$ uv run python -m vkdownloader batch urls_invalid.txt
exit=1
[stderr] Failed to read URL file: urls_invalid.txt — Failed to create log file parent directory
         'C:\py_exp\mko_vkideo\.temp\r2\urls_invalid.txt': [WinError 183] Cannot create a file when
         that file already exists
```

The prefix names a failure that did not occur; the real cause survives only because the handler
interpolates `{e}`.

By contrast a *bound* violation (`VKDOWNLOADER_MAX_RETRIES=99`, outside `le=10` at `config.py:59`) is
handled identically and correctly by both commands — `ValidationError` is caught first in each
(`cli.py:139`, `cli.py:278`) and both print the same formatted message and exit `1`. The divergence is
specific to `OSError`.

**Consequence:** an operator who has misconfigured `VKDOWNLOADER_LOG_FILE` and runs `batch` is told their
URL list is unreadable. Acting on that message — rewriting the URL file, or deleting it — destroys the
input the user actually supplied, and the real misconfiguration is left in place.

**Recommendation:** narrow the handler to the read it describes — `except OSError` around
`urls_file.read_text()` only — and let every other `OSError` fall through to a preamble-level handler
shared with `download`. Both commands should share one preamble and one failure-reporting path so this
class of divergence cannot recur.

---

### ENT-004: Interrupt-handler registration lives in the command layer for one command and in a service module for the other

| Field | Value |
|-------|-------|
| **ID** | ENT-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/signal_handlers.py` |
| **Classification** | advisory |

**Description:** The two commands reach their first delegation through the same four preamble steps
(`warn_unknown_env_vars` → `Settings(...)` → `setup_logging` → `_log_env_file_path`;
`cli.py:125-130` and `cli.py:237-242`). They then diverge on who owns interrupt handling:

| command | register | deregister |
|---|---|---|
| `download` | `cli.py:100` — **entry layer** (inside the `_download()` closure) | `cli.py:112` |
| `batch` | `services/batch_downloader.py:322` — **service layer** (inside `_run_batch_with_progress`) | `services/batch_downloader.py:401` |

`docs/STRUCT.md:48` declares `cli.py` the thin entry layer that owns argument parsing, error presentation
and exit codes. Registering process-wide interrupt handling is the same class of process-lifetime concern,
and the rule for this phase is that both commands do it at the same point in their bootstrap.

**Evidence (R1, R2, R8).** R2(c) — re-reading each preamble side by side gives the two orders above: the
four preamble steps are identical and in the same order, the registration point is not. R1(d) — the AST
import-edge pass confirms both modules reach the same helper (`cli.py:34`,
`services/batch_downloader.py:32`) but call it from different layers.

R8 — **documented skip with justification.** The declared platform is Windows; the two-line loop-level
registration probe for both handled signals returns:

```
loop.add_signal_handler(<Signals.SIGINT: 2>)   -> NotImplementedError
loop.add_signal_handler(<Signals.SIGTERM: 15>) -> NotImplementedError
```

Both raise here, so the `signal.signal` fallback at `signal_handlers.py:45-49` is what actually runs: the
layer-placement difference is *not* masked by platform behaviour. The fallback mechanism, the shutdown
Event, its cross-loop visibility and the context-copy workaround are phase `04`'s facets and are **not**
filed or re-severity-rated here.

**Aggravating detail — UNVERIFIED.** In `batch`, `setup_signal_handlers()` at
`services/batch_downloader.py:322` sits *before* the `try:` at `:325` whose `finally` calls
`cleanup_signal_handlers()` at `:401`; `generate_correlation_id()` and `bind_correlation_id()` occupy
`:323-324` in between. A failure on those two lines would leave the handlers registered with no
deregistration path. `download` has the same shape (`cli.py:100` before `cli.py:101`), so the two orders
are at least consistent. No step between the registration and the `try` was observed to fail; this is
stated as a structural fact, not an observed failure.

**Consequence:** handler lifetime is owned by two different layers depending on which command runs. The
`batch` command cannot be exercised, wrapped or reused without the service performing a process-wide side
effect on its behalf, and there is no single place to reason about when the handlers are live.

**Recommendation:** move both calls to the command layer, in the `_download` / `run_batch` wrapper
alongside `asyncio.run`, so registration and deregistration are one `try/finally` in one layer for both
commands, placed inside the `try` so the deregistration path covers the whole bootstrap. Leave
`get_shutdown_event()` where it is — only the registration lifecycle moves. Effort: small. Priority:
recommended; the runtime behaviour is correct today, this removes the divergence that makes it fragile.

---

### ENT-005: Eager package roots republish submodules' contents that nothing imports, and they are what makes two cross-layer cycles load-bearing

| Field | Value |
|-------|-------|
| **ID** | ENT-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/__init__.py`, `src/vkdownloader/utils/__init__.py`, `src/vkdownloader/models/__init__.py`, `src/vkdownloader/infrastructure/__init__.py` |
| **Classification** | advisory |

**Description:** All four package roots eagerly re-export names owned by their submodules:

| root | published names | own lines |
|---|---|---|
| `services/__init__.py` | `HLSDownloader`, `QualitySelector` | `:3-6` |
| `utils/__init__.py` | 5 names, two of them private to siblings | `:3-12` |
| `models/__init__.py` | 10 names | `:3-18` |
| `infrastructure/__init__.py` | `BrowserManager`, `JsonValue`, `NetworkMonitor` | `:3-10` |

Nothing imports any of them through the root. Every import site in the tree addresses the owning
submodule directly (`from ..utils.url_sanitizer import ...`, `from ..models.enums import ...`,
`from ..infrastructure.browser import ...`, `from .downloader import ...`). The re-export is also what
creates the two import cycles the code has to defer around:

* `services/__init__.py:3` → `services.downloader` → `services.extractor:15` → `infrastructure.browser`,
  which is why `infrastructure/browser.py:70` must import `..services.downloader_throttle` *inside*
  `__aexit__` with the comment "Lazy import to avoid circular dependency".
* `utils/__init__.py:3` → `utils.security:8` → `vkdownloader.exceptions`, which is why
  `exceptions.py:100` must import `vkdownloader.utils.url_sanitizer` *inside* `__init__` with the comment
  "Imported lazily to avoid a circular import".

Neither deferral is unjustified — both are load-bearing, as the experiment below proves. The finding is
that the package roots are what manufacture the cycles, so the cost of that coupling is paid by modules
that have nothing to do with it.

**Evidence (R1(b), R1(e), R6).** R1(e) deferral inventory, with each target's own module-level imports:

```
vkdownloader.exceptions:100  in __init__()      -> vkdownloader.utils.url_sanitizer
      target module-level vkdownloader imports: NONE
vkdownloader.infrastructure.browser:70  in __aexit__() -> vkdownloader.services.downloader_throttle
      target module-level vkdownloader imports: ['vkdownloader.config', 'vkdownloader.utils.formatting', 'vkdownloader.utils.url_sanitizer']
vkdownloader.services.downloader:657  in download_video() -> vkdownloader.utils.correlation
      target module-level vkdownloader imports: NONE
```

R1(b) cycle-causation experiment — each deferral hoisted to module scope and imported cold:

```
D1  exceptions.py            BASELINE (deferral kept) : IMPORT SUCCEEDED
                             HOISTED                  : FAILED -> ImportError: cannot import name
                                                            'DownloadError' from 'vkdownloader.exceptions'
                             HOISTED + vkdownloader.utils root neutralised : IMPORT SUCCEEDED
D2  infrastructure/browser.py BASELINE                 : IMPORT SUCCEEDED
                             HOISTED                  : FAILED -> ImportError: cannot import name
                                                            'BrowserManager' from
                                                            'vkdownloader.infrastructure.browser'
```

Neutralising the eager root (replacing it in `sys.modules` with an empty module carrying the correct
`__path__`) removes the failure for D1; for D2 the same neutralisation of `vkdownloader.services` is
blocked by the same root through a different route, and the neutralised-`infrastructure` arm instead
fails on relative-import resolution — i.e. the coupling is the root in both cases.

R1(b) F2, what a root drags in, cold, one module at a time:

```
-- import vkdownloader.services.downloader_throttle   (3 module-level imports of its own)
   pulled in: 24 vkdownloader modules, including vkdownloader.infrastructure.browser
-- same, with vkdownloader.services neutralised
   pulled in: 10 vkdownloader modules, NO vkdownloader.infrastructure at all
-- import vkdownloader.utils.correlation             (0 module-level imports of its own)
   pulled in: 11 vkdownloader modules
-- same, with vkdownloader.utils neutralised
   pulled in: 1 module
```

R6(a) consumer counts, production vs test, all tree searches excluding `.kilo/worktrees` and `.git`:

```
facade: vkdownloader.utils          -> (NO import of the facade module's published names anywhere)
facade: vkdownloader.models         -> (NO import of the facade module's published names anywhere)
facade: vkdownloader.infrastructure -> (NO import of the facade module's published names anywhere)
facade: vkdownloader.services       -> only 4 imports, all in tests, and all of SUBMODULES
                                        (test_cli.py:21 batch_downloader, test_ffmpeg_utils.py:155
                                         ffmpeg_utils, test_hls_downloader.py:2645,2671 signal_handlers)
HLSDownloader   prod=0  test=3     (test_hls_downloader.py:18,701,765)
QualitySelector  prod=2  test=2     (downloader.py:46, ytdlp_downloader.py:30 — both via services.quality)
```

**Consequence:** four public surfaces exist that no module uses and the tests do not validate (the tests
import the submodules). Because they exist, `import vkdownloader.exceptions` or
`import vkdownloader.infrastructure.browser` drags in the settings model and its whole dependency graph,
and any future reordering that puts those roots first produces an `ImportError` on a path that has no
logical reason to be coupled. The two deferrals are the price, and the price is invisible in the two
files that pay it.

**Recommendation:** make the four package roots empty apart from their docstring. Every import site
already addresses the owning submodule, so nothing has to change except the four `__init__` files —
after which `exceptions.py:100` and `infrastructure/browser.py:70` become ordinary module-scope imports
and both deferrals can be deleted. That is the cheapest change in this report: four deletions remove two
cycles, one cross-layer import and four unused public surfaces. Effort: small. Priority: recommended.

---

### ENT-006: The service-layer compatibility facade publishes 26 names — 12 private, one twice, and a registration helper without its cleanup counterpart

| Field | Value |
|-------|-------|
| **ID** | ENT-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/signal_handlers.py` |
| **Classification** | advisory |

**Description:** `services/downloader.py:175-202` is a documented compatibility facade (`:144-174` names
each symbol's real owner). It has three defects that make it a self-validating loop:

1. **Export-list hygiene.** `_format_argfile` appears twice — `:195` and `:200`.
2. **Private names published.** 12 of the 26 entries are underscore-prefixed names that their declaring
   modules treat as private: `_await_first_and_cancel_others`, `_build_ffmpeg_concat_command`,
   `_build_ytdlp_cli_command`, `_cleanup_segments`, `_cookies_to_netscape`, `_download_segment`,
   `_download_segment_parallel`, `_download_segment_sequential`, `_fetch_playlist_with_retry`,
   `_format_argfile`, `_merge_segments_batched`, `_parse_m3u8_segments`, `_retry_429_with_backoff`,
   `_temp_argfile`. Each is imported into `downloader.py` for the re-export alone (`:31-68`) and is
   marked `# noqa: F401 — backward-compat re-export`.
3. **A registered name published without its cleanup counterpart.** `setup_signal_handlers` is published
   at `:201` and imported at `:56` for that purpose, while its own module publishes *both* names together
   (`services/signal_handlers.py:18`). `cleanup_signal_handlers` is absent from the facade.

**Evidence (R6(a), R6(b), tree searches excluding `.kilo/worktrees` and `.git`).** Per-name consumer
counts, production vs test:

```
__all__ (26 entries, 25 unique)
  _await_first_and_cancel_others   prod=0  test=0   <<< NO CONSUMERS AT ALL
  FfmpegProgress                   prod=0  test=3   <<< TEST-ONLY
  ProgressParser                   prod=0  test=5   <<< TEST-ONLY
  read_progress                    prod=0  test=5   <<< TEST-ONLY
  perform_download                 prod=0  test=6   <<< TEST-ONLY
  download_with_ytdlp_with_resume_fallback prod=0 test=2 <<< TEST-ONLY
  check_ffmpeg_available           prod=0  test=1   <<< TEST-ONLY
  cancel_subprocess                prod=0  test=1   (test imports from ffmpeg_utils, not the facade)
  _format_argfile                  prod=0  test=1   <<< TEST-ONLY (and listed twice)
  _temp_argfile / _cleanup_segments / _build_ytdlp_cli_command / _parse_m3u8_segments
                                   prod=0  test=1   <<< TEST-ONLY
  _build_ffmpeg_concat_command     prod=0  test=1   <<< TEST-ONLY
  _fetch_playlist_with_retry       prod=0  test=1   <<< TEST-ONLY
  _download_segment / _download_segment_parallel / _download_segment_sequential
                                   prod=0  test=1   <<< TEST-ONLY
  _merge_segments_batched          prod=0  test=2   (both consumers import from ffmpeg_utils)
  _retry_429_with_backoff          prod=0  test=1   <<< TEST-ONLY
  setup_signal_handlers            prod=0  test=1   (both consumers import from signal_handlers)
  with production consumers:  download_video (cli.py:31, batch_downloader.py:29),
                              download_hls_with_resume, _cookies_to_netscape,
                              _merge_segments_batched, _retry_429_with_backoff, cancel_subprocess
```

15 of 26 entries have zero production consumers. Every test consumer imports them from `downloader`, so
the facade is validated by exactly the tests that would be rewritten alongside it.

R6(b) — the command declaration module's imports, marked public/private against the exporting module's
own declared surface: `cli.py` imports only public names from the service and utility layers
(`run_batch`, `download_video`, `get_shutdown_event`, `is_valid_video_url`, `setup_signal_handlers`,
`cleanup_signal_handlers`, `sanitize_url_for_log`). No private symbol crosses into the entry layer, so
that half of the declared rule is currently honoured.

**Consequence:** the service layer has a second, unofficial public API that no production code uses and
whose 12 private entries expose implementation detail (`_download_segment_parallel`,
`_merge_segments_batched`, `_temp_argfile`) as stable names. A future refactor of any of those internals
has to consider the facade, and nothing in the codebase tells it the facade is dead — the facade is
justified in its own comment block and kept alive by the tests alone.

**Recommendation:** delete the `__all__` block and the compatibility imports at `:31-68`, keeping the
symbols the module actually owns (`HLSDownloader`, `perform_download`, `download_video`,
`_semaphore_context`, `_temp_argfile`, `_format_argfile`) and pointing the 15 test-only import sites at
their owning modules. The comment at `:144-174` already names every owner, so the migration is
mechanical. Effort: small (test import churn dominates). Priority: recommended.

---

### ENT-007: The utility package root publishes two private symbols belonging to sibling modules

| Field | Value |
|-------|-------|
| **ID** | ENT-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/utils/__init__.py`, `docs/STRUCT.md` |
| **Classification** | advisory |

**Description:** `utils/__init__.py:3-4` imports and `:9,11` publishes two names that their own declaring
modules treat as private:

* `_resolve_output_file` — declared at `utils/security.py:82`
* `_strip_auth_params` — declared at `utils/url_sanitizer.py:11`

`docs/STRUCT.md:39` documents this list as current ("Exports sanitize_url_for_log, _strip_auth_params,
validate_output_path"), so the code and the structural description agree. The declared rule they
contradict is `docs/STRUCT.md:48`: the entry layer must make "No business logic or private-symbol
imports from service/utils layers" — a private symbol that a package root publishes is a private symbol
with a public name.

Note the related-but-separate point that `_strip_auth_params` already has a public alias,
`sanitize_url_for_log` (`utils/url_sanitizer.py:50-63`), and both are published in both files. The
duplication of *names* is not itself the finding; publishing the private one alongside it is.

**Evidence (R6(a), tree searches excluding `.kilo/worktrees` and `.git`).**

```
utils/__init__.py __all__ (5): ['validate_output_path', 'sanitize_title', '_resolve_output_file',
                                'sanitize_url_for_log', '_strip_auth_params']
  _strip_auth_params      prod=9  test=1  -- all 9 production sites import it from
                                       vkdownloader.utils.url_sanitizer / ..utils.url_sanitizer,
                                       NOT through the root
  _resolve_output_file   prod=1  test=1  -- downloader.py:28, from ..utils.security
  validate_output_path   prod=2  test=1  -- segment_downloader.py:20, ytdlp_downloader.py:32
  sanitize_title         prod=1  test=1  -- downloader.py:28
  sanitize_url_for_log   prod=1  test=0  -- cli.py:35, from .utils.url_sanitizer
R6(a) facade-path scan: facade vkdownloader.utils -> (NO import of the facade module's published
                              names anywhere, production or test)
```

The root's re-export list has **zero** consumers of any kind, and the three private-named entries are the
two that make the `utils.security → exceptions` coupling load-bearing for `exceptions.py:100` (ENT-005).

**Consequence:** `utils/__init__.py` advertises a five-name public surface that nothing uses and that
includes two names the owning modules declare private. It is the visible half of the cycle that forces
`exceptions.InvalidVideoUrlError.__init__` to defer its import, and a reader of `utils/__init__.py`
would reasonably conclude `_strip_auth_params` is the supported entry point.

**Recommendation:** delete the re-export block and `__all__` from `utils/__init__.py` (ENT-005 already
proposes exactly this) and update the `docs/STRUCT.md:39` line to match — the structural description is
the code's own claim and belongs to phase `09`, which should re-check it once the file is empty.
Effort: trivial. Priority: recommended.

---

### ENT-008: The batch service module imports the presentation framework, formats all user-facing batch text, and returns the process exit status

| Field | Value |
|-------|-------|
| **ID** | ENT-008 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** Three entry-layer responsibilities sit below the entry layer, all in one module:

1. **The presentation framework is imported at module scope** — `services/batch_downloader.py:18`,
   `import typer`.
2. **All user-facing batch text is formatted there** — 11 `typer.echo` calls: `:432` (per-result lines),
   `:441-449` (the summary block), `:459-461` (the failed-URL list), `:467-470` (the interrupted notice).
   `_print_batch_summary` (`:405-474`) is the whole of the batch command's user-visible contract.
3. **The process exit status is decided there** — `_print_batch_summary` returns `130` at `:471` and
   `1 if failed > 0 else 0` at `:474`; `run_batch` returns that value at `:509`; and the command raises
   it verbatim as `raise typer.Exit(code=exit_code)` at `cli.py:276`.

`docs/STRUCT.md:48` declares the entry layer to own "error presentation, exit codes". The module's own
docstring (`:3-5`) still claims the extraction kept the entry layer thin as
"argument parsing -> service call -> result presentation" — after the extraction, the *service* performs
the result presentation and computes the exit code, and the command's remaining contribution to the
output is `cli.py:265-276`.

The exit-code *meaning* (which code means what, and what the user sees for each) is phase `08`'s; this
phase owns only which layer decides it, and files that half only.

**Evidence (R6).**

```
--- presentation-framework (typer) import sites, whole tree ---
  [ENTRY]              src/vkdownloader/cli.py:18                 import typer
  [BELOW-ENTRY-LAYER]  src/vkdownloader/services/batch_downloader.py:18  import typer
  [BELOW-ENTRY-LAYER]  tests/test_cli.py:12                       from typer.testing import CliRunner

--- functions below the entry layer whose return value is raised as an exit status ---
  src/vkdownloader/services/batch_downloader.py:474  in _print_batch_summary()  returns 1 if failed > 0 else 0
  src/vkdownloader/services/batch_downloader.py:471  in _print_batch_summary()  returns 130
```

Consumer scan (worktrees excluded) — `run_batch` is reached from the command at `cli.py:30` and
`cli.py:266`, and from `tests/test_batch_downloader.py:433,558`; `_print_batch_summary` and
`_run_batch_with_progress` are also called directly by `tests/test_batch_downloader.py:197,369,400,410,470,480,514,524,578,586,598,612`.
The presentation and the outcome decision are therefore reachable without going through the command, and
the tests exercise them that way.

**Consequence:** the batch command cannot be replaced, re-skinned or run headless without the service
knowing about Typer, and any other front end that wanted to reuse the batch orchestration would inherit
`typer.echo` output and a `0/1/130` integer. The `batch` command is now three lines long, while its
behaviour lives one layer down.

**Recommendation:** have `run_batch` return its result as data (a result list plus the outcome enum the
model layer already has — `ProgressStatus` at `models/enums.py`, used at
`services/batch_downloader.py:119-123`) and leave the summary text and the exit-status choice to
`cli.py`. That removes the `typer` import from the service layer, moves the 11 `typer.echo` calls and the
`0/1/130` decision to the command, and makes the batch orchestration front-end independent — which is
also what makes it testable without capturing terminal output. Effort: medium. Priority: recommended.

---

### ENT-009: The correlation helpers are imported inside the hot download function with no cycle behind them and no stated reason

| Field | Value |
|-------|-------|
| **ID** | ENT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `services/downloader.py:657-661` imports the correlation helpers from inside
`download_video`, the function every single and batch download goes through:

```python
from ..utils.correlation import (
    bind_correlation_id, clear_correlation_id, generate_correlation_id,
)
```

There is no comment naming a reason, and the import-graph pass shows the target has **no** module-level
`vkdownloader` imports of its own — `utils/correlation.py:10-12` imports only `uuid` and
`structlog.contextvars`. Nothing it pulls in can come back to `services/downloader.py`.

**Evidence (R1(b), R1(e)).**

R1(e) deferral inventory, the target's own module-level imports:

```
vkdownloader.services.downloader:657  in download_video() -> vkdownloader.utils.correlation
      target module-level vkdownloader imports: NONE
```

R1(b) F1, the neutralisation experiment the phase prescribes — the eager `vkdownloader.services` root
replaced in `sys.modules` with an empty module carrying the correct `__path__`, then a copy of
`services/downloader.py` with the import hoisted to module scope is imported cold:

```
hoisted source, services root NEUTRALISED:
  RESULT: IMPORT SUCCEEDED -> no import-time failure without the deferral
```

For comparison, the same experiment on the two deferrals that *do* have a cycle behind them
(`exceptions.py:100`, `infrastructure/browser.py:70`) produces `ImportError` — see ENT-005. This is the
only one of the three deferrals in the project for which no import-time failure exists without it.

**Consequence:** no behavioural defect — the helpers are in `sys.modules` after the first call, so the
cost is one dict lookup per download. The cost is diagnostic: an unjustified deferral reads as "this edge
is dangerous", and the one deferral that genuinely *is* dangerous (ENT-005) has no marker that
distinguishes it. It also puts three names in a hot function body for no stated reason, which is where a
future import-time error would be looked for first and not found.

**Recommendation:** move the import to module scope next to the other `..utils` imports at
`services/downloader.py:28-29`. If the deferral is kept deliberately, add the reason as a comment — the
two justified deferrals in this codebase both have one, and their absence here is what makes this
unjustified deferral indistinguishable from them. Effort: trivial. Priority: recommended.

---

### ENT-010: A module-scope constant is derived by reflecting over the settings schema at import, and nine sibling call sites hardcode the same value

| Field | Value |
|-------|-------|
| **ID** | ENT-010 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** `services/downloader_throttle.py:18-19` freezes a value out of the settings model at
import time:

```python
# Single source of truth: the download timeout default is owned by Settings.download_timeout.
_DEFAULT_DOWNLOAD_TIMEOUT: int = Settings.model_fields["download_timeout"].default
```

The comment claims a single source of truth, but the same declared value is reproduced by a second,
independent mechanism — a literal in nine parameter and field defaults:

| location | second derivation |
|---|---|
| `services/segment_downloader.py:66` | `DownloadPolicy.download_timeout: int = 300` |
| `services/segment_downloader.py:146, 217, 282, 314, 370` | `download_timeout: int = 300` (5 functions) |
| `services/ffmpeg_utils.py:273, 323, 452` | `download_timeout: float = 300.0` (3 functions) |

**Evidence (R5, R1).** R5 — module-scope binding value and type after a cold import:

```
vkdownloader.services.downloader_throttle._DEFAULT_DOWNLOAD_TIMEOUT = 300   type=int
declared Settings.download_timeout default in config.py = 300
runtime reflection: Settings.model_fields['download_timeout'].default = 300
```

R5 second-derivation search (worktrees excluded) — the nine literals above, plus
`tests/test_config.py:28,393` asserting the literal `300`.

The reflection mechanism does work, and the second mechanism does not follow it. Mutating the declared
default before the consumer module is first imported, then importing cold:

```
declared default now                        : 42
  downloader_throttle._DEFAULT_DOWNLOAD_TIMEOUT: 42      <- tracks the schema
  segment_downloader.DownloadPolicy.download_timeout default: 300
  ffmpeg_utils._merge_segments_batched default      : 300.0
  ffmpeg_utils._perform_final_merge default         : 300.0
```

(Control run with the default left at `300` gives `300` in all four positions.)

**Consequence — UNVERIFIED as a live runtime defect.** On the production path every call site that
matters passes the value explicitly (`segment_downloader.py:496-497`, `:700`, `:833`, `:849` all read
`settings.download_timeout`), so an operator's `VKDOWNLOADER_DOWNLOAD_TIMEOUT` *is* honoured and the
duplication is currently latent. The risk is that the nine defaults silently disagree with a value the
code declares to be owned elsewhere: a caller that omits the argument — a new call site, a test helper —
inherits `300` with no signal that the settings model says something else. The import-time reflection
also means the constant is fixed at first import and cannot be re-derived, so the two mechanisms can
never re-converge at runtime.

**Recommendation:** the derived constant is the better half — keep the single-source comment and make it
real. Delete `_DEFAULT_DOWNLOAD_TIMEOUT` and have `_retry_429_with_backoff` take the value from the
caller that already holds `Settings` (`services/segment_downloader.py:168`, `:299`, `:348`, `:397`, `:408`
all forward it), then delete the nine literals so the settings model is the only place the number
appears. If a default is genuinely needed for the signatures, source it from the settings model the same
way `_DEFAULT_DOWNLOAD_TIMEOUT` does rather than repeating the literal. Effort: small. Priority:
recommended.

---

### ENT-011: `clear_correlation_id()` removes every bound context variable, not the one it names

| Field | Value |
|-------|-------|
| **ID** | ENT-011 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/utils/correlation.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/batch_downloader.py` |
| **Classification** | mandatory |

**Description:** `utils/correlation.py:38-44` is named `clear_correlation_id`, is documented as preventing
"correlation-ID leakage between operations", and its body is:

```python
structlog.contextvars.clear_contextvars()
```

`clear_contextvars()` takes no key and empties the whole structlog context. Any other key a caller bound
in the same context — a request id, a user id, a tenant id, any future tracing key — is destroyed by a
function whose name promises to remove one key. The docstring's first line ("Clear all context
variables") documents what the code does; the name and the rest of the docstring document what it
promises.

The helper is on every download path: `services/downloader.py:705-708` and
`services/batch_downloader.py:295-296` and `:399-402` all call it in a `finally`.

**Evidence (R7).** Harness using only the public helpers, printing the context after each step:

```
generate_correlation_id() -> '87aa35bd' (len=8, type=str)
  before any bind                                  get_correlation_id()=None   full_context={}
  after bind_correlation_id(cid)                   get_correlation_id()='87aa35bd'  full_context={'correlation_id': '87aa35bd'}
  after binding an unrelated context key           get_correlation_id()='87aa35bd'
       full_context={'request_id': 'abc', 'unrelated_key': 'do-not-delete', 'correlation_id': '87aa35bd'}
  after clear_correlation_id()                     get_correlation_id()=None   full_context={}
  -> unrelated_key survives?  NO (removed)
```

Nested three deep, each level binding then reading back, then a single clear at the innermost level:

```
  depth 1: bound d2801e75  -> get_correlation_id()='d2801e75'
  depth 2: bound c7617af6  -> get_correlation_id()='c7617af6'
  depth 3: bound 1349a508  -> get_correlation_id()='1349a508'
  innermost clear -> get_correlation_id()=None   (enclosing ids were ['d2801e75','c7617af6','1349a508'])
```

The innermost clear removed the enclosing operations' identifiers, not just its own.

**Consequence:** a caller that binds its own context keys before handing work to the downloader loses
them at the end of the download, with no error and no log line. The batch path calls the helper three
times per item (`:296` in `_download_single`, `:708` in `download_video`, `:402` in
`_run_batch_with_progress`), so anything an outer layer had bound is cleared three times over.

**Recommendation:** make the helper match its name and use the keyed removal structlog provides:
`structlog.contextvars.unbind_contextvars("correlation_id")`, or
`structlog.contextvars.clear_contextvars()` only if and when the module's own contract is explicitly
"this is the owner of the whole structlog context" — in which case rename it to
`clear_logging_context()` and say so in one place, so a future caller does not read the name and assume
key-scoped removal. The keyed form is a one-line change and makes the three call sites safe for callers
that bind their own keys. Effort: trivial. Priority: recommended.

---

### ENT-012: The nested download operation regenerates the correlation identifier and then clears the enclosing one

| Field | Value |
|-------|-------|
| **ID** | ENT-012 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/downloader.py` |
| **Classification** | mandatory |

**Description:** The batch path binds a correlation identifier at two nesting levels, and the inner one
overwrites the outer one instead of inheriting it:

| level | bind | clear |
|---|---|---|
| batch item — `_download_single` | `services/batch_downloader.py:197-198` | `:295-296` (`finally`) |
| batch run — `_run_batch_with_progress` | `:323-324` | `:399-402` (`finally`) |
| single download — `download_video` | `services/downloader.py:663-664` | `:705-708` (`finally`) |

`download_video` is awaited directly from `_download_single` (`services/batch_downloader.py:234`), so it
runs in the *same* context — there is no `asyncio.create_task` boundary and therefore no context copy
between the two binds. The inner bind at `downloader.py:664` shadows the item identifier, and the inner
`finally` at `downloader.py:708` clears the whole structlog context, taking the item identifier with it.

The code already works around this: the two error handlers in `_download_single` pass the identifier as
an explicit log field (`services/batch_downloader.py:274` and `:291`), and
`_run_batch_with_progress` passes it as `batch_correlation_id` (`:334`) instead of relying on the bound
value. Both are the signature of a bound value that does not survive on its own.

**Evidence (R7).** Harness reproducing the exact bind/clear shape of the two functions, using only the
public helpers:

```
bind outer (batch:198)            bound-in-context='dadf2546'   explicit-field='dadf2546'
    bind inner (downloader:664)   bound-in-context='dadf2546'   explicit-field='28215b50'
    clear inner (downloader:708)  bound-in-context=None         explicit-field='28215b50'
    log in handler (explicit)     bound-in-context=None         explicit-field='dadf2546'
after outer clear                 bound-in-context=None         explicit-field='-'
```

The enclosing identifier `dadf2546` is bound at the outer level, is no longer reachable the moment the
inner level binds, and is gone entirely after the inner `finally` runs. The record the outer handler
emits afterwards carries it only because it is passed explicitly.

**Consequence:** in `batch`, every record emitted inside the download — extraction, quality selection,
transfer, retries, throttling — carries the inner identifier, which appears nowhere else in the log. An
operator filtering a log file by batch item cannot join those records to the item's own summary line, and
records emitted after `download_video` returns or raises carry no correlation identifier at all. The
identifier that ties a run together exists in exactly one place: the explicit field on two error records.

**Recommendation:** bind once per logical operation and let nested work inherit it. The batch item and
the batch run are two operations, so they may hold two identifiers — but they must be two *keys*
(`correlation_id` for the item, `batch_correlation_id` for the run, which is what
`services/batch_downloader.py:334` already does) and the inner `download_video` must not bind a third:
it should read and re-emit the inherited one. Removing the bind/clear pair at
`services/downloader.py:663-664` and `:708` — and moving them to the single-download command, which is
the only path that has no enclosing operation — makes the identifier joinable end to end and lets the two
explicit fields at `services/batch_downloader.py:274,291` be deleted. Effort: small. Priority:
recommended; without it the correlation identifier the feature exists to provide does not survive the
batch path it was added for.

---

### ENT-013: Heavy integration libraries are loaded at module scope on every command path, including `--help`

| Field | Value |
|-------|-------|
| **ID** | ENT-013 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/progress_display.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `cli.py:30-33` imports the service layer at module scope, which reaches the integration
libraries unconditionally:

* `services/extractor.py:7` — `import yt_dlp`; `:8-10` — `from playwright.async_api import ...`
* `services/progress_display.py:16-28` — `rich.console`, `rich.progress`, `rich.text`
* `services/downloader_throttle.py:9` — `import aiohttp`; `services/segment_downloader.py:16` likewise

`docs/STRUCT.md:48` describes `cli.py` as the thin entry layer, and the declared layering puts the
extraction service below it. Loading a third-party integration library at the module scope of a module
every command path imports — whether or not the run reaches it — means `--help`, `--version`, and every
argument error pay for all of it.

**Evidence (R1(c)).**

```
$ uv run python -X importtime -c "import vkdownloader.cli"
TOTAL_MODULES_IMPORTED=739
import time:      1792 |     856428 | vkdownloader.cli          <- 856 ms cumulative
import time:      2179 |     112955 |           yt_dlp
import time:      1375 |     197973 |             aiohttp
import time:      4076 |     160788 |             yt_dlp        <- yt-dlp subtree total
import time:       670 |        670 |             playwright

$ uv run python -c "import vkdownloader.cli, sys; ..."
yt_dlp loaded: True    playwright loaded: True    aiohttp loaded: True    rich loaded: True
```

Wall clock, same interpreter and environment:

```
import vkdownloader.cli            851 ms
python -m vkdownloader --help     1043 ms
```

**Consequence:** every invocation pays ~850 ms and 739 module executions before Typer parses a single
argument. `--help` — the command a user reaches for first, and the one a shell completion or a
`--version` probe triggers — costs the same as a no-op. The cost is paid in a deployment where the
browser or the yt-dlp runtime is not installed, and the failure surfaces as an `ImportError` during
module import rather than as a diagnostic the operator can act on.

**Recommendation:** defer the heavy edges to the operations that need them, now that the phase has
established there is no import-time cycle to break (ENT-009 shows a function-scope import of an
integration-free module imports cleanly). The natural seams are
`services/extractor.py:7-10` (import `yt_dlp` and `playwright` inside `_extract_with_ytdlp` /
`_extract_with_browser`) and `services/progress_display.py:16-28` (the reporter already resolves its
`Console` lazily in `start()`, `progress_display.py:152-153`, so the `rich` column classes can follow the
same pattern). If the import-time cost is judged acceptable, the alternative is to state that in
`docs/STRUCT.md` next to the layering description so the next reader does not have to measure it.
Effort: medium (touches three modules and their tests' import-time assumptions). Priority: recommended,
but not urgent — nothing is functionally wrong today.

---

### ENT-014: The configuration object is rebuilt inside the service layer, outside the configured preamble

| Field | Value |
|-------|-------|
| **ID** | ENT-014 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/cli.py` |
| **Classification** | advisory |

**Description:** Each command builds `Settings` exactly once in its preamble (`cli.py:127` and
`cli.py:239`) and hands that object to its service. The service then builds a *second* configuration
object before doing any work — `services/downloader.py:652-653`:

```python
if max_retries_override is not None:
    settings = settings.model_copy(update={"max_retries": max_retries_override})
```

The command's object is what `setup_logging` configured itself from and what the command holds; the
object the download actually runs on is a copy the service made. `model_copy` does not re-validate, so
this second construction is not the same kind of object the preamble produced, and the command has no
visibility of it.

This phase owns only *how many times* and *where* the configuration object is built, and whether a build
happens outside the configured preamble. Whether the copied value violates the field's declared bounds,
and what the user sees as a result, are phase `02`'s and phase `08`'s facets and are **not** filed or
re-severity-rated here.

**Evidence (R5, R2(c)).** R5 — object identity and content across the boundary:

```
Settings built by the command preamble and handed to the service:
  preamble object   max_retries = 3
  service object    max_retries = 99   (model_copy does not re-validate)
  is it the same object the command built?   False
```

R2(c) — re-reading each command's preamble: both build `Settings` once, in the same four-step order, and
hand the same instance to their service; neither command builds a second one. The second build is on the
service side of the boundary in both paths, because both `cli.py:102-110` and `cli.py:265-275` funnel
into `services/downloader.py:601`.

**Consequence:** the object `setup_logging` read `log_level` and `log_file` from is not the object the
download runs on, so "what the command configured" and "what the service used" are two different
objects, and only the first is logged or reported. A future field added to `Settings` and applied
through a `model_copy` in the service layer would silently bypass the command entirely.

**Recommendation:** resolve the override in the command preamble, where the other CLI overrides already
are resolved — `cli.py:127` and `cli.py:239` pass `cookie_source` and `ssl_verify` as constructor
arguments for exactly this reason. Pass `max_retries` the same way and delete
`services/downloader.py:652-653`, so one `Settings` object is built, configured, and used. Effort:
trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 10 |
| LOW | 1 |
| **Total** | **14** |

| Dimension (§6) | Findings |
|---|---|
| (a) Bootstrap order, failure safety, sink configuration | ENT-001, ENT-002, ENT-003, ENT-004, ENT-014 |
| (b) Import-time effects and module-level state | ENT-010, ENT-013 |
| (c) Layer direction and cycle avoidance | ENT-005 |
| (d) Deferred-import justification | ENT-009 — the two justified deferrals (`exceptions.py:100`, `infrastructure/browser.py:70`) are **not** filed; R1(b) proved both load-bearing |
| (e) Entry-layer thinness and outcome ownership | ENT-008 |
| (f) Re-export facade discipline | ENT-005, ENT-006, ENT-007 |
| (g) Correlation-identifier lifecycle | ENT-011, ENT-012 |

## Mandatory Fixes

| ID | Severity | Title |
|---|---|---|
| ENT-001 | HIGH | Preamble records are emitted to structlog's default stdout sink, not the configured log sink |
| ENT-002 | HIGH | The single-download command's catch-all uses a log sink the failing preamble step was supposed to create |
| ENT-012 | HIGH | The nested download operation regenerates the correlation identifier and then clears the enclosing one |
| ENT-003 | MEDIUM | The batch command's OSError handler reports a log-directory failure as a URL-file read failure |
| ENT-008 | MEDIUM | The batch service module imports the presentation framework, formats all user-facing batch text, and returns the process exit status |
| ENT-011 | MEDIUM | `clear_correlation_id()` removes every bound context variable, not the one it names |

## Advisory Recommendations

| ID | Severity | Title | Effort | Priority |
|---|---|---|---|---|
| ENT-004 | MEDIUM | Interrupt-handler registration lives in the command layer for one command and in a service module for the other | small | recommended |
| ENT-005 | MEDIUM | Eager package roots republish submodules' contents that nothing imports, and they make two cross-layer cycles load-bearing | small | recommended |
| ENT-006 | MEDIUM | The service-layer compatibility facade publishes 26 names — 12 private, one twice, and a registration helper without its cleanup counterpart | small | recommended |
| ENT-007 | MEDIUM | The utility package root publishes two private symbols belonging to sibling modules | trivial | recommended |
| ENT-010 | MEDIUM | A module-scope constant is derived by reflecting over the settings schema at import, and nine sibling call sites hardcode the same value | small | recommended |
| ENT-013 | MEDIUM | Heavy integration libraries are loaded at module scope on every command path, including `--help` | medium | recommended, not urgent |
| ENT-014 | MEDIUM | The configuration object is rebuilt inside the service layer, outside the configured preamble | trivial | recommended |
| ENT-009 | LOW | The correlation helpers are imported inside the hot download function with no cycle behind them and no stated reason | trivial | recommended |

## Doc Updates Needed

None. This phase files no `DOC-UPDATE` findings. The one document claim touched here —
`docs/STRUCT.md:39` describing the utility package root's export list, and the layering description at
`docs/STRUCT.md:48` — belongs to phase `09`; ENT-007 cross-references it rather than re-filing it.

## Facets Deliberately Not Filed (owned by other phases)

| Facet | Owner | Where it surfaced in this phase |
|---|---|---|
| Exit-code meaning and its derivation from an outcome | `08` | ENT-008 files only *which layer* chooses the code (`services/batch_downloader.py:471,474` → `cli.py:276`) |
| Option design, precedence, overrides that bypass re-validation | `08`, `02` | ENT-014 files only *where* the second `Settings` is built, not whether the value is valid |
| Shutdown state from a signal, the event, its cross-loop visibility, the context-copy workaround | `04` | ENT-004 files only which layer registers/deregisters; R8 is an explicit documented skip |
| Terminal streams, live display, progress, log-record rendering, console encoding | `08` | ENT-001/ENT-002 file which sink a record reached; the `cp1251` `UnicodeEncodeError` is cited as evidence, not re-filed |
| File permission mode, creation mode, atomicity, cleanup | `07` | not touched |
| Whether a secret appears in anything emitted | `06` | not touched |
| File-local craft — typing, naming, module size, docstring accuracy | `09` | not touched |
| Whether the test suite proves any of the above | `10` | R4 cited only as the state the findings were observed against |

---
