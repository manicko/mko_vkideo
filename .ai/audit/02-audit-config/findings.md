---
name: 02-audit-config-findings
description: Configuration & Settings Models audit findings for mko_vkideo
agent: auditor
alwaysApply: false
---

# Phase 02 Audit Findings — Configuration & Settings Models

**Executor:** auditor
**Template:** .ai/audit/templates/audit-findings.md
**Status:** complete
**Validated:** no

---

## Findings

### CFG-001: `throttled_rate` documented default (100000) does not match code (10000)

| Field | Value |
|-------|-------|
| **ID** | CFG-001 |
| **Severity** | LOW |
| **Type** | SPEC-DEVIATION / DOC-UPDATE |
| **Affected Modules** | `src/vkdownloader/config.py`, `docs/11-guides/configuration.md`, `.env` |
| **Classification** | advisory |

**Description:** The settings model default for `throttled_rate` is `10000` (10 KB/s, a deliberately conservative value per the in-code description), but `docs/11-guides/configuration.md` line 32 documents the default as `100000` (10x higher). The repository `.env` template line 21 uses `10000`, matching the code, not the docs. Tests (`tests/test_config.py:117-119`) assert `10000`, confirming code is the source of truth.

**Evidence:**
- `config.py:83-88` — `throttled_rate: int = Field(default=10000, ...)`
- `configuration.md:32` — `| throttled_rate | VKDOWNLOADER_THROTTLED_RATE | 100000 | ...`
- `test_config.py:119` — `assert test_settings.throttled_rate == 10000`

**Recommendation:** Update `configuration.md` line 32 to show the correct default (`10000`). The code choice (conservative 10 KB/s) is intentional and should be preserved; fix the documentation, not the code. Effort: trivial. Priority: recommended.

---

### CFG-002: `browser_pre_interaction_wait` and `browser_post_interaction_wait` missing from config docs

| Field | Value |
|-------|-------|
| **ID** | CFG-002 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE / SPEC-DEVIATION |
| **Affected Modules** | `docs/11-guides/configuration.md`, `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** The `Settings` model defines two browser-stealth timing fields, `browser_pre_interaction_wait` (default 5) and `browser_post_interaction_wait` (default 8), which are actively consumed by the extractor (`extractor.py:212` and `extractor.py:214`). Neither field appears anywhere in `configuration.md` (neither in the settings table nor in any section). A user reading the configuration guide cannot discover or tune these values, and there is no `VKDOWNLOADER_*` env var mapping documented for them.

**Evidence:**
- `config.py:55-66` — both fields defined with `VKDOWNLOADER_*` env mapping via `env_prefix`.
- `extractor.py:212` — `await asyncio.sleep(self.settings.browser_pre_interaction_wait)`
- `extractor.py:214` — `await asyncio.sleep(self.settings.browser_post_interaction_wait)`
- `configuration.md` — full text search shows no occurrence of `browser_pre_interaction_wait` or `browser_post_interaction_wait`.

**Recommendation:** Add both fields to the `configuration.md` settings reference table (with env var names `VKDOWNLOADER_BROWSER_PRE_INTERACTION_WAIT` / `VKDOWNLOADER_BROWSER_POST_INTERACTION_WAIT`, defaults 5/8, and description of their role in browser extraction). Effort: trivial. Priority: recommended.

---

### CFG-003: Invalid `.env`/environment value raises an uncaught traceback to the end user

| Field | Value |
|-------|-------|
| **ID** | CFG-003 |
| **Severity** | MEDIUM |
| **Type** | RUNTIME-ERROR / BEST-PRACTICE |
| **Affected Modules** | `src/vkdownloader/cli.py`, `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** `Settings` is constructed at the top of each CLI command (`cli.py:392` in `download`, `cli.py:527` in `batch_download`) with no exception handling. When a `.env` file or `VKDOWNLOADER_*` environment variable contains a value that fails Pydantic validation (e.g., a non-integer for an `int` field, or an out-of-range value), `pydantic.ValidationError` propagates uncaught and the user sees a raw Python traceback instead of a clear, actionable configuration error. This is a robustness/correctness gap in configuration handling.

**Evidence (runtime, R2):**
```
$env:VKDOWNLOADER_MAX_RETRIES='notanint'; uv run python -c "from vkdownloader.config import Settings; s=Settings()"
...
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
max_retries
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='notanint', input_type=str]
  ...
EXIT=1
```
The same unhandled `ValidationError` is what the end user receives when launching `vkdownloader download ...` with a malformed `.env`, because `cli.py:392`/`cli.py:527` call `Settings(...)` directly.

**Recommendation:** Wrap `Settings(...)` construction in the CLI entry points and catch `ValidationError`, emitting a concise, user-facing message (which field, expected type/range, and how to fix the `.env`) before `typer.Exit(code=1)`. Effort: small. Priority: recommended.

---

### CFG-004: Misspelled environment variables are silently ignored (inconsistent with `extra='forbid'`)

| Field | Value |
|-------|-------|
| **ID** | CFG-004 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE / RUNTIME-ERROR |
| **Affected Modules** | `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** The model sets `extra='forbid'` (`config.py:141`), which correctly rejects unknown *kwargs* (covered by `test_config.py:48-68`). However, `pydantic-settings` v2 does **not** apply `extra='forbid'` to environment variables — a misspelled `VKDOWNLOADER_*` variable is silently dropped and the default value is used, producing no warning. This gives a false sense of safety from the `extra='forbid'` setting and can cause confusing "my config isn't taking effect" behavior (e.g., a user sets `VKDOWNLOADER_MAXRETRIES` instead of `VKDOWNLOADER_MAX_RETRIES` and silently gets the default). The inline docstring at `config.py:18-20` even acknowledges this limitation.

**Evidence (runtime, R2):**
```
$env:VKDOWNLOADER_MAXRETRIES='9'; uv run python -c "from vkdownloader.config import Settings; print(Settings().max_retries)"
max_retries effective = 3      # typo'd variable silently ignored; default retained
EXIT=0
```

**Recommendation:** Add a lightweight guard that scans `os.environ` for any `VKDOWNLOADER_`-prefixed keys not present in the model's field names (normalized) and emits a warning log before/at `Settings()` construction. Alternatively document this caveat prominently in `configuration.md`. Effort: small. Priority: recommended.

---

### CFG-005: `max_retries` documentation says "during batch processing" but applies to single downloads too

| Field | Value |
|-------|-------|
| **ID** | CFG-005 |
| **Severity** | LOW |
| **Type** | DOC-UPDATE / SPEC-DEVIATION |
| **Affected Modules** | `docs/11-guides/configuration.md`, `src/vkdownloader/config.py` |
| **Classification** | advisory |

**Description:** `configuration.md:27` describes `max_retries` as "Maximum retry attempts for failed segment downloads during batch processing (1-10)". In reality the field is consumed by both single (`download`) and batch (`batch`) paths — it maps to yt-dlp's `retries`/`fragment_retries` (`downloader.py:179-180`) and the segment downloader's `max_retries` (`segment_downloader.py:734,757`), all of which run on the single-download code path as well. The "during batch processing" qualifier is misleading and may cause users to believe the setting has no effect on single downloads.

**Evidence:**
- `configuration.md:27` — "Maximum retry attempts for failed segment downloads during batch processing (1-10)"
- `config.py:43-48` — field docstring: "Maximum retry attempts for failed requests"
- `downloader.py:179-180` and `segment_downloader.py:734,757` — `max_retries` used outside any batch-only guard.

**Recommendation:** Reword the `configuration.md` description to state the retries apply to both single and batch downloads (and to both network and fragment retries). Effort: trivial. Priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 2 |
| LOW | 3 |

## Mandatory Fixes

(None — no security, data-loss, or correctness defects requiring mandatory fixes were found.)

## Advisory Recommendations

- **CFG-001** — Fix `throttled_rate` default in `configuration.md` (100000 → 10000). Doc-only.
- **CFG-002** — Document `browser_pre/post_interaction_wait` in the config reference.
- **CFG-003** — Catch `ValidationError` at CLI `Settings()` construction; surface a clean config error.
- **CFG-004** — Warn on unknown `VKDOWNLOADER_*` env vars (typo guard).
- **CFG-005** — Correct `max_retries` description (applies to single + batch downloads).

## Doc Updates Needed

- **CFG-001** — `docs/11-guides/configuration.md` line 32 (throttled_rate default).
- **CFG-002** — `docs/11-guides/configuration.md` settings table (add 2 browser wait fields).
- **CFG-005** — `docs/11-guides/configuration.md` line 27 (max_retries scope).
- **CFG-004** (optional) — Document the `extra='forbid'` env-var caveat in `configuration.md`.

---

## Audit Notes (discovery & verification)

- **Config model:** single flat `Settings(BaseSettings)` model in `config.py` (16 fields). No sub-models; all sections (browser, download, logging) are flat fields.
- **Config-to-consumer trace:** every one of the 16 fields is consumed by at least one consumer (`browser.py`, `extractor.py`, `downloader.py`, `segment_downloader.py`, `cli.py`, `config.py`/`setup_logging`). No unused or dead config fields found.
- **Validation/Runtime:** `uv run ruff check src/vkdownloader/config.py` → pass; `uv run mypy src/vkdownloader/config.py` → pass (only a benign "unused section" note for test overrides); `uv run pytest tests/test_config.py` → 12 passed.
- **Init/Template service:** the project exposes no `init`/`scaffold` command (CLI has only `download` and `batch`). Dimension 3 (Init/Template Service) is not applicable; omitted.
- **Secrets:** `.env` (`configuration.md` example and repo template) contains only commented placeholder values; `.gitignore` excludes `.env`. No real secrets present. Dimension 4 leakage check: pass (no finding).
- **Path resolution:** `download_dir`/`log_file` are normalized via `expand_tilde_paths` (`config.py:110-115`); `download_dir` default resolves to `~/Downloads/vkdownloader`. Config is read from CWD-relative `.env` (documented limitation in `config.py:22-23`).
