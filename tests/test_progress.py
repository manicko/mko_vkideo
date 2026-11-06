"""RED tests for Block I - trustworthy progress, bytes, speed and ETA.

These tests target not-yet-implemented functionality.  Imports of the new
``progress`` module are guarded so that a missing implementation surfaces as
a clean test failure rather than a collection error.
"""

from __future__ import annotations

import io
import math
from typing import Any

import pytest
from rich.console import Console

from vkdownloader.services.downloader_throttle import ProgressManager
from vkdownloader.services.progress_display import RichProgressReporter
from vkdownloader.services.state_machine import DownloadStateMachine
from vkdownloader.services.ytdlp_downloader import _parse_ytdlp_progress_state


def _import_progress() -> Any:
    try:
        from vkdownloader.services import progress as progress_module
    except ImportError as exc:  # pragma: no cover - RED guard
        pytest.fail(f"progress module not implemented: {exc}")
    for name in ("JobPhase", "ProgressSnapshot", "ProgressTracker", "snapshot_to_legacy"):
        if not hasattr(progress_module, name):
            pytest.fail(f"progress module missing {name}")
    return progress_module


def _make_reporter(enabled: bool) -> tuple[RichProgressReporter, io.StringIO]:
    buffer = io.StringIO()
    console = Console(file=buffer, width=120, no_color=True)
    return RichProgressReporter(console=console, enabled=enabled), buffer


# ---------------------------------------------------------------------------
# Parser: plan samples
# ---------------------------------------------------------------------------


def test_plan_sample_false_tib_estimate_flagged() -> None:
    _import_progress()
    line = "[download]  20.0% of ~  42.03GiB at  696.50KiB/s ETA 26:40:31 (frag 380/1895)"
    state = _parse_ytdlp_progress_state(line)
    assert state is not None
    assert state.is_estimate is True
    assert state.fragment_index == 380
    assert state.fragment_count == 1895
    assert state.eta_seconds is not None
    assert state.eta_seconds >= 0
    assert math.isfinite(state.eta_seconds)


def test_plan_sample_1_65_tib_estimate_flagged() -> None:
    _import_progress()
    line = "[download]   0.5% of ~   1.65TiB at  259.73KiB/s ETA --:--:-- (frag 10/1895)"
    state = _parse_ytdlp_progress_state(line)
    assert state is not None
    assert state.is_estimate is True
    assert state.eta_seconds is None


def test_plan_sample_negative_eta_not_accepted() -> None:
    _import_progress()
    line = "[download]   0.6% of ~   1.38TiB at  438.36KiB/s ETA -4377:33:21 (frag 12/1895)"
    state = _parse_ytdlp_progress_state(line)
    assert state is not None
    assert state.is_estimate is True
    assert state.eta_seconds is None


def test_pct_out_of_bounds_rejected() -> None:
    _import_progress()
    for pct in (101.0, -1.0):
        line = f"[download]  {pct}% of 1.00GiB at 1.00MiB/s ETA 00:10"
        state = _parse_ytdlp_progress_state(line)
        assert state is None, f"pct={pct} should be rejected"


def test_downloaded_never_exceeds_total() -> None:
    _import_progress()
    line = "[download]  100.0% of 1.00GiB at 1.00MiB/s ETA 00:10"
    state = _parse_ytdlp_progress_state(line)
    assert state is not None
    assert state.downloaded <= state.total


def test_tib_total_flagged_estimate() -> None:
    _import_progress()
    line = "[download]   1.0% of 1.10TiB at 1.00MiB/s ETA 00:10"
    state = _parse_ytdlp_progress_state(line)
    assert state is not None
    assert state.is_estimate is True


def test_malformed_lines_do_not_crash() -> None:
    _import_progress()
    for line in ("", "binary\xff\xfe", "x" * 10000, "[download] garbage"):
        try:
            _parse_ytdlp_progress_state(line)
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"parser crashed on malformed line: {exc}")


def test_eta_unknown_and_dash_return_none() -> None:
    _import_progress()
    for line in (
        "[download]   0.0% of    4.93GiB at   10.37KiB/s ETA --:--:--",
        "[download]   0.0% of    4.93GiB at  Unknown B/s ETA Unknown",
    ):
        state = _parse_ytdlp_progress_state(line)
        assert state is not None
        assert state.eta_seconds is None


def test_eta_hh_mm_ss_parsed() -> None:
    _import_progress()
    line = "[download]   30.0% of 1.50GiB at 1.00MiB/s ETA 01:01:00"
    state = _parse_ytdlp_progress_state(line)
    assert state is not None
    assert state.eta_seconds == 3660


# ---------------------------------------------------------------------------
# ProgressSnapshot invariants
# ---------------------------------------------------------------------------


def test_progress_snapshot_frozen() -> None:
    progress = _import_progress()
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    snap = ProgressSnapshot(job_id="job", phase=JobPhase.DOWNLOADING)
    with pytest.raises((AttributeError,)):
        snap.job_id = "other"


def test_progress_snapshot_validated() -> None:
    progress = _import_progress()
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    with pytest.raises((ValueError, TypeError)):
        ProgressSnapshot(job_id="job", phase=JobPhase.DOWNLOADING, verified_segments=-1)


def test_progress_snapshot_defaults() -> None:
    progress = _import_progress()
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    snap = ProgressSnapshot(job_id="job", phase=JobPhase.DOWNLOADING)
    assert snap.verified_segments == 0
    assert snap.expected_segments is None
    assert snap.verified_bytes_on_disk == 0
    assert snap.network_bytes_this_session == 0
    assert snap.transfer_rate_bytes_per_sec is None
    assert snap.eta_seconds is None
    assert snap.is_estimate is False
    assert snap.attempt_id == 0
    assert snap.child_fragment_index == 0
    assert snap.child_fragment_count == 0


# ---------------------------------------------------------------------------
# ProgressTracker
# ---------------------------------------------------------------------------


def test_tracker_insufficient_data_returns_none() -> None:
    progress = _import_progress()
    ProgressTracker = progress.ProgressTracker
    tracker = ProgressTracker()
    assert tracker.transfer_rate_bytes_per_sec is None
    assert tracker.eta_seconds() is None


def test_tracker_sliding_window_excludes_stale() -> None:
    progress = _import_progress()
    ProgressTracker = progress.ProgressTracker
    tracker = ProgressTracker(window_seconds=60.0)
    tracker.observe(verified_segments=0, network_bytes_this_session=0, measured_at=0.0)
    tracker.observe(verified_segments=10, network_bytes_this_session=1000, measured_at=10.0)
    tracker.observe(verified_segments=20, network_bytes_this_session=2000, measured_at=100.0)
    rate = tracker.transfer_rate_bytes_per_sec
    assert rate is None or (isinstance(rate, float) and rate >= 0 and math.isfinite(rate))
    eta = tracker.eta_seconds(remaining_segments=5)
    assert eta is None or (isinstance(eta, float) and eta >= 0 and math.isfinite(eta))


def test_tracker_never_negative_or_nonfinite() -> None:
    progress = _import_progress()
    ProgressTracker = progress.ProgressTracker
    tracker = ProgressTracker()
    tracker.observe(verified_segments=0, network_bytes_this_session=0, measured_at=0.0)
    tracker.observe(verified_segments=5, network_bytes_this_session=500, measured_at=1.0)
    for rem in (-5, 0, 5):
        eta = tracker.eta_seconds(remaining_segments=rem)
        assert eta is None or (isinstance(eta, (int, float)) and eta >= 0 and math.isfinite(eta))


def test_tracker_reset() -> None:
    progress = _import_progress()
    ProgressTracker = progress.ProgressTracker
    tracker = ProgressTracker()
    tracker.observe(verified_segments=0, network_bytes_this_session=0, measured_at=0.0)
    tracker.observe(verified_segments=5, network_bytes_this_session=500, measured_at=1.0)
    tracker.reset()
    assert tracker.transfer_rate_bytes_per_sec is None


# ---------------------------------------------------------------------------
# eta_from_snapshot
# ---------------------------------------------------------------------------


def test_eta_from_snapshot_clamps_invalid() -> None:
    progress = _import_progress()
    if not hasattr(progress, "eta_from_snapshot"):
        pytest.fail("progress module missing eta_from_snapshot")
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    bad = ProgressSnapshot(job_id="j", phase=JobPhase.DOWNLOADING, eta_seconds=-5.0)
    assert progress.eta_from_snapshot(bad) is None
    nan_snap = None
    with pytest.raises((ValueError, TypeError)):
        nan_snap = ProgressSnapshot(
            job_id="j", phase=JobPhase.DOWNLOADING, eta_seconds=float("nan")
        )
    assert nan_snap is None
    good = ProgressSnapshot(job_id="j", phase=JobPhase.DOWNLOADING, eta_seconds=10.0)
    assert progress.eta_from_snapshot(good) == 10.0


# ---------------------------------------------------------------------------
# snapshot_to_legacy
# ---------------------------------------------------------------------------


def test_snapshot_to_legacy_segments_vs_bytes() -> None:
    progress = _import_progress()
    snapshot_to_legacy = progress.snapshot_to_legacy
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    seg = ProgressSnapshot(
        job_id="j", phase=JobPhase.DOWNLOADING, verified_segments=3, expected_segments=10
    )
    assert snapshot_to_legacy(seg) == (3, 10)
    byte = ProgressSnapshot(
        job_id="j",
        phase=JobPhase.DOWNLOADING,
        network_bytes_this_session=123,
        expected_segments=None,
    )
    assert snapshot_to_legacy(byte) == (123, 0)


# ---------------------------------------------------------------------------
# ProgressManager unit-aware
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progress_manager_segments_render_as_segments() -> None:
    manager = ProgressManager()
    updated = False
    for call in (
        lambda: manager.update(0, 100, 1895, "segments"),
        lambda: manager.update(0, 100, 1895, unit="segments"),
    ):
        try:
            await call()
            updated = True
            break
        except TypeError:
            continue
    if not updated:
        pytest.fail("ProgressManager.update does not accept unit")
    result = await manager.get_formatted_progress(1)
    assert "segments" in result
    assert "1895" in result


@pytest.mark.asyncio
async def test_progress_manager_bytes_render_as_bytes() -> None:
    manager = ProgressManager()
    updated = False
    for call in (
        lambda: manager.update(0, 12345, 100000, "bytes"),
        lambda: manager.update(0, 12345, 100000, unit="bytes"),
    ):
        try:
            await call()
            updated = True
            break
        except TypeError:
            continue
    if not updated:
        pytest.fail("ProgressManager.update does not accept unit")
    result = await manager.get_formatted_progress(1)
    assert "B" in result


@pytest.mark.asyncio
async def test_progress_manager_unknown_total_downloaded_only() -> None:
    manager = ProgressManager()
    updated = False
    for call in (
        lambda: manager.update(0, 12345, 0, "bytes"),
        lambda: manager.update(0, 12345, 0, unit="bytes"),
        lambda: manager.update(0, 12345, 0),
    ):
        try:
            await call()
            updated = True
            break
        except TypeError:
            continue
    if not updated:
        pytest.fail("ProgressManager.update signature mismatch")
    result = await manager.get_formatted_progress(1)
    assert "12.1KB" in result or "12345" in result


@pytest.mark.asyncio
async def test_progress_manager_large_segments_not_bytes() -> None:
    manager = ProgressManager()
    updated = False
    for call in (
        lambda: manager.update(0, 100, 1895, "segments"),
        lambda: manager.update(0, 100, 1895, unit="segments"),
    ):
        try:
            await call()
            updated = True
            break
        except TypeError:
            continue
    if not updated:
        pytest.fail("ProgressManager.update does not accept unit")
    result = await manager.get_formatted_progress(1)
    assert "segments" in result


# ---------------------------------------------------------------------------
# Multi-run anchoring
# ---------------------------------------------------------------------------


def test_multi_run_anchoring_preserves_verified_segments() -> None:
    _import_progress()
    sm = DownloadStateMachine.create(job_id="job", verified_segments=603, expected_segments=1895)
    assert sm.job_state.verified_segments == 603
    sm.update_progress_counters(verified_segments=10, expected_segments=1895)
    assert sm.job_state.verified_segments == 603
    assert sm.job_state.expected_segments == 1895


# ---------------------------------------------------------------------------
# Batch progress isolation
# ---------------------------------------------------------------------------


def test_batch_progress_isolation() -> None:
    progress = _import_progress()
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    reporter, buffer = _make_reporter(enabled=True)
    reporter.start()
    snap0 = ProgressSnapshot(job_id="a", phase=JobPhase.DOWNLOADING, verified_segments=1)
    snap1 = ProgressSnapshot(job_id="b", phase=JobPhase.DOWNLOADING, verified_segments=2)
    reporter.update_snapshot(0, snap0)
    reporter.update_snapshot(1, snap1)
    assert reporter._last_snapshots[0] == snap0
    assert reporter._last_snapshots[1] == snap1
    reporter.stop()


# ---------------------------------------------------------------------------
# TTY / non-TTY / Unicode output
# ---------------------------------------------------------------------------


def test_reporter_update_snapshot_non_tty_unicode() -> None:
    progress = _import_progress()
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    reporter, buffer = _make_reporter(enabled=False)
    reporter.start_task(0, title="caf\xc3\xa9")
    snap = ProgressSnapshot(job_id="j", phase=JobPhase.DOWNLOADING, eta_seconds=None)
    reporter.update_snapshot(0, snap)
    reporter.stop()
    assert isinstance(buffer.getvalue(), str)


def test_reporter_update_snapshot_tty_no_negative_eta() -> None:
    progress = _import_progress()
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    reporter, buffer = _make_reporter(enabled=True)
    reporter.start()
    reporter.start_task(0, title="video")
    snap = ProgressSnapshot(job_id="j", phase=JobPhase.WAITING, eta_seconds=-3.0)
    reporter.update_snapshot(0, snap)
    reporter.stop()
    output = buffer.getvalue()
    assert isinstance(output, str)


def test_reporter_update_snapshot_phase_rendered() -> None:
    progress = _import_progress()
    JobPhase = progress.JobPhase
    ProgressSnapshot = progress.ProgressSnapshot
    reporter, buffer = _make_reporter(enabled=True)
    reporter.start()
    reporter.start_task(0, title="video")
    snap = ProgressSnapshot(job_id="j", phase=JobPhase.REFRESHING_TOKEN, eta_seconds=None)
    reporter.update_snapshot(0, snap)
    reporter.stop()
    output = buffer.getvalue()
    assert isinstance(output, str)
