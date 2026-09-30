"""Network monitoring infrastructure for VK Video Downloader."""

import json
import re
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from playwright.async_api import Page, Response
from structlog import get_logger

from ..models.enums import PlaylistType
from ..utils.url_sanitizer import _strip_auth_params

logger = get_logger(__name__)


# Type alias for JSON values (recursive structure)
type JsonValue = dict[str, "JsonValue"] | list["JsonValue"] | str | int | float | bool | None


# HLS playlist tags for media-over-master classification (B7).
# Master playlists carry variant references; media playlists carry segments.
_MASTER_PLAYLIST_TAGS = ("#EXT-X-STREAM-INF", "#EXT-X-I-FRAME-STREAM-INF")
_MEDIA_PLAYLIST_TAG = "#EXT-X-PLAYLIST-TYPE"


class NetworkMonitor:
    """Monitors network traffic to capture m3u8 URLs from responses."""

    M3U8_PATTERN = re.compile(r"(?:https?://)?[^\s\"'<>]+\.m3u8(?:\?[^\s\"'<>]*)?")
    # Maximum response body size (in bytes) to parse for m3u8 URLs
    MAX_JSON_BODY_BYTES: int = 1_000_000

    def __init__(self, page: Page) -> None:
        """
        Initialize NetworkMonitor with a Playwright page.

        Args:
            page: Playwright Page instance to monitor network traffic for.
        """
        self.page = page
        self.m3u8_urls: list[str] = []
        self._playlist_types: dict[str, PlaylistType] = {}
        self._hls_filter_suspended_logged: bool = False
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

    def _classify_playlist(self, body: bytes | None) -> PlaylistType:
        """Three-valued media-over-master rank from a playlist response body.

        B7: Inspects the raw body bytes for HLS playlist tags. This is a rank
        only — it never filters addresses. Master playlists (containing
        ``#EXT-X-STREAM-INF`` or ``#EXT-X-I-FRAME-STREAM-INF``) carry variant
        stream references and are preferred for quality selection. Media
        playlists (containing ``#EXT-X-PLAYLIST-TYPE``) carry segments for a
        single variant. Absence of either tag yields ``UNCLASSIFIED``.
        """
        if body is None:
            return PlaylistType.UNCLASSIFIED
        try:
            text = body.decode("utf-8", errors="replace")
        except (UnicodeDecodeError, AttributeError):
            return PlaylistType.UNCLASSIFIED
        if any(tag in text for tag in _MASTER_PLAYLIST_TAGS):
            return PlaylistType.MASTER
        if _MEDIA_PLAYLIST_TAG in text:
            return PlaylistType.MEDIA
        return PlaylistType.UNCLASSIFIED

    def _rank_playlist(self, url: str) -> int:
        """Numeric rank for sorting: master (0) < unclassified (1) < media (2).

        Master playlists are ranked first because they enumerate all quality
        variants — the optimal entry point for stream selection.
        """
        playlist_type = self._playlist_types.get(url, PlaylistType.UNCLASSIFIED)
        if playlist_type == PlaylistType.MASTER:
            return 0
        if playlist_type == PlaylistType.MEDIA:
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

    def select(self) -> list[str]:
        """Select captured m3u8 addresses with an HLS-only filter and safety suspension.

        NET-008: Constrains the selection surface to HLS-only addresses
        (path suffix ``.m3u8``). If every captured address would be rejected
        by the filter, the filter is suspended and the unconstrained set is
        returned instead, with a single warning logged containing the reason
        and affected hosts.

        Exception totality (B7): this method never raises. All classification
        is wrapped so that a malformed address falls through to acceptance
        rather than propagating an exception to the caller.
        """
        try:
            captured = list(self.m3u8_urls)
            if not captured:
                return []

            hls_only = [addr for addr in captured if self._classify_hls(addr)]

            if not hls_only:
                if not self._hls_filter_suspended_logged:
                    self._log_suspension(captured)
                # Suspension: return the unconstrained set, ranked best-effort.
                return sorted(captured, key=self._rank_playlist)

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
                        playlist_type=self._playlist_types[normalized],
                    )
                else:
                    logger.debug("m3u8_url_captured", url=_strip_auth_params(normalized))

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

            # Enforce a byte cap even when Content-Length is absent
            # (chunked/streamed responses may omit the header).
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
                        self._playlist_types[normalized] = PlaylistType.UNCLASSIFIED
                        logger.debug(
                            "m3u8_url_found_in_json",
                            url=_strip_auth_params(normalized),
                        )
                elif isinstance(value, (dict, list)):
                    self._extract_urls_from_json(value)
        elif isinstance(data, list):
            for item in data:
                self._extract_urls_from_json(item)
