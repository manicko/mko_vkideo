"""CLI interface for VK Video Downloader using Typer."""

import asyncio
from pathlib import Path

import typer
from tqdm import tqdm

from .config import Settings, setup_logging
from .models.enums import QualityEnum
from .services.downloader import HLSDownloader
from .services.extractor import VKVideoExtractor
from .services.quality import QualitySelector

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
) -> None:
    """Download a single video from vkvideo.ru.

    Extracts available streams, selects the requested quality, and downloads the video
    to the specified output directory.
    """
    setup_logging()

    async def _download() -> Path | None:
        """Async implementation of video download."""
        extractor = VKVideoExtractor()
        video = await extractor.extract_streams(url)

        selector = QualitySelector()
        stream = selector.select(video.streams, quality)

        # Ensure output directory exists
        output.mkdir(parents=True, exist_ok=True)

        # Generate output filename
        output_file = output / f"{video.id}_{stream.quality}.mp4"

        downloader = HLSDownloader()
        result = await downloader.download_with_ffmpeg(
            str(stream.url),
            output_file,
            quality=str(stream.quality),
        )
        return result

    result = asyncio.run(_download())

    if result:
        typer.echo(f"Downloaded: {result}")
    else:
        typer.echo("Download failed", err=True)
        raise typer.Exit(code=1)


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
            extractor = VKVideoExtractor()
            video = await extractor.extract_streams(url)

            selector = QualitySelector()
            stream = selector.select(video.streams, quality)

            # Ensure output directory exists
            output.mkdir(parents=True, exist_ok=True)

            output_file = output / f"{video.id}_{stream.quality}.mp4"

            downloader = HLSDownloader()
            result = await downloader.download_with_ffmpeg(
                str(stream.url),
                output_file,
                quality=str(stream.quality),
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

    results = asyncio.run(_run_batch_with_progress())

    # Print results
    for url, output_path, status in results:
        typer.echo(f"{url}: {status}" + (f" -> {output_path}" if output_path else ""))

    # Summary
    successful = sum(1 for _, _, status in results if status == "success")
    failed = len(results) - successful
    typer.echo(f"\nCompleted: {successful} successful, {failed} failed")


def cli() -> None:
    """Entry point for CLI execution."""
    app()
