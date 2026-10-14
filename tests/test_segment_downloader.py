"""Tests for segment_downloader token-refresh retry logic."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import DownloadError
from vkdownloader.models.dtos import HLSDownloadRequest
from vkdownloader.models.enums import QualityLabel, StreamFormat
from vkdownloader.models.video import Stream
from vkdownloader.services.downloader_throttle import (
    URLBackoffCoordinator,
    _resource_key,
    _shutdown_event_ctx,
)
from vkdownloader.services.segment_downloader import (
    _REASON_CANCELLED,
    _REASON_SHUTDOWN,
    DownloadPolicy,
    PlaylistFetchResult,
    SegmentTask,
    _await_and_cancel,
    _check_download_space,
    _clear_stale_segments,
    _create_connector,
    _download_segment_sequential,
    _fetch_playlist_with_retry,
    _handle_token_refresh,
    _log_preserve_segments,
    _process_downloaded_segments,
    _SegmentFanoutOutcome,
    _tally_and_merge,
    download_hls_with_resume,
)
from vkdownloader.utils.url_sanitizer import _strip_auth_params

_VIDEO_URL = "https://vkvideo.ru/video-12345_67890"


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

        refresh_calls: list[str] = []
        fetch_urls: list[str] = []
        forwarded_quality: list[str] = []
        forwarded_preselected: list[str] = []

        async def fake_refresh(
            vid: str,
            extractor: MagicMock,
            settings: Settings,
            headers: dict[str, str],
            *,
            quality: str,
            preselected_url: str,
        ) -> tuple[str, str]:
            refresh_calls.append(vid)
            forwarded_quality.append(quality)
            forwarded_preselected.append(preselected_url)
            return refreshed_url, ""

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
                with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                    result = await _fetch_playlist_with_retry(
                        mock_session,
                        video_url,
                        m3u8_url,
                        headers,
                        mock_extractor,
                        test_settings,
                        max_retries=3,
                        quality="best",
                    )

        assert result is not None
        assert result.playlist_text == playlist
        assert result.base_url == refreshed_url
        assert refresh_calls == [video_url]
        assert fetch_urls == [m3u8_url, refreshed_url]
        assert headers.get("Cookie") == ""
        # Forced re-scope (B8): assert forwarded keywords by value.
        assert forwarded_quality == ["best"]
        assert forwarded_preselected == [m3u8_url]

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
            vid: str,
            extractor: MagicMock,
            settings: Settings,
            headers: dict[str, str],
            *,
            quality: str,
            preselected_url: str,
        ) -> tuple[str, str]:
            refresh_calls.append(object())
            return refreshed_url, ""

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
                with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                    result = await _fetch_playlist_with_retry(
                        mock_session,
                        video_url,
                        m3u8_url,
                        headers,
                        mock_extractor,
                        test_settings,
                        max_retries=3,
                        quality="best",
                    )

        assert result is not None
        assert result.playlist_text == playlist
        assert result.base_url == refreshed_url
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
            vid: str,
            extractor: MagicMock,
            settings: Settings,
            headers: dict[str, str],
            *,
            quality: str,
            preselected_url: str,
        ) -> tuple[str, str] | None:
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
                with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                    result = await _fetch_playlist_with_retry(
                        mock_session,
                        video_url,
                        m3u8_url,
                        headers,
                        mock_extractor,
                        test_settings,
                        max_retries=3,
                        quality="best",
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
            vid: str,
            extractor: MagicMock,
            settings: Settings,
            headers: dict[str, str],
            *,
            quality: str,
            preselected_url: str,
        ) -> tuple[str, str] | None:
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
                with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                    result = await _fetch_playlist_with_retry(
                        mock_session,
                        video_url,
                        m3u8_url,
                        headers,
                        None,
                        test_settings,
                        max_retries=3,
                        quality="best",
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
            vid: str,
            extractor: MagicMock,
            settings: Settings,
            headers: dict[str, str],
            *,
            quality: str,
            preselected_url: str,
        ) -> tuple[str, str] | None:
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
                with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                    result = await _fetch_playlist_with_retry(
                        mock_session,
                        video_url,
                        m3u8_url,
                        headers,
                        mock_extractor,
                        test_settings,
                        max_retries=3,
                        quality="best",
                    )

        assert result is None
        # Refresh was attempted once, but no second fetch occurred (fell through).
        assert len(refresh_calls) == 1
        assert fetch_count == 1


class TestSequentialSharesThePause:
    """Tests that _download_segment_sequential consults the shared backoff coordinator."""

    @pytest.mark.asyncio
    async def test_consults_backoff_coordinator_before_attempt(self, tmp_path: Path) -> None:
        """Sequential download checks wait_if_paused with the resource key."""
        segment_url = "https://cdn.example.com/seg1.ts"
        coordinator = URLBackoffCoordinator()
        coordinator.wait_if_paused = AsyncMock(wraps=coordinator.wait_if_paused)  # type: ignore[method-assign]

        with patch(
            "vkdownloader.services.segment_downloader._retry_429_with_backoff",
            return_value=b"segment-data",
        ):
            result = await _download_segment_sequential(
                MagicMock(),
                segment_url,
                tmp_path / "seg1.ts",
                {},
                backoff_coordinator=coordinator,
            )

        assert result is True
        coordinator.wait_if_paused.assert_awaited_once_with(segment_url)

    @pytest.mark.asyncio
    async def test_coordination_consulted_once_before_retry_internal(self, tmp_path: Path) -> None:
        """wait_if_paused is consulted once before _retry_429_with_backoff (which retries internally).

        D2: the outer for-loop was removed so the coordinator is consulted
        exactly once, not once-per-internal-retry.
        """
        segment_url = "https://cdn.example.com/seg1.ts"
        coordinator = URLBackoffCoordinator()
        coordinator.wait_if_paused = AsyncMock(wraps=coordinator.wait_if_paused)  # type: ignore[method-assign]

        with patch(
            "vkdownloader.services.segment_downloader._retry_429_with_backoff",
            return_value=b"segment-data",
        ):
            result = await _download_segment_sequential(
                MagicMock(),
                segment_url,
                tmp_path / "seg1.ts",
                {},
                max_retries=3,
                backoff_coordinator=coordinator,
            )

        assert result is True
        assert coordinator.wait_if_paused.await_count == 1


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


class TestTokenRefreshDoesNotMutateHeaders:
    """D3 (B4-era label): _handle_token_refresh must not mutate the caller's
    headers dict.

    Forced re-scope (B8): the stub now accepts the two new keyword-only
    parameters (``quality``, ``preselected_url``) and the test asserts their
    forwarded values by value, alongside the preserved B4 assertion that
    ``original_headers`` is unchanged.
    """

    @pytest.mark.asyncio
    async def test_headers_unchanged_after_refresh(self, test_settings: Settings) -> None:
        """The headers dict passed to _handle_token_refresh is not modified.

        _handle_token_refresh delegates to _refresh_token_and_retry (which does
        not accept or mutate headers), so the caller's dict must survive intact.

        Forced re-scope (B8): the stub accepts ``quality`` and
        ``preselected_url`` (keyword-only) and the test asserts both
        forwarded values by value, in addition to the preserved B4
        assertion that ``original_headers`` is unchanged.
        """
        video_url = "https://vkvideo.ru/video-12345_67890"
        original_headers = {"User-Agent": "test", "Cookie": "prior=value"}
        preselected_url = "https://example.com/preselected.m3u8"

        forwarded: dict[str, object] = {}

        async def fake_refresh_token_and_retry(
            vid: str,
            extractor: MagicMock,
            settings: Settings,
            *,
            quality: str,
            preselected_url: str,
        ) -> tuple[str, str]:
            forwarded["quality"] = quality
            forwarded["preselected_url"] = preselected_url
            return "https://refreshed.m3u8", "new=cookie"

        mock_extractor = MagicMock()

        with patch(
            "vkdownloader.services.segment_downloader._refresh_token_and_retry",
            side_effect=fake_refresh_token_and_retry,
        ):
            with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                result = await _handle_token_refresh(
                    video_url,
                    mock_extractor,
                    test_settings,
                    original_headers,
                    quality="best",
                    preselected_url=preselected_url,
                )

        assert result == ("https://refreshed.m3u8", "new=cookie")
        assert original_headers == {"User-Agent": "test", "Cookie": "prior=value"}
        # B8 forced re-scope: assert forwarded values by value.
        assert forwarded["quality"] == "best"
        assert forwarded["preselected_url"] == preselected_url


class TestSequentialIssuesAtMostMaxRetries:
    """D2: sequential strategy must issue at most max_retries HTTP requests."""

    @pytest.mark.asyncio
    async def test_at_most_max_retries_requests(self, tmp_path: Path) -> None:
        """_retry_429_with_backoff is called exactly once, not max_retries times."""
        segment_url = "https://cdn.example.com/seg1.ts"
        fetch_count = 0

        async def counting_retry(*args: object, **kwargs: object) -> bytes | None:
            nonlocal fetch_count
            fetch_count += 1
            return None

        with patch(
            "vkdownloader.services.segment_downloader._retry_429_with_backoff",
            side_effect=counting_retry,
        ):
            result = await _download_segment_sequential(
                MagicMock(),
                segment_url,
                tmp_path / "seg1.ts",
                {},
                max_retries=3,
            )

        assert result is False
        assert fetch_count == 1


class TestManifestRetryComputesBackoffDelay:
    """D1: _fetch_playlist_with_retry calls _compute_backoff_delay on retryable failures."""

    @pytest.mark.asyncio
    async def test_transport_failure_triggers_backoff_delay(self, test_settings: Settings) -> None:
        """A transport failure (None result) triggers _compute_backoff_delay + _wait_with_shutdown."""
        video_url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://example.com/playlist.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}

        async def fake_fetch(
            session: MagicMock, url: str, hdr: dict[str, str], timeout: object
        ) -> tuple[str, int] | None:
            return None  # Transport failure

        mock_session = MagicMock()
        mock_extractor = MagicMock()

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch(
                "vkdownloader.services.segment_downloader._compute_backoff_delay",
                return_value=0.0,
            ) as mock_delay,
            patch(
                "vkdownloader.services.segment_downloader._wait_with_shutdown",
                new_callable=AsyncMock,
                return_value=False,
            ) as mock_wait,
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await _fetch_playlist_with_retry(
                mock_session,
                video_url,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=3,
                quality="best",
            )

        assert result is None
        # Transport-failure branch: delay computed on each non-final attempt
        # _compute_backoff_delay is sync, so call_count (not await_count) is tracked.
        assert mock_delay.call_count == 2  # 2 retries after first attempt
        assert mock_wait.await_count == 2

    @pytest.mark.asyncio
    async def test_retryable_status_triggers_backoff_delay(self, test_settings: Settings) -> None:
        """A retryable HTTP status (429) triggers _compute_backoff_delay + _wait_with_shutdown."""
        video_url = "https://vkvideo.ru/video-12345_67890"
        m3u8_url = "https://example.com/playlist.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}

        async def fake_fetch(
            session: MagicMock, url: str, hdr: dict[str, str], timeout: object
        ) -> tuple[str, int] | None:
            return "", 429  # Retryable status

        mock_session = MagicMock()
        mock_extractor = MagicMock()

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch(
                "vkdownloader.services.segment_downloader._compute_backoff_delay",
                return_value=0.0,
            ) as mock_delay,
            patch(
                "vkdownloader.services.segment_downloader._wait_with_shutdown",
                new_callable=AsyncMock,
                return_value=False,
            ) as mock_wait,
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await _fetch_playlist_with_retry(
                mock_session,
                video_url,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=3,
                quality="best",
            )

        assert result is None
        assert mock_delay.call_count == 2  # 2 retries after first attempt
        assert mock_wait.await_count == 2
        # Verify delay was computed with the actual status code (429)
        assert mock_delay.call_args_list[0].args[0] == 429


class TestBackoffCoordinatorNormalizesInternally:
    """D4: URLBackoffCoordinator applies _resource_key internally, callers pass raw URLs."""

    @pytest.mark.asyncio
    async def test_pause_and_wait_same_origin_different_paths(self) -> None:
        """Pause on one path, wait on a different path of the same origin."""
        coordinator = URLBackoffCoordinator(pause_seconds=10.0)
        url_a = "https://user:pass@cdn.example.com/path1/seg.ts?token=abc"
        url_b = "https://cdn.example.com:8080/path2/seg.ts"

        # url_a and url_b have different origins (one has port 8080) вЂ” use same origin
        url_a = "https://user:pass@cdn.example.com/path1/seg.ts?token=abc"
        url_b = "https://cdn.example.com/path2/seg.ts"

        async def mock_wait_for(
            coro: Coroutine[object, object, object], timeout: float | None
        ) -> object:
            coro.close()
            raise TimeoutError()

        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for",
            side_effect=mock_wait_for,
        ):
            await coordinator.pause(url_a, coordinator.pause_seconds)
            result = await coordinator.wait_if_paused(url_b)

        assert result is True
        assert _resource_key(url_a) == _resource_key(url_b)

    @pytest.mark.asyncio
    async def test_no_external_key_needed(self) -> None:
        """Callers can pass the raw URL without pre-normalization."""
        coordinator = URLBackoffCoordinator(pause_seconds=10.0)
        raw_url = "https://user:pass@cdn.example.com:8080/path/seg.ts?token=abc"

        async def mock_wait_for(
            coro: Coroutine[object, object, object], timeout: float | None
        ) -> object:
            coro.close()
            raise TimeoutError()

        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for",
            side_effect=mock_wait_for,
        ):
            await coordinator.pause(raw_url, coordinator.pause_seconds)
            result = await coordinator.wait_if_paused(raw_url)

        assert result is True


class TestRefreshQualitySelection:
    """T1-T7: Quality selection on the token-refresh path (NET-005).

    Drives the real ``_fetch_playlist_with_retry`` / ``_handle_token_refresh``
    / ``_refresh_token_and_retry``, patching only ``extractor.extract_streams_with_cookies``
    and ``_fetch_single_playlist`` вЂ” so threading and both arms are exercised
    together rather than mocked around.

    New tag: D-15. Does not touch the pre-existing B4-era D1/D2/D3 labels in
    this file's older docstrings.
    """

    _VIDEO_URL = "https://vkvideo.ru/video-12345_67890"

    # ------------------------------------------------------------------ #
    #  T1 вЂ” best arm, two-element set, picks the higher stream           #
    #  (STUB-ONLY proof; production set is a singleton в†’ best is a noop)  #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_t1_best_quality_selects_second_element(self, test_settings: Settings) -> None:
        """T1: a best request over a two-element refreshed set resolves to the
        second element, proving the result is not element zero.

        STUB-ONLY proof (D3): ``_extract_with_browser`` appends **at most**
        one ``Stream``, so the production refreshed set is a singleton and
        the ``best`` arm is provably a no-op on it.  This stub injects two
        elements to exercise ``QualitySelector.select`` and prove it returns
        the higher stream rather than element zero.
        """
        m3u8_url = "https://example.com/initial.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}
        playlist = "#EXTM3U\nseg1.ts"

        stream_low = Stream(
            url="https://cdn.low.m3u8",
            format=StreamFormat.HLS,
            quality="360p",
            height=360,
        )
        stream_high = Stream(
            url="https://cdn.high.m3u8",
            format=StreamFormat.HLS,
            quality="1080p",
            height=1080,
        )

        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = AsyncMock(
            return_value=([stream_low, stream_high], "fresh_cookie", [])
        )

        fetch_count = 0

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            nonlocal fetch_count
            fetch_count += 1
            if fetch_count == 1:
                return "", 403
            return playlist, 200

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await _fetch_playlist_with_retry(
                MagicMock(),
                self._VIDEO_URL,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=2,
                quality="best",
            )

        assert result is not None
        # Best arm selected the higher stream (index 1), not element zero.
        assert result.base_url == stream_high.url
        assert result.base_url != stream_low.url

    # ------------------------------------------------------------------ #
    #  T2 вЂ” numeric request, singleton set, preselected address returned  #
    #  (production-shaped; falsifiable against today's unfixed code)      #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_t2_numeric_quality_returns_preselected(self, test_settings: Settings) -> None:
        """T2: a numeric request over a singleton refreshed set whose address
        differs from the preselected address returns the **preselected**
        address.

        Production-shaped, falsifiable-against-unfixed-code oracle (D1):
        unfixed code returns ``streams[0].url`` (the refreshed address that
        just failed); fixed code returns the ladder's ``m3u8_url``.
        """
        m3u8_url = "https://example.com/preselected.m3u8"
        refreshed_url = "https://cdn.refreshed.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}
        playlist = "#EXTM3U\nseg1.ts"

        stream = Stream(
            url=refreshed_url,
            format=StreamFormat.HLS,
            quality="1080p",
            height=1080,
        )

        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = AsyncMock(
            return_value=([stream], "fresh_cookie", [])
        )

        fetch_count = 0

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            nonlocal fetch_count
            fetch_count += 1
            if fetch_count == 1:
                return "", 403
            return playlist, 200

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await _fetch_playlist_with_retry(
                MagicMock(),
                self._VIDEO_URL,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=2,
                quality="720",
            )

        assert result is not None
        assert result.base_url == m3u8_url
        assert result.base_url != refreshed_url

    # ------------------------------------------------------------------ #
    #  T3 вЂ” worst request, singleton set, preselected address returned    #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_t3_worst_quality_returns_preselected(self, test_settings: Settings) -> None:
        """T3: a worst request returns the preselected address (same oracle as T2)."""
        m3u8_url = "https://example.com/preselected.m3u8"
        refreshed_url = "https://cdn.refreshed.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}
        playlist = "#EXTM3U\nseg1.ts"

        stream = Stream(
            url=refreshed_url,
            format=StreamFormat.HLS,
            quality="1080p",
            height=1080,
        )

        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = AsyncMock(
            return_value=([stream], "fresh_cookie", [])
        )

        fetch_count = 0

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            nonlocal fetch_count
            fetch_count += 1
            if fetch_count == 1:
                return "", 403
            return playlist, 200

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await _fetch_playlist_with_retry(
                MagicMock(),
                self._VIDEO_URL,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=2,
                quality="worst",
            )

        assert result is not None
        assert result.base_url == m3u8_url
        assert result.base_url != refreshed_url

    # ------------------------------------------------------------------ #
    #  T4 вЂ” out-of-enum quality, singleton set, preselected returned      #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_t4_out_of_enum_quality_returns_preselected(
        self, test_settings: Settings
    ) -> None:
        """T4: a quality value outside the enumeration (e.g. ``"999"``) returns
        the preselected address вЂ” no ``QualityParseError``, no ``except ValueError``.
        """
        m3u8_url = "https://example.com/preselected.m3u8"
        refreshed_url = "https://cdn.refreshed.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}
        playlist = "#EXTM3U\nseg1.ts"

        stream = Stream(
            url=refreshed_url,
            format=StreamFormat.HLS,
            quality="1080p",
            height=1080,
        )

        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = AsyncMock(
            return_value=([stream], "fresh_cookie", [])
        )

        fetch_count = 0

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            nonlocal fetch_count
            fetch_count += 1
            if fetch_count == 1:
                return "", 403
            return playlist, 200

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await _fetch_playlist_with_retry(
                MagicMock(),
                self._VIDEO_URL,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=2,
                quality="999",
            )

        assert result is not None
        assert result.base_url == m3u8_url
        assert result.base_url != refreshed_url

    # ------------------------------------------------------------------ #
    #  T5 вЂ” two-refresh sequence, non-best arm, budget exhausted          #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_t5_two_refresh_non_best_exhausts_budget(self, test_settings: Settings) -> None:
        """T5: two-refresh sequence (403 в†’ refresh в†’ 403 в†’ refresh) for the
        **non-best** arm with ``max_retries=2`` (explicit вЂ” not from
        ``test_settings`` which carries ``max_retries=1``).

        Asserts:
        - extractor awaited exactly twice with ``(video_url, force_browser=True)``
        - both fetch URLs are the **preselected** address (provably NOT the
          stub's refreshed URL)
        - cookie written on both refreshes (cookie1 seen on the second fetch;
          cookie2 in final ``headers``)
        - final result ``None`` (budget exhausted)
        - two ``stream_quality_selected`` records, each naming the preselected
          address

        This is the sequence the D1 decision changes вЂ” a test that merely
        counts extractor calls is worthless because today's unfixed code
        would pass it.
        """
        m3u8_url = "https://example.com/preselected.m3u8"
        refreshed_url = "https://cdn.refreshed.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}

        stream = Stream(
            url=refreshed_url,
            format=StreamFormat.HLS,
            quality="1080p",
            height=1080,
        )

        extract_mock = AsyncMock(
            side_effect=[
                ([stream], "cookie1", []),
                ([stream], "cookie2", []),
            ]
        )
        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = extract_mock

        fetch_calls: list[tuple[str, dict[str, str]]] = []

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            fetch_calls.append((url, dict(hdr)))
            return "", 403

        mock_logger = MagicMock()

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch("vkdownloader.services.segment_downloader.logger", mock_logger),
        ):
            result = await _fetch_playlist_with_retry(
                MagicMock(),
                self._VIDEO_URL,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=2,
                quality="720",
            )

        assert result is None

        # Extractor awaited exactly twice with (video_url, force_browser=True).
        assert extract_mock.await_count == 2
        for c in extract_mock.await_args_list:
            assert c.args[0] == self._VIDEO_URL
            assert c.kwargs["force_browser"] is True

        # Both fetches re-requested the preselected address вЂ” NOT the stub's
        # refreshed URL.  This is the D1 decision: unfixed code would have
        # re-requested the failed current_url (the 403 address).
        fetch_urls = [fc[0] for fc in fetch_calls]
        assert fetch_urls == [m3u8_url, m3u8_url]
        assert refreshed_url not in fetch_urls

        # Cookie written on both refreshes.
        assert fetch_calls[0][1].get("Cookie") is None  # before first refresh
        assert fetch_calls[1][1]["Cookie"] == "cookie1"  # from refresh #1
        assert headers["Cookie"] == "cookie2"  # from refresh #2

        # Two selection records, each naming the re-requested address.
        selection_records = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and c.args[0] == "stream_quality_selected"
        ]
        assert len(selection_records) == 2
        expected_url = _strip_auth_params(m3u8_url)
        for rec in selection_records:
            assert rec.kwargs["url"] == expected_url
            assert rec.kwargs["selected_from"] == "preselected"
            assert rec.kwargs["quality"] == QualityLabel.UNKNOWN.value
            assert rec.kwargs["height"] is None
            assert rec.kwargs["width"] is None

    # ------------------------------------------------------------------ #
    #  T6 вЂ” two-refresh sequence, best arm, budget exhausted              #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_t6_two_refresh_best_exhausts_budget(self, test_settings: Settings) -> None:
        """T6: two-refresh sequence (403 в†’ refresh в†’ 403 в†’ refresh) for the
        **best** arm with ``max_retries=2`` (explicit вЂ” not from
        ``test_settings`` which carries ``max_retries=1``).

        Asserts:
        - extractor awaited exactly twice with ``(video_url, force_browser=True)``
        - first fetch to the preselected (initial) address; second fetch to
          the **selector's** address (the refreshed stream)
        - cookie written on both refreshes
        - final result ``None`` (budget exhausted)
        - two ``stream_quality_selected`` records, each naming the selector's
          address with ``selected_from="refreshed_stream_set"``
        """
        m3u8_url = "https://example.com/preselected.m3u8"
        refreshed_url = "https://cdn.refreshed.m3u8"
        headers: dict[str, str] = {"User-Agent": "test"}

        stream = Stream(
            url=refreshed_url,
            format=StreamFormat.HLS,
            quality="1080p",
            height=1080,
        )

        extract_mock = AsyncMock(
            side_effect=[
                ([stream], "cookie1", []),
                ([stream], "cookie2", []),
            ]
        )
        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = extract_mock

        fetch_calls: list[tuple[str, dict[str, str]]] = []

        async def fake_fetch(
            session: MagicMock,
            url: str,
            hdr: dict[str, str],
            timeout: object,
        ) -> tuple[str, int] | None:
            fetch_calls.append((url, dict(hdr)))
            return "", 403

        mock_logger = MagicMock()

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_single_playlist",
                side_effect=fake_fetch,
            ),
            patch("vkdownloader.services.segment_downloader.logger", mock_logger),
        ):
            result = await _fetch_playlist_with_retry(
                MagicMock(),
                self._VIDEO_URL,
                m3u8_url,
                headers,
                mock_extractor,
                test_settings,
                max_retries=2,
                quality="best",
            )

        assert result is None

        # Extractor awaited exactly twice with (video_url, force_browser=True).
        assert extract_mock.await_count == 2
        for c in extract_mock.await_args_list:
            assert c.args[0] == self._VIDEO_URL
            assert c.kwargs["force_browser"] is True

        # First fetch to the initial preselected URL; second fetch to the
        # selector's address (the refreshed stream's URL).
        fetch_urls = [fc[0] for fc in fetch_calls]
        assert fetch_urls == [m3u8_url, refreshed_url]

        # Cookie written on both refreshes.
        assert fetch_calls[0][1].get("Cookie") is None
        assert fetch_calls[1][1]["Cookie"] == "cookie1"
        assert headers["Cookie"] == "cookie2"

        # Two selection records, each naming the selector's address.
        selection_records = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and c.args[0] == "stream_quality_selected"
        ]
        assert len(selection_records) == 2
        expected_url = _strip_auth_params(refreshed_url)
        for rec in selection_records:
            assert rec.kwargs["url"] == expected_url
            assert rec.kwargs["selected_from"] == "refreshed_stream_set"
            assert rec.kwargs["quality"] == QualityLabel.UNKNOWN.value
            assert rec.kwargs["height"] is None
            assert rec.kwargs["width"] is None

    # ------------------------------------------------------------------ #
    #  T7 вЂ” threading proof via download_hls_with_resume                 #
    # ------------------------------------------------------------------ #

    @pytest.mark.asyncio
    async def test_t7_quality_threaded_from_request(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """T7: threading proof вЂ” ``download_hls_with_resume`` forwards
        ``request.quality`` through ``_run_download_session`` to
        ``_fetch_playlist_with_retry``.

        ``_fetch_playlist_with_retry`` is replaced by a spy that records its
        keyword arguments.  The spy asserts it received ``quality == "720"``
        and the request's ``m3u8_url`` as its 3rd positional argument.

        Without this test the threading could be deleted and every other test
        would still pass вЂ” the others stub ``_handle_token_refresh`` or
        ``_fetch_playlist_with_retry`` with a static return value.
        """
        output_file = tmp_path / "video.mp4"

        spy = AsyncMock(
            return_value=PlaylistFetchResult(
                playlist_text="", base_url="https://example.com/playlist.m3u8"
            )
        )

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                spy,
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await download_hls_with_resume(
                HLSDownloadRequest(
                    video_url="https://vkvideo.ru/video-12345_67890",
                    m3u8_url="https://example.com/video.m3u8",
                    output_file=output_file,
                    quality="720",
                ),
                settings=test_settings,
            )

        assert result is None
        # Spy received quality="720" as a keyword argument.
        assert spy.call_args.kwargs["quality"] == "720"
        # And the request's m3u8_url as the 3rd positional argument.
        assert spy.call_args.args[2] == "https://example.com/video.m3u8"


class TestTreeLifetime:
    """P12-B7 (ART-005 lifetime): the segments working directory lives only while
    the merge needs it.

    The tree is created inside ``_run_download_session`` after the playlist is
    parsed, and every non-success exit removes it via ``_cleanup_segments`` in
    ``download_hls_with_resume``'s finally block. These oracles drive the full
    ``download_hls_with_resume`` entry point with ``_fetch_playlist_with_retry``
    and ``_process_downloaded_segments`` mocked, asserting the file-system side
    effect rather than the return value.
    """

    _PLAYLIST = "#EXTM3U\nseg1.ts"

    def _request(self, output_file: Path) -> HLSDownloadRequest:
        return HLSDownloadRequest(
            video_url="https://vkvideo.ru/video-12345_67890",
            m3u8_url="https://example.com/video.m3u8",
            output_file=output_file,
            quality="best",
        )

    @staticmethod
    def _segments_dir(output_file: Path) -> Path:
        return output_file.parent / f".{output_file.stem}_segments"

    @pytest.mark.asyncio
    async def test_no_tree_before_playlist_parsed(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """No working directory exists when the playlist fetch fails.

        P12-B7: the tree is created only after the playlist is parsed, so a None
        result from ``_fetch_playlist_with_retry`` must leave no directory behind.
        This is the strongest oracle — it fails if the mkdir stayed in
        ``download_hls_with_resume`` (i.e. before the fetch).
        """
        output_file = tmp_path / "video.mp4"
        segments_dir = self._segments_dir(output_file)

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                AsyncMock(return_value=None),
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await download_hls_with_resume(
                self._request(output_file),
                settings=test_settings,
            )

        assert result is None
        assert not segments_dir.exists()

    @pytest.mark.asyncio
    async def test_tree_removed_after_failed_session(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Tree is cleaned up when the session returns None (no merge produced).

        ``_process_downloaded_segments`` returning None is a non-success exit;
        the finally block must remove the working directory it just created.
        """
        output_file = tmp_path / "video.mp4"
        segments_dir = self._segments_dir(output_file)

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                AsyncMock(
                    return_value=PlaylistFetchResult(
                        playlist_text=self._PLAYLIST,
                        base_url="https://example.com/playlist.m3u8",
                    )
                ),
            ),
            patch(
                "vkdownloader.services.segment_downloader._process_downloaded_segments",
                AsyncMock(return_value=None),
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            result = await download_hls_with_resume(
                self._request(output_file),
                settings=test_settings,
            )

        assert result is None
        assert not segments_dir.exists()

    @pytest.mark.asyncio
    async def test_tree_removed_after_merge_failure(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Tree is cleaned up when ``_process_downloaded_segments`` raises.

        A ``RuntimeError`` propagates to the caller AND the finally block must
        still remove the working directory it just created.
        """
        output_file = tmp_path / "video.mp4"
        segments_dir = self._segments_dir(output_file)

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                AsyncMock(
                    return_value=PlaylistFetchResult(
                        playlist_text=self._PLAYLIST,
                        base_url="https://example.com/playlist.m3u8",
                    )
                ),
            ),
            patch(
                "vkdownloader.services.segment_downloader._process_downloaded_segments",
                AsyncMock(side_effect=RuntimeError("merge failed")),
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            with pytest.raises(RuntimeError, match="merge failed"):
                await download_hls_with_resume(
                    self._request(output_file),
                    settings=test_settings,
                )

        assert not segments_dir.exists()

    @pytest.mark.asyncio
    async def test_tree_removed_after_file_not_found(
        self, test_settings: Settings, tmp_path: Path
    ) -> None:
        """Tree is cleaned up when ``_process_downloaded_segments`` raises
        ``FileNotFoundError`` (the merge's existence check failing on a missing
        segment file).

        A ``FileNotFoundError`` propagates to the caller AND the finally block
        must still remove the working directory it just created.
        """
        output_file = tmp_path / "video.mp4"
        segments_dir = self._segments_dir(output_file)

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                AsyncMock(
                    return_value=PlaylistFetchResult(
                        playlist_text=self._PLAYLIST,
                        base_url="https://example.com/playlist.m3u8",
                    )
                ),
            ),
            patch(
                "vkdownloader.services.segment_downloader._process_downloaded_segments",
                AsyncMock(side_effect=FileNotFoundError("missing segment")),
            ),
            patch("vkdownloader.services.segment_downloader.logger", MagicMock()),
        ):
            with pytest.raises(FileNotFoundError, match="missing segment"):
                await download_hls_with_resume(
                    self._request(output_file),
                    settings=test_settings,
                )

        assert not segments_dir.exists()


class TestSegmentFanoutCompletion:
    """CON-006 + CON-007 + CON-008, enforced by phase04/VAL-402.

    Verifies _await_and_cancel distinguishes three fates at the type level:
    NOTHING_TO_DO (empty task list), COMPLETED (all settled), and
    cancellation (re-raised CancelledError with the correct reason logged).
    """

    @pytest.mark.asyncio
    async def test_nothing_to_do_returns_empty_result(self) -> None:
        """An empty task list yields the NOTHING_TO_DO outcome with empty results.

        Pre-fix code returned None here, so ``result.outcome`` would raise
        AttributeError instead of returning the typed outcome.
        """
        try:
            result = await asyncio.wait_for(
                _await_and_cancel([]),
                timeout=5.0,
            )
        except TimeoutError:
            pytest.fail("_await_and_cancel did not return within 5.0s for empty task list")

        assert result.outcome is _SegmentFanoutOutcome.NOTHING_TO_DO
        assert result.results == []

    @pytest.mark.asyncio
    async def test_raising_part_settles_siblings_before_propagating(self) -> None:
        """A non-cancellation exception from one task must settle every sibling
        before the exception is re-raised (CON-007).

        Pre-fix code only caught CancelledError, so a ValueError would escape
        without cancelling pending siblings вЂ” leaving an orphaned task.
        """
        started = asyncio.Event()
        never_set = asyncio.Event()
        # Sibling permit: starts at 1, the sibling acquires it (0), and
        # _await_and_cancel must release it back to 1 when it settles the
        # sibling before re-raising. Value 1 is the initial state.
        sibling_permit = asyncio.Semaphore(1)

        async def crashing_task() -> tuple[int, bool]:
            await started.wait()
            raise ValueError("segment download crashed")

        async def long_running_task() -> tuple[int, bool]:
            await started.wait()
            await sibling_permit.acquire()
            try:
                await never_set.wait()
            finally:
                sibling_permit.release()
            return (1, True)

        task1 = asyncio.create_task(crashing_task())
        task2 = asyncio.create_task(long_running_task())

        # Signal both tasks to start; task2 will block on never_set.
        started.set()
        await asyncio.sleep(0)

        # Assert the permit is held by the sibling before the raise.
        assert sibling_permit._value == 0

        try:
            with patch(
                "vkdownloader.services.segment_downloader.logger.info",
                side_effect=lambda *a, **kw: None,
            ):
                with pytest.raises(ValueError, match="segment download crashed"):
                    await asyncio.wait_for(
                        _await_and_cancel([task1, task2]),
                        timeout=5.0,
                    )
        except TimeoutError:
            pytest.fail("_await_and_cancel did not settle siblings within 5.0s")

        assert task1.done()
        assert task2.done()
        # No orphaned tasks remain after the exception propagates.
        leftover = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        assert leftover == []
        # Sibling permit returned to initial state after settlement.
        assert sibling_permit._value == 1, (
            "sibling permit must be released when the sibling is cancelled"
        )
        assert task2.done()

    @pytest.mark.asyncio
    async def test_cancelled_propagates_with_plain_cancelled_reason(self) -> None:
        """A CancelledError from a child task propagates and logs reason='cancelled'
        when the shutdown event is NOT set (CON-008).

        Pre-fix code always logged 'shutdown_requested' and swallowed the
        CancelledError (returned None instead of re-raising).
        """

        async def raises_cancelled() -> tuple[int, bool]:
            raise asyncio.CancelledError("cancelled by caller")

        task = asyncio.create_task(raises_cancelled())

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            captured: list[tuple[str, dict[str, object]]] = []

            def capture_info(event: str, **kwargs: object) -> None:
                captured.append((event, dict(kwargs)))

            try:
                with patch(
                    "vkdownloader.services.segment_downloader.logger.info",
                    side_effect=capture_info,
                ):
                    with pytest.raises(asyncio.CancelledError):
                        await asyncio.wait_for(
                            _await_and_cancel([task]),
                            timeout=5.0,
                        )
            except TimeoutError:
                pytest.fail("_await_and_cancel did not re-raise CancelledError within 5.0s")

            assert task.done()

            cancelled_events = [c for c in captured if c[0] == "download_cancelled"]
            assert len(cancelled_events) == 1
            assert cancelled_events[0][1].get("reason") == _REASON_CANCELLED
        finally:
            _shutdown_event_ctx.reset(token)

    @pytest.mark.asyncio
    async def test_cancelled_logs_shutdown_reason_when_stop_state_set(self) -> None:
        """A CancelledError from a child task logs reason='shutdown_requested'
        when the shutdown event IS set, and the CancelledError still propagates.

        This distinguishes a user-initiated stop from a plain cancellation:
        the reason field is driven by the actual stop state, not a constant.
        """

        async def raises_cancelled() -> tuple[int, bool]:
            raise asyncio.CancelledError("cancelled by caller")

        task = asyncio.create_task(raises_cancelled())

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()
            captured: list[tuple[str, dict[str, object]]] = []

            def capture_info(event: str, **kwargs: object) -> None:
                captured.append((event, dict(kwargs)))

            try:
                with patch(
                    "vkdownloader.services.segment_downloader.logger.info",
                    side_effect=capture_info,
                ):
                    with pytest.raises(asyncio.CancelledError):
                        await asyncio.wait_for(
                            _await_and_cancel([task]),
                            timeout=5.0,
                        )
            except TimeoutError:
                pytest.fail("_await_and_cancel did not re-raise CancelledError within 5.0s")

            assert task.done()

            cancelled_events = [c for c in captured if c[0] == "download_cancelled"]
            assert len(cancelled_events) == 1
            assert cancelled_events[0][1].get("reason") == _REASON_SHUTDOWN
        finally:
            _shutdown_event_ctx.reset(token)


class TestSegmentFanoutBoundedProduction:
    """CON-003: _process_downloaded_segments bounds the live task set by max_concurrent_segments.

    Four tests cover:
      1. Bound check — live pending never exceeds the ceiling.
      2. No work dropped — every segment index reaches the merge.
      3. Stop leaves no orphans — CancelledError propagates, semaphore is clean.
      4. NOTHING_TO_DO still typed — pre-existing segments reach the merge path.
    """

    @staticmethod
    def _make_policy(tmp_path: Path) -> DownloadPolicy:
        """Build a DownloadPolicy suitable for stubbing _download_segment_concurrent."""
        session = MagicMock()
        semaphore = asyncio.Semaphore(4)
        return DownloadPolicy(
            session=session,
            semaphore=semaphore,
            headers={},
            max_concurrent_segments=4,
            backoff_coordinator=None,
            video_url="https://vkvideo.ru/video-12345_67890",
            max_retries=3,
            download_timeout=300,
            m3u8_url="",
            segments_dir=tmp_path,
        )

    @pytest.mark.asyncio
    async def test_bound_check_live_pending_never_exceeds_ceiling(self, tmp_path: Path) -> None:
        """The FIRST_COMPLETED pump must keep live concurrent calls <= max_concurrent_segments.

        A stubbed ``_download_segment_concurrent`` tracks an active-call counter
        and records the maximum observed value. The ceiling (4) must never be
        exceeded.
        """
        active: list[int] = [0]
        max_live: list[int] = [0]

        async def stub(task: SegmentTask, policy: DownloadPolicy) -> tuple[int, bool]:
            active[0] += 1
            if active[0] > max_live[0]:
                max_live[0] = active[0]
            try:
                await asyncio.sleep(0)
            finally:
                active[0] -= 1
            return task.idx, True

        policy = self._make_policy(tmp_path)
        segments: list[str] = [f"https://example.com/seg{i}.ts" for i in range(200)]

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with patch(
                "vkdownloader.services.segment_downloader._download_segment_concurrent",
                side_effect=stub,
            ):
                await asyncio.wait_for(
                    _process_downloaded_segments(segments, policy, tmp_path / "out.mp4", None),
                    timeout=30.0,
                )
        finally:
            _shutdown_event_ctx.reset(token)

        assert max_live[0] <= 4, f"Live task set exceeded ceiling: {max_live[0]}"

    @pytest.mark.asyncio
    async def test_no_work_dropped_all_indices_reach_merge(self, tmp_path: Path) -> None:
        """All 200 segment indices must appear in the results passed to _tally_and_merge.

        Patches ``_tally_and_merge`` to capture its ``download_results`` argument
        and assert that every index 0..199 is present (sorted, no gaps).
        """
        policy = self._make_policy(tmp_path)
        segments: list[str] = [f"https://example.com/seg{i}.ts" for i in range(200)]

        async def stub(task: SegmentTask, policy: DownloadPolicy) -> tuple[int, bool]:
            await asyncio.sleep(0)
            return task.idx, True

        captured_results: list[tuple[int, bool]] = []

        async def fake_tally(
            download_results: list[tuple[int, bool]],
            segments_list: list[str],
            segments_dir: Path,
            output_file: Path,
            progress_callback: Callable[[str, int, int], None] | None,
            video_url: str,
        ) -> Path | None:
            captured_results.extend(download_results)
            return None  # Don't actually merge

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with (
                patch(
                    "vkdownloader.services.segment_downloader._download_segment_concurrent",
                    side_effect=stub,
                ),
                patch(
                    "vkdownloader.services.segment_downloader._tally_and_merge",
                    side_effect=fake_tally,
                ),
            ):
                await asyncio.wait_for(
                    _process_downloaded_segments(segments, policy, tmp_path / "out.mp4", None),
                    timeout=30.0,
                )
        finally:
            _shutdown_event_ctx.reset(token)

        assert len(captured_results) == 200
        indices = [r[0] for r in sorted(captured_results)]
        assert indices == list(range(200)), f"Missing indices: {set(range(200)) - set(indices)}"

    @pytest.mark.asyncio
    async def test_stop_leaves_no_orphans(self, tmp_path: Path) -> None:
        """When the task is cancelled mid-flight, CancelledError propagates and the semaphore is clean.

        The stub raises ``asyncio.CancelledError`` on the first call. We assert:
        - ``_process_downloaded_segments`` propagates the CancelledError.
        - After propagation, the semaphore's internal value matches its initial
          ``max_concurrent_segments`` (no leaked permits).
        """
        policy = self._make_policy(tmp_path)
        segments: list[str] = [f"https://example.com/seg{i}.ts" for i in range(20)]
        semaphore = policy.semaphore

        call_count: list[int] = [0]

        async def stub(task: SegmentTask, policy: DownloadPolicy) -> tuple[int, bool]:
            call_count[0] += 1
            raise asyncio.CancelledError("simulated stop")

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with patch(
                "vkdownloader.services.segment_downloader._download_segment_concurrent",
                side_effect=stub,
            ):
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(
                        _process_downloaded_segments(segments, policy, tmp_path / "out.mp4", None),
                        timeout=10.0,
                    )
        finally:
            _shutdown_event_ctx.reset(token)

        assert call_count[0] >= 1
        assert semaphore._value == policy.max_concurrent_segments, (
            f"Semaphore leaked permits: {semaphore._value} (expected {policy.max_concurrent_segments})"
        )

    @pytest.mark.asyncio
    async def test_nothing_to_do_is_typed_not_none(self, tmp_path: Path) -> None:
        """When all segment files already exist, the outcome is NOTHING_TO_DO, not None.

        Pre-creates all .ts files with non-zero size so ``_iter_pending_segment_tasks``
        yields nothing. Asserts the final return is None (no merge needed) AND
        that the fanout result reached ``_tally_and_merge`` with an empty results
        list and NOTHING_TO_DO outcome — by capturing the call.
        """
        num_segments = 3
        segments: list[str] = [f"https://example.com/seg{i}.ts" for i in range(num_segments)]

        # Pre-create all segment files so _iter_pending_segment_tasks yields nothing
        for i in range(num_segments):
            seg_path = tmp_path / f"{i:05d}.ts"
            seg_path.write_bytes(b"existing-segment-data")

        policy = self._make_policy(tmp_path)

        captured: dict[str, object] = {}

        async def fake_tally(
            download_results: list[tuple[int, bool]],
            segments_list: list[str],
            segments_dir: Path,
            output_file: Path,
            progress_callback: Callable[[str, int, int], None] | None,
            video_url: str,
        ) -> Path | None:
            captured["results"] = download_results
            return None

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with patch(
                "vkdownloader.services.segment_downloader._tally_and_merge",
                side_effect=fake_tally,
            ):
                result = await asyncio.wait_for(
                    _process_downloaded_segments(segments, policy, tmp_path / "out.mp4", None),
                    timeout=10.0,
                )
        finally:
            _shutdown_event_ctx.reset(token)

        assert result is None
        assert captured["results"] == []


class TestConnectorCeilingsFollowTheSetting:
    """CON-009: both connector ceilings derive from max_concurrent_downloads.

    Two tests cover:
      1. limit follows the setting across the declared range x both ssl_verify values.
      2. the aggregate arithmetic the commit body claims cannot drift from the code.
    """

    @pytest.mark.parametrize("ssl_verify", [True, False])
    @pytest.mark.parametrize("max_concurrent_downloads", [1, 4, 16])
    @pytest.mark.asyncio
    async def test_both_ceilings_follow_the_setting(
        self, max_concurrent_downloads: int, ssl_verify: bool
    ) -> None:
        settings = Settings(
            max_concurrent_downloads=max_concurrent_downloads,
            ssl_verify=ssl_verify,
        )
        connector = _create_connector(settings, _VIDEO_URL)
        try:
            # equality to the PARAMETER, never to a constant: asserting limit == 10
            # would encode CON-009 rather than fix it.
            assert connector.limit == max_concurrent_downloads, (
                f"connector.limit should equal max_concurrent_downloads="
                f"{max_concurrent_downloads}, got {connector.limit}"
            )
            assert connector.limit_per_host == max_concurrent_downloads, (
                f"connector.limit_per_host should equal max_concurrent_downloads="
                f"{max_concurrent_downloads}, got {connector.limit_per_host}"
            )
            # the per-origin term can never be the binding one, stated structurally
            # so the assertion does not depend on aiohttp internals.
            assert connector.limit_per_host >= connector.limit, (
                f"limit_per_host ({connector.limit_per_host}) must be >= "
                f"limit ({connector.limit}) so the per-origin term is never "
                "the binding one"
            )
        finally:
            await connector.close()

    @pytest.mark.asyncio
    async def test_aggregate_matches_the_claimed_arithmetic(self) -> None:
        """N connectors, one per in-flight download: the aggregate is N x min(limit, per_host)."""
        for videos_in_flight, claimed in ((4, 16), (16, 256)):
            connectors: list[aiohttp.TCPConnector] = []
            try:
                for _ in range(videos_in_flight):
                    settings = Settings(max_concurrent_downloads=videos_in_flight)
                    connectors.append(_create_connector(settings, _VIDEO_URL))
                one = connectors[0]
                aggregate = sum(c.limit for c in connectors)
                assert aggregate == videos_in_flight * min(one.limit, one.limit_per_host), (
                    f"aggregate {aggregate} != {videos_in_flight} * "
                    f"min({one.limit}, {one.limit_per_host})"
                )
                assert aggregate == claimed, (
                    f"aggregate {aggregate} != claimed {claimed} "
                    f"for videos_in_flight={videos_in_flight}"
                )
                # both deltas, pinned in OPPOSITE directions:
                #   40 -> 16 at N=4 (falls), 160 -> 256 at N=16 (rises)
            finally:
                for connector in connectors:
                    await connector.close()


class TestSweepExclusion:
    """ART-004: batch_*.ts excluded from merge-decision count; ART-013: .ts.tmp swept."""

    @pytest.mark.asyncio
    async def test_tally_excludes_batch_temps_and_reaches_merge(self, tmp_path: Path) -> None:
        """Without the batch_*.ts exclusion the count would be 3, not 2, so
        3 != len(segments) and the merge would be skipped. With the exclusion
        count = 2 == len(segments) and _merge_segments_batched is invoked.
        """
        segments_dir = tmp_path / ".segments"
        segments_dir.mkdir()
        (segments_dir / "00000.ts").write_bytes(b"seg0")
        (segments_dir / "00001.ts").write_bytes(b"seg1")
        (segments_dir / "batch_00000.ts").write_bytes(b"merged")

        fake_output = tmp_path / "output.mp4"
        segments = ["seg1.ts", "seg2.ts"]

        with (
            patch(
                "vkdownloader.services.segment_downloader.logger",
                MagicMock(),
            ),
            patch(
                "vkdownloader.services.segment_downloader._merge_segments_batched",
                new_callable=AsyncMock,
                return_value=fake_output,
            ) as mock_merge,
        ):
            result = await _tally_and_merge(
                download_results=[],
                segments=segments,
                segments_dir=segments_dir,
                output_file=fake_output,
                progress_callback=None,
                video_url="https://vkvideo.ru/video-12345_67890",
            )

        assert result == fake_output
        mock_merge.assert_awaited_once_with(segments_dir, fake_output, len(segments))

    def test_ts_tmp_cleaned_by_stale_sweep(self, tmp_path: Path) -> None:
        """ART-013: .ts.tmp residue is removed alongside .ts files in the stale sweep.

        A stale signature triggers the clearing branch: both *.ts and *.ts.tmp
        files are unlinked before downloading the current playlist's segments.
        """
        segments_dir = tmp_path / ".segments"
        segments_dir.mkdir()
        (segments_dir / "00000.ts").write_bytes(b"old segment")
        (segments_dir / "00001.ts.tmp").write_bytes(b"partial write")
        (segments_dir / "batch_00000.ts.tmp").write_bytes(b"partial batch")

        # Stale signature so the clearing path runs.
        (segments_dir / ".signature").write_text("stale-signature")

        with patch(
            "vkdownloader.services.segment_downloader.logger",
            MagicMock(),
        ):
            _clear_stale_segments(
                segments_dir,
                ["https://example.com/seg1.ts", "https://example.com/seg2.ts"],
            )

        assert not (segments_dir / "00000.ts").exists()
        assert not (segments_dir / "00001.ts.tmp").exists()
        assert not (segments_dir / "batch_00000.ts.tmp").exists()


class TestDownloadSpaceProbe:
    """P12-B8 (ART-012): the download stage probes free space before the fan-out.

    The probe mirrors _check_merge_space's shape: it raises DownloadError when
    the estimated demand exceeds free space, and treats an unreadable mount
    as neither full nor empty -- it logs and proceeds.

    The demand figure is segment_count x a per-segment budget
    (_DOWNLOAD_SEGMENT_BUDGET_BYTES). The budget is 2 MB, a conservative
    lower-bound estimate; actual segment sizes vary with bitrate and duration.
    """

    from vkdownloader.services.segment_downloader import (
        _DOWNLOAD_SEGMENT_BUDGET_BYTES,
    )

    def test_sufficient_space_proceeds(self, tmp_path: Path) -> None:
        """Free space above the estimate does not raise."""
        with patch(
            "vkdownloader.services.segment_downloader.shutil.disk_usage",
            return_value=_fake_disk_usage(self._DOWNLOAD_SEGMENT_BUDGET_BYTES * 100),
        ):
            _check_download_space(10, tmp_path)

    def test_insufficient_space_raises_before_fanout(self, tmp_path: Path) -> None:
        """A volume too small to hold the estimate raises DownloadError."""
        available = 1
        with patch(
            "vkdownloader.services.segment_downloader.shutil.disk_usage",
            return_value=_fake_disk_usage(available),
        ):
            with pytest.raises(DownloadError) as exc_info:
                _check_download_space(10, tmp_path)

        message = str(exc_info.value)
        expected_required = 10 * self._DOWNLOAD_SEGMENT_BUDGET_BYTES
        assert str(expected_required) in message
        assert str(available) in message
        assert "lower quality" in message

    def test_unreadable_volume_proceeds_with_download(self, tmp_path: Path) -> None:
        """A volume whose usage cannot be read does not block the download."""
        with (
            patch(
                "vkdownloader.services.segment_downloader.shutil.disk_usage",
                side_effect=OSError("unreadable mount"),
            ),
            patch(
                "vkdownloader.services.segment_downloader.logger",
                MagicMock(),
            ),
        ):
            _check_download_space(100, tmp_path)

    def test_free_space_exactly_meeting_requirement_proceeds(self, tmp_path: Path) -> None:
        """Free space equal to the requirement is enough, not one byte less."""
        segment_count = 10
        exact_free = segment_count * self._DOWNLOAD_SEGMENT_BUDGET_BYTES

        with patch(
            "vkdownloader.services.segment_downloader.shutil.disk_usage",
            return_value=_fake_disk_usage(exact_free),
        ):
            _check_download_space(segment_count, tmp_path)

    def test_one_byte_below_requirement_fails(self, tmp_path: Path) -> None:
        """One byte short of the requirement fails before the fan-out."""
        segment_count = 10
        short_free = segment_count * self._DOWNLOAD_SEGMENT_BUDGET_BYTES - 1

        with patch(
            "vkdownloader.services.segment_downloader.shutil.disk_usage",
            return_value=_fake_disk_usage(short_free),
        ):
            with pytest.raises(DownloadError):
                _check_download_space(segment_count, tmp_path)


def _fake_disk_usage(free_bytes: int) -> object:
    """Mirror the named-tuple shape shutil.disk_usage returns."""
    from collections import namedtuple

    DiskUsage = namedtuple("DiskUsage", "total used free")
    return DiskUsage(free_bytes * 2, free_bytes, free_bytes)


class TestDownloadPolicyReprRedaction:
    """SEC-008: DownloadPolicy.__repr__ must redact sensitive header values."""

    COOKIE_CANARY = "secret_cookie_value_9876543210"
    AUTH_CANARY = "secret_bearer_token_0987654321"

    @staticmethod
    def _make_policy() -> DownloadPolicy:
        """Build a DownloadPolicy with sensitive headers for repr testing."""
        return DownloadPolicy(
            session=MagicMock(),
            semaphore=asyncio.Semaphore(1),
            headers={
                "User-Agent": "test-agent",
                "Cookie": f"session={TestDownloadPolicyReprRedaction.COOKIE_CANARY}",
                "Authorization": f"Bearer {TestDownloadPolicyReprRedaction.AUTH_CANARY}",
            },
            max_concurrent_segments=4,
            backoff_coordinator=None,
            video_url="https://vkvideo.ru/video-12345_67890",
            max_retries=3,
            download_timeout=300,
        )

    def test_repr_redacts_cookie_header(self) -> None:
        """Cookie header value must not appear in repr."""
        policy = self._make_policy()
        rendered = repr(policy)
        assert self.COOKIE_CANARY not in rendered

    def test_repr_redacts_authorization_header(self) -> None:
        """Authorization header value must not appear in repr."""
        policy = self._make_policy()
        rendered = repr(policy)
        assert self.AUTH_CANARY not in rendered

    def test_repr_contains_redaction_marker(self) -> None:
        """Redacted headers must show the redaction marker."""
        policy = self._make_policy()
        rendered = repr(policy)
        assert "***REDACTED***" in rendered

    def test_repr_preserves_non_sensitive_headers(self) -> None:
        """Non-sensitive headers (e.g. User-Agent) must remain visible."""
        policy = self._make_policy()
        rendered = repr(policy)
        assert "test-agent" in rendered
