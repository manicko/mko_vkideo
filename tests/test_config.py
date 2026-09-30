"""Tests for configuration module."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from vkdownloader.config import (
    Settings,
    _scan_env_file,
    format_validation_error,
    setup_logging,
    warn_unknown_env_vars,
)
from vkdownloader.models.enums import CookieSource, LogLevel


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
        log_level="DEBUG",
    )

    assert settings.user_agent == "CustomAgent/1.0"
    assert settings.timezone == "America/New_York"
    assert settings.locale == "en-US"
    assert settings.max_retries == 5
    assert settings.download_timeout == 600
    assert settings.ssl_verify is False
    assert settings.max_concurrent_downloads == 8
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
    """Tests for empty-string download_dir handling (CFG-002)."""

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
    """Tests for format_validation_error (CFG-001 UX improvement)."""

    def test_extra_forbidden_suggests_did_you_mean(self) -> None:
        """format_validation_error should suggest 'did you mean' for extra_forbidden errors."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(maxretries="9")  # typo: missing underscore
        formatted = format_validation_error(exc_info.value)
        assert "Configuration error" in formatted
        assert "maxretries" in formatted
        # Should suggest the correct field name
        assert "Did you mean" in formatted or "Valid fields" in formatted

    def test_unknown_key_error_message(self) -> None:
        """format_validation_error should include loc and msg for unknown keys."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(unknown_key="test_value")
        formatted = format_validation_error(exc_info.value)
        assert "unknown_key" in formatted
        assert "Extra inputs are not permitted" in formatted
        assert "Received: <redacted>" in formatted
        assert "Fix the offending value(s)" in formatted


class TestSetupLogging:
    """Tests for setup_logging log file creation and permissions (SEC-003)."""

    def test_log_file_created_when_absent(self, tmp_path: Path) -> None:
        """SEC-003: setup_logging creates the configured log file."""
        log_file = tmp_path / "app.log"
        settings = Settings(log_file=str(log_file), log_level="DEBUG")

        setup_logging(settings)

        assert log_file.exists()

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Owner-only confinement is not offered on Windows: os.chmod there toggles "
        "only the read-only attribute, so the measured mode is 0o666 rather than the "
        "requested 0o600 (D-11).",
    )
    def test_log_file_created_with_owner_only_permissions(self, tmp_path: Path) -> None:
        """SEC-003: log file should be created with 0o600 permissions."""
        log_file = tmp_path / "app.log"
        settings = Settings(log_file=str(log_file), log_level="DEBUG")

        setup_logging(settings)

        mode = os.stat(log_file).st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Owner-only confinement is not offered on Windows: os.chmod there toggles "
        "only the read-only attribute, so the measured mode is 0o666 rather than the "
        "requested 0o600 (D-11).",
    )
    def test_existing_log_file_permissions_updated(self, tmp_path: Path) -> None:
        """SEC-003: existing log file should have permissions corrected to 0o600."""
        log_file = tmp_path / "existing.log"
        log_file.write_text("old content")
        # Set insecure permissions
        os.chmod(log_file, 0o644)

        settings = Settings(log_file=str(log_file), log_level="DEBUG")
        setup_logging(settings)

        mode = os.stat(log_file).st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"


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
            )
        assert "max_retries" in str(exc_info.value)

        # Above the ceiling → ValidationError naming max_retries
        with pytest.raises(ValidationError) as exc_info:
            _build_settings(
                cookie_source=None,
                ssl_verify=None,
                max_retries=ceiling + 1,
            )
        assert "max_retries" in str(exc_info.value)

        # Floor is accepted and survives on the constructed object
        settings = _build_settings(
            cookie_source=None,
            ssl_verify=None,
            max_retries=floor,
        )
        assert settings.max_retries == floor

        # Ceiling is accepted and survives
        settings = _build_settings(
            cookie_source=None,
            ssl_verify=None,
            max_retries=ceiling,
        )
        assert settings.max_retries == ceiling
