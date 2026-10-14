"""HLS segment downloader with segment-level resume support."""

from __future__ import annotations

import asyncio
import hashlib
import os
import random
import shutil
import ssl
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, fields
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Final
from urllib.parse import urljoin

from structlog import get_logger

from ..config import Settings
from ..exceptions import DownloadError
from ..models.enums import QualityKind, QualityLabel
from ..models.quality import QualitySpec
from ..utils.formatting import format_bytes
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params
from .concurrency import SemaphoreLike
from .downloader_throttle import (
    _TRANSPORT_FAILURE_STATUS,
    DEFAULT_DOWNLOAD_TIMEOUT,
    build_client_timeout,
    get_shutdown_event,
)
from .extractor import _extract_video_id
from .ffmpeg_utils import _merge_segments_batched
from .quality import QualitySelector
from .retry_policies import (
    RETRYABLE_STATUS_CODES,
    _compute_backoff_delay,
    _parse_retry_after,
    _retry_429_with_backoff,
    _wait_with_shutdown,
)

if TYPE_CHECKING:
    import aiohttp

    from ..models.dtos import HLSDownloadRequest
    from ..services.extractor import VKVideoExtractor
    from .downloader_throttle import URLBackoffCoordinator


@dataclass
class SegmentTask:
    """Identity and location for a single segment download task.

    Contains the segment's position, URL, and where to save it.
    """

    idx: int
    segment_url: str
    segments_dir: Path
    total_segments: int = 1


@dataclass
class PlaylistFetchResult:
    """Result of a successful playlist fetch.

    Attributes:
        playlist_text: The raw m3u8 playlist content.
        base_url: The actual base URL the playlist was served from, which may
            differ from the requested URL after a token-refresh redirect.
    """

    playlist_text: str
    base_url: str


@dataclass
class DownloadPolicy:
    """Download policy configuration for segment downloads.

    Bundles HTTP session, rate-limiting, and retry settings.
    """

    session: aiohttp.ClientSession
    semaphore: asyncio.Semaphore
    headers: dict[str, str]
    max_concurrent_segments: int
    backoff_coordinator: URLBackoffCoordinator | None
    video_url: str
    max_retries: int
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT
    is_bounded_batch: bool = False
    m3u8_url: str = ""
    segments_dir: Path = Path()
    # DF-003: Added to enable per-segment progress reporting from
    # _download_segment_concurrent instead of only at merge time.
    progress_callback: Callable[[str, int, int], None] | None = None

    def __repr__(self) -> str:
        """Return a safe representation with sensitive headers redacted.

        SEC-008: ``headers`` is a plain ``dict[str, str]`` because aiohttp
        requires ``str`` values (the Cookie ``SecretStr`` is unwrapped at
        ``segment_downloader.py:1346``).  The dataclass-generated
        ``__repr__`` would therefore emit the raw ``Cookie`` and
        ``Authorization`` header values to any debug log or debugger
        inspection.  This override redacts those keys while letting every
        other field fall through to its normal ``repr``.
        """
        parts: list[str] = []
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if field_info.name == "headers":
                safe_headers: dict[str, str] = {
                    key: _REDACTED if key in _SENSITIVE_HEADER_KEYS else val
                    for key, val in value.items()
                }
                parts.append(f"{field_info.name}={safe_headers!r}")
            else:
                parts.append(f"{field_info.name}={value!r}")
        return f"{type(self).__name__}({', '.join(parts)})"


# SEC-008: Header keys whose values must be redacted from DownloadPolicy.__repr__.
_SENSITIVE_HEADER_KEYS: Final[frozenset[str]] = frozenset({"Cookie", "Authorization"})
_REDACTED: Final[str] = "***REDACTED***"

logger = get_logger(__name__)


def _parse_m3u8_segments(content: str) -> list[str]:
    """Parse m3u8 playlist and extract segment URLs."""
    segments = []
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            segments.append(line)
    return segments


_PLAYLIST_SIGNATURE_FILE = ".signature"
_SEGMENT_TEMP_SUFFIX: Final = ".tmp"

# Per-segment estimated size used by the download-stage free-space probe.
# HLS segments are typically 2-10 seconds of video; 2 MB is a conservative
# lower-bound estimate that lets most segments download while catching
# catastrophically undersized volumes before the fan-out begins (ART-012,
# P12-B8). The figure is an estimate — actual segment sizes vary with bitrate
# and duration — and an unreadable mount is not treated as a full one.
_DOWNLOAD_SEGMENT_BUDGET_BYTES: Final[int] = 2 * 1024 * 1024


def _compute_playlist_signature(segments: list[str]) -> str:
    """Compute a SHA-256 signature of the segment URL list.

    Used to detect playlist changes between download sessions so stale
    segments from a previous playlist are not silently reused.

    Args:
        segments: List of segment URLs from the current playlist.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    joined = "\n".join(segments)
    return hashlib.sha256(joined.encode()).hexdigest()


def _clear_stale_segments(segments_dir: Path, segments: list[str]) -> None:
    """Remove stale segment files that belong to a previous playlist.

    If the playlist signature does not match the one on disk, all ``*.ts``
    files and ``*.ts.tmp`` residue in ``segments_dir`` are stale and must be
    removed before downloading the current playlist's segments.

    Args:
        segments_dir: Directory containing downloaded segments.
        segments: List of segment URLs from the current playlist.
    """
    if not segments_dir.exists():
        return

    signature = _compute_playlist_signature(segments)
    signature_file = segments_dir / _PLAYLIST_SIGNATURE_FILE

    if signature_file.exists():
        stored = signature_file.read_text(encoding="utf-8").strip()
        if stored == signature:
            return

    stale_count = len(list(segments_dir.glob("*.ts")))
    if stale_count:
        logger.info("clearing_stale_segments", count=stale_count)
    for stale_file in segments_dir.glob("*.ts"):
        stale_file.unlink(missing_ok=True)
    for stale_temp in segments_dir.glob(f"*.ts{_SEGMENT_TEMP_SUFFIX}"):
        stale_temp.unlink(missing_ok=True)

    signature_file.write_text(signature, encoding="utf-8")


def _check_download_space(segment_count: int, segments_dir: Path) -> None:
    """Fail before the fan-out begins when the volume cannot hold the download.

    The download stage writes segment files into ``segments_dir``; if the
    volume cannot hold them the fan-out stalls far from the merge, which is the
    one place the tool already probes. This probe mirrors the merge's
    ``_check_merge_space`` shape: it raises an actionable ``DownloadError``
    naming the required and available figures, and it treats an unreadable
    mount as evidence of neither full nor empty — it logs and proceeds (ART-012,
    P12-B8).

    The demand figure is an estimate: ``segment_count`` multiplied by a
    per-segment budget. The budget is conservative (2 MB); actual segment sizes
    vary with bitrate and duration. The probe's purpose is to catch
    catastrophically undersized volumes before the fan-out, not to be precise.

    Args:
        segment_count: Number of segments the download is about to fetch.
        segments_dir: Directory the segments will be written into; the volume
            probed is the one the download will fill.

    Raises:
        DownloadError: If the volume holds less free space than the estimate.
    """
    # G5 risk (§5.1): the probe must not pre-empt the merge's own, more
    # precise check. A download-stage failure is not catastrophic — segments
    # are resumable — so an unreadable mount logs and proceeds rather than
    # blocking a download that would otherwise succeed.
    try:
        free_bytes = shutil.disk_usage(segments_dir).free
    except OSError as exc:
        logger.warning("download_space_probe_failed", error=str(exc))
        return

    required_bytes = segment_count * _DOWNLOAD_SEGMENT_BUDGET_BYTES
    if free_bytes >= required_bytes:
        return

    hint = (
        "Free disk space, write the download to another output volume, or select a "
        "lower quality so the video is smaller."
    )
    logger.error(
        "download_insufficient_disk_space",
        required_bytes=required_bytes,
        available_bytes=free_bytes,
        hint=hint,
    )
    raise DownloadError(
        f"Not enough free space to download the segments: {format_bytes(required_bytes)} "
        f"required ({required_bytes} bytes) but only {format_bytes(free_bytes)} "
        f"available ({free_bytes} bytes). {hint}"
    )


async def _download_segment_sequential(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    segment_index: int = 0,
    max_retries: int = 3,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
    *,
    backoff_coordinator: URLBackoffCoordinator | None = None,
) -> bool:
    """Download a single HLS segment with sequential retry logic.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        output_path: Path to save the downloaded segment.
        headers: Request headers to use.
        segment_index: Index of the segment being downloaded (for logging).
        max_retries: Maximum retry attempts for 429/5xx responses.
        download_timeout: Total timeout for HTTP request in seconds.
        backoff_coordinator: Optional shared URLBackoffCoordinator for pausing
            retryable transport failures on the origin before each attempt.

    Returns:
        True on success, False on failure.
    """
    shutdown_event = get_shutdown_event()

    if shutdown_event.is_set():
        return False
    if backoff_coordinator is not None:
        await backoff_coordinator.wait_if_paused(segment_url)

    content = await _retry_429_with_backoff(
        session,
        segment_url,
        headers,
        segment_index,
        max_retries=max_retries,
        download_timeout=download_timeout,
    )
    if content is not None and len(content) > 0:
        # DF-010: Write to temp file then os.replace for atomicity
        temp_path = output_path.with_suffix(output_path.suffix + _SEGMENT_TEMP_SUFFIX)
        try:
            with open(temp_path, "wb") as f:
                f.write(content)
            os.replace(temp_path, output_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        return True
    return False


def _is_retryable_status(status_code: int) -> bool:
    """Check if status code is retryable (408, 425, 429, or 5xx transport failure)."""
    return status_code in RETRYABLE_STATUS_CODES


async def _notify_backoff_for_retryable_status(
    status_code: int,
    backoff_coordinator: URLBackoffCoordinator | None,
    resource_url: str | None,
) -> None:
    """Notify backoff coordinator for retryable HTTP status codes.

    The coordinator normalizes *resource_url* internally via ``_resource_key``,
    so callers may pass the raw URL.
    """
    if backoff_coordinator and resource_url and _is_retryable_status(status_code):
        await backoff_coordinator.pause(resource_url, backoff_coordinator.pause_seconds)


def _should_continue_on_retry(
    status_code: int,
    attempt: int,
    max_retries: int,
) -> bool:
    """Check if we should continue retrying for given status code."""
    return _is_retryable_status(status_code) and attempt < max_retries - 1


async def _run_parallel_download_with_backoff(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
    attempt: int,
    max_retries: int,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
) -> bool | None:
    """Run a single download attempt in parallel mode.

    Returns True on success, None for retryable status codes, False for fatal errors.
    """
    client_timeout = build_client_timeout(download_timeout)
    async with session.get(segment_url, headers=headers, timeout=client_timeout) as response:
        if response.status == 200:
            content = await response.read()
            if len(content) == 0:
                logger.warning("empty_segment_content", segment_url=_strip_auth_params(segment_url))
                return None
            # DF-010: Write to temp file then os.replace for atomicity
            temp_path = output_path.with_suffix(output_path.suffix + _SEGMENT_TEMP_SUFFIX)
            try:
                with open(temp_path, "wb") as f:
                    f.write(content)
                os.replace(temp_path, output_path)
            except Exception:
                temp_path.unlink(missing_ok=True)
                raise
            return True

        logger.warning("segment_download_failed", status=response.status)
        await _notify_backoff_for_retryable_status(response.status, backoff_coordinator, segment_url)

        if _should_continue_on_retry(response.status, attempt, max_retries):
            retry_after_seconds = _parse_retry_after(response)
            delay = _compute_backoff_delay(response.status, attempt, retry_after_seconds)
            shutdown_event = get_shutdown_event()
            await _wait_with_shutdown(delay, shutdown_event, attempt, video_url or "unknown")
            return None

        return False


async def _check_backoff_before_attempt(
    backoff_coordinator: URLBackoffCoordinator | None,
    resource_url: str | None,
    shutdown_event: asyncio.Event,
) -> bool:
    """Check backoff state before download attempt. Returns True if should abort."""
    if backoff_coordinator and resource_url:
        was_paused = await backoff_coordinator.wait_if_paused(resource_url)
        if was_paused and shutdown_event.is_set():
            return True
    return False


async def _try_single_download_attempt(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    backoff_coordinator: URLBackoffCoordinator | None,
    video_url: str | None,
    attempt: int,
    max_retries: int,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
) -> bool | None:
    """Try a single download attempt, return True on success. Handles exceptions.

    Returns True on success, None for retryable failures (including network
    errors), False for fatal HTTP status codes (non-retryable).
    """
    import aiohttp

    try:
        return await _run_parallel_download_with_backoff(
            session,
            segment_url,
            output_path,
            headers,
            backoff_coordinator,
            video_url,
            attempt,
            max_retries,
            download_timeout=download_timeout,
        )
    except aiohttp.ClientError as e:
        logger.error("segment_download_error", error=str(e))
        return None


async def _download_segment_parallel(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    max_retries: int = 3,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_url: str | None = None,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
) -> bool:
    """Download a single HLS segment with parallel retry logic and shared backoff.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        output_path: Path to save the downloaded segment.
        headers: Request headers to use.
        max_retries: Maximum retry attempts for 429/5xx responses.
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_url: Original video URL for coordinator keying (required if coordinator provided).
        download_timeout: Total timeout for HTTP request in seconds.

    Returns:
        True on success, False on failure.
    """
    shutdown_event = get_shutdown_event()

    for attempt in range(max_retries):
        if shutdown_event.is_set():
            return False
        if await _check_backoff_before_attempt(backoff_coordinator, segment_url, shutdown_event):
            return False

        result = await _try_single_download_attempt(
            session,
            segment_url,
            output_path,
            headers,
            backoff_coordinator,
            video_url,
            attempt,
            max_retries,
            download_timeout=download_timeout,
        )
        if result is True:
            return True
        if result is False:
            # Fatal error (non-retryable HTTP status) — fail fast, no retry
            return False
        # result is None: retryable transport failure. Back off before
        # retrying instead of looping with zero delay (NET-010 parallel),
        # mirroring the _fetch_playlist_with_retry backoff pattern.
        if attempt == max_retries - 1:
            return False
        delay = _compute_backoff_delay(_TRANSPORT_FAILURE_STATUS, attempt, None)
        sanitized_url = _strip_auth_params(segment_url)
        if await _wait_with_shutdown(delay, shutdown_event, attempt, sanitized_url):
            return False
        continue

    return False


async def _download_segment(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    max_concurrent_segments: int = 1,
    segment_index: int = 0,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_url: str | None = None,
    max_retries: int = 3,
    download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
) -> bool:
    """Download a single HLS segment.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        segment_url: URL of the segment to download.
        output_path: Path to save the downloaded segment.
        headers: Request headers to use.
        max_concurrent_segments: Maximum concurrent segment downloads. When 1, uses sequential retry.
        segment_index: Index of the segment being downloaded (for logging).
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_url: Original video URL for coordinator keying (required if coordinator provided).
        max_retries: Maximum retry attempts for parallel mode on 429/5xx responses.
        download_timeout: Total timeout for HTTP request in seconds.

    Returns:
        True on success, False on failure.
    """
    if max_concurrent_segments == 1:
        return await _download_segment_sequential(
            session,
            segment_url,
            output_path,
            headers,
            segment_index=segment_index,
            max_retries=max_retries,
            download_timeout=download_timeout,
            backoff_coordinator=backoff_coordinator,
        )

    return await _download_segment_parallel(
        session,
        segment_url,
        output_path,
        headers,
        max_retries=max_retries,
        backoff_coordinator=backoff_coordinator,
        video_url=video_url,
        download_timeout=download_timeout,
    )


def _cleanup_segments(segments_dir: Path) -> None:
    """Clean up downloaded segments.

    Args:
        segments_dir: Directory containing downloaded segments.
    """
    for f in segments_dir.glob("*"):
        if not f.is_file():
            continue
        f.unlink(missing_ok=True)
    try:
        segments_dir.rmdir()
    except OSError:
        pass


async def _refresh_token_and_retry(
    video_url: str,
    extractor: VKVideoExtractor,
    settings: Settings,
    *,
    preselected_url: str,
    quality: str,
) -> tuple[str, str] | None:
    """Refresh token via browser extraction on 403/410 error.

    Returns tuple of (address, cookies) on success, None if refresh failed.

    Quality arm (D1, NET-005): for the ``best`` arm the address is selected
    from the refreshed stream set via :class:`QualitySelector`. For every
    other arm the *preselected* address — the ladder's own ``m3u8_url``,
    never the ``current_url`` that just failed with 403/410 — is returned
    so the fresh cookie is applied to an address that did not already
    exhaust the retry budget once.

    The ``settings`` parameter is retained for signature stability (B4
    four-positional contract) but is not read here.
    """
    # DF-006: Removed the `cookie_source != BROWSER` guard. The
    # `force_browser=True` parameter already bypasses the CookieSource
    # check inside extract_streams_with_cookies, matching the pattern in
    # _attempt_segment_resume (downloader.py). Token refresh was
    # impossible with the default CookieSource.NONE configuration.
    #
    # The refresh does NOT bypass B7's filter: extract_streams_with_cookies
    # → _extract_with_browser → NetworkMonitor.select(), and the returned
    # streams[0].url is addresses[0] from that same filter.
    streams, new_cookies, _raw_cookies = await extractor.extract_streams_with_cookies(
        video_url, force_browser=True
    )
    if not streams:
        return None

    selector = QualitySelector()
    quality_spec = QualitySpec.parse(quality)

    if quality_spec.kind is QualityKind.BEST:
        # D3: on the real extractor _extract_with_browser appends at most
        # one Stream, so a singleton best-select is a no-op. The record
        # below makes the arm visible; the address comes from the selector
        # over the refreshed set.
        selected = selector.select(streams, quality_spec)
        address = str(selected.url)
        selected_from = "refreshed_stream_set"
    else:
        # D1: non-best arms return the ladder's preselected address, not
        # the address that just failed (current_url).
        address = preselected_url
        selected_from = "preselected"

    # D2: one additional selection record alongside the token_expired_fetching_new
    # record emitted by the caller. quality is UNKNOWN (B7's label), not "best".
    logger.info(
        "stream_quality_selected",
        url=_strip_auth_params(address),
        quality=QualityLabel.UNKNOWN.value,
        selected_from=selected_from,
        height=None,
        width=None,
        preselected_url=_strip_auth_params(preselected_url),
    )

    return address, new_cookies or ""


async def _fetch_single_playlist(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str],
    timeout: aiohttp.ClientTimeout,
) -> tuple[str, int] | None:
    """Fetch a single playlist, returning (playlist_text, status_code) or None on error."""
    import aiohttp

    try:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status == 200:
                return await response.text(), response.status
            return "", response.status
    except (aiohttp.ClientError, TimeoutError) as e:
        logger.warning("playlist_fetch_failed", error=str(e))
        return None


async def _handle_token_refresh(
    video_url: str,
    extractor: VKVideoExtractor,
    settings: Settings,
    headers: dict[str, str],
    *,
    quality: str,
    preselected_url: str,
) -> tuple[str, str] | None:
    """Handle token refresh on 403/410 error.

    Returns (address, new_cookies) tuple on success, None on failure.
    Does not mutate the caller's headers dict; the caller is responsible
    for applying new_cookies.

    ``quality`` and ``preselected_url`` are forwarded to
    :func:`_refresh_token_and_retry` unchanged (D4: no parsing, no default).
    The four positional parameters are unchanged from B4.
    """
    return await _refresh_token_and_retry(
        video_url,
        extractor,
        settings,
        quality=quality,
        preselected_url=preselected_url,
    )


async def _fetch_playlist_with_retry(
    session: aiohttp.ClientSession,
    video_url: str,
    m3u8_url: str,
    headers: dict[str, str],
    extractor: VKVideoExtractor | None,
    settings: Settings,
    max_retries: int = 3,
    *,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    quality: str,
) -> PlaylistFetchResult | None:
    """Fetch m3u8 playlist with token refresh on 403/410 and retry on transport failures.

    Args:
        session: aiohttp ClientSession for HTTP requests.
        video_url: Original video URL for token refresh.
        m3u8_url: Initial playlist URL to fetch and preselected address (D1)
            for the non-best arm on token refresh.
        headers: Request headers (mutated on token refresh).
        extractor: Optional VKVideoExtractor for token refresh.
        settings: Application settings.
        max_retries: Maximum retry attempts.
        backoff_coordinator: Optional shared backoff coordinator for pausing
            retryable transport failures on the origin.
        quality: Requested quality token, threaded unchanged from the
            download request (D4). Parsed into a QualitySpec to select an
            arm, exactly as the yt-dlp cookie sites do, so the BEST decision
            cannot depend on the token's spelling; never defaulted here.

    Returns:
        PlaylistFetchResult with playlist text and base URL on success,
        None on failure.
    """
    current_url = m3u8_url
    client_timeout = build_client_timeout(settings.download_timeout)
    shutdown_event = get_shutdown_event()

    for attempt in range(max_retries):
        if shutdown_event.is_set():
            return None

        if backoff_coordinator is not None:
            await backoff_coordinator.wait_if_paused(current_url)

        result = await _fetch_single_playlist(session, current_url, headers, client_timeout)

        if result is None:
            logger.warning(
                "playlist_retry_transport_error",
                url=_strip_auth_params(current_url),
                attempt=attempt + 1,
                max_retries=max_retries,
            )
            if attempt == max_retries - 1:
                return None
            if backoff_coordinator is not None:
                await backoff_coordinator.pause(current_url, backoff_coordinator.pause_seconds)
            # D1: compute the exponential-backoff delay and honour shutdown
            # before looping. Manifest retry has no Retry-After, so pass None.
            delay = _compute_backoff_delay(_TRANSPORT_FAILURE_STATUS, attempt, None)
            shutdown_triggered = await _wait_with_shutdown(
                delay, shutdown_event, attempt, _strip_auth_params(current_url)
            )
            if shutdown_triggered:
                return None
            continue

        playlist_text, status = result

        if status == 200:
            return PlaylistFetchResult(playlist_text=playlist_text, base_url=current_url)

        if _is_retryable_status(status):
            logger.warning(
                "playlist_retry_status",
                url=_strip_auth_params(current_url),
                status=status,
                attempt=attempt + 1,
                max_retries=max_retries,
            )
            if attempt == max_retries - 1:
                return None
            if backoff_coordinator is not None:
                await backoff_coordinator.pause(current_url, backoff_coordinator.pause_seconds)
            # D1: compute the exponential-backoff delay and honour shutdown
            # before looping. Manifest retry has no Retry-After, so pass None.
            delay = _compute_backoff_delay(status, attempt, None)
            shutdown_triggered = await _wait_with_shutdown(
                delay, shutdown_event, attempt, _strip_auth_params(current_url)
            )
            if shutdown_triggered:
                return None
            continue

        if status in (403, 410) and extractor is not None:
            logger.info(
                "token_expired_fetching_new",
                url=_strip_auth_params(current_url),
                status=status,
                attempt=attempt + 1,
            )
            refresh_result = await _handle_token_refresh(
                video_url,
                extractor,
                settings,
                headers,
                quality=quality,
                preselected_url=m3u8_url,
            )
            if refresh_result is not None:
                current_url, new_cookies = refresh_result
                headers["Cookie"] = new_cookies
                continue
            logger.warning(
                "playlist_fetch_failed_non_retryable",
                url=_strip_auth_params(current_url),
                status=status,
                reason="token_refresh_failed",
            )
            return None

        logger.warning(
            "playlist_fetch_failed_non_retryable",
            url=_strip_auth_params(current_url),
            status=status,
            reason="non_retryable",
        )
        return None

    return None


def _create_connector(settings: Settings, video_url: str) -> aiohttp.TCPConnector:
    """Create aiohttp connector with SSL settings.

    Args:
        settings: Application settings for SSL verification.
        video_url: Video URL for logging.

    Returns:
        Configured TCPConnector.
    """
    # CON-009: both ceilings are the same setting, so limit_per_host == limit is
    # provably non-binding (aiohttp enforces min(limit, limit_per_host) only when
    # limit_per_host > 0, and acquired per-host connections are a subset of all
    # acquired). The segment semaphore stays the single binding authority and the
    # transport never clips an operator's setting. The connector is per download
    # — this is NOT a process-wide pool — so the aggregate is per-download times
    # concurrent downloads.
    import aiohttp

    connection_ceiling = settings.max_concurrent_downloads
    if settings.ssl_verify:
        return aiohttp.TCPConnector(
            limit=connection_ceiling,
            limit_per_host=connection_ceiling,
        )

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))
    return aiohttp.TCPConnector(
        ssl=ssl_context,
        limit=connection_ceiling,
        limit_per_host=connection_ceiling,
    )


_REASON_SHUTDOWN: Final = "shutdown_requested"
_REASON_CANCELLED: Final = "cancelled"


class _SegmentFanoutOutcome(StrEnum):
    """Why the segment fan-out produced its result (CON-006, CON-008, phase04/VAL-402).

    COMPLETED: the factory produced at least one task and every task settled.
    NOTHING_TO_DO: no segment was missing, so the merge must still be attempted
    from what is already on disk. Cancellation is not a member — it is raised.
    """

    COMPLETED = "completed"
    NOTHING_TO_DO = "nothing_to_do"


@dataclass(frozen=True)
class _SegmentFanoutResult:
    """``_await_and_cancel``' return value: the outcome plus the results it produced.

    ``results`` is a list, not a tuple, so it reaches ``_tally_and_merge``
    unchanged. It is empty exactly when the outcome is NOTHING_TO_DO; the
    outcome is still carried explicitly, because a consumer must not be left
    inferring the distinction from a falsy length.
    """

    outcome: _SegmentFanoutOutcome
    results: list[tuple[int, bool]]


async def _cancel_and_settle(tasks: Iterable[asyncio.Task[object]]) -> None:
    """Cancel every unfinished task and wait for all of them to settle (CON-007).

    Shared by ``_await_and_cancel`` and the segment pump so the cancellation
    contract lives in one place — phase04/VAL-402.

    Args:
        tasks: Iterable of tasks to cancel and await. Tasks already done
            are left untouched.
    """
    pending = [task for task in tasks if not task.done()]
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)


async def _await_and_cancel(
    tasks: list[asyncio.Task[tuple[int, bool]]],
) -> _SegmentFanoutResult:
    """Await segment download tasks, settling every sibling before returning or raising.

    Args:
        tasks: Download tasks to await. Each returns (segment_index, success).

    Returns:
        ``_SegmentFanoutResult`` with outcome COMPLETED and one (index, success) tuple per
        task, or outcome NOTHING_TO_DO with an empty results list when no
        segment was missing.

    Raises:
        asyncio.CancelledError if the enclosing task is cancelled, after every
        sibling is settled. Any other exception from a task is re-raised,
        also after every sibling is settled.
    """
    # CON-006: "nothing to do" is an outcome, not None — the consumer must reach
    # the merge in the resume case instead of being told the download failed.
    if not tasks:
        return _SegmentFanoutResult(_SegmentFanoutOutcome.NOTHING_TO_DO, [])

    try:
        results = await asyncio.gather(*tasks)
    except BaseException as exc:
        # CON-007: a raising part must not orphan its siblings. CON-008: a
        # cancellation is re-raised, never turned into a return value.
        await _cancel_and_settle(tasks)
        if isinstance(exc, asyncio.CancelledError):
            logger.info(
                "download_cancelled",
                reason=_REASON_SHUTDOWN if get_shutdown_event().is_set() else _REASON_CANCELLED,
            )
        raise

    return _SegmentFanoutResult(_SegmentFanoutOutcome.COMPLETED, results)


async def _tally_and_merge(
    download_results: list[tuple[int, bool]],
    segments: list[str],
    segments_dir: Path,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
    video_url: str,
) -> Path | None:
    """Tally download results and merge if all segments downloaded.

    Uses ``download_results`` to detect per-segment failures explicitly,
    falling back to filesystem count for progress reporting.

    Args:
        download_results: List of (segment_index, success) tuples from completed tasks.
        segments: List of all segment URLs.
        segments_dir: Directory containing downloaded segments.
        output_file: Final output file path.
        progress_callback: Optional callback for progress updates.
        video_url: Video URL for progress callback video_id extraction.

    Returns:
        Path to merged file on success, None otherwise.
    """
    downloaded_count = len(
        [f for f in segments_dir.glob("*.ts") if not f.name.startswith("batch_")]
    )

    if progress_callback:
        video_id = _extract_video_id(video_url)
        progress_callback(video_id, downloaded_count, len(segments))

    # Detect failed segments explicitly from download results.
    # download_results is empty on the resume path (CON-006): no segment failed
    # explicitly, so the merge is decided by the on-disk count below.
    if download_results and not all(r for _, r in download_results):
        failed_indices = [idx for idx, r in download_results if not r]
        logger.warning("segment_download_failed", failed_indices=failed_indices)
        return None

    # All segments present on disk — merge
    if downloaded_count == len(segments):
        logger.info("merging_segments", count=len(segments))
        result = await _merge_segments_batched(segments_dir, output_file, len(segments))
        if result:
            _cleanup_segments(segments_dir)
        return result

    return None


async def _process_downloaded_segments(
    segments: list[str],
    policy: DownloadPolicy,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
) -> Path | None:
    """Process downloaded segments and merge if complete.

    Uses a FIRST_COMPLETED completion pump over a counting window of
    ``max_concurrent_segments`` task objects, bounding the live task set
    by the configured ceiling (CON-003). The per-item ``async with
    policy.semaphore:`` claim stays inside ``_download_segment_concurrent``;
    the window is a ``len()`` comparison on an int — no permit object is
    created by the pump.

    Args:
        segments: List of all segment URLs.
        policy: DownloadPolicy containing HTTP session, rate-limiting, and retry settings.
        output_file: Final output file path.
        progress_callback: Optional callback for progress updates.

    Returns:
        Path to merged file on success, None otherwise.
    """
    source = _iter_pending_segment_tasks(segments, policy)

    # first is None ⇒ no missing segments ⇒ NOTHING_TO_DO. Decided before any
    # task exists, so "results is empty" and "outcome is NOTHING_TO_DO" are
    # the same event by construction (phase04/VAL-402).
    first = next(source, None)
    if first is None:
        # Delegate NOTHING_TO_DO to _await_and_cancel — single authority.
        fanout = await _await_and_cancel([])
    else:
        pending: dict[asyncio.Task[tuple[int, bool]], int] = {}
        all_done: list[asyncio.Task[tuple[int, bool]]] = []

        task = asyncio.create_task(_download_segment_concurrent(first, policy))
        pending[task] = first.idx

        try:
            for item in source:
                # Store the pulled item on the next line, never break/return
                # before storing (measured: drops one item per full window).
                if len(pending) >= policy.max_concurrent_segments:
                    done, _ = await asyncio.wait(
                        list(pending),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for completed in done:
                        pending.pop(completed, None)
                        all_done.append(completed)
                new_task = asyncio.create_task(_download_segment_concurrent(item, policy))
                pending[new_task] = item.idx

            # Drain remaining tasks after the source is exhausted.
            while pending:
                done, _ = await asyncio.wait(
                    list(pending),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for completed in done:
                    pending.pop(completed, None)
                    all_done.append(completed)
        except BaseException:
            # CON-007/CON-008: cancel any still-live tasks, then propagate.
            await _cancel_and_settle(pending.keys())
            raise

        # Every _SegmentFanoutResult is minted by _await_and_cancel;
        # all tasks are now done, so gather returns immediately.
        fanout = await _await_and_cancel(all_done)

    # Restore input order: the FIRST_COMPLETED pump completes tasks out of
    # creation order, but _tally_and_merge's failed_indices ordering in the
    # segment_download_failed warning depends on index order.
    results = fanout.results
    results.sort(key=lambda r: r[0])

    # CON-006: fall through to _tally_and_merge UNCONDITIONALLY — even
    # NOTHING_TO_DO with an empty results list must reach the merge, which
    # checks the on-disk count. Never gate on truthiness.
    return await _tally_and_merge(
        results,
        segments,
        policy.segments_dir,
        output_file,
        progress_callback,
        policy.video_url,
    )


async def _download_segment_concurrent(
    task: SegmentTask,
    policy: DownloadPolicy,
) -> tuple[int, bool]:
    """Download a segment with semaphore rate limiting.

    Args:
        task: SegmentTask containing segment identity and location.
        policy: DownloadPolicy containing HTTP session, rate-limiting, and retry settings.

    Returns:
        Tuple of (segment_index, success) where success is True on download success.
    """
    shutdown_event = get_shutdown_event()

    if shutdown_event.is_set():
        raise asyncio.CancelledError("Download cancelled by user")

    async with policy.semaphore:
        if shutdown_event.is_set():
            raise asyncio.CancelledError("Download cancelled by user")

        full_url = (
            urljoin(policy.m3u8_url, task.segment_url)
            if not task.segment_url.startswith("http")
            else task.segment_url
        )

        segment_path = task.segments_dir / f"{task.idx:05d}.ts"
        result = await _download_segment(
            policy.session,
            full_url,
            segment_path,
            policy.headers,
            max_concurrent_segments=policy.max_concurrent_segments,
            segment_index=task.idx,
            backoff_coordinator=policy.backoff_coordinator,
            video_url=policy.video_url,
            max_retries=policy.max_retries,
            download_timeout=policy.download_timeout,
        )

        # DF-003: Report per-segment progress so users see incremental
        # progress during segment downloads, not just once at merge time.
        if policy.progress_callback is not None:
            video_id = _extract_video_id(policy.video_url)
            # Count segments downloaded so far (including existing) + result
            downloaded = len(list(task.segments_dir.glob("*.ts")))
            policy.progress_callback(video_id, downloaded, task.total_segments)

        if result and not policy.is_bounded_batch and policy.max_concurrent_segments == 1:
            if shutdown_event.is_set():
                raise asyncio.CancelledError("Download cancelled by user")

            delay = 1.5 + random.uniform(0, 0.5)
            try:
                await asyncio.wait_for(shutdown_event.wait(), timeout=delay)
                raise asyncio.CancelledError("Download cancelled by user")
            except TimeoutError:
                pass

        return task.idx, result


def _iter_pending_segment_tasks(
    segments: list[str],
    policy: DownloadPolicy,
) -> Iterator[SegmentTask]:
    """Yield SegmentTask objects for missing segments only (lazy source).

    Does NOT create asyncio tasks — the caller (the segment pump in
    ``_process_downloaded_segments``) owns task creation so it can bound
    the live task set by ``max_concurrent_segments`` (CON-003).

    Skips segments whose .ts file already exists with non-zero size.

    Args:
        segments: List of segment URLs to download.
        policy: DownloadPolicy containing HTTP session, rate-limiting, and retry settings.

    Yields:
        SegmentTask objects for segments that need downloading.
    """
    for i, seg in enumerate(segments):
        segment_path = policy.segments_dir / f"{i:05d}.ts"
        if segment_path.exists() and segment_path.stat().st_size > 0:
            logger.debug("skipping_existing_segment", idx=i)
            continue
        yield SegmentTask(
            idx=i,
            segment_url=seg,
            segments_dir=policy.segments_dir,
            total_segments=len(segments),
        )


async def _run_download_session(
    m3u8_url: str,
    headers: dict[str, str],
    settings: Settings,
    segments_dir: Path,
    output_file: Path,
    progress_callback: Callable[[str, int, int], None] | None,
    video_url: str,
    extractor: VKVideoExtractor | None,
    backoff_coordinator: URLBackoffCoordinator | None,
    video_semaphore: SemaphoreLike | None,
    *,
    quality: str,
) -> Path | None:
    """Run the download session with aiohttp client.

    Creates the segments working directory ``segments_dir`` only after the
    playlist is fetched and parsed — never before the first network round-trip
    (P12-B7, ART-005 lifetime). The directory is not removed here; removal on
    every non-success exit is the caller's responsibility.

    Probes the download volume's free space before the segment fan-out begins
    (P12-B8, ART-012): if the estimated demand (segment count × per-segment
    budget) exceeds available free space, raises ``DownloadError`` before any
    segment is fetched. An unreadable mount logs and proceeds.

    Args:
        m3u8_url: HLS playlist URL.
        headers: Request headers to use.
        settings: Application settings.
        segments_dir: Directory for downloaded segments (created here, after parse).
        output_file: Final output file path.
        progress_callback: Optional callback for progress updates.
        video_url: Video URL for progress callback and coordinator keying.
        extractor: Optional extractor for token refresh.
        backoff_coordinator: Optional URLBackoffCoordinator for shared rate limiting.
        video_semaphore: The batch video permit the caller already holds. This is
            used only to detect batch context (for the ``is_bounded_batch`` flag);
            the segment fan-out is bounded by a semaphore this layer owns.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    import aiohttp

    connector = _create_connector(settings, video_url)

    async with aiohttp.ClientSession(connector=connector) as session:
        playlist_result = await _fetch_playlist_with_retry(
            session,
            video_url,
            m3u8_url,
            headers,
            extractor,
            settings,
            max_retries=settings.max_retries,
            backoff_coordinator=backoff_coordinator,
            quality=quality,
        )
        if playlist_result is None or not playlist_result.playlist_text:
            return None

        segments = _parse_m3u8_segments(playlist_result.playlist_text)
        logger.info("found_segments", count=len(segments))

        # P12-B7 (ART-005 lifetime): the segments working directory is created
        # only after the playlist is parsed and segments are enumerated — not
        # in download_hls_with_resume before the fetch. Every non-success exit
        # removes it via _cleanup_segments in download_hls_with_resume's finally.
        segments_dir.mkdir(parents=True, exist_ok=True)

        _clear_stale_segments(segments_dir, segments)

        # P12-B8 (ART-012): probe the download volume's free space before the
        # fan-out begins, mirroring _check_merge_space's shape. The demand
        # figure is a per-segment estimate; an unreadable mount logs and
        # proceeds (a failed probe must not block a download that would
        # otherwise succeed — segments are resumable, unlike the merge).
        _check_download_space(len(segments), segments_dir)

        # D-01: The batch semaphore gates *videos* (one permit per video, acquired
        # once in perform_download). asyncio.Semaphore is not reentrant: reusing the
        # caller's batch permit here for per-segment acquisition would deadlock once
        # all video permits are held, because every inner acquisition would wait on a
        # permit the same task already holds. The segment fan-out is therefore
        # bounded by a semaphore this layer owns, sized by
        # max_concurrent_segments. The live task set is further
        # bounded by a counting window of that same ceiling in the segment
        # pump (len(pending) >= policy.max_concurrent_segments), so no more
        # than max_concurrent_segments task objects exist at once (CON-003).
        # CON-009: the connector this function constructs carries the SAME value as
        # both its total and its per-origin ceiling, so limit_per_host == limit is
        # provably non-binding (the per-host term can never be the binding one —
        # acquired per-host connections are a subset of all acquired) and the
        # transport never clips an operator's setting: the segment semaphore stays
        # the single binding authority. The connector is per download — this is NOT
        # a process-wide pool — so the aggregate is per-download times concurrent
        # downloads.
        semaphore_to_use: asyncio.Semaphore = asyncio.Semaphore(settings.max_concurrent_segments)
        is_bounded_batch = video_semaphore is not None

        policy = DownloadPolicy(
            session=session,
            semaphore=semaphore_to_use,
            headers=headers,
            max_concurrent_segments=settings.max_concurrent_segments,
            backoff_coordinator=backoff_coordinator,
            video_url=video_url,
            max_retries=settings.max_retries,
            download_timeout=settings.download_timeout,
            is_bounded_batch=is_bounded_batch,
            m3u8_url=playlist_result.base_url,
            segments_dir=segments_dir,
            progress_callback=progress_callback,  # DF-003: enable per-segment progress
        )

        return await _process_downloaded_segments(
            segments,
            policy,
            output_file,
            progress_callback,
        )


async def download_hls_with_resume(
    request: HLSDownloadRequest,
    settings: Settings | None = None,
    extractor: VKVideoExtractor | None = None,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_semaphore: SemaphoreLike | None = None,
) -> Path | None:
    """
    Download HLS stream with segment-level resume and token refresh.

    Downloads original HLS segments individually, tracks progress, and can resume
    after interruption by re-downloading missing segments. Uses batched merging
    to handle large number of segments.

    Args:
        request: HLSDownloadRequest containing download parameters.
        settings: Application settings. Uses default if not provided.
        extractor: Optional VKVideoExtractor for token refresh.
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
        video_semaphore: The batch video permit the caller already holds (one
            permit per video, acquired once in ``perform_download``). This is the
            batch-level semaphore, **not** the segment-level one: the segment
            fan-out is deliberately NOT gated by it, and is bounded instead by a
            semaphore this layer owns. Passing the batch permit here would
            deadlock (see D-01): ``asyncio.Semaphore`` is not reentrant, so a
            second acquisition from the same object per segment could never be
            satisfied once all video permits are held. When ``None`` (single-download
            mode), the segment layer still creates its own local semaphore sized
            by ``settings.max_concurrent_segments``.

    Returns:
        Path to downloaded MP4 file on success, None on failure.

    Tree lifetime (P12-B7, ART-005):
        The segments working directory (``segments_dir``) is created inside
        ``_run_download_session`` only after the playlist is parsed and the
        segment list is enumerated — not before the first network fetch. On every
        non-success exit the ``finally`` block reports the tree's state via
        ``_log_preserve_segments`` and then removes it via
        ``_cleanup_segments``, so no working directory is left behind after a
        failure. ``_cleanup_segments`` handles a non-existent directory
        gracefully (the playlist-fetch-failure path returns before the tree is
        ever created).
    """
    logger.info(
        "starting_segment_download",
        url=_strip_auth_params(request.video_url),
        output=str(request.output_file),
        quality=request.quality,
    )

    if settings is None:
        settings = Settings()
    output_file = validate_output_path(request.output_file)

    segments_dir = output_file.parent / f".{output_file.stem}_segments"

    headers: dict[str, str] = {
        "User-Agent": settings.user_agent,
        "Referer": "https://vkvideo.ru/",
    }
    if request.cookies:
        # SEC-008 (B7): request.cookies is a SecretStr, not a str. An aiohttp
        # headers mapping requires str values; a SecretStr raises
        # "Cannot serialize non-str key" at the wire, so unwrap it here.
        # DOWNSTREAM: policy.headers carries plain str values from this point,
        # so _download_segment_concurrent and the four hops to session.get need
        # no further change.
        headers["Cookie"] = request.cookies.get_secret_value()

    success = False
    try:
        result = await _run_download_session(
            request.m3u8_url,
            headers,
            settings,
            segments_dir,
            output_file,
            request.progress_callback,
            request.video_url,
            extractor,
            backoff_coordinator,
            video_semaphore,
            quality=request.quality,
        )
        if result is not None:
            success = True
            return result
        return None
    finally:
        if not success:
            # P12-B7 (ART-005 lifetime): report the tree's state, then remove it
            # on every non-success exit. _log_preserve_segments runs first so the
            # reporter sees the actual count; _cleanup_segments then removes the
            # tree. _cleanup_segments handles a non-existent dir gracefully.
            _log_preserve_segments(segments_dir)
            _cleanup_segments(segments_dir)


def _log_preserve_segments(segments_dir: Path) -> None:
    """Log preserved segments for resume on exception.

    Args:
        segments_dir: Directory containing downloaded segments.
    """
    if not segments_dir.exists():
        return

    # D-13: reported on every non-success exit, count 0 included. The old
    # `count > 0` gate emitted nothing in exactly the case that mattered --
    # a total loss -- so the operator saw silence instead of "nothing was
    # kept". The count below is deliberately labelled: it is every `*.ts` in
    # the working directory, and a failed merge leaves `batch_*.ts` temps
    # there, which a `*.ts` glob cannot distinguish from segments. The merge-decision
    # count in _tally_and_merge now excludes batch_*.ts (discharged by P12-B6);
    # _log_preserve_segments itself still reports the raw working-directory count
    # as its compensating control.
    working_count = len(list(segments_dir.glob("*.ts")))
    logger.info(
        "preserving_segments_for_resume",
        working_dir=str(segments_dir),
        working_dir_ts_count=working_count,
        count_note=(
            "every *.ts file in the working directory, including any batch_*.ts "
            "merge temp a failed merge left behind; this is not a count of "
            "resumable segments"
        ),
        next_action="clear the working directory before re-running the download",
    )
