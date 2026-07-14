---
name: 01-cli
description: CLI Entry Point & Command Layer
executor: validator
status: complete
validated: yes
---

# Phase 01 Audit Findings — CLI Entry Point & Command Layer

**Executor:** validator (validated from auditor findings)
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** yes

---

## Findings

### CLI-001: Test failure due to .env configuration overriding Settings defaults

| Field | Value |
|-------|-------|
| **ID** | CLI-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_config.py |
| **Classification** | mandatory |

**Description:** The test `test_settings_creates_with_defaults` in `tests/test_config.py:20` asserts that `settings.ssl_verify is True`, but this test fails because the `.env` file at line 12 sets `VKDOWNLOADER_SSL_VERIFY=false`. Pydantic-settings automatically loads `.env` files, causing the test to receive `ssl_verify=False` instead of the expected `True`. This is a test isolation issue where environment configuration leaks into tests.

**Evidence:** 
- Test output: `AssertionError: assert False is True` at `tests/test_config.py:20` (confirmed via execution)
- `.env` file line 12: `VKDOWNLOADER_SSL_VERIFY=false`
- Settings class in `src/vkdownloader/config.py:101-106` uses `model_config = {"env_file": ".env", ...}`
- Default field value in Settings.ssl_verify is `True` (config.py:47-50)

**Recommendation:** Modify the test to either: (1) create Settings with explicit `ssl_verify=True` to override the `.env` value, or (2) use `Settings(model_config={"env_file": None})` or mock the environment variable before the test. This ensures test isolation from environment configuration.

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type was RUNTIME-ERROR. Reclassified as SPEC-DEVIATION because the code (Settings default=True, .env value=false) correctly implements configuration loading, but the test assertion incorrectly assumes defaults without accounting for .env. The code is correct; the test expectation is wrong.
> - **See also:** —

---

### CLI-002: Business logic function `_sanitize_title` placed in CLI layer

| Field | Value |
|-------|-------|
| **ID** | CLI-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py:25-33, src/vkdownloader/utils/security.py |
| **Classification** | mandatory |

**Description:** The `_sanitize_title` function (lines 25-33 in cli.py) implements filesystem sanitization logic - replacing invalid characters, stripping whitespace, and limiting string length to 100 characters. The utils layer (`src/vkdownloader/utils/security.py`) already contains `validate_output_path` for path security. This function logically belongs alongside other sanitization utilities in the security module.

**Evidence:** 
```python
# cli.py:25-33
def _sanitize_title(title: str) -> str:
    """Sanitize title for filesystem safety."""
    for char in '/\\:*?"<>|':
        title = title.replace(char, "_")
    return title.strip()[:100]
```

- Function is used in cli.py lines 136 and 263 for filename generation
- utils/security.py exists for security-related utilities
- Project rule: "Strict Separation of Concerns" requires clear layer boundaries

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Downgraded severity from MEDIUM to LOW. Upgraded classification from advisory to mandatory. Original type was BEST-PRACTICE. Reclassified as SPEC-DEVIATION because the function is clearly utility code that violates the project's separation of concerns rule. The utils/security.py module already exists for this purpose.
> - **See also:** —

---

### CLI-003: Refactor `_download_single` to reuse `perform_download` instead of duplicating logic

| Field | Value |
|-------|-------|
| **ID** | CLI-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/cli.py:111-144, src/vkdownloader/cli.py:240-283, src/vkdownloader/services/downloader.py:1034-1130 |
| **Classification** | mandatory |

**Description:** Both `_download()` (download command, cli.py:111-144) and `_download_single()` (batch_download command, cli.py:240-283) duplicate stream extraction and Settings/Extractor instantiation that `perform_download` already handles. Both call `extractor.extract_streams(url)` and create Settings/Extractor objects, but they do so *before* calling `perform_download`, which then repeats the extraction internally (downloader.py:1063-1071), causing redundant work. Additionally, `perform_download` ignores the passed `quality` parameter for stream selection, instead using `streams[0].url` directly (line 1077), making the quality selection in the CLI calls effectively unused.

**Evidence:** 
- cli.py:115-117 and cli.py:249-251 create Settings/VKVideoExtractor and call `extractor.extract_streams(url)`
- cli.py:126-127 and cli.py:253-254 use QualitySelector to select a stream based on quality
- cli.py:142-144 and cli.py:269-274 call `perform_download` passing `str(stream.quality)`
- downloader.py:1063-1077 creates Settings/VKVideoExtractor if None, then calls `extractor.extract_streams(url)` AGAIN, ignoring the quality selection and using `streams[0].url`
- This results in: (1) duplicate stream extraction calls per download, (2) quality selection being ignored in the service layer

**Implementation Plan:**

**Step 1: Extend `perform_download` signature in downloader.py**
```python
async def perform_download(
    url: str,
    quality: str,
    output_file: Path,
    method: DownloadMethod,
    extractor: VKVideoExtractor | None = None,
    settings: Settings | None = None,
    backoff_coordinator: Any | None = None,
    semaphore: asyncio.Semaphore | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
    video_data: VideoWithStreams | None = None,      # NEW: Optional pre-extracted data
    selected_stream: Stream | None = None,            # NEW: Optional pre-selected stream
) -> Path | None:
```

**Step 2: Modify `perform_download` logic (lines 1061-1077)**
```python
logger.info("starting_download", method=str(method), url=_strip_auth_params(url), quality=quality, output=str(output_file))

# Use pre-extracted data if provided, otherwise extract
if video_data is not None and selected_stream is not None:
    streams = video_data.streams
    m3u8_url = str(selected_stream.url)
    effective_quality = selected_stream.quality
elif extractor is None:
    settings = settings or Settings()
    extractor = VKVideoExtractor(settings=settings)
    video_data = await extractor.extract_streams(url)
    streams = video_data.streams
    if not streams:
        logger.error("no_streams_found", url=_strip_auth_params(url))
        return None
    m3u8_url = str(streams[0].url)
    effective_quality = quality
else:
    # extractor provided but no video_data - still need extraction
    video_data = await extractor.extract_streams(url)
    streams = video_data.streams
    if not streams:
        logger.error("no_streams_found", url=_strip_auth_params(url))
        return None
    m3u8_url = str(streams[0].url)
    effective_quality = quality
```

**Step 3: Refactor `_download()` in cli.py (lines 111-144)**
- Keep Settings/Extractor creation (needed for quality listing)
- Remove stream extraction and quality selection before `perform_download` call
- OR pass pre-extracted data: `perform_download(..., video_data=video, selected_stream=stream)`

**Step 4: Refactor `_download_single()` in cli.py (lines 240-283)**
- Keep Settings/Extractor creation (batch-coordination-specific)
- Remove stream extraction and quality selection before `perform_download` call
- Pass pre-extracted data: `perform_download(..., video_data=video, selected_stream=stream, ...)`

**Step 5: Update both calls to use effective_quality if needed

This eliminates:
- Redundant stream extraction (currently 2 calls per download)
- Quality selection being silently ignored in the service layer
- Code duplication between `download()` and `batch_download()` commands

---

### CLI-004: Direct access to private `_progress_manager._state` attribute in CLI

| Field | Value |
|-------|-------|
| **ID** | CLI-004 |
| **Severity** | LOW |
| **Type** | — |
| **Affected Modules** | src/vkdownloader/cli.py:53, src/vkdownloader/services/downloader_throttle.py:78-140 |
| **Classification** | — |

> ~~CLI-004: Direct access to private `_progress_manager._state` attribute in CLI~~ [REJECTED]
> 
> **Rejection reason:** This is intentional design documented in ProgressManager class docstring (downloader_throttle.py:84-91). The code explicitly states: "Direct tuple assignment to `_state[url_index]` is GIL-atomic in CPython, providing safe fire-and-forget semantics for progress callbacks invoked from async tasks. The async lock protects the read path in get_formatted_progress, ensuring consistent reads while callbacks may write concurrently." Using the async `update` method from a sync callback would require blocking, which this design intentionally avoids.

---

## Cross-Phase Conflict Detected

**CLI-001 and CFG-001 are duplicate findings** describing the same test failure. Both phases correctly identify the same root cause (test isolation from .env configuration). This represents a duplicate audit across phases rather than conflicting evidence.

### Cross-Phase Dependencies

| Finding | Depends On | Notes |
|---------|------------|-------|
| CLI-002 | CFG-002 | Both involve layer boundaries; CFG-002 addresses models package exports |
| CLI-001 | — | Standalone test fix |

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 0 | — |
| Reclassified | 3 | CLI-001 (RUNTIME-ERROR→SPEC-DEVIATION), CLI-002 (BEST-PRACTICE→SPEC-DEVIATION), CLI-003 (BEST-PRACTICE→SPEC-DEVIATION with caveat) |
| Merged | 0 | — |
| Rejected | 1 | CLI-004 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| CLI-004 | Direct access to private `_progress_manager._state` attribute | Intentional design per ProgressManager docstring; GIL-atomic write pattern with async-protected reads is valid concurrency approach |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| CLI-001 | RUNTIME-ERROR | SPEC-DEVIATION | Code correctly loads .env config; test expectation is incorrect |
| CLI-002 | BEST-PRACTICE | SPEC-DEVIATION | Violates separation of concerns; function belongs in utils layer |
| CLI-003 | BEST-PRACTICE | SPEC-DEVIATION | Partial violation: download logic duplicated from `perform_download`, though batch coordination is appropriately placed |

### Remaining Issues After Validation

| ID | Issue | Classification |
|----|-------|----------------|
| CLI-001 | Test assertion needs fix for .env isolation | Mandatory fix |
| CLI-002 | `_sanitize_title` should move to utils/security.py | Mandatory fix |
| CLI-003 | Refactor both `_download()` and `_download_single()` to pass pre-extracted data to `perform_download` | Mandatory fix |

>**Note:** CLI-001 and CFG-001 describe the same issue (duplicate finding across phases). Fixing CLI-001 will resolve CFG-001.

---

## Rollout Analysis

- CLI-001 and CLI-002 can be fixed independently
- CLI-003 requires changes to both cli.py and downloader.py; must be done as single commit
- No circular dependencies or rollout conflicts detected