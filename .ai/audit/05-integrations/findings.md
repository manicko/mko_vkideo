# Phase 05 Audit Findings — External Integrations

**Executor:** audit-executor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification (pre-audit)

- **R1 — Import check:** `uv run python -c "import vkdownloader.cli, ...extractor, ...segment_downloader"` → `IMPORT_OK`. No missing optional deps; integrations degrade gracefully when `headless`/browser absent (browser only launched on demand).
- **R2 — Ruff:** `ruff check` on all integration modules → `All checks passed! (exit 0)`.
- **R3 — Mypy:** `mypy` on integration modules → `Success: no issues found in 8 source files`.
- **R3 — Tests:** `pytest tests/ -k "integration|browser|ffmpeg|network|segment|extractor|cookie|download"` → `167 passed, 56 deselected`.

All green. Findings below are from code/architecture analysis of the boundary code, not from failing checks.

---

## Findings

### INT-001: Orphaned ffmpeg subprocesses — `_active_processes` is tracked but never killed on shutdown

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE / RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/ffmpeg_utils.py:15`, `src/vkdownloader/services/downloader.py:227,238,248,289,302` |
| **Classification** | mandatory (correctness / resource leak) |

**Description:** `ffmpeg_utils.py:15` declares a module-global `_active_processes: set[asyncio.subprocess.Process]` with the comment "Track active ffmpeg processes for cleanup". `HLSDownloader.download_with_ffmpeg` adds the spawned process to this set (`downloader.py:227`) and removes it in a `finally` (`downloader.py:302`). `cancel_ffmpeg_process` exists and is invoked *only from inside the same coroutine* on the active process (`downloader.py:238,248,289`). A grep across the whole `src/` tree shows **no code path ever iterates `_active_processes` to terminate members** — the signal handler (`signal_handlers.py`) only sets `shutdown_event`; nothing drains the set.

Consequence: the set is pure bookkeeping. If `download_with_ffmpeg` is interrupted (Ctrl+C / `CancelledError`) after the process is spawned but before the `finally` runs cleanly — or if the cancellation does not propagate into the `asyncio.wait` block — the ffmpeg child process is leaked with its stdout/stderr pipes open. The module docstring promises cleanup that does not exist, so operators cannot rely on graceful teardown, and concurrent/batch runs can accumulate zombie ffmpeg processes bound to output files.

**Evidence:**
```python
# ffmpeg_utils.py:15
_active_processes: set[asyncio.subprocess.Process] = set()   # "Track ... for cleanup" — never consumed

# downloader.py:227 (inside download_with_ffmpeg)
_active_processes.add(process)
...
# downloader.py:302 (finally)
_active_processes.discard(process)
# -> no other reference to `_active_processes` anywhere in src/
```

**Recommendation:** Either (a) remove the global set and the misleading comment (since cleanup is handled per-coroutine via `cancel_ffmpeg_process` in the `finally`), or (b) make it functional: register an `atexit`/signal-time iterator that calls `cancel_ffmpeg_process` on every member so shutdown actually terminates tracked subprocesses. Prefer (a) for simplicity — the per-coroutine `finally` already covers the normal path, and a real global registry needs locking and loop-binding that this codebase deliberately avoids (see `downloader_throttle.get_shutdown_event` ContextVar pattern). Effort: small. Priority: recommended.

---

### INT-002: `accept_language` config field is silently ignored by the browser integration

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py:27`, `src/vkdownloader/infrastructure/browser.py:64-69`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** `Settings.accept_language` is defined (`config.py:27`) and documented as "Accept-Language header for browser requests" (`configuration.md`). However `BrowserManager.create_stealth_page` builds the Playwright context using only `user_agent`, `locale`, and `timezone` (`browser.py:64-69`); `accept_language` is never read. A user setting `VKDOWNLOADER_ACCEPT_LANGUAGE` has zero effect. Beyond the config deviation, the browser context is launched without an `Accept-Language` header, which weakens the stealth profile the project explicitly depends on (VK multi-layer bot detection, per `vkdownloader-limitations.md`).

**Evidence:**
```python
# browser.py:64
context = await self.browser.new_context(
    viewport={"width": 1920, "height": 1080},
    user_agent=self.settings.user_agent,
    locale=self.settings.locale,
    timezone_id=self.settings.timezone,
    # accept_language is NEVER passed here
)
```

**Recommendation:** Pass `accept_language=self.settings.accept_language` into `new_context(...)` (Playwright supports the `accept_language` kwarg), or remove the field and its docs if the header is intentionally not sent. Keeping a documented-but-dead config field invites silent misconfiguration. Effort: trivial. Priority: recommended.

---

### INT-003: `download_timeout` config is not propagated to yt-dlp (hardcoded `socket_timeout: 180`)

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py:51`, `src/vkdownloader/services/downloader.py:528`, `docs/11-guides/configuration.md` |
| **Classification** | advisory |

**Description:** `Settings.download_timeout` (default 300s, range 30–3600) is documented as the global "Download timeout in seconds" and is honored by the aiohttp/segment path (`segment_downloader.py` uses `settings.download_timeout` for `aiohttp.ClientTimeout`). But the yt-dlp path hardcodes `"socket_timeout": 180` (`downloader.py:528`) and does not pass `settings.download_timeout` at all. A user who raises `VKDOWNLOADER_DOWNLOAD_TIMEOUT` to 3600 to survive slow CDNs gets no effect on the yt-dlp code path, which will still abort sockets at 180s. This is an inconsistent config-to-integration flow and a silent partial-ignore of a documented field.

**Evidence:**
```python
# downloader.py (inside _download_with_ytdlp)
"socket_timeout": 180,                 # hardcoded, ignores settings.download_timeout
"retries": settings.max_retries,       # max_retries IS honored; timeout is not
```

**Recommendation:** Use `settings.download_timeout` for yt-dlp's `socket_timeout` (and consider `http_timeout`/`timeout` options) so the documented global timeout applies uniformly across both download paths. Effort: trivial. Priority: recommended.

---

### INT-004: ffmpeg stdout pipe is never drained — deadlock risk under large stdout

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:222,235-262,272-290` |
| **Classification** | mandatory (operational reliability) |

**Description:** In `download_with_ffmpeg`, the ffmpeg subprocess is created with `stdout=asyncio.subprocess.PIPE` and `stderr=asyncio.subprocess.PIPE` (`downloader.py:222-223`). Only `stderr` is ever read — either by `_monitor_progress` (when a `progress_callback` is supplied) or by `_drain_stderr` (otherwise). `stdout` is never read. ffmpeg normally prints to stderr, but its startup banner and any unexpected stdout output are captured into the OS pipe buffer (typically 64 KB on Windows). If ffmpeg ever writes ~64 KB to stdout, the pipe fills and ffmpeg blocks on the write syscall, deadlocking the whole `download_with_ffmpeg` coroutine with no timeout and no error — it will hang until the outer `download_timeout`/signal path intervenes, if at all.

**Evidence:**
```python
# downloader.py:222-223
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,   # never read anywhere
    stderr=asyncio.subprocess.PIPE,   # read via monitor/drain only
)
# _monitor_progress / _drain_stderr only operate on process.stderr
```

**Recommendation:** Set `stdout=asyncio.subprocess.DEVNULL` (ffmpeg progress is on stderr via `-progress pipe:2`), or spawn a dedicated task that drains `process.stdout`. This removes the latent deadlock and frees the OS pipe buffer. Effort: trivial. Priority: recommended.

---

### INT-005: yt-dlp / ffmpeg child processes leak on cancellation (thread executor not interruptible)

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:602-642` (`_download_with_ytdlp`) |
| **Classification** | mandatory (resource leak / correctness) |

**Description:** `_download_with_ytdlp` runs yt-dlp inside a worker thread via `loop.run_in_executor(None, _download)` (`downloader.py:622`). yt-dlp in turn spawns its own ffmpeg child process. On `asyncio.CancelledError` the code cancels the *asyncio task* (`downloader.py:632-636`) but the underlying thread — and the yt-dlp/ffmpeg process it owns — is neither daemonized nor interrupted; the docstring explicitly admits "the thread will continue." Under Ctrl+C / batch cancellation this means the yt-dlp+ffmpeg subtree keeps running in the background, holding the output file and any temp cookie file (`downloader.py:546-560` writes a Netscape cookie file that is only unlinked in the thread's `finally`). The temp cookie file cleanup can race with the still-running thread, and the output file stays locked, so a resume attempt may collide.

**Evidence:**
```python
# downloader.py:622
 download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))
# ...
# downloader.py:631-637 (on CancelledError)
 if not download_task.done():
     download_task.cancel()   # cancels the await, NOT the worker thread / yt-dlp process
# docstring: "the thread will continue, it will be cleaned up when the process exits"
```

**Recommendation:** Make the cancellation actually reach yt-dlp — e.g. keep a reference to the `yt_dlp.YoutubeDL` instance and call `ydl.interrupt_download()` / set a shared stop flag checked inside a progress hook, or run yt-dlp with a process-group handle that is killed on cancellation. At minimum, ensure the temp cookie file is removed by the spawning coroutine (not only the thread) to avoid races. Effort: medium. Priority: recommended.

---

### INT-006: Permanent segment failures are indistinguishable and surfaced only as a count mismatch

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py:163-204` (`_retry_429_with_backoff`), `src/vkdownloader/services/segment_downloader.py:530-560` (`_process_downloaded_segments`) |
| **Classification** | advisory |

**Description:** `_retry_429_with_backoff` returns `None` for *both* a permanently non-retryable status (e.g. 403/410 not in `RETRYABLE_STATUS_CODES`) and for a transient error that exhausted retries, with only a `logger.warning`. The sequential caller (`_download_segment_sequential`) converts `None` → `False` with no per-segment error captured. In `_process_downloaded_segments`, the only signal that something went wrong is `downloaded_count != len(segments)`, which silently skips the merge and returns `None` for the whole video. There is no distinct log that a *specific* segment failed permanently, making production incidents hard to diagnose (was it a transient blip, a hard 403, or a truncated file?). This is an observability gap at the integration boundary.

**Evidence:**
```python
# downloader_throttle.py:175-181 (non-retryable)
if response.status not in RETRYABLE_STATUS_CODES:
    logger.warning("segment_download_failed_non_retryable", status=...)
    return None          # same None as retry-exhausted / exception path
# _process_downloaded_segments:
if downloaded_count == len(segments):   # merge
    ...
return None                            # silent: no per-segment failure record
```

**Recommendation:** Return/record a typed result (e.g. an enum or `(ok, reason)` tuple) so permanent failures are logged with the segment index and status, and consider failing the whole download early with a clear error instead of a silent `None`. Effort: small. Priority: recommended.

---

### INT-007: Hardcoded magic-number sleeps in browser extraction are fragile

| Field | Value |
|-------|-------|
| **ID** | INT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py:200,202` (`_extract_with_browser`) |
| **Classification** | advisory |

**Description:** `_extract_with_browser` uses fixed `await asyncio.sleep(5)` after `page.goto` and `await asyncio.sleep(8)` after simulating interaction (`extractor.py:200,202`) to wait for the stream/token to appear. These magic numbers are not configurable and not tied to any observable condition (e.g. waiting for a network-idle or a captured m3u8). On a slow CDN the token may not be ready in 8s (silent `monitor.m3u8_urls` empty → `VideoNotFoundError`); on a fast one, 13s of dead wait is pure latency. The values are also not documented, so tuning requires code changes.

**Evidence:**
```python
# extractor.py:200,202
await asyncio.sleep(5)
await self._simulate_video_interaction(page)
await asyncio.sleep(8)   # fixed; no config, no event-based wait
```

**Recommendation:** Replace fixed sleeps with condition-based waits (e.g. poll `monitor.m3u8_urls` / wait for a specific network response with a bounded timeout), or at least expose the waits via `Settings`. Effort: small. Priority: recommended.

---

### INT-008 (cross-reference): Insecure/secure ffmpeg header builders coexist — already raised in Phase 03

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:144-166` (`_build_ffmpeg_cmd`) |
| **Classification** | advisory |

**Description:** `HLSDownloader._build_ffmpeg_cmd` (dead code, called only by tests) inlines the cookie value directly into the ffmpeg argv (`-headers "Cookie: {cookies}"`), the exact anti-pattern the live path avoids by routing cookies through a temp `@file` via `_temp_headers_file`. This was previously filed as SRV-002 in Phase 03 and the validator *rejected* the security framing (incorrect evidence: it claimed the method was in `__all__`, which it is not). The dead-code / coexistence concern remains valid from an integration-boundary perspective: keeping an insecure builder next to the secure one is a maintenance hazard if a future refactor switches `download_with_ffmpeg` to call it. No new evidence beyond the prior phase; recorded here for integration-phase completeness. Effort: small. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 4 |
| LOW | 3 |

## Mandatory Fixes

- **INT-001** (HIGH) — `_active_processes` is tracked but never killed on shutdown; ffmpeg subprocesses can be orphaned. Implement real cleanup or remove the dead global.
- **INT-004** (MEDIUM) — ffmpeg stdout pipe never drained; latent deadlock under large stdout.
- **INT-005** (MEDIUM) — yt-dlp/ffmpeg child processes leak on cancellation because the worker thread is not interruptible.

## Advisory Recommendations

- **INT-002** (MEDIUM, SPEC-DEVIATION) — `accept_language` config field ignored by the browser integration.
- **INT-003** (MEDIUM, SPEC-DEVIATION) — `download_timeout` not propagated to yt-dlp (hardcoded `socket_timeout: 180`).
- **INT-006** (LOW) — permanent segment failures indistinguishable / silent `None`.
- **INT-007** (LOW) — hardcoded magic-number sleeps in browser extraction.
- **INT-008** (LOW, cross-reference) — insecure/secure ffmpeg header builders coexist (previously SRV-002, validator-rejected security framing; dead-code concern stands).

## Doc Updates Needed

- **INT-002** — `docs/11-guides/configuration.md` lists `accept_language` as "Accept-Language header for browser" but it is never applied; either document the gap or fix the code.
- **INT-003** — `docs/11-guides/configuration.md` presents `download_timeout` as a global download timeout; clarify it does not currently affect the yt-dlp path.
