"""Quality selection service for choosing appropriate video streams."""

from structlog import get_logger

from ..exceptions import QualityNotAvailableError
from ..models.enums import QualityEnum
from ..models.video import Stream

logger = get_logger(__name__)


class QualitySelector:
    """Selects appropriate stream from available streams based on quality preference."""

    def _find_quality_match(self, streams: list[Stream], quality_str: str) -> Stream | None:
        """
        Find a stream matching the requested quality string.

        Supports both "720" and "720p" formats for matching.

        Args:
            streams: List of available streams to search.
            quality_str: Quality string to match (e.g., "720", "1080").

        Returns:
            Matching Stream object, or None if not found.
        """
        for stream in streams:
            stream_quality = stream.quality.replace("p", "") if stream.quality else ""
            if stream_quality == quality_str or stream.quality == quality_str:
                logger.debug("selected_matching_quality", quality=stream.quality)
                return stream
        return None

    def _get_fallback_stream(self, streams: list[Stream]) -> Stream:
        """
        Get the best quality stream as fallback.

        Args:
            streams: List of available streams.

        Returns:
            Stream with highest resolution.
        """
        return max(streams, key=lambda s: s.height or 0)

    def select(self, streams: list[Stream], quality: QualityEnum) -> Stream:
        """
        Select a stream based on quality preference.

        Args:
            streams: List of available streams to choose from.
            quality: Quality preference (best, worst, or specific resolution).

        Returns:
            Selected Stream object.

        Raises:
            ValueError: If streams list is empty.
            QualityNotAvailableError: If requested quality is not available.
        """
        if not streams:
            raise ValueError("Cannot select from empty streams list")

        match quality:
            case QualityEnum.BEST:
                result = self._get_fallback_stream(streams)
                logger.debug("selected_best_quality", quality=result.quality)
            case QualityEnum.WORST:
                result = min(streams, key=lambda s: s.height or float("inf"))
                logger.debug("selected_worst_quality", quality=result.quality)
            case _:
                # Try to find matching quality (support both "720" and "720p" formats)
                quality_str = str(quality)
                match = self._find_quality_match(streams, quality_str)
                if match:
                    result = match
                else:
                    # Quality not available - raise specific error
                    available_qualities = [s.quality for s in streams]
                    raise QualityNotAvailableError(
                        f"Requested quality '{quality}' not available. Available: {available_qualities}"
                    )

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
