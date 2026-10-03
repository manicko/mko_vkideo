# Phase 09 — Code-quality audit fixes — execution plan

Artifact under execution: `.ai/audit/99-validation/09-code-quality-validated-findings.md` (13 `QLT-` findings, 3 `VAL-` findings, 6 recorded warnings).
Artifact base: `a335b2a`. **Plan base: `HEAD = 09f1b10`**, working tree clean of any `src/`/`tests/`/`docs/`/`pyproject.toml` edit. **Re-baselined from `4bf9efb` → `09f1b10`** after the Product Owner's rulings A–D (§2.9) landed. `09f1b10` is three commits past the `58bb7ce` the re-baseline request named; both are measured and §2 states the figures at `09f1b10`.
Cross-plan corpus: plans 05–12, 13, 16 in `.ai/plans/`, the completion report `.ai/plans/09-concurrency-cancellation-audit-fixes-completion.md`, and the twelve validation artifacts under `.ai/audit/99-validation/`.

**Nothing in this plan modifies production code, tests, or any file under `.ai/audit/`. This file is the only write.**

---

## 1. Scope

### 1.0 Product Owner rulings folded into this re-baseline

Four rulings were made after this plan was first written. Each is recorded in §2.9 with its enforcement evidence. The rulings **narrow** this plan; they add no block and remove none except where noted.

| Ruling | Effect on this plan |
|---|---|
| **A — ffmpeg.** yt-dlp is the loader; ffmpeg is not a loader transport; **segment download stays and ffmpeg stays as the segment merge engine.** The group-A/group-C symbols are **permanent product surface**. `ffmpeg_utils.py` **can never be deleted whole.** | **No block removed.** This plan **never had a decomposition block touching `ffmpeg_utils.py`** — see §1.6, which states that explicitly and records that the ruling converts an accident into a decision. §1.4's group-B row becomes permanent-deleted rather than pending. `B11`'s citation census shrinks by three identifiers. `check_ffmpeg_available`'s disposition is resolved and two plans were wrong (§4.4 row 24) |
| **B — Python floor `>=3.14`.** Implementation is plan 16's; **the enforcement evidence is this phase's.** | **New, in scope for `B3`.** Three silent pins measured in `pyproject.toml`; new decision `D16`; `B3`'s scope and acceptance criteria extended. `QLT-009` re-measured: **the `Any` count did not move**, so it is **not** partly self-resolving |
| **C — exit code contract.** `0` success · `1` download failure and nothing else · `2` usage error · `3` configuration error · `4`+ unallocated. Implementation is plan 13's. | **Recorded as a constraint, not implemented.** `QLT-001` is **not widened** — it stays an internal-consistency finding. Enforcement evidence recorded in §2.9 |
| **D — not published.** The product is not published; the misleading release trigger is deleted by plan 16. | **Recorded only.** §2.9 records whether `QLT-008`'s and `QLT-005`'s value changes. Neither block's scope changes |

**Two housekeeping corrections to the re-baseline request, measured not inherited:**

1. **HEAD is `09f1b10`, not `58bb7ce`.** `58bb7ce` is an ancestor; three commits landed on top (`b0fb032`, `db0e33e`, `09f1b10`), touching `ffmpeg_utils.py`, `ytdlp_downloader.py`, `url_sanitizer.py`, `test_hls_downloader.py` (+302) and `test_url_sanitizer.py`. All §2 figures are measured at `09f1b10`.
2. **`uv run ruff format --check src tests` is GREEN at `09f1b10`** — "54 files already formatted". The reported red gate on two `with patch(...)` blocks in `TestYtDlpSubprocessShutdown` is **not reproducible at this base**; that class grew by 302 lines between `58bb7ce` and `09f1b10` and is now formatted. The narrow-fallback rule is nevertheless retained in §2.2 and §5.2 as a standing constraint, because a later commit can reintroduce it and a blanket reformat remains prohibited.

---

## 1. Scope

### 1.1 How this plan was derived

Three inputs, in this order:

1. The validated artifact above, read in sections (`## R0 — Discovery` … `## Validation Summary`).
2. The complete auditor dossier, including its §5.3 collision table tail, §6 ffmpeg exposure, §7 cross-phase overlaps and §8 drift — recovered from the tool-output artefact whose summary had been truncated.
3. **A re-measurement of the live tree by the Planner**, because the artifact's `## The tree-drift measurement, re-performed` section is void and because nine of the artifact's numbers had moved again. §2.5 records every correction with both figures.

The artifact's own drift section is recorded as **void** and is used for nothing: it measured `HEAD = a335b2a` against two dirty files modified by a concurrent agent. Those edits no longer exist (`git diff HEAD --numstat -- src/` is empty) and the base has moved 49 commits (92 files, +40143/−6757). Its shift-only verdict was correct for the tree it measured and examined 2 files, while phase-09's citations span ≥11 source files, 6 test files, 7 documents and `pyproject.toml`. Its one durable contribution is the negative finding — nothing in this plan is filed on line drift — which holds.

### 1.2 Anchor discipline — binding on every block

Of ~200 distinct `file:line` anchors across the 13 findings, exactly one file has zero drift: `exceptions.py`. Everything else moved.

**Rule: every block's scope in §3 and §6 is expressed by symbol, module, class, method, enum member, frozenset or document path. Zero `file:line` anchors appear in any block's scope.** This follows plan 12's precedent, which carries zero `file:line` anchors in its own file. Where a symbol name is itself a citation string (a `patch()` target), the string is quoted verbatim because it *is* the semantic anchor.

**Re-confirmed at `09f1b10`, per ruling B:** `exceptions.py` is **still 228 physical lines and still zero drift**. `B1` and `B13`'s shared-edit-region reasoning with `VAL-903` both depend on that, and it holds across the ffmpeg retirement.

The only line-shaped facts in this plan are in §2 (baseline measurements) and §5.4 (prohibitions that survive a fix), never in a block's scope.

### 1.3 IN — the 16 findings, mapped to 13 blocks

| Block | Findings | Sev | Risk |
|---|---|---|---|
| `B1` | `QLT-001` + `QLT-010` as one change; `VAL-903`'s ordering constraint discharged | HIGH | High |
| `B2` | `QLT-002` | MEDIUM | High |
| `B3` | `QLT-009` | LOW (was MEDIUM) | Medium |
| `B4` | `QLT-011` | MEDIUM | High |
| `B5` | `QLT-013` | LOW | Low |
| `B6` | `QLT-003` | LOW (was MEDIUM) | Medium |
| `B7` | `QLT-004` | LOW | Medium |
| `B8` | `QLT-005` | LOW | Low |
| `B9` | `QLT-006` | MEDIUM | Medium |
| `B10` | `QLT-008` | LOW | Low |
| `B11` | `QLT-007` | LOW | Medium |
| `B12` | `QLT-012` | LOW | Low |
| `B13` | `VAL-901` + `VAL-902` + the 6 recorded warnings — **escalation, no code** | CRITICAL / MEDIUM | High |

Findings merged and why:

- **`QLT-001` + `QLT-010` into `B1`.** `VAL-903` records that `exceptions.py` and `tests/test_exceptions.py` are a shared edit region and mandates one change. Two commits over the same region double the contention window and produce a transiently inconsistent vocabulary — an `ErrorCode` member that no `status_label()` can yet produce. Merged.
- **`QLT-011` + `QLT-013` split, not merged.** They share a file but not a risk. `QLT-013` is comment-only and must stay comment-only; `QLT-011` is a module move. Folding them would put a zero-risk edit behind the highest-risk decision in the phase. `QLT-013` becomes `B5`; `QLT-011` becomes `B4`.
- **`VAL-903`'s ordering constraint is not a finding to fix — it is discharged by `B1`'s construction.** Its census is re-measured in `B4`'s scope because it bears on the patch-string blast radius.

### 1.4 OUT — ceded, deferred, recorded

| Item | Disposition | Owner |
|---|---|---|
| `docs/STRUCT.md`'s `ffmpeg_utils.py` row | **YIELDED.** See §4.3, decision `D15`. | Plan 12 `P12-B12` |
| The `0o600`/`0o666` confinement posture | OUT | Plan 12 `P12-B11`, plan 11 `B3`, phase 10 `TST-013` |
| `DownloadMethod.FFMPEG` and the `--method ffmpeg` transport | **OUT and now DONE — permanently deleted.** `d572d96` removed `DownloadMethod.FFMPEG` **outright, with no tombstone member**, which is the correct outcome under rule 10. Measured at `09f1b10`: `DownloadMethod` has **only `YTDLP` and `AUTO`**; `grep` for `download_with_ffmpeg`, `HLSDownloader`, `_temp_argfile`, `_format_argfile`, `FfmpegProgress`, `ProgressParser`, `read_progress` across `src/`, `tests/`, `docs/` and `README.md` returns **0 hits**. The retirement is **clean**, which is why several blocks below shrink rather than grow | Closed |
| `_temp_argfile` / `_format_argfile` deletion | **OUT and now DONE** — `d572d96`. **Two consequences this plan must absorb:** the symbol no longer exists anywhere, and `test_temp_argfile_permissions_are_0600` was deleted with it, which is why the skip floor fell from 4 to 3 (§2.2) | Closed |
| `ffmpeg_utils.py` group B (`FfmpegProgress`, `ProgressParser`, `read_progress`, `_ProgressHandler`, `_PROGRESS_KEY_HANDLERS`) | **OUT and now DONE** — `d572d96`. **No block in this plan deletes, renames, splits or documents any ffmpeg symbol, surviving or retired** | Closed |
| `ffmpeg_utils.py` group A (`iter_process_lines`, `cancel_subprocess`, `cancel_ffmpeg_process`) and `check_ffmpeg_available` | **OUT — permanent product surface, per ruling A.** Measured present at `09f1b10`. `check_ffmpeg_available`'s only call site is a bare statement in `perform_download` whose **return value is discarded** — the ruling makes that permanent | Permanent |
| `ffmpeg_utils.py` group C (the eight merge-engine symbols) | **OUT — permanent product surface, per ruling A.** The HLS segment path's only merge. **It still spawns ffmpeg.** | Permanent |
| The four D-11 file-mode oracles | OUT — must not be deleted, weakened or un-skipped by any block. **Now 3, not 4** — see §2.2 | Plan 11 `B3`, phase 10 `TST-013` |
| `ffmpeg_utils.py`'s module docstring and `services/downloader.py`'s `ffmpeg_utils` ownership group | **OUT of every block.** Recorded in §5.6 as unowned so the gap stays visible. **Ruling A strengthens the case: the module is permanent product code whose docstring still describes a retired transport.** | Unowned — escalate with `B13` |
| `docs/01-tools/api-reference.md`'s `ffmpeg_utils` location rows | OUT | Unowned |
| `cookies.py`, `url_sanitizer.py`, `config.setup_logging`, `models/dtos.py::HLSDownloadRequest.cookies`, `segment_downloader.py::DownloadPolicy.headers`, `extractor.py::_extract_with_browser` | OUT | Plan 11 |
| `utils/security.py` traversal / containment / device names | OUT | Plan 12 `B1`, `B2`, `B5` |
| `docs/STRUCT.md`'s absence of YAML frontmatter | OUT — `STRUCT.md` is a root structural map with none and is edited in place | — |
| `segment_downloader.py` sweeps and working-tree lifetime | OUT | Plan 12 `P12-B6`, `B7`, `B8` |
| The import graph, cycles and re-export facades as a whole | OUT | Phase 01 `ENT-005/006/007` |
| `.kilo/commands/audit/phases/99-audit-validate.md`'s severity table (`VAL-601`) | OUT | Plan 11 `B9` |
| `.ai/audit/templates/audit-findings.md`'s pre-answered summary (`VAL-603`) | OUT | Plan 11 `B10` |
| `ignore_missing_imports = true` → `false` | **OUT.** `yt_dlp` is untyped and would produce a wall of errors for no gain. Criterion in `D6`. | Deferred, unowned |
| Making `docs/STRUCT.md` machine-checked | OUT — would add a test file and a frozenset edit for a scope this plan does not own. Recorded in §2.6 as an oracle gap. | Deferred |

### 1.5 Deferred — authorised later, not here

- `VAL-901`'s re-key of the flat `VAL-` namespace and `VAL-902`'s in-place annotation both require editing files under `.ai/audit/99-validation/`. Plan 11 `B10` carries an absolute staging prohibition on that path, and no document authorises this phase to write there. `B13` therefore **escalates** and stops. See §3.13.
- `VAL-901`'s half that needs no `.ai/audit/` write — naming the collision hazard and its owner — is delivered as the `B13` escalation note.

### 1.6 The `ffmpeg_utils.py` decomposition question — answered explicitly

The re-baseline asks whether this plan proposes splitting `ffmpeg_utils.py` along a retirement seam, and whether that block survives ruling A. **It does not propose it, and there is no such block to remove.**

The only module this plan splits is **`downloader_throttle.py`** (`B4`, `QLT-011`), and the split seam is **retry policy versus shutdown signalling** — a concern boundary that has nothing to do with ffmpeg and that exists independently of the retirement. `ffmpeg_utils.py` appears in this plan in exactly three places, and in **none** of them as an edit target:

1. **Prohibition** — §5.4 item 2: the module is never deleted whole, and group A and group C must survive.
2. **Out-of-scope lists** — `B4`, `B8`, `B11` each name it as something they do not touch.
3. **The yielded `docs/STRUCT.md` row** — §4.3, owned by plan 12 `P12-B12`, never written here.

**What ruling A changes.** Before the ruling, "do not decompose `ffmpeg_utils.py`" was a precaution derived from a transitional state: group B was pending deletion by plan 10, so the module had a foreseeable future in which its partition mattered. After the ruling the module is **permanent product code with a permanent three-part shape** — generic subprocess infrastructure (group A), the startup availability probe (`check_ffmpeg_available`), and the segment merge engine (group C) — and group B is already gone. The prohibition is therefore no longer precautionary: it is **the correct description of a module that will never have a retirement seam**. Any future decomposition of this file would be an ordinary refactor judged on its own merits, not a phase boundary.

**Ruling A also strengthens, and does not weaken, the argument for `B6` yielding the `docs/STRUCT.md` row.** The row reads "FFmpeg discovery and stream concatenation". Measured at `09f1b10`: **"discovery" names `check_ffmpeg_available`, which ruling A makes permanent product surface**, and the row omits both group A and group C. The sentence is therefore wrong about a module that will never change — a reader acting on it would delete permanent infrastructure and could not appeal to a pending retirement. That strengthens the case for plan 12 `P12-B12` owning the sentence; it does **not** transfer ownership to this phase. `B6` still yields it, and §4.3 still stands.

**One thing the ruling got right, recorded as a positive.** `DownloadMethod.FFMPEG` was **deleted outright rather than left as a tombstone member**. Rule 10 forbids leaving a tombstone, `d572d96` complied, and `models/enums.py` shrank by exactly one line with **zero residue** — `grep` for every deleted symbol across `src/`, `tests/`, `docs/` and `README.md` returns 0 hits. That is the codebase getting it right. It matters here because `B12`'s layering finding depends on `models/quality.py`'s shape: the enum module is **smaller** than when this plan was first written, the rule-10 obligation is discharged, and `B12`'s finding — that `models/quality.py` imports upward into `exceptions` lazily to break a real cycle — is **unaffected**, because that upward import is not an enum import at all.

---

## 2. Baseline

Every command in §2.1–§2.3 was **re-run by the Planner against the live tree**, first at `HEAD = 4bf9efb` and then again at **`HEAD = 09f1b10`** after the Product Owner's rulings. Nothing here is inherited from the artifact or from a summary. **Where the two bases disagree, the `09f1b10` figure is authoritative and the change is recorded in §2.5.**

### 2.1 Gates — re-run, and binding

Measured at `HEAD = 09f1b10`:

| Gate | Command | `4bf9efb` | **`09f1b10`** |
|---|---|---|---|
| Test suite | `uv run pytest -q -rs` | 772 passed, 4 skipped, 1 warning | **759 passed, 3 skipped, 1 warning** |
| Lint | `uv run ruff check src tests` | clean | **clean** |
| Format | `uv run ruff format --check src tests` | 54 files already formatted | **54 files already formatted — GREEN** |
| Lint (wide) | `uv run ruff check .` | clean | **clean** |
| Types (source) | `uv run mypy src` | clean, 31 source files | **clean, 31 source files** |
| Types (delta only) | `uv run mypy src tests` | 79 errors in 8 files | **89 errors in 8 files** |
| Rule-9 probe A | `uv run mypy --disallow-any-explicit src` | 11 errors in 8 files | **11 errors in 8 files — unchanged** |
| Rule-9 probe B | `uv run mypy --disallow-any-unimported src` | Success, 0 errors | **Success, 0 errors** |
| Rule-9 probe C | `uv run mypy --disallow-any-expr src` | 228 errors | not re-run; `B3` must re-measure |

**The reported red format gate does not reproduce.** The re-baseline states `ruff format --check src tests` is RED on two `with patch(...)` blocks in `TestYtDlpSubprocessShutdown` inside `tests/test_hls_downloader.py`. Measured at `09f1b10`: **green**, and `ruff format --check --diff tests/test_hls_downloader.py` reports "1 file already formatted". `TestYtDlpSubprocessShutdown` exists and that file gained **302 lines** across the three commits between `58bb7ce` and `09f1b10`, so the claim was plausibly true at `58bb7ce` and is not true now. The narrow-fallback rule is retained in §2.2 and §5.2 regardless, because a later commit can reintroduce it and a blanket reformat remains prohibited.

Notes that constrain how these may be used, unchanged:

- `mypy src` **cannot enforce rule 9.** `ignore_missing_imports = true` is set, so probe B succeeding is not evidence of cleanliness; it is evidence that the gate is invisible. Enforcing rule 9 is `B3`.
- `mypy src tests` is a **delta gate only** — **89** errors / 8 files at this base. Any block adding typed test code moves this number. It is never a pass/fail gate.
- Bare `uv run mypy` has **no default target**. Every invocation in this plan names its target explicitly.
- **The delta rose by exactly 10, and one of the new errors is a facade defect the retirement introduced** — see §2.5 correction 12. `B4` should expect to absorb it.

### 2.2 The skip floor and the warning — re-measured, and the floor has moved

**The skip floor is now 3, not 4. The count was lowered by a landed commit outside this plan, and this plan does not own the change.**

Measured at `09f1b10`, the skips are exactly three D-11 POSIX file-mode oracles, all `skipif(os.name == "nt")`:

| Skip | Test | Subject |
|---|---|---|
| 1 | `tests/test_config.py` — log file created with owner-only permissions | `config.setup_logging` |
| 2 | `tests/test_config.py` — existing log file permissions updated | the same function's re-correction branch |
| 3 | `tests/test_hls_downloader.py` — temp cookie file permissions | `ytdlp_downloader._create_temp_cookie_file` |

The fourth, `test_temp_argfile_permissions_are_0600`, **was deleted by `d572d96` along with its subject `_temp_argfile`**, which the ffmpeg retirement removed. That is why the count fell from 4 to 3. **No block in this plan caused it and no block may reverse it.**

- **The floor is now exactly 3.** No block may raise it. A fourth is review-blocking.
- **Lowering it remains an improvement** in principle, but not by deletion: the three remaining oracles are the only assertions in the suite that check POSIX file modes, and the fourth is now gone with its subject. `G-10` in §5.3 still holds — a skip must never be deleted as tidying, and never converted to a pass on Windows, where the assertion cannot succeed.
- **On Windows these three oracles never execute**, and `os.chmod` toggles only the read-only attribute, so `st_mode & 0o777` measures `0o666`. `create=True` appears **0 times** in `tests/`. No test asserts the `chmod` call is made at all. The exposure is unchanged by the retirement.

**The single warning — the Planner's correction to its attribution is now proven, not argued.** At `4bf9efb` the warning was attributed to `tests/test_exceptions.py::TestMapExceptionToStatus::test_unexpected_exception`, and the Planner showed that file alone emits zero warnings. At `09f1b10` the attribution has **moved**, with no edit to the shim:

```
09f1b10:  RuntimeWarning: coroutine 'Event.wait' was never awaited
          attributed to TestStructuredAttributes::test_status_label_base
          frame: .venv/Lib/site-packages/_pytest/fixtures.py:862  @property
```

The warning tracked a **GC-timing artefact**, not a code path. Both attributions are in `test_exceptions.py`, both name a coroutine the shim never creates, and the frame moved from `inspect.py`'s `_get_signature_of` to pytest's own fixtures module. **Therefore:**

- The warning count is a **ceiling (≤ 1)**, not a target. No block may claim deleting the shim "cleans up the warning" — that claim is unsupported and is now twice contradicted.
- `B1`'s report must not state or imply the warning falls.
- The creator is a `mock`/fixture/signature interaction elsewhere in the suite and is **phase 10's** subject, not this plan's.

### 2.2b The narrow format-fallback rule

If a future commit turns `ruff format --check src tests` red, the remediation is **narrow and named**: the specific blocks named in the re-baseline, inside `TestYtDlpSubprocessShutdown` in `tests/test_hls_downloader.py`, and nothing else.

**Prohibited:** `ruff format src tests`, `ruff format .`, or any reformat of a file outside the named blocks. A blanket reformat would touch every file in the phase's blast radius, convert other agents' in-flight work into this plan's diff, and hide a real change inside whitespace churn. **No block may absorb the format gate silently** — if it is red when a block starts, the block records that fact in its report and either applies the named fix or stops.

### 2.3 Structural measurements taken by the Planner

Measured at `HEAD = 09f1b10`. Where the value moved from `4bf9efb`, the old value is shown.

```
HEAD                                  09f1b10        (4bf9efb -> 58bb7ce -> 09f1b10)
git status                            no modification under src/, tests/, docs/, or pyproject.toml
.py files under src/vkdownloader/     31             (27 non-__init__ modules + 4 package markers)
.py files named in docs/STRUCT.md     29             (+1 non-.py: stealth.min.js)
.py files unnamed in docs/STRUCT.md   2              (models/quality.py, services/ytdlp_downloader.py)

tests/test_packaging.py
  EXPECTED_SDIST_ENTRIES              73            unchanged
  EXPECTED_WHEEL_ENTRIES              32            unchanged
  BUILDER_ADDED_SDIST_ENTRIES          2            unchanged
  EXPECTED_DIST_INFO_ENTRIES           4            unchanged
  of the 73 sdist entries, these are listed:
    docs/STRUCT.md
    docs/00-overview/doc-maintenance-rules.md
    docs/01-tools/vkdownloader-overview.md
    docs/99-reference/cli-reference.md
    docs/99-reference/cli-reference-clean.md
    docs/99-reference/ast-editor.md
    docs/99-reference/morfx-tools.md

PHYSICAL LINE COUNTS
src/vkdownloader/exceptions.py         228          unchanged  <- still zero drift
src/vkdownloader/models/enums.py        92          (93, -1: DownloadMethod.FFMPEG deleted outright)
src/vkdownloader/models/quality.py     113          unchanged
src/vkdownloader/services/downloader_throttle.py  409   unchanged
src/vkdownloader/services/ffmpeg_utils.py         553   (577, -24 net of retirement and two later commits)
src/vkdownloader/services/segment_downloader.py  1283  unchanged
src/vkdownloader/cli.py                            552   unchanged
src/vkdownloader/services/ytdlp_downloader.py     874   (815, +59)
src/vkdownloader/services/downloader.py           344   (690, -346: HLSDownloader and group B gone)
tests/test_exceptions.py                           225   unchanged
tests/test_hls_downloader.py                      4239   (4279, -40)
docs/STRUCT.md                                      52   unchanged

ENUM SHAPE
models/enums.py::DownloadMethod     YTDLP, AUTO  -- 2 members only.
                                       FFMPEG deleted outright, NOT tombstoned. Rule 10 satisfied.
models/enums.py::ErrorCode          8 members, unchanged
  VIDEO_NOT_FOUND, INVALID_URL, QUALITY_NOT_AVAILABLE, QUALITY_PARSE_ERROR,
  EXTRACTION_ERROR, DOWNLOAD_ERROR, PATH_TRAVERSAL, UNEXPECTED_ERROR
  -> no NO_STREAMS member and no NO_STREAMS-shaped value.

DELETION RESIDUE (grep across src/, tests/, docs/, README.md)
  download_with_ffmpeg, HLSDownloader, _temp_argfile, _format_argfile,
  FfmpegProgress, ProgressParser, read_progress            -> 0 hits

PERMANENT SURFACE, confirmed present (ruling A)
  ffmpeg_utils.py: iter_process_lines, cancel_subprocess, cancel_ffmpeg_process (alias),
                   check_ffmpeg_available, _merge_segments_batched
  downloader.py:    the single call site of check_ffmpeg_available is a BARE STATEMENT whose
                   return value is DISCARDED, under the comment about probing once at startup
                   so users learn about a missing binary before a long download fails at merge.
  -> ruling A makes this permanent. It also settles the three-plan disagreement; see §4.4 row 24.

FACADE, services/downloader.py  -- REGRESSED by the retirement
  __all__                          19 entries, ALL UNIQUE   (was 26 entries / 25 unique)
  owned by this module             perform_download, download_video, _semaphore_context
  symbol-ownership comment groups   3  (was 6-7)
  MISSING from the comment          segment_downloader.py, downloader_throttle.py,
                                   cookies.py, signal_handlers.py groups -- while __all__ still
                                   exports 10 names those modules own
  DESYNCHRONISED                   _attempt_segment_resume is named in the ownership comment
                                   as owned by ytdlp_downloader.py but is ABSENT from __all__
                                   -> live mypy src tests error:
                                      Module "vkdownloader.services.downloader" does not
                                      explicitly export attribute "_attempt_segment_resume"
                                   This is a NEW, unfiled facade defect introduced by d572d96.
  STILL OMITS group A              iter_process_lines is imported directly by ytdlp_downloader
                                   and never appears in __all__ or the ownership comment

pyproject.toml  [project]           requires-python = ">=3.12"     (ruling B: becomes ">=3.14")
                [tool.ruff]          target-version = "py312"      SILENT PIN
                [tool.mypy]          python_version = "3.12"       SILENT PIN
                                     strict = true, follow_imports = "silent",
                                     ignore_missing_imports = true,
                                     warn_unused_ignores = true, no plugins
                [[tool.mypy.overrides]]  still exactly ONE entry: module = "vkdownloader.cli"

EXIT CODES in cli.py (ruling C, recorded only)
  distinct values produced: 1 and 130 only.  0 on success, via return.
  2 (usage error) and 3 (configuration error) are UNALLOCATED IN CODE.
  Recorded as plan 13's obligation. QLT-001 is NOT widened.
```

**Load-bearing re-census for `B2` and `B4`:**

```
status_label(                 4 production call sites, all in batch_downloader._download_single
log_context(                  1 production call site,  ExtractionError arm of _download_single
user_message(                 0 production call sites (definition only)
_map_exception_to_status      0 production call sites (module docstring, definition, one comment)
                             14 occurrences in tests/ across TestMapExceptionToStatus and
                             TestExtractionErrorStatusMapping

batch_downloader._download_single   five except clauses. THREE log nothing:
  QualityNotAvailableError  -> returns status_label(), no record
  VideoNotFoundError        -> returns status_label(), no record
  ExtractionError           -> logger.error("extraction_error", **e.log_context())
  VKDownloadError           -> returns status_label(), no record
  Exception                 -> logger.exception("unexpected_error_in_batch_download")

cli.py::download   the ladder has NO VKDownloadError arm. Its terminal arm is
                   except Exception -> logger.exception("download_failed", url=sanitize_url_for_log(url))
cli.py::batch      the same shape; terminal arm logger.exception("batch_download_failed", ...)
cli.py::_PreambleFailure subclasses Exception, NOT VKDownloadError
```

**Load-bearing re-census for `B4` — the retry surface's real fan-in, UNCHANGED by the retirement:**

```
The five retry-policy symbols (RETRYABLE_STATUS_CODES, _retry_429_with_backoff,
_wait_with_shutdown, _compute_backoff_delay, _parse_retry_after) are imported by:

  services/segment_downloader.py   all five, and calls all five directly
  services/ytdlp_downloader.py     _compute_backoff_delay, _wait_with_shutdown
  services/downloader.py           _retry_429_with_backoff  -- re-export, still in __all__ (19 entries)
  tests/test_downloader_throttle.py  ONE from-import block naming five symbols

Separately, downloader_throttle.py is imported by SEVEN modules for
get_shutdown_event and/or URLBackoffCoordinator:
  cli.py, services/batch_downloader.py, services/downloader.py, services/extractor.py,
  services/segment_downloader.py, services/ytdlp_downloader.py, services/signal_handlers.py

tests/ patch() strings binding the retry symbols:  15 -- UNCHANGED from the 4bf9efb count
  downloader_throttle._wait_with_shutdown     3   (test_downloader_throttle, test_hls_downloader x2)
  segment_downloader._retry_429_with_backoff   4   (test_hls_downloader, test_segment_downloader x3)
  segment_downloader._compute_backoff_delay    2   (test_segment_downloader x2)
  segment_downloader._wait_with_shutdown       2   (test_segment_downloader x2)
  ytdlp_downloader._compute_backoff_delay      2   (test_hls_downloader x2)
  ytdlp_downloader._wait_with_shutdown         2   (test_hls_downloader x2)
  -> 3 break on a move (they name downloader_throttle's own namespace)
  -> 12 are move-robust (they name an importing module's re-exported attribute)
```

**Load-bearing re-census for `B11` — the dead-identifier set SHRANK. Full census at `09f1b10`:**

```
src/  (10 sites, 6 identifiers)   INT-008 x1  [downloader_throttle -- NEW, in no artifact]
                                   INT-006 x2  (downloader_throttle, browser)
                                   INT-004 x2  (browser)
                                   INT-003 x3  (extractor)
                                   STR-008 x1  (ffmpeg_utils, on iter_process_lines = GROUP A, SURVIVES)
                                   SRV-006 x1  (ytdlp_downloader)
tests/ (10 sites, 6 identifiers) INT-004 x3  INT-006 x2  INT-003 x2  STR-008 x1
                                   INT-007 x1  ("ffmpeg availability probing" -- SUBJECT IS PERMANENT)
                                   SRV-006 x1  SRV-003 x1  (inline comment in test_downloader_throttle,
                                                             on ProgressManager -- SURVIVES)
docs/ (3 sites, 2 identifiers)   SRV-006 x2  (api-reference, vkdownloader-overview)
                                   SRV-001 x1  (vkdownloader-overview)

GONE from src/ and tests/ entirely -- died with the retirement, no block edits them:
  INT-001   (its download_with_ffmpeg site and tests/test_hls_downloader.py::TestFfmpegCookiePassing)
  INT-005
  SRV-003   (its src sites; ONE survives in a test comment, see above)

B11's scope therefore SHRANK from 11+ identifiers across 4 test files to 8 identifiers
across src/, tests/ and docs/, and every remaining site is SURVIVING.
```

**Load-bearing re-census for `B9` — the two CLI references today:**

```
both files:  id: cli-reference,  related: [configuration-guide, ast-editor]
             neither lists the other
cli-reference.md          284 physical lines, 16 real em-dashes, valid UTF-8
cli-reference-clean.md    283 physical lines,  0 em-dashes, valid UTF-8 whose
                          content is a mojibake transcription of the same document
resolved:    -c short flag      in BOTH files
resolved:    cookie source      both list none|browser; the phantom `file` row is gone from both
resolved:    --ssl-verify       DIVERGENT: cli-reference.md says `verify` (not producible);
                                cli-reference-clean.md says `true`; config.py's default is True
resolved:    batch step list    DIVERGENT: cli-reference.md lists 7, cli-reference-clean.md lists 6
                                cli-reference.md's 7th step (skipped-URL summary) matches the code
both files still document `--method ffmpeg` -- plan 10 B10's surface
one inbound reference to cli-reference-clean.md exists, in
  docs/error-handling-logging-research-2025-2026.md
```

### 2.4 Repository constraints — binding on every block

1. **The packaging frozensets are a single-writer shared anchor.** 73 `EXPECTED_SDIST_ENTRIES`, 32 `EXPECTED_WHEEL_ENTRIES`, verified against a real `uv build`. **Any new file under `src/`, `tests/` or `docs/` — and any deletion of a listed `docs/` file — requires editing the relevant frozenset in the same commit.** Three of this plan's blocks trigger it:
   - `B4` if the retry module is a **new** file → `EXPECTED_WHEEL_ENTRIES` + `EXPECTED_SDIST_ENTRIES` + `BUILDER_ADDED_SDIST_ENTRIES` if it adds a package dir (it does not).
   - `B9` deletes a listed doc → **73 → 72**.
   - `B10` moves two listed docs (count unchanged, names changed) or deletes them (**72 → 70**).
   **`B9` and `B10` both write this frozenset and are therefore serialised.** `B4` and `B10` do not overlap if `B4` creates its new file and `B10` creates none.
   **`.ai/structure/` is NOT packaged** — no `.ai/` entry exists in `EXPECTED_SDIST_ENTRIES`. `B7` therefore carries no frozenset coupling. This is measured, not assumed.
2. **No shared-constants module.** All domain enums live in `models/enums.py`. Do not create one. **Rule 10's `DownloadMethod.FFMPEG` obligation is discharged** — the member was deleted outright with no tombstone (§2.9). No block may reintroduce it, and no block may treat a tombstone as acceptable.
3. **No Polars.** Rule 11 requires it; the project has no dependency for it. **Divergence recorded, dependency not introduced.**
4. **`structlog.get_logger(__name__)` is universal**, against rule 12's stdlib-`logging` wording. **Divergence recorded, matches plan 11 §1.3 item 8.**
5. **The re-export facade is plumbing, never the remedy.** `services/downloader.py` owns 3 names and re-exports 16 behind a 19-entry (all unique) `__all__` and a symbol-ownership comment that **currently has 3 groups and is desynchronised from its own `__all__`** (§2.5 correction 12). **Editing a re-export line is never the fix — the owning module is.** Stated identically in plan 11 and plan 12 and binding here. It constrains `B1` and `B4` directly, and the retirement's own mistake is an instance of the failure this rule exists to prevent.
6. **House style is dense decision-carrying comments** (`D-01`, `SEC-*`, `INT-*`, `STR-008`, `CON-*`, `DF-*`, `ART-*`, `TRN-*`). **A behaviour change must update the comment that justifies it.** Most of this phase is comment and docstring work, so this applies to nearly every block.
7. **`.ai/audit/**` is read-only** for plan execution. Only plan 11 `B10` may touch `.ai/audit/templates/`, and it carries an absolute staging prohibition on `.ai/audit/99-validation/**`.
8. **Commit shape** `{type}({scope}): {description}`. Stage by **explicit path**. Never `git add -A`, `git add .`, `git add -u`. Never amend, never force.
9. **English only** for every comment, log, docstring, error message and document line.
10. **One commit per block**, except where §4 declares a block internally serialised.
11. **One writer per file at a time.** Where two blocks touch the same file, §4 orders them.

### 2.5 Measured corrections to the artifact, the brief, and the rulings — sixteen

These are the figures an Implementor must use. Where they differ from the artifact, from the first-draft brief, or from the re-baseline request, **the measurement is authoritative and the other is wrong.**

| # | Claim | Planner measurement | Consequence |
|---|---|---|---|
| 1 | `docs/STRUCT.md`: 30 `.py` on disk, 28 named | **31 on disk, 29 named, 2 unnamed** (`models/quality.py`, `services/ytdlp_downloader.py`) | `B6`'s row count |
| 2 | `batch_downloader._download_single`: **four** of five clauses log nothing | **THREE of five** log nothing | `B2`'s work is three log calls, not four |
| 3 | 13 `patch()` strings on the retry symbols | **15 strings; 3 break, 12 robust** — **and still 15 at `09f1b10`**, unchanged by the retirement | `B4`'s blast radius |
| 4 | The single pytest warning is caused by the shim's test class | **Proven false twice.** At `4bf9efb` the file alone gave 33 passed / 0 warnings; at `09f1b10` the attribution **moved** to a different test in the same file, with no edit to the shim, and the frame moved to pytest's fixtures module | Warning count is a **ceiling**. `B1` may not claim it falls. Creator is phase 10's |
| 5 | `downloader_throttle.py` holds four concerns that share no caller | Imported by **7 of 31 modules**; `get_shutdown_event` and `URLBackoffCoordinator` are among the most-imported names in the tree | `B4` is not an unused-module extraction; it narrows a spine module. Raises risk and makes `D7` real |
| 6 | `QLT-006` merge direction: take `-c`, cookie source, `true` **and the 7-step list** from `cli-reference-clean.md` | `-c` and cookie source in **both**; `true` in `-clean`; **the 7-step list is in `cli-reference.md`**. All four files still present and unchanged in the retirement | `B9`'s merge is **bidirectional** |
| 7 | `ast-editor.md` is typographically damaged like `cli-reference-clean.md` | `ast-editor.md` is valid UTF-8 with 1 real em-dash. Only `cli-reference-clean.md` is a mojibake transcription (0 em-dashes against 16) | The mojibake argument applies to `-clean` alone |
| 8 | `QLT-005`: three of four line counts within ~1–20% | `~582`→**690**, `~722`→**874**, `~901`→**1283**, `~360`→**553**. **All four wrong.** `vkdownloader-overview.md`'s `downloader.py` count was **partially updated to `~350`** (actual 344) by the retirement; the other three are untouched | Strengthens `D10`'s default. One count is now approximately right, which makes the other three *more* misleading, not less |
| 9 | `--method ffmpeg` and `DownloadMethod.FFMPEG` are deleted, stated as a present-tense fact | At `4bf9efb` the member was still present. **At `09f1b10` the retirement has landed**: `DownloadMethod` has 2 members, and grep for all 7 deleted symbols across `src/`, `tests/`, `docs/`, `README.md` returns **0 hits** | The framing is now correct. **Skip floor fell 4→3** and `B11`'s scope shrank. `ffmpeg_utils.py` is 553 lines, not 577 |
| 10 | The skip floor is 4 | **It is 3.** The fourth oracle, `test_temp_argfile_permissions_are_0600`, was **deleted with its subject `_temp_argfile`** by `d572d96` | §2.2 re-based. **No block may raise it back to 4.** The floor moved for a reason outside this plan |
| 11 | `mypy src tests` is 79 errors in 8 files | **89 errors in 8 files** | §7's delta gate is re-based. `B3` re-measures |
| 12 | (new) — | **The retirement introduced a facade defect.** `services/downloader.py`'s symbol-ownership comment lost four groups (`segment_downloader`, `downloader_throttle`, `cookies`, `signal_handlers`) while `__all__` still exports 10 names those modules own, and `_attempt_segment_resume` is named in the comment but **absent from `__all__`** — producing a live `mypy src tests` error. `__all__` also fell from 26 entries / 25 unique to **19 entries / all unique** | **New, unfiled defect, and it is in this phase's subject matter.** Assigned to `B4` (§3.4) and recorded in §4.4 row 25. It is exactly the "editing a re-export line is never the fix" failure: the retirement edited the re-export surface and left the ownership map desynchronised |
| 13 | Re-baseline: `ruff format --check src tests` is RED on two `with patch(...)` blocks in `TestYtDlpSubprocessShutdown` | **GREEN at `09f1b10`** — "54 files already formatted"; the file alone reports "1 file already formatted". That file gained **302 lines** across the three commits since `58bb7ce` | Not reproducible at this base. The **narrow fallback is retained** anyway (§2.2b) and no block may absorb the gate silently |
| 14 | Re-baseline: HEAD is `58bb7ce` | **HEAD is `09f1b10`**, three commits later. `58bb7ce` is an ancestor. `b0fb032`, `db0e33e`, `09f1b10` touched `ffmpeg_utils.py` (+63/−3), `ytdlp_downloader.py` (+48/−19), `url_sanitizer.py`, `test_hls_downloader.py` (+302/−7), `test_url_sanitizer.py` (+20) | Every §2 figure is measured at `09f1b10`. `ffmpeg_utils.py`'s size is the net of the retirement and these two later commits |
| 15 | Ruling B: a 3.14 target may change which pydantic-inherited `__init__(**data: Any)` signatures surface, so `QLT-009` may be partly self-resolving | **`--disallow-any-explicit src` is still 11 errors in 8 files — the count did not move.** Identical file set; only one line number shifted (`ytdlp_downloader.py`, +5). `models/enums.py` shrank by one line and the count is unchanged | **`QLT-009` is NOT self-resolving.** `B3`'s override decision stands unchanged |
| 16 | Ruling C: an exit-code contract exists | **`cli.py` produces only `1` and `130`** (plus `0` by return). **`2` and `3` are unallocated in code.** | Recorded as plan 13's obligation. `QLT-001` is **not widened**; it stays internal-consistency |
| 17 | (new) — | **The retirement left two false facts in `vkdownloader-overview.md` that no plan owns.** Its `--method` row still lists `ffmpeg` as a value, and its `services/` listing still describes `ffmpeg_utils.py` as including "progress parsing" — group B, deleted, on a module ruling A makes permanent. `cli.py`'s own help was updated; this document was not | **Assigned to `B8`** (§3.8 criteria 2 and 3, §4.4 row 12). Plan 10 has landed and is no longer an owner; these are in the file `B8` edits and neither is in `docs/STRUCT.md`, so §4.3's yield is untouched |
| 18 | (new) — | **The retirement introduced a fourth divergence between the two CLI references.** `cli-reference-clean.md` retains a `--method ffmpeg` usage example that `cli-reference.md` no longer has | `B9`'s merge census grows from three divergences to four (§3.9, §4.4 row 12b). The example dies with the deleted file |

### 2.9 The rulings' enforcement evidence, recorded for handover

Rulings A–D are decisions. What follows is what this phase **measured about their enforcement**, which is what the owning plans need and what only this phase's gates produce.

**Ruling A — ffmpeg.** Measured: group A (`iter_process_lines`, `cancel_subprocess`, `cancel_ffmpeg_process`) present; `check_ffmpeg_available` present with a single bare-statement call site whose return value is discarded; the group C merge engine present and unchanged; group B and the loader path gone with **zero residue**; `DownloadMethod` has 2 members with **no tombstone**. `ffmpeg_utils.py` is 553 lines and is permanent product code. **Handover:** plan 12's `P12-B12` owns the `docs/STRUCT.md` sentence, and that sentence is now wrong about a permanent module — "discovery" names a permanent function, and the row omits both surviving groups. This plan does not write it (§4.3).

**Ruling B — Python floor.** Measured enforcement evidence, all three pins present and mutually inconsistent with the new floor:

| Declaration | Location | Value at `09f1b10` | Status |
|---|---|---|---|
| The package's supported floor | `[project] requires-python` | `>=3.12` | Plan 16's to change |
| The linter's target | `[tool.ruff] target-version` | `py312` | **Silent pin — nobody owns it today** |
| The type checker's target | `[tool.mypy] python_version` | `3.12` | **Silent pin — nobody owns it today** |

**Neither silent pin produces any error if left behind.** A linter and a type checker will happily analyse a 3.14 package as 3.12, which means the floor can be raised while the checks still validate the old language. That is the "declare it in one place, enforced nowhere" class of defect this phase exists to find, and it sits in `pyproject.toml`, which `B3` already touches. **Decision `D16` assigns both pins to `B3`**; the reasoning and the reconciliation rule are in §3.3 and §4.5.

**Ruling C — exit code contract.** Measured: `0` on success by return; `1` for download failure; `130` for cancellation; **no `2` and no `3` anywhere in `cli.py`.** The contract's four codes are therefore **recorded and unimplemented**, and `4`+ is unallocated as stated. This is plan 13's obligation. **`QLT-001` is not widened.** Its subject — `status_label()`, `error_code`, and the internal agreement between them — is an internal-consistency finding and stays one. The only thing this phase records is that `status_label()`'s values are **not** exit codes and must not be conflated with them: `QLT-001`'s `D1` decision changes what a batch summary prints, and adding `ErrorCode.NO_STREAMS` must not be justified as a status-code change.

**Ruling D — not published.** Measured effect on two findings:

| Finding | Depends on publication? | Value when nothing is published |
|---|---|---|
| `QLT-008` — two agent-tooling documents in `docs/99-reference/` | **No.** Both are listed in `EXPECTED_SDIST_ENTRIES`, and `tests/test_packaging.py` verifies both frozensets against a **real `uv build`** — 73 / 32 / 2 / 4, all unchanged. The sdist is still built and still asserted | **Unchanged.** The finding is about misplacement inside a repository whose own maintenance rules govern `docs/`, not about a published artifact. The frozenset coupling that makes `B10` risky is entirely internal |
| `QLT-005` — the export census across nine `__all__` lists | **Weakly.** Its subject is what a wheel's public surface actually is. `EXPECTED_WHEEL_ENTRIES` is asserted against a real build | **Reduced, but not zero.** With nothing published, the census is internal hygiene: it matters because the facade's `__all__` is what 30+ **test** import sites resolve through, not because a consumer imports it. `B8`'s scope is unchanged |

Nothing in ruling D requires an edit. It changes the **severity rationale** recorded for `QLT-005` from "consumers get a wrong public surface" to "the project's own test tree resolves through a surface the documentation misdescribes", and that is recorded in `B8`'s report requirement.

### 2.6 Oracle gaps — a refactor in these subjects passes silently

No test exists for any of the following. Each is a live hazard for the block that touches it:

| Gap | Exposed by |
|---|---|
| No test asserts `iter_process_lines` / `cancel_subprocess` are reachable from `ytdlp_downloader` | An `ffmpeg_utils.py` decomposition breaks group A and nothing fails. **No block here does that decomposition**, but the gap is recorded because group A must survive |
| No test asserts `models/enums.py` is the only enum module | Rule 10 is unenforced; `B1`'s `ErrorCode` addition is unchecked against a second enum module |
| No test asserts `status_label()` values equal `ErrorCode` values | **`QLT-010`'s own gap.** `B1` closes it and must therefore also add the assertion — see `B1`'s acceptance criterion 4 |
| No test asserts `docs/STRUCT.md` matches the filesystem | **`B6`'s own correctness is unverified by the suite.** `B6` must verify by enumeration, and record the enumeration |
| No test covers `models/quality.py::QualitySpec.parse` returning `QualityKind.EXACT` for `"unknown"` | `B6` documents a behaviour nothing pins |
| No test asserts import-form uniformity, by design | Both relative and absolute forms pass both gates, so `B12` is a documentation-correctness task with no code oracle |
| No test asserts `get_shutdown_event` is reachable from its 7 importers | `B4` moves code out of its module; a botched import fails at runtime, not at collection, in the paths that only call it inside a coroutine |
| `create=True` appears **0** times in `tests/` | No test creates a missing attribute on demand |

### 2.7 The landing rule

A block lands when its acceptance criteria are met, its per-block gate is green, **and its report states which measured facts in §2.3 it re-measured before editing.** Any block that discovers a §2.3 figure has moved records the new figure and re-derives its own scope from symbols; no block re-anchors on a line number to "confirm" a citation.

### 2.8 Test layout — the subject areas in this plan

| File | Lines | Classes that bind this phase's subjects |
|---|---|---|
| `tests/test_exceptions.py` | 225 | `TestMapExceptionToStatus` (the legacy shim; **the suite's only warning site — and §2.2 shows the warning is not its fault**), `TestStructuredAttributes`, `TestStatusLabel` (8 hard-coded label literals), `TestExtractionErrorStatusMapping` |
| `tests/test_downloader_throttle.py` | 895 | `TestRetry429WithBackoff`, `TestParseRetryAfter`, `TestComputeBackoffDelay` (incl. `test_retry_after_overrides_delay` and `test_retry_after_ignored_when_smaller`), `TestWaitWithShutdown`, `TestRetryableStatusCodes` (9 membership assertions incl. 408 and 425), `TestProgressManager` (6 instantiations), `TestBackoffPauseDuration`, and the single `from`-import block naming five retry symbols |
| `tests/test_hls_downloader.py` | 4239 | `TestYtdlpRetryBackoff` (`SRV-006`; patches `ytdlp_downloader._compute_backoff_delay` / `._wait_with_shutdown`), `TestIterProcessLines` (`STR-008`), **`TestYtDlpSubprocessShutdown`** (the class §2.2b's narrow format fallback names), `TestCreateTempCookieFile` (**the one remaining skip**), 5 retry-symbol patch strings. **`TestFfmpegCookiePassing`, `TestTempArgfile`, `TestSslVerifyFfmpegWarning`, `TestFfmpegProgress`, `TestProgressParser`, `TestReadProgress` and `TestHLSDownloader` were all deleted by `d572d96`**, taking 7 of this phase's citation sites with them |
| `tests/test_segment_downloader.py` | 1705 | `TestPreserveSegmentsReporter`, `TestSequentialSharesThePause`, `TestManifestRetryComputesBackoffDelay` (4 `segment_downloader.*` patches; patches **both** backoff symbols, so it would not notice a change to the `Retry-After` floor) |
| `tests/test_cli.py` | 2391 | `assert not hasattr(batch_downloader, "ProgressManager")` — the reachability oracle that keeps `ProgressManager` documented-as-retained rather than filed as dead code |
| `tests/test_packaging.py` | 581 | `EXPECTED_SDIST_ENTRIES` (73), `EXPECTED_WHEEL_ENTRIES` (32), `BUILDER_ADDED_SDIST_ENTRIES` (2), `EXPECTED_DIST_INFO_ENTRIES` (4) — **all four unchanged at `09f1b10`, and the lock is two-way: a deletion that skips an edit turns the suite red for a reason that reads like a broken fix** |
| `tests/test_config.py` | 1223 | `setup_logging` tests; **skips 1 and 2 — two of the three remaining** |

---

## 3. Execution blocks

Thirteen blocks. Each states: goal, exact semantic scope by symbol only, the alternatives where technical uncertainty exists with the decision criterion, acceptance criteria, out-of-scope, and the agent roster with the reason the roster is what it is.

**Decision IDs `D1`–`D15` are referenced from §4 and §7. Each carries a default; the default is what happens if the Implementor is given no instruction.**

---

### 3.1 `B1` — one derivation in `exceptions.py`, and the legacy shim's exit (`QLT-001` + `QLT-010`)

**Goal.** Make `VKDownloadError.status_label()` derive its value from `ErrorCode` exactly once, make every label an `ErrorCode` member value, and retire the legacy `_map_exception_to_status` shim together with its two test classes — as **one change**, discharging `VAL-903`'s ordering constraint.

**Semantic scope.**
- `VKDownloadError.status_label` — the sole derivation site.
- The six subclass overrides of `status_label`: on `VideoNotFoundError`, `InvalidVideoUrlError`, `QualityNotAvailableError`, `QualityParseError`, `ExtractionError`, `DownloadError`.
- `models/enums.py::ErrorCode` — member set. Adding `NO_STREAMS` is within scope; renaming or removing any member is not.
- `exceptions.py` module docstring, which currently advertises the shim as retained-for-backward-compatibility and directs new call sites at `status_label()`.
- `exceptions.py::_map_exception_to_status`, `exceptions.py::_quality_not_available_status`, `exceptions.py::_EXCEPTION_STATUS_HANDLERS`.
- The `Callable` import in `exceptions.py`, if `B3` widens this block's scope to the narrowing annotation (§3.3, `B3`'s shared hunk — **one commit, both edits**).
- `tests/test_exceptions.py::TestStatusLabel`, `::TestMapExceptionToStatus`, `::TestExtractionErrorStatusMapping`, and the module's `from vkdownloader.exceptions import _map_exception_to_status` statement.
- `batch_downloader._download_single`'s `except VKDownloadError` arm — **re-read only.** Its comment asserts the earlier clauses are "the documented replacement for the legacy `_map_exception_to_status` helper"; if `B1` deletes the shim, that comment must stop naming a symbol that no longer exists. No behaviour change to the arm.

**Why merged, not separate.** `VAL-903` records `exceptions.py` and `tests/test_exceptions.py` as a shared edit region with no competing claim — the only such region in the corpus. Two commits over it produce a transient state where `ErrorCode` carries a member no `status_label()` can produce, or where `status_label()` returns a value no `ErrorCode` names.

**Alternatives.**

- **`D1` — the label shape.** *Default: add `ErrorCode.NO_STREAMS` and keep exactly one derivation override, on `QualityNotAvailableError`, returning `ErrorCode.NO_STREAMS.value` when `available` is empty and `ErrorCode.QUALITY_NOT_AVAILABLE.value` otherwise. The other five overrides are deleted.* Alternative: **one label for both conditions** — add nothing, delete all six overrides, and let `QualityNotAvailableError.error_code` alone decide. *Criterion:* does `no_streams` have committed consumers? **It does** — it is asserted in `tests/test_exceptions.py` and is the string `batch_downloader._download_single` returns into the batch summary. Choosing the one-label option is defensible if the reviewer judges the batch output change acceptable and prefers the smaller enum; it is then a **deliberate, reported** user-visible change, not an accident.
- **`D2` — shim removal, same commit or a follow-up.** *Default: same commit.* Alternative: land the label derivation first, the shim's deletion second. *Criterion:* would a two-commit split be independently reviewable? No — both edits touch the same 11-line region of `exceptions.py` and the same two test classes, and `VAL-903` exists precisely to prevent the region being contended. One commit.
- **A third path exists and is rejected here:** repoint the 11 test call sites at `status_label()` and keep the shim. Rejected because the shim's output shape (`"<label>: <message>"`) is a second, incompatible status grammar with zero production consumers, and keeping it preserves the very divergence `QLT-001` files.

**Acceptance criteria.**
1. `VKDownloadError.status_label` is the only place a label is derived, except for the single `D1`-default override, which returns `ErrorCode` member values on both branches.
2. Every value `status_label()` can return is `some(ErrorCode).value` for some member of `ErrorCode`. No bare string literal appears in any `status_label` body.
3. `QualityParseError`'s divergence is closed: its label equals `ErrorCode.QUALITY_PARSE_ERROR.value`, not `"invalid_quality"`.
4. **`tests/test_exceptions.py` gains an assertion that closes `QLT-010`'s own oracle gap** (§2.6): for every exception class, `status_label()` returns that class's `error_code.value`, or a documented member listed for the one permitted override. This is the test that stops the defect from recurring, and the finding's own claim is that none exists.
5. `_map_exception_to_status`, `_quality_not_available_status` and `_EXCEPTION_STATUS_HANDLERS` are gone; `tests/test_exceptions.py` contains no reference to any of them; no test class name remains that exists only to exercise them.
6. The `exceptions.py` module docstring no longer advertises the shim, and every comment or docstring in `src/` that names `_map_exception_to_status` is updated in the same commit. The one known site is `batch_downloader._download_single`'s terminal-arm comment.
7. `grep` over `src/` for `_map_exception_to_status` returns **0** hits.
8. `batch_downloader._download_single` returns the same strings it returns today for every input it handles today. Verified by running its own test class before and after, not by inspection.
9. The `exceptions.py` module docstring's `status_label()` format description matches the implementation.
10. Gate: `uv run pytest -q -rs` → **759±n passed, 3 skipped, ≤1 warning**. The skip count is unchanged at **3** and the warning count does not rise. **`B1` does not claim the warning falls** (§2.2 — the attribution moved base to base, proving it a GC artefact).
11. `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run mypy src` → clean.
12. One commit, `{type}(exceptions): {description}`, explicit paths only.

**Out of scope.** `VKDownloadError.log_context` and `user_message` (those are `B2`'s). `models/enums.py`'s other enums. `batch_downloader._download_single`'s arm bodies. Anything in `tests/test_hls_downloader.py`, `tests/test_segment_downloader.py`, `tests/test_downloader_throttle.py`. The `ErrorCode` **values** of existing members.

**Agent roster — Auditor, Planner, Validator.** Auditor: the block deletes a symbol with 11 live call sites and must confirm at execution time that no production consumer has appeared since measurement; the shim is the kind of thing that grows. Planner: `D1` is a genuine design choice between a smaller enum and a preserved output contract, and it propagates into `B6`'s `exceptions.py` row and `B2`'s arm bodies — that propagation needs designing, not implementing. Validator: HIGH risk, a shared uncontested edit region, and a user-visible string in the batch summary with no oracle beyond the tests this block rewrites. **No Researcher** — no library, framework or best-practice question is involved.

---

### 3.2 `B2` — the exception ladder logs nothing it classifies (`QLT-002`)

**Goal.** Give every exception clause in the two ladders a log record that carries the structured context the code already computes, and remove the three silent outcomes in `batch_downloader._download_single`.

**Semantic scope.**
- `cli.py::download` — the `except` ladder. Add a `VKDownloadError` arm **between the `except typer.Exit` re-raise arm and the terminal `except Exception` arm**, logging `event="download_failed"` with `url=sanitize_url_for_log(url)` and `**e.log_context()`. The arm's placement is forced: `_PreambleFailure` subclasses `Exception`, **not** `VKDownloadError`, so placing the new arm before `_PreambleFailure` would swallow it; placing it before `except typer.Exit` would catch `typer.Exit`.
- `cli.py::batch` — the same shape, same placement rule, event `"batch_download_failed"`.
- `batch_downloader._download_single` — `except QualityNotAvailableError`, `except VideoNotFoundError`, and `except VKDownloadError`: **three** arms gain `logger.error` with the same event/URL/`log_context()` shape `ExtractionError` already uses. Per §2.5 correction 2 the count is three, not four.
- `VKDownloadError.user_message` — zero production callers. Within scope as a **presentation path for the two new `cli.py` arms**; its deletion is not.
- `batch_downloader._download_single`'s existing `except ExtractionError` arm — re-read for shape consistency only.
- `tests/test_cli.py` — additions asserting each new arm emits a record. Existing expectations are not changed; a changed expectation is an escalation, not an update.

**Alternatives.**

- **`D3` — `logger.error`, `logger.exception`, or `logger.error(..., exc_info=True)` for the new `cli.py::download` arm.** *Default: `logger.error`.* Alternative: `logger.exception` to preserve today's traceback on the record, or `logger.error(..., exc_info=True)` for the same effect with a non-exception-level event. *Criterion:* phase 08's `OUT-002` evidence is a captured JSON record with `event: "download_failed"`, `level: "error"` **and** an `exception` field carrying the rendered traceback. `OUT-002`'s whole claim is that one exception is rendered twice, and its remediation adds a processor in `setup_logging`. If phase 08's plan is written against that record shape, `logger.error` **changes the evidence that finding rests on**, and the correct choice is `exc_info=True` or `logger.exception`. **This is the highest-value open decision in `B2`** and it must be settled against phase 08's artifact, not by taste.
- **`D4` — `user_message()`: adopt or delete.** *Default: adopt* — use it as the user-facing text of the two new `cli.py` arms, which gives the method its first production caller for one line of code and keeps the presentation string out of the ladder bodies. Alternative: delete it as unreachable. *Criterion:* is it a declared public API surface? It is not in any `__all__`, has no caller, and is documented nowhere. Deletion is defensible; adopting is strictly cheaper and reversible, so adopt unless the reviewer judges the method itself misleading.
- **A third option is rejected:** put the new `VKDownloadError` arm *first* in the ladder, catching everything domain-specific at once. Rejected because it would displace the four hand-written user-facing messages, several of which carry deliberate wording — including one whose comment explains why a `"p"` suffix is not appended to a non-numeric token — and collapsing them is a UX change no finding asked for.

**Acceptance criteria.**
1. Every clause of both `cli.py` ladders and all five clauses of `batch_downloader._download_single` emit a log record. No clause returns a status tuple or an exit code silently.
2. The new `cli.py::download` arm is placed after `except typer.Exit: raise` and after `except _PreambleFailure`. Verified by reading the ladder, not by a test.
3. Both new `cli.py` arms reuse the **existing event names** (`download_failed`, `batch_download_failed`) so plan 11's redaction rules and any existing filter continue to bind, and so plan 11's sixteen-record inventory does not need amending.
4. `D3` is settled explicitly and recorded, with the reason. If `exc_info` is retained, the record keeps an `exception` field.
5. Each new record carries `url=` sanitised through `sanitize_url_for_log` and `**e.log_context()`, so `error_code` and `message` are present. No record contains a raw URL.
6. The four hand-written user-facing messages in `cli.py::download`'s ladder are byte-identical after the change, and `_PreambleFailure`'s renderer is not displaced.
7. `batch_downloader._download_single` returns the **same status tuples** it returns today for every input. Run its own test class before and after.
8. `tests/test_cli.py` gains coverage asserting a record is emitted on each new arm. Additions only.
9. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning, no new failures. `ruff`, `ruff format --check`, `mypy src` → clean. **Per ruling C, recorded only:** `cli.py` currently produces `1` and `130` and nothing else; this block adds no exit code and `QLT-001` is not widened into a contract change. The new `VKDownloadError` arm must `raise typer.Exit(code=1)` like its neighbours and must not introduce `2` or `3`.
10. **Plan 11 `B6` has landed.** Its acceptance criterion 3 ("both `logger.exception` sites in `cli.py` are covered without any edit to `cli.py`") constrains `B6`'s implementation, not this block's file access; but its sixteen-record inventory must not be stale when `B2` lands. §4 serialises `B2` after `P11-B6` for that reason.

**Out of scope.** `except typer.Exit`, `except (KeyboardInterrupt, asyncio.CancelledError)`, `except ValidationError`, `except _PreambleFailure` in either ladder — none may be reordered, renarrowed or removed. `batch_downloader`'s status-tuple grammar. `log_context`'s implementation. `config.setup_logging` (plan 11's). `utils/security.py` (plan 12's).

**Agent roster — Auditor, Planner, Validator.** Auditor: `D3` turns on a claim about a *different* phase's evidence record, and the ladder's current shape plus `_PreambleFailure`'s base class must be confirmed at execution time rather than inherited. Planner: the placement constraint is a real ordering problem with one correct answer and two wrong ones, and `D4` couples a new code path to an existing method's purpose. Validator: HIGH risk — the block touches the two files plan 11 also touches, changes an observability surface phase 08 has already filed on, and has no oracle for "a clause that logs nothing".

**No Researcher** — no external best-practice question.

---

### 3.3 `B3` — make rule 9 enforceable, and remove the five real `Any` (`QLT-009`)

**Goal.** Turn rule 9 from prose into a gate: enable a `disallow_any_explicit` check, and eliminate the explicit `Any` annotations the product's own types control — accepting a documented, narrow exemption for Pydantic-inherited ones, or removing them too. **Additionally, reconcile the two silent toolchain pins so that ruling B's floor is enforced rather than declared.**

**Re-measured at `09f1b10`:** `--disallow-any-explicit src` is **still 11 errors in 8 files — the count did not move**, with the identical file set. **`QLT-009` is not partly self-resolving** (§2.5 correction 15). Only one line number shifted, in `ytdlp_downloader.py`, because the retirement deleted lines above it. `B3`'s override decision stands exactly as first written.

**Semantic scope.**
- `pyproject.toml` `[tool.mypy]` — add the `disallow_any_explicit` flag; add `[[tool.mypy.overrides]]` entries as `D5` requires; **merge into the existing `vkdownloader.cli` override rather than adding a second one for the same module**, because mypy rejects duplicate override modules.
- `exceptions.py::_EXCEPTION_STATUS_HANDLERS` — the `Callable[..., str]` annotation. If `B1` deleted the dict, there is nothing to narrow; `B3` re-measures and reports that.
- `models/video.py` — three explicit `Any` annotations.
- `models/dtos.py` — one. `models/quality.py` — one, on `QualitySpec.__init__(**data: Any)`.
- `config.py` — one, on the settings model.
- `services/extractor.py` — two, on `_declares_video_codec` and `_build_streams`. **The artifact never listed these**; they are in scope.
- `services/ytdlp_downloader.py` — one, on `_partition_tasks`.
- `cli.py::_quality_option` — one, and it is **new since validation** (the artifact's "brand-new"). The return is a `typer.Option` whose declared type is not nameable as an annotation; the honest signature is `typer.models.OptionInfo`, which is what a Typer option factory returns.
- `tests/` — two `# type: ignore` comments exist today. **The artifact's "0" is false.** They are counted, not touched.
- **`[tool.ruff] target-version` and `[tool.mypy] python_version`** — both pinned to `py312` / `"3.12"` while ruling B moves `requires-python` to `>=3.14`. **In scope per `D16`.** Both are silent pins: neither produces an error if left behind, so a raised floor can coexist with checks that still validate the old language. Measured in §2.9.
- `[project] requires-python` — **plan 16's to change. Out of this block's scope**, except for `D16`'s reconciliation rule: if plan 16 lands first, `B3` re-measures and reconciles all three declarations to one value.

**Alternatives.**

- **`D5` — global flag with overrides, versus per-module gradual enablement.** *Default: enable `disallow_any_explicit` globally in `[tool.mypy]`, with an override for `vkdownloader.models.*` and for `vkdownloader.config`, and merge into `vkdownloader.cli`'s existing override.* Alternative: enable it per-module, which is strictly more overrides and the same total work. *Criterion:* **can the six Pydantic-inherited sites be removed at source instead?** `__init__(**data: Any)` on a `BaseModel` subclass is Pydantic's own signature; narrowing it means either `model_config`/annotation work on every field or an inline disable comment. If the Auditor finds the six removable, no override is needed and the gate is materially cleaner — **prefer that outcome and say so.** If they are not removable, the override is not a compromise, it is the correct description of a third-party signature.
- **`D6` — `ignore_missing_imports`.** *Default: OUT, unchanged.* *Criterion:* is `yt_dlp` to be typed in this phase? It is not. Turning the flag off surfaces `yt_dlp` as untyped and buys nothing; recording the divergence is the honest outcome.
- **`D16` — the two silent toolchain pins.** *Default: `B3` owns both `[tool.ruff] target-version` and `[tool.mypy] python_version`, setting each to the floor ruling B establishes.* Alternative: plan 16 owns all three declarations together, and `B3` leaves them alone. *Criterion:* **`B3` is the only block in this plan that touches `pyproject.toml`, and these pins are the same species of defect as `QLT-009` — declared in one place, enforced nowhere.** Leaving them behind after plan 16 raises `requires-python` to `>=3.14` produces a package that claims 3.14 while both its linter and its type checker validate 3.12, which is a state nobody has assigned an owner. The reconciliation rule: **whichever of plan 16 or `B3` lands second re-measures all three declarations and sets them to one value.** If plan 16 has already reconciled both pins when `B3` starts, `B3` records that and does not re-edit them — re-measure, never inherit.
- **A rejected option:** a `# mypy: disable-error-code="explicit-any"` per site instead of an override. Rejected because `warn_unused_ignores = true` makes every such comment self-invalidating the moment the annotation is fixed, and because per-site suppression is not enforcement — the gate would pass with 11 suppressions in place.

**Acceptance criteria.**
1. `uv run mypy --disallow-any-explicit src` → **0 errors in `src/`**, either because the flag is now on permanently in `[tool.mypy]` or because every reported site is covered by a named override whose reason is written in a comment.
2. `uv run mypy src` remains clean, still over 31 source files.
3. Every override entry carries a comment naming **which** Pydantic or third-party signature requires it and what would remove it. An override with no reason is not acceptable.
4. No override module is duplicated; `vkdownloader.cli` has exactly one entry, carrying both its original `disallow_untyped_decorators = false` and any `disallow_any_explicit = false` the decision requires.
5. The five real explicit `Any` are gone or converted to a precise type. `cli.py::_quality_option` in particular is annotated with a nameable Typer type, not `Any`.
6. The `tests/` `# type: ignore` count is recorded before and after, and any new one is justified.
7. `uv run mypy src tests` is reported as a **delta** against **89 errors / 8 files** at this base, with the direction stated. It is not a gate.
8. `uv run pytest -q -rs` → **3 skipped**, ≤1 warning. `ruff check src tests`, `ruff format --check src tests`, `ruff check .` → clean.
9. **Per `D16`: `[tool.ruff] target-version` and `[tool.mypy] python_version` no longer name a language older than `requires-python`,** or `B3`'s report records that plan 16 already reconciled them and `B3` did not re-edit them. **All three declarations must agree at the end of this block's commit.**
10. `pyproject.toml` is the only file changed outside `src/`. No new file, therefore **no frozenset edit**.
11. One commit, `{type}(types): {description}`, explicit paths.

**Out of scope.** `tests/` typing in general — the 89-error delta is not this block's work. `follow_imports`, `strict`, `warn_unused_configs`, `warn_redundant_casts`, `disallow_untyped_defs` and every other existing flag. `ruff`'s own rules. Adding type stubs. `[project] requires-python` — plan 16's, except for `D16`'s reconciliation rule.

**Agent roster — Researcher, Planner, Validator.** Researcher: this is genuinely a library-semantics question — per-module override wildcard matching, whether `disallow_any_explicit` is additive under `strict`, whether the Pydantic-inherited `__init__(**data: Any)` can be narrowed without upstream support, the `warn_unused_ignores` interaction, and **which `target-version` and `python_version` values correspond to a 3.14 floor in each tool**. **The one block in this plan where an external-documentation answer changes the implementation.** Planner: three override groups plus five source conversions plus a `Callable` annotation that may or may not still exist after `B1`, with `B1` and `B2` both upstream, plus `D16`'s three-way reconciliation. Validator: `pyproject.toml` is a **shared configuration file** — the blast radius of a wrong override pattern is every subsequent type check in the repository, and `D16`'s blast radius is every subsequent lint and type run against a language the package no longer claims. The finding has already been measured wrong twice.

**No Auditor** — the measurement is complete and unambiguous (11 errors in 8 files, re-run), and no uncertainty requires deeper code investigation. If `D5`'s source-removal question needs investigation, that is the Researcher's scope.

---

### 3.4 `B4` — split `downloader_throttle.py` at the concern that has no caller of its own (`QLT-011`)

**Goal.** Move the HTTP retry policy out of `downloader_throttle.py` into a module named for what it does, leaving behind the process-wide shutdown signalling, the shared backoff coordinator and `ProgressManager` — and update the four production importers, the facade, the documentation row and the test patch targets correctly.

**Why this block's risk is High, not Medium.** The artifact's premise is that `downloader_throttle.py` holds four concerns that share no state and no caller. §2.5 correction 5 refutes the second half: the module is **imported by 7 of 31 modules** for `get_shutdown_event` and `URLBackoffCoordinator`, which are among the most-imported names in the tree, and `cli.py` — the entry layer — imports it. This is not an unused-module extraction. It is a narrowing of a spine module, and the naming question that follows from that is `D7`.

**Semantic scope.**
- **Moving** (retry policy): `RETRYABLE_STATUS_CODES`, `_retry_429_with_backoff`, `_parse_retry_after`, `_compute_backoff_delay`, `_wait_with_shutdown`.
- **Staying** (shutdown signalling and coordination): `_shutdown_event_ctx`, `get_shutdown_event`, `URLBackoffCoordinator`, `ProgressManager`, `_resource_key` (it is `URLBackoffCoordinator`'s origin-key normaliser, not retry policy), and the pause/transport-failure constants that belong to the coordinator.
- **The new module** and its name — `D7`.
- `services/segment_downloader.py`'s import block and its five call sites.
- `services/ytdlp_downloader.py`'s import block and its two call sites.
- `services/downloader.py`'s re-export of `_retry_429_with_backoff` — the import, the `__all__` entry, **and the symbol-ownership comment**. Per §2.4 item 5, **the owning module is the fix; the facade's re-export line is not edited as a remedy** — the facade is updated to point at the new owner, which is a consequence of the move, not a substitute for it.
- **`services/downloader.py`'s facade defect, inherited from the retirement — new, unfiled (§2.5 correction 12).** The symbol-ownership comment lost four groups (`segment_downloader`, `downloader_throttle`, `cookies`, `signal_handlers`) while `__all__` still exports 10 names those modules own; and `_attempt_segment_resume` is named in the comment as owned by `ytdlp_downloader.py` but is **absent from `__all__`**, producing a live `mypy src tests` error. **This is `B4`'s to fix**, because `B4` already edits both the comment and `__all__`, and because it is precisely the failure §2.4 item 5 exists to prevent — a re-export surface edited without its ownership map. The comment must be restored to name every module that owns an exported name, and `_attempt_segment_resume` must be either added to `__all__` or removed from the comment, whichever matches whether `ytdlp_downloader.py` still exports it deliberately.
- `tests/test_downloader_throttle.py`'s single `from`-import block naming the five moved symbols.
- **15 `patch()` strings** in `tests/test_downloader_throttle.py`, `tests/test_hls_downloader.py` and `tests/test_segment_downloader.py` (§2.3). **3** name `downloader_throttle`'s own namespace and must be repointed; **12** name an importing module's re-exported attribute and **must not be changed** — rewriting them would be churn that also breaks any test that patches the attribute for a reason unrelated to location.
- `docs/01-tools/api-reference.md`'s `RETRYABLE_STATUS_CODES` row — **currently documents a 5-member set against a live 7-member `frozenset`.** This is a new false fact the artifact's drift table records as introduced by phase-03/04 work and never filed. Correcting it is in scope **because the constant moves** — `D8`.
- `docs/STRUCT.md`'s `downloader_throttle.py` row — **not written here.** `B6` writes it, after `B4`, so the row describes the post-split tree. §4 makes `B6` depend on `B4` for exactly this row.
- `tests/test_packaging.py` — if `D7` creates a new file under `src/`, the relevant frozenset is edited **in this commit**.

**Alternatives.**

- **`D7` — the naming.** *Default: the retry policy moves to a new module named for retrying, and `downloader_throttle.py` keeps its name.* Alternative: the residue is renamed to a shutdown-named module and the retry module takes the vacated name. *Criterion:* the residue has **7** importers. Renaming it converts a 5-importer change into a 12-importer change and puts `cli.py`, `signal_handlers.py`, `batch_downloader.py` and `extractor.py` in the blast radius for a name change that is not the finding. Renaming only pays if the residue's honest name is worth 7 extra import edits — which is a judgement about the project's vocabulary, and the project already accepts `downloader_throttle.py` as a name.
- **`D8` — the constant and its stale documentation.** *Default: `RETRYABLE_STATUS_CODES` moves with the retry policy, and `api-reference.md`'s row is corrected in the same commit.* Alternative: the constant stays in `downloader_throttle.py` and is imported by the new module. *Criterion:* a constant that travels with the code that uses it is the right default, and `TestRetryableStatusCodes` asserts 9 membership facts including `408` and `425` — so a doc edit in the same commit is not optional tidiness, it is the only way the documented value stays true while the value is being moved. Reject "fix the doc later": the constant's 7 members are asserted, the doc's 5 are not, and the drift recurs.
- **A rejected option:** split **three** ways — a shutdown module, a coordinator module, and a retry module. Rejected: `ProgressManager` is documented-as-retained with 6 test instantiations and `tests/test_cli.py` asserts its **absence** from `batch_downloader`; splitting it out would force a decision about its future that no finding asks for, and `QLT-011`'s own remedy proposes exactly two modules.
- **A rejected option:** move `ProgressManager` into the new module as "dead-adjacent". Rejected by measurement — see §2.6.

**Acceptance criteria.**
1. The five retry symbols are defined in exactly one module. `_retry_429_with_backoff`, `_wait_with_shutdown`, `_compute_backoff_delay`, `_parse_retry_after`, `RETRYABLE_STATUS_CODES` each resolve to the new module.
2. `_resource_key`, `get_shutdown_event`, `URLBackoffCoordinator`, `ProgressManager` and the coordinator's constants still resolve to `downloader_throttle.py`. **None is in the new module.**
3. All 7 residue importers are unchanged and still import successfully. Explicitly: `cli.py`, `services/batch_downloader.py`, `services/downloader.py`, `services/extractor.py`, `services/segment_downloader.py`, `services/ytdlp_downloader.py`, `services/signal_handlers.py`.
4. All 5 retry-policy importers import correctly: `segment_downloader`, `ytdlp_downloader`, `downloader` (re-export), `tests/test_downloader_throttle.py`, and the new module itself.
5. **Exactly 3** `patch()` strings change, all three naming the old module's own namespace. A `git diff` on the test files shows no other patch-target rewrite.
6. `services/downloader.py`'s symbol-ownership comment **and** its `__all__` both point at the new owner, **and the comment names every module that owns a name in `__all__`** — the four groups the retirement dropped are restored. `_attempt_segment_resume` is either in `__all__` or absent from the comment; the two must agree. `mypy src tests` no longer reports the "does not explicitly export" error for it.
7. `api-reference.md`'s `RETRYABLE_STATUS_CODES` row states the live 7-member set.
8. **`_compute_backoff_delay`'s arithmetic is unchanged** — `max()` semantics intact. See §5.4's prohibition. The two tests that name the floor (`test_retry_after_overrides_delay`, `test_retry_after_ignored_when_smaller`) pass without an expectation change.
9. If a new file was created, `tests/test_packaging.py`'s frozensets are edited **in this commit** and the counts are reported.
10. `downloader_throttle.py`'s module docstring, if it exists and describes the module's contents, matches the post-split module.
11. **No hunk touches `services/ffmpeg_utils.py`.** Per ruling A the module is permanent product code with a fixed three-part shape (§1.6); `B4` moves symbols between two modules and has no reason to touch a third. `git diff` over `ffmpeg_utils.py` is expected to be empty for this block.
12. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning, no new failures. Specifically green: `tests/test_downloader_throttle.py`, `tests/test_hls_downloader.py`, `tests/test_segment_downloader.py`, `tests/test_ffmpeg_utils.py`, `tests/test_cli.py`.
13. `ruff check src tests`, `ruff format --check src tests`, `mypy src` → clean.
14. One commit, `{type}(throttle): {description}`, explicit paths. **If `D7` creates a file, the frozenset edit is in this same commit.**

**Out of scope.** `ProgressManager` — not dead code, not moved, not renamed, not deleted. `_resource_key`'s origin-key normalisation semantics. `URLBackoffCoordinator`'s pause policy. `downloader_throttle.py`'s response-type classification used by `segment_downloader` (`is_retryable_status`). Every ffmpeg symbol, including the merge engine that still spawns ffmpeg. Plan 12's `ART-012` merge-multiplier change, which is a declared breaking change to three exact assertions in `tests/test_ffmpeg_utils.py::TestMergeFreeSpaceProbe`. `segment_downloader.py`'s concurrency work (phase 04, landed).

**Agent roster — Auditor, Planner, Validator.** Auditor: the patch-string census grew 9 → 13 → 15 and the fan-in was found to be 7 importers, not 0 — **the artifact's structural premise for this block is wrong, so it must be re-derived from the tree before any edit.** Validator: HIGH risk — a module move with five downstream importers, a facade whose re-export is under an explicit "the owning module is the fix" prohibition, a constant asserted in nine places and documented wrongly, and a new-file frozenset coupling. Planner: `D7` is a naming decision with a stated cost asymmetry, and the split boundary itself is a design judgement.

**No Researcher** — no external best-practice question; the design vocabulary is the project's own.

---

### 3.5 `B5` — the `Retry-After` comment states the opposite of the code (`QLT-013`)

**Goal.** Make the comment and docstring on the backoff computation describe what the code does — that `Retry-After` establishes a **floor**, not an override — without touching the code.

**Semantic scope.**
- The comment above the `Retry-After` preference inside `_compute_backoff_delay` (currently "Prefer Retry-After header over calculated delay").
- `_compute_backoff_delay`'s docstring, which currently reads "Respects Retry-After header if present" — a sentence that reads as a replacement and is not.
- `tests/test_downloader_throttle.py::TestComputeBackoffDelay` — **read only.** The two tests that name the floor are the pinning oracle; their names must remain accurate and they must remain unchanged.

**Alternatives.** *Default: correct the prose in place to state the floor.* Alternative: also rename the two tests, whose names say `overrides` while the behaviour is a floor. *Criterion:* the names are the artifact's evidence that the floor semantics are deliberately pinned. Renaming them would move the pin rather than remove the lie, and would make the diff look like a behaviour change. **Read-only.**

**Acceptance criteria.**
1. No change to `_compute_backoff_delay`'s body, to its signature, or to its arithmetic. `git diff` on the function shows comment and docstring lines only.
2. The prose states that `Retry-After` is a **floor** — the wait is `max(backoff, retry_after)`.
3. Both `test_retry_after_overrides_delay` and `test_retry_after_ignored_when_smaller` pass with **no change to name or expectation**.
4. No other function in the module is edited.
5. Gate: `uv run pytest tests/test_downloader_throttle.py -q` → green. `ruff check src tests`, `ruff format --check src tests` → clean.
6. One commit, `{type}(throttle): {description}`, explicit paths. **No frozenset edit** — no file is added or removed.

**Out of scope.** The code. The module split (`B4`). `RETRYABLE_STATUS_CODES`' value. The pause-duration constants.

**Agent roster — Planner only.** The diff is two prose sites, the behaviour oracle already exists and passes, and no file is added, moved or deleted. **A Validator review would exceed the risk**, and the reason is recorded rather than defaulted.

---

### 3.6 `B6` — `docs/STRUCT.md` names 29 of 31 modules and describes two of them wrongly (`QLT-003`)

**Goal.** Bring the structural map's module rows and its layering section in line with the tree, **yielding the `ffmpeg_utils.py` row to plan 12 `P12-B12`**.

**Semantic scope.**
- **Rows to correct** (measured in §2.5 correction 1 and §2.3): `models/enums.py` ("Quality, Method, CookieSource, etc." — names a `Quality` and a `Method` that do not exist; the enums are `QualityKind`, `QualityLabel`, `DownloadMethod`, `CookieSource`, `LogLevel`, `ErrorCode`, `ProgressStatus`), `models/video.py` ("Video metadata dataclass" — the module holds three `BaseModel`s), `models/dtos.py` (a row whose claims contradict the module), `services/concurrency.py` (a row that contradicts the module), `services/batch_downloader.py` (its parenthetical inventory is stale), `utils/__init__.py` (names 3 exports; the module's `__all__` has **5** — `sanitize_title` and `_resolve_output_file` are unnamed).
- **Rows to add**: `models/quality.py`, `services/ytdlp_downloader.py`. Plan 10 **explicitly ceded** the second to phase 09.
- **`services/downloader_throttle.py`'s row** — describes the post-`B4` module. Depends on `B4`.
- **The `Layering` section**: the entry-layer rule forbids private-symbol imports from service/utils layers, and `cli.py` imports the **private** `_strip_auth_params` from `utils` — **the declared rule is already violated in the entry layer.** And `models/quality.py` imports **upward** into `exceptions` (lazily, to break the `models → exceptions → utils.security → exceptions` cycle) — an inversion the layering section does not mention.
- **NOT `services/ffmpeg_utils.py`'s row.** Yielded — §4.3.

**Alternatives.** **`D14` — how the layering section records a rule the code violates.** *Default: amend the layering section to state both facts — the private-symbol import and the cycle-breaking upward import — as disclosed exceptions with their reasons, leaving the rule's intent intact.* Alternative: change the rule to permit the two forms, or delete the private-symbol prohibition. *Criterion:* is a reader of this section about to make a wrong decision? **Yes** — a reader who reads "no private-symbol imports from the entry layer" and does not see the exception will either "fix" `cli.py` or trust the rule as a description of the tree. Disclosure is strictly better than either deletion or silent violation. *Second criterion:* a disclosure that says the entry layer violates its own rule must not read as an invitation to change `cli.py`, because `B2` writes `cli.py` and `_strip_auth_params` is not in `B2`'s scope. The disclosure must therefore state that the import is deliberate.

**Acceptance criteria.**
1. Every `.py` path under `src/vkdownloader/` appears exactly once in the tree listing — 31 paths, measured by enumeration, with the enumeration recorded in the block's report. **Nothing here is checked by the suite** (§2.6).
2. The two previously unnamed modules are present: `models/quality.py`, `services/ytdlp_downloader.py`.
3. Each corrected row's parenthetical names symbols that exist in that module. `Quality` and `Method` do not appear as enum names.
4. `utils/__init__.py`'s row names all five names in its `__all__`.
5. `services/downloader_throttle.py`'s row describes the module as it exists **after `B4`**.
6. The `ffmpeg_utils.py` row is **byte-identical to what `P12-B12` leaves**. `git diff` on this block shows no hunk touching that row. If `P12-B12` has not landed, this block does not start (§4.2).
7. The layering section records the private-symbol import from the entry layer and the cycle-breaking upward import from the models layer, each with its reason and each marked deliberate.
8. No frontmatter is added. `STRUCT.md` is a root structural map and is edited in place.
9. `git diff --stat` shows `docs/STRUCT.md` as the only file changed. **No file added or removed → both frozensets stay at 73 / 32.**
10. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning. The doc edit is inert to every gate, which is the point of running them.
11. One commit, `{type}(docs): {description}`, explicit path.

**Out of scope.** The `ffmpeg_utils.py` row. The absence of frontmatter. `docs/STRUCT.md`'s header paragraph. Any second file — in particular **not** `.ai/structure/*`, which is `B7`. Any code.

**Agent roster — Auditor, Planner.** Auditor: **no test asserts this file matches the filesystem** (§2.6), so correctness is a measurement claim and must be measured, not asserted. Planner: `D14`'s disclosure wording is a judgement about whether a documented exception keeps a rule useful or makes it toothless, and it must read unambiguously to a reader who is about to edit `cli.py`. **No Validator** — the diff is inert to every gate, touches one file, adds no file, and the risk is a wrong parenthetical that `B7` and `B8` would independently expose.

---

### 3.7 `B7` — the generated structure maps describe 23 of 31 files, and three of the five describe another project (`QLT-004`)

**Goal.** Bring `.ai/structure/` back to describing **this** repository, and record the two front-end maps and the anchors file the finding never examined.

**Semantic scope.**
- `.ai/structure/back/py_map.yaml` — **23 entries against 31 `.py` modules.** Bring it to the full set. Present-but-unrecorded grew 7 → 8. **Recorded-but-absent symbols must be deleted: `QualityEnum` and `_parse_quality_to_enum`, both removed by the `QualityEnum` → `QualitySpec` migration, plus two more phantom symbols** — the Auditor must name all four at execution time.
- `.ai/structure/back/py_map.yaml`'s `cli.py` entry — it still records symbols that `services/batch_downloader.py` owns. Per §2.4 item 5, the fix is to record the **owning** module correctly.
- `.ai/structure/back/py_anchors.yaml` — 2927 lines. Carries the same **unsafe `.ai/builders/` prefix** as `map.md` (466 occurrences of that prefix). **The finding never examined this file.**
- `.ai/structure/front/ts_map.yaml` and `.ai/structure/front/ts_anchors.yaml` — **describe `C:/py_dev/mkobi/frontend/src/*.tsx`, a different project entirely.** 164 and 49 occurrences of that foreign path. **The finding never examined either file.**
- `.ai/structure/map.md` — still lists two `.pyc` entries for modules that no longer exist.

**Alternatives.**

- **`D9` — the two `front/` maps: delete or annotate.** *Default: delete both and record the deletion.* Alternative: annotate them as stale, or relocate them to a scratch location outside the repository. *Criterion:* does any tooling, plan or `.kilo` configuration reference them? Measured: **no `.ai/` path appears in `EXPECTED_SDIST_ENTRIES`, so these files are not shipped** — the frozenset does not constrain this block and deletion costs nothing packaging-wise. If a plan or config does reference them, annotate rather than delete.
- **The `builders/` prefix — a separate decision, not a `D`.** The finding's supporting claim is **correct and durable**: `.ai/builders/` is gitignored (`.gitignore`), `git ls-files .ai/builders` returns **0** files, so "resolves from a clean checkout" is **unsupported**. *Default: replace every `builders/`-prefixed anchor with a repository-relative path, or remove the anchors whose target cannot be reproduced.* *Criterion:* can the anchor be made checkout-reproducible at all? An anchor into an ignored, generated directory cannot be. Removing is correct; "fixing the prefix" is not available.
- **A rejected option:** hand-maintain `py_map.yaml` after this block. Rejected: the map is already 8 modules behind and 4 symbols stale within three commits of the last regeneration. A regenerated-from-the-tree map with a recorded regeneration command is the only shape that survives the next migration.

**Acceptance criteria.**
1. `py_map.yaml` records **31** modules, matching an enumeration of `.py` files under `src/vkdownloader/` produced in the same session. The enumeration is in the block's report.
2. **Zero** recorded-but-absent symbols. `QualityEnum` and `_parse_quality_to_enum` are gone; the other two phantom symbols are named and removed.
3. Zero present-but-unrecorded modules.
4. `py_map.yaml`'s `cli.py` entry attributes each symbol to the module that actually owns it. `services/batch_downloader.py` is named where it owns `ConcurrencyTracker`, `_TrackedSemaphore`, `run_batch`.
5. Every anchor path in `py_map.yaml`, `py_anchors.yaml` and `map.md` is **repository-relative and checkout-reproducible.** No path resolves into `.ai/builders/` or into any other gitignored directory. Verified with `git check-ignore` against every distinct prefix used.
6. `map.md` no longer lists a `.pyc` entry for a module that does not exist.
7. `front/ts_map.yaml` and `front/ts_anchors.yaml` are either deleted or annotated, per `D9`'s resolution, and the report states which and why.
8. **No frozenset edit.** `.ai/structure/` is not packaged — verified in §2.4 item 1. `git diff --stat` shows only files under `.ai/structure/`.
9. The regeneration command or procedure is recorded in the map's own header, so the next maintainer can regenerate rather than hand-patch.
10. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning. `.ai/` is not collected by the suite; this is a measurement gate, and criterion 1 **is** the gate.
11. One commit, `{type}(structure): {description}`, explicit paths under `.ai/structure/` only.

**Out of scope.** `docs/STRUCT.md` — that is `B6`, and the two artefacts have different formats and different audiences; this block does not make them agree beyond what each states. `.ai/audit/**` — read-only. Any code. `tests/test_packaging.py`.

**Agent roster — Auditor, Planner, Validator.** Auditor: the finding under-scoped **its own directory by three files**, one of them 2927 lines, and two of them describing a different repository — **the pattern is that the census is not trusted, so a fresh enumeration is required before any edit.** Validator: the block rewrites generated metadata that no test reads and no gate validates, and a plausible-looking but incomplete regeneration is indistinguishable from a correct one without independent checking. Planner: the `builders/`-prefix resolution and `D9` are judgement calls about what a structure map is *for*.

---

### 3.8 `B8` — the overview claims a universal export contract and a model that does not exist (`QLT-005`)

**Goal.** Remove the false universal-export claim and resolve the stale module line counts. **Re-scoped at `09f1b10`: the `DownloadProgress` half of this finding is already resolved, and two new false facts arrived with the retirement.**

**Semantic scope.**
- `docs/01-tools/vkdownloader-overview.md` — the universal-export claim ("All modules export X") against a re-run census of the nine `__all__` lists. The finding's own figure of "25 of 28" was measured on a stale tree and is re-derived at execution time.
- The same file's `services/` tree listing and its four line counts. Re-measured at `09f1b10`: `downloader.py` `~350` vs actual **344** (the retirement **partially corrected this one**), `ytdlp_downloader.py` `~722` vs **874**, `segment_downloader.py` `~901` vs **1283**, `ffmpeg_utils.py` `~360` vs **553**. Per §2.5 correction 8, **all four remain wrong, and the one now approximately right makes the other three more misleading, not less** — a reader who trusts `~350` has no reason to distrust `~722`.
- **Already done, and verified as such:** the `DownloadProgress Model Enhancement` section is **gone**. `DownloadProgress` and `eta_seconds` now occur **0 times** anywhere in `src/`, `tests/` or `docs/`. `B8` verifies this and does not repeat the work.
- **New, and unowned because plan 10 has landed:** the `--method` option row in this file still lists `ffmpeg` as a value. `cli.py`'s help was updated by the retirement; this document was not. It documents a deleted option value and is in `B8`'s file.
- **New, and unowned for the same reason:** this file's `services/` listing describes `ffmpeg_utils.py` as "FFmpeg commands, **progress parsing**, process management". Progress parsing was group B and is **deleted**; per ruling A the module is **permanent** and its surviving content is the subprocess infrastructure, the availability probe and the merge engine. This is the same defect class as `docs/STRUCT.md`'s row, but in a **different document that `B8` owns** — it does not touch the §4.3 yield.

**Alternatives.**

- **`D10` — correct the line counts or drop them.** *Default: drop them.* Alternative: replace them with the measured values. *Criterion:* does any document or test parse this tree listing? **None does.** A number in prose has no oracle, drifts silently, and is the artefact this finding exists to eliminate. If the maintainers want the figures, the correct home is a generated listing — which `B7` is the natural place to serve — not a hand-maintained one.
- **A rejected option:** treat the `--method` row or the `ffmpeg_utils.py` listing line as plan 10's and leave them. Rejected on measurement: **plan 10 has landed and left both behind.** No plan owns them now, they are false, and they are in the file `B8` edits. Leaving them is how `docs/STRUCT.md`'s row came to be wrong.
- **The rejected option from the first draft is now moot:** delete the whole `ProgressParser`/`DownloadProgress` region as one unit. It was rejected then because the `ProgressParser` paragraphs were plan 10's and adjacent to `DownloadProgress`. **Both regions are now gone**, so the adjacency hazard no longer exists and there is nothing to delete.

**Acceptance criteria.**
1. No universal-export claim survives. Any export statement the file makes is either scoped to a named module or removed.
2. The `--method` row no longer lists `ffmpeg`. Its remaining values match `cli.py`'s actual help.
3. This file's `ffmpeg_utils.py` listing line describes the module as it is — permanent, with the subprocess infrastructure, the availability probe and the merge engine — and does not mention progress parsing.
4. The four line counts are gone or measured-correct, per `D10`'s resolution, recorded either way.
5. `DownloadProgress` and `eta_seconds` remain at **0 occurrences** in the file, `src/` and `tests/`. Verified, not assumed.
6. `git diff --stat` shows only this one file. No frozenset edit.
7. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning.
8. One commit, `{type}(docs): {description}`, explicit path.

**Out of scope.** `docs/STRUCT.md` and its `ffmpeg_utils.py` row (`B6` yields it to plan 12 — §4.3; **this block's `ffmpeg_utils.py` edit is a different document and does not touch that yield**). `.ai/structure/*` (`B7`). `docs/01-tools/api-reference.md` — except the `RETRYABLE_STATUS_CODES` row, which belongs to `B4`'s commit because the constant moves there. `docs/99-reference/*` (`B9`, `B10`). `services/ffmpeg_utils.py` itself — **no code change**, and per ruling A the module is permanent.

**Agent roster — Auditor, Planner.** Auditor: the finding's export census was measured on a stale tree and every one of its four headline numbers has moved; the numbers must be re-censused before the prose is written. Planner: the ownership boundary with plan 10 is per-paragraph rather than per-file, and getting it wrong silently deletes another phase's work — the paragraph classification needs stating explicitly. **No Validator** — one file, prose only, no file added or removed, and `B9`/`B10` independently exercise the same rules.

---

### 3.9 `B9` — two files claim the same `id` and disagree on two facts (`QLT-006`)

**Goal.** Collapse `docs/99-reference/cli-reference-clean.md` into `docs/99-reference/cli-reference.md`, carrying the one fact that is correct only in the copy, and delete the copy.

**Semantic scope.**
- `docs/99-reference/cli-reference.md` — the survivor. It receives the `--ssl-verify` default.
- `docs/99-reference/cli-reference.md`'s batch step list — **the survivor's 7-step list is the correct one** and `cli-reference-clean.md`'s 6-step list is the wrong one (§2.5 correction 6).
- `docs/99-reference/cli-reference-clean.md` — **deleted.**
- **New at `09f1b10`:** the deleted copy still carries a `--method ffmpeg` usage example that `cli-reference.md` no longer has — a **fourth** fact divergence, introduced by the retirement. It goes with the file; `B9` records it so the merge census is complete.
- `tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` — **73 → 72**, edited in the same commit. **This is the coupling no audit or plan records.**
- `docs/error-handling-logging-research-2025-2026.md` — its one inbound reference to `cli-reference-clean.md` is updated in the same commit.
- `docs/00-overview/doc-maintenance-rules.md` — the "Single source of truth: Each fact lives in exactly one file" rule, per `D11`.

**Alternatives.**

- **`D11` — repair the maintenance rule, or rely on the deletion.** *Default: amend the rule minimally** — state its scope, and add that a byte-derivative copy must not be added without a pointer to the canonical file. Alternative: leave the rule untouched and rely on the deletion alone. *Criterion:* **was `cli-reference-clean.md` produced by an instruction that asks for a clean copy?** If a pipeline command or agent habit produces such copies, the rule is correct and the *instruction* is wrong — and the fix belongs at the instruction. **The instruction's home is not established by any artifact this plan has read, so this is escalated alongside `B13` rather than guessed at.** Default stands until that answer arrives.
- **A rejected option:** delete `cli-reference.md` and keep `-clean.md`. Rejected on measurement: `-clean.md` carries **0 em-dashes against 16** and stores mojibake as valid UTF-8; it is a damaged transcription, not the cleaner file. Keeping it would make the surviving document the damaged one.
- **A rejected option:** keep both and mark one canonical in frontmatter. Rejected — it satisfies neither the rule nor a reader, and it leaves two files to drift. That is the state this finding files.

**Acceptance criteria.**
1. Exactly one file under `docs/99-reference/` declares `id: cli-reference`.
2. `cli-reference.md` states the `--ssl-verify` default that `config.py` actually defaults to.
3. `cli-reference.md` carries the 7-step batch list, matching the code. The 6-step list appears nowhere.
4. `cli-reference-clean.md` does not exist.
5. **`EXPECTED_SDIST_ENTRIES` contains 72 entries, none of them `cli-reference-clean.md`, edited in the same commit.** `EXPECTED_WHEEL_ENTRIES` unchanged at 32. Both counts are stated in the report.
6. `docs/error-handling-logging-research-2025-2026.md` no longer references the deleted file, and the reference it now carries points at `cli-reference.md`.
7. Neither file's frontmatter changes. `cli-reference.md` keeps `id: cli-reference` and `related: [configuration-guide, ast-editor]`; it never listed the deleted copy, so no `related` edit is needed — **verified, not assumed.**
8. **`P10-B10` has landed, and the merge census is re-run rather than inherited.** The divergence count moved: `-c` flag, cookie-source rows and the two open facts are unchanged, and a **fourth** divergence appeared — the copy retains a `--method ffmpeg` usage example the survivor lost. Plan 10 and this plan characterise the file differently — plan 10 as pure mojibake, phase 09 as divergent on facts — and **both are correct**, which is why the direction of the merge had to be re-derived per row rather than taken from the artifact (§2.5 correction 6).
9. The block does **not** touch the cookie-source rows, the `--method` rows, the `--quality` rows or the `--method` help text — **all four documents are already correct on those** and no finding asks for them to change.
10. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning, with `tests/test_packaging.py` explicitly green. `ruff check src tests`, `ruff format --check src tests` → clean.
11. One commit, `{type}(docs): {description}`, explicit paths — `docs/99-reference/cli-reference.md`, `docs/99-reference/cli-reference-clean.md`, `tests/test_packaging.py`, the research document, and `doc-maintenance-rules.md` if `D11` resolves to amend.

**Out of scope.** `docs/99-reference/ast-editor.md` and `morfx-tools.md` (`B10`). Any ffmpeg row. `docs/STRUCT.md`. `doc-maintenance-rules.md`'s other rules — only the single-source rule is in scope.

**Agent roster — Auditor, Planner, Validator.** Auditor: the merge direction had to be re-derived — the artifact's instruction would have imported the **wrong** step list (§2.5 correction 6) — so the divergence must be re-measured per row at execution time. Validator: the block deletes a file listed in a packaging frozenset that **no plan or audit records as coupled to this deletion**, and a missed frozenset edit is a red suite that reads as "the fix broke packaging". Planner: `D11` is a rule-scope question, not an edit.

---

### 3.10 `B10` — two shipped reference documents describe no code in this repository (`QLT-008`)

**Goal.** Resolve `docs/99-reference/morfx-tools.md` (600 lines) and `docs/99-reference/ast-editor.md` (41 lines), which describe tooling that this repository does not contain, while keeping them reachable by whatever actually consumes them.

**Semantic scope.**
- `docs/99-reference/morfx-tools.md` — self-disclaims verbatim. Describes MCP code-transformation tools; this repository has no such tool. Its `related` array names `ast-editor` and `doc-maintenance-rules`.
- `docs/99-reference/ast-editor.md` — self-disclaims. Its `related` array names `doc-maintenance-rules` and `morfx-tools`.
- `tests/test_packaging.py::EXPECTED_SDIST_ENTRIES` — both files are listed. **Any move requires editing the frozenset in the same commit** (the count is unchanged; the names are).
- The **mutual** `related` cross-references: **if either file moves or is deleted, both `related` arrays change in the same commit.**

**Alternatives.**

- **`D12` — move, annotate in place, or delete.** *Default: move both out of `docs/99-reference/` into a developer-tooling location, keeping them shipped.* Alternative: delete both. Alternative: annotate each with a placement disclaimer and leave it. *Criterion:* **does `.kilo` agent or tool configuration consume these files by path?** They are shipped in the sdist, so under the project's own placement rule (`doc-maintenance-rules.md`: use `99-reference/` for guides and external docs) they are not external docs — they are *this project's* tooling docs at the wrong location. If an agent configuration consumes them, they are agent infrastructure, which argues for keeping them but not shipping them in `docs/`. The decision criterion is a lookup the Auditor must perform, not a preference.
- **A rejected option:** treat `ast-editor.md` as a third mojibake duplicate, on the theory that it shares the problem. Rejected by measurement (§2.5 correction 7): `ast-editor.md` is **valid UTF-8 with one real em-dash**. Only `cli-reference-clean.md` is a mojibake transcription. Carrying the argument forward would be filing a defect that does not exist.

**Acceptance criteria.**
1. Each of the two files is **moved, annotated, or deleted** — a resolution, recorded with its reason.
2. `EXPECTED_SDIST_ENTRIES` reflects the resolution **in the same commit**: 72 unchanged if both are moved, **70** if both are deleted, with the correct new names if moved. `EXPECTED_WHEEL_ENTRIES` unchanged at 32.
3. If either file moves or is deleted, **both `related` arrays** are consistent with the outcome. `grep` over `docs/` finds no `related` entry pointing at a path that does not exist.
4. If a move happens, the destination's placement rule is satisfied and the file's frontmatter is otherwise unchanged.
5. **Not** the mojibake argument of `B9`'s file. Each file's own claim about itself is quoted accurately.
6. **`B9` has landed.** Both blocks write the same frozenset; §4 serialises them so no two commits edit it concurrently.
7. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning, with `tests/test_packaging.py` explicitly green.
8. One commit, `{type}(docs): {description}`, explicit paths.

**Out of scope.** `cli-reference.md` and `cli-reference-clean.md` (`B9`). The agent/tool configuration itself — this block does not reconfigure any tooling. `doc-maintenance-rules.md`, except that its placement rule is the criterion for `D12`.

**Agent roster — Auditor, Planner.** Auditor: `D12` turns on whether a `.kilo` configuration references these paths, which is a repository lookup no finding has performed. Planner: the disposition of a 600-line shipped document is a product judgement about what this repository is for. **No Validator** — the frozenset coupling is the only mechanical risk and it is shared with `B9`, which carries the Validator.

---

### 3.11 `B11` — provenance tags cited from shipped source and documents that resolve nowhere (`QLT-007`)

**Goal.** Resolve or remove the dead `INT-` / `SRV-` / `STR-` citations, and do not invent identifiers to fill the gap.

**Re-censused at `09f1b10` — the scope SHRANK and the hazard changed shape.** The retirement deleted `INT-001`'s code sites and `tests/test_hls_downloader.py::TestFfmpegCookiePassing` outright, and `INT-005` with them. What remains is **8 identifiers across 23 sites**, and — unlike the first-draft census — **every remaining site survives.** The "does this site die with plan 10" classification that previously gated this block is therefore **no longer the primary task**; it becomes a verification step, because a future change could reintroduce dying sites. The block's scope also **widens by one identifier**: `INT-008` is now cited from `downloader_throttle.py` and appears in **no** audit artifact.

**Semantic scope.** Measured census at `09f1b10`:

| Identifier | Cited from (site count) | Status |
|---|---|---|
| `INT-008` | `services/downloader_throttle.py` (1) | **NEW — in no artifact.** Survives. Dead citation |
| `INT-006` | `services/downloader_throttle.py` (1), `infrastructure/browser.py` (1), `tests/test_downloader_throttle.py` (2) | Survives. Maintained decision tag |
| `INT-004` | `infrastructure/browser.py` (2), `tests/test_browser_infrastructure.py` (2), `tests/test_hls_downloader.py` (1) | Survives. Requirement recorded by phase 04's `B4` |
| `INT-003` | `services/extractor.py` (3), `tests/test_extractor.py` (2) | Survives. Requirement recorded by phase 04 |
| `STR-008` | `services/ffmpeg_utils.py` (1, on `iter_process_lines`), `tests/test_hls_downloader.py` (1) | Survives. **Group A — permanent product surface per ruling A.** The comment must remain and stay accurate |
| `INT-007` | `tests/test_hls_downloader.py` (1, "ffmpeg availability probing") | Survives. **Its subject `check_ffmpeg_available` is permanent product surface per ruling A** — the citation is dead but the requirement it names is real and durable |
| `SRV-006` | `services/ytdlp_downloader.py` (1), `docs/01-tools/api-reference.md` (1), `docs/01-tools/vkdownloader-overview.md` (1), `tests/test_hls_downloader.py` (1) | Survives. Requirement recorded only in the plan corpus |
| `SRV-003` | `tests/test_downloader_throttle.py` (1, inline, on `ProgressManager`) | Survives. Resolves only to a **retired** plan file under `.ai/plans/done/`. `ProgressManager` is documented-as-retained, so this site is live |
| `SRV-001` | `docs/01-tools/vkdownloader-overview.md` (1) | Survives. Module-split rationale |
| `INT-001`, `INT-005` | **0 sites** | **Dead with the retirement. No block edits them** |

**Verification step, not scoping step.** Before editing, confirm no site has become a dying site since `09f1b10`; and after editing, cross-check against any later retirement diff the way criterion 3 previously required.

**Alternatives.**

- **`D13` — for a tag whose requirement is recoverable: repoint, inline, or delete.** *Default: repoint only where a *findings* file records the requirement; otherwise delete the parenthetical and let the surrounding prose stand, which it already does for `SRV-006` and `SRV-001`.* Alternative: inline the requirement as prose. *Criterion:* **is the requirement recorded in `.ai/audit/*/findings.md` (durable) or only in `.ai/plans/*` (transient)?** Only a findings-file record justifies a citation — a citation to a plan is a citation that will die with the plan. Inline-as-prose is the right answer when the requirement is real but short, which is the case for the inter-retry backoff decision.
- **A rejected option:** add the missing identifiers to a registry document. Rejected by the finding's own instruction and by house rule: **an identifier with no requirement behind it is the same defect one level down.** A registry of twelve tags with no bodies would be a larger instance of the failure it fixes.
- **A rejected option:** delete all `INT-` tags as a namespace cleanup. Rejected — `INT-003`, `INT-004` and `INT-006` are **maintained** decision tags that four plans are currently keeping accurate. Deleting them would delete live provenance.

**Acceptance criteria.**
1. Every `INT-` / `SRV-` / `STR-` citation from **shipped source and shipped documents** either resolves to a findings-file requirement or is removed. The report lists each of the 8 identifiers and all 23 sites with its resolution.
2. **No identifier is invented.** The report contains no new `INT-`/`SRV-`/`STR-` token.
3. No hunk touches a site that has become dying since `09f1b10`. Verified against any retirement diff.
4. `services/ffmpeg_utils.py`'s `STR-008` comment on `iter_process_lines` is **present and accurate**. Per ruling A it sits on group A, which is **permanent product surface**, and a "remove ffmpeg comments" sweep is now doubly wrong: it would delete a comment on permanent code.
5. Each tag whose surrounding prose already states the rationale in full has its parenthetical removed rather than reworded.
6. Any tag left in place is left **because** a findings file records its requirement, and the report names that file. `INT-008` is resolved by this rule: it is cited, undefined, and recorded in no artifact.
7. `INT-007`'s site is treated per its subject: `check_ffmpeg_available` is permanent, so the requirement is real and must be preserved — as prose or as a pointer to a record, not by deletion.
8. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning. Comment-only and docstring-only changes are inert to every gate.
9. One commit, `{type}(comments): {description}`, explicit paths.

**Out of scope.** The `VAL-` namespace (`B13`). `D-01`…`D-12`, `SEC-*`, `CON-*`, `DF-*`, `ART-*`, `TRN-*` — the live provenance scheme. Any `INT-` or `SRV-` identifier's **code**, as opposed to its citation: `B11` changes comments and docstrings only. Any site that has become dying.

**Agent roster — Auditor, Planner, Validator.** Auditor: **the census moved under this block twice** — from 9 patch strings to 13 to 15, and now from 11+ identifiers to 8 with one brand-new addition. The block's premise was measured wrong at the first draft and again at the re-baseline, so the census must be re-run before any edit and the classification verified rather than inherited. Planner: `D13` needs a durable definition of "records the requirement" before any site can be classified, and ruling A changes the classification for `INT-007` and `STR-008` from "subject survives pending a retirement" to "subject is permanent". Validator: the block's failure mode is a plausible, confident, wrong citation — the exact defect it removes.

**No Researcher.**

---

### 3.12 `B12` — record why one module uses both import forms (`QLT-012`)

**Goal.** Record the import-form taxonomy with the case the finding's three buckets cannot hold, and keep the one deferral comment that is load-bearing.

**Semantic scope.**
- `models/quality.py` — the only module in the tree that uses **both** forms: a module-level relative `from .enums import QualityKind, QualityLabel`, and a **lazy absolute** `from vkdownloader.exceptions import QualityParseError` inside `QualitySpec.parse`. The lazy import breaks the cycle `models → exceptions → utils.security → exceptions`. It is load-bearing.
- `exceptions.py::InvalidVideoUrlError.__init__`'s deferral comment — the same cycle, from the other side. **Re-read and kept; not deleted.** It explains why the import is inside `__init__`.
- The taxonomy as it is recorded — wherever the project's import-form convention is written. If no such document exists, **this block does not create one**; it records the taxonomy in the module's own comment and reports that no convention document exists.

**Alternatives.**

- **`D14b` — a fourth bucket, or a documented exception.** *Default: a documented exception.* The mixed file gets a comment on the lazy import stating why it is absolute and why it is deferred; the taxonomy records the case. Alternative: add "mixed" as a fourth bucket to whatever document holds the taxonomy. *Criterion:* **is the cycle real?** It is, and it cannot be broken by making the import relative — the cycle passes through the package `__init__`. A mixed file here is not inconsistency, it is the correct resolution of a real constraint, and calling it a fourth bucket would invite a future maintainer to "regularise" it and reintroduce the cycle.
- **A rejected option:** make `models/quality.py` relative-only by importing `QualityParseError` through `models/enums.py`. Rejected: `models/enums.py` would have to import `exceptions`, which imports `models.enums` — the cycle would be relocated, not removed.

**Acceptance criteria.**
1. `models/quality.py`'s lazy absolute import carries a comment naming the cycle it breaks. The comment survives `B3`, which touches the same file for a different reason.
2. `exceptions.py`'s deferral comment is unchanged in substance and still accurate.
3. The taxonomy as recorded names the mixed case and classifies `models/quality.py` in it.
4. Measured counts in the report: **27** non-`__init__` modules — **16** relative-only, **3** absolute-only, **7** neither, **1** both.
5. No import statement changes. `git diff` on `models/quality.py` shows comment lines and, at most, the reformatting `ruff format` requires.
6. Gate: `uv run pytest -q -rs` → **3 skipped**, ≤1 warning. `ruff check src tests`, `ruff format --check src tests`, `mypy src` → clean.
7. One commit, `{type}(comments): {description}`, explicit paths.

**Out of scope.** Regularising any import in any other module. Creating a shared-constants module (§2.4 item 2 forbids it). The 16/3/7 modules' existing forms. `B3`'s type work.

**Agent roster — Planner only.** One file's comment, one deferral comment re-read, no behaviour change, no new file, and the behaviour is already pinned by 33 passing exception tests. **A Validator would exceed the risk**; the reason is recorded.

---

### 3.13 `B13` — the audit pipeline's own namespace (`VAL-901`, `VAL-902`, and the six recorded warnings) — **escalation, no code**

**Goal.** Record that phase 09's remaining findings cannot be implemented under the current authorisation, name the decision needed, and stop. **This block writes no product code, no test, and no file under `.ai/audit/`.**

**Why it is a block and not a note.** `VAL-901` is **CRITICAL** by the artifact's own rating and its measurement has grown by 12.6×: the flat `VAL-` namespace is now **553 occurrences across 52 distinct identifiers** (the artifact recorded 44 / 33), `VAL-003` alone appears **52 times**, `VAL-001` 46 times, `VAL-125` 26 times, and an **unparseable `VAL-7`** exists. Three mutually exclusive claims still carry `VAL-003`, and `VAL-902` establishes that one of the three does not reproduce. Bands in use: `0xx`, `1xx` (both `101`–`112` **and** `120`–`125`), `4xx`, `5xx`, `6xx`, `7xx`, `9xx` — and plan 12's own §1.5 called the collision "prospective", which it is not.

**The authorisation wall, stated exactly.** Both remedies require editing files under `.ai/audit/99-validation/` — `VAL-901` a re-key of twelve validation artifacts plus `.kilo/commands/audit/phases/99-audit-validate.md`, `VAL-902` an in-place annotation. Plan 11 `B10` carries an **absolute staging prohibition** on `.ai/audit/99-validation/**`, and **no document authorises this phase to write there.** Phase 09 is the only phase whose findings land in that directory, and nothing grants it the right. **Escalated, not absorbed.**

**Additional material discovered, recorded by this plan:**

- **A plan has already cited a `QLT-` identifier against the wrong subject.** Plan 11 cites *"the `QLT-004` `finally` discipline inside `_create_temp_cookie_file`"* — twice. Phase 09's `QLT-004` is *"the generated structure maps record 23 of 30 source files."* There is no other `QLT-004`; the prefix is phase 09's exclusive. This is the flat-namespace failure mode occurring in a **plan**, and it is live now.
- **`VAL-902`'s premise is partly obsolete.** It records a stale, superseded findings catalogue as present and deleted-but-unstaged. That catalogue was retired by the audit-renumbering commit; 8 of its 9 stale handbook names no longer exist. A reader acting on `VAL-902` will look for files that are gone.
- **`VAL-903`'s corpus-drift premise is likewise void**, for the same reason.
- **`api-reference.md`'s `RETRYABLE_STATUS_CODES` row is a new false fact** the artifact records as introduced by landed work and never filed. Assigned to `B4`.
- **The four `ffmpeg_utils.py` doc/ownership sites are unowned**: the module docstring, `services/downloader.py`'s `ffmpeg_utils` ownership group (which itself omits group A's `iter_process_lines`), and three `api-reference.md` location rows. Recorded in §5.6 as a gap for a future phase, not claimed here.
- **The stale-document warning spans six documents**, so a new maintainer's first map is wrong in ≥14 places. `B6`, `B7`, `B8`, `B9` and `B10` reduce this; they cannot close it.
- **`.kilo/commands/audit/refine.md` is still structurally malformed** — `{REQUIRE_RESEARCH}` defined nowhere, two `<subagent_prompt>` blocks, an unterminated `### 3.` — so a human-invoked refine pass still emits an empty subagent prompt. Unowned.

**Semantic scope.** A single escalation note, produced from this plan, recorded in the block's report and posted to the board. **No file under `.ai/audit/`.** No `.kilo/` edit.

**Acceptance criteria.**
1. The escalation states, in one place: what `VAL-901` and `VAL-902` are; why each is unimplementable under the current authorisation; what the options are (authorise phase 09 to write under `.ai/audit/99-validation/`, or assign the namespace to a phase that holds the prohibition, or record both as permanently unfixed); and which one is recommended.
2. It names the wrong-`QLT-004` citation in plan 11 as a live instance of the defect, with the two locations.
3. It records the four unowned `ffmpeg_utils.py` doc sites so they are not lost.
4. It records the `D11` question — **which instruction or agent habit produces a clean copy of a document** — as the open question that decides whether the single-source rule or the instruction is what gets fixed.
5. `git diff` shows **no** change under `.ai/audit/` and **no** change under `.kilo/`.
6. No file is added, moved or deleted by this block. **No frozenset edit.**
7. The block **reports the `VAL-` measurement from §2** as measured, with the artifact's own figures beside it, so the owner sees the growth rather than the original filing.

**Out of scope.** Every product-code remediation of a `VAL-` finding. `.kilo/commands/audit/phases/99-audit-validate.md` — plan 11 `B9`'s, and unowned thereafter. `.ai/audit/templates/` — plan 11 `B10`'s. `.kilo/commands/audit/refine.md` — unowned; recorded, not claimed.

**Agent roster — Auditor, Planner.** Auditor: the measurement has grown 12.6× and two of the three findings' premises have been invalidated by later commits — the census must be re-run so the owner sees current figures. Planner: the escalation's structure decides whether it gets acted on. **No Validator — and the reason is recorded rather than defaulted: there is no implementation to validate. This block produces a decision request, and validating a decision request would exceed its risk.**

---

## 4. Dependency graph, linearised order, and the conflict matrix

### 4.1 The graph

```
                      ┌──────────── external gates (other plans) ────────────┐
                      │  P10-B10  P10-B7  P10-B14                          │
                      │  P11-B2   P11-B4   P11-B5   P11-B6                 │
                      │  P12-B6   P12-B7   P12-B8   P12-B12                │
                      └──────────────────────┬──────────────────────────────┘
                                             │
   B13 escalation ──► (owner decision)       │
        no code                               │
                                             │
   B1 exceptions ──► B2 ladders ──► B3 types ──► B12 import record
    (zero drift,                            (pyproject.toml +
     uncontested)                            5 real Any)
        │
        └──► B4 throttle split ──► B6 STRUCT rows ──► B7 structure maps
              │                        ▲
              └──► api-reference.md ───┘
                   RETRYABLE row
        │
        ├──► B8 overview (counts)

   B5 Retry-After comment  (independent; placed early because it is zero-risk)

   B10 misplaced refs ──┐
                        ├──► B9 cli-reference collapse
                        │     (shared frozenset: B10 then B9)
   P10-B10 ─────────────┘

   B11 dead provenance ──► (needs P10-B7, P10-B10, P11-B4)
```

### 4.2 Linearised order, with the reason for each position

**Total order:**
`B13 → B1 → B2 → B3 → B12 → B5 → [external gates] → B4 → B6 → B7 → B10 → B9 → B8 → B11`

| # | Block | Why this position |
|---|---|---|
| 1 | `B13` | The only block that produces no code. It requests a decision from an owner, and one of its open questions — which instruction produces a clean copy of a document — **decides `D11`, which decides `B9`'s rule amendment**. Starting it costs nothing and can unblock work later in the order. |
| 2 | `B1` | `exceptions.py` is the **only zero-drift file** in the phase and the **only uncontested shared edit region** in the corpus (`VAL-903`). Starting here minimises the window in which another agent's edit can move the ground. It is also upstream of `B2`, `B3` and `B6`. |
| 3 | `B2` | Directly downstream of `B1`: the new `VKDownloadError` arms call `status_label()` and `log_context()`, and `B1` changes what `status_label()` returns for `QualityNotAvailableError`. **B2 before B1 would encode the old label contract into two new code paths.** |
| 4 | `B3` | Downstream of `B1` (the `Callable[..., str]` annotation may not exist after `B1`) and of `B2` (one-writer rule on `cli.py`: `B2` writes the ladders, `B3` writes `_quality_option`). Also the last block touching `pyproject.toml`. |
| 5 | `B12` | Shares `models/quality.py` with `B3`. After `B3`, so the block that adds the type gate is not followed by one that touches a file the gate just covered. Small, and it needs no gate to land. |
| 6 | `B5` | Zero risk, comment-only, behaviour already pinned by two passing tests. Placed here for the DAG, **not** to serialise it — `B5` is safe to land at any point, including before `B1`. It is here so its commit is not confused with `B4`'s. |
| — | **external gates** | `B4` cannot start until plan 12's `segment_downloader.py` track (`P12-B6`, `B7`, `B8`) and plan 11's `ytdlp_downloader.py` track (`B2`, `B5`) have landed, because `B4` writes both files. `B9` and `B11` need plan 10's `B10`. `B6` needs `P12-B12`. |
| 7 | `B4` | The phase's highest-risk block, and the one with the most external dependencies. Placed after the gates so it is not started twice. Upstream of `B6` (the throttle row) and `B8` (the line counts). |
| 8 | `B6` | Downstream of `B4` for one row and downstream of **`P12-B12`** for the whole file. Writing the throttle row before the split would produce a row that is wrong within the same phase. **If `P12-B12` has not landed, `B6` does not start** — its acceptance criterion 6 requires the `ffmpeg_utils.py` row to be byte-identical to what `P12-B12` leaves, which is unmeasurable until `P12-B12` lands. |
| 9 | `B7` | Records the tree. Running before `B6`/`B4` would record a module set that changes within the same phase. Last to touch generated structure metadata, so it captures the final tree. |
| 10 | `B10` | Writes `EXPECTED_SDIST_ENTRIES`. Placed **before** `B9` so that `B9`'s frozenset edit (`73 → 72`) starts from a state `B10` has already settled. If `B10` resolves to deletion, `B9` reports `70 → 69` instead of `72`; either way the two never edit the frozenset concurrently. |
| 11 | `B9` | Writes the same frozenset as `B10`, and needs `P10-B10`. Placing it after `B10` makes the frozenset single-writer for the whole phase. |
| 12 | `B8` | Needs `B4` (four stale line counts) and `P10-B10` (the ffmpeg paragraphs adjacent to the paragraphs being edited). Latest of the documentation blocks. |
| 13 | `B11` | The last block, because its scope is determined by what plans 10 and 11 have already rewritten. Editing a comment before the plan that owns its wording has landed would race that commit. |

**Safe parallelism.** `B5` may run in parallel with anything. `B13` may run in parallel with anything. `B7`'s `D9` sub-decision (the two `front/` maps) is independent of `B4` and `B6` and may be resolved early. Everything else is serialised by the graph above.

### 4.3 The `P12-B12` collision — **RESOLVED: phase 09 yields, and serialises behind**

This is the one collision the brief required this plan to settle rather than defer.

**The collision.** Plan 12's `P12-B12` owns one structural-map sentence in `docs/STRUCT.md` — the `services/` tree listing's entry for `ffmpeg_utils.py`, currently "FFmpeg discovery and stream concatenation" — with acceptance criterion 3: **"No other file changes."** `QLT-003` wants two added rows and seven corrections **on the same file, in the same commit window**, and neither document declares an order.

**The decision: `QLT-003` does not touch the `ffmpeg_utils.py` row at all, and `B6` runs after `P12-B12`.**

**The reason, in four parts.**

1. **The criterion is satisfiable only by sole ownership of the file in its commit.** "No other file changes" is trivially true whether or not another block edits a *different hunk of the same file in a different commit* — but only if the two never share a commit. Serialising guarantees that; overlapping does not. This is the same contention `VAL-903` records for `exceptions.py`, applied to a document.
2. **The sentence is not `QLT-003`'s to write even in principle.** The current text's defect is that it names "discovery" — which is precisely the group-B half that retires with the transport — and omits both the shared subprocess infrastructure (group A) and the merge engine (group C). A replacement must therefore be a **two-state** description that survives the retirement as well as precedes it. `QLT-003`'s scope is a census of missing and mis-described module rows; it has nothing to say about a module whose partition is plan 12's subject. Yielding costs phase 09 nothing it was ever entitled to.
3. **The finding itself is wrong about the row for a second, independent reason.** `docs/STRUCT.md`'s tree listing cannot describe group A **at all** today, because `iter_process_lines` and `cancel_subprocess` are not imported through the facade — `ytdlp_downloader` imports them directly — so they are absent from the facade's `__all__` and from its symbol-ownership group. Any row written from the facade's inventory understates the module. That is `P12-B12`'s import-graph argument to make, not `QLT-003`'s census argument.
4. **No ordering is declared anywhere, so the safest available rule applies.** Plan 12's `P12-B12` is marked "free at any point" in its own §4.2; `QLT-003` is the block that has a mandatory predecessor for its other rows. Yielding is therefore the assignment that leaves both plans coherent.

**What phase 09 takes from `docs/STRUCT.md`:** the `models/enums.py`, `models/video.py`, `models/dtos.py`, `services/concurrency.py`, `services/batch_downloader.py`, `utils/__init__.py` and `services/downloader_throttle.py` rows; the two added rows for `models/quality.py` and `services/ytdlp_downloader.py`; and the `Layering` section. **What it yields:** the `ffmpeg_utils.py` row, untouched.

**How the decision is verified.** `B6`'s acceptance criterion 6 requires that `git diff` on the block show **no hunk touching the `ffmpeg_utils.py` row**, and criterion 6's precondition — `P12-B12` having landed — is a hard start gate.

### 4.4 Conflict matrix over shared semantic anchors

| # | Anchor | Phase-09 block | Competing claim | Resolution | Severity |
|---|---|---|---|---|---|
| 1 | `docs/STRUCT.md` — the `ffmpeg_utils.py` row | `B6` yields it | Plan 12 `P12-B12` owns it, criterion "no other file changes" | **Resolved.** Yield + serialise. §4.3 | HIGH → resolved |
| 2 | `docs/STRUCT.md` — the other rows and the layering section | `B6` | Plan 12 `P12-B12` explicitly excludes "STRUCT.md's other entries" | **Clean.** `B6` is the sole owner | Clean |
| 3 | `docs/STRUCT.md` — `ytdlp_downloader.py`'s absent row | `B6` adds it | Plan 10 §1.4 **explicitly cedes** it to phase 09 | **Clean handoff.** Plan 10 does not touch it | Clean |
| 4 | `exceptions.py`, `tests/test_exceptions.py` | `B1` | No plan touches either | **Clean, uncontested.** The corpus's only claim with no competitor. Merged `QLT-001` + `QLT-010` to keep it that way | Clean |
| 5 | `cli.py` — the two `logger.exception` sites and their records | `B2` | Plan 11 `B6` criterion 3: "covered **without any edit to `cli.py`**" | **Serialised: `B2` after `P11-B6`.** Plan 11's criterion constrains `B6`'s implementation, not this phase's file access. `B2` **reuses the existing event names** so plan 11's sixteen-record inventory does not need amending and its rules bind identically. `B2` is also placed after `B1`, which `B2`'s code paths depend on | HIGH → serialised |
| 6 | `download_failed` record shape | `B2` (`D3`) | Phase 08 `OUT-002`'s evidence is a captured `download_failed` record carrying a rendered traceback | **Open decision `D3`.** `B2` may not change the record from `logger.exception` to `logger.error` until it is settled against phase 08's plan. Default `logger.error`; criterion is phase 08's dependency on that record's shape | HIGH → open decision |
| 7 | `services/downloader.py`'s re-export of `_retry_429_with_backoff` and its `__all__` entry | `B4` | Plans 11 and 12 both state: **the owning module is the fix; a re-export edit is never the remedy** | **Complies.** `B4` moves the owner and updates the facade as a consequence. The facade's `__all__` length stays at 26 | HIGH → complies |
| 8 | `services/segment_downloader.py` | `B4` | Plan 12 `P12-B6`/`B7`/`B8` — its one-writer track | **Serialised behind all three.** `B4` does not start until that track is complete | HIGH → serialised |
| 9 | `services/ytdlp_downloader.py` | `B4`, `B11` | Plan 11 `B2`/`B5` rewrite it | **Serialised behind both.** `B4` writes it; `B11` edits its comments and therefore runs **after `B4`** too | HIGH → serialised |
| 10 | `services/extractor.py`'s `INT-003` comments | `B11` | Plans 08 and 09 both record keeping `INT-003` accurate; plan 09 already landed `B9` there | **Clean.** `B11` re-points the citation, does not change behaviour, and the phase-09 completion report already corrected the `INT-004` sibling | Medium |
| 11 | `infrastructure/browser.py`'s `INT-004` comment | `B11` | Plan 09 (phase 04) `B4` corrected it; plan 08 also tracks it | **Clean.** The requirement is now recorded; `B11` re-points rather than rewrites | Medium |
| 12 | `docs/01-tools/vkdownloader-overview.md` — ffmpeg paragraphs | `B8` **now owns** two of them | Plan 10 `B10` owned the eight-file `--method ffmpeg` surface — **and has landed**, updating seven documentation sites while leaving this one document's `--method` row and `ffmpeg_utils.py` listing line behind | **Transferred by absence, not by claim.** Plan 10 no longer exists as an owner; both false facts are in the file `B8` edits; neither is in `docs/STRUCT.md`, so §4.3's yield is untouched. `B8`'s criteria 2 and 3 | Medium → assigned |
| 12b | `docs/99-reference/cli-reference-clean.md` retains a `--method ffmpeg` usage example that `cli-reference.md` no longer has | `B9` | No plan owns it | **A fourth fact divergence, introduced by the retirement.** `B9` already merges this file; the example is deleted with it. §4.3's bidirectional-merge rule covers it | Low |
| 13 | `docs/01-tools/vkdownloader-overview.md` — the `SRV-001` parenthetical | `B11` | Plan 10 §1.4 records the mojibake in `cli-reference-clean.md` as OUT and unowned; the `SRV-001` citation is a **different** paragraph | **Clean.** Different anchor | Low |
| 14 | `docs/99-reference/cli-reference-clean.md` | `B9` deletes it | Plan 10 §1.8 lists it as the file `B10` edits, and characterises it as pure mojibake | **Serialised after `P10-B10`.** Plan 10 `B10` still edits its `--method` rows; deleting first leaves it no target. Both characterisations are correct — the encoding damage is real **and** two fact rows genuinely differ — which is why the order matters | HIGH → serialised |
| 15 | `EXPECTED_SDIST_ENTRIES` (73) | `B4`, `B9`, `B10` | No plan or audit records that these findings touch it | **Single-writer serialised `B10` → `B9`.** `B4` only if a file is created, and `B4` precedes both. **This coupling is new in this plan** — §2.4 item 1 | HIGH → serialised |
| 16 | `.ai/structure/front/ts_map.yaml`, `ts_anchors.yaml` | `B7` | Unowned. No plan references them | **Clean.** No frozenset coupling — `.ai/` is not packaged | Low |
| 17 | `.ai/audit/99-validation/**` | `B13` **escalates** | Plan 11 `B10`'s absolute staging prohibition; no plan authorises phase 09 to write there | **Wall, not a conflict.** `B13` produces a decision request and stops. `VAL-901` and `VAL-902` remain unimplemented by design, not by oversight | HIGH → escalated |
| 18 | `.kilo/commands/audit/phases/99-audit-validate.md` severity table | `B13` records as unowned | Plan 11 `B9` owns it | **Clean.** Recorded so the gap after plan 11 is visible | Low |
| 19 | `.ai/audit/templates/audit-findings.md` | `B13` records as unowned | Plan 11 `B10` owns it — the only block permitted to touch `.ai/audit/` | **Clean.** Recorded | Low |
| 20 | Plan 11's two `QLT-004` citations | `B13` records | Plan 11 cites `QLT-004` for a `finally` discipline in `_create_temp_cookie_file`; phase 09's `QLT-004` is the structure-map census | **Live cross-plan defect.** Recorded, not corrected — plan 11 is not this plan's file | Medium |
| 21 | The D-11 file-mode skips — **three now, four before `d572d96`** | No block touches them | Plan 11 `B3` **and** phase 10 `TST-013` — **these two conflict** | **Binding prohibition on every block:** no block may raise the count above **3**, delete a skip, weaken a `skipif`, or convert a skip into a pass. §2.2 | Medium |
| 22 | `ffmpeg_utils.py` groups A and C | No block touches them | Ruling A makes both **permanent product surface**; group B is plan 12 `P12-B8`'s and now closed | **Binding prohibition, strengthened.** A and C survive permanently; C still spawns ffmpeg; the module is never deleted whole. `B4`'s criterion 11 makes "no hunk in `ffmpeg_utils.py`" a checked property | High |
| 23 | `ProgressManager` | No block touches it | Plan 11 `B3` (one of its members is a D-11 oracle's subject) | **Binding prohibition.** Not dead code: documented-as-retained, six test instantiations, and `tests/test_cli.py` asserts its absence from `batch_downloader`. Its inline `SRV-003` comment is a live citation `B11` resolves — that does not make the class dead | Medium |
| 24 | `check_ffmpeg_available` — **which plan's group assignment is right | No block edits it | **Three plans carried three answers.** Plan 12 §2.4.4 put it in the **dying** group and justified it as "only real users are the `download_with_ffmpeg` path"; plans 11 and 10 put it on the **surviving** side | **Resolved by ruling A: it stays — permanent product surface.** **Plan 12 was wrong**, and wrong in its *reason* as well as its conclusion: the function has a third call site, a bare statement in `perform_download` **whose return value is discarded**, and it guards the **merge**, which survives. This plan's §2.4 table already said "group B's assignment is contradicted by two other plans and by the code" before the ruling; the ruling confirms the code. Recorded so no future plan re-derives it from plan 12's stale text | High → resolved |
| 25 | `services/downloader.py`'s symbol-ownership comment vs its `__all__` | `B4` fixes it | **No plan owns it.** Introduced by `d572d96` | **New, unfiled, and in this phase's subject matter.** The comment lost four groups while `__all__` still exports 10 names those modules own, and `_attempt_segment_resume` is named but unexported — a live `mypy src tests` error. `B4`'s criterion 6 | Medium |
| 26 | `[tool.ruff] target-version` and `[tool.mypy] python_version` | `B3` owns both per `D16` | Plan 16 owns `[project] requires-python`; **nobody owns the two silent pins** | **Split by declaration, reconciled by whichever lands second.** `B3` is the only block touching `pyproject.toml`. §3.3 criterion 9 | Medium |

### 4.5 Decisions index

| ID | Decision | Default | Criterion | Block |
|---|---|---|---|---|
| `D1` | `status_label()` shape: add `ErrorCode.NO_STREAMS` with one derivation override, vs one label for both conditions | Add `NO_STREAMS` | Does `no_streams` have committed consumers? **Yes** — asserted in `tests/test_exceptions.py` and returned into the batch summary. The one-label option is defensible if the output change is accepted and reported | `B1` |
| `D2` | Shim removal in the same commit as the derivation | Same commit | Would a split be independently reviewable? No — same 11-line region, same two test classes, and `VAL-903` exists to prevent contention | `B1` |
| `D3` | `logger.error` vs `logger.exception` vs `exc_info=True` for the new `cli.py::download` arm | `logger.error` | Does phase 08's `OUT-002` plan depend on a `download_failed` record carrying `exception`? If yes, use `exc_info=True` | `B2` |
| `D4` | `user_message()` — adopt or delete | Adopt | Is it a declared public surface? No. Adopting costs one line and is reversible | `B2` |
| `D5` | `disallow_any_explicit` — global with overrides, or remove the six Pydantic sites at source | Global with overrides | **Can the six be removed at source?** If yes, prefer that — no override needed. If not, the override is the correct description of a third-party signature | `B3` |
| `D6` | `ignore_missing_imports` → `false` | OUT | Is `yt_dlp` typed in this phase? No | `B3` |
| `D7` | Split naming — new module for the retry policy, or rename the residue | New module; `downloader_throttle.py` keeps its name | The residue has **7** importers. Renaming converts a 5-importer change into a 12-importer change. Renaming pays only if the residue's honest name is worth 7 extra edits | `B4` |
| `D8` | `RETRYABLE_STATUS_CODES` moves, and `api-reference.md` is corrected in the same commit | Moves; doc corrected in the commit | The constant travels with its user, and 9 assertions vs 0 on the doc side mean the drift recurs if the doc lags | `B4` |
| `D9` | `.ai/structure/front/*` — delete or annotate | Delete both | Does any tooling or plan reference them? **No** measured reference, and `.ai/` is not packaged | `B7` |
| `D10` | The four stale line counts — correct or drop | Drop | Does anything parse the listing? **No.** A number in prose has no oracle and drifts silently | `B8` |
| `D11` | The single-source rule — amend or rely on the deletion | Amend minimally | **Which instruction produces a clean copy?** If a pipeline command does, the rule is right and the instruction is wrong — escalated with `B13` until answered | `B9` |
| `D12` | `ast-editor.md` / `morfx-tools.md` — move, annotate, or delete | Move out of `docs/99-reference/`, keep shipped | Does `.kilo` configuration consume them by path? If yes they are agent infrastructure, which argues for keeping but not shipping in `docs/` | `B10` |
| `D13` | A recoverable dead tag — repoint, inline, or delete | Repoint only where a **findings** file records the requirement; otherwise delete the parenthetical | Is the requirement in `.ai/audit/*/findings.md` (durable) or only `.ai/plans/*` (transient)? A citation to a plan dies with the plan | `B11` |
| `D14` | `docs/STRUCT.md`'s layering section — disclose the two violations | Disclose both as deliberate exceptions | Is a reader about to make a wrong decision? Yes — and a disclosure that reads as an invitation to change `cli.py` is worse than silence, so it must say the imports are deliberate | `B6` |
| `D14b` | `models/quality.py`'s mixed import form — fourth bucket or documented exception | Documented exception | Is the cycle real? Yes, and it cannot be made relative. A fourth bucket would invite a future maintainer to regularise it and reintroduce the cycle | `B12` |
| `D15` | `docs/STRUCT.md`'s `ffmpeg_utils.py` row — take or yield | **YIELD**, serialise behind `P12-B12` | Resolved, not open. §4.3 — and ruling A strengthens it, because the row is now wrong about a **permanent** module | `B6` |
| `D16` | The two silent toolchain pins — `B3` or plan 16 | **`B3` owns both** | They are the same species of defect as `QLT-009` — declared in one place, enforced nowhere — and `B3` is the only block touching `pyproject.toml`. **Whichever of `B3` or plan 16 lands second re-measures all three declarations and sets them to one value** | `B3` |

---

## 5. Risks

### 5.1 Implementation risks

| # | Risk | Blocks | Containment |
|---|---|---|---|
| I-1 | `status_label()`'s return value is **user-visible** in the batch summary, and **no test asserts `status_label()` values equal `ErrorCode` values** — the finding's own oracle gap (§2.6). A wrong choice changes printed output with nothing failing. | `B1` | `D1`'s default preserves `no_streams`. `B1`'s criterion 4 **adds the missing assertion**, which is the only durable fix. Criterion 8 requires running the batch test class before and after |
| I-2 | `D1`'s alternative — one label for both conditions — is a **reported user-visible change** with no oracle and no changelog surface. | `B1` | If chosen, it must be stated in the commit body and the block report as a deliberate output change, not an incidental one |
| I-3 | Narrowing `exceptions.py::_EXCEPTION_STATUS_HANDLERS`'s `Callable[..., str]` may fail, because a `Callable[[Exception], str]` annotation must accept every lambda in the dict — including `QualityParseError`'s, which takes the exception and reads `e.quality`. | `B3` | The annotation is verified by `mypy src`, which is clean today and must stay clean. If narrowing fails, the fallback is a per-entry `Callable[[SpecificType], str]`, not a suppression |
| I-4 | `models/quality.py::QualitySpec.__init__(**data: Any)` is **Pydantic's own signature**. `disallow_any_explicit` cannot be satisfied at source without upstream support. | `B3` | `D5`'s criterion anticipates it. A named override with a comment naming the third-party signature is the correct outcome, and `warn_unused_ignores = true` is precisely why a per-site disable comment is rejected |
| I-5 | `_wait_with_shutdown` is called by `_retry_429_with_backoff` **and directly** by `segment_downloader` and `ytdlp_downloader`. A move that updates `_retry_429_with_backoff`'s own import but not the two direct callers fails at runtime, not at collection, in paths where the symbol is only called inside a coroutine — and **`no test asserts `get_shutdown_event`'s reachability from its 7 importers** (§2.6). | `B4` | `B4`'s criteria 3 and 4 enumerate all 12 importers by name. The gates name the three test files that exercise them |
| I-6 | `services/downloader.py` re-exports `_retry_429_with_backoff` under `# noqa: F401` and lists it in `__all__`. **Editing the re-export line instead of moving the owning module is the documented failure mode** of this codebase — stated identically in plans 11 and 12. | `B4` | §2.4 item 5 makes it a standing prohibition; §4.4 row 7 records the compliance obligation; `B4`'s criterion 6 requires both the facade's ownership comment and its `__all__` to point at the new owner |
| I-7 | A "tidy the ffmpeg helpers" pass deletes group A (`iter_process_lines`, `cancel_subprocess`) or group C (the merge engine). **Per ruling A both are permanent product surface**, and `check_ffmpeg_available` is permanent too — its only call site discards its return value, which is exactly the shape that looks unused to a tidying pass. **Group A is imported directly by `ytdlp_downloader` and has no reachability oracle**; group C is the HLS segment path's only merge and **still spawns ffmpeg**. | all | §5.4 prohibitions 2 and 3. No block here edits any ffmpeg symbol, `B4`'s criterion 11 requires `git diff` over `ffmpeg_utils.py` to be **empty**, and no block's roster is scoped to that file |
| I-7b | **New at this base.** The retirement deleted four groups from `services/downloader.py`'s symbol-ownership comment and left `_attempt_segment_resume` named but unexported — a live `mypy src tests` error and a facade whose map contradicts its own `__all__`. | `B4` | Assigned to `B4` (§3.4, criterion 6) because `B4` already edits both surfaces. §4.4 row 25 records it. This is also the sharpest available illustration of §2.4 item 5: a re-export surface was edited and the ownership map was not |
| I-11 | **The retired loader's cleanup could be read as licence to clean further.** `d572d96` was clean — zero residue across `src/`, `tests/`, `docs/`, `README.md` — which makes "the ffmpeg stuff is gone, the rest of it is probably dead too" an attractive and wrong inference. `ffmpeg_utils.py` is now **permanent** and still carries the yt-dlp transport's subprocess infrastructure. | all | Ruling A is quoted in §1.6 and §5.4. `B4`'s criterion 11 makes the absence of an `ffmpeg_utils.py` hunk a **checked** property, not an intention |
| I-8 | The layering disclosure in `docs/STRUCT.md` could read as an invitation to "fix" `cli.py`'s private-symbol import — which `B2` is writing at the time. | `B6`, `B2` | `D14`'s second criterion: the disclosure must state the imports are deliberate |
| I-9 | `B3`'s override wildcard pattern, if wrong, silently exempts more or fewer modules than intended. A `[[tool.mypy.overrides]]` mistake is invisible in a passing run and durable in the repository. | `B3`, and every later block | `B3`'s criterion 3 requires a comment naming which signature requires each override; criterion 4 requires no duplicate override module. The Auditor verifies the wildcard matches exactly the intended set |
| I-10 | `B9`'s merge direction. The artifact's instruction — take the `-c` flag, the cookie source, the `true` default **and the 7-step list** all from `cli-reference-clean.md` — is **half wrong**: the 7-step list is in the *other* file (§2.5 correction 6). Following it imports the wrong step list into the surviving document. | `B9` | §2.3 records the measured divergence per row; `B9`'s roster requires the Auditor to re-derive per row rather than inherit |

### 5.2 Rollout risks

| # | Risk | Containment |
|---|---|---|
| R-1 | **Three external gates block a third of this plan.** `B4`, `B6`, `B8`, `B9` and `B11` cannot complete until plans 10, 11 and 12 have landed their tracks. Plan 10 is untracked and defers the shape of its own retirement to an open question (`Q4`). | §4.2 marks the gates explicitly. No block starts before its gate; §2.4 item 10 and §4.2's ordering are the enforcement |
| R-2 | **`EXPECTED_SDIST_ENTRIES` is a single-writer shared anchor** and three blocks write it. Two concurrent blocks produce a commit whose `tests/test_packaging.py` fails — which reads as "the fix broke packaging" and invites a revert of a correct change. | §4.4 row 15 serialises `B10` → `B9`; `B4` precedes both. Each block's criterion states the count it expects. **This coupling is recorded by no audit and no prior plan** |
| R-3 | **The three remaining D-11 skips never execute on Windows.** A decomposition, a module move, or a "simplify the `finally`" pass over any temp-file write site leaves the suite fully green while breaking owner-only confinement on every POSIX deployment. No test asserts the `chmod` call is made at all. **The retirement already removed one of the four oracles along with its subject** — correct, and it reduced the net by one. | §2.2 and §4.4 row 21. **No block here touches a temp-file write site**, but the exposure is recorded so no future block inherits it unawares |
| R-3b | **`ruff format --check src tests` was reported red and measured green** (§2.5 correction 13). A gate whose state is disputed is a gate a block may silently "fix" with a blanket reformat. | §2.2b's narrow rule: named blocks only in `TestYtDlpSubprocessShutdown`, never `ruff format src tests`. **No block may absorb the format gate silently** — it records the state and either applies the named fix or stops |
| R-4 | **`.ai/audit/**` is read-only for plan execution**, and `VAL-901`/`VAL-902`'s only remedies live there. Absorbing them would breach plan 11 `B10`'s prohibition; ignoring them leaves a CRITICAL finding unimplemented with no owner. | `B13` escalates and stops. The measurement is refreshed so the owner sees the growth, not the original filing |
| R-5 | **The stale-document warning spans six documents**, so a new maintainer's first map is wrong in ≥14 places. This plan reduces it; it cannot close it. | §5.6 records the residual so the gap is not mistaken for a fixed one |
| R-6 | Block reports inherit numbers from the artifact rather than re-measuring. Nine of them were already wrong (§2.5). | §2.7's landing rule: every block's report states which §2.3 facts it re-measured before editing |

### 5.3 Regression risks

| # | Risk | Blocks | Containment |
|---|---|---|---|
| G-1 | **15 `patch()` strings bind the five retry symbols**, not the 13 the dossier recorded (§2.5 correction 3; `VAL-903`'s own figure was 9). Only **3** name `downloader_throttle`'s own namespace and must be repointed; **12** name an importing module's re-exported attribute and are move-robust. | `B4` | `B4`'s criterion 5 requires **exactly three** changes and a `git diff` proving no other patch target was rewritten. Rewriting the 12 would be churn that also breaks unrelated tests |
| G-2 | `tests/test_downloader_throttle.py`'s single `from`-import block names all five moved symbols. Missing one is an **`ImportError` at collection**, which fails the whole file. | `B4` | Criterion 4 enumerates it; the per-block gate names the file |
| G-3 | `TestRetryableStatusCodes` asserts **9** membership facts including `408` and `425`. A constant edit fails loudly. | `B4` | This is the block's best oracle. It must stay green |
| G-4 | `TestStatusLabel` asserts **8** hard-coded label literals. `B1` must rewrite them against `ErrorCode.<MEMBER>.value` — and rewriting tests to match code is exactly what project rule 2 forbids if the code is wrong. | `B1` | Rule 2 applies: the **code** is corrected first, the tests follow. Criterion 4 adds the invariant assertion so the literals stop being the only oracle |
| G-5 | Changing `download_failed` from `logger.exception` to `logger.error` **removes the traceback** for domain exceptions — the record phase 08's `OUT-002` evidence rests on. | `B2` | `D3`. If phase 08 depends on the record's shape, `exc_info=True` |
| G-6 | **No test asserts `iter_process_lines` / `cancel_subprocess` are reachable from `ytdlp_downloader`.** An `ffmpeg_utils.py` decomposition would break group A with nothing failing. | none here | §2.6, §5.4 prohibition 2. No block in this plan decomposes `ffmpeg_utils.py`, and none is scoped to |
| G-7 | **No test asserts `models/enums.py` is the only enum module**, so rule 10 is unenforced and `B1`'s `ErrorCode` addition is unchecked against a second enum module. | `B1` | Recorded. `B1` does not create an enum module |
| G-8 | **No test asserts `docs/STRUCT.md` matches the filesystem** — `B6`'s own correctness claim is unverified by the suite. | `B6` | `B6`'s criterion 1 requires the enumeration to be produced and recorded in the block's report. **The enumeration is the gate** |
| G-9 | **`ProgressManager` must not be treated as dead code.** It is documented-as-retained, exercised six times in tests, and `tests/test_cli.py` asserts its **absence** from `batch_downloader` — a test that would fail if someone "cleaned it up". | `B4` | §4.4 row 23, §5.4 prohibition 4. `B4`'s out-of-scope names it explicitly |
| G-10 | **The three remaining D-11 skips could be lowered — and lowering one is a regression in disguise.** A skip converted to a pass on Windows would be a false green: the assertion cannot succeed there. The **fourth** oracle is already gone, deleted with its subject `_temp_argfile` by the retirement; that was correct, and it is the only legitimate shape of reduction. | all | §2.2: the count is a floor of exactly **3**. Reduction is legitimate **only** when the subject itself is deleted, never when an oracle is removed |

### 5.4 Prohibitions that survive a fix

These hold **after** every block in this plan has landed. Each is a state the repository must not reach by fixing something else.

1. **The three D-11 skips remain exactly three.** No block may raise the count, delete a skip, weaken a `skipif` condition, or convert a skip into a pass. The fourth was removed by the retirement **with its subject**, which is the only legitimate shape of reduction.
2. **`ffmpeg_utils.py` is permanent product code and is never deleted whole, and no ffmpeg symbol is deleted by this plan.** Per ruling A the module has a fixed three-part shape: **group A** (`iter_process_lines`, `cancel_subprocess`, the `cancel_ffmpeg_process` alias) is the yt-dlp transport's stdout draining and cancellation; **`check_ffmpeg_available`** is permanent, and its single bare-statement call site **discards its return value** — do not read that as deadness; **group C** (the eight merge-engine symbols) is the HLS segment path's only merge and **still spawns ffmpeg**. Group B is already deleted with **zero residue**, which makes a further sweep more tempting and more wrong.
3. **No test may assert group A's reachability in place of an import check that does not exist.** A new test that pins group A's reachability is welcome; a deletion of group A "because it is unused" is prohibited, and under ruling A it would delete permanent product code.
4. **`ProgressManager` is not dead code.** Documented-as-retained, six test instantiations, and `tests/test_cli.py` asserts its absence from `batch_downloader`. It is never filed as dead and never deleted. Its inline `SRV-003` comment is a live citation `B11` resolves — it does not make the class dead.
5. **No shared-constants module is created.** All domain enums stay in `models/enums.py`. **Rule 10's `DownloadMethod.FFMPEG` obligation is discharged — the member was deleted outright with no tombstone, and no block may reintroduce it or reintroduce tombstones for any other retired enum member.**
6. **No Polars.** Rule 11 requires it; the project has no dependency. **The divergence is recorded, not repaired.**
7. **`structlog.get_logger(__name__)` stays universal**, against rule 12's stdlib-`logging` wording. **The divergence is recorded, not repaired.**
8. **A re-export line is never the fix.** `services/downloader.py` is a facade; the owning module is the fix. Stated in plans 11 and 12 and binding here. **The retirement is a worked counter-example:** it edited the re-export surface and left the ownership map desynchronised (`B4`'s criterion 6).
9. **No identifier is invented** to fill a provenance gap. An identifier with no requirement behind it is the same defect one level down.
10. **No block edits any file under `.ai/audit/`.** Plan 11 `B10` is the only block permitted to touch `.ai/audit/templates/`, and it carries an absolute staging prohibition on `.ai/audit/99-validation/**`.
11. **No ffmpeg loader work, in either direction.** The loader path is **permanently deleted** and needs no documentation, no cleanup and no tombstone. `DownloadMethod` has two members and stays that way.
12. **No frontmatter is added to `docs/STRUCT.md`.** It is a root structural map with none and is edited in place.
13. **A behaviour change must update the comment that justifies it.** House style is dense decision-carrying comments (`D-01`, `SEC-*`, `INT-*`, `STR-008`, `CON-*`, `DF-*`, `ART-*`, `TRN-*`). Most of this phase is comment and docstring work, so this applies to nearly every block — and it is why `B5` and `B12` are separate from `B4` and `B1`: a prose fix must not be blocked behind, or bundled with, a structural decision. Ruling A sharpens it for `STR-008`: that comment is on **permanent** code now.
14. **No `print()` statements.** `logger = logging.getLogger(__name__)` per rule 12's wording; `structlog.get_logger(__name__)` per the codebase's universal practice (prohibition 7).
15. **Never `git add -A`, `git add .`, or `git add -u`.** Stage by explicit path. Commit shape `{type}({scope}): {description}`. Never amend, never force.
16. **`requires-python`, `[tool.ruff] target-version` and `[tool.mypy] python_version` must agree.** Per `D16`, a state where the package claims `>=3.14` while both tools validate `3.12` is a silent-pin defect and no block may leave it in place.
17. **No block implements the exit-code contract.** Ruling C is plan 13's; `2` and `3` are unallocated in code today and stay that way through this phase. `status_label()` values are **not** exit codes.

### 5.5 Compatibility risks

| # | Risk | Blocks | Containment |
|---|---|---|---|
| C-1 | Deleting `docs/99-reference/cli-reference-clean.md` orphans one inbound reference, in `docs/error-handling-logging-research-2025-2026.md`. | `B9` | `B9`'s criterion 6 updates it in the same commit |
| C-2 | `ast-editor.md` and `morfx-tools.md` name **each other** in their `related` arrays. Moving or deleting either orphans the other's `related` entry. | `B10` | `B10`'s criterion 3 requires both arrays to be consistent, verified by `grep` for a `related` entry naming a non-existent path |
| C-3 | `services/downloader.py`'s symbol-ownership comment and its 26-entry `__all__` both name `downloader_throttle.py` as the owner of a moved symbol. | `B4` | `B4`'s criterion 6 |
| C-4 | **`ErrorCode` gaining a member is a public-enum change.** `StrEnum` membership is used in log filters and structured output. Adding `NO_STREAMS` is **additive and safe**; **renaming or removing a member is not** and is out of `B1`'s scope. | `B1` | §3.1's semantic scope |
| C-5 | The layering disclosure makes a **rule that the code violates** visible. That is a change in what a reader can conclude, and it could be read as a rule change. | `B6` | `D14`: the disclosure must state the imports are deliberate, so it reads as documentation rather than as an invitation |
| C-6 | `B9` deletes a file a downstream consumer may vendor. Measured: exactly one inbound reference, in a research document, plus `cli-reference.md`'s frontmatter — which does **not** list the copy. | `B9` | `B9`'s criterion 7 states this was verified, not assumed |

### 5.6 Documentation risks

| # | Risk | Containment |
|---|---|---|
| DOC-1 | **Six documents are stale** (measured: `STRUCT.md`, `vkdownloader-overview.md`, `api-reference.md`, `cli-reference.md`, `cli-reference-clean.md`, `.ai/structure/*`). After this plan lands, the residual is smaller but **non-zero**, and a new maintainer's first map is still wrong in several places. | Recorded rather than claimed as fixed. §7's per-finding trace states what remains |
| DOC-2 | `B6` yields the `ffmpeg_utils.py` row. **If `P12-B12` never lands, `docs/STRUCT.md` keeps a sentence that would lead a reader to delete group A.** | `B6`'s hard start gate (§4.2, position 8) and criterion 6. The risk is that `B6` waits indefinitely — which is the correct outcome, because the sentence's cost to a reader is real and its fix is owned elsewhere |
| DOC-3 | `B8` and `B11` both edit `vkdownloader-overview.md`, in paragraphs owned by different phases, **adjacent**. A whole-section deletion takes plan 10's target with it. | `B8`'s criterion 4 and §3.8's rejected option. `B11` touches only the `SRV-001` and `SRV-006` parentheticals |
| DOC-4 | **`api-reference.md` carries two false facts.** One is assigned here (`RETRYABLE_STATUS_CODES`, to `B4`). The other — three "Location: `vkdownloader.services.ffmpeg_utils`" rows that do not distinguish the three groups — is **unowned**. | `B13` records the unowned set so it is not lost |
| DOC-5 | **Four `ffmpeg_utils.py` documentation sites are unowned**: the module docstring (which after the retirement describes only group C plus a generic utility), `services/downloader.py`'s `ffmpeg_utils` ownership group (which itself omits group A's `iter_process_lines`), and the three `api-reference.md` location rows. | `B13` records them. **No block in this plan claims them** — claiming them would mean touching ffmpeg documentation, which §1.4 forbids |
| DOC-6 | The artifact's `## The tree-drift measurement, re-performed` section is **void** and remains in a file a future planner may read. | §1.1 records it as void and states what it examined. **`.ai/audit/**` is read-only**, so the correction lives here, not there |

### 5.7 Test-pinning risks

| # | Risk | Containment |
|---|---|---|
| P-1 | **`QLT-013`'s two tests pin the floor semantics by name, not only by assertion.** `test_retry_after_overrides_delay` and `test_retry_after_ignored_when_smaller` both name the behaviour and the second asserts the floor. A refactor that "aligns the comment with the name" replaces `max()` with the header value and turns a correct 429 wait into one **shorter than its own backoff schedule**. | `B5` is comment-only and `B5`'s criterion 3 requires both tests to pass with **no change to name or expectation**. `B4`'s criterion 8 requires `_compute_backoff_delay`'s arithmetic unchanged. §3.5's rejected option names the tests read-only |
| P-2 | **`segment_downloader`'s only retry oracle patches both backoff symbols** (`TestManifestRetryComputesBackoffDelay`), so it would **not** notice a change to the `Retry-After` floor semantics. | P-1's containment. Recorded so no block treats that oracle as sufficient |
| P-3 | `tests/test_cli.py`'s `assert not hasattr(batch_downloader, "ProgressManager")` is the **only** thing keeping `ProgressManager` from being filed as dead. Deleting the assertion deletes the signal. | §5.4 prohibition 4. No block edits `tests/test_cli.py`'s existing assertions — `B2`'s additions only |
| P-4 | `B1`'s test rewrite is the largest test edit in the phase — 8 label literals plus two deleted classes. **Rule 2 applies:** tests follow corrected production code, never the reverse. | `B1`'s criterion 4 and §5.3's G-4. The new invariant assertion is the test that stops the defect recurring |

---

## 6. Task specifications

One task per block. A task names its preconditions, its steps, the gate it must pass, and what its report must contain. Scope, acceptance criteria and rosters are in §3 and are not restated here.

**Every task's report requirement is the same, and it is what makes the phase auditable:** which §2.3 facts were re-measured before editing, with both the old and new figures when they differ.

---

### 6.1 `B1` — one derivation in `exceptions.py`

**Preconditions.** None external. `HEAD = 4bf9efb`, working tree clean under `src/`, `tests/`, `docs/`.

**Steps.**
1. Re-measure: `ErrorCode`'s member set; `status_label()`'s override count; `_map_exception_to_status`'s production and test occurrence counts; `tests/test_exceptions.py`'s label-assertion count; the `batch_downloader._download_single` comment that names the shim. Record any drift from §2.3.
2. Confirm `_map_exception_to_status` still has **zero** production consumers and that no new one has appeared.
3. Settle `D1` and `D2` explicitly in the report, with the criterion from §4.5 satisfied.
4. Apply the single derivation; add `ErrorCode.NO_STREAMS` if `D1`'s default stands; delete the superseded overrides, the shim, its helper and the handler dict; update the module docstring and every comment that names the shim.
5. Rewrite `tests/test_exceptions.py`: label assertions against `ErrorCode` members; delete `TestMapExceptionToStatus` and `TestExtractionErrorStatusMapping`; remove the import. **Then add the invariant assertion that closes `QLT-010`'s oracle gap.**
6. Run `tests/test_exceptions.py`, then `tests/test_cli.py`, then `tests/test_hls_downloader.py`'s batch classes, before the full suite.

**Gate.** §3.1 criteria 1–12.

**Report must contain.** `D1` and `D2` with reasons; the label each exception class returned before and after; the re-measured facts; confirmation that the warning count did **not** rise and no claim that it fell (§2.2 correction 4).

---

### 6.2 `B2` — the exception ladders log nothing they classify

**Preconditions.** **`P11-B6` has landed** (§4.2). `B1` has landed.

**Steps.**
1. Re-measure both `cli.py` ladders' clause order and `batch_downloader._download_single`'s clause list; confirm **three** clauses log nothing (§2.5 correction 2).
2. Read phase 08's artifact and its `OUT-002` evidence record. **Settle `D3` against it** — this is the block's gating question, not a preference.
3. Settle `D4`.
4. Add the `VKDownloadError` arm to `cli.py::download` **between the `except typer.Exit` re-raise and the terminal `except Exception`**. Same shape for `cli.py::batch`. Reuse the existing event names.
5. Add `logger.error` to the three silent `batch_downloader._download_single` clauses, matching `ExtractionError`'s existing shape.
6. Confirm `_PreambleFailure` still subclasses `Exception` and not `VKDownloadError` **at edit time**, not from this plan.
7. Add tests to `tests/test_cli.py` asserting a record is emitted per new arm. **Additions only.**
8. Run `batch_downloader`'s own test class before and after and diff the status tuples it returns.

**Gate.** §3.2 criteria 1–12.

**Report must contain.** `D3` with the phase-08 evidence it was settled against; confirmation that the four hand-written messages are byte-identical; the record count before and after, so plan 11's inventory can be checked.

---

### 6.3 `B3` — make rule 9 enforceable

**Preconditions.** `B1` and `B2` have landed. **`B3`'s Researcher's library-semantics answer is in hand.**

**Steps.**
1. Re-run all three probes; record the figures or their drifted equivalents. **At `09f1b10` the `Any` count is 11 in 8 files and did not move** — but re-measure rather than inherit that (§2.5 correction 15).
2. Research, then settle `D5`: **can the six Pydantic-inherited sites be removed at source?** Prefer that outcome and say so if it holds.
3. Settle `D6` (default: OUT).
4. **Settle `D16`.** Read `[project] requires-python`, `[tool.ruff] target-version` and `[tool.mypy] python_version`. If plan 16 has not landed, set both tool pins to the floor ruling B establishes. If it has, verify all three already agree and record that this block did not re-edit them. **Re-measure; never inherit.**
5. Edit `pyproject.toml`: add the flag, add or merge the overrides, and **verify the wildcard matches exactly the intended module set** — a too-broad pattern is a silent exemption.
6. Convert the five real explicit `Any`, including `cli.py::_quality_option` → the nameable Typer option type, and `exceptions.py::_EXCEPTION_STATUS_HANDLERS` if it still exists after `B1`.
7. Record the `tests/` `# type: ignore` count before and after.
8. Run `mypy src`, then `mypy src tests` **as a delta only**.

**Gate.** §3.3 criteria 1–11.

**Report must contain.** `D5`, `D6` and `D16` with reasons; every override with the signature that requires it; **the three version declarations' values before and after**; the `mypy src tests` delta with its direction stated.

---

### 6.4 `B12` — record the mixed import form

**Preconditions.** `B3` has landed.

**Steps.** Re-measure the 16 / 3 / 7 / 1 census. Confirm `models/quality.py`'s two import forms and the cycle they resolve. Add the comment on the lazy absolute import. Re-read `exceptions.py`'s deferral comment and leave it. Record the taxonomy, **and report if no convention document exists** rather than creating one.

**Gate.** §3.12 criteria 1–7. **Report must contain.** The re-measured census.

---

### 6.5 `B5` — the `Retry-After` comment

**Preconditions.** None. Safe to land at any point in the order.

**Steps.** Correct the preference comment and the docstring to state the floor. **Touch nothing else in the module.** Run `tests/test_downloader_throttle.py` and confirm both floor tests pass unchanged.

**Gate.** §3.5 criteria 1–6. **Report must contain.** `git diff` showing comment and docstring lines only in `_compute_backoff_delay`.

---

### 6.6 `B4` — split `downloader_throttle.py`

**Preconditions.** **`P12-B6`, `P12-B7`, `P12-B8` have landed** (`segment_downloader.py`). **`P11-B2` and `P11-B5` have landed** (`ytdlp_downloader.py`).

**Steps.**
1. **Re-derive the block's premise.** The artifact's "no caller" claim is refuted (§2.5 correction 5). Measure the residue's importer count and the retry surface's importer count before acting.
2. Re-census the `patch()` strings. The figure has moved 9 → 13 → 15; **do not inherit 15** — count again.
3. Settle `D7` and `D8`.
4. Create the retry module with the five moved symbols. **No ffmpeg symbol moves.**
5. Update the 4 production importers and the facade's ownership comment and `__all__`. **Then fix the facade defect the retirement introduced** (§3.4): restore the four ownership groups the retirement dropped, and make `_attempt_segment_resume`'s presence in the comment agree with its presence in `__all__`.
6. Update the test `from`-import block and **exactly 3** `patch()` strings. Verify the other 12 are untouched.
7. Correct `api-reference.md`'s `RETRYABLE_STATUS_CODES` row **in this commit**.
8. If a file was created, edit `tests/test_packaging.py`'s frozensets **in this commit** and report the new counts.
9. Confirm `_compute_backoff_delay`'s arithmetic is byte-identical and both floor tests pass.
10. Run the four named test files, then the full suite.
11. **Confirm `git diff` over `services/ffmpeg_utils.py` is empty.** Per ruling A the module is permanent and outside this block's split (§1.6).

**Gate.** §3.4 criteria 1–14. **Report must contain.** The re-derived premise; the re-censused patch count broken into breaking and robust; `D7`/`D8` with reasons; the frozenset counts if a file was created; **the facade defect's before and after**; the empty `ffmpeg_utils.py` diff.

---

### 6.7 `B6` — `docs/STRUCT.md`

**Preconditions.** **`P12-B12` has landed.** `B4` has landed.

**Steps.**
1. Enumerate every `.py` path under `src/vkdownloader/` and record the enumeration. **This is the gate, because no test checks this file (§2.6).**
2. Correct the seven named rows; add the two missing ones; correct `utils/__init__.py`'s export inventory to five names.
3. Write `downloader_throttle.py`'s row against the **post-`B4`** module.
4. Settle `D14` and write the layering disclosure: the entry layer's private-symbol import and the models layer's cycle-breaking upward import, each marked deliberate.
5. Verify `git diff` shows **no hunk touching the `ffmpeg_utils.py` row**.

**Gate.** §3.6 criteria 1–11. **Report must contain.** The enumeration; the `P12-B12` provenance of the `ffmpeg_utils.py` row.

---

### 6.8 `B7` — the structure maps

**Preconditions.** `B6` has landed, so the tree is final.

**Steps.**
1. Re-enumerate the modules and diff against `py_map.yaml`'s entries. **Do not inherit 23 or 31.**
2. Name all four recorded-but-absent symbols; `QualityEnum` and `_parse_quality_to_enum` are two of them.
3. Re-attribute `cli.py`'s entry to the modules that own its symbols.
4. Resolve the `builders/` prefix: every anchor must become repository-relative and checkout-reproducible, or be removed. Verify each distinct prefix with `git check-ignore`.
5. Settle `D9` for the two `front/` maps.
6. Fix `map.md`'s `.pyc` entries.
7. Record the regeneration procedure in the map's own header.

**Gate.** §3.7 criteria 1–11. **Report must contain.** The enumeration and the diff; every prefix tested against `git check-ignore`; `D9`'s resolution.

---

### 6.9 `B10` — the two misplaced reference documents

**Preconditions.** None externally. **`B9` must not run concurrently** (§4.4 row 15).

**Steps.** Determine whether `.kilo` configuration consumes either file by path. Settle `D12`. Execute the resolution — move, annotate or delete — and edit `EXPECTED_SDIST_ENTRIES` **in the same commit**, updating the count to 72 (moved), 70 (deleted), or the correct new names. **If either file moves or is deleted, update both `related` arrays in the same commit.** Verify with `grep` that no `related` entry names a non-existent path. Quote each file's self-disclaimer accurately — **and do not carry `B9`'s mojibake argument across to `ast-editor.md` (§2.5 correction 7).**

**Gate.** §3.10 criteria 1–8. **Report must contain.** `D12` with the `.kilo` lookup result; the frozenset count before and after.

---

### 6.10 `B9` — collapse the two CLI references

**Preconditions.** **`P10-B10` has landed** — it has. `B10` has landed, so the frozenset is single-writer.

**Steps.**
1. Re-measure the divergence **per row** (§2.5 corrections 6 and 18 — the merge is bidirectional and there are now **four** divergences, not three). Settle which file is correct for `--ssl-verify` and which for the batch step list. **Do not follow the artifact's merge direction.**
2. Settle `D11`, or record that it is pending `B13`'s answer and apply the default.
3. Apply the correct `--ssl-verify` default to `cli-reference.md`.
4. Confirm `cli-reference.md`'s **7-step** batch list matches the code and that the 6-step list appears nowhere.
5. Delete `cli-reference-clean.md`, **including its `--method ffmpeg` usage example** — which is the retirement-introduced fourth divergence, and which `cli-reference.md` has already corrected.
6. Edit `EXPECTED_SDIST_ENTRIES` to **72** in the same commit. `EXPECTED_WHEEL_ENTRIES` stays at 32.
7. Update the one inbound reference in `docs/error-handling-logging-research-2025-2026.md`.
8. Confirm neither file's frontmatter changed and that `cli-reference.md` never listed the deleted copy.
9. Touch no cookie-source row, no `--quality` row and no `--method` help text — all four documents already agree on those.

**Gate.** §3.9 criteria 1–12, with `tests/test_packaging.py` explicitly green. **Report must contain.** The per-row divergence with the direction taken; both frozenset counts; `D11`'s resolution or its pending status.

---

### 6.11 `B8` — the overview document

**Preconditions.** **`P10-B10` has landed** — it has, and it updated seven documentation sites while leaving two false facts in this file. `B4` has landed (line counts).

**Steps.**
1. Re-census all nine `__all__` lists and the facade's reachability. **Do not inherit 30 or 27.**
2. Confirm `DownloadProgress` and `eta_seconds` still occur **0 times** in `src/`, `tests/` and `docs/`. **The section is already gone — verify, do not re-delete.**
3. Re-measure the four line counts against the post-`B4` tree. Settle `D10`.
4. Remove the universal-export claim, or scope it to a named module.
5. **Remove `ffmpeg` from the `--method` row**, matching `cli.py`'s actual help.
6. **Rewrite the `ffmpeg_utils.py` listing line** to describe the module as it is: permanent, carrying the shared subprocess infrastructure, the availability probe and the segment merge engine — **not** progress parsing, which is deleted. **This is a different document from `docs/STRUCT.md`; §4.3's yield is not engaged.**
7. Resolve the line counts per `D10`.
8. **Record, per ruling D, that `QLT-005`'s severity rationale is now internal** — the census matters because the project's own test tree resolves through the facade's `__all__`, not because a consumer imports it. No edit follows from this; it is a report requirement.

**Gate.** §3.8 criteria 1–8. **Report must contain.** The re-censused export figures; the four line counts before and after `B4`; the ruling-D severity note.

---

### 6.12 `B11` — the dead provenance identifiers

**Preconditions.** **`P10-B7` and `P10-B10` and `P11-B4` have landed**, so the comments they rewrite are final. `B4` has landed (it moves comments in `downloader_throttle`).

**Steps.**
1. **Classify every citation site as surviving or dying before editing anything.** A dying site's citing line goes with plan 10's deletion; editing it races that commit. This classification is the task.
2. Settle `D13`, with its durable-record criterion stated.
3. For each surviving site: repoint it if a **findings** file records the requirement, inline the requirement as prose if it is short and real, or delete the parenthetical if the surrounding prose already states the rationale in full.
4. **Do not invent an identifier.** Report must contain no new `INT-`/`SRV-` token.
5. Confirm `ffmpeg_utils.py`'s `STR-008` comment on `iter_process_lines` is present and accurate — group A survives.
6. Verify against the `P10-B10` diff that no dying site was touched.

**Gate.** §3.11 criteria 1–8. **Report must contain.** The full site list with survival status and resolution; every retained tag with the findings file that records its requirement.

---

### 6.13 `B13` — the escalation

**Preconditions.** None. **Runs first** (§4.2, position 1) and may run in parallel with anything.

**Steps.**
1. Re-measure the `VAL-` namespace: occurrence count, distinct count, per-identifier frequency, bands in use, and whether an unparseable `VAL-` token exists. **Do not inherit 553 / 52.**
2. Verify the three mutually exclusive `VAL-003` claims still stand and record which one `VAL-902` establishes as non-reproducing.
3. Confirm the authorisation wall: that both remedies require editing under `.ai/audit/99-validation/`, that plan 11 `B10`'s prohibition covers that path, and that no document authorises this phase.
4. Compose the escalation: what each finding is, why each is unimplementable, the options (authorise phase 09; assign to a phase without the prohibition; record as permanently unfixed), and which is recommended.
5. Add: plan 11's two wrong `QLT-004` citations as a live instance; the four unowned `ffmpeg_utils.py` documentation sites; the `D11` question; the malformed `refine.md`.
6. Post the note to the board and record it in the block's report.

**Gate.** §3.13 criteria 1–7. **Report must contain.** The measured figures beside the artifact's own; the options; the recommendation; the `D11` question stated as a question.

---

## 7. Verification strategy

Three layers: a per-block gate, an end-of-plan gate, and a per-finding trace showing what closes a finding and what the plan deliberately leaves open.

### 7.1 Per-block gates

Every block runs the full four-gate suite before landing. There is no "docs-only, skip the suite" exemption: a documentation block that skips the suite cannot prove it skipped it safely, and the frozenset coupling means a "docs-only" block may not be docs-only.

```powershell
uv run pytest -q -rs              # 759±n passed, EXACTLY 3 skipped, warnings ≤ 1
uv run ruff check src tests        # clean
uv run ruff format --check src tests # N files already formatted
uv run mypy src                    # clean, 31 source files
```

Additional per-block gates:

| Block | Additional gate |
|---|---|
| `B1` | `tests/test_exceptions.py` alone; then `batch_downloader`'s own class, diffed for identical status tuples |
| `B2` | `D3` settled in the report; `tests/test_cli.py` green with **additions only**; both `cli.py` ladders re-read for clause order |
| `B3` | `mypy --disallow-any-explicit src` → **0**; `mypy src tests` reported as a delta against 79 / 8, direction stated |
| `B4` | The four named test files green; `git diff` shows **exactly 3** patch-target rewrites; the residue's 7 importers import cleanly; `_compute_backoff_delay`'s arithmetic byte-identical |
| `B5` | `tests/test_downloader_throttle.py` green; both floor tests pass with **no** name or expectation change |
| `B6` | The module enumeration, produced and recorded — **this is the gate, because no test checks the file** |
| `B7` | The enumeration diff; every distinct anchor prefix tested against `git check-ignore` |
| `B8` | `git diff` shows the `--method` row and the `ffmpeg_utils.py` listing line corrected; `DownloadProgress`/`eta_seconds` still at 0 |
| `B9`, `B10` | `tests/test_packaging.py` explicitly green; all four frozenset counts reported (73 → 72, 32, 2, 4) |
| `B11` | `grep` for new `INT-`/`SRV-`/`STR-` tokens returns none; `ffmpeg_utils.py`'s `STR-008` comment present; the census lists 8 identifiers and all 23 sites |
| `B12` | The re-measured 16 / 3 / 7 / 1 census; no import statement changed |
| `B13` | `git diff` shows **no** change under `.ai/` and **no** change under `.kilo/` |

### 7.2 Skip-count and warning discipline

- **Exactly 3 skips, no more, ever.** A block that produces a fourth is blocked. §2.2 and §5.3 G-10.
- **Warnings ≤ 1, and the count must not rise.**
- **No block may claim the warning count falls.** §2.2 and §2.5 correction 4: the warning's attribution **moved between two test methods in the same file** across the two bases with no edit to the shim, which settles it as a cross-test GC artefact. Deleting the shim is not predicted to remove it. `B1`'s report must not say so. The creator is **phase 10's** subject.
- `create=True` remains **0 occurrences** in `tests/`.
- **If `ruff format --check src tests` is red when a block starts**, the fix is the named blocks in `TestYtDlpSubprocessShutdown` only. Never a blanket reformat. Never absorbed silently. §2.2b.

### 7.3 End-of-plan gate

Run once, after `B11` — or after the last block that lands if the external gates truncate the plan:

```powershell
uv run pytest -q -rs
uv run ruff check src tests
uv run ruff format --check src tests
uv run ruff check .
uv run mypy src
uv run mypy src tests                                    # delta only: 89 at 09f1b10, reported with direction
uv run mypy --disallow-any-explicit src                   # must be 0
uv run mypy --disallow-any-unimported src                 # reported, not gated (D6)
```

Plus the phase-level structural assertions, none of which any test performs:

| Assertion | Method |
|---|---|
| `docs/STRUCT.md` names every `.py` path under `src/vkdownloader/` | Enumeration, produced at the end and diffed against the file |
| `.ai/structure/back/py_map.yaml` records the same module set | Enumeration diff; zero recorded-but-absent symbols |
| No anchor in `.ai/structure/` resolves into a gitignored path | Every distinct prefix against `git check-ignore` |
| `grep` for `_map_exception_to_status` over `src/` | **0 hits** |
| `grep` for `DownloadProgress` and `eta_seconds` over `src/`, `tests/` and `docs/` | **0 hits** |
| The two CLI reference files no longer declare the same `id`, and the merge census is fully discharged | Frontmatter census; **four** divergences recorded, not three |
| `ffmpeg_utils.py`'s group A symbols, `check_ffmpeg_available` and every group C symbol still resolve | Import check, per §5.4 prohibition 2 and ruling A |
| `git diff --stat` over `src/vkdownloader/services/ffmpeg_utils.py` | **Empty for every block in this phase.** The module is permanent and outside this plan's edit surface (§1.6) |
| Every `INT-` / `SRV-` citation from shipped source and documents resolves or is gone | Site-by-site list from `B11`'s report |
| Both CLI reference files no longer declare the same `id` | Frontmatter census |
| `EXPECTED_SDIST_ENTRIES` and `EXPECTED_WHEEL_ENTRIES` match the real tree | `tests/test_packaging.py` |
| The `ffmpeg_utils.py` group A and group C symbols all still resolve | Import check, per §5.4 prohibition 2 |
| `models/enums.py` is still the only enum module | Enumeration |
| Nothing under `.ai/audit/` changed | `git diff --stat` over the whole phase |
| Nothing under `.kilo/` changed | `git diff --stat` over the whole phase |
| No ffmpeg symbol was deleted or renamed by this phase | `git diff` over `ffmpeg_utils.py` — expected **empty** |

### 7.4 Per-finding verification trace

| Finding | Closed by | Verified by | **Left open, deliberately** |
|---|---|---|---|
| `QLT-001` | `B1` | Label assertions against `ErrorCode` members; the new invariant assertion; identical batch status tuples | Whether `no_streams` should exist as an `ErrorCode` member at all — that is `D1`, and it is **recorded**, not decided by this plan |
| `QLT-002` | `B2` | Every ladder clause emits; the new invariant that no clause returns silently; additions to `tests/test_cli.py` | Whether `user_message()` should be deleted — `D4`, default adopt |
| `QLT-003` | `B6` | The module enumeration; zero hunk on the `ffmpeg_utils.py` row | The `ffmpeg_utils.py` row itself — **yielded to `P12-B12`** (§4.3). Also: no test checks the file, so the enumeration **is** the verification |
| `QLT-004` | `B7` | Zero phantom symbols; zero present-but-unrecorded; every anchor checkout-reproducible | Whether the maps should be generated rather than hand-maintained — rejected as out of scope, recorded |
| `QLT-005` | `B8` | `grep` returns 0 for `DownloadProgress` and `eta_seconds`; no universal-export claim survives; the `--method` row matches `cli.py`; the `ffmpeg_utils.py` listing describes the permanent module | Per ruling D the finding's **value is reduced, not zero** — with nothing published the census matters because the test tree resolves through the facade's `__all__` (§2.9). Recorded as a report requirement, not an edit |
| `QLT-006` | `B9` | One `id: cli-reference`; the correct default; the 7-step list; `EXPECTED_SDIST_ENTRIES` = 72 | `D11`'s underlying question — **which instruction produces a clean copy** — escalated with `B13` |
| `QLT-007` | `B11` | Every citation resolves or is gone; **no invented identifier**; `STR-008` on group A intact | **Scope shrank at `09f1b10`** from 11+ identifiers to 8, all surviving; `INT-008` is **new** and must be added to the census |
| `QLT-008` | `B10` | A recorded resolution per file; `related` consistency; the frozenset updated in the same commit | Per ruling D the **value is unchanged** — the sdist is still built and still asserted by `tests/test_packaging.py`, so the frozenset coupling that makes `B10` risky is entirely internal (§2.9) |
| `QLT-009` | `B3` | `--disallow-any-explicit src` → **0**; every override carries a reason; no duplicate override module; **all three Python version declarations agree** | Whether the six Pydantic sites are removable at source — `D5`'s criterion, decided by the Researcher, reported either way. **Per §2.5 correction 15 the `Any` count did not move at `09f1b10`, so the finding is not self-resolving.** `D6` (`ignore_missing_imports`) stays OUT |
| `QLT-010` | `B1` | **The invariant assertion this finding notes is missing now exists** — that assertion is the durable fix, not the deleted literals | — |
| `QLT-011` | `B4` | The five symbols in one module; the residue in the other; all 12 importers; exactly 3 patch rewrites; the facade's comment and `__all__` agree | `ProgressManager`'s future — **not dead code**, and `tests/test_cli.py` asserts its absence from `batch_downloader`. Also: **the facade defect the retirement introduced** (§2.5 correction 12) rides in this block, unfiled elsewhere |
| `QLT-012` | `B12` | The lazy import's comment names the cycle it breaks; the 16 / 3 / 7 / 1 census recorded | Whether the taxonomy belongs in a document that does not exist — **recorded, not created** |
| `QLT-013` | `B5` | Comment and docstring state the floor; both floor tests pass **unchanged**; the arithmetic is untouched | — |
| `VAL-901` | **NOT closed.** `B13` escalates. | The refreshed measurement, so the owner sees the 12.6× growth | Everything. **CRITICAL and unimplementable under the current authorisation** (§3.13, §4.4 row 17) |
| `VAL-902` | **NOT closed.** `B13` escalates. | The re-check that its premise is partly obsolete — the stale catalogue was retired | Everything. Also requires writing under `.ai/audit/99-validation/` |
| `VAL-903` | **Discharged, not implemented.** Its ordering constraint is satisfied by `B1`'s construction; its blast-radius census is re-measured in `B4` and found to be **15 patch strings, not 13** | `B1`'s single change over the shared region; `B4`'s exactly-3 rewrites | — |
| Warning 1 — stale documents | **Partially.** Six documents, five blocks | The end-of-plan structural assertions | **The residual is smaller and non-zero.** A new maintainer's first map is still wrong in several places |
| Warning 2 — `refine.md` malformed | **NOT closed.** `B13` records. | The recorded observation | Unowned. No plan touches `.kilo/commands/audit/` |
| Warning 3 — no shared provenance registry | **Addressed in posture.** `B11` deletes or re-points; nothing is invented | `grep` for new tokens returns none | A registry is **rejected**, not deferred — a registry of twelve tags with no bodies is a larger instance of the defect |
| Warning 4 — `VAL-903`'s premature rollout estimate | **Corrected.** The patch-string count is 15, not 9 and not 13 | `B4`'s re-census | — |
| Warning 5 — the tree-drift measurement is void | **Recorded** in §1.1 and §5.6 DOC-6 | §1.1's statement of what it examined | The artifact itself — **`.ai/audit/**` is read-only** |
| Warning 6 — `AGENTS.md` cited where absent | **Confirmed by measurement.** No `AGENTS.md` at the repository root | §2.3's status line | — |

### 7.5 What this plan will not have achieved

Stated plainly so the end-of-plan report does not overclaim:

1. **`VAL-901` remains CRITICAL and unimplemented.** Not by oversight — by authorisation. `B13` is the deliverable.
2. **`VAL-902` remains unimplemented**, for the same reason.
3. **`docs/STRUCT.md` will still be wrong about one module** if `P12-B12` never lands. `B6` waits rather than writes a row it is not entitled to write — and after ruling A that row now misdescribes a **permanent** module, so the wait is more expensive than it was.
4. **The stale-document problem is reduced, not closed.** §5.6 DOC-1. The retirement fixed seven sites and left at least **three** new ones: this plan assigns two to `B8` and one to `B9`, and §5.6 DOC-4/5 records the unowned remainder.
5. **`ffmpeg_utils.py`'s module docstring and `services/downloader.py`'s `ffmpeg_utils` ownership group stay wrong**, and are now wrong about permanent code. §5.6 DOC-5. **This plan will not fix them**, and saying so is the point: claiming them would mean editing ffmpeg documentation, which §1.4 forbids.
6. **The single pytest warning will probably still be there.** §2.2 correction 4, §7.2. Its creator is phase 10's subject.
7. **The four D-11 skips will be three, not four — already so, by a landed commit outside this plan.** §2.2. The fourth went with its subject.
8. **`pyproject.toml` still says `ignore_missing_imports = true`**, so `yt_dlp` remains invisible to the type checker. `D6`, default OUT. **Per `D16`, `B3` reconciles `requires-python`, `target-version` and `python_version` to one value** — but `requires-python` itself is plan 16's change, so the reconciliation may simply confirm plan 16's work.
9. **Two rules remain violated and unrepaired**: no Polars (§5.4 prohibition 6) and stdlib logging (§5.4 prohibition 7).
10. **The exit-code contract remains unimplemented.** Ruling C is plan 13's; `cli.py` still produces only `1` and `130`, and `2` and `3` are unallocated. §2.9.
11. **Phase 11's two wrong `QLT-004` citations remain wrong.** Recorded, not corrected — plan 11 is not this plan's file.
12. **`check_ffmpeg_available` looks dead and is not.** Its only call site discards its return value, which is exactly the shape a tidying pass removes. Ruling A makes it permanent; §5.4 prohibition 2 makes that binding.
13. **`services/downloader.py`'s ownership map stays wrong until `B4` lands** — and nothing else in this plan fixes it, because no other block edits that file's `__all__`.

---

## 8. Plan record

**Artifact:** `.ai/audit/99-validation/09-code-quality-validated-findings.md`
**Plan base:** `HEAD = 09f1b10` (first drafted against `4bf9efb`; re-baselined after the ffmpeg retirement `d572d96` and three subsequent commits)
**Rulings folded in:** A (ffmpeg — segment merge and subprocess infrastructure are permanent), B (Python floor `>=3.14`, enforcement evidence here), C (exit-code contract, recorded), D (not published, recorded). §1.0, §1.6, §2.9.
**Blocks:** 13 — `B1`–`B13`
**Order:** `B13 → B1 → B2 → B3 → B12 → B5 → [external gates] → B4 → B6 → B7 → B10 → B9 → B8 → B11`
**Findings closed:** 11 of 13 `QLT-` findings, plus `VAL-903`'s ordering constraint
**Findings escalated, not closed:** `VAL-901` (CRITICAL), `VAL-902`, plus all 6 recorded warnings
**Open decisions:** `D1`–`D16`, each with a default and a criterion — §4.5
**Corrections to the artifact, the brief, and the rulings:** 16, all measured — §2.5
**Yielded to another plan:** `docs/STRUCT.md`'s `ffmpeg_utils.py` row — §4.3, strengthened by ruling A
**Resolved three-way disagreement:** `check_ffmpeg_available` stays; plan 12 was wrong — §4.4 row 24
**Newly found and assigned:** the facade defect `d572d96` introduced in `services/downloader.py` — §2.5 correction 12, `B4`, §4.4 row 25
**Blocks removed by the rulings:** none. This plan never proposed an `ffmpeg_utils.py` decomposition — §1.6
**Couplings recorded by no prior audit or plan:** the `EXPECTED_SDIST_ENTRIES` / `EXPECTED_WHEEL_ENTRIES` dependency of `QLT-006` and `QLT-008` — §2.4 item 1, §4.4 row 15