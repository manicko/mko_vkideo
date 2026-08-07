"""CLI interface for VK Video Downloader using Typer."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import typer
from pydantic import ValidationError
from structlog import get_logger

from .config import Settings, setup_logging, warn_unknown_env_vars
from .exceptions import (
    ExtractionError,
    InvalidVideoUrlError,
    QualityNotAvailableError,
    QualityParseError,
    VideoNotFoundError,
    VKDownloadError,
    _map_exception_to_status,
)
from .models.enums import CookieSource, DownloadMethod, QualityEnum
from .services.downloader import download_video
from .services.downloader_throttle import ProgressManager, URLBackoffCoordinator, get_shutdown_event
from .services.extractor import VIDEO_ID_PATTERN
from .services.signal_handlers import cleanup_signal_handlers, setup_signal_handlers
from .utils.correlation import bind_correlation_id, clear_correlation_id, generate_correlation_id
from .utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)

# Module-level progress manager for thread-safe per-URL progress tracking
_progress_manager = ProgressManager()


def _log_env_file_path() -> None:
    """Log the resolved .env file path at debug level."""
    env_file = Path(".env")
    if env_file.exists():
        logger.debug("env_file_resolved", path=str(env_file.resolve()))
    else:
        logger.debug(".env file not found; using environment variables or defaults only")


def _format_validation_error(error: ValidationError) -> str:
    """Format a Pydantic ValidationError into a concise, user-facing message.

    Args:
        error: The ValidationError to format.

    Returns:
        A human-readable string listing each field error with the received
        value and a hint to check the .env file or environment variables.
    """
    lines = [
        "Configuration error: one or more settings have invalid values.",
        "Check your .env file or VKDOWNLOADER_* environment variables:",
    ]
    for err in error.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = err.get("msg", "validation failed")
        lines.append(f"  - {loc}: {msg}")
        lines.append("    Received: <redacted>")
    lines.append("Fix the offending value(s) and try again.")
    return "\n".join(lines)


@dataclass
class ConcurrencyTracker:
    """Track the peak number of concurrently in-flight downloads.

    Incremented when a download acquires the shared semaphore and
    decremented when it releases, so the peak reflects actual
    concurrency rather than the configured maximum.
    """

    _current: int = 0
    peak: int = 0

    def acquire(self) -> None:
        self._current += 1
        if self._current > self.peak:
            self.peak = self._current

    def release(self) -> None:
        self._current -= 1


class _TrackedSemaphore:
    """Semaphore wrapper that tracks peak concurrency.

    Implements the async context manager protocol so it can be used
    in place of ``asyncio.Semaphore`` in ``async with`` blocks.
    """

    def __init__(self, semaphore: asyncio.Semaphore, tracker: ConcurrencyTracker) -> None:
        self._semaphore = semaphore
        self._tracker = tracker

    async def acquire(self) -> bool:
        await self._semaphore.acquire()
        self._tracker.acquire()
        return True

    def release(self) -> None:
        self._tracker.release()
        self._semaphore.release()

    async def __aenter__(self) -> _TrackedSemaphore:
        await self.acquire()
        return self

    async def __aexit__(self, *args: object) -> None:
        self.release()


@dataclass
class DownloadContext:
    """Context for batch download operations, bundling batch-scoped state."""

    index: int
    shared_semaphore: asyncio.Semaphore | None = None
    backoff_coordinator: URLBackoffCoordinator | None = None
    progress_callback: Callable[[str, int, int], None] | None = None
    peak_tracker: ConcurrencyTracker | None = None


def _create_progress_callback(url_index: int) -> Callable[[str, int, int], None]:
    """Create fire-and-forget progress callback for a URL index.

    Args:
        url_index: Index of the URL in the batch for tracking.

    Returns:
        Callback function that updates shared progress state.

    Thread-safety:
        Uses `update_sync()` which performs direct dict assignment without lock
        protection. This is safe under CPython's GIL (dict.__setitem__ is
        atomic). However, callbacks fire from yt-dlp's thread-pool executor
        (loop.run_in_executor), not from the asyncio event loop thread. The
        async lock in `get_formatted_progress()` protects the read path,
        ensuring consistent reads while callbacks write from worker threads.
    """

    def callback(video_id: str, downloaded: int, total: int) -> None:
        _progress_manager.update_sync(url_index, downloaded, total)

    return callback


async def _format_progress(url_count: int) -> str:
    """Format progress state as per-URL segment format.

    Args:
        url_count: Total number of URLs in the batch.

    Returns:
        Formatted string like "video_1: 25/100, video_2: 45/150".
    """
    return await _progress_manager.get_formatted_progress(url_count)


async def _poll_progress_display(total: int, refresh_interval: float = 1.0) -> None:
    """Continuously refresh the progress display at a fixed interval.

    Runs as a background task during batch downloads so the user sees
    live progress updates rather than only when a download completes.

    Args:
        total: Total number of URLs in the batch.
        refresh_interval: Seconds between display refreshes.
    """
    while True:
        typer.echo(f"\r{await _format_progress(total)}", nl=False)
        await asyncio.sleep(refresh_interval)


async def _download_single(
    url: str,
    quality: QualityEnum,
    output: Path,
    method: DownloadMethod,
    settings: Settings,
    max_retries_override: int | None = None,
    context: DownloadContext | None = None,
) -> tuple[str, str, str]:
    """Download a single video and return result tuple.

    Args:
        url: Video URL to download.
        quality: Video quality selection.
        output: Output directory for downloaded video.
        method: Download method (yt-dlp, ffmpeg, or auto).
        settings: Application settings with environment-loaded values.
        max_retries_override: Optional max_retries override from CLI.
        context: Optional context for batch download operations.

    Returns:
        Tuple of (url, output_path, status).
    """
    # Extract batch-scoped values from context
    index = context.index if context else 0
    shared_semaphore = context.shared_semaphore if context else None
    backoff_coordinator = context.backoff_coordinator if context else None
    progress_callback = context.progress_callback if context else None
    peak_tracker = context.peak_tracker if context else None

    # Wrap semaphore with concurrency tracker so peak is measured at the
    # actual point of concurrency limiting, not the configured maximum.
    tracked_semaphore = None
    if shared_semaphore is not None and peak_tracker is not None:
        tracked_semaphore = _TrackedSemaphore(shared_semaphore, peak_tracker)

    # Bind a per-operation correlation ID so every log entry within this
    # download carries a traceable identifier in both single and batch mode.
    correlation_id = generate_correlation_id()
    bind_correlation_id(correlation_id)

    try:
        result = await download_video(
            url,
            quality,
            output,
            method,
            settings,
            max_retries_override=max_retries_override,
            backoff_coordinator=backoff_coordinator,
            semaphore=tracked_semaphore,
            progress_callback=progress_callback,
            output_index=index,
        )
        status = "success" if result else "failed"
        return (url, str(result) if result else "", status)

    except asyncio.CancelledError:
        # Re-raise CancelledError to allow batch cancellation
        raise
    except QualityNotAvailableError as e:
        return (url, "", e.status_label())
    except VideoNotFoundError as e:
        return (url, "", e.status_label())
    except ExtractionError as e:
        logger.error(
            "extraction_error",
            url=_strip_auth_params(url),
            correlation_id=correlation_id,
            **e.log_context(),
        )
        return (url, "", e.status_label())
    except VKDownloadError as e:
        return (url, "", e.status_label())
    except Exception as e:
        # Log unexpected exceptions to surface bugs, then return as a status tuple
        logger.exception(
            "unexpected_error_in_batch_download",
            url=_strip_auth_params(url),
            correlation_id=correlation_id,
        )
        return (url, "", _map_exception_to_status(e))
    finally:
        clear_correlation_id()


async def _run_batch_with_progress(
    urls: list[str],
    quality: QualityEnum,
    method: DownloadMethod,
    settings: Settings,
    max_retries: int | None,
    output: Path,
) -> tuple[list[tuple[str, str, str]], int]:
    """Run batch download with progress tracking.

    Args:
        urls: List of video URLs to download.
        quality: Video quality selection for all downloads.
        method: Download method (yt-dlp, ffmpeg, or auto).
        settings: Application settings.
        max_retries: Maximum retry attempts for failed segment downloads.
        output: Output directory for downloaded videos.

    Returns:
        List of result tuples (url, output_path, status).
    """
    # Setup signal handlers inside async context
    setup_signal_handlers()
    batch_correlation_id = generate_correlation_id()
    bind_correlation_id(batch_correlation_id)
    try:
        # Create shared semaphore and backoff coordinator at batch level
        concurrency_tracker = ConcurrencyTracker()
        shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        backoff_coordinator = URLBackoffCoordinator()

        logger.info(
            "batch_download_started",
            url_file_count=len(urls),
            batch_correlation_id=batch_correlation_id,
        )

        # Clear progress state for this batch
        await _progress_manager.clear()

        # Create progress callbacks for each URL
        callbacks = [_create_progress_callback(i) for i in range(len(urls))]

        tasks = [
            asyncio.create_task(
                _download_single(
                    url,
                    quality,
                    output,
                    method,
                    settings,
                    max_retries,
                    DownloadContext(
                        index=i,
                        shared_semaphore=shared_semaphore,
                        backoff_coordinator=backoff_coordinator,
                        progress_callback=callbacks[i],
                        peak_tracker=concurrency_tracker,
                    ),
                )
            )
            for i, url in enumerate(urls)
        ]
        total = len(urls)

        # Initial progress display in per-URL format
        typer.echo(f"\r{await _format_progress(total)}", nl=False)

        # Background task for real-time progress display
        progress_task = asyncio.create_task(_poll_progress_display(total))

        try:
            for coro in asyncio.as_completed(tasks):
                try:
                    await coro
                except asyncio.CancelledError:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise

            typer.echo()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            processed_results = [
                r
                if isinstance(r, tuple)
                else (urls[i], "", "cancelled")
                if isinstance(r, asyncio.CancelledError)
                else (urls[i], "", f"unexpected_error: {type(r).__name__}")
                for i, r in enumerate(results)
            ]
            return processed_results, concurrency_tracker.peak
        finally:
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
    finally:
        # Cleanup signal handlers to allow re-registration on subsequent loops
        cleanup_signal_handlers()
        clear_correlation_id()


def _print_batch_summary(
    results: list[tuple[str, str, str]],
    max_concurrent: int,
    skipped_count: int = 0,
) -> None:
    """Print batch download summary.

    Args:
        results: List of result tuples (url, output_path, status).
        peak_concurrent: Measured peak concurrency during the batch.
        skipped_count: Number of invalid URLs skipped during validation.
    """
    # Print results
    for url, output_path, status in results:
        typer.echo(f"{url}: {status}" + (f" -> {output_path}" if output_path else ""))

    # Summary
    successful = sum(1 for _, _, status in results if status == "success")
    failed = len(results) - successful

    typer.echo("\n\nDownload Summary:")
    typer.echo(f"  Total connections: {len(results)}")
    if skipped_count > 0:
        typer.echo(f"  Skipped (invalid URLs): {skipped_count}")
    typer.echo(f"  Peak concurrency: {max_concurrent}")
    typer.echo(f"  Successful: {successful}")
    typer.echo(f"  Failed: {failed}")

    # Show failed URLs with error reasons
    failed_urls = [(url, status) for url, _, status in results if status != "success"]
    if failed_urls:
        typer.echo("  Failed URLs:")
        for url, status in failed_urls:
            typer.echo(f"    - {url}: {status}")

    # Exit with code 1 if any downloads failed
    if failed > 0:
        raise typer.Exit(code=1)


app = typer.Typer(
    name="vkdownloader",
    help="Download videos from vkvideo.ru with quality selection support",
)


@app.command()
def download(
    url: str = typer.Argument(..., help="VK Video URL to download"),
    quality: QualityEnum = typer.Option(QualityEnum.BEST, help="Video quality selection"),
    output: Path = typer.Option(
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded video",
    ),
    method: DownloadMethod = typer.Option(
        DownloadMethod.AUTO,
        "--method",
        "-m",
        help="Download method: yt-dlp, ffmpeg, or auto",
    ),
    cookie_source: CookieSource = typer.Option(
        CookieSource.NONE,
        "--cookie-source",
        "-c",
        help="Cookie source: none or browser (file not implemented)",
    ),
    ssl_verify: bool = typer.Option(
        True,
        "--ssl-verify/--no-ssl-verify",
        help="Verify SSL certificates for CDN connections",
    ),
) -> None:
    """Download a single video from vkvideo.ru.

    Extracts available streams, selects the requested quality, and downloads the video
    to the specified output directory.

    Note: This command does not show live progress during download. For real-time
    per-URL progress display, use the ``batch`` command instead.
    """

    async def _download() -> Path | None:
        """Async implementation of video download."""
        setup_signal_handlers()
        try:
            result = await download_video(
                url,
                quality,
                output,
                method,
                settings,
                log_available_qualities=True,
            )
        finally:
            cleanup_signal_handlers()

        # Distinguish user-initiated cancellation from genuine download
        # failure.  The signal handler sets a shutdown Event (rather than
        # raising KeyboardInterrupt), so we inspect it inside the async
        # context — ContextVar changes inside asyncio.run() are NOT visible
        # to the caller (asyncio.run copies the context).
        if result is None and get_shutdown_event().is_set():
            raise KeyboardInterrupt
        return result

    try:
        # Detect misspelled VKDOWNLOADER_* env vars before construction
        warn_unknown_env_vars()
        # Create Settings once with environment-loaded values, merging CLI overrides
        settings = Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)
        setup_logging(settings)
        # Log resolved .env path for debugging configuration issues
        _log_env_file_path()
        result = asyncio.run(_download())

        if result:
            typer.echo(f"Downloaded: {result}")
        else:
            typer.echo("Download failed", err=True)
            raise typer.Exit(code=1)

    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from None
    except QualityParseError as e:
        typer.echo(
            f"Invalid quality value: {e.quality}. "
            "Use one of: 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p, best, worst.",
            err=True,
        )
        raise typer.Exit(code=1) from None
    except InvalidVideoUrlError:
        typer.echo(
            "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}",
            err=True,
        )
        raise typer.Exit(code=1) from None
    except (KeyboardInterrupt, asyncio.CancelledError):
        typer.echo("\nDownload cancelled by user", err=True)
        raise typer.Exit(code=130) from None
    except QualityNotAvailableError as e:
        # Access structured fields directly instead of parsing error message
        requested = e.requested
        available_qualities = e.available
        # Distinguish empty-stream case (available is empty) from missing quality
        if not available_qualities:
            typer.echo(
                "\nNo streams found for this video; the video may be private or unavailable.",
                err=True,
            )
        else:
            typer.echo(
                f"\nRequested quality '{requested}p' is not available for this video.",
                err=True,
            )
            typer.echo(f"Available qualities: {', '.join(available_qualities)}", err=True)
        raise typer.Exit(code=1) from None
    except VideoNotFoundError:
        typer.echo("Video not found. Verify the URL is correct and the video is public.", err=True)
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception:
        logger.exception("download_failed", url=_strip_auth_params(url))
        typer.echo("An error occurred during download", err=True)
        raise typer.Exit(code=1) from None


@app.command("batch")
def batch_download(
    urls_file: Path = typer.Argument(
        ...,
        exists=True,
        help="Path to file containing video URLs (one per line)",
    ),
    quality: QualityEnum = typer.Option(
        QualityEnum.BEST,
        help="Video quality selection for all downloads",
    ),
    output: Path = typer.Option(
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded videos",
    ),
    method: DownloadMethod = typer.Option(
        DownloadMethod.AUTO,
        "--method",
        "-m",
        help="Download method: yt-dlp, ffmpeg, or auto",
    ),
    cookie_source: CookieSource = typer.Option(
        CookieSource.NONE,
        "--cookie-source",
        "-c",
        help="Cookie source: none or browser (file not implemented)",
    ),
    ssl_verify: bool = typer.Option(
        True,
        "--ssl-verify/--no-ssl-verify",
        help="Verify SSL certificates for CDN connections",
    ),
    max_retries: int | None = typer.Option(
        None,
        "--max-retries",
        "-r",
        help="Maximum retry attempts for failed segment downloads",
    ),
) -> None:
    """Download multiple videos from a file.

    Reads video URLs from a file (one URL per line) and downloads each video
    with the specified quality to the output directory.
    """
    try:
        # Detect misspelled VKDOWNLOADER_* env vars before construction
        warn_unknown_env_vars()
        # Create Settings once with environment-loaded values, merging CLI overrides
        settings = Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)
        setup_logging(settings)
        # Log resolved .env path for debugging configuration issues
        _log_env_file_path()

        # Read and validate URLs from file
        valid_urls: list[str] = []
        skipped_count = 0

        for line in urls_file.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not VIDEO_ID_PATTERN.search(stripped):
                logger.warning("invalid_url_in_batch", url=_strip_auth_params(stripped))
                skipped_count += 1
                continue
            valid_urls.append(stripped)

        if skipped_count > 0:
            typer.echo(
                f"Skipped {skipped_count} invalid URL(s) (not valid VK video URLs)",
                err=True,
            )

        if not valid_urls:
            typer.echo(f"No URLs found in {urls_file}", err=True)
            raise typer.Exit(code=1)

        results, peak_concurrent = asyncio.run(
            _run_batch_with_progress(valid_urls, quality, method, settings, max_retries, output)
        )
        _print_batch_summary(results, peak_concurrent, skipped_count)

    except ValidationError as e:
        typer.echo(_format_validation_error(e), err=True)
        raise typer.Exit(code=1) from None
    except OSError as e:
        typer.echo(f"Failed to read URL file: {urls_file} — {e}", err=True)
        raise typer.Exit(code=1) from None
    except (KeyboardInterrupt, asyncio.CancelledError):
        typer.echo("\nDownload cancelled by user", err=True)
        raise typer.Exit(code=130) from None
    except typer.Exit:
        raise
    except Exception:
        logger.exception(
            "batch_download_failed",
            url_file=str(urls_file),
            url_count=len(valid_urls),
        )
        typer.echo("An error occurred during batch download", err=True)
        raise typer.Exit(code=1) from None


def cli() -> None:
    """Entry point for CLI execution."""
    app()


if __name__ == "__main__":
    cli()
