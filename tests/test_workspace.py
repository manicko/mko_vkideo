"""RED tests for Block D — output/tmp workspace and safe yt-dlp artifact routing.

These tests target the (not-yet-implemented) workspace module and the
Block D API changes. They are expected to FAIL until the implementation
lands. Collection must remain successful: all imports of not-yet-existing
modules are guarded inside test bodies / helpers.
"""

from __future__ import annotations

import inspect
import threading
from pathlib import Path

import pytest

from vkdownloader.exceptions import DownloadError


def _import_workspace():
    try:
        from vkdownloader.services import workspace as ws

        return ws
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"workspace module unavailable: {exc}")


def _import_ytdlp():
    try:
        from vkdownloader.services import ytdlp_downloader as m

        return m
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"ytdlp_downloader module unavailable: {exc}")


def _import_segment():
    try:
        from vkdownloader.services import segment_downloader as m

        return m
    except Exception as exc:  # pragma: no cover - RED path
        pytest.fail(f"segment_downloader module unavailable: {exc}")


def _import_security():
    from vkdownloader.utils import security as s

    return s


def test_make_workspace_layout(tmp_path: Path) -> None:
    ws = _import_workspace()
    final_path = tmp_path / "out" / "video.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)

    make = ws.make_workspace
    stable = ws.stable_job_id
    expected_job = stable("vid123", "best", final_path.name)

    workspace = make(final_path, "vid123", "best")

    assert workspace.final_path == final_path.resolve()
    assert workspace.root == final_path.parent / "tmp" / "jobs" / expected_job
    for d in (
        workspace.root,
        workspace.ytdlp_dir,
        workspace.segments_dir,
        workspace.staging_dir,
        workspace.diagnostics_dir,
    ):
        assert d.exists() and d.is_dir(), f"missing dir: {d}"
    assert workspace.log_path.parent.exists()
    assert workspace.state_path.parent == workspace.root
    assert workspace.job_state_path != workspace.segment_checkpoint_path
    assert workspace.job_state_path.name == "job_state.v2.json"
    assert workspace.segment_checkpoint_path.name == "segment_checkpoint.v2.json"
    assert workspace.job_state_path.parent == workspace.root
    assert workspace.segment_checkpoint_path.parent == workspace.root
    assert workspace.lock_path.parent == (final_path.parent / "tmp" / "locks")
    assert workspace.lock_path.parent.exists()
    assert (final_path.parent / "tmp").exists()
    assert (final_path.parent / "tmp" / "logs").exists()


def test_stable_job_id_stable_and_bounded() -> None:
    ws = _import_workspace()
    sid = ws.stable_job_id
    a = sid("video42", "1080", "Movie.mp4")
    b = sid("video42", "1080", "Movie.mp4")
    assert a == b
    c = sid("video42", "720", "Movie.mp4")
    assert a != c
    assert len(a) <= 120
    long_id = "x" * 200
    job = sid(long_id, "best", "out.mp4")
    assert len(job) <= 120
    import re

    assert re.search(r"[0-9a-f]{12}", job)


def test_workspace_rejects_traversal_and_symlink(tmp_path: Path) -> None:
    ws = _import_workspace()

    bad = tmp_path / "out" / ".." / ".." / "etc" / "x.mp4"
    with pytest.raises(DownloadError):
        ws.make_workspace(bad, "v", "best")

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("symlink not supported on this platform")
    escaped_final = link / "evil.mp4"
    with pytest.raises(DownloadError):
        ws.make_workspace(escaped_final, "v", "best")


def test_ytdlp_routing_interrupted(tmp_path: Path) -> None:
    ws_mod = _import_workspace()
    ytdlp = _import_ytdlp()

    final_path = tmp_path / "out" / "video.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    workspace = ws_mod.make_workspace(final_path, "vid1", "best")

    build = ytdlp._build_ytdlp_cli_command
    sig = inspect.signature(build)
    assert "workspace" in sig.parameters

    from vkdownloader.config import Settings

    cmd, cookie_file = build(
        final_path,
        "best",
        "Mozilla/5.0",
        Settings(),
        None,
        None,
        workspace=workspace,
    )

    assert "-P" in cmd
    joined = " ".join(str(c) for c in cmd)
    assert f"home:{workspace.staging_dir}" in joined
    assert f"temp:{workspace.ytdlp_dir}" in joined
    o_idx = cmd.index("-o")
    assert cmd[o_idx + 1] == workspace.final_path.name

    assert hasattr(ytdlp, "YtdlpArtifacts")
    Art = ytdlp.YtdlpArtifacts
    art = Art(directory=workspace.ytdlp_dir, final_name=final_path.name)
    assert art.temp_path == workspace.ytdlp_dir / (final_path.name + ".part")
    assert art.ytdl_path == workspace.ytdlp_dir / (final_path.name + ".ytdl")
    (workspace.ytdlp_dir / (final_path.name + ".part-Frag3.part")).write_bytes(b"x")
    frags = art.fragment_paths()
    assert any("part-Frag" in p.name for p in frags)
    assert art.has_artifacts() is True


def test_interruption_retry_reuses_workspace(tmp_path: Path) -> None:
    ws = _import_workspace()
    final_path = tmp_path / "out" / "video.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    w1 = ws.make_workspace(final_path, "vid1", "best")
    w2 = ws.make_workspace(final_path, "vid1", "best")
    assert w1.root == w2.root
    assert w1.ytdlp_dir == w2.ytdlp_dir


def test_other_jobs_intact(tmp_path: Path) -> None:
    ws = _import_workspace()
    final_path = tmp_path / "out" / "video.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    w_a = ws.make_workspace(final_path, "vida", "best")
    marker = w_a.root / "marker.txt"
    marker.write_text("keep")
    final_path_b = tmp_path / "out" / "other.mp4"
    w_b = ws.make_workspace(final_path_b, "vidb", "best")
    assert marker.exists() and marker.read_text() == "keep"
    assert w_a.root != w_b.root


def test_cyrillic_and_long_path(tmp_path: Path) -> None:
    ws = _import_workspace()
    final_path = tmp_path / "видео" / "Длинное имя файла.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    w = ws.make_workspace(final_path, "vid-кириллица", "best")
    assert w.root.exists()
    assert len(ws.stable_job_id("vid-кириллица", "best", final_path.name)) <= 120


def test_publish_exdev_leaves_both_files(tmp_path: Path, monkeypatch) -> None:
    ws = _import_workspace()
    import errno
    import os

    staged = tmp_path / "staged.mp4"
    final = tmp_path / "final.mp4"
    staged.write_bytes(b"staged-content")
    final.write_bytes(b"final-content")

    def _raise_exdev(*args, **kwargs):
        raise OSError(errno.EXDEV, "cross-device link")

    monkeypatch.setattr(os, "link", _raise_exdev)

    with pytest.raises(FileExistsError):
        ws.publish_verified_file(staged, final)

    assert staged.exists()
    assert staged.read_bytes() == b"staged-content"
    assert final.exists()
    assert final.read_bytes() == b"final-content"


def test_publish_race_no_overwrite(tmp_path: Path) -> None:
    ws = _import_workspace()

    final = tmp_path / "final.mp4"
    staged_a = tmp_path / "staged_a.mp4"
    staged_b = tmp_path / "staged_b.mp4"
    staged_a.write_bytes(b"content-a")
    staged_b.write_bytes(b"content-b")

    barrier = threading.Barrier(2)
    results: list[object] = []
    lock = threading.Lock()

    def worker(staged: Path) -> None:
        barrier.wait()
        try:
            ws.publish_verified_file(staged, final)
            with lock:
                results.append(("ok", staged.read_bytes()))
        except Exception as exc:  # noqa: BLE001
            with lock:
                results.append(("err", exc))

    ta = threading.Thread(target=worker, args=(staged_a,))
    tb = threading.Thread(target=worker, args=(staged_b,))
    ta.start()
    tb.start()
    ta.join()
    tb.join()

    assert len(results) == 2
    oks = [r for r in results if r[0] == "ok"]
    errs = [r for r in results if r[0] == "err"]
    assert len(oks) == 1, results
    assert len(errs) == 1, results
    assert isinstance(errs[0][1], FileExistsError)
    # final bytes unchanged relative to winner and still present
    assert final.exists()
    assert final.read_bytes() in (b"content-a", b"content-b")
    # both staged files survive
    assert staged_a.exists()
    assert staged_b.exists()


def test_segment_merge_targets_staging() -> None:
    seg = _import_segment()
    sig = inspect.signature(seg.download_hls_with_resume)
    assert "workspace" in sig.parameters


def test_legacy_root_part_not_touched(tmp_path: Path) -> None:
    ws = _import_workspace()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    legacy_part = out_dir / "video.mp4.part"
    legacy_part.write_bytes(b"legacy partial placeholder")

    discover = ws.discover_legacy_artifacts
    result = discover(out_dir)
    assert legacy_part.exists()
    assert isinstance(result, list)
    assert any(getattr(a, "path", None) == legacy_part for a in result)


def test_legacy_part_15gib_detected(tmp_path: Path) -> None:
    ws = _import_workspace()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    legacy_part = out_dir / "video.mp4.part"
    size = 15 * 1024**3
    with open(legacy_part, "wb") as handle:
        handle.seek(size - 1)
        handle.write(b"\x00")

    result = ws.discover_legacy_artifacts(out_dir)
    assert legacy_part.exists()
    assert isinstance(result, list)
    match = [a for a in result if getattr(a, "path", None) == legacy_part]
    assert match, result
    assert getattr(match[0], "size", None) == size


def test_job_lock_basic(tmp_path: Path) -> None:
    ws = _import_workspace()
    final_path = tmp_path / "out" / "video.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    workspace = ws.make_workspace(final_path, "vid1", "best")

    lock = ws.acquire_job_lock(workspace, timeout=1.0)
    assert lock is not None
    try:
        ws.acquire_job_lock(workspace, timeout=0.1)
    except Exception:
        pass
    release = getattr(lock, "release", None)
    if callable(release):
        release()


def test_cleanup_owned_job_artifacts(tmp_path: Path) -> None:
    ws = _import_workspace()
    final_path = tmp_path / "out" / "video.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    workspace = ws.make_workspace(final_path, "vid1", "best")
    assert workspace.root.exists()
    ws.cleanup_owned_job_artifacts(workspace)
    assert not workspace.root.exists()


def test_job_lock_real_process(tmp_path: Path) -> None:
    ws = _import_workspace()
    import subprocess
    import sys
    import time

    final_path = tmp_path / "out" / "video.mp4"
    final_path.parent.mkdir(parents=True, exist_ok=True)
    workspace = ws.make_workspace(final_path, "vid1", "best")

    src_root = str(Path(__file__).resolve().parents[2] / "src")
    script = (
        f"import sys, time; sys.path.insert(0, {src_root!r}); "
        "from pathlib import Path; "
        "from vkdownloader.services.workspace import _acquire_lock_at_path; "
        f"lock = _acquire_lock_at_path(Path({str(workspace.lock_path)!r}), 10.0); "
        "print('READY', flush=True); "
        "time.sleep(10); "
        "lock.release()"
    )

    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Wait for READY
    ready = False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        line = proc.stdout.readline() if proc.stdout else ""
        if "READY" in (line or ""):
            ready = True
            break
        if proc.poll() is not None:
            break
    assert ready, proc.stderr.read() if proc.stderr else ""

    try:
        with pytest.raises(DownloadError):
            ws.acquire_job_lock(workspace, timeout=0.2)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
