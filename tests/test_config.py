"""Tests for configuration module."""

import inspect
import io
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import IO, Any

import pytest
import structlog
from pydantic import ValidationError

from vkdownloader.config import (
    Settings,
    _scan_env_file,
    format_validation_error,
    setup_logging,
    warn_unknown_env_vars,
)
from vkdownloader.models.enums import CookieSource, LogLevel
from vkdownloader.services.downloader_throttle import DEFAULT_DOWNLOAD_TIMEOUT
from vkdownloader.services.ffmpeg_utils import (
    _merge_batch_segments,
    _merge_segments_batched,
    _perform_final_merge,
)
from vkdownloader.services.segment_downloader import (
    DownloadPolicy,
    _download_segment,
    _download_segment_parallel,
    _download_segment_sequential,
    _run_parallel_download_with_backoff,
    _try_single_download_attempt,
)


def test_settings_creates_with_defaults() -> None:
    """Test Settings creates with default values."""
    settings = Settings(ssl_verify=True)

    assert settings.user_agent is not None
    assert settings.timezone == "Europe/Moscow"
    assert settings.locale == "ru-RU"
    assert settings.max_retries == 3
    assert settings.download_timeout == 300
    assert settings.ssl_verify is True
    assert settings.max_concurrent_downloads == 4
    assert settings.log_level == LogLevel.INFO
    assert settings.log_file is None
    assert settings.stealth_enabled is False


def test_stealth_enabled_default_is_false() -> None:
    """B15 / D5: stealth_enabled defaults to False (opt-in, disabled by default)."""
    settings = Settings()
    assert settings.stealth_enabled is False


def test_stealth_enabled_env_example_value_constructs() -> None:
    """B15: the .env.example default value (false) constructs cleanly."""
    settings = Settings(stealth_enabled=False)
    assert settings.stealth_enabled is False


def test_stealth_enabled_from_env() -> None:
    """B15: VKDOWNLOADER_STEALTH_ENABLED=true is accepted and parsed to bool."""
    os.environ["VKDOWNLOADER_STEALTH_ENABLED"] = "true"
    try:
        settings = Settings()
        assert settings.stealth_enabled is True
    finally:
        del os.environ["VKDOWNLOADER_STEALTH_ENABLED"]


def test_settings_accepts_valid_fields() -> None:
    """Test Settings accepts all valid configuration fields."""
    settings = Settings(
        user_agent="CustomAgent/1.0",
        timezone="America/New_York",
        locale="en-US",
        max_retries=5,
        download_timeout=600,
        ssl_verify=False,
        max_concurrent_downloads=8,
        max_concurrent_segments=12,
        log_level="DEBUG",
    )

    assert settings.user_agent == "CustomAgent/1.0"
    assert settings.timezone == "America/New_York"
    assert settings.locale == "en-US"
    assert settings.max_retries == 5
    assert settings.download_timeout == 600
    assert settings.ssl_verify is False
    assert settings.max_concurrent_downloads == 8
    assert settings.max_concurrent_segments == 12
    assert settings.log_level == LogLevel.DEBUG


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
    """Test cookie_source accepts BROWSER and NONE only."""
    # Test BROWSER mode
    settings = Settings(cookie_source=CookieSource.BROWSER)
    assert settings.cookie_source == CookieSource.BROWSER

    # Test NONE mode (default)
    settings = Settings(cookie_source=CookieSource.NONE)
    assert settings.cookie_source == CookieSource.NONE

    # Test string input for valid modes
    settings = Settings(cookie_source="browser")
    assert settings.cookie_source == CookieSource.BROWSER

    settings = Settings(cookie_source="none")
    assert settings.cookie_source == CookieSource.NONE


def test_cookie_source_from_env() -> None:
    """Test cookie_source can be set via VKDOWNLOADER_COOKIE_SOURCE environment variable."""
    import os

    os.environ["VKDOWNLOADER_COOKIE_SOURCE"] = "browser"
    try:
        settings = Settings()
        assert settings.cookie_source == CookieSource.BROWSER
    finally:
        del os.environ["VKDOWNLOADER_COOKIE_SOURCE"]


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
    """Test http_chunk_size default value is 0 (disabled for reliable HLS)."""
    assert test_settings.http_chunk_size == 0


def test_http_chunk_size_validation(test_settings: Settings) -> None:
    """Test http_chunk_size accepts valid values and rejects invalid ones."""
    test_settings = Settings(http_chunk_size=1048576)
    assert test_settings.http_chunk_size == 1048576

    test_settings = Settings(http_chunk_size=104857600)
    assert test_settings.http_chunk_size == 104857600

    # 0 is valid (disabled)
    test_settings = Settings(http_chunk_size=0)
    assert test_settings.http_chunk_size == 0

    with pytest.raises(ValidationError):
        Settings(http_chunk_size=104857601)  # Above maximum


class TestConfigBackoffPause:
    """Tests for backoff_pause_seconds configuration (C1)."""

    def test_default_value(self) -> None:
        """Default backoff_pause_seconds is 10."""
        settings = Settings()
        assert settings.backoff_pause_seconds == 10

    def test_accepts_valid_values(self) -> None:
        """backoff_pause_seconds accepts values in range [1, 120]."""
        for val in [1, 10, 60, 120]:
            settings = Settings(backoff_pause_seconds=val)
            assert settings.backoff_pause_seconds == val

    def test_rejects_below_minimum(self) -> None:
        """backoff_pause_seconds rejects values below 1."""
        with pytest.raises(ValidationError):
            Settings(backoff_pause_seconds=0)

    def test_rejects_above_maximum(self) -> None:
        """backoff_pause_seconds rejects values above 120."""
        with pytest.raises(ValidationError):
            Settings(backoff_pause_seconds=121)


def test_log_level_validation() -> None:
    """Test log_level rejects invalid values and accepts valid ones."""
    # Valid log levels - case insensitive
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        s = Settings(log_level=level)
        assert s.log_level == LogLevel[level]

    # Lowercase input also works
    s = Settings(log_level="info")
    assert s.log_level == LogLevel.INFO

    # Invalid log level raises ValidationError
    with pytest.raises(ValidationError) as exc_info:
        Settings(log_level="INVALID")
    assert "log_level" in str(exc_info.value)


class TestWarnUnknownEnvVars:
    """Tests for the unknown environment variable typo guard."""

    def test_no_unknown_env_vars_returns_empty(self) -> None:
        """warn_unknown_env_vars returns empty list when only valid vars are set."""
        # Ensure no unknown VKDOWNLOADER_* vars are set
        original = dict(os.environ)
        try:
            # Remove any VKDOWNLOADER_* vars to get a clean state
            for key in list(os.environ):
                if key.startswith("VKDOWNLOADER_"):
                    del os.environ[key]
            assert warn_unknown_env_vars() == []
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_detects_unknown_env_var(self) -> None:
        """warn_unknown_env_vars detects and returns misspelled env var names."""
        original = dict(os.environ)
        try:
            for key in list(os.environ):
                if key.startswith("VKDOWNLOADER_"):
                    del os.environ[key]
            os.environ["VKDOWNLOADER_MAXRETRIES"] = "9"  # typo: missing underscore
            result = warn_unknown_env_vars()
            assert "VKDOWNLOADER_MAXRETRIES" in result
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_ignores_non_prefixed_env_vars(self) -> None:
        """warn_unknown_env_vars only checks VKDOWNLOADER_ prefixed vars."""
        original = dict(os.environ)
        try:
            for key in list(os.environ):
                if key.startswith("VKDOWNLOADER_"):
                    del os.environ[key]
            os.environ["SOME_OTHER_VAR"] = "value"
            assert warn_unknown_env_vars() == []
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_hide_input_in_errors_is_true(self) -> None:
        """Settings should hide input values in error messages."""
        assert Settings.model_config["hide_input_in_errors"] is True

    def test_validation_error_hides_input_values(self) -> None:
        """Validation errors should not leak raw input values."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(max_retries="not_a_number")
        error_str = str(exc_info.value)
        assert "not_a_number" not in error_str
        assert "max_retries" in error_str


class TestDownloadDirEmptyString:
    """Tests for empty-string handling of the path-typed fields."""

    def test_download_dir_empty_string_uses_default(self) -> None:
        """Settings(download_dir='') should use the default, not crash."""
        settings = Settings(download_dir="")
        expected_default = Settings.model_fields["download_dir"].default
        # Should be the default path, resolved to absolute
        assert settings.download_dir == expected_default.expanduser().resolve()

    def test_download_dir_empty_string_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """VKDOWNLOADER_DOWNLOAD_DIR='' should use default (via env var)."""
        # Clear any existing VKDOWNLOADER_ vars that might interfere
        original = dict(os.environ)
        try:
            for key in list(os.environ):
                if key.startswith("VKDOWNLOADER_"):
                    monkeypatch.delenv(key, raising=False)
            monkeypatch.setenv("VKDOWNLOADER_DOWNLOAD_DIR", "")
            settings = Settings()
            expected_default = Settings.model_fields["download_dir"].default
            assert settings.download_dir == expected_default.expanduser().resolve()
        finally:
            os.environ.clear()
            os.environ.update(original)

    def test_log_file_empty_string_still_uses_none(self) -> None:
        """Settings(log_file='') should still produce None (unchanged behavior)."""
        settings = Settings(log_file="")
        assert settings.log_file is None


_EMPTY_FREE_TEXT_SETTINGS: list[tuple[str, str]] = [
    ("user_agent", "VKDOWNLOADER_USER_AGENT"),
    ("timezone", "VKDOWNLOADER_TIMEZONE"),
    ("locale", "VKDOWNLOADER_LOCALE"),
]


class TestEmptyFreeTextSettings:
    """Tests for empty-value rejection on the free-text settings (CFG-007).

    Covers the three input paths that matter here -- a ``.env`` file, the
    process environment, and a constructor keyword -- for each of
    ``user_agent``, ``timezone`` and ``locale``. The adjacent path-field
    behaviour is pinned by :class:`TestDownloadDirEmptyString`, which this
    class does not duplicate and leaves untouched.
    """

    @pytest.mark.parametrize("field_name", ["user_agent", "timezone", "locale"])
    @pytest.mark.parametrize("bad_value", ["", "   ", "\t\n"])
    def test_constructor_rejects_empty(self, field_name: str, bad_value: str) -> None:
        """An empty or whitespace-only constructor value must fail validation.

        The failure must be self-diagnosing: the location names the setting and
        the message tells the user to remove the assignment, distinguishing it
        from a request for the default.
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(**{field_name: bad_value})

        formatted = format_validation_error(exc_info.value)
        # The setting is named in the rendered output...
        assert field_name in formatted
        # ...the value is redacted through the existing renderer...
        assert "Received: <redacted>" in formatted
        # ...and the message is explicit: it is not a silent fall-through.
        assert "must not be empty" in str(exc_info.value)
        assert "remove" in str(exc_info.value)

    @pytest.mark.parametrize(("field_name", "env_var"), _EMPTY_FREE_TEXT_SETTINGS)
    @pytest.mark.parametrize("bad_value", ["", "   ", "\t\n"])
    def test_empty_env_var_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        field_name: str,
        env_var: str,
        bad_value: str,
    ) -> None:
        """An exported empty VKDOWNLOADER_* value must fail validation.

        This is the OS-environment path: an empty string exported in the shell
        reaches the field and must be rejected, not silently dropped by
        ``env_ignore_empty`` (which is, and stays, ``False``).
        """
        monkeypatch.setenv(env_var, bad_value)
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        formatted = format_validation_error(exc_info.value)
        assert field_name in formatted
        assert "Received: <redacted>" in formatted
        assert "must not be empty" in str(exc_info.value)

    @pytest.mark.parametrize(("field_name", "env_var"), _EMPTY_FREE_TEXT_SETTINGS)
    @pytest.mark.parametrize("bad_value", ["", "   "])
    def test_empty_env_file_rejected(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        field_name: str,
        env_var: str,
        bad_value: str,
    ) -> None:
        """An empty assignment in a ``.env`` file must fail validation.

        This is the *reported* defect path: ``VKDOWNLOADER_USER_AGENT=`` in a
        ``.env`` must be rejected, not silently accepted as ``''``. The
        whitespace-only form is included because dotenv strips it to an empty
        string, which the validator must still reject.
        """
        env_file = tmp_path / ".env"
        env_file.write_text(f"{env_var}={bad_value}\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        formatted = format_validation_error(exc_info.value)
        assert field_name in formatted
        assert "Received: <redacted>" in formatted
        assert "must not be empty" in str(exc_info.value)

    def test_defaults_construct_cleanly(self) -> None:
        """Every field default must still validate: ``Settings()`` constructs.

        ``validate_default`` runs the new ``mode="before"`` validator against
        the field defaults, but each default is a non-empty string, so they
        all pass and the model constructs with no error.
        """
        settings = Settings()
        assert settings.user_agent == Settings.model_fields["user_agent"].default
        assert settings.timezone == "Europe/Moscow"
        assert settings.locale == "ru-RU"
        assert settings.user_agent.strip() != ""
        assert settings.timezone.strip() != ""
        assert settings.locale.strip() != ""

    def test_a_non_empty_value_is_accepted(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A non-empty value through any path is accepted, not only the default."""
        custom_ua = "MyCustomAgent/2.0"

        # Constructor path
        settings = Settings(user_agent=custom_ua)
        assert settings.user_agent == custom_ua

        # OS-environment path
        monkeypatch.setenv("VKDOWNLOADER_USER_AGENT", custom_ua)
        settings = Settings()
        assert settings.user_agent == custom_ua

        # .env file path (env override cleared so .env is the source)
        monkeypatch.delenv("VKDOWNLOADER_USER_AGENT", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text(f"VKDOWNLOADER_USER_AGENT={custom_ua}\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        settings = Settings()
        assert settings.user_agent == custom_ua


class TestEnvFileTypoDetection:
    """Tests for .env file typo detection in warn_unknown_env_vars (CFG-004)."""

    def test_detects_env_file_typo(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """warn_unknown_env_vars should detect typos in .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("VKDOWNLOADER_MAXRETRIES=9\n")

        original_cwd = Path.cwd()
        try:
            monkeypatch.chdir(tmp_path)
            result = warn_unknown_env_vars(env_file)
            assert "VKDOWNLOADER_MAXRETRIES" in result
        finally:
            os.chdir(str(original_cwd))

    def test_env_file_valid_var_not_flagged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """warn_unknown_env_vars should not flag valid .env variables."""
        env_file = tmp_path / ".env"
        env_file.write_text("VKDOWNLOADER_MAX_RETRIES=5\n")

        original_cwd = Path.cwd()
        try:
            monkeypatch.chdir(tmp_path)
            result = warn_unknown_env_vars(env_file)
            assert result == []
        finally:
            os.chdir(str(original_cwd))

    def test_env_file_missing_returns_empty(self, tmp_path: Path) -> None:
        """warn_unknown_env_vars should return empty list when .env doesn't exist."""
        result = warn_unknown_env_vars(tmp_path / "nonexistent.env")
        assert result == []

    # ------------------------------------------------------------------
    # R7b — misspelled keys in every assignment form are reported
    # (criteria 1, 5, 11)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("line", "expected_key"),
        [
            # Plain misspelled form
            ("VKDOWNLOADER_MAXRETRIES=9", "VKDOWNLOADER_MAXRETRIES"),
            # Leading whitespace — dotenv strips it
            ("  VKDOWNLOADER_MAXRETRIES=9", "VKDOWNLOADER_MAXRETRIES"),
            # Inline comment — dotenv strips the comment
            ("VKDOWNLOADER_MAXRETRIES=9  # oops", "VKDOWNLOADER_MAXRETRIES"),
            # Export prefix — dotenv strips it
            ("export VKDOWNLOADER_MAXRETRIES=9", "VKDOWNLOADER_MAXRETRIES"),
            # Lower-case — scope test is case-insensitive, membership uses raw key
            ("vkdownloader_maxretries=9", "vkdownloader_maxretries"),
            # Double-quoted key — dotenv retains the quotes
            ('"VKDOWNLOADER_MAXRETRIES"=9', '"VKDOWNLOADER_MAXRETRIES"'),
            # Quoted value — dotenv strips the quotes from the value
            ('VKDOWNLOADER_MAXRETRIES="9"', "VKDOWNLOADER_MAXRETRIES"),
        ],
    )
    def test_misspelled_forms_are_reported(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        line: str,
        expected_key: str,
    ) -> None:
        """Every misspelled form from the R7b table triggers the guard.

        The returned name is the user's own spelling — never a normalised copy.
        """
        env_file = tmp_path / ".env"
        env_file.write_text(line + "\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = warn_unknown_env_vars(env_file)

        assert expected_key in result, (
            f"misspelled form {line!r} should be reported with key {expected_key!r}; got {result!r}"
        )

    # ------------------------------------------------------------------
    # R7 — valid keys in every assignment form are not reported
    # (criterion 2)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "line",
        [
            "VKDOWNLOADER_MAX_RETRIES=5",
            "export VKDOWNLOADER_MAX_RETRIES=5",
            "  VKDOWNLOADER_MAX_RETRIES   =   5   ",
            "vkdownloader_max_retries=5",
            "VKDOWNLOADER_MAX_RETRIES=5 # bumped",
            'VKDOWNLOADER_MAX_RETRIES="5"',
            "VKDOWNLOADER_MAX_RETRIES='5'",
            "VKDOWNLOADER_TIMEZONE=America/New York",
        ],
    )
    def test_valid_forms_are_not_reported(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        line: str,
    ) -> None:
        """A valid key in every assignment form returns an empty list."""
        env_file = tmp_path / ".env"
        env_file.write_text(line + "\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = warn_unknown_env_vars(env_file)

        assert result == [], f"valid form {line!r} should not be reported; got {result!r}"

    # ------------------------------------------------------------------
    # Criterion 3 — scanned value matches what the model consumes
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("line", "field", "expected_value"),
        [
            ("VKDOWNLOADER_MAX_RETRIES=9 # bumped", "VKDOWNLOADER_MAX_RETRIES", "9"),
            ('VKDOWNLOADER_MAX_RETRIES="9"', "VKDOWNLOADER_MAX_RETRIES", "9"),
            ("VKDOWNLOADER_MAX_RETRIES='9'", "VKDOWNLOADER_MAX_RETRIES", "9"),
            (
                "VKDOWNLOADER_TIMEZONE=America/New York",
                "VKDOWNLOADER_TIMEZONE",
                "America/New York",
            ),
        ],
    )
    def test_scan_returns_value_the_model_consumes(
        self,
        tmp_path: Path,
        line: str,
        field: str,
        expected_value: str,
    ) -> None:
        """The scan sees exactly the value pydantic-settings consumes.

        dotenv strips inline comments and value-level quotes, so the scan
        sees the same value the model sees.
        """
        env_file = tmp_path / ".env"
        env_file.write_text(line + "\n", encoding="utf-8")

        scanned = _scan_env_file(env_file)

        assert scanned[field] == expected_value, (
            f"scan should return {expected_value!r} for {line!r}; got {scanned!r}"
        )

    # ------------------------------------------------------------------
    # Criterion 4 — interpolation parity with pydantic-settings
    # ------------------------------------------------------------------

    def test_interpolation_unset_var_returns_empty_string(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unresolved ``${VAR}`` is expanded to the empty string the model consumes."""
        monkeypatch.delenv("UNSET_VARIABLE", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("VKDOWNLOADER_MAX_RETRIES=${UNSET_VARIABLE}\n", encoding="utf-8")

        scanned = _scan_env_file(env_file)

        assert scanned["VKDOWNLOADER_MAX_RETRIES"] == ""

    def test_interpolation_set_var_is_resolved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A resolved ``${VAR}`` reflects the environment variable's value.

        This is the discriminating assertion: it fails if interpolation is
        disabled, because the literal ``'${SET_VAR}'`` would be returned instead.
        """
        monkeypatch.setenv("SET_VAR", "42")
        env_file = tmp_path / ".env"
        env_file.write_text("VKDOWNLOADER_MAX_RETRIES=${SET_VAR}\n", encoding="utf-8")

        scanned = _scan_env_file(env_file)
        value = scanned["VKDOWNLOADER_MAX_RETRIES"]

        assert value == "42", (
            f"expected resolved '42', got {value!r} (interpolation may be disabled)"
        )

    def test_interpolation_second_line_is_not_swallowed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A ``${UNSET}`` reference on one line does not drop the following line."""
        monkeypatch.delenv("UNSET_VARIABLE", raising=False)
        monkeypatch.setenv("SET_VAR", "7")
        env_file = tmp_path / ".env"
        env_file.write_text(
            "VKDOWNLOADER_MAX_RETRIES=${UNSET_VARIABLE}\nVKDOWNLOADER_THROTTLED_RATE=${SET_VAR}\n",
            encoding="utf-8",
        )

        scanned = _scan_env_file(env_file)

        assert scanned["VKDOWNLOADER_MAX_RETRIES"] == ""
        assert scanned["VKDOWNLOADER_THROTTLED_RATE"] == "7"

    # ------------------------------------------------------------------
    # Criterion 11 — quoted-key asymmetry
    # ------------------------------------------------------------------

    def test_single_quoted_valid_key_not_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A single-quoted valid key is accepted by the model, so the guard is silent.

        dotenv's ``parse_key`` has a single-quoted-key branch but no double-quoted
        counterpart: single quotes are stripped from the key, so the normalised
        name matches a declared field.
        """
        env_file = tmp_path / ".env"
        env_file.write_text("'VKDOWNLOADER_MAX_RETRIES'=5\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = warn_unknown_env_vars(env_file)

        assert result == []

    def test_double_quoted_valid_key_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A double-quoted valid key is rejected by the model, so the guard reports it.

        The returned name retains the double quotes — the strip-then-compare
        guard would have suppressed this, which is the false negative this block fixes.
        """
        env_file = tmp_path / ".env"
        env_file.write_text('"VKDOWNLOADER_MAX_RETRIES"=5\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = warn_unknown_env_vars(env_file)

        assert '"VKDOWNLOADER_MAX_RETRIES"' in result

    # ------------------------------------------------------------------
    # Criterion 12 — bare lines (no '=')
    # ------------------------------------------------------------------

    def test_bare_typo_line_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bare misspelled line (no ``=``) is reported, not silently ignored."""
        env_file = tmp_path / ".env"
        env_file.write_text("VKDOWNLOADER_MAXRETRIES\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = warn_unknown_env_vars(env_file)

        assert "VKDOWNLOADER_MAXRETRIES" in result

    def test_bare_valid_line_not_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A bare correctly-spelled line (no ``=``) is not flagged."""
        env_file = tmp_path / ".env"
        env_file.write_text("VKDOWNLOADER_MAX_RETRIES\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = warn_unknown_env_vars(env_file)

        assert result == []

    def test_bare_line_value_is_empty_string(self, tmp_path: Path) -> None:
        """A bare line (no ``=``) is retained with ``''`` not dropped.

        ``None`` (dotenv's marker for no value) is coerced to ``''``, so the
        guard can still flag a bare misspelled key.
        """
        env_file = tmp_path / ".env"
        env_file.write_text("VKDOWNLOADER_MAXRETRIES\n", encoding="utf-8")

        scanned = _scan_env_file(env_file)

        assert scanned == {"VKDOWNLOADER_MAXRETRIES": ""}

    # ------------------------------------------------------------------
    # Criterion 13 — BOM: guard's verdict agrees with the model's verdict
    # ------------------------------------------------------------------

    def test_bom_valid_key_agrees_with_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A BOM-prefixed valid key: guard verdict must equal model verdict.

        On python-dotenv 1.2.2 the BOM survives into the key, so the model
        rejects and the guard must report. On 1.2.3 the BOM is stripped, so
        the model accepts and the guard must be silent. The test asserts
        agreement on whichever version is installed, not a fixed outcome.
        """
        env_file = tmp_path / ".env"
        env_file.write_bytes(b"\xef\xbb\xbfVKDOWNLOADER_MAX_RETRIES=9\n")
        monkeypatch.chdir(tmp_path)

        guard_reports = bool(warn_unknown_env_vars(env_file))

        try:
            Settings()
            model_rejects = False
        except ValidationError:
            model_rejects = True

        assert guard_reports == model_rejects, (
            f"guard reports={guard_reports}, model rejects={model_rejects}"
        )

    def test_bom_typo_key_agrees_with_model(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A BOM-prefixed misspelled key: guard and model must agree."""
        env_file = tmp_path / ".env"
        env_file.write_bytes(b"\xef\xbb\xbfVKDOWNLOADER_MAXRETRIES=9\n")
        monkeypatch.chdir(tmp_path)

        guard_reports = bool(warn_unknown_env_vars(env_file))

        try:
            Settings()
            model_rejects = False
        except ValidationError:
            model_rejects = True

        assert guard_reports == model_rejects

    # ------------------------------------------------------------------
    # Criterion 14 — malformed line (unterminated quote) is dropped
    # ------------------------------------------------------------------

    def test_malformed_line_is_dropped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An unterminated quote drops the entire file from the guard's view.

        ``dotenv_values`` returns an empty mapping for a file containing a
        malformed line, so the guard has nothing to report. The model also
        sees nothing from that file, so neither flags the typo'd name.
        """
        env_file = tmp_path / ".env"
        env_file.write_text('VKDOWNLOADER_MAXRETRIES="9\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        result = warn_unknown_env_vars(env_file)

        assert result == []


class TestFormatValidationError:
    """Tests for format_validation_error suggestion quality (CFG-003)."""

    def test_extra_forbidden_suggests_did_you_mean(self) -> None:
        """format_validation_error should suggest 'did you mean' for extra_forbidden errors.

        CFG-003 requires the assertion to name the *correct* setting, not merely
        that a suggestion or a list is present.  The constructor-keyword typo
        ``maxretries`` is normalised to ``VKDOWNLOADER_MAXRETRIES`` and must
        suggest ``VKDOWNLOADER_MAX_RETRIES`` — the field the user actually meant.
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(maxretries="9")  # typo: missing underscore
        formatted = format_validation_error(exc_info.value)
        assert "Configuration error" in formatted
        # The location is rendered in the normalised environment-variable namespace
        assert "VKDOWNLOADER_MAXRETRIES" in formatted
        # CFG-003: the suggestion must be the correct setting, not a generic winner
        assert "Did you mean: VKDOWNLOADER_MAX_RETRIES?" in formatted

    def test_unknown_key_error_message(self) -> None:
        """format_validation_error should include loc and msg for unknown keys.

        CFG-003 normalises the location to the env-var namespace, so
        ``unknown_key`` is rendered as ``VKDOWNLOADER_UNKNOWN_KEY``.  Its
        similarity ratio is below the 0.9 intent gate, so it falls to the
        valid-name list rather than receiving a confident (and wrong) pointer.
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(unknown_key="test_value")
        formatted = format_validation_error(exc_info.value)
        assert "VKDOWNLOADER_UNKNOWN_KEY" in formatted
        assert "Extra inputs are not permitted" in formatted
        assert "Received: <redacted>" in formatted
        assert "Fix the offending value(s)" in formatted


# CFG-003 R8 — 19 plausible misspellings through the real environment-file path.
# Each row pairs the misspelled key with its intended target, or ``None`` when
# the key has no plausible intent (LOGIN, bare prefix, XYZ) or falls below the
# 0.9 intent gate (MAX_CONCURENT, ratio 0.825 — accepted as lost per D-1).
_CFG003_R8_TABLE: list[tuple[str, str | None]] = [
    ("VKDOWNLOADER_MAXRETRIES", "VKDOWNLOADER_MAX_RETRIES"),
    ("VKDOWNLOADER_MAX_RETRY", "VKDOWNLOADER_MAX_RETRIES"),
    ("VKDOWNLOADER_MAX_RETREIS", "VKDOWNLOADER_MAX_RETRIES"),
    ("VKDOWNLOADER_DOWNLAOD_TIMEOUT", "VKDOWNLOADER_DOWNLOAD_TIMEOUT"),
    ("VKDOWNLOADER_SSL_VERFY", "VKDOWNLOADER_SSL_VERIFY"),
    ("VKDOWNLOADER_LOG_LVL", "VKDOWNLOADER_LOG_LEVEL"),
    ("VKDOWNLOADER_COOKIE_SORCE", "VKDOWNLOADER_COOKIE_SOURCE"),
    ("VKDOWNLOADER_HEADLES", "VKDOWNLOADER_HEADLESS"),
    ("VKDOWNLOADER_THROTTLEDRATE", "VKDOWNLOADER_THROTTLED_RATE"),
    ("VKDOWNLOADER_HTTP_CHUNKSIZE", "VKDOWNLOADER_HTTP_CHUNK_SIZE"),
    ("VKDOWNLOADER_DOWNLOAD_DIRR", "VKDOWNLOADER_DOWNLOAD_DIR"),
    ("VKDOWNLOADER_USERAGENT", "VKDOWNLOADER_USER_AGENT"),
    ("VKDOWNLOADER_TIMEZONEE", "VKDOWNLOADER_TIMEZONE"),
    ("VKDOWNLOADER_LOCALE_", "VKDOWNLOADER_LOCALE"),
    ("VKDOWNLOADER_MAX_CONCURENT_DOWNLOADS", "VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS"),
    # Below the 0.9 intent gate or no plausible intent → valid-name list
    ("VKDOWNLOADER_MAX_CONCURENT", None),
    ("VKDOWNLOADER_LOGIN", None),
    ("VKDOWNLOADER_", None),
    ("VKDOWNLOADER_XYZ", None),
]


class TestEnvFileValidationRendering:
    """Tests for format_validation_error through the environment-file path (CFG-003).

    Drives the renderer through the **real environment-file path** — the path
    no test in the suite drives today and the path the defect lives on.
    Asserts on the rendered text, not on the guard's return value (which
    :class:`TestEnvFileTypoDetection` already covers).  Covers the full 19-row
    R8 table from the CFG-003 finding.
    """

    @pytest.mark.parametrize(
        ("env_key", "expected_suggestion"),
        _CFG003_R8_TABLE,
    )
    def test_env_file_rendering(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        env_key: str,
        expected_suggestion: str | None,
    ) -> None:
        """format_validation_error through the environment-file path.

        The renderer must match in the env-var namespace, so a genuine typo
        names the correct setting.  Keys below the 0.9 intent gate — including
        the three no-intent keys and ``VKDOWNLOADER_MAX_CONCURENT`` (ratio
        0.825, accepted as lost per D-1) — must render the valid-name list with
        no confident wrong pointer.
        """
        env_file = tmp_path / ".env"
        env_file.write_text(f"{env_key}=9\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValidationError) as exc_info:
            Settings()
        formatted = format_validation_error(exc_info.value)

        # The offending key is rendered in the normalised env-var namespace
        normalised_key = env_key.upper()
        assert f"  - {normalised_key}: " in formatted, (
            f"expected normalised loc {normalised_key} in error line; got:\n{formatted}"
        )

        if expected_suggestion is not None:
            assert f"Did you mean: {expected_suggestion}?" in formatted, (
                f"expected correct suggestion {expected_suggestion} for {env_key}; got:\n{formatted}"
            )
            assert "Valid variables:" not in formatted
        else:
            assert "Did you mean" not in formatted, (
                f"expected NO suggestion for {env_key}; got:\n{formatted}"
            )
            assert "Valid variables:" in formatted

    def test_double_quoted_correctly_spelled_key(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A double-quoted correctly-spelled key shows quotes and no suggestion.

        The quotes are the only defect, so the match-key resolves to the
        exact variable name and the self-referential suggestion is suppressed
        in favour of the valid-variable list.
        """
        env_file = tmp_path / ".env"
        env_file.write_text('"VKDOWNLOADER_MAX_RETRIES"=9\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValidationError) as exc_info:
            Settings()
        formatted = format_validation_error(exc_info.value)

        # The displayed location retains the double quotes the user typed.
        assert '"VKDOWNLOADER_MAX_RETRIES"' in formatted
        # Self-referential suggestion is suppressed — valid list is shown instead.
        assert "Did you mean" not in formatted
        assert "Valid variables:" in formatted

    def test_double_quoted_misspelled_key(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A double-quoted misspelled key shows quotes and a real suggestion.

        The displayed location retains the double quotes, but the match-key
        is stripped so the typo still resolves to the closest valid variable.
        """
        env_file = tmp_path / ".env"
        env_file.write_text('"VKDOWNLOADER_SSL_VERFY"=9\n', encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ValidationError) as exc_info:
            Settings()
        formatted = format_validation_error(exc_info.value)

        # The displayed location retains the double quotes.
        assert '"VKDOWNLOADER_SSL_VERFY"' in formatted
        # The stripped match-key resolves to the real target.
        assert "Did you mean: VKDOWNLOADER_SSL_VERIFY?" in formatted
        assert "Valid variables:" not in formatted

    """Tests for setup_logging log file creation and permissions (SEC-003)."""

    def test_log_file_created_when_absent(self, tmp_path: Path) -> None:
        """SEC-003: setup_logging creates the configured log file."""
        log_file = tmp_path / "app.log"
        settings = Settings(log_file=str(log_file), log_level="DEBUG")

        setup_logging(settings)

        assert log_file.exists()

    def test_log_file_created_with_owner_only_permissions(self, tmp_path: Path) -> None:
        """SEC-003: log file creation requests 0o600 and clears the read-only attribute.

        POSIX: ``setup_logging`` creates the log file via ``Path.touch(mode=0o600)``
        and ``st_mode & 0o777 == 0o600`` is asserted.

        Windows: ``touch`` and ``chmod`` are intercepted with a local recorder
        (Alt A) to confirm exactly one ``touch(mode=0o600)`` call and no
        ``chmod`` call in the creation branch, then the read-only attribute is
        asserted clear. Owner-only confinement is not guaranteed on Windows
        (D-11): the assertion targets the requested branch and the cleared
        attribute, not POSIX-style permission bits.
        """
        log_file = tmp_path / "app.log"
        settings = Settings(log_file=str(log_file), log_level="DEBUG")

        if os.name != "nt":
            setup_logging(settings)

            mode = os.stat(log_file).st_mode & 0o777
            assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
        else:
            # Alt A: spy on the creation branch with a local recorder (no mock import).
            touch_calls: list[Any] = []
            chmod_calls: list[Any] = []
            original_touch = Path.touch
            original_chmod = Path.chmod

            def _recording_touch(self: Path, *args: Any, **kwargs: Any) -> None:
                touch_calls.append((self, args, kwargs))
                return original_touch(self, *args, **kwargs)

            def _recording_chmod(self: Path, *args: Any, **kwargs: Any) -> None:
                chmod_calls.append((self, args, kwargs))
                return original_chmod(self, *args, **kwargs)

            Path.touch = _recording_touch  # type: ignore[method-assign]
            Path.chmod = _recording_chmod  # type: ignore[method-assign]
            try:
                setup_logging(settings)
            finally:
                Path.touch = original_touch  # type: ignore[method-assign]
                Path.chmod = original_chmod  # type: ignore[method-assign]

            # Assert the creation branch was taken as expected.
            assert len(touch_calls) == 1, f"Expected exactly one touch call, got {len(touch_calls)}"
            touch_kwargs = touch_calls[0][2]
            assert touch_kwargs.get("mode") == 0o600, (
                f"Expected touch(mode=0o600), got mode={touch_kwargs.get('mode')!r}"
            )
            assert len(chmod_calls) == 0, (
                f"Expected no chmod in creation branch, got {len(chmod_calls)}"
            )

            # Assert the read-only attribute is clear on the created file.
            assert getattr(os.stat(log_file), "st_file_attributes", 0) & 0x1 == 0, (
                "read-only attribute should be clear on a freshly created file"
            )

    def test_existing_log_file_permissions_updated(self, tmp_path: Path) -> None:
        """SEC-003: existing log file permissions are corrected to 0o600.

        POSIX: the file is pre-set to 0o644, setup_logging calls ``chmod(0o600)``,
        and ``st_mode & 0o777 == 0o600`` is asserted.

        Windows: the file is pre-set to 0o444 (read-only). setup_logging calls
        ``chmod(0o600)`` which clears the read-only attribute. If the precondition
        were not corrected, ``FileHandler`` construction would raise
        ``PermissionError`` when opening a read-only file, so the cleared
        attribute is asserted. Owner-only confinement is not guaranteed on
        Windows (D-11): the assertion targets the cleared attribute, not POSIX
        permission bits.
        """
        log_file = tmp_path / "existing.log"
        log_file.write_text("old content")
        # Set platform-specific "insecure" precondition.
        if os.name != "nt":
            os.chmod(log_file, 0o644)
        else:
            os.chmod(log_file, 0o444)

        settings = Settings(log_file=str(log_file), log_level="DEBUG")
        setup_logging(settings)

        if os.name != "nt":
            mode = os.stat(log_file).st_mode & 0o777
            assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
        else:
            # On Windows, os.chmod(0o600) clears the read-only attribute.
            assert getattr(os.stat(log_file), "st_file_attributes", 0) & 0x1 == 0, (
                "read-only attribute should be cleared after chmod(0o600)"
            )


class TestExcInfoClearing:
    """B3: exception tracebacks render exactly once in log output.

    Structlog's ``format_exc_info`` processor formats the traceback into the
    event dict (JSON key ``"exception"`` or console text).  The stdlib
    ``Logger.exception`` method then sets ``exc_info=True`` on the LogRecord,
    which would cause ``logging.Formatter`` to append a *second* traceback.

    ``_ExcInfoClearingFormatter`` clears ``record.exc_info`` / ``record.exc_text``
    before the base ``Formatter.format`` runs, so the traceback appears exactly
    once — inside the structlog-rendered output.
    """

    @staticmethod
    def _emit_exception(logger: structlog.stdlib.BoundLogger) -> None:
        """Emit a single exception-carrying log record."""
        try:
            raise ValueError("synthetic test error")
        except ValueError:
            logger.exception("something went wrong")

    def test_log_file_every_line_is_valid_json(self, tmp_path: Path) -> None:
        """B3: every line in a log file with an exception-carrying record parses as JSON."""
        log_file = tmp_path / "app.log"
        settings = Settings(log_level="DEBUG", log_file=str(log_file))

        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        saved_level = root.level
        root.handlers.clear()
        try:
            setup_logging(settings)
            logger = structlog.get_logger("b3-test")
            self._emit_exception(logger)

            root.handlers = root.handlers  # flush
            for h in root.handlers:
                h.flush()
        finally:
            root.handlers.clear()
            root.handlers.extend(saved_handlers)
            root.setLevel(saved_level)

        lines = log_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1, f"expected exactly 1 log line, got {len(lines)}"
        parsed = json.loads(lines[0])
        assert isinstance(parsed, dict)

    def test_traceback_appears_exactly_once_in_json(self, tmp_path: Path) -> None:
        """B3: the traceback appears exactly once and as a JSON key, not as a text line."""
        log_file = tmp_path / "app.log"
        settings = Settings(log_level="DEBUG", log_file=str(log_file))

        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        saved_level = root.level
        root.handlers.clear()
        try:
            setup_logging(settings)
            logger = structlog.get_logger("b3-test")
            self._emit_exception(logger)

            for h in root.handlers:
                h.flush()
        finally:
            root.handlers.clear()
            root.handlers.extend(saved_handlers)
            root.setLevel(saved_level)

        lines = log_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])

        exc = parsed.get("exception")
        assert exc is not None, "expected 'exception' key in JSON log record"
        assert isinstance(exc, str)
        # The traceback string contains the error class and message.
        assert "ValueError" in exc
        assert "synthetic test error" in exc
        # 'Traceback' should appear once in the formatted exception string.
        assert exc.count("Traceback") == 1

    def test_non_exception_record_parses(self, tmp_path: Path) -> None:
        """B3: non-exception records still parse as JSON with timestamp and level."""
        log_file = tmp_path / "app.log"
        settings = Settings(log_level="DEBUG", log_file=str(log_file))

        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        saved_level = root.level
        root.handlers.clear()
        try:
            setup_logging(settings)
            logger = structlog.get_logger("b3-test")
            logger.info("plain message", video_id="abc123")

            for h in root.handlers:
                h.flush()
        finally:
            root.handlers.clear()
            root.handlers.extend(saved_handlers)
            root.setLevel(saved_level)

        lines = log_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event"] == "plain message"
        assert parsed["level"] == "info"
        # TimeStamper ISO/UTC stamp is present.
        assert "timestamp" in parsed
        assert "video_id" in parsed

    def test_console_renderer_traceback_once(self) -> None:
        """B3: ConsoleRenderer (stderr) path renders the traceback exactly once."""
        buffer = io.StringIO()
        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        saved_level = root.level
        root.handlers.clear()
        try:
            # Redirect stderr so the StreamHandler writes to the buffer.
            old_stderr = sys.stderr
            sys.stderr = buffer
            try:
                setup_logging()  # ConsoleRenderer path: log_file=None
            finally:
                sys.stderr = old_stderr

            logger = structlog.get_logger("b3-test")
            self._emit_exception(logger)

            for h in root.handlers:
                h.flush()
        finally:
            root.handlers.clear()
            root.handlers.extend(saved_handlers)
            root.setLevel(saved_level)

        output = buffer.getvalue()
        # ConsoleRenderer renders the traceback once inside the event.
        assert output.count("Traceback") == 1


def _launch_dir(request: pytest.FixtureRequest) -> Path:
    """Return the directory the test session was launched from."""
    invocation_dir = request.config.invocation_params.dir
    assert invocation_dir is not None
    return Path(invocation_dir).resolve()


class TestEnvironmentIsolation:
    """Tests proving the suite is isolated from the ambient settings source (D-10)."""

    def test_no_ambient_product_variable_reaches_settings(self) -> None:
        """D-10: the autouse fixture strips every VKDOWNLOADER_* variable for each test."""
        assert os.environ, "the process environment must be real for this test to mean anything"
        leaked = sorted(key for key in os.environ if key.startswith("VKDOWNLOADER_"))
        assert leaked == [], f"ambient product variables reached the test: {leaked}"

        settings = Settings()
        assert settings.cookie_source == CookieSource.NONE
        assert settings.max_retries == 3
        assert settings.max_concurrent_downloads == 4
        assert settings.max_concurrent_segments == 4
        assert settings.download_timeout == 300
        assert settings.throttled_rate == 100000
        assert settings.log_level == LogLevel.INFO
        assert settings.log_file is None

    def test_env_file_in_launch_directory_cannot_reach_settings(
        self, request: pytest.FixtureRequest, tmp_path: Path
    ) -> None:
        """D-10: a .env in the launch directory is unreachable from the per-test cwd.

        The hostile file is built inside ``tmp_path`` and never in the launch
        directory. Writing it beside the launch point — which on a normal run is
        the repository root — would rewrite a developer's own configuration file
        for the duration of the test, and a hard kill between the write and the
        restore would leave that file poisoned. A stand-in launch directory under
        ``tmp_path`` gives the same proof with no write outside ``tmp_path``.
        """
        stand_in_launch_dir = tmp_path / "launch_dir"
        stand_in_launch_dir.mkdir()
        (stand_in_launch_dir / ".env").write_text(
            "VKDOWNLOADER_COOKIE_SOURCE=browser\nVKDOWNLOADER_MAX_RETRIES=9\n",
            encoding="utf-8",
        )

        # Positive control: a process launched *from* that directory reads the
        # file and takes the hostile values, so the file is proven capable of
        # flipping a default and the in-process assertions below cannot pass
        # merely because the file is inert.
        probe = (
            "from vkdownloader.config import Settings\n"
            "settings = Settings()\n"
            "print(settings.cookie_source)\n"
            "print(settings.max_retries)\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=stand_in_launch_dir,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert completed.returncode == 0, f"the probe subprocess failed:\n{completed.stderr}"
        observed = completed.stdout.split()
        assert observed == ["browser", "9"], (
            "a .env in the launch directory must be able to flip the documented "
            f"defaults, otherwise this test proves nothing; observed {observed}"
        )

        # The mechanism that keeps it out of reach: the autouse fixture moved the
        # process off the launch point, so no .env is resolvable from here.
        cwd = Path.cwd().resolve()
        assert cwd != _launch_dir(request), (
            f"the per-test working directory {cwd} must not be the launch directory"
        )
        assert not (cwd / ".env").exists(), (
            f"a .env is reachable from the per-test working directory {cwd}"
        )

        settings = Settings()
        assert settings.cookie_source == CookieSource.NONE
        assert settings.max_retries == 3

    def test_autouse_isolation_fixture_is_active(self, request: pytest.FixtureRequest) -> None:
        """D-10: the autouse fixture is registered and has moved the process off the launch point."""
        assert "isolate_settings_source" in request.fixturenames
        assert Path.cwd().resolve() != _launch_dir(request)
        assert not (Path.cwd() / ".env").exists()


class TestConditionalOverridesConstruction:
    """CFG-002: _build_settings validates max_retries bounds (Route A construction path).

    The bounds are derived from the field's own declared metadata, not hardcoded,
    so the test documents the field as the single source of truth for the range.
    """

    def test_max_retries_bounds_derived_from_field_metadata(self) -> None:
        """Floor and ceiling come from the field's declared constraints, not hardcoded."""
        from annotated_types import Ge, Le

        from vkdownloader.cli import _build_settings

        field = Settings.model_fields["max_retries"]
        floor = next(m.ge for m in field.metadata if isinstance(m, Ge))
        ceiling = next(m.le for m in field.metadata if isinstance(m, Le))

        # Below the floor → ValidationError naming max_retries
        with pytest.raises(ValidationError) as exc_info:
            _build_settings(
                cookie_source=None,
                ssl_verify=None,
                max_retries=floor - 1,
                log_level=None,
            )
        assert "max_retries" in str(exc_info.value)

        # Above the ceiling → ValidationError naming max_retries
        with pytest.raises(ValidationError) as exc_info:
            _build_settings(
                cookie_source=None,
                ssl_verify=None,
                max_retries=ceiling + 1,
                log_level=None,
            )
        assert "max_retries" in str(exc_info.value)

        # Floor is accepted and survives on the constructed object
        settings = _build_settings(
            cookie_source=None,
            ssl_verify=None,
            max_retries=floor,
            log_level=None,
        )
        assert settings.max_retries == floor

        # Ceiling is accepted and survives
        settings = _build_settings(
            cookie_source=None,
            ssl_verify=None,
            max_retries=ceiling,
            log_level=None,
        )
        assert settings.max_retries == ceiling


class TestDownloadTimeoutDescriptionStatesTheExitPath:
    """CON-010: download_timeout's description is the doc of record, and
    CON-010's remedy under D9 is a statement in it that may not be a
    partial truth.

    Three semantic facts are pinned, never the wording. Full-string
    equality is deliberately not used: the description is prose, and
    a test that failed on any reword would be a maintenance cost with
    no oracle value (rule 5).

      1. every consumer class the setting actually bounds is named;
      2. the exit-path subject -- the abandoned extraction thread
         joined at interpreter shutdown -- is named;
      3. the description states that THIS SETTING is not the bound
         applied on that path.
    """

    # Consumer classes, each verified present in src/: segment and
    # playlist HTTP (segment_downloader.py aiohttp.ClientTimeout and
    # downloader_throttle.download_segment_throttled);
    # each ffmpeg merge subprocess (segment_downloader.py ->
    # ffmpeg_utils._merge_segments_batched -> _merge_batch_segments
    # and _perform_final_merge, via policy.download_timeout);
    # the off-loop extraction's wait_for
    # (VKVideoExtractor._extract_with_ytdlp); and yt-dlp's socket
    # timeout as BOTH a library option (the ydl_opts dict) and a CLI
    # flag (ytdlp_downloader._build_ytdlp_cli_command's
    # --socket-timeout).
    _CONSUMER_TOKENS = (
        "segment",
        "playlist",
        "ffmpeg",
        "yt-dlp",
        "extraction",
    )

    # The mechanism is CPython's thread-pool join, so any wording
    # that still states the finding must name the thread, the
    # executor, or the shutdown. An "any of three" test rather than
    # one fixed word keeps a legitimate rewording green.
    _EXIT_PATH_SUBJECT_TOKENS = ("thread", "executor", "shutdown")

    # "this setting is not the bound on that path", in the ordinary
    # English forms that claim takes. The character class forbids a
    # sentence break between the negator and its referent, so a
    # negation about some other subject cannot satisfy it.
    _EXIT_PATH_DISCLAIMER_RE = re.compile(
        r"\b(?:not|never|no|neither|rather|instead)\b[^.?!]*"
        r"\b(?:this setting|download_timeout|this timeout)\b",
        re.IGNORECASE,
    )

    def _description(self) -> str:
        description = Settings.model_fields["download_timeout"].description
        assert isinstance(description, str), (
            "download_timeout must carry a description -- it is the doc "
            f"of record for what the setting bounds; got {description!r}"
        )
        return description

    def test_names_every_consumer_class_the_setting_bounds(self) -> None:
        """A description corrected to name three of four is still wrong."""
        lowered = self._description().lower()

        missing = [t for t in self._CONSUMER_TOKENS if t not in lowered]
        assert not missing, (
            "download_timeout's description must name every consumer class "
            f"the setting bounds; missing {missing} from "
            f"{self._description()!r}"
        )

    def test_names_the_exit_path_subject(self) -> None:
        """CON-010's first clause: state the exit-path bound here."""
        lowered = self._description().lower()

        assert any(t in lowered for t in self._EXIT_PATH_SUBJECT_TOKENS), (
            "download_timeout's description must name the exit-path "
            "subject -- the extraction thread joined at interpreter "
            f"shutdown; found none of {self._EXIT_PATH_SUBJECT_TOKENS} "
            f"in {self._description()!r}"
        )

    def test_states_this_setting_is_not_the_exit_path_bound(self) -> None:
        """D8 item 1: the description must disclaim the exit path."""
        description = self._description()

        assert self._EXIT_PATH_DISCLAIMER_RE.search(description), (
            "download_timeout's description must state that this setting "
            "is not the bound applied on the exit path (a negator and "
            "'this setting'/'download_timeout' in one clause); got "
            f"{description!r}"
        )


class _StrictStream(io.TextIOWrapper):
    """A cp1251 text stream with ``errors='strict'``.

    Mirrors the real-world condition where ``sys.stderr`` is cp1251 with a
    strict error handler -- the configuration under which a record carrying
    box-drawing characters propagates ``UnicodeEncodeError`` out of
    ``StreamHandler.emit`` (B16 / BRW-001).
    """

    def __init__(self, buf: io.BytesIO) -> None:
        super().__init__(buf, encoding="cp1251", errors="strict")


def _first_console_handler(root: logging.Logger) -> logging.StreamHandler[IO[str]]:
    """Return the first non-File ``StreamHandler`` on the root logger."""
    for handler in root.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            return handler
    raise AssertionError("no console StreamHandler found on root logger")


class TestSetupLoggingConsoleEncoding:
    """B16: the console sink must not raise on records carrying characters
    unencodable in the console's encoding; it must escape, not drop, them.

    The defect had no owning finding in any phase -- phase 01 deferred
    encoding to phase 08; phase 08 never filed it (D7 adopted it here).
    """

    def test_non_encodable_record_does_not_raise_and_reaches_handler(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B16: a record carrying box-drawing characters must not raise out
        of the console sink when stderr is strict-encoded, and must reach the
        handler's stream (not be silently swallowed by handleError).
        """
        buffer = io.BytesIO()
        monkeypatch.setattr(sys, "stderr", _StrictStream(buffer))

        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            setup_logging()
            handler = _first_console_handler(root)

            # U+2500 (BOX DRAWINGS LIGHT HORIZONTAL) is not in cp1251.
            # A strict stream raises UnicodeEncodeError on it; the encoding-
            # safe stream must escape it instead.
            record = logging.LogRecord(
                name="b16",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="browser launch failed ─━",
                args=(),
                exc_info=None,
            )

            handler.emit(record)  # must not raise

            output = buffer.getvalue()
            assert output, "record did not reach the console sink"
            assert b"browser launch failed" in output
        finally:
            root.handlers.clear()
            root.handlers.extend(saved_handlers)

    def test_non_encodable_record_is_escaped_not_dropped(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B16: the record's information must be preserved in the output,
        backslash-escaped rather than suppressed or truncated.

        A fix that merely suppresses the record (via handleError's ``except
        OSError: pass``) would leave the buffer empty or missing content --
        that is not a fix.
        """
        buffer = io.BytesIO()
        monkeypatch.setattr(sys, "stderr", _StrictStream(buffer))

        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            setup_logging()
            handler = _first_console_handler(root)

            record = logging.LogRecord(
                name="b16",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="browser launch failed ─━ details",
                args=(),
                exc_info=None,
            )

            handler.emit(record)

            output = buffer.getvalue()
            # The unencodable character is backslash-escaped (\u2500), proving
            # the record was emitted rather than dropped.
            assert b"\\u2500" in output, (
                f"expected backslash-escaped U+2500 in output; got {output!r}"
            )
            # Surrounding ASCII text is intact -- the record was not truncated.
            assert b"browser launch failed" in output
            assert b"details" in output
        finally:
            root.handlers.clear()
            root.handlers.extend(saved_handlers)

    def test_normal_record_not_swallowed_or_truncated(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B16: the encoding-safe stream must not swallow or truncate normal
        (ASCII) records -- only non-encodable characters are escaped.
        """
        buffer = io.BytesIO()
        monkeypatch.setattr(sys, "stderr", _StrictStream(buffer))

        root = logging.getLogger()
        saved_handlers = root.handlers[:]
        root.handlers.clear()
        try:
            setup_logging()
            handler = _first_console_handler(root)

            record = logging.LogRecord(
                name="b16",
                level=logging.INFO,
                pathname=__file__,
                lineno=1,
                msg="download complete, 1024 bytes",
                args=(),
                exc_info=None,
            )

            handler.emit(record)

            output = buffer.getvalue()
            assert b"download complete, 1024 bytes" in output, (
                f"normal record was truncated or swallowed; got {output!r}"
            )
        finally:
            root.handlers.clear()
            root.handlers.extend(saved_handlers)


class TestDownloadTimeoutSingleSource:
    """ENT-010: every download-timeout default is sourced from one constant.

    ``DEFAULT_DOWNLOAD_TIMEOUT`` mirrors ``Settings.download_timeout``'s declared
    schema default at import time; every consumer default across
    ``segment_downloader.py`` and ``ffmpeg_utils.py`` must equal it, so a schema
    change re-converges every site in a single edit rather than nine literals
    drifting out of step.
    """

    def test_constant_mirrors_schema_default(self) -> None:
        """The module constant equals the schema's declared default."""
        schema_default = Settings.model_fields["download_timeout"].default
        assert DEFAULT_DOWNLOAD_TIMEOUT == schema_default

    @pytest.mark.parametrize(
        "consumer",
        [
            DownloadPolicy,
            _download_segment,
            _download_segment_parallel,
            _download_segment_sequential,
            _run_parallel_download_with_backoff,
            _try_single_download_attempt,
            _merge_batch_segments,
            _merge_segments_batched,
            _perform_final_merge,
        ],
    )
    def test_consumer_default_equals_constant(self, consumer: Any) -> None:
        """Each ``download_timeout`` default equals the single constant.

        Introspected via ``inspect.signature`` rather than by reading source, so
        a reintroduced literal ``300`` fails the test even if it is never
        executed. Covers the ``DownloadPolicy`` field default plus the five
        ``segment_downloader`` parameter defaults and the three
        ``ffmpeg_utils`` parameter defaults (nine consumer sites in total).
        """
        default = inspect.signature(consumer).parameters["download_timeout"].default
        assert default == DEFAULT_DOWNLOAD_TIMEOUT


class TestMaxConcurrentSegments:
    """B14: tests for the max_concurrent_segments setting.

    This setting governs the per-video segment fan-out (the segment
    semaphore and yt-dlp's -N flag). It is decoupled from
    max_concurrent_downloads, which remains the batch-level video gate.
    """

    def test_default_value(self) -> None:
        """max_concurrent_segments defaults to 4."""
        settings = Settings()
        assert settings.max_concurrent_segments == 4

    def test_accepts_valid_values(self) -> None:
        """max_concurrent_segments accepts values in range [1, 16]."""
        for val in [1, 2, 4, 8, 16]:
            settings = Settings(max_concurrent_segments=val)
            assert settings.max_concurrent_segments == val

    def test_rejects_below_minimum(self) -> None:
        """max_concurrent_segments rejects values below 1."""
        with pytest.raises(ValidationError):
            Settings(max_concurrent_segments=0)

    def test_rejects_above_maximum(self) -> None:
        """max_concurrent_segments rejects values above 16."""
        with pytest.raises(ValidationError):
            Settings(max_concurrent_segments=17)

    def test_from_env_var(self) -> None:
        """VKDOWNLOADER_MAX_CONCURRENT_SEGMENTS is accepted via environment."""
        os.environ["VKDOWNLOADER_MAX_CONCURRENT_SEGMENTS"] = "6"
        try:
            settings = Settings()
            assert settings.max_concurrent_segments == 6
        finally:
            del os.environ["VKDOWNLOADER_MAX_CONCURRENT_SEGMENTS"]


@pytest.mark.parametrize(
    ("segments", "downloads", "expected_aggregate"),
    [
        # Default: min(4, 4) * 4 = 4 * 4 = 16
        (4, 4, 16),
        # Ceiling: min(16, 16) * 16 = 16 * 16 = 256
        (16, 16, 256),
        # segments capped by downloads: min(16, 4) * 4 = 4 * 4 = 16
        (16, 4, 16),
        # downloads capped by segments: min(4, 16) * 16 = 4 * 16 = 64
        (4, 16, 64),
    ],
)
def test_aggregate_segment_ceiling_formula(
    segments: int, downloads: int, expected_aggregate: int
) -> None:
    """The aggregate segment ceiling is min(segments, downloads) * downloads.

    This pins the effective maximum number of in-flight segment downloads across
    a batch: segment fan-out per video (segments, capped by downloads since the
    batch semaphore gates how many videos run concurrently) times the number of
    concurrent videos (downloads).
    """
    effective_per_video = min(segments, downloads)
    aggregate = effective_per_video * downloads
    assert aggregate == expected_aggregate
