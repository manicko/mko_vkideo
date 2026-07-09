"""Quality selection service for choosing appropriate video streams."""

from structlog import get_logger

from ..exceptions import QualityNotAvailableError
from ..models.enums import QualityEnum
from ..models.video import Stream

logger = get_logger(__name__)


class QualitySelector:
    """Selects appropriate stream from available streams based on quality preference."""

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
                result = max(streams, key=lambda s: s.height or 0)
                logger.debug("selected_best_quality", quality=result.quality)
            case QualityEnum.WORST:
                result = min(streams, key=lambda s: s.height or float("inf"))
                logger.debug("selected_worst_quality", quality=result.quality)
            case _:
                # Try to find matching quality (support both "720" and "720p" formats)
                quality_str = str(quality)
                for stream in streams:
                    stream_quality = stream.quality.replace("p", "") if stream.quality else ""
                    if stream_quality == quality_str or stream.quality == quality_str:
                        logger.debug("selected_matching_quality", quality=stream.quality)
                        return stream
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
