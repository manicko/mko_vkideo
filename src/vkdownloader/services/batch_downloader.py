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
from ..models.enums import DownloadMethod, ProgressStatus
from ..models.quality import QualitySpec
from ..models.video import Stream, VideoWithStreams
from ..services.downloader import download_video
from ..services.downloader_throttle import URLBackoffCoordinator, get_shutdown_event
from ..services.extractor import VIDEO_ID_PATTERN, VKVideoExtractor, _extract_video_segment
from ..services.progress_display import RichProgressReporter
from ..services.signal_handlers import cleanup_signal_handlers, setup_signal_handlers
from ..utils.correlation import (
    bind_correlation_id,
    clear_correlation_id,
    generate_correlation_id,
    get_correlation_id,
)
from ..utils.security import _resolve_output_file
from ..utils.url_sanitizer import _strip_auth_params
from .quality import QualitySelector

logger = get_logger(__name__)


@dataclass
class ConcurrencyTracker:
    """Track the peak number of concurrently in-flight video downloads.

    Incremented when a video download acquires the shared semaphore and
    decremented when it releases, so the peak reflects actual concurrency
    rather than the configured maximum. The unit is **videos**, not segments:
    the batch semaphore gates one permit per video (see D-01).
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
    """Semaphore wrapper that tracks peak concurrency of in-flight video downloads.

    Wraps the batch-level ``asyncio.Semaphore`` that gates one permit per video.
    The segment layer must **not** re-acquire from this semaphore per segment:
    ``asyncio.Semaphore`` is not reentrant, and re-acquiring would deadlock once
    all video permits are held (D-01). The segment fan-out is bounded by a
    separate semaphore the segment layer owns.

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
    video_data: VideoWithStreams | None = None
    selected_stream: Stream | None = None


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


def _classify_download_result(result: Path | None) -> str:
    """Classify a completed download into a batch status string.

    A transfer that produced an output file succeeded. A transfer that
    produced nothing is only a *failure* when the user did not ask for it
    to stop: the signal handler sets the shutdown Event rather than
    cancelling the task outright, so an interrupted item usually returns
    ``None`` instead of raising. Classifying that return value as a failure
    would report the user's own interruption as broken videos, which is the
    defect this helper exists to prevent (D-04).

    The predicate deliberately mirrors the single-download path in
    ``cli.py``: ``result is None and get_shutdown_event().is_set()``.

    Only the *returning* path is classified here. A download that raised a
    domain error reported its own status label, and a download that raised
    ``CancelledError`` never reaches this function at all.

    Args:
        result: The output file returned by ``download_video``, or ``None``
            when the transfer produced no file.

    Returns:
        ``ProgressStatus.SUCCESS.value``, ``ProgressStatus.CANCELLED.value``,
        or ``ProgressStatus.FAILED.value``.
    """
    if result is not None:
        return ProgressStatus.SUCCESS.value
    if get_shutdown_event().is_set():
        return ProgressStatus.CANCELLED.value
    return ProgressStatus.FAILED.value


def _extract_video_id(url: str) -> str:
    """Extract the canonical video-id segment from a URL for structured logs.

    Wraps the segment→pattern match that the ``ExtractionError`` arm of
    ``_download_single`` performs inline, so every logging arm emits a
    consistent ``video_id`` field without duplicating the pattern logic.

    Args:
        url: Video URL to extract an identifier from.

    Returns:
        The captured video-id group, or ``"unknown"`` when the segment
        does not match ``VIDEO_ID_PATTERN``.
    """
    segment = _extract_video_segment(url)
    match = VIDEO_ID_PATTERN.fullmatch(segment) if segment else None
    return match.group(2) if match else "unknown"


async def _download_single(
    url: str,
    quality: QualitySpec,
    output: Path,
    method: DownloadMethod,
    settings: Settings,
    context: DownloadContext | None = None,
) -> tuple[str, str, str]:
    """Download a single video and return result tuple.

    Args:
        url: Video URL to download.
        quality: Parsed quality request (keyword or exact stream label).
        output: Output directory for downloaded video.
        method: Download method (yt-dlp or auto).
        settings: Application settings with environment-loaded values.
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
    video_data = context.video_data if context else None
    selected_stream = context.selected_stream if context else None

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
            reporter.set_video_id(index, video_id)
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
        # is_enabled is memoised per reporter instance (resolved once on first
        # access, see RichProgressReporter.is_enabled), so it is safe to read
        # here before start() runs. Echo suppression (R5/AC2) keeps yt-dlp's
        # native console output silent when the rich display owns the terminal.
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
            backoff_coordinator=backoff_coordinator,
            semaphore=tracked_semaphore,
            progress_callback=progress_cb,
            output_index=index,
            echo=echo,
            title_callback=title_cb,
            video_data=video_data,
            selected_stream=selected_stream,
        )
        status = _classify_download_result(result)
        _finish(_to_progress_status(status))
        return (url, str(result) if result else "", status)

    except asyncio.CancelledError:
        # Re-raise CancelledError to allow batch cancellation, but still
        # mark the task as cancelled so the terminal shows a status line (R3).
        #
        # This is the *raising* cancellation route: the task was cancelled
        # outright and never returned a value. The *returning* route is the
        # common one during a Ctrl-C — the signal handler sets the shutdown
        # Event and the transfer unwinds to a plain ``None`` result, which
        # _classify_download_result() above turns into the same cancelled
        # status. Both routes therefore end as ProgressStatus.CANCELLED.
        _finish(ProgressStatus.CANCELLED)
        raise
    except QualityNotAvailableError as e:
        _finish(ProgressStatus.FAILED)
        logger.error(
            "quality_not_available",
            url=_strip_auth_params(url),
            video_id=_extract_video_id(url),
            correlation_id=get_correlation_id(),
            **e.log_context(),
        )
        return (url, "", e.status_label())
    except VideoNotFoundError as e:
        _finish(ProgressStatus.FAILED)
        logger.error(
            "video_not_found",
            url=_strip_auth_params(url),
            video_id=_extract_video_id(url),
            correlation_id=get_correlation_id(),
            **e.log_context(),
        )
        return (url, "", e.status_label())
    except ExtractionError as e:
        logger.error(
            "extraction_error",
            url=_strip_auth_params(url),
            video_id=_extract_video_id(url),
            correlation_id=get_correlation_id(),
            **e.log_context(),
        )
        _finish(ProgressStatus.FAILED)
        return (url, "", e.status_label())
    except VKDownloadError as e:
        _finish(ProgressStatus.FAILED)
        logger.error(
            "download_error",
            url=_strip_auth_params(url),
            video_id=_extract_video_id(url),
            correlation_id=get_correlation_id(),
            **e.log_context(),
        )
        return (url, "", e.status_label())
    except Exception as e:
        # Log unexpected exceptions to surface bugs, then return as a status tuple.
        # VKDownloadError subclasses are already handled by the earlier
        # except clauses which use exc.status_label() directly.
        # Only non-domain exceptions reach here — label them with their type.
        logger.exception(
            "unexpected_error_in_batch_download",
            url=_strip_auth_params(url),
        )
        _finish(ProgressStatus.FAILED)
        return (url, "", f"unexpected_error: {type(e).__name__}")
    finally:
        clear_correlation_id()


async def _run_batch_with_progress(
    urls: list[str],
    quality: QualitySpec,
    method: DownloadMethod,
    settings: Settings,
    output: Path,
) -> tuple[list[tuple[str, str, str]], int]:
    """Run batch download with progress tracking.

    Args:
        urls: List of video URLs to download.
        quality: Parsed quality request (keyword or exact stream label) for all downloads.
        method: Download method (yt-dlp or auto).
        settings: Application settings.
        output: Output directory for downloaded videos.

    Returns:
        Tuple of (results, peak_concurrent_videos) where results is a list of
        (url, output_path, status) tuples.

    Exact-URL duplicates within the batch are skipped (ProgressStatus.SKIPPED)
    before any network call, never launching a second download for the same URL.
    """
    # Setup signal handlers inside async context
    setup_signal_handlers()
    batch_correlation_id = generate_correlation_id()
    bind_correlation_id(batch_correlation_id)
    try:
        # Create shared semaphore (one permit per video) and backoff coordinator at batch level
        concurrency_tracker = ConcurrencyTracker()
        shared_semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        backoff_coordinator = URLBackoffCoordinator(pause_seconds=settings.backoff_pause_seconds)

        logger.info(
            "batch_download_started",
            url_file_count=len(urls),
        )

        # One RichProgressReporter per batch run: it is constructed here, never
        # as a module-level singleton, because a singleton would carry mutable
        # state across batch invocations and its start()/stop() lifecycle must
        # not be shared between runs.
        reporter = RichProgressReporter()

        # Bounded producer: keep one asyncio.Task per URL but bound only the
        # number of LIVE task objects to the configured ceiling (CON-003). The
        # window is a len() comparison — no permit object is created, and the
        # batch permit (D-01) is still acquired once-per-video inside
        # _download_single -> download_video -> perform_download, untouched here.
        # urls_left is the lazy source: it yields URL work without creating
        # tasks, so the pump owns task creation and can bound the live set.
        pending: dict[asyncio.Task[tuple[str, str, str]], int] = {}
        by_index: dict[int, tuple[str, str, str]] = {}
        seen_urls: set[str] = set()
        urls_left = iter(enumerate(urls))

        try:
            # reporter.start() MUST precede the first asyncio.create_task, not
            # merely the first await. A bounded producer creates its ceiling of
            # tasks up front and then awaits in the FIRST_COMPLETED pump; that
            # await yields control to the loop, which would let the created
            # tasks run and emit log records before start() — which re-points
            # the log handlers (_repoint_log_handlers) — has run. Ordering
            # start() ahead of create_task within this single synchronous block
            # makes the guarantee rest on statement order alone, so a future
            # edit that inserts an await between create_task and start() cannot
            # silently re-break it. (The pre-B7 invariant was "no await between
            # task creation and start()"; a bounded producer invalidates it, so
            # that wording is retired.) start() is inside this try so the
            # finally's stop() still runs if start() raises.
            reporter.start()

            # --- Pre-pass: resolve every URL to its output path before dispatch (B10, Decision A) ---
            # Each URL is extracted once; the resolved Path is the dedup key.
            # Last occurrence wins; earlier entries are terminalised as SKIPPED
            # before any asyncio.create_task, so no media transfer occurs for a skipped entry.
            _batch_extractor = VKVideoExtractor(settings=settings, backoff_coordinator=None)
            _batch_selector = QualitySelector()
            _resolved: list[tuple[VideoWithStreams, Stream, Path] | str | None] = [None] * len(urls)
            # Tier 1 pre-pass guard: exact-URL duplicates must not be extracted a
            # second time. _pre_pass_seen_urls is intentionally distinct from the
            # fill-phase loop's ``seen_urls`` — it is populated here, before the
            # fill-phase loop runs, so that the fill-phase Tier 1 check still
            # sees an empty ``seen_urls`` on the first occurrence and can own
            # the first-wins terminalisation (DEC-W R1). Duplicates land in
            # ``_resolved[i] = None`` and fall through to the fill-phase
            # ``if url in seen_urls`` branch for first-wins SKIPPED terminalisation.
            _pre_pass_seen_urls: set[str] = set()
            for i, url in enumerate(urls):
                if url in _pre_pass_seen_urls:
                    _resolved[i] = (
                        None  # Tier 1 duplicate — let fill-phase loop terminalise (first-wins)
                    )
                    continue
                _pre_pass_seen_urls.add(url)
                try:
                    _video = await _batch_extractor.extract_streams(url)
                    _stream = _batch_selector.select(_video.streams, quality)
                    _resolved[i] = (
                        _video,
                        _stream,
                        _resolve_output_file(_video, output, settings, i),
                    )
                except (
                    ExtractionError,
                    QualityNotAvailableError,
                    VideoNotFoundError,
                    VKDownloadError,
                ) as exc:
                    _status = exc.status_label()
                    _resolved[i] = _status
                    by_index[i] = (url, "", _status)
                    reporter.start_task(i)
                    reporter.finish_task(i, ProgressStatus.FAILED)

            # Tier 2: filename-collision dedup (last-wins). Terminalise losers before dispatch.
            _filename_registry: dict[Path, int] = {}
            for i, entry in enumerate(_resolved):
                if isinstance(entry, str) or entry is None:
                    continue
                _, _, resolved_path = entry
                if resolved_path in _filename_registry:
                    _loser = _filename_registry[resolved_path]
                    if _loser not in by_index:
                        logger.info("filename_collision_skipped", url=urls[_loser], index=_loser)
                        reporter.start_task(_loser)
                        reporter.finish_task(_loser, ProgressStatus.SKIPPED)
                        by_index[_loser] = (urls[_loser], "", ProgressStatus.SKIPPED.value)
                _filename_registry[resolved_path] = i
            # --- end pre-pass ---

            # Fill phase: consume the lazy source, spinning up one task per
            # non-duplicate URL and pumping (draining completed tasks) only
            # once the live window is full. Every pulled item is stored in
            # by_index: duplicates are stored directly (with the dedup
            # ``continue`` placed *after* the store, never before), and
            # non-duplicates are stored via their task's eventual result.
            # No break/return drops a pulled URL before it is stored
            # (measured: a drop there loses one URL per full window).
            for i, url in urls_left:
                # Pre-pass may have terminalised this index (extraction error
                # or filename-collision dedup) — skip it without dispatch.
                if i in by_index:
                    continue
                # Tier 1 dedup (DEC-W R1): exact-URL duplicates are skipped
                # before any network call, never launching a second media
                # download. The item is terminalised via finish_task so the
                # progress display renders the [⊘] skipped marker, matching
                # the contract that every batch item reaches finish_task.
                if url in seen_urls:
                    logger.info("duplicate_url_skipped", url=_strip_auth_params(url), index=i)
                    reporter.start_task(i)
                    reporter.finish_task(i, ProgressStatus.SKIPPED)
                    by_index[i] = (url, "", ProgressStatus.SKIPPED.value)
                    continue
                seen_urls.add(url)
                if len(pending) >= settings.max_concurrent_downloads:
                    done, _ = await asyncio.wait(list(pending), return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        by_index[pending.pop(task)] = task.result()
                # Forward pre-resolved video_data and selected_stream from the
                # pre-pass so download_video skips its own extraction. Binding
                # _resolved[i] to a local makes the tuple narrowing type-checkable.
                _resolved_entry = _resolved[i]
                _pre_video_data = _resolved_entry[0] if isinstance(_resolved_entry, tuple) else None
                _pre_selected_stream = (
                    _resolved_entry[1] if isinstance(_resolved_entry, tuple) else None
                )
                pending[
                    asyncio.create_task(
                        _download_single(
                            url,
                            quality,
                            output,
                            method,
                            settings,
                            DownloadContext(
                                index=i,
                                shared_semaphore=shared_semaphore,
                                backoff_coordinator=backoff_coordinator,
                                reporter=reporter,
                                peak_tracker=concurrency_tracker,
                                video_data=_pre_video_data,
                                selected_stream=_pre_selected_stream,
                            ),
                        )
                    )
                ] = i

            # Drain phase: the source is exhausted, settle every still-live task.
            while pending:
                done, _ = await asyncio.wait(list(pending), return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    by_index[pending.pop(task)] = task.result()

            # Restore URL-index ordering: the FIRST_COMPLETED pump completes
            # tasks out of creation order. A gap in by_index raises KeyError
            # here — a loud failure, the right failure mode beside the
            # falsy-result lesson of VAL-402.
            results = [by_index[i] for i in range(len(urls))]
            # The cancelled literal comes from the same ProgressStatus member
            # _classify_download_result() uses, so the two classification
            # sites cannot drift apart.
            processed_results = [
                r
                if isinstance(r, tuple)
                else (urls[i], "", ProgressStatus.CANCELLED.value)
                if isinstance(r, asyncio.CancelledError)
                else (urls[i], "", f"unexpected_error: {type(r).__name__}")
                for i, r in enumerate(results)
            ]
            return processed_results, concurrency_tracker.peak
        except asyncio.CancelledError:
            # Cancellation reaches the live siblings here: cancel the ones still
            # running and gather them so none outlives the operation. This is
            # the fan-out B2 makes live; the body is byte-identical to the
            # pre-B7 branch except it iterates the live `pending` set instead of
            # the full task list — semantically equivalent, since a completed
            # task needs no cancelling. Both 130 routes depend on it; do not
            # restructure.
            for task in pending:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            raise
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
    peak_concurrent_videos: int,
    skipped_count: int = 0,
) -> int:
    """Print batch download summary.

    Args:
        results: List of result tuples (url, output_path, status).
        peak_concurrent_videos: Measured peak number of concurrently in-flight
            video downloads during the batch.
        skipped_count: Number of invalid URLs skipped during validation.

    Returns:
        Exit code, three-way:

        * ``130`` if at least one download was cancelled by the user.
        * ``1`` if no download was cancelled and at least one failed.
        * ``0`` if every download succeeded (skipped items do not affect the
          exit code — a deduplicated URL is neither a failure nor a success).

        Cancellation takes precedence over failure: an interrupted run did
        not complete by the user's own doing, so its remaining "failures"
        are indistinguishable from work the interruption cut short. Reporting
        the interruption as such is the more truthful answer (D-04).
    """
    # Print results
    for url, output_path, status in results:
        typer.echo(f"{url}: {status}" + (f" -> {output_path}" if output_path else ""))

    # Summary. Success, cancellation, skip and failure are four distinct outcomes.
    # Each is counted explicitly so the aggregation can never misclassify one as
    # another — the previous subtraction rule (failed = total - success - cancelled)
    # would silently absorb a SKIPPED entry into the failed count (OUT-009).
    successful = sum(1 for _, _, status in results if status == ProgressStatus.SUCCESS.value)
    cancelled = sum(1 for _, _, status in results if status == ProgressStatus.CANCELLED.value)
    skipped = sum(1 for _, _, status in results if status == ProgressStatus.SKIPPED.value)
    failed = sum(
        1
        for _, _, status in results
        if status
        not in (
            ProgressStatus.SUCCESS.value,
            ProgressStatus.CANCELLED.value,
            ProgressStatus.SKIPPED.value,
        )
    )

    typer.echo("\n\nDownload Summary:")
    typer.echo(f"  Total videos: {len(results)}")
    if skipped_count > 0:
        typer.echo(f"  Skipped (invalid URLs): {skipped_count}")
    if skipped > 0:
        typer.echo(f"  Skipped (duplicates): {skipped}")
    typer.echo(f"  Peak concurrent videos: {peak_concurrent_videos}")
    typer.echo(f"  Successful: {successful}")
    typer.echo(f"  Failed: {failed}")
    if cancelled > 0:
        typer.echo(f"  Cancelled: {cancelled}")

    # Show failed URLs with error reasons. Cancelled and skipped items are
    # excluded: they were not failures and must not be listed as ones.
    failed_urls = [
        (url, status)
        for url, _, status in results
        if status
        not in (
            ProgressStatus.SUCCESS.value,
            ProgressStatus.CANCELLED.value,
            ProgressStatus.SKIPPED.value,
        )
    ]
    if failed_urls:
        typer.echo("  Failed URLs:")
        for url, status in failed_urls:
            typer.echo(f"    - {url}: {status}")

    if cancelled > 0:
        # Phrased as a possibility, not a measurement: the batch layer did
        # not count the segments itself, the segment layer does that and logs
        # preserving_segments_for_resume whenever it leaves data on disk.
        typer.echo(
            "  Interrupted by user: any partial segments already downloaded"
            " were preserved for resume; re-run this command to resume them."
        )
        return 130

    # Exit with code 1 if any downloads failed
    return 1 if failed > 0 else 0


async def run_batch(
    urls: list[str],
    quality: QualitySpec,
    method: DownloadMethod,
    settings: Settings,
    output: Path,
    skipped_count: int = 0,
) -> int:
    """Run a full batch download: orchestration + summary, returning an exit code.

    This is the public entry point for batch download orchestration, called
    by the CLI handler.  It orchestrates concurrent downloads with progress
    display, prints a summary, and returns a process exit code.

    Args:
        urls: List of validated video URLs to download.
        quality: Parsed quality request (keyword or exact stream label) for all downloads.
        method: Download method (yt-dlp or auto).
        settings: Application settings.
        output: Output directory for downloaded videos.
        skipped_count: Number of invalid URLs skipped during validation.

    Returns:
        Exit code, three-way: ``0`` if all downloads succeeded, ``1`` if any
        failed, ``130`` if any download was cancelled by the user. Cancellation
        wins over failure — see :func:`_print_batch_summary`, which computes it.
    """
    results, peak_concurrent_videos = await _run_batch_with_progress(
        urls, quality, method, settings, output
    )
    return _print_batch_summary(results, peak_concurrent_videos, skipped_count)
