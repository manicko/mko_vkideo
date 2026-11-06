"""Optional direct-FFmpeg transport adapter (Block H)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol, runtime_checkable

from structlog import get_logger

from ..config import Settings
from ..utils.url_sanitizer import sanitize_text_for_log
from .downloader_throttle import get_shutdown_event
from .ffmpeg_utils import (
    _SPAWN_BOUNDARY_KWARGS,
    _temp_argfile,
    cancel_subprocess,
    read_progress,
)
from .quality_refresh import StreamBinding
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

    async def download(self, binding: StreamBinding, workspace: object) -> Path | None:
        """Download ``binding`` into ``workspace`` staging area."""
        ...


class FfmpegTransport:
    """Direct FFmpeg HLS download transport (optional adapter)."""

    name = "ffmpeg"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings if settings is not None else Settings()

    async def download(self, binding: StreamBinding, workspace: object) -> Path | None:
        # Resolve staged output path.
        if workspace is not None and getattr(workspace, "staging_dir", None) is not None:
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
            if cookie_file is not None:
                separator = "&" if "?" in ffmpeg_url else "?"
                ffmpeg_url = f"{ffmpeg_url}{separator}cookies=file:{cookie_file}"

            headers_content = (
                f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n"
            )

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
                ffmpeg_args.insert(5, "-tls_verify")
                ffmpeg_args.insert(6, "0")

            shutdown_event = get_shutdown_event()
            stderr_chunks: list[bytes] = []

            async with _temp_argfile(ffmpeg_args) as argfile:
                cmd: list[str] = ["ffmpeg", f"@{argfile}"]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                    **_SPAWN_BOUNDARY_KWARGS,
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
                async for _progress in read_progress(
                    process.stderr,
                    stderr_collector=stderr_chunks,
                    shutdown_event=shutdown_event,
                    on_shutdown=_on_shutdown,
                ):
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
            logger.error("ffmpeg_transport_error", error=str(exc))
            return None
        finally:
            if cookie_file is not None:
                cookie_dir = cookie_file.parent
                try:
                    cookie_file.unlink(missing_ok=True)
                except OSError:
                    pass
                _remove_cookie_artifact_dir(cookie_dir)
