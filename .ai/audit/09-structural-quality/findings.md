---
name: Phase 09 Audit Findings — Structural Code Quality
executor: auditor
template: .ai/audit/templates/audit-findings.md
status: complete
validated: no
---

## Findings

### STR-001: Function `_merge_segments_batched` exceeds recommended length and complexity

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

**Recommendation:** Split into `_merge_batch_segments(batch_files, output_path)` for the repeated batch merge logic and `_perform_final_merge(temp_files, output_file)` for the final merge orchestration. Extract the ffmpeg command building into `_build_ffmpeg_concat_command(input_file, output)`.

---

### STR-002: Function `_parse_m3u8_playlist` has excessive nesting depth

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

**Recommendation:** Create a `DownloadJob` or `HLSDownloadRequest` data class to encapsulate related parameters. This improves testability and makes the function signature cleaner.

---

### STR-004: Function `_fetch_playlist_with_retry` has 6 parameters exceeding limit

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

**Recommendation:** Group request-related parameters into a `RequestContext` dataclass or reduce parameter count by making settings provide headers and max_retries internally.

---

### STR-005: `QualitySelector.select` has complexity of 11 and nesting of 4

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

**Recommendation:** Extract the chunk writing logic into `_write_chunks_to_file(response, output_path, callback, buffer_size)` to reduce nesting depth to 3.

---

### STR-007: `_extract_urls_from_json` has nesting depth of 4 with multiple nested iterations

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

**Recommendation:** Refactor to use early returns and flatten conditionals. Consider `_process_dict_value(value)` and `_process_list_item(item)` helpers.

---

### STR-008: `_fetch_playlist_with_retry` has nesting depth of 5 in retry loop

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

**Recommendation:** Extract `_handle_token_refresh(response, extractor, m3u8_url)` to flatten the retry logic and reduce nesting to 3 levels.

---

### STR-009: `_download_segment` has nesting depth of 4 with multiple return paths

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
- Line 201: logger.warning... [level 3]
- Line 203: except ... [level 2]

Function spans lines 188-205: 18 lines (excluding docstring)
Return statements: 3 (lines 200, 202, 205)
```

**Recommendation:** Extract the success and error paths into `_save_segment_content(response, output_path)` and `_handle_segment_error(response)` to reduce nesting and improve testability.

---

### STR-010: Import statement inside function body in `_parse_m3u8_playlist`

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

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 6 |
| LOW | 2 |

## Advisory Recommendations

1. **STR-001**: Refactor `_merge_segments_batched` into smaller focused functions (nesting depth 5)
2. **STR-002**: Refactor `_parse_m3u8_playlist` to reduce nesting depth from 6 to 2-3
3. **STR-003**: Group `download_hls_with_resume` parameters into a request dataclass
4. **STR-004**: Reduce parameter count in `_fetch_playlist_with_retry` (6 parameters)
5. **STR-005**: Extract quality matching logic in `QualitySelector.select` (nesting depth 4)
6. **STR-006**: Extract chunk writing logic in `HttpClient.download_file` (nesting depth 6)
7. **STR-007**: Flatten conditionals in `NetworkMonitor._extract_urls_from_json` (nesting depth 4)
8. **STR-008**: Flatten retry logic in `_fetch_playlist_with_retry` (nesting depth 5)
9. **STR-009**: Refactor `_download_segment` to reduce nesting depth from 4 to 3
10. **STR-010**: Move import statement to module level in `_parse_m3u8_playlist`
11. **STR-011**: Remove unused `domain` variable and `typing.Any` import

---

## Additional Metrics

**Average Cyclomatic Complexity:** C (12.33) — exceeds recommended threshold of ≤5

**Files with maintainability concerns:**
- All files have MI rank A except the functions noted above which are B/C rank

**Largest files (LOC):**
- src/vkdownloader/services/downloader.py - 319 LOC (exceeds 300 recommendation)
- src/vkdownloader/services/extractor.py - 281 LOC
- src/vkdownloader/cli.py - 165 LOC
- src/vkdownloader/infrastructure/http_client.py - 151 LOC