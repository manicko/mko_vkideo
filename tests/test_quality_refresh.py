"""RED tests for Block F — exact quality refresh without silent downgrade.

These tests describe the intended Block F contract. They are expected to fail
against the current tree because the production code has not been implemented
yet. Imports of not-yet-existing symbols are guarded with ``pytest.fail``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.config import Settings
from vkdownloader.models.enums import StreamFormat
from vkdownloader.models.video import Stream, VideoWithStreams
from vkdownloader.services.hls_parser import HLSVariantIdentity

VIDEO_URL = "https://vkvideo.ru/video-12345_67890"
OLD_URL = "https://cdn.example.com/expired/1440.m3u8?token=old"
NEW_URL = "https://cdn.example.com/fresh/1440.m3u8?token=new"


@pytest.mark.asyncio
async def test_refresh_exact_quality_uses_new_url() -> None:
    try:
        from vkdownloader.services.quality_refresh import StreamBinding, refresh_stream
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    extractor = MagicMock()
    extractor.extract_streams = AsyncMock(
        return_value=VideoWithStreams(
            id="v",
            streams=[Stream(url=NEW_URL, format=StreamFormat.HLS, quality="1440", height=1440)],
        )
    )
    previous = StreamBinding(
        media_playlist_url=OLD_URL, requested_quality="1440", actual_height=1440, variant_id="v1"
    )

    binding = await refresh_stream(VIDEO_URL, "1440", previous, extractor)

    assert binding.media_playlist_url == NEW_URL


@pytest.mark.asyncio
async def test_refresh_missing_1440_raises_quality_not_available() -> None:
    try:
        from vkdownloader.services.quality_refresh import StreamBinding, refresh_stream
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")
    try:
        from vkdownloader.exceptions import QualityNotAvailableError
    except ImportError as exc:
        pytest.fail(f"QualityNotAvailableError not available: {exc}")

    extractor = MagicMock()
    extractor.extract_streams = AsyncMock(
        return_value=VideoWithStreams(
            id="v",
            streams=[Stream(url=NEW_URL, format=StreamFormat.HLS, quality="1080", height=1080)],
        )
    )
    previous = StreamBinding(
        media_playlist_url=OLD_URL, requested_quality="1440", actual_height=1440, variant_id="v1"
    )

    with pytest.raises(QualityNotAvailableError):
        await refresh_stream(VIDEO_URL, "1440", previous, extractor)


@pytest.mark.asyncio
async def test_refresh_master_playlist_ambiguity_raises() -> None:
    try:
        from vkdownloader.services.quality_refresh import StreamBinding, refresh_stream
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")
    try:
        from vkdownloader.exceptions import QualityMismatchError
    except ImportError as exc:
        pytest.fail(f"QualityMismatchError not implemented: {exc}")

    extractor = MagicMock()
    extractor.extract_streams = AsyncMock(
        return_value=VideoWithStreams(
            id="v",
            streams=[
                Stream(
                    url="https://a.example/1440.m3u8",
                    format=StreamFormat.HLS,
                    quality="1440",
                    height=1440,
                ),
                Stream(
                    url="https://b.example/1440.m3u8",
                    format=StreamFormat.HLS,
                    quality="1440",
                    height=1440,
                ),
            ],
        )
    )
    previous = StreamBinding(
        media_playlist_url=OLD_URL, requested_quality="1440", actual_height=1440, variant_id="v1"
    )

    with pytest.raises(QualityMismatchError):
        await refresh_stream(VIDEO_URL, "1440", previous, extractor)


@pytest.mark.asyncio
async def test_refresh_unknown_height_browser_capture_rejected() -> None:
    try:
        from vkdownloader.services.quality_refresh import StreamBinding, refresh_stream
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")
    try:
        from vkdownloader.exceptions import QualityMismatchError
    except ImportError as exc:
        pytest.fail(f"QualityMismatchError not implemented: {exc}")

    extractor = MagicMock()
    extractor.extract_streams = AsyncMock(
        return_value=VideoWithStreams(
            id="v",
            streams=[
                Stream(
                    url="https://browser.example/hls.m3u8",
                    format=StreamFormat.HLS,
                    quality="unknown",
                    height=None,
                )
            ],
        )
    )
    previous = StreamBinding(
        media_playlist_url=OLD_URL, requested_quality="1440", actual_height=1440, variant_id="v1"
    )

    with pytest.raises(QualityMismatchError):
        await refresh_stream(VIDEO_URL, "1440", previous, extractor)


@pytest.mark.asyncio
async def test_refresh_loop_capped(test_settings: Settings) -> None:
    try:
        from vkdownloader.services.segment_downloader import _fetch_playlist_with_retry
    except ImportError as exc:
        pytest.fail(f"segment_downloader helper not available: {exc}")

    headers = {"User-Agent": "test"}
    refresh_calls: list[int] = []

    async def fake_refresh(*args, **kwargs):
        refresh_calls.append(1)
        return "https://example.com/refreshed.m3u8", ""

    async def fake_fetch(*args, **kwargs):
        return "", 403

    extractor = MagicMock()
    session = MagicMock()

    with patch(
        "vkdownloader.services.segment_downloader._handle_token_refresh", side_effect=fake_refresh
    ):
        with patch(
            "vkdownloader.services.segment_downloader._fetch_single_playlist",
            side_effect=fake_fetch,
        ):
            with patch("vkdownloader.services.segment_downloader.logger", MagicMock()):
                result = await _fetch_playlist_with_retry(
                    session,
                    VIDEO_URL,
                    "https://example.com/initial.m3u8",
                    headers,
                    extractor,
                    test_settings,
                    max_retries=2,
                    quality="1440",
                )

    assert result is None
    assert len(refresh_calls) <= 2


def test_refresh_quality_reordering_stable() -> None:
    try:
        from vkdownloader.services.quality_refresh import select_exact_or_fail
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    streams = [
        Stream(
            url="https://a.example/1080.m3u8", format=StreamFormat.HLS, quality="1080", height=1080
        ),
        Stream(
            url="https://b.example/1440.m3u8", format=StreamFormat.HLS, quality="1440", height=1440
        ),
    ]
    forward = select_exact_or_fail(streams, "1440")
    reversed_result = select_exact_or_fail(list(reversed(streams)), "1440")

    assert forward.url == reversed_result.url == "https://b.example/1440.m3u8"


@pytest.mark.asyncio
async def test_inexact_quality_raises_without_cleanup() -> None:
    try:
        from vkdownloader.services.quality_refresh import StreamBinding, refresh_stream
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")
    try:
        from vkdownloader.exceptions import QualityMismatchError
    except ImportError as exc:
        pytest.fail(f"QualityMismatchError not implemented: {exc}")

    extractor = MagicMock()
    extractor.extract_streams = AsyncMock(
        return_value=VideoWithStreams(
            id="v",
            streams=[
                Stream(
                    url="https://x.example/1080.m3u8",
                    format=StreamFormat.HLS,
                    quality="1080",
                    height=1080,
                )
            ],
        )
    )
    previous = StreamBinding(
        media_playlist_url=OLD_URL, requested_quality="1440", actual_height=1440, variant_id="v1"
    )

    with pytest.raises(QualityMismatchError):
        await refresh_stream(VIDEO_URL, "1440", previous, extractor)


@pytest.mark.asyncio
async def test_binding_propagates_variant_id_to_checkpoint() -> None:
    try:
        from vkdownloader.services.quality_refresh import binding_from_selected
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    from vkdownloader.services.checkpoint import JobCheckpoint

    variant = HLSVariantIdentity(
        variant_id="variant-abc",
        uri="https://example.com/1440.m3u8",
        codecs="avc1.4d401f",
        resolution="1920x1080",
    )
    binding = binding_from_selected(variant, requested_quality="1440", cookies=None)

    assert binding.variant_id == "variant-abc"

    checkpoint = JobCheckpoint(
        video_id="v",
        quality_requested="1440",
        stream_variant_id=binding.variant_id,
        playlist_fingerprint="0" * 64,
        generation_id="gen-0",
    )
    assert checkpoint.stream_variant_id == "variant-abc"


@pytest.mark.asyncio
async def test_resolve_cookies_exact_does_not_keep_expired_url() -> None:
    try:
        from vkdownloader.services.ytdlp_downloader import _resolve_cookies
    except ImportError as exc:
        pytest.fail(f"_resolve_cookies not available: {exc}")

    from vkdownloader.models.enums import CookieSource

    extractor = MagicMock()
    extractor.extract_streams = AsyncMock(
        return_value=VideoWithStreams(
            id="v",
            streams=[Stream(url=NEW_URL, format=StreamFormat.HLS, quality="1440", height=1440)],
        )
    )
    extractor.extract_streams_with_cookies = AsyncMock(
        return_value=(
            [Stream(url=NEW_URL, format=StreamFormat.HLS, quality="1440", height=1440)],
            "cookies",
            None,
        )
    )

    settings = Settings()
    settings.cookie_source = CookieSource.BROWSER

    try:
        from vkdownloader.services.quality_refresh import StreamBinding

        binding = StreamBinding(
            media_playlist_url=NEW_URL, requested_quality="1440", actual_height=1440, variant_id="v"
        )
        with patch(
            "vkdownloader.services.ytdlp_downloader.refresh_stream", AsyncMock(return_value=binding)
        ):
            result_url, _cookies, _raw = await _resolve_cookies(
                extractor, settings, VIDEO_URL, OLD_URL, "1440"
            )
    except ImportError:
        result_url, _cookies, _raw = await _resolve_cookies(
            extractor, settings, VIDEO_URL, OLD_URL, "1440"
        )

    assert result_url == NEW_URL
    assert result_url != OLD_URL


@pytest.mark.asyncio
async def test_attempt_segment_resume_exact_passes_new_url(tmp_path: Path) -> None:
    try:
        from vkdownloader.services.ytdlp_downloader import _attempt_segment_resume
    except ImportError as exc:
        pytest.fail(f"_attempt_segment_resume not available: {exc}")

    try:
        from vkdownloader.services.quality_refresh import StreamBinding
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    binding = StreamBinding(
        media_playlist_url=NEW_URL, requested_quality="1440", actual_height=1440, variant_id="v"
    )
    captured: dict[str, str] = {}

    async def fake_download(request, **kwargs):
        captured["m3u8_url"] = request.m3u8_url
        return None

    extractor = MagicMock()
    extractor.extract_streams_with_cookies = AsyncMock(return_value=([], None, None))

    output_file = tmp_path / "out.mp4"

    with patch(
        "vkdownloader.services.ytdlp_downloader.refresh_stream", AsyncMock(return_value=binding)
    ):
        with patch(
            "vkdownloader.services.ytdlp_downloader.download_hls_with_resume",
            side_effect=fake_download,
        ):
            with patch("vkdownloader.services.ytdlp_downloader.logger", MagicMock()):
                await _attempt_segment_resume(
                    VIDEO_URL,
                    OLD_URL,
                    output_file,
                    "1440",
                    0,
                    extractor,
                    Settings(),
                    None,
                )

    assert captured.get("m3u8_url") == NEW_URL


def test_stream_binding_is_frozen() -> None:
    try:
        from vkdownloader.services.quality_refresh import StreamBinding
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    binding = StreamBinding(media_playlist_url="u", requested_quality="1440")
    with pytest.raises(dataclasses.FrozenInstanceError):
        binding.media_playlist_url = "x"  # type: ignore[misc]


def test_select_exact_or_fail_matches_height() -> None:
    try:
        from vkdownloader.services.quality_refresh import select_exact_or_fail
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    streams = [
        Stream(
            url="https://a.example/1080.m3u8", format=StreamFormat.HLS, quality="1080", height=1080
        ),
        Stream(
            url="https://b.example/1440.m3u8", format=StreamFormat.HLS, quality="1440", height=1440
        ),
    ]
    selected = select_exact_or_fail(streams, "1440")
    assert selected.url == "https://b.example/1440.m3u8"


def test_select_exact_or_fail_rejects_unknown_height() -> None:
    try:
        from vkdownloader.services.quality_refresh import select_exact_or_fail
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")
    try:
        from vkdownloader.exceptions import QualityMismatchError
    except ImportError as exc:
        pytest.fail(f"QualityMismatchError not implemented: {exc}")

    streams = [
        Stream(
            url="https://u.example/hls.m3u8",
            format=StreamFormat.HLS,
            quality="unknown",
            height=None,
        )
    ]
    with pytest.raises(QualityMismatchError):
        select_exact_or_fail(streams, "1440")


def test_select_exact_or_fail_missing_height_raises() -> None:
    try:
        from vkdownloader.services.quality_refresh import select_exact_or_fail
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")
    try:
        from vkdownloader.exceptions import QualityNotAvailableError
    except ImportError as exc:
        pytest.fail(f"QualityNotAvailableError not available: {exc}")

    streams = [
        Stream(
            url="https://a.example/1080.m3u8", format=StreamFormat.HLS, quality="1080", height=1080
        )
    ]
    with pytest.raises(QualityNotAvailableError):
        select_exact_or_fail(streams, "1440")


def test_binding_from_selected_stream() -> None:
    try:
        from vkdownloader.services.quality_refresh import binding_from_selected
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    stream = Stream(
        url="https://u.example/1440.m3u8", format=StreamFormat.HLS, quality="1440", height=1440
    )
    binding = binding_from_selected(stream, requested_quality="1440", cookies="secret")
    assert binding.media_playlist_url == "https://u.example/1440.m3u8"
    assert binding.requested_quality == "1440"
    assert binding.actual_height == 1440
    assert binding.cookies == "secret"


def test_binding_from_selected_variant() -> None:
    try:
        from vkdownloader.services.quality_refresh import binding_from_selected
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")

    variant = HLSVariantIdentity(
        variant_id="variant-xyz",
        uri="https://u.example/1440.m3u8",
        codecs="avc1",
        resolution="1920x1080",
    )
    binding = binding_from_selected(variant, requested_quality="1440", cookies=None)
    assert binding.media_playlist_url == "https://u.example/1440.m3u8"
    assert binding.variant_id == "variant-xyz"
    assert binding.codecs == "avc1"


@pytest.mark.asyncio
async def test_refresh_mismatch_raises() -> None:
    try:
        from vkdownloader.services.quality_refresh import StreamBinding, refresh_stream
    except ImportError as exc:
        pytest.fail(f"quality_refresh not implemented: {exc}")
    try:
        from vkdownloader.exceptions import QualityMismatchError
    except ImportError as exc:
        pytest.fail(f"QualityMismatchError not implemented: {exc}")

    extractor = MagicMock()
    extractor.extract_streams = AsyncMock(
        return_value=VideoWithStreams(
            id="v",
            streams=[
                Stream(
                    url="https://x.example/1080.m3u8",
                    format=StreamFormat.HLS,
                    quality="1080",
                    height=1080,
                )
            ],
        )
    )
    previous = StreamBinding(
        media_playlist_url=OLD_URL, requested_quality="1440", actual_height=1440, variant_id="v1"
    )

    with pytest.raises(QualityMismatchError):
        await refresh_stream(VIDEO_URL, "1440", previous, extractor)


def test_quality_mismatch_error_code() -> None:
    try:
        from vkdownloader.exceptions import QualityMismatchError
    except ImportError as exc:
        pytest.fail(f"QualityMismatchError not implemented: {exc}")
    try:
        from vkdownloader.models.enums import ErrorCode

        code = ErrorCode.QUALITY_MISMATCH
    except (ImportError, AttributeError) as exc:
        pytest.fail(f"ErrorCode.QUALITY_MISMATCH not implemented: {exc}")

    err = QualityMismatchError("msg", requested="1440", available=["1080"], actual_height=1080)
    assert err.error_code is code
    assert err.error_code.value == "quality_mismatch"
    assert err.requested == "1440"
    assert err.available == ["1080"]
    assert err.actual_height == 1080
