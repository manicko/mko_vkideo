"""Regression tests for D-02: browser session cookies must survive the real consumer.

Playwright reports a browser *session* cookie with ``expires: -1``. The Netscape
format's expiry column wants either a positive UNIX timestamp or ``0`` to mean
"session cookie", so ``-1`` is a timestamp before the epoch. yt-dlp's consumer,
``YoutubeDLCookieJar.load()``, rejects a negative expires at parse time and skips
the entry with only a warning on stderr. With ``--cookie-source browser`` the
product therefore wrote a cookie file that contained no usable cookies.

Every test below drives the product's real writer,
``vkdownloader.services.ytdlp_downloader._create_temp_cookie_file``, and asserts
on what the real consumer parsed out of the resulting file. Assertions are made
against the jar, never against the file's text: a file that *looks* correct is
not evidence that the consumer accepted it.
"""

import time
from typing import cast

from playwright.async_api import Cookie
from yt_dlp.cookies import YoutubeDLCookieJar

from vkdownloader.services.ytdlp_downloader import _create_temp_cookie_file

_DOMAIN = ".vkvideo.ru"
_URL = "https://vkvideo.ru/"
_TEN_YEARS_SECONDS = 10 * 365 * 24 * 3600


def _cookie(name: str, value: str, expires: float) -> Cookie:
    """Build a Playwright-shaped cookie carrying an explicit ``expires`` value."""
    return {"name": name, "value": value, "domain": _DOMAIN, "path": "/", "expires": expires}


def _cookie_without_expiry_key(name: str, value: str) -> Cookie:
    """Build a Playwright-shaped cookie that carries no ``expires`` key at all."""
    return {"name": name, "value": value, "domain": _DOMAIN, "path": "/"}


def _cookie_with_null_expiry(name: str, value: str) -> Cookie:
    """Build a cookie whose ``expires`` key is present but set to ``None``.

    Playwright's ``Cookie`` stub types ``expires`` as ``float``, so this runtime
    shape is narrowed explicitly with ``cast`` rather than silenced.
    """
    return cast(
        "Cookie", {"name": name, "value": value, "domain": _DOMAIN, "path": "/", "expires": None}
    )


def _cookie_with_domain(name: str, value: str, domain: str, expires: float = -1) -> Cookie:
    """Build a Playwright-shaped cookie carrying an explicit ``domain``.

    Supports a **host-only** domain (no leading dot, e.g. ``vkvideo.ru``) —
    the shape Chromium reports for a cookie set without a ``Domain`` attribute
    and the shape SEC-009 proves defeats the Netscape consumer. The module-level
    ``_DOMAIN`` and the three builders above are untouched; this is an *add*,
    not a retarget.
    """
    return {
        "name": name,
        "value": value,
        "domain": domain,
        "path": "/",
        "expires": expires,
    }


class TestCookieRoundTripThroughConsumer:
    """Cookie serialisation verified by loading it with the real yt-dlp consumer."""

    def test_session_cookie_survives_consumer_round_trip(self) -> None:
        """D-02: a browser session cookie (expires -1) survives the real consumer."""
        # The real call site for a `--cookies` file is `load_cookies` in
        # yt_dlp/cookies.py, which builds `YoutubeDLCookieJar(cookie_file)` and
        # then calls `jar.load()` with no arguments. `load()`'s own defaults are
        # `ignore_discard=True, ignore_expires=True` (yt_dlp/cookies.py, the
        # `def load(self, filename=None, ignore_discard=True, ignore_expires=True)`
        # signature), so the bare `jar.load()` below is argument-for-argument
        # the load the product's download path performs.
        cookies: list[Cookie] = [_cookie("session_cookie", "live-value", -1)]

        path = _create_temp_cookie_file(cookies)
        try:
            jar = YoutubeDLCookieJar(str(path))
            jar.load()

            loaded = {cookie.name: cookie for cookie in jar}
            assert "session_cookie" in loaded
            assert loaded["session_cookie"].value == "live-value"
            # Normalised to 0, which the consumer rewrites into a session cookie.
            assert loaded["session_cookie"].discard is True
            assert loaded["session_cookie"].expires is None
        finally:
            path.unlink(missing_ok=True)

    def test_three_expiry_variants_round_trip(self) -> None:
        """D-02: session, absent and future expiries all survive; a past expiry is not used."""
        # Same verified invocation as above: `load_cookies` calls `jar.load()`
        # with no arguments, so `ignore_discard=True, ignore_expires=True`.
        # The second flag is what makes this test interesting: it disables
        # MozillaCookieJar._really_load's load-time expiry filter, so a past
        # timestamp is still retained in the jar and is instead dropped at use
        # time by DefaultCookiePolicy.return_ok_expires. Asserting on jar
        # contents alone would miss the past entry entirely, so both the parse
        # result and the consumer's use-time selection are asserted.
        now = int(time.time())
        cookies: list[Cookie] = [
            _cookie("session_cookie", "v", -1),
            _cookie_without_expiry_key("absent_expiry", "v"),
            _cookie("future_expiry", "v", now + _TEN_YEARS_SECONDS),
            _cookie("past_expiry", "v", now - _TEN_YEARS_SECONDS),
        ]

        path = _create_temp_cookie_file(cookies)
        try:
            jar = YoutubeDLCookieJar(str(path))
            jar.load()

            loaded = {cookie.name: cookie for cookie in jar}
            assert set(loaded) == {
                "session_cookie",
                "absent_expiry",
                "future_expiry",
                "past_expiry",
            }

            # The three live variants reach the consumer; the past one does not.
            sent = {cookie.name for cookie in jar.get_cookies_for_url(_URL)}
            assert sent == {"session_cookie", "absent_expiry", "future_expiry"}
        finally:
            path.unlink(missing_ok=True)

    def test_none_expiry_survives_round_trip(self) -> None:
        """D-02: an explicit ``expires: None`` is normalised and survives the real consumer."""
        # Same verified invocation as above: `load_cookies` calls `jar.load()`
        # with no arguments, so `ignore_discard=True, ignore_expires=True`; a
        # session cookie (`expires` 0, `discard` True) is therefore kept at load
        # time precisely because `ignore_discard=True`.
        cookies: list[Cookie] = [_cookie_with_null_expiry("null_expiry", "live-value")]

        path = _create_temp_cookie_file(cookies)
        try:
            jar = YoutubeDLCookieJar(str(path))
            jar.load()

            loaded = {cookie.name: cookie for cookie in jar}
            assert "null_expiry" in loaded
            assert loaded["null_expiry"].value == "live-value"
            assert loaded["null_expiry"].discard is True
            assert loaded["null_expiry"].expires is None
            assert "null_expiry" in {cookie.name for cookie in jar.get_cookies_for_url(_URL)}
        finally:
            path.unlink(missing_ok=True)

    def test_positive_timestamps_are_preserved(self) -> None:
        """D-02: normalisation rewrites only non-positive expiries, so real timestamps survive intact."""
        # Same verified invocation as above: `load_cookies` calls `jar.load()`
        # with no arguments, so `ignore_discard=True, ignore_expires=True` — the
        # past timestamp is dropped at use time by the cookie policy, not at
        # parse time. The far-future assertion is the load-time half: it proves
        # the normalisation did not collapse a real timestamp to 0.
        now = int(time.time())
        future = now + _TEN_YEARS_SECONDS
        cookies: list[Cookie] = [
            _cookie("far_future_expiry", "v", future),
            _cookie("past_expiry", "v", now - _TEN_YEARS_SECONDS),
        ]

        path = _create_temp_cookie_file(cookies)
        try:
            jar = YoutubeDLCookieJar(str(path))
            jar.load()

            loaded = {cookie.name: cookie for cookie in jar}
            # Written through unchanged: not the 0 sentinel, not the session form.
            assert loaded["far_future_expiry"].expires == future
            assert loaded["far_future_expiry"].discard is False

            sent = {cookie.name for cookie in jar.get_cookies_for_url(_URL)}
            assert "far_future_expiry" in sent
            assert "past_expiry" not in sent
        finally:
            path.unlink(missing_ok=True)

    def test_host_only_cookie_survives_consumer_round_trip(self) -> None:
        """SEC-009: a dotless-domain (host-only) cookie survives the real consumer.

        Before the fix, ``_cookies_to_netscape`` wrote the literal ``TRUE``
        into the ``include_subdomains`` column for every entry. The consumer
        (``MozillaCookieJar._really_load``) asserts
        ``domain_specified == initial_dot``; a host-only domain (no leading dot)
        makes ``initial_dot`` false while the column says ``TRUE``, so the
        assertion fires and the **entire file** is rejected — not just the
        offending entry.
        """
        cookies: list[Cookie] = [_cookie_with_domain("host_only", "live-value", "vkvideo.ru")]

        path = _create_temp_cookie_file(cookies)
        try:
            jar = YoutubeDLCookieJar(str(path))
            jar.load()

            loaded = {cookie.name: cookie for cookie in jar}
            assert "host_only" in loaded
            assert loaded["host_only"].value == "live-value"
        finally:
            path.unlink(missing_ok=True)

    def test_mixed_dotted_and_host_only_cookies_survive_consumer_round_trip(self) -> None:
        """SEC-009: a mixed file — dotted then host-only — survives with both cookies.

        This is the reproduction case for the whole-file loss: the dotless
        entry makes the consumer refuse the file outright, discarding the
        well-formed dotted entry that precedes it. A host-only-only test would
        not catch it because both entries are dotless; the mixed ordering is
        what proves the defect is all-or-nothing.
        """
        cookies: list[Cookie] = [
            _cookie_with_domain("dotted_cookie", "dotted-value", ".vkvideo.ru"),
            _cookie_with_domain("host_only_cookie", "host-only-value", "vkvideo.ru"),
        ]

        path = _create_temp_cookie_file(cookies)
        try:
            jar = YoutubeDLCookieJar(str(path))
            jar.load()

            loaded = {cookie.name: cookie for cookie in jar}
            assert "dotted_cookie" in loaded
            assert loaded["dotted_cookie"].value == "dotted-value"
            assert "host_only_cookie" in loaded
            assert loaded["host_only_cookie"].value == "host-only-value"
        finally:
            path.unlink(missing_ok=True)
