# Phase 03 Audit Findings — Service Layer & Business Logic

**Executor:** audit-executor
**Template:** .kilo/commands/audit/phases/03-audit-services.md
**Status:** complete
**Validated:** no

---

## Runtime Verification Evidence

- **R1 — Imports:** `uv run python -c "import vkdownloader.services.*"` → `IMPORTS OK`. No import errors.
- **R2 — Lint / Types:** `uv run ruff check src/vkdownloader/services/` → `All checks passed!`; `uv run mypy src/vkdownloader/services/` → `Success: no issues found in 9 source files`; `uv run ruff format --check` → `9 files already formatted`.
- **R3 — Tests:** `uv run pytest tests/ -q` → `223 passed in 11.08s`. All service-layer tests pass.
- **R4 — Dead code search:** grep across `src/` for each private helper. See SRV-002 (confirmed dead production code) and SRV-001/003 correctness/doc deviations.

> Note: Runtime verification shows the service layer is syntactically, type-wise, and test-green healthy. The findings below are behavioral/correctness defects that the passing test suite does not cover (cookie format, dead code with a security smell, and an internally-inconsistent doc).

---

## Findings

### SRV-001: Netscape cookie export swaps the `include-subdomains` and `secure` fields

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR (correctness) |
| **Affected Modules** | `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |

**Description:** `_cookies_to_netscape` builds the Netscape cookie-file line for the `list[Cookie]` branch with the `secure` and `include-subdomains` columns transposed. The official Netscape/curl format is `<domain>\t<include_subdomains TRUE/FALSE>\t<path>\t<secure TRUE/FALSE>\t<expiry>\t<name>\t<value>` (verified against everything.curl.dev / cyotek docs). The list branch writes:

```python
# cookies.py:45
lines.append(f"{domain}\t{secure}\t{path}\tFALSE\t{expires}\t{name}\t{value}")
```

- field 2 = `{secure}` (the cookie's secure flag) — but field 2 must be the **include-subdomains** flag.
- field 4 = hardcoded `FALSE` — but field 4 must be the cookie's **secure** flag.

By contrast the string branch (line 52) is correct: `.vkvideo.ru\tTRUE\t/\tFALSE\t0\t{name}\t{value}`. So the two code paths disagree.

**Evidence:**
- `cookies.py:35-46` — the list branch.
- `cookies.py:48-53` — the string branch, which orders fields correctly and exposes the defect by contrast.
- Consumers: `_download_with_ytdlp` (`downloader.py:538,543`) writes this file to `yt_dlp` `cookiefile`. yt-dlp/curl parse the file positionally, so a `secure` cookie is parsed with `secure=FALSE` and `include-subdomains=<secure-value>`.

**Impact:** For authenticated VK downloads (the `cookie_source=BROWSER` path), the CDN auth cookies are frequently `Secure`. With the secure flag dropped, consumers may refuse to send them over HTTPS or mis-scope them, causing intermittent authentication failures that are hard to diagnose. This is a silent correctness defect — tests pass because no test asserts the positional field order.

**Recommendation:** Reorder the list branch to match the string branch and the spec: `f"{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}"`. Add a unit test asserting the produced line splits into the correct positional fields (especially for a known `secure=True` cookie). Effort: trivial. Priority: recommended (mandatory correctness).

---

### SRV-002: Dead production code `_build_ffmpeg_cmd` embeds cookies in plaintext command-line args

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE (dead code / security smell) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

**Description:** `HLSDownloader._build_ffmpeg_cmd` (downloader.py:144-166) is never called anywhere in production code. The only callers are tests (`tests/test_hls_downloader.py:56,73,88,101,110,120`). The live ffmpeg path (`download_with_ffmpeg`, downloader.py:204-218) deliberately builds the command inline and routes cookies through a temp `@file` via `_temp_headers_file` specifically to keep secrets out of the process argument list (see the docstring at downloader.py:60-71: "This prevents cookies from appearing in process argument lists").

The dead `_build_ffmpeg_cmd` does the opposite — it inlines the cookie value directly into the argv string:

```python
# downloader.py:148
cookie_part = f"Cookie: {cookies}\r\n" if cookies else ""
```

and it is still re-exported from `downloader.py:116` (`"_build_ffmpeg_cmd"` in `__all__`). This is a maintenance hazard: the secure pattern (temp-file cookies) and the insecure pattern (inline cookies) now coexist, and a future refactor that switches `download_with_ffmpeg` to call `_build_ffmpeg_cmd` would silently reintroduce credential leakage into `ps`/process listings.

**Evidence:**
- `downloader.py:144-166` — definition, inline `cookies` in argv.
- `downloader.py:204-218` — the actually-used inline builder that correctly uses `@{headers_file}`.
- grep: only `tests/test_hls_downloader.py` calls `_build_ffmpeg_cmd(`; no `src/` caller.
- `downloader.py:116` — still listed in `__all__`.

**Impact:** No live bug today (dead code), but it preserves an insecure pattern next to the secure one and risks a future regression that exposes auth cookies in process arguments. It also misleads readers about which command-building path is authoritative.

**Recommendation:** Either delete `_build_ffmpeg_cmd` and its `__all__` entry (tests that only exercise it should be removed or repurposed to assert the secure inline path), or, if it is meant as the canonical builder, make `download_with_ffmpeg` actually call it and have it use the `@file` temp-file mechanism. Do not keep both. Effort: small. Priority: recommended (advisory).

---

### SRV-003: API reference documents `CookieSource.FILE` behavior that contradicts the code

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION (doc inconsistency) |
| **Affected Modules** | `docs/01-tools/api-reference.md`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

**Description:** `VKVideoExtractor.extract_streams_with_cookies` raises `NotImplementedError` when `cookie_source == CookieSource.FILE` (extractor.py:123-126). However `docs/01-tools/api-reference.md:99` documents the FILE case as: "When `cookie_source=FILE`: Placeholder returns streams without cookies" — i.e. it implies a graceful return, not an exception. The same doc's `CookieSource` table (api-reference.md:657) and `docs/01-tools/vkdownloader-overview.md:63` correctly state FILE raises `NotImplementedError`. So the repo's own docs contradict each other.

**Evidence:**
- `extractor.py:123-126` — `raise NotImplementedError("CookieSource.FILE is not implemented...")`.
- `api-reference.md:99` — "Placeholder returns streams without cookies".
- `api-reference.md:657` and `vkdownloader-overview.md:63` — correctly describe FILE as unimplemented / raises.

**Impact:** A developer reading the API reference will expect FILE to degrade gracefully (returns streams, no cookies) and may wire it into a config expecting that behavior; instead the call raises and aborts the run. Low severity (FILE is not a default and the overview is correct), but it is a concrete spec deviation and a trap for maintainers.

**Recommendation:** Pick one behavior and align the docs+code. If FILE is intentionally unimplemented, change `api-reference.md:99` to state it raises `NotImplementedError` (consistent with the table and overview). If graceful no-cookie fallback is desired, implement it in `extractor.py`. Effort: trivial. Priority: recommended (advisory).

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 1 |

## Mandatory Fixes

- **SRV-001** — Fix the transposed `include-subdomains`/`secure` fields in the Netscape cookie export (`cookies.py:45`). Correctness defect affecting authenticated downloads.

## Advisory Recommendations

- **SRV-002** — Remove or reconcile the dead, insecure `_build_ffmpeg_cmd` (`downloader.py:144-166`) so the plaintext-cookie pattern cannot be reintroduced. (advisory)
- **SRV-003** — Align `api-reference.md:99` with the actual `NotImplementedError` behavior for `CookieSource.FILE`. (advisory / doc)

## Doc Updates Needed

- **SRV-003** — `docs/01-tools/api-reference.md:99` must be updated to match the code (raises `NotImplementedError`) or the code must implement the documented graceful fallback.


