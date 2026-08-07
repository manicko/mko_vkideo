"""Security utilities for path validation and sanitization."""

from pathlib import Path

from structlog import get_logger

from ..config import Settings
from ..exceptions import DownloadError
from ..models.enums import ErrorCode
from ..models.video import VideoWithStreams

logger = get_logger(__name__)


def _sanitize_title(title: str) -> str:
    """Sanitize title for filesystem safety.

    Replaces characters that are invalid on Windows/Unix filesystems with underscores,
    strips whitespace, and limits length to 100 characters.
    """
    for char in '/\\:*?"<>|':
        title = title.replace(char, "_")
    return title.strip()[:100]


def validate_output_path(path: Path, warning: bool = True) -> Path:
    """
    Validate output path to prevent path traversal attacks.

    Resolves the path and checks for suspicious patterns that could indicate
    path traversal attempts. Also warns if the output path is inside the
    repository root.

    Args:
        path: The output path to validate.
        warning: Whether to log a warning if path is inside repo root.

    Returns:
        The resolved and validated Path.

    Raises:
        DownloadError: If path contains traversal attempts ("..").
    """
    # Check for path traversal in original path string
    path_str = str(path)
    if ".." in path_str:
        exc = DownloadError(f"Path traversal detected in output path: {path}")
        exc.error_code = ErrorCode.PATH_TRAVERSAL
        raise exc

    # Resolve to absolute path
    resolved = path.resolve()

    # Check if inside repository root (warn for safety)
    repo_root = Path(__file__).resolve().parent.parent.parent
    try:
        resolved.relative_to(repo_root)
        if warning:
            logger.warning(
                "output_path_inside_repository",
                path=str(resolved),
                repo_root=str(repo_root),
                error_code="output_path_in_repo",
            )
    except ValueError:
        # Path is outside repo root - this is expected for normal use
        pass

    return resolved


def _resolve_output_file(
    video: VideoWithStreams,
    output: Path,
    settings: Settings,
    index: int,
) -> Path:
    """Resolve output file path with sanitized filename.

    Args:
        video: Video with metadata for filename generation.
        output: Output directory override (or "." for default).
        settings: Application settings with default download_dir.
        index: Index for fallback filename (batch context).

    Returns:
        Resolved Path to the output file.
    """
    output_path = output if str(output) != "." else settings.download_dir
    output_path = Path(output_path).resolve()

    validated_output = validate_output_path(output_path, warning=False)
    validated_output.mkdir(parents=True, exist_ok=True)

    safe_title = _sanitize_title(video.title) if video.title else None
    if safe_title:
        output_file = validated_output / f"{safe_title}_{video.id}.mp4"
    else:
        output_file = validated_output / f"{index}_{video.id}.mp4"

    return output_file
