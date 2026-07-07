"""Configuration module for VK Video Downloader."""

import logging
from pathlib import Path

import structlog
from pydantic import Field
from pydantic_settings import BaseSettings

logger: structlog.BoundLogger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings with defaults and environment variable support."""

    # VK API settings
    vk_api_url: str = Field(
        default="https://api.vk.com/method",
        description="VK API base URL",
    )
    vk_api_version: str = Field(
        default="5.199",
        description="VK API version",
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
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout in seconds",
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_file: Path | None = Field(
        default=None,
        description="Optional log file path",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
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
            logging.getLevelName(settings.log_level)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Global settings instance
settings = Settings()
