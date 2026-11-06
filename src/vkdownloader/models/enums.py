"""Domain enums for VK Video Downloader."""

from enum import StrEnum


class QualityKind(StrEnum):
    """How a quality request is resolved against the streams of a video.

    VK publishes non-standard height ladders (for example 106p, 178p, 268p,
    358p, 536p, 804p, 1072p, 1610p), so the set of selectable resolutions
    cannot be a closed enum of "known" values. A request is therefore either
    a keyword (``BEST`` / ``WORST``) or an exact match against the quality
    label of one stream (``EXACT``).
    """

    BEST = "best"
    WORST = "worst"
    EXACT = "exact"


class QualityLabel(StrEnum):
    """Fixed stream quality labels assigned by the extractor.

    These are labels written onto :class:`~vkdownloader.models.video.Stream`
    records, not user selection modes — a stream whose height cannot be
    determined (browser HLS capture) is labelled ``UNKNOWN``.
    """

    UNKNOWN = "unknown"


class StreamFormat(StrEnum):
    """Stream format types."""

    HLS = "hls"
    MP4 = "mp4"


class LogLevel(StrEnum):
    """Standard logging level options."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DownloadMethod(StrEnum):
    """Download method options."""

    YTDLP = "yt-dlp"
    AUTO = "auto"


class CookieSource(StrEnum):
    """Cookie acquisition strategy for video downloads."""

    NONE = "none"
    BROWSER = "browser"


class ErrorCode(StrEnum):
    """Machine-readable error codes for structured logging and filtering.

    Each domain exception carries one of these codes so that log
    aggregators and users can filter and group by specific failure
    modes in structured (JSON) logs.
    """

    VIDEO_NOT_FOUND = "video_not_found"
    INVALID_URL = "invalid_url"
    QUALITY_NOT_AVAILABLE = "quality_not_available"
    QUALITY_MISMATCH = "quality_mismatch"
    NO_STREAMS = "no_streams"
    QUALITY_PARSE_ERROR = "quality_parse_error"
    EXTRACTION_ERROR = "extraction_error"
    DOWNLOAD_ERROR = "download_error"
    STEALTH_ASSET_MISSING = "stealth_asset_missing"
    PATH_TRAVERSAL = "path_traversal"
    WORKSPACE_LOCKED = "workspace_locked"
    UNEXPECTED_ERROR = "unexpected_error"


class DownloadState(StrEnum):
    """Observable download state for the Block G state machine.

    States are intentionally string-valued so they round-trip through JSON
    state files and diagnostic logs without conversion.
    """

    CREATED = "created"
    RESOLVE_STREAM = "resolve_stream"
    VALIDATE_VARIANT = "validate_variant"
    DOWNLOAD = "download"
    RETRY_SAME_SEGMENT = "retry_same_segment"
    REFRESH_STREAM = "refresh_stream"
    RATE_LIMIT_WAIT = "rate_limit_wait"
    RETRY = "retry"
    VERIFY_MEDIA = "verify_media"
    COMMIT = "commit"
    DONE = "done"
    PRESERVE_AND_STOP = "preserve_and_stop"
    CANCELLED = "cancelled"
    DISK_FULL = "disk_full"
    FAILED_RETRY_BUDGET = "failed_retry_budget"
    INTEGRITY_FAILED = "integrity_failed"
    FAILED = "failed"


class ErrorCategory(StrEnum):
    """Classification of a download failure for state-machine transitions."""

    CONNECTION_TIMEOUT = "connection_timeout"
    CONNECTION_RESET = "connection_reset"
    AUTH_EXPIRED = "auth_expired"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    NOT_FOUND = "not_found"
    SLOW_THROUGHPUT = "slow_throughput"
    DISK_FULL = "disk_full"
    PERMISSION_ERROR = "permission_error"
    INVALID_OUTPUT_PATH = "invalid_output_path"
    CANCELLED = "cancelled"
    INCOMPATIBLE_PLAYLIST = "incompatible_playlist"
    INCOMPATIBLE_CODEC = "incompatible_codec"
    INTEGRITY_FAILURE = "integrity_failure"
    UNKNOWN = "unknown"


class ProgressStatus(StrEnum):
    """Download progress status for a single item.

    ``IN_PROGRESS`` is the non-terminal state set when a task is created;
    it is the only status that does not reach ``finish_task``. Every other
    member is terminal:

    ``SUCCESS`` is the normal completion of a download. ``SKIPPED`` is
    produced by the batch-level dedup checks in ``_run_batch_with_progress``
    when a duplicate is detected before any network call: Tier 1 (exact-URL
    duplicate) or Tier 2 (resolved-filename collision, last-wins);
    ``CANCELLED`` by the shutdown signal during a batch run or by an
    explicit ``CancelledError`` in single-download mode. ``FAILED`` covers
    every other outcome.
    """

    IN_PROGRESS = "in_progress"

    SUCCESS = "success"

    FAILED = "failed"

    SKIPPED = "skipped"

    CANCELLED = "cancelled"


# Terminal statuses: every member except IN_PROGRESS. Derived from the enum
# so a newly added status is automatically terminal unless it is the
# in-progress state, preventing this set from drifting out of sync with the
# enum definition.
TERMINAL_STATUSES: frozenset[ProgressStatus] = frozenset(
    member for member in ProgressStatus if member != ProgressStatus.IN_PROGRESS
)
