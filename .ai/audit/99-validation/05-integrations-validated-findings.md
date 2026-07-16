# Phase 05 Audit Findings — External Integrations (Validated)

**Executor:** audit-executor
**Validator:** validator
**Template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** yes

---

## Scope Note — Task/Reality Mismatch

The phase task file (`05-audit-integrations.md`) references integrations such as Telegram, Google Sheets, Telethon, and `telepost`. None of these exist in this codebase. This is a VK video downloader whose real external integrations are:

- **yt-dlp** (`yt_dlp.YoutubeDL`) — stream extraction + primary download (blocking, run in thread pool)
- **ffmpeg** — invoked as subprocess via `asyncio.create_subprocess_exec` for HLS→MP4 and segment merge
- **Playwright (Chromium)** — `BrowserManager` + `NetworkMonitor` for cookie capture and m3u8 discovery
- **aiohttp** — `ClientSession` for direct HLS segment and playlist fetching
- **URLBackoffCoordinator** — shared rate-limit backoff across segments (in-process)
- **signal handlers** — `SIGINT`/`SIGTERM` → graceful shutdown event

The phantom references in the task file are treated as template boilerplate, not spec deviations.

---

## Runtime Verification (completed)

| Step | Command | Result |
|------|---------|--------|
| R1 — Import | `uv run python -c "import ..."` | `IMPORTS_OK` |
| R2 — Linter | `uv run ruff check src/vkdownloader/infrastructure src/vkdownloader/services src/vkdownloader/utils` | `All checks passed!` |
| R3 — Types | `uv run mypy src/vkdownloader/infrastructure src/vkdownloader/services` | `Success: no issues found` |
| R4 — Tests | `uv run pytest tests/test_browser_infrastructure.py tests/test_ffmpeg_utils.py tests/test_extractor.py tests/test_hls_downloader.py tests/test_downloader_throttle.py` | `154 passed` |

---

## Findings

### INT-001: `download_timeout` config is never applied to any HTTP request (no request timeout)

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` (L41-46), `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | mandatory (correctness/reliability) |

**Description:** `Settings.download_timeout` (default 300s, range 30–3600, documented in `docs/11-guides/configuration.md`) is a real, validated config field, but it is **never read** by any aiohttp call. Every `session.get(...)` in `segment_downloader.py` and `downloader_throttle.py` is made **without a `ClientTimeout` / `timeout=` argument**. A slow/hung CDN socket will block a segment indefinitely; the only way out is the user pressing Ctrl+C. This also leaks into batch mode, where one hung URL can stall the shared semaphore.

**Evidence:**
- `config.py:41-46` — `download_timeout` field defined
- `segment_downloader.py:112` — `async with session.get(segment_url, headers=headers)` (no timeout)
- `downloader_throttle.py:184` — `async with session.get(segment_url, headers=headers)` (no timeout)
- Grep for `ClientTimeout` returns zero matches

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via grep and code inspection. No `ClientTimeout` or `timeout=` argument exists on any aiohttp request in the codebase. The documented setting is inert, creating a reliability risk for hung connections.
> - **See also:** —

---

### INT-002: `accept_language` config field is defined and documented but never consumed

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (L23-26), `src/vkdownloader/infrastructure/browser.py` (`create_stealth_page`) |
| **Classification** | advisory |

**Description:** `Settings.accept_language` has a default and documented env var (`VKDOWNLOADER_ACCEPT_LANGUAGE`) in `docs/11-guides/configuration.md`, but it is **never passed** to the Playwright browser context. `BrowserManager.create_stealth_page` only sets `user_agent`, `locale`, and `timezone_id` (browser.py:64-69).

**Evidence:**
- `config.py:23-26` — field defined
- `browser.py:64-69` — `new_context(user_agent=..., locale=..., timezone_id=...)`; no `accept_language` key
- Grep for `accept_language` finds only the config definition

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The Playwright `new_context()` call at browser.py:64 does not include `accept_language`. The `_extract_with_browser` path does not apply it. This is a code-vs-documentation inconsistency.
> - **See also:** The same finding was validated in the config phase

---

### INT-003: Rate-limit backoff pause marks the next segment attempt as a failure instead of waiting

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | HIGH |
| **Type** | ~~BEST-PRACTICE~~ [REJECTED] |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` (`wait_if_paused` L56-69), `src/vkdownloader/services/segment_downloader.py` (`_check_backoff_before_attempt` L137-147) |
| **Classification** | advisory |

**Description:** The finding claims `wait_if_paused` returns `True` for both shutdown and normal backoff completion, and that this causes segment downloads to fail after rate-limiting. However, code inspection reveals the caller `_check_backoff_before_attempt` correctly checks `shutdown_event.is_set()` before aborting.

**Actual Code Flow:**
```python
# downloader_throttle.py:56-69
async def wait_if_paused(...): -> bool
    if time.time() >= timestamp:
        return False  # Was NOT paused (backoff already expired)
    # ... wait for backoff ...
    except TimeoutError:
        return True  # Backoff completed normally

# segment_downloader.py:143-147
async def _check_backoff_before_attempt(...): -> bool
    if backoff_coordinator and video_url:
        was_paused = await backoff_coordinator.wait_if_paused(video_url)
        if was_paused and shutdown_event.is_set():  # BOTH conditions required
            return True  # abort
    return False  # continue
```

After normal backoff completion: `wait_if_paused` returns `True`, but `shutdown_event.is_set()` is `False`, so `_check_backoff_before_attempt` returns `False` (don't abort). The download continues.

**Evidence:**
- `downloader_throttle.py:56-69` — returns `True` on both shutdown and normal timeout (as documented)
- `segment_downloader.py:143-147` — only aborts when BOTH `was_paused AND shutdown_event.is_set()`

> **Rejection reason:** The finding misrepresents the code's actual behavior. The `_check_backoff_before_attempt` function correctly distinguishes between "backoff completed normally" (continue) and "shutdown triggered" (abort) by checking `shutdown_event.is_set()`. This is a valid design pattern where `wait_if_paused` returns `True` to indicate "we had to wait" and the caller decides whether to abort based on shutdown state. No correctness bug exists.

---

### INT-004: Playwright always launches `headless=False` — hard failure on servers/CI/Docker

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` (L34-37) |
| **Classification** | advisory |

**Description:** `BrowserManager.__aenter__` hardcodes `headless=False` (browser.py:35). No config toggle exists, so browser-based downloads cannot run anywhere without a display.

**Evidence:**
- `browser.py:34-37` — `await playwright_instance.chromium.launch(headless=False, args=[...])`
- `config.py` — no `headless` setting exists

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. Playwright launch is hardcoded with `headless=False`. The documented workaround in `vkdownloader-limitations.md` line 45 acknowledges this but does not explicitly warn about server/CI incompatibility. The recommendation for a configurable `headless` setting is valid.
> - **See also:** DOCS-006 (related doc update flagged)

---

### INT-005: Network monitor silently swallows all JSON-parse errors (`except Exception: pass`)

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` (L62-70) |
| **Classification** | advisory |

**Description:** In `_intercept_response`, when VK returns a JSON XHR, the monitor calls `await response.json()` inside a `try/except Exception: pass` block. This masks programming errors and makes it impossible to distinguish malformed responses from code defects.

**Evidence:**
- `network_monitor.py:66-70` — `except Exception: pass` around `response.json()` and recursive extraction

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The broad `except Exception: pass` at lines 66-70 catches all exceptions. The recommendation to narrow to specific exceptions and add logging is valid.
> - **See also:** —

---

### INT-006: `CookieSource.FILE` is documented-but-unimplemented; `_should_abort_retry` is dead code

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` (L123-127), `src/vkdownloader/services/segment_downloader.py` (`_should_abort_retry` L128-135) |
| **Classification** | advisory |

**Description:** Two items: (1) `CookieSource.FILE` raises `NotImplementedError` but remains a live CLI option; (2) `_should_abort_retry` is never called.

**Evidence:**
- `extractor.py:123-127` — `raise NotImplementedError(...)` for `CookieSource.FILE`
- `segment_downloader.py:128-135` — `_should_abort_retry` defined, zero call sites

> **Validation Note:**
> - **Action:** merged
> - **Detail:** `_should_abort_retry` is a duplicate of SRV-004 (services layer validated report). It is the same dead code issue. CookieSource.FILE aspect remains as a distinct finding.
> - **See also:** SRV-004 (duplicate dead code finding)

---

### INT-007: Cookie→ffmpeg header formatting truncates to 20 cookies and hardcodes CDN domain in Netscape path

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` (`_format_cookies_for_ffmpeg` L234-245), `src/vkdownloader/services/cookies.py` (`_cookies_to_netscape` L6-20) |
| **Classification** | advisory |

**Description:** (1) `_format_cookies_for_ffmpeg` joins only the first 20 cookies into ffmpeg headers. (2) `_cookies_to_netscape` hardcodes `.vkvideo.ru` for all cookies.

**Evidence:**
- `extractor.py:245` — `return "; ".join(cookie_parts[:20])`
- `cookies.py:19` — `lines.append(f".vkvideo.ru\tTRUE\t/\tFALSE\t0\t{name}\t{value}")`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The 20-cookie cap is unconditional. No warning is logged when cookies are dropped. The Netscape format hardcodes domain. Both issues are real correctness concerns.
> - **See also:** —

---

### INT-008: ffmpeg subprocess success depends on returncode only; no output file verification

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`download_with_ffmpeg` L171-253) |
| **Classification** | advisory |

**Description:** `download_with_ffmpeg` returns `output_file` whenever `returncode == 0`, even if ffmpeg wrote zero bytes. No check that `output_file` actually grew.

**Evidence:**
- `downloader.py:243-251` — success path returns `output_file` based solely on `returncode == 0`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The success path checks only `returncode == 0` before returning the output file path. No file size validation occurs. The recommendation is valid.
> - **See also:** —

---

### INT-009: yt-dlp runs in a thread pool with no cancellation of the underlying native download

| Field | Value |
|-------|-------|
| **ID** | INT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp` L434-500) |
| **Classification** | advisory |

**Description:** yt-dlp runs inside `run_in_executor`. On `CancelledError`, only `download_task.cancel()` is called; the blocking thread continues. The comment at downloader.py:493-494 acknowledges this.

**Evidence:**
- `downloader.py:486-497` — `download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))`; on cancel only `download_task.cancel()` is called

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Confirmed via code inspection. The comment explicitly acknowledges the thread will continue. This is a known limitation. The recommendation is valid.
> - **See also:** SRV-006 (related finding in services layer)

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 4 |
| LOW | 3 |

*(Note: INT-003 rejected; INT-006 merged with SRV-004)*

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 7 | INT-001, INT-002, INT-004, INT-005, INT-007, INT-008, INT-009 |
| Reclassified | 0 | — |
| Merged | 1 | INT-006 (_should_abort_retry) → SRV-004 |
| Rejected | 1 | INT-003 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| INT-003 | Rate-limit backoff pause marks segment as failure | The finding misrepresents the code's actual behavior. `_check_backoff_before_attempt` correctly checks `shutdown_event.is_set()` before aborting, allowing downloads to continue after normal backoff completion. No correctness bug exists. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| INT-006 (_should_abort_retry component) | SRV-004 (Phase 03) | Same dead code function `_should_abort_retry` at segment_downloader.py:128. SRV-004 already validates this issue. The CookieSource.FILE aspect is retained as distinct. |

---

## Rollout Safety Analysis

No rollout safety issues detected. These findings are isolated to integration boundaries and can be addressed independently:

1. **INT-001** and **INT-008** are both HTTP/ffmpeg reliability improvements — can be applied independently
2. **CookieSource.FILE (INT-006)** involves CLI option handling
3. **INT-004** adds a new config option with safe default `False`
4. **INT-005** is exception handling refinement - low risk
5. **INT-007** is cookie formatting correctness - low risk
6. **INT-009** is operational improvement - can be documented if code change is complex

No circular dependencies or hidden dependency chains identified between these findings.