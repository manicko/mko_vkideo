"""Services package for VK Video Downloader."""

from .downloader import HLSDownloader
from .quality import QualitySelector

__all__ = ["HLSDownloader", "QualitySelector"]
