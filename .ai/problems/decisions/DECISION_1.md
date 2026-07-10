# Phase 1: Throttling and Concurrency Control - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement configurable download concurrency (sequential vs parallel) and adaptive throttling for anti-detection when downloading single-threaded. Systems may detect and block parallel segment downloads, so users need control over concurrency and automatic throttling for sensitive single-thread scenarios.
</domain>

<decisions>
## Implementation Decisions

### Concurrency Configuration Model

- **`max_concurrent_downloads` controls segment-level parallelism** (default: 4), respecting existing config bounds (1-16)
- **When `max_concurrent_downloads=1`**: Treated as sequential download mode for anti-detection purposes
- **No separate download mode enum** - concurrency is the single control surface for rate limiting
- **Architecture uses `asyncio.Semaphore`** which naturally handles both cases: value=1 serializes, values >1 parallelize

### AdaptiveThrottle Integration Strategy

- **DO NOT integrate AdaptiveThrottle into concurrent download flow** - it creates race conditions and serializes requests
- **AdaptiveThrottle is designed for sequential APIs** with time-based delays, not parallel segment downloads
- **For single-thread mode (`max_concurrent_downloads=1`)**: Add dedicated 429 retry handler with exponential backoff
- **Create new internal `_retry_429_with_backoff()` function** for segment downloads, separate from AdaptiveThrottle

### Default Behavior for Anti-Detection

- **When `max_concurrent_downloads=1`**: Enable automatic per-segment throttling with these defaults:
  - Base delay: 1.5 seconds between segment requests (conservative, ~40 RPM)
  - Exponential backoff: 1s, 2s, 4s on 429 responses
  - Jitter: random 0-0.5s to avoid pattern detection
  - Max retry attempts: 3 per segment
- **Respect `Retry-After` header** when present (prioritize server guidance)
- **Throttle applied per-segment**, not globally (maintains isolation)

### HTTP 429 Retry Strategy

- **Retry pattern**: exponential backoff with full jitter (AWS-recommended)
  - Attempt 0: random(0, 1s) + Retry-After if present
  - Attempt 1: random(0, 2s)
  - Attempt 2: random(0, 4s)
  - Attempt 3: random(0, 8s)
- **Cap maximum delay at 30 seconds**
- **Only retry on 429 and 5xx status codes** (not all errors)
- **Log retry attempts** with structured logging including `attempt`, `status`, `retry_after`, `segment_index`
- **Fail segment permanently** after max retries — let semaphore concurrency handle overall progress

### KiloCode's Discretion

- **Jitter implementation details**: Use `random.uniform(0, baseDelay)` for full jitter
- **Rate limit headers parsing**: Prioritize `Retry-After` over `X-RateLimit-*` headers
- **Exact retry count**: 3 retries confirmed, but timing/jitter parameters flexible
- **Batch merge timing**: Whether throttle affects post-download merging (no impact expected)
</decisions>

<specifics>
## Specific Requirements from Research

Based on web scraping best practices (Postman 2025, Zuplo 2026, APIScout 2026):

1. **Retry-After header handling** - Always check server guidance first before applying backoff
2. **Full jitter (not partial)** - Randomize within entire backoff window to prevent synchronized retries
3. **Per-endpoint throttling** - If multiple CDN endpoints are detected in future, separate throttle states needed
4. **Semaphore-based concurrency is correct** - No changes to existing `asyncio.Semaphore(settings.max_concurrent_downloads)` pattern

## Implementation Constraints

- Must NOT break existing parallel download functionality
- Must NOT introduce race conditions in throttle state
- Must work within existing Pydantic v2 + StrEnum patterns
- Must integrate cleanly with current `_download_segment()` function
</specifics>

<deferred>
## Deferred Ideas

- **Per-endpoint rate limiting** - Multiple CDN endpoints may need independent throttle states (future enhancement)
- **AdaptiveThrottle redesign** - Current class needs thread-safe refactor for concurrent use (out of scope)
- **Circuit breaker pattern** - Stop all downloads when 429 rate exceeds threshold (complexity for later)
- **Proxy rotation integration** - For distributed rate limiting across IPs (requires proxy infrastructure)
- **Telemetry-driven throttling** - Adjust rates based on rolling success/error metrics (advanced feature)
</deferred>

---

_Phase: 01-throttle-bypass_
_Context gathered: 2026-07-10_