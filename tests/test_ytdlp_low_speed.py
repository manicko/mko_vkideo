"""Tests for LowSpeedWarningTracker (Block D1)."""

from unittest.mock import patch

from vkdownloader.services.ytdlp_downloader import LowSpeedWarningTracker


def _logger_path() -> str:
    return "vkdownloader.services.ytdlp_downloader.logger"


def test_threshold_zero_disables_warnings() -> None:
    tracker = LowSpeedWarningTracker(0)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(0, now=0.0)
        tracker.observe(100, now=3.0)
        tracker.observe(200, now=6.0)
        mock_logger.warning.assert_not_called()


def test_fewer_than_sample_count_no_warning() -> None:
    tracker = LowSpeedWarningTracker(1000)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(0, now=0.0)
        tracker.observe(100, now=3.0)
        mock_logger.warning.assert_not_called()


def test_window_shorter_than_min_no_warning() -> None:
    tracker = LowSpeedWarningTracker(1000)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(0, now=0.0)
        tracker.observe(100, now=1.0)
        tracker.observe(200, now=2.0)
        mock_logger.warning.assert_not_called()


def test_sustained_low_emits_one_warning() -> None:
    tracker = LowSpeedWarningTracker(1000)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(0, now=0.0)
        tracker.observe(100, now=1.5)
        result = tracker.observe(200, now=3.0)
        assert result is True
        mock_logger.warning.assert_called_once()
        call = mock_logger.warning.call_args
        assert call.args[0] == "ytdlp_low_speed"
        kwargs = call.kwargs
        assert kwargs["threshold_bytes_per_sec"] == 1000
        assert kwargs["sample_count"] == 3
        assert kwargs["downloaded"] == 200
        assert kwargs["window_seconds"] == 3.0
        assert kwargs["rate_bytes_per_sec"] > 0
        assert kwargs["rate_bytes_per_sec"] < 1000


def test_repeated_low_suppressed_until_cooldown() -> None:
    tracker = LowSpeedWarningTracker(1000)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(0, now=0.0)
        tracker.observe(100, now=1.5)
        tracker.observe(200, now=3.0)
        tracker.observe(300, now=4.5)
        tracker.observe(400, now=6.0)
        result = tracker.observe(500, now=7.5)
        assert result is False
        assert mock_logger.warning.call_count == 1


def test_after_cooldown_new_warning() -> None:
    tracker = LowSpeedWarningTracker(1000)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(0, now=0.0)
        tracker.observe(100, now=1.5)
        tracker.observe(200, now=3.0)
        tracker.observe(200, now=30.0)
        tracker.observe(300, now=31.5)
        result = tracker.observe(400, now=33.0)
        assert result is True
        assert mock_logger.warning.call_count == 2


def test_recovery_resets_episode() -> None:
    tracker = LowSpeedWarningTracker(1000)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(0, now=0.0)
        tracker.observe(100, now=1.5)
        tracker.observe(200, now=3.0)
        tracker.observe(200, now=4.5)
        tracker.observe(5000, now=6.0)
        tracker.observe(10000, now=7.5)
        tracker.observe(10000, now=9.0)
        tracker.observe(10100, now=10.5)
        result = tracker.observe(10200, now=12.0)
        assert mock_logger.warning.call_count == 2


def test_no_byte_growth_no_warning_and_reset() -> None:
    tracker = LowSpeedWarningTracker(1000)
    with patch(_logger_path()) as mock_logger:
        tracker.observe(100, now=0.0)
        tracker.observe(100, now=1.5)
        tracker.observe(100, now=3.0)
        mock_logger.warning.assert_not_called()
        tracker.observe(100, now=4.5)
        tracker.observe(200, now=6.0)
        result = tracker.observe(300, now=7.5)
        assert mock_logger.warning.call_count == 1


def test_observe_signature_only_downloaded_and_now() -> None:
    tracker = LowSpeedWarningTracker(1000)
    import inspect

    sig = inspect.signature(tracker.observe)
    params = list(sig.parameters.keys())
    assert params == ["downloaded", "now"]