"""HLS downloader service with segment-level resume support."""

import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

import aiohttp
import yt_dlp
from structlog import get_logger

from ..config import Settings
from ..models.dtos import HLSDownloadRequest
from ..models.enums import DownloadMethod
from ..services.extractor import VKVideoExtractor
from ..utils.security import validate_output_path
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)

# Maximum retry attempts for getting new token on resume failure
MAX_RESUME_RETRIES = 3


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


async def download_hls_with_resume(request: HLSDownloadRequest) -> Path | None:
    """
    Download HLS stream with segment-level resume and token refresh.

    Downloads original HLS segments individually, tracks progress, and can resume
    after interruption by re-downloading missing segments. Uses batched merging
    to handle large number of segments.

    Args:
        request: HLSDownloadRequest containing all download parameters.

    Returns:
        Path to downloaded MP4 file on success, None on failure.
    """
    if request.settings is None:
        settings = Settings()
    else:
        settings = request.settings

    # Validate output path to prevent path traversal
    output_file = validate_output_path(request.output_file)

    segments_dir = output_file.parent / f".{output_file.stem}_segments"
    metadata_file = output_file.parent / f".{output_file.stem}_progress.json"

    segments_dir.mkdir(parents=True, exist_ok=True)

    try:
        downloaded_count = _load_downloaded_count(metadata_file)
        headers: dict[str, str] = {
            "User-Agent": settings.user_agent,
            "Referer": "https://vkvideo.ru/",
        }
        if request.cookies:
            headers["Cookie"] = request.cookies

        connector = aiohttp.TCPConnector(limit=10)
        async with aiohttp.ClientSession(connector=connector) as session:
            playlist_content = await _fetch_playlist_with_retry(
                session, request.video_url, request.m3u8_url, headers,
                request.extractor, settings
            )
            if not playlist_content:
                return None

            segments = _parse_m3u8_segments(playlist_content)
            logger.info("found_segments", count=len(segments), resume_from=downloaded_count)

            # Download missing segments
            for i in range(downloaded_count, len(segments)):
                segment_url = segments[i]
                if not segment_url.startswith("http"):
                    segment_url = urljoin(request.m3u8_url, segment_url)

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
    finally:
        # Clean up on failure - only if segments_dir still exists
        # (cleanup is done inside try block on success, so dir won't exist then)
        if segments_dir.exists():
            _cleanup_segments(segments_dir, metadata_file)


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


def _build_ffmpeg_concat_command(file_list_path: Path, output_file: Path) -> list[str]:
    """Build ffmpeg concat command for merging files.

    Args:
        file_list_path: Path to the file list text file.
        output_file: Path to the output file.

    Returns:
        Command list for ffmpeg.
    """
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
        str(output_file),
    ]

    return cmd


async def _merge_batch_segments(batch_files: list[Path], temp_dir: Path) -> Path | None:
    """Merge a batch of segments into a single temp file.

    Args:
        batch_files: List of segment file paths to merge.
        temp_dir: Directory for temp files.

    Returns:
        Path to merged batch file on success, None on failure.
    """
    # Derive batch_start from first file's index (e.g., "00000.ts" -> 0)
    batch_start = int(batch_files[0].stem)
    batch_output = temp_dir / f"batch_{batch_start:05d}.ts"
    file_list_path = temp_dir / f"batch_list_{batch_start}.txt"

    # Write file list for concat demuxer
    with open(file_list_path, "w", encoding="utf-8") as f:
        for segment_path in batch_files:
            f.write(f"file '{segment_path.as_posix()}'\n")

    cmd = _build_ffmpeg_concat_command(file_list_path, batch_output)

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

    return batch_output


async def _perform_final_merge(temp_files: list[Path], output_file: Path) -> bool:
    """Merge all batch temp files into final output.

    Args:
        temp_files: List of batch temp file paths to merge.
        output_file: Final output file path.

    Returns:
        True on success, False on failure.
    """
    final_list_path = temp_files[0].parent / "final_list.txt"

    # Write file list for concat demuxer
    with open(final_list_path, "w", encoding="utf-8") as f:
        for temp_file in temp_files:
            f.write(f"file '{temp_file.as_posix()}'\n")

    cmd = _build_ffmpeg_concat_command(final_list_path, output_file)

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
        return True

    logger.error("final_merge_failed", error=stderr.decode()[:200] if stderr else "Unknown")
    return False


async def _merge_segments_batched(segments_dir: Path, output_file: Path, count: int) -> Path | None:
    """Merge segments in batches to avoid command line limits.

    Args:
        segments_dir: Directory containing segment files.
        output_file: Final output file path.
        count: Total number of segments to merge.

    Returns:
        Path to output file on success, None on failure.
    """
    batch_size = 100
    temp_files: list[Path] = []

    # Process in batches
    for batch_start in range(0, count, batch_size):
        batch_end = min(batch_start + batch_size, count)
        batch_files = [segments_dir / f"{i:05d}.ts" for i in range(batch_start, batch_end)]

        # Check all files exist
        if not all(f.exists() for f in batch_files):
            continue

        result = await _merge_batch_segments(batch_files, segments_dir)
        if result is None:
            return None

        temp_files.append(result)

    # Final merge of all batches
    if temp_files:
        if await _perform_final_merge(temp_files, output_file):
            return output_file

    return None


def _load_downloaded_count(metadata_file: Path) -> int:
    """Load downloaded segment count from metadata."""
    if metadata_file.exists():
        try:
            with open(metadata_file, encoding="utf-8") as f:
                data: dict[str, int] = json.load(f)
                return data.get("downloaded_count", 0)
        except (json.JSONDecodeError, OSError):
            return 0
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


async def download_with_ytdlp_with_resume_fallback(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    extractor: VKVideoExtractor | None,
    settings: Settings | None = None,
) -> Path | None:
    """Download using yt-dlp with automatic segment-based resume on failure.

    Flow:
    1. Try yt-dlp download
    2. On failure with partial file: get fresh token via browser + switch to segment download
    3. Segment download resumes from last checkpoint

    Args:
        video_url: Original VK video URL.
        m3u8_url: HLS playlist URL (may be stale).
        output_file: Output file path.
        quality: Quality string.
        extractor: VKVideoExtractor for token refresh.
        settings: Application settings.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    if settings is None:
        settings = Settings()

    retry_count = 0

    while retry_count <= MAX_RESUME_RETRIES:
        result = await _download_with_ytdlp(video_url, output_file, quality, settings)

        if result:
            if retry_count > 0:
                logger.info("download_completed_after_retries", retries=retry_count)
            return result

        retry_count += 1

        # Check for partial file - switch to segment download with fresh token
        validated_output = validate_output_path(output_file, warning=False)
        if validated_output.exists() and validated_output.stat().st_size > 0:
            logger.warning(
                "download_interrupted_switching_to_segments",
                path=str(validated_output),
                size=validated_output.stat().st_size,
                retry=retry_count,
            )

            # Get fresh m3u8 URL with new token via browser
            if retry_count <= MAX_RESUME_RETRIES:
                logger.info("attempting_segment_resume", retry=retry_count)

                try:
                    if extractor is None:
                        extractor = VKVideoExtractor(settings=settings)
                    browser_streams, cookies = await extractor.extract_streams_with_cookies(
                        video_url
                    )
                    if browser_streams:
                        m3u8_url = str(browser_streams[0].url)
                        logger.info("fresh_token_obtained_for_resume")
                        # Remove partial file to start clean segment download
                        validated_output.unlink()
                        # Continue to segment download
                        segment_result = await download_hls_with_resume(
                            HLSDownloadRequest(
                                video_url=video_url,
                                m3u8_url=m3u8_url,
                                output_file=validated_output,
                                quality=quality,
                                cookies=cookies,
                                settings=settings,
                                extractor=extractor,
                            )
                        )
                        if segment_result:
                            return segment_result
                except Exception as e:
                    logger.warning("failed_to_refresh_token", error=str(e))
            else:
                logger.error("max_retries_exceeded")
                return None
        else:
            # No partial file and no success - original failure, no point in segment download
            return None

    # All retries exhausted without success
    return None


async def _download_with_ytdlp(
    video_url: str, output_file: Path, quality: str, settings: Settings
) -> Path | None:
    """Download using yt-dlp."""
    quality_str = quality.replace("p", "") if quality else "720"
    user_agent = settings.user_agent

    def _download() -> str:
        ydl_opts = {
            "outtmpl": str(output_file),
            "quiet": False,
            "no_warnings": True,
            "format": f"best[height<={quality_str}]",
            "nocheckcertificate": True,
            "hls_prefer_native": True,
            "http_headers": {
                "User-Agent": user_agent,
                "Referer": "https://vkvideo.ru/",
            },
            "socket_timeout": 180,
            "retries": 10,
            "fragment_retries": 10,
            "throttledratelimit": 0,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        return str(output_file)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _download)
        return Path(result)
    except Exception as e:
        logger.error("download_failed", error=str(e))
        return None


async def perform_download(
    url: str,
    quality: str,
    output_file: Path,
    method: DownloadMethod,
    extractor: VKVideoExtractor | None = None,
    settings: Settings | None = None,
) -> Path | None:
    """Perform video download using the specified method.

    Args:
        url: VK Video URL to download.
        quality: Quality string (e.g., "720", "1080").
        output_file: Output file path.
        method: Download method (yt-dlp, ffmpeg, or auto).
        extractor: Optional VKVideoExtractor for token refresh.
        settings: Application settings.

    Returns:
        Path to downloaded file on success, None on failure.
    """
    if settings is None:
        settings = Settings()

    if extractor is None:
        extractor = VKVideoExtractor(settings=settings)

    # Get m3u8 URL via yt-dlp (most reliable for extraction)
    video_data = await extractor.extract_streams(url)
    streams = video_data.streams

    if not streams:
        logger.error("no_streams_found", url=_strip_auth_params(url))
        return None

    m3u8_url = str(streams[0].url)

    match method:
        case DownloadMethod.YTDLP:
            return await download_with_ytdlp_with_resume_fallback(
                url, m3u8_url, output_file, quality, extractor, settings
            )
        case DownloadMethod.FFMPEG:
            # For ffmpeg: get cookies via browser first
            browser_streams, cookies = await extractor.extract_streams_with_cookies(url)
            if browser_streams:
                m3u8_url = str(browser_streams[0].url)
            downloader = HLSDownloader(settings=settings)
            result = await downloader.download_with_ffmpeg(
                m3u8_url, output_file, quality, cookies
            )
            if result is None:
                logger.info("ffmpeg_failed_fallback_to_segment_download")
                result = await download_hls_with_resume(
                    HLSDownloadRequest(
                        video_url=url,
                        m3u8_url=m3u8_url,
                        output_file=output_file,
                        quality=quality,
                        cookies=cookies,
                        settings=settings,
                        extractor=extractor,
                    )
                )
            return result
        case DownloadMethod.AUTO:
            # Auto: try yt-dlp first (more reliable), segment download for resume
            return await download_with_ytdlp_with_resume_fallback(
                url, m3u8_url, output_file, quality, extractor, settings
            )
        case _:
            logger.error("unknown_download_method", method=str(method))
            return None
