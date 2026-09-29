"""Human-readable rendering of byte counts for logs and user-facing messages.

The downloader reports progress and disk-space requirements in bytes, which are
meaningless to read: a 12,345-byte segment is ``12.1KB``. This module owns the
single rendering of that number, so the progress line and the pre-merge
free-space error cannot drift apart in units or rounding.
"""

_KIB = 1024
_MIB = 1024 * 1024
_GIB = 1024 * 1024 * 1024


def format_bytes(num_bytes: int) -> str:
    """Format a byte count into a human-readable string with an SI prefix.

    Binary multiples are used but reported with the conventional SI spelling
    (``KB``, ``MB``, ``GB``), which is what users of a downloader expect to
    read. Values are truncated to one decimal place.

    Args:
        num_bytes: Number of bytes.

    Returns:
        String like "25B", "1.5KB", "45.2MB", "2.1GB".
    """
    if num_bytes < _KIB:
        return f"{num_bytes}B"
    elif num_bytes < _MIB:
        return f"{num_bytes / _KIB:.1f}KB"
    elif num_bytes < _GIB:
        return f"{num_bytes / _MIB:.1f}MB"
    else:
        return f"{num_bytes / _GIB:.1f}GB"
