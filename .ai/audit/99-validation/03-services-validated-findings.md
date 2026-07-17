# Phase 03 Validated Audit Findings — Service Layer & Business Logic

**Validator:** validator
**Source:** .ai/audit/03-services/findings.md
**Status:** complete
**Validated:** yes

---

## Runtime Verification Evidence

- **R1 — Imports:** `uv run python -c "import vkdownloader.services.*"` → `IMPORTS OK`. No import errors.
- **R2 — Lint / Types:** `uv run ruff check src/vkdownloader/services/` → `All checks passed!`; `uv run mypy src/vkdownloader/services/` → `Success: no issues found in 9 source files`.
- **R3 — Tests:** `uv run pytest tests/ -q` → `223 passed in 11.08s`. All service-layer tests pass.
- **R4 — Dead code search:** grep across `src/` for `_build_ffmpeg_cmd` confirms no production caller exists.

> Note: Runtime verification shows the service layer is syntactically, type-wise, and test-green healthy. The findings below address behavioral/correctness defects that the passing test suite does not currently cover (cookie format field ordering, dead code with security smell, and doc inconsistency).

---

## Findings

### SRV-001: Netscape cookie export swaps the `include-subdomains` and `secure` fields

| Field | Value |
|-------|-------|
| **ID** | SRV-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/cookies.py` |
| **Classification** | mandatory |

> **Validation Note:**
> - **Action:** reclassified
> - **Detail:** Original type RUNTIME-ERROR reclassified to SPEC-DEVIATION. The code violates the Netscape cookie file format specification (curl.se/docs/http-cookies.html). The format requires positional fields: domain, include-subdomains, path, secure, expires, name, value. The implementation has secure and include-subdomains transposed.
> - **See also:** —

**Description:** `_cookies_to_netscape` builds the Netscape cookie-file line for the `list[Cookie]` branch with the `secure` and `include-subdomains` columns transposed. The official Netscape format is `<domain>\t<include_subdomains TRUE/FALSE>\t<path>\t<secure TRUE/FALSE>\t<expiry>\t<name>\t<value>` (verified against curl.se documentation). The list branch writes:

```python
# cookies.py:45
lines.append(f"{domain}\t{secure}\t{path}\tFALSE\t{expires}\t{name}\t{value}")
```

- field 2 = `{secure}` (the cookie's secure flag) — but field 2 must be the **include-subdomains** flag.
- field 4 = hardcoded `FALSE` — but field 4 must be the cookie's **secure** flag.

By contrast the string branch (line 52) is correct: `.vkvideo.ru\tTRUE\t/\tFALSE\t0\t{name}\t{value}`. So the two code paths disagree.

**Evidence:**
- `cookies.py:35-46` — the list branch.
- `cookies.py:48-53` — the string branch, which orders fields correctly.
- Consumers: `_download_with_ytdlp` (`downloader.py:538,543`) writes this file to yt-dlp `cookiefile`.

**Impact:** For authenticated VK downloads (the `cookie_source=BROWSER` path), CDN auth cookies are frequently `Secure`. With the secure flag dropped, consumers may refuse to send them over HTTPS or mis-scope them, causing intermittent authentication failures. This is a silent correctness defect — tests pass because no test asserts the positional field order.

**Recommendation:** Reorder the list branch to match the string branch and the spec: `f"{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}"`. Add a unit test asserting the produced line splits into the correct positional fields (especially for a known `secure=True` cookie). Effort: trivial.

---

### SRV-002: ~~Dead production code `_build_ffmpeg_cmd` embeds cookies in plaintext command-line args~~ [REJECTED]

| Field | Value |
|-------|-------|
| **ID** | SRV-002 |
| **Severity** | MEDIUM |
| **Affected Modules** | `src/vkdownloader/services/downloader.py` |
| **Classification** | advisory |

> **Rejection reason:** The finding correctly identifies that `_build_ffmpeg_cmd` (lines 144-166) is called only by tests and contains insecure cookie handling. However, the claim that it is "still re-exported from `downloader.py:116`" is **incorrect** — `_build_ffmpeg_cmd` is **NOT** in `__all__`. The `__all__` list at that location contains `_build_ffmpeg_concat_command` (a different function). Additionally, `_build_ffmpeg_cmd` is a private method (underscore-prefixed), not a public export. The security risk is lower than stated because the method is not publicly exported. The core concern about dead code remains, but the finding presents inaccurate evidence.

---

### SRV-003: API reference documents `CookieSource.FILE` behavior that contradicts the code

| Field | Value |
|-------|-------|
| **ID** | SRV-003 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | `docs/01-tools/api-reference.md`, `src/vkdownloader/services/extractor.py` |
| **Classification** | advisory |

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Finding correctly identifies doc inconsistency. `extractor.py:123-126` raises `NotImplementedError` for `CookieSource.FILE`, but `api-reference.md:99` states "Placeholder returns streams without cookies" implying graceful return. The enum definition and overview doc correctly state FILE raises NotImplementedError, creating internal doc contradiction.
> - **See also:** —

**Description:** `VKVideoExtractor.extract_streams_with_cookies` raises `NotImplementedError` when `cookie_source == CookieSource.FILE` (extractor.py:123-126). However `docs/01-tools/api-reference.md:99` documents the FILE case as: "When `cookie_source=FILE`: Placeholder returns streams without cookies" — implying a graceful return, not an exception. The same doc's `CookieSource` table (api-reference.md:657) and `docs/01-tools/vkdownloader-overview.md:63` correctly state FILE raises `NotImplementedError`. So the repo's own docs contradict each other.

**Evidence:**
- `extractor.py:123-126` — `raise NotImplementedError("CookieSource.FILE is not implemented...")`.
- `api-reference.md:99` — "Placeholder returns streams without cookies".
- `api-reference.md:657` and `vkdownloader-overview.md:63` — correctly describe FILE as unimplemented / raises.

**Impact:** A developer reading the API reference will expect FILE to degrade gracefully and may wire it into a config expecting that behavior; instead the call raises and aborts the run. Low severity, but it is a concrete spec deviation and a trap for maintainers.

**Recommendation:** Align `api-reference.md:99` with the actual `NotImplementedError` behavior for `CookieSource.FILE`. Effort: trivial.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 1 | SRV-003 |
| Reclassified | 1 | SRV-001 |
| Merged | 0 | — |
| Rejected | 1 | SRV-002 |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| SRV-002 | Dead production code `_build_ffmpeg_cmd` embeds cookies in plaintext command-line args | Incorrect evidence: `_build_ffmpeg_cmd` is NOT in `__all__`. The method is private and not publicly exported, reducing security exposure. The dead code concern remains, but the finding overstates the evidence. |

### Merged Findings

None.

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| SRV-001 | RUNTIME-ERROR | SPEC-DEVIATION | The code violates the Netscape cookie file format specification with transposed positional fields. |