"""yt-dlp subprocess download with cookie-file lifecycle and resume fallback."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.async_api import Cookie
from structlog import get_logger

from ..config import Settings
from ..exceptions import ExtractionError, QualityNotAvailableError, QualityParseError
from ..models.dtos import HLSDownloadRequest
from ..models.enums import CookieSource, QualityEnum
from ..services.cookies import _cookies_to_netscape
from ..services.downloader_throttle import (
    _compute_backoff_delay,
    _wait_with_shutdown,
    get_shutdown_event,
)
from ..services.extractor import VKVideoExtractor
from ..services.ffmpeg_utils import cancel_subprocess, iter_process_lines
from ..services.quality import QualitySelector
from ..services.segment_downloader import download_hls_with_resume
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params, sanitize_text_for_log

if TYPE_CHECKING:
    from ..services.concurrency import SemaphoreLike
    from .downloader_throttle import URLBackoffCoordinator

logger = get_logger(__name__)


def _create_temp_cookie_file(cookies: str | list[Cookie]) -> Path:
    """Create a temporary Netscape cookie file in the system temp directory.

    Unlike writing to the download output directory (which may be cloud-synced),
    the system temp directory is private and not synced, reducing the risk of
    live session-cookie leakage on abnormal termination.

    Args:
        cookies: Either a raw cookie string (Netscape format) or a list of
            Playwright Cookie objects.

    Returns:
        Path to the temporary cookie file (mode 0o600, applied on POSIX; see
        D-11). The caller is responsible for cleanup.
    """
    content = _cookies_to_netscape(cookies)
    fd, path = tempfile.mkstemp(suffix=".cookies.txt", prefix="vk_cookies_")
    # QLT-004: Always close the fd in `finally` BEFORE unlinking the file.
    # On Windows, an open fd locks the file and unlink will silently fail.
    # Suppressing close errors prevents masking the original write error.
    write_error: OSError | None = None
    try:
        os.write(fd, content.encode())
    except OSError as exc:
        write_error = exc
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    if write_error is not None:
        Path(path).unlink(missing_ok=True)
        raise write_error
    # DF-007: Explicitly set 0o600 permissions. tempfile.mkstemp creates
    # files subject to the process umask (typically 0o644 on Unix),
    # exposing live session cookies to other local users if the process
    # crashes before cleanup. 0o600 sets POSIX permission bits: on Windows
    # os.chmod toggles only the read-only attribute, so the owner-only
    # guarantee is not offered there (D-11) and the mode is requested for
    # its POSIX effect only.
    os.chmod(path, 0o600)
    return Path(path)


async def _await_first_and_cancel_others(
    *tasks: asyncio.Task[Any],
) -> tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]:
    """Launch tasks concurrently, await first completion, cancel remaining.

    Args:
        *tasks: Tasks to await concurrently.

    Returns:
        Tuple of (done_tasks, pending_tasks) after cancellation.
    """
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED,
    )
    # Cancel pending tasks
    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return done, pending


def _parse_quality_to_enum(quality: str) -> QualityEnum:
    """Parse quality string to QualityEnum for stream selection.

    Args:
        quality: Quality string (e.g., "720", "1080", "best", "worst", "720p").

    Returns:
        QualityEnum value matching the string.

    Raises:
        QualityParseError: If quality string cannot be parsed to QualityEnum.
    """
    try:
        return QualityEnum(quality)
    except ValueError:
        normalized = quality.rstrip("p") if quality else "best"
        try:
            return QualityEnum(normalized)
        except ValueError:
            raise QualityParseError(quality) from None


# yt-dlp progress line format (with --newline):
#   [download]  40.3% of 649.37MiB at 983.45KiB/s ETA 06:43
#
# yt-dlp produces several ETA formats depending on the calculated value:
#   - MM:SS        e.g. "06:43"         (eta < 1 hour)
#   - HH:MM:SS     e.g. "01:01:00"      (1h <= eta <= 99h)
#   - --:--:--     (eta > 99h or unknown, e.g. very large file / slow speed)
#   - "Unknown"    (speed is 0, eta not yet calculated)
#
# Speed can also be "Unknown B/s" right after start.  The regex uses
# permissive patterns for speed/eta because _parse_ytdlp_progress() only
# reads pct, size, and size_unit -- speed/eta groups exist for clarity only.
_YTDLP_PROGRESS_RE = re.compile(
    r"\[download\]\s+"
    r"(?P<pct>\d+(?:\.\d+)?)%"
    r"\s+of\s+"
    r"(?P<size>\d+(?:\.\d+)?)"
    r"(?P<size_unit>[KMG]?i?B)"
    r"\s+at\s+"
    r"(?P<speed>.+?)"
    r"\s+ETA\s+"
    r"(?P<eta>\S+)"
)

# Size unit multipliers to bytes
_SIZE_UNITS: dict[str, int] = {
    "B": 1,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
}


def _parse_ytdlp_progress(line: str) -> tuple[int, int] | None:
    """Parse a yt-dlp progress line into (downloaded_bytes, total_bytes).

    yt-dlp with ``--newline`` writes lines like::

        [download]   40.3% of 649.37MiB at 983.45KiB/s ETA 06:43
        [download]   0.0% of    4.93GiB at   10.37KiB/s ETA --:--:--

    Args:
        line: A decoded stderr line from the yt-dlp subprocess.

    Returns:
        Tuple of (downloaded_bytes, total_bytes) if the line matches the
        yt-dlp download-progress pattern, otherwise ``None``.
    """
    match = _YTDLP_PROGRESS_RE.search(line)
    if match is None:
        return None
    pct = float(match.group("pct"))
    size = float(match.group("size"))
    size_unit = match.group("size_unit")
    multiplier = _SIZE_UNITS.get(size_unit, 1)
    total = int(size * multiplier)
    downloaded = int(total * pct / 100)
    return downloaded, total


def _echo_ytdlp_line(line: str, *, echo: bool = True) -> None:
    """Echo a yt-dlp output line to the console.

    Progress lines (e.g. ``[download]  40.3% of 649.37MiB ...``) are
    rewritten in-place using carriage returns to restore the
    pre-migration behavior where yt-dlp used ``\\r`` for live progress
    updates.  Non-progress lines use newlines as-is.

    When ``echo`` is ``False`` (batch mode), nothing is written to stderr
    at all — progress data is emitted at DEBUG level instead and
    non-progress lines are dropped silently, so yt-dlp output never
    interleaves with the rich progress display.
    """
    if not echo:
        progress = _parse_ytdlp_progress(line)
        if progress is not None:
            downloaded, total = progress
            logger.debug(
                "ytdlp_progress_suppressed",
                downloaded=downloaded,
                total=total,
            )
        return
    if _parse_ytdlp_progress(line) is not None:
        text = line.rstrip("\n\r")
        width = shutil.get_terminal_size((80, 24)).columns
        sys.stderr.write("\r" + text.ljust(width)[:width] + "\r")
        sys.stderr.flush()
    else:
        sys.stderr.write(line)
        sys.stderr.flush()


def _build_ytdlp_cli_command(
    output_file: Path,
    quality_str: str,
    user_agent: str,
    settings: Settings,
    cookies: str | None,
    raw_cookies: list[Cookie] | None,
) -> tuple[list[str], Path | None]:
    """Build a yt-dlp CLI command list and optional temp cookie file path.

    The command is executed via ``asyncio.create_subprocess_exec`` so the
    yt-dlp process can be properly terminated on cancellation or shutdown.

    Args:
        output_file: Path to save the downloaded video.
        quality_str: Quality string without ``p`` suffix (e.g., ``"720"``).
        user_agent: User agent string for HTTP requests.
        settings: Application settings.
        cookies: Optional raw cookie string (Netscape format) for backward compat.
        raw_cookies: Optional list of Playwright Cookie objects for Netscape format.

    Returns:
        Tuple of (command list, cookie_file Path or None).
    """
    # Build format selector: use height filter for numeric quality, bare "best" otherwise
    format_selector = (
        f"best[height<={quality_str}]" if quality_str and quality_str.isdigit() else "best"
    )

    cmd: list[str] = [
        sys.executable,
        "-u",  # Unbuffered stderr — critical for real-time progress passthrough with PIPE
        "-m",
        "yt_dlp",
        "--encoding",
        "utf-8",
        "-o",
        str(output_file),
        "-f",
        format_selector,
        "--newline",
        "--hls-prefer-native",
        "--no-warnings",
        "--socket-timeout",
        str(settings.download_timeout),
        "-R",
        str(settings.max_retries),
        "--fragment-retries",
        str(settings.max_retries),
        "-N",
        str(settings.max_concurrent_downloads),
        "--throttled-rate",
        str(settings.throttled_rate),
        "--user-agent",
        user_agent,
        "--referer",
        "https://vkvideo.ru/",
    ]

    # --http-chunk-size forces range-request-based downloading of HLS segments.
    # When enabled (> 0), it can cause silent data corruption on CDNs that do not
    # properly support HTTP Range headers, producing files with corrupted segments
    # ("broken chunks in the middle"). Disabled by default (0) for reliability.
    # Only include when explicitly enabled by the user.
    if settings.http_chunk_size > 0:
        cmd.extend(["--http-chunk-size", str(settings.http_chunk_size)])

    if not settings.ssl_verify:
        cmd.append("--no-check-certificates")

    # Add cookies file if cookies are provided
    cookie_file: Path | None = None
    if raw_cookies:
        cookie_file = _create_temp_cookie_file(raw_cookies)
        cmd.extend(["--cookies", str(cookie_file)])
    elif cookies:
        cookie_file = _create_temp_cookie_file(cookies)
        cmd.extend(["--cookies", str(cookie_file)])

    return cmd, cookie_file


async def download_with_ytdlp_with_resume_fallback(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    extractor: VKVideoExtractor | None,
    settings: Settings | None = None,
    cookies: str | None = None,
    raw_cookies: list[Cookie] | None = None,
    *,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    video_semaphore: SemaphoreLike | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    echo: bool = True,
) -> Path | None:
    """Download using yt-dlp with automatic segment-based fallback on failure.

    Flow:
    1. Try yt-dlp download
    2. On failure with partial file: get fresh token via browser + switch to segment download
    3. Falls back to a fresh segment-based download via HLS; the partial yt-dlp file is discarded

    Args:
        video_url: Original VK video URL.
        m3u8_url: HLS playlist URL (may be stale).
        output_file: Output file path.
        quality: Quality string.
        extractor: VKVideoExtractor for token refresh.
        settings: Application settings.
        cookies: Optional cookies string for ffmpeg headers.
        raw_cookies: Optional raw Cookie objects for Netscape format (preserves domain).
        backoff_coordinator: Optional shared URLBackoffCoordinator for rate limiting.
            Used both for inter-retry backoff between yt-dlp attempts and for
            coordinating backoff during segment-resume fallback.
        video_semaphore: The batch video permit the caller already holds (one permit per
            video, acquired once in ``perform_download``). This is the batch-level
            semaphore, **not** the segment-level one: the segment fan-out is deliberately
            NOT gated by it and is bounded by a semaphore the segment layer owns. Re-
            acquiring from this non-reentrant semaphore per segment would deadlock (D-01).
            When ``None`` (single-download mode), no video-level permit is in effect.
        progress_callback: Optional callback for per-URL segment progress (video_id, downloaded, total).
        echo: When False, suppresses yt-dlp's native console echo (progress lines
            are emitted at DEBUG level instead; non-progress lines are dropped).
            Only governs yt-dlp output — has no effect on the ffmpeg or segment paths.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    if settings is None:
        settings = Settings()

    shutdown_event = get_shutdown_event()
    retry_count = 0

    while retry_count <= settings.max_retries:
        result = await _download_with_ytdlp(
            video_url,
            output_file,
            quality,
            settings,
            cookies,
            raw_cookies,
            progress_callback,
            echo=echo,
        )

        if result:
            if retry_count > 0:
                logger.info("download_completed_after_retries", retries=retry_count)
            return result

        retry_count += 1

        if shutdown_event.is_set():
            logger.info(
                "yt_dlp_download_cancelled",
                url=_strip_auth_params(video_url),
            )
            return None

        # Backoff between yt-dlp retry attempts (SRV-006):
        # Without this, the retry loop hammers the VK origin on failure.
        # Use _compute_backoff_delay with a 500 base status (yt-dlp failures
        # don't carry an HTTP status at this level); _wait_with_shutdown
        # respects the shared URLBackoffCoordinator's pause state if one is
        # provided, and allows interruption via the shutdown event.
        backoff_delay = _compute_backoff_delay(500, retry_count, None)
        if backoff_coordinator is not None:
            await backoff_coordinator.wait_if_paused(video_url)
        shutdown_triggered = await _wait_with_shutdown(
            backoff_delay,
            shutdown_event,
            retry_count,
            _strip_auth_params(video_url),
        )
        if shutdown_triggered:
            logger.info(
                "yt_dlp_download_cancelled_during_backoff", url=_strip_auth_params(video_url)
            )
            return None

        # Check for partial file - switch to segment download with fresh token
        validated_output = validate_output_path(output_file, warning=False)
        if not validated_output.exists() or validated_output.stat().st_size == 0:
            return None

        # Attempt segment resume with fresh token
        if (
            segment_result := await _attempt_segment_resume(
                video_url,
                m3u8_url,
                validated_output,
                quality,
                retry_count,
                extractor,
                settings,
                backoff_coordinator,
                video_semaphore,
                progress_callback,
            )
        ) is not None:
            return segment_result

    # All retries exhausted without success
    logger.error(
        "max_retries_exceeded",
        url=_strip_auth_params(video_url),
        retries=settings.max_retries,
    )
    # DF-008: Clean up partial output file left by yt-dlp on failure
    try:
        validated_output.unlink(missing_ok=True)
    except OSError:
        logger.warning("failed_to_cleanup_partial_file", path=str(validated_output))
    return None


async def _attempt_segment_resume(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    retry_count: int,
    extractor: VKVideoExtractor | None,
    settings: Settings,
    backoff_coordinator: URLBackoffCoordinator | None,
    video_semaphore: SemaphoreLike | None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> Path | None:
    """Attempt segment-based download with fresh token on yt-dlp failure.

    Called when yt-dlp fails and partial file exists. Forces browser extraction
    to get fresh token, then falls back to a fresh segment-based download via HLS.
    The partial yt-dlp file is discarded; segment download starts from the beginning.

    Args:
        video_url: Original VK video URL.
        m3u8_url: HLS playlist URL (may be stale).
        output_file: Output file path (partial file is discarded, segment download starts fresh).
        quality: Quality string.
        retry_count: Current retry attempt number.
        extractor: VKVideoExtractor for token refresh.
        settings: Application settings.
        backoff_coordinator: Optional shared URLBackoffCoordinator.
        video_semaphore: The batch video permit the caller already holds (one permit per
            video, acquired once in ``perform_download``). The segment fan-out is NOT
            gated by it; the segment layer owns its own semaphore (D-01).
        progress_callback: Optional callback for per-URL segment progress.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    logger.warning(
        "download_interrupted_switching_to_segments",
        url=_strip_auth_params(video_url),
        path=str(output_file),
        size=output_file.stat().st_size,
        retry=retry_count,
    )
    logger.info("attempting_segment_resume", retry=retry_count)

    try:
        if extractor is None:
            extractor = VKVideoExtractor(settings=settings)
        # Force browser for token refresh during resume (recovery scenario)
        browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(
            video_url, force_browser=True
        )
        if browser_streams:
            try:
                quality_enum = _parse_quality_to_enum(quality)
                # Browser streams always have quality="best" with height=None.
                # Only run quality selection for BEST; for numeric qualities, reuse the
                # pre-selected m3u8_url from the caller (yt-dlp already selected the stream).
                if quality_enum == QualityEnum.BEST:
                    selector = QualitySelector()
                    selected_stream = selector.select(browser_streams, quality_enum)
                    m3u8_url = str(selected_stream.url)
                    logger.info(
                        "fresh_token_obtained_for_resume",
                        quality=quality,
                        selected_quality=selected_stream.quality,
                    )
                else:
                    logger.info(
                        "browser_streams_selected_with_preselected_url_for_resume",
                        quality=quality,
                        m3u8_url=_strip_auth_params(m3u8_url),
                    )
            except QualityNotAvailableError:
                logger.error(
                    "requested_quality_not_available_in_browser_streams",
                    url=_strip_auth_params(video_url),
                    quality=quality,
                    available=[s.quality for s in browser_streams],
                )
                raise
            # Remove partial file to start clean segment download
            output_file.unlink()
            # Continue to segment download
            return await download_hls_with_resume(
                HLSDownloadRequest(
                    video_url=video_url,
                    m3u8_url=m3u8_url,
                    output_file=output_file,
                    quality=quality,
                    cookies=cookies,
                    progress_callback=progress_callback,
                ),
                settings=settings,
                extractor=extractor,
                backoff_coordinator=backoff_coordinator,
                video_semaphore=video_semaphore,
            )
    except (ExtractionError, OSError) as e:
        logger.warning(
            "failed_to_refresh_token",
            url=_strip_auth_params(video_url),
            error=str(e),
        )
    except ValueError as e:
        logger.error(
            "invalid_quality_for_browser_streams",
            url=_strip_auth_params(video_url),
            error=str(e),
        )
        raise

    return None


async def _download_with_ytdlp(
    video_url: str,
    output_file: Path,
    quality: str,
    settings: Settings,
    cookies: str | None = None,
    raw_cookies: list[Cookie] | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    *,
    echo: bool = True,
) -> Path | None:
    """Download video using yt-dlp via subprocess.

    Uses ``asyncio.create_subprocess_exec`` instead of ``run_in_executor``
    so the yt-dlp process can be properly terminated (SIGTERM -> SIGKILL)
    on cancellation or shutdown. yt-dlp has its own ``--socket-timeout``,
    ``-R`` (retries), ``--fragment-retries``, and ``-N`` (concurrent
    fragments) for network robustness — no application-level download
    timeout is imposed, avoiding premature kill of legitimate long downloads.

    Args:
        video_url: VK video URL to download.
        output_file: Path to save the downloaded video.
        quality: Quality string (e.g., "720", "1080").
        settings: Application settings.
        cookies: Optional cookies string for backward compatibility.
        raw_cookies: Optional raw Cookie objects for Netscape format.
        progress_callback: Optional callback for per-URL progress updates.
        echo: When False, suppresses yt-dlp's native console echo (progress lines
            are emitted at DEBUG level instead; non-progress lines are dropped).
            Only governs yt-dlp output — has no effect on the ffmpeg or segment paths.

    Returns:
        Path to the output file on success, None on failure.
    """
    logger.info(
        "starting_ytdlp_download",
        url=_strip_auth_params(video_url),
        output=str(output_file),
        quality=quality,
    )

    quality_str = quality.replace("p", "") if quality else "720"
    user_agent = settings.user_agent
    video_id = video_url.split("_")[-1] if "_" in video_url else video_url
    shutdown_event = get_shutdown_event()

    if not settings.ssl_verify:
        logger.warning("ssl_verification_disabled", url=_strip_auth_params(video_url))

    cmd, cookie_file = _build_ytdlp_cli_command(
        output_file,
        quality_str,
        user_agent,
        settings,
        cookies,
        raw_cookies,
    )
    # yt-dlp takes the URL as its final positional argument
    cmd.append(video_url)

    # yt-dlp writes progress and most output to stdout by default (confirmed
    # empirically). Using stdout=PIPE + stderr=STDOUT merges all output into a
    # single stream, avoiding dual-pipe deadlock complexity while preserving
    # error messages for structured logging on failure.
    process: asyncio.subprocess.Process | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_chunks: list[bytes] = []

        async def _on_shutdown() -> None:
            if not await cancel_subprocess(process):
                logger.warning(
                    "yt_dlp_cancel_not_clean",
                    pid=process.pid,
                    url=_strip_auth_params(video_url),
                )

        async def _monitor_progress() -> None:
            """Read stdout, parse yt-dlp progress, invoke callback."""
            assert process.stdout is not None
            async for line in iter_process_lines(
                process.stdout, shutdown_event, on_shutdown=_on_shutdown
            ):
                decoded = line.decode(errors="replace")
                _echo_ytdlp_line(decoded, echo=echo)
                output_chunks.append(line)
                progress = _parse_ytdlp_progress(decoded)
                if progress is not None and progress_callback is not None:
                    downloaded, total = progress
                    progress_callback(video_id, downloaded, total)

        async def _drain_output() -> None:
            """Drain stdout to prevent buffer deadlock when no callback."""
            assert process.stdout is not None
            async for line in iter_process_lines(
                process.stdout, shutdown_event, on_shutdown=_on_shutdown
            ):
                decoded = line.decode(errors="replace")
                _echo_ytdlp_line(decoded, echo=echo)
                output_chunks.append(line)

        if progress_callback:
            process_task = asyncio.create_task(process.wait())
            monitor_task = asyncio.create_task(_monitor_progress())
            await _await_first_and_cancel_others(process_task, monitor_task)
        else:
            process_task = asyncio.create_task(process.wait())
            drain_task = asyncio.create_task(_drain_output())
            await _await_first_and_cancel_others(process_task, drain_task)

        # Ensure the process is fully reaped before reading returncode.
        if process.returncode is None:
            await process.wait()

        output_data = b"".join(output_chunks) if output_chunks else b""

        if shutdown_event.is_set():
            logger.info("yt_dlp_download_cancelled", url=_strip_auth_params(video_url))
            return None

        if process.returncode != 0:
            # SEC-002: sanitize subprocess output to redact any signed
            # CDN URLs or cookie file paths that yt-dlp may echo in
            # error messages before persisting to log files.
            error_msg = output_data.decode() if output_data else "Unknown yt-dlp error"
            error_msg = sanitize_text_for_log(error_msg)
            logger.error(
                "download_failed",
                url=_strip_auth_params(video_url),
                returncode=process.returncode,
                error=error_msg,
            )
            return None

        logger.info("ytdlp_download_completed", output=str(output_file))
        return output_file

    except FileNotFoundError:
        # yt-dlp module / Python interpreter not found
        logger.error(
            "ytdlp_not_found",
            url=_strip_auth_params(video_url),
            exc_info=True,
        )
        return None
    except asyncio.CancelledError:
        logger.info("yt_dlp_download_cancelled", url=_strip_auth_params(video_url))
        if process is not None and process.returncode is None:
            if not await cancel_subprocess(process):
                logger.warning(
                    "yt_dlp_cancel_not_clean",
                    pid=process.pid,
                    url=_strip_auth_params(video_url),
                )
        raise
    finally:
        if cookie_file is not None and cookie_file.exists():
            cookie_file.unlink(missing_ok=True)
            logger.debug("cookie_file_cleaned_up", path=str(cookie_file))


async def _resolve_cookies(
    extractor: VKVideoExtractor,
    settings: Settings,
    url: str,
    m3u8_url: str,
    quality: str,
) -> tuple[str, str | None, list[Cookie] | None]:
    """Resolve cookies and update m3u8_url based on cookie_source setting.

    Args:
        extractor: VKVideoExtractor instance for stream extraction.
        settings: Application settings.
        url: Video URL to extract streams from.
        m3u8_url: Current m3u8 URL (may be updated if browser streams used).
        quality: Quality string for stream selection.

    Returns:
        Tuple of (updated m3u8_url, cookies string, raw cookies for Netscape format).

    Raises:
        QualityNotAvailableError: If requested quality is BEST but not available in browser streams.
    """
    if settings.cookie_source == CookieSource.BROWSER:
        browser_streams, cookies, raw_cookies = await extractor.extract_streams_with_cookies(url)
        if browser_streams:
            quality_enum = _parse_quality_to_enum(quality)
            # Browser streams always have quality="best" with height=None.
            # Only run quality selection for BEST; for numeric qualities, reuse the
            # pre-selected m3u8_url from the caller (yt-dlp already selected the stream).
            if quality_enum == QualityEnum.BEST:
                selector = QualitySelector()
                selected_stream = selector.select(browser_streams, quality_enum)
                m3u8_url = str(selected_stream.url)
                logger.info(
                    "browser_streams_selected",
                    quality=quality,
                    selected_quality=selected_stream.quality,
                )
            else:
                logger.info(
                    "browser_streams_selected_with_preselected_url",
                    quality=quality,
                    m3u8_url=_strip_auth_params(m3u8_url),
                )
        else:
            cookies = None
            raw_cookies = None
        return m3u8_url, cookies, raw_cookies
    return m3u8_url, None, None
