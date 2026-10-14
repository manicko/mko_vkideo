"""Configuration module for VK Video Downloader."""

import difflib
import io
import logging
import os
import sys
from pathlib import Path
from typing import IO, cast

import structlog
from dotenv import dotenv_values
from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings

from vkdownloader.models.enums import CookieSource, LogLevel
from vkdownloader.utils.url_sanitizer import redact_log_event


class Settings(BaseSettings):
    """Application settings with defaults and environment variable support.

    Configuration sources are resolved in priority order:
    1. Explicit keyword arguments to the constructor
    2. ``VKDOWNLOADER_*`` environment variables (``os.environ``)
    3. ``.env`` file in the current working directory
    4. Field defaults

    Note on unknown variables:
    - **``.env`` typos:** Rejected at construction with ``extra='forbid'``
      (a ValidationError). Use :func:`warn_unknown_env_vars` to detect them
      *before* construction crashes.
    - **OS environment typos:** Silently ignored by pydantic-settings
      (the default value is used). :func:`warn_unknown_env_vars` detects
      and warns about these.

    The .env file is resolved relative to the current working directory (CWD),
    not relative to the package installation location.
    """

    # Browser Automation settings
    headless: bool = Field(
        default=False,
        description="Run browser in headless mode (no GUI)",
    )
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for browser requests",
    )
    timezone: str = Field(
        default="Europe/Moscow",
        description="Timezone for the browser context",
    )
    locale: str = Field(
        default="ru-RU",
        description="Locale for the browser context",
    )
    stealth_enabled: bool = Field(
        default=False,
        description="Gates the browser anti-detection posture: when true, "
        "--disable-blink-features=AutomationControlled is passed to the "
        "chromium launch and stealth.min.js is injected as an init script. "
        "The stealth.min.js asset is a declared build artifact, so when this "
        "is true a missing asset is a hard error before the browser starts. "
        "Does NOT gate the browser context's viewport, user agent, locale or "
        "timezone, which are applied unconditionally as ordinary context "
        "identity. Disabled by default.",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed requests",
    )
    download_timeout: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Timeout in seconds applied to individual segment and playlist "
        "HTTP requests, to the off-loop yt-dlp extraction's wait_for, and to "
        "yt-dlp's socket timeout as a library option and as a CLI flag. "
        "Does NOT bound the ffmpeg merge subprocesses — each merge stage has its "
        "own separate per-stage budget (see ``_MERGE_STAGE_TIMEOUT`` in "
        "``ffmpeg_utils``). On expiry of that wait_for the extraction's OS thread "
        "is not stopped and cannot be; the executor is shut down non-blockingly "
        "(cancel_futures=True, wait=False) so the process is not held by it, and "
        "that teardown thread-join is bounded by ``shutdown_timeout``, not under "
        "this setting. Does not bound the yt-dlp child's post-drain re-wait — "
        "see ``download_stall_timeout`` for that inactivity bound. On retryable "
        "HTTP failures (408, 425, 429, 5xx), the exponential backoff delay is "
        "capped at 30 seconds per request — each request may wait up to that "
        "ceiling independently, so a batch of N concurrent videos may have "
        "multiple bounded waits in flight simultaneously.",
    )
    shutdown_timeout: float = Field(
        default=5.0,
        ge=1.0,
        le=60.0,
        description="Bound, in seconds, applied to the thread-join of the "
        "extraction executor at interpreter shutdown. When the off-loop yt-dlp "
        "extraction times out, its OS thread cannot be stopped — the "
        "``ThreadPoolExecutor`` is shut down non-blockingly "
        "(cancel_futures=True, wait=False) so the process is freed from the "
        "asyncio wait_for expiry, but the worker thread may still be running. "
        "This setting is the ceiling on how long the process will wait for "
        "that thread to drain during teardown, and is independent of — and "
        "normally far shorter than — ``download_timeout``, because the "
        "extraction has already been declared failed at that point and joining "
        "it longer serves nothing. CON-010 resolved.",
    )
    download_stall_timeout: float = Field(
        default=300.0,
        ge=30,
        le=3600,
        description="Inactivity bound, in seconds, on the one-shot re-wait that follows "
        "the yt-dlp reader consuming the download stream — ``process.wait()`` "
        "after EOF on the child's stdout. Once the reader task has drained every line "
        "and the child has gone silent, the clock starts: if the child has not exited "
        "within this many seconds it is terminated through the existing cancellation "
        "ladder (``cancel_subprocess``) and the resulting ``TimeoutError`` is "
        "re-raised. This is NOT a whole-operation budget — a download that keeps "
        "producing output is never killed, no matter how long it runs, because the "
        "reader's continued liveness holds the bound at bay until EOF. It does not "
        "apply to the ffmpeg merge subprocesses, which use a separate per-stage budget "
        "(``_MERGE_STAGE_TIMEOUT``).",
    )
    backoff_pause_seconds: int = Field(
        default=10,
        ge=1,
        le=120,
        description="Seconds a retryable transport failure pauses the origin before retrying, shared across all segment and manifest retries for that origin.",
    )
    browser_pre_interaction_wait: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Seconds to wait before video interaction in browser extraction",
    )
    browser_post_interaction_wait: int = Field(
        default=8,
        ge=1,
        le=30,
        description="Seconds to wait after video interaction in browser extraction",
    )
    ssl_verify: bool = Field(
        default=True,
        description="Verify SSL certificates for CDN connections",
    )

    # Download settings
    download_dir: Path = Field(
        default=Path.home() / "Downloads" / "vkdownloader",
        description="Directory for downloaded videos",
    )
    max_concurrent_downloads: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of videos downloading concurrently in a batch (1-16). "
        "The batch semaphore gates one permit per video. The segment fan-out within "
        "each video is bounded separately by ``max_concurrent_segments``. Each download's "
        "aiohttp connection pool is sized to this value for both the total and per-origin "
        "ceiling, so the transport never clips this setting. Setting this to 1 disables "
        "batch parallelism.",
    )
    max_concurrent_segments: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Maximum number of segments to download concurrently per video. "
        "Governs the segment fan-out semaphore and yt-dlp's -N (fragment concurrency) "
        "flag. The batch-level video gate remains governed by ``max_concurrent_downloads``. "
        "Setting this to 1 enables sequential segment download with an anti-detection delay.",
    )
    throttled_rate: int = Field(
        default=100000,
        ge=50000,
        le=1000000,
        description="Minimum download rate in bytes/sec. If yt-dlp's download rate falls below this threshold, yt-dlp aborts the download; the application then retries with a fresh token re-extract. Default is 100000 (100KB/s).",
    )
    http_chunk_size: int = Field(
        default=0,
        ge=0,
        le=104857600,
        description="HTTP chunk size in bytes for yt-dlp range-request downloads. "
        "Set to 0 (default) to disable --http-chunk-size for reliable HLS segment "
        "downloads. When non-zero, yt-dlp downloads each segment in fixed-size "
        "range requests, which can cause data corruption on CDNs that do not "
        "properly support HTTP Range headers. Advanced users only.",
    )
    cookie_source: CookieSource = Field(
        default=CookieSource.NONE,
        description="Cookie acquisition strategy: none or browser",
    )

    # Logging settings
    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_file: Path | None = Field(
        default=None,
        description="Optional log file path",
    )

    @field_validator("download_dir", mode="before")
    @classmethod
    def normalize_download_dir(cls, v: object) -> object:
        """Map empty-string download_dir to the field default (use-default semantics).

        An empty string typically arises when a user sets
        ``VKDOWNLOADER_DOWNLOAD_DIR=""`` in ``.env`` intending "use the default."
        Rather than crashing with an opaque ``path_type`` ValidationError, we
        silently fall back to the default download directory.

        This mirrors how ``log_file=""`` is handled (map to ``None`` for
        optional path fields) and ensures consistent empty-string behavior
        across all path-typed fields.
        """
        if v == "":
            return Settings.model_fields["download_dir"].default
        return v

    @field_validator("log_file", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: object) -> object:
        """Map empty-string log_file to None (no file logging).

        An empty string (e.g. ``VKDOWNLOADER_LOG_FILE=""``) is coerced to
        ``None`` so pydantic treats it as "no log file," consistent with the
        default. This is the same intent as ``normalize_download_dir`` for
        ``download_dir``: each path-typed field maps an empty string to its
        own declared default. The two differ only in what that default is.
        ``log_file`` is optional (``Path | None``) and defaults to ``None``,
        so empty means "no file"; ``download_dir`` is required (``Path``) and
        defaults to a concrete directory, so empty means "use the default
        directory". The behaviour is symmetric in intent -- each path field
        falls back to its own declared default -- so no audit-finding
        cross-reference is needed.
        """
        if v == "":
            return None
        return v

    @field_validator("user_agent", "timezone", "locale", mode="before")
    @classmethod
    def reject_empty_string(cls, v: object) -> object:
        """Reject an empty or whitespace-only free-text setting.

        An empty string (e.g. ``VKDOWNLOADER_USER_AGENT=``) is not a request
        for the default -- it is a request for an empty user-agent string --
        and the three free-text fields are forwarded verbatim into request
        headers, command lines and driver constructors, where an empty value
        is not neutral. There is no meaningful empty form for these, so the
        assignment must be removed to use the default rather than silently
        rewritten to it. This reuses the ``mode="before"`` pattern of
        ``normalize_download_dir`` and ``empty_string_to_none``; the field
        defaults are non-empty strings, so ``Settings()`` still constructs
        cleanly even though ``validate_default`` runs this validator against
        them.
        """
        if isinstance(v, str) and not v.strip():
            raise ValueError(
                "must not be empty or whitespace; remove the setting to use the default"
            )
        return v

    @field_validator("download_dir", "log_file", mode="after")
    @classmethod
    def expand_tilde_paths(cls, v: Path | None) -> Path | None:
        """Expand ``~`` and resolve to an absolute path.

        ``None`` values are passed through unchanged (empty-string inputs
        are handled separately by ``normalize_download_dir`` for download_dir
        and ``empty_string_to_none`` for log_file, and are not coerced to
        ``None`` here).
        """
        if v is None:
            return v
        return v.expanduser().resolve()

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str | LogLevel) -> LogLevel:
        """Coerce log level to uppercase and parse into LogLevel enum.

        Accepts a ``LogLevel`` directly or a string (e.g. ``"info"`` or
        ``"INFO"``), normalizing case for case-insensitive input.
        """
        if isinstance(v, LogLevel):
            return v
        return LogLevel(v.upper())

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "forbid",
        "env_prefix": "VKDOWNLOADER_",
        "hide_input_in_errors": True,
    }


_ENV_VAR_PREFIX = "VKDOWNLOADER_"


def _normalise_loc_to_env_var(loc: str) -> str:
    """Normalise a pydantic-reported location into the ``VKDOWNLOADER_*`` namespace.

    Strips one matching pair of surrounding quotes, strips the environment
    prefix when the location carries it (case-insensitively, because
    pydantic-settings lower-cased the key before reporting it), upper-cases
    the remainder and re-applies the prefix.

    The returned value is the **match key** — quote-stripped so that a
    quoted misspelling still resolves to the right target.  The caller is
    responsible for computing a quote-preserving display form when the
    quotes the user typed must stay visible in the rendered error line.

    The match key serves both namespaces: a constructor-keyword
    location (``maxretries``) is already a bare field name and normalises to
    ``VKDOWNLOADER_MAX_RETRIES``; an environment-file location
    (``vkdownloader_maxretries``) normalises to the same value, so the same
    matcher works regardless of which path produced the error.
    """
    if len(loc) >= 2 and loc[0] == loc[-1] and loc[0] in ("'", '"'):
        loc = loc[1:-1]
    if loc.lower().startswith(_ENV_VAR_PREFIX.lower()):
        loc = loc[len(_ENV_VAR_PREFIX) :]
    return _ENV_VAR_PREFIX + loc.upper()


def format_validation_error(error: ValidationError) -> str:
    """Format a Pydantic ValidationError into a concise, user-facing message.

    For ``extra_forbidden`` errors, normalises the reported location into the
    ``VKDOWNLOADER_*`` environment-variable namespace and suggests the closest
    valid variable name. Matching in one namespace avoids the namespace
    mismatch that produced confident wrong pointers — fuzzy-matching a 25-
    character prefixed, lower-cased key against 12-character field names —
    and an intent gate (``cutoff=0.9``) routes keys with no plausible target
    to the valid-name list rather than a wrong suggestion.

    The **displayed** location preserves any quotes the user typed, so a
    double-quoted key such as ``"VKDOWNLOADER_MAX_RETRIES"`` is shown with
    the quotes intact.  The **match key** is the quote-stripped form, so a
    quoted misspelling still resolves to the right target.  A self-referential
    suggestion (the closest match *is* the correct variable name) is
    suppressed: the valid-name list is shown instead, because the real
    problem is the quotes, not a typo.

    Args:
        error: The ValidationError to format.

    Returns:
        A human-readable string listing each field error with its valid range
        when the field carries ``Ge``/``Le`` constraints (e.g. ``max_retries`` →
        ``1..10``).
    """
    lines = [
        "Configuration error: one or more settings have invalid values.",
        "Invalid setting(s):",
    ]
    valid_env_vars = sorted(_build_valid_env_vars())
    for err in error.errors():
        loc = ".".join(str(part) for part in err.get("loc", ()))
        msg = err.get("msg", "validation failed")
        error_type = err.get("type", "")

        if error_type == "extra_forbidden" and loc:
            match_key = _normalise_loc_to_env_var(loc)
            if len(loc) >= 2 and loc[0] == loc[-1] and loc[0] in ("'", '"'):
                displayed_loc = f"{loc[0]}{match_key}{loc[-1]}"
            else:
                displayed_loc = match_key
            lines.append(f"  - {displayed_loc}: {msg}")
            close = difflib.get_close_matches(match_key, valid_env_vars, n=1, cutoff=0.9)
            if close and close[0] != match_key:
                lines.append(f"    Did you mean: {close[0]}? (check for typos)")
            else:
                lines.append(f"    Valid variables: {', '.join(valid_env_vars)}")
        else:
            range_msg = _range_error_message(loc)
            if range_msg is not None:
                msg = range_msg
            lines.append(f"  - {loc}: {msg}")

        lines.append("    Received: <redacted>")
    lines.append("Fix the offending value(s) and try again.")
    return "\n".join(lines)


def _range_error_message(field_name: str) -> str | None:
    """Return a concise range message for a field with ``Ge``/``Le`` bounds.

    For a field like ``max_retries`` with ``ge=1, le=10``, returns
    ``"must be in range 1..10"`` so the user sees both bounds in a single
    statement instead of the raw Pydantic per-constraint message.

    Returns ``None`` when the field has no both constraints, signalling the
    caller to fall back on the original Pydantic ``msg``.
    """
    from annotated_types import Ge, Le

    field = Settings.model_fields.get(field_name)
    if field is None:
        return None
    ge = next((m for m in field.metadata if isinstance(m, Ge)), None)
    le = next((m for m in field.metadata if isinstance(m, Le)), None)
    if ge is None or le is None:
        return None
    return f"must be in range {ge.ge}..{le.le}"


def _build_valid_env_vars() -> set[str]:
    """Build the set of valid VKDOWNLOADER_* environment variable names."""
    return {_ENV_VAR_PREFIX + name.upper() for name in Settings.model_fields}


def _scan_env_file(env_path: Path = Path(".env")) -> dict[str, str]:
    """Parse a ``.env`` file and return its key-value pairs.

    Delegates to ``dotenv.dotenv_values`` — the exact reader
    ``pydantic-settings`` uses through
    ``DotEnvSettingsSource._static_read_env_file``
    (``dotenv_values(file_path, encoding=encoding or 'utf8')`` at
    ``pydantic_settings/sources/providers/dotenv.py:80``). Parity with the
    consuming parser is therefore structural: any assignment form the
    model accepts, the scan sees with the same key and the same value.

    The call passes no ``interpolate`` argument, so ``dotenv_values``'
    own default ``interpolate=True`` applies — the same option the consuming
    parser uses. ``${VAR}`` references are expanded exactly as the model
    expands them, not left literal.

    Two things the shared reader does **not** normalise for us:

    * **Keys are returned exactly as the reader produces them.** The two
      quoted-key forms are *not* symmetric: ``'VKDOWNLOADER_X'`` loses
      its quotes (the model accepts it) while ``"VKDOWNLOADER_X"`` keeps
      them (the model rejects it), because ``parse_key`` has a dedicated
      single-quoted-key branch and no double-quoted counterpart
      (``dotenv/parser.py:112-120``). ``warn_unknown_env_vars`` applies
      its own normalisation to decide scope, but tests membership against
      the raw key so a quote-retaining key can never be mistaken for a
      declared field.
    * **The reader is case-preserving.** The consumer's case folding
      happens *after* the read, in ``parse_env_vars`` with
      ``case_sensitive=False`` (``pydantic_settings/sources/utils.py:32-42``),
      not in the reader.

    Args:
        env_path: Path to the .env file (default: ``.env`` in CWD).

    Returns:
        Dict mapping environment variable names to their raw string values.
        A key with no ``=`` (e.g. a bare ``VKDOWNLOADER_MAX_RETRIES`` line)
        is returned with an empty-string value, not dropped, so the guard
        can still flag it as unknown when the name is misspelled.
    """
    return {
        key: "" if value is None else value
        for key, value in dotenv_values(env_path, encoding="utf-8").items()
    }


def _is_unknown_env_var(key: str, valid_env_vars: set[str]) -> bool:
    """Return True if *key* is a VKDOWNLOADER_* variable not in *valid_env_vars*.

    **Scope** — *is this a VKDOWNLOADER_* key at all?* — is decided on a
    normalised copy of the name: one leading ``U+FEFF`` is skipped, one
    matching pair of surrounding quotes is stripped, and the prefix is
    tested case-insensitively against ``_ENV_VAR_PREFIX`` (the consumer
    lower-cases every key before matching, so the guard must match).

    **Membership** — *is this a declared field?* — is decided on the
    **raw** upper-cased name, never the normalised one. A quoted or
    BOM-prefixed key therefore can never match a declared field and is
    always reported, which is correct because the model rejects both.
    """
    scope = key.removeprefix("\ufeff")
    if len(scope) >= 2 and scope[0] == scope[-1] and scope[0] in ("'", '"'):
        scope = scope[1:-1]
    return scope.upper().startswith(_ENV_VAR_PREFIX) and key.upper() not in valid_env_vars


def warn_unknown_env_vars(env_file: Path = Path(".env")) -> list[str]:
    """Warn about unknown VKDOWNLOADER_* environment variables.

    Scans both the process environment (``os.environ``) and the resolved
    ``.env`` file for any ``VKDOWNLOADER_``-prefixed key that does not
    correspond to a recognized ``Settings`` field. This catches typos in
    both configuration mechanisms.

    - **OS environment typos:** Silently ignored by pydantic-settings
      (the default value is used). This function detects and warns.
    - **.env file typos:** Rejected by ``extra='forbid'`` at construction
      with a ValidationError. This function provides early detection
      *before* the crash, using the same typo guard as OS-env detection.

    Args:
        env_file: Path to the .env file to scan (default: ``.env`` in CWD).

    Returns:
        List of unknown environment variable names found in either
        ``os.environ`` or the ``.env`` file.
    """
    valid_env_vars = _build_valid_env_vars()

    # Scan OS environment
    os_unknown = [key for key in os.environ if _is_unknown_env_var(key, valid_env_vars)]

    # Scan .env file for typos (detects .env typos before they crash construction)
    file_env = _scan_env_file(env_file)
    file_unknown = [key for key in file_env if _is_unknown_env_var(key, valid_env_vars)]

    unknown = os_unknown + file_unknown
    return unknown


class _EncodingSafeConsoleStream(io.TextIOWrapper):
    """A ``TextIOWrapper`` whose ``close`` does not close the underlying buffer.

    ``logging.StreamHandler`` captures its stream at construction time, and the
    stream wraps ``sys.stderr``'s buffer.  A plain ``TextIOWrapper`` closes
    that buffer on ``close`` (and on garbage collection), which would tear down
    the real ``sys.stderr`` for the rest of the process.  This subclass flushes
    without closing, so the buffer stays alive.
    """

    def close(self) -> None:
        try:
            self.flush()
        except Exception:
            pass


class _EncodingSafeTextStream(io.TextIOBase):
    """A text-stream wrapper that escapes unencodable characters on write.

    Unlike :class:`_EncodingSafeConsoleStream` (which wraps a binary buffer via
    ``TextIOWrapper``), this wraps an already-textual stream such as rich's
    ``FileProxy``.  It re-encodes each ``write`` payload with
    ``errors="backslashreplace"`` so a record carrying characters the
    underlying stream cannot represent is escaped instead of raising
    ``UnicodeEncodeError``.

    Attribute access delegates to the wrapped stream so ``encoding``,
    ``buffer``, etc. remain available.  Only ``write`` and ``flush`` are
    overridden; ``close`` flushes without closing the underlying stream (the
    same policy as :class:`_EncodingSafeConsoleStream`).
    """

    def __init__(self, stream: IO[str]) -> None:
        self._stream = stream
        self._encoding: str = getattr(stream, "encoding", None) or sys.getdefaultencoding()

    def write(self, text: str) -> int:
        safe_text = text.encode(self._encoding, errors="backslashreplace").decode(self._encoding)
        return self._stream.write(safe_text)

    def flush(self) -> None:
        self._stream.flush()

    def close(self) -> None:
        try:
            self.flush()
        except Exception:
            pass

    def __getattr__(self, name: str) -> object:
        return getattr(self._stream, name)


def encoding_safe(stream: IO[str]) -> IO[str]:
    """Return *stream* wrapped with an encoding-safe error policy.

    Both :func:`setup_logging` and
    :meth:`RichProgressReporter._repoint_log_handlers` call this so the
    console sink applies a uniform ``backslashreplace`` policy regardless of
    how the stream is reached — direct stderr or the ``FileProxy`` rich
    installs during a Live display.

    * A ``TextIOWrapper`` (e.g. ``sys.stderr``) is wrapped at the binary
      buffer level with :class:`_EncodingSafeConsoleStream`, preserving the
      original B16 behaviour.
    * Any other text stream (e.g. rich's ``FileProxy``) is wrapped with
      :class:`_EncodingSafeTextStream`, which re-encodes writes with
      ``backslashreplace`` before delegating to the original stream.  This
      keeps writes routed through the FileProxy's Live-display mediation.

    Streams that are already one of our safe wrappers are returned unchanged.
    """
    if isinstance(stream, (_EncodingSafeConsoleStream, _EncodingSafeTextStream)):
        return stream
    if isinstance(stream, io.TextIOWrapper):
        raw = stream.buffer
        encoding = stream.encoding or sys.getdefaultencoding()
        return _EncodingSafeConsoleStream(
            raw,
            encoding=encoding,
            errors="backslashreplace",
            write_through=True,
        )
    return cast(IO[str], _EncodingSafeTextStream(stream))


class _ExcInfoClearingFormatter(logging.Formatter):
    """Formatter that suppresses the stdlib's duplicate traceback render.

    Structlog's ``format_exc_info`` processor already renders the traceback
    into the event dict (as a JSON ``"exception"`` key or as console text).
    However, when ``logger.exception()`` is called, the stdlib
    ``Logger.exception`` method unconditionally sets ``exc_info=True`` on the
    ``LogRecord``, so ``logging.Formatter.format`` appends a *second*
    traceback after the message — breaking one-JSON-object-per-line parseability
    of log files.

    This formatter clears ``record.exc_info`` and ``record.exc_text`` before
    delegating to the base ``Formatter``, so the traceback appears exactly once
    — inside the structlog-rendered output.
    """

    def format(self, record: logging.LogRecord) -> str:
        record.exc_info = None
        record.exc_text = None
        return super().format(record)


def setup_logging(settings: Settings | None = None) -> None:
    """Configure structlog for the application.

    Creates parent directory for log_file if it does not exist.

    Args:
        settings: Application settings. If None, uses default Settings().

    Raises:
        OSError: If log_file parent directory cannot be created.
    """
    if settings is None:
        settings = Settings()

    if settings.log_file is not None:
        log_path = settings.log_file
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(
                f"Failed to create log file parent directory '{log_path.parent}': {e}"
            ) from e
        # SEC-003: Create the log file before FileHandler opens it, so subprocess
        # output sanitized for SEC-002 is not readable by other local users.
        # 0o600 sets POSIX permission bits, and that is the only place the
        # owner-only confinement is delivered: on Windows `touch(mode=...)` ignores
        # the mode and `chmod` toggles only the read-only attribute, so both
        # branches leave the file readable by any local user. Confinement is not
        # offered there (D-11); the mode is requested for its POSIX effect only,
        # and no access control list is applied.
        if not log_path.exists():
            log_path.touch(mode=0o600)
        else:
            log_path.chmod(0o600)

    _formatter = _ExcInfoClearingFormatter(fmt="%(message)s")
    if settings.log_file:
        handler: logging.Handler = logging.FileHandler(settings.log_file)
    else:
        handler = logging.StreamHandler(encoding_safe(sys.stderr))
    handler.setFormatter(_formatter)

    logging.basicConfig(
        level=settings.log_level.value,
        handlers=[handler],
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            redact_log_event,
            structlog.processors.JSONRenderer()
            if settings.log_file
            else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
