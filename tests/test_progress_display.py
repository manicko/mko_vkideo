"""Unit tests for vkdownloader.services.progress_display.RichProgressReporter.

Tests render the rich ``Progress`` to an in-memory ``StringIO`` console with
``no_color=True`` so assertions are deterministic and escape-code free. The
headless recipe used throughout is::

    buffer = io.StringIO()
    console = Console(file=buffer, width=120, no_color=True)

No ``force_terminal`` is set for content assertions — a plain ``StringIO`` is
non-terminal, so rich emits a single final frame on ``stop()`` with no ANSI
codes and no ``\\r``, and ``auto_refresh`` is ``False`` (nothing races).
"""

from __future__ import annotations

import io
import logging
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from vkdownloader.models.enums import ProgressStatus
from vkdownloader.services.progress_display import RichProgressReporter


def _make_reporter(enabled: bool) -> tuple[RichProgressReporter, io.StringIO]:
    """Build a reporter wired to an in-memory headless console."""
    buffer = io.StringIO()
    console = Console(file=buffer, width=120, no_color=True)
    return RichProgressReporter(console=console, enabled=enabled), buffer


@pytest.fixture
def preserve_root_handlers() -> Iterator[None]:
    """Snapshot and restore ``logging.getLogger().handlers`` across a test.

    Several reporter tests attach a ``StreamHandler`` to the root logger to
    exercise handler re-pointing; this fixture guarantees no global logging
    state leaks between tests.
    """
    root = logging.getLogger()
    snapshot = list(root.handlers)
    try:
        yield
    finally:
        root.handlers[:] = snapshot


class TestRichProgressReporter:
    """All behavior of RichProgressReporter across enabled and disabled modes."""

    def test_known_total_renders_label_and_percentage(self) -> None:
        """A task with a known total shows its label and a percentage."""
        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.update(0, 50, 100)
        reporter.stop()
        content = buffer.getvalue()
        assert "video_0" in content
        assert "%" in content

    def test_set_title_changes_description_and_bare_label(self) -> None:
        """set_title relabels to 'video_0: {title}'; no title yields bare video_0."""
        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.start_task(0)
        reporter.update(0, 50, 100)
        reporter.stop()
        bare = buffer.getvalue()
        assert "video_0" in bare
        assert "video_0:" not in bare

        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.start_task(0)
        reporter.set_title(0, "Renamed")
        reporter.update(0, 50, 100)
        reporter.stop()
        titled = buffer.getvalue()
        assert "video_0: Renamed" in titled

    def test_finish_task_renders_each_status_marker(self) -> None:
        """finish_task renders the correct marker and outcome word per status."""
        cases = [
            (ProgressStatus.SUCCESS, "\u2713", "done"),
            (ProgressStatus.FAILED, "\u2717", "failed"),
            (ProgressStatus.SKIPPED, "\u2298", "skipped"),
            (ProgressStatus.CANCELLED, "\u2298", "cancelled"),
        ]
        for status, glyph, outcome in cases:
            reporter, buffer = _make_reporter(enabled=True)
            reporter.start()
            reporter.start_task(0)
            reporter.update(0, 50, 100)
            reporter.finish_task(0, status)
            reporter.stop()
            content = buffer.getvalue()
            assert f"[{glyph}]" in content
            assert outcome in content

    def test_two_concurrent_tasks_have_separate_lines(self) -> None:
        """Two active tasks each render on their own line with both labels."""
        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.start_task(0)
        reporter.start_task(1, title="Second")
        reporter.update(0, 50, 100)
        reporter.update(1, 25, 100)
        reporter.stop()
        content = buffer.getvalue()
        lines = [line for line in content.splitlines() if line.strip()]
        assert len(lines) >= 2
        assert "video_0" in content
        assert "video_1: Second" in content

    def test_unknown_total_stays_indeterminate_then_determinate(self) -> None:
        """total=0 keeps the task indeterminate; a later positive total adds a %."""
        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.start_task(0)
        reporter.update(0, 5000, 0)
        task = reporter._progress.tasks[reporter._tasks[0]]
        assert task.total is None
        assert not task.finished
        reporter.stop()
        assert "%" not in buffer.getvalue()

        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.update(0, 5000, 0)
        reporter.update(0, 5000, 10000)
        task = reporter._progress.tasks[reporter._tasks[0]]
        assert task.total == 10000
        reporter.stop()
        assert "%" in buffer.getvalue()

    def test_finish_success_renders_full_bar(self) -> None:
        """finish_task(SUCCESS) with a known total renders a 100% bar."""
        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.start_task(0)
        reporter.update(0, 50, 100)
        reporter.finish_task(0, ProgressStatus.SUCCESS)
        reporter.stop()
        content = buffer.getvalue()
        assert "100%" in content
        assert "\u2713" in content
        assert "done" in content

    def test_disabled_reporter_emits_fallback_logs_no_output(self) -> None:
        """Disabled mode renders nothing and emits progress + finished events."""
        reporter, buffer = _make_reporter(enabled=False)
        captured: list[tuple[str, dict[str, object]]] = []

        def capture(event: str, **fields: object) -> None:
            captured.append((event, fields))

        with patch(
            "vkdownloader.services.progress_display.logger.info",
            side_effect=capture,
        ):
            reporter.start()
            reporter.start_task(0)
            reporter.set_title(0, "ignored in disabled mode")
            reporter.update(0, 100, 200)
            reporter.finish_task(0, ProgressStatus.SUCCESS)
            reporter.stop()

        assert buffer.getvalue() == ""
        events = [event for event, _ in captured]
        assert events.count("download_progress") == 1
        assert events.count("download_finished") == 1
        _, progress_fields = captured[0]
        assert progress_fields["video_index"] == 0
        assert progress_fields["downloaded"] == 100
        assert progress_fields["total"] == 200

    def test_disabled_throttles_progress_logs(self) -> None:
        """Many rapid update() calls emit at most one download_progress event."""
        reporter, buffer = _make_reporter(enabled=False)
        progress_calls: list[str] = []

        def capture(event: str, **fields: object) -> None:
            if event == "download_progress":
                progress_calls.append(event)

        with patch(
            "vkdownloader.services.progress_display.logger.info",
            side_effect=capture,
        ):
            reporter.start()
            for i in range(20):
                reporter.update(0, 100 * i, 1000)
            reporter.finish_task(0, ProgressStatus.SUCCESS)
            reporter.stop()

        assert len(progress_calls) == 1
        assert buffer.getvalue() == ""

    def test_disabled_reporter_carries_title_in_fallback_logs(self) -> None:
        """R8: disabled-path structlog events carry video_label with the title."""
        reporter, _ = _make_reporter(enabled=False)
        captured: list[tuple[str, dict[str, object]]] = []

        def capture(event: str, **fields: object) -> None:
            captured.append((event, fields))

        with patch(
            "vkdownloader.services.progress_display.logger.info",
            side_effect=capture,
        ):
            reporter.start()
            reporter.start_task(0)
            reporter.set_title(0, "Some Title")
            reporter.update(0, 100, 200)
            reporter.finish_task(0, ProgressStatus.SUCCESS)
            reporter.stop()

        events = [event for event, _ in captured]
        assert events.count("download_progress") == 1
        assert events.count("download_finished") == 1

        _, progress_fields = captured[0]
        assert progress_fields["video_label"] == "video_0: Some Title"

        _, finished_fields = captured[1]
        assert finished_fields["video_label"] == "video_0: Some Title"

    def test_is_enabled_derives_from_console(self) -> None:
        """is_enabled mirrors the console terminal flag or the enabled override."""
        non_terminal = RichProgressReporter(
            console=Console(file=io.StringIO(), width=120, no_color=True)
        )
        assert non_terminal.is_enabled is False

        terminal_enabled = RichProgressReporter(
            console=Console(file=io.StringIO(), width=120, no_color=True),
            enabled=True,
        )
        assert terminal_enabled.is_enabled is True

        forced_disabled = RichProgressReporter(
            console=Console(file=io.StringIO(), width=120, no_color=True),
            enabled=False,
        )
        assert forced_disabled.is_enabled is False

        # When no console is supplied, is_enabled falls back to stderr isatty().
        assert RichProgressReporter().is_enabled is False
        with patch("vkdownloader.services.progress_display.sys.stderr") as fake_stderr:
            fake_stderr.isatty.return_value = False
            assert RichProgressReporter().is_enabled is False
            fake_stderr.isatty.return_value = True
            assert RichProgressReporter().is_enabled is True

    def test_start_and_stop_are_idempotent(self) -> None:
        """Double start, double stop, and stop-without-start are all safe."""
        reporter, _ = _make_reporter(enabled=True)
        reporter.start()
        reporter.start()
        reporter.stop()
        reporter.stop()

        reporter, _ = _make_reporter(enabled=True)
        reporter.stop()

    def test_start_task_duplicate_produces_single_line(self) -> None:
        """A second start_task for the same index warns and adds no line."""
        reporter, buffer = _make_reporter(enabled=True)
        with patch("vkdownloader.services.progress_display.logger.warning") as warn:
            reporter.start()
            reporter.start_task(0)
            reporter.start_task(0)
            reporter.update(0, 50, 100)
            reporter.stop()
        assert warn.call_count == 1
        assert buffer.getvalue().count("video_0") == 1

    def test_log_handlers_repointed_and_restored_on_terminal(
        self, tmp_path: Path, preserve_root_handlers: Iterator[None]
    ) -> None:
        """Terminal console repoints StreamHandlers to the FileProxy and restores them."""
        console = Console(file=io.StringIO(), force_terminal=True)
        reporter = RichProgressReporter(console=console)
        assert reporter.is_enabled is True

        sentinel = io.StringIO()
        stream_handler = logging.StreamHandler(sentinel)
        file_handler = logging.FileHandler(str(tmp_path / "audit.log"))
        root = logging.getLogger()
        root.addHandler(stream_handler)
        root.addHandler(file_handler)
        original_file_stream = file_handler.stream
        assert stream_handler.stream is sentinel
        try:
            reporter.start()
            # StreamHandler repointed onto the FileProxy-wrapped stderr.
            assert stream_handler.stream is not sentinel
            # FileHandler must be left untouched (only StreamHandlers qualify).
            assert file_handler.stream is original_file_stream
        finally:
            # stop() in finally so a failing assertion above cannot leak the
            # FileProxy as sys.stderr into later tests.
            reporter.stop()
            # After stop(), handlers must be repointed back to their original
            # streams. These run before removeHandler/close() because close()
            # nulls FileHandler.stream, which would fail the identity check.
            assert stream_handler.stream is sentinel
            assert file_handler.stream is original_file_stream
            root.removeHandler(stream_handler)
            root.removeHandler(file_handler)
            file_handler.close()

    def test_log_messages_render_above_live_display_and_resume(
        self, preserve_root_handlers: Iterator[None]
    ) -> None:
        """AC4/R6: a log record reaches the buffer above the live display, which then resumes.

        ``force_terminal=True`` is required: rich only installs the ``sys.stderr``
        FileProxy (and therefore only repoints the root StreamHandler) when the
        console reports itself as a terminal. Without it the handler stays bound
        to the sentinel stream and the record never enters the buffer.
        """
        buffer = io.StringIO()
        console = Console(file=buffer, force_terminal=True)
        reporter = RichProgressReporter(console=console)
        assert reporter.is_enabled is True

        sentinel = io.StringIO()
        stream_handler = logging.StreamHandler(sentinel)
        root = logging.getLogger()
        root.addHandler(stream_handler)
        try:
            reporter.start()
            reporter.start_task(0)
            reporter.update(0, 50, 100)

            # Emit a real record through the repointed handler, bypassing the
            # logger's own level check so the message is guaranteed to emit.
            record = logging.LogRecord(
                name="ac4_probe",
                level=logging.WARNING,
                pathname=__file__,
                lineno=1,
                msg="rate limit warning fired",
                args=None,
                exc_info=None,
            )
            stream_handler.handle(record)

            reporter.update(0, 100, 100)
        finally:
            # stop() in finally so the FileProxy-backed sys.stderr is always
            # restored even if an assertion below fails.
            reporter.stop()
            root.removeHandler(stream_handler)

        content = buffer.getvalue()
        # The distinctive message was not swallowed by the FileProxy/Live
        # mediation; it reached the live console and was written to the buffer.
        assert "rate limit warning fired" in content
        # The progress display kept rendering: a progress frame is present too.
        assert "video_0" in content
        # Ordering: the log message precedes the final (completed/100%) frame,
        # proving Live paused for the message and resumed afterwards.
        assert content.index("rate limit warning fired") < content.rindex("100%")

    def test_update_lazily_creates_task(self) -> None:
        """update() without a prior start_task still creates and labels the line."""
        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.update(0, 50, 100)
        assert 0 in reporter._tasks
        reporter.stop()
        content = buffer.getvalue()
        assert "video_0" in content
        assert "%" in content

    def test_long_title_is_truncated(self) -> None:
        """Titles longer than the cap are truncated with an ellipsis."""
        reporter, buffer = _make_reporter(enabled=True)
        long_title = "A" * 80
        reporter.start()
        reporter.start_task(0, title=long_title)
        reporter.stop()
        content = buffer.getvalue()
        assert "video_0:" in content
        assert "\u2026" in content
        assert long_title not in content

    def test_finish_task_without_task_logs_debug(self) -> None:
        """finish_task on an unknown index logs at debug instead of crashing."""
        reporter, _ = _make_reporter(enabled=True)
        with patch("vkdownloader.services.progress_display.logger.debug") as debug:
            reporter.start()
            reporter.finish_task(0, ProgressStatus.SUCCESS)
        assert debug.call_count == 1

    def test_set_title_without_task_records_label_no_render(self) -> None:
        """set_title without a task records the title (R8) but does not render."""
        reporter, buffer = _make_reporter(enabled=True)
        reporter.start()
        reporter.set_title(0, "Ghost")
        # R8: the title is recorded unconditionally for label formatting even
        # without a rich task; no rendering occurs since no task exists to update.
        assert 0 in reporter._titles
        assert reporter._titles[0] == "Ghost"
        assert buffer.getvalue() == ""
        reporter.stop()

    def test_start_builds_console_lazily_on_stderr(self) -> None:
        """start() builds Console(stderr=True) and renders when no console given."""
        stderr_buffer = io.StringIO()
        with patch("vkdownloader.services.progress_display.sys.stderr", stderr_buffer):
            reporter = RichProgressReporter(enabled=True)
            reporter.start()
            reporter.start_task(0, title="Lazy Build")
            reporter.update(0, 50, 100)
            reporter.finish_task(0, ProgressStatus.SUCCESS)
            reporter.stop()
        content = stderr_buffer.getvalue()
        assert "video_0: Lazy Build" in content
        assert "100%" in content

    def test_methods_are_noops_before_start_in_enabled_mode(self) -> None:
        """Public methods are safe (no-ops) when called before start() in enabled mode."""
        reporter, buffer = _make_reporter(enabled=True)
        with patch("vkdownloader.services.progress_display.logger.debug"):
            reporter.start_task(0)
            reporter.set_title(0, "Early")
            reporter.update(0, 50, 100)
            reporter.finish_task(0, ProgressStatus.SUCCESS)
        assert buffer.getvalue() == ""
        assert reporter._tasks == {}
