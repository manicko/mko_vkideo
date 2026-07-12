"""Configuration module for VK Video Downloader."""

import logging
from pathlib import Path

import structlog
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from vkdownloader.models.enums import CookieSource, DownloadMethod, LogLevel

logger: structlog.BoundLogger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings with defaults and environment variable support."""

    # Browser Automation settings
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for browser requests",
    )
    accept_language: str = Field(
        default="ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        description="Accept-Language header for browser requests",
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
    concurrent_fragments: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Concurrent HLS fragment downloads for yt-dlp (reduces throttling)",
    )
    throttled_rate: int = Field(
        default=100000,
        ge=50000,
        le=1000000,
        description="Minimum download rate in bytes/sec before throttling triggers re-extract",
    )
    http_chunk_size: int = Field(
        default=10485760,
        ge=1048576,
        le=104857600,
        description="HTTP chunk size in bytes for segment downloads",
    )
    download_method: DownloadMethod = Field(
        default=DownloadMethod.AUTO,
        description="Download method: 'yt-dlp', 'ffmpeg', or 'auto'",
    )
    cookie_source: CookieSource = Field(
        default=CookieSource.NONE,
        description="Cookie acquisition strategy: none, browser, or file",
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

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: str | LogLevel) -> LogLevel:
        if isinstance(v, LogLevel):
            return v
        return LogLevel(v.upper())

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "forbid",
        "env_prefix": "VKDOWNLOADER_",
    }


def setup_logging(settings: Settings | None = None) -> None:
    """Configure structlog for the application."""
    if settings is None:
        settings = Settings()

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer()
            if settings.log_file
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.value)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Global settings instance
settings = Settings()
