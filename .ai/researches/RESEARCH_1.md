# Phase 1: Throttling and Concurrency Control - Research Findings

## Executive Summary

This research addresses implementing `_retry_429_with_backoff()` for segment downloads when `max_concurrent_downloads=1` (sequential/anti-detection mode). Key findings confirm AWS full jitter exponential backoff as the standard approach, and the `Retry-After` header as authoritative when present.

---

## 1. Current Architecture Analysis

### 1.1 Configuration Model (HIGH Confidence)
**Source**: `.kilo/agents/researcher.md` instructions + `src\vkdownloader\config.py`

The existing configuration provides adequate controls:
- `max_concurrent_downloads: int = Field(default=4, ge=1, le=16)` - Controls segment-level parallelism
- When `max_concurrent_downloads=1`: Already serializes via semaphore (natural asyncio behavior)
- No separate mode enum needed - semaphore value=1 naturally serializes requests

### 1.2 Current Download Flow (HIGH Confidence)
**Source**: `src\vkdownloader\services\downloader.py` (lines 238-255)

```python
async def _download_segment(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
) -> bool:
    try:
        async with session.get(segment_url, headers=headers) as response:
            if response.status == 200:
                with open(output_path, "wb") as f:
                    f.write(await response.read())
                return True
            logger.warning("segment_download_failed", status=response.status)
            return False  # No 429 handling, no retry
    except Exception as e:
        logger.error("segment_download_error", error=str(e))
        return False
```

**Gap**: Missing 429 (and 5xx) retry logic with exponential backoff.

### 1.3 AdaptiveThrottle Status (HIGH Confidence)
**Source**: `src\vkdownloader\infrastructure\adaptive_throttle.py` + `RESEARCH_ADAPTIVE_THROTTLE.md`

- `AdaptiveThrottle` exists but is NOT integrated into the download flow
- Designed for **time-based throttling**, not **response-based rate limiting**
- Would create race conditions in concurrent context (shared `current_delay` state)
- **Recommendation from existing research**: DO NOT integrate into concurrent flow

---

## 2. AWS Full Jitter Exponential Backoff (HIGH Confidence)

### 2.1 Standard Pattern
**Source**: AWS Architecture Blog (2015) via websearch, confirmed current via AWS SDK docs

AWS-recommended full jitter formula:
```
delay = random(0, base_delay * 2^attempt)
```

Where base delay varies by error type:
- **Throttling errors (429)**: 1000ms (1 second) base delay
- **Transient errors (5xx)**: 50ms base delay (per 2026 AWS SDK update)

### 2.2 Implementation Details
**Source**: AWS SDK for JavaScript retry behavior documentation

| Attempt | Backoff Type | Max Delay (with jitter) |
|---------|--------------|------------------------|
| 0 | Full jitter | random(0, 1s) |
| 1 | Full jitter | random(0, 2s) |
| 2 | Full jitter | random(0, 4s) |
| 3+ | Full jitter | random(0, 8s) capped at 30s |

**Key Implementation Notes**:
- Use `random.uniform(0, base_delay * 2^attempt)` for full jitter
- Cap maximum delay at 30 seconds (prevents excessive waits)
- Jitter prevents "thundering herd" pattern detection

---

## 3. Retry-After Header Handling (HIGH Confidence)

### 3.1 Header Format per RFC 7231
**Source**: MDN HTTP Retry-After documentation via aiohttp_retry GitHub issue

The `Retry-After` header can contain:
1. **Delay seconds** (integer): `Retry-After: 120` (wait 120 seconds)
2. **HTTP date** (RFC 7231): `Retry-After: Fri, 31 Dec 1999 23:59:59 GMT`

### 3.2 Priority Rules
**Source**: aiohttp_retry GitHub issue #59

When `Retry-After` is present:
1. Parse as integer seconds if numeric format
2. Parse as HTTP date if date format
3. **Prioritize over exponential backoff** when both are available
4. Use `response.headers.get('Retry-After')` via aiohttp's CIMultiDictProxy

### 3.3 aiohttp Response Headers Access
**Source**: aiohttp 3.14.1 documentation

```python
# Headers are case-insensitive via CIMultiDictProxy
retry_after = response.headers.get('Retry-After')
# Returns string or None
```

---

## 4. Recommended Implementation Strategy

### 4.1 `_retry_429_with_backoff()` Function Design

The function should be **internal** (prefixed with `_`) and **per-segment** scoped:

```python
async def _retry_429_with_backoff(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    segment_index: int,
    max_retries: int = 3,
) -> bool:
    """Download segment with 429/5xx retry logic. Internal helper for _download_segment."""
    # Implementation details below
```

### 4.2 Retry Logic Flow

1. **Attempt 0**: Try request
   - On 429: Parse `Retry-After` header if present, else `random.uniform(0, 1s)`
   - On 5xx: `random.uniform(0, 0.05s)` (AWS transient error base)
2. **Attempt 1**: Exponential backoff `random.uniform(0, 2s)`
3. **Attempt 2**: Exponential backoff `random.uniform(0, 4s)`
4. **Attempt 3**: Exponential backoff `random.uniform(0, 8s)` capped at 30s
5. **After max_retries**: Return False (let semaphore handle overall progress)

### 4.3 Integration Point

Modify `_download_segment` to accept `segment_index` and conditionally apply retry logic:

```python
async def _download_segment(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict[str, str],
    segment_index: int = 0,
    max_retries: int = 3,
) -> bool:
    # When max_concurrent_downloads=1 (single-thread mode), apply retry logic
    # Otherwise, use simpler flow for parallel downloads
```

**Note**: The decision context specifies retry logic applies when `max_concurrent_downloads=1`, not as a general rule.

---

## 5. Structured Logging Requirements (HIGH Confidence)

**Source**: Phase context + structlog usage in existing codebase

Log retry attempts with this structured format:
```python
logger.warning(
    "segment_retry_429",
    attempt=attempt,
    status=response.status,
    retry_after=retry_after_seconds,
    segment_index=segment_index,
    url=_strip_auth_params(segment_url),
)
```

Required fields:
- `attempt`: Integer retry attempt number (0-indexed)
- `status`: HTTP status code (429 or 5xx)
- `retry_after`: Seconds from header (if present)
- `segment_index`: Index of segment being downloaded
- `url`: Sanitized URL (strip auth params)

---

## 6. Key Implementation Decisions

### 6.1 Jitter Implementation
**Source**: AWS documentation + Python standard library

Use `random.uniform(0, base_delay)` for full jitter:
```python
import random
delay = random.uniform(0, base_delay * (2 ** attempt))
```

### 6.2 Rate Limit Header Priority
**Source**: Phase context specification

Priority order:
1. `Retry-After` header (highest priority, server guidance)
2. `X-RateLimit-Reset` or similar (secondary)
3. Exponential backoff (fallback)

### 6.3 Retry Count
**Source**: Phase context specification

Confirmed: 3 retry attempts maximum per segment.

### 6.4 Status Codes for Retry
**Source**: Phase context + AWS SDK patterns

Retried status codes:
- **429** (Too Many Requests) - primary target
- **5xx** (500, 502, 503, 504) - transient server errors

Not retried:
- 400 (Bad Request)
- 401/403 (auth errors)
- 404 (not found)

---

## 7. What the Planner Needs to Know

### 7.1 Clear Requirements
- Implement `_retry_429_with_backoff()` as internal async function in `downloader.py`
- Integrate into `_download_segment` **only when** `max_concurrent_downloads=1`
- Use full jitter exponential backoff: `random.uniform(0, 2^attempt seconds)`
- Respect `Retry-After` header when present (prioritize server guidance)
- Log retry attempts with structured fields: `attempt`, `status`, `retry_after`, `segment_index`

### 7.2 Dependencies
- `random` module (stdlib) - already used in codebase
- `structlog` - already in use via `get_logger(__name__)`
- `aiohttp` - existing session with `response.headers` access

### 7.3 No External Dependencies Needed
- Do NOT use `AdaptiveThrottle` - it's unsuitable for concurrent segment downloads
- Do NOT add `aiohttp_retry` package - custom logic is simpler and more targeted
- Existing semaphore provides sufficient concurrency control

### 7.4 Risk Points to Address in Planning
1. **Backward compatibility**: Ensure parallel downloads (max_concurrent_downloads > 1) are not slowed down
2. **Semaphore interaction**: When `max_concurrent_downloads=1`, the retry waits should happen inside the semaphore context to maintain serialization
3. **Timeout handling**: Current `session.get()` doesn't have explicit timeout - uses client default

---

## 8. Sources

| Source | Confidence | Notes |
|--------|------------|-------|
| AWS SDK Retry Behavior Documentation (2026-07-05) | HIGH | Current official AWS guidance |
| AWS Architecture Blog (2015, still referenced in 2026 docs) | HIGH | Foundational jitter/backoff pattern |
| aiohttp 3.14.1 Documentation | HIGH | Response headers access via CIMultiDictProxy |
| aiohttp_retry GitHub Issue #59 | MEDIUM | Retry-After header handling patterns |
| Existing `RESEARCH_ADAPTIVE_THROTTLE.md` | HIGH | Confirms NO-GO for AdaptiveThrottle integration |