"""Security utilities for path validation and sanitization."""

from pathlib import Path

from structlog import get_logger

from ..exceptions import DownloadError

logger = get_logger(__name__)


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
        raise DownloadError(f"Path traversal detected in output path: {path}")

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
            )
    except ValueError:
        # Path is outside repo root - this is expected for normal use
        pass

    return resolved
