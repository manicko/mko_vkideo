import asyncio
import sys
from pathlib import Path

import yt_dlp
from structlog import get_logger

from vkdownloader.config import Settings, setup_logging
from vkdownloader.models.enums import DownloadMethod, QualityEnum
from vkdownloader.services.extractor import VKVideoExtractor
from vkdownloader.services.quality import QualitySelector
from vkdownloader.services.downloader import HLSDownloader

logger = get_logger(__name__)


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

    # Get available streams and qualities
    video_data = await extractor.extract_streams(url)
    streams = video_data.streams
    cookies = None
    browser_streams = []

    # For ffmpeg method, get fresh m3u8 URL and cookies from visible browser
    if method == DownloadMethod.FFMPEG:
        browser_streams, cookies = await extractor.extract_streams_with_cookies(url)

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

    # Choose download method
    if method == DownloadMethod.FFMPEG:
        downloader = HLSDownloader(settings=settings)
        # Use browser m3u8 URL (fresh token) if available
        m3u8_url = browser_streams[0].url if browser_streams else stream.url
        result = await downloader.download_with_ffmpeg(str(m3u8_url), output_file, str(stream.quality), cookies)
        # Fallback to yt-dlp if ffmpeg fails
        if result is None:
            logger.info("ffmpeg_failed_fallback_to_ytdlp")
            result = await _download_with_ytdlp(url, output_file, str(stream.quality))
        return result
    else:
        return await _download_with_ytdlp(url, output_file, str(stream.quality))


async def _download_with_ytdlp(video_url: str, output_file: Path, quality: str) -> Path | None:
    """Download using yt-dlp (handles VK protections)."""
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
            "socket_timeout": 120,
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