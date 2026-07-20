# Phase 02 Audit Findings — Configuration & Settings Models

**Executor:** auditor → validator
**Template:** .kilo/commands/audit/phases/02-audit-config.md
**Status:** complete
**Validated:** yes

---

## Findings

### CFG-001: cookie_source=FILE silently no-ops instead of raising (primary download flow)

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | src/vkdownloader/config.py, src/vkdownloader/services/extractor.py, src/vkdownloader/cli.py, src/vkdownloader/services/downloader.py, src/vkdownloader/services/segment_downloader.py |
| **Classification** | mandatory |

**Description:** The CookieSource.FILE enum value and configuration.md document that selecting file raises NotImplementedError. Use none or browser instead. In reality the NotImplementedError is only raised inside VKVideoExtractor.extract_streams_with_cookies(). The primary download/batch CLI flow never calls that method for stream acquisition.

- cli.py download and batch call extractor.extract_streams(url), which ignores cookie_source entirely
- downloader.py _resolve_cookies only invokes extract_streams_with_cookies when cookie_source == BROWSER
- segment_downloader.py _refresh_token short-circuits when cookie_source != BROWSER

Consequently cookie_source=file is accepted and behaves identically to none.

**Evidence:** Runtime: Settings(cookie_source='file') returns cookie_source=file with no error.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Code inspection confirms extract_streams never checks cookie_source. The NotImplementedError only exists in extract_streams_with_cookies which is only called when cookie_source == BROWSER or force_browser=True. Runtime verification confirms Settings(cookie_source='file') is accepted.
> - **See also:** —

**Recommendation:** Enforce FILE rejection at the config/CLI boundary or update documentation to reflect the current silent no-op behavior.

---

### CFG-002: extra=forbid does not protect the real config source (env / .env)

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py, tests/test_config.py |
| **Classification** | advisory |

**Description:** Settings.model_config sets extra: forbid, implying unknown configuration keys are rejected. In pydantic-settings v2, extra=forbid only applies to explicit model-construction kwargs, not environment variables or .env.

**Evidence:** Runtime: VKDOWNLOADER_BOGUS env var is silently ignored when Settings() is instantiated.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Runtime verification confirms unknown env vars are silently ignored. Pydantic-settings v2 behavior confirmed.
> - **See also:** —

**Recommendation:** Validate environment-derived config explicitly or add tests for unknown env var handling.

---

### CFG-003: Repo .env template references non-existent setting (VKDOWNLOADER_DOWNLOAD_METHOD)

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | .env, docs/11-guides/configuration.md, src/vkdownloader/config.py |
| **Classification** | advisory |

**Description:** The .env template line 25 contains VKDOWNLOADER_DOWNLOAD_METHOD=auto, but no download_method field exists in Settings. DownloadMethod is only used as a CLI option.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Settings has no download_method field. The .env template is inconsistent with code and docs.
> - **See also:** CFG-002 (silently ignored due to extra=forbid limitation)

**Recommendation:** Remove the stale VKDOWNLOADER_DOWNLOAD_METHOD line from .env.

---

### CFG-004: log_file/download_dir resolved at construction; missing parent dir yields unhelpful error

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py |
| **Classification** | advisory |

**Description:** When log_file points to a path whose parent directory does not exist, setup_logging() raises FileNotFoundError with no actionable message.

> **Validation Note:**
> - **Action:** validated
> - **Detail:** Runtime verification confirms FileNotFoundError is raised when log_file parent directory does not exist. setup_logging does not create parent directories.
> - **See also:** —

**Recommendation:** Create parent directory in setup_logging before FileHandler instantiation.

---

### CFG-005: .env is loaded relative to CWD only

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py |
| **Classification** | advisory |

**Description:** model_config uses env_file: .env which pydantic-settings resolves relative to CWD, not the package install location.

**Recommendation:** Document .env location requirement or support explicit config location.

---

### CFG-006: throttled_rate default may abort legitimate slow downloads

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | src/vkdownloader/config.py, src/vkdownloader/services/downloader.py |
| **Classification** | advisory |

**Description:** throttled_rate (default 100000 bytes/sec) maps to yt-dlp throttledratelimit which aborts downloads below threshold.

**Recommendation:** Raise default or document the trade-off.

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 6 | — |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

No findings rejected.

### Merged Findings

No findings merged.

### Reclassified Findings

No findings reclassified.

---

## Rollout Analysis

Findings are independent and can be addressed in any order. CFG-001 is high priority due to silent correctness loss on authentication.
