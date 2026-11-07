"""Tests for the programmable HLS fault-injection fixture (Block K)."""

from __future__ import annotations

import aiohttp
import pytest

from tests.integration.fixtures.hls_server import HlsServer, make_server


@pytest.mark.asyncio
async def test_hls_fault_server_fixture_exists() -> None:
    async with make_server(faults={}) as server:
        assert server.master_url.startswith("http://")


@pytest.mark.asyncio
async def test_fault_429_retry_after() -> None:
    async with make_server(faults={2: {"status": 429, "retry_after": 2}}) as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server.base_url}/seg/2") as resp:
                assert resp.status == 429
                assert resp.headers.get("Retry-After") == "2"


@pytest.mark.asyncio
async def test_fault_403_token_refresh() -> None:
    async with make_server(
        faults={1: {"status": 403, "rotate_token": True}},
        token="token-old",
        rotated_token="token-new",
    ) as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server.base_url}/seg/1?token=token-old") as resp:
                assert resp.status == 403
            # after rotation, new token succeeds
            async with session.get(f"{server.base_url}/seg/1?token=token-new") as resp:
                assert resp.status == 200


@pytest.mark.asyncio
async def test_fault_5xx_backoff() -> None:
    async with make_server(faults={0: {"status": 503, "failures": 1}}) as server:
        async with aiohttp.ClientSession() as session:
            r1 = await session.get(f"{server.base_url}/seg/0")
            assert r1.status == 503
            await r1.release()
            r2 = await session.get(f"{server.base_url}/seg/0")
            assert r2.status == 200
            await r2.release()


@pytest.mark.asyncio
async def test_fault_truncated_segment() -> None:
    async with make_server(faults={0: {"truncated": True}}) as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server.base_url}/seg/0") as resp:
                assert resp.status == 200
                data = await resp.read()
                assert 0 < len(data) < server.fragment_size
                assert resp.headers.get("X-Truncated") == "true"


@pytest.mark.asyncio
async def test_fault_bad_byterange() -> None:
    async with make_server(faults={-1: {"bad_byterange": True}}) as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{server.base_url}/range.bin", headers={"Range": "bytes=0-9"}
            ) as resp:
                assert resp.status == 206
                assert resp.headers.get("Content-Range") == "bytes 0-0/100"


@pytest.mark.asyncio
async def test_fault_missing_map_not_applicable() -> None:
    # Ensure media playlist is served and contains segments.
    async with make_server(faults={}) as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(server.media_url) as resp:
                text = await resp.text()
                assert "/seg/0" in text or "seg/0" in text


@pytest.mark.asyncio
async def test_hls_server_context_manager_scenario() -> None:
    from tests.integration.fixtures.hls_server import Scenario

    async with HlsServer(scenario=Scenario(fragment_count=3, status_sequence={404: [1]})) as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server.base_url}/seg/1") as resp:
                assert resp.status == 404
            async with session.get(f"{server.base_url}/seg/0") as resp:
                assert resp.status == 200
