"""Data Transfer Objects for VK Video Downloader."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr


class HLSDownloadRequest(BaseModel):
    """Request model for HLS download with segment-level resume.

    Contains only pure data fields - no service dependencies.
    Service objects (settings, extractor, backoff_coordinator) are passed
    as function arguments to download_hls_with_resume.
    """

    video_url: str
    m3u8_url: str
    output_file: Path
    quality: str = "best"
    # SEC-008 (B7): this is the only in-process session carrier. It carries a
    # flat session string ("name=value; name=value") produced by
    # extractor._format_cookies_for_ffmpeg. Both markers are needed:
    # Field(repr=False) hides the field from repr()/str() entirely, and
    # SecretStr masks the value inside any rendering that does reach it.
    # repr=False alone leaves the value a plain str, so model_dump() and
    # model_dump_json() would emit the secret in clear, and a careless
    # logger.debug(cookies=request.cookies) would log the session in full --
    # sanitize_text_for_log is the identity on a flat session string (its
    # only rules match https?:// URLs and vk_cookies_* artefact literals),
    # so the B6 redaction processor cannot catch it.
    #
    # Hazards (do not trade SecretStr for repr=False, or for Secret):
    #   - model_dump() returns a SecretStr OBJECT, not a str. No
    #     model_dump / model_dump_json / json.dumps consumer of this model
    #     exists in src/ or tests/ today (verified by AST+regex scan) --
    #     but that is a property of the current tree, not a permanent
    #     guarantee. model_dump_json()'s '**********' masking is NOT stable
    #     across pydantic 2.x minors (pydantic's own SecretStr docstring
    #     shows the value in clear); the python-mode model_dump() behaviour
    #     is stable and is what would surprise a future consumer.
    #   - Equality silently breaks: SecretStr("a") == "a" is False. No site
    #     in src/ compares request.cookies to anything, but a future
    #     comparison would be wrong without raising.
    #   - SecretStr derives truthiness from __len__ (empty => False), which
    #     makes the existing `if request.cookies:` guard behave correctly.
    #     Secret (the Pydantic v1 alias) has no __len__ and would make that
    #     guard always-true, so SecretStr -- not Secret -- is required here.
    cookies: SecretStr | None = Field(default=None, repr=False)
    progress_callback: Callable[[str, int, int], None] | None = None
