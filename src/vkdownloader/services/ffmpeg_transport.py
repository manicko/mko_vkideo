"""Optional direct-FFmpeg transport adapter (Block H)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from structlog import get_logger

from ..config import Settings
from ..utils.url_sanitizer import sanitize_exception, sanitize_text_for_log
from .downloader_throttle import get_shutdown_event
from .ffmpeg_utils import (
    _SPAWN_BOUNDARY_KWARGS,
    cancel_subprocess,
    read_progress,
)
from .quality_refresh import StreamBinding

if TYPE_CHECKING:
    from .workspace import DownloadWorkspace
from .ytdlp_downloader import (
    _await_first_and_cancel_others,
    _create_temp_cookie_file,
    _remove_cookie_artifact_dir,
)

logger = get_logger(__name__)


@runtime_checkable
class DownloadTransport(Protocol):
    """Protocol for a download transport adapter."""

    name: str

    async def download(
        self,
        binding: StreamBinding,
        workspace: DownloadWorkspace | None,
        progress_callback: Callable[[object], None] | None = None,
        progress_snapshot_callback: Callable[[object], None] | None = None,
    ) -> Path | None:
        """Download ``binding`` into ``workspace`` staging area."""
        ...


class FfmpegTransport:
    """Direct FFmpeg HLS download transport (optional adapter).

    Cookie values may be passed via argv/headers for this transport; this is a
    bounded risk because credentials are short-lived and scoped, and argv is
    never logged by this module.
    """

    name = "ffmpeg"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else Settings()

    async def download(
        self,
        binding: StreamBinding,
        workspace: DownloadWorkspace | None,
        progress_callback: Callable[[object], None] | None = None,
        progress_snapshot_callback: Callable[[object], None] | None = None,
    ) -> Path | None:
        # Resolve staged output path.
        if workspace is not None and workspace.staging_dir is not None:
            output_file = workspace.staging_dir / workspace.final_path.name
        else:
            # Fallback when no workspace is provided.
            output_file = Path("output.mp4")

        output_file.parent.mkdir(parents=True, exist_ok=True)

        cookie_file: Path | None = None
        try:
            raw_cookies = getattr(binding, "raw_cookies", None)
            cookies = getattr(binding, "cookies", None)
            if raw_cookies:
                cookie_file = _create_temp_cookie_file(raw_cookies)
            elif cookies:
                cookie_file = _create_temp_cookie_file(cookies)

            ffmpeg_url = binding.media_playlist_url

            # Build a Cookie header value from the binding's cookies without
            # embedding the cookie artifact path in the signed URL.
            cookie_header_value: str | None = None
            try:
                from .cookies import scope_cookies_for_url

                scoped_raw = scope_cookies_for_url(raw_cookies, binding.media_playlist_url)
                scoped_flat = (
                    scope_cookies_for_url(cookies, binding.media_playlist_url)
                    if cookies and not raw_cookies
                    else None
                )
            except Exception:  # noqa: BLE001
                scoped_raw = raw_cookies
                scoped_flat = cookies
            source = scoped_raw if raw_cookies else (scoped_flat if cookies else None)
            if source:
                if isinstance(source, list):
                    parts = []
                    for item in source:
                        if isinstance(item, dict):
                            name = str(item.get("name", "")).replace("\r", "").replace("\n", "")
                            value = str(item.get("value", "")).replace("\r", "").replace("\n", "")
                        else:
                            name = (
                                str(getattr(item, "name", "")).replace("\r", "").replace("\n", "")
                            )
                            value = (
                                str(getattr(item, "value", "")).replace("\r", "").replace("\n", "")
                            )
                        if name and value:
                            parts.append(f"{name}={value}")
                    cookie_header_value = "; ".join(parts)
                elif isinstance(source, str):
                    cookie_header_value = source

            headers_content = (
                f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n"
            )
            if cookie_header_value:
                headers_content += f"Cookie: {cookie_header_value}\r\n"

            ffmpeg_args: list[str] = [
                "-y",
                "-progress",
                "pipe:2",
                "-nostats",
                "-headers",
                headers_content,
                "-i",
                ffmpeg_url,
                "-c",
                "copy",
                str(output_file),
            ]
            if not getattr(self.settings, "ssl_verify", True):
                try:
                    i_index = ffmpeg_args.index("-i")
                except ValueError:
                    i_index = len(ffmpeg_args)
                ffmpeg_args[i_index:i_index] = ["-tls_verify", "0"]

            shutdown_event = get_shutdown_event()
            stderr_chunks: list[bytes] = []

            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                *ffmpeg_args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
                **_SPAWN_BOUNDARY_KWARGS,  # type: ignore[arg-type]
            )

            async def _on_shutdown() -> None:
                if process.returncode is None:
                    if not await cancel_subprocess(process):
                        logger.warning(
                            "ffmpeg_cancel_not_clean",
                            pid=process.pid,
                        )

            async def _read_progress() -> None:
                assert process.stderr is not None
                async for progress in read_progress(
                    process.stderr,
                    stderr_collector=stderr_chunks,
                    shutdown_event=shutdown_event,
                    on_shutdown=_on_shutdown,
                ):
                    if progress_callback is not None:
                        try:
                            progress_callback(progress)
                        except Exception:  # noqa: BLE001
                            pass
                    if progress_snapshot_callback is not None:
                        try:
                            # Best-effort translation; no strict schema.
                            progress_snapshot_callback(progress)
                        except Exception:  # noqa: BLE001
                            pass

            try:
                process_task = asyncio.create_task(process.wait())
                reader_task = asyncio.create_task(_read_progress())
                await _await_first_and_cancel_others(process_task, reader_task)

                if process.returncode is None:
                    await process.wait()

                stderr_data = b"".join(stderr_chunks) if stderr_chunks else b""

                if shutdown_event.is_set():
                    if process.returncode is None:
                        await cancel_subprocess(process)
                    return None

                if process.returncode != 0:
                    error_msg = (
                        stderr_data.decode(errors="replace")
                        if stderr_data
                        else "Unknown ffmpeg error"
                    )
                    error_msg = sanitize_text_for_log(error_msg)
                    logger.error(
                        "ffmpeg_download_failed",
                        returncode=process.returncode,
                        error=error_msg,
                    )
                    return None

                logger.info("ffmpeg_download_completed", output=str(output_file))
                return output_file
            except asyncio.CancelledError:
                if process.returncode is None:
                    await cancel_subprocess(process)
                raise
            finally:
                if process.returncode is None:
                    await cancel_subprocess(process)
        except Exception as exc:  # noqa: BLE001
            logger.error("ffmpeg_transport_error", error=sanitize_exception(exc))
            return None
        finally:
            if cookie_file is not None:
                cookie_dir = cookie_file.parent
                try:
                    cookie_file.unlink(missing_ok=True)
                except OSError:
                    pass
                _remove_cookie_artifact_dir(cookie_dir)
