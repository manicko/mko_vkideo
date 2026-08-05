# Phase 02 Audit Findings — Configuration & Settings Models

**Executor:** auditor (poolside/laguna-m.1:free)
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### CFG-001: Empty string env var for `log_file`/`download_dir` resolves to CWD, not None

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | HIGH |
| **Type** | RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/config.py` (lines 112-117, 140-145), `src/vkdownloader/cli.py` (lines 461-464), `docs/01-tools/installation.md` (line 124) |
| **Classification** | mandatory |

**Description:** The `Settings` model declares `log_file: Path | None` and `download_dir: Path` with an `expand_tilde_paths` field validator (mode="after") that calls `v.expanduser().resolve()`. When an environment variable or `.env` value is an empty string (e.g., `VKDOWNLOADER_LOG_FILE=`), pydantic-settings coerces the empty string to `Path("")` (equivalent to `Path(".")`), which is not `None`. The validator's `if v is None` guard is bypassed, and `Path("").expanduser().resolve()` resolves to the current working directory. This means an empty `VKDOWNLOADER_LOG_FILE=` value — which the installation docs show as an example (installation.md:124) — produces a `log_file` pointing at a directory, not `None`.

When `setup_logging()` (config.py:196-216) is called with such a `log_file`, it passes the CWD path to `logging.FileHandler()`, which raises `IsADirectoryError` because a directory path cannot be opened as a file. This error is not caught by the `try/except OSError` guard around `mkdir()` (config.py:203-206) because `FileHandler` is created outside that try block. The exception propagates up and crashes the CLI.

**Evidence:**
```
# R2 — Config loading verification: empty string LOG_FILE
$ python -c "
import os
for key in list(os.environ):
    if key.startswith('VKDOWNLOADER_'):
        del os.environ[key]
os.environ['VKDOWNLOADER_LOG_FILE'] = ''
from vkdownloader.config import Settings
s = Settings()
print(f'log_file empty string: {s.log_file!r}')
print(f'log_file is None: {s.log_file is None}')
"
log_file empty string: WindowsPath('C:/py_exp/mko_vkideo')
log_file is None: False

# Empty download_dir has the same issue:
os.environ['VKDOWNLOADER_DOWNLOAD_DIR'] = ''
s = Settings()
print(f'download_dir empty string: {s.download_dir!r}')  # -> CWD path, not default
```

The installation docs (installation.md:124) show `VKDOWNLOADER_LOG_FILE=` as a copy-pasteable example, which would trigger this bug.

The `expand_tilde_paths` validator (config.py:112-117):
```python
@field_validator("download_dir", "log_file", mode="after")
@classmethod
def expand_tilde_paths(cls, v: Path | None) -> Path | None:
    if v is None:
        return v
    return v.expanduser().resolve()
```

`Path("")` is not `None`, so the guard is skipped. The same applies to `download_dir` when set to empty string.

**Recommendation:** Add a `mode="before"` validator or a `field_validator` that converts empty strings to `None` before pydantic coerces them to `Path`. Alternatively, override `field_validator` with a check for `Path` that is equal to `Path(".")` or empty. The simplest fix is to add a `mode="before"` validator on both `log_file` and `download_dir` that returns `None` when the input is an empty string.

**Effort:** trivial
**Priority:** mandatory — runtime crash when following documented configuration example.

---
### CFG-002: `.env` template file missing `headless` setting

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.env` (root, lines 1-31), `src/vkdownloader/config.py` (lines 29-32) |
| **Classification** | advisory |

**Description:** The `.env` file at the repository root serves as a local configuration template with all settings commented out. However, it does not include a `VKDOWNLOADER_HEADLESS` entry, despite `headless` being a valid `Settings` field (config.py:29-32, default `False`). The configuration guide (configuration.md:23, 49-53) and installation docs (installation.md:111) both document this setting. A user consulting the `.env` file as a reference will not discover the `headless` option.

**Evidence:**
```
# .env (root) — full content:
# Browser Automation Settings
# VKDOWNLOADER_USER_AGENT=...
# VKDOWNLOADER_TIMEZONE=Europe/Moscow
# VKDOWNLOADER_LOCALE=ru-RU
# VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT=5
# VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT=8
# Request Settings
# VKDOWNLOADER_MAX_RETRIES=3
# VKDOWNLOADER_DOWNLOAD_TIMEOUT=300
# VKDOWNLOADER_SSL_VERIFY=false
# Download Settings
# VKDOWNLOADER_DOWNLOAD_DIR=~/Downloads/vkdownloader
# VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS=4
# VKDOWNLOADER_THROTTLED_RATE=10000
# VKDOWNLOADER_HTTP_CHUNK_SIZE=10485760
# Cookie Source (none, browser, file)
# VKDOWNLOADER_COOKIE_SOURCE=none
# Logging Settings
# VKDOWNLOADER_LOG_LEVEL=INFO
# VKDOWNLOADER_LOG_FILE=~/vkdownloader.log
# (no VKDOWNLOADER_HEADLESS entry anywhere)
```

The `Settings.model_fields` includes `headless`:
```python
headless: bool = Field(
    default=False,
    description="Run browser in headless mode (no GUI)",
),
```

**Recommendation:** Add a commented-out `VKDOWNLOADER_HEADLESS` entry to the `.env` template, consistent with all other documented settings. If `.env` is truly only a personal local file (gitignored), consider creating a tracked `.env.example` template that includes all fields.

**Effort:** trivial
**Priority:** recommended

---

### CFG-003: API reference shows wrong `throttled_rate` default (100000 vs 10000)

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/api-reference.md` (line 852), `docs/01-tools/installation.md` (line 119), `src/vkdownloader/config.py` (line 86) |
| **Classification** | advisory |

**Description:** The API reference table (api-reference.md:852) lists the `throttled_rate` default as `100000`, but the actual default in the `Settings` model is `10000` (config.py:86). The configuration guide (configuration.md:34) and the `.env` template both correctly state `10000`. The installation docs (installation.md:119) also show `100000` in the example `.env`. This discrepancy means users reading the API reference or copying the installation example will use a value 10x higher than the intended default.

**Evidence:**
```
# Code (config.py:85-89):
throttled_rate: int = Field(
    default=10000,
    ge=1000,
    le=1000000,
    description="Minimum download rate in bytes/sec before throttling triggers re-extract. ...",
)

# API reference (api-reference.md:852):
| `throttled_rate` | `100000` | Minimum bytes/sec before throttling triggers re-extract |

# Installation docs (installation.md:119):
VKDOWNLOADER_THROTTLED_RATE=100000

# Configuration guide (configuration.md:34):
| `throttled_rate` | `VKDOWNLOADER_THROTTLED_RATE` | 10000 | ... |
```

Runtime verification confirms the actual default:
```
$ python -c "from vkdownloader.config import Settings; print(Settings().throttled_rate)"
10000
```

**Recommendation:** Update api-reference.md:852 to show the default as `10000`, and update installation.md:119 to `VKDOWNLOADER_THROTTLED_RATE=10000` to match the code.

**Effort:** trivial
**Priority:** recommended

---

### CFG-004: API reference missing `browser_pre_interaction_wait` and `browser_post_interaction_wait`

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/api-reference.md` (lines 840-856), `src/vkdownloader/config.py` (lines 57-68), `src/vkdownloader/services/extractor.py` (lines 220-222) |
| **Classification** | advisory |

**Description:** The API reference "Key Attributes" table for `Settings` (api-reference.md:840-856) omits the `browser_pre_interaction_wait` and `browser_post_interaction_wait` fields. These fields exist in the `Settings` model (config.py:57-68, defaults 5 and 8, range 1-30) and are actively consumed by `VKVideoExtractor._extract_with_browser` (extractor.py:220-222) to control wait times during browser-based stream extraction. The configuration guide (configuration.md:27-28) documents both fields. A developer consulting the API reference will not know these settings exist.

**Evidence:**
```python
# config.py:57-68 (exists in model)
browser_pre_interaction_wait: int = Field(
    default=5, ge=1, le=30,
    description="Seconds to wait before video interaction in browser extraction",
)
browser_post_interaction_wait: int = Field(
    default=8, ge=1, le=30,
    description="Seconds to wait after video interaction in browser extraction",
)

# extractor.py:220-222 (consumed by service)
await asyncio.sleep(self.settings.browser_pre_interaction_wait)
await self._simulate_video_interaction(page)
await asyncio.sleep(self.settings.browser_post_interaction_wait)

# api-reference.md table skips these two fields entirely (lines 843-856)
```

Runtime verification confirms both fields exist with correct defaults:
```
$ python -c "from vkdownloader.config import Settings; s=Settings(); print(s.browser_pre_interaction_wait, s.browser_post_interaction_wait)"
5 8
```

**Recommendation:** Add `browser_pre_interaction_wait` (default `5`, range 1-30) and `browser_post_interaction_wait` (default `8`, range 1-30) rows to the API reference settings table, with descriptions matching config.py.

**Effort:** trivial
**Priority:** recommended

---
### CFG-005: `.env` template lists `file` as valid `cookie_source` option but code rejects it

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `.env` (line 26), `src/vkdownloader/config.py` (lines 97-99, 126-138), `src/vkdownloader/models/enums.py` (line 49) |
| **Classification** | advisory |

**Description:** The `.env` template comment on line 26 reads `# Cookie Source (none, browser, file) - controls browser launch for cookies`, listing `file` as a valid option. However, the `Settings` model explicitly rejects `CookieSource.FILE` at construction time via the `validate_cookie_source` field validator (config.py:126-138), which raises a `ValueError` (surfacing as `ValidationError`) when the value is `FILE` or the string `"file"`. The `cookie_source` field description itself correctly says "file not implemented" (config.py:99), but the `.env` template comment contradicts this by presenting `file` as a valid choice.

**Evidence:**
```python
# enums.py:49 — FILE exists in enum
class CookieSource(StrEnum):
    NONE = "none"
    BROWSER = "browser"
    FILE = "file"

# config.py:126-138 — FILE is rejected at construction
@field_validator("cookie_source", mode="before")
@classmethod
def validate_cookie_source(cls, v: object) -> object:
    if isinstance(v, CookieSource) and v == CookieSource.FILE:
        raise ValueError("CookieSource.FILE is not implemented. Use 'none' or 'browser' instead.")
    if isinstance(v, str) and v.lower() == "file":
        raise ValueError("CookieSource.FILE is not implemented. Use 'none' or 'browser' instead.")
    return v

# .env line 26 — misleading comment:
# Cookie Source (none, browser, file) - controls browser launch for cookies
```

Runtime verification:
```
$ VKDOWNLOADER_COOKIE_SOURCE=file python -c "from vkdownloader.config import Settings; Settings()"
ValidationError: 1 validation error for Settings
cookie_source: CookieSource.FILE is not implemented
```

**Recommendation:** Update the `.env` template comment to `(none, browser)` only, removing `file` from the list of presented options. If `file` must remain listed for future reference, annotate it as "(not implemented)".

**Effort:** trivial
**Priority:** recommended

---

### CFG-006: `CookieSource.FILE` documentation is inconsistent across docs (NotImplementedError vs "future enhancement" vs ValidationError)

| Field | Value |
|-------|-------|
| **ID** | CFG-006 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/11-guides/configuration.md` (line 66), `docs/99-reference/cli-reference-clean.md` (line 198), `src/vkdownloader/config.py` (lines 126-138), `src/vkdownloader/services/extractor.py` (lines 129-132) |
| **Classification** | advisory |

**Description:** Three different descriptions of the `CookieSource.FILE` behavior exist in the documentation, none matching the actual code:

1. **configuration.md:66** says: "file — Not implemented; selecting it raises `NotImplementedError`."
2. **cli-reference-clean.md:198** says: "file — Load cookies from external file (future enhancement)."
3. **Actual code** (config.py:126-138): The `validate_cookie_source` field validator raises a `ValueError`, which pydantic wraps as a `ValidationError`. No `NotImplementedError` is ever raised for this case. The `NotImplementedError` at extractor.py:130-132 is **unreachable dead code** because the validator blocks `FILE` at model construction time (before any code path reaches the extractor).

The CLI option `--cookie-source file` is accepted by Typer (since `file` is a valid enum value), but the subsequent `Settings(cookie_source=CookieSource.FILE)` call raises `ValidationError`, which is caught and displayed as a configuration error. So the user sees a `ValidationError` with message "CookieSource.FILE is not implemented."

**Evidence:**
```python
# extractor.py:129-132 — UNREACHABLE: validator blocks FILE before this code runs
if self.settings.cookie_source == CookieSource.FILE:
    raise NotImplementedError(
        "CookieSource.FILE is not implemented. Use --cookie-source browser or none instead."
    )

# CLI reference (cli-reference-clean.md:198) — contradicts code:
#   file — Load cookies from external file (future enhancement)

# configuration.md:66 — contradicts code:
#   file — Not implemented; selecting it raises NotImplementedError

# Actual error raised:
ValidationError: CookieSource.FILE is not implemented. Use 'none' or 'browser' instead.
```

Runtime verification:
```
$ VKDOWNLOADER_COOKIE_SOURCE=file python -c "from vkdownloader.config import Settings; s=Settings(); print(s.cookie_source)"
ValidationError: 1 validation error for Settings
cookie_source: CookieSource.FILE is not implemented. Use 'none' or 'browser' instead.
```

**Recommendation:** Align all three documentation sources with the actual behavior: `CookieSource.FILE` is rejected at model construction with a `ValidationError` (not `NotImplementedError`). The cli-reference-clean.md should drop "future enhancement" wording or clearly state that `file` is rejected. The unreachable `NotImplementedError` in extractor.py:129-132 should be removed or retained only with a clarifying comment that it is intentionally unreachable (defensive) — but per the project's dead-code policy, it should be investigated.

**Effort:** small (doc fixes are trivial; dead code removal is trivial)
**Priority:** recommended

---
### CFG-007: Installation `.env` example is incomplete, has wrong `throttled_rate`, and contains empty `LOG_FILE`

| Field | Value |
|-------|-------|
| **ID** | CFG-007 |
| **Severity** | MEDIUM |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/01-tools/installation.md` (lines 106-125), `src/vkdownloader/config.py` (lines 29-145) |
| **Classification** | advisory |

**Description:** The installation guide's example `.env` file (installation.md:106-125) is incomplete and contains incorrect values compared to the `Settings` model:

1. **Missing fields:** `VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT`, `VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT`, and `VKDOWNLOADER_COOKIE_SOURCE` are all valid `Settings` fields but are absent from the example. While these use safe defaults, a user copying the example verbatim gets no guidance about these configurable options.
2. **Wrong value:** `VKDOWNLOADER_THROTTLED_RATE=100000` does not match the actual default of `10000` (config.py:86). This is the same discrepancy as CFG-003.
3. **Empty value triggers crash:** `VKDOWNLOADER_LOG_FILE=` (empty string) resolves to the CWD instead of `None`, as documented in CFG-001. This is the example users are told to copy.

**Evidence:**
```
# installation.md:106-125 (the copy-pasteable example):
# Browser Automation settings
VKDOWNLOADER_USER_AGENT=Mozilla/5.0 ...
VKDOWNLOADER_TIMEZONE=Europe/Moscow
VKDOWNLOADER_LOCALE=ru-RU
VKDOWNLOADER_HEADLESS=false
VKDOWNLOADER_MAX_RETRIES=3
VKDOWNLOADER_DOWNLOAD_TIMEOUT=300
VKDOWNLOADER_SSL_VERIFY=true

# Download settings
VKDOWNLOADER_DOWNLOAD_DIR=~/Downloads/vkdownloader
VKDOWNLOADER_MAX_CONCURRENT_DOWNLOADS=4
VKDOWNLOADER_THROTTLED_RATE=100000          # < wrong; actual default is 10000
VKDOWNLOADER_HTTP_CHUNK_SIZE=10485760

# Logging
VKDOWNLOADER_LOG_LEVEL=INFO
VKDOWNLOADER_LOG_FILE=                       # < empty string; triggers CWD bug (CFG-001)

# MISSING: VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT
# MISSING: VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT
# MISSING: VKDOWNLOADER_COOKIE_SOURCE
```

**Recommendation:**
- Fix `VKDOWNLOADER_THROTTLED_RATE=10000` to match the actual default.
- Change `VKDOWNLOADER_LOG_FILE=` to either omit the line or set a concrete path like `VKDOWNLOADER_LOG_FILE=~/vkdownloader.log`.
- Add the three missing fields (commented, since they use safe defaults).

**Effort:** trivial
**Priority:** recommended

---

### CFG-008: No tracked `.env.example` template for new users

| Field | Value |
|-------|-------|
| **ID** | CFG-008 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE |
| **Affected Modules** | `.gitignore` (line 28), `.env` (root, gitignored), `docs/01-tools/installation.md` (lines 102-125) |
| **Classification** | advisory |

**Description:** The project gitignores `.env` (line 28 of `.gitignore`), which is correct practice. However, there is no tracked `.env.example` (or `.env.template`) file that new users can copy from. The only configuration reference is in the installation docs, which has the issues described in CFG-007. New users who clone the repository have no `.env` file and must manually create one based on documentation.

In the standard Python configuration pattern, a tracked `.env.example` with all fields commented out is the canonical way to bootstrap configuration. The existing `.env` file (which IS complete except for the missing `headless` per CFG-002) is not distributed because it is gitignored.

**Evidence:**
```
# .gitignore line 28:
.env

# No .env.example exists in the repository:
$ ls .env.example .env.template .env.sample  # all not found
```

**Recommendation:** Create a tracked `.env.example` file containing all `Settings` fields with correct default values (commented out). This gives new users a single, copy-pasteable template that always matches the model. The existing `.env` file can then be deleted or reduced to user-specific overrides only.

**Effort:** small (create one file with all 16 fields, commented out)
**Priority:** recommended

---
### CFG-009: CLI reference shows `ssl_verify` default as `verify` instead of `true`

| Field | Value |
|-------|-------|
| **ID** | CFG-009 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `docs/99-reference/cli-reference-clean.md` (lines 68, 126), `src/vkdownloader/cli.py` (lines 406-410) |
| **Classification** | advisory |

**Description:** The CLI reference table lists the `--ssl-verify/--no-ssl-verify` option default as `verify` (cli-reference-clean.md:68 and :126). The actual default is `True` (cli.py:406-410: `ssl_verify: bool = typer.Option(True, "--ssl-verify/--no-ssl-verify", ...)`). The value `verify` is not a valid boolean representation — it appears to be a copy of the Typer internal field name rather than the actual default value. This could mislead users about the default behavior.

**Evidence:**
```python
# cli.py:406-410 — actual default is True:
ssl_verify: bool = typer.Option(
    True,
    "--ssl-verify/--no-ssl-verify",
    help="Verify SSL certificates for CDN connections",
),

# cli-reference-clean.md:68 — shows incorrect default:
| `--ssl-verify/--no-ssl-verify` | | bool | `verify` | Verify SSL certificates ... |

# cli-reference-clean.md:126 — same incorrect default:
| `--ssl-verify/--no-ssl-verify` | | bool | `verify` | Verify SSL certificates ... |
```

The configuration guide (configuration.md:31) and API reference (api-reference.md:849) both correctly show the default as `true`/`True`.

**Recommendation:** Change both instances in cli-reference-clean.md from `verify` to `true` to match the actual code default.

**Effort:** trivial
**Priority:** recommended

---

### CFG-010: `throttled_rate` field description is misleading ("triggers re-extract")

| Field | Value |
|-------|-------|
| **ID** | CFG-010 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/config.py` (line 89), `docs/01-tools/api-reference.md` (line 852), `docs/11-guides/configuration.md` (line 34) |
| **Classification** | advisory |

**Description:** The `throttled_rate` field description says "Minimum download rate in bytes/sec before throttling triggers re-extract." This is misleading in two ways:

1. **Wrong mechanism name:** yt-dlp's `throttledratelimit` option causes the download to **abort** when the rate drops below the threshold — it does not "throttle." "Throttling" implies rate-limiting, but the actual behavior is download abortion.
2. **Wrong trigger attribution:** The description says "triggers re-extract," implying the throttling itself directly causes re-extraction. In reality, yt-dlp aborts the download, and the application's separate retry logic in `download_with_ytdlp_with_resume_fallback` (downloader.py:455-491) catches the failure and re-extracts with a fresh token. The re-extraction is not triggered by throttling — it is triggered by the download failure.

The second sentence of the description ("yt-dlp will abort below this threshold") is accurate, but the first sentence creates a misleading impression.

**Evidence:**
```python
# config.py:85-90 — misleading first sentence:
throttled_rate: int = Field(
    default=10000,
    ge=1000,
    le=1000000,
    description="Minimum download rate in bytes/sec before throttling triggers re-extract. "
    "Default is conservative (10KB/s) to avoid aborting legitimate slow downloads; "
    "yt-dlp will abort below this threshold.",
)

# yt-dlp uses throttledratelimit (downloader.py:174):
"throttledratelimit": settings.throttled_rate,

# Re-extraction is handled separately in downloader.py:455-491
# (download_with_ytdlp_with_resume_fallback retry loop), not by yt-dlp's throttledratelimit
```

**Recommendation:** Rewrite the description to accurately describe the behavior: "Minimum download rate in bytes/sec. If yt-dlp's download rate falls below this threshold, yt-dlp aborts the download; the application then retries with a fresh token re-extract. Default is 10000 (10KB/s)."

**Effort:** trivial
**Priority:** recommended

---

## Runtime Verification Summary

| Step | Status | Details |
|------|--------|---------|
| R1 — Model instantiation | Pass | Defaults applied correctly; `CookieSource.FILE` rejected with `ValidationError`; unknown kwargs rejected with `extra='forbid'`; `log_level` normalized case-insensitively. |
| R2 — Config loading | Pass (with bug) | Env vars load correctly (e.g., `VKDOWNLOADER_COOKIE_SOURCE=browser` > `CookieSource.BROWSER`). **Bug found:** empty string `VKDOWNLOADER_LOG_FILE=` resolves to CWD instead of `None` (see CFG-001). |
| R3 — Linter | Pass | `ruff check` — all checks passed. `mypy` — success, no issues found in 23 source files. |
| R4 — Test suite | Pass | All 248 tests pass (15 config tests, 248 total). No config-related test failures. |

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 6 |
| LOW | 3 |
| **Total** | **10** |

## Mandatory Fixes

- **CFG-001** (HIGH, RUNTIME-ERROR): Add a `mode="before"` validator to `log_file` and `download_dir` that converts empty strings to `None` before pydantic coerces them to `Path`. This prevents a runtime crash when `VKDOWNLOADER_LOG_FILE=` (empty string) is set — a pattern shown in the installation docs example.

## Advisory Recommendations

- **CFG-002** (MEDIUM, SPEC-DEVIATION): Add `VKDOWNLOADER_HEADLESS` entry to the `.env` template file.
- **CFG-003** (MEDIUM, SPEC-DEVIATION): Correct `throttled_rate` default from `100000` to `10000` in api-reference.md and installation.md.
- **CFG-004** (MEDIUM, SPEC-DEVIATION): Add `browser_pre_interaction_wait` and `browser_post_interaction_wait` rows to the API reference settings table.
- **CFG-005** (MEDIUM, SPEC-DEVIATION): Remove `file` from the `.env` template `cookie_source` comment, since it is rejected at construction.
- **CFG-006** (MEDIUM, SPEC-DEVIATION): Align `CookieSource.FILE` documentation across configuration.md, cli-reference-clean.md, and code. Document that `ValidationError` is raised (not `NotImplementedError`). Investigate the unreachable `NotImplementedError` in extractor.py:129-132.
- **CFG-007** (MEDIUM, SPEC-DEVIATION): Fix the installation `.env` example: correct `throttled_rate` value, fix empty `LOG_FILE`, add missing fields.
- **CFG-008** (LOW, BEST-PRACTICE): Create a tracked `.env.example` file with all settings fields for new-user onboarding.
- **CFG-009** (LOW, SPEC-DEVIATION): Change `verify` to `true` for `ssl_verify` default in cli-reference-clean.md:68,126.
- **CFG-010** (LOW, SPEC-DEVIATION): Rewrite `throttled_rate` description in config.py:89 to accurately describe yt-dlp abort behavior instead of "triggers re-extract".

## Doc Updates Needed

- **CFG-002**: Add `VKDOWNLOADER_HEADLESS` to `.env` template.
- **CFG-003**: Update `throttled_rate` default in api-reference.md:852 and installation.md:119.
- **CFG-004**: Add missing fields to api-reference.md settings table.
- **CFG-005**: Remove `file` from `.env` template comment.
- **CFG-006**: Align `CookieSource.FILE` behavior documentation across configuration.md:66 and cli-reference-clean.md:198.
- **CFG-007**: Fix installation.md `.env` example.
- **CFG-009**: Change `verify` to `true` for `ssl_verify` default in cli-reference-clean.md:68,126.
- **CFG-010**: Rewrite `throttled_rate` description in config.py:89 and propagate to api-reference.md:852 and configuration.md:34.

## Config-to-Consumer Flow Verification

All 16 `Settings` fields are consumed by at least one consumer:

| Field | Consumers |
|-------|-----------|
| `headless` | `infrastructure/browser.py:36` |
| `user_agent` | `infrastructure/browser.py:79`, `services/downloader.py:312,603`, `services/segment_downloader.py:810` |
| `timezone` | `infrastructure/browser.py:81` |
| `locale` | `infrastructure/browser.py:80` |
| `max_retries` | `services/downloader.py:181-182`, `services/segment_downloader.py:729,751`, `cli.py:198 (override)` |
| `download_timeout` | `services/downloader.py:180`, `services/segment_downloader.py:444,729,752` |
| `browser_pre_interaction_wait` | `services/extractor.py:220` |
| `browser_post_interaction_wait` | `services/extractor.py:222` |
| `ssl_verify` | `services/downloader.py:171,627-628,799`, `services/extractor.py:149`, `services/segment_downloader.py:480-487` |
| `download_dir` | `cli.py:130` |
| `max_concurrent_downloads` | `cli.py:272,593`, `services/downloader.py:173`, `services/segment_downloader.py:740,748` |
| `throttled_rate` | `services/downloader.py:174` |
| `http_chunk_size` | `services/downloader.py:175` |
| `cookie_source` | `services/downloader.py:687,831`, `services/extractor.py:121,129`, `services/segment_downloader.py:381` |
| `log_level` | `config.py:210` (`setup_logging`) |
| `log_file` | `config.py:199-214` (`setup_logging`) |

No unused config fields were found. No consumer parameter that should come from config is hardcoded instead.


