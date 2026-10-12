# Audit update: Plan 14 code-quality audit — live tree at HEAD `24dcddc`

**Auditor:** Kilo (senior staff architecture auditor)
**Date:** 2026-10-11
**Plan base:** `09f1b10` (`.ai/plans/14-code-quality-audit-fixes_fix.md`)
**Previous audit:** §9 "Audit update (2026-10-10)" at `2289f6f`
**Live HEAD:** `24dcddc` — 29 commits past the §9 baseline

## Summary

**No plan-14 block has been executed since the §9 audit.** All 13 blocks retain their §9 status, with two material changes caused by commits that landed *outside* this plan:

1. **Commit `6ab4a50` (`chore clean structure.md`)** deleted `docs/STRUCT.md` and `docs/error-handling-logging-research-2025-2026.md` but did **not** update `EXPECTED_SDIST_ENTRIES` in `tests/test_packaging.py`. This breaks the packaging tests (73 expected entries vs 71 actual). → **CRITICAL**
2. **Commit `6bd3188`** renamed `sanitize_title` → `sanitize_filename_component`, creating new staleness in `vkdownloader-overview.md` (B8 scope widened).
3. **P10/P12 external gates** have landed (segment_downloader refactoring, partial-file probe), but **P11 (ytdlp_downloader.py retry infrastructure) has not**. B4 remains blocked.

---

## Block-by-block status at HEAD `24dcddc`

| Block | §9 status (at 2289f6f) | Current status | Key evidence |
|---|---|---|---|
| B1 | NOT DONE | NOT DONE | exceptions.py still defines `_map_exception_to_status` (L216), `_EXCEPTION_STATUS_HANDLERS` (L240), `_quality_not_available_status` (L232); `ErrorCode.NO_STREAMS` absent; module docstring (L4-8) still advertises the shim |
| B2 | NOT DONE | NOT DONE | cli.py imports no `VKDownloadError` (L31-36); terminal `except Exception` arms at L486-490 and L609-614 use `logger.exception` without `log_context()`; `D3` unsettled |
| B3 | NOT DONE | NOT DONE | `pyproject.toml`: `requires-python=">=3.12"` (Ruling B says ≥3.14); no `disallow_any_explicit`; `target-version="py312"`, `python_version="3.12"` |
| B4 | NOT DONE | NOT DONE | All retry symbols still in `downloader_throttle.py`: `RETRYABLE_STATUS_CODES` (L53), `_retry_429_with_backoff` (L230), `_parse_retry_after` (L333), `_compute_backoff_delay` (L376), `_wait_with_shutdown` (L417). External gates: P10 ✓ LAND, P12 ✓ LAND, P11 ✗ NOT LAND |
| B5 | DONE | DONE | Commit `83ba0f8` documented Retry-After as floor; no change since |
| B6 | PARTIAL | **VOIDED** | `docs/STRUCT.md` was **deleted** by commit `6ab4a50` (not by B6). B6's entire premise — correcting rows in this file — is voided. `py_map.yaml` still has 23/31 modules + phantom symbols |
| B7 | NOT DONE | NOT DONE | `py_map.yaml`: 23 of 31 modules (7 missing); Windows-backslash `.ai/builders\..\..\src\` paths; phantom `HLSDownloader`, `_parse_quality_to_enum` in downloader.py entry; duplicate `__init__` in downloader_throttle.py entry; stale `playwright.async_api` import. `map.md`: lists 5 non-existent `.pyc` files, includes `egg-info/`, uses wrong drive letter (`C:\PY_EXP`) |
| B8 | PARTIAL | PARTIAL — **WORSENED** | 4 stale line counts drifted further since §9 audit; new `sanitize_title`→`sanitize_filename_component` staleness (6bd3188); universal-export claim (L292) survives; `ffmpeg_utils.py` listing (L286) still says "FFmpeg commands, process management" |
| B9 | NOT DONE | NOT DONE | `cli-reference-clean.md` still exists (208 lines); `docs/error-handling-logging-research-2025-2026.md` **deleted** by 6ab4a50 (B9 step 7 now moot); `D11` unresolved |
| B10 | NOT DONE | NOT DONE | `morfx-tools.md` (431 lines) and `ast-editor.md` (31 lines) still shipped; both describe non-existent mkobi MCP tooling |
| B11 | NOT DONE | NOT DONE | All 23 citation sites intact: 10 in src/ (INT-003×3, INT-004×2, INT-006×2, INT-008×1, STR-008×1, SRV-006×1), 10 in tests/ (+INT-007×1), 3 in docs/ (SRV-006×2, SRV-001×1). No new tokens |
| B12 | NOT DONE | NOT DONE | `models/quality.py` line 13: `from .enums import QualityKind, QualityLabel` — mixed import form undocumented (D14b: documented exception) |
| B13 | NOT DONE | NOT DONE | No escalation report produced; `VAL-901` (CRITICAL) and `VAL-902` remain unimplemented |

---

## B1 — `exceptions.py` (QLT-001 + QLT-010)

**Status:** NOT DONE — all §1/B1 acceptance criteria unmet.

**Evidence (HEAD 24dcddc):**

| Symbol | Location | Status |
|---|---|---|
| `_map_exception_to_status` | `exceptions.py:216` | **Still defined.** Module docstring `exceptions.py:6` names it. `README.md:157` also advertises it. |
| `_EXCEPTION_STATUS_HANDLERS` | `exceptions.py:240` | **Still defined.** Uses `Callable[..., str]` (implicit `Any` — also a B3 issue). |
| `_quality_not_available_status` | `exceptions.py:232` | **Still defined.** Only called from `_EXCEPTION_STATUS_HANDLERS`. |
| `ErrorCode.NO_STREAMS` | `models/enums.py:63-79` | **Absent.** 9 members listed; no `NO_STREAMS`. |

**Production call-site census:** `_map_exception_to_status` has **zero** production callers (definition only). The only callers are in `tests/test_exceptions.py` (14 references: lines 11, 17, 22, 28, 37, 44, 51, 57, 63, 70, 76, 201, 206, 218) and a single comment at `batch_downloader.py:303`.

**README.md:157** still reads: "The legacy `_map_exception_to_status()` helper and `_EXCEPTION_STATUS_HANDLERS` dict are retained for backward compatibility." This is outside B1's src/-only gate but is a stale documentation site.

## B2 — `cli.py` exception ladders (QLT-002)

**Status:** NOT DONE.

**Evidence:**

- `cli.py:31-36` imports **no** `VKDownloadError` — only `InvalidVideoUrlError`, `QualityNotAvailableError`, `QualityParseError`, `VideoNotFoundError`.
- `cli.py::download` ladder (L447-490): terminal `except Exception:` at L486-490 calls `logger.exception("download_failed", url=sanitize_url_for_log(url))` — no `**e.log_context()`, no `error_code` field.
- `cli.py::batch` ladder (L598-614): terminal `except Exception:` at L609-614 calls `logger.exception("batch_download_failed", url_file=..., url_count=...)` — no structured context.
- `D3` (`\error` vs `\error(..., exc_info=True)` vs `\error`) is **unsettled**. The plan requires settlement against phase-08's `OUT-002` evidence record, which has not been done.
- `D4` (`user_message()` adopt vs delete) is **unsettled**.
- **External dependency:** §5.2 criterion 10 requires "Plan 11 B6 has landed" (serialised before B2). No P11 commit is visible in the git log since 2289f6f.

## B3 — `pyproject.toml` type gate (QLT-009)

**Status:** NOT DONE.

**Evidence:**

- `pyproject.toml` `[tool.mypy]` has **no** `disallow_any_explicit` flag.
- `pyproject.toml` `[project] requires-python` = `">=3.12"` — Ruling B (Python floor ≥3.14) not enforced.
- `pyproject.toml` `[tool.ruff] target-version` = `"py312"` — stale per D16.
- `pyproject.toml` `[tool.mypy] python_version` = `"3.12"` — stale per D16.
- Three version declarations all say 3.12 (requires-python, target-version, python_version); Ruling B requires ≥3.14.
- `tests/test_exceptions.py` has two `# type: ignore` comments (per §2.3 line 468) — the plan's "0" was false.

## B4 — `downloader_throttle.py` split (QLT-011)

**Status:** NOT DONE. External gates **partially landed**.

**Five retry symbols still in `downloader_throttle.py`:**

| Symbol | Line | Planned new home |
|---|---|---|
| `RETRYABLE_STATUS_CODES` | 53 | New retry module |
| `_retry_429_with_backoff` | 230 | New retry module |
| `_parse_retry_after` | 333 | New retry module |
| `_compute_backoff_delay` | 376 | New retry module |
| `_wait_with_shutdown` | 417 | New retry module |

**Residue that stays (7 importers):** `get_shutdown_event` (L76), `URLBackoffCoordinator` (L98), `ProgressManager` (L159), `_resource_key` (L56).

**External gate status (§4.2 line 1019, §5.4):**

| Gate | Description | Status |
|---|---|---|
| P10 — Plan 12 segment_downloader track (P12-B6, B7, B8) | `segment_downloader.py` refactoring to shared subprocess spawn boundary | ✅ **LANDED** — commits `e2c5ad0`, `40404e2` |
| P12 — Partial-file probe repoint | Commit `767bb47` (P12-B9) repointed the probe to yt-dlp's `.part` temp name | ✅ **LANDED** — commit `767bb47` |
| P11 — Plan 11 ytdlp_downloader.py track (B2, B5) | Retry infrastructure refactoring in `ytdlp_downloader.py` | ❌ **NOT LANDED** — no P11 commits in the log since 2289f6f |

**Facade defect (§4.4 row 25, §2.5 correction 12):** Per §9.2 voided assertion #4, the four deleted groups were restored by commit `0ee7297` (before 2289f6f). The current `downloader.py:88-107` comment lists 7 groups. However, B4's criterion 6 still requires: the comment names every module that owns a name in `__all__`, `_attempt_segment_resume` is either added to `__all__` or removed from the comment (it is imported at L49 with `# noqa: F401` but absent from both `__all__` and the comment), and `mypy src tests` no longer reports the "does not explicitly export" error for it. The remaining 27 such mypy errors are owned by plan 18 (§9.2).

## B5 — Retry-After floor comment (QLT-013)

**Status:** DONE.

Commit `83ba0f8` documented Retry-After as a floor. The `_compute_backoff_delay` function's comment at `downloader_throttle.py:376` now states `max(backoff, retry_after)` semantics. No change since the §9 audit.

## B6 — `docs/STRUCT.md` corrections (QLT-003)

**Status:** **VOIDED** by commit `6ab4a50`.

Commit `6ab4a50` (`chore clean structure.md`), dated 2026-10-11T00:17:46, deleted:
- `docs/STRUCT.md` (71 lines)
- `docs/error-handling-logging-research-2025-2026.md` (952 lines)
- `.ai/plans/19-entry-architecture-audit-fixes-execution.md` (153 lines)

The §9 audit reported B6 as PARTIAL: "Three STRUCT.md rows added (quality.py, ytdlp_downloader.py); four rows still wrong; models→exceptions upward-import disclosure missing." That status is now **moot** — the file no longer exists.

**However**, the `.ai/structure/` maps (B7's domain) still enumerate the old module set and are stale. B6's module enumeration (the actual census work) was never produced as an independent deliverable — it lives in B7's maps. The §7.3 structural assertion "docs/STRUCT.md names every .py path under src/vkdownloader/" can no longer be evaluated against the (deleted) file.

**The §9 audit's claim that P12-B12 gates B6 is still binding**: B6 yields the `ffmpeg_utils.py` row to `P12-B12`. If `P12-B12` never lands, B6 cannot write a correct row for a permanent module.

## B7 — `.ai/structure/` map regeneration (QLT-004)

**Status:** NOT DONE — maps are stale, with new drift since §9 audit.

### `back/py_map.yaml`

- **23 of 31 modules** recorded. Missing 7: `__main__.py`, `models/quality.py`, `services/batch_downloader.py`, `services/concurrency.py`, `services/ytdlp_downloader.py`, `utils/correlation.py`, `utils/formatting.py`.
- **Unsafe path prefix:** every entry uses `C:\py_exp\mko_vkideo\.ai\builders\..\..\src\vkdownloader\...` — the `builders/` directory does not exist; the `..` resolution produces Windows-backslash paths that are not checkout-reproducible.
- **Phantom symbols** in the `downloader.py` entry (L148-181): lists `HLSDownloader` (class), `_parse_quality_to_enum`, `_build_ytdlp_options`, `__init__`, `_download` — none exist in the actual `downloader.py` (which has `perform_download`, `download_video`, `_semaphore_context`).
- **Phantom import** in `downloader.py` entry (L157): lists `playwright.async_api` — the actual `downloader.py` does not import playwright (imports: structlog, config, exceptions, models.*, services.*, utils.*, ffmpeg_utils, segment_downloader, signal_handlers, downloader_throttle, cookies, ytdlp_downloader).
- **Duplicate `__init__`** in the `downloader_throttle.py` entry (L194-195).

### `map.md` (.ai/structure/map.md)

- Listed at L1-80 as a Windows `tree` output. Drive letter is `C:\PY_EXP` (uppercase) vs actual `C:\py_exp` (lowercase).
- **5 `.pyc` entries** listed for non-existent modules: `adaptive_throttle.cpython-312.pyc`, `http_client.cpython-312.pyc` (both in `infrastructure/__pycache__/`), plus entries in `models/__pycache__/`, `services/__pycache__/`, `utils/__pycache__/`, and root `__pycache__/`.
- **`vkdownloader.egg-info/` directory** listed (build output, not source).
- **Same 7 missing modules** as `py_map.yaml`.

### `front/ts_map.yaml` and `front/ts_anchors.yaml`

- Both reference `C:/py_dev/mkobi/frontend/src/...` — a **completely foreign project** (mkobi frontend). No `.kilo` tool or plan references these files. D9 default: delete both.

## B8 — `vkdownloader-overview.md` (QLT-005)

**Status:** PARTIAL — **worsened** since §9 audit by commit `6bd3188`.

### Four stale line counts (overview L283-286 vs actual at HEAD 24dcddc)

| File | Overview says | Actual | Drift |
|---|---|---|---|
| `downloader.py` | ~350 | 342 | -8 (close) |
| `ytdlp_downloader.py` | ~722 | **1,278** | **+556** |
| `segment_downloader.py` | ~901 | **1,181** | **+280** |
| `ffmpeg_utils.py` | ~360 | **561** | **+201** |

The plan §2.3 (L406) recorded these as already wrong at 09f1b10: `~722→874`, `~901→1283`, `~360→553`. At HEAD 24dcddc they are worse. ytdlp_downloader.py grew from 874 (09f1b10) to 1,278 (HEAD), +404 lines — driven by P13 observability commits (`24dcddc`, `17b0b8b`, `8783a8b`).

### New staleness from `6bd3188`

Commit `6bd3188` (`refactor(security): rename sanitize_title -> sanitize_filename_component`) renamed the function, but two doc references survived:

- `vkdownloader-overview.md:85` — `| sanitize_title() | utils/security.py | ...` (actual name is now `sanitize_filename_component`)
- `vkdownloader-overview.md:154` — `Title sanitization for filesystem safety via sanitize_title()`

### Universal-export claim (L292)

`vkdownloader-overview.md:292` — "All modules export their public APIs through downloader.py for backward compatibility." This is false: `__all__` in `downloader.py` (L108-128) has 19 entries; the facade imports 25 symbols total; 8 are not in `__all__`. Only 6 are owned by `downloader.py` itself.

### Retirement claim on `--method` row (L284)

`vkdownloader-overview.md:284` describes `ytdlp_downloader.py` as "yt-dlp subprocess management, cookie-file lifecycle, retry-with-fallback" — this **never listed `ffmpeg`** so it does not need the `--method` fix. The §9 audit confirms the `--method` row was already corrected by P13 commit `5fe961f`.

### `DownloadProgress` / `eta_seconds`

`grep` over `src/`, `tests/`, `docs/` returns **0 hits** — §9 audit claim holds. The section is gone.

## B9 — collapse CLI references (QLT-006)

**Status:** NOT DONE.

- `docs/99-reference/cli-reference-clean.md` **still exists** (208 lines) at HEAD 24dcddc. It has a duplicate `id` with `cli-reference.md` and carries mojibake.
- `docs/error-handling-logging-research-2025-2026.md` was **DELETED** by commit `6ab4a50`. B9 step 7 ("Update the one inbound reference in docs/error-handling-logging-research-2025-2026.md") and acceptance criterion 6 are now **moot** — the file is gone.
- `D11` (the single-source rule question) is **unsettled**.
- **CRITICAL:** `EXPECTED_SDIST_ENTRIES` in `tests/test_packaging.py` (73 entries) still lists both deleted files:
  - Line 71: `"docs/STRUCT.md"` — file deleted by 6ab4a50
  - Line 72: `"docs/error-handling-logging-research-2025-2026.md"` — file deleted by 6ab4a50
  - The actual sdist would contain 71 entries, so `test_sdist_entry_set_matches_the_manifest` and `test_sdist_entry_count_matches_the_manifest` will **FAIL** when `uv build` succeeds.

## B10 — misplaced reference documents (QLT-008)

**Status:** NOT DONE.

- `docs/99-reference/morfx-tools.md` **still exists** (431 lines — plan claimed 600 at 09f1b10).
- `docs/99-reference/ast-editor.md` **still exists** (31 lines — plan claimed 41 at 09f1b10).
- Both describe non-existent mkobi MCP tooling.
- `D12` (`.kilo` configuration lookup) **unsettled** — no `.kilo` command or agent references these files by path.
- `EXPECTED_SDIST_ENTRIES` still lists both files (lines 80, 83).

## B11 — dead provenance identifiers (QLT-007)

**Status:** NOT DONE.

**Current citation census (23 sites, 8 distinct identifiers):**

### src/ — 10 sites, 6 identifiers

| Identifier | Count | Sites |
|---|---|---|
| `INT-003` | 3 | `extractor.py:274,290,331` |
| `INT-004` | 2 | `browser.py:16,101` |
| `INT-006` | 2 | `browser.py:121`, `downloader_throttle.py:308` |
| `INT-008` | 1 | `downloader_throttle.py:51` (**NEW** — not in the original artifact) |
| `STR-008` | 1 | `ffmpeg_utils.py:91` (was L80 at §9 audit) |
| `SRV-006` | 1 | `ytdlp_downloader.py:919` |

### tests/ — 11 sites, 7 identifiers (+1 permanent note)

| Identifier | Count | Sites |
|---|---|---|
| `INT-004` | 3 | `test_browser_infrastructure.py:245,267`, `test_hls_downloader.py:3423` |
| `INT-006` | 2 | `test_downloader_throttle.py:442,461` |
| `INT-003` | 2 | `test_extractor.py:196,215` |
| `STR-008` | 1 | `test_hls_downloader.py:2138` |
| `INT-007` | 1 | `test_hls_downloader.py:5101` (permanent-subject note) |
| `SRV-006` | 1 | `test_hls_downloader.py:5431` |
| `SRV-003` | 1 | `test_downloader_throttle.py:906` (inline comment on ProgressManager) |

### docs/ — 3 sites, 2 identifiers

| Identifier | Count | Sites |
|---|---|---|
| `SRV-006` | 2 | `api-reference.md:466`, `vkdownloader-overview.md:39` |
| `SRV-001` | 1 | `vkdownloader-overview.md:290` |

**No new `INT-`/`SRV-`/`STR-` tokens** have appeared since the §9 audit. B11's census is stable at 8 identifiers and 23 sites.

## B12 — `models/quality.py` mixed import form (QLT-009... actually QLT-012)

**Status:** NOT DONE.

`models/quality.py:13` uses `from .enums import QualityKind, QualityLabel` — a one-dot relative import. The file also mixes `from __future__ import annotations` (L7), `from typing import Self` (L9), and `from pydantic import ...` (L11) without a documenting comment. D14b default: document as a deliberate exception (the cycle cannot be made relative).

## B13 — escalation of VAL-901 / VAL-902

**Status:** NOT DONE.

No escalation report has been produced. `VAL-901` remains CRITICAL and unimplementable (requires writing under `.ai/audit/99-validation/`, which plan 11 B10 prohibits). `VAL-902` similarly requires writing under `.ai/audit/99-validation/`. Per §7.5 #1-2, these remain unimplemented by design, not by oversight.

---

## Changes since §9 audit (2289f6f → HEAD 24dcddc)

29 commits landed. None are plan-14 block commits. They fall into three groups:

### Commits that changed B8/B9/B10 state (outside plan 14)

| Commit | Effect | Block impacted |
|---|---|---|
| `6ab4a50` chore clean structure.md | Deleted `docs/STRUCT.md` (71 lines), `docs/error-handling-logging-research-2025-2026.md` (952 lines), `.commit-msg.txt`, `.ai/plans/19-entry-architecture-audit-fixes-execution.md`; moved 3 plan files to `.ai/plans/done/` | B6 (voided), B9 (step 7 moot), B10 (frozenset stale), B11 (one `.ai/` citation in audit corpus removed) |
| `6bd3188` rename sanitize_title → sanitize_filename_component | Renamed in `src/vkdownloader/utils/security.py`; updated `aabfc46` docs note; but **two doc references in `vkdownloader-overview.md` (L85, L154) not updated** | B8 (new staleness) |

### Commits that changed external-gate state

| Commit | Effect |
|---|---|
| `e2c5ad0` refactor(segment_downloader): create segments tree only after playlist parse | P10 gate partially landed |
| `40404e2` fix(segment_downloader): exclude batch_*.ts from merge count | P10 gate partially landed |
| `767bb47` fix(ytdlp): repoint partial-file probe to .part temp name (P12-B9) | P12-B9 gate landed |

### Commits that did NOT affect plan 14 scope

| Commit | Effect |
|---|---|
| `3cc2897` feat(cli): add --log-level option | P13-B2; touches cli.py and cli-reference docs |
| `5fe961f` fix(cli): name ffmpeg removal in --method help text | P13-B17; touches cli.py |
| `c0b0236` docs: mark B11/B12 complete in plan | Only edits plan files; false claim (B11/B12 not done) |
| `d63bf4b` docs: mark P12-B9 complete in plan | Only edits plan files |
| `cfe4ce8` docs: mark P12-B5 task done | Only edits plan files |
| `17b0b8b`, `24dcddc` feat(observability) | P13-B4, P13-B7; touches downloader_throttle.py and ytdlp_downloader.py |
| `65d1c0a`, `6a62e6c` fix(logging) | P13-B3, P13-B6 |
| `600af4d` fix(cli): name max_retries bound | P13-B5 |
| `fc3725f` docs(B16): remove stale ffmpeg references from docstrings | Docstrings only |
| `5d264d4` fix(security): make ART-009 warning fire on all call sites | security.py |
| `aabfc46` docs(security): clarify [:100] bound | Docs only |
| `1d09009` fix(batch): deduplicate by resolved output filename | batch_downloader.py |
| `8783a8b` test(ffmpeg_utils): pass m3u8_url in boundary test | Tests only |
| `2a8f60b` fix(extractor): anchor VIDEO_ID_PATTERN (B12 partial) | extractor.py |
| `a9fdd4a` fix(downloader): thread m3u8_url to yt-dlp child | downloader/ytdlp_downloader.py |
| `c64376d` chore(audit): remove stale audit problems report files | Cleanup |
| `0a1772a` audit(B14): working-tree provenance | Audit tooling |
| `e9bafb2` audit(B15): path-based exclusion list | Audit tooling |

---

## §9.2 voided assertions (re-verified at HEAD 24dcddc)

| Assertion | §9 audit verdict | Current state |
|---|---|---|
| §2.3/§2.9: "check_ffmpeg_available return value is discarded" | **VOID** — e6e6c68 consumes probe via `logger.warning("ffmpeg_missing_for_merge", …)` | Still void; the probe is consumed |
| §2.2: "Skip floor = 3 D-11 permission oracles" | **VOID** — 3778e13 made oracles executable; 3 live skips are POSIX-killpg | Still 3 skips |
| §2.3: "Format gate is red" | **VOID** — green at 54 files | Need re-verification |
| §2.5 correction 12: "Facade defect — four deleted groups" | **VOID** — 0ee7297 restored groups; 28 mypy errors remain, owned by plan 18 | Groups restored in `downloader.py:88-107`; `_attempt_segment_resume` imported (L49) but absent from `__all__` and the comment — B4's criterion 6 still unmet |
| QLT-009: "INT-014 as separate code path" | **VOID** — removed by ruling A; path is now INT-008 only | No INT-014 tokens found in grep |

---

## CRITICAL finding: packaging tests are broken

**Commit `6ab4a50` deleted two files from `docs/` without updating `EXPECTED_SDIST_ENTRIES`.**

`tests/test_packaging.py:66-143` (`EXPECTED_SDIST_ENTRIES`, 73 entries) still lists:
- Line 71: `"docs/STRUCT.md"` — **deleted** by 6ab4a50
- Line 72: `"docs/error-handling-logging-research-2025-2026.md"` — **deleted** by 6ab4a50

The sdist `include` list in `pyproject.toml` (L57) uses `/docs` as a directory include, so the archive will contain whatever files exist in `docs/` at build time. The two deleted files will **not** be in the archive.

This means:
- `test_sdist_entry_set_matches_the_manifest` — will **FAIL**: 2 unexpected missing entries
- `test_sdist_entry_count_matches_the_manifest` — will **FAIL**: expected 73, actual 71

The §7.3 end-of-plan gate requires `tests/test_packaging.py` to be explicitly green. This is currently impossible.

---

## External gate status for B4

Per §4.2 (L1019): "B4 cannot start until plan 12's segment_downloader.py track (P12-B6, B7, B8) and plan 11's ytdlp_downloader.py track (B2, B5) have landed."

| Gate | Commits | Status |
|---|---|---|
| Plan 12 segment_downloader track | `e2c5ad0` (refactor), `40404e2` (fix sweep .ts.tmp) | ✅ Landed since §9 audit |
| Plan 12 P12-B9 partial-file probe | `767bb47` | ✅ Landed since §9 audit |
| Plan 11 ytdlp_downloader track (B2, B5) | None found in git log since 2289f6f | ❌ Not landed |

B4 cannot start until P11's ytdlp_downloader.py retry infrastructure track lands. No P11 commits are visible in the log since the §9 audit baseline.

---

## §5.6 DOC issues (unowned staleness)

| DOC ID | File | Description | Plan status |
|---|---|---|---|
| DOC-1 | (6 docs) | Retirement fixed 7 sites, introduced ≥2 new stale references | Partially addressed |
| DOC-4 | vkdownloader-overview.md | Stale line counts (all 4) | B8 — not started |
| DOC-5 | `ffmpeg_utils.py` docstring, `downloader.py` ownership group | Module docstring and facade group stay wrong about permanent code | Unowned — §1.4/§4.4 row 26 |
| DOC-6 | `.ai/audit/**` | Tree-drift measurement is void | Recorded read-only |

### New DOC issues introduced since §9 audit

| Source | Doc issue | File | Lines |
|---|---|---|---|
| `6bd3188` | `sanitize_title()` → `sanitize_filename_component()` rename not propagated to docs | `vkdownloader-overview.md:85,154` | B8 scope |
| `6ab4a50` | `EXPECTED_SDIST_ENTRIES` still lists deleted files | `test_packaging.py:71-72` | B9/B10 scope |
| P13 commits | Line counts drifted further | `vkdownloader-overview.md:283-286` | B8 scope |
| `c0b0236` | Plan claims "B11/B12 complete" in commit message | Plan metadata | False claim |

---

## §2.3 facts re-measured at HEAD 24dcddc

| Fact | §9 audit figure (09f1b10) | Current figure | Change |
|---|---|---|---|
| `ErrorCode` member count | 8 at `09f1b10` / 9 at §9 audit (`2289f6f`) | **9** | `STEALTH_ASSET_MISSING` added by commit `c6d0214` between `09f1b10` and `2289f6f`; `PATH_TRAVERSAL` was already present at `09f1b10` (via `d572d96`). No change since §9 audit. `NO_STREAMS` remains absent |
| `status_label()` override count | 6 | **6** (unchanged) | No change |
| `mypy src tests` expected | 89 errors / 8 files | **Re-measure required** | Cannot determine without running mypy |
| `mypy --disallow-any-explicit src` | 11 errors / 8 files | **Re-measure required** | Cannot determine without running mypy |
| `RETRYABLE_STATUS_CODES` members | 7 | **7** | `{408, 425, 429, 500, 502, 503, 504}` at downloader_throttle.py:53 |
| `RETRYABLE_STATUS_CODES` documented | 5 (api-reference.md:182) | **5** | Still stale |
| ytdlp_downloader.py lines | 874 (09f1b10) | **1,278** | +404 since §9 audit |
| segment_downloader.py lines | 1283 (09f1b10) | **1,181** | -102 since §9 audit |
| ffmpeg_utils.py lines | 553 (09f1b10) | **561** | +8 since §9 audit |
| downloader.py lines | 344 (09f1b10) | **342** | -2 since §9 audit |
| `py_map.yaml` module count | 23/31 | **23/31** | Unchanged |
| `py_map.yaml` phantom symbols | — | **5** in downloader.py entry + duplicate `__init__` | Not re-measured by §9 audit |
| `front/` map prefix | `C:/py_dev/mkobi/frontend/` | **Same** | Foreign project, unchanged |
| `map.md` `.pyc` entries | 5 | **5** | Unchanged |
| `map.md` egg-info listed | Yes | **Yes** | Unchanged |
| `EXPECTED_SDIST_ENTRIES` count | 73 | **73** (stale — should be 71) | **BROKEN** by 6ab4a50 |
| `DownloadMethod` members | 2 (YTDLP, AUTO) | **2** | Unchanged |
| `_map_exception_to_status` production callers | 0 | **0** | Unchanged |
| `_map_exception_to_status` test callers | 11 | **11** | Unchanged (test_exceptions.py:11,17,22,28,37,44,51,57,63,70,76,201,206,218 — 14 references, 11 calls) |
| `VKDownloadError` imported in cli.py | No | **No** | Unchanged |
| D-11 skips | 3 | **3** | Unchanged |

---

## Recommendations

### Mandatory (blockers)

1. **[CRITICAL] Fix `EXPECTED_SDIST_ENTRIES`** — Commit `6ab4a50` deleted `docs/STRUCT.md` and `docs/error-handling-logging-research-2025-2026.md` from the source tree without updating `tests/test_packaging.py`. The `EXPECTED_SDIST_ENTRIES` frozenset (73 entries) still lists both. The packaging test will FAIL on any successful `uv build`. This is the highest-priority issue: it blocks the plan's end-of-plan gate and makes every subsequent block's "green test suite" claim false. **Fix:** remove both entries from `EXPECTED_SDIST_ENTRIES` (73→71), unless a later plan restores them. (Effort: trivial)

2. **[CRITICAL] Resolve P11 external gate for B4** — B4 cannot start until plan 11's ytdlp_downloader.py track (B2, B5) lands. No P11 commits are visible since the §9 audit baseline. The plan 14 order (§4.2) serialises B4 behind all three external gates. **Action:** determine whether P11 has landed in a branch not visible at this remote, or whether the gate is blocked.

### Advisory

3. **[B6] B6 is voided** — `docs/STRUCT.md` no longer exists. The §9 audit's "PARTIAL" status is stale. B6 should be re-scoped to "not applicable" or marked voided, with the module enumeration work (if still needed) folded into B7's map regeneration. (Effort: trivial — status only)

4. **[B7] Regenerate `.ai/structure/` maps from the live tree** — `py_map.yaml` is missing 7 modules, has 5 phantom symbols in the downloader.py entry, uses unsafe `.ai/builders/..\..` paths, and has a duplicate `__init__`. `map.md` lists 5 non-existent `.pyc` files, includes `egg-info/`, and uses wrong drive-letter casing. The `front/` maps reference an entirely foreign project (`C:/py_dev/mkobi/frontend/`). D9 default (delete front maps) is justified: no tooling or plan references them.

5. **[B8] Update `vkdownloader-overview.md`** — Fix 4 stale line counts (especially ytdlp_downloader.py: ~722→1,278; segment_downloader.py: ~901→1,181; ffmpeg_utils.py: ~360→561), replace `sanitize_title()` → `sanitize_filename_component()` at L85 and L154, remove or scope the universal-export claim at L292, and rewrite the ffmpeg_utils.py listing (L286) to describe the permanent module shape. D10 default: drop the line counts entirely (no oracle parses them).

6. **[B9] Delete `cli-reference-clean.md`** — The file still exists with a duplicate `id: cli-reference` and mojibake. B9's frozenset coupling (`73→72`) is now `71→70` after 6ab4a50's deletions. Step 7 (updating the research doc's inbound reference) is moot — the research doc was deleted.

7. **[B10] Resolve morfx-tools.md and ast-editor.md** — Both still exist (431 and 31 lines respectively) and describe non-existent mkobi MCP tooling. D12 default: move out of `docs/99-reference/` into a developer-tooling location. The frozenset coupling means the move must be edited in the same commit as the frozenset.

8. **[B12] Document the mixed import form** — `models/quality.py:13` uses `from .enums import QualityKind, QualityLabel` (one-dot relative) while the file also mixes `from __future__`, `from typing`, and `from pydantic`. D14b default: add a comment documenting this as a deliberate exception to break a circular import.

9. **[B13] Produce VAL-901 / VAL-902 escalation report** — No escalation has been written. VAL-901 is CRITICAL (3× growth) and VAL-902 is unimplemented. Both require writing under `.ai/audit/99-validation/`, which plan 11 B10 prohibits — B13 must escalate and stop.

---

## Conclusion

At HEAD `24dcddc`, plan 14 remains **unexecuted**. All 13 blocks retain their §9 audit status (B5 = DONE, B6 = voided by out-of-plan deletion, all others NOT DONE or PARTIAL). The §9 audit's voided assertions hold, with the facade defect (#4) partially voided (groups restored by 0ee7297) but B4's criterion 6 still unmet for `_attempt_segment_resume`.

The single most impactful new development is **CRITICAL**: commit `6ab4a50` broke the packaging test suite by deleting two files from `docs/` without updating `EXPECTED_SDIST_ENTRIES`. This was not a plan-14 action — it was commit-driven cleanup that bypassed the plan's serialisation rules and frozenset coupling. Every subsequent block that touches `tests/test_packaging.py` must now first reconcile the frozenset to the actual tree (73 expected → 71 actual), or the end-of-plan gate will never be green.
