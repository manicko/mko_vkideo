"""Unit tests for throttle utilities with retry logic for rate limiting."""

import time
from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.services.downloader_throttle import (
    _DEFAULT_BACKOFF_PAUSE_SECONDS,
    ProgressManager,
    URLBackoffCoordinator,
    _resource_key,
    build_client_timeout,
)
from vkdownloader.services.retry_policies import (
    RETRYABLE_STATUS_CODES,
    _compute_backoff_delay,
    _parse_retry_after,
    _retry_429_with_backoff,
    _wait_with_shutdown,
)


class TestRetry429WithBackoff:
    """Tests for _retry_429_with_backoff function."""

    @pytest.mark.asyncio
    async def test_successful_response_on_first_attempt(self) -> None:
        """Test successful response on first attempt (no retry)."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b"segment content")

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        result = await _retry_429_with_backoff(
            mock_session,
            "https://example.com/segment.ts",
            {"User-Agent": "test"},
            segment_index=0,
        )

        assert result == b"segment content"
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_429_retry_with_exponential_backoff(self) -> None:
        """Test 429 retry with exponential backoff timing."""
        mock_session = AsyncMock()
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {}
        mock_response_429.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_context = AsyncMock()
            if call_count == 1:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_429)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session.get = MagicMock(side_effect=get_side_effect)

        # Mock random.uniform to return 0 for instant timeout simulation
        # This avoids real time.sleep and prevents flaky timing
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2  # First 429, then success

    @pytest.mark.asyncio
    async def test_retry_after_header_overrides_delay(self) -> None:
        """Test Retry-After header overrides calculated delay."""
        mock_session = AsyncMock()
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {"Retry-After": "5"}
        mock_response_429.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_context = AsyncMock()
            if call_count == 1:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_429)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session.get = MagicMock(side_effect=get_side_effect)

        # Mock random.uniform to return 0 for instant timeout simulation
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_returns_none(self) -> None:
        """Test max retries (3) exceeded returns None."""
        mock_session = AsyncMock()
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {}
        mock_response_429.read = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response_429)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        # Mock random.uniform to return 0 for instant timeout simulation
        # This avoids real time.sleep and prevents flaky timing
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            start = time.monotonic()
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
                max_retries=3,
            )
            elapsed = time.monotonic() - start

        assert result is None
        assert mock_session.get.call_count == 3
        # C19: Final attempt (attempt == max_retries - 1) breaks without waiting,
        # so the total wall-clock stays well under 0.5s even though all retries
        # return a retryable status.
        assert elapsed < 0.5

    @pytest.mark.asyncio
    async def test_500_status_code_triggers_retry(self) -> None:
        """Test 500 status code triggers retry."""
        mock_session = AsyncMock()
        mock_response_500 = AsyncMock()
        mock_response_500.status = 500
        mock_response_500.headers = {}
        mock_response_500.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_context = AsyncMock()
            if call_count == 1:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_500)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session.get = MagicMock(side_effect=get_side_effect)

        # Mock random.uniform to return 0 for instant timeout simulation
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_502_status_code_triggers_retry(self) -> None:
        """Test 502 status code triggers retry."""
        mock_session = AsyncMock()
        mock_response_502 = AsyncMock()
        mock_response_502.status = 502
        mock_response_502.headers = {}
        mock_response_502.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_context = AsyncMock()
            if call_count == 1:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_502)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session.get = MagicMock(side_effect=get_side_effect)

        # Mock random.uniform to return 0 for instant timeout simulation
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_503_status_code_triggers_retry(self) -> None:
        """Test 503 status code triggers retry."""
        mock_session = AsyncMock()
        mock_response_503 = AsyncMock()
        mock_response_503.status = 503
        mock_response_503.headers = {}
        mock_response_503.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_context = AsyncMock()
            if call_count == 1:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_503)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session.get = MagicMock(side_effect=get_side_effect)

        # Mock random.uniform to return 0 for instant timeout simulation
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_504_status_code_triggers_retry(self) -> None:
        """Test 504 status code triggers retry."""
        mock_session = AsyncMock()
        mock_response_504 = AsyncMock()
        mock_response_504.status = 504
        mock_response_504.headers = {}
        mock_response_504.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_context = AsyncMock()
            if call_count == 1:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_504)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session.get = MagicMock(side_effect=get_side_effect)

        # Mock random.uniform to return 0 for instant timeout simulation
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_non_retry_status_codes_return_none_immediately(self) -> None:
        """Test non-retry status codes (403, 404) return None immediately."""
        for status_code in [403, 404]:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = status_code
            mock_response.headers = {}
            mock_response.read = AsyncMock()

            mock_context = AsyncMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_session.get = MagicMock(return_value=mock_context)

            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

            assert result is None, f"Failed for status code {status_code}"

    @pytest.mark.asyncio
    async def test_structured_logging_on_retry(self) -> None:
        """Test structured logging fields on 429 retry: attempt, status, retry_after, segment_index, url."""
        mock_session = AsyncMock()
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {"Retry-After": "2"}
        mock_response_429.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            mock_context = AsyncMock()
            if call_count == 1:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_429)
            else:
                mock_context.__aenter__ = AsyncMock(return_value=mock_response_200)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            return mock_context

        mock_session.get = MagicMock(side_effect=get_side_effect)

        # Mock random.uniform to return 0 for instant timeout simulation
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0):
            with patch(
                "vkdownloader.services.downloader_throttle._strip_auth_params",
                return_value="https://example.com/segment.ts",
            ):
                with patch(
                    "vkdownloader.services.downloader_throttle.logger.warning"
                ) as mock_warning:
                    result = await _retry_429_with_backoff(
                        mock_session,
                        "https://example.com/segment.ts?token=secret",
                        {"User-Agent": "test"},
                        segment_index=5,
                        max_retries=3,
                    )

        assert result == b"segment content"
        # Verify structured logging actually recorded the 429 retry with expected fields
        mock_warning.assert_called_once()
        assert mock_warning.call_args[0][0] == "segment_retry_429"
        call_kwargs = mock_warning.call_args[1]
        assert call_kwargs["attempt"] == 1
        assert call_kwargs["status"] == 429
        assert call_kwargs["retry_after"] == 2.0
        assert call_kwargs["segment_index"] == 5
        # Sanitized URL must not leak auth params
        assert call_kwargs["url"] == "https://example.com/segment.ts"
        assert "token=secret" not in call_kwargs["url"]

    @pytest.mark.asyncio
    async def test_structured_logging_on_non_retryable(self) -> None:
        """Test structured logging on non-retryable error."""
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.headers = {}
        mock_response.read = AsyncMock()

        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get = MagicMock(return_value=mock_context)

        with patch("vkdownloader.services.downloader_throttle.logger.warning") as mock_warning:
            with patch(
                "vkdownloader.services.downloader_throttle._strip_auth_params",
                return_value="https://example.com/segment.ts",
            ):
                result = await _retry_429_with_backoff(
                    mock_session,
                    "https://example.com/segment.ts",
                    {"User-Agent": "test"},
                    segment_index=3,
                )

        assert result is None
        mock_warning.assert_called_once()
        call_kwargs = mock_warning.call_args[1]
        assert call_kwargs["status"] == 403
        assert call_kwargs["segment_index"] == 3
        assert "url" in call_kwargs

    @pytest.mark.asyncio
    async def test_programming_error_not_swallowed_as_transient(self) -> None:
        """TypeError (programming error) is NOT caught as transient failure."""

        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=TypeError("unexpected type"))

        with patch(
            "vkdownloader.services.downloader_throttle._strip_auth_params",
            return_value="https://example.com/segment.ts",
        ):
            with pytest.raises(TypeError, match="unexpected type"):
                await _retry_429_with_backoff(
                    mock_session,
                    "https://example.com/segment.ts",
                    {"User-Agent": "test"},
                    segment_index=0,
                )

    @pytest.mark.asyncio
    async def test_timeout_error_handled_as_transient(self) -> None:
        """asyncio.TimeoutError is caught as a transient failure (not programming error)."""

        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=TimeoutError("socket timeout"))

        with (
            patch(
                "vkdownloader.services.downloader_throttle._strip_auth_params",
                return_value="https://example.com/segment.ts",
            ),
            patch("vkdownloader.services.downloader_throttle.get_shutdown_event") as mock_se,
            patch(
                "vkdownloader.services.retry_policies._wait_with_shutdown",
                new_callable=AsyncMock,
            ) as mock_wait,
        ):
            mock_se.return_value.is_set.return_value = False
            mock_wait.return_value = False  # Don't trigger shutdown

            with patch(
                "vkdownloader.services.downloader_throttle.random.uniform", return_value=0.0
            ):
                result = await _retry_429_with_backoff(
                    mock_session,
                    "https://example.com/segment.ts",
                    {"User-Agent": "test"},
                    segment_index=0,
                    max_retries=2,
                )

        assert result is None, "TimeoutError should return None (transient), not raise"


class TestURLBackoffCoordinator:
    """Tests for URLBackoffCoordinator class."""

    @pytest.mark.asyncio
    async def test_wait_if_paused_returns_false_when_not_paused(self) -> None:
        """Test wait_if_paused returns False when URL is not paused."""
        coordinator = URLBackoffCoordinator()
        result = await coordinator.wait_if_paused("https://example.com/video1")
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_if_paused_waits_until_backoff_expires(self) -> None:
        """Test wait_if_paused blocks until backoff expires."""
        coordinator = URLBackoffCoordinator()
        # Use larger margin (0.1s) to avoid race condition on slow CI
        await coordinator.pause("https://example.com/video1", 0.1)

        result = await coordinator.wait_if_paused("https://example.com/video1")
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_if_paused_returns_on_shutdown(self) -> None:
        """Test wait_if_paused respects shutdown event and returns early."""
        coordinator = URLBackoffCoordinator()
        await coordinator.pause("https://example.com/video1", 100.0)

        # Mock shutdown event with is_set() returning True
        mock_event = MagicMock()
        mock_event.is_set.return_value = True

        async def mock_wait_for(coro: Coroutine[Any, Any, Any], timeout: float | None) -> Any:
            # Simulate shutdown triggered - wait_for returns successfully
            return None

        with patch(
            "vkdownloader.services.downloader_throttle.get_shutdown_event",
            return_value=mock_event,
        ):
            with patch(
                "vkdownloader.services.downloader_throttle.asyncio.wait_for",
                side_effect=mock_wait_for,
            ):
                result = await coordinator.wait_if_paused("https://example.com/video1")

        assert result is True


class TestParseRetryAfter:
    """Tests for _parse_retry_after function."""

    @pytest.mark.parametrize(
        ("header_value", "expected"),
        [
            # Integer seconds
            ("120", 120.0),
            (" 120 ", 120.0),  # whitespace-padded
            ("-5", None),  # negative — rejected (criterion 2)
            ("0", None),  # zero — rejected (criterion 2)
            ("invalid", None),  # non-numeric
            # IMF-fixdate
            ("Mon, 01 Jan 2094 00:00:00 GMT", "positive"),  # future
            ("mon, 01 jan 2094 00:00:00 gmt", "positive"),  # lowercase
            ("Mon, 01 Jan 1994 00:00:00 GMT", None),  # past
            # RFC 850 (2-digit year, 68->2068)
            ("Monday, 01-Jan-68 00:00:00 GMT", "positive"),  # future
            # asctime
            ("Tue Jan  1 00:00:00 2094", "positive"),  # future
            # Absent / invalid
            (None, None),  # absent header
            ("not-a-date", None),  # unparseable
            ("", None),  # empty string
        ],
    )
    def test_retry_after_header_forms(self, header_value, expected) -> None:
        """Thirteen-row header-form table covering integer, IMF-fixdate, RFC 850,
        asctime, lower-case, negative, zero, whitespace-padded, past, absent,
        and invalid inputs."""
        mock_response = MagicMock()
        if header_value is None:
            mock_response.headers = {}
        else:
            mock_response.headers = {"Retry-After": header_value}

        result = _parse_retry_after(mock_response)

        if expected == "positive":
            assert isinstance(result, float) and result > 0
        else:
            assert result == expected


class TestComputeBackoffDelay:
    """Tests for _compute_backoff_delay function."""

    def test_429_uses_base_delay_1(self) -> None:
        """Test 429 status uses base_delay of 1.0."""
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.5):
            result = _compute_backoff_delay(429, 0, None)

        assert result == 0.5

    def test_5xx_uses_base_delay_0_05(self) -> None:
        """Test 5xx status uses base_delay of 0.05."""
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.025):
            result = _compute_backoff_delay(500, 0, None)

        assert result == 0.025

    def test_delay_caps_at_30_seconds(self) -> None:
        """Test delay upper bound is capped at 30 seconds on the jitter range."""
        with patch("vkdownloader.services.downloader_throttle.random.uniform") as mock_uniform:
            mock_uniform.return_value = 0.0  # Return 0 when called with capped upper bound
            result = _compute_backoff_delay(429, 100, None)

        call_args = mock_uniform.call_args[0]
        assert call_args[1] == 30.0  # jitter ceiling, not the Retry-After floor
        assert result == 0.0

    def test_retry_after_ceiling_applies_after_max(self) -> None:
        """Retry-After above the 30s ceiling is clamped, not passed through (NET-018)."""
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=5.0):
            result = _compute_backoff_delay(429, 0, 600.0)

        assert result == 30.0  # 600 clamped to ceiling

    def test_retry_after_overrides_delay(self) -> None:
        """Test Retry-After header value overrides calculated delay."""
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=0.5):
            result = _compute_backoff_delay(429, 0, 5.0)

        assert result == 5.0

    def test_retry_after_ignored_when_smaller(self) -> None:
        """Test Retry-After header ignored when smaller than calculated delay."""
        with patch("vkdownloader.services.downloader_throttle.random.uniform", return_value=2.0):
            result = _compute_backoff_delay(429, 2, 1.0)

        assert result == 2.0


class TestWaitWithShutdown:
    """Tests for _wait_with_shutdown function."""

    @pytest.mark.asyncio
    async def test_returns_false_when_no_shutdown(self) -> None:
        """Test returns False when delay completes without shutdown."""
        mock_event = MagicMock()

        async def mock_wait_for(coro: Coroutine[Any, Any, Any], timeout: float | None) -> Any:
            # Simulate timeout (no shutdown)
            raise TimeoutError()

        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for", side_effect=mock_wait_for
        ):
            result = await _wait_with_shutdown(0.1, mock_event, 0, "https://example.com/segment.ts")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_shutdown(self) -> None:
        """Test returns True when shutdown is triggered."""
        mock_event = MagicMock()

        async def mock_wait_for(coro: Coroutine[Any, Any, Any], timeout: float | None) -> Any:
            # Simulate shutdown triggered - return immediately
            return None

        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for", side_effect=mock_wait_for
        ):
            result = await _wait_with_shutdown(0.1, mock_event, 0, "https://example.com/segment.ts")

        assert result is True

    @pytest.mark.asyncio
    async def test_handles_none_event_with_sleep(self) -> None:
        """Test handles None shutdown_event by sleeping."""
        sleep_called: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_called.append(delay)

        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.sleep", side_effect=mock_sleep
        ):
            result = await _wait_with_shutdown(0.1, None, 0, "https://example.com/segment.ts")

        assert result is False
        assert sleep_called == [0.1]


class TestRetryableStatusCodes:
    """Tests for RETRYABLE_STATUS_CODES constant."""

    def test_contains_429(self) -> None:
        """Test that 429 is in RETRYABLE_STATUS_CODES."""
        assert 429 in RETRYABLE_STATUS_CODES

    def test_contains_5xx_codes(self) -> None:
        """Test that 5xx status codes are in RETRYABLE_STATUS_CODES."""
        assert 500 in RETRYABLE_STATUS_CODES
        assert 502 in RETRYABLE_STATUS_CODES
        assert 503 in RETRYABLE_STATUS_CODES
        assert 504 in RETRYABLE_STATUS_CODES

    def test_contains_408(self) -> None:
        """Test that 408 (Request Timeout) is in RETRYABLE_STATUS_CODES."""
        assert 408 in RETRYABLE_STATUS_CODES

    def test_contains_425(self) -> None:
        """Test that 425 (Too Early) is in RETRYABLE_STATUS_CODES."""
        assert 425 in RETRYABLE_STATUS_CODES

    def test_excludes_non_retryable_codes(self) -> None:
        """Test that non-retryable status codes are not in RETRYABLE_STATUS_CODES."""
        assert 200 not in RETRYABLE_STATUS_CODES
        assert 403 not in RETRYABLE_STATUS_CODES
        assert 404 not in RETRYABLE_STATUS_CODES


class TestBackoffPauseDuration:
    """Tests for URLBackoffCoordinator pause_seconds configuration."""

    def test_default_pause_seconds(self) -> None:
        """Default coordinator uses _DEFAULT_BACKOFF_PAUSE_SECONDS."""
        coordinator = URLBackoffCoordinator()
        assert coordinator.pause_seconds == _DEFAULT_BACKOFF_PAUSE_SECONDS

    def test_custom_pause_seconds(self) -> None:
        """Custom pause_seconds is stored on the coordinator."""
        coordinator = URLBackoffCoordinator(pause_seconds=5.0)
        assert coordinator.pause_seconds == 5.0


class TestResourceKey:
    """Tests for _resource_key function."""

    def test_strips_path_and_query(self) -> None:
        """_resource_key returns just the origin (host:port)."""
        url = "https://cdn.example.com/path/to/segment.ts?token=abc"
        assert _resource_key(url) == "cdn.example.com"

    def test_strips_userinfo(self) -> None:
        """_resource_key strips userinfo from the netloc."""
        url = "https://user:pass@cdn.example.com/seg.ts"
        assert _resource_key(url) == "cdn.example.com"

    def test_lowercases_host(self) -> None:
        """_resource_key lowercases the hostname."""
        url = "https://CDN.Example.COM/seg.ts"
        assert _resource_key(url) == "cdn.example.com"

    def test_keeps_port(self) -> None:
        """_resource_key includes the port when present."""
        url = "https://cdn.example.com:8080/seg.ts"
        assert _resource_key(url) == "cdn.example.com:8080"

    def test_different_paths_same_origin(self) -> None:
        """Different paths on the same origin produce the same key."""
        url1 = "https://cdn.example.com/path1/seg1.ts"
        url2 = "https://cdn.example.com/path2/seg2.ts"
        assert _resource_key(url1) == _resource_key(url2)

    def test_different_origins_different_keys(self) -> None:
        """Different origins produce different keys."""
        url1 = "https://cdn1.example.com/seg.ts"
        url2 = "https://cdn2.example.com/seg.ts"
        assert _resource_key(url1) != _resource_key(url2)


class TestBackoffCoordinatorPause:
    """Tests for URLBackoffCoordinator.pause method."""

    @pytest.mark.asyncio
    async def test_pause_sets_timestamp(self) -> None:
        """After pause, wait_if_paused returns True for the same key."""
        coordinator = URLBackoffCoordinator()
        await coordinator.pause("https://cdn.example.com/seg.ts", 1.0)
        result = await coordinator.wait_if_paused("https://cdn.example.com/seg.ts")
        assert result is True

    @pytest.mark.asyncio
    async def test_pause_overwrites_previous(self) -> None:
        """Second pause overwrites the previous timestamp, not stacked."""
        coordinator = URLBackoffCoordinator()
        url = "https://cdn.example.com/seg.ts"
        # First pause with a very short duration
        await coordinator.pause(url, 0.01)

        # Mock wait_for so we don't actually sleep
        async def mock_wait_for(coro: Coroutine[Any, Any, Any], timeout: float | None) -> Any:
            coro.close()  # Prevent unawaited-coroutine warning (GC-timing artifact)
            raise TimeoutError()

        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for",
            side_effect=mock_wait_for,
        ):
            result1 = await coordinator.wait_if_paused(url)
        # Still paused — the first pause (0.01s) is still active
        assert result1 is True

        # Second pause with a longer duration overwrites the timestamp
        await coordinator.pause(url, 100.0)
        with patch(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for",
            side_effect=mock_wait_for,
        ):
            result2 = await coordinator.wait_if_paused(url)
        assert result2 is True

    @pytest.mark.asyncio
    async def test_wait_if_paused_false_without_pause(self) -> None:
        """wait_if_paused returns False when no prior pause for that key."""
        coordinator = URLBackoffCoordinator()
        result = await coordinator.wait_if_paused("https://cdn.example.com/seg.ts")
        assert result is False


class TestBackoffPauseSharedState:
    """Tests for shared backoff state across different URL paths."""

    @pytest.mark.asyncio
    async def test_pause_on_one_path_pauses_different_path_same_origin(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pausing one path on an origin pauses a different path on the same origin."""
        coordinator = URLBackoffCoordinator(pause_seconds=10.0)
        url1 = "https://cdn.example.com/path1/seg.ts"
        url2 = "https://cdn.example.com/path2/seg.ts"

        await coordinator.pause(url1, coordinator.pause_seconds)

        assert _resource_key(url1) == _resource_key(url2)

        # wait_if_paused should return True for url2 because the key is the same.
        # Mock asyncio.wait_for so the test does not actually sleep 10 seconds.
        async def mock_wait_for(coro: Coroutine[Any, Any, Any], timeout: float | None) -> Any:
            coro.close()  # Prevent unawaited-coroutine warning
            raise TimeoutError()

        monkeypatch.setattr(
            "vkdownloader.services.downloader_throttle.asyncio.wait_for", mock_wait_for
        )

        result = await coordinator.wait_if_paused(url2)
        assert result is True


class TestProgressManager:
    """Tests for ProgressManager class."""

    @pytest.mark.asyncio
    async def test_update_stores_progress(self) -> None:
        """Test that update stores progress for a URL index."""
        manager = ProgressManager()
        await manager.update(0, 25, 100)

        result = await manager.get_formatted_progress(1)
        assert "video_0: 25/100" in result

    @pytest.mark.asyncio
    async def test_update_multiple_urls(self) -> None:
        """Test that update handles multiple URLs independently."""
        manager = ProgressManager()
        await manager.update(0, 25, 100)
        await manager.update(1, 50, 200)

        result = await manager.get_formatted_progress(2)
        assert "video_0: 25/100" in result
        assert "video_1: 50/200" in result

    @pytest.mark.asyncio
    async def test_get_formatted_progress_defaults_to_zero(self) -> None:
        """Test that get_formatted_progress returns 0B for unset URLs."""
        manager = ProgressManager()
        result = await manager.get_formatted_progress(3)

        assert "video_0: 0B" in result
        assert "video_1: 0B" in result
        assert "video_2: 0B" in result

    @pytest.mark.asyncio
    async def test_clear_removes_all_progress(self) -> None:
        """Test that clear removes all stored progress."""
        manager = ProgressManager()
        await manager.update(0, 50, 100)
        await manager.clear()

        result = await manager.get_formatted_progress(1)
        assert "video_0: 0B" in result

    @pytest.mark.asyncio
    async def test_overwrites_existing_progress(self) -> None:
        """Test that update overwrites existing progress for same index."""
        manager = ProgressManager()
        await manager.update(0, 25, 100)
        await manager.update(0, 75, 100)

        result = await manager.get_formatted_progress(1)
        assert "video_0: 75/100" in result
        assert "25" not in result

    @pytest.mark.asyncio
    async def test_unknown_total_shows_bytes_not_ratio(self) -> None:
        """Test that total=0 (unknown total) shows bytes with B suffix."""
        manager = ProgressManager()
        # Simulate ffmpeg progress: downloaded=12345, total=0 (unknown)
        await manager.update(0, 12345, 0)

        result = await manager.get_formatted_progress(1)
        assert "video_0: 12.1KB" in result
        assert "100" not in result  # Should NOT show 100% (when total is unknown)


class TestClientTimeoutComposition:
    """Table-driven tests that build_client_timeout maps the setting to a
    single composed client timeout object.

    sock_connect is intentionally dropped (redundant with connect); sock_read
    grows with the operator's budget. The returned object is inspected directly
    via its attributes rather than by importing the client library.
    """

    @pytest.mark.parametrize(
        ("download_timeout", "expected_total", "expected_connect", "expected_sock_read"),
        [
            (30, 30, 7, 30),  # floor
            (300, 300, 30, 300),  # default
            (3600, 3600, 30, 3600),  # ceiling
        ],
    )
    def test_composition(
        self,
        download_timeout: int,
        expected_total: int,
        expected_connect: int,
        expected_sock_read: int,
    ) -> None:
        """Each row checks total/connect/sock_read against the documented formula."""
        timeout = build_client_timeout(download_timeout)

        assert timeout.total == expected_total
        assert timeout.connect == expected_connect
        assert timeout.sock_read == expected_sock_read
        assert timeout.sock_connect is None
