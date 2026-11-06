"""Exact-quality stream binding and refresh helpers (Block F)."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import QualityMismatchError, QualityNotAvailableError
from ..models.quality import QualitySpec
from ..models.video import Stream
from .hls_parser import HLSVariantIdentity
from .quality import QualitySelector


@dataclass(frozen=True)
class StreamBinding:
    """A frozen, validated binding to one exact stream variant.

    ``media_playlist_url`` and ``cookies`` are sensitive and must never be
    logged or serialized.
    """

    media_playlist_url: str
    requested_quality: str
    actual_height: int | None = None
    variant_id: str = ""
    codecs: str | None = None
    cookies: object = None
    width: int | None = None
    raw_cookies: object = None
    height_verified: bool = False


def _candidate_height(candidate: object) -> int | None:
    height = getattr(candidate, "height", None)
    if isinstance(height, int):
        return height
    resolution = getattr(candidate, "resolution", None)
    if isinstance(resolution, str) and "x" in resolution:
        try:
            return int(resolution.rsplit("x", 1)[-1])
        except ValueError:
            return None
    return None


def _candidate_quality(candidate: object) -> str:
    quality = getattr(candidate, "quality", None)
    if isinstance(quality, str) and quality:
        return quality
    height = _candidate_height(candidate)
    if height is not None:
        return f"{height}p"
    return "unknown"


def _candidate_url(candidate: object) -> str:
    for attr in ("url", "uri", "media_playlist_url"):
        value = getattr(candidate, attr, None)
        if isinstance(value, str) and value:
            return value
    return ""


def _parse_requested_height(requested_quality: str) -> int | None:
    token = requested_quality.strip()
    if token.lower() in ("best", "worst"):
        return None
    if token.lower() == "unknown":
        return None
    if token.endswith(("p", "P")):
        token = token[:-1]
    if token.isdecimal():
        return int(token)
    return None


def select_exact_or_fail(candidates: list[object], requested_quality: str) -> object:
    """Select an exact stream or raise.

    Exact numeric requests require a verified matching height; browser-captured
    streams with an unknown/missing height are rejected. Ambiguous matches raise
    ``QualityMismatchError``.
    """
    requested = str(requested_quality).strip()
    available = [_candidate_quality(c) for c in candidates]

    rq = requested.lower()
    if rq in ("best", "worst"):
        quality_spec = QualitySpec.parse(requested)
        return QualitySelector().select(list(candidates), quality_spec)  # type: ignore[arg-type]

    if rq == "unknown":
        matches = [c for c in candidates if _candidate_quality(c).lower() == "unknown"]
        if not matches:
            raise QualityMismatchError(
                "Exact quality is unavailable or unverified",
                requested=requested,
                available=available,
                actual_height=None,
            )
        if len(matches) > 1:
            raise QualityMismatchError(
                "Ambiguous exact quality match",
                requested=requested,
                available=available,
                actual_height=None,
            )
        return matches[0]

    requested_height = _parse_requested_height(requested)
    if requested_height is None:
        # Fall back to label-based exact matching.
        quality_spec = QualitySpec.parse(
            requested if requested.lower().endswith("p") else f"{requested}p"
        )
        match = None
        for c in candidates:
            if quality_spec.matches(_candidate_quality(c)):
                match = c
                break
        if match is None:
            raise QualityMismatchError(
                "Exact quality is unavailable or unverified",
                requested=requested,
                available=available,
                actual_height=None,
            )
        return match

    exact_matches = [c for c in candidates if _candidate_height(c) == requested_height]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise QualityMismatchError(
            "Ambiguous exact quality match",
            requested=requested,
            available=available,
            actual_height=requested_height,
        )

    # No exact height match: reject unverified/unknown captures explicitly.
    unverified = [
        c
        for c in candidates
        if _candidate_height(c) is None
        or (_candidate_height(c) or 0) <= 0
        or _candidate_quality(c).lower() == "unknown"
    ]
    if unverified:
        raise QualityMismatchError(
            "Exact quality is unavailable or unverified",
            requested=requested,
            available=available,
            actual_height=_candidate_height(unverified[0]),
        )

    raise QualityMismatchError(
        "Exact quality is unavailable or unverified",
        requested=requested,
        available=available,
        actual_height=None,
    )


def binding_from_selected(
    selected: object,
    *,
    requested_quality: str | None = None,
    cookies: object = None,
    raw_cookies: object = None,
) -> StreamBinding:
    """Map a Stream or HLSVariantIdentity into a StreamBinding."""
    if isinstance(selected, HLSVariantIdentity):
        uri = selected.uri
        codecs = selected.codecs
        resolution = selected.resolution
        height = None
        if isinstance(resolution, str) and "x" in resolution:
            try:
                height = int(resolution.rsplit("x", 1)[-1])
            except ValueError:
                height = None
        if requested_quality is None:
            requested_quality = f"{height}p" if height is not None else selected.variant_id
        width = None
        if isinstance(resolution, str) and "x" in resolution:
            try:
                width = int(resolution.split("x", 1)[0])
            except ValueError:
                width = None
        variant_id = selected.variant_id
    elif isinstance(selected, Stream):
        uri = selected.url
        codecs = getattr(selected, "codecs", None)
        resolution = getattr(selected, "resolution", None)
        height = getattr(selected, "height", None)
        width = getattr(selected, "width", None)
        if requested_quality is None:
            requested_quality = getattr(selected, "quality", None) or (
                f"{height}p" if height is not None else "unknown"
            )
        variant_id = f"{codecs}:{resolution or height}"
    else:
        uri = _candidate_url(selected)
        codecs = getattr(selected, "codecs", None)
        resolution = getattr(selected, "resolution", None)
        height = _candidate_height(selected)
        width = getattr(selected, "width", None)
        if requested_quality is None:
            requested_quality = _candidate_quality(selected)
        variant_id = getattr(selected, "variant_id", None) or f"{codecs}:{resolution or height}"

    if requested_quality is None:
        requested_quality = "unknown"

    requested_str = str(requested_quality)
    height_verified = False
    if requested_str.isdecimal():
        try:
            height_verified = height is not None and height == int(requested_str)
        except ValueError:
            height_verified = False
    else:
        height_verified = True

    return StreamBinding(
        media_playlist_url=uri,
        requested_quality=requested_str,
        actual_height=height,
        variant_id=variant_id or "",
        codecs=codecs,
        cookies=cookies,
        width=width,
        raw_cookies=raw_cookies,
        height_verified=height_verified,
    )


async def refresh_stream(
    original_vk_url: str,
    requested_quality: str,
    previous: object,
    extractor: object,
) -> StreamBinding:
    """Refresh a stream binding, preserving the exact requested quality."""
    previous_cookies = getattr(previous, "cookies", None) if previous is not None else None
    previous_raw = getattr(previous, "raw_cookies", None) if previous is not None else None

    settings = getattr(extractor, "settings", None)
    cookie_source = getattr(settings, "cookie_source", None)
    try:
        from ..models.enums import CookieSource

        use_browser = (
            cookie_source == CookieSource.BROWSER
            or previous_cookies is not None
            or previous_raw is not None
        )
    except Exception:  # noqa: BLE001
        use_browser = previous_cookies is not None or previous_raw is not None

    if use_browser:
        extract_with_cookies = getattr(extractor, "extract_streams_with_cookies", None)
        if extract_with_cookies is None:
            raise RuntimeError("extractor missing extract_streams_with_cookies")
        streams, cookies, raw_cookies = await extract_with_cookies(
            original_vk_url, force_browser=True
        )
    else:
        extract_streams = getattr(extractor, "extract_streams", None)
        if extract_streams is None:
            raise RuntimeError("extractor missing extract_streams")
        vws = await extract_streams(original_vk_url)
        streams = getattr(vws, "streams", vws)
        cookies = None
        raw_cookies = None

    if not streams:
        raise QualityNotAvailableError(
            str(requested_quality),
            [],
            "No streams found after extraction",
        )

    selected = select_exact_or_fail(list(streams), requested_quality)
    binding = binding_from_selected(
        selected,
        requested_quality=requested_quality,
        cookies=cookies if cookies is not None else previous_cookies,
        raw_cookies=raw_cookies if raw_cookies is not None else previous_raw,
    )

    requested_str = str(requested_quality).strip()
    if requested_str.isdecimal():
        if binding.actual_height is None or binding.actual_height <= 0:
            raise QualityMismatchError(
                "Exact quality is unavailable or unverified",
                requested=requested_str,
                available=[_candidate_quality(s) for s in streams],
                actual_height=binding.actual_height,
            )
        if binding.actual_height != int(requested_str):
            raise QualityMismatchError(
                "Exact quality is unavailable or unverified",
                requested=requested_str,
                available=[_candidate_quality(s) for s in streams],
                actual_height=binding.actual_height,
            )

    return binding
