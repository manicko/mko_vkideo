"""Tests for ``perform_download`` method ladder (D-12).

Covers the FFMPEG fallback arm, the AUTO arm, and the unknown-method arm of
``perform_download`` in ``vkdownloader.services.downloader``. Each test patches
the names that ``perform_download`` re-exports from its own module namespace.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.exceptions import QualityNotAvailableError
from vkdownloader.models.dtos import HLSDownloadRequest
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
    """D-12: perform_download method-ladder coverage (FFMPEG/AUTO/unknown arms)."""

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
    async def test_ffmpeg_method_success_returns_path_without_segment_fallback(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 5: FFMPEG success returns path; segment download is NOT awaited."""
        settings = _make_settings(tmp_path, CookieSource.BROWSER)
        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader._resolve_cookies",
                new_callable=AsyncMock,
                return_value=(_M3U8, "ck", None),
            ),
            patch(
                "vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_ffmpeg,
            patch(
                "vkdownloader.services.downloader.download_hls_with_resume",
                new_callable=AsyncMock,
            ) as mock_seg,
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.FFMPEG,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )

        mock_ffmpeg.assert_awaited_once()
        mock_seg.assert_not_awaited()
        assert result == output_file

    @pytest.mark.asyncio
    async def test_ffmpeg_method_failure_falls_back_to_segment_download(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 6: FFMPEG failure (not cancelled) => segment fallback awaited with matching request; result propagates."""
        settings = _make_settings(tmp_path, CookieSource.BROWSER)
        output_file = tmp_path / "video.mp4"
        resolved_m3u8 = "https://cdn.example.com/resolved.m3u8"
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
            ),
            patch(
                "vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_ffmpeg,
            patch(
                "vkdownloader.services.downloader.download_hls_with_resume",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_seg,
            _shutdown_event_set(False),
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.FFMPEG,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )

        mock_ffmpeg.assert_awaited_once()
        mock_seg.assert_awaited_once()
        request = mock_seg.call_args.args[0]
        assert isinstance(request, HLSDownloadRequest)
        assert request.video_url == _URL
        assert request.m3u8_url == resolved_m3u8
        assert request.output_file == output_file
        assert request.quality == _QUALITY
        assert request.cookies == cookies_str
        assert result == output_file

    @pytest.mark.asyncio
    async def test_ffmpeg_method_failure_cancelled_returns_none(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 7: FFMPEG failure + shutdown set => returns None; segment fallback NOT awaited."""
        settings = _make_settings(tmp_path, CookieSource.BROWSER)
        output_file = tmp_path / "video.mp4"

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader._resolve_cookies",
                new_callable=AsyncMock,
                return_value=(_M3U8, "ck", None),
            ),
            patch(
                "vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_ffmpeg,
            patch(
                "vkdownloader.services.downloader.download_hls_with_resume",
                new_callable=AsyncMock,
            ) as mock_seg,
            _shutdown_event_set(True),
        ):
            result = await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.FFMPEG,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
            )

        mock_ffmpeg.assert_awaited_once()
        mock_seg.assert_not_awaited()
        assert result is None

    @pytest.mark.asyncio
    async def test_semaphore_forwarded_to_ytdlp_and_segment_paths_without_leak(
        self,
        tmp_path: Path,
    ) -> None:
        """D-12 case 8: shared semaphore forwarded to both ladders and fully released (no permit leak)."""
        settings = _make_settings(tmp_path, CookieSource.NONE)
        output_file = tmp_path / "video_output.mp4"
        semaphore = asyncio.Semaphore(2)
        initial = semaphore._value

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
            await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.AUTO,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
                semaphore=semaphore,
            )
        assert mock_ytdlp.call_args.kwargs["video_semaphore"] is semaphore
        assert semaphore._value == initial

        with (
            patch(
                "vkdownloader.services.downloader.check_ffmpeg_available",
                return_value=True,
            ),
            patch(
                "vkdownloader.services.downloader._resolve_cookies",
                new_callable=AsyncMock,
                return_value=(_M3U8, "ck", None),
            ),
            patch(
                "vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "vkdownloader.services.downloader.download_hls_with_resume",
                new_callable=AsyncMock,
                return_value=output_file,
            ) as mock_seg,
            _shutdown_event_set(False),
        ):
            await perform_download(
                _URL,
                _QUALITY,
                output_file,
                DownloadMethod.FFMPEG,
                settings=settings,
                video_data=_VIDEO,
                selected_stream=_STREAM,
                semaphore=semaphore,
            )
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
            patch(
                "vkdownloader.services.downloader.HLSDownloader.download_with_ffmpeg",
                new_callable=AsyncMock,
            ) as mock_ffmpeg,
            patch(
                "vkdownloader.services.downloader.download_hls_with_resume",
                new_callable=AsyncMock,
            ) as mock_seg,
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
        mock_ffmpeg.assert_not_awaited()
        mock_seg.assert_not_awaited()

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
