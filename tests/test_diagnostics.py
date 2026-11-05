"""RED tests for Block C diagnostics (ChildTranscriptSink)."""

from __future__ import annotations

from pathlib import Path

import pytest


def _import_sink():
    try:
        from vkdownloader.services.diagnostics import ChildTranscriptSink
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"ChildTranscriptSink not available: {exc}")
    return ChildTranscriptSink


def test_child_transcript_sink_exists_import() -> None:
    ChildTranscriptSink = _import_sink()
    assert ChildTranscriptSink is not None


def test_child_transcript_sink_constants_exist() -> None:
    try:
        from vkdownloader.services.diagnostics import (
            STRUCTURED_DIAGNOSTIC_EVENTS,
            STRUCTURED_DIAGNOSTIC_FIELDS,
        )
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"diagnostic constants not available: {exc}")
    assert len(STRUCTURED_DIAGNOSTIC_EVENTS) > 0
    assert len(STRUCTURED_DIAGNOSTIC_FIELDS) > 0


def test_progress_lines_bounded_memory_and_size(tmp_path: Path) -> None:
    ChildTranscriptSink = _import_sink()
    sink_path = tmp_path / "transcript.jsonl"
    sink = ChildTranscriptSink(sink_path)
    for i in range(10_000):
        sink.write_line(f"progress {i} 50%", is_progress=True)
    sink.close()

    assert sink_path.exists()
    assert sink_path.stat().st_size < 1024 * 1024


def test_secrets_canary_not_in_sink(tmp_path: Path) -> None:
    ChildTranscriptSink = _import_sink()
    sink_path = tmp_path / "transcript.jsonl"
    sink = ChildTranscriptSink(sink_path)
    secret = "SECRET_TOKEN_123"
    sink.write_line(f"downloading https://host/x?token={secret}")
    sink.write_line("Cookie: session=abc")
    sink.close()

    content = sink_path.read_text(encoding="utf-8")
    assert secret not in content
    assert "session=abc" not in content
