"""HLS playlist parsing and structural identity helpers."""

from __future__ import annotations

import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "HLSMediaSegment",
    "HLSMediaPlaylist",
    "HLSVariantIdentity",
    "UnsupportedHLSFeatureError",
    "parse_media_playlist",
    "parse_master_playlist",
    "compute_playlist_fingerprint",
    "normalize_segment_uri",
]


class UnsupportedHLSFeatureError(ValueError):
    """Raised when an HLS feature is not supported by this parser."""


class HLSMediaSegment(BaseModel):  # type: ignore[explicit-any]
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    sequence: int | None = None
    uri: str
    duration: float = 0.0
    byte_range: str | None = None
    byte_range_length: int | None = None
    byte_range_offset: int | None = None
    discontinuity: bool = False
    discontinuity_sequence: int = 0
    media_sequence: int | None = None
    init_map_uri: str | None = None
    init_map_identity: str | None = None
    key_method: str | None = None
    key_id: str | None = None

    @property
    def duration_seconds(self) -> float:
        return self.duration

    @property
    def url(self) -> str:
        return self.uri

    @property
    def init_map(self) -> str | None:
        return self.init_map_uri


class HLSVariantIdentity(BaseModel):  # type: ignore[explicit-any]
    model_config = ConfigDict(extra="forbid")

    variant_id: str
    uri: str
    bandwidth: int | None = None
    resolution: str | None = None
    codecs: str | None = None
    frame_rate: float | None = None
    audio_group: str | None = None

    @property
    def id(self) -> str:
        return self.variant_id

    @property
    def url(self) -> str:
        return self.uri


class HLSMediaPlaylist(BaseModel):  # type: ignore[explicit-any]
    model_config = ConfigDict(extra="forbid")

    media_sequence: int = 0
    discontinuity_sequence: int = 0
    target_duration: int | None = None
    version: int | None = None
    endlist: bool = False
    is_live: bool = False
    playlist_type: str | None = None
    independent_segments: bool = False
    segments: list[HLSMediaSegment] = Field(default_factory=list)
    init_map_uri: str | None = None
    init_map_identity: str | None = None
    codecs: str | None = None
    resolution: str | None = None
    key_method: str | None = None
    key_id: str | None = None

    @field_validator("segments", mode="before")
    @classmethod
    def _ensure_list(cls, value: object) -> object:
        return value if value is not None else []

    @property
    def init_map(self) -> str | None:
        return self.init_map_uri


_KNOWN_TAGS = {
    "EXTM3U",
    "EXT-X-VERSION",
    "EXT-X-TARGETDURATION",
    "EXT-X-MEDIA-SEQUENCE",
    "EXT-X-DISCONTINUITY",
    "EXT-X-DISCONTINUITY-SEQUENCE",
    "EXT-X-MAP",
    "EXT-X-BYTERANGE",
    "EXT-X-KEY",
    "EXT-X-ENDLIST",
    "EXT-X-PLAYLIST-TYPE",
    "EXT-X-INDEPENDENT-SEGMENTS",
    "EXTINF",
}


def _parse_attr_list(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    # Parse KEY=VALUE or KEY="VALUE" pairs.
    for match in re.finditer(r'([A-Z0-9-]+)=(?:"([^"]*)"|([^,]*))', text):
        key = match.group(1)
        value = match.group(2) if match.group(2) is not None else match.group(3)
        result[key] = value.strip() if value is not None else ""
    return result


def _strip_query(uri: str) -> str:
    parts = urlsplit(uri)
    return parts._replace(query="", fragment="").geturl()


def _init_map_identity(uri: str) -> str:
    return _strip_query(uri)


def parse_media_playlist(text: str, *, base_url: str | None = None) -> HLSMediaPlaylist:
    lines = [line.strip() for line in text.splitlines()]
    media_sequence = 0
    discontinuity_sequence = 0
    target_duration = None
    version = None
    endlist = False
    playlist_type = None
    independent_segments = False
    init_map_uri = None
    key_method = None
    key_id = None
    segments: list[HLSMediaSegment] = []
    current_duration = 0.0
    current_discontinuity = False
    pending_byterange: str | None = None
    index = 0
    discontinuity_counter = 0

    for raw in lines:
        if not raw:
            continue
        if raw.startswith("#"):
            if raw.startswith("#EXT-X-"):
                tag = raw[len("#") :].split(":", 1)[0]
                if tag not in _KNOWN_TAGS and tag != "EXT-X-MAP":
                    # EXT-X-MAP already in known; unknown tags rejected.
                    if tag not in _KNOWN_TAGS:
                        raise UnsupportedHLSFeatureError(f"unsupported HLS tag: {tag}")
            if raw.startswith("#EXT-X-VERSION:"):
                version = int(raw.split(":", 1)[1].strip())
            elif raw.startswith("#EXT-X-TARGETDURATION:"):
                target_duration = int(raw.split(":", 1)[1].strip())
            elif raw.startswith("#EXT-X-MEDIA-SEQUENCE:"):
                media_sequence = int(raw.split(":", 1)[1].strip())
            elif raw.startswith("#EXT-X-DISCONTINUITY-SEQUENCE:"):
                discontinuity_sequence = int(raw.split(":", 1)[1].strip())
                discontinuity_counter = discontinuity_sequence
            elif raw.startswith("#EXT-X-DISCONTINUITY"):
                current_discontinuity = True
            elif raw.startswith("#EXT-X-MAP:"):
                attrs = _parse_attr_list(raw.split(":", 1)[1])
                uri = attrs.get("URI")
                if not uri:
                    raise UnsupportedHLSFeatureError("EXT-X-MAP without URI")
                if base_url:
                    uri = urljoin(base_url, uri)
                init_map_uri = uri
            elif raw.startswith("#EXT-X-BYTERANGE:"):
                pending_byterange = raw.split(":", 1)[1].strip()
            elif raw.startswith("#EXT-X-KEY:"):
                attrs = _parse_attr_list(raw.split(":", 1)[1])
                method = (attrs.get("METHOD") or "").upper()
                if method and method != "NONE":
                    # Encryption (with or without key material) is rejected.
                    raise UnsupportedHLSFeatureError(f"unsupported HLS encryption method: {method}")
                key_method = method or "NONE"
                key_id = attrs.get("KEYID")
            elif raw.startswith("#EXT-X-ENDLIST"):
                endlist = True
            elif raw.startswith("#EXT-X-PLAYLIST-TYPE:"):
                playlist_type = raw.split(":", 1)[1].strip()
            elif raw.startswith("#EXT-X-INDEPENDENT-SEGMENTS"):
                independent_segments = True
            elif raw.startswith("#EXTINF:"):
                # #EXTINF:duration[,title]
                payload = raw[len("#EXTINF:") :].strip()
                duration_part = payload.split(",", 1)[0].strip()
                try:
                    current_duration = float(duration_part)
                except ValueError:
                    current_duration = 0.0
            # Unknown EXT-X tag check.
            elif raw.startswith("#EXT-X-"):
                tag = raw[len("#") :].split(":", 1)[0]
                if tag not in _KNOWN_TAGS:
                    raise UnsupportedHLSFeatureError(f"unsupported HLS tag: {tag}")
            continue
        else:
            # segment URI line
            if raw.startswith("#"):
                continue
            uri = raw
            if base_url:
                uri = urljoin(base_url, uri)
            byte_range = pending_byterange
            br_length = None
            br_offset = None
            if byte_range:
                if "@" in byte_range:
                    length_part, offset_part = byte_range.split("@", 1)
                    br_length = int(length_part)
                    br_offset = int(offset_part)
                else:
                    br_length = int(byte_range)
            segment_discontinuity = current_discontinuity
            seg_disc_seq = discontinuity_counter
            if current_discontinuity:
                discontinuity_counter += 1
            current_discontinuity = False
            seg_media_sequence = media_sequence + index if media_sequence is not None else None

            init_identity = _init_map_identity(init_map_uri) if init_map_uri else None
            segment = HLSMediaSegment(
                index=index,
                sequence=index,
                uri=uri,
                duration=current_duration,
                byte_range=byte_range,
                byte_range_length=br_length,
                byte_range_offset=br_offset,
                discontinuity=segment_discontinuity,
                discontinuity_sequence=seg_disc_seq,
                media_sequence=seg_media_sequence,
                init_map_uri=init_map_uri,
                init_map_identity=init_identity,
                key_method=key_method,
                key_id=key_id,
            )
            segments.append(segment)
            index += 1
            pending_byterange = None
            current_duration = 0.0

    is_live = not endlist

    # Live ambiguity guard: if playlist is live (no ENDLIST), it is not a fixed VOD.
    # We do not raise here; callers must handle is_live. But if media sequence is
    # missing for a live playlist, mark ambiguous? Keep permissive.

    init_identity = _init_map_identity(init_map_uri) if init_map_uri else None
    playlist = HLSMediaPlaylist(
        media_sequence=media_sequence or 0,
        discontinuity_sequence=discontinuity_sequence or discontinuity_counter,
        target_duration=target_duration,
        version=version,
        endlist=endlist,
        is_live=is_live,
        playlist_type=playlist_type,
        independent_segments=independent_segments,
        segments=segments,
        init_map_uri=init_map_uri,
        init_map_identity=init_identity,
        codecs=None,
        resolution=None,
        key_method=key_method,
        key_id=key_id,
    )
    return playlist


def parse_master_playlist(text: str, *, base_url: str | None = None) -> list[HLSVariantIdentity]:
    lines = [line.strip() for line in text.splitlines()]
    variants: list[HLSVariantIdentity] = []
    i = 0
    variant_index = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXT-X-STREAM-INF:"):
            attrs = _parse_attr_list(line.split(":", 1)[1])
            bandwidth = None
            if attrs.get("BANDWIDTH"):
                try:
                    bandwidth = int(attrs["BANDWIDTH"])
                except ValueError:
                    bandwidth = None
            resolution = attrs.get("RESOLUTION")
            codecs = attrs.get("CODECS")
            frame_rate = None
            if attrs.get("FRAME-RATE"):
                try:
                    frame_rate = float(attrs["FRAME-RATE"])
                except ValueError:
                    frame_rate = None
            # find next non-empty, non-comment URI
            j = i + 1
            while j < len(lines) and (not lines[j] or lines[j].startswith("#")):
                j += 1
            if j >= len(lines):
                raise UnsupportedHLSFeatureError("master playlist variant missing URI")
            uri = lines[j]
            if base_url:
                uri = urljoin(base_url, uri)
            variant_id = f"{resolution or 'unknown'}:{codecs or 'unknown'}:{bandwidth or 0}"
            # ensure uniqueness
            existing_ids = {v.variant_id for v in variants}
            if variant_id in existing_ids:
                variant_id = f"{variant_id}:{variant_index}"
            variants.append(
                HLSVariantIdentity(
                    variant_id=variant_id,
                    uri=uri,
                    bandwidth=bandwidth,
                    resolution=resolution,
                    codecs=codecs,
                    frame_rate=frame_rate,
                )
            )
            variant_index += 1
            i = j
        i += 1
    return variants


def normalize_segment_uri(uri: str, base_url: str | None = None) -> str:
    if base_url:
        return urljoin(base_url, uri)
    return uri


def compute_playlist_fingerprint(*args: object, **kwargs: object) -> str:
    """Compute a structural fingerprint excluding URLs and tokens."""
    variant = kwargs.get("variant") or kwargs.get("variant_identity")
    playlist = kwargs.get("playlist") or kwargs.get("media_playlist")
    for arg in args:
        if isinstance(arg, HLSMediaPlaylist):
            playlist = arg
        elif isinstance(arg, HLSVariantIdentity):
            variant = arg
        elif isinstance(arg, str):
            # Could be variant_id; store separately.
            if kwargs.get("_variant_id_str") is None:
                kwargs["_variant_id_str"] = arg

    variant_id = (
        kwargs.get("variant_id") or kwargs.get("stream_variant_id") or kwargs.get("_variant_id_str")
    )
    codecs = kwargs.get("codecs")
    resolution = kwargs.get("resolution")

    if isinstance(variant, HLSVariantIdentity):
        variant_id = variant_id or variant.variant_id
        codecs = codecs if codecs is not None else variant.codecs
        resolution = resolution if resolution is not None else variant.resolution
    elif isinstance(variant, str):
        variant_id = variant_id or variant

    if variant_id is None:
        variant_id = "unknown"

    # Media playlist fields.
    media_sequence = 0
    discontinuity_sequence = 0
    target_duration = None
    version = None
    init_map_identity = None
    endlist = False
    is_live = False
    segments_data = []
    if isinstance(playlist, HLSMediaPlaylist):
        media_sequence = playlist.media_sequence
        discontinuity_sequence = playlist.discontinuity_sequence
        target_duration = playlist.target_duration
        version = playlist.version
        init_map_identity = playlist.init_map_identity
        endlist = playlist.endlist
        is_live = playlist.is_live
        codecs = codecs if codecs is not None else playlist.codecs
        resolution = resolution if resolution is not None else playlist.resolution
        for seg in playlist.segments:
            segments_data.append(
                (
                    seg.index,
                    seg.duration,
                    seg.byte_range,
                    seg.byte_range_length,
                    seg.byte_range_offset,
                    seg.discontinuity,
                    seg.discontinuity_sequence,
                    seg.media_sequence,
                    seg.init_map_identity,
                    seg.key_method,
                    seg.key_id,
                )
            )
    else:
        # Allow passing segments list via kwargs.
        segs = kwargs.get("segments")
        if isinstance(segs, (list, tuple)):
            for idx, seg in enumerate(segs):
                if hasattr(seg, "duration"):
                    segments_data.append(
                        (  # type: ignore[arg-type]
                            idx,
                            getattr(seg, "duration", None),
                            getattr(seg, "byte_range", None),
                            getattr(seg, "byte_range_length", None),
                            getattr(seg, "byte_range_offset", None),
                            getattr(seg, "discontinuity", False),
                            getattr(seg, "discontinuity_sequence", 0),
                            getattr(seg, "media_sequence", None),
                            getattr(seg, "init_map_identity", None),
                            getattr(seg, "key_method", None),
                            getattr(seg, "key_id", None),
                        )
                    )
                else:
                    segments_data.append(
                        (
                            idx,
                            getattr(seg, "duration", 0.0) if hasattr(seg, "duration") else 0.0,
                            None,
                            None,
                            None,
                            False,
                            0,
                            None,
                            None,
                            None,
                            None,
                        )
                    )

    structural = {
        "variant_id": variant_id,
        "codecs": codecs,
        "resolution": resolution,
        "target_duration": target_duration,
        "version": version,
        "media_sequence": media_sequence,
        "discontinuity_sequence": discontinuity_sequence,
        "init_map_identity": init_map_identity,
        "endlist": endlist,
        "is_live": is_live,
        "segments": segments_data,
    }
    serialized = json.dumps(structural, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
