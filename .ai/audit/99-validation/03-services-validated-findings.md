---
name: 03-services
description: Phase 03 Audit Findings — Service Layer & Business Logic (Validated)
agent: validator
alwaysApply: false
---

# Phase 03 Audit Findings — Service Layer & Business Logic (Validated)

**Executor:** validator  
**Source:** `.ai/audit/03-services/findings.md`  
**Base:** Phase 03 Audit  
**Status:** complete  
**Validated:** yes

---

## Findings

### SRV-001: Dead code - `_parse_m3u8_playlist` method never called

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** The `_parse_m3u8_playlist` method (lines 218-281) is defined but never called. The implementation plan (02-implementation-details.md:278) and task file (TASK_025) reference it, but the actual implementation in `extract_streams` and `_extract_with_browser` uses NetworkMonitor.m3u8_urls instead. No documentation references this specific method. This is confirmed dead code.

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | LOW |
| **Type** | DEAD-CODE |
| **Affected Modules** | src/vkdownloader/services/extractor.py |
| **Classification** | advisory |

**Description:** The `_parse_m3u8_playlist` method is defined in `VKVideoExtractor` class (lines 218-281) but is never called anywhere in the codebase. It was planned for parsing m3u8 playlists to extract quality variants, but the current implementation uses NetworkMonitor to capture m3u8 URLs.

**Evidence:**
- mypy confirms the method exists: `src\vkdownloader\services\extractor.py:218`
- grep search returns only the definition and references in plan/task files
- Current implementation uses `NetworkMonitor.m3u8_urls` (line 174) instead of `_parse_m3u8_playlist`
- No service code invokes this method

**Recommendation:** Remove the unused method. Effort: trivial.

---

### SRV-002: Dead code - `AdaptiveThrottle` class exported but never used

> **Validation Note:**
> - **Action:** Reclassified
> - **Original Type:** DEAD-CODE
> - **New Type:** SPEC-DEVIATION
> - **Detail:** The `AdaptiveThrottle` class is documented in `vkdownloader-overview.md` and planned in 05-recommendations-and-improvements.md (Phase 3), but is never imported or used in any service code. Per validation rules: "If the spec, models, or config reference the component → reject the 'dead code' label and reclassify as SPEC-DEVIATION (missing integration, not dead code)." This represents incomplete integration of a planned feature.

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/infrastructure/adaptive_throttle.py |
| **Classification** | advisory |

**Description:** The `AdaptiveThrottle` class is defined and exported from `infrastructure/__init__.py` but is never imported or used anywhere in the service layer or application code. It is documented in `vkdownloader-overview.md` and planned for Phase 3 according to `05-recommendations-and-improvements.md`, indicating incomplete integration of a planned feature.

**Evidence:**
- Definition: `src\vkdownloader\infrastructure\adaptive_throttle.py:11`
- Export list: `src\vkdownloader\infrastructure\__init__.py:3,9`
- Documentation reference: `docs\01-tools\vkdownloader-overview.md:34`
- No usages found outside the module definition
- Planning document indicates this for Phase 3 Rate limiting

**Recommendation:** Either integrate this rate limiter if planned features are to be implemented, or remove it from code and documentation to maintain consistency. Effort: variable. Priority: context-dependent.

---

### SRV-003: Cookie type incompatibility in `_format_cookies_for_ffmpeg`

> **Validation Note:**
> - **Action:** Merged into CFG-004 (Phase 02)
> - **Detail:** This finding duplicates CFG-004 in Phase 02, which covers the same type annotation issues across downloader.py, browser.py, and extractor.py. See CFG-004 for full analysis and merge details.

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | MEDIUM |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/extractor.py:186 |
| **Classification** | mandatory |

**Description:** The `_format_cookies_for_ffmpeg` method signature accepts `list[dict]` but receives `list[Cookie]` from Playwright's `page.context.cookies()` API. This type mismatch causes actual mypy errors.

**Evidence:**
- mypy error: `src\vkdownloader\services\extractor.py:168: error: Argument 1 to "_format_cookies_for_ffmpeg" has incompatible type "list[Cookie]"; expected "list[dict[Any, Any]]"  [arg-type]`

**Merged Into:** See CFG-004 (Phase 02) - covers all type annotation issues in service layer.

---

### SRV-004: Unused import `typing.Any` in extractor.py

> **Validation Note:**
> - **Action:** Merged into CFG-004 (Phase 02)
> - **Detail:** This finding duplicates CFG-004 in Phase 02 and CLI-006 in Phase 01. All cover the same code quality issues in extractor.py.

| Field | Value |
|-------|-------|
| **ID** | SRV-004 |
| **Severity** | LOW |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/extractor.py:5 |
| **Classification** | advisory |

**Description:** The `typing.Any` import is unused in extractor.py.

**Evidence:**
- ruff error: `F401 [*] 'typing.Any' imported but unused` at line 5

**Merged Into:** See CFG-004 (Phase 02) and CLI-006.

---

### SRV-005: Unused variable `domain` in `_format_cookies_for_ffmpeg`

> **Validation Note:**
> - **Action:** Merged into CFG-004 (Phase 02)
> - **Detail:** This finding duplicates CFG-004 in Phase 02 and CLI-006 in Phase 01. All cover the same code quality issues in extractor.py.

| Field | Value |
|-------|-------|
| **ID** | SRV-005 |
| **Severity** | LOW |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/extractor.py:192 |
| **Classification** | advisory |

**Description:** Variable `domain` is extracted from cookies but never used.

**Evidence:**
- ruff error: `F841 Local variable 'domain' is assigned to but never used` at line 192

**Merged Into:** See CFG-004 (Phase 02) and CLI-006.

---

### SRV-006: Missing type annotation for `extractor` parameter in `download_hls_with_resume`

> **Validation Note:**
> - **Action:** Merged into CFG-004 (Phase 02)
> - **Detail:** This finding duplicates CFG-004 in Phase 02, which appropriately consolidates all type annotation issues across downloader.py, browser.py, and extractor.py.

| Field | Value |
|-------|-------|
| **ID** | SRV-006 |
| **Severity** | MEDIUM |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/downloader.py:71 |
| **Classification** | advisory |

**Description:** The `download_hls_with_resume` function accepts an `extractor` parameter without type annotation.

**Evidence:**
- mypy error: `Function is missing a type annotation for one or more parameters` at line 71

**Merged Into:** See CFG-004 (Phase 02).

---

### SRV-007: Missing type arguments for generic `dict` in downloader functions

> **Validation Note:**
> - **Action:** Merged into CFG-004 (Phase 02)
> - **Detail:** This finding duplicates CFG-004 in Phase 02, which appropriately consolidates all type annotation issues.

| Field | Value |
|-------|-------|
| **ID** | SRV-007 |
| **Severity** | MEDIUM |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/downloader.py:151,192 |
| **Classification** | advisory |

**Description:** Two functions use bare `dict` type instead of parameterized generic `dict[K, V]`.

**Evidence:**
- mypy error: `Missing type arguments for generic type "dict"` at lines 148-151 and 192

**Merged Into:** See CFG-004 (Phase 02).

---

### SRV-008: Returning `Any` from `_load_downloaded_count` function

> **Validation Note:**
> - **Action:** Merged into CFG-004 (Phase 02)
> - **Detail:** This finding duplicates CFG-004 in Phase 02, which covers all type annotation issues in downloader.py.

| Field | Value |
|-------|-------|
| **ID** | SRV-008 |
| **Severity** | LOW |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/services/downloader.py:301 |
| **Classification** | advisory |

**Description:** The `_load_downloaded_count` function returns `Any` from `json.load()` without explicit type conversion.

**Evidence:**
- mypy error: `Returning Any from function declared to return "int"` at line 301

**Merged Into:** See CFG-004 (Phase 02).

---

### SRV-009: `create_stealth_context` return type mismatch

> **Validation Note:**
> - **Action:** Merged into CFG-005 (Phase 02)
> - **Detail:** This finding duplicates CFG-005 in Phase 02, which covers the same `create_stealth_context` async return type issue. Both CFG-004 and CLI-005 also reference this same issue.

| Field | Value |
|-------|-------|
| **ID** | SRV-009 |
| **Severity** | HIGH |
| **Type** | MERGED |
| **Affected Modules** | src/vkdownloader/infrastructure/browser.py:13 |
| **Classification** | mandatory |

**Description:** The `create_stealth_context` function is missing `async` but calls `launch_persistent_context` which returns a coroutine in Playwright's async API.

**Evidence:**
- mypy error: `Incompatible return value type (got "Coroutine[Any, Any, BrowserContext]", expected "BrowserContext")` at line 29
- Function is defined as `def create_stealth_context(...)` but calls async Playwright method

**Merged Into:** See CFG-005 (Phase 02).

---

### SRV-010: Missing newlines at end of service files

> **Validation Note:**
> - **Action:** Validated
> - **Detail:** ruff format check confirms all three service files are missing trailing newlines. This is a consistent formatting issue across the service layer.

| Field | Value |
|-------|-------|
| **ID** | SRV-010 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/downloader.py, src/vkdownloader/services/extractor.py, src/vkdownloader/services/quality.py |
| **Classification** | advisory |

**Description:** All three service files are missing trailing newlines, violating consistent file formatting standards.

**Evidence:**
- ruff error: `W292 [*] No newline at end of file` in all three service files

**Recommendation:** Add trailing newlines to maintain consistent file formatting. Effort: trivial.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 2 | SRV-001, SRV-010 |
| Reclassified | 1 | SRV-002 (DEAD-CODE → SPEC-DEVIATION) |
| Merged | 7 | SRV-003 → CFG-004, SRV-004 → CFG-004, SRV-005 → CFG-004, SRV-006 → CFG-004, SRV-007 → CFG-004, SRV-008 → CFG-004, SRV-009 → CFG-005 |
| Rejected | 0 | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SRV-002 | DEAD-CODE | SPEC-DEVIATION | The component is documented and planned per 05-recommendations-and-improvements.md. Per validation rules: "If the spec, models, or config reference the component → reject the 'dead code' label and reclassify as SPEC-DEVIATION (missing integration, not dead code)." |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| SRV-003 | CFG-004 (Phase 02) | Duplicate type annotation issue for _format_cookies_for_ffmpeg |
| SRV-004 | CFG-004 (Phase 02) | Duplicate unused import issue |
| SRV-005 | CFG-004 (Phase 02) | Duplicate unused variable issue |
| SRV-006 | CFG-004 (Phase 02) | Duplicate missing type annotation for extractor parameter |
| SRV-007 | CFG-004 (Phase 02) | Duplicate missing type arguments for generic dict |
| SRV-008 | CFG-004 (Phase 02) | Duplicate returning Any from function |
| SRV-009 | CFG-005 (Phase 02) | Duplicate create_stealth_context async return type issue (also referenced in CLI-005) |

### Cross-Phase Conflicts

None detected. All findings are consistent with Phase 01 (CLI-005, CLI-006) and Phase 02 (CFG-004, CFG-005) findings. The type annotation issues and create_stealth_context issues span multiple phases, which is expected since they represent cross-cutting concerns.

---

## Warnings

- **Type Safety Risk:** mypy strict mode failures indicate the codebase lacks type annotations required by project rule #9. These issues are consolidated in CFG-004 (Phase 02).
- **Documentation Drift:** The `_parse_m3u8_playlist` method exists in code but is replaced by NetworkMonitor approach in the actual implementation. The method should be removed to avoid confusion.
- **Incomplete Integration Risk:** `AdaptiveThrottle` is documented and planned but never integrated. This creates inconsistency between documentation and actual behavior.

---

## Required Fixes (from Validated Findings)

**SRV-001:** Remove unused `_parse_m3u8_playlist` method from extractor.py - obsolete, superseded by yt-dlp and `_parse_m3u8_segments`

**SRV-002:** Either integrate `AdaptiveThrottle` or remove from code and documentation

**SRV-010:** Add trailing newlines to all three service files

---

## Research Addendum: `_parse_m3u8_playlist` and Resume Download Functionality (2026-07-09)

### Research Context

Investigation conducted on the `_parse_m3u8_playlist` dead code finding (SRV-001) and the `download_hls_with_resume` function implementation, focusing on requirements for bypassing bot protection, downloading large files, and supporting download resumption.

### Key Findings

#### 1. `_parse_m3u8_playlist` - Dead Code Assessment

| Aspect | Finding | Confidence |
|--------|---------|------------|
| **Current Status** | Never called - confirmed dead code | HIGH |
| **Replaced By** | NetworkMonitor.m3u8_urls for m3u8 capture | HIGH |
| **Functionality Gap** | Extracts quality variants from m3u8 playlist content | HIGH |
| **Current Implementation** | Uses yt-dlp for stream extraction (provides quality info) | HIGH |

**Analysis:**
- The method was designed to parse m3u8 playlists to extract individual quality variants (lines 218-281 in extractor.py)
- The actual implementation uses `NetworkMonitor.m3u8_urls` to capture URLs directly from browser network traffic
- For quality selection, the codebase uses yt-dlp's native format extraction which already provides quality metadata
- The `_parse_m3u8_segments` function in downloader.py (line 177) exists for segment extraction but serves a different purpose (download resumption)

**Conclusion:** `REMOVE` - the method is obsolete. yt-dlp handles m3u8 parsing for quality extraction, and `_parse_m3u8_segments` handles segment-level parsing for resume functionality.

#### 2. Resume Download Functionality Assessment (`download_hls_with_resume`)

| Aspect | Finding | Confidence |
|--------|---------|------------|
| **CRITICAL Bug** | DF-012: m3u8 URL passed to extractor expecting video URL | HIGH |
| **DF-010 Risk** | Partial segments not cleaned up on failure | HIGH |
| **Missing Parameter** | No `video_url` parameter for token refresh | HIGH |
| **Type Safety** | Multiple mypy violations in function | MEDIUM |

**Architecture Gap Analysis:**

The current flow has a critical design flaw:

```
download_hls_with_resume(m3u8_url, ...) 
    → _fetch_playlist_with_retry(m3u8_url, ...)
        → extractor.extract_streams_with_cookies(m3u8_url)  # ❌ WRONG: m3u8 URL passed
```

The `extract_streams_with_cookies` method calls `parse_video_id(url)` which expects `video-(-?\d+)_(\d+)` pattern, but receives m3u8 URLs like `https://vkvdXXX.okcdn.ru/video.m3u8?expires=...`.

**Required Fix:** Add `video_url: str` parameter and pass it through the call chain for proper token refresh on 403/410 responses.

#### 3. Modern HLS Download Strategies (2026 Research)

**Current Implementation Approach:**
- Segment-level downloading with batched ffmpeg merging
- Progress tracking via `.{stem}_progress.json` metadata files
- 403/410 retry with token refresh

**Modern Alternatives (from research):**

1. **yt-dlp Native Features (Recommended Primary):**
   - Built-in `--hls-prefer-native` flag for segment downloads
   - Automatic fragment retries (`--fragment-retries 10`)
   - Built-in resume support via `.part` files
   - PO Token support (2025+) for bot detection bypass
   - Multi-threaded download support

2. **Hybrid Approach (Current Code Direction):**
   - Browser automation (non-headless) for token/cookie capture
   - ffmpeg for direct segment download to MP4
   - Segment-level retry with batched merging

3. **Cloudflare Bypass Techniques (Relevant for CDN):**
   - TLS fingerprint masking (curl-cffi, Camoufox)
   - Browser automation with stealth scripts (currently implemented)
   - Proxy rotation for large-scale downloads

#### 4. Security Considerations

| Risk | Assessment | Source |
|------|------------|--------|
| Token expiration during long downloads | HIGH | VK tokens expire in 1-2 hours |
| Non-headless browser requirement | MEDIUM | User interaction required, but bypasses bot detection |
| CDN segment authentication | HIGH | Cookies required for segment access |

#### 5. Recommendation

1. **For SRV-001 (`_parse_m3u8_playlist`):** Remove entirely. The functionality is superseded by:
   - yt-dlp's native m3u8 parsing for quality extraction
   - `_parse_m3u8_segments` in downloader.py for resume logic

2. **For Resume Functionality (DF-012):** Fix the architectural gap:
   - Add `video_url: str` parameter to `download_hls_with_resume`
   - Pass `video_url` to `_fetch_playlist_with_retry`
   - Pass `video_url` to `extractor.extract_streams_with_cookies` for proper token refresh

3. **Consider Simplification:**
   - The current segment-based resume could be replaced by yt-dlp's native features
   - yt-dlp handles token refresh, retry logic, and resume more robustly
   - Would reduce code complexity while improving reliability

### Evidence Summary

- `extractor.py:218-281`: Dead `_parse_m3u8_playlist` method
- `extractor.py:76-79`: Primary extraction uses yt-dlp
- `extractor.py:152-184`: Browser extraction uses NetworkMonitor, not `_parse_m3u8_playlist`
- `downloader.py:166`: DF-012 bug - m3u8 URL passed incorrectly for refresh
- `downloader.py:177`: `_parse_m3u8_segments` - parallel functionality, actively used
- `main.py:78-80, 148-149`: `download_hls_with_resume` called with correct URL in some paths, demonstrating the parameter naming confusion

