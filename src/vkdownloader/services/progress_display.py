"""Multi-line rich progress reporter for concurrent batch downloads.

Renders one self-overwriting progress line per active download on a rich
``Live`` display when the output stream is a terminal. When the stream is not
a terminal (piped / CI / ``CliRunner``) the reporter falls back to throttled
structlog INFO events so no escape codes ever reach the output.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import IO

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    Task,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text
from structlog import get_logger

from ..config import encoding_safe
from ..models.enums import ProgressStatus

logger = get_logger(__name__)

__all__ = ["RichProgressReporter"]

# Fallback path: cap progress logs at 1/s per index. A 4-way concurrent batch
# fires up to ~16 update callbacks/second (4 per process); without throttling
# the structured log would be flooded with download_progress events.
_PROGRESS_LOG_INTERVAL_SECONDS: float = 1.0

# Long titles are truncated to keep each progress line readable on an 80-col
# terminal.
_MAX_TITLE_LENGTH: int = 60


class _StatusColumn(ProgressColumn):
    """Render a terminal status marker for a download task.

    Renders nothing while a task is in progress and a styled glyph once the task
    reaches a terminal status, which is carried in ``task.fields["status"]``.
    """

    def render(self, task: Task) -> Text:
        raw = task.fields.get("status")
        if raw is None:
            return Text("")
        # task.fields is dict[str, Any] upstream; coerce and validate so Any
        # never escapes into our own signatures or logic.
        try:
            status = ProgressStatus(str(raw))
        except ValueError:
            return Text("")
        match status:
            case ProgressStatus.SUCCESS:
                return Text("[✓]", style="green")
            case ProgressStatus.FAILED:
                return Text("[✗]", style="red")
            case ProgressStatus.SKIPPED:
                return Text("[⊘]", style="yellow")
            case ProgressStatus.CANCELLED:
                return Text("[⊘]", style="cyan")
            case ProgressStatus.IN_PROGRESS:
                return Text("")


def _format_outcome(status: ProgressStatus) -> str:
    """Map a terminal progress status to the word shown after the label.

    Uses a ``match`` (StrEnum members are a fixed value set) rather than a dict
    per project rule #10.
    """
    match status:
        case ProgressStatus.SUCCESS:
            return "done"
        case ProgressStatus.FAILED:
            return "failed"
        case ProgressStatus.SKIPPED:
            return "skipped"
        case ProgressStatus.CANCELLED:
            return "cancelled"
        case ProgressStatus.IN_PROGRESS:
            return "in_progress"


class RichProgressReporter:
    """Rich-based per-file progress display for concurrent batch downloads.

    Call :meth:`start` to open the live display, drive it with
    :meth:`start_task` / :meth:`update` / :meth:`finish_task`, then :meth:`stop`
    to tear it down. When the target console is not a terminal the reporter
    disables itself and emits throttled structlog INFO events instead, keeping
    piped/CI output free of escape codes.
    """

    def __init__(
        self,
        *,
        console: Console | None = None,
        enabled: bool | None = None,
        refresh_per_second: float = 10.0,
    ) -> None:
        self._console: Console | None = console
        self._enabled: bool | None = enabled
        self._refresh_per_second: float = refresh_per_second
        self._started: bool = False
        self._progress: Progress | None = None
        self._tasks: dict[int, TaskID] = {}
        self._titles: dict[int, str] = {}
        self._last_values: dict[int, tuple[int, int]] = {}
        self._last_log_time: dict[int, float] = {}
        self._saved_handler_streams: list[
            tuple[logging.StreamHandler[IO[str]], IO[str] | None]
        ] = []

    @property
    def is_enabled(self) -> bool:
        """Whether the rich live display is active for this reporter."""
        if self._enabled is not None:
            return self._enabled
        if self._console is not None:
            return self._console.is_terminal
        # No console provided yet: mirror Console(stderr=True).is_terminal
        # without constructing one (stderr is a TTY in production, BytesIO
        # under CliRunner). The real Console is still built lazily in start().
        return sys.stderr.isatty()

    def start(self) -> None:
        """Open the live display.

        Idempotent: a second call with no :meth:`stop` in between is a no-op.
        When disabled, this is a cheap no-op and all progress falls back to
        throttled structlog INFO events.
        """
        if self._started:
            return
        self._started = True
        if not self.is_enabled:
            return
        # Resolve the console lazily — never at import or construction time, so
        # the reporter binds to the stream that is live when display starts.
        if self._console is None:
            self._console = Console(stderr=True)
        progress = self._build_progress()
        progress.start()
        # Progress.start() swaps sys.stderr for rich's FileProxy when the console
        # is a terminal (redirect_stderr=True). Re-point StreamHandlers onto the
        # wrapped stderr so log writes are mediated by the Live display.
        if self._console.is_terminal:
            self._repoint_log_handlers()
        self._progress = progress

    def stop(self) -> None:
        """Close the live display and restore captured state.

        Safe to call without :meth:`start` and idempotent.

        Post-conditions, guaranteed even when a teardown step raises:
          - every in-flight task is terminalised as ``CANCELLED`` so the
            final frame is never left mid-work;
          - the live ``Progress`` is stopped and log handlers are restored;
          - every owned map (``_tasks``, ``_titles``, ``_last_values``,
            ``_last_log_time``) is cleared.

        Two nested ``finally`` blocks express two independent guarantees:
        ``progress.stop()`` and ``_restore_log_handlers()`` each release a
        *different* external resource (the Live ``FileProxy`` on ``sys.stderr``
        vs. handler stream redirections), so a failure in one must not skip
        the other. The four map clears are object-owned state and must
        always reset, so they sit in the outermost ``finally``. The first
        failure propagates; nothing is swallowed.
        """
        if not self._started:
            return
        self._started = False
        progress = self._progress
        self._progress = None

        try:
            # B12: terminalise in-flight tasks *before* the display closes so
            # the last frame carries a truthful marker, not an open bar.
            self._terminalise_tasks(progress)
            if progress is not None:
                # B11: progress.stop() releases the Live/FileProxy on sys.stderr.
                progress.stop()
        finally:
            try:
                self._restore_log_handlers()
            finally:
                self._tasks.clear()
                self._titles.clear()
                self._last_values.clear()
                self._last_log_time.clear()

    def _terminalise_tasks(self, progress: Progress | None) -> None:
        """Mark every in-flight task as ``CANCELLED`` before teardown.

        Tasks whose status is already terminal (set via :meth:`finish_task`)
        are left untouched — ``stop()`` never overwrites a real outcome. Only
        tasks that began work but never finished receive a terminal state, and
        ``CANCELLED`` is the only truthful one: the batch is over, not successful.
        """
        if progress is None:
            return
        for index, task_id in self._tasks.items():
            task = progress.tasks[task_id]
            if task.fields.get("status") is not None:
                continue
            outcome = _format_outcome(ProgressStatus.CANCELLED)
            label = self._format_label(index)
            progress.update(
                task_id,
                description=f"{label} {outcome}",
                status=ProgressStatus.CANCELLED.value,
            )

    def start_task(self, index: int, title: str | None = None) -> None:
        """Register a new download line for ``index``.

        The title is recorded unconditionally; the rich description is only
        updated when the display is enabled (R8).
        """
        # R8: record the title even when disabled so the non-TTY structlog
        # fallback events carry a useful video_label (video_{N}: {title}).
        if title is not None:
            self._titles[index] = title
        if not self.is_enabled:
            return
        if self._progress is None:
            return
        if index in self._tasks:
            logger.warning(
                "progress_task_already_exists",
                video_index=index,
            )
            return
        self._add_task(index)

    def set_title(self, index: int, title: str) -> None:
        """Rewrite the description of an existing task.

        The title is recorded unconditionally; the rich description is only
        updated when the display is enabled (R8).
        """
        # R8: record the title even when disabled so the non-TTY structlog
        # fallback events carry a useful video_label (video_{N}: {title}).
        self._titles[index] = title
        if not self.is_enabled:
            return
        if self._progress is None:
            return
        if index not in self._tasks:
            return
        self._progress.update(self._tasks[index], description=self._format_label(index))

    def update(self, index: int, downloaded: int, total: int) -> None:
        """Advance the progress line for ``index``.

        ``total <= 0`` means the size is unknown (the ffmpeg path); in that case
        the task stays indeterminate. ``total`` is only forwarded to rich when
        strictly positive, because rich treats ``total=0`` as an immediately
        finished task and breaks ``BarColumn``.
        """
        self._last_values[index] = (downloaded, total)
        if not self.is_enabled:
            self._log_progress(index, downloaded, total)
            return
        if self._progress is None:
            return
        task_id = self._tasks.get(index)
        if task_id is None:
            task_id = self._add_task(index)
        if total > 0:
            self._progress.update(task_id, total=total, completed=downloaded)
        else:
            # Never forward a non-positive total: rich.update ignores
            # total=None but total=0 marks the task finished immediately.
            self._progress.update(task_id, completed=downloaded)

    def finish_task(self, index: int, status: ProgressStatus) -> None:
        """Mark ``index`` as terminal and render its outcome marker."""
        label = self._format_label(index)
        if not self.is_enabled:
            self._log_finished(index, status, label)
            return
        task_id = self._tasks.get(index)
        if task_id is None:
            logger.debug(
                "finish_task_no_task",
                video_index=index,
                status=status.value,
            )
            return
        if self._progress is None:
            return
        outcome = _format_outcome(status)
        downloaded, total = self._last_values.get(index, (0, 0))
        if status == ProgressStatus.SUCCESS and total > 0:
            # The source-reported final byte count is not authoritative for a
            # completed download; show a full bar instead of a stuck 98%.
            self._progress.update(
                task_id,
                description=f"{label} {outcome}",
                completed=total,
                status=status.value,
            )
        else:
            # Leave completed/total untouched so the bar shows how far it got.
            self._progress.update(
                task_id,
                description=f"{label} {outcome}",
                status=status.value,
            )

    def _add_task(self, index: int) -> TaskID:
        """Create a rich task for ``index`` and remember its id."""
        progress = self._progress
        assert progress is not None, "start() must be called before adding tasks"
        task_id = progress.add_task(description=self._format_label(index), total=None)
        self._tasks[index] = task_id
        return task_id

    def _format_label(self, index: int) -> str:
        """Build the description shown by ``TextColumn`` for ``index``."""
        base = f"video_{index}"
        title = self._titles.get(index)
        if title is None:
            return base
        if len(title) <= _MAX_TITLE_LENGTH:
            return f"{base}: {title}"
        return f"{base}: {title[: _MAX_TITLE_LENGTH - 1]}…"

    def _build_progress(self) -> Progress:
        """Construct the configured ``Progress`` with positional columns."""
        console = self._console
        assert console is not None, "start() must be called before building progress"
        columns = (
            _StatusColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            # TaskProgressColumn renders the percentage (e.g. "50%") and is
            # empty when the total is unknown. DownloadColumn renders byte
            # counts ("50/100 bytes"), not a percentage, so it cannot stand in
            # for the percentage column required by R9/AC8.
            TaskProgressColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        )
        # All progress callbacks fire on the asyncio event loop thread (see
        # ytdlp_downloader._monitor_progress:649, downloader._monitor_progress:330,
        # and segment_downloader._download_segment_concurrent:711), so the per-task
        # dicts below are never touched concurrently and need no lock.
        return Progress(
            *columns,
            console=console,
            auto_refresh=console.is_terminal,
            refresh_per_second=self._refresh_per_second,
            transient=False,
            redirect_stdout=False,
            redirect_stderr=True,
        )

    def _repoint_log_handlers(self) -> None:
        """Move ``StreamHandler`` streams onto the FileProxy-wrapped stderr.

        WHY: ``logging.StreamHandler`` captures its stream at construction time,
        and ``setup_logging`` runs before the display starts. Once
        ``Progress.start()`` swaps ``sys.stderr`` for rich's ``FileProxy``, a
        handler still bound to the original stream writes straight past the Live
        display. ``setStream`` redirects it onto the wrapped stderr so log output
        is mediated by the Live display (pause, print above, resume) per R6.

        The repointed stream is passed through ``config.encoding_safe`` so the
        handler inherits the same ``backslashreplace`` encoding-safety policy
        that ``setup_logging`` installed on the standalone console sink (B16).
        Without this, the batch path — which is exactly when BRW-001's browser
        launch failure (carrying box-drawing characters) is logged — would
        discard B16's stream and raise ``UnicodeEncodeError`` inside
        ``StreamHandler.emit`` instead of escaping the unencodable characters.

        NOTE: This repoints only handlers on the *root* logger
        (``logging.getLogger().handlers``). ``config.setup_logging()`` installs
        its console ``StreamHandler`` there via ``logging.basicConfig`` (with the
        default root logger), so repointing works today. If that handler ever
        moves to a named logger, this method would silently stop intercepting
        console log output and log lines would write past the Live display again.
        """
        current_stderr = sys.stderr
        root = logging.getLogger()
        for handler in root.handlers:
            if not isinstance(handler, logging.StreamHandler):
                continue
            if isinstance(handler, logging.FileHandler):
                continue
            old_stream = handler.setStream(encoding_safe(current_stderr))
            self._saved_handler_streams.append((handler, old_stream))

    def _restore_log_handlers(self) -> None:
        """Restore each ``StreamHandler`` to its original stream.

        WHY: the inverse of :meth:`_repoint_log_handlers`. ``Progress.stop()``
        restores ``sys.stderr`` to the real stream; this puts every handler back
        on its pre-start stream so the post-stop log format is byte-identical
        to before the display started (per R6).
        """
        for handler, old_stream in self._saved_handler_streams:
            if old_stream is not None:
                handler.setStream(old_stream)
        self._saved_handler_streams.clear()

    def _log_progress(self, index: int, downloaded: int, total: int) -> None:
        """Emit a throttled ``download_progress`` INFO event (disabled path)."""
        now = time.monotonic()
        last = self._last_log_time.get(index, 0.0)
        if now - last < _PROGRESS_LOG_INTERVAL_SECONDS:
            return
        self._last_log_time[index] = now
        logger.info(
            "download_progress",
            video_index=index,
            video_label=self._format_label(index),
            downloaded=downloaded,
            total=total,
        )

    def _log_finished(self, index: int, status: ProgressStatus, label: str) -> None:
        """Emit a single ``download_finished`` INFO event (disabled path)."""
        downloaded, total = self._last_values.get(index, (0, 0))
        logger.info(
            "download_finished",
            video_index=index,
            video_label=label,
            status=status.value,
            downloaded=downloaded,
            total=total,
        )
