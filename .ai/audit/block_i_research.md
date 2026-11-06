# Block I Research — Trustworthy progress, bytes, speed and ETA

**Author:** researcher  
**Status:** research only (no code changed)  
**Source:** `.ai/plans/MKO_VKIDEO_Refactoring_Plan.md` Block I (lines 632-694)  
**Date:** 2026-11-06  

---

## 1. Current progress architecture map

### 1.1 yt-dlp parser layer (`services/ytdlp_downloader.py`)

Relevant symbols (all currently in production):

- `_YTDLP_PROGRESS_LINE_RE` — classifies a line as live progress.
- `_YTDLP_PROGRESS_RE` — extracts `pct`, `~` estimate flag, `size`, `size_unit`, speed, ETA, optional `(frag i/n)`.
- `_SIZE_UNITS` — byte multipliers including `TiB`/`TB`.
- `ProgressState` dataclass (`downloaded`, `total`, `fragment_index`, `fragment_count`, `is_estimate`).
- `_parse_ytdlp_progress_state(line)` — three branches:
  1. percent-and-size (`downloaded = total * pct / 100`);
  2. byte-count only (no total);
  3. percent-only fallback.
- `_parse_ytdlp_progress(line)` — legacy adapter returning `(downloaded, total)` or `None`.
- `_monitor_progress()` / `_drain_output()` — parse each decoded line and invoke:

```python
if fragment_count > 0:
    progress_callback(video_id, fragment_index, fragment_count)   # segments-as-(downloaded,total)
elif total > 0:
    progress_callback(video_id, downloaded, total)                # bytes
else:
    progress_callback(video_id, downloaded, 0)
```

Observed facts:

- `ProgressState.is_estimate` correctly records the `~` marker.
- The parser ignores yt-dlp's ETA text entirely; no ETA value is produced.
- The parser does not validate `pct` bounds, negative/overflow values, or impossible sizes.
- The monitor **overloads** `(downloaded, total)` with either segment counts or bytes depending on branch. No unit accompanies the update.
- On HLS, `fragment_count > 0` wins, so the byte size from the same line is discarded; progress becomes segment-based, and no byte throughput is measurable from yt-dlp output.
- On child restart, the monitor restarts at `frag 1`; nothing anchors to job-level verified progress.

### 1.2 Legacy callback contract

- `progress_callback: Callable[[str, int, int], None] | None` threaded through `downloader.download_video`, `download_with_ytdlp_with_resume_fallback`, `_download_with_ytdlp`, and segment paths.
- Segment backend reports segment counts: `progress_callback(video_id, downloaded_count, len(segments))`.
- `batch_downloader._on_progress(video_id, downloaded, total)` forwards to `RichProgressReporter.update(index, downloaded, total)`.

### 1.3 `ProgressManager` (`services/downloader_throttle.py`, lines 197-225)

- State: `dict[int, tuple[int, int]]` (downloaded, total).
- `get_formatted_progress()` heuristic:
  - `total <= 0` → bytes only;
  - `total > 1024` → bytes with SI formatting;
  - else → `{downloaded}/{total} segments`.
- This heuristic is the exact source of the "fragments confused with bytes" bug: 1,895 segments is `> 1024`, so a segment count is formatted as bytes.

### 1.4 Rich display (`services/progress_display.py`)

- `RichProgressReporter.update(index, downloaded, total)` stores `_last_values`.
- `total > 0` forwards `total=total, completed=downloaded` to rich; `total <= 0` forwards `completed=downloaded` only.
- Columns include `TransferSpeedColumn()` and `TimeRemainingColumn()`, whose ETA/speed are computed by rich from completed/total samples.
- Non-TTY path emits throttled `download_progress` with `downloaded`, `total`.
- No concept of phase, verified bytes, attempt id, or trustworthy ETA.

### 1.5 Batch orchestration (`services/batch_downloader.py`)

- `_on_progress` maps `(video_id, downloaded, total)` → reporter.
- Reporter is per batch; indices are isolated in dicts.
- Progress is callback-driven; no checkpoint anchoring.

### 1.6 Checkpoint/state machine (Blocks E/G)

- `checkpoint.JobCheckpoint` / `SegmentRecord` provide verified segment count, sizes, SHA-256, generation id.
- `state_machine.DownloadJobState` already exposes counters needed by Block I:
  `verified_segments`, `expected_segments`, `verified_bytes`, `network_bytes_this_session`, `fragment_done`, `fragment_total`, `attempt_id`, `state`.
- These counters are currently **not consumed** by progress code (Block G audit BG-001 confirms state machine is passive).

### 1.7 Existing tests

- `tests/test_hls_downloader.py::TestYtdlpProgressParsing` and `TestYtdlpProgressLineDetection` cover parser templates but not the three plan samples or invalid values.
- `tests/test_progress_display.py` covers rich reporter behavior, disabled path, handlers.
- `tests/test_downloader_throttle.py::TestProgressManager` covers heuristic formatting.
- No tests for trustworthy ETA, checkpoint-anchored multi-run progress, or impossible TiB/negative ETA.

---

## 2. Gap analysis

| # | Gap | Evidence | Impact |
|---|-----|----------|--------|
| G1 | `(downloaded, total)` is overloaded with segments vs bytes | monitor branch + ProgressManager heuristic | Wrong units, fake percentages, wrong ETA |
| G2 | yt-dlp estimated total (`~`) is multiplied into `downloaded` as if factual | `_parse_ytdlp_progress_state`: `downloaded = int(total * pct / 100)` with `is_estimate` only informational | 1-2 TiB "downloaded bytes" propagated as fact |
| G3 | No validation of pct bounds or totals | parser accepts any float | `%` can exceed 100 in UI if source is malformed |
| G4 | ETA text is parsed but discarded; negative ETA can leak if any future consumer uses it | `_YTDLP_PROGRESS_RE` captures `eta`, code ignores it | `-4377:33:21` must never reach UI |
| G5 | No phase model | only `ProgressStatus` (success/failed/...) | Cannot show refreshing/waiting/merging/verifying |
| G6 | No separation of verified bytes on disk vs network bytes this session | ProgressState has only downloaded/total | Transfer rate and ETA unreliable |
| G7 | Child restart rolls progress back to frag 1 | monitor resets; no checkpoint anchoring | False backward jumps |
| G8 | Rich's `TimeRemainingColumn`/`TransferSpeedColumn` derive ETA from rich's own sampling | progress_display columns | Conflicts with policy; can show fake active transfer during waits |
| G9 | ProgressManager heuristic cannot distinguish units | `total > 1024` | Must be replaced with explicit unit/phase |
| G10 | No adapter to preserve `progress_callback` API | direct signature change would break callers/tests | Migration risk |
| G11 | State machine counters exist but are unused by progress | BG-001 | Block I cannot consume verified progress until G is wired |
| G12 | No tests for plan's false TiB/negative ETA samples | test suite | RED coverage missing |

---

## 3. Proposed domain model

### 3.1 `JobPhase` (new StrEnum, in `models/enums.py` or `services/progress.py`)

```python
class JobPhase(str, Enum):
    DOWNLOADING = "downloading"
    REFRESHING_TOKEN = "refreshing_token"
    WAITING = "waiting"
    MERGING = "merging"
    VERIFYING = "verifying"
```

Mapping guidance (depends on G):

- `DownloadState.DOWNLOAD` / `RETRY_SAME_SEGMENT` / `RATE_LIMIT_WAIT` → `WAITING` when backoff active, else `DOWNLOADING`.
- `REFRESH_STREAM` → `REFRESHING_TOKEN`.
- `VERIFY_MEDIA` → `VERIFYING`.
- `COMMIT` with merge → `MERGING`.

### 3.2 `ProgressSnapshot` (frozen dataclass)

```python
@dataclass(frozen=True)
class ProgressSnapshot:
    job_id: str
    phase: JobPhase
    verified_segments: int
    expected_segments: int | None
    verified_bytes_on_disk: int
    network_bytes_this_session: int
    transfer_rate_bytes_per_sec: float | None
    eta_seconds: float | None
    is_estimate: bool
    attempt_id: int
    # optional, non-breaking diagnostics:
    child_fragment_index: int = 0
    child_fragment_count: int = 0
    measured_at: float | None = None
```

Notes:

- `verified_bytes_on_disk` must come from checkpoint/segment records (E), not from yt-dlp `%`.
- `network_bytes_this_session` is for transfer-rate calculation; for yt-dlp it should only advance when the parsed total is exact (`is_estimate=False`) or when transport-level counters are available.
- `is_estimate` is `True` when any component (yt-dlp `~`, TiB threshold, or segment-size variance) is not authoritative.
- Frozen + immutable ensures safe sharing across callbacks and threads.

### 3.3 Parsing validation additions

`_parse_ytdlp_progress_state` should:

1. Clamp/validate `pct` to `[0, 100]`; if outside, return `None` or a state with `pct=None` and `is_estimate=True` (recommended: return `None` for malformed, log at DEBUG).
2. Ensure `downloaded <= total` after derivation; otherwise mark `is_estimate=True` and set `downloaded=min(downloaded,total)`.
3. Record `eta_seconds=None` for `--:--:--`, `Unknown`, missing, or negative ETA.
4. Parse ETA defensively:
   - `MM:SS`, `HH:MM:SS` → seconds; reject if any component negative or total negative.
   - `--:--:--` → None.
   - `Unknown` → None.
5. Flag `is_estimate=True` for `~`.
6. For TiB totals (`>= 1 TiB`) with `~`, keep `is_estimate=True` and emit `progress_estimate_unreliable` via C's diagnostics (reason code `estimated_size_implausible`).

### 3.4 Adapter to legacy callback

Preserve `progress_callback(video_id, downloaded, total)` through an adapter:

- New optional `progress_snapshot_callback: Callable[[str, ProgressSnapshot], None] | None`.
- When only legacy callback is provided, derive `(downloaded, total)` from snapshot:
  - If `verified_segments`/`expected_segments` known → segments.
  - Else if `network_bytes_this_session` known → bytes.
  - Else `(0, 0)`.
- This keeps all existing tests/callers working until migration.

---

## 4. ETA policy

1. **Primary basis:** completed verified segments over a sliding window (30-90 s), using checkpoint timestamps/counts (E). Convert to ETA using remaining verified segment count, not byte %.
2. **Byte throughput supplement:** use real network byte throughput only when totals are exact and non-estimate; otherwise ignore.
3. **Variable segment sizes:** do not assume equal byte size; estimate remaining bytes from average verified segment size or media segment durations, and mark `is_estimate=True` when variance is high.
4. **Exclude waits:** intentional backoff/refresh/wait periods must not contribute to transfer rate. They may contribute to overall completion estimate only if a defensible wait duration is known (e.g., Retry-After).
5. **Restart anchoring:** job-level verified counters come from checkpoint/state machine; a child's `frag 10` never replaces `verified_segments=603`.
6. **Invalid ETA:** render `ETA: unknown` when insufficient data, inconsistent manifests, or non-positive/negative values. Never emit negative seconds.
7. **Phase honesty:** during refresh/wait/merge/verify, display phase text and do not show active transfer speed.
8. **Bounds:** ETA must be finite and `>= 0`; clamp tiny/negative to unknown, not to 0 silently unless genuinely complete.

---

## 5. Minimal change set

### New files

- `src/vkdownloader/services/progress.py` (or `models/progress.py`): `JobPhase`, `ProgressSnapshot`, `ProgressEstimator`, `eta_from_snapshot()`, adapter helpers.
- `tests/test_progress.py` (RED/GREEN): parser validation, snapshot invariants, ETA policy.

### Modified files

- `src/vkdownloader/models/enums.py`: add `JobPhase` StrEnum.
- `src/vkdownloader/services/ytdlp_downloader.py`:
  - harden `_parse_ytdlp_progress_state` (bounds, ETA parse, TiB flag).
  - add `progress_snapshot_callback` parameter to download functions.
  - in `_monitor_progress`/`_drain_output`, build `ProgressSnapshot` from parsed state + state machine counters; invoke new callback; keep legacy adapter.
  - do not roll back job counters on child restart.
- `src/vkdownloader/services/downloader.py`: pass state machine + attempt id into progress snapshot construction.
- `src/vkdownloader/services/progress_display.py`:
  - add `update_snapshot(index, snapshot)`; keep `update` as adapter.
  - add phase display and trustworthy ETA rendering; avoid rich's misleading ETA during waits (custom column or description suffix).
- `src/vkdownloader/services/downloader_throttle.py`:
  - replace `ProgressManager` heuristic with explicit unit-aware storage (`ProgressSnapshot` or `(value, total, unit)`).
  - update tests accordingly.
- `src/vkdownloader/services/batch_downloader.py`:
  - `_on_progress` accepts snapshot; passes to reporter; keep legacy adapter.
- `src/vkdownloader/services/segment_downloader.py`: report `ProgressSnapshot` with verified segment counts from checkpoint/state machine, not raw counts only.
- `src/vkdownloader/services/state_machine.py`: expose convenience accessor for counters (already present) and optional `update_progress_counters()`.

### Compatibility

- Keep `progress_callback` until all callers migrate (plan requirement).
- Adapter ensures old tests pass during transition.

---

## 6. Risks

- **API churn:** Changing callback signatures risks widespread test breakage; adapter mitigates.
- **Rich ETA conflict:** Rich's `TimeRemainingColumn` may still compute from completed/total; must either feed verified counts only or replace with custom column. Risk of double/conflicting ETA.
- **Checkpoint coupling:** Verified bytes require E's checkpoint to be populated and valid; until G/E fully wired, snapshot may show zeros. Must not fabricate bytes.
- **Performance:** Computing SHA/averages per progress update could stall UI; use cached checkpoint sizes.
- **Thread safety:** Snapshots are immutable but state machine counters may be updated concurrently; read under existing locks or copy.
- **Windows/Unicode:** Progress lines and titles already sanitized; ETA formatting must be ASCII-safe.
- **Test expectations:** ProgressManager heuristic tests will change; must update RED tests intentionally, not weaken them.
- **Overengineering:** Keep model minimal; avoid premature estimator complexity.

---

## 7. RED test plan (tests to write before implementation)

### Parser validation (`tests/test_hls_downloader.py` / new `tests/test_progress.py`)

- `test_plan_sample_false_tib_estimate_flagged`:
  - input: `[download]  20.0% of ~  42.03GiB at  696.50KiB/s ETA 26:40:31 (frag 380/1895)`
  - assert `is_estimate is True`, `fragment_index=380`, `fragment_count=1895`.
- `test_plan_sample_1_65_tib_estimate_flagged`:
  - input: `[download]   0.5% of ~   1.65TiB at  259.73KiB/s ETA --:--:-- (frag 10/1895)`
  - assert `is_estimate is True`, eta None.
- `test_plan_sample_negative_eta_not_accepted`:
  - input: `[download]   0.6% of ~   1.38TiB at  438.36KiB/s ETA -4377:33:21 (frag 12/1895)`
  - assert eta_seconds is None; `is_estimate is True`.
- `test_pct_out_of_bounds_rejected`:
  - `101.0%`, `-1.0%` → parser returns None or invalid flag; never `downloaded > total`.
- `test_downloaded_never_exceeds_total`.
- `test_malformed_lines_do_not_crash` (empty, binary, long lines).
- `test_eta_unknown_and_dash_return_none`.
- `test_eta_hh_mm_ss_parsed`.
- `test_byte_count_branch_no_total`.

### Snapshot invariants (`tests/test_progress.py`)

- `ProgressSnapshot` is frozen.
- `verified_bytes_on_disk` cannot be derived from `pct * estimated total` in tests (assert source uses checkpoint).
- `attempt_id` preserved.
- `eta_seconds` is None or `>= 0`.

### ProgressManager (`tests/test_downloader_throttle.py`)

- Replace heuristic expectations with explicit unit:
  - segments vs bytes are stored separately; 1,895 segments renders as segments even though `> 1024`.
  - unknown total renders downloaded only.
- Threading/concurrency unchanged.

### Progress display (`tests/test_progress_display.py`)

- New `update_snapshot` path renders phase and `ETA: unknown` when None.
- No negative ETA text.
- TTY and non-TTY output.
- Unicode titles.
- Batch isolation: two indices do not share snapshots.

### Multi-run anchoring (new, depends on E/G)

- Checkpoint with 603 verified segments; child reports frag 10; snapshot.verified_segments remains 603; no backward jump.
- Child frag count does not overwrite expected_segments if checkpoint has better value.

### ETA policy (new)

- Insufficient data → None/unknown.
- Wait periods excluded from rate (mock backoff).
- Variable segment sizes → is_estimate True.
- Negative/NaN inputs → unknown.

---

## 8. Dependencies and deferrals

- **Depends on C:** diagnostic event `progress_estimate_unreliable`, sanitized child transcript, attempt ids, redaction.
- **Depends on E:** verified bytes/segments from checkpoint; content identity; no fabrication of bytes.
- **Depends on G:** `DownloadJobState` counters and attempt id; phase transitions; refresh/wait phases. Note BG-001: state machine is currently passive; Block I consumption requires G wiring first.
- **Defer J:** full integration/acceptance matrix and release gating are not part of this research; only note that J's "Parser receives false TiB estimate/negative ETA → shows known verified bytes and ETA: unknown" maps to tests above.

---

## 9. Confidence

- Parser behavior and heuristic bug: HIGH (direct source inspection).
- Proposed model and ETA policy: MEDIUM (design proposal; requires G/E wiring).
- Rich display changes: MEDIUM (requires UX validation).
- Test feasibility: HIGH (existing test patterns support it).
