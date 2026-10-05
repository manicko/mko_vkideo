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
from typing import Any, TypedDict

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
from .models.enums import CookieSource, DownloadMethod
from .models.quality import QualitySpec
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

    Wraps OSErrors from env scanning, settings construction, or logging
    setup so both commands can route them to a single renderer instead of
    their own catch-alls. The ``logging_related`` flag records whether the
    cause originated from the logging step, so the renderer can append the
    log-file hint only for logging-related failures.
    """

    def __init__(self, message: str, *, logging_related: bool = False) -> None:
        super().__init__(message)
        self.logging_related = logging_related


def _render_preamble_failure(exc: BaseException) -> None:
    """Render a preamble/bootstrap failure on stderr via the entry layer.

    Reached by both ``download`` and ``batch`` for any OSError raised during
    the shared preamble — from env scanning, settings construction, or
    ``setup_logging``. The original cause is included in the message so the
    operator sees what actually failed. The log-file hint is appended only
    when the cause originated from the logging step; for env-scan or
    settings-construction failures the hint would point at the wrong file.
    The structured-log sink may not be configured in this state, so a log
    record is produced only when a sink can actually receive it — carrying
    only the error type name, no traceback, no source path, no settings
    object.
    """
    cause = exc.__cause__ if isinstance(exc, _PreambleFailure) else exc
    original = cause if cause is not None else exc
    cause_str = str(original) or type(original).__name__

    if _is_logging_failure(exc):
        message = (
            "Logging configuration failed; cannot continue. "
            f"{cause_str} "
            "Check the --log-file option or VKDOWNLOADER_LOG_FILE environment variable."
        )
    else:
        message = f"Command preamble failed; cannot continue. {cause_str}"

    typer.echo(message, err=True)
    if _logging_configured:
        logger.error(
            "preamble_failed",
            error_type=type(original).__name__,
        )


def _is_logging_failure(exc: BaseException) -> bool:
    """Return True when the preamble failure originated from the logging step."""
    return getattr(exc, "logging_related", False)


def _log_env_file_path() -> None:
    """Report the resolved .env file at the default log level.

    Called from the command preamble after ``setup_logging`` configures the
    structured-log sink, so the level chosen by ``log_level`` applies. Emits
    one INFO record per invocation — the resolved path when a ``.env`` exists
    in the process's current working directory, or a notice that no ``.env``
    was found — making the working-directory dependence of that resolution
    visible without raising the log level (CFG-008).
    """
    env_file = Path(".env")
    if env_file.exists():
        logger.info("env_file_resolved", path=str(env_file.resolve()))
    else:
        logger.info("env_file_not_found_using_environment_or_defaults")


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
    layer on one identity (A4).  ``warn_unknown_env_vars`` is resolved through
    this module's global namespace so that string-path patches targeting
    ``vkdownloader.cli.warn_unknown_env_vars`` still take effect here.

    Any ``OSError`` raised during the preamble is wrapped in
    ``_PreambleFailure`` so both commands delegate to
    ``_render_preamble_failure`` — keeping the bootstrap-failure path
    independent of the structured-log sink. The env-scan / settings step and
    the logging-setup step run in separate ``try`` blocks so the wrapper can
    set ``logging_related`` correctly: OSErrors from env scanning or settings
    construction carry ``logging_related=False``, while the logging step
    (after ``_build_settings`` returns) carries ``logging_related=True``, so
    the renderer appends the log-file hint only to logging-related failures.
    After ``setup_logging`` returns, ``_logging_configured`` is set so the
    catch-all can avoid emitting a log record through an unconfigured sink.
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
    except OSError as exc:
        raise _PreambleFailure(
            "OSError during command preamble (env scan or settings construction)"
        ) from exc

    try:
        setup_logging(settings)
        _logging_configured = True
        _log_env_file_path()
        return settings
    except OSError as exc:
        raise _PreambleFailure(
            "OSError during command preamble (logging setup)",
            logging_related=True,
        ) from exc


# The accepted --quality forms live in these two tuples: the help text and the
# rejection message are both rendered from them, so a new form cannot appear in
# one and go stale in the other. Every value named in the rejection message is
# accepted when pasted back into the command line (see
# docs/99-reference/cli-reference.md).
_QUALITY_KEYWORDS = ("best", "worst", "unknown")
_QUALITY_EXAMPLE_HEIGHTS = ("720", "1080", "1072")

_QUALITY_OPTION_HELP = (
    f"Video quality: {', '.join(_QUALITY_KEYWORDS)}, or any height in pixels "
    f"the video offers (e.g. {', '.join(_QUALITY_EXAMPLE_HEIGHTS)})"
)
_QUALITY_REJECTION_MESSAGE = (
    f"Use {', '.join(repr(name) for name in _QUALITY_KEYWORDS)}, or a height in "
    f"pixels the video offers (e.g. {', '.join(_QUALITY_EXAMPLE_HEIGHTS)})."
)


def _quality_option() -> Any:
    """Build the shared ``--quality`` option definition.

    VK height ladders are non-standard (a single video may offer 106p through
    1610p), so the option accepts a free-form token validated by
    :func:`_validate_quality` instead of a closed enum.

    Returns:
        A Typer option definition carrying the shared callback and help text.
    """
    return typer.Option(
        "best",
        "--quality",
        callback=_validate_quality,
        help=_QUALITY_OPTION_HELP,
    )


def _validate_quality(ctx: typer.Context, param: typer.CallbackParam, value: str) -> str:
    """Validate ``--quality`` during argument parsing.

    This is the single validation point for the option: it runs before the
    command body, so a bad token is a usage error (exit code 2) and nothing is
    attempted. The body then parses the accepted token into a ``QualitySpec``.

    Args:
        ctx: Click context (unused).
        param: The parameter being parsed (unused).
        value: Raw token supplied by the user.

    Returns:
        The unchanged token, which the command body parses into a QualitySpec.

    Raises:
        typer.BadParameter: If the token is not a keyword or a positive height.
    """
    try:
        QualitySpec.parse(value)
    except QualityParseError:
        raise typer.BadParameter(_QUALITY_REJECTION_MESSAGE) from None
    return value


# The --method option accepts the values of DownloadMethod (yt-dlp and
# auto). The help text lists the valid values but cannot name ffmpeg —
# test_method_help_text_excludes_ffmpeg pins ffmpeg's absence from --help —
# so the migration note that names the retired loader lives in the rejection
# message, rendered from the constant below so it cannot drift from the
# --method help text and the reference docs.
_METHOD_OPTION_HELP = "Download method: yt-dlp or auto"
_METHOD_REJECTION_MESSAGE = (
    "Choose from 'yt-dlp' or 'auto'. "
    "The ffmpeg download method was removed; "
    "ffmpeg is still required to merge downloaded segments."
)


def _validate_method(ctx: typer.Context, param: typer.CallbackParam, value: str) -> str:
    """Validate ``--method`` during argument parsing.

    Mirrors the ``--quality`` callback: the option is typed ``str`` so that
    the callback — not a closed enum coercion — performs validation, allowing
    a tailorised message for the retired ``ffmpeg`` value. An invalid token
    is a usage error (exit code 2) carrying a migration note that names the
    valid choices, explains that the ffmpeg *loader* was removed, and states
    that ffmpeg *as the segment-merge engine* is still required.

    Args:
        ctx: Click context (unused).
        param: The parameter being parsed (unused).
        value: Raw token supplied by the user.

    Returns:
        The unchanged token, one of the ``DownloadMethod`` values.

    Raises:
        typer.BadParameter: If the token is not a valid ``DownloadMethod``.
    """
    try:
        DownloadMethod(value)
    except ValueError:
        raise typer.BadParameter(_METHOD_REJECTION_MESSAGE) from None
    return value


app = typer.Typer(
    name="vkdownloader",
    help="Download videos from vkvideo.ru with quality selection support",
)


@app.command()
def download(
    url: str = typer.Argument(..., help="VK Video URL to download"),
    quality: str = _quality_option(),
    output: Path = typer.Option(
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded video",
    ),
    method: str = typer.Option(
        "auto",
        "--method",
        "-m",
        callback=_validate_method,
        help=_METHOD_OPTION_HELP,
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
                quality_spec,
                output,
                DownloadMethod(method),
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
        # The --quality callback already rejected anything unparseable during
        # argument parsing, so this cannot fail; it produces the typed request.
        quality_spec = QualitySpec.parse(quality)
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
        raise typer.Exit(code=3) from None
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
            # `requested` is already the canonical token (a keyword or a bare
            # height such as "1072"); appending "p" would render "bestp".
            typer.echo(
                f"\nRequested quality '{requested}' is not available for this video.",
                err=True,
            )
            typer.echo(f"Available qualities: {', '.join(available_qualities)}", err=True)
        raise typer.Exit(code=1) from None
    except VideoNotFoundError:
        typer.echo("Video not found. Verify the URL is correct and the video is public.", err=True)
        raise typer.Exit(code=1) from None
    except _PreambleFailure as exc:
        _render_preamble_failure(exc)
        raise typer.Exit(code=3) from None
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
    quality: str = _quality_option(),
    output: Path = typer.Option(
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded videos",
    ),
    method: str = typer.Option(
        "auto",
        "--method",
        "-m",
        callback=_validate_method,
        help=_METHOD_OPTION_HELP,
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

        # The --quality callback already rejected anything unparseable during
        # argument parsing, so this cannot fail; it produces the typed request.
        quality_spec = QualitySpec.parse(quality)
        settings = _run_command_preamble(
            cookie_source=cookie_source, ssl_verify=ssl_verify, max_retries=max_retries
        )

        # Read the URL file narrowly so a read failure produces the precise
        # "Failed to read URL file" message while every other OSError
        # (e.g. from the batch run) falls through to the generic catch-all.
        try:
            raw_urls = urls_file.read_text()
        except OSError as e:
            typer.echo(f"Failed to read URL file: {urls_file} — {e}", err=True)
            raise typer.Exit(code=1) from None

        # Read and validate URLs from file
        for line in raw_urls.splitlines():
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
                quality_spec,
                DownloadMethod(method),
                settings,
                output,
                skipped_count,
            )
        )
        raise typer.Exit(code=exit_code)

    except ValidationError as e:
        typer.echo(format_validation_error(e), err=True)
        raise typer.Exit(code=3) from None
    except _PreambleFailure as exc:
        _render_preamble_failure(exc)
        raise typer.Exit(code=3) from None
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
