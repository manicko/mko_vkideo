"""Programmable local HLS server for fault-injection tests (Block K)."""

from __future__ import annotations

import asyncio
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

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
    faults: dict[int, Any] = field(default_factory=dict)
    slow_fragment: int | None = None
    first_byte_delay_seconds: float = 0.0
    chunk_size: int = 1024
    chunk_delay_seconds: float = 0.0


@dataclass
class HlsServer:
    scenario: Scenario | None = None
    faults: dict[int, Any] | None = None
    host: str = "127.0.0.1"
    port: int = 0
    fragment_count: int = 4
    fragment_size: int = 1024
    token: str = "token-old"
    rotated_token: str = "token-new"
    slow_fragment: int | None = None
    first_byte_delay_seconds: float = 0.0
    chunk_size: int = 1024
    chunk_delay_seconds: float = 0.0
    reset_connection_on: set[int] = field(default_factory=set)
    _runner: web.AppRunner | None = field(default=None, init=False, repr=False)
    _site: web.TCPSite | None = field(default=None, init=False, repr=False)
    _attempts: dict[int, int] = field(
        default_factory=lambda: defaultdict(int), init=False, repr=False
    )
    _master_token: str = field(default="token-old", init=False, repr=False)
    _reset_remaining: set[int] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.scenario is not None:
            self.fragment_count = self.scenario.fragment_count
            self.fragment_size = self.scenario.fragment_size
            if self.scenario.faults:
                self.faults = {**self.scenario.faults, **(self.faults or {})}
            # Translate legacy status_sequence into faults.
            if self.scenario.status_sequence:
                faults = dict(self.faults or {})
                for status, indices in self.scenario.status_sequence.items():
                    for idx in indices:
                        faults[idx] = {"status": status}
                self.faults = faults
            self.slow_fragment = self.scenario.slow_fragment
            self.first_byte_delay_seconds = self.scenario.first_byte_delay_seconds
            self.chunk_size = self.scenario.chunk_size
            self.chunk_delay_seconds = self.scenario.chunk_delay_seconds
            self.reset_connection_on = set(self.scenario.reset_connection_on)
        if self.faults is None:
            self.faults = {}
        self._master_token = self.token
        if not self.reset_connection_on and self.scenario is not None:
            self.reset_connection_on = set(self.scenario.reset_connection_on)
        self._reset_remaining = set(self.reset_connection_on)

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def master_url(self) -> str:
        return f"{self.base_url}/master.m3u8"

    @property
    def media_url(self) -> str:
        return f"{self.base_url}/media.m3u8"

    def _fault_for(self, index: int) -> Any:
        return (self.faults or {}).get(index)

    def _normalize_fault(self, fault: Any) -> dict[str, Any]:
        if fault is None:
            return {}
        if isinstance(fault, int):
            return {"status": int(fault)}
        if isinstance(fault, str):
            return {"status": int(fault)} if fault.isdigit() else {"action": fault}
        if isinstance(fault, dict):
            return dict(fault)
        return {"status": int(fault)}

    async def start(self) -> HlsServer:
        return await self.__aenter__()

    async def stop(self) -> None:
        await self.__aexit__(None, None, None)

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
        if self.port == 0:
            self.port = self._site._server.sockets[0].getsockname()[1]  # type: ignore[union-attr]
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            self._site = None

    def _segment_payload(self, n: int) -> bytes:
        size = self.fragment_size
        seed = hashlib.sha256(str(n).encode()).digest()
        return (seed * (size // len(seed) + 1))[:size]

    def segment_payloads(self) -> list[bytes]:
        return [self._segment_payload(i) for i in range(self.fragment_count)]

    @staticmethod
    def _parse_range(rng: str | None, total: int) -> tuple[int, int]:
        if not rng or not rng.startswith("bytes="):
            return 0, total - 1
        spec = rng[6:].split(",")[0].strip()
        parts = spec.split("-")
        start_s = parts[0].strip() if len(parts) > 0 else ""
        end_s = parts[1].strip() if len(parts) > 1 else ""
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else total - 1
        if start < 0:
            start = max(0, total + start)
        end = min(end, total - 1)
        if end < start:
            end = start
        return start, end

    async def _master(self, request: web.Request) -> web.Response:
        body = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=1280x720\n/media.m3u8\n"
        return web.Response(text=body, content_type="application/vnd.apple.mpegurl")

    async def _media(self, request: web.Request) -> web.Response:
        lines = ["#EXTM3U", "#EXT-X-TARGETDURATION:1", "#EXT-X-MEDIA-SEQUENCE:0"]
        for i in range(self.fragment_count):
            tok = request.query.get("token", self._master_token)
            lines.append(f"/seg/{i}?token={tok}")
        lines.append("#EXT-X-ENDLIST")
        return web.Response(
            text="\n".join(lines) + "\n", content_type="application/vnd.apple.mpegurl"
        )

    async def _segment(self, request: web.Request) -> web.Response | web.StreamResponse:
        n = int(request.match_info["n"])

        # Reset-connection consumption (consumable).
        if n in self._reset_remaining:
            self._reset_remaining.discard(n)
            transport = request.transport
            if transport is not None:
                try:
                    transport.close()
                except Exception:  # noqa: BLE001
                    pass
            raise ConnectionResetError("reset connection on configured fragment")

        fault = self._normalize_fault(self._fault_for(n))
        self._attempts[n] += 1
        attempt = self._attempts[n]

        # Token rotation handling: if a token query is present and stale, 403.
        token = request.query.get("token", "")
        rotate = bool(fault.get("rotate_token") or fault.get("token_rotation"))
        failures = fault.get("failures")
        if failures is not None:
            if attempt <= int(failures):
                status = int(fault.get("status", 503))
            else:
                status = int(fault.get("success_status", 200))
        else:
            status = int(fault.get("status", 200))
        # token rotation: first request with old token fails 403
        if rotate and token == self.rotated_token:
            status = 200
        if rotate and token == self.token:
            status = 403

        if status != 200:
            headers = {}
            if "retry_after" in fault:
                headers["Retry-After"] = str(fault["retry_after"])
            resp = web.Response(status=status, headers=headers)
            # If rotation requested, promote token after a 403 so a retry
            # with the new token succeeds.
            if rotate and status == 403:
                self._master_token = self.rotated_token
            return resp

        # Truncated body simulation.
        if fault.get("truncated"):
            payload = self._segment_payload(n)
            partial = payload[: max(1, len(payload) // 2)]
            return web.Response(
                body=partial,
                content_type="video/mp2t",
                headers={"X-Truncated": "true"},
            )

        # Corrupt fragment.
        if fault.get("corrupt"):
            payload = bytearray(self._segment_payload(n))
            if payload:
                payload[0] ^= 0xFF
            return web.Response(body=bytes(payload), content_type="video/mp2t")

        # Bad BYTERANGE simulation on Range requests.
        rng = request.headers.get("Range")
        if rng and fault.get("bad_byterange"):
            return web.Response(
                status=206,
                body=self._segment_payload(n),
                headers={"Content-Range": "bytes 0-0/1", "Content-Length": "1"},
            )

        # Slow fragment delivery.
        slow = self.slow_fragment
        if self.scenario is not None and self.scenario.slow_fragment is not None:
            slow = self.scenario.slow_fragment
        if slow is not None and n == slow:
            first_delay = self.first_byte_delay_seconds
            chunk_size = self.chunk_size
            chunk_delay = self.chunk_delay_seconds
            if self.scenario is not None:
                first_delay = self.scenario.first_byte_delay_seconds
                chunk_size = self.scenario.chunk_size
                chunk_delay = self.scenario.chunk_delay_seconds
            payload = self._segment_payload(n)
            rng = request.headers.get("Range")
            status = 200
            data = payload
            headers = {"Content-Type": "video/mp2t"}
            if rng:
                start, end = self._parse_range(rng, len(payload))
                data = payload[start : end + 1]
                status = 206
                headers["Content-Range"] = f"bytes {start}-{end}/{len(payload)}"
                headers["Content-Length"] = str(len(data))
            resp = web.StreamResponse(status=status, headers=headers)
            await resp.prepare(request)
            await asyncio.sleep(first_delay)
            if data:
                await resp.write(data[:1])
                rest = data[1:]
                chunk = rest[:chunk_size]
                if chunk:
                    await resp.write(chunk)
                await asyncio.sleep(chunk_delay)
                if len(rest) > chunk_size:
                    await resp.write(rest[chunk_size:])
            await resp.write_eof()
            return resp

        # Normal range handling.
        if rng:
            # Minimal correct 206.
            data = self._segment_payload(n)
            return web.Response(
                status=206,
                body=data[:10],
                headers={"Content-Range": f"bytes 0-9/{len(data)}", "Content-Length": "10"},
            )

        payload = self._segment_payload(n)
        return web.Response(body=payload, content_type="video/mp2t")

    async def _range(self, request: web.Request) -> web.Response:
        rng = request.headers.get("Range")
        if not rng:
            return web.Response(status=200, body=b"x" * 100)
        if (self.faults or {}).get(-1, {}).get("bad_byterange"):
            return web.Response(status=206, body=b"x", headers={"Content-Range": "bytes 0-0/100"})
        return web.Response(status=206, body=b"x" * 10, headers={"Content-Range": "bytes 0-9/100"})


def make_server(faults: dict[int, Any] | None = None, **kwargs: Any) -> HlsServer:
    """Factory exposing the ``faults=...`` interface required by Block K."""
    if faults is not None:
        kwargs = {**kwargs, "faults": faults}
    # Allow scenario passthrough.
    return HlsServer(**kwargs)


def make_12_fragment_scenario(
    slow_fragment: int | None = None,
    reset_connection_on: Any = None,
    **kwargs: Any,
) -> Scenario:
    return Scenario(
        fragment_count=12,
        slow_fragment=slow_fragment,
        reset_connection_on=set(reset_connection_on or ()),
        **kwargs,
    )


def make_twelve_fragment_scenario(*args: Any, **kwargs: Any) -> Scenario:
    return make_12_fragment_scenario(*args, **kwargs)


twelve_fragment_scenario = make_12_fragment_scenario
slow_fragment_scenario = make_12_fragment_scenario

# Attach helpers to HlsServer for convenience.
HlsServer.make_12_fragment_scenario = staticmethod(make_12_fragment_scenario)  # type: ignore[attr-defined]
HlsServer.twelve_fragment_scenario = staticmethod(make_12_fragment_scenario)  # type: ignore[attr-defined]
HlsServer.build_12_fragment_scenario = staticmethod(make_12_fragment_scenario)  # type: ignore[attr-defined]


def make_segment_bytes(index: int, size: int = 1024) -> bytes:
    seed = hashlib.sha256(str(index).encode()).digest()
    return (seed * (size // len(seed) + 1))[:size]


__all__ = [
    "Scenario",
    "HlsServer",
    "make_server",
    "make_segment_bytes",
    "make_12_fragment_scenario",
    "make_twelve_fragment_scenario",
    "twelve_fragment_scenario",
    "slow_fragment_scenario",
]
