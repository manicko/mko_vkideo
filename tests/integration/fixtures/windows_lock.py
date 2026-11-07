"""Platform-guarded helper for holding a file descriptor without FILE_SHARE_DELETE.

This module provides a small test helper used to reproduce Windows
``SHARING VIOLATION`` conditions. On Windows it opens the target file with
``CreateFileW`` using ``FILE_SHARE_READ | FILE_SHARE_WRITE`` (deliberately
omitting ``FILE_SHARE_DELETE``) and keeps the handle open until released by
an event or a budget timeout. On POSIX platforms a best-effort ``fcntl.flock``
fallback is provided; the real WinError 32 path is covered by fault injection.
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
INVALID_HANDLE_VALUE = -1


def is_windows() -> bool:
    return sys.platform == "win32"


class WindowsDescriptorHolder:
    """Hold an open handle to a file without FILE_SHARE_DELETE."""

    def __init__(
        self,
        path: str | Path,
        *,
        creation_disposition: int = OPEN_ALWAYS,
        timeout: float | None = None,
        release_event: threading.Event | None = None,
        budget_exhaustion: bool = False,
    ) -> None:
        self.path = Path(path)
        self.creation_disposition = creation_disposition
        self.timeout = timeout
        self.release_event = release_event
        self.budget_exhaustion = budget_exhaustion
        self.handle: Any = None
        self._thread: threading.Thread | None = None

    def _open_windows(self) -> None:
        handle = ctypes.windll.kernel32.CreateFileW(
            str(self.path),
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            self.creation_disposition,
            0,
            None,
        )
        if handle == INVALID_HANDLE_VALUE:
            raise OSError(ctypes.get_last_error() or 32, "CreateFileW failed")
        self.handle = handle

    def _open_posix(self) -> None:
        fd = os.open(str(self.path), os.O_RDWR | os.O_CREAT)
        self.handle = fd
        try:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        except Exception:  # noqa: BLE001
            pass

    def _hold(self) -> None:
        if self.release_event is not None:
            self.release_event.wait(self.timeout)
        elif self.timeout is not None:
            time.sleep(self.timeout)
        self.release()

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            if is_windows():
                ctypes.windll.kernel32.CloseHandle(self.handle)
            else:
                try:
                    import fcntl

                    fcntl.flock(self.handle, fcntl.LOCK_UN)
                except Exception:  # noqa: BLE001
                    pass
                os.close(self.handle)
        except Exception:  # noqa: BLE001
            pass
        finally:
            self.handle = None

    def __enter__(self) -> WindowsDescriptorHolder:
        if is_windows():
            self._open_windows()
        else:
            self._open_posix()
        if self.budget_exhaustion or (self.timeout is not None and self.timeout > 0):
            event = self.release_event or threading.Event()
            self.release_event = event
            self._thread = threading.Thread(target=self._hold, daemon=True)
            self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=0.5)


@contextmanager
def windows_lock(
    path: str | Path,
    *,
    timeout: float | None = None,
    release_event: threading.Event | None = None,
    budget_exhaustion: bool = False,
    creation_disposition: int = OPEN_ALWAYS,
):
    holder = WindowsDescriptorHolder(
        path,
        creation_disposition=creation_disposition,
        timeout=timeout,
        release_event=release_event,
        budget_exhaustion=budget_exhaustion,
    )
    with holder:
        yield holder


def hold_file_descriptor(path, **kwargs: Any) -> WindowsDescriptorHolder:
    return WindowsDescriptorHolder(path, **kwargs)


WindowsLock = WindowsDescriptorHolder
WindowsFileLock = WindowsDescriptorHolder
DescriptorHolder = WindowsDescriptorHolder

__all__ = [
    "WindowsDescriptorHolder",
    "WindowsLock",
    "WindowsFileLock",
    "DescriptorHolder",
    "windows_lock",
    "hold_file_descriptor",
    "is_windows",
    "OPEN_ALWAYS",
    "OPEN_EXISTING",
]
