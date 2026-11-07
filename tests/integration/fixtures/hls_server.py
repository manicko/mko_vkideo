"""Programmable local HLS server for fault-injection tests.

This is a *fixture interface sketch* (see plan Block K / section 4). It is
not wired into any test yet; it provides a deterministic, offline HTTP
server that can serve master + media playlists and segments with configurable
status sequences, signed-URL expiry, byte-range handling and throttling.

Usage::

    from tests.integration.fixtures.hls_server import HlsServer, Scenario

    scenario = Scenario(fragment_count=4, status_sequence={403: [2], 429: [3]})
    async with HlsServer(scenario) as server:
        url = server.master_url
        ...
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from aiohttp import web


@dataclass
class Scenario:
    fragment_count: int = 4
    status_sequence: dict[int, list[int]] = field(default_factory=dict)
    expire_signature_after: int | None = None
    reset_connection_on: set[int] = field(default_factory=set)
    use_new_signature_for_recovery: bool = True
    byte_range: bool = False
    fragment_size: int = 1024


@dataclass
class HlsServer:
    scenario: Scenario
    host: str = "127.0.0.1"
    port: int = 0
    _runner: web.AppRunner | None = None
    _site: web.TCPSite | None = None

    @property
    def master_url(self) -> str:
        return f"http://{self.host}:{self.port}/master.m3u8"

    async def __aenter__(self) -> HlsServer:
        app = web.Application()
        app.router.add_get("/master.m3u8", self._master)
        app.router.add_get("/media.m3u8", self._media)
        app.router.add_get("/seg/{n}", self._segment)
        app.router.add_get("/range.bin", self._range)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()
        # Resolve actual port when 0 was requested.
        if self.port == 0:
            self.port = self._site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._runner is not None:
            await self._runner.cleanup()

    def _status_for(self, index: int) -> int:
        for status, indices in self.scenario.status_sequence.items():
            if index in indices:
                return status
        return 200

    async def _master(self, request: web.Request) -> web.Response:
        body = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=1280x720\n/media.m3u8\n"
        return web.Response(text=body, content_type="application/vnd.apple.mpegurl")

    async def _media(self, request: web.Request) -> web.Response:
        lines = ["#EXTM3U", "#EXT-X-TARGETDURATION:1", "#EXT-X-MEDIA-SEQUENCE:0"]
        for i in range(self.scenario.fragment_count):
            lines.append(f"/seg/{i}")
        lines.append("#EXT-X-ENDLIST")
        return web.Response(
            text="\n".join(lines) + "\n", content_type="application/vnd.apple.mpegurl"
        )

    async def _segment(self, request: web.Request) -> web.Response:
        n = int(request.match_info["n"])
        if n in self.scenario.reset_connection_on:
            raise ConnectionResetError("reset")
        status = self._status_for(n)
        if status != 200:
            return web.Response(status=status)
        if (
            self.scenario.expire_signature_after is not None
            and n > self.scenario.expire_signature_after
            and not self.scenario.use_new_signature_for_recovery
        ):
            return web.Response(status=403)
        payload = (n.to_bytes(4, "big") * (self.scenario.fragment_size // 4))[
            : self.scenario.fragment_size
        ]
        return web.Response(body=payload, content_type="video/mp2t")

    async def _range(self, request: web.Request) -> web.Response:
        rng = request.headers.get("Range")
        if not rng:
            return web.Response(status=200, body=b"x" * 100)
        # Minimal 206 response for valid Range.
        return web.Response(status=206, body=b"x" * 10, headers={"Content-Range": "bytes 0-9/100"})


def make_segment_bytes(index: int, size: int = 1024) -> bytes:
    seed = hashlib.sha256(str(index).encode()).digest()
    return (seed * (size // len(seed) + 1))[:size]


__all__ = ["Scenario", "HlsServer", "make_segment_bytes"]
