---
name: 09-structural-quality
description: Phase 09 Audit Findings — Structural Code Quality (Validated)
agent: validator
alwaysApply: false
---

# Phase 09 Audit Findings — Structural Code Quality (Validated)

**Executor:** validator  
**Source:** `.ai/audit/09-structural-quality/findings.md`  
**Base:** Phase 09 Audit  
**Status:** complete  
**Validated:** yes

---

## Findings

### STR-001: Function `_merge_segments_batched` exceeds recommended length and complexity

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Function spans 86 lines with cyclomatic complexity 14 (rank C). The function is actively used (called from `download_hls_with_resume` at line 140). Per project rule #4 (single responsibility) and #15 (small functions), this is a valid modularization opportunity with high ROI.

| Field | Value |
|-------|-------|
| **ID** | STR-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `_merge_segments_batched` function (lines 208-293) has cyclomatic complexity of 14 (rank C) and spans approximately 85 lines of effective code. It combines two distinct responsibilities: batch processing of segments and final merge orchestration. The function has multiple return points (3 returns) and deeply nested control flow with batch processing loops inside conditional blocks.

**Evidence:**
```
radon cc output:
src/vkdownloader/services/downloader.py
    F 208:0 _merge_segments_batched - C (14)

Nesting analysis (indentation levels):
- Line 214: for batch_start in range(...) [level 1]
- Line 225: with open(file_list_path) [level 2]
- Line 226: for segment_path in batch_files [level 3]
- Line 247: if process.returncode != 0 [level 3]
- Line 253: for segment_path in batch_files [level 3] (cleanup loop)
- Line 260: if temp_files [level 2]
- Line 262: with open(final_list_path) [level 3]
- Line 263: for temp_file in temp_files [level 4]
- Line 284: if process.returncode == 0 [level 4]
- Line 287: for tf in temp_files [level 5]

Return statements: 3 (lines 250, 289, 293)
Function spans lines 208-293: 86 lines (excluding docstring)
```

**Recommendation:** Extract `_merge_batch_segments(batch_files: list[Path], temp_dir: Path) -> list[Path]` for batch merging logic (lines 214-253), returning list of merged temp files. Extract `_perform_final_merge(temp_files: list[Path], output_file: Path) -> bool` for final merge orchestration (lines 260-293). Extract `_build_ffmpeg_concat_command(input_files: list[Path]) -> list[str]` for command building. This reduces complexity from 14 to ~6 per function. Effort: medium. Priority: recommended.

---

### STR-002: Function `_parse_m3u8_playlist` has excessive nesting depth

> **Validation Note:**
> - **Action:** REJECTED
> - **Rejection Reason:** `_parse_m3u8_playlist` is confirmed dead code - never called anywhere in the codebase (verified via grep search, only definition found). Per SRV-001 (Phase 03) and the mandatory spec cross-reference rule: dead code should be removed, not refactored. Recommending refactoring of dead code is wasteful and adds unnecessary noise to the codebase.

| Field | Value |
|-------|-------|
| **ID** | STR-002 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** The `_parse_m3u8_playlist` method (lines 218-281) has cyclomatic complexity of 12 (rank C) and nesting depth of 6 in its inner parsing loop. The function handles parsing m3u8 playlist tags while also checking stream URLs and building Stream objects, combining multiple concerns. This also violates the single-responsibility principle by mixing HTTP fetching with parsing logic and importing modules at function scope (line 236).

**Evidence:**
```
radon cc output:
src/vkdownloader/services/extractor.py
    M 218:4 VKVideoExtractor._parse_m3u8_playlist - C (12)

Nesting analysis (indentation levels):
- Line 238: for i, line in enumerate(lines) [level 1]
- Line 239: if line.startswith("#EXT-X-STREAM-INF") [level 2]
- Line 245: if i + 1 < len(lines) [level 3]
- Line 247: if stream_url [level 4]
- Line 249: if not stream_url.startswith("http") [level 5]
- Line 255: if resolution_match [level 6]
- Line 270: if not streams [level 2]
- Line 271: if url.endswith(".m3u8") [level 3]

Function spans lines 218-281: 64 lines (excluding docstring)
```

**Recommendation:** Extract into `_parse_stream_info(line, next_line, base_url)` returning optional Stream. Extract resolution and bandwidth parsing into helpers `_extract_bandwidth(line)` and `_parse_resolution(resolution_string)`.

---

### STR-003: Function `download_hls_with_resume` has 6 parameters exceeding limit

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Function has 6 parameters exceeding the recommended limit of 5. The function is actively used (called from main.py at lines 78, 148, 166). Per project rule #4 and #15, this is a valid modularization opportunity with high ROI.

| Field | Value |
|-------|-------|
| **ID** | STR-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `download_hls_with_resume` function (line 71) has 6 parameters (m3u8_url, output_file, quality, cookies, settings, extractor), exceeding the recommended limit of 5. This indicates the function may be doing too much and is harder to call and test.

**Evidence:**
```
src/vkdownloader/services/downloader.py:71-77
async def download_hls_with_resume(
    m3u8_url: str,
    output_file: Path,
    quality: str = "best",
    cookies: str | None = None,
    settings: Settings | None = None,
    extractor=None,
) -> Path | None:

Nesting analysis:
- Line 114: async with aiohttp.ClientSession [level 1]
- Line 116: if not playlist_content [level 2]
- Line 123: for i in range(downloaded_count, len(segments)) [level 2]
- Line 125: if not segment_url.startswith("http") [level 3]
- Line 129: if not segment_path.exists() [level 3]
- Line 131: if not success [level 4]
- Line 138: if downloaded_count == len(segments) [level 2]
- Line 141: if result [level 3]

Function spans lines 71-145: 75 lines (excluding docstring)
Return statements: 2 (lines 117, 143/145 - early returns at 2 locations)
```

**Recommendation:** Create `HLSDownloadRequest` dataclass with fields: `url: str, output_file: Path, quality: str, cookies: str | None, settings: Settings, extractor: VKVideoExtractor | None`. Modify function signature to `download_hls_with_resume(request: HLSDownloadRequest) -> Path | None`. This consolidates 6 parameters into 1 object and aligns with project rule #9 (Type Safety). Effort: small. Priority: recommended.

---

### STR-004: Function `_fetch_playlist_with_retry` has 6 parameters exceeding limit

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Function has 6 parameters exceeding limit. This function is actively used (called from `download_hls_with_resume` at line 115). Valid BEST-PRACTICE finding. Note: STR-008 is a duplicate of this same function - see merge below.

| Field | Value |
|-------|-------|
| **ID** | STR-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `_fetch_playlist_with_retry` function (line 148) has 6 parameters (session, m3u8_url, headers, extractor, settings, max_retries), exceeding the recommended limit of 5. It also has nesting depth of 5 inside its retry loop.

**Evidence:**
```
radon cc output:
src/vkdownloader/services/downloader.py
    F 148:0 _fetch_playlist_with_retry - B (8)

src/vkdownloader/services/downloader.py:148-154
async def _fetch_playlist_with_retry(
    session: aiohttp.ClientSession,
    m3u8_url: str,
    headers: dict,
    extractor,
    settings: Settings,
    max_retries: int = 3,
) -> str | None:
```

**Recommendation:** Create `PlaylistRequest` dataclass with `session, m3u8_url, headers, extractor, settings` fields. Add `get_max_retries() -> int` method to `Settings` class. Modify signature to `_fetch_playlist_with_retry(request: PlaylistRequest, max_retries: int = 3) -> str | None`. This reduces parameters from 6 to 2 and aligns with project rule #4 (Single Responsibility). Effort: small. Priority: recommended.

---

### STR-005: `QualitySelector.select` has complexity of 11 and nesting of 4

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Function complexity 11, nesting depth 4. The match/case structure with embedded loop is reasonable, but helper extraction would improve readability. Valid modularization opportunity.

| Field | Value |
|-------|-------|
| **ID** | STR-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/quality.py |
| **Classification** | advisory |

**Description:** The `select` method has cyclomatic complexity of 11 (rank C) with nesting depth of 4 due to the match/case structure combined with a for loop containing an if statement. While not critical, this could be simplified for readability.

**Evidence:**
```
radon cc output:
src/vkdownloader/services/quality.py
    M 14:4 QualitySelector.select - C (11)

Nesting analysis (line numbers):
- Line 31: match quality [level 1]
- Line 32: case QualityEnum.BEST [level 2]
- Line 35: case QualityEnum.WORST [level 2]
- Line 38: case _ [level 2]
- Line 41: for stream in streams [level 3]
- Line 43: if stream_quality == quality_str [level 4]
```

**Recommendation:** Extract the quality matching logic into `_find_quality_match(streams, quality_str)` and `_get_fallback_stream(streams)` helper methods. This reduces nesting and makes each path clearer.

---

### STR-006: `HttpClient.download_file` has nesting depth of 6

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Nesting depth of 6 is excessive. While complexity is only 6 (rank B), the deep nesting makes error handling paths harder to follow. Valid refactoring target.

| Field | Value |
|-------|-------|
| **ID** | STR-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/infrastructure/http_client.py |
| **Classification** | advisory |

**Description:** The `download_file` method has cyclomatic complexity of 6 (rank B) but reaches nesting depth of 6 inside the async context manager. The deep nesting makes error handling paths harder to follow.

**Evidence:**
```
src/vkdownloader/infrastructure/http_client.py:106-151
async def download_file(
    self,
    url: str,
    output_path: Path,
    progress_callback: Callable[[int, int], None] | None = None,
) -> None:

Nesting analysis:
- Line 127: try [level 1]
- Line 128: async with self.session.get(url) [level 2]
- Line 131: if content_length is not None [level 3]
- Line 137: with output_path.open("wb") [level 4]
- Line 138: async for chunk in response.content.iter_chunked [level 5]
- Line 142: if progress_callback is not None [level 6]

Function spans lines 106-151: 46 lines (excluding docstring)
```

**Recommendation:** Extract `_write_chunk_to_file(chunk: bytes, file_handle) -> int` and `_update_progress(downloaded: int, total: int, callback) -> None` helpers. Rewrite as:
```python
async def download_file(...):
    try:
        async with self.session.get(url) as response:
            if response.status == 200:
                with output_path.open("wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        self._write_chunk(chunk, f)
                        self._update_progress(downloaded, content_length, progress_callback)
    finally:
        # cleanup if needed
```
This reduces nesting depth from 6 to 2. Effort: small. Priority: recommended.

---

### STR-007: `_extract_urls_from_json` has nesting depth of 4 with multiple nested iterations

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Nesting depth 4 with recursive calls. The function is actively used (called from `_intercept_response` at line 64). Valid refactoring target for improved readability.

| Field | Value |
|-------|-------|
| **ID** | STR-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/infrastructure/network_monitor.py |
| **Classification** | advisory |

**Description:** The `_extract_urls_from_json` method has cyclomatic complexity of 9 (rank B) and nesting depth of 4. It handles both dict and list recursion with nested conditionals inside the iteration, making it a cognitive load hotspot.

**Evidence:**
```
radon cc output:
src/vkdownloader/infrastructure/network_monitor.py
    M 68:4 NetworkMonitor._extract_urls_from_json - B (9)

Nesting analysis:
- Line 75: if isinstance(data, dict) [level 1]
- Line 76: for value in data.values() [level 2]
- Line 77: if isinstance(value, str) [level 3]
- Line 79: if normalized not in self.m3u8_urls [level 4]
- Line 82: elif isinstance(value, (dict, list)) [level 3]
- Line 84: self._extract_urls_from_json(value) [level 3, recursive]
- Line 84: elif isinstance(data, list) [level 2]
- Line 85: for item in data [level 3]
- Line 86: self._extract_urls_from_json(item) [level 3, recursive]

Function spans lines 68-86: 19 lines (excluding docstring)
```

**Recommendation:** Refactor using early returns to flatten control flow:
```python
def _extract_urls_from_json(self, data: dict | list) -> None:
    if isinstance(data, dict):
        for value in data.values():
            self._process_value(value)
        return
    if isinstance(data, list):
        for item in data:
            self._extract_urls_from_json(item)

def _process_value(self, value: Any) -> None:
    if isinstance(value, str):
        self._add_m3u8_url(value)
    elif isinstance(value, (dict, list)):
        self._extract_urls_from_json(value)
```
This reduces nesting depth from 4 to 2. Effort: small. Priority: recommended.

---

### STR-008: `_fetch_playlist_with_retry` has nesting depth of 5 in retry loop

> **Validation Note:**
> - **Action:** Merged into STR-004
> - **Detail:** This finding describes the same function `_fetch_playlist_with_retry` as STR-004 with overlapping evidence (nesting depth 5 vs 5). STR-004 covers the parameter count issue and this nesting issue together. Merging to avoid duplication.

| Field | Value |
|-------|-------|
| **ID** | STR-008 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `_fetch_playlist_with_retry` function has nesting depth of 5 inside its retry loop, combining exception handling with conditional response logic.

**Evidence:**
```
src/vkdownloader/services/downloader.py:148-174
async def _fetch_playlist_with_retry(
    session: aiohttp.ClientSession,
    m3u8_url: str,
    headers: dict,
    extractor,
    settings: Settings,
    max_retries: int = 3,
) -> str | None:

Nesting analysis:
- Line 159: for attempt in range(max_retries) [level 1]
- Line 160: try [level 2]
- Line 161: async with session.get(...) [level 3]
- Line 162: if response.status == 200 [level 4]
- Line 164: if response.status in (403, 410) [level 4]
- Line 166: await extractor.extract_streams_with_cookies [level 5]
- Line 167: if streams [level 5]

Function spans lines 148-174: 27 lines (excluding docstring)
```

**Recommendation:** Extract `_handle_token_refresh(response: aiohttp.ClientResponse, extractor, video_url: str) -> str | None` to handle 403/410 responses. Rewrite to reduce nesting:
```python
async def _fetch_playlist_with_retry(...):
    for attempt in range(max_retries):
        async with session.get(...) as response:
            if response.status == 200:
                return await response.text()
            if response.status in (403, 410):
                result = await self._handle_token_refresh(response, extractor, video_url)
                if result:
                    return result
    return None
```
Note: `video_url` must be added as parameter to enable proper token refresh (see DF-012). Effort: small. Priority: mandatory (critical architectural fix).

---

### STR-009: `_download_segment` has nesting depth of 4 with multiple return paths

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** Nesting depth 4 with 3 return statements. Function is actively used (called from `download_hls_with_resume` at line 130). Valid refactoring target.

| Field | Value |
|-------|-------|
| **ID** | STR-009 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** The `_download_segment` function (lines 188-205) has cyclomatic complexity of 3 (rank A) but nesting depth of 4. It has 3 return statements and combines HTTP fetching with file writing in a single function, making testing harder.

**Evidence:**
```
src/vkdownloader/services/downloader.py:188-205
async def _download_segment(
    session: aiohttp.ClientSession,
    segment_url: str,
    output_path: Path,
    headers: dict,
) -> bool:

Nesting analysis:
- Line 195: try [level 1]
- Line 196: async with session.get(...) [level 2]
- Line 197: if response.status == 200 [level 3]
- Line 198: with open(output_path, "wb") [level 4]

Function spans lines 188-205: 18 lines (excluding docstring)
Return statements: 3 (lines 200, 202, 205)
```

**Recommendation:** Extract `_save_segment_content(response: aiohttp.ClientResponse, output_path: Path) -> bool` for the success path and leave error handling inline. Rewrite:
```python
async def _download_segment(...):
    async with session.get(segment_url, headers=headers) as response:
        if response.status == 200:
            return await self._save_segment_content(response, output_path)
        return False

async def _save_segment_content(...):
    data = await response.read()
    with open(output_path, "wb") as f:
        f.write(data)
    return True
```
This reduces nesting depth from 4 to 2 and improves testability. Effort: small. Priority: recommended.

---

### STR-010: Import statement inside function body in `_parse_m3u8_playlist`

> **Validation Note:**
> - **Action:** REJECTED
> - **Rejection Reason:** `_parse_m3u8_playlist` is confirmed dead code (SRV-001, Phase 03). Refactoring dead code is wasteful. The function should be removed entirely, making this recommendation obsolete.

| Field | Value |
|-------|-------|
| **ID** | STR-010 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** The `_parse_m3u8_playlist` function imports `urljoin` at line 236 inside the function body rather than at module level. This is a code smell that reduces readability and can cause subtle performance issues.

**Evidence:**
```
src/vkdownloader/services/extractor.py:236
from urllib.parse import urljoin
```

**Recommendation:** Move the import to the module-level imports at the top of the file.

---

### STR-011: Unused import `typing.Any` and unused variable `domain` in extractor.py

> **Validation Note:**
> - **Action:** Validated (with note)
> - **Detail:** Both issues are confirmed by ruff. However, `typing.Any` is not actually used per ruff check, and `domain` at line 192 is unused. These overlap with SRV-004 and SRV-005 (Phase 03) which were merged into CFG-004 (Phase 02). Keeping this finding as it represents genuine code quality issues, but noting cross-phase duplication.

| Field | Value |
|-------|-------|
| **ID** | STR-011 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** The `_format_cookies_for_ffmpeg` method assigns `domain` variable (line 192) that is never used. This is dead code that adds unnecessary cognitive load. Additionally, `typing.Any` is imported but not used in the module.

**Evidence:**
```
ruff output:
F401 [*] `typing.Any` imported but unused
F841 [*] Local variable `domain` is assigned to but never used

src/vkdownloader/services/extractor.py:5:5
from typing import Any

src/vkdownloader/services/extractor.py:192:13
domain = cookie.get("domain", "")  # assigned but never used
```

**Recommendation:** Remove the unused `domain` variable and the unused `Any` import.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 7 | STR-001, STR-003, STR-004, STR-005, STR-006, STR-007, STR-009 |
| Reclassified | 0 | — |
| Merged | 1 | STR-008 → STR-004 |
| Rejected | 2 | STR-002, STR-010 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| STR-002 | Function `_parse_m3u8_playlist` has excessive nesting depth | The `_parse_m3u8_playlist` function is confirmed dead code (SRV-001, Phase 03). Refactoring dead code is wasteful; it should be removed entirely. |
| STR-010 | Import statement inside function body in `_parse_m3u8_playlist` | The function `_parse_m3u8_playlist` is dead code. Recommending refactoring of dead code is inappropriate. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|-----------|
| STR-008 | STR-004 | Both findings describe the same function `_fetch_playlist_with_retry` with overlapping evidence about nesting depth and parameter count. |

---

## Warnings

- **Dead Code Risk:** `_parse_m3u8_playlist` method exists but is never called. It should be removed to avoid confusion (SRV-001, Phase 03).
- **Dead Code Risk:** STR-002 and STR-010 recommendations about `_parse_m3u8_playlist` refactoring are rejected because the function is dead code.
- **Cross-Phase Duplication:** STR-004/STR-008 and STR-011 duplicate issues found in Phase 03 (SRV-004, SRV-005) and Phase 02 (CFG-004). These are genuine issues but span phases.

---

## Advisory Recommendations

The following modularization opportunities have high ROI per project rule #15 (small modules and functions):

1. **STR-001**: Extract `_merge_batch_segments(batch_files: list[Path], temp_dir: Path) -> list[Path]` for batch merging logic, `_perform_final_merge(temp_files: list[Path], output_file: Path) -> bool` for final merge, and `_build_ffmpeg_concat_command(input_files: list[Path]) -> list[str]` for command building.

2. **STR-003**: Create `HLSDownloadRequest` dataclass with fields: `url: str, output_file: Path, quality: str, cookies: str | None, settings: Settings, extractor: VKVideoExtractor | None`. Modify signature to `download_hls_with_resume(request: HLSDownloadRequest) -> Path | None`.

3. **STR-004**: Create `PlaylistRequest` dataclass with session, m3u8_url, headers, extractor, settings. Add `get_max_retries() -> int` method to Settings. Note: video_url must be added for proper token refresh (see DF-012).

4. **STR-005**: Extract `_find_quality_match(streams, quality_str)` and `_get_fallback_stream(streams)` helper methods to reduce nesting.

5. **STR-006**: Extract `_write_chunk_to_file(chunk: bytes, file_handle) -> int` and `_update_progress(downloaded: int, total: int, callback) -> None` helpers to reduce nesting depth from 6 to 2.

6. **STR-007**: Refactor `_extract_urls_from_json` using early returns. Extract `_process_value(value)` helper.

7. **STR-009**: Extract `_save_segment_content(response, output_path) -> bool` for success path. Note: This function needs video_url parameter for proper token refresh (see DF-012).