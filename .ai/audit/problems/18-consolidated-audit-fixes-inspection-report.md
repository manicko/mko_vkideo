# Inspection Report — Plan 18: Consolidated Audit Fixes

**Auditor:** auditor
**Commit measured (HEAD):** `a03f823` — "test(B12): rename TST-prefixed identifiers in test tree to product-domain vocabulary"
**Working-tree state:** dirty (staged plan-file rename + untracked audit artifacts)
**Tooling versions (via `uv run`):** mypy 2.1.0, ruff 0.15.20, pytest (via uv)
**Tooling versions (system, not project-canonical):** mypy 2.4.0, ruff 0.14.1

> **Methodology note:** All gates were run both via `python -m` (system tools) and via `uv run` (project-pinned
> tools from `uv.lock`). Where they disagree, the `uv run` result is authoritative — it is the version the
> project's CI and task briefs invoke.

---

## 1. Git State and Relevant Commit History

### Current HEAD

```
a03f823  test(B12): rename TST-prefixed identifiers in test tree to product-domain vocabulary
151ea9f  Fix __all__ in downloader.py and resolve all mypy errors in tests
81ac327  chore(plan): archive plan 21 as completed (audit problems report cleanup)
468d6dd  chore(plan): rename completed plan 14 files to _done and archive audit problems report
...
723cb16  refactor(throttle): split retry policy into retry_policies module
...
3cc2897  feat(cli): add --log-level option and fix Live-1 hint (P13-B2)
48e4472  fix(cookies): add clean-cookies command for legacy bare file residue (R3, §9 Q1 Option D)
```

**Working tree (staged + untracked):**
```
 D .ai/plans/18-consolidated-audit-fixes-execution.md
A  .ai/plans/18-consolidated-audit-fixes-execution_fix.md
?? .ai/audit/orphaned-files/
?? .ai/audit/problems/18-consolidated-audit-fixes-audit-problems.md
?? .ai/plans/15-execution-plan.md
```

HEAD is `a03f823`, which is **2 commits ahead** of `151ea9f` (P18-B14's completing commit) and **3 commits ahead**
of the plan's declared `live_head: 468d6dd`.

### Key commits

| Commit | Summary | Relevant to |
|--------|---------|-------------|
| `151ea9f` | "Fix __all__ in downloader.py and resolve all mypy errors in tests" | P18-B14 claim of completion |
| `723cb16` | "refactor(throttle): split retry policy into retry_policies module" | P18-B28 partial split |
| `3cc2897` | "feat(cli): add --log-level option and fix Live-1 hint (P13-B2)" | R4 resolution (removed `--log-file` from preamble message; added `--log-level`) |
| `48e4472` | "fix(cookies): add clean-cookies command" | Doc issue #2 (third command) |

---

## 2. services/downloader.py :: __all__ and P18-B14 Completion

### Current state

`src/vkdownloader/services/downloader.py` lines 110–136: `__all__` contains **25 names**. All 6 names that
the plan's P18-B14 Phase 1 targets as "omitted" are now **present**:

1. `_create_temp_cookie_file` (line 122)
2. `_download_with_ytdlp` (line 126)
3. `_echo_ytdlp_line` (line 127)
4. `_is_ytdlp_progress_line` (line 129)
5. `_parse_ytdlp_progress` (line 132)
6. `_resolve_cookies` (line 133)

These were added by commit `151ea9f` (diff confirms 6 additions to the `__all__` list).

### Conclusion: Phase 1 (facade fix) — COMPLETE

Commit `151ea9f` fixed the 28 "does not explicitly export attribute" errors by extending `__all__`.

### Caveat: Phase 2 (172 residual errors) — UNRESOLVED per plan, but mypy is 0

The P18-B14 task brief (P18-B14.yaml) describes Phase 2 as fixing 172 residual test-side errors with an
expected distribution of `explicit-any 81 · arg-type 58 · attr-defined 4 · …`. However:

- At HEAD with project-pinned `uv run mypy` 2.1.0: **mypy src tests = 0 errors** (see §4 below).
- The 172-error distribution described in the task brief does **not** match the current mypy output.

**Interpretation:** Commit `151ea9f` claims to have resolved *all* mypy errors (200 → 0), and the project's
pinned mypy 2.1.0 confirms 0 errors. The task brief's Phase 2 distribution was based on the pre-`151ea9f`
state (200 errors at `468d6dd`). The fix is complete per project tooling. **No code change is needed for
the `__all__` or mypy gate.**

### Stale ownership comment (minor)

`downloader.py` lines 104–105 still comment that `_retry_429_with_backoff` is "owned by `downloader_throttle.py`",
but that function was moved to `retry_policies.py` by `723cb16` and is now imported from there (line 35–37):
```python
from .retry_policies import (
    _retry_429_with_backoff,  # noqa: F401 — backward-compat re-export
)
```
The comment is stale but harmless (the import is correct).

---

## 3. mypy src tests — Gate State

### Canonical result (`uv run mypy`)

```
$ uv run mypy src tests
Success: no issues found in 56 source files
EXIT: 0

$ uv run mypy src
Success: no issues found in 32 source files
EXIT: 0
```

**Via the project's pinned mypy 2.1.0: 0 errors in src, 0 errors in tests.** This matches commit `151ea9f`'s
claim. P18-B14's mypy gate is satisfied.

### System mypy discrepancy

```
$ python -m mypy src tests    (mypy 2.4.0, NOT project-pinned)
Found 328 errors in 16 files (checked 56 source files)
```

The 328 errors are overwhelmingly `untyped-decorator` (322), plus 6 misc/stragglers:

| Error code | Count |
|---|---|
| `untyped-decorator` | 322 |
| `misc` | 2 |
| `operator` | 1 |
| `attr-defined` | 1 |
| `return` | 1 |
| `no-any-return` | 1 |
| **Total** | **328** |

**Root cause:** mypy 2.4.0 (system) is stricter about `disallow_untyped_decorators` for `@pytest.mark.asyncio`
and `@pytest.fixture` decorators from `pytest-asyncio 1.4.0`, which do not ship typed stubs. mypy 2.1.0
(project-pinned via `uv.lock`) does not flag these. **This is a tool-version artifact, not a code defect.**

### Conclusion

P18-B14's mypy claim ("0 errors") is **valid when using the project's canonical toolchain** (`uv run mypy`).
The audit problems file (which states mypy = 0 at `151ea9f`) is accurate *for the project's pinned mypy version*.
The 328-error state only appears with the system-installed mypy 2.4.0, which is not what CI or task briefs invoke.

---

## 4. ruff format --check src tests — Rule C12 Violation

### Current state

```
$ uv run ruff format --check src tests
Would reformat: tests/test_cli.py
Would reformat: tests/test_config.py
Would reformat: tests/test_downloader_throttle.py
Would reformat: tests/test_hls_downloader.py
Would reformat: tests/test_segment_downloader.py
5 files would be reformatted, 51 files already formatted
EXIT: 1
```

(The system ruff 0.14.1 reports the identical 5 files — the version difference does not affect this result.)

### Violation confirmed

- **Rule violated:** C12 — "The format gate is green at entry and stays green"
- **All 5 files were modified by commit `151ea9f`**, which completed P18-B14. The commit did not run
  `ruff format` on its changes.
- The plan's gate table (§2.1, line 179) still reads "GREEN — 56 files already formatted" — this is **stale**;
  the gate is RED at the current HEAD.
- The plan's C12 rule (line 245) requires "54 files formatted at every block boundary" — the actual count is
  56 (a pre-existing 54-vs-56 internal inconsistency in the plan, separate from this violation).

### Required fix

`uv run ruff format src tests` (reformats the 5 files; no logic changes).

---

## 5. services/downloader_throttle.py and retry_policies.py — P18-B28 Split

### Current state

**`retry_policies.py`** (239 lines) — created by `723cb16`. Contains:
- `RETRYABLE_STATUS_CODES` (frozenset)
- `_retry_429_with_backoff` (async function)
- `_parse_retry_after`
- `_compute_backoff_delay`
- `_wait_with_shutdown`

Imports from `downloader_throttle`: `_HTTP_DATE_FORMATS`, `DEFAULT_DOWNLOAD_TIMEOUT`,
`build_client_timeout`, `logger`, and accesses `downloader_throttle._strip_auth_params` and
`downloader_throttle.get_shutdown_event()`.

**`downloader_throttle.py`** (230 lines) — still contains at line 87:
```python
class URLBackoffCoordinator:
```
Also contains `ProgressManager` (line 130), `build_client_timeout`, `_resource_key`,
`get_shutdown_event`, `_HTTP_DATE_FORMATS`, `_DEFAULT_BACKOFF_PAUSE_SECONDS`.

### What remains to complete the split

`URLBackoffCoordinator` — the class that manages shared backoff state per URL — **remains in
`downloader_throttle.py`** (line 87). It was **not** moved to `retry_policies.py` by `723cb16`.
`retry_policies.py` does not import or reference `URLBackoffCoordinator`.

`downloader.py` still imports `URLBackoffCoordinator` from `downloader_throttle` (line 64,
TYPE_CHECKING block):
```python
if TYPE_CHECKING:
    from .downloader_throttle import URLBackoffCoordinator
```

### Conclusion: P18-B28 split is PARTIAL

Commit `723cb16` moved the retry *functions* to `retry_policies.py` but left the
`URLBackoffCoordinator` *class* (and `ProgressManager`) in `downloader_throttle.py`. The split is
incomplete. P18-B28's 8 external gates are still pending re-measurement.

Whether `URLBackoffCoordinator` *should* move to `retry_policies.py` is a design decision (the class
manages backoff *state* and shutdown signaling, which overlaps with but is distinct from retry *policy*).
The plan's P18-B28 task brief does not specify a target location for the class — it only says "the split
lands with all 8 external gates re-measured and green" and "DEC-W keeps the downloader_throttle.py split
last in W6."

---

## 6. cli.py :: _render_preamble_failure and R4 Resolution

### Current state

`src/vkdownloader/cli.py` lines 71–103: `_render_preamble_failure` exists. The logging-failure
branch (line 93) now reads:

```python
"Check the VKDOWNLOADER_LOG_FILE environment variable or your .env file."
```

**`--log-file` is NOT referenced** anywhere in the function body. The original message
("Check the `--log-file` option or `VKDOWNLOADER_LOG_FILE` environment variable") was replaced by
commit `3cc2897` ("feat(cli): add --log-level option and **fix Live-1 hint**").

### CLI flag inventory

| Flag | Line(s) in cli.py | Exists? |
|------|--------------------|---------|
| `--log-level` | 394, 544, 650 | **Yes** (4 commands: download, batch, clean-cookies, and help context) |
| `--log-file` | — | **No** (only `VKDOWNLOADER_LOG_FILE` env var is referenced) |

### R4 resolution state

| R4 claim (plan §5.2, line 526) | Current reality | Status |
|---|---|---|
| "neither `--log-level` nor `--log-file` exists as a CLI flag" | `--log-level` **does** exist (commit `3cc2897`) | **STALE** |
| "cli._render_preamble_failure still tells the operator to Check the --log-file option" (plan appendix line 1607) | Function says "VKDOWNLOADER_LOG_FILE environment variable or your .env file" — **no `--log-file` reference** | **STALE** |

### Conclusion: R4 is RESOLVED in code

The user-facing inaccuracy that R4 identified (referencing a non-existent `--log-file` flag) **has been
fixed** by commit `3cc2897`. The function no longer names `--log-file`. `--log-level` exists. R4's core
problem no longer exists in the code.

**However**, the plan file has not been updated to reflect this:
- Plan §5.2 R4 (line 526) states R4 is "Unassigned" and describes the problem as current.
- Plan appendix (line 1607) states `_render_preamble_failure` "still names `--log-file` (R4)".
- The P18-B17 task brief (line 631) is still titled "plan 13 B17 — unchosen decision; candidate owner for R4"
  and includes acceptance criteria about R4 being in-scope or reported.

The plan file's R4 tracking is **stale** relative to the code. The code fix is already done.

---

## 7. Documentation Issues — Verification of All 7

### Issue 1: `docs/01-tools/api-reference.md` lines 774, 781 — `sanitize_title`

**Claim:** Documents `sanitize_title` which doesn't exist; should be `sanitize_filename_component`.

**Verification:** CONFIRMED.
- `src/vkdownloader/utils/security.py:22`: `def sanitize_filename_component(title: str) -> str:`
- No `def sanitize_title` exists anywhere in `src/` (grep returns zero hits).
- `downloader.py:350` calls `sanitize_filename_component(video.title)`.
- `docs/01-tools/api-reference.md:774` → `### sanitize_title`
- `docs/01-tools/api-reference.md:781` → `def sanitize_title(title: str) -> str:`

**Staleness:** The audit problems file (line 123) suggests verifying in `url_sanitizer.py` or
`filesystem_utils.py`, but the function is actually in `utils/security.py`. The function name
correction is correct; the location hint in the problems file is slightly off.

### Issue 2: `docs/01-tools/vkdownloader-overview.md` line 130 — "two commands"

**Claim:** Says "two commands" but CLI has three (download, batch, clean-cookies).

**Verification:** CONFIRMED.
- `cli.py:358`: `@app.command()` → `download`
- `cli.py:504`: `@app.command("batch")` → `batch`
- `cli.py:646`: `@app.command("clean-cookies")` → `clean-cookies` (added by `48e4472`)
- `docs/01-tools/vkdownloader-overview.md:130`: "The CLI (`cli.py`) provides two commands:"

### Issue 3: `docs/01-tools/vkdownloader-overview.md` line 16 — "direct HLS-to-MP4 conversion"

**Claim:** Describes ffmpeg as "direct HLS-to-MP4 conversion" but it's only a merge engine.

**Verification:** CONFIRMED.
- Line 16: "combines yt-dlp for stream extraction with ffmpeg for direct HLS-to-MP4 conversion"
- Line 286 (same document): "ffmpeg_utils.py - FFmpeg commands, availability probe, **merge engine**"
- The same document contradicts itself: line 16 says "direct HLS-to-MP4 conversion", line 286 says "merge engine".
- `ffmpeg_utils.py` contains `merge_segments_batched`, `perform_final_merge`, `build_ffmpeg_concat_command` —
  all merge/stitch operations, no HLS-to-MP4 transcoding.

### Issue 4: `docs/11-guides/configuration.md` line 75 — `auto` + `cookie_source=BROWSER`

**Claim:** Says "No browser involvement" but the browser IS launched.

**Verification:** CONFIRMED.
- Line 75: `| \`auto\` | No browser involvement | No browser involvement |`
- `downloader.py:253–257`: In the `DownloadMethod.AUTO` case, when
  `settings.cookie_source != CookieSource.NONE`, it calls `await _resolve_cookies(...)`.
- `extractor.py` (via `VKVideoExtractor._resolve_cookies`): when `cookie_source == CookieSource.BROWSER`,
  launches the browser to extract real cookies.
- Line 78 of the same doc even confirms: "the system forces browser launch regardless of `cookie_source`
  setting to recover from expired tokens."
- The `yt-dlp` row for `cookie_source=BROWSER` correctly says "Uses yt-dlp with browser cookies",
  but the `auto` row says "No browser involvement" — it should say the browser IS launched.

### Issue 5: `docs/00-overview/doc-maintenance-rules.md` lines 101–104 — wrong paths/APIs

**Claim:** References `core/` (should be `src/vkdownloader/`), `app.py` (should be `cli.py`),
`logging.getLogger(__name__)` (should be `structlog.get_logger(__name__)`).

**Verification:** CONFIRMED.
- Line 101: `Use \`logger = logging.getLogger(__name__)\` for all service layer output in \`core/\``
  - Real path: `src/vkdownloader/services/*.py` (no `core/` directory exists)
  - Real API: `from structlog import get_logger; logger = get_logger(__name__)` — used in
    `downloader_throttle.py:18`, `downloader.py:66`, `retry_policies.py` (via re-export)
- Line 102: `Use \`console.print()\` (Rich) for CLI user-facing output in \`app.py\``
  - Real entry module: `src/vkdownloader/cli.py` (no `app.py` exists)
- Line 103: `Use \`rich.progress.track()\` for terminal progress bars`
  - Project uses `services/progress_display.py` (`RichProgressReporter`), not `rich.progress.track()`

### Issue 6: `docs/00-overview/doc-maintenance-rules.md` line 9 — `related: overview.md`

**Claim:** `related` references `overview.md` but no such file exists; correct id is `vkdownloader-overview`.

**Verification:** CONFIRMED.
- Line 9: `related: - overview.md`
- `docs/01-tools/overview.md` does NOT exist (`Test-Path` → false).
- `docs/01-tools/vkdownloader-overview.md` exists with frontmatter `id: vkdownloader-overview` (line 2).
- The `related` field across the docs uses **IDs**, not filenames (e.g.,
  `vkdownloader-overview.md` lines 7–10 reference `vkdownloader-installation`, `vkdownloader-api-reference`,
  `configuration-guide` — all IDs).
- `overview.md` is neither a valid ID nor a valid filename in this project.

### Issue 7: `docs/01-tools/installation.md` lines 101, 107 — ruff commands omit `tests/`

**Claim:** Ruff commands show `src/` only; should be `src tests`.

**Verification:** CONFIRMED.
- Line 101: `uv run ruff check src/` — missing `tests`
- Line 107: `uv run ruff format --check src/` — missing `tests`
- Project gates (plan §2.1, lines 178–179): `ruff check src tests` and `ruff format --check src tests`
- P18-B14 task YAML verification (line 168): `uv run ruff format --check src tests`
- `pyproject.toml` ruff config has no per-command exclusion of `tests/`

---

## 8. .ai/plans/ Directory — Current State and read_only Staleness

### Directory tree (top-level entries only)

```
.ai/plans/
├── _recovery/                          ← binary blobs (created by 151ea9f)
│   ├── plan12.md   (410,908 bytes)
│   ├── plan13.md   (531,010 bytes)
│   └── plan14.md   (403,014 bytes)
├── done/                               ← archived plans with renamed suffixes
│   ├── 12-filesystem-artifacts-audit-fixes_fix.md
│   ├── 12-filesystem-artifacts-audit-fixes_audit_report.md
│   ├── 12-filesystem-artifacts-p12-b2-context_a.md
│   ├── 13-cli-observability-audit-fixes_done.md
│   ├── 13-cli-observability-audit-fixes-problems.md
│   ├── 14-code-quality-audit-fixes_done.md
│   ├── 14-code-quality-audit-doc-problems.md
│   └── (28 other done/ files)
├── tasks/
│   └── P18-B14.yaml
├── 15-execution-plan.md                ← untracked (working tree)
├── 15-test-coverage-audit-fixes.md
├── 18-consolidated-audit-fixes-execution_fix.md  ← staged rename from _execution.md
└── 23-plan-14-execution.md
```

### read_only references are STALE

The plan file (line 13–17) declares:
```yaml
reads_only:
  - .ai/plans/12-filesystem-artifacts-audit-fixes.md
  - .ai/plans/13-cli-observability-audit-fixes.md
  - .ai/plans/14-code-quality-audit-fixes.md
  - .ai/audit/**
```

**None of the three `.ai/plans/1X-*.md` paths exist at root.** They have been archived to `done/`
with suffixes (`_done`, `_fix`, `_audit_report`). The original filenames no longer exist:

| Plan file | Declared path (reads_only) | Exists? | Actual location |
|---|---|---|---|
| Plan 12 | `.ai/plans/12-filesystem-artifacts-audit-fixes.md` | **No** | `done/12-filesystem-artifacts-audit-fixes_fix.md` |
| Plan 13 | `.ai/plans/13-cli-observability-audit-fixes.md` | **No** | `done/13-cli-observability-audit-fixes_done.md` |
| Plan 14 | `.ai/plans/14-code-quality-audit-fixes.md` | **No** | `done/14-code-quality-audit-fixes_done.md` |

Recovery copies exist in `_recovery/` as `plan12.md`, `plan13.md`, `plan14.md` (binary blobs created by
`151ea9f`), but these are not the paths referenced in `reads_only`.

**Additional stale references in task briefs:** The P18-B28 task brief (line 1245) references
`source_reference: .ai/plans/14-code-quality-audit-fixes.md` — this path does not exist. Similar stale
references appear in P18-B16 (line 560), P18-B17 (line 577), P18-B31 (line 598), P18-B10 (line 615),
P18-B20 (line 634), P18-B18 (line 667), P18-B19 (line 689), etc.

---

## 9. Plan File Staleness — Summary

### 9.1 P18-B14 marked in-progress but completed

- P18-B14.yaml line 5: `Status: IN PROGRESS at 468d6dd`
- Plan §4.2 line 459: "W6 reduces to: P18-B14 (in-progress)"
- **But** commit `151ea9f` (in HEAD history) completed P18-B14: fixed `__all__` (25 names now present,
  all 6 added) and `mypy src tests` → 0 errors (confirmed via `uv run mypy`).
- **Plan is stale**: P18-B14 should be marked DONE.

### 9.2 Gate table is stale

- Plan §2.1 line 179: "ruff format --check src tests | GREEN — 56 files already formatted, exit 0"
- **Reality**: RED — 5 of 56 files need reformatting (§4 above).

### 9.3 read_only references stale

- See §8 above. All three plan references point to non-existent paths.

### 9.4 Appendix R4 claim stale

- Plan appendix line 1607: "cli._render_preamble_failure still names --log-file (R4)"
- **Reality**: The `--log-file` reference was removed by `3cc2897`. The function now says
  "VKDOWNLOADER_LOG_FILE environment variable or your .env file" (§6 above).

### 9.5 Appendix __all__ claim stale

- Plan appendix line 1595: "services/downloader.py::__all__ | 20 names; 6 private names ... omitted"
- **Reality**: `__all__` now has **25 names**; all 6 omitted names are present (§2 above).

### 9.6 Appendix mypy pin claim stale

- Plan appendix line 1602: "requires-python >=3.14, ruff py314, mypy 3.14 — all agree (Ruling B >=3.14
  has landed)"
- Plan §5.1 V9 (line 513) and P18-B30 task brief: state Ruling B (>=3.14) has **not** landed and
  P18-B30 is a no-op.
- These two sections of the same plan **contradict each other** on whether `>=3.14` has landed.

---

## 10. Live mypy Error Distribution (for completeness)

The 328 errors reported by system `python -m mypy` 2.4.0 are **not** reproducible with the project's
canonical `uv run mypy` 2.1.0 (which reports 0). The non-untyped-decorator errors (6 total) by code:

| Code | Count | Files |
|---|---|---|
| `misc` | 2 | test_batch_downloader.py:807, test_cli.py:2538 |
| `operator` | 1 | test_cli.py:2538 |
| `attr-defined` | 1 | test_batch_downloader.py:811 |
| `return` | 1 | test_packaging.py:248 |
| `no-any-return` | 1 | test_packaging.py:285 |

All 322 `untyped-decorator` errors are from `@pytest.mark.asyncio` / `@pytest.fixture` decorators
on async test functions and fixture functions. These are flagged only by mypy ≥2.2 (the system 2.4.0)
and are suppressed in the project's pinned mypy 2.1.0.

**Recommendation (advisory):** If the project upgrades mypy beyond 2.1.0, add a `[[tool.mypy.overrides]]`
block for `tests.*` with `disallow_untyped_decorators = false` (the same pattern already used for
`vkdownloader.cli` at pyproject.toml line ~69) to avoid 322 spurious errors from untyped pytest-asyncio
decorators.

---

## 11. Summary of Verification Results

| # | Claim from audit problems file | Verification result |
|---|---|---|
| Fix-1 | Rule C12 violation: 5 test files unformatted after `151ea9f` | **CONFIRMED** — 5 files need `ruff format` |
| Fix-2a | P18-B14 marked in-progress but `151ea9f` completed it | **CONFIRMED** — plan P18-B14.yaml + §4.2 say in-progress; code + mypy are done |
| Fix-2b | `read_only` references point to archived/moved plans | **CONFIRMED** — 3 paths at root don't exist; archived to `done/` |
| Fix-2c | Appendix R4 claim stale (`--log-file` doesn't exist) | **CONFIRMED** — function no longer names `--log-file`; `--log-level` exists |
| Fix-3 | P18-B28 partial: `URLBackoffCoordinator` still in `downloader_throttle.py` | **CONFIRMED** — class at line 87; not in `retry_policies.py` |
| Fix-4 | `read_only` references stale | **CONFIRMED** (same as Fix-2b) |
| Doc-1 | `sanitize_title` documented but doesn't exist | **CONFIRMED** — real name is `sanitize_filename_component` |
| Doc-2 | "two commands" but CLI has three | **CONFIRMED** — `download`, `batch`, `clean-cookies` |
| Doc-3 | ffmpeg described as "direct HLS-to-MP4 conversion" | **CONFIRMED** — it's a merge engine (doc contradicts itself at lines 16 vs 286) |
| Doc-4 | `auto` + `cookie_source=BROWSER` says "No browser involvement" | **CONFIRMED** — browser IS launched |
| Doc-5 | `core/`, `app.py`, `logging.getLogger` are wrong | **CONFIRMED** — should be `src/vkdownloader/`, `cli.py`, `structlog.get_logger` |
| Doc-6 | `related: overview.md` references non-existent file | **CONFIRMED** — correct ID is `vkdownloader-overview` |
| Doc-7 | Ruff commands show `src/` only, should be `src tests` | **CONFIRMED** — at installation.md lines 101, 107 |
| mypy | `mypy src tests` should be 0 | **0 errors via `uv run mypy` 2.1.0** (project canonical). 328 errors only with system mypy 2.4.0 (version artifact) |
| plans | `.ai/plans/` directory state | Source plans (12, 13, 14) archived to `done/` with renamed suffixes; recovery copies in `_recovery/` |

**Note on the audit problems file's HEAD claim:** The audit problems file (line 5) declares
"Actual commit (HEAD): 151ea9f". The actual current HEAD is `a03f823` (2 commits ahead of `151ea9f`).
The `a03f823` commit is test-only (identifier renames in `test_cli.py` and `test_hls_downloader.py`) and
does not affect any production code, mypy results (via `uv run`), or ruff results. The audit problems file
was written against `151ea9f` and is stale relative to the current HEAD on this metadata point only.
