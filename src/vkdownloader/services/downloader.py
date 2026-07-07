"""HLS downloader service using ffmpeg for direct HLS to MP4 conversion."""

import asyncio
from pathlib import Path

from structlog import get_logger

from ..config import Settings

logger = get_logger(__name__)


class HLSDownloader:
    """Downloads HLS streams to MP4 using ffmpeg's native HLS support."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize HLSDownloader with optional settings.

        Args:
            settings: Application settings. Uses global settings if not provided.
        """
        self.settings = settings if settings is not None else Settings()
        logger.debug("hls_downloader_initialized")

    def _build_ffmpeg_cmd(self, m3u8_url: str, output_file: Path) -> list[str]:
        """
        Build ffmpeg command for HLS to MP4 conversion.

        Args:
            m3u8_url: URL of the HLS m3u8 playlist.
            output_file: Path where the output MP4 file will be saved.

        Returns:
            List of command arguments for ffmpeg subprocess.
        """
        headers = f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n"

        cmd = [
            "ffmpeg",
            "-y",
            "-headers",
            headers,
            "-i",
            m3u8_url,
            "-c",
            "copy",
            str(output_file),
        ]

        logger.debug("built_ffmpeg_command", output=str(output_file))
        return cmd

    async def download_with_ffmpeg(
        self, m3u8_url: str, output_file: Path, quality: str = "best"
    ) -> Path | None:
        """
        Download HLS stream to MP4 using ffmpeg.

        Args:
            m3u8_url: URL of the HLS m3u8 playlist to download.
            output_file: Path where the output MP4 file will be saved.
            quality: Quality identifier for logging purposes.

        Returns:
            Path to downloaded MP4 file on success, None on failure.
        """
        logger.info("starting_ffmpeg_download", url=m3u8_url, output=str(output_file), quality=quality)

        cmd = self._build_ffmpeg_cmd(m3u8_url, output_file)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown ffmpeg error"
            logger.error("ffmpeg_download_failed", returncode=process.returncode, error=error_msg)
            return None

        logger.info("ffmpeg_download_completed", output=str(output_file))
        return output_file

