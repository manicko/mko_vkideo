"""CLI interface for VK Video Downloader using Typer.

This module is the thin entry layer: it parses command arguments, constructs
``Settings``, delegates to service-layer functions for actual work, and maps
results/exceptions into user-facing messages and exit codes.

Batch download orchestration (ConcurrencyTracker, _TrackedSemaphore,
DownloadContext, progress display, _download_single, _run_batch_with_progress,
_print_batch_summary) lives in ``services.batch_downloader`` so it is
unit-testable without invoking the Typer CLI.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from pydantic import ValidationError
from structlog import get_logger

from .config import Settings, format_validation_error, setup_logging, warn_unknown_env_vars
from .exceptions import (
    InvalidVideoUrlError,
    QualityNotAvailableError,
    QualityParseError,
    VideoNotFoundError,
)
from .models.enums import CookieSource, DownloadMethod, QualityEnum
from .services.batch_downloader import run_batch
from .services.downloader import download_video
from .services.downloader_throttle import get_shutdown_event
from .services.extractor import is_valid_video_url
from .services.signal_handlers import cleanup_signal_handlers, setup_signal_handlers
from .utils.url_sanitizer import sanitize_url_for_log

logger = get_logger(__name__)


def _log_env_file_path() -> None:
    """Log the resolved .env file path at debug level."""
    env_file = Path(".env")
    if env_file.exists():
        logger.debug("env_file_resolved", path=str(env_file.resolve()))
    else:
        logger.debug(".env file not found; using environment variables or defaults only")


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
        help="Cookie source: none or browser",
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
        help="Maximum retry attempts for failed downloads",
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
                max_retries_override=max_retries,
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
        typer.echo(format_validation_error(e), err=True)
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
        logger.exception("download_failed", url=sanitize_url_for_log(url))
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
        help="Cookie source: none or browser",
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
            if not is_valid_video_url(stripped):
                logger.warning("invalid_url_in_batch", url=sanitize_url_for_log(stripped))
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

        exit_code = asyncio.run(
            run_batch(
                valid_urls,
                quality,
                method,
                settings,
                max_retries,
                output,
                skipped_count,
            )
        )
        raise typer.Exit(code=exit_code)

    except ValidationError as e:
        typer.echo(format_validation_error(e), err=True)
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
