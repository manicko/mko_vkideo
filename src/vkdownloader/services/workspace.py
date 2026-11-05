"""Per-job workspace contract under output/tmp.

This module centralises the on-disk layout for one download job: a stable
directory under ``<output>/tmp/jobs/<job>`` holding every in-progress artefact
(yt-dlp fragments, segments, staging, state, diagnostics, lock), plus a
shared ``<output>/tmp/logs`` sink. The final, validated video lives at
``final_path`` (output root) and is published only after validation.
"""

from __future__ import annotations

import os
import shutil
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from structlog import get_logger

from ..exceptions import DownloadError
from ..models.enums import ErrorCode
from ..utils.security import validate_final_output_path

logger = get_logger(__name__)

try:  # pragma: no cover - exercised only when filelock is absent
    from filelock import FileLock
    from filelock import Timeout as _FileLockTimeout
except Exception:  # noqa: BLE001
    FileLock = None  # type: ignore[assignment]
    _FileLockTimeout = Exception  # type: ignore[assignment]


@dataclass(frozen=True)
class DownloadWorkspace:
    """Immutable per-job workspace layout."""

    final_path: Path
    root: Path
    ytdlp_dir: Path
    segments_dir: Path
    staging_dir: Path
    diagnostics_dir: Path
    state_path: Path
    log_path: Path
    lock_path: Path


def stable_job_id(video_id: str, quality: str, final_basename: str) -> str:
    """Derive a stable, bounded job id from non-secret inputs."""
    logical = f"{video_id}|{quality}|{final_basename.casefold()}"
    digest = sha256(logical.encode("utf-8")).hexdigest()[:12]
    safe_vid = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(video_id))[:32]
    return f"video-{safe_vid}-q{quality}-{digest}"


def make_workspace(final_path: Path, video_id: str, quality: str) -> DownloadWorkspace:
    """Create (or reuse) the per-job workspace tree for ``final_path``."""
    validated_final = validate_final_output_path(Path(final_path))
    tmp = validated_final.parent / "tmp"
    job = tmp / "jobs" / stable_job_id(video_id, quality, validated_final.name)

    ws = DownloadWorkspace(
        final_path=validated_final,
        root=job,
        ytdlp_dir=job / "ytdlp",
        segments_dir=job / "segments",
        staging_dir=job / "staging",
        diagnostics_dir=job / "diagnostics",
        state_path=job / "state.json",
        log_path=tmp / "logs" / f"{job.name}.jsonl",
        lock_path=job / "lock",
    )
    for d in (
        ws.root,
        ws.ytdlp_dir,
        ws.segments_dir,
        ws.staging_dir,
        ws.diagnostics_dir,
        tmp / "logs",
    ):
        d.mkdir(parents=True, exist_ok=True)
    return ws


class JobLock:
    """Thin handle returned by :func:`acquire_job_lock`."""

    def __init__(self, path: Path, release_cb: Any = None, handle: Any = None) -> None:
        self.path = path
        self._release_cb = release_cb
        self._handle = handle
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        if self._release_cb is not None:
            try:
                self._release_cb()
            except Exception:  # noqa: BLE001
                pass
        if self._handle is not None:
            try:
                self._handle.release()
            except Exception:  # noqa: BLE001
                pass

    def __enter__(self) -> JobLock:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.release()


def _raise_locked() -> None:
    exc = DownloadError("Workspace is locked by another process")
    exc.error_code = ErrorCode.WORKSPACE_LOCKED
    raise exc


def _is_pid_alive(pid: int) -> bool:
    try:
        from .ytdlp_downloader import _is_pid_alive as probe

        return probe(pid)
    except Exception:  # noqa: BLE001
        pass
    if os.name == "nt":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x0400, False, pid)
        if handle == 0:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == 259
            return False
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def acquire_job_lock(workspace: DownloadWorkspace, timeout: float = 10.0) -> Any:
    """Acquire an exclusive lock for ``workspace``."""
    lock_path = workspace.lock_path
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if FileLock is not None:
        lock = FileLock(str(lock_path), timeout=timeout)
        try:
            lock.acquire(timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if isinstance(exc, _FileLockTimeout) or "timeout" in msg or "lock" in msg:
                _raise_locked()
            raise
        return lock

    # Fallback: O_EXCL + PID owner.
    deadline = time.monotonic() + max(float(timeout), 0.0)

    def _read_owner() -> int | None:
        try:
            return int(lock_path.read_text().strip())
        except OSError, ValueError:
            return None

    while True:
        try:
            fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            handle_path = lock_path

            def _release() -> None:
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

            return JobLock(handle_path, release_cb=_release)
        except FileExistsError:
            owner = _read_owner()
            if owner is not None and not _is_pid_alive(owner):
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                _raise_locked()
            time.sleep(0.05)


def publish_verified_file(
    staged: Path,
    final: Path,
    final_lock: Any = None,
) -> Path:
    """Publish ``staged`` to ``final`` via an atomic, collision-safe rename."""
    staged = Path(staged)
    final = Path(final)

    def _do() -> Path:
        if final.exists() or final.is_symlink():
            raise FileExistsError(f"Refusing to overwrite existing output: {final}")
        os.rename(str(staged), str(final))
        return final

    if final_lock is not None and hasattr(final_lock, "__enter__"):
        with final_lock:
            return _do()
    return _do()


def cleanup_owned_job_artifacts(workspace: DownloadWorkspace) -> None:
    """Remove the owned job directory after a verified commit."""
    try:
        if workspace.root.exists():
            shutil.rmtree(workspace.root)
    except OSError:
        pass


@dataclass(frozen=True)
class LegacyArtifact:
    path: Path
    size: int
    kind: str


def discover_legacy_artifacts(output_dir: Path) -> list[LegacyArtifact]:
    """Dry-run discovery of legacy in-progress artefacts at ``output_dir``."""
    output_dir = Path(output_dir)
    result: list[LegacyArtifact] = []
    if not output_dir.exists():
        return result
    try:
        entries = list(output_dir.iterdir())
    except OSError:
        return result
    for entry in entries:
        kind: str | None = None
        if entry.is_file():
            name = entry.name
            if name.endswith(".part") or ".part-Frag" in name or name.endswith(".ytdl"):
                kind = "partial"
        elif entry.is_dir():
            if entry.name.startswith(".") and entry.name.endswith("_segments"):
                kind = "segments"
        if kind is None:
            continue
        try:
            if entry.is_file():
                size = entry.stat().st_size
            else:
                size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
        except OSError:
            size = 0
        result.append(LegacyArtifact(path=entry, size=size, kind=kind))
    return result


__all__ = [
    "DownloadWorkspace",
    "JobLock",
    "LegacyArtifact",
    "acquire_job_lock",
    "cleanup_owned_job_artifacts",
    "discover_legacy_artifacts",
    "publish_verified_file",
    "stable_job_id",
    "make_workspace",
]
