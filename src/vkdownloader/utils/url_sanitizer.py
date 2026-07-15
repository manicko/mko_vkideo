"""URL sanitization utilities for secure logging."""

from urllib.parse import urlsplit


def _strip_auth_params(url: str) -> str:
    """
    Redact URL for logging - show only scheme and host.

    Replaces path and all query values with redacted markers to prevent
    signed CDN URLs with embedded tokens from leaking into logs.

    Args:
        url: The original URL potentially containing auth parameters.

    Returns:
        URL with only scheme and host visible, all other components redacted.
    """
    try:
        parsed = urlsplit(url)
        if not parsed.scheme or not parsed.netloc:
            return "***REDACTED***"
        return f"{parsed.scheme}://{parsed.netloc}/***REDACTED***"
    except Exception:
        return "***REDACTED***"
