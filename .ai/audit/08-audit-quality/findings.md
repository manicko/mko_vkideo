# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** audit-executor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Runtime Verification (R1–R4)

| Step | Command | Result |
|------|---------|--------|
| R1 — ruff check | `uv run ruff check src/` | All checks passed |
| R1 — ruff format | `uv run ruff format --check src/` | 23 files already formatted |
| R1 — mypy | `uv run mypy src/` | Success: no issues found (strict mode) |
| R2 — pytest | `uv run pytest -q` | 201 passed, 4 warnings (unawaited coroutine warnings in tests — covered by phase 07) |
| R3 — dead code | grep for unused symbols / dead methods | See QLT-004, QLT-007 |
| R4 — security search | grep `print(`, `except:`, hardcoded secrets | No `print()`, no bare `except:`, no hardcoded secrets found |

Lint, format, type-check, and tests all pass. The findings below are real problems discovered through manual code review, dead-code analysis, and configuration-vs-behavior tracing.

---

## Findings

### QLT-001: `max_retries` setting is never wired into the segment download retry path

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/config.py`, `src/vkdownloader/cli.py` |
| **Classification** | mandatory |

**Description:** The `max_retries` setting (documented in `docs/11-guides/configuration.md:95` as *"Maximum retry attempts for failed segment downloads … the system will automatically retry up to this number of attempts"*) has no effect on actual segment downloads. In the default parallel path (`max_concurrent_downloads > 1`), a segment that receives a 429/5xx is logged and returned as `False` with **no retry at all** (`segment_downloader.py:84-97`). In the sequential path, `_retry_429_with_backoff` is invoked **without** `max_retries` (`segment_downloader.py:68`), so it always uses its hardcoded default of `3` regardless of configuration. yt-dlp is configured with a hardcoded `"retries": 10` (`downloader.py:380`), also ignoring the setting. `settings.max_retries` is only ever read by the unused `HttpClient` module (`http_client.py:94`), so the value is dead in the live code path.

**Evidence:**
- `segment_downloader.py:68` → `content = await _retry_429_with_backoff(session, segment_url, headers, segment_index)` (no `max_retries` arg; default `3`).
- `downloader.py:380` → `"retries": 10` (hardcoded, not `settings.max_retries`).
- `downloader_throttle.py:147` → `max_retries: int = 3` is the only source of the retry count.
- `docs/11-guides/configuration.md:95` claims automatic segment retry up to `max_retries`.

**Recommendation:**
- **What:** Pass `settings.max_retries` into `_retry_429_with_backoff` (and into the parallel-path retry, if one is added), and replace the hardcoded `"retries": 10` in yt-dlp options with `settings.max_retries`.
- **Why:** Today the documented knob is inert; operators who raise `max_retries` to survive flaky CDNs get no behavior change, while the retry/backoff "anti-bot" feature is misrepresented.
- **Effort:** small
- **Priority:** recommended (mandatory — correctness/spec deviation)

---

### QLT-002: `datetime.utcnow()` is deprecated and will break on a future Python (project supports >=3.12)

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `_parse_retry_after` uses `datetime.utcnow()` (`downloader_throttle.py:266`). `datetime.utcnow()` was deprecated in Python 3.12 (the project's minimum supported version) and is scheduled for removal (sources indicate Python 3.14). Because `requires-python = ">=3.12"`, running on 3.13+ already emits `DeprecationWarning`, and on the removal version it raises `AttributeError`, breaking `Retry-After` parsing for 429/503 responses.

**Evidence:**
- `downloader_throttle.py:266` → `now = datetime.utcnow()`
- `pyproject.toml:6` → `requires-python = ">=3.12"`
- Confirmed via websearch: `datetime.utcnow()` deprecated in 3.12, removal scheduled (AttributeError on removal; `-W error` CI fails today).

**Recommendation:**
- **What:** Replace with `datetime.now(timezone.utc)` (or `datetime.now(UTC)` on 3.11+). Import `from datetime import datetime, timezone`.
- **Why:** Keeps the tool runnable on current and future Python; avoids noisy deprecation warnings and a future hard crash in the rate-limit handling path.
- **Effort:** trivial
- **Priority:** recommended

---

### QLT-003: Declared dependencies `ffmpeg-python` and `tqdm` are never imported

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `pyproject.toml` |
| **Classification** | advisory |

**Description:** `pyproject.toml:24,27` declares `ffmpeg-python>=0.2.0` and `tqdm>=4.68.4` as runtime dependencies, but neither is imported anywhere in `src/` or `tests/`. `ffmpeg` is invoked by shelling out to the `ffmpeg` binary via `asyncio.create_subprocess_exec` (`ffmpeg_utils.py`, `downloader.py`), not via the `ffmpeg` Python library. No progress bar uses `tqdm`. Shipping unused dependencies inflates install size and implies capabilities (programmatic ffmpeg control, progress bars) that do not exist.

**Evidence:**
- grep for `import ffmpeg` / `from ffmpeg` / `import tqdm` / `tqdm(` across `src/` and `tests/` → zero matches.
- `pyproject.toml:24` → `"ffmpeg-python>=0.2.0"`, `pyproject.toml:27` → `"tqdm>=4.68.4"`.
- `ffmpeg_utils.py` / `downloader.py` spawn the `ffmpeg` executable directly.

**Recommendation:**
- **What:** Remove `ffmpeg-python` and `tqdm` from `[project].dependencies` (move to dev-only if used by tooling), or actually integrate them if the capability is intended.
- **Why:** Reduces supply-chain surface and install footprint, and removes misleading signals about what the tool does.
- **Effort:** trivial
- **Priority:** recommended

---

### QLT-004: Documented/exported `HttpClient` and `AdaptiveThrottle` subsystems are never used by the download flow

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/infrastructure/http_client.py`, `src/vkdownloader/infrastructure/adaptive_throttle.py`, `src/vkdownloader/infrastructure/__init__.py` |
| **Classification** | advisory |

**Description:** `HttpClient` (a full aiohttp wrapper with retry, timeout, and file-download logic) and `AdaptiveThrottle` (a dynamic RPM rate limiter) are exported from `infrastructure/__init__.py`, documented in `docs/01-tools/vkdownloader-overview.md:43,46` and `api-reference.md:747`, and even covered by `tests/test_http_client.py`. However, **no source module imports or calls them**. The real download path uses raw `aiohttp` directly inside `segment_downloader.py` and delegates to `yt-dlp`/`ffmpeg`. The result is duplicated HTTP logic, a maintained-but-dead subsystem with its own test suite, and documentation that describes components absent from the runtime path. Per the dead-code policy these are documented, so the recommendation is to *investigate their purpose* — either wire them in (so there is a single HTTP abstraction) or remove them and update the docs.

**Evidence:**
- `infrastructure/__init__.py:3,5` export `AdaptiveThrottle` and `HttpClient`.
- grep for `HttpClient(` / `AdaptiveThrottle(` outside their own definitions and tests → no source usages.
- `segment_downloader.py` opens its own `aiohttp.ClientSession` (`segment_downloader.py:230`) and `downloader.py` runs yt-dlp directly.

**Recommendation:**
- **What:** Decide whether `HttpClient`/`AdaptiveThrottle` are the intended single HTTP/rate-limit abstraction or vestigial. If intended, route `segment_downloader`/`extractor` through them. If not, delete the modules + tests and update `overview.md`/`api-reference.md`.
- **Why:** Eliminates two parallel implementations of HTTP/retry logic, reduces maintenance and confusion, and makes documentation truthful.
- **Effort:** medium
- **Priority:** recommended

---

### QLT-005: `validate_output_path` rejects any path containing `..`, blocking legitimate output directories

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/utils/security.py`, `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader.py`, `src/vkdownloader/services/segment_downloader.py` |
| **Classification** | mandatory |

**Description:** `validate_output_path` raises `DownloadError("Path traversal detected …")` whenever the raw path string contains the substring `".."` (`security.py:43-44`). This is both **over-restrictive** (a legitimate directory such as `-o ../downloads` or a folder named `my..data` is wrongly rejected) and **redundant** (the subsequent `path.resolve()` already canonicalizes `..` segments). It also provides weaker protection than intended: `resolve()` does not defeat symlink-based escapes, yet the explicit check gives a false sense of safety. The net effect is a real correctness bug — common, valid usage (`-o ../<dir>`) fails — while the security guarantee remains incomplete.

**Evidence:**
- `security.py:42-44` → `if ".." in path_str: raise DownloadError(...)`
- `security.py:47` → `resolved = path.resolve()` (already canonicalizes `..`)
- `cli.py:120` and `downloader.py:287` call `validate_output_path(output, warning=False)` with user-supplied paths.

**Recommendation:**
- **What:** Remove the `".." in path_str` substring check. Resolve first, then (if a sandbox is desired) verify the result is within an allowed root via `resolved.relative_to(allowed_root)`; otherwise trust `resolve()`.
- **Why:** Restores legitimate `-o ../…` usage and replaces a brittle substring heuristic with correct canonicalization-based validation.
- **Effort:** small
- **Priority:** recommended (mandatory — correctness)

---

### QLT-006: CLI reaches into `ProgressManager._state` private attribute and claims a false GIL-atomic thread-safety guarantee

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/services/downloader_throttle.py` |
| **Classification** | advisory |

**Description:** `cli.py:43` mutates the private `_state` dict directly: `_progress_manager._state[url_index] = (downloaded, total)`. `ProgressManager` already exposes a public, lock-protected `update()` method, but the CLI bypasses it. The accompanying comment (`cli.py:41-42` and `downloader_throttle.py:84-91`) asserts *"Direct tuple assignment to `_state[url_index]` is GIL-atomic in CPython, providing safe fire-and-forget semantics."* This is incorrect: dict item assignment (`dict.__setitem__`) is **not** guaranteed atomic under the GIL (only a subset of individual bytecode ops are). The code is currently safe only by accident — callbacks run in the same single-threaded event loop, not because of any GIL guarantee. A future maintainer who makes progress callbacks truly concurrent (threads/processes) would introduce data races based on this misleading claim.

**Evidence:**
- `cli.py:43` → `_progress_manager._state[url_index] = (downloaded, total)`
- `cli.py:41-42` and `downloader_throttle.py:87-88` → "GIL-atomic in CPython" comments.
- `downloader_throttle.py:97-106` → a public `update()` method exists but is never used by the callback.

**Recommendation:**
- **What:** Replace the direct `_state` write with `_progress_manager.update(url_index, downloaded, total)` and delete the incorrect "GIL-atomic" comments (explain the real single-event-loop reason for safety).
- **Why:** Enforces encapsulation, removes a false thread-safety claim that could cause real races later, and consolidates on one mutation path.
- **Effort:** trivial
- **Priority:** recommended

---

### QLT-007: Unused exported DTO models, dead methods, and unused `config.py` symbols

| Field | Value |
|-------|-------|
| **ID** | QLT-007 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/dtos.py`, `src/vkdownloader/models/video.py`, `src/vkdownloader/models/__init__.py`, `src/vkdownloader/services/downloader_throttle.py`, `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** Several exported/public symbols are defined and documented (per the dead-code policy, documented symbols are future-proofing rather than deletable dead code), but are never referenced by any source module:
- DTO models `DownloadRequest`, `DownloadResult`, `DownloadProgress`, `StreamWithCookies` — exported in `models/__init__.py` and documented in `api-reference.md`, but only `HLSDownloadRequest` is actually used.
- `ProgressManager.get_progress()` (`downloader_throttle.py:129`) — never called (only `get_formatted_progress`/`update`/`clear` are used).
- `URLBackoffCoordinator.is_paused()` (`downloader_throttle.py:51`) — never called (only `pause`/`wait_if_paused` are used).
- `config.py:12` module-level `logger: structlog.BoundLogger = structlog.get_logger(__name__)` — never used within `config.py`.
- `config.py:131` global `settings = Settings()` — never imported/referenced anywhere; every module instead instantiates its own `Settings()`.

These inflate the surface area and mislead readers about what is live API vs. planned API.

**Evidence:**
- grep for `DownloadRequest`/`DownloadResult`/`DownloadProgress`/`StreamWithCookies` in `src/` → only definitions and `models/__init__.py` re-exports (no call sites).
- grep for `.get_progress(` and `is_paused(` → only their own definitions.
- grep for `config.settings` / `import settings` → no references; global `settings = Settings()` at `config.py:131` is orphaned.

**Recommendation:**
- **What:** Investigate whether these are intended public/future API. If yes, document them explicitly as "not yet wired in"; if no, remove the unused models/methods and the orphaned `config.py` `logger`/`settings` symbols to shrink the public surface.
- **Why:** Reduces confusion about live vs. planned API and keeps the module's public surface honest.
- **Effort:** small
- **Priority:** recommended

---

### QLT-008: `HLSDownloadRequest` `__init__` is monkeypatched to lazily resolve forward references

| Field | Value |
|-------|-------|
| **ID** | QLT-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/models/dtos.py` |
| **Classification** | advisory |

**Description:** `dtos.py` patches the class at import time: `HLSDownloadRequest.__init__ = _lazy_init` (`dtos.py:85`), where `_lazy_init` rebinds `Settings`/`VKVideoExtractor`/`URLBackoffCoordinator` onto the module namespace and calls `model_rebuild()` on first instantiation. This is a fragile pattern that obscures normal Pydantic model construction, relies on module-global mutable state (`_model_rebuilt`), and risks subtle init-order bugs if the model is ever subclassed or built before its dependencies are importable. The same forward-reference problem is normally solved with `TYPE_CHECKING` imports plus a single explicit `HLSDownloadRequest.model_rebuild()` at the end of the module.

**Evidence:**
- `dtos.py:59-85` → `_ensure_model_rebuilt`, `_original_init`, `_lazy_init`, and `HLSDownloadRequest.__init__ = _lazy_init` with `# type: ignore[attr-defined]` / `# type: ignore[method-assign]`.
- The forward-referenced types are runtime-only (`Settings`, `VKVideoExtractor`, `URLBackoffCoordinator`); `from __future__ import annotations` already defers annotations.

**Recommendation:**
- **What:** Replace the `__init__` monkeypatch with `TYPE_CHECKING` imports for the three types and a single `HLSDownloadRequest.model_rebuild()` call after all imports resolve (or use `model_config = ConfigDict(defer_build=True)`).
- **Why:** Removes runtime patching/mutable global state, makes model construction predictable, and is the idiomatic Pydantic forward-reference approach.
- **Effort:** small
- **Priority:** recommended

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 6 |
| LOW | 2 |

## Mandatory Fixes

- **QLT-001** — `max_retries` config is inert in the real download/retry path (spec deviation).
- **QLT-005** — `validate_output_path` blocks legitimate `..` output paths (correctness bug).

## Advisory Recommendations

- **QLT-002** — Replace deprecated `datetime.utcnow()` (future `AttributeError`).
- **QLT-003** — Remove unused `ffmpeg-python` / `tqdm` dependencies.
- **QLT-004** — Investigate/integrate or remove the unused `HttpClient`/`AdaptiveThrottle` subsystems.
- **QLT-006** — Stop poking `ProgressManager._state`; remove false GIL-atomic claim.
- **QLT-007** — Trim unused/exported-but-dead models, methods, and `config.py` symbols.
- **QLT-008** — Replace `__init__` monkeypatch with idiomatic forward-reference handling.

## Doc Updates Needed

- **QLT-001** — `docs/11-guides/configuration.md:95` overstates `max_retries` behavior; correct or implement.
- **QLT-004** — `docs/01-tools/vkdownloader-overview.md` / `api-reference.md` describe `HttpClient`/`AdaptiveThrottle` as active components; mark as unused or remove.
- **QLT-007** — `api-reference.md` documents `DownloadRequest`, `DownloadResult`, `DownloadProgress`, `StreamWithCookies` as live models; clarify intended status.
