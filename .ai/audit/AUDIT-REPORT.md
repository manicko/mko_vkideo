# mko_vkideo — Consolidated Audit Report (Validated Findings)

**Project:** mko_vkideo — Python CLI for downloading VK videos
**Audit date:** 2026-07-20
**Pipeline:** multi-agent audit orchestrator (9 phases + validation)
**Scope:** 9 audit phases, all executor findings validated by independent validator subagents

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Phases executed | 9 / 9 |
| Executor findings produced | 56 |
| Rejected by validator | 6 |
| Merged / de-duplicated | 4 (2 merged into existing, 2 consolidated as duplicates) |
| **Validated findings retained** | **46** |

### Severity breakdown (validated findings)

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 4 |
| MEDIUM | 22 |
| LOW | 20 |

> Note: DF-001/DF-002 (Phase 06) are validated duplicates of the HIGH SRV-003 (Segment resume never completes). Counting them as separate HIGH would overstate severity; they are listed once under SRV-003. Net distinct HIGH = 4 (CLI-001, CFG-001, SRV-003, and the consolidated DF-001/DF-002).

### Mandatory fixes (must resolve before next release)

| ID | Phase | Severity | Issue |
|----|-------|----------|-------|
| **CLI-001** | 01 | HIGH | Batch path relabels genuine exceptions as "cancelled", hiding real failures |
| **CFG-001** | 02 | HIGH | `cookie_source=FILE` silently no-ops (behaves like `none`) in the primary CLI flow |
| **SRV-003** | 03 | HIGH | Segment resume double-counts progress and can never merge a resumed run (DF-001/DF-002 are the same bug) |
| **SRV-005** | 03 | MEDIUM (mandatory) | BROWSER cookie-source rejects all numeric qualities — only `best` works |

---

## 2. Validated Findings by Phase

### Phase 01 — Entry Point & Command Layer (CLI)
| ID | Severity | Type | Issue |
|----|----------|------|-------|
| CLI-001 | HIGH | SPEC-DEVIATION | `asyncio.gather(return_exceptions=True)` + post-processing at cli.py:249-251 coerces any non-tuple result (incl. real exceptions) into `('url','','cancelled')`, masking genuine failures as user cancellations. |
| CLI-002 | MEDIUM | SPEC-DEVIATION | `download` catches `ValueError` universally and prints "Invalid URL format" even when the real cause is `QualitySelector.select` raising "Cannot select from empty streams list". |
| CLI-003 | MEDIUM | DOC-UPDATE | `docs/99-reference/cli-reference.md` has 2 trailing NUL bytes (invalid UTF-8); corrupts tooling/readers. |
| CLI-004 | LOW | BEST-PRACTICE | Signal-handler registration is process-global but bound to the first event loop; second CLI invocation in same process loses handlers. |

### Phase 02 — Configuration & Settings Models
| ID | Severity | Type | Issue |
|----|----------|------|-------|
| CFG-001 | HIGH | SPEC-DEVIATION | `cookie_source=FILE` is accepted and silently behaves like `none` (the `NotImplementedError` is only in `extract_streams_with_cookies`, never called by the primary download path). |
| CFG-002 | MEDIUM | BEST-PRACTICE | `extra="forbid"` only guards explicit kwargs, not env/`.env`; unknown keys silently ignored. |
| CFG-003 | LOW | SPEC-DEVIATION | Repo `.env` references non-existent `VKDOWNLOADER_DOWNLOAD_METHOD`. |
| CFG-004 | LOW | BEST-PRACTICE | Missing `log_file` parent dir raises bare `FileNotFoundError` with no actionable message. |
| CFG-005 | LOW | BEST-PRACTICE | `.env` resolved relative to CWD only; installed/console usage from another dir loses config. |
| CFG-006 | LOW | BEST-PRACTICE | `throttled_rate` default (100 KB/s) may abort legitimate slow downloads on throttled CDNs. |

### Phase 03 — Service Layer & Business Logic
| ID | Severity | Type | Issue |
|----|----------|------|-------|
| SRV-003 | HIGH | RUNTIME-ERROR | Segment resume: `_run_download_session` ignores loaded `downloaded_count` for skipping, and `_tally_and_merge` adds old count to new, so `downloaded_count == len(segments)` is never true → merge never runs → no output. |
| SRV-005 | MEDIUM | SPEC-DEVIATION | BROWSER path yields a single `height=None`/`best` stream; `_resolve_cookies` re-selects with numeric quality → `QualityNotAvailableError` for every non-`best` quality. |
| SRV-001 | LOW | BEST-PRACTICE | `SegmentRetryResult` enum is dead code (0 references). |
| SRV-002 | LOW | BEST-PRACTICE | `ProgressManager.get_progress` never called. |
| SRV-004 | LOW | BEST-PRACTICE | Redundant `if retry_count <= MAX_RESUME_RETRIES:` inside the while loop at downloader.py:418. |
| SRV-006 | LOW | BEST-PRACTICE | BEST/WORST selection arbitrary when `height=None`. |
| SRV-007 | LOW | BEST-PRACTICE | "Segment resume" discards the partial yt-dlp file (full restart); docstrings overstate behavior. |

### Phase 04 — Security & Secret Management
| ID | Severity | Type | Issue |
|----|----------|------|-------|
| SEC-001 | MEDIUM | BEST-PRACTICE | BROWSER-mode Netscape cookie file written with default umask (world-readable on Unix) in shared download dir during the whole download. |
| SEC-002 | LOW | SPEC-DEVIATION | `--cookie-source file` is advertised in CLI/docs but raises `NotImplementedError` at runtime (overlaps CFG-001 — both describe the unimplemented `FILE` value from different paths). |
| SEC-003 | LOW | BEST-PRACTICE | Batch URL file content is not validated before enqueueing; malformed entries fail late and are swallowed into a summary. |

### Phase 05 — External Integrations
| ID | Severity | Type | Issue |
|----|----------|------|-------|
| INT-001 | MEDIUM | BEST-PRACTICE (mandatory lifecycle) | `BrowserManager.__aenter__` leaks the Playwright subprocess if `chromium.launch()` fails (no `__aexit__` invoked). |
| INT-002 | MEDIUM | BEST-PRACTICE | Browser not torn down on `KeyboardInterrupt` (signal handler only sets an event). |
| INT-003 | MEDIUM | SPEC-DEVIATION | `configuration.md` claims `auto`+`BROWSER` = "No browser involvement", but the AUTO path launches the browser. |
| INT-004 | MEDIUM | SPEC-DEVIATION | `CookieSource.FILE` is a valid enum that only crashes mid-extraction; should be validated/rejected at startup. |
| INT-005 | MEDIUM | BEST-PRACTICE | Parallel segment path uses hardcoded `asyncio.sleep(1.0)` (no jitter/Retry-After/shutdown-aware) vs. full-jitter sequential path. |
| INT-006 | MEDIUM | BEST-PRACTICE | `_fetch_single_playlist` swallows `asyncio.CancelledError`, blocking Ctrl+C during playlist resolution. |
| INT-007 | MEDIUM | BEST-PRACTICE | `NetworkMonitor` reads full JSON body for every response URL containing "video" (no size/depth guard). |
| INT-008 | MEDIUM | BEST-PRACTICE | `download_timeout` is one field used as total-cap for aiohttp and `socket_timeout` for yt-dlp with inconsistent semantics. |
| INT-009 | MEDIUM | BEST-PRACTICE | ffmpeg stderr may be truncated on normal exit; `cancel_ffmpeg_process` return value ignored. |
| INT-010 | MEDIUM | BEST-PRACTICE | Batch `.ts` temp files / segment dir left on disk when a merge fails/raises. |

### Phase 06 — End-to-End Data Flow
> DF-001 and DF-002 are validated duplicates of SRV-003 (Phase 03) — the same segment-resume counter/discard bug. Consolidated under SRV-003.

| ID | Severity | Type | Issue |
|----|----------|------|-------|
| DF-001 | HIGH | RUNTIME-ERROR | Resume metadata never reset; accumulated count can exceed total and permanently skip the merge. *(= SRV-003)* |
| DF-002 | MEDIUM | SPEC-DEVIATION | "Segment-level resume" re-downloads all segments instead of only missing ones. *(= SRV-003)* |

### Phase 07 — Test Quality
> TST-001 was REJECTED by the validator (evidence partially incorrect — component functions are tested; severity overstated).

| ID | Severity | Type | Issue |
|----|----------|------|-------|
| TST-002 | MEDIUM | BEST-PRACTICE | `perform_download` dispatch + FFMPEG→segment fallback lacks behavioral tests (only log-emission mocked). |
| TST-003 | MEDIUM | BEST-PRACTICE | `test_structured_logging_on_retry` asserts only the mock-guaranteed return; never verifies logging. |
| TST-004 | LOW | BEST-PRACTICE | `test_delay_capped_at_30_seconds` asserts nothing about the 30s cap (redundant + misleading). |
| TST-005 | LOW | BEST-PRACTICE | `test_empty_path_rejected` actually accepts `Path(".")`; misleading name. |
| TST-006 | MEDIUM | BEST-PRACTICE | `_sanitize_title` (Windows filename safety, exported API) has zero tests. |
| TST-007 | MEDIUM | BEST-PRACTICE | `_fetch_playlist_with_retry` token-refresh logic only ever mocked, never run. |
| TST-008 | LOW | BEST-PRACTICE | `setup_signal_handlers` (incl. Windows fallback) and `_resolve_cookies` untested. |

### Phase 08 — Code Quality, Security & Maintainability
> QLT-002 and QLT-004 REJECTED (factual errors). QLT-001 RECLASSIFIED → ARCHITECTURE_PATTERN (intentional backward-compat facade).

| ID | Severity | Type | Issue |
|----|----------|------|-------|
| QLT-001 | MEDIUM | ARCHITECTURE_PATTERN | `downloader.py` re-exports 25+ symbols it does not own (intentional `# Re-export for backward compatibility`); creates hidden test coupling. |
| QLT-003 | LOW | BEST-PRACTICE | `read_progress(duration_ms=...)` parameter is unused; docstring promises non-existent percentage logic. |
| QLT-005 | LOW | BEST-PRACTICE | `download_timeout` default `300` duplicated across `config.py` and `downloader_throttle.py` → drift risk. |
| QLT-006 | LOW | BEST-PRACTICE | BEST/WORST selection ranks `height=None` streams as 0/infinity → mis-ordered. |
| QLT-007 | LOW | BEST-PRACTICE | `Any` used at the yt-dlp boundary (only `Any` in `src/`); document the deviation (low ROI). |

### Phase 09 — Structural Code Quality
> STR-001, STR-003, STR-004 REJECTED. STR-002 MERGED → CLI-001. STR-008 MERGED → QLT-001.

| ID | Severity | Type | Issue |
|----|----------|------|-------|
| STR-005 | MEDIUM | BEST-PRACTICE | `_download_single` (cli.py) — CC 17 (only rank-C function), 93 lines, 5+ responsibilities. |
| STR-006 | MEDIUM | BEST-PRACTICE | Orchestrator functions take up to 11 parameters; introduce parameter objects. |
| STR-007 | LOW | BEST-PRACTICE | Duplicated output-path/filename logic in `cli.py` with inconsistent fallback filenames (single vs batch). |

---

## 3. Rejected Findings (removed from report)

| ID | Phase | Reason |
|----|-------|--------|
| TST-001 | 07 | Evidence partially incorrect; `_attempt_segment_resume` is private/unexported; component functions ARE tested. Severity overstated. |
| QLT-002 | 08 | Claims dead code; methods ARE called in `test_downloader_throttle.py` (not in production, but not "zero call sites"). |
| QLT-004 | 08 | Claims `dist/` violates conventions; `dist/` IS in `.gitignore`. Valid remediation remains (delete scratch files). |
| STR-001 | 09 | Claimed nesting depth 5 in `read_progress`; AST shows max depth 4. Severity overstated. |
| STR-003 | 09 | `_retry_429_with_backoff` already decomposed into helpers; describes outdated state. |
| STR-004 | 09 | `_extract_urls_from_json` is 18 lines; splitting has negative ROI per rule 4. |

## 4. Merged / De-duplicated Findings

| Original | Merged Into | Rationale |
|----------|-------------|-----------|
| STR-002 | CLI-001 | Shares root cause with batch error-handling; overlapping changes. |
| STR-008 | QLT-001 | Identical re-export facade issue; QLT-001 already validated. |
| DF-001 | SRV-003 | Same segment-resume counter bug (Phase 06 / Phase 03). |
| DF-002 | SRV-003 | Same "re-download all segments" behavior bug. |

---

## 5. Cross-Phase Themes & Root Causes

1. **Unimplemented `CookieSource.FILE` is the most pervasive latent defect.** CFG-001 (silent no-op in CLI flow) and SEC-002 (hard `NotImplementedError` in API path) / INT-004 describe the same unimplemented value from three angles. **Fix once, consistently**: reject `FILE` at the CLI/config boundary with a clear error, or remove it from the enum until implemented.

2. **Segment-resume is fundamentally broken.** SRV-003 (HIGH) + SRV-007 + DF-001 + DF-002 all stem from `download_hls_with_resume` never resetting metadata and accumulating counts. This is the single highest-impact correctness defect. Fix by (a) skipping already-present `.ts` files and (b) basing the merge decision on on-disk segment count.

3. **BROWSER cookie-source quality handling is broken.** SRV-005 (MEDIUM, mandatory) conflicts with documented ffmpeg+numeric usage (quality-selection.md, vkdownloader-limitations.md). Reuse the pre-selected stream URL instead of re-selecting on the single `best` browser stream.

4. **Batch error masking.** CLI-001 (HIGH) + STR-002/STR-005 (structural) all converge on `cli.py` batch exception handling. Fixing CLI-001 also simplifies STR-002.

5. **Lifecycle/resource cleanup gaps.** INT-001 (Playwright leak), INT-002/INT-006 (shutdown), INT-009/INT-010 (temp-file cleanup) should be addressed with a unified graceful-shutdown + temp-file-cleanup strategy.

6. **Test suite favors mock-everything with log/return assertions.** TST-002/003/006/007/008 identify the highest-risk control-flow paths (resume/fallback, token refresh, method dispatch, `_sanitize_title`) as effectively unverified.

---

## 6. Recommended Remediation Order

1. **SRV-003** + **DF-001/DF-002** — fix segment resume (HIGH, silent data-loss / no output).
2. **CLI-001** — fix batch error masking (HIGH, hides failures).
3. **CFG-001 + SEC-002 + INT-004** — resolve unimplemented `FILE` cookie-source consistently.
4. **SRV-005** — fix BROWSER numeric-quality rejection (mandatory SPEC-DEVIATION).
5. **SEC-001** — harden cookie-file permissions.
6. **INT-001/002/006/009/010** — resource-leak + shutdown + temp-file cleanup hardening.
7. Address MEDIUM advisory findings (CFG-002, CLI-002/003, INT-003/005/007/008, TST-*, QLT-001/003/005/006/007, STR-005/006/007).
8. Address LOW advisory findings (CFG-003/004/005/006, CLI-004, SRV-001/002/004/006/007, SEC-003, TST-004/005/008, QLT-*).

---

## 7. Validation Artifacts

All per-phase validated reports are retained under `.ai/audit/99-validation/`:

- `01-audit-cli-validated-findings.md`
- `02-audit-config-validated-findings.md`
- `03-audit-services-validated-findings.md`
- `04-audit-security-validated-findings.md`
- `05-audit-integrations-validated-findings.md`
- `06-audit-data-flow-validated-findings.md`
- `07-audit-tests-validated-findings.md`
- `08-audit-quality-validated-findings.md`
- `09-structural-quality-validated-findings.md`

Raw executor findings (pre-validation) are under `.ai/audit/<phase>/findings.md`.

---
*Generated by the multi-agent audit orchestrator. All findings independently validated by `validator` subagents (model: poolside/laguna-m.1:free). Production code was NOT modified.*
