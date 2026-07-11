---
wave: 1
depends_on: []
files_modified:
  - src/vkdownloader/services/downloader_throttle.py
  - src/vkdownloader/services/downloader.py
  - tests/test_downloader_throttle.py
  - tests/test_hls_downloader.py
depends_on_tasks: []
revision_notes: |
   - task_1: Clarified 1s base delay is for retry backoff (AWS Full Jitter), 1.5s is for inter-segment anti-detection delay (different purposes)
   - task_2: FIXED: _retry_429_with_backoff now returns `bytes | None` instead of `aiohttp.ClientResponse | None` to avoid response lifecycle issues - reads content inside retry loop before context manager exits
   - task_2: Added max_concurrent_downloads: int = 1 parameter for sequential mode detection
   - task_3: FIXED: Anti-detection delay now applied AFTER semaphore release (not inside), preserving parallel mode performance
   - task_3: Delay only applies when max_concurrent_downloads=1, no change to parallel mode behavior
   - task_4: Renamed to use tests/test_downloader_throttle.py for throttle unit tests
   - task_5: Added test for download_segment_concurrent modification with sequential mode
   - All changes maintain backward compatibility for parallel mode (max_concurrent_downloads > 1)
   - 5xx retry codes specified: 500, 502, 503, 504
   - SPEC-DEVIATION RESOLVED: Response content read inside retry function, returns bytes instead of response object
autonomous: false
---

# Phase 1: Throttling and Concurrency Control

<goal>
Implement configurable download concurrency (sequential vs parallel) and adaptive throttling for anti-detection when downloading single-threaded.
</goal>

<must_haves>
<ul>
<li><code>max_concurrent_downloads=1</code> enables sequential download mode with anti-detection throttling</li>
<li>Per-segment 429 retry handler with exponential backoff and full jitter</li>
<li>Respect <code>Retry-After</code> header when present</li>
<li>Structured logging for retry attempts with fields: attempt, status, retry_after, segment_index, url</li>
<li>Backward compatibility: parallel downloads (<code>max_concurrent_downloads > 1</code>) unaffected</li>
<li>Cap maximum delay at 30 seconds</li>
<li>Only retry on 429 and 5xx status codes</li>
<li>Apply 1.5s base delay with jitter between segments in sequential mode for anti-detection</li>
</ul>
</must_haves>

<validation_criteria>
<ul>
<li><code>_retry_429_with_backoff</code> function exists with signature returning <code>bytes | None</code></li>
<li><code>_download_segment</code> integrates throttling when <code>max_concurrent_downloads=1</code>, writes returned bytes to output_path</li>
<li>Existing parallel download tests pass unchanged (backward compatibility verified)</li>
<li>New tests for 429 retry behavior pass in <code>tests/test_downloader_throttle.py</code></li>
<li>Structured logging includes required fields: attempt, status, retry_after, segment_index, url</li>
<li>Anti-detection delay applies AFTER semaphore release in sequential mode (preserves parallel semaphore availability)</li>
</ul>
</validation_criteria>

<execution_notes>
<ul>
<li>Do NOT integrate AdaptiveThrottle into concurrent download flow (creates race conditions)</li>
<li>Throttle applied per-segment, not globally (maintains isolation)</li>
<li>Use stdlib <code>random</code> module for jitter implementation</li>
<li>Import from downloader_throttle in downloader.py to avoid circular dependency (throttle module has no dependencies on downloader)</li>
</ul>
</execution_notes>

<tasks>
<task id="task_1" wave="1">
<name>Create internal _retry_429_with_backoff() function</name>
<file>src/vkdownloader/services/downloader_throttle.py</file>
<description>Create new module with retry function implementing AWS Full Jitter exponential backoff for 429/5xx errors. Function reads response content and returns bytes to avoid lifecycle issues with context manager.</description>
<spec>
<ul>
<li>Function signature: <code>async def _retry_429_with_backoff(session: aiohttp.ClientSession, segment_url: str, headers: dict[str, str], segment_index: int, max_retries: int = 3) -> bytes | None</code></li>
<li>Implements AWS Full Jitter retry backoff: <code>random.uniform(0, base_delay * 2^attempt)</code> with 1s base for RETRY BACKOFF (distinct from 1.5s inter-segment delay)</li>
<li>Respects Retry-After header if present (prioritize server guidance)</li>
<li>Logs with structured fields: attempt, status, retry_after, segment_index, url on each retry attempt</li>
<li>Returns response content bytes on success (200), None on permanent failure after max retries</li>
<li>Reads response content inside retry loop before exiting context manager to avoid lifecycle issues</li>
<li>Only retries on 429 and 5xx status codes (500, 502, 503, 504)</li>
<li>Cap maximum delay at 30 seconds</li>
</ul>
</spec>
</task>

<task id="task_2" wave="2" depends_on="task_1">
<name>Modify _download_segment function for single-thread mode throttling</name>
<file>src/vkdownloader/services/downloader.py</file>
<description>Update _download_segment to delegate to _retry_429_with_backoff when max_concurrent_downloads=1, receiving bytes and writing to output.</description>
<spec>
<ul>
<li>Import _retry_429_with_backoff from downloader_throttle module</li>
<li>Update function signature: <code>async def _download_segment(session: aiohttp.ClientSession, segment_url: str, output_path: Path, headers: dict[str, str], max_concurrent_downloads: int = 1, segment_index: int = 0) -> bool</arg></li>
<li>max_concurrent_downloads default = 1 enables sequential mode detection (when semaphore=1 caller)</li>
<li>When max_concurrent_downloads=1: 
  <ul>
    <li>Call _retry_429_with_backoff for HTTP request (returns bytes | None)</li>
    <li>Check returned bytes is not None, then write bytes to output_path</li>
    <li>Return True on success, False on failure</li>
  </ul>
</li>
<li>When max_concurrent_downloads > 1: use existing direct download logic (no throttling)</li>
<li>Backward compatibility: callers passing (session, url, path, headers) must continue working without changes</li>
</ul>
</spec>
</task>

<task id="task_3" wave="2" depends_on="task_1">
<name>Update download_segment_concurrent coroutine with anti-detection delay</name>
<file>src/vkdownloader/services/downloader.py</file>
<description>Add 1.5s base delay with jitter between successful segment requests when in sequential mode, ensuring delay applies AFTER semaphore release.</description>
<spec>
<ul>
<li>Pass max_concurrent_downloads=settings.max_concurrent_downloads to _download_segment call</li>
<li>Pass segment_index=i to _download_segment for logging context</li>
<li>Apply 1.5s base delay + random jitter (0-0.5s) AFTER _download_segment returns True and AFTER async with semaphore exits</li>
<li>Do NOT apply inter-segment delay when max_concurrent_downloads > 1 (parallel mode unaffected)</li>
<li>Delay placement: outside the semaphore context block, after semaphore release, before loop continues</li>
</ul>
</spec>
</task>

<task id="task_4" wave="3" depends_on="task_2">
<name>Add unit tests for _retry_429_with_backoff</name>
<file>tests/test_downloader_throttle.py</file>
<description>Create unit tests for the 429 retry mechanism in dedicated throttle test file.</description>
<spec>
<ul>
<li>Test successful response on first attempt (no retry) - verify function returns bytes</li>
<li>Test 429 retry with exponential backoff: attempt 0 random(0,1s), attempt 1 random(0,2s), attempt 2 random(0,4s) - verify delay calculation</li>
<li>Test Retry-After header overrides calculated delay when present - verify server guidance takes priority</li>
<li>Test max retries (3) exceeded returns None</li>
<li>Test 5xx status codes trigger retry (500, 502, 503, 504)</li>
<li>Test non-retry status codes (403, 404) return None immediately without retry</li>
<li>Test delay capped at 30 seconds maximum</li>
<li>Test structured logging fields: attempt, status, retry_after, segment_index, url</li>
</ul>
</spec>
</task>

<task id="task_5" wave="3" depends_on="task_3">
<name>Add integration tests for sequential download mode</name>
<file>tests/test_hls_downloader.py</file>
<description>Create integration tests for sequential mode behavior and anti-detection delay in download_segment_concurrent.</description>
<spec>
<ul>
<li>Test max_concurrent_downloads=1 applies 1.5s inter-segment anti-detection delay AFTER semaphore release</li>
<li>Test parallel mode (max_concurrent_downloads > 1) does not apply inter-segment delay (preserve performance)</li>
<li>Test structured log output from _retry_429_with_backoff contains required fields: attempt, status, retry_after, segment_index, url</li>
<li>Test max_concurrent_downloads=1 with 429 response triggers exponential backoff retry via _retry_429_with_backoff</li>
<li>Test existing parallel download tests remain passing (backward compatibility)</li>
</ul>
</spec>
</task>
</tasks>