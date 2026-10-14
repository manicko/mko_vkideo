# Audit Problems Found — Plan 09 Verification

## Context

Audit of `.ai/plans/09-concurrency-cancellation-audit-fixes-completion.md` to verify
that all four blocks (B8, B9, B10, B11) were fully executed and committed.

## Verification Result: PLAN COMPLETE

All four blocks are committed and are ancestors of the current HEAD:

| Block | Commit | Finding/Topic | Status |
|-------|--------|--------------|--------|
| B8 | `514a210` | CON-009: transport pool ceiling from `max_concurrent_downloads` | DONE — code + tests + docs |
| B9 | `8611a31` | CON-010: exit-path bound in `download_timeout` description | DONE — docs-only, no runtime change |
| B11 | `3c25dda` | phase04/VAL-404: legal encoding for a not-executed finding | DONE — template + handbook + validator |
| B10 | `e6a556c` | CON-002: verification record | DONE — new record file committed |

Verification gates at HEAD (`3b95d65`):
- `uv run pytest -q` — 993 passed, 3 skipped, 1 warning
- `uv run ruff check src tests` — All checks passed!
- `uv run ruff format --check src tests` — 55 files already formatted
- `uv run mypy src` — Success: no issues found in 31 source files
- Read-only audit gate — PASS (both audit paths byte-identical to HEAD)
- B8/B9 block tests (`test_segment_downloader.py`, `test_config.py`) — 170 passed

## Documentation Issues Found

### ISSUE-01: `docs/01-tools/api-reference.md` — outdated `download_timeout` description

**File:** `docs/01-tools/api-reference.md`, line 443

**Current text:**
```
| download_timeout | int | 300 | Total timeout for HTTP request in seconds. |
```

**Problem:** The description in `api-reference.md` does not reflect the
B9 commit (`8611a31`) field-description update in `src/vkdownloader/config.py`.

The code's `download_timeout` field description (after B9) states the setting applies to:
- Individual segment and playlist HTTP requests
- Each ffmpeg merge subprocess
- The off-loop yt-dlp extraction's `wait_for`
- yt-dlp's socket timeout (as library option and CLI flag)

And states critically:
- The extraction thread is NOT stopped on expiry
- The abandoned thread is joined at interpreter shutdown under the
  interpreter's own thread-join rule, NOT under this setting
- It does NOT bound the yt-dlp child's post-drain re-wait (see `download_stall_timeout`)

The api-reference.md description "Total timeout for HTTP request in seconds" is:
1. **Incomplete** — omits the ffmpeg, yt-dlp extraction, and CLI flag consumers
2. **Misleading** — "Total timeout" implies it bounds the entire operation
3. **Missing the exit-path rule** — does not state that it does NOT bound the
   thread-join wait, which is the entire point of B9/CON-010

**Status:** This was deliberately left untouched by commit `1a9a555`
("docs(concurrency): align the operator documentation with the landed
concurrency changes"), which explicitly lists `docs/01-tools/api-reference.md`
among files "Not touched, with reasons recorded in the block report."
However, the discrepancy remains a documentation gap: a reader using the
API guide as reference gets a different, misleading description than the
code's field description.

**Owner:** Documentation ownership; the configuration guide's `download_timeout`
row is unowned per plan 09 D1/Q1 (plan 07's C12 never landed), and this
api-reference entry falls in the same coordination gap.

### ISSUE-02: `docs/01-tools/api-reference.md` — missing `download_stall_timeout` field

**File:** `docs/01-tools/api-reference.md`

**Problem:** The `download_stall_timeout` field (added in `5dc5912`, after the
plan's completion) does not appear in the API reference's Settings listing or
the example `.env` section. The `docs/11-guides/configuration.md` table
includes it (line 32), but `api-reference.md` does not. This is a general
docs drift issue, not caused by plan 09's work.

## Conclusion

Plan 09's four blocks are fully executed and committed. No code changes
(`_fix`) are required. The plan should be renamed to `_done` and moved to
`.ai/plans/done/`. The two documentation issues above are out of plan scope
but are recorded here as findings for future documentation work.
