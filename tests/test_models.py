"""Tests for domain models."""


from vkdownloader.models.enums import DownloadStatus, StreamFormat
from vkdownloader.models.video import DownloadProgress, Stream, Video, VideoWithStreams


def test_video_model_creation() -> None:
    """Test Video model creates with required fields."""
    video = Video(
        id="12345_67890",
        title="Test Video",
        description="Test description",
        duration=120,
        views=1000,
    )

    assert video.id == "12345_67890"
    assert video.title == "Test Video"
    assert video.description == "Test description"
    assert video.duration == 120
    assert video.views == 1000


def test_video_model_optional_fields() -> None:
    """Test Video model with minimal required fields."""
    video = Video(id="12345_67890")

    assert video.id == "12345_67890"
    assert video.title is None
    assert video.description is None
    assert video.duration is None
    assert video.thumbnail is None
    assert video.upload_date is None
    assert video.views is None


def test_stream_model_with_quality() -> None:
    """Test Stream model with quality and resolution fields."""
    stream = Stream(
        url="https://example.com/video.m3u8",
        format=StreamFormat.HLS,
        quality="1080",
        resolution="1920x1080",
        bitrate=4684000,
        width=1920,
        height=1080,
    )

    assert str(stream.url) == "https://example.com/video.m3u8"
    assert stream.format == StreamFormat.HLS
    assert stream.quality == "1080"
    assert stream.resolution == "1920x1080"
    assert stream.bitrate == 4684000
    assert stream.width == 1920
    assert stream.height == 1080


def test_stream_model_hls_format() -> None:
    """Test Stream model with HLS format."""
    stream = Stream(
        url="https://example.com/stream.m3u8",
        format=StreamFormat.HLS,
        quality="720",
    )

    assert stream.format == StreamFormat.HLS


def test_video_with_streams() -> None:
    """Test VideoWithStreams model combines Video and streams."""
    streams = [
        Stream(url="https://example.com/1080p.m3u8", format=StreamFormat.HLS, quality="1080"),
        Stream(url="https://example.com/720p.m3u8", format=StreamFormat.HLS, quality="720"),
    ]

    video = VideoWithStreams(
        id="12345_67890",
        title="Test Video",
        streams=streams,
    )

    assert video.id == "12345_67890"
    assert video.streams == streams
    assert len(video.streams) == 2


def test_download_progress_model() -> None:
    """Test DownloadProgress model tracks download state."""
    progress = DownloadProgress(
        video_id="12345_67890",
        downloaded_bytes=1024,
        total_bytes=2048,
        segments_downloaded=1,
        segments_total=2,
        status=DownloadStatus.DOWNLOADING,
    )

    assert progress.video_id == "12345_67890"
    assert progress.downloaded_bytes == 1024
    assert progress.total_bytes == 2048
    assert progress.segments_downloaded == 1
    assert progress.segments_total == 2
    assert progress.status == DownloadStatus.DOWNLOADING
    assert progress.error is None
