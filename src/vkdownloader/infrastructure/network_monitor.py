"""Network monitoring infrastructure for VK Video Downloader."""

import json
import re
from enum import StrEnum
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from playwright.async_api import Page, Response
from structlog import get_logger

from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


# Type alias for JSON values (recursive structure)
type JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None


# HLS playlist tags for media-over-master classification (B7).
# Master playlists carry variant references; media playlists carry segments.
_MASTER_PLAYLIST_TAGS = ("#EXT-X-STREAM-INF", "#EXT-X-I-FRAME-STREAM-INF")
_MEDIA_PLAYLIST_TAG = "#EXT-X-PLAYLIST-TYPE"


class _PlaylistType(StrEnum):
    """Module-private three-valued rank for media-over-master classification (B7).

    A rank only — it never filters captured addresses. Media playlists carry
    segment lists and are preferred; master manifests list variant references
    and are ranked last by ``select()``. Re-exported nowhere: this is a
    capture-time detail of ``NetworkMonitor``, not product vocabulary.
    """

    MEDIA = "media"
    UNCLASSIFIED = "unclassified"
    MASTER = "master"


class NetworkMonitor:
    """Monitors network traffic to capture m3u8 URLs from responses."""

    M3U8_PATTERN = re.compile(r"(?:https?://)?[^\s\"'<>]+\.m3u8(?:\?[^\s\"'<>]*)?")
    # Maximum response body size (in bytes) to parse for m3u8 URLs
    MAX_JSON_BODY_BYTES: int = 1_000_000

    # NET-008: Host allowlist — only addresses whose host is a first-party
    # VK Video domain or a subdomain thereof may be selected. A full URL
    # match (``host == suffix``) covers the apex; the dotted form covers
    # subdomains (``cdn.vkvideo.ru``). The allowlist is a tuple so it is
    # immutable and ordered for deterministic iteration.
    ALLOWED_HOST_SUFFIXES: tuple[str, ...] = (
        "vkvideo.ru",
        "vk.com",
    )

    def __init__(self, page: Page) -> None:
        """
        Initialize NetworkMonitor with a Playwright page.

        Args:
            page: Playwright Page instance to monitor network traffic for.
        """
        self.page = page
        self.m3u8_urls: list[str] = []
        self._playlist_types: dict[str, _PlaylistType] = {}
        self._hls_filter_suspended_logged: bool = False
        self._host_filter_suspended_logged: bool = False
        self._setup_interceptors()

    def _setup_interceptors(self) -> None:
        """Set up response interceptors for m3u8 detection."""
        logger.debug("setting_up_network_interceptors")
        self.page.on("response", self._intercept_response)

    def _normalize_url(self, url: str) -> str | None:
        """Classify an m3u8 address candidate; return its absolute https URL or None."""
        url = url.strip()
        if url.startswith("https://"):
            return url
        # D-14 (NET-016): Two rulings. (1) http:// is dropped, not carried
        # forward in plaintext — the sole consumer guards emptiness
        # (`if monitor.m3u8_urls:`) before indexing m3u8_urls[0], so an
        # http:// address is no longer discovered. (2) root-relative and
        # bare-relative candidates are dropped, not resolved against
        # page.url. The constructor holds a Page, so resolving would need no
        # signature change — which is exactly why the rejection matters: it
        # would invent a plausible-looking wrong host, the same failure class
        # this block removes. Rejected alternative: resolve against page.url.
        # A schemeless candidate is promoted only when its first component
        # looks like a host (contains a dot) AND it has a path; schemeless
        # hosts without a dot (intranet/stream.m3u8) and bare filenames
        # (stream.m3u8) are dropped — conservative, never wrong.
        if url.startswith("http://"):
            return None
        # scheme-relative is promoted before root-relative, so //host is not
        # swallowed by the / arm and dropped.
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("/"):
            return None
        head, sep, _ = url.partition("/")
        if sep and "." in head:
            return f"https://{url}"
        return None

    def _classify_hls(self, address: str) -> bool:
        """Classify an m3u8 address candidate as HLS (True) or non-HLS (False).

        NET-008: This is a deliberate local duplicate of
        ``extractor._classify_format``. The ``infrastructure`` layer cannot
        import upward into ``services.extractor``; importing would create a
        forbidden upward dependency edge. The suffix logic must agree with
        ``extractor._classify_format`` to keep the two parse sites from
        drifting. If this method changes, update
        ``extractor._classify_format`` in lockstep (NET-008).
        """
        try:
            path = urlsplit(address).path
        except ValueError:
            return False
        suffix = PurePosixPath(path).suffix.lower()
        return suffix == ".m3u8"

    def _is_allowed_host(self, address: str) -> bool:
        """Check whether an address's host is a first-party VK Video domain.

        NET-008: Constrains the selection surface to addresses whose host
        is an entry in ``ALLOWED_HOST_SUFFIXES`` or a subdomain thereof.
        A foreign origin whose URL ends in ``.m3u8`` — for example an
        ad-tracker or analytics host — is rejected so it cannot become
        the source handed to the downloader. ``urlsplit`` raising
        ``ValueError`` falls through to ``False`` (rejected).

        Args:
            address: An m3u8 address candidate.

        Returns:
            True if the host is allowed, False otherwise.
        """
        try:
            host = urlsplit(address).netloc
        except ValueError:
            return False
        if not host:
            return False
        host = host.lower()
        return any(
            host == suffix or host.endswith(f".{suffix}") for suffix in self.ALLOWED_HOST_SUFFIXES
        )

    def _classify_playlist(self, body: bytes | None) -> _PlaylistType:
        """Three-valued media-over-master rank from a playlist response body.

        B7: Inspects the raw body bytes for HLS playlist tags. This is a rank
        only — it never filters addresses. Media playlists (containing
        ``#EXT-X-PLAYLIST-TYPE``) carry segment lists for a single variant
        and are ranked first by ``select()``. Master manifests (containing
        ``#EXT-X-STREAM-INF`` or ``#EXT-X-I-FRAME-STREAM-INF``) list variant
        references only and are ranked last. Absence of both yields
        ``UNCLASSIFIED``.
        """
        if body is None:
            return _PlaylistType.UNCLASSIFIED
        try:
            text = body.decode("utf-8", errors="replace")
        except UnicodeDecodeError, AttributeError:
            return _PlaylistType.UNCLASSIFIED
        if any(tag in text for tag in _MASTER_PLAYLIST_TAGS):
            return _PlaylistType.MASTER
        if _MEDIA_PLAYLIST_TAG in text:
            return _PlaylistType.MEDIA
        return _PlaylistType.UNCLASSIFIED

    def _rank_playlist(self, url: str) -> int:
        """Numeric rank for sorting: media (0) < unclassified (1) < master (2).

        Media playlists carry segment lists and are the optimal download
        entry point. Master manifests list variant references only and have
        no segments on their own; they are ranked last. ``sorted()`` is
        stable (PEP 1741), so addresses with equal rank retain their
        arrival order, yielding a total ordering as required.
        """
        playlist_type = self._playlist_types.get(url, _PlaylistType.UNCLASSIFIED)
        if playlist_type == _PlaylistType.MEDIA:
            return 0
        if playlist_type == _PlaylistType.MASTER:
            return 2
        return 1

    async def _read_bounded_body(self, response: Response) -> bytes | None:
        """Read a response body capped at MAX_JSON_BODY_BYTES.

        B7: Reuses ``MAX_JSON_BODY_BYTES`` as the bound for the bounded body
        read used in media-over-master classification. Returns ``None`` on any
        read error so the caller falls through to ``UNCLASSIFIED``.
        """
        try:
            body = await response.body()
        except Exception as e:
            logger.debug(
                "playlist_body_read_error",
                url=_strip_auth_params(response.url),
                error=str(e.__class__.__name__),
            )
            return None
        if len(body) > self.MAX_JSON_BODY_BYTES:
            return body[: self.MAX_JSON_BODY_BYTES]
        return body

    def _log_suspension(self, captured: list[str]) -> None:
        """Log an HLS-filter suspension event exactly once, with reason and hosts."""
        self._hls_filter_suspended_logged = True
        try:
            hosts = sorted({urlsplit(addr).netloc for addr in captured if urlsplit(addr).netloc})
        except Exception:
            hosts = []
        logger.warning(
            "hls_filter_suspended",
            reason="all_addresses_non_hls",
            hosts=hosts,
            count=len(captured),
        )

    def _log_host_suspension(self, dropped: list[str]) -> None:
        """Log a host-filter suspension event exactly once, with reason and hosts.

        NET-008: When every captured address is from a non-VK host, the host
        filter is suspended and the unconstrained set is returned instead, with
        a single warning logged. The suspension mirrors the HLS-filter
        suspension: it is a safety valve for test environments or unusual
        deployments, not an acceptance that third-party hosts are safe — the
        warning names every dropped host so the operator can see the risk.
        """
        self._host_filter_suspended_logged = True
        try:
            hosts = sorted({urlsplit(addr).netloc for addr in dropped if urlsplit(addr).netloc})
        except Exception:
            hosts = []
        logger.warning(
            "host_filter_suspended",
            reason="all_addresses_non_vk",
            hosts=hosts,
            count=len(dropped),
        )

    def select(self) -> list[str]:
        """Select captured m3u8 addresses with an HLS-only filter and host allowlist.

        NET-008: Two constraints are applied before ranking:
        1. **Host allowlist** — only addresses whose host is a first-party
           VK Video domain (``vkvideo.ru``, ``vk.com``) or a subdomain
           thereof are admitted. A foreign origin whose URL ends in
           ``.m3u8`` is dropped before it can become the delivered source.
        2. **HLS-only filter** — path suffix ``.m3u8``; addresses with ``.m3u8``
           only in a directory name are rejected.

        If the host filter would reject every captured address, it is
        suspended and the unconstrained set is returned, with a single
        warning logged — mirroring the HLS-filter suspension. This is a
        safety valve for test or deployment environments, not an acceptance
        that third-party hosts are safe.

        Addresses are then ranked media-over-master: media playlists
        (carrying segment lists) come first, master manifests (variant
        references only) last, ties broken by arrival order (``sorted`` is
        stable per PEP 1741).

        Exception totality (B7): this method never raises. All classification
        is wrapped so that a malformed address falls through to acceptance
        rather than propagating an exception to the caller.
        """
        try:
            captured = list(self.m3u8_urls)
            if not captured:
                return []

            # NET-008: host allowlist — drop addresses from foreign origins.
            host_allowed: list[str] = []
            host_dropped: list[str] = []
            for addr in captured:
                if self._is_allowed_host(addr):
                    host_allowed.append(addr)
                else:
                    host_dropped.append(addr)
            if not host_allowed:
                if not self._host_filter_suspended_logged:
                    self._log_host_suspension(host_dropped)
                # Suspension: return the unconstrained set, ranked best-effort.
                return sorted(captured, key=self._rank_playlist)

            # B7: HLS-only filter — prefer `.m3u8` path suffix.
            hls_only: list[str] = []
            for addr in host_allowed:
                if self._classify_hls(addr):
                    hls_only.append(addr)
                else:
                    # B7: log every rejected candidate with its host and
                    # the rejection reason (host is logged only, not filtered).
                    try:
                        host = urlsplit(addr).netloc or "unknown"
                    except Exception:
                        host = "unknown"
                    logger.debug(
                        "hls_filter_rejected",
                        url=_strip_auth_params(addr),
                        host=host,
                        reason="path_suffix_not_m3u8",
                    )

            if not hls_only:
                if not self._hls_filter_suspended_logged:
                    self._log_suspension(host_allowed)
                # Suspension: return the unconstrained set, ranked best-effort.
                return sorted(host_allowed, key=self._rank_playlist)

            return sorted(hls_only, key=self._rank_playlist)
        except Exception as e:
            logger.warning(
                "hls_select_error",
                error=str(e.__class__.__name__),
                fallback="returning_unconstrained_set",
            )
            return list(self.m3u8_urls)

    async def _intercept_response(self, response: Response) -> None:
        """
        Intercept network responses and capture m3u8 URLs.

        Args:
            response: Playwright Response object.
        """
        url = response.url
        # Detect m3u8 candidate URLs in the response address (direct and
        # JSON-body paths are both handled here).
        if ".m3u8" in url.lower() or self.M3U8_PATTERN.search(url):
            normalized = self._normalize_url(url)
            if normalized is not None:
                if normalized not in self.m3u8_urls:
                    self.m3u8_urls.append(normalized)
                    # B7: classify playlist type from the response body
                    # for media-over-master ranking (rank only, never a filter).
                    body = await self._read_bounded_body(response)
                    self._playlist_types[normalized] = self._classify_playlist(body)
                    logger.debug(
                        "m3u8_url_captured",
                        url=_strip_auth_params(normalized),
                        host=urlsplit(normalized).netloc or "unknown",
                        playlist_type=self._playlist_types[normalized],
                    )
                else:
                    logger.debug(
                        "m3u8_url_captured",
                        url=_strip_auth_params(normalized),
                        host=urlsplit(normalized).netloc or "unknown",
                    )

        # Also check for XHR responses containing stream URLs
        if "video" in url and response.headers.get("content-type", "").startswith(
            "application/json"
        ):
            # Guard: skip oversized JSON bodies to avoid memory issues
            content_length = response.headers.get("content-length")
            if content_length is not None:
                try:
                    size_bytes = int(content_length)
                    if size_bytes >= self.MAX_JSON_BODY_BYTES:
                        logger.debug(
                            "skipping_oversized_json_response",
                            url=_strip_auth_params(url),
                            size=size_bytes,
                        )
                        return
                except ValueError:
                    pass  # Invalid content-length header, fall through to body check

            # The byte cap below bounds PARSING work (json.loads), not memory:
            # Playwright's Response.body() is all-or-nothing and cannot be
            # partially read, so on the chunked/streamed path (no
            # Content-Length, or an unparseable one) the entire body is
            # materialised before the cap is consulted (NET-011).
            try:
                body = await response.body()
            except Exception as e:
                logger.warning(
                    "response_body_error",
                    url=_strip_auth_params(url),
                    error=str(e.__class__.__name__),
                )
                return

            if len(body) >= self.MAX_JSON_BODY_BYTES:
                logger.debug(
                    "skipping_oversized_json_response",
                    url=_strip_auth_params(url),
                    size=len(body),
                )
                return

            try:
                data = json.loads(body)
                self._extract_urls_from_json(data)
            except json.JSONDecodeError:
                logger.warning(
                    "json_parse_error",
                    url=_strip_auth_params(url),
                    reason="invalid_json_in_response",
                )
            except Exception as e:
                logger.warning(
                    "response_json_error",
                    url=_strip_auth_params(url),
                    error=str(e.__class__.__name__),
                )

    def _extract_urls_from_json(self, data: JsonValue) -> None:
        """
        Recursively extract m3u8 URLs from JSON data.

        Args:
            data: JSON data to search for m3u8 URLs.
        """
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str) and ".m3u8" in value.lower():
                    normalized = self._normalize_url(value)
                    if normalized is not None and normalized not in self.m3u8_urls:
                        self.m3u8_urls.append(normalized)
                        # JSON-extracted URLs have no fetched playlist body
                        # yet, so they default to UNCLASSIFIED.
                        self._playlist_types[normalized] = _PlaylistType.UNCLASSIFIED
                        logger.debug(
                            "m3u8_url_found_in_json",
                            url=_strip_auth_params(normalized),
                            host=urlsplit(normalized).netloc or "unknown",
                        )
                elif isinstance(value, (dict, list)):
                    self._extract_urls_from_json(value)
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item)
