# Phase 05 Audit Findings — External Integrations (VALIDATED)

**Executor:** validator
**Source:** .ai/audit/05-audit-integrations/findings.md
**Validated against:** src/vkdownloader/ (downloader.py, extractor.py, infrastructure/browser.py, services/cookies.py, ffmpeg_utils.py, downloader_throttle.py, segment_downloader.py, config.py), tests/test_hls_downloader.py, docs/01-tools/vkdownloader-overview.md, docs/11-guides/configuration.md
**Date:** 2026-08-09
**Status:** complete — all six findings verified against implementation

Validator scope: each finding's evidence was matched to concrete source lines. No findings were rejected, reclassified, or merged — all six are technically accurate and apply to the current codebase. One minor factual inaccuracy is noted inline on INT-003 (does not change its verdict). Cross-phase references to SEC-001 (phase 04) and SRV-004 (phase 03) were confirmed consistent (no cross-phase conflicts).

## Runtime Verification (mandatory)

Inherited from the source audit. Re-confirmed where relevant:

- R1 (import): PASS — integration modules import cleanly.
- R2 lint/format/types: FAIL (pre-existing) — tracked CLI-003/CLI-004/CLI-005 in phase 01. Not in scope for this phase; no new integration-module violations introduced.
- R3 (tests): PASS — 325 passed. These findings are latent: the mock-based test bar (INT-002) gives false confidence and does not exercise real ffmpeg parsing.
- R4 (ffmpeg @file empirical): FAIL — confirms INT-001.
- R6 (yt-dlp opts empirical): FAIL — confirms INT-003 (ydl_opts keys exactly `[extract_flat, no_warnings, nocheckcertificate, quiet]`).
- R7 (browser lifecycle): FAIL — confirms INT-004.

## Findings

### INT-001: ffmpeg `-headers @file` syntax does not pass cookies to ffmpeg — documented "secret-safe cookie passing" is non-functional

> **Validation Note:**
> - **Action:** validated
> - **Type:** SPEC-DEVIATION, RUNTIME-ERROR
> - **Severity:** CRITICAL — confirmed and upheld
> - **Evidence check (all verified against source):**
>   - `src/vkdownloader/services/downloader.py:436-437`: `cmd` contains `"-headers", f"@{headers_file}"`. The file content is multi-line `User-Agent: ...\r\nReferer: ...\r\nCookie: ...` built at `downloader.py:421-427`. ffmpeg's `@file` is a generic response-file reader (whitespace/token split), not a value loader — confirmed the finding's mechanism analysis.
>   - `_temp_headers_file` at `downloader.py:98-117` docstring states the intent is to keep cookies out of the process argument list; the empirical ffmpeg output (`No trailing CRLF found in HTTP header`) matches the reported failure.
>   - `docs/01-tools/vkdownloader-overview.md:151` advertises `@file` cookie passing as functional — doc/code mismatch confirmed.
>   - The finding's preferred recommendation (use the existing Netscape cookie file via `-cookies`) is concrete and supported: `_create_temp_cookie_file` (`downloader.py:71-89`) and `_cookies_to_netscape` (`cookies.py:13`) already exist. Recommendation stands.
> - **Cross-reference:** layered on SEC-001 (phase 04, signed CDN tokens on cmdline) — consistent; if INT-001 is fixed by inlining `-headers`, it would re-expose SEC-001, reinforcing the recommendation to use the `cookies` file option instead.

**Verdict:** Validated. Code uses broken ffmpeg `@file` semantics; docs claim it works. Mandatory fix. Rollout ordering: INT-002 must change in lockstep (see below).

---

### INT-002: `test_download_with_ffmpeg_uses_header_file_syntax` provides false confidence by mocking subprocess and only checking @-prefix, never verifying ffmpeg reads headers from file

> **Validation Note:**
> - **Action:** validated
> - **Type:** SPEC-DEVIATION, RUNTIME-ERROR
> - **Severity:** HIGH — confirmed and upheld
> - **Evidence check (all verified):**
>   - `tests/test_hls_downloader.py:192-207`: `mock_process = AsyncMock()`, `returncode = 0`, `stderr.readline` returns `b""` — subprocess fully mocked, no real ffmpeg.
>   - `tests/test_hls_downloader.py:224-226`: asserts `headers_arg.startswith("@")` (prefix only) — confirmed.
>   - `tests/test_hls_downloader.py:228-232`: asserts `secret123`/`xyz789` absent from `captured_args` — true by construction (cookies written to file), proven nothing about ffmpeg reading them.
>   - This test is the sole coverage of the ffmpeg headers path (confirmed via the test file).
> - **Dependency:** INT-002 is a direct mirror of INT-001. The test currently asserts the *broken* behavior (`@` prefix). Any INT-001 fix that removes/reworks `@file` will break this test, so INT-001 and INT-002 must ship together.

**Verdict:** Validated. The test masks INT-001; mandatory fix (real-ffmpeg verification or removal). Required companion to INT-001.

---

### INT-003: yt-dlp library-mode extraction ignores Settings timeout/retry config and can hang indefinitely

> **Validation Note:**
> - **Action:** validated
> - **Type:** SPEC-DEVIATION, BEST-PRACTICE
> - **Severity:** MEDIUM — confirmed and upheld (core defect)
> - **Evidence check (all verified):**
>   - `src/vkdownloader/services/extractor.py:140-145`: `ydl_opts` contains exactly `quiet`, `no_warnings`, `extract_flat`, `nocheckcertificate` — omits `socket_timeout`, `retries`, `fragment_retries`, `throttled_rate`. Matches runtime R6 (`[extract_flat, no_warnings, nocheckcertificate, quiet]`).
>   - `src/vkdownloader/services/extractor.py:198`: `streams, title = await loop.run_in_executor(None, _sync_extract)` — no `asyncio.wait_for` wrapper. Confirmed.
>   - Contrast subprocess CLI path `downloader.py:294-307` maps `--socket-timeout`=`settings.download_timeout`, `-R`/`--fragment-retries`=`settings.max_retries`, `--throttled-rate`=`settings.throttled_rate`. Confirmed the config-to-integration gap.
>   - `config.py:45-90`: `max_retries` default 3, `download_timeout` default 300 (ge 30), `throttled_rate` default 10000. Confirmed.
> - **Minor inaccuracy (does not change verdict):** the finding states "yt-dlp's internal default socket timeout (when `socket_timeout` is unset) is 60 seconds". The actual yt-dlp default for `socket_timeout` is `None` (no socket timeout), so the hang risk is if anything *greater* than described. The core defect — Settings not propagated and no application-level `asyncio.wait_for` — stands and the recommendation (propagate Settings + wrap in `asyncio.wait_for(..., timeout=settings.download_timeout)`) is correct.

**Verdict:** Validated. Mandatory fix; isolated to the library-mode extraction path. No code conflict with existing tests.

---

### INT-004: Playwright browser and Playwright instance shutdown has no timeout — can hang indefinitely on teardown

> **Validation Note:**
> - **Action:** validated
> - **Type:** BEST-PRACTICE (operational reliability)
> - **Severity:** MEDIUM — confirmed and upheld
> - **Evidence check (all verified):**
>   - `src/vkdownloader/infrastructure/browser.py:61-66`: `__aexit__` calls `await self.browser.close()` then `await self.playwright.stop()` with no `asyncio.wait_for`, no `shutdown_event` check, and no `timeout` kwarg passed to `browser.close()`. Playwright's `Browser.close()` does accept a `timeout` kwarg (per upstream API). Confirmed.
>   - The established teardown pattern `cancel_subprocess` at `ffmpeg_utils.py:128-156` uses `asyncio.wait_for(process.wait(), timeout=5.0)` with SIGTERM>SIGKILL escalation — confirmed as the right comparator.
>   - `_wait_with_shutdown` (`downloader_throttle.py:310-340`) monitors the shared `shutdown_event`; `signal_handlers.py:29-33` sets it on Ctrl+C — confirmed the shared shutdown contract the browser path ignores.
>   - `extractor.py:211`: `async with BrowserManager(self.settings) as browser:` is the sole browser lifecycle boundary — confirmed.
> - **Rollout note:** recommendation must preserve the existing `finally` guarantee that `playwright.stop()` runs even if `browser.close()` raises; the timeout wrapper should be applied to `browser.close()` and `playwright.stop()` individually.

**Verdict:** Validated. Mandatory fix; small, backward-compatible addition (timeout + shutdown_event check) to browser teardown.

---

### INT-005: Misleading `ssl_verify_ignored_for_ffmpeg` warning contradicts actual SSL handling — ffmpeg DOES apply `-tls_verify 0`

> **Validation Note:**
> - **Action:** validated
> - **Type:** SPEC-DEVIATION (doc/log contradiction)
> - **Severity:** LOW — confirmed and upheld
> - **Evidence check (all verified):**
>   - `src/vkdownloader/services/downloader.py:1062-1069`: warning keyed `ssl_verify_ignored_for_ffmpeg` claims the `--no-ssl-verify` flag is not applied to the ffmpeg path. Confirmed.
>   - `src/vkdownloader/services/downloader.py:439-440`: `if not self.settings.ssl_verify: cmd.extend(["-tls_verify", "0"])` — ffmpeg's standard TLS-verification-disable flag, placed before `-i` (`downloader.py:441`). Confirmed functional; the warning is stale.
> - **Doc scope correction (minor):** the finding's doc-002 lists `docs/11-guides/configuration.md` as repeating the stale claim. `configuration.md:134-141` only says setting `ssl_verify=false` "Logs a security warning" — it does not repeat the "not applied to ffmpeg" falsehood. The only doc making the false claim is the runtime warning text itself and `vkdownloader-overview.md:151` (already covered under INT-001's docs-001). So docs-002's primary target is the warning text; the configuration.md reference is a secondary check with no actual mismatch. Recommendation stands (remove the warning).

**Verdict:** Validated. Advisory fix; trivial and safe (remove stale warning; the `-tls_verify 0` path already does the right thing).

---

### INT-006: Sequential download path broadly swallows programming errors as transient failures (divergent from parallel path)

> **Validation Note:**
> - **Action:** validated
> - **Type:** BEST-PRACTICE (error handling)
> - **Severity:** MEDIUM — confirmed and upheld
> - **Evidence check (all verified):**
>   - `src/vkdownloader/services/downloader_throttle.py:210-238`: `_retry_429_with_backoff` catches `asyncio.CancelledError` (correctly re-raised, `224-228`) then catches broad `Exception` at `229` and returns `None`, treating any error as a non-exception download failure. Confirmed.
>   - `src/vkdownloader/services/segment_downloader.py:255-286`: `_try_single_download_attempt` catches only `aiohttp.ClientError` at `283`. Confirmed (narrower granularity).
>   - `aiohttp` is imported in both modules (`downloader_throttle.py:9`, `segment_downloader.py:15`). Confirmed.
>   - `_download_segment_sequential` (`segment_downloader.py:166-170`) returns `False` on failure — confirmed it maps the `None` return into a failed/skipped segment, exactly as described.
> - **Behavior-change caution:** narrowing the catch to `aiohttp.ClientError` (+ optionally `asyncio.TimeoutError`) will let previously-swallowed programming errors surface as crashes. This is the *intended* outcome of the recommendation, but it is an observable behavior change — flag for rollout awareness. The `aiohttp.ClientError` does not cover `asyncio.TimeoutError` in all aiohttp versions, so both should be listed explicitly.
> - **Cross-reference:** links to SRV-004 (phase 03) for `api-reference.md:486-487` retry/backoff doc gap — confirmed consistent (same doc, different aspect); no conflict.

**Verdict:** Validated. Advisory fix; small but introduces a behavior change (surfaced errors previously swallowed). Rollout-safe if the change is intended.

---

## Cross-Phase & Cross-Finding Analysis

### Dependency chains

- **INT-001 - INT-002 (tight coupling):** INT-002's test asserts the broken `@` prefix that INT-001 proposes to remove/rework. Fixing INT-001 without updating INT-002 yields a failing build (test failure). These must be released together.
- **INT-001 - SEC-001 (phase 04, cross-phase):** SEC-001 covers signed CDN tokens remaining on the ffmpeg command line. INT-001 notes the fix is "layered on top of" SEC-001; if the chosen remediation inlines `-headers`, it reintroduces process-argument exposure. The recommendation correctly prefers the existing Netscape `cookies` file path (`_create_temp_cookie_file`/`_cookies_to_netscape`) to avoid this. Fix INT-001 via the `cookies` option to keep SEC-001 resolved.
- **INT-006 - SRV-004 (phase 03, cross-phase):** SRV-004 flags stale retry/backoff documentation in `api-reference.md`. INT-006 points at the same doc for parallel-mode retry claims. Separate root causes (error-handling taxonomy vs. doc accuracy) — keep separate findings, but doc authors fixing SRV-004 should account for INT-006's exception-handling scope.

### Conflicts detected

- None. No cross-phase conflicts: prior phase findings (phase 01 lint/format/type failures, SEC-001, SRV-004) are all consistent with the phase-05 runtime table and findings.

### Potential new findings (rollout safety)

- **INT-001/INT-002 rollout ordering:** If these two are split across releases, the test suite turns red. Enforce a single change-set. (Reported here; not a separate finding.)
- **INT-006 behavior change:** narrowing `except Exception` may convert silent segment-skip failures into hard crashes on latent bugs. Recommend a staged rollout: narrow catch + a dedicated fallback log so operators can opt into surfacing programming errors without an abrupt crash.

## Rollout Analysis

| Finding | Risk | Dependencies | Sequencing | Backward compatible? |
|--------|------|--------------|------------|----------------------|
| INT-001 | HIGH (touches active ffmpeg/AUTO fallback path) | INT-002 test must change simultaneously | Must ship with INT-002 | Mechanism changes; safe if cookies-file option adopted |
| INT-002 | LOW (test-only) | INT-001 | Must ship with INT-001 | N/A — test update |
| INT-003 | LOW (library extraction path only) | None | Independent | Yes (adds opts + timeout) |
| INT-004 | LOW (teardown path) | None | Independent | Yes (adds timeout) |
| INT-005 | TRIVIAL (remove stale warning) | None | Independent | Yes |
| INT-006 | MEDIUM (behavior change: errors surface) | None | Independent, advisory | Behavior change — surface errors previously swallowed |

Recommended order: INT-005 (trivial) > INT-004 (isolated) > INT-003 (isolated) > INT-001+INT-002 (together) > INT-006 (behavior change, last, with staged surfacing of errors).

## Execution Validation

- All referenced symbols and line ranges were confirmed present in the current source tree (downloader.py, extractor.py, browser.py, cookies.py, ffmpeg_utils.py, downloader_throttle.py, segment_downloader.py, config.py, test_hls_downloader.py, docs/01-tools/vkdownloader-overview.md, docs/11-guides/configuration.md).
- The phase-05 runtime verification table is corroborated by the source: R4 (ffmpeg @file) and R6 (ydl_opts keys) match the code exactly; R7 (browser __aexit__ lacks timeout) matches browser.py:61-66.
- No finding targets a stale or removed code path; no "fragile line-based anchor" concerns — all targets are stable functions/methods (`download_with_ffmpeg`, `_extract_with_ytdlp`, `BrowserManager.__aexit__`, `_retry_429_with_backoff`, `_try_single_download_attempt`).
- Ready for execution: YES for all six findings (with INT-001/INT-002 treated as a coupled unit).

## Warnings

- **Architectural risk (INT-001):** the ffmpeg download path is reachable from `DownloadMethod.AUTO` fallback (`downloader.py:1085-1110`). A regression here affects the auto-recovery path — ensure the fix preserves the `download_hls_with_resume` fallback on `result is None`.
- **Rollout risk (INT-001/INT-002):** splitting these two into separate releases breaks the build. Couple them in a single change-set.
- **Dependency risk (INT-003):** `run_in_executor` blocking the event loop is latent; the `asyncio.wait_for` wrapper must cancel the executor work, not just the await — verify yt-dlp cancellation behavior when the future is cancelled.
- **Documentation inconsistency (INT-005):** only `vkdownloader-overview.md:151` makes the false `@file` claim; `configuration.md` does not repeat it. Doc-002 scope is narrower than initially stated.
- **Behavior change (INT-006):** narrowed exception handling will surface previously-swallowed programming errors as crashes; stage this rollout.

## Required Fixes

1. **INT-001 (CRITICAL, Mandatory):** Replace `"-headers", f"@{headers_file}"` (`downloader.py:436-437`) and `_temp_headers_file` (`downloader.py:98-117`) with ffmpeg's `cookies` protocol option using the existing Netscape cookie file (`_create_temp_cookie_file`/`_cookies_to_netscape`). Update `docs/01-tools/vkdownloader-overview.md:151`.
2. **INT-002 (HIGH, Mandatory):** Update or replace `test_download_with_ffmpeg_uses_header_file_syntax` so it no longer asserts the broken `@` prefix; verify real header application via a local test HTTP server. Must accompany INT-001.
3. **INT-003 (MEDIUM, Mandatory):** Add `socket_timeout`, `retries`, `fragment_retries`, `throttled_rate` to `ydl_opts` (`extractor.py:140-145`); wrap `run_in_executor` (`extractor.py:198`) in `asyncio.wait_for(..., timeout=settings.download_timeout)`.

## Advisory Recommendations

1. **INT-004 (MEDIUM, Recommended):** Wrap `browser.close()`/`playwright.stop()` in `asyncio.wait_for` with a ~10s timeout and a `shutdown_event` check in `browser.py:61-66`; preserve the `finally` guarantee for `playwright.stop()`.
2. **INT-005 (LOW, Recommended):** Remove the stale `ssl_verify_ignored_for_ffmpeg` warning block (`downloader.py:1062-1069`).
3. **INT-006 (MEDIUM, Recommended):** Narrow `except Exception` in `_retry_429_with_backoff` (`downloader_throttle.py:229`) to `aiohttp.ClientError` (+ `asyncio.TimeoutError`, since `aiohttp.ClientError` does not cover `asyncio.TimeoutError` in all versions); align both paths on the same exception taxonomy.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 6 | INT-001, INT-002, INT-003, INT-004, INT-005, INT-006 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| — | — | — |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| — | — | — |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| — | — | — | — |

### One minor source inaccuracy

- **INT-003:** supporting text claims yt-dlp's unset `socket_timeout` defaults to 60s. Verified the actual default is `None` (no socket timeout), making the hang risk greater than stated. This does **not** change the finding's verdict, severity, or recommendation, which remain fully valid.
