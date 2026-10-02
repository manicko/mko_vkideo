"""Tests for segment_downloader token-refresh retry logic."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.services.downloader_throttle import (
    URLBackoffCoordinator,
    _resource_key,
    _shutdown_event_ctx,
)
from vkdownloader.services.segment_downloader import (
    _REASON_CANCELLED,
    _REASON_SHUTDOWN,
    _await_and_cancel,
    _download_segment_sequential,
    _fetch_playlist_with_retry,
    _handle_token_refresh,
    _log_preserve_segments,
    _SegmentFanoutOutcome,
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

        refresh_calls: list[str] = []
        fetch_urls: list[str] = []

        async def fake_refresh(
            vid: str, extractor: MagicMock, settings: Settings, headers: dict[str, str]
        ) -> tuple[str, str]:
            refresh_calls.append(vid)
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
                    )

        assert result is not None
        assert result.playlist_text == playlist
        assert result.base_url == refreshed_url
        assert refresh_calls == [video_url]
        assert fetch_urls == [m3u8_url, refreshed_url]
        assert headers.get("Cookie") == ""

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
            vid: str, extractor: MagicMock, settings: Settings, headers: dict[str, str]
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
            vid: str, extractor: MagicMock, settings: Settings, headers: dict[str, str]
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
            vid: str, extractor: MagicMock, settings: Settings, headers: dict[str, str]
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
            vid: str, extractor: MagicMock, settings: Settings, headers: dict[str, str]
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
        coordinator.wait_if_paused = AsyncMock(wraps=coordinator.wait_if_paused)

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
        coordinator.wait_if_paused = AsyncMock(wraps=coordinator.wait_if_paused)

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
    """D3: _handle_token_refresh must not mutate the caller's headers dict."""

    @pytest.mark.asyncio
    async def test_headers_unchanged_after_refresh(self, test_settings: Settings) -> None:
        """The headers dict passed to _handle_token_refresh is not modified.

        _handle_token_refresh delegates to _refresh_token_and_retry (which does
        not accept or mutate headers), so the caller's dict must survive intact.
        """
        video_url = "https://vkvideo.ru/video-12345_67890"
        original_headers = {"User-Agent": "test", "Cookie": "prior=value"}

        async def fake_refresh_token_and_retry(
            vid: str, extractor: MagicMock, settings: Settings
        ) -> tuple[str, str]:
            return "https://refreshed.m3u8", "new=cookie"

        mock_extractor = MagicMock()

        with patch(
            "vkdownloader.services.segment_downloader._refresh_token_and_retry",
            side_effect=fake_refresh_token_and_retry,
        ):
            with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                result = await _handle_token_refresh(
                    video_url, mock_extractor, test_settings, original_headers
                )

        assert result == ("https://refreshed.m3u8", "new=cookie")
        assert original_headers == {"User-Agent": "test", "Cookie": "prior=value"}


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

        # url_a and url_b have different origins (one has port 8080) — use same origin
        url_a = "https://user:pass@cdn.example.com/path1/seg.ts?token=abc"
        url_b = "https://cdn.example.com/path2/seg.ts"

        async def mock_wait_for(coro: object, timeout: float | None) -> object:
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

        async def mock_wait_for(coro: object, timeout: float | None) -> object:
            coro.close()
            raise TimeoutError()

        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for",
            side_effect=mock_wait_for,
        ):
            await coordinator.pause(raw_url, coordinator.pause_seconds)
            result = await coordinator.wait_if_paused(raw_url)

        assert result is True


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
        without cancelling pending siblings — leaving an orphaned task.
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
