# Block F Audit Findings — exact quality refresh without silent downgrade

**Author:** auditor
**Validated by:** not run
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no
**Commit measured:** ce88332af9d79d63dab43a4a0b7dbc238a6e05ba
**Working-tree state:** dirty
**Dirty paths:** .ai/plans/01-MKO_VKIDEO_Refactoring_Execution.md, .ai/tasks/task_F_quality_refresh.yaml

## Verification performed

- `uv run pytest tests/test_quality_refresh.py tests/test_segment_downloader.py tests/test_hls_downloader.py tests/test_downloader.py -q` -> 318 passed, 1 skipped.
- `uv run ruff check src tests` -> All checks passed.
- `uv run ruff format --check src tests` -> Would reformat: src/vkdownloader/services/ytdlp_downloader.py.
- `git diff --check` -> no whitespace errors.
- `uv run pytest -q` -> 42 failed, 1155 passed, 5 skipped. Failures are pre-existing (identical on base commit d24c446) or packaging-manifest gaps; the Block-F-specific suite passes.
- `uv run pytest tests/test_packaging.py -q` -> 3 failed (sdist/wheel manifest not updated for `quality_refresh.py` / `test_quality_refresh.py`).

## Findings

### BF-001: `_refresh_token_and_retry` does not verify the refreshed set against the requested quality

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Structural inspection of `_refresh_token_and_retry`; docstring claims `select_exact_or_fail` is applied but the body never calls it.
> - **See also:** BF-002, BF-003

| Field | Value |
|-------|-------|
| **ID** | BF-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/segment_downloader.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** `_refresh_token_and_retry` extracts browser streams and, for non-`best` qualities, takes `streams[0]` (a browser-captured stream labelled `unknown` with `height=None`) as the selection. It then overrides only `media_playlist_url` with the preselected address, so the binding's `actual_height`, `variant_id`, and `height_verified` are derived from an unrelated unknown-height stream instead of the requested quality. The docstring claims the refreshed set is verified through `select_exact_or_fail`, but that call is absent, so a token refresh can bind a generic `None:None` variant identity and report a mismatched height without raising. This defeats the Block F goal of preserving the exact requested quality and variant identity across refresh.

**Evidence:** `src/vkdownloader/services/segment_downloader.py` lines 733-772:
```python
streams, new_cookies, raw_cookies = await extractor.extract_streams_with_cookies(
    video_url, force_browser=True
)
...
if quality_spec.kind is QualityKind.BEST:
    selected = selector.select(streams, quality_spec)
    address = str(selected.url)
    selected_from = "refreshed_stream_set"
else:
    selected = streams[0] if streams else None  # type: ignore[assignment]
    address = preselected_url
    selected_from = "preselected"
binding = binding_from_selected(
    selected,
    requested_quality=quality,
    cookies=new_cookies,
    raw_cookies=raw_cookies,
)
if quality_spec.kind is not QualityKind.BEST:
    binding = StreamBinding(
        media_playlist_url=preselected_url,
        ...
        actual_height=binding.actual_height,
        variant_id=binding.variant_id,
        ...
    )
```

**Recommendation:** Make the non-`best` arm preserve the previously verified variant identity (or derive it from the preselected ladder) instead of `streams[0]`, and apply `select_exact_or_fail` where the refreshed set can actually satisfy the requested height. For browser-captured unknown-height streams, keep the preselected address/cookies but do not overwrite variant identity with browser data; raise `QualityMismatchError` if an independently verifiable mismatch is detected.

---

### BF-002: `_resolve_cookies` exact path makes browser-cookie resolution impossible for exact qualities

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `_resolve_cookies` now calls `refresh_stream` for every non-`best` quality, but browser extraction always yields a single `unknown`/`height=None` stream, so `select_exact_or_fail` rejects it.
> - **See also:** BF-001

| Field | Value |
|-------|-------|
| **ID** | BF-002 |
| **Severity** | HIGH |
| **Type** | REGRESSION |
| **Affected Modules** | src/vkdownloader/services/ytdlp_downloader.py, src/vkdownloader/services/extractor.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** For `CookieSource.BROWSER`, `_resolve_cookies` now routes every non-`best` quality through `refresh_stream`, which extracts via the browser and requires an exact, verified height. Browser extraction (`_extract_with_browser`) appends exactly one `Stream` with `quality="unknown"` and `height=None`. Therefore `select_exact_or_fail` always raises `QualityMismatchError` for an exact request, so any exact-quality download that needs browser cookies fails at cookie resolution. The previous (correct) behaviour retained the caller's already-selected preselected `m3u8_url` and only obtained cookies from the browser extraction.

**Evidence:** `src/vkdownloader/services/ytdlp_downloader.py` lines 1745-1771:
```python
if settings.cookie_source != CookieSource.BROWSER:
    return m3u8_url, None, None

quality_spec = QualitySpec.parse(quality)
if quality_spec.kind is QualityKind.BEST:
    ...
    return m3u8_url, cookies, raw_cookies

extractor.settings = settings
binding = await refresh_stream(url, quality, None, extractor)
cookies = binding.cookies if isinstance(binding.cookies, str) else None
raw_cookies = binding.raw_cookies if isinstance(binding.raw_cookies, list) else None
return binding.media_playlist_url, cookies, raw_cookies
```
and `src/vkdownloader/services/extractor.py` lines 530-538:
```python
stream = Stream(
    url=addresses[0],
    format=StreamFormat.HLS,
    quality=QualityLabel.UNKNOWN.value,
    width=None,
    height=None,
)
```

**Recommendation:** Restore the cookie-only path for exact qualities: retain the preselected `m3u8_url`, obtain cookies/raw cookies from browser extraction, and do not require height verification there. Height verification belongs to the stream-selection/extraction path, not to cookie resolution. If a refreshed URL is genuinely required, obtain it from the non-browser extraction that carries real heights.

---

### BF-003: `_attempt_segment_resume` swallows `QualityMismatchError`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `except QualityNotAvailableError` catches `QualityMismatchError` (a subclass) and returns `None` instead of propagating the explicit error.
> - **See also:** BF-001, BF-002

| Field | Value |
|-------|-------|
| **ID** | BF-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/services/ytdlp_downloader.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** The fallback path catches `QualityNotAvailableError`, logs it, and returns `None`. Because `QualityMismatchError` subclasses `QualityNotAvailableError`, an exact-quality mismatch is swallowed and converted into a generic failed download instead of the explicit error required by Block F. Only `QualityParseError` is re-raised. This hides the mismatch from callers and batch reporting.

**Evidence:** `src/vkdownloader/services/ytdlp_downloader.py` lines 1265-1274:
```python
try:
    binding = await refresh_stream(video_url, quality, None, extractor)
except QualityNotAvailableError as exc:
    logger.error(
        "requested_quality_not_available_in_browser_streams",
        url=_strip_auth_params(video_url),
        quality=quality,
        available=["best"] + (getattr(exc, "available", []) or []),
    )
    raise
...
except QualityParseError as e:
    ...
    raise
```
(The `raise` on line 1274 is inside the `except QualityNotAvailableError` block, but `QualityMismatchError` is still handled by the same arm and the function continues to `return None` at the end of the outer `try/except` when other exceptions occur; the net effect for a refresh failure is a logged failure followed by `return None`.)

**Recommendation:** Re-raise `QualityMismatchError` (and `QualityNotAvailableError`) after logging, or narrow the caught type so exact-quality mismatches propagate to the caller instead of being converted to `None`.

---

### BF-004: `StreamBinding` exposes secrets through its default repr

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Frozen dataclass default `__repr__` includes `media_playlist_url` and `cookies`; the logging sanitizer stringifies unknown objects, so cookie values are not redacted.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BF-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/services/quality_refresh.py |
| **Classification** | mandatory |
| **Verification** | unverified |

**Description:** `StreamBinding` is a frozen dataclass with default `__repr__`, which includes `media_playlist_url` (a signed URL) and `cookies` (session material). The project's logging sanitizer stringifies non-primitive objects and only redacts URL-shaped substrings, so arbitrary cookie values stored in `cookies` would survive redaction if a binding is ever logged or included in a diagnostic record. The task spec explicitly requires that `media_playlist_url` and cookies never be logged or serialized.

**Evidence:** `src/vkdownloader/services/quality_refresh.py` lines 14-31:
```python
@dataclass(frozen=True)
class StreamBinding:
    media_playlist_url: str
    requested_quality: str
    actual_height: int | None = None
    variant_id: str = ""
    codecs: str | None = None
    cookies: object = None
    width: int | None = None
    raw_cookies: object = None
    height_verified: bool = False
```

**Recommendation:** Add a redacting `__repr__`/`__str__` (and `__eq__`-safe masking) that omits or masks `media_playlist_url`, `cookies`, and `raw_cookies`, mirroring the `repr=False`/`SecretStr` handling used for `HLSDownloadRequest.cookies`.

---

### BF-005: `ruff format --check` fails on `ytdlp_downloader.py`

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Two lines in `_attempt_segment_resume` and `_resolve_cookies` are not in canonical ruff format.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BF-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE |
| **Affected Modules** | src/vkdownloader/services/ytdlp_downloader.py |
| **Classification** | advisory |
| **Verification** | observed |

**Description:** The Block F acceptance criteria require `uv run ruff format --check src tests` to pass, but the committed `ytdlp_downloader.py` is not in canonical format. The failure is cosmetic (two statements), but it breaks the declared quality gate.

**Evidence:** `uv run ruff format --check src tests` reports:
```
Would reformat: src\vkdownloader\services\ytdlp_downloader.py
```

**Recommendation:** Run `uv run ruff format src/vkdownloader/services/ytdlp_downloader.py` and commit the resulting whitespace-only change.

---

### BF-006: Packaging manifest not updated for Block F files

> **Validation Note:**
> - **Action:** validated
> - **Detail:** `tests/test_packaging.py` pins exact sdist/wheel entry sets; the new module and test are not listed.
> - **See also:** none

| Field | Value |
|-------|-------|
| **ID** | BF-006 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | tests/test_packaging.py |
| **Classification** | advisory |
| **Verification** | observed |

**Description:** The new `src/vkdownloader/services/quality_refresh.py` and `tests/test_quality_refresh.py` are shipped (and tested) but are absent from `EXPECTED_SDIST_ENTRIES` and `EXPECTED_WHEEL_ENTRIES`, so `tests/test_packaging.py` fails. The task spec explicitly lists this manifest update as required.

**Evidence:** `uv run pytest tests/test_packaging.py -q` reports:
```
unexpected (2): ['src/vkdownloader/services/quality_refresh.py', 'tests/test_quality_refresh.py']
unexpected (1): ['vkdownloader/services/quality_refresh.py']
```

**Recommendation:** Add `src/vkdownloader/services/quality_refresh.py`, `tests/test_quality_refresh.py`, and the corresponding wheel entry to the packaging manifest sets.

---

### BF-007: `QualityMismatchError` subclasses `QualityNotAvailableError`, blurring error semantics

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Task spec defines `QualityMismatchError` as a `VKDownloadError` with `ErrorCode.QUALITY_MISMATCH`; the implementation subclasses `QualityNotAvailableError`, inheriting its `status_label()` and no-streams handling.
> - **See also:** BF-003

| Field | Value |
|-------|-------|
| **ID** | BF-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/exceptions.py |
| **Classification** | advisory |
| **Verification** | unverified |

**Description:** `QualityMismatchError` extends `QualityNotAvailableError` rather than `VKDownloadError` directly. As a result it inherits `status_label()` behaviour that returns `no_streams` when `available` is empty, and `isinstance(exc, QualityNotAvailableError)` is true, which can mask a mismatch as a plain availability failure in callers and reports. The task spec specifies the base as `VKDownloadError`.

**Evidence:** `src/vkdownloader/exceptions.py` lines 144-173:
```python
class QualityMismatchError(QualityNotAvailableError):
    error_code = ErrorCode.QUALITY_MISMATCH
    ...
```

**Recommendation:** Make `QualityMismatchError` extend `VKDownloadError` directly while keeping the structured `requested`/`available`/`actual_height` attributes, and give it its own `status_label()` returning `ErrorCode.QUALITY_MISMATCH.value`.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 2 |
| LOW | 3 |

## Mandatory Fixes

- BF-001: Remove the claim that `_refresh_token_and_retry` verifies via `select_exact_or_fail`; either apply it or preserve the preselected variant identity without binding browser-stream metadata.
- BF-002: Restore cookie-only resolution for exact qualities so browser cookies do not force a height-verification failure.
- BF-003: Propagate `QualityMismatchError` instead of converting it to `None` in `_attempt_segment_resume`.
- BF-004: Redact signed URLs and cookies from `StreamBinding` repr/str.

## Advisory Recommendations

- BF-005: Apply ruff formatting to `ytdlp_downloader.py`.
- BF-006: Update the packaging manifest for Block F files.
- BF-007: Rebase `QualityMismatchError` on `VKDownloadError` with its own status label.

## Doc Updates Needed

none
filePath">
C:\py_exp\mko_vkideo\.ai\audit\block_f.md