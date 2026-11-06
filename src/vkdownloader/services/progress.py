"""Trustworthy progress snapshots, rate tracking and ETA helpers (Block I).

This module defines the frozen :class:`ProgressSnapshot` value object, the
:class:`JobPhase` enum (re-exported from :mod:`vkdownloader.models.enums`),
a sliding-window :class:`ProgressTracker` for transfer rate and ETA, and the
adapter helpers that keep the legacy ``(downloaded, total)`` callback API
working while callers migrate.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..models.enums import JobPhase

if TYPE_CHECKING:
    pass

__all__ = [
    "JobPhase",
    "ProgressSnapshot",
    "ProgressTracker",
    "snapshot_to_legacy",
    "eta_from_snapshot",
    "parse_ytdlp_eta",
]


@dataclass(frozen=True)
class ProgressSnapshot:
    """Immutable, job-wide progress snapshot.

    Fields are safe-defaulted so a partially populated snapshot is still
    valid. ``verified_*`` counters are anchored to checkpoint/state-machine
    state and never roll back on a child restart.
    """

    job_id: str
    phase: JobPhase
    verified_segments: int = 0
    expected_segments: int | None = None
    verified_bytes_on_disk: int = 0
    network_bytes_this_session: int = 0
    transfer_rate_bytes_per_sec: float | None = None
    eta_seconds: float | None = None
    is_estimate: bool = False
    attempt_id: int = 0
    child_fragment_index: int = 0
    child_fragment_count: int = 0
    measured_at: float | None = None

    def __post_init__(self) -> None:
        if self.verified_segments < 0:
            raise ValueError("verified_segments must be non-negative")
        if self.expected_segments is not None and self.expected_segments < 0:
            raise ValueError("expected_segments must be non-negative or None")
        if self.verified_bytes_on_disk < 0:
            raise ValueError("verified_bytes_on_disk must be non-negative")
        if self.network_bytes_this_session < 0:
            raise ValueError("network_bytes_this_session must be non-negative")
        if self.child_fragment_index < 0:
            raise ValueError("child_fragment_index must be non-negative")
        if self.child_fragment_count < 0:
            raise ValueError("child_fragment_count must be non-negative")
        if self.attempt_id < 0:
            raise ValueError("attempt_id must be non-negative")
        if self.transfer_rate_bytes_per_sec is not None:
            rate = self.transfer_rate_bytes_per_sec
            if rate < 0:
                raise ValueError("transfer_rate_bytes_per_sec must be non-negative")


def parse_ytdlp_eta(text: str) -> float | None:
    """Parse a yt-dlp ETA token into seconds.

    Accepts ``MM:SS`` and ``HH:MM:SS``. Returns ``None`` for dashes,
    ``Unknown``, empty, unparseable or negative values.
    """
    if text is None:
        return None
    token = str(text).strip()
    if not token or token.lower() in {"unknown", "n/a", "--:--:--"}:
        return None
    if token.startswith("-"):
        return None
    # Handle colon-separated durations.
    if ":" in token:
        parts = token.split(":")
        try:
            values = [int(p) for p in parts]
        except ValueError:
            return None
        if len(values) == 2:
            minutes, seconds = values
            hours = 0
        elif len(values) == 3:
            hours, minutes, seconds = values
        else:
            return None
        if minutes < 0 or seconds < 0 or hours < 0:
            return None
        if seconds >= 60 or minutes >= 60:
            # yt-dlp may emit minutes >= 60 in HH:MM:SS? reject malformed
            if len(values) == 2 and minutes >= 60:
                pass
        total = hours * 3600 + minutes * 60 + seconds
        if total < 0:
            return None
        return float(total)
    # Plain seconds?
    try:
        value = float(token)
    except ValueError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


class ProgressTracker:
    """Sliding-window tracker for transfer rate and ETA.

    Samples are pruned to ``window_seconds`` (clamped to 30..90s). Rate and
    ETA are ``None`` until enough samples exist; values are never negative or
    non-finite.
    """

    def __init__(self, *, window_seconds: float = 60.0, min_samples: int = 2) -> None:
        self._window_seconds = min(max(float(window_seconds), 30.0), 90.0)
        self._min_samples = max(1, int(min_samples))
        self._samples: list[tuple[float, int, int]] = []

    def observe(
        self,
        *,
        verified_segments: int,
        network_bytes_this_session: int,
        measured_at: float | None = None,
    ) -> None:
        if measured_at is None:
            measured_at = time.monotonic()
        try:
            vs = int(verified_segments)
        except TypeError, ValueError:
            vs = 0
        try:
            nb = int(network_bytes_this_session)
        except TypeError, ValueError:
            nb = 0
        if vs < 0:
            vs = 0
        if nb < 0:
            nb = 0
        self._samples.append((float(measured_at), nb, vs))
        self._prune()

    def _prune(self) -> None:
        if not self._samples:
            return
        latest = self._samples[-1][0]
        cutoff = latest - self._window_seconds
        self._samples = [s for s in self._samples if s[0] >= cutoff]

    @property
    def transfer_rate_bytes_per_sec(self) -> float | None:
        self._prune()
        if len(self._samples) < self._min_samples:
            return None
        first = self._samples[0]
        last = self._samples[-1]
        dt = last[0] - first[0]
        if dt <= 0:
            return None
        db = last[1] - first[1]
        if db < 0:
            db = 0
        rate = db / dt
        if not math.isfinite(rate) or rate < 0:
            return None
        return float(rate)

    def eta_seconds(
        self,
        *,
        remaining_segments: int | None = None,
        remaining_bytes: int | None = None,
        avg_segment_bytes: float | None = None,
    ) -> float | None:
        # Zero remaining => complete.
        if remaining_bytes == 0:
            return 0.0
        if remaining_segments == 0:
            return 0.0
        if remaining_segments is not None and remaining_segments < 0:
            return None
        if remaining_bytes is not None and remaining_bytes < 0:
            return None

        rate = self.transfer_rate_bytes_per_sec
        if rate is None or rate <= 0:
            return None

        rem_bytes: float | None = None
        if remaining_bytes is not None:
            rem_bytes = float(remaining_bytes)
        elif remaining_segments is not None:
            if remaining_segments is None or remaining_segments <= 0:
                return 0.0 if remaining_segments == 0 else None
            avg = avg_segment_bytes
            if avg is None and len(self._samples) >= 2:
                first = self._samples[0]
                last = self._samples[-1]
                dseg = last[2] - first[2]
                dbytes = last[1] - first[1]
                if dseg > 0:
                    avg = dbytes / dseg
            if avg is None or avg <= 0:
                return None
            rem_bytes = float(remaining_segments) * float(avg)

        if rem_bytes is None:
            return None
        if rem_bytes < 0:
            return None
        if rem_bytes == 0:
            return 0.0
        eta = rem_bytes / rate
        if not math.isfinite(eta) or eta < 0:
            return None
        return float(eta)

    def reset(self) -> None:
        self._samples.clear()


def snapshot_to_legacy(snapshot: ProgressSnapshot) -> tuple[int, int]:
    """Convert a :class:`ProgressSnapshot` to the legacy ``(downloaded, total)`` tuple.

    Segments are reported when segment counters are available; otherwise byte
    counts are used. Unknown totals become ``0``.
    """
    # Segment-based progress when fragment/expected segment counts exist.
    if getattr(snapshot, "child_fragment_count", 0) and snapshot.child_fragment_count > 0:
        return (int(snapshot.child_fragment_index), int(snapshot.child_fragment_count))
    if snapshot.expected_segments is not None:
        return (int(snapshot.verified_segments), int(snapshot.expected_segments))
    # Byte-based progress.
    return (int(snapshot.network_bytes_this_session), 0)


def eta_from_snapshot(snapshot: ProgressSnapshot) -> float | None:
    """Validate a snapshot's ETA, returning ``None`` for invalid values."""
    val = snapshot.eta_seconds
    if val is None:
        return None
    try:
        f = float(val)
    except TypeError, ValueError:
        return None
    if not math.isfinite(f) or f < 0:
        return None
    return f
