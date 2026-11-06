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
from ..models.enums import DownloadState, ErrorCategory, QualityKind, QualityLabel
from ..models.quality import QualitySpec
from ..utils.diagnostics import bind_diagnostic_context
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
from .quality_refresh import (
    StreamBinding,
    binding_from_selected,
)
from .retry_policies import (
    RETRYABLE_STATUS_CODES,
    _compute_backoff_delay,
    _parse_retry_after,
    _retry_429_with_backoff,
    _wait_with_shutdown,
)
from .workspace import DownloadWorkspace

if TYPE_CHECKING:
    import aiohttp

    from ..models.dtos import HLSDownloadRequest
    from ..services.extractor import VKVideoExtractor
    from .checkpoint import JobCheckpoint
    from .downloader_throttle import URLBackoffCoordinator
    from .state_machine import DownloadStateMachine


@dataclass
class SegmentTask:
    """Identity and location for a single segment download task.

    Contains the segment's position, URL, and where to save it.
    """

    idx: int
    segment_url: str
    segments_dir: Path
    total_segments: int = 1
    byte_range: tuple[int, int] | None = None
    init_map_uri: str | None = None
    init_map_identity: str | None = None


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
    stream_binding: object | None = None
    stream_variant_id: str | None = None

    @property
    def variant_id(self) -> str | None:
        if self.stream_variant_id is not None:
            return self.stream_variant_id
        binding = self.stream_binding
        if binding is not None:
            return getattr(binding, "variant_id", None)
        return None


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
    progress_snapshot_callback: Callable[[str, object], None] | None = None
    # Block E checkpoint fields.
    # Block G raw cookies for per-host scoping.
    raw_cookies: object | None = None
    state_path: Path | None = None
    stream_variant_id: str | None = None
    video_id: str | None = None
    quality_requested: str | None = None
    playlist_fingerprint: str | None = None
    generation_id: str | None = None
    segment_durations: list[float] | None = None
    media_sequence: int | None = None
    discontinuity_sequence: int = 0
    init_map_identity: str | None = None
    init_map_sha256: str | None = None
    segment_byte_ranges: list[tuple[int, int] | None] | None = None
    codecs: str | None = None
    resolution: str | None = None
    is_live: bool = False
    endlist: bool = False
    checkpoint: JobCheckpoint | None = None
    checkpoint_lock: asyncio.Lock | None = None
    state_machine: DownloadStateMachine | None = None

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


def _reconcile_checkpoint(
    *,
    segments_dir: Path,
    state_path: Path | None = None,
    video_id: str,
    quality_requested: str,
    stream_variant_id: str,
    playlist_fingerprint: str,
    media_sequence: int | None = None,
    discontinuity_sequence: int = 0,
    init_map_identity: str | None = None,
    codecs: str | None = None,
    resolution: str | None = None,
    is_live: bool = False,
    endlist: bool = True,
    generation_id: str | None = None,
    segments: list[str] | None = None,
    checkpoint: JobCheckpoint | None = None,
) -> JobCheckpoint:
    """Verify or quarantine checkpoint, returning an active checkpoint."""
    from . import checkpoint as _cp

    segments_dir = Path(segments_dir)
    segments_dir.mkdir(parents=True, exist_ok=True)
    if state_path is None:
        state_path = segments_dir / "state.json"
    state_path = Path(state_path)

    # Recovery directory for corrupt checkpoint bytes (dated, outside job dir).
    try:
        job_id = segments_dir.parent.name
        tmp_root = segments_dir.parent.parent.parent
        recovery_dir = tmp_root / "recovery" / job_id
    except Exception:  # noqa: BLE001
        recovery_dir = segments_dir.parent / "recovery"

    existing = None
    unreadable = False
    try:
        if state_path.exists():
            existing = _cp.read_checkpoint(
                state_path, segments_dir, recovery_dir=recovery_dir, preserve=True
            )
            if existing is None:
                unreadable = True
    except Exception:  # noqa: BLE001
        existing = None
        unreadable = True

    if existing is not None:
        ok = _cp.verify_checkpoint(
            existing,
            stream_variant_id=stream_variant_id,
            playlist_fingerprint=playlist_fingerprint,
            init_map_identity=init_map_identity,
            media_sequence=media_sequence,
            discontinuity_sequence=discontinuity_sequence,
        )
        if not ok:
            # Allocate a new generation ID (gen-{n+1}) and preserve prior generation.
            try:
                prior = existing.generation_id or "gen-0"
                num = 0
                if isinstance(prior, str) and prior.startswith("gen-"):
                    try:
                        num = int(prior.split("-", 1)[1])
                    except TypeError, ValueError:
                        num = 0
                new_gen = f"gen-{num + 1}"
            except Exception:  # noqa: BLE001
                new_gen = "gen-1"
            _cp.quarantine_generation(segments_dir, existing.generation_id)
            segments_dir.mkdir(parents=True, exist_ok=True)
            generation_id = new_gen
        else:
            # Identity matches: keep checkpoint even if individual segments are
            # corrupt; _iter_pending_segment_tasks handles those.
            return existing

    if unreadable:
        # Checkpoint present but unreadable: quarantine the old generation.
        _cp.quarantine_generation(segments_dir, generation_id or "gen")
        segments_dir.mkdir(parents=True, exist_ok=True)

    gen = generation_id or "gen-0"
    new_checkpoint = _cp.JobCheckpoint(
        schema_version=_cp.CHECKPOINT_SCHEMA_VERSION,
        video_id=video_id,
        quality_requested=quality_requested,
        stream_variant_id=stream_variant_id,
        playlist_fingerprint=playlist_fingerprint,
        generation_id=gen,
        media_sequence=media_sequence,
        discontinuity_sequence=discontinuity_sequence,
        init_map_identity=init_map_identity,
        codecs=codecs,
        resolution=resolution,
        is_live=is_live,
        endlist=endlist,
        segments={},
    )
    _cp.write_checkpoint_atomic(state_path, new_checkpoint)
    return new_checkpoint


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

    # Block B: an absent signature means we have no evidence that the files on
    # disk belong to a different playlist. Preserve them (and record the current
    # signature) only when the directory holds no *.ts segments, so an empty or
    # segment-free directory is never assumed to share identity with a different
    # playlist. If *.ts files are already present, fall through to the clearing
    # branch below: identity is never assumed for unknown partials.
    if not signature_file.exists():
        has_ts = any(segments_dir.glob("*.ts"))
        if not has_ts:
            try:
                signature_file.write_text(signature, encoding="utf-8")
            except OSError:
                pass
            return
        # has_ts is True: do not return; continue to the clearing branch.

    try:
        stored = (
            signature_file.read_text(encoding="utf-8").strip() if signature_file.exists() else ""
        )
    except OSError:
        stored = ""
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
    byte_range: tuple[int, int] | None = None,
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

    if byte_range is not None:
        offset, length = byte_range
        req_headers = dict(headers)
        req_headers["Range"] = f"bytes={offset}-{offset + length - 1}"
        req_headers["Accept-Encoding"] = "identity"
        client_timeout = build_client_timeout(download_timeout)
        content = None
        try:
            async with session.get(
                segment_url, headers=req_headers, timeout=client_timeout
            ) as resp:
                if resp.status != 206:
                    return False
                cr = resp.headers.get("Content-Range", "")
                # parse bytes start-end/total
                if not cr.lower().startswith("bytes "):
                    return False
                try:
                    range_part, _total = cr[len("bytes ") :].split("/", 1)
                    start_str, end_str = range_part.split("-", 1)
                    start = int(start_str)
                    end = int(end_str)
                except ValueError, TypeError:
                    return False
                if start != offset or end != offset + length - 1:
                    return False
                payload = await resp.read()
                if len(payload) != length:
                    return False
                content = payload
        except Exception:  # noqa: BLE001
            return False
        if content is None:
            return False
        temp_path = output_path.with_suffix(output_path.suffix + _SEGMENT_TEMP_SUFFIX)
        try:
            with open(temp_path, "wb") as f:
                f.write(content)
            os.replace(temp_path, output_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise
        return True

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
        await _notify_backoff_for_retryable_status(
            response.status, backoff_coordinator, segment_url
        )

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
    byte_range: tuple[int, int] | None = None,
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
    byte_range: tuple[int, int] | None = None,
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
    if max_concurrent_segments == 1 or byte_range is not None:
        return await _download_segment_sequential(
            session,
            segment_url,
            output_path,
            headers,
            segment_index=segment_index,
            max_retries=max_retries,
            download_timeout=download_timeout,
            backoff_coordinator=backoff_coordinator,
            byte_range=byte_range,
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
        byte_range=byte_range,
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
) -> StreamBinding | None:
    """Refresh token via browser extraction on 403/410 error.

    Returns a :class:`StreamBinding` on success, ``None`` if refresh failed.

    Quality arm (D1, NET-005): for the ``best`` arm the address is selected
    from the refreshed stream set via :class:`QualitySelector`. For every other
    arm the *preselected* address -- the ladder's own ``m3u8_url``, never the
    ``current_url`` that just failed with 403/410 -- is returned so the fresh
    cookie is applied to an address that did not already exhaust the retry
    budget once. Non-best arms keep the preselected address and credentials
    without binding browser-captured stream metadata.
    """
    streams, new_cookies, raw_cookies = await extractor.extract_streams_with_cookies(
        video_url, force_browser=True
    )
    if not streams:
        return None

    selector = QualitySelector()
    quality_spec = QualitySpec.parse(quality)

    if quality_spec.kind is QualityKind.BEST:
        selected = selector.select(streams, quality_spec)
        address = str(selected.url)
        selected_from = "refreshed_stream_set"
        binding = binding_from_selected(
            selected,
            requested_quality=quality,
            cookies=new_cookies,
            raw_cookies=raw_cookies,
        )
    else:
        # D1: non-best arms return the ladder's preselected address, not
        # the address that just failed (current_url). Preserve the preselected
        # identity; do not bind browser-captured stream metadata.
        address = preselected_url
        selected_from = "preselected"
        binding = StreamBinding(
            media_playlist_url=preselected_url,
            requested_quality=quality,
            cookies=new_cookies,
            raw_cookies=raw_cookies,
        )

    logger.info(
        "stream_quality_selected",
        url=_strip_auth_params(address),
        quality=QualityLabel.UNKNOWN.value,
        selected_from=selected_from,
        height=None,
        width=None,
        preselected_url=_strip_auth_params(preselected_url),
    )

    return binding


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
) -> object | None:
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
    state_machine: DownloadStateMachine | None = None,
    preselected_variant_id: str | None = None,
    preselected_height: int | None = None,
    progress_snapshot_callback: Callable[[str, object], None] | None = None,
    raw_cookies: object | None = None,
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
    refreshed_binding = None
    refreshed_variant_id = None
    client_timeout = build_client_timeout(settings.download_timeout)
    shutdown_event = get_shutdown_event()

    if state_machine is None:
        try:
            from .extractor import _extract_video_id
            from .state_machine import DownloadStateMachine
            from .workspace import stable_job_id

            state_machine = DownloadStateMachine.create(
                job_id=stable_job_id(_extract_video_id(video_url), str(quality), "playlist.m3u8"),
                quality_requested=quality,
                workspace=None,
            )
        except Exception:  # noqa: BLE001
            state_machine = None

    for attempt in range(max_retries):
        if shutdown_event.is_set():
            return None

        if backoff_coordinator is not None:
            await backoff_coordinator.wait_if_paused(current_url)

        request_headers = dict(headers)
        _cv = _cookie_header_for_url(raw_cookies, current_url)
        if _cv:
            request_headers["Cookie"] = _cv
        result = await _fetch_single_playlist(session, current_url, request_headers, client_timeout)

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
            return PlaylistFetchResult(
                playlist_text=playlist_text,
                base_url=current_url,
                stream_binding=refreshed_binding,
                stream_variant_id=(
                    getattr(refreshed_binding, "variant_id", None)
                    if refreshed_binding is not None
                    else refreshed_variant_id
                ),
            )

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
            if state_machine is None:
                try:
                    from .extractor import _extract_video_id
                    from .state_machine import DownloadStateMachine
                    from .workspace import stable_job_id

                    state_machine = DownloadStateMachine.create(
                        job_id=stable_job_id(
                            _extract_video_id(video_url), str(quality), "playlist.m3u8"
                        ),
                        quality_requested=quality,
                        workspace=None,
                    )
                except Exception:  # noqa: BLE001
                    state_machine = None
            if state_machine is not None:
                try:
                    if not state_machine.request_refresh("token_expired"):
                        return None
                except Exception:  # noqa: BLE001
                    return None
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
                if hasattr(refresh_result, "media_playlist_url"):
                    current_url = refresh_result.media_playlist_url
                    new_cookies = getattr(refresh_result, "cookies", None)
                    if new_cookies is None:
                        new_cookies = ""
                    refreshed_binding = refresh_result
                    refreshed_variant_id = getattr(refresh_result, "variant_id", None)
                elif isinstance(refresh_result, tuple):
                    if len(refresh_result) > 0:
                        current_url = refresh_result[0]
                    new_cookies = refresh_result[1] if len(refresh_result) > 1 else ""
                    if len(refresh_result) > 2:
                        refreshed_variant_id = refresh_result[2]
                else:
                    new_cookies = ""
                raw_refreshed = (
                    getattr(refreshed_binding, "raw_cookies", None)
                    if refreshed_binding is not None
                    else None
                )
                if (
                    raw_refreshed is None
                    and isinstance(refresh_result, tuple)
                    and len(refresh_result) > 3
                ):
                    raw_refreshed = refresh_result[3]
                _cv = _cookie_header_for_url(raw_refreshed, current_url)
                if _cv:
                    headers["Cookie"] = _cv
                elif new_cookies:
                    headers["Cookie"] = new_cookies
                else:
                    headers["Cookie"] = ""
                # BG-002: compare refreshed binding against preselected identity.
                _pre_variant = refreshed_variant_id
                _pre_height = None
                if refreshed_binding is not None:
                    _pre_height = getattr(refreshed_binding, "actual_height", None)
                if state_machine is not None:
                    try:
                        quality_match = True
                        variant_match = True
                        if hasattr(refresh_result, "media_playlist_url"):
                            actual_height = getattr(refresh_result, "actual_height", None)
                            requested = str(quality).strip()
                            target_height = (
                                preselected_height if preselected_height is not None else None
                            )
                            if target_height is None and requested.isdecimal():
                                target_height = int(requested)
                            if target_height is not None and actual_height is not None:
                                quality_match = actual_height == target_height
                            new_variant = getattr(refresh_result, "variant_id", None)
                            target_variant = (
                                preselected_variant_id
                                if preselected_variant_id is not None
                                else _pre_variant
                            )
                            if target_variant is not None:
                                variant_match = new_variant == target_variant
                        if not (quality_match and variant_match):
                            try:
                                state_machine.transition(
                                    DownloadState.PRESERVE_AND_STOP,
                                    reason_code="refresh_mismatch",
                                    error_category=ErrorCategory.INTEGRITY_FAILURE,
                                )
                            except Exception:  # noqa: BLE001
                                pass
                            return None
                        state_machine.record_refresh_completed(
                            quality_match=quality_match, variant_match=variant_match
                        )
                    except Exception:  # noqa: BLE001
                        return None
                continue
            logger.warning(
                "playlist_fetch_failed_non_retryable",
                url=_strip_auth_params(current_url),
                status=status,
                reason="token_refresh_failed",
            )
            return None

        if status == 404 and state_machine is not None:
            try:
                state_machine.reverify_playlist_on_404()
            except Exception:  # noqa: BLE001
                pass
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
    checkpoint: object | None = None,
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
    segments_dir = Path(segments_dir)
    from . import checkpoint as _cp

    # Verified record count is the authority; glob count is diagnostic only.
    verified_count = 0
    if checkpoint is not None:
        try:
            verified_count = sum(
                1
                for r in getattr(checkpoint, "segments", {}).values()
                if _cp.verify_segment_record(r, segments_dir)
            )
        except Exception:  # noqa: BLE001
            verified_count = 0
    glob_count = len([f for f in segments_dir.glob("*.ts") if not f.name.startswith("batch_")])
    logger.debug("tally_glob_diagnostic", glob_count=glob_count, verified_count=verified_count)

    has_records = bool(getattr(checkpoint, "segments", None)) if checkpoint is not None else False
    if has_records:
        downloaded_count = verified_count
    else:
        downloaded_count = glob_count

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
            pass
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
        checkpoint=policy.checkpoint,
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

        request_headers = dict(policy.headers)
        _cv = _cookie_header_for_url(getattr(policy, "raw_cookies", None), full_url)
        if _cv:
            request_headers["Cookie"] = _cv

        segment_path = task.segments_dir / f"{task.idx:05d}.ts"
        result = await _download_segment(
            policy.session,
            full_url,
            segment_path,
            request_headers,
            max_concurrent_segments=policy.max_concurrent_segments,
            segment_index=task.idx,
            backoff_coordinator=policy.backoff_coordinator,
            video_url=policy.video_url,
            max_retries=policy.max_retries,
            download_timeout=policy.download_timeout,
            byte_range=task.byte_range,
        )

        # Block E: publish checkpoint entry only after a successful rename.
        if result:
            try:
                from . import checkpoint as _cp

                if policy.checkpoint is not None:
                    seg_path = segment_path
                    size = seg_path.stat().st_size
                    sha = _cp.streaming_sha256(seg_path)
                    duration = None
                    durations = policy.segment_durations
                    if durations and task.idx < len(durations):
                        duration = durations[task.idx]
                    record = _cp.SegmentRecord(
                        sequence=task.idx,
                        relative_file=seg_path.name,
                        size=size,
                        sha256=sha,
                        duration_seconds=duration,
                        byte_range=(
                            f"{task.byte_range[0]}-{task.byte_range[0] + task.byte_range[1] - 1}"
                            if task.byte_range
                            else None
                        ),
                        discontinuity_sequence=policy.discontinuity_sequence or 0,
                        media_sequence=policy.media_sequence,
                        generation_id=policy.generation_id or "gen-0",
                        init_map_sha256=getattr(policy, "init_map_sha256", None),
                    )
                    lock = policy.checkpoint_lock
                    if lock is not None:
                        async with lock:
                            _cp.upsert_segment_record(
                                policy.checkpoint,
                                str(task.idx),
                                record,
                                state_path=policy.state_path,
                                segments_dir=policy.segments_dir,
                                write=True,
                            )
                    else:
                        _cp.upsert_segment_record(
                            policy.checkpoint,
                            str(task.idx),
                            record,
                            state_path=policy.state_path,
                            segments_dir=policy.segments_dir,
                            write=True,
                        )
            except Exception as exc:  # noqa: BLE001
                logger.warning("checkpoint_publish_failed", idx=task.idx, error=str(exc))

        # DF-003: Report per-segment progress so users see incremental
        # progress during segment downloads, not just once at merge time.
        if policy.progress_callback is not None:
            video_id = _extract_video_id(policy.video_url)
            # Use checkpoint verified count when available.
            if policy.checkpoint is not None:
                try:
                    from . import checkpoint as _cp

                    downloaded = sum(
                        1
                        for r in policy.checkpoint.segments.values()
                        if _cp.verify_segment_record(r, task.segments_dir)
                    )
                except Exception:  # noqa: BLE001
                    downloaded = len(list(task.segments_dir.glob("*.ts")))
            else:
                downloaded = len(list(task.segments_dir.glob("*.ts")))
            policy.progress_callback(video_id, downloaded, task.total_segments)

        if policy.progress_snapshot_callback is not None:
            try:
                from .progress import JobPhase, ProgressSnapshot

                video_id = _extract_video_id(policy.video_url)
                if policy.checkpoint is not None:
                    try:
                        from . import checkpoint as _cp

                        verified_segments = sum(
                            1
                            for r in policy.checkpoint.segments.values()
                            if _cp.verify_segment_record(r, task.segments_dir)
                        )
                    except Exception:  # noqa: BLE001
                        verified_segments = len(list(task.segments_dir.glob("*.ts")))
                else:
                    verified_segments = len(list(task.segments_dir.glob("*.ts")))
                sm = policy.state_machine
                job_id = sm.job_state.job_id if sm is not None else video_id
                expected_segments = task.total_segments
                if sm is not None and getattr(sm.job_state, "expected_segments", None) is not None:
                    val = sm.job_state.expected_segments
                    if val is not None:
                        expected_segments = val
                verified_bytes = sm.job_state.verified_bytes if sm is not None else 0
                network_bytes = sm.job_state.network_bytes_this_session if sm is not None else 0
                attempt = sm.job_state.attempt_id if sm is not None else 0
                snapshot = ProgressSnapshot(
                    job_id=str(job_id),
                    phase=JobPhase.DOWNLOADING,
                    verified_segments=int(verified_segments or 0),
                    expected_segments=expected_segments,
                    verified_bytes_on_disk=int(verified_bytes or 0),
                    network_bytes_this_session=int(network_bytes or 0),
                    transfer_rate_bytes_per_sec=0.0,
                    eta_seconds=None,
                    is_estimate=True,
                    attempt_id=int(attempt or 0),
                    child_fragment_index=task.idx,
                    child_fragment_count=task.total_segments,
                    measured_at=__import__("time").monotonic(),
                )
                policy.progress_snapshot_callback(video_id, snapshot)
            except Exception:  # noqa: BLE001
                pass

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
        record = None
        if policy.checkpoint is not None:
            try:
                record = policy.checkpoint.segments.get(str(i))
            except Exception:  # noqa: BLE001
                record = None

        if record is not None:
            try:
                from . import checkpoint as _cp

                if _cp.verify_segment_record(record, policy.segments_dir):
                    logger.debug("skipping_verified_segment", idx=i)
                    continue
            except Exception:  # noqa: BLE001
                pass
        byte_range = None
        ranges = getattr(policy, "segment_byte_ranges", None)
        if ranges and i < len(ranges):
            byte_range = ranges[i]
        yield SegmentTask(
            idx=i,
            segment_url=seg,
            segments_dir=policy.segments_dir,
            total_segments=len(segments),
            byte_range=byte_range,
            init_map_uri=None,
            init_map_identity=policy.init_map_identity,
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
    attempt_id: int | None = None,
    diagnostic_context: object | None = None,
    state_path: Path | None = None,
    video_id: str | None = None,
    stream_variant_id: str | None = None,
    playlist_fingerprint: str | None = None,
    generation_id: str | None = None,
    state_machine: DownloadStateMachine | None = None,
    progress_snapshot_callback: Callable[[str, object], None] | None = None,
    raw_cookies: object | None = None,
) -> Path | None:
    """Run the download session with aiohttp client.

    Creates the segments working directory ``segments_dir`` only after the
    playlist is fetched and parsed - never before the first network round-trip
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

    _bind_segment_diagnostic_context(diagnostic_context)

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
            state_machine=state_machine,
            progress_snapshot_callback=progress_snapshot_callback,
            raw_cookies=raw_cookies,
        )
        if playlist_result is None or not playlist_result.playlist_text:
            return None

        if (
            stream_variant_id is None
            and getattr(playlist_result, "stream_binding", None) is not None
        ):
            stream_variant_id = getattr(playlist_result.stream_binding, "variant_id", None)
        if stream_variant_id is None:
            stream_variant_id = getattr(playlist_result, "stream_variant_id", None)

        segments_text = playlist_result.playlist_text
        base_url = playlist_result.base_url

        # Master playlist resolution (fail-closed): never treat variants as segments.
        selected_variant = None
        try:
            from . import hls_parser as _hp

            if "#EXT-X-STREAM-INF" in segments_text:
                variants = _hp.parse_master_playlist(segments_text, base_url=base_url)
                # Exact quality match: prefer resolution height equal to requested.
                selected_variant = _select_hls_variant(variants, quality)
                if selected_variant is None and variants:
                    # No exact match: fail closed rather than downgrade.
                    logger.warning("hls_variant_no_exact_match", quality=quality)
                    return None
                if selected_variant is not None:
                    # Fetch selected media playlist.
                    async with session.get(str(getattr(selected_variant, "uri", ""))) as resp:
                        if resp.status != 200:
                            return None
                        segments_text = await resp.text()
                    base_url = getattr(selected_variant, "uri", base_url)
                    if stream_variant_id is None:
                        stream_variant_id = getattr(selected_variant, "variant_id", None)
        except Exception as exc:  # noqa: BLE001
            logger.warning("hls_master_resolution_failed", error=str(exc))
            return None

        # Structured parse must succeed before any segment directory creation.
        try:
            from . import hls_parser as _hp

            media_playlist = _hp.parse_media_playlist(segments_text, base_url=base_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("hls_parse_failed", error=str(exc))
            return None

        segments = [str(s.uri) for s in media_playlist.segments]
        logger.info("found_segments", count=len(segments))

        # Fallback variant identity (non-trivial) if still missing.
        if stream_variant_id is None:
            try:
                from urllib.parse import urlparse

                host = urlparse(base_url).hostname or "unknown"
            except Exception:  # noqa: BLE001
                host = "unknown"
            import hashlib as _hl

            digest = _hl.sha256(_strip_query_token(base_url).encode("utf-8")).hexdigest()[:8]
            stream_variant_id = f"{quality}:{host}:{digest}"

        segment_durations = [s.duration for s in media_playlist.segments]
        is_live = bool(getattr(media_playlist, "is_live", False))
        endlist = bool(getattr(media_playlist, "endlist", True))
        media_sequence = getattr(media_playlist, "media_sequence", None)
        discontinuity_sequence = getattr(media_playlist, "discontinuity_sequence", 0)
        init_map_identity = getattr(media_playlist, "init_map_identity", None)
        codecs = getattr(media_playlist, "codecs", None) or (
            getattr(selected_variant, "codecs", None) if selected_variant else None
        )
        resolution = getattr(media_playlist, "resolution", None) or (
            getattr(selected_variant, "resolution", None) if selected_variant else None
        )

        # Reject live playlists fail-closed when explicitly marked live.
        if getattr(media_playlist, "playlist_type", None) == "LIVE":
            logger.warning("hls_live_playlist_unsupported")
            return None

        if stream_variant_id is None:
            stream_variant_id = f"{codecs or 'unknown'}:{resolution or 'unknown'}"
        if video_id is None:
            video_id = _extract_video_id(video_url)
        if playlist_fingerprint is None:
            try:
                from . import hls_parser as _hp

                playlist_fingerprint = _hp.compute_playlist_fingerprint(
                    media_playlist,
                    variant_id=stream_variant_id,
                    codecs=codecs,
                    resolution=resolution,
                )
            except Exception:  # noqa: BLE001
                playlist_fingerprint = f"fp:{len(segments)}"

        # Build byte-range list aligned with segments.
        segment_byte_ranges: list[tuple[int, int] | None] = []
        for s in media_playlist.segments:
            if (
                getattr(s, "byte_range_offset", None) is not None
                and getattr(s, "byte_range_length", None) is not None
            ):
                segment_byte_ranges.append(
                    (int(s.byte_range_offset or 0), int(s.byte_range_length or 0))
                )
            else:
                segment_byte_ranges.append(None)

        # Fetch + verify EXT-X-MAP before fan-out (best-effort; store hash).
        init_map_sha256 = None
        init_map_uri = getattr(media_playlist, "init_map_uri", None)
        if init_map_uri:
            try:
                async with session.get(init_map_uri) as resp:
                    if resp.status == 200:
                        map_bytes = await resp.read()
                        import hashlib as _hl

                        init_map_sha256 = _hl.sha256(map_bytes).hexdigest()
            except Exception:  # noqa: BLE001
                init_map_sha256 = None

        # P12-B7 (ART-005 lifetime): the segments working directory is created
        # only after the playlist is parsed and segments are enumerated.
        segments_dir.mkdir(parents=True, exist_ok=True)

        if state_path is None:
            state_path = segments_dir / "state.json"

        checkpoint = _reconcile_checkpoint(
            segments_dir=segments_dir,
            state_path=state_path,
            video_id=video_id or _extract_video_id(video_url),
            quality_requested=quality,
            stream_variant_id=stream_variant_id,
            playlist_fingerprint=playlist_fingerprint,
            media_sequence=media_sequence,
            discontinuity_sequence=discontinuity_sequence,
            init_map_identity=init_map_identity,
            codecs=codecs,
            resolution=resolution,
            is_live=is_live,
            endlist=endlist,
            generation_id=generation_id,
        )

        # P12-B8 (ART-012): probe the download volume's free space before the
        # fan-out begins, mirroring _check_merge_space's shape. The demand
        # figure is a per-segment estimate; an unreadable mount logs and
        # proceeds (a failed probe must not block a download that would
        # otherwise succeed — segments are resumable, unlike the merge).
        _check_download_space(len(segments), segments_dir)

        semaphore_to_use: asyncio.Semaphore = asyncio.Semaphore(settings.max_concurrent_segments)
        is_bounded_batch = video_semaphore is not None

        checkpoint_lock = asyncio.Lock()
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
            progress_callback=progress_callback,
            progress_snapshot_callback=progress_snapshot_callback,
            state_path=state_path,
            stream_variant_id=stream_variant_id,
            video_id=video_id,
            quality_requested=quality,
            playlist_fingerprint=playlist_fingerprint,
            generation_id=checkpoint.generation_id,
            segment_durations=segment_durations,
            media_sequence=media_sequence,
            discontinuity_sequence=discontinuity_sequence,
            init_map_identity=init_map_identity,
            codecs=codecs,
            resolution=resolution,
            is_live=is_live,
            endlist=endlist,
            checkpoint=checkpoint,
            checkpoint_lock=checkpoint_lock,
            state_machine=state_machine,
            segment_byte_ranges=segment_byte_ranges,
            init_map_sha256=init_map_sha256,
            raw_cookies=raw_cookies,
        )

        return await _process_downloaded_segments(
            segments,
            policy,
            output_file,
            progress_callback,
        )


def _coerce_diagnostic_context(value: object) -> dict[str, object]:
    """Coerce a diagnostic context object into a mapping of bindable fields."""
    if value is None:
        return {}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        data = value.to_dict()
    elif isinstance(value, dict):
        data = value
    else:
        data = vars(value)
    return {str(k): v for k, v in data.items() if v is not None}


def _bind_segment_diagnostic_context(value: object) -> None:
    if value is None:
        return
    try:
        bind_diagnostic_context(**_coerce_diagnostic_context(value))
    except Exception:
        pass


def _select_hls_variant(variants: object, quality: object) -> object | None:
    """Select variant by exact requested height; no downgrade."""
    variants_list = variants if isinstance(variants, (list, tuple)) else []
    if not variants_list:
        return None
    target = None
    try:
        target = int(str(quality).rstrip("p"))
    except TypeError, ValueError:
        target = None
    if target is None:
        return max(variants_list, key=lambda v: (getattr(v, "bandwidth", 0) or 0,))  # type: ignore[no-any-return]
    for v in variants_list:
        res = getattr(v, "resolution", None)
        if res:
            try:
                height = int(str(res).split("x")[-1])
            except TypeError, ValueError:
                height = None
            if height == target:
                return v  # type: ignore[no-any-return]
    return None


def _strip_query_token(url: str) -> str:
    try:
        from urllib.parse import urlsplit

        parts = urlsplit(str(url))
        return parts._replace(query="").geturl()
    except Exception:  # noqa: BLE001
        return str(url).split("?", 1)[0]


def _cookie_header_for_url(raw_cookies: object | None, url: str) -> str | None:
    """Build a Cookie header value scoped to ``url``."""
    try:
        from .cookies import scope_cookies_for_url

        scoped = scope_cookies_for_url(raw_cookies, url)
    except Exception:  # noqa: BLE001
        scoped = raw_cookies
    if scoped is None:
        return None
    if isinstance(scoped, str):
        return scoped.strip() or None
    if isinstance(scoped, list):
        parts: list[str] = []
        for cookie in scoped:
            if isinstance(cookie, dict):
                name = cookie.get("name")
                value = cookie.get("value")
            else:
                name = getattr(cookie, "name", None)
                value = getattr(cookie, "value", None)
            if name is None or value is None:
                continue
            parts.append(f"{name}={value}")
        return "; ".join(parts) or None
    return None


async def download_hls_with_resume(
    request: HLSDownloadRequest,
    settings: Settings | None = None,
    extractor: VKVideoExtractor | None = None,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_semaphore: SemaphoreLike | None = None,
    attempt_id: int | None = None,
    diagnostic_context: object | None = None,
    workspace: DownloadWorkspace | None = None,
    state_path: Path | None = None,
    video_id: str | None = None,
    stream_variant_id: str | None = None,
    playlist_fingerprint: str | None = None,
    generation_id: str | None = None,
    stream_binding: object | None = None,
    state_machine: DownloadStateMachine | None = None,
    progress_snapshot_callback: Callable[[str, object], None] | None = None,
    job_lock: object | None = None,
) -> Path | None:
    """
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
        ``_log_preserve_segments`` and PRESERVES it (no ``_cleanup_segments``),
        so partial segments remain available for resume. ``_cleanup_segments``
        runs only in ``_tally_and_merge`` after a verified merge.
    """
    _bind_segment_diagnostic_context(diagnostic_context)
    logger.info(
        "starting_segment_download",
        url=_strip_auth_params(request.video_url),
        output=str(request.output_file),
        quality=request.quality,
        attempt_id=attempt_id,
    )

    if settings is None:
        settings = Settings()
    output_file = validate_output_path(request.output_file)

    if workspace is not None:
        segments_dir = workspace.segments_dir
        merge_output = workspace.staging_dir / output_file.name
        if state_path is None:
            state_path = workspace.segment_checkpoint_path
    else:
        segments_dir = output_file.parent / f".{output_file.stem}_segments"
        merge_output = output_file
        if state_path is None:
            state_path = segments_dir / "state.json"

    if video_id is None:
        video_id = getattr(request, "video_id", None)
    if stream_variant_id is None:
        stream_variant_id = getattr(request, "stream_variant_id", None)
    if stream_variant_id is None:
        stream_binding = stream_binding or getattr(request, "stream_binding", None)
        if stream_binding is not None:
            stream_variant_id = getattr(stream_binding, "variant_id", None)
    if playlist_fingerprint is None:
        playlist_fingerprint = getattr(request, "playlist_fingerprint", None)

    headers: dict[str, str] = {
        "User-Agent": settings.user_agent,
        "Referer": "https://vkvideo.ru/",
    }
    raw_cookies = request.raw_cookies
    if raw_cookies is None and getattr(request, "stream_binding", None) is not None:
        raw_cookies = getattr(request.stream_binding, "raw_cookies", None)
    if raw_cookies is None and request.cookies:
        raw_cookies = request.cookies.get_secret_value()
    # SEC-008: base headers carry no Cookie; per-request scoping builds it.

    success = False
    try:
        result = await _run_download_session(
            request.m3u8_url,
            headers,
            settings,
            segments_dir,
            merge_output,
            request.progress_callback,
            request.video_url,
            extractor,
            backoff_coordinator,
            video_semaphore,
            quality=request.quality,
            attempt_id=attempt_id,
            diagnostic_context=diagnostic_context,
            state_path=state_path,
            video_id=video_id,
            stream_variant_id=stream_variant_id,
            playlist_fingerprint=playlist_fingerprint,
            generation_id=generation_id,
            state_machine=state_machine,
            progress_snapshot_callback=progress_snapshot_callback,
            raw_cookies=raw_cookies,
        )
        if result is not None:
            if workspace is not None:
                try:
                    from .ffmpeg_utils import check_ffprobe_available
                    from .media_validation import validate_media_file
                    from .workspace import (
                        acquire_publish_lock,
                        cleanup_owned_job_artifacts,
                        publish_verified_file,
                    )

                    expected_height = None
                    try:
                        expected_height = int(str(request.quality).rstrip("p"))
                    except TypeError, ValueError:
                        expected_height = None

                    if state_machine is not None:
                        try:
                            state_machine.transition(DownloadState.ALL_SEGMENTS_VERIFIED)
                            state_machine.transition(DownloadState.MERGING_IN_STAGING)
                            state_machine.transition(DownloadState.CANDIDATE_READY)
                            state_machine.transition(DownloadState.VALIDATING)
                        except Exception:  # noqa: BLE001
                            pass

                    if not check_ffprobe_available():
                        return None
                    try:
                        await validate_media_file(result, expected_height=expected_height)
                    except Exception:  # noqa: BLE001
                        return None

                    if state_machine is not None:
                        try:
                            state_machine.transition(DownloadState.VALIDATED)
                        except Exception:  # noqa: BLE001
                            pass

                    final_lock = acquire_publish_lock(workspace.final_path, 10.0)
                    if state_machine is not None:
                        try:
                            state_machine.transition(DownloadState.ATOMIC_NO_CLOBBER_PUBLICATION)
                        except Exception:  # noqa: BLE001
                            pass
                    publish_verified_file(result, workspace.final_path, final_lock=final_lock)
                    if job_lock is not None:
                        try:
                            job_lock.release()  # type: ignore[attr-defined]
                        except Exception:  # noqa: BLE001
                            pass
                    try:
                        await validate_media_file(
                            workspace.final_path, expected_height=expected_height
                        )
                    except Exception:  # noqa: BLE001
                        return None
                    if not (
                        workspace.final_path.exists()
                        and workspace.final_path.is_file()
                        and workspace.final_path.stat().st_size > 0
                    ):
                        return None
                    if state_machine is not None:
                        try:
                            state_machine.transition(DownloadState.FINAL_COMMITTED)
                            state_machine.transition(DownloadState.CLEANUP_OWNED_TEMP_ARTIFACTS)
                        except Exception:  # noqa: BLE001
                            pass
                    cleanup_owned_job_artifacts(workspace)
                    result = workspace.final_path
                except FileExistsError, OSError, FileNotFoundError, Exception:
                    return None
            else:
                try:
                    from .ffmpeg_utils import check_ffprobe_available
                    from .media_validation import validate_media_file

                    if result.exists() and result.is_file():
                        if not check_ffprobe_available():
                            return None
                        await validate_media_file(result)
                    _cleanup_segments(segments_dir)
                except Exception:  # noqa: BLE001
                    return None
            success = True
            return result
        return None
    finally:
        if not success:
            logger.warning(
                "job_failed_preserved",
                attempt_id=attempt_id,
                path=str(output_file),
            )
        if not success:
            # Block B: preserve partials on every non-success exit. Log only;
            # never delete the working directory here. _cleanup_segments runs
            # solely in _tally_and_merge after a verified merge.
            try:
                _log_preserve_segments(segments_dir)
            except Exception:
                # Guard so a logging failure cannot mask the original exception.
                pass


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
        next_action="resume from the preserved working directory; clear it only if segments are corrupt",
    )
