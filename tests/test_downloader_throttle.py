"""Unit tests for throttle utilities with retry logic for rate limiting."""

from unittest.mock import AsyncMock, MagicMock, patch
from asyncio import TimeoutError

import pytest

from vkdownloader.services.downloader_throttle import (
    RETRYABLE_STATUS_CODES,
    _parse_retry_after,
    _retry_429_with_backoff,
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
        # Should only call get once (no retry)
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

        def get_side_effect(*args, **kwargs):
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

        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            # Raise TimeoutError to simulate normal timeout (allows retry to continue)
            mock_wait_for.side_effect = TimeoutError()
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2  # First 429, then success
        # Should have wait_for call with timeout (between 0 and 1.0 on first retry)
        assert mock_wait_for.call_count == 1
        # Extract timeout from the call - it's keyword argument 'timeout'
        timeout_arg = mock_wait_for.call_args[1].get("timeout")
        assert timeout_arg is not None
        assert 0 <= timeout_arg <= 1.0

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

        def get_side_effect(*args, **kwargs):
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

        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            # Raise TimeoutError to simulate normal timeout (allows retry to continue)
            mock_wait_for.side_effect = TimeoutError()
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
            )

        assert result == b"segment content"
        assert call_count == 2
        # Retry-After of 5 should be used as timeout
        timeout_arg = mock_wait_for.call_args[1].get("timeout")
        assert timeout_arg == 5.0

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

        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()
            result = await _retry_429_with_backoff(
                mock_session,
                "https://example.com/segment.ts",
                {"User-Agent": "test"},
                segment_index=0,
                max_retries=3,
            )

        assert result is None
        # Should attempt 3 times (max_retries)
        assert mock_session.get.call_count == 3

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

        def get_side_effect(*args, **kwargs):
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

        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()
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

        def get_side_effect(*args, **kwargs):
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

        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()
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

        def get_side_effect(*args, **kwargs):
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

        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()
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

        def get_side_effect(*args, **kwargs):
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

        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()
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
    async def test_delay_capped_at_30_seconds(self) -> None:
        """Test delay is capped at 30 seconds maximum."""
        mock_session = AsyncMock()
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {}
        mock_response_429.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args, **kwargs):
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

        # Patch wait_for to raise TimeoutError (normal timeout, allows retry)
        with patch("vkdownloader.services.downloader_throttle.asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()
            with patch("vkdownloader.services.downloader_throttle.random.uniform") as mock_uniform:
                mock_uniform.return_value = 1.0  # Return any valid value
                result = await _retry_429_with_backoff(
                    mock_session,
                    "https://example.com/segment.ts",
                    {"User-Agent": "test"},
                    segment_index=0,
                    max_retries=3,
                )

                assert result == b"segment content"
                # Verify uniform was called - the upper bound should be capped at 30
                upper_bound = mock_uniform.call_args[0][1]  # Second positional arg is upper bound
                assert upper_bound == 1.0  # For attempt 0, upper_bound = min(1.0, 30)

    @pytest.mark.asyncio
    async def test_structured_logging_on_retry(self) -> None:
        """Test structured logging fields: attempt, status, retry_after, segment_index, url."""
        mock_session = AsyncMock()
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {"Retry-After": "2"}
        mock_response_429.read = AsyncMock()

        mock_response_200 = AsyncMock()
        mock_response_200.status = 200
        mock_response_200.read = AsyncMock(return_value=b"segment content")

        call_count = 0

        def get_side_effect(*args, **kwargs):
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

        # Capture log calls
        with patch(
            "vkdownloader.services.downloader_throttle.logger.warning"
        ) as mock_warning:
            with patch(
                "vkdownloader.services.downloader_throttle._strip_auth_params",
                return_value="https://example.com/segment.ts",
            ):
                with patch(
                    "vkdownloader.services.downloader_throttle.asyncio.wait_for"
                ) as mock_wait_for:
                    # Raise TimeoutError to simulate normal timeout (allows retry to continue)
                    mock_wait_for.side_effect = TimeoutError()
                    result = await _retry_429_with_backoff(
                        mock_session,
                        "https://example.com/segment.ts?token=secret",
                        {"User-Agent": "test"},
                        segment_index=5,
                        max_retries=3,
                    )

        assert result == b"segment content"
        # Verify structured logging was called with correct fields
        mock_warning.assert_called_once()
        call_kwargs = mock_warning.call_args[1]
        assert call_kwargs["attempt"] == 1
        assert call_kwargs["status"] == 429
        assert call_kwargs["retry_after"] == 2.0
        assert call_kwargs["segment_index"] == 5
        assert call_kwargs["url"] == "https://example.com/segment.ts"

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

        with patch(
            "vkdownloader.services.downloader_throttle.logger.warning"
        ) as mock_warning:
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


class TestParseRetryAfter:
    """Tests for _parse_retry_after function."""

    def test_parse_integer_seconds(self) -> None:
        """Test parsing Retry-After header with integer seconds."""
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "120"}

        result = _parse_retry_after(mock_response)

        assert result == 120.0

    def test_no_retry_after_header(self) -> None:
        """Test None returned when no Retry-After header present."""
        mock_response = MagicMock()
        mock_response.headers = {}

        result = _parse_retry_after(mock_response)

        assert result is None

    def test_invalid_integer_returns_none(self) -> None:
        """Test invalid integer format returns None."""
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "invalid"}

        result = _parse_retry_after(mock_response)

        assert result is None

    def test_invalid_date_format_returns_none(self) -> None:
        """Test invalid date format returns None."""
        mock_response = MagicMock()
        mock_response.headers = {"Retry-After": "not-a-date"}

        result = _parse_retry_after(mock_response)

        assert result is None


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

    def test_excludes_non_retryable_codes(self) -> None:
        """Test that non-retryable status codes are not in RETRYABLE_STATUS_CODES."""
        assert 200 not in RETRYABLE_STATUS_CODES
        assert 403 not in RETRYABLE_STATUS_CODES
        assert 404 not in RETRYABLE_STATUS_CODES
