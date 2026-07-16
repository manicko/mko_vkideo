"""CLI interface for VK Video Downloader using Typer."""

import asyncio
from collections.abc import Callable
from pathlib import Path

import typer
from structlog import get_logger

from .config import Settings, setup_logging
from .exceptions import QualityNotAvailableError
from .models.enums import CookieSource, DownloadMethod, QualityEnum
from .services.downloader import perform_download
from .services.downloader_throttle import ProgressManager, URLBackoffCoordinator
from .services.extractor import VKVideoExtractor
from .services.quality import QualitySelector
from .services.signal_handlers import setup_signal_handlers
from .utils.security import _sanitize_title, validate_output_path

logger = get_logger(__name__)

# Module-level progress manager for thread-safe per-URL progress tracking
_progress_manager = ProgressManager()


def _create_progress_callback(url_index: int) -> Callable[[str, int, int], None]:
    """Create fire-and-forget progress callback for a URL index.

    Args:
        url_index: Index of the URL in the batch for tracking.

    Returns:
        Callback function that updates shared progress state.

    Thread-safety:
        Uses `update_sync()` which performs direct assignment without lock protection.
        This is safe because callbacks execute sequentially in the single-threaded
        asyncio event loop. The async lock in `get_formatted_progress()` protects the
        read path, ensuring consistent reads while callbacks write concurrently.
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


async def _download_single(
    url: str,
    index: int,
    quality: QualityEnum,
    output: Path,
    method: DownloadMethod,
    cookie_source: CookieSource,
    ssl_verify: bool,
    max_retries: int | None,
    shared_semaphore: asyncio.Semaphore | None = None,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> tuple[str, str, str]:
    """Download a single video and return result tuple.

    Args:
        url: Video URL to download.
        index: Index of the URL in the batch.
        quality: Video quality selection.
        output: Output directory for downloaded video.
        method: Download method (yt-dlp, ffmpeg, or auto).
        cookie_source: Cookie acquisition strategy.
        ssl_verify: Whether to verify SSL certificates.
        max_retries: Maximum retry attempts, or None to use default.
        shared_semaphore: Optional semaphore for concurrency control.
        backoff_coordinator: Optional coordinator for rate limiting.
        progress_callback: Optional callback for progress updates.

    Returns:
        Tuple of (url, output_path, status).
    """
    try:
        actual_max_retries = max_retries if max_retries is not None else Settings().max_retries
        settings = Settings(
            cookie_source=cookie_source, max_retries=actual_max_retries, ssl_verify=ssl_verify
        )
        extractor = VKVideoExtractor(settings=settings)
        video = await extractor.extract_streams(url)

        selector = QualitySelector()
        stream = selector.select(video.streams, quality)

        # Apply settings download_dir as default output path
        output_path = output if str(output) != "." else settings.download_dir
        output_path = Path(output_path).resolve()

        # Validate output directory to prevent path traversal
        validated_output = validate_output_path(output_path, warning=False)

        # Ensure output directory exists
        validated_output.mkdir(parents=True, exist_ok=True)

        # Generate output filename with sanitized title
        safe_title = _sanitize_title(video.title) if video.title else None
        if safe_title:
            output_file = validated_output / f"{safe_title}_{video.id}.mp4"
        else:
            output_file = validated_output / f"{index}_{video.id}.mp4"

        result = await perform_download(
            url,
            str(stream.quality),
            output_file,
            method,
            extractor,
            settings,
            backoff_coordinator=backoff_coordinator,
            semaphore=shared_semaphore,
            progress_callback=progress_callback,
            video_data=video,
            selected_stream=stream,
        )

        status = "success" if result else "failed"
        return (url, str(output_file) if result else "", status)

    except asyncio.CancelledError:
        # Re-raise CancelledError to allow batch cancellation
        raise
    except Exception as e:
        return (url, "", f"error: {e}")


async def _run_batch_with_progress(
    urls: list[str],
    quality: QualityEnum,
    method: DownloadMethod,
    cookie_source: CookieSource,
    ssl_verify: bool,
    max_retries: int | None,
    output: Path,
) -> list[tuple[str, str, str]]:
    """Run batch download with progress tracking.

    Args:
        urls: List of video URLs to download.
        quality: Video quality selection for all downloads.
        method: Download method (yt-dlp, ffmpeg, or auto).
        cookie_source: Cookie acquisition strategy.
        ssl_verify: Whether to verify SSL certificates.
        max_retries: Maximum retry attempts for failed segment downloads.
        output: Output directory for downloaded videos.

    Returns:
        List of result tuples (url, output_path, status).
    """
    # Setup signal handlers inside async context
    setup_signal_handlers()
    # Create shared semaphore and backoff coordinator at batch level
    shared_semaphore = asyncio.Semaphore(Settings().max_concurrent_downloads)
    backoff_coordinator = URLBackoffCoordinator()

    # Clear progress state for this batch
    await _progress_manager.clear()

    # Create progress callbacks for each URL
    callbacks = [_create_progress_callback(i) for i in range(len(urls))]

    tasks = [
        asyncio.create_task(
            _download_single(
                url,
                i,
                quality,
                output,
                method,
                cookie_source,
                ssl_verify,
                max_retries,
                shared_semaphore,
                backoff_coordinator,
                callbacks[i],
            )
        )
        for i, url in enumerate(urls)
    ]
    total = len(urls)

    # Initial progress display in per-URL format
    typer.echo(f"\r{await _format_progress(total)}", nl=False)

    for coro in asyncio.as_completed(tasks):
        try:
            await coro
        except asyncio.CancelledError:
            # Cancel remaining tasks on interrupt
            for task in tasks:
                if not task.done():
                    task.cancel()
            # Wait for cancellation to propagate
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        # Update progress display with \r overwrite
        typer.echo(f"\r{await _format_progress(total)}", nl=False)

    typer.echo()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Filter out CancelledError results
    return [
        r if isinstance(r, tuple) else (urls[i], "", "cancelled") for i, r in enumerate(results)
    ]


def _print_batch_summary(
    results: list[tuple[str, str, str]],
    max_concurrent: int,
) -> None:
    """Print batch download summary.

    Args:
        results: List of result tuples (url, output_path, status).
        max_concurrent: Maximum concurrent downloads setting.
    """
    # Print results
    for url, output_path, status in results:
        typer.echo(f"{url}: {status}" + (f" -> {output_path}" if output_path else ""))

    # Summary
    successful = sum(1 for _, _, status in results if status == "success")
    failed = len(results) - successful

    typer.echo("\n\nDownload Summary:")
    typer.echo(f"  Total connections: {len(results)}")
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
    quality: QualityEnum = typer.Option(QualityEnum.BEST, help="Video quality selection"),  # noqa: B008
    output: Path = typer.Option(  # noqa: B008
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded video",
    ),
    method: DownloadMethod = typer.Option(  # noqa: B008
        DownloadMethod.AUTO,
        "--method",
        "-m",
        help="Download method: yt-dlp, ffmpeg, or auto",
    ),
    cookie_source: CookieSource = typer.Option(  # noqa: B008
        CookieSource.NONE,
        "--cookie-source",
        "-c",
        help="Cookie source: none, browser, or file",
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
    """
    setup_logging()

    async def _download() -> Path | None:
        """Async implementation of video download."""
        # Setup signal handlers inside async context
        setup_signal_handlers()
        settings = Settings(cookie_source=cookie_source, ssl_verify=ssl_verify)
        extractor = VKVideoExtractor(settings=settings)
        video = await extractor.extract_streams(url)

        # Print available qualities
        if video.streams:
            logger.info("available_streams", count=len(video.streams))
            selector = QualitySelector()
            available = selector.list_available_qualities(video.streams)
            logger.info("available_qualities", qualities=available[:8])

        selector = QualitySelector()
        stream = selector.select(video.streams, quality)

        # Apply settings download_dir as default output path
        output_path = output if str(output) != "." else settings.download_dir
        output_path = Path(output_path).resolve()

        # Validate output directory to prevent path traversal
        validated_output = validate_output_path(output_path, warning=False)

        # Ensure output directory exists
        validated_output.mkdir(parents=True, exist_ok=True)

        # Generate output filename with sanitized title
        safe_title = _sanitize_title(video.title) if video.title else None
        if safe_title:
            output_file = validated_output / f"{safe_title}_{video.id}.mp4"
        else:
            output_file = validated_output / f"{video.id}_{stream.quality}.mp4"

        return await perform_download(
            url,
            str(stream.quality),
            output_file,
            method,
            extractor,
            settings,
            video_data=video,
            selected_stream=stream,
        )

    try:
        result = asyncio.run(_download())

        if result:
            typer.echo(f"Downloaded: {result}")
        else:
            typer.echo("Download failed", err=True)
            raise typer.Exit(code=1)

    except ValueError:
        typer.echo(
            "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}",
            err=True,
        )
        raise typer.Exit(code=1) from None
    except (KeyboardInterrupt, asyncio.CancelledError):
        typer.echo("\nDownload cancelled", err=True)
        raise typer.Exit(code=130) from None
    except QualityNotAvailableError as e:
        # Access structured fields directly instead of parsing error message
        requested = e.requested
        available_qualities = e.available
        typer.echo(
            f"\nRequested quality '{requested}p' is not available for this video.",
            err=True,
        )
        typer.echo(f"Available qualities: {', '.join(available_qualities)}", err=True)
        raise typer.Exit(code=1) from None
    except Exception:
        logger.exception("download_failed")
        typer.echo("An error occurred during download", err=True)
        raise typer.Exit(code=1) from None


@app.command("batch")
def batch_download(
    urls_file: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        help="Path to file containing video URLs (one per line)",
    ),
    quality: QualityEnum = typer.Option(  # noqa: B008
        QualityEnum.BEST,
        help="Video quality selection for all downloads",
    ),
    output: Path = typer.Option(  # noqa: B008
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded videos",
    ),
    method: DownloadMethod = typer.Option(  # noqa: B008
        DownloadMethod.AUTO,
        "--method",
        "-m",
        help="Download method: yt-dlp, ffmpeg, or auto",
    ),
    cookie_source: CookieSource = typer.Option(  # noqa: B008
        CookieSource.NONE,
        "--cookie-source",
        "-c",
        help="Cookie source: none, browser, or file",
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
    setup_logging()

    # Read URLs from file
    urls = [
        line.strip()
        for line in urls_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    if not urls:
        typer.echo(f"No URLs found in {urls_file}", err=True)
        raise typer.Exit(code=1)

    try:
        results = asyncio.run(
            _run_batch_with_progress(
                urls, quality, method, cookie_source, ssl_verify, max_retries, output
            )
        )
        _print_batch_summary(results, Settings().max_concurrent_downloads)

    except (KeyboardInterrupt, asyncio.CancelledError):
        typer.echo("\nDownload cancelled", err=True)
        raise typer.Exit(code=130) from None


def cli() -> None:
    """Entry point for CLI execution."""
    app()
