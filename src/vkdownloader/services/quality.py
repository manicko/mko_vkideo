"""Quality selection service for choosing appropriate video streams."""

from structlog import get_logger

from ..exceptions import QualityNotAvailableError
from ..models.enums import QualityKind
from ..models.quality import QualitySpec
from ..models.video import Stream

logger = get_logger(__name__)


class QualitySelector:
    """Selects appropriate stream from available streams based on quality preference."""

    def _find_quality_match(self, streams: list[Stream], quality: QualitySpec) -> Stream | None:
        """
        Find a stream whose quality label satisfies the requested quality.

        The match is delegated to :meth:`QualitySpec.matches`, which accepts
        both the ``720`` and ``720p`` spellings and accepts any height the
        video happens to offer (not only a fixed set of resolutions).

        Args:
            streams: List of available streams to search.
            quality: Parsed quality request to match.

        Returns:
            Matching Stream object, or None if not found.
        """
        for stream in streams:
            if quality.matches(stream.quality):
                logger.debug("selected_matching_quality", quality=stream.quality)
                return stream
        return None

    def _rank_key(self, indexed: tuple[int, Stream]) -> tuple[bool, int, int]:
        """Rank key shared by both the BEST and WORST arms (NET-017).

        ``carries_a_usable_height`` is True only for a strictly positive height;
        ``height <= 0`` (the placeholder) is treated as absent so it can no
        longer be confused with a genuinely missing ``None``. This rule is
        written here in the ranker and separately in ``_build_streams`` (the
        label): the duplication is deliberate, because ``extractor.py`` may not
        import this module (the "0 is absent" contract must hold in both places
        to keep the two parse sites from drifting). The ``input_position`` from
        ``enumerate`` makes the order total: without it a ``{0, None}`` pair
        yields two equal keys and both directions return the first record.
        """
        index, stream = indexed
        height = stream.height
        # NET-017: height <= 0 is treated as absent so a placeholder zero
        # cannot be confused with a missing None.
        if height is not None and height > 0:
            return (True, height, index)
        return (False, 0, index)

    def _get_fallback_stream(self, streams: list[Stream]) -> Stream:
        """
        Get the best quality stream as fallback.

        Streams that carry a usable (positive) height rank above those that do
        not. The position tiebreaker from ``_rank_key`` makes the order total, so
        a placeholder ``0`` and an absent ``None`` within the same set are never
        selected by both arms — they resolve to different streams by input
        position.

        Args:
            streams: List of available streams.

        Returns:
            Stream with the highest usable height (or the last stream in input
            order when none carry a usable height).
        """
        # NET-017: shared rank key — see _rank_key. max picks the highest usable
        # height; ties fall to the highest input_position, never both arms alike.
        return max(enumerate(streams), key=self._rank_key)[1]

    def select(self, streams: list[Stream], quality: QualitySpec) -> Stream:
        """
        Select a stream based on quality preference.

        Args:
            streams: List of available streams to choose from.
            quality: Parsed quality request (a keyword or an exact height).

        Returns:
            Selected Stream object.

        Raises:
            QualityNotAvailableError: If the streams list is empty or the
                requested quality is not available.
        """
        if not streams:
            raise QualityNotAvailableError("", [], "Cannot select quality from empty streams list")

        match quality.kind:
            case QualityKind.BEST:
                result = self._get_fallback_stream(streams)
                logger.debug("selected_best_quality", quality=result.quality)
            case QualityKind.WORST:
                # NET-017: shared rank key — see _rank_key. min picks the lowest
                # usable height; ties fall to the lowest input_position, so the
                # WORST arm returns a different record than BEST on a {0, None} set.
                _, result = min(enumerate(streams), key=self._rank_key)
                logger.debug("selected_worst_quality", quality=result.quality)
            case _:
                # Exact match on one quality label, whatever height it carries.
                match = self._find_quality_match(streams, quality)
                if match:
                    result = match
                else:
                    # Quality not available - raise specific error
                    available_qualities = list(dict.fromkeys(s.quality for s in streams))
                    raise QualityNotAvailableError(str(quality), available_qualities)

        return result

    def list_available_qualities(self, streams: list[Stream]) -> list[str]:
        """
        Get sorted list of available quality options from streams.

        Args:
            streams: List of available streams.

        Returns:
            Sorted list of unique quality strings in descending order by resolution.
        """
        qualities = list({s.quality for s in streams})

        def sort_key(q: str) -> int:
            """Extract numeric height for sorting, defaults to 0."""
            try:
                return int(q.replace("p", ""))
            except ValueError:
                return 0

        qualities.sort(key=sort_key, reverse=True)
        logger.debug("listed_qualities", qualities=qualities)
        return qualities
