"""Tests for batch_downloader.py D-01 deadlock regression and semaphore ownership."""

import asyncio
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import QualityNotAvailableError
from vkdownloader.models.enums import (
    CookieSource,
    DownloadMethod,
    ProgressStatus,
    StreamFormat,
)
from vkdownloader.models.quality import QualitySpec
from vkdownloader.models.video import Stream, VideoWithStreams
from vkdownloader.services.batch_downloader import (
    ConcurrencyTracker,
    DownloadContext,
    _download_single,
    _print_batch_summary,
    _run_batch_with_progress,
    _TrackedSemaphore,
    run_batch,
)
from vkdownloader.services.downloader_throttle import _shutdown_event_ctx
from vkdownloader.services.segment_downloader import PlaylistFetchResult
from vkdownloader.services.ytdlp_downloader import _ytdlp_temp_name


def _make_settings(tmp_path: Path) -> Settings:
    """Build Settings with explicit kwargs so CWD/.env cannot override values."""
    return Settings(
        cookie_source=CookieSource.NONE,
        max_concurrent_downloads=2,
        max_retries=1,
        download_dir=tmp_path,
    )


def _hls_stream() -> Stream:
    """Return a single HLS stream for test videos."""
    return Stream(
        url="https://example.com/playlist.m3u8",
        format=StreamFormat.HLS,
        quality="best",
        height=1080,
    )


def _browser_streams() -> list[Stream]:
    """Return browser-extracted streams for token-refresh fallback."""
    return [
        Stream(
            url="https://example.com/fresh_token.m3u8",
            format=StreamFormat.HLS,
            quality="best",
            height=1080,
        )
    ]


def _make_mock_extract_streams() -> object:
    """Return an async mock that yields a unique VideoWithStreams per URL."""

    async def mock_extract_streams(url: str) -> VideoWithStreams:
        video_id = url.split("_")[-1]
        return VideoWithStreams(
            id=f"12345_{video_id}",
            title=f"test_video_{video_id}",
            streams=[_hls_stream()],
        )

    return mock_extract_streams


def _make_mock_download_segment() -> object:
    """Return an async mock for _download_segment that writes a dummy segment."""

    async def mock_download_segment(
        session: object,
        segment_url: str,
        output_path: Path,
        headers: dict[str, str],
        **kwargs: object,
    ) -> bool:
        output_path.write_bytes(b"segment data")
        return True

    return mock_download_segment


def _expected_output_path(tmp_path: Path, url: str) -> Path:
    """Compute the output file path that download_video will resolve for a URL."""
    video_id = url.split("_")[-1]
    return tmp_path / f"test_video_{video_id}_12345_{video_id}.mp4"


def _batch_urls(count: int) -> list[str]:
    """Return ``count`` distinct, valid-looking batch URLs."""
    return [f"https://vkvideo.ru/video-12345_{i:05d}" for i in range(count)]


def _make_batch_download(outcomes: Mapping[str, Path | None | BaseException]) -> object:
    """Return an async ``download_video`` stand-in replaying per-URL outcomes.

    An outcome of ``None`` means "the transfer returned no file", an outcome
    that is an exception instance means "the transfer raised it". This stubs
    the process boundary only: the classification, the progress-status bridge
    and the summary all run as production code, which is what lets these
    tests fail on the D-04 regression.
    """

    async def mock_download_video(url: str, *args: object, **kwargs: object) -> Path | None:
        outcome = outcomes[url]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return mock_download_video


@contextmanager
def _batch_runtime(download: object) -> Iterator[None]:
    """Patch only the batch's process boundary for the duration of one run.

    Deliberately does NOT patch the classification helper, the shutdown
    event, or the summary printer: the whole point of these tests is to
    drive the real path between the download result and the summary.
    """
    with (
        patch("vkdownloader.services.batch_downloader.setup_signal_handlers"),
        patch("vkdownloader.services.batch_downloader.cleanup_signal_handlers"),
        patch("vkdownloader.services.batch_downloader.download_video", side_effect=download),
        patch(
            "vkdownloader.services.batch_downloader.VKVideoExtractor.extract_streams",
            side_effect=_make_mock_extract_streams(),
        ),
    ):
        yield


class TestBatchDownloaderSemaphore:
    """D-01 deadlock regression and semaphore ownership tests."""

    @pytest.mark.asyncio
    async def test_batch_completes_without_deadlock_when_max_reached(self, tmp_path: Path) -> None:
        """D-01: batch of max_concurrent+2 URLs completes; at least one via segment path."""
        settings = Settings(
            cookie_source=CookieSource.NONE,
            max_concurrent_downloads=2,
            max_retries=1,
            download_dir=tmp_path,
        )

        n = settings.max_concurrent_downloads + 2
        urls = [f"https://vkvideo.ru/video-12345_{i:05d}" for i in range(n)]

        # Pre-create .part files so the yt-dlp fallback engages segment resume.
        for url in urls:
            _ytdlp_temp_name(_expected_output_path(tmp_path, url)).write_bytes(b"partial")

        # _merge_segments_batched returns the output_file arg so the chain sees success.
        merge_side_effect = lambda segments_dir, output_file, *_: output_file  # noqa: E731

        with (
            patch("vkdownloader.services.batch_downloader.setup_signal_handlers"),
            patch("vkdownloader.services.batch_downloader.cleanup_signal_handlers"),
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
                side_effect=_make_mock_extract_streams(),
            ),
            patch(
                "vkdownloader.services.ytdlp_downloader._download_with_ytdlp",
                return_value=None,
            ),
            patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=(_browser_streams(), None, None),
            ),
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                return_value=PlaylistFetchResult(
                    playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\n",
                    base_url="https://example.com/playlist.m3u8",
                ),
            ),
            patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=_make_mock_download_segment(),
            ),
            patch(
                "vkdownloader.services.segment_downloader._merge_segments_batched",
                side_effect=merge_side_effect,
            ),
        ):
            results, peak = await asyncio.wait_for(
                _run_batch_with_progress(
                    urls,
                    QualitySpec.parse("best"),
                    DownloadMethod.AUTO,
                    settings,
                    output=tmp_path,
                ),
                timeout=30,
            )

        # Deadlock regression: all URLs must complete (a hang would TimeoutError).
        assert len(results) == n
        for url, _output_path, status in results:
            assert status == "success", f"{url} failed with status '{status}'"

        # Peak concurrency must never exceed the configured video limit.
        assert peak <= settings.max_concurrent_downloads

    @pytest.mark.asyncio
    async def test_segment_layer_does_not_acquire_caller_video_semaphore(
        self, tmp_path: Path
    ) -> None:
        """D-01: segment layer does not gate on the caller's video permit."""
        from vkdownloader.models.dtos import HLSDownloadRequest
        from vkdownloader.services.segment_downloader import download_hls_with_resume

        settings = Settings(
            cookie_source=CookieSource.NONE,
            max_concurrent_downloads=2,
            max_retries=1,
            download_dir=tmp_path,
        )

        output_path = tmp_path / "video.mp4"
        video_semaphore = asyncio.Semaphore(2)

        # Hold all permits so any inner acquisition from this object would block.
        await video_semaphore.acquire()
        await video_semaphore.acquire()
        initial_value = video_semaphore._value

        async def mock_download_segment(
            session: object,
            segment_url: str,
            seg_output: Path,
            headers: dict[str, str],
            **kwargs: object,
        ) -> bool:
            seg_output.write_bytes(b"segment data")
            return True

        merge_side_effect = lambda segments_dir, output_file, *_: output_file  # noqa: E731

        with (
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                return_value=PlaylistFetchResult(
                    playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\n",
                    base_url="https://example.com/playlist.m3u8",
                ),
            ),
            patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=mock_download_segment,
            ),
            patch(
                "vkdownloader.services.segment_downloader._merge_segments_batched",
                side_effect=merge_side_effect,
            ),
        ):
            result = await asyncio.wait_for(
                download_hls_with_resume(
                    HLSDownloadRequest(
                        video_url="https://vkvideo.ru/video-12345_67890",
                        m3u8_url="https://example.com/video.m3u8",
                        output_file=output_path,
                    ),
                    settings=settings,
                    video_semaphore=video_semaphore,  # type: ignore[arg-type]
                ),
                timeout=10,
            )

        # Segment layer completed using its own semaphore; caller's permits untouched.
        assert result == output_path
        assert video_semaphore._value == initial_value

    @pytest.mark.asyncio
    async def test_permit_leak_after_completed_batch(self, tmp_path: Path) -> None:
        """D-01: after a completed download, all semaphore permits are returned."""
        settings = _make_settings(tmp_path)

        semaphore = asyncio.Semaphore(2)
        initial_value = semaphore._value
        tracker = ConcurrencyTracker()
        context = DownloadContext(
            index=0,
            shared_semaphore=semaphore,
            peak_tracker=tracker,
        )

        url = "https://vkvideo.ru/video-12345_00001"
        output_file = _expected_output_path(tmp_path, url)
        # Pre-create .part file (yt-dlp's temp name) so the retry loop
        # doesn't exit early at the partial-file probe.
        _ytdlp_temp_name(output_file).write_bytes(b"partial")

        merge_side_effect = lambda segments_dir, out_file, *_: out_file  # noqa: E731

        mock_video = VideoWithStreams(
            id="12345_00001",
            title="test_video_00001",
            streams=[_hls_stream()],
        )

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
                new_callable=AsyncMock,
                return_value=mock_video,
            ),
            patch(
                "vkdownloader.services.ytdlp_downloader._download_with_ytdlp",
                return_value=None,
            ),
            patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams_with_cookies",
                return_value=(_browser_streams(), None, None),
            ),
            patch(
                "vkdownloader.services.segment_downloader._fetch_playlist_with_retry",
                return_value=PlaylistFetchResult(
                    playlist_text="#EXTM3U\nseg1.ts\nseg2.ts\n",
                    base_url="https://example.com/playlist.m3u8",
                ),
            ),
            patch(
                "vkdownloader.services.segment_downloader._download_segment",
                side_effect=_make_mock_download_segment(),
            ),
            patch(
                "vkdownloader.services.segment_downloader._merge_segments_batched",
                side_effect=merge_side_effect,
            ),
        ):
            result = await asyncio.wait_for(
                _download_single(
                    url,
                    QualitySpec.parse("best"),
                    tmp_path,
                    DownloadMethod.AUTO,
                    settings,
                    context=context,
                ),
                timeout=30,
            )

        # Download succeeded via segment path.
        assert result[2] == "success"

        # All semaphore permits returned — no leak.
        assert semaphore._value == initial_value
        assert tracker._current == 0
        assert tracker.peak > 0

    def test_print_batch_summary_labels_peak_concurrent_videos(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-01: batch summary labels the peak figure with its unit."""
        results: list[tuple[str, str, str]] = [
            ("https://vkvideo.ru/video-1_1", str(Path("/tmp/video.mp4")), "success"),
            ("https://vkvideo.ru/video-1_2", "", "failed"),
        ]

        exit_code = _print_batch_summary(results, peak_concurrent_videos=2, skipped_count=0)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Peak concurrent videos: 2" in captured.out
        assert "Peak concurrency" not in captured.out


class TestBatchCancellationReporting:
    """D-04: an interrupted batch reports cancellation, not failure."""

    @pytest.mark.asyncio
    async def test_interrupted_batch_reports_cancelled_not_failed(self, tmp_path: Path) -> None:
        """D-04 core: with the shutdown event set, an empty result is cancelled, not failed.

        Runs the real classification and the real summary printer — only the
        download itself is stubbed — so the statuses and the exit code are
        the product's own.
        """
        settings = _make_settings(tmp_path)
        urls = _batch_urls(3)
        download = _make_batch_download(dict.fromkeys(urls, None))

        # get_shutdown_event() lazily caches a loop-bound Event in a ContextVar.
        # Inject one inside the test coroutine and restore the previous state
        # with the token, so a set Event never leaks into another test's loop.
        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()
            with _batch_runtime(download):
                results, peak = await asyncio.wait_for(
                    _run_batch_with_progress(
                        urls,
                        QualitySpec.parse("best"),
                        DownloadMethod.AUTO,
                        settings,
                        output=tmp_path,
                    ),
                    timeout=30,
                )
            exit_code = _print_batch_summary(results, peak, 0)
        finally:
            _shutdown_event_ctx.reset(token)

        statuses = [status for _url, _output_path, status in results]
        assert statuses == [ProgressStatus.CANCELLED.value] * len(urls)
        assert ProgressStatus.FAILED.value not in statuses
        assert exit_code == 130

    @pytest.mark.asyncio
    async def test_interrupted_batch_summary_does_not_count_cancellations_as_failures(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-04: the summary reports zero failures, the cancelled count, and resume data."""
        settings = _make_settings(tmp_path)
        urls = _batch_urls(2)
        download = _make_batch_download(dict.fromkeys(urls, None))

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()
            with _batch_runtime(download):
                exit_code = await asyncio.wait_for(
                    run_batch(
                        urls,
                        QualitySpec.parse("best"),
                        DownloadMethod.AUTO,
                        settings,
                        tmp_path,
                    ),
                    timeout=30,
                )
        finally:
            _shutdown_event_ctx.reset(token)

        captured = capsys.readouterr()
        assert exit_code == 130
        assert "Successful: 0" in captured.out
        assert "Failed: 0" in captured.out
        assert f"  Cancelled: {len(urls)}" in captured.out
        assert "preserved for resume" in captured.out
        # A cancelled item is not a failure, so it is never listed as one.
        assert "Failed URLs:" not in captured.out
        for url in urls:
            assert f"{url}: {ProgressStatus.CANCELLED.value}" in captured.out

    @pytest.mark.asyncio
    async def test_uninterrupted_failed_download_is_still_a_failure(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-04 guard: without the shutdown event, an empty result is still a failure."""
        settings = _make_settings(tmp_path)
        urls = _batch_urls(2)
        download = _make_batch_download(dict.fromkeys(urls, None))

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with _batch_runtime(download):
                results, peak = await asyncio.wait_for(
                    _run_batch_with_progress(
                        urls,
                        QualitySpec.parse("best"),
                        DownloadMethod.AUTO,
                        settings,
                        output=tmp_path,
                    ),
                    timeout=30,
                )
            exit_code = _print_batch_summary(results, peak, 0)
        finally:
            _shutdown_event_ctx.reset(token)

        assert [status for _url, _output_path, status in results] == [
            ProgressStatus.FAILED.value
        ] * len(urls)
        assert exit_code == 1
        captured = capsys.readouterr()
        assert f"Failed: {len(urls)}" in captured.out
        assert "Cancelled:" not in captured.out
        assert "preserved for resume" not in captured.out

    @pytest.mark.asyncio
    async def test_mixed_outcomes_classify_independently(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-04: success, cancellation and failure are three independent buckets."""
        settings = _make_settings(tmp_path)
        succeeded_url, cancelled_url, failed_url = _batch_urls(3)
        urls = [succeeded_url, cancelled_url, failed_url]
        download = _make_batch_download(
            {
                succeeded_url: tmp_path / "ok.mp4",
                cancelled_url: None,
                failed_url: QualityNotAvailableError("1080", ["720"]),
            }
        )

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()
            with _batch_runtime(download):
                results, peak = await asyncio.wait_for(
                    _run_batch_with_progress(
                        urls,
                        QualitySpec.parse("best"),
                        DownloadMethod.AUTO,
                        settings,
                        output=tmp_path,
                    ),
                    timeout=30,
                )
            exit_code = _print_batch_summary(results, peak, 0)
        finally:
            _shutdown_event_ctx.reset(token)

        by_url = {url: status for url, _output_path, status in results}
        assert by_url[succeeded_url] == ProgressStatus.SUCCESS.value
        assert by_url[cancelled_url] == ProgressStatus.CANCELLED.value
        # A download that raised a domain error failed, whatever the flag says.
        assert by_url[failed_url] == "quality_not_available"

        captured = capsys.readouterr()
        assert "Successful: 1" in captured.out
        assert "Failed: 1" in captured.out
        assert "  Cancelled: 1" in captured.out
        assert f"    - {failed_url}: quality_not_available" in captured.out
        assert f"    - {cancelled_url}:" not in captured.out
        # Cancellation wins over failure: the run did not finish by the user's doing.
        assert exit_code == 130

    @pytest.mark.asyncio
    async def test_clean_run_prints_no_cancelled_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-04: the Cancelled line is conditional and adds no noise to a clean run."""
        settings = _make_settings(tmp_path)
        urls = _batch_urls(3)
        download = _make_batch_download(
            {url: tmp_path / f"video_{index}.mp4" for index, url in enumerate(urls)}
        )

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with _batch_runtime(download):
                exit_code = await asyncio.wait_for(
                    run_batch(
                        urls,
                        QualitySpec.parse("best"),
                        DownloadMethod.AUTO,
                        settings,
                        tmp_path,
                    ),
                    timeout=30,
                )
        finally:
            _shutdown_event_ctx.reset(token)

        captured = capsys.readouterr()
        assert exit_code == 0
        assert f"Successful: {len(urls)}" in captured.out
        assert "Failed: 0" in captured.out
        assert "Cancelled:" not in captured.out
        assert "preserved for resume" not in captured.out

    def test_print_batch_summary_returns_130_when_cancelled(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-04: the exit-code precedence, pinned independently of the async path."""
        cancelled_results: list[tuple[str, str, str]] = [
            ("https://vkvideo.ru/video-1_1", "", ProgressStatus.CANCELLED.value),
            ("https://vkvideo.ru/video-1_2", "", "quality_not_available"),
        ]
        exit_code = _print_batch_summary(cancelled_results, peak_concurrent_videos=1)
        cancelled_output = capsys.readouterr().out

        assert exit_code == 130
        assert "Failed: 1" in cancelled_output
        assert "  Cancelled: 1" in cancelled_output
        assert f"    - {cancelled_results[1][0]}: quality_not_available" in cancelled_output
        assert f"    - {cancelled_results[0][0]}:" not in cancelled_output

        failed_results: list[tuple[str, str, str]] = [
            ("https://vkvideo.ru/video-1_1", "", "video_not_found")
        ]
        exit_code = _print_batch_summary(failed_results, peak_concurrent_videos=1)
        failed_output = capsys.readouterr().out

        assert exit_code == 1
        assert "Failed: 1" in failed_output
        assert "Cancelled:" not in failed_output

        success_results: list[tuple[str, str, str]] = [
            (
                "https://vkvideo.ru/video-1_1",
                str(Path("/tmp/video.mp4")),
                ProgressStatus.SUCCESS.value,
            )
        ]
        exit_code = _print_batch_summary(success_results, peak_concurrent_videos=1)
        success_output = capsys.readouterr().out

        assert exit_code == 0
        assert "Successful: 1" in success_output
        assert "Cancelled:" not in success_output


class TestBatchCancellationPropagates:
    """Route B: a child that *raises* CancelledError re-raises through run_batch,
    never reaching _print_batch_summary.

    This is the raising route (B), distinct from the returning route tested by
    TestBatchCancellationReporting (A): the former propagates CancelledError
    directly; the latter returns an exit code 130 from the summary printer.
    """

    @pytest.mark.asyncio
    async def test_run_batch_re_raises_cancelled_when_child_raises(self, tmp_path: Path) -> None:
        """When a child download raises CancelledError, run_batch re-raises it
        and _print_batch_summary is never called.

        Route B (raising): the CancelledError propagates out of
        _run_batch_with_progress before run_batch can invoke
        _print_batch_summary. The exit code 130 is produced by cli.py's
        CancelledError arm, not by _print_batch_summary.
        """
        settings = _make_settings(tmp_path)
        urls = _batch_urls(1)
        download = _make_batch_download({urls[0]: asyncio.CancelledError("cancelled by caller")})

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with _batch_runtime(download):
                with patch(
                    "vkdownloader.services.batch_downloader._print_batch_summary"
                ) as mock_summary:
                    try:
                        await asyncio.wait_for(
                            run_batch(
                                urls,
                                QualitySpec.parse("best"),
                                DownloadMethod.AUTO,
                                settings,
                                tmp_path,
                            ),
                            timeout=5.0,
                        )
                    except TimeoutError:
                        pytest.fail("run_batch did not propagate CancelledError within 5.0s")
                    except asyncio.CancelledError:
                        pass  # expected -- route B raises CancelledError
        finally:
            _shutdown_event_ctx.reset(token)

        mock_summary.assert_not_called()


class TestCorrelationInheritance:
    """Verify correlation-ID scoping through the real batch orchestration.

    ``download_video`` must inherit the identifier bound by its caller rather
    than generating/clearing its own (DF-002), so a per-item id bound in
    ``_download_single`` flows through and is cleared exactly once by
    ``_download_single``'s finally.
    """

    @pytest.mark.asyncio
    async def test_download_video_inherits_and_preserves_item_correlation_id(
        self, tmp_path: Path
    ) -> None:
        """The identifier visible inside download_video equals the item id
        bound by _download_single, and the same id is still bound after
        download_video returns.

        Probes structlog.contextvars.get_contextvars() at two observable
        points — one inside the download and one after it back in
        _download_single — rather than scraping rendered log text.
        """
        import structlog.contextvars

        from vkdownloader.utils import correlation as _correlation

        settings = _make_settings(tmp_path)
        url = _batch_urls(1)[0]

        bound_ids: list[str] = []
        inside_context: list[str | None] = []
        after_context: list[str | None] = []

        def _track_bind(correlation_id: str) -> None:
            bound_ids.append(correlation_id)
            _correlation.bind_correlation_id(correlation_id)

        def _track_clear() -> None:
            after_context.append(structlog.contextvars.get_contextvars().get("correlation_id"))
            _correlation.clear_correlation_id()

        async def _probe_inside_download(*args: object, **kwargs: object) -> Path:
            inside_context.append(structlog.contextvars.get_contextvars().get("correlation_id"))
            return tmp_path / "ok.mp4"

        with (
            patch("vkdownloader.services.batch_downloader.setup_signal_handlers"),
            patch("vkdownloader.services.batch_downloader.cleanup_signal_handlers"),
            patch(
                "vkdownloader.services.batch_downloader.VKVideoExtractor.extract_streams",
                side_effect=_make_mock_extract_streams(),
            ),
            patch(
                "vkdownloader.services.batch_downloader.bind_correlation_id",
                side_effect=_track_bind,
            ),
            patch(
                "vkdownloader.services.batch_downloader.clear_correlation_id",
                side_effect=_track_clear,
            ),
            patch(
                "vkdownloader.services.batch_downloader.download_video",
                side_effect=_probe_inside_download,
            ),
        ):
            results, _peak = await asyncio.wait_for(
                _run_batch_with_progress(
                    [url],
                    QualitySpec.parse("best"),
                    DownloadMethod.AUTO,
                    settings,
                    output=tmp_path,
                ),
                timeout=30,
            )

        # _run_batch_with_progress binds the run-level id first; _download_single
        # binds the item-level id second. With one item, bound_ids[-1] is the
        # item's identifier.
        item_correlation_id = bound_ids[-1]

        # Observable point 1 — inside download_video: the bound id equals the
        # item's id, proving download_video inherited rather than regenerated.
        assert inside_context[0] == item_correlation_id, (
            f"download_video saw correlation_id={inside_context[0]!r}, "
            f"expected item id {item_correlation_id!r}"
        )

        # Observable point 2 — after download_video returns, back in
        # _download_single: the same id is still bound — download_video did
        # not clear it. _download_single's finally then clears it.
        assert after_context[0] == item_correlation_id, (
            f"after download_video, correlation_id={after_context[0]!r}, "
            f"expected still bound as {item_correlation_id!r}"
        )

        assert results[0][2] == "success"


class TestBatchLiveTaskBounding:
    """B7: bound the live asyncio task set to the concurrency ceiling."""

    @pytest.mark.asyncio
    async def test_bounded_producer_never_exceeds_ceiling(self, tmp_path: Path) -> None:
        """B7: with more URLs than the ceiling, live ``_download_single`` tasks peak at the ceiling.

        Stubs ``download_video`` (not ``_download_single``) so the real batch
        pump and classification run. Counts live tasks via ``asyncio.all_tasks``
        filtered on ``get_coro().__qualname__ == "_download_single"``.
        """
        ceiling = 4
        settings = Settings(
            cookie_source=CookieSource.NONE,
            max_concurrent_downloads=ceiling,
            max_retries=1,
            download_dir=tmp_path,
        )
        n_urls = 200
        urls = _batch_urls(n_urls)

        peak_live = 0
        current_live = 0

        async def _counting_download(*args: object, **kwargs: object) -> Path | None:
            nonlocal current_live, peak_live
            # Count live _download_single tasks via asyncio.all_tasks() --
            # this matches the production measurement approach (D-01).
            live = sum(
                1
                for t in asyncio.all_tasks()
                if not t.done()
                and (coro := t.get_coro()) is not None
                and coro.__qualname__ == "_download_single"
            )
            current_live = live
            peak_live = max(peak_live, current_live)
            await asyncio.sleep(0.01)
            return tmp_path / "video.mp4"

        with _batch_runtime(_counting_download):
            results, peak = await asyncio.wait_for(
                _run_batch_with_progress(
                    urls,
                    QualitySpec.parse("best"),
                    DownloadMethod.AUTO,
                    settings,
                    output=tmp_path,
                ),
                timeout=30,
            )

        assert len(results) == n_urls
        assert peak_live <= ceiling, f"peak_live={peak_live} exceeded ceiling={ceiling}"
        result_urls = {url for url, _, _ in results}
        assert result_urls == set(urls), "some URLs were dropped by the bounded producer"

    @pytest.mark.asyncio
    async def test_stop_with_unstarted_urls_reports_cancelled_exit_130(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """B7: stopping before all URLs are claimed yields all-CANCELLED + exit 130.

        Uses ``_make_batch_download`` with ``None`` outcomes + a pre-set shutdown
        Event (the returning route A), mirroring ``test_interrupted_batch_reports_cancelled_not_failed``.
        """
        ceiling = 2
        settings = Settings(
            cookie_source=CookieSource.NONE,
            max_concurrent_downloads=ceiling,
            max_retries=1,
            download_dir=tmp_path,
        )
        urls = _batch_urls(3)
        download = _make_batch_download(dict.fromkeys(urls, None))

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            _shutdown_event_ctx.get().set()
            with _batch_runtime(download):
                results, peak = await asyncio.wait_for(
                    _run_batch_with_progress(
                        urls,
                        QualitySpec.parse("best"),
                        DownloadMethod.AUTO,
                        settings,
                        output=tmp_path,
                    ),
                    timeout=30,
                )
        finally:
            _shutdown_event_ctx.reset(token)

        statuses = [status for _url, _output_path, status in results]
        assert statuses == [ProgressStatus.CANCELLED.value] * len(urls)
        assert peak <= ceiling

        exit_code = _print_batch_summary(results, peak, 0)
        captured = capsys.readouterr()
        assert exit_code == 130
        assert "Successful: 0" in captured.out
        assert "Failed: 0" in captured.out
        assert f"  Cancelled: {len(urls)}" in captured.out

    @pytest.mark.asyncio
    async def test_no_half_claimed_batch_permit_after_stop(self, tmp_path: Path) -> None:
        """B7 / D-01: stopping mid-batch leaks no batch-level semaphore permits.

        Drives the raising route (a child that raises ``CancelledError``) so
        control reaches the ``asyncio.CancelledError`` handler in
        ``_run_batch_with_progress``. Patches ``_TrackedSemaphore`` to count
        acquire/release calls: every acquire must have a matching release even
        when the batch is cancelled mid-flight.
        """
        ceiling = 2
        settings = Settings(
            cookie_source=CookieSource.NONE,
            max_concurrent_downloads=ceiling,
            max_retries=1,
            download_dir=tmp_path,
        )
        urls = _batch_urls(4)
        download = _make_batch_download(
            {
                urls[0]: asyncio.CancelledError("stop"),
                urls[1]: None,
                urls[2]: None,
                urls[3]: None,
            }
        )

        original_cls = _TrackedSemaphore
        acquire_count = 0
        release_count = 0

        class _CountingTrackedSemaphore(original_cls):  # type: ignore[misc,valid-type]
            async def acquire(self) -> bool:
                nonlocal acquire_count
                acquire_count += 1
                return await super().acquire()  # type: ignore[no-any-return]

            def release(self) -> None:
                nonlocal release_count
                release_count += 1
                super().release()

        token = _shutdown_event_ctx.set(asyncio.Event())
        try:
            with _batch_runtime(download):
                with patch(
                    "vkdownloader.services.batch_downloader._TrackedSemaphore",
                    _CountingTrackedSemaphore,
                ):
                    with pytest.raises(asyncio.CancelledError):
                        await asyncio.wait_for(
                            _run_batch_with_progress(
                                urls,
                                QualitySpec.parse("best"),
                                DownloadMethod.AUTO,
                                settings,
                                output=tmp_path,
                            ),
                            timeout=5.0,
                        )
        finally:
            _shutdown_event_ctx.reset(token)

        # Every acquire must have a matching release -- no half-claimed permits.
        assert acquire_count == release_count, (
            f"permits leaked: {acquire_count} acquired, {release_count} released"
        )


class TestBatchDedupSkip:
    """B9: an exact-URL duplicate in the batch is skipped, not re-downloaded."""

    @pytest.mark.asyncio
    async def test_duplicate_url_marked_skipped_not_downloaded(self, tmp_path: Path) -> None:
        """B9 oracle: an exact-URL duplicate reaches finish_task(SKIPPED) and is
        never sent to download_video.

        Fails on regression if: the dedup check is removed (duplicate is
        downloaded twice), finish_task is called with anything other than
        SKIPPED, or the SKIPPED status never reaches results.
        """
        settings = _make_settings(tmp_path)
        first_url, second_url = _batch_urls(2)
        urls = [first_url, first_url, second_url]  # first_url duplicated

        download_calls: list[str] = []

        async def tracking_download(url: str, *args: object, **kwargs: object) -> Path | None:
            download_calls.append(url)
            return tmp_path / "video.mp4"

        with patch(
            "vkdownloader.services.batch_downloader.RichProgressReporter"
        ) as mock_reporter_cls:
            mock_reporter = mock_reporter_cls.return_value
            with _batch_runtime(tracking_download):
                results, _ = await asyncio.wait_for(
                    _run_batch_with_progress(
                        urls,
                        QualitySpec.parse("best"),
                        DownloadMethod.AUTO,
                        settings,
                        output=tmp_path,
                    ),
                    timeout=30,
                )

        # download_video was called once per unique URL; the duplicate was not
        # re-fetched (no second media download per DEC-W R1).
        assert download_calls.count(first_url) == 1
        assert download_calls.count(second_url) == 1
        assert len(download_calls) == 2

        # The duplicate (index 1) reached finish_task(SKIPPED) — the real
        # producer path, not a mocked renderer call.
        mock_reporter.finish_task.assert_any_call(1, ProgressStatus.SKIPPED)

        # Results carry the SKIPPED status for the duplicate position.
        statuses = [status for _, _, status in results]
        assert statuses[1] == ProgressStatus.SKIPPED.value
        assert statuses[0] == ProgressStatus.SUCCESS.value
        assert statuses[2] == ProgressStatus.SUCCESS.value
        assert ProgressStatus.FAILED.value not in statuses

    @pytest.mark.asyncio
    async def test_duplicate_skip_summary_reports_skipped_not_failed(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A batch with a duplicate URL: the duplicate is skipped and the
        summary reports it as Skipped, not Failed, with exit code 0.

        Fails on regression if: Total videos excludes the skipped item, the
        Skipped line is absent, or the skipped item is mis-counted as failed.
        """
        settings = _make_settings(tmp_path)
        first_url = _batch_urls(1)[0]
        urls = [first_url, first_url]

        download = _make_batch_download({first_url: tmp_path / "ok.mp4"})

        with _batch_runtime(download):
            results, _ = await asyncio.wait_for(
                _run_batch_with_progress(
                    urls,
                    QualitySpec.parse("best"),
                    DownloadMethod.AUTO,
                    settings,
                    output=tmp_path,
                ),
                timeout=30,
            )

        exit_code = _print_batch_summary(results, 1, 0)
        captured = capsys.readouterr()

        # Total videos includes skipped items in len(results).
        assert "Total videos: 2" in captured.out
        assert "Successful: 1" in captured.out
        assert "Failed: 0" in captured.out
        assert "Skipped (duplicates): 1" in captured.out
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_filename_dedup_skipped_entry_not_called(self, tmp_path: Path) -> None:
        """B10: two URLs resolving to the same output filename produce exactly one
        ``download_video`` dispatch — the last survivor only — and the loser is
        never dispatched.

        Fails on regression if: the pre-pass is removed (both dispatched), the
        wrong entry wins (first instead of last), or the loser's SKIPPED status
        never reaches results.
        """
        settings = _make_settings(tmp_path)
        url_a = "https://vkvideo.ru/video-12345_00001"
        url_b = "https://vkvideo.ru/video-12345_00002"
        urls = [url_a, url_b]

        # Same id; titles "Title?A" and "Title:A" both sanitise to "Title_A"
        # so _resolve_output_file yields the identical path for both entries.
        video_a = VideoWithStreams(id="12345", title="Title?A", streams=[_hls_stream()])
        video_b = VideoWithStreams(id="12345", title="Title:A", streams=[_hls_stream()])

        async def mock_extract_streams(url: str) -> VideoWithStreams:
            return video_a if url == url_a else video_b

        download_calls: list[str] = []

        async def tracking_download(url: str, *args: object, **kwargs: object) -> Path | None:
            download_calls.append(url)
            return tmp_path / "Title_A_12345.mp4"

        with patch(
            "vkdownloader.services.batch_downloader.RichProgressReporter"
        ) as mock_reporter_cls:
            mock_reporter = mock_reporter_cls.return_value
            with _batch_runtime(tracking_download):
                with patch(
                    "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
                    side_effect=mock_extract_streams,
                ):
                    results, _ = await asyncio.wait_for(
                        _run_batch_with_progress(
                            urls,
                            QualitySpec.parse("best"),
                            DownloadMethod.AUTO,
                            settings,
                            output=tmp_path,
                        ),
                        timeout=30,
                    )

        # download_video was dispatched exactly once — for the survivor (url_b,
        # the last in list order).  The loser (url_a) was terminalised as
        # SKIPPED in the pre-pass and never reaches the dispatch path.
        assert len(download_calls) == 1
        assert download_calls[0] == url_b

        # The loser (index 0) reached finish_task(SKIPPED) via the real producer
        # path — the pre-pass terminalisation, not a mocked renderer call.
        mock_reporter.finish_task.assert_any_call(0, ProgressStatus.SKIPPED)

        # Results carry the SKIPPED status for the loser position.
        statuses = [status for _, _, status in results]
        assert statuses[0] == ProgressStatus.SKIPPED.value
        assert statuses[1] == ProgressStatus.SUCCESS.value
        assert ProgressStatus.FAILED.value not in statuses

    @pytest.mark.asyncio
    async def test_filename_dedup_mkdir_side_effect(self, tmp_path: Path) -> None:
        """B10 (C9): the ``_resolve_output_file`` mkdir side effect runs for every
        resolved entry — including the filename-collision loser — so the output
        directory is created even for a skipped entry.

        Fails on regression if: the pre-pass skips resolution for a collided
        entry (loser's mkdir never runs), or the loser reaches the fill phase
        and is dispatched before being terminalised.
        """
        from vkdownloader.utils.security import _resolve_output_file

        settings = _make_settings(tmp_path)
        url_a = "https://vkvideo.ru/video-12345_00001"
        url_b = "https://vkvideo.ru/video-12345_00002"
        urls = [url_a, url_b]

        # Same id; titles sanitise to the same filename component → collision.
        video_a = VideoWithStreams(id="12345", title="Title?A", streams=[_hls_stream()])
        video_b = VideoWithStreams(id="12345", title="Title:A", streams=[_hls_stream()])

        async def mock_extract_streams(url: str) -> VideoWithStreams:
            return video_a if url == url_a else video_b

        download = _make_batch_download({url_b: tmp_path / "Title_A_12345.mp4"})

        # Non-existent subdirectory so the mkdir side effect is observable.
        output_dir = tmp_path / "batch_output"
        assert not output_dir.exists()

        # Spy on _resolve_output_file: every call records the index and then
        # delegates to the real implementation (which performs the mkdir).
        resolve_indices: list[int] = []

        def tracking_resolve(
            video: VideoWithStreams,
            output: Path,
            settings_obj: Settings,
            index: int,
        ) -> Path:
            resolve_indices.append(index)
            return _resolve_output_file(video, output, settings_obj, index)

        with patch("vkdownloader.services.batch_downloader.RichProgressReporter"):
            with _batch_runtime(download):
                with patch(
                    "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
                    side_effect=mock_extract_streams,
                ):
                    with patch(
                        "vkdownloader.services.batch_downloader._resolve_output_file",
                        side_effect=tracking_resolve,
                    ):
                        results, _ = await asyncio.wait_for(
                            _run_batch_with_progress(
                                urls,
                                QualitySpec.parse("best"),
                                DownloadMethod.AUTO,
                                settings,
                                output=output_dir,
                            ),
                            timeout=30,
                        )

        # The loser (index 0) is terminalised as SKIPPED in by_index.
        statuses = [status for _, _, status in results]
        assert statuses[0] == ProgressStatus.SKIPPED.value

        # _resolve_output_file was called for BOTH entries (including the
        # loser) in the pre-pass — the mkdir side effect (C9) ran for every
        # resolved entry, not just the survivor.
        assert resolve_indices == [0, 1]

        # The output directory was created by the mkdir side effect.
        assert output_dir.exists()
        assert output_dir.is_dir()


class TestBatchSummarySkippedAggregation:
    """Aggregation of a SKIPPED entry in the batch summary.

    Distinct from ``TestBatchDedupSkip``: these tests assert how the summary
    *counts* a skipped entry, feeding a hand-built ``results`` list and
    exercising no dedup logic at all.
    """

    def test_skipped_entry_counted_as_skipped_not_as_failed(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """B9: a SKIPPED entry in results is counted under Skipped, not Failed.

        Fails on regression if the subtraction rule returns
        ``failed = len(results) - successful - cancelled`` (which would count
        the skipped item as failed) or if the Skipped line is absent.
        """
        results: list[tuple[str, str, str]] = [
            (
                "https://vkvideo.ru/video-1_1",
                str(Path("/tmp/video.mp4")),
                ProgressStatus.SUCCESS.value,
            ),
            ("https://vkvideo.ru/video-1_2", "", ProgressStatus.SKIPPED.value),
        ]

        exit_code = _print_batch_summary(results, peak_concurrent_videos=1, skipped_count=0)
        captured = capsys.readouterr()

        # Total videos includes skipped items in len(results).
        assert "Total videos: 2" in captured.out
        assert "Successful: 1" in captured.out
        assert "Failed: 0" in captured.out
        assert "Skipped (duplicates): 1" in captured.out
        # A skipped item is not a failure, so it never appears in Failed URLs.
        assert "Failed URLs:" not in captured.out
        assert exit_code == 0
