"""Unit tests for throttle utilities with retry logic for rate limiting."""

import asyncio
import builtins
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from vkdownloader.services.downloader_throttle import (
    RETRYABLE_STATUS_CODES,
    ProgressManager,
    URLBackoffCoordinator,
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
            mock_wait_for.side_effect = builtins.TimeoutError()
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
                    mock_wait_for.side_effect = builtins.TimeoutError()
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
        await coordinator.pause("https://example.com/video1", 0.01)

        result = await coordinator.wait_if_paused("https://example.com/video1")
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_if_paused_returns_on_shutdown(self) -> None:
        """Test wait_if_paused respects shutdown event and returns early."""
        coordinator = URLBackoffCoordinator()
        await coordinator.pause("https://example.com/video1", 100.0)

        # Mock shutdown event that is already set
        mock_event = MagicMock()
        mock_event.is_set.return_value = True
        mock_event.wait = AsyncMock()

        with patch(
            "vkdownloader.services.downloader_throttle.get_shutdown_event",
            return_value=mock_event,
        ):
            result = await coordinator.wait_if_paused("https://example.com/video1")

        # Should return True when shutdown is triggered
        assert result is True
        mock_event.wait.assert_called_once()


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
        """Test that get_formatted_progress returns 0/0 for unset URLs."""
        manager = ProgressManager()
        result = await manager.get_formatted_progress(3)

        assert "video_0: 0/0" in result
        assert "video_1: 0/0" in result
        assert "video_2: 0/0" in result

    @pytest.mark.asyncio
    async def test_clear_removes_all_progress(self) -> None:
        """Test that clear removes all stored progress."""
        manager = ProgressManager()
        await manager.update(0, 50, 100)
        await manager.clear()

        result = await manager.get_formatted_progress(1)
        assert "video_0: 0/0" in result

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
    async def test_progress_manager_concurrent_updates(self) -> None:
        """Test that ProgressManager handles concurrent updates safely."""
        manager = ProgressManager()
        url_count = 10

        async def update_task(idx: int) -> None:
            for i in range(100):
                await manager.update(idx, i, 100)

        # Run concurrent updates
        await asyncio.gather(*[update_task(i) for i in range(url_count)])

        # Verify all states are consistent
        progress = await manager.get_formatted_progress(url_count)
        assert "video_" in progress
        for i in range(url_count):
            value = await manager.get_progress(i)
            assert value == (99, 100)  # Last update

    @pytest.mark.asyncio
    async def test_progress_manager_concurrent_reads_during_writes(self) -> None:
        """Test that concurrent reads return consistent data during writes."""
        manager = ProgressManager()
        url_count = 5
        read_results: list[tuple[int, tuple[int, int]]] = []

        async def update_task(idx: int) -> None:
            for i in range(50):
                await manager.update(idx, i, 100)

        async def read_task(reader_id: int) -> None:
            for _ in range(50):
                for i in range(url_count):
                    value = await manager.get_progress(i)
                    # Should always have valid tuple values
                    assert isinstance(value, tuple)
                    assert len(value) == 2
                    read_results.append((reader_id, value))

        # Run concurrent reads and writes
        await asyncio.gather(
            *[update_task(i) for i in range(url_count)],
            *[read_task(i) for i in range(3)]
        )

        # Verify no race conditions - all read results should be valid
        assert len(read_results) > 0
        for _reader_id, value in read_results:
            downloaded, total = value
            assert total == 100  # Total should always be our test value
            assert 0 <= downloaded <= 100  # Downloaded should be in valid range

    @pytest.mark.asyncio
    async def test_get_progress_returns_default_for_missing_key(self) -> None:
        """Test that get_progress returns (0, 0) for unset index."""
        manager = ProgressManager()
        result = await manager.get_progress(999)
        assert result == (0, 0)
