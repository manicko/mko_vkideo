---
source_plan: .ai/plans/11-credentials-secrets-audit-fixes.md
source_spec: .ai/audit/99-validation/06-credentials-secrets-validated-findings.md
baseline_head: 36b801e
measured_at: 2026-10-04
status: ready-for-execution
---

# Execution plan — credentials and secrets audit fixes (plan 11, re-baselined)

**This plan supersedes the execution half of plan 11.** Plan 11 remains the historical
record and is not modified. Where the two disagree, this plan wins, because every number
in it was re-measured on the live tree at `36b801e`. Nine specific corrections are carried
in §2; every one of them voids a gate that an Implementor would otherwise inherit.

**Blocks `B1` and `B2` of plan 11 are new execution records, not new work.** `B1` is
closed. `B2` landed with a HIGH defect that no existing test can see, and it decomposes
into three blocks: `R1` (removability — the HIGH defect), `R2` (the sweep's creation
race), `R3` (the legacy residue — **conditional**, blocked on a product answer in §9).

**Vocabulary.** `EB-n` prefixes an execution block introduced by this plan. A bare `Bn`
prefix is a plan-11 block carried forward unchanged in scope, with its corrected
baseline and its narrowed scope stated here.

---

## §1 Execution record

| Block | Finding | Status at `36b801e` | Commit | Gates / defect |
|---|---|---|---|---|
| `B1` | `SEC-009` | **LANDED — closed** | `f6e8ebe` | All four acceptance criteria met: the Netscape `include_subdomains` column is derived from the domain's own leading dot; the dotless round trip survives the installed `YoutubeDLCookieJar` on its own and in a mixed file; the dotted case is unaffected; the existing test class was extended rather than replaced. No further work. |
| `B2` | `SEC-001`, `SEC-002`, `VAL-602` | **PARTIAL — HIGH defect** | `36b801e` | Acceptance criterion 1 **fails**: the per-run directory is never removed. Acceptance criterion 8 **violated**: `test_file_created_in_system_temp_dir` was renamed to `test_file_created_in_private_cookie_subdir` and its expectation inverted, which plan 11 declares a design failure rather than a test update — the commit does not record it as one. `T-B2` step 12 **unmet**: the commit message body is empty, so `D-1`'s citation, `D-2`'s deferral and `D-3`'s anchor note survive nowhere. `VAL-602` narrowed, not closed: a PID-less directory is still swept. The real `SEC-002` residue is untouched. Split into `R1`, `R2`, `R3`. |
| `R1` | `SEC-002` (removability) | **LANDED — closed by `72c8283`** | `72c8283` | `SEC-002` closed by Validator adjudication: **ACCEPT WITH REQUIRED FOLLOW-UP** (`V-1` provenance defect, commit-body only). Gates: 820 passed / 6 skipped; `test_hls_downloader.py` 192 passed / 2 skipped; `ruff check` clean; `ruff format --check` clean (54 files); `mypy src` clean; `mypy src tests` 93 errors in 8 files; skips 6 = 3 D-11 + 3 pre-existing `killpg`; residue 0 directories in `%TEMP%`. |
| `R2` | `VAL-602` (creation race) | PENDING | — | New block. |
| `R3` | `SEC-002` (legacy residue) | **BLOCKED on §9 Q1** | — | New, conditional. Does not start until the Product Owner answers. |
| `B3` | `SEC-003` | PENDING | — | Narrowed: three oracles plus `D-4`. Test-only (§2.6). |
| `B4` | `SEC-006` | PENDING | — | Narrowed: documentation duty reduced to two items (§2.7). |
| `B5` | `SEC-005` | PENDING | — | Format obligation void; mypy gate re-based. |
| `B6` | `SEC-007` | PENDING | — | Highest risk. Enumeration corrected to 21 names / 24 sites; traceback population corrected to 8 (§2.4). |
| `B7` | `SEC-008` | PENDING | — | Unchanged in scope. |
| `B8` | `SEC-010` | PENDING | — | Unchanged in scope. `D-9` deferred to §9 Q3. |
| `B9` | `VAL-601` | PENDING | — | Unchanged in scope. |
| `B10` | `VAL-603` | PENDING | — | Evidence falsified; default flipped to `Alt A`; `06`'s own zero-table is the live instance (§2.5). |

**What `B2` got right and must be preserved, not rewritten.** The per-run private
directory creation; the `owner.pid` record; the liveness-gated sweep; `atexit` registered
once; the frozen strings `vk_cookies_`, `.cookies.txt` and the call `os.chmod(path,
0o600)`; the `try`/`except OSError`/`else` teardown in `_download_with_ytdlp`'s
`finally`, with `cookie_file_cleanup_failed` on a failed destroy and
`cookie_file_cleaned_up` on success; the `DF-007:` comment correction; `D-2`'s deferral
(no `pywin32`, no ctypes ACL reader); `D-3`'s module-level anchor; and **no top-level glob
and no age heuristic**. `D-1` is implemented **correctly** and must survive intact:
`_is_pid_alive` branches on `os.name == "nt"` and uses `ctypes` `OpenProcess` with
`PROCESS_QUERY_INFORMATION` (not `SYNCHRONIZE`), then `GetExitCodeProcess` and
`CloseHandle`, treating `259` / `STILL_ACTIVE` as alive; `os.kill(pid, 0)` is POSIX-only.
Nobody may "simplify" that away — see §6.

---

## §2 Corrected baseline

### 2.1 The baseline moved 21 commits, not 2

Plan 11's execution record was written at `58bb7ce`. The tree is at `36b801e`.
**`git rev-list --count 58bb7ce..36b801e` returns 21.** Plan 11's second revision treated
the move as two commits (its own two landed blocks). Every number it cited was measured
before nineteen other commits landed, including `12d97d4` (phase 05, which added skips),
`486bfd9` (which pre-sanitised two records `B6` would otherwise wrap) and `db0e33e` /
`feea5c8` (which added the overrun records `B6` must now count).

### 2.2 Measured baseline at `36b801e` — this table replaces plan 11's

| Command | Measured | Plan 11's number | Verdict |
|---|---|---|---|
| `uv run pytest -q -rs` | **812 passed, 6 skipped, 1 warning in 38.91s**, exit 0 | 752 passed, 3 skipped | **void** |
| `uv run ruff check src tests` | `All checks passed!`, exit 0 | clean | confirmed |
| `uv run ruff format --check src tests` | **54 files already formatted, exit 0 — GREEN** | "red on `tests/test_hls_downloader.py`, exit 1" | **void — plan 11 is wrong** |
| `uv run mypy src` | `Success`, 31 source files, exit 0 | clean | confirmed |
| `uv run mypy src tests` | **93 errors in 8 files** | 86 in §2.1/§7.2 **and** 79 in §5.4/`T-B7` | **void — plan 11 contradicted itself, and both values are stale** |
| `uv run pytest tests/test_packaging.py -q` | 14 passed | green | confirmed |

`mypy src tests`'s eight error files: `tests/test_quality_spec.py`,
`tests/test_progress_display.py`, `tests/test_extractor.py`,
`tests/test_segment_downloader.py`, `tests/test_hls_downloader.py`,
`tests/test_downloader.py`, `tests/test_batch_downloader.py`, `tests/test_config.py`.

**Collapsed delta gate: `mypy src tests` ≤ 93.** 86 and 79 are both void. Plan 11 states
86 in its baseline and its end-of-plan gate, and 79 in `§5.4` and in `T-B7`'s own gate —
two different numbers for the same command on the same tree, neither of which matches
either of the two measurements. Any Implementor who inherits either number is wrong.

### 2.3 The format gate is green — every "must reformat or explain the pre-existing red" obligation is deleted

Plan 11 attaches the sentence *"Never fold an unrelated reformat into a test-semantics
change"* to `B3`, `B5`, `B6` and `B7`, and carries an exception clause in its end-of-plan
gate. All of it is void: the gate passes. There is no pre-existing red to account for.
`ruff format --check src tests` in §7 is a plain pass condition with no escape hatch, and
the commits that touch `tests/test_hls_downloader.py` must leave it formatted without
introducing a formatting commit.

### 2.4 Skip identity — all six, and the D-11 floor is still exactly three

| # | Test | Origin |
|---|---|---|
| 1 | `tests/test_config.py` … `test_log_file_created_with_owner_only_permissions` | **D-11** — the `SEC-003` log-file oracle |
| 2 | `tests/test_config.py` … `test_existing_log_file_permissions_updated` | **D-11** |
| 3 | `tests/test_hls_downloader.py` `TestCreateTempCookieFile::test_file_permissions_are_0600` | **D-11** — the `SEC-003` artefact oracle |
| 4 | `tests/test_ffmpeg_utils.py::…::test_killpg_called_when_returncode_none` | **not D-11** — added by `12d97d4` (phase 05), `"POSIX-only: killpg path"` |
| 5 | `tests/test_ffmpeg_utils.py::…::test_killpg_skipped_when_returncode_set` | **not D-11** — same commit, same reason |
| 6 | `tests/test_hls_downloader.py::…` (`cancel_subprocess` grandchild test) | **not D-11** — same commit, `"POSIX-only: killpg reaches descendants"` |

**Ceiling expressed against the measured 6**, with skips 4–6 named as pre-existing and
unrelated to this plan. The **D-11-guarded count is exactly 3**, which is `B3`'s premise,
and it must be stated as "every remaining D-11 guard is justified per-oracle in the commit
message", not as a total-skip number.

### 2.5 Correction 4 — `B6`'s enumeration, and its traceback population

Plan 11 §3.6 lists **18 records**. Measured: **21 distinct record names across 24
exception-text sites.** All 18 still exist; six further sites appeared. The new ones:

| Record | Module | Sites | Origin |
|---|---|---|---|
| `cookie_file_cleanup_failed` | `services/ytdlp_downloader.py` | `_remove_cookie_artifact_dir` | `36b801e` (`B2`) |
| `ytdlp_reader_line_overrun` | `services/ytdlp_downloader.py` | `_monitor_progress`, `_drain_output` | `db0e33e`, `feea5c8` |
| `subprocess_line_overrun` | `services/ffmpeg_utils.py` | reader drain | `db0e33e` |
| `merge_spawn_failed` | `services/ffmpeg_utils.py` | `_merge_batch_segments`, `_perform_final_merge` | `486bfd9` |

Plan 11's own rule — *a count that differs from 18 is an `Auditor` finding that changes
the closure claim* — makes this a finding, and it is recorded as one here.

**Traceback-carrying records: 8, not 5 or 6.** Five `exc_info=True`
(`browser_launch_failed`, `browser_close_failed`, `playwright_stop_failed`,
`video_player_click_failed`, `ytdlp_not_found`) plus three `logger.exception`
(`download_failed`, `batch_download_failed`, `unexpected_error_in_batch_download`).
Plan 11 says "five" in §3.6 and "six" in §2.4 and §3.6's own table. Internally
inconsistent, and wrong in both places.

**Two of `B6`'s records are already sanitised at the call site**, landed by `486bfd9`:
`services/ffmpeg_utils.py`'s `batch_merge_failed` and `final_merge_failed`, both
`error=sanitize_text_for_log(...)`. That is exactly the per-site-wrapping pattern `B6`
rejects as `Alt B`. **Idempotency is therefore load-bearing in production today**, not
only in `B6`'s planned tests, and `D-7`'s scope choice must account for values that have
already been transformed once. These two records are plan-10 `B14`'s — **do not edit
them, and do not touch any merge code in `services/ffmpeg_utils.py`.**

Excluded as plan 11 directs: `infrastructure/network_monitor.py` × 4 — class name only.

**One instance the enumeration misses.** `cookie_file_cleaned_up` also carries
`path=str(cookie_file)`, at **DEBUG**, on **every successful download**. That is a larger
exposure than the warning `B2` added, because it fires on the success path rather than on
a failure path. It is in scope for `B4` and `B6`, and it widens `D-7`'s candidate key
allowlist to include `path` (§3.6).

### 2.6 Correction 6 — `B3` criterion 7's argfile clause is phantom; the `SEC-003:` comment is already correct

`argfile` has **zero** occurrences anywhere in `src/`, and `git log -S "argfile" --
src/vkdownloader/config.py` returns nothing. The `SEC-003:` comment above
`setup_logging`'s log-file branch **never mentioned an argfile**; it already states that
`touch(mode=…)` ignores the mode on Windows, that `chmod` toggles only the read-only
attribute, that "no access control list is applied", and that confinement is not offered
there (`D-11`). **Strike the clause.** Its substantive half — the comment must not imply a
confinement Windows does not deliver — is **already satisfied**.

Consequence: **`B3`'s remaining scope is test-only.** It writes no production file. Plan
11's `B3`→`B6` file lock on `config.py` disappears; the ordering dependency from `B3` to
`B6` survives only as a *content* dependency (the oracles exercise `setup_logging`'s final
shape), not as a write lock.

`B3` reduces to: **convert three oracles, resolve `D-4`.**

### 2.7 Correction 7 — `B4`'s documentation duty narrows to two items

`09f1b10` already corrected two of plan 11's three documentation sites: the
`sanitize_text_for_log` docstring now reads "preventing signed CDN URLs with embedded
tokens from leaking into logs", and the `SEC-002:` comment no longer claims "or cookie file
paths". **Do not re-litigate a claim that is already gone.** `B4`'s remaining documentation
duty is exactly: (a) state which shapes **are** matched and which are **not**; (b) name
`Cookie:` headers as uncovered, if and only if `D-5` resolves to `Alt A`.

### 2.8 Correction 8 — the four structural facts the Implementor must not re-derive

- `docs/STRUCT.md` forbids the **entry layer** (`cli.py`, `__main__.py`) from importing
  **private** symbols from the service/utils layers, and allows services to import private
  `utils` symbols internally. **`config.py` is not named in any layer.** Plan 11's
  "entry-adjacent" is an inference, not a rule. Measured: `config.py` imports only
  `vkdownloader.models.enums` and has **zero** `logger.` calls.
- `pyproject.toml`: `requires-python = ">=3.12"` (Decision C / plan 16 not applied —
  correct). `pydantic>=2.0.0` **is declared**, so `B7`'s `SecretStr` resolves — the
  `ignore_missing_imports` caveat in `T-B7` step 5 is satisfied by inspection, not by the
  mypy gate. `psutil`, `pywin32`, `portalocker` and `polars` are **all absent**.
- `tests/test_packaging.py`: `EXPECTED_SDIST_ENTRIES` 73, `EXPECTED_WHEEL_ENTRIES` 32,
  `BUILDER_ADDED_SDIST_ENTRIES` 2 — unchanged. **Neither landed commit added a file**, so
  no frozenset edit was required and none was made. Correct, and the gate stays at 14
  passed.
- `utils/__init__.py`'s `__all__` is `["validate_output_path", "sanitize_title",
  "_resolve_output_file", "sanitize_url_for_log", "_strip_auth_params"]`;
  `sanitize_text_for_log` is correctly not re-exported. Note `_strip_auth_params` is
  underscore-named yet sits in `__all__`, so plan 11's "must be a public name"
  requirement for `B6`'s processor is a **plan-level decision, not a consequence of the
  package's own convention.**

---

## §3 Execution blocks, in dependency order

### `R1` — Make the per-run directory actually removable (`SEC-002`)

**Goal.** `_remove_cookie_artifact_dir` calls `Path.rmdir()`, which succeeds only on an
**empty** directory, while `_create_cookie_artifact_dir` always writes `owner.pid` into it.
Verified empirically at `36b801e`: the directory is **never** removed. Close that, and with
it the log-noise regression, the inverted docstring, the missing provenance and the
untested-oracle gap.

**Findings carried.** `SEC-002` (partially discharged by `36b801e`), plus `B2`'s unmet
`T-B2` steps 12 and its violated criterion 8.

**Exact semantic scope.**

1. `services/ytdlp_downloader.py::_remove_cookie_artifact_dir` — make the removal succeed
   on every interceptable end, and emit `cookie_file_cleanup_failed` **only** when a
   directory genuinely survives. Its docstring is currently **inverted**: it presents
   failure as the exceptional case, and failure is the only case. Rewrite it to state the
   real condition.
2. `services/ytdlp_downloader.py::_create_cookie_artifact_dir` and
   `::owner.pid` (`_OWNER_PID_FILENAME`) — only as `R1`'s chosen alternative requires. See
   `R1-D1`; this is the coupling point with `R2`.
3. `services/ytdlp_downloader.py::_download_with_ytdlp` — the `finally` block's
   `try`/`except OSError`/`else` shape, the `_remove_cookie_artifact_dir(cookie_file.parent)`
   call, and the two event names. **Shape and names are preserved.**
4. `services/ytdlp_downloader.py::_is_pid_alive` — **read-only for this block.** Its
   Windows `ctypes` probe is correct and is preserved verbatim in behaviour.
5. `tests/test_hls_downloader.py::TestCreateTempCookieFile` — add a test asserting the
   directory is **removable** (absent after teardown). The existing tests assert the
   artefact's *parent* is the private subdir and that the directory is *tracked*; neither
   can see this defect. Add a test asserting no `cookie_file_cleanup_failed` record is
   emitted on the **success** path.
6. The third artefact string `vk_cookies__dir` (composed from `_COOKIE_ARTIFACT_PREFIX` +
   `_ARTEFACT_DIR_SUFFIX`) is **unfrozen and uncovered**: `.gitignore` does not match it,
   and a directory holding only `owner.pid` can therefore surface in `git status`. Freeze it
   explicitly and either extend `.gitignore` or record why not — see `R1-D4`.
7. **Provenance, in the commit message body.** Plan 11 requires `T-B2` step 12 and this
   block discharges it: `D-1`'s citation (the `_is_pid_alive` rationale currently survives
   only as a code comment asserting "confirmed" with no source), `D-2`'s deferral with the
   forbidden dependency named, `D-3`'s module-level anchor choice, the `T-B2` step-12
   obligation `36b801e` left empty, and the rename-and-inversion of
   `test_file_created_in_system_temp_dir`. History is not rewritten; nothing is amended.

**Alternatives — genuine technical uncertainty. No choice is made here.**

- **`Alt A` — delete the `owner.pid` record, then `rmdir`.** Unlink the PID file first.
  After the cookie file is gone the directory is empty and `rmdir` succeeds. If the cookie
  file's own `unlink` failed (an indexer holding it), `rmdir` fails for a *real* reason and
  the existing warning is then **correct**. Cost, and it is a real one: the directory loses
  its liveness marker while it still exists, which widens the PID-less window `R2` exists
  to close. The two blocks are coupled — `R2` must know which alternative `R1` chose.
- **`Alt B` — `shutil.rmtree`, reusing the existing `_purge_cookie_artifact_dir` helper.**
  House rules 7 and 8 favour reuse: the sweep and the `atexit` handler already purge
  unconditionally through it. Cost: unconditional destruction. If the cookie file's `unlink`
  failed, the tree removal will likely fail too, and with `ignore_errors=True` that failure
  is **silent** — trading a visible signal for invisible residue. Without
  `ignore_errors=True` the `OSError` arm survives and the warning returns.
- **`Alt C` — move the liveness marker out of the directory into its name**, so
  `_create_cookie_artifact_dir` composes the prefix with the current PID. The directory is
  then self-describing, `rmdir` succeeds after the file is unlinked, and a PID-less
  directory becomes structurally impossible — which closes `R2`'s race by the same
  mechanism. Cost: the largest behavioural change of the three; the sweep's parse surface
  moves from "read `owner.pid`" to "parse the name"; the third artefact string's format
  changes, and it is the string `.gitignore` must match.

**Criterion for choosing** (for `R1`'s Researcher and Planner, not for this plan):

1. Must never destroy a directory that still holds credential material a failed `unlink`
   left behind, without a visible record.
2. Must keep the sweep's liveness signal — a directory with a live owner is never reclaimed.
3. Must not add a dependency (`psutil`, `portalocker`, `pywin32` are all absent and stay
   absent; stdlib `ctypes` / `msvcrt` / `shutil` are available).
4. Prefer reuse of `_purge_cookie_artifact_dir` and the smallest diff that satisfies 1–3.
5. Whichever is chosen, the choice must be compatible with `R2`'s sweep rule for a
   **PID-less** directory — `R1` reports its choice and `R2` consumes it.

**Open decisions.**

- `R1-D1` — which alternative. Criterion above. Additionally, `R1`'s **Researcher** must
  settle one platform question before `Alt A` or `Alt B` is chosen: on Windows, whether a
  just-written file inside a fresh `mkdtemp` directory can be unlinked and the directory
  then removed, given that the teardown runs in a `finally` that may precede full child
  reaping and given that an indexer or scanner can hold a transient handle without
  `FILE_SHARE_DELETE`. If that can fail, a retry or a deferral to `atexit` is required and
  the criterion "must never destroy … without a visible record" decides between them.
- `R1-D2` — whether the warning is unconditional or conditional on genuine survival.
  Non-negotiable outcome: the record is emitted **exactly** when a directory survived, and
  **never** on the ordinary success path.
- `R1-D3` — the inverted docstring. Non-negotiable: it states the real condition.
- `R1-D4` — the `vk_cookies__dir` ignore gap. Alternatives: add a `.gitignore` rule for the
  directory pattern; or name the directory so that the files inside it match an existing
  rule; or state in the commit why no rule is needed. Criterion: **an untracked artefact
  must never appear in `git status`.** This matters more than usual here because the
  working tree already carries unrelated untracked entries that must not be swept up
  (§6).
- `R1-D5` — provenance only; see scope item 7. Non-negotiable.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | After a real `_download_with_ytdlp` end — success, failure, and cancel — the per-run directory is **absent**. Runs on Windows, not skipped. | new test in `tests/test_hls_downloader.py::TestCreateTempCookieFile` |
| 2 | No `cookie_file_cleanup_failed` record on the success path. | new test, captured records |
| 3 | `_remove_cookie_artifact_dir`'s docstring states the real failure condition. | review |
| 4 | A test asserts **removability**, distinct from the existing "parent is the private subdir" assertion. | new test |
| 5 | `_is_pid_alive`'s Windows branch is preserved: `PROCESS_QUERY_INFORMATION`, `259` / `STILL_ACTIVE`, `CloseHandle`; `os.kill(pid, 0)` POSIX-only. | review + existing coverage |
| 6 | Frozen strings `vk_cookies_`, `.cookies.txt`, `os.chmod(path, 0o600)` unchanged; `cookie_file_cleanup_failed` / `cookie_file_cleaned_up` names unchanged; the `try`/`except OSError`/`else` shape unchanged; no top-level glob, no age heuristic. | review |
| 7 | `test_file_created_in_private_cookie_subdir` is **retained**; the commit message records the rename and the inversion **with its reason**. The reason is legitimate: the subject moved one directory level down, so the old assertion is not relaxed but re-aimed at a stronger property. The failure was that the commit recorded none. | commit message |
| 8 | The commit message body carries `D-1`'s citation, `D-2`'s deferral and dependency, `D-3`'s anchor, and the `T-B2` step-12 discharge. | commit message |
| 9 | `vk_cookies__dir` is frozen explicitly and its ignore coverage is either extended or recorded. | commit + `.gitignore` if touched |
| 10 | **Gates:** full suite green · `ruff check src tests` clean · `ruff format --check src tests` **green, no exception clause** · `mypy src` clean · `mypy src tests` **≤ 93** · skips ≤ 6 with all six named. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The defect is confirmed but the *teardown ordering* — what runs before `_remove_cookie_artifact_dir` and what may still hold a handle — has not been traced against the live module. That trace decides `R1-D1`. |
| `Researcher` | **yes, narrowly scoped** | One external-behaviour question with real platform stakes: Windows file/directory deletion semantics, handle sharing, and what happens when a directory is removed while a contained file is transiently open. This cannot be settled from the repository. |
| `Planner` | **yes** | Three coherent alternatives with a cross-block coupling; the sequencing of the removal, the record and the sweep must be designed before code is written. |
| `Validator` | **yes** | HIGH risk: a cleanup path that silently stops working is the worst failure mode available here (plan 11's own words about the reaper), and this block rewrites it. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `fix(cookies): remove the per-run artefact directory on every interceptable end`

```yaml
id: EB-R1
title: Make the per-run cookie artefact directory actually removable
priority: high
depends_on: []
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.2, §3.3 (T-B2 steps 1, 4, 5, 12), §6.4, §7.1 (B2 row)"
source_blocks: [B2]
description: >-
  services/ytdlp_downloader.py::_remove_cookie_artifact_dir calls Path.rmdir(), which
  succeeds only on an empty directory, while _create_cookie_artifact_dir always writes
  owner.pid into it. The directory is therefore never removed on any interceptable end,
  a cookie_file_cleanup_failed warning is logged on every download including successful
  ones, and the function's docstring presents failure as the exceptional case when
  failure is the only case. This block makes the removal succeed, restores the
  warning to its correct meaning, rewrites the docstring, discharges T-B2 step 12's
  provenance obligations, and adds the removability oracle that the landed tests
  structurally cannot express.
goals:
  - The per-run directory is absent after every interceptable end of _download_with_ytdlp.
  - cookie_file_cleanup_failed is emitted exactly when a directory survives, never on success.
  - _remove_cookie_artifact_dir's docstring states the real failure condition.
  - T-B2 step 12 is discharged in the commit message body; no history is rewritten.
  - The third artefact string vk_cookies__dir is frozen and its ignore coverage is stated.
files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: modify
    semantic_anchors:
      - _remove_cookie_artifact_dir
      - _create_cookie_artifact_dir
      - _OWNER_PID_FILENAME
      - _COOKIE_ARTIFACT_PREFIX
      - _ARTEFACT_DIR_SUFFIX
      - _COOKIE_ARTIFACT_DIRS
      - _download_with_ytdlp
      - _is_pid_alive
  - path: tests/test_hls_downloader.py
    targets: modify
    semantic_anchors:
      - TestCreateTempCookieFile
      - test_file_created_in_private_cookie_subdir
  - path: .gitignore
    targets: conditional
    semantic_anchors:
      - the vk_cookies_*.cookies.txt rule
changes:
  - what: >-
      Make _remove_cookie_artifact_dir actually remove the directory, and emit
      cookie_file_cleanup_failed only on genuine survival.
    why: >-
      rmdir on a directory containing owner.pid always fails; the warning is therefore a
      per-download regression and the docstring inverts the real behaviour.
    alternatives_considered:
      - "Alt A: unlink owner.pid, then rmdir (widens the PID-less window R2 must cover)."
      - "Alt B: shutil.rmtree via the existing _purge_cookie_artifact_dir (silent if ignore_errors)."
      - "Alt C: carry the PID in the directory name (largest change; also closes R2's race)."
    blocked_by: []
  - what: Add a removability test and a success-path no-warning test.
    why: >-
      The landed tests assert the directory is tracked, not that it is removable, so no
      existing test can see this defect.
    alternatives_considered: []
    blocked_by: []
  - what: Record the rename and inversion of test_file_created_in_system_temp_dir in the commit message.
    why: >-
      Plan 11 declares an inverted oracle a design failure that must be recorded as one.
      The retarget is legitimate; the silence was not.
    alternatives_considered: []
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: The per-run directory is absent after success, failure and cancel; the test runs on Windows.
    verified_by: uv run pytest tests/test_hls_downloader.py -q -rs
  - id: AC-2
    criterion: No cookie_file_cleanup_failed record on the success path.
    verified_by: new test asserting captured records
  - id: AC-3
    criterion: A test asserts removability, distinct from the parent-is-private-subdir assertion.
    verified_by: new test
  - id: AC-4
    criterion: >-
      _is_pid_alive's Windows ctypes probe is preserved in behaviour; os.kill(pid, 0)
      stays POSIX-only.
    verified_by: review
  - id: AC-5
    criterion: >-
      Frozen strings, event names, the teardown shape, and the absence of a top-level glob
      and an age heuristic are all unchanged.
    verified_by: review
  - id: AC-6
    criterion: >-
      The commit message names every oracle converted, the rename and inversion with its
      reason, D-1's citation, D-2's deferral, D-3's anchor, and the T-B2 step-12 discharge.
    verified_by: git log -1
  - id: AC-7
    criterion: vk_cookies__dir is frozen explicitly and its ignore coverage extended or recorded.
    verified_by: commit message
  - id: AC-8
    criterion: >-
      Full suite green; ruff check clean; ruff format --check green; mypy src clean;
      mypy src tests <= 93; skips <= 6 with all six named.
    verified_by: §7 gates
```

---

#### `R1-AUDIT` — block-`R1` audit findings (Auditor; supersedes parts of `R1` above)

Read-only inspection at `36b801e`. Everything below is **verified by execution** on Windows
unless marked otherwise. No production code, no existing audit-phase file, and nothing in the
staging area was touched.

##### `R1-A1` — two defects in `_remove_cookie_artifact_dir`, not one

`_remove_cookie_artifact_dir` calls `Path.rmdir()` inside `try`/`except OSError`. Because
`_create_cookie_artifact_dir` always writes `_OWNER_PID_FILENAME` into the directory it creates,
`rmdir` **never** succeeds on a directory this module created. Measured: after the call the
directory still exists holding `['owner.pid']`, and the record
`cookie_file_cleanup_failed / error="[WinError 145] The directory is not empty: ..."` is emitted.
Control: an empty `mkdtemp` directory **is** removed by the same call, so the empty-directory
precondition is the only blocker.

**Second, independent defect:** `_remove_cookie_artifact_dir` **never discards from
`_COOKIE_ARTIFACT_DIRS`**. Measured: the set grows by one entry per teardown (1 entry after 1
teardown, 4 entries after 4). `_sweep_stale_cookie_dirs`'s `discard` and
`_cleanup_cookie_artifact_dirs`' `clear` are the only removers, so the set accumulates dead
`Path` objects for the process lifetime — unbounded in batch mode. A fix that makes removal
succeed must also discard, or the atexit handler keeps re-purging already-removed paths.

##### `R1-A2` — the landed `finally:` nests the directory teardown inside the file guard

`_download_with_ytdlp`'s `finally:` is `if cookie_file is not None and cookie_file.exists():`,
and `_remove_cookie_artifact_dir(cookie_file.parent)` sits **inside** that guard. If the
credential file is already absent the directory teardown is skipped entirely. Fixing
`_remove_cookie_artifact_dir` alone therefore does **not** close `AC-1`; the guard must also be
lifted so the directory teardown runs whenever `cookie_file is not None`. The credential-file
unlink → directory removal ordering is already correct and must be preserved.

##### `R1-A3` — `_create_cookie_artifact_dir` allocates a distinct directory per call

Measured: `_create_cookie_artifact_dir()` returns `vk_cookies__dir<v1>`, while a subsequent
`_create_temp_cookie_file()` returns a file inside `vk_cookies__dir<v2>` — **not** `<v1>`.
`_create_temp_cookie_file` calls `_create_cookie_artifact_dir` internally. Any test that calls
`_create_cookie_artifact_dir()` and then expects `_create_temp_cookie_file()` to land inside it
will fail. `_build_ytdlp_cli_command` is the sole production caller and is invoked exactly once
per `_download_with_ytdlp`, and `_download_with_ytdlp` has exactly one production caller
(`download_with_ytdlp_with_resume_fallback`) plus a backward-compat re-export in
`services/downloader.py`.

##### `R1-A4` — the spurious record is a live `SEC-007` / `SEC-006` instance, persisted verbatim

`config.setup_logging` wires `structlog.stdlib.LoggerFactory()` + `structlog.stdlib.BoundLogger`
into `logging.basicConfig(..., handlers=[logging.FileHandler(settings.log_file)])` with a
`JSONRenderer`. Measured end to end with `log_file` set: the record below is written to the log
file verbatim, with no redaction processor anywhere in the chain.

- event: `cookie_file_cleanup_failed`
- level: `warning`
- fields: `path` (full temp path to the artefact directory), `error`
  (`[WinError 145] The directory is not empty: '<path>'`)

`path` never matches a `SEC-006` transform trigger (`INVALID_VIDEO_URL` regexes), and `error` is
raw `OSError` text. `R1` removes the record on the success path; `B6` must still own the
general surface, and this record is the concrete live instance to cite in `B6`.

##### `R1-A5` — `.gitignore` does **not** match the credential file either

The module comment on `_COOKIE_ARTIFACT_PREFIX` / `_COOKIE_ARTIFACT_SUFFIX` claims the suffix
`.cookies.txt` "is what `.gitignore` matches", and plan 11 §2.3 item 4 repeats it. Measured with
`git check-ignore -v --no-index`: `.gitignore`'s only cookie rule is `*_cookies.txt`, which
requires the name to end in `_cookies.txt`. The product emits `vk_cookies_<rand>.cookies.txt` —
a **dot** separator. Result: **not ignored**. `vk_cookies__dir<rand>/owner.pid` is also not
ignored.

This falsifies plan 11 §2.3 item 4 and §3.2's "the suffix `.cookies.txt` … is what `.gitignore`
matches" justification for freezing the suffix. The suffix is still worth freezing — `R3` and
`B4`/`B6` key on it — but the stated reason is wrong.

##### `R1-A6` — `AC-7`'s "can surface in `git status`" premise is false; default to its third alternative

Artefacts are created under `tempfile.gettempdir()` (`%TEMP%`), which is **outside** the working
tree, and nothing in `tests/` or `src/` redirects `TEMP`/`TMP` into the repo. A residue directory
therefore cannot appear in `git status` today. `AC-7` is already satisfied by *location*, so
`.gitignore` must stay `targets: conditional` (it already is) and the commit message should take
`R1-D4`'s third alternative — record in the commit message why no rule is needed (artefacts live
in the OS temp root, outside version control) — rather than adding a rule that guards a path the
product never writes to. `.gitignore` is a pre-existing global gap (`*_cookies.txt` matches
nothing the product produces); fixing it is **not** `R1`'s job.

`R1`'s `files` block also omits `TestCookieArtefactLifecycle`, but `R1-A11` shows two of its
tests must be modified (item 7 of `R1-A12`). Add `TestCookieArtefactLifecycle`,
`test_create_cookie_artifact_dir_creates_private_subdir_in_temp` and
`test_create_cookie_artifact_dir_writes_owner_pid` to the `tests/test_hls_downloader.py`
`semantic_anchors`, and add `_create_temp_cookie_file`, `_purge_cookie_artifact_dir`,
`_read_owner_pid` and `_sweep_stale_cookie_dirs` to the
`src/vkdownloader/services/ytdlp_downloader.py` `semantic_anchors`.

##### `R1-A7` — `_purge_cookie_artifact_dir` is unconditionally destructive; reuse is caller-gated only

`_purge_cookie_artifact_dir` is `shutil.rmtree(cookie_dir, ignore_errors=True)`. It consults no
liveness — the gate lives in `_sweep_stale_cookie_dirs`, not in the helper. Measured: handing it
a directory whose `_OWNER_PID_FILENAME` records a **live** PID removed both the directory **and**
the live run's credential file. So a recursive purge is sound in `_remove_cookie_artifact_dir`
**only** because the caller has already attempted the credential-file unlink; the helper itself
offers no protection. `_cleanup_cookie_artifact_dirs` calls it on every tracked directory at
`atexit`, which in a multi-threaded process can race a still-running download.

Additional measured hazard specific to reuse: with a locked file inside the directory,
`shutil.rmtree(..., ignore_errors=True)` **silently** left both the directory and the credential
file on disk and emitted **no record** — while still deleting `_OWNER_PID_FILENAME`. That
manufactures a **PID-less** residue directory, which is exactly the state `R2` exists to defend.

##### `R1-A8` — Windows handle lifecycle and ordering: resolved, no new constraint

`_create_cookie_artifact_dir` writes `_OWNER_PID_FILENAME` via `Path.write_text`, which closes
its descriptor before returning. Measured: the file can be unlinked immediately afterwards, and
the directory is then removed successfully by `rmdir`. So **no lingering handle blocks removal**;
the blocker is the empty-directory precondition alone. For contrast, a credential file held open
without delete sharing makes `os.unlink` raise `PermissionError` / WinError 32.

Ordering is already correct in the landed `finally:`: `cookie_file.unlink(missing_ok=True)`
precedes `_remove_cookie_artifact_dir(cookie_file.parent)`. Preserve it. `AC-1` is about the
directory being gone, not about the ordering being wrong.

##### `R1-A9` — the docstring inversion, and where the `D-1` citation legitimately comes from

`_remove_cookie_artifact_dir`'s docstring presents the `OSError` arm as the exceptional case
("Successful removal emits no record. If the file could not be deleted … `rmdir` will fail …
that failure is also logged"). Inverted: successful removal is the exception, and today failure is
the **only** case. The inversion must be corrected as part of `R1` (`AC-6`).

`36b801e`'s commit **body is empty** (measured via `git log -1 --format=%b 36b801e`), so `D-1`'s
citation was never recorded. Two legitimate sources, neither requiring `os.kill` against a live
process:

1. `docs.python.org/3/library/os.html#os.kill` — "Any other value for `sig` will cause the process
   to be unconditionally killed by the `TerminateProcess` API, and the exit code will be set to
   `sig`."
2. CPython 3.12 `Modules/posixmodule.c`, `win32_kill` — `if (sig == CTRL_C_EVENT || sig ==
   CTRL_BREAK_EVENT) { GenerateConsoleCtrlEvent(sig, pid); }` else
   `{ OpenProcess(PROCESS_ALL_ACCESS, …); TerminateProcess(handle, sig); }`.

##### `R1-A10` — **`D-1`'s recorded rationale is factually wrong; the decision still stands**

Plan 17 §1 and `_is_pid_alive`'s docstring both assert: "CPython maps non-console signal values to
`TerminateProcess` (confirmed: signal 0 is not in the console-control set)". **The parenthetical is
false.** Measured: `signal.CTRL_C_EVENT == 0` and `signal.CTRL_BREAK_EVENT == 1` on this
interpreter, and `win32_kill` branches on exactly those two constants (source above). So
`os.kill(pid, 0)` on Windows takes the **console-control** path, not the `TerminateProcess` path.

The **decision is unchanged and must be preserved** — `os.kill(pid, 0)` stays POSIX-only and the
ctypes `OpenProcess` + `GetExitCodeProcess` + `CloseHandle` probe stays on the `nt` branch — but
for the correct reasons:

- `GenerateConsoleCtrlEvent(CTRL_C_EVENT, pid)` only works for a process attached to a console;
  for a non-console target CPython raises `OSError`/`PermissionError`, so the probe would be
  unreliable in exactly the batch/service case `SEC-002` targets.
- For a **console** target it would deliver a real **Ctrl+C event** to that process's console
  group — a genuine hazard to the operator's own foreground program.

`R1` must therefore (a) record the corrected `D-1` citation from `R1-A9`, and (b) correct
`_is_pid_alive`'s docstring and `_COOKIE_ARTIFACT_PREFIX`/`_SUFFIX` comment claims that assert
"confirmed" without a source. Do **not** alter the probe's behaviour (`AC-4`).

##### `R1-A11` — the oracle gap, confirmed, plus residue-producing tests

Confirmed: **no existing test asserts the directory is gone.** Every test that touches removal
asserts only tracking, or asserts nothing about the directory at all. `TestCookieArtefactLifecycle`
and `TestCreateTempCookieFile` pass green (13 passed, 1 skipped — the skip is `D-11`) while the
directory is never removed.

Three tests call `_remove_cookie_artifact_dir` in a `finally` and then `discard` the directory
from `_COOKIE_ARTIFACT_DIRS` — `test_create_cookie_artifact_dir_creates_private_subdir_in_temp`,
`test_create_cookie_artifact_dir_writes_owner_pid`, and
`test_file_created_in_private_cookie_subdir` (renamed by `36b801e` from
`test_file_created_in_system_temp_dir`, which inverted `assert result.parent == temp_dir` into
`assert result.parent != temp_dir`; the rename and inversion were **not** recorded in the empty
commit body). Measured residue after one run of the two classes: **3** directories, each holding
only `['owner.pid']`, all with a dead owner PID — matching §`R3`'s independent measurement of "3
directories from today's suite run". Once `R1` lands these `finally` blocks become no-ops and the
residue disappears; the tests should stop discarding a directory they now assert is gone.

##### `R1-A12` — tests `R1` must add (the evidence the suite could not produce)

1. `_remove_cookie_artifact_dir` on a directory created by `_create_cookie_artifact_dir`, asserting
   `not cookie_dir.exists()` — a **removed** assertion, not a tracked one. Windows-verified.
2. The same, through the full round trip: `_create_temp_cookie_file` → `unlink` →
   `_remove_cookie_artifact_dir(cookie_file.parent)` → assert the **parent** is gone.
3. `_download_with_ytdlp` teardown on the success path asserting the directory is absent **and**
   that no `cookie_file_cleanup_failed` record was emitted (covers `AC-1` and `AC-2` together).
4. The failure path: with `Path.unlink` patched to raise `PermissionError`, assert the credential
   file survives, the directory survives, exactly one `cookie_file_cleanup_failed` record is
   emitted, and the outcome (`None` or the output path) is unchanged.
5. The cancel path: `asyncio.CancelledError` propagates and the directory is absent.
6. A test that the teardown still runs when the credential file has already vanished — this is
   the `R1-A2` guard, and no current test covers it.
7. `test_create_cookie_artifact_dir_creates_private_subdir_in_temp` and
   `test_create_cookie_artifact_dir_writes_owner_pid`: replace the `finally`-block
   `_remove_cookie_artifact_dir` + `discard` with a post-assertion that the directory is gone, so
   a regression fails the test instead of leaking residue.
8. Assert `_COOKIE_ARTIFACT_DIRS` does **not** grow across repeated create/teardown cycles
   (`R1-A1`).

Do **not** weaken any existing oracle. `AC-5`'s prohibition on a top-level glob and an age
heuristic still holds.

##### `R1-A13` — `docs/STRUCT.md`

`docs/STRUCT.md` constrains `services/` only to "streaming download orchestration, stream
extraction, quality selection, throttling, batch coordination" plus internal private-symbol imports
from `utils/`. Nothing about temp-file or directory lifecycle. Separately, the documented `src/` tree
**omits `services/ytdlp_downloader.py`** entirely — pre-existing drift from the loader removal, not
`R1`'s to fix, but it means `R1` has no `STRUCT.md` duty.

##### `R1-A14` — commit-message debt `R1` must discharge

Add to `AC-6`'s list:

- **C1** — `_remove_cookie_artifact_dir`'s docstring inversion corrected (`R1-A9`).
- **C2** — `D-1`'s citation recorded from CPython `Modules/posixmodule.c` `win32_kill` **and**
  `docs.python.org/3/library/os.html#os.kill`, together with the correction that
  `signal.CTRL_C_EVENT == 0` so the console-control branch — not `TerminateProcess` — is what
  `os.kill(pid, 0)` would hit on Windows (`R1-A10`).
- **C3** — `test_file_created_in_private_cookie_subdir`'s rename and assertion inversion (from
  `test_file_created_in_system_temp_dir`'s `assert result.parent == temp_dir`) recorded with its
  reason, since `36b801e` left the body empty (`R1-A11`).

---

#### `R1-RESEARCH` — the alternative, and three smaller settlements (Researcher)

Read-only at `36b801e`. No production code, no test, and no audit-phase file was
touched. Every measurement below was executed on this machine (Windows, CPython
3.12.1) unless marked otherwise. Supersedes `R1`'s "no choice is made here" for
`Alt A` / `Alt B` / `Alt C`; `R1-D1`, `R1-D2` and `R1-D3` are closed here.

##### `R1-R1` — decision: **`Alt A`**, specified as a contents-first, non-recursive removal

`Alt A` is selected, in this exact form:

1. `_remove_cookie_artifact_dir` unlinks **exactly one named file**,
   `cookie_dir / _OWNER_PID_FILENAME`, via `unlink(missing_ok=True)`. It never
   globs, never recurses, and never touches the credential file.
2. Then it calls `cookie_dir.rmdir()`.
3. **`FileNotFoundError` is the success case**, not a failure: a concurrent sweep
   (or an earlier teardown) already removed it. `FileNotFoundError` is a subclass
   of `OSError`, so **its `except` arm must precede `except OSError`**.
4. If `owner.pid`'s own unlink raises a non-`FileNotFoundError` `OSError`, log one
   `cookie_file_cleanup_failed` and **return without attempting `rmdir`** — `rmdir`
   provably cannot succeed while that file is present, and a second failing call
   would add nothing.
5. At most **one** record per call, carrying `path=str(cookie_dir)` and the
   raising `OSError`'s text.
6. `_COOKIE_ARTIFACT_DIRS.discard(cookie_dir)` **only when the directory is
   gone**, under `_COOKIE_LIFECYCLE_LOCK`, never held across a filesystem call.

Body shape the Planner should write (semantics, not literal code):

```
try:
    (cookie_dir / _OWNER_PID_FILENAME).unlink(missing_ok=True)
    cookie_dir.rmdir()
except FileNotFoundError:            # must precede except OSError
    removed = True
except OSError as exc:
    removed, failure = False, exc
with _COOKIE_LIFECYCLE_LOCK:
    if removed:
        _COOKIE_ARTIFACT_DIRS.discard(cookie_dir)
if not removed:
    logger.warning("cookie_file_cleanup_failed", path=str(cookie_dir), error=str(failure))
```

`missing_ok=True` makes `FileNotFoundError` reachable only from `rmdir`, so the
single `try` is unambiguous.

**Measured, on Windows, replicating the module's own sequence** (fresh `mkdtemp`,
`owner.pid` written, `mkstemp` credential file written + `chmod 0o600`, file
unlinked, then `Alt A`):

| Measurement | Result |
|---|---|
| Per-run directories removed | **50 / 50** |
| Landed shape (`rmdir` with `owner.pid` present) | **0 / 10** — `WinError 145` (`ERROR_DIR_NOT_EMPTY`), every time |
| The `owner.pid`-unlink → `rmdir` window Alt A opens | **median 0.164 ms, max 0.322 ms** (not "sub-microsecond") |
| `_create_cookie_artifact_dir` called twice → same directory? | **No** (`R1-A3` confirmed) |

**Why the "PID-less window" objection to `Alt A` does not decide it.** The window
is real but it is bounded, and nothing of consequence is inside it:

- The credential file is unlinked **before** `_remove_cookie_artifact_dir` runs —
  in the `finally:` (`cookie_file.unlink` then the directory call) and in
  `_create_temp_cookie_file`'s write-error path. So the PID-less window can never
  contain credential material.
- If another process's sweep wins the race it calls `rmtree`; on an empty
  directory that **succeeds**, and our `rmdir` then raises `FileNotFoundError`,
  which rule 3 classifies as success. No record, no residue.
- If this process is hard-killed inside the ~0.16 ms window, what leaks is **one
  empty directory**. An empty directory holds no credential material, and the
  owning process's `atexit` had no chance to run either — so `R2`'s PID-less rule
  will leave it. That is the entire cost, and it is accepted.

**Why not `Alt B` — `shutil.rmtree`.** Measured against a credential file held
open by a plain Python handle (CPython opens Windows files without
`FILE_SHARE_DELETE`, so `unlink` raises `PermissionError` / `WinError 32`):

| Variant | Result |
|---|---|
| `rmtree(..., ignore_errors=True)` | **Silently** deleted `_OWNER_PID_FILENAME`, left the directory **and** the credential file, emitted **nothing** |
| `rmtree(...)` without `ignore_errors` | Raised `PermissionError` (visible) — but the residue was **still** PID-less: `owner.pid` had already been unlinked before the raise |

Both variants **manufacture the PID-less residue `R2` exists to prevent**, because
`shutil.rmtree` deletes entries one at a time and gives no ordering guarantee.
With `ignore_errors=True` it is unconditional: the documented contract is "If
`ignore_errors` is set, errors are ignored", so traversal **continues** past the
locked credential file and `_OWNER_PID_FILENAME` is always removed. Two further
objections stand on their own: it erases the contract distinction between "the
caller proved this is stale, destroy unconditionally" (the sweep, the `atexit`
handler) and "teardown of this run's own directory" (here); and it violates
criterion 1, because a locked credential file is destroyed if `rmtree` reaches it
at all. **`Alt B` cannot be made safe.** Measured: 20 / 20 trials produced the
PID-less residue under `ignore_errors=True`, under both creation orders.

**Why not `Alt C` — the PID in the directory name.** Rejected on four independent
grounds, any one sufficient:

1. **It is prohibited by this block's own non-negotiable list**, which requires
   the `owner.pid` record to be preserved. `Alt C` removes it.
2. Three existing tests import or write `_OWNER_PID_FILENAME`
   (`test_create_cookie_artifact_dir_writes_owner_pid`,
   `test_sweep_stale_cookie_dirs_removes_dead_owner`,
   `test_sweep_stale_cookie_dirs_preserves_live_owner`), and a fourth
   (`test_read_owner_pid_missing_file_returns_none`) depends on `_read_owner_pid`
   itself rather than on the symbol. Measured at `72c8283` by AST scan: exactly three
   test functions reference `_OWNER_PID_FILENAME`. `R1`'s rule "do not weaken any
   existing oracle" (`R1-A12`) forbids rewriting them.
3. It trades the record for a **parse surface**: `_read_owner_pid` would move from
   reading a file to parsing a name, and the parse must survive a PID-reuse and a
   `mkdtemp` random tail. Measured: the tail is **exactly 8 characters** from
   `[a-z0-9_]` (`_RandomNameSequence.characters`), so the PID must be delimited —
   another thing that can be got wrong silently.
4. **The silent-no-op hazard is real and unguarded.** `mkdtemp`'s uniqueness comes
   from `os.mkdir` raising `FileExistsError` and the loop retrying with a fresh
   name (up to `TMP_MAX`); the prefix is prepended verbatim and is *not* part of
   the uniqueness mechanism — so embedding a PID is safe for collision purposes.
   But the **sweep filter** is `entry.name.startswith(_COOKIE_ARTIFACT_PREFIX +
   _ARTEFACT_DIR_SUFFIX)` — a bare `startswith`. Any edit that moves the PID
   outside the leading run, or any change to `_ARTEFACT_DIR_SUFFIX`'s value,
   turns the sweep into a **silent no-op**: no error, no test failure, and residue
   accumulates forever — the exact `SEC-002` failure the sweep exists to prevent.
   `R3`, `B4` and `B6` all key on these strings. `Alt C` buys a zero window and
   pays with a silent-failure mode in the safety net.

**No fourth option is better.** The two obvious candidates were measured and lost:
`rmtree` **without** `ignore_errors` has the same PID-less residue as `Alt B`
(above); "retry `rmdir` after unlinking `owner.pid`" is strictly worse than plain
`Alt A` — it adds one *guaranteed* failing `rmdir` on every teardown (so a record
must be suppressed on the first failure) while shrinking the PID-less window by
exactly nothing, since the window is the same gap in both orderings. A
rename-to-tombstone scheme was considered and dropped: it does not remove the
empty-directory precondition, adds a fifth artefact string for the sweep's
`startswith` to match, and makes a failed rename indistinguishable from a
successful teardown. Restoring `owner.pid` when `rmdir` fails was also considered
and **declined**: the residue is self-healing without it (the next sweep `rmtree`s
it once the lock clears, and the owning process's `atexit` purges it
unconditionally), and restoring would add a write to a path that has already
failed once, for no measurable gain. House rule 5 applies.

##### `R1-R2` — research findings, with sources

**F1. `shutil.rmtree(ignore_errors=True)` on Windows with a locked file.**
`shutil.rmtree.__doc__` (installed 3.12.1): *"If `ignore_errors` is set, errors
are ignored; otherwise, if `onexc` or `onerror` is set, it is called to handle the
error … If `ignore_errors` is false and both `onexc` and `onerror` are None, the
exception is reraised."* Measured: `owner.pid` is deleted, the directory and the
credential file survive, no record is emitted, 20 / 20. Under
`ignore_errors=False` the raise is visible but the residue is still PID-less.
**Confidence: HIGH** (executed + documented).

**F2. Windows directory-removal preconditions.** `RemoveDirectoryW`
(learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-removedirectoryw):
*"Deletes an existing empty directory"* and *"This path must specify an empty
directory, and the calling process must have delete access to the directory."*
The empty-directory precondition is therefore **absolute, not a race** — the
landed `rmdir` can never succeed against a directory this module created. The
same page: *"The RemoveDirectory function marks a directory for deletion on
close. Therefore, the directory is not removed until the last handle to the
directory is closed."* So a handle **to the directory** defers removal rather than
failing it — measured: `rmdir` **succeeded** with an open `os.scandir(d)` handle
held. The blocker is **contents**, not handles-on-the-directory. A handle **to a
file inside** is the real hazard: `PermissionError` / `WinError 32`.
`pathlib.Path.rmdir.__doc__`: *"Remove this directory. The directory must be
empty."* **Confidence: HIGH.**

**F3. `tempfile.mkdtemp` naming and uniqueness.** Measured: 1000 / 1000 unique;
every name is `vk_cookies__dir` + exactly 8 characters from
`0123456789_abcdefghijklmnopqrstuvwxyz`; every directory is a direct child of the
temp root. Source (`inspect.getsource(tempfile.mkdtemp)`): uniqueness comes from
`_os.mkdir(file, 0o700)` raising `FileExistsError` → `continue` → fresh name, up to
`TMP_MAX = 2147483647` attempts. The prefix is prepended verbatim and is **not**
part of the uniqueness mechanism, so a PID inside the prefix cannot cause a
collision failure. (`_RandomNameSequence` is additionally re-seeded per PID.)
`mkdtemp.__doc__`: *"Caller is responsible for deleting the directory when done
with it."* — which is the obligation `R1` exists to discharge.
**Confidence: HIGH.**

**F4. `atexit` and interpreter shutdown.** Measured: inside an `atexit` handler
the filesystem is fully usable (`mkdtemp` + write + `unlink` + `rmdir` all
succeeded), `shutil` is usable, and module globals are still bound. Handlers run
**LIFO** (measured). Also measured, and more useful: a **non-daemon thread is
joined before any `atexit` handler runs** — a worker thread printed *before* the
late-registered handler. **This corrects `R1-A7`'s atexit-race concern** for this
product: `src/` starts no threads of its own (only `loop.run_in_executor(None,
_sync_extract)` in `services/extractor.py`, whose `ThreadPoolExecutor` threads are
non-daemon), so `_cleanup_cookie_artifact_dirs` cannot race a live download at
exit. **Practical implication:** `atexit` is a sound **safety net** but a poor
**primary** mechanism — it only runs on an orderly exit, it runs once, and it
carries no per-run observability. Per-run teardown in the `finally:` must remain
the primary path; `atexit` stays the net. **Confidence: HIGH** for the measured
behaviour on this interpreter; I did **not** read `Python/pylifecycle.c` to
confirm the mechanism (`Py_FinalizeEx` calling `wait_for_thread_shutdown()` before
`call_py_exitfuncs()`), so treat that explanation as MEDIUM.

**F5. House conventions for directory removal.** Only two patterns exist in
`src/`: `services/segment_downloader.py::_cleanup_segments` (unlink-loop over
`glob("*")`, then `rmdir`, `except OSError: pass`) and
`_purge_cookie_artifact_dir` (`rmtree(ignore_errors=True)`). **Judgement: keep
logging on failure**, and the grounds are specific rather than generic. (i)
`_cleanup_segments` swallows because a segment directory is **bulk, non-sensitive,
and fully reproducible** — losing one costs nothing. A cookie artefact directory
is the product's only on-disk credential, and losing it silently is
`SEC-002` recurring. (ii) `_purge_cookie_artifact_dir` swallows because its callers
have **already proved** the target is residue, so failure is uninteresting. This
function is neither: the caller has attempted, and possibly failed, the destroy.
(iii) The record is **novel for this codebase** — but so is the failure mode: no
other cleanup in `src/` can leave credential material on disk. Logging it is the
only thing that makes a locked-file residue *observable* instead of invisible.
It must be a **warning on genuine survival only** (`R1-D2`), never on success.

##### `R1-R3` — the `_COOKIE_ARTIFACT_DIRS` discard

Prune **inside `_remove_cookie_artifact_dir`**, and only on a definitive "gone"
outcome — `rmdir` returned, or `FileNotFoundError`. The helper is the only place
that knows the outcome, so it is the single choke point; putting the `discard` in
either caller would need a status return and would leave
`_create_temp_cookie_file`'s write-error path wrong for free.

**Do not discard on failure.** The set's meaning is "directories this process
created that may still exist". A surviving directory must stay tracked so the
`atexit` handler reclaims it; discarding it would convert a reclaimable residue
into a permanent one. Growth is therefore bounded by *actual failures*, not by
runs — which retires the unbounded-growth defect (`R1-A1`) on the success path
without weakening the safety net.

Interaction with `_cleanup_cookie_artifact_dirs`: **no change to it.** It already
snapshots under the lock, purges **outside** the lock, then `clear()`s. With the
discard in place a removed directory is simply not in the snapshot, so it is never
re-purged at exit — which is exactly the required post-condition. Keep the lock
**out** of the purge loop: `_COOKIE_LIFECYCLE_LOCK` is a plain `threading.Lock`
and `_purge_cookie_artifact_dir` can block on a locked file, so holding it there
would stall `_create_cookie_artifact_dir` for every other thread.
`_sweep_stale_cookie_dirs` already follows this discipline — copy it.

##### `R1-R4` — the lifted `finally:` guard

**Post-condition.** The directory teardown runs **whenever
`cookie_file is not None`**, independently of whether the file existed and of
whether its unlink succeeded.

Required shape — note the inner `exists()` guard is **kept**:

```
finally:
    if cookie_file is not None:
        if cookie_file.exists():
            try:
                cookie_file.unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("cookie_file_cleanup_failed", path=str(cookie_file), error=str(exc))
            else:
                logger.debug("cookie_file_cleaned_up", path=str(cookie_file))
        _remove_cookie_artifact_dir(cookie_file.parent)
```

Why the inner guard survives rather than being folded into the outer one: folding
it would make `unlink(missing_ok=True)` "succeed" on an absent file and fire the
`else`, emitting `cookie_file_cleaned_up` for a file that was never there. Plan 17
§2.5 already names `cookie_file_cleaned_up`'s `path=` field — at DEBUG, on every
successful download — as an over-broad `SEC-006`/`SEC-007` exposure that `B4` and
`B6` must widen the transform for. Manufacturing *more* of those records would
worsen the very exposure `B6` has to absorb. Keeping the guard preserves the
existing record semantics **exactly** and costs one nesting level.

The `try` / `except OSError` / `else` shape and both event names are preserved
verbatim; the credential-file-unlink-before-directory-`rmdir` ordering is
load-bearing (`Alt A` depends on it) and is now stated as such in a comment.

**Event name for the directory's failure: reuse `cookie_file_cleanup_failed`. No
new name.** Grounds: (i) plan 17 §2.5's corrected enumeration — 21 names / 24
sites — lists `_remove_cookie_artifact_dir` under that name; a new name voids it
and hands `B6` a re-derivation. (ii) The two arms are already distinguished by
the shape of `path` (file path vs directory path), which is the established
convention here. (iii) One name means one grep returns the whole story of a failed
teardown. (iv) There is no **success** record for the directory: silence on
success is `R1-D2`'s non-negotiable, and the removability test is the oracle.

**Two records are correct on the locked-file path.** In production a locked
credential file yields one record from the file arm (`path=` the file) and one
from the directory arm (`path=` the directory) — two distinct facts, two distinct
paths. Do not suppress the second. But `R1-A12` item 4's "exactly one record"
assertion only holds because that test patches `Path.unlink` wholesale, so the
`owner.pid` unlink raises too and rule 4 short-circuits. **The Validator must not
generalise that assertion to a real lock.** The Validator should additionally
assert that all four existing `cookie_file_cleanup_failed` / `cookie_file_cleaned_up`
tests still pass **unchanged**; by inspection they do — three use
`assert_any_call` on the file path (unaffected by a directory-path record), one
counts `cookie_file_cleaned_up` debug calls (still exactly 1), and
`test_cookie_cleanup_failure_child_reaped_before_unlink` asserts only call
*ordering*, which `Alt A` preserves.

##### `R1-R5` — the corrected `D-1` rationale

The landed parenthetical — *"because CPython maps non-console signal values to
`TerminateProcess` (confirmed: signal 0 is not in the console-control set)"* — is
**false**, and it is false in the direction that matters: `signal.CTRL_C_EVENT ==
0` (measured, this interpreter), so `os.kill(pid, 0)` on Windows does **not** take
the `TerminateProcess` branch at all. The decision is unchanged and stands for
better reasons. **The parenthetical must be corrected in place — deleted, not
merely supplemented.** A code comment that asserts a checked fact and is wrong is
worse than no comment, and `R1-A10(b)` already requires the correction.

Verified sources:

- `docs.python.org/3/library/os.html#os.kill`: *"The `signal.CTRL_C_EVENT` and
  `signal.CTRL_BREAK_EVENT` signals are special signals which can only be sent to
  console processes which share a common console window, e.g., some subprocesses.
  Any other value for `sig` will cause the process to be unconditionally killed by
  the `TerminateProcess` API, and the exit code will be set to `sig`."*
- CPython **3.12.1** `Modules/posixmodule.c`, `os_kill_impl`:

  ```c
  if (sig == CTRL_C_EVENT || sig == CTRL_BREAK_EVENT) {
      if (GenerateConsoleCtrlEvent(sig, (DWORD)pid) == 0) { ... }
      else { Py_RETURN_NONE; }
  }
  ...
  /* If the signal is outside of what GenerateConsoleCtrlEvent can use,
     attempt to open and terminate the process. */
  handle = OpenProcess(PROCESS_ALL_ACCESS, FALSE, (DWORD)pid);
  ...
  if (TerminateProcess(handle, sig) == 0) { ... }
  ```

Exact text for `_is_pid_alive`'s docstring (replaces the current wording;
behaviour untouched, per `AC-4`):

> On POSIX, uses `os.kill(pid, 0)` — signal 0 tests process existence without
> delivering a signal. `os.kill` is **prohibited** on the Windows branch, but not
> because it would terminate the target: on Windows `os.kill(pid, sig)` dispatches
> the two console-control values first — `signal.CTRL_C_EVENT` (0) and
> `signal.CTRL_BREAK_EVENT` (1) go to `GenerateConsoleCtrlEvent`, and only any
> other value reaches `TerminateProcess`. Because `CTRL_C_EVENT == 0`,
> `os.kill(pid, 0)` takes the **console-control** branch, which makes it wrong as
> a probe twice over: against a target that is not attached to a console the call
> fails with `OSError` and says nothing about liveness — exactly the batch and
> service case `SEC-002` targets — and against a console-attached target it
> delivers a real CTRL_C event to that process's console group, which reaches the
> operator's own foreground program. A `ctypes` probe via `OpenProcess` +
> `GetExitCodeProcess` is used instead (D-1); `STILL_ACTIVE` (259) means the
> process has not exited yet.

Commit-message wording for `D-1` (for `AC-6` / `R1-A14` **C2**):

> `D-1` resolved: `os.kill(pid, 0)` stays POSIX-only and the Windows branch keeps
> the `ctypes` `OpenProcess`/`GetExitCodeProcess`/`CloseHandle` probe. The
> previously recorded rationale was wrong and is corrected here. It claimed
> "signal 0 is not in the console-control set"; measured on this interpreter,
> `signal.CTRL_C_EVENT == 0` and `signal.CTRL_BREAK_EVENT == 1`, and CPython
> 3.12.1 `Modules/posixmodule.c::os_kill_impl` branches on exactly those two
> constants (`GenerateConsoleCtrlEvent`) before reaching `OpenProcess` +
> `TerminateProcess`, per `os.kill`'s documentation. So `os.kill(pid, 0)` on
> Windows is unreliable as a probe for a non-console target and would deliver a
> real CTRL_C to the operator's console group for a console target. The probe is
> unchanged in behaviour; only the documented reason is corrected.

**Also correct in place, same commit:** the module comment on
`_COOKIE_ARTIFACT_PREFIX` / `_COOKIE_ARTIFACT_SUFFIX` claims the suffix
`.cookies.txt` "is what `.gitignore` matches". `R1-A5` falsified that —
`.gitignore`'s only cookie rule is `*_cookies.txt`, which needs an **underscore**
before `cookies.txt`, and the product emits a **dot** separator. The suffix stays
frozen (`R3`, `B4`, `B6` key on it); only the stated reason is wrong and must be
fixed. Leaving a known-false claim one line above a corrected one is worse than
either. This discharges `R1-A5` inside `R1` rather than deferring it.

##### `R1-R6` — what `R1` still does not own

- `.gitignore`: unchanged. `R1-A6` established artefacts live in the OS temp root,
  outside version control, so `AC-7` is satisfied by location; `R1` takes
  `R1-D4`'s third alternative and records that in the commit message.
- `_purge_cookie_artifact_dir`, `_read_owner_pid`, `_sweep_stale_cookie_dirs`,
  `_is_pid_alive`'s probe, `_ensure_cookie_lifecycle_started`/`atexit`
  registration, the frozen strings, `os.chmod(path, 0o600)` and the `DF-007:`
  comment are all **untouched** by this selection. `Alt A` changes the *removal*
  function and the *tracking set's* lifecycle; it does not touch the sweep.
- `R2` is **not** pre-empted. `Alt A` does not narrow the **creation** window at
  all — `_create_cookie_artifact_dir` still calls `mkdtemp` and only then writes
  `owner.pid`. `R2` needs its own decision on its own four alternatives.

---

#### `R1-DESIGN` — implementor task (Planner)

Supersedes the `R1` block's "no choice is made here" and its "Alternatives" list. `Alt A`
is settled by `R1-R1`; the scope additions are `R1-A1`…`R1-A14`; the three settlements are
`R1-R3`, `R1-R4`, `R1-R5`. Symbols are named, never line-numbered.

```yaml
id: EB-R1
title: Make the per-run cookie artefact directory actually removable
priority: high
depends_on: []

source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.2 (B2), §3.3 (T-B2 steps 1, 4, 5, 12), §6.4, §7.1 (B2 row)"
source_blocks: [B2]
source_findings: [SEC-002, VAL-602]
supersedes: "R1-D1, R1-D2, R1-D3 closed by R1-RESEARCH; AC-7 premise voided by R1-A6"

description: >
  _remove_cookie_artifact_dir calls Path.rmdir(), which succeeds only on an empty
  directory, while _create_cookie_artifact_dir always writes owner.pid into the
  directory it creates. Measured at 36b801e: 0 of 10 removals succeed (WinError 145),
  a cookie_file_cleanup_failed warning is emitted on every download including
  successful ones and reaches the persisted log file, and the function's docstring
  presents failure as the exceptional case when failure is the only case. Three
  further defects must be closed in the same change: the tracking set
  _COOKIE_ARTIFACT_DIRS is never pruned (R1-A1); the directory teardown in
  _download_with_ytdlp's finally: is nested inside the file-existence guard so it is
  skipped when the credential file has already vanished (R1-A2); and no test anywhere
  asserts the directory is gone, only that it is tracked (R1-A12). This task applies
  Alt A, lifts the finally: guard, corrects two false comments, adds the eight
  oracles the suite structurally cannot express, and discharges the commit-message
  provenance debt 36b801e left empty.

goals:
  - The per-run artefact directory is absent after every interceptable end of _download_with_ytdlp.
  - cookie_file_cleanup_failed is emitted only on genuine survival, never on the success path.
  - _COOKIE_ARTIFACT_DIRS is pruned on success and retained on failure, so growth is bounded by real failures.
  - The directory teardown runs whenever cookie_file is not None, independent of file existence.
  - The two false in-code claims (the D-1 parenthetical, the .gitignore claim) are corrected in place.
  - T-B2 step 12 provenance is discharged in a NEW commit body. History is not rewritten.

files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: modify
    targets_detail:
      modify:
        - _remove_cookie_artifact_dir          # body + docstring rewritten
        - _download_with_ytdlp                 # the finally: guard only
        - _is_pid_alive                        # docstring text only, behaviour untouched
      comment_only:
        - the module comment above _COOKIE_ARTIFACT_PREFIX / _COOKIE_ARTIFACT_SUFFIX
    semantic_anchors:
      insert_before:
        - type: function
          value: _sweep_stale_cookie_dirs
      modify_in_place:
        - type: function
          value: _remove_cookie_artifact_dir
        - type: function
          value: _download_with_ytdlp
        - type: function
          value: _is_pid_alive
        - type: module_constant
          value: _COOKIE_ARTIFACT_PREFIX
        - type: module_constant
          value: _COOKIE_ARTIFACT_SUFFIX
    read_only_symbols_referenced_not_changed:
      - _OWNER_PID_FILENAME
      - _COOKIE_ARTIFACT_DIRS
      - _COOKIE_LIFECYCLE_LOCK

  - path: tests/test_hls_downloader.py
    targets: modify
    targets_detail:
      modify:
        - TestCreateTempCookieFile
        - TestCookieArtefactLifecycle
      rewrite_finally_blocks_only:
        - test_create_cookie_artifact_dir_creates_private_subdir_in_temp
        - test_create_cookie_artifact_dir_writes_owner_pid
        - test_file_created_in_private_cookie_subdir
      add_new_tests_to:
        - TestCookieArtefactLifecycle
        - TestCreateTempCookieFile
    semantic_anchors:
      insert_after:
        - type: class
          value: TestCreateTempCookieFile
        - type: class
          value: TestCookieArtefactLifecycle
      modify_in_place:
        - type: method
          value: test_create_cookie_artifact_dir_creates_private_subdir_in_temp
        - type: method
          value: test_create_cookie_artifact_dir_writes_owner_pid
        - type: method
          value: test_file_created_in_private_cookie_subdir

out_of_scope:
  # Named explicitly so the Implementor does not "improve" them. Each is load-bearing.
  - symbol: _create_cookie_artifact_dir
    reason: >
      Alt A does not touch creation. mkdtemp still runs before owner.pid is written, so
      R2's creation window is untouched and R2 needs its own decision. R1-A3 measured that
      this function allocates a DISTINCT directory per call, so no test may assume a
      directory from one call contains a file from another.
  - symbol: _purge_cookie_artifact_dir
    reason: >
      R1-A7 measured that shutil.rmtree(ignore_errors=True) destroys a live run's
      credential file when handed a directory with a live owner.pid; it consults no
      liveness itself. Reusing it was Alt B and was rejected. Untouched.
  - symbol: _sweep_stale_cookie_dirs
    reason: Liveness-gated sweep. Preserve verbatim, including the bare startswith filter.
  - symbol: _cleanup_cookie_artifact_dirs
    reason: >
      R1-R3: no change. It already snapshots under the lock, purges outside it, then
      clear()s. With the discard in place a removed directory is simply not in the snapshot.
  - symbol: _read_owner_pid
    reason: Untouched. Four existing tests depend on it.
  - symbol: _ensure_cookie_lifecycle_started
    reason: atexit stays registered exactly once. Untouched.
  - symbol: _is_pid_alive (implementation)
    reason: >
      The ctypes probe is correct and must not be simplified away: PROCESS_QUERY_INFORMATION
      (0x0400, not SYNCHRONIZE), GetExitCodeProcess, CloseHandle, 259 / STILL_ACTIVE as
      alive, os.kill(pid, 0) POSIX-only. Docstring text only.
  - path: src/vkdownloader/config.py
    reason: setup_logging and the log file's own artefact are B4/B6 subjects.
  - path: src/vkdownloader/services/ffmpeg_utils.py
    reason: >
      Merge engine is permanent product code. batch_merge_failed / final_merge_failed are
      plan-10 B14's records and B6's idempotency fixture.
  - path: .gitignore
    reason: >
      R1-A6 / R1-R6: artefacts live under tempfile.gettempdir(), outside the working tree,
      so a residue directory cannot appear in git status. AC-7 is satisfied by location.
      The pre-existing global gap (*_cookies.txt matches nothing the product produces) is
      NOT R1's job. R1-D4's third alternative is taken and recorded in the commit message.
  - path: docs/STRUCT.md
    reason: R1-A13: no duty. It constrains services/ by responsibility only.

changes:

  - action: modify_function
    target: _remove_cookie_artifact_dir
    description: >
      Rewrite the body to Alt A and correct the inverted docstring. Unlink EXACTLY one
      named file, cookie_dir / _OWNER_PID_FILENAME, via unlink(missing_ok=True); never a
      glob, never recursion, never the credential file. Then cookie_dir.rmdir().
      FileNotFoundError is the SUCCESS case (a concurrent sweep or an earlier teardown
      already removed it) and because it subclasses OSError its except arm MUST precede
      except OSError. Because both calls share one try, an OSError raised by the owner.pid
      unlink propagates out before rmdir is reached, which is exactly rule 4: log one
      record and return without attempting rmdir, since rmdir provably cannot succeed while
      owner.pid is present. At most one record per call, path=str(cookie_dir), error=str(exc).
      No record on success. Prune _COOKIE_ARTIFACT_DIRS under _COOKIE_LIFECYCLE_LOCK only on
      a definitive gone-outcome (rmdir returned, or FileNotFoundError). Never discard on
      failure: the set means "directories this process created that may still exist", and
      discarding a survivor converts reclaimable residue into permanent residue. The lock is
      never held across a filesystem call. Keep this to exactly ONE logger.warning call site
      so plan 17 §2.5's 21-names / 24-sites enumeration stays exact for B6.
      Docstring must state the REAL condition: removal succeeds once owner.pid is gone; the
      only genuine failure is a surviving directory (a credential file held without delete
      sharing), which is recorded and left for the atexit handler to reclaim.
    code_hint: |
      def _remove_cookie_artifact_dir(cookie_dir: Path) -> None:
          """Remove this run's cookie artefact directory and its owner record.

          The directory holds exactly two things: the credential file, which the
          caller has already unlinked, and ``owner.pid``, written by
          ``_create_cookie_artifact_dir``. ``Path.rmdir`` succeeds only on an EMPTY
          directory, so ``owner.pid`` is unlinked first and the directory is then
          removed. No glob, no recursion: the credential file is never touched here.

          ``FileNotFoundError`` is success, not failure - a concurrent sweep (or an
          earlier teardown) already removed the directory - so its arm precedes the
          ``OSError`` arm, which it subclasses. An ``OSError`` from the ``owner.pid``
          unlink means ``rmdir`` provably cannot succeed while that file exists, so it
          is not attempted; one ``cookie_file_cleanup_failed`` record is emitted and
          the directory is left tracked for the ``atexit`` handler.

          A record is emitted only on genuine survival. Successful removal is silent.
          """
          removed = False
          failure: OSError | None = None
          try:
              (cookie_dir / _OWNER_PID_FILENAME).unlink(missing_ok=True)
              cookie_dir.rmdir()
          except FileNotFoundError:  # must precede except OSError: it subclasses it
              removed = True
          except OSError as exc:
              failure = exc
          with _COOKIE_LIFECYCLE_LOCK:
              if removed:
                  _COOKIE_ARTIFACT_DIRS.discard(cookie_dir)
          if failure is not None:
              logger.warning(
                  "cookie_file_cleanup_failed",
                  path=str(cookie_dir),
                  error=str(failure),
              )
    notes:
      - >
        Annotate failure explicitly. mypy is strict = true in pyproject.toml; a bare
        `failure = None` later assigned an OSError is an error ("Need type annotation").
      - >
        Guard the record with `if failure is not None`, NOT with `if not removed` plus
        str(failure). The latter type-checks but can emit error="None".
      - >
        Do NOT move the discard into either caller. This function is the single choke
        point that knows the outcome; a caller-side discard would need a status return and
        would leave _create_temp_cookie_file's write-error path wrong for free.

  - action: modify_function
    target: _download_with_ytdlp (the finally: block only)
    description: >
      Lift the guard so the directory teardown runs whenever cookie_file is not None,
      independently of whether the file existed and of whether its unlink succeeded.
      R1-A2 is why this is mandatory: fixing the helper alone does NOT close the finding.
      The INNER exists() guard STAYS. Folding it in would make unlink(missing_ok=True)
      "succeed" on an absent file and fire the else, emitting cookie_file_cleaned_up for a
      file that never existed - and that record already carries path= at DEBUG on every
      successful download, an over-broad SEC-006/SEC-007 exposure B4 and B6 must absorb.
      Manufacturing more of them worsens it. Preserve the try / except OSError / else shape
      and both event names verbatim. The credential-file-unlink-before-directory-rmdir
      ordering is load-bearing: Alt A depends on it, because the PID-less window it opens
      can therefore never contain credential material. State that in a comment.
    code_hint: |
      finally:
          if cookie_file is not None:
              # The inner exists() guard is kept: folding it in would make
              # unlink(missing_ok=True) "succeed" on an absent file and emit
              # cookie_file_cleaned_up for a file that never existed.
              if cookie_file.exists():
                  try:
                      cookie_file.unlink(missing_ok=True)
                  except OSError as exc:
                      # A failed destroy must never replace the download's own outcome.
                      logger.warning(
                          "cookie_file_cleanup_failed",
                          path=str(cookie_file),
                          error=str(exc),
                      )
                  else:
                      logger.debug("cookie_file_cleaned_up", path=str(cookie_file))
              # LOAD-BEARING ORDER: the credential file is unlinked above, so the
              # directory is empty apart from owner.pid and the removal below can
              # succeed. Run this whenever a cookie file was created, even if it has
              # already vanished or its unlink failed - otherwise the directory leaks.
              _remove_cookie_artifact_dir(cookie_file.parent)
    notes:
      - >
        Event name for the directory's failure stays cookie_file_cleanup_failed. No new
        name (R1-R4): §2.5's enumeration lists this site under that name, and the two arms
        are already distinguished by the shape of path (file path vs directory path).
      - >
        On a REAL locked credential file two records are correct - one per failed step,
        distinguishable by path. Do not suppress the second. R1-A12 item 4's
        "exactly one record" holds only because that test patches Path.unlink wholesale,
        so the owner.pid unlink raises too and rule 4 short-circuits.

  - action: modify_docstring
    target: _is_pid_alive
    description: >
      Correct the false parenthetical IN PLACE - deleted, not supplemented. It claims
      "CPython maps non-console signal values to TerminateProcess (confirmed: signal 0 is
      not in the console-control set)". That is false: signal.CTRL_C_EVENT == 0 and
      signal.CTRL_BREAK_EVENT == 1 (measured), and CPython 3.12.1
      Modules/posixmodule.c::os_kill_impl branches on exactly those two constants
      (GenerateConsoleCtrlEvent) before reaching OpenProcess + TerminateProcess. So
      os.kill(pid, 0) on Windows takes the CONSOLE-CONTROL path, not TerminateProcess. The
      decision is unchanged and stands for better reasons: the probe is unreliable for a
      non-console target (OSError says nothing about liveness - exactly the batch and
      service case SEC-002 targets), and for a console target it would deliver a real
      CTRL_C to the operator's own console group. Behaviour untouched. Use R1-R5's exact
      replacement wording.
    code_hint: |
      On POSIX, uses ``os.kill(pid, 0)`` - signal 0 tests process existence without
      delivering a signal. ``os.kill`` is **prohibited** on the Windows branch, but not
      because it would terminate the target: on Windows ``os.kill(pid, sig)`` dispatches
      the two console-control values first - ``signal.CTRL_C_EVENT`` (0) and
      ``signal.CTRL_BREAK_EVENT`` (1) go to ``GenerateConsoleCtrlEvent``, and only any
      other value reaches ``TerminateProcess``. Because ``CTRL_C_EVENT == 0``,
      ``os.kill(pid, 0)`` takes the **console-control** branch, which makes it wrong as a
      probe twice over: against a target that is not attached to a console the call fails
      with ``OSError`` and says nothing about liveness - exactly the batch and service
      case ``SEC-002`` targets - and against a console-attached target it delivers a real
      CTRL_C event to that process's console group, which reaches the operator's own
      foreground program. A ``ctypes`` probe via ``OpenProcess`` + ``GetExitCodeProcess``
      is used instead (D-1); ``STILL_ACTIVE`` (259) means the process has not exited yet.

  - action: modify_comment
    target: the module comment above _COOKIE_ARTIFACT_PREFIX and _COOKIE_ARTIFACT_SUFFIX
    description: >
      Correct the false claim that the suffix ".cookies.txt" is "what .gitignore matches".
      R1-A5 measured with git check-ignore -v --no-index: .gitignore's only cookie rule is
      *_cookies.txt, which requires an UNDERSCORE before cookies.txt, while the product
      emits vk_cookies_<rand>.cookies.txt - a DOT separator. Not ignored. The strings stay
      frozen (R3, B4 and B6 key on them); only the stated reason is wrong. Leaving a
      known-false claim one line above a corrected one is worse than either.
    code_hint: |
      # Cookie artefact lifecycle constants (SEC-001, SEC-002, VAL-602).
      # These strings are frozen by B2: the prefix ``vk_cookies_`` is what the
      # sweep is keyed on, and the suffix ``.cookies.txt`` is what the operator-facing
      # redaction and cleanup tooling keys on. Renaming either breaks coverage silently.
      # Note: neither string is matched by ``.gitignore`` - its only cookie rule is
      # ``*_cookies.txt``, which needs an underscore where the product emits a dot.
      # The artefacts live under the OS temp root, outside the working tree, so no
      # ignore rule is required for them to stay out of ``git status``.

implementation_sequence:
  # Each step leaves the tree valid. No commit is made until step 8.
  - step: 1
    action: >
      Correct the two false comments FIRST, in isolation: the _COOKIE_ARTIFACT_PREFIX /
      _SUFFIX module comment and _is_pid_alive's docstring. Comment-only, zero behavioural
      risk, and it is the cheapest possible review. Run mypy src and ruff check/format on
      src to confirm nothing moved.
  - step: 2
    action: >
      Rewrite _remove_cookie_artifact_dir (body + docstring) per change 1. Do NOT yet touch
      _download_with_ytdlp. At this point the helper is correct but the finally: guard still
      skips it when the file is absent; every existing test still passes because nothing
      asserted removal. Confirm with uv run pytest tests/test_hls_downloader.py -q -rs.
  - step: 3
    action: >
      Lift the finally: guard in _download_with_ytdlp per change 2. Confirm the four existing
      cookie_file_cleaned_up / cookie_file_cleanup_failed tests in TestYtDlpSubprocessShutdown
      are green UNCHANGED. They are: three use assert_any_call on the file path (a
      directory-path record does not collide), one counts cookie_file_cleaned_up debug calls
      (still exactly 1), and test_cookie_cleanup_failure_child_reaped_before_unlink asserts
      only call ordering, which Alt A preserves.
  - step: 4
    action: >
      Rewrite the three existing finally blocks per required_tests items 9-11. This is the
      point at which the suite starts to have teeth: from here a removal regression FAILS a
      test instead of silently leaking residue. Confirm the three tests are green.
  - step: 5
    action: >
      Add required_tests items 1, 2 and 8 (helper-level removability, full round trip, and
      the no-growth assertion). Run uv run pytest tests/test_hls_downloader.py -q -rs.
  - step: 6
    action: >
      Add required_tests items 3 to 6 (the four _download_with_ytdlp end-path oracles:
      success, failure, cancel, already-vanished file). These need the existing
      create_subprocess_exec patch idiom from TestYtDlpSubprocessShutdown. Run the file.
  - step: 7
    action: >
      Add required_tests item 7 (the locked-file failure oracle). Run the file, then the full
      suite, and record the skip count.
  - step: 8
    action: >
      Run every gate. Then stage exactly two explicit paths and commit ONCE with the
      message specified in commit_message_must_record. One commit for the block.

constraints:
  preservation_list:
    - The per-run private directory created by _create_cookie_artifact_dir.
    - The owner.pid liveness record (_OWNER_PID_FILENAME = "owner.pid").
    - The liveness-gated sweep: never a top-level glob, never an age heuristic (VAL-602).
    - atexit registered exactly once, guarded by _cookie_lifecycle_started.
    - Frozen strings _COOKIE_ARTIFACT_PREFIX = "vk_cookies_" and _COOKIE_ARTIFACT_SUFFIX = ".cookies.txt".
    - The os.chmod(path, 0o600) call and the corrected DF-007: comment above it.
    - The finally: teardown's try / except OSError / else shape and BOTH event names, verbatim.
    - D-2's deferral: no pywin32, no ctypes ACL reader. Half (ii) of SEC-001 stays deferred.
    - D-3's module-level anchor (_ensure_cookie_lifecycle_started), not the cli.py preamble.
    - _is_pid_alive's ctypes implementation, not simplified away.
    - QLT-004: close the fd in finally BEFORE unlinking.
  ordering_rules:
    - rule: >
        The credential-file unlink precedes the directory rmdir, in the finally: AND in
        _create_temp_cookie_file's write-error path. Load-bearing, not incidental: it is
        what guarantees Alt A's PID-less window can never hold credential material.
      enforced_by: A comment at both sites, and required_tests items 1, 2 and 3.
    - rule: >
        `except FileNotFoundError` must textually precede `except OSError` in
        _remove_cookie_artifact_dir. FileNotFoundError subclasses OSError; reversed order
        silently classifies a successful concurrent removal as a failure and emits a
        spurious warning on a correct teardown.
      enforced_by: >
        Required test - a second _remove_cookie_artifact_dir call on an already-removed
        directory must emit no record. The Validator checks this ordering explicitly.
    - rule: One logger.warning call site for cookie_file_cleanup_failed in this module.
  hard_prohibitions:
    - No new dependency. psutil, pywin32, portalocker and polars stay absent.
    - >
      No new file. A new services/ or utils/ module would require a tests/test_packaging.py
      frozenset edit, which plan 11 §2.5 forbids. The lifecycle stays in the module that
      already owns the artefact.
    - structlog only (module-level `logger = get_logger(__name__)`). No stdlib logging import.
    - No print(). Use logger.
    - No new `Any`. The module already imports Any for asyncio.Task typing; do not add to it.
    - English only in all comments, docstrings, error text and the commit message.
    - No line-length escape: ruff line-length is 100.
    - Do not modify any file under .ai/audit/99-validation/. Do not modify plan 11 or plan 17.
    - >
      Every existing test asserting cookie_file_cleaned_up or cookie_file_cleanup_failed stays
      green UNCHANGED. No existing oracle may be weakened, relaxed or deleted.
    - No amend, no force-push, no git reset, no git checkout, no history rewrite.

required_tests:
  # R1-A12 items 1-8, plus the three finally-block rewrites. Each oracle asserts the
  # directory is GONE. assert_any_call on cookie_file_cleanup_failed cannot distinguish the
  # file-unlink record from the directory-rmdir record (both carry the same event name) -
  # assert on path=, or on the filesystem, never on the event name alone.
  - id: T1
    r1_a12_item: 1
    name: test_remove_cookie_artifact_dir_removes_created_dir
    place: TestCookieArtefactLifecycle
    asserts: >
      _create_cookie_artifact_dir() then _remove_cookie_artifact_dir(cookie_dir) leaves
      `not cookie_dir.exists()`. A REMOVED assertion, not a tracked one. Runs on Windows.
  - id: T2
    r1_a12_item: 2
    name: test_full_round_trip_removes_parent_dir
    place: TestCookieArtefactLifecycle
    asserts: >
      _create_temp_cookie_file -> unlink -> _remove_cookie_artifact_dir(file.parent) leaves
      `not file.parent.exists()`. The full round trip through the production entry point.
  - id: T3
    r1_a12_item: 3
    name: test_download_success_removes_dir_and_emits_no_cleanup_failure
    place: TestYtDlpSubprocessShutdown
    asserts: >
      On the success path the directory is absent AND no cookie_file_cleanup_failed record
      was emitted. Covers the lifted guard, the removability, and the log-noise regression
      in one oracle. Reuse the existing create_subprocess_exec patch idiom.
  - id: T4
    r1_a12_item: 4
    name: test_locked_cookie_file_records_one_failure_and_keeps_both
    place: TestYtDlpSubprocessShutdown
    asserts: >
      With Path.unlink patched to raise PermissionError: the credential file survives, the
      directory survives, exactly one cookie_file_cleanup_failed record is emitted (it holds
      only because this test patches Path.unlink wholesale, so the owner.pid unlink raises
      too and rule 4 short-circuits - do NOT generalise this to a real lock), and the
      outcome (None or the output path) is unchanged. Also assert the directory is still
      tracked in _COOKIE_ARTIFACT_DIRS - never discard on failure.
  - id: T5
    r1_a12_item: 5
    name: test_cancel_path_removes_dir
    place: TestYtDlpSubprocessShutdown
    asserts: >
      asyncio.CancelledError propagates out of _download_with_ytdlp AND the per-run
      directory is absent. The cancel arm re-raises; the finally: must still have run.
  - id: T6
    r1_a12_item: 6
    name: test_teardown_runs_when_cookie_file_already_absent
    place: TestYtDlpSubprocessShutdown
    asserts: >
      With the credential file deleted before the finally: runs, _remove_cookie_artifact_dir
      is still called and the directory is absent. This is the R1-A2 guard and no current
      test covers it. Without it the block does not close.
  - id: T7
    r1_a12_item: 7
    name: test_owner_pid_unlink_failure_skips_rmdir_and_records
    place: TestCookieArtefactLifecycle
    asserts: >
      A credential file left in the directory makes rmdir fail: one
      cookie_file_cleanup_failed record with path=str(cookie_dir), the directory survives,
      it is still tracked, and cookie_file_cleaned_up is NOT emitted for it. Plus a
      companion assertion that a second call on an already-removed directory emits NO
      record - this is what pins the FileNotFoundError-before-OSError arm ordering.
  - id: T8
    r1_a12_item: 8
    name: test_artifact_dir_set_does_not_grow_across_cycles
    place: TestCookieArtefactLifecycle
    asserts: >
      After N create/teardown cycles the size of _COOKIE_ARTIFACT_DIRS is unchanged
      (N >= 3). R1-A1 measured it growing by one entry per teardown. Growth must be
      bounded by real failures, not by runs.
  - id: T9
    r1_a12_item: 7 (rewrite)
    name: test_create_cookie_artifact_dir_creates_private_subdir_in_temp
    place: TestCookieArtefactLifecycle
    change: >
      Replace the finally block's _remove_cookie_artifact_dir + _COOKIE_ARTIFACT_DIRS.discard
      with a post-assertion `assert not cookie_dir.exists()`. Keep both existing assertions
      (direct child of the temp root; tracked) unchanged and add the gone-assertion.
  - id: T10
    r1_a12_item: 7 (rewrite)
    name: test_create_cookie_artifact_dir_writes_owner_pid
    place: TestCookieArtefactLifecycle
    change: Same rewrite as T9. Keep the owner.pid existence and PID-value assertions.
  - id: T11
    r1_a12_item: 7 (rewrite)
    name: test_file_created_in_private_cookie_subdir
    place: TestCreateTempCookieFile
    change: >
      Replace the finally block's _remove_cookie_artifact_dir + discard with
      `assert not result.parent.exists()` after the body. Keep all three existing
      assertions (not the temp root, strict descendant, tracked) unchanged. Its docstring
      already explains the inversion; leave that text alone.
  - note_on_why_the_rewrite_matters: >
      Today those three finally blocks discard a directory they have just failed to remove,
      converting TRACKED residue into UNTRACKED residue - measured at 3 such directories
      after one test run, all dead-owner, which is the same count R3 measured independently.
      After Alt A they become no-ops; the rewrite makes a regression FAIL a test instead of
      leaking residue silently.

commit_message_must_record:
  subject: "fix(cookies): remove the per-run artefact directory on every interceptable end"
  body_must_contain:
    - >
      Alt A selected: unlink cookie_dir / _OWNER_PID_FILENAME with unlink(missing_ok=True),
      then cookie_dir.rmdir(). FileNotFoundError is the success case and its except arm
      precedes except OSError because it subclasses OSError. An OSError from the owner.pid
      unlink records once and skips rmdir, which provably cannot succeed while that file
      exists. Measured 50/50 removals on Windows against 0/10 for the landed shape
      (WinError 145).
    - >
      Why Alt B was rejected, with the measurement: shutil.rmtree(ignore_errors=True) with a
      credential file held open without delete sharing silently deleted owner.pid, left the
      directory AND the credential file, and emitted nothing - 20/20 trials, both creation
      orders. Without ignore_errors it raises visibly but the residue is still PID-less,
      because rmtree deletes entries one at a time with no ordering guarantee. Alt B
      MANUFACTURES the PID-less residue R2 exists to prevent and cannot be made safe.
    - >
      Why Alt C was rejected, on four independent grounds: prohibited by this block's
      non-negotiable list (it removes the owner.pid record); three existing tests import or
      write _OWNER_PID_FILENAME and a fourth depends on _read_owner_pid itself; it trades a
      file read for a name parse where mkdtemp's tail is
      exactly 8 characters from [a-z0-9_] so the PID must be delimited; and the sweep's bare
      startswith(dir_prefix) filter would become an unguarded silent no-op, hiding every
      stale directory forever.
    - >
      D-1's citation AND the correction. os.kill(pid, 0) stays POSIX-only; the Windows branch
      keeps the ctypes OpenProcess/GetExitCodeProcess/CloseHandle probe. The previously
      recorded rationale was wrong: it claimed "signal 0 is not in the console-control set".
      Measured on this interpreter signal.CTRL_C_EVENT == 0 and signal.CTRL_BREAK_EVENT == 1,
      and CPython 3.12.1 Modules/posixmodule.c::os_kill_impl branches on exactly those two
      constants (GenerateConsoleCtrlEvent) before reaching OpenProcess + TerminateProcess,
      per os.kill's documentation. So os.kill(pid, 0) on Windows is unreliable as a probe for
      a non-console target and would deliver a real CTRL_C to the operator's console group for
      a console target. The probe is unchanged in behaviour; only the documented reason is
      corrected. The false parenthetical was deleted, not supplemented.
    - >
      That 36b801e's commit body was EMPTY, so none of this provenance was recorded, and that
      history is not rewritten - it is discharged by this new commit's body.
    - >
      That test_file_created_in_system_temp_dir was renamed to
      test_file_created_in_private_cookie_subdir and its assertion inverted from
      `result.parent == temp_dir` to `result.parent != temp_dir`, unrecorded by 36b801e. The
      retarget is legitimate - the subject moved one directory level down, so the assertion is
      not relaxed but re-aimed at a stronger property. The failure was the silence, and it is
      recorded here.
    - >
      That NO .gitignore rule was added, and why: artefacts are created under
      tempfile.gettempdir() (%TEMP%), outside the working tree, so a residue directory cannot
      surface in git status. R1-A5 separately measured that .gitignore's only cookie rule,
      *_cookies.txt, does not match the product's vk_cookies_<rand>.cookies.txt either
      (underscore vs dot); that is a pre-existing global gap, not R1's to fix, and the
      module comment claiming otherwise has been corrected in place.
    - >
      That Alt A opens a PID-less window between the owner.pid unlink and the rmdir, measured
      at median 0.164 ms / max 0.322 ms, and that R2 INHERITS it: a hard kill inside that
      window leaks one EMPTY directory, which R2's PID-less rule will decline. The window
      cannot hold credential material because the credential file is always unlinked first.
    - >
      D-2's deferral with the dependency named (no pywin32, no ctypes ACL reader; half (ii) of
      SEC-001 stays deferred) and D-3's anchor choice (the module-level guard in
      ytdlp_downloader.py, not the cli.py preamble).
    - >
      That no top-level glob and no age heuristic was used, and why: VAL-602 rejected both, and
      a top-level glob would sweep artefacts belonging to other tools in a shared temp root.
    - >
      That _COOKIE_ARTIFACT_DIRS is now pruned only on a definitive gone-outcome and never on
      failure, so growth is bounded by real failures rather than by runs, and the atexit
      handler no longer re-purges removed paths.

acceptance_criteria:
  - id: AC-1
    criterion: The per-run directory is absent after success, failure and cancel; the tests run on Windows and are not skipped.
    verified_by: uv run pytest tests/test_hls_downloader.py -q -rs
  - id: AC-2
    criterion: No cookie_file_cleanup_failed record on any success path.
    verified_by: T3, T7
  - id: AC-3
    criterion: A test asserts removability, distinct from the existing parent-is-private-subdir assertion.
    verified_by: T1, T2
  - id: AC-4
    criterion: >
      _is_pid_alive's Windows branch is preserved in behaviour - PROCESS_QUERY_INFORMATION,
      259 / STILL_ACTIVE, CloseHandle, os.kill(pid, 0) POSIX-only - and only its docstring
      changed.
    verified_by: review + T-tests unchanged
  - id: AC-5
    criterion: >
      Frozen strings, both event names, the try/except OSError/else shape, os.chmod(path, 0o600),
      the DF-007: comment, and the absence of a top-level glob and an age heuristic are all
      unchanged. The teardown runs whenever cookie_file is not None.
    verified_by: review
  - id: AC-6
    criterion: >
      The commit message names the Alt A selection and both rejections, the corrected D-1
      rationale with its citation, the empty body of 36b801e, the unrecorded rename and
      inversion, the .gitignore decision, and the ~0.16 ms window R2 inherits.
    verified_by: git log -1
  - id: AC-7
    criterion: The third artefact string vk_cookies__dir is frozen explicitly and its ignore coverage is RECORDED, not extended.
    verified_by: commit message
  - id: AC-8
    criterion: _COOKIE_ARTIFACT_DIRS does not grow across repeated create/teardown cycles, and a survivor stays tracked.
    verified_by: T8, T4
  - id: AC-9
    criterion: The three existing finally blocks assert the directory is gone; no existing oracle was weakened.
    verified_by: T9, T10, T11 + the four TestYtDlpSubprocessShutdown cookie tests unchanged

gates:
  - command: uv run pytest -q -rs
    pass_condition: exit 0; total skips <= 6; the three phase-05 killpg skips are pre-existing and unrelated; the D-11 floor stays 3
  - command: uv run pytest tests/test_hls_downloader.py -q -rs
    pass_condition: >
      green, and the new lifecycle tests are RUNNING on Windows - not skipped. A new
      skipif on os.name == "nt" in any of T1-T11 is a failure of this gate.
  - command: uv run mypy src
    pass_condition: "Success: no issues found; exit 0"
  - command: uv run ruff check src tests
    pass_condition: "All checks passed!"
  - command: uv run ruff format --check src tests
    pass_condition: exit 0; green with NO exception clause; do not fold a reformat into this change
  - command: uv run mypy src tests
    pass_condition: error count <= 93 (delta gate; the exit code is meaningless and is not a gate)
  - command: git status --porcelain
    pass_condition: >
      only the two intended paths staged; nothing under tmp/; nothing under
      .ai/audit/99-validation/; the pre-existing unrelated entries untouched and uncommitted
  not_gates:
    - uv run ruff check .   # red on untracked tmp/ by design
    - uv run mypy           # invalid invocation
    - the exit code of uv run mypy src tests
    - the legacy bare-file residue count (belongs to plan 17 §9 Q1)

staging:
  stage_exactly_these_paths:
    - src/vkdownloader/services/ytdlp_downloader.py
    - tests/test_hls_downloader.py
  never:
    - git add -A
    - git add .
    - git add -u
    - git commit --amend
    - git push --force
    - git reset (any form)
    - git checkout (any form)
  leave_untouched_and_uncommitted:
    - tmp/
    - tmp_old_sec.md
    - tmp_old_sec2.md
    - the deleted .ai/plans/00_* through 07_* templates
    - .ai/problems/PROBLEM.md
    - .kilo/commands/implement/implement-plan-multiagent.md
    - the untracked plans 05-08
    - .gitignore
  verification_before_commit: git diff --cached --name-only must list exactly the two paths above.

validator_notes:
  - >
    On the locked-file path TWO records are correct in production - one from the file arm
    (path = the file) and one from the directory arm (path = the directory) - two distinct
    facts, two distinct paths. Do not let T4's "exactly one record" be generalised to a real
    lock; it holds only because T4 patches Path.unlink wholesale.
  - >
    Check the arm ordering explicitly: except FileNotFoundError must textually precede
    except OSError in _remove_cookie_artifact_dir. Reversed, a correct teardown emits a
    spurious warning.
  - >
    Verify the four existing cookie_file_cleaned_up / cookie_file_cleanup_failed tests pass
    UNCHANGED: test_cookie_file_removed_and_logged_on_success,
    test_cookie_cleanup_failure_does_not_replace_success_outcome,
    test_cookie_cleanup_failure_does_not_replace_failure_outcome,
    test_cookie_cleanup_failure_does_not_replace_shutdown_outcome,
    test_cookie_cleanup_failure_child_reaped_before_unlink.
  - Re-measure that no residue directory is left in the OS temp root after a test run.
  - >
    Recorded, not owned by R1: _sweep_stale_cookie_dirs's docstring says the prefix is
    "vk_cookies_dir", but the composed value is "vk_cookies__dir" (_COOKIE_ARTIFACT_PREFIX
    + _ARTEFACT_DIR_SUFFIX, i.e. a doubled underscore). The code is correct; the docstring
    is not. R1-R6 puts the sweep out of scope, so this is handed to R2 rather than fixed
    here - do not touch it in this commit.
```

---

#### `R1-VALIDATION` — validation record (Validator)

Verbatim record of the independent Validator's adjudication of block `R1` as landed at
`72c8283`. **Verdict: `ACCEPT WITH REQUIRED FOLLOW-UP`.** `SEC-002` is **closed** by that
commit — mechanism, arm ordering, tracking-set pruning, lifted guard, all regression
prohibitions, all eleven tests, and all seven gates verified by execution. The single
required follow-up item, **`V-1`**, is a provenance defect in the commit *body* only; it
is recorded here and **no code change** accompanies it, because nothing in `SEC-002`'s
closure depends on it and history may not be amended.

##### `V-1` — commit-body polarity inversion (Alt B safety claim)

`72c8283`'s body reads: "Alt B MANUFACTURES the PID-less residue R2 exists to prevent
**and can be made safe**." `R1-R1` (line 750) mandates the opposite polarity:
**"and *cannot* be made safe."** The inversion is unsupported and is false as written:

- `shutil.rmtree` violates criterion 1 (`R1-R1`) — it reaches the credential file — so it
  cannot satisfy "must never destroy a directory that still holds credential material a
  failed unlink left behind, without a visible record".
- With `ignore_errors=True` the raise is swallowed (`R1-A7`, `R1-R1`): the failure is
  invisible, exactly the silent-residue hazard `R2` exists to prevent.
- Without `ignore_errors=True` the `OSError` arm survives and the warning returns, but the
  residue remains PID-less (the `owner.pid` unlink precedes the raise), so "made safe" is
  not restored. The only repair — restoring `owner.pid` after the failed `rmtree` — was
  explicitly **declined** in `R1-R1`.

Resolution: the body text is corrected **in this record only** — Alt B **cannot** be made
safe; the landed shape does not use it. No production file is amended; `72c8283` stands as
committed. Nothing in `SEC-002`'s closure depends on the commit body's prose.

##### Evidence the Validator established

**Falsification was run, not reasoned.** Against the pre-fix `36b801e` source in a scratch
copy:

- 10 of the 11 new/rewritten tests **fail**; every failure is `WinError 145`-driven.
- Isolating the lifted guard alone → **1 failed, 10 passed**; the single failure is
  `test_teardown_runs_when_cookie_file_already_absent` — so **T6 alone pins the guard**.
- Isolating the reversed `except` arms → **1 failed, 2 passed**; the single failure is
  `test_owner_pid_unlink_failure_skips_rmdir_and_records` Part B — so **T7 alone pins the
  arm ordering**.

The five pre-existing cookie tests are **byte-identical** between `36b801e` and `72c8283`
(AST-extracted, including decorators). No expectation got looser. The only hunk inside
`TestYtDlpSubprocessShutdown` is a pure 245-line addition.

`T4` (`test_locked_cookie_file_records_one_failure_and_keeps_both`) is **non-discriminating
by design** — it passes against both pre-fix and post-fix source. It is a non-regression
guard pinning the failure-path contract, and its docstring correctly carries the "do not
generalise to a real lock" warning. Honest accounting: **10 of 11 discriminate.**

Residue after a full suite run: **0 directories in `%TEMP%`** (was 3 before).

Commit-body falsifiable claims re-measured — all **true** except `V-1`:

| Claim in body | Re-measured | Verdict |
|---|---|---|
| Alt A 50/50 removals | 50 / 50 | true |
| Landed shape 0/10 | 0 / 10 (`WinError 145`) | true |
| PID-less window median | 0.165 ms | true |
| `signal.CTRL_C_EVENT == 0` | `0` | true |
| `CTRL_BREAK_EVENT == 1` | `1` | true |
| CPython | 3.12.1 | true |
| `36b801e` body length | 0 characters (empty) | true |
| rename + assertion inversion present in that diff | present | true |
| `.gitignore` rule is `*_cookies.txt` vs product's dot separator | confirmed via `git check-ignore` | true |
| artefacts under `%TEMP%` outside the tree | confirmed | true |
| no pywin32 or ACL reader | confirmed | true |
| `D-3`'s anchor is module-level | confirmed | true |

Gates re-run independently (final `§7` numbers):

| Gate | Result |
|---|---|
| full suite | **820 passed, 6 skipped** |
| `test_hls_downloader.py` | **192 passed, 2 skipped** |
| `mypy src` | clean (31 files) |
| `ruff check src tests` | clean |
| `ruff format --check src tests` | clean (54 files) |
| `mypy src tests` | **93 errors in 8 files** |
| `test_packaging` | 14 passed |

Skip accounting exact: 3 D-11 (`test_config.py` ×2, `test_hls_downloader.py` ×1) +
3 pre-existing `killpg` (`test_ffmpeg_utils.py` ×2, `test_hls_downloader.py` ×1).
**D-11 floor still 3; no new skip.**

##### Advisories carried forward

- **`A-1` → hands to `R2`.** The recorded window maximum (0.322 ms) understates the tail.
  Over 200 samples: median **0.165 ms**, max **0.864 ms**. Conclusion unaffected (an empty
  directory, never credential material), but `R2` must budget the larger tail.
- **`A-2`.** `_is_pid_alive`'s new text says `os.kill(pid, 0)` "delivers a real CTRL_C event
  to that process's console group" for a console target. `GenerateConsoleCtrlEvent`'s second
  argument is a **process-group id**, so delivery additionally requires the target to be a
  console process-group leader; for a non-leader console process the call also fails. Wording
  inherited verbatim from `R1-R5`'s prescribed text; the operative conclusion (never probe
  with `os.kill` on Windows) is unaffected. Precision only.
- **`A-3`.** `_remove_cookie_artifact_dir`'s docstring explains the *unlink*-`OSError`
  short-circuit but not the *`rmdir`-`OSError` path (`WinError 145` with a surviving
  credential file) — reachable, and exercised by `T7`, whose own docstring describes it
  correctly.
- **`A-4`.** The test name `test_owner_pid_unlink_failure_skips_rmdir_and_records` names an
  unlink failure, but the test's scenario is an `rmdir` failure. Name inherited from
  `required_tests` T7; the test's docstring is accurate. Rule 4's true short-circuit is
  exercised by `T4`.
- **`A-5`.** In `test_file_created_in_private_cookie_subdir` the `finally:` no longer attempts
  directory removal, so a body failure leaks untracked residue. Test-only; `T9`/`T10` keep
  their `finally` removal and correctly keep the survivor **tracked** so `atexit` reclaims it.
- **`A-6`.** Bookkeeping — resolved in the execution-table update and the `B1`/`R2` hand-off
  below.

##### `R2` hand-off

Nothing is inherited silently:

- **The sweep's creation race is untouched.** `_create_cookie_artifact_dir` still calls
  `mkdtemp` and only then writes `owner.pid`, and `_sweep_stale_cookie_dirs` still treats a
  missing PID record as stale and `rmtree`s it. `R2`'s alternatives remain genuinely open.
- **`Alt A`'s PID-less window is inherited** — not pre-empted. Between the `owner.pid`
  unlink and the `rmdir`, median 0.165 ms / max 0.864 ms (re-measured over 200 samples; see
  `A-1`). A hard kill inside it leaks **one empty directory**, which `R2`'s PID-less rule
  will decline. It cannot hold credential material — the credential file is always unlinked
  first: in `_download_with_ytdlp`'s `finally:` and in `_create_temp_cookie_file`'s
  write-error path, where the unlink precedes the directory removal in both.
- **Two coverage notes.** `R2` should not inherit `V-2` as a defect — `T4` is a deliberate
  non-regression guard, non-discriminating by design (see above). `T6` and `T7` are single
  points of coverage for the guard and the arm ordering respectively, and `R2` should not
  weaken either.
- **The doubled-underscore docstring drift is carried to `R2`.** `_sweep_stale_cookie_dirs`'s
  docstring still says the prefix is `vk_cookies_dir` while the composed value is
  `vk_cookies__dir` (`_COOKIE_ARTIFACT_PREFIX` + `_ARTEFACT_DIR_SUFFIX`). The code is
  correct; the docstring is not. `R1`'s scope puts the sweep out of reach, so this is
  **deferred to `R2`** — do not touch it in the `R1` commit.

---

### `R2` — Close the sweep's creation race (`VAL-602`)

**Goal.** `_create_cookie_artifact_dir` calls `mkdtemp` and **then** writes `owner.pid`;
`_sweep_stale_cookie_dirs` treats a missing PID record as stale and deletes with
`rmtree`. A concurrently-starting run's directory is therefore deleted out from under it.
`VAL-602`'s concurrency hazard is narrowed, not closed, at `36b801e`. Criterion 5 covers a
*live* PID only — never a *PID-less* directory.

**Findings carried.** `VAL-602` (incomplete at `36b801e`), `SEC-002` (concurrent-reclamation
half).

**Exact semantic scope.**

1. `services/ytdlp_downloader.py::_create_cookie_artifact_dir` and
   `::_read_owner_pid` — the creation window between the directory existing and its
   liveness record existing.
2. `services/ytdlp_downloader.py::_sweep_stale_cookie_dirs` — the rule for a directory with
   **no** readable `owner.pid`. Today: stale. It must become a state that cannot destroy a
   live artefact.
3. `services/ytdlp_downloader.py::_purge_cookie_artifact_dir` — only as an alternative
   requires.
4. `tests/test_hls_downloader.py` — a test that a **PID-less** directory survives a sweep,
   plus re-verification that the dead-PID sweep and live-PID survival tests exist and pass.
   Criterion 5 covers a live PID only; this block adds the missing half.

**Alternatives — genuine technical uncertainty. No choice is made here.**

- **`Alt A` — grace by age on a PID-less directory only.** Cheap. Weakness that must be
  stated: this invents the magic duration `VAL-602` explicitly said a fixer must invent and
  cannot judge. Note the asymmetry that keeps it defensible — an age threshold used as a
  **skip** condition is not the age-based **deletion** criterion `VAL-602` rejected.
- **`Alt B` — a creation marker written into the new directory**, with "no marker at all"
  read as mid-creation and therefore untouchable. Narrows the window to microseconds; does
  not close it.
- **`Alt C` — the PID in the directory name** (fuses with `R1`'s `Alt C`). A directory whose
  name carries no parseable PID is never deleted. Zero window. Largest change, and it must
  be chosen jointly with `R1`.
- **`Alt D` — a cross-process lock around sweep and create.** Stdlib `msvcrt.locking` /
  `fcntl` on a well-known lock file in the temp root; no new dependency. Structurally
  correct. Costs a fourth artefact string and its ignore coverage, and the lock's own
  failure modes need stating.

**Criterion for choosing:** a directory that is provably mid-creation must never be
deleted; **no magic duration may be invented**; no new dependency; prefer a structural
solution (C or D) over a duration. `R2` consumes `R1`'s recorded choice — if `R1` chose
`Alt A` (record deleted before removal), this block's PID-less rule must cover that window
by construction, and the coupling is named in the commit.

**Open decisions.**

- `R2-D1` — which alternative. Criterion above, plus `R1`'s recorded choice.
- `R2-D2` — whether a PID-less directory is *skipped* forever or reclaimed under a
  separately-justified rule. Criterion: reclamation must not be able to destroy a live
  artefact, and any reclamation rule must be stated separately from the liveness rule so a
  reader can tell them apart.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | A **PID-less** directory survives a sweep. Runs on Windows. | new test |
| 2 | A directory whose `owner.pid` records a **dead** PID is swept. | existing test, re-verified present and passing |
| 3 | A directory whose `owner.pid` records the **current** process survives. | existing test |
| 4 | No age heuristic appears in the **deletion** criterion. No top-level glob appears. | review |
| 5 | The commit message names `R1`'s chosen alternative and how this block's rule covers it. | commit message |
| 6 | **Gates:** as `R1`. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The window's real extent must be traced against the live call order — `_ensure_cookie_lifecycle_started` sweeps *before* the run's directory is created, but a second process in another terminal does not observe that ordering. |
| `Researcher` | no | No external behaviour is in question. This is an ordering and atomicity design problem inside one module, answerable from the repository. Skipped deliberately rather than padded. |
| `Planner` | **yes** | Four alternatives with a hard safety criterion and a coupling to `R1`'s choice. |
| `Validator` | **yes** | The failure mode being closed is a destructive one; a wrong rule here deletes a concurrent instance's credential file. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `fix(cookies): never reclaim a cookie artefact directory that is still being created`

```yaml
id: EB-R2
title: Close the cookie artefact sweep's creation race
priority: high
depends_on: [EB-R1]
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.2, §6.4 (T-B2 steps 6, 12), §6.5, §7.1 (B2 row)"
source_blocks: [B2]
description: >-
  _create_cookie_artifact_dir creates the directory with mkdtemp and only then writes
  owner.pid, while _sweep_stale_cookie_dirs treats an unreadable owner.pid as stale and
  purges with rmtree. A concurrently-starting run's directory is therefore destroyed out
  from under it, so VAL-602's concurrency hazard is narrowed rather than closed at 36b801e.
  This block makes the PID-less state incapable of destroying a live artefact, without
  inventing a magic duration and without a new dependency.
goals:
  - A directory that is provably mid-creation is never deleted by the sweep.
  - Dead-PID reclamation and live-PID survival are unchanged and both remain tested.
  - The rule is compatible with, and explicitly records, R1's chosen alternative.
files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: modify
    semantic_anchors:
      - _create_cookie_artifact_dir
      - _read_owner_pid
      - _sweep_stale_cookie_dirs
      - _purge_cookie_artifact_dir
      - _ensure_cookie_lifecycle_started
  - path: tests/test_hls_downloader.py
    targets: modify
    semantic_anchors:
      - TestCreateTempCookieFile
      - the sweep lifecycle tests
  - path: .gitignore
    targets: conditional
    semantic_anchors:
      - the vk_cookies_*.cookies.txt rule
changes:
  - what: Give the PID-less directory a rule that cannot destroy a live artefact.
    why: >-
      mkdtemp-then-write leaves a window the sweep reads as staleness; criterion 5 covered
      a live PID only and never a PID-less directory.
    alternatives_considered:
      - "Alt A: age grace on a PID-less directory only (invents a duration; VAL-602 warns against it)."
      - "Alt B: creation marker in the directory (narrows the window, does not close it)."
      - "Alt C: PID in the directory name (zero window; choose jointly with R1)."
      - "Alt D: stdlib cross-process lock around sweep and create (structural; adds a lock artefact string)."
    blocked_by: []
  - what: Add the PID-less survival test and re-verify the dead-PID and live-PID tests.
    why: >-
      The creation race is only observable through the sweep's own test surface.
    alternatives_considered: []
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: A directory with no readable owner.pid survives a sweep, on Windows.
    verified_by: new test
  - id: AC-2
    criterion: A dead-PID directory is swept; the current process's own directory survives.
    verified_by: existing tests, re-verified
  - id: AC-3
    criterion: No age heuristic in the deletion criterion; no top-level temp glob.
    verified_by: review
  - id: AC-4
    criterion: The commit message names R1's chosen alternative and how this rule covers it.
    verified_by: git log -1
  - id: AC-5
    criterion: Full suite green; ruff check clean; ruff format --check green; mypy src clean; mypy src tests <= 93.
    verified_by: §7 gates
```

#### `R2-AUDIT` — block-`R2` audit findings (Auditor)

Read-only inspection at `72c8283`. Nothing was modified — no production code, no test, no
audit-phase file, and nothing in the staging area. Every measurement below was **executed** on
this machine (Windows, CPython 3.12.1, NTFS, `%TEMP%` holding 2383–2385 entries) unless marked
otherwise. Symbols are named, never line-numbered. The `R1-AUDIT`, `R1-RESEARCH`, `R1-DESIGN`
and `R1-VALIDATION` regions were read in full and are inherited explicitly in `R2-A13`.
**No alternative is chosen here**; each is characterised against the real code in `R2-A11`.

**Baseline adopted, not re-derived.** 820 passed / 6 skipped · `test_hls_downloader.py` 192
passed / 2 skipped · `mypy src` clean (31 files) · `ruff check src tests` clean ·
`ruff format --check src tests` clean (54 files) · `mypy src tests` 93 errors in 8 files ·
D-11 oracle floor 3 · skips 6 = 3 D-11 + 3 pre-existing `killpg`. Residue in `%TEMP%`
measured at both the start and the end of this audit: **0** artefact directories, **1295**
legacy bare `vk_cookies_*.cookies.txt` files (`R3`'s subject). `git status` is byte-identical
before and after. `TestCookieArtefactLifecycle` re-run at `72c8283`: **12 passed**.

##### `R2-A1` — the creation window is real, wider than "no file", and `write_text` is not atomic

`_create_cookie_artifact_dir` performs, in this exact order:

1. `_ensure_cookie_lifecycle_started()` — sweep, then `atexit.register` (`R2-A5`).
2. `Path(tempfile.mkdtemp(prefix=dir_prefix))` — **the directory now exists and is
   enumerable by any concurrent sweep, and carries no PID record.**
3. `owner_file = cookie_dir / _OWNER_PID_FILENAME` — pure path arithmetic, no I/O.
4. `owner_file.write_text(str(os.getpid()))` — **not atomic.**
5. `with _COOKIE_LIFECYCLE_LOCK: _COOKIE_ARTIFACT_DIRS.add(cookie_dir)`.

**Step 4 is not atomic, and the first observable sub-state is not "file absent" but "file
present and zero-length".** `Path.write_text` is `io.open(mode='w')` then `write` then
`close`; `mode='w'` **creates the file** before any byte is written. A sweep that reads the
directory inside that span sees `owner.pid` with `st_size == 0`.

Measured (200 trials, split of the exact sequence):

| Span | median | p95 | max |
|---|---|---|---|
| `open(mode='w')` — the sub-window in which `owner.pid` exists and is **empty** | 0.107 ms | — | 0.327 ms |
| `write` + `close` | 0.062 ms | — | 0.207 ms |
| **`write_text` end to end — the PID-less window** | **0.236 ms** | 0.546 ms | **1.482 ms** |
| `lock` + `set.add` (after the record exists) | 0.018 ms | 0.039 ms | 0.119 ms |

So the window a concurrent sweep can observe as "PID-less" is **median ≈ 0.24 ms, max ≈ 1.5 ms**
— two orders of magnitude wider than the "microseconds" the `R2` block's `Alt B` bullet
assumes, and *wider than* `R1`'s teardown-side window, which `R1-VALIDATION`'s `A-1`
re-measured at median 0.165 ms / max 0.864 ms over 200 samples. My independent re-measure of
the teardown window this session: **median 0.120 ms, max 0.454 ms** over 200 samples — same
order, consistent with the recorded figure. **`R2` must budget both tails, and they are the
same size; the creation window is the larger of the two.**

Also **not** atomic, and unmeasured by `R1`: there is no `fsync` anywhere in the create path, so
a machine-level crash (power loss) can leave `owner.pid` present and zero-length indefinitely.
That state is classified stale by the current rule and destroyed — which is the *safe*
direction for a crash, so this is correctness-of-documentation only, but it does mean the
"zero-length" sub-state is reachable without concurrency.

**What `_read_owner_pid` returns for a partially-written file: a wrong `int`, not `None`.**
Verified by execution:

| `owner.pid` content | `_read_owner_pid` | `_is_pid_alive` | sweep classification |
|---|---|---|---|
| absent | `None` | — | **stale** |
| `""` (zero-length) | `None` | — | **stale** |
| `"   \n"` | `None` | — | **stale** |
| `"not-a-pid"` | `None` | — | **stale** |
| `"<pid>\x00"` | `None` | — | **stale** |
| `"14"` (torn write of `"14920"`) | **`14`** | `False` | **stale — and wrong** |
| `"-1"` | `-1` | `False` | stale |
| `"0"` | `0` | `False` | stale |
| `"2147483647"` | `2147483647` | `False` | stale |
| `owner.pid` is a **directory** | `None` | — | **stale** |
| `owner.pid` **ACL-denied** (`icacls /deny <user>:(R)`) | `None` | — | **stale** |

The torn-write row is the important one: `int()` accepts any ASCII digit prefix, so a partial
write does **not** degrade to `None` — it produces a **plausible-looking but wrong PID**, which
then answers the liveness question with `False`. `R2`'s scope item 1 names `_read_owner_pid`;
this is a distinct misclassification channel from the one the `R2` block describes, and a
fix that only changes the *sweep's* treatment of `None` does not close it. **A torn write is
not practically reachable on this platform** (5 bytes, one `WriteFile`, no `fsync`) — it is
listed for completeness, not as a hazard to size.

##### `R2-A2` — `_read_owner_pid`'s `(OSError, ValueError) → None` conflates six distinct states

Verified by reading. `int(owner_file.read_text().strip())` inside `try`, with a single
`except (OSError, ValueError): return None`. The `None` return therefore means **any one** of:

1. `owner.pid` does not exist — **mid-creation** (the `R2` subject) **or** the `R1` teardown window.
2. `owner.pid` exists but is empty — the `open(mode='w')` sub-window (`R2-A1`), or a crash.
3. `owner.pid` exists, is non-empty, and is unparseable — truncated/garbage/`NUL`-suffixed.
4. `owner.pid` is a **directory**, not a file — `IsADirectoryError` is an `OSError`.
5. `owner.pid` is **unreadable** — `PermissionError` from an ACL, an indexer, or another user
   in a shared temp root. **Executed**: `icacls /deny` → `read_text` raises `PermissionError`
   → `_read_owner_pid` returns `None`.
6. `owner.pid` is a **partially-written digit prefix** — returns a *wrong `int`*, not `None`
   (`R2-A1`).

States 1, 2 and 5 are **"I could not determine the owner"** and are treated as **"the owner
is dead"**. That conflation *is* the misclassification, and it is not only a creation problem:
**state 5 destroys a live run's directory** whenever the owner is a process this user cannot
query — see `R2-A6`, where that is measured.

##### `R2-A3` — `_sweep_stale_cookie_dirs`: the exact rule, and it is over-broad against `VAL-602`'s own text

Verified by reading. In order:

1. `temp_dir = Path(tempfile.gettempdir())`.
2. `dir_prefix = _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX` → composed value
   **`'vk_cookies__dir'`** (measured by `repr`), a **doubled** underscore.
3. `stale: list[Path] = []`.
4. One `try` wrapping the whole classification loop:
   `for entry in temp_dir.iterdir():` → `if not entry.is_dir(): continue` →
   `if not entry.name.startswith(dir_prefix): continue` → `owner_pid = _read_owner_pid(entry)`
   → **`if owner_pid is None or not _is_pid_alive(owner_pid): stale.append(entry)`**.
5. `except OSError: return` — a mid-iteration failure **discards the entire snapshot**, so
   nothing is purged on a partial scan. Fail-safe direction; noted, not a defect.
6. **Purge loop outside the `try` and outside the lock:** for each entry,
   `_purge_cookie_artifact_dir(cookie_dir)` then, under `_COOKIE_LIFECYCLE_LOCK`, a single
   `_COOKIE_ARTIFACT_DIRS.discard(cookie_dir)`. The lock is **never held across a filesystem
   call** — the `R1-R3` discipline, correctly followed. The `discard` of a *foreign*
   directory is a no-op on the local set (`Path` hashing is by string); harmless.

**The filter is a bare `startswith` on a composed prefix — `R1-R1`'s ground 4 is confirmed
still true at `72c8283`.** Nothing guards it: no assertion, no test that a fresh
`_create_cookie_artifact_dir()` result is matched by the sweep's own filter. Any alternative
that moves the PID out of the leading run, or edits either constant, converts the sweep into a
**silent no-op** — the exact `SEC-002`/`VAL-602` failure mode `VAL-602` calls "the worst
failure mode available here".

**The rule is over-broad relative to the finding it implements — `[SPEC-DEVIATION]`.**
`VAL-602`'s recommendation (verbatim, `06-credentials-secrets-validated-findings.md`) is:
*"make the reaper a sweep of *those* directories, deleting one only when its recorded PID is
no longer live"*. A directory with **no recorded PID** has no recorded PID to find not-live, so
the finding as written does not authorise deleting it. The landed `owner_pid is None or not
_is_pid_alive(owner_pid)` adds the `or None` disjunct. **`R2`'s fix is therefore a restoration
of `VAL-602`'s stated semantics, not a new policy** — which materially strengthens the case
against `Alt B`-style rules that keep `None ⇒ stale`.

**Operational cost, measured.** `_sweep_stale_cookie_dirs()` called against the real
`%TEMP%` (2383 entries, 0 matches): **median 148.5 ms, min 139.4 ms, max 172.3 ms**, i.e.
**~62 µs per entry**, dominated by `entry.is_dir()` (one `stat` per entry; `_read_owner_pid`
runs only for matches). This is paid **synchronously, inside `_build_ytdlp_cli_command`, on the
event-loop thread, at the first artefact creation of every process**. Two consequences for
`R2`: (a) it is a real, if small, start-up latency tax that grows with the temp root; (b) any
design that holds a cross-process lock across the whole scan serialises 148 ms, whereas
*classify-under-lock, purge-outside-lock* — the shape the code already has — does not. Measured
`Path.iterdir()` cost and enumerator advance rate are in `R2-A7`.

##### `R2-A4` — `_purge_cookie_artifact_dir` confirmed recursive and unconditional — and it **cannot** reach a credential file during this race

Verified by reading: `shutil.rmtree(cookie_dir, ignore_errors=True)`, no liveness consult, no
depth limit, no allow-list. `R1-A7` stands. Two `R2`-specific consequences, both executed or
traced:

- **The brief's worst case — "a lost credential mid-download" — is NOT reachable through the
  creation race.** `_create_cookie_artifact_dir` runs to completion before `_create_temp_cookie_file`
  calls `tempfile.mkstemp(dir=str(cookie_dir))`. Within the PID-less window the directory is
  **empty by construction**, so `rmtree` destroys the directory and nothing else.
- **The blast radius is an unhandled `FileNotFoundError` from `write_text`.** Executed
  deterministically (see `R2-A7`): the victim's `_create_cookie_artifact_dir` raises
  `FileNotFoundError: ...\owner.pid`. That call site is `_build_ytdlp_cli_command`, which
  `_download_with_ytdlp` invokes **before its `try:`** — so `cookie_file` is never bound, no
  `finally:` runs, and nothing leaks. `download_with_ytdlp_with_resume_fallback`'s retry loop
  has **no** `except` around `_download_with_ytdlp`. Consequences by mode
  (verified by reading): **batch** → caught by `_download_single`'s `except Exception`, recorded
  as `unexpected_error_in_batch_download` via `logger.exception` (full traceback, i.e. the
  `R1-A4` `SEC-006`/`SEC-007` record shape, and the temp path appears in it), item marked
  `FAILED` as `unexpected_error: FileNotFoundError` — **one video lost, loudly**. **Single** →
  propagates to the CLI as an unhandled exception. No credential is lost and no residue is
  created in either mode; the cost is a failed download plus a noise-level record.

##### `R2-A5` — `_ensure_cookie_lifecycle_started`: sweep-then-register, and a latent intra-process window

Verified by reading. Exact body: acquire `_COOKIE_LIFECYCLE_LOCK` → `if
_cookie_lifecycle_started: return` → **`_cookie_lifecycle_started = True`** → release the lock →
`_sweep_stale_cookie_dirs()` → `atexit.register(_cleanup_cookie_artifact_dirs)`.

Two orderings matter, and only the first is correct:

- **Sweep before `atexit.register`:** the sweeper runs *before* the safety net exists. If
  anything unhandled escaped the sweep, the process would run its whole life with **no atexit
  net** and every surviving directory would become permanent residue. Nothing currently can
  escape — `Path.is_dir()` swallows `OSError`/`ValueError`, `_read_owner_pid` catches
  `OSError`, `iterdir()`'s `OSError` is inside the `try`, `_purge_cookie_artifact_dir` uses
  `ignore_errors=True` — so this is **latent, not live**. `[BEST-PRACTICE]`, trivial effort:
  register first, then sweep, or wrap the sweep in `try/except Exception`. Recommend recording,
  not changing, unless the `R2` design adds a new failure mode to the sweep.
- **Flag set *before* the sweep:** this is what makes single-thread self-collision impossible
  (see `R2-A7`) and what makes the multi-thread case **reachable**: thread A sets the flag, then
  spends 148 ms sweeping; thread B enters `_create_cookie_artifact_dir`, sees the flag, skips
  the sweep, and calls `mkdtemp` — creating a PID-less directory **inside A's sweep**. Same
  window, same destruction, no second process needed.

**Is the multi-thread case reachable in today's product? No — verified by reading.** The whole
create path is synchronous and contains no `await`: `_download_with_ytdlp` (async) →
`_build_ytdlp_cli_command` (plain `def`) → `_create_temp_cookie_file` (plain `def`) →
`_create_cookie_artifact_dir` (plain `def`). `batch_downloader` uses
`asyncio.create_task` + `gather` inside **one** event loop — there is **no** `multiprocessing`,
no `ProcessPoolExecutor`, no `subprocess.Popen`, and no `threading.Thread` anywhere in `src/`
(the only executor use is `extractor.py`'s `loop.run_in_executor(None, _sync_extract)`, which
runs Playwright extraction and never touches cookies). So concurrent artefact creation inside
one process cannot interleave today. It becomes reachable the moment anything calls
`_download_with_ytdlp` from a worker thread — and the module's use of a `threading.Lock` for
its own state signals that thread-safety is already assumed. `[BEST-PRACTICE]`, small effort:
either re-order the flag to be set *after* the sweep, or document the single-threaded
precondition next to `_COOKIE_LIFECYCLE_LOCK`.

##### `R2-A6` — PID reuse is **fast and random** on this platform, and `handle == 0` conflates "denied" with "dead"

**`A-2` is confirmed and must not be actioned.** `_is_pid_alive`'s `ctypes` probe is correct:
`OpenProcess(PROCESS_QUERY_INFORMATION=0x0400, False, pid)`, and `GetExitCodeProcess` with
`STILL_ACTIVE == 259`, and `CloseHandle` in `finally`. Measured `_is_pid_alive(os.getpid()) is
True`; `999999 → False`; `0, -1, 4 → False`. `R1-A10`'s corrected rationale and `R1-R5`'s
prescribed docstring are in place at `72c8283`. **Nothing in `R2` may change the probe's
behaviour** — `AC-4` of `R1` and `R1-A2` both say so. The two findings below are about what
the probe's *result* is allowed to mean.

**(a) PID reuse is fast, not slow — `[BEST-PRACTICE]` on `R1`'s implicit assumption.**
Executed, 400 `subprocess` spawns: **400 distinct PIDs, zero reuse**, all **multiples of 4**,
range `176 … 27628`, spread across 4 KiB buckets roughly uniformly (`{0:39, 1:43, 2:41, 3:45,
4:76, 5:78, 6:78}`, no entry ≥ 32768). So this platform does **not** allocate PIDs
sequentially — the counter is randomised, which is the documented Windows mitigation against
PID-reuse attacks. Consequences:

- The PID space in use is at most **32768 slots ÷ 4 = ~8192 distinct values**.
- With **345 live processes** on this box (`tasklist | Measure-Object -Line`), a *specific*
  dead PID is re-drawn with probability ≈ `345 / 8192` ≈ **4.2 % per new process creation**.
- Expected reuse of a given dead PID ≈ **24 process creations**. On a desktop with a browser, an
  editor and CI running — and with this product spawning **one yt-dlp subprocess per download**
  plus one ffmpeg per remux — that is **seconds to minutes, not hours or days**.
- A 25 s / 328-spawn burst produced no reuse, which is consistent (expected collisions in 328
  draws ≈ 328·345/8192 ≈ 13 *pairs* of live-PID collisions, but a *specific* PID being re-drawn
  328 times is only ≈13 expected hits spread over 328 distinct PIDs — i.e. the measurement is
  consistent with reuse being real but not yet observed at this volume).

**Direction of the error is safe:** a recycled PID makes a **dead** owner's directory look
**live**, so the residue is **retained**, not destroyed. The cost is that `SEC-002`'s residue
reclamation is unreliable for residue whose owner died within the last few thousand process
creations — which, given `R1-R4`'s failure path (a credential file whose unlink failed leaves a
surviving directory), can be credential-bearing. This is **pre-existing at `72c8283`**, is
independent of whichever alternative `R2` picks, and is **not** in `R2`'s declared scope; it
belongs in a `SEC-002`-residue note. Do **not** fix it with an age rule — that is the move
`VAL-602` rejected.

**(b) `handle == 0` conflates "does not exist" with "exists but access denied" — a SECOND
live-directory-destroy hazard, structurally identical to the creation race.** Executed with
`ctypes.WinDLL("kernel32", use_last_error=True)`:

| PID | `OpenProcess` handle | `GetLastError` | `_is_pid_alive` | reality |
|---|---|---|---|---|
| `0`, `1`, `2`, `3`, `4` | **0** | — | `False` | PID 4 is **`System`**, confirmed live by `tasklist` |
| `4` | **0** | **5 (`ERROR_ACCESS_DENIED`)** | **`False`** | **alive, misreported dead** |
| `999999` | **0** | **87 (`ERROR_INVALID_PARAMETER`)** | `False` | genuinely absent |
| `os.getpid()` | 296 | 0 | `True` | `GetExitCodeProcess` → `259` |

So a directory whose `owner.pid` names a process running **elevated, as a service, as SYSTEM,
or under another account** is classified **stale and `rmtree`'d while its owner is actively
running** — the same "destroy a live artefact" outcome `R2` exists to prevent, arriving through
a different channel. `_read_owner_pid` state 5 (`R2-A2`) is the second half of the same pair:
an unreadable `owner.pid` also yields `None` ⇒ stale.

**This is a scope gap, not a fix for `R2` to absorb silently.** `R2`'s declared scope is
`_create_cookie_artifact_dir`, `_read_owner_pid`, `_sweep_stale_cookie_dirs`,
`_purge_cookie_artifact_dir` and one test class — `_is_pid_alive` is not listed, and `R1-A2`
forbids changing its behaviour. The correct disposition is: **`R2-D3`, a new open decision**,
"does a PID record that cannot be *proven* dead count as stale?", with the default answer
**no** — which is the same conclusion `R2` reaches for the PID-less state and would apply to
this one for free if `R2` states its rule as a **default-deny** ("destroy only on a *positive*
demonstration of death") rather than as a special case for `None`. A Planner that adopts that
framing closes (b) as a side effect without touching the probe. **Recommend raising it, not
implementing it here.**

##### `R2-A7` — the race, quantified

**Deterministic proof that the defect is real** (not probabilistic reasoning). `Path.write_text`
was replaced with a wrapper that blocks on `_OWNER_PID_FILENAME` after `mkdtemp` returned; a
second thread ran `_sweep_stale_cookie_dirs()` and then released the block. Executed result:

```
exception  FileNotFoundError: [Errno 2] No such file or directory:
           'C:\...\Temp\vk_cookies__dir4g3tgpok\owner.pid'
residue dirs: []
```

The victim's directory was destroyed and the victim crashed. Every time the sweep *reaches* the
directory inside the window, the outcome is certain — only the *reaching* is probabilistic.

**Window width** (`R2-A1` table): median **0.236 ms**, p95 **0.546 ms**, max **1.482 ms**,
over 300 trials; the lock+`set.add` after the record exists adds 0.018 ms median.

**Sweep cost and enumerator advance rate.** `_sweep_stale_cookie_dirs()` on the real
`%TEMP%`: median **148.5 ms** for 2383 entries = **~62 µs per entry**. `os.scandir` **is**
streaming on this platform: a directory created at delay 0 / 1 / 5 / 20 / 50 / 100 ms into an
in-flight enumeration was yielded by that enumeration in **20/20 trials at every delay**, and a
bare full enumeration costs **~4.2 ms** (the 148 ms figure is `entry.is_dir()`'s 2383 `stat`
calls, not enumeration). **A directory created during a sweep is therefore always *seen*; the
only question is whether it is seen *soon enough*.**

**Hit-rate bound per concurrently-starting pair.** The enumerator advances one entry every
~62 µs. The race fires iff the sweeper reaches the new directory within `W` of its creation:
`P ≈ W / 62 µs / 2383 entries`.

| Window figure | entries covered | P per concurrent pair |
|---|---|---|
| median 0.236 ms | ~4 | **~0.16 %** (≈ 1 in 600) |
| p95 0.546 ms | ~9 | ~0.37 % |
| max 1.482 ms | ~24 | ~1.0 % |

So: **rare, bounded at roughly 1-in-100 to 1-in-600 per overlapping pair, and deterministic once
reached.** The `R2` criterion is "must never", so rarity does not discharge it — and the cost
when it fires is a **failed download**, not a lost credential (`R2-A4`).

**Does it need a second process? Yes.** Verified by reading: `_sweep_stale_cookie_dirs` is
reachable from exactly **one** call site, `_ensure_cookie_lifecycle_started`, which
`_create_cookie_artifact_dir` invokes **before** its own `mkdtemp`. With one thread, a process
therefore always sweeps before it holds any directory — **self-collision is impossible**, refuting
the single-process hypothesis. (`R2`'s own roster note says exactly this and is correct.) The
**threaded** exception is `R2-A5` and is not reachable in today's `src/`.

**Are concurrent processes realistic on the declared platform? Yes, and the finding names the
scenario.** `VAL-602` (verbatim): *"the product has no single-instance lock — nothing in `src/`
prevents a second process from starting while a first is mid-transfer … a batch in one terminal
and a single download in another is enough."* Executed/verified:

- **Batch mode does not fork.** `batch_downloader._run_batch_with_progress` uses
  `asyncio.create_task` + `gather` in **one** process; `_TrackedSemaphore` gates concurrency
  with an `asyncio.Semaphore`. So "many workers in batch mode" does **not** multiply processes.
- **Multiplicity comes from (a) two operator invocations** — two terminals, a batch plus a
  single, or a **Task Scheduler job whose next run overlaps the previous** (very common for a
  downloader with a multi-minute runtime and a short schedule interval) — and **(b) an
  installer/updater relaunching the CLI mid-run**.
- **The product itself raises the collision rate.** It runs the sweep on the *first* artefact
  creation of *every* process, and it creates a new directory **per download**
  (`R1-A3`: `_create_cookie_artifact_dir` allocates a distinct directory per call), so a
  long batch process and a short single-run process overlap in exactly the phase where the
  victim's first artefact appears.
- **The test suite is a third source.** `_sweep_stale_cookie_dirs` is tested against the
  **real** `%TEMP%`, and the two existing sweep tests *create* `vk_cookies__dir*` directories
  there. There is **no** `[tool.pytest.ini_options]`, no `addopts`, and **no `pytest-xdist`**
  in `pyproject.toml`, so the suite is serial today and self-collides only if the sweep tests
  are ever parallelised — or if a developer's IDE runs a second pytest process. Low probability,
  non-zero, and free to fix in the test design (`R2-A12`).

##### `R2-A8` — the two PID-less windows are byte-identical on disk, and nothing distinguishes them

Verified by reading plus executed state table (`R2-A1`).

| | **creation window** (`R2-A1`) | **teardown window** (`R1` `Alt A`, inherited) |
|---|---|---|
| Opens after | `mkdtemp` returns | `(dir / _OWNER_PID_FILENAME).unlink(missing_ok=True)` returns |
| Closes when | `write_text` completes | `cookie_dir.rmdir()` returns |
| Measured width | median 0.236 ms / max 1.482 ms | median 0.120–0.165 ms / max 0.454–0.864 ms |
| On disk while open | **empty directory**, or empty directory + zero-length `owner.pid` | **empty directory** |
| `_read_owner_pid` | `None` | `None` |
| Contents | never credential material | never credential material (`R1-R1`, confirmed: the file is unlinked first in `_download_with_ytdlp`'s `finally:` **and** in `_create_temp_cookie_file`'s write-error path) |
| Cost of a hard kill inside it | **the whole download fails** (`FileNotFoundError`, `R2-A4`) | **one empty directory leaks** and the PID-less rule declines it |

**They are the same bytes on disk. No marker, no name convention, no mtime convention separates
them.** Both are "an empty directory named `vk_cookies__dir<8 chars>`". Consequence for each
candidate rule:

- A rule that says **"PID-less ⇒ never destroy"** protects the **creation** window and, as a
  side effect, **converts `R1`'s one-empty-directory leak into a permanent leak**. It is the
  right trade (destroying a live artefact is worse than retaining an empty directory — the
  brief's own ordering, and `VAL-602`'s), but the cost must be *named*, and `R2-D2` already asks
  whether a PID-less directory is skipped forever or reclaimed under a separately-justified rule.
- A rule that says **"PID-less and younger than T ⇒ skip"** protects the **creation** window
  **and** still reclaims `R1`'s leak once the directory ages past `T` — strictly better on both
  counts, at the price of inventing `T`, which the `R2` block's own criterion forbids.
- A rule that says **"PID-less ⇒ destroy, but only if the directory is empty *and* something
  proves it is not mid-creation"** cannot be implemented from what is on disk. There is no such
  proof available without a marker, a name, or an age.
- **A structural rule (lock, or PID-in-name) makes the question disappear for both windows**,
  because in both cases the authoritative liveness signal is *not* the `owner.pid` file.

##### `R2-A9` — the deferred docstring drift: **two** defects in **one** docstring, not one

Confirmed and scoped. `_sweep_stale_cookie_dirs`'s docstring carries exactly two factual errors,
and a repo-wide grep finds them **nowhere else** in `src/`, `tests/` or `docs/`:

1. *"the product prefix (`vk_cookies_dir`)"* — the composed value is **`vk_cookies__dir`**
   (`_COOKIE_ARTIFACT_PREFIX` + `_ARTEFACT_DIR_SUFFIX`, a doubled underscore; measured by
   `repr`). **Correct the string, or better, delete the literal and name the two constants**
   (`_COOKIE_ARTIFACT_PREFIX` + _ARTEFACT_DIR_SUFFIX`) so the docstring cannot drift again.
   `[DOC-UPDATE]`, trivial effort.
2. *"the concurrency hazard VAL-002 rules out (VAL-602)"* — **`VAL-002` is a different phase's
   finding.** There are three unrelated `VAL-002`s: phase-02 config (orchestrator filenames),
   phase-03 network resilience (`NET-004`/`NET-002`/`NET-010` in one function), and phase-05.
   The cookie finding is **`VAL-602`**. The parenthetical `(VAL-602)` is right; the inline id is
   wrong. Plans 06 and 07 establish an explicit convention that `VAL-` ids **must** be
   phase-qualified ("the highest **process** risk in the plan"), and this docstring violates it.
   **Delete the bare `VAL-002`** — the correct id is already in the same sentence. `[DOC-UPDATE]`,
   trivial effort.

`R1`'s scope put the sweep out of reach and deferred both to `R2`; `R2-A13` inherits them. Scope
is **one docstring, two tokens, one commit hunk** — but it belongs in `R2`'s commit, because
`R2` is the block that rewrites that function's decision rule and a docstring that mis-states
the prefix next to a `startswith(dir_prefix)` filter is the most expensive kind of stale comment.

##### `R2-A10` — risks, per candidate rule direction

**Retention (a sweep that never reclaims).** A rule of the form "PID-less ⇒ never destroy" makes
the residue class **`owner.pid` absent or unreadable** permanently unreclaimable. Measured
today's contributors to that class: `R1`'s teardown-window kill; `R1-A7`'s `rmtree(
ignore_errors=True)` on a locked file, which **deletes `owner.pid` and leaves the directory
plus the credential file** (20/20 in `R1-R1`'s trial); a machine crash between `open` and
`write`; and `R2-A2`'s ACL-denied state. **The worst member of that class is
credential-bearing** (the locked-file case), so "retain forever" is not a harmless default — it
is `SEC-002`'s residue half reappearing under a new name. Any rule `R2` adopts must therefore
state, in the docstring, **what reclaims that class**, or state explicitly that nothing does
and that the operator must. `R2-D2` is exactly this question and must not be answered "skip
forever" without that sentence.

**Destruction (worse than retention).** Two distinct ways `R2` could make this worse:
(i) a grace threshold `T` shorter than the *slowest* creation window — the window is 0.236 ms
median but `R2-A1` measured **1.482 ms max** on an idle machine; under memory/disk pressure a
`mkdtemp` on a cold, large, AV-scanned `%TEMP%` can plausibly take tens of ms, so any `T` below
a few seconds is unjustified on this evidence and any `T` above a few seconds is nearly free;
(ii) a rule keyed on a *directory-empty* test, which is true during the creation window **and**
true in `R1-A7`'s locked-file residue for a different reason, conflating them. Neither is
avoidable if the rule is stated as *"destroy only on a positive demonstration of death"*, which
is the framing recommended in `R2-A6(b)`.

**PID reuse.** Quantified in `R2-A6(a)`: ~4.2 % per process creation, expected reuse of a
specific dead PID in ~24 process creations on this box. Direction: **retains residue**, so it
compounds the retention risk above and never the destruction risk. It is pre-existing,
`R2`-independent, and must not be "fixed" with an age rule.

**`A-2` applies unchanged.** `_is_pid_alive`'s Windows probe is correct and must not be
touched. `R2` may change **what a failed probe is allowed to conclude** (`R2-A6(b)`) but not
**how the probe works**.

**Interaction with `R3`.** `R3` is blocked on §9 Q1 and concerns **legacy bare files**
(`vk_cookies_*.cookies.txt`, no directory). Its own text says the safety argument `R2`
establishes "does not exist for this class". Constraints `R2` imposes on `R3`, and vice versa:

- **`R2` constrains `R3` only through the sweep's structure.** If `R2` changes
  `_sweep_stale_cookie_dirs`'s **signature or return contract**, or splits the classification
  into a helper, `R3`'s "a **new** sweep function rather than a branch inside the existing
  one" becomes cheaper or harder. `R3` should therefore be told which shape `R2` landed.
- **`R2` must not widen the sweep's match set.** A new marker artefact (`Alt B`) must live
  **inside** the directory, or the sweep starts matching something new and `R3`'s "the sweep
  matches only `vk_cookies__dir*` directories" baseline changes.
- **`R2` must not touch `_COOKIE_ARTIFACT_SUFFIX`** — it is `R3`'s key.
- **`R3` does not constrain `R2` at all.** No `R2` alternative needs to match bare files.
- `R3`'s blocked status means `R2` cannot be validated by "the residue class is now empty" —
  the 1295 legacy files stay. `R2`'s `AC-1` evidence must therefore be a **test of the rule**,
  not a residue count. (This is also why the test design in `R2-A12` is (a)+(c), not a
  before/after residue measurement.)

##### `R2-A11` — the four alternatives, characterised against the real code — **not chosen**

Shared facts, all measured or read above, that apply to every row:

- The creation window is **median 0.236 ms / max 1.482 ms** (`R2-A1`, `R2-A7`).
- The teardown window is **median 0.120–0.165 ms / max 0.454–0.864 ms** (`R1-VALIDATION` `A-1`,
  re-measured). The two windows are **byte-identical on disk** and **no marker separates them**
  (`R2-A8`).
- The sweep's filter is a bare `entry.name.startswith(_COOKIE_ARTIFACT_PREFIX +
  _ARTEFACT_DIR_SUFFIX)`; composed value `'vk_cookies__dir'`. **It is not guarded by any test
  or assertion** (`R2-A3`). The three strings `_COOKIE_ARTIFACT_PREFIX`,
  `_ARTEFACT_DIR_SUFFIX` and `_COOKIE_ARTIFACT_SUFFIX` are `R3`'s and `B4`/`B6`'s keys.
- `%TEMP%` here holds 2383 entries; `_sweep_stale_cookie_dirs()` costs **median 148.5 ms**
  (`R2-A3`).

---

**`Alt A` — age grace on a PID-less directory only.**

| | |
|---|---|
| **Changes** | `_sweep_stale_cookie_dirs` gains one extra `stat` per **matching** directory (`st_birthtime`/`st_ctime`) and one comparison. `_read_owner_pid`'s `None` branch becomes "skip if younger than T". |
| **Breaks** | Nothing structural. Introduces **a magic duration** — which is the one thing `R2`'s own criterion forbids and which `VAL-602` explicitly said a fixer "must invent and cannot judge". Also uses an age in the *decision*, which is the shape `VAL-602` rejected — the block's defence is that age-as-**skip** ≠ age-as-**deletion**, and that defence holds only for as long as the rule never reuses T to delete. |
| **Closes `R1`'s teardown window?** **Yes, and uniquely among the non-structural options.** The teardown-window leak is also PID-less, so it ages past T and is then reclaimed. `Alt A` is the only candidate that *improves* on the status `R1` left behind. |
| **New / frozen strings?** **None.** No new artefact; no constant touched; the `startswith` filter is untouched. Zero silent-no-op risk. |
| **Windows cost** | One extra `stat` per matching directory (0 today) — negligible. `Alt A` is the **only** candidate that depends on timestamp quality. Measured: `st_birthtime` exists on this platform (Python 3.12), `st_ctime == st_birthtime` on Windows, writing a file inside bumps `st_mtime` but **not** `st_ctime`, and recorded deltas resolve to ~0.5 ms at zero sleep and track a 1 ms sleep accurately — while `CLOCK_REALTIME` resolution is 0.015625 s. So the timestamp *values* are fine-grained enough, but this is an empirical property of one NTFS volume, not a documented guarantee, and not a property of every filesystem a user might point `TEMP` at. |
| **Judgement** | Cheapest and safest structurally; the whole cost is one unjustified number. **If** a duration is accepted, `R2-A10` bounds it from below: T must exceed the **slowest** creation window, and 1.482 ms was measured on an *idle* machine, so a sub-second T is unjustified. A T of a few seconds costs nothing operationally (worst case: a few empty directories retained for a few seconds) and is two to three orders of magnitude above the measured window. |

---

**`Alt B` — creation marker written into the new directory; "no marker at all" means mid-creation.**

| | |
|---|---|
| **Changes** | `_create_cookie_artifact_dir` writes a second file inside the new directory. `_sweep_stale_cookie_dirs` gains a third case: *marker absent ⇒ skip*. |
| **Breaks** | Nothing existing — but it **manufactures a new, un-reclaimable residue class**. Every PID-less directory that is *not* mid-creation (a hard kill in `R1`'s teardown window, `R1-A7`'s `rmtree`-on-locked-file residue, a crash between `open` and `write`, `R2-A2`'s ACL-denied state) has **no marker either**, so it is indistinguishable from mid-creation and is retained **forever**. That is `SEC-002`'s residue half reappearing under a new name, and its worst member is credential-bearing. `Alt B` therefore needs a **second, separately-justified reclamation rule** for marker-less PID-less directories — which is a duration again, and so re-imports the thing it was meant to avoid. |
| **Closes `R1`'s teardown window?** **No** — it is *indistinguishable* from it, which is worse. |
| **New / frozen strings?** **One new artefact filename** (e.g. `creating`). It must live **inside** the directory; placed in the temp root, or given a name that does not start with `vk_cookies__dir`, the sweep would either match nothing new or start matching something it should not. **The frozen strings must not be touched**, and as long as they are not, the `startswith` filter is safe. `R2-A10` makes "marker inside the directory" an explicit constraint for `R3`. |
| **Windows cost** | Nil beyond the extra file. `mkdtemp` may be kept as-is (write the marker into its result) — no need to replace it with `Path.mkdir`, so POSIX `0o700` semantics are untouched. |
| **Judgement** | The only option that makes the two windows **distinguishable in principle**, and it is what makes "never destroy mid-creation" *provable* rather than inferred. But "no marker ⇒ skip" has failure direction **retain**, and what it retains is the credential-bearing kind unless a second rule is added. It also does not close the window the block is named after — it relabels it. |

---

**`Alt C` — encode the owner PID in the directory name at `mkdtemp` time.**

| | |
|---|---|
| **Changes** | `dir_prefix` becomes PID-bearing; `_read_owner_pid` becomes a name **parser**; `_OWNER_PID_FILENAME` becomes redundant or is removed. **Zero window** — the directory is PID-bearing from the instant `mkdir` returns. |
| **Breaks** | The frozen strings, which is the single worst failure mode available. `R1-R1` ground 4 is explicit: `mkdtemp` uniqueness comes from `mkdir` + `FileExistsError` retry and the prefix is prepended verbatim, so embedding a PID is collision-safe — but **any edit that moves the PID outside the leading run, or changes `_ARTEFACT_DIR_SUFFIX`, turns the sweep into a silent no-op**: no error, no test failure, residue accumulates forever. Nothing guards the filter today (`R2-A3`). It also breaks `R1-R1`'s non-negotiable "preserve the `owner.pid` record", and three existing test functions reference `_OWNER_PID_FILENAME` (`R1-R1` ground 2). It must be chosen **jointly with `R1`**, whose landed `Alt A` already unlinks `owner.pid` before `rmdir` — so the name would become the *only* record, a strict reduction in evidence. |
| **Closes `R1`'s teardown window?** **Yes** — the name survives `owner.pid`'s unlink, so the teardown window closes for free; the only option that closes both with no new state at all. |
| **New / frozen strings?** **Touches frozen strings.** Unacceptable without a guard. If chosen anyway it must ship with a test that a fresh `_create_cookie_artifact_dir()` result **is matched by the sweep's own filter** — the missing assertion from `R2-A3`. |
| **Windows cost** | Parse surface: the `mkdtemp` tail is exactly 8 characters from `[a-z0-9_]`, so the PID must be delimited (`R1-R1`). Trivial cost. |
| **Judgement** | The strongest safety property and the weakest safety *net*. `R1` already rejected it; nothing in `R2`'s measurement reopens that. |

---

**`Alt D` — stdlib cross-process lock around classify and create (`msvcrt.locking` / `fcntl`).**

| | |
|---|---|
| **Changes** | `_create_cookie_artifact_dir` takes an exclusive OS lock, then `mkdtemp` + `write_text` + `set.add`, then releases. `_sweep_stale_cookie_dirs` takes the same lock, **classifies**, releases, and only then purges — the code already has the classify/purge split (`R2-A3` item 6), so no purge ever happens under the lock and the 148 ms scan is never serialised. Zero window. |
| **Breaks** | Nothing existing; `_read_owner_pid` and the rule both stay as they are for directories that *do* carry a record. **The trap, measured:** a second handle in the **same** process locking the same byte raises `PermissionError [Errno 13]` (executed) — so the implementation must cache **one** module-level handle and/or guard re-entry, or the second concurrent artefact creation in one process turns into an exception. This is exactly the intra-process case `R2-A5` opens. |
| **Closes `R1`'s teardown window?** **No, not by itself** — the teardown window is not guarded by a create-side lock. It closes only if the lock is also held around `_remove_cookie_artifact_dir`'s unlink→`rmdir` span: a third acquisition site and a broader change. **Honest answer: partial.** |
| **New / frozen strings?** **One new well-known lock-file name in the temp root** (a fourth artefact string). **No frozen constant is touched**, so the `startswith` filter is safe. The lock file is fixed-name, 1 byte, permanent, carries nothing sensitive — so it needs **no** `.gitignore` rule (`R1-A6`: artefacts live outside the working tree) and is not `R3`'s subject (`R3` keys on `_COOKIE_ARTIFACT_SUFFIX`). |
| **Windows cost** | Measured: `msvcrt.locking(LK_LOCK, 1)` acquire **median 0.0020 ms, max 0.0172 ms**; release **median 0.0017 ms** — about **1 % of the window it closes**. Cross-process exclusion **verified by execution**: a child holding the lock makes the parent's `LK_NBLCK` raise `PermissionError`; after `p.kill()` (`TerminateProcess`) the parent acquires immediately — **the OS releases a dead holder's lock**, so a hard-killed run cannot wedge the next one. POSIX needs `fcntl.flock`, a different API and therefore a second code path to keep in step. |
| **Judgement** | Structurally correct, near-zero measured cost, and the only option whose cost is a *new* string rather than a *changed* one. Its weakness is scope: it closes the creation window, leaves `R1`'s teardown window, and introduces a cross-process synchronisation primitive into a module that has none — the one thing `VAL-602` observed the product lacks entirely. |

**Cross-cutting, verified by execution, applying whichever row is chosen:**

1. **The `startswith` filter needs a guard test regardless.** Nothing today asserts that a freshly created directory is matched by the sweep's filter. `R2` should add that assertion **first**, before any rule change, so a later edit that breaks the filter fails a test instead of silently disabling the sweep. Cheapest high-value item in the block, independent of `R2-D1`.
2. **`Alt C` is the only option that edits frozen strings**; `Alt B` the only one that adds a string the sweep could match. `Alt A` and `Alt D` are string-neutral.
3. **No option makes the sweep cheaper.** The 148 ms median is `entry.is_dir()`; no rule touches it.

##### `R2-A12` — test strategy: **(a) deterministic rule test + (c) a guarded two-process test; not (b) alone**

**Decision: (a) is mandatory and is the primary evidence. (c) is a bounded addition with a
deterministic synchronisation point. A bare (b) is rejected.** Justification:

- The defect is a **concurrency window of median 0.236 ms**. `R2-A7` bounded the real hit rate at
  **~1 in 100 to 1 in 600 per overlapping pair**. A test that runs the sweep and the create
  concurrently and hopes to collide would need thousands of iterations to have even a coin-flip
  chance, and would then be **flaky by construction** — a test that fails 1 run in 600 is worse
  than no test, because it trains the team to re-run red builds. **A test needing real timing to
  be reliable is unacceptable, so the rule test carries the block.**
- **(a) — the classification rule — is exactly what needs pinning, and it is fully
  deterministic.** The rule is a pure function of a directory's on-disk state; construct each
  state with `tempfile.mkdtemp(prefix=_COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX)` and
  assert survival/destruction. Required cases, each its own test, **no sleeps anywhere**:
  1. **PID-less, brand new — survives** (`AC-1`). Empty directory, no `owner.pid`.
  2. **PID-less, explicitly old — the landed rule's behaviour asserted.** If the rule is
     `Alt A`, age the directory **without sleeping** — construct it and set the timestamp
     backwards explicitly, or inject the clock/age the rule reads. **This is the case that
     forbids a `sleep`.**
  3. **Zero-length `owner.pid` — survives.** `R2-A1`'s widest sub-window, and the one `AC-1` as
     currently worded ("no readable `owner.pid`") would otherwise miss.
  4. **Unparseable `owner.pid` — survives.** State 3 of `R2-A2`.
  5. **`owner.pid` is a directory — survives.** State 4 of `R2-A2` (the `A-3` path).
  6. **Dead PID — swept.** Existing `test_sweep_stale_cookie_dirs_removes_dead_owner`, unchanged
     (`AC-2`).
  7. **Live PID (current process) — survives.** Existing
     `test_sweep_stale_cookie_dirs_preserves_live_owner`, unchanged (`AC-2`).
  8. **Torn / digit-prefix PID — behaviour asserted explicitly**, so `R2-A1`'s wrong-`int`
     channel is either closed or documented as accepted (`AC-1` extended).
  9. **The `startswith` filter guard.** Assert that `_create_cookie_artifact_dir()`'s own result
     is matched by the sweep's filter — i.e. the sweep is not a silent no-op. **Write this
     first** (`R2-A11` cross-cutting 1). Nothing pins it today.
- **(c) — the two-process test — is worth having, but only with a deterministic barrier.** Use
  `subprocess` on `sys.executable` with two marker files: the child signals "directory created,
  record not yet written" and then **blocks on the parent's signal file**; the parent runs the
  sweep, then releases the child. Same shape as the probe that proved the defect in `R2-A7`, so it
  **fails against the pre-fix source (discriminating)** and passes after — with no reliance on
  timing. Put it in its own class so it can be skipped where `msvcrt`/`fcntl` is unavailable and
  so a hang cannot stall the rule tests.
- **Isolation, non-negotiable:** every new test must restore `_cookie_lifecycle_started` in a
  `finally:` (the pattern `test_ensure_cookie_lifecycle_started_registers_atexit_once` already
  uses) and clean its own directory in a `finally:`. `R1-A11`'s residue lesson applies — a test
  that leaks residue makes the next run's sweep measurement meaningless. `A-5` is the trap.
- **Do not weaken any `R1` oracle.** `T6` and `T7` are single points of coverage for the lifted
  guard and the `except`-arm ordering (`R1-VALIDATION`) and must pass unchanged.

**Does `test_read_owner_pid_missing_file_returns_none` need to change?**

**The assertion does not; its docstring must.** Verified by reading. The test asserts
`_read_owner_pid(tmp_path) is None` for a directory with no `owner.pid` — a statement about
`_read_owner_pid`, which `R2` should not change at all (its `None` return is still the correct
"no readable record" answer; what changes is what the **sweep** may conclude from it). **So
`R2` must leave the assertion byte-identical.** What `R2` must change is the test's **docstring**,
which currently asserts the *old* policy in prose:

> *"A directory without `owner.pid` is treated as having no recorded owner; the sweep sees `None`
> from this function and **treats the directory as stale, removing it** (SEC-002)."*

That sentence becomes false the moment `R2` lands and would then be a comment that contradicts
the code — the highest-cost kind of stale documentation. Rewrite it to state the new contract:
`_read_owner_pid` returns `None` when there is no readable record, and **the sweep declines to
destroy on `None`** because "cannot determine the owner" is not "the owner is dead". Additionally
recommend: (a) the docstring should not claim `SEC-002` for a behaviour `SEC-002` does not
specify — `VAL-602` is the id; (b) if `R2` adopts `Alt A`, add a **sibling** test for the aged
case rather than overloading this one, so this test stays a pure `_read_owner_pid` unit test.

##### `R2-A13` — what `R2` inherits from `R1`, stated explicitly

Read in full: `R1-AUDIT` (`R1-A1`…`R1-A14`), `R1-RESEARCH` (`R1-R1`…`R1-R6`), `R1-DESIGN`, and
`R1-VALIDATION` (`V-1`, advisories `A-1`…`A-6`). Inherited, not silently:

1. **`R1` chose `Alt A`** — a contents-first, non-recursive `_remove_cookie_artifact_dir`:
   `unlink(owner.pid, missing_ok=True)` then `rmdir()`; `FileNotFoundError` **precedes**
   `except OSError`; a non-`FileNotFoundError` `OSError` from the unlink logs one
   `cookie_file_cleanup_failed` and **returns without attempting `rmdir`**; at most one record
   per call; successful removal is silent. **`R2` must not weaken any of this, and `AC-5`
   requires the commit message to name `Alt A` and say how `R2`'s rule covers its window.**
2. **`_COOKIE_ARTIFACT_DIRS.discard` happens only on a definitive gone-outcome and never on
   failure — CONFIRMED STILL TRUE at `72c8283`.** Verified by reading `_remove_cookie_artifact_dir`:
   `removed` becomes `True` only on `rmdir` returning or on `FileNotFoundError`; the `discard`
   sits inside `with _COOKIE_LIFECYCLE_LOCK:` guarded by `if removed:`; the warning is emitted
   only when `failure is not None`, i.e. never on success. Verified by execution:
   `test_owner_pid_unlink_failure_skips_rmdir_and_records` Part A asserts the directory stays
   tracked after a failed `rmdir`; `TestCookieArtefactLifecycle` is **12 passed** at `72c8283`.
   **`R2` does not touch this function.**
3. **`R1`'s PID-less window is inherited, not pre-empted** — recorded median 0.165 ms / max
   0.864 ms over 200 samples (`A-1`); my independent re-measure median 0.120 ms / max 0.454 ms.
   The credential file is always unlinked first (`_download_with_ytdlp`'s `finally:` **and**
   `_create_temp_cookie_file`'s write-error path), so it can never hold credential material. A hard
   kill inside it leaks **one empty directory** that `R2`'s PID-less rule will decline.
   **`Alt A` and `Alt C` close it; `Alt B` cannot distinguish it; `Alt D` closes it only if the
   lock is extended to `_remove_cookie_artifact_dir`.**
4. **`R1-R3`'s lock discipline is already correct in `_sweep_stale_cookie_dirs`** (snapshot under
   no lock, purge outside the lock, `discard` under the lock) — `R2` must preserve it. It matters
   more under `Alt D`: `_purge_cookie_artifact_dir` can block on a locked file (`R1-A7`), and
   holding `_COOKIE_LIFECYCLE_LOCK` there would stall every other thread's
   `_create_cookie_artifact_dir`.
5. **`A-1` applies** — budget the larger tail; the creation window (`R2-A1`) is in fact the larger
   of the two.
6. **`A-2` applies** — `_is_pid_alive`'s Windows probe is correct and must not be changed
   (`R2-A6`). Its docstring wording is already correct at `72c8283`.
7. **`A-3`, `A-4`, `A-5` are `R1`'s test/doc items.** `R2` should not weaken them and should not
   re-fix them. `A-3` (the undocumented `rmdir`-`OSError` path) matters because `R2-A12` case 5
   relies on that path being reachable.
8. **`V-1` is a commit-body defect only**, recorded and not actionable. `R2` must not repeat it —
   `R2-A5` and `R2-A9` belong in `R2`'s commit body alongside `AC-6`'s citation list.
9. **`T4` is a deliberate non-regression guard, non-discriminating by design** — `R2` must not
   inherit it as a defect or "fix" it.
10. **The doubled-underscore docstring drift is `R2`'s** (`R2-A9`). Scope: **one docstring, two
    tokens** (`vk_cookies_dir` → name the two constants; delete the bare `VAL-002`).
11. **`R1-A5`'s falsified claim is already corrected** in the module comment at `72c8283`
    (verified by reading: it now states neither string is matched by `.gitignore`). `.gitignore`
    stays `targets: conditional` and **untouched** — `R1-A6` settled it by location, and nothing
    in `R2` changes that.
12. **`R1-R6`'s claim that `R2` is not pre-empted is confirmed** — `_create_cookie_artifact_dir`
    still calls `mkdtemp` and only then writes `owner.pid`.

##### `R2-A14` — open questions this audit hands to the Planner

1. **`R2-D1`** — which alternative. Inputs: `R2-A11` (all four characterised), `R2-A8` (the two
   windows are indistinguishable on disk), `R2-A10` (retention can be credential-bearing).
   **No recommendation is made here.**
2. **`R2-D2`** — skipped forever, or reclaimed under a separately-justified rule. `R2-A10` bounds
   it: "skip forever" must be accompanied by a docstring sentence naming who reclaims the class,
   because its worst member holds a credential file (`R1-A7`).
3. **`R2-D3` (new, raised by `R2-A6(b)`)** — does a PID that **cannot be probed** count as dead?
   Measured: `OpenProcess` on live PID 4 (`System`, confirmed by `tasklist`) fails with
   `ERROR_ACCESS_DENIED` and `_is_pid_alive` returns `False`, so an elevated / SYSTEM /
   other-account owner is destroyed while running. **Recommend the Planner frame `R2`'s rule as
   default-deny — "destroy only on a positive demonstration of death" — which answers `R2-D3` for
   free and without touching `_is_pid_alive`.** Out of `R2`'s declared scope as written; needs an
   explicit decision.
4. **Should `_ensure_cookie_lifecycle_started`'s flag be set after the sweep, not before?**
   (`R2-A5`) Latent today; reachable the moment anything calls the download path from a worker
   thread. Trivial change; arguably belongs to a later block rather than `R2`.
5. **Should `atexit.register` precede the sweep?** (`R2-A5`) Latent; no live failure path today.

##### `R2-A15` — edits made by this audit

**Exactly one file was modified: `.ai/plans/17-credentials-secrets-audit-fixes-execution.md`**,
by inserting this `#### R2-AUDIT` subsection (findings `R2-A1`…`R2-A15`) into the `R2` region,
immediately after the `EB-R2` yaml block and before the `### R3` heading. Nothing else.

Verified untouched afterwards: `git status --porcelain` is byte-identical to its pre-audit state
(7 deleted `.ai/plans/00_*`…`07_*` + `VALIDATION_REPORT.md` + `error_ref.md`, `M
.ai/problems/PROBLEM.md`, `M .kilo/commands/implement/implement-plan-multiagent.md`, untracked
plans 05–08, untracked `tmp/`, `tmp_old_sec.md`, `tmp_old_sec2.md`, untracked plan 17).
Specifically: **no production code, no test, no `.gitignore`, no plan 11, neither source file, and
no other audit-phase region was edited.** Nothing staged, nothing committed. Temporary probe
directories created under `%TEMP%` by the measurement scripts were removed; final residue:
**0** artefact directories, **1295** legacy bare files (unchanged, `R3`'s subject).

---

#### R2-DESIGN — implementor task (Planner)

```yaml
id: EB-R2
title: Make the cookie-artefact sweep destroy only on a positive demonstration of death
priority: high
depends_on: [EB-R1]
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.1, §6.4 (T-B2 step 5), §7.2 (R2 row)"
source_blocks: [B2]
description: >-
  VAL-602's creation race: _create_cookie_artifact_dir calls mkdtemp and only then
  writes owner.pid, while _sweep_stale_cookie_dirs classifies owner_pid is None as
  stale, so a concurrent run's directory can be destroyed under it (measured window
  median 0.236 ms / max 1.482 ms; ~1-in-600 per overlapping pair, certain once
  reached). R2-A1..R2-A15 are superseded by this task. The rule is restated as
  default-deny -- destroy only on a positive demonstration of death -- which closes
  the PID-less states, R1's teardown window, and R2-D3 (an unprobeable owner PID
  currently reads as dead) as one rule. Alt A's age grace is adopted as a SKIP
  condition on the PID-less branch only, so the PID-less class is reclaimable instead
  of permanently retained; the threshold is 30 s. No production file is added and no
  frozen constant is touched.
goals:
  - Close the creation race: a directory observed mid-creation must never be destroyed.
  - Close R2-D3: an owner PID that cannot be probed must never be read as dead.
  - Keep the PID-less class reclaimable, and name in the docstring who reclaims what
    the sweep cannot.
  - Correct both factual defects in _sweep_stale_cookie_dirs's docstring.
  - Pin the sweep's startswith filter, which no test guards today (R2-A3).
files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: modify
    semantic_anchors:
      - _sweep_stale_cookie_dirs
      - _is_pid_alive
      - _read_owner_pid
      - _create_cookie_artifact_dir
      - _COOKIE_ARTIFACT_PREFIX
      - _ARTEFACT_DIR_SUFFIX
      - _OWNER_PID_FILENAME
  - path: tests/test_hls_downloader.py
    targets: modify
    semantic_anchors:
      - TestCookieArtefactLifecycle
      - test_read_owner_pid_missing_file_returns_none
      - test_sweep_stale_cookie_dirs_removes_dead_owner
      - test_sweep_stale_cookie_dirs_preserves_live_owner
  - path: .ai/plans/11-credentials-secrets-audit-fixes.md
    targets: read_only
    semantic_anchors:
      - "§5 residue estimate, §6 remediation phases"
  - path: .gitignore
    targets: conditional
    semantic_anchors:
      - "*_cookies.txt"
    reason_if_triggered: >-
      Not expected. R2 introduces no new artefact in the temp root and no new file in
      the tree; .gitignore stays targets: conditional and untouched (R1-A6).
changes:
  - action: add
    target: _COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS
    where: module scope, immediately after _OWNER_PID_FILENAME
    type: new_module_constant
    description: >-
      A float duration, 30.0, with a comment carrying the measured justification
      (median 0.236 ms / p95 0.546 ms / max 1.482 ms on an IDLE machine; >2e4x the
      measured maximum; ~1.9e3x the measured CLOCK_REALTIME resolution of
      0.015625 s). Never a frozen string; not a key for R3, B4 or B6.
  - action: add
    target: _OwnerLiveness
    where: module scope, immediately after _is_pid_alive
    type: new_module_private_strenum
    description: >-
      A StrEnum with exactly three members -- LIVE, DEAD, UNPROBEABLE -- following
      the existing _PlaylistType / _SegmentFanoutOutcome precedent (leading
      underscore, module-private). This is the fixed value set of the sweep's
      decision, so house rule 10 applies.
  - action: add
    target: _is_pid_probe_conclusive
    where: immediately after _is_pid_alive, before _read_owner_pid
    type: new_function
    description: >-
      pid -> bool. Closes R2-D3 WITHOUT touching _is_pid_alive. Returns True when
      _is_pid_alive's False for that pid was a positive demonstration of
      non-existence, False when the probe was inconclusive. Non-Windows: returns
      True unconditionally, because _is_pid_alive already maps PermissionError to
      alive on POSIX. Windows: re-issues OpenProcess(PROCESS_QUERY_INFORMATION)
      and treats ERROR_INVALID_PARAMETER (87) as conclusive; any other failure,
      including ERROR_ACCESS_DENIED (5), is inconclusive.
    traps:
      - >-
        It MUST load the DLL as ctypes.WinDLL("kernel32", use_last_error=True) and
        read ctypes.get_last_error(). Reusing ctypes.windll.kernel32 does not arm the
        last-error slot on Windows and can report a stale code, which would make a
        denied owner look conclusively dead and re-open the hazard. This is the trap
        the Auditor's own measurement used WinDLL for.
      - >-
        When the handle is non-zero it MUST be closed with CloseHandle. Leaving it
        open leaks a handle per stale-looking directory.
      - >-
        This is not an ACL reader and adds no dependency (D-2 stands): it inspects
        only GetLastError after a process-handle open the module already performs.
        It touches no ctypes name pywin32 would own.
  - action: add
    target: _cookie_artifact_dir_age_seconds
    where: immediately before _sweep_stale_cookie_dirs
    type: new_function
    description: >-
      cookie_dir -> float | None. Seconds since the directory was created, or None
      when the age cannot be established. Reads st_birthtime where the platform
      provides it and falls back to st_ctime otherwise (on Windows st_ctime IS the
      creation time; on POSIX it is the inode-change time, which for a fresh
      directory is the creation time). Returns None on OSError so an unstattable
      directory degrades to retain. max(0.0, time.time() - created_at) so a clock
      that steps backwards cannot produce a negative age. Uses time.time(), NOT
      time.monotonic(): the value is compared against a filesystem timestamp
      produced by another process, so only the wall clock is comparable. Adding
      `import time` to the module imports is part of this change.
  - action: modify
    target: _sweep_stale_cookie_dirs
    type: decision_rule
    description: >-
      Replace `if owner_pid is None or not _is_pid_alive(owner_pid)` with the
      default-deny decision, per matching directory, keeping the existing structure
      byte-for-byte around it:
        (1) _read_owner_pid returns an int -> _is_pid_probe_conclusive(pid) and
            _is_pid_alive(pid) together: alive -> retain; not alive and conclusive
            -> stale; not alive and inconclusive -> retain.
        (2) _read_owner_pid returns None -> stale only when
            _cookie_artifact_dir_age_seconds(entry) is not None AND is >=
            _COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS; age None (unknown) -> retain.
      Branch (1) must call _is_pid_alive exactly once per directory; branch (2) must
      not call it at all. The grace is a SKIP condition on the PID-less branch ONLY
      and must never appear in the criterion for a directory that carries a readable
      record -- that is what keeps plan 17 §6.3 (no age heuristic in the deletion
      criterion) satisfied and keeps AC-2 green.
    rationale: >-
      R2-A11: default-deny closes the creation window, R2-A2 states 1-5 and R2-D3
      with one rule instead of four special cases, and is robust against both a
      too-short threshold and an emptiness-keyed rule (R2-A10).
  - action: modify
    target: _sweep_stale_cookie_dirs
    type: docstring
    description: >-
      Rewrite. Must (a) state the rule as default-deny, (b) name the two constants
      _COOKIE_ARTIFACT_PREFIX and _ARTEFACT_DIR_SUFFIX instead of the literal
      "vk_cookies_dir" -- the composed value is vk_cookies__dir, a doubled
      underscore, so the literal is wrong (R2-A9 defect 1), (c) delete the bare
      cross-phase "VAL-002" and keep only VAL-602 (R2-A9 defect 2), (d) say that an
      unreadable owner.pid is NOT reclaimed automatically and name who reclaims it,
      (e) say that an owner PID this user cannot probe is retained unconditionally
      and is not this process's to reclaim, and (f) say that the age grace applies
      only to the PID-less branch, never to a directory carrying a readable record.
  - action: docstring_only
    target: _read_owner_pid
    description: >-
      One added sentence: None means "no readable record", not "the owner is dead";
      what the sweep may conclude from None is _sweep_stale_cookie_dirs's business.
      No behavioural change -- its return value and its except clause are untouched.
  - action: comment_only
    target: _create_cookie_artifact_dir
    description: >-
      Add a comment recording that the directory is observable without its PID record
      between mkdtemp returning and write_text completing, and that the sweep's
      PID-less grace is what covers that window (VAL-602). NO behavioural change:
      mkdtemp stays, the write stays where it is, the lock and set.add stay, and
      the 0o700 POSIX semantics of mkdtemp are untouched.
  - action: none
    target: _is_pid_alive
    description: >-
      Byte-identical. R1-A2, plan 17 §6.1 and AC-4 forbid touching it. It stays in
      production use: _sweep_stale_cookie_dirs still calls it, via branch (1).
  - action: none
    target: _purge_cookie_artifact_dir
    description: Byte-identical.
  - action: none
    target: _cleanup_cookie_artifact_dirs
    description: >-
      No change required. Confirmed at 72c8283: R2's decision lives entirely in
      classification, and _cleanup_cookie_artifact_dirs purges only this process's
      own tracked directories.
  - action: modify
    target: tests/test_hls_downloader.py
    type: docstring_only
    description: >-
      test_read_owner_pid_missing_file_returns_none: the ASSERTION stays
      byte-identical (`assert _read_owner_pid(tmp_path) is None`). Only the docstring
      changes -- it currently states the old policy in prose ("the sweep sees None
      from this function and treats the directory as stale, removing it (SEC-002)"),
      which becomes false. Rewrite it to say _read_owner_pid returns None when
      there is no readable record and the sweep DECLINES TO DESTROY on None,
      because "cannot determine the owner" is not "the owner is dead". Drop the
      SEC-002 attribution; the relevant id is VAL-602.
  - action: add
    target: tests/test_hls_downloader.py
    type: new_tests
    description: >-
      Eleven rule tests in TestCookieArtefactLifecycle plus one real-helper test,
      and one new test class for the two-process test. See required_tests.
out_of_scope:
  - _is_pid_alive's implementation, including its Windows probe and its docstring.
  - _purge_cookie_artifact_dir, _remove_cookie_artifact_dir and _COOKIE_ARTIFACT_DIRS.
  - _ensure_cookie_lifecycle_started's flag ordering (R2-A14 items 4 and 5 -- latent, not in R2).
  - The ~1295 legacy bare vk_cookies_* files (R3, blocked on §9 Q1).
  - _COOKIE_ARTIFACT_SUFFIX, _COOKIE_ARTIFACT_PREFIX, _ARTEFACT_DIR_SUFFIX, _OWNER_PID_FILENAME.
  - tests/test_packaging.py -- no new file is added, so its frozenset needs no edit.
  - .gitignore.
  - Any file under .ai/audit/99-validation/.
implementation_sequence:
  - step: 1
    change: required_tests[0] -- the startswith filter guard
    note: >-
      FIRST, before any rule change (R2-A11 cross-cutting 1). Green immediately
      against 72c8283; converts the worst failure mode from silent to red.
  - step: 2
    change: changes[1], changes[2], changes[3], changes[4] -- _OwnerLiveness, _is_pid_probe_conclusive, _cookie_artifact_dir_age_seconds, the grace constant
    note: >-
      New symbols only; nothing calls them yet. Suite stays green.
  - step: 3
    change: changes[5] -- the decision rule in _sweep_stale_cookie_dirs
    note: >-
      Two dead-PID tests (AC-2) must still pass here; the PID-less tests go red
      only if a rule test is wrong. Green.
  - step: 4
    change: changes[6], changes[7], changes[8] -- the two docstrings and the create-path comment
    note: No behaviour. Green.
  - step: 5
    change: required_tests[1..11] -- the rule tests
    note: >-
      Add these BEFORE or WITH step 3, whichever the Implementor prefers, but they
      must all pass in the same commit as the rule. Commit red is not a state to
      be left in at any commit boundary.
  - step: 6
    change: required_tests[12] -- the two-process test
    note: >-
      Verify it FAILS against pre-fix source by stashing the production change
      only (`git stash push src/vkdownloader/services/ytdlp_downloader.py`) and
      observing the single discriminating assertion, then restore. Never commit
      that state.
constraints:
  - Default-deny: destroy only on a positive demonstration of death.
  - No new dependency: psutil, pywin32/win32security, portalocker and polars stay absent.
  - No new file.
  - _COOKIE_ARTIFACT_SUFFIX, _COOKIE_ARTIFACT_PREFIX, _ARTEFACT_DIR_SUFFIX and
    _OWNER_PID_FILENAME are unchanged, and the PID is never moved out of the
    sweep's leading startswith run.
  - Any marker artefact must live inside the directory. (R2 adds none.)
  - _purge_cookie_artifact_dir and _is_pid_alive stay byte-identical.
  - The classify/purge split and the snapshot-then-purge-outside-the-lock discipline
    stay exactly as they are: the scan and the _COOKIE_ARTIFACT_DIRS.discard remain
    outside _COOKIE_LIFECYCLE_LOCK, and the discard remains inside it.
  - _sweep_stale_cookie_dirs keeps its signature (-> None) and its return contract.
  - Classification is NOT split into a helper. The decision stays inline in
    _sweep_stale_cookie_dirs, because R2's block forbids widening the sweep's
    match set or branching a second rule into it while R3 is blocked. The two new
    helpers are pure leaves (probe conclusiveness, age lookup) and neither touches
    the filter or the match set.
  - The sweep's match set does not widen: still only directories whose name
    startswith _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX.
  - The os.scandir/iterdir streaming behaviour and the early `return` on OSError
    are unchanged.
  - R1's teardown contract is preserved verbatim: unlink then rmdir,
    except FileNotFoundError before except OSError, no rmdir after a failed
    unlink, _COOKIE_ARTIFACT_DIRS discarded only on a definitive gone-outcome.
  - structlog only, no print(), no Any, English only, strict typing clean.
  - Do not weaken T6 or T7, and do not weaken any R1 oracle.
required_tests:
  - id: T1
    name: test_created_cookie_dir_matches_the_sweep_filter
    where: TestCookieArtefactLifecycle
    why: >-
      The R2-A3 silent-no-op guard. Assert that _create_cookie_artifact_dir()'s
      result name startswith _COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX --
      i.e. the sweep's own filter expression would match it. Written FIRST.
      No sleep, no timing.
  - id: T2
    name: test_pidless_new_dir_survives_sweep
    why: >-
      AC-1. A directory built with
      Path(tempfile.mkdtemp(prefix=_COOKIE_ARTIFACT_PREFIX + _ARTEFACT_DIR_SUFFIX))
      with no owner.pid survives _sweep_stale_cookie_dirs(). This is the creation
      race's on-disk shape.
  - id: T3
    name: test_pidless_dir_aged_past_grace_is_swept
    why: >-
      The reclamation half. Deterministic ageing by MONKEYPATCHING
      _cookie_artifact_dir_age_seconds to return
      _COOKIE_ARTIFACT_PIDLESS_GRACE_SECONDS + 1. Do NOT use os.utime: the
      platform split matters. On Windows, os.utime moves only st_mtime and
      leaves st_birthtime (and therefore st_ctime, equal to it) untouched, so
      a birth-time rule cannot be aged from a test on Windows at all. On POSIX,
      os.stat_result exposes no st_birthtime (the helper falls back to st_ctime)
      and os.utime DOES move st_ctime because POSIX st_ctime is inode-change
      time -- so a birth-time rule is unusable there too, but for a different
      reason. The clock seam is the only portable deterministic route on both.
  - id: T4
    name: test_pidless_dir_with_unknown_age_survives_sweep
    why: >-
      The default-deny third state. _cookie_artifact_dir_age_seconds patched to
      return None: the directory is retained. Pins "cannot establish the age" ->
      retain, which is what makes the rule safe on a filesystem with unusable
      timestamps.
  - id: T5
    name: test_zero_length_owner_pid_survives_sweep
    why: >-
      R2-A1's widest sub-window (open() creates the file before any byte lands).
      owner.pid written as "" -> _read_owner_pid returns None -> retained because
      it is inside the grace.
  - id: T6
    name: test_unparseable_owner_pid_survives_sweep
    why: R2-A2 state 3. owner.pid containing a NUL suffix or non-numeric text.
  - id: T7
    name: test_owner_pid_is_a_directory_survives_sweep
    why: >-
      R2-A2 state 4, the IsADirectoryError path in _read_owner_pid. Also proves
      that path stays reachable (R1-A3, inherited advisory A-3).
  - id: T8
    name: test_torn_digit_prefix_owner_pid_behaviour_is_explicit
    why: >-
      R2-A1's wrong-int channel: owner.pid containing "14" of "14920" makes
      _read_owner_pid return 14. The test asserts the ACTUAL, documented outcome
      -- 14 is not the current pid, so the probe reports not-alive; whether the
      sweep then reclaims depends on conclusiveness, and for an arbitrary
      unprivileged pid that is conclusive. Assert the outcome explicitly so the
      behaviour is pinned rather than incidental, and name in the docstring that
      this channel yields a plausible-but-wrong PID.
  - id: T9
    name: test_sweep_stale_cookie_dirs_removes_dead_owner
    change: unchanged
    why: AC-2, case 6. MUST still pass byte-identical.
  - id: T10
    name: test_sweep_stale_cookie_dirs_preserves_live_owner
    change: unchanged
    why: AC-2, case 7. MUST still pass byte-identical.
  - id: T11
    name: test_cookie_artifact_dir_age_seconds_reports_a_fresh_directory_as_fresh
    why: >-
      Real-helper smoke test with NO monkeypatching: a just-created directory
      reports an age well below the grace and not None. Without it the clock seam
      could be hiding a broken helper.
  - id: T12
    name: test_cookie_artifact_dir_age_seconds_returns_none_when_unstattable
    why: >-
      A path that cannot be stat'd yields None, not an exception. Keeps the helper's
      OSError handling pinned without needing permissions gymnastics.
  - id: T13
    name: TestCookieArtefactCreationRaceAcrossProcesses
    kind: new_test_class
    where: its own class, after TestCookieArtefactLifecycle
    why: >-
      The discriminating end-to-end proof (R2-A12 (c)). Uses subprocess on
      sys.executable, matching the existing TestProcessBoundaryDescendant idiom,
      with a two-marker-file barrier and NO reliance on timing.
    design:
      - >-
        The child is a -c script that monkeypatches pathlib.Path.write_text in the
        ytdlp_downloader module's namespace so that the call for a path named
        owner.pid (1) writes the parent's "created" marker file, (2) busy-waits on
        the parent's "release" marker file with a bounded timeout, then (3) delegates
        to the real Path.write_text. It then calls _create_cookie_artifact_dir(),
        prints the resulting directory path on stdout, and exits 0.
      - >-
        The parent starts the child with subprocess.Popen, then polls for the
        "created" marker with a generous bounded timeout (30 s) and fails loudly if
        it never appears. It asserts the child's directory exists and owner.pid does
        NOT yet exist, then calls _sweep_stale_cookie_dirs(), then makes the SINGLE
        DISCRIMINATING ASSERTION: the child's directory still exists. Against
        pre-fix source the sweep purges it and this assertion fails; there is no
        timing dependency, because the child is parked between mkdtemp and write_text
        for the whole sweep.
      - >-
        The parent then writes the "release" marker, waits for the child with a
        bounded timeout, and asserts the child exited 0 and that owner.pid now
        holds a valid PID -- i.e. the victim completed its create.
      - >-
        finally: ALWAYS write the release marker (so a mid-test assertion cannot
        park the child forever), kill the child if it is still running, restore
        _cookie_lifecycle_started to its original value, and rmtree the child's
        directory with ignore_errors=True. R1-A11's residue lesson and A-5's trap.
      - >-
        No sleep for synchronisation. Poll intervals are for readiness only, and
        every wait is bounded.
    skip_policy: >-
      No platform skip. The test uses only pathlib and subprocess and must RUN on
      Windows; add no skipif that could hide it. Its own class keeps a hang from
      stalling the rule tests (R2-A12).
gates:
  - uv run pytest -q -rs --maxfail=1 --deselect tests/test_hls_downloader.py::TestParallelSegmentsDownload::test_interrupted_segment_resume_retries_with_fresh_range
  - uv run pytest -q -rs
  - >-
    Assert total skips <= 6: three D-11 skips plus three pre-existing phase-05
    killpg skips. The D-11 floor stays 3. R2 adds NO skip, so the count must be
    exactly 6 -- any other number means something was skipped or unskipped by
    accident.
  - uv run mypy src
  - uv run ruff check src tests
  - uv run ruff format --check src tests
  - "uv run mypy src tests  # delta gate only, exit code meaningless (plan 17 §6.14); error count must not rise above 93"
  - uv run pytest tests/test_packaging.py -q
  - >-
    The new rule tests and the two-process test ACTUALLY RUN on Windows: assert
    from the -rs report that TestCookieArtefactCreationRaceAcrossProcesses is not
    among the skips.
  - git status --porcelain
staging:
  paths_only: true
  paths:
    - src/vkdownloader/services/ytdlp_downloader.py
    - tests/test_hls_downloader.py
  prohibited:
    - git add -A
    - "git add ."
    - git add -u
    - git reset
    - git checkout
    - git commit --amend
    - git push --force
commit_message_must_record:
  - Alt A is adopted, as a SKIP condition on the PID-less branch only, and why the
    deletion criterion stays age-free (plan 17 §6.3).
  - The threshold's derivation: median 0.236 ms / p95 0.546 ms / max 1.482 ms
    measured on an idle machine, and why 30 s is two to three orders of magnitude
    above any defensible loaded-machine bound.
  - That the rule is default-deny, and that this is what closes R2-D3.
  - That _is_pid_alive is unmodified and is still the liveness oracle.
  - VAL-602, and SEC-002 where the rule bears on it.
  - R2-A5 (needs a second process) and R2-A9 (the two docstring defects), alongside
    AC-6's citation list. This discharges R1-VALIDATION V-1 rather than repeating it.
  - That R1's Alt A teardown window is closed by the same grace.
  - That the PID-less class's reclamation is age-based and that the unprobeable-owner
    class is deliberately NOT reclaimed automatically.
  - That no legacy bare-file residue was touched and R3 remains blocked on §9 Q1.
acceptance_criteria:
  - id: AC-1
    criterion: >-
      A PID-less directory survives the sweep while it is inside the grace window,
      and is reclaimed once it is provably older than it. Both directions are
      pinned by deterministic tests with no sleeps.
    verified_by: new test
  - id: AC-2
    criterion: >-
      A directory whose recorded owner PID is probed and conclusively not alive is
      still reclaimed; one owned by the live current process is still preserved.
      Both existing tests pass unchanged.
    verified_by: test
  - id: AC-3
    criterion: >-
      An owner PID this user cannot probe (access denied) is retained, not reclaimed,
      and _is_pid_alive is byte-identical to 72c8283.
    verified_by: new test + git diff
  - id: AC-4
    criterion: >-
      The sweep's own startswith filter provably matches a freshly created artefact
      directory, pinned by a test that does not depend on any rule change.
    verified_by: new test
  - id: AC-5
    criterion: >-
      The commit message records Alt A, the threshold and its derivation, the
      default-deny framing, the R1 teardown-window coverage, and both docstring
      defects.
    verified_by: git log -1
  - id: AC-6
    criterion: >-
      _sweep_stale_cookie_dirs's docstring names _COOKIE_ARTIFACT_PREFIX and
      _ARTEFACT_DIR_SUFFIX instead of the literal, contains no bare VAL-002, names
      who reclaims the PID-less and unprobeable-owner classes, and states that the
      grace never applies to a directory carrying a readable record.
    verified_by: review
  - id: AC-7
    criterion: >-
      The two-process test fails against pre-fix source and passes after, with no
      timing dependence, and leaves no residue and no leaked child.
    verified_by: new test + stash round-trip
  - id: AC-8
    criterion: >-
      Nothing is added to the frozen-string list, no new file exists, .gitignore is
      untouched, and _sweep_stale_cookie_dirs's signature and match set are
      unchanged.
    verified_by: git diff
  - id: AC-9
    criterion: >-
      test_read_owner_pid_missing_file_returns_none keeps its assertion
      byte-identical; only its docstring changed, and it no longer claims SEC-002.
    verified_by: git diff
  - id: AC-10
    criterion: Gates, all as listed.
    verified_by: command output
```

---

### `R3` — Legacy bare-file residue in the shared temp root (`SEC-002`) — **CONDITIONAL**

**Do not start this block** until §9 Q1 is answered by the Product Owner.

**Goal.** The landed sweep matches only `vk_cookies__dir*` **directories**. Measured: **1294
legacy bare `vk_cookies_*.cookies.txt` files sit in the shared temp root**, plus 3
directories from today's suite run containing only `owner.pid`. A freshly created bare file
was verified to survive `_sweep_stale_cookie_dirs()`. Those 1294 files are the actual
`SEC-002` accumulation and they contain credential material, written by versions before the
per-run directory existed.

**Findings carried.** `SEC-002` (the residue half, still open).

**Exact semantic scope, if authorised.**

1. `services/ytdlp_downloader.py::_sweep_stale_cookie_dirs` — an additional, **separately
   justified** reclamation rule for legacy bare files. It must be distinguishable from the
   liveness-gated directory rule by name and by docstring, because the safety argument is
   different in each case: a directory carries a liveness record and a bare file does not.
2. A **new** sweep function rather than a branch inside the existing one, so the two rules
   are separately testable and separately reviewable.
3. `tests/test_hls_downloader.py` — tests for the new rule, including the negative case the
   owner is most likely to care about: that a **concurrently running instance's live bare
   file is not deleted**.

**Alternatives — no choice is made here, and the choice is the owner's.**

- **`Alt A` — reclaim every matching bare file older than a stated threshold.** Simple, and
  it re-introduces exactly the guessed-duration problem `VAL-602` rejected, on the class
  where the safety argument is weakest.
- **`Alt B` — reclaim only files older than the age at which no plausible run can still hold
  one.** Same shape as `Alt A`, better-justified bound; still a duration.
- **`Alt C` — do not reclaim; document the residue and leave it to the operator.** Zero
  risk, and `SEC-002` stays open on its residue half.
- **`Alt D` — reclaim only on an explicit operator action** (a documented manual command or
  a documented cleanup instruction), never automatically at start-up.

**Criterion for choosing (product, not technical):** whether the product may delete files
outside its own run scope, in a directory shared with every other process on the machine,
that may belong to a concurrently running instance. A bare file carries **no PID record**,
so there is no liveness signal to gate on — the entire safety argument `R2` establishes
does not exist for this class. That is why this is §9 Q1 and not an implementation choice.

**Acceptance criteria (if authorised).**

| # | Criterion | Verified by |
|---|---|---|
| 1 | The new rule is separately named and separately documented from the directory sweep. | review |
| 2 | The concurrent-instance negative case is tested. | new test |
| 3 | No duration is invented without a stated reason. | commit message |
| 4 | **Gates:** as `R1`. | §7 |

**Required agent roster** (if authorised): `Auditor` **yes** (the residue must be counted and
characterised before any deletion rule is designed); `Researcher` **yes** (temp-directory
hygiene conventions across platforms — what is considered safe to reclaim from a shared root);
`Planner` **yes**; `Validator` **yes** (a rule that deletes files it does not own is the
highest-consequence block in this plan); `Implementor` **yes**.

**Commit shape.** `fix(cookies): reclaim legacy bare cookie artefacts from the shared temp root`
— subject to §9 Q1. If the answer is `Alt C` or `Alt D`, this block becomes a
documentation-only block and its commit is `docs(cookies): record the legacy bare-artefact
residue and the operator's options`.

```yaml
id: EB-R3
title: Reclaim legacy bare cookie artefacts from the shared temp root
priority: high
depends_on: [EB-R2]
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.2, §6.4 (T-B2 step 4)"
source_blocks: [B2]
status: blocked_on_product_decision
description: >-
  CONDITIONAL on §9 Q1. The landed sweep matches only vk_cookies__dir* directories.
  Measured: 1294 legacy bare vk_cookies_*.cookies.txt files sit in the shared temp root
  and contain credential material; a freshly created bare file survives the sweep. They
  are the actual SEC-002 accumulation. A bare file carries no PID record, so the liveness
  gate that makes directory reclamation safe has no counterpart here, and a concurrently
  running instance's live file is indistinguishable from residue.
goals:
  - Close the SEC-002 residue half, or record formally that it stays open.
  - Never delete a bare file belonging to a concurrently running instance, if a rule is authorised.
files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: modify
    semantic_anchors:
      - _sweep_stale_cookie_dirs
      - _COOKIE_ARTIFACT_PREFIX
      - _COOKIE_ARTIFACT_SUFFIX
  - path: tests/test_hls_downloader.py
    targets: modify
    semantic_anchors:
      - the sweep lifecycle tests
  - path: docs/
    targets: conditional
    semantic_anchors:
      - the operator-facing cookie-artefact documentation
changes:
  - what: Add a separately named reclamation rule for legacy bare files, if authorised.
    why: >-
      1294 credential-bearing files accumulate in the shared temp root and the landed sweep
      structurally cannot match them.
    alternatives_considered:
      - "Alt A: age threshold on every matching bare file."
      - "Alt B: age threshold beyond any plausible run."
      - "Alt C: do not reclaim; document the residue."
      - "Alt D: reclaim only on an explicit operator action."
    blocked_by: [product_decision_Q1]
acceptance_criteria:
  - id: AC-1
    criterion: The bare-file rule is separately named and documented from the directory sweep.
    verified_by: review
  - id: AC-2
    criterion: The concurrent-instance negative case is tested.
    verified_by: new test
  - id: AC-3
    criterion: No duration is introduced without a stated reason.
    verified_by: git log -1
```

---

### `B3` — Convert the three surviving oracles (`SEC-003`)

**Goal.** Turn three D-11-guarded oracles into oracles that execute on Windows, or justify
every remaining guard per-oracle in the commit message. **The argfile clause is struck**
(§2.6) and the `SEC-003:` comment needs no correction — it is already correct. **`B3`'s
remaining scope is test-only.**

**Findings carried.** `SEC-003`; `R1`'s delivered artefact-directory semantics.

**Exact semantic scope.**

1. `tests/test_config.py` — two oracles: `test_log_file_created_with_owner_only_permissions`
   and `test_existing_log_file_permissions_updated`. `D-4` applies to both.
2. `tests/test_hls_downloader.py::TestCreateTempCookieFile` — the credential-artefact
   oracle. Convert it to assert what `R1` delivers: the artefact's parent is the per-run
   private directory **this process created**, and that directory is **removable**. The
   POSIX mode assertion may be **kept as an additional** check — additive, never a
   replacement that loses coverage. The docstring states what is asserted on which platform.
3. Resolve `D-4` for the two log-file oracles.
4. **No production file is written.** The `SEC-003:` comment above `setup_logging`'s
   log-file branch is already accurate: `touch(mode=…)` ignores the mode on Windows,
   `chmod` toggles only the read-only attribute, "no access control list is applied", `D-11`
   is named. Do not touch `config.py`.

**`D-4` — genuine uncertainty. No choice is made here.**

- **`Alt A`** — assert the requested mode. Minimal, honest, weakly meaningful on Windows.
- **`Alt B`** — assert the read-only attribute is **clear**. A real Windows-meaningful
  assertion, which the `0o444` positive control proves the platform can report.
- **`Alt C` — PROHIBITED.** Reading the DACL needs a dependency §1.3.4 forbids
  (`pywin32` is absent and stays absent).

**Criterion:** `B` preferred where both are satisfiable, `A` as the minimal fallback.
**Neither `A` nor `B` may assert owner-only confinement on Windows.** If both are
unsatisfying, the honest outcome is the POSIX gate plus a Windows-side test that pins the
branch and the request, with a docstring that says plainly what is and is not guaranteed.

**Open decisions.** `B3-D1` — `D-4`'s alternative. `B3-D2` — if all three oracles stay
gated, the block is reported **not-landed**; that is a permitted and honest outcome and
must be stated as such rather than papered over with a count.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | A **named conversion**, not a count delta: the commit names every oracle converted, every oracle left gated **and why**, and the resulting skip count. | commit message |
| 2 | No surviving oracle claims owner-only confinement on Windows. | review |
| 3 | The D-11-guarded count is 0, or every remaining guard is justified per-oracle. | commit message |
| 4 | The artefact oracle asserts **removability**, the property `R1` delivers. | new test |
| 5 | The artifact's docstring states what is asserted on which platform. | review |
| 6 | **No production file is modified.** | `git status` |
| 7 | **Gates:** full suite green · `ruff check src tests` clean · `ruff format --check src tests` **green** · `mypy src` clean · `mypy src tests` ≤ 93 · **total skips ≤ 6**, with the three non-D-11 phase-05 skips named as pre-existing and unrelated. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | `D-4`'s satisfiability is platform behaviour, and whether `Alt B` can assert anything meaningful must be established against the live `setup_logging` and the `0o444` positive control, not assumed. |
| `Researcher` | **conditional — only if `D-4` reaches `Alt B`** | Then the question becomes external: what a Windows read-only-attribute assertion can and cannot prove about ACLs. Not required if `Alt A` is chosen. |
| `Planner` | **yes** | Three oracles with different subjects, one of which must not be converted into a weaker assertion than it replaces. |
| `Validator` | **yes** | The central risk here is a **quietly weakened oracle** — a green test that asserts less than the one it replaced. Only independent review catches that. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `test(logging): give the permission oracles an assertion Windows can execute`

```yaml
id: EB-B3
title: Convert the three surviving permission oracles into Windows-executable assertions
priority: medium
depends_on: [EB-R1]
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.3, §6.5 (T-B3), §7.1 (B3 row)"
source_blocks: [B3]
description: >-
  Three oracles are guarded by skipif(D-11) and assert nothing on Windows. This block
  converts them, or justifies every remaining guard per-oracle in the commit message.
  The argfile clause of the original criterion is struck: argfile has zero occurrences in
  src/, the SEC-003 comment never mentioned one, and the comment is already correct.
  No production file is written.
goals:
  - Every surviving oracle either executes on Windows or is justified per-oracle.
  - The artefact oracle asserts the property R1 delivers: parent is this process's private
    directory and that directory is removable.
  - No oracle claims owner-only confinement on Windows.
files:
  - path: tests/test_config.py
    targets: modify
    semantic_anchors:
      - test_log_file_created_with_owner_only_permissions
      - test_existing_log_file_permissions_updated
  - path: tests/test_hls_downloader.py
    targets: modify
    semantic_anchors:
      - TestCreateTempCookieFile
      - test_file_permissions_are_0600
changes:
  - what: Resolve D-4 for both log-file oracles and convert or justify each.
    why: >-
      D-11 leaves the log-file confinement claim with no executable oracle at all.
    alternatives_considered:
      - "Alt A: assert the requested mode (minimal, weakly meaningful on Windows)."
      - "Alt B: assert the read-only attribute is clear (Windows-meaningful; proven reportable)."
      - "Alt C: read the DACL - PROHIBITED, needs a forbidden dependency."
    blocked_by: []
  - what: Convert the artefact oracle to assert removability, keeping the POSIX mode check additively.
    why: >-
      The oracle must assert what R1 delivers, not what the mode bit claims.
    alternatives_considered: []
    blocked_by: []
  - what: Do not modify config.py; the SEC-003 comment is already correct.
    why: >-
      The argfile obligation is phantom and the comment no longer implies a confinement
      Windows does not deliver.
    alternatives_considered: []
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: The commit names every oracle converted, every one left gated with its reason, and the skip count.
    verified_by: git log -1
  - id: AC-2
    criterion: No surviving oracle claims owner-only confinement on Windows.
    verified_by: review
  - id: AC-3
    criterion: The artefact oracle asserts removability; the POSIX mode assertion is retained additively.
    verified_by: new test
  - id: AC-4
    criterion: No production file modified.
    verified_by: git status
  - id: AC-5
    criterion: >-
      Full suite green; ruff check clean; ruff format --check green; mypy src clean;
      mypy src tests <= 93; total skips <= 6 with the three phase-05 killpg skips named
      as pre-existing and unrelated.
    verified_by: §7 gates
```

---

### `B4` — Widen the transform so the redaction claim is true (`SEC-006`)

**Goal.** `sanitize_text_for_log` matches `https?://[^\s'"<>]+` and nothing else, while the
product states that subprocess output is sanitised to redact "any signed CDN URLs **or
cookie file paths**". The capability is present and simply not pointed at the surface that
needs it. **Documentation duty narrows to two items** (§2.7).

**Findings carried.** `SEC-006`. Newly in scope: `cookie_file_cleaned_up`'s `path=` field
(DEBUG, every successful download) and `cookie_file_cleanup_failed`'s `path=` field —
the live instances of the shape the transform cannot match.

**Exact semantic scope.**

1. `utils/url_sanitizer.py::sanitize_text_for_log` — add the artefact-name rule.
2. `utils/url_sanitizer.py::_URL_REGEX` — the module-level pattern; whatever new pattern is
   introduced is a sibling constant, not an edit to `_URL_REGEX`, whose URL-only scope is
   load-bearing.
3. `utils/url_sanitizer.py::sanitize_text_for_log`'s docstring — **item (a)** of the
   remaining documentation duty: state which shapes **are** matched and which are **not**.
   `_strip_auth_params`'s docstring was already corrected by `09f1b10`; do not revisit it.
4. `services/ytdlp_downloader.py`'s `SEC-002:` comment — already corrected by `09f1b10`
   (it no longer claims "or cookie file paths"). **Do not re-litigate.**
5. `tests/test_url_sanitizer.py` — the four **existing** cases must pass **unchanged**; add
   a case for an artefact path, including `cookie_file_cleanup_failed`'s own `path` value
   shape; a case proving double application equals single application.
6. **Item (b)** of the documentation duty — name `Cookie:` headers as uncovered — applies
   **only if** `D-5` resolves to `Alt A`.

**`D-5` — genuine uncertainty. No choice is made here.**

- **`Alt A`** — artefact-name patterns only (`vk_cookies_[^\s'"]+`, `vk_ffmpeg_[^\s'"]+`).
  Smallest change that makes the product's own claim true. Leaves bare `name=value` pairs
  and `Cookie:` header values unmatched.
- **`Alt B`** — `Alt A` plus a `Cookie:`-header rule.

**Criterion:** `Alt B` requires evidence that a sink receives a `Cookie:` header **from a
child process**. Absent that evidence, `Alt B` adds a rule for a shape nothing produces,
which is speculative. Note the measured fact that pushes the other way:
`services/ffmpeg_utils.py` does import `sanitize_text_for_log` for merge-failure stderr,
so child stderr *is* a sink — but whether a child ever prints a `Cookie:` header is exactly
the third-party-behaviour question plan 11 records as skip S-4 and declines to answer. That
is why this is a research question, not a judgement call.

**Open decisions.** `B4-D1` — `D-5`'s alternative. `B4-D2` — whether the replacement value
keeps a recognisable stem. **This is a product question and it is in §9 Q2**: the operator
reads these records to triage a failure, so whether a redacted artefact path leaves a
recognisable remainder is an experience decision, not a technical one.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | An artefact path in free text is redacted, including the shape of `cookie_file_cleanup_failed`'s and `cookie_file_cleaned_up`'s `path` values. | new test |
| 2 | The four **existing** cases pass **unchanged**. | `uv run pytest tests/test_url_sanitizer.py -q` |
| 3 | Double application equals single application. | new test |
| 4 | Text with no matched shape is byte-identical. | new test |
| 5 | The host stays visible. | new test |
| 6 | The docstring states what is matched and what is not; `Cookie:` headers are named as uncovered if `Alt A`. | review |
| 7 | `_URL_REGEX` keeps its URL-only scope. | review |
| 8 | **Gates:** full suite green · `ruff check` clean · `ruff format --check` **green** · `mypy src` clean · `mypy src tests` ≤ 93. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | Every sink that can carry an artefact path must be enumerated on the live tree — and the enumeration grew since plan 11 (§2.5). |
| `Researcher` | **yes** | `D-5` turns on real-world log-redaction practice for header values and path shapes, and on the child-process behaviour plan 11 records as skip S-4. Neither is derivable from the repository. |
| `Planner` | **yes** | `Alt B` changes the double-application guarantee for every downstream consumer — `B5` and `B6` both depend on it. |
| `Validator` | **yes** | Idempotency and "unmatched text is byte-identical" are the two properties most easily broken by an over-eager pattern, and they are the two `B6` inherits. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `fix(sanitizer): redact the product's own artefact names in child output`

```yaml
id: EB-B4
title: Widen sanitize_text_for_log to cover the product's own artefact names
priority: medium
depends_on: []
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.4, §6.6 (T-B4), §7.1 (B4 row)"
source_blocks: [B4]
description: >-
  sanitize_text_for_log matches https?:// and nothing else, so a bare filesystem path -
  the shape of the credential artefact's own name - passes through it byte-identical
  while the product states that subprocess output is redacted for cookie file paths.
  The live instances are cookie_file_cleanup_failed and cookie_file_cleaned_up, both of
  which carry path=str(...); the latter fires at DEBUG on every successful download.
  Documentation duty is narrowed to two items, because 09f1b10 already corrected the
  sanitize_text_for_log docstring and the SEC-002 comment.
goals:
  - The product's redaction claim about artefact names is true in code.
  - The transform stays additive, idempotent, and byte-identical on unmatched text.
files:
  - path: src/vkdownloader/utils/url_sanitizer.py
    targets: modify
    semantic_anchors:
      - sanitize_text_for_log
      - _URL_REGEX
      - _strip_auth_params
  - path: tests/test_url_sanitizer.py
    targets: modify
    semantic_anchors:
      - the existing sanitize_text_for_log cases
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: no-change
    semantic_anchors:
      - the SEC-002 comment above the download_failed log site
changes:
  - what: Add an artefact-name rule to sanitize_text_for_log as a sibling pattern.
    why: >-
      The declared protection for the credential file's path is not delivered by the code
      that claims to deliver it.
    alternatives_considered:
      - "Alt A: artefact-name patterns only (vk_cookies_..., vk_ffmpeg_...)."
      - "Alt B: Alt A plus a Cookie: header rule (requires evidence a child prints one)."
    blocked_by: []
  - what: State what is matched and what is not; name Cookie: headers as uncovered under Alt A.
    why: >-
      A coverage claim nobody can check is the defect SEC-006 names.
    alternatives_considered: []
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: An artefact path in free text is redacted, including the path field shape.
    verified_by: new test in tests/test_url_sanitizer.py
  - id: AC-2
    criterion: The four existing cases pass unchanged.
    verified_by: uv run pytest tests/test_url_sanitizer.py -q
  - id: AC-3
    criterion: Double application equals single application; unmatched text is byte-identical; the host stays visible.
    verified_by: new tests
  - id: AC-4
    criterion: _URL_REGEX keeps its URL-only scope.
    verified_by: review
  - id: AC-5
    criterion: Full suite green; ruff check clean; ruff format --check green; mypy src clean; mypy src tests <= 93.
    verified_by: §7 gates
```

---

### `B5` — Transform the terminal echo (`SEC-005`)

**Goal.** `_echo_ytdlp_line` writes raw `line`/`text` to `sys.stderr` with nothing applied
to it, while the same bytes are transformed by `sanitize_text_for_log` before they reach
the log file. Inside one run the identical input is treated two ways.

**Findings carried.** `SEC-005`; `B4`'s `D-5`; the ruling recorded on `OUT-007` — non-progress
child output becomes **one log record per line**, with `sys.stderr` kept clean.

**Exact semantic scope.**

1. `services/ytdlp_downloader.py::_echo_ytdlp_line` — apply the transform to `line` and to
   `text` before anything reaches `sys.stderr`. Its docstring currently describes no
   transform; it must describe the one now applied.
2. `services/ytdlp_downloader.py::_is_ytdlp_progress_line` — **unchanged.** Confirmed as the
   write-branch admission predicate. `_parse_ytdlp_progress` is a different function on a
   different branch and is not this predicate.
3. `services/ytdlp_downloader.py::_drain_output` and `::_monitor_progress` — the drain
   path's record-per-line ruling. **Do not touch** `ytdlp_reader_line_overrun`; it is
   phase-05/plan-10 work and is counted in `B6`'s enumeration, not edited here.
4. `tests/test_hls_downloader.py` — the `echo` contract: `\r` rewrite unchanged ·
   **`echo=False` writes nothing to stderr** · the rewritten non-progress test asserts the
   owner's record-per-line ruling · a new redaction case.

**Open decisions.** `B5-D1` — none outstanding on the ruling; it is recorded. `B5-D2` —
whether `sanitize_url_for_log`'s all-or-nothing fallback is ever a better fit than
`sanitize_text_for_log` for this surface. Criterion: the echo surface admits any
non-progress line whole, so a partial-value transform is the correct control and an
all-or-nothing one would destroy the operator's diagnostic text. Default is clear; recorded
for the Validator.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | A signed CDN address in a non-progress line reaches the console **redacted**, while the benign "unchanged" case stays green. | new test |
| 2 | The `\r` rewrite is unchanged. | existing test |
| 3 | `echo=False` writes nothing to stderr. | existing test |
| 4 | The rewritten non-progress test asserts the record-per-line ruling. | review |
| 5 | The one declared test change is a **rewrite with a reason**, never a relaxation, and the reason is in the commit message. | commit message |
| 6 | `_echo_ytdlp_line`'s docstring describes the transform now applied. | review |
| 7 | `ytdlp_reader_line_overrun` and both `ffmpeg_utils` merge records are untouched. | review |
| 8 | **Gates:** full suite green · `ruff check` clean · `ruff format --check` **green** · `mypy src` clean · `mypy src tests` ≤ 93. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The admission predicate and the exact write branches must be re-derived on the live tree; plan 11's own record admits the site enumeration drifted once already. |
| `Researcher` | no | The control is chosen and specified; there is no external behaviour in question. |
| `Planner` | **yes** | One declared test rewrite in a file three other blocks also write (§4). |
| `Validator` | **yes** | The stderr-clean half is the half the owner's ruling *strengthens* and the half most easily broken by this change. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `fix(ytdlp): sanitize child lines before they reach the terminal`

```yaml
id: EB-B5
title: Apply the redaction transform inside the child-output echo
priority: high
depends_on: [EB-B4]
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.5, §6.7 (T-B5), §7.1 (B5 row), §1.6 (record-per-line ruling)"
source_blocks: [B5]
description: >-
  _echo_ytdlp_line writes raw child lines to sys.stderr with nothing applied, while the
  same bytes are transformed before they reach the log file. The admission predicate is
  _is_ytdlp_progress_line, so every non-progress line passes straight through. This block
  applies the transform before anything reaches stderr and records the owner's ruling that
  non-progress output becomes one log record per line with stderr kept clean.
goals:
  - The two surfaces agree by construction rather than by two call sites remembering to.
  - The stderr-clean half of the echo contract is preserved.
files:
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: modify
    semantic_anchors:
      - _echo_ytdlp_line
      - _is_ytdlp_progress_line
      - _download_with_ytdlp
      - _drain_output
      - _monitor_progress
  - path: tests/test_hls_downloader.py
    targets: modify
    semantic_anchors:
      - the echo contract tests
      - the non-progress output tests
changes:
  - what: Transform line and text with sanitize_text_for_log before the stderr write.
    why: >-
      The same bytes are treated two ways in one run; the unredacted surface is the one
      most likely to be captured.
    alternatives_considered:
      - "sanitize_url_for_log's all-or-nothing fallback - rejected: it would destroy the operator's diagnostic text on a surface that admits whole lines."
    blocked_by: []
  - what: Update _echo_ytdlp_line's docstring to describe the transform.
    why: >-
      The docstring currently describes no transform, which is how the gap survived.
    alternatives_considered: []
    blocked_by: []
  - what: Rewrite the non-progress echo test to assert the record-per-line ruling.
    why: >-
      The ruling changes what the test may assert; a relaxation is prohibited.
    alternatives_considered: []
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: A signed CDN address in a non-progress line reaches the console redacted.
    verified_by: new test
  - id: AC-2
    criterion: The \r rewrite is unchanged and echo=False writes nothing to stderr.
    verified_by: existing tests
  - id: AC-3
    criterion: The declared test change is a rewrite with a stated reason.
    verified_by: git log -1
  - id: AC-4
    criterion: ytdlp_reader_line_overrun and both ffmpeg merge records are untouched.
    verified_by: review
  - id: AC-5
    criterion: Full suite green; ruff check clean; ruff format --check green; mypy src clean; mypy src tests <= 93.
    verified_by: §7 gates
```

---

### `B6` — One central redaction processor (`SEC-007`) — **highest risk in this plan**

**Goal.** Exception text and rendered tracebacks reach the log untransformed at **21 record
names across 24 sites** (§2.4). The product redacts its own `url` field two keys away in the
same record, so the log looks protected while the address sits in the adjacent field. Install
one `structlog` processor that redacts centrally, so no call site is edited and a new call
site is covered by construction.

**Findings carried.** `SEC-007` (HIGH), including the eight traceback-carrying records; the
21/24 enumeration; the two already-sanitised-at-call-site records; `cookie_file_cleaned_up`'s
`path` field.

**Measured chain in `config.py::setup_logging` — position is load-bearing.**

| # | Processor |
|---|---|
| 1 | `structlog.contextvars.merge_contextvars` |
| 2 | `structlog.stdlib.add_log_level` |
| 3 | `structlog.processors.TimeStamper(fmt="iso", utc=True)` |
| 4 | **`structlog.processors.format_exc_info`** — an `ExceptionRenderer`; structlog **26.1.0** |
| 5 | `structlog.processors.UnicodeDecoder()` |
| 6 | `structlog.processors.JSONRenderer()` if `settings.log_file` else `structlog.dev.ConsoleRenderer()` |

There is exactly **one free slot, position 5**, between `format_exc_info` and the renderer.
Empirically `format_exc_info` **consumes** `exc_info` and writes the rendered traceback into
the **`exception`** key — so a processor placed at 5 sees `exception`, never `exc_info`.

**Exact semantic scope.**

1. **The processor** — a `structlog` processor that redacts values, event-name-agnostic,
   idempotent, and never raising.
2. `config.py::setup_logging` — insert it at **position 5**. **No other processor moves.**
   `cli.py` gets the same wiring for its own pre-`setup_logging` console path, limited to
   whatever that path actually uses.
3. **Zero edits** to any of the 21 records' call sites, and **zero** to `cli.py`'s handlers.
   This is the whole point of the block: the rejected `Alt B` remedy was per-site wrapping,
   and `486bfd9` already applied it to two records.
4. **Do not touch `services/ffmpeg_utils.py`'s merge code.** `batch_merge_failed` and
   `final_merge_failed` are plan-10 `B14`'s records; their `sanitize_text_for_log` calls stay
   exactly as they are. They are the **idempotency fixture**: values already transformed once
   must come out unchanged.
5. **Excluded** as plan 11 directs: `infrastructure/network_monitor.py` × 4 — class name only.
6. **The eight traceback-carrying records** are covered because their rendered text lands in
   `exception`: `browser_launch_failed`, `browser_close_failed`, `playwright_stop_failed`,
   `video_player_click_failed`, `ytdlp_not_found` (`exc_info=True`), and `download_failed`,
   `batch_download_failed`, `unexpected_error_in_batch_download` (`logger.exception`).
7. `tests/` — the five tests in plan 11 §7.1's `B6` row, plus the corrected 21/24 enumeration.

**`D-7` — key allowlist vs all strings. Genuine uncertainty. No choice is made here.**

- **`Alt A` — key allowlist.** Candidate keys on the measured facts: **`error`**,
  **`exception`**, and **`path`** — the last added here, because `cookie_file_cleanup_failed`
  and `cookie_file_cleaned_up` both carry `path=str(...)` and the latter fires at DEBUG on
  every successful download. Narrower, cheaper, no false positives on operator messages.
- **`Alt B` — every string value.** Broadest, zero key knowledge needed, and therefore
  robust to a future record that names its payload something else. Cost: it will eventually
  redact a legitimate operator-facing message, which degrades failure diagnosis.

**Criterion:** measured collisions. `path=` also appears at `cli.py`'s
`env_file_resolved`, `infrastructure/browser.py`'s `add_init_script`,
`utils/security.py`'s output-path record, `ytdlp_downloader.py`'s
`failed_to_cleanup_partial_file`, and one further `path=` site — so `path` is **not** a
path-only key and `Alt A` needs a rule that does not blind those. Redaction must also be
**idempotent against the two already-sanitised records**. If `Alt B` is chosen, the
Validator must confirm the operator-facing sites are acceptable collateral.

**Placement and visibility — genuine uncertainty. No choice is made here.**

- **Module:** extend `utils/url_sanitizer.py` (default in plan 11; no frozenset edit) **or**
  create `utils/log_redaction.py` (mandatory `EXPECTED_SDIST_ENTRIES` / `EXPECTED_WHEEL_ENTRIES`
  edit in `tests/test_packaging.py`). Criterion for choosing: single responsibility. The
  processor is not a URL sanitiser; a module named `url_sanitizer` gaining an
  event-dict-transforming processor is a naming debt. If the new module is chosen,
  `tests/test_packaging.py` is **not** `no-change` — the frozensets are asserted constants
  and the packaging gate (`14 passed`) will fail until they are updated in the same commit.
- **Name visibility:** `config.py` is **not named in any layer of `docs/STRUCT.md`** (§2.8),
  so plan 11's "entry-adjacent must be a public name" rule is an inference. Measured:
  `config.py` imports only `vkdownloader.models.enums` and has **zero** `logger.` calls.
  Meanwhile `utils/__init__.py::__all__` already lists the private `_strip_auth_params`, so the
  package's own convention does **not** require a public name either. Alternatives: a public
  name re-exported from `utils/__init__.py`; a public name on the module path; a private name
  used within the same layer. Criterion: house rule 8 (meaningful, consistent naming) read
  against the entry-layer rule **as written**, which does not cover `config.py`. This is a
  convention question for the Researcher and Planner, not for this plan.

**Open decisions.** `B6-D1` — `D-7`'s alternative. `B6-D2` — module placement, with the
`test_packaging.py` consequence stated. `B6-D3` — name visibility. `B6-D4` — whether the
processor redacts **keys** as well as values (an event whose *key* is a secret is
conceivable and currently unhandled). Criterion: only if a measured instance exists;
otherwise it is speculative and must not be built.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | An `exc_info=True` record's **rendered traceback** is redacted through the **configured** chain. | new test |
| 2 | No edit to any of the 21 records' call sites; no edit to `cli.py`'s handlers. | `git diff` review |
| 3 | `cookie_file_cleanup_failed`'s **both** fields are redacted; `cookie_file_cleaned_up`'s `path` is redacted. | new test |
| 4 | The processor's **chain position** is asserted — a reorder that moves it before `format_exc_info` silently disables the block. | new test |
| 5 | The processor is proven **event-name-agnostic**. | new test |
| 6 | **Idempotency against a pre-sanitised call site**: `batch_merge_failed` and `final_merge_failed` come out unchanged. | new test |
| 7 | All **21** record names and **24** sites are covered by the pipeline; **no** twenty-second record appeared. | re-count at §7 |
| 8 | The processor never raises on a non-string value, a `None`, a nested mapping, or an absent key. | new test |
| 9 | `services/ffmpeg_utils.py`'s merge code is untouched. | `git diff` review |
| 10 | **Gates:** full suite green · `ruff check` clean · `ruff format --check` **green** · `mypy src` clean · `mypy src tests` ≤ 93 · `tests/test_packaging.py` **14 passed**. | §7 |

**Required agent roster — all four.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The enumeration is already known to have grown from 18 to 21 records and the chain position is load-bearing; both must be re-derived against the live `config.py` before a processor is designed. |
| `Researcher` | **yes** | `structlog` 26.1.0 processor contracts: where a processor may sit, what `format_exc_info` guarantees about `exc_info` consumption, `EventDict` mutation safety, and `cache_logger_on_first_use` interaction. All external, all version-specific. |
| `Planner` | **yes** | Three live decisions (`D-7`, placement, visibility), each with a consequence the other blocks inherit — `B5` and `B4` both depend on the idempotency and coverage guarantees this block fixes. |
| `Validator` | **yes** | Highest-risk block: it edits the single global logging path, and a defect there degrades **every** log record in the product while the test suite stays green. No other block in this plan has that blast radius. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `fix(logging): redact exception text and rendered tracebacks centrally`

```yaml
id: EB-B6
title: Install one central structlog redaction processor
priority: high
depends_on: [EB-B4, EB-B5]
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.6, §6.8 (T-B6), §7.1 (B6 row), §1.5 (Decision B)"
source_blocks: [B6]
description: >-
  Exception text and rendered tracebacks reach the log untransformed at 21 record names
  across 24 sites, including eight that carry a traceback. The product redacts its own url
  field two keys away in the same record. This block installs one event-name-agnostic,
  idempotent structlog processor at chain position 5 - the single free slot between
  format_exc_info and the renderer - so no call site is edited and a new call site is
  covered by construction.
goals:
  - Every one of the 21 records is redacted through the configured chain with zero call-site edits.
  - The two records already sanitised at the call site pass through idempotently.
  - A future reorder cannot silently disable the control.
files:
  - path: src/vkdownloader/config.py
    targets: modify
    semantic_anchors:
      - setup_logging
      - the structlog.configure processors list
  - path: src/vkdownloader/utils/url_sanitizer.py
    targets: conditional
    semantic_anchors:
      - sanitize_text_for_log
  - path: src/vkdownloader/utils/log_redaction.py
    targets: conditional
    semantic_anchors:
      - the processor entry point
  - path: src/vkdownloader/utils/__init__.py
    targets: conditional
    semantic_anchors:
      - __all__
  - path: src/vkdownloader/services/ffmpeg_utils.py
    targets: no-change
    semantic_anchors:
      - batch_merge_failed
      - final_merge_failed
  - path: src/vkdownloader/infrastructure/network_monitor.py
    targets: no-change
    semantic_anchors:
      - the four class-name-only records
  - path: tests/test_packaging.py
    targets: conditional
    semantic_anchors:
      - EXPECTED_SDIST_ENTRIES
      - EXPECTED_WHEEL_ENTRIES
  - path: tests/
    targets: modify
    semantic_anchors:
      - the structlog configuration tests
      - the exception-text record tests
changes:
  - what: Add one event-name-agnostic, idempotent, never-raising redaction processor at chain position 5.
    why: >-
      Per-site wrapping is rejected: 486bfd9 already applied it to two records and it
      leaves every future record unprotected.
    alternatives_considered:
      - "Alt B (rejected): wrap error=str(e) at each site - rejected as the control; survives only as the idempotency fixture."
      - "Alt A (rejected): JSONRenderer wrapper - rewrites the wire format."
    blocked_by: []
  - what: Resolve D-7 - key allowlist (error, exception, path) vs every string value.
    why: >-
      path is not a path-only key: five benign sites also use it, so an allowlist needs a
      rule that does not blind them.
    alternatives_considered:
      - "Alt A: key allowlist - error, exception, path."
      - "Alt B: every string value."
    blocked_by: []
  - what: Choose the module - extend url_sanitizer.py, or add utils/log_redaction.py.
    why: >-
      Single responsibility: an event-dict processor is not a URL sanitiser.
    alternatives_considered:
      - "New module - mandatory tests/test_packaging.py frozenset edit in the same commit."
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: An exc_info=True record's rendered traceback is redacted through the configured chain.
    verified_by: new test
  - id: AC-2
    criterion: No edit to any of the 21 records' call sites and none to cli.py's handlers.
    verified_by: git diff review
  - id: AC-3
    criterion: cookie_file_cleanup_failed's both fields and cookie_file_cleaned_up's path are redacted.
    verified_by: new test
  - id: AC-4
    criterion: The processor's chain position after format_exc_info is asserted.
    verified_by: new test
  - id: AC-5
    criterion: Event-name-agnosticism is asserted.
    verified_by: new test
  - id: AC-6
    criterion: Idempotency against the pre-sanitised batch_merge_failed and final_merge_failed.
    verified_by: new test
  - id: AC-7
    criterion: All 21 record names and 24 sites are covered and no twenty-second record appeared.
    verified_by: §7 re-count
  - id: AC-8
    criterion: The processor never raises on non-string, None, nested-mapping or absent-key input.
    verified_by: new test
  - id: AC-9
    criterion: >-
      Full suite green; ruff check clean; ruff format --check green; mypy src clean;
      mypy src tests <= 93; tests/test_packaging.py 14 passed.
    verified_by: §7 gates
```

---

### `B7` — Mark the session carriers (`SEC-008`)

**Goal.** `HLSDownloadRequest.cookies` is a plain `str` on a Pydantic model and
`DownloadPolicy.headers` is a plain `dict[str, str]` on a dataclass. Both render the session
in full through `repr()`, `str()` and `model_dump_json()`. Nothing in the type system, the
linter or the suite would object to one careless `logger.debug(policy)`.

**Findings carried.** `SEC-008`. Premise holds: `SecretStr`, `repr=False` and `model_dump`
are **zero occurrences** repo-wide, so nothing already does this the wrong way.

**Exact semantic scope.**

1. `models/dtos.py::HLSDownloadRequest.cookies` → `SecretStr`. Not `Field(repr=False)` —
   that hides the field but leaves the value a plain `str`.
2. `services/segment_downloader.py::DownloadPolicy.headers` → `field(repr=False)`. A `dict`
   cannot be a `SecretStr`. A custom `__repr__` printing a header count is acceptable **if
   stated**.
3. **All four sites in one commit** — both `HLSDownloadRequest` constructions
   (`services/downloader.py`, `services/ytdlp_downloader.py::_download_with_ytdlp`), the one
   `DownloadPolicy` construction (`services/segment_downloader.py`), and the consumer that
   unwraps into the outgoing `Cookie` header.
4. `services/ytdlp_downloader.py::_attempt_segment_resume` — the refresh path must still
   work; this is the one file shared with `B5` (§4).
5. `tests/` — `repr()` of an `HLSDownloadRequest` carrying cookies contains no cookie value;
   `repr()` of a `DownloadPolicy` carrying a `Cookie` header contains no header value; the
   segment path still sends the `Cookie` header unchanged; the refresh path still works.
6. **No `Any`.** The unwrap is a typed call.

**Verified premise that removes a caveat.** `pydantic>=2.0.0` **is declared** in
`pyproject.toml`, so `SecretStr` resolves. `T-B7` step 5's `ignore_missing_imports` caveat
is satisfied by inspection and needs no dependency check — record that, do not re-verify it
as a gate.

**Open decisions.** `B7-D1` — none material. If `Alt A`-vs-`field(repr=False)` for
`DownloadPolicy` is contested, the criterion is plan 11's: a `dict` cannot be a `SecretStr`,
`field(repr=False)` costs nothing, and a custom `__repr__` is acceptable only if stated.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | Neither carrier's `repr()` contains its value. | new tests |
| 2 | The segment path still sends the `Cookie` header unchanged. | new test |
| 3 | `_attempt_segment_resume`'s refresh path still works. | existing + new test |
| 4 | All four sites land in **one** commit; no `Any` appears. | `git diff` + mypy |
| 5 | `mypy src` stays clean — this is the real gate here, because the new tests live in `tests/`, whose mypy errors are the 93. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The site counts are the whole finding's evidence (2 constructions, 1 policy construction, 1 consumer). A different count is an `Auditor` finding. |
| `Researcher` | no | `SecretStr` and `field(repr=False)` are well-understood, and `pydantic>=2.0.0` is declared. |
| `Planner` | **yes** | Four sites across three modules and two type systems must move together, and the new tests land in files that already carry mypy errors. |
| `Validator` | **yes** | The risk is a *silently narrowed* secret: an unwrap that returns the wrong thing, or a `Cookie` header that stops being sent. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `fix(models): mark the session carriers so they do not render their contents`

```yaml
id: EB-B7
title: Mark HLSDownloadRequest.cookies and DownloadPolicy.headers as sensitive
priority: medium
depends_on: []
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.7, §6.9 (T-B7), §7.1 (B7 row)"
source_blocks: [B7]
description: >-
  HLSDownloadRequest.cookies is a plain str and DownloadPolicy.headers a plain dict; both
  render the session in full through repr, str and model_dump_json. Marking them makes the
  sensitive field self-describing, which is the property the finding is about. pydantic
  is declared, so SecretStr resolves by inspection. The mypy gate is 93, not 79 or 86.
goals:
  - Neither carrier renders its value through repr, str or model_dump_json.
  - The segment path still sends the Cookie header unchanged and the refresh path still works.
files:
  - path: src/vkdownloader/models/dtos.py
    targets: modify
    semantic_anchors:
      - HLSDownloadRequest
      - HLSDownloadRequest.cookies
  - path: src/vkdownloader/services/segment_downloader.py
    targets: modify
    semantic_anchors:
      - DownloadPolicy
      - DownloadPolicy.headers
      - the DownloadPolicy construction site
      - the Cookie header attachment site
  - path: src/vkdownloader/services/downloader.py
    targets: modify
    semantic_anchors:
      - the HLSDownloadRequest construction site
  - path: src/vkdownloader/services/ytdlp_downloader.py
    targets: modify
    semantic_anchors:
      - _download_with_ytdlp
      - _attempt_segment_resume
      - the HLSDownloadRequest construction site
  - path: tests/
    targets: modify
    semantic_anchors:
      - the HLSDownloadRequest and DownloadPolicy tests
changes:
  - what: cookies becomes SecretStr; headers becomes field(repr=False).
    why: >-
      The subject is the carrier, not the call site; nothing today stops a careless
      logger.debug(policy).
    alternatives_considered:
      - "Field(repr=False) on cookies - rejected: hides the field but leaves a plain str."
      - "A SecretStr header value - not expressible for a dict."
    blocked_by: []
  - what: Update both constructions, the policy construction and the unwrapping consumer in one commit.
    why: A partial move is a type error at best and a silently wrong header at worst.
    alternatives_considered: []
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: Neither carrier's repr contains its value.
    verified_by: new tests
  - id: AC-2
    criterion: The segment path still sends the Cookie header unchanged.
    verified_by: new test
  - id: AC-3
    criterion: The refresh path still works and no Any appears.
    verified_by: existing tests, mypy src
  - id: AC-4
    criterion: Full suite green; mypy src clean; ruff check clean; ruff format --check green; mypy src tests <= 93.
    verified_by: §7 gates
```

---

### `B8` — Record the cookie-harvest decision (`SEC-010`)

**Goal.** The harvest takes the whole context store and nothing narrows it. A reason is
stated — "Includes all cookies to ensure proper CDN authentication" — but no statement says
which consumer needs a cookie for a domain other than the CDN's, and no code asks. Decide
the dependency, write it down, and narrow to it if the answer is that it can be narrowed.

**Findings carried.** `SEC-010`. The bounding fact holds: `storage_state` 0,
`launch_persistent_context` 0, `user_data_dir` 0, `new_context` 1 — the context is
ephemeral, so the blast radius stays bounded and `Alt A` remains the defensible default.

**Exact semantic scope.**

1. `services/extractor.py::_extract_with_browser` — the harvest site
   (`page.context.cookies()`, no argument) carries the written reason naming what the
   cookies are for.
2. `services/extractor.py::_format_cookies_for_ffmpeg` — **docstring only.** Do **not**
   rename it: its name references the retired transport and belongs to the removal track.
3. `services/extractor.py::create_stealth_page` — **the harvest call does not change.**
4. `tests/test_extractor.py` — under `Alt A`, a test pinning the composition contract so an
   accidental change fails.

**`D-9` — the product decision, deferred to §9 Q3.**

- **`Alt A` (default)** — record the dependency precisely at the harvest site and pin the
  composition with a test. **No behaviour change.**
- **`Alt B`** — narrow the flat header by domain suffix. Requires an owner statement of the
  CDN's cookie-domain dependency or a live-origin observation; neither is available, and
  the change **cannot be validated on this platform**. Under `Alt B` a `Validator` review is
  **required** in addition to everything else.

**Open decisions.** `B8-D1` — `D-9`. **This is a product answer, not a technical one**, and
it is §9 Q3. Do not start `Alt B` work before it is answered.

**Stop condition.** Re-verify the bounding fact before anything: `create_stealth_page` still
uses `new_context(viewport=…, user_agent=…, locale=…, timezone_id=…)`, and there is still no
`storage_state`, no `launch_persistent_context`, no `user_data_dir`. **If any has appeared,
the exposure is no longer bounded — this block's priority and default both change; stop and
report.**

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | The harvest site carries a written reason naming what the cookies are for. | review |
| 2 | Under `Alt A`: the composition-pinning test exists and passes; `tests/test_extractor.py` green. | new test |
| 3 | `_format_cookies_for_ffmpeg` is **not** renamed; only its docstring may change. | `git diff` |
| 4 | The harvest call is unchanged. | `git diff` |
| 5 | The commit message records which alternative was chosen and the criterion that decided it. | commit message |
| 6 | **Gates:** as `R1`. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The stop condition is a bounding fact that must be re-derived; if it has moved, the block's shape changes. |
| `Researcher` | **conditional — only under `Alt B`** | Then cookie-domain scoping practice across CDNs and HTTP clients is in question. Not required for `Alt A`, which changes no behaviour. |
| `Planner` | **no** | Under `Alt A` the work is a docstring plus a pinning test. Skipped deliberately. **Required under `Alt B`.** |
| `Validator` | **conditional — required under `Alt B`** | Under `Alt A` the Validator's job is covered by the end-of-plan gate. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `docs(extractor): record why the browser cookie harvest is not filtered`

```yaml
id: EB-B8
title: Record the cookie-harvest dependency at the harvest site
priority: low
depends_on: []
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.8, §6.10 (T-B8), §7.1 (B8 row), §1.7 (Decision C)"
source_blocks: [B8]
description: >-
  The harvest takes the whole context store and nothing narrows it, while the stated reason
  names a consumer but not a dependency. Under the default Alt A this block writes the
  dependency down at the harvest site and pins the composition contract with a test; no
  behaviour changes and _format_cookies_for_ffmpeg is not renamed. Alt B (narrow by domain
  suffix) is blocked on the product answer in §9 Q3 and cannot be validated on this platform.
goals:
  - The harvest's breadth is justified by a written reason or narrowed to a stated dependency.
  - The bounding fact that keeps this LOW - an ephemeral context - is re-verified before any work.
files:
  - path: src/vkdownloader/services/extractor.py
    targets: modify
    semantic_anchors:
      - _extract_with_browser
      - _format_cookies_for_ffmpeg
      - create_stealth_page
  - path: tests/test_extractor.py
    targets: modify
    semantic_anchors:
      - the cookie-harvest tests
changes:
  - what: Record the dependency at the harvest site and pin the composition with a test.
    why: >-
      A judgement recorded as a judgement, with the dependency it rests on named as missing,
      is the correct disposition for a LOW advisory finding.
    alternatives_considered:
      - "Alt B: narrow the flat header by domain suffix - requires an owner dependency statement or a live-origin observation; unvalidatable on this platform."
    blocked_by: [product_decision_Q3]
acceptance_criteria:
  - id: AC-1
    criterion: The bounding fact is re-verified before any edit; a change to it stops the block.
    verified_by: Auditor finding
  - id: AC-2
    criterion: The harvest site carries a written reason naming what the cookies are for.
    verified_by: review
  - id: AC-3
    criterion: _format_cookies_for_ffmpeg is not renamed and the harvest call is unchanged.
    verified_by: git diff review
  - id: AC-4
    criterion: The composition-pinning test exists and passes; tests/test_extractor.py is green.
    verified_by: new test
  - id: AC-5
    criterion: The commit records the chosen alternative and the deciding criterion.
    verified_by: git log -1
```

---

### `B9` — The severity row for a validated finding (`VAL-601`)

**Goal.** The validation stage is told to re-derive every severity from its own verification
and is given a four-row table with no row for the outcome verification most often produces.
Two runs have now independently invented the same rule to fill the gap. A fifth **row** — not
a fifth **word** — gives the instruction a source.

**Findings carried.** `VAL-601`. Audit-pipeline only — **not** an exit-code finding.

**Exact semantic scope.**

1. `.kilo/commands/audit/phases/99-audit-validate.md` — add the fifth **row** to the
   severity table: a finding whose verification passed and whose decision is `validated`.
   The row states both the band and where the band comes from. It does not redefine a
   severity word, and it does not make a decision change a severity. The existing
   decision-application rule — `Validated` keeps the severity as-is — is the source the row
   points at.
2. **Check for sibling copies** of the four-row table under `.kilo/commands/audit/phases/`.
   Fixing one file and not its siblings leaves the corpus inconsistent — **report what you
   find**, and fix the siblings in the same commit if they are the same table.
3. Adjust surrounding prose **only if** the new row makes an existing sentence inaccurate.
4. **Add no fifth severity word.** This block touches exactly one file (or one file plus its
   confirmed siblings). **No source, no test.**

**Open decisions.** None. This is the least uncertain block in the plan.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | A reader can answer "what severity does a validated finding carry?" from the table alone. | review |
| 2 | A fifth **row** exists; no fifth **word** does. | review |
| 3 | No sibling table is left unfixed, or what was found is reported. | Auditor finding + `git diff` |
| 4 | Exactly one file (plus confirmed siblings) is touched. | `git status` |
| 5 | **Gates:** as `R1`, minus the test requirement. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The sibling-copy sweep is a filesystem fact that must be established before the commit's file set is known. |
| `Researcher` | no | The fix is a table row in a project-owned document. |
| `Planner` | no | Single-file, no design. Skipped deliberately. |
| `Validator` | **yes** | An ambiguous row is worse than the gap, because the document's value is that it is followed literally. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `docs(audit): add the severity row for a finding that passes verification`

```yaml
id: EB-B9
title: Add a validated-finding row to the audit severity table
priority: low
depends_on: []
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.9, §6.11 (T-B9), §7.1 (B9 row)"
source_blocks: [B9]
description: >-
  The validation stage is told to re-derive every severity from its own verification and is
  given a four-row table with no row for a validated finding. Two runs have independently
  invented the same rule. This block adds a fifth row - not a fifth word - naming both the
  band and the source the band comes from, and reports any sibling copies of the table.
goals:
  - The instruction at the decision-application rule has a source for every decision.
  - No sibling table is left inconsistent.
files:
  - path: .kilo/commands/audit/phases/99-audit-validate.md
    targets: modify
    semantic_anchors:
      - the severity table
      - the decision-application rule
      - the no-fifth-word statement
changes:
  - what: Add the validated-finding row; fix or report sibling copies of the table.
    why: >-
      An unexecutable instruction is how a document acquires a practice nobody wrote down.
    alternatives_considered: []
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: A reader can answer the validated-finding severity question from the table alone.
    verified_by: review
  - id: AC-2
    criterion: A fifth row exists; no fifth word does.
    verified_by: review
  - id: AC-3
    criterion: No sibling table is left unfixed, or the finding is reported.
    verified_by: Auditor finding
  - id: AC-4
    criterion: Exactly one file plus confirmed siblings is touched.
    verified_by: git status
```

---

### `B10` — Stop the template pre-answering its summary (`VAL-603`) — **evidence corrected, default flipped**

**Goal.** `.ai/audit/templates/audit-findings.md` supplies four sections whose
`## Summary` arrives **pre-answered with zeros**, so a report emitting it verbatim claims to
have found nothing — the one thing `problems-only` forbids.

**Correction 5 — plan 11's evidence base is falsified.** Plan 11 asserts "all **eleven**
`99-validation/*.md` artifacts delete all four sections". Measured: **12 artifacts exist** and
the sections are **not** universally deleted.

| Artifact | What it actually does |
|---|---|
| `02-config-validated-findings.md` | **Keeps all four** and fills `## Summary` with real re-derived tallies (`HIGH 2 / MEDIUM 4 / LOW 2`) plus prose explaining the derivation. The section working exactly as intended. |
| `13-cli-observability-validated-findings.md` | **Keeps all four** and fills `## Summary` with `HIGH 1 / MEDIUM 9 / LOW 7`, same way. |
| `07-filesystem-artifacts-validated-findings.md` | **Keeps and repurposes** `## Summary` as a findings index. |
| `01-entry-architecture-validated-findings.md` | Keeps `## Advisory Recommendations`. |
| **`06-credentials-secrets-validated-findings.md`** — this plan's own spec store | **Keeps all four sections with the template's pre-filled zeros verbatim** (`CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0`) **while its own findings table lists HIGH findings** (`SEC-005`, `SEC-007`, `SEC-009`). |

Plan 11's preferred `Alt B` (delete the four sections) would therefore **remove a section two
executors use correctly** and a third repurposes. The defensible choice is `Alt A` — make
them fillable. **The live instance of `VAL-603`'s actual defect is `06`'s stale zero-table.**

**Alternatives — the default is now `Alt A`. No further choice is required for `Alt A`; the
alternatives are recorded so the reasoning is auditable.**

- **`Alt A` (DEFAULT, reversed from plan 11) — make the four sections fillable.** Remove every
  pre-filled count so the section cannot be answered before the work is done; give the three
  action lists real headings. Evidence-based: two executors already fill them correctly, so
  the format's problem is that the section arrives pre-answered, not that it exists.
- **`Alt B` (rejected) — delete the four sections.** **Rejected on the measured evidence:** it
  would remove a section two executors use correctly and a third repurposes.
- **`Alt C` — keep the zero table and add an instruction to fill it.** Rejected: the failure
  mode is precisely a report emitting the section verbatim; an instruction does not remove
  that route.

**Scope question — reasoned, not assumed.** Is `06`'s stale zero-table in scope for a fix
block? **No, on three grounds, and the reasoning is recorded so it is not re-litigated:**
(1) this execution plan is forbidden from modifying any audit-phase file, and
`.ai/audit/99-validation/**` is audit-phase; (2) `06` is the **historical record** of a
validation run, and editing a historical record to look correct falsifies it; (3) `06` is an
**instance** of the defect, not the defect — the defect is in the template, and the template
is what `B10` fixes. So `06` is recorded here as a live defect for the audit-pipeline owner,
and `B10`'s `Alt A` prevents recurrence by making the section impossible to answer in
advance. **Conditional escalation:** if the Product Owner authorises a post-hoc correction to
`06`, it lands in its **own** commit that says in its message that it is a post-hoc
correction — never silently, and never inside `B10`'s commit.

**Exact semantic scope.**

1. `.ai/audit/templates/audit-findings.md` — remove every pre-filled count; give the three
   action lists real headings; state, per section, whether it is fillable or removed.
2. Fix any cross-reference pointing at a removed section. Leave the `## Findings` block and
   the field-reference table alone, except for those cross-references.
3. **Staging prohibition.** Stage **exactly one path**: `.ai/audit/templates/audit-findings.md`.
   **Never** anything under `.ai/audit/99-validation/**`. Confirm with `git status` before
   committing.
4. **No source, no test.**

**Open decisions.** `B10-D1` — the conditional escalation to `06`, only if the Product Owner
authorises it (see above). No technical decision remains: `Alt A` is the default on the
evidence and no choice is needed.

**Acceptance criteria.**

| # | Criterion | Verified by |
|---|---|---|
| 1 | No pre-filled count remains in the template. | review |
| 2 | Each of the four sections is **fillable**, stated per section in the commit message. | commit message |
| 3 | `git status` shows **no** path under `.ai/audit/99-validation/` touched. | `git status` |
| 4 | Exactly one path is staged. | `git status` |
| 5 | No cross-reference points at a removed section. | review |
| 6 | **Gates:** as `R1`, minus the test requirement. | §7 |

**Required agent roster.**

| Agent | Required | Reason |
|---|---|---|
| `Auditor` | **yes** | The 12-artifact survey is the evidence the block stands on and it has already falsified plan 11 once; it must be re-verified, not inherited. |
| `Researcher` | no | The format is project-owned and the alternative space is closed by the measured evidence. |
| `Planner` | **yes** | The block now carries a scope judgement — what to do about an instance of the defect it is forbidden to touch — and that judgement must be written down before the edit, not after. |
| `Validator` | **yes** | The staging prohibition is the only thing protecting the validation corpus from being edited by a fix block, and this plan's own history shows an audit-phase file being changed by a fix-shaped task. |
| `Implementor` | **yes** | One at a time. |

**Commit shape.** `docs(audit): make the findings template sections fillable instead of pre-answered`

```yaml
id: EB-B10
title: Make the findings template's four sections fillable rather than pre-answered
priority: low
depends_on: []
source_reference: .ai/plans/11-credentials-secrets-audit-fixes.md
source_section: "§3.10, §6.12 (T-B10), §7.1 (B10 row)"
source_blocks: [B10]
description: >-
  The template's Summary table arrives pre-answered with zeros, so a report emitting it
  verbatim claims to have found nothing. Plan 11's evidence - that all eleven validation
  artifacts delete the four sections - is falsified: twelve artifacts exist, two fill all
  four sections correctly with re-derived tallies, a third repurposes Summary as an index,
  and this plan's own spec store keeps the zeros while listing HIGH findings. The default
  therefore flips to Alt A: make the sections fillable.
goals:
  - The four sections cannot be answered before the work is done.
  - Nothing under .ai/audit/99-validation/** is modified.
files:
  - path: .ai/audit/templates/audit-findings.md
    targets: modify
    semantic_anchors:
      - the Summary section
      - the Mandatory Fixes section
      - the Advisory Recommendations section
      - the Doc Updates Needed section
  - path: .ai/audit/99-validation/06-credentials-secrets-validated-findings.md
    targets: forbidden
    semantic_anchors:
      - the pre-filled zero table
changes:
  - what: Remove every pre-filled count; give the three action lists real headings; state per section that it is fillable.
    why: >-
      A zero-filled table is a report that has already answered itself, which is the one
      thing the pipeline's binding rule forbids. Two executors already fill the section
      correctly, so the defect is the pre-answering, not the section.
    alternatives_considered:
      - "Alt B: delete the four sections - rejected on the measured evidence; two executors use them correctly."
      - "Alt C: keep the zeros and instruct the phase to fill them - rejected; the verbatim-emission route stays open."
    blocked_by: []
  - what: Record 06's stale zero-table as a live instance, out of scope for a fix block.
    why: >-
      It is an audit-phase historical record; editing it would falsify the record, and the
      template is the defect.
    alternatives_considered:
      - "Conditional post-hoc correction in its own commit, only if the Product Owner authorises it."
    blocked_by: []
acceptance_criteria:
  - id: AC-1
    criterion: No pre-filled count remains in the template and each section is stated as fillable.
    verified_by: review
  - id: AC-2
    criterion: Nothing under .ai/audit/99-validation/ is modified and exactly one path is staged.
    verified_by: git status
  - id: AC-3
    criterion: No cross-reference points at a removed section.
    verified_by: review
  - id: AC-4
    criterion: The commit message states, per section, fillable or removed.
    verified_by: git log -1
```

---

## §4 Dependency graph, linearised order, and per-block file locks

### 4.1 Graph

```
                    ┌──────────────► B3  (test-only; needs R1's artefact semantics)
                    │
   R1 ──────────────┼──► R2 ──► R3  (CONDITIONAL — blocked on §9 Q1)
   │
   B4 (no deps) ────┼──► B5 ──────┐
                    │             ├──► B6
                    └─────────────┘

   B7  (no deps)      B8 (no deps, Alt A)      B9 (no deps)      B10 (no deps)
```

`R1` precedes `R2` because `R1` decides **where the liveness record lives**, and `R2`'s rule
for a PID-less directory must be chosen to cover it. `B4` precedes `B5` and `B6` because the
idempotency and coverage guarantees they rely on are decided in `B4`. `B3` follows `B6` as a
**content** dependency only — the oracles exercise `setup_logging`'s final shape — and not as
a write lock, because striking the argfile clause removed `B3`'s only production edit.

### 4.2 Linearised order

**Serial chain:** `R1 → R2 → B4 → B5 → B6 → B3`

**Parallel with the chain:** `B7`, `B8` (under `Alt A`), `B9`, `B10` — all four are
independent of every other block and of each other.

**Conditional, after `R2`:** `R3`, only once §9 Q1 is answered.

**A workable single-Implementor sequence:** `R1 → R2 → B4 → B5 → B6 → B3 → B7 → B9 → B10 →
B8`. With a second Implementor, `B7`/`B9`/`B10` may run against `B4`–`B6` **except** that
each file in §4.3 has exactly one writer at a time.

### 4.3 File locks — one writer at a time

| File | Blocks that write it | Note |
|---|---|---|
| `services/ytdlp_downloader.py` | `R1`, `R2`, `B5`, `B7` | The most contended file. Four blocks, strictly serialised. `R1` and `R2` must not overlap. |
| `tests/test_hls_downloader.py` | `R1`, `R2`, `B3`, `B5`, (`R3`) | Also the file plan 11 wrongly called format-red. It is **green**; the commits must leave it formatted without a formatting commit. |
| `utils/url_sanitizer.py` | `B4`, then `B6` (only if `Alt A` placement is chosen) | `B6` must not start until `B4`'s pattern set is frozen. |
| `config.py` | `B6` **only** | `B3`'s `SEC-003:` comment duty is void (§2.6), so `B3` writes **no** production file. |
| `models/dtos.py`, `services/segment_downloader.py`, `services/downloader.py` | `B7` only | No contention. |
| `services/extractor.py`, `tests/test_extractor.py` | `B8` only | No contention. |
| `.kilo/commands/audit/phases/99-audit-validate.md` (+ confirmed siblings) | `B9` only | No contention. |
| `.ai/audit/templates/audit-findings.md` | `B10` only | **Forbidden**: anything under `.ai/audit/99-validation/**`. |
| `tests/test_packaging.py` | `B6` only, and only if the new-module placement is chosen | The frozensets are asserted constants; `14 passed` fails until they are updated in the same commit. |

**`services/ffmpeg_utils.py` is locked read-only for this entire plan.** No block writes it.
`batch_merge_failed` and `final_merge_failed` are plan-10 `B14`'s records and are `B6`'s
idempotency fixture.

---

## §5 Risks — carried forward **corrected**, each with containment

| # | Risk | Status | Containment |
|---|---|---|---|
| 1 | `os.kill(pid, 0)` on Windows would raise, failing every liveness check and making the sweep a no-op. | **CLOSED at `36b801e`** by `D-1`'s `ctypes` probe. | **Preserve it.** §6 prohibits simplifying it away. `R1`/`R2` review criterion 4. |
| 2 | The reaper deletes a **live** credential file belonging to a concurrently running instance. | **NARROWED, NOT CLOSED** — a *live-PID* directory is safe; a **PID-less** directory is still swept. | `R2` closes it. Until `R2` lands, treat the sweep as unsafe against a concurrently-starting run. |
| 3 | **NEW** — `R1`'s removal change may itself create a PID-less window (if the record is deleted before the directory is). | Open, and **created by the fix** rather than pre-existing. | `R1` records its choice; `R2`'s PID-less rule must cover it by construction; the coupling is stated in both commit messages and in `R1-D1`/`R2-D1`'s criteria. This is the single most important interaction in the plan. |
| 4 | **NEW** — unconditional tree removal (`Alt B`) destroys a directory that still holds credential material after a failed `unlink`, silently. | Open. | `R1-D1` criterion 1 forbids it; `R1-D2` requires the record on genuine survival. |
| 5 | **NEW** — `cookie_file_cleaned_up` writes `path=str(cookie_file)` at **DEBUG on every successful download**: an artefact path into the log on the *success* path, a larger exposure than the warning `B2` added. | Open. | In scope for `B4` (pattern coverage) and `B6` (`path` in `D-7`'s allowlist). §2.5. |
| 6 | **NEW** — `vk_cookies__dir` is a third, unfrozen, uncovered artefact string; `.gitignore` does not match it. | Open. | `R1` scope item 6 and `R1-D4`. Criterion: an untracked artefact must never appear in `git status` — sharpened by the pre-existing untracked entries in §6. |
| 7 | **NEW** — the product may delete files it does not own, in a shared temp root, that may belong to a concurrent instance with no PID record. | Open, unbounded. | **Not contained by this plan.** It is §9 Q1. `R3` does not start until it is answered. |
| 8 | **NEW** — `git status` already carries unrelated changes: deleted `.ai/plans/00_overview.md`…`07_*` templates, modified `.ai/problems/PROBLEM.md`, modified `.kilo/commands/audit/implement-plan-multiagent.md`, untracked `tmp/`, `tmp_old_sec.md`, `tmp_old_sec2.md`, untracked plan files 05–08. A careless `git add` sweeps them into a block's commit. | Open. | §6. Every commit stages **specific paths only**. `uv run ruff check .` is red on untracked `tmp/` and is **not a gate**. |
| 9 | The sweep deletes a live artefact (original `VAL-602` hazard). | Closed by `D-1`'s liveness gate. | `R1`/`R2` acceptance criteria. |
| 10 | `ignore_missing_imports = true` hides an undeclared import from the `src` gate. | **RESOLVED for `pydantic`** — `pydantic>=2.0.0` is declared; `SecretStr` resolves by inspection. | `B7` records the inspection rather than re-verifying a gate. Still true for any *future* dependency; no block adds one. |
| 11 | Double transform corrupting a record that a call site already sanitised. | **Load-bearing in production today**, not only in tests — `486bfd9` sanitised two records at the call site. | `B4` AC-3 and `B6` AC-6 assert double application equals single application. |
| 12 | Transform applied **before** the progress predicate — two surfaces keep disagreeing. | Closed by the sweep. | §6 prohibition. |
| 13 | Over-broad redaction degrades failure diagnosis. | Open. | `B4` AC-4 ("unmatched text is byte-identical"); `B6` AC-8 ("never raises"); `D-7` is an explicit choice, not a default. |
| 14 | A `structlog` processor mutates or raises on the event dict and degrades **every** log record while the suite stays green. | Open — highest blast radius in the plan. | `B6` AC-8 plus `Validator` review. `B6` gets all four agents. |
| 15 | `B6` misses a carrier because the enumeration grew (18 → 21 records / 24 sites). | Open. | `B6` AC-7: a re-count at §7, and any new record is an `Auditor` finding. |
| 16 | Narrowing the cookie harvest breaks a CDN dependency that cannot be observed on this platform. | Mitigated by default. | `D-9` defaults to `Alt A` (no behaviour change); `Alt B` requires the product answer (§9 Q3) and a `Validator` review, and is **declared unvalidated on this platform**. |
| 17 | **VOID** — "pre-existing red on `ruff format --check`". | **Deleted.** The gate is green. | §2.3. No exception clause anywhere in §7. |
| 18 | **CORRECTED** — stale count risk. Plan 11 named 18 records, 5-or-6 traceback records, 3 total skips, and `mypy src tests` at both 86 and 79. | Corrected. | §2.2, §2.4, §2.5. Any Implementor quoting 18, 3, 86 or 79 is quoting a void number. |

---

## §6 Regression prohibitions that survive a fix

These survive every block. They are **not** re-litigated by any Implementor.

1. **Do not simplify `_is_pid_alive`'s Windows branch away.** `OpenProcess` with
   `PROCESS_QUERY_INFORMATION` (not `SYNCHRONIZE`), `GetExitCodeProcess`, `CloseHandle`,
   `259` / `STILL_ACTIVE` as alive, `os.kill(pid, 0)` POSIX-only. It is correct.
2. **Do not delete a live artefact.** Never `rmtree` or purge a directory whose recorded
   `owner.pid` names a live process — including the current one.
3. **Do not put an age heuristic in the sweep's *deletion* criterion**, and do not reintroduce
   a top-level glob over the temp root. `VAL-602` rejected both. An age threshold used as a
   *skip* condition is a different thing and is judged separately in `R2`.
4. **Do not touch merge code in `services/ffmpeg_utils.py`.** `batch_merge_failed` and
   `final_merge_failed` are plan-10 `B14`'s records and `B6`'s idempotency fixture.
5. **Do not add a dependency.** `psutil`, `pywin32`, `portalocker` and `polars` are absent and
   stay absent. `D-2`'s deferral stands.
6. **Do not modify any file under `.ai/audit/99-validation/**`.** Audit-phase files are out of
   scope for every block in this plan. `B10`'s staging prohibition names the single path it may
   write.
7. **Do not stage or commit any of the pre-existing unrelated working-tree changes**: the
   deleted `.ai/plans/00_overview.md`…`07_*` templates, `.ai/problems/PROBLEM.md`,
   `.kilo/commands/audit/implement-plan-multiagent.md`, untracked `tmp/`,
   `tmp_old_sec.md`, `tmp_old_sec2.md`, and untracked plan files 05–08. Do not "clean them
   up" either. Every commit stages specific paths.
8. **Do not amend, reset, or rewrite history.** `36b801e`'s empty commit body is discharged by
   a **new** commit's message, never by an amend.
9. **Do not run `git reset` or `git checkout`.** Other agents' work in the tree is normal.
10. **Do not fold an unrelated reformat into a test-semantics change** — and note the original
    motivation is void: `ruff format --check src tests` is green and must stay green.
11. **Do not rename `_format_cookies_for_ffmpeg`** in `B8`. Its name belongs to the removal track.
12. **Do not weaken an oracle into passing.** `B3`'s whole finding is the absence of an
    executable oracle; a converted test that asserts less than the one it replaced is a
    regression, not a fix.
13. **Do not treat `uv run ruff check .` as a gate.** It is red on untracked `tmp/` by design.
14. **Do not treat `uv run mypy src tests`'s exit code as a gate.** It is a delta count only.
15. **Do not treat `uv run mypy` with no path as a gate.** Invalid invocation.

---

## §7 End-of-plan verification gate, re-measured

Run after the last block lands, in this order, and record the outputs in the completion note.
**The pass conditions are the measured `36b801e` values. Any Implementor who quotes 752, 3,
86, 79, 18 or "the format gate is red" is quoting a void number.**

| # | Command | Pass condition |
|---|---|---|
| 1 | `uv run pytest -q -rs` | exit 0 · **skips ≤ 6**, all six named (§2.4) with the three phase-05 `killpg` skips identified as pre-existing and unrelated · **passed ≥ 812** |
| 2 | `uv run ruff check src tests` | `All checks passed!` · exit 0 |
| 3 | `uv run ruff format --check src tests` | exit 0 · **54 files already formatted** — no exception clause |
| 4 | `uv run mypy src` | `Success: no issues found` · 31 source files · exit 0 |
| 5 | `uv run mypy src tests` | error count **≤ 93** (delta gate; exit code is meaningless) |
| 6 | `uv run pytest tests/test_packaging.py -q` | **14 passed** |
| 7 | `git status --porcelain` | only intended paths · **nothing** under `.ai/audit/99-validation/` · **nothing** under `tmp/` · the §6.8 entries untouched and uncommitted |
| 8 | Re-derivation sweep | `atexit`, `mkdtemp`, `O_EXCL`, `chown`, `umask`, `0o700`, `icacls`/`setfacl`/`win32security` — record what now exists in `src/` and confirm it is only what `R1`/`R2` added |
| 9 | Re-count of the exception-text sinks | all **21 record names across 24 sites** are covered by the pipeline · **no twenty-second** appeared |
| 10 | Re-count of the D-11-guarded oracles | **zero** remaining, or every one justified per-oracle in the completion note · total skips still ≤ 6 |
| 11 | Nothing permanent removed | `services/ffmpeg_utils.py` still exports its full permanent surface and still defines `cancel_ffmpeg_process` (a **module-level alias** for `cancel_subprocess`, not a `def`) · `DownloadMethod` still has exactly `YTDLP` and `AUTO` |
| 12 | Frozen strings intact | `vk_cookies_`, `.cookies.txt`, `os.chmod(path, 0o600)`, `cookie_file_cleanup_failed`, `cookie_file_cleaned_up` unchanged |
| 13 | `git log --oneline` | one commit per block, `{type}({scope}): {description}` shape, **nothing amended**, every commit body substantive |

**Not gates, and must never be reported as such:** `uv run ruff check .` (red on untracked
`tmp/`), `uv run mypy` with no path (invalid invocation), `uv run mypy src tests`'s exit code
(delta only), the legacy bare-file residue count (goes to §9 Q1, not to a gate).

---

## §8 Per-finding closure trace

A finding is closed when its **acceptance criterion is observable**, not when a commit exists.

| Finding | Closed when | Block | Verified at |
|---|---|---|---|
| `SEC-001` | The yt-dlp cookie artefact is inside a directory this process created, `atexit` is registered once, and the `DF-007:` comment matches. **The mode bit alone is not the evidence** — it is a measured no-op on Windows. | `R1` (partly already discharged by `36b801e`) | `R1` AC-1, AC-5, AC-6 |
| `SEC-002` — reclamation | A stale directory with a **dead** PID is swept; one with a **live** PID survives; one that is **mid-creation** survives. | `R1`, `R2` | `R2` AC-1, AC-2 |
| `SEC-002` — residue | The **1294** legacy bare files in the shared temp root are reclaimed, **or** formally recorded as open with the operator's options. | `R3` (**conditional**, §9 Q1) — otherwise **stays open** | `R3` AC-1…3 |
| `SEC-003` | **Each surviving oracle has a Windows-executable assertion, or is justified per-oracle**; no surviving oracle claims Windows confinement. The argfile clause is struck and the `SEC-003:` comment needs no edit. | `B3` | `B3` AC-1, AC-2 |
| `SEC-004` | **Superseded, not closed — confirmed by Decision A.** Recorded as retired, its removal surface split into deleted-permanently vs. permanent-product-surface, and skip S-3 re-recorded as retired. **No verification is possible or intended** — a fix here would be the defect. | — | §7 item 11 |
| `SEC-005` | A signed CDN address in a non-progress line reaches the console **redacted**, while the benign "unchanged" case and the stderr-clean clause stay green. The one declared test change is recorded with its reason. | `B5` | `B5` AC-1…3 |
| `SEC-006` | An artefact path in free text is redacted — including **`cookie_file_cleanup_failed`'s own `path` field** and **`cookie_file_cleaned_up`'s**, which fires on every success. Text with no matched shape is byte-identical; the host stays visible; double application is a no-op. | `B4` (and `B6` for the pipeline guarantee) | `B4` AC-1…4 |
| `SEC-007` | An `exc_info=True` record's **rendered traceback** is redacted through the **configured** chain, with **no** edit to any of the 21 call sites, none to `cli.py`'s handlers, and the processor proven event-name-agnostic and idempotent. | `B6` | `B6` AC-1…6 |
| `SEC-008` | Neither carrier's `repr()` contains its value, and the segment path still sends its `Cookie` header. | `B7` | `B7` AC-1, AC-2 |
| `SEC-009` | **Closed at `f6e8ebe`.** A host-only domain survives a real `YoutubeDLCookieJar` round trip **on its own** and **in a mixed file**, with the dotted case unaffected. | `B1` — **no block** | landed |
| `SEC-010` | The harvest site carries a written reason naming what the cookies are for, and the composition is pinned by a test. Under `Alt B` instead: the narrowed set is demonstrated by a test and the change is **declared unvalidated on this platform**. | `B8` | `B8` AC-2, AC-4 |
| `VAL-601` | The table has a row for a validated finding; it introduces no fifth severity **word**; no sibling table is left unfixed. **Audit-pipeline only — not an exit-code finding.** | `B9` | `B9` AC-1…3 |
| `VAL-602` | **Partially discharged by `36b801e`**; narrowed, not closed. Closed only when: no top-level glob, no age heuristic in the deletion criterion, a liveness gate with its own survival test, a PID-less directory that survives, and the reconciled order (sweep defined before the run's directory is created; the `finally` still removes the file). | `R1`, `R2` | `R2` AC-1…4 |
| `VAL-603` | No pre-filled count remains in the template; all four sections are **fillable**, stated per section; nothing under `.ai/audit/99-validation/` is touched. `06`'s stale zero-table is recorded as the live instance and left to its owner. **Audit-pipeline only — not an exit-code finding.** | `B10` | `B10` AC-1, AC-2 |

**Counts that must not drift again:** exception-text records **21 / 24 sites**; traceback
records **8**; D-11-guarded oracles **3**; total skips **6**; `mypy src tests` **93**; suite
**812 passed**.

---

## §9 Open decisions requiring a **product** answer

Three questions. Each is about behaviour the operator sees, a rule the product applies, or a
trade-off the operator owns. Nothing technical or architectural is in this list — those are
the Researcher and Planner's decisions inside each block, with criteria recorded there.

### Q1 — Should the product sweep pre-existing bare `vk_cookies_*.cookies.txt` files out of the shared temp root?

**The situation, in product terms.** Earlier versions of the product wrote the borrowed
session straight into the shared temp folder (`%TEMP%`) and never reclaimed it. There are
**1294 such files there now**, and each contains live session material. The product's new
cleanup pass only recognises the private per-run folders introduced by the fix, so those 1294
files are invisible to it and will stay there indefinitely.

**The trade-off.** The operator's shared temp folder also holds files that a **second,
currently running instance** of the product is actively using — and an old-style file carries
no record of who owns it. So there is no way for the product to tell "abandoned" from "in use
right now". Options:

| Option | What the operator gets | What it costs |
|---|---|---|
| **A — reclaim automatically after a stated age** | The 1294 files go away on their own; the folder stops accumulating. | A second concurrent download longer than the threshold can lose its session file mid-transfer. Needs a duration we would otherwise have to invent. |
| **B — reclaim only files older than any plausible run** | Same cleanup, with a bound we can justify. | Still a duration; a very long download could still be caught. |
| **C — do not reclaim; tell the operator they are there and how to remove them** | Nothing is ever deleted that might be in use. `SEC-002`'s residue half stays open and the files stay on disk. | The 1294 files remain until the operator acts. |
| **D — reclaim only when the operator explicitly asks** (a documented command or cleanup step) | Cleanup on demand, with the operator as the decision point. | Not automatic; the operator has to know it exists. |

**Recommendation: D.** It is the only option that cleans up without ever guessing whether
something is live, and it leaves the "how long is a download" question — which we cannot
answer from here — out of the product entirely. If the owner would rather have it fully
automatic, **B** is the honest version of that, and the threshold must be written down with
its reason.

**This is `R3`. It does not start until this is answered.**

### Q2 — When a cookie file's path is redacted in the operator's log, should a recognisable part of it survive?

**The situation, in product terms.** With `R1` and `B4` in place, the path of the credential
file is removed from the log records that mention it — which today include one written at
**debug level on every successful download**, so it is a routine sight, not a rare one.
Operators read those records to work out which file went wrong.

**The trade-off.** The path has two useful halves: the folder (says roughly *when* and *where*),
and the file name (says *which run*). Options:

| Option | What the operator gets | What it costs |
|---|---|---|
| **A — replace the whole path with the redaction marker** | Nothing about the path is disclosed. | The operator cannot correlate the record with a run at all; several failures become harder to triage. |
| **B — keep the folder, remove the file name** | "Something under the temp folder was cleaned up" survives; the identifying part does not. | Still reveals where the product stores credentials — which the folder name also advertises. |
| **C — keep a short non-reversible hint of the file name** | Runs remain correlatable. | A hint is still a hint; hard to reason about and easy to get wrong. |

**Recommendation: B.** The file name is the only part that identifies a specific borrowed
session; the folder does not, and it is already visible to anyone who can read the log. This
keeps the records triageable without disclosing which session was involved.

### Q3 — Does the CDN actually need cookies set for other domains, and if so, which ones?

**The situation, in product terms.** When the product borrows a session from the operator's
browser, it currently takes **every** cookie the page collected and packs them all into one
undifferentiated header that gets sent to whatever server the next media request resolves to.
The code's stated reason is "proper CDN authentication", but nothing says which cookies the CDN
needs beyond its own. A cookie set for an unrelated third-party site therefore travels to the
CDN.

**The trade-off.** Options:

| Option | What the operator gets | What it costs |
|---|---|---|
| **A — keep the current behaviour and write down the reason** | Nothing breaks. | The wider, unscoped header stays; it is the widest single contributor to the credential's footprint on disk, in the process list, and on the wire. |
| **B — send only the cookies whose domain matches the CDN** | The narrowest possible credential footprint. | If the CDN turns out to depend on a cookie set elsewhere, downloads break and **we cannot detect that from here** — it needs a real download against the live service. |

**Recommendation: A, unless the owner knows the answer.** The reason is that we have no way to
validate `B` on this platform: if a real CDN does need a cross-domain cookie, `B` breaks
downloads in a way only a live run would reveal. If the owner knows the CDN's cookie-domain
dependency and can state it, `B` becomes the right answer and we implement it with that
statement recorded in the code.

**This is `B8`'s `D-9`. `B8` proceeds under `A` immediately; `B` waits for this answer.**

---

**End of the execution plan.** Plan 11 remains the historical record and is unmodified; this
file supersedes its execution half only.