"""RED tests for Block G yt-dlp outer loop scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest

from vkdownloader.config import Settings


def _import_ytdlp():
    try:
        from vkdownloader.services.ytdlp_downloader import _build_ytdlp_cli_command
    except ImportError as exc:
        pytest.fail(f"yt-dlp helpers not available: {exc}")
    return _build_ytdlp_cli_command


def _import_state_machine():
    try:
        from vkdownloader.models.enums import DownloadState, ErrorCategory
        from vkdownloader.services.state_machine import DownloadStateMachine
    except ImportError as exc:
        pytest.fail(f"Block G state machine not available: {exc}")
    return DownloadState, ErrorCategory, DownloadStateMachine


def test_ytdlp_internal_retries_are_one(test_settings: Settings) -> None:
    from vkdownloader.config import Settings

    custom = Settings(max_retries=3)
    _build_ytdlp_cli_command = _import_ytdlp()
    cmd, _ = _build_ytdlp_cli_command(
        output_file=Path("/tmp/test.mp4"),
        quality_str="720",
        user_agent=custom.user_agent,
        settings=custom,
        cookies=None,
        raw_cookies=None,
    )
    assert "-R" in cmd
    assert cmd[cmd.index("-R") + 1] == "1"
    assert "--fragment-retries" in cmd
    assert cmd[cmd.index("--fragment-retries") + 1] == "1"


def test_block_g_state_machine_importable() -> None:
    DownloadState, ErrorCategory, DownloadStateMachine = _import_state_machine()
    assert DownloadState is not None
    assert ErrorCategory is not None
    assert DownloadStateMachine is not None
