"""RED tests for Block G retry state machine."""

from __future__ import annotations

import asyncio
from enum import StrEnum
from unittest.mock import patch

import pytest


def _import_block_g():
    try:
        from vkdownloader.models.enums import DownloadState, ErrorCategory
        from vkdownloader.services.state_machine import (
            COMBINED_RETRY_BUDGET,
            REFRESH_CAP,
            YTDLP_INTERNAL_RETRIES,
            DownloadJobState,
            DownloadStateMachine,
        )
    except ImportError as exc:
        pytest.fail(f"Block G modules not available: {exc}")
    return (
        DownloadState,
        ErrorCategory,
        DownloadJobState,
        DownloadStateMachine,
        YTDLP_INTERNAL_RETRIES,
        REFRESH_CAP,
        COMBINED_RETRY_BUDGET,
    )


def _job_state(sm):
    return getattr(sm, "job_state", None) or getattr(sm, "_job_state", None)


def _new_sm(tmp_path):
    (
        DownloadState,
        ErrorCategory,
        DownloadJobState,
        DownloadStateMachine,
        YTDLP_INTERNAL_RETRIES,
        REFRESH_CAP,
        COMBINED_RETRY_BUDGET,
    ) = _import_block_g()
    from vkdownloader.services.workspace import make_workspace

    ws = make_workspace(tmp_path / "out.mp4", "vid1", "720")
    try:
        sm = DownloadStateMachine.create(job_id=ws.job_id, workspace=ws)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id=ws.job_id), workspace=ws)
    return DownloadState, ErrorCategory, DownloadJobState, DownloadStateMachine, sm, ws


def test_download_state_is_strenum():
    DownloadState, *_ = _import_block_g()
    assert issubclass(DownloadState, StrEnum)
    expected = {
        "created",
        "resolve_stream",
        "validate_variant",
        "download",
        "retry_same_segment",
        "refresh_stream",
        "rate_limit_wait",
        "retry",
        "verify_media",
        "commit",
        "done",
        "preserve_and_stop",
        "cancelled",
        "disk_full",
        "failed_retry_budget",
        "integrity_failed",
        "failed",
        "all_segments_verified",
        "merging_in_staging",
        "candidate_ready",
        "validating",
        "validated",
        "atomic_no_clobber_publication",
        "final_committed",
        "cleanup_owned_temp_artifacts",
    }
    assert {m.value for m in DownloadState} == expected


def test_error_category_is_strenum():
    _, ErrorCategory, *_ = _import_block_g()
    assert issubclass(ErrorCategory, StrEnum)
    expected = {
        "connection_timeout",
        "connection_reset",
        "auth_expired",
        "rate_limited",
        "server_error",
        "not_found",
        "slow_throughput",
        "disk_full",
        "permission_error",
        "file_locked",
        "invalid_output_path",
        "cancelled",
        "incompatible_playlist",
        "incompatible_codec",
        "integrity_failure",
        "unknown",
    }
    assert {m.value for m in ErrorCategory} == expected


def test_job_state_pydantic():
    _, _, DownloadJobState, *_ = _import_block_g()
    from pydantic import BaseModel

    assert issubclass(DownloadJobState, BaseModel)
    s = DownloadJobState(job_id="job-1")
    assert s.job_id == "job-1"


def test_constants():
    *_, YTDLP_INTERNAL_RETRIES, REFRESH_CAP, COMBINED_RETRY_BUDGET = _import_block_g()
    assert YTDLP_INTERNAL_RETRIES == 1
    assert REFRESH_CAP == 2
    assert COMBINED_RETRY_BUDGET == 6


def test_allowed_transition_persists(tmp_path):
    DownloadState, _, _, _, sm, ws = _new_sm(tmp_path)
    sm.transition(DownloadState.RESOLVE_STREAM, reason_code="start")
    assert sm.state == DownloadState.RESOLVE_STREAM
    assert ws.job_state_path.exists()
    from vkdownloader.services.state_machine import DownloadStateMachine

    loaded = DownloadStateMachine.load(ws)
    assert loaded.state == DownloadState.RESOLVE_STREAM


def test_disallowed_transition_raises(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    with pytest.raises(ValueError):
        sm.transition(DownloadState.DONE)
    assert sm.state == DownloadState.CREATED


def test_load_restores_counters(tmp_path):
    DownloadState, _, _, DownloadStateMachine, sm, ws = _new_sm(tmp_path)
    js = _job_state(sm)
    js.verified_segments = 7
    js.verified_bytes = 1234
    js.network_bytes_this_session = 5678
    js.attempt_id = 3
    js.fragment_done = 2
    js.fragment_total = 10
    sm.persist()
    loaded = DownloadStateMachine.load(ws)
    ljs = _job_state(loaded)
    assert ljs.verified_segments == 7
    assert ljs.verified_bytes == 1234
    assert ljs.network_bytes_this_session == 5678
    assert ljs.attempt_id == 3
    assert ljs.fragment_done == 2
    assert ljs.fragment_total == 10


def test_atomic_write_uses_os_replace(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    with patch("os.replace") as m:
        sm.transition(DownloadState.RESOLVE_STREAM, reason_code="start", persist=True)
        assert m.called


def test_combined_retry_budget(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    *_, COMBINED_RETRY_BUDGET = _import_block_g()
    for _ in range(COMBINED_RETRY_BUDGET):
        assert sm.record_retry("yt-dlp", "reason", 1.0)
    assert not sm.record_retry("yt-dlp", "reason", 1.0)
    assert sm.is_budget_exhausted()


def test_refresh_cap(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    *_, _, REFRESH_CAP, _ = _import_block_g()
    for _ in range(REFRESH_CAP):
        assert sm.request_refresh("reason")
    assert not sm.request_refresh("reason")


def test_classify_timeout():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    assert sm.classify_error(TimeoutError("t")) == ErrorCategory.CONNECTION_TIMEOUT


def test_classify_connection_reset():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    assert sm.classify_error(ConnectionResetError("r")) == ErrorCategory.CONNECTION_RESET


def test_classify_auth():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    for st in (401, 403, 410):
        assert sm.classify_error(Exception("a"), http_status=st) == ErrorCategory.AUTH_EXPIRED


def test_classify_rate_limited():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    assert sm.classify_error(Exception("r"), http_status=429) == ErrorCategory.RATE_LIMITED


def test_classify_server_error():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    assert sm.classify_error(Exception("s"), http_status=500) == ErrorCategory.SERVER_ERROR


def test_classify_not_found():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    assert sm.classify_error(Exception("nf"), http_status=404) == ErrorCategory.NOT_FOUND


def test_classify_disk_full():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    import errno

    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    exc = OSError(errno.ENOSPC, "No space left on device")
    assert sm.classify_error(exc) == ErrorCategory.DISK_FULL


def test_classify_cancelled():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    assert sm.classify_error(asyncio.CancelledError()) == ErrorCategory.CANCELLED


def test_classify_permission():
    _, ErrorCategory, _, _, _, _, _ = _import_block_g()
    import errno

    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    exc = OSError(errno.EACCES, "Permission denied")
    assert sm.classify_error(exc) == ErrorCategory.PERMISSION_ERROR


def test_observe_throughput_single_false():
    _, _, _, _, _, _, _ = _import_block_g()
    from vkdownloader.services.state_machine import DownloadJobState, DownloadStateMachine

    try:
        sm = DownloadStateMachine.create(job_id="job-1", workspace=None)
    except TypeError:
        sm = DownloadStateMachine(DownloadJobState(job_id="job-1"), workspace=None)
    assert sm.observe_throughput(10) is False


def test_record_retry_increments(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    js = _job_state(sm)
    before = js.retries_used
    assert sm.record_retry("yt-dlp", "reason", 1.5)
    assert _job_state(sm).retries_used == before + 1


def test_request_refresh_and_completed(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    assert sm.request_refresh("token_expired")
    assert _job_state(sm).refresh_count == 1
    sm.record_refresh_completed(quality_match=True, variant_match=True)


def test_reverify_playlist_on_404(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    sm.reverify_playlist_on_404()
    assert getattr(_job_state(sm), "playlist_reverified", False) is True


def test_terminal_preserve_artifacts(tmp_path):
    DownloadState, _, _, _, sm, ws = _new_sm(tmp_path)
    assert _job_state(sm).preserve_artifacts is True
    artifact = ws.root / "partial.bin"
    artifact.write_text("x")
    *_, COMBINED_RETRY_BUDGET = _import_block_g()
    for _ in range(COMBINED_RETRY_BUDGET + 1):
        sm.record_retry("yt-dlp", "reason", 0.1)
    assert artifact.exists()


def test_counters_exposed():
    _, _, DownloadJobState, *_ = _import_block_g()
    js = DownloadJobState(job_id="job-1")
    for f in (
        "verified_segments",
        "verified_bytes",
        "network_bytes_this_session",
        "attempt_id",
        "fragment_done",
        "fragment_total",
    ):
        assert hasattr(js, f)


def test_no_secrets_persisted(tmp_path):
    DownloadState, _, _, _, sm, ws = _new_sm(tmp_path)
    sm.persist()
    text = ws.job_state_path.read_text(encoding="utf-8")
    assert "SECRET" not in text
    assert "token=" not in text
    assert "cookie" not in text.lower()


def test_can_transition_helper(tmp_path):
    DownloadState, _, _, _, sm, _ = _new_sm(tmp_path)
    assert isinstance(sm.can_transition(DownloadState.RESOLVE_STREAM), bool)
