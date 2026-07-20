"""Configuration module for VK Video Downloader."""

import logging
from pathlib import Path

import structlog
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from vkdownloader.models.enums import CookieSource, LogLevel

logger: structlog.BoundLogger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings with defaults and environment variable support.

    Note: unknown VKDOWNLOADER_* environment variables are silently ignored due to
    pydantic-settings v2 extra='forbid' limitation — it only applies to explicit
    kwargs passed to the model constructor, not to environment variables.

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
        description="Timezone for browser stealth configuration",
    )
    locale: str = Field(
        default="ru-RU",
        description="Locale for browser stealth configuration",
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
        description="Download timeout in seconds",
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
        description="Maximum concurrent downloads",
    )
    throttled_rate: int = Field(
        default=10000,
        ge=1000,
        le=1000000,
        description="Minimum download rate in bytes/sec before throttling triggers re-extract. Default is conservative (10KB/s) to avoid aborting legitimate slow downloads; yt-dlp will abort below this threshold.",
    )
    http_chunk_size: int = Field(
        default=10485760,
        ge=1048576,
        le=104857600,
        description="HTTP chunk size in bytes for segment downloads",
    )
    cookie_source: CookieSource = Field(
        default=CookieSource.NONE,
        description="Cookie acquisition strategy: none or browser (file not implemented)",
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

    @field_validator("download_dir", "log_file", mode="after")
    @classmethod
    def expand_tilde_paths(cls, v: Path | None) -> Path | None:
        if v is None:
            return v
        return v.expanduser().resolve()

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str | LogLevel) -> LogLevel:
        if isinstance(v, LogLevel):
            return v
        return LogLevel(v.upper())

    @field_validator("cookie_source", mode="before")
    @classmethod
    def validate_cookie_source(cls, v: object) -> object:
        """Reject CookieSource.FILE at model construction (not implemented)."""
        if isinstance(v, CookieSource) and v == CookieSource.FILE:
            raise ValueError(
                "CookieSource.FILE is not implemented. Use 'none' or 'browser' instead."
            )
        if isinstance(v, str) and v.lower() == "file":
            raise ValueError(
                "CookieSource.FILE is not implemented. Use 'none' or 'browser' instead."
            )
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "forbid",
        "env_prefix": "VKDOWNLOADER_",
    }


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

    logging.basicConfig(
        format="%(message)s",
        level=settings.log_level.value,
        handlers=[
            logging.StreamHandler()
            if not settings.log_file
            else logging.FileHandler(settings.log_file)
        ],
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
            if settings.log_file
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
