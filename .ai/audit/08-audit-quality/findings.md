# Phase 08 Audit Findings — Code Quality, Security & Maintainability

**Executor:** auditor (Senior architecture auditor)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/08-audit-quality.md
**Status:** complete
**Validated:** no
**Problems-only:** yes (passing checks are omitted per phase output mode)

**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).
Source: `src/vkdownloader/` (`cli.py`, `config.py`, `exceptions.py`, `models/`, `infrastructure/`,
`services/`, `utils/`, `__main__.py`, `stealth.min.js`). Tests: `tests/`.

Issues already filed in phases 01-07 are cited by ID and not re-filed here; the runtime
verification table restates them only as evidence that the gates they affect are still red.

---

## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 — Lint | `uv run ruff check src/ tests/` | FAIL (1 error, pre-existing) | `tests/test_correlation.py:28` F841 unused `full` — filed CLI-003 (phase 01) / TST-001 (phase 07). `src/vkdownloader/` alone: PASS. |
| R1 — Lint (whole repo) | `uv run ruff check .` | FAIL (459 errors, escalating) | Dominated by unparseable stray scripts in `.temp/` (QLT-005). |
| R1 — Types | `uv run mypy src/vkdownloader` | FAIL (1 error, pre-existing) | `utils/correlation.py:55` unused `type: ignore[no-any-return]` — filed CLI-004 (phase 01). 26 source files checked. |
| R1 — Format | `uv run ruff format --check src/ tests/` | FAIL (4 files, pre-existing) | `services/downloader.py`, `tests/test_cli.py`, `tests/test_hls_downloader.py`, `tests/test_security.py` — filed CLI-005 (phase 01). |
| R2 — Tests | `uv run pytest` | PASS | 325 passed in 12.94s; no failures, no skips. |
| R3 — Dead code | `pyflakes` on `src/` + `tests/` | 2 findings (1 new) | `signal_handlers.py:63` redundant `global` (QLT-003, new); `test_correlation.py:28` unused `full` (CLI-003/TST-001). `_write_netscape_cookie_file` dead code already filed SRV-002 (phase 03). Verified live callers exist for `_await_first_and_cancel_others`, `_temp_headers_file`, `_parse_ytdlp_progress`, `_echo_ytdlp_line`. |
| R4 — Security | grep secrets / `print(` / bare `except:` | PASS on forbidden patterns | No hardcoded secrets in app code (matches only in `.temp/secret_scan.py` scanner and a `test_hls_downloader.py` test fixture `access_token=mytoken`). No `print(` in `src/` or `tests/`. No bare `except:`. 6 `except Exception` sites found (not bare) — 2 surface new code-quality angles (QLT-002, QLT-004). No credentials logged directly. |

> The R1 lint/format/type failures are pre-existing and already tracked under phase-01
> findings CLI-003/CLI-004/CLI-005. They are restated here only as runtime evidence, not
> re-filed. No *new* lint/type/format defects were introduced in `src/vkdownloader/`.

---

## Findings

### QLT-001: `Any` type usage in production code violates the project "no `any`" rule

| Field | Value |
|-------|-------|
| **ID** | QLT-001 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE, SPEC-DEVIATION |
| **Affected Modules** | `src/vkdownloader/services/concurrency.py:5,15`; `src/vkdownloader/services/downloader.py:14,60,121-122` |
| **Classification** | advisory |

**Description:** Project rule #9 mandates "Avoid `any` completely" and this phase's "No `Any` types"
check forbids it. Yet `Any` is imported and used in two production modules:

- `services/concurrency.py:5`, `line 15`: `SemaphoreLike.__aenter__(self) -> Any` — the protocol's
  context-manager return is widened to `Any`, defeating the protocol's type contract.
- `services/downloader.py:14`, `line 60`: `_semaphore_context(semaphore: SemaphoreLike | None) -> Any`
  returns either a `SemaphoreLike` or a `nullcontext()`.
- `services/downloader.py:121-122`: `*tasks: asyncio.Task[Any])` and
  `-> tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]`.

mypy (strict) passes only because it permits `Any` by default; the project's own rule does not.

**Evidence:**
- `src/vkdownloader/services/concurrency.py:5` — `from typing import Any, Protocol`
- `src/vkdownloader/services/concurrency.py:15` — `async def __aenter__(self) -> Any: ...`
- `src/vkdownloader/services/downloader.py:14` — `from typing import TYPE_CHECKING, Any`
- `src/vkdownloader/services/downloader.py:60` — `def _semaphore_context(semaphore: SemaphoreLike | None) -> Any:`
- `src/vkdownloader/services/downloader.py:121-122` — `*tasks: asyncio.Task[Any]` / return `tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]`
- Grep `ruff check --select F401` on `src/`: no unused `Any` import (it is used), so this is a
  type-quality, not dead-import, issue.

**Recommendation:** Narrow the two easily-fixable sites: type `SemaphoreLike.__aenter__` to
`object` (or a dedicated return protocol), and `_semaphore_context` to
`SemaphoreLike | AbstractContextManager[object]`. The `asyncio.Task[Any]` cases `121-122` are the asyncio API convention and harder to remove without
`asyncio.Task[Coroutine[Any, Any, object]]` verbosity; treat them as a secondary follow-up. Effort: small; priority: recommended.

---

### QLT-002: No-op `except Exception: raise` in download_hls_with_resume

| Field | Value |
|-------|-------|
| **ID** | QLT-002 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE (maintainability) |
| **Affected Modules** | `src/vkdownloader/services/segment_downloader.py:885-886` |
| **Classification** | advisory |

**Description:** `download_hls_with_resume` ends with:

```python
    except Exception:
        raise
    finally:
        if not success:
            _log_preserve_segments(segments_dir)
```

The `except Exception: raise` block catches and immediately re-raises, performing no work. It is
functionally dead — the `try/finally` already runs the preserve-on-failure cleanup for both the
normal and exceptional paths. A reader encountering this clause reasonably concludes that special
error handling exists here, when none does; it is misleading and should be removed (the bare
`try/finally` expresses the intent). None of the prior phase findings (01-07) call this out.

**Evidence:**
- `src/vkdownloader/services/segment_downloader.py:885-886` — `except Exception:` / `raise`.
- pyflakes does not flag it (it is syntactically valid), so it survives the lint gate; it is a
  readability/maintenance smell, not a defect the tooling catches.

**Recommendation:** Delete the no-op `except Exception: raise` block; keep the `try/finally`.
If future special handling is intended, add it explicitly rather than a pass-through catch.
Effort: trivial; priority: recommended.

---

### QLT-003: Redundant `global` declaration flagged by pyflakes

| Field | Value |
|-------|-------|
| **ID** | QLT-003 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE (correctness/hygiene) |
| **Affected Modules** | `src/vkdownloader/services/signal_handlers.py:63` |
| **Classification** | advisory |

**Description:** `cleanup_signal_handlers()` opens with `global _registered_signals`
(line 63). pyflakes reports this name as unused-in-scope: the function never rebinds
`_registered_signals` (it only calls `_registered_signals.clear()`, which mutates the set
in place, and iterates it). The `global` declaration is therefore redundant and misleading — it
implies a module-level rebinding that never happens. It also means the function does not
actually protect against a future assignment-style bug; if someone later writes
`_registered_signals = ...`, the `global` would silently change behavior in a non-obvious
direction.

**Evidence:**
- `uv run python -m pyflakes`-equivalent (`uvx pyflakes src/vkdownloader/ tests/`) output:
  `src/vkdownloader/services/signal_handlers.py:63:5: \`global _registered_signals\` is unused:
  name is never assigned in scope`.
- `src/vkdownloader/services/signal_handlers.py:63` — `global _registered_signals`;
  line 86 — `_registered_signals.clear()` (mutation, not rebinding).

**Recommendation:** Remove the `global _registered_signals` line. The mutable set is already
reachable from the module namespace; `.clear()` mutates it correctly without a declaration.
Effort: trivial; priority: recommended.

---

### QLT-004: Broad `except` with double-close hazard in _create_temp_cookie_file

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE (correctness) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:88-94` (`_create_temp_cookie_file`) |
| **Classification** | advisory |

**Description:** `_create_temp_cookie_file` writes the cookie file with:

```python
    fd, path = tempfile.mkstemp(suffix=".cookies.txt", prefix="vk_cookies_")
    try:
        os.write(fd, content.encode())
        os.close(fd)
    except Exception:
        os.close(fd)            # hazard if the os.close on the line above already raised
        Path(path).unlink(missing_ok=True)
        raise
```

The handler catches broad `Exception` and then calls `os.close(fd)` again. If `os.write`
succeeded but the first `os.close(fd)` (line 90) raised (e.g. an already-closed descriptor or
an OS error), the second `os.close(fd)` raises `OSError: [Errno 9] Bad file descriptor`, which
propagates out of the `except` block, masking the original error. The subsequent
`Path(path).unlink(...)` never runs, so a temp file containing live VK session cookies
(`remixsid` etc.) could be left on disk on that path. The broad `except Exception` also swallows
the original exception type before re-raising (only the re-raised original is preserved if the
double-close doesn't fire).

**Evidence:**
- `src/vkdownloader/services/downloader.py:87-95`.
- Contrast with the project's own `0o600` cookie-file guidance (phase 04 SEC-004 / phase 06
  DF-007 already flag that these cookie files are not created `0o600` and may be left on
  crash); QLT-004 is the error-handling-angle gap in the same function.

**Recommendation:** Narrow the `except` to the specific I/O `OSError` from `os.write`, and
structure the close so it cannot run twice — e.g. close in a `finally` with a "closed" flag, or
use `contextlib.closing`/`os.fdopen` so a single `close()` runs. Ensure the temp-file cleanup
runs even when the descriptor-close itself fails. Effort: small; priority: recommended.

---

### QLT-005: Unparseable stray tooling scripts in `.temp/` break the whole-repo lint gate

| Field | Value |
|-------|-------|
| **ID** | QLT-005 |
| **Severity** | MEDIUM |
| **Type** | BEST-PRACTICE, SPEC-DEVIATION |
| **Affected Modules** | `.temp/write_findings.py`, `.temp/deadcheck.py`, `.ai/builders/back/*.py` (repo working tree; git-tracked) |
| **Classification** | advisory |

**Description:** The repo working tree contains a `.temp/` directory of stray, auto-generated
tooling scripts (audit helpers and dead-code scanners). Two of them are **unparseable Python**
and therefore cannot be imported, executed, or lint-fixed:

- `.temp/write_findings.py` — `SyntaxError: unterminated string literal` at line 61
  (`add('"m3u8 URLs contain ... -- directly as a command-line")` — an `add()` call with no
  arguments / malformed string).
- `.temp/deadcheck.py` — `SyntaxError: invalid non-printable character U+FEFF` at line 1
  (a UTF-8 BOM at file start).

Because `pyproject.toml` defines no `[tool.ruff] exclude`, running the linter over the whole
repo (`uv run ruff check .`) fails with **459 errors**, the large majority being the invalid
syntax in these two files. `.gitignore` also has no `.temp/` rule, and `git check-ignore`
confirms `.temp/write_findings.py`, `.temp/secret_scan.py`, and `.ai/builders/back/py_map.py`
are **not ignored**; `git ls-files` shows several `.temp/*` files (incl. `.temp/deadcheck.py`,
`.temp/*.txt`, `.temp/_yt_dlp_test.bin`) are **tracked in git**. The only reason
`uv run ruff check src/ tests/` (the src/tests-scoped command from `commands.md`) stays green
is that it does not include `.temp/`.

This is an escalation of the phase-01 CLI-003/CLI-005 recommendation (add a ruff `exclude` for
tooling paths / prune stray scripts): the recommendation was not applied, and the `.temp/`
directory has since accumulated an unparseable script, making the whole-repo gate far worse
(3 errors in phase 01 → 459 now).

**Evidence:**
- `uv run ruff check .` → `Found 459 errors` (run on `2026-08-09`); the dominant entries are
  `invalid-syntax` at `.temp\write_findings.py` (lines 61+) and `.temp\deadcheck.py:1`.
- `uv run python -c "...ast.parse..."` per-file:
  `.temp/write_findings.py -> PARSE-FAIL: unterminated string literal (line 61)`;
  `.temp/deadcheck.py -> PARSE-FAIL: invalid non-printable character U+FEFF (line 1)`;
  `.temp/secret_scan.py -> PARSE-OK`; `.ai/builders/back/py_map.py -> PARSE-OK`;
  `.ai/builders/back/py_map_libcst.py -> PARSE-OK`.
- `git check-ignore .temp/write_findings.py .temp/secret_scan.py .ai/builders/back/py_map.py`
  exits 1 (none ignored).
- `git ls-files '.temp/*' '.ai/builders/*'` lists tracked stray artifacts
  (`deadcheck.py`, `dj_stderr.txt`, `j_stdout.txt`, `p_stderr.txt`, `srv004_test.txt`,
  `srv004_test2.txt`, `_yt_dlp_test.bin`, ...).

**Recommendation:** Add `[tool.ruff] exclude = [".temp", ".ai/builders"]` to `pyproject.toml`
so non-application tooling is outside the lint/format/type gate (closes the root cause left open
by CLI-005), and delete/prune the stray `.temp/*.py` audit scripts and their `.txt`/`.bin`
outputs from the working tree (and from git if tracked). This restores a green whole-repo
`ruff check .` and removes the repository-noise that obscures real lint errors. Effort: trivial
(exclude) + small (prune); priority: recommended.

---

### QLT-006: Inconsistent docstring coverage on a documented validator

| Field | Value |
|-------|-------|
| **ID** | QLT-006 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE (maintainability) |
| **Affected Modules** | `src/vkdownloader/config.py:112-117` (`empty_string_to_none`) |
| **Classification** | advisory |

**Description:** `Settings.empty_string_to_none` (a pydantic `field_validator` at
`config.py:112-117`) has no docstring, while its three sibling validators in the same class —
`expand_tilde_paths` (`config.py:119-131`), `normalize_log_level` (`133-143`), and
`validate_cookie_source` (`145-157`) — are all documented. The missing docstring also makes the
CFG-002 field's empty-string behavior (which is subtle: `download_dir=""` crashes with an opaque
`path_type` error while `log_file=""` degrades to `None`) undocumented at the site where the
behavior is implemented, forcing readers to follow the CFG-002 trail to understand it.

**Evidence:**
- `src/vkdownloader/config.py:112-117`:
  ```python
  @field_validator("download_dir", "log_file", mode="before")
  @classmethod
  def empty_string_to_none(cls, v: object) -> object:
      if v == "":
          return None
      return v
  ```
  No docstring. Siblings at `config.py:119-157` each have an Args/body docstring.

**Recommendation:** Add a docstring to `empty_string_to_none` describing the `""` -> `None`
coercion and the `download_dir` vs `log_file` asymmetry (cross-referencing CFG-002), matching the
sibling validators' style. Effort: trivial; priority: recommended.

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 1 (QLT-005) |
| LOW | 5 (QLT-001, QLT-002, QLT-003, QLT-004, QLT-006) |
| **Total** | **6** |

## Mandatory Fixes

_No findings are classified as mandatory (security / data-loss / correctness gate)._ All six are
advisory. (The pre-existing mandatory lint/type/format failures — F841 `tests/test_correlation.py:28`,
`correlation.py:55` unused `type: ignore`, and the 4 format-drift files — are already tracked
under phase-01 findings CLI-003/CLI-004/CLI-005 and are not re-filed here.)

## Advisory Recommendations

- **QLT-001 (LOW):** Narrow `Any` usages in `services/concurrency.py` and `services/downloader.py`
  (protocol return + `_semaphore_context` return + `asyncio.Task[Any]`) to restore the project's
  strict "no `any`" typing posture. [BEST-PRACTICE] type safety.
- **QLT-002 (LOW):** Remove the no-op `except Exception: raise` in
  `segment_downloader.py:download_hls_with_resume`; the `try/finally` already covers cleanup.
  [BEST-PRACTICE] readability.
- **QLT-003 (LOW):** Drop the redundant `global _registered_signals` in `signal_handlers.py`
  (pyflakes-flagged). [BEST-PRACTICE] hygiene.
- **QLT-004 (LOW):** Narrow the broad `except` and eliminate the double-`os.close(fd)` hazard in
  `_create_temp_cookie_file`, guaranteeing temp cookie-file cleanup on the close-failure path.
  [BEST-PRACTICE] correctness / avoids leaving `remixsid` cookie files on disk.
- **QLT-005 (MEDIUM):** Add `[tool.ruff] exclude = [".temp", ".ai/builders"]` and prune the
  unparseable `.temp/*.py` audit scripts + stray outputs from the working tree/git. Restores a
  green whole-repo `ruff check .`. [BEST-PRACTICE] lint-gate hygiene / repo cleanliness.
- **QLT-006 (LOW):** Add the missing docstring to `Settings.empty_string_to_none`, matching its
  sibling validators. [BEST-PRACTICE] maintainability.

## Doc Updates Needed

_None. All findings are code-quality issues in `src/`/`tests/` (or repo tooling); no documentation
deviations were found in this phase. (Stale docs from prior phases remain tracked under CLI-007,
SRV-004/SRV-005, CFG-003/CFG-004, INT-001/INT-005.)
