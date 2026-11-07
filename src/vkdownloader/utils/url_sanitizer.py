"""URL sanitization utilities for secure logging."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from structlog.typing import EventDict

# Matches http/https URLs in text (including query strings with signed tokens).
# Used to redact URLs found in subprocess stdout/stderr before logging.
_URL_REGEX = re.compile(r"https?://[^\s'\"<>]+")

# Artefact-path redaction rules (SEC-006). The literals are duplicated from
# services/ytdlp_downloader._COOKIE_ARTIFACT_PREFIX / _COOKIE_ARTIFACT_SUFFIX /
# _ARTEFACT_DIR_SUFFIX; utils/ must not import services/ (layer rule, and it
# would invert the import order).
#
# Left-boundary law: a rule's left boundary must be a predicate its own
# replacement can never satisfy. ***REDACTED*** ends in '*', a non-word char, so
# a \b guard would manufacture a boundary on the second pass (measured 3
# fixed-point violations in 400 000). '*' is inside the negated class
# `[^\s'\"<>]` — the excluded set: characters whose presence before a match
# position EXCLUDES it — so the lookbehind below is unsatisfiable by the
# marker (0 violations). The parent is
# CONSUMED by the optional greedy lead, not asserted by lookbehind: a
# variable-length lookbehind is illegal in this re module, and consuming the
# parent is what removes the username-bearing temp root
# (C:\Users\<name>\AppData\Local\Temp, CWE-532).
#
# No re.IGNORECASE: every matched string is built from a frozen lowercase
# literal, and IGNORECASE widens [a-z] with U+0130/U+0131/U+017F/U+212A for
# zero measured coverage gain. The tail is [a-z0-9_]+, not {8}:
# tempfile._RandomNameSequence.characters is a CPython internal whose length is
# not contractual. The match ends at the artefact NAME; a trailing separator is
# never consumed, so the marker cannot fuse to the next path component
# (***REDACTED***\owner.pid).
_ARTEFACT_LEAD = r"(?<![^\s'\"<>])(?:[^\s'\"<>]*[\\/])?"
_COOKIE_FILE_ARTEFACT_REGEX = re.compile(_ARTEFACT_LEAD + r"vk_cookies_[a-z0-9_]+\.cookies\.txt")
_COOKIE_DIR_ARTEFACT_REGEX = re.compile(_ARTEFACT_LEAD + r"vk_cookies__dir[a-z0-9_]+")

# Cookie header redaction (SEC-003). Redacts the entire value of ``Cookie:`` /
# ``Set-Cookie:`` headers, including any attributes, so secret cookie values
# cannot leak through child-process output or exception messages. The header
# name itself is preserved for diagnostic context.
_COOKIE_HEADER_REGEX = re.compile(r"(?i)((?:set-cookie|cookie):)\s*.*")

# Bare cookie-pair redaction (SEC-003). Targets common cookie/secret-bearing
# keys rather than every ``key=value`` run, so ordinary diagnostic fields such
# as ``status=ok`` or ``count=42`` survive untouched. Only the value is
# replaced; the key is preserved as non-secret diagnostic context.
_COOKIE_PAIR_KEYS = (
    "session",
    "sessionid",
    "session_id",
    "sid",
    "csrftoken",
    "csrf_token",
    "xsrf",
    "xsrf_token",
    "auth",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "jwt",
    "cookie",
    "secret",
)
_COOKIE_PAIR_REGEX = re.compile(
    r"(?i)\b(" + "|".join(re.escape(key) for key in _COOKIE_PAIR_KEYS) + r")\s*=\s*[^\s;]+"
)


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
        host = parsed.netloc.rsplit("@", 1)[-1]
        return f"{parsed.scheme}://{host}/***REDACTED***"
    except Exception:
        return "***REDACTED***"


def sanitize_text_for_log(text: str) -> str:
    """Redact URLs and the product's own artefact paths from text.

    Scans ``text`` for ``http(s)://`` URLs and for the artefact shapes the
    product's lifecycle writes - ``vk_cookies_<tail>.cookies.txt`` and the
    ``vk_cookies__dir<tail>`` directory - and replaces each match while keeping
    diagnostic context.

    The substitutions run in a fixed order: URL first, then the cookie-file
    artefact, then the cookie-directory artefact. URL-first is mandatory: an
    artefact path nested inside a URL must redact the path and preserve the host;
    artefact-first would swallow the whole run and destroy the host.

    Shapes that ARE matched:
        - ``https?://`` URLs (reduced to ``scheme://host/***REDACTED***``).
        - ``Cookie:`` / ``Set-Cookie:`` header values (entire value redacted).
        - Bare cookie pairs for common cookie/secret-bearing keys such as
          ``session=...`` or ``token=...`` (value only redacted).
        - ``vk_cookies_<tail>.cookies.txt`` file artefacts, including any
          leading parent path, which is consumed so the username-bearing temp
          root is removed (CWE-532).
        - ``vk_cookies__dir<tail>`` directory artefacts, same rule.

    Shapes that are NOT matched:
        - Ordinary ``key=value`` diagnostics whose key is not a known
          cookie/secret-bearing key (e.g. ``status=ok``, ``count=42``).
        - Bare ``name=value`` pairs and user-chosen output paths that do not
          bear one of the artefact shapes above.

    Accepted collateral: an unquoted ``key=value`` run carrying an artefact
    collapses whole (``path=C:\\…\\vk_cookies_x.cookies.txt`` ->
    ``***REDACTED***``) because the identifying parent is consumed with the key.
    This is bounded - the three child-output sinks receive whitespace-delimited
    argv, never ``key=``; structlog dict values keep the key as
    ``"path": "***REDACTED***"``.

    Accepted residual: when two artefact names are concatenated with no
    separator between them, only the first is redacted and the second is
    deliberately left unredacted (``***REDACTED***vk_cookies_b.cookies.txt``).
    That non-redaction is precisely what makes the rule a fixed point:
    ``***REDACTED***`` ends in ``*``, so a ``\\b``-guarded rule would
    manufacture a boundary on the second pass and consume the second name,
    breaking idempotency (measured 3 fixed-point violations in 400 000 for
    ``\\b``, 0 for the chosen lookbehind). This is a deliberate accepted
    residual, not an oversight, and is unreachable from production: every
    value that reaches a sink is either a ``str(Path)`` from ``mkstemp`` /
    ``mkdtemp`` (always preceded by a separator or run start) or
    whitespace-delimited child argv.

    Args:
        text: Raw text that may contain URLs or artefact paths (e.g. yt-dlp or
            ffmpeg stderr, or an error message built from a child transcript).

    Returns:
        Text with URLs redacted to ``scheme://host/***REDACTED***`` and
        artefact tokens redacted to ``***REDACTED***``.
    """
    text = _URL_REGEX.sub(lambda m: _strip_auth_params(m.group(0)), text)
    text = _COOKIE_HEADER_REGEX.sub(r"\1 ***REDACTED***", text)
    text = _COOKIE_PAIR_REGEX.sub(lambda m: f"{m.group(1)}=***REDACTED***", text)
    text = _COOKIE_FILE_ARTEFACT_REGEX.sub("***REDACTED***", text)
    text = _COOKIE_DIR_ARTEFACT_REGEX.sub("***REDACTED***", text)
    return text


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


# Structural keys injected by structlog processors or contextvars that must
# never be redacted: ``event`` is the log message (redacting it would rename/
# corrupt the record), ``level`` is the log-level string, ``timestamp`` is the
# ISO-8601 stamp from TimeStamper, and ``correlation_id`` is the 8-char hex
# trace identifier from ``utils/correlation.py`` — all used for log grouping
# and correlation, so transforming them would break observability semantics.
_STRUCTURAL_KEYS: frozenset[str] = frozenset({"event", "level", "timestamp", "correlation_id"})


_PRIMITIVE_TYPES: tuple[type, ...] = (int, float, bool, complex, type(None))


def _sanitize_value(
    value: object,
    depth: int,
    seen: set[int],
) -> object:
    if isinstance(value, str):
        return sanitize_text_for_log(value)
    if isinstance(value, bytes):
        return sanitize_for_log(value)
    if isinstance(value, BaseException):
        return sanitize_exception(value)
    if isinstance(value, (list, tuple, dict)):
        return _sanitize_collection(value, depth, seen)
    if isinstance(value, _PRIMITIVE_TYPES):
        return value
    # Unknown/non-primitive objects: stringify and sanitize so secrets in
    # their repr cannot leak unredacted.
    return sanitize_text_for_log(str(value))


def _sanitize_deep(
    value: object,
    seen: set[int],
) -> object:
    """Sanitize every string leaf in a subtree without a depth bound.

    Used at the depth boundary so collections that are too deep to recurse
    through the normal bounded path still have their string leaves redacted.
    Cycle guard prevents infinite traversal; a cycle yields an empty
    container rather than the original object.
    """
    if isinstance(value, str):
        return sanitize_text_for_log(value)
    if isinstance(value, bytes):
        return sanitize_for_log(value)
    if isinstance(value, BaseException):
        return sanitize_exception(value)
    if not isinstance(value, (list, tuple, dict)):
        if isinstance(value, _PRIMITIVE_TYPES):
            return value
        return sanitize_text_for_log(str(value))
    if id(value) in seen:
        if isinstance(value, list):
            return []
        if isinstance(value, tuple):
            return ()
        return {}
    seen.add(id(value))
    try:
        if isinstance(value, list):
            return [_sanitize_deep(item, seen) for item in value]
        if isinstance(value, tuple):
            return tuple(_sanitize_deep(item, seen) for item in value)
        if isinstance(value, dict):
            return {k: _sanitize_deep(v, seen) for k, v in value.items()}
        return value
    finally:
        seen.discard(id(value))


def _sanitize_collection(
    value: object,
    depth: int = 0,
    seen: set[int] | None = None,
) -> object:
    """Recursively sanitize containers with a bounded depth and cycle guard."""
    if seen is None:
        seen = set()
    if not isinstance(value, (list, tuple, dict)):
        return _sanitize_value(value, depth, seen)
    if depth >= 8:
        return _sanitize_deep(value, seen)
    if id(value) in seen:
        if isinstance(value, list):
            return []
        if isinstance(value, tuple):
            return ()
        return {}
    seen.add(id(value))
    try:
        if isinstance(value, list):
            return [_sanitize_value(item, depth + 1, seen) for item in value]
        if isinstance(value, tuple):
            return tuple(_sanitize_value(item, depth + 1, seen) for item in value)
        if isinstance(value, dict):
            return {k: _sanitize_value(v, depth + 1, seen) for k, v in value.items()}
        return value
    finally:
        seen.discard(id(value))


def sanitize_exception(exc: BaseException) -> str:
    """Sanitize an exception into a safe string (no raw .args leakage)."""
    try:
        message = str(exc)
    except Exception:
        message = type(exc).__name__
    return sanitize_text_for_log(f"{type(exc).__name__}: {message}")


def sanitize_for_log(value: object) -> object:
    """Public helper to sanitize arbitrary values for logging."""
    if isinstance(value, str):
        return sanitize_text_for_log(value)
    if isinstance(value, bytes):
        try:
            return sanitize_text_for_log(value.decode("utf-8", errors="replace"))
        except Exception:
            return "***REDACTED***"
    if isinstance(value, BaseException):
        return sanitize_exception(value)
    if isinstance(value, (list, tuple, dict)):
        return _sanitize_collection(value, 0, set())
    if isinstance(value, (int, float, bool, complex, type(None))):
        return value
    return sanitize_text_for_log(str(value))


def redact_log_event(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    for key, value in list(event_dict.items()):
        if key in _STRUCTURAL_KEYS:
            continue
        event_dict[key] = _sanitize_value(value, 0, set())
    return event_dict


__all__ = [
    "_COOKIE_DIR_ARTEFACT_REGEX",
    "_COOKIE_FILE_ARTEFACT_REGEX",
    "_COOKIE_HEADER_REGEX",
    "_COOKIE_PAIR_REGEX",
    "_strip_auth_params",
    "redact_log_event",
    "sanitize_text_for_log",
    "sanitize_url_for_log",
    "sanitize_exception",
    "sanitize_for_log",
]
