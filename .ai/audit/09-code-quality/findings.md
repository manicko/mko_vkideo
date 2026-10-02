---
name: 09-code-quality-findings
description: Phase 09 — Code Quality audit findings (error taxonomy, documentation-to-code drift, checker reach, fixed values, boundary types, responsibilities, file-local consistency)
agent: audit-executor
alwaysApply: false
---

# Phase 09 Audit Findings — Code Quality

**Executor:** audit-executor
**Template:** `.kilo/commands/audit/phases/09-audit-code-quality.md`
**Status:** complete
**Validated:** no

**Measured against:** the **working tree**, at `HEAD` = `a335b2a` plus uncommitted edits to two files that a concurrent agent changed **during** this phase's run (`src/vkdownloader/cli.py`, `src/vkdownloader/config.py` — a CFG-003/CFG-004 typo-guard fix: `warn_unknown_env_vars` now returns its list, `cli.py` renders it to stderr, `config.py`'s module logger is removed). Every anchor in those two files was verified **twice** — once against the working tree and once against `git show HEAD:<path>` — so a line-number drift is never mistaken for a content change:

| File | Working tree | `HEAD` (`a335b2a`) | Result of the two-way check |
|---|---|---|---|
| `src/vkdownloader/cli.py` | 383 lines | 365 lines | All 13 cited anchors are **content-identical** in both; each maps to `HEAD` at a uniform **+18** offset (`cli.py:159`→`141`, `:165`→`147`, `:222`→`204`, `:225`→`207`, `:232`→`214`, `:241`→`223`, `:258`→`240`, `:263`→`245`, `:328`→`310`, `:356`→`338`). **Line numbers reported are the working tree's.** No finding in this report depends on the drift: the handler ladder names the same conditions, in the same order, under both. |
| `src/vkdownloader/config.py` | 372 lines | 382 lines | `config.py:12` is **identical in both** (shift 0). `config.py:15`→`HEAD:17` and `config.py:77`→`HEAD:79` (uniform **−2**; `HEAD` is the longer file because it still carries the two-line module logger and its warning loop). **Line numbers reported are the working tree's.** |

**The phase-08 precedent applies here in both directions and is neither repeated nor assumed:** the earlier validator mistook its own working-tree drift for a systematic anchor defect and withdrew the finding. That error is not mirrored here — the drift is real and is reported as a drift, and the content comparison above shows the drift is **entirely** a line-number shift with no code change behind it at any cited anchor. Nothing is filed on the drift itself.
**Platform:** Windows. This phase is entirely static: file reads, AST scans, and in-process probes run through `uv run python -`. No container, no database, no service, no terminal.
**Trees searched separately throughout:** `src/` (30 `.py` files) and `tests/` (22 `.py` files). Every scan excluded `.kilo/worktrees/` and `.temp/`.

**R1 baseline — the state in which the findings below were observed, cited as coverage and filed nowhere.** All four commands were run twice: once against `a335b2a` and again after the mid-run working-tree change described above. **Both runs produced identical results**, so no finding depends on which of the two states was measured.

| Command | Target | Result |
|---|---|---|
| `uv run pytest tests -q` | test tree | `498 passed, 4 skipped in 28.59s` (denominator: 502 collected) |
| `uv run ruff check src tests` | both trees | `All checks passed!` exit 0 (52 files) |
| `uv run ruff format --check src tests` | both trees | `52 files already formatted` exit 0 |
| `uv run mypy src` | source tree | `Success: no issues found in 30 source files` exit 0 |
| `uv run mypy src tests` | both trees | `Found 55 errors in 6 files (checked 52 source files)` exit 1 — every error in `tests/` |

**Both documented skip texts** (`tests/test_config.py:337`, `tests/test_config.py:353`, `tests/test_hls_downloader.py:533`, `tests/test_hls_downloader.py:678`): *"Owner-only confinement is not offered on Windows: `os.chmod` there toggles only the read-only attribute, so the measured mode is 0o666 rather than the requested 0o600 (D-11)."* Recorded as a documented skip, not as a clean result.

**R1 mypy key-by-key record.** Configured block: `pyproject.toml:90-108`. `strict = true` (line 92) expands, per the installed mypy's own `--help`, to: `--disallow-any-generics, --disallow-subclassing-any, --disallow-untyped-calls, --disallow-untyped-defs, --disallow-incomplete-defs, --check-untyped-defs, --disallow-untyped-decorators, --warn-redundant-casts, --warn-unused-ignores, --warn-return-any, --no-implicit-reexport, --strict-equality, --extra-checks`. Keys **absent** from both `strict` and the explicit block: `--disallow-any-explicit`, `--disallow-any-expr`, `--disallow-any-unimported`. Missing-imports policy: **on** (`pyproject.toml:104`, `ignore_missing_imports = true`). One override at `pyproject.toml:106-108` relaxes `disallow_untyped_decorators` for `vkdownloader.cli` only.

**R1 per-dependency typing-marker table** (`py.typed` asserted in each installed package directory):

| Package | Installed | `py.typed` |
|---|---|---|
| playwright | 1.61.0 | present |
| aiohttp | 3.14.1 | present |
| pydantic | 2.13.4 | present |
| pydantic_settings | 2.14.2 | present |
| typer | 0.26.8 | present |
| rich | 15.0.0 | present |
| structlog | 26.1.0 | present |
| **yt_dlp** | **2026.7.4** | **ABSENT** |

**R7 annotation inventory (`src/` only).** An AST scan of parameter, return and assignment-annotation positions finds 4 explicit `Any` annotations in 2 files. The checker's own `--disallow-any-explicit` key, which the configured profile does not carry, reports **8 explicit-`Any` uses in 6 files**, the other four being non-annotation uses inside Pydantic `model_config` dicts and a callable alias (see QLT-009). Suppression comments: **1**, `infrastructure/browser.py:103` `# type: ignore[union-attr]`. `cast(Any, ...)` sites: **0**. `type: ignore` in `tests/`: **0**.

---

## Findings

### QLT-001: `QualityNotAvailableError` carries two identifiers, and the two ladders that derive its label have already diverged

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/exceptions.py`, `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/models/enums.py` |
| **Classification** | mandatory |

**Description:** One declared condition — "the requested quality cannot be satisfied" — is reported under three different names depending on which rung of the taxonomy the reader consults, and the two independent implementations of that condition's label already disagree with each other.

`QualityNotAvailableError` has two outcomes, distinguished by whether `available` is empty. `error_code` is `QUALITY_NOT_AVAILABLE` on **both** outcomes (`exceptions.py:117`), but `status_label()` returns `"no_streams"` on the empty outcome and `"quality_not_available"` on the non-empty one (`exceptions.py:141-149`). `ErrorCode` (`models/enums.py:52-67`) has **no** `no_streams` member, so the label the batch summary prints is not a member of the enumeration the log is supposed to be filtered by.

The retained legacy shim implements the same ladder a second time and picks a *third* answer for the same object. `exceptions.py:212-217`:

```python
def _quality_not_available_status(exc: QualityNotAvailableError) -> str:
    if not exc.available and exc.requested:
        return f"no_streams: {exc}"
```

The guard requires `exc.requested` to be truthy. The production raise site supplies `requested` as the quality string (`downloader.py:669-673`), so the guard passes — but `quality.py:70` supplies it as the empty string, and on that instance the shim falls through to the `quality_not_available:` branch. The two ladders therefore disagree on exactly the object the shim was written to handle.

**Evidence** — R2, in-process probe through `uv run python -`, no file created. Rung table printed side by side for every declared condition (all 7 classes plus both branches of `QualityNotAvailableError`); the two decisive rows:

```
condition                                            | error_code            | status_label()      | log_context()['error_code']
QualityNotAvailableError [BRANCH A: available EMPTY] | quality_not_available | no_streams          | quality_not_available
QualityNotAvailableError [BRANCH B: available NON-EMPTY]| quality_not_available| quality_not_available| quality_not_available

# the exact object quality.py:70 raises:
error_code     : quality_not_available
status_label() : 'no_streams'
log_context()  : {'error_code': 'quality_not_available', 'message': 'Cannot select quality from empty streams list'}
shim           : 'quality_not_available: requested p, available: '

ErrorCode has a no_streams member? False
```

R2 call-site counts, per tree. `status_label(` — `src`: 7 definitions (the base plus six overrides, all in `exceptions.py`) and **4** production calls, `batch_downloader.py:263,266,275,278`; `tests`: 9. `user_message(` — `src`: 1 (the definition at `exceptions.py:54`); `tests`: 1. **`user_message()` has zero production call sites in either tree.** `log_context(` — `src`: the definition at `exceptions.py:58` plus **one** production call, `batch_downloader.py:272`; `tests`: 2. `_map_exception_to_status` — `src`: the definition only, **zero production call sites**; `tests`: 12.

R3 reachability of branch A is **established**, not assumed. `src/vkdownloader/services/downloader.py:668-673` raises the empty-`available` instance on the ordinary no-streams path, before `selector.select` is reached:

```python
if not video.streams:
    raise QualityNotAvailableError(
        str(quality), [], "No streams found for this video; the video may be private or unavailable",
    )
```

That condition is consumed by two different surfaces: `cli.py:241-257` (`download`) bypasses `status_label()` entirely and prints `"No streams found for this video; the video may be private or unavailable."`; `batch_downloader.py:261-263` (`batch`) puts `e.status_label()` into the result tuple, which `_print_batch_summary` prints verbatim as `<url>: no_streams` (`batch_downloader.py:426,455`).

**Exact consequence:** a user running `vkdownloader batch urls.txt` sees the failure labelled `no_streams`; an operator filtering the structured log by `error_code=quality_not_available` — the vocabulary `models/enums.py:52-58` declares for exactly this purpose ("so that log aggregators and users can filter and group by specific failure modes") — does not see it, because no `ErrorCode.NO_STREAMS` exists to filter on. The three readers of one failure (user, log aggregator, legacy shim) each get a different name and cannot correlate them.

**Recommendation:** pick one identifier per condition. The smallest change that removes the divergence: delete the two-outcome branch in `status_label()` and return `ErrorCode.QUALITY_NOT_AVAILABLE.value`, then delete `_quality_not_available_status` and the `QualityNotAvailableError` row from `_EXCEPTION_STATUS_HANDLERS` so only one ladder remains; or, if `no_streams` is the wanted user-facing wording, add `NO_STREAMS = "no_streams"` to `ErrorCode` and return `self.error_code.value` from the base `status_label()` so the label and the log field are derived from the same member. Either way the two branches in `exceptions.py:141-149` and `exceptions.py:212-217` must be made to agree; leaving both in place is the defect.

---

### QLT-002: The taxonomy's log-context rung is reached by one condition out of six, and the two commands disagree about which
| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/batch_downloader.py`, `src/vkdownloader/cli.py`, `src/vkdownloader/exceptions.py` |
| **Classification** | mandatory |

**Description:** `exceptions.py:1-9` declares the hierarchy's purpose as: exceptions carry a machine-readable `ErrorCode` "and a polymorphic `status_label()` so that structured JSON logs and batch results can be filtered deterministically", and the `log_context()` rung exists to feed structlog. Measured, `log_context()` has exactly **one** production call site in the whole source tree, and it sits on the single condition (`ExtractionError`) that has its own ladder clause.

`services/batch_downloader.py:261-293` is the batch command's per-item ladder. Three of its four domain clauses emit a status string and **no log call at all**:

| Clause | Line | Label emitted | Log call | `error_code` recorded |
|---|---|---|---|---|
| `except QualityNotAvailableError` | 261-263 | `e.status_label()` | none | no |
| `except VideoNotFoundError` | 264-266 | `e.status_label()` | none | no |
| `except ExtractionError` | 267-275 | `e.status_label()` | `logger.error("extraction_error", …, **e.log_context())` | **yes** |
| `except VKDownloadError` (catch-all) | 276-278 | `e.status_label()` | none | no |

The single command's ladder (`cli.py:222-266`) records no `error_code` on any path: the generic handler at `cli.py:263-266` emits `logger.exception("download_failed", url=sanitize_url_for_log(url))` and prints `"An error occurred during download"`.

**Evidence** — R2 call-site counts and R3 per-term record, both from the `src/` tree. `log_context(` appears at `exceptions.py:58` (definition) and `batch_downloader.py:272` (the only call). The hierarchy declares seven conditions — the base `VKDownloadError` plus six subclasses. Of the six subclasses the product can actually raise, **five** have zero production log-context call sites: `VideoNotFoundError`, `InvalidVideoUrlError`, `QualityNotAvailableError`, `QualityParseError`, `DownloadError`. (`VKDownloadError` is never raised directly — no `raise VKDownloadError` exists in `src/` — so it is the sixth declared condition and the sixth with no call site.)

R3 command-asymmetry record, reachability established per term:

| Condition | Reachable on `download`? | Reachable on `batch`? | Handler | Surface on `download` | Surface on `batch` |
|---|---|---|---|---|---|
| `ValidationError` | yes | yes | `cli.py:222` / `cli.py:356` | `format_validation_error` text | same text |
| `QualityParseError` | yes | yes (`ytdlp_downloader.py:130`) | `cli.py:225` / falls to `batch_downloader.py:276` | full list of accepted qualities | status string `invalid_quality` |
| `InvalidVideoUrlError` | yes (`extractor.py:102`) | no — `cli.py:328` pre-validates every list-file entry | `cli.py:232` / `batch_downloader.py:276` | "Invalid URL format…" | (unreachable via the CLI; status string `invalid_url` if a caller passes one directly) |
| `QualityNotAvailableError` | yes | yes | `cli.py:241` / `batch_downloader.py:261` | "No streams found…" or "Requested quality…" | status string only |
| `VideoNotFoundError` | yes (`extractor.py:134,171,179`) | yes | `cli.py:258` / `batch_downloader.py:264` | "Video not found…" | status string only |
| **`ExtractionError`** | yes (`browser.py:47`, `extractor.py:215,231,252,275`) | yes | *not named* → `cli.py:263` / `batch_downloader.py:267` | `"An error occurred during download"` + `download_failed` log with **no** code | `extraction_error` log **with** `error_code=extraction_error` |
| **`DownloadError`** | yes (`ffmpeg_utils.py:444`) | yes | *not named* → `cli.py:263` / `batch_downloader.py:276` | `"An error occurred during download"` + `download_failed` log with **no** code | status string `download_error`, no log |

No condition is raised that neither ladder names: the diff of the hierarchy's seven conditions against `cli.py:222-266` ∪ `batch_downloader.py:261-291` ∪ `cli.py:356-374` is empty, and the two commands' generic handlers terminate every unnamed condition.

**Exact consequence:** the same browser-launch failure (`browser.py:47`, `ExtractionError`) is `{"event": "extraction_error", "error_code": "extraction_error", …}` in the log when it happens under `batch`, and `{"event": "download_failed", "url": "…"}` with no code when it happens under `download`. An operator cannot tell from the log which of the six domain conditions ended a single-video run; the declared `error_code` vocabulary exists for that purpose and is not delivered on the command most users run.

**Recommendation:** make the two terminal handlers symmetric rather than adding new ones. In `cli.py:263-266`, catch `VKDownloadError` before the generic `Exception` clause and emit `logger.error("download_failed", url=…, **e.log_context())`, matching `batch_downloader.py:267-275`. Add the same one-line `logger.error(..., **e.log_context())` to `batch_downloader.py:261-263` and `264-266`, which currently record nothing. If `error_code` is genuinely not wanted on the single-download path, delete `log_context()` and `error_code` from `exceptions.py` and the module docstring's claim at `exceptions.py:1-9`, so the declared vocabulary and the delivered one match.

---

### QLT-003: `docs/STRUCT.md` omits one of 31 source files and three of its 30 rows contradict the file they name

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/STRUCT.md`, `src/vkdownloader/**` |
| **Classification** | advisory |

**Description:** The project's own architecture document is the navigation map for `src/vkdownloader`. Checked against the tree it indexes, in both directions, one module is missing and three rows describe something the named file does not contain.

**Denominator:** the document's own path list (30 paths named in the fenced tree, `docs/STRUCT.md:7-44`) and its own row list (the same 30 lines). **Code the claims name:** `src/vkdownloader/**`.

**Evidence** — R4(a) and R4(b), by AST scan of the source tree and per-row read of the named files. Both directions of the path diff:

- **Named but absent:** none. Every path `docs/STRUCT.md` names resolves.
- **Present but unnamed (1 of 31):** `src/vkdownloader/services/ytdlp_downloader.py` — 779 lines, 13 top-level definitions, the second-largest module in `services/`, and the module the yt-dlp download path, the temp cookie-file lifecycle and the segment-resume fallback all live in (`ytdlp_downloader.py:313` `download_with_ytdlp_with_resume_fallback`, `:564` `_download_with_ytdlp`, `:731` `_resolve_cookies`).

Per-row content comparison — three rows where the one-line description does not match the named file's declared contents:

| Document row, verbatim | The named file's actual declared contents | Match |
|---|---|---|
| `docs/STRUCT.md:28` — `concurrency.py # Concurrency primitives (re-export / compatibility)` | `services/concurrency.py` is 16 lines and declares exactly one thing: `class SemaphoreLike(Protocol)` (`concurrency.py:8-16`). It has **no** `__all__`, re-exports nothing, and holds no compatibility shim. | **contradicted** |
| `docs/STRUCT.md:22` — `dtos.py # Data transfer objects (Stream, StreamInfo)` | `models/dtos.py` declares one class, `HLSDownloadRequest` (`dtos.py:11`). `Stream` is declared in `models/video.py:15`, not `dtos.py`. No symbol named `StreamInfo` exists anywhere in `src/` or `tests/`. | **contradicted** |
| `docs/STRUCT.md:39` — `utils/__init__.py # Exports sanitize_url_for_log, _strip_auth_params, validate_output_path` | The file's own export list, `utils/__init__.py:6-12`, has five entries: `validate_output_path`, `sanitize_title`, `_resolve_output_file`, `sanitize_url_for_log`, `_strip_auth_params`. Two of the five — `sanitize_title` and `_resolve_output_file` — are unnamed. | **contradicted** |

One further row is imprecise but not contradicted and is not filed: `docs/STRUCT.md:23` names the enum classes `Quality` and `Method` where the module declares `QualityEnum` and `DownloadMethod` (`models/enums.py:6,37`).

**Exact consequence:** a reader who follows `docs/STRUCT.md` to find the yt-dlp integration finds no entry for it, and a reader who follows it to `concurrency.py` expecting a compatibility shim finds a 16-line `Protocol` instead. No product behaviour follows from the document; the cost is that the map a new maintainer trusts first is wrong in five places out of thirty.

**Recommendation:** add the `services/ytdlp_downloader.py` row, and correct the three descriptions to what the files declare: `concurrency.py` → `SemaphoreLike Protocol (async semaphore shape)`; `dtos.py` → `HLSDownloadRequest`; `utils/__init__.py` → the five names its `__all__` actually lists. All four edits are one line each in `docs/STRUCT.md`; the code needs no change, because on all three contradicted rows the code is the more defensible choice.

---

### QLT-004: The generated structure maps record 23 of 30 source files and two symbols that no longer exist

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `.ai/structure/back/py_map.yaml`, `.ai/structure/map.md`, `src/vkdownloader/**` |
| **Classification** | advisory |

**Description:** Both machine-generated structure maps are stale relative to the tree they describe. `.ai/structure/back/py_map.yaml` records 23 entries against 30 Python files, and two of the symbols it names are absent from the source. `.ai/structure/map.md` records the same 7 omissions as a directory listing. The recorded `cli.py` entry describes a module that commit `a335b2a` replaced.

**Denominator:** the maps' own entry lists (23 entries in `py_map.yaml`; the file list in `map.md`). **Code the claims name:** `src/vkdownloader/**`.

**Evidence** — R5(a), by parsing `py_map.yaml` and AST-parsing every source file.

- **Path resolvability:** all 23 recorded paths begin `C:\py_exp\mko_vkideo\.ai\builders\..\..\src\vkdownloader\`. `.ai/builders/` is tracked (`.ai/builders/back/run.md`, `.ai/builders/front/run.md`), so every recorded path resolves from a clean checkout. **No unresolvable path.** Verdict recorded because the check was run, not because it found something.
- **Entry count:** 23 recorded, 30 Python files on disk, **0 recorded-but-absent**, **7 present-but-unrecorded**: `__main__.py`, `services/batch_downloader.py`, `services/concurrency.py`, `services/progress_display.py`, `services/ytdlp_downloader.py`, `utils/correlation.py`, `utils/formatting.py`.
- **Symbol diff, both directions.** Named but absent (2 classes/functions, not counting entries the map flattens from method bodies): `models/enums.py` records class `SegmentRetryResult` (`py_map.yaml:116`) — `models/enums.py` is 81 lines and declares seven `StrEnum` classes, none of them that one; `cli.py` records function `_create_progress_callback` (`py_map.yaml:22`) — no such symbol exists in `cli.py`. Present but unnamed: 10 classes (`ConcurrencyTracker`, `ErrorCode`, `InvalidVideoUrlError`, `ProgressStatus`, `QualityParseError`, `RichProgressReporter`, `SemaphoreLike`, `_SettingsOverrides`, `_StatusColumn`, `_TrackedSemaphore`) and 74 top-level functions.
- **The `cli.py` entry describes a superseded module.** `py_map.yaml:19-27` lists `classes: [DownloadContext]` and `functions: [_create_progress_callback, callback, _print_batch_summary, download, batch_download, cli]` and imports `services.quality` and `dataclasses`. In the current tree `DownloadContext` is in `services/batch_downloader.py:96`, `_print_batch_summary` is in `services/batch_downloader.py:399`, and `cli.py` imports neither `dataclasses` nor `services.quality`.
- **`.ai/structure/map.md` omits the same 7 files**, listed at `map.md:35-44` (services) and `map.md:57-60` (utils) with no `__main__.py` at `map.md:4-9`.

**Exact consequence:** the map an agent or maintainer loads first reports a module layout that predates four commits (`eeddff0`, `d62671b`, `ea44b3d`, `a335b2a`). A search driven by it lands on `cli.py` for symbols that moved to `batch_downloader.py`, and never finds the yt-dlp module at all. Nothing checks these files against the tree, so the drift only widens.

**Recommendation:** regenerate both artefacts from the tree rather than hand-patching them — they are declared generated documents, and every one of the seven omissions and both absent symbols would disappear in one regeneration pass. If regeneration is not available in this pipeline, delete them: a stale generated map that is never regenerated is worse than none, because it is trusted. Separately, change the recorded prefix from `.ai\builders\..\..\src\` to `src\` so the paths read as repository-relative rather than depending on a directory that happens to be tracked.

---

### QLT-005: `vkdownloader-overview.md` states a universal export claim that fails for 25 of 28 names, and describes a model that does not exist

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/01-tools/vkdownloader-overview.md`, `src/vkdownloader/**` |
| **Classification** | advisory |

**Description:** Three claims in one tool document fail against the code they name: a universal claim about how the package exports its API, a model that is described field by field and does not exist, and a stated line count the tree contradicts.

**Denominators, one per claim:**

1. **Universal export claim.** `docs/01-tools/vkdownloader-overview.md:330`, verbatim: *"All modules export their public APIs through `downloader.py` for backward compatibility."* Denominator: every export list declared in the source tree — nine `__all__` lists. Code the claim names: `src/vkdownloader/services/downloader.py`.
2. **Named model.** `docs/01-tools/vkdownloader-overview.md:212-218`, verbatim: *"### DownloadProgress Model Enhancement / The `DownloadProgress` model includes: / - `speed` — Bytes per second download rate / - `eta_seconds` — Estimated time to completion / - `percent` — Percentage completion (when duration known)"*. Denominator: every top-level class and model in `src/`. Code the claim names: none exists.
3. **Stated line count.** `docs/01-tools/vkdownloader-overview.md:324`, verbatim: `ffmpeg_utils.py (~360 lines)`. Denominator: the file's own line count. Code the claim names: `src/vkdownloader/services/ffmpeg_utils.py`.

**Evidence** — R4(b) and R4(c), by AST parse of the source tree and the document.

| Claim | Measured | Verdict |
|---|---|---|
| "All modules export their public APIs through `downloader.py`" | `services/downloader.py`'s `__all__` holds **25** names. The tree's other eight `__all__` lists declare **28** names between them, of which **25 are not reachable through it**. Only three are: `HLSDownloader`, `_cookies_to_netscape`, `setup_signal_handlers`. Absent: `BrowserManager`, `JsonValue`, `NetworkMonitor` (`infrastructure/__init__.py`); all ten `models/__init__.py` names; `QualitySelector` (`services/__init__.py`); `_sanitize_cookie_value` (`services/cookies.py`); `RichProgressReporter` (`services/progress_display.py`); `cleanup_signal_handlers` (`services/signal_handlers.py`); all five `utils/__init__.py` names; `sanitize_text_for_log`, `sanitize_url_for_log` (`utils/url_sanitizer.py`). | **contradicted** |
| `DownloadProgress` model with `speed`, `eta_seconds`, `percent` | `DownloadProgress` occurs in **0** files under `src/` and **0** files under `tests/`. `eta_seconds` occurs in **0** files under `src/`. | **absent** |
| `ffmpeg_utils.py (~360 lines)` | `ffmpeg_utils.py` is **515** lines — 43 % more than stated. (The three counts on adjacent lines 321-323 — `~582`, `~722`, `~901` for `downloader.py`, `ytdlp_downloader.py`, `segment_downloader.py` — measure 703, 779, 939; within ~20 % and not filed.) | **contradicted** |

**Exact consequence:** `docs/01-tools/vkdownloader-overview.md` is the document a maintainer reads to learn where the package's API is re-exported from. Following its instruction, an importer of `RichProgressReporter`, `NetworkMonitor`, `sanitize_url_for_log` or any model type reaches an `ImportError`, because none of them is in `services.downloader`. A reader of §"DownloadProgress Model Enhancement" is told the model has `speed`, `eta_seconds` and `percent` fields and then finds that no such model exists — and the adjacent section at `:202` correctly describes `progress_callback` as receiving `FfmpegProgress` objects, so the document contradicts itself as well as the tree.

**Recommendation:** delete the sentence at `:330` and replace it with the true statement — `services/downloader.py` re-exports its own module's surface for backward compatibility; the package's other modules export through their own `__all__`. Delete the `DownloadProgress Model Enhancement` section at `:212-218` outright; there is no model to describe. Correct `~360` to `~515` at `:324`, or drop the line counts from `:321-324` entirely, since a count that must be hand-maintained will drift again.

---

### QLT-006: Two copies of the CLI reference declare the same document id, have already diverged on facts, and nothing chooses between them

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | MEDIUM |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/99-reference/cli-reference.md`, `docs/99-reference/cli-reference-clean.md` |
| **Classification** | mandatory |

**Description:** `docs/99-reference/cli-reference.md` (179 lines) and `docs/99-reference/cli-reference-clean.md` (177 lines) are two copies of the same document. Both open with the **same frontmatter `id: cli-reference`** (`cli-reference.md:2` and `cli-reference-clean.md:2`), so the document's own identity scheme cannot tell them apart. They have already diverged on facts about the command line, and the two copies are wrong in opposite directions: one is correct on facts but has lost every em-dash to a `?`, the other has intact typography but is wrong on the command's options.

`docs/00-overview/doc-maintenance-rules.md:18` states the rule being broken: *"**Single source of truth:** Each fact lives in exactly one file."*

**Denominator:** the document set — every document under `docs/` describing the CLI. **Code the claims name:** `src/vkdownloader/cli.py` and `src/vkdownloader/models/enums.py`.

**Evidence** — R6(b), `git diff --no-index` between the pair, and each divergent row read against the code.

```
 docs/99-reference/cli-reference.md => docs/99-reference/cli-reference-clean.md
 1 file changed, 22 insertions(+), 24 deletions(-)   (123 diff lines)
```

The four divergent rows, checked against `cli.py`:

| Row | `cli-reference.md` | `cli-reference-clean.md` | What the code says |
|---|---|---|---|
| `--cookie-source` short flag (`:69`, `:130`) | none listed | `-c` | `cli.py:159-164` declares `typer.Option(None, "--cookie-source", "-c", …)`. **`-c` exists** → `cli-reference.md` is wrong |
| `--cookie-source` legal values (`:69`, `:212`) | "`none`, `browser`, or `file`", plus a table row `` `file` `` "Load cookies from external file (future enhancement)" | "`none` or `browser`", row absent | `models/enums.py:45-49` declares `CookieSource` with exactly `NONE` and `BROWSER`. **There is no `file` source** → `cli-reference.md` documents a feature that does not exist |
| `--ssl-verify` default (`:70`, `:131`) | `verify` | `true` | `cli.py:165-169` declares `bool | None` defaulting to `None`, and `config.py:77-80` defaults `ssl_verify` to `True`. `verify` is not a value any source can produce → `cli-reference.md` is wrong |
| `batch` step list (`:143-149`, `:140-146`) | 7 steps, including "3. Validates each remaining URL against the VK video URL pattern; non-matching entries are skipped with a warning and counted as invalid" and "7. … including the number of invalid URLs skipped" | 6 steps, both omitted | `cli.py:328-338` does validate and count skipped URLs, and `batch_downloader.py:437-438` prints the skipped count → **`cli-reference-clean.md` is wrong** |

Encoding, measured on the raw bytes of both files:

```
cli-reference.md         bytes=10233  U+2014 em-dash=12  '?'=1
cli-reference-clean.md   bytes=10196  U+2014 em-dash=0   '?'=15   (CRLF line endings)
```

`cli-reference-clean.md` has **zero** em-dashes and **15** literal `?` bytes where the other file has 12 em-dashes — a console/cp1252 round-trip that destroyed every em-dash in the file. The copy named "clean" is the typographically damaged one.

**Exact consequence:** there is no rule anywhere in the repository that names one of these two as authoritative. A maintainer told by a colleague to check "the CLI reference" opens one of two documents; if they open `cli-reference.md` they conclude the tool has a `file` cookie source and no `-c` flag and will write a config against it; if they open `cli-reference-clean.md` they miss the invalid-URL-skipping step and the skipped-count output. Both outcomes are false premises acted on directly, and neither document can simply be deleted — the factually-wrong copy holds the correct typography and the factually-correct copy holds the damaged typography, so the fix requires merging, not picking.

**Recommendation:** merge into `docs/99-reference/cli-reference.md`: keep that file's em-dashes and take the `-c` flag, the two-value cookie source, the `true` default, and the 7-step batch list from `cli-reference-clean.md`, correcting the `file` row and the ssl default against `cli.py` and `models/enums.py`. Then delete `cli-reference-clean.md`. To stop the fork recurring, add one line to `docs/00-overview/doc-maintenance-rules.md` stating that a document's `id` is unique per repository and that a second file carrying an existing `id` is a defect — the duplicate is currently invisible to every check the pipeline runs.

---

### QLT-007: Three defect identifiers cited from source code and from tool documents are defined nowhere in the repository

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `docs/01-tools/vkdownloader-overview.md`, `docs/01-tools/api-reference.md` |
| **Classification** | advisory |

**Description:** Source comments and tool documents cite `INT-001`, `SRV-006` and `SRV-001` as the provenance for design decisions, security invariants and a refactor. None of the three is defined anywhere in the repository — not in `.ai/plans/`, not in `.ai/audit/`, not in `docs/`, not in `.kilo/`. A maintainer auditing the cookie-confinement invariant at `downloader.py:230` can follow the `SEC-003` half of the citation and reaches a real finding; the `INT-001` half leads nowhere.

**Denominator:** every identifier referenced from a source comment or a `docs/` file. **Code the claims name:** the cited files themselves.

**Evidence** — R6(a), by regex search for each identifier across every `.py`, `.md`, `.yaml` and `.toml` file in the repository, excluding `.kilo/worktrees/` and `.venv/`.

```
INT-001  total=8 occurrences, 0 definitions
   src/vkdownloader/services/downloader.py:230   "(SEC-003/INT-001). This replaces the"
   src/vkdownloader/services/downloader.py:256   "# INT-001: Pass cookies via the ffmpeg `cookies` protocol option"
   src/vkdownloader/services/downloader.py:275   "# Build headers as a plain string (NOT @file syntax - INT-001 fix)."
   tests/test_hls_downloader.py:694, 700, 745, 755, 764
SRV-006  total=4 occurrences, 0 definitions
   src/vkdownloader/services/ytdlp_downloader.py:393  "# Backoff between yt-dlp retry attempts (SRV-006):"
   docs/01-tools/api-reference.md:580
   docs/01-tools/vkdownloader-overview.md:41
SRV-001  total=1 occurrence, 0 definitions
   docs/01-tools/vkdownloader-overview.md:328
```

The prefixes actually in use in the shipped audit corpus are `ART`, `BE`, `BRW`, `CFG`, `CON`, `DF`, `ENT`, `FE`, `NET`, `OUT`, `SEC`, `SHA`, `TRN`, `VAL`. **No `INT-` prefix and no `SRV-` prefix exists.** For contrast, the identifiers used alongside these do resolve: `D-01`/`D-04`/`D-11` resolve to `.ai/plans/done/01-confirmed-code-defects_DONE.md` (`:20`, `:23`, `:30`), and `AC2`/`AC8`/`T9` resolve to `.ai/plans/done/01_batch_progress_display_spec_DONE.md` (`:231`, `:237`, `:202`).

**Exact consequence:** three citations in shipped code cannot be followed. `downloader.py:230` and `:256` cite `INT-001` as the reason the ffmpeg cookie path is written the way it is; a maintainer changing `_create_temp_cookie_file` cannot find the requirement it was written against. `ytdlp_downloader.py:393` cites `SRV-006` as the reason for inter-retry backoff. No code behaviour changes; the cost is that three provenance trails dead-end inside the repository.

**Recommendation:** resolve each to the document that actually records it, or delete it. `INT-001` most plausibly corresponds to a phase-05 finding about the ffmpeg `-headers @file` misuse — point all five sites at that finding's real ID. If `SRV-006` and `SRV-001` have no surviving record, remove the parentheticals from `ytdlp_downloader.py:393`, `docs/01-tools/vkdownloader-overview.md:41` and `:328`, and `docs/01-tools/api-reference.md:580`; the surrounding prose already states the rationale in full. Do **not** invent new IDs to fill the gap — an ID with no requirement behind it is the same defect one level down.

---

### QLT-008: Two documents in `docs/99-reference/` describe no code in this repository

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/99-reference/morfx-tools.md`, `docs/99-reference/ast-editor.md` |
| **Classification** | advisory |

**Description:** `docs/` indexes thirteen files. Two of them — 462 lines between them, the largest pair in the reference folder — document agent tooling that this repository does not contain and code it does not contain. `morfx-tools.md` is self-aware about the first half of this and says so in its own note; `ast-editor.md` is not.

**Denominator:** every document under `docs/`. **Code the claims name:** none — recorded as such.

**Evidence** — R6(b), by reading each document's subject matter and searching the repository for what they name.

| Document | Lines | Names | Resolution |
|---|---|---|---|
| `docs/99-reference/morfx-tools.md` | 431 | `telegram_service.py` and other DSL examples; the `morfx` AST transformation tool | Its own note at `morfx-tools.md:16-17` states: *"The DSL examples in this document reference `telegram_service.py` and other files that are synthetic examples for illustration purposes only. They do not correspond to actual files in this codebase. This project is a VK Video Downloader, not a Telegram posting application."* — **the document describes no code in this repository, and says so.** |
| `docs/99-reference/ast-editor.md` | 31 | the `list_symbols` tool; `morfx` | `list_symbols` is not defined in `.kilo/agents/`, `.kilo/commands/`, `kilo.json`, `pyproject.toml`, or any source file. The document instructs the reader to *"**Always run first:** `list_symbols` to discover exact names"* — a command that does not exist here. |

The project's own maintenance rules, `docs/00-overview/doc-maintenance-rules.md:42`, place guides and external docs in `99-reference/`, so the placement is by design; what is not by design is that two of that folder's four files describe a different project.

**Exact consequence:** a maintainer who opens `docs/99-reference/` — the folder the rules designate for reference material — finds that two of its four documents describe a Telegram posting application and an AST tool this project does not ship. `ast-editor.md` is the sharper case: its opening instruction is to run a command that does not exist, and a reader who follows it has no way to tell the document is inapplicable. Neither document's presence changes product behaviour.

**Recommendation:** move both out of the project's `docs/` tree — `morfx-tools.md` is a reasonable agent-tooling reference to keep, but it belongs with the tooling that provides `morfx`, not with this CLI's reference material. If they must stay, add a one-line banner at the top of each naming this repository and stating that the tools described are not installed here; `morfx-tools.md:16-17` already contains that sentence and only needs promoting from a blockquote note into a header.

---

### QLT-009: The configured mypy profile cannot enforce the project's own "no `any`" rule, and one dependency is invisible to it

| Field | Value |
|-------|-------|
| **ID** | QLT-009 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `pyproject.toml`, `src/vkdownloader/exceptions.py`, `src/vkdownloader/models/video.py`, `src/vkdownloader/models/dtos.py`, `src/vkdownloader/config.py`, `src/vkdownloader/services/extractor.py`, `src/vkdownloader/services/ytdlp_downloader.py` |
| **Classification** | advisory |

**Description:** `.kilo/rules/project.md` rule 9 states: *"**Type Safety Everywhere** … Strict TypeScript on frontend and Pydantic v2 + type hints on backend. Share types via OpenAPI. **Avoid `any` completely.**"* The configured checker cannot enforce that rule. `strict = true` expands to thirteen flags, none of which is `--disallow-any-explicit`; the three keys that would enforce "avoid `any`" are absent from the explicit block at `pyproject.toml:90-104` as well. A green `mypy src` therefore certifies a rule the profile does not carry.

**Denominator:** the strict profile's own key list, read from the installed mypy's `--help`, against the configured block. **Code the claim names:** the eight explicit-`Any` annotations that pass today.

**Evidence** — R1 (configuration and per-dependency marker table, both recorded above) and R7. R-N governs this finding: it is evidenced by reading the configured key set and by asserting a marker per installed package, not by making the checker emit a third-party diagnostic.

`uv run mypy --help`, installed version:

```
> --strict   Strict mode; enables the following flags:
              --disallow-any-generics, --disallow-subclassing-any,
              --disallow-untyped-calls, --disallow-untyped-defs,
              --disallow-incomplete-defs, --check-untyped-defs,
              --disallow-untyped-decorators, --warn-redundant-casts,
              --warn-unused-ignores, --warn-return-any,
              --no-implicit-reexport, --strict-equality, --extra-checks
```

Absent from that list and from `pyproject.toml:90-104`: `--disallow-any-explicit`, `--disallow-any-expr`, `--disallow-any-unimported`.

What the missing key would surface — `uv run mypy --disallow-any-explicit src`:

```
exceptions.py:220              Explicit "Any" is not allowed
models/video.py:8, :15, :27    Explicit "Any" is not allowed
models/dtos.py:11              Explicit "Any" is not allowed
config.py:15                   Explicit "Any" is not allowed
services/extractor.py:40       Explicit "Any" is not allowed
services/ytdlp_downloader.py:86 Explicit "Any" is not allowed
Found 8 errors in 6 files (checked 30 source files)
```

`--disallow-any-unimported` reports nothing, because every other dependency ships `py.typed` (R1 table) — so `yt_dlp` is the only unmarked boundary, and it is reached from exactly one place:

| Package without a marker | Source files importing it | Call sites into it |
|---|---|---|
| `yt_dlp` 2026.7.4 | `services/extractor.py:1` (`import yt_dlp`) — 1 file | 1 attribute site, `yt_dlp.YoutubeDL`, consumed at `extractor.py:211` |

With `ignore_missing_imports = true` (`pyproject.toml:104`), nothing stands between the caller and that boundary: a renamed or misspelled `yt_dlp` attribute produces no diagnostic in `mypy src`, only at runtime. The suppression inventory for the same tree is one comment, `infrastructure/browser.py:103` (`# type: ignore[union-attr]`), and zero `cast(Any, …)` sites.

**Exact consequence:** `mypy src` passes with 8 explicit-`Any` uses in the tree, four of them in the models layer that the project's own standards document names as the layer that must use Pydantic typing. Nothing in the configured pipeline will fail if a ninth is added, so the rule that says "avoid `any` completely" is a convention with no enforcement point, and the single third-party integration the checker cannot see (`yt_dlp`, behind a single attribute access) has no signature check at all.

**Recommendation:** add `disallow_any_explicit = true` to `pyproject.toml:90-104` and fix the eight sites it names — `exceptions.py:220` is `dict[type[Exception], Callable[..., str]]`, which is a concrete type already; `models/video.py:8,15,27` and `models/dtos.py:11` are Pydantic `model_config`/payload dictionaries where `JsonValue` is the right type (it is already imported and re-exported by `infrastructure/__init__.py:4`); `config.py:15` and the two service sites need the boundary typed at the point of use. Do **not** add `disallow_any_expr`: it reports 224 sites, almost all of them structlog and Typer surface, and turning it on would consume more effort than the rule is worth. Enabling `disallow_any_explicit` alone closes the gap the project's own rule names, at eight sites.

---

### QLT-010: `ErrorCode` member values are re-spelled as bare string literals in every `status_label()` override

| Field | Value |
|-------|-------|
| **ID** | QLT-010 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/exceptions.py`, `src/vkdownloader/models/enums.py` |
| **Classification** | advisory |

**Description:** Every exception subclass overrides `status_label()` by returning a hand-written string literal that duplicates the value of its own `ErrorCode` member, and nothing checks that the two agree. Five of the six subclasses do this; the sixth (the base) derives the label from `self.error_code`, which is the correct pattern.

**Denominator:** every `status_label()` override the hierarchy declares, against every `ErrorCode` member the project declares. **Code the claims name:** `src/vkdownloader/exceptions.py`.

**Evidence** — R8(b), by AST scan for `ast.Constant` string literals matching a declared enum member's value, across all 30 source files.

| Site, verbatim | Member whose value it duplicates |
|---|---|
| `exceptions.py:77` `return "video_not_found"` | `ErrorCode.VIDEO_NOT_FOUND` (`enums.py:60`) |
| `exceptions.py:106` `return "invalid_url"` | `ErrorCode.INVALID_URL` (`enums.py:61`) |
| `exceptions.py:149` `return "quality_not_available"` | `ErrorCode.QUALITY_NOT_AVAILABLE` (`enums.py:62`) |
| `exceptions.py:183` `return "extraction_error"` | `ErrorCode.EXTRACTION_ERROR` (`enums.py:64`) |
| `exceptions.py:193` `return "download_error"` | `ErrorCode.DOWNLOAD_ERROR` (`enums.py:65`) |

`exceptions.py:171` (`return "invalid_quality"`) is the one override whose value is **not** an `ErrorCode` member — `QualityParseError`'s code is `quality_parse_error` — so that condition too carries a second identifier, alongside the one recorded in QLT-001. It is recorded here as evidence for the same rule rather than filed separately, since QLT-001 already requires the two label ladders to be reconciled.

The rest of the tree's raw-literal sites were classified and are **not** filed, because each is an external protocol's vocabulary rather than a project value: `ffmpeg_utils.py:80` and `:256` and `downloader.py:303` spell `"ffmpeg"` as the **binary name** on `PATH`, not `DownloadMethod.FFMPEG`; `extractor.py:51` compares yt-dlp's `vcodec` value `"none"`; `ytdlp_downloader.py:257` emits yt-dlp's format selector `best`; `ytdlp_downloader.py:158-165` `_SIZE_UNITS` parses the unit suffix of yt-dlp's own progress output; `ffmpeg_utils.py:111` `_PROGRESS_KEY_HANDLERS` keys on ffmpeg's `-progress` pipe keys. `progress_display.py:83-93` returns display **words** (`done`, `failed`, `skipped`, `cancelled`, `in_progress`) from a `match` over `ProgressStatus` members, and its own comment at `:80-82` records the choice: *"Uses a `match` (StrEnum members are a fixed value set) rather than a dict per project rule #10."* That is the rule applied, and it is recorded as justified rather than filed.

**Exact consequence:** renaming an `ErrorCode` member's value — which is a supported operation, since the values are the strings log aggregators filter on — silently leaves `status_label()` returning the old string. Nothing in `mypy`, `ruff` or `pytest` can catch it, because both spellings are valid `str` and the suite's assertions on `status_label()` (`tests/test_exceptions.py:128-158`) hard-code the literals rather than reading them from the enum. The failure would surface only as a log filter that no longer matches.

**Recommendation:** delete the five overrides and let the base implementation at `exceptions.py:52` (`f"error: {self.error_code.value}"`) do the work, adding `error_code = ErrorCode.INVALID_QUALITY` to `models/enums.py` and setting it on `QualityParseError` (`exceptions.py:159`) so the one divergent override also disappears. That removes ten lines and makes the label a single derivation from the enumeration. If the `"error: "` prefix on the base is unwanted, change the base rather than overriding it six times. Independently, change `tests/test_exceptions.py:123-158` to assert against `ErrorCode.<MEMBER>.value` so a rename fails the suite instead of passing it.

---

### QLT-011: `services/downloader_throttle.py` carries four unrelated concerns in 371 lines under one module name

| Field | Value |
|-------|-------|
| **ID** | QLT-011 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** One module named for throttling holds four concerns that share no state and no caller: process-level shutdown signalling, per-URL backoff coordination, a legacy progress-state manager, and an HTTP 429 retry policy. Measured on all three axes: **371 lines, 11 top-level definitions (7 functions/classes + 4 module-level constants), longest single definition 96 lines, 2.96 top-level definitions per hundred lines.** The density column does **not** by itself separate this file from the tree's other large modules — `services/segment_downloader.py` sits at 3.19 and `services/ytdlp_downloader.py` at 1.67 — so the separation is made by the labelled inventory below, which is what the phase's method asks for. **The cost filed is navigation. No behaviour defect is claimed, and the file is not declared wrong for being large.**

**Denominator:** every file in the source tree, measured on all three axes. **Code the claim names:** `src/vkdownloader/services/downloader_throttle.py`.

**Evidence** — R10, per-file AST measurement of all 30 source files (assignments and annotated assignments both counted); the labelled inventory of this file's top-level definitions:

| Definition | Lines | Label |
|---|---|---|
| `_shutdown_event_ctx` (`:26`), `get_shutdown_event` (`:31-43`) | 18 | **shutdown signalling** — a process-wide `ContextVar`-backed `asyncio.Event` |
| `URLBackoffCoordinator` (`:46-75`) | 30 | **per-URL backoff coordination** |
| `ProgressManager` (`:78-171`) | 94 | **legacy progress state** — 5 methods, documented as retained (`:84`) and instantiated by no production caller |
| `_retry_429_with_backoff` (`:174-269`), `_parse_retry_after` (`:272-303`), `_compute_backoff_delay` (`:306-338`), `_wait_with_shutdown` (`:341-371`) | 198 | **HTTP 429 retry policy** — response-header parsing and delay computation |

Four distinct labels across 11 definitions. `services/segment_downloader.py` (939 lines, 30 top-level definitions, 3.19 per hundred lines) and `services/ytdlp_downloader.py` (779 lines, 13 definitions, 1.67) are the two files most likely to be mistaken for the same problem, and neither is one: each holds **one** feature area across many small helpers — parsing, fetching, merging, retry and cleanup all serve a single segment download or a single yt-dlp invocation. This file is the inverse shape: comparable density, four unrelated concerns, and the concern occupying the majority of the file is named neither by the module nor by the architecture document. `docs/STRUCT.md:31` describes it as *"Adaptive throttling (ProgressManager, URLBackoffCoordinator, get_shutdown_event)"* — three of the four, and none of the four retry-policy functions, which together are 198 of its 371 lines.

Verified reachability, so the cost is a real search and not a stale-label worry: the retry-policy concern is **live** — `segment_downloader.py:162` calls `_retry_429_with_backoff`, and `segment_downloader.py:251-252` and `ytdlp_downloader.py:399` call `_parse_retry_after` / `_compute_backoff_delay`. `ProgressManager` is the opposite: `ProgressManager` occurs only at `downloader_throttle.py:78` (the class) and `:87` (its own docstring), so it is instantiated nowhere in `src/`. That class is **documented** as retained (`downloader_throttle.py:84`), so under the phase's dead-code policy it is future-proofing rather than dead code and is not filed as such — it is counted here only as one of the four labels.

**Exact consequence:** a maintainer looking for the 429 retry policy has no entry point into this file — neither the module name nor the architecture document's one-line row points at `_retry_429_with_backoff`, `_parse_retry_after`, `_compute_backoff_delay` or `_wait_with_shutdown`, which together are 198 of the file's 371 lines and are called from two other modules. Finding them means reading the file. Nothing here breaks at runtime and no test is failing; the cost is entirely the search.

**Recommendation:** split the retry policy into its own module — `services/http_retry.py`, holding `_retry_429_with_backoff`, `_parse_retry_after`, `_compute_backoff_delay` and `_wait_with_shutdown` — and add the row to `docs/STRUCT.md:31`. That is a file move plus an import change in each of the two callers and leaves the remaining three concerns (shutdown, backoff coordination, progress state) as one coherent module whose existing name already describes them. Do **not** attempt a broader reorganisation of the service layer: nothing in the measurement calls for one.

---

### QLT-012: Import form is relative in 15 files and absolute in 3

| Field | Value |
|-------|-------|
| **ID** | QLT-012 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/__main__.py`, `src/vkdownloader/config.py`, `src/vkdownloader/exceptions.py` |
| **Classification** | advisory |

**Description:** Of the 25 non-package-root modules, 18 import a sibling at all. Fifteen use the relative form; three use the absolute `vkdownloader.…` form. A tree-wide search for the dominant form therefore misses three files, two of which — the settings model and the exception hierarchy — are imported by most of the other eighteen.

**Denominator:** every `__init__.py` excluded (the four package roots and their eager re-exports are phase 01's subject, ENT-005). The remaining 25 files split into: 15 relative, 3 absolute, 7 that import nothing from the package at all (`models/dtos.py`, `models/enums.py`, `services/concurrency.py`, `services/cookies.py`, `utils/correlation.py`, `utils/formatting.py`, `utils/url_sanitizer.py`). **Code the claim names:** the three files listed.

**Evidence** — R11, by AST classification of every `ImportFrom` node in the 30 source files.

```
RELATIVE imports (15 files):  cli.py, infrastructure/browser.py,
  infrastructure/network_monitor.py, models/video.py, services/batch_downloader.py,
  services/downloader.py, services/downloader_throttle.py, services/extractor.py,
  services/ffmpeg_utils.py, services/progress_display.py, services/quality.py,
  services/segment_downloader.py, services/signal_handlers.py,
  services/ytdlp_downloader.py, utils/security.py

ABSOLUTE vkdownloader.* imports (3 files, 4 statements):
  __main__.py:3     from vkdownloader.cli import cli
  config.py:12      from vkdownloader.models.enums import CookieSource, LogLevel
  exceptions.py:13  from vkdownloader.models.enums import ErrorCode
  exceptions.py:100 from vkdownloader.utils.url_sanitizer import _strip_auth_params
```

The one absolute import *inside* a function body is `exceptions.py:100`, `from vkdownloader.utils.url_sanitizer import _strip_auth_params`, whose comment at `:97-99` names the reason: *"Imported lazily to avoid a circular import."* That deferral is one of the two the phase-01 validator proved load-bearing, and it is recorded here as justified. The finding is the other three statements, none of which carries such a reason.

**Exact consequence:** neither form is wrong, and `mypy src` accepts both, so nothing fails. The cost is that a tree-wide search for the form fifteen files use returns nothing for `config.py`, `exceptions.py` or `__main__.py`, and a reader moving between modules has to know which convention each file follows before a name resolves.

**Recommendation:** convert the three to the relative form the other fifteen use — `from .models.enums import …` in `config.py:12`, `from .cli import cli` in `__main__.py:3`, and `from .utils.url_sanitizer import …` in `exceptions.py:100`. Three lines, no behaviour change, and the tree becomes uniform. Leave `exceptions.py:100` lazy; only change its import style.

---

### QLT-013: The comment on `_compute_backoff_delay` says `Retry-After` overrides the calculated delay; the code treats it as a floor, and a test pins that

| Field | Value |
|-------|-------|
| **ID** | QLT-013 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py`, `tests/test_downloader_throttle.py` |
| **Classification** | advisory |

**Description:** An inline comment states a precedence rule that the two lines beneath it implement in the opposite sense. Routed to this phase by phase 03 (`Named, not filed here: … 09 the Retry-After precedence-comment vs max() wording`). A maintainer who acts on the comment changes correct code and breaks a passing test.

**Denominator:** the code the comment names — `_compute_backoff_delay` (`downloader_throttle.py:306-338`). **Code the claim names:** the same function, plus the two call sites that supply the value.

**Evidence** — the comment, the code, and the measured behaviour. `downloader_throttle.py:334-336`, verbatim:

```python
    # Prefer Retry-After header over calculated delay
    if retry_after_seconds is not None:
        delay = max(delay, retry_after_seconds)
```

`max()` makes `Retry-After` a **lower bound**, not an override: the delay is only ever raised to `Retry-After`, never lowered to it. Measured through the product's own function, with `random.uniform` pinned:

```
comment at :334 says: 'Prefer Retry-After header over calculated delay'
code at :336 is        : delay = max(delay, retry_after_seconds)

  status=429 attempt=0 retry_after=5.0 jitter=0.5  -> 5.0   (Retry-After 5.0 > jitter 0.5)
  status=429 attempt=2 retry_after=1.0 jitter=2.0  -> 2.0   (Retry-After 1.0 < jitter 2.0)  <-- override would give 1.0
  status=429 attempt=0 retry_after=0.1 jitter=0.5  -> 0.5   (Retry-After 0.1 < jitter 0.5)  <-- override would give 0.1
```

The behaviour is not accidental and is not under test by accident: `tests/test_downloader_throttle.py:598-603` (`test_retry_after_overrides_delay`) asserts the raising case, and `tests/test_downloader_throttle.py:605-610` (`test_retry_after_ignored_when_smaller`) asserts `jitter=2.0, Retry-After=1.0 → 2.0`, naming the floor behaviour in the test name itself. Two callers supply the value: `segment_downloader.py:251` and `ytdlp_downloader.py:399` (`_compute_backoff_delay(500, retry_count, None)` — no header, so the branch is not taken on the yt-dlp path).

The docstring one level up is not wrong and is not part of this finding: `downloader_throttle.py:314` says *"Respects Retry-After header if present"*, which `max()` satisfies exactly. Only the inline comment at `:334` claims an override.

**Exact consequence:** a maintainer reading `:334` and trusting it replaces `max(delay, retry_after_seconds)` with `retry_after_seconds`, which makes a 429 wait **less** than its own backoff schedule whenever the server sends a small `Retry-After` — the opposite of the intent — and fails `tests/test_downloader_throttle.py:605-610`. The code is right and the comment is wrong, so the fix is one word, not a behavioural change.

**Recommendation:** change the comment at `downloader_throttle.py:334` to state the rule that is implemented — e.g. *"Treat Retry-After as a floor: wait at least that long, never less than the calculated delay"*. Do not change `max()` and do not change the tests; the floor behaviour is what `tests/test_downloader_throttle.py:605-610` pins and what the two callers rely on.

---

## Subjects checked and not filed

Recorded per the phase's non-reproduction rule: a subject that did not reproduce is filed as a non-reproduction with the exact inputs recorded, never as a clean bill of health.

**`services/ffmpeg_utils.py:474-478` — the comment claiming a `FileNotFoundError` is not an `OSError` subclass: NOT REPRODUCED.** This was routed to this phase as a known-wrong comment. On reading the full sentence and checking both premises against the code, the comment is accurate and no finding is filed. Verbatim, `ffmpeg_utils.py:471-478`:

> `DownloadError`: If the volume lacks the free space the merge requires. … It is deliberately not an ``OSError`` subclass: the yt-dlp resume path wraps this call in ``except (ExtractionError, OSError)`` (ytdlp_downloader.py), which would swallow a FileNotFoundError here, relabel it "failed_to_refresh_token" and return None, losing the message.

Antecedent of *"It"* is `DownloadError`, not `FileNotFoundError`. `DownloadError` is a `VKDownloadError` (`exceptions.py:186`), whose MRO is `DownloadError → VKDownloadError → Exception`; it is not an `OSError` subclass, and that is why `ytdlp_downloader.py:547`'s `except (ExtractionError, OSError)` does not catch it. The sentence about `FileNotFoundError` asserts the opposite of what the routing note recorded — that the handler **would** swallow it. `uv run python -c "import inspect; print(issubclass(FileNotFoundError, OSError))"` returns `True`, confirming the handler does swallow it, which is the comment's own stated reason for preferring `DownloadError`. Both premises verified: the handler exists at `ytdlp_downloader.py:547`, and the call chain reaches the raising function — `download_hls_with_resume` → `segment_downloader.py:614` → `_merge_segments_batched` → `ffmpeg_utils.py:444`. No change recommended.

**Reported, not filed:** `progress_display.py:62-63`, the `except ValueError` arm of `ProgressStatus(str(raw))`, is unreachable from the production domain — the sole writer of `task.fields["status"]` is `finish_task` (`progress_display.py:270`, `:277`), which passes `status.value`. The arm is a defensive coercion over `dict[str, Any]` that rich owns, and the coercion is documented at `progress_display.py:58-59`. Recorded per R8's reachability requirement; not filed, because no severity condition covers an unreachable defensive branch and adding one would manufacture a defect.

**Cross-referenced, not re-filed:** ENT-005, ENT-006, ENT-007, ENT-009, ENT-010 and ENT-014 (phase 01); CFG-003, CFG-004 (phase 02); SEC-001..004 (phase 06). In particular, `services/downloader.py`'s `__all__` repeats `_format_argfile` twice (26 entries, 25 unique) — **inert at runtime**, since `__all__` is a list of strings and the repetition changes no import. That repetition is already filed as ENT-006 by phase 01 and is not re-filed here. The facade question itself is phase 01's, not this phase's.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 7 |
| LOW | 4 |

**Verification rows executed, and the tree each searched:** R1 (both trees, plus configuration and per-package marker tables), R2 (`src/` and `tests/` counted separately), R3 (both command entry points, reachability established per term), R4(a/b/c) (source tree against `docs/STRUCT.md` and `docs/01-tools/*.md`), R5 (source tree against `.ai/structure/back/py_map.yaml` and `.ai/structure/map.md`), R6(a/b) (all source docstrings and comments; all thirteen `docs/` files), R7 (`src/`; `tests/` checked for suppressions and returned zero), R8 (`src/`, all 30 files; enum members traced to all four conversion sites), R9 (`src/` boundaries with reachability class recorded), R10 (all 30 files, three axes each), R11 (all nine export lists; import form across all 30 files). No row lacked a method. No row was skipped for lack of evidence; the only skips are the four documented pytest skips recorded at the top.

## Mandatory Fixes

| ID | Severity | One-line |
|---|---|---|
| QLT-001 | HIGH | `QualityNotAvailableError` reports one condition under three names; `status_label()` and `_quality_not_available_status` already disagree on the same object. |
| QLT-002 | HIGH | `log_context()` is reached on 1 of the 6 conditions the product can raise; `ExtractionError` is logged with its code under `batch` and without it under `download`. |
| QLT-006 | MEDIUM | `cli-reference.md` and `cli-reference-clean.md` share the id `cli-reference`, diverge on facts in opposite directions, and nothing says which is authoritative. |

## Advisory Recommendations

| ID | Severity | One-line |
|---|---|---|
| QLT-003 | MEDIUM | `docs/STRUCT.md` omits `services/ytdlp_downloader.py` and three of its rows contradict the files they name. |
| QLT-004 | MEDIUM | `.ai/structure/back/py_map.yaml` and `.ai/structure/map.md` record 23 of 30 files and two symbols that no longer exist. |
| QLT-005 | MEDIUM | `vkdownloader-overview.md` claims all modules export through `downloader.py` (25 of 28 names do not) and documents a `DownloadProgress` model that does not exist. |
| QLT-009 | MEDIUM | The configured mypy profile carries none of the three `Any` keys, so the project's "avoid `any` completely" rule has no enforcement point; `yt_dlp` is the one unmarked boundary. |
| QLT-010 | MEDIUM | Five `status_label()` overrides re-spell `ErrorCode` member values as bare literals; nothing checks they agree. |
| QLT-011 | MEDIUM | `services/downloader_throttle.py` holds four unrelated concerns, 198 of its 371 lines in a retry policy no document names. |
| QLT-007 | LOW | `INT-001`, `SRV-006` and `SRV-001` are cited from source and docs and defined nowhere in the repository. |
| QLT-008 | LOW | `morfx-tools.md` and `ast-editor.md` describe tooling and code this repository does not contain. |
| QLT-012 | LOW | Import form is relative in 15 files and absolute in 3 (`__main__.py`, `config.py`, `exceptions.py`). |
| QLT-013 | LOW | `downloader_throttle.py:334` says `Retry-After` overrides the backoff delay; `max()` makes it a floor, and a test pins that. |

## Doc Updates Needed

`QLT-003` (`docs/STRUCT.md`), `QLT-004` (`.ai/structure/back/py_map.yaml`, `.ai/structure/map.md`), `QLT-005` (`docs/01-tools/vkdownloader-overview.md`), `QLT-006` (merge and delete `docs/99-reference/cli-reference-clean.md`), `QLT-007` (`src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/ytdlp_downloader.py`, `docs/01-tools/vkdownloader-overview.md`, `docs/01-tools/api-reference.md`), `QLT-008` (`docs/99-reference/morfx-tools.md`, `docs/99-reference/ast-editor.md`).

---

## Ownership map for the validator

| Facet this phase filed | Owned elsewhere — cited, not filed |
|---|---|
| Error taxonomy: codes, labels, messages, log context (`QLT-001`, `QLT-002`, `QLT-010`) | Escape, exit status, stream content → `08` |
| Per-command contract claim *inside* the authoritative CLI reference (`QLT-005` `--cookie-source` / `DownloadProgress` rows are documentation claims about code; the option list itself is `08`'s) | CLI option surface, declared defaults, exit codes → `08` |
| Structural documentation of the system and in-code docstrings (`QLT-003`, `QLT-004`, `QLT-005`, `QLT-007`, `QLT-008`, `QLT-013`) | Setting field type/bound/sourcing → `02` |
| Configured checker reach and the `Any` surface (`QLT-009`) | Subprocess, browser, ffmpeg behaviour → `05`; file modes and artefact lifecycle → `07`; credential content and lifetimes → `06` |
| Import form inside one file (`QLT-012`) | Import graph, cycles, re-export facades, bootstrap order → `01` (ENT-005/006/007) |
| Module concern spread (`QLT-011`) | Structural arrangement of modules and direction of imports → `01` |
| Comment-vs-code precedence claim (`QLT-013`), filed as a documentation claim about code | Whether the resulting wait policy is *right* → `03` (network resilience), which routed it here for the comment only |

**Adjacent phases not run at the time of writing:** the base context lists phases `01`–`08` as produced and `10`–`11` as not. Where this phase cites a neighbour's subject it cites the finding ID recorded in the corpus at `a335b2a` rather than re-deriving it, per binding rule 6.

