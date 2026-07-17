# Phase 05 Validated Audit Findings — External Integrations

**Validator:** validator
**Source:** .ai/audit/05-integrations/findings.md
**Status:** complete
**Validated:** yes

---

## Runtime Verification Evidence

- **R1 — Import check:** Confirmed imports work (`sqlite3`, `ffmpeg`, etc.)
- **R2 — Ruff:** No lint errors in integration modules
- **R3 — Mypy:** No type issues found in integration modules
- **R4 — Tests:** 167 tests pass for integration-related code

> Note: Runtime verification shows the integration layer is syntactically and type-safe. The findings below are correctness defects and architectural concerns.

---

## Findings

### INT-001: Orphaned ffmpeg subprocesses — `_active_processes` is tracked but never killed on shutdown

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py:15`, `src/vkdownloader/services/downloader.py:227,302` |
| **Classification** | mandatory (correctness / resource leak) |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type BEST-PRACTICE reclassified to SPEC-DEVIATION. The module-level comment at ffmpeg_utils.py:14 states "Track active ffmpeg processes for cleanup" but no cleanup code iterates this set. The implementation violates its own documented intent.
> - **See also:** —

**Description:** `_active_processes` is a module-global set declared with a comment promising cleanup. However, the signal handler only sets `shutdown_event`, and nothing ever iterates `_active_processes` to call `cancel_ffmpeg_process`. The set serves no purpose beyond per-coroutine tracking.

**Evidence:**
```python
# ffmpeg_utils.py:15
_active_processes: set[asyncio.subprocess.Process] = set()  # "Track ... for cleanup" — never consumed
```

**Recommendation:** Remove the global `_active_processes` set and its misleading comment. The per-coroutine cleanup via `cancel_ffmpeg_process` in `finally` handles the normal path.

---

### INT-002: `accept_language` config field is silently ignored by the browser integration

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py:27`, `src/vkdownloader/infrastructure/browser.py:64-69`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Evidence verified. `Settings.accept_language` is defined and documented as "Accept-Language header for browser requests" but `BrowserManager.create_stealth_page` never reads it. This is a spec deviation between config definition and usage.
> - **See also:** —

**Description:** `Settings.accept_language` is defined and documented, but `BrowserManager.create_stealth_page` builds the Playwright context without using this setting.

**Evidence:**
```python
# browser.py:64-69
context = await self.browser.new_context(
    viewport={"width": 1920, "height": 1080},
    user_agent=self.settings.user_agent,
    locale=self.settings.locale,
    timezone_id=self.settings.timezone,
    # accept_language is NEVER passed here
)
```

**Recommendation:** Either pass `accept_language=self.settings.accept_language` into `new_context()`, or remove the field and its docs. Effort: trivial. Priority: recommended.

---

### INT-003: `download_timeout` config is not propagated to yt-dlp (hardcoded `socket_timeout: 180`)

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py:45`, `src/vkdownloader/services/downloader.py:528`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Evidence verified. `Settings.download_timeout` (default 300s) is documented as global timeout and used by segment path, but yt-dlp path hardcodes `socket_timeout: 180`. This violates the documented behavior.
> - **See also:** —

**Description:** `Settings.download_timeout` is documented as global timeout but the yt-dlp path ignores it with a hardcoded value.

**Evidence:**
```python
# downloader.py:528
"socket_timeout": 180,                 # hardcoded, ignores settings.download_timeout
```

**Recommendation:** Use `settings.download_timeout` for yt-dlp's `socket_timeout` so the documented global timeout applies uniformly. Effort: trivial.

---

### INT-004: ffmpeg stdout pipe is never drained — deadlock risk under large stdout

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:220-224` |
| **Classification** | mandatory (operational reliability) |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type BEST-PRACTICE reclassified to SPEC-DEVIATION. The `-progress pipe:2` flag routes progress to stderr, implying stdout is unused. Setting `stdout=PIPE` contradicts this intent and creates a latent deadlock risk.
> - **See also:** —

**Description:** `download_with_ffmpeg` creates subprocess with `stdout=PIPE` but never reads it. Only stderr is read via `_monitor_progress` or `_drain_stderr`.

**Evidence:**
```python
# downloader.py:220-224
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,   # never read anywhere
    stderr=asyncio.subprocess.PIPE,   # read via monitor/drain only
)
```

**Recommendation:** Set `stdout=asyncio.subprocess.DEVNULL` since ffmpeg progress goes to stderr via `-progress pipe:2`. Effort: trivial.

---

### INT-005: yt-dlp / ffmpeg child processes leak on cancellation (thread executor not interruptible)

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:577-588` |
| **Classification** | mandatory (resource leak / correctness) |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Evidence verified. `_download_with_ytdlp` runs yt-dlp in a thread executor. On `CancelledError`, only the asyncio task is cancelled, not the worker thread. The code explicitly admits "the thread will continue". This is a real resource leak concern.
> - **See also:** —

**Description:** `_download_with_ytdlp` spawns yt-dlp in a thread executor; cancellation doesn't interrupt the underlying process.

**Evidence:**
```python
# downloader.py:577
download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))
...
# downloader.py:582-588
if not download_task.done():
    download_task.cancel()   # cancels the await, NOT the worker thread
```

**Recommendation:** Implement actual yt-dlp interruption via `ydl.interrupt_download()` or process-group killing. Effort: medium. Priority: recommended.

---

### INT-006: Permanent segment failures are indistinguishable and surfaced only as a count mismatch

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py:196-203`, `src/vkdownloader/services/segment_downloader.py:504` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type BEST-PRACTICE reclassified to SPEC-DEVIATION. The code violates the principle that failures should be distinguishable. Both permanent and transient failures return `None` with no way for callers to differentiate.
> - **See also:** —

**Description:** `_retry_429_with_backoff` returns `None` for both non-retryable status codes and retry-exhausted failures, with no distinction.

**Evidence:**
```python
# downloader_throttle.py:196-203
if response.status not in RETRYABLE_STATUS_CODES:
    return None          # same None as retry-exhausted / exception path
```

**Recommendation:** Return a typed result distinguishing permanent vs transient failures. Effort: small. Priority: recommended.

---

### INT-007: Hardcoded magic-number sleeps in browser extraction are fragile

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py:200,202` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Evidence verified. Fixed sleeps of 5s and 8s are used without configuration or event-based alternatives. The values are undocumented, making tuning require code changes. This contradicts operational configurability principles.
> - **See also:** —

**Description:** `_extract_with_browser` uses fixed `await asyncio.sleep(5)` and `await asyncio.sleep(8)` without configuration or condition-based waits.

**Evidence:**
```python
# extractor.py:200,202
await asyncio.sleep(5)
await self._simulate_video_interaction(page)
await asyncio.sleep(8)   # fixed; no config, no event-based wait
```

**Recommendation:** Replace with condition-based waits or expose via `Settings`. Effort: small. Priority: recommended.

---

### INT-008 (cross-reference): Insecure/secure ffmpeg header builders coexist — already raised in Phase 03

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:144-166` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** merged
> - **Detail:** This finding duplicates SRV-002 from Phase 03. The dead `_build_ffmpeg_cmd` method with insecure cookie handling was already assessed. The Phase 03 validator rejected the security framing due to incorrect evidence claim, but the dead-code concern stands.
> - **See also:** SRV-002 (Phase 03)

**Description:** `_build_ffmpeg_cmd` inlines cookies in argv, contradicting the secure temp-file pattern used in production.

**Evidence:**
```python
# downloader.py:148
cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""  # inlined in argv
```

**Recommendation:** Remove `_build_ffmpeg_cmd` or make it use the secure temp-file mechanism. Effort: small.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 5 | INT-002, INT-003, INT-005, INT-007 |
| Reclassified | 3 | INT-001, INT-004, INT-006 |
| Merged | 1 | INT-008 → SRV-002 (Phase 03) |
| Rejected | 0 | — |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| INT-008 | SRV-002 (Phase 03) | Same root cause: dead `_build_ffmpeg_cmd` method exists next to the secure `_temp_headers_file` pattern. Already assessed in Phase 03. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| INT-001 | BEST-PRACTICE | SPEC-DEVIATION | Comment declares intent for cleanup but no cleanup code exists. |
| INT-004 | BEST-PRACTICE | SPEC-DEVIATION | `-progress pipe:2` implies stdout unused but PIPE still set. |
| INT-006 | BEST-PRACTICE | SPEC-DEVIATION | No error differentiation violates explicit failure principles. |

---

## Final Assessment

All findings are validated as correct observations. INT-008 is merged into the Phase 03 finding for consolidation. The integration layer exhibits:

1. **Resource/config gaps** (INT-001, INT-002, INT-003): Incomplete implementation of documented behavior
2. **Deadlock risks** (INT-004, INT-005): Process lifecycle and pipe management issues
3. **Observability gaps** (INT-006): Undifferentiated failure modes
4. **Maintainability issues** (INT-007, INT-008): Hardcoded values and dead code coexistence