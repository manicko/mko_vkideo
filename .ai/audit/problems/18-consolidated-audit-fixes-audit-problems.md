# Audit Problems — Plan 18: Consolidated Audit Fixes Execution

**Plan file:** `.ai/plans/18-consolidated-audit-fixes-execution.md`
**Live HEAD declaration:** `468d6dd`
**Actual commit (HEAD):** `151ea9f`
**Audit date:** 2026-10-12

---

## Summary

The plan is **not complete** — P18-B14 was delivered by commit `151ea9f`, but several blocks remain pending and the commit introduced a Rule C12 violation (format gate turned RED). The plan file has not been updated to reflect P18-B14's completion, and its appendix contains stale claims about R4.

**Classification: `_fix`** (plan is valid and actionable; code fixes are needed before the plan can be archived as `_done`).

---

## 1. Plan File State — Stale (Section: Completed vs. Plan)

### 1.1 P18-B14 Marked In-Progress, Not Done

The plan (§4.2, line 59) lists P18-B14 as the "next executable block (in-progress)" but commit `151ea9f` has already completed it.

**Evidence:**
- Commit `151ea9f`: `Fix __all__ in downloader.py and resolve all mypy errors in tests (completes P18-B14)`
- `downloader.py` `__all__` (lines 56-62, 122-133): exports 6 private names with `# noqa: F401`
- `mypy src tests` → `Success: no issues found in 56 source files` (was 200 errors at `468d6dd`)
- Task file created: `.ai/plans/tasks/P18-B14.yaml`

**Expected action:** Update plan §4.2 / gate table to mark P18-B014 as DONE.

### 1.2 Stale `reads_only` References

The plan's `reads_only` list (lines 13-17) references `.ai/plans/12-*.md`, `.13-*.md`, `.14-*.md`, but these source plans have been archived and moved to `.ai/plans/done/` with renamed filenames.

**Evidence:**
- `reads_only` declares: `12-filesystem-artifacts-audit-fixes.md`, `13-cli-observability-audit-fixes.md`, `14-code-quality-audit-fixes.md`
- Actual files in `.ai/plans/`: `12-filesystem-artifacts-audit-fixes_fix.md` (archived), `13-cli-observability-audit-fixes_done.md` (archived), `14-code-quality-audit-fixes_done.md` (archived)
- The original filenames do not exist at their declared paths.

**Impact:** Anyone following the `reads_only` list will not find the referenced files at those paths.

### 1.3 Appendix Claim About R4 Is Stale

Line 1607: "cli._render_preamble_failure still names --log-file (R4)" — R4 is actually resolved.

**Evidence:**
- `src/vkdownloader/cli.py:93` contains: `"Check the VKDOWNLOADER_LOG_FILE environment variable or your .env file."`
- There is no `--log-file` reference in `cli.py`.
- See §2.2 (R4 Resolved) below.

---

## 2. Rule C12 Violation — Format Gate RED (RUNTIME-ERROR / SPEC-DEVIATION)

**Severity:** High (universal integrity gate)
**Rule violated:** C12 — "The format gate is green at entry and stays green"

Commit `151ea9f` (which completed P18-B14) left 5 test files unformatted, turning the format gate RED.

**Evidence:**
```
$ ruff format --check src tests
Would reformat: tests/test_cli.py
Would reformat: tests/test_config.py
Would reformat: tests/test_downloader_throttle.py
Would reformat: tests/test_hls_downloader.py
Would reformat: tests/test_segment_downloader.py
5 files would be reformatted, 51 files already formatted
```

All 5 files were modified by commit `151ea9f`:
```
 tests/test_cli.py                 |   8 +-
 tests/test_config.py              |  66 ++++++++--------
 tests/test_downloader_throttle.py |  13 ++--
 tests/test_hls_downloader.py      | 156 +++++++++++++++++++-------------------
 tests/test_segment_downloader.py  |  10 +--
```

The plan's gate table (§2.1) declares format GREEN at `468d6dd` (51 + 5 = 56 files formatted). At HEAD, it is RED (5 of 56 files need formatting).

**Required fix:** `uv run ruff format src tests`

---

## 3. P18-B28 Partially Complete — `downloader_throttle.py` Still Contains `URLBackoffCoordinator` (SPEC-DEVIATION)

**Severity:** High (blocking P18-B28 completion)
**Block:** W6 (P18-B28) from plan §4.2

The plan indicates P18-B28 includes a `downloader_throttle.py` split into `retry_policies.py` + remainder. Commit `723cb16` created `retry_policies.py` but `downloader_throttle.py` still contains `URLBackoffCoordinator` (line 87), meaning the split is incomplete.

**Evidence:**
- `src/vkdownloader/services/retry_policies.py` exists (created by `723cb16`)
- `src/vkdownloader/services/downloader_throttle.py:87` — `class URLBackoffCoordinator` still present
- 8 external gates pending re-measurement (per plan §4.2 W6)

**Required action:** Complete the `downloader_throttle.py` split and re-measure the 8 external gates.

---

## 4. Documentation Problems Found in `docs/`

### 4.1 Stale `sanitize_title` API Reference (DOC-UPDATE)

**File:** `docs/01-tools/api-reference.md` (lines 774, 781)

The API reference documents `sanitize_title` as a public function, but it no longer exists in the codebase.

**Evidence:**
```
Line 774: ### sanitize_title
Line 781: def sanitize_title(title: str) -> str:
```
```
$ grep -r "sanitize_title" src/
(no results)
```

A prior audit report (`.ai/audit/problems/14-code-quality-audit-doc-problems.md`) incorrectly claimed `grep sanitize_title docs/ → 0 hits`. The stale references are still present.

**Correct function name:** `sanitize_filename_component` (verify in `src/vkdownloader/url_sanitizer.py` or `filesystem_utils.py`).

### 4.2 Misleading CLI Command Count (DOC-UPDATE)

**File:** `docs/01-tools/vkdownloader-overview.md` (line 130)

The overview states "The CLI provides two commands" but the CLI actually provides three.

**Evidence:**
- `docs/01-tools/vkdownloader-overview.md:130`: "The CLI (`cli.py`) provides two commands:"
- `src/vkdownloader/cli.py`:
  - Line 358: `@app.command()` → `download` (default, unnamed)
  - Line 504: `@app.command("batch")` → `batch`
  - Line 646: `@app.command("clean-cookies")` → `clean-cookies`

**Required fix:** Update to "three commands: download, batch, clean-cookies" and document `clean-cookies`.

### 4.3 Misleading ffmpeg Description (DOC-UPDATE)

**File:** `docs/01-tools/vkdownloader-overview.md` (line 16)

The overview describes ffmpeg as doing "direct HLS-to-MP4 conversion." In reality, ffmpeg is only the merge engine for stitched segments.

**Evidence:**
- Line 16: "combines yt-dlp for stream extraction with ffmpeg for direct HLS-to-MP4 conversion"
- Line 286: `ffmpeg_utils.py - FFmpeg commands, availability probe, merge engine`
- The architecture tree (line 286) contradicts line 16 — ffmpeg is explicitly labeled "merge engine", not a direct conversion pipeline.

**Required fix:** Update line 16 to reflect that ffmpeg is the merge engine used for stitching downloaded segments.

### 4.4 Incorrect `auto` + `cookie_source=BROWSER` Table Entry (DOC-UPDATE)

**File:** `docs/11-guides/configuration.md` (line 75)

The configuration guide's comparison table states "No browser involvement" for the `auto` method with `cookie_source=BROWSER`, but the browser IS launched.

**Evidence:**
- Line 72-74: Table with rows for `yt-dlp` and `auto`, columns for `cookie_source=NONE` and `cookie_source=BROWSER`
- Line 75: `auto` + `cookie_source=BROWSER` cell says "No browser involvement"
- `src/vkdownloader/services/downloader.py`: `DownloadMethod.AUTO` case — when `settings.cookie_source != CookieSource.NONE`, calls `await _resolve_cookies(...)`, which launches the browser for cookie resolution.

**Required fix:** Update the table entry to indicate browser IS involved for `auto` + `cookie_source=BROWSER`.

### 4.5 Doc Maintenance Rules Reference Wrong Paths (DOC-UPDATE)

**File:** `docs/00-overview/doc-maintenance-rules.md` (lines 101-104)

The Output Guidelines reference incorrect paths and APIs that don't match the project.

**Evidence:**
- Line 101: `logger = logging.getLogger(__name__)` — the project uses `structlog.get_logger(__name__)`, not stdlib `logging`
- Line 101: `in core/` — the source directory is `src/vkdownloader/`, not `core/`
- Line 102: `in app.py` — the CLI module is `cli.py`, not `app.py`

**Required fix:** Update to reference `src/vkdownloader/`, `cli.py`, and `structlog`.

### 4.6 Ruff Commands in Installation Guide Omit `tests/` (DOC-UPDATE)

**File:** `docs/01-tools/installation.md` (lines 101, 107)

The installation guide shows ruff commands that only check `src/`, omitting `tests/`. This is inconsistent with the project's universal gate which checks `src tests`.

**Evidence:**
- Line 101: `uv run ruff check src/`
- Line 107: `uv run ruff format --check src/`
- The plan's universal gate (§2.1) and all verification runs use `src tests`

**Required fix:** Update to `src tests` to match the project's actual gate commands.

### 4.7 Broken `related` Link in doc-maintenance-rules.md (DOC-UPDATE)

**File:** `docs/00-overview/doc-maintenance-rules.md` (line 9, frontmatter)

The frontmatter `related` field references `overview.md`, but no file named `overview.md` exists in `docs/`. The overview document is at `docs/01-tools/vkdownloader-overview.md` with id `vkdownloader-overview`.

**Evidence:**
- Line 9: `- overview.md`
- `docs/` directory has no `overview.md` file (confirmed by directory listing)

**Required fix:** Update the `related` reference to the correct id: `vkdownloader-overview`.

---

## 5. Remaining Pending Blocks (from plan §4.2)

| Block | Task ID | Target Files | Status at HEAD |
|-------|---------|-------------|----------------|
| W6 | P18-B28 | `downloader_throttle.py` split, `retry_policies.py` | PARTIAL — `URLBackoffCoordinator` still in `downloader_throttle.py` |
| W5 | P18-B22 | plan 13 B6 — logging chain | Not started since `468d6dd` |
| W5 | P18-B23 | plan 13 B7 — logging chain | Not started since `468d6dd` |
| W5 | P18-B24 | plan 13 B4 — logging chain | Not started since `468d6dd` |
| W5 | P18-B25 | plan 13 B2 — logging chain | Not started since `468d6dd` |
| Anywhere | P18-B39 | plan 13 B14 | Not started |
| Anywhere | P18-B40 | plan 13 B15 | Not started |

Only 2 commits landed since `468d6dd`:
- `81ac327` — chore(plan): archive plan 21 as completed (no code changes)
- `151ea9f` — P18-B14 completion + format regression

No commits addressed any of the pending blocks above.

---

## 6. Test Results Summary

| Gate | Result at `468d6dd` | Result at HEAD (`151ea9f`) | Status |
|------|---------------------|---------------------------|--------|
| `ruff check src tests` | PASS | PASS | OK |
| `ruff format --check src tests` | GREEN (56 files) | RED (5 files) | **VIOLATION** (C12) |
| `mypy src tests` | 200 errors | 0 errors (56 files) | OK (P18-B14 fixed) |
| `pytest` | — | 1097 passed, 3 skipped | OK |

---

## Required Fixes

1. **Ruff format:** Run `uv run ruff format src tests` to fix 5 test files (Rule C12)
2. **Plan file:** Update §4.2 and gate table to mark P18-B14 as DONE; fix `reads_only` paths; correct appendix R4 claim
3. **P18-B28:** Complete `downloader_throttle.py` split; move `URLBackoffCoordinator` to `retry_policies.py` or complete the remainder split
4. **Docs — `api-reference.md`:** Replace `sanitize_title` with `sanitize_filename_component` (lines 774, 781)
5. **Docs — `vkdownloader-overview.md`:** Fix command count (line 130: "two" → "three"); fix ffmpeg description (line 16: "direct HLS-to-MP4 conversion" → "merge engine for stitching segments")
6. **Docs — `configuration.md`:** Fix `auto` + `cookie_source=BROWSER` table entry (line 75: "No browser involvement" → browser IS involved)
7. **Docs — `doc-maintenance-rules.md`:** Fix paths/APIs (lines 101-104): `core/` → `src/vkdownloader/`, `app.py` → `cli.py`, `logging.getLogger` → `structlog.get_logger`; fix `related: overview.md` → `vkdownloader-overview` (line 9)
8. **Docs — `installation.md`:** Fix ruff commands (lines 101, 107): `src/` → `src tests`
