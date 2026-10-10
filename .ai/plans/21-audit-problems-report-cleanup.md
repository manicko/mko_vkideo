# Execution Plan 21 — Audit Problems Report Cleanup & Test Regression Fix

> **Source audit reports (read-only, to be deleted after completion):**
> - `.ai/audit/problems/05-entry-architecture-audit-fixes_audit_report.md`
> - `.ai/audit/problems/05-entry-architecture-audit-fixes_verification.md`
> - `.ai/audit/problems/06-config-audit-fixes.md`
> - `.ai/audit/problems/10-subprocess-browser-audit-fixes_audit_report.md`
> - `.ai/audit/problems/code_context_report.md` (artifact from this audit pass — to be deleted)
>
> **Code context:** Auditor (`ses_edb0959d3ffeOibpkXszg26AQq`) — four-command verification matrix (ruff check clean, ruff format clean, mypy src clean 31 files, pytest 1042 passed / 3 skipped / 1 failed).
>
> **Git HEAD:** `2a8f60b`

---

## 0. Current State

All 15 problems documented across the four audit reports have been verified against
the working tree at HEAD `2a8f60b`:

| # | Problem | Report Source | Status |
|---|---------|---------------|--------|
| 1 | `.python-version` missing, packaging tests fail | 06-config P1 | **FIXED** |
| 2 | "Python 3.10" in install.md vs `>=3.12` | 06-config P2 | **FIXED** |
| 3 | `Any` usage in config.py and cli.py | 06-config P3 | **FIXED** |
| 4 | `--max-retries` "batch command only" doc drift | 06-config P4 | **STALE** (out of scope — phase 08) |
| 5 | Package-root `__init__.py` re-exports (B7) | 05-entry P1 | **FIXED** |
| 6 | Hardcoded `300`/`300.0` timeout literals (B8) | 05-entry P2 | **FIXED** |
| 7 | `**Executor:**` in audit template (B9) | 05-entry P3 | **FIXED** |
| 8 | `VAL-` without phase-qualified format (B10 D4) | 05-entry P4 | **FIXED** |
| 9 | `AGENTS.md` reference in audit-refine.md (B10 D5) | 05-entry P5 | **FIXED** |
| 10 | `docs/STRUCT.md` missing entry-layer import cost (B13) | 05-entry P6 | **FIXED** |
| 11 | `.python-version` deleted (05-entry P7) | 05-entry P7 | **FIXED** |
| 12 | `?` corruption in cli-reference-clean.md | 10-subprocess P1 | **STILL PRESENT** (out of scope) |
| 13 | Stale path for error-handling research | 10-subprocess P2 | **STALE** (plan-description issue) |
| 14 | `ytdlp_downloader.py` omitted from STRUCT.md | 10-subprocess P3 | **FIXED** |
| 15 | Uncommitted changes to source files | 06-config add'l | **RESOLVED** |

**Conclusion:** All in-scope problems are FIXED. The two remaining items are
explicitly out of scope (Problem 4 belongs to phase 08; Problem 12 is
acknowledged pre-existing and out of scope). Problem 13 is a plan-description
accuracy issue, not a code defect.

### Test regression found during validation

Commit `a9fdd4a` ("fix(downloader): thread m3u8_url to yt-dlp child and support
worst quality (B9 route-a)") changed the `_download_with_ytdlp` function signature
to add `m3u8_url: str` as the second parameter, but did not update the
`test_download_with_ytdlp_passes_boundary` test in `tests/test_ffmpeg_utils.py`
(line 1177). This is a regression introduced by a post-verification commit, not
described in any of the four audit reports, but caught during final validation.

---

## 1. Execution Blocks

### Block 1 — Fix test regression: `test_download_with_ytdlp_passes_boundary`

- **Owner:** Implementor
- **Risk:** LOW — single test call needs one additional argument
- **File:** `tests/test_ffmpeg_utils.py`
- **Scope:** Add the `m3u8_url` argument (second positional) to the
  `_download_with_ytdlp` call at line 1177, matching the pattern used in
  `tests/test_hls_downloader.py` (line 1220: `"https://example.com/playlist.m3u8"`).
- **Acceptance criteria:**
  - `test_download_with_ytdlp_passes_boundary` passes
  - `uv run pytest tests/test_ffmpeg_utils.py -q` — all pass, 0 failures
  - `uv run ruff check tests/test_ffmpeg_utils.py` — clean
  - `uv run ruff format --check tests/test_ffmpeg_utils.py` — clean
- **Commit:** `test(ffmpeg_utils): pass m3u8_url to _download_with_ytdlp in boundary test`

### Block 2 — Delete stale audit problems report files

- **Owner:** Implementor (file operations)
- **Risk:** LOW — deleting stale problem reports with no remaining code dependencies
- **Files to delete:**
  1. `C:\py_exp\mko_vkideo\.ai/audit/problems/05-entry-architecture-audit-fixes_audit_report.md`
  2. `C:\py_exp\mko_vkideo\.ai/audit/problems/05-entry-architecture-audit-fixes_verification.md`
  3. `C:\py_exp\mko_vkideo\.ai/audit/problems/06-config-audit-fixes.md`
  4. `C:\py_exp\mko_vkideo\.ai/audit/problems/10-subprocess-browser-audit-fixes_audit_report.md`
  5. `C:\py_exp\mko_vkideo\.ai/audit/problems/code_context_report.md` (artifact from this pass)
- **Acceptance criteria:**
  - All five files removed from `.ai/audit/problems/`
  - `git status` shows them as deleted
  - No broken references caused by deletion (verified: only `code_context_report.md`
    and `19-entry-architecture-audit-fixes-execution.md` referenced them, and the
    latter is a superseded execution plan)
- **Commit:** `chore(audit): remove stale audit problems report files`

### Block 3 — Final validation

- **Owner:** Validator
- **Risk:** LOW — verification gate
- **Acceptance criteria:**
  - `uv run ruff check src tests` — clean
  - `uv run ruff format --check src tests` — clean
  - `uv run mypy src` — clean
  - `uv run pytest -q -rs` — all pass (excluding the known Windows-only skips)
  - `uv run pytest tests/test_packaging.py -q` — all pass

---

## 2. Implementation Sequence

```
Block 1 (test fix)
  → commit
  → Block 2 (delete audit files)
  → commit
  → Block 3 (final validation)
```

Blocks 1 and 2 are independent and can be done in sequence. Block 3 must run
after both commits.
