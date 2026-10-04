"""Tests for URL sanitization utilities.

The sanitizer redacts two product artefact shapes (the cookie-file artefact
``vk_cookies_<tail>.cookies.txt`` and the artefact directory
``vk_cookies__dir<tail>``) and signed ``https?://`` URLs (scheme+host only).
These tests lock the redaction claim at both the byte-identity boundary
(user data that *resembles* an artefact must not match) and the filesystem
boundary (real artefact paths created by the cookie lifecycle must match).
"""

from __future__ import annotations

import shutil
import string
import tempfile
from pathlib import Path

from vkdownloader.services.ytdlp_downloader import (
    _create_cookie_artifact_dir,
    _create_temp_cookie_file,
    _remove_cookie_artifact_dir,
)
from vkdownloader.utils.url_sanitizer import (
    _COOKIE_DIR_ARTEFACT_REGEX,
    _strip_auth_params,
    sanitize_text_for_log,
)

REDACTED = "***REDACTED***"


class TestStripAuthParams:
    """Tests for _strip_auth_params function."""

    def test_strips_url_with_query_params(self) -> None:
        """Test URL with query parameters is fully redacted."""
        url = "https://example.com/video.m3u8?token=abc123"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"
        assert "token" not in result
        assert "abc123" not in result

    def test_strips_url_with_multiple_query_params(self) -> None:
        """Test URL with multiple query parameters is fully redacted."""
        url = "https://example.com/video.m3u8?token=abc123&expire=3600&quality=720"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"
        assert "token" not in result
        assert "expire" not in result
        assert "quality" not in result
        assert "abc123" not in result

    def test_handles_url_without_query_params(self) -> None:
        """Test URL without query parameters still gets redacted."""
        url = "https://example.com/video.m3u8"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"

    def test_handles_empty_url(self) -> None:
        """Test empty URL returns redacted marker."""
        url = ""
        result = _strip_auth_params(url)

        assert result == "***REDACTED***"

    def test_strips_signed_cdn_url_with_path_token(self) -> None:
        """Test signed CDN URL with token in path is fully redacted."""
        url = "https://cdn.example.com/signature123/segment_0.ts?quality=720"
        result = _strip_auth_params(url)

        assert result == "https://cdn.example.com/***REDACTED***"
        assert "signature123" not in result
        assert "quality" not in result

    def test_strips_unknown_auth_params(self) -> None:
        """Test unknown auth parameters are redacted (allowlist strategy)."""
        url = "https://example.com/video.m3u8?siv=signed_value&extra=extra_value"
        result = _strip_auth_params(url)

        assert result == "https://example.com/***REDACTED***"
        assert "siv" not in result
        assert "signed_value" not in result

    def test_preserves_scheme_and_host(self) -> None:
        """Test that scheme and host are preserved."""
        url = "https://example.com/video.m3u8?token=secret"
        result = _strip_auth_params(url)

        assert "https://" in result
        assert "example.com" in result

    def test_handles_invalid_url(self) -> None:
        """Test that invalid URLs return redacted marker."""
        url = "not a valid url with ?query=params"
        result = _strip_auth_params(url)

        assert result == "***REDACTED***"


class TestSanitizeTextForLog:
    """Tests for sanitize_text_for_log function (SEC-002 subprocess output redaction)."""

    # ------------------------------------------------------------------
    # Legacy / capability-boundary tests (unchanged from the URL-only era).
    # ------------------------------------------------------------------

    def test_redacts_url_in_text(self) -> None:
        """Test that URLs in text are redacted to scheme://host only."""
        text = "Error: cannot fetch https://cdn.example.com/seg.m3u8?token=abc123&sig=def456"
        result = sanitize_text_for_log(text)

        assert "abc123" not in result
        assert "def456" not in result
        assert "cdn.example.com" in result
        assert "https://cdn.example.com" in result

    def test_redacts_multiple_urls_in_text(self) -> None:
        """Test that multiple URLs in text are all redacted."""
        text = "From https://a.example.com/x?tok=aaa to https://b.example.com/y?tok=bbb"
        result = sanitize_text_for_log(text)

        assert "aaa" not in result
        assert "bbb" not in result
        assert "a.example.com" in result
        assert "b.example.com" in result

    def test_preserves_text_without_urls(self) -> None:
        """Test that text without URLs is unchanged."""
        text = "Simple error message with no URLs here"
        result = sanitize_text_for_log(text)

        assert result == text

    def test_redacts_url_in_yt_dlp_output(self) -> None:
        """Test URL redaction in typical yt-dlp error output format."""
        text = (
            "[download] https://vkvideo.ru/video-123_456 "
            "[warning] error: failed to fetch https://cdn.vkhost.com/stream.m3u8?sig=xyz"
        )
        result = sanitize_text_for_log(text)

        assert "sig=xyz" not in result
        assert "stream.m3u8?sig=xyz" not in result
        assert "vkvideo.ru" in result  # Host preserved for debugging
        assert "cdn.vkhost.com" in result  # Host preserved for debugging

    def test_transform_before_truncate_proves_sanitize_order(self) -> None:
        """SEC-002: prove sanitize-then-truncate ordering (ffmpeg_utils pattern).

        ``ffmpeg_utils`` calls ``sanitize_text_for_log(error)[:200]``. When a
        signed URL starts past the 200-char boundary, truncating first would
        silently drop it (no host in the log); sanitizing first shrinks it to
        ``scheme://host/***REDACTED***`` so the host survives truncation.

        The ``len == 200`` assertion is the discriminator. The full input is
        226 chars (170 filler + a 56-char signed URL); sanitization replaces
        the URL with its 38-char redacted form, yielding 208 chars, and
        ``[:200]`` then truncates to exactly 200. Reversing the order to
        truncate-then-sanitize would feed ``error[:200]`` (170 filler + 30
        chars of the URL) to the transform; the partial URL is matched and
        replaced with the 38-char redaction, producing 208 chars with no
        truncation applied, so ``len`` would be 208 rather than 200. The
        assertion pins the mandatory sanitize-then-truncate sequence.
        """
        filler = "x" * 170
        signed_url = "https://cdn.example.com/seg.m3u8?token=SECRET123&sig=ABC"
        error = f"{filler}{signed_url}"

        result = sanitize_text_for_log(error)[:200]

        assert "cdn.example.com" in result
        assert "SECRET123" not in result
        assert "ABC" not in result
        assert len(result) == 200

    def test_redacts_signed_cdn_url_in_merge_failure_text(self) -> None:
        """Merge-failure stderr with a signed CDN URL must be fully redacted."""
        text = (
            "ffmpeg version 6.0 Copyright (c) 2023\n"
            "Error opening https://cdn.vkhost.com/segments/00000.ts"
            "?token=s3cr3t&sig=deadbeef as\n"
            "Input #0"
        )
        result = sanitize_text_for_log(text)

        assert "s3cr3t" not in result
        assert "deadbeef" not in result
        assert "cdn.vkhost.com" in result
        assert "https://cdn.vkhost.com" in result

    def test_preserves_plaintext_merge_failure_text(self) -> None:
        """Plaintext error messages without URLs pass through byte-identical."""
        text = "Error: invalid data found when processing input stream"
        result = sanitize_text_for_log(text)

        assert result == text

    # ------------------------------------------------------------------
    # Artefact-redaction tests (B4).
    # ------------------------------------------------------------------

    def test_redacts_cookie_file_artefact_backslash(self) -> None:
        """A backslash cookie-file artefact path collapses to one redaction."""
        text = r"C:\Temp\vk_cookies_q1w2e3r4.cookies.txt"

        assert sanitize_text_for_log(text) == REDACTED

    def test_redacts_cookie_file_artefact_forward_slash(self) -> None:
        """A forward-slash cookie-file artefact path collapses to one redaction."""
        text = r"C:/Temp/vk_cookies_q1w2e3r4.cookies.txt"

        assert sanitize_text_for_log(text) == REDACTED

    def test_dir_artefact_leaves_owner_pid_suffix(self) -> None:
        """The directory rule redacts the path but leaves ``owner.pid`` intact."""
        text = r"C:\Users\x\AppData\Local\Temp\vk_cookies__dir9lfm4h4w4\owner.pid"

        assert sanitize_text_for_log(text) == r"***REDACTED***\owner.pid"

    def test_url_host_survives_when_artefact_embedded_in_url(self) -> None:
        """URL-first ordering preserves the host even when an artefact is the path."""
        text = "GET https://cdn.example.com/proxy?p=C:/Users/x/Temp/vk_cookies_a.cookies.txt"

        assert sanitize_text_for_log(text) == "GET https://cdn.example.com/***REDACTED***"

    def test_glued_artefact_keeps_second_name_as_literal(self) -> None:
        """Two artefacts glued with no separator: only the first is redacted.

        When two artefact names are concatenated with no path separator
        between them, the second is deliberately left unredacted. That
        non-redaction is precisely what makes the rule a fixed point:
        ``***REDACTED***`` ends in ``*``, so a ``\\b``-guarded rule would
        manufacture a boundary on the second pass and consume the second name,
        breaking idempotency (measured 3 fixed-point violations in 400 000
        for ``\\b``, 0 for the chosen lookbehind). This is a deliberate
        accepted residual, not an oversight, and is unreachable from
        production.
        """
        text = r"C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txtvk_cookies_b.cookies.txt"
        once = sanitize_text_for_log(text)

        assert once == "***REDACTED***vk_cookies_b.cookies.txt"
        assert sanitize_text_for_log(once) == once

    def test_nested_file_inside_dir_yields_single_marker(self) -> None:
        """A file artefact inside a dir artefact collapses to one marker."""
        text = r"C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txt"

        assert sanitize_text_for_log(text) == REDACTED

    def test_preserves_surrounding_quotes_and_punctuation(self) -> None:
        """Quotes are preserved; ``(`` consumed as collateral.

        ``'`` and ``"`` are in ``[\\s'\"<>]`` — the left-boundary allowance
        set: characters whose presence before a match does NOT exclude it
        (the complement of the lookbehind's negated class) — so an artefact
        directly wrapped in quotes is matched and the quotes surround the
        marker. ``(`` is NOT in this set, so it is absorbed into the
        artefact's greedy path-prefix lead (accepted collateral, same class
        as ``key=path/...``) while the closing ``)`` survives.
        """
        parens = r"(\C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txt)"
        single = r"'C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txt'"
        double = r'"C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txt"'

        assert sanitize_text_for_log(parens) == f"{REDACTED})"
        assert sanitize_text_for_log(single) == f"'{REDACTED}'"
        assert sanitize_text_for_log(double) == f'"{REDACTED}"'

    def test_redacts_artefact_at_line_start_and_line_end(self) -> None:
        """Artefacts at the start and end of separate lines are both redacted."""
        text = (
            r"C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txt"
            "\nmiddle line preserved\n"
            r"C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txt"
        )

        assert sanitize_text_for_log(text) == f"{REDACTED}\nmiddle line preserved\n{REDACTED}"

    def test_benign_cookie_header_is_byte_identical(self) -> None:
        """A ``Cookie:`` HTTP header is NOT matched (D-5 / Alt A) — byte-identical."""
        text = "Cookie: a=b; c=d"

        assert sanitize_text_for_log(text) == text

    def test_unquoted_key_value_loses_key_as_collateral(self) -> None:
        """``key=path/...`` is consumed by the artefact's greedy lead (accepted collateral).

        The design originally asked for a case asserting the ``path=`` key
        survives alongside the value. That case is unimplementable as
        designed: the greedy lead consumes ``=`` because ``=`` is not
        whitespace, a quote, or ``<`` / ``>`` (the left-boundary allowance
        set) and is followed by a path separator, so
        ``path=C:\\...\\vk_cookies_x.cookies.txt`` collapses whole to
        ``***REDACTED***`` (measured), with no key left behind. The
        Implementor substituted this truthful collateral case instead. It is
        bounded: the three child-output sinks receive whitespace-delimited
        argv, never ``key=``; structlog dict values keep the key as
        ``"path": "***REDACTED***"``.
        """
        text = r"path=C:\Users\x\Temp\vk_cookies_x.cookies.txt"

        assert sanitize_text_for_log(text) == REDACTED

    def test_is_idempotent_with_existing_redaction_marker(self) -> None:
        """An artefact followed by an existing marker keeps the marker stable."""
        text = r"C:\Temp\vk_cookies__dirabc12345\vk_cookies_q1w2e3r4.cookies.txt -> ***REDACTED***"

        assert sanitize_text_for_log(text) == f"{REDACTED} -> {REDACTED}"

    def test_redaction_marker_literal_is_not_redacted(self) -> None:
        """The literal marker matches no rule — stays unchanged (idempotency base case)."""
        assert sanitize_text_for_log(REDACTED) == REDACTED

    def test_glued_artefact_without_separator_not_matched(self) -> None:
        """An artefact glued to other text without a separator is not matched."""
        text = "foovk_cookies_a.cookies.txt"

        assert sanitize_text_for_log(text) == text

    # ------------------------------------------------------------------
    # Negative tests: user data that *resembles* the artefact prefix.
    # ------------------------------------------------------------------

    def test_filesystem_paths_are_not_redacted(self) -> None:
        """User-chosen paths resembling the artefact prefix stay byte-identical.

        A user folder named ``vk_cookies_videos`` or ``vk_cookies__downloads``
        looks like it could be an artefact, but ``_COOKIE_DIR_ARTEFACT_REGEX``
        requires the literal ``vk_cookies__dir`` stem, so these are NOT matched
        and pass through unchanged. This pins the negative boundary so the
        redaction claim cannot silently widen to real user data.
        """
        signed_url = "https://cdn.example.com/seg.m3u8?token=abc123&sig=def456"
        clip_videos = "C:/Users/x/Videos/vk_cookies_videos/clip.mp4"
        clip_downloads = r"C:\Users\x\Downloads\vk_cookies__downloads\clip.mp4"
        text = f"videos={clip_videos} - downloads={clip_downloads} - fetch={signed_url}"
        result = sanitize_text_for_log(text)

        assert "https://cdn.example.com" in result
        assert "abc123" not in result
        assert "def456" not in result
        assert clip_videos in result
        assert clip_downloads in result


class TestArtefactAlphabetOracle:
    """Filesystem-grounded tests: real artefact paths must be redacted.

    These cases create real artefact paths via the cookie lifecycle helpers
    (which use :mod:`tempfile`) and assert the sanitizer redacts them -- the
    counterpart to the byte-identity boundary tests above.
    """

    def test_real_artefact_dir_is_redacted(self) -> None:
        """A directory created by ``_create_cookie_artifact_dir`` is redacted."""
        cookie_dir = _create_cookie_artifact_dir()
        try:
            assert sanitize_text_for_log(str(cookie_dir)) == REDACTED
        finally:
            _remove_cookie_artifact_dir(cookie_dir)

    def test_real_artefact_file_is_redacted(self) -> None:
        """A cookie file created by ``_create_temp_cookie_file`` is redacted."""
        cookie_file = _create_temp_cookie_file("session=test")
        try:
            assert sanitize_text_for_log(str(cookie_file)) == REDACTED
        finally:
            cookie_file.unlink(missing_ok=True)
            _remove_cookie_artifact_dir(cookie_file.parent)

    def test_similarly_shaped_non_artefact_is_byte_identical(self) -> None:
        """A ``vk_cookies_temp*`` temp dir is NOT an artefact -- byte-identical."""
        non_artefact = Path(tempfile.mkdtemp(prefix="vk_cookies_temp"))
        try:
            assert sanitize_text_for_log(str(non_artefact)) == str(non_artefact)
        finally:
            shutil.rmtree(non_artefact, ignore_errors=True)

    def test_artefact_tail_alphabet_is_subset_of_regex_charset(self) -> None:
        """``tempfile`` tails use only ``[a-z0-9_]`` -- the regex accepts them all."""
        cookie_dir = _create_cookie_artifact_dir()
        try:
            tail = cookie_dir.name[len("vk_cookies__dir") :]
            assert set(tail) <= set(string.ascii_lowercase + string.digits + "_")
            match = _COOKIE_DIR_ARTEFACT_REGEX.search(str(cookie_dir))
            assert match is not None
            assert match.group(0).endswith(cookie_dir.name)
        finally:
            _remove_cookie_artifact_dir(cookie_dir)
