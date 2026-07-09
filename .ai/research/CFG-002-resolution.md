# Research: Resolving Unused Configuration Fields (CFG-002)

## Executive Summary

CFG-002 identifies six configuration fields defined in `Settings` but not integrated into the service layer:

| Field | Lines | Status | Currently Used By |
|-------|-------|--------|-------------------|
| `vk_api_url`, `vk_api_version` | 17-24 | **Unused** | Nothing |
| `request_delay_min`, `request_delay_max` | 43-52 | **Unused** | Tests only |
| `concurrency` | 59-64 | **Unused** | Tests only |
| `timeout_seconds` | 83-88 | **Unused** | Tests only |

---

## Architecture Analysis

### Current Configuration Flow

```
Settings (config.py)
    │
    ├── user_agent, accept_language, locale, timezone ──→ BrowserManager, HttpClient
    ├── max_retries ──→ HttpClient.get() (retry loop)
    ├── download_timeout ──→ HttpClient.__aenter__() (timeout param)
    ├── max_concurrent_downloads ──→ cli.py:138 (semaphore for batch downloads)
    └── download_dir ──→ cli.py:48,51,116 (output directory)
```

### Key Observations

1. **VK API fields** are completely orphaned - no VK API integration exists
2. **Delay fields** (`request_delay_min/max`) could integrate with `AdaptiveThrottle`
3. **Concurrency fields** (`concurrency` vs `max_concurrent_downloads`) are redundant - both control download parallelism
4. **Timeout fields** (`timeout_seconds` vs `download_timeout`) are redundant - both control request timeouts

---

## Field-by-Field Assessment

### 1. VK API Fields (`vk_api_url`, `vk_api_version`)

**Status: Remove**

- No VK API client code exists anywhere in the codebase
- Project uses `yt-dlp` (primary) and `Playwright` (fallback) for extraction, not direct API
- Implementation plan for VK API was never executed
- No test fixtures or documentation references them

**Confidence: HIGH** - No evidence of planned implementation, orphaned from inception.

---

### 2. Request Delay Fields (`request_delay_min`, `request_delay_max`)

**Status: Option A - Remove OR Option B - Integrate**

**Option A (Remove):**
- `AdaptiveThrottle` already has hardcoded RPM-based delays (`base_rpm=20, max_rpm=60`)
- Adding settings integration would require refactoring `AdaptiveThrottle`
- Tests reference them but don't actually test delay behavior

**Option B (Integrate):**
- `AdaptiveThrottle` could be configured via settings
- Would require constructor changes: `__init__(self, settings: Settings | None = None)`
- Would provide user control over rate limiting

**Current `AdaptiveThrottle` usage:**
```python
# browser.py:157, downloader.py:115 - no instantiation found
# The class exists but is never instantiated in production code
```

**Confidence: HIGH** - Class exists but unused; integration would require significant changes.

---

### 3. Concurrency Field

**Status: Remove**

The project has TWO separate concurrency-related fields:
- `concurrency` (default=8, lines 59-64) - **never used**
- `max_concurrent_downloads` (default=4, lines 77-82) - **actively used in cli.py:138**

Both serve the identical purpose (controlling parallel downloads) with different names and defaults.
The inconsistency itself is a design problem.

**Confidence: HIGH** - Direct redundancy with an actively-used field.

---

### 4. Timeout Field

**Status: Remove**

The project has TWO separate timeout-related fields:
- `timeout_seconds` (default=30, lines 83-88) - **never used**
- `download_timeout` (default=300, lines 65-70) - **actively used in http_client.py:41**

**Usage comparison:**
- `http_client.py:41`: `timeout = aiohttp.ClientTimeout(total=self.settings.download_timeout)`
- `timeout_seconds` is referenced in `tests/conftest.py:14` and `docs/01-tools/api-reference.md:330`

**Confidence: HIGH** - Direct redundancy with an actively-used field.

---

## Recommended Solution

**Remove all six unused fields** (`vk_api_url`, `vk_api_version`, `request_delay_min`, `request_delay_max`, `concurrency`, `timeout_seconds`) and update dependent files.

### Rationale

1. **Simplicity:** The alternative would require integrating unused settings, but:
   - `AdaptiveThrottle` exists but is never instantiated - no immediate need for delay settings
   - `concurrency` and `timeout_seconds` duplicate existing working fields

2. **Consistency:** Removes documentation/code mismatches

3. **Type Safety:** Reduces potential for user confusion about which field to use

### Implementation Changes

| File | Action |
|------|--------|
| `src/vkdownloader/config.py` | Remove 6 fields (lines 17-24, 43-52, 59-64, 83-88) |
| `tests/conftest.py` | Remove `concurrency=2` and `timeout_seconds=10` from `test_settings()` fixture |
| `docs/01-tools/api-reference.md` | Remove references to `timeout_seconds`, `request_delay_min/max` |

### Alternative Considered: Integrate Delay Settings

If rate limiting control is desired:
1. Instantiate `AdaptiveThrottle` in `HttpClient` or `VKVideoExtractor`
2. Add `throttle: AdaptiveThrottle` field to `HttpClient`
3. Call `throttle.wait()` before HTTP requests
4. This would be a **new feature**, not completing a planned one

**Decision: Defer** - Feature not currently needed; `AdaptiveThrottle` is unused in production.

---

## Verification Steps

After implementation:
1. Run `uv run ruff check` - ensure no import/type issues
2. Run `uv run mypy` - ensure no type errors from removed fields
3. Run `uv run pytest` - ensure tests still pass with updated fixture

---

## References

- Config file: `src/vkdownloader/config.py`
- HTTP client: `src/vkdownloader/infrastructure/http_client.py`
- CLI usage: `src/vkdownloader/cli.py:138`
- Throttle class: `src/vkdownloader/infrastructure/adaptive_throttle.py`
- Tests: `tests/conftest.py`
- Docs: `docs/01-tools/api-reference.md:330-332`
- Plans: `.ai/plans/02-implementation-details.md:129-132`