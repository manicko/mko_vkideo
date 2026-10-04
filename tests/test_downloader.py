"""Tests for ``perform_download`` method ladder (D-12).

Covers the AUTO arm, and the unknown-method arm of ``perform_download``
in ``vkdownloader.services.downloader``. Each test patches the names that
``perform_download`` re-exports from its own module namespace.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import QualityNotAvailableError
from vkdownloader.models.enums import CookieSource, DownloadMethod, StreamFormat
from vkdownloader.models.video import Stream, VideoWithStreams
from vkdownloader.services.downloader import perform_download
from vkdownloader.services.downloader_throttle import _shutdown_event_ctx

_URL = "https://vkvideo.ru/video-12345_67890"
_QUALITY = "720"
_M3U8 = "https://cdn.example.com/v.m3u8"
_STREAM = Stream(
    url=_M3U8,
    format=StreamFormat.HLS,
    quality="720p",
    height=720,
)
_VIDEO = VideoWithStreams(id="12345_67890", streams=[_STREAM])


def _make_settings(tmp_path: Path, cookie_source: CookieSource) -> Settings:
    """Build Settings with explicit kwargs so CWD/.env cannot override values."""
    return Settings(
        cookie_source=cookie_source,
        max_concurrent_downloads=2,
        download_dir=tmp_path,
    )


@contextmanager
def _shutdown_event_set(is_set: bool) -> Iterator[None]:
    """Inject a fresh, loop-bound shutdown Event for the running coroutine.

    ``get_shutdown_event`` lazily caches an ``asyncio.Event`` in a ContextVar.
    Because that Event is bound to the creating loop, it must never leak across
    tests; the token restores the prior (unset) ContextVar state on exit so a
    set Event is never left behind for another test's loop.
    """
    token = _shutdown_event_ctx.set(asyncio.Event())
    try:
        if is_set:
            _shutdown_event_ctx.get().set()
        yield
    finally:
        _shutdown_event_ctx.reset(token)


class TestPerformDownload:
    """D-12: perform_download method-ladder coverage (AUTO/unknown arms)."""

    @pytest.mark.asyncio
    async def test_auto_none_cookie_source_skips_cookie_resolution(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 1: AUTO + cookie_source=NONE skips _resolve_cookies; forwards None cookies."""
        settings = _make_settings(tmp_path, CookieSource.NONE)
        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader._resolve_cookies",
                new_callable=AsyncMock,
            ) as mock_resolve,
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_ytdlp,
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.AUTO,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )

        mock_resolve.assert_not_awaited()
        mock_ytdlp.assert_awaited_once()
        assert mock_ytdlp.call_args.args[1] == _M3U8
        assert mock_ytdlp.call_args.kwargs["cookies"] is None
        assert mock_ytdlp.call_args.kwargs["raw_cookies"] is None
        assert result == output_file

    @pytest.mark.asyncio
    async def test_auto_browser_cookie_source_resolves_and_forwards_cookies(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 2: AUTO + browser cookies resolved; (m3u8, cookies, raw) triple forwarded verbatim, m3u8 url changed."""
        settings = _make_settings(tmp_path, CookieSource.BROWSER)
        output_file = tmp_path / "video.mp4"
        changed_m3u8 = "https://cdn.example.com/v2_token.m3u8"
        cookies_str = "session=abc"
        raw_cookies = [{"name": "session", "value": "abc"}]

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader._resolve_cookies",
                new_callable=AsyncMock,
                return_value=(changed_m3u8, cookies_str, raw_cookies),
            ) as mock_resolve,
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_ytdlp,
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.AUTO,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )

        mock_resolve.assert_awaited_once()
        assert mock_resolve.call_args.args[3] == _M3U8
        mock_ytdlp.assert_awaited_once()
        assert mock_ytdlp.call_args.args[1] == changed_m3u8
        assert mock_ytdlp.call_args.kwargs["cookies"] == cookies_str
        assert mock_ytdlp.call_args.kwargs["raw_cookies"] == raw_cookies
        assert result == output_file

    @pytest.mark.asyncio
    async def test_auto_returns_ytdlp_ladder_result_path_and_none(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 3: AUTO returns exactly what the yt-dlp ladder returns (Path and None)."""
        settings = _make_settings(tmp_path, CookieSource.NONE)
        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_ytdlp,
        ):
            path_result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.AUTO,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )
        assert path_result == output_file
        mock_ytdlp.assert_awaited_once()

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_ytdlp_none,
        ):
            none_result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.AUTO,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )
        assert none_result is None
        mock_ytdlp_none.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ytdlp_method_resolves_cookies_and_propagates_result(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 4: YTDLP resolves cookies and propagates the ladder result."""
        settings = _make_settings(tmp_path, CookieSource.BROWSER)
        output_file = tmp_path / "video.mp4"
        resolved_m3u8 = "https://cdn.example.com/v.m3u8"
        cookies_str = "ck=1"
        raw_cookies = [{"name": "ck", "value": "1"}]

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader._resolve_cookies",
                new_callable=AsyncMock,
                return_value=(resolved_m3u8, cookies_str, raw_cookies),
            ) as mock_resolve,
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_ytdlp,
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.YTDLP,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )

        mock_resolve.assert_awaited_once()
        mock_ytdlp.assert_awaited_once()
        assert mock_ytdlp.call_args.kwargs["cookies"] == cookies_str
        assert result == output_file

    @pytest.mark.asyncio
    async def test_semaphore_forwarded_to_yt_dlp_and_segment_paths_without_leak(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12: video_semaphore forwarded to the yt-dlp ladder and the segment
        path; fully released (no permit leak).

        ``perform_download`` (AUTO arm) forwards the semaphore to
        ``download_with_ytdlp_with_resume_fallback`` — the yt-dlp ladder, pinned
        through the full ``perform_download`` entry point here.

        The segment path (``download_hls_with_resume``) is only reached from
        ``_attempt_segment_resume``, which is reached from inside
        ``download_with_ytdlp_with_resume_fallback`` after a yt-dlp failure when a
        partial file exists. Since this unit test mocks the outer
        ``download_with_ytdlp_with_resume_fallback`` entry point, that inner path
        is unreachable through ``perform_download`` here. The segment-path
        semaphore assertion is therefore re-anchored at
        ``_attempt_segment_resume`` — the layer that actually passes
        ``video_semaphore`` to ``download_hls_with_resume`` — rather than left
        as a second redundant yt-dlp assertion.
        """
        from vkdownloader.services.ytdlp_downloader import _attempt_segment_resume

        settings = _make_settings(tmp_path, CookieSource.NONE)
        output_file = tmp_path / "video_output.mp4"
        semaphore = asyncio.Semaphore(2)
        initial = semaphore._value

        # --- yt-dlp ladder: perform_download forwards the semaphore ---
        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_ytdlp,
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.AUTO,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
                semaphore=semaphore,
            )

        assert result == output_file
        assert mock_ytdlp.call_args.kwargs["video_semaphore"] is semaphore
        assert semaphore._value == initial

        # --- segment path: _attempt_segment_resume forwards to download_hls_with_resume ---
        seg_output = tmp_path / "segment_output.mp4"
        seg_output.write_bytes(b"partial data")

        stream = Stream(
            url="https://example.com/fresh.m3u8",
            format=StreamFormat.HLS,
            quality="best",
            height=1080,
        )
        mock_extractor = MagicMock()
        mock_extractor.extract_streams_with_cookies = AsyncMock(return_value=([stream], None, None))

        with patch(
            "vkdownloader.services.ytdlp_downloader.download_hls_with_resume",
            new_callable=AsyncMock,
            return_value=seg_output,
        ) as mock_seg:
            seg_result = await _attempt_segment_resume(
                _URL,
                _M3U8,
                seg_output,
                "1080",
                retry_count=1,
                extractor=mock_extractor,
                settings=settings,
                backoff_coordinator=None,
                video_semaphore=semaphore,
            )

        assert seg_result == seg_output
        assert mock_seg.call_args.kwargs["video_semaphore"] is semaphore
        assert semaphore._value == initial

    @pytest.mark.asyncio
    async def test_semaphore_none_completes_normally(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 9: semaphore=None (nullcontext path) completes normally."""
        settings = _make_settings(tmp_path, CookieSource.NONE)
        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_ytdlp,
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.AUTO,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
                semaphore=None,
            )

        mock_ytdlp.assert_awaited_once()
        assert mock_ytdlp.call_args.kwargs.get("video_semaphore") is None
        assert result == output_file

    @pytest.mark.asyncio
    async def test_unknown_method_returns_none_without_raising(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 10: unrecognized DownloadMethod value returns None without raising."""
        settings = _make_settings(tmp_path, CookieSource.NONE)
        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader._resolve_cookies",
                new_callable=AsyncMock,
            ) as mock_resolve,
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
            ) as mock_ytdlp,
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                cast(DownloadMethod, "not-a-real-method"),
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )

        assert result is None
        mock_resolve.assert_not_awaited()
        mock_ytdlp.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_extraction_empty_streams_raises_quality_not_available(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 11: extraction returns zero streams => QualityNotAvailableError; no downloader called."""
        settings = _make_settings(tmp_path, CookieSource.NONE)
        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader.VKVideoExtractor.extract_streams",
                new_callable=AsyncMock,
                return_value=VideoWithStreams(id="12345_67890", streams=[]),
            ),
            patch(
                "vkdownloader.services.downloader.download_with_ytdlp_with_resume_fallback",
                new_callable=AsyncMock,
            ) as mock_ytdlp,
            patch(
                "vkdownloader.services.downloader.download_hls_with_resume",
                new_callable=AsyncMock,
            ) as mock_seg,
        ):
            with pytest.raises(QualityNotAvailableError):
                await perform_download(
                    _URL,
                    _QUALITY,
                    output_file,
                    DownloadMethod.AUTO,
                    settings=settings,
                )

        mock_ytdlp.assert_not_awaited()
        mock_seg.assert_not_awaited()
