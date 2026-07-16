# Phase 05 Audit Findings — External Integrations

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** no

---

## Scope Note — Task/Reality Mismatch

The phase task file (`05-audit-integrations.md`) is written generically and references integrations
such as Telegram, Google Sheets, Telethon, and `telepost`. A repository-wide grep confirmed **none
of these exist** in this codebase. This is a VK video downloader (CLI) whose real external
integrations are:

- **yt-dlp** (`yt_dlp.YoutubeDL`) — stream extraction + primary download (blocking, run in thread pool).
- **ffmpeg** — invoked as a subprocess via `asyncio.create_subprocess_exec` for HLS→MP4 and segment merge.
- **Playwright (Chromium)** — `BrowserManager` + `NetworkMonitor` for cookie capture and m3u8 discovery.
- **aiohttp** — `ClientSession` for direct HLS segment and playlist fetching (CDN).
- **URLBackoffCoordinator** — shared rate-limit backoff across segments (in-process, not an external system).
- **signal handlers** — `SIGINT`/`SIGTERM` → graceful shutdown event.

The audit below covers the **actual** integration surface. The phantom Telegram/Google-Sheets/etc.
references in the task file should be treated as template boilerplate, not as a spec deviation
(their absence is expected for this project).

---

## Runtime Verification (completed)

| Step | Command | Result |
|------|---------|--------|
| R1 — Import | `uv run python -c "import vkdownloader.cli; ... infra.browser; ... services.extractor; services.downloader; services.segment_downloader; services.downloader_throttle; services.ffmpeg_utils"` | `IMPORTS_OK` — no import errors, optional deps present |
| R2 — Linter | `uv run ruff check src/.../infrastructure src/.../services src/.../utils` | `All checks passed!` |
| R2 — Types | `uv run mypy src/vkdownloader/infrastructure src/.../extractor.py ...` | `Success: no issues found in 8 source files` |
| R3 — Tests | `uv run pytest tests/test_browser_infrastructure.py tests/test_ffmpeg_utils.py tests/test_extractor.py tests/test_hls_downloader.py tests/test_downloader_throttle.py` | `154 passed` |

Runtime verification surfaced **no crashes**, but static analysis of the integration boundary
revealed the findings below.

---

## Findings

### INT-001: `download_timeout` config is never applied to any HTTP request (no request timeout)

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/config.py` (L41-46), `src/vkdownloader/services/segment_downloader.py` (`_run_download_session`, `_fetch_playlist_with_retry`, `_run_parallel_download_with_backoff`, `_download_segment_sequential`/`_retry_429_with_backoff`) |
| **Classification** | mandatory (correctness/reliability) |

**Description:** `Settings.download_timeout` (default 300s, range 30–3600, documented in
`docs/11-guides/configuration.md`) is a real, validated config field, but it is **never read** by
any aiohttp call. Every `session.get(...)` in `segment_downloader.py` and `downloader_throttle.py`
is made **without a `ClientTimeout` / `timeout=` argument**. There is also no `aiohttp.TCPConnector`
or session-level timeout. A slow/hung CDN socket will block a segment (or the playlist fetch)
indefinitely; the only way out is the user pressing Ctrl+C (shutdown event). The failure also
leaks into batch mode, where one hung URL can stall the shared semaphore.

Grep confirms: there is no `ClientTimeout` or `timeout=` anywhere in the codebase (22 `timeout=`
occurrences, all `asyncio.wait_for(shutdown_event.wait(), timeout=...)` for shutdown, or
`cancel_ffmpeg_process(timeout=5.0)` / `page.goto(timeout=60000)` — none apply to CDN fetches).

**Evidence:**
- `config.py:41-46` — `download_timeout` field defined and documented as "Download timeout in seconds".
- `segment_downloader.py:317` — `async with session.get(current_url, headers=headers) as response:` (no timeout).
- `segment_downloader.py:112` — `async with session.get(segment_url, headers=headers) as response:` (no timeout).
- `downloader_throttle.py:184` — `async with session.get(segment_url, headers=headers) as response:` (no timeout).
- Grep for `ClientTimeout` returns zero matches.

**Recommendation:** Construct an `aiohttp.ClientTimeout(total=settings.download_timeout)` and pass
`timeout=` to every `session.get(...)`. This makes the configured field effective and prevents
indefinite hangs on a dead CDN connection. Effort: small. Priority: recommended (fixes a real
reliability hole where a legit config knob is inert).

---

### INT-002: `accept_language` config field is defined and documented but never consumed

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (L23-26), `src/vkdownloader/infrastructure/browser.py` (`create_stealth_page`) |
| **Classification** | advisory |

**Description:** `Settings.accept_language` has a default and a documented env var
(`VKDOWNLOAD_ACCEPT_LANGUAGE`) in `docs/11-guides/configuration.md`, but it is **never passed** to
the Playwright browser context. `BrowserManager.create_stealth_page` only sets `user_agent`,
`locale`, and `timezone_id` (browser.py:64-69). The `accept_language` field is dead config — a
user setting it has no effect, and the browser will send Playwright's default Accept-Language
header.

**Evidence:**
- `config.py:23-26` — field defined.
- `browser.py:64-69` — `new_context(user_agent=..., locale=..., timezone_id=...)`; no `accept_language` key.
- Grep for `accept_language` finds only the config definition (no usage).

**Recommendation:** Either (a) wire `accept_language` into `new_context(..., accept_language=self.settings.accept_language)` so the documented setting works, or (b) remove the field and its doc entry. The code choice (omitting it) is simpler; if stealth realism benefits from a ru-RU Accept-Language, option (a) is preferable. Effort: trivial. Priority: recommended.

---

### INT-003: Rate-limit backoff pause marks the next segment attempt as a *failure* instead of waiting

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | HIGH |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` (`URLBackoffCoordinator.wait_if_paused` L56-69), `src/vkdownloader/services/segment_downloader.py` (`_check_backoff_before_attempt` L137-147, `_download_segment_parallel` L217-229, `_notify_backoff_for_retryable_status` L79-86) |
| **Classification** | mandatory (correctness) |

**Description:** The shared `URLBackoffCoordinator` is designed so that when one segment of a URL
hits 429/5xx, all segments pause. On a 429, `_notify_backoff_for_retryable_status` calls
`await backoff_coordinator.pause(video_url, 10.0)` (segment_downloader.py:86). On the next segment
attempt, `_download_segment_parallel` calls `_check_backoff_before_attempt`, which calls
`wait_if_paused`.

The bug: `wait_if_paused` returns `True` in **two distinct situations** — (a) shutdown was
triggered, and (b) the backoff window elapsed **normally** (it falls through to `return True` at
L69 after `TimeoutError`). `_check_backoff_before_attempt` then returns `True`, and
`_download_segment_parallel` treats that as "abort → return False" (segment failed).

Consequence: after a normal, *successful* backoff wait, the segment attempt is recorded as a
**failure**, consuming one of the `max_retries` slots. With the default `max_retries=3`, a single
rate-limit event can burn all retries across the URL's segments and mark the download failed —
exactly the opposite of the intended "pause then continue" behavior. The unit test
`test_wait_if_paused_waits_until_backoff_expires` even asserts `result is True` for normal
completion, codifying the buggy contract.

**Evidence:**
- `downloader_throttle.py:56-69` — `wait_if_paused` returns `True` on normal timeout (L68-69), same as on shutdown.
- `segment_downloader.py:142-147` — returns `True` to abort.
- `segment_downloader.py:220-221` — `if await _check_backoff_before_attempt(...): return False` (segment fails).
- `segment_downloader.py:85-86` — `pause(video_url, 10.0)` on retryable status.

**Recommendation:** Distinguish "still paused, keep waiting" / "shutdown" from "backoff done,
proceed". `wait_if_paused` should return a three-state result (or a bool meaning *only* "abort due
to shutdown") and the caller should *continue* the loop after backoff rather than return failure.
The simplest correct fix: have `wait_if_paused` return `True` only when shutdown is set, and return
`False` (proceed) when the pause simply elapsed. Effort: small. Priority: recommended (this
defeats the rate-limit resilience the coordinator exists to provide).

---

### INT-004: Playwright always launches `headless=False` — hard failure on servers/CI/Docker

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py` (L34-37), `src/vkdownloader/services/extractor.py` (`extract_streams_with_cookies`, `_extract_with_browser`) |
| **Classification** | advisory |

**Description:** `BrowserManager.__aenter__` hardcodes `headless=False` (browser.py:35). This is
documented in `docs/11-guides/vkdownloader-limitations.md` as a deliberate workaround for VK's
headless detection. However, it means cookie-based download (`--cookie-source browser`) **cannot
run anywhere without a display**: headless Linux servers, CI pipelines, and the Docker-only
deployment posture mentioned in the audit rules will fail at `chromium.launch(headless=False)`
(no X server). There is no config toggle (`Settings` has no `headless` field), so the user cannot
opt into headless even where acceptable.

**Evidence:**
- `browser.py:34-37` — `await playwright_instance.chromium.launch(headless=False, args=[...])` with no settings-driven option.
- `config.py` — no `headless` setting exists.
- Docs confirm the non-headless requirement but frame it only as "user must wait for a browser window", not as a hard environment requirement.

**Recommendation:** Add a `headless` setting (default `False` to preserve current anti-bot behavior,
overridable to `True` for servers). When `True`, also consider `args=["--no-sandbox"]` for
containerized environments. Document the display requirement explicitly. Effort: small.
Priority: recommended (portability / deployment beyond the developer's desktop).

---

### INT-005: Network monitor silently swallows all JSON-parse errors (`except Exception: pass`)

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/network_monitor.py` (L62-70) |
| **Classification** | advisory |

**Description:** In `_intercept_response`, when VK returns a JSON XHR, the monitor calls
`await response.json()` inside a `try/except Exception: pass` block (network_monitor.py:66-70).
Catching bare `Exception` (vs. `json.JSONDecodeError` / `aiohttp.ContentTypeError`) means any
programming error, attribute error, or unexpected exception in `_extract_urls_from_json` is also
silently discarded. This masks bugs and makes it impossible to tell whether a stream URL was
missed due to a malformed response or a code defect.

**Evidence:**
- `network_monitor.py:66-70` — `except Exception: pass` around `response.json()` and recursive extraction.

**Recommendation:** Narrow the handler to `except (json.JSONDecodeError, aiohttp.ContentTypeError)`
and log a debug line on skip (stream URLs are already redacted). This preserves the "ignore
malformed JSON" intent while surfacing real errors. Effort: trivial. Priority: recommended.

---

### INT-006: `CookieSource.FILE` is documented-but-unimplemented; `_should_abort_retry` is dead code

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` (L123-127), `src/vkdownloader/services/segment_downloader.py` (`_should_abort_retry` L128-135), `models/enums.py` (`CookieSource.FILE`) |
| **Classification** | advisory |

**Description:** Two related "documented but non-functional" items:
1. `CookieSource.FILE` is an enum value exposed on the CLI (`--cookie-source file`), and
   `configuration.md` explicitly states "file is not implemented; selecting it raises
   `NotImplementedError`". The code raises `NotImplementedError` (extractor.py:124-127). This is
   consistent with docs, but the enum value remains a live, selectable CLI option that can only
   fail. Per the Dead Code Policy this is arguably "future-proofing" — acceptable, but the CLI
   should ideally not offer an option guaranteed to raise.
2. `_should_abort_retry` (segment_downloader.py:128-135) is defined but **never called** anywhere
   (grep confirms only its definition). It is dead code; its body (`return backoff_coordinator is
   not None and video_url is not None`) is also a near-no-op that doesn't reflect its name.

**Evidence:**
- `extractor.py:123-127` — `raise NotImplementedError(...)` for `CookieSource.FILE`.
- `segment_downloader.py:128-135` — `_should_abort_retry` defined, zero call sites.
- `enums.py:60` — `FILE = "file"` exposed to CLI.

**Recommendation:** (a) Either remove `CookieSource.FILE` from the enum or implement it; if kept as
a stub, it should not be a user-selectable CLI choice without clear `NotImplemented` feedback at
parse time. (b) Delete `_should_abort_retry` (or wire it in if a real abort decision was intended).
Effort: trivial. Priority: recommended.

---

### INT-007: Cookie→ffmpeg header formatting truncates to 20 cookies and hardcodes CDN domain in Netscape path

| Field | Value |
|-------|-------|-------|
| **ID** | INT-007 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py` (`_format_cookies_for_ffmpeg` L234-245), `src/vkdownloader/services/cookies.py` (`_cookies_to_netscape` L6-20) |
| **Classification** | advisory |

**Description:**
1. `_format_cookies_for_ffmpeg` joins **only the first 20 cookies** (`cookie_parts[:20]`,
   extractor.py:245) into the ffmpeg `Cookie:` header with a comment "Limit to avoid header size
   issues". VK CDN/authentication commonly relies on multiple cookies (including `remix`/`vk`/
   `auth`/session tokens). Arbitrarily dropping cookies #21+ can produce an **incomplete auth
   header** that silently fails CDN segment requests with 403 — which then triggers the 403 token
   refresh path, wasting work or failing the download. The truncation is undocumented and
   unconditional.
2. `_cookies_to_netscape` (cookies.py:19) hardcodes the domain to `.vkvideo.ru` for **every**
   cookie, regardless of the cookie's actual `domain` attribute from the browser. If any required
   cookie is scoped to a different host (e.g. `vk.com`, `userapi.com`, or the `okcdn.ru` CDN), the
   Netscape file will carry a wrong domain and yt-dlp may ignore it. Because `_cookies_to_netscape`
   is only used on the yt-dlp path (not the ffmpeg header path), its impact is narrower, but the
   hardcoded domain is still a latent correctness issue.

**Evidence:**
- `extractor.py:245` — `return "; ".join(cookie_parts[:20])`.
- `cookies.py:19` — `lines.append(f".vkvideo.ru\tTRUE\t/\tFALSE\t0\t{name}\t{value}")` for every cookie.
- `extractor.py:241-242` — strips `\r`/`\n` from name/value but not `"` (acceptable since argv-passed, but worth noting the header is built as a single `-headers` arg).

**Recommendation:** (a) Remove or make the 20-cookie cap configurable; if a header-size guard is
truly needed, log a warning when cookies are dropped so auth failures are diagnosable. (b) Build
the Netscape line from the cookie's real `domain` (falling back to `.vkvideo.ru`) instead of
hardcoding. Effort: small. Priority: recommended.

---

### INT-008: ffmpeg subprocess success depends on returncode only; `process.wait()` race with progress reader is not fully guarded

| Field | Value |
|-------|-------|
| **ID** | INT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`download_with_ffmpeg` L171-253) |
| **Classification** | advisory |

**Description:** In `download_with_ffmpeg`, the code correctly tracks the process in
`_active_processes` and cancels on shutdown, and reads stderr to avoid buffer deadlock. However:
- When `progress_callback` is provided, the code waits on `process_task` and `monitor_task` with
  `FIRST_COMPLETED` and cancels the loser, then reads `stderr_data`. If ffmpeg exits non-zero but
  the monitor task is still mid-iteration, the `finally` discards the process but `stderr_data` may
  be incomplete (acceptable for logging). More importantly, a non-zero exit is only detected via
  `process.returncode != 0` — for the no-callback path the same holds. This is functionally fine,
  but there is **no check that `output_file` actually grew / exists** before returning "success":
  `download_with_ffmpeg` returns `output_file` whenever `returncode == 0`, even if ffmpeg wrote
  zero bytes (e.g., a valid-but-empty or instantly-aborted stream). The caller then treats a
  possibly-empty file as a successful download.
- `_active_processes` is a module-global set; on `KeyboardInterrupt` outside an `await` point the
  process set is not iterated to kill stragglers (signal handler only sets the event; ffmpeg is
  only cancelled when control returns to an `await` checkpoint). This is a minor resource-leak
  edge case, not a correctness break.

**Evidence:**
- `downloader.py:243-251` — success path returns `output_file` based solely on `returncode == 0`.
- `downloader.py:178 / 253` — `_active_processes.add/discard`; no global cleanup loop on hard interrupt.

**Recommendation:** After a zero returncode, verify `output_file.exists()` and
`output_file.stat().st_size > 0` before declaring success (return `None` + error otherwise). The
global ffmpeg kill on hard interrupt is optional given the shutdown-event design. Effort: trivial.
Priority: recommended.

---

### INT-009: yt-dlp runs in a thread pool with no cancellation of the underlying native download

| Field | Value |
|-------|
| **ID** | INT-009 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` (`_download_with_ytdlp` L434-500), `src/vkdownloader/services/extractor.py` (`_extract_with_ytdlp` L146-194) |
| **Classification** | advisory |

**Description:** yt-dlp is invoked inside `loop.run_in_executor(None, _download)` /
`_sync_extract`. On `asyncio.CancelledError`, the code calls `download_task.cancel()` but the
blocking thread continues running until yt-dlp finishes or its socket times out (the comment at
downloader.py:493-494 acknowledges this). There is no `ydl.stop_download()` hook wired, and no
thread-interrupt mechanism. The consequence is that a Ctrl+C during a yt-dlp download does not
actually stop the native download promptly — it lingers, holding the output file and bandwidth.
This is a known limitation of running blocking libraries under `run_in_executor`, but it degrades
the "graceful shutdown" guarantee the signal handlers promise.

**Evidence:**
- `downloader.py:486-497` — `download_task = asyncio.ensure_future(loop.run_in_executor(None, _download))`; on cancel only `download_task.cancel()` is called; comment notes the thread "will continue".
- `extractor.py:191` — same `run_in_executor` pattern for extraction.

**Recommendation:** Hold a reference to the `YoutubeDL` instance and call `ydl.stop_download()` from
the signal/shutdown handler (yt-dlp supports it), or document that yt-dlp downloads do not
interrupt instantly. Effort: small. Priority: recommended (operability of Ctrl+C).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 3 |

**Note on runtime verification:** `uv run pytest` (154 integration-related tests), `ruff check`,
and `mypy` all pass; module imports succeed. No crash or type error was found at runtime. All
findings below are static-analysis / design defects in the integration boundary that tests do not
exercise (notably the backoff-abort logic, the missing HTTP timeout, and the headless requirement).

## Mandatory Fixes

- **INT-001** (HIGH) — Wire `download_timeout` into aiohttp `ClientTimeout`; without it, CDN fetches have no timeout and can hang indefinitely.
- **INT-003** (HIGH) — Fix `URLBackoffCoordinator.wait_if_paused` so a completed backoff does not mark the segment as failed; current behavior defeats rate-limit resilience and can fail downloads prematurely.

## Advisory Recommendations

- **INT-002** (LOW) — Consume or remove the inert `accept_language` config field.
- **INT-004** (MEDIUM) — Make Playwright `headless` configurable; `headless=False` hard-fails on servers/CI/Docker.
- **INT-005** (MEDIUM) — Narrow `except Exception: pass` in the network monitor to specific exceptions and log skips.
- **INT-006** (LOW) — Remove dead `_should_abort_retry`; decide FILE cookie source (implement or de-expose from CLI).
- **INT-007** (MEDIUM) — Remove the unconditional 20-cookie cap (or warn on drop); use real cookie domain in Netscape export.
- **INT-008** (LOW) — Verify output file size after ffmpeg zero-returncode before reporting success.
- **INT-009** (LOW) — Wire `ydl.stop_download()` so Ctrl+C actually stops a yt-dlp download thread.

## Doc Updates Needed

- **INT-002 / DOC-UPDATE** — `docs/11-guides/configuration.md` documents `accept_language` as effective; either implement it or strike it from the settings table.
- **INT-004 / DOC-UPDATE** — `docs/11-guides/vkdownloader-limitations.md` should state explicitly that `--cookie-source browser` requires a graphical display (headless=False), i.e. it will not run on headless servers/CI/Docker without one.
- **INT-006 / DOC-UPDATE** — The CLI help (`--cookie-source file`) and `CookieSource.FILE` enum advertise an option that always raises `NotImplementedError`; either document the failure clearly at the CLI layer or remove the choice.

---
