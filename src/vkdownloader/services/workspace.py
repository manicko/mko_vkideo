"""Per-job workspace contract under output/tmp.

This module centralises the on-disk layout for one download job: a stable
directory under ``<output>/tmp/jobs/<job>`` holding every in-progress artefact
(yt-dlp fragments, segments, staging, state, diagnostics, lock), plus a
shared ``<output>/tmp/logs`` sink. The final, validated video lives at
``final_path`` (output root) and is published only after validation.
"""

from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from structlog import get_logger

from ..exceptions import DownloadError
from ..models.enums import ErrorCode
from ..utils.security import validate_final_output_path

logger = get_logger(__name__)

# Quality tokens must be safe path components: alphanumerics, underscore and
# hyphen, at most 16 characters. Anything else (path separators, "..", spaces)
# is rejected fail-closed (P1-1).
_QUALITY_RE = re.compile(r"^[A-Za-z0-9_-]{1,16}$")


def _validate_quality(quality: object) -> str:
    q = str(quality)
    if ".." in q or "/" in q or "\\" in q:
        raise ValueError(f"Unsafe quality token: {quality!r}")
    if not _QUALITY_RE.fullmatch(q):
        raise ValueError(f"Invalid quality token: {quality!r}")
    return q


try:  # pragma: no cover - exercised only when filelock is absent
    from filelock import FileLock
    from filelock import Timeout as _FileLockTimeout
except Exception:  # noqa: BLE001
    FileLock = None  # type: ignore
    _FileLockTimeout = Exception  # type: ignore


@dataclass(frozen=True)
class DownloadWorkspace:
    """Immutable per-job workspace layout."""

    final_path: Path
    root: Path
    ytdlp_dir: Path
    segments_dir: Path
    staging_dir: Path
    diagnostics_dir: Path
    job_state_path: Path
    segment_checkpoint_path: Path
    state_path: Path
    log_path: Path
    lock_path: Path
    job_id: str


def stable_job_id(video_id: str, quality: str, final_basename: str) -> str:
    """Derive a stable, bounded job id from non-secret inputs."""
    quality = _validate_quality(quality)
    logical = f"{video_id}|{quality}|{final_basename.casefold()}"
    digest = sha256(logical.encode("utf-8")).hexdigest()[:12]
    safe_vid = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(video_id))[:32]
    return f"video-{safe_vid}-q{quality}-{digest}"


def make_workspace(final_path: Path, video_id: str, quality: str) -> DownloadWorkspace:
    """Create (or reuse) the per-job workspace tree for ``final_path``."""
    quality = _validate_quality(quality)
    validated_final = validate_final_output_path(Path(final_path))
    job_id = stable_job_id(video_id, quality, validated_final.name)
    tmp = validated_final.parent / "tmp"
    job = tmp / "jobs" / job_id

    ws = DownloadWorkspace(
        final_path=validated_final,
        root=job,
        ytdlp_dir=job / "ytdlp",
        segments_dir=job / "segments",
        staging_dir=job / "staging",
        diagnostics_dir=job / "diagnostics",
        job_state_path=job / "job_state.v2.json",
        segment_checkpoint_path=job / "segment_checkpoint.v2.json",
        state_path=job / "state.json",
        log_path=tmp / "logs" / f"{job.name}.jsonl",
        lock_path=tmp / "locks" / f"{job_id}.lock",
        job_id=job_id,
    )
    # Create lock parent before acquiring lock (unlocked).
    (tmp / "locks").mkdir(parents=True, exist_ok=True)
    creation_lock = _acquire_lock_at_path(ws.lock_path, 10.0)
    try:
        for d in (
            ws.root,
            ws.ytdlp_dir,
            ws.segments_dir,
            ws.staging_dir,
            ws.diagnostics_dir,
            tmp / "logs",
        ):
            d.mkdir(parents=True, exist_ok=True)
        marker = ws.root / ".vkdownloader-job"
        marker.write_text(ws.job_id, encoding="utf-8")
    finally:
        creation_lock.release()
    return ws


class JobLock:
    """Thin handle returned by :func:`acquire_job_lock`."""

    def __init__(self, path: Path, release_cb: object = None, handle: object = None) -> None:
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
                self._release_cb()  # type: ignore[operator]
            except Exception:  # noqa: BLE001
                pass
        if self._handle is not None:
            try:
                self._handle.release()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass

    def __enter__(self) -> JobLock:
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()


def _raise_locked() -> None:
    exc = DownloadError("Workspace is locked by another process")
    exc.error_code = ErrorCode.WORKSPACE_LOCKED
    raise exc


def _is_pid_alive(pid: int) -> bool:
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


class _JobLockLike(Protocol):
    def __enter__(self) -> _JobLockLike: ...
    def __exit__(self, *exc: object) -> None: ...
    def release(self) -> None: ...


def _acquire_lock_at_path(lock_path: Path, timeout: float = 10.0) -> JobLock:
    """Acquire an exclusive lock at ``lock_path``, returning a JobLock."""
    lock_path = Path(lock_path)
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
        return JobLock(path=lock_path, handle=lock)

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

            def _release() -> None:
                try:
                    lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

            return JobLock(path=lock_path, release_cb=_release)
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


def acquire_job_lock(workspace: DownloadWorkspace, timeout: float = 10.0) -> JobLock:
    """Acquire an exclusive lock for ``workspace``."""
    return _acquire_lock_at_path(workspace.lock_path, timeout)


def acquire_publish_lock(final: Path, timeout: float = 10.0) -> JobLock:
    """Acquire an exclusive lock for publishing ``final``."""
    final = Path(final)
    lock_path = final.parent / f".{final.name}.publish.lock"
    return _acquire_lock_at_path(lock_path, timeout)


def publish_verified_file(
    staged: Path,
    final: Path,
    final_lock: object = None,
) -> Path:
    """Publish ``staged`` to ``final`` via an atomic, collision-safe operation.

    Copies the staged payload into a reserved temp file in ``final.parent``,
    fsyncs it, then commits with ``os.link`` (no-clobber). A guarded
    ``os.replace`` fallback is used only for unsupported hard-link errors.
    """
    import errno as _errno

    staged = Path(staged)
    final = Path(final)
    final.parent.mkdir(parents=True, exist_ok=True)

    if not staged.is_file():
        raise FileNotFoundError(f"Staged file not found: {staged}")

    lock = (
        final_lock
        if (final_lock is not None and hasattr(final_lock, "__enter__"))
        else acquire_publish_lock(final, 10.0)
    )
    temp = final.parent / f".{final.name}.publish-{os.getpid()}-{uuid.uuid4().hex}.tmp"

    with lock:  # type: ignore[attr-defined]
        if final.exists() or final.is_symlink():
            raise FileExistsError(f"Refusing to overwrite existing output: {final}")

        try:
            fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            try:
                with os.fdopen(fd, "wb") as out:
                    with open(staged, "rb") as src:
                        shutil.copyfileobj(src, out, length=1024 * 1024)
                    out.flush()
                    os.fsync(out.fileno())
            except BaseException:
                temp.unlink(missing_ok=True)
                raise

            try:
                os.link(str(temp), str(final))
            except OSError as exc:
                if exc.errno == _errno.EEXIST:
                    temp.unlink(missing_ok=True)
                    raise FileExistsError(
                        f"Refusing to overwrite existing output: {final}"
                    ) from exc
                if exc.errno in (
                    _errno.EXDEV,
                    _errno.ENOTSUP,
                    _errno.EOPNOTSUPP,
                    _errno.EPERM,
                    _errno.ENOSYS,
                ):
                    if final.exists() or final.is_symlink():
                        temp.unlink(missing_ok=True)
                        raise FileExistsError(
                            f"Refusing to overwrite existing output: {final}"
                        ) from None
                    os.replace(str(temp), str(final))
                else:
                    temp.unlink(missing_ok=True)
                    raise

            temp.unlink(missing_ok=True)

            try:
                if staged.exists():
                    staged.unlink()
            except OSError:
                pass

            _fsync_dir(final.parent)

            if not (final.exists() and final.is_file() and final.stat().st_size > 0):
                raise OSError(f"Published file missing after commit: {final}")
            return final
        except BaseException:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise


def _fsync_dir(path: Path) -> None:
    """Best-effort fsync of a directory; skipped on Windows."""
    if os.name == "nt":
        return
    try:
        dir_fd = os.open(str(path), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


@dataclass(frozen=True)
class LegacyArtifact:
    path: Path
    size: int
    kind: str


def cleanup_owned_job_artifacts(workspace: DownloadWorkspace) -> None:
    """Remove the owned job directory after a verified commit."""
    root = Path(workspace.root)
    try:
        if root.is_symlink():
            logger.warning("cleanup_refused_symlink", root=str(root))
            return
        resolved_root = root.resolve()
    except OSError:
        logger.warning("cleanup_refused_resolve", root=str(root))
        return

    tmp_jobs = (workspace.final_path.parent / "tmp" / "jobs").resolve()
    if resolved_root.parent != tmp_jobs:
        logger.warning("cleanup_refused_containment", root=str(resolved_root))
        return
    if resolved_root.name != workspace.job_id:
        logger.warning("cleanup_refused_name", root=str(resolved_root))
        return

    marker = resolved_root / ".vkdownloader-job"
    try:
        marker_text = marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""
    except OSError:
        marker_text = ""
    if marker_text != workspace.job_id:
        logger.warning("cleanup_refused_marker", root=str(resolved_root))
        return

    try:
        if resolved_root.exists():
            shutil.rmtree(resolved_root)
    except OSError:
        pass


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
        if entry.is_symlink():
            continue
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


def migrate_legacy_artifacts(
    output_dir: Path,
    workspace: DownloadWorkspace,
    *,
    dry_run: bool = True,
    verify: bool = True,
    remove_original: bool = False,
) -> list[dict[str, object]]:
    """Opt-in migration of legacy artifacts into the owned workspace.

    Defaults to dry-run and preserves both copies until verification.
    """
    artifacts = discover_legacy_artifacts(Path(output_dir))
    plan: list[dict[str, object]] = []
    for artifact in artifacts:
        if artifact.kind == "segments":
            destination = Path(workspace.segments_dir)
        else:
            destination = Path(workspace.staging_dir) / Path(artifact.path).name

        if dry_run:
            plan.append(
                {
                    "artifact": str(artifact.path),
                    "destination": str(destination),
                    "action": "planned",
                }
            )
            continue

        if destination.exists():
            plan.append(
                {
                    "artifact": str(artifact.path),
                    "destination": str(destination),
                    "action": "already_migrated",
                }
            )
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        src_hash = None
        if Path(artifact.path).is_file():
            src_hash = _file_hash(Path(artifact.path))
            shutil.copy2(artifact.path, destination)
            if verify:
                if _file_hash(destination) != src_hash:
                    try:
                        destination.unlink(missing_ok=True)
                    except OSError:
                        pass
                    raise RuntimeError("legacy migration verification failed")
        else:
            shutil.copytree(artifact.path, destination)

        if remove_original:
            try:
                if Path(artifact.path).is_file():
                    Path(artifact.path).unlink()
                else:
                    shutil.rmtree(artifact.path)
            except OSError:
                pass

        plan.append(
            {
                "artifact": str(artifact.path),
                "destination": str(destination),
                "action": "migrated",
            }
        )
    return plan


def _file_hash(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


__all__ = [
    "DownloadWorkspace",
    "JobLock",
    "LegacyArtifact",
    "acquire_job_lock",
    "acquire_publish_lock",
    "cleanup_owned_job_artifacts",
    "discover_legacy_artifacts",
    "migrate_legacy_artifacts",
    "publish_verified_file",
    "stable_job_id",
    "make_workspace",
]
