"""VK Video Downloader - Download videos from vkvideo.ru with quality selection support."""

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("vkdownloader")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0+uninstalled"
