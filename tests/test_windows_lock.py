"""Tests for the Windows descriptor-holding helper."""

from __future__ import annotations

import sys
import threading

import pytest

from tests.integration.fixtures.windows_lock import WindowsDescriptorHolder, windows_lock


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_windows_holder_opens(tmp_path) -> None:
    p = tmp_path / "target.part"
    p.write_bytes(b"x")
    with WindowsDescriptorHolder(p) as h:
        assert h.handle is not None


def test_platform_guard_allows_posix_fallback(tmp_path) -> None:
    p = tmp_path / "target.part"
    p.write_bytes(b"x")
    with windows_lock(p, timeout=0.1):
        assert p.exists()


def test_budget_exhaustion_mode(tmp_path) -> None:
    p = tmp_path / "target.part"
    p.write_bytes(b"x")
    ev = threading.Event()
    with windows_lock(p, timeout=0.2, release_event=ev, budget_exhaustion=True):
        pass
    assert p.exists()
