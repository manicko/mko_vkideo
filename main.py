import asyncio
import sys
from pathlib import Path

import yt_dlp
from structlog import get_logger

from vkdownloader.config import Settings, setup_logging
from vkdownloader.models.enums import DownloadMethod, QualityEnum
from vkdownloader.services.extractor import VKVideoExtractor
from vkdownloader.services.quality import QualitySelector
from vkdownloader.services.downloader import download_hls_with_resume, HLSDownloader

logger = get_logger(__name__)

# Maximum retry attempts for getting new token on resume failure
MAX_RESUME_RETRIES = 3


async def download_video(
    url: str,
    quality: QualityEnum = QualityEnum.BEST,
    output_dir: Path = Path("."),
    method: DownloadMethod = DownloadMethod.AUTO,
) -> Path | None:
    """Download a video from VK Video.

    Args:
        url: VK Video URL to download.
        quality: Video quality selection.
        output_dir: Output directory for downloaded video.
        method: Download method (yt-dlp, ffmpeg, or auto).

    Returns:
        Path to downloaded file on success, None on failure.
    """
    setup_logging()
    settings = Settings()

    extractor = VKVideoExtractor(settings=settings)
    video_id = extractor.parse_video_id(url)[0] + "_" + extractor.parse_video_id(url)[1]

    # Get available streams and qualities (without browser)
    video_data = await extractor.extract_streams(url)
    streams = video_data.streams

    # Print available qualities
    if streams:
        print(f"Available streams: {len(streams)}")
        selector = QualitySelector()
        available = selector.list_available_qualities(streams)
        print(f"Qualities: {', '.join(available[:8])}")

    selector = QualitySelector()
    stream = selector.select(streams, quality)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{video_id}_{stream.quality}.mp4"

    # Get m3u8 URL
    m3u8_url = str(stream.url)

    # Choose download method
    if method == DownloadMethod.YTDLP:
        # For yt-dlp: use yt-dlp with segment fallback for resume
        result = await download_with_ytdlp_with_resume_fallback(
            url, m3u8_url, output_file, str(stream.quality), extractor, settings
        )
        return result
    elif method == DownloadMethod.FFMPEG:
        # For ffmpeg: get cookies via browser first
        browser_streams, cookies = await extractor.extract_streams_with_cookies(url)
        m3u8_url = str(browser_streams[0].url) if browser_streams else m3u8_url
        downloader = HLSDownloader(settings=settings)
        result = await downloader.download_with_ffmpeg(m3u8_url, output_file, str(stream.quality), cookies)
        if result is None:
            logger.info("ffmpeg_failed_fallback_to_segment_download")
            result = await download_hls_with_resume(
                m3u8_url, output_file, str(stream.quality), cookies, settings, extractor
            )
        return result
    else:
        # Auto: try yt-dlp first (more reliable), segment download for resume
        return await download_with_ytdlp_with_resume_fallback(
            url, m3u8_url, output_file, str(stream.quality), extractor, settings
        )


async def download_with_ytdlp_with_resume_fallback(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str,
    extractor: VKVideoExtractor,
    settings: Settings,
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
    retry_count = 0

    while retry_count <= MAX_RESUME_RETRIES:
        result = await _download_with_ytdlp(video_url, output_file, quality)

        if result:
            if retry_count > 0:
                logger.info("download_completed_after_retries", retries=retry_count)
            return result

        retry_count += 1

        # Check for partial file - switch to segment download with fresh token
        if output_file.exists() and output_file.stat().st_size > 0:
            logger.warning(
                "download_interrupted_switching_to_segments",
                path=str(output_file),
                size=output_file.stat().st_size,
                retry=retry_count,
            )

            if retry_count <= MAX_RESUME_RETRIES:
                print(f"Download interrupted. Switching to segment-based resume ({retry_count}/{MAX_RESUME_RETRIES})...")

                # Get fresh m3u8 URL with new token via browser
                try:
                    browser_streams, cookies = await extractor.extract_streams_with_cookies(video_url)
                    if browser_streams:
                        m3u8_url = str(browser_streams[0].url)
                        logger.info("fresh_token_obtained_for_resume")
                        # Remove partial file to start clean segment download
                        output_file.unlink()
                        # Continue to segment download
                        return await download_hls_with_resume(
                            m3u8_url, output_file, quality, cookies, settings, extractor
                        )
                except Exception as e:
                    logger.warning("failed_to_refresh_token", error=str(e))
            else:
                logger.error("max_retries_exceeded")
                print(f"Failed to download after {MAX_RESUME_RETRIES} attempts. Stopping.", file=sys.stderr)
                return None
        else:
            # No partial file and no success - original failure, no point in segment download
            return None

    # Final fallback to segment download
    if output_file.exists():
        output_file.unlink()

    logger.info("final_fallback_to_segment_download")
    return await download_hls_with_resume(m3u8_url, output_file, quality, None, settings, extractor)


async def _download_with_ytdlp(video_url: str, output_file: Path, quality: str) -> Path | None:
    """Download using yt-dlp."""
    quality_str = quality.replace("p", "") if quality else "720"

    def _download() -> str:
        ydl_opts = {
            "outtmpl": str(output_file),
            "quiet": False,
            "no_warnings": True,
            "format": f"best[height<={quality_str}]",
            "nocheckcertificate": True,
            "hls_prefer_native": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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


def main() -> None:
    """Main entry point for video download."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <vk_video_url> [quality] [output_dir] [method]")
        print("  quality: 240, 360, 480, 720, 1080, best (default), worst")
        print("  output_dir: directory for downloaded video (default: current directory)")
        print("  method: yt-dlp, ffmpeg, auto (default)")
        sys.exit(1)

    url = sys.argv[1]

    try:
        quality = QualityEnum(sys.argv[2]) if len(sys.argv) > 2 else QualityEnum.BEST
    except ValueError:
        print(f"Invalid quality: {sys.argv[2]}")
        print(f"Available qualities: {', '.join(q.value for q in QualityEnum)}")
        sys.exit(1)

    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(".")

    try:
        method = DownloadMethod(sys.argv[4]) if len(sys.argv) > 4 else DownloadMethod.AUTO
    except ValueError:
        print(f"Invalid method: {sys.argv[4]}")
        print(f"Available methods: {', '.join(m.value for m in DownloadMethod)}")
        sys.exit(1)

    result = asyncio.run(download_video(url, quality, output_dir, method))

    if result:
        print(f"Downloaded: {result}")
    else:
        print("Download failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()