---
name: 08-audit-quality-validated-findings
description: Validator-validated findings for Phase 08 (Code Quality, Security & Maintainability)
agent: validator
---

# Phase 08 Audit Findings (Validated) — Code Quality, Security & Maintainability

**Executor:** auditor (Senior architecture auditor)
**Validator:** validator (conservative, evidence-driven)
**Template:** .ai/audit/templates/audit-findings.md
**Phase template:** .kilo/commands/audit/phases/08-audit-quality.md
**Source findings:** .ai/audit/08-audit-quality/findings.md
**Status:** complete
**Validated:** yes
**Problems-only:** yes (passing checks are omitted per phase output mode)

**System under audit:** vkdownloader v0.1.0 — VK Video Downloader CLI (Python 3.12, uv, MIT).
Source: `src/vkdownloader/` (`cli.py`, `config.py`, `exceptions.py`, `models/`, `infrastructure/`,
`services/`, `utils/`, `__main__.py`, `stealth.min.js`). Tests: `tests/`.

This report is self-contained. The original findings are reproduced below with inline validation
decisions applied. The reader never needs to consult the source findings file.

---

## Validation Methodology

Per .kilo/commands/audit/phases/99-audit-validate.md, each finding was validated against:

1. **Implementation** — source code at the cited file paths and line numbers (read in full).
2. **Lint/types/format** — `uv run ruff check src/ tests/`, `uv run ruff check .`, `uv run mypy src/vkdownloader`, `uv run ruff format --check src/ tests/`, and `uvx pyflakes` re-run by the validator.
3. **Documentation** — `pyproject.toml` (ruff/mypy config), prior-phase findings referenced by the auditor.
4. **Runtime** — `uv run pytest` (325 passed).
5. **Cross-phase consistency** — compared against findings in phases 01 (CLI-003/004/005), 02 (CFG-001/002), 03 (SRV-002), 04 (SEC-004), 06 (DF-007), 07 (TST-001).

### Environment

- Python 3.12, uv
- Ruff: `ruff check src/` -> 0 errors; `ruff check src/ tests/` -> 1 error (F841 test_correlation.py:28); `ruff check .` -> 459 errors (dominated by .temp/ syntax failures)
- mypy: `uv run mypy src/vkdownloader` -> 1 error (correlation.py:55 unused type:ignore); config.py/svc modules mypy-clean for `Any`
- Ruff format: `ruff format --check src/ tests/` -> 4 files would reformat (downloader.py, test_cli.py, test_hls_downloader.py, test_security.py)
- pyflakes: `uvx pyflakes src/vkdownloader/` -> 1 finding (signal_handlers.py:63 redundant global)
- pytest: 325 passed in ~13s

---
## Runtime Verification (mandatory)

| Step | Command | Result | Evidence |
|------|---------|--------|----------|
| R1 — Lint | `uv run ruff check src/ tests/` | FAIL (1 error, pre-existing) | `tests/test_correlation.py:28` F841 unused `full` — filed CLI-003 (phase 01) / TST-001 (phase 07). `src/vkdownloader/` alone: PASS. |
| R1 — Lint (whole repo) | `uv run ruff check .` | FAIL (459 errors, escalating) | Dominated by unparseable stray scripts in `.temp/` (QLT-005). |
| R1 — Types | `uv run mypy src/vkdownloader` | FAIL (1 error, pre-existing) | `utils/correlation.py:55` unused `type: ignore[no-any-return]` — filed CLI-004 (phase 01). 26 source files checked. |
| R1 — Format | `uv run ruff format --check src/ tests/` | FAIL (4 files, pre-existing) | `services/downloader.py`, `tests/test_cli.py`, `tests/test_hls_downloader.py`, `tests/test_security.py` — filed CLI-005 (phase 01). |
| R2 — Tests | `uv run pytest` | PASS | 325 passed in 12.94s; no failures, no skips. |
| R3 — Dead code | `uvx pyflakes src/vkdownloader/` | 1 finding (1 new) | `signal_handlers.py:63` redundant `global` (QLT-003, new). `_write_netscape_cookie_file` dead code already filed SRV-002 (phase 03) — confirmed zero callers in `src/` and `tests/` via grep. Verified live callers exist for `_await_first_and_cancel_others`, `_temp_headers_file`, `_parse_ytdlp_progress`, `_echo_ytdlp_line`. |
| R4 — Security | grep secrets / `print(` / bare `except:` | PASS on forbidden patterns | No hardcoded secrets in app code. No `print(` in `src/` or `tests/`. No bare `except:`. 6 `except Exception:` sites (without `as e`) found — 2 surface new code-quality angles (QLT-002, QLT-004). No credentials logged directly. |

> The R1 lint/format/type failures are pre-existing and already tracked under phase-01
> findings CLI-003/CLI-004/CLI-005. They are restated here only as runtime evidence, not
> re-filed. No *new* lint/type/format defects were introduced in `src/vkdownloader/`.

---

## Findings
### QLT-001: `Any` type usage in production code violates the project "no `any`" rule

> **Validation Note:**
> - **Action:** validated (unchanged)
> - **Detail:** All four `Any` usage sites confirmed by direct code inspection:
>   `concurrency.py:5` (`from typing import Any, Protocol`), `concurrency.py:15` (`async def __aenter__(self) -> Any: ...`),
>   `downloader.py:14` (`from typing import TYPE_CHECKING, Any`), `downloader.py:60` (`def _semaphore_context(semaphore: SemaphoreLike | None) -> Any:`), and `downloader.py:121-122` (`*tasks: asyncio.Task[Any]` / `tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]`).
>   `ruff check --select F401 src/` passes (Any is used, not an unused import). `mypy src/vkdownloader` passes with only 1 unrelated error (correlation.py:55); mypy `strict=true` does NOT set `disallow_any_explicit=true`, so explicit `Any` in annotations is permitted by the type-checker. Project rule #9 ("Avoid `any` completely") is therefore violated in code but not enforced by tooling — the deviation is real.
> - **Evidence verified:** `ruff check --select F401 src/` -> All checks passed. `mypy src/vkdownloader` -> 1 error (correlation.py:55), 0 errors in concurrency.py/downloader.py.
> - **See also:** Project rule #9 (Type Safety Everywhere); pyproject.toml `[tool.mypy]` (strict=true, no disallow_any_explicit).

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
- `src/vkdownloader/services/concurrency.py:5` — `from typing import Any, Protocol` (confirmed)
- `src/vkdownloader/services/concurrency.py:15` — `async def __aenter__(self) -> Any: ...` (confirmed)
- `src/vkdownloader/services/downloader.py:14` — `from typing import TYPE_CHECKING, Any` (confirmed)
- `src/vkdownloader/services/downloader.py:60` — `def _semaphore_context(semaphore: SemaphoreLike | None) -> Any:` (confirmed)
- `src/vkdownloader/services/downloader.py:121-122` — `*tasks: asyncio.Task[Any]` / return `tuple[set[asyncio.Task[Any]], set[asyncio.Task[Any]]]` (confirmed)
- Grep `ruff check --select F401` on `src/`: no unused `Any` import (it is used), so this is a
  type-quality, not dead-import, issue. (confirmed: "All checks passed!")

**Recommendation:** Narrow the two easily-fixable sites: type `SemaphoreLike.__aenter__` to
`object` (or a dedicated return protocol), and `_semaphore_context` to
`SemaphoreLike | AbstractContextManager[object]`. The `asyncio.Task[Any]` cases `121-122` are the asyncio API convention and harder to remove without
`asyncio.Task[Coroutine[Any, Any, object]]` verbosity; treat them as a secondary follow-up. Effort: small; priority: recommended.

---
### QLT-002: No-op `except Exception: raise` in download_hls_with_resume

> **Validation Note:**
> - **Action:** validated (unchanged)
> - **Detail:** Confirmed by direct code inspection at `segment_downloader.py:885-886`. The function
>   `download_hls_with_resume` has a `try ... finally:` block (~884-889). The `try` body sets
>   `success = False` at the top, sets `success = True` only when `result is not None` (line 882),
>   and the `finally` block calls `_log_preserve_segments(segments_dir)` when `not success`. The
>   `except Exception: raise` at lines 885-886 sits between the `try` body and the `finally` and
>   performs no work — it catches all exceptions and immediately re-raises them. The `try/finally`
>   already ensures `_log_preserve_segments` runs on both normal and exceptional paths, so the
>   `except` clause is functionally dead. `uvx pyflakes src/vkdownloader/` confirms pyflakes does NOT
>   flag this (syntactically valid); it only reports QLT-003.
> - **Evidence verified:** `segment_downloader.py:885-886` — `except Exception:` / `raise`.
>   `uvx pyflakes src/vkdownloader/` reports only signal_handlers.py:63 (QLT-003).
> - **See also:** None. No prior phase findings (01-07) cite this code location.

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
- `src/vkdownloader/services/segment_downloader.py:885-886` — `except Exception:` / `raise`. (confirmed)
- pyflakes does not flag it (it is syntactically valid), so it survives the lint gate; it is a
  readability/maintenance smell, not a defect the tooling catches. (confirmed: uvx pyflakes on src/ reports only QLT-003)

**Recommendation:** Delete the no-op `except Exception: raise` block; keep the `try/finally`.
If future special handling is intended, add it explicitly rather than a pass-through catch.
Effort: trivial; priority: recommended.

---
### QLT-003: Redundant `global` declaration flagged by pyflakes

> **Validation Note:**
> - **Action:** validated (unchanged)
> - **Detail:** Confirmed by direct code inspection at `signal_handlers.py:63`. The function
>   `cleanup_signal_handlers()` declares `global _registered_signals` but never rebinds the name —
>   it only calls `_registered_signals.clear()` (line 86, in-place mutation) and iterates with
>   `list(_registered_signals)` (lines 71, 79). The `global` declaration is therefore redundant.
>   `uvx pyflakes src/vkdownloader/services/signal_handlers.py` confirms exactly:
>   `signal_handlers.py:63:5: `global _registered_signals` is unused: name is never assigned in scope`.
> - **Evidence verified:** pyflakes output matches the finding's claim verbatim.
> - **See also:** None.

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
- `uvx pyflakes src/vkdownloader/services/signal_handlers.py` output:
  `src/vkdownloader/services/signal_handlers.py:63:5: `global _registered_signals` is unused:
  name is never assigned in scope`. (confirmed verbatim)
- `src/vkdownloader/services/signal_handlers.py:63` — `global _registered_signals`;
  line 86 — `_registered_signals.clear()` (mutation, not rebinding). (confirmed)

**Recommendation:** Remove the `global _registered_signals` line. The mutable set is already
reachable from the module namespace; `.clear()` mutates it correctly without a declaration.
Effort: trivial; priority: recommended.

---
### QLT-004: Broad `except` with double-close hazard in _create_temp_cookie_file

> **Validation Note:**
> - **Action:** validated (unchanged)
> - **Detail:** Confirmed by direct code inspection at `downloader.py:87-95`. The function
>   `_create_temp_cookie_file` does: `fd, path = tempfile.mkstemp(...)` (line 87) -> `os.write(fd, ...)`
>   (line 89) -> `os.close(fd)` (line 90) inside a `try`, with `except Exception:` (line 91) that
>   calls `os.close(fd)` again (line 92) then `Path(path).unlink(missing_ok=True)` (line 93) and
>   `raise` (line 94). If `os.write` succeeds but the first `os.close(fd)` (line 90) raises an
>   `OSError` (e.g. EBADF), the except handler re-calls `os.close(fd)` (line 92) on an
>   already-closed descriptor, which raises `OSError: [Errno 9] Bad file descriptor`, masking the
>   original error and preventing `Path(path).unlink()` (line 93) from running — leaving a temp
>   cookie file on disk. grep confirms 6 `except Exception:` sites (without `as e`) in src/, of
>   which this and QLT-002 are the 2 flagged as code-quality concerns.
> - **Evidence verified:** Code at `downloader.py:87-95` matches the finding's quoted snippet exactly.
> - **See also:** DF-007 (phase 06) recommends `os.chmod(path, 0o600)` for the same function;
>   SEC-004 (phase 04) is a related security-angle finding. QLT-004 covers the error-handling gap,
>   not permissions — complementary, no conflict.

| Field | Value |
|-------|-------|
| **ID** | QLT-004 |
| **Severity** | LOW |
| **Type** | BEST-PRACTICE (correctness) |
| **Affected Modules** | `src/vkdownloader/services/downloader.py:87-95` (`_create_temp_cookie_file`) |
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
(`remixsid` etc.) could be left on disk on that path.

**Evidence:**
- `src/vkdownloader/services/downloader.py:87-95` (confirmed — matches the finding's snippet)
- grep `except Exception` in `src/vkdownloader/` -> 6 `except Exception:` sites (without `as e`);
  this function (downloader.py:91) and QLT-002 (segment_downloader.py:885) are the 2 that surface
  code-quality angles. (confirmed)
- Contrast with the project's own cookie-file guidance (phase 06 DF-007 already flags
  that these cookie files use `tempfile.mkstemp` at default permissions; QLT-004 is the
  error-handling-angle gap in the same function). (confirmed in phase 06 validated report)

**Recommendation:** Narrow the `except` to the specific I/O `OSError` from `os.write`, and
structure the close so it cannot run twice — e.g. close in a `finally` with a "closed" flag, or
use `os.fdopen` so a single `close()` runs. Ensure the temp-file cleanup
runs even when the descriptor-close itself fails. Effort: small; priority: recommended.

---
### QLT-005: Unparseable stray tooling scripts in `.temp/` break the whole-repo lint gate

> **Validation Note:**
> - **Action:** validated (unchanged)
> - **Detail:** All evidence claims verified:
>   1. `.temp/write_findings.py` is unparseable: `ast.parse(open(".temp/write_findings.py").read())` -> SyntaxError: unterminated string literal at line 61. (confirmed)
>   2. `.temp/deadcheck.py` is unparseable: hex dump of first 3 bytes = `ef bb bf` (UTF-8 BOM, U+FEFF). `ast.parse` raises SyntaxError: invalid character at line 1. (Minor note: under the Windows default text encoding, Python's `ast.parse` reported the codepoint as U+00BB rather than U+FEFF; however the raw bytes EF BB BF unambiguously confirm a UTF-8 BOM, matching the finding's claim.)
>   3. `.temp/secret_scan.py`, `.ai/builders/back/py_map.py`, `.ai/builders/back/py_map_libcst.py` all PARSE-OK. (confirmed)
>   4. `.gitignore` has no `.temp/` or `.ai/builders` rule. (confirmed)
>   5. `git check-ignore .temp/write_findings.py .temp/secret_scan.py .ai/builders/back/py_map.py` exits 1 (none ignored). (confirmed)
>   6. `git ls-files ".temp/*"` lists tracked files: `.temp/deadcheck.py`, `.temp/_yt_dlp_test.bin`, `.temp/dj_stderr.txt`, ... (`.temp/write_findings.py` is NOT tracked — only the older .txt/.bin files and deadcheck.py are tracked). `.ai/builders/back/py_map.py` and `py_map_libcst.py` ARE tracked. (confirmed)
>   7. `pyproject.toml` has `[tool.ruff]` with only `line-length`/`target-version` — no `exclude` key. (confirmed)
>   8. `uv run ruff check .` -> "Found 459 errors." (confirmed)
>   9. QLT-005 is an escalation of CLI-005 (phase 01): the phase-01 validated report recommends adding a ruff exclude; it was NOT applied (pyproject.toml still has no exclude). The `.temp/` directory has since accumulated `.temp/write_findings.py` with invalid syntax, escalating from 3 errors (phase 01) to 459 (now). (confirmed)
> - **Evidence verified:** All claims confirmed by validator re-execution.
> - **See also:** CLI-003, CLI-005 (phase 01) — shared root cause (missing ruff `exclude` for scaffolding paths).

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
  (a UTF-8 BOM at file start; hex dump of bytes 1-3: EF BB BF).

Because `pyproject.toml` defines no `[tool.ruff] exclude`, running the linter over the whole
repo (`uv run ruff check .`) fails with **459 errors**, the large majority being the invalid
syntax in these two files. `.gitignore` also has no `.temp/` rule, and `git check-ignore`
confirms `.temp/write_findings.py`, `.temp/secret_scan.py`, and `.ai/builders/back/py_map.py`
are **not ignored**; `git ls-files` shows several `.temp/*` files (incl. `.temp/deadcheck.py`,
`.temp/*.txt`, `.temp/_yt_dlp_test.bin`) are **tracked in git**. The only reason
`uv run ruff check src/ tests/` (the src/tests-scoped command from `commands.md`) stays green
is that it does not include `.temp/`.

This is an escalation of the phase-01 CLI-005 recommendation (add a ruff `exclude` for
tooling paths / prune stray scripts): the recommendation was not applied, and the `.temp/`
directory has since accumulated an unparseable script, making the whole-repo gate far worse
(3 errors in phase 01 -> 459 now).

**Evidence:**
- `uv run ruff check .` -> `Found 459 errors` (run on `2026-08-09`); the dominant entries are
  `invalid-syntax` at `.temp\write_findings.py` (lines 61+) and `.temp\deadcheck.py:1`. (confirmed)
- `uv run python -c "...ast.parse..."` per-file:
  `.temp/write_findings.py -> PARSE-FAIL: unterminated string literal (line 61)` (confirmed);
  `.temp/deadcheck.py -> PARSE-FAIL: invalid non-printable character at line 1` (confirmed, hex: EF BB BF = UTF-8 BOM = U+FEFF);
  `.temp/secret_scan.py -> PARSE-OK` (confirmed); `.ai/builders/back/py_map.py -> PARSE-OK` (confirmed);
  `.ai/builders/back/py_map_libcst.py -> PARSE-OK` (confirmed).
- `git check-ignore .temp/write_findings.py .temp/secret_scan.py .ai/builders/back/py_map.py`
  exits 1 (none ignored). (confirmed)
- `git ls-files '.temp/*' '.ai/builders/*'` lists tracked stray artifacts
  (`.temp/deadcheck.py`, `.temp/dj_stderr.txt`, `.temp/dj_stdout.txt`, ..., `.temp/_yt_dlp_test.bin`).
  `.temp/write_findings.py` is NOT tracked (working-tree only). `.ai/builders/back/py_map.py` and
  `py_map_libcst.py` ARE tracked. (confirmed)
- `pyproject.toml [tool.ruff]`: no `exclude` key present. (confirmed)

**Recommendation:** Add `[tool.ruff] exclude = [".temp", ".ai/builders"]` to `pyproject.toml`
so non-application tooling is outside the lint/format/type gate (closes the root cause left open
by CLI-005), and delete/prune the stray `.temp/*.py` audit scripts and their `.txt`/`.bin`
outputs from the working tree (and from git if tracked). This restores a green whole-repo
`ruff check .` and removes the repository-noise that obscures real lint errors. Effort: trivial
(exclude) + small (prune); priority: recommended.

---
### QLT-006: Inconsistent docstring coverage on a documented validator

> **Validation Note:**
> - **Action:** validated (unchanged)
> - **Detail:** Confirmed by direct code inspection at `config.py:112-117`. The
>   `Settings.empty_string_to_none` validator has NO docstring. Its three sibling validators in
>   the same class all have docstrings: `expand_tilde_paths` (config.py:119-131),
>   `normalize_log_level` (config.py:133-143), and `validate_cookie_source` (config.py:145-157).
>   The missing docstring also means the CFG-002 empty-string behavior (`download_dir=""` crashes
>   with an opaque path_type error while `log_file=""` degrades to None) is undocumented at the
>   site where the behavior is implemented. QLT-006 correctly references CFG-002 (phase 02,
>   validated); note that the code's own inline comment at config.py:126-127 mis-references
>   CFG-001 (should be CFG-002) and misnames LOG_FILE (should be download_dir) — this was already
>   flagged in the phase 02 validated report. QLT-006's recommendation to add a docstring
>   cross-referencing CFG-002 is sound and consistent with the phase 02 recommendation to
>   correct the misnamed comment.
> - **Evidence verified:** Code at config.py:112-117 matches the finding's quoted snippet. Sibling
>   docstrings confirmed. CFG-002 validated in phase 02.
> - **See also:** CFG-002 (phase 02) — shares the same code area (empty_string_to_none +
>   expand_tilde_paths); complementary finding, no conflict. Phase 02 validated report already
>   recommends correcting the config.py:126-127 comment to reference download_dir, not LOG_FILE.

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
  No docstring. Siblings at `config.py:119-157` each have an Args/body docstring. (confirmed)

**Recommendation:** Add a docstring to `empty_string_to_none` describing the `""` -> `None`
coercion and the `download_dir` vs `log_file` asymmetry (cross-referencing CFG-002), matching the
sibling validators' style. Effort: trivial; priority: recommended.

---
## Cross-Finding Analysis

### Cross-phase overlaps

| Overlap | Phases | Nature | Assessment |
|---------|--------|--------|------------|
| Missing ruff exclude for `.temp/`/`.ai/` | QLT-005 (PH08) + CLI-003/CLI-005 (PH01) | QLT-005 is an escalation: phase-01 found 3 ruff errors from `.temp/deadcheck.py` + test F841; recommendation to add exclude was NOT applied; `.temp/write_findings.py` was subsequently added, escalating to 459 errors. | Same root cause (missing ruff `exclude` in pyproject.toml). QLT-005 is a worsening, not a duplicate. No conflict. |
| Cookie-file error handling + permissions | QLT-004 (PH08) + DF-007 (PH06) + SEC-004 (PH04) | All three touch `_create_temp_cookie_file` (downloader.py:87-95). DF-007 targets file permissions (0644 -> 0o600); QLT-004 targets the double-close error-handling hazard. | Same function, different angle. Complementary, no conflict. No merge — distinct fixes. |
| Empty-string config handling | QLT-006 (PH08) + CFG-002 (PH02) | CFG-002 flags the asymmetric crash for `download_dir=""`; QLT-006 flags the missing docstring on the `empty_string_to_none` validator that implements the behavior. | Same code area, different finding type (user-facing behavior vs. docstring coverage). Complementary, no conflict. |
| Redundant `global` + unused var | QLT-003 (PH08) + CLI-003/TST-001 (PH01/PH07) | QLT-003 flags `signal_handlers.py:63` redundant global; the test F841 at `test_correlation.py:28` is restated as runtime evidence (not re-filed). | QLT-003 is genuinely new; the test F841 is correctly attributed to CLI-003/TST-001. No conflict. |

### Cross-phase conflicts

**None detected.** All phases report consistent runtime verification:

- pytest: 325 passed (confirmed by validator re-run)
- ruff check src/ tests/: 1 error (F841 test_correlation.py:28) — same as phase 01 CLI-003
- ruff check .: 459 errors — escalated from phase 01's 3 (see QLT-005 overlap above)
- ruff format --check src/ tests/: 4 files — same as phase 01 CLI-005 (subset of the 7 whole-repo)
- mypy src/vkdownloader: 1 error (correlation.py:55) — same as phase 01 CLI-004

No phase claims "all commands work" while another reports a crash. No contradictory behavioral assertions about the same code.

### Dependency chains

| Finding | Depends on | Reason |
|---------|-----------|--------|
| QLT-005 (ruff exclude) | CLI-005 (phase 01) | Same root cause. CLI-005's recommendation was not applied; QLT-005 escalates. Fix is shared (one `exclude` config). |
| QLT-004 (error handling) | None | Independent of DF-007 (permissions) — different code line within same function. |
| QLT-006 (docstring) | None | Independent; can be applied alongside CFG-002's recommended comment fix (config.py:126-127). |
| QLT-001, QLT-002, QLT-003 | None | Fully independent. |

No circular dependencies. No hidden dependency chains.

---
## Rollout Safety Assessment

**Circular dependencies:** None. All six findings target independent, well-scoped code locations
with no inter-module import changes.

**Unsafe execution sequences:** None detected. All findings are advisory. No finding requires a
database migration or schema change. No finding introduces a new runtime dependency.

**Fragile insertion points:**
- QLT-003's removal of `global _registered_signals` is a single-line deletion at line 63 — no
  structural impact.
- QLT-002's removal of the no-op `except` block is a 2-line deletion at lines 885-886 — the
  `try/finally` structure is preserved.
- QLT-004's restructuring of `_create_temp_cookie_file` (downloader.py:87-95) is a small,
  self-contained error-handling rewrite — the function signature and return type are unchanged.
- QLT-001's narrowing of `Any` annotations is a type-annotation change only (no runtime effect).
- QLT-005's `pyproject.toml` `exclude` addition + `.temp/` file deletion is a config/repo-cleanup
  change — no application code impact.
- QLT-006's docstring addition is a no-op at runtime.

**Backward compatibility:** None of the six findings change public APIs, CLI contracts, or
config schemas. QLT-001's annotation narrowing may require downstream type-checker consumers to
adjust, but the project has no external type consumers (internal CLI package, v0.1.0 Alpha).

---

## Execution Validation

**Applicability & readiness:** All 6 findings are applicable to the current codebase (v0.1.0).
Verified by:

- Direct source code inspection — all cited line numbers match exactly
- Runtime verification — ruff/mypy/format/pytest/pyflakes re-run by the validator (results above)
- Dependency/import chain tracing — grep across `src/` and `tests/` for affected symbols
- Documentation comparison — pyproject.toml config, prior-phase validated reports

| ID | Targets confirmed | Status |
|----|-------------------|--------|
| QLT-001 | concurrency.py:5,15; downloader.py:14,60,121-122 | Ready |
| QLT-002 | segment_downloader.py:885-886 | Ready |
| QLT-003 | signal_handlers.py:63 | Ready |
| QLT-004 | downloader.py:87-95 | Ready |
| QLT-005 | pyproject.toml `[tool.ruff]` (no exclude); `.temp/` scripts (unparseable); git tracking status | Ready |
| QLT-006 | config.py:112-117 (missing docstring); sibling validators at 119-157 (have docstrings) | Ready |

**Execution prerequisites:** None. All findings are independent, advisory, and do not depend on
prior-phase fixes to be safe. QLT-005's exclude recommendation overlaps with CLI-005 (phase 01)
but the config change is trivial and backward-compatible (excludes only non-application paths).

---
## Warnings

- **Lint gate escalation (QLT-005):** The whole-repo `ruff check .` gate has degraded from 3 errors
  (phase 01) to 459 errors. While `ruff check src/ tests/` (the project's documented command) remains
  green, any future broad-scope lint run will be unusably noisy until the `.temp/` exclude is applied
  and stray scripts are pruned.
- **Cookie-file security convergence (QLT-004 + DF-007):** Both findings target
  `_create_temp_cookie_file` (downloader.py:87-95). If both are fixed in the same PR, the
  `os.chmod(path, 0o600)` from DF-007 and the error-handling restructure from QLT-004 must be
  composed carefully to avoid reordering `os.write`/`os.close` relative to `os.chmod`.
- **Docstring cross-reference accuracy (QLT-006):** The code's inline comment at config.py:126-127
  mis-references CFG-001 (should be CFG-002) and misnames LOG_FILE (should be download_dir). This
  was already flagged in the phase 02 (CFG-002) validated report. QLT-006's recommendation to add a
  docstring to `empty_string_to_none` should also correct this adjacent comment for consistency.
- **pyflakes not installed:** The project's dev dependencies (`pyproject.toml` dev group) do NOT
  include `pyflakes`. The auditor noted pyflakes findings, but the project's actual gate uses `ruff`
  (which includes pyflakes F-codes). This means QLT-003 (redundant `global`) is NOT caught by the
  project's lint gate — it would only surface if pyflakes or ruff's F824 rule were enabled.

---

## Required Fixes

_No findings are classified as mandatory (security / data-loss / correctness gate). All six are
advisory._ (The pre-existing mandatory lint/type/format failures — F841 `tests/test_correlation.py:28`,
`correlation.py:55` unused `type: ignore`, and the 4 format-drift files — are already tracked
under phase-01 findings CLI-003/CLI-004/CLI-005 and are not re-filed here.)

## Advisory Recommendations

| ID | Title | Type | Effort | Verdict |
|----|-------|------|--------|---------|
| QLT-001 | Narrow `Any` usages in concurrency.py and downloader.py | BEST-PRACTICE, SPEC-DEVIATION | small | Validated |
| QLT-002 | Remove no-op `except Exception: raise` in segment_downloader.py | BEST-PRACTICE | trivial | Validated |
| QLT-003 | Remove redundant `global _registered_signals` in signal_handlers.py | BEST-PRACTICE | trivial | Validated |
| QLT-004 | Fix double-close hazard in `_create_temp_cookie_file` (downloader.py) | BEST-PRACTICE | small | Validated |
| QLT-005 | Add `[tool.ruff] exclude` for `.temp`/`.ai/builders`; prune unparseable stray scripts | BEST-PRACTICE, SPEC-DEVIATION | trivial + small | Validated |
| QLT-006 | Add missing docstring to `empty_string_to_none` in config.py | BEST-PRACTICE | trivial | Validated |

## Doc Updates Needed

_None. All findings are code-quality issues in `src/`/`tests/` (or repo tooling); no documentation
deviations were found in this phase. (Stale docs from prior phases remain tracked under CLI-007,
SRV-004/SRV-005, CFG-003/CFG-004, INT-001/INT-005.)

---

## Validation Summary

| Action | Count | Details |
|--------|-------|---------|
| Validated (unchanged) | 6 | QLT-001, QLT-002, QLT-003, QLT-004, QLT-005, QLT-006 |
| Reclassified | 0 | — |
| Merged | 0 | — |
| Rejected | 0 | — |

### Rejected Findings

| ID | Title | Reason |
|----|-------|--------|
| (none) | — | All 6 findings were verified against the live codebase. No rejections. |

### Merged Findings

| Original ID | Merged Into | Rationale |
|-------------|-------------|----------|
| (none) | — | No findings share a single root cause within this phase. Cross-phase overlaps documented in the Cross-Finding Analysis above (QLT-005 overlaps CLI-005; QLT-004 overlaps DF-007; QLT-006 overlaps CFG-002) — all complementary, none merged. |

### Reclassified Findings

| ID | Original Type | New Type | Rationale |
|----|---------------|----------|-----------|
| (none) | — | — | All findings retain their original type classifications. No reclassifications. |

### Cross-Phase Conflicts

| Conflict | Phases | Resolution |
|----------|--------|-----------|
| (none) | — | No contradictory evidence between phases. All runtime verification results are consistent. |

### Recommended Fix Ordering

1. **QLT-005** (lint-gate hygiene) — apply first: add `[tool.ruff] exclude` to pyproject.toml
   and prune `.temp/` stray scripts. Restores a green `ruff check .`, unblocking all future lint
   runs.
2. **QLT-003, QLT-002** (trivial hygiene) — delete the redundant `global` and the no-op `except`
   block. Single-line deletions, no behavioral change.
3. **QLT-001, QLT-006** (type/doc hygiene) — narrow `Any` annotations and add the missing
   docstring. Low risk, independent.
4. **QLT-004** (error-handling fix) — restructure `_create_temp_cookie_file`'s try/except. Apply
   alongside or after DF-007 (phase 06, `os.chmod(path, 0o600)`) to compose cleanly in the same
   function.
5. All findings are independent and advisory; ordering is by effort and gate impact, not by hard
   dependency.

---

*End of validation report.*
