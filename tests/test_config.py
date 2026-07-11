"""Tests for configuration module."""

import pytest
from pydantic import ValidationError

from vkdownloader.config import Settings
from vkdownloader.models.enums import CookieSource, DownloadMethod


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


def test_cookie_source_default() -> None:
    """Test cookie_source default value is CookieSource.NONE."""
    settings = Settings()
    assert settings.cookie_source == CookieSource.NONE


def test_cookie_source_validation() -> None:
    """Test cookie_source accepts all enum values."""
    # Test BROWSER mode
    settings = Settings(cookie_source=CookieSource.BROWSER)
    assert settings.cookie_source == CookieSource.BROWSER

    # Test FILE mode
    settings = Settings(cookie_source=CookieSource.FILE)
    assert settings.cookie_source == CookieSource.FILE

    # Test NONE mode (default)
    settings = Settings(cookie_source=CookieSource.NONE)
    assert settings.cookie_source == CookieSource.NONE


def test_cookie_source_from_env() -> None:
    """Test cookie_source can be set via COOKIE_SOURCE environment variable."""
    import os

    os.environ["COOKIE_SOURCE"] = "browser"
    try:
        settings = Settings()
        assert settings.cookie_source == CookieSource.BROWSER
    finally:
        del os.environ["COOKIE_SOURCE"]


def test_concurrent_fragments_default(test_settings: Settings) -> None:
    """Test concurrent_fragments default value is 4."""
    assert test_settings.concurrent_fragments == 4


def test_concurrent_fragments_validation(test_settings: Settings) -> None:
    """Test concurrent_fragments accepts valid values and rejects invalid ones."""
    test_settings = Settings(concurrent_fragments=1)
    assert test_settings.concurrent_fragments == 1

    test_settings = Settings(concurrent_fragments=16)
    assert test_settings.concurrent_fragments == 16

    with pytest.raises(ValidationError):
        Settings(concurrent_fragments=0)  # Below minimum

    with pytest.raises(ValidationError):
        Settings(concurrent_fragments=17)  # Above maximum


def test_throttled_rate_default(test_settings: Settings) -> None:
    """Test throttled_rate default value is 100000."""
    assert test_settings.throttled_rate == 100000


def test_throttled_rate_validation(test_settings: Settings) -> None:
    """Test throttled_rate accepts valid values and rejects invalid ones."""
    test_settings = Settings(throttled_rate=50000)
    assert test_settings.throttled_rate == 50000

    test_settings = Settings(throttled_rate=1000000)
    assert test_settings.throttled_rate == 1000000

    with pytest.raises(ValidationError):
        Settings(throttled_rate=49999)  # Below minimum

    with pytest.raises(ValidationError):
        Settings(throttled_rate=1000001)  # Above maximum


def test_http_chunk_size_default(test_settings: Settings) -> None:
    """Test http_chunk_size default value is 10485760."""
    assert test_settings.http_chunk_size == 10485760


def test_http_chunk_size_validation(test_settings: Settings) -> None:
    """Test http_chunk_size accepts valid values and rejects invalid ones."""
    test_settings = Settings(http_chunk_size=1048576)
    assert test_settings.http_chunk_size == 1048576

    test_settings = Settings(http_chunk_size=104857600)
    assert test_settings.http_chunk_size == 104857600

    with pytest.raises(ValidationError):
        Settings(http_chunk_size=1048575)  # Below minimum

    with pytest.raises(ValidationError):
        Settings(http_chunk_size=104857601)  # Above maximum
