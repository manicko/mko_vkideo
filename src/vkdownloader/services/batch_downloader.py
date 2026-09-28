"""Batch download orchestration service for VK Video Downloader.

Encapsulates the concurrency orchestration, progress display, and result
aggregation for batch downloads, keeping the CLI entry layer thin
(argument parsing -> service call -> result presentation).

The orchestration was previously embedded in ``cli.py``; it has been
extracted here so it is unit-testable without invoking the Typer CLI.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import typer
from structlog import get_logger

from ..config import Settings
from ..exceptions import (
    ExtractionError,
    QualityNotAvailableError,
    VideoNotFoundError,
    VKDownloadError,
)
from ..models.enums import DownloadMethod, ProgressStatus, QualityEnum
from ..services.downloader import download_video
from ..services.downloader_throttle import URLBackoffCoordinator
from ..services.progress_display import RichProgressReporter
from ..services.signal_handlers import cleanup_signal_handlers, setup_signal_handlers
from ..utils.correlation import bind_correlation_id, clear_correlation_id, generate_correlation_id
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


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
    reporter: RichProgressReporter | None = None
    peak_tracker: ConcurrencyTracker | None = None


def _to_progress_status(status: str) -> ProgressStatus:
    """Map a batch result status string to a :class:`ProgressStatus`.

    ``progress_display`` uses ``ProgressStatus`` members for terminal
    status markers; the batch layer produces status strings, so this
    helper bridges the two representations.

    Args:
        status: A status string returned by ``_download_single``.

    Returns:
        The corresponding ``ProgressStatus`` enum member.
    """
    if status == ProgressStatus.SUCCESS.value:
        return ProgressStatus.SUCCESS
    if status == ProgressStatus.CANCELLED.value:
        return ProgressStatus.CANCELLED
    return ProgressStatus.FAILED


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
    peak_tracker = context.peak_tracker if context else None
    reporter = context.reporter if context else None

    # Wrap semaphore with concurrency tracker so peak is measured at the
    # actual point of concurrency limiting, not the configured maximum.
    tracked_semaphore = None
    if shared_semaphore is not None and peak_tracker is not None:
        tracked_semaphore = _TrackedSemaphore(shared_semaphore, peak_tracker)

    # Bind a per-operation correlation ID so every log entry within this
    # download carries a traceable identifier in both single and batch mode.
    correlation_id = generate_correlation_id()
    bind_correlation_id(correlation_id)

    # Closures route progress/title data through the reporter when present.
    # The reporter methods are themselves no-ops when disabled (non-TTY), so
    # the ``if reporter is not None`` guard only handles the single-download
    # path where no context (and therefore no reporter) exists.
    def _on_progress(video_id: str, downloaded: int, total: int) -> None:
        if reporter is not None:
            reporter.update(index, downloaded, total)

    def _on_title(sanitized_title: str) -> None:
        if reporter is not None:
            reporter.set_title(index, sanitized_title)

    def _finish(status: ProgressStatus) -> None:
        if reporter is not None:
            reporter.finish_task(index, status)

    echo: bool = True
    progress_cb: Callable[[str, int, int], None] | None = None
    title_cb: Callable[[str], None] | None = None

    if reporter is not None:
        # is_enabled only AFTER start() has been called (done in
        # _run_batch_with_progress). Reading it before start() would reflect the
        # pre-start stderr state instead of the resolved Console; echo suppression
        # (R5/AC2) keeps yt-dlp's native console output silent when the rich
        # display owns the terminal.
        echo = not reporter.is_enabled
        progress_cb = _on_progress
        title_cb = _on_title

    try:
        if reporter is not None:
            reporter.start_task(index)

        result = await download_video(
            url,
            quality,
            output,
            method,
            settings,
            max_retries_override=max_retries_override,
            backoff_coordinator=backoff_coordinator,
            semaphore=tracked_semaphore,
            progress_callback=progress_cb,
            output_index=index,
            echo=echo,
            title_callback=title_cb,
        )
        status = "success" if result else "failed"
        _finish(_to_progress_status(status))
        return (url, str(result) if result else "", status)

    except asyncio.CancelledError:
        # Re-raise CancelledError to allow batch cancellation, but still
        # mark the task as cancelled so the terminal shows a status line (R3).
        _finish(ProgressStatus.CANCELLED)
        raise
    except QualityNotAvailableError as e:
        _finish(ProgressStatus.FAILED)
        return (url, "", e.status_label())
    except VideoNotFoundError as e:
        _finish(ProgressStatus.FAILED)
        return (url, "", e.status_label())
    except ExtractionError as e:
        logger.error(
            "extraction_error",
            url=_strip_auth_params(url),
            correlation_id=correlation_id,
            **e.log_context(),
        )
        _finish(ProgressStatus.FAILED)
        return (url, "", e.status_label())
    except VKDownloadError as e:
        _finish(ProgressStatus.FAILED)
        return (url, "", e.status_label())
    except Exception as e:
        # Log unexpected exceptions to surface bugs, then return as a status tuple.
        # VKDownloadError subclasses are already handled by the earlier
        # except clauses which use exc.status_label() (the documented
        # replacement for the legacy _map_exception_to_status helper).
        # Only non-domain exceptions reach here — label them with their type.
        logger.exception(
            "unexpected_error_in_batch_download",
            url=_strip_auth_params(url),
            correlation_id=correlation_id,
        )
        _finish(ProgressStatus.FAILED)
        return (url, "", f"unexpected_error: {type(e).__name__}")
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
        Tuple of (results, peak_concurrent) where results is a list of
        (url, output_path, status) tuples.
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

        # One RichProgressReporter per batch run: it is constructed here, never
        # as a module-level singleton, because a singleton would carry mutable
        # state across batch invocations and its start()/stop() lifecycle must
        # not be shared between runs.
        reporter = RichProgressReporter()

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
                        reporter=reporter,
                        peak_tracker=concurrency_tracker,
                    ),
                )
            )
            for i, url in enumerate(urls)
        ]

        try:
            # start() must run before the first await below: the tasks created
            # above are scheduled with asyncio.create_task but do not run until
            # the loop yields, and there is no await between task creation and
            # here. start() is inside this try so the finally's stop() still
            # runs if start() raises.
            reporter.start()
            for coro in asyncio.as_completed(tasks):
                try:
                    await coro
                except asyncio.CancelledError:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise

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
            # stop() is placed in this finally so it also runs when the batch
            # is cancelled (CancelledError), restoring the terminal to normal
            # output per R3.
            reporter.stop()
    finally:
        # Cleanup signal handlers to allow re-registration on subsequent loops
        cleanup_signal_handlers()
        clear_correlation_id()


def _print_batch_summary(
    results: list[tuple[str, str, str]],
    max_concurrent: int,
    skipped_count: int = 0,
) -> int:
    """Print batch download summary.

    Args:
        results: List of result tuples (url, output_path, status).
        max_concurrent: Measured peak concurrency during the batch.
        skipped_count: Number of invalid URLs skipped during validation.

    Returns:
        Exit code: 0 if all downloads succeeded, 1 if any failed.
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
    return 1 if failed > 0 else 0


async def run_batch(
    urls: list[str],
    quality: QualityEnum,
    method: DownloadMethod,
    settings: Settings,
    max_retries: int | None,
    output: Path,
    skipped_count: int = 0,
) -> int:
    """Run a full batch download: orchestration + summary, returning an exit code.

    This is the public entry point for batch download orchestration, called
    by the CLI handler.  It orchestrates concurrent downloads with progress
    display, prints a summary, and returns a process exit code.

    Args:
        urls: List of validated video URLs to download.
        quality: Video quality selection for all downloads.
        method: Download method (yt-dlp, ffmpeg, or auto).
        settings: Application settings.
        max_retries: Maximum retry attempts for failed segment downloads.
        output: Output directory for downloaded videos.
        skipped_count: Number of invalid URLs skipped during validation.

    Returns:
        Exit code: 0 if all downloads succeeded, 1 if any failed.
    """
    results, peak_concurrent = await _run_batch_with_progress(
        urls, quality, method, settings, max_retries, output
    )
    return _print_batch_summary(results, peak_concurrent, skipped_count)
