"""URL sanitization utilities for secure logging."""

import re
from urllib.parse import urlsplit

# Matches http/https URLs in text (including query strings with signed tokens).
# Used to redact URLs found in subprocess stdout/stderr before logging.
_URL_REGEX = re.compile(r"https?://[^\s'\"<>]+")


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


def sanitize_text_for_log(text: str) -> str:
    """Redact all URLs found in arbitrary text (e.g. subprocess output).

    Scans ``text`` for ``http(s)://`` URLs and replaces each match
    with only its scheme and host via :func:`_strip_auth_params`,
    preventing signed CDN tokens or cookie file paths in subprocess
    output from leaking into log files.

    Args:
        text: Raw text that may contain URLs (e.g. ffmpeg/yt-dlp stderr).

    Returns:
        Text with all URLs redacted to ``scheme://host/***REDACTED***/``.
    """
    return _URL_REGEX.sub(lambda m: _strip_auth_params(m.group(0)), text)


def sanitize_url_for_log(url: str) -> str:
    """Redact URL for logging — show only scheme and host.

    Public alias for :func:`_strip_auth_params`. Replaces path and all query
    values with redacted markers to prevent signed CDN URLs with embedded
    tokens from leaking into logs.

    Args:
        url: The original URL potentially containing auth parameters.

    Returns:
        URL with only scheme and host visible, all other components redacted.
    """
    return _strip_auth_params(url)


__all__ = ["_strip_auth_params", "sanitize_text_for_log", "sanitize_url_for_log"]
