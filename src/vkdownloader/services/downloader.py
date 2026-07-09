"""HLS downloader service with segment-level resume support."""

import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

import aiohttp
from structlog import get_logger

from ..config import Settings
from ..services.extractor import VKVideoExtractor
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


class HLSDownloader:
    """Downloads HLS streams to MP4 with segment-level resume support."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize HLSDownloader with optional settings.

        Args:
            settings: Application settings. Uses global settings if not provided.
        """
        self.settings = settings if settings is not None else Settings()

    def _build_ffmpeg_cmd(
        self, m3u8_url: str, output_file: Path, cookies: str | None = None
    ) -> list[str]:
        """Build ffmpeg command for HLS to MP4 conversion."""
        cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""
        headers = f"User-Agent: {self.settings.user_agent}\r\nReferer: https://vkvideo.ru/\r\n{cookie_part}"

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

        return cmd

    async def download_with_ffmpeg(
        self, m3u8_url: str, output_file: Path, quality: str = "best", cookies: str | None = None
    ) -> Path | None:
        """Download HLS stream to MP4 using ffmpeg."""
        logger.info(
            "starting_ffmpeg_download",
            url=_strip_auth_params(m3u8_url),
            output=str(output_file),
            quality=quality,
            has_cookies=bool(cookies),
        )

        cmd = self._build_ffmpeg_cmd(m3u8_url, output_file, cookies)

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


async def download_hls_with_resume(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str = "best",
    cookies: str | None = None,
    settings: Settings | None = None,
    extractor: VKVideoExtractor | None = None,
) -> Path | None:
    """
    Download HLS stream with segment-level resume and token refresh.

    Downloads original HLS segments individually, tracks progress, and can resume
    after interruption by re-downloading missing segments. Uses batched merging
    to handle large number of segments.

    Args:
        video_url: Original VK video URL (for token refresh on 403/410).
        m3u8_url: URL of the HLS m3u8 playlist.
        output_file: Path where the output MP4 file will be saved.
        quality: Quality identifier for logging purposes.
        cookies: Optional cookies from browser session for authentication.
        settings: Application settings.
        extractor: Optional extractor for token refresh on retry.

    Returns:
        Path to downloaded MP4 file on success, None on failure.
    """
    if settings is None:
        settings = Settings()

    segments_dir = output_file.parent / f".{output_file.stem}_segments"
    metadata_file = output_file.parent / f".{output_file.stem}_progress.json"

    segments_dir.mkdir(parents=True, exist_ok=True)

    downloaded_count = _load_downloaded_count(metadata_file)
    headers: dict[str, str] = {
        "User-Agent": settings.user_agent,
        "Referer": "https://vkvideo.ru/",
    }
    if cookies:
        headers["Cookie"] = cookies

    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        playlist_content = await _fetch_playlist_with_retry(
            session, video_url, m3u8_url, headers, extractor, settings
        )
        if not playlist_content:
            return None

        segments = _parse_m3u8_segments(playlist_content)
        logger.info("found_segments", count=len(segments), resume_from=downloaded_count)

        # Download missing segments
        for i in range(downloaded_count, len(segments)):
            segment_url = segments[i]
            if not segment_url.startswith("http"):
                segment_url = urljoin(m3u8_url, segment_url)

            segment_path = segments_dir / f"{i:05d}.ts"
            if not segment_path.exists():
                success = await _download_segment(session, segment_url, segment_path, headers)
                if not success:
                    return None

            downloaded_count += 1
            _save_downloaded_count(metadata_file, downloaded_count)

    # All downloaded - merge in batches
    if downloaded_count == len(segments):
        logger.info("merging_segments", count=downloaded_count)
        result = await _merge_segments_batched(segments_dir, output_file, len(segments))
        if result:
            _cleanup_segments(segments_dir, metadata_file)
        return result

    return None


async def _fetch_playlist_with_retry(
    session: aiohttp.ClientSession,
    video_url: str,
    m3u8_url: str,
    headers: dict[str, str],
    extractor: VKVideoExtractor | None,
    settings: Settings,
    max_retries: int = 3,
) -> str | None:
    """Fetch m3u8 playlist with token refresh on 403/401."""
    current_url = m3u8_url

    for attempt in range(max_retries):
        try:
            async with session.get(current_url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                if response.status in (403, 410) and extractor:
                    logger.info("token_expired_fetching_new", attempt=attempt + 1)
                    streams, new_cookies = await extractor.extract_streams_with_cookies(video_url)
                    if streams:
                        current_url = str(streams[0].url)
                        headers["Cookie"] = new_cookies or ""
                        continue
        except Exception as e:
            logger.warning("playlist_fetch_failed", error=str(e))

    return None


def _parse_m3u8_segments(content: str) -> list[str]:
    """Parse m3u8 playlist and extract segment URLs."""
    segments = []
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            segments.append(line)
    return segments


async def _download_segment(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
) -> bool:
    """Download a single HLS segment."""
    try:
        async with session.get(segment_url, headers=headers) as response:
            if response.status == 200:
                with open(output_path, "wb") as f:
                    f.write(await response.read())
                return True
            logger.warning("segment_download_failed", status=response.status)
            return False
    except Exception as e:
        logger.error("segment_download_error", error=str(e))
        return False


async def _merge_segments_batched(segments_dir: Path, output_file: Path, count: int) -> Path | None:
    """Merge segments in batches to avoid command line limits."""
    batch_size = 100
    temp_files = []

    # Process in batches
    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        batch_files = [segments_dir / f"{i:05d}.ts" for i in range(batch_start, batch_end)]

        # Check all files exist
        if not all(f.exists() for f in batch_files):
            continue

        batch_output = segments_dir / f"batch_{batch_start:05d}.ts"
        file_list_path = segments_dir / f"batch_list_{batch_start}.txt"

        with open(file_list_path, "w", encoding="utf-8") as f:
            for segment_path in batch_files:
                f.write(f"file '{segment_path.as_posix()}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(file_list_path),
            "-c",
            "copy",
            str(batch_output),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error = stderr.decode() if stderr else "Unknown error"
            logger.error("batch_merge_failed", error=error[:200])
            return None

        # Remove individual segment files after batch merge
        for segment_path in batch_files:
            segment_path.unlink()
        file_list_path.unlink()

        temp_files.append(batch_output)

    # Final merge of all batches
    if temp_files:
        final_list_path = segments_dir / "final_list.txt"
        with open(final_list_path, "w", encoding="utf-8") as f:
            for temp_file in temp_files:
                f.write(f"file '{temp_file.as_posix()}'\n")

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(final_list_path),
            "-c",
            "copy",
            str(output_file),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info("merge_completed", output=str(output_file))
            final_list_path.unlink()
            for tf in temp_files:
                tf.unlink()
            return output_file

        logger.error("final_merge_failed", error=stderr.decode()[:200] if stderr else "Unknown")

    return None


def _load_downloaded_count(metadata_file: Path) -> int:
    """Load downloaded segment count from metadata."""
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
            data: dict[str, int] = json.load(f)
            return data.get("downloaded_count", 0)
    return 0


def _save_downloaded_count(metadata_file: Path, count: int) -> None:
    """Save downloaded segment count to metadata."""
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump({"downloaded_count": count}, f)


def _cleanup_segments(segments_dir: Path, metadata_file: Path) -> None:
    """Clean up downloaded segments."""
    for f in segments_dir.glob("*"):
        f.unlink()
    try:
        segments_dir.rmdir()
    except OSError:
        pass
    metadata_file.unlink(missing_ok=True)
