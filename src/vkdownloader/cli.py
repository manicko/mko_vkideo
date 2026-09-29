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
from typing import TypedDict

import typer
from pydantic import ValidationError
from structlog import get_logger

from .config import (
    Settings,
    _build_valid_env_vars,
    format_validation_error,
    setup_logging,
    warn_unknown_env_vars,
)
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

# Tracks whether setup_logging has completed successfully for the current
# invocation. Reset on every preamble call so the catch-all can avoid
# emitting a log record through an unconfigured sink (ENT-002).
_logging_configured: bool = False


class _PreambleFailure(Exception):
    """Raised when the shared preamble encounters an OSError.

    Wraps OSErrors from env scanning or logging setup so both commands can
    route them to a single renderer instead of their own catch-alls.
    """


_PREAMBLE_FAILURE_MESSAGE = (
    "Logging configuration failed; cannot continue. "
    "Check the --log-file option or VKDOWNLOADER_LOG_FILE environment variable."
)


def _render_preamble_failure(exc: BaseException) -> None:
    """Render a preamble/bootstrap failure on stderr via the entry layer.

    Reached by both ``download`` and ``batch`` for any OSError raised during
    the shared preamble — currently from ``setup_logging`` when the log
    directory cannot be created. The structured-log sink is not configured
    in this state, so the message is emitted to stderr through
    ``typer.echo`` and a log record is produced only when a sink can
    actually receive it. The record carries only the error type name —
    no traceback, no source path, no settings object.
    """
    typer.echo(_PREAMBLE_FAILURE_MESSAGE, err=True)
    if _logging_configured:
        cause = exc.__cause__
        logger.error(
            "preamble_failed",
            error_type=type(cause if cause is not None else exc).__name__,
        )


def _log_env_file_path() -> None:
    """Log the resolved .env file path at debug level."""
    env_file = Path(".env")
    if env_file.exists():
        logger.debug("env_file_resolved", path=str(env_file.resolve()))
    else:
        logger.debug(".env file not found; using environment variables or defaults only")


class _SettingsOverrides(TypedDict, total=False):
    """Constructor keywords for the options a user actually supplied.

    A key is present only when the user typed the option. An unsupplied option
    therefore occupies no configuration source, leaving VKDOWNLOADER_* variables
    and the .env file reachable for that field (CFG-001).
    """

    cookie_source: CookieSource
    ssl_verify: bool
    max_retries: int


def _build_settings(
    *,
    cookie_source: CookieSource | None,
    ssl_verify: bool | None,
    max_retries: int | None,
) -> Settings:
    """Construct the one Settings object a command invocation runs on.

    Only options the user actually supplied become constructor keywords. Every
    supplied value is validated by the model, so the declared bounds on
    ``max_retries`` still apply (CFG-002). An option the user did not type is
    left to the model's own documented precedence: constructor keyword,
    VKDOWNLOADER_* variable, .env file, field default.
    """
    overrides: _SettingsOverrides = {}
    if cookie_source is not None:
        overrides["cookie_source"] = cookie_source
    if ssl_verify is not None:
        overrides["ssl_verify"] = ssl_verify
    if max_retries is not None:
        overrides["max_retries"] = max_retries
    return Settings(**overrides)


def _run_command_preamble(
    *,
    cookie_source: CookieSource | None,
    ssl_verify: bool | None,
    max_retries: int | None,
) -> Settings:
    """Run the shared four-step command bootstrap and return the constructed Settings.

    Every command invocation performs the same preamble:

      1. detect unrecognised ``VKDOWNLOADER_*`` variables (via
         ``warn_unknown_env_vars``); each detected variable is rendered once,
         as plain text to stderr with ``typer.echo(..., err=True)``, naming
         the offending variable and the set of valid variables, so the notice
         reaches the operator exactly once and stays out of the logging path;
      2. construct ``Settings`` from the supplied overrides (via ``_build_settings``,
         which only forwards options the user actually typed);
      3. configure logging from the constructed Settings (via ``setup_logging``);
      4. report the resolved environment file (via ``_log_env_file_path``).

    The single ``Settings`` instance is returned so the calling command can pass
    the same object downstream, keeping logging configuration and the service
    layer on one identity (A4).      ``warn_unknown_env_vars`` is resolved through
    this module's global namespace so that string-path patches targeting
    ``vkdownloader.cli.warn_unknown_env_vars`` still take effect here.

    Any ``OSError`` raised during the preamble is wrapped in
    ``_PreambleFailure`` so both commands delegate to
    ``_render_preamble_failure`` — keeping the bootstrap-failure path
    independent of the structured-log sink. After ``setup_logging``
    returns, ``_logging_configured`` is set so the catch-all can avoid
    emitting a log record through an unconfigured sink.
    """
    global _logging_configured
    _logging_configured = False
    try:
        unknown_vars = warn_unknown_env_vars()
        if unknown_vars:
            valid_vars = sorted(_build_valid_env_vars())
            for var in unknown_vars:
                typer.echo(
                    f"Ignored unknown environment variable '{var}'. "
                    f"Valid variables: {', '.join(valid_vars)}. "
                    f"Check for typos.",
                    err=True,
                )
        settings = _build_settings(
            cookie_source=cookie_source, ssl_verify=ssl_verify, max_retries=max_retries
        )
        setup_logging(settings)
        _logging_configured = True
        _log_env_file_path()
        return settings
    except OSError as exc:
        raise _PreambleFailure(
            "OSError during command preamble (env scan or logging setup)"
        ) from exc


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
    cookie_source: CookieSource | None = typer.Option(
        None,
        "--cookie-source",
        "-c",
        help="Cookie source: none or browser (effective default: none; from VKDOWNLOADER_COOKIE_SOURCE or .env)",
    ),
    ssl_verify: bool | None = typer.Option(
        None,
        "--ssl-verify/--no-ssl-verify",
        help="Verify SSL certificates for CDN connections (effective default: true; from VKDOWNLOADER_SSL_VERIFY or .env)",
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
        settings = _run_command_preamble(
            cookie_source=cookie_source, ssl_verify=ssl_verify, max_retries=max_retries
        )
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
        accepted_qualities = ", ".join(quality_value.value for quality_value in QualityEnum)
        typer.echo(
            f"Invalid quality value: {e.quality}. Use one of: {accepted_qualities}.",
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
    except _PreambleFailure as exc:
        _render_preamble_failure(exc)
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception:
        if _logging_configured:
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
    cookie_source: CookieSource | None = typer.Option(
        None,
        "--cookie-source",
        "-c",
        help="Cookie source: none or browser (effective default: none; from VKDOWNLOADER_COOKIE_SOURCE or .env)",
    ),
    ssl_verify: bool | None = typer.Option(
        None,
        "--ssl-verify/--no-ssl-verify",
        help="Verify SSL certificates for CDN connections (effective default: true; from VKDOWNLOADER_SSL_VERIFY or .env)",
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
        valid_urls: list[str] = []
        skipped_count = 0

        settings = _run_command_preamble(
            cookie_source=cookie_source, ssl_verify=ssl_verify, max_retries=max_retries
        )

        # Read and validate URLs from file
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
                output,
                skipped_count,
            )
        )
        raise typer.Exit(code=exit_code)

    except ValidationError as e:
        typer.echo(format_validation_error(e), err=True)
        raise typer.Exit(code=1) from None
    except _PreambleFailure as exc:
        _render_preamble_failure(exc)
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
        if _logging_configured:
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
