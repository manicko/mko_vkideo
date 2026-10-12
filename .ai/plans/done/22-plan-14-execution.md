# Execution plan: Plan 14 code-quality audit fixes (updated 2026-10-11)

**Source plan:** `.ai/plans/14-code-quality-audit-fixes_fix.md` (1623 lines, 13 blocks B1–B13)
**Auditor report:** `.ai/audit/problems/14-code-quality-audit-update-2026-10-11.md`
**Plan base:** `09f1b10` | **§9 audit:** `2289f6f` | **Live HEAD:** `24dcddc` (29 commits past §9)

## Adjustments from the §9 audit

| Change | Impact |
|---|---|
| `6ab4a50` deleted `docs/STRUCT.md` and `docs/error-handling-logging-research-2025-2026.md` | B6 **VOIDED**; `EXPECTED_SDIST_ENTRIES` **broken** (CRITICAL) |
| `6bd3188` renamed `sanitize_title` → `sanitize_filename_component` | B8 **worsened** (2 new stale refs in overview) |
| P13 observability commits (`24dcddc`, `17b0b8b`, `3cc2897`, etc.) | `cli.py::_quality_option` already uses `cast(OptionInfo, …)` — B3's `Any` site is gone |
| `2a8f60b` anchored `VIDEO_ID_PATTERN` | B12 partial (extraction side); `quality.py` mixed-import remains |

## Block status at HEAD `24dcddc`

| Block | Plan §9 | Current | External gate | Executability |
|---|---|---|---|---|
| B1 | NOT DONE | NOT DONE | None | ✅ Can execute |
| B2 | NOT DONE | NOT DONE | P11-B6 not landed | ⚠️ Proceed after B1 (P11-B6 check needed) |
| B3 | NOT DONE | NOT DONE | P11-B6 | ⚠️ Proceed after B1+B2 (P13 already fixed cli.py Any) |
| B4 | NOT DONE | NOT DONE | P11 not landed | ❌ BLOCKED |
| B5 | DONE | DONE | — | ✅ Already complete |
| B6 | PARTIAL | **VOIDED** | P12-B12 | ❌ Skipped (deleted by 6ab4a50; scope folded to B7) |
| B7 | NOT DONE | NOT DONE | None (B6 voided) | ✅ Can execute |
| B8 | PARTIAL | PARTIAL (worsened) | B4+ P10-B10 | ⚠️ Partial (post-B4 line counts deferred) |
| B9 | NOT DONE | NOT DONE | P10-B10 + B10 | ⚠️ After B10 |
| B10 | NOT DONE | NOT DONE | None | ✅ Can execute |
| B11 | NOT DONE | NOT DONE | P10-B7, P10-B10, P11-B4 | ⚠️ Check gate status |
| B12 | NOT DONE | NOT DONE | B3 | ⚠️ After B3 |
| B13 | NOT DONE | NOT DONE | None | ✅ Can execute (no code) |

## Execution order

```
PREREQ → B13 → B1 → B2 → B3 → B12 → B7 → B10 → B9 → B8 → B11 → B4(blocked)
```

### PREREQ — Fix broken packaging test (CRITICAL)
- **File:** `tests/test_packaging.py`
- **Action:** Remove `"docs/STRUCT.md"` and `"docs/error-handling-logging-research-2025-2026.md"` from `EXPECTED_SDIST_ENTRIES` (74→72 entries).
- **Rationale:** Commit `6ab4a50` deleted both files without updating the frozenset. All block gates run `pytest`, which currently fails on `test_packaging.py`.

### B13 — VAL-901/VAL-902 escalation (documentation only)
- **Scope:** Produce escalation report. No code changes.
- **Agent roster:** Auditor, Planner → Implementation is documentation-only.

### B1 — exceptions.py shim removal (QLT-001 + QLT-010)
- **Scope:** Delete `_map_exception_to_status`, `_quality_not_available_status`, `_EXCEPTION_STATUS_HANDLERS`; add `ErrorCode.NO_STREAMS`; unify `status_label()` derivation; rewrite `tests/test_exceptions.py`.
- **Agent roster:** Auditor, Planner, Validator

### B2 — cli.py exception ladders (QLT-002)
- **Scope:** Add `VKDownloadError` arm to both cli.py ladders; add `logger.error` to 3 silent `batch_downloader._download_single` arms; settle D3 against phase-08 evidence.
- **Agent roster:** Auditor, Planner, Validator
- **Note:** Pre-condition P11-B6 — must verify whether both `logger.exception` sites are already test-covered.

### B3 — pyproject.toml type gate (QLT-009)
- **Scope:** Enable `disallow_any_explicit`; reconcile `requires-python`/`target-version`/`python_version` to ≥3.14 (D16); fix remaining `Any` sites (models/video.py, dtos.py, quality.py, config.py, extractor.py, ytdlp_downloader.py).
- **Agent roster:** Researcher (mypy library-semantics), Planner, Validator
- **Note:** `cli.py::_quality_option` Any site already fixed by P13.

### B12 — quality.py mixed import documentation (QLT-012)
- **Scope:** Add documenting comment on `from .enums import …` in `quality.py:13`.
- **Agent roster:** Planner only (trivial, comment-only)

### B7 — .ai/structure/ map regeneration (QLT-004, includes B6 scope)
- **Scope:** Regenerate `py_map.yaml` (23→31 modules, remove 5 phantom symbols, fix unsafe paths); delete `front/` maps (D9); fix `map.md` (.pyc entries, egg-info, drive-letter casing); record regeneration procedure.
- **Agent roster:** Auditor, Planner, Validator

### B10 — misplaced reference documents (QLT-008)
- **Scope:** Resolve `morfx-tools.md` and `ast-editor.md` per D12; update `EXPECTED_SDIST_ENTRIES`.
- **Agent roster:** Auditor, Planner

### B9 — collapse CLI references (QLT-006)
- **Scope:** Delete `cli-reference-clean.md`; merge correct content into `cli-reference.md`; update `EXPECTED_SDIST_ENTRIES` (72→71).
- **Agent roster:** Auditor, Planner, Validator

### B8 — vkdownloader-overview.md (QLT-005)
- **Scope:** Fix stale line counts (D10 default: drop); fix `sanitize_title` refs; scope/remove universal-export claim; rewrite ffmpeg_utils.py listing.
- **Agent roster:** Auditor, Planner
- **Note:** Post-B4 line-count reconciliation deferred if B4 remains blocked.

### B11 — dead provenance citations (QLT-007)
- **Scope:** Resolve 23 citation sites across 8 identifiers; no new tokens.
- **Agent roster:** Auditor, Planner, Validator

### B4 — downloader_throttle.py split (QLT-011) — BLOCKED
- **Blocker:** P11 (ytdlp_downloader.py retry infrastructure) has not landed.
- **Status:** Deferred until P11 lands.

## Voided assertions (all hold at HEAD 24dcddc)
1. §2.3/§2.9: `check_ffmpeg_available` return value consumed (commit `e6e6c68`).
2. §2.2: Skip floor = 3 POSIX-killpg oracles (commit `3778e13`).
3. §2.3: Format gate green.
4. §2.5 correction 12: Facade groups restored (commit `0ee7297`); `_attempt_segment_resume` absence from `__all__` is B4's criterion 6.
5. QLT-009: `INT-014` removed; path is `INT-008` only.

## Decisions carried forward (D1–D16)
- D1: Add `ErrorCode.NO_STREAMS` (default) — `no_streams` has committed consumers in `test_exceptions.py` and `batch_downloader._download_single`.
- D2: Shim removal in same commit as derivation.
- D3: Default `logger.error`; settle against phase-08 `OUT-002` evidence.
- D4: Adopt `user_message()` as presentation path for new arms.
- D5: Global `disallow_any_explicit` with per-module overrides for Pydantic-inherited `Any`.
- D7: New module for retry policy; `downloader_throttle.py` keeps its name (7 importers).
- D9: Delete `front/` maps (no tooling references them).
- D10: Drop stale line counts (no oracle parses them).
- D11: Pending B13 escalation answer; apply default (amend the single-source rule).
- D12: Move `morfx-tools.md` and `ast-editor.md` out of `docs/99-reference/`, keep shipped.
- D14b: Document `quality.py` mixed import as deliberate cycle-break exception.
- D16: B3 owns both `target-version` and `python_version` pins.
