"""Tests for segment_downloader token-refresh retry logic."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.services.segment_downloader import (
    _fetch_playlist_with_retry,
    _log_preserve_segments,
)


class TestFetchPlaylistWithRetry:
    """Tests for _fetch_playlist_with_retry token-refresh path.

    These exercise the real retry loop (refresh + retry) rather than mocking
    _fetch_playlist_with_retry with a static return value.
    """

    @pytest.mark.asyncio
    async def test_token_refresh_runs_on_403_then_retry_succeeds(
        self, test_settings: Settings
    ) -> None:
        """Test that a 403 triggers token refresh and a real retry that succeeds."""
        video_url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://example.com/initial.m3u8"
        refreshed_url = "https://example.com/refreshed.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}
        playlist = "#EXTM3U\nseg1.ts\nseg2.ts"

        refresh_calls: list[tuple[str, dict[str, str]]] = []
        fetch_urls: list[str] = []

        async def fake_refresh(
            vid: str, extractor: MagicMock, settings: Settings, hdr: dict[str, str]
        ) -> str:
            refresh_calls.append((vid, hdr))
            return refreshed_url

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            fetch_urls.append(url)
            if len(fetch_urls) == 1:
                return "", 403
            return playlist, 200

        mock_session = MagicMock()
        mock_extractor = MagicMock()

        with patch(
            "vkdownloader.services.segment_downloader._handle_token_refresh",
            side_effect=fake_refresh,
        ):
            with patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ):
                result = await _fetch_playlist_with_retry(
                    mock_session,
                    video_url,
                    m3u8_url,
                    headers,
                    mock_extractor,
                    test_settings,
                    max_retries=3,
                )

        # Token refresh actually ran, then a second fetch with the refreshed URL.
        assert result == playlist
        assert len(refresh_calls) == 1
        assert refresh_calls[0][0] == video_url
        assert fetch_urls == [m3u8_url, refreshed_url]

    @pytest.mark.asyncio
    async def test_token_refresh_runs_on_410_then_retry_succeeds(
        self, test_settings: Settings
    ) -> None:
        """Test that a 410 triggers token refresh and a real retry that succeeds."""
        video_url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://example.com/initial.m3u8"
        refreshed_url = "https://example.com/refreshed.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}
        playlist = "#EXTM3U\nseg1.ts"

        refresh_calls: list[object] = []
        fetch_statuses: list[int] = []

        async def fake_refresh(
            vid: str, extractor: MagicMock, settings: Settings, hdr: dict[str, str]
        ) -> str:
            refresh_calls.append(object())
            return refreshed_url

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            if not fetch_statuses:
                fetch_statuses.append(410)
                return "", 410
            fetch_statuses.append(200)
            return playlist, 200

        mock_session = MagicMock()
        mock_extractor = MagicMock()

        with patch(
            "vkdownloader.services.segment_downloader._handle_token_refresh",
            side_effect=fake_refresh,
        ):
            with patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ):
                result = await _fetch_playlist_with_retry(
                    mock_session,
                    video_url,
                    m3u8_url,
                    headers,
                    mock_extractor,
                    test_settings,
                    max_retries=3,
                )

        assert result == playlist
        assert len(refresh_calls) == 1
        assert len(fetch_statuses) == 2
        assert fetch_statuses == [410, 200]

    @pytest.mark.asyncio
    async def test_no_refresh_when_status_not_403_or_410(self, test_settings: Settings) -> None:
        """Test that non-403/410 errors return None without refreshing."""
        video_url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://example.com/initial.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}

        refresh_call_count = 0

        async def fake_refresh(
            vid: str, extractor: MagicMock, settings: Settings, hdr: dict[str, str]
        ) -> str | None:
            nonlocal refresh_call_count
            refresh_call_count += 1
            return None

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            return "", 404

        mock_session = MagicMock()
        mock_extractor = MagicMock()

        with patch(
            "vkdownloader.services.segment_downloader._handle_token_refresh",
            side_effect=fake_refresh,
        ):
            with patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ):
                result = await _fetch_playlist_with_retry(
                    mock_session,
                    video_url,
                    m3u8_url,
                    headers,
                    mock_extractor,
                    test_settings,
                    max_retries=3,
                )

        assert result is None
        assert refresh_call_count == 0

    @pytest.mark.asyncio
    async def test_no_refresh_and_no_retry_when_extractor_missing(
        self, test_settings: Settings
    ) -> None:
        """Test that a 403 with no extractor does not attempt token refresh."""
        video_url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://example.com/initial.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}

        refresh_call_count = 0

        async def fake_refresh(
            vid: str, extractor: MagicMock, settings: Settings, hdr: dict[str, str]
        ) -> str | None:
            nonlocal refresh_call_count
            refresh_call_count += 1
            return None

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            return "", 403

        mock_session = MagicMock()

        with patch(
            "vkdownloader.services.segment_downloader._handle_token_refresh",
            side_effect=fake_refresh,
        ):
            with patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ):
                result = await _fetch_playlist_with_retry(
                    mock_session,
                    video_url,
                    m3u8_url,
                    headers,
                    None,
                    test_settings,
                    max_retries=3,
                )

        assert result is None
        assert refresh_call_count == 0

    @pytest.mark.asyncio
    async def test_refresh_failure_falls_through(self, test_settings: Settings) -> None:
        """Test that a refresh returning None yields no retry and returns None."""
        video_url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://example.com/initial.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}

        refresh_calls: list[object] = []
        fetch_count = 0

        async def fake_refresh(
            vid: str, extractor: MagicMock, settings: Settings, hdr: dict[str, str]
        ) -> str | None:
            refresh_calls.append(object())
            return None

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            nonlocal fetch_count
            fetch_count += 1
            return "", 403

        mock_session = MagicMock()
        mock_extractor = MagicMock()

        with patch(
            "vkdownloader.services.segment_downloader._handle_token_refresh",
            side_effect=fake_refresh,
        ):
            with patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ):
                result = await _fetch_playlist_with_retry(
                    mock_session,
                    video_url,
                    m3u8_url,
                    headers,
                    mock_extractor,
                    test_settings,
                    max_retries=3,
                )

        assert result is None
        # Refresh was attempted once, but no second fetch occurred (fell through).
        assert len(refresh_calls) == 1
        assert fetch_count == 1


class TestPreserveSegmentsReporter:
    """D-13: the reporter speaks on every non-success exit."""

    def test_reports_zero_count_directory(self, tmp_path: Path) -> None:
        """A directory with zero segments still produces a log record.

        The old `count > 0` gate emitted nothing here -- exactly the case
        that mattered (a total loss). The count is now labelled as a
        working-directory count and the action is to clear the directory.
        """
        mock_logger = MagicMock()
        with patch("vkdownloader.services.segment_downloader.logger", mock_logger):
            _log_preserve_segments(tmp_path)

        mock_logger.info.assert_called_once()
        call = mock_logger.info.call_args
        assert call.args[0] == "preserving_segments_for_resume"
        assert call.kwargs["working_dir"] == str(tmp_path)
        assert call.kwargs["working_dir_ts_count"] == 0
        assert "not a count of resumable segments" in call.kwargs["count_note"]
        assert "clear the working directory" in call.kwargs["next_action"]

    def test_count_includes_merge_temps_and_says_so(self, tmp_path: Path) -> None:
        """The count includes batch_*.ts temps and the record says so.

        This is the compensating control for the ART-004 deferral: the *.ts
        glob counts merge temps as well as segments, so the record carries an
        explicit note that the number is not a resumable-segment count.
        """
        (tmp_path / "00000.ts").write_bytes(b"seg")
        (tmp_path / "00001.ts").write_bytes(b"seg")
        (tmp_path / "batch_00000.ts").write_bytes(b"merged")

        mock_logger = MagicMock()
        with patch("vkdownloader.services.segment_downloader.logger", mock_logger):
            _log_preserve_segments(tmp_path)

        mock_logger.info.assert_called_once()
        call = mock_logger.info.call_args
        assert call.args[0] == "preserving_segments_for_resume"
        assert call.kwargs["working_dir_ts_count"] == 3
        assert "including any batch_*.ts" in call.kwargs["count_note"]
        assert "not a count of resumable segments" in call.kwargs["count_note"]
        assert "clear the working directory" in call.kwargs["next_action"]

    def test_missing_directory_emits_nothing(self, tmp_path: Path) -> None:
        """An absent segments directory is skipped, not logged as zero."""
        missing_dir = tmp_path / "does_not_exist"

        mock_logger = MagicMock()
        with patch("vkdownloader.services.segment_downloader.logger", mock_logger):
            _log_preserve_segments(missing_dir)

        mock_logger.info.assert_not_called()
