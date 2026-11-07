"""Tests for the programmable HLS fault-injection fixture (Block K)."""

from __future__ import annotations

import time

import aiohttp
import pytest

from tests.integration.fixtures.hls_server import HlsServer, make_12_fragment_scenario, make_server


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




@pytest.mark.asyncio
async def test_twelve_fragment_scenario_helper() -> None:
    scenario = make_12_fragment_scenario(slow_fragment=2, first_byte_delay_seconds=0.05, chunk_size=16, chunk_delay_seconds=0.05)
    assert scenario.fragment_count == 12
    async with HlsServer(scenario=scenario) as server:
        async with aiohttp.ClientSession() as session:
            async with session.get(server.media_url) as resp:
                text = await resp.text()
            assert "/seg/11" in text
            r0 = await session.get(f"{server.base_url}/seg/0")
            d0 = await r0.read()
            await r0.release()
            r1 = await session.get(f"{server.base_url}/seg/1")
            d1 = await r1.read()
            await r1.release()
            assert d0 != d1


@pytest.mark.asyncio
async def test_slow_fragment_timing_and_range() -> None:
    scenario = make_12_fragment_scenario(slow_fragment=3, first_byte_delay_seconds=0.1, chunk_size=8, chunk_delay_seconds=0.1)
    async with HlsServer(scenario=scenario) as server:
        async with aiohttp.ClientSession() as session:
            start = time.monotonic()
            async with session.get(f"{server.base_url}/seg/3") as resp:
                assert resp.headers.get("Content-Type") == "video/mp2t"
                data = await resp.read()
            elapsed = time.monotonic() - start
            assert elapsed >= 0.15
            assert len(data) == server.fragment_size
            async with session.get(f"{server.base_url}/seg/3", headers={"Range": "bytes=0-4"}) as resp:
                assert resp.status == 206
                body = await resp.read()
                assert len(body) == 5


@pytest.mark.asyncio
async def test_reset_connection_on_consumable() -> None:
    scenario = make_12_fragment_scenario(reset_connection_on={1})
    async with HlsServer(scenario=scenario) as server:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{server.base_url}/seg/1") as resp:
                    await resp.read()
            except Exception:
                pass
            async with session.get(f"{server.base_url}/seg/1") as resp:
                assert resp.status == 200
