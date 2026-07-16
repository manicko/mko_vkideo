# Research Report: HLSDownloadRequest Refactoring Analysis

**Task:** TASK_010_qlt_008_hlsdownloadrequest_research  
**Date:** 2026-07-15  
**Type:** Research  

## Executive Summary

The `HLSDownloadRequest` model is used in 2 production code instantiation sites and 9 test instantiation sites. It carries 3 runtime service objects (Settings, VKVideoExtractor, URLBackoffCoordinator) and 2 runtime state objects (asyncio.Semaphore, Callable) as attributes. The current monkeypatched `__init__` pattern is problematic but functional. **Approach 1 (extract services to function signature) is recommended** with moderate risk due to the need to update 2 call sites.

---

## 1. HLSDownloadRequest Model Definition Analysis

**Location:** `src/vkdownloader/models/dtos.py` (lines 24-85)

### Fields Categorized:

| Field | Type | Category | Notes |
|-------|------|----------|-------|
| `video_url` | `str` | Data | Primitive, no circular deps |
| `m3u8_url` | `str` | Data | Primitive, no circular deps |
| `output_file` | `Path` | Data | Standard library, no circular deps |
| `quality` | `str` | Data | Primitive, default "best" |
| `cookies` | `str \| None` | Data | Optional primitive |
| `settings` | `Settings \| None` | **Runtime Service** | Forward reference, monkeypatched |
| `extractor` | `VKVideoExtractor \| None` | **Runtime Service** | Forward reference, monkeypatched |
| `backoff_coordinator` | `URLBackoffCoordinator \| None` | **Runtime Service** | Forward reference, monkeypatched |
| `progress_callback` | `Callable[[str, int, int], None] \| None` | **Runtime State** | Callable type, no forward ref |
| `semaphore` | `asyncio.Semaphore \| None` | **Runtime State** | asyncio type, no forward ref |

### Current Anti-Pattern:
- Lines 27-42: Uses `arbitrary_types_allowed=True` to bypass Pydantic validation for service types
- Lines 59-70: `_ensure_model_rebuilt()` lazily imports and binds types at runtime
- Lines 73-85: Monkeypatches `__init__` to trigger model rebuild on first instantiation

---

## 2. Call Sites Inventory

### 2.1 Production Code Instantiation Sites

| File | Line | Context |
|------|------|---------|
| `src/vkdownloader/services/downloader.py` | 362 | Inside `download_with_ytdlp_with_resume_fallback` - passes: `settings`, `extractor`, `backoff_coordinator`, `semaphore`, `progress_callback` |
| `src/vkdownloader/services/downloader.py` | 641 | Inside `perform_download` (DownloadMethod.FFMPEG case) - passes: `settings`, `extractor`, `backoff_coordinator`, `semaphore`, `progress_callback` |

### 2.2 Production Code Attribute Access Sites

**File:** `src/vkdownloader/services/segment_downloader.py`

| Line | Attribute | Usage Pattern |
|------|-----------|---------------|
| 215 | `request.settings` | Check for None, fallback to default Settings() |
| 218 | `request.settings` | Assign to local `settings` variable |
| 235-236 | `request.cookies` | Read and add to headers dict |
| 249 | `request.extractor` | Pass to `_fetch_playlist_with_retry()` |
| 277 | `request.m3u8_url` | Pass to `urljoin()` for segment URL resolution |
| 287 | `request.backoff_coordinator` | Pass to `_download_segment()` |
| 334 | `request.progress_callback` | Check truthiness before calling |
| 340 | `request.progress_callback` | Call with `(video_id, downloaded_count, len(segments))` |

### 2.3 Function Signature Analysis

**Function:** `download_hls_with_resume(request: HLSDownloadRequest, semaphore: asyncio.Semaphore | None = None)`

**Observation:** The `semaphore` parameter is **redundant** - it's already in `HLSDownloadRequest` as `request.semaphore`. The function accepts it both ways:
1. From the `request.semaphore` attribute (used in instantiation)
2. As a direct parameter (used to override and for backward compatibility)

**Lines 260-264:** Function uses `semaphore` parameter when provided, falls back to `request.semaphore`, then to creating a new one based on settings.

---

## 3. Test File Analysis

**File:** `tests/test_hls_downloader.py`

### Test Instantiation Patterns:
- 9 `HLSDownloadRequest()` instantiations in tests
- Tests consistently provide `settings=test_settings` parameter
- Tests **do not** provide `extractor`, `backoff_coordinator`, or `semaphore` in most cases
- Tests mock the underlying functions (`_fetch_playlist_with_retry`, `_download_segment`, etc.)

### Mock Compatibility:
Tests create real `HLSDownloadRequest` instances, which will trigger the monkeypatch on first use. The current pattern works because:
1. Tests run in isolation
2. Mocks replace the actual download logic
3. No type validation is performed on mocked return values

---

## 4. Cross-Module Dependencies

| Module | HLSDownloadRequest Reference |
|--------|----------------------------|
| `src/vkdownloader/models/__init__.py` | Re-exports `HLSDownloadRequest` (line 3, 12) |
| `src/vkdownloader/services/segment_downloader.py` | TYPE_CHECKING import only (line 24) |
| `src/vkdownloader/services/downloader.py` | Direct import, instantiation (line 16) |
| `src/vkdownloader/services/downloader_throttle.py` | No direct reference (URLBackoffCoordinator only) |

**Key Insight:** `downloader_throttle.py` does NOT reference `HLSDownloadRequest`. The circular import concern (Settings, VKVideoExtractor, URLBackoffCoordinator) is handled by the monkeypatch, but is unnecessary since `downloader_throttle.py` only provides `URLBackoffCoordinator` without importing the model.

---

## 5. Approach Evaluation

### Approach 1: Keep data fields in Pydantic model, extract services in function signature

**Changes Required:**

```python
# Before
async def download_hls_with_resume(
    request: HLSDownloadRequest,
    semaphore: asyncio.Semaphore | None = None,
) -> Path | None:

# After  
async def download_hls_with_resume(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str = "best",
    cookies: str | None = None,
    settings: Settings | None = None,
    extractor: VKVideoExtractor | None = None,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    semaphore: asyncio.Semaphore | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> Path | None:
```

**Pros:**
- Eliminates monkeypatch anti-pattern entirely
- Restores Pydantic validation for data fields
- Makes all dependencies explicit in function signature
- Follows dependency injection best practices
- Type checkers can validate all parameter types at call sites
- Clearer separation between data and services

**Cons:**
- More verbose function signature (10 parameters vs 2)
- Requires updating 2 call sites in `downloader.py`
- `download_hls_with_resume` is exported and used by tests (9 test updates)

**Risk Assessment:** **MODERATE**
- Call sites are well-contained (both in `downloader.py`)
- Tests use simple instantiation patterns
- No external API consumers identified

### Approach 2: Use TYPE_CHECKING imports + model_rebuild without monkeypatch

**Changes Required:**
- Move imports to top of file with `TYPE_CHECKING` guards
- Call `HLSDownloadRequest.model_rebuild()` at module end after imports
- No runtime monkeypatch

**Pros:**
- Minimal code changes
- Preserves current instantiation pattern
- Eliminates monkeypatch
- Maintains backward compatibility

**Cons:**
- Still mixes data and service objects in one model
- `semaphore` and `progress_callback` are stateful, not configuration
- Pydantic validation still bypassed for service types (`arbitrary_types_allowed=True`)
- Model accepts `None` for services, leading to runtime checks

**Risk Assessment:** **LOW**
- Very minimal changes required
- No call site changes needed
- Still has architectural smell of mixing concerns

---

## 6. Recommendation

**Recommended Approach: 1 (Extract services to function signature)**

**Rationale:**
1. The current design conflates two different concerns:
   - **Data:** URL, output path, quality, cookies (configuration for a download)
   - **Services:** Settings, Extractor, BackoffCoordinator (runtime dependencies)
   - **State:** Semaphore, ProgressCallback (concurrency and notification primitives)

2. Option 1 cleanly separates these concerns, making the function signature explicitly declare all dependencies.

3. The 2 call sites in `downloader.py` are straightforward to update:
   - Line 361-374: `download_with_ytdlp_with_resume_fallback` call
   - Line 640-652: `perform_download` FFMPEG fallback call

4. The `semaphore` parameter already exists as a separate parameter, indicating the design was moving toward explicit parameters.

---

## 7. Implementation Path for Approach 1

### Step 1: Create new function signature
```python
async def download_hls_with_resume(
    video_url: str,
    m3u8_url: str,
    output_file: Path,
    quality: str = "best",
    cookies: str | None = None,
    settings: Settings | None = None,
    extractor: VKVideoExtractor | None = None,
    backoff_coordinator: URLBackoffCoordinator | None = None,
    semaphore: asyncio.Semaphore | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> Path | None:
```

### Step 2: Remove monkeypatch from `dtos.py`
- Remove `_ensure_model_rebuilt()`, `_lazy_init`, and `__init__` patch
- Keep `HLSDownloadRequest` as data-only model OR consider removing it entirely

### Step 3: Update call sites in `downloader.py`
- Lines 361-374: Unpack `HLSDownloadRequest` fields to keyword arguments
- Lines 640-652: Same unpacking pattern

### Step 4: Update tests
- 9 test instantiations need to be converted to direct parameter calls

---

## 8. Risk Mitigation

- Run full test suite after changes (`pytest tests/test_hls_downloader.py`)
- Verify backward compatibility if `HLSDownloadRequest` is kept as data-only model
- Consider deprecation path: keep old function signature wrapping new one if external consumers exist

---

## 9. Go/No-Go Decision

**GO** - Proceed with Approach 1

The refactoring will improve code quality, enable proper type checking, and eliminate the fragile monkeypatch pattern. The risk is manageable with 11 total call sites to update (2 prod + 9 test), all of which follow consistent patterns.