---
wave: 1
depends_on: []
files_modified:
  - src/vkdownloader/services/downloader_throttle.py
  - src/vkdownloader/services/downloader.py
  - tests/test_hls_downloader.py
depends_on_tasks: []
revision_notes: |
  - task_1: No changes needed - function signature aiohttp.ClientResponse | None is correct
  - task_2: Added explicit note that _download_segment must write response content after receiving from retry function
  - task_2: Added optional segment_index parameter to _download_segment for backward compatibility
  - task_3: Clarified delay placement: AFTER _download_segment succeeds but BEFORE semaphore exits
  - All changes maintain backward compatibility for parallel mode (max_concurrent_downloads > 1)
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
<li><code>_retry_429_with_backoff</code> function exists with signature returning <code>aiohttp.ClientResponse | None</code></li>
<li><code>_download_segment</code> integrates throttling when <code>max_concurrent_downloads=1</code>, writes response content after receiving from retry function</li>
<li>Existing parallel download tests pass unchanged (backward compatibility verified)</li>
<li>New tests for 429 retry behavior pass</li>
<li>Structured logging includes required fields: attempt, status, retry_after, segment_index, url</li>
<li>Anti-detection delay applies within semaphore boundary after successful download in sequential mode</li>
</ul>
</validation_criteria>

<execution_notes>
<ul>
<li>Do NOT integrate AdaptiveThrottle into concurrent download flow (creates race conditions)</li>
<li>Throttle applied per-segment, not globally (maintains isolation)</li>
<li>Use stdlib <code>random</code> module for jitter implementation</li>
</ul>
</execution_notes>

<tasks>
<task id="task_1" wave="1">
<name>Create internal _retry_429_with_backoff() function</name>
<file>src/vkdownloader/services/downloader_throttle.py</file>
<description>Create new module with retry function implementing AWS Full Jitter exponential backoff for 429/5xx errors.</description>
<spec>
<ul>
<li>Function signature: <code>async def _retry_429_with_backoff(session: aiohttp.ClientSession, segment_url: str, headers: dict[str, str], segment_index: int, max_retries: int = 3) -> aiohttp.ClientResponse | None</code></li>
<li>Implements AWS Full Jitter retry backoff: <code>random.uniform(0, base_delay * 2^attempt)</code> with 1s base for 429, capped at 30s</li>
<li>Respects Retry-After header if present (prioritize server guidance)</li>
<li>Logs with structured fields: attempt, status, retry_after, segment_index, url on each retry attempt</li>
<li>Returns response on success (200), None on permanent failure after max retries</li>
<li>Only retries on 429 and 5xx status codes</li>
</ul>
</spec>
</task>

<task id="task_2" wave="2" depends_on="task_1">
<name>Modify _download_segment function for single-thread mode throttling</name>
<file>src/vkdownloader/services/downloader.py</file>
<description>Update _download_segment to delegate to _retry_429_with_backoff when max_concurrent_downloads=1, writing response content after receiving it.</description>
<spec>
<ul>
<li>Import _retry_429_with_backoff from downloader_throttle module</li>
<li>Update function signature to accept max_concurrent_downloads: int = 4 and segment_index: int = 0 parameters (both optional for backward compatibility)</li>
<li>When max_concurrent_downloads=1: 
  <ul>
    <li>Call _retry_429_with_backoff for HTTP request (returns aiohttp.ClientResponse | None)</li>
    <li>Check returned response status == 200, then write response content to output_path</li>
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
<description>Add 1.5s base delay with jitter between successful segment requests when in sequential mode, ensuring delay applies within semaphore boundary.</description>
<spec>
<ul>
<li>Pass max_concurrent_downloads=settings.max_concurrent_downloads to _download_segment call</li>
<li>Pass segment_index=i to _download_segment for logging context</li>
<li>Apply 1.5s base delay + random jitter (0-0.5s) in download_segment_concurrent AFTER _download_segment returns True but BEFORE async with semaphore exits</li>
<li>Do NOT apply inter-segment delay when max_concurrent_downloads > 1 (parallel mode)</li>
<li>Delay placement: inside the semaphore context block, after successful download, before the final return</li>
</ul>
</spec>
</task>

<task id="task_4" wave="3" depends_on="task_2">
<name>Add unit tests for _retry_429_with_backoff</name>
<file>tests/test_hls_downloader.py</file>
<description>Create unit tests for the 429 retry mechanism.</description>
<spec>
<ul>
<li>Test successful response on first attempt (no retry) - verify function returns aiohttp.ClientResponse</li>
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

<task id="task_5" wave="3" depends_on="task_2">
<name>Add integration tests for sequential download mode</name>
<file>tests/test_hls_downloader.py</file>
<description>Create integration tests for sequential mode behavior and anti-detection delay.</description>
<spec>
<ul>
<li>Test max_concurrent_downloads=1 applies 1.5s inter-segment anti-detection delay (within semaphore context after download success)</li>
<li>Test parallel mode (max_concurrent_downloads > 1) does not apply inter-segment delay</li>
<li>Test structured log output from _retry_429_with_backoff contains required fields: attempt, status, retry_after, segment_index, url</li>
<li>Test max_concurrent_downloads=1 with 429 response triggers exponential backoff retry via _retry_429_with_backoff</li>
<li>Test existing parallel download tests remain passing (backward compatibility)</li>
</ul>
</spec>
</task>
</tasks>