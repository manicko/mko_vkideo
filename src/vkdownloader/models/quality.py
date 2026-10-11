"""Quality specification model for VK Video Downloader.

Provides a typed representation of a user-requested video quality that supports
both keyword selection (``best`` / ``worst``) and exact stream-label matching.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from .enums import QualityKind, QualityLabel

# Import-form taxonomy (QLT-012). No project-wide convention document exists —
# confirmed by searching .kilo/rules/, .ai/context/, docs/STRUCT.md (see
# .ai/audit/99-validation/09-code-quality-validated-findings.md:554).
#
# Measured census of 26 non-__init__ modules:
#   15 relative-only   (from . / from ..)
#    3 absolute-only   (from vkdownloader.…)
#    7 neither         (stdlib / third-party only)
#    1 both            (this module — relative module-level + lazy absolute)
#
# This is the only module using both forms. The absolute lazy import below is
# load-bearing: it breaks a cycle that the package __init__ does not (the
# models package __init__ is empty, so an eager absolute import here would not
# trigger a partial-init failure today, but it would close the edge
# quality → exceptions → utils.security → models.video → models.quality the
# moment any future change re-opens the utils.security → exceptions edge).


class QualitySpec(BaseModel):
    """A validated quality request: a keyword or one exact stream label.

    VK height ladders are not the 240/360/720/1080 series assumed by older
    versions of this tool (a single video may offer 106p through 1610p), so a
    request cannot be modelled as a closed enum of resolutions. ``QualitySpec``
    carries either a selection keyword (``best`` / ``worst``) or the exact
    quality label of a single stream (``1072p``, or ``unknown`` for a
    browser-captured HLS stream with no height).

    Attributes:
        kind: How the request is resolved against the available streams.
        label: Quality label matched exactly; set only for ``QualityKind.EXACT``.
    """

    model_config = ConfigDict(frozen=True)

    kind: QualityKind
    label: str | None = None

    @model_validator(mode="after")
    def _validate_label(self) -> Self:
        """Require a label for exact matches and forbid one otherwise."""
        if self.kind is QualityKind.EXACT and not self.label:
            raise ValueError("QualityKind.EXACT requires a non-empty label")
        if self.kind is not QualityKind.EXACT and self.label:
            raise ValueError(f"QualityKind.{self.kind.value} must not carry a label")
        return self

    @classmethod
    def parse(cls, raw: str) -> QualitySpec:
        """Parse a user-supplied quality token into a specification.

        Accepted input: the keywords ``best``, ``worst`` and ``unknown``, or
        any positive height in pixels (with an optional trailing ``p``, so
        both ``1072`` and ``1072p`` select the 1072p stream). An empty value
        falls back to ``best``, matching the CLI default.

        Args:
            raw: Raw quality token from the command line or a caller.

        Returns:
            The parsed specification.

        Raises:
            QualityParseError: If the token is not a keyword nor a positive height.
        """
        # QLT-012: deferred to runtime to break an import cycle.
        # An eager module-level import would close
        # models.quality → exceptions → utils.security → models.video → models,
        # because utils.security imports both exceptions.DownloadError and
        # models.video.VideoWithStreams. The cycle is dormant today (exceptions
        # imports url_sanitizer, a leaf, not utils.security), but this lazy form
        # is a defensive barrier: moving it to module scope would reintroduce
        # the ImportError the moment any cycle edge is re-added. The import is
        # absolute rather than relative to make the cross-layer boundary
        # (models → exceptions) explicit — the package __init__ does not
        # re-export subpackage contents, so a relative form would hide the
        # layer crossing. See config.py:621 (B6 RF-1) for the parallel case.
        from vkdownloader.exceptions import QualityParseError

        if raw is None or raw.strip() == "":
            return cls(kind=QualityKind.BEST)

        token = raw.strip()
        normalized = token.lower()

        if normalized == "best":
            return cls(kind=QualityKind.BEST)
        if normalized == "worst":
            return cls(kind=QualityKind.WORST)
        if normalized == "unknown":
            return cls(kind=QualityKind.EXACT, label=QualityLabel.UNKNOWN.value)

        # Accept a positive height with an optional trailing p/P (case-insensitive).
        height = token[:-1] if token[-1] in ("p", "P") else token
        if height.isdecimal() and int(height) > 0:
            return cls(kind=QualityKind.EXACT, label=f"{int(height)}p")

        raise QualityParseError(token)

    def matches(self, stream_label: str) -> bool:
        """Report whether a stream quality label satisfies this request.

        Args:
            stream_label: Quality label of a stream (e.g. ``"1072p"``).

        Returns:
            True for an exact request whose label equals ``stream_label``
            (numeric form without the ``p`` suffix is accepted too). Keyword
            requests (``best`` / ``worst``) never match a single label.
        """
        if self.kind is not QualityKind.EXACT:
            return False
        if self.label is None:
            return False
        # Accept both "1072p" and "1072" as matching forms.
        return stream_label == self.label or (
            stream_label.removesuffix("p") == self.label.removesuffix("p")
        )

    def __str__(self) -> str:
        """Return the canonical token for this request.

        The result is the value the CLI accepts and the string handed to the
        yt-dlp format selector, so a height is rendered digit-only (``"1072"``).
        """
        if self.kind is QualityKind.EXACT:
            return self.label.removesuffix("p") if self.label else ""
        return self.kind.value
