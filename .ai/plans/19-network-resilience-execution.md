# Plan 19 — Network Resilience Execution Plan

> **Status**: DRAFT — execution roadmap derived from Plan 07 §1.5 + Auditor `{code_context}`
> **Base**: `07-network-resilience-audit-fixes.md`
> **Last verified tree**: `HEAD = 009f9fc`

## §1 — Corrected Execution Status (from Plan 07 §1.5)

| Block | Finding | Status | Remaining Work |
|---|---|---|---|
| B1 | NET-001 | **DONE** (tree) | Add proving tests: `TestMergeBatchSegments` + `_log_preserve_segments` empty-dir test |
| B2 | VAL-001 | **DONE** | Add missing test: SSL-verification warning oracle |
| B3 | VAL-004 | **DONE** | No tests needed (prose fix) |
| B4 | NET-009/004/002/010 | **DONE** (tree) | Tests exist with different names — verify coverage |
| B5 | NET-017 | **DONE** (tree) | Tests exist (22 in `test_quality_selector.py`) — verify coverage |
| B6 | NET-016 | **DONE** (verified) | None |
| B7 | NET-008 | **BLOCKED** (research-gated) | Researcher: confirm `vkvideo.ru` ↔ `vk.com` CDN origin sharing |
| B8 | NET-005 | **DONE** (tree) | Tests exist (`TestRefreshQualitySelection`) — verify coverage |
| B9 | NET-003 | **PARTIAL** | Fix format-selector `worst→best` inversion; add `m3u8_url` param; re-scope pinned test |
| B10 | NET-015 | **DROP** | `download_with_ffmpeg` / `DownloadMethod.FFMPEG` deleted by `d572d96` |
| B11 | NET-006/007 | **PARTIAL** (see §2) | Collapse 3 ClientTimeout compositions into helper; add merge budget; §3.9 decisions |
| B12 | NET-012 | **PARTIAL** (split) | Switch to `re.fullmatch`; defer host-constant to B7 Researcher |
| B13 | NET-013 | **DONE** (tree) | Add proving test: `-N` value, `--referer` present |
| B14 | NET-014 | **DEFER** (product decision) | Decouple concurrency levels; add new setting |
| B15 | NET-018 | **NOT DONE** | Parse all 3 date forms; fix ceiling-after-max; reconcile with `83ba0f8`; §3.13 decision |
| B16 | NET-011 | **DONE** (tree) | None (comment-only) |

**Test baseline**: 993 passed, 3 skipped, 0 failed (re-run at assessment).

## §2 — Blocks Requiring Action

### B11 — §3.9 Decisions (Tech Lead)

Four forks in Plan 07 §3.9. Simplest options that close the findings:

1. **Helper placement**: **(a)** in `downloader_throttle.py` — `segment_downloader.py` already imports it; the third site is inside `downloader_throttle.py` itself, so no new edge is added.
2. **sock_read shape**: `download_timeout` itself — true per-read ceiling that grows with the setting; no new field.
3. **Merge-budget formula**: **(c)** per-stage constant — simplest; satisfies criterion 3 (budget ≠ HTTP setting).
4. **CLI option**: omit — status quo for `download_timeout` (env/`.env`-only).

> **Constraint**: Must not add a `src/` module (avoids `EXPECTED_SDIST_ENTRIES` change). Must not add `ffmpeg_utils → downloader_throttle` edge.

### B9 — Fix format-selector inversion + address handoff

**Current state**:
- `ytdlp_downloader.py:733-734`: format-selector ternary uses `best` but with `worst → best` inversion
- `_download_with_ytdlp` (line 1083): NO `m3u8_url` parameter; receives `video_url` (page URL)
- `cmd.append(video_url)` at line 1152: passes page URL, not m3u8 URL
- `test_cli_command_format_best_when_quality_not_digit` pins the defect

**Required**:
1. Fix inversion: `worst` selects worst, `best` selects best
2. Add `m3u8_url` parameter to `_download_with_ytdlp`
3. Pass selected address to child process
4. Re-scope `test_cli_command_format_best_when_quality_not_digit`
5. Add proving tests: `test_cli_command_format_best_for_best_quality`, `test_cli_command_format_worst_for_worst_quality`, `test_child_receives_selected_address`

### B12 — URL gate anchoring (host-constant deferred to B7)

**Current state**:
- `extractor.py:27`: `VIDEO_ID_PATTERN = re.compile(r"video-(-?\d+)_(\d+)")` with unanchored `.search`
- 3 `url.split("_")[-1]` slices remain

**Required**:
1. Switch `.search` → `re.fullmatch` with `^...$` anchors
2. Consolidate URL parsing into single identifier-derived path
3. Add `test_video_url_acceptance_table` data-driven test
4. Defer host-constant to B7 Researcher

### B15 — Parse all date forms + ceiling-after-max + reconcile `83ba0f8`

**Current state**:
- `_parse_retry_after` (downloader_throttle.py:314-345): parses only IMF-fixdate (`%a, %d %b %Y %H:%M:%S GMT`); misses RFC 850 + asctime
- `_compute_backoff_delay` (lines 348-380): `min(delay, 30.0)` ceiling applied to local term BEFORE `max(delay, retry_after_seconds)` → Retry-After: 600 produces 600s wait
- **Conflict with `83ba0f8`**: comment says "Retry-After is a floor" (uncapped)

**Required** (contingent on user decision in §4):
- If **clamped floor**: add RFC 850 + asctime parsing; reorder ceiling-after-max; update `83ba0f8` comment
- If **uncapped floor**: amend B15 spec; do not reorder ceiling

### B14 — Concurrency decoupling (product decision)

**Current state**: `max_concurrent_downloads` (default=4, range 1-16) drives:
1. Batch gate (whole-video permit) — `batch_downloader.py`
2. Segment fan-out semaphore — `segment_downloader.py`
3. yt-dlp child `-N` argument — `ytdlp_downloader.py:757`
4. TCPConnector `limit` and `limit_per_host` — `segment_downloader.py:733-746` (NOT to be touched per plan)

**Required** (contingent on user decision in §4):
- Add new `max_concurrent_segments` setting if option (a) chosen
- Update `ytdlp_downloader.py` `-N` to carry new value
- Update batch gate to use `max_concurrent_downloads`
- Update `config.py` descriptions
- Update `docs/11-guides/configuration.md` + `.env.example`

## §3 — Execution Order

```
Step 0: This plan is written (current step)
Step 1: User decisions — B14 shape, B15 clamp-vs-uncapped (+ §3.13 ceiling scope)
Step 2: B11 §3.9 decisions (Tech Lead) → Planner + Implementor
Step 3: B11 implementation (ClientTimeout helper + merge budget) → Implementor + tests
Step 4: B15 implementation (contingent on B11 + user decision) → Implementor + tests
Step 5: B9 implementation (independent) → Implementor + tests
Step 6: B12 anchoring (independent) → Implementor + tests
Step 7: B7 Researcher assignment (parallel) → Researcher
Step 8: B14 implementation (contingent on user decision) → Planner + Implementor + tests
Step 9: B2 + B13 + B4 + B5 + B8 + B16 proving tests (parallel) → Implementor
Step 10: Documentation updates
Step 11: Validation (pytest + ruff + mypy)
```

**Dependencies**:
- B15 depends on B4 (done) + B11 (Step 2-3) — `C12`
- B14 independent (no code deps, needs product decision)
- B9, B12 independent (no deps)
- B7 research blocks B7 + B12-host-constant half
- B13 depends on B14 (if `-N` changes) — else independent

## §4 — Product Decisions Requiring User Input

### Decision 1 — B14: Which level does `max_concurrent_downloads` govern?

Plan 07 §3.12 presents three shapes:

- **(a)** `max_concurrent_downloads` governs **whole videos only** (its declared meaning); a new `max_concurrent_segments` governs the per-item fan-out. **New setting with new default.** Existing operators' video-level concurrency does not change. *(Plan recommendation — simplest that closes the finding.)*
- **(b)** `max_concurrent_downloads` governs the **per-item fan-out** (where the traffic actually is); a new setting governs whole videos. **Inverts the setting's declared meaning** — worst for compatibility.
- **(c)** No new setting; derive the video-level count from something already present. **Makes the bound implicit** — does not satisfy the finding's "declared rather than inherited" requirement.

### Decision 2 — B15: Should `Retry-After` be clamped to the 30s ceiling or remain an uncapped floor?

- **Clamp**: Apply `min(delay, 30.0)` **after** `max(delay, retry_after_seconds)`. `Retry-After: 600` → 30s wait. Requires updating commit `83ba0f8`'s comment. *(Plan B15 spec.)*
- **Uncapped floor**: Keep `83ba0f8`'s documentation — Retry-After can exceed the 30s ceiling. Amends B15's acceptance criterion 4.

### Decision 3 (only if Decision 2 = Clamp) — B15 §3.13: Is the ceiling per-request or per-video?

- **Per-request**: Every request can wait up to the 30s ceiling. A batch of N videos can have `⌈N/100⌉+1` waits simultaneously.
- **Per-video**: The 30s ceiling is the total retry budget per video. A slow origin degrades the batch rather than the request.

## §5 — Verification Strategy

The four project verification commands:
```
uv run pytest -q -rs
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
```

Target: 993 + (new proving tests) passed, 3 skipped, 0 failed; zero lint errors; zero mypy errors.
