# B4 Unblock Report — External Gate P11 Analysis

**Date:** 2026-10-11
**Author:** Tech Lead
**Subject:** Determining whether B4 (QLT-011: downloader_throttle.py split) is unblocked

---

## Summary

**The "External gate P11" constraint on B4 is RESOLVED.** No external plan dependency prevents B4 from being executed. The naming "P11" is a **plan-renumbering artifact** from the audit restructuring, and the commits it referred to have all landed.

---

## Root Cause of the Confusion

The code-quality plan (.ai/plans/14-code-quality-audit-fixes_fix.md) references "Plan 11" as an external gate:

> **Preconditions.** P11-B2 and P11-B5 have landed (ytdlp_downloader.py).

The "Plan 11" numbering comes from the original planning phase, before audit phases were renumbered. The audit phase-to-plan mapping:

| Audit Phase | Directory | Current Plan File | Plan Number |
|---|---|---|---|
| Phase 06 | 06-credentials-secrets | 11-credentials-secrets-audit-fixes.md | Plan 11 |
| Phase 08 | 08-cli-observability | 13-cli-observability-audit-fixes_fix.md | Plan 13 |
| Phase 09 | 09-code-quality | 14-code-quality-audit-fixes_fix.md | Plan 14 |

The "P11" reference in the code-quality plan actually points to **Phase 08 (CLI Observability) = Plan 13**, based on:
1. The commits referenced in execution (P13-B2, P13-B5, P13-B6) match CLI observability commits
2. Plan 13 (CLI observability) writes to ytdlp_downloader.py
3. The code-quality plan's §4.2 says "Plan 11's ytdlp_downloader.py track (B2, B5)" — these are Phase 13 blocks

---

## Landing Status

### Phase 13 (CLI Observability) — ALL LANDED

| Commit | Block | Description |
|---|---|---|
| 3cc2897 | P13-B2 | eat(cli): add --log-level option and fix Live-1 hint |
| 600af4d | P13-B5 | ix(cli): name max_retries bound in validation message |
| 6a62e6c | P13-B6 | ix(logging): derive ConsoleRenderer colors from sys.stderr.isatty() |
| 65d1c0a | P13-B3 | ix(logging): clear exc_info on LogRecord to prevent double traceback |
| 17b0b8b | P13-B4 | eat(observability): add correlation_id + video_id to log records |
| 24dcddc | P13-B7 | eat(observability): record suppressed non-progress child output |

All Phase 13 blocks are in the git history **before** the code-quality plan baseline 24dcddc.

### Phase 12 (Filesystem artifacts) — LANDED

Commit e2c5ad0 (refactor), 40404e2 (fix sweep), 767bb47 (partial-file probe) all landed.

---

## What Needs to Happen for B4

B4 (QLT-011: downloader_throttle.py split) needs to:

### 1. Identify the 5 retry symbols to extract from downloader_throttle.py:
- RETRYABLE_STATUS_CODES (currently L22)
- _retry_429_with_backoff (currently L230)
- _parse_retry_after (currently L333)
- _compute_backoff_delay (currently L376)
- _wait_with_shutdown (currently L417)

### 2. Create a new retry module (e.g., services/retry_policies.py)

### 3. Move the symbols and update imports in:
- services/ytdlp_downloader.py — imports _compute_backoff_delay, _wait_with_shutdown, URLBackoffCoordinator
- services/segment_downloader.py — imports retry-related symbols

### 4. Update services/downloader.py facade if needed

### 5. The symbol-ownership comment in downloader.py:88-107 needs _attempt_segment_resume added to __all__

---

## Recommendation

**B4 can now be executed.** The external gate has landed. The plan's execution order was:

`
PREREQ → B13 → B1 → B2 → B3 → B12 → B7 → B10 → B9 → B8 → B11 → B4(blocked)
`

B4 should now be re-enabled and executed. It was the **only block left NOT DONE** in the plan.

---

## Evidence

- Retry symbols are still in downloader_throttle.py (not yet split)
- Phase 13 commits landed before the plan-14 baseline (24dcddc)
- Plan 14 commits (B1-B3, B5-B12, B13) are all present in the git log
