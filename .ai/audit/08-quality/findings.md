---
name: 08-quality-findings
description: Phase 08 audit findings — Code Quality, Security & Maintainability
agent: auditor
template: .ai/audit/templates/audit-findings.md
status: complete
validated: no
---

# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Summary

| Step | Command | Result |
|------|---------|--------|
| R1 — Linter | `uv run ruff check src/` | All checks passed (no errors) |
| R1 — Type check | `uv run mypy src/` | Success: no issues in 23 source files (strict mode) |
| R2 — Tests | `uv run pytest tests/` | 217 passed in 13.50s |
| R3 — Dead code | grep for unused methods/params/imports | 2 confirmed unused methods, 1 unused param, stray files |
| R4 — Security | grep for secrets / `print()` / bare `except:` | No hardcoded secrets; no bare `except:`; `print()` only in stray scratch files; `except Exception` uses are guarded re-raise or redaction patterns |

> Note: lint/type/test all pass, so the findings below are maintainability/structure
> issues discovered during manual review and targeted dead-code searches, not
> CI-failing defects.

---

## Findings

### QLT-001: `downloader.py` re-exports 25+ symbols it does not own

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py`, `tests/test_hls_downloader.py` |
| **Classification** | advisory |

**Description:** `downloader.py` imports a large set of functions from sibling
modules (`segment_downloader.py`, `ffmpeg_utils.py`, `downloader_throttle.py`,
`cookies.py`, `signal_handlers.py`) and re-lists them in its `__all__` block
(lines 208–232), presenting them as if `downloader.py` were their owner. Examples
that are *defined elsewhere* but re-exported here: `download_hls_with_resume`
(segment_downloader), `_download_segment*`, `_parse_m3u8_segments`,
`_load/_save_downloaded_count`, `_cleanup_segments`, `_fetch_playlist_with_retry`,
`_retry_429_with_backoff` (downloader_throttle), `_cookies_to_netscape` (cookies),
`setup_signal_handlers` (signal_handlers), `cancel_ffmpeg_process` /
`read_progress` / `_merge_segments_batched` / `_build_ffmpeg_concat_command`
(ffmpeg_utils).

This confuses module ownership and violates the project's "strict separation of
concerns" and layer-boundary conventions. The symptom is visible in the test
suite: `tests/test_hls_downloader.py` imports `download_hls_with_resume` from
`vkdownloader.services.downloader` (lines 11–20, 489, 541, 584, 731, 809, 879)
even though the function is defined in `segment_downloader.py`. Tests therefore
depend on a re-export facade rather than the real module, so moving code between
modules silently changes the test import paths' correctness.

**Evidence:**
- `src/vkdownloader/services/downloader.py:36-47` — imports of foreign symbols.
- `src/vkdownloader/services/downloader.py:208-232` — `__all__` listing 25+ names.
- `tests/test_hls_downloader.py:11-20, 489` — `from vkdownloader.services.downloader import download_hls_with_resume` (defined in `segment_downloader.py`).

**Recommendation:** Stop using `downloader.py` as a re-export facade. Remove the
foreign symbols from `downloader.py`'s imports and `__all__`, and have callers and
tests import directly from the owning module (e.g. `from vkdownloader.services.segment_downloader import download_hls_with_resume`). Keep `downloader.py` owning only `perform_download`, `HLSDownloader`, and its genuine helpers (`_build_ytdlp_options`, `_await_first_and_cancel_others`, `_parse_quality_to_enum`, `_resolve_cookies`).
- **Effort:** small
- **Priority:** recommended (not mandatory)

---

### QLT-002: Dead code — `ProgressManager.update()` and `get_progress()` never called

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `ProgressManager` exposes four public methods. Only `update_sync()`,
`get_formatted_progress()`, and `clear()` are used (by `cli.py`). The async
`update()` (lines 94–103) and `get_progress()` (lines 143–153) have zero call
sites anywhere in `src/` or `tests/` (grep for `.update(` and `get_progress(`
returns only the definitions). They are dead code that adds maintenance surface
and misleads readers about which progress path is actually live (sync callback
vs async).

**Evidence:**
- `src/vkdownloader/services/downloader_throttle.py:94-103` (`update`) and `:143-153` (`get_progress`) — defined, never invoked.
- Grep across `src/` and `tests/`: only the definitions match; no call sites.

**Recommendation:** Remove `update()` and `get_progress()` (and their docstrings),
or, if async progress updates are a planned feature, document the intent in a
TODO rather than leaving silently-dead public API. Aligns with the project's
"small modules/functions" and dead-code policies.
- **Effort:** trivial
- **Priority:** recommended (not mandatory)

---

### QLT-003: Unused function parameter `duration_ms` in `read_progress`

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py` |
| **Classification** | advisory |

**Description:** `read_progress()` declares `duration_ms: int | None = None`
(lines 64–68) and its docstring claims it is used "for percentage calculation".
The body never references `duration_ms`, and no percentage is computed — consumers
compute progress externally or not at all. The dead parameter is misleading and
violates the "no speculative abstractions / no unused code" guidance.

**Evidence:**
- `src/vkdownloader/services/ffmpeg_utils.py:64-97` — `duration_ms` declared but unused in the function body; no percentage logic present.

**Recommendation:** Remove the `duration_ms` parameter and the corresponding
docstring line. If percentage progress is a genuine future requirement, track it
as an explicit TODO rather than a no-op parameter.
- **Effort:** trivial
- **Priority:** recommended (not mandatory)

---

### QLT-004: Stray scratch files at repo root and in `.temp/`

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | repo root (`cli_ruff_output.txt`), `.temp/deadcheck.py`, `dist/` |
| **Classification** | advisory |

**Description:** The repository contains leftover developer scratch artifacts that
are not part of the documented source/test/docs layout and violate project
conventions:
- `cli_ruff_output.txt` (root) — an old ruff report referencing now-deleted files
  `cli_test.py` / `cli_test2.py`, which themselves used `print()` (forbidden by
  project rule 11) and failed import-sort checks.
- `.temp/deadcheck.py` — a scratch AST dead-code script that uses `print()`
  directly (project rule 11: "No print() statements; use logging") and is not
  referenced anywhere.
- `dist/` — build artifact directory committed/scattered at root.

These files clutter the repo, can confuse tooling/globbers, and `deadcheck.py`
directly breaks the "no print()" rule.

**Evidence:**
- Root listing shows `cli_ruff_output.txt` (1078 bytes); its content references deleted `cli_test.py`/`cli_test2.py` containing `print(...)`.
- `.temp/deadcheck.py:1` — uses `print(...)` (line 30), not logging.

**Recommendation:** Delete `cli_ruff_output.txt`, `.temp/deadcheck.py`, and the
stray `dist/` directory; add `.temp/` and `dist/` to `.gitignore` if such scratch
output is generated locally. Keep the repository limited to the documented layout
(src, tests, docs, .kilo, .ai).
- **Effort:** trivial
- **Priority:** recommended (not mandatory)

---

### QLT-005: Duplicated `download_timeout` default constant

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** The download timeout default of `300` seconds is defined twice:
- `Settings.download_timeout` default `300` in `config.py:41-46`.
- `DEFAULT_DOWNLOAD_TIMEOUT = 300` in `downloader_throttle.py:17`, with the
  comment "matches Settings.download_timeout default".

These are two independent sources of truth for the same value. If one is changed
(e.g. the Pydantic default), the other silently drifts, producing inconsistent
timeouts depending on which code path sets the value. This is a classic
"magic-number duplication" smell.

**Evidence:**
- `src/vkdownloader/config.py:41-46` — `download_timeout: int = Field(default=300, ...)`.
- `src/vkdownloader/services/downloader_throttle.py:17` — `DEFAULT_DOWNLOAD_TIMEOUT = 300`.

**Recommendation:** Make `downloader_throttle.py` read the value from
`Settings.download_timeout` (it already receives `settings` in the call paths) and
delete the local `DEFAULT_DOWNLOAD_TIMEOUT` constant, or export it from a single
shared constants module. Single source of truth prevents drift.
- **Effort:** trivial
- **Priority:** recommended (not mandatory)

---

### QLT-006: BEST/WORST quality selection can pick a `height=None` (zero-height) stream

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/quality.py`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `_get_fallback_stream()` (used for `BEST`) does
`max(streams, key=lambda s: s.height or 0)` (quality.py:45), and `WORST` does
`min(streams, key=lambda s: s.height or float("inf"))` (quality.py:70). When a
stream has `height=None` (the default for the browser-extracted "best" stream —
see `extractor.py:222-230`, which appends a `Stream` with `height=None`), the
`or 0`/`or float("inf")` fallback collapses the resolution into a sentinel value.

Concrete consequence: for `BEST`, if the only available stream is the
browser-extracted `Stream(quality="best", height=None)`, `max` returns it (height
treated as 0). That is fine in isolation, but if a real low-resolution stream
(e.g. height=240) co-exists with the `None` stream, `max` returns the `None`
stream over the 240 one only when ordering ties at 0 — i.e. resolution is not
actually maximized, and selection becomes order/coverage dependent. The absence of
explicit `None` handling means "unknown height" is silently ranked as "zero /
infinite", which is semantically wrong.

**Evidence:**
- `src/vkdownloader/services/quality.py:35-45` (`_get_fallback_stream`) and `:66-71` (`BEST`/`WORST`).
- `src/vkdownloader/services/extractor.py:222-230` — browser path appends `Stream(url=..., format=HLS, quality="best", width=None, height=None)`.

**Recommendation:** Treat `height is None` explicitly: either exclude `None`-height
streams from BEST/WORST ranking, or sort with a defined policy (e.g. fallback to
`width`, then to stream order). Add a regression test covering mixed
`height=None` + numeric-height inputs so resolution ranking cannot regress.
- **Effort:** small
- **Priority:** recommended (not mandatory)

---

### QLT-007: `Any` type usage confined to yt-dlp boundary (rule 9 "avoid Any completely")

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** Project rule 9 ("Type Safety Everywhere") states to avoid `Any`
completely. `downloader.py` uses `Any` in four places, all at the yt-dlp boundary:
- `asyncio.Task[Any]` (lines 81–82)
- `dict[str, Any]` return of `_build_ytdlp_options` (line 139)
- `ydl_opts: dict[str, Any]` (line 161)
- `dict[str, Any]` progress hook param (line 194)

These are the external `yt_dlp.YoutubeDL` option dict and progress-hook payload,
which are untyped third-party structures. mypy strict passes because they are
isolated. Still, per the project's hard "no Any" rule, these are the only `Any`
occurrences in the whole `src/` tree and could be tightened.

**Evidence:**
- `src/vkdownloader/services/downloader.py:11, 81-82, 139, 161, 194` — `Any` used only at the yt-dlp integration boundary.

**Recommendation:** Where feasible, replace `dict[str, Any]` with a `TypedDict`
describing the small set of yt-dlp option keys actually used, and type the
progress-hook payload explicitly (yt-dlp's hook dict has known string keys). If a
fully typed shape is impractical at the boundary, add a single documented
`# type: ignore`/explicit comment explaining why `Any` is unavoidable, so the
deviation from rule 9 is visible and justified rather than incidental.
- **Effort:** small
- **Priority:** recommended (not mandatory)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 6 |

## Mandatory Fixes

None. All findings are advisory (maintainability/structure improvements). No
security vulnerabilities, data-loss risks, or correctness defects were found in
this phase.

## Advisory Recommendations

- **QLT-001** (MEDIUM): Remove `downloader.py` re-export facade; import from owning modules.
- **QLT-002** (LOW): Delete unused `ProgressManager.update()` / `get_progress()`.
- **QLT-003** (LOW): Remove unused `duration_ms` param from `read_progress`.
- **QLT-004** (LOW): Delete stray scratch files (`cli_ruff_output.txt`, `.temp/deadcheck.py`, `dist/`).
- **QLT-005** (LOW): De-duplicate `download_timeout` default constant.
- **QLT-006** (LOW): Handle `height=None` explicitly in BEST/WORST selection.
- **QLT-007** (LOW): Tighten `Any` at the yt-dlp boundary per rule 9.

## Doc Updates Needed

None required. No documentation was found to diverge from the code in this phase
(the stray `cli_ruff_output.txt` is a scratch artifact, not documentation).

---

## Verification Notes

- `uv run ruff check src/` → "All checks passed!"
- `uv run mypy src/` (strict) → "Success: no issues found in 23 source files"
- `uv run pytest tests/` → 217 passed
- No hardcoded secrets, no bare `except:`, and no `print()` in `src/` (only in
  stray `.temp/deadcheck.py` and the deleted `cli_test*.py` referenced by the
  stale `cli_ruff_output.txt`).
