---
wave: 1
depends_on: []
files_modified:
  - src/vkdownloader/services/downloader_throttle.py
  - src/vkdownloader/services/downloader.py
  - tests/test_hls_downloader.py
depends_on_tasks: []
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
<li><code>_retry_429_with_backoff</code> function exists and handles all retry scenarios</li>
<li><code>_download_segment</code> integrates throttling when <code>max_concurrent_downloads=1</code></li>
<li>Existing parallel download tests pass unchanged</li>
<li>New tests for 429 retry behavior pass</li>
<li>Structured logging includes required fields</li>
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
<li>Logs with structured fields: attempt, status, retry_after, segment_index, url</li>
<li>Returns response on success (200), None on permanent failure after max retries</li>
<li>Only retries on 429 and 5xx status codes</li>
</ul>
</spec>
</task>

<task id="task_2" wave="2" depends_on="task_1">
<name>Modify _download_segment function for single-thread mode throttling</name>
<file>src/vkdownloader/services/downloader.py</file>
<description>Update _download_segment to delegate to _retry_429_with_backoff when max_concurrent_downloads=1.</description>
<spec>
<ul>
<li>Import _retry_429_with_backoff from downloader_throttle module</li>
<li>Update function signature to accept max_concurrent_downloads: int = 4 parameter</li>
<li>When max_concurrent_downloads=1: delegate to _retry_429_with_backoff for HTTP requests</li>
<li>When max_concurrent_downloads > 1: use existing direct download logic (no throttling)</li>
</ul>
</spec>
</task>

<task id="task_3" wave="2" depends_on="task_1">
<name>Update download_segment_concurrent coroutine with anti-detection delay</name>
<file>src/vkdownloader/services/downloader.py</file>
<description>Add 1.5s base delay with jitter between successful segment requests when in sequential mode.</description>
<spec>
<ul>
<li>Pass max_concurrent_downloads=settings.max_concurrent_downloads to _download_segment call</li>
<li>Pass segment_index=i to _download_segment for logging context</li>
<li>When inside semaphore and max_concurrent_downloads=1: apply 1.5s base delay + random jitter (0-0.5s) after successful segment download</li>
<li>Do NOT apply inter-segment delay when max_concurrent_downloads > 1 (parallel mode)</li>
</ul>
</spec>
</task>

<task id="task_4" wave="3" depends_on="task_2">
<name>Add unit tests for _retry_429_with_backoff</name>
<file>tests/test_hls_downloader.py</file>
<description>Create unit tests for the 429 retry mechanism.</description>
<spec>
<ul>
<li>Test successful response on first attempt (no retry)</li>
<li>Test 429 retry with exponential backoff: attempt 0 random(0,1s), attempt 1 random(0,2s), attempt 2 random(0,4s)</li>
<li>Test Retry-After header overrides calculated delay when present</li>
<li>Test max retries (3) exceeded returns None</li>
<li>Test 5xx status codes trigger retry</li>
<li>Test non-retry status codes (403, 404) return None immediately without retry</li>
<li>Test delay capped at 30 seconds maximum</li>
</ul>
</spec>
</task>

<task id="task_5" wave="3" depends_on="task_2">
<name>Add integration tests for sequential download mode</name>
<file>tests/test_hls_downloader.py</file>
<description>Create integration tests for sequential mode behavior and anti-detection delay.</description>
<spec>
<ul>
<li>Test max_concurrent_downloads=1 applies 1.5s inter-segment anti-detection delay</li>
<li>Test parallel mode (max_concurrent_downloads > 1) does not apply inter-segment delay</li>
<li>Test structured log output contains required fields: attempt, status, retry_after, segment_index, url</li>
<li>Test max_concurrent_downloads=1 with 429 response triggers exponential backoff retry</li>
</ul>
</spec>
</task>
</tasks>