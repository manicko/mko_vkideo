"""CLI interface for VK Video Downloader using Typer."""

import asyncio
from pathlib import Path

import typer
from structlog import get_logger
from tqdm import tqdm

from .config import Settings, setup_logging
from .models.enums import DownloadMethod, QualityEnum
from .services.downloader import perform_download
from .services.extractor import VKVideoExtractor
from .services.quality import QualitySelector
from .utils.security import validate_output_path

logger = get_logger(__name__)

app = typer.Typer(
    name="vkdownloader",
    help="Download videos from vkvideo.ru with quality selection support",
)


@app.command()
def download(
    url: str = typer.Argument(..., help="VK Video URL to download"),
    quality: QualityEnum = typer.Option(QualityEnum.BEST, help="Video quality selection"),  # noqa: B008
    output: Path = typer.Option(  # noqa: B008
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded video",
    ),
    method: DownloadMethod = typer.Option(  # noqa: B008
        DownloadMethod.AUTO,
        "--method",
        "-m",
        help="Download method: yt-dlp, ffmpeg, or auto",
    ),
) -> None:
    """Download a single video from vkvideo.ru.

    Extracts available streams, selects the requested quality, and downloads the video
    to the specified output directory.
    """
    setup_logging()

    async def _download() -> Path | None:
        """Async implementation of video download."""
        settings = Settings()
        extractor = VKVideoExtractor(settings=settings)
        video = await extractor.extract_streams(url)

        # Print available qualities
        if video.streams:
            logger.info("available_streams", count=len(video.streams))
            selector = QualitySelector()
            available = selector.list_available_qualities(video.streams)
            logger.info("available_qualities", qualities=available[:8])

        selector = QualitySelector()
        stream = selector.select(video.streams, quality)

        # Validate output directory to prevent path traversal
        validated_output = validate_output_path(output, warning=False)

        # Ensure output directory exists
        validated_output.mkdir(parents=True, exist_ok=True)

        # Generate output filename
        output_file = validated_output / f"{video.id}_{stream.quality}.mp4"

        return await perform_download(
            url, str(stream.quality), output_file, method, extractor, settings
        )

    try:
        result = asyncio.run(_download())

        if result:
            typer.echo(f"Downloaded: {result}")
        else:
            typer.echo("Download failed", err=True)
            raise typer.Exit(code=1)

    except ValueError:
        typer.echo(
            "Invalid URL format. Expected format: https://vkvideo.ru/video-{owner_id}_{video_id}",
            err=True,
        )
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        typer.echo("\nDownload cancelled", err=True)
        raise typer.Exit(code=130) from None
    except Exception:
        typer.echo("An error occurred during download", err=True)
        raise typer.Exit(code=1) from None


@app.command("batch")
def batch_download(
    urls_file: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        help="Path to file containing video URLs (one per line)",
    ),
    quality: QualityEnum = typer.Option(  # noqa: B008
        QualityEnum.BEST,
        help="Video quality selection for all downloads",
    ),
    output: Path = typer.Option(  # noqa: B008
        ".",
        "--output",
        "-o",
        help="Output directory for downloaded videos",
    ),
    method: DownloadMethod = typer.Option(  # noqa: B008
        DownloadMethod.AUTO,
        "--method",
        "-m",
        help="Download method: yt-dlp, ffmpeg, or auto",
    ),
) -> None:
    """Download multiple videos from a file.

    Reads video URLs from a file (one URL per line) and downloads each video
    with the specified quality to the output directory.
    """
    setup_logging()

    # Read URLs from file
    urls = [
        line.strip()
        for line in urls_file.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    if not urls:
        typer.echo(f"No URLs found in {urls_file}", err=True)
        raise typer.Exit(code=1)

    async def _download_single(url: str) -> tuple[str, str, str]:
        """Download a single video and return result tuple."""
        try:
            settings = Settings()
            extractor = VKVideoExtractor(settings=settings)
            video = await extractor.extract_streams(url)

            selector = QualitySelector()
            stream = selector.select(video.streams, quality)

            # Validate output directory to prevent path traversal
            validated_output = validate_output_path(output, warning=False)

            # Ensure output directory exists
            validated_output.mkdir(parents=True, exist_ok=True)

            output_file = validated_output / f"{video.id}_{stream.quality}.mp4"

            result = await perform_download(
                url, str(stream.quality), output_file, method, extractor, settings
            )

            status = "success" if result else "failed"
            return (url, str(output_file) if result else "", status)

        except Exception as e:
            return (url, "", f"error: {e}")

    # Initialize progress bar
    pbar = tqdm(urls, desc="Downloading videos", unit="video")

    async def _run_batch_with_progress() -> list[tuple[str, str, str]]:
        """Run batch download with tqdm progress callback."""
        semaphore = asyncio.Semaphore(Settings().max_concurrent_downloads)

        async def _limited_download(url: str) -> tuple[str, str, str]:
            async with semaphore:
                result = await _download_single(url)
                pbar.update(1)
                return result

        tasks = [_limited_download(url) for url in urls]
        results = await asyncio.gather(*tasks)
        pbar.close()
        return list(results)

    try:
        results = asyncio.run(_run_batch_with_progress())

        # Print results
        for url, output_path, status in results:
            typer.echo(f"{url}: {status}" + (f" -> {output_path}" if output_path else ""))

        # Summary
        successful = sum(1 for _, _, status in results if status == "success")
        failed = len(results) - successful
        typer.echo(f"\nCompleted: {successful} successful, {failed} failed")

    except KeyboardInterrupt:
        pbar.close()
        typer.echo("\nDownload cancelled", err=True)
        raise typer.Exit(code=130) from None


def cli() -> None:
    """Entry point for CLI execution."""
    app()
