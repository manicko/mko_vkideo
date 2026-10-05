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
        - ``vk_cookies_<tail>.cookies.txt`` file artefacts, including any
          leading parent path, which is consumed so the username-bearing temp
          root is removed (CWE-532).
        - ``vk_cookies__dir<tail>`` directory artefacts, same rule.

    Shapes that are NOT matched:
        - ``Cookie:`` / ``Set-Cookie:`` header values (D-5 resolved to Alt A;
          B4-AUDIT measured no child process emits one to any sink).
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


def _sanitize_collection(
    value: list[object] | tuple[object, ...] | dict[str, object],
) -> list[object] | tuple[object, ...] | dict[str, object]:
    """Apply :func:`sanitize_text_for_log` depth-1 into a container.

    Builds a **new** container of the same type (never mutates the input, which
    structlog's shallow per-record copy would otherwise share across records).
    Top-level ``str`` elements are redacted; nested containers are passed
    through unchanged (depth-1 only). Dict keys are preserved byte-identical;
    only the values are sanitised.
    """
    if isinstance(value, list):
        return [sanitize_text_for_log(v) if isinstance(v, str) else v for v in value]
    if isinstance(value, tuple):
        return tuple(sanitize_text_for_log(v) if isinstance(v, str) else v for v in value)
    if isinstance(value, dict):
        return {k: sanitize_text_for_log(v) if isinstance(v, str) else v for k, v in value.items()}


def redact_log_event(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Redact URLs and artefact paths from every string value in a structlog event dict.

    This is a central, event-name-agnostic structlog processor (B6) that applies
    :func:`sanitize_text_for_log` to every ``str`` value in the event dict,
    excluding the structural keys that structlog itself manages (``event``,
    ``level``, ``timestamp``, ``correlation_id``). It is idempotent: the redaction
    marker is a fixed point of ``sanitize_text_for_log``, so running the processor
    on an already-redacted value is a no-op.

    The module holds both the text transform (:func:`sanitize_text_for_log`) and
    this event-dict transform over that same policy, so the redaction rules
    (URL regex, artefact regexes, ordering, idempotency) stay in one place.

    Non-string values (``None``, ``int``, ``bool``, ``float``, ``bytes``,
    collections) are passed through unchanged. For ``list`` / ``tuple`` / ``dict``
    values, the processor recurses **depth-1**: string elements are redacted,
    non-string leaves pass through, and nested containers deeper than depth-1
    are returned without further recursion. The original container is never
    mutated in place — a new container is always built, because structlog's
    per-record dict copy is shallow and a shared list/tuple/dict would otherwise
    leak redacted state across records.

    A ``StrEnum`` member is an ``isinstance(value, str)`` match; ``re.sub`` returns
    a plain ``str``, so the field's rendered output is byte-identical even though
    its Python type narrows from enum to ``str``.
    """
    for key, value in event_dict.items():
        if key in _STRUCTURAL_KEYS:
            continue
        if isinstance(value, str):
            event_dict[key] = sanitize_text_for_log(value)
        elif isinstance(value, (list, tuple, dict)):
            event_dict[key] = _sanitize_collection(value)
    return event_dict


__all__ = [
    "_strip_auth_params",
    "redact_log_event",
    "sanitize_text_for_log",
    "sanitize_url_for_log",
]
