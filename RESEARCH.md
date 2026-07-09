# Research Findings: DF-010 and DF-011 Implementation

## DF-010: Segment Download Cleanup - Partial Completion Handling

### Current Architecture Analysis

**Location:** `src\vkdownloader\services\downloader.py:71-145`

**Current Flow:**
1. `download_hls_with_resume` creates `segments_dir` and `metadata_file` for progress tracking
2. Downloads segments in a loop (line 123-135)
3. On segment download failure (line 130-132), returns `None` immediately **without cleanup**
4. On merge batch failure (line 250), returns `None` **without cleanup** - temp files left
5. On final merge failure (line 291), returns `None` **without cleanup** - partial batches left
6. `_cleanup_segments()` (lines 311-319) only called on FULL SUCCESS (line 142)
7. On FAILURE: partial `.ts` files, `.progress.json`, and batch temp files remain on disk

**Problem:** No cleanup in error paths leaves orphaned temporary files.

### Best Practices Research (Confidence: HIGH)

Based on Python official docs and async concurrency patterns:

1. **contextlib.asynccontextmanager with try/finally** - The standard pattern for async resource cleanup:
```python
@contextlib.asynccontextmanager
async def managed_resource():
    resource = acquire()
    try:
        yield resource
    finally:
        cleanup()  # Always runs, even on exception
```

2. **Atomic file writes** - Write to temp file first, rename on completion (per pyhaul design):
   - Destination file doesn't exist until complete
   - Incomplete data lives in `.part` file
   - Atomic rename on success

3. **BaseException handling** - Catch `asyncio.CancelledError` (Python 3.8+: inherits from `BaseException`, not `Exception`)

### Recommended Solution

Wrap the download logic in a try/finally block to ensure cleanup on partial completion:

```python
async def download_hls_with_resume(...) -> Path | None:
    # ... setup ...
    try:
        # ... download loop ...
        if downloaded_count == len(segments):
            result = await _merge_segments_batched(...)
            if result:
                return result
    finally:
        # Only cleanup if download didn't complete
        if downloaded_count < len(segments) or result is None:
            _cleanup_partial_download(segments_dir, metadata_file)
```

**Implementation priority:**
1. Add try/finally around download loop
2. Create `_cleanup_partial_download()` that removes partial segment files
3. Preserve resume capability: keep progress file if download can be resumed

---

## DF-011: Settings Concurrency Parameters Unused in Batch Download

### Current Architecture Analysis

**Location:** `src\vkdownloader\cli.py:138`

**Current Flow:**
1. `Settings()` created inline inside `_run_batch_with_progress` (line 138)
2. Only `max_concurrent_downloads` used for semaphore
3. Available but unused settings:
   - `concurrency` (line 59-64 in config.py) - default 8
   - `request_delay_min/max` (lines 43-52 in config.py) - 2.0-5.0 seconds
   - `timeout_seconds` (lines 83-88) - 30 seconds
4. `AdaptiveThrottle` class exists (`infrastructure\adaptive_throttle.py`) but never integrated

**Problem:** Batch download creates redundant Settings instances and ignores rate-limiting configuration.

### Best Practices Research (Confidence: HIGH)

Based on aio-libs aiohttp docs and rate-limiting patterns:

1. **Single session reuse** - aiohttp docs recommend persistent session:
```python
async with aiohttp.ClientSession() as session:  # Reuse across requests
    for url in urls:
        async with session.get(url) as resp:
            ...
```

2. **Adaptive rate limiting** - The existing `AdaptiveThrottle` provides:
   - `wait()` - Apply delay before requests
   - `on_rate_limited()` - Backoff on 429/403 responses
   - `on_success()` - Recovery toward base delay

3. **Semaphore + throttle combination** - Best practice from 2025 rate-limiting guides:
   - Semaphore controls concurrency (how many simultaneous)
   - Throttle controls rate (how many per time window)

### Recommended Solution

Create Settings once at start of `batch_download` command and integrate AdaptiveThrottle:

```python
@app.command("batch")
def batch_download(...) -> None:
    setup_logging()
    settings = Settings()  # Create once
    throttle = AdaptiveThrottle(base_rpm=settings.concurrency)  # Use for rate limiting

    async def _download_single(url: str) -> tuple[str, str, str]:
        try:
            await throttle.wait()  # Apply rate limiting delay
            # ... extraction and download ...
            throttle.on_success()
        except Exception:
            throttle.on_rate_limited()
            # ...

    async def _run_batch_with_progress():
        semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        # ...
```

**Implementation priority:**
1. Move `Settings()` instantiation to function start (outside nested function)
2. Create `AdaptiveThrottle` with settings-based delay
3. Call `throttle.wait()` before each request
4. Call `throttle.on_success()` or `throttle.on_rate_limited()` based on response

---

## Summary Recommendation

| Issue | Priority | Solution |
|-------|----------|----------|
| DF-010 | High | Add try/finally cleanup in `download_hls_with_resume` |
| DF-011 | Medium | Move Settings to top-level, integrate AdaptiveThrottle |

Both issues follow the same pattern: extract resources/configuration to outer scope and ensure deterministic cleanup.