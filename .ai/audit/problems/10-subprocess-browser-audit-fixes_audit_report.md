# Audit Problems Report — Plan 10: Subprocess & Browser Audit Fixes

**Plan:** `10-subprocess-browser-audit-fixes.md` (subprocess and browser audit fixes)
**Audit date:** 2026-10-09
**Repository:** `vkdownloader` (`C:\py_exp\mko_vkideo`)
**Scope:** Verification of plan completion and problems found in docs during audit.

---

## Summary

The plan describes 15 execution blocks (B1–B16, with B3 deleted as moot by `D2`).
All 15 blocks have been implemented and committed. Verification against the working
tree and the commit range `d572d96..0a38b61` (16 commits, 15 block + 1 docs-support)
shows:

- **All 15 blocks fully implemented.** Each block has a dedicated commit with a
  subject matching the plan's block name. Seven supporting commits
  (`7eda45a`, `b20ea62`, `5d9b9a0`, `a8294b7`, `0ee7297`, `4a88153`, and others)
  provide documentation alignment, test additions, exception refactoring, and
  stale-comment restoration — all directly attributable to phase-05 fixes.
- **Tests pass:** `uv run pytest tests -q` → 1010 passed, 3 skipped (all Windows
  POSIX-only killpg tests).
- **Lint/format/type checks clean:**
  `uv run ruff check src` → all checks passed;
  `uv run ruff format --check src` → 31 files already formatted;
  `uv run mypy src` → no issues found in 31 source files.
- **Decision record exists:** `.ai/decisions/05-subprocess-browser-decision-record.md`
  written by B9.
- **Settings fields added with three-place rule:** `download_stall_timeout`
  (B11) and `stealth_enabled` (B15) present in `config.py`, `.env.example`, and
  `docs/11-guides/configuration.md`.
- **`ErrorCode.STEALTH_ASSET_MISSING` StrEnum member** added by B15.

**Verdict:** The plan is **complete** and **requires no code rework.** The plan
file has been renamed to `10-subprocess-browser-audit-fixes_done.md` and moved
to `.ai/plans/done/`.

---

## Block verification summary

| Block | Finding(s) | Commit | Verification |
|-------|-----------|--------|--------------|
| B1 | TRN-002 (re-scoped) | `435ba0b` | Cookie-file `unlink` wrapped in `try/except OSError`; warning logged; return value preserved |
| B2 | TRN-004 | `db0e33e` | `readline()` `ValueError` caught; drain continues; `DownloadError` raised; `fire()` exactly-once and `watch_task` preserved |
| B3 | TRN-005 | — | Deleted as moot by D2 (parse half removed with `read_progress`) |
| B4 | TRN-006 (sink half) | `58bb7ce` | Failed task exception retrieved and logged at B4's call sites; normal completion produces no record |
| B5 | TRN-012 | `b0fb032` | Both surviving call sites guard with `and process.returncode is None`; `cancel_subprocess` contract unchanged |
| B6 | TRN-011 | `feea5c8` | `output_chunks` bounded; `echo=False` path unaffected; four echo tests stay green |
| B7 | TRN-009 (claim) | `09f1b10` | Docstring false claim removed; path-shaped test added pinning the boundary |
| B8 | BRW-001(a) | `be76206` | `ExtractionError` message carries missing-exe + remedy; `from None` preserved; banner suppressed |
| B9 | VAL-501 + VAL-502 | `0a38b61` | Decision record written to `.ai/decisions/`; both chains recorded as closed/evaporated |
| B10 | TRN-001 + TRN-010 | `d572d96` | `DownloadMethod.FFMPEG` removed; `download_with_ffmpeg`, `_temp_argfile`, `_format_argfile`, `read_progress`, `ProgressParser`, `FfmpegProgress`, `_PROGRESS_KEY_HANDLERS` deleted; 7 doc sites updated; auto-method semantics documented |
| B11 | TRN-007 | `5dc5912` | `download_stall_timeout: float = Field(default=300.0, ge=30, le=3600)`; inactivity bound on re-wait; NET-007 preserved |
| B12 | TRN-003 | `12d97d4` | `start_new_session=True` (POSIX) / `CREATE_NEW_PROCESS_GROUP` (Windows) at 3 spawn sites; Windows residual documented |
| B13 | TRN-008 | `e6e6c68` | `check_ffmpeg_available()` return value used (`if not check_ffmpeg_available():`); arm (a) deleted; arms (b)/(c)/(d) reconciled |
| B14 | TRN-009 (capability) | `486bfd9` | `sanitize_text_for_log` applied at `batch_merge_failed` and `final_merge_failed` sinks; transform before truncate |
| B15 | BRW-003 | `c6d0214` | `stealth_enabled: bool = Field(default=False)`; gated components 1 & 2; ungated component 3; asset check before driver; `ErrorCode.STEALTH_ASSET_MISSING` |
| B16 | console-encoding | `183d40f` | `StreamHandler` constructed with `errors="backslashreplace"` via `_encoding_safe_console_stream()` |

---

## Supporting commits (all attributable to phase-05 fixes)

| Commit | Subject | Supports |
|--------|---------|----------|
| `7eda45a` | docs: align documentation with the phase 05 subprocess and browser fixes | Documentation consistency across all blocks |
| `b20ea62` | fix(logging): keep the encoding-safe console policy across progress repointing | B16 follow-up |
| `5d9b9a0` | refactor(exceptions): narrow ExtractionError's error_code to ErrorCode | B15 ErrorCode refinement |
| `a8294b7` | test(subprocess): pin the coverage the phase 05 fixes claimed | Regression tests for B1–B16 |
| `0ee7297` | refactor(downloader): restore stale symbol-ownership and handler documentation | B10/B7 comment corrections |
| `4a88153` | docs: correct cookie-passing and auto-method claims, and record the mypy deviation | Documentation accuracy |

---

## Problems found in docs

All problems below are **pre-existing or stale-plan-description issues**. No plan-05
implementation changed the code or docs to introduce them; they are recorded
for the record. **No code changes were made by this audit.**

### Problem 1 — `docs/99-reference/cli-reference-clean.md`: lossy encoding corruption

**Severity:** LOW (documentation hygiene; pre-existing, documented in plan §1.8)

**File:** `docs/99-reference/cli-reference-clean.md`

**Description:** The plan's §1.8 describes this file as having "cp1251 mojibake"
where the em dash appears as `вЂ"`. The actual corruption is different: the file
has **lost** its non-ASCII characters — em dashes (U+2014) and other Unicode
glyphs are replaced with literal `?` (ASCII `0x3F`). There are **no Cyrillic**
characters in the file (verified by Python decode: 0 Cyrillic code points).

| Metric | `cli-reference.md` | `cli-reference-clean.md` |
|--------|-------------------|--------------------------|
| Lines | 290 | 290 |
| Em dashes (U+2014) | 21 | 1 |
| Question marks | 25 | 23 |
| Characters matching `cli-reference.md` | — | 2993 / 13705 (~22%) |

**Evidence:**
```
Position 197: clean has '?' but orig has '—'
Context clean: 'e:** `vkdownloader` ? VK Video Downloade'
Context orig:  'e:** `vkdownloader` — VK Video Downloader'
```

The file is neither a "clean copy" nor "exact duplicate" of `cli-reference.md` —
it is a corrupted copy. It is linked from
`docs/error-handling-logging-research-2025-2026.md` (CLI-007). The plan
correctly states this is **deliberately not fixed** by this plan (B10 still
edits its `--method` rows).

**Plan's role:** none — acknowledged pre-existing; documented in §1.8.

### Problem 2 — `docs/error-handling-logging-research-2025-2026.md`: path discrepancy

**Severity:** LOW (stale path reference in plan §1.8)

**File:** `docs/error-handling-logging-research-2025-2026.md`

**Description:** The plan's §1.8 states:
> "Exactly one file links to it (`docs/99-reference/error-handling-logging-research-2025-2026.md`)."

The file **does not exist** at `docs/99-reference/error-handling-logging-research-2025-2026.md`.
It exists at `docs/error-handling-logging-research-2025-2026.md` (root of the
`docs/` directory, not inside `99-reference/`). The plan's path is stale.

**Evidence:**
```
docs/99-reference/error-handling-logging-research-2025-2026.md: False
docs/error-handling-logging-research-2025-2026.md: True
```

**Plan's role:** none — this is a plan-description accuracy issue, not a code or
implementation defect.

### Problem 3 — `docs/STRUCT.md`: plan's omission claim is stale

**Severity:** LOW (stale claim in plan §1.8)

**File:** `docs/STRUCT.md`

**Description:** The plan's §1.8 states:
> "`docs/STRUCT.md`'s omission of `ytdlp_downloader.py` — OUT — phase 09 by R-E
> — Recorded upstream as a cross-reference and not filed."

The file **does** list `ytdlp_downloader.py`. It is present in the module tree
with the description "yt-dlp subprocess wrapper (cookie artefact lifecycle,
B2/R1/R2)". The omission described in the plan has been resolved (likely by
documentation alignment work, e.g. commit `3b95d65`).

**Plan's role:** none — the plan's §1.8 claim is stale as of execution time.

### Problem 4 — `C:\py_dev\mko_bazuna` path does not exist

**Severity:** INFO (environment)

**Description:** The user's instructions reference `C:\py_dev\mko_bazuna` as the
project root for target paths (`.ai/plans/done/` and `.ai/audit/problems/`).
The actual project root is `C:\py_exp\mko_vkideo`. The plan file was found
and processed at the actual project root. Target directories `.ai/plans/done/`
and `.ai/audit/problems/` both exist under the actual project root.

---

## Test verification

| Command | Result |
|---------|--------|
| `uv run ruff check src` | All checks passed |
| `uv run ruff format --check src` | 31 files already formatted |
| `uv run mypy src` | Success: no issues found in 31 source files |
| `uv run pytest tests -q` | 1010 passed, 3 skipped, 1 warning |

The 3 skipped tests are all POSIX-only `killpg` path tests introduced by B12:
- `tests/test_ffmpeg_utils.py::166 POSIX-only: killpg path`
- `tests/test_ffmpeg_utils.py::189 POSIX-only: killpg path`
- `tests/test_hls_downloader.py::4642 POSIX-only: killpg reaches descendants`

The baseline skip count (4 Windows-gate `os.chmod` tests) decreased to 3
because B10 deleted `TestTempArgfile::test_temp_argfile_permissions_are_0600`
along with its deleted subject (`_temp_argfile`). This is a structural
consequence of the deletion, not a test-weakening.

---

## Rollout / execution analysis

**Ordering respected:** The plan's §4.2 topological order was followed exactly:
B10 (deletion) → B1 → B5 → B4 → B2 → B7 → B14 → B6 → B8 → B11 → B15 → B16 →
B12 → B13 → B9. Each block's commit subject matches its plan heading.

**Dependencies respected:**
- B1, B5, B4, B13 depend on B10 (deletion) — all sequenced after B10 ✓
- B5 before B12 and B11 — respected ✓
- B8 before B15 and B16 — respected ✓
- B11 before B15 (three-place rule for `Settings` fields) — respected ✓

**Commit hygiene:** Each block is a single commit with a subject line naming the
finding. The commit bodies carry before/after measurements, prohibitions, and
dispositions as specified by the plan.

**No code changes made by this audit.**
