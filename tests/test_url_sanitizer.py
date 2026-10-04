"""Tests for URL sanitization utilities.

The sanitizer redacts two product artefact shapes (the cookie-file artefact
``vk_cookies_<tail>.cookies.txt`` and the artefact directory
``vk_cookies__dir<tail>``) and signed ``https?://`` URLs (scheme+host only).
These tests lock the redaction claim at both the byte-identity boundary
(user data that *resembles* an artefact must not match) and the filesystem
boundary (real artefact paths created by the cookie lifecycle must match).
"""

from __future__ import annotations

import inspect
import io
import json
import logging
import shutil
import string
import tempfile
from pathlib import Path
from typing import Any

import structlog

from vkdownloader.config import setup_logging
from vkdownloader.services.ytdlp_downloader import (
    _create_cookie_artifact_dir,
    _create_temp_cookie_file,
    _remove_cookie_artifact_dir,
)
from vkdownloader.utils.url_sanitizer import (
    _COOKIE_DIR_ARTEFACT_REGEX,
    _STRUCTURAL_KEYS,
    _strip_auth_params,
    redact_log_event,
    sanitize_text_for_log,
)

REDACTED = "***REDACTED***"
_TEST_LOGGER = logging.getLogger("test.redact")


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


class TestRedactLogEventProcessor:
    """Tests for the ``redact_log_event`` structlog processor (B6).

    Covers the acceptance criteria from plan 17 §B6:
    - exc_info=True traceback redaction through the configured chain
    - cookie_file_cleanup_failed (both fields) and cookie_file_cleaned_up (path)
    - processor chain position (after format_exc_info, after UnicodeDecoder,
      before renderer)
    - event-name-agnosticism
    - idempotency (processor output is a fixed point)
    - never-raises on non-string, None, nested mapping, absent key
    """

    SIGNED_URL = "https://cdn.example.com/seg.m3u8?token=SECRET123&sig=ABC"

    # ------------------------------------------------------------------
    # AC-1: exc_info=True record's rendered traceback is redacted
    # ------------------------------------------------------------------

    def test_exc_info_traceback_is_redacted_through_chain(self) -> None:
        """An exc_info=True record carrying a signed URL in the exception message
        is redacted in the rendered ``exception`` field.
        """
        structlog.reset_defaults()
        buf = io.StringIO()
        root = logging.getLogger()
        old_handlers = root.handlers[:]
        root.handlers.clear()
        root.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.handlers.append(handler)
        try:
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso", utc=True),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    redact_log_event,
                    structlog.processors.JSONRenderer(),
                ],
                wrapper_class=structlog.stdlib.BoundLogger,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=False,
            )
            logger = structlog.get_logger("test.exc_info")

            url = self.SIGNED_URL
            try:
                raise ValueError(f"fetch failed: {url}")
            except ValueError:
                logger.error("download failed", exc_info=True)

            output = buf.getvalue().strip()
        finally:
            root.handlers.clear()
            root.handlers.extend(old_handlers)

        parsed = json.loads(output)
        assert "exception" in parsed
        assert "Traceback" in parsed["exception"]
        assert "SECRET123" not in parsed["exception"]
        assert "ABC" not in parsed["exception"]
        assert "cdn.example.com" in parsed["exception"]

    # ------------------------------------------------------------------
    # AC-3: cookie_file_cleanup_failed + cookie_file_cleaned_up
    # ------------------------------------------------------------------

    def test_cookie_file_cleanup_failed_both_fields_redacted(self) -> None:
        """``cookie_file_cleanup_failed`` carries ``path`` and ``error``, both
        bearing artefact tokens — both must be redacted.
        """
        cookie_file = _create_temp_cookie_file("session=test")
        try:
            cleanup_error = f"PermissionError: cannot delete {cookie_file}"
            event_dict = {
                "event": "cookie_file_cleanup_failed",
                "path": str(cookie_file),
                "error": cleanup_error,
            }
            result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

            assert result["path"] == REDACTED
            assert "Cannot delete" not in result["error"] or cookie_file.name not in result["error"]
            # Both values must lose the artefact token
            assert cookie_file.name not in result["path"]
            assert cookie_file.name not in result["error"]
        finally:
            cookie_file.unlink(missing_ok=True)
            _remove_cookie_artifact_dir(cookie_file.parent)

    def test_cookie_file_cleaned_up_path_is_redacted(self) -> None:
        """``cookie_file_cleaned_up`` carries ``path=str(cookie_file)`` at DEBUG —
        the artefact path must be redacted.
        """
        cookie_file = _create_temp_cookie_file("session=test")
        try:
            event_dict = {
                "event": "cookie_file_cleaned_up",
                "path": str(cookie_file),
            }
            result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

            assert result["path"] == REDACTED
        finally:
            cookie_file.unlink(missing_ok=True)
            _remove_cookie_artifact_dir(cookie_file.parent)

    # ------------------------------------------------------------------
    # AC-4: chain position
    # ------------------------------------------------------------------

    def test_processor_positioned_after_format_exc_info_and_unicode_decoder(
        self,
    ) -> None:
        """The processor sits after ``format_exc_info`` and ``UnicodeDecoder``,
        and before the renderer.
        """
        from structlog.dev import ConsoleRenderer
        from structlog.processors import (
            ExceptionRenderer,
            JSONRenderer,
            UnicodeDecoder,
        )

        setup_logging()
        processors = structlog.get_config()["processors"]

        processor_idx = None
        format_exc_idx = None
        unicode_idx = None
        renderer_idx = None
        for i, proc in enumerate(processors):
            if proc is redact_log_event:
                processor_idx = i
            if isinstance(proc, ExceptionRenderer):
                format_exc_idx = i
            if isinstance(proc, UnicodeDecoder):
                unicode_idx = i
            if isinstance(proc, (JSONRenderer, ConsoleRenderer)):
                renderer_idx = i

        assert processor_idx is not None, "redact_log_event not found in processors"
        assert format_exc_idx is not None
        assert unicode_idx is not None
        assert renderer_idx is not None

        assert processor_idx > format_exc_idx, (
            "redact_log_event must be after format_exc_info (ExceptionRenderer)"
        )
        assert processor_idx > unicode_idx, (
            "redact_log_event must be after UnicodeDecoder (values must be str)"
        )
        assert processor_idx < renderer_idx, "redact_log_event must be before the renderer"

    # ------------------------------------------------------------------
    # AC-5: event-name-agnosticism
    # ------------------------------------------------------------------

    def test_same_value_under_different_names_produces_identical_output(
        self,
    ) -> None:
        """Two records with different ``event`` names but the same secret-bearing
        value produce identical redaction.
        """
        url = self.SIGNED_URL
        event_dict_a = {"event": "record_a", "detail": url}
        event_dict_b = {"event": "record_b", "detail": url}

        result_a = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict_a))
        result_b = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict_b))

        assert result_a["detail"] == result_b["detail"]
        assert "SECRET123" not in result_a["detail"]
        assert "ABC" not in result_a["detail"]
        assert "cdn.example.com" in result_a["detail"]

    def test_synthetic_novel_key_is_redacted(self) -> None:
        """A key name not present in any of the 22 enumerated records still gets
        redacted — the processor is key-agnostic, not allowlist-driven.
        """
        event_dict = {
            "event": "novel_record",
            "custom_payload_key": self.SIGNED_URL,
        }
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert "SECRET123" not in result["custom_payload_key"]
        assert "cdn.example.com" in result["custom_payload_key"]

    def test_processor_source_contains_no_enumerated_record_names(self) -> None:
        """The processor source/bytecode mentions none of the 22 enumerated
        record names — the function is structural, not name-branched.
        """
        from vkdownloader.utils.url_sanitizer import redact_log_event as proc_module

        module_source = inspect.getsource(proc_module)
        # The enumerated record names from the 22-name census
        record_names = [
            "browser_launch_failed",
            "browser_close_failed",
            "playwright_stop_failed",
            "video_player_click_failed",
            "ytdlp_not_found",
            "download_failed",
            "batch_download_failed",
            "unexpected_error_in_batch_download",
            "cookie_file_cleanup_failed",
            "cookie_file_cleaned_up",
            "env_file_resolved",
            "output_path_inside_repository",
            "failed_to_cleanup_partial_file",
            "download_interrupted_switching_to_segments",
            "starting_download",
            "starting_ytdlp_download",
            "starting_segment_download",
            "merge_completed",
            "ytdlp_download_completed",
            "primary_error",
            "retryable_transport_error",
        ]
        for name in record_names:
            assert name not in module_source, (
                f"record name {name!r} found in processor source — "
                "processor must be event-name-agnostic"
            )

    # ------------------------------------------------------------------
    # AC-6: idempotency (processor output is a fixed point)
    # ------------------------------------------------------------------

    def test_processor_output_is_fixed_point(self) -> None:
        """S(S(x)) == S(x): running the processor on its own output is a no-op.

        This is the corrected idempotency claim (B6-R10). The pre-sanitised
        call-site values (``batch_merge_failed``, ``final_merge_failed``) are
        already-fixed-point inputs; the processor must not expand them.
        """
        pre_sanitised = sanitize_text_for_log(
            f"filler {self.SIGNED_URL} more filler {self.SIGNED_URL}"
        )
        event_dict = {"event": "batch_merge_failed", "error": pre_sanitised}
        once = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))
        twice = redact_log_event(_TEST_LOGGER, "debug", dict(once))

        assert once["error"] == twice["error"], "processor output must be a fixed point"
        assert "SECRET123" not in once["error"]

    def test_pre_sanitised_url_value_comes_out_unchanged(self) -> None:
        """A value already reduced by sanitize_text_for_log survives the
        processor unchanged (the B4-R7 fixed-point fixture).
        """
        pre = sanitize_text_for_log(self.SIGNED_URL)
        event_dict = {"event": "download_failed", "url": pre}
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert result["url"] == pre
        assert result["url"] == "https://cdn.example.com/***REDACTED***"

    # ------------------------------------------------------------------
    # AC-8: never raises on non-string, None, nested mapping, absent key
    # ------------------------------------------------------------------

    def test_none_value_passes_through(self) -> None:
        """A ``None`` value (real input: ``ytdlp_not_found``'s ``path=exc.filename``)
        is passed through unchanged without raising.
        """
        event_dict: dict[str, Any] = {"event": "ytdlp_not_found", "path": None}
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert result["path"] is None

    def test_non_string_value_passes_through(self) -> None:
        """int, bool, float values pass through unchanged without raising."""
        event_dict: dict[str, Any] = {
            "event": "segment_done",
            "bytes": 1024,
            "success": True,
            "ratio": 0.75,
        }
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert result["bytes"] == 1024
        assert result["success"] is True
        assert result["ratio"] == 0.75

    def test_empty_event_dict_passes_through(self) -> None:
        """An event dict with no values (only ``event``) renders without raising."""
        event_dict = {"event": "bare_event"}
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert result == {"event": "bare_event"}

    def test_bytes_value_passes_through(self) -> None:
        """A ``bytes`` value (pre-UnicodeDecoder) passes through unchanged.
        After UnicodeDecoder runs, the same processor would see a ``str`` and
        redact — but the processor itself never raises on ``bytes``.
        """
        event_dict = {"event": "raw_blob", "blob": b"https://cdn.example.com/x?token=SECRET"}
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert result["blob"] == b"https://cdn.example.com/x?token=SECRET"

    def test_list_values_are_depth1_sanitised(self) -> None:
        """A ``list`` value has its string elements redacted via depth-1 recursion,
        but nested non-strings (int, None) pass through, and the original list is
        not mutated in place (structlog's shallow copy would otherwise share it).
        """
        event_dict: dict[str, Any] = {
            "event": "captured_m3u8_urls",
            "urls": [self.SIGNED_URL, "https://b.example.com/y", None, 4096],
        }
        original_list = event_dict["urls"]
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        # Each string element redacted; non-strings preserved
        assert "SECRET123" not in result["urls"][0]
        assert "cdn.example.com" in result["urls"][0]
        assert result["urls"][1] == "https://b.example.com/***REDACTED***"
        assert result["urls"][2] is None
        assert result["urls"][3] == 4096

        # Original list unchanged (no in-place mutation)
        assert original_list[0] == self.SIGNED_URL
        assert "SECRET123" in original_list[0]

    def test_tuple_values_are_depth1_sanitised_and_return_tuple(self) -> None:
        """A ``tuple`` value is sanitised depth-1 and returned as a tuple."""
        event_dict: dict[str, Any] = {
            "event": "some_event",
            "paths": (self.SIGNED_URL, "plain text"),
        }
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert isinstance(result["paths"], tuple)
        assert "SECRET123" not in result["paths"][0]
        assert result["paths"][1] == "plain text"

    def test_dict_values_are_depth1_sanitised_keys_preserved(self) -> None:
        """A ``dict`` value has its string VALUES redacted depth-1, but its KEYS
        are preserved byte-identical (they are data, not structlog's structural
        keys), and the original dict is not mutated in place.
        """
        event_dict: dict[str, Any] = {
            "event": "some_event",
            "metadata": {
                "url_key": self.SIGNED_URL,
                "count": 42,
            },
        }
        original_dict = event_dict["metadata"]
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert "SECRET123" not in result["metadata"]["url_key"]
        assert "cdn.example.com" in result["metadata"]["url_key"]
        assert result["metadata"]["count"] == 42

        # Keys preserved byte-identical
        assert set(result["metadata"].keys()) == {"url_key", "count"}

        # Original dict unchanged (no in-place mutation)
        assert original_dict["url_key"] == self.SIGNED_URL
        assert "SECRET123" in original_dict["url_key"]

    def test_captured_m3u8_urls_record_through_configured_chain(self) -> None:
        """The live ``captured_m3u8_urls`` record carries ``urls=[...]`` — a list of
        signed CDN URLs. Through the fully configured chain, each is redacted,
        and the original list object is not mutated in place.
        """
        structlog.reset_defaults()
        buf = io.StringIO()
        root = logging.getLogger()
        old_handlers = root.handlers[:]
        root.handlers.clear()
        root.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(buf)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.handlers.append(handler)
        try:
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="iso", utc=True),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    redact_log_event,
                    structlog.processors.JSONRenderer(),
                ],
                wrapper_class=structlog.stdlib.BoundLogger,
                logger_factory=structlog.stdlib.LoggerFactory(),
                cache_logger_on_first_use=False,
            )
            logger = structlog.get_logger("test.m3u8")

            url_list = [self.SIGNED_URL, "https://b.example.com/alt.m3u8?sig=BBB"]
            logger.info("captured_m3u8_urls", urls=url_list)

            output = buf.getvalue().strip()
        finally:
            root.handlers.clear()
            root.handlers.extend(old_handlers)

        parsed = json.loads(output)
        urls = parsed["urls"]

        assert "SECRET123" not in urls[0]
        assert "ABC" not in urls[0]
        assert "cdn.example.com" in urls[0]
        assert "BBB" not in urls[1]
        assert "b.example.com" in urls[1]

        # Original list object must remain unchanged (no in-place mutation)
        assert url_list[0] == self.SIGNED_URL
        assert "SECRET123" in url_list[0]


class TestStructuralKeysDenylist:
    """Verify the structural-key denylist matches the measured injected set."""

    def test_denylist_contains_four_structural_keys(self) -> None:
        """The denylist is exactly {event, level, timestamp, correlation_id}."""
        assert _STRUCTURAL_KEYS == frozenset({"event", "level", "timestamp", "correlation_id"})

    def test_structural_keys_are_not_redacted(self) -> None:
        """Values under structural keys are never redacted, even if they
        contain a URL or artefact token.
        """
        event_dict: dict[str, Any] = {
            "event": "https://cdn.example.com/x?token=SECRET",
            "level": "https://cdn.example.com/y?token=SECRET2",
            "timestamp": "https://cdn.example.com/z?token=SECRET3",
            "correlation_id": "https://cdn.example.com/w?token=SECRET4",
        }
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert result["event"] == event_dict["event"]
        assert result["level"] == event_dict["level"]
        assert result["timestamp"] == event_dict["timestamp"]
        assert result["correlation_id"] == event_dict["correlation_id"]


class TestRedactLogEventDirect:
    """Direct unit tests of the ``redact_log_event`` processor without the
    configured chain.
    """

    def test_redacts_url_value(self) -> None:
        """A URL in any string value is redacted to scheme://host.***REDACTED***."""
        event_dict: dict[str, Any] = {
            "event": "some_event",
            "url": "https://cdn.example.com/seg.m3u8?token=SECRET",
        }
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert "SECRET" not in result["url"]
        assert "cdn.example.com" in result["url"]

    def test_redacts_artefact_path_in_value(self) -> None:
        """An artefact path in any string value is redacted."""
        cookie_file = _create_temp_cookie_file("session=test")
        try:
            event_dict: dict[str, Any] = {
                "event": "some_event",
                "path": str(cookie_file),
            }
            result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

            assert result["path"] == REDACTED
        finally:
            cookie_file.unlink(missing_ok=True)
            _remove_cookie_artifact_dir(cookie_file.parent)

    def test_redacts_multiple_string_values(self) -> None:
        """Every string value in the dict is independently redacted."""
        event_dict: dict[str, Any] = {
            "event": "multi_field",
            "url_a": "https://a.example.com/x?tok=AAA",
            "url_b": "https://b.example.com/y?tok=BBB",
            "message": "fetch https://c.example.com/z?tok=CCC failed",
        }
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert "AAA" not in result["url_a"]
        assert "BBB" not in result["url_b"]
        assert "CCC" not in result["message"]
        assert "a.example.com" in result["url_a"]
        assert "b.example.com" in result["url_b"]
        assert "c.example.com" in result["message"]

    def test_preserves_event_key(self) -> None:
        """The ``event`` key value is never redacted."""
        event_dict = {"event": "my_log_event_name"}
        result = redact_log_event(_TEST_LOGGER, "debug", dict(event_dict))

        assert result["event"] == "my_log_event_name"
