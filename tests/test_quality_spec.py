"""Tests for the QualitySpec model: parsing, matching, and rendering."""

import subprocess
import sys

import pytest

from vkdownloader.exceptions import QualityParseError
from vkdownloader.models.enums import QualityKind
from vkdownloader.models.quality import QualitySpec


class TestParse:
    """Parsing of user-supplied quality tokens."""

    @pytest.mark.parametrize(
        ("token", "kind", "label"),
        [
            ("best", QualityKind.BEST, None),
            ("BEST", QualityKind.BEST, None),
            ("worst", QualityKind.WORST, None),
            ("unknown", QualityKind.EXACT, "unknown"),
            ("1072", QualityKind.EXACT, "1072p"),
            ("1072p", QualityKind.EXACT, "1072p"),
            ("1072P", QualityKind.EXACT, "1072p"),
            (" 720 ", QualityKind.EXACT, "720p"),
        ],
    )
    def test_accepted_tokens(self, token: str, kind: QualityKind, label: str | None) -> None:
        """Keywords and any positive height (with optional p) are accepted."""
        spec = QualitySpec.parse(token)

        assert spec.kind is kind
        assert spec.label == label

    def test_empty_token_defaults_to_best(self) -> None:
        """An empty token falls back to the CLI default rather than failing."""
        assert QualitySpec.parse("").kind is QualityKind.BEST
        assert QualitySpec.parse("   ").kind is QualityKind.BEST

    @pytest.mark.parametrize(
        "token",
        ["0", "00", "-5", "abc", "hight", "1080x", "bestt", "p", "²"],
    )
    def test_rejected_tokens(self, token: str) -> None:
        """Anything that is not a keyword or a positive height is rejected.

        ``²`` (superscript two) is a digit to ``str.isdigit`` but not to
        ``int``; it must surface as QualityParseError rather than as a bare
        ValueError, because the CLI renders QualityParseError as a usage error
        with exit code 2.
        """
        with pytest.raises(QualityParseError) as exc_info:
            QualitySpec.parse(token)

        assert exc_info.value.quality == token
        assert exc_info.value.status_label() == "invalid_quality"

    def test_non_ascii_decimal_digit_normalises_to_its_height(self) -> None:
        """A decimal digit ``int()`` accepts is a height, rendered in ASCII.

        ``isdecimal`` (not ``isdigit``) is the acceptance predicate: ``٣`` is a
        decimal digit that ``int()`` reads as 3, so it selects the 3p stream
        and renders as ``3p`` — while ``²`` is rejected outright.
        """
        spec = QualitySpec.parse("٣")

        assert spec.label == "3p"
        assert str(spec) == "3"


def test_importing_exceptions_first_does_not_cycle() -> None:
    """`vkdownloader.exceptions` must be importable on its own.

    ``exceptions`` imports ``vkdownloader.models.enums``, whose package
    ``__init__`` re-exports QualitySpec, so a module-level import of
    ``exceptions`` from ``models/quality.py`` would close the cycle and break
    ``import vkdownloader.exceptions`` as the first import of the process. An
    in-process import cannot observe this (the test session already imported
    the package), so a fresh interpreter is used.
    """
    result = subprocess.run(
        [sys.executable, "-c", "import vkdownloader.exceptions"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


class TestMatches:
    """Label matching for exact requests."""

    def test_matches_p_suffixed_label(self) -> None:
        """A height request matches the label the extractor writes."""
        assert QualitySpec.parse("1072").matches("1072p") is True

    def test_matches_numeric_label(self) -> None:
        """A height request also matches a label without the p suffix."""
        assert QualitySpec.parse("1072").matches("1072") is True

    def test_does_not_match_other_height(self) -> None:
        """A height request does not match a different height."""
        assert QualitySpec.parse("1072").matches("1610p") is False

    def test_keyword_requests_never_match_a_label(self) -> None:
        """best/worst are ranking requests, not label matches."""
        assert QualitySpec.parse("best").matches("best") is False
        assert QualitySpec.parse("best").matches("1610p") is False
        assert QualitySpec.parse("worst").matches("worst") is False

    def test_unknown_request_matches_only_the_unknown_label(self) -> None:
        """The unknown request matches the browser-capture label only."""
        spec = QualitySpec.parse("unknown")

        assert spec.matches("unknown") is True
        assert spec.matches("1072p") is False


class TestRendering:
    """Rendering of a spec back into the token the CLI accepts."""

    @pytest.mark.parametrize(
        ("token", "expected"),
        [
            ("best", "best"),
            ("worst", "worst"),
            ("unknown", "unknown"),
            ("1072", "1072"),
            ("1072p", "1072"),
        ],
    )
    def test_str_is_the_accepted_token(self, token: str, expected: str) -> None:
        """str() yields a token the CLI and the yt-dlp selector both accept."""
        assert str(QualitySpec.parse(token)) == expected


class TestValidation:
    """Structural invariants of the model."""

    def test_exact_requires_a_label(self) -> None:
        """An exact request without a label is not a valid state."""
        with pytest.raises(ValueError, match="EXACT requires"):
            QualitySpec(kind=QualityKind.EXACT)

    def test_exact_rejects_an_empty_label(self) -> None:
        """An exact request with a blank label is not a valid state."""
        with pytest.raises(ValueError, match="EXACT requires"):
            QualitySpec(kind=QualityKind.EXACT, label="")

    def test_keywords_must_not_carry_a_label(self) -> None:
        """A keyword request with a label is not a valid state."""
        with pytest.raises(ValueError, match="must not carry a label"):
            QualitySpec(kind=QualityKind.BEST, label="1072p")

    def test_spec_is_frozen(self) -> None:
        """A spec is immutable, so a request cannot be mutated downstream."""
        spec = QualitySpec.parse("1072")

        with pytest.raises(ValueError):
            spec.label = "1610p"  # type: ignore[misc]
