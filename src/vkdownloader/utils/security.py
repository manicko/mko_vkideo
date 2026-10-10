"""Security utilities for path validation and sanitization."""

from pathlib import Path

from structlog import get_logger

from ..config import Settings
from ..exceptions import DownloadError
from ..models.enums import ErrorCode
from ..models.video import VideoWithStreams

logger = get_logger(__name__)

# C0 control characters (chr(0)-chr(31)) and DEL (chr(127)) are not legal in
# filenames on any platform and corrupt console/log output when embedded in a
# title. They are replaced with underscores — never stripped — because str.strip
# cannot reach control characters in the middle of a string, and a null byte
# that survives sanitization would raise ValueError at the filesystem layer.
_CONTROL_CHARS = "".join(chr(c) for c in range(32)) + chr(127)


def sanitize_filename_component(title: str) -> str:
    """Sanitize a filename component for filesystem safety.

    Replaces characters that are invalid on Windows/Unix filesystems — the nine
    path-separator and reserved characters and the C0 control range
    (chr(0)-chr(31)) plus DEL (chr(127)) — with underscores, strips surrounding
    whitespace, and limits the title component to 100 characters. The composed
    output path — including the ``_{id}.mp4`` suffix and the output directory —
    is not length-bounded by this function; any path-length limit is enforced
    by the platform, not by this code.

    This function does **not** handle reserved Windows device names (CON, PRN,
    AUX, NUL, COM1-COM9, LPT1-LPT9) or trailing dots and spaces — those are
    filesystem properties outside this function's scope. Reserved names are
    ordinary files on POSIX (§5.7 item 8).
    """
    for char in '/\\:*?"<>|' + _CONTROL_CHARS:
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
    # Check for path traversal in the original path (before resolution).
    # This catches ".." components in unresolved user input.
    if ".." in path.parts:
        exc = DownloadError(f"Path traversal detected in output path: {path}")
        exc.error_code = ErrorCode.PATH_TRAVERSAL
        raise exc

    # Resolve to absolute path
    resolved = path.resolve()

    # Defense-in-depth: check for ".." components in the resolved path too.
    # This catches edge cases where symlinks or UNC paths cause ".." to
    # survive resolution, and makes the guard effective even when callers
    # pass already-resolved paths (where the pre-resolution check is a no-op).
    if ".." in resolved.parts:
        exc = DownloadError(f"Path traversal detected in resolved path: {resolved}")
        exc.error_code = ErrorCode.PATH_TRAVERSAL
        raise exc

    # Check if inside repository root (warn for safety)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
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

    validated_output = validate_output_path(output_path)
    validated_output.mkdir(parents=True, exist_ok=True)

    safe_title = sanitize_filename_component(video.title) if video.title else None
    if safe_title:
        output_file = validated_output / f"{safe_title}_{video.id}.mp4"
    else:
        output_file = validated_output / f"{index}_{video.id}.mp4"

    return output_file
