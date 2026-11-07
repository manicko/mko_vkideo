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


def test_child_started_event_listed() -> None:
    from vkdownloader.services.diagnostics import (
        STRUCTURED_DIAGNOSTIC_EVENTS,
        STRUCTURED_DIAGNOSTIC_FIELDS,
    )

    assert "child_started" in STRUCTURED_DIAGNOSTIC_EVENTS
    for f in ("pid", "launch_number", "phase", "next_action", "artifact_snapshot"):
        assert f in STRUCTURED_DIAGNOSTIC_FIELDS


def test_diagnostic_context_has_new_fields() -> None:
    from vkdownloader.services.diagnostics import DiagnosticContext

    ctx = DiagnosticContext(pid=1, launch_number=2, phase="x", next_action="y", artifact_snapshot={"a": 1})
    d = ctx.to_dict()
    assert d["pid"] == 1
    assert d["artifact_snapshot"] == {"a": 1}


def test_artifact_snapshot_helper_shape() -> None:
    import tempfile
    from pathlib import Path

    from vkdownloader.services.ytdlp_downloader import (
        YtdlpArtifacts,
        _capture_ytdlp_artifact_snapshot,
    )

    d = Path(tempfile.mkdtemp())
    art = YtdlpArtifacts(directory=d, final_name="video.mp4")
    (d / "video.mp4.part").write_bytes(b"abc")
    snap = _capture_ytdlp_artifact_snapshot(art)
    assert snap is not None
    assert "video.mp4.part" in snap
    assert snap["video.mp4.part"] == 3


def test_artifact_snapshot_returns_none_on_oserror(monkeypatch) -> None:
    import tempfile
    from pathlib import Path

    from vkdownloader.services.ytdlp_downloader import (
        YtdlpArtifacts,
        _capture_ytdlp_artifact_snapshot,
    )

    d = Path(tempfile.mkdtemp())
    art = YtdlpArtifacts(directory=d, final_name="video.mp4")

    def boom(self):
        raise OSError("boom")

    monkeypatch.setattr(Path, "exists", boom)
    snap = _capture_ytdlp_artifact_snapshot(art)
    assert snap is None
