# Phase 05 Audit Findings — External Integrations

**Executor:** auditor (Senior architecture auditor)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/05-audit-integrations.md
**Status:** complete
**Validated:** no
**Problems-only:** yes (passing checks are omitted per phase output mode)
**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).
External integration surface audited: Playwright browser automation (infrastructure/browser.py),
yt-dlp (library mode services/extractor.py + subprocess CLI mode services/downloader.py),
ffmpeg subprocess (services/downloader.py, services/ffmpeg_utils.py), aiohttp HTTP client
(services/segment_downloader.py, services/downloader_throttle.py), OS signal handlers
(services/signal_handlers.py), shared shutdown ContextVar + URLBackoffCoordinator
(services/downloader_throttle.py), stealth.min.js injection (infrastructure/browser.py:27).
Reference docs: docs/01-tools/vkdownloader-overview.md,
docs/11-guides/vkdownloader-limitations.md, docs/11-guides/configuration.md.

## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 — Import | uv run python -c import all integration modules | PASS | All integration modules import cleanly; no import-time errors. |
| R2 — Lint | uv run ruff check src/vkdownloader/ tests/ | FAIL (pre-existing) | 1 error: tests/test_correlation.py:28 F841 unused (tracked CLI-003 in phase 01). src/vkdownloader/ alone: PASS. |
| R2 — Format | uv run ruff format --check src/vkdownloader/ tests/ | FAIL (pre-existing) | 4 files would reformat: services/downloader.py, tests/test_cli.py, tests/test_hls_downloader.py, tests/test_security.py — tracked as CLI-005 in phase 01. |
| R2 — Types | uv run mypy src/vkdownloader | FAIL (pre-existing) | 1 error: utils/correlation.py:55 unused type: ignore — tracked as CLI-004 in phase 01. No integration-module type errors. |
| R3 — Tests | uv run pytest | PASS | 325 passed. Key integration tests: test_hls_downloader.py, test_downloader_throttle.py, test_segment_downloader.py, test_extractor.py. |
| R4 — ffmpeg @file empirical | ffmpeg -headers @file -i url | FAIL | Multi-header @file produces CRLF error (mangled); inline works. See INT-001. |
| R5 — Wheel packaging | uv build --wheel + inspect | PASS | stealth.min.js IS included in wheel (vkdownloader/stealth.min.js, 2608 bytes). No packaging gap. |
| R6 — yt-dlp library opts | python -c inspect ydl_opts | FAIL | ydl_opts keys: extract_flat, no_warnings, nocheckcertificate, quiet. No socket_timeout, no retries. See INT-003. |
| R7 — Browser lifecycle | static read infrastructure/browser.py | FAIL | BrowserManager.__aexit__ (lines 61-66) has no timeout on close/stop. See INT-004. |

---

## Findings

### INT-001: ffmpeg `-headers @file` syntax does not pass cookies to ffmpeg — documented "secret-safe cookie passing" is non-functional

| Field | Value |
|-------|-------|
| **ID** | INT-001 |
| **Severity** | CRITICAL |
| **Type** | SPEC-DEVIATION, RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:393-539` (`HLSDownloader.download_with_ffmpeg`); `docs/01-tools/vkdownloader-overview.md:149-152` |
| **Classification** | mandatory |

**Description:** The ffmpeg download path (`DownloadMethod.FFMPEG`, also the fallback from `DownloadMethod.AUTO` at `perform_download` `downloader.py:1085-1110`) attempts to pass HTTP headers (User-Agent, Referer, Cookie) to ffmpeg via the @file response-file syntax: `"-headers", f"@{headers_file}"` (`downloader.py:436-437`). This is a fundamental misunderstanding of ffmpeg CLI semantics. The @file mechanism is ffmpeg's generic argument-file reader: it reads the file, splits content on whitespace/newlines into separate tokens, and splices them in as individual command-line arguments. It is NOT a mechanism for loading an option value from a file.

Consequence: with a multi-line headers file (`User-Agent: ...\r\nReferer: ...\r\nCookie: ...\r\n`), ffmpeg's @-reader splits the file into whitespace-delimited tokens (`User-Agent:`, `...`, `Referer:`, `...`, `Cookie:`, `vk=secret123;`). Only the first token (`User-Agent:`) is consumed as the -headers value; everything after becomes stray arguments. ffmpeg emits `No trailing CRLF found in HTTP header. Adding it.` and sends a mangled/empty header set — cookies are never applied. On authenticated VK CDNs this means ffmpeg receives 403/401 or downloads without a session, silently producing empty or corrupt output.

The project documentation explicitly advertises this mechanism as functional: "Secret-safe ffmpeg cookie passing: VK session cookies are written to a temporary headers file and passed to ffmpeg via the @file syntax instead of command-line -headers arguments" (`docs/01-tools/vkdownloader-overview.md:149-152`). The docstring of `_temp_headers_file` (`downloader.py:98-117`) likewise states "This prevents cookies from appearing in process argument lists." The documentation describes behavior that is non-functional.

This is a correctness failure (authenticated ffmpeg downloads do not work) layered on top of the already-filed SEC-001 (m3u8 URL tokens remain on the command line, so the process-listing protection goal is not even fully achieved).

**Evidence (empirical, ffmpeg N-117624, ffmpeg at C:\ffmpeg\ffmpeg.exe):**

Multi-header @file (the real-world case with User-Agent + Referer + Cookie):
```
[headers @ 00000123c3a44bc0] No trailing CRLF found in HTTP header. Adding it.
[headers @ 00000123c3a44bc0] HTTP error 404 Not Found
```
Inline -headers (the only correct syntax — no CRLF warning, headers applied):
```
[headers @ 000001ff70a40cc0] HTTP error 404 Not Found    # no CRLF warning
```

Code path:
- `downloader.py:422-427`: headers content built as `f"User-Agent: ...\r\nReferer: ...\r\n{cookie_part}"`
- `downloader.py:429`: `async with _temp_headers_file(headers_content) as headers_file:`
- `downloader.py:436-437`: `"-headers", f"@{headers_file}"` — the broken syntax
- `_temp_headers_file` (`downloader.py:98-117`): writes headers content to a temp file via `os.write(fd, headers.encode())`

**Recommendation (mandatory):** Replace the @file headers mechanism with one ffmpeg actually supports for file-based headers. Options:
1. Use ffmpeg's `cookies` protocol option (Netscape cookie file) — the project already creates a Netscape cookie file via `_create_temp_cookie_file` (`downloader.py:71`) and `_cookies_to_netscape` (`cookies.py:13`); pass it via `-cookies <file>` or the `cookies` URL parameter so ffmpeg reads cookies without them touching the command line.
2. If full header passing is required, inline -headers is the only correct syntax — but this reintroduces process-argument exposure (address SEC-001 jointly).

Either way, the @file path and `_temp_headers_file` must be removed or reworked. Effort: medium; priority: mandatory.

---

### INT-002: `test_download_with_ffmpeg_uses_header_file_syntax` provides false confidence by mocking subprocess and only checking @-prefix, never verifying ffmpeg reads headers from file

| Field | Value |
|-------|-------|
| **ID** | INT-002 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION, RUNTIME-ERROR |
| **Affected Modules** | `tests/test_hls_downloader.py:183-232`; `src/vkdownloader/services/downloader.py:429-441` |
| **Classification** | mandatory |

**Description:** The test `test_download_with_ffmpeg_uses_header_file_syntax` (`test_hls_downloader.py:184-232`) is the only test covering the ffmpeg headers-file mechanism — the exact mechanism that is broken (see INT-001). The test mocks `asyncio.create_subprocess_exec` and asserts only that:

1. The headers argument starts with `@` or `/` (line 224-226) — i.e. it checks the **prefix** of the argument, not that ffmpeg correctly reads multi-line HTTP headers from the file.
2. Cookie values do not appear in the command-line arguments (lines 228-232).

Neither assertion verifies that ffmpeg, when actually invoked, parses and applies the multi-line header content from the file. The test gives **false confidence** that the @file approach works for cookie safety, when in fact ffmpeg treats @file as a whitespace-splitting response-file reader (see INT-001 evidence: mangles multi-header content, emits "No trailing CRLF found in HTTP header").

Because the subprocess is fully mocked (`AsyncMock` with `returncode = 0`, `readline` returning `b""`), the test never exercises ffmpeg's real option parsing. A passing test here says nothing about whether headers reach ffmpeg.

This is not merely a test-quality gap — it is a test that actively **obstructs** detection of INT-001: the green test bar reassures maintainers that the cookie-safety mechanism is working, when it is silently broken.

**Evidence:**
- `tests/test_hls_downloader.py:192-207`: `mock_process = AsyncMock()`, `mock_process.returncode = 0`, `mock_process.stderr.readline = AsyncMock(return_value=b"")` — fully mocked, no real ffmpeg invoked.
- `tests/test_hls_downloader.py:224-226`: assertion only checks `headers_arg.startswith("@") or headers_arg.startswith("/")` — the @file prefix is what the code produces, but the assertion does not verify ffmpeg parses the file content as a single multi-line `-headers` value.
- `tests/test_hls_downloader.py:228-232`: assertions check `secret123` and `xyz789` are absent from `captured_args` — true by construction because cookies go into the file, but this proves nothing about whether ffmpeg reads them.
- The test was the *only* coverage of the `download_with_ffmpeg` headers path; there is no complementary test that invokes a real (or version-checked) ffmpeg binary to verify header application.

**Recommendation (mandatory):** Either (a) replace the mock-based assertion with an integration test that invokes a real ffmpeg binary and verifies it receives the correct HTTP headers (e.g. via a local test HTTP server that logs received headers), or (b) remove this test and its assertions until a real verification path exists — a green test that asserts only syntactic @file usage is worse than no test because it masks INT-001. Effort: medium; priority: mandatory.

---

### INT-003: yt-dlp library-mode extraction ignores Settings timeout/retry config and can hang indefinitely

| Field | Value |
|-------|-------|
| **ID** | INT-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION, BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/extractor.py:138-201` (`_extract_with_ytdlp`); `src/vkdownloader/services/downloader.py:294-307` (yt-dlp subprocess CLI options); `src/vkdownloader/config.py:45-96` |
| **Classification** | mandatory |

**Description:** yt-dlp is used in two modes — **library mode** for stream extraction
(`extractor.py:_extract_with_ytdlp`, called by `extract_streams` and `extract_streams_with_cookies`)
and **subprocess CLI mode** for actual download (`downloader.py:_build_ytdlp_cli_command`).

The subprocess CLI path correctly maps every relevant Settings field to yt-dlp CLI flags:
`--socket-timeout` = `settings.download_timeout` (`downloader.py:294`), `-R` / `--retries` =
`settings.max_retries` (`downloader.py:296`), `--fragment-retries` = `settings.max_retries`
(`downloader.py:298`), `--throttled-rate` = `settings.throttled_rate` (`downloader.py:302`).

The **library-mode** path (`extractor.py:140-145`) sets only four `ydl_opts` keys:
`quiet`, `no_warnings`, `extract_flat`, `nocheckcertificate`. It omits `socket_timeout`,
`retries`, `fragment_retries`, and `throttled_rate` — so the user's configured `download_timeout`,
`max_retries`, and `throttled_rate` Settings have **zero effect** on library-mode yt-dlp extraction.

Worse, the library-mode extraction runs via `loop.run_in_executor(None, _sync_extract)`
(`extractor.py:198`) with **no `asyncio.wait_for` timeout wrapper**. yt-dlp's internal
default socket timeout (when `socket_timeout` is unset) is 60 seconds, but yt-dlp can still
hang indefinitely on stuck connections or DNS issues. With no application-level timeout,
a single unresponsive VK video can block the entire asyncio event loop (via the thread executor)
for the duration of `Settings.download_timeout` (default 300s) or longer — and in batch mode
where the semaphore limits concurrency, a hung extraction starves other downloads.

This is a config-to-integration flow defect: Settings fields that reach the subprocess CLI path
do not reach the library path, and the library path has no independent timeout safety net.

**Evidence:**
- `extractor.py:140-145`:
  ```python
  ydl_opts = {
      "quiet": True,
      "no_warnings": True,
      "extract_flat": False,
      "nocheckcertificate": not self.settings.ssl_verify,
  }
  ```
  No `socket_timeout`, no `retries`, no `fragment_retries`, no `throttled_rate`.
- `extractor.py:198`: `streams, title = await loop.run_in_executor(None, _sync_extract)` — no
  `asyncio.wait_for` wrapper, no timeout.
- `downloader.py:294-307` (subprocess CLI path, for contrast):
  ```python
  "--socket-timeout", str(settings.download_timeout),
  "-R", str(settings.max_retries),
  "--fragment-retries", str(settings.max_retries),
  "--throttled-rate", str(settings.throttled_rate),
  ```
- `config.py:45-56`: `max_retries` (default 3), `download_timeout` (default 300),
  `throttled_rate` (default 10000) — all configurable Settings fields that are not propagated
  to `ydl_opts`.
- Empirically verified: `ydl_opts` keys at runtime are exactly
  `['extract_flat', 'no_warnings', 'nocheckcertificate', 'quiet']` — no timeout/retry keys.

**Recommendation (mandatory):** Propagate Settings to the library-mode path: add
`socket_timeout=settings.download_timeout`, `retries=settings.max_retries`,
`fragment_retries=settings.max_retries`, and `throttled_rate=settings.throttled_rate` to
`ydl_opts`. Additionally, wrap the `run_in_executor` call in `asyncio.wait_for(..., timeout=settings.download_timeout)`
so yt-dlp extraction cannot block the event loop indefinitely. Effort: small; priority: mandatory.

---

### INT-004: Playwright browser and Playwright instance shutdown has no timeout — can hang indefinitely on teardown

| Field | Value |
|-------|-------|
| **ID** | INT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE (operational reliability) |
| **Affected Modules** | `src/vkdownloader/infrastructure/browser.py:48-66` (`BrowserManager.__aexit__`); `src/vkdownloader/services/extractor.py:211-250` (`_extract_with_browser`) |
| **Classification** | mandatory |

**Description:** `BrowserManager` wraps Playwright browser lifecycle in an async context
manager. `__aexit__` (`browser.py:61-66`) calls `await self.browser.close()` and then
`await self.playwright.stop()` **without any timeout wrapper**. If the headless Chromium
process hangs during shutdown — a known intermittent issue with Chromium in headless mode
(often triggered by unclosed CDP connections, pending network requests, or extension
processes) — `browser.close()` and `playwright.stop()` will block forever, hanging the
entire download with no error message and no recovery path.

Compare this to the subprocess shutdown paths, which all use `cancel_subprocess()`
(`ffmpeg_utils.py:128-156`) with a 5-second SIGTERM-to-SIGKILL escalation:
```python
process.terminate()
await asyncio.wait_for(process.wait(), timeout=5.0)
process.kill()
```
The aiohttp segment downloader uses the shared `shutdown_event` ContextVar to interrupt
waits (`downloader_throttle.py:310-340` `_wait_with_shutdown`). The signal handler sets
that event on Ctrl+C (`signal_handlers.py:29-33`). But the browser close path ignores
the shutdown event entirely — even if Ctrl+C has been pressed and `shutdown_event` is set,
`__aexit__` will still call `browser.close()` with no timeout, blocking the graceful shutdown.

The `_extract_with_browser` method (`extractor.py:203-250`) calls the browser via
`async with BrowserManager(self.settings) as browser:` (line 211). If browser teardown hangs,
the context manager never exits, and the token-refresh-on-failure path
(`_attempt_segment_resume`, `downloader.py:677-683`) which forces `force_browser=True`
can wedge the entire fallback chain. In batch download mode (where a single stuck browser
teardown blocks the concurrency semaphore), this can stall all pending downloads.

**Evidence:**
- `browser.py:61-66`:
  ```python
  try:
      if self.browser:
          await self.browser.close()
  finally:
      if self.playwright:
          await self.playwright.stop()
  ```
  No `asyncio.wait_for`, no `shutdown_event` check, no timeout parameter passed to
  `browser.close()` (Playwright's `Browser.close()` accepts a `timeout` kwarg but it is not used).
- `ffmpeg_utils.py:128-156`: `cancel_subprocess` uses `asyncio.wait_for(process.wait(), timeout=5.0)`
  with SIGTERM-to-SIGKILL escalation — the established pattern for external resource cleanup.
- `downloader_throttle.py:310-340`: `_wait_with_shutdown` monitors `shutdown_event` during waits.
- `signal_handlers.py:29-33`: `setup_signal_handlers` registers handlers that set `shutdown_event`.
- `extractor.py:211`: `async with BrowserManager(self.settings) as browser:` — the only browser
  lifecycle boundary in the codebase.

**Recommendation (mandatory):** Wrap browser and Playwright teardown in a timeout with
the shared `shutdown_event`. Use `asyncio.wait_for` with a reasonable timeout (e.g. 10s)
matching the `cancel_subprocess` pattern, and check `get_shutdown_event().is_set()` before
attempting close. If close hangs, force `playwright.stop()` (which kills all browser processes)
as a fallback. Effort: small; priority: mandatory.

---

### INT-005: Misleading `ssl_verify_ignored_for_ffmpeg` warning contradicts actual SSL handling — ffmpeg DOES apply `-tls_verify 0`

| Field | Value |
|-------|-------|
| **ID** | INT-005 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION (doc/log contradiction) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:1062-1069` (warning); `src/vkdownloader/services/downloader.py:439-440` (actual SSL handling) |
| **Classification** | advisory |

**Description:** In `perform_download`'s `DownloadMethod.FFMPEG` branch, when
`settings.ssl_verify` is False, the application emits a warning claiming SSL verification
is ignored for the ffmpeg download path:

- `downloader.py:1062-1069`:
  ```python
  if not settings.ssl_verify:
      logger.warning(
          "ssl_verify_ignored_for_ffmpeg",
          url=_strip_auth_params(url),
          hint="The --no-ssl-verify flag is not applied to the direct ffmpeg download path;
  use --method yt-dlp or --method auto for SSL verification control on the CDN connection.",
      )
  ```

This warning is **factually wrong**. The ffmpeg download path (`HLSDownloader.download_with_ffmpeg`)
DOES apply SSL verification control via `-tls_verify 0` at `downloader.py:439-440`:

- `downloader.py:439-440`:
  ```python
  if not self.settings.ssl_verify:
      cmd.extend(["-tls_verify", "0"])
  ```

The `-tls_verify 0` flag is ffmpeg's standard mechanism to disable TLS certificate
verification — it is placed before `-i` (`downloader.py:441`) so it correctly applies to
the input m3u8 URL and segment fetches. The warning was almost certainly written before
`-tls_verify 0` was added to `download_with_ffmpeg`, and was never removed.

Consequence: when a user runs `vkdownloader --no-ssl-verify --method ffmpeg`, they see a
warning telling them SSL verification is NOT controlled, prompting them to switch to
`--method yt-dlp` or `auto` unnecessarily — even though `--method ffmpeg` correctly
respects the flag. This is misleading to operators debugging TLS issues.

**Evidence:**
- `downloader.py:1062-1069` — the warning claiming `--no-ssl-verify` is not applied to ffmpeg path.
- `downloader.py:439-440` — the actual `-tls_verify 0` flag that IS applied when `ssl_verify=False`.
- ffmpeg's `-tls_verify` is a valid global option documented at ffmpeg.org: "If set to 0,
  the TLS verification will be disabled."
- The `-tls_verify 0` appears before `-i` (`downloader.py:441`), which is the correct
  position for a global option affecting the subsequent input URL.

**Recommendation (advisory):** Remove the `ssl_verify_ignored_for_ffmpeg` warning block
at `downloader.py:1062-1069`. If any residual gap exists (e.g. segment fetching within
ffmpeg uses a different TLS path than the input), document it precisely rather than
claiming blanket non-support. Effort: trivial; priority: recommended.

---

### INT-006: Sequential download path broadly swallows programming errors as transient failures (divergent from parallel path)

| Field | Value |
|-------|-------|
| **ID** | INT-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE (error handling) |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py:224-238` (`_retry_429_with_backoff`); `src/vkdownloader/services/segment_downloader.py:271-286` (`_try_single_download_attempt`) |
| **Classification** | advisory |

**Description:** yt-dlp's segment-download retry logic is implemented in two divergent
code paths depending on whether `max_concurrent_downloads == 1` (sequential) or `> 1`
(parallel):

- **Sequential** (`_download_segment_sequential` → `_retry_429_with_backoff`,
  `downloader_throttle.py:149-238`): the retry function catches `asyncio.CancelledError`
  (correctly re-raised at line 224-228), then catches **broad `Exception`** at line 229
  and returns `None` — treating any unexpected error (including `TypeError`, `AttributeError`,
  `KeyError`, `ValueError`) as an indistinguishable download failure with no retry.

- **Parallel** (`_download_segment_parallel` → `_try_single_download_attempt`,
  `segment_downloader.py:255-286`): catches only `aiohttp.ClientError` (line 283),
  which is the correct granularity — network/HTTP-layer exceptions are retryable, while
  programming errors propagate.

The sequential path's `except Exception` (line 229) masks bugs: a malformed response
causing an `AttributeError` in response handling, a `KeyError` from malformed JSON, or
a `TypeError` from incorrect argument passing — all are silently logged as
`segment_download_error` and the segment is marked failed. The caller (`_download_segment_sequential`,
`segment_downloader.py:166-170`) returns `False`, and the segment is simply re-queued
or skipped, with no signal to the operator that something unexpected happened. In batch
mode this can cause silent data corruption (partial segments merged into incomplete video)
with only a warning in debug logs.

The two paths also diverge on what "non-retryable" means: the parallel path distinguishes
fatal HTTP status (returns `False`, fail-fast at line 239) from retryable (returns `None`
at line 237), while the sequential path lumps everything into `None` (retryable) via the
broad catch.

This divergence is undocumented: `api-reference.md:486-487` (per phase-03 finding SRV-004)
falsely claims parallel mode "uses direct download without retry backoff" — the reverse
issue of a similar documentation gap on the sequential path's exception handling.

**Evidence:**
- `downloader_throttle.py:224-229`:
  ```python
  except asyncio.CancelledError:
      logger.info("segment_download_cancelled", ...)
      raise
  except Exception as e:
      logger.error("segment_download_error", error=str(e), ...)
      return None
  ```
  The broad `except Exception` returns `None`, which the caller maps to a non-exception
  failure (segment `False`).
- `segment_downloader.py:283`:
  ```python
  except aiohttp.ClientError as e:
      logger.error("segment_download_error", error=str(e))
      return None
  ```
  The parallel path narrows to `aiohttp.ClientError` only.
- The `aiohttp` import is present in both modules (`downloader_throttle.py:9`, `segment_downloader.py:15`).

**Recommendation (advisory):** Narrow the sequential path's catch to `aiohttp.ClientError`
(and optionally `asyncio.TimeoutError`, which is a subclass of `OSError` not `aiohttp.ClientError`
— note `aiohttp.ClientError` does not cover `async_timeout.TimeoutError` in all aiohttp versions).
Any other `Exception` should propagate so programming errors are surfaced during development
and testing. Align both paths on the same exception taxonomy. Effort: small; priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 1 |
| **Total** | **6** |

## Mandatory Fixes

1. **INT-001 (CRITICAL):** ffmpeg `-headers @file` syntax is non-functional — cookies never reach ffmpeg. Replace with ffmpeg's `cookies` protocol option (Netscape cookie file) or inline `-headers`. Remove `_temp_headers_file` / `f"@{headers_file}"` path.
2. **INT-002 (HIGH):** `test_download_with_ffmpeg_uses_header_file_syntax` mocks subprocess and asserts only @-prefix existence — gives false confidence. Replace with real ffmpeg invocation against a test HTTP server, or remove until verified.
3. **INT-003 (MEDIUM):** yt-dlp library-mode extraction ignores Settings `download_timeout`, `max_retries`, `throttled_rate` and runs without `asyncio.wait_for` timeout. Propagate Settings to `ydl_opts` and wrap `run_in_executor` in `asyncio.wait_for`.

## Advisory Recommendations

1. **INT-004 (MEDIUM):** `BrowserManager.__aexit__` has no timeout on `browser.close()`/`playwright.stop()` — can hang indefinitely. Wrap in `asyncio.wait_for` with the shared `shutdown_event`.
2. **INT-005 (LOW):** `ssl_verify_ignored_for_ffmpeg` warning is stale — ffmpeg actually applies `-tls_verify 0`. Remove the misleading warning.
3. **INT-006 (MEDIUM):** Sequential download path broad `except Exception` in `_retry_429_with_backoff` masks programming errors. Narrow to `aiohttp.ClientError` + `asyncio.TimeoutError` to match parallel path.

## Doc Updates Needed

1. **INT-001 / docs-001:** `docs/01-tools/vkdownloader-overview.md:149-152` advertises ffmpeg `@file` cookie passing as functional. Once the code is fixed, update the doc to describe the actual mechanism (e.g. ffmpeg `cookies` file option). If the mechanism changes to inline `-headers`, update to reflect that cookies are on the process command line (referencing SEC-001 from phase 04).
2. **INT-005 / docs-002:** `docs/11-guides/configuration.md` (if it references the `--no-ssl-verify` flag behavior for ffmpeg) should be checked for the same stale claim. The warning text at `downloader.py:1062-1069` serves as the source of truth for any doc that references it.
3. **INT-006 / docs-003:** `docs/01-tools/api-reference.md` (per phase-03 finding SRV-004) already has stale retry/backoff documentation. Ensure any doc updates for INT-006 correct the parallel-mode behavior description as well.

---

*Findings written incrementally to this file. Last update: see git history.*


