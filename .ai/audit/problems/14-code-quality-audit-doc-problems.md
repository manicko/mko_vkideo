# Audit Problems Report — Plan 14 Documentation Check

**Date:** 2026-10-10  
**Auditor:** Plan 14 status audit  
**Scope:** Documentation issues found in `docs/` during verification of plan `14-code-quality-audit-fixes.md`  
**Note:** The user requested checks against `C:\py_dev\mko_bazuna\docs`, but that path is not accessible in this environment. This report covers `C:\py_exp\mko_vkideo\docs` (the live workspace) instead, which is the project the plan targets.

---

## Summary

Plan 14 (`14-code-quality-audit-fixes.md`) describes 13 execution blocks (B1–B13) targeting code-quality audit findings (`QLT-001` through `QLT-013`, plus `VAL-901/902/903`). **None of the blocks have been executed.** The plan file retains its original name (no `_fix` or `_done` suffix), and the vast majority of its target issues remain unaddressed in the code. Some issues were incidentally fixed by other plans' commits (tracked in `.ai/plans/18-consolidated-audit-fixes-execution.md` §5.1, V1–V13), but the plan as a whole is still valid, referenced by plan 18 as a source plan, and its core blocks remain unimplemented.

**Conclusion: rename to `_fix`.** The work is not complete, the plan is valid and needed, the plan does not violate architecture or quality — it fixes violations.

---

## Block-by-block execution status

| Block | Description | Status | Evidence |
|---|---|---|---|
| B1 | Delete `_map_exception_to_status` shim; unify `status_label()` against `ErrorCode`; add `NO_STREAMS` | **NOT DONE** | `exceptions.py` still defines `_map_exception_to_status` (line 216), `_EXCEPTION_STATUS_HANDLERS` (line 240), `_quality_not_available_status` (line 232); 6 `status_label()` overrides still return bare string literals; `NO_STREAMS` absent from `ErrorCode`; module docstring still advertises the shim |
| B2 | Add logging to silent exception ladder clauses in `cli.py` and `batch_downloader` | **NOT DONE** | `cli.py` ladders have no `VKDownloadError` arm; terminal `except Exception` uses `logger.exception` with no `log_context()` |
| B3 | Enable `disallow_any_explicit`; reconcile Python version pins | **NOT DONE** | `pyproject.toml` lacks `disallow_any_explicit`; `requires-python` still `>=3.12`; `target-version = "py312"`; `python_version = "3.12"` — Ruling B (`>=3.14`) has not landed |
| B4 | Split `downloader_throttle.py` (retry policy → new module) | **NOT DONE** | All 5 retry symbols still in `downloader_throttle.py`; no new module file exists |
| B5 | Document Retry-After as a floor (not an override) | **DONE** | Commit `83ba0f8` corrected the comment and docstring |
| B6 | Fix `docs/STRUCT.md` stale rows | **PARTIAL** | Three rows added (quality.py, ytdlp_downloader.py); four rows still wrong (enums.py "Quality,Method" names nothing; video.py "dataclass" wrong; dtos.py; concurrency.py); Layering disclosure of `models→exceptions` upward import not recorded |
| B7 | Fix `.ai/structure/` stale maps | **NOT DONE** | `py_map.yaml` records 23 of 31 modules; phantom symbols `QualityEnum`/`_parse_quality_to_enum` still present; `front/*` maps reference `py_dev` project (164 refs); `py_anchors.yaml` has 466 `builders/`-prefixed anchors; `map.md` lists 5 `.pyc` entries for non-existent modules |
| B8 | Fix `vkdownloader-overview.md` universal-export claim and stale line counts | **PARTIAL** | `--method ffmpeg` row already fixed (ceded per plan 18 §1.2); but "All modules export their public APIs through `downloader.py`" (universal-export claim, line 292) still present; four line counts still wrong: `downloader.py (~350 vs 344)`, `ytdlp_downloader.py (~722 vs 874)`, `segment_downloader.py (~901 vs 1283)`, `ffmpeg_utils.py (~360 vs 636)` |
| B9 | Delete `cli-reference-clean.md`; merge into `cli-reference.md` | **NOT DONE** | `cli-reference-clean.md` still exists; both files declare `id: cli-reference`; file contains mojibake (0 em-dashes vs 16 in the survivor); still has `--method ffmpeg` usage example |
| B10 | Resolve misplaced `morfx-tools.md` / `ast-editor.md` (describe non-existent MCP tooling) | **NOT DONE** | Both files shipped in sdist (`EXPECTED_SDIST_ENTRIES`); `morfx-tools.md` (600 lines) describes `morfX_replace` etc.; `ast-editor.md` (41 lines) describes `ast-editor` tools; neither documents any code in this repository; both `related` cross-reference each other |
| B11 | Resolve dead `INT-`/`SRV-`/`STR-` provenance citations | **NOT DONE** | `INT-008` cited from `downloader_throttle.py` (line 51) but appears in no findings file; `SRV-001` cited from `vkdownloader-overview.md` (line 290); `STR-008` on `iter_process_lines` in `ffmpeg_utils.py` (line 80) |
| B12 | Record the mixed import form in `models/quality.py` | **NOT DONE** | `models/quality.py` uses both relative module-level import and lazy absolute import (breaking a cycle); no comment on the lazy import explains the cycle |
| B13 | Produce escalation note for `VAL-901`/`VAL-902` (cannot edit `.ai/audit/`) | **NOT DONE** | No escalation report produced |

---

## Documentation problems found in `docs/`

### 1. `docs/STRUCT.md` — stale and wrong rows (plan 14 B6)

| Line | Row | Problem |
|---|---|---|
| 14 | `exceptions.py` | Comment says "Domain exceptions + legacy status mapping" — the "legacy status mapping" refers to `_map_exception_to_status` which B1 was supposed to remove; the label is stale pending B1's execution |
| 23 | `enums.py` | Parenthetical says "Quality, Method, CookieSource, etc." — `Quality` and `Method` are not enum names in the file; actual enums are `QualityKind`, `QualityLabel`, `DownloadMethod`, `CookieSource`, `LogLevel`, `ErrorCode`, `ProgressStatus` |
| 25 | `video.py` | Says "Video metadata dataclass" — the module holds three `BaseModel` subclasses, not dataclasses |
| 32 | `downloader_throttle.py` | Describes post-B4 pre-split state — will be stale once B4 splits the module |
| 34 | `ffmpeg_utils.py` | Says "FFmpeg discovery and stream concatenation" — yielded to plan 12 `P12-B12`; misdescribes a permanent module per Ruling A (omits subprocess infrastructure and merge engine groups) |
| 48-54 (Layering) | — | The entry-layer rule ("No private-symbol imports from service/utils layers") is violated by `cli.py` importing `_strip_auth_params` from utils, but this exception is not disclosed |

### 2. `docs/01-tools/vkdownloader-overview.md` — universal-export claim and stale counts (plan 14 B8)

| Line | Problem |
|---|---|
| 292 | "All modules export their public APIs through `downloader.py` for backward compatibility" — false universal-export claim; the file should be scoped or removed |
| 283 | `downloader.py (~350 lines)` — actual: 344 (partially corrected by retirement) |
| 284 | `ytdlp_downloader.py (~722 lines)` — actual: 874 |
| 285 | `segment_downloader.py (~901 lines)` — actual: 1283 |
| 286 | `ffmpeg_utils.py (~360 lines)` — actual: 636 |

### 3. `docs/01-tools/api-reference.md` — stale constant census (plan 14 B4/D8)

| Line | Problem |
|---|---|
| 182 | `RETRYABLE_STATUS_CODES` documented as `{429, 500, 502, 503, 504}` (5 members) — actual: `{408, 425, 429, 500, 502, 503, 504}` (7 members) |

### 4. `docs/99-reference/cli-reference-clean.md` — should be deleted (plan 14 B9)

| Problem |
|---|
| File declares `id: cli-reference` — duplicates `cli-reference.md` |
| Mojibake transcription: 0 em-dashes vs 16 in the survivor |
| Retains `--method ffmpeg` usage example (deleted transport) |
| Listed in `EXPECTED_SDIST_ENTRIES` (73 → should be 72) |

### 5. `docs/99-reference/morfx-tools.md` and `ast-editor.md` — non-existent tooling docs (plan 14 B10)

| File | Problem |
|---|---|
| `morfx-tools.md` (600 lines) | Describes `morfX_replace`, `morfx_file_delete`, etc. — MCP code-transformation tools this repository does not contain; self-disclaims but remains shipped in sdist |
| `ast-editor.md` (41 lines) | Describes `ast-editor` tools — not in this codebase; both files cross-reference each other in `related` arrays |

### 6. `.ai/structure/` — stale generation maps (plan 14 B7)

| File | Problem |
|---|---|
| `back/py_map.yaml` | 23 entries against 31 `.py` modules; contains phantom symbols `QualityEnum` and `_parse_quality_to_enum` |
| `back/py_anchors.yaml` | 466 anchors use the unsafe `.ai/builders/` prefix (gitignored, unresolvable from clean checkout) |
| `front/ts_map.yaml` | References `C:/py_dev/mkobi/frontend/src/*.tsx` — a different project (164 references) |
| `front/ts_anchors.yaml` | Same foreign project references (49 references) |
| `map.md` | Lists 5 `.pyc` entries for modules that do not exist |

---

## Code problems found during audit (documentation only — no code changes made)

| File | Problem | Plan 14 block |
|---|---|---|
| `src/vkdownloader/exceptions.py` | `_map_exception_to_status`, `_EXCEPTION_STATUS_HANDLERS`, `_quality_not_available_status` still defined (shim not removed); module docstring still advertises the shim; 6 `status_label()` overrides return bare strings | B1 |
| `src/vkdownloader/exceptions.py` | `_EXCEPTION_STATUS_HANDLERS` uses `Callable[..., str]` annotation — explicit `Any` | B3 |
| `src/vkdownloader/cli.py` | No `VKDownloadError` arm in either exception ladder; terminal arms use `logger.exception` without structured `log_context()` | B2 |
| `pyproject.toml` | No `disallow_any_explicit` flag; `requires-python = ">=3.12"` (Ruling B not landed); `target-version = "py312"` and `python_version = "3.12"` are silent pins unenforced against the declared floor | B3, D16 |
| `src/vkdownloader/services/downloader_throttle.py` | Retry policy symbols (`RETRYABLE_STATUS_CODES`, `_retry_429_with_backoff`, `_parse_retry_after`, `_compute_backoff_delay`, `_wait_with_shutdown`) not split into a separate module | B4 |

---

## Source-plan assertion voidance recorded (per plan 18 §5.1)

The following plan 14 §2 assertions have been voided by commits between `09f1b10` and the live HEAD:

- **Plan 14 §2.3 / §2.9** "`check_ffmpeg_available`'s return value is discarded" — **void**. Commit `e6e6c68` now consumes the probe's answer via `logger.warning("ffmpeg_missing_for_merge", …)`.
- **Plan 14 §2.5 correction 12** (facade defect in `services/downloader.py`) — the symbol-ownership comment's four deleted groups were **restored** by commit `0ee7297`. However, 94 `mypy src tests` errors remain (the 28 `does not explicitly export attribute` errors are now owned by plan 18 `P18-B14` / `DEC-Z`).
- **Plan 14 §2.2** (skip floor = 3 D-11 oracles) — **void**. Commit `3778e13` made the permission oracles executable; the 3 live skips are now POSIX-killpg oracles, not D-11 oracles.
- **Plan 14 §2.3** (format gate red) — **void**. Gate is green at 54 files.

These voidances are tracked in `.ai/plans/18-consolidated-audit-fixes-execution.md` §5.1 (V1–V13). Plan 14 remains the source-of-truth for blocks B1, B2, B3, B4, B6, B7, B9, B10, B11, B12, B13 as re-scoped by plan 18.
