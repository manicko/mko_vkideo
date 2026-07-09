"""Tests for configuration module."""

import pytest
from pydantic import ValidationError

from vkdownloader.config import Settings
from vkdownloader.models.enums import DownloadMethod


def test_settings_creates_with_defaults() -> None:
    """Test Settings creates with default values."""
    settings = Settings()

    assert settings.user_agent is not None
    assert settings.accept_language == "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    assert settings.timezone == "Europe/Moscow"
    assert settings.locale == "ru-RU"
    assert settings.max_retries == 3
    assert settings.download_timeout == 300
    assert settings.ssl_verify is True
    assert settings.max_concurrent_downloads == 4
    assert settings.download_method == DownloadMethod.AUTO
    assert settings.log_level == "INFO"
    assert settings.log_file is None


def test_settings_accepts_valid_fields() -> None:
    """Test Settings accepts all valid configuration fields."""
    settings = Settings(
        user_agent="CustomAgent/1.0",
        accept_language="en-US,en;q=0.9",
        timezone="America/New_York",
        locale="en-US",
        max_retries=5,
        download_timeout=600,
        ssl_verify=False,
        max_concurrent_downloads=8,
        download_method=DownloadMethod.YTDLP,
        log_level="DEBUG",
    )

    assert settings.user_agent == "CustomAgent/1.0"
    assert settings.accept_language == "en-US,en;q=0.9"
    assert settings.timezone == "America/New_York"
    assert settings.locale == "en-US"
    assert settings.max_retries == 5
    assert settings.download_timeout == 600
    assert settings.ssl_verify is False
    assert settings.max_concurrent_downloads == 8
    assert settings.download_method == DownloadMethod.YTDLP
    assert settings.log_level == "DEBUG"


def test_settings_rejects_unknown_keys() -> None:
    """Test Settings rejects unknown configuration keys with ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(unknown_key="test_value")

    error = exc_info.value
    assert "Extra inputs are not permitted" in str(error)
    assert "unknown_key" in str(error)


def test_settings_rejects_multiple_unknown_keys() -> None:
    """Test Settings rejects multiple unknown keys in ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            max_retries=3,
            invalid_field="value",
            another_invalid="another",
        )

    error = exc_info.value
    assert "Extra inputs are not permitted" in str(error)
