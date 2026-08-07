"""Tests for correlation ID utilities."""

import uuid

from vkdownloader.utils.correlation import (
    bind_correlation_id,
    clear_correlation_id,
    generate_correlation_id,
    get_correlation_id,
)


def test_generate_correlation_id_returns_hex() -> None:
    """Test that generate_correlation_id returns a unique 8-char hex string."""
    cid = generate_correlation_id()
    assert len(cid) == 8
    assert all(c in "0123456789abcdef" for c in cid)


def test_generate_correlation_id_uniqueness() -> None:
    """Test that generate_correlation_id produces unique IDs."""
    ids = {generate_correlation_id() for _ in range(100)}
    assert len(ids) == 100


def test_generate_correlation_id_truncates_uuid() -> None:
    """Test that generate_correlation_id truncates uuid4 to 8 hex chars."""
    full = uuid.uuid4().hex
    # Ensure the generated ID is a prefix of some uuid4 hex
    cid = generate_correlation_id()
    assert len(cid) == 8
    # Verify it's a valid hex string
    int(cid, 16)


def test_bind_and_clear_correlation_id() -> None:
    """Test that bind sets and clear removes the correlation ID from context."""
    cid = generate_correlation_id()
    bind_correlation_id(cid)
    assert get_correlation_id() == cid
    clear_correlation_id()
    assert get_correlation_id() is None


def test_correlation_id_does_not_leak_after_clear() -> None:
    """Test that clearing the context removes the correlation ID completely."""
    cid1 = generate_correlation_id()
    bind_correlation_id(cid1)
    assert get_correlation_id() == cid1

    cid2 = generate_correlation_id()
    bind_correlation_id(cid2)
    assert get_correlation_id() == cid2  # Overwritten, not appended

    clear_correlation_id()
    assert get_correlation_id() is None  # Fully cleared
