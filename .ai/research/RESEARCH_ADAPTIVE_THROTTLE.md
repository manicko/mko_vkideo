# AdaptiveThrottle Integration Research

## Executive Summary

**Recommendation: NO-GO for integration** - The existing concurrency mechanisms already provide adequate rate limiting control, and AdaptiveThrottle is not suitable for handling 429 responses in concurrent segment downloads.

---

## 1. AdaptiveThrottle Analysis

### Current Implementation (`src\vkdownloader\infrastructure\adaptive_throttle.py`)

The `AdaptiveThrottle` class provides:
- **Base delay calculation** from RPM settings (default: 20 RPM → 3 second base delay)
- **Exponential backoff** on rate limiting (1.5x multiplier, capped at 10 seconds)
- **Gradual recovery** on success (0.95x multiplier, minimum 1 second)
- **Random jitter** (0-1 second added to each wait)

**Key limitation**: The class implements a **time-based throttling strategy**, not a **response-based rate limiting strategy**. It predates the segment parallelization work and was designed for sequential requests.

---

## 2. Current Download Flow Analysis

### Segment Download Path (`download_hls_with_resume`)

The current implementation already has two overlapping rate-limiting mechanisms:

1. **Semaphore-based concurrency** (line 155 in downloader.py):
   ```python
   semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)  # Default: 4
   ```
   This limits concurrent requests to 4 by default.

2. **TCP connector limit** (line 142 in downloader.py):
   ```python
   connector = aiohttp.TCPConnector(limit=10)
   ```
   This sets a hard limit of 10 total connections.

### Missing: 429 Response Handling

The `_download_segment` function (lines 238-255) does NOT handle 429 (Too Many Requests) responses:
```python
async def _download_segment(...) -> bool:
    async with session.get(segment_url, headers=headers) as response:
        if response.status == 200:
            # success
        logger.warning("segment_download_failed", status=response.status)
        return False  # No retry, no throttle adjustment
```

There is no retry loop, no exponential backoff, and no rate limit recovery.

---

## 3. Consumer Analysis

### Where AdaptiveThrottle Could Be Used

| Component | Potential Use | Assessment |
|-----------|---------------|------------|
| `_download_segment` | Wait before retry on 429 | **Not recommended** - would serialize requests |
| `download_segment_concurrent` | Rate limiting between downloads | **Not recommended** - conflicts with concurrency |
| `_fetch_playlist_with_retry` | Rate limiting on 403/410 | **Redundant** - already uses retry logic for token refresh |

### Import Analysis

`AdaptiveThrottle` is only imported in `infrastructure/__init__.py` for export purposes. It is **not used anywhere** in the codebase.

---

## 4. Impact Assessment on Concurrent Downloads

### Why AdaptiveThrottle is Problematic

**Scenario**: 4 concurrent segment downloads start simultaneously.

| Problem | Impact |
|---------|--------|
| **Serialized waits** | If each segment calls `throttle.wait()`, the first task waits, but others proceed immediately. This creates an artificial bottleneck. |
| **Shared state violation** | AdaptiveThrottle maintains a single `current_delay` value. Concurrent tasks would race to update it, causing unpredictable behavior. |
| **No 429 detection** | The current implementation doesn't detect or handle HTTP 429 responses at all. |
| **Overlap with semaphore** | The semaphore already controls concurrency. Adding throttle would create conflicting rate-limiting policies. |

### Current Configuration Adequacy

The existing settings provide sufficient control:
- `max_concurrent_downloads: int = 4` - Controls segment download concurrency
- `concurrent_fragments: int = 4` - Controls yt-dlp HLS fragment concurrency
- `throttled_rate: int = 100000` - yt-dlp's built-in throttling detection (100KB/s threshold)

---

## 5. Alternative Strategies

### Option A: Per-Endpoint Rate Limiting (Recommended Alternative)

If rate limiting is needed, implement endpoint-specific throttling:

```python
class PerEndpointThrottle:
    """Track and rate limit per CDN endpoint."""
    
    def __init__(self) -> None:
        self.endpoint_delays: dict[str, float] = {}
    
    async def wait_if_needed(self, endpoint: str) -> None:
        delay = self.endpoint_delays.get(endpoint, 0)
        if delay > 0:
            await asyncio.sleep(delay)
    
    def record_rate_limited(self, endpoint: str) -> None:
        current = self.endpoint_delays.get(endpoint, 1.0)
        self.endpoint_delays[endpoint] = min(current * 1.5, 10.0)
```

This would allow different endpoints to have independent throttling states.

### Option B: Retry with Exponential Backoff (For 429)

Add proper 429 handling to `_download_segment`:

```python
async def _download_segment_with_retry(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    max_retries: int = 3,
) -> bool:
    for attempt in range(max_retries):
        async with session.get(segment_url, headers=headers) as response:
            if response.status == 200:
                output_path.write_bytes(await response.read())
                return True
            if response.status == 429:
                # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(2 ** attempt + random.uniform(0, 1))
                continue
            return False
    return False
```

### Option C: Do Nothing (Recommended)

The current architecture is sufficient:
1. Concurrent downloads (4 by default) already spread the load
2. yt-dlp handles throttling detection via `throttled_rate` parameter
3. Adding complexity (AdaptiveThrottle) provides no measurable benefit

---

## 6. Detailed Findings

### 6.1 AdaptiveThrottle Design Mismatch

The class design assumes:
- Sequential request flow where each request calls `wait()` before proceeding
- Single shared rate limit across all endpoints
- Rate limiting triggered externally (caller must invoke `on_rate_limited()`)

The segment download flow assumes:
- Concurrent requests that should complete as fast as possible
- Independent failure handling per segment
- No coordination between parallel download tasks

### 6.2 Conflict Analysis

If AdaptiveThrottle were integrated naively:

```python
# PROBLEMATIC APPROACH
async def download_segment_concurrent(idx: int, segment_url: str) -> bool:
    await throttle.wait()  # Blocks ALL concurrent tasks here!
    async with semaphore:
        # ... download
```

This would serialize all downloads, negating the benefit of concurrent downloads.

### 6.3 Thread Safety Concern

The `AdaptiveThrottle` class uses instance variables (`current_delay`) without synchronization. In concurrent asyncio context:
- All tasks share the same throttle instance
- `on_rate_limited()` and `on_success()` race to update `current_delay`
- Behavior becomes unpredictable under load

---

## 7. Recommendation

### Decision: NO-GO

**Reasoning:**

1. **Architectural mismatch**: AdaptiveThrottle is designed for sequential, not concurrent, request flows.

2. **No 429 handling gap**: The real gap is missing retry logic for 429 responses, not rate limiting.

3. **Redundant concurrency**: The semaphore already provides rate limiting; adding AdaptiveThrottle would duplicate logic with different semantics.

4. **Complexity vs. benefit**: Integration would add complexity without measurable improvement - the concurrent downloads already bypass per-connection throttling.

5. **Thread safety concerns**: Concurrent access to shared `current_delay` would cause race conditions.

### Alternative Implementation (If Required)

If rate limiting is deemed necessary after further analysis, implement:

1. Replace `AdaptiveThrottle` with a thread-safe, per-endpoint throttle with proper 429 detection in `_download_segment`
2. Add retry logic with exponential backoff for HTTP 429 responses
3. Integrate with existing semaphore rather than replacing it

---

## 8. Summary Table

| Aspect | Current State | With AdaptiveThrottle | Recommendation |
|--------|---------------|---------------------|----------------|
| 429 handling | None | None (class doesn't detect 429) | Add retry logic |
| Concurrency | Semaphore (4) | Would serialize | Keep semaphore |
| Rate limiting | None | Time-based, sequential | Use concurrent approach |
| Thread safety | N/A | Unsafe concurrent access | Would need redesign |
| yt-dlp throttling | `throttled_rate=100000` | Unchanged | Keep as-is |

---

## 9. Next Steps

1. **Do NOT integrate AdaptiveThrottle** - Close task_011 without implementation
2. **Consider adding 429 retry logic** to `_download_segment` if 429 errors are observed in production
3. **Monitor download success rates** and adjust `max_concurrent_downloads` (currently 4) based on actual CDN behavior